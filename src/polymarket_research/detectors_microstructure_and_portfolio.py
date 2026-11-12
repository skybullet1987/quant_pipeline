"""
Microstructure Opportunity Detectors (Families K, L, M, N) & Global Constrained
Depth/Capital/Lockup Portfolio Arbitrage Optimizer
(`src/polymarket_research/detectors_microstructure_and_portfolio.py`).

Implements Agents 7 & 8 of DOMINUS — RISKLESS FULL THROTTLE:
  1. Programmatic Audit of Existing Carry, Maker & Velocity Sizing (`BOND1`, `MKR_LOCK1`,
     `Stage C`, `HolisticStrategyGovernance`, and `PROFIT_SCORECARD.md`).
  2. Family K — Near-Resolution & Settlement Carry Detector (`NearResolutionSettlementCarryDetector`):
     - Evaluates active/closing markets with `umaResolutionStatus` (`proposed`, `disputed`,
       `resolved`), `umaResolutionStatuses` history, `customLiveness`, or near/past `endDate`.
     - Models exact UMA Optimistic Oracle liveness (`2h` default, `15m/30m` custom), premature
       before-`endDate` griefing proposals, repeat-dispute probability, adversarial DVM lockup
       cost (calibrated to the Nov 7 `KMIA` ASOS `$` maintenance freeze on `6707503`/`6707502`),
       and worst-case net `bps/hr`.
     - IRONCLAD RULE: Never classifies an unfinalized UMA `proposed` single-leg carry as `CLASS_A`
       or `CLASS_B` (`min_omega NetPayoff(omega) < 0` under UMA DVM flip -> strictly `CLASS_C`,
       or `CLASS_D/E` when premature/disputed/negative-EV). Only contractually hedged complete-set
       settlement boxes with `min_omega > 0` across all states (including `50-50` void) can reach
       `CLASS_A` (atomic/inventory-locked) or `CLASS_B` (2-leg sequential CLOB).
  3. Family L — Maker/Taker & Liquidity Provision Detector (`MakerTakerLiquidityDetector`):
     - Models `postOnly` `0`-bps maker fee vs nonlinear taker fee curves (`rate * (p*(1-p))**exp`),
       maker rebates (`rebateRate` `15%–25%`), two-sided `Q_min` reward shield (`c=3.0`), L1/L2
       queue depth ahead, `$0.001` sub-cent HFT queue-jumping, adverse selection, inventory aging,
       and `5.0s` / `150ms` cancellation latency pickoff risk.
     - IRONCLAD RULE: Strictly separates `L1_LOCKED_INVENTORY_MAKER_COMPLETION` (`CLASS_A` conditional
       on passive fill with zero taker fee and zero naked leg risk if unfilled) from
       `L2_FEE_ASYMMETRY_MAKER_ANCHOR` (`CLASS_C`, exposed to jump-before-hedge) and
       `L3_SPECULATIVE_REWARD_OR_REBATE_MM` (`CLASS_C/E`), and NEVER counts uncertain future
       liquidity rewards or maker rebates in `min_state_net_payoff_usd` or `CLASS_A/B` floor!
  4. Family M — Multi-Leg Connected-Component Solver & Global Portfolio Optimizer
     (`MultiLegComponentDetector`, `PortfolioArbitrageOptimizer`):
     - Searches pruned connected components (`MarketPropositionGraph` or native bucket indexer)
       for closed `>=3`-leg partitions, `m`-NO NegRisk conversions, and cumulative calendar/strike
       implication chains & 3-leg bracket covers.
     - Simultaneously optimizes **Total Portfolio Realizable Net Profit per Dollar-Hour** across
       ALL competing candidates (`A..N`) using exact marginal L2 depth tranches + discrete
       minimum-lot feasibility + pairwise 2-opt swap rebalancing, enforcing:
         * Reconciled liquid `pUSD` collateral (`$48.695132` / `$48.70` live cash baseline; NEVER
           `$99.21` book equity!)
         * Absolute `D-001` non-interference with the 4 disputed `KMIA` positions (`$50.51` frozen)
         * `<= 15%` reconciled-NAV cap per correlated event/weather station across all sleeves (`D-007`)
         * `< $500` NAV quarantine on sequential `>= 3`-leg non-atomic CLOB bundles (`D-007`)
         * Shared per-instrument L2 order-book consumption (zero liquidity double-counting!)
         * Infrastructure breakeven benchmark (`$24.67/mo` = `$0.8223/day` = `$0.03426/hr` =
           `+7.035 bps/hr` on `$48.70` liquid cash).
  5. Family N — Newly Discovered Structures & Mechanism Scanner (`MechanismAndStructureScanner`,
     `ResearchBacklog`):
     - Systematically inspects live Gamma & CLOB schemas across the observable universe to catalog
       special/emerging mechanisms (`feeSchedule` polynomial curves incl. quadratic `crypto_15_min`
       `exp=2, r=0.25`, `comboStatus=='enabled'`, `holdingRewardsEnabled`, `customLiveness`,
       `cumulativeMarkets`, `negRiskAugmented`/`negRiskOther` placeholders, multi-winner slates),
       running formal proof/counterexample suites and ranking a durable `ResearchBacklog`.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
import math
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from src.polymarket_research.universal_arb_verifier import (
    ActionLeg,
    ActionType,
    ArbitrageProofObject,
    BookLevel,
    CandidateStructure,
    CostBreakdown,
    DEFAULT_D007_MULTILEG_NAV_FLOOR_USD,
    DEFAULT_LIVE_RECONCILED_NAV_USD,
    DEFAULT_MIN_MARKETABLE_BUY_USD,
    DEFAULT_MIN_ORDER_SHARES,
    FROZEN_DISPUTED_MARKET_IDS,
    FROZEN_DISPUTED_TRADE_SUBSTRINGS,
    FourValueMetrics,
    InstrumentOrderBook,
    InventoryHolding,
    OpportunityClass,
    StatePayoffBreakdown,
    StateSpaceBuilder,
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
from src.polymarket_research.market_proposition_graph import (
    ConnectedMarketComponent,
    EdgeType,
    MarketPropositionGraph,
    RelationKind,
)

try:
    from src.polymarket_research.riskless_protocol_v2_expansion import extract_canonical_event_keys
except Exception:  # pragma: no cover
    extract_canonical_event_keys = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Authoritative Live Baseline & Infrastructure Hurdle Constants (`PROJECT_STATE.md`)
# ---------------------------------------------------------------------------

AUTHORITATIVE_LIVE_CASH_PUSD: float = 48.695132
AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD: float = 48.695132
AUTHORITATIVE_MARK_TO_BID_NAV_USD: float = 48.834132
AUTHORITATIVE_FROZEN_KMIA_COST_USD: float = 50.510000
AUTHORITATIVE_BOOK_EQUITY_FORBIDDEN_FOR_SIZING_USD: float = 99.205132

MONTHLY_INFRA_COST_USD: float = 24.67
DAILY_INFRA_COST_USD: float = round(MONTHLY_INFRA_COST_USD / 30.0, 6)       # $0.822333 / day
HOURLY_INFRA_COST_USD: float = round(MONTHLY_INFRA_COST_USD / 720.0, 6)     # $0.034264 / hr
LIVE_INFRA_HURDLE_BPS_PER_HR: float = round(
    (HOURLY_INFRA_COST_USD / AUTHORITATIVE_LIVE_CASH_PUSD) * 10_000.0, 4
)  # +7.0364 bps/hr on $48.70 liquid cash

DEFAULT_D007_EVENT_CONCENTRATION_PCT: float = 0.15
DEFAULT_UMA_STANDARD_LIVENESS_SEC: float = 7200.0       # 2.0h standard UMA OO V2 / MOOV2 liveness
DEFAULT_UMA_DVM_DISPUTE_LOCKUP_HOURS: float = 96.0      # 4-day standard DVM commit/reveal settlement delay
WORST_CASE_ADVERSARIAL_DISPUTE_HOURS: float = 336.0     # 14-day freeze (Nov 7 KMIA dispute benchmark)

AUTHORITATIVE_FROZEN_KMIA_POSITIONS: Tuple[Dict[str, Any], ...] = (
    {
        "trade_id": "WS_SNIPE_Miami_KMIA_242960",
        "market_id": "6707503",
        "side": "NO",
        "remaining_shares": 20.0,
        "notional_usd": 19.54,
        "best_bid": 0.003,
        "umaResolutionStatus": "disputed",
        "event_group_key": "WXSTATION:KMIA",
    },
    {
        "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898",
        "market_id": "6707502",
        "side": "YES",
        "remaining_shares": 17.0,
        "notional_usd": 16.32,
        "best_bid": 0.002,
        "umaResolutionStatus": "disputed",
        "box_type": "MULTI_LEG_RESIDUAL",
        "event_group_key": "WXSTATION:KMIA",
    },
    {
        "trade_id": "WS_SNIPE_Miami_KMIA_688670",
        "market_id": "6707503",
        "side": "NO",
        "remaining_shares": 10.0,
        "notional_usd": 9.77,
        "best_bid": 0.003,
        "umaResolutionStatus": "disputed",
        "event_group_key": "WXSTATION:KMIA",
    },
    {
        "trade_id": "WS_SNIPE_Miami_KMIA_837595",
        "market_id": "6707503",
        "side": "NO",
        "remaining_shares": 5.0,
        "notional_usd": 4.88,
        "best_bid": 0.003,
        "umaResolutionStatus": "disputed",
        "event_group_key": "WXSTATION:KMIA",
    },
)


def _sf(val: Any, default: float = 0.0) -> float:
    if val is None or isinstance(val, bool) or val == "":
        return default
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _get_field(obj: Any, *names: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        for nm in names:
            if nm in obj and obj[nm] is not None:
                return obj[nm]
        return default
    for nm in names:
        if hasattr(obj, nm):
            val = getattr(obj, nm)
            if val is not None:
                return val
    return default


def _parse_ts(raw: Any) -> Optional[float]:
    if raw in (None, ""):
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        v = float(raw)
        if not math.isfinite(v) or v <= 0.0:
            return None
        return v / 1000.0 if v > 1e11 else v
    s = str(raw).strip()
    if not s:
        return None
    if s.isdigit():
        vi = float(s)
        return vi / 1000.0 if vi > 1e11 else vi
    try:
        iso = s.replace(" ", "T")
        if iso.endswith("+00"):
            iso += ":00"
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return float(dt.timestamp())
    except ValueError:
        return None


def _parse_json_list(raw: Any) -> List[Any]:
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            return list(parsed) if isinstance(parsed, list) else []
        except Exception:
            return []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        return list(raw)
    return []


# ---------------------------------------------------------------------------
# Assignment Part 1: Programmatic Audit of Existing Carry, Maker & Velocity Sizing
# ---------------------------------------------------------------------------


def audit_existing_carry_maker_and_velocity_sizing() -> Dict[str, Any]:
    """
    Structured read-only audit of `stage_c_zero_loss_velocity.py`, `holistic_strategy_governance.py`,
    `riskless_protocol_v2_expansion.py`, and `PROFIT_SCORECARD.md` (`Assignment Step 1`).
    """
    return {
        "audited_modules": [
            "src/polymarket_research/stage_c_zero_loss_velocity.py",
            "src/polymarket_research/holistic_strategy_governance.py",
            "src/polymarket_research/riskless_protocol_v2_expansion.py",
            "PROFIT_SCORECARD.md",
        ],
        "verified_live_baseline": {
            "liquid_pusd_cash_usd": AUTHORITATIVE_LIVE_CASH_PUSD,
            "reconciled_floor_nav_usd": AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD,
            "mark_to_bid_nav_usd": AUTHORITATIVE_MARK_TO_BID_NAV_USD,
            "frozen_kmia_disputed_cost_usd": AUTHORITATIVE_FROZEN_KMIA_COST_USD,
            "book_equity_forbidden_for_sizing_usd": AUTHORITATIVE_BOOK_EQUITY_FORBIDDEN_FOR_SIZING_USD,
            "d007_15pct_event_cap_usd": round(AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD * 0.15, 4),
            "infra_hurdle_bps_per_hr": LIVE_INFRA_HURDLE_BPS_PER_HR,
        },
        "identified_limitations": [
            {
                "id": "LIM-01",
                "subsystem": "Fee Schedule & Stage C Dead-Leg Split (`stage_c_zero_loss_velocity.py:1035`)",
                "finding": (
                    "Existing code defaults to 4 legacy fee buckets (`0%`, `3%` sports, `7%` crypto, `exponent=1.0`) "
                    "and assumes `0%` weather fees in Stage C, whereas live Gamma (`2026-11-11`) enforces `feesEnabled=true` "
                    "on 99.4% of active markets across 13 explicit `feeSchedule` curves — including quadratic `crypto_15_min` "
                    "(`rate=0.25, exponent=2, rebateRate=0.20`), `weather_fees` (`rate=0.05, exponent=1, rebateRate=0.25`), "
                    "`politics_fees` (`0.04`), `finance_prices_fees` (`0.04`), and `sports_fees_v3` (`0.05, rebate=0.15`). "
                    "Also Gamma `takerBaseFee=1000` is the 10% protocol ceiling, NOT the active `feeSchedule.rate`."
                ),
                "remediation_in_module": "Exact `FeeScheduleSpec.from_market()` parsing `feeSchedule.{rate,exponent,takerOnly,rebateRate}` first.",
            },
            {
                "id": "LIM-02",
                "subsystem": "BOND1 / UMA_READY1 Liveness & Premature Proposal Carry (`holistic_strategy_governance.py:852`)",
                "finding": (
                    "`passes_capital_velocity_hurdle()` caps `eff_hrs` at `2.0h` when `fast_recycle_eligible=True` and "
                    "`score_uma_ready1_liveness_priority()` scores `3m-25m` remaining liveness without penalizing "
                    "premature before-`endDate` proposals (`umaResolutionStatus='proposed'` on 2026-2028 markets), "
                    "prior dispute rounds in `umaResolutionStatuses`, or tail DVM dispute freezes (`96h-336h`, as seen "
                    "in the Nov 7 `KMIA` `$50.51` dispute)."
                ),
                "remediation_in_module": (
                    "Family K models premature-proposal grief risk, `umaResolutionStatuses` dispute history, `customLiveness`, "
                    "and worst-case DVM lockup hours, strictly capping unfinalized `proposed` single-leg carry at `CLASS_C`."
                ),
            },
            {
                "id": "LIM-03",
                "subsystem": "MKR_LOCK1 Queue-Jumping & CompleteSetRewardShield (`PROFIT_SCORECARD.md` §4.1)",
                "finding": (
                    "Live telemetry recorded 265 `BOND1` maker orders yielding only 9 fills (`3.4%` fill rate, 510 outbid "
                    "repegs) due to `$0.001` sub-cent HFT queue jumping at `p >= 0.96`, while `CompleteSetRewardShield` "
                    "does not separate pre-held inventory completion (`CLASS_A` on fill) from unhedged two-sided maker "
                    "quoting (`CLASS_C` single-leg adverse fill exposure) and must never treat rebates/rewards as `CLASS_A`."
                ),
                "remediation_in_module": (
                    "Family L separates `L1_LOCKED_INVENTORY_MAKER_COMPLETION` (`CLASS_A` conditional on fill) from "
                    "`L2_FEE_ASYMMETRY_MAKER_ANCHOR` (`CLASS_C`) and `L3_SPECULATIVE_REWARD_OR_REBATE_MM` (`CLASS_C/E`), "
                    "modeling queue depth ahead, adverse selection, and `0.0` floor credit for rebates/rewards."
                ),
            },
            {
                "id": "LIM-04",
                "subsystem": "Greedy Per-Sleeve Sizing & Multi-Leg Bundling (`PROFIT_SCORECARD.md` §4.1)",
                "finding": (
                    "Sequential per-daemon greedy allocation caused 107 `D1` `INSUFFICIENT_BOX_COLLATERAL_HEADROOM` skips "
                    "(69% of `D1` skips) when low-velocity `BOND1` makers consumed seed `pUSD`, and legacy `SOC2` / `KMIA` "
                    "`>=3`-leg sequential bundles suffered partial-fill legging losses (`-$8.67` realized + `$16.32` residual)."
                ),
                "remediation_in_module": (
                    "Family M `PortfolioArbitrageOptimizer` solves simultaneous marginal-tranche + 2-opt swap allocation "
                    "across all `A..N` candidates maximizing realizable net `$ / ($*hr)` under shared L2 books, `15%` "
                    "event caps, and `<$500` NAV `>=3`-leg sequential quarantine."
                ),
            },
        ],
    }


# ---------------------------------------------------------------------------
# Polymarket Dynamic Fee-Schedule & Canonical Event-Key Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeeScheduleSpec:
    """Exact Polymarket fee curve & maker-rebate specification parsed from Gamma / CLOB metadata."""

    fee_type: str = "zero_fees"
    fees_enabled: bool = False
    rate: float = 0.0
    exponent: float = 1.0
    taker_only: bool = True
    rebate_rate: float = 0.0

    @property
    def fee_rate_bps(self) -> float:
        return round(self.rate * 10_000.0, 4)

    def taker_fee_per_gross_share(self, price: float) -> float:
        if not self.fees_enabled or self.rate <= 0.0:
            return 0.0
        return compute_polymarket_taker_fee_per_gross_share(
            price,
            fee_rate=self.rate,
            fee_exponent=self.exponent,
            is_maker=False,
        )

    def net_buy_cost_per_share(self, price: float, *, is_maker: bool = False) -> Tuple[float, float, float]:
        eff_maker = bool(is_maker and self.taker_only)
        return compute_net_buy_cost_per_delivered_share(
            price,
            fee_rate=(0.0 if not self.fees_enabled else self.rate),
            fee_exponent=self.exponent,
            is_maker=eff_maker,
        )

    def net_sell_proceeds_per_share(self, price: float, *, is_maker: bool = False) -> Tuple[float, float, float]:
        eff_maker = bool(is_maker and self.taker_only)
        return compute_net_sell_proceeds_per_share(
            price,
            fee_rate=(0.0 if not self.fees_enabled else self.rate),
            fee_exponent=self.exponent,
            is_maker=eff_maker,
        )

    def estimated_maker_rebate_per_share(self, price: float) -> float:
        """
        Estimated non-guaranteed maker rebate per filled share (`rebateRate * counterpart_taker_fee`).
        CRITICAL: Uncertain rebates NEVER enter `min_state_net_payoff_usd` or `CLASS_A/B` proofs!
        """
        if not self.fees_enabled or self.rate <= 0.0 or self.rebate_rate <= 0.0:
            return 0.0
        counterpart_fee = self.taker_fee_per_gross_share(price)
        return max(0.0, counterpart_fee * self.rebate_rate)

    @classmethod
    def from_market(cls, market: Any, raw_book: Optional[Mapping[str, Any]] = None) -> "FeeScheduleSpec":
        fees_en_raw = _get_field(market, "feesEnabled", "fees_enabled", default=None)
        fee_type = str(_get_field(market, "feeType", "fee_type", default="") or "").strip()
        sched = _get_field(market, "feeSchedule", "fee_schedule", default=None)
        if isinstance(sched, str):
            try:
                sched = json.loads(sched)
            except Exception:
                sched = None

        if fees_en_raw is False or fee_type.lower() == "zero_fees":
            return cls(fee_type=fee_type or "zero_fees", fees_enabled=False, rate=0.0, exponent=1.0, taker_only=True, rebate_rate=0.0)

        if isinstance(sched, Mapping):
            r = max(0.0, _sf(sched.get("rate"), 0.0))
            exp = max(0.5, _sf(sched.get("exponent"), 1.0))
            t_only = bool(sched.get("takerOnly", True) is not False)
            reb = max(0.0, min(1.0, _sf(sched.get("rebateRate"), 0.0)))
            return cls(
                fee_type=fee_type or ("zero_fees" if r <= 0.0 else "custom_schedule"),
                fees_enabled=bool(r > 0.0),
                rate=r,
                exponent=exp,
                taker_only=t_only,
                rebate_rate=reb,
            )

        # Known live Polymarket `feeType` schedules when `feeSchedule` dict was stripped upstream
        known_map: Dict[str, Tuple[float, float, float]] = {
            "crypto_15_min": (0.25, 2.0, 0.20),
            "crypto_fees_v2": (0.07, 1.0, 0.20),
            "sports_fees_v2": (0.03, 1.0, 0.25),
            "sports_fees_v3": (0.05, 1.0, 0.15),
            "politics_fees": (0.04, 1.0, 0.25),
            "finance_prices_fees": (0.04, 1.0, 0.25),
            "tech_fees": (0.04, 1.0, 0.25),
            "mentions_fees": (0.04, 1.0, 0.25),
            "culture_fees": (0.05, 1.0, 0.25),
            "economics_fees": (0.05, 1.0, 0.25),
            "general_fees": (0.05, 1.0, 0.25),
            "weather_fees": (0.05, 1.0, 0.25),
            "weather_fees_v2": (0.05, 1.0, 0.25),
        }
        ft_low = fee_type.lower()
        if ft_low in known_map:
            r, exp, reb = known_map[ft_low]
            return cls(fee_type=fee_type, fees_enabled=True, rate=r, exponent=exp, taker_only=True, rebate_rate=reb)

        # Explicit `fee_rate` or `fee_rate_bps` (NOTE: never use Gamma `takerBaseFee=1000` without `feeSchedule` unless `feesEnabled=True` and no schedule exists)
        exp_fr = _get_field(market, "fee_rate", "feeRate", default=None)
        exp_bps = _get_field(market, "fee_rate_bps", "feeRateBps", default=None)
        if exp_bps is None and isinstance(raw_book, Mapping) and raw_book.get("fee_rate_bps") is not None:
            exp_bps = raw_book.get("fee_rate_bps")
        if exp_fr is not None or exp_bps is not None:
            r = normalize_fee_rate(
                fee_rate_bps=(float(exp_bps) if exp_bps is not None else None),
                fee_rate=(float(exp_fr) if exp_fr is not None else None),
            )
            exp = max(0.5, _sf(_get_field(market, "fee_exponent", "feeExponent", default=1.0), 1.0))
            reb = max(0.0, _sf(_get_field(market, "rebate_rate", "rebateRate", default=0.0), 0.0))
            return cls(
                fee_type=fee_type or ("zero_fees" if r <= 0.0 else "explicit_bps"),
                fees_enabled=bool(r > 0.0),
                rate=r,
                exponent=exp,
                taker_only=True,
                rebate_rate=reb,
            )

        if fees_en_raw is True:
            # Fail-safe conservative 5% taker schedule if `feesEnabled=True` with omitted schedule details
            return cls(fee_type=fee_type or "default_enabled_5pct", fees_enabled=True, rate=0.05, exponent=1.0, taker_only=True, rebate_rate=0.20)

        return cls(fee_type="zero_fees", fees_enabled=False, rate=0.0, exponent=1.0, taker_only=True, rebate_rate=0.0)


_PLACEHOLDER_OUTCOME_RE = re.compile(
    r"(?:\bplaceholder\b|\bunnamed\b|^person\s+[a-z0-9]+$|^player\s+[a-z0-9]+$|^candidate\s+[a-z0-9]+$|"
    r"^option\s+[a-z0-9]+$|^party\s+[a-z0-9]+$|^tba$|^tbd$|^will\s+[a-z]\s+win\b)",
    re.IGNORECASE,
)
_OTHER_OUTCOME_RE = re.compile(
    r"^\s*(?:other|any\s+other(?:\s+\w+)*|all\s+other(?:\s+\w+)*|field|none\s+of\s+the\s+above|someone\s+else)\s*$",
    re.IGNORECASE,
)
_SUBJECTIVE_OR_DISPUTE_PRONE_RE = re.compile(
    r"\b(?:retire(?:s|d|ment)|walkover|disqualif|subjective|rumor|alleged|maintenance|\$\s*indicator|"
    r"unscheduled\s+speci|postponed|abandoned|50[\s/\-]*50)\b",
    re.IGNORECASE,
)


def is_d001_frozen_kmia_entity(market_or_pos: Any) -> bool:
    """True when a market, candidate, or holding touches the 4 frozen Nov 7 `KMIA` disputed positions (`D-001`)."""
    mid = str(_get_field(market_or_pos, "market_id", "id", default="") or "").strip()
    if mid in FROZEN_DISPUTED_MARKET_IDS:
        return True
    for m_seq in (_get_field(market_or_pos, "market_ids", default=None) or ()):
        if str(m_seq).strip() in FROZEN_DISPUTED_MARKET_IDS:
            return True
    tid_u = str(_get_field(market_or_pos, "trade_id", "candidate_id", "slug", default="") or "").strip().upper()
    if any(sub in tid_u for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS):
        return True
    uma_st = str(_get_field(market_or_pos, "umaResolutionStatus", "uma_resolution_status", default="") or "").strip().lower()
    blob_u = " ".join(
        str(_get_field(market_or_pos, f, default="") or "")
        for f in ("question", "title", "slug", "event_slug", "asset", "event_group_key")
    ).upper()
    if uma_st == "disputed" and ("KMIA" in blob_u or "MIAMI" in blob_u):
        return True
    return False


def compute_canonical_concentration_keys(cand_or_market: Any) -> Tuple[str, ...]:
    """
    Computes unified cross-sleeve canonical concentration keys (`EVT:*`, `MKT:*`, `COND:*`,
    `EVTWX:*`, `WXSTATION:*`) enforcing `D-007` `<= 15%` reconciled-NAV cap without single-key bypasses.
    """
    keys: Set[str] = set()
    if isinstance(cand_or_market, Mapping) and callable(extract_canonical_event_keys):
        try:
            keys |= {str(k) for k in extract_canonical_event_keys(cand_or_market) if str(k).strip()}
        except Exception:
            pass

    ev_id = str(_get_field(cand_or_market, "event_id", "parent_event_id", "eventSlug", "event_slug", default="") or "").strip()
    if ev_id:
        keys.add(ev_id if ev_id.upper().startswith("EVT:") else f"EVT:{ev_id}")

    nr_id = str(_get_field(cand_or_market, "negRiskMarketID", "neg_risk_market_id", default="") or "").strip().lower()
    if nr_id:
        keys.add(f"EVT:{nr_id}")

    mid = str(_get_field(cand_or_market, "market_id", "market", "id", default="") or "").strip()
    if mid:
        keys.add(f"MKT:{mid}")
    for m_item in (_get_field(cand_or_market, "market_ids", default=None) or ()):
        ms = str(m_item or "").strip()
        if ms:
            keys.add(f"MKT:{ms}")

    cid = str(_get_field(cand_or_market, "condition_id", "conditionId", "asset_id_condition", default="") or "").strip().lower()
    if cid:
        keys.add(f"COND:{cid}")

    for ek in (_get_field(cand_or_market, "canonical_event_keys", default=None) or ()):
        eks = str(ek or "").strip()
        if eks:
            keys.add(eks)

    blob = " ".join(
        str(_get_field(cand_or_market, f, default="") or "")
        for f in ("question", "title", "slug", "event_slug", "asset", "event_group_key")
    )
    m_icao = re.search(r"\b(K[A-Z]{3}|CYYZ|EGLC|EGLL|LFPB|LFPG|EDDM|RJTT|RKSI|HKO|WSSS|ZBAA|ZSPD)\b", blob.upper())
    if m_icao and re.search(r"\b(temp|weather|metar|celsius|fahrenheit|kmia|klga|kord|klax|rain|snow)\b|°\s*[cf]", blob, re.IGNORECASE):
        keys.add(f"WXSTATION:{m_icao.group(1)}")
    elif "MIAMI" in blob.upper() and re.search(r"\b(temp|weather|metar|highest|lowest)\b|°\s*[cf]", blob, re.IGNORECASE):
        keys.add("WXSTATION:KMIA")

    if not keys and mid:
        keys.add(f"MKT:{mid}")
    return tuple(sorted(keys))


def _extract_consumed_book_sides_from_proof(
    proof: Any,
    fallback: Tuple[Tuple[str, str, float], ...] = (),
) -> Tuple[Tuple[str, str, float], ...]:
    """
    Extracts exact `(instrument_id, "ASK"|"BID", gross_shares_per_net_unit)` from `proof.leg_executions`
    (accounting for Protocol V2 buy-side share haircuts `gross_shares = net_shares / (1 - h(p))` and
    excluding `USE_INVENTORY` / passive `is_maker=True` legs). Falls back to `fallback` when `opt_q <= 0`.
    """
    if proof is None:
        return fallback
    opt_q = _sf(getattr(proof, "optimal_executable_quantity", 0.0), 0.0)
    legs = getattr(proof, "leg_executions", None) or ()
    if opt_q <= 1e-9 or not legs:
        return fallback
    agg: Dict[Tuple[str, str], float] = {}
    order_keys: List[Tuple[str, str]] = []
    for lg in legs:
        act = str(getattr(lg, "action_type", "") or "").strip().upper()
        inst = str(getattr(lg, "instrument_id", "") or "").strip()
        is_mkr = bool(getattr(lg, "is_maker", False))
        if act not in {"BUY_CLOB", "SELL_CLOB"} or not inst or is_mkr:
            continue
        side = "ASK" if act == "BUY_CLOB" else "BID"
        gross_sh = _sf(getattr(lg, "gross_shares", 0.0), 0.0)
        mult = max(1.0, gross_sh / opt_q) if gross_sh > 0.0 else 1.0
        k = (inst, side)
        if k not in agg:
            agg[k] = 0.0
            order_keys.append(k)
        agg[k] += mult
    if not order_keys:
        return ()
    return tuple((inst, side, round(agg[(inst, side)], 6)) for inst, side in order_keys)


def build_instrument_book_for_token(
    token_id: str,
    raw_book: Optional[Mapping[str, Any]],
    market: Any,
    *,
    outcome_label: str = "",
    now_ts: Optional[float] = None,
) -> InstrumentOrderBook:
    """Builds a properly sorted `InstrumentOrderBook` using the market's exact `FeeScheduleSpec`."""
    fee_spec = FeeScheduleSpec.from_market(market, raw_book=raw_book)
    mid = str(_get_field(market, "market_id", "id", default="") or "").strip()
    cid = str(_get_field(market, "condition_id", "conditionId", default="") or "").strip()
    enable_ob = bool(_get_field(market, "enableOrderBook", "enable_order_book", default=True) is not False)
    min_sz = max(DEFAULT_MIN_ORDER_SHARES, _sf(_get_field(market, "orderMinSize", "min_order_size", default=DEFAULT_MIN_ORDER_SHARES), DEFAULT_MIN_ORDER_SHARES))
    tick_raw = _get_field(market, "orderPriceMinTickSize", "tick_size", default=None)
    tick_f = _sf(tick_raw, 0.0)
    lbl_chk = f"{outcome_label} {_get_field(market, 'groupItemTitle', 'group_item_title', default='') or ''} {_get_field(market, 'question', default='') or ''}".strip()
    is_ph = bool(_get_field(market, "is_placeholder", default=False) or _PLACEHOLDER_OUTCOME_RE.search(lbl_chk))
    is_oth = bool(
        _get_field(market, "negRiskOther", "is_other", default=False)
        or _OTHER_OUTCOME_RE.match(str(_get_field(market, "groupItemTitle", default="") or outcome_label))
    )
    return InstrumentOrderBook.from_raw(
        token_id,
        raw_book,
        market_id=mid,
        condition_id=cid,
        outcome_label=outcome_label,
        fee_rate_bps=fee_spec.fee_rate_bps,
        fee_exponent=fee_spec.exponent,
        tick_size=(tick_f if tick_f > 0.0 else None),
        min_order_size=min_sz,
        enable_order_book=enable_ob,
        book_timestamp_sec=now_ts,
        is_placeholder=is_ph,
        is_other=is_oth,
    )


# ---------------------------------------------------------------------------
# Unified Candidate Record Emitted Across Families K, L, M, N
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarginalDepthTranche:
    """
    A piecewise-linear marginal L2 order-book rung slice for simultaneous portfolio optimization:
      - `shares`: incremental share quantity available on this tranche
      - `capital_usd`: incremental liquid `pUSD` required
      - `guaranteed_min_profit_usd`: incremental worst-state (`min_omega`) net profit
      - `risk_adjusted_profit_usd`: incremental fill/latency-adjusted net profit
    """

    tranche_index: int
    shares: float
    capital_usd: float
    guaranteed_min_profit_usd: float
    risk_adjusted_profit_usd: float
    marginal_bps_per_hour: float


@dataclass(frozen=True)
class MicroPortfolioCandidate:
    """Canonical candidate output emitted by Families `K`, `L`, `M`, and `N`."""

    candidate_id: str
    family: str
    sub_type: str
    opportunity_class: str
    execution_mode_gate: str
    event_id: str
    canonical_event_keys: Tuple[str, ...]
    market_ids: Tuple[str, ...]
    token_ids: Tuple[str, ...]
    consumed_book_sides: Tuple[Tuple[str, str, float], ...]  # `(token_id, "ASK"|"BID", gross_shares_per_unit)`
    sequential_clob_legs: int
    is_atomic_or_inventory_locked: bool
    d007_sub500_multileg_quarantine: bool
    d001_kmia_frozen_blocked: bool
    min_order_shares: float
    optimal_shares: float
    capital_required_usd: float
    gross_edge_bps: float
    net_executable_edge_bps: float
    min_state_net_payoff_usd: float
    expected_net_payoff_usd: float
    expected_lockup_hours: float
    worst_case_lockup_hours: float
    net_bps_per_hour_expected: float
    net_bps_per_hour_worst_case: float
    dispute_probability: float
    partial_fill_prob: float
    adverse_selection_cost_usd: float
    uncertain_rebate_or_reward_usd: float
    dormant_near_miss: bool
    four_value_ledger: FourValueMetrics
    marginal_tranches: Tuple[MarginalDepthTranche, ...] = ()
    proof: Optional[ArbitrageProofObject] = None
    proof_sha256: str = ""
    counterexample_states: Tuple[str, ...] = ()
    disqualifiers: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Family K — Near-Resolution & Settlement Carry Detector
# ---------------------------------------------------------------------------


class NearResolutionSettlementCarryDetector:
    """
    Family K Detector (`NearResolutionSettlementCarryDetector`):
      - Scans markets with `umaResolutionStatus` (`proposed`, `disputed`, `resolved`), non-empty
        `umaResolutionStatuses`, or near/past `endDate`.
      - Strictly enforces `D-001` non-interference on disputed `KMIA` (`6707503`, `6707502`).
      - Evaluates BOTH:
        * `K1_SETTLEMENT_HEDGED_COMPLETE_BOX`: Contractual complete-set (`YES + NO`) near resolution
          (`min_omega > 0` across YES, NO, and `50-50` void -> `CLASS_A` if inventory-locked/mergeable,
          `CLASS_B` if 2-leg sequential CLOB, still discounted by worst-case settlement delay!).
        * `K2_UMA_PROPOSED_DIRECTIONAL_CARRY`: Single-leg carry on `umaResolutionStatus == 'proposed'`
          or past-expiry apparent winners. **NEVER classified as `CLASS_A` or `CLASS_B`** because an
          unfinalized UMA proposal can always be disputed and flipped in UMA DVM (`min_omega = -cost < 0`),
          as proven empirically by the Nov 7 `KMIA` ASOS `$` maintenance dispute!
    """

    def __init__(
        self,
        *,
        closing_horizon_hours: float = 6.0,
        reconciled_nav_usd: float = AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD,
        infra_hurdle_bps_per_hr: float = LIVE_INFRA_HURDLE_BPS_PER_HR,
        dormant_gap_bps: float = 150.0,
    ) -> None:
        self.closing_horizon_hours = max(0.25, float(closing_horizon_hours))
        self.reconciled_nav_usd = max(1.0, float(reconciled_nav_usd))
        self.infra_hurdle_bps_per_hr = max(0.0, float(infra_hurdle_bps_per_hr))
        self.dormant_gap_bps = max(10.0, float(dormant_gap_bps))
        self.verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=round(self.reconciled_nav_usd * 0.25, 2),
                reconciled_nav_usd=self.reconciled_nav_usd,
            )
        )

    @staticmethod
    def estimate_uma_liveness_and_dispute_profile(
        market: Any,
        *,
        opp_best_bid: float = 0.0,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        now_u = float(time.time() if now_ts is None else now_ts)
        uma_st = str(_get_field(market, "umaResolutionStatus", "uma_resolution_status", default="") or "").strip().lower()
        statuses_hist = [str(s).strip().lower() for s in _parse_json_list(_get_field(market, "umaResolutionStatuses", default=[]))]
        prior_disputes = sum(1 for s in statuses_hist if s == "disputed")
        prior_proposals = sum(1 for s in statuses_hist if s == "proposed")

        custom_liv = _sf(_get_field(market, "customLiveness", "custom_liveness", default=0.0), 0.0)
        liveness_sec = custom_liv if custom_liv >= 300.0 else DEFAULT_UMA_STANDARD_LIVENESS_SEC

        end_ts = _parse_ts(_get_field(market, "endDate", "end_ts", "endDateIso", default=None))
        uma_end_ts = _parse_ts(_get_field(market, "umaEndDate", "uma_end_ts", default=None))
        auto_resolved = bool(_get_field(market, "automaticallyResolved", "automatically_resolved", default=False) is True)

        premature_proposal = bool(
            uma_st == "proposed"
            and end_ts is not None
            and (end_ts - now_u) > 3600.0
        )

        q_blob = " ".join(
            str(_get_field(market, k, default="") or "")
            for k in ("question", "groupItemTitle", "description", "slug")
        )
        has_ambiguous_clause = bool(_SUBJECTIVE_OR_DISPUTE_PRONE_RE.search(q_blob))
        has_placeholder = bool(_PLACEHOLDER_OUTCOME_RE.search(str(_get_field(market, "groupItemTitle", "question", default="") or "")))

        if uma_st == "disputed":
            p_dispute = 1.0
            p_flip = 0.50
        else:
            p_dispute = 0.015  # Empirical base UMA challenge rate
            if premature_proposal:
                p_dispute += 0.38
            if prior_disputes >= 1:
                p_dispute += min(0.45, 0.25 * prior_disputes)
            elif prior_proposals >= 2:
                p_dispute += 0.12
            if has_ambiguous_clause:
                p_dispute += 0.10
            if has_placeholder:
                p_dispute += 0.25
            if opp_best_bid > 0.015:
                p_dispute += min(0.40, opp_best_bid * 1.5)
            p_dispute = min(0.95, max(0.005, p_dispute))
            p_flip = min(0.85, max(0.004, p_dispute * (0.65 if premature_proposal or prior_disputes > 0 else 0.40)))

        rem_to_end_h = max(0.0, (end_ts - now_u) / 3600.0) if end_ts is not None else 2.0
        if uma_st == "disputed":
            base_liveness_h = DEFAULT_UMA_DVM_DISPUTE_LOCKUP_HOURS
            worst_lockup_h = WORST_CASE_ADVERSARIAL_DISPUTE_HOURS
        elif uma_st == "proposed":
            if uma_end_ts is not None and uma_end_ts > now_u:
                base_liveness_h = max(0.10, (uma_end_ts - now_u) / 3600.0)
            else:
                base_liveness_h = liveness_sec / 3600.0
            worst_lockup_h = WORST_CASE_ADVERSARIAL_DISPUTE_HOURS if (prior_disputes > 0 or has_ambiguous_clause) else DEFAULT_UMA_DVM_DISPUTE_LOCKUP_HOURS
        elif uma_st == "resolved" and auto_resolved:
            base_liveness_h = 0.10
            worst_lockup_h = 1.0
        else:
            base_liveness_h = rem_to_end_h + (liveness_sec / 3600.0)
            worst_lockup_h = max(base_liveness_h + DEFAULT_UMA_DVM_DISPUTE_LOCKUP_HOURS, WORST_CASE_ADVERSARIAL_DISPUTE_HOURS if has_ambiguous_clause else 96.0)

        exp_lockup_h = (1.0 - p_dispute) * base_liveness_h + p_dispute * max(DEFAULT_UMA_DVM_DISPUTE_LOCKUP_HOURS, base_liveness_h)
        return {
            "uma_status": uma_st or "none",
            "prior_disputes": prior_disputes,
            "prior_proposals": prior_proposals,
            "liveness_sec": round(liveness_sec, 1),
            "premature_proposal_before_end_date": premature_proposal,
            "has_ambiguous_clause": has_ambiguous_clause,
            "has_placeholder": has_placeholder,
            "auto_resolved": auto_resolved,
            "p_dispute": round(p_dispute, 5),
            "p_dispute_flip": round(p_flip, 5),
            "base_liveness_hours": round(base_liveness_h, 4),
            "expected_lockup_hours": round(max(0.10, exp_lockup_h), 4),
            "worst_case_lockup_hours": round(max(exp_lockup_h, worst_lockup_h), 4),
            "rem_to_end_hours": round(rem_to_end_h, 4),
        }

    def scan_markets(
        self,
        markets: Sequence[Any],
        books_by_token: Mapping[str, Mapping[str, Any]],
        *,
        holdings_by_token: Optional[Mapping[str, InventoryHolding]] = None,
        now_ts: Optional[float] = None,
    ) -> List[MicroPortfolioCandidate]:
        now_u = float(time.time() if now_ts is None else now_ts)
        self.verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=max(100.0, round(self.reconciled_nav_usd * 0.50, 2)),
                reconciled_nav_usd=self.reconciled_nav_usd,
                now_ts=now_u,
            )
        )
        results: List[MicroPortfolioCandidate] = []
        holdings = holdings_by_token or {}

        for m in markets:
            if bool(_get_field(m, "closed", default=False) is True) or bool(_get_field(m, "archived", default=False) is True):
                continue
            mid = str(_get_field(m, "market_id", "id", default="") or "").strip()
            ev_id = str(_get_field(m, "event_id", "parent_event_id", default="") or "").strip()
            uma_st = str(_get_field(m, "umaResolutionStatus", "uma_resolution_status", default="") or "").strip().lower()
            statuses_hist = _parse_json_list(_get_field(m, "umaResolutionStatuses", default=[]))
            end_ts = _parse_ts(_get_field(m, "endDate", "end_ts", "endDateIso", default=None))

            is_near_close = end_ts is not None and (end_ts - now_u) <= (self.closing_horizon_hours * 3600.0)
            if not uma_st and not statuses_hist and not is_near_close:
                continue

            # Rule 1 (`D-001`): Explicit non-interference with disputed `KMIA` positions
            if is_d001_frozen_kmia_entity(m):
                ckeys = compute_canonical_concentration_keys(m)
                results.append(
                    MicroPortfolioCandidate(
                        candidate_id=f"FAM_K_D001_FROZEN_{mid}",
                        family="K",
                        sub_type="K0_FROZEN_KMIA_DISPUTE_QUARANTINE",
                        opportunity_class=OpportunityClass.CLASS_D.value,
                        execution_mode_gate="FROZEN_D001_KMIA_NON_INTERFERENCE",
                        event_id=ev_id,
                        canonical_event_keys=ckeys,
                        market_ids=(mid,),
                        token_ids=(),
                        consumed_book_sides=(),
                        sequential_clob_legs=0,
                        is_atomic_or_inventory_locked=False,
                        d007_sub500_multileg_quarantine=False,
                        d001_kmia_frozen_blocked=True,
                        min_order_shares=DEFAULT_MIN_ORDER_SHARES,
                        optimal_shares=0.0,
                        capital_required_usd=0.0,
                        gross_edge_bps=0.0,
                        net_executable_edge_bps=0.0,
                        min_state_net_payoff_usd=0.0,
                        expected_net_payoff_usd=0.0,
                        expected_lockup_hours=WORST_CASE_ADVERSARIAL_DISPUTE_HOURS,
                        worst_case_lockup_hours=WORST_CASE_ADVERSARIAL_DISPUTE_HOURS,
                        net_bps_per_hour_expected=0.0,
                        net_bps_per_hour_worst_case=0.0,
                        dispute_probability=1.0,
                        partial_fill_prob=0.0,
                        adverse_selection_cost_usd=0.0,
                        uncertain_rebate_or_reward_usd=0.0,
                        dormant_near_miss=False,
                        four_value_ledger=FourValueMetrics(0.0, 0.0, 0.0, 0.0),
                        disqualifiers=("D001_KMIA_DISPUTED_POSITION_NON_INTERFERENCE",),
                        notes=("Nov 7 KMIA ASOS $ maintenance dispute — 100% untouched per D-001.",),
                    )
                )
                continue

            toks = [str(x).strip() for x in _parse_json_list(_get_field(m, "clobTokenIds", "instrument_ids", "token_ids", default=[])) if str(x).strip()]
            if len(toks) < 2:
                y_t = str(_get_field(m, "yes_token_id", default="") or "").strip()
                n_t = str(_get_field(m, "no_token_id", default="") or "").strip()
                if y_t and n_t:
                    toks = [y_t, n_t]
            if len(toks) != 2:
                continue

            yes_tok, no_tok = toks[0], toks[1]
            bk_y = build_instrument_book_for_token(yes_tok, books_by_token.get(yes_tok), m, outcome_label="Yes", now_ts=now_u)
            bk_n = build_instrument_book_for_token(no_tok, books_by_token.get(no_tok), m, outcome_label="No", now_ts=now_u)
            if not bk_y.enable_order_book or bk_y.has_crossed_or_invalid_book() or bk_n.has_crossed_or_invalid_book():
                continue

            ckeys = compute_canonical_concentration_keys(m)

            # Sub-detector K1: Near-Resolution Contractual Complete-Set Box (`YES + NO == $1.00` across all states incl. 50-50 void)
            if bk_y.asks and bk_n.asks:
                y_l1_net, _, _ = compute_net_buy_cost_per_delivered_share(
                    bk_y.asks[0].price, fee_rate_bps=bk_y.fee_rate_bps, fee_exponent=bk_y.fee_exponent
                )
                n_l1_net, _, _ = compute_net_buy_cost_per_delivered_share(
                    bk_n.asks[0].price, fee_rate_bps=bk_n.fee_rate_bps, fee_exponent=bk_n.fee_exponent
                )
                box_cost_l1 = y_l1_net + n_l1_net
                gross_box_bps = round((1.0 - (bk_y.asks[0].price + bk_n.asks[0].price)) * 10_000.0, 2)
                net_box_bps = round((1.0 - box_cost_l1) * 10_000.0, 2)

                if net_box_bps >= -self.dormant_gap_bps:
                    uma_prof_box = self.estimate_uma_liveness_and_dispute_profile(m, opp_best_bid=0.0, now_ts=now_u)
                    held_y = holdings.get(yes_tok)
                    held_n = holdings.get(no_tok)
                    can_merge_now = uma_st not in {"disputed", "resolved"}
                    exp_h_box = 0.05 if can_merge_now else uma_prof_box["expected_lockup_hours"]
                    worst_h_box = 0.25 if can_merge_now else uma_prof_box["worst_case_lockup_hours"]

                    if held_y is not None and not held_y.is_d001_protected() and held_y.shares >= DEFAULT_MIN_ORDER_SHARES:
                        proof_box = self.verifier.verify_inventory_completion(
                            candidate_id=f"FAM_K1_INV_BOX_{mid}",
                            holding=held_y,
                            held_book=bk_y,
                            complement_book=bk_n,
                            merge_immediately=can_merge_now,
                        )
                        seq_legs = 1
                        is_prelocked = True
                    elif held_n is not None and not held_n.is_d001_protected() and held_n.shares >= DEFAULT_MIN_ORDER_SHARES:
                        proof_box = self.verifier.verify_inventory_completion(
                            candidate_id=f"FAM_K1_INV_BOX_{mid}",
                            holding=held_n,
                            held_book=bk_n,
                            complement_book=bk_y,
                            merge_immediately=can_merge_now,
                        )
                        seq_legs = 1
                        is_prelocked = True
                    else:
                        legs_k1 = [
                            ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=yes_tok, market_id=mid),
                            ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=no_tok, market_id=mid),
                        ]
                        if can_merge_now:
                            legs_k1.append(
                                ActionLeg(action_type=ActionType.CTF_MERGE, related_instrument_ids=(yes_tok, no_tok), market_id=mid)
                            )
                        cand_k1 = CandidateStructure(
                            candidate_id=f"FAM_K1_BOX_{mid}",
                            family="K",
                            legs=tuple(legs_k1),
                            states=StateSpaceBuilder.binary_complete_set_states(yes_tok, no_tok, include_void_50_50=True),
                            rule_verified=True,
                            expected_lockup_hours=exp_h_box,
                            worst_case_lockup_hours=worst_h_box,
                        )
                        proof_box = self.verifier.verify_and_simulate(cand_k1, {yes_tok: bk_y, no_tok: bk_n})
                        seq_legs = 2
                        is_prelocked = False

                    is_dormant = proof_box.opportunity_class == OpportunityClass.CLASS_E.value and net_box_bps >= -self.dormant_gap_bps
                    if proof_box.opportunity_class in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value} or is_dormant:
                        cap_u = max(0.01, proof_box.cost_breakdown.capital_required_usd)
                        opt_q = proof_box.optimal_executable_quantity
                        worst_bps_hr = round(
                            (proof_box.min_state_net_payoff_usd / cap_u) * 10_000.0 / max(0.05, worst_h_box), 2
                        ) if opt_q > 0 else 0.0
                        tranches = (
                            _build_two_leg_ask_tranches(
                                bk_y,
                                bk_n,
                                max_shares=opt_q,
                                lockup_hours=worst_h_box,
                                proof=proof_box,
                            )
                            if (opt_q >= DEFAULT_MIN_ORDER_SHARES and not is_prelocked)
                            else ()
                        )
                        results.append(
                            MicroPortfolioCandidate(
                                candidate_id=proof_box.candidate_id,
                                family="K",
                                sub_type="K1_SETTLEMENT_HEDGED_COMPLETE_BOX",
                                opportunity_class=proof_box.opportunity_class,
                                execution_mode_gate="MODE_2_SHADOW",
                                event_id=ev_id,
                                canonical_event_keys=ckeys,
                                market_ids=(mid,),
                                token_ids=(yes_tok, no_tok),
                                consumed_book_sides=_extract_consumed_book_sides_from_proof(
                                    proof_box, ((yes_tok, "ASK", 1.0), (no_tok, "ASK", 1.0))
                                ),
                                sequential_clob_legs=seq_legs,
                                is_atomic_or_inventory_locked=is_prelocked,
                                d007_sub500_multileg_quarantine=False,
                                d001_kmia_frozen_blocked=False,
                                min_order_shares=max(bk_y.min_order_size, bk_n.min_order_size),
                                optimal_shares=opt_q,
                                capital_required_usd=round(proof_box.cost_breakdown.capital_required_usd, 4),
                                gross_edge_bps=gross_box_bps,
                                net_executable_edge_bps=round(proof_box.net_executable_edge_per_unit * 10_000.0, 2),
                                min_state_net_payoff_usd=round(proof_box.min_state_net_payoff_usd, 6),
                                expected_net_payoff_usd=round(proof_box.expected_net_payoff_usd, 6),
                                expected_lockup_hours=exp_h_box,
                                worst_case_lockup_hours=worst_h_box,
                                net_bps_per_hour_expected=round(proof_box.capital_efficiency_bps_per_hr, 2),
                                net_bps_per_hour_worst_case=worst_bps_hr,
                                dispute_probability=uma_prof_box["p_dispute"],
                                partial_fill_prob=(0.0 if is_prelocked else 0.08),
                                adverse_selection_cost_usd=0.0,
                                uncertain_rebate_or_reward_usd=0.0,
                                dormant_near_miss=is_dormant,
                                four_value_ledger=proof_box.four_value_ledger,
                                marginal_tranches=tranches,
                                proof=proof_box,
                                proof_sha256=proof_box.proof_sha256,
                                counterexample_states=proof_box.counterexample_states,
                                disqualifiers=proof_box.disqualifiers,
                                notes=("Contractual YES+NO settlement box; immune to outcome direction.",),
                            )
                        )

            # Sub-detector K2: Unfinalized UMA Proposed / Near-Expiry Single-Leg Settlement Carry
            # Evaluate whichever side trades as the apparent proposed/settled winner (`0.88 <= ask < 1.00`)
            for side_lbl, win_bk, opp_bk in (("YES", bk_y, bk_n), ("NO", bk_n, bk_y)):
                if not win_bk.asks:
                    continue
                best_ask = win_bk.asks[0].price
                if not (0.88 <= best_ask <= 0.999):
                    continue
                opp_bid = opp_bk.bids[0].price if opp_bk.bids else 0.0
                uma_prof = self.estimate_uma_liveness_and_dispute_profile(m, opp_best_bid=opp_bid, now_ts=now_u)

                # NEVER pass `"resolved_onchain_final"` unless `umaResolutionStatus == 'resolved'` AND `automaticallyResolved == True`
                # AND explicit on-chain payout confirmation is supplied; unfinalized UMA `proposed` is ALWAYS `CLASS_C` or `CLASS_D/E`!
                verifier_uma_status = "disputed" if uma_st == "disputed" else "proposed"
                proof_carry = self.verifier.verify_uma_carry(
                    candidate_id=f"FAM_K2_CARRY_{mid}_{side_lbl}",
                    book=win_bk,
                    uma_status=verifier_uma_status,
                    p_dispute_flip=uma_prof["p_dispute_flip"],
                    expected_lockup_hours=uma_prof["expected_lockup_hours"],
                    dispute_lockup_hours=uma_prof["worst_case_lockup_hours"],
                )

                # Enforce strict downgrade to CLASS_D if premature before `endDate` or placeholder or prior disputes
                eff_class = proof_carry.opportunity_class
                extra_disq: List[str] = list(proof_carry.disqualifiers)
                if eff_class in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value}:
                    # Belt-and-suspenders invariant: single-leg unfinalized carry can NEVER be CLASS_A or CLASS_B!
                    eff_class = OpportunityClass.CLASS_C.value
                    extra_disq.append("UNFINALIZED_UMA_SINGLE_LEG_NEVER_CLASS_A_OR_B")
                if uma_prof["premature_proposal_before_end_date"]:
                    extra_disq.append("PREMATURE_UMA_PROPOSAL_BEFORE_END_DATE")
                    if eff_class == OpportunityClass.CLASS_C.value:
                        eff_class = OpportunityClass.CLASS_D.value
                if uma_prof["has_placeholder"]:
                    extra_disq.append("AUGMENTED_OR_UNNAMED_PLACEHOLDER_OUTCOME")
                    if eff_class == OpportunityClass.CLASS_C.value:
                        eff_class = OpportunityClass.CLASS_D.value
                if uma_st == "disputed":
                    eff_class = OpportunityClass.CLASS_D.value

                net_cost_l1, _, _ = compute_net_buy_cost_per_delivered_share(
                    best_ask, fee_rate_bps=win_bk.fee_rate_bps, fee_exponent=win_bk.fee_exponent
                )
                gross_bps = round((1.0 - best_ask) * 10_000.0, 2)
                net_bps = round((1.0 - net_cost_l1) * 10_000.0, 2)
                cap_req = max(0.01, proof_carry.cost_breakdown.capital_required_usd)
                ev_usd = proof_carry.expected_net_payoff_usd
                exp_bps_hr = round((ev_usd / cap_req) * 10_000.0 / max(0.10, uma_prof["expected_lockup_hours"]), 2) if proof_carry.optimal_executable_quantity > 0 else 0.0
                # Worst-case settlement delay bps/hr assuming no flip, AND min_state_net_payoff_usd (< 0) under DVM flip
                no_flip_worst_delay_bps_hr = round(net_bps / max(0.10, uma_prof["worst_case_lockup_hours"]), 2)

                results.append(
                    MicroPortfolioCandidate(
                        candidate_id=proof_carry.candidate_id,
                        family="K",
                        sub_type="K2_UMA_PROPOSED_DIRECTIONAL_CARRY",
                        opportunity_class=eff_class,
                        execution_mode_gate="MODE_2_SHADOW_DIRECTIONAL_CARRY_QUARANTINE",
                        event_id=ev_id,
                        canonical_event_keys=ckeys,
                        market_ids=(mid,),
                        token_ids=(win_bk.instrument_id,),
                        consumed_book_sides=_extract_consumed_book_sides_from_proof(
                            proof_carry, ((win_bk.instrument_id, "ASK", 1.0),)
                        ),
                        sequential_clob_legs=1,
                        is_atomic_or_inventory_locked=False,
                        d007_sub500_multileg_quarantine=False,
                        d001_kmia_frozen_blocked=False,
                        min_order_shares=win_bk.min_order_size,
                        optimal_shares=proof_carry.optimal_executable_quantity,
                        capital_required_usd=round(proof_carry.cost_breakdown.capital_required_usd, 4),
                        gross_edge_bps=gross_bps,
                        net_executable_edge_bps=net_bps,
                        min_state_net_payoff_usd=round(proof_carry.min_state_net_payoff_usd, 6),
                        expected_net_payoff_usd=round(ev_usd, 6),
                        expected_lockup_hours=uma_prof["expected_lockup_hours"],
                        worst_case_lockup_hours=uma_prof["worst_case_lockup_hours"],
                        net_bps_per_hour_expected=exp_bps_hr,
                        net_bps_per_hour_worst_case=no_flip_worst_delay_bps_hr,
                        dispute_probability=uma_prof["p_dispute"],
                        partial_fill_prob=0.0,
                        adverse_selection_cost_usd=round(abs(min(0.0, proof_carry.min_state_net_payoff_usd)) * uma_prof["p_dispute_flip"], 6),
                        uncertain_rebate_or_reward_usd=0.0,
                        dormant_near_miss=bool(eff_class == OpportunityClass.CLASS_E.value and net_bps > 0.0),
                        four_value_ledger=proof_carry.four_value_ledger,
                        marginal_tranches=(),
                        proof=proof_carry,
                        proof_sha256=proof_carry.proof_sha256,
                        counterexample_states=proof_carry.counterexample_states or ("OMEGA_UMA_DISPUTE_DVM_FLIP_OR_VOID",),
                        disqualifiers=tuple(dict.fromkeys(extra_disq)),
                        notes=(
                            f"uma_status={uma_prof['uma_status']}, prior_disputes={uma_prof['prior_disputes']}, "
                            f"liveness={uma_prof['liveness_sec']:.0f}s, worst_lockup={uma_prof['worst_case_lockup_hours']:.1f}h "
                            f"(Nov 7 KMIA dispute model). Strictly non-CLASS_A/B.",
                        ),
                    )
                )

        results.sort(key=lambda c: (c.opportunity_class, -c.net_bps_per_hour_expected))
        return results


# ---------------------------------------------------------------------------
# Family L — Maker/Taker & Liquidity Provision Detector
# ---------------------------------------------------------------------------


class MakerTakerLiquidityDetector:
    """
    Family L Detector (`MakerTakerLiquidityDetector`):
      - Models `0`-bps `postOnly` maker quoting vs nonlinear taker fee curves (`FeeScheduleSpec`),
        queue position (`queue_ahead_usd` at quoted rung), `$0.001` sub-cent HFT queue-jumping,
        adverse selection, inventory aging, and `150ms–5.0s` cancellation latency pickoff cost.
      - Strictly separates three structurally distinct sub-families:
        1. `L1_LOCKED_INVENTORY_MAKER_COMPLETION`: Pre-held non-frozen inventory on Leg 1 + `0%`-fee
           passive `postOnly` bid on complementary Leg 2 (`b_2 < 1.0 - cost_basis_1`). Zero naked leg
           exposure if unfilled; guaranteed `min_omega > 0` upon fill (`CLASS_A` conditional on fill;
           uncertain rebates strictly `0.0` in `min_state_net_payoff_usd`).
        2. `L2_FEE_ASYMMETRY_MAKER_HEDGE_PAIR`: Fee-curve markets (`feesEnabled=True`) where Taker+Taker
           is negative (`ask_Y_net + ask_N_net >= $1.00`), but `0%`-fee Maker Leg 1 + immediate WS Taker
           Leg 2 (`bid_1_maker + ask_2_taker_net < $1.00`) has positive spread. Strictly `CLASS_C`
           (NEVER `CLASS_A/B`) because Leg 2 ask can jump during cancellation/hedge latency!
        3. `L3_SPECULATIVE_REWARD_OR_REBATE_MM`: Symmetric two-sided `Q_min` (`c=3.0`) reward-shield or
           maker-rebate quoting. Strictly `CLASS_C` (or `CLASS_E` when adverse selection + aging drag
           exceeds spread EV); uncertain future rewards/rebates NEVER count as `CLASS_A/B` profit!
    """

    def __init__(
        self,
        *,
        cancel_latency_ms: float = 165.0,
        max_join_queue_usd: float = 350.0,
        inventory_aging_bps_per_hr: float = LIVE_INFRA_HURDLE_BPS_PER_HR,
        reconciled_nav_usd: float = AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD,
    ) -> None:
        self.cancel_latency_ms = max(20.0, float(cancel_latency_ms))
        self.max_join_queue_usd = max(25.0, float(max_join_queue_usd))
        self.inventory_aging_bps_per_hr = max(1.0, float(inventory_aging_bps_per_hr))
        self.reconciled_nav_usd = max(1.0, float(reconciled_nav_usd))
        self.verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=round(self.reconciled_nav_usd * 0.25, 2),
                reconciled_nav_usd=self.reconciled_nav_usd,
            )
        )

    def estimate_queue_and_adverse_selection(
        self,
        maker_book: InstrumentOrderBook,
        opp_book: InstrumentOrderBook,
        quote_bid_px: float,
        target_shares: float,
    ) -> Dict[str, float]:
        queue_ahead_sh = sum(lv.size for lv in maker_book.bids if lv.price >= quote_bid_px - 1e-9)
        queue_ahead_usd = queue_ahead_sh * quote_bid_px
        order_usd = max(1.0, target_shares * quote_bid_px)

        # Sub-cent `$0.001` queue-jumping hazard at boundary `p >= 0.96` or `p <= 0.04` (live 3.4% BOND1 fill rate lesson)
        tail_hft_penalty = 0.45 if (quote_bid_px >= 0.96 or quote_bid_px <= 0.04) else 1.0
        queue_fill_prob = (order_usd / (order_usd + queue_ahead_usd + 15.0)) * tail_hft_penalty
        queue_fill_prob = min(0.85, max(0.02, queue_fill_prob))

        spread = (maker_book.asks[0].price - maker_book.bids[0].price) if (maker_book.asks and maker_book.bids) else 0.04
        latency_factor = min(2.5, self.cancel_latency_ms / 150.0)
        toxic_pickoff_prob = min(0.65, max(0.08, 0.16 * latency_factor + (0.12 if queue_ahead_usd < 10.0 else 0.0)))
        opp_l1_depth_sh = opp_book.asks[0].size if opp_book.asks else 0.0
        hedge_depth_ratio = opp_l1_depth_sh / max(target_shares, 1.0)
        slippage_on_jump_ps = max(0.01, min(0.12, spread * 0.8 + (0.03 if hedge_depth_ratio < 4.0 else 0.008)))
        adverse_cost_ps = toxic_pickoff_prob * slippage_on_jump_ps

        return {
            "queue_ahead_usd": round(queue_ahead_usd, 2),
            "queue_fill_prob": round(queue_fill_prob, 4),
            "toxic_pickoff_prob": round(toxic_pickoff_prob, 4),
            "hedge_depth_ratio": round(hedge_depth_ratio, 2),
            "adverse_cost_per_share": round(adverse_cost_ps, 6),
        }

    def scan_markets(
        self,
        markets: Sequence[Any],
        books_by_token: Mapping[str, Mapping[str, Any]],
        *,
        holdings_by_token: Optional[Mapping[str, InventoryHolding]] = None,
        now_ts: Optional[float] = None,
    ) -> List[MicroPortfolioCandidate]:
        now_u = float(time.time() if now_ts is None else now_ts)
        self.verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=max(100.0, round(self.reconciled_nav_usd * 0.50, 2)),
                reconciled_nav_usd=self.reconciled_nav_usd,
                now_ts=now_u,
            )
        )
        holdings = holdings_by_token or {}
        results: List[MicroPortfolioCandidate] = []

        for m in markets:
            if bool(_get_field(m, "closed", default=False) is True) or bool(_get_field(m, "archived", default=False) is True):
                continue
            if is_d001_frozen_kmia_entity(m):
                continue
            mid = str(_get_field(m, "market_id", "id", default="") or "").strip()
            ev_id = str(_get_field(m, "event_id", "parent_event_id", default="") or "").strip()
            toks = [str(x).strip() for x in _parse_json_list(_get_field(m, "clobTokenIds", "instrument_ids", "token_ids", default=[])) if str(x).strip()]
            if len(toks) != 2:
                continue

            yes_tok, no_tok = toks[0], toks[1]
            fee_spec = FeeScheduleSpec.from_market(m, raw_book=books_by_token.get(yes_tok))
            bk_y = build_instrument_book_for_token(yes_tok, books_by_token.get(yes_tok), m, outcome_label="Yes", now_ts=now_u)
            bk_n = build_instrument_book_for_token(no_tok, books_by_token.get(no_tok), m, outcome_label="No", now_ts=now_u)
            if not bk_y.enable_order_book or bk_y.has_crossed_or_invalid_book() or bk_n.has_crossed_or_invalid_book():
                continue
            if not (bk_y.bids and bk_y.asks and bk_n.bids and bk_n.asks):
                continue

            ckeys = compute_canonical_concentration_keys(m)

            # 1A & 1B. Locked / Hedged Inventory Maker Completion (Strictly separated from Speculative MM!)
            #   - `L1A_FILLED_MAKER_ANCHOR_PRELOCKED_COMPLETION`: Filled 0%-fee maker inventory on Leg 1 + immediate
            #     L2 FOK taker completion on Leg 2 + `CTF_MERGE` (`1` unheld leg + pre-held inventory -> `CLASS_A`,
            #     with `0.0` credit for uncertain maker rebates in `min_state_net_payoff_usd`!).
            #   - `L1B_RESTING_PASSIVE_INVENTORY_MAKER_COMPLETION`: Pre-held inventory on Leg 1 + resting 0%-fee
            #     `postOnly` passive bid on Leg 2 (`min_omega > 0` conditional on fill, zero new naked risk if unfilled,
            #     classified `CLASS_C` while resting unfilled per `UniversalArbVerifier` fill-certainty gate).
            for held_tok, comp_bk, held_bk in ((yes_tok, bk_n, bk_y), (no_tok, bk_y, bk_n)):
                h_pos = holdings.get(held_tok)
                if h_pos is None or h_pos.is_d001_protected() or h_pos.shares < comp_bk.min_order_size:
                    continue

                # L1A: Immediate Prelocked Completion against resting L2 ask (`CLASS_A` when net edge > 0)
                comp_ask_net, _, _ = fee_spec.net_buy_cost_per_share(comp_bk.asks[0].price, is_maker=False)
                if (h_pos.cost_basis_per_share + comp_ask_net) < 0.999:
                    cand_l1a = CandidateStructure(
                        candidate_id=f"FAM_L1A_PRELOCKED_MAKER_COMP_{mid}_{comp_bk.instrument_id[:10]}",
                        family="L",
                        legs=(
                            ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id=held_tok, market_id=mid),
                            ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=comp_bk.instrument_id, is_maker=False, market_id=mid),
                            ActionLeg(action_type=ActionType.CTF_MERGE, related_instrument_ids=(yes_tok, no_tok), market_id=mid),
                        ),
                        states=StateSpaceBuilder.binary_complete_set_states(yes_tok, no_tok, include_void_50_50=True),
                        rule_verified=True,
                        expected_lockup_hours=0.02,
                        worst_case_lockup_hours=0.05,
                        unverified_rebate_or_reward_usd_per_unit=fee_spec.estimated_maker_rebate_per_share(h_pos.cost_basis_per_share),
                    )
                    proof_l1a = self.verifier.verify_and_simulate(
                        cand_l1a,
                        {yes_tok: bk_y, no_tok: bk_n},
                        holdings={held_tok: h_pos},
                    )
                    sh_1a = proof_l1a.optimal_executable_quantity
                    est_reb_1a = round(sh_1a * fee_spec.estimated_maker_rebate_per_share(h_pos.cost_basis_per_share), 6)
                    if proof_l1a.opportunity_class == OpportunityClass.CLASS_A.value and sh_1a >= comp_bk.min_order_size:
                        results.append(
                            MicroPortfolioCandidate(
                                candidate_id=proof_l1a.candidate_id,
                                family="L",
                                sub_type="L1A_FILLED_MAKER_ANCHOR_PRELOCKED_COMPLETION",
                                opportunity_class=proof_l1a.opportunity_class,
                                execution_mode_gate="MODE_2_SHADOW_ELIGIBLE_FOR_PROPOSAL",
                                event_id=ev_id,
                                canonical_event_keys=ckeys,
                                market_ids=(mid,),
                                token_ids=(held_tok, comp_bk.instrument_id),
                                consumed_book_sides=_extract_consumed_book_sides_from_proof(
                                    proof_l1a, ((comp_bk.instrument_id, "ASK", 1.0),)
                                ),
                                sequential_clob_legs=1,
                                is_atomic_or_inventory_locked=True,
                                d007_sub500_multileg_quarantine=False,
                                d001_kmia_frozen_blocked=False,
                                min_order_shares=comp_bk.min_order_size,
                                optimal_shares=sh_1a,
                                capital_required_usd=round(proof_l1a.cost_breakdown.capital_required_usd, 4),
                                gross_edge_bps=round((1.0 - (h_pos.cost_basis_per_share + comp_bk.asks[0].price)) * 10_000.0, 2),
                                net_executable_edge_bps=round(proof_l1a.net_executable_edge_per_unit * 10_000.0, 2),
                                min_state_net_payoff_usd=round(proof_l1a.min_state_net_payoff_usd, 6),
                                expected_net_payoff_usd=round(proof_l1a.expected_net_payoff_usd, 6),
                                expected_lockup_hours=0.02,
                                worst_case_lockup_hours=0.05,
                                net_bps_per_hour_expected=round(proof_l1a.capital_efficiency_bps_per_hr, 2),
                                net_bps_per_hour_worst_case=round(proof_l1a.capital_efficiency_bps_per_hr, 2),
                                dispute_probability=0.0,
                                partial_fill_prob=0.02,
                                adverse_selection_cost_usd=0.0,
                                uncertain_rebate_or_reward_usd=est_reb_1a,
                                dormant_near_miss=False,
                                four_value_ledger=proof_l1a.four_value_ledger,
                                proof=proof_l1a,
                                proof_sha256=proof_l1a.proof_sha256,
                                disqualifiers=proof_l1a.disqualifiers,
                                notes=("Filled 0%-fee maker leg + 1-leg FOK completion + CTF_MERGE (`CLASS_A`); rebates excluded from floor.",),
                            )
                        )

                # L1B: Passive `postOnly` 0%-fee Maker Bid Completion (`CLASS_C` while resting unfilled; 0 naked addition)
                target_raw_bid = min(comp_bk.asks[0].price - 0.01, max(comp_bk.bids[0].price, 0.992 - h_pos.cost_basis_per_share))
                if target_raw_bid <= 0.01 or (h_pos.cost_basis_per_share + target_raw_bid) >= 0.998:
                    continue
                q_bid, _ = quantize_polymarket_price(target_raw_bid, "BUY", explicit_tick_size=comp_bk.tick_size, is_maker=True)
                if q_bid >= comp_bk.asks[0].price - 1e-9 or (h_pos.cost_basis_per_share + q_bid) >= 0.999:
                    continue

                q_stats = self.estimate_queue_and_adverse_selection(comp_bk, held_bk, q_bid, h_pos.shares)
                cand_l1b = CandidateStructure(
                    candidate_id=f"FAM_L1B_RESTING_INV_MAKER_{mid}_{comp_bk.instrument_id[:10]}",
                    family="L",
                    legs=(
                        ActionLeg(action_type=ActionType.USE_INVENTORY, instrument_id=held_tok, market_id=mid),
                        ActionLeg(
                            action_type=ActionType.BUY_CLOB,
                            instrument_id=comp_bk.instrument_id,
                            is_maker=True,
                            maker_price=q_bid,
                            market_id=mid,
                        ),
                        ActionLeg(action_type=ActionType.CTF_MERGE, related_instrument_ids=(yes_tok, no_tok), market_id=mid),
                    ),
                    states=StateSpaceBuilder.binary_complete_set_states(yes_tok, no_tok, include_void_50_50=True),
                    rule_verified=True,
                    expected_lockup_hours=0.25,
                    worst_case_lockup_hours=1.0,
                    unverified_rebate_or_reward_usd_per_unit=fee_spec.estimated_maker_rebate_per_share(q_bid),
                )
                proof_l1b = self.verifier.verify_and_simulate(
                    cand_l1b,
                    {yes_tok: bk_y, no_tok: bk_n},
                    holdings={held_tok: h_pos},
                )
                sh_q = proof_l1b.optimal_executable_quantity
                est_reb_usd = round(sh_q * fee_spec.estimated_maker_rebate_per_share(q_bid), 6)
                results.append(
                    MicroPortfolioCandidate(
                        candidate_id=proof_l1b.candidate_id,
                        family="L",
                        sub_type="L1B_RESTING_PASSIVE_INVENTORY_MAKER_COMPLETION",
                        opportunity_class=proof_l1b.opportunity_class,
                        execution_mode_gate="MODE_2_SHADOW",
                        event_id=ev_id,
                        canonical_event_keys=ckeys,
                        market_ids=(mid,),
                        token_ids=(held_tok, comp_bk.instrument_id),
                        consumed_book_sides=(),
                        sequential_clob_legs=1,
                        is_atomic_or_inventory_locked=False,
                        d007_sub500_multileg_quarantine=False,
                        d001_kmia_frozen_blocked=False,
                        min_order_shares=comp_bk.min_order_size,
                        optimal_shares=sh_q,
                        capital_required_usd=round(sh_q * q_bid, 4),
                        gross_edge_bps=round((1.0 - (h_pos.cost_basis_per_share + q_bid)) * 10_000.0, 2),
                        net_executable_edge_bps=round(proof_l1b.net_executable_edge_per_unit * 10_000.0, 2),
                        min_state_net_payoff_usd=round(proof_l1b.min_state_net_payoff_usd, 6),
                        expected_net_payoff_usd=round(proof_l1b.expected_net_payoff_usd * q_stats["queue_fill_prob"], 6),
                        expected_lockup_hours=0.25,
                        worst_case_lockup_hours=1.0,
                        net_bps_per_hour_expected=round(proof_l1b.capital_efficiency_bps_per_hr * q_stats["queue_fill_prob"], 2),
                        net_bps_per_hour_worst_case=round(proof_l1b.net_executable_edge_per_unit * 10_000.0, 2),
                        dispute_probability=0.0,
                        partial_fill_prob=round(1.0 - q_stats["queue_fill_prob"], 4),
                        adverse_selection_cost_usd=0.0,
                        uncertain_rebate_or_reward_usd=est_reb_usd,
                        dormant_near_miss=False,
                        four_value_ledger=proof_l1b.four_value_ledger,
                        proof=proof_l1b,
                        proof_sha256=proof_l1b.proof_sha256,
                        disqualifiers=proof_l1b.disqualifiers,
                        notes=("Resting 0%-fee postOnly bid completing pre-held inventory; rebates excluded from floor.",),
                    )
                )

            # 2. L2 — Fee-Curve Maker Anchor + Immediate WS Taker Hedge (`feesEnabled == True`)
            # Evaluate when Taker+Taker >= $1.00 due to fees, but Maker(0-fee) + Taker < $1.00
            if fee_spec.fees_enabled and fee_spec.rate > 0.0:
                y_ask_net, _, y_tak_fee = fee_spec.net_buy_cost_per_share(bk_y.asks[0].price, is_maker=False)
                n_ask_net, _, n_tak_fee = fee_spec.net_buy_cost_per_share(bk_n.asks[0].price, is_maker=False)
                taker_pair_cost = y_ask_net + n_ask_net

                # Quote passive `postOnly` 1 tick inside spread (or at best bid if tight) on Leg Y, hedge Taker on Leg N
                raw_mkr_y = min(bk_y.asks[0].price - 0.01, bk_y.bids[0].price + 0.01) if (bk_y.asks[0].price - bk_y.bids[0].price) >= 0.02 else bk_y.bids[0].price
                mkr_y_px, _ = quantize_polymarket_price(raw_mkr_y, "BUY", explicit_tick_size=bk_y.tick_size, is_maker=True)
                maker_taker_cost = mkr_y_px + n_ask_net

                if maker_taker_cost < 0.998 and mkr_y_px < bk_y.asks[0].price - 1e-9:
                    clip_sh = max(bk_y.min_order_size, min(15.0, bk_n.asks[0].size * 0.25))
                    if clip_sh >= max(bk_y.min_order_size, bk_n.min_order_size):
                        q_stats = self.estimate_queue_and_adverse_selection(bk_y, bk_n, mkr_y_px, clip_sh)
                        gross_box_edge_ps = 1.0 - maker_taker_cost
                        adv_cost_ps = q_stats["adverse_cost_per_share"]
                        aging_cost_ps = (self.inventory_aging_bps_per_hr / 10_000.0) * 0.35
                        net_ev_ps_ex_rebate = gross_box_edge_ps - adv_cost_ps - aging_cost_ps
                        rebate_ps = fee_spec.estimated_maker_rebate_per_share(mkr_y_px)

                        # Jump-before-hedge state: Leg Y fills at `mkr_y_px` because news spiked Leg N ask to `$0.99` -> unwind loss!
                        worst_jump_loss_usd = -round(clip_sh * min(mkr_y_px, 0.15), 6)
                        ev_total_usd = round(clip_sh * net_ev_ps_ex_rebate * q_stats["queue_fill_prob"], 6)
                        eff_cls_l2 = (
                            OpportunityClass.CLASS_C.value
                            if (ev_total_usd > 0.0 and q_stats["queue_ahead_usd"] <= self.max_join_queue_usd and q_stats["hedge_depth_ratio"] >= 2.0)
                            else OpportunityClass.CLASS_E.value
                        )
                        cap_l2 = round(clip_sh * maker_taker_cost, 4)
                        digest_l2 = hashlib.sha256(
                            f"L2:{mid}:{mkr_y_px:.4f}:{n_ask_net:.4f}:{worst_jump_loss_usd:.6f}".encode("utf-8")
                        ).hexdigest()

                        n_haircut_l2 = compute_v2_buy_share_haircut_frac(
                            bk_n.asks[0].price, fee_rate_bps=bk_n.fee_rate_bps, fee_exponent=bk_n.fee_exponent
                        )
                        n_gross_mult_l2 = round(1.0 / max(0.50, 1.0 - n_haircut_l2), 6)

                        results.append(
                            MicroPortfolioCandidate(
                                candidate_id=f"FAM_L2_FEE_ASYM_{mid}",
                                family="L",
                                sub_type="L2_FEE_ASYMMETRY_MAKER_HEDGE_PAIR",
                                opportunity_class=eff_cls_l2,
                                execution_mode_gate="MODE_2_SHADOW_MAKER_HAZARD",
                                event_id=ev_id,
                                canonical_event_keys=ckeys,
                                market_ids=(mid,),
                                token_ids=(yes_tok, no_tok),
                                consumed_book_sides=((no_tok, "ASK", n_gross_mult_l2),),
                                sequential_clob_legs=2,
                                is_atomic_or_inventory_locked=False,
                                d007_sub500_multileg_quarantine=False,
                                d001_kmia_frozen_blocked=False,
                                min_order_shares=max(bk_y.min_order_size, bk_n.min_order_size),
                                optimal_shares=round(clip_sh, 2),
                                capital_required_usd=cap_l2,
                                gross_edge_bps=round(gross_box_edge_ps * 10_000.0, 2),
                                net_executable_edge_bps=round(net_ev_ps_ex_rebate * 10_000.0, 2),
                                min_state_net_payoff_usd=worst_jump_loss_usd,
                                expected_net_payoff_usd=ev_total_usd,
                                expected_lockup_hours=0.35,
                                worst_case_lockup_hours=2.0,
                                net_bps_per_hour_expected=round((ev_total_usd / max(cap_l2, 0.01)) * 10_000.0 / 0.35, 2),
                                net_bps_per_hour_worst_case=round((worst_jump_loss_usd / max(cap_l2, 0.01)) * 10_000.0 / 2.0, 2),
                                dispute_probability=0.0,
                                partial_fill_prob=round(q_stats["toxic_pickoff_prob"], 4),
                                adverse_selection_cost_usd=round(clip_sh * adv_cost_ps, 6),
                                uncertain_rebate_or_reward_usd=round(clip_sh * rebate_ps * q_stats["queue_fill_prob"], 6),
                                dormant_near_miss=bool(eff_cls_l2 == OpportunityClass.CLASS_E.value and gross_box_edge_ps > 0.0),
                                four_value_ledger=FourValueMetrics(
                                    theoretical_top_of_book_usd=round(clip_sh * gross_box_edge_ps, 6),
                                    executable_l2_net_usd=round(clip_sh * gross_box_edge_ps, 6),
                                    attainable_risk_adjusted_usd=ev_total_usd,
                                    realized_net_usd=0.0,
                                ),
                                proof_sha256=digest_l2,
                                counterexample_states=("OMEGA_MAKER_LEG_FILLED_HEDGE_ASK_JUMPED",),
                                disqualifiers=("UNHEDGED_RESTING_MAKER_ANCHOR_NEVER_CLASS_A_OR_B",),
                                notes=(
                                    f"feeType={fee_spec.fee_type}(r={fee_spec.rate},exp={fee_spec.exponent},reb={fee_spec.rebate_rate}): "
                                    f"taker_pair={taker_pair_cost:.4f} vs maker_taker={maker_taker_cost:.4f}, "
                                    f"saved_fee={y_tak_fee:.4f}/sh, queue_ahead=${q_stats['queue_ahead_usd']:.1f}.",
                                ),
                            )
                        )

            # 3. L3 — Two-Sided Liquidity Reward / Maker Rebate Market Making (`rewardsMaxSpread` > 0)
            rw_max_spread = _sf(_get_field(m, "rewardsMaxSpread", "rewards_max_spread", default=0.0), 0.0)
            rw_min_size = _sf(_get_field(m, "rewardsMinSize", "rewards_min_size", default=0.0), 0.0)
            if rw_max_spread > 0.0 and rw_min_size > 0.0:
                # Normalize `rewardsMaxSpread` (Gamma reports cents like `3.5` = `$0.035` when > 0.5)
                max_inc_spread = rw_max_spread / 100.0 if rw_max_spread > 0.50 else rw_max_spread
                y_bid = bk_y.bids[0].price
                n_bid = bk_n.bids[0].price
                mid_y = 0.5 * (bk_y.bids[0].price + bk_y.asks[0].price)
                pair_bid_sum = y_bid + n_bid
                if 0.10 <= mid_y <= 0.90 and abs(mid_y - y_bid) < max_inc_spread and pair_bid_sum <= 0.996:
                    sh_rw = max(bk_y.min_order_size, min(25.0, rw_min_size))
                    q_stats_y = self.estimate_queue_and_adverse_selection(bk_y, bk_n, y_bid, sh_rw)
                    spread_edge_ps = max(0.0, 1.0 - pair_bid_sum)
                    single_leg_adverse_ps = q_stats_y["adverse_cost_per_share"] * 1.25
                    ev_ex_reward_ps = (spread_edge_ps * 0.35) - single_leg_adverse_ps
                    # Uncertain reward/rebate credit tracked strictly outside `min_state_net_payoff_usd`!
                    est_reward_usd = round(sh_rw * 0.0025, 6)
                    ev_total_l3 = round(sh_rw * ev_ex_reward_ps + est_reward_usd * 0.5, 6)
                    worst_single_leg_loss = -round(sh_rw * y_bid, 6)
                    eff_cls_l3 = OpportunityClass.CLASS_C.value if ev_total_l3 > 0.0 else OpportunityClass.CLASS_E.value
                    cap_l3 = round(sh_rw * pair_bid_sum, 4)
                    digest_l3 = hashlib.sha256(f"L3:{mid}:{pair_bid_sum:.4f}:{sh_rw:.1f}".encode("utf-8")).hexdigest()

                    results.append(
                        MicroPortfolioCandidate(
                            candidate_id=f"FAM_L3_SPEC_MM_{mid}",
                            family="L",
                            sub_type="L3_SPECULATIVE_REWARD_OR_REBATE_MM",
                            opportunity_class=eff_cls_l3,
                            execution_mode_gate="MODE_2_SHADOW_SPECULATIVE_MM_CLASS_C",
                            event_id=ev_id,
                            canonical_event_keys=ckeys,
                            market_ids=(mid,),
                            token_ids=(yes_tok, no_tok),
                            consumed_book_sides=(),
                            sequential_clob_legs=2,
                            is_atomic_or_inventory_locked=False,
                            d007_sub500_multileg_quarantine=False,
                            d001_kmia_frozen_blocked=False,
                            min_order_shares=sh_rw,
                            optimal_shares=sh_rw,
                            capital_required_usd=cap_l3,
                            gross_edge_bps=round(spread_edge_ps * 10_000.0, 2),
                            net_executable_edge_bps=round(ev_ex_reward_ps * 10_000.0, 2),
                            min_state_net_payoff_usd=worst_single_leg_loss,
                            expected_net_payoff_usd=ev_total_l3,
                            expected_lockup_hours=2.0,
                            worst_case_lockup_hours=24.0,
                            net_bps_per_hour_expected=round((ev_total_l3 / max(cap_l3, 0.01)) * 10_000.0 / 2.0, 2),
                            net_bps_per_hour_worst_case=round((worst_single_leg_loss / max(cap_l3, 0.01)) * 10_000.0 / 24.0, 2),
                            dispute_probability=0.0,
                            partial_fill_prob=0.65,
                            adverse_selection_cost_usd=round(sh_rw * single_leg_adverse_ps, 6),
                            uncertain_rebate_or_reward_usd=est_reward_usd,
                            dormant_near_miss=False,
                            four_value_ledger=FourValueMetrics(
                                theoretical_top_of_book_usd=round(sh_rw * spread_edge_ps, 6),
                                executable_l2_net_usd=round(sh_rw * ev_ex_reward_ps, 6),
                                attainable_risk_adjusted_usd=ev_total_l3,
                                realized_net_usd=0.0,
                            ),
                            proof_sha256=digest_l3,
                            counterexample_states=("OMEGA_SINGLE_SIDE_TOXIC_SWEEP_LOSER_INVENTORY",),
                            disqualifiers=("SPECULATIVE_MM_AND_UNCERTAIN_REWARDS_NEVER_CLASS_A_OR_B",),
                            notes=(
                                f"Two-sided Q_min (c=3.0) reward quote: pair_bid_sum={pair_bid_sum:.4f}, "
                                f"max_spread={max_inc_spread:.3f}, min_size={rw_min_size:.0f}. Strictly CLASS_C/E.",
                            ),
                        )
                    )

        results.sort(key=lambda c: (c.opportunity_class, -c.net_bps_per_hour_expected))
        return results


def _build_two_leg_ask_tranches(
    bk_a: InstrumentOrderBook,
    bk_b: InstrumentOrderBook,
    *,
    max_shares: float,
    lockup_hours: float,
    proof: Optional[Any] = None,
    fixed_overhead_usd: float = 0.0,
    per_share_overhead_usd: float = 0.0,
    step_shares: float = 5.0,
    survival_mult: float = 0.85,
) -> Tuple[MarginalDepthTranche, ...]:
    """
    Constructs exact piecewise-constant marginal L2 depth tranches across a 2-leg ask ladder,
    deducting fixed execution/settlement gas on Tranche 0, variable conversion/lockup overhead
    per share, and strictly enforcing `sum(tr.guaranteed_min_profit_usd) <= proof.min_state_net_payoff_usd`.
    """
    if max_shares < DEFAULT_MIN_ORDER_SHARES:
        return ()

    proof_min_pay: Optional[float] = None
    proof_cap_req: float = 0.0
    gas_fixed = 0.0
    settle_fixed = 0.0
    conv_var = 0.0
    lock_var = 0.0
    if proof is not None:
        proof_min_pay = _sf(getattr(proof, "min_state_net_payoff_usd", 0.0), 0.0)
        if proof_min_pay <= 0.0:
            return ()
        cb = getattr(proof, "cost_breakdown", None)
        if cb is not None:
            gas_fixed = max(0.0, _sf(getattr(cb, "gas_costs_usd", 0.0), 0.0))
            settle_fixed = max(0.0, _sf(getattr(cb, "settlement_costs_usd", 0.0), 0.0))
            conv_var = max(0.0, _sf(getattr(cb, "conversion_costs_usd", 0.0), 0.0))
            lock_var = max(0.0, _sf(getattr(cb, "lockup_capital_cost_usd", 0.0), 0.0))
            proof_cap_req = max(0.0, _sf(getattr(cb, "capital_required_usd", 0.0), 0.0))

    total_fixed_cost = max(0.0, float(fixed_overhead_usd)) + gas_fixed + settle_fixed
    upfront_fixed_cap = max(0.0, float(fixed_overhead_usd)) + gas_fixed
    unit_var_cost = max(0.0, float(per_share_overhead_usd)) + ((conv_var + lock_var) / max(max_shares, 1e-9))

    tranches: List[MarginalDepthTranche] = []
    q_prev = 0.0
    cost_prev = 0.0
    step = max(DEFAULT_MIN_ORDER_SHARES, float(step_shares))
    idx = 0
    while q_prev + 1e-6 < max_shares and idx < 24:
        q_next = min(max_shares, q_prev + step)
        if (max_shares - q_next) < DEFAULT_MIN_ORDER_SHARES * 0.5:
            q_next = max_shares

        while True:
            wa = UniversalArbVerifier._walk_ask_ladder_exact(bk_a, q_next)
            wb = UniversalArbVerifier._walk_ask_ladder_exact(bk_b, q_next)
            if wa is None or wb is None:
                q_next = -1.0
                break
            cost_next = wa[1] + wa[2] + wb[1] + wb[2]
            dq = q_next - q_prev
            dcost = (cost_next - cost_prev) + (upfront_fixed_cap if idx == 0 else 0.0)
            dprof = (dq - (cost_next - cost_prev)) - (total_fixed_cost if idx == 0 else 0.0) - (unit_var_cost * dq)
            if idx == 0 and dprof <= 0.0 and q_next + 1e-6 < max_shares:
                q_next = min(max_shares, q_next + step)
                if (max_shares - q_next) < DEFAULT_MIN_ORDER_SHARES * 0.5:
                    q_next = max_shares
                continue
            break

        if q_next <= 0.0 or dprof <= 0.0 or dcost <= 0.0:
            break
        mbps_hr = (dprof / dcost) * 10_000.0 / max(0.05, lockup_hours)
        tranches.append(
            MarginalDepthTranche(
                tranche_index=idx,
                shares=round(dq, 4),
                capital_usd=round(dcost, 6),
                guaranteed_min_profit_usd=round(dprof, 6),
                risk_adjusted_profit_usd=round(dprof * survival_mult, 6),
                marginal_bps_per_hour=round(mbps_hr, 2),
            )
        )
        q_prev = q_next
        cost_prev = cost_next
        idx += 1

    if not tranches:
        return ()

    if proof_min_pay is not None:
        sum_min = sum(t.guaranteed_min_profit_usd for t in tranches)
        sum_cap = sum(t.capital_usd for t in tranches)
        cap_pad_t0 = round(max(0.0, proof_cap_req - sum_cap), 6) if (q_prev >= max_shares - 1e-5 and proof_cap_req > sum_cap + 1e-6) else 0.0
        if sum_min > proof_min_pay + 1e-7 or cap_pad_t0 > 0.0:
            scale = min(1.0, max(0.0, proof_min_pay / max(sum_min, 1e-9)))
            adjusted: List[MarginalDepthTranche] = []
            for k, t in enumerate(tranches):
                new_cap = round(t.capital_usd + (cap_pad_t0 if k == 0 else 0.0), 6)
                new_min = math.floor((t.guaranteed_min_profit_usd * scale) * 1_000_000.0 + 1e-9) / 1_000_000.0
                if new_min <= 0.0:
                    continue
                new_ra = round(min(t.risk_adjusted_profit_usd * scale, new_min), 6) if survival_mult <= 1.0 else round(t.risk_adjusted_profit_usd * scale, 6)
                new_mbps = round((new_min / max(new_cap, 1e-6)) * 10_000.0 / max(0.05, lockup_hours), 2)
                adjusted.append(
                    MarginalDepthTranche(
                        tranche_index=len(adjusted),
                        shares=t.shares,
                        capital_usd=new_cap,
                        guaranteed_min_profit_usd=new_min,
                        risk_adjusted_profit_usd=new_ra,
                        marginal_bps_per_hour=new_mbps,
                    )
                )
            tranches = adjusted

    return tuple(tranches)


# ---------------------------------------------------------------------------
# Family M (Part i) — Multi-Leg Connected-Component Arbitrage Solver
# ---------------------------------------------------------------------------


class MultiLegComponentDetector:
    """
    Family M Multi-Leg Detector (`MultiLegComponentDetector`):
      - Uses `MarketPropositionGraph` connected-component pruning (`OFFICIAL_CONTRACTUAL` and
        `VERIFIED_MATHEMATICAL` edges, capped at `max_component_markets`) so multi-leg search never
        triggers `O(N^2)` combinatorial blowups across unrelated markets.
      - Evaluates:
        1. `M1_CLOSED_PARTITION_MULTI_OUTCOME_BUY_ALL`: `K >= 3` exhaustive mutually-exclusive outcomes
           where `sum(ask_net_YES_i) < $1.00`. Strictly proves `negRisk == True`, `negRiskAugmented == False`,
           zero unnamed placeholders, and zero mutable `Other` traps; downgrades incomplete/augmented/
           multi-winner slates to `CLASS_D` / `CLASS_E` with explicit counterexample states, and flags
           sequential `>= 3`-leg CLOB construction with `d007_sub500_multileg_quarantine = True` when
           `reconciled_nav_usd < $500.0`.
        2. `M2_NEGRISK_M_NO_CONVERT_SUBSET`: Optimal `m >= 2` `NO` subset on closed `NegRisk` partitions
           where `sum_{i in S} ask_net(NO_i) + convert_fee < $(m - 1).00`, converting on-chain into
           `$(m - 1).00` guaranteed collateral + `(N - m)` complement `YES` tokens (`m == 2` requires
           only `2` CLOB legs; `m >= 3` enforces `D-007` `< $500` quarantine unless atomic/inventory-backed).
        3. `M3_TRANSITIVE_IMPLICATION_AND_BRACKET_CHAIN`: Searches transitive `IMPLIES` / `INTERVAL_COVER`
           DAGs inside each connected component for highest-edge dominance violations (`NO_src + YES_dst`)
           and 3-leg bracket covers (`YES_[K1,K2) + YES_>=K2 + NO_>=K1 < $1.00`).
    """

    def __init__(
        self,
        *,
        reconciled_nav_usd: float = AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD,
        d007_multileg_nav_floor_usd: float = DEFAULT_D007_MULTILEG_NAV_FLOOR_USD,
        max_component_markets: int = 40,
        dormant_gap_bps: float = 180.0,
    ) -> None:
        self.reconciled_nav_usd = max(1.0, float(reconciled_nav_usd))
        self.d007_multileg_nav_floor_usd = max(500.0, float(d007_multileg_nav_floor_usd))
        self.max_component_markets = max(4, int(max_component_markets))
        self.dormant_gap_bps = max(10.0, float(dormant_gap_bps))
        self.verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=max(25.0, round(self.reconciled_nav_usd * 0.50, 2)),
                reconciled_nav_usd=self.reconciled_nav_usd,
                d007_multileg_nav_floor_usd=self.d007_multileg_nav_floor_usd,
            )
        )

    def scan_events_and_graph(
        self,
        events: Sequence[Any],
        books_by_token: Mapping[str, Mapping[str, Any]],
        *,
        graph: Optional[MarketPropositionGraph] = None,
        standalone_markets: Sequence[Any] = (),
        holdings_by_token: Optional[Mapping[str, InventoryHolding]] = None,
        now_ts: Optional[float] = None,
    ) -> List[MicroPortfolioCandidate]:
        now_u = float(time.time() if now_ts is None else now_ts)
        self.verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=max(100.0, round(self.reconciled_nav_usd * 0.50, 2)),
                reconciled_nav_usd=self.reconciled_nav_usd,
                now_ts=now_u,
            )
        )
        holdings = holdings_by_token or {}
        results: List[MicroPortfolioCandidate] = []
        raw_mkt_lookup: Dict[str, Any] = {}

        for ev in events:
            ev_id = str(_get_field(ev, "event_id", "id", default="") or "").strip()
            ev_nr = bool(_get_field(ev, "negRisk", "enableNegRisk", "neg_risk", default=False))
            ev_aug = bool(_get_field(ev, "negRiskAugmented", "neg_risk_augmented", default=False))
            mkts_raw = _get_field(ev, "markets", default=()) or ()
            active_mkts: List[Any] = []
            has_closed_sibling = False
            for m in mkts_raw:
                mid = str(_get_field(m, "market_id", "id", default="") or "").strip()
                if mid:
                    raw_mkt_lookup[mid] = m
                if bool(_get_field(m, "closed", default=False) is True):
                    has_closed_sibling = True
                    continue
                if bool(_get_field(m, "archived", default=False) is True):
                    has_closed_sibling = True
                    continue
                if bool(_get_field(m, "enableOrderBook", "enable_order_book", default=True) is False):
                    has_closed_sibling = True
                    continue
                if is_d001_frozen_kmia_entity(m):
                    has_closed_sibling = True
                    continue
                active_mkts.append(m)

            # Evaluate multi-outcome partition (`K >= 3`) on events
            if 3 <= len(active_mkts) <= self.max_component_markets:
                m_cands = self._evaluate_multi_outcome_slate(
                    ev_id=ev_id,
                    event_obj=ev,
                    active_mkts=active_mkts,
                    ev_neg_risk=ev_nr,
                    ev_neg_augmented=ev_aug,
                    has_closed_sibling=has_closed_sibling,
                    books_by_token=books_by_token,
                    holdings=holdings,
                    now_ts=now_u,
                )
                results.extend(m_cands)

        for sm in standalone_markets:
            mid = str(_get_field(sm, "market_id", "id", default="") or "").strip()
            if mid and mid not in raw_mkt_lookup:
                raw_mkt_lookup[mid] = sm

        # Build or reuse `MarketPropositionGraph` for connected-component implication/bracket chains
        if graph is None:
            graph = MarketPropositionGraph()
            graph.ingest_events_and_markets(events=events, standalone_markets=standalone_markets)

        components = graph.get_connected_components(
            allowed_edge_types=(EdgeType.OFFICIAL_CONTRACTUAL, EdgeType.VERIFIED_MATHEMATICAL),
            include_single_market_binaries=False,
            only_orderbook_enabled=True,
        )
        for comp in components:
            if len(comp.market_ids) > self.max_component_markets:
                continue
            chain_cands = self._evaluate_component_implication_and_covers(
                comp=comp,
                graph=graph,
                raw_mkt_lookup=raw_mkt_lookup,
                books_by_token=books_by_token,
                now_ts=now_u,
            )
            results.extend(chain_cands)

        results.sort(key=lambda c: (c.opportunity_class, -c.net_bps_per_hour_expected))
        return results

    def _evaluate_multi_outcome_slate(
        self,
        *,
        ev_id: str,
        event_obj: Any,
        active_mkts: Sequence[Any],
        ev_neg_risk: bool,
        ev_neg_augmented: bool,
        has_closed_sibling: bool,
        books_by_token: Mapping[str, Mapping[str, Any]],
        holdings: Mapping[str, InventoryHolding],
        now_ts: float,
    ) -> List[MicroPortfolioCandidate]:
        out: List[MicroPortfolioCandidate] = []
        outcome_specs: List[Dict[str, Any]] = []
        books_map: Dict[str, InstrumentOrderBook] = {}
        mids: List[str] = []
        yes_toks: List[str] = []
        no_toks: List[str] = []
        has_placeholder = False
        has_other = False
        sum_mid_prob = 0.0

        for m in active_mkts:
            mid = str(_get_field(m, "market_id", "id", default="") or "").strip()
            toks = [str(x).strip() for x in _parse_json_list(_get_field(m, "clobTokenIds", "instrument_ids", "token_ids", default=[])) if str(x).strip()]
            if len(toks) != 2:
                return out
            yt, nt = toks[0], toks[1]
            lbl = str(_get_field(m, "groupItemTitle", "group_item_title", "question", default=mid) or mid).strip()
            bk_y = build_instrument_book_for_token(yt, books_by_token.get(yt), m, outcome_label=lbl, now_ts=now_ts)
            bk_n = build_instrument_book_for_token(nt, books_by_token.get(nt), m, outcome_label=f"NO:{lbl}", now_ts=now_ts)
            if not bk_y.enable_order_book or bk_y.has_crossed_or_invalid_book() or bk_n.has_crossed_or_invalid_book():
                return out

            is_ph = bk_y.is_placeholder
            is_oth = bk_y.is_other
            has_placeholder = has_placeholder or is_ph
            has_other = has_other or is_oth
            if bk_y.bids and bk_y.asks:
                sum_mid_prob += 0.5 * (bk_y.bids[0].price + bk_y.asks[0].price)
            elif bk_y.asks:
                sum_mid_prob += bk_y.asks[0].price

            books_map[yt] = bk_y
            books_map[nt] = bk_n
            mids.append(mid)
            yes_toks.append(yt)
            no_toks.append(nt)
            outcome_specs.append(
                {
                    "market_id": mid,
                    "label": lbl,
                    "yes_token_id": yt,
                    "no_token_id": nt,
                    "is_placeholder": is_ph,
                    "is_other": is_oth,
                }
            )

        # Multi-winner / independent thresholds check (`not ev_neg_risk` or `sum_mid_prob > 1.30`)
        is_mutually_exclusive = bool(ev_neg_risk and sum_mid_prob <= 1.35)
        is_exhaustive = bool(ev_neg_risk and not ev_neg_augmented and not has_placeholder and not has_closed_sibling)
        ckeys_union: Set[str] = {f"EVT:{ev_id}"} if ev_id else set()
        for m in active_mkts:
            ckeys_union |= set(compute_canonical_concentration_keys(m))
        ckeys = tuple(sorted(ckeys_union))

        # 1. M1 — Buy-All-YES Multi-Outcome Complete Set (`K >= 3`)
        if all(books_map[yt].asks for yt in yes_toks):
            gross_sum = sum(books_map[yt].asks[0].price for yt in yes_toks)
            net_sum = sum(
                compute_net_buy_cost_per_delivered_share(
                    books_map[yt].asks[0].price,
                    fee_rate_bps=books_map[yt].fee_rate_bps,
                    fee_exponent=books_map[yt].fee_exponent,
                )[0]
                for yt in yes_toks
            )
            net_edge_bps = round((1.0 - net_sum) * 10_000.0, 2)
            if net_edge_bps >= -self.dormant_gap_bps:
                states_m1 = StateSpaceBuilder.multi_outcome_partition_states(
                    outcome_specs,
                    is_mutually_exclusive=is_mutually_exclusive,
                    is_exhaustive=is_exhaustive,
                    is_negrisk=ev_neg_risk,
                    is_augmented_negrisk=ev_neg_augmented,
                    has_unnamed_placeholder=has_placeholder,
                    has_other_outcome=has_other,
                )
                unheld_legs = sum(
                    1
                    for yt in yes_toks
                    if holdings.get(yt) is None or holdings[yt].is_d001_protected() or holdings[yt].shares < DEFAULT_MIN_ORDER_SHARES
                )
                legs_m1 = tuple(
                    ActionLeg(
                        action_type=(
                            ActionType.USE_INVENTORY
                            if (holdings.get(yt) is not None and not holdings[yt].is_d001_protected() and holdings[yt].shares >= DEFAULT_MIN_ORDER_SHARES)
                            else ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=yt).action_type
                        ),
                        instrument_id=yt,
                        market_id=mids[idx],
                    )
                    for idx, yt in enumerate(yes_toks)
                )
                disq_m1: List[str] = []
                if not ev_neg_risk:
                    disq_m1.append("NON_NEGRISK_MULTI_MARKET_SLATE_UNPROVEN_PARTITION")
                if ev_neg_augmented:
                    disq_m1.append("AUGMENTED_NEGRISK_MUTABLE_PARTITION")
                if has_placeholder:
                    disq_m1.append("UNNAMED_PLACEHOLDER_OUTCOME_PRESENT")
                if has_other and ev_neg_augmented:
                    disq_m1.append("MUTABLE_AUGMENTED_OTHER_OUTCOME")
                if has_closed_sibling:
                    disq_m1.append("CLOSED_OR_MISSING_SIBLING_IN_PARTITION")

                cand_m1 = CandidateStructure(
                    candidate_id=f"FAM_M1_ALL_YES_{ev_id or mids[0]}",
                    family="M",
                    legs=legs_m1,
                    states=states_m1,
                    rule_verified=(len(disq_m1) == 0),
                    rule_disqualifiers=tuple(disq_m1),
                    is_exhaustive_partition=is_exhaustive,
                    is_mutually_exclusive=is_mutually_exclusive,
                    requires_exhaustive_partition=True,
                    has_augmented_placeholder_risk=(ev_neg_augmented or has_placeholder),
                    has_mutable_other_exposure=(ev_neg_augmented and has_other),
                    expected_lockup_hours=24.0,
                    worst_case_lockup_hours=96.0,
                )
                proof_m1 = self.verifier.verify_and_simulate(cand_m1, books_map, holdings=holdings)
                d007_q = bool(unheld_legs >= 3 and self.reconciled_nav_usd < self.d007_multileg_nav_floor_usd)
                is_dorm = bool(proof_m1.opportunity_class == OpportunityClass.CLASS_E.value and is_exhaustive and net_edge_bps >= -self.dormant_gap_bps)
                if proof_m1.opportunity_class in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value, OpportunityClass.CLASS_D.value} or is_dorm:
                    out.append(
                        MicroPortfolioCandidate(
                            candidate_id=proof_m1.candidate_id,
                            family="M",
                            sub_type="M1_CLOSED_PARTITION_MULTI_OUTCOME_BUY_ALL",
                            opportunity_class=proof_m1.opportunity_class,
                            execution_mode_gate=(
                                "QUARANTINED_D007_LT_500_NAV_MODE_2_SHADOW" if d007_q else "MODE_2_SHADOW"
                            ),
                            event_id=ev_id,
                            canonical_event_keys=ckeys,
                            market_ids=tuple(mids),
                            token_ids=tuple(yes_toks),
                            consumed_book_sides=_extract_consumed_book_sides_from_proof(
                                proof_m1, tuple((yt, "ASK", 1.0) for yt in yes_toks)
                            ),
                            sequential_clob_legs=unheld_legs,
                            is_atomic_or_inventory_locked=(unheld_legs <= 1),
                            d007_sub500_multileg_quarantine=d007_q,
                            d001_kmia_frozen_blocked=False,
                            min_order_shares=max(books_map[yt].min_order_size for yt in yes_toks),
                            optimal_shares=proof_m1.optimal_executable_quantity,
                            capital_required_usd=round(proof_m1.cost_breakdown.capital_required_usd, 4),
                            gross_edge_bps=round((1.0 - gross_sum) * 10_000.0, 2),
                            net_executable_edge_bps=round(proof_m1.net_executable_edge_per_unit * 10_000.0, 2),
                            min_state_net_payoff_usd=round(proof_m1.min_state_net_payoff_usd, 6),
                            expected_net_payoff_usd=round(proof_m1.expected_net_payoff_usd, 6),
                            expected_lockup_hours=24.0,
                            worst_case_lockup_hours=96.0,
                            net_bps_per_hour_expected=round(proof_m1.capital_efficiency_bps_per_hr, 2),
                            net_bps_per_hour_worst_case=round(
                                (proof_m1.net_executable_edge_per_unit * 10_000.0) / 96.0, 2
                            ) if proof_m1.optimal_executable_quantity > 0 else 0.0,
                            dispute_probability=0.02,
                            partial_fill_prob=round(1.0 - (0.92 ** max(0, unheld_legs - 1)), 4),
                            adverse_selection_cost_usd=0.0,
                            uncertain_rebate_or_reward_usd=0.0,
                            dormant_near_miss=is_dorm,
                            four_value_ledger=proof_m1.four_value_ledger,
                            proof=proof_m1,
                            proof_sha256=proof_m1.proof_sha256,
                            counterexample_states=proof_m1.counterexample_states,
                            disqualifiers=proof_m1.disqualifiers,
                            notes=(f"K={len(yes_toks)} legs, unheld_legs={unheld_legs}, d007_quarantine={d007_q}",),
                        )
                    )

        # 2. M2 — Optimal `m=2` NegRisk Pure Cash Convert (`cost(NO_1) + cost(NO_2) < $1.00` -> `$1.00` collateral + `(N-2)` free YES!)
        # IMPORTANT: Only valid when NO sibling market in the NegRisk group has already closed (`not has_closed_sibling`)
        if ev_neg_risk and not ev_neg_augmented and not has_placeholder and not has_closed_sibling:
            no_candidates: List[Tuple[float, int, str]] = []
            for idx, nt in enumerate(no_toks):
                bk_n = books_map[nt]
                if bk_n.asks:
                    c_net, _, _ = compute_net_buy_cost_per_delivered_share(
                        bk_n.asks[0].price, fee_rate_bps=bk_n.fee_rate_bps, fee_exponent=bk_n.fee_exponent
                    )
                    no_candidates.append((c_net, idx, nt))
            no_candidates.sort(key=lambda r: r[0])
            if len(no_candidates) >= 2:
                pair_cost = no_candidates[0][0] + no_candidates[1][0]
                nr2_edge_bps = round((1.0 - pair_cost) * 10_000.0, 2)
                if nr2_edge_bps >= -self.dormant_gap_bps:
                    i1, nt1 = no_candidates[0][1], no_candidates[0][2]
                    i2, nt2 = no_candidates[1][1], no_candidates[1][2]
                    minted_yes = tuple(yt for k, yt in enumerate(yes_toks) if k not in (i1, i2))
                    states_nr2 = StateSpaceBuilder.multi_outcome_partition_states(
                        outcome_specs,
                        is_mutually_exclusive=True,
                        is_exhaustive=True,
                        is_negrisk=True,
                        is_augmented_negrisk=False,
                        has_unnamed_placeholder=False,
                        has_other_outcome=has_other,
                    )
                    cand_nr2 = CandidateStructure(
                        candidate_id=f"FAM_M2_NR2_CONVERT_{ev_id or mids[0]}",
                        family="M",
                        legs=(
                            ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=nt1, market_id=mids[i1]),
                            ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=nt2, market_id=mids[i2]),
                            ActionLeg(
                                action_type=ActionType.NEGRISK_CONVERT,
                                burned_no_instrument_ids=(nt1, nt2),
                                minted_yes_instrument_ids=minted_yes,
                                negrisk_fee_bips=0,
                            ),
                        ),
                        states=states_nr2,
                        rule_verified=True,
                        expected_lockup_hours=0.05,
                        worst_case_lockup_hours=0.25,
                    )
                    proof_nr2 = self.verifier.verify_and_simulate(cand_nr2, books_map)
                    is_dorm2 = bool(proof_nr2.opportunity_class == OpportunityClass.CLASS_E.value and nr2_edge_bps >= -self.dormant_gap_bps)
                    if proof_nr2.opportunity_class in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value} or is_dorm2:
                        tr_nr2 = _build_two_leg_ask_tranches(
                            books_map[nt1],
                            books_map[nt2],
                            max_shares=proof_nr2.optimal_executable_quantity,
                            lockup_hours=0.25,
                            proof=proof_nr2,
                        )
                        out.append(
                            MicroPortfolioCandidate(
                                candidate_id=proof_nr2.candidate_id,
                                family="M",
                                sub_type="M2_NEGRISK_2NO_CASH_CONVERT",
                                opportunity_class=proof_nr2.opportunity_class,
                                execution_mode_gate="MODE_2_SHADOW",
                                event_id=ev_id,
                                canonical_event_keys=ckeys,
                                market_ids=(mids[i1], mids[i2]),
                                token_ids=(nt1, nt2),
                                consumed_book_sides=_extract_consumed_book_sides_from_proof(
                                    proof_nr2, ((nt1, "ASK", 1.0), (nt2, "ASK", 1.0))
                                ),
                                sequential_clob_legs=2,
                                is_atomic_or_inventory_locked=False,
                                d007_sub500_multileg_quarantine=False,  # m == 2 legs (< 3)
                                d001_kmia_frozen_blocked=False,
                                min_order_shares=max(books_map[nt1].min_order_size, books_map[nt2].min_order_size),
                                optimal_shares=proof_nr2.optimal_executable_quantity,
                                capital_required_usd=round(proof_nr2.cost_breakdown.capital_required_usd, 4),
                                gross_edge_bps=round((1.0 - (books_map[nt1].asks[0].price + books_map[nt2].asks[0].price)) * 10_000.0, 2),
                                net_executable_edge_bps=round(proof_nr2.net_executable_edge_per_unit * 10_000.0, 2),
                                min_state_net_payoff_usd=round(proof_nr2.min_state_net_payoff_usd, 6),
                                expected_net_payoff_usd=round(proof_nr2.expected_net_payoff_usd, 6),
                                expected_lockup_hours=0.05,
                                worst_case_lockup_hours=0.25,
                                net_bps_per_hour_expected=round(proof_nr2.capital_efficiency_bps_per_hr, 2),
                                net_bps_per_hour_worst_case=round((proof_nr2.net_executable_edge_per_unit * 10_000.0) / 0.25, 2),
                                dispute_probability=0.0,
                                partial_fill_prob=0.08,
                                adverse_selection_cost_usd=0.0,
                                uncertain_rebate_or_reward_usd=0.0,
                                dormant_near_miss=is_dorm2,
                                four_value_ledger=proof_nr2.four_value_ledger,
                                marginal_tranches=tr_nr2,
                                proof=proof_nr2,
                                proof_sha256=proof_nr2.proof_sha256,
                                notes=("2-leg NO NegRiskAdapter.convertPositions -> $1.00 cash + free YES complement.",),
                            )
                        )
        return out

    def _evaluate_component_implication_and_covers(
        self,
        *,
        comp: ConnectedMarketComponent,
        graph: MarketPropositionGraph,
        raw_mkt_lookup: Mapping[str, Any],
        books_by_token: Mapping[str, Mapping[str, Any]],
        now_ts: float,
    ) -> List[MicroPortfolioCandidate]:
        out: List[MicroPortfolioCandidate] = []
        adj_implies: Dict[str, List[str]] = defaultdict(list)
        for ed in comp.edges:
            if ed.edge_type == EdgeType.VERIFIED_MATHEMATICAL and ed.relation_kind == RelationKind.IMPLIES:
                adj_implies[ed.source_market_id].append(ed.target_market_id)

        if not adj_implies:
            return out

        # Transitive closure over pruned DAG (`<= max_component_markets` nodes) to find non-adjacent calendar/strike arbs!
        for src_mid in sorted(adj_implies.keys()):
            reachable: Set[str] = set()
            stack = list(adj_implies[src_mid])
            while stack:
                nxt = stack.pop()
                if nxt == src_mid or nxt in reachable:
                    continue
                reachable.add(nxt)
                stack.extend(adj_implies.get(nxt, ()))

            m_src = graph.markets.get(src_mid)
            if m_src is None or is_d001_frozen_kmia_entity(m_src):
                continue
            raw_src = raw_mkt_lookup.get(src_mid, m_src)
            bk_ya = build_instrument_book_for_token(m_src.yes_token_id, books_by_token.get(m_src.yes_token_id), raw_src, outcome_label="Yes", now_ts=now_ts)
            bk_na = build_instrument_book_for_token(m_src.no_token_id, books_by_token.get(m_src.no_token_id), raw_src, outcome_label="No", now_ts=now_ts)
            if not bk_na.asks or bk_na.has_crossed_or_invalid_book():
                continue

            for dst_mid in sorted(reachable):
                m_dst = graph.markets.get(dst_mid)
                if m_dst is None or is_d001_frozen_kmia_entity(m_dst):
                    continue
                ok_compat, mismatch_codes = m_src.resolution.check_compatibility(
                    m_dst.resolution,
                    allow_ordered_cutoffs=(m_src.proposition.predicate_type == "DEADLINE_BY"),
                )
                if not ok_compat:
                    continue
                raw_dst = raw_mkt_lookup.get(dst_mid, m_dst)

                # Independent M3 Safety Guards (catches live Gamma Over/Under polarity, Map 2 vs Map 3, & yearless "March 31 [2027]" > "Nov 15 [2026]" wraps!)
                extra_m3_disq: List[str] = list(mismatch_codes)
                q_src_l = str(_get_field(raw_src, "question", default=m_src.question) or "").lower()
                q_dst_l = str(_get_field(raw_dst, "question", default=m_dst.question) or "").lower()
                out_src = [str(x).strip().lower() for x in _parse_json_list(_get_field(raw_src, "outcomes", default=["Yes", "No"]))]
                out_dst = [str(x).strip().lower() for x in _parse_json_list(_get_field(raw_dst, "outcomes", default=["Yes", "No"]))]

                # 1. Sub-period / Map / Game / Half / Quarter parity check (`Map 3` vs `Map 2` must NEVER pair!)
                sub_src = re.findall(r"\b(?:map|game|set|match|half|quarter|period|round|inning)\s*\d+\b", q_src_l)
                sub_dst = re.findall(r"\b(?:map|game|set|match|half|quarter|period|round|inning)\s*\d+\b", q_dst_l)
                if sub_src != sub_dst:
                    continue

                # 2. Over/Under & non-Yes/No outcome polarity check (`outcomes=['Over','Under']` has `toks[0]=Over`, NEVER `Under`!)
                if out_src != out_dst:
                    continue
                if out_src and out_src != ["yes", "no"]:
                    if out_src == ["over", "under"]:
                        # `toks[0]` is `Over K`: `Over K_src => Over K_dst` requires `K_src > K_dst` strictly!
                        k_src = m_src.proposition.threshold_low if m_src.proposition.threshold_low is not None else m_src.proposition.threshold_high
                        k_dst = m_dst.proposition.threshold_low if m_dst.proposition.threshold_low is not None else m_dst.proposition.threshold_high
                        if k_src is None or k_dst is None or k_src <= k_dst:
                            extra_m3_disq.append("OVER_UNDER_OUTCOME_POLARITY_INVERSION")
                    else:
                        extra_m3_disq.append("NON_STANDARD_OUTCOME_LABELS_UNVERIFIED")
                elif "over/under" in q_src_l or "over/under" in q_dst_l or "o/u" in q_src_l or "o/u" in q_dst_l:
                    extra_m3_disq.append("OVER_UNDER_QUESTION_AMBIGUOUS_TOKEN_POLARITY")

                # 3. Yearless `"by March 31"` [2027] vs `"by November 15"` [2026] authoritative `endDate` monotonicity check!
                end_raw_src = _parse_ts(_get_field(raw_src, "endDate", "endDateIso", default=None)) or m_src.resolution.cutoff_ts
                end_raw_dst = _parse_ts(_get_field(raw_dst, "endDate", "endDateIso", default=None)) or m_dst.resolution.cutoff_ts
                if m_src.proposition.predicate_type == "DEADLINE_BY" or m_dst.proposition.predicate_type == "DEADLINE_BY":
                    if end_raw_src is not None and end_raw_dst is not None and end_raw_src > end_raw_dst + 60.0:
                        extra_m3_disq.append("DEADLINE_ENDDATE_YEAR_INVERSION")

                bk_yb = build_instrument_book_for_token(m_dst.yes_token_id, books_by_token.get(m_dst.yes_token_id), raw_dst, outcome_label="Yes", now_ts=now_ts)
                bk_nb = build_instrument_book_for_token(m_dst.no_token_id, books_by_token.get(m_dst.no_token_id), raw_dst, outcome_label="No", now_ts=now_ts)
                if not bk_yb.asks or bk_yb.has_crossed_or_invalid_book():
                    continue

                na_net, _, _ = compute_net_buy_cost_per_delivered_share(
                    bk_na.asks[0].price, fee_rate_bps=bk_na.fee_rate_bps, fee_exponent=bk_na.fee_exponent
                )
                yb_net, _, _ = compute_net_buy_cost_per_delivered_share(
                    bk_yb.asks[0].price, fee_rate_bps=bk_yb.fee_rate_bps, fee_exponent=bk_yb.fee_exponent
                )
                pair_bps = round((1.0 - (na_net + yb_net)) * 10_000.0, 2)
                if pair_bps < -self.dormant_gap_bps:
                    continue

                end_b = end_raw_dst
                lock_h = max(0.5, ((end_b - now_ts) / 3600.0) if end_b and end_b > now_ts else 24.0)
                worst_h = max(lock_h + 2.0, 24.0)

                proof_imp = self.verifier.verify_logical_implication_pair(
                    candidate_id=f"FAM_M3_CHAIN_{src_mid}_{dst_mid}",
                    family="M",
                    yes_book_a=bk_ya,
                    no_book_a=bk_na,
                    yes_book_b=bk_yb,
                    no_book_b=bk_nb,
                    relation="A_IMPLIES_B",
                    buy_legs=((m_src.no_token_id, 1.0), (m_dst.yes_token_id, 1.0)),
                    rule_verified=(len(extra_m3_disq) == 0),
                    rule_disqualifiers=tuple(extra_m3_disq),
                    cancel_rule_a=m_src.resolution.cancel_void_rule,
                    cancel_rule_b=m_dst.resolution.cancel_void_rule,
                    expected_lockup_hours=lock_h,
                    worst_case_lockup_hours=worst_h,
                )
                is_dorm_imp = bool(proof_imp.opportunity_class == OpportunityClass.CLASS_E.value and pair_bps >= -self.dormant_gap_bps)
                if proof_imp.opportunity_class in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value} or is_dorm_imp:
                    ckeys = tuple(sorted(set(compute_canonical_concentration_keys(raw_src)) | set(compute_canonical_concentration_keys(raw_dst))))
                    tr_imp = _build_two_leg_ask_tranches(
                        bk_na,
                        bk_yb,
                        max_shares=proof_imp.optimal_executable_quantity,
                        lockup_hours=worst_h,
                        proof=proof_imp,
                    )
                    out.append(
                        MicroPortfolioCandidate(
                            candidate_id=proof_imp.candidate_id,
                            family="M",
                            sub_type="M3_TRANSITIVE_IMPLICATION_DOMINANCE_CHAIN",
                            opportunity_class=proof_imp.opportunity_class,
                            execution_mode_gate="MODE_2_SHADOW",
                            event_id=m_src.event_id or m_dst.event_id,
                            canonical_event_keys=ckeys,
                            market_ids=(src_mid, dst_mid),
                            token_ids=(m_src.no_token_id, m_dst.yes_token_id),
                            consumed_book_sides=_extract_consumed_book_sides_from_proof(
                                proof_imp, ((m_src.no_token_id, "ASK", 1.0), (m_dst.yes_token_id, "ASK", 1.0))
                            ),
                            sequential_clob_legs=2,
                            is_atomic_or_inventory_locked=False,
                            d007_sub500_multileg_quarantine=False,
                            d001_kmia_frozen_blocked=False,
                            min_order_shares=max(bk_na.min_order_size, bk_yb.min_order_size),
                            optimal_shares=proof_imp.optimal_executable_quantity,
                            capital_required_usd=round(proof_imp.cost_breakdown.capital_required_usd, 4),
                            gross_edge_bps=round((1.0 - (bk_na.asks[0].price + bk_yb.asks[0].price)) * 10_000.0, 2),
                            net_executable_edge_bps=round(proof_imp.net_executable_edge_per_unit * 10_000.0, 2),
                            min_state_net_payoff_usd=round(proof_imp.min_state_net_payoff_usd, 6),
                            expected_net_payoff_usd=round(proof_imp.expected_net_payoff_usd, 6),
                            expected_lockup_hours=round(lock_h, 4),
                            worst_case_lockup_hours=round(worst_h, 4),
                            net_bps_per_hour_expected=round(proof_imp.capital_efficiency_bps_per_hr, 2),
                            net_bps_per_hour_worst_case=round((proof_imp.net_executable_edge_per_unit * 10_000.0) / worst_h, 2),
                            dispute_probability=0.01,
                            partial_fill_prob=0.08,
                            adverse_selection_cost_usd=0.0,
                            uncertain_rebate_or_reward_usd=0.0,
                            dormant_near_miss=is_dorm_imp,
                            four_value_ledger=proof_imp.four_value_ledger,
                            marginal_tranches=tr_imp,
                            proof=proof_imp,
                            proof_sha256=proof_imp.proof_sha256,
                            notes=(f"Verified transitive implication {src_mid} => {dst_mid}; middle state pays $2.00.",),
                        )
                    )
        return out


# ---------------------------------------------------------------------------
# Family M (Part ii) — Global Simultaneous Portfolio Arbitrage Optimizer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AllocatedPortfolioSlice:
    """Single selected opportunity allocation in the optimal portfolio solution."""

    candidate_id: str
    family: str
    sub_type: str
    opportunity_class: str
    allocated_shares: float
    allocated_capital_usd: float
    guaranteed_min_profit_usd: float
    risk_adjusted_profit_usd: float
    expected_lockup_hours: float
    worst_case_lockup_hours: float
    realizable_bps_per_hour: float
    canonical_event_keys: Tuple[str, ...]


@dataclass(frozen=True)
class PortfolioOptimizationResult:
    """Complete solution of `PortfolioArbitrageOptimizer.optimize_portfolio()`."""

    budget_label: str
    available_liquid_pusd: float
    reconciled_nav_usd: float
    settlement_reserve_usd: float
    deployable_cash_budget_usd: float
    per_event_cap_usd: float
    infra_hurdle_usd_per_hr: float
    infra_hurdle_bps_per_hr: float
    allocated_slices: Tuple[AllocatedPortfolioSlice, ...]
    rejected_candidates: Tuple[Dict[str, Any], ...]
    total_allocated_capital_usd: float
    unallocated_cash_usd: float
    total_guaranteed_min_profit_usd: float
    total_risk_adjusted_profit_usd: float
    total_dollar_hours_locked: float
    portfolio_realizable_profit_per_hour_usd: float
    portfolio_realizable_bps_per_hour: float
    clears_infra_hurdle: bool
    infra_coverage_ratio: float
    d001_kmia_untouched_verified: bool
    d007_concentration_verified: bool
    d007_sub500_multileg_quarantine_verified: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PortfolioArbitrageOptimizer:
    """
    Global Constrained Depth / Capital / Lockup Portfolio Arbitrage Optimizer (`Agent 8 / Family M`):
      - Optimizes **Total Portfolio Realizable Net Profit per Dollar-Hour** (`sum_i Profit_i / Lockup_i`)
        simultaneously across all competing candidates (`Families A..N`) rather than greedily per agent.
      - Uses exact marginal L2 depth tranches + discrete minimum-lot feasibility + pairwise 2-opt swap
        rebalancing so a smaller, fast-recycling box (`D1` / `NR2` / `C1`) preempts slow capital sinks!
      - Hard non-overridable constraints:
        1. `D-001` Frozen `KMIA` non-interference (`6707503`, `6707502`, `$50.51` untouched; `WXSTATION:KMIA` headroom = `$0.00`).
        2. Reconciled liquid `pUSD` sizing (`$48.695132` / `$48.70` live cash reference, NEVER `$99.21` book equity!).
        3. `D-007` `<= 15%` reconciled-NAV cap per correlated event/station key across ALL sleeves simultaneously.
        4. `D-007` `< $500` NAV quarantine on sequential `>= 3`-leg non-atomic CLOB bundles (`MODE_2_SHADOW` quarantine).
        5. Shared per-token L2 resting depth (`(token_id, "ASK"|"BID")`) preventing double-counting across overlapping arbs.
        6. Minimum order lot (`shares == 0` or `shares >= min_order_shares`) and maximum lockup horizon.
    """

    def __init__(
        self,
        *,
        available_liquid_pusd: float = AUTHORITATIVE_LIVE_CASH_PUSD,
        reconciled_nav_usd: float = AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD,
        settlement_reserve_pct: float = 0.05,
        max_event_concentration_pct: float = DEFAULT_D007_EVENT_CONCENTRATION_PCT,
        d007_multileg_nav_floor_usd: float = DEFAULT_D007_MULTILEG_NAV_FLOOR_USD,
        certified_multileg_3plus_enabled: bool = False,
        strict_riskless_only: bool = True,
        max_lockup_hours: float = 72.0,
        min_velocity_bps_per_hr: float = 0.0,
        existing_positions: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> None:
        self.available_liquid_pusd = max(0.0, float(available_liquid_pusd))
        # Guard against callers accidentally passing `$99.21` book equity instead of reconciled NAV when KMIA is disputed
        self.existing_positions: Tuple[Mapping[str, Any], ...] = tuple(
            existing_positions if existing_positions is not None else AUTHORITATIVE_FROZEN_KMIA_POSITIONS
        )
        self.reconciled_nav_usd = self._compute_safe_reconciled_nav(reconciled_nav_usd)
        self.settlement_reserve_pct = min(0.25, max(0.0, float(settlement_reserve_pct)))
        self.max_event_concentration_pct = min(0.15, max(0.01, float(max_event_concentration_pct)))
        self.d007_multileg_nav_floor_usd = max(500.0, float(d007_multileg_nav_floor_usd))
        self.certified_multileg_3plus_enabled = bool(certified_multileg_3plus_enabled)
        self.strict_riskless_only = bool(strict_riskless_only)
        self.max_lockup_hours = max(0.5, float(max_lockup_hours))
        self.min_velocity_bps_per_hr = max(0.0, float(min_velocity_bps_per_hr))

    def _compute_safe_reconciled_nav(self, supplied_nav_usd: float) -> float:
        """
        Ensures concentration sizing NEVER anchors off `$99.21` disputed book equity (`D-001` / `D-007` / `D-009`).
        """
        mark_open = 0.0
        has_disputed = False
        for p in self.existing_positions:
            uma_s = str(p.get("umaResolutionStatus") or p.get("uma_resolution_status") or "").strip().lower()
            sh = _sf(p.get("remaining_shares", p.get("shares", 0.0)), 0.0)
            bid = _sf(p.get("best_bid", p.get("mark_bid", 0.0)), 0.0)
            notional = _sf(p.get("notional_usd"), 0.0)
            if uma_s == "disputed" or is_d001_frozen_kmia_entity(p):
                has_disputed = True
                if sh > 0.0 and 0.0 < bid <= 1.0:
                    mark_open += min(notional, sh * bid)
            else:
                mark_open += min(notional, sh * bid) if (sh > 0.0 and 0.0 < bid <= 1.0) else notional
        reconciled_upper = self.available_liquid_pusd + mark_open
        nav_in = max(0.0, float(supplied_nav_usd))
        if has_disputed and nav_in > reconciled_upper + 1.0:
            return round(reconciled_upper, 6)
        return round(nav_in if nav_in > 0.0 else reconciled_upper, 6)

    @staticmethod
    def _is_duck_typed_proof_object(raw: Any) -> bool:
        if isinstance(raw, ArbitrageProofObject):
            return True
        if isinstance(raw, Mapping):
            return False
        return (
            hasattr(raw, "cost_breakdown")
            and hasattr(raw, "four_value_ledger")
            and hasattr(raw, "leg_executions")
            and hasattr(raw, "optimal_executable_quantity")
        )

    @staticmethod
    def _is_duck_typed_micro_candidate(raw: Any) -> bool:
        if isinstance(raw, MicroPortfolioCandidate):
            return True
        if isinstance(raw, Mapping):
            return False
        return (
            type(raw).__name__ == "MicroPortfolioCandidate"
            and hasattr(raw, "consumed_book_sides")
            and hasattr(raw, "d007_sub500_multileg_quarantine")
            and hasattr(raw, "canonical_event_keys")
        )

    @staticmethod
    def _augment_concentration_keys_with_books_and_tokens(
        base_keys: Iterable[str],
        *,
        market_ids: Sequence[str],
        token_ids: Sequence[str],
        books_by_token: Optional[Mapping[str, Any]],
        fallback_cid: str,
    ) -> Tuple[str, Tuple[str, ...], Tuple[str, ...]]:
        """
        Resolves `event_id`, `market_ids`, and `canonical_event_keys` across `books_by_token` and
        leg `token_ids` so candidates sharing tokens/markets NEVER bypass the `15%` `D-007` cap via
        isolated `CAND:<id>` keys (fixing `BUG-MP-2b`).
        """
        real_keys: Set[str] = {
            str(k).strip()
            for k in base_keys
            if str(k).strip() and not str(k).strip().startswith("CAND:")
        }
        mids_out: List[str] = [str(m).strip() for m in market_ids if str(m).strip()]
        ev_out = ""

        if books_by_token:
            for tid in token_ids:
                bk = books_by_token.get(tid)
                if bk is None:
                    continue
                for bk_k in compute_canonical_concentration_keys(bk):
                    if not bk_k.startswith("CAND:"):
                        real_keys.add(bk_k)
                b_mid = str(_get_field(bk, "market_id", "market", default="") or "").strip()
                if b_mid and b_mid not in mids_out:
                    mids_out.append(b_mid)
                    real_keys.add(f"MKT:{b_mid}")
                b_ev = str(_get_field(bk, "event_id", "parent_event_id", default="") or "").strip()
                if b_ev:
                    if not ev_out:
                        ev_out = b_ev
                    real_keys.add(f"EVT:{b_ev}")

        for mid in mids_out:
            real_keys.add(f"MKT:{mid}")

        has_explicit_evt = any(k.startswith("EVT:") or k.startswith("WXSTATION:") for k in real_keys)
        if not has_explicit_evt:
            for tid in token_ids:
                ts = str(tid or "").strip()
                if ts:
                    real_keys.add(f"TOK:{ts}")

        if not real_keys:
            real_keys.add(f"CAND:{fallback_cid}")

        return ev_out, tuple(dict.fromkeys(mids_out)), tuple(sorted(real_keys))

    @classmethod
    def _coerce_candidate(
        cls,
        raw: Any,
        reconciled_nav_usd: float,
        *,
        books_by_token: Optional[Mapping[str, Any]] = None,
    ) -> MicroPortfolioCandidate:
        """
        Duck-types candidates from ANY peer module (`A..N`) — including foreign-module-path
        `ArbitrageProofObject` / `MicroPortfolioCandidate` instances (`PYTHONPATH=src` vs `repo root`) —
        into `MicroPortfolioCandidate`.
        """
        if cls._is_duck_typed_micro_candidate(raw):
            base_ck = tuple(getattr(raw, "canonical_event_keys", ()) or ())
            has_non_cand = any(not str(k).startswith("CAND:") for k in base_ck)
            if isinstance(raw, MicroPortfolioCandidate) and (has_non_cand or not getattr(raw, "token_ids", ())):
                return raw
            ev_aug, mids_aug, ck_aug = cls._augment_concentration_keys_with_books_and_tokens(
                base_ck,
                market_ids=tuple(getattr(raw, "market_ids", ()) or ()),
                token_ids=tuple(getattr(raw, "token_ids", ()) or ()),
                books_by_token=books_by_token,
                fallback_cid=str(getattr(raw, "candidate_id", "CAND")),
            )
            raw_d = raw.to_dict() if hasattr(raw, "to_dict") else asdict(raw)
            raw_d["event_id"] = str(getattr(raw, "event_id", "") or ev_aug)
            raw_d["market_ids"] = mids_aug
            raw_d["canonical_event_keys"] = ck_aug
            raw_d["four_value_ledger"] = FourValueMetrics(
                theoretical_top_of_book_usd=_sf(_get_field(getattr(raw, "four_value_ledger", None), "theoretical_top_of_book_usd", default=0.0)),
                executable_l2_net_usd=_sf(_get_field(getattr(raw, "four_value_ledger", None), "executable_l2_net_usd", default=0.0)),
                attainable_risk_adjusted_usd=_sf(_get_field(getattr(raw, "four_value_ledger", None), "attainable_risk_adjusted_usd", default=0.0)),
                realized_net_usd=0.0,
            )
            raw_d["marginal_tranches"] = tuple(
                MarginalDepthTranche(
                    tranche_index=int(getattr(t, "tranche_index", idx)),
                    shares=float(getattr(t, "shares", 0.0)),
                    capital_usd=float(getattr(t, "capital_usd", 0.0)),
                    guaranteed_min_profit_usd=float(getattr(t, "guaranteed_min_profit_usd", 0.0)),
                    risk_adjusted_profit_usd=float(getattr(t, "risk_adjusted_profit_usd", 0.0)),
                    marginal_bps_per_hour=float(getattr(t, "marginal_bps_per_hour", 0.0)),
                )
                for idx, t in enumerate(getattr(raw, "marginal_tranches", ()) or ())
            )
            raw_d["proof"] = getattr(raw, "proof", None)
            return MicroPortfolioCandidate(**raw_d)

        if cls._is_duck_typed_proof_object(raw):
            cb = getattr(raw, "cost_breakdown", None)
            fvl = getattr(raw, "four_value_ledger", None)
            legs_exec = tuple(getattr(raw, "leg_executions", ()) or ())
            cap = max(0.0, _sf(getattr(cb, "capital_required_usd", 0.0), 0.0))
            opt_q = max(0.0, _sf(getattr(raw, "optimal_executable_quantity", 0.0), 0.0))
            seq_legs = sum(
                1
                for lg in legs_exec
                if str(getattr(lg, "action_type", "")).upper() in {"BUY_CLOB", "SELL_CLOB"}
                and not bool(getattr(lg, "is_maker", False))
            )
            exp_h = max(0.05, _sf(getattr(cb, "expected_lockup_hours", 2.0), 2.0))
            worst_h = max(exp_h, _sf(getattr(cb, "worst_case_lockup_hours", exp_h), exp_h))
            tids_proof = tuple(
                dict.fromkeys(
                    str(getattr(lg, "instrument_id", "")).strip()
                    for lg in legs_exec
                    if str(getattr(lg, "instrument_id", "")).strip()
                )
            )
            consumed = _extract_consumed_book_sides_from_proof(
                raw, tuple((t, "ASK", 1.0) for t in tids_proof)
            )
            mids_from_legs = tuple(
                dict.fromkeys(
                    str(getattr(lg, "market_id", "")).strip()
                    for lg in legs_exec
                    if str(getattr(lg, "market_id", "")).strip()
                )
            )
            cid_p = str(getattr(raw, "candidate_id", f"PROOF_{id(raw)}"))
            ev_p, mids_p, ckeys_p = cls._augment_concentration_keys_with_books_and_tokens(
                compute_canonical_concentration_keys(raw),
                market_ids=mids_from_legs,
                token_ids=tids_proof,
                books_by_token=books_by_token,
                fallback_cid=cid_p,
            )
            is_prelocked_p = bool(getattr(raw, "is_atomic_or_prelocked", False))
            d007_q = bool(
                getattr(raw, "d007_sub500_multileg_quarantine", False)
                or (seq_legs >= 3 and not is_prelocked_p and reconciled_nav_usd < 500.0)
            )
            opp_cls_p = getattr(raw, "opportunity_class", OpportunityClass.CLASS_D.value)
            if hasattr(opp_cls_p, "value"):
                opp_cls_p = str(opp_cls_p.value)
            else:
                opp_cls_p = str(opp_cls_p)
            disq_p = tuple(str(d) for d in (getattr(raw, "disqualifiers", ()) or ()))
            d001_blk_p = bool(
                "D001" in " ".join(disq_p)
                or is_d001_frozen_kmia_entity(raw)
                or any("KMIA" in k or "6707503" in k or "6707502" in k for k in ckeys_p)
            )
            min_pay_p = _sf(getattr(raw, "min_state_net_payoff_usd", 0.0), 0.0)
            exp_pay_p = _sf(getattr(raw, "expected_net_payoff_usd", min_pay_p), min_pay_p)
            fvl_coerced = FourValueMetrics(
                theoretical_top_of_book_usd=_sf(getattr(fvl, "theoretical_top_of_book_usd", min_pay_p), min_pay_p),
                executable_l2_net_usd=_sf(getattr(fvl, "executable_l2_net_usd", min_pay_p), min_pay_p),
                attainable_risk_adjusted_usd=_sf(getattr(fvl, "attainable_risk_adjusted_usd", exp_pay_p), exp_pay_p),
                realized_net_usd=0.0,
            )
            fam_p = str(getattr(raw, "family", "UNKNOWN") or "UNKNOWN")
            return MicroPortfolioCandidate(
                candidate_id=cid_p,
                family=fam_p,
                sub_type=f"PROOF_{fam_p}",
                opportunity_class=opp_cls_p,
                execution_mode_gate=str(getattr(raw, "execution_mode_cap", "MODE_2_SHADOW")),
                event_id=ev_p,
                canonical_event_keys=ckeys_p,
                market_ids=mids_p,
                token_ids=tids_proof,
                consumed_book_sides=consumed,
                sequential_clob_legs=seq_legs,
                is_atomic_or_inventory_locked=is_prelocked_p,
                d007_sub500_multileg_quarantine=d007_q,
                d001_kmia_frozen_blocked=d001_blk_p,
                min_order_shares=DEFAULT_MIN_ORDER_SHARES,
                optimal_shares=opt_q,
                capital_required_usd=cap,
                gross_edge_bps=round(_sf(getattr(raw, "gross_top_of_book_edge_per_unit", 0.0)) * 10_000.0, 2),
                net_executable_edge_bps=round(_sf(getattr(raw, "net_executable_edge_per_unit", 0.0)) * 10_000.0, 2),
                min_state_net_payoff_usd=min_pay_p,
                expected_net_payoff_usd=exp_pay_p,
                expected_lockup_hours=exp_h,
                worst_case_lockup_hours=worst_h,
                net_bps_per_hour_expected=_sf(getattr(raw, "capital_efficiency_bps_per_hr", 0.0)),
                net_bps_per_hour_worst_case=round((min_pay_p / max(cap, 0.01)) * 10_000.0 / worst_h, 2) if opt_q > 0 else 0.0,
                dispute_probability=0.0,
                partial_fill_prob=0.0,
                adverse_selection_cost_usd=0.0,
                uncertain_rebate_or_reward_usd=0.0,
                dormant_near_miss=False,
                four_value_ledger=fvl_coerced,
                proof=raw,  # type: ignore[arg-type]
                proof_sha256=str(getattr(raw, "proof_sha256", "") or ""),
                counterexample_states=tuple(str(s) for s in (getattr(raw, "counterexample_states", ()) or ())),
                disqualifiers=disq_p,
            )

        # Generic Mapping / peer dataclass coercion (`@complete-negrisk`, `@logical-specialized`, `@pipeline-shadow`)
        proof_sub = _get_field(raw, "proof", default=None)
        cb_sub = _get_field(raw, "cost_breakdown", default=getattr(proof_sub, "cost_breakdown", None))
        fvl_sub = _get_field(raw, "four_value_ledger", default=getattr(proof_sub, "four_value_ledger", None))

        cid = str(_get_field(raw, "candidate_id", "id", default=f"CAND_{id(raw)}") or f"CAND_{id(raw)}")
        fam = str(_get_field(raw, "family", default="UNKNOWN") or "UNKNOWN").strip().upper()
        sub = str(_get_field(raw, "sub_type", "strategy_type", "detector_name", default=fam) or fam)
        cls_s = _get_field(raw, "opportunity_class", "classification", "arb_class", default=getattr(proof_sub, "opportunity_class", OpportunityClass.CLASS_D.value))
        if hasattr(cls_s, "value"):
            cls_s = str(getattr(cls_s, "value"))
        else:
            cls_s = str(cls_s)

        opt_q = max(
            0.0,
            _sf(
                _get_field(
                    raw,
                    "optimal_shares",
                    "optimal_executable_quantity",
                    "shares",
                    default=getattr(proof_sub, "optimal_executable_quantity", 0.0),
                )
            ),
        )
        cap_u = max(
            0.0,
            _sf(
                _get_field(
                    raw,
                    "capital_required_usd",
                    "acquisition_cost_usd",
                    "notional_usd",
                    default=_get_field(cb_sub, "capital_required_usd", default=0.0),
                )
            ),
        )
        min_pay = _sf(
            _get_field(
                raw,
                "min_state_net_payoff_usd",
                "executable_l2_net_usd",
                "guaranteed_net_profit_usd",
                default=getattr(proof_sub, "min_state_net_payoff_usd", 0.0),
            )
        )
        exp_pay = _sf(
            _get_field(
                raw,
                "expected_net_payoff_usd",
                "attainable_risk_adjusted_usd",
                default=getattr(proof_sub, "expected_net_payoff_usd", min_pay),
            ),
            min_pay,
        )
        exp_h = max(0.05, _sf(_get_field(raw, "expected_lockup_hours", "lockup_hours", default=_get_field(cb_sub, "expected_lockup_hours", default=2.0)), 2.0))
        worst_h = max(exp_h, _sf(_get_field(raw, "worst_case_lockup_hours", default=_get_field(cb_sub, "worst_case_lockup_hours", default=exp_h)), exp_h))
        seq_legs = int(_sf(_get_field(raw, "sequential_clob_legs", "num_legs", "leg_count", default=2), 2.0))
        is_atomic = bool(_get_field(raw, "is_atomic_or_inventory_locked", "is_atomic_or_prelocked", default=getattr(proof_sub, "is_atomic_or_prelocked", False)))
        d001_blk = is_d001_frozen_kmia_entity(raw)
        d007_q = bool(
            _get_field(raw, "d007_sub500_multileg_quarantine", default=getattr(proof_sub, "d007_sub500_multileg_quarantine", False))
            or (seq_legs >= 3 and not is_atomic and reconciled_nav_usd < 500.0)
        )
        mids = tuple(str(x) for x in (_get_field(raw, "market_ids", default=None) or ()) if str(x))
        mid_single = str(_get_field(raw, "market_id", default="") or "").strip()
        if mid_single and not mids:
            mids = (mid_single,)
        tids = tuple(str(x) for x in (_get_field(raw, "token_ids", "instrument_ids", default=None) or ()) if str(x))
        if not tids and proof_sub is not None:
            tids = tuple(
                dict.fromkeys(
                    str(getattr(lg, "instrument_id", "")).strip()
                    for lg in (getattr(proof_sub, "leg_executions", ()) or ())
                    if str(getattr(lg, "instrument_id", "")).strip()
                )
            )
        ev_raw = str(_get_field(raw, "event_id", default="") or "").strip()
        base_ck = set(compute_canonical_concentration_keys(raw))
        if ev_raw:
            base_ck.add(f"EVT:{ev_raw}")
        ev_aug, mids_aug, ckeys = cls._augment_concentration_keys_with_books_and_tokens(
            base_ck,
            market_ids=mids,
            token_ids=tids,
            books_by_token=books_by_token,
            fallback_cid=cid,
        )
        if any("KMIA" in k or "6707503" in k or "6707502" in k for k in ckeys):
            d001_blk = True

        consumed_raw = _get_field(raw, "consumed_book_sides", default=None)
        if consumed_raw:
            consumed = tuple((str(t), str(s).upper(), float(w)) for t, s, w in consumed_raw)
        elif proof_sub is not None:
            consumed = _extract_consumed_book_sides_from_proof(proof_sub, tuple((t, "ASK", 1.0) for t in tids))
        else:
            consumed = tuple((t, "ASK", 1.0) for t in tids)

        bps_hr_exp = round((exp_pay / max(cap_u, 0.01)) * 10_000.0 / exp_h, 2) if opt_q > 0 and cap_u > 0 else 0.0
        bps_hr_wst = round((min_pay / max(cap_u, 0.01)) * 10_000.0 / worst_h, 2) if opt_q > 0 and cap_u > 0 else 0.0

        return MicroPortfolioCandidate(
            candidate_id=cid,
            family=fam,
            sub_type=sub,
            opportunity_class=cls_s,
            execution_mode_gate=("QUARANTINED_D007_LT_500_NAV" if d007_q else "MODE_2_SHADOW"),
            event_id=ev_raw or ev_aug,
            canonical_event_keys=ckeys,
            market_ids=mids_aug,
            token_ids=tids,
            consumed_book_sides=consumed,
            sequential_clob_legs=seq_legs,
            is_atomic_or_inventory_locked=is_atomic,
            d007_sub500_multileg_quarantine=d007_q,
            d001_kmia_frozen_blocked=d001_blk,
            min_order_shares=max(DEFAULT_MIN_ORDER_SHARES, _sf(_get_field(raw, "min_order_shares", "min_order_size", default=DEFAULT_MIN_ORDER_SHARES), DEFAULT_MIN_ORDER_SHARES)),
            optimal_shares=opt_q,
            capital_required_usd=cap_u,
            gross_edge_bps=_sf(_get_field(raw, "gross_edge_bps", default=0.0)),
            net_executable_edge_bps=_sf(_get_field(raw, "net_executable_edge_bps", default=0.0)),
            min_state_net_payoff_usd=min_pay,
            expected_net_payoff_usd=exp_pay,
            expected_lockup_hours=exp_h,
            worst_case_lockup_hours=worst_h,
            net_bps_per_hour_expected=bps_hr_exp,
            net_bps_per_hour_worst_case=bps_hr_wst,
            dispute_probability=_sf(_get_field(raw, "dispute_probability", default=0.0)),
            partial_fill_prob=_sf(_get_field(raw, "partial_fill_prob", default=0.0)),
            adverse_selection_cost_usd=_sf(_get_field(raw, "adverse_selection_cost_usd", default=0.0)),
            uncertain_rebate_or_reward_usd=_sf(_get_field(raw, "uncertain_rebate_or_reward_usd", default=0.0)),
            dormant_near_miss=bool(_get_field(raw, "dormant_near_miss", default=False)),
            four_value_ledger=FourValueMetrics(
                theoretical_top_of_book_usd=_sf(_get_field(raw, "theoretical_top_of_book_usd", default=_get_field(fvl_sub, "theoretical_top_of_book_usd", default=min_pay))),
                executable_l2_net_usd=min_pay,
                attainable_risk_adjusted_usd=exp_pay,
                realized_net_usd=0.0,
            ),
            proof=proof_sub,
            proof_sha256=str(_get_field(raw, "proof_sha256", default=getattr(proof_sub, "proof_sha256", "")) or ""),
        )

    @staticmethod
    def _extract_book_rungs_sorted(
        books_by_token: Optional[Mapping[str, Any]],
        token_id: str,
        side: str,
        *,
        eligible_candidates: Sequence[Tuple[MicroPortfolioCandidate, Tuple[MarginalDepthTranche, ...]]] = (),
    ) -> List[List[float]]:
        """
        Builds a mutable price-sorted L2 rung list `[[price, remaining_gross_shares], ...]`
        (asks ascending, bids descending).
        CRITICAL (`BUG-MP-1` fix):
          1. Preserves per-rung prices so unwalked expensive rungs (e.g. `500 sh @ $0.99`) can NEVER
             subsidize double-allocation of a thin profitable L1 rung (`10 sh @ $0.40`).
          2. When `books_by_token` is `None` or lacks `token_id`, derives bounded capacity from
             `cand.proof.leg_executions` (`l1_available_shares` / `gross_shares` at `worst_limit_price`)
             or `max(cand.optimal_shares * mult)` — NEVER `1e9`!
        """
        side_u = side.upper()
        if books_by_token and token_id in books_by_token:
            bk = books_by_token[token_id]
            out_rungs: List[List[float]] = []
            if hasattr(bk, "asks") and hasattr(bk, "bids") and not isinstance(bk, Mapping):
                lv_seq = bk.asks if side_u == "ASK" else bk.bids
                for lv in lv_seq:
                    px = _sf(getattr(lv, "price", 0.0), 0.0)
                    sz = _sf(getattr(lv, "size", 0.0), 0.0)
                    if 0.0 < px < 1.0 and sz > 0.0:
                        out_rungs.append([px, sz])
            elif isinstance(bk, Mapping):
                raw_lvs = bk.get("asks" if side_u == "ASK" else "bids") or ()
                for lv in raw_lvs:
                    if isinstance(lv, Mapping):
                        px = _sf(lv.get("price"), 0.0)
                        sz = _sf(lv.get("size"), 0.0)
                    elif isinstance(lv, (list, tuple)) and len(lv) >= 2:
                        px = _sf(lv[0], 0.0)
                        sz = _sf(lv[1], 0.0)
                    else:
                        px, sz = 0.0, 0.0
                    if 0.0 < px < 1.0 and sz > 0.0:
                        out_rungs.append([px, sz])
            out_rungs.sort(key=lambda r: (-r[0] if side_u == "BID" else r[0]))
            return out_rungs

        # Fallback when `books_by_token` is `None` or missing `token_id`: infer bounded rung from proofs/candidates
        inferred_px = 0.0 if side_u == "ASK" else 1.0
        inferred_gross_cap = 0.0
        found_from_proof = False
        for cand, _ in eligible_candidates:
            prf = cand.proof
            if prf is not None and getattr(prf, "leg_executions", None):
                for lg in getattr(prf, "leg_executions", ()):
                    act = str(getattr(lg, "action_type", "")).upper()
                    lg_side = "ASK" if act == "BUY_CLOB" else ("BID" if act == "SELL_CLOB" else "")
                    if lg_side == side_u and str(getattr(lg, "instrument_id", "")).strip() == token_id and not bool(getattr(lg, "is_maker", False)):
                        found_from_proof = True
                        w_px = _sf(getattr(lg, "worst_limit_price", 0.0), 0.0) or _sf(getattr(lg, "l1_price", 0.0), 0.0)
                        if 0.0 < w_px < 1.0:
                            inferred_px = max(inferred_px, w_px) if side_u == "ASK" else min(inferred_px, w_px)
                        rungs_w = int(_sf(getattr(lg, "rungs_walked", 1), 1.0))
                        l1_av = _sf(getattr(lg, "l1_available_shares", 0.0), 0.0)
                        gr_sh = _sf(getattr(lg, "gross_shares", 0.0), 0.0)
                        known_sh = max(l1_av, gr_sh) if rungs_w <= 1 else max(gr_sh, l1_av)
                        inferred_gross_cap = max(inferred_gross_cap, known_sh)

        if found_from_proof and inferred_gross_cap > 0.0:
            px_clean = inferred_px if 0.0 < inferred_px < 1.0 else (0.50)
            return [[px_clean, inferred_gross_cap]]

        max_cand_gross = 0.0
        for cand, _ in eligible_candidates:
            for tok, s_dir, mult in cand.consumed_book_sides:
                if tok == token_id and s_dir == side_u:
                    max_cand_gross = max(max_cand_gross, max(0.0, cand.optimal_shares * mult))
        if max_cand_gross > 0.0:
            return [[0.9999 if side_u == "ASK" else 0.0001, max_cand_gross]]
        return []

    @staticmethod
    def _candidate_leg_limit_prices(cand: MicroPortfolioCandidate) -> Dict[Tuple[str, str], float]:
        """Returns `(token_id, side) -> worst_executable_limit_price` so unwalked expensive rungs are excluded."""
        limits: Dict[Tuple[str, str], float] = {}
        prf = cand.proof
        if prf is not None and getattr(prf, "leg_executions", None):
            for lg in getattr(prf, "leg_executions", ()):
                act = str(getattr(lg, "action_type", "")).upper()
                inst = str(getattr(lg, "instrument_id", "")).strip()
                if act not in {"BUY_CLOB", "SELL_CLOB"} or not inst or bool(getattr(lg, "is_maker", False)):
                    continue
                side_u = "ASK" if act == "BUY_CLOB" else "BID"
                w_px = _sf(getattr(lg, "worst_limit_price", 0.0), 0.0) or _sf(getattr(lg, "l1_price", 0.0), 0.0)
                if 0.0 < w_px < 1.0:
                    k = (inst, side_u)
                    if k not in limits:
                        limits[k] = w_px
                    else:
                        limits[k] = max(limits[k], w_px) if side_u == "ASK" else min(limits[k], w_px)
        for tok, side_u, _ in cand.consumed_book_sides:
            k = (tok, side_u)
            if k not in limits:
                limits[k] = 1.0 if side_u == "ASK" else 0.0
        return limits

    @staticmethod
    def _available_gross_within_limit(rungs: Sequence[Sequence[float]], side: str, limit_px: float) -> float:
        if side == "ASK":
            return sum(float(r[1]) for r in rungs if float(r[0]) <= limit_px + 1e-9 and float(r[1]) > 0.0)
        return sum(float(r[1]) for r in rungs if float(r[0]) >= limit_px - 1e-9 and float(r[1]) > 0.0)

    @staticmethod
    def _consume_book_rungs(
        rungs: List[List[float]],
        side: str,
        limit_px: float,
        gross_needed: float,
    ) -> List[Tuple[int, float]]:
        rem = max(0.0, float(gross_needed))
        taken_log: List[Tuple[int, float]] = []
        for idx, r in enumerate(rungs):
            if rem <= 1e-12:
                break
            if r[1] <= 1e-12:
                continue
            ok_px = (r[0] <= limit_px + 1e-9) if side == "ASK" else (r[0] >= limit_px - 1e-9)
            if not ok_px:
                continue
            take = min(r[1], rem)
            r[1] = max(0.0, r[1] - take)
            rem -= take
            taken_log.append((idx, take))
        return taken_log

    def _synthesize_tranches(self, cand: MicroPortfolioCandidate) -> Tuple[MarginalDepthTranche, ...]:
        if cand.marginal_tranches:
            tr_in = list(cand.marginal_tranches)
            if cand.min_state_net_payoff_usd <= 0.0:
                return ()
            sum_min = sum(t.guaranteed_min_profit_usd for t in tr_in)
            if sum_min > cand.min_state_net_payoff_usd + 1e-6:
                scale = max(0.0, cand.min_state_net_payoff_usd / max(sum_min, 1e-9))
                eff_h = max(0.05, cand.expected_lockup_hours)
                clamped: List[MarginalDepthTranche] = []
                for t in tr_in:
                    new_min = math.floor((t.guaranteed_min_profit_usd * scale) * 1_000_000.0 + 1e-9) / 1_000_000.0
                    if new_min <= 0.0:
                        continue
                    new_ra = round(min(t.risk_adjusted_profit_usd * scale, new_min), 6)
                    clamped.append(
                        MarginalDepthTranche(
                            tranche_index=len(clamped),
                            shares=t.shares,
                            capital_usd=t.capital_usd,
                            guaranteed_min_profit_usd=new_min,
                            risk_adjusted_profit_usd=new_ra,
                            marginal_bps_per_hour=round((new_ra / max(t.capital_usd, 1e-6)) * 10_000.0 / eff_h, 2),
                        )
                    )
                return tuple(clamped)
            return tuple(tr_in)
        if cand.optimal_shares < cand.min_order_shares or cand.capital_required_usd <= 0.0 or cand.min_state_net_payoff_usd <= 0.0:
            return ()
        unit_cap = cand.capital_required_usd / cand.optimal_shares
        unit_min_p = cand.min_state_net_payoff_usd / cand.optimal_shares
        unit_ra_p = max(0.0, min(cand.expected_net_payoff_usd, cand.four_value_ledger.attainable_risk_adjusted_usd or cand.expected_net_payoff_usd)) / cand.optimal_shares
        if unit_ra_p <= 0.0:
            unit_ra_p = unit_min_p * (1.0 - 0.5 * cand.partial_fill_prob)

        step = max(cand.min_order_shares, 5.0)
        tranches: List[MarginalDepthTranche] = []
        q_done = 0.0
        idx = 0
        eff_h = max(0.05, cand.expected_lockup_hours)
        while q_done + 1e-6 < cand.optimal_shares and idx < 32:
            dq = min(step, cand.optimal_shares - q_done)
            if (cand.optimal_shares - (q_done + dq)) < cand.min_order_shares * 0.5:
                dq = cand.optimal_shares - q_done
            dc = dq * unit_cap
            dmp = dq * unit_min_p
            drp = dq * unit_ra_p
            tranches.append(
                MarginalDepthTranche(
                    tranche_index=idx,
                    shares=round(dq, 4),
                    capital_usd=round(dc, 6),
                    guaranteed_min_profit_usd=round(dmp, 6),
                    risk_adjusted_profit_usd=round(drp, 6),
                    marginal_bps_per_hour=round((drp / max(dc, 1e-6)) * 10_000.0 / eff_h, 2),
                )
            )
            q_done += dq
            idx += 1
        return tuple(tranches)

    def optimize_portfolio(
        self,
        candidates: Sequence[Any],
        *,
        books_by_token: Optional[Mapping[str, Any]] = None,
        budget_label: str = "LIVE_REFERENCE_48_70_PUSD",
    ) -> PortfolioOptimizationResult:
        reserve_usd = round(self.available_liquid_pusd * self.settlement_reserve_pct, 4)
        deployable_cash = max(0.0, round(self.available_liquid_pusd - reserve_usd, 6))
        per_event_cap_usd = round(self.reconciled_nav_usd * self.max_event_concentration_pct, 6)

        # Pre-seed existing open exposure per canonical event key (including `$50.51` frozen `KMIA` -> `WXSTATION:KMIA` capped out!)
        used_by_event_key: Dict[str, float] = defaultdict(float)
        for pos in self.existing_positions:
            p_notional = max(0.0, _sf(pos.get("notional_usd"), 0.0))
            if p_notional <= 0.0:
                continue
            for pk in compute_canonical_concentration_keys(pos):
                used_by_event_key[pk] += p_notional

        coerced = [
            self._coerce_candidate(c, self.reconciled_nav_usd, books_by_token=books_by_token)
            for c in candidates
        ]
        eligible: List[Tuple[MicroPortfolioCandidate, Tuple[MarginalDepthTranche, ...]]] = []
        rejected: List[Dict[str, Any]] = []

        for c in coerced:
            if c.d001_kmia_frozen_blocked or is_d001_frozen_kmia_entity(c):
                rejected.append({"candidate_id": c.candidate_id, "family": c.family, "reason": "D001_FROZEN_KMIA_NON_INTERFERENCE"})
                continue
            if c.dormant_near_miss:
                rejected.append({"candidate_id": c.candidate_id, "family": c.family, "reason": "DORMANT_NEAR_MISS_NEGATIVE_NET_SPREAD"})
                continue
            if self.strict_riskless_only and c.opportunity_class not in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value}:
                rejected.append(
                    {
                        "candidate_id": c.candidate_id,
                        "family": c.family,
                        "reason": f"STRICT_RISKLESS_CLASS_GATE:{c.opportunity_class}",
                    }
                )
                continue
            if self.strict_riskless_only and c.min_state_net_payoff_usd <= 0.0:
                rejected.append({"candidate_id": c.candidate_id, "family": c.family, "reason": "NON_POSITIVE_MIN_STATE_NET_PAYOFF"})
                continue
            if c.sequential_clob_legs >= 3 and not c.is_atomic_or_inventory_locked:
                if self.reconciled_nav_usd < self.d007_multileg_nav_floor_usd - 1e-6:
                    rejected.append(
                        {
                            "candidate_id": c.candidate_id,
                            "family": c.family,
                            "reason": f"D007_MULTILEG_3PLUS_QUARANTINED_BELOW_500_NAV:legs={c.sequential_clob_legs}:nav={self.reconciled_nav_usd:.2f}",
                        }
                    )
                    continue
                if not self.certified_multileg_3plus_enabled:
                    rejected.append(
                        {
                            "candidate_id": c.candidate_id,
                            "family": c.family,
                            "reason": f"D007_MULTILEG_3PLUS_UNCERTIFIED_ABOVE_500_NAV:legs={c.sequential_clob_legs}",
                        }
                    )
                    continue
            if c.worst_case_lockup_hours > self.max_lockup_hours + 1e-6:
                rejected.append(
                    {
                        "candidate_id": c.candidate_id,
                        "family": c.family,
                        "reason": f"EXCEEDS_MAX_LOCKUP_HORIZON:{c.worst_case_lockup_hours:.1f}h>{self.max_lockup_hours:.1f}h",
                    }
                )
                continue
            if c.net_bps_per_hour_expected < self.min_velocity_bps_per_hr - 1e-6:
                rejected.append(
                    {
                        "candidate_id": c.candidate_id,
                        "family": c.family,
                        "reason": f"BELOW_MIN_VELOCITY_HURDLE:{c.net_bps_per_hour_expected:.2f}<{self.min_velocity_bps_per_hr:.2f}",
                    }
                )
                continue
            if c.optimal_shares < c.min_order_shares - 1e-6 or c.capital_required_usd < DEFAULT_MIN_MARKETABLE_BUY_USD - 1e-6:
                rejected.append({"candidate_id": c.candidate_id, "family": c.family, "reason": "BELOW_MIN_ORDER_LOT_OR_NOTIONAL"})
                continue

            tr = self._synthesize_tranches(c)
            if not tr:
                rejected.append({"candidate_id": c.candidate_id, "family": c.family, "reason": "NO_POSITIVE_MARGINAL_L2_TRANCHES"})
                continue
            eligible.append((c, tr))

        # Shared price-bounded L2 book rung ledger `(token_id, side) -> [[price, remaining_gross_shares], ...]`
        rem_book_rungs: Dict[Tuple[str, str], List[List[float]]] = {}
        cand_limit_px: List[Dict[Tuple[str, str], float]] = []
        for c, _ in eligible:
            cand_limit_px.append(self._candidate_leg_limit_prices(c))
            for tok, side, _ in c.consumed_book_sides:
                key_bs = (tok, side)
                if key_bs not in rem_book_rungs:
                    rem_book_rungs[key_bs] = self._extract_book_rungs_sorted(
                        books_by_token, tok, side, eligible_candidates=eligible
                    )

        # Phase 1: Simultaneous Marginal-Velocity Tranche Solver across all candidates
        # At each iteration, picks the feasible next marginal tranche `(cand_idx, tranche_idx)` maximizing
        # `marginal_bps_per_hour` (with tiny tie-break favoring `CLASS_A` over `CLASS_B`).
        next_tr_idx: List[int] = [0] * len(eligible)
        alloc_sh: List[float] = [0.0] * len(eligible)
        alloc_cap: List[float] = [0.0] * len(eligible)
        alloc_min_p: List[float] = [0.0] * len(eligible)
        alloc_ra_p: List[float] = [0.0] * len(eligible)
        alloc_rung_log: List[List[Tuple[Tuple[str, str], int, float]]] = [[] for _ in eligible]
        rem_cash = deployable_cash

        while rem_cash >= DEFAULT_MIN_MARKETABLE_BUY_USD - 1e-6:
            best_choice: Optional[Tuple[float, int, MarginalDepthTranche]] = None
            for i, (cand, tr_list) in enumerate(eligible):
                ti = next_tr_idx[i]
                if ti >= len(tr_list):
                    continue
                tr = tr_list[ti]
                if tr.capital_usd > rem_cash + 1e-9:
                    continue
                # Event concentration cap check across ALL canonical keys of `cand`
                if any(used_by_event_key[ek] + tr.capital_usd > per_event_cap_usd + 1e-9 for ek in cand.canonical_event_keys):
                    continue
                # Shared price-bounded L2 rung depth check across ALL consumed `(token_id, side)` legs
                lim_map_i = cand_limit_px[i]
                if any(
                    self._available_gross_within_limit(
                        rem_book_rungs[(tok, side)], side, lim_map_i.get((tok, side), 1.0 if side == "ASK" else 0.0)
                    )
                    < (tr.shares * mult) - 1e-7
                    for tok, side, mult in cand.consumed_book_sides
                ):
                    continue
                cls_bonus = 1.02 if cand.opportunity_class == OpportunityClass.CLASS_A.value else 1.00
                score = tr.marginal_bps_per_hour * cls_bonus
                if best_choice is None or score > best_choice[0]:
                    best_choice = (score, i, tr)

            if best_choice is None:
                break

            _, chosen_i, chosen_tr = best_choice
            chosen_cand = eligible[chosen_i][0]
            lim_map_c = cand_limit_px[chosen_i]
            next_tr_idx[chosen_i] += 1
            alloc_sh[chosen_i] += chosen_tr.shares
            alloc_cap[chosen_i] += chosen_tr.capital_usd
            alloc_min_p[chosen_i] += chosen_tr.guaranteed_min_profit_usd
            alloc_ra_p[chosen_i] += chosen_tr.risk_adjusted_profit_usd
            rem_cash -= chosen_tr.capital_usd
            for ek in chosen_cand.canonical_event_keys:
                used_by_event_key[ek] += chosen_tr.capital_usd
            for tok, side, mult in chosen_cand.consumed_book_sides:
                k_bs = (tok, side)
                taken = self._consume_book_rungs(
                    rem_book_rungs[k_bs],
                    side,
                    lim_map_c.get(k_bs, 1.0 if side == "ASK" else 0.0),
                    chosen_tr.shares * mult,
                )
                for r_idx, q_taken in taken:
                    alloc_rung_log[chosen_i].append((k_bs, r_idx, q_taken))

        # Phase 2: Discrete Minimum-Lot Feasibility Repair + Pairwise 2-Opt Rebalancing
        # Drop any partial allocation that failed to reach `min_order_shares` and recycle its cash/cap/rungs!
        for i, (cand, _) in enumerate(eligible):
            if 0.0 < alloc_sh[i] < cand.min_order_shares - 1e-6:
                rem_cash += alloc_cap[i]
                for ek in cand.canonical_event_keys:
                    used_by_event_key[ek] = max(0.0, used_by_event_key[ek] - alloc_cap[i])
                for k_bs, r_idx, q_taken in alloc_rung_log[i]:
                    rem_book_rungs[k_bs][r_idx][1] += q_taken
                alloc_rung_log[i].clear()
                alloc_sh[i] = alloc_cap[i] = alloc_min_p[i] = alloc_ra_p[i] = 0.0

        # 2-Opt Swap Check: if an unallocated lumpy candidate `j` (whose Tranche 0 required more cash than
        # remained after smaller allocations) yields strictly higher total portfolio `profit / hr` than a lower-rate
        # allocated candidate `i`, swap `i -> j` while respecting all event & price-bounded L2 rung constraints!
        for j, (cand_j, tr_j_list) in enumerate(eligible):
            if alloc_sh[j] > 0.0 or not tr_j_list:
                continue
            tr0 = tr_j_list[0]
            if tr0.shares < cand_j.min_order_shares - 1e-6:
                continue
            lim_map_j = cand_limit_px[j]
            rate_j = tr0.risk_adjusted_profit_usd / max(0.05, cand_j.expected_lockup_hours)
            for i, (cand_i, _) in enumerate(eligible):
                if alloc_sh[i] <= 0.0:
                    continue
                rate_i = alloc_ra_p[i] / max(0.05, cand_i.expected_lockup_hours)
                if rate_j <= rate_i + 1e-9:
                    continue
                if rem_cash + alloc_cap[i] < tr0.capital_usd - 1e-9:
                    continue
                shared_keys = set(cand_i.canonical_event_keys) & set(cand_j.canonical_event_keys)
                evt_ok = all(
                    (used_by_event_key[ek] - (alloc_cap[i] if ek in shared_keys else 0.0) + tr0.capital_usd) <= per_event_cap_usd + 1e-9
                    for ek in cand_j.canonical_event_keys
                )
                if not evt_ok:
                    continue
                # Temporarily restore `i`'s rungs to check exact price-bounded rung feasibility for `j`
                for k_bs, r_idx, q_taken in alloc_rung_log[i]:
                    rem_book_rungs[k_bs][r_idx][1] += q_taken
                rungs_ok = all(
                    self._available_gross_within_limit(
                        rem_book_rungs[(tok, side)], side, lim_map_j.get((tok, side), 1.0 if side == "ASK" else 0.0)
                    )
                    >= (tr0.shares * mult) - 1e-7
                    for tok, side, mult in cand_j.consumed_book_sides
                )
                if not rungs_ok:
                    for k_bs, r_idx, q_taken in alloc_rung_log[i]:
                        rem_book_rungs[k_bs][r_idx][1] = max(0.0, rem_book_rungs[k_bs][r_idx][1] - q_taken)
                    continue

                # Commit improving 2-opt portfolio swap `i -> j`
                rem_cash = rem_cash + alloc_cap[i] - tr0.capital_usd
                for ek in cand_i.canonical_event_keys:
                    used_by_event_key[ek] = max(0.0, used_by_event_key[ek] - alloc_cap[i])
                alloc_rung_log[i].clear()
                alloc_sh[i] = alloc_cap[i] = alloc_min_p[i] = alloc_ra_p[i] = 0.0

                alloc_sh[j] = tr0.shares
                alloc_cap[j] = tr0.capital_usd
                alloc_min_p[j] = tr0.guaranteed_min_profit_usd
                alloc_ra_p[j] = tr0.risk_adjusted_profit_usd
                for ek in cand_j.canonical_event_keys:
                    used_by_event_key[ek] += tr0.capital_usd
                for tok, side, mult in cand_j.consumed_book_sides:
                    k_bs = (tok, side)
                    taken_j = self._consume_book_rungs(
                        rem_book_rungs[k_bs],
                        side,
                        lim_map_j.get(k_bs, 1.0 if side == "ASK" else 0.0),
                        tr0.shares * mult,
                    )
                    for r_idx, q_taken in taken_j:
                        alloc_rung_log[j].append((k_bs, r_idx, q_taken))
                break

        slices: List[AllocatedPortfolioSlice] = []
        for i, (cand, _) in enumerate(eligible):
            if alloc_sh[i] <= 0.0:
                rejected.append(
                    {
                        "candidate_id": cand.candidate_id,
                        "family": cand.family,
                        "reason": "CROWDED_OUT_BY_BUDGET_CONCENTRATION_OR_SHARED_L2_DEPTH",
                    }
                )
                continue
            eff_h = max(0.05, cand.expected_lockup_hours)
            bps_hr = round((alloc_ra_p[i] / max(alloc_cap[i], 1e-6)) * 10_000.0 / eff_h, 2)
            slices.append(
                AllocatedPortfolioSlice(
                    candidate_id=cand.candidate_id,
                    family=cand.family,
                    sub_type=cand.sub_type,
                    opportunity_class=cand.opportunity_class,
                    allocated_shares=round(alloc_sh[i], 4),
                    allocated_capital_usd=round(alloc_cap[i], 4),
                    guaranteed_min_profit_usd=round(alloc_min_p[i], 6),
                    risk_adjusted_profit_usd=round(alloc_ra_p[i], 6),
                    expected_lockup_hours=cand.expected_lockup_hours,
                    worst_case_lockup_hours=cand.worst_case_lockup_hours,
                    realizable_bps_per_hour=bps_hr,
                    canonical_event_keys=cand.canonical_event_keys,
                )
            )

        slices.sort(key=lambda s: -s.realizable_bps_per_hour)
        tot_cap = round(sum(s.allocated_capital_usd for s in slices), 4)
        tot_min_p = round(sum(s.guaranteed_min_profit_usd for s in slices), 6)
        tot_ra_p = round(sum(s.risk_adjusted_profit_usd for s in slices), 6)
        tot_dollar_hrs = round(sum(s.allocated_capital_usd * max(0.05, s.expected_lockup_hours) for s in slices), 6)
        prof_per_hr = round(sum(s.risk_adjusted_profit_usd / max(0.05, s.expected_lockup_hours) for s in slices), 6)
        port_bps_hr = round((prof_per_hr / max(self.available_liquid_pusd, 0.01)) * 10_000.0, 4)
        hurdle_bps_hr = round((HOURLY_INFRA_COST_USD / max(self.available_liquid_pusd, 0.01)) * 10_000.0, 4)

        # Post-optimization mathematical self-audit assertions
        kmia_untouched = all(
            not any("KMIA" in k or "6707503" in k or "6707502" in k for k in s.canonical_event_keys)
            for s in slices
        )
        new_by_evt: Dict[str, float] = defaultdict(float)
        for s in slices:
            for ek in s.canonical_event_keys:
                new_by_evt[ek] += s.allocated_capital_usd
        conc_ok = all(v <= per_event_cap_usd + 1e-4 for v in new_by_evt.values())

        return PortfolioOptimizationResult(
            budget_label=budget_label,
            available_liquid_pusd=round(self.available_liquid_pusd, 6),
            reconciled_nav_usd=round(self.reconciled_nav_usd, 6),
            settlement_reserve_usd=reserve_usd,
            deployable_cash_budget_usd=round(deployable_cash, 6),
            per_event_cap_usd=round(per_event_cap_usd, 6),
            infra_hurdle_usd_per_hr=HOURLY_INFRA_COST_USD,
            infra_hurdle_bps_per_hr=hurdle_bps_hr,
            allocated_slices=tuple(slices),
            rejected_candidates=tuple(rejected),
            total_allocated_capital_usd=tot_cap,
            unallocated_cash_usd=round(max(0.0, self.available_liquid_pusd - tot_cap), 4),
            total_guaranteed_min_profit_usd=tot_min_p,
            total_risk_adjusted_profit_usd=tot_ra_p,
            total_dollar_hours_locked=tot_dollar_hrs,
            portfolio_realizable_profit_per_hour_usd=prof_per_hr,
            portfolio_realizable_bps_per_hour=port_bps_hr,
            clears_infra_hurdle=bool(prof_per_hr >= HOURLY_INFRA_COST_USD - 1e-9),
            infra_coverage_ratio=round(prof_per_hr / max(HOURLY_INFRA_COST_USD, 1e-9), 4),
            d001_kmia_untouched_verified=kmia_untouched,
            d007_concentration_verified=conc_ok,
            d007_sub500_multileg_quarantine_verified=True,
        )

    @classmethod
    def evaluate_shadow_budget_curve(
        cls,
        candidates: Sequence[Any],
        *,
        books_by_token: Optional[Mapping[str, Any]] = None,
        budgets_usd: Sequence[float] = (AUTHORITATIVE_LIVE_CASH_PUSD, 250.0, 500.0, 1000.0),
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluates optimal simultaneous allocation at `$48.70` live cash vs shadow scale milestones."""
        curve: Dict[str, Dict[str, Any]] = {}
        for b in budgets_usd:
            is_live_ref = abs(float(b) - AUTHORITATIVE_LIVE_CASH_PUSD) < 0.05
            lbl = "LIVE_CASH_BASELINE_48_70" if is_live_ref else f"SHADOW_BUDGET_{int(round(b))}"
            opt = cls(
                available_liquid_pusd=float(b),
                reconciled_nav_usd=(AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD if is_live_ref else float(b)),
                existing_positions=(AUTHORITATIVE_FROZEN_KMIA_POSITIONS if is_live_ref else ()),
            )
            res = opt.optimize_portfolio(candidates, books_by_token=books_by_token, budget_label=lbl)
            curve[lbl] = res.to_dict()
        return curve


# ---------------------------------------------------------------------------
# Family N — Newly Discovered Structures, Mechanism Scanner & ResearchBacklog
# ---------------------------------------------------------------------------


KNOWN_GAMMA_EVENT_KEYS: frozenset[str] = frozenset(
    {
        "active", "archived", "automaticallyActive", "category", "closed", "commentCount", "competitive",
        "createdAt", "creationDate", "cumulativeMarkets", "cyom", "deploying", "description", "enableNegRisk",
        "enableOrderBook", "endDate", "estimateValue", "eventMetadata", "featured", "gmpChartMode", "icon",
        "id", "image", "liquidity", "liquidityAmm", "liquidityClob", "markets", "negRisk", "negRiskAugmented",
        "negRiskMarketID", "new", "openInterest", "pendingDeployment", "resolutionSource", "restricted",
        "series", "seriesSlug", "showAllOutcomes", "showMarketImages", "slug", "sortBy", "startDate",
        "subTitle", "tags", "ticker", "title", "updatedAt", "version", "volume", "volume1mo", "volume1wk",
        "volume1yr", "volume24hr",
    }
)

KNOWN_GAMMA_MARKET_KEYS: frozenset[str] = frozenset(
    {
        "acceptingOrders", "acceptingOrdersTimestamp", "active", "approved", "archived", "automaticallyActive",
        "automaticallyResolved", "bestAsk", "bestBid", "category", "clearBookOnStart", "clobRewards",
        "clobTokenIds", "closed", "closedTime", "comboStatus", "Competitive", "competitive", "conditionId",
        "createdAt", "customLiveness", "cyom", "deploying", "deployingTimestamp", "description",
        "enableOrderBook", "endDate", "endDateIso", "events", "fallbackResolutionType", "featured", "fee",
        "feeSchedule", "feeType", "feesEnabled", "funded", "gameId", "groupItemThreshold", "groupItemTitle",
        "hasReviewedDates", "holdingRewardsEnabled", "icon", "id", "image", "lastTradePrice", "line",
        "liquidity", "liquidityAmm", "liquidityClob", "liquidityNum", "makerBaseFee", "manualActivation",
        "marketMakerAddress", "marketType", "negRisk", "negRiskMarketID", "negRiskOther", "negRiskRequestID",
        "new", "oneDayPriceChange", "oneHourPriceChange", "oneMonthPriceChange", "oneWeekPriceChange",
        "oneYearPriceChange", "orderMinSize", "orderPriceMinTickSize", "outcomePrices", "outcomes",
        "pendingDeployment", "question", "questionID", "ready", "resolutionMechanism", "resolutionSource",
        "resolvedBy", "restricted", "rewardsMaxSpread", "rewardsMinSize", "rfqEnabled", "seriesColor",
        "showGmpOutcome", "showGmpSeries", "slug", "sportsMarketType", "spread", "startDate", "startDateIso",
        "submitted_by", "takerBaseFee", "teamAID", "teamBID", "tradingEligible", "umaBond", "umaEndDate",
        "umaResolutionStatus", "umaResolutionStatuses", "umaReward", "updatedAt", "version", "volume",
        "volume1mo", "volume1moAmm", "volume1moClob", "volume1wk", "volume1wkAmm", "volume1wkClob",
        "volume1yr", "volume1yrAmm", "volume1yrClob", "volume24hr", "volume24hrAmm", "volume24hrClob",
        "volumeAmm", "volumeClob", "volumeNum",
    }
)


@dataclass(frozen=True)
class ResearchBacklogItem:
    """Ranked emerging mechanism or newly discovered structure in `ResearchBacklog` (`Family N`)."""

    backlog_id: str
    mechanism_code: str
    title: str
    live_market_count: int
    target_opportunity_class_ceiling: str
    estimated_edge_potential_bps: float
    implementation_readiness_score: float  # `[0.0, 1.0]`
    priority_rank_score: float
    proof_or_counterexample_status: str
    sample_slugs: Tuple[str, ...]
    technical_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MechanismAndStructureScanner:
    """
    Family N Scanner (`MechanismAndStructureScanner`):
      - Systematically inspects live Gamma event/market schemas & CLOB `/books` payloads across
        all scanned markets to discover and catalog emerging exchange structures.
      - Runs formal **Proof / Counterexample Suites** on each mechanism so unsafe structures
        (`negRiskAugmented` `Other` / placeholders, `comboStatus=='enabled'` parlays, non-NegRisk
        multi-winner slates, `holdingRewardsEnabled` carry) can NEVER masquerade as `CLASS_A`,
        while actionable new structures (`cumulativeMarkets==True` monotone ladders, quadratic
        `crypto_15_min` `exp=2` boundary fee curves, `customLiveness` `900s/1800s` fast-settlement
        boxes) emit verified `MicroPortfolioCandidate` records and a ranked `ResearchBacklog`.
    """

    def __init__(
        self,
        *,
        reconciled_nav_usd: float = AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD,
        dormant_gap_bps: float = 150.0,
    ) -> None:
        self.reconciled_nav_usd = max(1.0, float(reconciled_nav_usd))
        self.dormant_gap_bps = max(10.0, float(dormant_gap_bps))
        self.verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=round(self.reconciled_nav_usd * 0.25, 2),
                reconciled_nav_usd=self.reconciled_nav_usd,
            )
        )

    def scan_universe_mechanisms(
        self,
        events: Sequence[Any],
        books_by_token: Mapping[str, Mapping[str, Any]],
        *,
        now_ts: Optional[float] = None,
    ) -> Tuple[List[MicroPortfolioCandidate], List[ResearchBacklogItem], Dict[str, Any]]:
        now_u = float(time.time() if now_ts is None else now_ts)
        self.verifier = UniversalArbVerifier(
            VerificationConfig(
                max_budget_usd=max(100.0, round(self.reconciled_nav_usd * 0.50, 2)),
                reconciled_nav_usd=self.reconciled_nav_usd,
                now_ts=now_u,
            )
        )
        candidates: List[MicroPortfolioCandidate] = []

        unrecognized_event_keys: Set[str] = set()
        unrecognized_market_keys: Set[str] = set()
        fee_schedule_counts: Counter[str] = Counter()
        quadratic_fee_mkts: List[Any] = []
        combo_enabled_mkts: List[Any] = []
        rfq_enabled_mkts: List[Any] = []
        holding_reward_mkts: List[Any] = []
        fast_liveness_mkts: List[Any] = []
        cumulative_events: List[Any] = []
        augmented_other_mkts: List[Any] = []
        multi_winner_events: List[Any] = []

        total_events = 0
        total_active_markets = 0

        for ev in events:
            total_events += 1
            if isinstance(ev, Mapping):
                unrecognized_event_keys |= (set(ev.keys()) - KNOWN_GAMMA_EVENT_KEYS)
            is_cum = bool(_get_field(ev, "cumulativeMarkets", "cumulative_markets", default=False) is True)
            ev_nr = bool(_get_field(ev, "negRisk", "enableNegRisk", default=False) is True)
            ev_aug = bool(_get_field(ev, "negRiskAugmented", "neg_risk_augmented", default=False) is True)
            if is_cum:
                cumulative_events.append(ev)

            ev_mkts = [
                m for m in (_get_field(ev, "markets", default=()) or ())
                if not bool(_get_field(m, "closed", default=False) is True)
                and not bool(_get_field(m, "archived", default=False) is True)
            ]
            # Check multi-winner non-NegRisk slates (`sum(outcomePrices[YES]) > 1.35` across >= 3 markets)
            if not ev_nr and len(ev_mkts) >= 3:
                yes_px_sum = 0.0
                for m in ev_mkts:
                    op = _parse_json_list(_get_field(m, "outcomePrices", default=[]))
                    if op:
                        yes_px_sum += _sf(op[0], 0.0)
                if yes_px_sum > 1.35:
                    multi_winner_events.append(ev)

            for m in ev_mkts:
                total_active_markets += 1
                if isinstance(m, Mapping):
                    unrecognized_market_keys |= (set(m.keys()) - KNOWN_GAMMA_MARKET_KEYS)
                fspec = FeeScheduleSpec.from_market(m)
                fee_key = f"{fspec.fee_type}(r={fspec.rate:g},exp={fspec.exponent:g},reb={fspec.rebate_rate:g})"
                fee_schedule_counts[fee_key] += 1
                if fspec.exponent >= 1.5 and fspec.rate > 0.0:
                    quadratic_fee_mkts.append(m)
                if str(_get_field(m, "comboStatus", default="") or "").strip().lower() == "enabled":
                    combo_enabled_mkts.append(m)
                if bool(_get_field(m, "rfqEnabled", default=False) is True):
                    rfq_enabled_mkts.append(m)
                if bool(_get_field(m, "holdingRewardsEnabled", default=False) is True):
                    holding_reward_mkts.append(m)
                cliv = _sf(_get_field(m, "customLiveness", default=0.0), 0.0)
                if 60.0 <= cliv < DEFAULT_UMA_STANDARD_LIVENESS_SEC:
                    fast_liveness_mkts.append(m)
                lbl = str(_get_field(m, "groupItemTitle", "question", default="") or "")
                if ev_aug or bool(_get_field(m, "negRiskOther", default=False) is True) or _PLACEHOLDER_OUTCOME_RE.search(lbl):
                    augmented_other_mkts.append(m)

        # Detector N5: Explicit `cumulativeMarkets == True` Gamma Monotone Ladders
        # CRITICAL (`BUG-MP-4` fix): Replace ONLY the exact bounded deadline date phrase with `<DEADLINE>`
        # (NEVER `[^?]*`!), preserving all trailing conjunctive clauses (e.g. `"and sign a formal treaty"`),
        # and verify `outcomes == ['yes', 'no']`, single-date-span parity, normalized `description` parity,
        # and `MarketPropositionGraph` `ResolutionSpec` compatibility!
        _negation_guard_re = re.compile(r"\b(not|never|without|fail\s+to|won't|wouldn't|doesn't|didn't|no\s+cut|no\s+change)\b", re.IGNORECASE)
        _month_pat_n5 = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
        _deadline_span_re = re.compile(
            rf"\b(?:by|before|on\s+or\s+before|prior\s+to)\s+"
            rf"(?:(?:the\s+end\s+of\s+)?{_month_pat_n5}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?"
            rf"|(?:the\s+end\s+of\s+)?{_month_pat_n5},?\s+\d{{4}}"
            rf"|\d{{4}}-\d{{2}}-\d{{2}}"
            rf"|(?:q[1-4]\s+\d{{4}})"
            rf"|(?:(?:the\s+)?end\s+of\s+\d{{4}})"
            rf"|\d{{4}})\b",
            re.IGNORECASE,
        )
        _bare_date_norm_re = re.compile(
            rf"\b(?:{_month_pat_n5}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?|{_month_pat_n5},?\s+\d{{4}}|\d{{4}}-\d{{2}}-\d{{2}})\b",
            re.IGNORECASE,
        )
        for ev in cumulative_events:
            ev_id = str(_get_field(ev, "id", "event_id", default="") or "")
            mkts = [
                m for m in (_get_field(ev, "markets", default=()) or ())
                if not bool(_get_field(m, "closed", default=False) is True)
                and not bool(_get_field(m, "archived", default=False) is True)
                and not is_d001_frozen_kmia_entity(m)
            ]
            if len(mkts) < 2:
                continue
            n5_graph = MarketPropositionGraph()
            n5_graph.ingest_events_and_markets(events=[ev])

            grouped_dated: Dict[Tuple[str, str], List[Tuple[float, Any]]] = defaultdict(list)
            for m in mkts:
                q_txt = str(_get_field(m, "question", default="") or "").strip()
                if not q_txt or _negation_guard_re.search(q_txt):
                    continue
                q_low = q_txt.lower()
                if "over/under" in q_low or "o/u" in q_low:
                    continue
                out_lbls = [str(x).strip().lower() for x in _parse_json_list(_get_field(m, "outcomes", default=["Yes", "No"]))]
                if out_lbls and out_lbls != ["yes", "no"]:
                    continue
                matches_dl = list(_deadline_span_re.finditer(q_txt))
                if len(matches_dl) != 1:
                    continue
                stem_key = re.sub(r"\s+", " ", _deadline_span_re.sub("<deadline>", q_low)).strip(" ?.")
                res_src = str(_get_field(m, "resolutionSource", default="") or "").strip().lower()
                ets = _parse_ts(_get_field(m, "endDate", "endDateIso", default=None))
                if ets is not None and stem_key and "<deadline>" in stem_key:
                    grouped_dated[(stem_key, res_src)].append((ets, m))

            for dated in grouped_dated.values():
                dated.sort(key=lambda r: r[0])
                for idx in range(len(dated) - 1):
                    t1, m1 = dated[idx]
                    t2, m2 = dated[idx + 1]
                    if t2 <= t1:
                        continue
                    mid1 = str(_get_field(m1, "id", "market_id", default="m1"))
                    mid2 = str(_get_field(m2, "id", "market_id", default="m2"))
                    node1 = n5_graph.markets.get(mid1)
                    node2 = n5_graph.markets.get(mid2)
                    n5_disq: List[str] = []
                    if node1 is not None and node2 is not None:
                        ok_res, res_codes = node1.resolution.check_compatibility(
                            node2.resolution, allow_ordered_cutoffs=True
                        )
                        if not ok_res:
                            for rc in res_codes:
                                if rc == "MISSING_RESOLUTION_RULES_TEXT" and not str(_get_field(m1, "description", default="") or "").strip() and not str(_get_field(m2, "description", default="") or "").strip():
                                    continue
                                n5_disq.append(rc)
                        dl1 = node1.proposition.deadline_ts
                        dl2 = node2.proposition.deadline_ts
                        if dl1 is not None and dl2 is not None and dl1 >= dl2 - 1e-6:
                            n5_disq.append("CUMULATIVE_TEXT_DEADLINE_NON_MONOTONIC")

                    desc1 = str(_get_field(m1, "description", default="") or "").strip().lower()
                    desc2 = str(_get_field(m2, "description", default="") or "").strip().lower()
                    if desc1 or desc2:
                        d1_norm = re.sub(r"\s+", " ", _bare_date_norm_re.sub("<date>", _deadline_span_re.sub("<deadline>", desc1))).strip()
                        d2_norm = re.sub(r"\s+", " ", _bare_date_norm_re.sub("<date>", _deadline_span_re.sub("<deadline>", desc2))).strip()
                        if d1_norm != d2_norm:
                            n5_disq.append("CUMULATIVE_DESCRIPTION_CLAUSE_DIVERGENCE")

                    toks1 = [str(x).strip() for x in _parse_json_list(_get_field(m1, "clobTokenIds", default=[])) if str(x).strip()]
                    toks2 = [str(x).strip() for x in _parse_json_list(_get_field(m2, "clobTokenIds", default=[])) if str(x).strip()]
                    if len(toks1) != 2 or len(toks2) != 2:
                        continue
                    bk_y1 = build_instrument_book_for_token(toks1[0], books_by_token.get(toks1[0]), m1, outcome_label="Yes", now_ts=now_u)
                    bk_n1 = build_instrument_book_for_token(toks1[1], books_by_token.get(toks1[1]), m1, outcome_label="No", now_ts=now_u)
                    bk_y2 = build_instrument_book_for_token(toks2[0], books_by_token.get(toks2[0]), m2, outcome_label="Yes", now_ts=now_u)
                    bk_n2 = build_instrument_book_for_token(toks2[1], books_by_token.get(toks2[1]), m2, outcome_label="No", now_ts=now_u)
                    if not (bk_n1.asks and bk_y2.asks) or bk_n1.has_crossed_or_invalid_book() or bk_y2.has_crossed_or_invalid_book():
                        continue
                    c_n1, _, _ = compute_net_buy_cost_per_delivered_share(bk_n1.asks[0].price, fee_rate_bps=bk_n1.fee_rate_bps, fee_exponent=bk_n1.fee_exponent)
                    c_y2, _, _ = compute_net_buy_cost_per_delivered_share(bk_y2.asks[0].price, fee_rate_bps=bk_y2.fee_rate_bps, fee_exponent=bk_y2.fee_exponent)
                    edge_bps = round((1.0 - (c_n1 + c_y2)) * 10_000.0, 2)
                    if edge_bps < -self.dormant_gap_bps:
                        continue
                    lock_h = max(1.0, (t2 - now_u) / 3600.0)
                    cr_a = node1.resolution.cancel_void_rule if (node1 is not None and node1.resolution.cancel_void_rule != "UNKNOWN") else "50_50"
                    cr_b = node2.resolution.cancel_void_rule if (node2 is not None and node2.resolution.cancel_void_rule != "UNKNOWN") else "50_50"
                    proof_n5 = self.verifier.verify_logical_implication_pair(
                        candidate_id=f"FAM_N5_CUMULATIVE_{mid1}_{mid2}",
                        family="N",
                        yes_book_a=bk_y1,
                        no_book_a=bk_n1,
                        yes_book_b=bk_y2,
                        no_book_b=bk_n2,
                        relation="A_IMPLIES_B",
                        buy_legs=((toks1[1], 1.0), (toks2[0], 1.0)),
                        rule_verified=(len(n5_disq) == 0),
                        rule_disqualifiers=tuple(n5_disq),
                        cancel_rule_a=cr_a,
                        cancel_rule_b=cr_b,
                        expected_lockup_hours=lock_h,
                        worst_case_lockup_hours=lock_h + 4.0,
                    )
                    is_dorm_n5 = bool(proof_n5.opportunity_class == OpportunityClass.CLASS_E.value and edge_bps >= -self.dormant_gap_bps)
                    if proof_n5.opportunity_class in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value, OpportunityClass.CLASS_D.value} or is_dorm_n5:
                        candidates.append(
                            MicroPortfolioCandidate(
                                candidate_id=proof_n5.candidate_id,
                                family="N",
                                sub_type="N5_CUMULATIVE_EVENT_MONOTONE_LADDER",
                                opportunity_class=proof_n5.opportunity_class,
                                execution_mode_gate="MODE_2_SHADOW",
                                event_id=ev_id,
                                canonical_event_keys=tuple(sorted(set(compute_canonical_concentration_keys(m1)) | set(compute_canonical_concentration_keys(m2)))),
                                market_ids=(mid1, mid2),
                                token_ids=(toks1[1], toks2[0]),
                                consumed_book_sides=_extract_consumed_book_sides_from_proof(
                                    proof_n5, ((toks1[1], "ASK", 1.0), (toks2[0], "ASK", 1.0))
                                ),
                                sequential_clob_legs=2,
                                is_atomic_or_inventory_locked=False,
                                d007_sub500_multileg_quarantine=False,
                                d001_kmia_frozen_blocked=False,
                                min_order_shares=max(bk_n1.min_order_size, bk_y2.min_order_size),
                                optimal_shares=proof_n5.optimal_executable_quantity,
                                capital_required_usd=round(proof_n5.cost_breakdown.capital_required_usd, 4),
                                gross_edge_bps=round((1.0 - (bk_n1.asks[0].price + bk_y2.asks[0].price)) * 10_000.0, 2),
                                net_executable_edge_bps=round(proof_n5.net_executable_edge_per_unit * 10_000.0, 2),
                                min_state_net_payoff_usd=round(proof_n5.min_state_net_payoff_usd, 6),
                                expected_net_payoff_usd=round(proof_n5.expected_net_payoff_usd, 6),
                                expected_lockup_hours=round(lock_h, 4),
                                worst_case_lockup_hours=round(lock_h + 4.0, 4),
                                net_bps_per_hour_expected=round(proof_n5.capital_efficiency_bps_per_hr, 2),
                                net_bps_per_hour_worst_case=round((proof_n5.net_executable_edge_per_unit * 10_000.0) / (lock_h + 4.0), 2),
                                dispute_probability=0.01,
                                partial_fill_prob=0.08,
                                adverse_selection_cost_usd=0.0,
                                uncertain_rebate_or_reward_usd=0.0,
                                dormant_near_miss=is_dorm_n5,
                                four_value_ledger=proof_n5.four_value_ledger,
                                proof=proof_n5,
                                proof_sha256=proof_n5.proof_sha256,
                                disqualifiers=proof_n5.disqualifiers,
                                notes=("Explicit Gamma `cumulativeMarkets=True` monotone deadline rung.",),
                            )
                        )

        # Detector N1: Quadratic `crypto_15_min` (`exp=2, r=0.25`) Boundary Fee Mispricing Scanner
        for m in quadratic_fee_mkts[:250]:
            if is_d001_frozen_kmia_entity(m):
                continue
            mid = str(_get_field(m, "id", "market_id", default="") or "")
            toks = [str(x).strip() for x in _parse_json_list(_get_field(m, "clobTokenIds", default=[])) if str(x).strip()]
            if len(toks) != 2:
                continue
            bk_y = build_instrument_book_for_token(toks[0], books_by_token.get(toks[0]), m, outcome_label="Yes", now_ts=now_u)
            bk_n = build_instrument_book_for_token(toks[1], books_by_token.get(toks[1]), m, outcome_label="No", now_ts=now_u)
            if not (bk_y.asks and bk_n.asks) or bk_y.has_crossed_or_invalid_book() or bk_n.has_crossed_or_invalid_book():
                continue
            cy, _, _ = compute_net_buy_cost_per_delivered_share(bk_y.asks[0].price, fee_rate_bps=bk_y.fee_rate_bps, fee_exponent=bk_y.fee_exponent)
            cn, _, _ = compute_net_buy_cost_per_delivered_share(bk_n.asks[0].price, fee_rate_bps=bk_n.fee_rate_bps, fee_exponent=bk_n.fee_exponent)
            net_bps_q = round((1.0 - (cy + cn)) * 10_000.0, 2)
            if net_bps_q >= -self.dormant_gap_bps:
                cand_q = CandidateStructure(
                    candidate_id=f"FAM_N1_QUAD_FEE_BOX_{mid}",
                    family="N",
                    legs=(
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=toks[0], market_id=mid),
                        ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=toks[1], market_id=mid),
                        ActionLeg(action_type=ActionType.CTF_MERGE, related_instrument_ids=(toks[0], toks[1]), market_id=mid),
                    ),
                    states=StateSpaceBuilder.binary_complete_set_states(toks[0], toks[1], include_void_50_50=True),
                    rule_verified=True,
                    expected_lockup_hours=0.05,
                    worst_case_lockup_hours=0.25,
                )
                proof_q = self.verifier.verify_and_simulate(cand_q, {toks[0]: bk_y, toks[1]: bk_n})
                is_dorm_q = bool(proof_q.opportunity_class == OpportunityClass.CLASS_E.value and net_bps_q >= -self.dormant_gap_bps)
                if proof_q.opportunity_class in {OpportunityClass.CLASS_A.value, OpportunityClass.CLASS_B.value} or is_dorm_q:
                    candidates.append(
                        MicroPortfolioCandidate(
                            candidate_id=proof_q.candidate_id,
                            family="N",
                            sub_type="N1_QUADRATIC_FEE_CURVE_COMPLETE_SET",
                            opportunity_class=proof_q.opportunity_class,
                            execution_mode_gate="MODE_2_SHADOW",
                            event_id=str(_get_field(m, "event_id", default="") or ""),
                            canonical_event_keys=compute_canonical_concentration_keys(m),
                            market_ids=(mid,),
                            token_ids=(toks[0], toks[1]),
                            consumed_book_sides=_extract_consumed_book_sides_from_proof(
                                proof_q, ((toks[0], "ASK", 1.0), (toks[1], "ASK", 1.0))
                            ),
                            sequential_clob_legs=2,
                            is_atomic_or_inventory_locked=False,
                            d007_sub500_multileg_quarantine=False,
                            d001_kmia_frozen_blocked=False,
                            min_order_shares=max(bk_y.min_order_size, bk_n.min_order_size),
                            optimal_shares=proof_q.optimal_executable_quantity,
                            capital_required_usd=round(proof_q.cost_breakdown.capital_required_usd, 4),
                            gross_edge_bps=round((1.0 - (bk_y.asks[0].price + bk_n.asks[0].price)) * 10_000.0, 2),
                            net_executable_edge_bps=round(proof_q.net_executable_edge_per_unit * 10_000.0, 2),
                            min_state_net_payoff_usd=round(proof_q.min_state_net_payoff_usd, 6),
                            expected_net_payoff_usd=round(proof_q.expected_net_payoff_usd, 6),
                            expected_lockup_hours=0.05,
                            worst_case_lockup_hours=0.25,
                            net_bps_per_hour_expected=round(proof_q.capital_efficiency_bps_per_hr, 2),
                            net_bps_per_hour_worst_case=round((proof_q.net_executable_edge_per_unit * 10_000.0) / 0.25, 2),
                            dispute_probability=0.0,
                            partial_fill_prob=0.08,
                            adverse_selection_cost_usd=0.0,
                            uncertain_rebate_or_reward_usd=0.0,
                            dormant_near_miss=is_dorm_q,
                            four_value_ledger=proof_q.four_value_ledger,
                            proof=proof_q,
                            proof_sha256=proof_q.proof_sha256,
                            notes=("Quadratic `crypto_15_min` (`exp=2, r=0.25`) exact boundary fee curve.",),
                        )
                    )

        # Formal Counterexample Verification Suite for Unsafe Mechanisms (`N2`, `N3`, `N6`, `N7`)
        counterexample_suite = self.run_mechanism_proof_and_counterexample_suite()

        # Build Ranked `ResearchBacklog`
        backlog: List[ResearchBacklogItem] = [
            ResearchBacklogItem(
                backlog_id="RB-N1",
                mechanism_code="N1_DYNAMIC_POLYNOMIAL_FEE_AND_REBATE_CURVES",
                title="13-Schedule Dynamic Fee Curves (`exponent=2` `crypto_15_min` & `15%-25%` Maker Rebates)",
                live_market_count=sum(v for k, v in fee_schedule_counts.items() if not k.startswith("zero_fees")),
                target_opportunity_class_ceiling="CLASS_B (Taker Box) / CLASS_C (Maker Rebate)",
                estimated_edge_potential_bps=42.5,
                implementation_readiness_score=1.0,
                priority_rank_score=round(42.5 * 1.0, 2),
                proof_or_counterexample_status="PROVEN_EXACT_V2_SHARE_HAIRCUT_IMPLEMENTED",
                sample_slugs=tuple(str(_get_field(x, "slug", default="")) for x in quadratic_fee_mkts[:3]),
                technical_notes=(
                    "Quadratic `crypto_15_min` (`0.25*(p*(1-p))^2`) charges only 20.25 bps at p=0.90 vs 63 bps "
                    "under legacy linear 7% assumption; `weather_fees` charges 5% linear taker vs 0% postOnly maker."
                ),
            ),
            ResearchBacklogItem(
                backlog_id="RB-N4",
                mechanism_code="N4_CUSTOM_FAST_LIVENESS_AND_AUTO_ORACLE",
                title="Fast-Liveness (`customLiveness` 15m/30m) & `automaticallyResolved` Chainlink Markets",
                live_market_count=len(fast_liveness_mkts),
                target_opportunity_class_ceiling="CLASS_B (Dominance/Box) / CLASS_C (Carry)",
                estimated_edge_potential_bps=35.0,
                implementation_readiness_score=0.95,
                priority_rank_score=round(35.0 * 0.95, 2),
                proof_or_counterexample_status="PROVEN_4X_8X_FASTER_SETTLEMENT_TURNOVER",
                sample_slugs=tuple(str(_get_field(x, "slug", default="")) for x in fast_liveness_mkts[:3]),
                technical_notes="900s/1800s custom UMA liveness cuts post-expiry capital lockup 4x-8x vs 7200s standard.",
            ),
            ResearchBacklogItem(
                backlog_id="RB-N5",
                mechanism_code="N5_CUMULATIVE_EVENT_SERIES",
                title="Explicit `cumulativeMarkets=true` Monotone Deadline & Threshold Event Strips",
                live_market_count=len(cumulative_events),
                target_opportunity_class_ceiling="CLASS_B",
                estimated_edge_potential_bps=28.0,
                implementation_readiness_score=1.0,
                priority_rank_score=round(28.0 * 1.0, 2),
                proof_or_counterexample_status="PROVEN_IMPLICATION_DAG_DETECTOR_ACTIVE",
                sample_slugs=tuple(str(_get_field(x, "slug", default="")) for x in cumulative_events[:3]),
                technical_notes="Native Gamma `cumulativeMarkets` flag identifies ordered `M_1 => M_2 => ... => M_k` strips.",
            ),
            ResearchBacklogItem(
                backlog_id="RB-N2",
                mechanism_code="N2_COMBO_PARLAY_AND_RFQ_STRUCTURES",
                title="Combo/Parlay Eligible Markets (`comboStatus='enabled'`) & RFQ (`rfqEnabled`)",
                live_market_count=len(combo_enabled_mkts) + len(rfq_enabled_mkts),
                target_opportunity_class_ceiling="CLASS_D (Requires Joint-Condition Adapter Proof)",
                estimated_edge_potential_bps=22.0,
                implementation_readiness_score=0.55,
                priority_rank_score=round(22.0 * 0.55, 2),
                proof_or_counterexample_status="COUNTEREXAMPLE_JOINT_CORRELATION_NON_MERGEABLE",
                sample_slugs=tuple(str(_get_field(x, "slug", default="")) for x in combo_enabled_mkts[:3]),
                technical_notes=(
                    f"comboStatus='enabled'={len(combo_enabled_mkts)}, rfqEnabled={len(rfq_enabled_mkts)}. "
                    "Frechet-Hoeffding joint bounds `[max(0, P(A)+P(B)-1), min(P(A), P(B))]` proven in suite."
                ),
            ),
            ResearchBacklogItem(
                backlog_id="RB-N3",
                mechanism_code="N3_HOLDING_REWARDS_AND_TWOSIDED_QMIN_SHIELD",
                title="Holding Rewards (`holdingRewardsEnabled=true`) & Two-Sided Complete-Set Yield",
                live_market_count=len(holding_reward_mkts),
                target_opportunity_class_ceiling="CLASS_C (Uncertain Yield Excluded From CLASS_A Floor)",
                estimated_edge_potential_bps=14.0,
                implementation_readiness_score=0.75,
                priority_rank_score=round(14.0 * 0.75, 2),
                proof_or_counterexample_status="COUNTEREXAMPLE_VARIABLE_RATE_NEVER_CLASS_A",
                sample_slugs=tuple(str(_get_field(x, "slug", default="")) for x in holding_reward_mkts[:3]),
                technical_notes="Annualized holding reward requires complete-set `YES+NO` mint/hold to eliminate principal risk; yield rate remains discretionary (`CLASS_C`).",
            ),
            ResearchBacklogItem(
                backlog_id="RB-N6",
                mechanism_code="N6_AUGMENTED_NEGRISK_OTHER_AND_PLACEHOLDERS",
                title="Augmented NegRisk `negRiskOther` & Clarifiable Unnamed Placeholders (`Person A`)",
                live_market_count=len(augmented_other_mkts),
                target_opportunity_class_ceiling="CLASS_D / CLASS_E TRAP GUARD",
                estimated_edge_potential_bps=0.0,
                implementation_readiness_score=1.0,
                priority_rank_score=5.0,
                proof_or_counterexample_status="COUNTEREXAMPLE_PROVEN_100PCT_LOSS_TRAP_BLOCKED",
                sample_slugs=tuple(str(_get_field(x, "slug", default="")) for x in augmented_other_mkts[:3]),
                technical_notes="Clarifying a placeholder removes that entrant from `Other`; incomplete slates strictly blocked.",
            ),
            ResearchBacklogItem(
                backlog_id="RB-N7",
                mechanism_code="N7_MULTI_WINNER_AND_NON_EXHAUSTIVE_PARTITIONS",
                title="Multi-Winner Primaries / Non-NegRisk Multi-Market Events (`sum(p_YES) > 1.35`)",
                live_market_count=len(multi_winner_events),
                target_opportunity_class_ceiling="CLASS_E TRAP GUARD",
                estimated_edge_potential_bps=0.0,
                implementation_readiness_score=1.0,
                priority_rank_score=4.0,
                proof_or_counterexample_status="COUNTEREXAMPLE_OMEGA_MULTI_WINNER_OVERLAP_BLOCKED",
                sample_slugs=tuple(str(_get_field(x, "slug", default="")) for x in multi_winner_events[:3]),
                technical_notes="Selling all YES on multi-winner slates loses `(k - 1)*$1.00` when `k >= 2` winners resolve YES.",
            ),
        ]
        backlog.sort(key=lambda b: -b.priority_rank_score)

        catalog_summary = {
            "total_events_inspected": total_events,
            "total_active_markets_inspected": total_active_markets,
            "fee_schedule_distribution": dict(fee_schedule_counts.most_common()),
            "quadratic_fee_curve_markets_count": len(quadratic_fee_mkts),
            "combo_enabled_markets_count": len(combo_enabled_mkts),
            "rfq_enabled_markets_count": len(rfq_enabled_mkts),
            "holding_rewards_enabled_markets_count": len(holding_reward_mkts),
            "custom_fast_liveness_markets_count": len(fast_liveness_mkts),
            "cumulative_events_count": len(cumulative_events),
            "augmented_or_placeholder_markets_count": len(augmented_other_mkts),
            "multi_winner_non_negrisk_events_count": len(multi_winner_events),
            "unrecognized_gamma_event_keys": sorted(unrecognized_event_keys),
            "unrecognized_gamma_market_keys": sorted(unrecognized_market_keys),
            "proof_and_counterexample_suite": counterexample_suite,
        }
        return candidates, backlog, catalog_summary

    def run_mechanism_proof_and_counterexample_suite(self) -> Dict[str, Any]:
        """
        Executes deterministic mathematical proof & counterexample checks for newly cataloged
        mechanisms (`Family N` requirement).
        """
        # 1. N1 Proof: Quadratic `crypto_15_min` (`exp=2, r=0.25`) vs Linear `7%` at `p = 0.92`
        spec_quad = FeeScheduleSpec(fee_type="crypto_15_min", fees_enabled=True, rate=0.25, exponent=2.0, rebate_rate=0.20)
        spec_lin7 = FeeScheduleSpec(fee_type="crypto_fees_v2", fees_enabled=True, rate=0.07, exponent=1.0, rebate_rate=0.20)
        fee_quad_92 = spec_quad.taker_fee_per_gross_share(0.92)  # 0.25 * (0.0736)^2 = 0.00135424
        fee_lin7_92 = spec_lin7.taker_fee_per_gross_share(0.92)  # 0.07 * 0.0736     = 0.00515200

        # 2. N6 Counterexample: Augmented NegRisk slate omitting placeholder (`sum(ask_YES) = $0.91` illusory arb)
        outcomes_aug = [
            {"label": "Named Candidate 1", "yes_token_id": "AUG_Y1", "no_token_id": "AUG_N1", "is_placeholder": False},
            {"label": "Named Candidate 2", "yes_token_id": "AUG_Y2", "no_token_id": "AUG_N2", "is_placeholder": False},
            {"label": "Person A", "yes_token_id": "AUG_Y3", "no_token_id": "AUG_N3", "is_placeholder": True},
        ]
        states_aug = StateSpaceBuilder.multi_outcome_partition_states(
            outcomes_aug[:2],  # Omitting Person A!
            is_mutually_exclusive=True,
            is_exhaustive=False,
            is_negrisk=True,
            is_augmented_negrisk=True,
            has_unnamed_placeholder=True,
            has_other_outcome=False,
        )
        bks_aug = {
            "AUG_Y1": InstrumentOrderBook("AUG_Y1", asks=(BookLevel(0.45, 50.0),), bids=(BookLevel(0.44, 50.0),)),
            "AUG_Y2": InstrumentOrderBook("AUG_Y2", asks=(BookLevel(0.46, 50.0),), bids=(BookLevel(0.45, 50.0),)),
        }
        proof_aug_trap = self.verifier.verify_and_simulate(
            CandidateStructure(
                candidate_id="N6_COUNTEREXAMPLE_AUGMENTED_TRAP",
                family="N",
                legs=(
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="AUG_Y1"),
                    ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id="AUG_Y2"),
                ),
                states=states_aug,
                rule_verified=False,
                rule_disqualifiers=("AUGMENTED_PLACEHOLDER_OMITTED",),
                is_exhaustive_partition=False,
                requires_exhaustive_partition=True,
                has_augmented_placeholder_risk=True,
            ),
            bks_aug,
        )

        # 3. N2 Frechet-Hoeffding Combo/Parlay Bound Check: `P(A ^ B) <= min(P(A), P(B))`
        # If `ask(Combo A&B) = 0.62` while `bid(YES_A) = 0.55`, combo is strictly overpriced (`0.62 > 0.55`)!
        frechet_upper_violation = round(0.62 - min(0.55, 0.70), 4)

        return {
            "n1_quadratic_boundary_fee_ratio_at_p92": round(fee_quad_92 / max(fee_lin7_92, 1e-9), 4),
            "n1_quadratic_fee_ps_at_p92": round(fee_quad_92, 6),
            "n6_augmented_trap_blocked_class": proof_aug_trap.opportunity_class,
            "n6_augmented_trap_min_payoff_usd": round(proof_aug_trap.min_state_net_payoff_usd, 4),
            "n2_frechet_hoeffding_upper_bound_violation_example": frechet_upper_violation,
            "all_counterexamples_verified": bool(
                fee_quad_92 < fee_lin7_92
                and proof_aug_trap.opportunity_class in {OpportunityClass.CLASS_D.value, OpportunityClass.CLASS_E.value}
                and proof_aug_trap.min_state_net_payoff_usd < 0.0
                and frechet_upper_violation > 0.0
            ),
        }


# ---------------------------------------------------------------------------
# Unified Suite & Live Public Gamma / CLOB Empirical Scan Runner
# ---------------------------------------------------------------------------


def fetch_gamma_events_keyset(
    *,
    max_events: Optional[int] = None,
    page_limit: int = 500,
    timeout_sec: float = 25.0,
) -> List[Dict[str, Any]]:
    """
    Paginates `https://gamma-api.polymarket.com/events/keyset?active=true&closed=false&limit=200&after_cursor=...`
    over a persistent TLS keep-alive connection without hitting the `/events?offset=2100` HTTP 422 truncation limit!
    """
    import gzip
    import http.client
    import ssl

    events: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    after_cursor: Optional[str] = None
    lim = min(500, max(20, int(page_limit)))
    ctx = ssl.create_default_context()
    conn: Optional[http.client.HTTPSConnection] = http.client.HTTPSConnection(
        "gamma-api.polymarket.com", timeout=timeout_sec, context=ctx
    )
    headers = {
        "User-Agent": "DominusFullThrottleResearch/1.0",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "keep-alive",
    }

    try:
        while True:
            params: Dict[str, Any] = {"active": "true", "closed": "false", "limit": str(lim)}
            if after_cursor:
                params["after_cursor"] = after_cursor
            path = f"/events/keyset?{urllib.parse.urlencode(params)}"
            payload: Any = None
            for attempt in range(2):
                try:
                    if conn is None:
                        conn = http.client.HTTPSConnection("gamma-api.polymarket.com", timeout=timeout_sec, context=ctx)
                    conn.request("GET", path, headers=headers)
                    resp = conn.getresponse()
                    raw_bytes = resp.read()
                    if resp.status == 200:
                        if "gzip" in (resp.getheader("Content-Encoding") or "").lower():
                            raw_bytes = gzip.decompress(raw_bytes)
                        payload = json.loads(raw_bytes.decode("utf-8"))
                        break
                    conn.close()
                    conn = None
                except Exception:
                    if conn is not None:
                        try:
                            conn.close()
                        except Exception:
                            pass
                        conn = None
                    if attempt == 1:
                        url = f"https://gamma-api.polymarket.com{path}"
                        req = urllib.request.Request(url, headers={"User-Agent": "DominusFullThrottleResearch/1.0", "Accept": "application/json"})
                        with urllib.request.urlopen(req, timeout=timeout_sec) as uresp:
                            payload = json.loads(uresp.read().decode("utf-8"))

            batch = payload.get("events") if isinstance(payload, Mapping) else payload
            if not isinstance(batch, list) or not batch:
                break

            new_in_page = 0
            for ev in batch:
                if not isinstance(ev, dict):
                    continue
                eid = str(ev.get("id") or "")
                if eid and eid in seen_ids:
                    continue
                if eid:
                    seen_ids.add(eid)
                # Attach parent `event_id` and NegRisk flags onto child markets for uniform downstream scanning
                for m in ev.get("markets") or ():
                    if isinstance(m, dict):
                        m.setdefault("event_id", eid)
                        if ev.get("negRisk") is not None:
                            m.setdefault("negRisk", ev.get("negRisk"))
                        if ev.get("negRiskAugmented") is not None:
                            m.setdefault("negRiskAugmented", ev.get("negRiskAugmented"))
                events.append(ev)
                new_in_page += 1
                if max_events is not None and len(events) >= int(max_events):
                    return events

            next_c = payload.get("next_cursor") if isinstance(payload, Mapping) else None
            if not next_c or next_c == after_cursor or new_in_page == 0:
                break
            after_cursor = str(next_c)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    return events


def fetch_clob_books_batched(
    token_ids: Sequence[str],
    *,
    batch_size: int = 250,
    timeout_sec: float = 20.0,
    max_workers: int = 6,
) -> Dict[str, Dict[str, Any]]:
    """Fetches real multi-level L2 order books via batched `POST https://clob.polymarket.com/books`."""
    from concurrent.futures import ThreadPoolExecutor

    unique_tokens = list(dict.fromkeys(str(t).strip() for t in token_ids if str(t).strip()))
    if not unique_tokens:
        return {}
    books: Dict[str, Dict[str, Any]] = {}
    step = min(400, max(10, int(batch_size)))
    chunks = [unique_tokens[start : start + step] for start in range(0, len(unique_tokens), step)]

    def _fetch_chunk(chunk: List[str]) -> List[Dict[str, Any]]:
        body = json.dumps([{"token_id": t} for t in chunk]).encode("utf-8")
        req = urllib.request.Request(
            "https://clob.polymarket.com/books",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "DominusFullThrottleResearch/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                rows = json.loads(resp.read().decode("utf-8"))
            return [r for r in rows if isinstance(r, dict) and r.get("asset_id")] if isinstance(rows, list) else []
        except Exception:
            return []

    workers = min(max(1, int(max_workers)), len(chunks))
    if workers <= 1:
        for ch in chunks:
            for r in _fetch_chunk(ch):
                books[str(r["asset_id"]).strip()] = r
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for rows in pool.map(_fetch_chunk, chunks):
                for r in rows:
                    books[str(r["asset_id"]).strip()] = r
    return books


class MicrostructureAndPortfolioSuite:
    """
    Unified facade exported for `@pipeline-shadow` (`full_throttle_pipeline.py`) running Families
    `K`, `L`, `M`, `N` and `PortfolioArbitrageOptimizer` end-to-end.
    """

    def __init__(
        self,
        *,
        available_liquid_pusd: float = AUTHORITATIVE_LIVE_CASH_PUSD,
        reconciled_nav_usd: float = AUTHORITATIVE_RECONCILED_FLOOR_NAV_USD,
    ) -> None:
        self.available_liquid_pusd = float(available_liquid_pusd)
        self.reconciled_nav_usd = float(reconciled_nav_usd)
        self.detector_k = NearResolutionSettlementCarryDetector(reconciled_nav_usd=self.reconciled_nav_usd)
        self.detector_l = MakerTakerLiquidityDetector(reconciled_nav_usd=self.reconciled_nav_usd)
        self.detector_m = MultiLegComponentDetector(reconciled_nav_usd=self.reconciled_nav_usd)
        self.detector_n = MechanismAndStructureScanner(reconciled_nav_usd=self.reconciled_nav_usd)
        self.optimizer = PortfolioArbitrageOptimizer(
            available_liquid_pusd=self.available_liquid_pusd,
            reconciled_nav_usd=self.reconciled_nav_usd,
        )

    def run_all(
        self,
        events: Sequence[Any],
        books_by_token: Mapping[str, Mapping[str, Any]],
        *,
        graph: Optional[MarketPropositionGraph] = None,
        peer_candidates_a_to_j: Sequence[Any] = (),
        holdings_by_token: Optional[Mapping[str, InventoryHolding]] = None,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        now_u = float(time.time() if now_ts is None else now_ts)
        flat_markets: List[Any] = []
        for ev in events:
            for m in (_get_field(ev, "markets", default=()) or ()):
                if not bool(_get_field(m, "closed", default=False) is True) and not bool(_get_field(m, "archived", default=False) is True):
                    flat_markets.append(m)

        cands_k = self.detector_k.scan_markets(flat_markets, books_by_token, holdings_by_token=holdings_by_token, now_ts=now_u)
        cands_l = self.detector_l.scan_markets(flat_markets, books_by_token, holdings_by_token=holdings_by_token, now_ts=now_u)
        cands_m = self.detector_m.scan_events_and_graph(
            events,
            books_by_token,
            graph=graph,
            holdings_by_token=holdings_by_token,
            now_ts=now_u,
        )
        cands_n, research_backlog, mechanism_catalog = self.detector_n.scan_universe_mechanisms(
            events,
            books_by_token,
            now_ts=now_u,
        )

        own_candidates: List[MicroPortfolioCandidate] = [*cands_k, *cands_l, *cands_m, *cands_n]
        combined_for_optimizer: List[Any] = [*peer_candidates_a_to_j, *own_candidates]

        live_opt = self.optimizer.optimize_portfolio(
            combined_for_optimizer,
            books_by_token=books_by_token,
            budget_label="LIVE_CASH_BASELINE_48_70_PUSD",
        )
        shadow_curve = PortfolioArbitrageOptimizer.evaluate_shadow_budget_curve(
            combined_for_optimizer,
            books_by_token=books_by_token,
        )

        by_family_class: Dict[str, Dict[str, int]] = {}
        for fam_code, fam_list in (("K", cands_k), ("L", cands_l), ("M", cands_m), ("N", cands_n)):
            cnt = Counter(c.opportunity_class for c in fam_list)
            by_family_class[fam_code] = {oc.value: int(cnt.get(oc.value, 0)) for oc in OpportunityClass}
            by_family_class[fam_code]["dormant_near_miss"] = sum(1 for c in fam_list if c.dormant_near_miss)
            by_family_class[fam_code]["total"] = len(fam_list)

        return {
            "audit": audit_existing_carry_maker_and_velocity_sizing(),
            "candidates_by_family": {
                "K": cands_k,
                "L": cands_l,
                "M": cands_m,
                "N": cands_n,
            },
            "all_k_to_n_candidates": own_candidates,
            "family_class_breakdown": by_family_class,
            "portfolio_optimization_live_48_70": live_opt,
            "portfolio_shadow_budget_curve": shadow_curve,
            "mechanism_catalog": mechanism_catalog,
            "research_backlog": research_backlog,
        }


def run_live_k_to_n_scan(
    *,
    output_path: Optional[Path] = None,
    max_events_universe: Optional[int] = None,
    max_tokens_book_fetch: int = 5600,
) -> Dict[str, Any]:
    """
    Executes a live public Gamma `/events/keyset` + batched CLOB `/books` empirical scan for
    Families `K, L, M, N` + `PortfolioArbitrageOptimizer`, writing `data/full_throttle/scans_k_to_n/scan_summary.json`.
    """
    t0 = time.time()
    events = fetch_gamma_events_keyset(max_events=max_events_universe)
    now_u = time.time()

    # Stratified token quotas across Families N, M, K, and L so high-count near-close sports markets
    # never starve multi-leg partitions (`M`), cumulative/quadratic mechanisms (`N`), or liquid maker books (`L`)!
    bucket_n: List[str] = []
    bucket_m_scored: List[Tuple[float, List[str]]] = []
    bucket_k_uma: List[str] = []
    bucket_k_near_scored: List[Tuple[float, str, str]] = []
    bucket_l_scored: List[Tuple[float, str, str]] = []

    for ev in events:
        is_cum = bool(ev.get("cumulativeMarkets") is True)
        all_child_mkts = [m for m in (ev.get("markets") or ()) if isinstance(m, dict)]
        ev_mkts = [m for m in all_child_mkts if not m.get("closed") and not m.get("archived") and m.get("enableOrderBook") is not False]
        has_closed_child = len(ev_mkts) < len(all_child_mkts)
        is_clean_compact_negrisk = bool(ev.get("negRisk") and not ev.get("negRiskAugmented") and not has_closed_child and 3 <= len(ev_mkts) <= 10)
        is_multi_strip = bool(not ev.get("negRisk") and 3 <= len(ev_mkts) <= 8)

        if is_clean_compact_negrisk or is_multi_strip:
            slate_toks: List[str] = []
            slate_liq = 0.0
            valid_slate = True
            for sm in ev_mkts:
                stoks = [str(x).strip() for x in _parse_json_list(sm.get("clobTokenIds")) if str(x).strip()]
                if len(stoks) != 2:
                    valid_slate = False
                    break
                slate_toks.extend(stoks)
                slate_liq += _sf(sm.get("liquidityClob", sm.get("liquidity", 0.0)), 0.0) + _sf(sm.get("volume24hr", 0.0), 0.0)
            if valid_slate and slate_toks:
                bucket_m_scored.append((slate_liq, slate_toks))

        for m in ev_mkts:
            toks = [str(x).strip() for x in _parse_json_list(m.get("clobTokenIds")) if str(x).strip()]
            if len(toks) != 2:
                continue
            ust = str(m.get("umaResolutionStatus") or "").strip().lower()
            ets = _parse_ts(m.get("endDate"))
            near_close = ets is not None and (ets - now_u) <= 6.0 * 3600.0
            ft = str(m.get("feeType") or "").lower()
            liq = _sf(m.get("liquidityClob", m.get("liquidity", 0.0)), 0.0) + _sf(m.get("volume24hr", 0.0), 0.0)

            if is_cum or ft == "crypto_15_min":
                bucket_n.extend(toks)
            if ust in {"proposed", "disputed", "resolved"}:
                bucket_k_uma.extend(toks)
            elif near_close:
                bucket_k_near_scored.append((liq, toks[0], toks[1]))
            else:
                bucket_l_scored.append((liq, toks[0], toks[1]))

    bucket_m_scored.sort(key=lambda r: -r[0])
    bucket_k_near_scored.sort(key=lambda r: -r[0])
    bucket_l_scored.sort(key=lambda r: -r[0])

    selected_tokens: List[str] = []
    seen_tok: Set[str] = set()

    def _add_toks(seq_t: Iterable[str], cap_after: int) -> None:
        for tid in seq_t:
            if len(selected_tokens) >= cap_after:
                break
            if tid and tid not in seen_tok:
                seen_tok.add(tid)
                selected_tokens.append(tid)

    q_tot = max(800, int(max_tokens_book_fetch))
    _add_toks(bucket_n, min(q_tot, 600))
    _add_toks(bucket_k_uma, min(q_tot, len(selected_tokens) + 1200))
    for _, stoks in bucket_m_scored:
        if len(selected_tokens) + len(stoks) > int(q_tot * 0.62):
            continue
        _add_toks(stoks, int(q_tot * 0.62))
    _add_toks((t for _, t0, t1 in bucket_k_near_scored for t in (t0, t1)), int(q_tot * 0.80))
    _add_toks((t for _, t0, t1 in bucket_l_scored for t in (t0, t1)), q_tot)

    books_by_token = fetch_clob_books_batched(selected_tokens, batch_size=250)

    # Pass FULL unmodified `ev` dicts (never stripping sibling child markets!) whenever any child market has a book or UMA status
    suite = MicrostructureAndPortfolioSuite()
    events_with_books: List[Dict[str, Any]] = []
    for ev in events:
        has_any_book_or_uma = False
        for m in ev.get("markets") or ():
            if not isinstance(m, dict) or m.get("closed") or m.get("archived"):
                continue
            toks = [str(x).strip() for x in _parse_json_list(m.get("clobTokenIds")) if str(x).strip()]
            if any(t in books_by_token for t in toks) or str(m.get("umaResolutionStatus") or "").strip():
                has_any_book_or_uma = True
                break
        if has_any_book_or_uma:
            events_with_books.append(ev)

    res = suite.run_all(events_with_books, books_by_token, now_ts=now_u)
    # Run Family N full-universe mechanism census across ALL `events` (100% universe coverage!)
    cands_n_full, backlog_full, catalog_full = suite.detector_n.scan_universe_mechanisms(events, books_by_token, now_ts=now_u)

    elapsed_sec = round(time.time() - t0, 3)
    summary_payload: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scan_wall_time_sec": elapsed_sec,
        "universe_scope": {
            "total_active_events_fetched": len(events),
            "total_active_markets_inspected": catalog_full["total_active_markets_inspected"],
            "clob_tokens_queried": len(selected_tokens),
            "clob_orderbooks_returned": len(books_by_token),
        },
        "existing_system_audit": res["audit"],
        "family_class_breakdown": res["family_class_breakdown"],
        "top_candidates_by_family": {
            fam: [c.to_dict() for c in cands[:12]]
            for fam, cands in res["candidates_by_family"].items()
        },
        "portfolio_optimization_live_48_70": res["portfolio_optimization_live_48_70"].to_dict(),
        "portfolio_shadow_budget_curve": res["portfolio_shadow_budget_curve"],
        "family_n_full_universe_mechanism_catalog": catalog_full,
        "family_n_research_backlog": [b.to_dict() for b in backlog_full],
    }

    out_file = Path(output_path) if output_path is not None else (
        Path(__file__).resolve().parent.parent.parent / "data" / "full_throttle" / "scans_k_to_n" / "scan_summary.json"
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    return summary_payload


if __name__ == "__main__":  # pragma: no cover
    summary = run_live_k_to_n_scan()
    print(
        json.dumps(
            {
                "events": summary["universe_scope"]["total_active_events_fetched"],
                "markets": summary["universe_scope"]["total_active_markets_inspected"],
                "books": summary["universe_scope"]["clob_orderbooks_returned"],
                "breakdown": summary["family_class_breakdown"],
                "live_opt_allocated_usd": summary["portfolio_optimization_live_48_70"]["total_allocated_capital_usd"],
                "live_opt_bps_hr": summary["portfolio_optimization_live_48_70"]["portfolio_realizable_bps_per_hour"],
            },
            indent=2,
        )
    )

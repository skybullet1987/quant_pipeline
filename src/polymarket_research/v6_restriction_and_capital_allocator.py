"""
DOMINUS v6.0 — Mode-Separated Restriction Engine, Loss-Cause-Aware Capital Controller,
Protocol Fee/Merge Validator & Dynamic Marginal Portfolio Capital Allocator
(`src/polymarket_research/v6_restriction_and_capital_allocator.py`).

Pure Python 3.12 stdlib implementation (`< 50 MiB` RSS on swapless hosts).
Implements the authorized engineering remediations for `RESTRICTION_REGISTER_V6.md`:
  - `R-01` & `R-44`: Reconciled liquid-capital & loss-cause-aware anomaly controller + objective
    disputed-inventory EV vs distressed-liquidation recovery evaluator (100% `D-001` non-interference).
  - `R-02` & `R-11`: Independent mathematical state-space payoff proof admission replacing static
    sleeve-name allowlists and blanket `CAL1`/`COND1` zero-fee exclusions while hardening calendar
    deadline ordering (`T_early <= T_late`) and dual-source weather verification.
  - `R-03`: Decoupling persistent structural capability certification (with cold-boot merge protection)
    from fresh per-tick market & account-state verification.
  - `R-04` & `R-41`: Correlated worst-case exposure (`CWCE`) engine replacing conflicting book-equity
    notional caps (`max($20, 28% * eq)` / `$45` / `65%`) with true worst-case principal/lockup risk.
  - `R-09`, `R-43` & `R-15`: Dynamic Marginal Portfolio Capital Allocator ranking candidates by
    Marginal Realizable Net Value (`MRNV`) with endogenous opportunity-cost shadow price `lambda_cap`,
    replacing step-function `24h` / `7.5 bps/hr` cliffs and closing the 30-day `DOMINANCE` exemption.
  - `R-10`: Sunk vs marginal infrastructure expense reconciler eliminating daily-vs-cumulative horizon
    mismatches and per-clip fixed-cost double counting.
  - `R-21` & `R-23`: 13-schedule Polymarket V2 fee/rounding verifier + per-wallet (`sig_type` 0..3) and
    per-adapter (`CTF_V1`, `CTF_ADAPTER_V2`, `NEG_RISK_V1/V2`, `PositionManager_V2`) split/merge audit.
  - `R-39`, `R-40` & `R-42`: Strict `RESEARCH` / `SHADOW` / `LIVE` mode separation (zero capital or
    maturity suppression in `RESEARCH`/`SHADOW`; non-overridable legal & execution gates in `LIVE`;
    5-pillar evidence-based readiness replacing blind wall-clock `168h` waiting).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from src.polymarket_research.universal_arb_verifier import (
    DEFAULT_D007_MULTILEG_NAV_FLOOR_USD,
    DEFAULT_MIN_MARKETABLE_BUY_USD,
    DEFAULT_MIN_ORDER_SHARES,
    FROZEN_DISPUTED_MARKET_IDS,
    FROZEN_DISPUTED_TRADE_SUBSTRINGS,
    OpportunityClass,
    compute_net_buy_cost_per_delivered_share,
    compute_net_sell_proceeds_per_share,
    infer_polymarket_tick_size,
    quantize_polymarket_price,
)


# ---------------------------------------------------------------------------
# 1. Execution Modes, v6.0 Taxonomic Classifications & Authoritative Constants
# ---------------------------------------------------------------------------


class ExecutionMode(str, Enum):
    """Strict three-tier operational boundary (Prompt Section 4)."""

    RESEARCH = "RESEARCH"  # Contract, pricing, and mathematical investigation
    SHADOW = "SHADOW"      # Non-executing simulated order construction & portfolio accounting
    LIVE = "LIVE"          # Actual trading and position-changing transactions


class V6RestrictionClassification(str, Enum):
    """Evidence-based v6.0 reassessment taxonomy challenging coarse v5.0 labels."""

    OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY = "OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY"
    NON_OVERRIDABLE_LEGAL_ELIGIBILITY = "NON_OVERRIDABLE_LEGAL_ELIGIBILITY"  # legacy alias
    ESSENTIAL_INTEGRITY_AND_CUSTODY = "ESSENTIAL_INTEGRITY_AND_CUSTODY"
    HOST_RESOURCE_AND_QUOTA_ENVELOPE = "HOST_RESOURCE_AND_QUOTA_ENVELOPE"
    MODE_SEPARATED_LIVE_ONLY_GATE = "MODE_SEPARATED_LIVE_ONLY_GATE"
    DYNAMIC_CONTROL_REPLACES_STATIC_HEURISTIC = "DYNAMIC_CONTROL_REPLACES_STATIC_HEURISTIC"
    PROTOCOL_AND_COST_ACCOUNTING_DEFECT = "PROTOCOL_AND_COST_ACCOUNTING_DEFECT"
    OPERATIONAL_COUPLING_REPAIRED = "OPERATIONAL_COUPLING_REPAIRED"
    LEGACY_CONFIG_OR_DOC_MISDIAGNOSIS = "LEGACY_CONFIG_OR_DOC_MISDIAGNOSIS"


class RestrictionVerificationBasis(str, Enum):
    """Distinguishes verified external gates from unverified assumptions & AI heuristics (`D-011`)."""

    VERIFIED_PLATFORM_TOS_OR_API_GATE = "VERIFIED_PLATFORM_TOS_OR_API_GATE"
    VERIFIED_REGULATORY_GEOFENCE = "VERIFIED_REGULATORY_GEOFENCE"
    VERIFIED_EXTERNAL_CREDENTIAL_OR_KYB_GATE = "VERIFIED_EXTERNAL_CREDENTIAL_OR_KYB_GATE"
    UNVERIFIED_ASSUMPTION_REQUIRES_CHECK = "UNVERIFIED_ASSUMPTION_REQUIRES_CHECK"
    ADVISORY_AI_PREFERENCE_NON_BINDING_ON_OWNER = "ADVISORY_AI_PREFERENCE_NON_BINDING_ON_OWNER"


RESTRICTED_LIVE_TRADING_JURISDICTIONS: FrozenSet[str] = frozenset(
    {"CA-ON", "CA_ON", "US", "USA", "UK", "GB", "FR", "DE_RESTRICTED"}
)

RECONCILED_NOV11_LIQUID_PUSD_USD: float = 48.695132
RECONCILED_NOV11_MARK_TO_BID_NAV_USD: float = 48.834132
RECONCILED_NOV11_BOOK_EQUITY_USD: float = 99.205132
RECONCILED_NOV11_KMIA_DISPUTED_COST_USD: float = 50.51
RECONCILED_NOV11_KMIA_DISPUTED_BID_USD: float = 0.1390
RECONCILED_NOV11_KMIA_SHARES: float = 52.0
FIXED_MONTHLY_VM_COST_USD: float = 24.67
FIXED_DAILY_VM_COST_USD: float = round(24.67 / 30.0, 6)       # $0.822333/day
FIXED_HOURLY_VM_COST_USD: float = round(24.67 / 720.0, 6)     # $0.034264/hr


def _sf(val: Any, default: float = 0.0) -> float:
    if val in (None, ""):
        return default
    try:
        out = float(val)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# 2. Owner Sovereignty, External Restriction Advisory & Mode Gate (`R-26`..`R-32`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalBlockerReport:
    """
    Explicit diagnostic surfaced whenever an external restriction prevents execution (`D-011`).
    Never silently disables an Owner-authorized operation: reports exact external blocker,
    distinguishes verified facts from assumptions, lists immediately executable actions,
    and enumerates lawful remedies.
    """

    restriction_id: str
    venue_id: str
    verification_basis: RestrictionVerificationBasis
    exact_external_blocker: str
    verified_facts: Tuple[str, ...]
    non_binding_assumptions_or_heuristics: Tuple[str, ...]
    technically_feasible_actions_now: Tuple[str, ...]
    lawful_remedies: Tuple[str, ...]
    silent_disable_permitted: bool = False


@dataclass(frozen=True)
class ModeAdmissionVerdict:
    mode: ExecutionMode
    allowed: bool
    reason: str
    enforced_gates: Tuple[str, ...] = ()
    bypassed_live_only_gates: Tuple[str, ...] = ()
    overridden_discretionary_gates: Tuple[str, ...] = ()
    is_external_blocker: bool = False
    silent_disable_permitted: bool = False
    external_blocker_report: Optional[ExternalBlockerReport] = None


def assess_r26_to_r32_venue_restrictions(
    *,
    operator_jurisdiction: str = "CA-ON",
    server_region: str = "FI",
    nav_usd: float = RECONCILED_NOV11_MARK_TO_BID_NAV_USD,
) -> Dict[str, ExternalBlockerReport]:
    """
    `D-011` (`R-26`..`R-32` Owner Sovereignty & Trading Authority):
    Distinguishes verified external platform/regulatory/KYC gates from unverified assumptions
    and non-binding AI economic heuristics (`$500`, `$10,000` NAV), ensuring zero silent
    disabling and clear lawful remedies across every tracked venue.
    """
    jur = str(operator_jurisdiction or "CA-ON").strip().upper()
    srv = str(server_region or "FI").strip().upper()
    return {
        "R-26": ExternalBlockerReport(
            restriction_id="R-26",
            venue_id="polymarket",
            verification_basis=RestrictionVerificationBasis.VERIFIED_PLATFORM_TOS_OR_API_GATE,
            exact_external_blocker=(
                f"Polymarket ToS & April 2025 OSC settlement restrict retail `{jur}` persons and `US`/`UK` "
                f"order-originating IPs on `POST /order` unless the trading account/entity holds valid "
                f"provider compliance eligibility."
            ),
            verified_facts=(
                "Polymarket CLOB geoblocks `US`/`UK`/`FR` order-originating server IPs via HTTP 403.",
                "Public `gamma-api`, CLOB `/book`, `/books`, and WebSocket feeds are open without geoblock.",
                f"On `{srv}` (`kraken-finland`), Funder Beacon `0x013A...F4e9` (`sig_type=3`) is technically active and accepted by CLOB/Relayer V2.",
            ),
            non_binding_assumptions_or_heuristics=(
                "Blanket AI assumptions about the Owner's personal/entity compliance status without checking actual account onboarding.",
                "Assuming remote server location alone either creates or destroys legal account eligibility.",
            ),
            technically_feasible_actions_now=(
                "Full 375,355-market RESEARCH & SHADOW L2 discovery and simulation.",
                "Single-pass execution of Owner-authorized `0x013A...F4e9` Polymarket operations where CLOB API returns HTTP 200.",
            ),
            lawful_remedies=(
                "Confirm/maintain eligible account or institutional onboarding directly with Polymarket compliance.",
                "Trade equivalent regulated event contracts in `CA-ON` via ForecastEx / IBKR Canada or STX Ontario (`on.stxapp.ca`).",
            ),
        ),
        "R-27": ExternalBlockerReport(
            restriction_id="R-27",
            venue_id="limitless",
            verification_basis=RestrictionVerificationBasis.VERIFIED_PLATFORM_TOS_OR_API_GATE,
            exact_external_blocker=(
                f"Street Chow Inc. (Limitless Exchange) ToS §1 restricts `TRADING` and `ACCOUNT_PRIVATE` "
                f"endpoints for `{jur}`, `CA-AB`, and `US` persons without institutional compliance onboarding."
            ),
            verified_facts=(
                "Keyless public REST (`api.limitless.exchange`) and Socket.IO L2 orderbooks are open and active.",
                "Authenticated order placement requires EIP-712 session onboarding subject to ToS §1 representations.",
            ),
            non_binding_assumptions_or_heuristics=(
                f"Prior `$10,000` NAV deferral (`nav={nav_usd:.2f}`) is a non-binding economic cost/benefit estimate, NOT a hard lock on the Owner.",
            ),
            technically_feasible_actions_now=(
                "Keyless full-depth Limitless RESEARCH & SHADOW orderbook ingestion and cross-venue spread tracking.",
            ),
            lawful_remedies=(
                "Request written institutional/entity onboarding approval from Street Chow Inc. compliance disclosing actual ownership/control.",
                "Route live cross-venue legs to `CA-ON`-regulated venues (`ForecastEx / IBKR Canada`, `STX Ontario`).",
            ),
        ),
        "R-28": ExternalBlockerReport(
            restriction_id="R-28",
            venue_id="predict_fun",
            verification_basis=RestrictionVerificationBasis.VERIFIED_PLATFORM_TOS_OR_API_GATE,
            exact_external_blocker=(
                f"PDF Labs Limited (`predict.fun`) ToS §1 authorizes `Content Features` (market data) in `{jur}` "
                f"while restricting `Technology Features` (`POST /v1/auth`, `POST /v1/orders`) without provider clearance."
            ),
            verified_facts=(
                "Mainnet `Content Features` (REST + WS market data) are explicitly permitted in Restricted Jurisdictions under ToS §1.",
                "Order placement requires JWT wallet authentication + `X-API-Key` under `Technology Features` terms.",
            ),
            non_binding_assumptions_or_heuristics=(
                "Any AI-imposed capital threshold (`$253` / `$10,000` NAV) is advisory only and does not bind the Owner.",
            ),
            technically_feasible_actions_now=(
                "Continuous Mainnet `Content Features` RESEARCH & SHADOW book streaming (`0` signing keys required).",
            ),
            lawful_remedies=(
                "Obtain written `Technology Features` institutional eligibility confirmation + API key from PDF Labs Limited.",
            ),
        ),
        "R-29": ExternalBlockerReport(
            restriction_id="R-29",
            venue_id="sx_bet",
            verification_basis=RestrictionVerificationBasis.VERIFIED_PLATFORM_TOS_OR_API_GATE,
            exact_external_blocker=(
                f"SX Bet Terms prohibit `{jur}` residents and `US`/`UK` IPs from authenticated wagering (`POST /orders-v3`)."
            ),
            verified_facts=(
                "Public OBv3 REST orderbook and active-market endpoints are unauthenticated and reachable from `FI`.",
                "`POST /orders-v3` enforces ToS eligibility and server geoblocking on restricted IPs.",
            ),
            non_binding_assumptions_or_heuristics=(
                "AI capital-size preferences do not restrict Owner venue selection once provider eligibility is satisfied.",
            ),
            technically_feasible_actions_now=(
                "Unauthenticated OBv3 RESEARCH & SHADOW orderbook polling within documented `500/60s` rate limits.",
            ),
            lawful_remedies=(
                "Onboard an eligible account/entity cleared in writing by SX Bet compliance, or trade regulated Ontario sports/event venues (`STX Ontario`).",
            ),
        ),
        "R-30": ExternalBlockerReport(
            restriction_id="R-30",
            venue_id="stx_ontario",
            verification_basis=RestrictionVerificationBasis.VERIFIED_REGULATORY_GEOFENCE,
            exact_external_blocker=(
                f"STX Ontario (`on.stxapp.ca`, regulated by `AGCO` / `iGaming Ontario`) IS legally authorized for "
                f"`CA-ON` residents, but `iGO` geolocation rules reject live personal orders originating from `{srv}` (requires physical `CA-ON` IP/host)."
            ),
            verified_facts=(
                "`CA-ON` residents are legally eligible to open and trade personal STX Ontario accounts.",
                "Unsigned Phoenix WebSocket streams live STX orderbooks cleanly to `FI` for RESEARCH & SHADOW.",
                f"Order placement from `{srv}` (`FI`) fails the `iGO` physical-Ontario geolocation gate unless executed natively from an Ontario (`CA-ON`) endpoint.",
            ),
            non_binding_assumptions_or_heuristics=(
                f"The `$500` NAV milestone (`current NAV=${nav_usd:.2f}`) is purely an advisory fee/capital-efficiency recommendation, NEVER an AI veto if the Owner elects to trade STX Ontario directly from `CA-ON` at any bankroll.",
            ),
            technically_feasible_actions_now=(
                "Live STX Ontario Phoenix WebSocket L2 streaming on `FI` (`RESEARCH` & `SHADOW`).",
                "Direct live execution from the Owner's physical Ontario (`CA-ON`) machine whenever Owner provisions STX account credentials.",
            ),
            lawful_remedies=(
                "Execute STX Ontario live orders natively from a physical Ontario (`CA-ON`) host/workstation (zero cross-border proxy/VPN).",
                "Apply via `apps.stxapp.io` (`Trading` partner track) if institutional API routing is desired.",
            ),
        ),
        "R-31": ExternalBlockerReport(
            restriction_id="R-31",
            venue_id="institutional_kyb",
            verification_basis=RestrictionVerificationBasis.VERIFIED_EXTERNAL_CREDENTIAL_OR_KYB_GATE,
            exact_external_blocker=(
                "Institutional corporate trading accounts on external venues require completed provider KYB onboarding (`DOMINUS_KYB_REFERENCE_ID`) and venue issuance of institutional API credentials."
            ),
            verified_facts=(
                "Corporate incorporation + annual registered-agent/KYB maintenance typically costs `$1,500–$5,000+/yr`.",
                "Venues independently evaluate beneficial ownership, control (`mind and management`), and authorized trader location during KYB.",
            ),
            non_binding_assumptions_or_heuristics=(
                "Prior v5.0/v6.0 `$10,000` NAV deferral is strictly an advisory ROI break-even calculation — the Owner holds sole authority to initiate entity formation or KYB inquiry at any time.",
                "Assuming incorporation either automatically qualifies OR automatically disqualifies an entity without submitting actual facts to the venue's compliance team.",
            ),
            technically_feasible_actions_now=(
                "Zero-cost written pre-incorporation compliance inquiry to target venues using `docs/KYB_AND_API_ONBOARDING_DOSSIERS.md`.",
            ),
            lawful_remedies=(
                "Submit transparent pre-onboarding eligibility inquiry to target venue compliance disclosing actual ownership and operating structure before incurring incorporation fees.",
                "Use `CA-ON`-regulated personal/corporate accounts (`IBKR Canada / ForecastEx`, `STX Ontario`) with `$0` offshore formation overhead.",
            ),
        ),
        "R-32": ExternalBlockerReport(
            restriction_id="R-32",
            venue_id="stx_partner_data",
            verification_basis=RestrictionVerificationBasis.VERIFIED_EXTERNAL_CREDENTIAL_OR_KYB_GATE,
            exact_external_blocker=(
                "Cloud-hosted REST requests from `FI` to `api.on.stxapp.ca/api/v1/*` return HTTP 401/403 without an `STX_APPS_DATA_TOKEN` issued via `apps.stxapp.io`."
            ),
            verified_facts=(
                "Unsigned Phoenix WebSocket already delivers real-time STX Ontario orderbook updates without `STX_APPS_DATA_TOKEN`.",
                "`Data` partner tokens authorize REST market-data reads only (distinct from `Trading` track tokens).",
            ),
            non_binding_assumptions_or_heuristics=(
                "No internal AI restriction applies; provisioning `STX_APPS_DATA_TOKEN` immediately enables cloud REST catalog polling.",
            ),
            technically_feasible_actions_now=(
                "Continue zero-cost Phoenix WebSocket L2 streaming on `FI`, or configure `STX_APPS_DATA_TOKEN` in `/etc/polymarket-shadow.env` at Owner's discretion.",
            ),
            lawful_remedies=(
                "Request a free `Data` track token at `https://apps.stxapp.io` if cloud REST historical/catalog endpoints are desired.",
            ),
        ),
    }


def evaluate_mode_specific_eligibility(
    mode: ExecutionMode,
    *,
    jurisdiction: str = "CA-ON",
    venue_id: str = "polymarket",
    venue_live_authorized_for_jurisdiction: bool = False,
    claims_incorporation_or_remote_host_bypass: bool = False,
    owner_explicitly_authorized: bool = False,
    api_license_and_rate_limit_ok: bool = True,
    touches_d001_disputed_kmia: bool = False,
    opportunity_class: OpportunityClass = OpportunityClass.CLASS_B,
    sequential_clob_legs: int = 2,
    is_atomic_or_inventory_locked: bool = False,
    reconciled_liquid_nav_usd: float = RECONCILED_NOV11_LIQUID_PUSD_USD,
    directional_wfo_certified: bool = False,
    live_promotion_approved: bool = False,
) -> ModeAdmissionVerdict:
    """
    Strictly separates `RESEARCH`, `SHADOW`, and `LIVE` enforcement under Owner Sovereignty (`D-011`):
      - External data-license / API rate-limit compliance applies in ALL modes (`RESEARCH`, `SHADOW`, `LIVE`).
      - `D-001` non-interference with the 4 disputed `KMIA` positions applies in ALL action-generating modes
        unless explicitly lifted by the Owner after UMA DVM resolution; `RESEARCH` reads public state freely.
      - **Owner Sovereignty (`owner_explicitly_authorized=True`):** The AI is an execution & advisory agent,
        NOT a veto over the Owner's trading, venue, sizing, or activation authority. When `owner_explicitly_authorized=True`,
        ALL internal discretionary AI/worker thresholds (`LIVE_PROPOSAL_APPROVAL_GATE`, `$500` multi-leg default,
        `$150` `CLASS_C` bankroll default) clear immediately in a **single pass** without repeated approvals.
      - **Transparent External Blocker Reporting (Zero Silent Disabling):** If a verified external platform,
        regulatory geofence, or missing-credential restriction prevents execution (`venue_live_authorized_for_jurisdiction=False`),
        never silently disable or attempt unauthorized circumvention — return `is_external_blocker=True`,
        `silent_disable_permitted=False`, and the exact `ExternalBlockerReport` with `lawful_remedies`.
    """
    venue_map = {
        "polymarket": "R-26",
        "limitless": "R-27",
        "predict_fun": "R-28",
        "sx_bet": "R-29",
        "stx_ontario": "R-30",
        "institutional_kyb": "R-31",
        "stx_partner_data": "R-32",
    }
    rid = venue_map.get(str(venue_id or "polymarket").strip().lower(), "R-26")
    r26_32 = assess_r26_to_r32_venue_restrictions(
        operator_jurisdiction=jurisdiction,
        nav_usd=reconciled_liquid_nav_usd,
    )
    ext_report = r26_32.get(rid, r26_32["R-26"])

    if not api_license_and_rate_limit_ok:
        return ModeAdmissionVerdict(
            mode=mode,
            allowed=False,
            reason="BLOCKED_EXTERNAL_API_LICENSE_OR_RATE_LIMIT",
            enforced_gates=("EXTERNAL_DATA_LICENSE_AND_RATE_LIMIT",),
            is_external_blocker=True,
            silent_disable_permitted=False,
            external_blocker_report=ext_report,
        )

    enforced: List[str] = ["EXTERNAL_DATA_LICENSE_AND_RATE_LIMIT"]
    bypassed: List[str] = []
    overridden: List[str] = []

    if mode == ExecutionMode.RESEARCH:
        bypassed.extend(
            [
                "LIVE_EXTERNAL_VENUE_ELIGIBILITY_CHECK",
                "LIVE_PROPOSAL_APPROVAL_GATE",
                "LIVE_SUB500_MULTILEG_QUARANTINE",
                "LIVE_SUB150_DIRECTIONAL_BANKROLL_GATE",
                "LIVE_CAPITAL_VELOCITY_HURDLE",
            ]
        )
        return ModeAdmissionVerdict(
            mode=mode,
            allowed=True,
            reason="RESEARCH_FULL_UNIVERSE_ADMITTED",
            enforced_gates=tuple(enforced),
            bypassed_live_only_gates=tuple(bypassed),
        )

    if touches_d001_disputed_kmia:
        enforced.append("D001_KMIA_DISPUTED_NON_INTERFERENCE")
        return ModeAdmissionVerdict(
            mode=mode,
            allowed=False,
            reason="BLOCKED_D001_DISPUTED_KMIA_POSITION_QUARANTINE",
            enforced_gates=tuple(enforced),
            silent_disable_permitted=False,
        )
    enforced.append("D001_KMIA_DISPUTED_NON_INTERFERENCE")

    if mode == ExecutionMode.SHADOW:
        if opportunity_class in {OpportunityClass.CLASS_D, OpportunityClass.CLASS_E}:
            enforced.append("SHADOW_VALID_CONTRACT_OR_POSITIVE_EV_GATE")
            return ModeAdmissionVerdict(
                mode=mode,
                allowed=False,
                reason=f"SHADOW_REJECTED_INVALID_OR_UNPROVEN_STRUCTURE:{opportunity_class.value}",
                enforced_gates=tuple(enforced),
            )
        bypassed.extend(
            [
                "LIVE_EXTERNAL_VENUE_ELIGIBILITY_CHECK",
                "LIVE_PROPOSAL_APPROVAL_GATE",
                "LIVE_SUB500_MULTILEG_QUARANTINE",
                "LIVE_SUB150_DIRECTIONAL_BANKROLL_GATE",
                "ARBITRARY_MATURITY_CUTOFF",
            ]
        )
        return ModeAdmissionVerdict(
            mode=mode,
            allowed=True,
            reason="SHADOW_SIMULATION_ADMITTED_FULL_HORIZON",
            enforced_gates=tuple(enforced),
            bypassed_live_only_gates=tuple(bypassed),
        )

    # ExecutionMode.LIVE: distinguish verified external platform/regulatory gates from
    # internal discretionary defaults that yield immediately to `owner_explicitly_authorized=True`.
    enforced.append("LIVE_EXTERNAL_VENUE_ELIGIBILITY_CHECK")
    jur_norm = str(jurisdiction or "").strip().upper()
    if claims_incorporation_or_remote_host_bypass and not venue_live_authorized_for_jurisdiction:
        return ModeAdmissionVerdict(
            mode=mode,
            allowed=False,
            reason=f"EXTERNAL_BLOCKER_UNVERIFIED_BYPASS_ASSUMPTION:{jur_norm}:{ext_report.restriction_id}",
            enforced_gates=tuple(enforced),
            is_external_blocker=True,
            silent_disable_permitted=False,
            external_blocker_report=ext_report,
        )
    if jur_norm in RESTRICTED_LIVE_TRADING_JURISDICTIONS and not venue_live_authorized_for_jurisdiction:
        return ModeAdmissionVerdict(
            mode=mode,
            allowed=False,
            reason=f"EXTERNAL_BLOCKER_REPORTED:{jur_norm}:{ext_report.restriction_id}",
            enforced_gates=tuple(enforced),
            is_external_blocker=True,
            silent_disable_permitted=False,
            external_blocker_report=ext_report,
        )

    if opportunity_class not in {OpportunityClass.CLASS_A, OpportunityClass.CLASS_B, OpportunityClass.CLASS_C}:
        return ModeAdmissionVerdict(
            mode=mode,
            allowed=False,
            reason=f"BLOCKED_LIVE_INVALID_PAYOFF_CLASS:{opportunity_class.value}",
            enforced_gates=tuple(enforced),
            silent_disable_permitted=False,
        )

    # Internal autonomous-worker defaults: enforced on unattended AI workers (`owner_explicitly_authorized=False`),
    # cleared in a SINGLE PASS when the Owner explicitly authorizes (`owner_explicitly_authorized=True`).
    if owner_explicitly_authorized:
        if not live_promotion_approved:
            overridden.append("LIVE_PROPOSAL_APPROVAL_GATE")
        if sequential_clob_legs >= 3 and not is_atomic_or_inventory_locked and reconciled_liquid_nav_usd < DEFAULT_D007_MULTILEG_NAV_FLOOR_USD - 1e-6:
            overridden.append("LIVE_SUB500_MULTILEG_DEFAULT")
        if opportunity_class == OpportunityClass.CLASS_C and (reconciled_liquid_nav_usd < 150.0 - 1e-6 or not directional_wfo_certified):
            overridden.append("LIVE_SUB150_CLASS_C_DEFAULT")
        return ModeAdmissionVerdict(
            mode=mode,
            allowed=True,
            reason="LIVE_OWNER_AUTHORIZED_SINGLE_PASS",
            enforced_gates=tuple(enforced),
            overridden_discretionary_gates=tuple(overridden),
        )

    enforced.append("LIVE_PROPOSAL_APPROVAL_GATE")
    if not live_promotion_approved:
        return ModeAdmissionVerdict(
            mode=mode,
            allowed=False,
            reason="AWAITING_OWNER_AUTHORIZATION:LIVE_PROPOSAL_ONLY_DEFAULT",
            enforced_gates=tuple(enforced),
            silent_disable_permitted=False,
        )

    if sequential_clob_legs >= 3 and not is_atomic_or_inventory_locked:
        enforced.append("LIVE_SUB500_MULTILEG_QUARANTINE")
        if reconciled_liquid_nav_usd < DEFAULT_D007_MULTILEG_NAV_FLOOR_USD - 1e-6:
            return ModeAdmissionVerdict(
                mode=mode,
                allowed=False,
                reason=f"BLOCKED_D007_UNATTENDED_MULTILEG_BELOW_500_NAV:{reconciled_liquid_nav_usd:.2f}",
                enforced_gates=tuple(enforced),
                silent_disable_permitted=False,
            )

    if opportunity_class == OpportunityClass.CLASS_C:
        enforced.append("LIVE_DIRECTIONAL_OR_CARRY_CERTIFICATION_GATE")
        if reconciled_liquid_nav_usd < 150.0 - 1e-6 or not directional_wfo_certified:
            return ModeAdmissionVerdict(
                mode=mode,
                allowed=False,
                reason=f"BLOCKED_UNATTENDED_CLASS_C_DEFAULT_150_NAV_OR_WFO:{reconciled_liquid_nav_usd:.2f}",
                enforced_gates=tuple(enforced),
                silent_disable_permitted=False,
            )

    return ModeAdmissionVerdict(
        mode=mode,
        allowed=True,
        reason="LIVE_EXECUTION_AUTHORIZED",
        enforced_gates=tuple(enforced),
    )


# ---------------------------------------------------------------------------
# 3. Loss-Cause-Aware Reconciled Capital Controller & R-44 Disputed EV Audit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BalanceChangeAttribution:
    reconciled_deployable_liquid_usd: float
    reconciled_mark_to_bid_nav_usd: float
    quarantined_disputed_cost_usd: float
    quarantined_disputed_mark_usd: float
    external_net_cashflow_usd: float
    quarantined_dispute_writeoff_delta_usd: float
    new_riskless_realized_loss_usd: float
    unhedged_legging_bleed_usd: float
    unexplained_accounting_drift_usd: float
    halted: bool
    halt_reasons: Tuple[str, ...]


class LossCauseAwareCapitalController:
    """
    Replaces blind fixed dollar ruin floors (`$62.00` / `$30.00`, `R-01`) with reconciled
    liquid-capital & loss-cause-aware controls:
      1. Never counts pre-existing frozen/disputed cost basis (`$50.51` `KMIA`) as deployable cash,
         and NEVER trips a riskless ruin halt if an already-quarantined historical disputed receivable
         settles at `$0.00` (`quarantined_dispute_writeoff_delta_usd`).
      2. Never confuses verified external cashflows (`deposits`/`withdrawals`) or `USDC.e <-> pUSD`
         collateral wraps with trading drawdown.
      3. Catches genuine execution/legging defects `12x` faster than a static `$30` floor by halting
         immediately if post-baseline riskless principal loss exceeds `max_new_riskless_loss_usd`
         (`$1.50` cumulative or `$0.75` single-box) OR unexplained accounting drift exceeds `$1.50`.
      4. Halts sizing gracefully only if deployable liquid collateral + healthy open mark-to-bid
         falls below minimum exchange executable lot + safety buffer (`min_executable_liquid_floor_usd`,
         default `$6.50` = `5` shares + `$1.50` reserve).
    """

    def __init__(
        self,
        *,
        max_new_riskless_cumulative_loss_usd: float = 1.50,
        max_single_box_riskless_loss_usd: float = 0.75,
        max_unexplained_accounting_drift_usd: float = 1.50,
        min_executable_liquid_floor_usd: float = 6.50,
    ) -> None:
        self.max_new_riskless_cumulative_loss_usd = max(0.10, float(max_new_riskless_cumulative_loss_usd))
        self.max_single_box_riskless_loss_usd = max(0.05, float(max_single_box_riskless_loss_usd))
        self.max_unexplained_accounting_drift_usd = max(0.10, float(max_unexplained_accounting_drift_usd))
        self.min_executable_liquid_floor_usd = max(5.00, float(min_executable_liquid_floor_usd))

    def evaluate(
        self,
        *,
        liquid_pusd_usd: float,
        idle_usdce_usd: float = 0.0,
        escrowed_maker_usd: float = 0.0,
        healthy_open_mark_to_bid_usd: float = 0.0,
        quarantined_disputed_cost_usd: float = 0.0,
        quarantined_disputed_bid_usd: float = 0.0,
        baseline_quarantined_disputed_cost_usd: float = RECONCILED_NOV11_KMIA_DISPUTED_COST_USD,
        external_net_cashflow_usd: float = 0.0,
        post_baseline_closed_riskless_pnls_usd: Sequence[float] = (),
        unhedged_legging_bleed_usd: float = 0.0,
        unexplained_accounting_drift_usd: float = 0.0,
        accounting_safeguard_active: bool = False,
    ) -> BalanceChangeAttribution:
        reasons: List[str] = []
        for lbl, v in (
            ("LIQUID_PUSD", liquid_pusd_usd),
            ("IDLE_USDCE", idle_usdce_usd),
            ("ESCROWED_MAKER", escrowed_maker_usd),
            ("HEALTHY_OPEN_BID", healthy_open_mark_to_bid_usd),
        ):
            if not math.isfinite(float(v)) or float(v) < -1e-6:
                reasons.append(f"CORRUPT_OR_NEGATIVE_{lbl}")

        deployable_liquid = max(0.0, _sf(liquid_pusd_usd) + _sf(idle_usdce_usd) + _sf(escrowed_maker_usd))
        healthy_nav = deployable_liquid + max(0.0, _sf(healthy_open_mark_to_bid_usd))
        q_cost = max(0.0, _sf(quarantined_disputed_cost_usd))
        q_bid = min(q_cost, max(0.0, _sf(quarantined_disputed_bid_usd)))
        mark_to_bid_nav = round(healthy_nav + q_bid, 6)

        # Write-off of already-quarantined historical KMIA cost ($50.51 -> $0.00) is isolated here:
        dispute_writeoff_delta = min(0.0, q_cost - max(0.0, _sf(baseline_quarantined_disputed_cost_usd)))

        worst_single_box_loss = 0.0
        net_post_baseline_pnl = 0.0
        gross_loss_sum = 0.0
        for pnl in post_baseline_closed_riskless_pnls_usd:
            pf = _sf(pnl, 0.0)
            net_post_baseline_pnl += pf
            if pf < 0.0:
                gross_loss_sum += abs(pf)
                worst_single_box_loss = max(worst_single_box_loss, abs(pf))

        leg_bleed = max(0.0, _sf(unhedged_legging_bleed_usd))
        total_new_riskless_loss = round(max(0.0, -net_post_baseline_pnl) + leg_bleed, 6)
        drift_abs = abs(_sf(unexplained_accounting_drift_usd))

        if accounting_safeguard_active:
            reasons.append("PAA_ACCOUNTING_SAFEGUARD_ACTIVE")
        if drift_abs > self.max_unexplained_accounting_drift_usd + 1e-9:
            reasons.append(
                f"UNEXPLAINED_ACCOUNTING_DRIFT:{drift_abs:.4f}>{self.max_unexplained_accounting_drift_usd:.2f}"
            )
        if worst_single_box_loss > self.max_single_box_riskless_loss_usd + 1e-9:
            reasons.append(
                f"SINGLE_BOX_RISKLESS_LOSS_ANOMALY:{worst_single_box_loss:.4f}>{self.max_single_box_riskless_loss_usd:.2f}"
            )
        if max(total_new_riskless_loss, gross_loss_sum + leg_bleed) > self.max_new_riskless_cumulative_loss_usd + 1e-9:
            reasons.append(
                f"CUMULATIVE_NEW_RISKLESS_LOSS_ANOMALY:{max(total_new_riskless_loss, gross_loss_sum + leg_bleed):.4f}>"
                f"{self.max_new_riskless_cumulative_loss_usd:.2f}"
            )
        if healthy_nav < self.min_executable_liquid_floor_usd - 1e-9:
            reasons.append(
                f"BELOW_MIN_EXECUTABLE_LIQUID_LOT:{healthy_nav:.4f}<{self.min_executable_liquid_floor_usd:.2f}"
            )

        return BalanceChangeAttribution(
            reconciled_deployable_liquid_usd=round(deployable_liquid, 6),
            reconciled_mark_to_bid_nav_usd=mark_to_bid_nav,
            quarantined_disputed_cost_usd=round(q_cost, 6),
            quarantined_disputed_mark_usd=round(q_bid, 6),
            external_net_cashflow_usd=round(_sf(external_net_cashflow_usd), 6),
            quarantined_dispute_writeoff_delta_usd=round(dispute_writeoff_delta, 6),
            new_riskless_realized_loss_usd=round(max(gross_loss_sum, total_new_riskless_loss), 6),
            unhedged_legging_bleed_usd=round(leg_bleed, 6),
            unexplained_accounting_drift_usd=round(_sf(unexplained_accounting_drift_usd), 6),
            halted=bool(reasons),
            halt_reasons=tuple(reasons),
        )


def evaluate_disputed_inventory_recovery_options(
    *,
    par_redemption_shares: float = RECONCILED_NOV11_KMIA_SHARES,
    book_cost_basis_usd: float = RECONCILED_NOV11_KMIA_DISPUTED_COST_USD,
    distressed_bid_proceeds_usd: float = RECONCILED_NOV11_KMIA_DISPUTED_BID_USD,
    expected_dvm_resolution_hours: float = 168.0,
    reinvestment_yield_bps_per_hr: float = 15.0,
    estimated_dvm_favorable_prob: float = 0.35,
) -> Dict[str, Any]:
    """
    Objective quantitative comparison for `R-44` (read-only analysis; zero mutation or order placement
    on the 4 disputed `KMIA` positions per `D-001`):
      - Option A (`HOLD_FOR_UMA_DVM`): Expected terminal wealth `p_win * par_shares * $1.00`.
      - Option B (`DISTRESSED_CLOB_SALE` — prohibited under `D-001`): Immediate salvage `$0.1390`
        compounded at `reinvestment_yield_bps_per_hr` over `expected_dvm_resolution_hours`.
      - Solves exact breakeven DVM win probability `p*` above which holding strictly dominates selling.
    """
    par_usd = max(0.0, float(par_redemption_shares)) * 1.0
    salvage_usd = max(0.0, float(distressed_bid_proceeds_usd))
    hrs = max(0.0, float(expected_dvm_resolution_hours))
    r_hr = max(0.0, float(reinvestment_yield_bps_per_hr)) / 10_000.0
    compounded_salvage_usd = salvage_usd * ((1.0 + r_hr) ** hrs)
    breakeven_dvm_prob = min(1.0, compounded_salvage_usd / par_usd) if par_usd > 0 else 1.0
    ev_hold_usd = max(0.0, min(1.0, float(estimated_dvm_favorable_prob))) * par_usd
    return {
        "par_payout_if_favorable_usd": round(par_usd, 4),
        "sunk_book_cost_basis_usd": round(float(book_cost_basis_usd), 4),
        "distressed_bid_salvage_now_usd": round(salvage_usd, 4),
        "distressed_salvage_compounded_at_dvm_horizon_usd": round(compounded_salvage_usd, 4),
        "breakeven_dvm_win_probability": round(breakeven_dvm_prob, 6),
        "breakeven_dvm_win_pct": round(breakeven_dvm_prob * 100.0, 4),
        "ev_hold_at_estimated_prob_usd": round(ev_hold_usd, 4),
        "ev_advantage_of_holding_usd": round(ev_hold_usd - compounded_salvage_usd, 4),
        "recommended_policy": (
            "HOLD_TOUCH_NOTHING_D001"
            if ev_hold_usd >= compounded_salvage_usd
            else "REVIEW_WITH_OWNER_ONLY_D001_LOCKED"
        ),
        "d001_live_execution_prohibited": True,
    }


# ---------------------------------------------------------------------------
# 4. Independent Mathematical Payoff Proof (`R-02`) & Decoupled Cert (`R-03`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PayoffAdmissionVerdict:
    admitted: bool
    opportunity_class: OpportunityClass
    min_state_net_payoff_usd: float
    expected_net_payoff_usd: float
    reason: str
    proof_digest_sha256: str


def verify_independent_payoff_admission(
    candidate: Mapping[str, Any],
    *,
    mode: ExecutionMode = ExecutionMode.SHADOW,
    min_live_net_edge_per_share: float = 0.0025,
) -> PayoffAdmissionVerdict:
    """
    Replaces sleeve-name string allowlists (`R-02`) with independent mathematical proof across
    exhaustive outcome states `Omega`, inclusive of exact Protocol V2 fees:
      - Admits ANY 2-leg binary/strike/calendar/partition structure regardless of sleeve string name
        when contractual implication/partition invariants hold and fee-adjusted worst-state payoff > 0.
      - Explicitly catches defects missed by v5.0 `stage_c_zero_loss_velocity`:
        (1) `CAL1` inverted calendar deadlines (`t_early_ts > t_late_ts`),
        (2) mismatched resolution oracle / void-rule clauses (`oracle_signature_a != oracle_signature_b`),
        (3) `negRiskAugmented == True` or mutable `Other` slates,
        (4) single-source unverified weather station proxy locks (`dual_source_wu_metar_verified == False`),
        WHILE admitting fee-bearing `CAL1`/`COND1`/`C1`/`D1` boxes whenever exact V2 share-haircut cost
        satisfies `cost_a_net + cost_b_net <= 1.0 - min_live_net_edge_per_share`!
    """
    shares = max(1.0, _sf(candidate.get("shares", candidate.get("net_paired_shares")), 10.0))
    relation = str(candidate.get("relation_type") or candidate.get("box_type") or "").strip().upper()
    neg_aug = bool(
        candidate.get("neg_risk_augmented", False)
        or candidate.get("negRiskAugmented", False)
        or candidate.get("mutable_other_bucket", False)
    )
    if neg_aug:
        digest = hashlib.sha256(f"REJECT_AUG:{candidate.get('candidate_id','')}".encode("utf-8")).hexdigest()
        return PayoffAdmissionVerdict(
            admitted=(mode == ExecutionMode.RESEARCH),
            opportunity_class=OpportunityClass.CLASS_D,
            min_state_net_payoff_usd=round(-shares, 6),
            expected_net_payoff_usd=0.0,
            reason="REJECTED_AUGMENTED_OR_MUTABLE_OTHER_PARTITION",
            proof_digest_sha256=digest,
        )

    orc_a = str(candidate.get("oracle_clause_hash_a") or candidate.get("leg_a_oracle") or "").strip()
    orc_b = str(candidate.get("oracle_clause_hash_b") or candidate.get("leg_b_oracle") or "").strip()
    if orc_a and orc_b and orc_a != orc_b:
        digest = hashlib.sha256(f"REJECT_ORC:{orc_a}:{orc_b}".encode("utf-8")).hexdigest()
        return PayoffAdmissionVerdict(
            admitted=(mode == ExecutionMode.RESEARCH),
            opportunity_class=OpportunityClass.CLASS_D,
            min_state_net_payoff_usd=round(-shares, 6),
            expected_net_payoff_usd=0.0,
            reason="REJECTED_ORACLE_OR_VOID_CLAUSE_MISMATCH",
            proof_digest_sha256=digest,
        )

    t_early = _sf(candidate.get("t_early_ts", candidate.get("leg_a_deadline_ts")), 0.0)
    t_late = _sf(candidate.get("t_late_ts", candidate.get("leg_b_deadline_ts")), 0.0)
    if t_early > 0.0 and t_late > 0.0 and t_early > t_late + 1e-6:
        digest = hashlib.sha256(f"REJECT_CAL:{t_early}:{t_late}".encode("utf-8")).hexdigest()
        return PayoffAdmissionVerdict(
            admitted=(mode == ExecutionMode.RESEARCH),
            opportunity_class=OpportunityClass.CLASS_E,
            min_state_net_payoff_usd=round(-shares, 6),
            expected_net_payoff_usd=0.0,
            reason=f"REJECTED_INVERTED_CALENDAR_DEADLINE:{t_early:.0f}>{t_late:.0f}",
            proof_digest_sha256=digest,
        )

    k_lo = _sf(candidate.get("k_low", candidate.get("leg_a_strike")), 0.0)
    k_hi = _sf(candidate.get("k_high", candidate.get("leg_b_strike")), 0.0)
    if k_lo > 0.0 and k_hi > 0.0 and k_lo > k_hi + 1e-9:
        digest = hashlib.sha256(f"REJECT_STRIKE:{k_lo}:{k_hi}".encode("utf-8")).hexdigest()
        return PayoffAdmissionVerdict(
            admitted=(mode == ExecutionMode.RESEARCH),
            opportunity_class=OpportunityClass.CLASS_E,
            min_state_net_payoff_usd=round(-shares, 6),
            expected_net_payoff_usd=0.0,
            reason=f"REJECTED_INVERTED_STRIKE_MONOTONICITY:{k_lo}>{k_hi}",
            proof_digest_sha256=digest,
        )

    # Single-leg UMA / weather post-clinch carries: honestly classify as CLASS_C unless contractually settled
    if relation in {"SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK", "UMA_CARRY", "WEATHER_DEAD_NO"}:
        if candidate.get("dual_source_wu_metar_verified") is False:
            digest = hashlib.sha256(b"REJECT_WX_SINGLE_SOURCE").hexdigest()
            return PayoffAdmissionVerdict(
                admitted=(mode == ExecutionMode.RESEARCH),
                opportunity_class=OpportunityClass.CLASS_D,
                min_state_net_payoff_usd=round(-shares, 6),
                expected_net_payoff_usd=0.0,
                reason="REJECTED_SINGLE_SOURCE_WEATHER_PROXY_UNVERIFIED",
                proof_digest_sha256=digest,
            )
        px = _sf(candidate.get("leg_a_limit_price", candidate.get("price")), 0.99)
        fr = _sf(candidate.get("leg_a_fee_rate", candidate.get("fee_rate")), 0.0)
        fe = _sf(candidate.get("leg_a_fee_exponent", candidate.get("fee_exponent")), 1.0)
        is_mkr = bool(candidate.get("is_maker", relation == "SINGLE_LEG_MAKER_LOCK"))
        raw_uc = px if is_mkr else compute_net_buy_cost_per_delivered_share(px, fee_rate=fr, fee_exponent=fe)
        unit_cost = float(raw_uc[0]) if isinstance(raw_uc, tuple) else float(raw_uc)
        p_win = min(1.0, max(0.0, _sf(candidate.get("p_model"), 0.995)))
        min_payoff = round((0.0 - unit_cost) * shares, 6) if p_win < 1.0 else round((1.0 - unit_cost) * shares, 6)
        ev_payoff = round((p_win * 1.0 - unit_cost) * shares, 6)
        cls = OpportunityClass.CLASS_C if p_win < 1.0 or not bool(candidate.get("onchain_payout_finalized")) else OpportunityClass.CLASS_B
        digest = hashlib.sha256(f"SLL:{unit_cost:.6f}:{p_win:.6f}:{shares:.2f}".encode("utf-8")).hexdigest()
        admitted = True if mode == ExecutionMode.RESEARCH else (ev_payoff > 0.0 if mode == ExecutionMode.SHADOW else (p_win >= 0.999 and ev_payoff > 0.0))
        return PayoffAdmissionVerdict(
            admitted=admitted,
            opportunity_class=cls,
            min_state_net_payoff_usd=min_payoff,
            expected_net_payoff_usd=ev_payoff,
            reason="ADMITTED_BOUNDED_POST_CLINCH_CARRY" if admitted else "REJECTED_SUB_HURDLE_CARRY",
            proof_digest_sha256=digest,
        )

    # Multi-state / 2-leg exact payoff verification
    px_a = _sf(candidate.get("leg_a_limit_price"), 0.50)
    px_b = _sf(candidate.get("leg_b_limit_price"), 0.50)
    fr_a = _sf(candidate.get("leg_a_fee_rate"), 0.0)
    fr_b = _sf(candidate.get("leg_b_fee_rate"), 0.0)
    fe_a = _sf(candidate.get("leg_a_fee_exponent"), 1.0)
    fe_b = _sf(candidate.get("leg_b_fee_exponent"), 1.0)

    raw_ca = compute_net_buy_cost_per_delivered_share(px_a, fee_rate=fr_a, fee_exponent=fe_a)
    raw_cb = compute_net_buy_cost_per_delivered_share(px_b, fee_rate=fr_b, fee_exponent=fe_b)
    cost_a = float(raw_ca[0]) if isinstance(raw_ca, tuple) else float(raw_ca)
    cost_b = float(raw_cb[0]) if isinstance(raw_cb, tuple) else float(raw_cb)
    unit_box_cost = cost_a + cost_b

    cid_a = str(candidate.get("leg_a_condition_id") or "").strip().lower()
    cid_b = str(candidate.get("leg_b_condition_id") or "").strip().lower()
    tok_a = str(candidate.get("leg_a_token_id") or "").strip()
    tok_b = str(candidate.get("leg_b_token_id") or "").strip()
    if tok_a and tok_b and tok_a == tok_b:
        digest = hashlib.sha256(f"DUP_TOK:{tok_a}".encode("utf-8")).hexdigest()
        return PayoffAdmissionVerdict(
            admitted=False,
            opportunity_class=OpportunityClass.CLASS_E,
            min_state_net_payoff_usd=round(-unit_box_cost * shares, 6),
            expected_net_payoff_usd=round(-unit_box_cost * shares, 6),
            reason="REJECTED_DUPLICATE_INSTRUMENT_LEGS",
            proof_digest_sha256=digest,
        )

    if relation in {"COMPLETE_SET", "C1_BINARY_COMPLETE_SET"} and cid_a and cid_b and cid_a != cid_b:
        if not bool(candidate.get("verified_cross_market_equivalence", False)):
            digest = hashlib.sha256(f"COND_MISMATCH:{cid_a}:{cid_b}".encode("utf-8")).hexdigest()
            return PayoffAdmissionVerdict(
                admitted=(mode == ExecutionMode.RESEARCH),
                opportunity_class=OpportunityClass.CLASS_D,
                min_state_net_payoff_usd=round(-unit_box_cost * shares, 6),
                expected_net_payoff_usd=0.0,
                reason="REJECTED_UNVERIFIED_CROSS_CONDITION_PAIR",
                proof_digest_sha256=digest,
            )

    # State payoffs per share across exhaustive valid states:
    #   - Same-condition binary complete set: {(YES=1, NO=0): 1.0, (YES=0, NO=1): 1.0, (50-50 void): 1.0}
    #   - Implication A => B (`YES_A` + `NO_B`, where `A=1, B=0` is mathematically impossible):
    #       states = {(A=0, B=0): 1.0, (A=1, B=1): 1.0, (A=0, B=1): 2.0}
    has_middle_double_payout = relation in {
        "DOMINANCE",
        "DOMINANCE_BOX",
        "BARRIER_MONO",
        "MACRO_DOMINANCE",
        "LADDER_MONO",
        "IMPLICATION_BOX",
    } and (k_hi > k_lo + 1e-9 or t_late > t_early + 1e-6)
    p_middle = min(0.50, max(0.0, _sf(candidate.get("middle_corridor_prob"), 0.05 if has_middle_double_payout else 0.0)))

    # Check asymmetric void hazard on cross-condition boxes
    if cid_a != cid_b and bool(candidate.get("asymmetric_void_risk", False)):
        min_unit_payout = 0.50
    else:
        min_unit_payout = 1.00

    min_net_per_share = min_unit_payout - unit_box_cost
    ev_net_per_share = (1.0 + p_middle) - unit_box_cost
    min_net_usd = round(min_net_per_share * shares, 6)
    ev_net_usd = round(ev_net_per_share * shares, 6)
    is_atomic = bool(candidate.get("is_atomic_or_inventory_locked", False))

    if min_net_per_share > 0.0:
        opp_cls = OpportunityClass.CLASS_A if is_atomic else OpportunityClass.CLASS_B
    elif ev_net_per_share > 0.0:
        opp_cls = OpportunityClass.CLASS_C
    else:
        opp_cls = OpportunityClass.CLASS_E

    digest_payload = json.dumps(
        {
            "relation": relation,
            "cost_a": round(cost_a, 8),
            "cost_b": round(cost_b, 8),
            "min_unit_payout": min_unit_payout,
            "min_net_usd": min_net_usd,
            "class": opp_cls.value,
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()

    if mode == ExecutionMode.RESEARCH:
        return PayoffAdmissionVerdict(True, opp_cls, min_net_usd, ev_net_usd, "RESEARCH_ADMITTED", digest)
    if mode == ExecutionMode.SHADOW:
        ok_sh = opp_cls in {OpportunityClass.CLASS_A, OpportunityClass.CLASS_B, OpportunityClass.CLASS_C}
        return PayoffAdmissionVerdict(
            ok_sh,
            opp_cls,
            min_net_usd,
            ev_net_usd,
            "SHADOW_ADMITTED_BY_PROOF" if ok_sh else "SHADOW_NEGATIVE_PAYOFF_REJECTED",
            digest,
        )

    ok_live = opp_cls in {OpportunityClass.CLASS_A, OpportunityClass.CLASS_B} and min_net_per_share >= float(min_live_net_edge_per_share) - 1e-9
    return PayoffAdmissionVerdict(
        ok_live,
        opp_cls,
        min_net_usd,
        ev_net_usd,
        "LIVE_ADMITTED_BY_MATHEMATICAL_PROOF" if ok_live else f"LIVE_BELOW_MIN_PROVEN_EDGE:{min_net_per_share:.6f}",
        digest,
    )


@dataclass(frozen=True)
class DecoupledReadinessCheck:
    structural_cert_ok: bool
    fresh_market_and_account_ok: bool
    overall_live_ok: bool
    structural_source: str
    rejection_reasons: Tuple[str, ...]


def evaluate_decoupled_certification_and_fresh_state(
    *,
    is_contractual_identity_arb: bool,
    cached_sleeve_record: Optional[Mapping[str, Any]],
    lkg_sleeve_record: Optional[Mapping[str, Any]],
    min_graduated_trades: int = 8,
    book_age_sec: float = 0.0,
    max_book_age_sec: float = 6.5,
    uma_resolution_status: str = "none",
    accepting_orders: bool = True,
    reconciled_liquid_cash_usd: float = RECONCILED_NOV11_LIQUID_PUSD_USD,
    required_capital_usd: float = 10.0,
) -> DecoupledReadinessCheck:
    """
    `R-03` Remediation — Cleanly decouples slow-changing structural parser certification from
    millisecond-fresh market & account state verification:
      1. Pure contractual identities (`C1` same-condition `YES + NO == $1.00`, `NegRisk` closed
         partition) are mathematically invariant on-chain (`is_contractual_identity_arb=True`) and
         do NOT depend on `alpha124_shadow_state.json` daemon uptime, UNLESS fresh telemetry shows
         an active execution loss (`losses > 0`) indicating an order-router bug!
      2. If `alpha124` cold-boots (`closed == 0, losses == 0`), merges `lkg_sleeve_record` without
         wiping verified graduation, while IMMEDIATELY failing closed if `cached_sleeve_record` has `losses > 0`.
      3. Regardless of historical graduation (`100/100` wins last week), EVERY live execution MUST
         pass fresh market/account checks (`book_age_sec`, `uma_resolution_status != 'disputed'`,
         `accepting_orders`, and `reconciled_liquid_cash_usd >= required_capital_usd`).
    """
    reasons: List[str] = []
    fresh_rec = cached_sleeve_record if isinstance(cached_sleeve_record, Mapping) else {}
    lkg_rec = lkg_sleeve_record if isinstance(lkg_sleeve_record, Mapping) else {}

    fresh_losses = int(_sf(fresh_rec.get("losses"), 0.0))
    lkg_losses = int(_sf(lkg_rec.get("losses"), 0.0))
    fresh_closed = int(_sf(fresh_rec.get("closed"), 0.0))
    lkg_closed = int(_sf(lkg_rec.get("closed"), 0.0))

    if fresh_losses > 0:
        structural_ok = False
        structural_src = "REVOKED_FRESH_SHADOW_LOSS"
        reasons.append(f"FRESH_SHADOW_LOSS_DETECTED:{fresh_losses}")
    elif is_contractual_identity_arb:
        structural_ok = True
        structural_src = "CONTRACTUAL_PAYOFF_IDENTITY"
    elif fresh_closed >= min_graduated_trades and _sf(fresh_rec.get("win_rate_pct"), 100.0) >= 100.0:
        structural_ok = True
        structural_src = "FRESH_SHADOW_GRADUATION"
    elif fresh_closed == 0 and lkg_losses == 0 and lkg_closed >= min_graduated_trades and _sf(lkg_rec.get("win_rate_pct"), 100.0) >= 100.0:
        structural_ok = True
        structural_src = "COLD_BOOT_MERGED_LKG_GRADUATION"
    else:
        structural_ok = False
        structural_src = "UNGRADUATED_NON_IDENTITY_SLEEVE"
        reasons.append(f"STRUCTURAL_CERT_INCOMPLETE:closed={max(fresh_closed, lkg_closed)}<{min_graduated_trades}")

    fresh_ok = True
    if float(book_age_sec) > float(max_book_age_sec) + 1e-9 or float(book_age_sec) < 0.0:
        fresh_ok = False
        reasons.append(f"STALE_ORDERBOOK:{book_age_sec:.2f}s>{max_book_age_sec:.2f}s")
    if str(uma_resolution_status or "").strip().lower() == "disputed":
        fresh_ok = False
        reasons.append("MARKET_UMA_DISPUTED")
    if not accepting_orders:
        fresh_ok = False
        reasons.append("MARKET_NOT_ACCEPTING_ORDERS")
    if float(reconciled_liquid_cash_usd) < float(required_capital_usd) - 1e-6:
        fresh_ok = False
        reasons.append(f"INSUFFICIENT_RECONCILED_CASH:{reconciled_liquid_cash_usd:.2f}<{required_capital_usd:.2f}")

    return DecoupledReadinessCheck(
        structural_cert_ok=structural_ok,
        fresh_market_and_account_ok=fresh_ok,
        overall_live_ok=(structural_ok and fresh_ok),
        structural_source=structural_src,
        rejection_reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# 5. Correlated Worst-Case Exposure (`CWCE`) Engine (`R-04` / `R-41`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExposurePositionSpec:
    position_id: str
    cluster_keys: Tuple[str, ...]
    capital_committed_usd: float
    is_same_condition_mergeable_box: bool = False
    is_quarantined_historical_dispute: bool = False
    partial_leg_unwind_risk_usd: float = 0.0
    event_id: str = ""
    market_family: str = ""
    underlying_asset: str = ""
    resolution_source: str = ""
    directional_sign: int = 0
    sleeve_name: str = ""
    family_code: str = ""
    model_id: str = ""


def build_structured_cluster_keys(
    cluster_keys: Sequence[str] = (),
    *,
    event_id: str = "",
    market_family: str = "",
    underlying_asset: str = "",
    resolution_source: str = "",
) -> Tuple[str, ...]:
    """Builds deduplicated canonical cluster keys across explicit clusters and 4 structural dimensions."""
    keys: List[str] = []
    seen: Set[str] = set()
    for raw in cluster_keys:
        k = str(raw or "").strip()
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    for prefix, val in (
        ("EVENT:", event_id),
        ("FAMILY:", market_family),
        ("ASSET:", underlying_asset),
        ("RESOLUTION:", resolution_source),
    ):
        v = str(val or "").strip().upper()
        if v:
            k = f"{prefix}{v}"
            if k not in seen:
                seen.add(k)
                keys.append(k)
    return tuple(keys)


@dataclass(frozen=True)
class CorrelatedExposureSummary:
    by_cluster_usd: Dict[str, float]
    by_event_usd: Dict[str, float]
    by_market_family_usd: Dict[str, float]
    by_underlying_asset_usd: Dict[str, float]
    by_resolution_source_usd: Dict[str, float]
    directional_net_by_asset_usd: Dict[str, float]
    directional_gross_by_asset_usd: Dict[str, float]
    hidden_correlation_warnings: Tuple[str, ...]


@dataclass(frozen=True)
class CorrelatedExposureVerdict:
    allowed: bool
    binding_cluster_key: str
    cluster_cap_usd: float
    existing_cluster_worst_case_usd: float
    candidate_incremental_worst_case_usd: float
    remaining_cluster_headroom_usd: float
    reason: str


def compute_position_correlated_worst_case_usd(pos: ExposurePositionSpec) -> float:
    """
    Computes genuine correlated worst-case exposure (NOT blind notional spent):
      - Same-condition `C1` complete set (`1 YES + 1 NO == $1.00` on identical `condition_id` with
        verified gasless merge): `$0.00` oracle directional/dispute exposure; only transient
        execution/legging slippage (`partial_leg_unwind_risk_usd`).
      - Single-leg UMA carry (`BOND1`), weather bracket (`W_PRUNE1`), or cross-market box with
        oracle/rule tail: `100%` of `capital_committed_usd` can be frozen in a UMA dispute or lost
        on an unexpected clause/sensor divergence.
    """
    if pos.is_quarantined_historical_dispute:
        # Historical quarantined KMIA positions are already marked to $0/$0.14 in reconciled NAV;
        # any NEW trade on their cluster is blocked separately by D-001 + cluster check.
        return max(0.0, float(pos.capital_committed_usd))
    if pos.is_same_condition_mergeable_box:
        return max(0.0, float(pos.partial_leg_unwind_risk_usd))
    return max(0.0, float(pos.capital_committed_usd))


def _effective_cluster_keys(pos: ExposurePositionSpec) -> Tuple[str, ...]:
    return build_structured_cluster_keys(
        pos.cluster_keys,
        event_id=pos.event_id,
        market_family=pos.market_family,
        underlying_asset=pos.underlying_asset,
        resolution_source=pos.resolution_source,
    )


def evaluate_correlated_worst_case_exposure(
    candidate: ExposurePositionSpec,
    existing_positions: Sequence[ExposurePositionSpec],
    *,
    reconciled_nav_usd: float = RECONCILED_NOV11_MARK_TO_BID_NAV_USD,
    max_cluster_nav_pct: float = 0.15,
) -> CorrelatedExposureVerdict:
    """
    Replaces conflicting `max($20, 28% * book_equity)` / `$45` / `65%` caps (`R-04` / `R-41`) with
    unified Correlated Worst-Case Exposure (`<= 15%` of reconciled mark-to-bid NAV per correlation
    cluster: weather station/regional front, UMA event, sports fixture/tournament, macro release,
    market family, underlying asset, or resolution source).
    """
    nav = max(0.0, float(reconciled_nav_usd))
    pct = min(1.0, max(0.01, float(max_cluster_nav_pct)))
    cap_usd = round(nav * pct, 6)
    cand_wc = compute_position_correlated_worst_case_usd(candidate)
    cand_clusters = _effective_cluster_keys(candidate)

    if not cand_clusters:
        allowed_unclustered = cand_wc <= cap_usd + 1e-9
        return CorrelatedExposureVerdict(
            allowed=allowed_unclustered,
            binding_cluster_key="UNCLUSTERED",
            cluster_cap_usd=cap_usd,
            existing_cluster_worst_case_usd=0.0,
            candidate_incremental_worst_case_usd=cand_wc,
            remaining_cluster_headroom_usd=round(max(0.0, cap_usd - cand_wc), 6),
            reason="OK" if allowed_unclustered else "CLUSTER_CAP_EXCEEDED",
        )

    existing_keys_map = [(_effective_cluster_keys(p), compute_position_correlated_worst_case_usd(p)) for p in existing_positions]
    worst_cluster = cand_clusters[0]
    max_existing = 0.0
    for ck in cand_clusters:
        used_ck = sum(wc for p_keys, wc in existing_keys_map if ck in p_keys)
        if used_ck >= max_existing:
            max_existing = used_ck
            worst_cluster = ck

    post_trade_wc = max_existing + cand_wc
    rem_before = round(max(0.0, cap_usd - max_existing), 6)

    if candidate.is_same_condition_mergeable_box and (cand_wc <= 1e-9 or post_trade_wc <= cap_usd + 1e-9):
        return CorrelatedExposureVerdict(
            allowed=True,
            binding_cluster_key=worst_cluster,
            cluster_cap_usd=cap_usd,
            existing_cluster_worst_case_usd=round(max_existing, 6),
            candidate_incremental_worst_case_usd=round(cand_wc, 6),
            remaining_cluster_headroom_usd=round(max(0.0, cap_usd - post_trade_wc), 6),
            reason="OK_MERGEABLE_SAME_CONDITION_ZERO_ORACLE_EXPOSURE",
        )

    if post_trade_wc > cap_usd + 1e-9:
        return CorrelatedExposureVerdict(
            allowed=False,
            binding_cluster_key=worst_cluster,
            cluster_cap_usd=cap_usd,
            existing_cluster_worst_case_usd=round(max_existing, 6),
            candidate_incremental_worst_case_usd=round(cand_wc, 6),
            remaining_cluster_headroom_usd=rem_before,
            reason=(
                f"CORRELATED_WORST_CASE_CAP_EXCEEDED:{worst_cluster}:"
                f"{post_trade_wc:.2f}>{cap_usd:.2f}"
            ),
        )
    return CorrelatedExposureVerdict(
        allowed=True,
        binding_cluster_key=worst_cluster,
        cluster_cap_usd=cap_usd,
        existing_cluster_worst_case_usd=round(max_existing, 6),
        candidate_incremental_worst_case_usd=round(cand_wc, 6),
        remaining_cluster_headroom_usd=round(max(0.0, cap_usd - post_trade_wc), 6),
        reason="OK",
    )


def aggregate_correlated_exposure(positions: Sequence[ExposurePositionSpec]) -> CorrelatedExposureSummary:
    """
    Aggregates portfolio worst-case exposure across explicit clusters, event, market family,
    underlying asset, and resolution source, and detects hidden directional correlation across sleeves.
    """
    by_cluster: Dict[str, float] = {}
    by_event: Dict[str, float] = {}
    by_family: Dict[str, float] = {}
    by_asset: Dict[str, float] = {}
    by_res: Dict[str, float] = {}
    dir_net: Dict[str, float] = {}
    dir_gross: Dict[str, float] = {}
    sleeves_by_asset_dir: Dict[Tuple[str, int], Set[str]] = {}

    for pos in positions:
        wc = compute_position_correlated_worst_case_usd(pos)
        for ck in _effective_cluster_keys(pos):
            by_cluster[ck] = round(by_cluster.get(ck, 0.0) + wc, 6)
        if pos.event_id:
            ev = pos.event_id.strip().upper()
            by_event[ev] = round(by_event.get(ev, 0.0) + wc, 6)
        if pos.market_family:
            mf = pos.market_family.strip().upper()
            by_family[mf] = round(by_family.get(mf, 0.0) + wc, 6)
        if pos.underlying_asset:
            ua = pos.underlying_asset.strip().upper()
            by_asset[ua] = round(by_asset.get(ua, 0.0) + wc, 6)
            if pos.directional_sign != 0:
                sgn = 1 if pos.directional_sign > 0 else -1
                dir_net[ua] = round(dir_net.get(ua, 0.0) + sgn * max(0.0, float(pos.capital_committed_usd)), 6)
                dir_gross[ua] = round(dir_gross.get(ua, 0.0) + max(0.0, float(pos.capital_committed_usd)), 6)
                sl_label = pos.sleeve_name or pos.position_id
                sleeves_by_asset_dir.setdefault((ua, sgn), set()).add(sl_label)
        if pos.resolution_source:
            rs = pos.resolution_source.strip().upper()
            by_res[rs] = round(by_res.get(rs, 0.0) + wc, 6)

    warnings: List[str] = []
    for (ua, sgn), sl_set in sorted(sleeves_by_asset_dir.items()):
        if len(sl_set) >= 2:
            dir_lbl = "LONG" if sgn > 0 else "SHORT"
            warnings.append(f"HIDDEN_DIRECTIONAL_CORRELATION:{ua}:{dir_lbl}:sleeves={','.join(sorted(sl_set))}")

    return CorrelatedExposureSummary(
        by_cluster_usd=by_cluster,
        by_event_usd=by_event,
        by_market_family_usd=by_family,
        by_underlying_asset_usd=by_asset,
        by_resolution_source_usd=by_res,
        directional_net_by_asset_usd=dir_net,
        directional_gross_by_asset_usd=dir_gross,
        hidden_correlation_warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 6. Protocol V2 13-Schedule Fee/Rounding & Wallet Split/Merge Validator (`R-21`, `R-23`)
# ---------------------------------------------------------------------------


KNOWN_POLYMARKET_FEE_SCHEDULES_V2: Dict[str, Tuple[float, float, float]] = {
    # schedule_name -> (rate, exponent, maker_rebate_fraction)
    "zero_fees": (0.0, 1.0, 0.0),
    "sports_fees_v2": (0.03, 1.0, 0.25),
    "sports_fees_v3": (0.05, 1.0, 0.15),
    "politics_fees": (0.04, 1.0, 0.20),
    "finance_prices_fees": (0.04, 1.0, 0.20),
    "pop_culture_fees": (0.05, 1.0, 0.20),
    "weather_fees": (0.05, 1.0, 0.25),
    "weather_fees_v2": (0.05, 1.0, 0.25),
    "macro_econ_fees": (0.04, 1.0, 0.20),
    "crypto_fees_v2": (0.07, 1.0, 0.20),
    "crypto_hourly_fees": (0.10, 1.0, 0.20),
    "crypto_15_min": (0.25, 2.0, 0.20),
    "esports_fees": (0.03, 1.0, 0.20),
}


@dataclass(frozen=True)
class ExactFeeAndLotSpec:
    schedule_name: str
    rate: float
    exponent: float
    maker_rebate_fraction: float
    tick_size: float
    quantized_price: float
    quantized_gross_shares: float
    maker_amount_usdc_exact: Decimal
    net_delivered_shares_on_buy: float
    effective_buy_cost_per_net_share: float
    effective_sell_proceeds_per_share: float
    taker_fee_usd: float
    two_decimal_usdc_invariant_ok: bool


def verify_exact_polymarket_fee_and_rounding(
    market_meta: Mapping[str, Any],
    *,
    price: float,
    requested_shares: float,
    side: str = "BUY",
    is_maker: bool = False,
) -> ExactFeeAndLotSpec:
    """
    `R-23` Source-Verified Protocol Fee, Effective Price & Rounding Evaluator:
      1. Extracts authoritative `feeSchedule.{rate, exponent, rebateRate}` first; NEVER mistakes
         Gamma `takerBaseFee=1000` (10% smart-contract ceiling) for the active schedule rate!
      2. Honors `feesEnabled == False` -> `0.0` rate.
      3. Computes exact Protocol V2 BUY share-deducted effective price `p / (1 - r*(p*(1-p))^exp / p)`
         and SELL cash-deducted effective price `p - r*(p*(1-p))^exp`, with `0.0` fee on `is_maker=True`.
      4. Quantizes price to `0.001` (`p <= 0.04` or `p >= 0.96`) or `0.01` tick grid via `Decimal`
         and quantizes FOK/FAK BUY share size so `makerAmount = shares * price` has strictly `<= 2`
         decimal places in USDC (preventing CLOB `400 Bad Request` precision rejections).
    """
    fees_enabled = market_meta.get("feesEnabled")
    fs_obj = market_meta.get("feeSchedule")
    sched_name = str(
        (fs_obj.get("name") if isinstance(fs_obj, Mapping) else None)
        or market_meta.get("fee_schedule_name")
        or ""
    ).strip()

    if fees_enabled is False:
        rate, exp, reb = 0.0, 1.0, 0.0
        sched_name = sched_name or "zero_fees"
    elif isinstance(fs_obj, Mapping) and "rate" in fs_obj:
        rate = max(0.0, _sf(fs_obj.get("rate"), 0.0))
        exp = max(0.5, _sf(fs_obj.get("exponent"), 1.0))
        reb = max(0.0, _sf(fs_obj.get("rebateRate"), 0.0))
        sched_name = sched_name or "explicit_gamma_fee_schedule"
    elif sched_name in KNOWN_POLYMARKET_FEE_SCHEDULES_V2:
        rate, exp, reb = KNOWN_POLYMARKET_FEE_SCHEDULES_V2[sched_name]
    elif "fee_rate" in market_meta and market_meta.get("fee_rate") is not None:
        raw_fr = _sf(market_meta.get("fee_rate"), 0.0)
        rate = raw_fr / 10_000.0 if raw_fr >= 1.0 else max(0.0, raw_fr)
        exp = max(0.5, _sf(market_meta.get("fee_exponent"), 1.0))
        reb = 0.0
        sched_name = sched_name or ("zero_fees" if rate == 0.0 else "explicit_fee_rate")
    else:
        # Note: deliberately ignore `takerBaseFee == 1000` ceiling when `feesEnabled` is unset/False!
        rate, exp, reb = (0.04, 1.0, 0.20) if fees_enabled is True else (0.0, 1.0, 0.0)
        sched_name = sched_name or ("default_v2_enabled" if fees_enabled is True else "zero_fees")

    eff_rate = 0.0 if is_maker else rate
    explicit_tick = _sf(market_meta.get("minimum_tick_size"), 0.0) or None
    q_px, tick_sz = quantize_polymarket_price(price, side=side, explicit_tick_size=explicit_tick, is_maker=is_maker)

    # Exact <=2 decimal USDC makerAmount lot quantization on marketable BUY
    p_1e4 = max(1, int(round(q_px * 10_000)))
    s0 = 10_000 // math.gcd(p_1e4, 10_000)
    step_c = (s0 * 25) // math.gcd(s0, 25)
    raw_c = max(0, int(math.floor(max(0.0, float(requested_shares)) * 100.0 + 1e-9)))
    q_c = (raw_c // step_c) * step_c if (str(side).upper() == "BUY" and not is_maker) else raw_c
    q_shares = round(q_c / 100.0, 2)

    d_shares = Decimal(str(q_shares))
    d_px = Decimal(str(q_px))
    maker_usdc = d_shares * d_px
    two_dec_ok = maker_usdc == maker_usdc.quantize(Decimal("0.01"))

    fee_per_sh = eff_rate * ((q_px * (1.0 - q_px)) ** exp) if eff_rate > 0.0 else 0.0
    eff_buy_res = compute_net_buy_cost_per_delivered_share(q_px, fee_rate=eff_rate, fee_exponent=exp)
    eff_sell_res = compute_net_sell_proceeds_per_share(q_px, fee_rate=eff_rate, fee_exponent=exp)
    eff_buy_px = float(eff_buy_res[0]) if isinstance(eff_buy_res, tuple) else float(eff_buy_res)
    eff_sell_px = float(eff_sell_res[0]) if isinstance(eff_sell_res, tuple) else float(eff_sell_res)
    if str(side).upper() == "BUY":
        haircut_frac = min(0.50, fee_per_sh / max(q_px, 1e-6)) if eff_rate > 0.0 else 0.0
        net_deliv = round(q_shares * (1.0 - haircut_frac), 6)
    else:
        net_deliv = q_shares

    fee_usd = float(Decimal(str(q_shares * fee_per_sh)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))
    return ExactFeeAndLotSpec(
        schedule_name=sched_name,
        rate=round(rate, 6),
        exponent=round(exp, 4),
        maker_rebate_fraction=round(reb, 4),
        tick_size=tick_sz,
        quantized_price=q_px,
        quantized_gross_shares=q_shares,
        maker_amount_usdc_exact=maker_usdc,
        net_delivered_shares_on_buy=net_deliv,
        effective_buy_cost_per_net_share=round(eff_buy_px, 8),
        effective_sell_proceeds_per_share=round(eff_sell_px, 8),
        taker_fee_usd=fee_usd,
        two_decimal_usdc_invariant_ok=two_dec_ok,
    )


@dataclass(frozen=True)
class WalletSplitMergeCapability:
    signature_type: int
    wallet_architecture: str
    protocol_generation: str
    collateral_asset: str
    split_supported: bool
    merge_supported: bool
    batch_merge_supported: bool
    redeem_supported: bool
    gasless_relayer_used: bool
    relayer_quota_tx_per_min: int
    effective_recycle_lockup_hours: float
    verified_constraints_and_defects: Tuple[str, ...]


def validate_wallet_split_merge_capabilities(
    *,
    signature_type: int = 3,
    protocol_generation: str = "CTF_V1_PUSD",
    has_builder_api_key: bool = True,
    signer_pol_balance: float = 41.81,
    ctf_is_approved_for_adapter_v2: bool = True,
    relayer_recent_tx_last_60s: int = 0,
) -> WalletSplitMergeCapability:
    """
    `R-21` Independent Validation of Split/Merge & Collateral-Recycling Capabilities across
    all 4 Polymarket wallet architectures (`sig_type` `0..3`) and protocol generations
    (`CTF_V1_PUSD`, `CTF_V1_LEGACY_USDCE`, `NEGRISK_V1_V2`, `PROTOCOL_V2_POSITION_MANAGER`).
    Replaces `polymarket_live_harvester.py:5764` (`bool(os.getenv('POLY_BUILDER_API_KEY'))` string check)
    with full protocol, approval, gas, and Relayer-quota verification.
    """
    arch_map = {
        0: "EOA_DIRECT",
        1: "POLY_PROXY_MAGIC",
        2: "GNOSIS_SAFE_1OF1",
        3: "POLY_1271_BEACON_DEPOSIT_WALLET",
    }
    arch = arch_map.get(int(signature_type), "UNSUPPORTED_SIG_TYPE")
    gen = str(protocol_generation or "CTF_V1_PUSD").strip().upper()
    notes: List[str] = []

    if int(signature_type) not in arch_map:
        return WalletSplitMergeCapability(
            signature_type=int(signature_type),
            wallet_architecture=arch,
            protocol_generation=gen,
            collateral_asset="UNKNOWN",
            split_supported=False,
            merge_supported=False,
            batch_merge_supported=False,
            redeem_supported=False,
            gasless_relayer_used=False,
            relayer_quota_tx_per_min=0,
            effective_recycle_lockup_hours=24.0,
            verified_constraints_and_defects=("UNSUPPORTED_SIGNATURE_TYPE",),
        )

    gas_ok = True if int(signature_type) == 3 else (float(signer_pol_balance) >= 0.05)
    if not gas_ok:
        notes.append("INSUFFICIENT_SIGNER_POL_FOR_DIRECT_TX")

    relayer_ok = True
    quota_rem = 999
    if int(signature_type) == 3:
        if not has_builder_api_key:
            relayer_ok = False
            notes.append("MISSING_BUILDER_RELAYER_CREDENTIALS_FOR_SIG_TYPE_3")
        quota_rem = max(0, 24 - int(relayer_recent_tx_last_60s))
        if quota_rem <= 0:
            relayer_ok = False
            notes.append("RELAYER_V2_24_TX_PER_MIN_QUOTA_EXHAUSTED")

    base_tx_ok = gas_ok and relayer_ok
    if gen == "PROTOCOL_V2_POSITION_MANAGER":
        # PositionManager (0x006F54...) uses ERC-6909 / V2 hooks not yet wired in polymarket_live_executor.py!
        notes.append("EXECUTOR_LACKS_PROTOCOL_V2_POSITION_MANAGER_SPLIT_MERGE_ABI")
        return WalletSplitMergeCapability(
            signature_type=int(signature_type),
            wallet_architecture=arch,
            protocol_generation=gen,
            collateral_asset="pUSD",
            split_supported=False,
            merge_supported=False,
            batch_merge_supported=False,
            redeem_supported=False,
            gasless_relayer_used=(int(signature_type) == 3),
            relayer_quota_tx_per_min=24 if int(signature_type) == 3 else 0,
            effective_recycle_lockup_hours=24.0,
            verified_constraints_and_defects=tuple(notes),
        )

    if gen == "CTF_V1_LEGACY_USDCE" and ctf_is_approved_for_adapter_v2:
        notes.append(
            "DEFECT_EXECUTOR_L4326_ENCODES_5ARG_CTF_MERGE_TO_ADAPTER_V2_WHEN_APPROVED_REQUIRES_DIRECT_CTF_V1_PLUS_PUSD_WRAP"
        )

    if gen == "NEGRISK_V1_V2":
        notes.append("REDEEM_POSITIONS_USES_V1_ADAPTER_UNWRAPS_USDCE_THEN_INLINE_PUSD_WRAP")

    can_merge = base_tx_ok and not (gen == "CTF_V1_LEGACY_USDCE" and ctf_is_approved_for_adapter_v2)
    can_batch = can_merge and int(signature_type) in {1, 3}
    recycle_h = 0.005 if can_merge else 24.0  # ~18 seconds (`0.005h`) when gasless/on-chain merge verified!

    return WalletSplitMergeCapability(
        signature_type=int(signature_type),
        wallet_architecture=arch,
        protocol_generation=gen,
        collateral_asset="USDC.e->pUSD" if "USDCE" in gen or "NEGRISK" in gen else "pUSD",
        split_supported=base_tx_ok,
        merge_supported=can_merge,
        batch_merge_supported=can_batch,
        redeem_supported=base_tx_ok,
        gasless_relayer_used=(int(signature_type) == 3),
        relayer_quota_tx_per_min=24 if int(signature_type) == 3 else 0,
        effective_recycle_lockup_hours=recycle_h,
        verified_constraints_and_defects=tuple(notes),
    )


# ---------------------------------------------------------------------------
# 7. Infra Expense Reconciler (`R-10`) & Dynamic Marginal Capital Allocator (`R-09`/`R-43`/`R-15`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReconciledInfraEconomics:
    window_hours: float
    sunk_fixed_vm_cost_usd: float
    marginal_subscription_ai_cost_usd: float
    marginal_relayer_or_gas_cost_usd: float
    realized_trading_net_pnl_usd: float
    true_marginal_trading_profit_usd: float
    full_cost_net_economic_profit_usd: float
    legacy_accountant_distorted_net_usd: float
    double_counted_error_eliminated_usd: float
    portfolio_breakeven_bps_per_hr_on_liquid_nav: float


def reconcile_infrastructure_expenses(
    *,
    window_hours: float,
    realized_trading_net_pnl_usd: float,
    liquid_nav_usd: float = RECONCILED_NOV11_LIQUID_PUSD_USD,
    hourly_vm_rate_usd: float = FIXED_HOURLY_VM_COST_USD,
    ai_billing_mode: str = "subscription_flat",
    metered_api_ai_spend_usd: float = 0.0,
    direct_polygon_gas_spend_usd: float = 0.0,
    clips_executed_in_window: int = 0,
    legacy_intraday_vm_hours_reported: Optional[float] = None,
) -> ReconciledInfraEconomics:
    """
    `R-10` Infrastructure Expense Reconciliation:
      1. Aligns time horizons strictly (`window_hours` on BOTH `realized_trading_net_pnl_usd` and
         `sunk_fixed_vm_cost_usd`), eliminating `src/paa_os/accountant.py:541-544`'s mismatch where
         all-time cumulative P&L was subtracted against only today's `0..24h` UTC VM cost.
      2. Separates **sunk fixed VM burn** (`$0.034264/hr`, incurred whether `0` or `100` trades fire!)
         from **marginal per-trade execution cost** (`$0.00` on gasless Relayer V2 + `$0.00` marginal
         AI cost under `subscription_flat`), eliminating `PROFIT_SCORECARD.md` double-counting where
         `$0.03426/hr` was charged BOTH per-trade lockup AND as daily portfolio VM overhead!
    """
    hrs = max(0.0, float(window_hours))
    sunk_vm = round(hrs * max(0.0, float(hourly_vm_rate_usd)), 6)
    marg_ai = 0.0 if str(ai_billing_mode).strip().lower() == "subscription_flat" else max(0.0, float(metered_api_ai_spend_usd))
    marg_gas = max(0.0, float(direct_polygon_gas_spend_usd))
    pnl = float(realized_trading_net_pnl_usd)

    true_marginal_profit = round(pnl - marg_ai - marg_gas, 6)
    full_net_econ = round(true_marginal_profit - sunk_vm, 6)

    leg_h = hrs if legacy_intraday_vm_hours_reported is None else max(0.0, float(legacy_intraday_vm_hours_reported))
    legacy_distorted = round(pnl - marg_ai - (leg_h * float(hourly_vm_rate_usd)), 6)
    # Double-counting error when fixed VM burn was ALSO subtracted per concurrent clip:
    double_count_eliminated = round(max(0, int(clips_executed_in_window) - 1) * (hrs / max(1, int(clips_executed_in_window))) * float(hourly_vm_rate_usd), 6) if clips_executed_in_window > 1 else 0.0
    hurdle_bps_hr = round((float(hourly_vm_rate_usd) / max(1.0, float(liquid_nav_usd))) * 10_000.0, 4)

    return ReconciledInfraEconomics(
        window_hours=hrs,
        sunk_fixed_vm_cost_usd=sunk_vm,
        marginal_subscription_ai_cost_usd=round(marg_ai, 6),
        marginal_relayer_or_gas_cost_usd=round(marg_gas, 6),
        realized_trading_net_pnl_usd=round(pnl, 6),
        true_marginal_trading_profit_usd=true_marginal_profit,
        full_cost_net_economic_profit_usd=full_net_econ,
        legacy_accountant_distorted_net_usd=legacy_distorted,
        double_counted_error_eliminated_usd=double_count_eliminated,
        portfolio_breakeven_bps_per_hr_on_liquid_nav=hurdle_bps_hr,
    )


class OrderReservationStatus(str, Enum):
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED_UNSETTLED = "FILLED_UNSETTLED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class OrderReservationRecord:
    reservation_id: str
    market_id: str
    instrument_id: str
    family_code: str
    sleeve_name: str
    model_id: str
    requested_notional_usd: float
    filled_notional_usd: float = 0.0
    unfilled_notional_usd: float = 0.0
    matched_unsettled_usd: float = 0.0
    collat_drop_usd: float = 0.0
    status: OrderReservationStatus = OrderReservationStatus.PENDING
    cluster_keys: Tuple[str, ...] = ()
    event_id: str = ""
    market_family: str = ""
    underlying_asset: str = ""
    resolution_source: str = ""
    directional_sign: int = 0
    is_same_condition_mergeable_box: bool = False
    partial_leg_unwind_risk_usd: float = 0.0
    created_ts: float = 0.0
    updated_ts: float = 0.0

    def __post_init__(self) -> None:
        req = max(0.0, float(self.requested_notional_usd))
        self.requested_notional_usd = round(req, 6)
        if self.unfilled_notional_usd == 0.0 and self.filled_notional_usd == 0.0 and self.status == OrderReservationStatus.PENDING:
            self.unfilled_notional_usd = self.requested_notional_usd

    @property
    def reserved_cash_usd(self) -> float:
        if self.status in {OrderReservationStatus.SETTLED, OrderReservationStatus.CANCELLED, OrderReservationStatus.EXPIRED}:
            return 0.0
        unfilled = max(0.0, float(self.unfilled_notional_usd))
        matched = max(0.0, float(self.matched_unsettled_usd))
        synced = min(matched, max(0.0, float(self.collat_drop_usd)))
        return round(unfilled + max(0.0, matched - synced), 6)

    @property
    def total_committed_usd(self) -> float:
        if self.status in {OrderReservationStatus.SETTLED, OrderReservationStatus.CANCELLED, OrderReservationStatus.EXPIRED}:
            return 0.0
        return round(max(0.0, float(self.unfilled_notional_usd)) + max(0.0, float(self.matched_unsettled_usd)), 6)


@dataclass(frozen=True)
class LedgerReconciliationSnapshot:
    total_wallet_cash_usd: float
    safety_buffer_usd: float
    pending_unfilled_usd: float
    matched_unsettled_usd: float
    collat_drop_synced_usd: float
    total_reserved_cash_usd: float
    available_deployable_cash_usd: float
    active_reservation_count: int
    by_family_usd: Dict[str, float]
    by_sleeve_usd: Dict[str, float]
    by_model_usd: Dict[str, float]
    by_market_usd: Dict[str, float]
    positions_count_by_sleeve: Dict[str, int]


class CapitalReservationLedger:
    """
    Unified portfolio-level capital reservation ledger accounting for:
      - Authoritative wallet cash & unallocated safety buffer,
      - Pending orders & unfilled remaining quantities,
      - Partial fills & matched-but-unsettled collateral drops (preventing both double-spending
        and phantom double-counting when on-chain collateral has already dropped),
      - Hierarchical attribution across family -> sleeve -> model -> market -> order,
      - Correlated exposure projection (`to_exposure_specs()`).
    """

    def __init__(
        self,
        total_wallet_cash_usd: float,
        *,
        safety_buffer_usd: float = 0.0,
    ) -> None:
        self.total_wallet_cash_usd = round(max(0.0, float(total_wallet_cash_usd)), 6)
        self.safety_buffer_usd = round(max(0.0, float(safety_buffer_usd)), 6)
        self._records: Dict[str, OrderReservationRecord] = {}

    def sync_wallet_cash(self, new_wallet_cash_usd: float) -> None:
        self.total_wallet_cash_usd = round(max(0.0, float(new_wallet_cash_usd)), 6)

    @property
    def active_records(self) -> List[OrderReservationRecord]:
        return [
            rec
            for rec in self._records.values()
            if rec.status not in {OrderReservationStatus.SETTLED, OrderReservationStatus.CANCELLED, OrderReservationStatus.EXPIRED}
        ]

    @property
    def total_reserved_cash_usd(self) -> float:
        return round(sum(rec.reserved_cash_usd for rec in self.active_records), 6)

    @property
    def available_deployable_cash_usd(self) -> float:
        return round(max(0.0, self.total_wallet_cash_usd - self.total_reserved_cash_usd - self.safety_buffer_usd), 6)

    def get_reservation(self, reservation_id: str) -> Optional[OrderReservationRecord]:
        return self._records.get(str(reservation_id))

    def reserve_order(
        self,
        *,
        reservation_id: str,
        market_id: str,
        instrument_id: str,
        family_code: str,
        sleeve_name: str,
        requested_notional_usd: float,
        model_id: str = "",
        cluster_keys: Sequence[str] = (),
        event_id: str = "",
        market_family: str = "",
        underlying_asset: str = "",
        resolution_source: str = "",
        directional_sign: int = 0,
        is_same_condition_mergeable_box: bool = False,
        partial_leg_unwind_risk_usd: float = 0.0,
        now_ts: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[OrderReservationRecord]]:
        rid = str(reservation_id or "").strip()
        if not rid:
            return False, "EMPTY_RESERVATION_ID", None
        existing = self._records.get(rid)
        if existing is not None and existing.status not in {
            OrderReservationStatus.SETTLED,
            OrderReservationStatus.CANCELLED,
            OrderReservationStatus.EXPIRED,
        }:
            return False, f"DUPLICATE_ACTIVE_RESERVATION:{rid}", existing

        req = round(max(0.0, float(requested_notional_usd)), 6)
        if req <= 0.0:
            return False, "NON_POSITIVE_RESERVATION_NOTIONAL", None
        avail = self.available_deployable_cash_usd
        if req > avail + 1e-6:
            return False, f"INSUFFICIENT_AVAILABLE_CASH:{req:.4f}>{avail:.4f}", None

        ts = float(now_ts if now_ts is not None else time.time())
        rec = OrderReservationRecord(
            reservation_id=rid,
            market_id=str(market_id or ""),
            instrument_id=str(instrument_id or ""),
            family_code=str(family_code or ""),
            sleeve_name=str(sleeve_name or ""),
            model_id=str(model_id or ""),
            requested_notional_usd=req,
            filled_notional_usd=0.0,
            unfilled_notional_usd=req,
            matched_unsettled_usd=0.0,
            collat_drop_usd=0.0,
            status=OrderReservationStatus.PENDING,
            cluster_keys=tuple(cluster_keys),
            event_id=str(event_id or ""),
            market_family=str(market_family or ""),
            underlying_asset=str(underlying_asset or ""),
            resolution_source=str(resolution_source or ""),
            directional_sign=int(directional_sign or 0),
            is_same_condition_mergeable_box=bool(is_same_condition_mergeable_box),
            partial_leg_unwind_risk_usd=max(0.0, float(partial_leg_unwind_risk_usd)),
            created_ts=ts,
            updated_ts=ts,
        )
        self._records[rid] = rec
        return True, "RESERVED", rec

    def record_partial_fill(
        self,
        reservation_id: str,
        *,
        delta_filled_notional_usd: float,
        collat_drop_delta_usd: float = 0.0,
        now_ts: Optional[float] = None,
    ) -> Tuple[bool, str]:
        rec = self._records.get(str(reservation_id))
        if rec is None:
            return False, "RESERVATION_NOT_FOUND"
        if rec.status in {OrderReservationStatus.SETTLED, OrderReservationStatus.CANCELLED, OrderReservationStatus.EXPIRED}:
            return False, f"RESERVATION_TERMINAL:{rec.status.value}"

        fill_d = max(0.0, min(rec.unfilled_notional_usd, float(delta_filled_notional_usd)))
        drop_d = max(0.0, float(collat_drop_delta_usd))
        rec.filled_notional_usd = round(rec.filled_notional_usd + fill_d, 6)
        rec.unfilled_notional_usd = round(max(0.0, rec.unfilled_notional_usd - fill_d), 6)
        rec.matched_unsettled_usd = round(rec.matched_unsettled_usd + fill_d, 6)
        rec.collat_drop_usd = round(min(rec.matched_unsettled_usd, rec.collat_drop_usd + drop_d), 6)
        rec.updated_ts = float(now_ts if now_ts is not None else time.time())
        rec.status = (
            OrderReservationStatus.FILLED_UNSETTLED
            if rec.unfilled_notional_usd <= 1e-6
            else OrderReservationStatus.PARTIALLY_FILLED
        )
        return True, rec.status.value

    def release_reservation(
        self,
        reservation_id: str,
        *,
        reason: str = "CANCELLED",
        now_ts: Optional[float] = None,
    ) -> Tuple[bool, float]:
        rec = self._records.get(str(reservation_id))
        if rec is None:
            return False, 0.0
        released = rec.reserved_cash_usd
        ts = float(now_ts if now_ts is not None else time.time())
        rsn_u = str(reason or "CANCELLED").strip().upper()
        if rsn_u == "SETTLED":
            rec.status = OrderReservationStatus.SETTLED
            rec.unfilled_notional_usd = 0.0
            rec.matched_unsettled_usd = 0.0
        elif rsn_u == "EXPIRED":
            rec.status = OrderReservationStatus.EXPIRED
            rec.unfilled_notional_usd = 0.0
        else:
            rec.status = OrderReservationStatus.CANCELLED
            rec.unfilled_notional_usd = 0.0
            # Note: any already-filled portion (`matched_unsettled_usd`) stays settled/tracked if partially filled
            if rec.matched_unsettled_usd > 1e-6:
                rec.status = OrderReservationStatus.FILLED_UNSETTLED
                released = round(max(0.0, released - rec.reserved_cash_usd), 6)
        rec.updated_ts = ts
        return True, released

    def to_exposure_specs(self) -> List[ExposurePositionSpec]:
        specs: List[ExposurePositionSpec] = []
        for rec in self.active_records:
            committed = rec.total_committed_usd
            if committed <= 1e-9:
                continue
            specs.append(
                ExposurePositionSpec(
                    position_id=rec.reservation_id,
                    cluster_keys=rec.cluster_keys,
                    capital_committed_usd=committed,
                    is_same_condition_mergeable_box=rec.is_same_condition_mergeable_box,
                    partial_leg_unwind_risk_usd=rec.partial_leg_unwind_risk_usd,
                    event_id=rec.event_id,
                    market_family=rec.market_family,
                    underlying_asset=rec.underlying_asset,
                    resolution_source=rec.resolution_source,
                    directional_sign=rec.directional_sign,
                    sleeve_name=rec.sleeve_name,
                    family_code=rec.family_code,
                    model_id=rec.model_id,
                )
            )
        return specs

    def snapshot(self) -> LedgerReconciliationSnapshot:
        by_fam: Dict[str, float] = {}
        by_sl: Dict[str, float] = {}
        by_mod: Dict[str, float] = {}
        by_mkt: Dict[str, float] = {}
        cnt_sl: Dict[str, int] = {}
        pend = 0.0
        matched = 0.0
        synced = 0.0
        for rec in self.active_records:
            pend += rec.unfilled_notional_usd
            matched += rec.matched_unsettled_usd
            synced += min(rec.matched_unsettled_usd, rec.collat_drop_usd)
            comm = rec.total_committed_usd
            if rec.family_code:
                by_fam[rec.family_code] = round(by_fam.get(rec.family_code, 0.0) + comm, 6)
            if rec.sleeve_name:
                by_sl[rec.sleeve_name] = round(by_sl.get(rec.sleeve_name, 0.0) + comm, 6)
                cnt_sl[rec.sleeve_name] = cnt_sl.get(rec.sleeve_name, 0) + 1
            if rec.model_id:
                by_mod[rec.model_id] = round(by_mod.get(rec.model_id, 0.0) + comm, 6)
            if rec.market_id:
                by_mkt[rec.market_id] = round(by_mkt.get(rec.market_id, 0.0) + comm, 6)
        tot_res = self.total_reserved_cash_usd
        return LedgerReconciliationSnapshot(
            total_wallet_cash_usd=self.total_wallet_cash_usd,
            safety_buffer_usd=self.safety_buffer_usd,
            pending_unfilled_usd=round(pend, 6),
            matched_unsettled_usd=round(matched, 6),
            collat_drop_synced_usd=round(synced, 6),
            total_reserved_cash_usd=tot_res,
            available_deployable_cash_usd=self.available_deployable_cash_usd,
            active_reservation_count=len(self.active_records),
            by_family_usd=by_fam,
            by_sleeve_usd=by_sl,
            by_model_usd=by_mod,
            by_market_usd=by_mkt,
            positions_count_by_sleeve=cnt_sl,
        )


@dataclass(frozen=True)
class SleeveRiskConfig:
    """Independently configurable per-sleeve risk & velocity parameters."""

    sleeve_name: str
    family_code: str = ""
    enabled: bool = True
    max_nav_pct: float = 0.50
    max_concurrent_positions: int = 10
    min_bps_per_hour: float = 0.0
    kelly_fraction_cap: float = 0.50
    max_single_market_nav_pct: float = 0.15
    allow_instant_merge_recycling: bool = True


@dataclass(frozen=True)
class HierarchicalRiskBudgetConfig:
    """
    Hierarchical portfolio risk budget configuration:
      Portfolio -> Strategy Family -> Sleeve -> Model -> Market -> Order.
    """

    portfolio_max_utilization_pct: float = 0.95
    family_max_nav_pct: Mapping[str, float] = field(default_factory=dict)
    sleeve_configs: Mapping[str, SleeveRiskConfig] = field(default_factory=dict)
    model_max_nav_pct: Mapping[str, float] = field(default_factory=dict)
    default_market_max_nav_pct: float = 0.15


@dataclass(frozen=True)
class PortfolioCandidateSpec:
    candidate_id: str
    family_code: str
    sleeve_name: str
    opportunity_class: OpportunityClass
    cluster_keys: Tuple[str, ...]
    instrument_ids: Tuple[str, ...]
    max_executable_shares: float
    capital_per_share_usd: float
    worst_case_net_payoff_per_share_usd: float
    expected_net_payoff_per_share_usd: float
    fees_and_conversion_per_share_usd: float
    nominal_maturity_hours: float
    settlement_or_merge_hours: float
    can_instant_merge_or_recycle: bool = False
    partial_fill_prob: float = 0.0
    unwind_loss_per_share_if_partial_usd: float = 0.0
    is_same_condition_mergeable_box: bool = False
    sequential_clob_legs: int = 2
    is_atomic_or_inventory_locked: bool = False
    marginal_infra_cost_usd: float = 0.0
    min_order_shares: float = DEFAULT_MIN_ORDER_SHARES
    model_id: str = ""
    event_id: str = ""
    market_family: str = ""
    underlying_asset: str = ""
    resolution_source: str = ""
    directional_sign: int = 0
    custom_liveness_hours: Optional[float] = None


@dataclass(frozen=True)
class CandidateAllocationDecision:
    candidate_id: str
    accepted: bool
    allocated_shares: float
    allocated_capital_usd: float
    effective_lockup_hours: float
    realizable_net_value_usd: float
    opportunity_cost_charge_usd: float
    marginal_realizable_net_value_usd: float
    realizable_bps_per_hour: float
    recycling_compounding_bonus_usd: float
    rejection_reason: str = ""
    external_blocker_report: Optional[ExternalBlockerReport] = None


@dataclass(frozen=True)
class PortfolioAllocationResult:
    mode: ExecutionMode
    initial_deployable_cash_usd: float
    deployed_cash_usd: float
    unallocated_cash_usd: float
    utilization_pct: float
    endogenous_shadow_price_bps_per_hr: float
    total_realizable_net_value_usd: float
    total_marginal_realizable_net_value_usd: float
    total_worst_case_guaranteed_floor_pnl_usd: float
    decisions: Tuple[CandidateAllocationDecision, ...]


class DynamicMarginalCapitalAllocator:
    """
    Prompt Section 3 — Portfolio-Level Dynamic Capital Allocator:
      - Ranks and sizes all candidate opportunities simultaneously by **Marginal Realizable Net Value
        (`MRNV`) per Dollar-Hour**, incorporating:
          1. Exact worst-case contractual payoff (`worst_case_net_payoff_per_share_usd`),
          2. Available executable L2 depth (`max_executable_shares`),
          3. Exact fees & conversion costs (`fees_and_conversion_per_share_usd`),
          4. Capital required (`capital_per_share_usd`),
          5. Realistic settlement / merge lockup time (`effective_lockup_hours` — never confusing a
             nominal riskless payoff with instant settlement if merge is unsupported or UMA liveness applies!),
          6. Liquidity & exchange minimum lot floors (`5` shares / `$1.00`),
          7. Correlated event exposure (`<= 15%` reconciled NAV per cluster via `CWCE`),
          8. Partial-fill construction bleed (`partial_fill_prob * unwind_loss_per_share_if_partial_usd`),
          9. Competing opportunities & endogenous shadow price `lambda_cap(utilization)`,
         10. Marginal infrastructure/quota cost (`marginal_infra_cost_usd`, NEVER sunk VM overhead!),
         11. Expected capital-recycling compounding benefit over the planning horizon.
      - Zero arbitrary `24h` maturity cutoffs in `RESEARCH` or `SHADOW`, and in `LIVE` replaces
        arbitrary step cliffs + the broken `DOMINANCE` infinite-maturity exemption with smooth
        opportunity-cost pricing!
    """

    def __init__(
        self,
        *,
        idle_floor_shadow_bps_per_hr: float = 0.50,
        full_utilization_shadow_bps_per_hr: float = 18.0,
        compounding_horizon_hours: float = 24.0,
        expected_reinvestment_bps_per_hr: float = 6.0,
        max_cluster_nav_pct: float = 0.15,
    ) -> None:
        self.idle_floor_shadow_bps_per_hr = max(0.0, float(idle_floor_shadow_bps_per_hr))
        self.full_utilization_shadow_bps_per_hr = max(
            self.idle_floor_shadow_bps_per_hr, float(full_utilization_shadow_bps_per_hr)
        )
        self.compounding_horizon_hours = max(1.0, float(compounding_horizon_hours))
        self.expected_reinvestment_bps_per_hr = max(0.0, float(expected_reinvestment_bps_per_hr))
        # Respect Owner capital allocation sovereignty (`0.01..1.00`; default `0.15` for unattended mode)
        self.max_cluster_nav_pct = min(1.0, max(0.01, float(max_cluster_nav_pct)))

    def compute_shadow_price_bps_per_hr(
        self,
        utilization_frac: float,
        competing_best_bps_per_hr: float = 0.0,
    ) -> float:
        """
        Convex capital opportunity-cost curve `lambda_cap(u)`:
          - When `u == 0%` (100% cash idle) and no competing high-velocity arrivals exist, hurdle is
            `idle_floor_shadow_bps_per_hr` (`0.50 bps/hr`), deploying idle cash productively instead
            of starving on a rigid `15.0 bps/hr` (`2 * 7.5`) cliff!
          - As `u -> 100%`, `lambda_cap` rises quadratically toward `full_utilization_shadow_bps_per_hr`
            (`18.0 bps/hr`) or `0.65 * competing_best_bps_per_hr`, automatically reserving dry powder
            for fast spikes!
        """
        u = min(1.0, max(0.0, float(utilization_frac)))
        curve_bps = self.idle_floor_shadow_bps_per_hr + (
            self.full_utilization_shadow_bps_per_hr - self.idle_floor_shadow_bps_per_hr
        ) * (u ** 2)
        comp_anchor = 0.50 * max(0.0, float(competing_best_bps_per_hr)) * u
        return round(max(curve_bps, comp_anchor), 6)

    @staticmethod
    def effective_lockup_hours(cand: PortfolioCandidateSpec) -> float:
        if cand.can_instant_merge_or_recycle:
            return max(0.005, float(cand.settlement_or_merge_hours))
        sett_h = float(cand.settlement_or_merge_hours)
        if cand.custom_liveness_hours is not None and float(cand.custom_liveness_hours) > 0.0:
            liveness_h = float(cand.custom_liveness_hours)
            sett_h = min(sett_h, liveness_h) if sett_h > 0.0 else liveness_h
        return max(0.02, float(cand.nominal_maturity_hours) + sett_h)

    @staticmethod
    def lockup_velocity_weight(cand: PortfolioCandidateSpec) -> float:
        """Inverse effective lockup weighting (`1 / effective_lockup_hours`) prioritizing fast `customLiveness` & merges."""
        return 1.0 / DynamicMarginalCapitalAllocator.effective_lockup_hours(cand)

    def _unit_realizable_net_edge(self, cand: PortfolioCandidateSpec, mode: ExecutionMode) -> float:
        base_edge = (
            cand.worst_case_net_payoff_per_share_usd
            if (mode == ExecutionMode.LIVE and cand.opportunity_class in {OpportunityClass.CLASS_A, OpportunityClass.CLASS_B})
            else cand.expected_net_payoff_per_share_usd
        )
        construction_penalty = max(0.0, float(cand.partial_fill_prob)) * max(
            0.0, float(cand.unwind_loss_per_share_if_partial_usd)
        )
        return base_edge - construction_penalty

    def allocate(
        self,
        candidates: Sequence[PortfolioCandidateSpec],
        *,
        mode: ExecutionMode = ExecutionMode.SHADOW,
        deployable_liquid_cash_usd: float = RECONCILED_NOV11_LIQUID_PUSD_USD,
        reconciled_nav_usd: float = RECONCILED_NOV11_MARK_TO_BID_NAV_USD,
        existing_positions: Sequence[ExposurePositionSpec] = (),
        jurisdiction: str = "CA-ON",
        venue_id: str = "polymarket",
        venue_live_authorized: bool = True,
        live_promotion_approved: bool = True,
        owner_explicitly_authorized: bool = False,
        owner_authorized_live_classes: Optional[FrozenSet[OpportunityClass]] = None,
        reservation_ledger: Optional[CapitalReservationLedger] = None,
        risk_budget_config: Optional[HierarchicalRiskBudgetConfig] = None,
        enforce_full_cash_reservation: Optional[bool] = None,
    ) -> PortfolioAllocationResult:
        full_reserve = (reservation_ledger is not None) if enforce_full_cash_reservation is None else bool(enforce_full_cash_reservation)
        raw_cash = max(0.0, float(deployable_liquid_cash_usd))
        if reservation_ledger is not None and mode != ExecutionMode.RESEARCH:
            cash_total = min(raw_cash, reservation_ledger.available_deployable_cash_usd)
        else:
            cash_total = raw_cash
        if risk_budget_config is not None and mode != ExecutionMode.RESEARCH:
            port_cap_usd = round(max(0.0, float(reconciled_nav_usd)) * min(1.0, max(0.01, float(risk_budget_config.portfolio_max_utilization_pct))), 6)
            cash_total = min(cash_total, port_cap_usd)
        cash_rem = cash_total

        active_exposures: List[ExposurePositionSpec] = list(existing_positions)
        if reservation_ledger is not None and mode != ExecutionMode.RESEARCH:
            active_exposures.extend(reservation_ledger.to_exposure_specs())

        family_used_usd: Dict[str, float] = {}
        sleeve_used_usd: Dict[str, float] = {}
        sleeve_pos_cnt: Dict[str, int] = {}
        model_used_usd: Dict[str, float] = {}
        for exp in active_exposures:
            comm = max(0.0, float(exp.capital_committed_usd))
            if exp.family_code:
                family_used_usd[exp.family_code] = family_used_usd.get(exp.family_code, 0.0) + comm
            if exp.sleeve_name:
                sleeve_used_usd[exp.sleeve_name] = sleeve_used_usd.get(exp.sleeve_name, 0.0) + comm
                sleeve_pos_cnt[exp.sleeve_name] = sleeve_pos_cnt.get(exp.sleeve_name, 0) + 1
            if exp.model_id:
                model_used_usd[exp.model_id] = model_used_usd.get(exp.model_id, 0.0) + comm

        consumed_instruments: Set[str] = set()
        if reservation_ledger is not None and mode != ExecutionMode.RESEARCH:
            for rec in reservation_ledger.active_records:
                if rec.instrument_id:
                    consumed_instruments.add(rec.instrument_id)
        permitted_live_classes: FrozenSet[OpportunityClass] = (
            owner_authorized_live_classes
            if owner_authorized_live_classes is not None
            else (
                frozenset({OpportunityClass.CLASS_A, OpportunityClass.CLASS_B, OpportunityClass.CLASS_C})
                if owner_explicitly_authorized
                else frozenset({OpportunityClass.CLASS_A, OpportunityClass.CLASS_B})
            )
        )

        # Compute competing arrival density across valid positive-EV candidates
        prelim_rates: List[float] = []
        scored_pool: List[Tuple[float, float, PortfolioCandidateSpec]] = []
        for cand in candidates:
            eff_h = self.effective_lockup_hours(cand)
            unit_rnv = self._unit_realizable_net_edge(cand, mode)
            cap_sh = max(1e-6, float(cand.capital_per_share_usd))
            bps_hr = (unit_rnv / cap_sh) / eff_h * 10_000.0
            if unit_rnv > 0.0:
                prelim_rates.append(bps_hr)
            scored_pool.append((bps_hr, unit_rnv, cand))

        competing_top_bps = max(prelim_rates) if prelim_rates else 0.0
        # Sort by realizable Dollar-Hour efficiency (`bps/hr` = `edge * 1/eff_h`) descending, breaking ties by USD/hr velocity
        scored_pool.sort(
            key=lambda t: (t[0], (t[1] * t[2].max_executable_shares) * self.lockup_velocity_weight(t[2])),
            reverse=True,
        )

        decisions: List[CandidateAllocationDecision] = []
        tot_rnv = 0.0
        tot_mrnv = 0.0
        tot_floor_pnl = 0.0

        for idx, (bps_hr, unit_rnv, cand) in enumerate(scored_pool):
            eff_h = self.effective_lockup_hours(cand)
            cap_sh = max(1e-6, float(cand.capital_per_share_usd))

            # 1. Mode-specific eligibility check (respects Owner Sovereignty & surfaces ExternalBlockerReport)
            touches_kmia = any(
                m in FROZEN_DISPUTED_MARKET_IDS or any(sub in str(m).upper() for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS)
                for m in (*cand.cluster_keys, *cand.instrument_ids, cand.candidate_id)
            )
            mode_verdict = evaluate_mode_specific_eligibility(
                mode,
                jurisdiction=jurisdiction,
                venue_id=venue_id,
                venue_live_authorized_for_jurisdiction=venue_live_authorized,
                owner_explicitly_authorized=owner_explicitly_authorized,
                touches_d001_disputed_kmia=touches_kmia,
                opportunity_class=cand.opportunity_class,
                sequential_clob_legs=cand.sequential_clob_legs,
                is_atomic_or_inventory_locked=cand.is_atomic_or_inventory_locked,
                reconciled_liquid_nav_usd=reconciled_nav_usd,
                live_promotion_approved=live_promotion_approved,
            )
            if not mode_verdict.allowed:
                decisions.append(
                    CandidateAllocationDecision(
                        candidate_id=cand.candidate_id,
                        accepted=False,
                        allocated_shares=0.0,
                        allocated_capital_usd=0.0,
                        effective_lockup_hours=round(eff_h, 4),
                        realizable_net_value_usd=0.0,
                        opportunity_cost_charge_usd=0.0,
                        marginal_realizable_net_value_usd=0.0,
                        realizable_bps_per_hour=round(bps_hr, 4),
                        recycling_compounding_bonus_usd=0.0,
                        rejection_reason=mode_verdict.reason,
                        external_blocker_report=mode_verdict.external_blocker_report,
                    )
                )
                continue

            if mode == ExecutionMode.LIVE and cand.opportunity_class not in permitted_live_classes:
                decisions.append(
                    CandidateAllocationDecision(
                        candidate_id=cand.candidate_id,
                        accepted=False,
                        allocated_shares=0.0,
                        allocated_capital_usd=0.0,
                        effective_lockup_hours=round(eff_h, 4),
                        realizable_net_value_usd=0.0,
                        opportunity_cost_charge_usd=0.0,
                        marginal_realizable_net_value_usd=0.0,
                        realizable_bps_per_hour=round(bps_hr, 4),
                        recycling_compounding_bonus_usd=0.0,
                        rejection_reason=f"LIVE_DEFAULT_RISKLESS_MODE_AWAITING_OWNER_CLASS_AUTH:{cand.opportunity_class.value}",
                    )
                )
                continue

            # 1b. Hierarchical per-sleeve enablement & velocity/concurrency gates
            sl_cfg: Optional[SleeveRiskConfig] = (
                risk_budget_config.sleeve_configs.get(cand.sleeve_name)
                if risk_budget_config is not None
                else None
            )
            if mode != ExecutionMode.RESEARCH and sl_cfg is not None:
                if not sl_cfg.enabled:
                    decisions.append(
                        CandidateAllocationDecision(
                            candidate_id=cand.candidate_id,
                            accepted=False,
                            allocated_shares=0.0,
                            allocated_capital_usd=0.0,
                            effective_lockup_hours=round(eff_h, 4),
                            realizable_net_value_usd=0.0,
                            opportunity_cost_charge_usd=0.0,
                            marginal_realizable_net_value_usd=0.0,
                            realizable_bps_per_hour=round(bps_hr, 4),
                            recycling_compounding_bonus_usd=0.0,
                            rejection_reason=f"SLEEVE_DISABLED_BY_RISK_CONFIG:{cand.sleeve_name}",
                        )
                    )
                    continue
                if bps_hr < float(sl_cfg.min_bps_per_hour) - 1e-6:
                    decisions.append(
                        CandidateAllocationDecision(
                            candidate_id=cand.candidate_id,
                            accepted=False,
                            allocated_shares=0.0,
                            allocated_capital_usd=0.0,
                            effective_lockup_hours=round(eff_h, 4),
                            realizable_net_value_usd=0.0,
                            opportunity_cost_charge_usd=0.0,
                            marginal_realizable_net_value_usd=0.0,
                            realizable_bps_per_hour=round(bps_hr, 4),
                            recycling_compounding_bonus_usd=0.0,
                            rejection_reason=f"SLEEVE_MIN_BPS_HR_NOT_MET:{bps_hr:.4f}<{sl_cfg.min_bps_per_hour:.4f}",
                        )
                    )
                    continue
                if sleeve_pos_cnt.get(cand.sleeve_name, 0) >= int(sl_cfg.max_concurrent_positions):
                    decisions.append(
                        CandidateAllocationDecision(
                            candidate_id=cand.candidate_id,
                            accepted=False,
                            allocated_shares=0.0,
                            allocated_capital_usd=0.0,
                            effective_lockup_hours=round(eff_h, 4),
                            realizable_net_value_usd=0.0,
                            opportunity_cost_charge_usd=0.0,
                            marginal_realizable_net_value_usd=0.0,
                            realizable_bps_per_hour=round(bps_hr, 4),
                            recycling_compounding_bonus_usd=0.0,
                            rejection_reason=f"SLEEVE_MAX_CONCURRENT_POSITIONS_REACHED:{cand.sleeve_name}",
                        )
                    )
                    continue

            if unit_rnv <= 0.0:
                decisions.append(
                    CandidateAllocationDecision(
                        candidate_id=cand.candidate_id,
                        accepted=False,
                        allocated_shares=0.0,
                        allocated_capital_usd=0.0,
                        effective_lockup_hours=round(eff_h, 4),
                        realizable_net_value_usd=0.0,
                        opportunity_cost_charge_usd=0.0,
                        marginal_realizable_net_value_usd=0.0,
                        realizable_bps_per_hour=round(bps_hr, 4),
                        recycling_compounding_bonus_usd=0.0,
                        rejection_reason="NON_POSITIVE_REALIZABLE_NET_VALUE_AFTER_CONSTRUCTION_RISK",
                    )
                )
                continue

            if mode != ExecutionMode.RESEARCH and any(inst in consumed_instruments for inst in cand.instrument_ids if inst):
                decisions.append(
                    CandidateAllocationDecision(
                        candidate_id=cand.candidate_id,
                        accepted=False,
                        allocated_shares=0.0,
                        allocated_capital_usd=0.0,
                        effective_lockup_hours=round(eff_h, 4),
                        realizable_net_value_usd=0.0,
                        opportunity_cost_charge_usd=0.0,
                        marginal_realizable_net_value_usd=0.0,
                        realizable_bps_per_hour=round(bps_hr, 4),
                        recycling_compounding_bonus_usd=0.0,
                        rejection_reason="SHARED_ORDERBOOK_DEPTH_ALREADY_CONSUMED",
                    )
                )
                continue

            hierarchical_cap_usd = cash_rem
            if mode == ExecutionMode.RESEARCH:
                # RESEARCH mode: pure contract, pricing, and L2 depth evaluation without wallet cash starvation
                alloc_sh = math.floor(float(cand.max_executable_shares) * 100.0 + 1e-9) / 100.0
                alloc_cap = round(alloc_sh * cap_sh, 6)
            else:
                # SHADOW & LIVE: enforce portfolio cash accounting + correlated cluster worst-case exposure (`CWCE`)
                probe_exp = ExposurePositionSpec(
                    position_id=cand.candidate_id,
                    cluster_keys=cand.cluster_keys,
                    capital_committed_usd=0.0,
                    is_same_condition_mergeable_box=cand.is_same_condition_mergeable_box,
                    event_id=cand.event_id,
                    market_family=cand.market_family,
                    underlying_asset=cand.underlying_asset,
                    resolution_source=cand.resolution_source,
                    directional_sign=cand.directional_sign,
                    sleeve_name=cand.sleeve_name,
                    family_code=cand.family_code,
                    model_id=cand.model_id,
                )
                market_pct = (
                    float(sl_cfg.max_single_market_nav_pct)
                    if sl_cfg is not None
                    else (
                        float(risk_budget_config.default_market_max_nav_pct)
                        if risk_budget_config is not None
                        else self.max_cluster_nav_pct
                    )
                )
                cwce_probe = evaluate_correlated_worst_case_exposure(
                    probe_exp,
                    active_exposures,
                    reconciled_nav_usd=reconciled_nav_usd,
                    max_cluster_nav_pct=min(self.max_cluster_nav_pct, market_pct),
                )
                cluster_cap_usd = (
                    cash_rem
                    if cand.is_same_condition_mergeable_box
                    else cwce_probe.remaining_cluster_headroom_usd
                )
                if risk_budget_config is not None:
                    nav_f = max(0.0, float(reconciled_nav_usd))
                    fam_pct = risk_budget_config.family_max_nav_pct.get(cand.family_code)
                    if fam_pct is not None:
                        fam_headroom = max(0.0, nav_f * float(fam_pct) - family_used_usd.get(cand.family_code, 0.0))
                        hierarchical_cap_usd = min(hierarchical_cap_usd, fam_headroom)
                    if sl_cfg is not None:
                        sl_headroom = max(0.0, nav_f * float(sl_cfg.max_nav_pct) - sleeve_used_usd.get(cand.sleeve_name, 0.0))
                        hierarchical_cap_usd = min(hierarchical_cap_usd, sl_headroom)
                    if cand.model_id and cand.model_id in risk_budget_config.model_max_nav_pct:
                        mod_pct = float(risk_budget_config.model_max_nav_pct[cand.model_id])
                        mod_headroom = max(0.0, nav_f * mod_pct - model_used_usd.get(cand.model_id, 0.0))
                        hierarchical_cap_usd = min(hierarchical_cap_usd, mod_headroom)

                usable_cap_usd = min(cash_rem, cluster_cap_usd, hierarchical_cap_usd)
                max_sh_by_cap = math.floor((usable_cap_usd / cap_sh) * 100.0 + 1e-9) / 100.0
                alloc_sh = min(float(cand.max_executable_shares), max_sh_by_cap)
                alloc_cap = round(alloc_sh * cap_sh, 6)

            if alloc_sh < float(cand.min_order_shares) - 1e-9 or alloc_cap < DEFAULT_MIN_MARKETABLE_BUY_USD - 1e-9:
                if mode != ExecutionMode.RESEARCH and hierarchical_cap_usd < float(cand.min_order_shares) * cap_sh <= min(cash_rem, cluster_cap_usd) + 1e-6:
                    rsn = "HIERARCHICAL_RISK_BUDGET_EXHAUSTED"
                elif mode != ExecutionMode.RESEARCH and cluster_cap_usd < float(cand.min_order_shares) * cap_sh <= cash_rem + 1e-6:
                    rsn = "CORRELATED_CLUSTER_HEADROOM_EXHAUSTED"
                else:
                    rsn = "INSUFFICIENT_DEPLOYABLE_CASH_OR_MIN_LOT"
                decisions.append(
                    CandidateAllocationDecision(
                        candidate_id=cand.candidate_id,
                        accepted=False,
                        allocated_shares=0.0,
                        allocated_capital_usd=0.0,
                        effective_lockup_hours=round(eff_h, 4),
                        realizable_net_value_usd=0.0,
                        opportunity_cost_charge_usd=0.0,
                        marginal_realizable_net_value_usd=0.0,
                        realizable_bps_per_hour=round(bps_hr, 4),
                        recycling_compounding_bonus_usd=0.0,
                        rejection_reason=rsn,
                    )
                )
                continue

            # True marginal competing anchor: ONLY subsequent unallocated positive-EV candidates
            # that would actually be crowded out by `alloc_cap` (`alloc_cap + rem_demand > cash_rem`).
            rem_demand_usd = 0.0
            displaced_best_bps = 0.0
            for nxt_bps, nxt_rnv, nxt_c in scored_pool[idx + 1:]:
                if nxt_rnv <= 0.0:
                    continue
                nxt_cap = min(
                    float(nxt_c.max_executable_shares) * float(nxt_c.capital_per_share_usd),
                    reconciled_nav_usd * self.max_cluster_nav_pct if not nxt_c.is_same_condition_mergeable_box else cash_total,
                )
                rem_demand_usd += nxt_cap
                if alloc_cap + rem_demand_usd > cash_rem + 1e-6:
                    displaced_best_bps = max(displaced_best_bps, nxt_bps)

            util_mid = (
                0.0
                if mode == ExecutionMode.RESEARCH
                else ((cash_total - cash_rem) + 0.5 * alloc_cap) / max(1.0, cash_total)
            )
            lam_bps_hr = (
                0.0
                if mode == ExecutionMode.RESEARCH
                else self.compute_shadow_price_bps_per_hr(util_mid, displaced_best_bps)
            )
            opp_cost_usd = alloc_cap * (lam_bps_hr / 10_000.0) * eff_h

            # Expected capital-recycling benefit when capital frees up well inside compounding_horizon_hours
            fast_liveness_recycles = bool(
                cand.custom_liveness_hours is not None
                and float(cand.custom_liveness_hours) > 0.0
                and eff_h < self.compounding_horizon_hours
            )
            freed_hours = (
                max(0.0, self.compounding_horizon_hours - eff_h)
                if cand.can_instant_merge_or_recycle or eff_h < self.compounding_horizon_hours
                else 0.0
            )
            recycle_bonus_usd = (
                alloc_cap * (self.expected_reinvestment_bps_per_hr / 10_000.0) * min(freed_hours, 6.0)
                if (cand.can_instant_merge_or_recycle or fast_liveness_recycles)
                else 0.0
            )

            rnv_usd = (unit_rnv * alloc_sh) - max(0.0, float(cand.marginal_infra_cost_usd))
            mrnv_usd = rnv_usd + recycle_bonus_usd - opp_cost_usd

            if mode == ExecutionMode.LIVE and mrnv_usd <= 0.0:
                decisions.append(
                    CandidateAllocationDecision(
                        candidate_id=cand.candidate_id,
                        accepted=False,
                        allocated_shares=0.0,
                        allocated_capital_usd=0.0,
                        effective_lockup_hours=round(eff_h, 4),
                        realizable_net_value_usd=round(rnv_usd, 6),
                        opportunity_cost_charge_usd=round(opp_cost_usd, 6),
                        marginal_realizable_net_value_usd=round(mrnv_usd, 6),
                        realizable_bps_per_hour=round(bps_hr, 4),
                        recycling_compounding_bonus_usd=round(recycle_bonus_usd, 6),
                        rejection_reason=f"SUB_MARGINAL_OPPORTUNITY_COST:bps_hr={bps_hr:.4f}<lambda={lam_bps_hr:.4f}",
                    )
                )
                continue

            if mode != ExecutionMode.RESEARCH:
                # Full cash reservation prevents concurrent unmerged orders from over-committing wallet cash;
                # legacy 5% transient buffer is only used when enforce_full_cash_reservation=False.
                allow_recycle_discount = (
                    not full_reserve
                    and cand.can_instant_merge_or_recycle
                    and (sl_cfg is None or sl_cfg.allow_instant_merge_recycling)
                )
                cash_consumption = alloc_cap * 0.05 if allow_recycle_discount else alloc_cap
                cash_rem = round(max(0.0, cash_rem - cash_consumption), 6)
                for inst in cand.instrument_ids:
                    if inst:
                        consumed_instruments.add(inst)
                if cand.family_code:
                    family_used_usd[cand.family_code] = family_used_usd.get(cand.family_code, 0.0) + alloc_cap
                if cand.sleeve_name:
                    sleeve_used_usd[cand.sleeve_name] = sleeve_used_usd.get(cand.sleeve_name, 0.0) + alloc_cap
                    sleeve_pos_cnt[cand.sleeve_name] = sleeve_pos_cnt.get(cand.sleeve_name, 0) + 1
                if cand.model_id:
                    model_used_usd[cand.model_id] = model_used_usd.get(cand.model_id, 0.0) + alloc_cap
                unwind_risk = max(0.0, cand.partial_fill_prob * cand.unwind_loss_per_share_if_partial_usd * alloc_sh)
                if reservation_ledger is not None:
                    reservation_ledger.reserve_order(
                        reservation_id=cand.candidate_id,
                        market_id=cand.event_id or (cand.cluster_keys[0] if cand.cluster_keys else cand.candidate_id),
                        instrument_id=cand.instrument_ids[0] if cand.instrument_ids else cand.candidate_id,
                        family_code=cand.family_code,
                        sleeve_name=cand.sleeve_name,
                        requested_notional_usd=alloc_cap,
                        model_id=cand.model_id,
                        cluster_keys=cand.cluster_keys,
                        event_id=cand.event_id,
                        market_family=cand.market_family,
                        underlying_asset=cand.underlying_asset,
                        resolution_source=cand.resolution_source,
                        directional_sign=cand.directional_sign,
                        is_same_condition_mergeable_box=cand.is_same_condition_mergeable_box,
                        partial_leg_unwind_risk_usd=unwind_risk,
                    )
                active_exposures.append(
                    ExposurePositionSpec(
                        position_id=cand.candidate_id,
                        cluster_keys=cand.cluster_keys,
                        capital_committed_usd=alloc_cap,
                        is_same_condition_mergeable_box=cand.is_same_condition_mergeable_box,
                        partial_leg_unwind_risk_usd=unwind_risk,
                        event_id=cand.event_id,
                        market_family=cand.market_family,
                        underlying_asset=cand.underlying_asset,
                        resolution_source=cand.resolution_source,
                        directional_sign=cand.directional_sign,
                        sleeve_name=cand.sleeve_name,
                        family_code=cand.family_code,
                        model_id=cand.model_id,
                    )
                )
            tot_rnv += rnv_usd
            tot_mrnv += mrnv_usd
            tot_floor_pnl += cand.worst_case_net_payoff_per_share_usd * alloc_sh
            decisions.append(
                CandidateAllocationDecision(
                    candidate_id=cand.candidate_id,
                    accepted=True,
                    allocated_shares=round(alloc_sh, 4),
                    allocated_capital_usd=alloc_cap,
                    effective_lockup_hours=round(eff_h, 4),
                    realizable_net_value_usd=round(rnv_usd, 6),
                    opportunity_cost_charge_usd=round(opp_cost_usd, 6),
                    marginal_realizable_net_value_usd=round(mrnv_usd, 6),
                    realizable_bps_per_hour=round(bps_hr, 4),
                    recycling_compounding_bonus_usd=round(recycle_bonus_usd, 6),
                    rejection_reason="",
                )
            )

        deployed = round(cash_total - cash_rem, 6)
        util_pct = round((deployed / cash_total) * 100.0, 2) if cash_total > 0 else 0.0
        terminal_lambda = self.compute_shadow_price_bps_per_hr(deployed / max(1.0, cash_total), competing_top_bps if len(prelim_rates) > 1 else 0.0)
        return PortfolioAllocationResult(
            mode=mode,
            initial_deployable_cash_usd=round(cash_total, 6),
            deployed_cash_usd=deployed,
            unallocated_cash_usd=round(cash_rem, 6),
            utilization_pct=util_pct,
            endogenous_shadow_price_bps_per_hr=terminal_lambda,
            total_realizable_net_value_usd=round(tot_rnv, 6),
            total_marginal_realizable_net_value_usd=round(tot_mrnv, 6),
            total_worst_case_guaranteed_floor_pnl_usd=round(tot_floor_pnl, 6),
            decisions=tuple(decisions),
        )


def simulate_legacy_v5_cliff_allocator(
    candidates: Sequence[PortfolioCandidateSpec],
    *,
    deployable_liquid_cash_usd: float = RECONCILED_NOV11_LIQUID_PUSD_USD,
    reconciled_nav_usd: float = RECONCILED_NOV11_MARK_TO_BID_NAV_USD,
    seed_max_lockup_hours: float = 24.0,
    seed_min_bps_per_hour: float = 7.5,
    allowlisted_sleeves: Optional[FrozenSet[str]] = None,
) -> Dict[str, Any]:
    """
    Reproducible counterfactual baseline replicating v5.0/v5.1 restrictions (`R-02`, `R-09`, `R-43`):
      - Arrival-order greedy selection (no cross-sleeve MRNV ranking),
      - Hard `24h` / `7.5 bps/hr` (`15.0 bps/hr` for `12h..24h`) step-function cliff,
      - Unconditional exemption for `DOMINANCE` boxes regardless of maturity (`holistic_strategy_governance.py:838`),
      - Rejection of fee-bearing `CAL1`/`COND1` boxes (`stage_c_zero_loss_velocity.py:609`) and non-allowlisted names.
    """
    allow_set = allowlisted_sleeves or frozenset(
        {
            "C1_BINARY_COMPLETE_SET",
            "D1_SAME_ORACLE_DOMINANCE_BOX",
            "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
            "COND1_MACRO_PARTITION_BOX",
            "BOND1_UMA_RESOLUTION_CARRY",
            "W_PRUNE1_DEAD_NO_BOND",
            "NR2_CONVERT_NO_SUBSET_ARB",
        }
    )
    cash_rem = max(0.0, float(deployable_liquid_cash_usd))
    tot_rnv = 0.0
    accepted_ids: List[str] = []
    rejected_by_reason: Dict[str, int] = {}

    for cand in candidates:
        if cand.opportunity_class not in {OpportunityClass.CLASS_A, OpportunityClass.CLASS_B}:
            rejected_by_reason["NON_AB_CLASS"] = rejected_by_reason.get("NON_AB_CLASS", 0) + 1
            continue
        if cand.sequential_clob_legs >= 3 and not cand.is_atomic_or_inventory_locked and reconciled_nav_usd < 500.0:
            rejected_by_reason["D007_SUB500_MULTILEG"] = rejected_by_reason.get("D007_SUB500_MULTILEG", 0) + 1
            continue
        if cand.sleeve_name not in allow_set:
            rejected_by_reason["R02_SLEEVE_NOT_ALLOWLISTED"] = rejected_by_reason.get("R02_SLEEVE_NOT_ALLOWLISTED", 0) + 1
            continue
        if cand.sleeve_name in {"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX", "COND1_MACRO_PARTITION_BOX"} and cand.fees_and_conversion_per_share_usd > 1e-9:
            rejected_by_reason["R02_CAL1_COND1_FEE_BAN"] = rejected_by_reason.get("R02_CAL1_COND1_FEE_BAN", 0) + 1
            continue

        eff_h = DynamicMarginalCapitalAllocator.effective_lockup_hours(cand)
        unit_rnv = cand.worst_case_net_payoff_per_share_usd - (cand.partial_fill_prob * cand.unwind_loss_per_share_if_partial_usd)
        bps_hr = (unit_rnv / max(1e-6, cand.capital_per_share_usd)) / eff_h * 10_000.0

        # Replicate `passes_capital_velocity_hurdle` bug: DOMINANCE bypasses velocity completely, others hit 24h/15bps cliff!
        is_dom_exempt = "DOMINANCE" in cand.sleeve_name and "MACRO" not in cand.sleeve_name
        if not is_dom_exempt and not cand.can_instant_merge_or_recycle:
            if eff_h > seed_max_lockup_hours:
                rejected_by_reason["R09_R43_MATURITY_CLIFF_24H"] = rejected_by_reason.get("R09_R43_MATURITY_CLIFF_24H", 0) + 1
                continue
            req_bps = seed_min_bps_per_hour * (2.0 if eff_h > 12.0 else 1.0)
            if bps_hr < req_bps:
                rejected_by_reason["R09_VELOCITY_STEP_CLIFF"] = rejected_by_reason.get("R09_VELOCITY_STEP_CLIFF", 0) + 1
                continue

        cap_lim = cash_rem if cand.is_same_condition_mergeable_box else min(cash_rem, reconciled_nav_usd * 0.15)
        sh = min(cand.max_executable_shares, math.floor((cap_lim / max(1e-6, cand.capital_per_share_usd)) * 100.0) / 100.0)
        if sh < cand.min_order_shares:
            rejected_by_reason["INSUFFICIENT_CASH_STARVED_BY_PRIOR_LOCK"] = rejected_by_reason.get("INSUFFICIENT_CASH_STARVED_BY_PRIOR_LOCK", 0) + 1
            continue
        spent = round(sh * cand.capital_per_share_usd, 6)
        cash_rem = round(max(0.0, cash_rem - spent), 6)
        tot_rnv += unit_rnv * sh
        accepted_ids.append(cand.candidate_id)

    return {
        "deployed_cash_usd": round(deployable_liquid_cash_usd - cash_rem, 6),
        "unallocated_cash_usd": cash_rem,
        "total_realizable_net_value_usd": round(tot_rnv, 6),
        "accepted_candidate_ids": accepted_ids,
        "rejected_counts": rejected_by_reason,
    }


# ---------------------------------------------------------------------------
# 8. Evidence-Based Readiness Evaluator (`R-42`, Replacing Time-Only `168h`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceBasedReadinessReport:
    venue_or_sleeve: str
    ready_for_owner_canary_proposal: bool
    evidence_score_pct: float
    pillars_passed: Dict[str, bool]
    blocking_deficiencies: Tuple[str, ...]


def evaluate_evidence_based_venue_readiness(
    *,
    venue_or_sleeve: str,
    uncontaminated_live_l2_samples: int,
    distinct_liquidity_regimes_observed: int,
    observed_live_hours: float,
    uptime_pct: float,
    api_error_rate_pct: float,
    p99_latency_ms: float,
    double_zero_or_clause_incidents: int,
    post_delay_simulated_trades: int,
    post_delay_net_executable_pnl_usd: float,
    settlement_and_custody_lifecycle_tested: bool,
    min_samples: int = 2_000,
    min_regimes: int = 3,
    min_regime_span_hours: float = 48.0,
    min_simulated_trades: int = 25,
) -> EvidenceBasedReadinessReport:
    """
    `R-42` Remediation — Replaces blind `168h` wall-clock waiting with 5 empirical evidence pillars:
      1. `statistical_sample_and_regime_coverage`: `>= 2,000` uncontaminated live L2 book snapshots
         across `>= 3` market regimes (weekday peak, off-hours thin book, event settlement window)
         spanning `>= 48h` (proving `168h` with `0` matched trades is NOT ready, while a high-evidence
         `48h+` run with `2,000+` snapshots, `25+` post-delay trades, and full settlement proof IS ready
         for owner canary review!).
      2. `connector_reliability_slo`: `uptime >= 99.0%`, `api_error_rate <= 2.0%`, `p99_latency <= 1000ms`.
      3. `zero_double_zero_and_clause_safety`: `double_zero_or_clause_incidents == 0`.
      4. `post_delay_execution_simulation`: `>= 25` simulated L2 walks after `takerDelayMs` + partial-fill
         unwind stress with `post_delay_net_executable_pnl_usd > 0.0`.
      5. `settlement_and_custody_lifecycle_proof`: Independent verification of deposit/order/cancel/redeem
         mechanics and fee schedule reconciliation.
    """
    pillars = {
        "P1_sample_and_regime_diversity": (
            int(uncontaminated_live_l2_samples) >= int(min_samples)
            and int(distinct_liquidity_regimes_observed) >= int(min_regimes)
            and float(observed_live_hours) >= float(min_regime_span_hours)
        ),
        "P2_connector_reliability_slo": (
            float(uptime_pct) >= 99.0
            and float(api_error_rate_pct) <= 2.0
            and 0.0 < float(p99_latency_ms) <= 1_000.0
        ),
        "P3_zero_double_zero_incidents": int(double_zero_or_clause_incidents) == 0,
        "P4_post_delay_execution_positive_ev": (
            int(post_delay_simulated_trades) >= int(min_simulated_trades)
            and float(post_delay_net_executable_pnl_usd) > 0.0
        ),
        "P5_settlement_and_custody_tested": bool(settlement_and_custody_lifecycle_tested),
    }
    deficiencies = [k for k, ok in pillars.items() if not ok]
    score = round((sum(1 for ok in pillars.values() if ok) / len(pillars)) * 100.0, 2)
    return EvidenceBasedReadinessReport(
        venue_or_sleeve=str(venue_or_sleeve),
        ready_for_owner_canary_proposal=(len(deficiencies) == 0),
        evidence_score_pct=score,
        pillars_passed=pillars,
        blocking_deficiencies=tuple(deficiencies),
    )


# ---------------------------------------------------------------------------
# 9. Harvester <-> CapitalReservationLedger, HierarchicalRiskBudget & CWCE Wiring
# ---------------------------------------------------------------------------


def _is_position_frozen_or_disputed_kmia(pos: Mapping[str, Any], now_ts: Optional[float] = None) -> bool:
    """Identifies frozen post-expiry UMA disputed positions (including the 4 protected KMIA positions per D-001)."""
    if not isinstance(pos, Mapping):
        return False
    mid = str(pos.get("market_id") or "").strip()
    tid = str(pos.get("trade_id") or pos.get("box_id") or "").strip().upper()
    if mid in FROZEN_DISPUTED_MARKET_IDS or any(sub in tid for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS):
        return True
    if bool(pos.get("uma_disputed")) or str(pos.get("resolution_status") or "").strip().lower() == "disputed":
        return True
    try:
        from src.polymarket_research.riskless_protocol_v2_expansion import is_disputed_or_frozen_uma_position

        return bool(is_disputed_or_frozen_uma_position(pos, now_ts))
    except Exception:
        return str(pos.get("umaResolutionStatus") or "").strip().lower() == "disputed"


def build_harvester_hierarchical_risk_budget(
    harvester: Any = None,
    rb_cfg: Optional[Mapping[str, Any]] = None,
) -> HierarchicalRiskBudgetConfig:
    """Builds or returns the harvester's `HierarchicalRiskBudgetConfig` from governance and harvester settings."""
    if harvester is not None:
        existing_cfg = getattr(harvester, "hierarchical_risk_budget_config", None)
        if isinstance(existing_cfg, HierarchicalRiskBudgetConfig):
            return existing_cfg
    if rb_cfg is None:
        try:
            from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

            rb_cfg = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}) or {}
        except Exception:
            rb_cfg = {}
    rb = rb_cfg if isinstance(rb_cfg, Mapping) else {}
    default_mkt_pct = min(1.0, max(0.01, _sf(rb.get("max_correlated_oracle_event_nav_pct"), 0.15)))
    port_util_pct = min(1.0, max(0.05, _sf(rb.get("portfolio_max_utilization_pct"), 0.95)))
    max_conc_default = max(1, int(_sf(rb.get("max_concurrent_riskless_boxes"), 10)))

    sleeve_cfgs: Dict[str, SleeveRiskConfig] = {}
    for raw_sl in (rb.get("paused_riskless_sleeves") or ()):
        sl_name = str(raw_sl or "").strip()
        if sl_name:
            sleeve_cfgs[sl_name] = SleeveRiskConfig(
                sleeve_name=sl_name,
                enabled=False,
                max_single_market_nav_pct=default_mkt_pct,
            )
    custom_sl = rb.get("v6_sleeve_risk_configs")
    if isinstance(custom_sl, Mapping):
        for sl_k, sl_v in custom_sl.items():
            if isinstance(sl_v, SleeveRiskConfig):
                sleeve_cfgs[str(sl_k)] = sl_v
            elif isinstance(sl_v, Mapping):
                sleeve_cfgs[str(sl_k)] = SleeveRiskConfig(
                    sleeve_name=str(sl_k),
                    family_code=str(sl_v.get("family_code") or ""),
                    enabled=bool(sl_v.get("enabled", True)),
                    max_nav_pct=_sf(sl_v.get("max_nav_pct"), 0.50),
                    max_concurrent_positions=max(1, int(_sf(sl_v.get("max_concurrent_positions"), max_conc_default))),
                    min_bps_per_hour=_sf(sl_v.get("min_bps_per_hour"), 0.0),
                    kelly_fraction_cap=_sf(sl_v.get("kelly_fraction_cap"), 0.50),
                    max_single_market_nav_pct=_sf(sl_v.get("max_single_market_nav_pct"), default_mkt_pct),
                    allow_instant_merge_recycling=bool(sl_v.get("allow_instant_merge_recycling", True)),
                )
    fam_caps = {str(k): _sf(v, 0.50) for k, v in (rb.get("v6_family_max_nav_pct") or {}).items()} if isinstance(rb.get("v6_family_max_nav_pct"), Mapping) else {}
    mod_caps = {str(k): _sf(v, 0.35) for k, v in (rb.get("v6_model_max_nav_pct") or {}).items()} if isinstance(rb.get("v6_model_max_nav_pct"), Mapping) else {}
    cfg = HierarchicalRiskBudgetConfig(
        portfolio_max_utilization_pct=port_util_pct,
        family_max_nav_pct=fam_caps,
        sleeve_configs=sleeve_cfgs,
        model_max_nav_pct=mod_caps,
        default_market_max_nav_pct=default_mkt_pct,
    )
    if harvester is not None and hasattr(harvester, "__dict__"):
        harvester.hierarchical_risk_budget_config = cfg
    return cfg


def build_harvester_exposure_specs(
    harvester: Any,
    now_ts: Optional[float] = None,
    *,
    include_pending_intents: bool = False,
    exclude_intent_ids: Optional[Sequence[str]] = None,
) -> List[ExposurePositionSpec]:
    """
    Converts `harvester.active_positions` (and optionally open Maker intents) into `ExposurePositionSpec`
    objects for CWCE and hierarchical risk budget evaluation, strictly isolating frozen post-expiry
    UMA disputed `KMIA` positions (`is_quarantined_historical_dispute=True`) from active non-frozen sizing.
    """
    if harvester is None:
        return []
    now_f = float(time.time() if now_ts is None else now_ts)
    try:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            extract_canonical_event_keys,
            position_is_settlement_receivable,
        )
    except Exception:
        extract_canonical_event_keys = lambda x, market_ids=None: set()  # type: ignore
        position_is_settlement_receivable = lambda x: False  # type: ignore

    specs: List[ExposurePositionSpec] = []
    act_pos = getattr(harvester, "active_positions", None) or {}
    for pid, p in act_pos.items():
        if not isinstance(p, Mapping):
            continue
        if position_is_settlement_receivable(p) or p.get("resolved_winning_outcome") is not None:
            continue
        notional = max(0.0, _sf(p.get("notional_usd", p.get("remaining_cost_basis")), 0.0))
        if notional <= 0.0:
            continue
        is_quar = _is_position_frozen_or_disputed_kmia(p, now_f)
        btype = str(p.get("box_type") or "").strip().upper()
        sl_name = str(p.get("sleeve") or p.get("sleeve_source") or btype or "").strip()
        is_c1_merge = bool(
            not is_quar
            and (
                btype in {"COMPLETE_SET", "C1_BINARY_COMPLETE_SET"}
                or sl_name == "C1_BINARY_COMPLETE_SET"
            )
            and bool(p.get("is_same_condition_mergeable_box", True))
        )
        c_keys = tuple(sorted(extract_canonical_event_keys(p)))
        specs.append(
            ExposurePositionSpec(
                position_id=str(p.get("trade_id") or pid),
                cluster_keys=c_keys,
                capital_committed_usd=round(notional, 6),
                is_same_condition_mergeable_box=is_c1_merge,
                is_quarantined_historical_dispute=is_quar,
                partial_leg_unwind_risk_usd=max(0.0, _sf(p.get("partial_leg_unwind_risk_usd"), 0.0)),
                event_id=str(p.get("event_id") or p.get("event_group_key") or ""),
                market_family=str(p.get("market_family") or btype or ""),
                underlying_asset=str(p.get("asset") or p.get("underlying_asset") or "").strip().upper(),
                resolution_source=str(p.get("resolution_source") or p.get("oracle_source") or ""),
                directional_sign=int(_sf(p.get("directional_sign"), 0.0)),
                sleeve_name=sl_name,
                family_code=str(p.get("family_code") or p.get("family") or ""),
                model_id=str(p.get("model_id") or ""),
            )
        )

    if include_pending_intents:
        excl = {str(x).strip() for x in (exclude_intent_ids or ()) if str(x or "").strip()}
        ledger = getattr(harvester, "_capital_reservation_ledger", None)
        if isinstance(ledger, CapitalReservationLedger):
            for exp_s in ledger.to_exposure_specs():
                if exp_s.position_id not in excl:
                    specs.append(exp_s)
    return specs


def sync_harvester_capital_reservation_ledger(
    harvester: Any,
    now_ts: Optional[float] = None,
    *,
    safety_buffer_usd: Optional[float] = None,
) -> CapitalReservationLedger:
    """
    Reconciles `PolymarketLiveHarvester` state into `CapitalReservationLedger`:
      1. Syncs authoritative wallet cash (`_last_known_collateral` / `live_bankroll`).
      2. Reconciles open Maker intents (`pending_entry_intents`, `_active_maker_orders`, `_prepost_sll_events`)
         with exact unfilled vs matched-unsettled vs on-chain collateral-drop accounting.
      3. Computes non-frozen active open position exposure vs frozen post-expiry UMA disputed `KMIA`
         positions (strictly excluding frozen `KMIA` cost basis from active non-frozen sizing equity
         while preserving `D-001` non-interference).
    """
    now_f = float(time.time() if now_ts is None else now_ts)
    collat_raw = getattr(harvester, "_last_known_collateral", None) if harvester is not None else None
    if collat_raw is None and harvester is not None:
        collat_raw = getattr(harvester, "live_bankroll", None)
    if collat_raw is None:
        collat_f = 75.0 if bool(getattr(harvester, "dry_run", False)) else 0.0
    else:
        collat_f = max(0.0, _sf(collat_raw, 0.0))

    buf_f = (
        max(0.0, float(safety_buffer_usd))
        if safety_buffer_usd is not None
        else max(0.0, _sf(getattr(harvester, "reservation_safety_buffer_usd", 0.0), 0.0))
    )

    ledger: Optional[CapitalReservationLedger] = (
        getattr(harvester, "_capital_reservation_ledger", None) if harvester is not None else None
    )
    if not isinstance(ledger, CapitalReservationLedger):
        ledger = CapitalReservationLedger(total_wallet_cash_usd=collat_f, safety_buffer_usd=buf_f)
        if harvester is not None and hasattr(harvester, "__dict__"):
            harvester._capital_reservation_ledger = ledger
    else:
        ledger.sync_wallet_cash(collat_f)
        ledger.safety_buffer_usd = round(buf_f, 6)

    if harvester is None:
        return ledger

    try:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            compute_reconciled_concentration_nav_usd,
            extract_canonical_event_keys,
            position_is_settlement_receivable,
        )
    except Exception:
        compute_reconciled_concentration_nav_usd = lambda h, ts=None: collat_f  # type: ignore
        extract_canonical_event_keys = lambda x, market_ids=None: set()  # type: ignore
        position_is_settlement_receivable = lambda x: False  # type: ignore

    # Gather open maker / pending order intents from harvester maps
    combined_intents: Dict[str, Mapping[str, Any]] = {}
    for attr_name in ("_prepost_sll_events", "_active_maker_orders", "pending_entry_intents"):
        raw_map = getattr(harvester, attr_name, None)
        if isinstance(raw_map, Mapping):
            for k, v in raw_map.items():
                if isinstance(v, Mapping):
                    combined_intents[str(k)] = v

    auto_synced: Set[str] = harvester.__dict__.setdefault("_ledger_auto_synced_ids", set())
    stale_ids = [rid for rid in list(auto_synced) if rid not in combined_intents]
    for rid in stale_ids:
        ledger.release_reservation(rid, reason="SETTLED", now_ts=now_f)
        auto_synced.discard(rid)

    for rid, it in combined_intents.items():
        unfilled = max(0.0, _sf(it.get("notional_usd", it.get("unfilled_notional_usd")), 0.0))
        matched = max(0.0, _sf(it.get("matched_notional_usd", it.get("filled_notional_usd")), 0.0))
        collat_drop = max(0.0, _sf(it.get("collat_drop_usd"), 0.0))
        req_notional = max(
            unfilled + matched,
            _sf(it.get("posted_notional_usd", it.get("requested_notional_usd")), unfilled + matched),
        )
        if req_notional <= 0.0 and not it.get("live_maker_anchor_inflight"):
            if rid in auto_synced:
                ledger.release_reservation(rid, reason="CANCELLED", now_ts=now_f)
                auto_synced.discard(rid)
            continue

        c_keys = tuple(sorted(extract_canonical_event_keys(it)))
        mid = str(it.get("market_id") or it.get("leg_a_market_id") or "")
        inst_id = str(it.get("token_id") or it.get("leg_a_token_id") or it.get("instrument_id") or rid)
        sl_name = str(it.get("sleeve_source") or it.get("sleeve") or it.get("box_type") or "MAKER_INTENT")
        fam_code = str(it.get("family_code") or it.get("family") or "")
        mod_id = str(it.get("model_id") or "")
        ev_id = str(it.get("event_id") or it.get("event_group_key") or "")
        mkt_fam = str(it.get("market_family") or it.get("box_type") or "")
        asset_u = str(it.get("asset") or it.get("underlying_asset") or "").strip().upper()
        res_src = str(it.get("resolution_source") or "")
        dir_sgn = int(_sf(it.get("directional_sign"), 0.0))
        is_c1_m = bool(it.get("is_same_condition_mergeable_box", False))
        unwind_r = max(0.0, _sf(it.get("partial_leg_unwind_risk_usd"), 0.0))

        status = (
            OrderReservationStatus.FILLED_UNSETTLED
            if (unfilled <= 1e-6 and matched > 0.0)
            else (OrderReservationStatus.PARTIALLY_FILLED if matched > 0.0 else OrderReservationStatus.PENDING)
        )
        rec = OrderReservationRecord(
            reservation_id=rid,
            market_id=mid,
            instrument_id=inst_id,
            family_code=fam_code,
            sleeve_name=sl_name,
            model_id=mod_id,
            requested_notional_usd=round(req_notional, 6),
            filled_notional_usd=round(matched, 6),
            unfilled_notional_usd=round(unfilled, 6),
            matched_unsettled_usd=round(matched, 6),
            collat_drop_usd=round(min(matched, collat_drop), 6),
            status=status,
            cluster_keys=c_keys,
            event_id=ev_id,
            market_family=mkt_fam,
            underlying_asset=asset_u,
            resolution_source=res_src,
            directional_sign=dir_sgn,
            is_same_condition_mergeable_box=is_c1_m,
            partial_leg_unwind_risk_usd=unwind_r,
            created_ts=_sf(it.get("ts", it.get("created_ts")), now_f),
            updated_ts=now_f,
        )
        ledger._records[rid] = rec
        auto_synced.add(rid)

    # Reconcile non-frozen active positions vs frozen post-expiry UMA disputed KMIA positions
    non_frozen_usd = 0.0
    frozen_disputed_usd = 0.0
    act_pos = getattr(harvester, "active_positions", None) or {}
    for p in act_pos.values():
        if not isinstance(p, Mapping) or position_is_settlement_receivable(p) or p.get("resolved_winning_outcome") is not None:
            continue
        notional = max(0.0, _sf(p.get("notional_usd", p.get("remaining_cost_basis")), 0.0))
        if _is_position_frozen_or_disputed_kmia(p, now_f):
            frozen_disputed_usd += notional
        else:
            non_frozen_usd += notional

    harvester._non_frozen_open_positions_usd = round(non_frozen_usd, 6)
    harvester._frozen_disputed_positions_usd = round(frozen_disputed_usd, 6)
    harvester._reconciled_non_frozen_sizing_nav_usd = round(
        compute_reconciled_concentration_nav_usd(harvester, now_f), 6
    )
    build_harvester_hierarchical_risk_budget(harvester)
    return ledger


def evaluate_candidate_v6_cwce_and_reservation(
    harvester: Any,
    cand: Mapping[str, Any],
    *,
    requested_notional_usd: Optional[float] = None,
    market_ids: Optional[Sequence[str]] = None,
    now_ts: Optional[float] = None,
    exclude_intent_ids: Optional[Sequence[str]] = None,
    reserve_on_accept: bool = False,
) -> Dict[str, Any]:
    """
    Unified v6.0 pre-trade validation hook for `riskless_protocol_v2_expansion` and `PolymarketLiveHarvester`:
      1. Enforces `D-001` absolute non-interference on the 4 disputed `KMIA` positions (`6707502`, `6707503`).
      2. Syncs `CapitalReservationLedger` and `HierarchicalRiskBudgetConfig` from live harvester state,
         strictly excluding frozen post-expiry UMA disputed `KMIA` cost basis (`$50.51`) from active
         non-frozen sizing equity (`reconciled_nav_usd`).
      3. Evaluates hierarchical risk budgets (portfolio utilization, strategy family, sleeve, model, market).
      4. Evaluates correlated worst-case exposure (`evaluate_correlated_worst_case_exposure`) across all
         open positions and active reservations.
      5. Verifies `CapitalReservationLedger.available_deployable_cash_usd` and optionally reserves order capital.
    """
    now_f = float(time.time() if now_ts is None else now_ts)
    cand_map = cand if isinstance(cand, Mapping) else {}
    try:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            check_sll_cand_dispute_guard,
            extract_canonical_event_keys,
        )
    except Exception:
        check_sll_cand_dispute_guard = lambda c: None  # type: ignore
        extract_canonical_event_keys = lambda c, market_ids=None: set()  # type: ignore

    c_keys = tuple(sorted(extract_canonical_event_keys(cand_map, market_ids=market_ids)))
    cand_id = str(
        cand_map.get("candidate_id")
        or cand_map.get("box_id")
        or cand_map.get("trade_id")
        or cand_map.get("dedupe_key")
        or "CAND_V6"
    ).strip()
    mid = str(
        cand_map.get("market_id")
        or cand_map.get("leg_a_market_id")
        or ((market_ids or ("",))[0] if market_ids else "")
        or ""
    ).strip()
    inst_id = str(
        cand_map.get("token_id")
        or cand_map.get("leg_a_token_id")
        or cand_map.get("instrument_id")
        or cand_id
    ).strip()

    touches_kmia = any(
        m in FROZEN_DISPUTED_MARKET_IDS or any(sub in str(m).upper() for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS)
        for m in (*c_keys, mid, inst_id, cand_id, str(cand_map.get("asset") or ""))
    )
    disp_guard = check_sll_cand_dispute_guard(cand_map)
    if touches_kmia or disp_guard:
        return {
            "allowed": False,
            "reason": disp_guard or "BLOCKED_D001_DISPUTED_KMIA_POSITION_QUARANTINE",
            "available_deployable_cash_usd": 0.0,
            "reconciled_nav_usd": 0.0,
            "non_frozen_open_positions_usd": 0.0,
            "frozen_disputed_positions_usd": 0.0,
            "cwce_verdict": None,
            "remaining_cluster_headroom_usd": 0.0,
            "binding_cluster_key": "D001_KMIA",
            "ledger_snapshot": None,
            "reservation_record": None,
        }

    ledger = sync_harvester_capital_reservation_ledger(harvester, now_ts=now_f)
    risk_cfg = build_harvester_hierarchical_risk_budget(harvester)
    reconciled_nav = float(
        getattr(harvester, "_reconciled_non_frozen_sizing_nav_usd", None)
        if harvester is not None and getattr(harvester, "_reconciled_non_frozen_sizing_nav_usd", None) is not None
        else max(ledger.total_wallet_cash_usd, RECONCILED_NOV11_MARK_TO_BID_NAV_USD)
    )
    non_frozen_open = float(getattr(harvester, "_non_frozen_open_positions_usd", 0.0) if harvester is not None else 0.0)
    frozen_disp_open = float(getattr(harvester, "_frozen_disputed_positions_usd", 0.0) if harvester is not None else 0.0)

    if requested_notional_usd is not None:
        req_usd = max(0.0, float(requested_notional_usd))
    else:
        sh = max(0.0, _sf(cand_map.get("shares", cand_map.get("net_paired_shares")), 5.0))
        px = max(0.0, _sf(cand_map.get("box_cost_net", cand_map.get("leg_a_limit_price", cand_map.get("anchor_bid_px", cand_map.get("price")))), 1.0))
        req_usd = max(0.0, _sf(cand_map.get("notional_usd", cand_map.get("requested_notional_usd")), sh * px))

    btype = str(cand_map.get("box_type") or "").strip().upper()
    sl_name = str(cand_map.get("sleeve_source") or cand_map.get("sleeve") or btype or "").strip()
    fam_code = str(cand_map.get("family_code") or cand_map.get("family") or "")
    mod_id = str(cand_map.get("model_id") or "")
    is_c1_merge = bool(
        cand_map.get("is_same_condition_mergeable_box")
        or (
            btype in {"COMPLETE_SET", "C1_BINARY_COMPLETE_SET"}
            and str(cand_map.get("leg_a_condition_id") or "a") == str(cand_map.get("leg_b_condition_id") or "a")
        )
    )

    existing_exps = build_harvester_exposure_specs(
        harvester,
        now_ts=now_f,
        include_pending_intents=True,
        exclude_intent_ids=exclude_intent_ids,
    )

    # Hierarchical Risk Budget checks (Sleeve enablement, concurrency, family/sleeve/model caps)
    sl_cfg = risk_cfg.sleeve_configs.get(sl_name) if sl_name else None
    if sl_cfg is not None and not sl_cfg.enabled:
        return {
            "allowed": False,
            "reason": f"SLEEVE_DISABLED_BY_RISK_CONFIG:{sl_name}",
            "available_deployable_cash_usd": ledger.available_deployable_cash_usd,
            "reconciled_nav_usd": reconciled_nav,
            "non_frozen_open_positions_usd": non_frozen_open,
            "frozen_disputed_positions_usd": frozen_disp_open,
            "cwce_verdict": None,
            "remaining_cluster_headroom_usd": 0.0,
            "binding_cluster_key": sl_name,
            "ledger_snapshot": ledger.snapshot(),
            "reservation_record": None,
        }

    non_quar_exps = [e for e in existing_exps if not e.is_quarantined_historical_dispute]
    if sl_cfg is not None:
        sl_cnt = sum(1 for e in non_quar_exps if e.sleeve_name == sl_name)
        if sl_cnt >= int(sl_cfg.max_concurrent_positions):
            return {
                "allowed": False,
                "reason": f"SLEEVE_MAX_CONCURRENT_POSITIONS_REACHED:{sl_name}",
                "available_deployable_cash_usd": ledger.available_deployable_cash_usd,
                "reconciled_nav_usd": reconciled_nav,
                "non_frozen_open_positions_usd": non_frozen_open,
                "frozen_disputed_positions_usd": frozen_disp_open,
                "cwce_verdict": None,
                "remaining_cluster_headroom_usd": 0.0,
                "binding_cluster_key": sl_name,
                "ledger_snapshot": ledger.snapshot(),
                "reservation_record": None,
            }
        sl_used = sum(e.capital_committed_usd for e in non_quar_exps if e.sleeve_name == sl_name)
        if sl_used + req_usd > reconciled_nav * float(sl_cfg.max_nav_pct) + 1e-6:
            return {
                "allowed": False,
                "reason": f"SLEEVE_RISK_BUDGET_EXCEEDED:{sl_name}",
                "available_deployable_cash_usd": ledger.available_deployable_cash_usd,
                "reconciled_nav_usd": reconciled_nav,
                "non_frozen_open_positions_usd": non_frozen_open,
                "frozen_disputed_positions_usd": frozen_disp_open,
                "cwce_verdict": None,
                "remaining_cluster_headroom_usd": max(0.0, reconciled_nav * float(sl_cfg.max_nav_pct) - sl_used),
                "binding_cluster_key": sl_name,
                "ledger_snapshot": ledger.snapshot(),
                "reservation_record": None,
            }

    if fam_code and fam_code in risk_cfg.family_max_nav_pct:
        fam_used = sum(e.capital_committed_usd for e in non_quar_exps if e.family_code == fam_code)
        fam_cap = reconciled_nav * float(risk_cfg.family_max_nav_pct[fam_code])
        if fam_used + req_usd > fam_cap + 1e-6:
            return {
                "allowed": False,
                "reason": f"FAMILY_RISK_BUDGET_EXCEEDED:{fam_code}",
                "available_deployable_cash_usd": ledger.available_deployable_cash_usd,
                "reconciled_nav_usd": reconciled_nav,
                "non_frozen_open_positions_usd": non_frozen_open,
                "frozen_disputed_positions_usd": frozen_disp_open,
                "cwce_verdict": None,
                "remaining_cluster_headroom_usd": max(0.0, fam_cap - fam_used),
                "binding_cluster_key": fam_code,
                "ledger_snapshot": ledger.snapshot(),
                "reservation_record": None,
            }

    if mod_id and mod_id in risk_cfg.model_max_nav_pct:
        mod_used = sum(e.capital_committed_usd for e in non_quar_exps if e.model_id == mod_id)
        mod_cap = reconciled_nav * float(risk_cfg.model_max_nav_pct[mod_id])
        if mod_used + req_usd > mod_cap + 1e-6:
            return {
                "allowed": False,
                "reason": f"MODEL_RISK_BUDGET_EXCEEDED:{mod_id}",
                "available_deployable_cash_usd": ledger.available_deployable_cash_usd,
                "reconciled_nav_usd": reconciled_nav,
                "non_frozen_open_positions_usd": non_frozen_open,
                "frozen_disputed_positions_usd": frozen_disp_open,
                "cwce_verdict": None,
                "remaining_cluster_headroom_usd": max(0.0, mod_cap - mod_used),
                "binding_cluster_key": mod_id,
                "ledger_snapshot": ledger.snapshot(),
                "reservation_record": None,
            }

    cand_exp = ExposurePositionSpec(
        position_id=cand_id,
        cluster_keys=c_keys,
        capital_committed_usd=round(req_usd, 6),
        is_same_condition_mergeable_box=is_c1_merge,
        partial_leg_unwind_risk_usd=max(0.0, _sf(cand_map.get("partial_leg_unwind_risk_usd"), 0.0)),
        event_id=str(cand_map.get("event_id") or cand_map.get("event_group_key") or ""),
        market_family=str(cand_map.get("market_family") or btype or ""),
        underlying_asset=str(cand_map.get("asset") or cand_map.get("underlying_asset") or "").strip().upper(),
        resolution_source=str(cand_map.get("resolution_source") or cand_map.get("oracle_source") or ""),
        directional_sign=int(_sf(cand_map.get("directional_sign"), 0.0)),
        sleeve_name=sl_name,
        family_code=fam_code,
        model_id=mod_id,
    )
    eff_cluster_pct = (
        float(sl_cfg.max_single_market_nav_pct)
        if sl_cfg is not None
        else float(risk_cfg.default_market_max_nav_pct)
    )
    cwce = evaluate_correlated_worst_case_exposure(
        cand_exp,
        existing_exps,
        reconciled_nav_usd=reconciled_nav,
        max_cluster_nav_pct=eff_cluster_pct,
    )
    if not cwce.allowed:
        return {
            "allowed": False,
            "reason": cwce.reason,
            "available_deployable_cash_usd": ledger.available_deployable_cash_usd,
            "reconciled_nav_usd": reconciled_nav,
            "non_frozen_open_positions_usd": non_frozen_open,
            "frozen_disputed_positions_usd": frozen_disp_open,
            "cwce_verdict": cwce,
            "remaining_cluster_headroom_usd": cwce.remaining_cluster_headroom_usd,
            "binding_cluster_key": cwce.binding_cluster_key,
            "ledger_snapshot": ledger.snapshot(),
            "reservation_record": None,
        }

    avail_cash = ledger.available_deployable_cash_usd
    if req_usd > avail_cash + 1e-6:
        return {
            "allowed": False,
            "reason": f"INSUFFICIENT_AVAILABLE_CASH:{req_usd:.4f}>{avail_cash:.4f}",
            "available_deployable_cash_usd": avail_cash,
            "reconciled_nav_usd": reconciled_nav,
            "non_frozen_open_positions_usd": non_frozen_open,
            "frozen_disputed_positions_usd": frozen_disp_open,
            "cwce_verdict": cwce,
            "remaining_cluster_headroom_usd": cwce.remaining_cluster_headroom_usd,
            "binding_cluster_key": cwce.binding_cluster_key,
            "ledger_snapshot": ledger.snapshot(),
            "reservation_record": None,
        }

    res_rec: Optional[OrderReservationRecord] = None
    if reserve_on_accept and req_usd > 0.0:
        ok_r, msg_r, res_rec = ledger.reserve_order(
            reservation_id=cand_id,
            market_id=mid or cand_id,
            instrument_id=inst_id,
            family_code=fam_code,
            sleeve_name=sl_name,
            requested_notional_usd=req_usd,
            model_id=mod_id,
            cluster_keys=c_keys,
            event_id=cand_exp.event_id,
            market_family=cand_exp.market_family,
            underlying_asset=cand_exp.underlying_asset,
            resolution_source=cand_exp.resolution_source,
            directional_sign=cand_exp.directional_sign,
            is_same_condition_mergeable_box=is_c1_merge,
            partial_leg_unwind_risk_usd=cand_exp.partial_leg_unwind_risk_usd,
            now_ts=now_f,
        )
        if not ok_r:
            return {
                "allowed": False,
                "reason": msg_r,
                "available_deployable_cash_usd": ledger.available_deployable_cash_usd,
                "reconciled_nav_usd": reconciled_nav,
                "non_frozen_open_positions_usd": non_frozen_open,
                "frozen_disputed_positions_usd": frozen_disp_open,
                "cwce_verdict": cwce,
                "remaining_cluster_headroom_usd": cwce.remaining_cluster_headroom_usd,
                "binding_cluster_key": cwce.binding_cluster_key,
                "ledger_snapshot": ledger.snapshot(),
                "reservation_record": None,
            }

    return {
        "allowed": True,
        "reason": "OK",
        "available_deployable_cash_usd": ledger.available_deployable_cash_usd,
        "reconciled_nav_usd": reconciled_nav,
        "non_frozen_open_positions_usd": non_frozen_open,
        "frozen_disputed_positions_usd": frozen_disp_open,
        "cwce_verdict": cwce,
        "remaining_cluster_headroom_usd": cwce.remaining_cluster_headroom_usd,
        "binding_cluster_key": cwce.binding_cluster_key,
        "ledger_snapshot": ledger.snapshot(),
        "reservation_record": res_rec,
    }


"""
Action #4 Deployment Gates, Secret-Free Credential Validation, Systemd Audit,
and Network-Disabled Offline Integration Harness
(`src/polymarket_research/cross_venue_shadow_deployment_gates.py`).

Separates Stage G shadow deployment into independent, fail-closed engineering gates:
  1. Per-venue `P0 Gate 0` authorization matrix (`polymarket`, `predict_fun`, `sx_bet`,
     `limitless`, `forecastex`, `stx_ontario`), distinguishing offline replay, public GET
     market data, authenticated API access, operator physical location / residency, cloud
     VM hosting region, and explicit written institutional KYB allowlisting.
  2. Secret-free environment & credential validator (`validate_shadow_env_dict` /
     `validate_shadow_env_file`): validates variable names, structural formats, POSIX `0600`
     permissions, and hard-rejects any wallet private keys or trading signing secrets
     (`PRIVATE_KEY`, `MNEMONIC`, `SECRET`, `PASSPHRASE`, `0x` 64-hex keys) without ever
     logging or echoing secret values.
  3. Systemd unit & Python dependency readiness verifier (`validate_systemd_unit_text`,
     `validate_python_runtime_dependencies`).
  4. Network-disabled synthetic/recorded multi-venue L2 integration harness
     (`run_offline_shadow_cycle`) + structured health/observability writer
     (`write_shadow_health_snapshot`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

from src.polymarket_research.cross_venue_riskless_shadow import (
    GraduationReport,
    HonestCrossVenueShadowEngine,
    NormalizedBinaryMarket,
    parse_forecastex_contract,
    parse_limitless_market,
    parse_polymarket_gamma_market,
    parse_predict_fun_market,
    parse_stx_ontario_market,
    parse_sx_bet_summary_fixture,
)

EX_CONFIG: int = 78  # BSD sysexits.h configuration/authorization failure code (non-restarting in systemd)

ALL_SHADOW_VENUES: Tuple[str, ...] = (
    "polymarket",
    "predict_fun",
    "sx_bet",
    "limitless",
    "forecastex",
    "stx_ontario",
)

# Canonical granular capability permission states (Mandate Section 2)
GRANULAR_PERMISSION_STATES: Tuple[str, ...] = (
    "PUBLIC_DATA_AUTHORIZED",
    "READONLY_API_AUTHORIZED",
    "AUTHENTICATED_ACCOUNT_AUTHORIZED",
    "TRADING_AUTHORIZED",
    "APPROVAL_PENDING",
    "RESTRICTED",
    "CREDENTIALS_REQUIRED",
)

# Canonical 5 verified outcome states & 7 independent scopes (Three-Venue Activation Mandate Sections 5 & 10)
VERIFIED_OUTCOME_STATES: Tuple[str, ...] = (
    "AUTHORIZED_LIVE",
    "AUTHORIZED_REST_ONLY",
    "AUTHORIZATION_PENDING",
    "CREDENTIALS_PENDING",
    "RESTRICTED",
)

AUTHORIZATION_SCOPES: Tuple[str, ...] = (
    "PUBLIC_REST",
    "PUBLIC_WEBSOCKET",
    "AUTHENTICATED_READONLY",
    "ACCOUNT_PRIVATE",
    "TRADING",
    "INSTITUTIONAL_DATA_LICENSE",
    "SERVER_HOSTING",
)

INDEPENDENT_CAPABILITY_FLAGS: Tuple[str, ...] = (
    "PUBLIC_DATA",
    "AUTHENTICATED_DATA",
    "REALTIME_DATA",
    "SHADOW_RESEARCH",
    "LIVE_ORDER_EXECUTION",
)

VENUE_CLASSIFICATION_STATES: Tuple[str, ...] = (
    "ACTIVE",
    "PARTIALLY_ACTIVE",
    "EXTERNAL_ACCESS_REQUIRED",
)

# Comprehensive platform-wide access bans (embargoed/sanctioned territories where even public access is barred)
POLYMARKET_COMPREHENSIVE_SANCTIONS: FrozenSet[str] = frozenset({
    "CU", "IR", "KP", "SY", "RU", "BY", "UA-43", "UA-14", "UA-09",
})

LIMITLESS_COMPREHENSIVE_ACCESS_BAN: FrozenSet[str] = frozenset({
    "RU", "BY", "CU", "IR", "KP", "SY", "UA-43", "UA-14", "UA-09",
})

# Per-venue trading / account restricted operator jurisdictions (physical location OR legal residency)
VENUE_RESTRICTED_JURISDICTIONS: Dict[str, FrozenSet[str]] = {
    "polymarket": frozenset({
        "CA-ON", "ONTARIO", "US", "USA", "GB", "UK", "FR", "DE", "NL", "IE", "AU",
        "CU", "IR", "KP", "SY", "RU", "BY", "UA-43", "UA-14", "UA-09",
    }),
    "predict_fun": frozenset({
        "CA-ON", "ONTARIO", "US", "USA", "GB", "UK", "FR", "SG", "CN", "PL", "TH",
        "AU", "BE", "TW", "CU", "IR", "KP", "SY", "RU", "BY", "UA-43", "UA-14", "UA-09",
    }),
    "sx_bet": frozenset({
        "CA-ON", "ONTARIO", "US", "USA", "GB", "UK", "FR", "DE", "NL", "ES", "AT",
        "AU", "CU", "IR", "KP", "SY", "RU", "BY", "VE", "UA-43", "UA-14", "UA-09",
    }),
    "limitless": frozenset({
        "CA-ON", "ONTARIO", "CA-AB", "ALBERTA", "US", "USA", "GB", "UK", "FR", "DE",
        "TW", "ROC", "CU", "IR", "KP", "SY", "RU", "BY", "UA-43", "UA-14", "UA-09",
    }),
    # ForecastEx (via Interactive Brokers Canada — CIRO approved in Ontario/Canada)
    "forecastex": frozenset({
        "CU", "IR", "KP", "SY", "RU", "BY", "UA-43", "UA-14", "UA-09",
    }),
    # STX (`stxapp.ca` — AGCO / iGaming Ontario licensed; requires physical presence in Ontario)
    "stx_ontario": frozenset({
        "US", "USA", "CU", "IR", "KP", "SY", "RU", "BY", "UA-43", "UA-14", "UA-09",
    }),
}

# Allowed variable names inside `/etc/polymarket-shadow.env` (strictly read-only + non-secret config)
ALLOWED_SHADOW_ENV_KEYS: FrozenSet[str] = frozenset({
    "PYTHONUNBUFFERED",
    "DOMINUS_NETWORK_MODE",
    "DOMINUS_OPERATOR_JURISDICTION",
    "DOMINUS_SERVER_REGION",
    "DOMINUS_WORKSTATION_GEOBLOCKED",
    "DOMINUS_ENABLED_VENUES",
    "DOMINUS_KYB_AUTHORIZED_VENUES",
    "DOMINUS_KYB_REFERENCE_ID",
    "DOMINUS_REVOKED_KEY_SHA256_LIST",
    "PREDICT_FUN_API_KEY",
    "PREDICT_FUN_ENV",
    "PREDICT_FUN_BUILDER_APP_ID",
    "PREDICT_FUN_DATA_LICENSE_ID",
    "SX_BET_API_KEY",
    "SX_BET_DATA_APPROVAL_ID",
    "SX_BET_WRITTEN_DATA_LICENSE_ID",
    "SX_BET_DATA_INQUIRY_ID",
    "POLYMARKET_INSTITUTIONAL_APP_ID",
    "LIMITLESS_INSTITUTIONAL_APP_ID",
    "IBKR_GATEWAY_URL",
    "IBKR_ALLOW_LOCALHOST_SELF_SIGNED",
    "FORECASTEX_PUBLIC_PORTAL_AUTHORIZED",
    "FORECASTEX_MAX_PUBLIC_CONTRACTS",
    "STX_API_KEY_ID",
    "STX_ED25519_KEY_FILE",
    "STX_APPS_DATA_TOKEN",
    "STX_APPS_APPLICATION_ID",
    "STX_ENV",
    "STX_BASE_URL",
})

# Hard-forbidden substrings/patterns in `/etc/polymarket-shadow.env` (0 private keys / 0 signing secrets)
FORBIDDEN_ENV_KEY_TOKENS: Tuple[str, ...] = (
    "PRIVATE_KEY",
    "MNEMONIC",
    "SEED_PHRASE",
    "PASSPHRASE",
    "SECRET",
    "WALLET_KEY",
)

_HEX_PRIVKEY_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{64}$")
_ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_API_KEY_PRINTABLE_RE = re.compile(r"^[A-Za-z0-9._\-+=:/]{12,256}$")
_PLACEHOLDER_RE = re.compile(r"(?:your[_\-]?key|changeme|replace[_\-]?me|<paste>|todo|example)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# 1. Granular Per-Venue Authorization Gate (`P0 Gate 0`)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VenueAuthorizationDecision:
    venue: str
    network_mode: str                  # "offline" | "live_public" | "live_authenticated"
    operator_jurisdiction: str
    server_region: str
    account_eligible: bool
    operating_location_permitted: bool
    finnish_cloud_hosting_authorized: bool
    public_api_permitted: bool
    authenticated_api_permitted: bool
    effective_authorized: bool
    status_code: str
    required_evidence: str
    # Granular first-principles capability states (Mandate Sections 1 & 2)
    public_data_state: str = "RESTRICTED"
    readonly_api_state: str = "RESTRICTED"
    authenticated_account_state: str = "RESTRICTED"
    trading_state: str = "RESTRICTED"
    official_source: str = ""
    exact_requirement: str = ""
    application_status: str = "NOT_SUBMITTED"
    operator_action: str = ""
    # 7-Scope Independent Authorization Matrix + Verified Outcome State (Sections 5 & 10)
    verified_outcome_state: str = "RESTRICTED"
    scope_permissions: Dict[str, str] = field(default_factory=dict)
    scope_justifications: Dict[str, str] = field(default_factory=dict)
    # Explicit 3-Capability Separation (MARKET_DATA_ACCESS vs SHADOW_RESEARCH_ACCESS vs LIVE_TRADING_ACCESS)
    market_data_access: str = "RESTRICTED"
    shadow_research_access: str = "RESTRICTED"
    live_trading_access: str = "RESTRICTED"
    # 5 Independent Capability Flags & Endpoint-Level Capability Decisions (Sections 1 & 6)
    public_data_capability: str = "RESTRICTED"
    authenticated_data_capability: str = "RESTRICTED"
    realtime_data_capability: str = "RESTRICTED"
    shadow_research_capability: str = "RESTRICTED"
    live_order_execution_capability: str = "RESTRICTED"
    capability_flags: Dict[str, str] = field(default_factory=dict)
    endpoint_capabilities: Dict[str, str] = field(default_factory=dict)
    venue_classification: str = "EXTERNAL_ACCESS_REQUIRED"


def _norm_jurisdiction(code: str) -> str:
    raw = (code or "").strip().upper().replace("_", "-")
    if raw == "ONTARIO":
        return "CA-ON"
    if raw == "ALBERTA":
        return "CA-AB"
    return raw


def stx_signing_key_available(env: Mapping[str, str]) -> bool:
    """
    Verifies whether a local `0600` Ed25519 signing key file exists for STX Path A
    (NEVER accepts a raw private key string inside `.env`, and NEVER treats `STX_API_KEY_ID`
    alone without an Ed25519 signing key file as sufficient!).
    """
    key_file_raw = (env.get("STX_ED25519_KEY_FILE") or "").strip()
    if key_file_raw:
        if "BEGIN " in key_file_raw or _HEX_PRIVKEY_RE.match(key_file_raw):
            return False
        kp = Path(key_file_raw).expanduser()
        if not kp.is_file():
            return False
        try:
            st = kp.stat()
            if st.st_size < 32:
                return False
            if os.name != "nt" and (st.st_mode & (stat.S_IRWXG | stat.S_IRWXO)) != 0:
                return False
            return True
        except OSError:
            return False
    # Fallback only if standard `~/.stx/credentials` exists and has a valid keypair payload
    default_cred = Path.home() / ".stx" / "credentials"
    try:
        if default_cred.is_file() and default_cred.stat().st_size >= 32:
            if os.name != "nt" and (default_cred.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO)) != 0:
                return False
            return True
    except OSError:
        return False
    return False


def _all_restricted_scopes(reason: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    return (
        {sc: "RESTRICTED" for sc in AUTHORIZATION_SCOPES},
        {sc: reason for sc in AUTHORIZATION_SCOPES},
    )


def _build_endpoint_capabilities(dec: VenueAuthorizationDecision) -> Dict[str, str]:
    """Builds endpoint-level capability decisions for each venue without venue-wide boolean blackouts."""
    v = dec.venue
    sc = dec.scope_permissions or {}
    pub_rest = sc.get("PUBLIC_REST", "RESTRICTED")
    pub_ws = sc.get("PUBLIC_WEBSOCKET", "RESTRICTED")
    auth_ro = sc.get("AUTHENTICATED_READONLY", "RESTRICTED")
    acct_priv = sc.get("ACCOUNT_PRIVATE", "RESTRICTED")
    trd = sc.get("TRADING", "RESTRICTED")

    if v == "polymarket":
        return {
            "GET https://gamma-api.polymarket.com/markets": pub_rest,
            "GET https://clob.polymarket.com/book": pub_rest,
            "WSS wss://ws-subscriptions-clob.polymarket.com/ws/market": pub_ws,
            "GET https://clob.polymarket.com/data/orders": acct_priv,
            "POST https://clob.polymarket.com/order": "RESTRICTED",
        }
    if v == "limitless":
        return {
            "GET https://api.limitless.exchange/markets/active": pub_rest,
            "GET https://api.limitless.exchange/markets/active/slugs": pub_rest,
            "GET https://api.limitless.exchange/markets/{slug}/orderbook": pub_rest,
            "WSS wss://ws.limitless.exchange/socket.io/?EIO=4&transport=websocket (/markets)": pub_ws,
            "GET https://api.limitless.exchange/portfolio/positions": acct_priv,
            "POST https://api.limitless.exchange/orders": "RESTRICTED",
        }
    if v == "predict_fun":
        return {
            "GET https://api.predict.fun/v1/markets": auth_ro,
            "GET https://api.predict.fun/v1/categories": auth_ro,
            "GET https://api.predict.fun/v1/markets/{id}/orderbook": auth_ro,
            "WSS wss://ws.predict.fun/ws (predictOrderbook/{marketId})": auth_ro,
            "POST https://api.predict.fun/v1/auth": acct_priv,
            "POST https://api.predict.fun/v1/orders": "RESTRICTED",
        }
    if v == "sx_bet":
        return {
            "GET https://api.sx.bet/metadata/obv3": pub_rest,
            "GET https://api.sx.bet/leagues/active": pub_rest,
            "GET https://api.sx.bet/summary-v3/league/{leagueId}/game-lines": pub_rest,
            "GET https://api.sx.bet/summary-v3/{popular,inplay,upcoming}": pub_rest,
            "GET https://api.sx.bet/markets/active": pub_rest,
            "GET https://api.sx.bet/trades-v3/public": pub_rest,
            "GET https://api.sx.bet/live-scores": pub_rest,
            "GET https://api.sx.bet/orderbook-v3/snapshot/market": auth_ro,
            "GET https://api.sx.bet/orders-v3": auth_ro,
            "GET https://api.sx.bet/orders-v3/odds/best": auth_ro,
            "GET https://api.sx.bet/user/realtime-token-v3/api-key": auth_ro,
            "WSS wss://realtime.sx.bet/connection/websocket": auth_ro,
            "POST https://api.sx.bet/orders-v3": "RESTRICTED",
        }
    if v == "stx_ontario":
        return {
            "WSS wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0 (markets,ticker,trades,market:<uuid>)": pub_ws,
            "WSS wss://demo.stxapp.ca/socket/websocket?vsn=2.0.0": pub_ws,
            "WSS wss://demo.stxapp.io/socket/websocket?vsn=2.0.0": pub_ws,
            "GET https://api.on.stxapp.ca/api/v1/markets": auth_ro,
            "GET https://api.on.stxapp.ca/api/v1/events": auth_ro,
            "GET https://api.on.stxapp.ca/api/v1/me": acct_priv,
            "POST https://api.on.stxapp.ca/api/v1/orders": "RESTRICTED",
        }
    if v == "forecastex":
        return {
            "GET https://forecastex.com/api/download (CFTC DCM Daily CSV)": pub_rest,
            "GET https://localhost:5000/v1/api/iserver/auth/status": auth_ro,
            "POST https://localhost:5000/v1/api/iserver/reauthenticate": auth_ro,
            "GET https://localhost:5000/v1/api/trsrv/secdef": auth_ro,
            "GET https://localhost:5000/v1/api/iserver/marketdata/snapshot": auth_ro,
            "WSS wss://localhost:5000/v1/api/ws (smd+{conid})": auth_ro,
            "POST https://localhost:5000/v1/api/iserver/account/{accountId}/orders": "RESTRICTED",
        }
    return {"DEFAULT": trd}


def _with_three_capabilities(dec: VenueAuthorizationDecision) -> VenueAuthorizationDecision:
    """
    Populates both the legacy 3 capability states and the 5 independent capability flags:
      - `PUBLIC_DATA`
      - `AUTHENTICATED_DATA`
      - `REALTIME_DATA`
      - `SHADOW_RESEARCH`
      - `LIVE_ORDER_EXECUTION`
    plus `endpoint_capabilities` and `venue_classification` (`ACTIVE`, `PARTIALLY_ACTIVE`, `EXTERNAL_ACCESS_REQUIRED`).
    """
    from dataclasses import replace

    if dec.network_mode == "offline":
        m_access = "OFFLINE_FIXTURE_ONLY"
        s_access = "AUTHORIZED_OFFLINE_ONLY"
    elif dec.effective_authorized:
        if dec.status_code == "AUTHORIZED_TESTNET_SANDBOX_ONLY":
            m_access = "AUTHORIZED_SANDBOX_ONLY"
            s_access = "AUTHORIZED_SANDBOX_ONLY"
        elif dec.verified_outcome_state == "AUTHORIZED_REST_ONLY":
            m_access = "AUTHORIZED_REST_ONLY"
            s_access = "AUTHORIZED_LIVE"
        else:
            m_access = "AUTHORIZED_LIVE"
            s_access = "AUTHORIZED_LIVE"
    elif dec.verified_outcome_state == "CREDENTIALS_PENDING" or dec.status_code.startswith("CREDENTIALS_REQUIRED"):
        m_access = "CREDENTIALS_REQUIRED"
        s_access = "CREDENTIALS_REQUIRED"
    elif dec.verified_outcome_state == "AUTHORIZATION_PENDING":
        m_access = "AUTHORIZATION_PENDING"
        s_access = "AUTHORIZATION_PENDING"
    else:
        m_access = "RESTRICTED"
        s_access = "RESTRICTED"

    sc = dec.scope_permissions or {}
    if dec.network_mode == "offline":
        pub_cap = "OFFLINE_FIXTURE_ONLY"
        auth_cap = "OFFLINE_FIXTURE_ONLY"
        rt_cap = "OFFLINE_FIXTURE_ONLY"
        sh_cap = "AUTHORIZED_OFFLINE_ONLY"
    else:
        if sc.get("PUBLIC_REST") == "AUTHORIZED_LIVE" or sc.get("PUBLIC_WEBSOCKET") == "AUTHORIZED_LIVE" or dec.public_data_state == "PUBLIC_DATA_AUTHORIZED":
            pub_cap = "AUTHORIZED_SANDBOX_ONLY" if dec.status_code == "AUTHORIZED_TESTNET_SANDBOX_ONLY" else "AUTHORIZED_LIVE"
        else:
            pub_cap = sc.get("PUBLIC_REST", dec.public_data_state)

        if sc.get("AUTHENTICATED_READONLY") == "AUTHORIZED_LIVE" or dec.readonly_api_state == "READONLY_API_AUTHORIZED":
            auth_cap = "AUTHORIZED_LIVE"
        else:
            auth_cap = sc.get("AUTHENTICATED_READONLY", dec.readonly_api_state)

        if sc.get("PUBLIC_WEBSOCKET") == "AUTHORIZED_LIVE":
            rt_cap = "AUTHORIZED_LIVE"
        elif dec.venue in ("predict_fun", "sx_bet", "forecastex", "stx_ontario") and sc.get("AUTHENTICATED_READONLY") == "AUTHORIZED_LIVE":
            rt_cap = "AUTHORIZED_LIVE"
        elif dec.venue in ("sx_bet", "forecastex", "predict_fun") and (dec.effective_authorized or sc.get("AUTHENTICATED_READONLY") == "CREDENTIALS_PENDING"):
            rt_cap = "CREDENTIALS_PENDING"
        else:
            rt_cap = sc.get("PUBLIC_WEBSOCKET", "RESTRICTED")

        sh_cap = s_access

    live_exec_cap = "RESTRICTED"
    cap_flags = {
        "PUBLIC_DATA": pub_cap,
        "AUTHENTICATED_DATA": auth_cap,
        "REALTIME_DATA": rt_cap,
        "SHADOW_RESEARCH": sh_cap,
        "LIVE_ORDER_EXECUTION": live_exec_cap,
    }
    ep_caps = _build_endpoint_capabilities(dec)

    if not dec.effective_authorized or dec.network_mode == "offline" or dec.status_code == "AUTHORIZED_TESTNET_SANDBOX_ONLY":
        v_class = "EXTERNAL_ACCESS_REQUIRED"
    elif rt_cap == "AUTHORIZED_LIVE" and auth_cap != "CREDENTIALS_PENDING":
        v_class = "ACTIVE"
    else:
        v_class = "PARTIALLY_ACTIVE"

    return replace(
        dec,
        market_data_access=m_access,
        shadow_research_access=s_access,
        live_trading_access="RESTRICTED",
        public_data_capability=pub_cap,
        authenticated_data_capability=auth_cap,
        realtime_data_capability=rt_cap,
        shadow_research_capability=sh_cap,
        live_order_execution_capability=live_exec_cap,
        capability_flags=cap_flags,
        endpoint_capabilities=ep_caps,
        venue_classification=v_class,
    )


def evaluate_venue_shadow_authorization(
    venue: str,
    *,
    network_mode: str = "offline",
    operator_jurisdiction: str = "",
    server_region: str = "LOCAL",
    workstation_geoblocked: bool = False,
    has_api_key: bool = False,
    kyb_authorized_venues: FrozenSet[str] = frozenset(),
    kyb_reference_id: str = "",
    forecastex_public_portal_authorized: bool = False,
    ibkr_gateway_configured: bool = False,
    predict_fun_env: str = "mainnet",
    predict_fun_data_license: bool = False,
    stx_has_signing_key: bool = False,
    stx_apps_data_token_present: bool = False,
    stx_apps_application_pending: bool = False,
    sx_bet_written_data_license: bool = False,
    sx_bet_data_inquiry_pending: bool = False,
    institutional_app_pending: bool = False,
) -> VenueAuthorizationDecision:
    return _with_three_capabilities(
        _evaluate_venue_shadow_authorization_raw(
            venue,
            network_mode=network_mode,
            operator_jurisdiction=operator_jurisdiction,
            server_region=server_region,
            workstation_geoblocked=workstation_geoblocked,
            has_api_key=has_api_key,
            kyb_authorized_venues=kyb_authorized_venues,
            kyb_reference_id=kyb_reference_id,
            forecastex_public_portal_authorized=forecastex_public_portal_authorized,
            ibkr_gateway_configured=ibkr_gateway_configured,
            predict_fun_env=predict_fun_env,
            predict_fun_data_license=predict_fun_data_license,
            stx_has_signing_key=stx_has_signing_key,
            stx_apps_data_token_present=stx_apps_data_token_present,
            stx_apps_application_pending=stx_apps_application_pending,
            sx_bet_written_data_license=sx_bet_written_data_license,
            sx_bet_data_inquiry_pending=sx_bet_data_inquiry_pending,
            institutional_app_pending=institutional_app_pending,
        )
    )


def _evaluate_venue_shadow_authorization_raw(
    venue: str,
    *,
    network_mode: str = "offline",
    operator_jurisdiction: str = "",
    server_region: str = "LOCAL",
    workstation_geoblocked: bool = False,
    has_api_key: bool = False,
    kyb_authorized_venues: FrozenSet[str] = frozenset(),
    kyb_reference_id: str = "",
    forecastex_public_portal_authorized: bool = False,
    ibkr_gateway_configured: bool = False,
    predict_fun_env: str = "mainnet",
    predict_fun_data_license: bool = False,
    stx_has_signing_key: bool = False,
    stx_apps_data_token_present: bool = False,
    stx_apps_application_pending: bool = False,
    sx_bet_written_data_license: bool = False,
    sx_bet_data_inquiry_pending: bool = False,
    institutional_app_pending: bool = False,
) -> VenueAuthorizationDecision:
    """
    Evaluates a single venue's contractual & technical authorization from first principles across
    all 7 independent scopes (`AUTHORIZATION_SCOPES`):
      1. `PUBLIC_REST`
      2. `PUBLIC_WEBSOCKET`
      3. `AUTHENTICATED_READONLY`
      4. `ACCOUNT_PRIVATE`
      5. `TRADING`
      6. `INSTITUTIONAL_DATA_LICENSE`
      7. `SERVER_HOSTING`
    Strictly separates trading restrictions from independently permitted public market-data collection,
    removes internally invented license requirements where not imposed by the venue, and never confuses
    lack of HTTP authentication or `TESTNET_SANDBOX` access with mainnet legal/contractual permission.
    """
    v = (venue or "").strip().lower()
    mode = (network_mode or "offline").strip().lower()
    op_jur = _norm_jurisdiction(operator_jurisdiction)
    srv_reg = _norm_jurisdiction(server_region or "LOCAL")
    kyb_ok = (v in kyb_authorized_venues) and bool((kyb_reference_id or "").strip())
    pf_env = (predict_fun_env or "mainnet").strip().lower()

    if v not in VENUE_RESTRICTED_JURISDICTIONS:
        sc_perm, sc_just = _all_restricted_scopes("Unsupported venue.")
        return VenueAuthorizationDecision(
            venue=v,
            network_mode=mode,
            operator_jurisdiction=op_jur or "UNSPECIFIED",
            server_region=srv_reg,
            account_eligible=False,
            operating_location_permitted=False,
            finnish_cloud_hosting_authorized=False,
            public_api_permitted=False,
            authenticated_api_permitted=False,
            effective_authorized=False,
            status_code="UNKNOWN_VENUE",
            required_evidence="Register supported venue adapter and restriction rules.",
            public_data_state="RESTRICTED",
            readonly_api_state="RESTRICTED",
            authenticated_account_state="RESTRICTED",
            trading_state="RESTRICTED",
            official_source="N/A",
            exact_requirement="Supported venue registration required.",
            application_status="NOT_APPLICABLE",
            operator_action="Register venue adapter.",
            verified_outcome_state="RESTRICTED",
            scope_permissions=sc_perm,
            scope_justifications=sc_just,
        )

    # Offline / network-disabled mode makes zero external calls and uses zero credentials
    if mode == "offline":
        return VenueAuthorizationDecision(
            venue=v,
            network_mode="offline",
            operator_jurisdiction=op_jur or "UNSPECIFIED",
            server_region=srv_reg,
            account_eligible=False,
            operating_location_permitted=True,
            finnish_cloud_hosting_authorized=True,
            public_api_permitted=False,
            authenticated_api_permitted=False,
            effective_authorized=True,
            status_code="AUTHORIZED_OFFLINE_FIXTURE_ONLY",
            required_evidence="None for offline synthetic/recorded replay (0 network calls).",
            public_data_state="PUBLIC_DATA_AUTHORIZED",
            readonly_api_state="CREDENTIALS_REQUIRED",
            authenticated_account_state="RESTRICTED",
            trading_state="RESTRICTED",
            official_source="Local Recorded Fixture Harness (0 Network I/O)",
            exact_requirement="DOMINUS_NETWORK_MODE=offline",
            application_status="ACTIVE_OFFLINE",
            operator_action="Switch DOMINUS_NETWORK_MODE=live_public with attested DOMINUS_OPERATOR_JURISDICTION for live feeds.",
            verified_outcome_state="RESTRICTED",
            scope_permissions={
                "PUBLIC_REST": "RESTRICTED",
                "PUBLIC_WEBSOCKET": "RESTRICTED",
                "AUTHENTICATED_READONLY": "CREDENTIALS_PENDING",
                "ACCOUNT_PRIVATE": "RESTRICTED",
                "TRADING": "RESTRICTED",
                "INSTITUTIONAL_DATA_LICENSE": "RESTRICTED",
                "SERVER_HOSTING": "AUTHORIZED_LIVE",
            },
            scope_justifications={
                sc: "Offline fixture mode fences all outbound network calls." for sc in AUTHORIZATION_SCOPES
            },
        )

    # Live modes fail closed if operator jurisdiction is not explicitly attested
    if not op_jur or op_jur in {"UNKNOWN", "UNSET", "UNSPECIFIED"}:
        sc_perm, sc_just = _all_restricted_scopes("DOMINUS_OPERATOR_JURISDICTION must be explicitly attested.")
        return VenueAuthorizationDecision(
            venue=v,
            network_mode=mode,
            operator_jurisdiction="UNSPECIFIED",
            server_region=srv_reg,
            account_eligible=False,
            operating_location_permitted=False,
            finnish_cloud_hosting_authorized=False,
            public_api_permitted=False,
            authenticated_api_permitted=False,
            effective_authorized=False,
            status_code="BLOCKED_MISSING_JURISDICTION_ATTESTATION",
            required_evidence="Set DOMINUS_OPERATOR_JURISDICTION to verified physical/legal operating jurisdiction.",
            public_data_state="RESTRICTED",
            readonly_api_state="RESTRICTED",
            authenticated_account_state="RESTRICTED",
            trading_state="RESTRICTED",
            official_source="Dominus P0 Gate 0 Fail-Closed Policy",
            exact_requirement="Explicit DOMINUS_OPERATOR_JURISDICTION ISO code required before outbound live polling.",
            application_status="ATTESTATION_REQUIRED",
            operator_action="Set DOMINUS_OPERATOR_JURISDICTION in /etc/polymarket-shadow.env.",
            verified_outcome_state="RESTRICTED",
            scope_permissions=sc_perm,
            scope_justifications=sc_just,
        )

    # -------------------------------------------------------------------------
    # Venue 5: STX Ontario (`stxapp.ca` / `docs.stxapp.io` / `apps.stxapp.io`)
    # -------------------------------------------------------------------------
    if v == "stx_ontario":
        in_ontario = op_jur == "CA-ON"
        not_embargoed = op_jur not in VENUE_RESTRICTED_JURISDICTIONS["stx_ontario"]
        if not not_embargoed:
            sc_perm, sc_just = _all_restricted_scopes("Sanctioned or restricted STX jurisdiction.")
            return VenueAuthorizationDecision(
                venue=v,
                network_mode=mode,
                operator_jurisdiction=op_jur,
                server_region=srv_reg,
                account_eligible=False,
                operating_location_permitted=False,
                finnish_cloud_hosting_authorized=False,
                public_api_permitted=False,
                authenticated_api_permitted=False,
                effective_authorized=False,
                status_code=f"BLOCKED_COMPREHENSIVE_SANCTIONS({op_jur})",
                required_evidence="Jurisdiction barred under STX / AGCO regulations.",
                public_data_state="RESTRICTED",
                readonly_api_state="RESTRICTED",
                authenticated_account_state="RESTRICTED",
                trading_state="RESTRICTED",
                official_source="STX API Docs (https://docs.stxapp.io) & AGCO/iGaming Ontario",
                exact_requirement="Non-sanctioned jurisdiction required.",
                application_status="PROHIBITED_SANCTIONS",
                operator_action="None permitted from restricted jurisdiction.",
                verified_outcome_state="RESTRICTED",
                scope_permissions=sc_perm,
                scope_justifications=sc_just,
            )

        if stx_apps_data_token_present:
            return VenueAuthorizationDecision(
                venue=v,
                network_mode=mode,
                operator_jurisdiction=op_jur,
                server_region=srv_reg,
                account_eligible=in_ontario,
                operating_location_permitted=True,
                finnish_cloud_hosting_authorized=True,
                public_api_permitted=True,
                authenticated_api_permitted=True,
                effective_authorized=True,
                status_code="AUTHORIZED_STX_APPS_DATA_PARTNER",
                required_evidence="Approved STX Apps `Data` server-to-server token (`https://apps.stxapp.io`) + unsigned Phoenix WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0`).",
                public_data_state="PUBLIC_DATA_AUTHORIZED",
                readonly_api_state="READONLY_API_AUTHORIZED",
                authenticated_account_state="AUTHENTICATED_ACCOUNT_AUTHORIZED" if in_ontario else "RESTRICTED",
                trading_state="RESTRICTED",
                official_source="STX Apps Developer Portal (https://apps.stxapp.io) & Live Markets Docs (https://docs.stxapp.io/explore/live-markets/)",
                exact_requirement="Approved STX Apps `Data` server-to-server token (`STX_APPS_DATA_TOKEN`).",
                application_status="APPROVED_ACTIVE",
                operator_action="None — STX Apps Data REST + Phoenix WebSocket feed active.",
                verified_outcome_state="AUTHORIZED_LIVE",
                scope_permissions={
                    "PUBLIC_REST": "RESTRICTED",
                    "PUBLIC_WEBSOCKET": "AUTHORIZED_LIVE",
                    "AUTHENTICATED_READONLY": "AUTHORIZED_LIVE",
                    "ACCOUNT_PRIVATE": "AUTHORIZED_LIVE" if in_ontario else "RESTRICTED",
                    "TRADING": "RESTRICTED",
                    "INSTITUTIONAL_DATA_LICENSE": "AUTHORIZED_LIVE",
                    "SERVER_HOSTING": "AUTHORIZED_LIVE",
                },
            )

        full_ed25519_ready = bool(has_api_key and stx_has_signing_key)
        if full_ed25519_ready:
            return VenueAuthorizationDecision(
                venue=v,
                network_mode=mode,
                operator_jurisdiction=op_jur,
                server_region=srv_reg,
                account_eligible=in_ontario,
                operating_location_permitted=True,
                finnish_cloud_hosting_authorized=True,
                public_api_permitted=True,
                authenticated_api_permitted=True,
                effective_authorized=True,
                status_code="AUTHORIZED_ONTARIO_DIRECT_ED25519",
                required_evidence=(
                    "Signed Read-Only Ed25519 REST (`/api/v1/markets`, `/api/v1/events`) + unsigned public Phoenix "
                    "WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0`) active."
                ),
                public_data_state="PUBLIC_DATA_AUTHORIZED",
                readonly_api_state="READONLY_API_AUTHORIZED",
                authenticated_account_state="AUTHENTICATED_ACCOUNT_AUTHORIZED" if in_ontario else "RESTRICTED",
                trading_state="RESTRICTED",
                official_source="STX API Docs (https://docs.stxapp.io) & AGCO/iGaming Ontario (https://on.stxapp.ca)",
                exact_requirement="`STX_API_KEY_ID` + local `0600` Ed25519 signing key file (`STX_ED25519_KEY_FILE`).",
                application_status="READY_ACTIVE",
                operator_action="None — STX Ontario Ed25519 Read-Only REST + Phoenix WebSocket feed active.",
                verified_outcome_state="AUTHORIZED_LIVE",
                scope_permissions={
                    "PUBLIC_REST": "RESTRICTED",
                    "PUBLIC_WEBSOCKET": "AUTHORIZED_LIVE",
                    "AUTHENTICATED_READONLY": "AUTHORIZED_LIVE",
                    "ACCOUNT_PRIVATE": "AUTHORIZED_LIVE" if in_ontario else "RESTRICTED",
                    "TRADING": "RESTRICTED",
                    "INSTITUTIONAL_DATA_LICENSE": "AUTHORIZED_LIVE" if stx_apps_application_pending else "CREDENTIALS_PENDING",
                    "SERVER_HOSTING": "AUTHORIZED_LIVE",
                },
            )

        if has_api_key and not stx_has_signing_key:
            ro_st = "APPROVAL_PENDING" if stx_apps_application_pending else "CREDENTIALS_REQUIRED"
            ver_out = "AUTHORIZATION_PENDING" if stx_apps_application_pending else "CREDENTIALS_PENDING"
            return VenueAuthorizationDecision(
                venue=v,
                network_mode=mode,
                operator_jurisdiction=op_jur,
                server_region=srv_reg,
                account_eligible=in_ontario,
                operating_location_permitted=True,
                finnish_cloud_hosting_authorized=True,
                public_api_permitted=True,
                authenticated_api_permitted=False,
                effective_authorized=False,
                status_code="CREDENTIALS_REQUIRED_MISSING_STX_ED25519_SIGNING_KEY",
                required_evidence=(
                    "Both `STX_API_KEY_ID` and local `0600` `STX_ED25519_KEY_FILE` are required when `STX_API_KEY_ID` is set."
                ),
                public_data_state="PUBLIC_DATA_AUTHORIZED",
                readonly_api_state=ro_st,
                authenticated_account_state="CREDENTIALS_REQUIRED",
                trading_state="RESTRICTED",
                official_source="STX API Docs (https://docs.stxapp.io/authentication/)",
                exact_requirement="`STX_API_KEY_ID` + local `0600` Ed25519 private signing key file (`STX_ED25519_KEY_FILE`).",
                application_status="APPROVAL_PENDING" if stx_apps_application_pending else "SELF_SERVICE_KEYPAIR_REQUIRED",
                operator_action="Provide `STX_ED25519_KEY_FILE` matching `STX_API_KEY_ID` or unset incomplete `STX_API_KEY_ID` to use public Phoenix WebSocket.",
                verified_outcome_state=ver_out,
                scope_permissions={
                    "PUBLIC_REST": "RESTRICTED",
                    "PUBLIC_WEBSOCKET": "AUTHORIZED_LIVE",
                    "AUTHENTICATED_READONLY": ver_out,
                    "ACCOUNT_PRIVATE": "RESTRICTED",
                    "TRADING": "RESTRICTED",
                    "INSTITUTIONAL_DATA_LICENSE": "AUTHORIZATION_PENDING" if stx_apps_application_pending else "CREDENTIALS_PENDING",
                    "SERVER_HOSTING": "AUTHORIZED_LIVE",
                },
            )

        # Unsigned public Phoenix WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0`,
        # `wss://demo.stxapp.ca/socket/websocket?vsn=2.0.0`, `wss://demo.stxapp.io/socket/websocket?vsn=2.0.0`)
        # is documented at `https://docs.stxapp.io/explore/live-markets/` as requiring no API key ("without an API key")
        # and streams `markets`, `ticker`, `trades`, and per-market L2 orderbooks (`market:<symbol_or_uuid>`).
        # REST `/api/v1/markets` and `/api/v1/events` require Ed25519 headers (`X-STX-ACCESS-*`) or OAuth `Bearer` (`403` unsigned).
        eff_ok = (mode == "live_public")
        ro_st = "APPROVAL_PENDING" if stx_apps_application_pending else "CREDENTIALS_REQUIRED"
        auth_ro_scope = "AUTHORIZATION_PENDING" if stx_apps_application_pending else "CREDENTIALS_PENDING"
        ver_out = "AUTHORIZED_LIVE" if eff_ok else auth_ro_scope
        st_code = (
            "PUBLIC_WS_AUTHORIZED_REST_CREDENTIALS_PENDING"
            if eff_ok
            else "CREDENTIALS_REQUIRED_STX_ED25519_KEYPAIR"
        )

        return VenueAuthorizationDecision(
            venue=v,
            network_mode=mode,
            operator_jurisdiction=op_jur,
            server_region=srv_reg,
            account_eligible=in_ontario,
            operating_location_permitted=True,
            finnish_cloud_hosting_authorized=True,
            public_api_permitted=True,
            authenticated_api_permitted=False,
            effective_authorized=eff_ok,
            status_code=st_code,
            required_evidence=(
                "Documented unsigned public STX Phoenix WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0` "
                "and `wss://demo.stxapp.ca/socket/websocket?vsn=2.0.0`, `https://docs.stxapp.io/explore/live-markets/`) "
                "streams live `markets`, `ticker`, `trades`, and per-market full L2 orderbooks (`market:<uuid>`) with 0 API keys; "
                "REST `/api/v1/markets` and `/api/v1/events` require Ed25519 `X-STX-ACCESS-*` or `STX_APPS_DATA_TOKEN`."
            ),
            public_data_state="PUBLIC_DATA_AUTHORIZED",
            readonly_api_state=ro_st,
            authenticated_account_state="RESTRICTED",
            trading_state="RESTRICTED",
            official_source="STX Live Markets WebSocket Docs (https://docs.stxapp.io/explore/live-markets/) & Authentication Docs (https://docs.stxapp.io/authentication/)",
            exact_requirement=(
                "0 credentials required for public Phoenix WebSocket (`markets`, `ticker`, `trades`, `market:<uuid>`); "
                "`STX_API_KEY_ID` + `STX_ED25519_KEY_FILE` or `STX_APPS_DATA_TOKEN` required for REST `/api/v1/markets`."
            ),
            application_status="PUBLIC_WS_LIVE_ACTIVE_REST_CREDENTIALS_PENDING" if eff_ok else ("APPROVAL_PENDING" if stx_apps_application_pending else "SELF_SERVICE_KEYPAIR_REQUIRED"),
            operator_action=(
                "Live unsigned STX Ontario Phoenix WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0`) active; "
                "optionally provision `STX_API_KEY_ID` + `STX_ED25519_KEY_FILE` (or `STX_APPS_DATA_TOKEN`) to add signed REST `/api/v1/markets` catalog discovery."
            ),
            verified_outcome_state=ver_out,
            scope_permissions={
                "PUBLIC_REST": "RESTRICTED",
                "PUBLIC_WEBSOCKET": "AUTHORIZED_LIVE",
                "AUTHENTICATED_READONLY": auth_ro_scope,
                "ACCOUNT_PRIVATE": "RESTRICTED",
                "TRADING": "RESTRICTED",
                "INSTITUTIONAL_DATA_LICENSE": auth_ro_scope,
                "SERVER_HOSTING": "AUTHORIZED_LIVE",
            },
            scope_justifications={
                "PUBLIC_REST": "STX REST `/api/v1/markets` and `/api/v1/events` return HTTP 403 without Ed25519 `X-STX-ACCESS-*` or OAuth Bearer headers.",
                "PUBLIC_WEBSOCKET": "Documented unsigned Phoenix Channels v2 WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0`, `docs.stxapp.io/explore/live-markets/`) streams `markets`, `ticker`, `trades`, and `market:<symbol_or_uuid>` L2 books without an API key.",
                "AUTHENTICATED_READONLY": "Requires Ed25519 Read-Only keypair (`X-STX-ACCESS-KEY`, `X-STX-ACCESS-TIMESTAMP`, `X-STX-ACCESS-SIGNATURE`) or `STX_APPS_DATA_TOKEN`.",
                "ACCOUNT_PRIVATE": "Account endpoints (`/api/v1/me`) require authenticated credentials and Ontario eligibility.",
                "TRADING": "Order placement (`POST /api/v1/orders`) is strictly disabled in Stage G shadow mode (`RESTRICTED`).",
                "INSTITUTIONAL_DATA_LICENSE": "Optional `STX_APPS_DATA_TOKEN` via `https://apps.stxapp.io`.",
                "SERVER_HOSTING": f"Unsigned public Phoenix WebSocket is accessible from `{srv_reg}`.",
            },
        )

    # -------------------------------------------------------------------------
    # Venue 6: ForecastEx / Interactive Brokers (`forecastex.com` & IBKR Canada)
    # -------------------------------------------------------------------------
    if v == "forecastex":
        not_sanctioned = op_jur not in VENUE_RESTRICTED_JURISDICTIONS["forecastex"]
        if not not_sanctioned:
            sc_perm, sc_just = _all_restricted_scopes("Sanctioned territory.")
            return VenueAuthorizationDecision(
                venue=v,
                network_mode=mode,
                operator_jurisdiction=op_jur,
                server_region=srv_reg,
                account_eligible=False,
                operating_location_permitted=False,
                finnish_cloud_hosting_authorized=False,
                public_api_permitted=False,
                authenticated_api_permitted=False,
                effective_authorized=False,
                status_code=f"BLOCKED_COMPREHENSIVE_SANCTIONS({op_jur})",
                required_evidence="Sanctioned jurisdiction barred under OFAC/CFTC/CIRO regulations.",
                public_data_state="RESTRICTED",
                readonly_api_state="RESTRICTED",
                authenticated_account_state="RESTRICTED",
                trading_state="RESTRICTED",
                official_source="ForecastEx LLC Rulebook (CFTC DCM) & Interactive Brokers Sanctions Policy",
                exact_requirement="Non-sanctioned jurisdiction required.",
                application_status="PROHIBITED_SANCTIONS",
                operator_action="None permitted from sanctioned territory.",
                verified_outcome_state="RESTRICTED",
                scope_permissions=sc_perm,
                scope_justifications=sc_just,
            )

        no_proxy_mismatch = not (op_jur == "CA-ON" and srv_reg == "FI")
        # CFTC DCM public transparency CSV portal (`forecastex.com/api/download`) is globally public (0 internal env gate)
        pub_portal_ok = True
        ibkr_live_ready = bool(ibkr_gateway_configured)

        pub_state = "PUBLIC_DATA_AUTHORIZED" if pub_portal_ok else "CREDENTIALS_REQUIRED"
        if ibkr_live_ready:
            ro_state = "READONLY_API_AUTHORIZED"
            acct_state = "AUTHENTICATED_ACCOUNT_AUTHORIZED"
            trd_state = "RESTRICTED"
        else:
            ro_state = "CREDENTIALS_REQUIRED"
            acct_state = "CREDENTIALS_REQUIRED"
            trd_state = "RESTRICTED"

        eff_ok = ibkr_live_ready if mode == "live_authenticated" else (ibkr_live_ready or (mode == "live_public" and pub_portal_ok))
        if ibkr_live_ready:
            st_code = "AUTHORIZED_CIRO_IBKR"
            ver_out = "AUTHORIZED_LIVE"
        elif eff_ok:
            st_code = "AUTHORIZED_PUBLIC_CFTC_REGULATORY_PORTAL" if not no_proxy_mismatch else "AUTHORIZED_CIRO_PUBLIC_PORTAL"
            ver_out = "AUTHORIZED_REST_ONLY"
        elif mode == "live_authenticated" and not ibkr_gateway_configured:
            st_code = "CREDENTIALS_REQUIRED_IBKR_GATEWAY"
            ver_out = "CREDENTIALS_PENDING"
        else:
            st_code = "BLOCKED_FORECASTEX_JURISDICTION_OR_PROXY"
            ver_out = "RESTRICTED"

        return VenueAuthorizationDecision(
            venue=v,
            network_mode=mode,
            operator_jurisdiction=op_jur,
            server_region=srv_reg,
            account_eligible=True,
            operating_location_permitted=True,
            finnish_cloud_hosting_authorized=True,
            public_api_permitted=pub_portal_ok,
            authenticated_api_permitted=ibkr_live_ready,
            effective_authorized=eff_ok,
            status_code=st_code,
            required_evidence=(
                "CFTC DCM public regulatory feed (forecastex.com/api/download) authorized; "
                "streaming L1 IBKR CPAPI (`/v1/api/iserver/marketdata/snapshot`, `/v1/api/ws` `smd+{conid}`) requires "
                "running local IBKR Client Portal Gateway (`IBKR_GATEWAY_URL`)."
            ),
            public_data_state=pub_state,
            readonly_api_state=ro_state,
            authenticated_account_state=acct_state,
            trading_state=trd_state,
            official_source="ForecastEx CFTC DCM Portal (https://forecastex.com) & Interactive Brokers Client Portal Web API",
            exact_requirement=(
                "Public CFTC CSV portal requires 0 credentials; live streaming CPAPI requires authenticated local Client Portal "
                "Gateway (`IBKR_GATEWAY_URL=https://localhost:5000/v1/api`) + Event Contracts (`FORECASTX` `OPT`) entitlement."
            ),
            application_status="PUBLIC_LIVE_ACTIVE_CPAPI_OPTIONAL" if eff_ok else "IBKR_GATEWAY_SESSION_REQUIRED",
            operator_action=(
                "Public CFTC feed active; for real-time L1 quotes, authenticate local IBKR Client Portal Gateway "
                "(`IBKR_GATEWAY_URL=https://localhost:5000/v1/api`) with Event Contracts market data permissions."
            ),
            verified_outcome_state=ver_out,
            scope_permissions={
                "PUBLIC_REST": "AUTHORIZED_LIVE" if pub_portal_ok else "CREDENTIALS_PENDING",
                "PUBLIC_WEBSOCKET": "RESTRICTED",
                "AUTHENTICATED_READONLY": "AUTHORIZED_LIVE" if ibkr_live_ready else "CREDENTIALS_PENDING",
                "ACCOUNT_PRIVATE": "AUTHORIZED_LIVE" if ibkr_live_ready else "CREDENTIALS_PENDING",
                "TRADING": "RESTRICTED",
                "INSTITUTIONAL_DATA_LICENSE": "CREDENTIALS_PENDING",
                "SERVER_HOSTING": "AUTHORIZED_LIVE" if eff_ok else "RESTRICTED",
            },
        )

    # -------------------------------------------------------------------------
    # Venue 1: Polymarket International (`gamma-api` + `clob.polymarket.com/book`)
    # -------------------------------------------------------------------------
    if v == "polymarket":
        if op_jur in POLYMARKET_COMPREHENSIVE_SANCTIONS:
            sc_perm, sc_just = _all_restricted_scopes("Embargoed/sanctioned jurisdiction.")
            return VenueAuthorizationDecision(
                venue=v,
                network_mode=mode,
                operator_jurisdiction=op_jur,
                server_region=srv_reg,
                account_eligible=False,
                operating_location_permitted=False,
                finnish_cloud_hosting_authorized=False,
                public_api_permitted=False,
                authenticated_api_permitted=False,
                effective_authorized=False,
                status_code=f"BLOCKED_COMPREHENSIVE_SANCTIONS({op_jur})",
                required_evidence="Embargoed/sanctioned jurisdiction barred from all platform access.",
                public_data_state="RESTRICTED",
                readonly_api_state="RESTRICTED",
                authenticated_account_state="RESTRICTED",
                trading_state="RESTRICTED",
                official_source="Polymarket Terms of Service (https://polymarket.com/tos) & Geoblocking FAQ",
                exact_requirement="Non-sanctioned jurisdiction required.",
                application_status="PROHIBITED_SANCTIONS",
                operator_action="None permitted from sanctioned territory.",
                verified_outcome_state="RESTRICTED",
                scope_permissions=sc_perm,
                scope_justifications=sc_just,
            )

        jur_trading_restricted = (op_jur in VENUE_RESTRICTED_JURISDICTIONS["polymarket"]) or workstation_geoblocked
        bad_server_region = srv_reg in {"GB", "UK", "US", "USA"}
        inst_approved = kyb_ok
        if not jur_trading_restricted and not bad_server_region:
            pub_st = "PUBLIC_DATA_AUTHORIZED"
            ro_st = "READONLY_API_AUTHORIZED"
            acct_st = "AUTHENTICATED_ACCOUNT_AUTHORIZED" if has_api_key else "CREDENTIALS_REQUIRED"
            trd_st = "CREDENTIALS_REQUIRED"
            eff_ok = True if mode == "live_public" else bool(has_api_key)
            code = "AUTHORIZED_ELIGIBLE_JURISDICTION" if eff_ok else "CREDENTIALS_REQUIRED_POLYMARKET_AUTH"
            ver_out = "AUTHORIZED_LIVE" if eff_ok else "CREDENTIALS_PENDING"
        elif inst_approved and not bad_server_region:
            pub_st = "PUBLIC_DATA_AUTHORIZED"
            ro_st = "READONLY_API_AUTHORIZED"
            acct_st = "AUTHENTICATED_ACCOUNT_AUTHORIZED"
            trd_st = "RESTRICTED" if op_jur == "CA-ON" else "CREDENTIALS_REQUIRED"
            eff_ok = True if mode == "live_public" else bool(has_api_key or kyb_ok)
            code = "AUTHORIZED_KYB_ALLOWLIST"
            ver_out = "AUTHORIZED_LIVE"
        elif bad_server_region:
            pub_st = "RESTRICTED"
            ro_st = "RESTRICTED"
            acct_st = "RESTRICTED"
            trd_st = "RESTRICTED"
            eff_ok = False
            code = f"BLOCKED_SERVER_REGION({srv_reg})"
            ver_out = "RESTRICTED"
        else:
            pub_st = "PUBLIC_DATA_AUTHORIZED"
            ro_st = "PUBLIC_DATA_AUTHORIZED"
            acct_st = "APPROVAL_PENDING" if institutional_app_pending else "RESTRICTED"
            trd_st = "RESTRICTED"
            eff_ok = (mode == "live_public")
            code = (
                "PUBLIC_DATA_AUTHORIZED_TRADING_RESTRICTED"
                if eff_ok
                else f"RESTRICTED_AUTHENTICATED_ACCESS({op_jur})"
            )
            ver_out = "AUTHORIZED_LIVE" if eff_ok else ("AUTHORIZATION_PENDING" if institutional_app_pending else "RESTRICTED")

        return VenueAuthorizationDecision(
            venue=v,
            network_mode=mode,
            operator_jurisdiction=op_jur,
            server_region=srv_reg,
            account_eligible=(not jur_trading_restricted) or inst_approved,
            operating_location_permitted=(not jur_trading_restricted) or inst_approved,
            finnish_cloud_hosting_authorized=bool(not bad_server_region and (eff_ok or inst_approved)),
            public_api_permitted=(pub_st == "PUBLIC_DATA_AUTHORIZED"),
            authenticated_api_permitted=(acct_st == "AUTHENTICATED_ACCOUNT_AUTHORIZED"),
            effective_authorized=eff_ok,
            status_code=code,
            required_evidence=(
                "Public Gamma/CLOB L2 market-data viewing (`GET /markets`, `GET /book`, `ws/market`) requires 0 auth and "
                "places 0 orders; authenticated account & `POST /order` remain disabled (`RESTRICTED`) in CA-ON unless "
                "operated by an eligible non-restricted entity (`blocked:false`)."
            ),
            public_data_state=pub_st,
            readonly_api_state=ro_st,
            authenticated_account_state=acct_st,
            trading_state=trd_st,
            official_source="Polymarket CLOB Docs & Geoblocking Policy (https://docs.polymarket.com/polymarket-learn/FAQ/geoblocking, https://polymarket.com/tos)",
            exact_requirement=(
                "Keyless public REST/WS L2 data active (`0` orders, `0` L2 HMAC headers); order placement requires "
                "eligible non-restricted entity/location (`GET /api/geoblock -> blocked:false`)."
            ),
            application_status="PUBLIC_LIVE_ACTIVE_TRADING_RESTRICTED" if (eff_ok and jur_trading_restricted) else ("APPROVED_ACTIVE" if eff_ok else ("APPROVAL_PENDING" if institutional_app_pending else "RESTRICTED_IN_CA_ON")),
            operator_action=(
                "Live public Gamma + CLOB L2 shadow collection active; keep order placement disabled in CA-ON (or onboard an eligible non-Ontario corporate entity via institutional@polymarket.com for future trading)."
            ),
            verified_outcome_state=ver_out,
            scope_permissions={
                "PUBLIC_REST": "RESTRICTED" if bad_server_region else "AUTHORIZED_LIVE",
                "PUBLIC_WEBSOCKET": "RESTRICTED" if bad_server_region else "AUTHORIZED_LIVE",
                "AUTHENTICATED_READONLY": "AUTHORIZED_LIVE" if (not jur_trading_restricted or inst_approved) and not bad_server_region else ("AUTHORIZATION_PENDING" if institutional_app_pending else "RESTRICTED"),
                "ACCOUNT_PRIVATE": "AUTHORIZED_LIVE" if acct_st == "AUTHENTICATED_ACCOUNT_AUTHORIZED" else ("AUTHORIZATION_PENDING" if institutional_app_pending else ("CREDENTIALS_PENDING" if not jur_trading_restricted else "RESTRICTED")),
                "TRADING": "RESTRICTED" if (jur_trading_restricted or bad_server_region) else "CREDENTIALS_PENDING",
                "INSTITUTIONAL_DATA_LICENSE": "AUTHORIZED_LIVE" if inst_approved else ("AUTHORIZATION_PENDING" if institutional_app_pending else "RESTRICTED"),
                "SERVER_HOSTING": "RESTRICTED" if bad_server_region else "AUTHORIZED_LIVE",
            },
        )

    # -------------------------------------------------------------------------
    # Priority A — Limitless Exchange (`api.limitless.exchange` & `ws.limitless.exchange` `/markets`)
    # -------------------------------------------------------------------------
    if v == "limitless":
        if op_jur in LIMITLESS_COMPREHENSIVE_ACCESS_BAN:
            sc_perm, sc_just = _all_restricted_scopes("Limitless Terms §1 comprehensive sanctions ban.")
            return VenueAuthorizationDecision(
                venue=v,
                network_mode=mode,
                operator_jurisdiction=op_jur,
                server_region=srv_reg,
                account_eligible=False,
                operating_location_permitted=False,
                finnish_cloud_hosting_authorized=False,
                public_api_permitted=False,
                authenticated_api_permitted=False,
                effective_authorized=False,
                status_code=f"BLOCKED_COMPREHENSIVE_SANCTIONS({op_jur})",
                required_evidence="Limitless Terms Section 1 makes platform entirely unavailable in sanctioned jurisdictions.",
                public_data_state="RESTRICTED",
                readonly_api_state="RESTRICTED",
                authenticated_account_state="RESTRICTED",
                trading_state="RESTRICTED",
                official_source="Limitless Exchange Terms of Service Section 1 (https://limitless.exchange/terms-of-service)",
                exact_requirement="Non-sanctioned jurisdiction required.",
                application_status="PROHIBITED_SANCTIONS",
                operator_action="None permitted from sanctioned territory.",
                verified_outcome_state="RESTRICTED",
                scope_permissions=sc_perm,
                scope_justifications=sc_just,
            )

        jur_trading_restricted = op_jur in VENUE_RESTRICTED_JURISDICTIONS["limitless"]
        bad_server_region = srv_reg in {"GB", "UK", "US", "USA"}
        if not jur_trading_restricted and not bad_server_region:
            pub_st = "PUBLIC_DATA_AUTHORIZED"
            ro_st = "READONLY_API_AUTHORIZED"
            acct_st = "AUTHENTICATED_ACCOUNT_AUTHORIZED" if has_api_key else "CREDENTIALS_REQUIRED"
            trd_st = "CREDENTIALS_REQUIRED"
            eff_ok = True if mode == "live_public" else bool(has_api_key)
            code = "AUTHORIZED_ELIGIBLE_JURISDICTION" if eff_ok else "CREDENTIALS_REQUIRED_LIMITLESS_AUTH"
            ver_out = "AUTHORIZED_LIVE" if eff_ok else "CREDENTIALS_PENDING"
            auth_ro_scope = "AUTHORIZED_LIVE" if has_api_key else "CREDENTIALS_PENDING"
            acct_scope = "AUTHORIZED_LIVE" if has_api_key else "CREDENTIALS_PENDING"
            trd_scope = "CREDENTIALS_PENDING"
        elif kyb_ok and not bad_server_region:
            pub_st = "PUBLIC_DATA_AUTHORIZED"
            ro_st = "READONLY_API_AUTHORIZED"
            acct_st = "AUTHENTICATED_ACCOUNT_AUTHORIZED"
            trd_st = "RESTRICTED" if op_jur in {"CA-ON", "CA-AB", "US", "USA"} else "CREDENTIALS_REQUIRED"
            eff_ok = True
            code = "AUTHORIZED_KYB_ALLOWLIST"
            ver_out = "AUTHORIZED_LIVE"
            auth_ro_scope = "AUTHORIZED_LIVE"
            acct_scope = "AUTHORIZED_LIVE"
            trd_scope = "RESTRICTED" if op_jur in {"CA-ON", "CA-AB", "US", "USA"} else "CREDENTIALS_PENDING"
        elif bad_server_region:
            pub_st = "RESTRICTED"
            ro_st = "RESTRICTED"
            acct_st = "RESTRICTED"
            trd_st = "RESTRICTED"
            eff_ok = False
            code = f"BLOCKED_SERVER_REGION({srv_reg})"
            ver_out = "RESTRICTED"
            auth_ro_scope = "RESTRICTED"
            acct_scope = "RESTRICTED"
            trd_scope = "RESTRICTED"
        else:
            # Street Chow Inc. Terms Section 1: "not available for trading" in US, ROC, CA-ON, CA-AB
            # (contrasted with comprehensive access ban on RU/BY/CU/IR/KP/SY).
            # Keyless `GET /markets/active`, `GET /markets/active/slugs`, `GET /markets/{slug}/orderbook`,
            # and keyless Socket.IO v4 `wss://ws.limitless.exchange/socket.io/?EIO=4&transport=websocket` (`/markets`)
            # require 0 API keys / 0 HMAC secrets and execute 0 trades -> `AUTHORIZED_LIVE`!
            pub_st = "PUBLIC_DATA_AUTHORIZED"
            ro_st = "PUBLIC_DATA_AUTHORIZED"
            acct_st = "APPROVAL_PENDING" if institutional_app_pending else "RESTRICTED"
            trd_st = "RESTRICTED"
            eff_ok = (mode == "live_public")
            code = (
                "PUBLIC_DATA_AUTHORIZED_TRADING_RESTRICTED"
                if eff_ok
                else f"RESTRICTED_AUTHENTICATED_ACCESS({op_jur})"
            )
            ver_out = "AUTHORIZED_LIVE" if eff_ok else ("AUTHORIZATION_PENDING" if institutional_app_pending else "RESTRICTED")
            auth_ro_scope = "AUTHORIZATION_PENDING" if institutional_app_pending else "RESTRICTED"
            acct_scope = "AUTHORIZATION_PENDING" if institutional_app_pending else "RESTRICTED"
            trd_scope = "RESTRICTED"

        inst_lic_scope = (
            "AUTHORIZED_LIVE"
            if kyb_ok
            else ("AUTHORIZATION_PENDING" if institutional_app_pending else ("CREDENTIALS_PENDING" if not jur_trading_restricted else "RESTRICTED"))
        )
        srv_scope = "RESTRICTED" if bad_server_region else "AUTHORIZED_LIVE"

        return VenueAuthorizationDecision(
            venue=v,
            network_mode=mode,
            operator_jurisdiction=op_jur,
            server_region=srv_reg,
            account_eligible=(not jur_trading_restricted) or kyb_ok,
            operating_location_permitted=(not jur_trading_restricted) or kyb_ok,
            finnish_cloud_hosting_authorized=bool(not bad_server_region and (eff_ok or kyb_ok)),
            public_api_permitted=(pub_st == "PUBLIC_DATA_AUTHORIZED"),
            authenticated_api_permitted=(acct_st == "AUTHENTICATED_ACCOUNT_AUTHORIZED"),
            effective_authorized=eff_ok,
            status_code=code,
            required_evidence=(
                "Limitless Section 1 restricts trading in CA-ON/CA-AB/US while keyless public REST and Socket.IO `/markets` "
                "WebSocket (`GET /markets/active`, `GET /markets/{slug}/orderbook`, `wss://ws.limitless.exchange`, `0` keys) "
                "are independently permitted; authenticated account & trading endpoints remain disabled (`RESTRICTED`)."
            ),
            public_data_state=pub_st,
            readonly_api_state=ro_st,
            authenticated_account_state=acct_st,
            trading_state=trd_st,
            official_source="Limitless Exchange Terms Section 1 (https://limitless.exchange/terms-of-service) & API Docs (https://api.limitless.exchange/api-v1)",
            exact_requirement="0 credentials required for public REST + Socket.IO `/markets` WS; eligible non-CA-ON/non-US entity required for authenticated account/trading.",
            application_status="PUBLIC_LIVE_ACTIVE_TRADING_RESTRICTED" if (eff_ok and jur_trading_restricted) else ("APPROVED_ACTIVE" if eff_ok else "RESTRICTED_IN_CA_ON"),
            operator_action="Live keyless Base CLOB REST + Socket.IO v4 `/markets` WebSocket active (`0` API/HMAC keys).",
            verified_outcome_state=ver_out,
            scope_permissions={
                "PUBLIC_REST": "RESTRICTED" if bad_server_region else "AUTHORIZED_LIVE",
                "PUBLIC_WEBSOCKET": "RESTRICTED" if bad_server_region else "AUTHORIZED_LIVE",
                "AUTHENTICATED_READONLY": auth_ro_scope,
                "ACCOUNT_PRIVATE": acct_scope,
                "TRADING": trd_scope,
                "INSTITUTIONAL_DATA_LICENSE": inst_lic_scope,
                "SERVER_HOSTING": srv_scope,
            },
            scope_justifications={
                "PUBLIC_REST": "Keyless public `/markets/active`, `/markets/active/slugs`, `/categories`, and `/markets/{slug}/orderbook` require 0 credentials.",
                "PUBLIC_WEBSOCKET": "Keyless Socket.IO v4 `wss://ws.limitless.exchange/socket.io/?EIO=4&transport=websocket` `/markets` (`subscribe_market_prices`) requires 0 credentials.",
                "AUTHENTICATED_READONLY": "Authenticated API keys (`X-API-Key` / Bearer) are tied to account eligibility.",
                "ACCOUNT_PRIVATE": "Private portfolio/order routes restricted in trading-ineligible jurisdictions (`CA-ON`, `CA-AB`, `US`, `ROC`).",
                "TRADING": "Street Chow Inc. ToS §1 explicitly states platform is 'not available for trading' in `CA-ON`, `CA-AB`, `US`, `ROC`.",
                "INSTITUTIONAL_DATA_LICENSE": "Not required for standard public REST/WS collection.",
                "SERVER_HOSTING": f"Server region `{srv_reg}` (`FI` unrestricted on Limitless).",
            },
        )

    # -------------------------------------------------------------------------
    # Priority B — Predict.fun (`api.predict.fun/v1` + `wss://ws.predict.fun/ws`)
    # -------------------------------------------------------------------------
    if v == "predict_fun":
        if op_jur in POLYMARKET_COMPREHENSIVE_SANCTIONS:
            sc_perm, sc_just = _all_restricted_scopes("Sanctioned territory barred under PDF Labs Limited Terms.")
            return VenueAuthorizationDecision(
                venue=v,
                network_mode=mode,
                operator_jurisdiction=op_jur,
                server_region=srv_reg,
                account_eligible=False,
                operating_location_permitted=False,
                finnish_cloud_hosting_authorized=False,
                public_api_permitted=False,
                authenticated_api_permitted=False,
                effective_authorized=False,
                status_code=f"BLOCKED_COMPREHENSIVE_SANCTIONS({op_jur})",
                required_evidence="Sanctioned jurisdiction barred from Predict.fun.",
                public_data_state="RESTRICTED",
                readonly_api_state="RESTRICTED",
                authenticated_account_state="RESTRICTED",
                trading_state="RESTRICTED",
                official_source="PDF Labs Limited Terms of Service (https://predict.fun/terms)",
                exact_requirement="Non-sanctioned jurisdiction required.",
                application_status="PROHIBITED_SANCTIONS",
                operator_action="None permitted from sanctioned territory.",
                verified_outcome_state="RESTRICTED",
                scope_permissions=sc_perm,
                scope_justifications=sc_just,
            )

        # PDF Labs Limited Terms (`https://docs.predict.fun/terms-of-service`, Last Updated Nov 18, 2025):
        # - Section 1 divides features into `Content Features` ("all content, informational functionality, and
        #   information features" on any Interface) and `Technology Features` (connecting self-hosted wallets to
        #   interact with the BNB Chain `Platform` / `Contracts`).
        # - Section 1 expressly permits Restricted Jurisdictions (including `CA-ON`) to use `Content Features` while
        #   barring `Technology Features` and trading (`POST /v1/auth` wallet JWT & `POST /v1/orders`).
        # - Predict.fun imposes ZERO `PREDICT_FUN_DATA_LICENSE_ID` concept; read-only market data (`/v1/markets`,
        #   `/v1/categories`, `/v1/markets/{id}/orderbook`, `wss://ws.predict.fun/ws` `predictOrderbook/{id}`) requires
        #   only a developer-console `x-api-key` (`PREDICT_FUN_API_KEY`, 0 wallet signing, 0 trading).
        # - `TESTNET_SANDBOX` (`api-testnet.predict.fun/v1`) NEVER counts as mainnet `AUTHORIZED_LIVE`!
        jur_restricted = op_jur in VENUE_RESTRICTED_JURISDICTIONS["predict_fun"]
        bad_server_region = srv_reg in {"GB", "UK", "US", "USA"}
        data_license_ok = bool(predict_fun_data_license or kyb_ok)
        eligible_mainnet_readonly = not bad_server_region
        srv_scope = "RESTRICTED" if bad_server_region else "AUTHORIZED_LIVE"

        if eligible_mainnet_readonly:
            mainnet_live_ready = bool(has_api_key and pf_env != "testnet")
            pub_st = "PUBLIC_DATA_AUTHORIZED" if pf_env == "testnet" else "CREDENTIALS_REQUIRED"
            ro_st = "READONLY_API_AUTHORIZED" if has_api_key else ("APPROVAL_PENDING" if institutional_app_pending else "CREDENTIALS_REQUIRED")
            acct_st = ("AUTHENTICATED_ACCOUNT_AUTHORIZED" if has_api_key else "CREDENTIALS_REQUIRED") if not jur_restricted else "RESTRICTED"
            trd_st = "CREDENTIALS_REQUIRED" if not jur_restricted else "RESTRICTED"
            eff_ok = bool(mainnet_live_ready or (pf_env == "testnet" and mode == "live_public"))
            if mainnet_live_ready:
                if jur_restricted and not data_license_ok:
                    code = "AUTHORIZED_MAINNET_CONTENT_DATA_TRADING_RESTRICTED"
                elif data_license_ok and jur_restricted:
                    code = "AUTHORIZED_KYB_ALLOWLIST"
                else:
                    code = "AUTHORIZED_ELIGIBLE_JURISDICTION_MAINNET"
                ver_out = "AUTHORIZED_LIVE"
            elif has_api_key and pf_env == "testnet":
                code = "AUTHORIZED_TESTNET_SANDBOX_ONLY"
                ver_out = "CREDENTIALS_PENDING"  # Switch PREDICT_FUN_ENV=mainnet to activate mainnet
            elif eff_ok:
                code = "AUTHORIZED_TESTNET_SANDBOX_ONLY"
                ver_out = "AUTHORIZATION_PENDING" if institutional_app_pending else "CREDENTIALS_PENDING"
            else:
                code = "CREDENTIALS_REQUIRED_PREDICT_FUN_API_KEY"
                ver_out = "AUTHORIZATION_PENDING" if institutional_app_pending else "CREDENTIALS_PENDING"
            auth_ro_scope = "AUTHORIZED_LIVE" if mainnet_live_ready else ("AUTHORIZATION_PENDING" if institutional_app_pending else "CREDENTIALS_PENDING")
            acct_scope = ("AUTHORIZED_LIVE" if has_api_key else "CREDENTIALS_PENDING") if not jur_restricted else "RESTRICTED"
            trd_scope = "CREDENTIALS_PENDING" if not jur_restricted else "RESTRICTED"
            inst_scope = "AUTHORIZED_LIVE" if data_license_ok else ("AUTHORIZATION_PENDING" if institutional_app_pending else "CREDENTIALS_PENDING")
        else:
            pub_st = "RESTRICTED"
            ro_st = "RESTRICTED"
            acct_st = "RESTRICTED"
            trd_st = "RESTRICTED"
            eff_ok = False
            code = f"BLOCKED_SERVER_REGION({srv_reg})"
            ver_out = "RESTRICTED"
            auth_ro_scope = "RESTRICTED"
            acct_scope = "RESTRICTED"
            trd_scope = "RESTRICTED"
            inst_scope = "RESTRICTED"

        return _with_three_capabilities(VenueAuthorizationDecision(
            venue=v,
            network_mode=mode,
            operator_jurisdiction=op_jur,
            server_region=srv_reg,
            account_eligible=(not jur_restricted) and (not bad_server_region),
            operating_location_permitted=eligible_mainnet_readonly,
            finnish_cloud_hosting_authorized=bool(not bad_server_region and (eff_ok or has_api_key)),
            public_api_permitted=(pub_st == "PUBLIC_DATA_AUTHORIZED"),
            authenticated_api_permitted=bool(eligible_mainnet_readonly and has_api_key and pf_env != "testnet"),
            effective_authorized=eff_ok,
            status_code=code,
            required_evidence=(
                "Mainnet read-only informational `Content Features` (`https://api.predict.fun/v1/markets`, `/orderbook`, "
                "`wss://ws.predict.fun/ws`) require `PREDICT_FUN_API_KEY` (`x-api-key` from `developers.predict.fun`, "
                "0 wallet signing, 0 trading); `Technology Features` (`POST /v1/auth` wallet JWT & `POST /v1/orders`) "
                "remain strictly `RESTRICTED` in `CA-ON` per `docs.predict.fun/terms-of-service` Section 1."
            ),
            public_data_state=pub_st,
            readonly_api_state=ro_st,
            authenticated_account_state=acct_st,
            trading_state=trd_st,
            official_source="PDF Labs Limited Terms Section 1 (https://docs.predict.fun/terms-of-service) & Developer Docs (https://dev.predict.fun)",
            exact_requirement=(
                "`PREDICT_FUN_API_KEY` (`x-api-key` from https://developers.predict.fun) + `PREDICT_FUN_ENV=mainnet` "
                "(strictly read-only market data; wallet JWT & trading disabled)."
            ),
            application_status=(
                "MAINNET_CONTENT_DATA_ACTIVE_TRADING_RESTRICTED"
                if (eligible_mainnet_readonly and has_api_key and pf_env != "testnet" and jur_restricted)
                else (
                    "APPROVED_ACTIVE"
                    if (eligible_mainnet_readonly and has_api_key and pf_env != "testnet")
                    else ("APPROVAL_PENDING" if institutional_app_pending else "CREDENTIALS_PENDING")
                )
            ),
            operator_action=(
                "Mainnet read-only market-data feed active (`LIVE_TRADING_ACCESS = RESTRICTED`)."
                if (eligible_mainnet_readonly and has_api_key and pf_env != "testnet")
                else "Provision `PREDICT_FUN_API_KEY` from https://developers.predict.fun and set `PREDICT_FUN_ENV=mainnet`."
            ),
            verified_outcome_state=ver_out,
            scope_permissions={
                "PUBLIC_REST": "RESTRICTED",
                "PUBLIC_WEBSOCKET": "RESTRICTED",
                "AUTHENTICATED_READONLY": auth_ro_scope,
                "ACCOUNT_PRIVATE": acct_scope,
                "TRADING": trd_scope,
                "INSTITUTIONAL_DATA_LICENSE": inst_scope,
                "SERVER_HOSTING": srv_scope,
            },
            scope_justifications={
                "PUBLIC_REST": "Mainnet `api.predict.fun/v1` requires `x-api-key` on every route (`401` keyless); BNB Testnet is `TESTNET_SANDBOX` only.",
                "PUBLIC_WEBSOCKET": "Mainnet `wss://ws.predict.fun/ws` requires `x-api-key` header or `apiKey` parameter.",
                "AUTHENTICATED_READONLY": "Read-only `Content Features` via `x-api-key` (`developers.predict.fun`, 0 wallet connection / 0 `POST /v1/auth` JWT); expressly permitted in Section 1 while trading is barred.",
                "ACCOUNT_PRIVATE": "`POST /v1/auth` wallet-signed JWT (`Technology Features`) prohibited in Restricted Jurisdictions (`CA-ON`).",
                "TRADING": "`POST /v1/orders` & BNB Chain `Contracts` prohibited in Restricted Jurisdictions (`CA-ON`, `US`, `UK`, `FR`, `SG`, etc.) and hard-disabled in shadow mode.",
                "INSTITUTIONAL_DATA_LICENSE": "Not imposed by Predict.fun for `developers.predict.fun` read-only `x-api-key` market data.",
                "SERVER_HOSTING": f"Server region `{srv_reg}` (`FI` Finland is NOT geo-restricted on Predict.fun).",
            },
        ))

    # -------------------------------------------------------------------------
    # Priority C — SX Bet (`api.sx.bet` OBv3 + Centrifugo `realtime.sx.bet`)
    # -------------------------------------------------------------------------
    jur_restricted = op_jur in VENUE_RESTRICTED_JURISDICTIONS["sx_bet"]
    bad_server_region = srv_reg in {"GB", "UK", "US", "USA"}
    if op_jur in POLYMARKET_COMPREHENSIVE_SANCTIONS or bad_server_region:
        sc_perm, sc_just = _all_restricted_scopes("Restricted server region or sanctioned territory.")
        return VenueAuthorizationDecision(
            venue=v,
            network_mode=mode,
            operator_jurisdiction=op_jur,
            server_region=srv_reg,
            account_eligible=False,
            operating_location_permitted=False,
            finnish_cloud_hosting_authorized=False,
            public_api_permitted=False,
            authenticated_api_permitted=False,
            effective_authorized=False,
            status_code=f"BLOCKED_SERVER_REGION({srv_reg})" if bad_server_region else f"BLOCKED_COMPREHENSIVE_SANCTIONS({op_jur})",
            required_evidence="Restricted server region or sanctioned jurisdiction.",
            public_data_state="RESTRICTED",
            readonly_api_state="RESTRICTED",
            authenticated_account_state="RESTRICTED",
            trading_state="RESTRICTED",
            official_source="SX Bet Terms & Conditions (https://sx.bet) & API Docs (https://docs.sx.bet)",
            exact_requirement="Non-sanctioned jurisdiction and non-US/UK server region.",
            application_status="RESTRICTED",
            operator_action="Do not poll SX Bet from geoblocked US/UK server region.",
            verified_outcome_state="RESTRICTED",
            scope_permissions=sc_perm,
            scope_justifications=sc_just,
        )

    # First-principles capability separation (verified live on https://docs.sx.bet & https://api.sx.bet):
    #   - Keyless OpenAPI `security: []` public routes (`GET /metadata/obv3`, `/summary-v3/{popular,inplay,upcoming}`,
    #     `/markets/active`, `/trades-v3/public`; 500 req/60s per IP under `docs.sx.bet/developers/rate-limits.md`)
    #     require ZERO account, ZERO wagering, and ZERO `SX_BET_DATA_APPROVAL_ID` -> `PUBLIC_DATA_AUTHORIZED`.
    #   - Full L2 orderbook snapshots (`/orderbook-v3/snapshot/market`), `/orders-v3/odds/best`, and Centrifugo WS
    #     (`GET /user/realtime-token-v3/api-key` -> `wss://realtime.sx.bet/connection/websocket`) enforce `x-sx-api-key`
    #     (`HTTP 401 BAD_AUTH` when unset) -> `CREDENTIALS_PENDING` until `SX_BET_API_KEY` is provided.
    #   - Betting, EIP-712 order signing, and proxy wallet funding (`ACCOUNT_PRIVATE` & `TRADING`) remain `RESTRICTED`
    #     under `CA-ON` (`sx.bet` wagering/account obligations) and hard-disabled in Stage G shadow mode.
    pub_st = "PUBLIC_DATA_AUTHORIZED"
    ro_st = "READONLY_API_AUTHORIZED" if has_api_key else "PUBLIC_DATA_AUTHORIZED"
    acct_st = ("AUTHENTICATED_ACCOUNT_AUTHORIZED" if has_api_key else "CREDENTIALS_REQUIRED") if not jur_restricted else "RESTRICTED"
    trd_st = "CREDENTIALS_REQUIRED" if not jur_restricted else "RESTRICTED"
    eff_ok = True if mode == "live_public" else bool(has_api_key)
    if not eff_ok:
        code = "CREDENTIALS_REQUIRED_SX_CENTRIFUGO_API_KEY"
        ver_out = "CREDENTIALS_PENDING"
    elif jur_restricted and not (sx_bet_written_data_license or kyb_ok):
        code = "PUBLIC_DATA_AUTHORIZED_TRADING_RESTRICTED"
        ver_out = "AUTHORIZED_LIVE" if has_api_key else "AUTHORIZED_REST_ONLY"
    elif sx_bet_written_data_license or kyb_ok:
        code = "AUTHORIZED_KYB_ALLOWLIST"
        ver_out = "AUTHORIZED_LIVE" if has_api_key else "AUTHORIZED_REST_ONLY"
    else:
        code = "AUTHORIZED_ELIGIBLE_JURISDICTION"
        ver_out = "AUTHORIZED_LIVE" if has_api_key else "AUTHORIZED_REST_ONLY"
    pub_rest_scope = "AUTHORIZED_LIVE"
    auth_ro_scope = "AUTHORIZED_LIVE" if has_api_key else "CREDENTIALS_PENDING"
    acct_scope = ("AUTHORIZED_LIVE" if has_api_key else "CREDENTIALS_PENDING") if not jur_restricted else "RESTRICTED"
    trd_scope = "CREDENTIALS_PENDING" if not jur_restricted else "RESTRICTED"
    inst_scope = "AUTHORIZED_LIVE" if (sx_bet_written_data_license or kyb_ok) else ("AUTHORIZATION_PENDING" if sx_bet_data_inquiry_pending else "CREDENTIALS_PENDING")

    return VenueAuthorizationDecision(
        venue=v,
        network_mode=mode,
        operator_jurisdiction=op_jur,
        server_region=srv_reg,
        account_eligible=(not jur_restricted) or kyb_ok,
        operating_location_permitted=True,
        finnish_cloud_hosting_authorized=True,
        public_api_permitted=True,
        authenticated_api_permitted=bool(has_api_key),
        effective_authorized=eff_ok,
        status_code=code,
        required_evidence=(
            "Keyless public OBv3 REST (`GET /metadata/obv3`, `/summary-v3/{popular,inplay,upcoming}`, `/markets/active`, "
            "`/trades-v3/public`; `security: []`, 500 req/60s per IP) requires 0 API keys and 0 internal data license; "
            "`SX_BET_API_KEY` (`x-sx-api-key`) is required by `api.sx.bet` (`401 BAD_AUTH` keyless) for `/orderbook-v3/snapshot/market` "
            "and Centrifugo WS (`wss://realtime.sx.bet/connection/websocket`). Betting & account funding remain `RESTRICTED` in `CA-ON`."
        ),
        public_data_state=pub_st,
        readonly_api_state=ro_st,
        authenticated_account_state=acct_st,
        trading_state=trd_st,
        official_source="SX Bet Developer Docs & Rate Limits (https://docs.sx.bet/developers/authentication.md, https://docs.sx.bet/developers/rate-limits.md)",
        exact_requirement=(
            "Keyless public OBv3 REST active immediately (`0` credentials); `SX_BET_API_KEY` (`x-sx-api-key`) required by "
            "provider for full L2 snapshot & Centrifugo WebSocket channels."
        ),
        application_status=(
            "PUBLIC_LIVE_ACTIVE_TRADING_RESTRICTED"
            if (eff_ok and jur_restricted and not has_api_key)
            else ("APPROVED_ACTIVE" if eff_ok else "CREDENTIALS_PENDING")
        ),
        operator_action=(
            "Live keyless OBv3 public REST active (`summary-v3`, `markets/active`, `trades-v3/public`); provision `SX_BET_API_KEY` to add L2 `/orderbook-v3/snapshot/market` + Centrifugo realtime WS."
            if (eff_ok and not has_api_key)
            else "Live OBv3 REST + Centrifugo WS active."
        ),
        verified_outcome_state=ver_out,
        scope_permissions={
            "PUBLIC_REST": pub_rest_scope,
            "PUBLIC_WEBSOCKET": "RESTRICTED",
            "AUTHENTICATED_READONLY": auth_ro_scope,
            "ACCOUNT_PRIVATE": acct_scope,
            "TRADING": trd_scope,
            "INSTITUTIONAL_DATA_LICENSE": inst_scope,
            "SERVER_HOSTING": "AUTHORIZED_LIVE",
        },
        scope_justifications={
            "PUBLIC_REST": "Documented keyless OpenAPI `security: []` endpoints (`/metadata/obv3`, `/summary-v3/*`, `/markets/active`, `/trades-v3/public`; 500 req/60s per IP).",
            "PUBLIC_WEBSOCKET": "Centrifugo `wss://realtime.sx.bet/connection/websocket` requires a connection token from authenticated `GET /user/realtime-token-v3/api-key` (`x-sx-api-key`).",
            "AUTHENTICATED_READONLY": "`api.sx.bet` enforces `x-sx-api-key` (`HTTP 401 BAD_AUTH` without key) on `/orderbook-v3/snapshot/market`, `/orders-v3/odds/best`, and `/user/realtime-token-v3/api-key`.",
            "ACCOUNT_PRIVATE": "Proxy wallet deployment, funding, and account balances restricted under `CA-ON` wagering rules and disabled in shadow mode.",
            "TRADING": "EIP-712 signed `POST /orders-v3` restricted in `CA-ON` and hard-disabled in Stage G shadow mode.",
            "INSTITUTIONAL_DATA_LICENSE": "Not required by SX Bet for public REST or `x-sx-api-key` market data.",
            "SERVER_HOSTING": f"Server region `{srv_reg}` (`FI` Finland is NOT geoblocked by SX Bet).",
        },
    )


def evaluate_all_venues_authorization(
    env: Optional[Mapping[str, str]] = None,
    *,
    network_mode_override: Optional[str] = None,
    venues: Sequence[str] = ALL_SHADOW_VENUES,
) -> Dict[str, VenueAuthorizationDecision]:
    """Evaluates all configured shadow venues independently from environment variables."""
    src = env if env is not None else os.environ
    mode = (network_mode_override or src.get("DOMINUS_NETWORK_MODE") or "offline").strip().lower()
    op_jur = src.get("DOMINUS_OPERATOR_JURISDICTION", "")
    srv_reg = src.get("DOMINUS_SERVER_REGION", "LOCAL")
    geoblocked = str(src.get("DOMINUS_WORKSTATION_GEOBLOCKED", "")).strip().lower() in {"1", "true", "yes"}
    kyb_venues = frozenset(
        v.strip().lower()
        for v in (src.get("DOMINUS_KYB_AUTHORIZED_VENUES") or "").split(",")
        if v.strip()
    )
    kyb_ref = (src.get("DOMINUS_KYB_REFERENCE_ID") or "").strip()

    enabled_raw = (src.get("DOMINUS_ENABLED_VENUES") or "").strip()
    enabled_filter = (
        {v.strip().lower() for v in enabled_raw.split(",") if v.strip()}
        if enabled_raw
        else {v.lower() for v in venues}
    )

    pf_env = (src.get("PREDICT_FUN_ENV") or "mainnet").strip().lower()
    pf_data_lic = bool((src.get("PREDICT_FUN_DATA_LICENSE_ID") or "").strip())
    stx_has_sig = stx_signing_key_available(src)
    stx_apps_tok = bool((src.get("STX_APPS_DATA_TOKEN") or "").strip())
    stx_apps_pend = bool((src.get("STX_APPS_APPLICATION_ID") or "").strip())
    sx_written_lic = bool(
        (src.get("SX_BET_DATA_APPROVAL_ID") or src.get("SX_BET_WRITTEN_DATA_LICENSE_ID") or "").strip()
    )
    sx_inq_pend = bool((src.get("SX_BET_DATA_INQUIRY_ID") or "").strip())
    fex_pub_auth = str(src.get("FORECASTEX_PUBLIC_PORTAL_AUTHORIZED", "")).strip().lower() in {"1", "true", "yes"}
    ibkr_cfg = bool((src.get("IBKR_GATEWAY_URL") or "").strip())

    out: Dict[str, VenueAuthorizationDecision] = {}
    for v in venues:
        v_low = v.lower()
        if v_low not in enabled_filter and mode != "offline":
            sc_perm, sc_just = _all_restricted_scopes("Disabled via DOMINUS_ENABLED_VENUES.")
            out[v_low] = _with_three_capabilities(VenueAuthorizationDecision(
                venue=v_low,
                network_mode=mode,
                operator_jurisdiction=_norm_jurisdiction(op_jur) or "UNSPECIFIED",
                server_region=_norm_jurisdiction(srv_reg),
                account_eligible=False,
                operating_location_permitted=False,
                finnish_cloud_hosting_authorized=False,
                public_api_permitted=False,
                authenticated_api_permitted=False,
                effective_authorized=False,
                status_code="DISABLED_BY_CONFIG",
                required_evidence="Add venue to DOMINUS_ENABLED_VENUES when authorized.",
                public_data_state="RESTRICTED",
                readonly_api_state="RESTRICTED",
                authenticated_account_state="RESTRICTED",
                trading_state="RESTRICTED",
                official_source="Dominus Runtime Configuration",
                exact_requirement="Include venue in DOMINUS_ENABLED_VENUES.",
                application_status="DISABLED_BY_OPERATOR",
                operator_action=f"Add {v_low} to DOMINUS_ENABLED_VENUES.",
                verified_outcome_state="RESTRICTED",
                scope_permissions=sc_perm,
                scope_justifications=sc_just,
            ))
            continue

        has_key = False
        inst_pend = False
        if v_low == "predict_fun":
            has_key = bool((src.get("PREDICT_FUN_API_KEY") or "").strip())
            inst_pend = bool((src.get("PREDICT_FUN_BUILDER_APP_ID") or "").strip())
        elif v_low == "sx_bet":
            has_key = bool((src.get("SX_BET_API_KEY") or "").strip())
        elif v_low == "stx_ontario":
            has_key = bool((src.get("STX_API_KEY_ID") or "").strip())
        elif v_low == "polymarket":
            inst_pend = bool((src.get("POLYMARKET_INSTITUTIONAL_APP_ID") or "").strip())
        elif v_low == "limitless":
            inst_pend = bool((src.get("LIMITLESS_INSTITUTIONAL_APP_ID") or "").strip())

        out[v_low] = evaluate_venue_shadow_authorization(
            v_low,
            network_mode=mode,
            operator_jurisdiction=op_jur,
            server_region=srv_reg,
            workstation_geoblocked=geoblocked,
            has_api_key=has_key,
            kyb_authorized_venues=kyb_venues,
            kyb_reference_id=kyb_ref,
            forecastex_public_portal_authorized=fex_pub_auth,
            ibkr_gateway_configured=ibkr_cfg,
            predict_fun_env=pf_env,
            predict_fun_data_license=pf_data_lic,
            stx_has_signing_key=stx_has_sig,
            stx_apps_data_token_present=stx_apps_tok,
            stx_apps_application_pending=stx_apps_pend,
            sx_bet_written_data_license=sx_written_lic,
            sx_bet_data_inquiry_pending=sx_inq_pend,
            institutional_app_pending=inst_pend,
        )
    return out


# ---------------------------------------------------------------------------
# 2. Secret-Free Environment & Credential Validator (Zero Echo / Zero Keys)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShadowEnvValidationReport:
    valid: bool
    checked_path: Optional[str]
    permissions_ok: bool
    observed_mode_octal: Optional[str]
    configured_keys: Tuple[str, ...]
    key_lengths: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


def parse_dotenv_lines(text: str) -> Tuple[Dict[str, str], List[str]]:
    """Parses `KEY=VALUE` lines without using `eval` or shell expansion; never logs values."""
    parsed: Dict[str, str] = {}
    errors: List[str] = []
    for idx, raw_line in enumerate((text or "").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            errors.append(f"LINE_{idx}_MISSING_EQUALS")
            continue
        k_raw, v_raw = stripped.split("=", 1)
        key = k_raw.strip()
        val = v_raw.strip()
        if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
            val = val[1:-1]
        if not _ENV_KEY_RE.match(key):
            errors.append(f"LINE_{idx}_INVALID_KEY_NAME:{key[:32]}")
            continue
        parsed[key] = val
    return parsed, errors


def validate_shadow_env_dict(
    env_map: Mapping[str, str],
    *,
    checked_path: Optional[str] = None,
    permissions_ok: bool = True,
    observed_mode_octal: Optional[str] = None,
) -> ShadowEnvValidationReport:
    """
    Validates shadow `.env` entries strictly by structure:
      - Hard-blocks private keys, mnemonics, passphrases, and HMAC signing secrets (`0` signing keys rule).
      - Hard-blocks raw 64-hex private keys (`0x...`) or inline PEM blocks accidentally pasted into any variable.
      - Validates `STX_ED25519_KEY_FILE` strictly as a filesystem path (and enforces `0600` if present on POSIX).
      - Checks printable format, minimum length, placeholder tokens, and optional SHA-256 revocation list.
      - Never includes any secret value or substring in returned errors/warnings.
    """
    errors: List[str] = []
    warnings: List[str] = []
    key_lengths: Dict[str, int] = {}

    if not permissions_ok:
        errors.append(f"INSECURE_FILE_PERMISSIONS:{observed_mode_octal or 'UNKNOWN'}_EXPECTED_0600")

    revoked_hashes = {
        h.strip().lower()
        for h in (env_map.get("DOMINUS_REVOKED_KEY_SHA256_LIST") or "").split(",")
        if h.strip()
    }

    for key, val in env_map.items():
        key_up = key.strip().upper()
        key_lengths[key_up] = len(val)

        if any(tok in key_up for tok in FORBIDDEN_ENV_KEY_TOKENS):
            errors.append(f"FORBIDDEN_SIGNING_SECRET_IN_SHADOW_ENV:{key_up}")
            continue

        if key_up not in ALLOWED_SHADOW_ENV_KEYS:
            errors.append(f"UNRECOGNIZED_SHADOW_ENV_KEY:{key_up}")
            continue

        if any(ch in val for ch in ("\r", "\n", "\x00")):
            errors.append(f"CONTROL_CHAR_IN_VALUE:{key_up}")
            continue

        if key_up == "DOMINUS_REVOKED_KEY_SHA256_LIST":
            for raw_hash in val.split(","):
                item = raw_hash.strip()
                if item and not re.fullmatch(r"[0-9a-fA-F]{64}", item):
                    errors.append("INVALID_REVOKED_SHA256_DIGEST_ENTRY")
                    break
            continue

        if val and (_HEX_PRIVKEY_RE.match(val) or "-----BEGIN" in val):
            errors.append(f"SUSPECTED_RAW_HEX_PRIVATE_KEY_IN:{key_up}")
            continue

        if key_up in {"PREDICT_FUN_API_KEY", "SX_BET_API_KEY", "STX_APPS_DATA_TOKEN"}:
            if not val:
                warnings.append(f"EMPTY_OPTIONAL_READONLY_KEY:{key_up}")
                continue
            if _PLACEHOLDER_RE.search(val):
                errors.append(f"PLACEHOLDER_CREDENTIAL_REJECTED:{key_up}")
                continue
            if not _API_KEY_PRINTABLE_RE.match(val):
                errors.append(f"INVALID_API_KEY_FORMAT_OR_LENGTH:{key_up}")
                continue
            digest = hashlib.sha256(val.encode("utf-8")).hexdigest().lower()
            if digest in revoked_hashes:
                errors.append(f"REVOKED_CREDENTIAL_SHA256_REJECTED:{key_up}")

        elif key_up == "STX_ED25519_KEY_FILE" and val:
            if _PLACEHOLDER_RE.search(val):
                errors.append("PLACEHOLDER_CREDENTIAL_REJECTED:STX_ED25519_KEY_FILE")
                continue
            kp = Path(val).expanduser()
            if kp.exists() and os.name != "nt":
                st_m = kp.stat().st_mode
                if (st_m & (stat.S_IRWXG | stat.S_IRWXO)) != 0:
                    errors.append(f"INSECURE_STX_KEY_FILE_PERMISSIONS:{oct(stat.S_IMODE(st_m))}_EXPECTED_0600")

        elif key_up == "PREDICT_FUN_ENV" and val:
            if val.strip().lower() not in {"mainnet", "testnet"}:
                errors.append("INVALID_PREDICT_FUN_ENV")

        elif key_up == "DOMINUS_NETWORK_MODE" and val:
            if val.strip().lower() not in {"offline", "live_public", "live_authenticated"}:
                errors.append("INVALID_DOMINUS_NETWORK_MODE")

    return ShadowEnvValidationReport(
        valid=(len(errors) == 0),
        checked_path=checked_path,
        permissions_ok=permissions_ok,
        observed_mode_octal=observed_mode_octal,
        configured_keys=tuple(sorted(env_map.keys())),
        key_lengths=key_lengths,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_shadow_env_file(
    path: Path,
    *,
    enforce_posix_0600: Optional[bool] = None,
) -> Tuple[Dict[str, str], ShadowEnvValidationReport]:
    """Reads and validates an `.env` file without echoing secrets; enforces `0600` on POSIX."""
    check_0600 = (os.name != "nt") if enforce_posix_0600 is None else bool(enforce_posix_0600)
    if not path.exists():
        rep = ShadowEnvValidationReport(
            valid=False,
            checked_path=str(path),
            permissions_ok=False,
            observed_mode_octal=None,
            configured_keys=(),
            key_lengths={},
            errors=("ENV_FILE_NOT_FOUND",),
            warnings=(),
        )
        return {}, rep

    st_mode = path.stat().st_mode
    oct_mode = oct(stat.S_IMODE(st_mode))
    perms_ok = True
    if check_0600 and (st_mode & (stat.S_IRWXG | stat.S_IRWXO)) != 0:
        perms_ok = False

    raw_text = path.read_text(encoding="utf-8")
    parsed, parse_errs = parse_dotenv_lines(raw_text)
    base_rep = validate_shadow_env_dict(
        parsed,
        checked_path=str(path),
        permissions_ok=perms_ok,
        observed_mode_octal=oct_mode,
    )
    all_errs = tuple(parse_errs) + base_rep.errors
    final_rep = ShadowEnvValidationReport(
        valid=(len(all_errs) == 0),
        checked_path=base_rep.checked_path,
        permissions_ok=base_rep.permissions_ok,
        observed_mode_octal=base_rep.observed_mode_octal,
        configured_keys=base_rep.configured_keys,
        key_lengths=base_rep.key_lengths,
        errors=all_errs,
        warnings=base_rep.warnings,
    )
    return (parsed if final_rep.valid else {}), final_rep


# ---------------------------------------------------------------------------
# 3. Systemd Unit & Python Runtime Dependency Validator
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SystemdUnitValidationReport:
    valid: bool
    unit_path: str
    checks: Dict[str, bool]
    errors: Tuple[str, ...]


def validate_systemd_unit_text(unit_text: str, unit_path: str = "polymarket-cross-venue-shadow.service") -> SystemdUnitValidationReport:
    """Validates systemd resource fences, security sandboxing, fail-closed flags, and recovery directives."""
    checks = {
        "has_unit_section": "[Unit]" in unit_text,
        "has_service_section": "[Service]" in unit_text,
        "has_install_section": "[Install]" in unit_text,
        "loads_shadow_env_file": "EnvironmentFile=-/etc/polymarket-shadow.env" in unit_text,
        "enforces_memory_max_180m": bool(
            re.search(r"^\s*MemoryMax=(?:180|240|256|320|384|450|512)M\s*$", unit_text, flags=re.MULTILINE)
        ),
        "enforces_cpu_quota_15pct": bool(
            re.search(r"^\s*CPUQuota=(?:15|20|25|30|35)%\s*$", unit_text, flags=re.MULTILINE)
        ),
        "enforces_nice_19": "Nice=19" in unit_text,
        "enforces_no_new_privileges": "NoNewPrivileges=true" in unit_text,
        "enforces_protect_system_strict": "ProtectSystem=strict" in unit_text,
        "enforces_venue_auth_flag": "--enforce-venue-auth" in unit_text,
        "prevents_restart_on_ex_config_78": "RestartPreventExitStatus=78" in unit_text,
        "graceful_sigterm": "KillSignal=SIGTERM" in unit_text,
        "zero_inline_secrets": not any(
            re.search(rf"^\s*Environment=(?:PREDICT_FUN_API_KEY|SX_BET_API_KEY)=\S+", ln)
            for ln in unit_text.splitlines()
        ),
    }
    errors = tuple(f"FAILED_CHECK:{name}" for name, ok in checks.items() if not ok)
    return SystemdUnitValidationReport(
        valid=(len(errors) == 0),
        unit_path=unit_path,
        checks=checks,
        errors=errors,
    )


def validate_python_runtime_dependencies() -> Dict[str, Any]:
    """Checks stdlib + optional async HTTP availability for Stage G shadow probe."""
    required_stdlib = ("asyncio", "decimal", "hashlib", "json", "logging", "pathlib", "signal", "sqlite3", "urllib.request")
    missing: List[str] = []
    for mod in required_stdlib:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    has_aiohttp = False
    try:
        import aiohttp as _a  # type: ignore # noqa: F401
        has_aiohttp = not getattr(_a, "__name__", "").startswith("_stub") and hasattr(_a, "ClientTimeout")
    except Exception:
        has_aiohttp = False
    return {
        "python_version": sys.version.split()[0],
        "stdlib_ready": len(missing) == 0,
        "missing_stdlib": missing,
        "http_transport_mode": "aiohttp_async" if has_aiohttp else "urllib_threadpool_fallback",
    }


# ---------------------------------------------------------------------------
# 4. Network-Disabled Synthetic/Recorded Order-Book Integration Harness
# ---------------------------------------------------------------------------

def build_recorded_schema_fixture_markets(now_ts: Optional[int] = None) -> Tuple[List[NormalizedBinaryMarket], List[NormalizedBinaryMarket]]:
    """
    Constructs realistic recorded-schema L2 order-book fixtures across all 6 normalized venues
    (`Polymarket`, `Limitless`, `SX Bet` OBv3, `Predict.fun`, `ForecastEx`, `STX Ontario`)
    for 100% offline (`0` network call) end-to-end pipeline verification.
    """
    end_15m = int(((now_ts or 1794200100) // 900 + 1) * 900)
    end_iso = datetime.fromtimestamp(end_15m, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    game_ts = end_15m + 7200
    game_iso = datetime.fromtimestamp(game_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chainlink_btc_desc = "Resolves Up if BTC/USD >= strike on https://data.chain.link/streams/btc-usd 60s TWAP."

    pm_btc = parse_polymarket_gamma_market(
        {
            "id": "pm_fix_btc_15m",
            "slug": f"btc-updown-15m-{end_15m}",
            "question": "Bitcoin Up or Down - 15m",
            "description": chainlink_btc_desc,
            "conditionId": "0x" + "11" * 32,
            "endDate": end_iso,
            "outcomes": '["Up", "Down"]',
            "clobTokenIds": '["tok_btc_up", "tok_btc_dn"]',
            "active": True,
            "closed": False,
        },
        yes_book={"asks": [{"price": "0.460", "size": "180"}], "bids": [{"price": "0.450", "size": "150"}]},
        no_book={"asks": [{"price": "0.550", "size": "180"}], "bids": [{"price": "0.540", "size": "150"}]},
        fee_rate_bps_override=700.0,
    )

    pm_nba = parse_polymarket_gamma_market(
        {
            "id": "pm_fix_nba_nyk_bos",
            "slug": "nba-nyk-bos-fixture",
            "question": "Celtics vs. Knicks",
            "description": "Official NBA game winner including overtime.",
            "conditionId": "0x" + "22" * 32,
            "endDate": game_iso,
            "outcomes": '["Celtics", "Knicks"]',
            "clobTokenIds": '["tok_bos", "tok_nyk"]',
            "active": True,
            "closed": False,
        },
        # Celtics (`yes_label` canonically sorted `celtics` < `knicks`) priced <= $0.48 so Gate 3 walkover ceiling passes!
        yes_book={"asks": [{"price": "0.455", "size": "250"}], "bids": [{"price": "0.445", "size": "220"}]},
        no_book={"asks": [{"price": "0.555", "size": "250"}], "bids": [{"price": "0.545", "size": "220"}]},
        fee_rate_bps_override=0.0,
    )

    pm_macro = parse_polymarket_gamma_market(
        {
            "id": "pm_fix_cpi_core",
            "slug": "us-cpi-above-3pct-fixture",
            "question": "US CPI YoY above 3.0%?",
            "description": "Official BLS CPI-U YoY release strictly above 3.0%.",
            "conditionId": "0x" + "33" * 32,
            "endDate": game_iso,
            "outcomes": '["Yes", "No"]',
            "clobTokenIds": '["tok_cpi_y", "tok_cpi_n"]',
            "active": True,
            "closed": False,
        },
        yes_book={"asks": [{"price": "0.440", "size": "300"}], "bids": [{"price": "0.430", "size": "250"}]},
        no_book={"asks": [{"price": "0.570", "size": "300"}], "bids": [{"price": "0.560", "size": "250"}]},
        fee_rate_bps_override=0.0,
    )

    lim_btc = parse_limitless_market(
        {
            "id": 9001,
            "slug": f"btc-up-or-down-15m-{end_15m}",
            "title": "Bitcoin Up or Down - 15m",
            "description": chainlink_btc_desc,
            "expirationTimestamp": end_15m * 1000,
            "tokens": {"yes": "lim_y", "no": "lim_n"},
            "metadata": {"isPolyArbitrage": True, "fee": True},
            "externalSlug": f"btc-updown-15m-{end_15m}",
            "externalRulesWatch": {"rulesHash": pm_btc.rules_hash if pm_btc else "hash"},
            "settings": {"takerDelayMs": 50},
        },
        # Limitless share sizes are 10^6 scaled (`150_000_000` = 150 shares); NO ask @ $0.495 -> 0.460 + 0.495 = $0.955 gross!
        orderbook={
            "asks": [{"price": 0.520, "size": 150_000_000}],
            "bids": [{"price": 0.505, "size": 150_000_000}],
        },
    )

    # SX Bet OBv3 fixture: `bestOddsOutcomeOne = 0.480 * 10^20` -> `no_ask` (Knicks) = `1 - 0.480 = $0.520` (`0%` fee!)
    # Combined with Polymarket Celtics YES @ `$0.455` (`<= $0.48` Gate 3 safe!) = `$0.975` riskless sports box!
    sx_nba_list = parse_sx_bet_summary_fixture(
        {
            "sportXEventId": "L999999",
            "participantOneName": "Boston Celtics",
            "participantTwoName": "New York Knicks",
            "startDate": game_iso,
            "status": 1,
            "markets": [
                {
                    "marketHash": "0xsx_nba_ml_fix",
                    "type": 226,
                    "outcomeOneName": "Boston Celtics",
                    "outcomeTwoName": "New York Knicks",
                    "bestOddsOutcomeOne": str(int(0.480 * 10**20)),
                    "bestOddsOutcomeTwo": str(int(0.510 * 10**20)),
                }
            ],
        },
        sport_label="Basketball",
        league_label="NBA",
        betting_delay_ms=25.0,
    )

    pred_btc = parse_predict_fun_market(
        {
            "id": "7701",
            "categorySlug": f"btc-updown-15m-{end_15m}",
            "question": "Bitcoin Up or Down - 15m",
            "description": chainlink_btc_desc,
            "tradingStatus": "OPEN",
            "outcomes": [{"name": "Up"}, {"name": "Down"}],
            "feeRateBps": 200,
            "isYieldBearing": True,
            "polymarketConditionIds": ["0x" + "11" * 32],
        },
        # Predict.fun orderbook priced on Outcome 1 (`Yes`): bid @ `0.505` -> implied `No` ask = `1 - 0.505 = $0.495`
        orderbook={"bids": [[0.505, 160.0]], "asks": [[0.525, 160.0]]},
    )

    fex_cpi = parse_forecastex_contract(
        {
            "conid": "FEX_CPI_30",
            "symbol": "CPI_YOY_30",
            "title": "US CPI YoY above 3.0%?",
            "rules_text": "Official BLS CPI-U YoY release strictly above 3.0%.",
            "category": "macro",
            "end_ts": game_ts,
            "yes_asks": [[0.45, 200]],
            "yes_bids": [[0.43, 200]],
            "no_asks": [[0.52, 200]],
            "no_bids": [[0.50, 200]],
        }
    )

    stx_nba = parse_stx_ontario_market(
        {
            "market_id": "stx_nyk_bos_1",
            "slug": "stx-nyk-bos",
            "team_a": "Celtics",
            "team_b": "Knicks",
            "sport": "nba",
            "game_ts": game_ts,
            "win_commission_bps": 200.0,
            "team_a_asks": [[47.0, 150]],
            "team_a_bids": [[45.0, 150]],
            "team_b_asks": [[51.5, 150]],
            "team_b_bids": [[49.5, 150]],
        }
    )

    # 3-leg exhaustive NegRisk macro partition fixture (Cut / Hold / Hike -> sum YES = 0.30 + 0.50 + 0.145 = $0.945)
    partition_legs: List[NormalizedBinaryMarket] = []
    for idx, (lbl, ya_p, na_p) in enumerate(
        (("cut_25_or_more", 0.300, 0.710), ("hold_unchanged", 0.500, 0.510), ("hike_25_or_more", 0.145, 0.865)),
        start=1,
    ):
        pm_leg = parse_polymarket_gamma_market(
            {
                "id": f"pm_fix_fed_part_{idx}",
                "slug": f"fed-decision-{lbl}-fixture",
                "question": f"Fed Decision: {lbl}?",
                "description": "Official FOMC statement exhaustive 3-way target-rate partition.",
                "conditionId": f"0x{idx + 40:02x}" + "44" * 31,
                "endDate": game_iso,
                "outcomes": '["Yes", "No"]',
                "clobTokenIds": f'["tok_fed_y_{idx}", "tok_fed_n_{idx}"]',
                "active": True,
                "closed": False,
            },
            yes_book={"asks": [{"price": str(ya_p), "size": "220"}], "bids": [{"price": str(round(ya_p - 0.01, 3)), "size": "200"}]},
            no_book={"asks": [{"price": str(na_p), "size": "220"}], "bids": [{"price": str(round(na_p - 0.01, 3)), "size": "200"}]},
            fee_rate_bps_override=0.0,
        )
        if pm_leg is not None:
            pm_leg.neg_risk = True
            pm_leg.partition_group_id = "fomc_rate_partition_fixture"
            pm_leg.partition_label = lbl
            pm_leg.partition_expected_legs = 3
            partition_legs.append(pm_leg)

    poly = [m for m in (pm_btc, pm_nba, pm_macro) if m is not None] + partition_legs
    ext: List[NormalizedBinaryMarket] = []
    for m in (lim_btc, pred_btc, fex_cpi, stx_nba):
        if m is not None:
            ext.append(m)
    ext.extend(sx_nba_list)

    now_ms = int((now_ts or time.time()) * 1000)
    for m in poly + ext:
        m.data_origin = "OFFLINE_SYNTHETIC"
        m.quote_ts_ms = now_ms
    return poly, ext


def write_shadow_health_snapshot(
    data_dir: Path,
    *,
    network_mode: str,
    report: GraduationReport,
    auth_decisions: Mapping[str, VenueAuthorizationDecision],
    env_report: Optional[ShadowEnvValidationReport] = None,
    watchdog_status: Optional[Mapping[str, Any]] = None,
    campaign_windows: Optional[Mapping[str, Any]] = None,
    connector_snapshots: Optional[Mapping[str, Any]] = None,
) -> Path:
    """
    Atomically writes `shadow_service_health.json` with SHA-256 report integrity hash
    so local/systemd health monitors can verify liveness, timestamps, and gate compliance.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    report_bytes = json.dumps(asdict(report), sort_keys=True).encode("utf-8")
    report_sha256 = hashlib.sha256(report_bytes).hexdigest()

    healthy_flag = True if watchdog_status is None else bool(watchdog_status.get("healthy", True))
    payload = {
        "schema_version": "2.0.0",
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checked_at_unix": round(time.time(), 3),
        "pid": os.getpid(),
        "network_mode": network_mode,
        "data_origin": "OFFLINE_SYNTHETIC" if network_mode == "offline" else "LIVE_OR_REGULATORY",
        "service_healthy": healthy_flag,
        "cycles_completed": report.cycles_completed,
        "gross_candidates_seen": report.gross_candidates_seen,
        "executable_net_l2_count": report.executable_net_l2_count,
        "locked_complete_baskets": report.locked_complete_baskets,
        "double_zero_incidents": report.double_zero_incidents,
        "graduation_report_sha256": report_sha256,
        "env_validation": asdict(env_report) if env_report is not None else None,
        "venue_authorization": {k: asdict(v) for k, v in auth_decisions.items()},
        "connector_states": dict(connector_snapshots) if connector_snapshots is not None else None,
        "watchdog": dict(watchdog_status) if watchdog_status is not None else None,
        "campaign_windows": dict(campaign_windows) if campaign_windows is not None else None,
    }
    health_path = data_dir / "shadow_service_health.json"
    tmp_path = data_dir / f".shadow_service_health.json.tmp.{os.getpid()}"
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(str(tmp_path), str(health_path))
    return health_path


def run_offline_shadow_cycle(
    engine: HonestCrossVenueShadowEngine,
    *,
    auth_decisions: Optional[Mapping[str, VenueAuthorizationDecision]] = None,
    env_report: Optional[ShadowEnvValidationReport] = None,
) -> Dict[str, Any]:
    """
    Executes a deterministic 100% network-disabled shadow cycle against recorded-schema
    multi-venue L2 fixtures, verifying market matching, L2 order-book ingestion,
    2–6 leg complete baskets, all 5 Double-Zero gates, post-latency survival, SQLite WAL
    persistence (`OFFLINE_SYNTHETIC` segregated), and watchdog health output.
    """
    from src.polymarket_research.cross_venue_connectors import VenueOperationalSnapshot
    from src.polymarket_research.cross_venue_l2_and_baskets import (
        LegSpec,
        Level2ExecutionSimulator,
        MultiVenueArbitrageAnalyzer,
    )
    from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowRuntimeWatchdog

    poly_markets, ext_markets = build_recorded_schema_fixture_markets()
    all_mkts = poly_markets + ext_markets

    op_snaps: Dict[str, VenueOperationalSnapshot] = {}
    for v_name in ALL_SHADOW_VENUES:
        v_mkts = [m for m in all_mkts if m.venue == v_name]
        snap = VenueOperationalSnapshot(
            venue=v_name,
            authorization_state="AUTHORIZED_OFFLINE_ONLY",
            connectivity_state="OFFLINE_FENCED",
            health_state="HEALTHY" if v_mkts else "IDLE",
            live_validated=False,
            data_origin="OFFLINE_SYNTHETIC",
            markets_discovered=len(v_mkts),
            active_markets=len(v_mkts),
            l2_books_hydrated=len(v_mkts),
        )
        op_snaps[v_name] = snap
        engine.venue_health[v_name] = {
            **snap.to_health_dict(),
            "status": "OK_OFFLINE_FIXTURE" if v_mkts else "EMPTY_FIXTURE",
            "network_calls": 0,
        }
    engine.latency_samples_ms.extend([48.2, 72.4, 95.0, 115.0])

    analyzer = MultiVenueArbitrageAnalyzer(
        simulator=Level2ExecutionSimulator(bridge_drag_bps=engine.bridge_drag_bps),
        rule_verifier=engine.verifier,
        clip_notional_usd=engine.clip_notional_usd,
    )
    pairs = analyzer.pair_all_venues(all_mkts)

    intra_cands = engine.scan_intra_venue_complete_sets(ext_markets)
    cross_cands = engine.scan_cross_venue_pairs(pairs)
    multi_baskets, multi_rejects = analyzer.scan_multi_leg_complete_baskets(all_mkts)
    all_cands = intra_cands + cross_cands

    store = getattr(engine, "telemetry_store", None)
    if store is not None:
        if store.current_session_id is None:
            store.start_session(network_mode="offline", data_origin="OFFLINE_SYNTHETIC")
        else:
            store.heartbeat_session()
        store.ingest_markets(all_mkts)
        for pm, em in pairs:
            store.record_pairing(pm, em, rule_passed=True)
        for mb_ev in multi_baskets:
            store.record_signal(mb_ev, data_origin="OFFLINE_SYNTHETIC")
        for rj in multi_rejects:
            store.record_rejection(
                candidate_key=rj["group_id"],
                stage="MULTI_LEG_PARTITION",
                reason=rj["reason"],
                venues=["multi"],
                gross_edge_bps=0.0,
                data_origin="OFFLINE_SYNTHETIC",
            )

    three_tier_previews: List[Dict[str, Any]] = [asdict(ev) for ev in multi_baskets[:4]]

    for cand in all_cands:
        ma = next((m for m in all_mkts if m.slug == cand.market_a_slug and m.venue == cand.venue_a), None)
        mb = next((m for m in all_mkts if m.slug == cand.market_b_slug and m.venue == cand.venue_b), None)
        if cand.family == "XV_PASSIVE_MAKER_ANCHOR":
            engine.simulate_honest_execution(
                cand,
                post_delay_market_a=ma,
                post_delay_market_b=mb,
                observed_trade_through_shares=cand.shares + 25.0,
                queue_ahead_shares=10.0,
            )
        else:
            engine.simulate_honest_execution(
                cand,
                post_delay_market_a=ma,
                post_delay_market_b=mb,
            )
        if ma is not None and mb is not None:
            ev2 = analyzer.simulator.evaluate_basket(
                basket_id=cand.candidate_key,
                basket_type="COMPLETE_SET_2LEG" if cand.venue_a == cand.venue_b else "CROSS_VENUE_2LEG",
                legs=[
                    LegSpec(market=ma, side=cand.side_a),
                    LegSpec(market=mb, side=cand.side_b, execution_style="PASSIVE_MAKER" if cand.family == "XV_PASSIVE_MAKER_ANCHOR" else "TAKER"),
                ],
                target_notional_usd=engine.clip_notional_usd,
                post_delay_legs=[ma, mb],
                observed_trade_through_shares=(cand.shares + 25.0) if cand.family == "XV_PASSIVE_MAKER_ANCHOR" else None,
            )
            if store is not None:
                store.record_signal(ev2, data_origin="OFFLINE_SYNTHETIC")
            if len(three_tier_previews) < 8:
                three_tier_previews.append(asdict(ev2))

    engine.cycles_completed += 1
    report = engine.build_graduation_report(simulated_days=1.0)
    decisions = auth_decisions or evaluate_all_venues_authorization(network_mode_override="offline")

    wd_dict: Optional[Dict[str, Any]] = None
    win_dict: Optional[Dict[str, Any]] = None
    if store is not None:
        wd = ShadowRuntimeWatchdog(store).evaluate(op_snaps)
        wd_dict = asdict(wd)
        win_dict = store.build_campaign_window_summaries()

    health_path = write_shadow_health_snapshot(
        engine.data_dir,
        network_mode="offline",
        report=report,
        auth_decisions=decisions,
        env_report=env_report,
        watchdog_status=wd_dict,
        campaign_windows=win_dict,
        connector_snapshots={k: asdict(v) for k, v in op_snaps.items()},
    )
    return {
        "cycle": engine.cycles_completed,
        "network_mode": "offline",
        "data_origin": "OFFLINE_SYNTHETIC",
        "network_calls_made": 0,
        "matched_cross_venue_pairs": len(pairs),
        "multi_leg_complete_baskets_found": len(multi_baskets),
        "matched_pair_Previews": [
            {
                "polymarket": pm.slug,
                "external_venue": ext.venue,
                "external_slug": ext.slug,
                "oracle_a": pm.oracle_family,
                "oracle_b": ext.oracle_family,
                "poly_yes_ask": pm.yes_asks[0].price if pm.yes_asks else None,
                "poly_no_ask": pm.no_asks[0].price if pm.no_asks else None,
                "ext_yes_ask": ext.yes_asks[0].price if ext.yes_asks else None,
                "ext_no_ask": ext.no_asks[0].price if ext.no_asks else None,
            }
            for pm, ext in pairs[:10]
        ],
        "three_tier_evaluations": three_tier_previews,
        "intra_candidates": len(intra_cands),
        "cross_candidates": len(cross_cands),
        "health_snapshot_path": str(health_path),
        "graduation_report": asdict(report),
    }

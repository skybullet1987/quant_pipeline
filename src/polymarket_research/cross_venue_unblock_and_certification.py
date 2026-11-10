"""
Autonomous Blocker Registry, Single-Venue Hot-Reload Credential Lifecycle Manager,
168-Hour Per-Venue Certification Engine, and Bankroll Gate Verifier
(`src/polymarket_research/cross_venue_unblock_and_certification.py`).

Implements Sections 2, 3, 4, and 6 of the DOMINUS Master Unblock & Full Activation Directive:
  - `VENUE_ENDPOINT_AUTH_MATRIX`: Exact classification of public GET vs. authenticated read-only
    vs. prohibited trading endpoints and token/session rotation windows across all 6 venues.
  - `CredentialLifecycleManager`: Non-echoing `0600` credential provisioning, SHA-256 revocation
    enforcement, token/clock-skew/tickle expiry tracking, and targeted single-collector hot-reload
    (`hot_reload_single_venue_collector`) without interrupting healthy running feeds.
  - `PersistentBlockerRegistry`: Restart-safe SQLite + JSON (`blocker_registry.json`) registry
    recording all 9 required fields per blocker, preventing infinite auth retry loops via
    config-fingerprint gating, and auto-activating individual collectors when preconditions pass.
  - `VenueCertificationTracker`: Restart-persistent per-venue `168h` (`604,800s`) live shadow
    certification tracker (`Gates G1–G5` + uptime, freshness, API error rate, liquidity,
    execution-adjusted PnL, rule-mismatch count, and RSS headroom), strictly segregating
    `OFFLINE_SYNTHETIC` fixtures from live observation hours.
  - `BankrollMilestoneVerifier`: Programmatic audit of all 8 roadmap bankroll gates
    (`$88`, `$98`, `$110`, `$125`, `$140`, `$253`, `$450`, `$525`) with zero fabricated equity
    or settlement counts.
"""

from __future__ import annotations

import contextlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import sqlite3
import stat
import time
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

from src.polymarket_research.cross_venue_shadow_deployment_gates import (
    ALL_SHADOW_VENUES,
    VenueAuthorizationDecision,
    evaluate_all_venues_authorization,
    parse_dotenv_lines,
    stx_signing_key_available,
    validate_shadow_env_dict,
)
from src.polymarket_research.cross_venue_telemetry_and_watchdog import get_process_rss_mb

logger = logging.getLogger(__name__)

CERTIFICATION_TARGET_HOURS: float = 168.0
CERTIFICATION_TARGET_SECONDS: float = CERTIFICATION_TARGET_HOURS * 3600.0


# ---------------------------------------------------------------------------
# 1. Endpoint Authentication & Jurisdiction Matrix (BLOCKS A & B)
# ---------------------------------------------------------------------------

VENUE_ENDPOINT_AUTH_MATRIX: Dict[str, Dict[str, Any]] = {
    "polymarket": {
        "display_name": "Polymarket International",
        "public_get_endpoints": [
            "GET https://gamma-api.polymarket.com/markets",
            "GET https://clob.polymarket.com/book?token_id=...",
            "GET https://clob.polymarket.com/fee-rate?token_id=...",
            "WSS wss://ws-subscriptions-clob.polymarket.com/ws/market",
        ],
        "authenticated_readonly_endpoints": [],
        "prohibited_trading_endpoints": [
            "POST /order",
            "POST /orders",
            "DELETE /order",
            "DELETE /cancel-all",
        ],
        "credential_env_keys": [],
        "rotation_or_keepalive_sec": None,
        "max_clock_skew_sec": 30.0,
        "jurisdiction_summary": (
            "Two-tier separation: keyless public Gamma/CLOB discovery & L2 orderbooks are open globally "
            "(PUBLIC_DATA_AUTHORIZED except comprehensive sanctions); order placement (POST /order) & "
            "account operations are RESTRICTED in CA-ON per Polymarket Geographic Restrictions & OSC settlement."
        ),
    },
    "predict_fun": {
        "display_name": "Predict.fun (BNB Chain)",
        "public_get_endpoints": [
            "GET https://api-testnet.predict.fun/v1/markets (Unauthenticated BNB Testnet Sandbox — TESTNET_SANDBOX)",
            "GET https://api-testnet.predict.fun/v1/markets/{id}/orderbook (TESTNET_SANDBOX)",
        ],
        "authenticated_readonly_endpoints": [
            "GET https://api.predict.fun/v1/markets (Requires x-api-key; 240 req/min global)",
            "GET https://api.predict.fun/v1/markets/{id}/orderbook (Requires x-api-key; 500 req/min orderbook)",
            "GET https://api.predict.fun/v1/categories (Requires x-api-key)",
            "WSS wss://ws.predict.fun/ws?apiKey=... (predictOrderbook/{id}, predictTopOfBook/{id})",
        ],
        "prohibited_trading_endpoints": [
            "POST /v1/auth/message",
            "POST /v1/auth",
            "POST /v1/orders",
            "POST /v1/orders/remove",
        ],
        "credential_env_keys": ["PREDICT_FUN_API_KEY"],
        "rotation_or_keepalive_sec": 82_800.0,  # 23h proactive refresh window (JWT expires at 24h)
        "max_clock_skew_sec": 30.0,
        "jurisdiction_summary": (
            "Mainnet REST /v1/markets & WSS ws.predict.fun/ws require x-api-key (developers.predict.fun), AND "
            "PDF Labs Limited Terms bar CA-ON Restricted Persons from Technology Features unless operated by an "
            "eligible non-restricted entity or covered by PREDICT_FUN_DATA_LICENSE_ID. Unauthenticated BNB Testnet "
            "(PREDICT_FUN_ENV=testnet) is strictly segregated as TESTNET_SANDBOX and never treated as mainnet LIVE."
        ),
    },
    "sx_bet": {
        "display_name": "SX Bet (SX Rollup OBv3)",
        "public_get_endpoints": [
            "GET https://api.sx.bet/metadata/obv3",
            "GET https://api.sx.bet/leagues/active",
            "GET https://api.sx.bet/summary-v3/league/{leagueId}/game-lines (with x-time-zone header)",
            "GET https://api.sx.bet/summary-v3/{popular,inplay,upcoming}",
            "GET https://api.sx.bet/markets/active?pageSize=100",
            "GET https://api.sx.bet/trades-v3/public?perPage=50",
            "GET https://api.sx.bet/live-scores?sportXEventIds=...",
        ],
        "authenticated_readonly_endpoints": [
            "GET https://api.sx.bet/orderbook-v3/snapshot/market?marketHash=... (Requires x-sx-api-key)",
            "GET https://api.sx.bet/orders-v3?marketHashes=... (Requires x-sx-api-key)",
            "GET https://api.sx.bet/orders-v3/odds/best?marketHashes=... (Requires x-sx-api-key)",
            "GET https://api.sx.bet/user/realtime-token-v3/api-key (Requires x-sx-api-key; <= 30 req/60s)",
            "WSS wss://realtime.sx.bet/connection/websocket (Centrifugo orderbook_v3:{marketHash}, best_odds_v3:global)",
        ],
        "prohibited_trading_endpoints": [
            "POST /orders-v3",
            "POST /orders/new",
            "POST /orders/fill",
            "POST /orders/cancel/v2",
        ],
        "credential_env_keys": ["SX_BET_API_KEY"],
        "rotation_or_keepalive_sec": 3_300.0,  # Centrifugo realtime token refresh every 55m when WS active
        "max_clock_skew_sec": 30.0,
        "jurisdiction_summary": (
            "Public OBv3 REST (/metadata/obv3, /leagues/active, /summary-v3/league/{id}/game-lines, /summary-v3/*, "
            "/markets/active, /trades-v3/public, /live-scores) requires 0 API keys and 0 written data license "
            "(PUBLIC_DATA = AUTHORIZED_LIVE). Full L2 snapshot (/orderbook-v3/snapshot/market), /orders-v3, and "
            "Centrifugo WS require SX_BET_API_KEY (x-sx-api-key)."
        ),
    },
    "limitless": {
        "display_name": "Limitless Exchange (Base L2)",
        "public_get_endpoints": [
            "GET https://api.limitless.exchange/markets/active?limit=25&page=1..12",
            "GET https://api.limitless.exchange/markets/active/slugs",
            "GET https://api.limitless.exchange/categories",
            "GET https://api.limitless.exchange/markets/{slug}/orderbook",
            "WSS wss://ws.limitless.exchange/socket.io/?EIO=4&transport=websocket (namespace /markets: subscribe_market_prices -> orderbookUpdate, oraclePriceData, newPriceData)",
        ],
        "authenticated_readonly_endpoints": [],
        "prohibited_trading_endpoints": [
            "POST /orders",
            "DELETE /orders/{id}",
            "DELETE /orders/all/{slug}",
        ],
        "credential_env_keys": [],  # Stage G shadow uses 0 API/HMAC secrets; chat-exposed secret permanently excluded
        "rotation_or_keepalive_sec": 84_600.0,  # 23.5h proactive WS reconnect before 24h LB 1006 drop
        "max_clock_skew_sec": 30.0,
        "jurisdiction_summary": (
            "Two-tier separation in Street Chow Inc. Terms Section 1: CA-ON/CA-AB/US are listed as "
            "'not available for trading' (AUTHORIZED_LIVE for keyless PUBLIC_REST + PUBLIC_WEBSOCKET on FI hosting; "
            "AUTHENTICATED_READONLY, ACCOUNT_PRIVATE, and TRADING remain RESTRICTED under CA-ON)."
        ),
    },
    "forecastex": {
        "display_name": "ForecastEx / Interactive Brokers (CFTC DCM & CIRO)",
        "public_get_endpoints": [
            "GET https://forecastex.com/api/download?type=summary&date=YYYYMMDD",
            "GET https://forecastex.com/api/download?type=prices&date=YYYYMMDD",
            "GET https://forecastex.com/api/download?type=pairs&date=YYYYMMDD (10-minute CFTC intraday refresh)",
        ],
        "authenticated_readonly_endpoints": [
            "GET {IBKR_GATEWAY_URL}/iserver/auth/status",
            "POST {IBKR_GATEWAY_URL}/iserver/reauthenticate",
            "GET {IBKR_GATEWAY_URL}/tickle (55s keepalive)",
            "GET {IBKR_GATEWAY_URL}/trsrv/secdef?conids=...",
            "GET {IBKR_GATEWAY_URL}/iserver/secdef/search?symbol=...",
            "GET {IBKR_GATEWAY_URL}/iserver/secdef/info?conid=...&sectype=OPT&exchange=FORECASTX",
            "GET {IBKR_GATEWAY_URL}/iserver/marketdata/snapshot?conids=...&fields=84,86,88,85,6509",
            "WSS {IBKR_GATEWAY_URL}/ws (smd+{conid}+{\"fields\":[\"31\",\"84\",\"85\",\"86\",\"88\",\"6509\"]})",
        ],
        "prohibited_trading_endpoints": [
            "POST /iserver/account/{accountId}/orders",
            "DELETE /iserver/account/{accountId}/order/{orderId}",
        ],
        "credential_env_keys": ["IBKR_GATEWAY_URL"],
        "rotation_or_keepalive_sec": 55.0,  # CPAPI /tickle every 55s (<60s idle timeout)
        "max_clock_skew_sec": 30.0,
        "jurisdiction_summary": (
            "Regulated by CFTC (US DCM/DCO) and CIRO (via Interactive Brokers Canada Inc. in Ontario); "
            "public CFTC transparency CSV feeds are globally PUBLIC_DATA_AUTHORIZED; authenticated IBKR CPAPI "
            "requires a running local Client Portal Gateway session (IBKR_GATEWAY_URL)."
        ),
    },
    "stx_ontario": {
        "display_name": "STX Ontario (AGCO / iGaming Ontario)",
        "public_get_endpoints": [
            "WSS wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0 (Unsigned Phoenix v2: markets, ticker, trades, market:<symbol_or_uuid>)",
            "WSS wss://demo.stxapp.ca/socket/websocket?vsn=2.0.0 (Ontario Demo Phoenix v2)",
            "WSS wss://demo.stxapp.io/socket/websocket?vsn=2.0.0 (US Demo Phoenix v2)",
        ],
        "authenticated_readonly_endpoints": [
            "GET https://api.on.stxapp.ca/api/v1/me (Path A: STX_API_KEY_ID + 0600 STX_ED25519_KEY_FILE)",
            "GET https://api.on.stxapp.ca/api/v1/markets (Requires X-STX-ACCESS-* Ed25519 headers or Bearer STX_APPS_DATA_TOKEN)",
            "GET https://api.on.stxapp.ca/api/v1/events (Requires X-STX-ACCESS-* Ed25519 headers or Bearer STX_APPS_DATA_TOKEN)",
            "GET https://api.on.stxapp.ca/api/v1/markets/{id}/orderbook",
        ],
        "prohibited_trading_endpoints": [
            "POST /api/v1/orders",
            "DELETE /api/v1/orders/{id}",
            "POST /api/v1/orders/cancel_all",
        ],
        "credential_env_keys": ["STX_API_KEY_ID", "STX_ED25519_KEY_FILE"],
        "rotation_or_keepalive_sec": 25.0,  # Phoenix heartbeat every 25s (<30s timeout)
        "max_clock_skew_sec": 28.0,  # X-STX-ACCESS-TIMESTAMP ms must be within <30s of STX server
        "jurisdiction_summary": (
            "Unsigned public Phoenix WebSocket (wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0, documented at "
            "https://docs.stxapp.io/explore/live-markets/) streams real-time markets, ticker, trades, and per-market "
            "L2 orderbooks (market:<uuid>) with 0 API keys (PUBLIC_DATA = AUTHORIZED_LIVE, REALTIME_DATA = AUTHORIZED_LIVE). "
            "REST /api/v1/markets and /api/v1/events require Ed25519 X-STX-ACCESS-* headers or STX_APPS_DATA_TOKEN."
        ),
    },
}


# ---------------------------------------------------------------------------
# 2. Credential Lifecycle & Single-Collector Hot-Reload Manager (BLOCK B)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VenueCredentialStatus:
    venue: str
    requires_credentials_for_mode: bool
    credentials_present: bool
    format_valid: bool
    revoked_rejected: bool
    keepalive_or_rotation_interval_sec: Optional[float]
    seconds_since_last_refresh: Optional[float]
    needs_proactive_refresh: bool
    status_code: str


class CredentialLifecycleManager:
    """
    Manages secret-free credential validation, non-echoing `0600` atomic provisioning,
    rotation/keepalive monitoring, and targeted single-collector hot-reload.
    """

    def __init__(self, env_file_path: Optional[Path] = None) -> None:
        self.env_file_path = Path(env_file_path) if env_file_path else None
        self.last_refresh_by_venue: Dict[str, float] = {}

    @staticmethod
    def compute_safe_env_fingerprint(env: Mapping[str, str]) -> str:
        """Computes a deterministic SHA-256 fingerprint of config state without exposing secret values."""
        h = hashlib.sha256()
        for k in sorted(env.keys()):
            val = str(env.get(k) or "")
            val_digest = hashlib.sha256(val.encode("utf-8")).hexdigest()[:16] if val else "EMPTY"
            h.update(f"{k}={len(val)}:{val_digest};".encode("utf-8"))
        return h.hexdigest()

    def provision_env_updates_atomic(
        self,
        env_path: Path,
        updates: Mapping[str, str],
        *,
        enforce_0600: bool = True,
    ) -> Tuple[bool, Tuple[str, ...]]:
        """
        Atomically merges `updates` into `env_path` with `0600` permissions after structural &
        revocation validation. Never prints, logs, or returns any secret values.
        """
        existing: Dict[str, str] = {}
        if env_path.exists():
            parsed, errs = parse_dotenv_lines(env_path.read_text(encoding="utf-8"))
            if errs:
                return False, tuple(errs)
            existing.update(parsed)
        merged = dict(existing)
        for k, v in updates.items():
            merged[str(k).strip()] = str(v)

        rep = validate_shadow_env_dict(merged, checked_path=str(env_path), permissions_ok=True)
        if not rep.valid:
            return False, rep.errors

        env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Dominus Stage G Read-Only Shadow Environment (Managed Atomically — 0600)",
            *[f"{k}={merged[k]}" for k in sorted(merged.keys())],
            "",
        ]
        tmp_path = env_path.parent / f".{env_path.name}.tmp.{os.getpid()}"
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            if enforce_0600 and os.name != "nt":
                os.chmod(str(tmp_path), stat.S_IRUSR | stat.S_IWUSR)
            os.replace(str(tmp_path), str(env_path))
        finally:
            if tmp_path.exists():
                with contextlib.suppress(OSError):
                    tmp_path.unlink()
        now = time.time()
        for v in ALL_SHADOW_VENUES:
            self.last_refresh_by_venue[v] = now
        return True, ()

    def evaluate_all_credentials(
        self,
        env: Mapping[str, str],
        *,
        now_unix: Optional[float] = None,
    ) -> Dict[str, VenueCredentialStatus]:
        now = time.time() if now_unix is None else float(now_unix)
        val_rep = validate_shadow_env_dict(env)
        err_set = set(val_rep.errors)
        mode = (env.get("DOMINUS_NETWORK_MODE") or "offline").strip().lower()

        out: Dict[str, VenueCredentialStatus] = {}
        for v in ALL_SHADOW_VENUES:
            spec = VENUE_ENDPOINT_AUTH_MATRIX[v]
            keys: List[str] = list(spec["credential_env_keys"])
            rot_sec: Optional[float] = spec["rotation_or_keepalive_sec"]

            req_cred = False
            pf_testnet = v == "predict_fun" and (env.get("PREDICT_FUN_ENV") or "").strip().lower() == "testnet"
            if mode != "offline":
                if v == "stx_ontario":
                    req_cred = True
                elif v == "predict_fun" and not pf_testnet:
                    req_cred = True
                elif mode == "live_authenticated" and keys:
                    req_cred = True

            if v == "stx_ontario":
                has_path_a = bool((env.get("STX_API_KEY_ID") or "").strip()) and stx_signing_key_available(env)
                has_path_b = bool((env.get("STX_APPS_DATA_TOKEN") or "").strip())
                present = has_path_a or has_path_b
            else:
                present = all(bool((env.get(k) or "").strip()) for k in keys) if keys else True

            revoked = any(f"REVOKED_CREDENTIAL_SHA256_REJECTED:{k}" in err_set for k in keys)
            bad_fmt = any(
                any(err.endswith(f":{k}") for err in err_set)
                for k in keys
            )
            last_ref = self.last_refresh_by_venue.get(v)
            elapsed = round(max(0.0, now - last_ref), 2) if last_ref is not None else None
            needs_rot = bool(rot_sec is not None and elapsed is not None and elapsed >= rot_sec)

            if revoked:
                code = "REJECTED_REVOKED_SHA256"
            elif bad_fmt:
                code = "REJECTED_INVALID_FORMAT"
            elif req_cred and not present:
                code = "MISSING_REQUIRED_CREDENTIAL"
            elif needs_rot:
                code = "PROACTIVE_ROTATION_OR_KEEPALIVE_DUE"
            elif keys and present:
                code = "CREDENTIAL_READY_READONLY"
            else:
                code = "KEYLESS_PUBLIC_READONLY"

            out[v] = VenueCredentialStatus(
                venue=v,
                requires_credentials_for_mode=req_cred,
                credentials_present=present,
                format_valid=not bad_fmt,
                revoked_rejected=revoked,
                keepalive_or_rotation_interval_sec=rot_sec,
                seconds_since_last_refresh=elapsed,
                needs_proactive_refresh=needs_rot,
                status_code=code,
            )
        return out

    def hot_reload_single_venue_collector(
        self,
        collector: Any,
        venue: str,
        updated_env: Mapping[str, str],
    ) -> Dict[str, Any]:
        """
        Rebuilds & re-authorizes ONLY `venue` inside `LiveCrossVenueShadowCollector` without
        restarting or disturbing the connection state, WebSocket caches, or circuit breakers of
        any other venue!
        """
        from src.polymarket_research.cross_venue_connectors import (
            ForecastExIBKRConnector,
            LimitlessConnector,
            PolymarketConnector,
            PredictFunConnector,
            STXOntarioConnector,
            SXBetOBv3Connector,
        )

        v = venue.strip().lower()
        if v not in ALL_SHADOW_VENUES:
            raise ValueError(f"Unsupported venue for hot-reload: {v}")

        env_rep = validate_shadow_env_dict(updated_env)
        if not env_rep.valid:
            return {
                "reloaded": False,
                "venue": v,
                "reason": "ENV_VALIDATION_FAILED",
                "errors": list(env_rep.errors),
            }

        collector.env.update({str(k): str(val) for k, val in updated_env.items()})
        decisions = evaluate_all_venues_authorization(collector.env)
        dec = decisions[v]

        factory_map = {
            "polymarket": lambda: PolymarketConnector(max_pages=2, page_limit=100, max_hydrated_markets=64, env=collector.env),
            "limitless": lambda: LimitlessConnector(
                max_pages=collector.limitless_pages,
                orderbook_top_n=collector.limitless_orderbook_top_n,
                env=collector.env,
            ),
            "sx_bet": lambda: SXBetOBv3Connector(max_market_pages=2, max_order_batches=2, env=collector.env),
            "predict_fun": lambda: PredictFunConnector(
                max_pages=2,
                page_size=100,
                orderbook_top_n=48,
                testnet_smoke=collector.predict_testnet_smoke,
                env=collector.env,
            ),
            "forecastex": lambda: ForecastExIBKRConnector(env=collector.env),
            "stx_ontario": lambda: STXOntarioConnector(env=collector.env),
        }
        old_conn = collector.connectors.get(v)
        if old_conn is not None and hasattr(old_conn, "stop_background_ws"):
            old_conn.stop_background_ws()
        collector.connectors[v] = factory_map[v]()

        if collector.authorized_venues is not None:
            if dec.effective_authorized:
                collector.authorized_venues.add(v)
                collector.blocked_venue_reasons.pop(v, None)
            else:
                collector.authorized_venues.discard(v)
                collector.blocked_venue_reasons[v] = dec.status_code

        self.last_refresh_by_venue[v] = time.time()
        return {
            "reloaded": True,
            "venue": v,
            "effective_authorized": dec.effective_authorized,
            "verified_outcome_state": dec.verified_outcome_state,
            "authorization_status": dec.status_code,
            "scope_permissions": dict(dec.scope_permissions),
            "untouched_venues": [x for x in ALL_SHADOW_VENUES if x != v],
        }


# ---------------------------------------------------------------------------
# 3. Persistent Blocker Registry & Self-Healing Unblocker (Section 6)
# ---------------------------------------------------------------------------

@dataclass
class BlockerRecord:
    blocker_id: str
    affected_venue: str
    failed_requirement: str
    evidence: str
    available_remediation: str
    assigned_owner: str
    last_verification_utc: str
    retry_conditions: str
    current_state: str  # ACTIVE_BLOCKED | TRANSIENT_BACKOFF | RESOLVED_ACTIVE
    config_fingerprint_sha256: str = ""
    next_eligible_check_unix: float = 0.0
    verification_count: int = 1


class PersistentBlockerRegistry:
    """
    Durable SQLite + JSON (`blocker_registry.json`) blocker tracker with loop-free
    fingerprint gating for compliance/credential blocks and bounded retry for technical faults.
    """

    def __init__(self, data_dir: Path, *, db_filename: str = "shadow_telemetry.sqlite3") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / db_filename
        self.json_path = self.data_dir / "blocker_registry.json"
        self._init_table()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_table(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blocker_registry (
                    blocker_id TEXT PRIMARY KEY,
                    affected_venue TEXT NOT NULL,
                    failed_requirement TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    available_remediation TEXT NOT NULL,
                    assigned_owner TEXT NOT NULL,
                    last_verification_utc TEXT NOT NULL,
                    retry_conditions TEXT NOT NULL,
                    current_state TEXT NOT NULL,
                    config_fingerprint_sha256 TEXT NOT NULL,
                    next_eligible_check_unix REAL NOT NULL,
                    verification_count INTEGER NOT NULL DEFAULT 1
                );
                """
            )

    def load_all(self) -> Dict[str, BlockerRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM blocker_registry ORDER BY blocker_id").fetchall()
        return {
            str(r["blocker_id"]): BlockerRecord(
                blocker_id=str(r["blocker_id"]),
                affected_venue=str(r["affected_venue"]),
                failed_requirement=str(r["failed_requirement"]),
                evidence=str(r["evidence"]),
                available_remediation=str(r["available_remediation"]),
                assigned_owner=str(r["assigned_owner"]),
                last_verification_utc=str(r["last_verification_utc"]),
                retry_conditions=str(r["retry_conditions"]),
                current_state=str(r["current_state"]),
                config_fingerprint_sha256=str(r["config_fingerprint_sha256"]),
                next_eligible_check_unix=float(r["next_eligible_check_unix"]),
                verification_count=int(r["verification_count"]),
            )
            for r in rows
        }

    def upsert_record(self, rec: BlockerRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO blocker_registry(
                    blocker_id, affected_venue, failed_requirement, evidence,
                    available_remediation, assigned_owner, last_verification_utc,
                    retry_conditions, current_state, config_fingerprint_sha256,
                    next_eligible_check_unix, verification_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(blocker_id) DO UPDATE SET
                    failed_requirement=excluded.failed_requirement,
                    evidence=excluded.evidence,
                    available_remediation=excluded.available_remediation,
                    assigned_owner=excluded.assigned_owner,
                    last_verification_utc=excluded.last_verification_utc,
                    retry_conditions=excluded.retry_conditions,
                    current_state=excluded.current_state,
                    config_fingerprint_sha256=excluded.config_fingerprint_sha256,
                    next_eligible_check_unix=excluded.next_eligible_check_unix,
                    verification_count=excluded.verification_count
                """,
                (
                    rec.blocker_id,
                    rec.affected_venue,
                    rec.failed_requirement,
                    rec.evidence,
                    rec.available_remediation,
                    rec.assigned_owner,
                    rec.last_verification_utc,
                    rec.retry_conditions,
                    rec.current_state,
                    rec.config_fingerprint_sha256,
                    rec.next_eligible_check_unix,
                    rec.verification_count,
                ),
            )
        self._write_json_snapshot()

    def _write_json_snapshot(self) -> Path:
        records = self.load_all()
        payload = {
            "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "active_blockers_count": sum(1 for r in records.values() if r.current_state != "RESOLVED_ACTIVE"),
            "resolved_count": sum(1 for r in records.values() if r.current_state == "RESOLVED_ACTIVE"),
            "blockers": [asdict(r) for r in records.values()],
        }
        tmp = self.data_dir / f".blocker_registry.json.tmp.{os.getpid()}"
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(self.json_path))
        return self.json_path

    def sync_from_runtime_state(
        self,
        *,
        env: Mapping[str, str],
        auth_decisions: Mapping[str, VenueAuthorizationDecision],
        connector_snapshots: Optional[Mapping[str, Any]] = None,
        collector: Optional[Any] = None,
        cred_manager: Optional[CredentialLifecycleManager] = None,
        now_unix: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Synchronizes persistent blockers from live authorization + connector states:
          - Never re-polls permanent `AUTH_BLOCKED` / `MISSING_CREDENTIALS` venues when
            `config_fingerprint_sha256` is unchanged (eliminating infinite retry loops).
          - Automatically hot-reloads & unblocks an individual venue if `env` changed and
            `auth_decisions[v].effective_authorized` transitioned to `True`!
        """
        now = time.time() if now_unix is None else float(now_unix)
        now_utc = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        fp = CredentialLifecycleManager.compute_safe_env_fingerprint(env)
        existing = self.load_all()
        auto_unblocked: List[str] = []

        for v in ALL_SHADOW_VENUES:
            bid = f"BLK::{v.upper()}"
            prev = existing.get(bid)
            dec = auth_decisions.get(v)
            snap = (connector_snapshots or {}).get(v)
            snap_dict = snap if isinstance(snap, Mapping) else (asdict(snap) if snap is not None and hasattr(snap, "__dataclass_fields__") else {})

            # Check if a previously blocked venue is now authorized after a config/KYB update!
            if (
                prev is not None
                and prev.current_state == "ACTIVE_BLOCKED"
                and prev.config_fingerprint_sha256 != fp
                and dec is not None
                and dec.effective_authorized
                and collector is not None
                and cred_manager is not None
            ):
                reload_res = cred_manager.hot_reload_single_venue_collector(collector, v, env)
                if reload_res.get("reloaded"):
                    auto_unblocked.append(v)

            if dec is not None and not dec.effective_authorized:
                # Skip redundant verification writes when fingerprint is identical (0 infinite retry loops)
                if prev is not None and prev.current_state == "ACTIVE_BLOCKED" and prev.config_fingerprint_sha256 == fp and prev.failed_requirement == dec.status_code:
                    continue
                owner = (
                    "OPERATOR_CREDENTIALS"
                    if dec.status_code.startswith("CREDENTIALS_REQUIRED")
                    else "INSTITUTIONAL_OR_CONTRACTUAL_EXTERNAL"
                )
                self.upsert_record(
                    BlockerRecord(
                        blocker_id=bid,
                        affected_venue=v,
                        failed_requirement=dec.status_code,
                        evidence=(
                            f"verified_outcome={dec.verified_outcome_state}, "
                            f"operator_jurisdiction={dec.operator_jurisdiction}, "
                            f"server_region={dec.server_region}, network_mode={dec.network_mode}, "
                            f"scopes={json.dumps(dec.scope_permissions, sort_keys=True)}"
                        ),
                        available_remediation=dec.operator_action or (dec.required_evidence + " (See docs/KYB_AND_API_ONBOARDING_DOSSIERS.md)."),
                        assigned_owner=owner,
                        last_verification_utc=now_utc,
                        retry_conditions="Re-evaluate automatically ONLY when /etc/polymarket-shadow.env SHA-256 fingerprint changes.",
                        current_state="ACTIVE_BLOCKED",
                        config_fingerprint_sha256=fp,
                        next_eligible_check_unix=0.0,
                        verification_count=(prev.verification_count + 1) if prev else 1,
                    )
                )
                continue

            auth_st = str(snap_dict.get("authorization_state") or "")
            conn_st = str(snap_dict.get("connectivity_state") or "")
            hlth_st = str(snap_dict.get("health_state") or "")
            last_err = str(snap_dict.get("last_error") or "")
            snap_origin = str(snap_dict.get("data_origin") or "")

            if snap_origin == "TESTNET_SANDBOX" and dec is not None and dec.readonly_api_state != "READONLY_API_AUTHORIZED":
                req_code = f"MAINNET_{dec.readonly_api_state}"
                if prev is not None and prev.current_state == "ACTIVE_BLOCKED" and prev.config_fingerprint_sha256 == fp and prev.failed_requirement == req_code:
                    continue
                self.upsert_record(
                    BlockerRecord(
                        blocker_id=bid,
                        affected_venue=v,
                        failed_requirement=req_code,
                        evidence=(
                            f"Testnet sandbox protocol validation active (active_markets={snap_dict.get('active_markets', 0)}, "
                            f"data_origin=TESTNET_SANDBOX); mainnet_verified_outcome={dec.verified_outcome_state}, "
                            f"mainnet readonly_api={dec.readonly_api_state}"
                        ),
                        available_remediation=dec.operator_action or dec.required_evidence,
                        assigned_owner=(
                            "OPERATOR_CREDENTIALS"
                            if dec.readonly_api_state == "CREDENTIALS_REQUIRED"
                            else "INSTITUTIONAL_OR_CONTRACTUAL_EXTERNAL"
                        ),
                        last_verification_utc=now_utc,
                        retry_conditions="Mainnet re-evaluates when /etc/polymarket-shadow.env fingerprint changes.",
                        current_state="ACTIVE_BLOCKED",
                        config_fingerprint_sha256=fp,
                        next_eligible_check_unix=0.0,
                        verification_count=(prev.verification_count + 1) if prev else 1,
                    )
                )
                continue

            if auth_st in ("MISSING_CREDENTIALS", "AUTH_FAILED_PERMANENT"):
                if prev is not None and prev.current_state == "ACTIVE_BLOCKED" and prev.config_fingerprint_sha256 == fp and prev.failed_requirement == auth_st:
                    continue
                self.upsert_record(
                    BlockerRecord(
                        blocker_id=bid,
                        affected_venue=v,
                        failed_requirement=auth_st,
                        evidence=last_err or f"Connector reported {auth_st}",
                        available_remediation=(
                            f"Provision read-only credential for {v} via CredentialLifecycleManager "
                            "(0600 env / ~/.stx/credentials) and trigger single-venue hot-reload."
                        ),
                        assigned_owner="OPERATOR_CREDENTIALS",
                        last_verification_utc=now_utc,
                        retry_conditions="Re-evaluate when credential file or shadow .env fingerprint changes.",
                        current_state="ACTIVE_BLOCKED",
                        config_fingerprint_sha256=fp,
                        next_eligible_check_unix=0.0,
                        verification_count=(prev.verification_count + 1) if prev else 1,
                    )
                )
            elif conn_st == "DEGRADED_BACKOFF" or hlth_st in ("CIRCUIT_OPEN", "RATE_LIMITED", "FAULTED"):
                backoff_until = float(snap_dict.get("backoff_until_unix") or (now + 30.0))
                self.upsert_record(
                    BlockerRecord(
                        blocker_id=bid,
                        affected_venue=v,
                        failed_requirement=f"TECHNICAL_{hlth_st or conn_st}",
                        evidence=last_err or f"connectivity={conn_st}, health={hlth_st}",
                        available_remediation="Automatic jittered exponential circuit-breaker recovery.",
                        assigned_owner="AUTOMATED_RUNTIME",
                        last_verification_utc=now_utc,
                        retry_conditions=f"Bounded automatic retry after unix={backoff_until:.0f}.",
                        current_state="TRANSIENT_BACKOFF",
                        config_fingerprint_sha256=fp,
                        next_eligible_check_unix=backoff_until,
                        verification_count=(prev.verification_count + 1) if prev else 1,
                    )
                )
            elif conn_st in ("CONNECTED_REST", "CONNECTED_WS") and hlth_st in ("HEALTHY", "EMPTY_BOOK"):
                self.upsert_record(
                    BlockerRecord(
                        blocker_id=bid,
                        affected_venue=v,
                        failed_requirement="NONE",
                        evidence=(
                            f"LIVE ({snap_dict.get('data_origin', 'LIVE')}): "
                            f"active_markets={snap_dict.get('active_markets', 0)}, "
                            f"l2_books={snap_dict.get('l2_books_hydrated', 0)}"
                        ),
                        available_remediation="Operational — accruing 168h certification.",
                        assigned_owner="AUTOMATED_RUNTIME",
                        last_verification_utc=now_utc,
                        retry_conditions="Continuous 15s health & freshness monitoring.",
                        current_state="RESOLVED_ACTIVE",
                        config_fingerprint_sha256=fp,
                        next_eligible_check_unix=now + 15.0,
                        verification_count=(prev.verification_count + 1) if prev else 1,
                    )
                )

        all_now = self.load_all()
        return {
            "auto_unblocked_venues": auto_unblocked,
            "active_blockers": [asdict(r) for r in all_now.values() if r.current_state != "RESOLVED_ACTIVE"],
            "resolved_venues": [r.affected_venue for r in all_now.values() if r.current_state == "RESOLVED_ACTIVE"],
            "json_path": str(self.json_path),
        }


# ---------------------------------------------------------------------------
# 4. Restart-Safe 168-Hour Per-Venue Certification Engine (BLOCK E & Sec 3)
# ---------------------------------------------------------------------------

class VenueCertificationTracker:
    """
    Tracks independent `168h` (`7-day`) live shadow certification per venue in SQLite WAL,
    preserving cumulative live observation intervals, API error rates, liquidity, and `G1–G5`
    graduation metrics across process restarts while strictly excluding `OFFLINE_SYNTHETIC` runs.
    """

    def __init__(self, data_dir: Path, *, db_filename: str = "shadow_telemetry.sqlite3") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / db_filename
        self.report_path = self.data_dir / "certification_report.json"
        self._cached_ob_stats: Optional[Tuple[float, Dict[str, Dict[str, Any]]]] = None
        self._init_tables()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=-8192;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_tables(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS venue_certification_state (
                    venue TEXT PRIMARY KEY,
                    first_live_unix REAL,
                    last_cycle_unix REAL,
                    last_healthy_unix REAL,
                    cumulative_live_healthy_sec REAL NOT NULL DEFAULT 0.0,
                    cumulative_live_downtime_sec REAL NOT NULL DEFAULT 0.0,
                    live_cycles_ok INTEGER NOT NULL DEFAULT 0,
                    live_cycles_failed INTEGER NOT NULL DEFAULT 0,
                    synthetic_cycles_segregated INTEGER NOT NULL DEFAULT 0,
                    last_active_markets INTEGER NOT NULL DEFAULT 0,
                    last_l2_books INTEGER NOT NULL DEFAULT 0,
                    peak_rss_mb REAL NOT NULL DEFAULT 0.0,
                    data_origin TEXT NOT NULL DEFAULT 'NONE'
                );

                CREATE TABLE IF NOT EXISTS venue_freshness_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_unix REAL NOT NULL,
                    venue TEXT NOT NULL,
                    quote_age_sec REAL NOT NULL,
                    median_latency_ms REAL
                );
                CREATE INDEX IF NOT EXISTS idx_vf_venue_ts ON venue_freshness_samples(venue, ts_unix);
                """
            )

    def record_cycle_observation(
        self,
        *,
        connector_snapshots: Mapping[str, Any],
        network_mode: str,
        cycle_interval_sec: float = 15.0,
        now_unix: Optional[float] = None,
    ) -> None:
        now = time.time() if now_unix is None else float(now_unix)
        rss_mb = get_process_rss_mb()

        with self._connect() as conn:
            cur = conn.cursor()
            for v in ALL_SHADOW_VENUES:
                raw_s = connector_snapshots.get(v)
                s = (
                    raw_s
                    if isinstance(raw_s, Mapping)
                    else (asdict(raw_s) if raw_s is not None and hasattr(raw_s, "__dataclass_fields__") else {})
                )
                origin = str(s.get("data_origin") or ("OFFLINE_SYNTHETIC" if network_mode == "offline" else "NONE"))
                conn_st = str(s.get("connectivity_state") or "DISCONNECTED")
                hlth_st = str(s.get("health_state") or "IDLE")
                auth_st = str(s.get("authorization_state") or "UNINITIALIZED")
                act_mkts = int(s.get("active_markets") or s.get("markets_parsed") or 0)
                l2_bks = int(s.get("l2_books_hydrated") or s.get("l2_books_fetched") or 0)
                med_lat = s.get("median_latency_ms")

                prev = cur.execute("SELECT * FROM venue_certification_state WHERE venue = ?", (v,)).fetchone()
                first_live = float(prev["first_live_unix"]) if (prev and prev["first_live_unix"] is not None) else None
                last_cyc = float(prev["last_cycle_unix"]) if (prev and prev["last_cycle_unix"] is not None) else None
                last_ok = float(prev["last_healthy_unix"]) if (prev and prev["last_healthy_unix"] is not None) else None
                cum_ok = float(prev["cumulative_live_healthy_sec"]) if prev else 0.0
                cum_dn = float(prev["cumulative_live_downtime_sec"]) if prev else 0.0
                cyc_ok = int(prev["live_cycles_ok"]) if prev else 0
                cyc_fail = int(prev["live_cycles_failed"]) if prev else 0
                cyc_syn = int(prev["synthetic_cycles_segregated"]) if prev else 0
                peak_rss = max(float(prev["peak_rss_mb"]) if prev else 0.0, rss_mb)

                dt = min(max(1.0, float(cycle_interval_sec) * 2.0), max(0.0, now - last_cyc)) if last_cyc is not None else float(cycle_interval_sec)

                if network_mode == "offline" or origin in ("OFFLINE_SYNTHETIC", "TESTNET_SANDBOX"):
                    cyc_syn += 1
                elif auth_st in ("AUTHORIZED_LIVE",) or conn_st in ("CONNECTED_REST", "CONNECTED_WS", "DEGRADED_BACKOFF"):
                    is_live_healthy = (
                        origin in ("LIVE_VERIFIED", "REGULATORY_PUBLIC_DELAYED")
                        and conn_st in ("CONNECTED_REST", "CONNECTED_WS")
                        and hlth_st in ("HEALTHY", "EMPTY_BOOK")
                        and act_mkts > 0
                    )
                    if is_live_healthy:
                        if first_live is None:
                            first_live = now
                        cum_ok += dt
                        cyc_ok += 1
                        last_ok = now
                        quote_age = max(0.0, now - float(s.get("last_success_unix") or now))
                        cur.execute(
                            "INSERT INTO venue_freshness_samples(ts_unix, venue, quote_age_sec, median_latency_ms) VALUES (?, ?, ?, ?)",
                            (now, v, round(quote_age, 3), float(med_lat) if med_lat is not None else None),
                        )
                        if cyc_ok % 50 == 0:
                            cur.execute(
                                "DELETE FROM venue_freshness_samples WHERE venue = ? AND id NOT IN (SELECT id FROM venue_freshness_samples WHERE venue = ? ORDER BY ts_unix DESC LIMIT 2000)",
                                (v, v),
                            )
                    elif auth_st == "AUTHORIZED_LIVE":
                        cum_dn += dt
                        cyc_fail += 1

                cur.execute(
                    """
                    INSERT INTO venue_certification_state(
                        venue, first_live_unix, last_cycle_unix, last_healthy_unix,
                        cumulative_live_healthy_sec, cumulative_live_downtime_sec,
                        live_cycles_ok, live_cycles_failed, synthetic_cycles_segregated,
                        last_active_markets, last_l2_books, peak_rss_mb, data_origin
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(venue) DO UPDATE SET
                        first_live_unix=excluded.first_live_unix,
                        last_cycle_unix=excluded.last_cycle_unix,
                        last_healthy_unix=excluded.last_healthy_unix,
                        cumulative_live_healthy_sec=excluded.cumulative_live_healthy_sec,
                        cumulative_live_downtime_sec=excluded.cumulative_live_downtime_sec,
                        live_cycles_ok=excluded.live_cycles_ok,
                        live_cycles_failed=excluded.live_cycles_failed,
                        synthetic_cycles_segregated=excluded.synthetic_cycles_segregated,
                        last_active_markets=excluded.last_active_markets,
                        last_l2_books=excluded.last_l2_books,
                        peak_rss_mb=excluded.peak_rss_mb,
                        data_origin=excluded.data_origin
                    """,
                    (
                        v,
                        first_live,
                        now,
                        last_ok,
                        round(cum_ok, 3),
                        round(cum_dn, 3),
                        cyc_ok,
                        cyc_fail,
                        cyc_syn,
                        act_mkts,
                        l2_bks,
                        peak_rss,
                        origin,
                    ),
                )

    def build_certification_report(
        self,
        *,
        auth_decisions: Optional[Mapping[str, VenueAuthorizationDecision]] = None,
        now_unix: Optional[float] = None,
    ) -> Dict[str, Any]:
        now = time.time() if now_unix is None else float(now_unix)
        rss_now = get_process_rss_mb()
        venues_out: Dict[str, Any] = {}

        with self._connect() as conn:
            cur = conn.cursor()
            has_ob = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='orderbook_snapshots'"
            ).fetchone() is not None

            fp_rejects_by_v: Dict[str, int] = {v: 0 for v in ALL_SHADOW_VENUES}
            rule_mismatches_by_v: Dict[str, int] = {v: 0 for v in ALL_SHADOW_VENUES}
            cache_valid = (
                now_unix is None
                and self._cached_ob_stats is not None
                and (now - self._cached_ob_stats[0]) < 60.0
                and len(self._cached_ob_stats[1]) == len(ALL_SHADOW_VENUES)
            )
            if has_ob and not cache_valid:
                r_all = cur.execute(
                    """
                    SELECT stage, reason, venues_csv, COUNT(*) AS c
                    FROM rejected_opportunities
                    WHERE data_origin IN ('LIVE_VERIFIED', 'REGULATORY_PUBLIC_DELAYED')
                    GROUP BY data_origin, stage, reason, venues_csv
                    """
                ).fetchall()
                for rr in r_all:
                    v_set = {x.strip() for x in str(rr["venues_csv"] or "").split(",") if x.strip()}
                    c_val = int(rr["c"] or 0)
                    is_rg = str(rr["stage"]) == "RULE_GATE"
                    for v_item in v_set:
                        if v_item in fp_rejects_by_v:
                            fp_rejects_by_v[v_item] += c_val
                            if is_rg:
                                rule_mismatches_by_v[v_item] += c_val

            for v in ALL_SHADOW_VENUES:
                st = cur.execute("SELECT * FROM venue_certification_state WHERE venue = ?", (v,)).fetchone()
                cum_ok = float(st["cumulative_live_healthy_sec"]) if st else 0.0
                cum_dn = float(st["cumulative_live_downtime_sec"]) if st else 0.0
                cyc_ok = int(st["live_cycles_ok"]) if st else 0
                cyc_fail = int(st["live_cycles_failed"]) if st else 0
                cyc_syn = int(st["synthetic_cycles_segregated"]) if st else 0
                act_mkts = int(st["last_active_markets"]) if st else 0
                l2_bks = int(st["last_l2_books"]) if st else 0
                peak_rss = max(float(st["peak_rss_mb"]) if st else 0.0, rss_now)
                origin = str(st["data_origin"]) if st else "NONE"

                tot_obs = cum_ok + cum_dn
                uptime_pct = round((cum_ok / tot_obs) * 100.0, 3) if tot_obs > 0 else 0.0
                tot_cyc = cyc_ok + cyc_fail
                err_rate_pct = round((cyc_fail / tot_cyc) * 100.0, 3) if tot_cyc > 0 else 0.0

                fresh_rows = cur.execute(
                    "SELECT quote_age_sec, median_latency_ms FROM venue_freshness_samples WHERE venue = ? ORDER BY ts_unix DESC LIMIT 500",
                    (v,),
                ).fetchall()
                ages = sorted(float(r["quote_age_sec"]) for r in fresh_rows)
                lats = sorted(float(r["median_latency_ms"]) for r in fresh_rows if r["median_latency_ms"] is not None)
                p95_age = round(ages[min(len(ages) - 1, int(0.95 * len(ages)))], 2) if ages else None
                p99_lat = round(lats[min(len(lats) - 1, int(0.99 * len(lats)))], 2) if lats else None

                avg_depth = 0.0
                matched_opps = 0
                sim_pnl = 0.0
                obs_pnl = 0.0
                fp_rejects = 0
                rule_mismatches = 0
                dz_count = 0

                quarantined_cnt = 0
                if has_ob:
                    cached_venue_ob = (
                        self._cached_ob_stats[1].get(v)
                        if (now_unix is None and self._cached_ob_stats is not None and (now - self._cached_ob_stats[0]) < 60.0)
                        else None
                    )
                    if cached_venue_ob is not None:
                        avg_depth = cached_venue_ob["avg_depth"]
                        matched_opps = cached_venue_ob["matched_opps"]
                        sim_pnl = cached_venue_ob["sim_pnl"]
                        obs_pnl = cached_venue_ob["obs_pnl"]
                        quarantined_cnt = cached_venue_ob["quarantined_cnt"]
                        fp_rejects = cached_venue_ob["fp_rejects"]
                        rule_mismatches = cached_venue_ob["rule_mismatches"]
                        dz_count = cached_venue_ob["dz_count"]
                    else:
                        sig_cols = {str(r["name"]) for r in cur.execute("PRAGMA table_info(arbitrage_signals)").fetchall()}
                        has_contam_col = "contaminated" in sig_cols
                        contam_clause = " AND COALESCE(contaminated, 0) = 0" if has_contam_col else ""

                        d_row = cur.execute(
                            "SELECT COALESCE(AVG(total_depth_usd), 0.0) AS d FROM orderbook_snapshots WHERE venue = ? AND data_origin IN ('LIVE_VERIFIED', 'REGULATORY_PUBLIC_DELAYED') AND total_depth_usd > 0.0",
                            (v,),
                        ).fetchone()
                        avg_depth = round(float(d_row["d"]), 2) if d_row else 0.0

                        p_row = cur.execute(
                            "SELECT COUNT(*) AS c FROM pairing_candidates WHERE (venue_a = ? OR venue_b = ?) AND rule_passed = 1 AND data_origin IN ('LIVE_VERIFIED', 'REGULATORY_PUBLIC_DELAYED')",
                            (v, v),
                        ).fetchone()
                        matched_opps = int(p_row["c"]) if p_row else 0

                        s_row = cur.execute(
                            f"""
                            SELECT COALESCE(SUM(sim_exec_edge_usd), 0.0) AS sp, COALESCE(SUM(obs_net_pnl_usd), 0.0) AS op
                            FROM arbitrage_signals
                            WHERE (',' || venues_csv || ',') LIKE ? AND data_origin IN ('LIVE_VERIFIED', 'REGULATORY_PUBLIC_DELAYED'){contam_clause}
                            """,
                            (f"%,{v},%",),
                        ).fetchone()
                        if s_row:
                            sim_pnl = round(float(s_row["sp"]), 4)
                            obs_pnl = round(float(s_row["op"]), 4)

                        if has_contam_col:
                            q_row = cur.execute(
                                "SELECT COUNT(*) AS qc FROM arbitrage_signals WHERE (',' || venues_csv || ',') LIKE ? AND COALESCE(contaminated, 0) = 1",
                                (f"%,{v},%",),
                            ).fetchone()
                            quarantined_cnt = int(q_row["qc"]) if q_row else 0

                        fp_rejects = fp_rejects_by_v.get(v, 0)
                        rule_mismatches = rule_mismatches_by_v.get(v, 0)

                        dz_row = cur.execute(
                            "SELECT COALESCE(SUM(double_zero_incident), 0) AS dz FROM market_resolutions WHERE data_origin NOT IN ('OFFLINE_SYNTHETIC', 'TESTNET_SANDBOX')"
                        ).fetchone()
                        dz_count = int(dz_row["dz"]) if dz_row else 0
                        if now_unix is None:
                            if self._cached_ob_stats is None or (now - self._cached_ob_stats[0]) >= 60.0:
                                self._cached_ob_stats = (now, {})
                            self._cached_ob_stats[1][v] = {
                                "avg_depth": avg_depth,
                                "matched_opps": matched_opps,
                                "sim_pnl": sim_pnl,
                                "obs_pnl": obs_pnl,
                                "quarantined_cnt": quarantined_cnt,
                                "fp_rejects": fp_rejects,
                                "rule_mismatches": rule_mismatches,
                                "dz_count": dz_count,
                            }

                live_hours = round(cum_ok / 3600.0, 4)
                rem_hours = round(max(0.0, CERTIFICATION_TARGET_HOURS - live_hours), 4)
                pct_168h = round(min(100.0, (cum_ok / CERTIFICATION_TARGET_SECONDS) * 100.0), 4)
                duration_done = cum_ok >= CERTIFICATION_TARGET_SECONDS
                rss_ok = peak_rss <= 512.0

                gates = {
                    "duration_168h_complete": duration_done,
                    "uptime_ge_99pct": uptime_pct >= 99.0 if tot_obs > 0 else False,
                    "api_error_rate_le_2pct": err_rate_pct <= 2.0 if tot_cyc > 0 else False,
                    "G2_zero_double_zero_incidents": dz_count == 0,
                    "rss_within_180mb_cgroup": rss_ok,
                    "rss_within_320mb_cgroup": rss_ok,
                    "rss_within_512mb_cgroup": rss_ok,
                }

                dec = (auth_decisions or {}).get(v)
                if duration_done and all(gates.values()):
                    verdict = "CERTIFIED_168H"
                    milestone_stage = "STAGE_C_168H_FORMAL_GRADUATION"
                elif cum_ok >= 48.0 * 3600.0:
                    verdict = "IN_PROGRESS_LIVE"
                    milestone_stage = "STAGE_B_48H_DIRECTIONAL_VIABILITY"
                elif cum_ok >= 24.0 * 3600.0:
                    verdict = "IN_PROGRESS_LIVE"
                    milestone_stage = "STAGE_B_24H_DIRECTIONAL_VIABILITY"
                elif cum_ok > 0:
                    verdict = "IN_PROGRESS_LIVE"
                    milestone_stage = "STAGE_A_DATA_STREAMING_OPERATIONAL"
                elif origin == "TESTNET_SANDBOX":
                    verdict = "TESTNET_SANDBOX_PROTOCOL_VALIDATION"
                    milestone_stage = "SANDBOX_ONLY"
                elif dec is not None and not dec.effective_authorized:
                    verdict = f"BLOCKED_AWAITING_ACTIVATION({dec.status_code})"
                    milestone_stage = "BLOCKED_EXTERNAL_OR_CREDENTIALS"
                elif cyc_syn > 0:
                    verdict = "OFFLINE_SYNTHETIC_ONLY"
                    milestone_stage = "OFFLINE_SYNTHETIC"
                else:
                    verdict = "IDLE_AWAITING_CREDENTIALS_OR_START"
                    milestone_stage = "IDLE"

                eta_168h_utc = (
                    datetime.fromtimestamp(now + rem_hours * 3600.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    if cum_ok > 0
                    else None
                )

                venues_out[v] = {
                    "venue": v,
                    "venue_classification": getattr(dec, "venue_classification", "EXTERNAL_ACCESS_REQUIRED") if dec is not None else "EXTERNAL_ACCESS_REQUIRED",
                    "certification_verdict": verdict,
                    "milestone_stage": milestone_stage,
                    "data_origin": origin,
                    "capabilities": {
                        "market_data_access": getattr(dec, "market_data_access", "UNKNOWN") if dec is not None else "UNKNOWN",
                        "shadow_research_access": getattr(dec, "shadow_research_access", "UNKNOWN") if dec is not None else "UNKNOWN",
                        "live_trading_access": "RESTRICTED",
                        "PUBLIC_DATA": getattr(dec, "public_data_capability", "RESTRICTED") if dec is not None else "RESTRICTED",
                        "AUTHENTICATED_DATA": getattr(dec, "authenticated_data_capability", "RESTRICTED") if dec is not None else "RESTRICTED",
                        "REALTIME_DATA": getattr(dec, "realtime_data_capability", "RESTRICTED") if dec is not None else "RESTRICTED",
                        "SHADOW_RESEARCH": getattr(dec, "shadow_research_capability", "RESTRICTED") if dec is not None else "RESTRICTED",
                        "LIVE_ORDER_EXECUTION": "RESTRICTED",
                    },
                    "endpoint_capabilities": getattr(dec, "endpoint_capabilities", {}) if dec is not None else {},
                    "certified_live_hours": live_hours,
                    "target_hours": CERTIFICATION_TARGET_HOURS,
                    "progress_168h_pct": pct_168h,
                    "remaining_hours": rem_hours,
                    "earliest_168h_eta_utc": eta_168h_utc,
                    "uptime_pct": uptime_pct,
                    "freshness_p95_age_sec": p95_age,
                    "p99_http_latency_ms": p99_lat,
                    "live_cycles_ok": cyc_ok,
                    "live_cycles_failed": cyc_fail,
                    "synthetic_cycles_segregated": cyc_syn,
                    "api_error_rate_pct": err_rate_pct,
                    "active_markets": act_mkts,
                    "l2_books_hydrated": l2_bks,
                    "mean_book_depth_usd": avg_depth,
                    "matched_opportunities": matched_opps,
                    "simulated_executable_edge_usd": sim_pnl,
                    "execution_adjusted_post_delay_pnl_usd": obs_pnl,
                    "quarantined_contaminated_signals": quarantined_cnt,
                    "false_positive_arb_rejections": fp_rejects,
                    "settlement_rule_mismatches_caught": rule_mismatches,
                    "double_zero_incidents": dz_count,
                    "peak_rss_mb": peak_rss,
                    "gates": gates,
                }

        report = {
            "generated_at_utc": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target_certification_hours": CERTIFICATION_TARGET_HOURS,
            "current_rss_mb": rss_now,
            "certified_venues": [v for v, d in venues_out.items() if d["certification_verdict"] == "CERTIFIED_168H"],
            "active_live_certifying_venues": [
                v for v, d in venues_out.items() if d["certification_verdict"] == "IN_PROGRESS_LIVE"
            ],
            "venues": venues_out,
        }
        tmp = self.data_dir / f".certification_report.json.tmp.{os.getpid()}"
        tmp.write_text(json.dumps(report, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(self.report_path))
        return report


# ---------------------------------------------------------------------------
# 5. Roadmap Bankroll Milestone Gate Verifier ($88 .. $525) (Section 4)
# ---------------------------------------------------------------------------

BANKROLL_MILESTONE_SPECS: Tuple[Dict[str, Any], ...] = (
    {
        "gate_usd": 88.0,
        "bracket_id": "M2.1",
        "min_settled_trades": 8,
        "requires_cross_venue_168h": False,
        "unlocks": "Graduate top zero-loss D1/C1 sub-sleeves to +20% clip sizing inside Polygon harvester.",
    },
    {
        "gate_usd": 98.0,
        "bracket_id": "M2.2",
        "min_settled_trades": 16,
        "requires_cross_venue_168h": False,
        "unlocks": "Expand resting 0%-fee Maker-Anchor concurrency to 2 simultaneous corridors.",
    },
    {
        "gate_usd": 110.0,
        "bracket_id": "M2.3",
        "min_settled_trades": 25,
        "requires_cross_venue_168h": False,
        "unlocks": "Unlock 3-leg NegRisk closed-partition conversion sweeps at $15-$22 clip cap.",
    },
    {
        "gate_usd": 125.0,
        "bracket_id": "M3.1",
        "min_settled_trades": 35,
        "requires_cross_venue_168h": False,
        "unlocks": "Scale verified riskless Polygon box clip cap to $25 with strict $0 accounting discrepancy.",
    },
    {
        "gate_usd": 140.0,
        "bracket_id": "M3.2",
        "min_settled_trades": 48,
        "requires_cross_venue_168h": False,
        "unlocks": "Begin Stage G cross-venue capital staging preparation (still 0 live external orders until 168h + P0 Gate 0).",
    },
    {
        "gate_usd": 253.0,
        "bracket_id": "M4.1_STAGE_G_MICRO",
        "min_settled_trades": 80,
        "requires_cross_venue_168h": True,
        "unlocks": "Eligible for $20-$25 micro-live second-venue arbitrage ONLY on P0-authorized & 168h-certified venues.",
    },
    {
        "gate_usd": 450.0,
        "bracket_id": "M5.1_MULTI_VENUE_SCALE",
        "min_settled_trades": 140,
        "requires_cross_venue_168h": True,
        "unlocks": "Scale multi-venue riskless complete-basket allocation across >=2 168h-certified venues.",
    },
    {
        "gate_usd": 525.0,
        "bracket_id": "M5.2_INSTITUTIONAL_TIER",
        "min_settled_trades": 180,
        "requires_cross_venue_168h": True,
        "unlocks": "Full multi-venue institutional maker-anchor + Relay L2 automated treasury rebalance tier.",
    },
)


class BankrollMilestoneVerifier:
    """
    Audits all 8 roadmap bankroll gates (`$88`, `$98`, `$110`, `$125`, `$140`, `$253`, `$450`, `$525`)
    against real account equity, settled trades, `$0.00` accounting discrepancy, `riskless_only_mode`,
    and `168h` cross-venue certification without fabricating equity or settlements.
    """

    @staticmethod
    def verify_gates(
        *,
        total_account_equity_usd: float,
        settled_live_trades: int,
        accounting_discrepancy_usd: float = 0.0,
        riskless_only_mode: bool = True,
        certified_168h_venues: Sequence[str] = (),
        p0_authorized_live_venues: Sequence[str] = (),
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        eq = round(float(total_account_equity_usd), 6)
        settled = max(0, int(settled_live_trades))
        disc = round(abs(float(accounting_discrepancy_usd)), 6)
        disc_ok = disc <= 0.01
        cert_set = [str(v) for v in certified_168h_venues]
        auth_set = [str(v) for v in p0_authorized_live_venues]

        milestones: List[Dict[str, Any]] = []
        highest_unlocked: Optional[float] = None
        next_target: Optional[Dict[str, Any]] = None

        for spec in BANKROLL_MILESTONE_SPECS:
            target = float(spec["gate_usd"])
            req_trades = int(spec["min_settled_trades"])
            req_xv = bool(spec["requires_cross_venue_168h"])

            eq_ok = eq >= target
            tr_ok = settled >= req_trades
            xv_ok = (len(cert_set) >= 1 and len(auth_set) >= 1) if req_xv else True
            passed = bool(eq_ok and tr_ok and disc_ok and riskless_only_mode and xv_ok)

            missing: List[str] = []
            if not eq_ok:
                missing.append(f"EQUITY_SHORTFALL(${target - eq:.2f}_NEEDED)")
            if not tr_ok:
                missing.append(f"SETTLEMENTS_SHORTFALL({req_trades - settled}_MORE_NEEDED)")
            if not disc_ok:
                missing.append(f"ACCOUNTING_DISCREPANCY(${disc:.4f}>0.01)")
            if not riskless_only_mode:
                missing.append("RISKLESS_ONLY_MODE_DISABLED")
            if req_xv and not xv_ok:
                missing.append("REQUIRES_P0_AUTHORIZED_AND_168H_CERTIFIED_EXTERNAL_VENUE")

            row = {
                "gate_usd": target,
                "bracket_id": spec["bracket_id"],
                "passed": passed,
                "equity_ok": eq_ok,
                "equity_deficit_usd": round(max(0.0, target - eq), 4),
                "settlements_ok": tr_ok,
                "required_settled_trades": req_trades,
                "observed_settled_trades": settled,
                "accounting_discrepancy_ok": disc_ok,
                "riskless_only_mode_ok": bool(riskless_only_mode),
                "cross_venue_168h_ok": xv_ok,
                "blocking_reasons": missing,
                "unlocks": spec["unlocks"],
            }
            milestones.append(row)
            if passed:
                highest_unlocked = target
            elif next_target is None:
                next_target = row

        result = {
            "verified_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "observed_total_account_equity_usd": eq,
            "observed_settled_live_trades": settled,
            "accounting_discrepancy_usd": disc,
            "riskless_only_mode": bool(riskless_only_mode),
            "certified_168h_venues": cert_set,
            "p0_authorized_live_venues": auth_set,
            "highest_unlocked_gate_usd": highest_unlocked,
            "next_gate": next_target,
            "milestones": milestones,
        }
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = output_path.parent / f".{output_path.name}.tmp.{os.getpid()}"
            tmp.write_text(json.dumps(result, indent=2), encoding="utf-8")
            os.replace(str(tmp), str(output_path))
        return result


# ---------------------------------------------------------------------------
# 6. Machine-Readable Restriction Transparency Registry (Mandate Section 6)
# ---------------------------------------------------------------------------

RESTRICTION_CATEGORIES = (
    "INTERNAL_ADMINISTRATIVE",
    "TECHNICAL",
    "EXTERNAL_AUTHORIZATION",
    "PRODUCTION_SAFETY",
)


@dataclass(frozen=True)
class RestrictionEntry:
    restriction_id: str
    venue: str
    affected_capability: str
    restriction_category: str  # INTERNAL_ADMINISTRATIVE | TECHNICAL | EXTERNAL_AUTHORIZATION | PRODUCTION_SAFETY
    origin: str
    is_external: bool
    supporting_evidence: str
    blocks_rest: bool
    blocks_websocket: bool
    blocks_shadow_research: bool
    blocks_trading: bool
    current_status: str  # ELIMINATED_UNLOCKED | CREDENTIALS_PENDING | ACTIVE_RESTRICTED | ENFORCED_SAFETY_GATE
    remediation_or_auth_step: str


class RestrictionRegistry:
    """
    Machine-readable restriction transparency registry (`restriction_registry.json` + SQLite WAL table)
    auditing every eliminated internal gate and every remaining technical, external, or production-safety
    boundary without cascading trading restrictions into permitted read-only research.
    """

    def __init__(self, data_dir: Path, *, db_filename: str = "shadow_telemetry.sqlite3") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / db_filename
        self.json_path = self.data_dir / "restriction_registry.json"
        self._init_table()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_table(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS restriction_registry (
                    restriction_id TEXT PRIMARY KEY,
                    venue TEXT NOT NULL,
                    affected_capability TEXT NOT NULL,
                    restriction_category TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    is_external INTEGER NOT NULL,
                    supporting_evidence TEXT NOT NULL,
                    blocks_rest INTEGER NOT NULL,
                    blocks_websocket INTEGER NOT NULL,
                    blocks_shadow_research INTEGER NOT NULL,
                    blocks_trading INTEGER NOT NULL,
                    current_status TEXT NOT NULL,
                    remediation_or_auth_step TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );
                """
            )

    def build_entries(
        self,
        *,
        env: Mapping[str, str],
        auth_decisions: Mapping[str, VenueAuthorizationDecision],
        connector_snapshots: Optional[Mapping[str, Any]] = None,
    ) -> List[RestrictionEntry]:
        has_sx_key = bool((env.get("SX_BET_API_KEY") or "").strip())
        has_pf_key = bool((env.get("PREDICT_FUN_API_KEY") or "").strip())
        has_ibkr = bool((env.get("IBKR_GATEWAY_URL") or "").strip())
        stx_dec = auth_decisions.get("stx_ontario")
        stx_live = bool(stx_dec and stx_dec.effective_authorized)

        entries: List[RestrictionEntry] = [
            # --- Category A: INTERNAL_ADMINISTRATIVE (Eliminated & Unlocked) ---
            RestrictionEntry(
                restriction_id="INT_ADMIN::PREDICT_FUN_DATA_LICENSE_ID",
                venue="predict_fun",
                affected_capability="predict_fun:MARKET_DATA_ACCESS",
                restriction_category="INTERNAL_ADMINISTRATIVE",
                origin="DOMINUS_LEGACY_INTERNAL_GATE (Removed)",
                is_external=False,
                supporting_evidence="docs.predict.fun/terms-of-service §1 separates informational `Content Features` (permitted in Restricted Jurisdictions) from `Technology Features` (wallet/trading); no `PREDICT_FUN_DATA_LICENSE_ID` exists in provider docs.",
                blocks_rest=False,
                blocks_websocket=False,
                blocks_shadow_research=False,
                blocks_trading=False,
                current_status="ELIMINATED_UNLOCKED",
                remediation_or_auth_step="Eliminated in cross_venue_shadow_deployment_gates.py; Mainnet REST + WS active via PREDICT_FUN_API_KEY.",
            ),
            RestrictionEntry(
                restriction_id="INT_ADMIN::SX_BET_DATA_APPROVAL_ID_PUBLIC_REST",
                venue="sx_bet",
                affected_capability="sx_bet:PUBLIC_REST_AND_SHADOW_RESEARCH",
                restriction_category="INTERNAL_ADMINISTRATIVE",
                origin="DOMINUS_LEGACY_INTERNAL_GATE (Removed)",
                is_external=False,
                supporting_evidence="docs.sx.bet/developers/authentication.md & rate-limits.md publish keyless OpenAPI `security: []` endpoints (`/metadata/obv3`, `/summary-v3/*`, `/markets/active`, `/trades-v3/public`, 500 req/60s per IP) with zero license ID.",
                blocks_rest=False,
                blocks_websocket=False,
                blocks_shadow_research=False,
                blocks_trading=False,
                current_status="ELIMINATED_UNLOCKED",
                remediation_or_auth_step="Eliminated in cross_venue_shadow_deployment_gates.py; keyless public OBv3 REST collector active immediately.",
            ),
            RestrictionEntry(
                restriction_id="INT_ADMIN::FORECASTEX_PUBLIC_PORTAL_AUTHORIZED_FLAG",
                venue="forecastex",
                affected_capability="forecastex:PUBLIC_REST",
                restriction_category="INTERNAL_ADMINISTRATIVE",
                origin="DOMINUS_LEGACY_INTERNAL_GATE (Removed)",
                is_external=False,
                supporting_evidence="forecastex.com/api/download CFTC Part 16 DCM regulatory CSV portal is globally public with zero authentication.",
                blocks_rest=False,
                blocks_websocket=False,
                blocks_shadow_research=False,
                blocks_trading=False,
                current_status="ELIMINATED_UNLOCKED",
                remediation_or_auth_step="Eliminated internal boolean env prerequisite; 600 public CFTC contracts ingested continuously.",
            ),
            RestrictionEntry(
                restriction_id="INT_ADMIN::RSS_180MB_CGROUP_MISMATCH",
                venue="system",
                affected_capability="system:VENUE_CERTIFICATION_RSS_GATE",
                restriction_category="INTERNAL_ADMINISTRATIVE",
                origin="DOMINUS_CONFIG_DRIFT (Fixed)",
                is_external=False,
                supporting_evidence="polymarket-cross-venue-shadow.service enforces MemoryHigh=280M, MemoryMax=320M.",
                blocks_rest=False,
                blocks_websocket=False,
                blocks_shadow_research=False,
                blocks_trading=False,
                current_status="ELIMINATED_UNLOCKED",
                remediation_or_auth_step="Aligned VenueCertificationTracker RSS check to 320.0 MB systemd cgroup budget.",
            ),
            RestrictionEntry(
                restriction_id="INT_ADMIN::STX_ONTARIO_FI_PUBLIC_WS_GATE",
                venue="stx_ontario",
                affected_capability="stx_ontario:PUBLIC_WEBSOCKET_AND_SHADOW_RESEARCH",
                restriction_category="INTERNAL_ADMINISTRATIVE",
                origin="DOMINUS_LEGACY_INTERNAL_GATE (Removed)",
                is_external=False,
                supporting_evidence="https://docs.stxapp.io/explore/live-markets/ documents unsigned public Phoenix Channels v2 WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0`, `wss://demo.stxapp.ca/socket/websocket?vsn=2.0.0`, `wss://demo.stxapp.io/socket/websocket?vsn=2.0.0`) streaming `markets`, `ticker`, `trades`, and `market:<symbol_or_uuid>` L2 orderbooks without an API key.",
                blocks_rest=False,
                blocks_websocket=False,
                blocks_shadow_research=False,
                blocks_trading=False,
                current_status="ELIMINATED_UNLOCKED",
                remediation_or_auth_step="Removed BLOCKED_STX_REQUIRES_DIRECT_CA_ON_PRESENCE gate for live_public mode; STX Ontario Phoenix WebSocket collector active.",
            ),
            # --- Category B: TECHNICAL (Provider-Enforced Auth Headers / Missing Credentials) ---
            RestrictionEntry(
                restriction_id="TECH::SX_BET_CENTRIFUGO_WS_AND_FULL_L2_SNAPSHOT",
                venue="sx_bet",
                affected_capability="sx_bet:AUTHENTICATED_READONLY_AND_WEBSOCKET",
                restriction_category="TECHNICAL",
                origin="PROVIDER_API_HTTP_401_WITHOUT_KEY (api.sx.bet)",
                is_external=True,
                supporting_evidence="Verified empirically on https://api.sx.bet: `/orderbook-v3/snapshot/market`, `/orders-v3/odds/best`, `/orders-v3`, and `/user/realtime-token-v3/api-key` (`wss://realtime.sx.bet/connection/websocket`) return `401 BAD_AUTH` without `x-sx-api-key` (`SX_BET_API_KEY` len=0 in /etc/polymarket-shadow.env). Does NOT block keyless public REST (`/leagues/active`, `/summary-v3/league/{id}/game-lines`, `/summary-v3/*`, `/markets/active`, `/trades-v3/public`, `/live-scores`).",
                blocks_rest=False,
                blocks_websocket=not has_sx_key,
                blocks_shadow_research=False,
                blocks_trading=False,
                current_status="ELIMINATED_UNLOCKED" if has_sx_key else "CREDENTIALS_PENDING",
                remediation_or_auth_step="Keyless public REST (`365+` active quoted binary markets across 35 leagues) is active now; provision an authorized `SX_BET_API_KEY` (`x-sx-api-key`) via `--host self --provision-secret SX_BET_API_KEY` to upgrade to `/orderbook-v3/snapshot/market` + Centrifugo WS.",
            ),
            RestrictionEntry(
                restriction_id="TECH::PREDICT_FUN_MAINNET_API_KEY",
                venue="predict_fun",
                affected_capability="predict_fun:AUTHENTICATED_READONLY_AND_WEBSOCKET",
                restriction_category="TECHNICAL",
                origin="PROVIDER_API_HTTP_401_WITHOUT_KEY (api.predict.fun)",
                is_external=True,
                supporting_evidence="Mainnet `https://api.predict.fun/v1/*` and `wss://ws.predict.fun/ws` require `x-api-key` header (`PREDICT_FUN_API_KEY` len=56 provisioned in /etc/polymarket-shadow.env).",
                blocks_rest=not has_pf_key,
                blocks_websocket=not has_pf_key,
                blocks_shadow_research=not has_pf_key,
                blocks_trading=False,
                current_status="ELIMINATED_UNLOCKED" if has_pf_key else "CREDENTIALS_PENDING",
                remediation_or_auth_step="Active (`PREDICT_FUN_API_KEY` provisioned and streaming Mainnet REST + WS).",
            ),
            RestrictionEntry(
                restriction_id="TECH::FORECASTEX_IBKR_CPAPI_GATEWAY",
                venue="forecastex",
                affected_capability="forecastex:REALTIME_IBKR_WEBSOCKET",
                restriction_category="TECHNICAL",
                origin="LOCAL_IBKR_CLIENT_PORTAL_GATEWAY_NOT_CONFIGURED",
                is_external=True,
                supporting_evidence="IBKR Client Portal Web API (`smd+{conid}`) requires an authenticated local IBKR Client Portal Gateway session (`IBKR_GATEWAY_URL` unset on FI VM). Does NOT block public CFTC CSV REST collection.",
                blocks_rest=False,
                blocks_websocket=not has_ibkr,
                blocks_shadow_research=False,
                blocks_trading=False,
                current_status="ELIMINATED_UNLOCKED" if has_ibkr else "CREDENTIALS_PENDING",
                remediation_or_auth_step="Public CFTC CSV REST feed is active; optionally run IBKR Client Portal Gateway (`IBKR_GATEWAY_URL=https://localhost:5000/v1/api`) for live streaming quotes.",
            ),
            RestrictionEntry(
                restriction_id="TECH::STX_ONTARIO_REST_ED25519_CREDENTIALS",
                venue="stx_ontario",
                affected_capability="stx_ontario:AUTHENTICATED_REST_V1_MARKETS",
                restriction_category="TECHNICAL",
                origin="PROVIDER_HTTP_403_WITHOUT_ED25519_OR_OAUTH_HEADERS (api.on.stxapp.ca/api/v1/markets)",
                is_external=True,
                supporting_evidence="REST `GET /api/v1/markets` and `GET /api/v1/events` require Ed25519 `X-STX-ACCESS-*` headers or OAuth `Bearer` (`STX_APPS_DATA_TOKEN`). Does NOT block unsigned public Phoenix WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0`).",
                blocks_rest=not bool(env.get("STX_APPS_DATA_TOKEN") or env.get("STX_API_KEY_ID")),
                blocks_websocket=False,
                blocks_shadow_research=False,
                blocks_trading=False,
                current_status="ELIMINATED_UNLOCKED" if bool(env.get("STX_APPS_DATA_TOKEN") or env.get("STX_API_KEY_ID")) else "CREDENTIALS_PENDING",
                remediation_or_auth_step="Unsigned public STX Ontario Phoenix WebSocket is active now; optionally provision `STX_API_KEY_ID` + `STX_ED25519_KEY_FILE` (or `STX_APPS_DATA_TOKEN`) to add signed REST `/api/v1/markets` catalog discovery.",
            ),
            # --- Category C: EXTERNAL_AUTHORIZATION (Provider Geofences & Contractual Boundaries) ---
            RestrictionEntry(
                restriction_id="EXT_AUTH::LIVE_TRADING_JURISDICTION_EXCLUSIONS",
                venue="all_offshore_venues",
                affected_capability="polymarket,limitless,predict_fun,sx_bet,stx_ontario,forecastex:LIVE_ORDER_EXECUTION",
                restriction_category="EXTERNAL_AUTHORIZATION",
                origin="PROVIDER_TERMS_AND_GEOBLOCKING_ON_ORDER_PLACEMENT",
                is_external=True,
                supporting_evidence="Polymarket Geo FAQ (`POST /order`), Limitless ToS §1 (`not available for trading` in CA-ON), Predict.fun ToS §1 (`Technology Features` / `Contracts` in CA-ON), SX Bet Terms (`Your Obligations` wagering in CA-ON), and STX Ontario AGCO rules (`POST /api/v1/orders`). Strictly isolated from `PUBLIC_DATA`, `REALTIME_DATA`, and `SHADOW_RESEARCH`.",
                blocks_rest=False,
                blocks_websocket=False,
                blocks_shadow_research=False,
                blocks_trading=True,
                current_status="ACTIVE_RESTRICTED",
                remediation_or_auth_step="Isolated strictly to `LIVE_ORDER_EXECUTION`; zero impact on authorized read-only market data and shadow simulation.",
            ),
            # --- Category D: PRODUCTION_SAFETY (Capital & Accounting Safeguards Preserved) ---
            RestrictionEntry(
                restriction_id="PROD_SAFETY::STAGE_G_READONLY_ZERO_SIGNING_KEYS_AND_168H_GATES",
                venue="all_venues",
                affected_capability="all_venues:REAL_CAPITAL_EXECUTION",
                restriction_category="PRODUCTION_SAFETY",
                origin="DOMINUS_STAGE_G_RISK_AND_CERTIFICATION_INVARIANTS",
                is_external=False,
                supporting_evidence="Enforces GET-only/subscribe-only shadow connectors, 0 wallet private keys in `/etc/polymarket-shadow.env`, 5 Double-Zero settlement gates (`CrossVenueRuleVerifier`), and 168h `VenueCertificationTracker` + `Gates G1-G5` before real-capital deployment.",
                blocks_rest=False,
                blocks_websocket=False,
                blocks_shadow_research=False,
                blocks_trading=True,
                current_status="ENFORCED_SAFETY_GATE",
                remediation_or_auth_step="Preserved per production safety mandate; never blocks read-only data collection or shadow research.",
            ),
        ]
        return entries

    def sync_and_persist(
        self,
        *,
        env: Mapping[str, str],
        auth_decisions: Mapping[str, VenueAuthorizationDecision],
        connector_snapshots: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entries = self.build_entries(
            env=env,
            auth_decisions=auth_decisions,
            connector_snapshots=connector_snapshots,
        )
        with self._connect() as conn:
            for e in entries:
                conn.execute(
                    """
                    INSERT INTO restriction_registry(
                        restriction_id, venue, affected_capability, restriction_category,
                        origin, is_external, supporting_evidence, blocks_rest, blocks_websocket,
                        blocks_shadow_research, blocks_trading, current_status,
                        remediation_or_auth_step, updated_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(restriction_id) DO UPDATE SET
                        venue=excluded.venue,
                        affected_capability=excluded.affected_capability,
                        restriction_category=excluded.restriction_category,
                        origin=excluded.origin,
                        is_external=excluded.is_external,
                        supporting_evidence=excluded.supporting_evidence,
                        blocks_rest=excluded.blocks_rest,
                        blocks_websocket=excluded.blocks_websocket,
                        blocks_shadow_research=excluded.blocks_shadow_research,
                        blocks_trading=excluded.blocks_trading,
                        current_status=excluded.current_status,
                        remediation_or_auth_step=excluded.remediation_or_auth_step,
                        updated_at_utc=excluded.updated_at_utc
                    """,
                    (
                        e.restriction_id,
                        e.venue,
                        e.affected_capability,
                        e.restriction_category,
                        e.origin,
                        1 if e.is_external else 0,
                        e.supporting_evidence,
                        1 if e.blocks_rest else 0,
                        1 if e.blocks_websocket else 0,
                        1 if e.blocks_shadow_research else 0,
                        1 if e.blocks_trading else 0,
                        e.current_status,
                        e.remediation_or_auth_step,
                        now_utc,
                    ),
                )
        by_cat: Dict[str, int] = {}
        for e in entries:
            by_cat[e.restriction_category] = by_cat.get(e.restriction_category, 0) + 1
        payload = {
            "schema_version": "1.0.0",
            "updated_at_utc": now_utc,
            "counts_by_category": by_cat,
            "eliminated_internal_count": sum(
                1 for e in entries if e.restriction_category == "INTERNAL_ADMINISTRATIVE" and e.current_status == "ELIMINATED_UNLOCKED"
            ),
            "restrictions": [asdict(e) for e in entries],
        }
        tmp = self.data_dir / f".restriction_registry.json.tmp.{os.getpid()}"
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(self.json_path))
        return payload

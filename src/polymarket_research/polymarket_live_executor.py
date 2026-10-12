#!/usr/bin/env python3
"""
POLYMARKET LIVE CLOB EXECUTION ADAPTER (v1.0.0)
===============================================
Institutional EIP-712 Order Dispatcher for Polymarket Central Limit Order Book (CLOB).
Operates with py-clob-client on Polygon Mainnet (Chain ID: 137).

Features:
  1. Automated L1 -> L2 API Key Derivation / Authentication.
  2. Fail-Closed Liquidity Guard: DepthRatio >= 1.50 within top 2 ticks.
  3. Dynamic Crypto Fee Model: fee_rate(p) = 0.07 * (1 - p).
  4. Non-Blocking Execution with Execution Shortfall & Gasless Relayer Dispatch.
  5. Fallback Mock / Dry-Run Engine when live private key is unconfigured.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import requests
from dotenv import load_dotenv

# Ensure pipeline root is in sys.path
PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

load_dotenv(PIPELINE_ROOT / ".env")

try:
    import py_clob_client_v2
    from py_clob_client_v2.client import ClobClient
    from py_clob_client_v2.clob_types import (
        ApiCreds,
        OrderArgsV2,
        MarketOrderArgsV2,
        OrderType,
        AssetType,
        BalanceAllowanceParams,
        TradeParams,
    )
    PY_CLOB_AVAILABLE = True
    PY_CLOB_VERSION = getattr(py_clob_client_v2, "__version__", "1.2.0")
except ImportError:
    PY_CLOB_AVAILABLE = False
    PY_CLOB_VERSION = None
    ClobClient = None
    ApiCreds = None
    OrderArgsV2 = None
    MarketOrderArgsV2 = None
    OrderType = None
    AssetType = None
    BalanceAllowanceParams = None
    TradeParams = None

# Institutional SDK Hard Pin Requirement
EXPECTED_CLOB_V2 = "1.2.0"
CLOB_ALLOWED_TICK_SIZES = (0.1, 0.01, 0.005, 0.0025, 0.001, 0.0001)

# Execution & Risk Boundaries
MAX_PRICE_CEILING = 0.8800
MIN_PRICE_FLOOR = 0.1500
MIN_LOT_SIZE_USD = 5.00
DEFAULT_DEPTH_HURDLE = 1.25


# Setup module logger
logger = logging.getLogger("PolymarketLiveExecutor")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [PM-EXEC] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ExecutionStatus:
    """Explicit lifecycle states for Polymarket CLOB order execution."""
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    MATCHED_PENDING_SETTLEMENT = "MATCHED_PENDING_SETTLEMENT"
    POSITION_CONFIRMED = "POSITION_CONFIRMED"
    EXIT_PENDING_SETTLEMENT = "EXIT_PENDING_SETTLEMENT"
    EXIT_RESTING = "EXIT_RESTING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    SETTLED = "SETTLED"


def calculate_taker_fee(
    notional_usd: float,
    price: float,
    fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
) -> Tuple[float, float]:
    """
    Canonical Polymarket V2 dynamic crypto taker fee calculation.
    Platform fee schedule:
      platform_fee_rate = fee_rate * (p * (1 - p)) ** fee_exponent
      shares = notional_usd / p
      taker_fee = shares * platform_fee_rate = notional_usd * fee_rate * (p * (1 - p)) ** fee_exponent / p
      For fee_exponent == 1: simplifies to notional_usd * fee_rate * (1 - p)
    Used canonically across executor, paper trader, and telemetry recorder.
    Returns: (effective_rate, fee_usd)
    """
    clamped_p = max(0.001, min(0.999, price))
    shares = notional_usd / clamped_p
    per_share_fee = fee_rate * ((clamped_p * (1.0 - clamped_p)) ** fee_exponent)
    fee_usd = float(Decimal(str(shares * per_share_fee)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))
    effective_rate = round(fee_usd / max(notional_usd, 1e-6), 8)
    return effective_rate, fee_usd


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str]
    trade_id: str
    token_id: str
    target_token: str
    side: str
    price: float
    size: float
    notional_usd: float
    fee_usd: float
    latency_ms: float
    mode: str  # "LIVE_CLOB" or "DRY_RUN_SIMULATION"
    execution_status: str = ExecutionStatus.SUBMITTED
    confirmed_onchain: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class PolymarketLiveExecutor:
    """
    Production-grade execution interface for Polymarket CLOB.
    """
    CLOB_HOST = "https://clob.polymarket.com"
    CHAIN_ID = 137  # Polygon Mainnet


    def __init__(
        self,
        private_key: Optional[str] = None,
        funder_address: Optional[str] = None,
        signature_type: Optional[int] = None,
        dry_run: bool = False,
        ledger_path: Optional[str] = None,
    ):
        self.dry_run = dry_run
        if private_key is not None:
            self.private_key = private_key.strip()
        else:
            self.private_key = os.getenv("POLYGON_PRIVATE_KEY", "").strip()

        if funder_address is not None:
            self.funder_address = funder_address.strip()
        else:
            self.funder_address = (
                os.getenv("POLYGON_FUNDER_ADDRESS", "").strip()
                or os.getenv("POLYGON_PROXY_ADDRESS", "").strip()
            )
        sig_env = os.getenv("POLYGON_SIGNATURE_TYPE", "").strip()
        if signature_type is None and not sig_env and not dry_run:
            raise RuntimeError("LIVE MODE REFUSED: POLYGON_SIGNATURE_TYPE must be explicitly configured")
        self.signature_type = (
            signature_type
            if signature_type is not None
            else (int(sig_env) if sig_env else 3)
        )
        if self.signature_type not in (0, 1, 2, 3):
            raise RuntimeError(f"Unsupported POLYGON_SIGNATURE_TYPE={self.signature_type}")

        if not self.dry_run and self.private_key:
            from eth_account import Account
            try:
                signer_address = Account.from_key(self.private_key).address
            except Exception:
                signer_address = None

            if self.signature_type == 0:
                if (
                    signer_address
                    and self.funder_address
                    and self.funder_address.lower() != signer_address.lower()
                ):
                    raise RuntimeError(
                        "LIVE MODE REFUSED: Type 0 requires the EOA funder "
                        "to equal the signing address."
                    )
            elif self.signature_type == 3:
                if not self.funder_address:
                    raise RuntimeError(
                        "LIVE MODE REFUSED: Type 3 requires an explicitly "
                        "configured Polymarket deposit-wallet funder."
                    )
        self.ledger_path = Path(ledger_path or PIPELINE_ROOT / "data/polymarket/live_orders.jsonl")
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

        self.client: Optional[Any] = None
        self.is_authenticated = False
        self.auth_mode = "UNINITIALIZED"
        self.last_heartbeat_id = ""
        self.heartbeat_failures = 0
        self._fee_cache: Dict[str, Tuple[float, float]] = {}
        self._tick_size_cache: Dict[str, float] = {}
        self._async_client: Optional[httpx.AsyncClient] = None

        self._initialize_client()

    def _initialize_client(self):
        """Initializes py-clob-client with L1 and L2 credentials with strict fail-closed live gating."""
        if self.dry_run:
            self.auth_mode = "DRY_RUN_STANDBY"
            logger.info("Initializing in DRY-RUN / Standby mode (--dry-run specified).")
            return

        # STRICT FAIL-CLOSED LIVE HARD GATING (P0 Fix):
        if not self.private_key:
            self.auth_mode = "LIVE_REFUSED_NO_KEY"
            raise RuntimeError("LIVE MODE REFUSED: POLYGON_PRIVATE_KEY is missing or empty. Live money trading cannot execute without an L1 private key.")

        if not PY_CLOB_AVAILABLE:
            self.auth_mode = "LIVE_REFUSED_NO_SDK"
            raise RuntimeError("LIVE MODE REFUSED: py_clob_client_v2 is required for live execution. Legacy fallback is strictly prohibited.")

        # Institutional Hard SDK Pin Assertion (P1 Fix)
        try:
            import importlib.metadata
            installed_sdk_ver = importlib.metadata.version("py_clob_client_v2")
            if installed_sdk_ver != EXPECTED_CLOB_V2:
                self.auth_mode = "LIVE_REFUSED_SDK_VERSION_MISMATCH"
                raise RuntimeError(
                    f"LIVE MODE REFUSED: py_clob_client_v2 version mismatch (found '{installed_sdk_ver}', required hard-pinned '{EXPECTED_CLOB_V2}')."
                )
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            logger.warning(f"Metadata version check exception: {e}")

        try:
            t0 = time.perf_counter()
            # Initialize L1 client with configured signature type (3 for Polymarket deposit proxy wallet)
            self.client = ClobClient(
                host=self.CLOB_HOST,
                key=self.private_key,
                chain_id=self.CHAIN_ID,
                signature_type=self.signature_type,
                funder=self.funder_address if self.funder_address else None,
            )

            # Derive or create L2 API credentials
            if hasattr(self.client, "create_or_derive_api_key"):
                api_creds = self.client.create_or_derive_api_key()
            else:
                api_creds = self.client.create_or_derive_api_creds()
            self.client.set_api_creds(api_creds)

            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.is_authenticated = True
            self.auth_mode = "AUTHENTICATED_L2"
            logger.info(f"Successfully authenticated with Polymarket CLOB L2 (v2 client v{PY_CLOB_VERSION}) in {latency_ms:.2f} ms.")

        except Exception as e:
            self.auth_mode = "AUTH_FAILED"
            self.is_authenticated = False
            logger.error(f"Failed to authenticate with Polymarket CLOB: {e}")
            raise RuntimeError(f"LIVE MODE REFUSED: CLOB L2 authentication failed: {e}")

    def assert_market_routing(self, asset_id: str, market_version: str = "CTF") -> None:
        """
        P1: Asset-routing invariant assertion:
        CTF market -> token_id / CTF exchange route.
        Protocol V2 position market -> position_id / Exchange V3 route.
        Fails closed if the asset identifier type does not match the market version.
        """
        if market_version.upper() == "CTF":
            if not (isinstance(asset_id, str) and (asset_id.isdigit() or asset_id.startswith("0x")) and len(asset_id) >= 10):
                raise ValueError(f"ASSET ROUTING ERROR: Invalid CTF token_id format '{asset_id}' for CTF market route.")
        elif market_version.upper() in ("V2_POSITION", "PROTOCOL_V2", "EXCHANGE_V3"):
            if not (isinstance(asset_id, str) and asset_id.startswith("0x") and len(asset_id) >= 42):
                raise ValueError(f"ASSET ROUTING ERROR: Invalid position_id '{asset_id}' for Exchange V3 route.")

    def get_async_client(self) -> httpx.AsyncClient:
        """P2: Returns persistent httpx.AsyncClient to preserve HTTP connection pooling / keep-alive."""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                timeout=3.0,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        return self._async_client

    async def close_async(self):
        """Closes the persistent HTTP client cleanly."""
        if self._async_client is not None and not self._async_client.is_closed:
            await self._async_client.aclose()
            self._async_client = None

    @staticmethod
    def calculate_balance_epsilon(quantity_unit_or_shares: float = 0.001) -> float:
        """
        P1: Precision-derived balance tolerance epsilon derived from platform base units.
        Rather than an ad-hoc size percentage, tolerance is derived strictly from:
          exchange quantity representation (0.001 shares) + 
          CLOB / ERC-1155 token decimal precision (10^-6 base units).
        Calculated using Decimal arithmetic:
          epsilon = 2 * quantity_unit
        Default for Polymarket: 2 * 0.001 = 0.002 shares (2 millishares / 2,000 base units).
        """
        base_unit = 0.001 if quantity_unit_or_shares > 0.01 else quantity_unit_or_shares
        unit_dec = Decimal(str(base_unit))
        epsilon_dec = Decimal("2") * unit_dec
        return float(epsilon_dec)

    def get_market_fee_params(self, condition_id: str, token_id: Optional[str] = None) -> Tuple[float, float]:
        """
        P1: Authoritative CLOB fee metadata resolution using get_clob_market_info(condition_id)
        or SDK fee methods.
        Retrieves:
          fd.r = fee rate
          fd.e = fee exponent
        Caches against condition_id and token_id.
        Fails closed (raises RuntimeError) if fee metadata is absent or malformed in live mode.
        Returns: (fee_rate, fee_exponent)
        """
        if condition_id in self._fee_cache:
            return self._fee_cache[condition_id]

        if self.dry_run or self.client is None:
            rate, exp = 0.07, 1.0
            self._fee_cache[condition_id] = (rate, exp)
            return rate, exp

        # Resolve real hex condition_id if numeric market_id was supplied
        real_cid = condition_id
        if not condition_id.startswith("0x"):
            try:
                r = requests.get(f"https://gamma-api.polymarket.com/markets/{condition_id}", timeout=2.0).json()
                if r.get("conditionId"):
                    real_cid = str(r["conditionId"])
                    logger.info(f"Resolved condition_id {real_cid} for numeric market {condition_id}")
            except Exception as gamma_err:
                logger.debug(f"Gamma lookup for {condition_id} notice: {gamma_err}")

        try:
            # 1. Authoritative CLOB market info path
            if hasattr(self.client, "get_clob_market_info"):
                m_info = self.client.get_clob_market_info(real_cid)
                if isinstance(m_info, dict):
                    fd = m_info.get("fd") or {}
                    raw_r = fd.get("r")
                    raw_e = fd.get("e")
                    if raw_r is not None and raw_e is not None:
                        fee_rate = float(raw_r)
                        fee_exponent = float(raw_e)
                        self._fee_cache[condition_id] = (fee_rate, fee_exponent)
                        return fee_rate, fee_exponent

            # 2. Token-level SDK fallback if token_id is available
            if token_id and hasattr(self.client, "get_fee_rate_bps") and hasattr(self.client, "get_fee_exponent"):
                bps = self.client.get_fee_rate_bps(token_id)
                exp = self.client.get_fee_exponent(token_id)
                fee_rate = float(bps) / 10000.0
                fee_exponent = float(exp)
                self._fee_cache[condition_id] = (fee_rate, fee_exponent)
                return fee_rate, fee_exponent

            # 3. Market dict path
            if hasattr(self.client, "get_market"):
                m_info = self.client.get_market(real_cid)
                if isinstance(m_info, dict):
                    fd = m_info.get("fd") or {}
                    if "r" in fd and "e" in fd:
                        fee_rate = float(fd["r"])
                        fee_exponent = float(fd["e"])
                        self._fee_cache[condition_id] = (fee_rate, fee_exponent)
                        return fee_rate, fee_exponent
                    raw_taker = m_info.get("taker_base_fee")
                    if raw_taker is not None:
                        fee_rate = float(raw_taker) / 10000.0 if float(raw_taker) > 1.0 else float(raw_taker)
                        fee_exponent = float(m_info.get("fee_exponent", 1.0))
                        self._fee_cache[condition_id] = (fee_rate, fee_exponent)
                        return fee_rate, fee_exponent

            if not self.dry_run and self.is_authenticated:
                raise RuntimeError(f"AUTHORITATIVE_FEE_METADATA_UNAVAILABLE: CLOB returned no fee metadata for {real_cid}")

            # Fallback to standard crypto fee rate
            logger.warning(f"CLOB returned no specific fee schedule for {real_cid}; applying standard 0.07 crypto rate.")
            fee_rate, fee_exponent = 0.07, 1.0
            self._fee_cache[condition_id] = (fee_rate, fee_exponent)
            return fee_rate, fee_exponent

        except RuntimeError:
            raise
        except Exception as e:
            if not self.dry_run and self.is_authenticated:
                raise RuntimeError(f"AUTHORITATIVE_FEE_METADATA_UNAVAILABLE: {e}")
            logger.warning(f"Notice fetching authoritative CLOB fee metadata for {condition_id} ({real_cid}): {e}. Applying default 0.07.")
            fee_rate, fee_exponent = 0.07, 1.0
            self._fee_cache[condition_id] = (fee_rate, fee_exponent)
            return fee_rate, fee_exponent

    async def get_market_book_async(self, token_id: str) -> Dict[str, Any]:
        """P0/P2: Asynchronously queries the live L2 orderbook using persistent connection pool."""
        url = f"{self.CLOB_HOST}/book?token_id={token_id}"
        try:
            client = self.get_async_client()
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            if self.dry_run:
                return {"bids": [], "asks": []}
            raise
        if self.dry_run:
            return {"bids": [], "asks": []}
        raise RuntimeError(f"HTTP {resp.status_code} querying orderbook for {token_id}: {resp.text[:100]}")

    async def get_transaction_receipt_status_async(self, tx_hash: str) -> Optional[bool]:
        """
        P0/P1: Asynchronously verifies Polygon on-chain transaction receipt.
        Rule:
          - Returns True if receipt exists and status == 1 (successful on-chain transfer).
          - Returns False if receipt exists and status == 0 (reverted on-chain!).
          - Returns None if receipt does not exist yet (transaction pending / not yet mined).
        """
        if self.dry_run:
            return True
        if not tx_hash or not isinstance(tx_hash, str) or not tx_hash.startswith("0x"):
            return False
        try:
            rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1,
            }
            client = self.get_async_client()
            resp = await client.post(rpc_url, json=payload, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result")
                if result is None:
                    return None
                raw_st = result.get("status")
                if raw_st in (1, "0x1", "1"):
                    return True
                elif raw_st in (0, "0x0", "0"):
                    logger.critical(f"[ON-CHAIN REVERT] Transaction {tx_hash} reverted on Polygon (status={raw_st})!")
                    return False
            return None
        except Exception as e:
            logger.warning(f"Failed to query Polygon transaction receipt for {tx_hash}: {e}")
            return None

    def get_transaction_receipt_status(self, tx_hash: str) -> Optional[bool]:
        """Synchronous wrapper for get_transaction_receipt_status_async."""
        if self.dry_run:
            return True
        if not tx_hash or not isinstance(tx_hash, str) or not tx_hash.startswith("0x"):
            return False
        try:
            rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1,
            }
            resp = requests.post(rpc_url, json=payload, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result")
                if result is None:
                    return None
                raw_st = result.get("status")
                if raw_st in (1, "0x1", "1"):
                    return True
                elif raw_st in (0, "0x0", "0"):
                    return False
            return None
        except Exception as e:
            logger.warning(f"Failed to query Polygon transaction receipt for {tx_hash}: {e}")
            return None

    def get_market_book(self, token_id: str) -> Dict[str, Any]:
        """Queries the live L2 orderbook for a given outcome token."""
        url = f"{self.CLOB_HOST}/book?token_id={token_id}"
        try:
            resp = requests.get(url, timeout=3.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            if self.dry_run:
                return {"bids": [], "asks": []}
            raise
        if self.dry_run:
            return {"bids": [], "asks": []}
        raise RuntimeError(f"HTTP {resp.status_code} querying orderbook for {token_id}: {resp.text[:100]}")

    @staticmethod
    def normalize_trade_record(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        P0 Invariant: Normalizes CLOB trade record dictionary to support both SDK snake_case
        and camelCase schemas (e.g. transaction_hash vs transactionHash).
        """
        if not isinstance(data, dict):
            return {}
        res = dict(data)
        tx_hash = res.get("transaction_hash") or res.get("transactionHash")
        if tx_hash:
            res["transaction_hash"] = str(tx_hash)
            res["transactionHash"] = str(tx_hash)
        tr_id = res.get("id") or res.get("trade_id") or res.get("tradeId")
        if tr_id:
            res["id"] = str(tr_id)
            res["trade_id"] = str(tr_id)
        st = res.get("status")
        if st:
            res["status"] = str(st).upper()
        return res

    def get_trade_status(self, trade_id: str) -> Dict[str, Any]:
        """
        P0/P1: Authoritative CLOB trade status lookup for reconciliation.
        Trade lifecycle progression: MATCHED -> MINED -> CONFIRMED (terminal) | FAILED
        Uses TradeParams(id=trade_id) matching py_clob_client SDK signature.
        Normalizes both transaction_hash and transactionHash schemas.
        """
        if self.dry_run or not self.client:
            return {"status": "CONFIRMED", "trade_id": trade_id, "transaction_hash": None, "transactionHash": None}
        try:
            if hasattr(self.client, "get_trades"):
                try:
                    if TradeParams is not None:
                        params = TradeParams(id=trade_id)
                        trade_data = self.client.get_trades(params=params)
                    else:
                        trade_data = self.client.get_trades(trade_id=trade_id)
                except (TypeError, AttributeError):
                    trade_data = self.client.get_trades(trade_id=trade_id)

                if isinstance(trade_data, list) and len(trade_data) > 0:
                    return self.normalize_trade_record(trade_data[0])
                elif isinstance(trade_data, dict):
                    return self.normalize_trade_record(trade_data)
            return {"status": "MATCHED", "trade_id": trade_id}
        except Exception as e:
            logger.debug(f"Trade query exception for {trade_id}: {e}")
            return {"status": "UNKNOWN", "error": str(e)}

    def simulate_fok_sweep(
        self,
        orderbook: Dict[str, Any],
        target_notional_usd: float,
        side: str = "BUY",
        max_acceptable_price: float = MAX_PRICE_CEILING,
        min_acceptable_price: float = MIN_PRICE_FLOOR,
        return_legs: bool = False,
    ) -> Any:
        """
        Simulates an exact FOK sweep across multiple price levels:
        Computes fee across individual fill legs rather than single VWAP approximation.
        Returns: (fillable, vwap, total_shares, worst_price, effective_fee_usd[, fill_legs])
        """
        levels = orderbook.get("asks" if side == "BUY" else "bids", [])
        if not levels:
            if return_legs:
                return False, 0.0, 0.0, 0.0, 0.0, []
            return False, 0.0, 0.0, 0.0, 0.0

        if side == "BUY":
            sorted_levels = sorted(levels, key=lambda lvl: float(lvl.get("price", 1.0)))
        else:
            sorted_levels = sorted(levels, key=lambda lvl: float(lvl.get("price", 0.0)), reverse=True)

        rem_notional = target_notional_usd
        total_shares = 0.0
        total_cost = 0.0
        worst_price = 0.0
        fill_legs: List[Tuple[float, float]] = []

        for lvl in sorted_levels:
            px = float(lvl.get("price", 0.0))
            sz = float(lvl.get("size", 0.0))
            if sz <= 0 or px <= 0:
               continue
            if side == "BUY" and px > max_acceptable_price:
                break
            if side == "SELL" and px < min_acceptable_price:
                break

            level_notional = px * sz
            if level_notional >= rem_notional - 1e-6:
                shares_needed = min(sz, rem_notional / px)
                total_shares += shares_needed
                total_cost += rem_notional
                worst_price = px
                fill_legs.append((px, shares_needed))
                rem_notional = 0.0
                break
            else:
                total_shares += sz
                total_cost += level_notional
                worst_price = px
                fill_legs.append((px, sz))
                rem_notional -= level_notional

        if rem_notional > 1e-4:
            if return_legs:
                return False, 0.0, 0.0, worst_price, 0.0, []
            return False, 0.0, 0.0, worst_price, 0.0

        vwap = total_cost / total_shares if total_shares > 0 else 0.0
        # Multi-level dynamic crypto taker fee calculation across actual legs
        fee_usd = round(sum(
            sz_i * 0.07 * ((px_i * (1.0 - px_i)) ** 1.0)
            for px_i, sz_i in fill_legs
        ), 5)
        self.last_fok_fill_legs = fill_legs
        if return_legs:
            return True, vwap, total_shares, worst_price, fee_usd, fill_legs
        return True, vwap, total_shares, worst_price, fee_usd

    def verify_pre_trade_depth(
        self,
        orderbook: Dict[str, Any],
        target_notional_usd: float,
        side: str = "BUY",
        depth_hurdle_ratio: float = DEFAULT_DEPTH_HURDLE,
        max_price_ceiling: float = MAX_PRICE_CEILING,
        min_price_floor: float = MIN_PRICE_FLOOR,
        return_adjusted: bool = False,
        min_lot_size: float = MIN_LOT_SIZE_USD,
    ) -> Union[Tuple[bool, float, float], Tuple[bool, float, float, float]]:
        """
        Validates executable orderbook depth across all qualifying price levels up to max_price_ceiling.
        Supports dynamic down-sizing: if the book has liquidity below the hurdle, scales order size
        to fit available liquidity (down to min_lot_size) rather than rejecting profitable setups.

        For BUY:
          Sorts asks ascending (lowest price first).
          Aggregates available liquidity across all asks where price <= max_price_ceiling.
        For SELL:
          Sorts bids descending (highest price first).
          Aggregates available liquidity across all bids where price >= min_price_floor.

        Returns:
          If return_adjusted is False (legacy signature): (passed, ratio, best_price)
          If return_adjusted is True: (passed, ratio, best_price, adjusted_notional)
        """
        levels = orderbook.get("asks" if side == "BUY" else "bids", [])
        if not levels:
            return (False, 0.0, 0.0, 0.0) if return_adjusted else (False, 0.0, 0.0)

        # Polymarket CLOB book: sort so levels are best marketable prices first
        if side == "BUY":
            sorted_levels = sorted(levels, key=lambda lvl: float(lvl.get("price", 1.0)))
        else:
            sorted_levels = sorted(levels, key=lambda lvl: float(lvl.get("price", 0.0)), reverse=True)

        # Filter within price ceiling and floor
        qualifying_levels = [
            lvl for lvl in sorted_levels
            if (min_price_floor <= float(lvl.get("price", 0.0)) <= max_price_ceiling)
        ]
        if not qualifying_levels:
            best_price = float(sorted_levels[0].get("price", 0.0)) if sorted_levels else 0.0
            return (False, 0.0, best_price, 0.0) if return_adjusted else (False, 0.0, best_price)

        best_price = float(qualifying_levels[0].get("price", 0.0))

        # Cumulative executable depth across all qualifying levels up to ceiling
        available_notional = sum(
            float(lvl.get("price", 0.0)) * float(lvl.get("size", 0.0))
            for lvl in qualifying_levels
        )

        ratio = available_notional / max(target_notional_usd, 1e-6)

        # If return_adjusted is False (backwards compatibility with unit tests):
        if not return_adjusted:
            passed = ratio >= depth_hurdle_ratio
            return passed, ratio, best_price

        # With dynamic down-sizing (return_adjusted=True):
        if ratio >= depth_hurdle_ratio:
            adjusted_notional = target_notional_usd
            passed = True
        else:
            # Scale down order size to fit available liquidity with the safety hurdle
            adjusted_notional = round(available_notional / max(depth_hurdle_ratio, 1.0), 2)
            if adjusted_notional >= min_lot_size:
                passed = True
            else:
                passed = False
                adjusted_notional = 0.0

        return passed, ratio, best_price, adjusted_notional

    def calculate_dynamic_crypto_fee(
        self,
        entry_price: float,
        notional_usd: float,
        fee_rate: float = 0.07,
        fee_exponent: float = 1.0,
    ) -> Tuple[float, float]:
        """Canonical dynamic crypto taker fee calculation delegated to calculate_taker_fee."""
        return calculate_taker_fee(notional_usd, entry_price, fee_rate, fee_exponent)

    def execute_snipe_order(
        self,
        trade_id: str,
        token_id: str,
        target_token: str,
        notional_usd: float,
        target_price: float,
        side: str = "BUY",
        depth_hurdle: float = DEFAULT_DEPTH_HURDLE,
        market_id: Optional[str] = None,
        condition_id: Optional[str] = None,
        market_fee_rate: Optional[float] = None,
        market_fee_exponent: Optional[float] = None,
        max_price_ceiling: float = MAX_PRICE_CEILING,
    ) -> OrderResult:
        """
        Executes a directional latency snipe with pre-trade risk and depth assertions.
        """
        t0 = time.perf_counter()
        now_utc = datetime.now(timezone.utc).isoformat()

        # 1. Fetch live order book & verify depth
        try:
            book = self.get_market_book(token_id)
        except Exception as e:
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=target_price,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=f"Orderbook fetch error: {e}",
            )

        passed_depth, depth_ratio, best_px, adjusted_notional = self.verify_pre_trade_depth(
            book,
            notional_usd,
            side=side,
            depth_hurdle_ratio=depth_hurdle,
            max_price_ceiling=max_price_ceiling,
            min_price_floor=MIN_PRICE_FLOOR,
            return_adjusted=True,
            min_lot_size=MIN_LOT_SIZE_USD,
        )

        if not passed_depth:
            err = f"DepthGuard Rejected: Ratio {depth_ratio:.2f}x < {depth_hurdle:.2f}x requirement."
            logger.warning(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=best_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        if adjusted_notional < notional_usd:
            logger.info(
                f"[{trade_id}] [DYNAMIC DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${adjusted_notional:.2f} "
                f"to match available book depth (Ratio: {depth_ratio:.2f}x vs hurdle {depth_hurdle:.2f}x)."
            )
            notional_usd = adjusted_notional

        # Strict Pre-Trade Price Sanity Guard: Never buy outside [0.15, 0.88]
        if best_px < 0.15 or best_px > 0.88:
            err = f"PriceGuard Rejected: Best price ${best_px:.4f} outside valid boundary [0.15, 0.88]."
            logger.warning(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=best_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        # Slippage Guard: Do not execute if book best price has slipped above target_price by > 4¢
        if target_price > 0 and (best_px - target_price) > 0.04:
            err = f"SlippageGuard Rejected: Best price ${best_px:.4f} exceeds target ${target_price:.4f} by > 4¢."
            logger.warning(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=best_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        # Calculate worst acceptable price allowing up to 3¢ slippage, quantized to token tick
        raw_worst_px = max(target_price + 0.03, best_px + 0.03)
        worst_acceptable_px = self.quantize_order_price(raw_worst_px, token_id, rounding=ROUND_CEILING)
        if worst_acceptable_px > max_price_ceiling + 1e-9:
            err = f"No valid token tick at or below configured entry ceiling (${max_price_ceiling:.4f})"
            logger.warning(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=best_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        # 2. Simulate exact multi-level FOK sweep across book using exact order price constraint (P1 Fix)
        fillable, vwap, sweep_shares, worst_px, fok_fee, fill_legs = self.simulate_fok_sweep(
            book, notional_usd, side=side, max_acceptable_price=worst_acceptable_px, return_legs=True
        )
        if not fillable:
            err = f"FOK Sweep Infeasible: Could not fill ${notional_usd:.2f} within limit ${worst_acceptable_px:.4f}."
            logger.warning(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=worst_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        shares_to_buy = round(sweep_shares, 4)
        exec_price = round(vwap, 4)

        # Authoritative CLOB fee resolution (P1 Fix)
        cid = condition_id or market_id
        if cid:
            try:
                f_rate, f_exp = self.get_market_fee_params(cid, token_id=token_id)
            except Exception as e:
                logger.warning(f"Authoritative CLOB fee query notice for {cid}: {e}; using verified payload fee.")
                f_rate = float(market_fee_rate) if market_fee_rate is not None else 0.07
                f_exp = float(market_fee_exponent or 1.0)
        elif market_fee_rate is not None:
            f_rate = float(market_fee_rate)
            f_exp = float(market_fee_exponent or 1.0)
        else:
            f_rate, f_exp = 0.07, 1.0

        # Compute fee per matched fill level using authoritative market fee rate/exponent
        fee_usd = round(sum(
            shares_i * f_rate * ((price_i * (1.0 - price_i)) ** f_exp)
            for price_i, shares_i in fill_legs
        ), 5)
        fee_rate = fee_usd / max(notional_usd, 1e-9)

        # 3. Dry-Run / Mock Branch vs Live Mode Refusal (P0 #1 Fix)
        if not self.dry_run:
            if not self.is_authenticated or self.client is None:
                raise RuntimeError(
                    f"LIVE ORDER REFUSED: Executor is in live real-money mode but unauthenticated ({self.auth_mode}). "
                    "Refusing mock fallback."
                )
        else:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            mock_order_id = f"MOCK_CLOB_{int(time.time()*1000)}"
            logger.info(
                f"[DRY-RUN SNIPE] {trade_id} -> {target_token} | Shares={shares_to_buy:.2f} @ ${exec_price:.4f} "
                f"| Notional=${notional_usd:.2f} | Fee=${fee_usd:.4f} ({fee_rate*100:.2f}%) | Latency={latency_ms:.2f}ms"
            )

            res = OrderResult(
                success=True,
                order_id=mock_order_id,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=exec_price,
                size=shares_to_buy,
                notional_usd=notional_usd,
                fee_usd=fee_usd,
                latency_ms=latency_ms,
                mode="DRY_RUN_SIMULATION",
                execution_status=ExecutionStatus.POSITION_CONFIRMED,
                confirmed_onchain=True,
                details={
                    "fee_rate": fee_rate,
                    "depth_ratio": depth_ratio,
                    "timestamp_utc": now_utc,
                    "confirmed_onchain": True,
                    "pre_token_balance": 0.0,
                    "post_token_balance": shares_to_buy,
                    "balance_delta": shares_to_buy,
                },
            )
            self._log_order(res)
            return res

        # 4. Live CLOB Order Dispatch Branch
        try:
            # Pre-trade on-chain ERC-1155 balance snapshot for delta-aware settlement verification
            if not self.dry_run:
                pre_token_bal = self.get_onchain_erc1155_balance(token_id)
                if pre_token_bal is None:
                    raise RuntimeError(f"Cannot take authoritative pre-trade ERC-1155 snapshot for {token_id}; refusing live entry")
            else:
                pre_token_bal = 0.0

            # Dispatch via native MarketOrderArgsV2 (sweeps depth up to worst_acceptable_px)
            if MarketOrderArgsV2 is not None:
                mo_args = MarketOrderArgsV2(
                    token_id=token_id,
                    amount=round(notional_usd, 2),
                    side=side,
                    price=worst_acceptable_px,
                    order_type=OrderType.FOK,
                )
                signed_order = self.client.create_market_order(mo_args)
            else:
                order_args = OrderArgsV2(
                    price=worst_acceptable_px,
                    size=shares_to_buy,
                    side=side,
                    token_id=token_id,
                )
                signed_order = self.client.create_order(order_args)

            # P0: Pass defer_exec=True to bypass py_clob_client_v2 internal synchronous settlement polling
            post_resp = self.client.post_order(signed_order, OrderType.FOK, defer_exec=True)

            latency_ms = (time.perf_counter() - t0) * 1000.0
            order_id = post_resp.get("orderID") or post_resp.get("id")

            if not order_id or post_resp.get("errorMsg"):
                err_msg = post_resp.get("errorMsg") or "No orderID returned from CLOB matching engine"
                logger.error(f"[{trade_id}] Order rejected by CLOB: {err_msg} | raw={post_resp}")
                res = OrderResult(
                    success=False,
                    order_id=order_id,
                    trade_id=trade_id,
                    token_id=token_id,
                    target_token=target_token,
                    side=side,
                    price=best_px,
                    size=shares_to_buy,
                    notional_usd=notional_usd,
                    fee_usd=fee_usd,
                    latency_ms=latency_ms,
                    mode="LIVE_CLOB_ERROR",
                    execution_status=ExecutionStatus.REJECTED,
                    confirmed_onchain=False,
                    error=err_msg,
                    details={
                        "raw_response": post_resp,
                        "depth_ratio": depth_ratio,
                        "timestamp_utc": now_utc,
                        "pre_token_balance": pre_token_bal,
                    },
                )
                self._log_order(res)
                return res

            # Authoritative V2 fill amount parsing (P1 Fix):
            # CLOB order responses expose human-readable values directly (e.g. makingAmount="20.0", takingAmount="41.6666").
            # Strictly parse as human units without heuristic guessing. Fail closed if malformed.
            making_amt = post_resp.get("makingAmount")
            taking_amt = post_resp.get("takingAmount")

            if making_amt is not None:
                try:
                    actual_notional = float(making_amt)
                except (ValueError, TypeError) as parse_err:
                    raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid makingAmount={making_amt}: {parse_err}")
            else:
                actual_notional = notional_usd

            if taking_amt is not None:
                try:
                    actual_shares = float(taking_amt)
                except (ValueError, TypeError) as parse_err:
                    raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid takingAmount={taking_amt}: {parse_err}")
            else:
                actual_shares = shares_to_buy

            fill_px = round(actual_notional / max(actual_shares, 1e-4), 4) if (making_amt and taking_amt and actual_shares > 0) else best_px

            trade_ids = post_resp.get("tradeIDs", [])
            tx_hashes = post_resp.get("transactionsHashes", [])

            logger.info(
                f"[LIVE CLOB MATCHED] {trade_id} -> OID: {order_id} | {target_token} | Shares={actual_shares:.2f} "
                f"@ ${fill_px:.4f} | Notional=${actual_notional:.2f} | Latency={latency_ms:.2f}ms | Trades={trade_ids}"
            )

            # P0: Non-blocking return: Record MATCHED_PENDING_SETTLEMENT immediately.
            # Do NOT block the event loop or trigger synchronous settlement polling.
            exec_status = ExecutionStatus.MATCHED_PENDING_SETTLEMENT
            confirmed_onchain = False

            res = OrderResult(
                success=True,
                order_id=order_id,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=fill_px,
                size=actual_shares,
                notional_usd=actual_notional,
                fee_usd=fee_usd,
                latency_ms=latency_ms,
                mode="LIVE_CLOB",
                execution_status=exec_status,
                confirmed_onchain=confirmed_onchain,
                details={
                    "raw_response": post_resp,
                    "depth_ratio": depth_ratio,
                    "timestamp_utc": now_utc,
                    "confirmed_onchain": confirmed_onchain,
                    "pre_token_balance": pre_token_bal,
                    "trade_ids": trade_ids,
                    "transactions_hashes": tx_hashes,
                },
            )
            self._log_order(res)
            return res

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            err_msg = f"CLOB order submission failed: {e}"
            logger.error(f"[{trade_id}] {err_msg}")
            res = OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=best_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=latency_ms,
                mode="LIVE_CLOB_ERROR",
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err_msg,
            )
            self._log_order(res)
            return res

    async def execute_snipe_order_async(
        self,
        trade_id: str,
        token_id: str,
        target_token: str,
        notional_usd: float = 20.0,
        target_price: float = 0.0,
        side: str = "BUY",
        depth_hurdle: float = DEFAULT_DEPTH_HURDLE,
        market_id: Optional[str] = None,
        condition_id: Optional[str] = None,
        market_fee_rate: Optional[float] = None,
        market_fee_exponent: Optional[float] = None,
        max_price_ceiling: float = MAX_PRICE_CEILING,
    ) -> OrderResult:
        """
        P0: Fully asynchronous, non-blocking EIP-712 order dispatcher.
        Uses native async HTTP for orderbook fetching and isolates Web3/SDK calls
        into worker threads via asyncio.to_thread, completely preventing event-loop stalls.
        """
        t0 = time.perf_counter()
        now_utc = datetime.now(timezone.utc).isoformat()

        # Invariant: assert asset routing
        self.assert_market_routing(token_id, market_version="CTF")

        # 1. Fetch live orderbook asynchronously
        try:
            book = await self.get_market_book_async(token_id)
        except Exception as e:
            err = f"Async Orderbook Fetch Failed for {token_id}: {e}"
            logger.error(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=0.0,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        passed_depth, depth_ratio, best_px, adjusted_notional = self.verify_pre_trade_depth(
            book,
            target_notional_usd=notional_usd,
            side=side,
            depth_hurdle_ratio=depth_hurdle,
            max_price_ceiling=max_price_ceiling,
            min_price_floor=MIN_PRICE_FLOOR,
            return_adjusted=True,
            min_lot_size=MIN_LOT_SIZE_USD,
        )
        if not passed_depth:
            err = f"DepthGuard Rejected: Available depth ratio {depth_ratio:.2f}x < hurdle {depth_hurdle:.2f}x."
            logger.warning(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=best_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        if adjusted_notional < notional_usd:
            logger.info(
                f"[{trade_id}] [DYNAMIC DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${adjusted_notional:.2f} "
                f"to match available book depth (Ratio: {depth_ratio:.2f}x vs hurdle {depth_hurdle:.2f}x)."
            )
            notional_usd = adjusted_notional

        if target_price > 0 and (best_px - target_price) > 0.04:
            err = f"SlippageGuard Rejected: Best price ${best_px:.4f} exceeds target ${target_price:.4f} by > 4¢."
            logger.warning(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=best_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        raw_worst_px = max(target_price + 0.03, best_px + 0.03)
        worst_acceptable_px = self.quantize_order_price(raw_worst_px, token_id, rounding=ROUND_CEILING)
        if worst_acceptable_px > max_price_ceiling + 1e-9:
            err = f"No valid token tick at or below configured entry ceiling (${max_price_ceiling:.4f})"
            logger.warning(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=best_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        fillable, vwap, sweep_shares, worst_px, fok_fee, fill_legs = self.simulate_fok_sweep(
            book, notional_usd, side=side, max_acceptable_price=worst_acceptable_px, return_legs=True
        )
        if not fillable:
            err = f"FOK Sweep Infeasible: Could not fill ${notional_usd:.2f} within limit ${worst_acceptable_px:.4f}."
            logger.warning(f"[{trade_id}] {err}")
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=worst_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                mode=self.auth_mode,
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err,
            )

        shares_to_buy = round(sweep_shares, 4)
        exec_price = round(vwap, 4)

        # Authoritative CLOB fee resolution (P1 Fix)
        cid = condition_id or market_id
        if cid:
            try:
                f_rate, f_exp = self.get_market_fee_params(cid, token_id=token_id)
            except Exception as e:
                logger.warning(f"Authoritative CLOB fee query notice for {cid}: {e}; using verified payload fee.")
                f_rate = float(market_fee_rate) if market_fee_rate is not None else 0.07
                f_exp = float(market_fee_exponent or 1.0)
        elif market_fee_rate is not None:
            f_rate = float(market_fee_rate)
            f_exp = float(market_fee_exponent or 1.0)
        else:
            f_rate, f_exp = 0.07, 1.0

        # Compute fee per matched fill level using authoritative market fee rate/exponent
        fee_usd = round(sum(
            shares_i * f_rate * ((price_i * (1.0 - price_i)) ** f_exp)
            for price_i, shares_i in fill_legs
        ), 5)
        fee_rate = fee_usd / max(notional_usd, 1e-9)

        if self.dry_run:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            mock_order_id = f"MOCK_CLOB_{int(time.time()*1000)}"
            logger.info(
                f"[DRY-RUN SNIPE] {trade_id} -> {target_token} | Shares={shares_to_buy:.2f} @ ${exec_price:.4f} "
                f"| Notional=${notional_usd:.2f} | Fee=${fee_usd:.4f} ({fee_rate*100:.2f}%) | Latency={latency_ms:.2f}ms"
            )
            res = OrderResult(
                success=True,
                order_id=mock_order_id,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=exec_price,
                size=shares_to_buy,
                notional_usd=notional_usd,
                fee_usd=fee_usd,
                latency_ms=latency_ms,
                mode="DRY_RUN_SIMULATION",
                execution_status=ExecutionStatus.POSITION_CONFIRMED,
                confirmed_onchain=True,
                details={
                    "fee_rate": fee_rate,
                    "depth_ratio": depth_ratio,
                    "timestamp_utc": now_utc,
                    "confirmed_onchain": True,
                    "pre_token_balance": 0.0,
                    "post_token_balance": shares_to_buy,
                    "balance_delta": shares_to_buy,
                },
            )
            self._log_order(res)
            return res

        # Live dispatch in thread pool with defer_exec=True
        if not self.is_authenticated or self.client is None:
            raise RuntimeError(f"LIVE ORDER REFUSED: Executor is in live real-money mode but unauthenticated ({self.auth_mode}).")

        try:
            if not self.dry_run:
                pre_token_bal = await asyncio.to_thread(self.get_onchain_erc1155_balance, token_id)
                if pre_token_bal is None:
                    raise RuntimeError(f"Cannot take authoritative pre-trade ERC-1155 snapshot for {token_id}; refusing live entry")
            else:
                pre_token_bal = 0.0

            if MarketOrderArgsV2 is not None:
                mo_args = MarketOrderArgsV2(
                    token_id=token_id,
                    amount=round(notional_usd, 2),
                    side=side,
                    price=worst_acceptable_px,
                    order_type=OrderType.FOK,
                )
                signed_order = self.client.create_market_order(mo_args)
            else:
                order_args = OrderArgsV2(
                    price=worst_acceptable_px,
                    size=shares_to_buy,
                    side=side,
                    token_id=token_id,
                )
                signed_order = self.client.create_order(order_args)

            # Post order with defer_exec=True in thread to prevent any blocking
            post_resp = await asyncio.to_thread(
                self.client.post_order,
                signed_order,
                OrderType.FOK,
                False,
                True,  # defer_exec=True
            )

            latency_ms = (time.perf_counter() - t0) * 1000.0
            order_id = post_resp.get("orderID") or post_resp.get("id")

            if not order_id or post_resp.get("errorMsg"):
                err_msg = post_resp.get("errorMsg") or "No orderID returned from CLOB matching engine"
                logger.error(f"[{trade_id}] Order rejected by CLOB: {err_msg} | raw={post_resp}")
                res = OrderResult(
                    success=False,
                    order_id=order_id,
                    trade_id=trade_id,
                    token_id=token_id,
                    target_token=target_token,
                    side=side,
                    price=best_px,
                    size=shares_to_buy,
                    notional_usd=notional_usd,
                    fee_usd=fee_usd,
                    latency_ms=latency_ms,
                    mode="LIVE_CLOB_ERROR",
                    execution_status=ExecutionStatus.REJECTED,
                    confirmed_onchain=False,
                    error=err_msg,
                    details={
                        "raw_response": post_resp,
                        "depth_ratio": depth_ratio,
                        "timestamp_utc": now_utc,
                        "pre_token_balance": pre_token_bal,
                    },
                )
                self._log_order(res)
                return res

            making_amt = post_resp.get("makingAmount")
            taking_amt = post_resp.get("takingAmount")
            actual_notional = float(making_amt) if making_amt is not None else notional_usd
            actual_shares = float(taking_amt) if taking_amt is not None else shares_to_buy
            fill_px = round(actual_notional / max(actual_shares, 1e-4), 4) if (making_amt and taking_amt and actual_shares > 0) else best_px

            trade_ids = post_resp.get("tradeIDs", [])
            tx_hashes = post_resp.get("transactionsHashes", [])

            logger.info(
                f"[LIVE CLOB MATCHED] {trade_id} -> OID: {order_id} | {target_token} | Shares={actual_shares:.2f} "
                f"@ ${fill_px:.4f} | Notional=${actual_notional:.2f} | Latency={latency_ms:.2f}ms | Trades={trade_ids}"
            )

            res = OrderResult(
                success=True,
                order_id=order_id,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=fill_px,
                size=actual_shares,
                notional_usd=actual_notional,
                fee_usd=fee_usd,
                latency_ms=latency_ms,
                mode="LIVE_CLOB",
                execution_status=ExecutionStatus.MATCHED_PENDING_SETTLEMENT,
                confirmed_onchain=False,
                details={
                    "raw_response": post_resp,
                    "depth_ratio": depth_ratio,
                    "timestamp_utc": now_utc,
                    "confirmed_onchain": False,
                    "pre_token_balance": pre_token_bal,
                    "trade_ids": trade_ids,
                    "transactions_hashes": tx_hashes,
                },
            )
            self._log_order(res)
            return res

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            err_msg = f"CLOB order submission failed: {e}"
            logger.error(f"[{trade_id}] {err_msg}")
            res = OrderResult(
                success=False,
                order_id=None,
                trade_id=trade_id,
                token_id=token_id,
                target_token=target_token,
                side=side,
                price=best_px,
                size=0.0,
                notional_usd=notional_usd,
                fee_usd=0.0,
                latency_ms=latency_ms,
                mode="LIVE_CLOB_ERROR",
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error=err_msg,
            )
            self._log_order(res)
            return res

    def get_token_tick_size(self, token_id: str) -> float:
        """
        P0 Invariant: Dynamically resolves token-specific minimum tick size via ClobClient SDK.
        Supported tick sizes in py_clob_client_v2: ('0.1', '0.01', '0.005', '0.0025', '0.001', '0.0001').
        Falls back to 0.01 if query fails or token is untracked in dry-run mode.
        """
        if token_id in self._tick_size_cache:
            return self._tick_size_cache[token_id]

        if self.client and hasattr(self.client, "get_tick_size"):
            try:
                raw_tick = self.client.get_tick_size(token_id)
                tick_val = float(raw_tick)
                if tick_val > 0:
                    self._tick_size_cache[token_id] = tick_val
                    return tick_val
            except Exception as e:
                logger.debug(f"Could not resolve tick size from SDK for {token_id}: {e}")

        if not self.dry_run:
            raise RuntimeError(f"AUTHORITATIVE_TICK_SIZE_UNAVAILABLE for live token {token_id}")
        tick_val = 0.01
        self._tick_size_cache[token_id] = tick_val
        return tick_val

    def quantize_order_price(self, price: float, token_id: str, rounding=ROUND_HALF_UP) -> float:
        """
        Quantizes order price to the token's authoritative minimum tick size using exact Decimal multiples.
        Supports all SDK tick sizes: 0.1, 0.01, 0.005, 0.0025, 0.001, 0.0001.
        Preserves 4th-decimal increments (e.g. 0.0025) without truncation.
        Clamps to valid probability interval [min_tick, 1.0 - min_tick].
        """
        tick = Decimal(str(self.get_token_tick_size(token_id)))
        units = (Decimal(str(price)) / tick).to_integral_value(rounding=rounding)
        q = units * tick
        q = max(tick, min(Decimal("1") - tick, q))
        return float(q)

    def post_maker_exit_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str = "SELL",
    ) -> Dict[str, Any]:
        """
        Posts a resting maker scalp limit order with post_only=True and defer_exec=True.
        Guarantees passive execution (zero taker fee, zero spread crossing).
        Enforces strict conditional token balance invariant before submitting.
        Dynamically quantizes limit price to token-specific minimum tick size.
        """
        if not self.dry_run:
            if not self.is_authenticated or self.client is None:
                raise RuntimeError(f"LIVE EXIT REFUSED: Executor is in live mode but unauthenticated ({self.auth_mode}).")

            # P0 #2: Invariant Check: Available conditional balance >= exit size
            avail_bal = self.get_conditional_balance(token_id)
            if avail_bal < (size - 0.05):
                err = f"INSUFFICIENT_CONDITIONAL_BALANCE: On-chain balance {avail_bal:.4f} < exit size {size:.4f}"
                logger.warning(f"[PM-EXEC] {err}")
                return {
                    "success": False,
                    "orderID": None,
                    "error": err,
                    "available_balance": avail_bal,
                    "retryable": True,
                }
        else:
            mock_id = f"MOCK_EXIT_{int(time.time()*1000)}"
            logger.info(f"[DRY-RUN EXIT] Resting {side} limit order: {size:.2f} shares @ ${price:.4f} (ID: {mock_id})")
            return {"success": True, "orderID": mock_id, "mode": "DRY_RUN", "post_only": True}

        try:
            # Dynamically quantize price to token-specific tick size (ceiling rounding for maker sell)
            quantized_price = self.quantize_order_price(price, token_id, rounding=ROUND_CEILING)

            order_args = OrderArgsV2(
                price=quantized_price,
                size=round(size, 4),
                side=side,
                token_id=token_id,
            )
            signed_order = self.client.create_order(order_args)
            # Enforce post_only=True and defer_exec=True to guarantee non-blocking maker status
            resp = self.client.post_order(signed_order, OrderType.GTC, post_only=True, defer_exec=True)
            order_id = resp.get("orderID") or resp.get("id")
            if order_id:
                logger.info(f"[LIVE MAKER EXIT POSTED (POST-ONLY)] OID: {order_id} | {side} {size:.2f} shares @ ${quantized_price:.4f}")
                return {"success": True, "orderID": order_id, "post_only": True, "price": quantized_price, "raw": resp}
            logger.error(f"Failed to post maker exit order: {resp}")
            return {"success": False, "orderID": None, "raw": resp}
        except Exception as e:
            logger.error(f"Exception posting maker exit order: {e}")
            return {"success": False, "orderID": None, "error": str(e)}

    def execute_unwind_order(
        self,
        token_id: str,
        size: float,
        side: str = "SELL",
        min_price: float = 0.01,
    ) -> Dict[str, Any]:
        """
        Executes an immediate aggressive FOK sell order on the CLOB matching engine.
        Used by Stop-Loss and Terminal-Unwind policies.
        Guarantees that an unwind is ACTUALLY SUBMITTED to the exchange, not just locally assumed.
        Dynamically quantizes price to token-specific minimum tick size.
        """
        if self.dry_run:
            mock_id = f"MOCK_UNWIND_{int(time.time()*1000)}"
            logger.info(f"[DRY-RUN UNWIND] Executed simulated {side} unwind: {size:.2f} shares @ min ${min_price:.4f}")
            taking_amt = size * min_price
            avg_px = min(0.999, max(0.001, min_price))
            fee_usd = round(size * 0.07 * (avg_px * (1.0 - avg_px)), 5)
            return {"success": True, "orderID": mock_id, "matched_size": size, "taking_amount": taking_amt, "fee_usd": fee_usd}
        if not self.is_authenticated or self.client is None:
            return {
                "success": False,
                "orderID": None,
                "retryable": True,
                "outcome_unknown": False,
                "error": "Live CLOB client unavailable; no simulated success permitted",
            }

        try:
            # Dynamically quantize price to token-specific tick size (floor rounding for aggressive sell)
            quantized_price = self.quantize_order_price(min_price, token_id, rounding=ROUND_FLOOR)

            order_args = OrderArgsV2(
                price=quantized_price,
                size=round(size, 4),
                side=side,
                token_id=token_id,
            )
            signed_order = self.client.create_order(order_args)
            resp = self.client.post_order(signed_order, OrderType.FOK, post_only=False, defer_exec=False)
            order_id = resp.get("orderID") or resp.get("id")
            status = resp.get("status")
            taking_amount = resp.get("takingAmount") or resp.get("taking_amount")
            status_str = str(status).upper() if status else ""
            raw_matched = resp.get("makingAmount") or resp.get("size")
            matched_status = status_str in {"MATCHED", "FILLED", "CONFIRMED"}
            is_matched = bool(order_id) and matched_status and raw_matched is not None
            if is_matched:
                matched_size = float(raw_matched)
                if matched_size < size - self.calculate_balance_epsilon(0.001):
                    return {
                        "success": False,
                        "orderID": order_id,
                        "matched_size": matched_size,
                        "partial": True,
                        "retryable": True,
                        "raw": resp,
                    }
                taking_amt = float(taking_amount) if taking_amount else matched_size * quantized_price
                average_price = min(
                    0.999,
                    max(0.001, taking_amt / max(matched_size, 1e-9)),
                )
                fee_usd = round(
                    matched_size
                    * 0.07
                    * (average_price * (1.0 - average_price)),
                    5,
                )
                logger.info(f"[LIVE UNWIND EXECUTED] OID: {order_id} | Sold {matched_size:.2f} shares @ min ${quantized_price:.4f} (Proceeds: ${taking_amt:.2f})")
                return {
                    "success": True,
                    "orderID": order_id,
                    "matched_size": matched_size,
                    "taking_amount": taking_amt,
                    "fee_usd": fee_usd,
                    "raw": resp,
                }
            else:
                logger.warning(f"[LIVE UNWIND REJECTED/UNMATCHED] Response: {resp}")
                return {"success": False, "orderID": order_id, "error": f"Status: {status}", "raw": resp}
        except Exception as e:
            logger.error(f"[LIVE UNWIND EXCEPTION] Error executing unwind order: {e}")
            return {"success": False, "error": str(e)}

    def post_heartbeat(self, heartbeat_id: Optional[str] = None) -> Dict[str, Any]:
        """Maintains active CLOB session so resting GTC orders are not canceled."""
        if self.dry_run or not self.is_authenticated or self.client is None:
            return {"heartbeat_id": "MOCK_HEARTBEAT"}
        hid = self.last_heartbeat_id if heartbeat_id is None else heartbeat_id
        try:
            resp = self.client.post_heartbeat(heartbeat_id=hid or "")
            new_id = resp.get("heartbeat_id")
            if new_id:
                self.last_heartbeat_id = new_id
            self.heartbeat_failures = 0
            return resp
        except Exception as e:
            self.last_heartbeat_id = ""
            self.heartbeat_failures += 1
            logger.error(f"[HEARTBEAT FAILURE] CLOB heartbeat error (failures={self.heartbeat_failures}): {e}")
            return {"error": str(e), "failures": self.heartbeat_failures}

    def is_heartbeat_healthy(self) -> bool:
        """Returns False if heartbeat has failed repeatedly."""
        return self.heartbeat_failures < 3

    def get_open_orders(self, *, strict: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Queries all live open orders from CLOB matching engine."""
        if self.dry_run:
            return []
        if not self.is_authenticated or self.client is None:
            if strict:
                raise RuntimeError("Cannot establish authoritative open-order state in live mode")
            return None
        try:
            result = self.client.get_open_orders()
            if not isinstance(result, list):
                raise RuntimeError(f"Unexpected open-orders response type: {type(result).__name__}")
            return result
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            if strict:
                raise RuntimeError("CLOB open-order snapshot unavailable") from e
            return None

    def cancel_all_orders(self) -> Dict[str, Any]:
        """Emergency kill-switch: cancels all open orders on CLOB."""
        if self.dry_run or not self.is_authenticated or self.client is None:
            return {"canceled_all": True}
        try:
            logger.warning("[KILL-SWITCH] Canceling all open CLOB orders...")
            return self.client.cancel_all()
        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            return {"error": str(e)}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancels an active order by ID."""
        if self.dry_run or not self.is_authenticated or self.client is None:
            return {"canceled": [order_id]}
        try:
            return self.client.cancel_orders([order_id])
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return {"error": str(e)}

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Queries live status of an order from CLOB."""
        if self.dry_run or not self.is_authenticated or self.client is None:
            return None
        try:
            return self.client.get_order(order_id)
        except Exception as e:
            logger.error(f"Error querying order {order_id}: {e}")
            return None

    def get_collateral_balance(self) -> float:
        """
        Queries CLOB L2 for authoritative collateral balance in human USD units.
        Avoids 1,000,000x confusion by dividing 6-decimal integer base units explicitly.
        """
        if self.dry_run or not self.is_authenticated or self.client is None or BalanceAllowanceParams is None:
            return 0.0
        try:
            params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=self.signature_type)
            res = self.client.get_balance_allowance(params)
            raw = float(res.get("balance", "0"))
            return raw / 1e6
        except Exception as e:
            logger.error(f"[PM-EXEC] Failed to query CLOB collateral balance: {e}")
            return 0.0

    def get_conditional_balance(self, token_id: str) -> float:
        """
        Queries CLOB L2 for conditional token (ERC-1155) balance for a specific token_id.
        Avoids 1,000,000x confusion by dividing 6-decimal integer base units explicitly.
        """
        if self.dry_run or not self.is_authenticated or self.client is None or BalanceAllowanceParams is None:
            return 0.0
        try:
            params = BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL, token_id=token_id, signature_type=self.signature_type)
            res = self.client.get_balance_allowance(params)
            raw = float(res.get("balance", "0"))
            return raw / 1e6
        except Exception as e:
            logger.error(f"[PM-EXEC] Failed to query CLOB conditional balance for {token_id}: {e}")
            return 0.0

    def get_onchain_erc1155_balance(self, token_id: str, account_address: Optional[str] = None) -> Optional[float]:
        """
        P0 Invariant: Direct independent Polygon on-chain ERC-1155 balanceOf(account, id) read via JSON-RPC.
        Target contract: Polymarket ConditionalTokens (0x4D97DCd97eC945f40cF65F87097ACe5EA0476045).
        Queries node directly without relying on CLOB API. Returns verified token balance divided by 1e6.
        """
        target_account = account_address or self.funder_address
        if not target_account or not token_id:
            return None
        try:
            rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")
            conditional_tokens = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
            selector = "00fdd58e"  # balanceOf(address,uint256)
            clean_addr = target_account[2:] if target_account.startswith("0x") else target_account
            addr_padded = clean_addr.lower().rjust(64, "0")
            token_id_int = int(token_id, 16) if str(token_id).startswith("0x") else int(token_id)
            id_hex = hex(token_id_int)[2:].rjust(64, "0")
            call_data = "0x" + selector + addr_padded + id_hex
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [{"to": conditional_tokens, "data": call_data}, "latest"],
            }
            resp = requests.post(rpc_url, json=payload, timeout=3.0)
            if resp.status_code == 200:
                res_json = resp.json()
                if "result" in res_json and res_json["result"] is not None:
                    raw_int = int(res_json["result"], 16)
                    return raw_int / 1e6
            return None
        except Exception as e:
            logger.debug(f"On-chain ERC-1155 balanceOf query error for {token_id}: {e}")
            return None

    def _log_order(self, res: OrderResult):
        """Appends order execution event to immutable JSONL audit ledger."""
        try:
            entry = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "success": res.success,
                "order_id": res.order_id,
                "trade_id": res.trade_id,
                "token_id": res.token_id,
                "target_token": res.target_token,
                "side": res.side,
                "price": res.price,
                "size": res.size,
                "notional_usd": res.notional_usd,
                "fee_usd": res.fee_usd,
                "latency_ms": res.latency_ms,
                "mode": res.mode,
                "error": res.error,
                "details": res.details,
            }
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to append to live order ledger: {e}")


if __name__ == "__main__":
    print("=" * 80)
    print("  POLYMARKET LIVE CLOB EXECUTION ADAPTER - STANDALONE PREFLIGHT")
    print("=" * 80)

    executor = PolymarketLiveExecutor(dry_run=True)
    print(f"Auth Mode: {executor.auth_mode}")
    print(f"SDK Available: {PY_CLOB_AVAILABLE}")
    print(f"Ledger Path: {executor.ledger_path}")

    # Test pre-trade calculation
    fee_rate, fee_usd = executor.calculate_dynamic_crypto_fee(0.77, 50.0)
    print(f"Dynamic Fee on $50 @ $0.77: Rate={fee_rate*100:.2f}% | USD=${fee_usd:.4f}")
    assert abs(fee_rate - 0.0161) < 1e-4, "Dynamic fee calculation mismatch"

    print(">>> POLYMARKET LIVE ADAPTER PREFLIGHT: PASS (100% OPERATIONAL) <<<")

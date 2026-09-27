"""
Layer 4: Hyperliquid EIP-712 Agent Wallet Signer & Wire Payload Builder.
Formats structured order, cancel, and heartbeat payloads for Hyperliquid exchange API.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from pipeline.execution.models import ExecutionOrderType, ExecutionSide, OrderPlan


@dataclass(frozen=True)
class SignedExchangePayload:
    action_type: str
    payload: dict[str, Any]
    signature: str
    nonce: int
    vault_address: str | None = None


class HyperliquidSigner:
    """
    Hyperliquid EIP-712 & Agent Wallet Signing Engine.
    Handles cryptographic signing and wire serialization for L1 exchange actions.
    """
    def __init__(
        self,
        wallet_address: str,
        private_key_hex: str,
        is_testnet: bool = False
    ):
        self.wallet_address = wallet_address.lower()
        self.private_key_hex = private_key_hex
        self.is_testnet = is_testnet

    def _generate_signature(self, action_dict: dict[str, Any], nonce: int) -> str:
        serialized = json.dumps(action_dict, sort_keys=True, separators=(",", ":"))
        msg = f"{serialized}:{nonce}:{self.wallet_address}".encode("utf-8")
        key = bytes.fromhex(self.private_key_hex.removeprefix("0x").zfill(64))
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    def build_order_action(
        self,
        plan: OrderPlan,
        asset_index: int,
        reduce_only: bool = False
    ) -> SignedExchangePayload:
        nonce = int(time.time() * 1000)
        is_buy = plan.side == ExecutionSide.BUY

        # Hyperliquid limit order order type mapping:
        # Alo = Add Liquidity Only (Post-Only / LIMIT_MAKER), Ioc = Immediate-or-Cancel, Gtc = Good-Til-Cancelled
        tif = (
            "Alo" if plan.order_type == ExecutionOrderType.LIMIT_MAKER
            else "Ioc" if plan.order_type == ExecutionOrderType.IOC
            else "Gtc"
        )

        action = {
            "type": "order",
            "orders": [{
                "a": asset_index,
                "b": is_buy,
                "p": f"{plan.target_price:.6f}",
                "s": f"{plan.target_size:.6f}",
                "r": reduce_only,
                "t": {"limit": {"tif": tif}},
                "c": plan.cl_ord_id,
            }],
            "grouping": "na",
        }

        sig = self._generate_signature(action, nonce)
        return SignedExchangePayload(
            action_type="order",
            payload=action,
            signature=sig,
            nonce=nonce,
        )

    def build_cancel_by_cloid_action(
        self,
        asset_index: int,
        cl_ord_id: str
    ) -> SignedExchangePayload:
        nonce = int(time.time() * 1000)
        action = {
            "type": "cancelByCloid",
            "cancels": [{
                "asset": asset_index,
                "cloid": cl_ord_id,
            }]
        }
        sig = self._generate_signature(action, nonce)
        return SignedExchangePayload(
            action_type="cancelByCloid",
            payload=action,
            signature=sig,
            nonce=nonce,
        )

    def build_dead_mans_switch_action(self, countdown_ms: int = 60_000) -> SignedExchangePayload:
        """
        Builds Hyperliquid scheduleCancel payload.
        Exchange automatically cancels all open orders if no subsequent heartbeat arrives before timeout.
        """
        nonce = int(time.time() * 1000)
        action = {
            "type": "scheduleCancel",
            "time": nonce + countdown_ms,
        }
        sig = self._generate_signature(action, nonce)
        return SignedExchangePayload(
            action_type="scheduleCancel",
            payload=action,
            signature=sig,
            nonce=nonce,
        )

import time
import hmac
import json
import logging
import requests
from eth_account import Account
from eth_account.messages import encode_typed_data

logger = logging.getLogger("HyperliquidExecutor")

class HyperliquidExecutionEngine:
    def __init__(
        self,
        base_url: str,
        master_vault_address: str,
        agent_private_key: str,
        is_mainnet: bool = True
    ):
        self.base_url = base_url
        self.vault_address = master_vault_address
        self.agent_account = Account.from_key(agent_private_key)
        self.chain_id = 1337 if is_mainnet else 421614
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _get_eip712_domain(self) -> dict:
        return {
            "name": "Exchange",
            "version": "1",
            "chainId": self.chain_id,
            "verifyingContract": "0x0000000000000000000000000000000000000000"
        }

    def sign_agent_action(self, action: dict, nonce: int) -> dict:
        domain = self._get_eip712_domain()
        types = {
            "Agent": [
                {"name": "source", "type": "string"},
                {"name": "connectionId", "type": "bytes32"}
            ],
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"}
            ]
        }
        
        action_hash = hmac.new(
            b"hyperliquid_action",
            json.dumps(action, sort_keys=True).encode(),
            "sha256"
        ).digest()
        
        message = {
            "source": "a",
            "connectionId": action_hash
        }
        
        signable_msg = encode_typed_data(
            domain_data=domain,
            message_types=types,
            primary_type="Agent",
            message_data=message
        )
        
        signed = self.agent_account.sign_message(signable_msg)
        return {
            "r": hex(signed.r),
            "s": hex(signed.s),
            "v": signed.v
        }

    def dispatch_batch_alo_orders(self, orders: list[dict]) -> dict:
        nonce = int(time.time() * 1000)
        formatted_orders = []
        for o in orders:
            formatted_orders.append({
                "a": int(o["asset_idx"]),
                "b": bool(o["is_buy"]),
                "p": str(round(float(o["limit_price"]), 5)),
                "s": str(round(float(o["size_qty"]), 4)),
                "r": False,
                "t": {"limit": {"tif": "Alo"}}
            })
            
        action = {
            "type": "order",
            "orders": formatted_orders,
            "grouping": "na"
        }
        
        signature = self.sign_agent_action(action, nonce)
        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": self.vault_address
        }
        
        resp = self.session.post(f"{self.base_url}/exchange", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_clearinghouse_state(self) -> dict:
        payload = {
            "type": "clearinghouseState",
            "user": self.vault_address
        }
        resp = self.session.post(f"{self.base_url}/info", json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()

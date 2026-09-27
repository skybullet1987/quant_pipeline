import math
from typing import Dict, Any, Tuple, List, Optional
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

class HyperliquidGateway:
    def __init__(self, secret_key: str = None, account_address: str = None, testnet: bool = True):
        self.testnet = testnet
        self.base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        self.info = Info(self.base_url, skip_ws=True)
        
        self.wallet = None
        self.exchange = None
        self.account_address = account_address

        if secret_key:
            self.wallet = Account.from_key(secret_key)
            self.account_address = account_address if account_address else self.wallet.address
            # Agent signs for Master account_address
            self.exchange = Exchange(self.wallet, self.base_url, account_address=self.account_address)

        self.meta = self.info.meta()
        self.sz_decimals: Dict[str, int] = {
            token["name"]: token["szDecimals"] for token in self.meta["universe"]
        }

    def get_account_state(self) -> Tuple[float, float, Dict[str, Dict[str, float]]]:
        """Returns total unified portfolio value, withdrawable cash, and open positions."""
        if not self.account_address:
            raise ValueError("Account address required to fetch state.")
        
        user_state = self.info.user_state(self.account_address)
        spot_state = self.info.spot_user_state(self.account_address)

        # 1. Total base collateral from Unified Spot Pool
        spot_balances = {b["coin"]: b for b in spot_state.get("balances", [])}
        usdc_total = float(spot_balances.get("USDC", {}).get("total", 0.0))
        usdc_hold = float(spot_balances.get("USDC", {}).get("hold", 0.0))

        # 2. Extract active perps positions
        positions = {}
        total_unrealized = 0.0
        for pos in user_state.get("assetPositions", []):
            p = pos["position"]
            s = p["coin"]
            sz = float(p["szi"])
            upnl = float(p.get("unrealizedPnl", 0.0))
            if abs(sz) > 0:
                total_unrealized += upnl
                positions[s] = {
                    "size": sz,
                    "entry_px": float(p["entryPx"]),
                    "unrealized_pnl": upnl,
                    "leverage": float(p.get("leverage", {}).get("value", 1.0))
                }

        # In Hyperliquid unified spot/perp accounts, spot USDC total already dynamically tracks unified mark equity
        total_equity = usdc_total if usdc_total > 0 else float(user_state["marginSummary"]["accountValue"])
        available_cash = max(0.0, usdc_total - usdc_hold)

        return total_equity, available_cash, positions

    def get_open_orders(self) -> List[Dict[str, Any]]:
        if not self.account_address:
            return []
        return self.info.open_orders(self.account_address)

    def cancel_all_open_orders(self) -> int:
        if not self.exchange:
            raise ValueError("Exchange wallet required to cancel orders.")
        orders = self.get_open_orders()
        canceled_count = 0
        for o in orders:
            res = self.exchange.cancel(o["coin"], o["oid"])
            if res.get("status") == "ok":
                canceled_count += 1
        return canceled_count

    def close_all_positions(self) -> List[Dict[str, Any]]:
        """Flattens all open positions immediately using aggressive IOC orders."""
        if not self.exchange:
            raise ValueError("Exchange wallet required to close positions.")
        _, _, positions = self.get_account_state()
        results = []
        for sym, pos in positions.items():
            sz = pos["size"]
            is_buy_to_close = sz < 0
            rounded_sz = abs(self.round_sz(sym, sz))
            mid = self.get_mid_price(sym)
            slip_px = self.round_px(mid * 1.05 if is_buy_to_close else mid * 0.95)
            
            res = self.exchange.order(
                sym, is_buy_to_close, rounded_sz, slip_px,
                order_type={"limit": {"tif": "Ioc"}}, reduce_only=True
            )
            results.append({"symbol": sym, "size": sz, "res": res})
        return results

    def round_sz(self, symbol: str, size: float) -> float:
        dec = self.sz_decimals.get(symbol, 2)
        factor = 10 ** dec
        truncated = math.floor(abs(size) * factor) / factor
        return round(truncated, dec) * (1 if size >= 0 else -1)

    def round_px(self, symbol_or_px: Any, price: Optional[float] = None) -> float:
        if price is None:
            try:
                px = float(symbol_or_px)
                if px <= 0: return 0.0
                scale = 5 - int(math.floor(math.log10(abs(px)))) - 1
                if scale < 0:
                    return float(round(px, scale))
                return float(round(px, min(5, scale)))
            except (ValueError, TypeError):
                return 0.0
        symbol = str(symbol_or_px)
        px = float(price)
        if px <= 0: return 0.0
        sz_dec = self.sz_decimals.get(symbol, 2)
        max_decimals = max(0, 6 - sz_dec)
        scale = 5 - int(math.floor(math.log10(abs(px)))) - 1
        if scale < 0:
            return float(round(px, scale))
        target_decimals = min(max_decimals, scale)
        return float(round(px, target_decimals))

    def validate_l1_order(
        self,
        symbol: str,
        price: float,
        size: float,
        is_reduce_only: bool = False
    ) -> Tuple[bool, str, float, float]:
        """Validates order against Hyperliquid L1 node quantization invariants."""
        sz_dec = self.sz_decimals.get(symbol, 2)
        q_px = self.round_px(symbol, price)
        q_sz = abs(self.round_sz(symbol, size))
        notional = q_px * q_sz
        if not is_reduce_only and notional < 10.00:
            return False, f"Order notional ${notional:.2f} below $10.00 L1 minimum", q_px, q_sz
        if q_sz <= 0.0:
            return False, "Order size truncated to 0.0 under szDecimals floor", q_px, q_sz
        return True, "VALID", q_px, q_sz

    def get_frontend_open_orders(self) -> List[Dict[str, Any]]:
        """Retrieves all open orders including triggers, avoiding the SDK dex='' 422 deserialization bug."""
        if not self.account_address:
            return []
        try:
            res = self.info.post("/info", {"type": "frontendOpenOrders", "user": self.account_address})
            if isinstance(res, list):
                return res
            return []
        except Exception as e:
            print(f"--> [Gateway Warning] Failed to fetch frontend open orders: {e}", flush=True)
            return []

    def cancel_stale_maker_orders(self) -> int:
        """Cancels only resting non-trigger limit orders, strictly preserving active TP/SL brackets."""
        if not self.exchange:
            return 0
        fe_orders = self.get_frontend_open_orders()
        canceled_count = 0
        for o in fe_orders:
            if not o.get("isTrigger") and "trigger" not in str(o.get("orderType", "")).lower():
                try:
                    res = self.exchange.cancel(o["coin"], o["oid"])
                    if res.get("status") == "ok":
                        canceled_count += 1
                except Exception:
                    pass
        return canceled_count

    def cancel_all_trigger_orders(self) -> int:
        """Cancels all active TP/SL trigger orders cleanly so exact fresh brackets can be armed."""
        if not self.exchange:
            return 0
        fe_orders = self.get_frontend_open_orders()
        canceled_count = 0
        for o in fe_orders:
            if o.get("isTrigger") or "trigger" in str(o.get("orderType", "")).lower():
                try:
                    res = self.exchange.cancel(o["coin"], o["oid"])
                    if res.get("status") == "ok":
                        canceled_count += 1
                except Exception:
                    pass
        return canceled_count

    def get_mid_price(self, symbol: str) -> float:
        l2 = self.info.l2_snapshot(symbol)
        bids, asks = l2.get("levels", [[], []])
        if not bids or not asks:
            raise ValueError(f"Orderbook empty for {symbol}")
        best_bid = float(bids[0]["px"])
        best_ask = float(asks[0]["px"])
        return (best_bid + best_ask) / 2.0

    def place_alo_order(self, symbol: str, is_buy: bool, size: float, price: float) -> Dict[str, Any]:
        if not self.exchange:
            return {}
        try:
            rounded_sz = abs(self.round_sz(symbol, size))
            rounded_px = self.round_px(symbol, price)
            if rounded_sz <= 0 or rounded_px <= 0:
                return {}
            return self.exchange.order(
                symbol, is_buy, rounded_sz, rounded_px,
                order_type={"limit": {"tif": "Alo"}}, reduce_only=False
            )
        except Exception as e:
            print(f"--> [Gateway Warning] Failed to place ALO order for {symbol}: {e}", flush=True)
            return {"error": str(e)}

    def place_trigger_stop(self, symbol: str, is_buy_to_close: bool, size: float, trigger_price: float) -> Dict[str, Any]:
        if not self.exchange:
            return {}
        try:
            rounded_sz = abs(self.round_sz(symbol, size))
            rounded_px = self.round_px(symbol, trigger_price)
            if rounded_sz <= 0 or rounded_px <= 0:
                return {}
            return self.exchange.order(
                symbol, is_buy_to_close, rounded_sz, rounded_px,
                order_type={"trigger": {"isMarket": True, "triggerPx": float(rounded_px), "tpsl": "sl"}},
                reduce_only=True
            )
        except Exception as e:
            print(f"--> [Gateway Warning] Failed to place trigger stop for {symbol}: {e}", flush=True)
            return {"error": str(e)}

    def close_position(self, symbol: str, size: float, is_long: bool) -> Dict[str, Any]:
        if not self.exchange:
            return {}
        try:
            is_buy_to_close = not is_long
            rounded_sz = abs(self.round_sz(symbol, size))
            mid = self.get_mid_price(symbol)
            slip_px = self.round_px(symbol, mid * 1.05 if is_buy_to_close else mid * 0.95)
            return self.exchange.order(
                symbol, is_buy_to_close, rounded_sz, slip_px,
                order_type={"limit": {"tif": "Ioc"}}, reduce_only=True
            )
        except Exception as e:
            print(f"--> [Gateway Warning] Failed to close position for {symbol}: {e}", flush=True)
            return {"error": str(e)}


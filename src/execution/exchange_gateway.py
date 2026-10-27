import math
import hashlib
import time
from typing import Dict, Any, Tuple, List, Optional
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.utils.types import Cloid

_TRANSIENT_ERR_MARKERS = ("502", "503", "504", "bad gateway", "service unavailable", "gateway timeout", "timed out", "connection aborted", "connection reset")


def _is_transient_gateway_exc(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(tok in msg for tok in _TRANSIENT_ERR_MARKERS)


class HyperliquidGateway:
    def __init__(self, secret_key: str = None, account_address: str = None, testnet: bool = True):
        self.testnet = testnet
        self.base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        self.info = Info(self.base_url, skip_ws=True)
        
        self.wallet = None
        self.exchange = None
        self.account_address = account_address
        self.last_user_state: Dict[str, Any] = {}

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
        self.last_user_state = user_state
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
                pos_val = float(p.get("positionValue", 0.0))
                mark_px = pos_val / abs(sz) if abs(sz) > 0 and pos_val > 0 else float(p["entryPx"])
                positions[s] = {
                    "size": sz,
                    "entry_px": float(p["entryPx"]),
                    "mark_px": mark_px,
                    "unrealized_pnl": upnl,
                    "leverage": float(p.get("leverage", {}).get("value", 1.0))
                }

        # In Hyperliquid unified spot/perp accounts, spot USDC total already dynamically tracks unified mark equity
        margin_acct_val = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
        total_equity = usdc_total if usdc_total > 0 else margin_acct_val
        available_cash = max(0.0, usdc_total - usdc_hold)

        return total_equity, available_cash, positions

    def get_bbo_and_mid(self, symbol: str) -> Tuple[float, float, float]:
        """Returns (best_bid, best_ask, mid_price) from live L2 orderbook snapshot."""
        l2 = self.info.l2_snapshot(symbol)
        bids, asks = l2.get("levels", [[], []])
        if not bids or not asks:
            raise ValueError(f"Orderbook empty for {symbol}")
        best_bid = float(bids[0]["px"])
        best_ask = float(asks[0]["px"])
        return best_bid, best_ask, (best_bid + best_ask) / 2.0

    def get_tick_size(self, symbol: str, ref_price: float) -> float:
        """Computes exact Hyperliquid L1 tick size for a symbol at ref_price."""
        if ref_price <= 0:
            return 1e-4
        sz_dec = self.sz_decimals.get(symbol, 2)
        max_decimals = max(0, 6 - sz_dec)
        scale = 5 - int(math.floor(math.log10(abs(ref_price)))) - 1
        target_decimals = min(max_decimals, scale) if scale >= 0 else scale
        return float(10.0 ** (-target_decimals))

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
            raw_slip = mid * 1.05 if is_buy_to_close else mid * 0.95
            
            # Oracle collar clamp (+/- 4.5%) to avoid exchange rejection
            oracle_px = self.get_oracle_price(sym)
            if oracle_px > 0:
                if is_buy_to_close:
                    raw_slip = min(raw_slip, oracle_px * 1.045)
                else:
                    raw_slip = max(raw_slip, oracle_px * 0.955)

            slip_px = self.round_px(sym, raw_slip)
            
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
            raise RuntimeError(f"Unexpected non-list response for frontendOpenOrders: {res}")
        except Exception as e:
            print(f"--> [Gateway Warning] Failed to fetch frontend open orders: {e}", flush=True)
            raise RuntimeError(f"Exchange query frontendOpenOrders failed: {e}") from e

    def cancel_stale_maker_orders(self) -> int:
        """Cancels only resting non-trigger limit orders, strictly preserving active TP/SL brackets."""
        if not self.exchange:
            return 0
        try:
            fe_orders = self.get_frontend_open_orders()
        except Exception as e:
            print(f"--> [Gateway Warning] Skipping cancel_stale_maker_orders due to query error: {e}", flush=True)
            return 0
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
        try:
            fe_orders = self.get_frontend_open_orders()
        except Exception as e:
            print(f"--> [Gateway Warning] Skipping cancel_all_trigger_orders due to query error: {e}", flush=True)
            return 0
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

    def place_alo_order(self, symbol: str, is_buy: bool, size: float, price: float, cloid: Optional[str] = None) -> Dict[str, Any]:
        if not self.exchange:
            return {}
        try:
            rounded_sz = abs(self.round_sz(symbol, size))
            rounded_px = self.round_px(symbol, price)
            if rounded_sz <= 0 or rounded_px <= 0:
                return {}
            cloid_obj = None
            if cloid:
                hex_str = "0x" + hashlib.md5(cloid.encode("utf-8")).hexdigest()
                cloid_obj = Cloid.from_str(hex_str)
            return self.exchange.order(
                symbol, is_buy, rounded_sz, rounded_px,
                order_type={"limit": {"tif": "Alo"}}, reduce_only=False,
                cloid=cloid_obj
            )
        except Exception as e:
            if _is_transient_gateway_exc(e):
                raise
            print(f"--> [Gateway Warning] Failed to place ALO order for {symbol}: {e}", flush=True)
            return {"error": str(e)}

    def place_trigger_stop(self, symbol: str, is_buy_to_close: bool, size: float, trigger_price: float, cloid: Optional[str] = None) -> Dict[str, Any]:
        if not self.exchange:
            return {}
        try:
            rounded_sz = abs(self.round_sz(symbol, size))
            rounded_px = self.round_px(symbol, trigger_price)
            if rounded_sz <= 0 or rounded_px <= 0:
                return {}
            # Protective 3.0% limit slippage collar once trigger fires so thin books still match
            raw_limit_px = rounded_px * 1.030 if is_buy_to_close else rounded_px * 0.970
            limit_px = self.round_px(symbol, raw_limit_px)
            cloid_obj = None
            if cloid:
                hex_str = "0x" + hashlib.md5(cloid.encode("utf-8")).hexdigest()
                cloid_obj = Cloid.from_str(hex_str)
            return self.exchange.order(
                symbol, is_buy_to_close, rounded_sz, limit_px,
                order_type={"trigger": {"isMarket": True, "triggerPx": float(rounded_px), "tpsl": "sl"}},
                reduce_only=True,
                cloid=cloid_obj
            )
        except Exception as e:
            if _is_transient_gateway_exc(e):
                raise
            print(f"--> [Gateway Warning] Failed to place trigger stop for {symbol}: {e}", flush=True)
            return {"error": str(e)}

    def place_trigger_tp(self, symbol: str, is_buy_to_close: bool, size: float, trigger_price: float, cloid: Optional[str] = None) -> Dict[str, Any]:
        if not self.exchange:
            return {}
        try:
            rounded_sz = abs(self.round_sz(symbol, size))
            rounded_px = self.round_px(symbol, trigger_price)
            if rounded_sz <= 0 or rounded_px <= 0:
                return {}
            # Marketable 3.0% slippage collar in the closing direction (BUY above trigger, SELL below trigger)
            raw_limit_px = rounded_px * 1.030 if is_buy_to_close else rounded_px * 0.970
            limit_px = self.round_px(symbol, raw_limit_px)
            cloid_obj = None
            if cloid:
                hex_str = "0x" + hashlib.md5(cloid.encode("utf-8")).hexdigest()
                cloid_obj = Cloid.from_str(hex_str)
            return self.exchange.order(
                symbol, is_buy_to_close, rounded_sz, limit_px,
                order_type={"trigger": {"isMarket": True, "triggerPx": float(rounded_px), "tpsl": "tp"}},
                reduce_only=True,
                cloid=cloid_obj
            )
        except Exception as e:
            if _is_transient_gateway_exc(e):
                raise
            print(f"--> [Gateway Warning] Failed to place trigger TP for {symbol}: {e}", flush=True)
            return {"error": str(e)}

    def get_oracle_price(self, symbol: str) -> float:
        try:
            ctxs = self.info.meta_and_asset_ctxs()[1]
            universe = [t["name"] for t in self.meta["universe"]]
            if symbol in universe:
                idx = universe.index(symbol)
                return float(ctxs[idx].get("oraclePx", 0.0))
        except Exception:
            pass
        try:
            return self.get_mid_price(symbol)
        except Exception:
            return 0.0

    def close_position(self, symbol: str, size: float, is_long: bool) -> Dict[str, Any]:
        """
        Multi-Stage Emergency Position Exit (Partial-Fill Safe):
          Stage 1: 5-Tick Marketable Limit IOC Sweep anchored to live L2 BBO.
          Stage 2: Wide 5% / Oracle-Collar Aggressive IOC Sweep for any remaining unfilled size.
          Stage 3: Resting GTC Reduce-Only Marketable Limit fallback if book has zero resting liquidity.
        """
        if not self.exchange:
            return {}
        try:
            is_buy_to_close = not is_long
            rounded_sz = abs(self.round_sz(symbol, size))
            if rounded_sz <= 0:
                return {}

            oracle_px = self.get_oracle_price(symbol)
            try:
                best_bid, best_ask, mid = self.get_bbo_and_mid(symbol)
            except Exception:
                # Survive one-sided / empty L2 books (e.g. broken Testnet book or flash vacuum) via oraclePx fallback
                l2 = {}
                try:
                    l2 = self.info.l2_snapshot(symbol)
                except Exception:
                    pass
                bids, asks = l2.get("levels", [[], []]) if isinstance(l2, dict) else ([], [])
                ref_px = oracle_px if oracle_px > 0 else 0.0
                if ref_px <= 0:
                    if bids:
                        ref_px = float(bids[0]["px"])
                    elif asks:
                        ref_px = float(asks[0]["px"])
                if ref_px <= 0:
                    raise ValueError(f"Orderbook empty and oracle unavailable for {symbol}")
                mid = ref_px
                best_bid = float(bids[0]["px"]) if bids else mid * 0.995
                best_ask = float(asks[0]["px"]) if asks else mid * 1.005

            tick_sz = self.get_tick_size(symbol, mid)

            # Stage 1: 5-Tick Marketable Limit Sweep across opposing BBO
            stage1_raw = (best_ask + 5.0 * tick_sz) if is_buy_to_close else max(tick_sz, best_bid - 5.0 * tick_sz)
            if oracle_px > 0:
                if is_buy_to_close:
                    stage1_raw = min(stage1_raw, max(best_ask, oracle_px * 1.045))
                else:
                    stage1_raw = max(stage1_raw, min(best_bid, oracle_px * 0.955))
            stage1_px = self.round_px(symbol, stage1_raw)

            res1 = self.exchange.order(
                symbol, is_buy_to_close, rounded_sz, stage1_px,
                order_type={"limit": {"tif": "Ioc"}}, reduce_only=True
            )
            statuses1 = res1.get("response", {}).get("data", {}).get("statuses", [{}]) if isinstance(res1, dict) else [{}]
            first1 = statuses1[0] if statuses1 else {}

            rem_sz = rounded_sz
            if isinstance(first1, dict):
                if "resting" in first1:
                    return res1
                if "filled" in first1:
                    filled_obj = first1.get("filled")
                    filled_sz = float(filled_obj.get("totalSz", rounded_sz)) if isinstance(filled_obj, dict) else rounded_sz
                    rem_sz = abs(self.round_sz(symbol, max(0.0, rounded_sz - filled_sz)))
                    if rem_sz <= 0:
                        return res1

            # Stage 2: Wide 5% / Oracle-Collar Aggressive IOC Sweep on remaining unfilled size `rem_sz`
            raw_slip = mid * 1.05 if is_buy_to_close else mid * 0.95
            if oracle_px > 0:
                if is_buy_to_close:
                    raw_slip = min(max(raw_slip, best_ask), oracle_px * 1.045)
                else:
                    raw_slip = max(min(raw_slip, best_bid), oracle_px * 0.955)

            slip_px = self.round_px(symbol, raw_slip)
            res2 = self.exchange.order(
                symbol, is_buy_to_close, rem_sz, slip_px,
                order_type={"limit": {"tif": "Ioc"}}, reduce_only=True
            )
            statuses2 = res2.get("response", {}).get("data", {}).get("statuses", [{}]) if isinstance(res2, dict) else [{}]
            first2 = statuses2[0] if statuses2 else {}

            rem_sz2 = rem_sz
            if isinstance(first2, dict) and "filled" in first2:
                filled_obj2 = first2.get("filled")
                filled_sz2 = float(filled_obj2.get("totalSz", rem_sz)) if isinstance(filled_obj2, dict) else rem_sz
                rem_sz2 = abs(self.round_sz(symbol, max(0.0, rem_sz - filled_sz2)))
                if rem_sz2 <= 0:
                    return res2

            if rem_sz2 > 0 and isinstance(first2, dict) and (
                ("error" in first2)
                or ("filled" in first2)
            ):
                # Stage 3: Book has insufficient resting liquidity -> place GTC reduce-only at collar for remainder
                return self.exchange.order(
                    symbol, is_buy_to_close, rem_sz2, slip_px,
                    order_type={"limit": {"tif": "Gtc"}}, reduce_only=True
                )
            return res2
        except Exception as e:
            if _is_transient_gateway_exc(e):
                raise
            print(f"--> [Gateway Warning] Failed to close position for {symbol}: {e}", flush=True)
            return {"error": str(e)}

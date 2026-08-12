import os
import sqlite3
import datetime
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
from eth_account import Account
import eth_utils

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

from execution.base_executor import AbstractExecutionEngine, Order, Fill

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [HYPERLIQUID] %(message)s")

class HyperliquidExecutionEngine(AbstractExecutionEngine):
    def __init__(self, db_path: str = "live_execution_telemetry.db", is_testnet: bool = True):
        self.db_path = db_path
        self.is_testnet = is_testnet
        self.api_url = constants.TESTNET_API_URL if is_testnet else constants.MAINNET_API_URL
        
        raw_private = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
        raw_master = os.getenv("HYPERLIQUID_MASTER_ADDRESS", "")
        
        if not raw_private:
            raise ValueError("HYPERLIQUID_PRIVATE_KEY missing from .env file!")
            
        clean_private = raw_private.strip().replace('"', '').replace("'", "")
        self.account = Account.from_key(clean_private)
        self.agent_address = eth_utils.to_checksum_address(self.account.address)
        
        if raw_master:
            clean_master = raw_master.strip().replace('"', '').replace("'", "").lower()
            self.master_address = eth_utils.to_checksum_address(clean_master)
        else:
            self.master_address = self.agent_address
        
        logging.info(f"Agent Wallet: {self.agent_address}")
        logging.info(f"Master Account (Equity/Positions): {self.master_address}")
        logging.info(f"Target Endpoint: {'TESTNET' if is_testnet else 'MAINNET'} ({self.api_url})")

        self.info = Info(self.api_url, skip_ws=True)
        self.exchange = Exchange(self.account, self.api_url, account_address=self.master_address)
        
        self.sz_decimals: Dict[str, int] = {}
        self.max_leverage_map: Dict[str, int] = {}
        self._refresh_asset_metadata()
        self._init_db()

    def _refresh_asset_metadata(self):
        try:
            meta = self.info.meta()
            for asset in meta.get("universe", []):
                coin = asset["name"]
                self.sz_decimals[coin] = asset["szDecimals"]
                self.max_leverage_map[coin] = asset.get("maxLeverage", 50)
            logging.info(f"Loaded metadata for {len(self.sz_decimals)} Hyperliquid assets.")
        except Exception as e:
            logging.error(f"Failed to fetch Hyperliquid asset metadata: {e}")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_telemetry (
                order_id TEXT PRIMARY KEY, symbol TEXT, regime TEXT,
                predicted_prob REAL, kelly_fraction REAL, order_side TEXT,
                intended_limit_price REAL, actual_fill_price REAL, estimated_slippage REAL,
                size_notional REAL, status TEXT, exit_reason TEXT, net_pnl REAL,
                fee_paid REAL, entry_time TEXT, exit_time TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _clean_coin_symbol(self, ticker: str) -> str:
        return ticker.upper().replace("USD", "").replace("USDT", "").replace("-PERP", "")

    def submit_order(self, order: Order) -> bool:
        coin = self._clean_coin_symbol(order.symbol)
        if coin not in self.sz_decimals:
            logging.warning(f"Coin '{coin}' not supported on Hyperliquid. Skipping order.")
            return False

        sz_dec = self.sz_decimals[coin]
        is_buy = (order.side.upper() == "BUY")

        try:
            lev = getattr(order, "leverage", 10)
            self.exchange.update_leverage(int(lev), coin, is_cross=True)
            
            mids = self.info.all_mids()
            mid_price = float(mids.get(coin, order.price))
            
            base_sz = round(order.size_notional / mid_price, sz_dec)
            if base_sz <= 0:
                logging.warning(f"Calculated size for {coin} is 0 after decimal rounding ({sz_dec} dec). Skipping.")
                return False

            logging.info(f"Placing Order: [{order.side}] {coin} | Sz: {base_sz} (${order.size_notional:,.2f}) @ ${order.price:,.4f}")

            order_result = self.exchange.order(
                name=coin, is_buy=is_buy, sz=base_sz, limit_px=round(order.price, 4),
                order_type={"limit": {"tif": "Gtc"}}
            )
            
            status_data = order_result.get("response", {}).get("data", {}).get("statuses", [{}])[0]
            if "error" in status_data:
                logging.error(f"Hyperliquid Order Rejected for {coin}: {status_data['error']}")
                return False

            if order.take_profit > 0:
                self.exchange.order(
                    name=coin, is_buy=not is_buy, sz=base_sz, limit_px=round(order.take_profit, 4),
                    order_type={"trigger": {"isMarket": True, "triggerPx": round(order.take_profit, 4), "tpsl": "tp"}},
                    reduce_only=True
                )

            if order.stop_loss > 0:
                self.exchange.order(
                    name=coin, is_buy=not is_buy, sz=base_sz, limit_px=round(order.stop_loss, 4),
                    order_type={"trigger": {"isMarket": True, "triggerPx": round(order.stop_loss, 4), "tpsl": "sl"}},
                    reduce_only=True
                )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO execution_telemetry (order_id, symbol, regime, predicted_prob, kelly_fraction, order_side, intended_limit_price, actual_fill_price, size_notional, status, entry_time, order.signal_price_binance, order.live_price_hl, order.basis_drift_pct, order.limit_offset_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?)
            """, (order.order_id, order.symbol, order.regime, order.p_tp, order.kelly_fraction, order.side, order.price, mid_price, order.size_notional, order.timestamp.isoformat(), getattr(order, getattr(order, "signal_price_binance", 0.0), 0.0), getattr(order, getattr(order, "live_price_hl", 0.0), 0.0), getattr(order, getattr(order, "basis_drift_pct", 0.0), 0.0), getattr(order, getattr(order, "limit_offset_pct", 0.0), 0.0)))
            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logging.error(f"Exception submitting order to Hyperliquid: {e}")
            return False

    def process_market_update(self, current_timestamp: datetime.datetime, ticker_data: Dict[str, dict]) -> List[Fill]:
        return []

    def get_open_positions(self) -> Dict[str, dict]:
        user_state = self.info.user_state(self.master_address)
        if "error" in user_state:
            raise ValueError(f"Hyperliquid API Error fetching positions: {user_state}")
            
        pos_dict = {}
        for pos in (user_state.get("assetPositions") or []):
            p = pos.get("position") or {}
            coin = p.get("coin")
            szi = float(p.get("szi") or 0.0)
            if szi != 0:
                pos_dict[coin] = {
                    "size": szi, "entry_price": float(p.get("entryPx") or 0.0),
                    "unrealized_pnl": float(p.get("unrealizedPnl") or 0.0),
                    "return_on_equity": float(p.get("returnOnEquity") or 0.0)
                }
        return pos_dict

    def get_account_equity(self) -> float:
        try:
            user_state = self.info.user_state(self.master_address)
            perps_val = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
            
            spot_state = self.info.spot_user_state(self.master_address)
            spot_total, spot_hold = 0.0, 0.0
            for b in spot_state.get("balances", []):
                if b.get("coin") == "USDC":
                    spot_total = float(b.get("total", 0.0))
                    spot_hold = float(b.get("hold", 0.0))
            
            # Net unallocated spot + perps value
            unallocated_spot = spot_total - spot_hold
            return perps_val + unallocated_spot
        except Exception as e:
            logging.error(f"Error fetching account equity: {e}")
            return 0.0

    def get_available_margin(self, leverage: float = 10.0) -> float:
        user_state = self.info.user_state(self.master_address)
        if "error" in user_state:
            raise ValueError(f"Hyperliquid API Error fetching margin: {user_state}")
            
        cv = float((user_state.get("crossMarginSummary") or {}).get("accountValue") or 0.0)
        cm = float((user_state.get("crossMarginSummary") or {}).get("totalMarginUsed") or 0.0)
        
        mv = float((user_state.get("marginSummary") or {}).get("accountValue") or 0.0)
        mm = float((user_state.get("marginSummary") or {}).get("totalMarginUsed") or 0.0)
        
        wd = float(user_state.get("withdrawable") or 0.0)
        
        if cv > 0:
            account_val, total_margin = cv, cm
        elif mv > 0:
            account_val, total_margin = mv, mm
        else:
            account_val, total_margin = wd, 0.0
            
        if account_val == 0.0:
            try:
                spot_state = self.info.spot_user_state(self.master_address)
                for b in (spot_state.get("balances") or []):
                    if b.get("coin") == "USDC":
                        account_val = float(b.get("total") or 0.0)
            except Exception:
                pass
                
        return max(0.0, account_val - total_margin)

    def cancel_stale_orders(self, open_positions: dict = None) -> int:
        """Cancels resting limit/trigger orders for coins that do not have an active open position."""
        if open_positions is None:
            open_positions = self.get_open_positions()
            
        try:
            addr = getattr(self, 'wallet_address', None) or getattr(self, 'account', None)
            if hasattr(addr, 'address'):
                addr = addr.address
            
            info_client = getattr(self, 'info', None)
            exchange_client = getattr(self, 'exchange', None)
            
            if not info_client or not exchange_client or not addr:
                logging.warning("Cannot cancel orders: missing info, exchange, or wallet address attribute.")
                return 0

            open_orders = info_client.open_orders(addr)
            if not open_orders:
                logging.info("[GARBAGE COLLECTOR] No resting orders found on exchange.")
                return 0

            canceled_count = 0
            for ord_info in open_orders:
                coin = ord_info.get("coin")
                oid = ord_info.get("oid")
                
                # If the coin has NO active position open, cancel its resting orders
                if coin and coin not in open_positions and oid is not None:
                    res = exchange_client.cancel(coin, oid)
                    if res.get("status") == "ok":
                        canceled_count += 1
                        logging.info(f"[GARBAGE COLLECTOR] Cancelled stale order for {coin} (OID: {oid})")
                    else:
                        logging.warning(f"[GARBAGE COLLECTOR] Failed to cancel {coin} (OID: {oid}): {res}")

            return canceled_count
        except Exception as e:
            logging.error(f"[GARBAGE COLLECTOR] Exception during order cancellation: {e}")
            return 0

import sqlite3
import datetime
import uuid
from typing import Dict, List, Optional
from execution.base_executor import AbstractExecutionEngine, Order, Fill

class PaperExecutionEngine(AbstractExecutionEngine):
    def __init__(self, initial_capital: float = 1000.0, db_path: str = "execution_telemetry.db"):
        self.capital = initial_capital
        self.peak_capital = initial_capital
        self.db_path = db_path
        self.pending_orders: Dict[str, Order] = {}
        self.active_positions: Dict[str, dict] = {}
        self.roundtrip_fee_pct = 0.0014  # 0.14% taker fee + slippage buffer
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_telemetry (
                order_id TEXT PRIMARY KEY,
                symbol TEXT,
                regime TEXT,
                predicted_prob REAL,
                kelly_fraction REAL,
                order_side TEXT,
                intended_limit_price REAL,
                actual_fill_price REAL,
                estimated_slippage REAL,
                size_notional REAL,
                status TEXT,
                exit_reason TEXT,
                net_pnl REAL,
                fee_paid REAL,
                entry_time TEXT,
                exit_time TEXT
            )
        """)
        conn.commit()
        conn.close()

    def submit_order(self, order: Order) -> bool:
        if len(self.active_positions) + len(self.pending_orders) >= 5:
            return False
            
        self.pending_orders[order.order_id] = order
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO execution_telemetry 
            (order_id, symbol, regime, predicted_prob, kelly_fraction, order_side, intended_limit_price, size_notional, status, entry_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
        """, (order.order_id, order.symbol, order.regime, order.p_tp, order.kelly_fraction, order.side, order.price, order.size_notional, order.timestamp.isoformat()))
        conn.commit()
        conn.close()
        return True

    def process_market_update(self, current_timestamp: datetime.datetime, ticker_data: Dict[str, dict]) -> List[Fill]:
        fills = []
        
        # 1. Process Pending Entries
        filled_order_ids = []
        for order_id, order in list(self.pending_orders.items()):
            symbol_data = ticker_data.get(order.symbol)
            if not symbol_data:
                continue
                
            low_price = symbol_data['low']
            high_price = symbol_data['high']
            
            # Fill Condition
            if (order.side == 'BUY' and low_price <= order.price) or (order.side == 'SELL' and high_price >= order.price):
                fill_price = order.price
                slippage = 0.0
                entry_fee = order.size_notional * (self.roundtrip_fee_pct / 2.0)
                
                # Deduct entry fee immediately from capital
                self.capital -= entry_fee
                
                self.active_positions[order_id] = {
                    'order': order,
                    'fill_price': fill_price,
                    'notional': order.size_notional,
                    'entry_time': current_timestamp,
                    'entry_fee': entry_fee
                }
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE execution_telemetry 
                    SET status = 'OPEN', actual_fill_price = ?, estimated_slippage = ?, fee_paid = ?
                    WHERE order_id = ?
                """, (fill_price, slippage, entry_fee, order_id))
                conn.commit()
                conn.close()
                
                filled_order_ids.append(order_id)
                fills.append(Fill(order_id, order.symbol, order.side, fill_price, order.size_notional, entry_fee, slippage, current_timestamp))

        for oid in filled_order_ids:
            del self.pending_orders[oid]

        # 2. Process Active Position Exits (TP / SL)
        closed_position_ids = []
        for order_id, pos in list(self.active_positions.items()):
            order = pos['order']
            symbol_data = ticker_data.get(order.symbol)
            if not symbol_data:
                continue

            low_price = symbol_data['low']
            high_price = symbol_data['high']
            
            exit_reason = None
            exit_price = 0.0

            if order.side == 'BUY':
                if high_price >= order.take_profit:
                    exit_reason, exit_price = 'TP_HIT', order.take_profit
                elif low_price <= order.stop_loss:
                    exit_reason, exit_price = 'SL_HIT', order.stop_loss
            elif order.side == 'SELL':
                if low_price <= order.take_profit:
                    exit_reason, exit_price = 'TP_HIT', order.take_profit
                elif high_price >= order.stop_loss:
                    exit_reason, exit_price = 'SL_HIT', order.stop_loss

            if exit_reason:
                price_return = (exit_price - pos['fill_price']) / pos['fill_price'] if order.side == 'BUY' else (pos['fill_price'] - exit_price) / pos['fill_price']
                gross_pnl = pos['notional'] * price_return
                exit_fee = pos['notional'] * (self.roundtrip_fee_pct / 2.0)
                
                net_pnl = gross_pnl - exit_fee
                self.capital += (pos['notional'] / 10.0) + gross_pnl - exit_fee  # Release margin + pnl - exit fee

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE execution_telemetry 
                    SET status = 'CLOSED', exit_reason = ?, net_pnl = ?, fee_paid = ?, exit_time = ?
                    WHERE order_id = ?
                """, (exit_reason, net_pnl, pos['entry_fee'] + exit_fee, current_timestamp.isoformat(), order_id))
                conn.commit()
                conn.close()

                closed_position_ids.append(order_id)
                fills.append(Fill(order_id, order.symbol, 'SELL' if order.side == 'BUY' else 'BUY', exit_price, pos['notional'], exit_fee, 0.0, current_timestamp, exit_reason))

        for oid in closed_position_ids:
            del self.active_positions[oid]

        return fills

    def get_open_positions(self) -> Dict[str, dict]:
        return self.active_positions

    def get_account_equity(self) -> float:
        return self.capital

    def get_available_margin(self, leverage: float = 10.0) -> float:
        used_margin = sum(pos['notional'] / leverage for pos in self.active_positions.values())
        return max(0.0, self.capital - used_margin)

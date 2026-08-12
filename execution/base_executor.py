from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, List
import datetime

@dataclass
class Order:
    order_id: str
    symbol: str
    side: str                # 'BUY' or 'SELL'
    order_type: str          # 'LIMIT' or 'MARKET'
    price: float
    size_notional: float
    stop_loss: float
    take_profit: float
    timestamp: datetime.datetime
    regime: str
    p_tp: float
    kelly_fraction: float
    signal_price_binance: Optional[float] = 0.0
    live_price_hl: Optional[float] = 0.0
    basis_drift_pct: Optional[float] = 0.0
    limit_offset_pct: Optional[float] = 0.0

@dataclass
class Fill:
    order_id: str
    symbol: str
    side: str
    fill_price: float
    size_notional: float
    fee_paid: float
    slippage: float
    fill_timestamp: datetime.datetime
    exit_reason: Optional[str] = None

class AbstractExecutionEngine(ABC):
    
    @abstractmethod
    def submit_order(self, order: Order) -> bool:
        """Submits a new order to the engine."""
        pass

    @abstractmethod
    def process_market_update(self, current_timestamp: datetime.datetime, ticker_data: Dict[str, dict]) -> List[Fill]:
        """Evaluates pending orders against new market data (candle high/low/close)."""
        pass

    @abstractmethod
    def get_open_positions(self) -> Dict[str, dict]:
        """Returns currently active positions."""
        pass

    @abstractmethod
    def get_account_equity(self) -> float:
        """Returns total portfolio balance."""
        pass

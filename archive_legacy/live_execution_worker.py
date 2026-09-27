import os
import time
import logging
import datetime
import numpy as np
import pandas as pd
import joblib
from catboost import CatBoostClassifier
from validate_live_features import LiveFeatureValidationGate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [EXEC_WORKER] %(message)s"
)

class HyperliquidMockClient:
    """Mock client representing the Hyperliquid Python SDK (eth_account signed)"""
    def __init__(self):
        self.account_equity = 1000.00  # Starting with $1,000
        self.positions = {}
        
    def get_equity(self):
        return self.account_equity
        
    def execute_order(self, ticker, side, size_usd):
        logging.info(f"EXCHANGE: Executing {side} on {ticker} | Size: ${size_usd:,.2f}")
        self.positions[ticker] = {'side': side, 'size': size_usd, 'entry_price': 65000.0} # Mock entry

class RiskAndPositionManager:
    def __init__(self, max_drawdown_pct=0.15, kelly_fraction=0.5, win_rate=0.71, payoff_ratio=1.1):
        self.max_drawdown_pct = max_drawdown_pct
        self.kelly_fraction = kelly_fraction  # 0.5 = Half-Kelly
        
        # Kelly Criterion: f* = p - (q / b)
        # p = win rate (71%), q = loss rate (29%), b = payoff ratio (Avg Win / Avg Loss)
        p = win_rate
        q = 1.0 - p
        self.full_kelly = p - (q / payoff_ratio)
        self.target_risk_pct = self.full_kelly * self.kelly_fraction
        
        self.peak_equity = 0.0
        self.circuit_breaker_active = False
        
        logging.info(f"Risk Manager Initialized. Half-Kelly Target Risk: {self.target_risk_pct*100:.2f}% of Equity")

    def check_circuit_breaker(self, current_equity):
        """High-Water Mark Circuit Breaker"""
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        if drawdown >= self.max_drawdown_pct:
            logging.error(f"CIRCUIT BREAKER TRIPPED! Drawdown: {drawdown*100:.2f}%. Halting execution.")
            self.circuit_breaker_active = True
            return True
        return False

    def calculate_position_size(self, current_equity, leverage=10.0):
        """Calculates exact dollar size for the order based on Half-Kelly and Leverage"""
        # Base risk capital allocated to this trade
        risk_capital = current_equity * self.target_risk_pct
        
        # Notional position size using 10x leverage
        notional_size = risk_capital * leverage
        return notional_size

    def calculate_trailing_stop(self, side, entry_price, highest_high, lowest_low, current_atr):
        """Chandelier Exit logic (1.5x ATR trailing stop)"""
        atr_multiplier = 1.5
        
        if side == "LONG":
            stop_price = highest_high - (current_atr * atr_multiplier)
            # Stop price cannot move backwards (must trail up)
            return stop_price
        elif side == "SHORT":
            stop_price = lowest_low + (current_atr * atr_multiplier)
            return stop_price

class LiveExecutionWorker:
    def __init__(self, bundle_dir="model_bundle_v1.0.0"):
        self.bundle_dir = bundle_dir
        self.exchange = HyperliquidMockClient()
        self.risk_manager = RiskAndPositionManager()
        self.gate = LiveFeatureValidationGate(bundle_dir=self.bundle_dir)
        
        self.load_models()

    def load_models(self):
        logging.info("Loading Production Models and Calibrators...")
        self.model_long = CatBoostClassifier().load_model(f"{self.bundle_dir}/long_expert.cbm")
        self.model_short = CatBoostClassifier().load_model(f"{self.bundle_dir}/short_expert.cbm")
        self.calibrator_long = joblib.load(f"{self.bundle_dir}/calibrator_long.pkl")
        self.calibrator_short = joblib.load(f"{self.bundle_dir}/calibrator_short.pkl")

    def process_live_candle(self, live_feature_dict):
        # 1. Check Circuit Breaker
        current_equity = self.exchange.get_equity()
        if self.risk_manager.check_circuit_breaker(current_equity):
            return # Block all execution if circuit breaker is tripped
            
        # 2. Pass through Validation Gate
        current_vol_percentile = 0.85 # Mock vol percentile
        is_valid, df_vec, reason = self.gate.validate_payload(live_feature_dict, current_vol_percentile)
        
        if not is_valid:
            logging.warning(f"Feature Gate Rejected Payload: {reason}")
            return
            
        # 3. Model Inference
        raw_prob_long = self.model_long.predict_proba(df_vec)[:, 1][0]
        raw_prob_short = self.model_short.predict_proba(df_vec)[:, 1][0]
        
        # 4. Probability Calibration
        cal_prob_long = self.calibrator_long.predict_proba(np.array([[raw_prob_long]]))[:, 1][0] if hasattr(self.calibrator_long, 'predict_proba') else self.calibrator_long.predict([raw_prob_long])[0]
        cal_prob_short = self.calibrator_short.predict_proba(np.array([[raw_prob_short]]))[:, 1][0] if hasattr(self.calibrator_short, 'predict_proba') else self.calibrator_short.predict([raw_prob_short])[0]
        
        logging.info(f"Calibrated Probs -> LONG: {cal_prob_long:.3f} | SHORT: {cal_prob_short:.3f}")

        # 5. Signal Execution & Sizing
        # Assuming thresholds dictate > 0.51 is a valid signal
        if cal_prob_long > 0.51:
            size_usd = self.risk_manager.calculate_position_size(current_equity, leverage=10.0)
            self.exchange.execute_order(live_feature_dict['ticker'], "LONG", size_usd)
            
            # Example Trailing Stop Calculation Printout
            current_atr = live_feature_dict.get('atr_14', 100) # Mock ATR
            stop = self.risk_manager.calculate_trailing_stop("LONG", 65000, 65500, 65000, current_atr)
            logging.info(f"Trailing Stop set at: ${stop:.2f}")

        elif cal_prob_short > 0.51:
            size_usd = self.risk_manager.calculate_position_size(current_equity, leverage=10.0)
            self.exchange.execute_order(live_feature_dict['ticker'], "SHORT", size_usd)

if __name__ == "__main__":
    worker = LiveExecutionWorker()
    
    # Mocking a live incoming websocket payload
    mock_payload = {
        'ticker': 'BTC-PERP',
        'hour_of_day': '14',
        'day_of_week': '3',
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'atr_14': 150.5
    }
    # Populate the rest of the required expected base features with dummy data for the test
    for feat in worker.gate.expected_base_features:
        if feat not in mock_payload:
            mock_payload[feat] = 1.0
            
    print("\n--- Simulating Live Websocket Tick ---")
    worker.process_live_candle(mock_payload)

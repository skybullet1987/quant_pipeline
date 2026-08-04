import json
import logging
import datetime
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [FEATURE_GATE] %(message)s"
)

class LiveFeatureValidationGate:
    def __init__(self, bundle_dir="model_bundle_v1.0.0"):
        self.bundle_dir = bundle_dir
        self.load_bundle_configs()

    def load_bundle_configs(self):
        try:
            with open(f"{self.bundle_dir}/feature_schema.json", "r") as f:
                self.schema = json.load(f)
            with open(f"{self.bundle_dir}/thresholds.json", "r") as f:
                self.thresholds = json.load(f)
            
            self.expected_all_features = self.schema['all_features']
            self.expected_base_features = self.schema['base_features']
            self.expected_cat_features = self.schema['cat_features']
            self.vol_gate = self.thresholds.get('volatility_percentile_gate', 0.75)
            
            logging.info(f"Loaded schema gate: {len(self.expected_all_features)} features expected.")
        except Exception as e:
            logging.error(f"Failed to load model bundle configuration from {self.bundle_dir}: {e}")
            raise e

    def validate_payload(self, live_dict, current_vol_percentile=1.0):
        """
        Validates a single live 1-minute incoming feature dictionary.
        
        Returns:
            (bool, pd.DataFrame or None, str): (is_valid, aligned_dataframe, rejection_reason)
        """
        # 1. TIMESTAMP LATENCY CHECK
        if 'timestamp' in live_dict:
            try:
                msg_time = pd.to_datetime(live_dict['timestamp'], utc=True)
                now_time = datetime.datetime.now(datetime.timezone.utc)
                latency_seconds = (now_time - msg_time).total_seconds()
                
                if latency_seconds > 120.0:  # Older than 2 minutes
                    return False, None, f"STALE DATA: Payload timestamp is {latency_seconds:.1f}s old."
            except Exception as e:
                return False, None, f"TIMESTAMP ERROR: Could not parse timestamp ({e})."

        # 2. SCHEMA INTEGRITY CHECK
        missing_cols = [c for c in self.expected_all_features if c not in live_dict]
        if missing_cols:
            return False, None, f"SCHEMA MISMATCH: Missing {len(missing_cols)} expected features: {missing_cols[:3]}..."

        # 3. NULL / NAN / INF CHECK
        for col in self.expected_base_features:
            val = live_dict[col]
            if val is None or pd.isna(val) or np.isinf(val):
                return False, None, f"CORRUPTED VALUE: Feature '{col}' contains invalid value ({val})."

        # 4. OUTLIER SPIKE / SANITY CHECK (Zero or negative price/volatility protection)
        for col in self.expected_base_features:
            if 'price' in col or 'close' in col or 'atr' in col:
                if live_dict[col] <= 0:
                    return False, None, f"OUTLIER SANITY ERROR: '{col}' is non-positive ({live_dict[col]})."

        # 5. REGIME GATE CHECK (Top 25% Volatility Filter)
        if current_vol_percentile < self.vol_gate:
            return False, None, f"REGIME GATE LOCKED: Current Vol Percentile ({current_vol_percentile:.2f}) < Required Gate ({self.vol_gate:.2f})."

        # 6. FEATURE ALIGNMENT & TYPE CASTING
        try:
            df = pd.DataFrame([live_dict])
            
            # Ensure categorical types are string-encoded as expected by CatBoost
            for col in self.expected_cat_features:
                df[col] = df[col].astype(str)
                
            # Strict column reordering to match exact bundle training schema
            df_aligned = df[self.expected_all_features].copy()
            
            return True, df_aligned, "PASSED"
        except Exception as e:
            return False, None, f"ALIGNMENT ERROR: Failed to construct feature vector ({e})."

if __name__ == "__main__":
    print("Testing Live Feature Validation Gate...")
    
    # Initialize gate using model_bundle_v1.0.0/
    gate = LiveFeatureValidationGate(bundle_dir="model_bundle_v1.0.0")
    
    # Mock valid payload
    mock_payload = {feat: 1.0 for feat in gate.expected_base_features}
    mock_payload['ticker'] = 'BTC-PERP'
    mock_payload['hour_of_day'] = '14'
    mock_payload['day_of_week'] = '3'
    mock_payload['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Run Test 1: Valid Payload in High Vol Regime
    is_valid, df_vec, reason = gate.validate_payload(mock_payload, current_vol_percentile=0.85)
    print(f"\n[Test 1 High-Vol]: Valid={is_valid} | Reason={reason}")
    if is_valid:
        print(f"Aligned Vector Shape: {df_vec.shape}")

    # Run Test 2: Low Vol Regime Lockout
    is_valid, df_vec, reason = gate.validate_payload(mock_payload, current_vol_percentile=0.40)
    print(f"\n[Test 2 Low-Vol]: Valid={is_valid} | Reason={reason}")

    # Run Test 3: Corrupted NaN Value
    corrupted_payload = mock_payload.copy()
    corrupted_payload[gate.expected_base_features[0]] = np.nan
    is_valid, df_vec, reason = gate.validate_payload(corrupted_payload, current_vol_percentile=0.85)
    print(f"\n[Test 3 Corrupted NaN]: Valid={is_valid} | Reason={reason}")

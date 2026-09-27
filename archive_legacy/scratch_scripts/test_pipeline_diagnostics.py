import os
import joblib
import pandas as pd
import numpy as np
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.utils import constants
from dotenv import load_dotenv
from catboost import CatBoostClassifier, Pool

load_dotenv()
secret_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
account = Account.from_key(secret_key)
master_addr = os.getenv("HYPERLIQUID_MASTER_ADDRESS", "0x9703B71686219D34869e8FB89a93263f9e0d50A5")

info = Info(constants.TESTNET_API_URL, skip_ws=True)

# 1. Hyperliquid Account Inspection
print("\n" + "=" * 60)
print("1. HYPERLIQUID ACCOUNT STATE DIAGNOSTIC")
print("=" * 60)
user_state = info.user_state(master_addr)
spot_state = info.spot_user_state(master_addr)

print("Perp marginSummary     :", user_state.get("marginSummary"))
print("Perp crossMarginSummary:", user_state.get("crossMarginSummary"))
print("Perp withdrawable      :", user_state.get("withdrawable"))
print("Spot balances          :", spot_state.get("balances"))

# 2. Inspect Calibrator and Models
print("\n" + "=" * 60)
print("2. MODEL & CALIBRATOR DIAGNOSTIC")
print("=" * 60)
try:
    cal_s = joblib.load("models/prod/meta_calibrator_short.pkl")
    print("Meta Calibrator Short Type:", type(cal_s))
    dummy_inputs = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
    if hasattr(cal_s, 'predict_proba'):
        print("Calibrator predict_proba output:", cal_s.predict_proba(dummy_inputs.reshape(-1, 1)))
    elif hasattr(cal_s, 'predict'):
        print("Calibrator predict output      :", cal_s.predict(dummy_inputs))
except Exception as e:
    print("Calibrator inspection failed:", e)


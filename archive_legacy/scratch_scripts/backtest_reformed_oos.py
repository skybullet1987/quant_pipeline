#!/usr/bin/env python3
import glob
import os
import pandas as pd
import numpy as np
from tactical_regime import TacticalRegimeEngine
from risk_engine import PortfolioRiskEngine

print("\n" + "=" * 80)
print("       RUNNING REFORMED OOS WALK-FORWARD BACKTEST (TRUE CANDLE SIM)")
print("=" * 80)

# Check for processed features/candles or run via dagster asset
feature_files = sorted(glob.glob("data/oos_features_*.parquet") + glob.glob("oos_decisions_*.parquet"))
print(f"Located Data Assets: {len(feature_files)} files found.")

# Initialize Engines
tactical = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)
risk_engine = PortfolioRiskEngine(
    risk_budget_pct=0.015,       # 1.5% equity per SL
    max_slot_equity_pct=0.35,    # Max 35% equity notional per slot
    max_gross_leverage=2.00,
    atr_stop_multiplier=1.50
)

print("• Tactical Regime Engine Initialized (Dynamic Hurdle & Prior Multipliers)")
print("• Decoupled Volatility Sizer Initialized (1.5% Risk Budget / 1.5x ATR Stop)")
print("=" * 80 + "\n")

#!/usr/bin/env python3
"""
polymarket_daily_projections.py
===============================
Live Day-by-Day Equity, Net Profit & Phased Sleeve Graduation Projection Engine
(v4.2 Post-Purge Clean Roster Edition — Zero Quarantined Sleeves).

Dynamically anchors Day 0 to the REAL live collateral balance and closed trade ledger in
`data/polymarket/live_harvester_state.json`, tracks real-time shadow graduation progress
across all active non-quarantined sleeves in:
  - `data/alpha124/alpha124_shadow_state.json` (`D1`, `D1_QUIET`, `D1_4H`, `W1`, `W3`, `B2`, `M3`, `N1`, `U1`, `S5M`, `C1`, `S2`)
  - `data/polymarket/state_shadow_sol_v392.json` (`SLEEVE_SOL_V392_SHADOW`)
  - `data/polymarket/shadow_phase3_4_tracker.jsonl` (`SHADOW_PHASE3A_MAKER`)
  - `data/exp316/exp316_shadow_state.json` (`EXP316_TRACK_A_LATE_LOCK`)

Strictly excludes all quarantined/retired sleeves (`M4_SHOCK_STRIKE_CATCHUP`, `W2_ENSEMBLE_VALUE`,
`W2_MAKER_OVERROUND`, `M1_SVI_MAKER_SCALP`, `M2_STRIKE_CONVERGENCE`, `P1_PREOPEN_MAKER_STRADDLE`,
`B1_CONVEX_TAIL_YES`, and `SLEEVE_XRP_V392_SHADOW`), and enforces empirical CLOB L1/L2 depth caps:
  - P25 Conservative (Finland ~295ms RTT + variance/drawdown haircut)
  - P50 Base         (Current Finland VM + empirical D1/SOL/Phase3A/W1/B2 caps)
  - P75 Upside       (Low-latency <15ms non-restricted EU execution + full active roster)

Writes atomic JSON output to `data/polymarket/live_daily_projections.json` and prints a
human-readable day-by-day table for CLI / scheduled telemetry checks.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
LIVE_STATE_FILE = PIPELINE_ROOT / "data" / "polymarket" / "live_harvester_state.json"
ALPHA124_STATE_FILE = (
    PIPELINE_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json"
    if (PIPELINE_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json").exists()
    else PIPELINE_ROOT / "data" / "polymarket" / "alpha124_shadow_state.json"
)
EXP316_STATE_FILE = PIPELINE_ROOT / "data" / "exp316" / "exp316_shadow_state.json"
SOL_SHADOW_FILE = PIPELINE_ROOT / "data" / "polymarket" / "state_shadow_sol_v392.json"
XRP_SHADOW_FILE = PIPELINE_ROOT / "data" / "polymarket" / "state_shadow_xrp_v392.json"
PHASE34_TRACKER_FILE = PIPELINE_ROOT / "data" / "polymarket" / "shadow_phase3_4_tracker.jsonl"
RISK_CONFIG_FILE = PIPELINE_ROOT / "config" / "polymarket_risk_config.json"
STRATEGY_RISK_CONFIG_FILE = PIPELINE_ROOT / "config" / "polymarket_strategy_and_risk.json"
OUTPUT_JSON_FILE = PIPELINE_ROOT / "data" / "polymarket" / "live_daily_projections.json"

QUARANTINED_SLEEVES = frozenset({
    "M4_SHOCK_STRIKE_CATCHUP",
    "W2_ENSEMBLE_VALUE",
    "W2_MAKER_OVERROUND",
    "M1_SVI_MAKER_SCALP",
    "M2_STRIKE_CONVERGENCE",
    "P1_PREOPEN_MAKER_STRADDLE",
    "B1_CONVEX_TAIL_YES",
    "B4_TOUCHED_BARRIER_WICK_LOCK",
    "ZERO_FEE_MAKER_ANCHOR_BOX",
    "SLEEVE_XRP_V392_SHADOW",
    "D1_MAKER_ANCHOR_BOX",
    "ZF_INTRADAY_MAKER_BOX",
    "SHADOW_PHASE3A_MAKER",
    "NR_CONV_NO_BASKET_ARB",
})

DIRECTIONAL_ONLY_SLEEVES = frozenset({
    "SLEEVE_SOL_V392_SHADOW",
    "S5M_CHAINLINK_SNIPER",
    "S4H_CHAINLINK_CONVERGENCE",
    "U1_DAILY_UPDOWN_LOCK",
    "B2_BARRIER_NO_LOCK",
    "CM_SHOCK_PYTH_CATALYST",
    "EXP316_TRACK_A_LATE_LOCK",
})


GRADUATION_SPECS: List[Dict[str, Any]] = [
    {
        "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
        "wave": "Wave 1 (Live Graduated)",
        "target_day": 1,
        "min_days": 0.25,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 13.5,
        "l1_daily_pnl_cap_usd": 140.0,
    },
    {
        "sleeve": "D1_QUIET_BOOK_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 3,
        "min_days": 0.25,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 65.0,
    },
    {
        "sleeve": "D1_4H_DOMINANCE_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 60.0,
    },
    {
        "sleeve": "C1_BINARY_COMPLETE_SET",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "NR2_CONVERT_NO_SUBSET_ARB",
        "wave": "Wave 1 (m=2 Atomic Convert)",
        "target_day": 4,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "M3_LADDER_MONO_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "B3_BARRIER_MONO_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "D1_MAKER_ANCHOR_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 45.0,
    },
    {
        "sleeve": "N1_NEGRISK_CROSS_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 20.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "W3_WEATHER_SLATE_ARB",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "CM_B3_PYTH_BARRIER_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "SP1_NBA_ZERO_FEE_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "ZF_INTRADAY_MAKER_BOX",
        "wave": "Wave 1 (Fast-Track Maker Box 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 92.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "NR0_ZERO_FEE_SLATE_ARB",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "ZERO_FEE_MAKER_ANCHOR_BOX",
        "wave": "Wave 1 (Fast-Track Maker Box)",
        "target_day": 5,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 92.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "CTF_OVERROUND_MINT_SELL",
        "wave": "Wave 1 (Instant Mint-Sell 8/8)",
        "target_day": 4,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "TW1_COUNTING_TRUNCATION_AND_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 5,
        "min_days": 1.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "FED1_CENTRAL_BANK_LP_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "COND1_MACRO_PARTITION_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "D2_12PM_BINANCE_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 5,
        "min_days": 1.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "GAS1_AAA_GASOLINE_LOCK",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 20.0,
    },
    {
        "sleeve": "MKR_REWARD_LOCKED_CARRY",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 20.0,
    },
    {
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "wave": "Wave 1 (Live Graduated 8/8)",
        "target_day": 1,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 45.25,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 25.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 25.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 25.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 20.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 25.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 20.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "wave": "Wave 1 (Liquid-Guarded Live)",
        "target_day": 1,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 22.0,
        "l1_daily_pnl_cap_usd": 20.0,
    },
    {
        "sleeve": "SP4_MULTISPORT_CORRIDOR_DOMINANCE_BOX",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 25.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "LP2_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 25.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "NR1_CLOSED_PARTITION_COMPLETE_SET",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 25.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "NR2_CONVERT_NO_SUBSET_ARB",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 25.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "CRY_INC1_INTRADAY_STRIKE_INCLUSION_BOX",
        "wave": "Wave 1 (0-Loss Math Live)",
        "target_day": 1,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 25.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "SP2_NBA_ENDGAME_LOCK",
        "wave": "Wave 2 (Day 7 NBA Endgame)",
        "target_day": 7,
        "min_days": 3.0,
        "min_settled": 15,
        "min_wr_pct": 93.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 45.0,
    },
    {
        "sleeve": "W1_LOW_TROUGH_LOCK",
        "wave": "Wave 2 (Day 8 METAR Low)",
        "target_day": 8,
        "min_days": 4.0,
        "min_settled": 15,
        "min_wr_pct": 88.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 40.0,
    },
    {
        "sleeve": "SLEEVE_SOL_V392_SHADOW",
        "wave": "Wave 2 (Day 5 SOL)",
        "target_day": 5,
        "min_days": 1.5,
        "min_settled": 30,
        "min_wr_pct": 85.0,
        "source": "sol_shadow",
        "stage1_ticket_usd": 12.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "SHADOW_PHASE3A_MAKER",
        "wave": "Wave 2 (Day 6 Maker)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 25,
        "min_wr_pct": 80.0,
        "source": "phase3a_shadow",
        "stage1_ticket_usd": 14.0,
        "l1_daily_pnl_cap_usd": 32.0,
    },
    {
        "sleeve": "W1_SOLAR_PEAK_LOCK",
        "wave": "Wave 2 (Day 8 METAR)",
        "target_day": 8,
        "min_days": 5.0,
        "min_settled": 20,
        "min_wr_pct": 86.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 95.0,
    },
    {
        "sleeve": "B2_BARRIER_NO_LOCK",
        "wave": "Wave 2 (Day 8 Barrier)",
        "target_day": 8,
        "min_days": 5.0,
        "min_settled": 25,
        "min_wr_pct": 88.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 55.0,
    },
    {
        "sleeve": "CM_B2_PYTH_SESSION_NO_LOCK",
        "wave": "Wave 2 (Day 9 Pyth 0%-Fee)",
        "target_day": 9,
        "min_days": 5.0,
        "min_settled": 25,
        "min_wr_pct": 88.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 45.0,
    },
    {
        "sleeve": "CM_U1_PYTH_CLOSE_LOCK",
        "wave": "Wave 2 (Day 10 Pyth Close)",
        "target_day": 10,
        "min_days": 5.0,
        "min_settled": 25,
        "min_wr_pct": 88.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "EXP316_TRACK_A_LATE_LOCK",
        "wave": "Wave 2 (Day 10 Strike)",
        "target_day": 10,
        "min_days": 5.0,
        "min_settled": 25,
        "min_wr_pct": 80.0,
        "source": "exp316",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "U1_DAILY_UPDOWN_LOCK",
        "wave": "Wave 3 (Day 15 Daily)",
        "target_day": 15,
        "min_days": 10.0,
        "min_settled": 20,
        "min_wr_pct": 85.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "S5M_CHAINLINK_SNIPER",
        "wave": "Wave 3 (Day 15 5m)",
        "target_day": 15,
        "min_days": 7.0,
        "min_settled": 35,
        "min_wr_pct": 82.0,
        "source": "alpha124",
        "stage1_ticket_usd": 14.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "S4H_CHAINLINK_CONVERGENCE",
        "wave": "Wave 3 (Day 14 4h)",
        "target_day": 14,
        "min_days": 7.0,
        "min_settled": 25,
        "min_wr_pct": 85.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "CM_SHOCK_PYTH_CATALYST",
        "wave": "Wave 3 (Day 16 Macro Jump)",
        "target_day": 16,
        "min_days": 10.0,
        "min_settled": 25,
        "min_wr_pct": 82.0,
        "source": "alpha124",
        "stage1_ticket_usd": 14.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "S2_EXACT_TWAP_LOCK",
        "wave": "Wave 1 (Live Bridged S2MKR)",
        "target_day": 1,
        "min_days": 0.25,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 14.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        "wave": "Wave 1 (Live Bridged S2MKR)",
        "target_day": 1,
        "min_days": 0.25,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 14.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
        "wave": "Wave 1 (Live BOND2 Carry)",
        "target_day": 1,
        "min_days": 0.25,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 16.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "UMA_READY1_LIVENESS_PRIORITY",
        "wave": "Wave 1 (Live BOND1 Inherited)",
        "target_day": 1,
        "min_days": 0.25,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "W_PRUNE1_DEAD_NO_BOND",
        "wave": "Wave 1 (Live METAR Ratchet)",
        "target_day": 1,
        "min_days": 0.25,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
        "wave": "Wave 1 (Live Zero-Loss Math)",
        "target_day": 2,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "CTF_OVERROUND_MINT_SELL",
        "wave": "Wave 2 ($140 Pre-Split Gun)",
        "target_day": 5,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 28.0,
    },
]


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_phase3a_summary(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"closed": 0, "wins": 0, "pnl_usd": 0.0}
    closed = 0
    wins = 0
    pnl = 0.0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("status") != "RESOLVED":
                    continue
                if str(rec.get("event_type") or "") != "SHADOW_PHASE3A_MAKER_RESOLVED":
                    continue
                closed += 1
                p = float(rec.get("shadow_net_pnl_usd") or 0.0)
                pnl += p
                if p > 0.0 or rec.get("won") is True:
                    wins += 1
    except Exception:
        pass
    return {"closed": closed, "wins": wins, "pnl_usd": round(pnl, 2)}


def _parse_iso(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
    except Exception:
        return None


def compute_v393_ticket_size(
    equity: float,
    seed_threshold: float = 88.0,
    seed_ticket: float = 12.0,
    dynamic_pct: float = 0.18,
    scale_up_threshold: float = 110.0,
    scale_up_pct: float = 0.22,
    max_cap: float = 200.0,
    min_smooth_floor: float = 66.67,
) -> float:
    """Exact smooth dynamic sizing curve matching `config/polymarket_risk_config.json` & `polymarket_live_harvester.py`."""
    if equity < 48.0:
        return 0.0
    if equity < min_smooth_floor:
        return round(seed_ticket, 2)
    if equity < scale_up_threshold:
        return round(min(max_cap, max(seed_ticket, equity * dynamic_pct)), 2)
    return round(min(max_cap, equity * scale_up_pct), 2)


def compute_v540_ticket_size(equity: float, max_cap: float = 200.0) -> float:
    """Exact v5.4.1 blended directional ticket size (BTC 1.0x + ETH 0.85x + SOL 0.85x = 0.90x blend)."""
    if equity < 42.0:
        return 0.0
    if equity < 98.0:
        pct = 0.22
    elif equity < 253.0:
        pct = 0.26
    elif equity < 1003.0:
        pct = 0.22
    else:
        pct = 0.16
    return round(min(max_cap, max(10.0, equity * pct * 0.90)), 2)


compute_v541_ticket_size = compute_v540_ticket_size


def _depth_decay(ticket_usd: float, knee_usd: float = 65.0) -> float:
    """Smooth L2 orderbook slippage compression factor as ticket size grows above knee_usd."""
    if ticket_usd <= 20.0:
        return 1.0
    return max(0.58, 1.0 / (1.0 + 0.35 * ((ticket_usd - 20.0) / max(20.0, knee_usd))))


def _box_concurrency_mult(equity: float) -> float:
    """
    Models working-capital & velocity expansion from Seed (<=24h lockup, >=8 bps/hr, 1-2 active boxes)
    to Institutional (10 concurrent box slots, <=72h velocity), calibrated to Alpha-124 T1000 empirical
    live-book realization ($408.29 / 8.47d = $48.20/d raw -> ~$24.13/d P50 live capture after competition).
    """
    if equity < 98.0:
        return 1.00
    if equity < 253.0:
        return 1.00 + 0.32 * ((equity - 98.0) / 155.0)
    if equity < 1003.0:
        return 1.32 + 0.48 * ((equity - 253.0) / 750.0)
    return min(2.35, 1.80 + 0.55 * min(1.0, (equity - 1003.0) / 2000.0))


def _wilson_lcb_pct(wins: int, n: int, z: float = 1.2816) -> float:
    """One-sided ~90% Wilson score lower confidence bound on win rate (in percent)."""
    if n <= 0:
        return 0.0
    p = max(0.0, min(1.0, wins / float(n)))
    z2 = z * z
    denom = 1.0 + z2 / n
    center = p + z2 / (2.0 * n)
    rad = z * ((p * (1.0 - p) / n + z2 / (4.0 * n * n)) ** 0.5)
    return round(100.0 * max(0.0, (center - rad) / denom), 2)


STRICT_PURE_RISKLESS_LIVE_SLEEVES = frozenset(
    {
        "D1_SAME_ORACLE_DOMINANCE_BOX",
        "D1_4H_DOMINANCE_BOX",
        "D1_QUIET_BOOK_BOX",
        "C1_BINARY_COMPLETE_SET",
        "NR2_CONVERT_NO_SUBSET_ARB",
    }
)


def _is_riskless_only_mode_configured(strategy_cfg: Optional[Dict[str, Any]] = None) -> bool:
    cfg = strategy_cfg if isinstance(strategy_cfg, dict) else _load_json(STRATEGY_RISK_CONFIG_FILE)
    dir_cfg = cfg.get("directional") if isinstance(cfg, dict) else None
    if isinstance(dir_cfg, dict) and "riskless_only_mode" in dir_cfg:
        return bool(dir_cfg.get("riskless_only_mode"))
    return False


def _is_strict_pure_riskless_configured(strategy_cfg: Optional[Dict[str, Any]] = None) -> bool:
    cfg = strategy_cfg if isinstance(strategy_cfg, dict) else _load_json(STRATEGY_RISK_CONFIG_FILE)
    rb_cfg = cfg.get("riskless_boxes") if isinstance(cfg, dict) else None
    if isinstance(rb_cfg, dict) and "strict_pure_riskless_mode" in rb_cfg:
        return bool(rb_cfg.get("strict_pure_riskless_mode")) and not bool(
            rb_cfg.get("enable_single_leg_maker_bond1", True)
        )
    return False


def simulate_single_day_net_pnl(
    day_idx: int,
    equity_start: float,
    scenario: str,
    scale_up_threshold: float = 98.0,
    shadow_by_sleeve: Optional[Dict[str, Dict[str, Any]]] = None,
    sol_shadow: Optional[Dict[str, Any]] = None,
    phase3a_shadow: Optional[Dict[str, Any]] = None,
    exp316_t1k: Optional[Dict[str, Any]] = None,
    riskless_only: Optional[bool] = None,
    strict_pure_riskless: Optional[bool] = None,
) -> Tuple[float, Dict[str, float], str]:
    """
    Computes empirically grounded single-day net profit (USD):
      - When `riskless_only=True` (default when `directional.riskless_only_mode == true` in
        `config/polymarket_strategy_and_risk.json`), models the exact `v5.7.1` Pure Riskless
        5-Engine Velocity Curve (`0` unhedged directional trades):
          1. `BOND1_and_BOND2_uma_resolution_carry`: Event-diversified highest-velocity-first `BOND1`
             Maker/Taker + `BOND2` Official-Source Pre-Proposal + `W_PRUNE1` Routine-METAR Dead-NO.
          2. `S2_rtds_twap_and_clinch_locks`: `S2` Taker + Tier-1 (`BTC`/`ETH`/`SOL`/`XRP`) `T-28s`
             `S2MKR` + `MKR_LOCK1` / `SP2` / `CL1` WebSocket Clinch Sniper.
          3. `D1_same_oracle_and_quiet_boxes`: `D1` Same-Oracle & Quiet Boxes with `<70ms` Selective
             Batch Cancel-on-Arb (`>=200 bps` full-clip sweep).
          4. `V3_zero_loss_math_and_c1_merge_boxes`: `SP1`, `TEN1`, `CAL1`, `COND1`, `NR_M1` Convert,
             and `~2.5s` instant on-chain `CTF.mergePositions` `C1` Complete Sets.
          5. `dynamic_tier_unlock_sleeves`: Auto-unlocks `MKR_REWARD_LOCKED_CARRY` at `>=$125` and
             `PreSplitOverroundGunEngine` at `>=$140`.
      - When `riskless_only=False`, preserves legacy `v5.4.1` blended directional + riskless curve.
    """
    is_pure_riskless = _is_riskless_only_mode_configured() if riskless_only is None else bool(riskless_only)
    is_strict_math_only = (
        is_pure_riskless
        and (_is_strict_pure_riskless_configured() if strict_pure_riskless is None else bool(strict_pure_riskless))
    )
    cmult = _box_concurrency_mult(equity_start)

    if is_strict_math_only:
        taker_race_mult_s = {
            "P25_CONSERVATIVE": 0.52,
            "P50_BASE_FINLAND": 1.00,
            "P75_LONDON_UPSIDE": 1.82,
        }[scenario]
        # Calibrated strictly to empirical 3W/0L live (+$12.72) + 51W/0L Alpha-124 shadow (+$256.88 / 14.45d = $17.78/d @ $1,000)
        # with 100% of free liquid cash (0% locked in BOND1/S2/carries) and 0 blocked IPC head-of-line noise.
        d1_cap_s = 60.0 if equity_start < 98.0 else (120.0 if equity_start < 253.0 else (160.0 if equity_start < 1003.0 else 220.0))
        t_d1_s = min(d1_cap_s, max(10.0, equity_start * 0.88))
        d1_fills_s = 0.92 * taker_race_mult_s * (1.0 + 0.42 * (cmult - 1.0))
        cap_d1_s = {"P25_CONSERVATIVE": 10.5, "P50_BASE_FINLAND": 19.5, "P75_LONDON_UPSIDE": 36.0}[scenario]
        pnl_d1_s = min(cap_d1_s, t_d1_s * d1_fills_s * (0.0245 * _depth_decay(t_d1_s, knee_usd=85.0)))

        # Opportunistic 2-leg C1 Complete-Set Gasless Merge + m=2 NegRisk NO-Subset Convert ONLY (all single-leg & cross-question corridors = $0)
        zf_cap_s = 55.0 if equity_start < 98.0 else (105.0 if equity_start < 253.0 else 155.0)
        t_zf_s = min(zf_cap_s, max(10.0, equity_start * 0.65))
        zf_fills_s = 0.16 * taker_race_mult_s * cmult
        cap_zf_s = {"P25_CONSERVATIVE": 2.5, "P50_BASE_FINLAND": 4.5, "P75_LONDON_UPSIDE": 8.5}[scenario]
        pnl_zf_s = min(cap_zf_s, t_zf_s * zf_fills_s * (0.0145 * _depth_decay(t_zf_s, knee_usd=80.0)))

        breakdown_s: Dict[str, float] = {
            "BOND1_and_BOND2_uma_resolution_carry": 0.0,
            "S2_rtds_twap_and_clinch_locks": 0.0,
            "D1_same_oracle_and_quiet_boxes": round(pnl_d1_s, 2),
            "V3_zero_loss_math_and_c1_merge_boxes": round(pnl_zf_s, 2),
            "dynamic_tier_unlock_sleeves": 0.0,
        }
        if equity_start >= 1003.0:
            ms_s = "INSTITUTIONAL_MATH_RISKLESS (>=$1,003): Depth-Capped D1 Same-Oracle + C1 Merge + m=2 NR2 Convert ($220 Box Cap)"
        elif equity_start >= 253.0:
            ms_s = "SCALE_MATH_RISKLESS ($253-$1,003): $120-$160 D1/C1/NR2(m=2) Payoff-Dominance Only (0 Single-Leg Carries)"
        elif equity_start >= 98.0:
            ms_s = "GROWTH_MATH_RISKLESS ($98-$253): $120 D1 Cap + C1 Instant Merge + m=2 NR2 Convert (100% Unencumbered Cash)"
        else:
            ms_s = "SEED_MATH_RISKLESS (<$98): Pure Payoff-Dominance D1 + C1 Merge + m=2 NR2 (0 UMA/Single-Leg Dispute Exposure)"
        return round(sum(breakdown_s.values()), 2), breakdown_s, ms_s

    if is_pure_riskless:
        taker_race_mult = {
            "P25_CONSERVATIVE": 0.52,
            "P50_BASE_FINLAND": 1.00,
            "P75_LONDON_UPSIDE": 1.82,
        }[scenario]
        maker_vel_mult = {
            "P25_CONSERVATIVE": 0.58,
            "P50_BASE_FINLAND": 1.00,
            "P75_LONDON_UPSIDE": 1.48,
        }[scenario]

        # Working-capital-conserving allocation (concurrent resting + split capital <= 92% of equity;
        # instant Cancel-on-Arb D1/S2/C1 sweeps preempt BOND1 makers briefly and deduct preemption time).
        active_wc_pool = max(10.0, equity_start * 0.92)
        rw_notional = min(85.0, max(21.0, equity_start * 0.175)) if equity_start >= 125.0 else 0.0
        ps_lot = min(60.0, max(15.0, equity_start * 0.12)) if equity_start >= 140.0 else 0.0

        # 1. Event-Diversified BOND1 / BOND2 / UMA_READY1 / W_PRUNE1 Carry (<=92% pool net of Tier-1/2 unlocks)
        carry_pool = min(220.0, max(10.0, active_wc_pool - rw_notional - ps_lot))
        carry_time_share = 0.88  # 12% intraday duty-cycle deducted when Cancel-on-Arb preempts makers
        carry_turns = 2.40 * carry_time_share * maker_vel_mult * (1.0 + 0.35 * (cmult - 1.0))
        cap_carry_r = {"P25_CONSERVATIVE": 8.0, "P50_BASE_FINLAND": 14.5, "P75_LONDON_UPSIDE": 23.5}[scenario]
        pnl_carry_r = min(cap_carry_r, carry_pool * carry_turns * (0.0045 * _depth_decay(carry_pool * 0.25, knee_usd=85.0)))

        # 2. S2 RTDS Exact TWAP (Tier-1 BTC/ETH/SOL/XRP T-28s S2MKR + Taker) + WS Clinch Sniper
        t_s2 = min(95.0, max(9.0, equity_start * 0.36))
        s2_fills = 2.55 * (0.45 * maker_vel_mult + 0.55 * taker_race_mult) * (1.0 + 0.30 * (cmult - 1.0))
        cap_s2 = {"P25_CONSERVATIVE": 11.5, "P50_BASE_FINLAND": 21.0, "P75_LONDON_UPSIDE": 36.5}[scenario]
        pnl_s2 = min(cap_s2, t_s2 * s2_fills * (0.0096 * _depth_decay(t_s2, knee_usd=70.0)))

        # 3. D1 Same-Oracle & Quiet Boxes (with <70ms Batch Cancel-on-Arb freeing up to $45+ clip on >=200 bps arbs)
        d1_cap_r = 60.0 if equity_start < 98.0 else (120.0 if equity_start < 253.0 else (160.0 if equity_start < 1003.0 else 220.0))
        t_d1_r = min(d1_cap_r, max(14.0, equity_start * 0.58))
        d1_fills_r = 0.82 * taker_race_mult * (1.0 + 0.42 * (cmult - 1.0))
        cap_d1_r = {"P25_CONSERVATIVE": 17.0, "P50_BASE_FINLAND": 32.0, "P75_LONDON_UPSIDE": 59.0}[scenario]
        pnl_d1_r = min(cap_d1_r, t_d1_r * d1_fills_r * (0.0255 * _depth_decay(t_d1_r, knee_usd=75.0)))

        # 4. V3 0-Loss Math Corridors (SP1, TEN1, CAL1, COND1), NR_M1 Convert & ~2.5s Instant C1 Complete-Set Merge
        zf_cap_r = 55.0 if equity_start < 98.0 else (105.0 if equity_start < 253.0 else 155.0)
        t_zf_r = min(zf_cap_r, max(12.0, equity_start * 0.40))
        zf_fills_r = 0.78 * taker_race_mult * cmult
        cap_zf_r = {"P25_CONSERVATIVE": 11.5, "P50_BASE_FINLAND": 21.0, "P75_LONDON_UPSIDE": 36.5}[scenario]
        pnl_zf_r = min(cap_zf_r, t_zf_r * zf_fills_r * (0.0205 * _depth_decay(t_zf_r, knee_usd=80.0)))

        # 5. Dynamic Equity-Gated Riskless Unlocks ($125 MKR_REWARD 17.5%/$21 + $140 BTC Pre-Split 12%/$15-$60)
        pnl_unlock = 0.0
        if rw_notional > 0.0:
            pnl_unlock += rw_notional * 0.0145 * maker_vel_mult
        if ps_lot > 0.0:
            ps_cycles = 2.20 * (0.40 * maker_vel_mult + 0.60 * taker_race_mult)
            cap_ps = {"P25_CONSERVATIVE": 8.5, "P50_BASE_FINLAND": 15.5, "P75_LONDON_UPSIDE": 26.5}[scenario]
            pnl_unlock += min(cap_ps, ps_lot * ps_cycles * (0.0115 * _depth_decay(ps_lot, knee_usd=75.0)))

        breakdown_r: Dict[str, float] = {
            "BOND1_and_BOND2_uma_resolution_carry": round(pnl_carry_r, 2),
            "S2_rtds_twap_and_clinch_locks": round(pnl_s2, 2),
            "D1_same_oracle_and_quiet_boxes": round(pnl_d1_r, 2),
            "V3_zero_loss_math_and_c1_merge_boxes": round(pnl_zf_r, 2),
            "dynamic_tier_unlock_sleeves": round(pnl_unlock, 2),
        }
        if equity_start >= 1003.0:
            milestone_r = "INSTITUTIONAL_RISKLESS (>=$1,003): Full 5-Engine Zero-Loss Stack ($160-$220 Box Caps + Pre-Split Gun)"
        elif equity_start >= 253.0:
            milestone_r = "SCALE_RISKLESS ($253-$1,003): $120-$160 D1/C1 Caps + Multi-Asset Pre-Split Overround Gun + 88% BOND1"
        elif equity_start >= 140.0:
            milestone_r = "TIER_2_UNLOCKED (>=$140): Pre-Split Atomic Overround Gun + MKR_REWARD Carry + Full Riskless Stack"
        elif equity_start >= 125.0:
            milestone_r = "TIER_1_UNLOCKED ($125-$140): MKR_REWARD_LOCKED_CARRY Live + Cancel-on-Arb D1/S2 ($140 Pre-Split Next)"
        else:
            milestone_r = "SEED_PURE_RISKLESS (<$125): 0-Loss 5-Engine Velocity (Tier-1 S2MKR T-28s + <70ms Cancel-on-Arb + BOND1)"
        return round(sum(breakdown_r.values()), 2), breakdown_r, milestone_r

    fills_dir_base = {
        "P25_CONSERVATIVE": 0.85,
        "P50_BASE_FINLAND": 1.35,
        "P75_LONDON_UPSIDE": 1.95,
    }[scenario]
    ev_per_ticket_base = {
        "P25_CONSERVATIVE": 0.145,
        "P50_BASE_FINLAND": 0.182,
        "P75_LONDON_UPSIDE": 0.210,
    }[scenario]
    kelly_geom_drag = {
        "P25_CONSERVATIVE": 0.91,
        "P50_BASE_FINLAND": 0.95,
        "P75_LONDON_UPSIDE": 0.97,
    }[scenario]
    box_mult = {
        "P25_CONSERVATIVE": 0.62,
        "P50_BASE_FINLAND": 1.00,
        "P75_LONDON_UPSIDE": 1.42,
    }[scenario]

    t_v541 = compute_v541_ticket_size(equity_start)
    slot_mult = 1.28 if equity_start >= 253.0 else (1.15 if equity_start >= 150.0 else 1.00)
    eff_dir_fills = fills_dir_base * slot_mult
    ev_dir = ev_per_ticket_base * kelly_geom_drag * _depth_decay(t_v541, knee_usd=65.0)
    cap_dir = {"P25_CONSERVATIVE": 55.0, "P50_BASE_FINLAND": 95.0, "P75_LONDON_UPSIDE": 145.0}[scenario]
    pnl_dir = min(cap_dir, t_v541 * eff_dir_fills * ev_dir)

    # 2. D1 Same-Oracle & Quiet-Book Boxes (62W/0L combined, ~5 min hold, 90% cash allowance, 2-dec FOK quantizer)
    d1_cap = 60.0 if equity_start < 98.0 else (120.0 if equity_start < 253.0 else (150.0 if equity_start < 1003.0 else 220.0))
    t_d1 = min(d1_cap, max(14.0, equity_start * 0.48))
    d1_fills = 1.95 * box_mult * (1.0 + 0.45 * (cmult - 1.0))
    cap_d1 = {"P25_CONSERVATIVE": 24.0, "P50_BASE_FINLAND": 38.0, "P75_LONDON_UPSIDE": 58.0}[scenario]
    pnl_d1 = min(cap_d1, t_d1 * d1_fills * (0.031 * _depth_decay(t_d1, knee_usd=75.0)))

    # 3. Unleashed 0-Loss Mathematical Partition & Sports Boxes (live from Day 1 via _can_emit_zero_loss_math_live)
    zf_cap = (
        60.0
        if equity_start < 98.0
        else (max(60.0, equity_start * 0.40) if equity_start < 253.0 else (120.0 if equity_start < 1003.0 else 150.0))
    )
    t_zf = min(zf_cap, max(14.0, equity_start * 0.36))
    zf_fills = 1.20 * box_mult * cmult
    cap_zf = {"P25_CONSERVATIVE": 16.0, "P50_BASE_FINLAND": 26.0, "P75_LONDON_UPSIDE": 40.0}[scenario]
    pnl_zf = min(cap_zf, t_zf * zf_fills * (0.0235 * _depth_decay(t_zf, knee_usd=80.0)))

    # 4. Dual-Queue BOND1 UMA Carry (23W/0L shadow, 4W/0L live) + Liquid-Guarded MKR_LOCK1 (<=1 slot, <=90s)
    carry_cap = 45.25 if equity_start < 98.0 else (85.0 if equity_start < 253.0 else (130.0 if equity_start < 1003.0 else 180.0))
    t_carry = min(carry_cap, equity_start * 0.42)
    carry_fills = 2.10 * box_mult * (1.0 + 0.55 * (cmult - 1.0))
    cap_carry = {"P25_CONSERVATIVE": 6.5, "P50_BASE_FINLAND": 11.0, "P75_LONDON_UPSIDE": 17.0}[scenario]
    pnl_carry = min(cap_carry, t_carry * carry_fills * 0.0082)

    breakdown: Dict[str, float] = {
        "v541_high_z_directional_sniper": round(pnl_dir, 2),
        "D1_same_oracle_and_quiet_boxes": round(pnl_d1, 2),
        "V3_zero_loss_math_partition_boxes": round(pnl_zf, 2),
        "BOND1_and_liquid_MKR_LOCK1_carry": round(pnl_carry, 2),
    }

    if equity_start >= 1003.0:
        milestone = "INSTITUTIONAL (>=$1,003): 4 Dir Slots ($160-$200 Cap) + 10 Box Slots ($150-$220 L1 Depth Cap)"
    elif equity_start >= 253.0:
        milestone = "SCALE ($253-$1,003): 4 Dir Slots (22% Ticket) + $120-$150 Box Cap + 88% BOND1"
    elif equity_start >= 150.0:
        milestone = "HYPER_GROWTH 3-Slot (>=$150): 3 Crypto Dir Slots (26% Ticket) + $120 D1 Cap + 48h Velocity"
    elif equity_start >= 98.0:
        milestone = "HYPER_GROWTH ($98-$150): 26% Dir Ticket + $120 D1 / 40% ZF Box Cap + 48h Velocity"
    else:
        milestone = "UNLEASHED_LAUNCH (<$98): v5.4.1 High-Z Sniper + 90% D1 ($60) + 0-Loss Math Boxes + 78% BOND1"

    total_day_pnl = round(sum(breakdown.values()), 2)
    return total_day_pnl, breakdown, milestone


def compute_live_equity_and_rates(
    live_st: Dict[str, Any],
    fallback_equity: float = 75.84,
) -> Dict[str, Any]:
    """
    Computes true cash-conserving portfolio equity, locked riskless box floor equity,
    and box-grouped economic trade win rates from `live_harvester_state.json`.
    """
    raw_total_eq = float(live_st.get("total_account_equity") or 0.0)
    raw_bankroll = float(live_st.get("live_bankroll") or 0.0)
    has_live_balance = (
        ("total_account_equity" in live_st and live_st.get("total_account_equity") is not None)
        or ("live_bankroll" in live_st and live_st.get("live_bankroll") is not None)
    )

    active_pos = live_st.get("active_positions")
    active_legs = list(active_pos.values()) if isinstance(active_pos, dict) else []
    open_cost_val = 0.0
    box_legs_by_id: Dict[str, List[Dict[str, Any]]] = {}
    non_box_val = 0.0

    for leg in active_legs:
        if not isinstance(leg, dict):
            continue
        notional = float(leg.get("remaining_cost_basis", leg.get("notional_usd", 0.0)) or 0.0)
        partner_closed = leg.get("_closed_partner_leg")
        if (
            leg.get("is_dominance_box")
            and isinstance(partner_closed, dict)
            and float(partner_closed.get("payout_usd", 0.0) or 0.0) <= 0.01
        ):
            leg_val = max(
                float(leg.get("expected_terminal_payout_usd") or leg.get("entry_shares") or 0.0),
                notional + float(partner_closed.get("notional_usd", 0.0) or 0.0),
            )
            open_cost_val += leg_val
            non_box_val += leg_val
            continue

        cash_fee = 0.0
        if leg.get("is_dominance_box") or leg.get("is_single_leg_lock"):
            fee_asset = str(leg.get("entry_fee_asset") or "").upper()
            if fee_asset != "SHARES":
                cash_fee = float(leg.get("entry_fee_cash_usd") or leg.get("fee_usd") or 0.0)
            elif (
                leg.get("inventory_reconciled")
                and float(leg.get("fee_usd", 0.0) or 0.0) == 0.0
                and float(leg.get("fee_rate_applied", 0.0) or 0.0) > 0.0
                and float(leg.get("entry_shares", 0.0) or 0.0) > 0.0
                and float(leg.get("entry_shares", 0.0) or 0.0)
                >= float(leg.get("gross_entry_shares") or leg.get("entry_shares") or 0.0) - 0.02
            ):
                sh_l = float(leg["entry_shares"])
                rpx = notional / sh_l
                if 0.0 < rpx < 1.0:
                    fr_l = float(leg.get("fee_rate_applied") or 0.0)
                    fe_l = float(leg.get("fee_exponent_applied") or 1.0)
                    cash_fee = round(sh_l * fr_l * ((rpx * (1.0 - rpx)) ** fe_l), 4)

        leg_cost = notional + cash_fee
        open_cost_val += leg_cost
        bid_k = str(leg.get("box_id") or "").strip()
        if leg.get("is_dominance_box") and bid_k:
            box_legs_by_id.setdefault(bid_k, []).append(leg)
        else:
            non_box_val += leg_cost

    locked_maker_usd = 0.0
    stale_unverified_collat_drop_usd = 0.0
    collat_excludes_maker = (
        live_st.get("collateral_includes_resting_maker") is False
        or str(live_st.get("collateral_source") or "").upper() == "CLOB_BALANCE_API"
    )
    if isinstance(live_st.get("pending_entry_intents"), dict):
        for intent in live_st["pending_entry_intents"].values():
            if not isinstance(intent, dict):
                continue
            if collat_excludes_maker and (
                intent.get("live_maker_anchor_inflight")
                or intent.get("maker_wire_inflight")
                or intent.get("entry_order_id")
            ):
                locked_maker_usd += max(0.0, float(intent.get("notional_usd") or 0.0))
            if intent.get("live_maker_anchor_inflight"):
                matched_u = max(0.0, float(intent.get("matched_notional_usd") or 0.0))
                drop_u = max(0.0, float(intent.get("collat_drop_usd") or 0.0))
                hb_ts = float(intent.get("heartbeat_ts") or 0.0)
                surp_ts = float(intent.get("_collat_surplus_ts") or intent.get("ts") or 0.0)
                if drop_u > matched_u + 1e-6 and surp_ts > 0.0 and (hb_ts - surp_ts) >= 25.0:
                    stale_unverified_collat_drop_usd += drop_u - matched_u

    if has_live_balance:
        reconstructed_eq = raw_bankroll + open_cost_val + locked_maker_usd
        adj_raw_total_eq = max(0.0, raw_total_eq - stale_unverified_collat_drop_usd)
        live_equity = max(adj_raw_total_eq, reconstructed_eq)
    else:
        live_equity = float(fallback_equity)

    box_floor_val = 0.0
    for b_legs in box_legs_by_id.values():
        if len(b_legs) >= 2:
            paired_sh = min(float(x.get("remaining_shares", x.get("entry_shares", 0.0)) or 0.0) for x in b_legs)
            box_floor_val += max(paired_sh, sum(float(x.get("remaining_cost_basis", x.get("notional_usd", 0.0)) or 0.0) for x in b_legs))
        else:
            box_floor_val += sum(float(x.get("remaining_cost_basis", x.get("notional_usd", 0.0)) or 0.0) for x in b_legs)

    non_box_floor_val = 0.0
    for leg in active_legs:
        if not isinstance(leg, dict):
            continue
        bid_k = str(leg.get("box_id") or "").strip()
        if leg.get("is_dominance_box") and bid_k:
            continue
        notional = float(leg.get("remaining_cost_basis", leg.get("notional_usd", 0.0)) or 0.0)
        if leg.get("is_single_leg_lock") or str(leg.get("box_type") or "").upper() == "SINGLE_LEG_LOCK" or str(leg.get("trade_id") or "").startswith(("WS_SNIPE_", "LOCK1_", "MKR_LOCK1_")):
            rem_sh = float(leg.get("remaining_shares", leg.get("entry_shares", 0.0)) or 0.0)
            non_box_floor_val += max(notional, rem_sh)
        else:
            non_box_floor_val += notional

    locked_floor_equity = (
        max(live_equity, raw_bankroll + non_box_floor_val + box_floor_val + locked_maker_usd)
        if has_live_balance
        else live_equity
    )
    hwm_equity = max(float(live_st.get("high_water_mark_equity") or 0.0), live_equity)

    closed_live = [t for t in (live_st.get("closed_positions") or []) if isinstance(t, dict)]
    box_counts: Dict[str, int] = {}
    for t in closed_live:
        bk = str(t.get("box_id") or "").strip()
        if bk:
            box_counts[bk] = box_counts.get(bk, 0) + 1

    econ_groups: Dict[str, Dict[str, Any]] = {}
    for idx, t in enumerate(closed_live):
        raw_p = t.get("realized_pnl_usd")
        if raw_p is None:
            raw_p = t.get("net_pnl_usd")
        if raw_p is not None:
            leg_pnl = float(raw_p)
        else:
            leg_pnl = (
                float(t.get("realized_exit_cash", 0.0) or 0.0)
                - float(t.get("notional_usd", 0.0) or 0.0)
                - float(t.get("fee_usd", 0.0) or 0.0)
            )
        bk = str(t.get("box_id") or "").strip()
        is_grouped_box = bool(bk) and (bool(t.get("is_dominance_box")) or box_counts.get(bk, 0) > 1)
        g_key = f"BOX::{bk}" if is_grouped_box else f"TRD::{idx}::{t.get('trade_id') or idx}"
        grp = econ_groups.setdefault(g_key, {"pnl": 0.0, "any_won_flag": False, "legs": 0})
        grp["pnl"] += leg_pnl
        grp["legs"] += 1
        if t.get("won") is True:
            grp["any_won_flag"] = True

    econ_total = len(econ_groups)
    econ_wins = sum(
        1
        for g in econ_groups.values()
        if g["pnl"] > 0.0 or (abs(g["pnl"]) <= 1e-9 and g["any_won_flag"])
    )
    econ_wr_pct = round(100.0 * econ_wins / econ_total, 2) if econ_total > 0 else 0.0

    return {
        "live_equity": live_equity,
        "locked_floor_equity": locked_floor_equity,
        "liquid_working_cash_usd": round(raw_bankroll + box_floor_val, 4) if has_live_balance else round(live_equity, 4),
        "frozen_single_leg_cost_usd": round(non_box_val, 4) if has_live_balance else 0.0,
        "hwm_equity": hwm_equity,
        "closed_legs_count": len(closed_live),
        "economic_trades_count": econ_total,
        "economic_wins": econ_wins,
        "economic_win_rate_pct": econ_wr_pct,
    }


def _simulate_cash_horizon(
    start_cash: float,
    days_n: int,
    scale_up_thr: float,
    *,
    strict_pure_riskless: bool = False,
) -> Dict[str, Dict[str, float]]:
    scenarios = ("P25_CONSERVATIVE", "P50_BASE_FINLAND", "P75_LONDON_UPSIDE")
    eq_map = {sc: float(start_cash) for sc in scenarios}
    out: Dict[str, Dict[str, float]] = {}
    for d in range(1, max(days_n, 365) + 1):
        p50_day = 0.0
        for sc in scenarios:
            pnl_d, _, _ = simulate_single_day_net_pnl(
                d,
                max(10.0, eq_map[sc]),
                sc,
                scale_up_threshold=scale_up_thr,
                riskless_only=True,
                strict_pure_riskless=strict_pure_riskless,
            )
            eq_map[sc] = round(eq_map[sc] + pnl_d, 2)
            if sc == "P50_BASE_FINLAND":
                p50_day = pnl_d
        if d in (1, 7, 14, 30, 60, 90, 180, 365):
            out[f"day_{d}"] = {
                "p25_equity": eq_map["P25_CONSERVATIVE"],
                "p50_equity": eq_map["P50_BASE_FINLAND"],
                "p75_equity": eq_map["P75_LONDON_UPSIDE"],
                "p50_daily_pnl": p50_day,
                "p50_net_profit": round(eq_map["P50_BASE_FINLAND"] - float(start_cash), 2),
            }
    return out


def build_live_projections(
    days: int = 30,
    fallback_equity: float = 75.84,
    riskless_only: Optional[bool] = None,
    strict_pure_riskless: Optional[bool] = None,
) -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    live_st = _load_json(LIVE_STATE_FILE)
    a124_st = _load_json(ALPHA124_STATE_FILE)
    exp316_st = _load_json(EXP316_STATE_FILE)
    sol_st = _load_json(SOL_SHADOW_FILE)
    xrp_st = _load_json(XRP_SHADOW_FILE)
    p3a_st = _load_phase3a_summary(PHASE34_TRACKER_FILE)
    risk_cfg = _load_json(RISK_CONFIG_FILE)
    strat_cfg = _load_json(STRATEGY_RISK_CONFIG_FILE)
    is_pure_riskless = _is_riskless_only_mode_configured(strat_cfg) if riskless_only is None else bool(riskless_only)
    is_strict_math_only = (
        is_pure_riskless
        and (_is_strict_pure_riskless_configured(strat_cfg) if strict_pure_riskless is None else bool(strict_pure_riskless))
    )

    eq_stats = compute_live_equity_and_rates(live_st, fallback_equity=fallback_equity)
    live_equity = eq_stats["live_equity"]
    locked_floor_equity = eq_stats["locked_floor_equity"]
    liquid_working_cash = eq_stats["liquid_working_cash_usd"]
    frozen_single_leg_cost = eq_stats["frozen_single_leg_cost_usd"]
    hwm_equity = eq_stats["hwm_equity"]
    scale_up_thr = float(risk_cfg.get("scale_up_equity_threshold") or 110.0)

    closed_econ_n = eq_stats["economic_trades_count"]
    live_wins = eq_stats["economic_wins"]
    live_wr_pct = eq_stats["economic_win_rate_pct"]

    a124_started = _parse_iso(a124_st.get("started_at"))
    shadow_days_elapsed = (
        round(max(0.0, (now_utc - a124_started).total_seconds() / 86400.0), 2)
        if a124_started
        else 1.0
    )

    by_sleeve = a124_st.get("by_sleeve") or {}
    exp316_t1k = (exp316_st.get("tiers") or {}).get("T1000") or {}

    paused_riskless_set = {
        str(x).upper()
        for x in ((strat_cfg.get("riskless_boxes") or {}).get("paused_riskless_sleeves") or [])
        if x
    }
    grad_tracker: List[Dict[str, Any]] = []
    for sp in GRADUATION_SPECS:
        sl = sp["sleeve"]
        if is_strict_math_only and sl not in STRICT_PURE_RISKLESS_LIVE_SLEEVES:
            continue
        if sl in QUARANTINED_SLEEVES or sl.upper() in paused_riskless_set:
            continue
        if is_pure_riskless and sl in DIRECTIONAL_ONLY_SLEEVES:
            continue
        src = sp["source"]
        if src == "sol_shadow":
            closed_n = int(sol_st.get("total_trades_settled") or 0)
            wins_n = int(sol_st.get("winning_trades") or 0)
            open_n = int(sol_st.get("active_open_positions_count") or 0)
            pnl_ref = float(sol_st.get("realized_pnl") or 0.0)
        elif src == "phase3a_shadow":
            closed_n = int(p3a_st.get("closed") or 0)
            wins_n = int(p3a_st.get("wins") or 0)
            open_n = 0
            pnl_ref = float(p3a_st.get("pnl_usd") or 0.0)
        elif src == "exp316":
            closed_n = int(exp316_t1k.get("trades") or 0)
            wins_n = int(exp316_t1k.get("wins") or 0)
            open_n = int(exp316_st.get("active_positions") or 0)
            pnl_ref = float(exp316_t1k.get("net_pnl_usd") or 0.0)
        else:
            sl_data = by_sleeve.get(sl) or {}
            closed_n = int(sl_data.get("closed") or 0)
            wins_n = int(sl_data.get("wins") or 0)
            open_n = int(sl_data.get("open") or 0)
            pnl_ref = float(sl_data.get("realized_pnl_t1000_usd") or 0.0)

        wr_pct = round(100.0 * wins_n / closed_n, 2) if closed_n > 0 else 0.0
        wr_lcb90_pct = _wilson_lcb_pct(wins_n, closed_n)
        sample_pct = round(min(100.0, 100.0 * closed_n / sp["min_settled"]), 1)
        time_pct = round(min(100.0, 100.0 * shadow_days_elapsed / sp["min_days"]), 1)
        ready = (
            closed_n >= sp["min_settled"]
            and shadow_days_elapsed >= sp["min_days"]
            and wr_pct >= sp["min_wr_pct"]
            and wr_lcb90_pct >= max(0.0, sp["min_wr_pct"] - 20.0)
            and pnl_ref > 0.0
        )
        grad_tracker.append(
            {
                "sleeve": sl,
                "wave": sp["wave"],
                "source": src,
                "open_now": open_n,
                "settled_now": closed_n,
                "target_settled": sp["min_settled"],
                "sample_progress_pct": sample_pct,
                "days_elapsed": shadow_days_elapsed,
                "min_days": sp["min_days"],
                "time_progress_pct": time_pct,
                "win_rate_pct": wr_pct,
                "wilson_lcb90_wr_pct": wr_lcb90_pct,
                "target_wr_pct": sp["min_wr_pct"],
                "realized_pnl_t1000_usd": round(pnl_ref, 2),
                "ready_for_stage1_micro_live": ready,
            }
        )

    scenarios = ["P25_CONSERVATIVE", "P50_BASE_FINLAND", "P75_LONDON_UPSIDE"]
    eq_track = {sc: live_equity for sc in scenarios}
    start_date = now_utc.date()

    sim_horizon = max(days, 365)
    milestone_targets = (100, 250, 500, 1000, 2500, 5000, 10000)
    milestone_eta: Dict[str, Dict[str, Any]] = {f"usd_{m}": {} for m in milestone_targets}
    all_rows: List[Dict[str, Any]] = []
    for d in range(1, sim_horizon + 1):
        dt_str = (start_date + timedelta(days=d - 1)).isoformat()
        row: Dict[str, Any] = {"day": d, "date_utc": dt_str}
        milestone_lbl = ""
        base_breakdown: Dict[str, float] = {}
        for sc in scenarios:
            eq_prev = eq_track[sc]
            deployable_eq_prev = (
                max(10.0, eq_prev - frozen_single_leg_cost)
                if (is_pure_riskless and frozen_single_leg_cost > 0.0)
                else eq_prev
            )
            pnl_d, bdown, m_lbl = simulate_single_day_net_pnl(
                d,
                deployable_eq_prev,
                sc,
                scale_up_threshold=scale_up_thr,
                shadow_by_sleeve=by_sleeve,
                sol_shadow=sol_st,
                phase3a_shadow=p3a_st,
                exp316_t1k=exp316_t1k,
                riskless_only=is_pure_riskless,
                strict_pure_riskless=is_strict_math_only,
            )
            eq_end = round(eq_prev + pnl_d, 2)
            eq_track[sc] = eq_end
            short_k = sc.split("_")[0].lower()  # p25 / p50 / p75
            row[f"{short_k}_daily_pnl_usd"] = pnl_d
            row[f"{short_k}_end_equity_usd"] = eq_end
            for m in milestone_targets:
                mk = f"usd_{m}"
                if f"{short_k}_day" not in milestone_eta[mk] and eq_end >= float(m):
                    milestone_eta[mk][f"{short_k}_day"] = d
                    milestone_eta[mk][f"{short_k}_date_utc"] = dt_str
            if sc == "P50_BASE_FINLAND":
                milestone_lbl = m_lbl
                base_breakdown = bdown
                row["p50_v393_ticket_usd"] = 0.0 if is_pure_riskless else compute_v541_ticket_size(eq_prev)
        row["active_regime_and_milestone"] = milestone_lbl
        row["p50_sleeve_pnl_breakdown_usd"] = base_breakdown
        all_rows.append(row)

    daily_rows = all_rows[:days]

    payload = {
        "generated_at_utc": now_utc.isoformat(),
        "model_version": (
            "v6.2.0_strict_pure_riskless_math_dominance_only"
            if is_strict_math_only
            else (
                "v5.7.1_pure_riskless_5_engine_velocity"
                if is_pure_riskless
                else "v5.4.1_high_z_sniper_plus_unleashed_zero_loss_boxes"
            )
        ),
        "riskless_only_mode": is_pure_riskless,
        "strict_pure_riskless_mode": is_strict_math_only,
        "strict_pure_riskless_firewall_enabled": bool(
            ((_load_json(STRATEGY_RISK_CONFIG_FILE).get("riskless_boxes")) or {}).get("strict_pure_riskless_mode", False)
        ),
        "row2_post_clinch_carries_enabled": bool(
            ((_load_json(STRATEGY_RISK_CONFIG_FILE).get("riskless_boxes")) or {}).get("enable_single_leg_maker_bond1", True)
        ),
        "quarantined_sleeves_excluded": sorted(QUARANTINED_SLEEVES),
        "anchor_live_state": {
            "live_equity_usd": round(live_equity, 2),
            "liquid_working_cash_usd": round(liquid_working_cash, 2),
            "frozen_single_leg_cost_usd": round(frozen_single_leg_cost, 2),
            "locked_box_payout_floor_equity_usd": round(locked_floor_equity, 2),
            "high_water_mark_usd": round(hwm_equity, 2),
            "riskless_only_mode": is_pure_riskless,
            "strict_pure_riskless_mode": is_strict_math_only,
            "current_v393_ticket_usd": 0.0 if is_pure_riskless else compute_v541_ticket_size(live_equity),
            "current_v540_btc_ticket_usd": 0.0 if is_pure_riskless else round(min(200.0, live_equity * (0.22 if live_equity < 98.0 else 0.26)), 2),
            "current_v540_eth_sol_ticket_usd": 0.0 if is_pure_riskless else round(min(170.0, live_equity * (0.22 if live_equity < 98.0 else 0.26) * 0.85), 2),
            "current_cancel_on_arb_max_sweep_usd": round(min(45.0, max(20.0, live_equity * 0.88)), 2),
            "distance_to_125_reward_carry_unlock_usd": round(max(0.0, 125.0 - live_equity), 2),
            "distance_to_140_presplit_overround_unlock_usd": round(max(0.0, 140.0 - live_equity), 2),
            "distance_to_88_dynamic_sizing_usd": round(max(0.0, 88.0 - live_equity), 2),
            "distance_to_98_hyper_growth_usd": round(max(0.0, 98.0 - live_equity), 2),
            "distance_to_110_slot2_unlock_usd": round(max(0.0, 110.0 - live_equity), 2),
            "distance_to_150_slot3_unlock_usd": round(max(0.0, 150.0 - live_equity), 2),
            "distance_to_253_scale_tier_usd": round(max(0.0, 253.0 - live_equity), 2),
            "distance_to_1003_institutional_tier_usd": round(max(0.0, 1003.0 - live_equity), 2),
            "live_closed_trades": closed_econ_n,
            "live_closed_legs": eq_stats["closed_legs_count"],
            "live_wins": live_wins,
            "live_win_rate_pct": live_wr_pct,
            "alpha124_markets_monitored": a124_st.get("markets_monitored", {}),
            "alpha124_open_shadow_positions": a124_st.get("open_positions_count", 0),
            "alpha124_resting_maker_bids": a124_st.get("pending_maker_orders_count", 0),
            "sol_shadow_settled": sol_st.get("total_trades_settled", 0),
            "sol_shadow_win_rate_pct": sol_st.get("win_rate_pct", 0.0),
            "phase3a_maker_settled": p3a_st.get("closed", 0),
            "xrp_shadow_settled": xrp_st.get("total_trades_settled", 0),
        },
        "summary_horizons_usd": {
            f"day_{k}": {
                "date_utc": all_rows[k - 1]["date_utc"],
                "p25_equity": all_rows[k - 1]["p25_end_equity_usd"],
                "p50_equity": all_rows[k - 1]["p50_end_equity_usd"],
                "p75_equity": all_rows[k - 1]["p75_end_equity_usd"],
                "p50_daily_pnl": all_rows[k - 1]["p50_daily_pnl_usd"],
                "p50_net_profit": round(all_rows[k - 1]["p50_end_equity_usd"] - live_equity, 2),
            }
            for k in (1, 4, 7, 10, 14, 21, 30, 60, 90, 180, 365)
            if k <= len(all_rows)
        },
        "milestone_eta_days": milestone_eta,
        "post_nov14_miami_scenarios_usd": {
            "favorable_86_87f_payout_52usd": {
                "starting_liquid_cash_usd": round(liquid_working_cash + 52.00, 2) if frozen_single_leg_cost > 0.0 else round(liquid_working_cash, 2),
                "horizons": _simulate_cash_horizon(
                    liquid_working_cash + (52.00 if frozen_single_leg_cost > 0.0 else 0.0),
                    days,
                    scale_up_thr,
                    strict_pure_riskless=is_strict_math_only,
                ),
            },
            "adverse_zero_payout_0usd": {
                "starting_liquid_cash_usd": round(liquid_working_cash, 2),
                "requires_circuit_breaker_floor_ack_below_48usd": bool(liquid_working_cash < 48.0),
                "horizons": _simulate_cash_horizon(
                    liquid_working_cash,
                    days,
                    scale_up_thr,
                    strict_pure_riskless=is_strict_math_only,
                ),
            },
        },
        "p75_jurisdiction_compliance_note": (
            "P75 models lawful low-latency EU execution (~8-12ms RTT in Group-2 API-open regions such as GCP europe-west4 "
            "Netherlands or AWS eu-west-1 Dublin after verifying live POST /order via check_polymarket_region_latency.py "
            "--verify-post-only, while keeping manual Web UI access on Group-1 Finland europe-north1; or ~22-25ms RTT in "
            "Group-1 Stockholm europe-north2). Never deploy unwhitelisted live order placement to Group-3 CLOB close-only "
            "regions (UK eu-west-2, DE, FR, BE, CH, US, CA-ON)."
        ),
        "live_riskless_funnel": live_st.get("live_riskless_funnel", {}),
        "sleeve_graduation_live_tracker": grad_tracker,
        "day_by_day_schedule": daily_rows,
    }
    return payload


def write_live_projections_atomic(days: int = 30) -> Dict[str, Any]:
    payload = build_live_projections(days=days)
    OUTPUT_JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT_JSON_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, OUTPUT_JSON_FILE)
    return payload


def print_human_scorecard(payload: Dict[str, Any]) -> None:
    anc = payload["anchor_live_state"]
    print(f"=== DOMINUS POLYMARKET LIVE DAY-BY-DAY PROJECTIONS [{payload.get('model_version')}] ({payload['generated_at_utc']}) ===")
    if payload.get("riskless_only_mode"):
        print(
            f"Anchor Live Equity: ${anc['live_equity_usd']:.2f} (HWM ${anc['high_water_mark_usd']:.2f}) | "
            f"Live Epoch: {anc['live_wins']}W/{anc['live_closed_trades'] - anc['live_wins']}L ({anc['live_win_rate_pct']:.1f}% WR) | "
            f"To $125 Reward Unlock: ${anc['distance_to_125_reward_carry_unlock_usd']:.2f} | "
            f"To $140 Pre-Split Gun: ${anc['distance_to_140_presplit_overround_unlock_usd']:.2f}"
        )
    else:
        print(
            f"Anchor Live Equity: ${anc['live_equity_usd']:.2f} (HWM ${anc['high_water_mark_usd']:.2f}) | "
            f"Live Epoch: {anc['live_wins']}W/{anc['live_closed_trades'] - anc['live_wins']}L ({anc['live_win_rate_pct']:.1f}% WR) | "
            f"To $88 Dynamic: ${anc['distance_to_88_dynamic_sizing_usd']:.2f} | To $110 Slot-2: ${anc['distance_to_110_slot2_unlock_usd']:.2f}"
        )
    print("\n--- Clean Active Shadow Sleeve Graduation Readiness (Quarantined Sleeves Excluded) ---")
    for g in payload["sleeve_graduation_live_tracker"]:
        status_tag = "READY" if g["ready_for_stage1_micro_live"] else "WAIT "
        print(
            f"  [{status_tag}] {g['sleeve']:28s} | {g['wave']:22s} | Settled={g['settled_now']:2d}/{g['target_settled']:2d} "
            f"(Open={g['open_now']:2d}) | WR={g['win_rate_pct']:6.1f}% (req>={g['target_wr_pct']:5.1f}%) | "
            f"Ref PnL=${g['realized_pnl_t1000_usd']:+7.2f}"
        )
    print("\n--- 30-Day Live-Anchored Compounding Schedule (Post-Purge Clean Roster, Depth-Capped) ---")
    print("Day | Date       | P25 Eq ($) | P50 Base Eq ($) | P50 Day PnL | P75 LowLat ($) | Active Regime / Graduation Milestone")
    print("-" * 122)
    for r in payload["day_by_day_schedule"]:
        print(
            f"D{r['day']:02d} | {r['date_utc']} | ${r['p25_end_equity_usd']:9.2f} | "
            f"${r['p50_end_equity_usd']:14.2f} | ${r['p50_daily_pnl_usd']:+10.2f} | "
            f"${r['p75_end_equity_usd']:13.2f} | {r['active_regime_and_milestone']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Live Polymarket Day-by-Day Projections & Graduation Tracker")
    parser.add_argument("--days", type=int, default=30, help="Projection horizon in days")
    parser.add_argument("--json-only", action="store_true", help="Print JSON payload instead of ASCII table")
    args = parser.parse_args()
    payload = write_live_projections_atomic(days=args.days)
    if args.json_only:
        print(json.dumps(payload, indent=2))
    else:
        print_human_scorecard(payload)


if __name__ == "__main__":
    main()

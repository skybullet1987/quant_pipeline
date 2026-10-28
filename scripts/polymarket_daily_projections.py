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
    PIPELINE_ROOT / "data" / "polymarket" / "alpha124_shadow_state.json"
    if (PIPELINE_ROOT / "data" / "polymarket" / "alpha124_shadow_state.json").exists()
    else PIPELINE_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json"
)
EXP316_STATE_FILE = PIPELINE_ROOT / "data" / "exp316" / "exp316_shadow_state.json"
SOL_SHADOW_FILE = PIPELINE_ROOT / "data" / "polymarket" / "state_shadow_sol_v392.json"
XRP_SHADOW_FILE = PIPELINE_ROOT / "data" / "polymarket" / "state_shadow_xrp_v392.json"
PHASE34_TRACKER_FILE = PIPELINE_ROOT / "data" / "polymarket" / "shadow_phase3_4_tracker.jsonl"
RISK_CONFIG_FILE = PIPELINE_ROOT / "config" / "polymarket_risk_config.json"
OUTPUT_JSON_FILE = PIPELINE_ROOT / "data" / "polymarket" / "live_daily_projections.json"

QUARANTINED_SLEEVES = frozenset({
    "M4_SHOCK_STRIKE_CATCHUP",
    "W2_ENSEMBLE_VALUE",
    "W2_MAKER_OVERROUND",
    "M1_SVI_MAKER_SCALP",
    "M2_STRIKE_CONVERGENCE",
    "P1_PREOPEN_MAKER_STRADDLE",
    "B1_CONVEX_TAIL_YES",
    "SLEEVE_XRP_V392_SHADOW",
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
        "sleeve": "B4_TOUCHED_BARRIER_WICK_LOCK",
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
        "wave": "Wave 3 (Conditional)",
        "target_day": 15,
        "min_days": 10.0,
        "min_settled": 30,
        "min_wr_pct": 94.0,
        "source": "alpha124",
        "stage1_ticket_usd": 12.0,
        "l1_daily_pnl_cap_usd": 35.0,
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


def _depth_decay(ticket_usd: float, knee_usd: float = 65.0) -> float:
    """Smooth L2 orderbook slippage compression factor as ticket size grows above knee_usd."""
    if ticket_usd <= 20.0:
        return 1.0
    return max(0.58, 1.0 / (1.0 + 0.35 * ((ticket_usd - 20.0) / max(20.0, knee_usd))))


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


def simulate_single_day_net_pnl(
    day_idx: int,
    equity_start: float,
    scenario: str,
    scale_up_threshold: float = 110.0,
    shadow_by_sleeve: Optional[Dict[str, Dict[str, Any]]] = None,
    sol_shadow: Optional[Dict[str, Any]] = None,
    phase3a_shadow: Optional[Dict[str, Any]] = None,
    exp316_t1k: Optional[Dict[str, Any]] = None,
) -> Tuple[float, Dict[str, float], str]:
    """
    Computes realistic single-day net profit (USD) across ONLY clean, non-quarantined active sleeves:
      1. `< $110` single-slot directional crypto concurrency guard + `0.82` `:45-:00` fast-pool
         collision discount across `v4.1` BTC/ETH, `D1`, and `SOL`
      2. Explicit Working-Capital Partition (`fast_intraday_pool` vs `slow_24h_pool`)
         so 6h-24h Weather (`W1`) / Barrier (`B2`) / Multi-Strike (`EXP-316`) tickets NEVER
         double-count collateral used by intraday `v4.1` / `D1` / `SOL` sleeves
      3. Empirical CLOB L1/L2 orderbook depth caps (`BTC` ~$200 L1, `ETH` ~$63 L1, `SOL` ~$20 L1,
         `D1` `T5000` paired ceiling)
      4. Zero allocation (`$0.00`) to all quarantined sleeves (`W2_ENSEMBLE_VALUE`, `W2_MAKER_OVERROUND`,
         `M1_SVI_MAKER_SCALP`, `M4_SHOCK_STRIKE_CATCHUP`, `M2`, `P1_PREOPEN_MAKER_STRADDLE`, `B1`, `XRP`),
         and hard `> $0` shadow-PnL gate on high-payoff-skew `S2_EXACT_TWAP_LOCK`.
    """
    mult_map = {
        "P25_CONSERVATIVE": 0.62,
        "P50_BASE_FINLAND": 1.00,
        "P75_LONDON_UPSIDE": 1.35,
    }
    kelly_geom_drag = {
        "P25_CONSERVATIVE": 0.68,
        "P50_BASE_FINLAND": 0.80,
        "P75_LONDON_UPSIDE": 0.86,
    }[scenario]
    m = mult_map[scenario] * kelly_geom_drag
    is_low_lat = scenario == "P75_LONDON_UPSIDE"
    fast_concurrency_disc = 0.82

    # Partition total USDC.e between Fast Intraday Turnover (<15m-4h) and Slow 6h-24h Lockups
    if day_idx < 8:
        fast_pool = equity_start
        slow_pool = 0.0
    elif day_idx < 15:
        fast_pool = equity_start * 0.68
        slow_pool = equity_start * 0.32
    else:
        fast_pool = equity_start * 0.60
        slow_pool = equity_start * 0.40

    breakdown: Dict[str, float] = {}
    milestone = "Wave 1 Live: WFO v3.9.5 (BTC+ETH) + D1 (15m/5m, QuietBook 13/13 & 4h)"

    # 1. Core Live Engine: Purged-WFO v3.9.5 Sub-Hourly & 1h BTC+ETH Sniper (92.86% WR, PF=3.34 across 3,278 mkts)
    t_v39 = compute_v393_ticket_size(fast_pool if day_idx >= 8 else equity_start)
    if t_v39 == 0.0 and equity_start >= 48.0:
        t_v39 = 12.0
    has_slot2 = equity_start >= scale_up_threshold
    eff_fills_v39 = (7.2 if has_slot2 else 5.8) * (1.12 if is_low_lat else 1.0)
    ev_v39 = 0.092 * m * _depth_decay(t_v39, knee_usd=60.0)
    cap_v39 = 195.0 if is_low_lat else 145.0
    pnl_v39 = min(cap_v39, t_v39 * eff_fills_v39 * ev_v39)
    breakdown["wfo_v395_directional_live"] = round(pnl_v39, 2)

    # 2. Wave 1 (Live Now): D1 Same-Oracle Dominance Boxes (15m/5m 28/28 + QuietBook 13/13 + 4h Corridors, 38% sizing >= $95)
    d1_pct = 0.38 if equity_start >= 95.0 else 0.25
    if day_idx < 4 and not has_slot2:
        t_d1 = min(42.0, max(15.0, fast_pool * d1_pct))
        live_boxes_per_day = 2.8 * fast_concurrency_disc * (1.18 if is_low_lat else 1.0)
    elif day_idx < 8:
        t_d1 = min(65.0, max(25.0, fast_pool * min(0.32, d1_pct)))
        live_boxes_per_day = 3.2 * fast_concurrency_disc * (1.20 if is_low_lat else 1.0)
        milestone = "Wave 1 Scale-Up: 2-Slot (>=$110, 22% WFO v3.9.5) + 38% D1 Boxes"
    else:
        t_d1 = min(145.0, max(30.0, fast_pool * 0.25))
        live_boxes_per_day = 3.8 * fast_concurrency_disc * (1.22 if is_low_lat else 1.0)
    ev_d1 = 0.052 * max(0.70, min(1.12, m)) * _depth_decay(t_d1, knee_usd=65.0)
    cap_d1 = 240.0 if is_low_lat else 165.0
    pnl_d1 = min(cap_d1, t_d1 * live_boxes_per_day * ev_d1)
    breakdown["D1_dominance_boxes"] = round(pnl_d1, 2)
    if has_slot2 and day_idx < 5:
        milestone = "Wave 1 Scale-Up: 2-Slot (>=$110, 22% WFO v3.9.5) + 38% D1 Boxes"

    # 3. Wave 2A (Day 5+): Graduated SOL Sub-Hourly (capped at $22 ticket for $20 p50 L1 depth) + Phase 3A 0%-Fee Maker Fallback
    if day_idx >= 5:
        sol_pnl_ok = float((sol_shadow or {}).get("realized_pnl", 1.0) or 0.0) >= 0.0
        t_sol = min(22.0, max(12.0, fast_pool * 0.10)) if sol_pnl_ok else 0.0
        pnl_sol = min(
            28.0 if is_low_lat else 18.0,
            t_sol * (1.8 * fast_concurrency_disc) * (0.062 * m * _depth_decay(t_sol, knee_usd=20.0)),
        )
        if pnl_sol > 0.0:
            breakdown["SOL_subhourly_graduated"] = round(pnl_sol, 2)
        if day_idx < 8:
            milestone = "Wave 2A Live: +SOL Sub-Hourly ($12-$22 L1-Capped)"

    if day_idx >= 6:
        p3a_ok = float((phase3a_shadow or {}).get("pnl_usd", 1.0) or 0.0) >= 0.0
        if p3a_ok:
            t_p3a = min(30.0, max(12.0, fast_pool * 0.11))
            pnl_p3a = min(
                36.0 if is_low_lat else 24.0,
                t_p3a * 1.5 * (0.065 * max(0.65, min(1.08, m)) * _depth_decay(t_p3a, knee_usd=40.0)),
            )
            breakdown["Phase3A_maker_fallback"] = round(pnl_p3a, 2)
            if day_idx < 8:
                milestone = "Wave 2A Live: +SOL & Phase-3A 0%-Fee Maker Fallback"

    # 4. Wave 2B (Day 8+): Slow-Pool High-WR Locks — W1 80-City 0%-Fee METAR + W3 Slate Arb + B2 Barrier + EXP-316 Track A
    if day_idx >= 8:
        in_stage1_w2 = day_idx < 14
        slow_t1_budget = min(48.0, slow_pool) if in_stage1_w2 else (slow_pool * (0.72 if day_idx >= 15 else 0.95))
        milestone = (
            "Wave 2B Micro-Live: +W1 80-City METAR, B2 Barrier, EXP-316 ($15 cap)"
            if in_stage1_w2
            else "Wave 2B Stage-2 Half-Kelly (Fast/Slow Partitioned)"
        )

        avg_t_w1 = max(12.0, (slow_t1_budget * 0.58) / 2.2)
        pnl_w1 = min(
            120.0 if is_low_lat else 85.0,
            (slow_t1_budget * 0.58) * 1.25 * (0.074 * max(0.65, min(1.08, m)) * _depth_decay(avg_t_w1, 90.0)),
        )
        # B2 + EXP-316 Track A strictly capped per rung (EXP-316 T2500 proved L2 exit slippage above ~$100-$150/rung)
        exp_hc = 1.0 if float((exp316_t1k or {}).get("net_pnl_usd", 1.0) or 0.0) >= 0.0 else 0.65
        avg_t_b2 = min(90.0, max(12.0, (slow_t1_budget * 0.42) / 2.0))
        pnl_b2_exp = min(
            80.0 if is_low_lat else 55.0,
            (slow_t1_budget * 0.42) * 1.30 * (0.060 * m * _depth_decay(avg_t_b2, 70.0) * exp_hc),
        )
        breakdown["W1_W3_weather_metar_locks"] = round(pnl_w1, 2)
        breakdown["B2_EXP316_barrier_strike_locks"] = round(pnl_b2_exp, 2)

    # 5. Wave 3 (Day 15+): Clean Post-Purge Additions ONLY (U1 Daily Up/Down + S5M 5m Sniper + N1/M3/C1 Cross-Boxes)
    # Quarantined W2_ENSEMBLE_VALUE, W2_MAKER_OVERROUND, M1_SVI_MAKER_SCALP, M4_SHOCK_STRIKE_CATCHUP, P1 = $0.00!
    if day_idx >= 15:
        in_stage1_w3 = day_idx < 21
        milestone = (
            "Wave 3 Micro-Live: +U1 Daily Lock, S5M 5m Sniper & N1 NegRisk Boxes"
            if in_stage1_w3
            else "Full Clean Roster Compounding (Zero Quarantined Sleeves, Depth-Capped)"
        )
        w3_budget = min(45.0, slow_pool * 0.28) if in_stage1_w3 else (slow_pool * 0.28)
        avg_t_w3 = max(14.0, w3_budget / 2.5)
        pnl_u1_s5m_n1 = min(
            75.0 if is_low_lat else 48.0,
            w3_budget * 1.45 * (0.062 * m * _depth_decay(avg_t_w3, 65.0)),
        )
        breakdown["U1_S5M_N1_clean_wave3"] = round(pnl_u1_s5m_n1, 2)

        # Conditional S2 Exact TWAP Lock: strictly gated at $0.00 until shadow N>=10 and net PnL > $0!
        s2_stat = (shadow_by_sleeve or {}).get("S2_EXACT_TWAP_LOCK") or {}
        if int(s2_stat.get("closed") or 0) >= 10 and float(s2_stat.get("realized_pnl_t1000_usd") or 0.0) > 0.0:
            t_s2 = min(45.0, max(12.0, fast_pool * 0.12))
            pnl_s2 = min(
                45.0 if is_low_lat else 30.0,
                t_s2 * (2.4 * fast_concurrency_disc) * (0.042 * m * _depth_decay(t_s2, 45.0)),
            )
            breakdown["S2_exact_twap_lock"] = round(pnl_s2, 2)

    total_day_pnl = round(sum(breakdown.values()), 2)
    return total_day_pnl, breakdown, milestone


def build_live_projections(days: int = 30, fallback_equity: float = 85.08) -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    live_st = _load_json(LIVE_STATE_FILE)
    a124_st = _load_json(ALPHA124_STATE_FILE)
    exp316_st = _load_json(EXP316_STATE_FILE)
    sol_st = _load_json(SOL_SHADOW_FILE)
    xrp_st = _load_json(XRP_SHADOW_FILE)
    p3a_st = _load_phase3a_summary(PHASE34_TRACKER_FILE)
    risk_cfg = _load_json(RISK_CONFIG_FILE)

    live_equity = float(
        live_st.get("total_account_equity")
        or live_st.get("live_bankroll")
        or fallback_equity
    )
    hwm_equity = float(live_st.get("high_water_mark_equity") or live_equity)
    scale_up_thr = float(risk_cfg.get("scale_up_equity_threshold") or 110.0)

    closed_live = live_st.get("closed_positions") or []
    live_wins = sum(
        1
        for t in closed_live
        if float(
            t.get("realized_pnl_usd")
            or t.get("net_pnl_usd")
            or (
                float(t.get("realized_exit_cash", 0.0))
                - float(t.get("notional_usd", 0.0))
                - float(t.get("fee_usd", 0.0))
            )
        )
        > 0
    )

    a124_started = _parse_iso(a124_st.get("started_at"))
    shadow_days_elapsed = (
        round(max(0.0, (now_utc - a124_started).total_seconds() / 86400.0), 2)
        if a124_started
        else 1.0
    )

    by_sleeve = a124_st.get("by_sleeve") or {}
    exp316_t1k = (exp316_st.get("tiers") or {}).get("T1000") or {}

    grad_tracker: List[Dict[str, Any]] = []
    for sp in GRADUATION_SPECS:
        sl = sp["sleeve"]
        if sl in QUARANTINED_SLEEVES:
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

    daily_rows: List[Dict[str, Any]] = []
    for d in range(1, days + 1):
        dt_str = (start_date + timedelta(days=d - 1)).isoformat()
        row: Dict[str, Any] = {"day": d, "date_utc": dt_str}
        milestone_lbl = ""
        base_breakdown: Dict[str, float] = {}
        for sc in scenarios:
            eq_prev = eq_track[sc]
            pnl_d, bdown, m_lbl = simulate_single_day_net_pnl(
                d,
                eq_prev,
                sc,
                scale_up_threshold=scale_up_thr,
                shadow_by_sleeve=by_sleeve,
                sol_shadow=sol_st,
                phase3a_shadow=p3a_st,
                exp316_t1k=exp316_t1k,
            )
            eq_end = round(eq_prev + pnl_d, 2)
            eq_track[sc] = eq_end
            short_k = sc.split("_")[0].lower()  # p25 / p50 / p75
            row[f"{short_k}_daily_pnl_usd"] = pnl_d
            row[f"{short_k}_end_equity_usd"] = eq_end
            if sc == "P50_BASE_FINLAND":
                milestone_lbl = m_lbl
                base_breakdown = bdown
                row["p50_v393_ticket_usd"] = compute_v393_ticket_size(eq_prev)
        row["active_regime_and_milestone"] = milestone_lbl
        row["p50_sleeve_pnl_breakdown_usd"] = base_breakdown
        daily_rows.append(row)

    payload = {
        "generated_at_utc": now_utc.isoformat(),
        "model_version": "v4.2_post_purge_clean_roster",
        "quarantined_sleeves_excluded": sorted(QUARANTINED_SLEEVES),
        "anchor_live_state": {
            "live_equity_usd": round(live_equity, 2),
            "high_water_mark_usd": round(hwm_equity, 2),
            "current_v393_ticket_usd": compute_v393_ticket_size(live_equity),
            "distance_to_88_dynamic_sizing_usd": round(max(0.0, 88.0 - live_equity), 2),
            "distance_to_110_slot2_unlock_usd": round(max(0.0, scale_up_thr - live_equity), 2),
            "live_closed_trades": len(closed_live),
            "live_wins": live_wins,
            "live_win_rate_pct": round(100.0 * live_wins / len(closed_live), 2) if closed_live else 0.0,
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
                "date_utc": daily_rows[k - 1]["date_utc"],
                "p25_equity": daily_rows[k - 1]["p25_end_equity_usd"],
                "p50_equity": daily_rows[k - 1]["p50_end_equity_usd"],
                "p75_equity": daily_rows[k - 1]["p75_end_equity_usd"],
                "p50_net_profit": round(daily_rows[k - 1]["p50_end_equity_usd"] - live_equity, 2),
            }
            for k in (1, 4, 7, 10, 14, 21, 30)
            if k <= len(daily_rows)
        },
        "p75_jurisdiction_compliance_note": (
            "P75 models <15ms low-latency execution; Polymarket restricts UK (eu-west-2), FR, DE, IE, and ON — "
            "keep live execution on Finland (or another verified non-restricted EU region) unless lawful eligibility is confirmed."
        ),
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

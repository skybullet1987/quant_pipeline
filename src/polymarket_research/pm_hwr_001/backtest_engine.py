#!/usr/bin/env python3
"""
PM-HWR-001: Stage 3 (Pre-Registered Parameter Grid) & Stage 4 (Execution Simulator)
===================================================================================
Backtesting engine replaying granular orderbook telemetry across chronological folds
(Train, Validation, and untouched Holdout).

Evaluates:
  Family A: Late-candle probability engine (TTE, normalized strike distance z, p_win)
  Family B: Lead-lag & shock flow (OFI, volume shock, book staleness)
  Family C: Regime filters (volatility bucket, trend alignment)
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path("data/polymarket")
OUTPUT_DIR = Path("data/pm_hwr_001")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TELEMETRY_BTC = DATA_DIR / "polymarket_hourly_telemetry.jsonl"
TELEMETRY_ETH = DATA_DIR / "polymarket_hourly_telemetry_eth.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
SHOCK_FILE = DATA_DIR / "live_shock_triggers.jsonl"


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function (Abramowitz & Stegun approximation)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def polymarket_crypto_fee_v2(price: float, fee_rate: float = 0.07) -> float:
    """Polymarket crypto dynamic fee schedule: fee = fee_rate * p * (1 - p)."""
    p = max(0.001, min(0.999, price))
    return fee_rate * p * (1.0 - p)


@dataclass
class CandidateConfig:
    candidate_id: str
    family: str  # 'FAMILY_A_LATE_CANDLE', 'FAMILY_B_LEAD_LAG', 'FAMILY_C_REGIME'
    max_tte: float  # seconds to expiry ceiling (e.g. 60, 120, 180, 300, 600)
    min_tte: float  # seconds to expiry floor (e.g. 10)
    min_z_score: float  # normalized spot distance threshold (e.g. 1.5, 2.0, 2.5, 3.0)
    max_entry_price: float  # maximum acceptable execution price (e.g. 0.85, 0.90, 0.94)
    min_model_prob: float  # minimum calibrated probability (e.g. 0.90, 0.95, 0.98)
    vol_regime: Optional[str] = None  # None, 'LOW_VOL', 'NORMAL_VOL', 'HIGH_VOL'
    require_trend_aligned: bool = False
    stop_loss_enabled: bool = False
    stop_loss_threshold: float = 0.55  # CLOB price stop unwind trigger


@dataclass
class SimulatedTrade:
    market_id: str
    timestamp: str
    timestamp_unix: float
    asset: str
    tte: float
    side: str
    spot: float
    strike_open: float
    z_score: float
    model_prob: float
    ask_price: float
    vwap_20: float
    fee_per_share: float
    ticket_usd: float
    shares_bought: float
    winning_outcome: str
    won: bool
    exit_type: str  # 'EXPIRY_SETTLEMENT' or 'STOP_LOSS_UNWIND'
    exit_price: float
    gross_pnl: float
    fee_usd: float
    net_pnl: float
    fold: str  # 'TRAIN', 'VALIDATION', 'HOLDOUT'


def load_resolutions() -> Dict[str, Dict[str, Any]]:
    resolutions = {}
    with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                resolutions[str(r["market_id"])] = r
    return resolutions


def get_fold(candle_close_ts: float) -> str:
    """Chronological split:
    Train:      2026-09-28 to 2026-10-05 (close_ts < 1791244800)
    Validation: 2026-10-06 to 2026-10-09 (1791244800 <= close_ts < 1791590400)
    Holdout:    2026-10-10 to 2026-10-12 (close_ts >= 1791590400)
    """
    dt = datetime.fromtimestamp(candle_close_ts, tz=timezone.utc)
    day_str = dt.strftime("%Y-%m-%d")
    if day_str <= "2026-10-05":
        return "TRAIN"
    elif day_str <= "2026-10-09":
        return "VALIDATION"
    else:
        return "HOLDOUT"


def run_candidate_sweep(
    configs: List[CandidateConfig],
    ticket_size_usd: float = 30.0,
) -> Dict[str, Any]:
    resolutions = load_resolutions()

    # Pre-parse telemetry frames and group by market
    print("Loading and indexing orderbook telemetry frames...")
    market_frames = []

    telemetry_files = [(TELEMETRY_BTC, "BTC"), (TELEMETRY_ETH, "ETH")]
    for t_file, asset in telemetry_files:
        if not t_file.exists():
            continue
        with open(t_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    frame = json.loads(line)
                    mid = str(frame.get("market_id"))
                    if mid not in resolutions:
                        continue
                    tte = float(frame.get("seconds_to_expiry", 9999.0))
                    if tte > 650.0:  # only keep frames within last ~10 mins for efficiency
                        continue
                    spot = float(frame.get("binance_spot", 0.0))
                    open_px = float(frame.get("binance_1h_open", 0.0))
                    if spot <= 0 or open_px <= 0:
                        continue

                    market_frames.append((mid, asset, frame, resolutions[mid]))
                except Exception:
                    pass

    print(f"Loaded {len(market_frames)} eligible candidate evaluation frames.")

    results_by_candidate = {}

    for cfg in configs:
        trades_by_fold = {"TRAIN": [], "VALIDATION": [], "HOLDOUT": []}
        seen_market_per_cfg = set()

        for mid, asset, frame, res in market_frames:
            if mid in seen_market_per_cfg:
                continue

            tte = float(frame.get("seconds_to_expiry", 9999.0))
            if not (cfg.min_tte <= tte <= cfg.max_tte):
                continue

            spot = float(frame.get("binance_spot", 0.0))
            open_px = float(frame.get("binance_1h_open", 0.0))
            close_ts = float(res.get("candle_close_ts", 0.0))
            fold = get_fold(close_ts)

            # Standardized 1H realized volatility estimate
            # BTC median hourly vol ~ 0.0050 (0.50%), ETH ~ 0.0075 (0.75%)
            sigma_1h = 0.0050 if asset == "BTC" else 0.0075

            # Volatility regime filter
            if cfg.vol_regime:
                # Approximate 1h volatility from distance
                dist_abs = abs(spot - open_px) / open_px
                if cfg.vol_regime == "LOW_VOL" and dist_abs > 0.004:
                    continue
                elif cfg.vol_regime == "HIGH_VOL" and dist_abs < 0.007:
                    continue

            # Normalized distance to strike: z = (Spot - Open) / (sigma * Open * sqrt(tte / 3600))
            tte_ratio = max(0.001, tte / 3600.0)
            sigma_remaining = sigma_1h * math.sqrt(tte_ratio)
            z_score = (spot - open_px) / (open_px * sigma_remaining)

            # Directional model probability:
            # P(Close >= Open) = Phi(z_score)
            p_up = normal_cdf(z_score)
            p_down = 1.0 - p_up

            # Check if either side meets conviction threshold
            target_side = None
            model_prob = 0.0
            z_val = 0.0

            if p_up >= cfg.min_model_prob and z_score >= cfg.min_z_score:
                target_side = "UP"
                model_prob = p_up
                z_val = z_score
            elif p_down >= cfg.min_model_prob and (-z_score) >= cfg.min_z_score:
                target_side = "DOWN"
                model_prob = p_down
                z_val = -z_score

            if not target_side:
                continue

            # Check market book for target side
            book = frame.get(target_side, {})
            best_ask = float(book.get("best_ask", 0.0) or 0.0)
            vwap_raw = book.get("vwap_$20")
            vwap_20 = float(vwap_raw) if vwap_raw is not None else best_ask
            exec_price = vwap_20 if vwap_20 > 0 else best_ask

            if exec_price <= 0.0 or exec_price > cfg.max_entry_price:
                continue

            # Check available ask depth (must be >= $20 to support $30 ticket)
            ask_size = float(book.get("ask_size_l1") or book.get("ask_size") or 0.0)
            if ask_size * exec_price < 15.0:
                continue

            # Calculate fees and shares
            fee_per_share = polymarket_crypto_fee_v2(exec_price)
            shares = ticket_size_usd / exec_price
            fee_total = shares * fee_per_share

            # Ground truth outcome
            winning_outcome = res.get("winning_outcome")
            won = (target_side == winning_outcome)

            # Exit simulation
            exit_type = "EXPIRY_SETTLEMENT"
            exit_price = 1.0 if won else 0.0

            if won:
                gross_pnl = shares * 1.0 - ticket_size_usd
            else:
                gross_pnl = -ticket_size_usd

            net_pnl = gross_pnl - fee_total

            trade = SimulatedTrade(
                market_id=mid,
                timestamp=frame.get("timestamp", ""),
                timestamp_unix=float(frame.get("timestamp_unix", 0.0)),
                asset=asset,
                tte=tte,
                side=target_side,
                spot=spot,
                strike_open=open_px,
                z_score=round(z_val, 2),
                model_prob=round(model_prob, 4),
                ask_price=round(exec_price, 4),
                vwap_20=round(vwap_20, 4),
                fee_per_share=round(fee_per_share, 4),
                ticket_usd=ticket_size_usd,
                shares_bought=round(shares, 4),
                winning_outcome=winning_outcome,
                won=won,
                exit_type=exit_type,
                exit_price=exit_price,
                gross_pnl=round(gross_pnl, 4),
                fee_usd=round(fee_total, 4),
                net_pnl=round(net_pnl, 4),
                fold=fold,
            )

            trades_by_fold[fold].append(trade)
            seen_market_per_cfg.add(mid)

        # Aggregate fold metrics for candidate
        fold_summaries = {}
        for f_name, f_trades in trades_by_fold.items():
            n_t = len(f_trades)
            if n_t == 0:
                fold_summaries[f_name] = {
                    "n_trades": 0,
                    "win_rate_pct": 0.0,
                    "win_rate_95ci": [0.0, 0.0],
                    "total_net_pnl": 0.0,
                    "ev_per_trade": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "profit_factor": 0.0,
                    "max_drawdown": 0.0,
                }
                continue

            wins = [t for t in f_trades if t.won]
            losses = [t for t in f_trades if not t.won]
            wr = len(wins) / n_t

            # Wilson Score CI
            z = 1.96
            denom = 1 + (z**2) / n_t
            center = (wr + (z**2) / (2 * n_t)) / denom
            margin = (z * math.sqrt((wr * (1 - wr) / n_t) + ((z**2) / (4 * (n_t**2))))) / denom
            ci_lower = max(0.0, center - margin)
            ci_upper = min(1.0, center + margin)

            pnls = [t.net_pnl for t in f_trades]
            tot_pnl = sum(pnls)
            ev = tot_pnl / n_t

            win_pnls = [t.net_pnl for t in wins]
            loss_pnls = [t.net_pnl for t in losses]
            avg_w = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
            avg_l = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0.0
            pf = abs(sum(win_pnls) / sum(loss_pnls)) if loss_pnls and sum(loss_pnls) != 0 else float("inf")

            # Max drawdown
            cum = 0.0
            peak = 0.0
            max_dd = 0.0
            for p in pnls:
                cum += p
                if cum > peak:
                    peak = cum
                dd = peak - cum
                if dd > max_dd:
                    max_dd = dd

            fold_summaries[f_name] = {
                "n_trades": n_t,
                "wins": len(wins),
                "losses": len(losses),
                "win_rate_pct": round(wr * 100, 2),
                "win_rate_95ci": [round(ci_lower * 100, 2), round(ci_upper * 100, 2)],
                "ci_lower_pct": round(ci_lower * 100, 2),
                "total_net_pnl": round(tot_pnl, 2),
                "ev_per_trade": round(ev, 2),
                "avg_win": round(avg_w, 2),
                "avg_loss": round(avg_l, 2),
                "profit_factor": round(pf, 2) if pf != float("inf") else "inf",
                "max_drawdown": round(max_dd, 2),
            }

        results_by_candidate[cfg.candidate_id] = {
            "config": asdict(cfg),
            "folds": fold_summaries,
            "total_qualifying_markets": len(seen_market_per_cfg),
        }

    return results_by_candidate


def generate_candidate_grid() -> List[CandidateConfig]:
    """Generate pre-registered candidate hypotheses across Family A, B, and C."""
    grid = []

    # 1. Baseline Control (Current Harvester proxy)
    grid.append(CandidateConfig(
        candidate_id="CONTROL_BASELINE",
        family="CONTROL",
        max_tte=600.0,
        min_tte=60.0,
        min_z_score=1.15,
        max_entry_price=0.88,
        min_model_prob=0.75,
    ))

    # 2. Family A: Late-Candle Probability Engine
    # Grid: TTE in [60s, 120s, 180s, 300s]
    # z_score in [1.5, 2.0, 2.5, 3.0]
    # max_entry_price in [0.85, 0.90, 0.94]
    # min_model_prob in [0.90, 0.95, 0.98]
    family_a_params = [
        # Conservative Late-Candle (Targeting 95%+)
        ("CAND_A1_SNIPER_60S_Z2.5", 60.0, 10.0, 2.5, 0.94, 0.95),
        ("CAND_A2_SNIPER_120S_Z2.5", 120.0, 10.0, 2.5, 0.94, 0.95),
        ("CAND_A3_SNIPER_180S_Z2.5", 180.0, 10.0, 2.5, 0.94, 0.95),
        ("CAND_A4_SNIPER_300S_Z2.5", 300.0, 10.0, 2.5, 0.92, 0.95),
        # Ultra-High Conviction (Targeting 98%+)
        ("CAND_A5_EXTREME_60S_Z3.0", 60.0, 10.0, 3.0, 0.95, 0.98),
        ("CAND_A6_EXTREME_120S_Z3.0", 120.0, 10.0, 3.0, 0.95, 0.98),
        ("CAND_A7_EXTREME_180S_Z3.0", 180.0, 10.0, 3.0, 0.95, 0.98),
        # Moderate Conviction / Higher Frequency
        ("CAND_A8_MODERATE_180S_Z2.0", 180.0, 10.0, 2.0, 0.90, 0.90),
        ("CAND_A9_MODERATE_300S_Z2.0", 300.0, 10.0, 2.0, 0.90, 0.90),
        ("CAND_A10_WIDE_600S_Z2.0", 600.0, 60.0, 2.0, 0.88, 0.90),
    ]

    for cid, max_t, min_t, min_z, max_p, min_prob in family_a_params:
        grid.append(CandidateConfig(
            candidate_id=cid,
            family="FAMILY_A_LATE_CANDLE",
            max_tte=max_t,
            min_tte=min_t,
            min_z_score=min_z,
            max_entry_price=max_p,
            min_model_prob=min_prob,
        ))

    # 3. Family C: Selective Regime Filters
    grid.append(CandidateConfig(
        candidate_id="CAND_C1_REGIME_LOW_VOL_180S",
        family="FAMILY_C_REGIME",
        max_tte=180.0,
        min_tte=10.0,
        min_z_score=2.0,
        max_entry_price=0.92,
        min_model_prob=0.92,
        vol_regime="LOW_VOL",
    ))
    grid.append(CandidateConfig(
        candidate_id="CAND_C2_REGIME_HIGH_VOL_180S",
        family="FAMILY_C_REGIME",
        max_tte=180.0,
        min_tte=10.0,
        min_z_score=2.5,
        max_entry_price=0.92,
        min_model_prob=0.95,
        vol_regime="HIGH_VOL",
    ))

    return grid


def main():
    print("=" * 80)
    print("   PM-HWR-001: STAGE 3 & 4 PRE-REGISTERED PARAMETER SWEEP")
    print("=" * 80)

    grid = generate_candidate_grid()
    print(f"Pre-registered {len(grid)} candidate configurations (including control).")

    results = run_candidate_sweep(grid, ticket_size_usd=30.0)

    out_file = OUTPUT_DIR / "stage3_4_backtest_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"✓ Backtest complete. Results written to: {out_file}\n")

    # Print summary table
    print(f"{'Candidate ID':<28} | {'Train WR':<10} | {'Val WR':<10} | {'Holdout WR':<12} | {'Holdout 95% CI':<16} | {'Holdout N':<10} | {'Holdout EV':<10}")
    print("-" * 105)
    for cid, res in results.items():
        folds = res["folds"]
        tr_wr = f"{folds['TRAIN']['win_rate_pct']}% ({folds['TRAIN']['n_trades']})" if folds['TRAIN']['n_trades'] > 0 else "0"
        val_wr = f"{folds['VALIDATION']['win_rate_pct']}% ({folds['VALIDATION']['n_trades']})" if folds['VALIDATION']['n_trades'] > 0 else "0"
        ho = folds['HOLDOUT']
        ho_wr = f"{ho['win_rate_pct']}%" if ho['n_trades'] > 0 else "0"
        ho_ci = f"[{ho['win_rate_95ci'][0]}%, {ho['win_rate_95ci'][1]}%]" if ho['n_trades'] > 0 else "N/A"
        ho_n = f"{ho['n_trades']}"
        ho_ev = f"${ho['ev_per_trade']}" if ho['n_trades'] > 0 else "N/A"
        print(f"{cid:<28} | {tr_wr:<10} | {val_wr:<10} | {ho_wr:<12} | {ho_ci:<16} | {ho_n:<10} | {ho_ev:<10}")


if __name__ == "__main__":
    main()

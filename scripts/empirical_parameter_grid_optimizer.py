#!/usr/bin/env python3
"""
Empirical Parameter Grid Optimizer for Polymarket 1-Hour Crypto Contracts.
Simulates Cartesian parameter grid across all recorded historical & live telemetry:
  - data/polymarket/live_shock_triggers.jsonl
  - data/polymarket/polymarket_hourly_telemetry.jsonl
  - data/polymarket/finalized_market_resolutions.jsonl
"""

import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "polymarket"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
TRIGGERS_FILE = DATA_DIR / "live_shock_triggers.jsonl"
TELEMETRY_FILE = DATA_DIR / "polymarket_hourly_telemetry.jsonl"


def calculate_taker_fee(notional_usd: float, price: float, fee_rate: float = 0.07, fee_exponent: float = 1.0) -> float:
    clamped_p = max(0.001, min(0.999, price))
    shares = notional_usd / clamped_p
    per_share_fee = fee_rate * ((clamped_p * (1.0 - clamped_p)) ** fee_exponent)
    return float(Decimal(str(shares * per_share_fee)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))


def is_nyse_open_window(ts_unix: float) -> bool:
    dt = datetime.fromtimestamp(ts_unix, tz=timezone.utc)
    # NYSE open is 9:30 AM ET -> 13:30 UTC. Blackout window: 13:30:00 to 13:59:59 UTC
    return dt.hour == 13 and dt.minute >= 30


def main():
    print("=" * 80)
    print("POLYMARKET EMPIRICAL PARAMETER GRID OPTIMIZATION")
    print("=" * 80)
    start_load_ts = time.time()

    # 1. Load Ground-Truth Market Resolutions
    resolutions = {}
    if RESOLUTIONS_FILE.exists():
        with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    resolutions[str(rec["market_id"])] = rec
    print(f"Loaded {len(resolutions)} finalized market resolutions.", flush=True)

    # 2. Load Candidate Shock Triggers First to get Candidate Market IDs
    triggers = []
    candidate_market_ids = set()
    if TRIGGERS_FILE.exists():
        with open(TRIGGERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                mid = str(rec.get("market_id"))
                if mid not in resolutions:
                    continue
                t0 = float(rec.get("t0_unix", 0.0))
                tte = float(rec.get("seconds_to_expiry", 0.0))
                s_dir = rec.get("shock_direction")  # "BUY" or "SELL"
                if not s_dir:
                    continue
                target = "UP" if s_dir == "BUY" else "DOWN"
                features = rec.get("pre_shock_features_t0", {})
                target_features = features.get(target, {})
                ask = float(target_features.get("best_ask", 0.0) or 0.0)
                bid = float(target_features.get("best_bid", 0.0) or 0.0)
                dist = float(rec.get("candle_distance_pct", 0.0))
                asset = rec.get("asset", "BTC")

                candidate_market_ids.add(mid)
                triggers.append({
                    "market_id": mid,
                    "asset": asset,
                    "t0_unix": t0,
                    "seconds_to_expiry": tte,
                    "target_token": target,
                    "ask_price": ask,
                    "bid_price": bid,
                    "candle_distance_pct": dist,
                    "title": rec.get("title", ""),
                })

    triggers.sort(key=lambda x: x["t0_unix"])
    print(f"Loaded {len(triggers)} candidate triggers across {len(candidate_market_ids)} target markets.", flush=True)

    # 3. Load Telemetry Only For Candidate Markets (Fast Filter)
    telemetry_by_market = defaultdict(list)
    t_telem_start = time.time()
    if TELEMETRY_FILE.exists():
        with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                # Quick substring check before expensive json.loads
                # Checks if any candidate mid is in line:
                rec = json.loads(line)
                mid = str(rec.get("market_id"))
                if mid not in candidate_market_ids:
                    continue

                ts = float(rec.get("timestamp_unix", 0.0))
                spot = float(rec.get("binance_spot", 0.0))
                dist = float(rec.get("candle_distance_pct", 0.0))
                up_b = float(rec.get("UP", {}).get("best_bid", 0.0) or 0.0)
                up_a = float(rec.get("UP", {}).get("best_ask", 0.0) or 0.0)
                dn_b = float(rec.get("DOWN", {}).get("best_bid", 0.0) or 0.0)
                dn_a = float(rec.get("DOWN", {}).get("best_ask", 0.0) or 0.0)
                telemetry_by_market[mid].append((ts, spot, dist, up_b, up_a, dn_b, dn_a))

    for mid in telemetry_by_market:
        telemetry_by_market[mid].sort(key=lambda x: x[0])
    print(f"Indexed high-resolution telemetry for {len(telemetry_by_market)} target markets in {time.time() - t_telem_start:.2f}s.", flush=True)

    # Grid Definitions
    policies = ["Policy A (Hold+99c TP)", "Policy B (Hold+99c TP+Spot Retrace Stop)"]
    price_floors = [0.72, 0.75, 0.78, 0.80]
    max_ttes = [600.0, 900.0, 1200.0, 1500.0]
    spot_cushions = [0.15, 0.20, 0.25]
    nyse_filters = [False, True]
    concurrencies = [1, 2]

    total_combos = (
        len(policies)
        * len(price_floors)
        * len(max_ttes)
        * len(spot_cushions)
        * len(nyse_filters)
        * len(concurrencies)
    )
    print(f"Total Parameter Combinations in Grid: {total_combos}")
    print("-" * 80)

    # Simulation Function
    def evaluate_grid_point(
        policy: str,
        p_floor: float,
        p_ceil: float,
        max_tte: float,
        min_cushion: float,
        nyse_filter: bool,
        max_concurrent: int,
    ) -> Dict[str, Any]:
        trades = []
        active_positions = []  # list of dicts: {'market_id': ..., 'asset': ..., 'expiry_ts': ...}
        traded_market_ids = set()

        for trig in triggers:
            mid = trig["market_id"]
            if mid in traded_market_ids:
                continue

            t0 = trig["t0_unix"]
            # Expire finished positions from active_positions list
            active_positions = [p for p in active_positions if p["expiry_ts"] > t0]

            if len(active_positions) >= max_concurrent:
                continue

            # Concurrency check per asset: never hold 2 of the same asset
            if any(p["asset"] == trig["asset"] for p in active_positions):
                continue

            # Filters:
            tte = trig["seconds_to_expiry"]
            if tte > max_tte or tte < 120.0:
                continue

            ask = trig["ask_price"]
            if ask < p_floor or ask > p_ceil:
                continue

            dist = trig["candle_distance_pct"]
            target = trig["target_token"]
            if abs(dist) < min_cushion:
                continue
            if target == "UP" and dist < min_cushion:
                continue
            if target == "DOWN" and dist > -min_cushion:
                continue

            if nyse_filter and is_nyse_open_window(t0):
                continue

            # Trade execution:
            res = resolutions[mid]
            candle_close_ts = float(res.get("candle_close_ts", t0 + tte))
            winning_outcome = res.get("winning_outcome")

            notional = 25.00
            entry_px = ask
            shares = notional / entry_px
            entry_fee = calculate_taker_fee(notional, entry_px)

            # Post-entry outcome evaluation:
            market_telem = telemetry_by_market.get(mid, [])
            post_entry_telem = [pt for pt in market_telem if pt[0] >= t0]

            exit_price = None
            exit_reason = None

            # Policy B: Check spot strike retrace
            if "Policy B" in policy:
                # Retrace check: spot crosses back across open by 5 bps against position for >= 15 consecutive seconds
                # UP position: dist <= -0.05%
                # DOWN position: dist >= +0.05%
                consecutive_adverse_start = None
                for pt in post_entry_telem:
                    pt_ts, pt_spot, pt_dist, pt_up_b, pt_up_a, pt_dn_b, pt_dn_a = pt
                    is_adverse = (pt_dist <= -0.05) if target == "UP" else (pt_dist >= 0.05)
                    if is_adverse:
                        if consecutive_adverse_start is None:
                            consecutive_adverse_start = pt_ts
                        elif pt_ts - consecutive_adverse_start >= 15.0:
                            # Strike-retrace stop triggered!
                            bid_at_stop = pt_up_b if target == "UP" else pt_dn_b
                            exit_price = max(0.40, min(0.65, bid_at_stop if bid_at_stop > 0.01 else 0.45))
                            exit_reason = "STRIKE_RETRACE_STOP"
                            break
                    else:
                        consecutive_adverse_start = None

            # If not stopped out by Policy B, check 99c Maker TP fill:
            if exit_price is None:
                for pt in post_entry_telem:
                    pt_ts, pt_spot, pt_dist, pt_up_b, pt_up_a, pt_dn_b, pt_dn_a = pt
                    target_ask = pt_up_a if target == "UP" else pt_dn_a
                    target_bid = pt_up_b if target == "UP" else pt_dn_b
                    # If market touched 99c or better
                    if target_ask >= 0.99 or target_bid >= 0.99:
                        exit_price = 0.99
                        exit_reason = "MAKER_TP_99C"
                        break

            # If still open, hold to maturity settlement:
            if exit_price is None:
                if target == winning_outcome:
                    exit_price = 1.00
                    exit_reason = "EXPIRY_WON"
                else:
                    exit_price = 0.00
                    exit_reason = "EXPIRY_LOST"

            # Financial calculation:
            payout = shares * exit_price
            exit_fee = 0.0  # 0% maker / redemption fee
            net_pnl = payout - notional - entry_fee - exit_fee
            won = (net_pnl > 0)

            trades.append({
                "market_id": mid,
                "asset": trig["asset"],
                "target": target,
                "entry_price": entry_px,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "notional": notional,
                "net_pnl": net_pnl,
                "won": won,
                "entry_time": t0,
            })

            traded_market_ids.add(mid)
            active_positions.append({
                "market_id": mid,
                "asset": trig["asset"],
                "expiry_ts": candle_close_ts,
            })

        # Calculate portfolio metrics:
        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "net_pnl": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "params": {},
            }

        wins = [t for t in trades if t["won"]]
        losses = [t for t in trades if not t["won"]]
        win_rate = (len(wins) / total_trades) * 100.0

        gross_profit = sum(t["net_pnl"] for t in wins)
        gross_loss = abs(sum(t["net_pnl"] for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
        net_pnl = sum(t["net_pnl"] for t in trades)

        # Max Drawdown calculation:
        cum_pnl = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in trades:
            cum_pnl += t["net_pnl"]
            if cum_pnl > peak:
                peak = cum_pnl
            dd = peak - cum_pnl
            if dd > max_dd:
                max_dd = dd

        return {
            "total_trades": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "net_pnl": net_pnl,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "params": {
                "policy": policy,
                "p_floor": p_floor,
                "p_ceil": p_ceil,
                "max_tte": max_tte,
                "min_cushion": min_cushion,
                "nyse_filter": nyse_filter,
                "max_concurrent": max_concurrent,
            },
        }

    # Run the grid search
    grid_results = []
    p_ceil = 0.88
    step = 0
    t_sim_start = time.time()

    for pol in policies:
        for pf in price_floors:
            for mt in max_ttes:
                for mc in spot_cushions:
                    for nf in nyse_filters:
                        for cc in concurrencies:
                            step += 1
                            res = evaluate_grid_point(
                                policy=pol,
                                p_floor=pf,
                                p_ceil=p_ceil,
                                max_tte=mt,
                                min_cushion=mc,
                                nyse_filter=nf,
                                max_concurrent=cc,
                            )
                            grid_results.append(res)

    print(f"Simulation completed across {len(grid_results)} combinations in {time.time() - t_sim_start:.2f}s.\n")

    # Filter candidates with at least 15 trades
    valid_results = [r for r in grid_results if r["total_trades"] >= 10]
    valid_results.sort(key=lambda x: (x["net_pnl"], x["profit_factor"], x["win_rate"]), reverse=True)

    print("=" * 120)
    print(f"{'RANK':<4} | {'POLICY':<22} | {'FLOOR':<5} | {'TTE':<5} | {'CUSHION':<7} | {'NYSE_BLK':<8} | {'CONC':<4} | {'TRADES':<6} | {'WIN %':<7} | {'PROFIT FACTOR':<13} | {'MAX DD ($)':<10} | {'NET PNL ($)':<10}")
    print("-" * 120)

    for i, r in enumerate(valid_results[:15], 1):
        p = r["params"]
        pol_short = "Policy A (Pure Hold)" if "Policy A" in p["policy"] else "Policy B (Spot Retrace)"
        print(
            f"{i:<4} | {pol_short:<22} | {p['p_floor']:<5.2f} | {int(p['max_tte']):<4}s | "
            f"{p['min_cushion']*100:<5.1f}% | {str(p['nyse_filter']):<8} | {p['max_concurrent']:<4} | "
            f"{r['total_trades']:<6} | {r['win_rate']:<6.1f}% | {r['profit_factor']:<13.2f} | "
            f"${r['max_drawdown']:<9.2f} | +${r['net_pnl']:<9.2f}"
        )
    print("=" * 120)

    # Save top results to JSON artifact
    out_path = DATA_DIR / "grid_optimization_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(valid_results[:25], f, indent=2)
    print(f"Saved Top 25 combinations to {out_path}")


if __name__ == "__main__":
    main()

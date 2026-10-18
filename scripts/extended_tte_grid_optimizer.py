#!/usr/bin/env python3
"""
Extended Max TTE Grid Optimizer (25m to 50m) for Polymarket 1-Hour Contracts.
Evaluates:
  - Max TTE: [1500s, 1800s, 2100s, 2400s, 2700s, 3000s]
  - Cushion Modes: [0.15% flat, 0.18% flat, 0.20% flat, Tiered (0.20% if TTE>1500s else 0.15%)]
  - Concurrency: max_concurrent = 2 (and max_concurrent = 1)
  - Policy: Policy B (Spot-Retrace stop 15s confirmation + 99c Maker TP)
  - Price bounds: [0.72, 0.88]
  - NYSE Blackout: 13:30-14:00 UTC
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
    return dt.hour == 13 and dt.minute >= 30


def main():
    print("=" * 85)
    print("EXTENDED MAX TTE GRID OPTIMIZATION (25m to 50m)")
    print("=" * 85)
    t_start = time.time()

    # 1. Load Ground-Truth Market Resolutions
    resolutions = {}
    if RESOLUTIONS_FILE.exists():
        with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    resolutions[str(rec["market_id"])] = rec
    print(f"Loaded {len(resolutions)} finalized market resolutions.", flush=True)

    # 2. Load Candidate Shock Triggers
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
                s_dir = rec.get("shock_direction")
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
    print(f"Loaded {len(triggers)} candidate triggers across {len(candidate_market_ids)} markets.", flush=True)

    # 3. Load Telemetry for candidate markets
    telemetry_by_market = defaultdict(list)
    t_telem_start = time.time()
    if TELEMETRY_FILE.exists():
        with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
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
    print(f"Indexed high-res telemetry in {time.time() - t_telem_start:.2f}s.\n", flush=True)

    # 4. Simulation Engine
    def simulate(max_tte: float, cushion_mode: str, max_concurrent: int) -> Dict[str, Any]:
        trades = []
        active_positions = []
        traded_market_ids = set()

        for trig in triggers:
            mid = trig["market_id"]
            if mid in traded_market_ids:
                continue

            t0 = trig["t0_unix"]
            active_positions = [p for p in active_positions if p["expiry_ts"] > t0]
            if len(active_positions) >= max_concurrent:
                continue

            if any(p["asset"] == trig["asset"] for p in active_positions):
                continue

            tte = trig["seconds_to_expiry"]
            if tte > max_tte or tte < 120.0:
                continue

            ask = trig["ask_price"]
            if ask < 0.72 or ask > 0.88:
                continue

            dist = trig["candle_distance_pct"]
            target = trig["target_token"]

            # Cushion threshold:
            if cushion_mode == "0.15%":
                req_cushion = 0.15
            elif cushion_mode == "0.18%":
                req_cushion = 0.18
            elif cushion_mode == "0.20%":
                req_cushion = 0.20
            elif cushion_mode == "Tiered":
                req_cushion = 0.20 if tte > 1500.0 else 0.15
            else:
                req_cushion = 0.15

            if abs(dist) < req_cushion:
                continue
            if target == "UP" and dist < req_cushion:
                continue
            if target == "DOWN" and dist > -req_cushion:
                continue

            if is_nyse_open_window(t0):
                continue

            # Trade entered
            res = resolutions[mid]
            candle_close_ts = float(res.get("candle_close_ts", t0 + tte))
            winning_outcome = res.get("winning_outcome")

            notional = 25.00
            entry_px = ask
            shares = notional / entry_px
            entry_fee = calculate_taker_fee(notional, entry_px)

            market_telem = telemetry_by_market.get(mid, [])
            post_entry_telem = [pt for pt in market_telem if pt[0] >= t0]

            exit_price = None
            exit_reason = None

            # Policy B spot retrace check (15s persistence)
            consecutive_adverse_start = None
            for pt in post_entry_telem:
                pt_ts, pt_spot, pt_dist, pt_up_b, pt_up_a, pt_dn_b, pt_dn_a = pt
                is_adverse = (pt_dist <= -0.05) if target == "UP" else (pt_dist >= 0.05)
                if is_adverse:
                    if consecutive_adverse_start is None:
                        consecutive_adverse_start = pt_ts
                    elif pt_ts - consecutive_adverse_start >= 15.0:
                        bid_at_stop = pt_up_b if target == "UP" else pt_dn_b
                        exit_price = max(0.40, min(0.65, bid_at_stop if bid_at_stop > 0.01 else 0.45))
                        exit_reason = "STRIKE_RETRACE_STOP"
                        break
                else:
                    consecutive_adverse_start = None

            # 99c Maker TP
            if exit_price is None:
                for pt in post_entry_telem:
                    pt_ts, pt_spot, pt_dist, pt_up_b, pt_up_a, pt_dn_b, pt_dn_a = pt
                    target_ask = pt_up_a if target == "UP" else pt_dn_a
                    target_bid = pt_up_b if target == "UP" else pt_dn_b
                    if target_ask >= 0.99 or target_bid >= 0.99:
                        exit_price = 0.99
                        exit_reason = "MAKER_TP_99C"
                        break

            # Settlement
            if exit_price is None:
                if target == winning_outcome:
                    exit_price = 1.00
                    exit_reason = "EXPIRY_WON"
                else:
                    exit_price = 0.00
                    exit_reason = "EXPIRY_LOST"

            exit_dollars = shares * exit_price
            exit_fee = calculate_taker_fee(exit_dollars, exit_price) if exit_reason == "STRIKE_RETRACE_STOP" else 0.0
            net_pnl = exit_dollars - notional - entry_fee - exit_fee
            won = net_pnl > 0.0

            trades.append({
                "market_id": mid,
                "asset": trig["asset"],
                "entry_ts": t0,
                "tte": tte,
                "entry_px": entry_px,
                "exit_px": exit_price,
                "exit_reason": exit_reason,
                "net_pnl": net_pnl,
                "won": won,
            })
            traded_market_ids.add(mid)
            active_positions.append({"market_id": mid, "asset": trig["asset"], "expiry_ts": candle_close_ts})

        if not trades:
            return {"total_trades": 0, "win_rate": 0.0, "net_pnl": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0}

        wins = [t for t in trades if t["won"]]
        losses = [t for t in trades if not t["won"]]
        wr = (len(wins) / len(trades)) * 100.0

        gross_profit = sum(t["net_pnl"] for t in wins)
        gross_loss = abs(sum(t["net_pnl"] for t in losses))
        pf = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
        net_pnl = sum(t["net_pnl"] for t in trades)

        # Max Drawdown
        cum = 0.0
        peak = 0.0
        mdd = 0.0
        for t in trades:
            cum += t["net_pnl"]
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > mdd:
                mdd = dd

        return {
            "max_tte": max_tte,
            "cushion_mode": cushion_mode,
            "max_concurrent": max_concurrent,
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": wr,
            "profit_factor": pf,
            "max_drawdown": mdd,
            "net_pnl": net_pnl,
        }

    # Grid runs
    max_ttes = [1500.0, 1800.0, 2100.0, 2400.0, 2700.0, 3000.0]
    cushion_modes = ["0.15%", "0.18%", "0.20%", "Tiered"]
    concurrencies = [2, 1]

    results = []
    for conc in concurrencies:
        for c_mode in cushion_modes:
            for tte_val in max_ttes:
                res = simulate(tte_val, c_mode, conc)
                results.append(res)

    results.sort(key=lambda x: x["net_pnl"], reverse=True)

    print(f"{'Rank':<4} | {'Conc':<4} | {'Max TTE':<10} | {'Cushion Mode':<12} | {'Trades':<6} | {'Win Rate':<8} | {'PF':<6} | {'Max DD':<8} | {'Net PnL':<10}")
    print("-" * 85)
    for i, r in enumerate(results[:20], 1):
        tte_str = f"{int(r['max_tte'])}s ({int(r['max_tte']/60)}m)"
        print(f"#{i:<3} | {r['max_concurrent']:<4} | {tte_str:<10} | {r['cushion_mode']:<12} | {r['total_trades']:<6} | {r['win_rate']:<7.1f}% | {r['profit_factor']:<6.2f} | ${r['max_drawdown']:<7.2f} | +${r['net_pnl']:<9.2f}")

    # Save to file
    out_file = DATA_DIR / "extended_tte_grid_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved all {len(results)} configurations to {out_file}.")


if __name__ == "__main__":
    main()

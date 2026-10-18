#!/usr/bin/env python3
"""
Full Multi-Parameter Flawlessness Optimization across 583 Resolved Markets.
Strict Objective: Win Rate >= 93.0%, Max Drawdown <= $26.00, Profit Factor >= 3.60.
1. Forensic audit of the 5 baseline losses (timestamp, asset, hour, dist, exit reason).
2. Hourly UTC blackout scan across all 24 hours.
3. Multi-parameter sweep over:
   - Early Blowout Gate (1500s < TTE <= 2500s): early_cushion in [0.35%, 0.40%, 0.45%, 0.50%], early_min_p in [0.78, 0.80]
   - Late Window Price Floor: [0.70, 0.72, 0.75, 0.78]
   - Price Ceiling: [0.88, 0.90, 0.92, 0.93]
   - Late Window Cushion: [0.12%, 0.15%, 0.18%, 0.20%]
   - Spot-Retrace Stop threshold & persistence: [-0.03%, -0.05%, -0.08%] x [10s, 15s, 25s]
   - Maker TP target: [0.98, 0.99, 1.00]
"""

import json
import math
import sys
import time
from collections import defaultdict, Counter
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
    print("POLYMARKET FULL MULTI-PARAMETER FLAWLESSNESS OPTIMIZATION")
    print("=" * 85)

    # 1. Load Ground-Truth Market Resolutions
    resolutions = {}
    with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                resolutions[str(rec["market_id"])] = rec
    print(f"Loaded {len(resolutions)} finalized market resolutions.")

    # 2. Load Candidate Triggers
    triggers = []
    candidate_mids = set()
    with open(TRIGGERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            mid = str(rec.get("market_id"))
            if mid not in resolutions:
                continue
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

            candidate_mids.add(mid)
            triggers.append({
                "market_id": mid,
                "asset": asset,
                "t0_unix": float(rec.get("t0_unix", 0.0)),
                "seconds_to_expiry": float(rec.get("seconds_to_expiry", 0.0)),
                "target_token": target,
                "ask_price": ask,
                "bid_price": bid,
                "candle_distance_pct": dist,
                "title": rec.get("title", ""),
            })

    triggers.sort(key=lambda x: x["t0_unix"])
    print(f"Loaded {len(triggers)} candidate triggers across {len(candidate_mids)} markets.")

    # 3. Load Telemetry
    telemetry_by_market = defaultdict(list)
    t_start = time.time()
    with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            mid = str(rec.get("market_id"))
            if mid not in candidate_mids:
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
    print(f"Indexed high-res telemetry in {time.time() - t_start:.2f}s.\n")

    # =========================================================================
    # PART A: FORENSIC AUDIT OF THE 5 LOSSES IN ROW #4 (1500s Baseline)
    # =========================================================================
    print("=" * 85)
    print("PART A: FORENSIC AUDIT OF THE 5 LOSSES IN BASELINE (1500s, 0.15% cushion, $0.72-$0.88)")
    print("=" * 85)

    def run_simulation(
        max_tte: float = 1500.0,
        early_cushion: Optional[float] = None,
        early_min_p: float = 0.78,
        late_floor: float = 0.72,
        p_ceil: float = 0.88,
        late_cushion: float = 0.15,
        retrace_thresh: float = -0.05,
        retrace_persist: float = 15.0,
        tp_target: float = 0.99,
        extra_blackout_hours: Optional[List[int]] = None,
        max_conc: int = 2,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        trades = []
        active_positions = []
        traded_market_ids = set()

        for trig in triggers:
            mid = trig["market_id"]
            if mid in traded_market_ids:
                continue

            t0 = trig["t0_unix"]
            active_positions = [p for p in active_positions if p["expiry_ts"] > t0]
            if len(active_positions) >= max_conc:
                continue
            if any(p["asset"] == trig["asset"] for p in active_positions):
                continue

            tte = trig["seconds_to_expiry"]
            if tte > max_tte or tte < 120.0:
                continue

            dt = datetime.fromtimestamp(t0, tz=timezone.utc)
            if is_nyse_open_window(t0):
                continue
            if extra_blackout_hours and dt.hour in extra_blackout_hours:
                continue

            ask = trig["ask_price"]
            dist = trig["candle_distance_pct"]
            target = trig["target_token"]

            # Early window vs Late window rules:
            if tte > 1500.0:
                if early_cushion is None:
                    continue  # Early window disabled
                if abs(dist) < early_cushion:
                    continue
                if target == "UP" and dist < early_cushion:
                    continue
                if target == "DOWN" and dist > -early_cushion:
                    continue
                if ask < early_min_p or ask > p_ceil:
                    continue
            else:
                if abs(dist) < late_cushion:
                    continue
                if target == "UP" and dist < late_cushion:
                    continue
                if target == "DOWN" and dist > -late_cushion:
                    continue
                if ask < late_floor or ask > p_ceil:
                    continue

            # Position opened
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

            # Policy B spot retrace check
            consecutive_adverse_start = None
            for pt in post_entry_telem:
                pt_ts, pt_spot, pt_dist, pt_up_b, pt_up_a, pt_dn_b, pt_dn_a = pt
                is_adverse = (pt_dist <= retrace_thresh) if target == "UP" else (pt_dist >= -retrace_thresh)
                if is_adverse:
                    if consecutive_adverse_start is None:
                        consecutive_adverse_start = pt_ts
                    elif pt_ts - consecutive_adverse_start >= retrace_persist:
                        bid_at_stop = pt_up_b if target == "UP" else pt_dn_b
                        exit_price = max(0.40, min(0.65, bid_at_stop if bid_at_stop > 0.01 else 0.45))
                        exit_reason = "STRIKE_RETRACE_STOP"
                        break
                else:
                    consecutive_adverse_start = None

            # Maker TP check
            if exit_price is None and tp_target < 1.00:
                for pt in post_entry_telem:
                    pt_ts, pt_spot, pt_dist, pt_up_b, pt_up_a, pt_dn_b, pt_dn_a = pt
                    target_ask = pt_up_a if target == "UP" else pt_dn_a
                    target_bid = pt_up_b if target == "UP" else pt_dn_b
                    if target_ask >= tp_target or target_bid >= tp_target:
                        exit_price = tp_target
                        exit_reason = f"MAKER_TP_{int(tp_target*100)}C"
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
                "utc_hour": dt.hour,
                "utc_str": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "tte": tte,
                "target": target,
                "dist": dist,
                "entry_px": entry_px,
                "exit_px": exit_price,
                "exit_reason": exit_reason,
                "winning_outcome": winning_outcome,
                "net_pnl": net_pnl,
                "won": won,
            })
            traded_market_ids.add(mid)
            active_positions.append({"market_id": mid, "asset": trig["asset"], "expiry_ts": candle_close_ts})

        if not trades:
            stats = {"total_trades": 0, "win_rate": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "net_pnl": 0.0}
            return trades, stats

        wins = [t for t in trades if t["won"]]
        losses = [t for t in trades if not t["won"]]
        wr = (len(wins) / len(trades)) * 100.0
        gp = sum(t["net_pnl"] for t in wins)
        gl = abs(sum(t["net_pnl"] for t in losses))
        pf = (gp / gl) if gl > 0 else 999.0
        cum = peak = mdd = 0.0
        for t in trades:
            cum += t["net_pnl"]
            if cum > peak:
                peak = cum
            if peak - cum > mdd:
                mdd = peak - cum

        stats = {
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": wr,
            "profit_factor": pf,
            "max_drawdown": mdd,
            "net_pnl": sum(t["net_pnl"] for t in trades),
        }
        return trades, stats

    # Baseline 1500s run
    baseline_trades, baseline_stats = run_simulation(max_tte=1500.0, late_floor=0.72, p_ceil=0.88, late_cushion=0.15)
    baseline_losses = [t for t in baseline_trades if not t["won"]]

    print(f"Baseline Summary: {baseline_stats['total_trades']} trades | {baseline_stats['wins']}W / {baseline_stats['losses']}L | {baseline_stats['win_rate']:.1f}% WR | PF: {baseline_stats['profit_factor']:.2f} | MDD: ${baseline_stats['max_drawdown']:.2f} | Net: +${baseline_stats['net_pnl']:.2f}")
    print("\nDetailed Forensic Log of the 5 Baseline Losses:")
    print(f"{'#':<2} | {'Timestamp (UTC)':<22} | {'Asset':<5} | {'Token':<5} | {'TTE':<6} | {'Dist':<8} | {'Entry':<6} | {'Exit':<6} | {'Exit Reason':<20} | {'Loss ($)':<8}")
    print("-" * 105)
    for i, l in enumerate(baseline_losses, 1):
        print(f"#{i:<1} | {l['utc_str']:<22} | {l['asset']:<5} | {l['target']:<5} | {int(l['tte']):<4}s | {l['dist']:+6.2f}% | ${l['entry_px']:<5.2f} | ${l['exit_px']:<5.2f} | {l['exit_reason']:<20} | ${l['net_pnl']:<7.2f}")

    # Loss distribution across hours
    loss_hours = Counter(l["utc_hour"] for l in baseline_losses)
    print("\nLoss Distribution by UTC Hour:", dict(loss_hours))

    # Test if blacking out any single hour removes losses without sacrificing net PnL:
    hourly_impact = {}
    for hr in range(24):
        _, hr_stats = run_simulation(max_tte=1500.0, extra_blackout_hours=[hr])
        hourly_impact[hr] = hr_stats

    best_hr_remove = sorted(hourly_impact.items(), key=lambda x: x[1]["profit_factor"], reverse=True)[:3]
    print(f"Top hours where blacking out improves Profit Factor: {[(h, round(s['profit_factor'], 2), round(s['net_pnl'], 2)) for h, s in best_hr_remove]}")

    # =========================================================================
    # PART B: MULTI-PARAMETER FLAWLESSNESS SWEEP
    # =========================================================================
    print("\n" + "=" * 85)
    print("PART B: MULTI-PARAMETER FLAWLESSNESS SWEEP (Strict WR >= 93%, Max DD <= $26, PF >= 3.60)")
    print("=" * 85)

    early_cushions = [None, 0.35, 0.40, 0.45, 0.50]
    early_min_prices = [0.78, 0.80]
    max_ttes = [1500.0, 2100.0, 2400.0, 2500.0]
    late_floors = [0.70, 0.72, 0.75, 0.78]
    p_ceils = [0.88, 0.90, 0.92]
    late_cushions = [0.15, 0.18, 0.20]
    retrace_threshs = [-0.03, -0.05, -0.08]
    retrace_persists = [10.0, 15.0, 25.0]
    tp_targets = [0.98, 0.99, 1.00]

    grid_results = []
    t_sweep_start = time.time()

    # Smart pruning: iterate through combinations
    for tp in tp_targets:
        for r_thresh in retrace_threshs:
            for r_persist in retrace_persists:
                for l_cush in late_cushions:
                    for l_floor in late_floors:
                        for p_ceil in p_ceils:
                            # 1. Baseline window only (max_tte = 1500)
                            _, s_base = run_simulation(
                                max_tte=1500.0,
                                early_cushion=None,
                                late_floor=l_floor,
                                p_ceil=p_ceil,
                                late_cushion=l_cush,
                                retrace_thresh=r_thresh,
                                retrace_persist=r_persist,
                                tp_target=tp,
                                max_conc=2,
                            )
                            if s_base["win_rate"] >= 93.0 and s_base["profit_factor"] >= 3.60 and s_base["max_drawdown"] <= 26.00:
                                grid_results.append({
                                    "params": {
                                        "max_tte": 1500.0, "early_cushion": None, "early_min_p": None,
                                        "late_floor": l_floor, "p_ceil": p_ceil, "late_cushion": l_cush,
                                        "retrace_thresh": r_thresh, "retrace_persist": r_persist, "tp_target": tp,
                                    },
                                    "stats": s_base,
                                })

                            # 2. Early blowout window enabled (max_tte in [2100, 2400, 2500])
                            for e_cush in [0.35, 0.40, 0.45, 0.50]:
                                for e_p in early_min_prices:
                                    for tte_val in [2100.0, 2400.0, 2500.0]:
                                        _, s_early = run_simulation(
                                            max_tte=tte_val,
                                            early_cushion=e_cush,
                                            early_min_p=e_p,
                                            late_floor=l_floor,
                                            p_ceil=p_ceil,
                                            late_cushion=l_cush,
                                            retrace_thresh=r_thresh,
                                            retrace_persist=r_persist,
                                            tp_target=tp,
                                            max_conc=2,
                                        )
                                        if s_early["win_rate"] >= 93.0 and s_early["profit_factor"] >= 3.60 and s_early["max_drawdown"] <= 26.00:
                                            grid_results.append({
                                                "params": {
                                                    "max_tte": tte_val, "early_cushion": e_cush, "early_min_p": e_p,
                                                    "late_floor": l_floor, "p_ceil": p_ceil, "late_cushion": l_cush,
                                                    "retrace_thresh": r_thresh, "retrace_persist": r_persist, "tp_target": tp,
                                                },
                                                "stats": s_early,
                                            })

    print(f"Sweep complete in {time.time() - t_sweep_start:.2f}s.")
    print(f"Found {len(grid_results)} combinations passing Flawlessness Filter (WR >= 93.0%, Max DD <= $26, PF >= 3.60).\n")

    # Sort by Net PnL descending
    grid_results.sort(key=lambda x: (x["stats"]["net_pnl"], x["stats"]["profit_factor"]), reverse=True)

    print("=" * 115)
    print(f"{'Rank':<4} | {'TTE':<5} | {'Early Cush':<10} | {'Floor-Ceil':<11} | {'Late Cush':<9} | {'Stop/Persist':<12} | {'TP':<4} | {'Trades':<6} | {'WR':<6} | {'PF':<5} | {'Max DD':<7} | {'Net PnL':<9}")
    print("=" * 115)
    for i, res in enumerate(grid_results[:15], 1):
        p = res["params"]
        s = res["stats"]
        e_str = f">={p['early_cushion']}%" if p['early_cushion'] else "DISABLED"
        fc_str = f"{p['late_floor']}-{p['p_ceil']}"
        stop_str = f"{p['retrace_thresh']}%/{int(p['retrace_persist'])}s"
        tp_str = f"{int(p['tp_target']*100)}c" if p['tp_target'] < 1.0 else "100c"
        print(f"#{i:<3} | {int(p['max_tte']):<5} | {e_str:<10} | {fc_str:<11} | >={p['late_cushion']:<6.2f}% | {stop_str:<12} | {tp_str:<4} | {s['total_trades']:<6} | {s['win_rate']:<5.1f}% | {s['profit_factor']:<5.2f} | ${s['max_drawdown']:<6.2f} | +${s['net_pnl']:<8.2f}")

    # Save to JSON
    with open(DATA_DIR / "flawlessness_optimization_results.json", "w") as f:
        json.dump(grid_results, f, indent=2)


if __name__ == "__main__":
    main()

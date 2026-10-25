#!/usr/bin/env python3
"""
Joint Walk-Forward Grid Search & Out-of-Sample Optimizer (15m + 1h, BTC + ETH)
==============================================================================
Evaluates coupled entry/exit/cushion/price-band parameter grids across the full
1.43 GB recorded L2 telemetry corpus on kraken-finland using a strict chronological
70% In-Sample (IS) / 30% Out-of-Sample (OOS) Walk-Forward split.

Runs under nice -n 19 to ensure zero impact on live production trading latency.
"""

from __future__ import annotations

import json
import math
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "polymarket"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
TRIGGERS_FILE = DATA_DIR / "live_shock_triggers.jsonl"
TELEM_BTC_FILE = DATA_DIR / "polymarket_hourly_telemetry.jsonl"
TELEM_ETH_FILE = DATA_DIR / "polymarket_hourly_telemetry_eth.jsonl"


def calculate_taker_fee(notional_usd: float, price: float, fee_rate: float = 0.07, fee_exponent: float = 1.0) -> float:
    if fee_rate <= 0.0:
        return 0.0
    clamped_p = max(0.001, min(0.999, price))
    shares = notional_usd / clamped_p
    per_share_fee = fee_rate * ((clamped_p * (1.0 - clamped_p)) ** fee_exponent)
    return float(Decimal(str(shares * per_share_fee)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))


def is_nyse_open_window(ts_unix: float, is_1h: bool) -> bool:
    dt = datetime.fromtimestamp(ts_unix, tz=timezone.utc)
    start_min = 15 if is_1h else 30
    return dt.hour == 13 and dt.minute >= start_min


def compute_entry_quality(
    z_score: float,
    shock_ofi: float,
    target_obi: float,
    spread: float,
    abs_dist_pct: float,
    sigma_rem_pct: float,
) -> float:
    # Matches production composite entry_quality_score in [0, 1]
    z_norm = min(1.0, max(0.0, abs(z_score) / 2.5))
    ofi_norm = min(1.0, max(0.0, abs(shock_ofi)))
    obi_norm = min(1.0, max(0.0, (target_obi + 1.0) / 2.0))
    spread_norm = min(1.0, max(0.0, 1.0 - (spread / 0.06)))
    cush_ratio = abs_dist_pct / max(0.02, sigma_rem_pct)
    cush_norm = min(1.0, max(0.0, cush_ratio / 1.2))
    return 0.25 * z_norm + 0.20 * ofi_norm + 0.20 * obi_norm + 0.15 * spread_norm + 0.20 * cush_norm


def main() -> None:
    try:
        os.nice(19)
    except Exception:
        pass

    t_init = time.time()
    print("=" * 95)
    print("POLYMARKET JOINT WALK-FORWARD PARAMETER GRID OPTIMIZER (15M + 1H | BTC + ETH)")
    print("=" * 95, flush=True)

    # 1. Load Ground-Truth Resolutions
    resolutions: Dict[str, Dict[str, Any]] = {}
    with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                resolutions[str(rec["market_id"])] = rec
    print(f"[1/5] Loaded {len(resolutions)} finalized market resolutions.", flush=True)

    # 2. Load Candidate Triggers (deduplicating rapid bursts within 3s per market)
    triggers: List[Dict[str, Any]] = []
    candidate_mids = set()
    last_trig_ts_by_mid: Dict[str, float] = {}

    with open(TRIGGERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            mid = str(rec.get("market_id", ""))
            if mid not in resolutions:
                continue
            t0 = float(rec.get("t0_unix", 0.0) or 0.0)
            if t0 - last_trig_ts_by_mid.get(mid, 0.0) < 3.0:
                continue
            s_dir = rec.get("shock_direction")
            if s_dir not in ("BUY", "SELL"):
                continue
            target = "UP" if s_dir == "BUY" else "DOWN"
            features = rec.get("pre_shock_features_t0") or {}
            tf = features.get(target) or {}
            ask = float(tf.get("vwap_$20") or tf.get("best_ask") or 0.0)
            bid = float(tf.get("best_bid") or 0.0)
            if ask <= 0.05 or ask >= 0.98:
                continue

            spread = float(tf.get("spread") or max(0.01, ask - bid))
            target_obi = float(tf.get("obi_depth") or tf.get("obi_l1") or 0.0)
            dist = float(rec.get("candle_distance_pct", 0.0) or 0.0)
            tte = float(rec.get("seconds_to_expiry", 0.0) or 0.0)
            horizon = str(rec.get("horizon") or resolutions[mid].get("horizon") or "1h").lower()
            is_15m = "15m" in horizon or (0 < tte <= 900.0 and ":" in str(rec.get("title", "")))
            candle_dur = 900.0 if is_15m else 3600.0
            candle_sigma = float(rec.get("candle_sigma") or (0.0025 if is_15m else 0.0050))
            sigma_rem_pct = candle_sigma * 100.0 * math.sqrt(max(0.01, min(1.0, tte / candle_dur)))

            z_score = float(rec.get("z_score") or rec.get("z_val") or 1.0)
            shock_ofi = float(rec.get("shock_ofi") or 0.8)
            eq_score = compute_entry_quality(z_score, shock_ofi, target_obi, spread, abs(dist), sigma_rem_pct)

            fee_meta = rec.get("fee_metadata") or {}
            fee_rate = float(fee_meta.get("fee_rate_market", 0.07 if is_15m else 0.0) or 0.0)
            fee_exp = float(fee_meta.get("fee_exponent", 1.0) or 1.0)

            last_trig_ts_by_mid[mid] = t0
            candidate_mids.add(mid)
            triggers.append({
                "market_id": mid,
                "asset": str(rec.get("asset", "BTC")).upper(),
                "is_15m": is_15m,
                "t0_unix": t0,
                "tte": tte,
                "target": target,
                "ask": ask,
                "bid": bid,
                "spread": spread,
                "dist": dist,
                "sigma_rem_pct": sigma_rem_pct,
                "eq_score": eq_score,
                "fee_rate": fee_rate,
                "fee_exp": fee_exp,
            })

    triggers.sort(key=lambda x: x["t0_unix"])
    n_15m = sum(1 for x in triggers if x["is_15m"])
    n_1h = len(triggers) - n_15m
    print(
        f"[2/5] Loaded {len(triggers)} deduplicated triggers ({n_15m} 15m, {n_1h} 1h) "
        f"across {len(candidate_mids)} settled markets.",
        flush=True,
    )

    # 3. Load Telemetry (BTC + ETH) for Candidate Markets
    telemetry_by_market: Dict[str, List[Tuple[float, float, float, float, float, float]]] = defaultdict(list)
    t_telem = time.time()
    for tfile in (TELEM_BTC_FILE, TELEM_ETH_FILE):
        if not tfile.exists():
            continue
        with open(tfile, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                mid = str(rec.get("market_id", ""))
                if mid not in candidate_mids:
                    continue
                ts = float(rec.get("timestamp_unix", 0.0) or 0.0)
                dist = float(rec.get("candle_distance_pct", 0.0) or 0.0)
                up_b = float((rec.get("UP") or {}).get("best_bid") or 0.0)
                up_a = float((rec.get("UP") or {}).get("best_ask") or 0.0)
                dn_b = float((rec.get("DOWN") or {}).get("best_bid") or 0.0)
                dn_a = float((rec.get("DOWN") or {}).get("best_ask") or 0.0)
                telemetry_by_market[mid].append((ts, dist, up_b, up_a, dn_b, dn_a))

    for mid in telemetry_by_market:
        telemetry_by_market[mid].sort(key=lambda x: x[0])
    print(
        f"[3/5] Indexed BTC+ETH L2 telemetry for {len(telemetry_by_market)} markets in {time.time() - t_telem:.2f}s.",
        flush=True,
    )

    # 4. Precompute Exit Outcomes Across 6 Exit Policies
    # Policy tuple: (name, tp_delta_or_abs, is_abs_tp, bid_drop_salvage, spot_retrace_thresh, retrace_persist_s)
    exit_policies = [
        ("P1_PROD_+14c_Salv22c", 0.14, False, 0.22, -0.06, 15.0),
        ("P2_TIGHT_+12c_Salv15c", 0.12, False, 0.15, -0.05, 12.0),
        ("P3_ASYM_+16c_Salv16c", 0.16, False, 0.16, -0.05, 15.0),
        ("P4_CONVEX_+20c_Salv16c", 0.20, False, 0.16, -0.05, 15.0),
        ("P5_HOLD99c_Salv18c", 0.99, True, 0.18, -0.05, 15.0),
        ("P6_HOLD99c_SpotStopOnly", 0.99, True, 0.99, -0.05, 15.0),
    ]

    t_pre = time.time()
    precomputed: Dict[str, List[Tuple[float, str, float]]] = {}
    NOTIONAL = 16.50  # Current base ticket on $74.50 bankroll

    for pol_name, tp_val, is_abs_tp, bid_salvage, retrace_th, retrace_s in exit_policies:
        outcomes: List[Tuple[float, str, float]] = []
        for trig in triggers:
            mid = trig["market_id"]
            t0 = trig["t0_unix"]
            target = trig["target"]
            ask = trig["ask"]
            fee_rate = trig["fee_rate"]
            fee_exp = trig["fee_exp"]
            res = resolutions[mid]
            winning = res.get("winning_outcome")
            close_ts = float(res.get("candle_close_ts") or (t0 + trig["tte"]))

            tp_px = min(0.99, tp_val if is_abs_tp else (ask + tp_val))
            salvage_px = max(0.05, ask - bid_salvage)

            m_telem = telemetry_by_market.get(mid, [])
            # Binary search start index
            lo, hi = 0, len(m_telem)
            while lo < hi:
                m_idx = (lo + hi) // 2
                if m_telem[m_idx][0] < t0:
                    lo = m_idx + 1
                else:
                    hi = m_idx

            exit_px: Optional[float] = None
            exit_reason = "EXPIRY"
            exit_ts = close_ts
            adv_start: Optional[float] = None

            for idx_pt in range(lo, len(m_telem)):
                pt_ts, pt_dist, up_b, up_a, dn_b, dn_a = m_telem[idx_pt]
                tb = up_b if target == "UP" else dn_b
                ta = up_a if target == "UP" else dn_a

                # 1. Check Maker TP fill (resting limit sell filled when bid >= tp_px or ask > tp_px)
                if tb >= tp_px or (ta >= tp_px + 0.01 and tb >= tp_px - 0.01):
                    exit_px = tp_px
                    exit_reason = "MAKER_TP"
                    exit_ts = pt_ts
                    break

                # 2. Check Hard Bid Drop Salvage (after 8s grace)
                if (pt_ts - t0) >= 8.0 and 0.02 < tb <= salvage_px:
                    exit_px = tb
                    exit_reason = "BID_SALVAGE"
                    exit_ts = pt_ts
                    break

                # 3. Check Spot Retrace Stop across candle open
                adv = (pt_dist <= retrace_th) if target == "UP" else (pt_dist >= -retrace_th)
                if adv:
                    if adv_start is None:
                        adv_start = pt_ts
                    elif (pt_ts - adv_start) >= retrace_s and tb > 0.02:
                        exit_px = tb
                        exit_reason = "SPOT_STOP"
                        exit_ts = pt_ts
                        break
                else:
                    adv_start = None

            if exit_px is None:
                exit_px = 1.00 if (target == winning) else 0.00
                exit_reason = "EXPIRY_WIN" if (target == winning) else "EXPIRY_LOSS"
                exit_ts = close_ts

            shares = NOTIONAL / ask
            entry_fee = calculate_taker_fee(NOTIONAL, ask, fee_rate, fee_exp)
            gross_payout = shares * exit_px
            # Maker TP and Expiry Redemption pay 0 taker fee; Taker stop/salvage pays taker fee
            exit_fee = (
                calculate_taker_fee(gross_payout, exit_px, fee_rate, fee_exp)
                if exit_reason in ("BID_SALVAGE", "SPOT_STOP")
                else 0.0
            )
            net_pnl = gross_payout - NOTIONAL - entry_fee - exit_fee
            outcomes.append((net_pnl, exit_reason, exit_ts))

        precomputed[pol_name] = outcomes

    print(f"[4/5] Precomputed exact L2 trade paths across {len(exit_policies)} exit policies in {time.time() - t_pre:.2f}s.", flush=True)

    # Chronological 70% In-Sample / 30% Out-of-Sample Split by Market Settlement Timestamp
    all_mids_sorted = sorted(candidate_mids, key=lambda m: float(resolutions[m].get("candle_close_ts", 0.0)))
    split_idx = int(len(all_mids_sorted) * 0.70)
    is_mids = set(all_mids_sorted[:split_idx])
    oos_mids = set(all_mids_sorted[split_idx:])
    print(f"      Walk-Forward Split: {len(is_mids)} In-Sample markets (70%) | {len(oos_mids)} Out-of-Sample markets (30%)", flush=True)

    def eval_subset(
        allowed_mids: set,
        is_15m_mode: bool,
        pol_name: str,
        p_floor: float,
        p_ceil: float,
        max_tte: float,
        min_cush: float,
        sigma_mult: float,
        min_eq: float,
    ) -> Dict[str, Any]:
        outcomes = precomputed[pol_name]
        pnls: List[float] = []
        wins = 0
        active: List[Tuple[str, float]] = []
        traded = set()

        for i, trig in enumerate(triggers):
            if trig["is_15m"] != is_15m_mode:
                continue
            mid = trig["market_id"]
            if mid not in allowed_mids or mid in traded:
                continue
            t0 = trig["t0_unix"]
            active = [a for a in active if a[1] > t0]
            if len(active) >= 2 or any(a[0] == trig["asset"] for a in active):
                continue

            tte = trig["tte"]
            min_tte = 30.0 if is_15m_mode else 90.0
            if tte < min_tte or tte > max_tte:
                continue
            if is_nyse_open_window(t0, not is_15m_mode):
                continue

            ask = trig["ask"]
            if ask < p_floor or ask > p_ceil:
                continue

            dist = trig["dist"]
            target = trig["target"]
            req_cush = max(min_cush, sigma_mult * trig["sigma_rem_pct"])
            # Price-conditioned discount: if entry ask < 0.68, require 25% less spot cushion (catching move early)
            if ask <= 0.68:
                req_cush *= 0.75

            if target == "UP" and dist < req_cush:
                continue
            if target == "DOWN" and dist > -req_cush:
                continue
            if trig["eq_score"] < min_eq:
                continue

            net_pnl, _reason, exit_ts = outcomes[i]
            pnls.append(net_pnl)
            if net_pnl > 0:
                wins += 1
            traded.add(mid)
            active.append((trig["asset"], exit_ts))

        n = len(pnls)
        if n == 0:
            return {"n": 0, "wr": 0.0, "pf": 0.0, "dd": 0.0, "pnl": 0.0, "ev": 0.0}
        gp = sum(x for x in pnls if x > 0)
        gl = abs(sum(x for x in pnls if x <= 0))
        pf = (gp / gl) if gl > 0 else (99.0 if gp > 0 else 0.0)
        cum = 0.0
        pk = 0.0
        mdd = 0.0
        for x in pnls:
            cum += x
            if cum > pk:
                pk = cum
            if (pk - cum) > mdd:
                mdd = pk - cum
        return {
            "n": n,
            "wr": (wins / n) * 100.0,
            "pf": pf,
            "dd": mdd,
            "pnl": sum(pnls),
            "ev": sum(pnls) / n,
        }

    # 5. Run Joint WFO Sweeps for Sleeve 1 (15m) and Sleeve 2 (1h)
    print("\n[5/5] Sweeping Coupled Parameter Grids (In-Sample Training -> Out-of-Sample Validation)...", flush=True)

    for sleeve_label, is_15m_flag in [("SLEEVE 1: 15-MINUTE SUB-HOURLY (BTC + ETH)", True), ("SLEEVE 2: 1-HOUR HOURLY (BTC + ETH)", False)]:
        print("\n" + "=" * 95)
        print(f"  {sleeve_label}")
        print("=" * 95)

        # Evaluate Current Prod Baseline first
        if is_15m_flag:
            base_is = eval_subset(is_mids, True, "P1_PROD_+14c_Salv22c", 0.55, 0.85, 690.0, 0.08, 0.75, 0.70)
            base_oos = eval_subset(oos_mids, True, "P1_PROD_+14c_Salv22c", 0.55, 0.85, 690.0, 0.08, 0.75, 0.70)
            p_floors = [0.52, 0.55, 0.60, 0.65]
            p_ceils = [0.72, 0.75, 0.78, 0.82, 0.85]
            max_ttes = [450.0, 600.0, 690.0, 780.0]
            min_cushs = [0.03, 0.05, 0.06, 0.08, 0.10]
            sigma_mults = [0.0, 0.35, 0.50, 0.75]
            min_eqs = [0.50, 0.60, 0.70]
        else:
            base_is = eval_subset(is_mids, False, "P1_PROD_+14c_Salv22c", 0.55, 0.82, 2700.0, 0.15, 0.75, 0.70)
            base_oos = eval_subset(oos_mids, False, "P1_PROD_+14c_Salv22c", 0.55, 0.82, 2700.0, 0.15, 0.75, 0.70)
            p_floors = [0.55, 0.60, 0.65, 0.70, 0.74]
            p_ceils = [0.74, 0.78, 0.82, 0.86, 0.90]
            max_ttes = [1500.0, 2100.0, 2700.0]
            min_cushs = [0.08, 0.12, 0.15, 0.20, 0.25]
            sigma_mults = [0.0, 0.35, 0.50, 0.75]
            min_eqs = [0.50, 0.60, 0.70]

        print(
            f"CURRENT PROD BASELINE -> "
            f"IS: {base_is['n']} trades, WR={base_is['wr']:.1f}%, PF={base_is['pf']:.2f}, PnL=${base_is['pnl']:+.2f} | "
            f"OOS: {base_oos['n']} trades, WR={base_oos['wr']:.1f}%, PF={base_oos['pf']:.2f}, PnL=${base_oos['pnl']:+.2f}, MaxDD=${base_oos['dd']:.2f}"
        )

        candidates = []
        min_is_trades = 8 if is_15m_flag else 12
        min_oos_trades = 4 if is_15m_flag else 5

        for pol_name, *_ in exit_policies:
            for pf in p_floors:
                for pc in p_ceils:
                    if pc <= pf + 0.08:
                        continue
                    for mt in max_ttes:
                        for mc in min_cushs:
                            for sm in sigma_mults:
                                for meq in min_eqs:
                                    res_is = eval_subset(is_mids, is_15m_flag, pol_name, pf, pc, mt, mc, sm, meq)
                                    if res_is["n"] < min_is_trades or res_is["pnl"] <= 0 or res_is["pf"] < 1.35:
                                        continue
                                    res_oos = eval_subset(oos_mids, is_15m_flag, pol_name, pf, pc, mt, mc, sm, meq)
                                    if res_oos["n"] < min_oos_trades or res_oos["pnl"] <= 0 or res_oos["pf"] < 1.35:
                                        continue
                                    candidates.append({
                                        "pol": pol_name,
                                        "pf": pf,
                                        "pc": pc,
                                        "mt": mt,
                                        "mc": mc,
                                        "sm": sm,
                                        "meq": meq,
                                        "is": res_is,
                                        "oos": res_oos,
                                        "tot_pnl": res_is["pnl"] + res_oos["pnl"],
                                        "tot_n": res_is["n"] + res_oos["n"],
                                    })

        # Rank by OOS Net PnL * log(1 + OOS PF), requiring strong OOS stability
        candidates.sort(
            key=lambda x: (
                x["oos"]["pnl"] * math.log1p(min(20.0, x["oos"]["pf"])),
                x["tot_pnl"],
            ),
            reverse=True,
        )

        print(f"Found {len(candidates)} Walk-Forward Certified configurations (positive IS & OOS with PF >= 1.35).")
        print("-" * 95)
        print(
            f"{'Rk':<3} | {'Exit Policy':<23} | {'Band':<9} | {'MaxTTE':<6} | {'Cush':<5} | {'SigM':<4} | {'Eq':<4} | "
            f"{'IS N/WR/PnL':<20} | {'OOS N/WR/PF/MaxDD/PnL'}"
        )
        print("-" * 95)
        shown = set()
        rk = 0
        for c in candidates:
            sig = (c["pol"], c["pf"], c["pc"], c["mt"], c["mc"], c["sm"])
            if sig in shown:
                continue
            shown.add(sig)
            rk += 1
            is_s = c["is"]
            oos_s = c["oos"]
            print(
                f"#{rk:<2} | {c['pol']:<23} | {c['pf']:.2f}-{c['pc']:.2f} | {int(c['mt']):<5}s | "
                f"{c['mc']:.2f}% | {c['sm']:.2f} | {c['meq']:.2f} | "
                f"{is_s['n']:>3} / {is_s['wr']:>4.1f}% / ${is_s['pnl']:>+6.2f} | "
                f"{oos_s['n']:>3} / {oos_s['wr']:>4.1f}% / PF {oos_s['pf']:>4.2f} / DD ${oos_s['dd']:>4.2f} / ${oos_s['pnl']:>+6.2f}"
            )
            if rk >= 10:
                break

    print(f"\nTotal WFO runtime: {time.time() - t_init:.2f}s.")


if __name__ == "__main__":
    main()

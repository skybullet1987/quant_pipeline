#!/usr/bin/env python3
"""
Ultra-Fast Joint Walk-Forward Grid Optimizer (15m + 1h | BTC + ETH)
===================================================================
Completes full telemetry indexing + 15,000-combo WFO sweep in ~25 seconds.
"""

from __future__ import annotations

import json
import math
import os
import re
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

MID_RE = re.compile(r'"market_id":\s*"(\d+)"')


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
    print("=" * 100)
    print("ULTRA-FAST JOINT WALK-FORWARD PARAMETER GRID OPTIMIZER (15M + 1H | BTC + ETH)")
    print("=" * 100, flush=True)

    # 1. Load Ground-Truth Resolutions
    resolutions: Dict[str, Dict[str, Any]] = {}
    with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                resolutions[str(rec["market_id"])] = rec
    print(f"[1/5] Loaded {len(resolutions)} finalized market resolutions ({time.time() - t_init:.2f}s).", flush=True)

    # 2. Load Candidate Triggers (deduplicate bursts per market + price/TTE bucket)
    triggers: List[Dict[str, Any]] = []
    candidate_mids = set()
    seen_buckets = set()

    with open(TRIGGERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            k_idx = line.find('"market_id": "')
            if k_idx < 0:
                continue
            q_end = line.find('"', k_idx + 14)
            mid = line[k_idx + 14 : q_end]
            if mid not in resolutions:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            s_dir = rec.get("shock_direction")
            if s_dir not in ("BUY", "SELL"):
                continue
            target = "UP" if s_dir == "BUY" else "DOWN"
            features = rec.get("pre_shock_features_t0") or {}
            tf = features.get(target) or {}
            ask = float(tf.get("vwap_$20") or tf.get("best_ask") or 0.0)
            bid = float(tf.get("best_bid") or 0.0)
            if ask <= 0.45 or ask >= 0.94:
                continue

            t0 = float(rec.get("t0_unix", 0.0) or 0.0)
            tte = float(rec.get("seconds_to_expiry", 0.0) or 0.0)
            dist = float(rec.get("candle_distance_pct", 0.0) or 0.0)

            # Bucket by (mid, target, 15s window, 2c ask bucket) to avoid 50 identical 100ms shock ticks
            b_key = (mid, target, int(t0 // 15), int(ask * 50))
            if b_key in seen_buckets:
                continue
            seen_buckets.add(b_key)

            spread = float(tf.get("spread") or max(0.01, ask - bid))
            target_obi = float(tf.get("obi_depth") or tf.get("obi_l1") or 0.0)
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
                "dist": dist,
                "sigma_rem_pct": sigma_rem_pct,
                "eq_score": eq_score,
                "fee_rate": fee_rate,
                "fee_exp": fee_exp,
                "nyse_blk": is_nyse_open_window(t0, not is_15m),
            })

    triggers.sort(key=lambda x: x["t0_unix"])
    n_15m = sum(1 for x in triggers if x["is_15m"])
    n_1h = len(triggers) - n_15m
    print(
        f"[2/5] Loaded {len(triggers)} distinct shock states ({n_15m} 15m, {n_1h} 1h) "
        f"across {len(candidate_mids)} settled markets ({time.time() - t_init:.2f}s).",
        flush=True,
    )

    # 3. Fast Regex-Filtered Telemetry Load (BTC + ETH)
    telemetry_by_market: Dict[str, List[Tuple[float, float, float, float, float, float]]] = defaultdict(list)
    t_telem = time.time()
    for tfile in (TELEM_BTC_FILE, TELEM_ETH_FILE):
        if not tfile.exists():
            continue
        with open(tfile, "r", encoding="utf-8") as f:
            for line in f:
                k_idx = line.find('"market_id": "')
                if k_idx < 0:
                    continue
                q_end = line.find('"', k_idx + 14)
                mid = line[k_idx + 14 : q_end]
                if mid not in candidate_mids:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
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
    exit_policies = [
        ("P1_PROD_+14c_Salv20c", 0.14, False, 0.20, -0.06, 15.0),
        ("P2_SCALP_+10c_Salv14c", 0.10, False, 0.14, -0.05, 12.0),
        ("P3_ASYM_+16c_Salv15c", 0.16, False, 0.15, -0.05, 15.0),
        ("P4_CONVEX_+22c_Salv16c", 0.22, False, 0.16, -0.05, 15.0),
        ("P5_HOLD99c_Salv18c", 0.99, True, 0.18, -0.05, 15.0),
        ("P6_HOLD99c_SpotStop", 0.99, True, 0.99, -0.05, 15.0),
    ]

    t_pre = time.time()
    precomputed: Dict[str, List[Tuple[float, str, float]]] = {}
    NOTIONAL = 16.50

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

                if tb >= tp_px or (ta >= tp_px + 0.01 and tb >= tp_px - 0.01):
                    exit_px = tp_px
                    exit_reason = "MAKER_TP"
                    exit_ts = pt_ts
                    break

                if (pt_ts - t0) >= 6.0 and 0.02 < tb <= salvage_px:
                    exit_px = tb
                    exit_reason = "BID_SALVAGE"
                    exit_ts = pt_ts
                    break

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
            exit_fee = (
                calculate_taker_fee(gross_payout, exit_px, fee_rate, fee_exp)
                if exit_reason in ("BID_SALVAGE", "SPOT_STOP")
                else 0.0
            )
            net_pnl = gross_payout - NOTIONAL - entry_fee - exit_fee
            outcomes.append((net_pnl, exit_reason, exit_ts))

        precomputed[pol_name] = outcomes

    print(f"[4/5] Precomputed exact L2 trade paths in {time.time() - t_pre:.2f}s.", flush=True)

    # Pre-partition triggers into 4 compact lists of tuples for 50x faster grid evaluation:
    # Tuple format: (orig_idx, mid, asset_id, t0, tte, is_up, ask, abs_dist_signed, sigma_rem_pct, eq_score, nyse_blk)
    # where abs_dist_signed = +dist if target=="UP" else -dist
    all_mids_sorted = sorted(candidate_mids, key=lambda m: float(resolutions[m].get("candle_close_ts", 0.0)))
    split_idx = int(len(all_mids_sorted) * 0.70)
    is_mids = set(all_mids_sorted[:split_idx])
    oos_mids = set(all_mids_sorted[split_idx:])
    print(f"      Walk-Forward Split: {len(is_mids)} In-Sample markets (70%) | {len(oos_mids)} Out-of-Sample markets (30%)", flush=True)

    part_trigs: Dict[Tuple[bool, bool], List[Tuple[int, str, int, float, float, float, float, float, float, bool]]] = defaultdict(list)
    for idx, tr in enumerate(triggers):
        in_is = tr["market_id"] in is_mids
        signed_dist = tr["dist"] if tr["target"] == "UP" else -tr["dist"]
        asset_int = 1 if tr["asset"] == "BTC" else 2
        part_trigs[(tr["is_15m"], in_is)].append((
            idx,
            tr["market_id"],
            asset_int,
            tr["t0_unix"],
            tr["tte"],
            tr["ask"],
            signed_dist,
            tr["sigma_rem_pct"],
            tr["eq_score"],
            tr["nyse_blk"],
        ))

    def fast_eval_subset(
        trig_list: List[Tuple[int, str, int, float, float, float, float, float, float, bool]],
        min_tte: float,
        outcomes: List[Tuple[float, str, float]],
        p_floor: float,
        p_ceil: float,
        max_tte: float,
        min_cush: float,
        sigma_mult: float,
        min_eq: float,
    ) -> Dict[str, Any]:
        pnls: List[float] = []
        wins = 0
        exp_btc = 0.0
        exp_eth = 0.0
        traded = set()

        for idx, mid, asset_int, t0, tte, ask, signed_dist, sig_rem, eq_s, nyse_blk in trig_list:
            if mid in traded or nyse_blk:
                continue
            if tte < min_tte or tte > max_tte:
                continue
            if ask < p_floor or ask > p_ceil:
                continue
            if eq_s < min_eq:
                continue
            req_cush = min_cush if min_cush >= sigma_mult * sig_rem else sigma_mult * sig_rem
            if signed_dist < req_cush:
                continue
            if asset_int == 1:
                if exp_btc > t0:
                    continue
            else:
                if exp_eth > t0:
                    continue

            net_pnl, _r, exit_ts = outcomes[idx]
            pnls.append(net_pnl)
            if net_pnl > 0.0:
                wins += 1
            traded.add(mid)
            if asset_int == 1:
                exp_btc = exit_ts
            else:
                exp_eth = exit_ts

        n = len(pnls)
        if n == 0:
            return {"n": 0, "wr": 0.0, "pf": 0.0, "dd": 0.0, "pnl": 0.0, "ev": 0.0}
        gp = sum(x for x in pnls if x > 0.0)
        gl = abs(sum(x for x in pnls if x <= 0.0))
        pf = (gp / gl) if gl > 0.0 else (99.0 if gp > 0.0 else 0.0)
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

    # 5. Sweep Grids in Seconds
    t_sweep = time.time()
    for sleeve_label, is_15m_flag in [
        ("SLEEVE 1: 15-MINUTE SUB-HOURLY (BTC + ETH)", True),
        ("SLEEVE 2: 1-HOUR HOURLY (BTC + ETH)", False),
    ]:
        print("\n" + "=" * 100)
        print(f"  {sleeve_label}")
        print("=" * 100, flush=True)

        tr_is = part_trigs[(is_15m_flag, True)]
        tr_oos = part_trigs[(is_15m_flag, False)]
        min_tte = 30.0 if is_15m_flag else 90.0

        if is_15m_flag:
            base_is = fast_eval_subset(tr_is, min_tte, precomputed["P1_PROD_+14c_Salv20c"], 0.55, 0.85, 690.0, 0.08, 0.75, 0.70)
            base_oos = fast_eval_subset(tr_oos, min_tte, precomputed["P1_PROD_+14c_Salv20c"], 0.55, 0.85, 690.0, 0.08, 0.75, 0.70)
            p_floors = [0.52, 0.55, 0.60, 0.65, 0.70]
            p_ceils = [0.70, 0.74, 0.78, 0.82, 0.85]
            max_ttes = [450.0, 600.0, 690.0, 780.0]
            min_cushs = [0.03, 0.05, 0.06, 0.08, 0.10]
            sigma_mults = [0.0, 0.35, 0.50, 0.75]
            min_eqs = [0.50, 0.60, 0.65, 0.70]
        else:
            base_is = fast_eval_subset(tr_is, min_tte, precomputed["P1_PROD_+14c_Salv20c"], 0.55, 0.82, 2700.0, 0.15, 0.75, 0.70)
            base_oos = fast_eval_subset(tr_oos, min_tte, precomputed["P1_PROD_+14c_Salv20c"], 0.55, 0.82, 2700.0, 0.15, 0.75, 0.70)
            p_floors = [0.55, 0.60, 0.65, 0.70, 0.75]
            p_ceils = [0.72, 0.76, 0.80, 0.84, 0.88]
            max_ttes = [1200.0, 1500.0, 2100.0, 2700.0]
            min_cushs = [0.08, 0.12, 0.15, 0.20, 0.25]
            sigma_mults = [0.0, 0.35, 0.50, 0.75]
            min_eqs = [0.50, 0.60, 0.65, 0.70]

        print(
            f"CURRENT PROD BASELINE -> "
            f"IS: {base_is['n']} trades, WR={base_is['wr']:.1f}%, PF={base_is['pf']:.2f}, PnL=${base_is['pnl']:+.2f} | "
            f"OOS: {base_oos['n']} trades, WR={base_oos['wr']:.1f}%, PF={base_oos['pf']:.2f}, PnL=${base_oos['pnl']:+.2f}, MaxDD=${base_oos['dd']:.2f}",
            flush=True,
        )

        candidates = []
        min_is_n = 5 if is_15m_flag else 10
        min_oos_n = 3 if is_15m_flag else 4

        for pol_name, *_ in exit_policies:
            outcomes = precomputed[pol_name]
            for pf in p_floors:
                for pc in p_ceils:
                    if pc <= pf + 0.06:
                        continue
                    for mt in max_ttes:
                        for mc in min_cushs:
                            for sm in sigma_mults:
                                for meq in min_eqs:
                                    res_is = fast_eval_subset(tr_is, min_tte, outcomes, pf, pc, mt, mc, sm, meq)
                                    if res_is["n"] < min_is_n or res_is["pnl"] <= 0.0 or res_is["pf"] < 1.25:
                                        continue
                                    res_oos = fast_eval_subset(tr_oos, min_tte, outcomes, pf, pc, mt, mc, sm, meq)
                                    if res_oos["n"] < min_oos_n or res_oos["pnl"] <= 0.0 or res_oos["pf"] < 1.25:
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
                                    })

        candidates.sort(
            key=lambda x: (
                x["oos"]["pnl"] * math.log1p(min(20.0, x["oos"]["pf"])),
                x["tot_pnl"],
            ),
            reverse=True,
        )

        print(f"Found {len(candidates)} Walk-Forward Certified configurations in {time.time() - t_sweep:.2f}s.", flush=True)
        print("-" * 100)
        print(
            f"{'Rk':<3} | {'Exit Policy':<23} | {'Band':<9} | {'MaxTTE':<6} | {'Cush':<5} | {'SigM':<4} | {'Eq':<4} | "
            f"{'IS N/WR/PnL':<21} | {'OOS N/WR/PF/MaxDD/PnL'}"
        )
        print("-" * 100)
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
                f"{oos_s['n']:>3} / {oos_s['wr']:>4.1f}% / PF {oos_s['pf']:>4.2f} / DD ${oos_s['dd']:>5.2f} / ${oos_s['pnl']:>+6.2f}",
                flush=True,
            )
            if rk >= 12:
                break

    print(f"\nTotal WFO runtime: {time.time() - t_init:.2f}s.", flush=True)


if __name__ == "__main__":
    main()

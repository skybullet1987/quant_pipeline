#!/usr/bin/env python3
"""
Backtest 2D Cushion x Ask-Price Convexity Matrix & Curve Variants on 15m Subhourly (Sleeve 1) Markets,
including both the historical dataset and today's live 15m trades.
"""

import json
import math
from collections import defaultdict
from pathlib import Path
from backtest_hard_bid_drop_variants import (
    RESOLUTIONS_FILE,
    TRIGGERS_FILE,
    STATE_FILE,
    calculate_taker_fee,
    simulate_position_path,
)


def max_ask_for_curve(curve_name: str, cush_pct: float, tte: float, asset: str) -> float:
    sigma_c = 0.0050 if asset == "BTC" else 0.0068
    sigma_rem_pct = sigma_c * 100.0 * math.sqrt(max(tte, 30.0) / 900.0)
    z_strike = cush_pct / max(sigma_rem_pct, 1e-6)

    if curve_name == "C0_FLAT_078 (Current)":
        return 0.78 if cush_pct >= 0.06 else 0.0
    elif curve_name == "C1_STEPPED (0.06->.68, 0.09->.74, 0.13->.78)":
        if cush_pct < 0.06:
            return 0.0
        elif cush_pct < 0.09:
            return 0.68
        elif cush_pct < 0.13:
            return 0.74
        else:
            return 0.78
    elif curve_name == "C2_TIGHT_LOW (0.06->.65, 0.08->.72, 0.12->.78)":
        if cush_pct < 0.06:
            return 0.0
        elif cush_pct < 0.08:
            return 0.65
        elif cush_pct < 0.12:
            return 0.72
        else:
            return 0.78
    elif curve_name == "C3_LINEAR (min(0.78, 0.56 + 2.0*cush))":
        if cush_pct < 0.06:
            return 0.0
        return round(min(0.78, 0.56 + 2.0 * cush_pct), 4)
    elif curve_name == "C4_Z_STRIKE (z<0.22->.68, z<0.35->.74, else .78)":
        if cush_pct < 0.06:
            return 0.0
        if z_strike < 0.22:
            return 0.68
        elif z_strike < 0.35:
            return 0.74
        else:
            return 0.78
    elif curve_name == "C5_MIN_CUSH_008_CAP_078":
        return 0.78 if cush_pct >= 0.08 else 0.0
    else:
        raise ValueError(curve_name)


def main():
    resolutions = {}
    with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                resolutions[str(rec["market_id"])] = rec

    state = json.load(open(STATE_FILE, "r", encoding="utf-8"))
    # Include all closed positions from state that may not yet be in finalized_market_resolutions.jsonl
    for p in state.get("closed_positions", []):
        mid = str(p.get("market_id"))
        if mid not in resolutions and p.get("resolved_winning_outcome"):
            resolutions[mid] = {"market_id": mid, "winning_outcome": p["resolved_winning_outcome"]}

    # Also check Gamma for 6022563 / 6019058 if needed
    known_15m = {
        "6012995": "UP",
        "6013539": "DOWN",
        "6014317": "UP",
        "6016117": "DOWN",
        "6017333": "DOWN",
        "6019058": "DOWN",
        "6022563": "DOWN",
    }
    for m_id, out in known_15m.items():
        if m_id not in resolutions:
            resolutions[m_id] = {"market_id": m_id, "winning_outcome": out}

    triggers_15m = []
    trigger_telem = defaultdict(list)
    seen_buckets = set()
    needle = '"market_id": "'

    with open(TRIGGERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            k_idx = line.find(needle)
            if k_idx < 0:
                continue
            mid = line[k_idx + len(needle) : line.find('"', k_idx + len(needle))]
            if mid not in resolutions:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue

            t0 = float(rec.get("t0_unix", 0.0) or 0.0)
            dist = float(rec.get("candle_distance_pct", 0.0) or 0.0)
            features = rec.get("pre_shock_features_t0") or {}
            up_tf = features.get("UP") or {}
            dn_tf = features.get("DOWN") or {}
            up_b = float(up_tf.get("best_bid") or 0.0)
            up_a = float(up_tf.get("best_ask") or 0.0)
            dn_b = float(dn_tf.get("best_bid") or 0.0)
            dn_a = float(dn_tf.get("best_ask") or 0.0)
            if t0 > 0 and (up_b > 0 or dn_b > 0):
                trigger_telem[mid].append((t0, dist, up_b, up_a, dn_b, dn_a))

            s_dir = rec.get("shock_direction")
            if s_dir not in ("BUY", "SELL"):
                continue
            shock_ofi = abs(float(rec.get("shock_ofi", 0.0) or 0.0))
            if shock_ofi < 0.45:
                continue
            target = "UP" if s_dir == "BUY" else "DOWN"
            tf = features.get(target) or {}
            ask = float(tf.get("vwap_$20") or tf.get("best_ask") or 0.0)
            bid = float(tf.get("best_bid") or 0.0)
            if ask < 0.55 or ask > 0.78:
                continue
            tte = float(rec.get("seconds_to_expiry", 0.0) or 0.0)
            signed_dist = dist if target == "UP" else -dist

            horizon = str(rec.get("horizon") or resolutions[mid].get("horizon") or "1h").lower()
            is_15m = "15m" in horizon or (0 < tte <= 900.0 and ":" in str(rec.get("title", "")))
            if not is_15m:
                continue
            if not (30.0 <= tte <= 600.0 and signed_dist >= 0.06):
                continue

            b_key = (mid, target)
            if b_key in seen_buckets:
                continue
            seen_buckets.add(b_key)

            fee_meta = rec.get("fee_metadata") or {}
            fee_rate = float(fee_meta.get("fee_rate_market", 0.07) or 0.07)
            fee_exp = float(fee_meta.get("fee_exponent", 1.0) or 1.0)

            triggers_15m.append({
                "market_id": mid,
                "title": rec.get("title", ""),
                "asset": str(rec.get("asset", "BTC")).upper(),
                "t0_unix": t0,
                "tte": tte,
                "expiry_ts": float(rec.get("expiry_ts") or (t0 + tte)),
                "target": target,
                "ask": ask,
                "bid": bid,
                "signed_dist": signed_dist,
                "fee_rate": fee_rate,
                "fee_exp": fee_exp,
            })

    for mid in trigger_telem:
        trigger_telem[mid].sort(key=lambda x: x[0])

    # Simulate each 15m trade under V4 stop (current deployed 15m stop)
    for tr in triggers_15m:
        mid = tr["market_id"]
        win_out = resolutions[mid].get("winning_outcome")
        notional = 20.0
        shares = notional / tr["ask"]
        efee = calculate_taker_fee(notional, tr["ask"], tr["fee_rate"], tr["fee_exp"])
        pnl, won, rsn, ex_px = simulate_position_path(
            trigger_telem[mid], tr["t0_unix"], tr["expiry_ts"], tr["target"],
            tr["ask"], tr["signed_dist"], True, shares, notional, efee,
            tr["fee_rate"], tr["fee_exp"], win_out, "V4_STRICT_WRONGSIDE_8BPS_12S",
        )
        tr["pnl"] = pnl
        tr["won"] = won
        tr["rsn"] = rsn
        tr["exp_win"] = (tr["target"] == win_out)

    print("=" * 105)
    print(f"PART 1: 2D CUSHION x ASK-PRICE MATRIX ON 15M SUBHOURLY MARKETS (n={len(triggers_15m)} trades)")
    print("=" * 105)
    cush_bands = [
        ("0.06% - 0.08% (Thin)", 0.06, 0.08),
        ("0.08% - 0.11% (Moderate)", 0.08, 0.11),
        ("0.11% - 0.15% (Solid)", 0.11, 0.15),
        (">= 0.15% (Strong)", 0.15, 99.0),
    ]
    ask_bands = [
        ("$0.55 - $0.68", 0.55, 0.68),
        ("$0.68 - $0.73", 0.68, 0.73),
        ("$0.73 - $0.78", 0.73, 0.781),
    ]
    for c_label, c_lo, c_hi in cush_bands:
        print(f"\n--- Cushion Band: {c_label} ---")
        for a_label, a_lo, a_hi in ask_bands:
            cell = [t for t in triggers_15m if c_lo <= t["signed_dist"] < c_hi and a_lo <= t["ask"] < a_hi]
            n = len(cell)
            if not n:
                print(f"  Ask {a_label:15s}: n=  0")
                continue
            w = sum(1 for t in cell if t["won"])
            tot = sum(t["pnl"] for t in cell)
            losses = [t["pnl"] for t in cell if not t["won"]]
            print(
                f"  Ask {a_label:15s}: n={n:3d} | WR={100*w/n:5.1f}% | TotalPnL=${tot:+7.2f} | "
                f"Avg=${tot/n:+5.2f}/tr | Losses={len(losses)}"
            )

    print("\n" + "=" * 105)
    print("PART 2: 15M CONVEXITY CURVE COMPARISON (HISTORICAL + TODAY'S LIVE 15M TRADES)")
    print("=" * 105)
    curves = [
        "C0_FLAT_078 (Current)",
        "C1_STEPPED (0.06->.68, 0.09->.74, 0.13->.78)",
        "C2_TIGHT_LOW (0.06->.65, 0.08->.72, 0.12->.78)",
        "C3_LINEAR (min(0.78, 0.56 + 2.0*cush))",
        "C4_Z_STRIKE (z<0.22->.68, z<0.35->.74, else .78)",
        "C5_MIN_CUSH_008_CAP_078",
    ]
    for cname in curves:
        sub = [
            t for t in triggers_15m
            if t["ask"] <= max_ask_for_curve(cname, t["signed_dist"], t["tte"], t["asset"])
        ]
        n = len(sub)
        w = sum(1 for t in sub if t["won"])
        l = n - w
        tot = sum(t["pnl"] for t in sub)
        gross_win = sum(t["pnl"] for t in sub if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in sub if t["pnl"] < 0))
        pf = gross_win / max(0.01, gross_loss)
        print(
            f"  {cname:48s}: n={n:3d} ({w}W/{l}L) | WR={100*w/max(1,n):5.1f}% | "
            f"TotalPnL=${tot:+7.2f} | Avg=${tot/max(1,n):+5.2f}/tr | PF={pf:5.2f}x"
        )

    print("\n--- Effect on Today's 7 Live Post-Fix 15m Trades (including Trade #9 6022563) ---")
    live_15m = [p for p in state.get("closed_positions", [])[-9:] if p.get("sleeve") == "SLEEVE_1_SUBHOURLY_15M"]
    for cname in curves:
        kept_pnl = 0.0
        kept_w = 0
        kept_n = 0
        blocked = []
        for p in live_15m:
            open_sp = float(p.get("candle_open_spot", 0.0) or 0.0)
            entry_sp = float(p.get("entry_spot_ref", 0.0) or 0.0)
            cush = abs((entry_sp - open_sp) / open_sp) * 100.0 if open_sp > 0 else 0.0
            tte = float(p.get("entry_tte", 300.0) or 300.0)
            asset = str(p.get("asset", "ETH"))
            px = float(p.get("entry_price", 0.70))
            pnl = float(p.get("net_pnl_usd", 0.0) or 0.0)
            cap = max_ask_for_curve(cname, cush, tte, asset)
            if px <= cap + 1e-4:
                kept_n += 1
                kept_pnl += pnl
                if pnl > 0:
                    kept_w += 1
            else:
                blocked.append(f"{p.get('market_id')}(cush={cush:.3f}%,px=${px:.3f},pnl=${pnl:+.2f})")
        print(
            f"  {cname:48s}: Kept={kept_n}/{len(live_15m)} ({kept_w}W) | "
            f"LiveNetPnL=${kept_pnl:+6.2f} | Blocked={blocked}"
        )


if __name__ == "__main__":
    main()

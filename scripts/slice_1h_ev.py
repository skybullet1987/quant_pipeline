#!/usr/bin/env python3
"""
Grid slice on the 271 historical 1-hour (Sleeve 2) trades to find the exact
(TTE window, min_cushion_pct, max_ask) regime that turns 1-hour trades strictly +EV.
"""

import json
from collections import defaultdict
from pathlib import Path
from backtest_hard_bid_drop_variants import (
    RESOLUTIONS_FILE,
    TRIGGERS_FILE,
    TELEM_BTC_FILE,
    TELEM_ETH_FILE,
    calculate_taker_fee,
    simulate_position_path,
)


def main():
    resolutions = {}
    with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                resolutions[str(rec["market_id"])] = rec

    triggers_1h = []
    candidate_mids = set()
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
            s_dir = rec.get("shock_direction")
            if s_dir not in ("BUY", "SELL"):
                continue
            shock_ofi = abs(float(rec.get("shock_ofi", 0.0) or 0.0))
            if shock_ofi < 0.45:
                continue
            target = "UP" if s_dir == "BUY" else "DOWN"
            features = rec.get("pre_shock_features_t0") or {}
            tf = features.get(target) or {}
            ask = float(tf.get("vwap_$20") or tf.get("best_ask") or 0.0)
            bid = float(tf.get("best_bid") or 0.0)
            if ask < 0.55 or ask > 0.84:
                continue
            t0 = float(rec.get("t0_unix", 0.0) or 0.0)
            tte = float(rec.get("seconds_to_expiry", 0.0) or 0.0)
            dist = float(rec.get("candle_distance_pct", 0.0) or 0.0)
            signed_dist = dist if target == "UP" else -dist

            horizon = str(rec.get("horizon") or resolutions[mid].get("horizon") or "1h").lower()
            is_15m = "15m" in horizon or (0 < tte <= 900.0 and ":" in str(rec.get("title", "")))
            if is_15m:
                continue
            if not (30.0 <= tte <= 2400.0 and signed_dist >= 0.08):
                continue

            b_key = (mid, target, int(tte // 300))
            if b_key in seen_buckets:
                continue
            seen_buckets.add(b_key)

            fee_meta = rec.get("fee_metadata") or {}
            fee_rate = float(fee_meta.get("fee_rate_market", 0.07) or 0.07)
            fee_exp = float(fee_meta.get("fee_exponent", 1.0) or 1.0)

            candidate_mids.add(mid)
            triggers_1h.append({
                "market_id": mid,
                "asset": str(rec.get("asset", "BTC")).upper(),
                "t0_unix": t0,
                "tte": tte,
                "expiry_ts": float(rec.get("expiry_ts") or (t0 + tte)),
                "target": target,
                "ask": ask,
                "bid": bid,
                "signed_dist": signed_dist,
                "shock_ofi": shock_ofi,
                "z_val": abs(float(rec.get("z_val") or rec.get("z_score") or 0.0)),
                "fee_rate": fee_rate,
                "fee_exp": fee_exp,
            })

    telemetry_by_market = defaultdict(list)
    for tfile in (TELEM_BTC_FILE, TELEM_ETH_FILE):
        if not tfile.exists():
            continue
        with open(tfile, "r", encoding="utf-8") as f:
            for line in f:
                k_idx = line.find(needle)
                if k_idx < 0:
                    continue
                mid = line[k_idx + len(needle) : line.find('"', k_idx + len(needle))]
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

    # Pre-simulate each 1h candidate under V2_STRICT_WRONGSIDE_4_5BPS_6S and V5_3ZONE_SALVAGE_ONLY
    for tr in triggers_1h:
        mid = tr["market_id"]
        win_out = resolutions[mid].get("winning_outcome")
        notional = 20.0
        shares = notional / tr["ask"]
        efee = calculate_taker_fee(notional, tr["ask"], tr["fee_rate"], tr["fee_exp"])
        pnl_v2, won_v2, _, _ = simulate_position_path(
            telemetry_by_market[mid], tr["t0_unix"], tr["expiry_ts"], tr["target"],
            tr["ask"], tr["signed_dist"], False, shares, notional, efee,
            tr["fee_rate"], tr["fee_exp"], win_out, "V2_STRICT_WRONGSIDE_4_5BPS_6S",
        )
        pnl_v5, won_v5, _, _ = simulate_position_path(
            telemetry_by_market[mid], tr["t0_unix"], tr["expiry_ts"], tr["target"],
            tr["ask"], tr["signed_dist"], False, shares, notional, efee,
            tr["fee_rate"], tr["fee_exp"], win_out, "V5_3ZONE_SALVAGE_ONLY",
        )
        tr["pnl_v2"] = pnl_v2
        tr["won_v2"] = won_v2
        tr["pnl_v5"] = pnl_v5
        tr["won_v5"] = won_v5
        tr["exp_win"] = (tr["target"] == win_out)

    print("=" * 105)
    print(f"1-HOUR (SLEEVE 2) BREAKDOWN BY TTE BAND x CUSHION x PRICE BAND (Total candidate pool={len(triggers_1h)})")
    print("=" * 105)

    for tte_name, tte_lo, tte_hi in [
        ("Late Sniper [30s, 600s]", 30.0, 600.0),
        ("Late-Mid [30s, 900s]", 30.0, 900.0),
        ("Mid-Hour [900s, 1800s]", 900.0, 1800.0),
        ("Early-Mid [1200s, 2100s]", 1200.0, 2100.0),
        ("All 1h [30s, 2100s]", 30.0, 2100.0),
    ]:
        print(f"\n--- TTE Window: {tte_name} ---")
        for min_cush in [0.08, 0.12, 0.15, 0.18, 0.22, 0.25, 0.30]:
            for max_ask in [0.72, 0.75, 0.78, 0.82]:
                seen_m = set()
                sub = []
                for tr in triggers_1h:
                    if tr["market_id"] in seen_m:
                        continue
                    if tte_lo <= tr["tte"] <= tte_hi and tr["signed_dist"] >= min_cush and 0.55 <= tr["ask"] <= max_ask:
                        seen_m.add(tr["market_id"])
                        sub.append(tr)
                n = len(sub)
                if n < 8:
                    continue
                tot_v2 = sum(t["pnl_v2"] for t in sub)
                wr_v2 = 100.0 * sum(1 for t in sub if t["won_v2"]) / n
                tot_v5 = sum(t["pnl_v5"] for t in sub)
                wr_v5 = 100.0 * sum(1 for t in sub if t["won_v5"]) / n
                ewr = 100.0 * sum(1 for t in sub if t["exp_win"]) / n
                if tot_v2 > 0 or tot_v5 > 0 or min_cush in (0.10, 0.18, 0.25):
                    print(
                        f"  cush>={min_cush:.2f}% | ask<={max_ask:.2f} | n={n:3d} | ExpWR={ewr:5.1f}% | "
                        f"V2: WR={wr_v2:5.1f}% PnL=${tot_v2:+7.2f} (${tot_v2/n:+5.2f}/tr) | "
                        f"V5: WR={wr_v5:5.1f}% PnL=${tot_v5:+7.2f} (${tot_v5/n:+5.2f}/tr)"
                    )


if __name__ == "__main__":
    main()

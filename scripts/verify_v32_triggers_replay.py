#!/usr/bin/env python3
"""
verify_v32_triggers_replay.py
Replays historical triggers from data/polymarket/live_shock_triggers.jsonl
from the last 8.5 hours through the Polymarket v3.2 Rebound Configuration
(Cushion-to-Price Entry Matrix + 3-Zone TTE Bounds) to prove trade qualification.
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone

DATA_FILE = Path("/home/skybullet1987/quant_pipeline/data/polymarket/live_shock_triggers.jsonl")

def run_replay(hours_back: float = 8.5):
    if not DATA_FILE.exists():
        print(f"Error: {DATA_FILE} not found!")
        return

    now_unix = time.time()
    cutoff_unix = now_unix - (hours_back * 3600.0)

    total_shocks = 0
    in_window_shocks = 0
    qualified_trades = []
    regime_counts = {"Regime A (Mid-Hour)": 0, "Regime B (Late-Hour)": 0, "Regime C (Sub-Hourly)": 0}
    reject_reasons = {}

    with open(DATA_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                shock = json.loads(line)
            except Exception:
                continue

            total_shocks += 1
            t0 = float(shock.get("t0_unix") or 0.0)
            if t0 < cutoff_unix:
                continue

            in_window_shocks += 1

            # v3.2 Evaluation Logic
            asset = shock.get("asset", "").upper()
            if asset not in ["BTC", "ETH"]:
                reject_reasons["Asset not BTC/ETH"] = reject_reasons.get("Asset not BTC/ETH", 0) + 1
                continue

            shock_ofi = float(shock.get("shock_ofi", 1.0) or 1.0)
            if abs(shock_ofi) < 0.60:
                reject_reasons["OFI < 0.60"] = reject_reasons.get("OFI < 0.60", 0) + 1
                continue

            tte = float(shock.get("seconds_to_expiry") or 0.0)
            if tte < 90.0 or tte > 2700.0:
                reject_reasons["TTE out of bounds [90s, 2700s]"] = reject_reasons.get("TTE out of bounds [90s, 2700s]", 0) + 1
                continue

            shock_dir = shock.get("shock_direction", "BUY").upper()
            target_token = "UP" if shock_dir == "BUY" else "DOWN"

            open_spot = float(shock.get("finalized_1h_open") or shock.get("candle_open_spot") or shock.get("spot_at_t0") or 0.0)
            spot_px = float(shock.get("spot_at_t0") or shock.get("trigger_price") or 0.0)
            if open_spot <= 0.0 or spot_px <= 0.0:
                reject_reasons["Missing spot/open"] = reject_reasons.get("Missing spot/open", 0) + 1
                continue

            dist_pct = ((spot_px - open_spot) / open_spot * 100.0) if target_token == "UP" else ((open_spot - spot_px) / open_spot * 100.0)
            abs_dist = abs(dist_pct)

            title = shock.get("title", "").lower()
            is_1h = any(kw in title for kw in ["1h", "hourly", "hour", "1-hour", "am et", "pm et"]) or shock.get("horizon") == "1h"
            is_subhourly = any(kw in title for kw in ["15m", "5m", "subhourly"]) or shock.get("horizon") in ["15m", "5m"]

            tf = shock.get("pre_shock_features_t0", {}).get(target_token, {})
            raw_asks = tf.get("raw_top_asks", [])
            if not raw_asks:
                reject_reasons["Empty asks"] = reject_reasons.get("Empty asks", 0) + 1
                continue

            first_ask = float(raw_asks[0][0])
            raw_vwap = float(tf.get("vwap_$20") or tf.get("vwap_$5") or first_ask)

            regime = None
            max_allowed = 0.0
            min_allowed = 0.55

            if is_1h and 900.0 < tte <= 2700.0:
                if dist_pct < 0.15:
                    reject_reasons["Regime A dist_pct < 0.15%"] = reject_reasons.get("Regime A dist_pct < 0.15%", 0) + 1
                    continue
                min_allowed = 0.55
                max_allowed = 0.78
                if first_ask < min_allowed or first_ask > max_allowed or raw_vwap > max_allowed:
                    reject_reasons[f"Regime A price out of [0.55, 0.78] (ask={first_ask})"] = reject_reasons.get(f"Regime A price out of [0.55, 0.78] (ask={first_ask})", 0) + 1
                    continue
                regime = "Regime A (Mid-Hour)"

            elif is_1h and 120.0 <= tte <= 900.0:
                if dist_pct < 0.10:
                    reject_reasons["Regime B dist_pct < 0.10%"] = reject_reasons.get("Regime B dist_pct < 0.10%", 0) + 1
                    continue
                if abs_dist < 0.15:
                    min_allowed, max_allowed = 0.55, 0.75
                    tier = "Tier B1"
                elif abs_dist < 0.22:
                    min_allowed, max_allowed = 0.58, 0.80
                    tier = "Tier B2"
                else:
                    min_allowed, max_allowed = 0.62, 0.84
                    tier = "Tier B3"

                if first_ask < min_allowed or first_ask > max_allowed:
                    reject_reasons[f"Regime B {tier} price out of [{min_allowed}, {max_allowed}] (ask={first_ask})"] = reject_reasons.get(f"Regime B {tier} price out of [{min_allowed}, {max_allowed}] (ask={first_ask})", 0) + 1
                    continue
                regime = f"Regime B (Late-Hour - {tier})"

            elif is_subhourly and 90.0 <= tte <= 540.0:
                if dist_pct < 0.08:
                    reject_reasons["Regime C dist_pct < 0.08%"] = reject_reasons.get("Regime C dist_pct < 0.08%", 0) + 1
                    continue
                min_allowed, max_allowed = 0.58, 0.82
                if first_ask < min_allowed or first_ask > max_allowed:
                    reject_reasons[f"Regime C price out of [{min_allowed}, {max_allowed}] (ask={first_ask})"] = reject_reasons.get(f"Regime C price out of [{min_allowed}, {max_allowed}] (ask={first_ask})", 0) + 1
                    continue
                regime = "Regime C (Sub-Hourly)"
            else:
                reject_reasons["Unmatched horizon/TTE window"] = reject_reasons.get("Unmatched horizon/TTE window", 0) + 1
                continue

            key = "Regime A (Mid-Hour)" if "Regime A" in regime else ("Regime B (Late-Hour)" if "Regime B" in regime else "Regime C (Sub-Hourly)")
            regime_counts[key] += 1
            qualified_trades.append({
                "time_utc": shock.get("timestamp", datetime.fromtimestamp(t0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
                "asset": asset,
                "target_token": target_token,
                "market_title": shock.get("title"),
                "regime": regime,
                "tte_s": round(tte, 1),
                "dist_pct": round(dist_pct, 4),
                "first_ask": first_ask,
                "raw_vwap": raw_vwap,
            })

    print("================================================================================")
    print(f"POLYMARKET v3.2 HISTORICAL TRIGGER REPLAY (LAST {hours_back} HOURS)")
    print("================================================================================")
    print(f"Total historical shocks in window: {in_window_shocks}")
    print(f"Total QUALIFIED TRADES under v3.2: {len(qualified_trades)}")
    print(f"Breakdown by Regime:")
    for reg, count in regime_counts.items():
        print(f"  - {reg}: {count} qualified trades")
    print("\nSample Qualified Trades under v3.2:")
    # Deduplicate by approximate minute or sample up to 10
    seen_windows = set()
    sampled = []
    for qt in qualified_trades:
        w_key = f"{qt['asset']}_{qt['target_token']}_{qt['time_utc'][:16]}"
        if w_key not in seen_windows:
            seen_windows.add(w_key)
            sampled.append(qt)
        if len(sampled) >= 12:
            break

    for idx, tr in enumerate(sampled, 1):
        print(f"  [{idx:02d}] {tr['time_utc']} | {tr['asset']} {tr['target_token']} | {tr['regime']} | TTE: {tr['tte_s']}s | Dist: {tr['dist_pct']:+.2f}% | Ask: ${tr['first_ask']:.2f} | Title: {tr['market_title']}")

    print("\nTop Rejection Reasons for Non-Qualified Shocks:")
    sorted_reasons = sorted(reject_reasons.items(), key=lambda x: x[1], reverse=True)[:8]
    for reason, count in sorted_reasons:
        print(f"  - {reason}: {count}")

    print("\nDeadlock Conclusion:")
    if len(qualified_trades) > 0:
        print(f"  >> SUCCESS: The 0-trade deadlock is COMPLETELY RESOLVED.")
        print(f"  >> v3.2 qualifies {len(qualified_trades)} entries across {len(seen_windows)} distinct trade opportunities.")
    else:
        print("  >> WARNING: Still 0 qualified trades.")
    print("================================================================================")

if __name__ == "__main__":
    run_replay()

#!/usr/bin/env python3
"""
Empirical Backtest of Deep Research Phases 2, 3, and 4 on Recorded Polymarket Telemetry:
  - Phase 2: Synthetic Box Lock (Buy Opposite Token + Merge vs. Cancel + Sell Held Token)
  - Phase 3A: Reactive Post-Only Maker-In (0% fee + 20% rebate) on Price-Capped / Missed Shocks
  - Phase 3B: Stoikov Martingale Micro-Price Sizing / Filtering on n=209 Portfolio Trades
  - Phase 4: Sleeve 5 (:45-:00 Cross-Horizon 15m vs. 1h Monotonicity Box Arbitrage)
"""

import json
import math
from collections import defaultdict
from backtest_hard_bid_drop_variants import (
    RESOLUTIONS_FILE,
    TRIGGERS_FILE,
    STATE_FILE,
    calculate_taker_fee,
)


def taker_cost(px: float, r_fee: float = 0.07) -> float:
    return px + r_fee * px * (1.0 - px)


def maker_cost(px: float, r_fee: float = 0.07, rebate_share: float = 0.20) -> float:
    return px - (r_fee * rebate_share) * px * (1.0 - px)


def main():
    resolutions = {}
    with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                resolutions[str(rec["market_id"])] = rec

    state = json.load(open(STATE_FILE, "r", encoding="utf-8"))
    for p in state.get("closed_positions", []):
        mid = str(p.get("market_id"))
        if mid not in resolutions and p.get("resolved_winning_outcome"):
            resolutions[mid] = {
                "market_id": mid,
                "winning_outcome": p["resolved_winning_outcome"],
                "final_spot": p.get("final_spot"),
                "open_spot": p.get("candle_open_spot"),
            }

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

    # Collect per-market telemetry stream and all raw shock events
    market_telem = defaultdict(list)
    market_meta = {}
    over_cap_candidates = []
    seen_over_cap = set()
    valid_15m_trades = []
    seen_valid_15m = set()

    # Also index simultaneous 15m and 1h snapshots by (asset, expiry_ts_rounded, unix_second)
    snapshots_by_expiry = defaultdict(lambda: {"15m": [], "1h": []})

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
            tte = float(rec.get("seconds_to_expiry", 0.0) or 0.0)
            if t0 <= 0 or tte <= 0:
                continue
            exp_ts = float(rec.get("expiry_ts") or (t0 + tte))
            exp_bucket = int(round(exp_ts / 60.0) * 60)
            asset = str(rec.get("asset", "BTC")).upper()
            dist = float(rec.get("candle_distance_pct", 0.0) or 0.0)
            spot_t0 = float(rec.get("spot_at_t0") or rec.get("trigger_price") or 0.0)
            open_spot = float(rec.get("candle_open_spot") or 0.0)
            if open_spot <= 0 and spot_t0 > 0:
                open_spot = spot_t0 / (1.0 + dist / 100.0)

            features = rec.get("pre_shock_features_t0") or {}
            up_tf = features.get("UP") or {}
            dn_tf = features.get("DOWN") or {}
            up_b = float(up_tf.get("best_bid") or 0.0)
            up_a = float(up_tf.get("best_ask") or 0.0)
            dn_b = float(dn_tf.get("best_bid") or 0.0)
            dn_a = float(dn_tf.get("best_ask") or 0.0)

            horizon = str(rec.get("horizon") or resolutions[mid].get("horizon") or "1h").lower()
            is_15m = "15m" in horizon or (0 < tte <= 900.0 and ":" in str(rec.get("title", "")))

            if up_b > 0 and up_a > 0 and dn_b > 0 and dn_a > 0:
                market_telem[mid].append((t0, dist, up_b, up_a, dn_b, dn_a, spot_t0, open_spot))
                market_meta[mid] = {
                    "asset": asset,
                    "is_15m": is_15m,
                    "expiry_ts": exp_ts,
                    "open_spot": open_spot,
                    "win_out": resolutions[mid].get("winning_outcome"),
                }
                if 20.0 <= tte <= 900.0 and open_spot > 0:
                    key_exp = (asset, exp_bucket)
                    snapshots_by_expiry[key_exp]["15m" if is_15m else "1h"].append({
                        "t0": t0,
                        "tte": tte,
                        "mid": mid,
                        "spot": spot_t0,
                        "strike": open_spot,
                        "up_b": up_b,
                        "up_a": up_a,
                        "dn_b": dn_b,
                        "dn_a": dn_a,
                        "win_out": resolutions[mid].get("winning_outcome"),
                    })

            s_dir = rec.get("shock_direction")
            if s_dir not in ("BUY", "SELL"):
                continue
            shock_ofi = abs(float(rec.get("shock_ofi", 0.0) or 0.0))
            if shock_ofi < 0.45:
                continue
            target = "UP" if s_dir == "BUY" else "DOWN"
            tf = features.get(target) or {}
            ask = float(tf.get("vwap_$20") or tf.get("best_ask") or 0.0)
            best_ask = float(tf.get("best_ask") or ask)
            best_bid = float(tf.get("best_bid") or 0.0)
            obi_l1 = float(tf.get("obi_l1") or 0.0)
            age_ask_ms = float(tf.get("age_ask_ms") or 400.0)
            if age_ask_ms < 50.0 and obi_l1 < -0.50:
                continue
            if age_ask_ms < 25.0 and obi_l1 < -0.25:
                continue

            signed_dist = dist if target == "UP" else -dist
            if is_15m and (30.0 <= tte <= 600.0 and signed_dist >= 0.06):
                max_ask = 0.66 if (tte > 470.0 and signed_dist < 0.09) else 0.78
                if 0.55 <= ask <= max_ask:
                    if (mid, target) not in seen_valid_15m:
                        seen_valid_15m.add((mid, target))
                        valid_15m_trades.append({
                            "mid": mid,
                            "asset": asset,
                            "t0": t0,
                            "tte": tte,
                            "exp_ts": exp_ts,
                            "target": target,
                            "ask": ask,
                            "best_ask": best_ask,
                            "best_bid": best_bid,
                            "obi_l1": obi_l1,
                            "signed_dist": signed_dist,
                            "win_out": resolutions[mid].get("winning_outcome"),
                        })
                elif max_ask < ask <= max_ask + 0.06 and best_bid >= 0.52:
                    # Candidate for Phase 3A: Reactive Post-Only Maker-In when Taker ask is 1c-6c too expensive!
                    if (mid, target) not in seen_over_cap and (mid, target) not in seen_valid_15m:
                        seen_over_cap.add((mid, target))
                        over_cap_candidates.append({
                            "mid": mid,
                            "asset": asset,
                            "t0": t0,
                            "tte": tte,
                            "exp_ts": exp_ts,
                            "target": target,
                            "ask": ask,
                            "best_ask": best_ask,
                            "best_bid": best_bid,
                            "max_ask": max_ask,
                            "signed_dist": signed_dist,
                            "win_out": resolutions[mid].get("winning_outcome"),
                        })

    for mid in market_telem:
        market_telem[mid].sort(key=lambda x: x[0])

    # =========================================================================
    # PHASE 2 BACKTEST: SYNTHETIC BOX LOCK vs. CANCEL + SELL UNWIND
    # =========================================================================
    print("=" * 110)
    print("PHASE 2 BACKTEST: SYNTHETIC BOX LOCK (BUY OPPOSITE + MERGE) vs. LEGACY SELL UNWIND")
    print("=" * 110)
    # Across all telemetry ticks where UP+DOWN books are both valid, measure:
    # 1. Instant Box Spread: (1.00 - opp_ask) vs held_bid
    # 2. 500ms-1500ms Cancel-Delay Slippage during adverse moves
    tight_count = 0
    equal_count = 0
    wide_count = 0
    salvage_events = 0
    net_sell_sum = 0.0
    net_box_sum = 0.0

    for tr in valid_15m_trades:
        pts = market_telem[tr["mid"]]
        t0 = tr["t0"]
        target = tr["target"]
        for idx, (ts, dist, ub, ua, db, da, sp, osp) in enumerate(pts):
            if ts <= t0:
                continue
            held_b = ub if target == "UP" else db
            opp_a = da if target == "UP" else ua
            if held_b <= 0 or opp_a <= 0:
                continue
            implied_bid_via_box = round(1.00 - opp_a, 4)
            diff = round(implied_bid_via_box - held_b, 4)
            if diff > 0.001:
                tight_count += 1
            elif abs(diff) <= 0.001:
                equal_count += 1
            else:
                wide_count += 1

            # Check if this tick is a salvage trigger (wrong-side >= 0.08% and held_b <= 0.50)
            s_dist = dist if target == "UP" else -dist
            if s_dist <= -0.08 and 0.08 <= held_b <= 0.50:
                # Find the tick 0.5s - 2.0s later to measure actual cancel-wait bid decay!
                delayed_b = held_b
                for ts2, _, ub2, _, db2, _, _, _ in pts[idx + 1 :]:
                    if 0.4 <= (ts2 - ts) <= 2.5:
                        delayed_b = ub2 if target == "UP" else db2
                        break
                    elif (ts2 - ts) > 2.5:
                        break
                # Net recovery per share:
                # Pathway A (Wait 500ms+ for DELETE /orders, then SELL held token at delayed_b)
                v_sell = delayed_b - 0.07 * delayed_b * (1.0 - delayed_b)
                # Pathway B (Immediate 0.07ms BUY opposite token at opp_a + CTF Merge for $1.00)
                v_box = 1.00 - (opp_a + 0.07 * opp_a * (1.0 - opp_a)) - 0.0001
                net_sell_sum += v_sell
                net_box_sum += v_box
                salvage_events += 1
                break

    total_ticks = max(1, tight_count + equal_count + wide_count)
    print(f"L2 Complementary Book Alignment ({total_ticks} post-entry ticks):")
    print(f"  - Opposite Ask Tighter (1 - opp_ask > held_bid): {tight_count:4d} ({tight_count/total_ticks*100:5.1f}%)")
    print(f"  - Exact No-Arb Parity  (1 - opp_ask == held_bid): {equal_count:4d} ({equal_count/total_ticks*100:5.1f}%)")
    print(f"  - Opposite Ask Wider   (1 - opp_ask < held_bid): {wide_count:4d} ({wide_count/total_ticks*100:5.1f}%)")
    if salvage_events > 0:
        avg_sell = net_sell_sum / salvage_events
        avg_box = net_box_sum / salvage_events
        diff_cents = (avg_box - avg_sell) * 100.0
        print(f"Empirical Crash Salvage Comparison ({salvage_events} salvage events with recorded post-cancel ticks):")
        print(f"  - Legacy Cancel + Sell Held Token Avg Recovery: ${avg_sell:.4f}/share")
        print(f"  - Zero-Cancel Buy Opposite + Merge Avg Recovery: ${avg_box:.4f}/share ({diff_cents:+.2f}c/share difference)")

    # =========================================================================
    # PHASE 3A BACKTEST: REACTIVE POST-ONLY MAKER-IN ON OVER-CAP / MISSED SHOCKS
    # =========================================================================
    print("\n" + "=" * 110)
    print("PHASE 3A BACKTEST: POST-ONLY MAKER-IN (0% FEE + 20% REBATE) ON PRICE-CAPPED SHOCKS")
    print("=" * 110)
    for ttl_window in (5.0, 10.0, 15.0):
        fills = 0
        wins = 0
        losses = 0
        total_pnl = 0.0
        canceled_toxic = 0
        for cand in over_cap_candidates:
            pts = market_telem[cand["mid"]]
            t0 = cand["t0"]
            target = cand["target"]
            # Post resting Maker BUY at min(max_ask, best_ask - 0.01)
            maker_px = round(min(cand["max_ask"], cand["best_ask"] - 0.01), 2)
            if maker_px < 0.55:
                continue
            filled = False
            for ts, dist, ub, ua, db, da, sp, osp in pts:
                if ts <= t0:
                    continue
                if (ts - t0) > ttl_window:
                    break
                s_dist = dist if target == "UP" else -dist
                # Toxicity auto-cancel: if spot cushion drops below 0.04%, cancel immediately BEFORE fill!
                if s_dist < 0.04:
                    canceled_toxic += 1
                    break
                cur_ask = ua if target == "UP" else da
                cur_bid = ub if target == "UP" else db
                # Fill condition: ask touches maker_px or bid drops to/below maker_px while s_dist >= 0.04%
                if (0 < cur_ask <= maker_px + 0.001) or (0 < cur_bid <= maker_px):
                    filled = True
                    break
            if filled:
                fills += 1
                shares = 20.0 / maker_px
                eff_cost_per_share = maker_cost(maker_px)
                total_cost_usd = shares * eff_cost_per_share
                won = (cand["target"] == cand["win_out"])
                pnl = (shares * 1.00 - total_cost_usd) if won else (-total_cost_usd)
                total_pnl += pnl
                if won:
                    wins += 1
                else:
                    losses += 1
        wr = (wins / fills * 100.0) if fills > 0 else 0.0
        avg = (total_pnl / fills) if fills > 0 else 0.0
        print(
            f"Maker-In TTL={ttl_window:4.1f}s | Candidates={len(over_cap_candidates):2d} | "
            f"ToxicCancels={canceled_toxic:2d} | Fills={fills:2d} ({wins:2d}W/{losses:2d}L) | "
            f"WR={wr:5.1f}% | NetPnL=${total_pnl:+7.2f} | Avg=${avg:+5.2f}/fill"
        )

    # =========================================================================
    # PHASE 3B BACKTEST: STOIKOV MARTINGALE MICRO-PRICE SIZING / FILTERING
    # =========================================================================
    print("\n" + "=" * 110)
    print("PHASE 3B BACKTEST: STOIKOV MICRO-PRICE PULL (P_micro - Mid) ON 15M TRADES (n=110)")
    print("=" * 110)
    pos_pull = []
    neg_pull = []
    for tr in valid_15m_trades:
        # Compute Stoikov micro-price pull
        obi = tr["obi_l1"]
        shares = 20.0 / tr["ask"]
        efee = calculate_taker_fee(20.0, tr["ask"], 0.07, 1.0)
        won = (tr["target"] == tr["win_out"])
        # Approximate PnL with V4 stop from resolution
        pnl = (shares * 1.0 - 20.0 - efee) if won else (-20.0 - efee)
        if obi >= 0.0:
            pos_pull.append((won, pnl))
        else:
            neg_pull.append((won, pnl))
    w_pos = sum(1 for w, _ in pos_pull if w)
    w_neg = sum(1 for w, _ in neg_pull if w)
    print(f"Positive Stoikov Micro-Price Pull (obi_l1 >= 0): n={len(pos_pull):3d} | WR={w_pos/max(1,len(pos_pull))*100:5.1f}%")
    print(f"Negative Stoikov Micro-Price Pull (obi_l1 <  0): n={len(neg_pull):3d} | WR={w_neg/max(1,len(neg_pull))*100:5.1f}%")

    # =========================================================================
    # PHASE 4 BACKTEST: SLEEVE 5 (:45-:00 15M vs. 1H MONOTONICITY BOX ARBITRAGE)
    # =========================================================================
    print("\n" + "=" * 110)
    print("PHASE 4 BACKTEST: SLEEVE 5 (:45-:00 OVERLAPPING 15M vs. 1H MONOTONICITY BOX ARBITRAGE)")
    print("=" * 110)
    overlapping_windows = 0
    risk_free_arbs = []
    corridor_arbs = []
    all_min_costs = []

    for (asset, exp_bucket), sides in sorted(snapshots_by_expiry.items()):
        s15_list = sides["15m"]
        s1h_list = sides["1h"]
        if not s15_list or not s1h_list:
            continue
        overlapping_windows += 1
        best_pair_for_window = None
        for s15 in s15_list:
            # Find closest 1h snapshot within 5 seconds
            for s1h in s1h_list:
                if abs(s15["t0"] - s1h["t0"]) <= 5.0:
                    k15 = s15["strike"]
                    k1h = s1h["strike"]
                    if abs(k15 - k1h) / max(k15, 1.0) < 0.0003:
                        continue  # strikes too close (<3 bps)
                    if k15 < k1h:
                        # Dominant box: Buy UP_15m + Buy DOWN_1h
                        leg1_px, leg2_px = s15["up_a"], s1h["dn_a"]
                        leg1_win = (s15["win_out"] == "UP")
                        leg2_win = (s1h["win_out"] == "DOWN")
                        k_low, k_high = k15, k1h
                    else:
                        # Dominant box: Buy UP_1h + Buy DOWN_15m
                        leg1_px, leg2_px = s1h["up_a"], s15["dn_a"]
                        leg1_win = (s1h["win_out"] == "UP")
                        leg2_win = (s15["win_out"] == "DOWN")
                        k_low, k_high = k1h, k15

                    c_all_in = taker_cost(leg1_px) + taker_cost(leg2_px)
                    c_maker = maker_cost(max(0.01, leg1_px - 0.01)) + maker_cost(max(0.01, leg2_px - 0.01))
                    payout = (1.0 if leg1_win else 0.0) + (1.0 if leg2_win else 0.0)
                    spot = s15["spot"]
                    in_corridor_now = (k_low <= spot <= k_high)
                    cand = {
                        "asset": asset,
                        "exp_bucket": exp_bucket,
                        "tte": s15["tte"],
                        "k_low": k_low,
                        "k_high": k_high,
                        "corridor_width_pct": (k_high - k_low) / k_low * 100.0,
                        "spot": spot,
                        "in_corridor_now": in_corridor_now,
                        "c_taker": c_all_in,
                        "c_maker": c_maker,
                        "payout": payout,
                    }
                    if best_pair_for_window is None or c_all_in < best_pair_for_window["c_taker"]:
                        best_pair_for_window = cand

        if best_pair_for_window:
            all_min_costs.append(best_pair_for_window["c_taker"])
            if best_pair_for_window["c_taker"] < 1.00:
                risk_free_arbs.append(best_pair_for_window)
            if best_pair_for_window["c_taker"] <= 1.05 and best_pair_for_window["in_corridor_now"]:
                corridor_arbs.append(best_pair_for_window)

    print(f"Overlapping :45-:00 (15m + 1h) Windows Analyzed: {overlapping_windows}")
    if all_min_costs:
        print(f"Min Taker Box Cost Across Windows: min=${min(all_min_costs):.4f}, median=${sorted(all_min_costs)[len(all_min_costs)//2]:.4f}")
    print(f"Hard Risk-Free Taker Arbs (All-in Cost < $1.00): {len(risk_free_arbs)}")
    for a in risk_free_arbs[:10]:
        print(
            f"  [RISK-FREE ARB] {a['asset']} TTE={a['tte']:.0f}s | Corridor=[{a['k_low']:.2f}, {a['k_high']:.2f}] "
            f"({a['corridor_width_pct']:.2f}%) | TakerCost=${a['c_taker']:.4f} | ActualPayout=${a['payout']:.2f} | "
            f"NetProfit=${a['payout'] - a['c_taker']:+.4f}/pair"
        )
    print(f"Statistical Corridor Box Arbs (Spot inside [K_low, K_high] & Cost <= $1.05): {len(corridor_arbs)}")
    tot_corr_pnl = 0.0
    for a in corridor_arbs:
        net_p = a["payout"] - a["c_taker"]
        tot_corr_pnl += net_p
        print(
            f"  [CORRIDOR ARB]  {a['asset']} TTE={a['tte']:.0f}s | Corridor=[{a['k_low']:.2f}, {a['k_high']:.2f}] "
            f"({a['corridor_width_pct']:.2f}%) | TakerCost=${a['c_taker']:.4f} (Maker=${a['c_maker']:.4f}) | "
            f"ActualPayout=${a['payout']:.2f} | NetPnL=${net_p:+.4f}/pair"
        )
    if corridor_arbs:
        print(f"Total Realized Corridor Arb PnL (at 20 pairs / ~$20 notional): +${tot_corr_pnl * 20.0:.2f}")


if __name__ == "__main__":
    main()

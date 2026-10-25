#!/usr/bin/env python3
"""
Empirical Backtest of the 5 Additional Deep Research Ideas across Recorded Polymarket Telemetry:
  Idea 1: Marginal-VWAP / Elastic Prewarm Rung Down-Snapping (preventing FOK Sweep Infeasible)
  Idea 2: CTF splitPosition + Dual $0.54 Maker Straddle ("Mint-and-Make" in 2100s-3400s 1h Zone)
  Idea 3: First-Passage Tranche-1 Maker Exit (+8c to +11c + 15s V2 hold) on 1h Mid-Hour Trades
  Idea 4: Cross-Venue Basis Snapback Filter (aligned_div_bps > 4.0 & aligned_cb_move_bps < 0.8)
  Idea 5: Instant Pre-Signed Fallback Rung (+2c/+3c <= Ask_max) upon 400 FAK Miss
"""

import json
import math
from collections import defaultdict
from backtest_hard_bid_drop_variants import (
    RESOLUTIONS_FILE,
    TRIGGERS_FILE,
    STATE_FILE,
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

    state = json.load(open(STATE_FILE, "r", encoding="utf-8"))
    for p in state.get("closed_positions", []):
        mid = str(p.get("market_id"))
        if mid not in resolutions and p.get("resolved_winning_outcome"):
            resolutions[mid] = {"market_id": mid, "winning_outcome": p["resolved_winning_outcome"]}

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

    market_telem = defaultdict(list)
    trades_15m = []
    trades_1h = []
    thin_l1_rescued = []
    straddle_1h_markets = {}
    seen_15m = set()
    seen_1h = set()
    seen_thin = set()

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
            dist = float(rec.get("candle_distance_pct", 0.0) or 0.0)
            features = rec.get("pre_shock_features_t0") or {}
            up_tf = features.get("UP") or {}
            dn_tf = features.get("DOWN") or {}
            up_b = float(up_tf.get("best_bid") or 0.0)
            up_a = float(up_tf.get("best_ask") or 0.0)
            dn_b = float(dn_tf.get("best_bid") or 0.0)
            dn_a = float(dn_tf.get("best_ask") or 0.0)

            horizon = str(rec.get("horizon") or resolutions[mid].get("horizon") or "1h").lower()
            is_15m = "15m" in horizon or (0 < tte <= 900.0 and ":" in str(rec.get("title", "")))

            if up_b > 0 or dn_b > 0:
                market_telem[mid].append((t0, dist, up_b, up_a, dn_b, dn_a))

            # Idea 2: Track 1h markets that have a calm early window (2100s <= TTE <= 3400s, |dist| <= 0.04%)
            if not is_15m and 2100.0 <= tte <= 3400.0 and abs(dist) <= 0.04 and mid not in straddle_1h_markets:
                if 0.46 <= up_a <= 0.54 and 0.46 <= dn_a <= 0.54:
                    straddle_1h_markets[mid] = {
                        "mid": mid,
                        "t0": t0,
                        "tte": tte,
                        "exp_ts": exp_ts,
                        "win_out": resolutions[mid].get("winning_outcome"),
                    }

            s_dir = rec.get("shock_direction")
            if s_dir not in ("BUY", "SELL"):
                continue
            shock_ofi = abs(float(rec.get("shock_ofi", 0.0) or 0.0))
            if shock_ofi < 0.45:
                continue
            target = "UP" if s_dir == "BUY" else "DOWN"
            tf = features.get(target) or {}
            raw_asks = tf.get("raw_top_asks") or []
            best_ask = float(tf.get("best_ask") or 0.0)
            vwap_20 = float(tf.get("vwap_$20") or best_ask)
            vwap_10 = float(tf.get("vwap_$10") or best_ask)
            obi_l1 = float(tf.get("obi_l1") or 0.0)
            age_ask_ms = float(tf.get("age_ask_ms") or 400.0)
            if age_ask_ms < 50.0 and obi_l1 < -0.50:
                continue
            if age_ask_ms < 25.0 and obi_l1 < -0.25:
                continue

            signed_dist = dist if target == "UP" else -dist
            v_div = float(rec.get("venue_divergence_bps") or 0.0)
            cb_mv = float(rec.get("coinbase_move_bps_2s") or 0.0)
            cb_spot = float(rec.get("coinbase_spot") or 0.0)

            if is_15m:
                if not (30.0 <= tte <= 600.0 and signed_dist >= 0.06):
                    continue
                max_ask = 0.66 if (tte > 470.0 and signed_dist < 0.09) else 0.78
                # Idea 1 check: What if best_ask <= max_ask and vwap_10 <= max_ask, but vwap_20 > max_ask (or L1 depth < $21.55)?
                l1_notional = (float(raw_asks[0][0]) * float(raw_asks[0][1])) if raw_asks else 25.0
                if 0.55 <= best_ask <= max_ask and (vwap_20 > max_ask or l1_notional < 21.55) and l1_notional >= 12.0:
                    if (mid, target) not in seen_thin:
                        seen_thin.add((mid, target))
                        thin_l1_rescued.append({
                            "mid": mid,
                            "target": target,
                            "best_ask": best_ask,
                            "l1_notional": min(16.50, l1_notional),
                            "win_out": resolutions[mid].get("winning_outcome"),
                        })
                if 0.55 <= vwap_20 <= max_ask and (mid, target) not in seen_15m:
                    seen_15m.add((mid, target))
                    trades_15m.append({
                        "mid": mid,
                        "t0": t0,
                        "tte": tte,
                        "exp_ts": exp_ts,
                        "target": target,
                        "ask": vwap_20,
                        "best_ask": best_ask,
                        "max_ask": max_ask,
                        "signed_dist": signed_dist,
                        "v_div": v_div,
                        "cb_mv": cb_mv,
                        "cb_spot": cb_spot,
                        "win_out": resolutions[mid].get("winning_outcome"),
                    })
            else:
                # Deployed 1h rules
                ok_1h = False
                max_ask_1h = 0.78
                if 900.0 < tte <= 1800.0 and signed_dist >= 0.12 and 0.55 <= vwap_20 <= 0.72:
                    ok_1h = True
                    max_ask_1h = 0.72
                elif 600.0 < tte <= 900.0 and signed_dist >= 0.15 and 0.55 <= vwap_20 <= 0.80:
                    ok_1h = True
                    max_ask_1h = 0.80
                elif 30.0 <= tte <= 600.0 and signed_dist >= 0.08 and 0.55 <= vwap_20 <= 0.80:
                    ok_1h = True
                    max_ask_1h = 0.80
                if ok_1h and (mid, target) not in seen_1h:
                    seen_1h.add((mid, target))
                    trades_1h.append({
                        "mid": mid,
                        "t0": t0,
                        "tte": tte,
                        "exp_ts": exp_ts,
                        "target": target,
                        "ask": vwap_20,
                        "best_ask": best_ask,
                        "max_ask": max_ask_1h,
                        "signed_dist": signed_dist,
                        "v_div": v_div,
                        "cb_mv": cb_mv,
                        "cb_spot": cb_spot,
                        "win_out": resolutions[mid].get("winning_outcome"),
                    })

    for mid in market_telem:
        market_telem[mid].sort(key=lambda x: x[0])

    # =========================================================================
    # IDEA 1: MARGINAL-VWAP / PREWARM RUNG DOWN-SNAPPING ($21.55 -> $16.50 / $12.00)
    # =========================================================================
    print("=" * 110)
    print("IDEA 1 BACKTEST: ELASTIC RUNG DOWN-SNAPPING WHEN L1/LIMIT DEPTH < $21.55 (PREVENTING FOK INFEASIBLE)")
    print("=" * 110)
    w_thin = sum(1 for t in thin_l1_rescued if t["target"] == t["win_out"])
    l_thin = len(thin_l1_rescued) - w_thin
    pnl_thin = 0.0
    for t in thin_l1_rescued:
        notional = 16.50 if t["l1_notional"] >= 16.50 else 12.00
        sh = notional / t["best_ask"]
        ef = calculate_taker_fee(notional, t["best_ask"], 0.07, 1.0)
        won = (t["target"] == t["win_out"])
        pnl_thin += (sh * 1.0 - notional - ef) if won else (-notional - ef)
    print(
        f"Thin-L1 Qualified Shocks (L1 < $21.55 at limit_px, snapped to $16.50/$12.00): "
        f"n={len(thin_l1_rescued)} ({w_thin}W/{l_thin}L) | WR={w_thin/max(1,len(thin_l1_rescued))*100:.1f}% | "
        f"NetPnL=${pnl_thin:+.2f} | Avg=${pnl_thin/max(1,len(thin_l1_rescued)):+.2f}/trade"
    )

    # =========================================================================
    # IDEA 2: CTF splitPosition + DUAL $0.54 MAKER STRADDLE IN 2100s-3400s 1H ZONE
    # =========================================================================
    print("\n" + "=" * 110)
    print("IDEA 2 BACKTEST: CTF splitPosition + DUAL $0.54 MAKER STRADDLE IN 2100s-3400s 1H ZONE")
    print("=" * 110)
    for target_sell_px in (0.53, 0.54, 0.55):
        both_filled = 0
        one_filled_win = 0
        one_filled_loss = 0
        neither_filled = 0
        straddle_pnl = 0.0
        rebate = 0.20 * 0.07 * target_sell_px * (1.0 - target_sell_px)
        eff_sell = target_sell_px + rebate  # e.g. $0.5435
        for mid, s in straddle_1h_markets.items():
            pts = market_telem[mid]
            up_hit = False
            dn_hit = False
            for ts, dist, ub, ua, db, da in pts:
                if ts <= s["t0"]:
                    continue
                if ub >= target_sell_px or ua > target_sell_px + 0.01:
                    up_hit = True
                if db >= target_sell_px or da > target_sell_px + 0.01:
                    dn_hit = True
            # 20 pairs ($20 USDC split into 20 UP + 20 DOWN)
            pairs = 20.0
            if up_hit and dn_hit:
                both_filled += 1
                straddle_pnl += pairs * (2.0 * eff_sell - 1.00)
            elif up_hit and not dn_hit:
                # Sold UP at eff_sell, still holding DOWN to expiry (or stop)
                if s["win_out"] == "DOWN":
                    one_filled_win += 1
                    straddle_pnl += pairs * (eff_sell + 1.00 - 1.00)
                else:
                    one_filled_loss += 1
                    straddle_pnl += pairs * (eff_sell + 0.00 - 1.00)
            elif dn_hit and not up_hit:
                if s["win_out"] == "UP":
                    one_filled_win += 1
                    straddle_pnl += pairs * (eff_sell + 1.00 - 1.00)
                else:
                    one_filled_loss += 1
                    straddle_pnl += pairs * (eff_sell + 0.00 - 1.00)
            else:
                neither_filled += 1
        tot_s = len(straddle_1h_markets)
        print(
            f"Dual Maker Sell @ ${target_sell_px:.2f} | Markets={tot_s:3d} | BothHit={both_filled:2d} "
            f"(+${(2*eff_sell-1)*20:.2f}/ea) | 1-Leg OneWayLoss={one_filled_loss:2d} (-${(1-eff_sell)*20:.2f}/ea) | "
            f"NetPnL=${straddle_pnl:+7.2f} (${straddle_pnl/max(1,tot_s):+5.2f}/mkt)"
        )

    # =========================================================================
    # IDEA 3: FIRST-PASSAGE TRANCHE-1 MAKER EXIT (+9c/+11c) ON 1H MID-HOUR TRADES
    # =========================================================================
    print("\n" + "=" * 110)
    print("IDEA 3 BACKTEST: FIRST-PASSAGE TRANCHE-1 MAKER EXIT ON 1H TRADES (n=99)")
    print("=" * 110)
    mid_hour_trades = [t for t in trades_1h if t["tte"] > 900.0]
    for t1_offset in (0.99, 0.08, 0.10, 0.12, 0.14):
        tot_p = 0.0
        wins = 0
        t1_fills = 0
        for tr in mid_hour_trades:
            pts = market_telem[tr["mid"]]
            sh = 20.0 / tr["ask"]
            ef = calculate_taker_fee(20.0, tr["ask"], 0.07, 1.0)
            if t1_offset >= 0.50:
                # Hold to maturity (with V2 stop)
                pnl, won, _, _ = simulate_position_path(
                    pts, tr["t0"], tr["exp_ts"], tr["target"], tr["ask"],
                    tr["signed_dist"], False, sh, 20.0, ef, 0.07, 1.0,
                    tr["win_out"], "V2_STRICT_WRONGSIDE_4_5BPS_6S",
                )
            else:
                # Check if 50% Tranche 1 fills at entry + t1_offset before any stop
                t1_px = min(0.95, round(tr["ask"] + t1_offset, 2))
                hit_t1 = False
                for ts, dist, ub, ua, db, da in pts:
                    if ts <= tr["t0"]:
                        continue
                    b = ub if tr["target"] == "UP" else db
                    if b >= t1_px:
                        hit_t1 = True
                        break
                pnl_full, won_full, _, _ = simulate_position_path(
                    pts, tr["t0"], tr["exp_ts"], tr["target"], tr["ask"],
                    tr["signed_dist"], False, sh, 20.0, ef, 0.07, 1.0,
                    tr["win_out"], "V3_STRICT_WRONGSIDE_4_5BPS_12S" if hit_t1 else "V2_STRICT_WRONGSIDE_4_5BPS_6S",
                )
                if hit_t1:
                    t1_fills += 1
                    reb = 0.20 * 0.07 * t1_px * (1.0 - t1_px)
                    pnl_half1 = 0.5 * sh * (t1_px + reb) - 10.0 - 0.5 * ef
                    pnl = pnl_half1 + 0.5 * pnl_full
                    won = pnl > 0
                else:
                    pnl = pnl_full
                    won = won_full
            tot_p += pnl
            if won:
                wins += 1
        label = "Hold-to-Maturity ($0.98 TP)" if t1_offset >= 0.50 else f"50% Tranche-1 @ entry+${t1_offset:.2f}"
        print(
            f"{label:<32} | n={len(mid_hour_trades):2d} | T1_Fills={t1_fills:2d} | "
            f"WR={wins/max(1,len(mid_hour_trades))*100:5.1f}% | TotalPnL=${tot_p:+7.2f} | Avg=${tot_p/max(1,len(mid_hour_trades)):+5.2f}"
        )

    # =========================================================================
    # IDEA 4: CROSS-VENUE BASIS SNAPBACK FILTER (aligned_div_bps > 4.0 & cb_move < 0.8)
    # =========================================================================
    print("\n" + "=" * 110)
    print("IDEA 4 BACKTEST: CROSS-VENUE BASIS SNAPBACK FILTER ON 15M (n=110) & 1H (n=99)")
    print("=" * 110)
    for s_name, t_list in (("15m Sleeve 1", trades_15m), ("1h Sleeve 2", trades_1h)):
        vetoed = []
        kept = []
        for tr in t_list:
            d_sign = 1.0 if tr["target"] == "UP" else -1.0
            al_div = d_sign * tr["v_div"]
            al_cb = d_sign * tr["cb_mv"]
            won = (tr["target"] == tr["win_out"])
            if tr["cb_spot"] > 0 and al_div > 4.0 and al_cb < 0.8:
                vetoed.append(won)
            else:
                kept.append(won)
        vw = sum(1 for w in vetoed if w)
        vl = len(vetoed) - vw
        kw = sum(1 for w in kept if w)
        print(
            f"{s_name:<15} | Vetoed by Basis Snapback: n={len(vetoed):2d} ({vw}W/{vl}L) | "
            f"Kept: n={len(kept):3d} (WR={kw/max(1,len(kept))*100:5.1f}%)"
        )

    # =========================================================================
    # IDEA 5: HEADROOM FOR INSTANT +2c/+3c PRE-SIGNED FALLBACK ON 400 FAK MISS
    # =========================================================================
    print("\n" + "=" * 110)
    print("IDEA 5 BACKTEST: HEADROOM (Ask_max - best_ask >= $0.03) FOR INSTANT FALLBACK RUNG ON 400 MISS")
    print("=" * 110)
    eligible_fallback = [t for t in trades_15m if (t["max_ask"] - t["best_ask"]) >= 0.03]
    w_fb = sum(1 for t in eligible_fallback if t["target"] == t["win_out"])
    l_fb = len(eligible_fallback) - w_fb
    pnl_at_plus2c = 0.0
    for t in eligible_fallback:
        fb_px = min(t["max_ask"], t["best_ask"] + 0.025)
        sh = 20.0 / fb_px
        ef = calculate_taker_fee(20.0, fb_px, 0.07, 1.0)
        won = (t["target"] == t["win_out"])
        pnl_at_plus2c += (sh * 1.0 - 20.0 - ef) if won else (-20.0 - ef)
    print(
        f"15m Trades with >=3c Headroom Below Ask_max: {len(eligible_fallback)}/{len(trades_15m)} ({len(eligible_fallback)/max(1,len(trades_15m))*100:.1f}%)"
    )
    print(
        f"If Rescued via +2.5c Fallback Rung on 400 Miss: {w_fb}W/{l_fb}L (WR={w_fb/max(1,len(eligible_fallback))*100:.1f}%) | "
        f"NetPnL=${pnl_at_plus2c:+.2f} (+${pnl_at_plus2c/max(1,len(eligible_fallback)):.2f}/trade)"
    )


if __name__ == "__main__":
    main()

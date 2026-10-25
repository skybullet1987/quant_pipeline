#!/usr/bin/env python3
"""
Backtest of HARD_BID_DROP_SALVAGE variants across:
1. Today's 7 live post-fix trades (exact entry prices, shares, timestamps, and telemetry paths)
2. Full historical 15m (Sleeve 1) and 1h (Sleeve 2) qualified trigger dataset
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DATA_DIR = Path("data/polymarket")
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
TRIGGERS_FILE = DATA_DIR / "live_shock_triggers.jsonl"
TELEM_BTC_FILE = DATA_DIR / "polymarket_hourly_telemetry.jsonl"
TELEM_ETH_FILE = DATA_DIR / "polymarket_hourly_telemetry_eth.jsonl"
STATE_FILE = DATA_DIR / "live_harvester_state.json"


def calculate_taker_fee(notional_usd: float, price: float, fee_rate: float = 0.07, fee_exponent: float = 1.0) -> float:
    if fee_rate <= 0.0 or notional_usd <= 0.0:
        return 0.0
    clamped_p = max(0.001, min(0.999, price))
    shares = notional_usd / clamped_p
    per_share_fee = fee_rate * ((clamped_p * (1.0 - clamped_p)) ** fee_exponent)
    return float(Decimal(str(shares * per_share_fee)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))


def simulate_position_path(
    m_telem,
    t0: float,
    expiry_ts: float,
    target: str,
    entry_px: float,
    entry_s_dist_pct: float,
    is_15m: bool,
    shares: float,
    notional_usd: float,
    entry_fee: float,
    fee_rate: float,
    fee_exp: float,
    winning_outcome: str,
    variant: str,
):
    """
    Replays exact L2 + spot telemetry from t0 to expiry under the specified stop/salvage variant.
    Note: s_dist_pct is signed cushion in percent (+ means winning side of candle open, - means losing side).
    entry_move_pct (fractional, e.g. -0.0010 = -0.10%) is (s_dist_pct - entry_s_dist_pct) / 100.0.
    """
    lo, hi = 0, len(m_telem)
    while lo < hi:
        mid_idx = (lo + hi) // 2
        if m_telem[mid_idx][0] < t0:
            lo = mid_idx + 1
        else:
            hi = mid_idx

    tp_px = 0.99 if entry_px >= 0.78 else 0.98
    max_seen_bid = entry_px
    low_bid_start = None
    opp_breakout_start = None
    ratchet_start = None

    exit_px = None
    exit_reason = "EXPIRY"

    for idx_pt in range(lo, len(m_telem)):
        pt_ts, pt_dist_pct, up_b, up_a, dn_b, dn_a = m_telem[idx_pt]
        tte_rem = max(0.0, expiry_ts - pt_ts)
        best_b = up_b if target == "UP" else dn_b
        best_a = up_a if target == "UP" else dn_a
        s_dist_pct = pt_dist_pct if target == "UP" else -pt_dist_pct
        entry_move_frac = (s_dist_pct - entry_s_dist_pct) / 100.0
        wrong_side_pct = -s_dist_pct  # > 0 when on losing side of candle open
        wrong_side_frac = wrong_side_pct / 100.0

        # 1. Resting Maker TP Fill
        if best_b >= tp_px or (best_a >= tp_px + 0.01 and best_b >= tp_px - 0.01):
            exit_px = tp_px
            exit_reason = "MAKER_TP"
            break

        # 2. Peak-Bid Trailing Profit Ratchet
        if best_b > 0:
            max_seen_bid = max(max_seen_bid, best_b)
        min_ratchet_arm = max(0.88, entry_px + 0.16)
        if max_seen_bid >= min_ratchet_arm:
            trail_delta = 0.05 if max_seen_bid >= 0.90 else 0.07
            trail_floor = round(max_seen_bid - trail_delta, 4)
            if best_b <= trail_floor and tte_rem >= 25.0 and best_b >= (entry_px + 0.10):
                if ratchet_start is None:
                    ratchet_start = pt_ts
                elif (pt_ts - ratchet_start) >= 4.0:
                    exit_px = best_b
                    exit_reason = "TRAILING_RATCHET"
                    break
            else:
                ratchet_start = None
        else:
            ratchet_start = None

        # 3. Final-45s Capital Recycler
        if tte_rem <= 45.0 and best_b >= 0.85 and best_b > (entry_px + 0.03):
            exit_px = best_b
            exit_reason = "FINAL_45S_RECYCLE"
            break

        # 4. TIER 2: Hard Bid-Drop + Spot Adverse Move Stop
        req_wrong_frac = 0.0004 if is_15m else 0.0005  # 0.04% (15m) or 0.05% (1h) wrong side of open
        hold_req_s = 6.0
        if variant == "V0_CURRENT_WITH_BYPASS":
            spot_adverse = (
                (wrong_side_frac >= req_wrong_frac and best_b <= 0.52)
                or (best_b <= 0.48 and entry_move_frac <= -0.0010)
            )
            enable_hard_bid_drop = True
        elif variant == "V1_REQUIRE_WRONGSIDE_GT_0":
            # Even on best_b <= 0.48, spot MUST be on the losing side of candle open (wrong_side_frac > 0)
            spot_adverse = (
                (wrong_side_frac >= req_wrong_frac and best_b <= 0.52)
                or (wrong_side_frac > 0.0 and best_b <= 0.48 and entry_move_frac <= -0.0010)
            )
            enable_hard_bid_drop = True
        elif variant == "V2_STRICT_WRONGSIDE_4_5BPS_6S":
            # Remove entry_move_pct bypass completely: require wrong_side_frac >= 0.04%/0.05%
            spot_adverse = (wrong_side_frac >= req_wrong_frac and best_b <= 0.52)
            enable_hard_bid_drop = True
        elif variant == "V3_STRICT_WRONGSIDE_4_5BPS_12S":
            spot_adverse = (wrong_side_frac >= req_wrong_frac and best_b <= 0.52)
            hold_req_s = 12.0
            enable_hard_bid_drop = True
        elif variant == "V4_STRICT_WRONGSIDE_8BPS_12S":
            spot_adverse = (wrong_side_frac >= 0.0008 and best_b <= 0.50)
            hold_req_s = 12.0
            enable_hard_bid_drop = True
        elif variant == "V5_3ZONE_SALVAGE_ONLY":
            spot_adverse = False
            enable_hard_bid_drop = False
        else:
            raise ValueError(f"Unknown variant {variant}")

        if enable_hard_bid_drop and best_b >= 0.08 and best_b <= (entry_px - 0.20) and spot_adverse and tte_rem >= 25.0:
            if low_bid_start is None:
                low_bid_start = pt_ts
            elif (pt_ts - low_bid_start) >= hold_req_s:
                exit_px = best_b
                exit_reason = "HARD_BID_DROP_SALVAGE"
                break
        else:
            low_bid_start = None

        # 5. 3-Zone TTE-Adaptive Wrong-Side Salvage Stop
        if wrong_side_pct <= 0.0:
            opp_breakout_start = None
        else:
            if tte_rem > 900.0:
                req_init, req_sust, req_dur, min_b = 0.16, 0.14, 40.0, 0.08
            elif tte_rem > 180.0:
                req_init, req_sust, req_dur, min_b = 0.11, 0.09, 18.0, 0.08
            elif tte_rem >= 25.0:
                req_init, req_sust, req_dur, min_b = 0.06, 0.04, 8.0, 0.06
            else:
                req_init, req_sust, req_dur, min_b = 999.0, 999.0, 999.0, 0.99

            if opp_breakout_start is None:
                if wrong_side_pct >= req_init:
                    opp_breakout_start = pt_ts
            else:
                if wrong_side_pct >= req_sust:
                    if (pt_ts - opp_breakout_start) >= req_dur and best_b >= min_b:
                        exit_px = best_b
                        exit_reason = "3ZONE_OPP_SALVAGE"
                        break
                else:
                    opp_breakout_start = None

    if exit_px is None:
        exit_px = 1.00 if (target == winning_outcome) else 0.00
        exit_reason = "EXPIRY_WIN" if (target == winning_outcome) else "EXPIRY_LOSS"

    gross_payout = round(shares * exit_px, 2)
    is_taker_exit = exit_reason in ("HARD_BID_DROP_SALVAGE", "3ZONE_OPP_SALVAGE", "TRAILING_RATCHET", "FINAL_45S_RECYCLE")
    exit_fee = calculate_taker_fee(gross_payout, exit_px, fee_rate, fee_exp) if is_taker_exit else 0.0
    net_pnl = round(gross_payout - notional_usd - entry_fee - exit_fee, 2)
    return net_pnl, (net_pnl > 0), exit_reason, exit_px


def main():
    resolutions = {}
    with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                resolutions[str(rec["market_id"])] = rec

    state = json.load(open(STATE_FILE, "r", encoding="utf-8"))
    live_7 = state["closed_positions"][-7:]
    # Ensure resolutions for today's 7 live markets are populated (including 5978915 which resolved Down)
    known_outcomes = {
        "6012995": "UP",
        "6013539": "DOWN",
        "6014317": "UP",
        "5972389": "DOWN",
        "6016117": "DOWN",
        "6017333": "DOWN",
        "5978915": "DOWN",
    }
    for m_id, out in known_outcomes.items():
        if m_id not in resolutions:
            resolutions[m_id] = {"market_id": m_id, "winning_outcome": out}

    # Collect all candidate market IDs
    triggers = []
    candidate_mids = set(known_outcomes.keys())
    seen_buckets = set()
    needle = '"market_id": "'
    trigger_telem_by_market = defaultdict(list)

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
                trigger_telem_by_market[mid].append((t0, dist, up_b, up_a, dn_b, dn_a))

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
            if ask < 0.55 or ask > 0.78:
                continue
            t0 = float(rec.get("t0_unix", 0.0) or 0.0)
            tte = float(rec.get("seconds_to_expiry", 0.0) or 0.0)
            dist = float(rec.get("candle_distance_pct", 0.0) or 0.0)
            signed_dist = dist if target == "UP" else -dist

            horizon = str(rec.get("horizon") or resolutions[mid].get("horizon") or "1h").lower()
            is_15m = "15m" in horizon or (0 < tte <= 900.0 and ":" in str(rec.get("title", "")))
            max_t = 600.0 if is_15m else 2100.0
            min_c = 0.06 if is_15m else 0.10
            max_a = 0.78 if is_15m else 0.76
            if not (30.0 <= tte <= max_t and signed_dist >= min_c and 0.55 <= ask <= max_a):
                continue

            b_key = (mid, target)
            if b_key in seen_buckets:
                continue
            seen_buckets.add(b_key)

            fee_meta = rec.get("fee_metadata") or {}
            fee_rate = float(fee_meta.get("fee_rate_market", 0.07) or 0.07)
            fee_exp = float(fee_meta.get("fee_exponent", 1.0) or 1.0)

            candidate_mids.add(mid)
            triggers.append({
                "market_id": mid,
                "title": rec.get("title", ""),
                "asset": str(rec.get("asset", "BTC")).upper(),
                "is_15m": is_15m,
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

    triggers.sort(key=lambda x: x["t0_unix"])

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

    for mid in candidate_mids:
        if mid not in telemetry_by_market or len(telemetry_by_market[mid]) == 0:
            telemetry_by_market[mid].extend(trigger_telem_by_market.get(mid, []))

    for mid in telemetry_by_market:
        telemetry_by_market[mid].sort(key=lambda x: x[0])

    variants = [
        "V0_CURRENT_WITH_BYPASS",
        "V1_REQUIRE_WRONGSIDE_GT_0",
        "V2_STRICT_WRONGSIDE_4_5BPS_6S",
        "V3_STRICT_WRONGSIDE_4_5BPS_12S",
        "V4_STRICT_WRONGSIDE_8BPS_12S",
        "V5_3ZONE_SALVAGE_ONLY",
    ]

    print("=" * 105)
    print("PART 1: BACKTEST REPLAY OF TODAY'S 7 LIVE POST-FIX TRADES (15:22 - 17:50 UTC)")
    print("=" * 105)
    for v in variants:
        tot_pnl = 0.0
        wins = 0
        details = []
        for pos in live_7:
            mid = str(pos["market_id"])
            t0 = float(pos["entry_ts"])
            exp_ts = float(pos["candle_expiry_ts"])
            target = pos["target_token"]
            entry_px = float(pos["entry_price"])
            open_sp = float(pos["candle_open_spot"])
            entry_sp = float(pos["entry_spot_ref"])
            raw_dist_pct = ((entry_sp - open_sp) / open_sp) * 100.0 if open_sp > 0 else 0.0
            s_dist_pct = raw_dist_pct if target == "UP" else -raw_dist_pct
            is_15m = pos.get("sleeve") == "SLEEVE_1_SUBHOURLY_15M"
            shares = float(pos["entry_shares"])
            notional = float(pos["notional_usd"])
            entry_fee = float(pos.get("fee_usd", 0.0) or 0.0)
            win_out = known_outcomes[mid]

            pnl, won, rsn, ex_px = simulate_position_path(
                telemetry_by_market[mid],
                t0, exp_ts, target, entry_px, s_dist_pct, is_15m,
                shares, notional, entry_fee, 0.07, 1.0, win_out, v,
            )
            tot_pnl += pnl
            if won:
                wins += 1
            details.append(f"{mid}({target}):${pnl:+.2f}[{rsn}@${ex_px:.2f}]")
        print(f"\n{v:32s} -> Wins={wins}/7 ({100*wins/7:4.1f}%) | NetPnL=${tot_pnl:+6.2f}")
        print("  " + " | ".join(details))

    print("\n" + "=" * 105)
    print(f"PART 2: FULL HISTORICAL DATASET BACKTEST (n={len(triggers)} qualified trades across 15m + 1h)")
    print("=" * 105)
    for subset_label, filter_fn in [
        ("ALL (15m + 1h Combined)", lambda tr: True),
        ("15m Subhourly (Sleeve 1)", lambda tr: tr["is_15m"]),
        ("1h Hourly (Sleeve 2)", lambda tr: not tr["is_15m"]),
    ]:
        sub_trigs = [t for t in triggers if filter_fn(t) and len(telemetry_by_market.get(t["market_id"], [])) > 0]
        print(f"\n--- {subset_label} (n={len(sub_trigs)} trades with full L2 telemetry) ---")
        for v in variants:
            pnls = []
            wins = 0
            premature_itm_dumps = 0
            for tr in sub_trigs:
                mid = tr["market_id"]
                win_out = resolutions[mid].get("winning_outcome")
                notional = 20.0
                shares = notional / tr["ask"]
                efee = calculate_taker_fee(notional, tr["ask"], tr["fee_rate"], tr["fee_exp"])
                pnl, won, rsn, ex_px = simulate_position_path(
                    telemetry_by_market[mid],
                    tr["t0_unix"], tr["expiry_ts"], tr["target"], tr["ask"],
                    tr["signed_dist"], tr["is_15m"], shares, notional, efee,
                    tr["fee_rate"], tr["fee_exp"], win_out, v,
                )
                pnls.append(pnl)
                if won:
                    wins += 1
                if rsn in ("HARD_BID_DROP_SALVAGE", "3ZONE_OPP_SALVAGE") and (tr["target"] == win_out) and pnl < 0:
                    premature_itm_dumps += 1
            n = len(pnls)
            tot = sum(pnls)
            wr = 100.0 * wins / max(1, n)
            avg = tot / max(1, n)
            print(
                f"  {v:32s}: n={n:3d} | WR={wr:5.1f}% | TotalPnL=${tot:+8.2f} | "
                f"Avg=${avg:+5.2f}/tr | FalseStopOnWinners={premature_itm_dumps:2d}"
            )


if __name__ == "__main__":
    main()

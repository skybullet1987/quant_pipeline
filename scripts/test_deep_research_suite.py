#!/usr/bin/env python3
"""
Empirical Verification Suite for the Gemini Deep Research Report Proposals
against the n=147 15m (Sleeve 1) and n=99 1h (Sleeve 2) recorded Polymarket trades.
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


def _student_t_cdf_nu6(z: float) -> float:
    if z == 0.0:
        return 0.5
    x = z / math.sqrt(6.0 + z * z)
    x2 = x * x
    poly = x * (1.0 + 0.5 * (1.0 - x2) + 0.375 * (1.0 - x2) * (1.0 - x2))
    return 0.5 + 0.5 * poly if z > 0 else 0.5 - 0.5 * float(abs(poly))


def compute_dr_raw_surface(asset: str, signed_cush_frac: float, tte_sec: float, shock_ofi: float) -> float:
    """Exact Section 2.3 function from the Deep Research report."""
    if signed_cush_frac <= 0.0 or tte_sec <= 5.0:
        return 0.0
    sigma_anchor = 0.0050 if asset.upper() == "BTC" else 0.0068
    tte_clamped = max(tte_sec, 10.0)
    sigma_rem = sigma_anchor * math.sqrt(tte_clamped / 900.0)
    decay_factor = 1.0 - math.exp(-(math.log(2.0) / 15.0) * tte_clamped)
    beta_ofi = 0.00065 if asset.upper() == "BTC" else 0.00085
    transient_drift_frac = (beta_ofi * abs(shock_ofi)) * decay_factor
    z_eff = (signed_cush_frac + transient_drift_frac) / sigma_rem
    p_true = _student_t_cdf_nu6(z_eff)
    delta_min = 0.020 + 0.015 * math.sqrt(tte_clamped / 900.0)
    target_cost_cap = p_true - delta_min
    if target_cost_cap <= 0.01:
        return 0.0
    r_fee = 0.07
    discriminant = (1.0 + r_fee) ** 2 - 4.0 * r_fee * target_cost_cap
    raw_ask_max = ((1.0 + r_fee) - math.sqrt(max(0.0, discriminant))) / (2.0 * r_fee)
    ask_max = min(0.78, max(0.0, raw_ask_max))
    return ask_max if ask_max >= 0.55 else 0.0


def compute_stoikov_micro_price(bid: float, ask: float, obi_l1: float) -> float:
    """Section 6.1 Stoikov Martingale Micro-Price approximation."""
    if bid <= 0 or ask <= 0 or ask <= bid:
        return ask
    mid = 0.5 * (bid + ask)
    spread = ask - bid
    i_tilde = 0.5 * max(-1.0, min(1.0, obi_l1))  # in [-0.5, 0.5]
    if spread <= 0.015:
        a1, a3 = 0.72, 0.96
    else:
        a1, a3 = 0.58, 0.64
    return mid + spread * (a1 * i_tilde + a3 * (i_tilde ** 3))


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
            opp_tf = features.get("DOWN" if target == "UP" else "UP") or {}
            ask = float(tf.get("vwap_$20") or tf.get("best_ask") or 0.0)
            best_ask = float(tf.get("best_ask") or ask)
            bid = float(tf.get("best_bid") or 0.0)
            obi_l1 = float(tf.get("obi_l1") or 0.0)
            obi_depth = float(tf.get("obi_depth") or 0.0)
            age_ask_ms = float(tf.get("age_ask_ms") or 500.0)
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
                "best_ask": best_ask,
                "bid": bid,
                "opp_bid": float(opp_tf.get("best_bid") or 0.0),
                "opp_ask": float(opp_tf.get("best_ask") or 0.0),
                "obi_l1": obi_l1,
                "obi_depth": obi_depth,
                "age_ask_ms": age_ask_ms,
                "shock_ofi": shock_ofi,
                "signed_dist": signed_dist,
                "candle_sigma": float(rec.get("candle_sigma") or 0.0),
                "fee_rate": fee_rate,
                "fee_exp": fee_exp,
            })

    for mid in trigger_telem:
        trigger_telem[mid].sort(key=lambda x: x[0])

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
        tr["ex_px"] = ex_px
        tr["shares"] = shares

    print("=" * 110)
    print("TEST 1: DEEP RESEARCH SECTION 2.3 RAW SURFACE vs. HYBRID / MICROSTRUCTURE GATES ON 15M (n=147)")
    print("=" * 110)

    def eval_rule(name, filter_fn, size_fn=None):
        total_pnl = 0.0
        wins = 0
        losses = 0
        gp = 0.0
        gl = 0.0
        t9_kept = False
        t8_kept = False
        for tr in triggers_15m:
            if not filter_fn(tr):
                continue
            mult = size_fn(tr) if size_fn else 1.0
            p = tr["pnl"] * mult
            total_pnl += p
            if tr["won"]:
                wins += 1
                gp += max(0.0, p)
            else:
                losses += 1
                gl += abs(min(0.0, p))
            if tr["market_id"] == "6022563":
                t9_kept = True
            if tr["market_id"] == "6019058":
                t8_kept = True
        n = wins + losses
        wr = (wins / n * 100.0) if n else 0.0
        avg = (total_pnl / n) if n else 0.0
        pf = (gp / gl) if gl > 0 else 99.9
        print(
            f"{name:<52} | n={n:3d} ({wins:3d}W/{losses:2d}L) | WR={wr:5.1f}% | "
            f"PnL=${total_pnl:+7.2f} | Avg=${avg:+5.2f} | PF={pf:4.2f}x | T8:{'Y' if t8_kept else 'N'} T9:{'Y' if t9_kept else 'N'}"
        )

    # 1. Baseline C0
    eval_rule("C0_BASELINE (cush>=0.06%, ask<=0.78)", lambda tr: True)

    # 2. Deep Research Raw Section 2.3 Surface (uncalibrated pure diffusion)
    eval_rule(
        "DR_RAW_SEC2.3 (Pure Diffusion Student-t Ask_max)",
        lambda tr: tr["ask"] <= compute_dr_raw_surface(tr["asset"], tr["signed_dist"] / 100.0, tr["tte"], tr["shock_ofi"]),
    )

    # 3. Why did Trade #9 fail? Check TTE x Cushion x Ask interaction!
    # Notice Trade #9 had TTE=534s (>450s), cush=0.061% (<0.08%), ask=$0.763 (>0.68)!
    eval_rule(
        "H1_EARLY_CANDLE_CAP (if TTE>420s & cush<0.09%: ask<=0.68)",
        lambda tr: not (tr["tte"] > 420.0 and tr["signed_dist"] < 0.09 and tr["ask"] > 0.68),
    )
    eval_rule(
        "H2_EARLY_CANDLE_CAP (if TTE>360s & cush<0.08%: ask<=0.68)",
        lambda tr: not (tr["tte"] > 360.0 and tr["signed_dist"] < 0.08 and tr["ask"] > 0.68),
    )

    # 4. Stoikov Micro-Price + Thin Cushion Gate
    eval_rule(
        "H3_STOIKOV_MICRO + EARLY_CAP (TTE>420s & cush<0.09% -> .68)",
        lambda tr: (
            not (tr["tte"] > 420.0 and tr["signed_dist"] < 0.09 and tr["ask"] > 0.68)
            and not (tr["signed_dist"] < 0.08 and tr["obi_l1"] < -0.35 and tr["ask"] > 0.68)
        ),
    )

    # 5. Bayesian Market-Prior + Diffusion Quadratic Surface (Fixing Deep Research's 0.50 prior flaw!)
    def bayesian_surface_ok(tr):
        # Blend market mid/Stoikov micro-price with Student-t diffusion + time-decay penalty
        p_micro = compute_stoikov_micro_price(tr["bid"], tr["best_ask"], tr["obi_l1"])
        sigma_anchor = 0.0050 if tr["asset"] == "BTC" else 0.0068
        sigma_rem = sigma_anchor * math.sqrt(max(tr["tte"], 15.0) / 900.0)
        c_frac = tr["signed_dist"] / 100.0
        z_eff = (c_frac + 0.0012 * tr["shock_ofi"]) / sigma_rem
        p_diff = _student_t_cdf_nu6(z_eff)
        # Weight diffusion heavily when TTE is high (>420s), weight market micro-price when TTE <= 420s
        w_diff = 0.65 if tr["tte"] > 420.0 else 0.25
        p_post = w_diff * p_diff + (1.0 - w_diff) * max(p_micro, p_diff)
        # Quadratic fee check
        r_fee = 0.07
        cost = tr["ask"] + r_fee * tr["ask"] * (1.0 - tr["ask"])
        return (p_post - cost) >= -0.015

    eval_rule("H4_BAYESIAN_STOIKOV_SURFACE (Prior=P_micro + Student-t)", bayesian_surface_ok)

    # 6. Dynamic Sizing: Full size normally, 0.5x in the (0.06-0.08% x $0.68-$0.73) pocket, block TTE>420s thin high-ask
    eval_rule(
        "H5_HYBRID_BEST (H1_EARLY_CAP + 0.5x weak cell $0.68-$0.73)",
        lambda tr: not (tr["tte"] > 420.0 and tr["signed_dist"] < 0.09 and tr["ask"] > 0.68),
        lambda tr: 0.5 if (tr["signed_dist"] < 0.08 and 0.68 < tr["ask"] <= 0.73) else 1.0,
    )

    print("\n" + "=" * 110)
    print("TEST 2: DEEP RESEARCH SECTION 5 (SYNTHETIC BOX LOCK: BUY OPPOSITE + MERGE) ON SALVAGE & EXITS")
    print("=" * 110)
    # Check all salvage/ratchet exits in 15m and quantify Synthetic Box Lock gain
    salvage_trades = [tr for tr in triggers_15m if tr["rsn"] != "EXPIRY"]
    box_gain_total = 0.0
    for tr in salvage_trades:
        # Under Synthetic Box Lock, zero-cancel saves ~3.5c of crash slippage on HARD_BID_DROP_SALVAGE
        # plus any complementary book tightness
        if "SALVAGE" in tr["rsn"]:
            gain = tr["shares"] * 0.035
        else:
            gain = tr["shares"] * 0.010
        box_gain_total += gain
    print(f"Early/Salvage Exits in 15m: {len(salvage_trades)} trades")
    print(f"Estimated Synthetic Box Lock Recovery Gain (0ms cancel wait + CTF merge): +${box_gain_total:.2f} (+${box_gain_total/max(1,len(salvage_trades)):.2f}/salvage)")

    # Print breakdown of the 18 losses in C0 by TTE and Cushion
    print("\n" + "=" * 110)
    print("TEST 3: 15M PERFORMANCE BY TTE HORIZON & EARLY-CANDLE CUSHION GATES")
    print("=" * 110)
    bands = [
        ("30s - 300s (Late 15m)", 30.0, 300.0),
        ("300s - 450s (Mid 15m)", 300.0, 450.0),
        ("450s - 525s (Early-Mid)", 450.0, 525.0),
        ("525s - 600s (Very Early)", 525.0, 601.0),
    ]
    for bname, lo, hi in bands:
        eval_rule(bname, lambda tr, lo=lo, hi=hi: lo <= tr["tte"] < hi)

    print("-" * 110)
    eval_rule("SLICE_A: TTE <= 470s (All cushions >= 0.06%)", lambda tr: tr["tte"] <= 470.0)
    eval_rule("SLICE_B: TTE > 470s & cush < 0.09%", lambda tr: tr["tte"] > 470.0 and tr["signed_dist"] < 0.09)
    eval_rule("SLICE_C: TTE > 470s & cush >= 0.09%", lambda tr: tr["tte"] > 470.0 and tr["signed_dist"] >= 0.09)
    eval_rule(
        "RULE_TTE_CUSH_1: TTE<=470s OR cush>=0.09%",
        lambda tr: tr["tte"] <= 470.0 or tr["signed_dist"] >= 0.09,
    )
    eval_rule(
        "RULE_TTE_CUSH_2: TTE<=470s OR (cush>=0.09% & ask<=0.73)",
        lambda tr: tr["tte"] <= 470.0 or (tr["signed_dist"] >= 0.09 and tr["ask"] <= 0.73),
    )
    eval_rule(
        "RULE_TTE_CUSH_3: TTE<=470s OR ask<=0.66 OR cush>=0.09%",
        lambda tr: tr["tte"] <= 470.0 or tr["ask"] <= 0.66 or tr["signed_dist"] >= 0.09,
    )
    eval_rule(
        "COMBO_1: RULE_TTE_CUSH_1 + MM_RELOAD_VETO (age<25ms & obi<-0.25)",
        lambda tr: (tr["tte"] <= 470.0 or tr["signed_dist"] >= 0.09)
        and not (tr["age_ask_ms"] < 25.0 and tr["obi_l1"] < -0.25),
    )
    eval_rule(
        "COMBO_2: RULE_TTE_CUSH_3 + MM_RELOAD_VETO (age<25ms & obi<-0.25)",
        lambda tr: (tr["tte"] <= 470.0 or tr["ask"] <= 0.66 or tr["signed_dist"] >= 0.09)
        and not (tr["age_ask_ms"] < 25.0 and tr["obi_l1"] < -0.25),
    )


if __name__ == "__main__":
    main()

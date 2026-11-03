"""
Order-Flow Walk-Forward Simulators & Shadow-to-Live Legging Parity Engines (v4.0)
=================================================================================
Zero-live-risk quantitative simulation engines for calibrating multi-step order-flow
sequences and multi-leg D1 Dominance Box execution without N=1 live parameter tweaking:

  1. `simulate_microclip_cascade_entry`:
     100ms micro-clip cascade replay with trade-print / L1 queue depletion across all 4
     live directional entry steps:
       - Step 1: Primary Smart FAK (`best_ask + fak_buffer` capped at `max_px`)
       - Step 2: Idea #1 Elastic Down-Snap (`$16.50 -> $12.00` rung when L1 depth is thin)
       - Step 3: Idea #5 Sequential `+2c` FAK Retry (`eff_z >= 1.25` on `FAK_KILLED_NO_MATCH`)
       - Step 4: Phase 3A Passive `GTC postOnly` Maker-In (`0%` fee, `3.5s` TTL, `100ms`
                 adverse-spot shield canceling immediately on `> 50%` cushion decay)

  2. `simulate_d1_box_with_latency_skew` & `calibrate_d1_box_wfo`:
     Asynchronous 2-leg D1 Dominance Box simulator across inter-leg skew `delta_t_ms` in
     `[0ms, 400ms]`, comparing `fragile_first` (`depth_ratio_threshold`, `15m/5m` before `4h`)
     vs `parallel_2leg`, and calibrating Stage-1 / Stage-2 legged-out unwind giveback caps
     via chronological Purged Train -> Embargo -> Validation -> Embargo -> Sealed Holdout.

  3. `compute_d1_legging_drag_haircut`:
     Empirical `15%-25%` thin-book asymmetric leg-miss + `-2c` unwind slip + `2x` V2 taker-fee
     drag haircut enforcing Shadow-vs-Live EV parity in `alpha_124_shadow_daemon.py` and
     8/8 live graduation gating in `polymarket_live_harvester.py`.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DEFAULT_FEE_RATE = 0.07


def v2_taker_fee_per_share(px: float, fee_rate: float = DEFAULT_FEE_RATE, fee_exponent: float = 1.0) -> float:
    """Polymarket V2 nonlinear taker fee per share (`rate * (p * (1 - p)) ** exp`)."""
    if fee_rate <= 0.0:
        return 0.0
    px_c = max(0.001, min(0.999, float(px)))
    return float(fee_rate) * ((px_c * (1.0 - px_c)) ** float(fee_exponent))


def build_candidate_micro_clips(cand: Dict[str, Any]) -> List[Tuple[float, float, float, float]]:
    """
    Returns chronologically sorted `(elapsed_sec, cushion, bid, ask)` micro-clips over `[0.05s, 6.0s]`.
    Uses explicit `cand["micro_clips"]` (`100ms, 250ms, 500ms, 1s, 5s` recorder impulse clips) when
    present, falling back deterministically to `ask_500ms`, `ask_1000ms`, and early `cand["path"]` ticks.
    """
    raw_mc = cand.get("micro_clips")
    if isinstance(raw_mc, (list, tuple)) and raw_mc:
        out = [
            (float(r[0]), float(r[1]), float(r[2]), float(r[3]))
            for r in raw_mc
            if isinstance(r, (list, tuple)) and len(r) >= 4 and float(r[0]) > 0.0
        ]
        if out:
            out.sort(key=lambda x: x[0])
            return out

    eff_cush = float(cand.get("cushion_oracle", cand.get("cushion_min", 0.0)) or 0.0)
    bid_t0 = float(cand.get("bid_t0", 0.0) or 0.0)
    ask_t0 = float(cand.get("ask_t0", 1.0) or 1.0)
    ask_500 = float(cand.get("ask_500ms") or ask_t0)
    ask_1000 = float(cand.get("ask_1000ms") or ask_500)
    tte0 = float(cand.get("tte", 300.0) or 300.0)

    synthesized: List[Tuple[float, float, float, float]] = [
        (0.10, eff_cush, bid_t0, round(0.5 * (ask_t0 + ask_500), 4)),
        (0.25, eff_cush, bid_t0, round(0.25 * ask_t0 + 0.75 * ask_500, 4)),
        (0.50, eff_cush, max(0.01, round(ask_500 - max(0.01, ask_t0 - bid_t0), 4)), ask_500),
        (1.00, eff_cush, max(0.01, round(ask_1000 - max(0.01, ask_t0 - bid_t0), 4)), ask_1000),
    ]
    for row in cand.get("path") or ():
        if len(row) < 4:
            continue
        dt_p = round(max(0.0, tte0 - float(row[0])), 3)
        if 1.05 <= dt_p <= 6.0:
            synthesized.append((dt_p, float(row[1]), float(row[2]), float(row[3])))
    synthesized.sort(key=lambda x: x[0])
    return synthesized


def _clip_at_or_after(
    clips: Sequence[Tuple[float, float, float, float]],
    target_dt: float,
    fallback: Tuple[float, float, float, float],
) -> Tuple[float, float, float, float]:
    for cl in clips:
        if cl[0] >= target_dt - 1e-6:
            return cl
    return clips[-1] if clips else fallback


def simulate_microclip_cascade_entry(
    cand: Dict[str, Any],
    cfg: Dict[str, Any],
    latency_mode: str = "500ms",
) -> Optional[Tuple[float, float, float, float, str]]:
    """
    Simulates the 4-step directional entry cascade with 100ms micro-clip trade-print queue depletion.

    Returns:
      `(fill_px, entry_fee_per_share, fill_elapsed_sec, size_mult, step_tag)` or `None` if unfilled/vetoed.
    """
    ask_t0 = float(cand.get("ask_t0", 1.0) or 1.0)
    bid_t0 = float(cand.get("bid_t0", 0.0) or 0.0)
    min_px = float(cfg.get("min_px", 0.52))
    max_px = float(cfg.get("max_px", 0.85))
    fak_buffer = float(cfg.get("fak_buffer", 0.02))
    fee_rate = float(cfg.get("fee_rate", DEFAULT_FEE_RATE))

    ticket_usd = max(5.0, float(cfg.get("cascade_ticket_usd", 16.50)))
    elastic_usd = max(5.0, min(ticket_usd, float(cfg.get("elastic_downsnap_usd", 12.00))))
    fallback_min_z = float(cfg.get("fallback_2c_min_z", 1.25))
    fallback_add = float(cfg.get("fallback_2c_add", 0.02))
    enable_elastic = bool(cfg.get("enable_elastic_downsnap", True))
    enable_fb_2c = bool(cfg.get("enable_fallback_2c", True))
    enable_phase3a = bool(cfg.get("enable_phase3a_rescue", True))
    phase3a_ttl_s = max(0.20, float(cfg.get("phase3a_ttl_s", 3.5)))
    shield_decay = min(0.95, max(0.10, float(cfg.get("phase3a_spot_shield_decay", 0.50))))

    eff_cush = float(
        cand.get("cushion_oracle", cand.get("cushion_min", 0.0))
        if cfg.get("use_cl_proxy", True)
        else cand.get("cushion_min", 0.0)
    )
    eff_z = float(
        cand.get("z_oracle", cand.get("z_cushion", 0.0))
        if cfg.get("use_cl_proxy", True)
        else cand.get("z_cushion", 0.0)
    )
    l1_ask_usd = float(cand.get("l1_ask_usd", ticket_usd) or 0.0)
    slip20 = max(0.0, float(cand.get("slip20_t0", 0.0) or 0.0))
    shock_vol = float(cand.get("shock_vol", 0.0) or 0.0)

    clips = build_candidate_micro_clips(cand)
    lat_s = 0.50 if latency_mode == "500ms" else 1.00
    lat_ask_direct = float(cand.get("ask_500ms" if latency_mode == "500ms" else "ask_1000ms") or ask_t0)
    lat_clip = _clip_at_or_after(clips, lat_s, (lat_s, eff_cush, bid_t0, lat_ask_direct))
    ask_lat = lat_ask_direct if cand.get("micro_clips") is None else float(lat_clip[3])
    cush_lat = float(lat_clip[1])
    bid_lat = float(lat_clip[2]) if float(lat_clip[2]) > 0.0 else max(0.01, round(ask_lat - max(0.01, ask_t0 - bid_t0), 4))

    # Adverse collapse guard parity: never buy into a >= 4c ask collapse from t0
    if (ask_t0 - ask_lat) >= 0.04:
        return None

    # Trade-print queue depletion penalty when shock volume sweeps thin L1 asks during transit
    depletion_ticks = 0.01 if (shock_vol >= 450_000.0 and l1_ask_usd < ticket_usd * 1.50) else 0.0
    eff_ask_lat = round(min(0.99, ask_lat + depletion_ticks), 4)

    target_limit_px = round(min(max_px, ask_t0 + fak_buffer), 4)
    hybrid_z_split = bool(cfg.get("hybrid_z_split", False))
    z_taker_cut = float(cfg.get("z_taker_cut", 1.20))
    route_maker_first = hybrid_z_split and eff_z < z_taker_cut

    if not route_maker_first:
        # STEP 1: Primary Smart FAK at full ticket (`$16.50`)
        if 0.0 < eff_ask_lat < 0.99 and l1_ask_usd >= ticket_usd:
            vwap_full = round(max(eff_ask_lat, ask_t0 + min(0.03, slip20)), 4)
            if vwap_full <= target_limit_px and vwap_full <= max_px:
                return (vwap_full, v2_taker_fee_per_share(vwap_full, fee_rate), lat_s, 1.0, "STEP1_SMART_FAK")

        # STEP 2: Idea #1 Elastic Down-Snap (`$16.50 -> $12.00 -> $8.00`) when L1 depth blocks full ticket
        if enable_elastic and 0.0 < eff_ask_lat < 0.99:
            min_elastic_usd = float(cfg.get("min_elastic_usd", elastic_usd))
            for rung_usd in (elastic_usd, min_elastic_usd):
                if rung_usd < ticket_usd and l1_ask_usd >= rung_usd - 1e-6:
                    scale_r = round(rung_usd / ticket_usd, 4)
                    vwap_elastic = round(max(eff_ask_lat, ask_t0 + min(0.02, slip20 * scale_r)), 4)
                    if vwap_elastic <= target_limit_px and vwap_elastic <= max_px:
                        return (
                            vwap_elastic,
                            v2_taker_fee_per_share(vwap_elastic, fee_rate),
                            round(lat_s + 0.05, 3),
                            scale_r,
                            "STEP2_ELASTIC_DOWNSNAP",
                        )

        # STEP 3: Idea #5 Sequential `+2c` Pre-Signed FAK Retry (`z_strike >= 1.25` on FAK zero-match miss)
        if (
            enable_fb_2c
            and eff_z >= fallback_min_z
            and (target_limit_px + 0.01) <= (max_px + 1e-6)
            and l1_ask_usd >= elastic_usd
        ):
            fb_limit_px = round(min(max_px, target_limit_px + fallback_add), 4)
            if fb_limit_px > target_limit_px + 1e-6:
                t_fb = round(lat_s + 0.15, 3)
                fb_clip = _clip_at_or_after(clips, t_fb, (t_fb, cush_lat, bid_lat, eff_ask_lat))
                ask_fb = round(min(0.99, float(fb_clip[3]) + depletion_ticks), 4)
                if (ask_t0 - ask_fb) >= 0.04:
                    return None
                fb_mult = 1.0 if l1_ask_usd >= ticket_usd else round(elastic_usd / ticket_usd, 4)
                vwap_fb = round(max(ask_fb, ask_t0 + min(0.03, slip20 * fb_mult)), 4)
                if 0.0 < ask_fb < 0.99 and vwap_fb <= fb_limit_px and vwap_fb <= max_px:
                    return (
                        vwap_fb,
                        v2_taker_fee_per_share(vwap_fb, fee_rate),
                        t_fb,
                        fb_mult,
                        "STEP3_FAK_PLUS_2C_FALLBACK",
                    )

    # STEP 4: Passive `GTC postOnly=True` Maker-In (Shielded Maker-First for marginal z or Phase 3A Rescue)
    if not enable_phase3a and not route_maker_first:
        return None
    t_p3a_start = round(lat_s + (0.05 if route_maker_first else 0.20), 3)
    p3a_init = _clip_at_or_after(clips, t_p3a_start, (t_p3a_start, cush_lat, bid_lat, eff_ask_lat))
    ask_reb = float(p3a_init[3])
    bid_reb = float(p3a_init[2]) if float(p3a_init[2]) > 0.0 else bid_lat
    cush_init = float(p3a_init[1])
    if eff_cush > 0.0 and cush_init < eff_cush * (1.0 - shield_decay):
        return None
    if ask_reb <= min_px + 0.005 or (ask_t0 - ask_reb) >= 0.04:
        return None

    # postOnly resting bid strictly >= 1 tick below ask_reb and within [min_px, max_px]
    if route_maker_first:
        spread_reb = round(ask_reb - bid_reb, 4)
        maker_px = round(min(max_px, ask_reb - 0.01, bid_reb + (0.01 if spread_reb >= 0.02 else 0.0)), 2)
    else:
        maker_px = round(min(max_px, ask_reb - 0.01, max(bid_reb, ask_t0)), 2)
    if maker_px < min_px or maker_px >= ask_reb - 1e-6:
        return None

    # 1-tick join queue-depth cap (`<= $45` ahead at L1 when not improving bid)
    use_comp_shield = bool(cfg.get("use_complement_shield", route_maker_first))
    max_join_queue_usd = float(cfg.get("max_maker_join_queue_usd", 45.0))
    l1_bid_usd = float(cand.get("l1_bid_usd", 0.0) or 0.0)
    if use_comp_shield and maker_px <= bid_reb + 1e-6 and l1_bid_usd > max_join_queue_usd:
        return None

    opp_clips = {
        round(float(r[0]), 3): float(r[4])
        for r in (cand.get("micro_clips_opp") or cand.get("micro_clips") or ())
        if isinstance(r, (list, tuple)) and len(r) >= 5 and float(r[4]) > 0.0
    }
    opp_bid_t0 = float(cand.get("opp_bid_t0", 0.0) or 0.0)
    if use_comp_shield and opp_bid_t0 > 0.0 and round(1.0 - opp_bid_t0, 4) <= maker_px - 1e-6:
        return None

    maker_fee_ps = (
        -0.20 * v2_taker_fee_per_share(maker_px, fee_rate)
        if bool(cfg.get("include_maker_rebate", False))
        else 0.0
    )
    eff_ttl_s = float(cfg.get("maker_ttl_s", 6.0)) if route_maker_first else phase3a_ttl_s
    p3a_mult = 1.0 if l1_ask_usd >= ticket_usd else round(elastic_usd / ticket_usd, 4)
    t_deadline = t_p3a_start + eff_ttl_s
    step_lbl = "HYBRID_MAKER_FIRST" if route_maker_first else "STEP4_PHASE3A_MAKER_RESCUE"
    for dt_c, cush_c, b_c, a_c in clips:
        if dt_c < t_p3a_start - 1e-6:
            continue
        if dt_c > t_deadline + 1e-6:
            break
        # 100ms Adverse-Spot Shield: cancel immediately BEFORE passive toxic fill if cushion decays > 50%
        if eff_cush > 0.0 and (cush_c <= 0.0 or cush_c < eff_cush * (1.0 - shield_decay)):
            return None
        # Complement-Book HFT Repricing Shield (`1 - opp_bid < maker_px` or pre-fill lead `1 - opp_bid <= maker_px` while `ask > maker_px`)
        if use_comp_shield:
            opp_b_now = opp_clips.get(round(dt_c, 3), 0.0)
            if opp_b_now > 0.0:
                comp_ask = round(1.0 - opp_b_now, 4)
                if comp_ask <= maker_px - 1e-6 or (a_c > maker_px + 1e-6 and comp_ask <= maker_px + 1e-6):
                    return None
        # Queue-depletion passive fill: ask crosses down to/through maker_px while shields hold
        if 0.0 < a_c <= maker_px:
            return (maker_px, round(maker_fee_ps, 6), round(dt_c, 3), p3a_mult, step_lbl)

    return None


def compute_d1_legging_drag_haircut(
    shares: float,
    box_cost_net: float,
    avail_a_shares: float,
    avail_b_shares: float,
    px_a: float,
    px_b: float,
    fee_rate_a: float = DEFAULT_FEE_RATE,
    fee_rate_b: float = DEFAULT_FEE_RATE,
    is_4h_mixed: bool = False,
    is_zero_itode: bool = False,
    unwind_slip_cents: float = 0.02,
) -> Dict[str, float]:
    """
    Computes empirical asymmetric leg-miss + `-2c` unwind + `2x` V2 taker-fee drag haircut for D1 boxes.
    Enforces Shadow-vs-Live parity so thin-book boxes (`min(avail_a, avail_b) < 1.5x * shares`) or mixed
    `4h` itode pairs cannot inflate unadjusted shadow EV or prematurely trigger 8/8 live graduation.
    """
    sh = max(1.0, float(shares))
    min_avail = min(max(0.0, float(avail_a_shares)), max(0.0, float(avail_b_shares)))
    depth_mult = min_avail / sh

    if depth_mult < 1.15:
        p_miss = 0.22
    elif depth_mult < 1.50:
        p_miss = 0.16
    elif depth_mult < 2.25:
        p_miss = 0.05
    else:
        p_miss = 0.015

    if is_zero_itode:
        p_miss *= 0.40
    if is_4h_mixed:
        p_miss = min(0.35, p_miss + 0.05)

    px_mid = max(0.02, min(0.98, 0.5 * (float(px_a) + float(px_b))))
    fr_mid = max(0.0, 0.5 * (float(fee_rate_a) + float(fee_rate_b)))
    fee_in = v2_taker_fee_per_share(px_mid, fr_mid)
    px_uw = max(0.01, px_mid - float(unwind_slip_cents))
    fee_out = v2_taker_fee_per_share(px_uw, fr_mid)
    unwind_loss_ps = float(unwind_slip_cents) + fee_in + fee_out

    drag_per_pair = p_miss * unwind_loss_ps
    gross_floor_per_pair = 1.0 - float(box_cost_net)
    adj_ev_per_pair = gross_floor_per_pair - drag_per_pair

    return {
        "min_depth_mult": round(depth_mult, 4),
        "p_leg_miss": round(p_miss, 4),
        "unwind_loss_per_share": round(unwind_loss_ps, 5),
        "legging_drag_per_pair": round(drag_per_pair, 5),
        "legging_drag_usd": round(sh * drag_per_pair, 4),
        "gross_floor_per_pair": round(gross_floor_per_pair, 5),
        "legging_adjusted_net_ev_per_pair": round(adj_ev_per_pair, 5),
        "legging_adjusted_min_profit_usd": round(sh * adj_ev_per_pair, 4),
    }


def simulate_d1_box_with_latency_skew(
    box_cand: Dict[str, Any],
    policy_cfg: Dict[str, Any],
    delta_t_ms: float = 150.0,
) -> Dict[str, Any]:
    """
    Simulates asynchronous 2-leg D1 Dominance Box execution under inter-leg latency skew `delta_t_ms` (`[0, 400]`).
    Compares `fragile_first` vs `parallel_2leg` routing and Stage-1 / Stage-2 legged-out unwind giveback caps.
    """
    sh = max(5.0, float(box_cand.get("shares", 12.0)))
    px_a = float(box_cand.get("leg_a_limit_price", 0.48))
    px_b = float(box_cand.get("leg_b_limit_price", 0.48))
    avail_a = float(box_cand.get("leg_a_avail_shares", sh * 2.0))
    avail_b = float(box_cand.get("leg_b_avail_shares", sh * 2.0))
    hz_a = str(box_cand.get("leg_a_horizon", "15m")).lower()
    hz_b = str(box_cand.get("leg_b_horizon", "5m")).lower()
    fr_a = float(box_cand.get("leg_a_fee_rate", DEFAULT_FEE_RATE))
    fr_b = float(box_cand.get("leg_b_fee_rate", DEFAULT_FEE_RATE))
    box_cost_net = float(box_cand.get("box_cost_net") or (px_a + px_b + v2_taker_fee_per_share(px_a, fr_a) + v2_taker_fee_per_share(px_b, fr_b)))
    corridor_hit = bool(box_cand.get("corridor_jackpot", False))

    min_depth_gate = float(policy_cfg.get("min_depth_mult_gate", 1.50))
    depth_ratio_thresh = float(policy_cfg.get("depth_ratio_threshold", 1.35))
    routing_mode = str(policy_cfg.get("routing_mode", "hybrid_auto"))
    max_giveback_frac = float(policy_cfg.get("max_giveback_frac", 0.35))
    max_box_cost = float(policy_cfg.get("max_box_cost_net", 0.985))

    min_avail = min(avail_a, avail_b)
    max_avail = max(avail_a, avail_b)
    if box_cost_net > max_box_cost or (min_avail / sh) < min_depth_gate:
        return {"entered": False, "outcome": "GATED_OUT", "pnl_usd": 0.0, "legged_out": False}

    is_4h_mixed = ("4h" in (hz_a, hz_b)) and (hz_a != hz_b)
    asym_ratio = max_avail / max(min_avail, 1e-6)
    if routing_mode == "fragile_first":
        use_fragile_first = True
    elif routing_mode == "parallel_2leg":
        use_fragile_first = False
    else:
        use_fragile_first = bool(is_4h_mixed or asym_ratio >= depth_ratio_thresh or box_cost_net > 0.975)

    # Order legs so leg_1 is the fragile / sub-hourly leg when `use_fragile_first`
    a_first = True
    if is_4h_mixed:
        a_first = (hz_a != "4h")
    elif avail_b < avail_a:
        a_first = False

    if a_first:
        l1 = (px_a, avail_a, fr_a, float(box_cand.get("depletion_a_per_s", 18.0)), float(box_cand.get("bid_drop_a", 0.02)))
        l2 = (px_b, avail_b, fr_b, float(box_cand.get("depletion_b_per_s", 10.0)), float(box_cand.get("bid_drop_b", 0.02)))
    else:
        l1 = (px_b, avail_b, fr_b, float(box_cand.get("depletion_b_per_s", 18.0)), float(box_cand.get("bid_drop_b", 0.02)))
        l2 = (px_a, avail_a, fr_a, float(box_cand.get("depletion_a_per_s", 10.0)), float(box_cand.get("bid_drop_a", 0.02)))

    base_transit_s = float(box_cand.get("base_transit_s", 0.12))
    skew_s = max(0.0, float(delta_t_ms) / 1000.0)

    if use_fragile_first:
        rem_l1 = l1[1] - l1[3] * base_transit_s
        if rem_l1 < sh:
            # Fragile-first aborts cleanly before sending Leg 2 -> $0.00 unwind loss!
            return {"entered": False, "outcome": "LEG1_CLEAN_ABORT", "pnl_usd": 0.0, "legged_out": False}
        rem_l2 = l2[1] - l2[3] * (base_transit_s + skew_s)
        filled_leg = l1
        leg2_ok = rem_l2 >= sh
    else:
        # Parallel 2-leg: minimal inter-leg skew (25% residual network jitter), but if fragile leg misses,
        # thick leg still fills and forces an immediate legged-out unwind!
        rem_l1 = l1[1] - l1[3] * (base_transit_s + 0.25 * skew_s)
        rem_l2 = l2[1] - l2[3] * (base_transit_s + 0.25 * skew_s)
        if rem_l1 >= sh and rem_l2 >= sh:
            leg2_ok = True
            filled_leg = l1
        elif rem_l1 < sh and rem_l2 < sh:
            return {"entered": False, "outcome": "BOTH_MISSED_CLEAN", "pnl_usd": 0.0, "legged_out": False}
        else:
            leg2_ok = False
            filled_leg = l1 if rem_l1 >= sh else l2

    if leg2_ok:
        payout_per_pair = 2.0 if corridor_hit else 1.0
        pnl = round(sh * (payout_per_pair - box_cost_net), 4)
        return {"entered": True, "outcome": "BOX_LOCKED", "pnl_usd": pnl, "legged_out": False}

    # Legged-out unwind: Stage-1 (`px_1 - stage1_cap`) vs Stage-2 (`px_1 * 0.85`)
    px_1, _, fr_1, _, mkt_bid_drop = filled_leg
    fee_in = v2_taker_fee_per_share(px_1, fr_1)
    gross_edge_ps = max(0.01, 1.0 - box_cost_net)
    stage1_cap_drop = max(0.01, min(0.03, max_giveback_frac * gross_edge_ps * 2.0))
    live_bid_uw = max(0.02, round(px_1 - mkt_bid_drop, 4))
    stage1_floor = round(max(0.02, px_1 - stage1_cap_drop), 4)

    if live_bid_uw >= stage1_floor:
        uw_px = live_bid_uw
        uw_stage = "LEGGED_OUT_STAGE1"
    else:
        # Stage 1 misses when bid dropped past Stage-1 cap; Stage 2 sweeps delayed market bid (`-1.5c` extra decay)
        uw_px = max(0.02, round(max(px_1 * 0.85, live_bid_uw - 0.015), 4))
        uw_stage = "LEGGED_OUT_STAGE2"

    fee_out = v2_taker_fee_per_share(uw_px, fr_1)
    pnl_uw = round(sh * ((uw_px - px_1) - fee_in - fee_out), 4)
    return {"entered": True, "outcome": uw_stage, "pnl_usd": pnl_uw, "legged_out": True}


def _default_d1_calibration_events(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if data_dir is not None:
        cand_p = Path(data_dir) / "d1_live_box_candidates.jsonl"
        if cand_p.exists():
            try:
                raw_lines = cand_p.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                raw_lines = []
            for ln in raw_lines:
                if not ln.strip():
                    continue
                # Per-line parse: one torn/corrupt line must not discard the whole calibration file
                try:
                    d = json.loads(ln)
                    if not isinstance(d, dict):
                        continue
                    sh = max(5.0, float(d.get("shares") or 12.0))
                    av_a = float(d.get("leg_a_avail_shares") or sh * 1.8)
                    av_b = float(d.get("leg_b_avail_shares") or sh * 1.8)
                    events.append({
                        **d,
                        "depletion_a_per_s": round(max(4.0, 0.32 * av_a), 2),
                        "depletion_b_per_s": round(max(4.0, 0.24 * av_b), 2),
                        "bid_drop_a": 0.02 if float(d.get("box_cost_net") or 0.98) <= 0.98 else 0.03,
                        "bid_drop_b": 0.02,
                    })
                except Exception:
                    continue
    if len(events) >= 36:
        return events

    # Deterministic 60-event structural stress corpus spanning thick, asymmetric, thin-book, and 4h-mixed boxes
    corpus: List[Dict[str, Any]] = []
    archetypes = [
        # (cost_net, avail_a, avail_b, hz_a, hz_b, dep_a, dep_b, drop_a, jackpot)
        (0.968, 36.0, 34.0, "15m", "5m", 14.0, 12.0, 0.015, False),
        (0.974, 19.0, 42.0, "15m", "5m", 22.0, 10.0, 0.020, False),
        (0.991, 13.5, 28.0, "15m", "5m", 24.0, 14.0, 0.030, False),
        (0.976, 38.0, 20.0, "4h", "15m", 10.0, 26.0, 0.025, False),
        (0.964, 30.0, 29.0, "15m", "5m", 12.0, 12.0, 0.015, True),
        (0.982, 16.0, 35.0, "4h", "15m", 28.0, 12.0, 0.030, False),
    ]
    for idx in range(60):
        cost_n, av_a, av_b, hz_a, hz_b, dep_a, dep_b, drop_a, jpot = archetypes[idx % len(archetypes)]
        jitter = ((idx % 5) - 2) * 0.0015
        corpus.append({
            "shares": 12.0,
            "box_cost_net": round(cost_n + jitter, 4),
            "leg_a_limit_price": round(0.5 * (cost_n + jitter) - 0.01, 4),
            "leg_b_limit_price": round(0.5 * (cost_n + jitter) - 0.01, 4),
            "leg_a_avail_shares": av_a,
            "leg_b_avail_shares": av_b,
            "leg_a_horizon": hz_a,
            "leg_b_horizon": hz_b,
            "depletion_a_per_s": dep_a,
            "depletion_b_per_s": dep_b,
            "bid_drop_a": drop_a,
            "bid_drop_b": 0.02,
            "corridor_jackpot": bool(jpot and (idx % 12 == 4)),
        })
    return corpus


def _score_d1_slice(
    events: Sequence[Dict[str, Any]],
    cfg: Dict[str, Any],
    skew_grid_ms: Sequence[float] = (0.0, 100.0, 200.0, 400.0),
) -> Dict[str, Any]:
    pnls: List[float] = []
    legged = 0
    entered = 0
    for ev in events:
        for dt_ms in skew_grid_ms:
            r = simulate_d1_box_with_latency_skew(ev, cfg, delta_t_ms=dt_ms)
            if r["entered"]:
                entered += 1
                pnls.append(float(r["pnl_usd"]))
                if r["legged_out"]:
                    legged += 1
    gw = sum(x for x in pnls if x > 0.0)
    gl = abs(sum(x for x in pnls if x <= 0.0))
    pf = gw / gl if gl > 1e-6 else (99.0 if gw > 0.0 else 0.0)
    return {
        "entered": entered,
        "net_pnl_usd": round(sum(pnls), 3),
        "profit_factor": round(pf, 3),
        "legged_out_count": legged,
        "legged_out_rate": round(legged / max(entered, 1), 4),
    }


def calibrate_d1_box_wfo(
    box_events: Optional[Sequence[Dict[str, Any]]] = None,
    data_dir: Optional[Path] = None,
    purge_gap: int = 3,
) -> Dict[str, Any]:
    """
    Runs chronological Purged Train -> Embargo -> Validation -> Embargo -> Sealed Holdout WFO
    for D1 Multi-Leg Box routing (`fragile_first` vs `parallel_2leg` vs `hybrid_auto`),
    `depth_ratio_threshold`, `min_depth_mult_gate`, and Stage-1 `max_giveback_frac`.
    """
    events = list(box_events) if box_events is not None else _default_d1_calibration_events(data_dir)
    n = len(events)
    i_tr = max(4, int(0.50 * n))
    i_vl_s = min(n, i_tr + purge_gap)
    i_vl_e = max(i_vl_s + 2, int(0.75 * n))
    i_ho_s = min(n, i_vl_e + purge_gap)

    tr_ev = events[:i_tr]
    vl_ev = events[i_vl_s:i_vl_e]
    ho_ev = events[i_ho_s:]

    best_score = -1e9
    best_cfg: Dict[str, Any] = {
        "routing_mode": "hybrid_auto",
        "depth_ratio_threshold": 1.35,
        "min_depth_mult_gate": 1.50,
        "max_giveback_frac": 0.35,
        "max_box_cost_net": 0.985,
    }
    best_tr: Dict[str, Any] = {}
    best_vl: Dict[str, Any] = {}
    grid_count = 0

    for r_mode in ("hybrid_auto", "fragile_first", "parallel_2leg"):
        for dr_th in (1.20, 1.35, 1.50):
            for md_gate in (1.15, 1.50, 1.75):
                for gb_frac in (0.25, 0.35, 0.50):
                    cand_cfg = {
                        "routing_mode": r_mode,
                        "depth_ratio_threshold": dr_th,
                        "min_depth_mult_gate": md_gate,
                        "max_giveback_frac": gb_frac,
                        "max_box_cost_net": 0.985,
                    }
                    grid_count += 1
                    s_tr = _score_d1_slice(tr_ev, cand_cfg)
                    s_vl = _score_d1_slice(vl_ev, cand_cfg)
                    if s_tr["entered"] < 4 or s_vl["entered"] < 2:
                        continue
                    sc = (
                        min(s_tr["net_pnl_usd"], s_vl["net_pnl_usd"])
                        + 0.25 * (s_tr["net_pnl_usd"] + s_vl["net_pnl_usd"])
                        - 8.0 * max(s_tr["legged_out_rate"], s_vl["legged_out_rate"])
                    )
                    if sc > best_score:
                        best_score = sc
                        best_cfg = cand_cfg
                        best_tr = s_tr
                        best_vl = s_vl

    if not best_tr:
        best_tr = _score_d1_slice(tr_ev, best_cfg)
        best_vl = _score_d1_slice(vl_ev, best_cfg)
    best_ho = _score_d1_slice(ho_ev, best_cfg)
    naive_parallel_ho = _score_d1_slice(
        ho_ev,
        {
            "routing_mode": "parallel_2leg",
            "depth_ratio_threshold": 1.50,
            "min_depth_mult_gate": 1.00,
            "max_giveback_frac": 0.25,
            "max_box_cost_net": 0.995,
        },
    )

    return {
        "events_total": n,
        "purge_gap_events": purge_gap,
        "grid_configs_evaluated": grid_count,
        "selected_d1_policy": best_cfg,
        "train": best_tr,
        "val": best_vl,
        "sealed_holdout": best_ho,
        "unfiltered_parallel_holdout_baseline": naive_parallel_ho,
    }


def compute_d1_maker_anchor_drag_haircut(
    shares: float,
    pair_eff: float,
    bid_anc: float,
    hdg_px: float,
    hdg_avail_shares: float,
    fee_rate_anc: float = DEFAULT_FEE_RATE,
    fee_exponent_anc: float = 1.0,
    queue_front: bool = True,
    is_4h_mixed: bool = False,
    scratch_slip_cents: float = 0.015,
) -> Dict[str, float]:
    """
    Computes residual post-fill 250ms FOK hedge-miss + taker-scratch drag for `D1_MAKER_ANCHOR_BOX`.
    Maker Leg 1 pays 0% entry fee (saving ~100% of Leg 1 fee + 1c spread); if Leg 2 FOK misses during
    the 250ms hedge transit, only the exit scratch pays 1x V2 taker fee + `scratch_slip_cents`.
    """
    sh = max(1.0, float(shares))
    depth_mult = max(0.0, float(hdg_avail_shares)) / sh
    if depth_mult < 1.50:
        p_miss = 0.14
    elif depth_mult < 2.50:
        p_miss = 0.055
    else:
        p_miss = 0.020
    if not queue_front:
        p_miss = min(0.30, p_miss + 0.025)
    if is_4h_mixed:
        p_miss = min(0.30, p_miss + 0.020)

    scr_px = max(0.01, float(bid_anc) - float(scratch_slip_cents))
    fee_scr = v2_taker_fee_per_share(scr_px, fee_rate_anc, fee_exponent_anc)
    scratch_loss_ps = (float(bid_anc) - scr_px) + fee_scr
    drag_per_pair = p_miss * scratch_loss_ps
    gross_floor_ps = 1.0 - float(pair_eff)
    adj_ev_ps = gross_floor_ps - drag_per_pair
    rebate_20pct_ps = 0.20 * v2_taker_fee_per_share(float(bid_anc), fee_rate_anc, fee_exponent_anc)

    return {
        "hdg_depth_mult": round(depth_mult, 4),
        "p_hedge_miss_250ms": round(p_miss, 4),
        "scratch_loss_per_share": round(scratch_loss_ps, 5),
        "legging_drag_per_pair": round(drag_per_pair, 5),
        "legging_drag_usd": round(sh * drag_per_pair, 4),
        "gross_floor_per_pair": round(gross_floor_ps, 5),
        "legging_adjusted_net_ev_per_pair": round(adj_ev_ps, 5),
        "legging_adjusted_min_profit_usd": round(sh * adj_ev_ps, 4),
        "maker_rebate_20pct_est_usd": round(sh * rebate_20pct_ps, 4),
    }


def _default_d1_maker_leg1_events() -> List[Dict[str, Any]]:
    """
    Deterministic 60-event near-arb D1 corpus (`taker_net` in `[1.001, 1.028]`) spanning:
      - Calm 2c-spread mid-book boxes (`$0.48/$0.50 + $0.47/$0.48`),
      - Calm 1c-spread mid-book boxes (`$0.48/$0.49 + $0.48/$0.49`) with healthy vs collapsing OBI,
      - Sub-cent `0.001`-tick 4h/15m tail boxes (`$0.964/$0.999 + $0.01/$0.02`, matching real XRP 4h_15m),
      - Adverse-spot snipers (`spot_move_bps` against anchor) where directional cancel-on-move saves scratches.
    """
    archetypes = [
        # (anc_side, bid_anc, ask_anc, obi_anc, ask_hdg, hdg_sh, spot_ret_bps, fill_if_kept, hdg_jump_on_adv, shares)
        ("UP", 0.48, 0.50, 0.12, 0.48, 85.0, 0.6, True, 0.00, 18.0),      # 2c spread queue-front clean fill
        ("DOWN", 0.48, 0.49, 0.18, 0.49, 95.0, -0.8, True, 0.00, 18.0),   # 1c spread healthy OBI + favorable spot
        ("UP", 0.48, 0.49, -0.48, 0.49, 60.0, -4.2, True, 0.04, 18.0),    # Toxic collapsing OBI + adverse drop -> must veto/cancel!
        ("UP", 0.964, 0.999, 0.10, 0.019, 32.0, 0.4, True, 0.00, 15.0),   # 0.001-tick tail anchor (saves 3.6c vs taker!)
        ("DOWN", 0.47, 0.49, 0.05, 0.49, 70.0, 3.8, True, 0.03, 18.0),    # Adverse +3.8bps rise against DOWN -> directional cancel saves!
        ("UP", 0.46, 0.48, 0.22, 0.50, 18.0, 0.3, True, 0.02, 18.0),      # Thin hedge (<2x shares) -> depth gate blocks!
    ]
    out: List[Dict[str, Any]] = []
    for idx in range(60):
        side, b_a, a_a, obi_a, a_h, h_sh, s_ret, f_ok, h_jmp, sh = archetypes[idx % len(archetypes)]
        jit = ((idx % 3) - 1) * 0.001
        out.append({
            "anc_side": side,
            "bid_anc": round(b_a, 3),
            "ask_anc": round(a_a, 3),
            "obi_anc": round(obi_a + jit * 10.0, 3),
            "ask_hdg": round(a_h, 3),
            "hdg_shares": h_sh,
            "spot_ret_bps": s_ret,
            "passive_fill": f_ok,
            "hdg_jump_on_adverse": h_jmp,
            "shares": sh,
            "fee_rate": DEFAULT_FEE_RATE,
        })
    return out


def simulate_d1_maker_leg1_box(ev: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates a single `D1_MAKER_ANCHOR_BOX` candidate under queue-realistic + 250ms hedge latency physics."""
    b_anc = float(ev["bid_anc"])
    a_anc = float(ev["ask_anc"])
    obi_anc = float(ev.get("obi_anc", 0.0))
    a_hdg = float(ev["ask_hdg"])
    hdg_sh = float(ev["hdg_shares"])
    sh = max(5.0, float(ev.get("shares", 18.0)))
    fr = float(ev.get("fee_rate", DEFAULT_FEE_RATE))
    side = str(ev.get("anc_side", "UP")).upper()
    spot_ret_bps = float(ev.get("spot_ret_bps", 0.0))

    def _snap_px(p: float) -> float:
        p = round(float(p), 4)
        return (math.floor((p + 1e-9) * 100.0) / 100.0) if (0.04 + 1e-9 < p < 0.96 - 1e-9) else (math.floor((p + 1e-9) * 1000.0) / 1000.0)

    tick_b = 0.001 if (b_anc >= 0.96 or b_anc < 0.04) else 0.01
    tick_a = 0.001 if (a_anc > 0.96 or a_anc <= 0.04) else 0.01
    step_bid = _snap_px(b_anc + tick_b)
    max_under = _snap_px(a_anc - tick_a)
    spr = round(a_anc - b_anc, 4)
    allow_join_1c = bool(cfg.get("allow_join_1c_mid", True))
    min_obi_1c = float(cfg.get("min_obi_join_1c", -0.15))
    min_obi_any = float(cfg.get("min_obi_any", -0.35))
    min_hdg_mult = float(cfg.get("min_hdg_depth_mult", 2.5))
    max_post_net = float(cfg.get("max_post_net", 0.988))
    adv_cancel_bps = float(cfg.get("adverse_spot_cancel_bps", 2.5))

    if obi_anc < min_obi_any or hdg_sh < max(15.0, min_hdg_mult * sh):
        return {"posted": False, "filled": False, "hedged": False, "pnl_usd": 0.0, "scratched": False}

    if step_bid <= max_under + 1e-9 and step_bid > b_anc + 1e-9:
        cand_bid = min(step_bid, max_under)
        q_front = True
    elif allow_join_1c and spr >= 0.01 - 1e-9 and 0.15 <= a_anc <= 0.85 and obi_anc >= min_obi_1c:
        cand_bid = _snap_px(b_anc)
        q_front = False
    else:
        return {"posted": False, "filled": False, "hedged": False, "pnl_usd": 0.0, "scratched": False}

    hdg_eff0 = a_hdg + v2_taker_fee_per_share(a_hdg, fr)
    max_anc = _snap_px(max_post_net - hdg_eff0)
    bid_px = min(cand_bid, max_anc)
    if bid_px < round(b_anc - (tick_b if q_front else 0.0), 3) or bid_px <= 0.02 or bid_px >= a_anc:
        return {"posted": False, "filled": False, "hedged": False, "pnl_usd": 0.0, "scratched": False}
    if not (0.900 <= (bid_px + hdg_eff0) <= max_post_net):
        return {"posted": False, "filled": False, "hedged": False, "pnl_usd": 0.0, "scratched": False}

    # Directional cancel-on-spot-move BEFORE toxic sniper fill ($0.00 cost on postOnly cancel)
    adv_bps = (-spot_ret_bps) if side == "UP" else spot_ret_bps
    if adv_bps > adv_cancel_bps:
        return {"posted": True, "filled": False, "hedged": False, "pnl_usd": 0.0, "scratched": False}

    if not ev.get("passive_fill", True):
        return {"posted": True, "filled": False, "hedged": False, "pnl_usd": 0.0, "scratched": False}

    hdg_px_fill = round(a_hdg + (float(ev.get("hdg_jump_on_adverse", 0.0)) if adv_bps > 1.5 else 0.0), 4)
    pair_eff = bid_px + hdg_px_fill + v2_taker_fee_per_share(hdg_px_fill, fr)
    if 0.900 <= pair_eff <= 0.995:
        drag = compute_d1_maker_anchor_drag_haircut(
            shares=sh, pair_eff=pair_eff, bid_anc=bid_px, hdg_px=hdg_px_fill,
            hdg_avail_shares=hdg_sh, fee_rate_anc=fr, queue_front=q_front,
        )
        return {
            "posted": True,
            "filled": True,
            "hedged": True,
            "scratched": False,
            "pnl_usd": round(sh * (1.0 - pair_eff), 4),
            "adj_pnl_usd": drag["legging_adjusted_min_profit_usd"],
        }

    scr_px = max(0.01, bid_px - max(0.015, float(ev.get("hdg_jump_on_adverse", 0.02))))
    scr_net = scr_px - v2_taker_fee_per_share(scr_px, fr)
    loss_u = round(sh * (scr_net - bid_px), 4)
    return {"posted": True, "filled": True, "hedged": False, "scratched": True, "pnl_usd": loss_u, "adj_pnl_usd": loss_u}


def calibrate_d1_maker_leg1_wfo(
    maker_events: Optional[Sequence[Dict[str, Any]]] = None,
    purge_gap: int = 3,
) -> Dict[str, Any]:
    """Purged Train -> Embargo -> Validation -> Embargo -> Sealed Holdout WFO for `D1_MAKER_ANCHOR_BOX` (`EXP-PM-406`)."""
    events = list(maker_events) if maker_events is not None else _default_d1_maker_leg1_events()
    n = len(events)
    i_tr = max(4, int(0.50 * n))
    i_vl_s = min(n, i_tr + purge_gap)
    i_vl_e = max(i_vl_s + 2, int(0.75 * n))
    i_ho_s = min(n, i_vl_e + purge_gap)
    tr_ev, vl_ev, ho_ev = events[:i_tr], events[i_vl_s:i_vl_e], events[i_ho_s:]

    def _eval(sub: Sequence[Dict[str, Any]], cfg: Dict[str, Any]) -> Dict[str, Any]:
        rows = [simulate_d1_maker_leg1_box(e, cfg) for e in sub]
        fills = [r for r in rows if r["filled"]]
        wins = [r for r in fills if r["hedged"]]
        scratches = [r for r in fills if r["scratched"]]
        adj_pnl = sum(float(r.get("adj_pnl_usd", r["pnl_usd"])) for r in fills)
        raw_pnl = sum(float(r["pnl_usd"]) for r in fills)
        return {
            "posted": sum(1 for r in rows if r["posted"]),
            "fills": len(fills),
            "wins": len(wins),
            "scratches": len(scratches),
            "win_rate_pct": round(100.0 * len(wins) / len(fills), 2) if fills else 0.0,
            "raw_pnl_usd": round(raw_pnl, 4),
            "legging_adjusted_pnl_usd": round(adj_pnl, 4),
        }

    best_sc = -1e9
    best_cfg: Dict[str, Any] = {
        "allow_join_1c_mid": True,
        "min_obi_join_1c": -0.15,
        "min_obi_any": -0.35,
        "min_hdg_depth_mult": 2.5,
        "adverse_spot_cancel_bps": 2.5,
        "max_post_net": 0.988,
    }
    best_tr: Dict[str, Any] = {}
    best_vl: Dict[str, Any] = {}
    grid_n = 0
    for join_1c in (True, False):
        for adv_bps in (2.0, 2.5, 5.0):
            for obi_1c in (-0.15, -0.40):
                for hdg_m in (1.5, 2.5):
                    cfg_c = {
                        "allow_join_1c_mid": join_1c,
                        "min_obi_join_1c": obi_1c,
                        "min_obi_any": -0.35,
                        "min_hdg_depth_mult": hdg_m,
                        "adverse_spot_cancel_bps": adv_bps,
                        "max_post_net": 0.988,
                    }
                    grid_n += 1
                    s_tr, s_vl = _eval(tr_ev, cfg_c), _eval(vl_ev, cfg_c)
                    if s_tr["fills"] < 3 or s_vl["fills"] < 2:
                        continue
                    sc = (
                        min(s_tr["legging_adjusted_pnl_usd"], s_vl["legging_adjusted_pnl_usd"])
                        + 0.30 * (s_tr["legging_adjusted_pnl_usd"] + s_vl["legging_adjusted_pnl_usd"])
                        - 6.0 * (s_tr["scratches"] + s_vl["scratches"])
                    )
                    if sc > best_sc:
                        best_sc, best_cfg, best_tr, best_vl = sc, cfg_c, s_tr, s_vl

    if not best_tr:
        best_tr, best_vl = _eval(tr_ev, best_cfg), _eval(vl_ev, best_cfg)
    best_ho = _eval(ho_ev, best_cfg)
    naive_ho = _eval(
        ho_ev,
        {
            "allow_join_1c_mid": True,
            "min_obi_join_1c": -1.0,
            "min_obi_any": -1.0,
            "min_hdg_depth_mult": 1.0,
            "adverse_spot_cancel_bps": 99.0,
            "max_post_net": 0.992,
        },
    )
    return {
        "events_total": n,
        "purge_gap_events": purge_gap,
        "grid_configs_evaluated": grid_n,
        "selected_maker_leg1_policy": best_cfg,
        "train": best_tr,
        "val": best_vl,
        "sealed_holdout": best_ho,
        "unguarded_maker_holdout_baseline": naive_ho,
    }


def compute_v395_pricing_and_twap_gate(
    cand: Dict[str, Any],
    *,
    df: Optional[float] = None,
    jump_vol_mult: float = 1.0,
    use_kemna_vorst: bool = False,
) -> Tuple[float, float]:
    """
    Computes `(z_adj, p_win)` for a subhourly candidate under:
      - Kemna-Vorst continuous 60s-TWAP remaining sigma (`sqrt(tau - 40)` for `tau >= 60s`),
      - `jump_vol_mult` volatility multiplier,
      - Unit-variance Student-t (`Var(X) = 1.0` via `t_std = z * sqrt((nu - 2)/nu)`) or Gaussian (`df=None`).
    """
    from src.polymarket_research.exact_twap_lock_engine import (
        compute_kemna_vorst_twap_sigma_rem,
        compute_unit_variance_student_t_cdf,
    )

    cush = float(cand.get("cushion_oracle", cand.get("cushion_min", 0.0)) or 0.0)
    tte = max(5.0, float(cand.get("tte", 300.0) or 300.0))
    sig_rem_base = max(0.00025, float(cand.get("sigma_rem", 0.0020) or 0.0020))
    sig_1h = sig_rem_base / math.sqrt(max(tte, 1.0) / 3600.0)
    if use_kemna_vorst and str(cand.get("hz") or "") in ("5m", "15m"):
        sig_rem = max(0.00018, compute_kemna_vorst_twap_sigma_rem(sig_1h, tte, window_sec=60.0))
    else:
        sig_rem = sig_rem_base
    sig_eff = sig_rem * max(0.50, float(jump_vol_mult))
    z_adj = cush / sig_eff
    ofi = min(1.0, max(0.0, float(cand.get("shock_ofi", 0.0) or 0.0)))
    z_prob = z_adj + 0.25 * ofi
    if df is None or math.isinf(float(df)) or float(df) > 100.0:
        p_win = 0.5 * (1.0 + math.erf(z_prob / math.sqrt(2.0)))
    else:
        p_win = compute_unit_variance_student_t_cdf(z_prob, df=float(df))
    return round(z_adj, 5), round(max(0.01, min(0.995, p_win)), 5)


def run_wfo_post_selection_diagnostics(
    *,
    cands: Sequence[Dict[str, Any]],
    dev_cands: Sequence[Dict[str, Any]],
    holdout_cands: Sequence[Dict[str, Any]],
    best_cfg: Dict[str, Any],
    best_tr: Dict[str, Any],
    best_vl: Dict[str, Any],
    best_hold_500: Dict[str, Any],
    stage2_results: Sequence[Any],
    data_dir: Path,
    purge_sec: float,
    evaluate_portfolio_fn: Any,
    prefilter_fn: Any,
    dev_score_fn: Any,
    simulate_single_fn: Any,
) -> Dict[str, Any]:
    """Runs CPCV(6,2), Chainlink mismatch audit, 50-trade Monte Carlo, top-5 OOS summary, and live counterfactual."""
    import itertools
    import random
    import statistics

    all_sorted = sorted(cands, key=lambda x: x["t0"])
    n_all = len(all_sorted)
    n_groups = 6
    group_bounds: List[Tuple[float, float]] = []
    for g_idx in range(n_groups):
        g_i0 = int((g_idx / n_groups) * n_all)
        g_i1 = int(((g_idx + 1) / n_groups) * n_all) - 1
        group_bounds.append((all_sorted[g_i0]["t0"], all_sorted[max(g_i0, g_i1)]["t0"]))

    apriori_cpcv_grid: List[Dict[str, Any]] = []
    for px_lo, px_hi in [(0.55, 0.80), (0.55, 0.82), (0.55, 0.85)]:
        for z_th in [0.65, 0.85, 1.05]:
            for c_th in [0.0004, 0.0006]:
                for f_b in [0.01, 0.02]:
                    for ex_p in ["single_95", "two_tranche_14_98", "two_tranche_95_98", "hold_98"]:
                        for s_m, r_a, w_t, s_p in [("spot_persist", None, 0.0009, 18.0), ("hybrid_persist", 0.12, 0.0006, 15.0)]:
                            apriori_cpcv_grid.append({
                                "assets": ("BTC", "ETH"), "horizons": ("15m", "1h"),
                                "min_tte_15m": 90.0, "max_tte_15m": 480.0, "min_tte_1h": 150.0, "max_tte_1h": 1200.0,
                                "min_px": px_lo, "max_px": px_hi, "max_spread": 0.03, "min_l1_usd": 20.0,
                                "min_cushion": c_th, "min_z": z_th, "min_ofi": 0.60,
                                "use_venue_veto": True, "use_cl_proxy": True, "entry_mode": "taker_fak", "fak_buffer": f_b,
                                "exit_policy": ex_p, "ratchet_arm": r_a, "ratchet_drop": 0.06,
                                "salvage_mode": s_m, "wrong_side_thresh": w_t, "salvage_persist_s": s_p,
                                "clob_drop_thresh": 0.22, "final_45s_unwind": False,
                            })
    apriori_superset = prefilter_fn(all_sorted, {
        "assets": ("BTC", "ETH"), "horizons": ("15m", "1h"),
        "min_tte_15m": 90.0, "max_tte_15m": 480.0, "min_tte_1h": 150.0, "max_tte_1h": 1200.0,
        "min_px": 0.55, "max_px": 0.85, "max_spread": 0.03, "min_l1_usd": 20.0,
        "min_cushion": 0.0004, "min_z": 0.65, "min_ofi": 0.60, "use_venue_veto": True, "use_cl_proxy": True,
    })

    cpcv_splits = []
    for g_a, g_b in itertools.combinations(range(n_groups), 2):
        test_intervals = [group_bounds[g_a], group_bounds[g_b]]
        train_cpcv = [
            c for c in apriori_superset
            if all((c["exp_ts"] < (ts_i - purge_sec)) or (c["t0"] > (te_i + purge_sec)) for ts_i, te_i in test_intervals)
        ]
        oos_cpcv = []
        for g_t in (g_a, g_b):
            t_s, t_e = group_bounds[g_t]
            purge_left = purge_sec if (g_t > 0 and (g_t - 1) not in (g_a, g_b)) else 0.0
            purge_right = purge_sec if (g_t < n_groups - 1 and (g_t + 1) not in (g_a, g_b)) else 0.0
            eff_s, eff_e = t_s + purge_left, t_e - (purge_right * 0.25)
            oos_cpcv.extend(c for c in apriori_superset if eff_s <= c["t0"] <= eff_e and c["exp_ts"] <= t_e)
        oos_cpcv.sort(key=lambda x: x["t0"])

        n_tc = len(train_cpcv)
        t_cut_inner = train_cpcv[int(0.70 * n_tc)]["t0"] if n_tc >= 20 else 0.0
        in_tr = [c for c in train_cpcv if c["exp_ts"] <= t_cut_inner]
        in_vl = [c for c in train_cpcv if c["t0"] >= (t_cut_inner + purge_sec)]
        fitted_cfg = apriori_cpcv_grid[0]
        best_cpcv_sc = -1e9
        for cand_cfg in apriori_cpcv_grid:
            ri_tr = evaluate_portfolio_fn(in_tr, cand_cfg, latency_mode="500ms")
            if ri_tr["trades"] < 20 or ri_tr["total_pnl"] <= 0 or ri_tr["profit_factor"] < 1.20:
                continue
            ri_vl = evaluate_portfolio_fn(in_vl, cand_cfg, latency_mode="500ms")
            if ri_vl["trades"] < 8 or ri_vl["total_pnl"] <= 0 or ri_vl["profit_factor"] < 1.15:
                continue
            sc_i = dev_score_fn(ri_tr, ri_vl)
            if sc_i > best_cpcv_sc:
                best_cpcv_sc, fitted_cfg = sc_i, cand_cfg
        if best_cpcv_sc <= -1e8:
            for cand_cfg in apriori_cpcv_grid:
                ri_all = evaluate_portfolio_fn(train_cpcv, cand_cfg, latency_mode="500ms")
                if ri_all["trades"] >= 25 and ri_all["total_pnl"] > 0:
                    sc_i = dev_score_fn(ri_all, ri_all)
                    if sc_i > best_cpcv_sc:
                        best_cpcv_sc, fitted_cfg = sc_i, cand_cfg

        r_cpcv = evaluate_portfolio_fn(oos_cpcv, fitted_cfg, latency_mode="500ms")
        r_cpcv_seed = evaluate_portfolio_fn(oos_cpcv, fitted_cfg, latency_mode="500ms", max_concurrent=1, ticket_usd=12.0)
        cpcv_splits.append({
            "test_groups": [g_a, g_b], "fitted_exit_policy": fitted_cfg["exit_policy"], "fitted_min_z": fitted_cfg["min_z"],
            "trades": r_cpcv["trades"], "total_pnl": r_cpcv["total_pnl"], "seed_12_c1_pnl": r_cpcv_seed["total_pnl"],
            "win_rate": r_cpcv["win_rate"], "profit_factor": r_cpcv["profit_factor"], "sharpe": r_cpcv["sharpe"],
            "wipeout_rate": r_cpcv["wipeout_rate"],
        })

    cpcv_pnls_list = [s["total_pnl"] for s in cpcv_splits]
    cpcv_seed_pnls = [s["seed_12_c1_pnl"] for s in cpcv_splits]
    cpcv_summary = {
        "mode": "GENUINE_OUT_OF_SAMPLE_REFIT_CPCV_6_2", "n_groups": 6, "k_test_groups": 2,
        "apriori_grid_size": len(apriori_cpcv_grid), "total_combinations": len(cpcv_splits),
        "positive_combinations": sum(1 for x in cpcv_pnls_list if x > 0),
        "positive_rate": round(sum(1 for x in cpcv_pnls_list if x > 0) / max(len(cpcv_splits), 1), 4),
        "seed_12_c1_positive_combinations": sum(1 for x in cpcv_seed_pnls if x > 0),
        "median_oos_trades": int(statistics.median(s["trades"] for s in cpcv_splits)),
        "median_oos_pnl_usd": round(statistics.median(cpcv_pnls_list), 2),
        "mean_oos_pnl_usd": round(statistics.mean(cpcv_pnls_list), 2),
        "median_seed_12_c1_oos_pnl_usd": round(statistics.median(cpcv_seed_pnls), 2),
        "min_oos_pnl_usd": round(min(cpcv_pnls_list), 2),
        "median_oos_pf": round(statistics.median(s["profit_factor"] for s in cpcv_splits), 3),
        "median_oos_sharpe": round(statistics.median(s["sharpe"] for s in cpcv_splits), 3),
        "splits": cpcv_splits,
    }

    mismatch_mids = set()
    ver_p = data_dir / "verified_gamma_resolutions.json"
    if ver_p.exists():
        try:
            for k_m, v_m in json.loads(ver_p.read_text(encoding="utf-8")).items():
                if isinstance(v_m, dict) and (
                    v_m.get("oracle_mismatch") or v_m.get("mismatch")
                    or (v_m.get("binance_winner") and v_m.get("winner") and v_m.get("binance_winner") != v_m.get("winner"))
                ):
                    mismatch_mids.add(str(k_m))
        except Exception:
            pass
    for gt_name in ("ground_truth_resolutions.jsonl", "ground_truth_resolutions_eth.jsonl", "ground_truth_resolutions_sol.jsonl"):
        gt_p = data_dir / gt_name
        if gt_p.exists():
            try:
                for ln in gt_p.read_text(encoding="utf-8", errors="replace").splitlines():
                    if ln.strip():
                        row_g = json.loads(ln)
                        if row_g.get("oracle_mismatch") or (
                            row_g.get("binance_winning_outcome") and row_g.get("gamma_winning_outcome")
                            and row_g.get("binance_winning_outcome") != row_g.get("gamma_winning_outcome")
                        ):
                            mismatch_mids.add(str(row_g.get("market_id")))
            except Exception:
                pass
    for c_item in all_sorted:
        if c_item["path"]:
            tte_end_i, cush_end_i, _, _, _ = c_item["path"][-1]
            if tte_end_i <= 30.0 and abs(cush_end_i) >= 0.00001 and ((cush_end_i > 0) != bool(c_item["won"])):
                mismatch_mids.add(str(c_item.get("mid")))
        if str(c_item.get("mid")) in mismatch_mids:
            c_item["oracle_mismatch"] = True

    mismatch_cands = [c for c in all_sorted if c.get("oracle_mismatch")]
    mm_raw = evaluate_portfolio_fn(mismatch_cands, dict(best_cfg, use_cl_proxy=False), latency_mode="500ms")
    mm_cl = evaluate_portfolio_fn(mismatch_cands, dict(best_cfg, use_cl_proxy=True), latency_mode="500ms")
    full_no_cl = evaluate_portfolio_fn(all_sorted, dict(best_cfg, use_cl_proxy=False), latency_mode="500ms")
    full_with_cl = evaluate_portfolio_fn(all_sorted, dict(best_cfg, use_cl_proxy=True), latency_mode="500ms")

    bp1_base = dict(best_cfg)
    if not str(bp1_base.get("exit_policy", "")).startswith("two_tranche"):
        bp1_base["exit_policy"] = "two_tranche_12_98"
    bp1_delayed = evaluate_portfolio_fn(all_sorted, dict(bp1_base, t2_post_lag_s=5.0), latency_mode="500ms")
    bp1_inline = evaluate_portfolio_fn(all_sorted, dict(bp1_base, t2_post_lag_s=0.05), latency_mode="500ms")
    bp1_concurrent = evaluate_portfolio_fn(all_sorted, dict(bp1_base, t2_post_lag_s=0.0), latency_mode="500ms")

    chainlink_proxy_audit = {
        "mismatch_markets_identified": len(mismatch_mids),
        "mismatch_candidates_total": len(mismatch_cands),
        "mismatch_raw_trades": mm_raw["trades"], "mismatch_raw_pnl": mm_raw["total_pnl"],
        "mismatch_cl_proxy_trades": mm_cl["trades"], "mismatch_cl_proxy_pnl": mm_cl["total_pnl"],
        "full_dataset_raw_pnl": full_no_cl["total_pnl"], "full_dataset_raw_pf": full_no_cl["profit_factor"],
        "full_dataset_cl_proxy_pnl": full_with_cl["total_pnl"], "full_dataset_cl_proxy_pf": full_with_cl["profit_factor"],
        "blueprint1_tranche2_comparison": {
            "delayed_5s_pnl": bp1_delayed["total_pnl"], "delayed_5s_pf": bp1_delayed["profit_factor"],
            "inline_50ms_pnl": bp1_inline["total_pnl"], "inline_50ms_pf": bp1_inline["profit_factor"],
            "concurrent_0ms_pnl": bp1_concurrent["total_pnl"], "concurrent_0ms_pf": bp1_concurrent["profit_factor"],
        },
    }

    oos_unit_rets = [p / 15.0 for p in (best_vl["pnls"] + best_hold_500["pnls"])]
    if len(oos_unit_rets) < 20:
        oos_unit_rets = [p / 15.0 for p in best_tr["pnls"]]

    def _sim_bankroll(label: str, start_eq: float, base_pct: float, min_tkt: float, floor_u: float, seed_cap: float = 0.0, corr_p: float = 0.0) -> Dict[str, Any]:
        rng_mc = random.Random(20261025)
        halted_cnt = 0
        end_eqs, max_dds = [], []
        n_r = max(1, len(oos_unit_rets))
        for _ in range(10000):
            eq, pk, mdd, halted, t_done = start_eq, start_eq, 0.0, False, 0
            while t_done < 50 and oos_unit_rets:
                if eq < floor_u:
                    halted = True
                    break
                if seed_cap > 0.0 and eq < seed_cap:
                    eq += min(eq, 12.0) * oos_unit_rets[rng_mc.randrange(n_r)]
                    t_done += 1
                else:
                    tkt = min(eq, max(min_tkt, round(eq * base_pct, 2)))
                    if corr_p > 0.0 and rng_mc.random() < corr_p and (t_done + 1) < 50:
                        r1 = oos_unit_rets[rng_mc.randrange(n_r)]
                        r2 = r1 if rng_mc.random() < 0.75 else oos_unit_rets[rng_mc.randrange(n_r)]
                        eq += tkt * r1 + (tkt * 0.54) * r2
                        t_done += 2
                    else:
                        eq += tkt * oos_unit_rets[rng_mc.randrange(n_r)]
                        t_done += 1
                pk = max(pk, eq)
                mdd = max(mdd, pk - eq)
                if eq < floor_u:
                    halted = True
                    break
            if halted:
                halted_cnt += 1
            end_eqs.append(eq)
            max_dds.append(mdd)
        end_eqs.sort()
        max_dds.sort()
        return {
            "policy": label, "start_equity_usd": start_eq, "floor_usd": floor_u,
            "halt_prob_50_trades": round(halted_cnt / 10000, 4),
            "median_terminal_equity_usd": round(end_eqs[5000], 2),
            "p05_terminal_equity_usd": round(end_eqs[500], 2),
            "p95_terminal_equity_usd": round(end_eqs[9500], 2),
            "p95_max_drawdown_usd": round(max_dds[9500], 2),
        }

    bankroll_mc = [
        _sim_bankroll("v3.7_UNPATCHED_22PCT_FLOOR65_CONC2", 76.49, 0.22, 12.0, 65.00, corr_p=0.25),
        _sim_bankroll("CENTRAL_CFG_18PCT_FLOOR66.67_CONC2", 76.49, 0.18, 12.0, 66.67, corr_p=0.25),
        _sim_bankroll("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR48", 76.49, 0.18, 12.0, 48.00, seed_cap=88.0, corr_p=0.15),
        _sim_bankroll("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR52", 76.49, 0.18, 12.0, 52.00, seed_cap=88.0, corr_p=0.15),
    ]

    top5_summary = []
    seen_top5_cores = set()
    for sc, c_i, tr_i, vl_i, _ in stage2_results:
        ck_i = (c_i["assets"], c_i["horizons"], c_i["min_px"], c_i["max_px"], c_i["min_z"], c_i["min_cushion"], c_i["entry_mode"], c_i["exit_policy"])
        if ck_i in seen_top5_cores:
            continue
        seen_top5_cores.add(ck_i)
        ho_i = evaluate_portfolio_fn(holdout_cands, c_i, latency_mode="500ms")
        top5_summary.append({
            "score": round(sc, 2),
            "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in c_i.items()},
            "train": {k: v for k, v in tr_i.items() if k != "pnls"},
            "val": {k: v for k, v in vl_i.items() if k != "pnls"},
            "holdout": {k: v for k, v in ho_i.items() if k != "pnls"},
        })
        if len(top5_summary) >= 5:
            break

    live_counterfactual: Dict[str, Any] = {}
    st_path = data_dir / "live_harvester_state.json"
    if st_path.exists():
        st = json.loads(st_path.read_text(encoding="utf-8"))
        closed_live = st.get("closed_positions", [])
        cand_by_eid = {c["event_id"]: c for c in cands}
        cf_total, matched_live, filtered_out_losses, filtered_out_wins = 0.0, 0, 0, 0
        post_rebate_traces = []
        for pos in closed_live:
            act_pnl = float(pos.get("net_pnl_usd") or 0.0)
            eid = str(pos.get("event_id") or "")
            tid = str(pos.get("trade_id") or "")
            c_match = cand_by_eid.get(eid)
            if not c_match:
                continue
            matched_live += 1
            sim = simulate_single_fn(c_match, best_cfg, latency_mode="500ms")
            notional = float(pos.get("notional_usd") or 15.0)
            if sim is None:
                cf_pnl, cf_reason = 0.0, "VETOED_AT_ENTRY"
                if act_pnl < 0:
                    filtered_out_losses += 1
                else:
                    filtered_out_wins += 1
            else:
                cf_pnl, cf_reason = round(sim[0] * notional, 2), sim[1]
            cf_total += cf_pnl
            if "6076647" in tid or "6082720" in tid or act_pnl <= -15.0:
                post_rebate_traces.append({
                    "trade_id": tid, "entry_price": pos.get("entry_price"), "max_seen_bid": pos.get("max_seen_bid"),
                    "actual_pnl_usd": round(act_pnl, 2), "actual_close_reason": pos.get("close_reason"),
                    "wfo_counterfactual_pnl_usd": cf_pnl, "wfo_counterfactual_action": cf_reason,
                })
        live_counterfactual = {
            "total_live_closed_trades": len(closed_live), "matched_to_trigger_dataset": matched_live,
            "actual_matched_subset_pnl_usd": round(sum(float(p.get("net_pnl_usd") or 0.0) for p in closed_live if str(p.get("event_id") or "") in cand_by_eid), 2),
            "wfo_optimal_counterfactual_pnl_usd": round(cf_total, 2),
            "filtered_out_losing_trades": filtered_out_losses, "filtered_out_winning_trades": filtered_out_wins,
            "wipeout_trades_counterfactual": post_rebate_traces,
        }

    cv_folds = []
    n_dev = len(dev_cands)
    if n_dev >= 100:
        for fold_idx, (tr_f, te_f) in enumerate([(0.25, 0.43), (0.43, 0.62), (0.62, 0.81), (0.81, 1.00)], start=1):
            t_cut = dev_cands[int(tr_f * n_dev)]["t0"]
            t_end = dev_cands[min(n_dev - 1, int(te_f * n_dev) - 1)]["t0"]
            oos_fold = [c for c in dev_cands if (t_cut + purge_sec) <= c["t0"] <= t_end]
            r_fold = evaluate_portfolio_fn(oos_fold, best_cfg, latency_mode="500ms")
            cv_folds.append({
                "fold": fold_idx, "oos_candidates": len(oos_fold), "trades": r_fold["trades"],
                "total_pnl": r_fold["total_pnl"], "win_rate": r_fold["win_rate"],
                "profit_factor": r_fold["profit_factor"], "wipeout_rate": r_fold["wipeout_rate"],
            })

    return {
        "cpcv_summary": cpcv_summary,
        "chainlink_proxy_audit": chainlink_proxy_audit,
        "bankroll_mc": bankroll_mc,
        "top5_summary": top5_summary,
        "live_counterfactual": live_counterfactual,
        "cv_folds": cv_folds,
    }


def run_subhourly_v395_wfo_ablation_suite(
    cands: Sequence[Dict[str, Any]],
    evaluate_portfolio_fn: Any,
    purge_sec: float = 900.0,
) -> Dict[str, Any]:
    """
    Runs Track B Purged Walk-Forward (`Train 50% -> Embargo -> Val 25% -> Embargo -> Sealed Holdout 25%`)
    across `15m` and `5m` subhourly candidates, testing:
      1. Gaussian (`df=inf`) vs Unit-Variance Student-t (`df in {4, 6, 8}`) x `jump_vol_mult in {1.00, 1.15, 1.25}` Brier calibration,
      2. Kemna-Vorst continuous `[45s, 90s]` TWAP variance bridge vs hard `90s` cutoff,
      3. Hybrid `z`-Split (`z_taker_cut in {1.05, 1.15, 1.25}`) + Complement-Book Shield + `20%` Maker Rebate,
      4. `250ms` Coinbase Impulse Veto (`-2.5 bps`) vs `2.0s` Coinbase Veto (`-4.0 bps`),
      5. `5m` Horizon Split (`[60s, 180s]`, `z >= 0.80`) on `BTC`, `ETH`, `SOL`.
    """
    sub_15m = sorted([c for c in cands if c.get("hz") == "15m"], key=lambda x: x["t0"])
    sub_5m = sorted([c for c in cands if c.get("hz") == "5m"], key=lambda x: x["t0"])

    def _purged_split(items: Sequence[Dict[str, Any]], embargo: float) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        if len(items) < 12:
            return list(items), [], []
        t0s = [c["t0"] for c in items]
        t_tr = t0s[int(0.50 * len(t0s))]
        t_vl = t0s[int(0.75 * len(t0s))]
        tr = [c for c in items if c["exp_ts"] <= t_tr]
        vl = [c for c in items if c["t0"] >= (t_tr + embargo) and c["exp_ts"] <= t_vl]
        ho = [c for c in items if c["t0"] >= (t_vl + embargo)]
        return tr, vl, ho

    tr_15, vl_15, ho_15 = _purged_split(sub_15m, purge_sec)
    tr_5, vl_5, ho_5 = _purged_split(sub_5m, max(300.0, purge_sec * 0.5))

    # 1. Out-of-sample Brier calibration across Gaussian vs Unit-Variance Student-t x jump_vol_mult in [0.75, 2.50] sigma
    cal_sample_dev = [c for c in (tr_15 + vl_15) if 60.0 <= c["tte"] <= 480.0 and 0.75 <= abs(c.get("z_oracle", 0.0)) <= 2.50]
    cal_sample_ho = [c for c in ho_15 if 60.0 <= c["tte"] <= 480.0 and 0.75 <= abs(c.get("z_oracle", 0.0)) <= 2.50]

    def _brier(rows: Sequence[Dict[str, Any]], df_v: Optional[float], jvm: float) -> float:
        if not rows:
            return 0.25
        err = 0.0
        for r in rows:
            _, p_w = compute_v395_pricing_and_twap_gate(r, df=df_v, jump_vol_mult=jvm, use_kemna_vorst=True)
            y = 1.0 if r.get("won") else 0.0
            err += (p_w - y) ** 2
        return round(err / len(rows), 6)

    brier_grid = []
    best_cal = {"df": None, "jump_vol_mult": 1.0, "dev_brier": 1.0}
    for df_opt in (None, 4.0, 6.0, 8.0):
        for jvm_opt in (1.00, 1.15, 1.25):
            b_dev = _brier(cal_sample_dev, df_opt, jvm_opt)
            b_ho = _brier(cal_sample_ho, df_opt, jvm_opt)
            row_b = {
                "df": "gaussian" if df_opt is None else df_opt,
                "jump_vol_mult": jvm_opt,
                "dev_n": len(cal_sample_dev),
                "dev_brier": b_dev,
                "holdout_n": len(cal_sample_ho),
                "holdout_brier": b_ho,
            }
            brier_grid.append(row_b)
            if b_dev < best_cal["dev_brier"]:
                best_cal = {"df": row_b["df"], "jump_vol_mult": jvm_opt, "dev_brier": b_dev, "holdout_brier": b_ho}

    base_15m_cfg = {
        "assets": ("BTC", "ETH", "SOL"),
        "horizons": ("15m",),
        "min_tte_15m": 90.0, "max_tte_15m": 480.0,
        "min_tte_5m": 60.0, "max_tte_5m": 180.0,
        "min_tte_1h": 150.0, "max_tte_1h": 600.0,
        "min_px": 0.55, "max_px": 0.81,
        "max_spread": 0.03, "min_l1_usd": 12.0,
        "min_cushion": 0.0006, "min_z": 0.78, "min_ofi": 0.60,
        "use_venue_veto": True, "use_cl_proxy": True,
        "entry_mode": "cascade_v4", "fak_buffer": 0.02,
        "cascade_ticket_usd": 16.50, "elastic_downsnap_usd": 12.00, "min_elastic_usd": 8.00,
        "exit_policy": "hold_98", "ratchet_arm": None, "ratchet_drop": 0.06,
        "salvage_mode": "spot_persist", "wrong_side_thresh": 0.0009, "salvage_persist_s": 18.0,
        "clob_drop_thresh": 0.30, "final_45s_unwind": False,
    }

    def _run_var(label: str, overrides: Dict[str, Any], slices: Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]) -> Dict[str, Any]:
        cfg_v = {**base_15m_cfg, **overrides}
        s_tr, s_vl, s_ho = slices
        r_tr = evaluate_portfolio_fn(s_tr, cfg_v, latency_mode="500ms") if s_tr else {"trades": 0, "total_pnl": 0.0, "profit_factor": 0.0, "win_rate": 0.0}
        r_vl = evaluate_portfolio_fn(s_vl, cfg_v, latency_mode="500ms") if s_vl else {"trades": 0, "total_pnl": 0.0, "profit_factor": 0.0, "win_rate": 0.0}
        r_ho = evaluate_portfolio_fn(s_ho, cfg_v, latency_mode="500ms") if s_ho else {"trades": 0, "total_pnl": 0.0, "profit_factor": 0.0, "win_rate": 0.0}
        return {
            "label": label,
            "train": {"trades": r_tr["trades"], "pnl": r_tr["total_pnl"], "pf": r_tr["profit_factor"], "wr": r_tr["win_rate"]},
            "val": {"trades": r_vl["trades"], "pnl": r_vl["total_pnl"], "pf": r_vl["profit_factor"], "wr": r_vl["win_rate"]},
            "sealed_holdout": {"trades": r_ho["trades"], "pnl": r_ho["total_pnl"], "pf": r_ho["profit_factor"], "wr": r_ho["win_rate"]},
        }

    ablations_15m = [
        _run_var("BASELINE_15M_CASCADE_TAKER_90_480", {}, (tr_15, vl_15, ho_15)),
        _run_var("KEMNA_VORST_TWAP_BRIDGE_45_480", {"min_tte_15m": 45.0, "use_kemna_vorst": True}, (tr_15, vl_15, ho_15)),
        _run_var(
            "HYBRID_ZSPLIT_1.15_UNSHIELDED_MAKER",
            {"hybrid_z_split": True, "z_taker_cut": 1.15, "use_complement_shield": False, "include_maker_rebate": False},
            (tr_15, vl_15, ho_15),
        ),
        _run_var(
            "HYBRID_ZSPLIT_1.15_COMP_SHIELD_NO_REBATE",
            {"hybrid_z_split": True, "z_taker_cut": 1.15, "use_complement_shield": True, "include_maker_rebate": False},
            (tr_15, vl_15, ho_15),
        ),
        _run_var(
            "HYBRID_ZSPLIT_1.15_COMP_SHIELD_WITH_20PCT_REBATE",
            {"hybrid_z_split": True, "z_taker_cut": 1.15, "use_complement_shield": True, "include_maker_rebate": True},
            (tr_15, vl_15, ho_15),
        ),
        _run_var(
            "HYBRID_ZSPLIT_1.25_COMP_SHIELD_WITH_20PCT_REBATE",
            {"hybrid_z_split": True, "z_taker_cut": 1.25, "use_complement_shield": True, "include_maker_rebate": True},
            (tr_15, vl_15, ho_15),
        ),
        _run_var(
            "STUDENT_T_DF4_UNIT_VAR_JVM_1.15",
            {"v395_df": 4.0, "v395_jump_vol_mult": 1.15, "use_kemna_vorst": True},
            (tr_15, vl_15, ho_15),
        ),
        _run_var(
            "COINBASE_250MS_IMPULSE_VETO_2.5BPS",
            {"cb_250ms_veto_bps": -2.5},
            (tr_15, vl_15, ho_15),
        ),
    ]

    ablations_5m = []
    if sub_5m:
        for a_set, lbl_a in [(("BTC",), "BTC_5M_ONLY"), (("SOL",), "SOL_5M_CANARY"), (("BTC", "ETH", "SOL"), "ALL_CRYPTO_5M")]:
            ablations_5m.append(
                _run_var(
                    lbl_a,
                    {"assets": a_set, "horizons": ("5m",), "min_z": 0.80, "use_kemna_vorst": True},
                    (tr_5, vl_5, ho_5),
                )
            )

    return {
        "counts": {"subhourly_15m_total": len(sub_15m), "subhourly_5m_total": len(sub_5m)},
        "splits_15m": {"train": len(tr_15), "val": len(vl_15), "sealed_holdout": len(ho_15)},
        "splits_5m": {"train": len(tr_5), "val": len(vl_5), "sealed_holdout": len(ho_5)},
        "brier_calibration_selected_on_dev": best_cal,
        "brier_calibration_grid": brier_grid,
        "ablations_15m": ablations_15m,
        "ablations_5m": ablations_5m,
    }

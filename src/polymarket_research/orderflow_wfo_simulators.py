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

    # STEP 1: Primary Smart FAK at full ticket (`$16.50`)
    if 0.0 < eff_ask_lat < 0.99 and l1_ask_usd >= ticket_usd:
        vwap_full = round(max(eff_ask_lat, ask_t0 + min(0.03, slip20)), 4)
        if vwap_full <= target_limit_px and vwap_full <= max_px:
            return (vwap_full, v2_taker_fee_per_share(vwap_full, fee_rate), lat_s, 1.0, "STEP1_SMART_FAK")

    # STEP 2: Idea #1 Elastic Down-Snap (`$16.50 -> $12.00`) when L1 depth or multi-level sweep blocks full ticket
    if enable_elastic and elastic_usd < ticket_usd and 0.0 < eff_ask_lat < 0.99 and l1_ask_usd >= elastic_usd:
        scale_r = round(elastic_usd / ticket_usd, 4)
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

    # STEP 4: Phase 3A Passive `GTC postOnly=True` Maker-In Rescue (`0%` fee + `100ms` adverse-spot shield)
    if not enable_phase3a:
        return None
    t_p3a_start = round(lat_s + 0.20, 3)
    p3a_init = _clip_at_or_after(clips, t_p3a_start, (t_p3a_start, cush_lat, bid_lat, eff_ask_lat))
    ask_reb = float(p3a_init[3])
    bid_reb = float(p3a_init[2]) if float(p3a_init[2]) > 0.0 else bid_lat
    cush_init = float(p3a_init[1])
    if eff_cush > 0.0 and cush_init < eff_cush * (1.0 - shield_decay):
        return None
    if ask_reb <= min_px + 0.005 or (ask_t0 - ask_reb) >= 0.04:
        return None

    # postOnly resting bid strictly >= 1 tick below ask_reb and within [min_px, max_px]
    maker_px = round(min(max_px, ask_reb - 0.01, max(bid_reb, ask_t0)), 2)
    if maker_px < min_px or maker_px >= ask_reb - 1e-6:
        return None

    p3a_mult = 1.0 if l1_ask_usd >= ticket_usd else round(elastic_usd / ticket_usd, 4)
    t_deadline = t_p3a_start + phase3a_ttl_s
    for dt_c, cush_c, b_c, a_c in clips:
        if dt_c < t_p3a_start - 1e-6:
            continue
        if dt_c > t_deadline + 1e-6:
            break
        # 100ms Adverse-Spot Shield: cancel immediately BEFORE passive toxic fill if cushion decays > 50%
        if eff_cush > 0.0 and (cush_c <= 0.0 or cush_c < eff_cush * (1.0 - shield_decay)):
            return None
        # Queue-depletion passive fill: ask crosses down to/through maker_px while spot shield holds
        if 0.0 < a_c <= maker_px:
            return (maker_px, 0.0, round(dt_c, 3), p3a_mult, "STEP4_PHASE3A_MAKER_RESCUE")

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

    tick = 0.001 if (a_anc >= 0.96 or a_anc <= 0.04) else 0.01
    spr = round(a_anc - b_anc, 4)
    allow_join_1c = bool(cfg.get("allow_join_1c_mid", True))
    min_obi_1c = float(cfg.get("min_obi_join_1c", -0.15))
    min_obi_any = float(cfg.get("min_obi_any", -0.35))
    min_hdg_mult = float(cfg.get("min_hdg_depth_mult", 2.5))
    max_post_net = float(cfg.get("max_post_net", 0.988))
    adv_cancel_bps = float(cfg.get("adverse_spot_cancel_bps", 2.5))

    if obi_anc < min_obi_any or hdg_sh < max(15.0, min_hdg_mult * sh):
        return {"posted": False, "filled": False, "hedged": False, "pnl_usd": 0.0, "scratched": False}

    if spr >= 2.0 * tick - 1e-9:
        cand_bid = round(min(b_anc + tick, a_anc - tick), 3 if tick < 0.01 else 2)
        q_front = True
    elif allow_join_1c and spr >= 0.01 - 1e-9 and 0.15 <= a_anc <= 0.85 and obi_anc >= min_obi_1c:
        cand_bid = round(b_anc, 2)
        q_front = False
    else:
        return {"posted": False, "filled": False, "hedged": False, "pnl_usd": 0.0, "scratched": False}

    hdg_eff0 = a_hdg + v2_taker_fee_per_share(a_hdg, fr)
    scale = 1000.0 if tick < 0.01 else 100.0
    max_anc = math.floor((max_post_net - hdg_eff0) * scale + 1e-9) / scale
    bid_px = min(cand_bid, max_anc)
    if bid_px < round(b_anc - (tick if q_front else 0.0), 3) or bid_px <= 0.02 or bid_px >= a_anc:
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

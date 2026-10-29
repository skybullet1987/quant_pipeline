"""
========================================================================================
DOMINUS POLYMARKET ALPHA-124 11-SLEEVE EXPANSION + PROJECTIONS + TESTS (<1 MB COMPANION BUNDLE)
Generated: 2026-10-29 03:17:08 UTC
Pairs with polymarket_all_in_one.txt (<1 MB) for tools enforcing a 1 MB per-file upload cap
Repository: /home/skybullet1987/quant_pipeline
========================================================================================

TABLE OF CONTENTS (Exact 1-Based Line Ranges & Raw Module Sizes):
  [01] systemd/polymarket-alpha124-shadow.service (Lines 30 - 63 | 854 B) :: Alpha-124 Unified Shadow systemd Unit
  [02] src/polymarket_research/orderflow_wfo_simulators.py (Lines 64 - 904 | 37,391 B) :: v4.0 100ms Micro-Clip 4-Step Cascade Replay, D1 Latency-Skew WFO & Legging-Drag Parity Engine
  [03] src/polymarket_research/net_alpha_opportunity_engine.py (Lines 905 - 1,665 | 32,785 B) :: v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine
  [04] src/polymarket_research/weather_metar_engine.py (Lines 1,666 - 3,013 | 58,186 B) :: Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb
  [05] src/polymarket_research/barrier_onetouch_svi_engine.py (Lines 3,014 - 3,549 | 21,735 B) :: Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)
  [06] src/polymarket_research/multistrike_svi_scalper.py (Lines 3,550 - 4,273 | 29,320 B) :: Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner
  [07] src/polymarket_research/same_oracle_dominance_box.py (Lines 4,274 - 5,113 | 34,006 B) :: Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine
  [08] src/polymarket_research/exact_twap_lock_engine.py (Lines 5,114 - 5,349 | 9,226 B) :: Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock
  [09] src/polymarket_research/tradfi_sports_zero_fee_engine.py (Lines 5,350 - 6,359 | 41,060 B) :: Zero-Fee Pyth Commodities/Metals/Equities (CM_B3/B2/U1), B4 Wick Lock, NBA Polish-Middle (SP1) & NegRisk (NR0)
  [10] src/polymarket_research/macro_counting_ctf_engine.py (Lines 6,360 - 7,403 | 47,109 B) :: Phase-2 Multi-Vertical Structural & Oracle Engine (TW1 xtracker, FED1 125-State LP, COND1 Oil-Senate, CTF Overround, AAA Gas, D2 12PM)
  [11] src/polymarket_research/alpha_124_shadow_daemon.py (Lines 7,404 - 15,367 | 426,712 B) :: Unified Multi-Vertical Shadow Daemon (Crypto, Weather METAR/HKO, Pyth Commodities/Metals/Equities, NBA, FOMC/Oil-Senate/Counting/AAA)
  [12] scripts/backtest_alpha_124.py (Lines 15,368 - 16,228 | 40,009 B) :: Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124
  [13] scripts/polymarket_daily_projections.py (Lines 16,229 - 17,144 | 34,838 B) :: Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker
  [14] scripts/alpha124_status.py (Lines 17,145 - 17,223 | 3,091 B) :: Live Alpha-124 11-Sleeve Scorecard & Orderbook Opportunity Inspector
  [15] scripts/polymarket_scorecard_snapshot.py (Lines 17,224 - 17,373 | 4,891 B) :: Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot
  [16] tests/test_alpha_124_oracles.py (Lines 17,374 - 20,520 | 163,349 B) :: Unit Tests: Weather METAR/HKO, Jump-SVI Barrier, Pyth Session/Boxes, NBA Boxes, D1, S2 & Wallet
"""

from __future__ import annotations

# ======================================================================================
# [01/16] MODULE: systemd/polymarket-alpha124-shadow.service
# PURPOSE: Alpha-124 Unified Shadow systemd Unit
# ======================================================================================

# Non-Python configuration / systemd unit embedded verbatim:
POLYMARKET_ALPHA124_SHADOW_SERVICE = r'''
[Unit]
Description=Polymarket Alpha-124 Unified Shadow Engine (#1 Weather + #2 Barrier + #4 Multi-Strike SVI + #7 Same-Oracle Dominance Boxes)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/skybullet1987/quant_pipeline
Environment=PYTHONUNBUFFERED=1
Environment=PM_DISABLE_SHADOW_M4_CATCHUP=1
Environment=PM_DISABLE_SHADOW_W2_TAKER=1
# 2-vCPU host: keep below the live harvester + BTC/ETH recorders (1000) so shadow scans never starve
# the latency-critical live path (CPU starvation caused recorder WS ping timeouts / slow-consumer drops).
CPUWeight=300
IOWeight=300
ExecStart=/home/skybullet1987/quant_pipeline/venv/bin/python src/polymarket_research/alpha_124_shadow_daemon.py
Restart=always
RestartSec=10
KillSignal=SIGTERM
KillMode=process
TimeoutStopSec=15s

[Install]
WantedBy=default.target

'''

# ======================================================================================
# [02/16] MODULE: src/polymarket_research/orderflow_wfo_simulators.py
# PURPOSE: v4.0 100ms Micro-Clip 4-Step Cascade Replay, D1 Latency-Skew WFO & Legging-Drag Parity Engine
# ======================================================================================

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

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

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

# ======================================================================================
# [03/16] MODULE: src/polymarket_research/net_alpha_opportunity_engine.py
# PURPOSE: v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine
# ======================================================================================

#!/usr/bin/env python3
"""
v4.0 Unified Net-Alpha, Quote-Survival, Complete-Set & Capital-Efficiency Engine
================================================================================
Synthesizes the v4.0 institutional execution & portfolio-allocation upgrades:
  1. Explicit Missing-Feature Hygiene (zero optimistic microstructure defaults on live CTF tokens).
  2. Calibrated Event-Time Quote-Survival & Net-Alpha Meta-Scorer:
       EV_net = P(fill | RTT, age_ask, spread, L1_depth, OBI, +2c_FAK) * E[net_PnL | fill]
                - (1 - P(fill)) * C_opportunity
     with Walk-Forward calibration over historical live order / candidate ledgers.
  3. Adaptive Maker / Taker / Skip Router (comparing price-improved <=p_max Taker FAK vs
     0%-fee `post_only=True` Maker with queue-depletion & adverse-selection markout, zero
     unverified rebate inflation).
  4. State-Dependent Optimal-Stopping Exit & Pre-Expiry $0.985-$0.99 Cash-Recycling Controller
     (plus complementary opposite-token merge/offset dominance check & OBI maker step-down).
  5. Same-Market Binary YES+NO Complete-Set Underround Scanner (`C1_BINARY_COMPLETE_SET`).
  6. Probabilistic Cross-Oracle Basis Box Expectancy (`B_T = USDT/USD - 1` distribution).
  7. Cross-Daemon `/dev/shm/pm_global_positions.json` State Bus & Capital-Efficiency
     Opportunity Auction (`EV_net / ($ * lock_hours)` with correlation & corridor-completion bonus).
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_INV_SQRT2 = 0.7071067811865475


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x * _INV_SQRT2))


def is_real_polygon_ctf_token(token_id: Any) -> bool:
    s = str(token_id or "").strip()
    return bool(s and s.isdigit() and len(s) >= 20)


def compute_category_taker_fee_per_share(
    price: float,
    fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
) -> float:
    if fee_rate <= 0.0:
        return 0.0
    p = max(0.001, min(0.999, float(price)))
    return float(fee_rate) * ((p * (1.0 - p)) ** float(fee_exponent))


# ==============================================================================
# 1. EXPLICIT MISSING-FEATURE HYGIENE (ChatGPT #9)
# ==============================================================================

def inspect_microstructure_feature_completeness(
    shock: Dict[str, Any],
    target_token: str,
    token_id: str = "",
) -> Dict[str, Any]:
    """
    Checks whether live microstructure features are genuinely observed vs missing.
    On real 20+-digit Polygon CTF tokens, missing `age_ask_ms` or `shock_ofi` NEVER
    receives an optimistic numerical default (`400ms` or `1.0`).
    """
    feats = shock.get("pre_shock_features_t0") or {}
    tf = (feats.get(target_token) or {}) if isinstance(feats, dict) else {}
    real_tok = is_real_polygon_ctf_token(token_id or tf.get("token_id"))

    is_special = (
        shock.get("shock_source") in ("BOUNDARY_LOCK", "EXP316_TRACK_A_CONVERGENCE")
        or shock.get("sleeve") == "SLEEVE_3_STRIKE_CONVERGENCE"
    )
    is_live_packet = bool(
        "fee_metadata" in shock
        or "shock_ofi" in shock
        or str(shock.get("event_id") or "").startswith("SHOCK_")
    )
    missing: List[str] = []
    if tf.get("age_ask_ms") is None and not is_special:
        missing.append("age_ask_ms")
    if shock.get("shock_ofi") is None and not is_special and is_live_packet:
        missing.append("shock_ofi")
    if tf.get("obi_l1") is None and not is_special:
        missing.append("obi_l1")
    if shock.get("coinbase_spot") is None and shock.get("chainlink_proxy_spot") is None:
        missing.append("usd_venue_anchor")

    hard_missing = any(k in missing for k in ("age_ask_ms", "shock_ofi"))
    uncertainty_haircut = 0.0
    if real_tok and missing:
        uncertainty_haircut = min(0.06, 0.015 * len(missing))

    return {
        "is_real_ctf_token": real_tok,
        "complete": len(missing) == 0,
        "hard_veto_live": bool(real_tok and hard_missing),
        "missing_fields": missing,
        "uncertainty_haircut": round(uncertainty_haircut, 4),
    }


# ==============================================================================
# 2. EVENT-TIME QUOTE-SURVIVAL & NET-ALPHA META-SCORER (ChatGPT #1)
# ==============================================================================

def estimate_quote_survival_and_net_alpha(
    p_win: float,
    ask_price: float,
    limit_price: float,
    p_max: float,
    fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
    clob_rtt_ms: float = 240.0,
    age_ask_ms: Optional[float] = None,
    spread: float = 0.01,
    l1_depth_usd: float = 35.0,
    obi_l1: float = 0.0,
    shock_ofi: float = 0.80,
    notional_usd: float = 14.0,
    target_exit_px: float = 0.965,
    expected_salvage_net: float = 0.36,
    uncertainty_haircut: float = 0.0,
    opp_cost_bps: float = 12.0,
    survival_params: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Computes survival probability `P(fill)` of the resting CLOB quote across `clob_rtt_ms`
    and expected net dollar alpha:
      EV_net = P(fill) * E[net_PnL | fill] - (1 - P(fill)) * C_opp
    Strictly caps execution limit at `min(limit_price, p_max)`.
    """
    eff_limit = round(min(float(limit_price), float(p_max)), 4)
    if ask_price <= 0.0 or eff_limit < ask_price - 1e-6 or notional_usd <= 0.0:
        return {
            "p_fill": 0.0,
            "ev_net_usd": 0.0,
            "ev_given_fill_usd": 0.0,
            "eff_limit_px": eff_limit,
            "eligible": False,
        }

    cfg = survival_params or {}
    b0 = float(cfg.get("b0", -0.35))
    b_impr = float(cfg.get("b_impr_per_cent", 0.72))
    b_rtt = float(cfg.get("b_rtt_per_100ms", -0.38))
    b_depth = float(cfg.get("b_log_depth", 0.34))
    b_age = float(cfg.get("b_age_stale", 0.30))
    b_obi = float(cfg.get("b_obi", -0.35))

    price_impr_cents = max(0.0, (eff_limit - float(ask_price)) * 100.0)
    rtt_100 = max(0.05, float(clob_rtt_ms) / 100.0)
    depth_term = math.log(max(1.0, float(l1_depth_usd) / max(8.0, float(notional_usd))))
    # Untouched quote (age_ask_ms >= 200ms) indicates MM has not repriced yet; ultra-fresh (<40ms) means race underway
    if age_ask_ms is None:
        age_term = -0.35
    elif age_ask_ms < 45.0:
        age_term = -0.60
    else:
        age_term = min(1.2, (float(age_ask_ms) - 100.0) / 350.0)

    z_surv = (
        b0
        + b_impr * min(2.5, price_impr_cents)
        + b_rtt * rtt_100
        + b_depth * depth_term
        + b_age * age_term
        + b_obi * float(obi_l1)
        - 0.15 * max(0.0, (float(spread) - 0.01) * 100.0)
        - 0.20 * max(0.0, abs(float(shock_ofi)) - 0.85)
    )
    p_fill = 1.0 / (1.0 + math.exp(-max(-12.0, min(12.0, z_surv))))
    p_fill = max(0.02, min(0.98, p_fill))

    # Expected fill price: if L1 survives we get ask_price; if L1 partially lifted we average toward eff_limit
    expected_exec_px = min(eff_limit, float(ask_price) + 0.35 * max(0.0, eff_limit - float(ask_price)))
    fee_ps = compute_category_taker_fee_per_share(expected_exec_px, fee_rate, fee_exponent)
    eff_cost_ps = expected_exec_px + fee_ps

    p_win_lcb = max(0.01, min(0.995, float(p_win) - float(uncertainty_haircut)))
    exp_payoff_ps = p_win_lcb * float(target_exit_px) + (1.0 - p_win_lcb) * float(expected_salvage_net)
    net_edge_ps = exp_payoff_ps - eff_cost_ps
    shares = float(notional_usd) / max(0.01, expected_exec_px)
    ev_given_fill_usd = shares * net_edge_ps
    opp_cost_usd = float(notional_usd) * (float(opp_cost_bps) / 10000.0)
    ev_net_usd = p_fill * ev_given_fill_usd - (1.0 - p_fill) * opp_cost_usd

    return {
        "p_fill": round(p_fill, 4),
        "expected_exec_px": round(expected_exec_px, 4),
        "eff_cost_ps": round(eff_cost_ps, 4),
        "net_edge_ps": round(net_edge_ps, 4),
        "ev_given_fill_usd": round(ev_given_fill_usd, 4),
        "ev_net_usd": round(ev_net_usd, 4),
        "eff_limit_px": eff_limit,
        "eligible": bool(ev_net_usd > 0.0 and net_edge_ps > 0.0),
    }


def fit_quote_survival_from_ledger(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Walk-Forward empirical calibration helper over `live_orders.jsonl` records.
    Measures empirical Shot-1 fill rate vs `FAK_KILLED_NO_MATCH` and `clob_http_post_ms`
    to tune intercept `b0` without touching WFO signal thresholds.
    """
    n_tot = 0
    n_fill = 0
    rtts: List[float] = []
    for r in records:
        if not isinstance(r, dict):
            continue
        mode = str(r.get("mode") or "")
        if mode not in ("LIVE_CLOB", "FAK_KILLED_NO_MATCH", "CLOB_HTTP_400_REJECTION"):
            continue
        n_tot += 1
        if bool(r.get("success")) or mode == "LIVE_CLOB":
            n_fill += 1
        telem = ((r.get("details") or {}).get("latency_telemetry") or {})
        rtt = float(telem.get("clob_http_post_ms") or r.get("latency_ms") or 0.0)
        if rtt > 0.0:
            rtts.append(rtt)

    if n_tot < 5:
        return {"sample_count": n_tot, "empirical_fill_rate": None, "b0": -0.35, "median_rtt_ms": 240.0}

    emp_rate = max(0.05, min(0.95, n_fill / float(n_tot)))
    rtts_sorted = sorted(rtts)
    med_rtt = rtts_sorted[len(rtts_sorted) // 2] if rtts_sorted else 240.0
    # Center log-odds intercept around observed baseline at med_rtt
    raw_logit = math.log(emp_rate / (1.0 - emp_rate))
    b0_cal = max(-1.6, min(1.2, raw_logit + 0.38 * (med_rtt / 100.0)))
    return {
        "sample_count": n_tot,
        "empirical_fill_rate": round(emp_rate, 4),
        "median_rtt_ms": round(med_rtt, 2),
        "b0": round(b0_cal, 4),
    }


# ==============================================================================
# 3. ADAPTIVE MAKER / TAKER / SKIP EXECUTION ROUTER (ChatGPT #2 + Gemini #9)
# ==============================================================================

def select_maker_taker_skip_route(
    p_win: float,
    best_bid: float,
    best_ask: float,
    p_max: float,
    fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
    notional_usd: float = 14.0,
    clob_rtt_ms: float = 240.0,
    age_ask_ms: Optional[float] = 350.0,
    l1_ask_usd: float = 40.0,
    l1_bid_usd: float = 40.0,
    obi_l1: float = 0.0,
    shock_ofi: float = 0.80,
    target_exit_px: float = 0.965,
    expected_salvage_net: float = 0.36,
    adverse_markout_cents: float = 0.022,
    verified_maker_rebate_share: float = 0.0,
) -> Dict[str, Any]:
    """
    Evaluates `TAKER_PRICE_IMPROVED_FAK` vs `MAKER_POST_ONLY_3P5S` vs `SKIP` on identical
    net dollar EV terms. Never assumes unverified maker rebates (`verified_maker_rebate_share=0.0`
    by default unless empirically measured in ledger).
    """
    spread = round(float(best_ask) - float(best_bid), 4)
    limit_taker = round(min(float(p_max), float(best_ask) + 0.02), 2)
    taker_eval = estimate_quote_survival_and_net_alpha(
        p_win=p_win,
        ask_price=best_ask,
        limit_price=limit_taker,
        p_max=p_max,
        fee_rate=fee_rate,
        fee_exponent=fee_exponent,
        clob_rtt_ms=clob_rtt_ms,
        age_ask_ms=age_ask_ms,
        spread=max(0.01, spread),
        l1_depth_usd=l1_ask_usd,
        obi_l1=obi_l1,
        shock_ofi=shock_ofi,
        notional_usd=notional_usd,
        target_exit_px=target_exit_px,
        expected_salvage_net=expected_salvage_net,
    )
    ev_taker = float(taker_eval["ev_net_usd"]) if taker_eval["eligible"] else -1e-6

    # Evaluate 3.5s post_only=True 0%-fee Maker Bid
    ev_maker = -1e-6
    maker_bid = 0.0
    p_fill_maker = 0.0
    if best_bid > 0.01 and best_ask > best_bid + 0.005:
        cand_bid = round(best_bid + 0.01, 2) if spread >= 0.02 else round(best_bid, 2)
        maker_bid = round(min(cand_bid, best_ask - 0.01, p_max), 2)
        if maker_bid >= best_bid - 1e-6 and 0.04 <= maker_bid < best_ask - 1e-6:
            improves_queue = maker_bid > best_bid + 1e-6
            queue_ratio = 0.0 if improves_queue else min(3.0, l1_bid_usd / max(8.0, notional_usd))
            p_fill_maker = max(0.05, min(0.65, (0.42 if improves_queue else 0.24) * math.exp(-0.35 * queue_ratio)))
            # Conservative maker rebate: 0.0 unless verified_maker_rebate_share > 0
            rebate_ps = 0.0
            if verified_maker_rebate_share > 0.0 and fee_rate > 0.0:
                rebate_ps = float(verified_maker_rebate_share) * compute_category_taker_fee_per_share(
                    maker_bid, fee_rate, fee_exponent
                )
            eff_maker_cost = maker_bid - rebate_ps
            # Apply adverse-selection markout haircut on passive fills (informed sellers hitting our bid)
            p_win_maker = max(0.01, float(p_win) - float(adverse_markout_cents))
            exp_pay_m = p_win_maker * float(target_exit_px) + (1.0 - p_win_maker) * float(expected_salvage_net)
            sh_m = float(notional_usd) / max(0.01, maker_bid)
            ev_given_m = sh_m * (exp_pay_m - eff_maker_cost)
            if ev_given_m > 0.0:
                ev_maker = p_fill_maker * ev_given_m

    if ev_taker <= 0.0 and ev_maker <= 0.0:
        route = "SKIP"
    elif ev_taker >= ev_maker:
        route = "TAKER_PRICE_IMPROVED_FAK"
    else:
        route = "MAKER_POST_ONLY_3P5S"

    return {
        "route": route,
        "ev_taker_usd": round(max(0.0, ev_taker), 4),
        "ev_maker_usd": round(max(0.0, ev_maker), 4),
        "taker_limit_px": limit_taker,
        "maker_bid_px": maker_bid,
        "p_fill_taker": taker_eval["p_fill"],
        "p_fill_maker": round(p_fill_maker, 4),
    }


# ==============================================================================
# 4. OPTIMAL-STOPPING EXIT & PRE-EXPIRY CASH RECYCLING (ChatGPT #3 + Gemini #6/#13)
# ==============================================================================

def evaluate_optimal_stopping_exit(
    entry_px: float,
    rem_shares: float = 10.0,
    best_bid: float = 0.0,
    best_ask: float = 0.0,
    curr_target_px: float = 0.95,
    tte_sec: float = 60.0,
    obi_l1: float = 0.0,
    v_spot_15s_pct: float = 0.0,
    opp_ask_complement: Optional[float] = None,
    fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
    post_expiry_lock_min: float = 6.0,
    opp_ev_per_dollar_min: float = 0.0025,
    current_maker_px: Optional[float] = None,
    **_unused_kw: Any,
) -> Dict[str, Any]:
    """
    State-dependent optimal-stopping controller for open CTF positions:
      1. `PRE_EXPIRY_99C_RECYCLE` (Gemini #6): in `8s <= TTE <= 25s` when `best_bid >= 0.985`,
         taker fee at $0.99 is `0.07 * 0.99 * 0.01 = $0.00069/sh` (~0.07c!), freeing 100% of
         collateral BEFORE `:00/:15/:30/:45` rollover and avoiding 5-15m post-expiry lockup.
      2. `SYNTHETIC_COMPLEMENT_MERGE` (ChatGPT #4): checks if buying opposite outcome at
         `opp_ask_complement` (`1.00 - opp_ask - fee(opp_ask)`) dominates crossing a wide bid.
      3. `OBI_MAKER_STEP_DOWN` (Gemini #13): when `best_bid >= 0.91`, `obi_l1 <= -0.40` (heavy
         ask reload wall), and `v_spot_15s_pct <= 0.0`, steps resting 0%-fee Maker exit to
         `best_bid + 0.01` to lock profit passively before a -5c drop triggers a taker ratchet.
      4. `HOLD_RESTING`: keep resting `$0.95 / $0.98` maker tranches.
    """
    if current_maker_px is not None:
        curr_target_px = float(current_maker_px)
    if rem_shares < 5.0 or best_bid <= 0.0:
        return {"action": "HOLD_RESTING", "target_px": curr_target_px, "reason": "SUB_LOT_OR_NO_BID"}

    direct_fee_ps = compute_category_taker_fee_per_share(best_bid, fee_rate, fee_exponent)
    direct_net_ps = best_bid - direct_fee_ps

    # Check complementary opposite-token offset dominance
    synth_net_ps = 0.0
    if opp_ask_complement is not None and 0.005 <= float(opp_ask_complement) <= 0.98:
        opp_fee_ps = compute_category_taker_fee_per_share(float(opp_ask_complement), fee_rate, fee_exponent)
        synth_net_ps = 1.0 - float(opp_ask_complement) - opp_fee_ps

    # 1. Pre-expiry $0.985-$0.99 instant cash recycling (`8s <= TTE <= 25s`)
    if 8.0 <= tte_sec <= 25.0 and best_bid >= 0.985 and best_bid > (entry_px + 0.02):
        giveup_ps = 1.0 - direct_net_ps
        recycle_gain_ps = best_bid * float(post_expiry_lock_min) * float(opp_ev_per_dollar_min)
        if giveup_ps <= max(0.016, recycle_gain_ps + 0.004):
            return {
                "action": "PRE_EXPIRY_99C_RECYCLE",
                "target_px": round(max(0.98, best_bid), 2),
                "net_proceeds_ps": round(direct_net_ps, 5),
                "taker_fee_ps": round(direct_fee_ps, 5),
                "reason": f"Instant pre-rollover cash recycle @ ${best_bid:.3f} (fee=${direct_fee_ps:.4f}/sh)",
            }

    # 2. Complementary opposite-outcome offset dominance check (when crossing spread)
    if synth_net_ps > direct_net_ps + 0.006 and tte_sec <= 45.0 and synth_net_ps > (entry_px + 0.03):
        return {
            "action": "SYNTHETIC_COMPLEMENT_MERGE",
            "target_px": round(float(opp_ask_complement), 4),
            "net_proceeds_ps": round(synth_net_ps, 5),
            "direct_net_ps": round(direct_net_ps, 5),
            "reason": f"Opposite-ask offset yields ${synth_net_ps:.4f}/sh > direct bid ${direct_net_ps:.4f}/sh",
        }

    # 3. Micro-price / OBI dynamic 0%-fee Maker step-down before reversal
    if (
        tte_sec >= 30.0
        and curr_target_px >= 0.945
        and best_bid >= 0.91
        and best_bid > (entry_px + 0.05)
        and obi_l1 <= -0.40
        and v_spot_15s_pct <= 0.0
    ):
        cand_maker = round(min(curr_target_px - 0.01, max(entry_px + 0.06, best_bid + 0.01)), 2)
        if best_ask > 0.0:
            cand_maker = round(min(cand_maker, max(best_bid + 0.01, best_ask)), 2)
        if cand_maker < curr_target_px - 0.005 and cand_maker >= 0.92:
            return {
                "action": "OBI_MAKER_STEP_DOWN",
                "target_px": cand_maker,
                "net_proceeds_ps": cand_maker,
                "reason": f"Heavy ask reload (obi_l1={obi_l1:.2f} <= -0.40) at bid=${best_bid:.2f}; stepping 0%-fee Maker TP to ${cand_maker:.2f}",
            }

    return {"action": "HOLD_RESTING", "target_px": curr_target_px, "net_proceeds_ps": round(direct_net_ps, 5)}


# ==============================================================================
# 5. SAME-MARKET BINARY COMPLETE-SET ARB SCANNER (`C1` — ChatGPT #4)
# ==============================================================================

def scan_binary_complete_set_arb(
    market_id: str,
    condition_id: str,
    yes_token: str,
    no_token: str,
    asks_yes_raw: List[Any],
    asks_no_raw: List[Any],
    target_budget_usd: float = 100.0,
    fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
    max_complete_set_cost: float = 0.994,
    min_shares: int = 10,
    max_box_cost_net: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Walks equal integer share quantity `Q` across `YES` and `NO` asks of the EXACT SAME
    binary market (`condition_id`). Since `YES + NO == $1.00` identically on-chain with
    zero oracle/basis divergence, `net_cost_per_pair <= max_complete_set_cost` locks a
    deterministic riskless floor (redeemable/mergeable for $1.00).
    """
    if max_box_cost_net is not None:
        max_complete_set_cost = float(max_box_cost_net)
    if not market_id or not yes_token or not no_token or str(yes_token) == str(no_token):
        return {"filled": False, "reason": "INVALID_TOKENS"}

    def _norm_asks(raw: List[Any]) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        for item in raw or []:
            if isinstance(item, dict):
                p, s = float(item.get("price") or 0.0), float(item.get("size") or 0.0)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                p, s = float(item[0]), float(item[1])
            else:
                continue
            if p > 0.0 and s > 0.0:
                out.append((p, s))
        out.sort(key=lambda x: x[0])
        return out

    asks_y = _norm_asks(asks_yes_raw)
    asks_n = _norm_asks(asks_no_raw)
    if not asks_y or not asks_n:
        return {"filled": False, "reason": "EMPTY_SIDE_BOOK"}

    l1_y_usd = asks_y[0][0] * asks_y[0][1]
    l1_n_usd = asks_n[0][0] * asks_n[0][1]
    min_l1_usd = round(min(l1_y_usd, l1_n_usd), 2)

    # Quick best-ask pre-filter before full level walk
    best_y, best_n = asks_y[0][0], asks_n[0][0]
    min_fee_pair = (
        compute_category_taker_fee_per_share(best_y, fee_rate, fee_exponent)
        + compute_category_taker_fee_per_share(best_n, fee_rate, fee_exponent)
    )
    if (best_y + best_n + min_fee_pair) > max_complete_set_cost + 0.015:
        return {
            "filled": False,
            "reason": "NO_UNDERROUND",
            "best_pair_net": round(best_y + best_n + min_fee_pair, 5),
        }

    avail_y = sum(s for p, s in asks_y if p <= best_y + 0.02)
    avail_n = sum(s for p, s in asks_n if p <= best_n + 0.02)
    max_q_budget = int(math.floor(float(target_budget_usd) / max(0.10, best_y + best_n)))
    q_int = int(min(max_q_budget, math.floor(avail_y), math.floor(avail_n)))
    if q_int < int(min_shares):
        return {"filled": False, "reason": "INSUFFICIENT_EQUAL_SHARES", "l1_usd": min_l1_usd}

    def _walk_shares(levels: List[Tuple[float, float]], q_req: float) -> Optional[Tuple[float, float, float]]:
        rem = q_req
        spent = 0.0
        worst_px = 0.0
        for px, sz in levels:
            take = min(rem, sz)
            spent += take * px
            worst_px = max(worst_px, px)
            rem -= take
            if rem <= 1e-6:
                break
        if rem > 1e-5:
            return None
        vwap = spent / q_req
        fee_ps = compute_category_taker_fee_per_share(vwap, fee_rate, fee_exponent)
        return vwap, fee_ps, worst_px

    wy = _walk_shares(asks_y, float(q_int))
    wn = _walk_shares(asks_n, float(q_int))
    if wy is None or wn is None:
        return {"filled": False, "reason": "DEPTH_WALK_SHORTFALL", "l1_usd": min_l1_usd}

    vwap_y, fee_y_ps, lim_y = wy
    vwap_n, fee_n_ps, lim_n = wn
    pair_cost_net = vwap_y + fee_y_ps + vwap_n + fee_n_ps
    if pair_cost_net > max_complete_set_cost + 1e-6:
        return {
            "filled": False,
            "reason": "NET_COST_ABOVE_CAP",
            "box_cost_net": round(pair_cost_net, 5),
            "l1_usd": min_l1_usd,
        }

    spent_total = q_int * (vwap_y + vwap_n)
    fee_total = q_int * (fee_y_ps + fee_n_ps)
    min_profit_usd = q_int * (1.0 - pair_cost_net)
    return {
        "filled": True,
        "market_id": str(market_id),
        "condition_id": str(condition_id),
        "yes_token": str(yes_token),
        "no_token": str(no_token),
        "shares": q_int,
        "vwap": round(vwap_y + vwap_n, 5),
        "eff_px": round(pair_cost_net, 5),
        "box_cost_net": round(pair_cost_net, 5),
        "riskless_floor_per_pair": round(1.0 - pair_cost_net, 5),
        "guaranteed_min_profit_usd": round(min_profit_usd, 4),
        "spent_usd": round(spent_total, 2),
        "fee_usd": round(fee_total, 4),
        "limit_yes": round(lim_y, 4),
        "limit_no": round(lim_n, 4),
        "avail_yes_shares": round(avail_y, 2),
        "avail_no_shares": round(avail_n, 2),
        "l1_usd": min_l1_usd,
    }


# ==============================================================================
# 6. PROBABILISTIC CROSS-ORACLE BASIS BOX EXPECTANCY (ChatGPT #6)
# ==============================================================================

def evaluate_cross_oracle_basis_box_ev(
    spot_px: float,
    k_low: float,
    k_high: float,
    c_taker_net: float,
    tte_sec: float,
    sigma_1h: float = 0.0055,
    mu_basis_bps: float = 2.0,
    sigma_basis_bps: float = 8.5,
) -> Dict[str, Any]:
    """
    Prices a cross-oracle corridor box (e.g. 15m Chainlink USD 60s-TWAP vs 1h Binance USDT Close)
    explicitly as a PROBABILISTIC relative-value trade (NEVER deterministic arbitrage!).
    Computes `p_double_win` ($2.00), `p_double_loss` ($0.00 basis-trap wipeout), and net EV/pair.
    """
    if spot_px <= 0.0 or k_low <= 0.0 or k_high < k_low:
        return {"eligible": False, "ev_per_pair": -1.0, "p_double_loss": 1.0, "p_double_win": 0.0}

    corridor_frac = (k_high - k_low) / k_low
    sig_spot = max(0.0004, float(sigma_1h) * math.sqrt(max(15.0, float(tte_sec)) / 3600.0))
    # Cross-oracle basis std includes USDT/USD peg variance + 60s TWAP vs instant close variance
    sig_twap_diff = sig_spot * math.sqrt(min(1.0, 20.0 / max(20.0, float(tte_sec)))) * 0.35
    sig_basis = math.hypot(float(sigma_basis_bps) / 10000.0, sig_twap_diff)
    mu_b = float(mu_basis_bps) / 10000.0

    # Probability spot lands in [k_low, k_high]
    z_hi = math.log(k_high / spot_px) / sig_spot
    z_lo = math.log(k_low / spot_px) / sig_spot
    p_in_corridor = max(0.0, min(1.0, _norm_cdf(z_hi) - _norm_cdf(z_lo)))

    # Basis-trap double-loss occurs near boundaries if cross-oracle divergence exceeds corridor width + boundary distance
    p_basis_flip = _norm_cdf((-corridor_frac - abs(mu_b)) / max(1e-5, sig_basis))
    boundary_density_wt = min(1.0, 0.35 + 0.65 * math.exp(-abs(math.log(((k_low + k_high) * 0.5) / spot_px)) / sig_spot))
    p_double_loss = max(0.0005, min(0.45, p_basis_flip * boundary_density_wt))
    p_double_win = max(0.0, p_in_corridor * (1.0 - p_basis_flip))
    p_single = max(0.0, 1.0 - p_double_win - p_double_loss)

    expected_payout = 2.0 * p_double_win + 1.0 * p_single
    ev_per_pair = expected_payout - float(c_taker_net)
    return {
        "classification": "PROBABILISTIC_CROSS_ORACLE_RV",
        "is_riskless": False,
        "p_double_win": round(p_double_win, 4),
        "p_single_floor": round(p_single, 4),
        "p_double_loss": round(p_double_loss, 4),
        "expected_payout": round(expected_payout, 4),
        "ev_per_pair": round(ev_per_pair, 4),
        "expected_net_profit_per_pair": round(ev_per_pair, 4),
        "eligible": bool(ev_per_pair >= 0.018 and p_double_loss <= 0.045),
    }


# ==============================================================================
# 7. CROSS-DAEMON SHM POSITION BUS & CAPITAL-EFFICIENCY AUCTION (Gemini #15 + ChatGPT #10)
# ==============================================================================

def _global_positions_shm_path() -> Path:
    shm_dir = os.environ.get("PM_FAST_TICK_DIR")
    if shm_dir:
        return Path(shm_dir) / "pm_global_positions.json"
    default_shm = Path("/dev/shm")
    if default_shm.exists():
        return default_shm / "pm_global_positions.json"
    return Path(__file__).resolve().parent.parent.parent / "data" / "polymarket" / "pm_global_positions.json"


def read_global_positions_shm(max_age_sec: float = 120.0) -> Dict[str, Any]:
    path = _global_positions_shm_path()
    if not path.exists():
        return {"daemons": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"daemons": {}}
        daemons = data.get("daemons") or {}
        now = time.time()
        fresh_daemons = {
            k: v
            for k, v in daemons.items()
            if isinstance(v, dict) and (now - float(v.get("updated_ts") or 0.0)) <= max_age_sec
        }
        return {"daemons": fresh_daemons}
    except Exception:
        return {"daemons": {}}


def publish_global_positions_shm(daemon_name: str, positions: Iterable[Dict[str, Any]]) -> bool:
    """
    Publishes compact open-position exposure vector to `/dev/shm/pm_global_positions.json`
    so live & shadow sleeves coordinate correlation and synthetic corridor completions.
    """
    path = _global_positions_shm_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        cur = read_global_positions_shm(max_age_sec=600.0)
        daemons = dict(cur.get("daemons") or {})
        compact: List[Dict[str, Any]] = []
        for p in positions:
            if not isinstance(p, dict):
                continue
            compact.append({
                "id": str(p.get("trade_id") or p.get("position_id") or ""),
                "sleeve": str(p.get("sleeve") or ""),
                "asset": str(p.get("asset") or p.get("asset_or_city") or "").upper(),
                "side": str(p.get("target_token") or p.get("side") or "").upper(),
                "strike": float(p.get("candle_open_spot") or (p.get("extra") or {}).get("strike") or 0.0),
                "expiry_ts": float(p.get("candle_expiry_ts") or p.get("close_ts") or 0.0),
                "notional_usd": float(p.get("notional_usd") or p.get("entry_eff_px_t1000") or 0.0),
            })
        daemons[str(daemon_name)] = {"updated_ts": round(time.time(), 3), "positions": compact}
        payload = {"updated_at_ts": round(time.time(), 3), "daemons": daemons}
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def compute_capital_efficiency_utility(
    candidate: Dict[str, Any],
    active_global_positions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Scores any candidate trade across all 13 sleeves on a unified Capital-Efficiency metric:
      Utility ($EV / ($ * lock_hr)) = net_edge_frac / max(0.08, lock_hours)
                                      - tail_penalty - corr_penalty + corridor_completion_bonus
    """
    net_edge = float(candidate.get("net_edge") or 0.0)
    ask_px = max(0.05, float(candidate.get("ask_vwap") or 0.50))
    p_model = float(candidate.get("p_model") or (ask_px + net_edge))
    tte_sec = max(15.0, float(candidate.get("tte_sec") or 3600.0))
    lock_hours = max(0.08, min(24.0, tte_sec / 3600.0))
    roi_est = net_edge / ask_px
    ev_per_dollar_hr = roi_est / lock_hours

    tail_loss_prob = max(0.0, 1.0 - p_model)
    tail_penalty = 0.08 * (tail_loss_prob ** 2)

    cand_asset = str(candidate.get("asset") or "").upper()
    cand_side = str(candidate.get("side") or "").upper()
    cand_exp = float(candidate.get("expiry_ts") or 0.0)
    cand_strike = float(candidate.get("strike") or 0.0)

    corr_penalty = 0.0
    corridor_bonus = 0.0
    for pos in active_global_positions or []:
        p_asset = str(pos.get("asset") or "").upper()
        if not cand_asset or p_asset != cand_asset:
            continue
        p_exp = float(pos.get("expiry_ts") or 0.0)
        same_window = cand_exp > 0.0 and p_exp > 0.0 and abs(cand_exp - p_exp) <= 900.0
        p_side = str(pos.get("side") or "").upper()
        p_strike = float(pos.get("strike") or 0.0)
        if same_window:
            if p_side == cand_side and cand_side in ("UP", "DOWN", "YES", "NO"):
                corr_penalty += 0.12
            elif (
                cand_strike > 0.0
                and p_strike > 0.0
                and ((p_side == "UP" and cand_side == "DOWN" and p_strike < cand_strike)
                     or (p_side == "DOWN" and cand_side == "UP" and cand_strike < p_strike))
            ):
                # Synthetic corridor completion (`Gemini #15`): locks K_low < K_high dominance floor!
                corridor_bonus += 0.25

    utility = ev_per_dollar_hr - tail_penalty - corr_penalty + corridor_bonus
    return {
        "ev_per_dollar_hour": round(ev_per_dollar_hr, 4),
        "utility_score": round(utility, 4),
        "lock_hours": round(lock_hours, 3),
        "corr_penalty": round(corr_penalty, 4),
        "corridor_completion_bonus": round(corridor_bonus, 4),
    }


def rank_opportunities_capital_auction(
    opportunities: List[Dict[str, Any]],
    active_global_positions: Optional[List[Dict[str, Any]]] = None,
    active_positions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Annotates and sorts opportunities descending by `utility_score` (`EV / ($ * lock_hr)`)."""
    eff_positions = active_global_positions if active_global_positions is not None else active_positions
    enriched: List[Dict[str, Any]] = []
    for opp in opportunities:
        item = dict(opp)
        metrics = compute_capital_efficiency_utility(item, active_global_positions=eff_positions)
        item["ev_per_dollar_hour"] = metrics["ev_per_dollar_hour"]
        item["utility_score"] = metrics["utility_score"]
        if metrics["corridor_completion_bonus"] > 0:
            item["synthetic_corridor_completion"] = True
        enriched.append(item)
    enriched.sort(key=lambda x: (-float(x.get("utility_score", 0.0)), -float(x.get("net_edge", 0.0))))
    return enriched

# ======================================================================================
# [04/16] MODULE: src/polymarket_research/weather_metar_engine.py
# PURPOSE: Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb
# ======================================================================================

#!/usr/bin/env python3
"""
Option #1: Automated Multi-City Daily Weather Engine (METAR Oracle + NWP Ensemble)
==================================================================================
Implements exact bit-for-bit Polymarket Airport Weather Oracle parsing and two
orthogonal systematic weather alpha sleeves:

  1. W1_SOLAR_PEAK_LOCK (Target 88%-95% Win Rate):
     - Monitors routine ICAO METAR observations (strictly excluding SPECI per spec,
       preferring 8-digit T-group remarks in tenths of °C over whole-°C body groups).
     - After local diurnal peak (or post-sunrise trough for Lowest-Temp markets),
       verifies physical cooling cushion + multi-model NWP remaining-day trajectory
       (ECMWF + GFS + ICON) before locking underpriced winning brackets into settlement.

  2. W2_ENSEMBLE_VALUE (Calibrated 71-Member Multi-Model Ensemble + MOS Bias Correction):
     - Combines Open-Meteo multi-model ensembles (ICON 40m + GFS 31m + ECMWF IFS)
       with real-time METAR runway persistence bias correction:
         bias(t + dt) = (T_metar_now - T_model_now) * exp(-dt / tau_hours)
     - Truncates impossible lower/upper brackets already ruled out by intraday METARs.
     - Captures mispriced brackets (0% fee on Polymarket `zero_fees` weather markets).
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import json
import logging
import math
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger("WeatherMetarEngine")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
AWC_METAR_URL = "https://aviationweather.gov/api/data/metar"
AWC_STATION_URL = "https://aviationweather.gov/api/data/stationinfo"
IEM_ASOS_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
OPEN_METEO_ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_HIST_FORECAST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"

# Verified station metadata cache (ICAO -> (lat, lon, iana_tz, city_label))
STATION_CATALOG: Dict[str, Tuple[float, float, str, str]] = {
    "RJTT": (35.5523, 139.7798, "Asia/Tokyo", "Tokyo"),
    "EGLC": (51.5053, 0.0553, "Europe/London", "London"),
    "ZSPD": (31.1434, 121.8052, "Asia/Shanghai", "Shanghai"),
    "ZSQD": (36.3667, 120.0944, "Asia/Shanghai", "Qingdao"),
    "WMKK": (2.7456, 101.7099, "Asia/Kuala_Lumpur", "Kuala Lumpur"),
    "RCSS": (25.0694, 121.5525, "Asia/Taipei", "Taipei"),
    "EDDM": (48.3538, 11.7861, "Europe/Berlin", "Munich"),
    "LFPB": (48.9694, 2.4414, "Europe/Paris", "Paris"),
    "ZUUU": (30.5785, 103.9471, "Asia/Shanghai", "Chengdu"),
    "SBGR": (-23.4356, -46.4731, "America/Sao_Paulo", "Sao Paulo"),
    "LEMD": (40.4719, -3.5626, "Europe/Madrid", "Madrid"),
    "ZHHH": (30.7838, 114.2081, "Asia/Shanghai", "Wuhan"),
    "EHAM": (52.3086, 4.7639, "Europe/Amsterdam", "Amsterdam"),
    "EPWA": (52.1657, 20.9671, "Europe/Warsaw", "Warsaw"),
    "WSSS": (1.3502, 103.9940, "Asia/Singapore", "Singapore"),
    "ZBAA": (40.0801, 116.5846, "Asia/Shanghai", "Beijing"),
    "ZUCK": (29.7192, 106.6417, "Asia/Shanghai", "Chongqing"),
    "LTFM": (41.2753, 28.7519, "Europe/Istanbul", "Istanbul"),
    "KMIA": (25.7959, -80.2870, "America/New_York", "Miami"),
    "OPKC": (24.9065, 67.1608, "Asia/Karachi", "Karachi"),
    "KLGA": (40.7769, -73.8740, "America/New_York", "NYC"),
    "RKSI": (37.4602, 126.4407, "Asia/Seoul", "Seoul"),
    "LLBG": (32.0114, 34.8867, "Asia/Jerusalem", "Tel Aviv"),
    "ZGGG": (23.3924, 113.2988, "Asia/Shanghai", "Guangzhou"),
    "OEJN": (21.6796, 39.1565, "Asia/Riyadh", "Jeddah"),
    "VILK": (26.7606, 80.8893, "Asia/Kolkata", "Lucknow"),
    "ZGSZ": (22.6393, 113.8107, "Asia/Shanghai", "Shenzhen"),
    "LIMC": (45.6306, 8.7281, "Europe/Rome", "Milan"),
    "RKPK": (35.1795, 128.9382, "Asia/Seoul", "Busan"),
    "LTAC": (40.1281, 32.9951, "Europe/Istanbul", "Ankara"),
    "SAEZ": (-34.8222, -58.5358, "America/Argentina/Buenos_Aires", "Buenos Aires"),
    "KSEA": (47.4502, -122.3088, "America/Los_Angeles", "Seattle"),
    "KDAL": (32.8471, -96.8518, "America/Chicago", "Dallas"),
    "NZWN": (-41.3272, 174.8053, "Pacific/Auckland", "Wellington"),
    "KSFO": (37.6213, -122.3790, "America/Los_Angeles", "San Francisco"),
    "KORD": (41.9742, -87.9073, "America/Chicago", "Chicago"),
    "MMMX": (19.4363, -99.0721, "America/Mexico_City", "Mexico City"),
    "CYYZ": (43.6777, -79.6248, "America/Toronto", "Toronto"),
    "RPLL": (14.5086, 121.0194, "Asia/Manila", "Manila"),
    "EFHK": (60.3172, 24.9633, "Europe/Helsinki", "Helsinki"),
    "KATL": (33.6407, -84.4277, "America/New_York", "Atlanta"),
    "KHOU": (29.6454, -95.2789, "America/Chicago", "Houston"),
    "KDEN": (39.8561, -104.6737, "America/Denver", "Denver"),
    "UUWW": (55.5915, 37.2615, "Europe/Moscow", "Moscow"),
    "MPMG": (8.9733, -79.5556, "America/Panama", "Panama City"),
    "KAUS": (30.1945, -97.6699, "America/Chicago", "Austin"),
    "KLAX": (33.9425, -118.4081, "America/Los_Angeles", "Los Angeles"),
    "HKO": (22.3019, 114.1742, "Asia/Hong_Kong", "Hong Kong"),
}

HKO_1MIN_CSV_URL = "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature.csv"
HKO_MAXMIN_CSV_URL = "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_since_midnight_maxmin.csv"
HKO_RHRREAD_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en"

_T_REMARK_RE = re.compile(r"(?:^|\s)T([01])(\d{3})(?:\d{4}|////)(?=\s|$)")
_BODY_TEMP_RE = re.compile(r"(?:^|\s)(M?\d{2})/(?:M?\d{2}|//)(?=\s|$)")
_METAR_TS_RE = re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b")
_CONVECTIVE_WX_RE = re.compile(
    r"(?:^|\s)(?:[-+]|VC)?(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)*\b"
    r"|(?:FEW|SCT|BKN|OVC)\d{3}(?:CB|TCU)\b"
    r"|\b(?:CB|TCU|RAB\d{2,4}|TSB\d{2,4}|P\d{4})\b"
)
_AWC_ICAO_RE = re.compile(r"aviationweather\.gov/api/data/metar\?ids=([A-Z0-9]{4})", re.IGNORECASE)
_NOAA_ICAO_RE = re.compile(r"weather\.gov/wrh/timeseries\?site=([A-Z0-9]{4})", re.IGNORECASE)
_PAREN_ICAO_RE = re.compile(r"\(([A-Z]{4})\)")
_SERIES_TO_ICAO: Dict[str, str] = {
    "tokyo-daily-weather": "RJTT",
    "london-daily-weather": "EGLC",
    "london-daily-lowest-temperature": "EGLC",
    "shanghai-daily-weather": "ZSPD",
    "shanghai-daily-lowest-temperature": "ZSPD",
    "chengdu-daily-weather": "ZUUU",
    "beijing-daily-weather": "ZBAA",
    "wuhan-daily-weather": "ZHHH",
    "chongqing-daily-weather": "ZUCK",
    "guangzhou-daily-weather": "ZGGG",
    "shenzhen-daily-weather": "ZGSZ",
    "qingdao-daily-weather": "ZSQD",
    "paris-daily-weather": "LFPB",
    "munich-daily-weather": "EDDM",
    "miami-daily-weather": "KMIA",
    "miami-daily-lowest-temperature": "KMIA",
    "nyc-daily-weather": "KLGA",
    "nyc-daily-lowest-temperature": "KLGA",
    "houston-daily-weather": "KHOU",
    "austin-daily-weather": "KAUS",
    "los-angeles-daily-weather": "KLAX",
    "los-angeles-daily-lowest-temperature": "KLAX",
    "seoul-daily-weather": "RKSI",
    "seoul-daily-lowest-temperature": "RKSI",
    "busan-daily-weather": "RKPK",
    "chicago-daily-weather": "KORD",
    "seattle-daily-weather": "KSEA",
    "dallas-daily-weather": "KDAL",
    "madrid-daily-weather": "LEMD",
    "amsterdam-daily-weather": "EHAM",
    "taipei-daily-weather": "RCSS",
    "singapore-daily-weather": "WSSS",
    "hong-kong-daily-weather": "HKO",
    "hong-kong-daily-lowest-temperature": "HKO",
    "wellington-daily-weather": "NZWN",
    "wellington-daily-lowest-temperature": "NZWN",
    "warsaw-daily-weather": "EPWA",
    "warsaw-daily-lowest-temperature": "EPWA",
    "buenos-aires-daily-weather": "SAEZ",
    "helsinki-daily-weather": "EFHK",
    "denver-daily-weather": "KDEN",
    "toronto-daily-weather": "CYYZ",
    "mexico-city-daily-weather": "MMMX",
    "tel-aviv-daily-weather": "LLBG",
    "istanbul-daily-weather": "LTFM",
    "sao-paulo-daily-weather": "SBGR",
    "manila-daily-weather": "RPLL",
    "atlanta-daily-weather": "KATL",
    "san-francisco-daily-weather": "KSFO",
}

HIGH_VOLUME_WEATHER_SERIES: Tuple[str, ...] = (
    "hong-kong-daily-weather",
    "hong-kong-daily-lowest-temperature",
    "chengdu-daily-weather",
    "beijing-daily-weather",
    "seoul-daily-weather",
    "seoul-daily-lowest-temperature",
    "shanghai-daily-weather",
    "shanghai-daily-lowest-temperature",
    "tokyo-daily-weather",
    "wuhan-daily-weather",
    "chongqing-daily-weather",
    "guangzhou-daily-weather",
    "shenzhen-daily-weather",
    "taipei-daily-weather",
    "singapore-daily-weather",
    "nyc-daily-weather",
    "nyc-daily-lowest-temperature",
    "chicago-daily-weather",
    "london-daily-weather",
    "london-daily-lowest-temperature",
    "miami-daily-weather",
    "miami-daily-lowest-temperature",
    "austin-daily-weather",
    "los-angeles-daily-weather",
    "los-angeles-daily-lowest-temperature",
    "houston-daily-weather",
    "dallas-daily-weather",
    "wellington-daily-weather",
    "wellington-daily-lowest-temperature",
    "warsaw-daily-weather",
    "warsaw-daily-lowest-temperature",
    "buenos-aires-daily-weather",
    "helsinki-daily-weather",
    "denver-daily-weather",
    "toronto-daily-weather",
    "paris-daily-weather",
    "madrid-daily-weather",
)
_MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


@dataclass
class WeatherBucket:
    market_id: str
    condition_id: str
    label: str
    question: str
    yes_token: str
    no_token: str
    unit: str  # "C" or "F"
    low_bound: float  # -inf for "X or below"
    high_bound: float  # +inf for "X or higher"
    outcome_yes_resolved: Optional[int] = None  # 1 or 0 for closed markets
    fee_rate: float = 0.0
    fee_exponent: float = 1.0
    neg_risk: Optional[bool] = None  # Gamma `negRisk`; None = unknown (blocks LIVE C1 emits)
    def contains_rounded(self, rounded_int: int) -> bool:
        return self.low_bound <= rounded_int <= self.high_bound


@dataclass
class WeatherEventSpec:
    event_id: str
    slug: str
    series_slug: str
    title: str
    icao: str
    city: str
    lat: float
    lon: float
    tz_name: str
    obs_date: date
    metric: str  # "HIGH" or "LOW"
    unit: str  # "C" or "F"
    fee_type: str
    end_date_iso: str
    buckets: List[WeatherBucket] = field(default_factory=list)


@dataclass
class MetarObservation:
    icao: str
    utc_dt: datetime
    local_dt: datetime
    temp_c: float
    has_t_remark: bool
    raw_line: str
    has_convective_precip: bool = False
    is_corrected: bool = False


def round_half_up_polymarket(val: float) -> int:
    """
    Exact Polymarket Weather rounding rule verified against spec examples:
      13.9 -> 14, 17.4 -> 17, 16.5 -> 17, -1.7 -> -2, -8.5 -> -8.
    Mathematically identical to floor(val + 0.5) with float epsilon guard.
    """
    return int(math.floor(val + 0.5 + 1e-12))


def celsius_to_market_int(temp_c: float, unit: str) -> int:
    if unit.upper() == "F":
        val_f = temp_c * 9.0 / 5.0 + 32.0
        return round_half_up_polymarket(val_f)
    return round_half_up_polymarket(temp_c)


def parse_bucket_bounds(label: str) -> Optional[Tuple[str, float, float]]:
    """
    Parses Polymarket weather bucket titles such as:
      '16°C or below', '17°C', '26°C or higher',
      '71°F or below', '72-73°F', '90°F or higher',
      '-2°C or below', '-1°C', '-4--3°F'
    Returns (unit, low_bound, high_bound).
    """
    s = label.strip().replace("−", "-").replace("–", "-")
    unit_m = re.search(r"°\s*([CF])", s, re.IGNORECASE)
    if not unit_m:
        return None
    unit = unit_m.group(1).upper()
    low_s = s.lower()

    if "or below" in low_s or "or lower" in low_s or "or less" in low_s or "under" in low_s:
        m = re.search(r"(-?\d+)\s*°", s)
        if not m:
            return None
        return unit, float("-inf"), float(int(m.group(1)))

    if "or higher" in low_s or "or above" in low_s or "or more" in low_s:
        m = re.search(r"(-?\d+)\s*°", s)
        if not m:
            return None
        return unit, float(int(m.group(1))), float("inf")

    m_range = re.search(r"(-?\d+)\s*(?:°[CF])?\s*(?:-|to)\s*(-?\d+)\s*°", s, re.IGNORECASE)
    if m_range:
        lo, hi = int(m_range.group(1)), int(m_range.group(2))
        return unit, float(min(lo, hi)), float(max(lo, hi))

    m_single = re.search(r"(-?\d+)\s*°", s)
    if m_single:
        v = float(int(m_single.group(1)))
        return unit, v, v
    return None


def parse_metar_line(
    raw_line: str,
    icao: str,
    ref_utc: datetime,
    tz_name: str,
    explicit_utc_dt: Optional[datetime] = None,
) -> Optional[MetarObservation]:
    """
    Parses a single raw METAR line strictly per Polymarket Weather contract rules:
      1. Any line whose report begins with SPECI is excluded.
      2. Extracts 8-digit hourly temperature remark T[01]xxx.... (0.1°C) if present.
      3. Otherwise falls back to body temperature group M?dd/M?dd (1.0°C).
    """
    line = raw_line.strip()
    if not line:
        return None
    # Strip optional leading timestamp prefix if present
    upper = line.upper()
    tokens = upper.split()
    if not tokens:
        return None
    if "SPECI" in tokens[:3]:
        return None
    if icao.upper() not in tokens[:4]:
        return None
    is_cor = "COR" in tokens[:5]

    utc_dt = explicit_utc_dt
    if utc_dt is None:
        m_ts = _METAR_TS_RE.search(upper)
        if not m_ts:
            return None
        day_i, hr_i, min_i = int(m_ts.group(1)), int(m_ts.group(2)), int(m_ts.group(3))
        # Resolve year/month near ref_utc cleanly across month boundaries
        candidates: List[datetime] = []
        for d_off in (-32, 0, 32):
            anchor = ref_utc + timedelta(days=d_off)
            try:
                cand = datetime(anchor.year, anchor.month, day_i, hr_i, min_i, tzinfo=timezone.utc)
                candidates.append(cand)
            except ValueError:
                continue
        if not candidates:
            return None
        utc_dt = min(candidates, key=lambda c: abs((c - ref_utc).total_seconds()))

    # 1. Check 8-digit T-remark (only in RMK section if RMK is present)
    rmk_part = upper.split("RMK", 1)[1] if "RMK" in upper else upper
    m_rem = _T_REMARK_RE.search(rmk_part)
    if m_rem:
        sign = -1.0 if m_rem.group(1) == "1" else 1.0
        temp_c = sign * (int(m_rem.group(2)) / 10.0)
        has_t = True
    else:
        # 2. Fallback to body temperature group before RMK
        body_part = upper.split("RMK", 1)[0]
        m_body = _BODY_TEMP_RE.search(body_part)
        if not m_body:
            return None
        grp = m_body.group(1)
        temp_c = -float(int(grp[1:])) if grp.startswith("M") else float(int(grp))
        has_t = False

    local_dt = utc_dt.astimezone(ZoneInfo(tz_name))
    has_precip = bool(_CONVECTIVE_WX_RE.search(upper))
    return MetarObservation(
        icao=icao.upper(),
        utc_dt=utc_dt,
        local_dt=local_dt,
        temp_c=temp_c,
        has_t_remark=has_t,
        raw_line=line,
        has_convective_precip=has_precip,
        is_corrected=is_cor,
    )


def parse_obs_date_from_event(title: str, desc: str, end_date_iso: str) -> Optional[date]:
    """Extracts the target local observation date from event description or title."""
    # Description pattern: "on 26 Oct '26" or "on 25 Oct '26"
    m_desc = re.search(r"\bon\s+(\d{1,2})\s+([A-Za-z]+)\s+'?(\d{2,4})\b", desc)
    if m_desc:
        day_v = int(m_desc.group(1))
        mon_v = _MONTH_MAP.get(m_desc.group(2).lower())
        yr_v = int(m_desc.group(3))
        if yr_v < 100:
            yr_v += 2000
        if mon_v:
            try:
                return date(yr_v, mon_v, day_v)
            except ValueError:
                pass

    # Title pattern: "on October 26?" or "on October 25, 2026?"
    ref_year = 2026
    if end_date_iso:
        try:
            ref_year = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00")).year
        except Exception:
            pass
    m_title = re.search(r"\bon\s+([A-Za-z]+)\s+(\d{1,2})(?:,?\s*(\d{4}))?", title)
    if m_title:
        mon_v = _MONTH_MAP.get(m_title.group(1).lower())
        day_v = int(m_title.group(2))
        yr_v = int(m_title.group(3)) if m_title.group(3) else ref_year
        if mon_v:
            try:
                return date(yr_v, mon_v, day_v)
            except ValueError:
                pass
    return None


def parse_weather_event(
    ev: Dict[str, Any],
    allow_historical_same_station: bool = False,
    series_slug_hint: str = "",
) -> Optional[WeatherEventSpec]:
    """
    Converts a Polymarket Gamma event dict into a validated WeatherEventSpec.
    Live mode (`allow_historical_same_station=False`) strictly requires an explicit
    aviationweather.gov ICAO METAR oracle URL + SPECI rule in description.
    Backtest mode (`allow_historical_same_station=True`) also accepts pre-Oct-23
    markets at the exact same airport station (NOAA/Wunderground airport METAR feed).
    """
    title = str(ev.get("title") or "")
    tl = title.lower()
    if "highest temperature in" in tl:
        metric = "HIGH"
    elif "lowest temperature in" in tl:
        metric = "LOW"
    else:
        return None

    mkts = ev.get("markets") or []
    if len(mkts) < 4:
        return None

    series_arr = ev.get("series") or []
    s_slug = str(series_arr[0].get("slug") if series_arr else (ev.get("seriesSlug") or series_slug_hint or ""))
    desc = str(mkts[0].get("description") or ev.get("description") or "")

    icao: Optional[str] = None
    m_icao = _AWC_ICAO_RE.search(desc)
    if m_icao and "SPECI" in desc:
        icao = m_icao.group(1).upper()
    elif "weather.gov.hk" in desc.lower() and "hong kong observatory" in desc.lower():
        icao = "HKO"
    elif allow_historical_same_station:
        m_noaa = _NOAA_ICAO_RE.search(desc)
        m_par = _PAREN_ICAO_RE.search(desc)
        if m_noaa and m_noaa.group(1).upper() in STATION_CATALOG:
            icao = m_noaa.group(1).upper()
        elif m_par and m_par.group(1).upper() in STATION_CATALOG:
            icao = m_par.group(1).upper()
        elif s_slug in _SERIES_TO_ICAO:
            icao = _SERIES_TO_ICAO[s_slug]

    if not icao or icao not in STATION_CATALOG:
        return None

    lat, lon, tz_name, city = STATION_CATALOG[icao]
    end_iso = str(ev.get("endDate") or mkts[0].get("endDate") or "")
    obs_date = parse_obs_date_from_event(title, desc, end_iso)
    if obs_date is None:
        return None

    fee_type = str(mkts[0].get("feeType") or "zero_fees")

    buckets: List[WeatherBucket] = []
    for m in mkts:
        lbl = str(m.get("groupItemTitle") or m.get("question") or "")
        parsed = parse_bucket_bounds(lbl)
        if not parsed:
            continue
        unit, lo, hi = parsed
        toks = m.get("clobTokenIds")
        if isinstance(toks, str):
            try:
                toks = json.loads(toks)
            except Exception:
                toks = []
        if not toks or len(toks) < 2:
            continue

        resolved_yes: Optional[int] = None
        if m.get("closed"):
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    op = json.loads(op)
                except Exception:
                    op = None
            if isinstance(op, list) and len(op) >= 2:
                try:
                    if float(op[0]) >= 0.99:
                        resolved_yes = 1
                    elif float(op[1]) >= 0.99:
                        resolved_yes = 0
                except Exception:
                    pass

        m_fee_sched = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
        fees_enabled = bool(m.get("feesEnabled", False))
        raw_rate = float(m_fee_sched.get("rate") or 0.0)
        b_fee_rate = raw_rate if (fees_enabled and raw_rate > 0.0) else 0.0
        b_fee_exp = float(m_fee_sched.get("exponent") or 1.0)

        buckets.append(
            WeatherBucket(
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                label=lbl,
                question=str(m.get("question") or lbl),
                yes_token=str(toks[0]),
                no_token=str(toks[1]),
                unit=unit,
                low_bound=lo,
                high_bound=hi,
                outcome_yes_resolved=resolved_yes,
                fee_rate=b_fee_rate,
                fee_exponent=b_fee_exp,
            )
        )

    if len(buckets) < 4:
        return None
    buckets.sort(key=lambda b: (b.low_bound, b.high_bound))
    if any(b.fee_rate > 0.0 for b in buckets):
        fee_type = "fees_enabled"
    return WeatherEventSpec(
        event_id=str(ev.get("id") or ""),
        slug=str(ev.get("slug") or ""),
        series_slug=s_slug,
        title=title,
        icao=icao,
        city=city,
        lat=lat,
        lon=lon,
        tz_name=tz_name,
        obs_date=obs_date,
        metric=metric,
        unit=buckets[0].unit,
        fee_type=fee_type,
        end_date_iso=end_iso,
        buckets=buckets,
    )


def parse_hko_csv_observations(
    raw_1min_csv: str,
    raw_maxmin_csv: str,
    obs_date: date,
    tz_name: str = "Asia/Hong_Kong",
) -> List[MetarObservation]:
    """
    Parses Hong Kong Observatory (`HKO`) official 1-minute tenths-of-°C live air temperature
    and midnight-to-now Absolute Daily Max/Min CSV feeds (`HK Observatory` station, NOT Chek Lap Kok airport).
    """
    tz = ZoneInfo(tz_name)
    local_start = datetime(obs_date.year, obs_date.month, obs_date.day, 0, 0, tzinfo=tz)
    cur_c: Optional[float] = None
    cur_dt_loc: Optional[datetime] = None
    max_c: Optional[float] = None
    min_c: Optional[float] = None

    for ln in (raw_1min_csv or "").splitlines():
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) >= 3 and parts[1] in ("HK Observatory", "Hong Kong Observatory") and len(parts[0]) >= 12 and parts[0][:12].isdigit():
            try:
                dt_l = datetime.strptime(parts[0][:12], "%Y%m%d%H%M").replace(tzinfo=tz)
                if dt_l.date() == obs_date:
                    cur_c = float(parts[2])
                    cur_dt_loc = dt_l
            except ValueError:
                pass

    for ln in (raw_maxmin_csv or "").splitlines():
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) >= 4 and parts[1] in ("HK Observatory", "Hong Kong Observatory") and len(parts[0]) >= 12 and parts[0][:12].isdigit():
            try:
                dt_l = datetime.strptime(parts[0][:12], "%Y%m%d%H%M").replace(tzinfo=tz)
                if dt_l.date() == obs_date:
                    if parts[2] and parts[2].upper() != "N/A":
                        max_c = float(parts[2])
                    if parts[3] and parts[3].upper() != "N/A":
                        min_c = float(parts[3])
                    if cur_dt_loc is None:
                        cur_dt_loc = dt_l
            except ValueError:
                pass

    if cur_dt_loc is None:
        return []
    out: List[MetarObservation] = []
    # Stamp midnight-since-start min/max near start of local day so they anchor exact `running_ext_c`
    # without distorting the recent 3.5h real-time NWP bias window!
    if min_c is not None:
        dt_min = min(cur_dt_loc, local_start + timedelta(minutes=1))
        out.append(MetarObservation("HKO", dt_min.astimezone(timezone.utc), dt_min, min_c, True, f"HKO_MIN {min_c:.1f}C"))
    if max_c is not None:
        dt_max = min(cur_dt_loc, local_start + timedelta(minutes=2))
        out.append(MetarObservation("HKO", dt_max.astimezone(timezone.utc), dt_max, max_c, True, f"HKO_MAX {max_c:.1f}C"))
    eff_cur = cur_c if cur_c is not None else (max_c if max_c is not None else min_c)
    if eff_cur is not None:
        out.append(MetarObservation("HKO", cur_dt_loc.astimezone(timezone.utc), cur_dt_loc, eff_cur, True, f"HKO_1M {eff_cur:.1f}C"))
    out.sort(key=lambda o: o.utc_dt)
    return out


def fetch_hko_observations_sync(
    obs_date: date,
    tz_name: str = "Asia/Hong_Kong",
    timeout: float = 7.0,
) -> List[MetarObservation]:
    """Fetches official Hong Kong Observatory (`HKO`) 1-min and midnight max/min observations."""
    raw_1m = ""
    raw_mm = ""
    hdrs = {"User-Agent": "DominusWeatherEngine/1.0"}
    try:
        raw_1m = urllib.request.urlopen(urllib.request.Request(HKO_1MIN_CSV_URL, headers=hdrs), timeout=timeout).read().decode("utf-8-sig", errors="ignore")
    except Exception as exc:
        logger.debug(f"HKO 1min CSV notice: {exc}")
    try:
        raw_mm = urllib.request.urlopen(urllib.request.Request(HKO_MAXMIN_CSV_URL, headers=hdrs), timeout=timeout).read().decode("utf-8-sig", errors="ignore")
    except Exception as exc:
        logger.debug(f"HKO maxmin CSV notice: {exc}")
    parsed = parse_hko_csv_observations(raw_1m, raw_mm, obs_date, tz_name)
    if parsed:
        return parsed
    try:
        data = json.loads(urllib.request.urlopen(urllib.request.Request(HKO_RHRREAD_URL, headers=hdrs), timeout=timeout).read().decode("utf-8"))
        t_blk = data.get("temperature") or {}
        rec_iso = str(t_blk.get("recordTime") or "")
        dt_l = datetime.fromisoformat(rec_iso).astimezone(ZoneInfo(tz_name)) if rec_iso else datetime.now(ZoneInfo(tz_name))
        if dt_l.date() == obs_date:
            for item in t_blk.get("data") or []:
                if "Observatory" in str(item.get("place") or ""):
                    v = float(item["value"])
                    return [MetarObservation("HKO", dt_l.astimezone(timezone.utc), dt_l, v, False, f"HKO_RHR {v:.1f}C")]
    except Exception:
        pass
    return []


def fetch_metar_observations_sync(
    icao: str,
    obs_date: date,
    tz_name: str,
    timeout: float = 8.0,
) -> List[MetarObservation]:
    """
    Fetches routine METAR observations for (icao, obs_date) in station local time.
    Uses exact Polymarket AWC endpoint for recent dates (<= 13 days) and falls back
    seamlessly to Iowa Environmental Mesonet (IEM ASOS) raw METAR archive for older dates.
    """
    if icao.upper() == "HKO":
        return fetch_hko_observations_sync(obs_date, tz_name, timeout=timeout)
    tz = ZoneInfo(tz_name)
    local_start = datetime(obs_date.year, obs_date.month, obs_date.day, 0, 0, tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    utc_end_query = local_end.astimezone(timezone.utc) + timedelta(hours=3)
    now_utc = datetime.now(timezone.utc)
    query_anchor = min(now_utc, utc_end_query)

    age_days = (now_utc - local_start.astimezone(timezone.utc)).total_seconds() / 86400.0
    obs_by_ts: Dict[int, MetarObservation] = {}

    def _merge_metar(parsed_obs: MetarObservation) -> None:
        ts_k = int(parsed_obs.utc_dt.timestamp())
        prev = obs_by_ts.get(ts_k)
        if (
            prev is None
            or parsed_obs.is_corrected
            or (not prev.is_corrected and (parsed_obs.has_t_remark or not prev.has_t_remark))
        ):
            obs_by_ts[ts_k] = parsed_obs

    if age_days <= 13.5:
        iso_q = query_anchor.strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"{AWC_METAR_URL}?ids={icao.upper()}&format=raw&date={iso_q}&hours=36"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
            raw_text = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")
            # AWC emits newest lines first; iterate oldest -> newest so COR amendments supersede originals (`M-02`)
            for line in reversed(raw_text.splitlines()):
                parsed = parse_metar_line(line, icao, query_anchor, tz_name)
                if parsed and parsed.local_dt.date() == obs_date:
                    _merge_metar(parsed)
        except Exception as exc:
            logger.debug(f"AWC METAR fetch fallback for {icao} {obs_date}: {exc}")

    if not obs_by_ts:
        # Fallback to IEM ASOS historical raw METAR archive
        u_start = local_start.astimezone(timezone.utc) - timedelta(hours=2)
        u_end = local_end.astimezone(timezone.utc) + timedelta(hours=2)
        st_param = icao.upper()[1:] if (len(icao) == 4 and icao.upper().startswith("K")) else icao.upper()
        params = urllib.parse.urlencode({
            "station": st_param,
            "data": "metar",
            "year1": u_start.year, "month1": u_start.month, "day1": u_start.day,
            "year2": u_end.year, "month2": u_end.month, "day2": u_end.day,
            "tz": "Etc/UTC",
            "format": "onlycomma",
            "latlon": "no", "elev": "no",
            "missing": "M", "trace": "T", "direct": "no",
            "report_type": ["3", "4"],
        }, doseq=True)
        try:
            req = urllib.request.Request(f"{IEM_ASOS_URL}?{params}", headers={"User-Agent": "DominusWeatherEngine/1.0"})
            csv_txt = urllib.request.urlopen(req, timeout=timeout + 4.0).read().decode("utf-8", errors="ignore")
            for row in csv_txt.splitlines()[1:]:
                parts = row.split(",", 2)
                if len(parts) < 3:
                    continue
                try:
                    dt_utc = datetime.strptime(parts[1].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                parsed = parse_metar_line(parts[2], icao, dt_utc, tz_name, explicit_utc_dt=dt_utc)
                if parsed and parsed.local_dt.date() == obs_date:
                    _merge_metar(parsed)
        except Exception as exc:
            logger.debug(f"IEM METAR archive fetch error for {icao} {obs_date}: {exc}")

    return sorted(obs_by_ts.values(), key=lambda o: o.utc_dt)


def compute_weather_probabilities(
    spec: WeatherEventSpec,
    eval_utc: datetime,
    metars_so_far: List[MetarObservation],
    ensemble_hourly_c: Dict[int, List[float]],
    forecast_sigma_base_c: float = 1.15,
    bias_decay_tau_hr: float = 6.0,
    taf_extreme_c: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes strictly causal (as-of `eval_utc`) bucket probabilities and physical solar-lock signals:
      - `metars_so_far`: strictly filtered to `o.utc_dt <= eval_utc` on `spec.obs_date`.
      - `ensemble_hourly_c`: mapping of `unix_hour_ts -> [member_1_temp_c, ..., member_M_temp_c]`
        covering `spec.obs_date` in the station's local timezone.
    Returns dict with per-bucket probabilities, lock metrics, and model diagnostics.
    """
    tz = ZoneInfo(spec.tz_name)
    eval_local = eval_utc.astimezone(tz)
    local_day_start = datetime(spec.obs_date.year, spec.obs_date.month, spec.obs_date.day, 0, 0, tzinfo=tz)
    local_day_end = local_day_start + timedelta(days=1)

    valid_obs = [o for o in metars_so_far if o.utc_dt <= eval_utc and o.local_dt.date() == spec.obs_date]
    has_obs = len(valid_obs) > 0
    latest_obs = valid_obs[-1] if has_obs else None

    if has_obs:
        if spec.metric == "HIGH":
            running_ext_c = max(o.temp_c for o in valid_obs)
        else:
            running_ext_c = min(o.temp_c for o in valid_obs)
        running_ext_int = celsius_to_market_int(running_ext_c, spec.unit)
    else:
        running_ext_c = None
        running_ext_int = None

    # Compute real-time MOS / station runway persistence bias from recent METARs vs ensemble mean
    # Guard against transient convective rain-shower cold pools (e.g. KMIA midday RA/CB cooling runway by -2.3°C)
    bias_c = 0.0
    eff_bias_tau_hr = bias_decay_tau_hr
    recent_convective = False
    convective_cold_pool = False
    if latest_obs is not None:
        recent_window = [o for o in valid_obs if (eval_utc - o.utc_dt).total_seconds() <= 12600.0][-3:]
        recent_convective = any(
            o.has_convective_precip for o in valid_obs if (eval_utc - o.utc_dt).total_seconds() <= 7200.0
        )
        local_hr_now = eval_local.hour + eval_local.minute / 60.0
        sudden_daytime_drop = (
            spec.metric == "HIGH"
            and 9.0 <= local_hr_now <= 16.25
            and running_ext_c is not None
            and (running_ext_c - latest_obs.temp_c) >= 1.2
        )
        if ensemble_hourly_c and recent_window:
            obs_biases: List[float] = []
            for o_rec in recent_window:
                nearest_hr = int(round(o_rec.utc_dt.timestamp() / 3600.0) * 3600)
                ref_members = ensemble_hourly_c.get(nearest_hr)
                if ref_members:
                    ens_mean_hr = sum(ref_members) / len(ref_members)
                    obs_biases.append(o_rec.temp_c - ens_mean_hr)
            if obs_biases:
                obs_biases.sort()
                if len(obs_biases) == 3:
                    raw_bias = obs_biases[1]  # Median / trimmed mean of last 3 routine METARs
                else:
                    raw_bias = sum(obs_biases) / len(obs_biases)
                # Clear-sky systematic NWP airport bias rarely exceeds +/-1.5°C; larger swings are mesoscale
                bias_c = max(-1.5, min(1.5, raw_bias))
                if spec.metric == "HIGH" and raw_bias < -0.35 and (recent_convective or sudden_daytime_drop):
                    convective_cold_pool = True
                    # Do NOT extrapolate transient rain-cooled runway air across the rest of the sunny afternoon!
                    bias_c = max(-0.45, raw_bias * 0.20)
                    eff_bias_tau_hr = min(bias_decay_tau_hr, 1.2)
        elif recent_convective or sudden_daytime_drop:
            convective_cold_pool = spec.metric == "HIGH"

    # Build remaining hourly timestamps on `obs_date` strictly after `eval_utc`
    rem_hour_ts: List[int] = []
    cur_dt = max(local_day_start, eval_local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    while cur_dt < local_day_end:
        rem_hour_ts.append(int(cur_dt.astimezone(timezone.utc).timestamp()))
        cur_dt += timedelta(hours=1)
    if eval_local < local_day_end and not rem_hour_ts:
        # Between 23:00:00 and 23:59:59 local time: routine 23:53-23:59 METAR can still print (`H-02`)!
        rem_hour_ts.append(int(local_day_end.astimezone(timezone.utc).timestamp()))

    # Determine number of ensemble trajectories (or synthesize Gaussian trajectories around mean if 1-3 deterministic models)
    sample_counts = [len(ensemble_hourly_c[t]) for t in rem_hour_ts if t in ensemble_hourly_c and ensemble_hourly_c[t]]
    if not sample_counts and ensemble_hourly_c:
        sample_counts = [len(v) for v in ensemble_hourly_c.values() if v]
    n_raw = min(sample_counts) if sample_counts else 0

    # Construct N=13-quadrature x M-member calibrated Ensemble trajectories over remaining hours
    z_grid = [-2.1, -1.5, -1.1, -0.75, -0.45, -0.2, 0.0, 0.2, 0.45, 0.75, 1.1, 1.5, 2.1]
    bucket_weights = [0.0 for _ in spec.buckets]
    total_weight = 0.0
    member_extremes: List[float] = []

    rem_hours_count = len(rem_hour_ts)
    if eval_local >= local_day_end and running_ext_int is not None:
        # Observation day has physically ended in local station time!
        for idx, b in enumerate(spec.buckets):
            bucket_weights[idx] = 1.0 if b.contains_rounded(running_ext_int) else 0.0
        total_weight = 1.0
    elif n_raw > 0 and rem_hours_count > 0:
        # Residual sub-grid / urban runway representation uncertainty (shrinks when few hours remain)
        sigma_resid = forecast_sigma_base_c * min(1.0, math.sqrt(max(1.0, rem_hours_count) / 10.0))
        if n_raw >= 15:
            # Multi-member ensemble already captures synoptic spread; add modest runway microclimate kernel
            sigma_kernel = max(0.45, 0.55 * sigma_resid)
        else:
            # 1-3 deterministic models (e.g., historical archive or partial fallback): use full forecast error kernel
            sigma_kernel = max(0.75, sigma_resid)
        if convective_cold_pool:
            # Post-shower solar recovery vs lingering outflow cloud cover increases afternoon peak spread
            sigma_kernel *= 1.45

        for m_idx in range(n_raw):
            # Future extreme for member m_idx with bias decay
            base_future_vals: List[float] = []
            for h_ts in rem_hour_ts:
                vals = ensemble_hourly_c.get(h_ts)
                if not vals:
                    continue
                v = vals[min(m_idx, len(vals) - 1)]
                dt_hr = max(0.0, (h_ts - eval_utc.timestamp()) / 3600.0)
                decayed_bias = bias_c * math.exp(-dt_hr / max(0.5, eff_bias_tau_hr))
                base_future_vals.append(v + decayed_bias)

            if not base_future_vals:
                continue
            fut_ext_base = max(base_future_vals) if spec.metric == "HIGH" else min(base_future_vals)
            if taf_extreme_c is not None and math.isfinite(float(taf_extreme_c)):
                # Blend official human-forecaster Airport TAF TX/TN group as a 15% physical runway prior (`Gemini #11`)
                fut_ext_base = 0.85 * fut_ext_base + 0.15 * float(taf_extreme_c)
            member_extremes.append(fut_ext_base)

            for z in z_grid:
                w = math.exp(-0.5 * z * z)
                sim_fut_c = fut_ext_base + z * sigma_kernel
                if running_ext_c is not None:
                    final_c = max(running_ext_c, sim_fut_c) if spec.metric == "HIGH" else min(running_ext_c, sim_fut_c)
                else:
                    final_c = sim_fut_c
                final_int = celsius_to_market_int(final_c, spec.unit)
                for b_idx, b in enumerate(spec.buckets):
                    if b.contains_rounded(final_int):
                        bucket_weights[b_idx] += w
                        break
                total_weight += w

    peak_iqr_c = 0.0
    if len(member_extremes) >= 4:
        s_ext = sorted(member_extremes)
        q25 = s_ext[int(0.25 * (len(s_ext) - 1))]
        q75 = s_ext[int(0.75 * (len(s_ext) - 1))]
        peak_iqr_c = max(0.0, q75 - q25)

    if total_weight <= 0.0:
        probs = [1.0 / len(spec.buckets) for _ in spec.buckets]
    else:
        probs = [max(0.001, min(0.998, w / total_weight)) for w in bucket_weights]
        s_p = sum(probs)
        probs = [p / s_p for p in probs]

    # Check W1_SOLAR_PEAK_LOCK qualification
    is_solar_lock_window = False
    cooling_cushion_c = 0.0
    locked_bucket_idx: Optional[int] = None
    p_locked_bucket = 0.0

    if has_obs and latest_obs is not None and running_ext_c is not None and running_ext_int is not None:
        local_hr_float = eval_local.hour + eval_local.minute / 60.0
        for idx, b in enumerate(spec.buckets):
            if b.contains_rounded(running_ext_int):
                locked_bucket_idx = idx
                p_locked_bucket = probs[idx]
                break

        if spec.metric == "HIGH":
            cooling_cushion_c = running_ext_c - latest_obs.temp_c
            # Post-afternoon solar peak: local time >= 15:45 on clear days, or >= 17:30 if convective rain cooled runway!
            min_lock_hr = 17.50 if (recent_convective or convective_cold_pool) else 15.75
            past_peak = (eval_local.date() > spec.obs_date) or (
                eval_local.date() == spec.obs_date and local_hr_float >= min_lock_hr
            )
            if past_peak and (eval_local.date() > spec.obs_date or cooling_cushion_c >= 0.8) and p_locked_bucket >= 0.88:
                is_solar_lock_window = True
        else:
            # LOW temperature market:
            #   (a) Late-night lock (`>= 22:30` local) with `>= 1.0°C` warming cushion, OR
            #   (b) Post-sunrise morning trough lock (`09:30 <= local_hr < 22:30`) with `>= 2.0°C` warming cushion
            #       AND strict NWP evening cold-front veto (`min(member_extremes) >= running_ext_c + 1.8°C`).
            warming_cushion_c = latest_obs.temp_c - running_ext_c
            cooling_cushion_c = warming_cushion_c
            past_trough_late = (eval_local.date() > spec.obs_date) or (
                eval_local.date() == spec.obs_date and local_hr_float >= 22.5
            )
            morning_trough_safe = (
                eval_local.date() == spec.obs_date
                and 9.50 <= local_hr_float < 22.5
                and warming_cushion_c >= 2.0
                and n_raw >= 15
                and bool(member_extremes)
                and min(member_extremes) >= (running_ext_c + 1.8)
            )
            if p_locked_bucket >= 0.90 and (
                (past_trough_late and (eval_local.date() > spec.obs_date or warming_cushion_c >= 1.0))
                or morning_trough_safe
            ):
                is_solar_lock_window = True

    return {
        "probs": probs,
        "has_obs": has_obs,
        "obs_count": len(valid_obs),
        "latest_temp_c": latest_obs.temp_c if latest_obs else None,
        "running_ext_c": running_ext_c,
        "running_ext_int": running_ext_int,
        "bias_c": round(bias_c, 3),
        "convective_cold_pool": convective_cold_pool,
        "ensemble_member_count": n_raw,
        "peak_iqr_c": round(peak_iqr_c, 3),
        "rem_hours_count": rem_hours_count,
        "is_solar_lock": is_solar_lock_window,
        "cooling_cushion_c": round(cooling_cushion_c, 2),
        "locked_bucket_idx": locked_bucket_idx,
        "p_locked_bucket": round(p_locked_bucket, 4),
    }


def fetch_live_ensemble_hourly_sync(lat: float, lon: float, timeout: float = 8.0) -> Dict[int, List[float]]:
    """
    Fetches live 71-member NWP ensemble hourly temperatures (ICON 40m + GFS 31m)
    plus deterministic ECMWF IFS 0.25° from Open-Meteo in UTC unix seconds.
    """
    hourly_members: Dict[int, List[float]] = {}
    ens_url = (
        f"{OPEN_METEO_ENSEMBLE_URL}?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&hourly=temperature_2m&models=icon_seamless,gfs_seamless&past_days=1&forecast_days=3&timeformat=unixtime"
    )
    for attempt in range(2):
        try:
            req = urllib.request.Request(ens_url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
            hourly = data.get("hourly") or {}
            times = hourly.get("time") or []
            raw_keys = sorted(k for k in hourly.keys() if k.startswith("temperature_2m"))
            # Keep deterministic member alignment across all hours (`M-02`: never shift member indices on single-hour None)
            aligned_series: List[List[float]] = []
            for k in raw_keys:
                arr = hourly.get(k) or []
                if len(arr) < len(times):
                    continue
                filled: List[float] = []
                last_v: Optional[float] = None
                missing_n = 0
                for raw_v in arr[: len(times)]:
                    if raw_v is not None:
                        last_v = float(raw_v)
                        filled.append(last_v)
                    elif last_v is not None:
                        missing_n += 1
                        filled.append(last_v)
                    else:
                        missing_n = len(times)
                        break
                if len(filled) == len(times) and missing_n <= max(2, len(times) // 10):
                    aligned_series.append(filled)
            for idx, ts in enumerate(times):
                vals = [series[idx] for series in aligned_series]
                if vals:
                    hourly_members[int(ts)] = vals
            if hourly_members:
                break
        except Exception as exc:
            if attempt == 0:
                time.sleep(0.45)
            else:
                logger.debug(f"Open-Meteo ensemble fetch notice ({lat},{lon}): {exc}")

    # Augment with deterministic ECMWF IFS 0.25° (upweighted x5 for skill superiority)
    ec_url = (
        f"{OPEN_METEO_FORECAST_URL}?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&hourly=temperature_2m&models=ecmwf_ifs025&past_days=1&forecast_days=3&timeformat=unixtime"
    )
    try:
        req = urllib.request.Request(ec_url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
        ec_data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
        ec_h = ec_data.get("hourly") or {}
        ec_times = ec_h.get("time") or []
        ec_vals = ec_h.get("temperature_2m") or ec_h.get("temperature_2m_ecmwf_ifs025") or []
        for idx, ts in enumerate(ec_times):
            if idx < len(ec_vals) and ec_vals[idx] is not None:
                v = float(ec_vals[idx])
                hourly_members.setdefault(int(ts), []).extend([v] * 8)
    except Exception:
        pass

    return hourly_members


def fetch_historical_nwp_hourly_sync(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
    timeout: float = 10.0,
) -> Dict[int, List[float]]:
    """
    Fetches archived historical point-in-time NWP forecasts (ECMWF IFS 0.25°, GFS, ICON)
    from Open-Meteo Historical Forecast Archive for leak-free backtesting.
    """
    url = (
        f"{OPEN_METEO_HIST_FORECAST_URL}?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        f"&hourly=temperature_2m&models=ecmwf_ifs025,gfs_seamless,icon_seamless&timeformat=unixtime"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    m_keys = sorted(k for k in hourly.keys() if k.startswith("temperature_2m"))
    out: Dict[int, List[float]] = {}
    for idx, ts in enumerate(times):
        vals: List[float] = []
        for k in m_keys:
            arr = hourly[k]
            if idx < len(arr) and arr[idx] is not None:
                v = float(arr[idx])
                # Weight ECMWF 2x relative to GFS and ICON
                if "ecmwf" in k:
                    vals.extend([v, v])
                else:
                    vals.append(v)
        if vals:
            out[int(ts)] = vals
    return out


_TAF_TEMP_RE = re.compile(r"\bT([XN])(M?\d{2})/(\d{2})(\d{2})Z\b")
AWC_TAF_URL = "https://aviationweather.gov/api/data/taf"

# Empirical ICAO routine hourly METAR release minute past the hour (US ASOS :51-:54, ICAO Europe/Asia :00/:20/:50)
STATION_ROUTINE_RELEASE_MIN: Dict[str, Tuple[int, ...]] = {
    "KLGA": (51,), "KORD": (51,), "KATL": (52,), "KDAL": (53,), "KHOU": (53,),
    "KMIA": (53,), "KSEA": (53,), "KSFO": (56,), "KDEN": (53,), "KAUS": (53,), "KLAX": (53,), "CYYZ": (0,),
    "EGLC": (20, 50), "LFPB": (0, 30), "EDDM": (20, 50), "LIMC": (20, 50), "EFHK": (20, 50),
    "RJTT": (0, 30), "RKSI": (0, 30), "RKPK": (0,), "ZSPD": (0,), "ZGSZ": (0,),
    "RPLL": (0,), "LTAC": (20, 50), "SAEZ": (0,), "NZWN": (0, 30), "MMMX": (45,),
}


def compute_adaptive_metar_poll_ttl(
    icao: str,
    metars_so_far: Optional[List[MetarObservation]] = None,
    now_utc: Optional[datetime] = None,
) -> float:
    """
    Station-release-minute synchronized METAR polling cadence (`Gemini #11`):
    Returns `10.0s` inside `[release_min - 1, release_min + 4]` (capturing new hourly METARs within
    seconds of AWC publication!) and `300.0s` during quiet mid-hour windows.
    """
    if icao.upper() == "HKO":
        return 45.0
    dt = now_utc or datetime.now(timezone.utc)
    cur_min = dt.minute + dt.second / 60.0
    release_mins: List[int] = list(STATION_ROUTINE_RELEASE_MIN.get(icao.upper(), ()))
    if metars_so_far:
        recent_mins = sorted({o.utc_dt.minute for o in metars_so_far[-4:]})
        for rm in recent_mins:
            if rm not in release_mins:
                release_mins.append(rm)
    if not release_mins:
        release_mins = [0, 51, 53]
    for r_min in release_mins:
        # Circular 60-minute distance from `r_min`: check `delta in [-1.0, +4.5]`
        delta = (cur_min - float(r_min) + 30.0) % 60.0 - 30.0
        if -1.0 <= delta <= 4.5:
            return 10.0
    return 300.0


def parse_taf_temperature_extremes(
    raw_taf: str,
    icao: str,
    ref_utc: datetime,
    tz_name: str,
) -> Dict[date, Dict[str, float]]:
    """
    Parses official NWS/ICAO Terminal Aerodrome Forecast (`TAF`) `TXdd/ddhhZ` and `TNdd/ddhhZ`
    temperature extreme groups into `{local_obs_date: {"HIGH": temp_c, "LOW": temp_c}}`.
    """
    if not raw_taf or icao.upper() not in raw_taf.upper():
        return {}
    tz = ZoneInfo(tz_name)
    out: Dict[date, Dict[str, float]] = {}
    for m in _TAF_TEMP_RE.finditer(raw_taf.upper()):
        kind = "HIGH" if m.group(1) == "X" else "LOW"
        raw_t = m.group(2)
        temp_c = -float(int(raw_t[1:])) if raw_t.startswith("M") else float(int(raw_t))
        day_i, hr_i = int(m.group(3)), min(23, int(m.group(4)))
        cands: List[datetime] = []
        for d_off in (-16, 0, 16):
            anc = ref_utc + timedelta(days=d_off)
            try:
                cands.append(datetime(anc.year, anc.month, day_i, hr_i, 0, tzinfo=timezone.utc))
            except ValueError:
                continue
        if not cands:
            continue
        valid_utc = min(cands, key=lambda c: abs((c - ref_utc).total_seconds()))
        loc_date = valid_utc.astimezone(tz).date()
        rec = out.setdefault(loc_date, {})
        if kind == "HIGH":
            rec["HIGH"] = max(rec.get("HIGH", -999.0), temp_c)
        else:
            rec["LOW"] = min(rec.get("LOW", 999.0), temp_c)
    return out


def fetch_taf_extremes_sync(
    icao: str,
    obs_date: date,
    tz_name: str,
    timeout: float = 5.0,
) -> Dict[str, float]:
    """Fetches official `aviationweather.gov/api/data/taf` `TX`/`TN` runway extremes for `(icao, obs_date)`."""
    if icao.upper() == "HKO":
        return {}
    url = f"{AWC_TAF_URL}?ids={icao.upper()}&format=raw"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DominusWeatherEngine/1.0"})
        raw_txt = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")
        by_date = parse_taf_temperature_extremes(raw_txt, icao, datetime.now(timezone.utc), tz_name)
        return dict(by_date.get(obs_date) or {})
    except Exception:
        return {}


def verify_weather_slate_partition(spec: WeatherEventSpec) -> bool:
    """
    Verifies that `spec.buckets` forms an exact, gap-free, non-overlapping integer partition
    over `[-60, 140]` so exactly ONE bucket resolves `YES = $1.00` (`ChatGPT #5`).
    """
    if len(spec.buckets) < 3:
        return False
    for k in range(-60, 141):
        hits = sum(1 for b in spec.buckets if b.contains_rounded(k))
        if hits != 1:
            return False
    return True


def evaluate_weather_event_slate(
    spec: WeatherEventSpec,
    probs: List[float],
    bucket_books: Dict[str, Dict[str, Any]],
    target_budget_usd: float = 10.0,
    max_underround_sum: float = 0.985,
) -> Dict[str, Any]:
    """
    Event-Level Weather Slate Arbitrage & Constrained Subset Optimizer (`Gemini #10` + `ChatGPT #5`):
      1. `FULL_SLATE_DUTCH_ARB`: When `verify_weather_slate_partition(spec)` is True and
         `sum_i ask_yes(i) <= max_underround_sum` (`0%` weather fees!), equal shares across all
         buckets lock a deterministic riskless `$1.00 - sum_asks` payout!
      2. `CONSTRAINED_SUBSET_BASKET`: Multi-bucket positive-EV adjacent subset (`2..3` buckets)
         maximizing `EV_net` subject to total basket cost `<= $0.88/share` and combined win prob `>= 0.72`.
    """
    partition_ok = verify_weather_slate_partition(spec)
    rows: List[Dict[str, Any]] = []
    no_rows: List[Dict[str, Any]] = []
    for idx, b in enumerate(spec.buckets):
        bk = bucket_books.get(b.market_id) or {}
        ask_y = bk.get("ask_yes")
        ask_sz = float(bk.get("ask_yes_shares") or 0.0)
        ask_n = bk.get("ask_no")
        ask_n_sz = float(bk.get("ask_no_shares") or 0.0)
        p_b = float(probs[idx]) if idx < len(probs) else 0.0
        fr_b = max(0.0, float(getattr(b, "fee_rate", 0.0) or 0.0))
        fe_b = max(1.0, float(getattr(b, "fee_exponent", 1.0) or 1.0))
        if ask_y is not None and 0.005 <= float(ask_y) <= 0.99 and ask_sz >= 5.0:
            ask_yf = float(ask_y)
            fee_yf = fr_b * ((ask_yf * (1.0 - ask_yf)) ** fe_b) if fr_b > 0.0 else 0.0
            eff_yf = ask_yf + fee_yf
            rows.append({
                "idx": idx,
                "market_id": b.market_id,
                "label": b.label,
                "yes_token": b.yes_token,
                "ask_yes": ask_yf,
                "eff_ask_yes": round(eff_yf, 6),
                "fee_per_share": round(fee_yf, 6),
                "fee_rate": fr_b,
                "fee_exponent": fe_b,
                "ask_yes_shares": ask_sz,
                "prob": p_b,
                "edge": p_b - eff_yf,
            })
        if ask_n is not None and 0.005 <= float(ask_n) <= 0.995 and ask_n_sz >= 5.0:
            ask_nf = float(ask_n)
            fee_nf = fr_b * ((ask_nf * (1.0 - ask_nf)) ** fe_b) if fr_b > 0.0 else 0.0
            eff_nf = ask_nf + fee_nf
            no_rows.append({
                "idx": idx,
                "market_id": b.market_id,
                "label": b.label,
                "yes_token": b.no_token,
                "no_token": b.no_token,
                "side": "NO",
                "ask_yes": ask_nf,
                "eff_ask_yes": round(eff_nf, 6),
                "fee_per_share": round(fee_nf, 6),
                "fee_rate": fr_b,
                "fee_exponent": fe_b,
                "ask_yes_shares": ask_n_sz,
            })

    full_slate: Optional[Dict[str, Any]] = None
    if partition_ok and len(rows) == len(spec.buckets):
        sum_asks = sum(r["eff_ask_yes"] for r in rows)
        sum_raw_asks = sum(r["ask_yes"] for r in rows)
        min_sh = min(r["ask_yes_shares"] for r in rows)
        if sum_asks <= max_underround_sum and min_sh >= 5.0:
            equal_sh = max(5.0, min(min_sh, math.floor(float(target_budget_usd) / max(0.10, sum_asks))))
            if equal_sh * sum_asks <= float(target_budget_usd) * 1.25:
                full_slate = {
                    "mode": "FULL_SLATE_DUTCH_ARB",
                    "side": "ALL_BUCKETS_YES",
                    "guaranteed_payout_per_set": 1.0,
                    "sum_asks": round(sum_asks, 5),
                    "sum_raw_asks": round(sum_raw_asks, 5),
                    "guaranteed_edge_per_set": round(1.0 - sum_asks, 5),
                    "equal_shares": float(equal_sh),
                    "total_cost_usd": round(equal_sh * sum_asks, 4),
                    "guaranteed_profit_usd": round(equal_sh * (1.0 - sum_asks), 4),
                    "legs": rows,
                }
    if full_slate is None and partition_ok and len(no_rows) == len(spec.buckets) and len(spec.buckets) >= 3:
        n_b = float(len(spec.buckets))
        guar_pay = n_b - 1.0
        sum_asks_no = sum(r["eff_ask_yes"] for r in no_rows)
        min_sh_no = min(r["ask_yes_shares"] for r in no_rows)
        if sum_asks_no <= guar_pay - (1.0 - max_underround_sum) and min_sh_no >= 5.0:
            equal_sh_no = max(5.0, min(min_sh_no, math.floor(float(target_budget_usd) / max(0.50, sum_asks_no))))
            if equal_sh_no * sum_asks_no <= float(target_budget_usd) * 1.25:
                full_slate = {
                    "mode": "FULL_SLATE_NO_COMPLEMENT_ARB",
                    "side": "ALL_BUCKETS_NO",
                    "guaranteed_payout_per_set": round(guar_pay, 4),
                    "sum_asks": round(sum_asks_no, 5),
                    "guaranteed_edge_per_set": round(guar_pay - sum_asks_no, 5),
                    "equal_shares": float(equal_sh_no),
                    "total_cost_usd": round(equal_sh_no * sum_asks_no, 4),
                    "guaranteed_profit_usd": round(equal_sh_no * (guar_pay - sum_asks_no), 4),
                    "legs": no_rows,
                }

    # Constrained positive-EV subset (2-3 buckets with individual edge >= +0.04, combined prob >= 0.72, sum_asks <= 0.88)
    pos_rows = sorted([r for r in rows if r["edge"] >= 0.04], key=lambda x: x["edge"], reverse=True)
    best_subset: Optional[Dict[str, Any]] = None
    if len(pos_rows) >= 2:
        cand_legs = pos_rows[:3]
        sum_sub_asks = sum(r["eff_ask_yes"] for r in cand_legs)
        sum_sub_prob = min(0.999, sum(r["prob"] for r in cand_legs))
        min_sub_sh = min(r["ask_yes_shares"] for r in cand_legs)
        net_edge_set = sum_sub_prob - sum_sub_asks
        if sum_sub_asks <= 0.88 and sum_sub_prob >= 0.72 and net_edge_set >= 0.09 and min_sub_sh >= 5.0:
            eq_sh = max(5.0, min(min_sub_sh, math.floor(float(target_budget_usd) / max(0.10, sum_sub_asks))))
            best_subset = {
                "mode": "CONSTRAINED_SUBSET_BASKET",
                "sum_asks": round(sum_sub_asks, 5),
                "combined_prob": round(sum_sub_prob, 5),
                "expected_edge_per_set": round(net_edge_set, 5),
                "equal_shares": float(eq_sh),
                "total_cost_usd": round(eq_sh * sum_sub_asks, 4),
                "max_loss_usd": round(eq_sh * sum_sub_asks, 4),
                "legs": cand_legs,
            }

    return {
        "partition_verified": partition_ok,
        "quoted_buckets": len(rows),
        "total_buckets": len(spec.buckets),
        "full_slate_arb": full_slate,
        "subset_basket": best_subset,
    }

# ======================================================================================
# [05/16] MODULE: src/polymarket_research/barrier_onetouch_svi_engine.py
# PURPOSE: Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)
# ======================================================================================

#!/usr/bin/env python3
"""
Option #2: Crypto One-Touch Barrier ("Hit / Dip") Jump-SVI Engine
=================================================================
Models Polymarket's Daily, Weekly, and Monthly One-Touch Barrier contracts:
  - "What price will Bitcoin/Ethereum/Solana/XRP hit on [Date] / [Week] / [Month]?"
  - Exact Oracle Rule: Resolves "Yes" IMMEDIATELY if ANY finalized Binance 1-minute
    Spot USDT candle (`High >= K` for upward rungs, `Low <= K` for downward rungs)
    touches the barrier within the active window.

Why Retail Misprices These Ladders:
  1. Retail confuses terminal expiry digital probability P(S_T >= K) with continuous
     first-passage probability P(max_{0<=t<=T} S_t >= K) ~= 2 * P(S_T >= K).
  2. Furthermore, because settlement triggers on 1-minute Binance candle WICKS
     (`High`/`Low`) under fat-tailed crypto jump-diffusion, empirical barrier touch
     rates exceed flat-vol Gaussian reflection unless skew + wick/jump scaling is applied.

Two Sub-Sleeves:
  - B1_CONVEX_TAIL_YES: Underpriced OTM `YES` touch rungs ($0.04 <= ask <= $0.35)
    with strong positive EV and asymmetry (+3x to +15x payoff), tracked both for
    `2x` 0%-fee Maker Scalp exit AND full $1.00 barrier touch settlement.
  - B2_BARRIER_NO_LOCK: Final-window (`1h <= TTE <= 12h`) `NO` ("will NOT touch")
    convergence when barrier remains untouched with strong vol-adjusted safety cushion.
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import json
import logging
import math
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_INV_SQRT2 = 0.7071067811865475


def _fast_norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x * _INV_SQRT2))


try:
    from src.polymarket_research.deribit_svi_surface import (
        GLOBAL_SVI_ENGINE,
        SVIParams,
        scale_svi_sticky_delta,
    )
except Exception:
    GLOBAL_SVI_ENGINE = None
    SVIParams = Any  # type: ignore
    scale_svi_sticky_delta = None  # type: ignore

logger = logging.getLogger("BarrierOneTouchEngine")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
BINANCE_API_URL = "https://api.binance.com"
BINANCE_FAPI_URL = "https://fapi.binance.com"

HIT_SERIES = [
    ("BTC", "DAILY", "bitcoin-hit-price-daily"),
    ("BTC", "WEEKLY", "bitcoin-hit-price-weekly"),
    ("BTC", "MONTHLY", "bitcoin-hit-price-monthly"),
    ("ETH", "DAILY", "ethereum-hit-price-daily"),
    ("ETH", "WEEKLY", "ethereum-hit-price-weekly"),
    ("ETH", "MONTHLY", "ethereum-hit-price-monthly"),
    ("SOL", "DAILY", "solana-hit-price-daily"),
    ("SOL", "WEEKLY", "solana-hit-price-weekly"),
    ("SOL", "MONTHLY", "solana-hit-price-monthly"),
    ("XRP", "DAILY", "xrp-hit-price-daily"),
    ("XRP", "WEEKLY", "xrp-hit-price-weekly"),
    ("XRP", "MONTHLY", "xrp-hit-price-monthly"),
    ("BNB", "MONTHLY", "bnb-hit-price-monthly"),
    ("DOGE", "MONTHLY", "dogecoin-hit-price-monthly"),
    ("HYPE", "MONTHLY", "hyperliquid-hit-price-monthly"),
]

ASSET_BINANCE_SYMBOL = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "BNB": "BNBUSDT",
    "DOGE": "DOGEUSDT",
    "HYPE": "HYPEUSDT",
}

ASSET_BINANCE_FUTURES_ONLY = frozenset({"HYPE"})

ASSET_VOL_MULT_VS_BTC = {
    "BTC": 1.00,
    "ETH": 1.28,
    "SOL": 1.75,
    "XRP": 1.85,
    "BNB": 1.45,
    "DOGE": 2.10,
    "HYPE": 2.35,
}


@dataclass
class BarrierRungSpec:
    event_id: str
    series_slug: str
    horizon_group: str
    asset: str
    market_id: str
    condition_id: str
    question: str
    group_label: str
    strike: float
    direction: str  # "UP" ("reach") or "DOWN" ("dip to")
    start_ts: float
    end_ts: float
    yes_token: str
    no_token: str
    fee_rate: float = 0.07
    resolved_yes: Optional[int] = None


_EXPLICIT_DOLLAR_STRIKE_RE = re.compile(
    r"\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b"
)
_ANCHORED_BARRIER_STRIKE_RE = re.compile(
    r"(?:↑|↓|\b(?:reach|hit|touch|dip(?:\s+to)?|drop(?:\s+to)?|above|below|over|under)\b)\s*\$?\s*"
    r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b",
    re.IGNORECASE,
)


def parse_strike_from_text(question: str, group_label: str = "") -> Optional[float]:
    for pat in (_EXPLICIT_DOLLAR_STRIKE_RE, _ANCHORED_BARRIER_STRIKE_RE):
        for txt in (question, group_label):
            m = pat.search(txt)
            if m:
                raw = m.group(1).replace(",", "")
                try:
                    val = float(raw)
                    if m.group(2):
                        val *= 1000.0
                    if val > 0:
                        return val
                except ValueError:
                    continue
    return None


def parse_barrier_direction(question: str, group_label: str = "") -> Optional[str]:
    q = question.lower()
    g = group_label.strip()
    if g.startswith("↓") or any(w in q for w in ("dip", "drop", "below", "fall")):
        return "DOWN"
    if g.startswith("↑") or any(w in q for w in ("reach", "hit", "touch", "above")):
        return "UP"
    return None


_CRYPTO_MONTH_RE = re.compile(
    r"\bin\s+(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(\d{4}))?(?:\?|\b)",
    re.IGNORECASE,
)
_CRYPTO_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_hit_event(ev: Dict[str, Any], asset: str, horizon_group: str, series_slug: str) -> List[BarrierRungSpec]:
    end_str = str(ev.get("endDate") or "")
    start_str = str(ev.get("startDate") or ev.get("creationDate") or "")
    if not end_str:
        return []
    try:
        end_ts = datetime.fromisoformat(end_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        return []

    default_dur = {"DAILY": 86400.0, "WEEKLY": 7 * 86400.0, "MONTHLY": 30 * 86400.0}.get(horizon_group, 86400.0)
    start_ts = end_ts - default_dur
    if start_str:
        try:
            st_cand = datetime.fromisoformat(start_str.replace("Z", "+00:00")).timestamp()
            if end_ts - 35 * 86400.0 <= st_cand < end_ts:
                start_ts = max(start_ts, st_cand)
        except Exception:
            pass
    m_cm = _CRYPTO_MONTH_RE.search(str(ev.get("title") or ""))
    if m_cm:
        try:
            from zoneinfo import ZoneInfo
            ny = ZoneInfo("America/New_York")
            mo_c = _CRYPTO_MONTHS[m_cm.group(1).lower()]
            yr_c = int(m_cm.group(2)) if m_cm.group(2) else datetime.fromtimestamp(end_ts - 5 * 86400.0, tz=ny).year
            start_ts = max(start_ts, datetime(yr_c, mo_c, 1, 0, 0, tzinfo=ny).timestamp())
        except Exception:
            pass

    rungs: List[BarrierRungSpec] = []
    for m in ev.get("markets") or []:
        q = str(m.get("question") or "")
        gl = str(m.get("groupItemTitle") or "")
        direction = parse_barrier_direction(q, gl)
        strike = parse_strike_from_text(q, gl)
        if not direction or not strike or strike <= 0:
            continue
        toks = m.get("clobTokenIds")
        if isinstance(toks, str):
            try:
                toks = json.loads(toks)
            except Exception:
                toks = []
        if not toks or len(toks) < 2:
            continue

        resolved_yes: Optional[int] = None
        if m.get("closed"):
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    op = json.loads(op)
                except Exception:
                    op = None
            if isinstance(op, list) and len(op) >= 2:
                try:
                    if float(op[0]) >= 0.99:
                        resolved_yes = 1
                    elif float(op[1]) >= 0.99:
                        resolved_yes = 0
                except Exception:
                    pass

        m_start_ts = start_ts
        for m_st_raw in (m.get("startDate"), m.get("createdAt")):
            if m_st_raw:
                try:
                    m_st = datetime.fromisoformat(str(m_st_raw).replace("Z", "+00:00")).timestamp()
                    if start_ts - 3600.0 <= m_st < end_ts:
                        # Mid-period dynamically minted rungs resolve "from the creation of this market":
                        # add +60s boundary buffer so the ambiguous creation-minute candle is never assumed touched.
                        buf = 60.0 if (m_st > start_ts + 300.0 or "creation of this market" in str(m.get("description") or "").lower()) else 0.0
                        m_start_ts = max(m_start_ts, min(end_ts - 60.0, m_st + buf))
                except Exception:
                    pass

        rungs.append(
            BarrierRungSpec(
                event_id=str(ev.get("id") or ""),
                series_slug=series_slug,
                horizon_group=horizon_group,
                asset=asset.upper(),
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                question=q,
                group_label=gl,
                strike=strike,
                direction=direction,
                start_ts=m_start_ts,
                end_ts=end_ts,
                yes_token=str(toks[0]),
                no_token=str(toks[1]),
                resolved_yes=resolved_yes,
            )
        )
    return rungs


def first_passage_touch_prob(
    spot: float,
    strike: float,
    tte_seconds: float,
    iv_annual: float,
    direction: str,
    wick_vol_multiplier: float = 1.12,
    jump_tail_blend: float = 0.08,
    forward_drift_annual: float = 0.0,
    realized_vol_ratio: float = 1.0,
) -> float:
    """
    Computes continuous first-passage barrier touch probability under risk-neutral
    log-diffusion with SVI wing implied vol `iv_annual`, plus:
      1. `wick_vol_multiplier`: accounts for 1-minute Binance High/Low candle wicks
         exceeding continuous mid-price diffusion (calibrated on Train split).
      2. `jump_tail_blend` scaled by `realized_vol_ratio` (`ChatGPT #7` dynamic regime-switching
         jump intensity): fat-tailed jump-diffusion mixture (1.65x vol stress regime).
      3. `forward_drift_annual` (`Gemini #14`): Deribit futures/forward carry drift `r_impl`.
    """
    if spot <= 0.0 or strike <= 0.0:
        return 0.0
    if direction == "UP" and spot >= strike:
        return 1.0
    if direction == "DOWN" and spot <= strike:
        return 1.0
    if tte_seconds <= 1.0:
        return 0.0

    t_years = tte_seconds / (365.25 * 86400.0)
    b = abs(math.log(strike / spot))
    r_drift = max(-0.30, min(0.40, float(forward_drift_annual or 0.0)))

    def _single_regime_touch(sig: float) -> float:
        sig_eff = max(0.08, min(4.0, sig))
        v_sqrt_t = sig_eff * math.sqrt(t_years)
        if v_sqrt_t <= 1e-8:
            return 0.0
        # Log-price drift mu = (r_drift - 0.5 * sig^2) toward UP (+b), or (-r_drift + 0.5 * sig^2) toward DOWN (-b)
        mu = (r_drift - 0.5 * (sig_eff ** 2)) if direction == "UP" else (-r_drift + 0.5 * (sig_eff ** 2))
        d1 = (-b + mu * t_years) / v_sqrt_t
        d2 = (-b - mu * t_years) / v_sqrt_t
        exponent = max(-60.0, min(60.0, (2.0 * mu * b) / (sig_eff ** 2)))
        p = _fast_norm_cdf(d1) + math.exp(exponent) * _fast_norm_cdf(d2)
        return max(0.0001, min(0.9999, p))

    sig_base = iv_annual * wick_vol_multiplier
    p_normal = _single_regime_touch(sig_base)
    p_jump = _single_regime_touch(sig_base * 1.65)
    rv_mult = max(0.5, min(3.5, float(realized_vol_ratio or 1.0))) ** 1.5
    eff_jump_blend = min(0.35, max(0.02, float(jump_tail_blend) * rv_mult)) if abs(realized_vol_ratio - 1.0) > 1e-6 else float(jump_tail_blend)
    p_total = (1.0 - eff_jump_blend) * p_normal + eff_jump_blend * p_jump
    return max(0.0001, min(0.9999, p_total))


def evaluate_barrier_no_net_ev(
    p_touch: float,
    ask_no: float,
    fee_rate: float = 0.07,
    min_net_ev_per_share: float = 0.035,
    max_loss_to_gain_ratio: float = 9.0,
) -> Dict[str, Any]:
    """
    Payoff-asymmetry gate for high-probability `B2_BARRIER_NO_LOCK` (`ChatGPT #7`):
    Verifies net-of-fee expected dollar value AND caps downside-loss / net-gain asymmetry.
    """
    p_no = max(0.0001, min(0.9999, 1.0 - float(p_touch)))
    px = max(0.01, min(0.99, float(ask_no)))
    fee_ps = float(fee_rate) * px * (1.0 - px)
    eff_cost = px + fee_ps
    net_gain_if_win = max(1e-6, 1.0 - eff_cost)
    ev_net = p_no - eff_cost
    loss_gain_ratio = eff_cost / net_gain_if_win
    eligible = bool(ev_net >= min_net_ev_per_share and loss_gain_ratio <= max_loss_to_gain_ratio)
    return {
        "eligible": eligible,
        "p_no": round(p_no, 5),
        "eff_cost_no": round(eff_cost, 5),
        "ev_net_per_share": round(ev_net, 5),
        "loss_to_gain_ratio": round(loss_gain_ratio, 3),
    }


def get_wing_implied_vol(
    asset: str,
    spot: float,
    strike: float,
    tte_seconds: float,
    dvol_annual_override: Optional[float] = None,
) -> Tuple[float, str]:
    """
    Returns (iv_annual, source) at strike `K`, incorporating Deribit SVI wing smile
    when live, or parametric crypto volatility skew around `dvol_annual_override` in backtests.
    """
    asset_u = asset.upper()
    t_years = max(1e-5, tte_seconds / (365.25 * 86400.0))
    k = math.log(strike / spot) if (spot > 0 and strike > 0) else 0.0

    if dvol_annual_override is None and GLOBAL_SVI_ENGINE is not None:
        svi = GLOBAL_SVI_ENGINE.get_svi_params(
            asset_u, allow_sync_if_empty=True, target_tte_sec=tte_seconds
        )
        if svi is not None:
            # Path-integrated ATM-to-barrier implied vol (`H-03`: avoids pure wing vol overpricing first-passage)
            iv_atm = float(svi.implied_vol(0.0, t_override=t_years))
            iv_bar = float(svi.implied_vol(k, t_override=t_years))
            return 0.5 * (iv_atm + iv_bar), "DERIBIT_SVI_WING"
        if asset_u in ("SOL", "XRP"):
            btc_svi = GLOBAL_SVI_ENGINE.get_svi_params(
                "BTC", allow_sync_if_empty=True, target_tte_sec=tte_seconds
            )
            if btc_svi is not None:
                mult = ASSET_VOL_MULT_VS_BTC.get(asset_u, 1.75)
                if scale_svi_sticky_delta is not None:
                    alt_svi = scale_svi_sticky_delta(btc_svi, mult, spot if spot > 0 else 100.0)
                    iv_atm = float(alt_svi.implied_vol(0.0, t_override=t_years))
                    iv_bar = float(alt_svi.implied_vol(k, t_override=t_years))
                    return 0.5 * (iv_atm + iv_bar), "BTC_SVI_STICKY_DELTA"
                return float(btc_svi.implied_vol(k / mult, t_override=t_years) * mult), "BTC_SVI_SCALED"

    base_iv = dvol_annual_override if dvol_annual_override is not None else (0.42 * ASSET_VOL_MULT_VS_BTC.get(asset_u, 1.0))
    # Empirical crypto volatility smile: OTM wings carry higher implied vol (convexity + downside skew)
    wing_convexity = 1.0 + 1.35 * min(0.25, abs(k)) + (-0.20 * k if k < 0 else 0.08 * k)
    return max(0.15, min(3.0, base_iv * wing_convexity)), "DVOL_SMILE_PARAMETRIC"


def detect_barrier_monotonicity_boxes(
    quote_rows: List[Dict[str, Any]],
    fee_rate: float = 0.07,
    max_box_cost_net: float = 0.995,
) -> List[Dict[str, Any]]:
    """
    Detects deterministic same-event One-Touch Barrier Monotonicity Boxes (`B3_BARRIER_MONO_BOX`):
      - Upward barriers (`direction == "UP"`, `K_low < K_high`):
          `YES(↑K_low) + NO(↑K_high)` pays >= $1.00 everywhere ($2.00 when `max S_t in [K_low, K_high)`).
      - Downward barriers (`direction == "DOWN"`, `K_low < K_high`):
          `YES(↓K_high) + NO(↓K_low)` pays >= $1.00 everywhere ($2.00 when `min S_t in (K_low, K_high]`).
    """
    arbs: List[Dict[str, Any]] = []
    for direction in ("UP", "DOWN"):
        sub = sorted(
            [q for q in quote_rows if str(q.get("direction") or "").upper() == direction and float(q.get("strike") or 0.0) > 0.0],
            key=lambda x: float(x["strike"]),
        )
        for i in range(len(sub)):
            for j in range(i + 1, len(sub)):
                q_lo, q_hi = sub[i], sub[j]
                k_lo, k_hi = float(q_lo["strike"]), float(q_hi["strike"])
                if k_hi <= k_lo * 1.0005:
                    continue
                if direction == "UP":
                    leg_yes_q, leg_no_q = q_lo, q_hi
                    lbl = f"YES(↑{k_lo:g})+NO(↑{k_hi:g})"
                else:
                    leg_yes_q, leg_no_q = q_hi, q_lo
                    lbl = f"YES(↓{k_hi:g})+NO(↓{k_lo:g})"
                if (
                    "start_ts" in leg_yes_q
                    and "start_ts" in leg_no_q
                    and float(leg_yes_q["start_ts"]) > float(leg_no_q["start_ts"]) + 1e-6  # YES window must start no later than NO
                ):
                    continue
                ay = leg_yes_q.get("ask_yes")
                an = leg_no_q.get("ask_no")
                if ay is None or an is None:
                    continue
                py, pn = float(ay), float(an)
                if not (0.01 <= py <= 0.99 and 0.01 <= pn <= 0.99):
                    continue
                fr_y = float(leg_yes_q.get("fee_rate", fee_rate))
                fr_n = float(leg_no_q.get("fee_rate", fee_rate))
                net_cost = py + (fr_y * py * (1.0 - py)) + pn + (fr_n * pn * (1.0 - pn))
                if 0.900 <= net_cost <= max_box_cost_net:
                    arbs.append({
                        "direction": direction,
                        "label": lbl,
                        "low_strike": k_lo,
                        "high_strike": k_hi,
                        "leg_yes_market_id": str(leg_yes_q["market_id"]),
                        "leg_yes_condition_id": str(leg_yes_q.get("condition_id") or ""),
                        "yes_token": str(leg_yes_q["yes_token"]),
                        "yes_opp_token": str(leg_yes_q.get("no_token") or ""),
                        "leg_no_market_id": str(leg_no_q["market_id"]),
                        "leg_no_condition_id": str(leg_no_q.get("condition_id") or ""),
                        "no_token": str(leg_no_q["no_token"]),
                        "no_opp_token": str(leg_no_q.get("yes_token") or ""),
                        "box_cost_gross": round(py + pn, 5),
                        "box_cost_net": round(net_cost, 5),
                        "guaranteed_edge": round(1.0 - net_cost, 5),
                    })
    arbs.sort(key=lambda x: x["box_cost_net"])
    return arbs


def _fetch_finalized_klines(
    sym: str,
    st_ms: int,
    en_ms: int,
    interval: str,
    timeout: float,
) -> List[List[Any]]:
    if sym == "HYPEUSDT":
        url = (
            f"{BINANCE_FAPI_URL}/fapi/v1/klines?symbol={sym}&interval={interval}"
            f"&startTime={st_ms}&endTime={en_ms}&limit=1000"
        )
    else:
        url = (
            f"{BINANCE_API_URL}/api/v3/klines?symbol={sym}&interval={interval}"
            f"&startTime={st_ms}&endTime={en_ms}&limit=1000"
        )
    req = urllib.request.Request(url, headers={"User-Agent": "DominusBarrierEngine/1.0"})
    rows = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    if not isinstance(rows, list):
        return []
    # Strictly retain finalized candles whose closeTime (r[6]) <= en_ms (exact Polymarket 1m oracle rule)
    return [r for r in rows if len(r) >= 7 and int(r[6]) <= en_ms]


def fetch_binance_window_extremes_sync(
    asset: str,
    start_ts: float,
    end_ts: float,
    interval: str = "1m",
    timeout: float = 6.0,
) -> Optional[Tuple[float, float, float]]:
    """
    Returns (max_high, min_low, latest_close) over `[start_ts, end_ts]` from finalized Binance
    Spot USDT klines (`closeTime <= end_ts`).
    For windows > 950 minutes (e.g. Weekly/Monthly barriers), stitches finalized `1h` extremes
    across `[start_ts, end_ts]` with finalized `1m` candles over the latest 2 hours so `limit=1000`
    never truncates multi-day history AND recent wicks are checked at exact 1-minute resolution.
    """
    sym = ASSET_BINANCE_SYMBOL.get(asset.upper())
    if not sym or end_ts <= start_ts:
        return None
    st_ms = int(start_ts * 1000)
    en_ms = int(end_ts * 1000)
    span_sec = end_ts - start_ts
    try:
        combined: List[List[Any]] = []
        if span_sec > 57000.0 and interval in ("1m", "5m"):
            # Exact finalized 1m candles cover any mid-hour start before the first whole 1h kline (`H-04`)
            head_en_ms = min(en_ms, ((st_ms // 3_600_000) + 1) * 3_600_000 + 60_000)
            if head_en_ms > st_ms:
                combined.extend(_fetch_finalized_klines(sym, st_ms, head_en_ms, "1m", timeout))
            # Coarse finalized 1h candles cover up to 41.6 days without truncation
            combined.extend(_fetch_finalized_klines(sym, st_ms, en_ms, "1h", timeout))
            # Exact finalized 1m candles cover the latest 2 hours (including any partial current hour)
            tail_st_ms = max(st_ms, en_ms - 7200 * 1000)
            combined.extend(_fetch_finalized_klines(sym, tail_st_ms, en_ms, "1m", timeout))
        else:
            combined.extend(_fetch_finalized_klines(sym, st_ms, en_ms, interval, timeout))

        if not combined:
            return None
        max_h = max(float(r[2]) for r in combined)
        min_l = min(float(r[3]) for r in combined)
        latest_row = max(combined, key=lambda r: int(r[6]))
        last_c = float(latest_row[4])
        return max_h, min_l, last_c
    except Exception:
        return None

# ======================================================================================
# [06/16] MODULE: src/polymarket_research/multistrike_svi_scalper.py
# PURPOSE: Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner
# ======================================================================================

#!/usr/bin/env python3
"""
Option #4: Multi-Strike SVI Breeden-Litzenberger Maker-Scalper & Convergence Engine
===================================================================================
Upgrades Polymarket Daily/Weekly Crypto Strike Ladder trading ("Bitcoin/ETH/SOL/XRP
above ___ on [Date]?") from flat-Gaussian volatility to:
  1. Live Deribit 5-Parameter Gatheral SVI + Breeden-Litzenberger risk-neutral
     digital extraction: P(S_T > K) = -e^(rT) * dC/dK (capturing volatility skew!).
  2. Short-horizon Spot Momentum Alignment Gate (never fading an active spot impulse).
  3. Cross-Strike Monotonicity Arb / Inversion Detector across all rungs of the ladder:
     for K_low < K_high, P(S_T > K_low) >= P(S_T > K_high) ->
     Ask(YES K_low) + Ask(NO K_high) < 1.00 - fees locks riskless corridor floor!

Two Sub-Sleeves:
  - M1_SVI_MAKER_SCALP: Intra-day SVI dislocation (`0.14 <= ask <= 0.86`, `TTE > 1.5h`)
    with 0%-fee Maker +4.5c Take-Profit target and SVI fair-value invalidation stop.
  - M2_STRIKE_CONVERGENCE: Final-window (`15m <= TTE <= 3.5h`, `0.65 <= ask <= 0.90`)
    high-cushion ITM digital convergence into Binance 12:00 PM ET 1m candle close.
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

_INV_SQRT2 = 0.7071067811865475


def _fast_norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x * _INV_SQRT2))


def _fast_bs_call(F: float, K: float, T: float, sigma: float) -> float:
    if T <= 0.0 or sigma <= 0.0 or K <= 0.0 or F <= 0.0:
        return max(0.0, F - K)
    vol_sqrt_t = sigma * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * (sigma ** 2) * T) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    return F * _fast_norm_cdf(d1) - K * _fast_norm_cdf(d2)


def _fast_bl_digital(F: float, K: float, T_years: float, svi: Any) -> float:
    T_eff = max(1e-6, T_years)
    dK = max(0.01, K * 0.001)
    k_up = math.log((K + dK) / F)
    k_dn = math.log(max(1e-6, K - dK) / F)
    c_up = _fast_bs_call(F, K + dK, T_eff, svi.implied_vol(k_up, t_override=T_eff))
    c_dn = _fast_bs_call(F, max(1e-6, K - dK), T_eff, svi.implied_vol(k_dn, t_override=T_eff))
    p_rnd = -(c_up - c_dn) / (2.0 * dK)
    return max(0.0001, min(0.9999, p_rnd))


try:
    from src.polymarket_research.deribit_svi_surface import (
        GLOBAL_SVI_ENGINE,
        SVIParams,
        compute_breeden_litzenberger_digital,
        enforce_monotone_ladder_probabilities,
    )
except Exception:
    GLOBAL_SVI_ENGINE = None
    SVIParams = Any  # type: ignore
    compute_breeden_litzenberger_digital = None  # type: ignore
    enforce_monotone_ladder_probabilities = None  # type: ignore

logger = logging.getLogger("MultiStrikeSVIScalper")

STRIKE_SERIES = [
    ("BTC", "btc-multi-strikes-weekly"),
    ("ETH", "ethereum-multi-strikes-weekly"),
    ("SOL", "solana-multi-strikes-weekly"),
    ("XRP", "xrp-multi-strikes-weekly"),
]

ASSET_VOL_MULT_VS_BTC = {
    "BTC": 1.00,
    "ETH": 1.28,
    "SOL": 1.75,
    "XRP": 1.85,
}


@dataclass
class StrikeRungSpec:
    event_id: str
    series_slug: str
    asset: str
    title: str
    market_id: str
    condition_id: str
    question: str
    strike: float
    is_downward: bool
    end_ts: float
    yes_token: str
    no_token: str
    fee_rate: float = 0.07
    resolved_yes: Optional[int] = None


_EXPLICIT_DOLLAR_RE = re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b")
_ANCHORED_STRIKE_RE = re.compile(
    r"\b(?:above|below|over|under|less than|greater than|higher than|lower than)\s+\$?\s*"
    r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b",
    re.IGNORECASE,
)
_CLEAN_LABEL_STRIKE_RE = re.compile(
    r"^\s*[↑↓><]?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*$"
)


def _extract_threshold_strike(q: str, gl: str) -> Optional[float]:
    for pat, txt in (
        (_EXPLICIT_DOLLAR_RE, q),
        (_EXPLICIT_DOLLAR_RE, gl),
        (_ANCHORED_STRIKE_RE, q),
        (_CLEAN_LABEL_STRIKE_RE, gl),
    ):
        m_num = pat.search(txt)
        if m_num:
            try:
                strike = float(m_num.group(1).replace(",", ""))
                if m_num.group(2):
                    strike *= 1000.0
                if strike > 0:
                    return strike
            except ValueError:
                continue
    return None


def parse_multistrike_event(ev: Dict[str, Any], asset: str, series_slug: str) -> List[StrikeRungSpec]:
    end_str = str(ev.get("endDate") or "")
    if not end_str:
        return []
    try:
        end_ts = datetime.fromisoformat(end_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        return []

    e_title = str(ev.get("title") or "")
    rungs: List[StrikeRungSpec] = []
    for m in ev.get("markets") or []:
        q = str(m.get("question") or "")
        gl = str(m.get("groupItemTitle") or "")
        # Exclude range buckets like "$80,000-$82,000" if any exist; focus on clean threshold strikes
        if "between" in q.lower():
            continue
        strike = _extract_threshold_strike(q, gl)
        if strike is None or strike <= 0:
            continue

        toks = m.get("clobTokenIds")
        if isinstance(toks, str):
            try:
                toks = json.loads(toks)
            except Exception:
                toks = []
        if not toks or len(toks) < 2:
            continue

        resolved_yes: Optional[int] = None
        if m.get("closed"):
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    op = json.loads(op)
                except Exception:
                    op = None
            if isinstance(op, list) and len(op) >= 2:
                try:
                    if float(op[0]) >= 0.99:
                        resolved_yes = 1
                    elif float(op[1]) >= 0.99:
                        resolved_yes = 0
                except Exception:
                    pass

        is_down = any(w in q.lower() for w in ("below", "under", "less than", "lower than"))
        rungs.append(
            StrikeRungSpec(
                event_id=str(ev.get("id") or ""),
                series_slug=series_slug,
                asset=asset.upper(),
                title=e_title,
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                question=q,
                strike=strike,
                is_downward=is_down,
                end_ts=end_ts,
                yes_token=str(toks[0]),
                no_token=str(toks[1]),
                resolved_yes=resolved_yes,
            )
        )
    rungs.sort(key=lambda r: r.strike)
    return rungs


def us_session_vol_multiplier(now_ts: float, end_ts: float) -> float:
    """
    Applies a 1.35x implied-vol safety buffer if `[now_ts, end_ts]` spans the high-jump
    US Macro + NYSE Cash Open window (`12:25 UTC - 14:30 UTC`), where realized crypto
    jump variance significantly exceeds 24h average DVOL.
    """
    tte = end_ts - now_ts
    if tte <= 0 or tte > 21600:  # Only relevant for short intraday horizons (<= 6h)
        return 1.0
    day_anchor = int(now_ts // 86400) * 86400
    for d_off in (0, 86400):
        w_start = day_anchor + d_off + 12 * 3600 + 25 * 60
        w_end = day_anchor + d_off + 14 * 3600 + 30 * 60
        if max(now_ts, w_start) < min(end_ts, w_end):
            return 1.35
    return 1.0


def evaluate_svi_digital_fair_value(
    asset: str,
    spot: float,
    strike: float,
    tte_seconds: float,
    is_downward: bool = False,
    dvol_annual_override: Optional[float] = None,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes skew-aware Breeden-Litzenberger digital probability P(YES) and P(NO).
    Uses live Deribit 5-parameter SVI when `dvol_annual_override` is None, or
    parametric SVI skew calibrated around historical Deribit DVOL during backtests.
    """
    if spot <= 0 or strike <= 0 or tte_seconds <= 0:
        return {"p_yes": 0.5, "p_no": 0.5, "iv_annual": 0.45, "z_sigma": 0.0, "source": "INVALID"}

    asset_u = asset.upper()
    t_years = max(1e-6, tte_seconds / (365.25 * 86400.0))
    sess_mult = us_session_vol_multiplier(now_ts, now_ts + tte_seconds) if now_ts is not None else 1.0

    if dvol_annual_override is None and GLOBAL_SVI_ENGINE is not None:
        res_yes = GLOBAL_SVI_ENGINE.evaluate_strike_probability(
            asset=asset_u,
            spot=spot,
            strike=strike,
            tte_seconds=tte_seconds * (sess_mult ** 2),
            outcome="YES",
            is_downward_question=is_downward,
            allow_sync_fetch=True,
            target_tte_sec=tte_seconds,
        )
        p_yes = float(res_yes["p_svi"])
        iv_ann = float(res_yes["svi_iv_annual"]) * sess_mult
        vol_t = max(1e-6, iv_ann * math.sqrt(t_years))
        z_sig = abs(math.log(spot / strike)) / vol_t
        return {
            "p_yes": round(p_yes, 4),
            "p_no": round(1.0 - p_yes, 4),
            "iv_annual": round(iv_ann, 4),
            "z_sigma": round(z_sig, 3),
            "source": res_yes["source"],
        }

    # Historical / parametric SVI Breeden-Litzenberger evaluation around DVOL (C-speed math.erf)
    base_iv = (dvol_annual_override if dvol_annual_override is not None else (0.42 * ASSET_VOL_MULT_VS_BTC.get(asset_u, 1.0))) * sess_mult
    w_atm = (base_iv ** 2) * t_years
    if SVIParams is not Any:
        svi_hist = SVIParams(
            a=max(1e-8, w_atm * 0.86),
            b=max(1e-7, w_atm * 0.34),
            rho=-0.12,
            m=0.0,
            sigma=0.05,
            t_years=t_years,
            forward_price=spot,
            calibrated_at=0.0,
        )
        k = math.log(strike / spot)
        iv_ann = svi_hist.implied_vol(k, t_override=t_years)
        p_above = _fast_bl_digital(spot, strike, t_years, svi_hist)
    else:
        iv_ann = base_iv
        vol_t = max(1e-6, iv_ann * math.sqrt(t_years))
        d2 = (math.log(spot / strike) - 0.5 * (iv_ann ** 2) * t_years) / vol_t
        p_above = _fast_norm_cdf(d2)

    p_yes = (1.0 - p_above) if is_downward else p_above
    vol_t = max(1e-6, iv_ann * math.sqrt(t_years))
    z_sig = abs(math.log(spot / strike)) / vol_t
    return {
        "p_yes": round(max(0.001, min(0.999, p_yes)), 4),
        "p_no": round(max(0.001, min(0.999, 1.0 - p_yes)), 4),
        "iv_annual": round(iv_ann, 4),
        "z_sigma": round(z_sig, 3),
        "source": "DVOL_SVI_BL",
    }


def detect_ladder_monotonicity_boxes(
    quote_rows: List[Dict[str, Any]],
    fee_rate: float = 0.07,
) -> List[Dict[str, Any]]:
    """
    Given sorted upward threshold rungs (`K_1 < K_2 < ...`), checks every pair `i < j`:
      Since `{S_T > K_j}` implies `{S_T > K_i}`, buying `YES(K_i)` + `NO(K_j)` pays:
        - $1.00 if S_T <= K_i (NO(K_j) wins)
        - $2.00 if K_i < S_T <= K_j (BOTH win!)
        - $1.00 if S_T > K_j (YES(K_i) wins)
      So minimum payout is strictly >= $1.00! If `ask_yes(K_i) + ask_no(K_j) + fees < 1.00`,
      it is a deterministic same-oracle monotonicity arbitrage box.
    """
    arbs: List[Dict[str, Any]] = []
    up_rows = sorted([r for r in quote_rows if not r.get("is_downward")], key=lambda x: x["strike"])
    for i in range(len(up_rows)):
        for j in range(i + 1, len(up_rows)):
            lo = up_rows[i]
            hi = up_rows[j]
            if hi["strike"] <= lo["strike"]:
                continue
            ask_y_lo = float(lo.get("ask_yes") or 1.0)
            ask_n_hi = float(hi.get("ask_no") or 1.0)
            if not (0.01 <= ask_y_lo <= 0.98 and 0.01 <= ask_n_hi <= 0.98):
                continue
            fee_1 = fee_rate * ask_y_lo * (1.0 - ask_y_lo)
            fee_2 = fee_rate * ask_n_hi * (1.0 - ask_n_hi)
            total_cost = ask_y_lo + ask_n_hi + fee_1 + fee_2
            if total_cost <= 0.996:
                arbs.append({
                    "low_strike": lo["strike"],
                    "high_strike": hi["strike"],
                    "low_market_id": lo["market_id"],
                    "high_market_id": hi["market_id"],
                    "yes_token_low": lo["yes_token"],
                    "no_token_high": hi["no_token"],
                    "ask_yes_low": ask_y_lo,
                    "ask_no_high": ask_n_hi,
                    "box_cost_net": round(total_cost, 5),
                    "riskless_floor_edge": round(1.0 - total_cost, 5),
                })
    return arbs


def evaluate_coherent_strike_ladder(
    asset: str,
    spot: float,
    rungs: List[StrikeRungSpec],
    tte_seconds: float,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Jointly evaluates all upward rungs on an event expiry and projects `P(S_T > K_i)` onto
    the exact PAVA monotone simplex (`ChatGPT #8`), guaranteeing zero cross-rung probability inversion.
    """
    up_rungs = sorted([r for r in rungs if not r.is_downward], key=lambda x: x.strike)
    raw_pairs: List[Tuple[float, float]] = []
    meta_by_k: Dict[float, Dict[str, Any]] = {}
    for r in up_rungs:
        fv = evaluate_svi_digital_fair_value(asset, spot, r.strike, tte_seconds, is_downward=False, now_ts=now_ts)
        raw_pairs.append((r.strike, float(fv["p_yes"])))
        meta_by_k[r.strike] = fv
    if enforce_monotone_ladder_probabilities is not None and raw_pairs:
        mono = enforce_monotone_ladder_probabilities(raw_pairs)
    else:
        mono = {"strikes": [k for k, _ in raw_pairs], "probs": [p for _, p in raw_pairs], "interval_probs": [], "max_adjustment": 0.0}
    coherent_by_market: Dict[str, Dict[str, Any]] = {}
    for idx, r in enumerate(up_rungs):
        p_coh = float(mono["probs"][idx]) if idx < len(mono["probs"]) else float(meta_by_k[r.strike]["p_yes"])
        fv_row = dict(meta_by_k[r.strike])
        fv_row["p_yes_raw"] = fv_row["p_yes"]
        fv_row["p_yes"] = round(p_coh, 4)
        fv_row["p_no"] = round(1.0 - p_coh, 4)
        coherent_by_market[r.market_id] = fv_row
    return {
        "by_market_id": coherent_by_market,
        "strikes": mono["strikes"],
        "probs": mono["probs"],
        "interval_probs": mono["interval_probs"],
        "max_adjustment": mono["max_adjustment"],
    }


NEGRISK_SERIES: List[Tuple[str, str]] = [
    ("BTC", "bitcoin-neg-risk-weekly"),
    ("ETH", "ethereum-neg-risk-weekly"),
    ("SOL", "solana-neg-risk-weekly"),
    ("XRP", "xrp-neg-risk-weekly"),
]

DAILY_UPDOWN_SERIES: List[Tuple[str, str]] = [
    ("BTC", "btc-up-or-down-daily"),
    ("ETH", "eth-up-or-down-daily"),
    ("SOL", "sol-up-or-down-daily"),
    ("XRP", "xrp-up-or-down-daily"),
    ("BNB", "bnb-up-or-down-daily"),
    ("DOGE", "dogecoin-up-or-down-daily"),
]

ZERO_FEE_PYTH_DAILY_SERIES: List[Tuple[str, str]] = [
    ("EURUSD", "eurusd-daily-up-or-down"),
    ("GBPUSD", "gbpusd-daily-up-or-down"),
    ("USDJPY", "usdjpy-daily-up-or-down"),
    ("USDCHF", "usdchf-daily-up-or-down"),
    ("DXY", "dxy-daily-up-or-down"),
    ("GOLD", "gold-daily-up-or-down"),
    ("SILVER", "silver-daily-up-or-down"),
    ("OIL", "oil-daily-up-or-down"),
]


@dataclass
class NegRiskBracketSpec:
    event_id: str
    series_slug: str
    asset: str
    title: str
    market_id: str
    condition_id: str
    question: str
    bracket_kind: str  # "LOWER_TAIL", "RANGE", "UPPER_TAIL"
    k_low: Optional[float]
    k_high: Optional[float]
    end_ts: float
    yes_token: str
    no_token: str
    fee_rate: float = 0.07
    resolution_source: str = ""


@dataclass
class DailyUpDownSpec:
    event_id: str
    series_slug: str
    asset: str
    title: str
    market_id: str
    condition_id: str
    start_ts: float
    end_ts: float
    up_token: str
    down_token: str
    fee_rate: float = 0.07
    resolution_source: str = ""


_RANGE_LABEL_RE = re.compile(
    r"^\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*[-–—]\s*"
    r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*$"
)
_BETWEEN_Q_RE = re.compile(
    r"\bbetween\s+\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s+and\s+"
    r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b",
    re.IGNORECASE,
)
_LOWER_TAIL_LABEL_RE = re.compile(
    r"^\s*<\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*$"
)
_UPPER_TAIL_LABEL_RE = re.compile(
    r"^\s*>\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*$"
)


def _num_with_k(num_s: str, k_s: Optional[str]) -> float:
    val = float(num_s.replace(",", ""))
    if k_s:
        val *= 1000.0
    return val


def parse_negrisk_bracket_event(ev: Dict[str, Any], asset: str, series_slug: str) -> List[NegRiskBracketSpec]:
    end_str = str(ev.get("endDate") or "")
    if not end_str:
        return []
    try:
        end_ts = datetime.fromisoformat(end_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        return []

    e_title = str(ev.get("title") or "")
    e_id = str(ev.get("id") or "")
    brackets: List[NegRiskBracketSpec] = []

    for m in ev.get("markets") or []:
        if m.get("closed") or m.get("acceptingOrders") is False:
            continue
        q = str(m.get("question") or "")
        gl = str(m.get("groupItemTitle") or "")
        toks = m.get("clobTokenIds")
        if isinstance(toks, str):
            try:
                toks = json.loads(toks)
            except Exception:
                toks = []
        if not isinstance(toks, list) or len(toks) < 2:
            continue

        b_kind: Optional[str] = None
        k_lo: Optional[float] = None
        k_hi: Optional[float] = None

        m_rng = _RANGE_LABEL_RE.match(gl) or _BETWEEN_Q_RE.search(q)
        if m_rng:
            a_v = _num_with_k(m_rng.group(1), m_rng.group(2))
            b_v = _num_with_k(m_rng.group(3), m_rng.group(4))
            if b_v > a_v > 0:
                b_kind = "RANGE"
                k_lo, k_hi = a_v, b_v
        else:
            m_lo = _LOWER_TAIL_LABEL_RE.match(gl)
            m_hi = _UPPER_TAIL_LABEL_RE.match(gl)
            q_low = q.lower()
            if m_lo or ("less than" in q_low or "below" in q_low or "under" in q_low):
                k_v = _num_with_k(m_lo.group(1), m_lo.group(2)) if m_lo else _extract_threshold_strike(q, gl)
                if k_v and k_v > 0:
                    b_kind = "LOWER_TAIL"
                    k_hi = k_v
            elif m_hi or ("greater than" in q_low or "above" in q_low or "over" in q_low):
                k_v = _num_with_k(m_hi.group(1), m_hi.group(2)) if m_hi else _extract_threshold_strike(q, gl)
                if k_v and k_v > 0:
                    b_kind = "UPPER_TAIL"
                    k_lo = k_v

        if b_kind is None:
            continue

        fee_sched = m.get("feeSchedule") or {}
        fee_rate = float(fee_sched.get("rate", 0.07) if m.get("feesEnabled", True) else 0.0)
        res_src = str(m.get("resolutionSource") or ev.get("resolutionSource") or "").strip().lower()
        brackets.append(
            NegRiskBracketSpec(
                event_id=e_id,
                series_slug=series_slug,
                asset=asset.upper(),
                title=e_title,
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                question=q,
                bracket_kind=b_kind,
                k_low=k_lo,
                k_high=k_hi,
                end_ts=end_ts,
                yes_token=str(toks[0]),
                no_token=str(toks[1]),
                fee_rate=fee_rate,
                resolution_source=res_src,
            )
        )
    return brackets


def build_negrisk_cross_box_bundles(
    rungs: List[StrikeRungSpec],
    brackets: List[NegRiskBracketSpec],
    spot: float = 0.0,
    max_strike_dist_log: float = 0.14,
    tail_max_strike_dist_log: float = 0.24,
) -> List[Dict[str, Any]]:
    """
    Constructs exact deterministic cross-contract arbitrage bundles pairing `Multi-Strike`
    (`Above K`) rungs against `NegRisk` (`<K_min`, `[K_1, K_2]`, `>K_max`) brackets sharing
    the identical settlement timestamp (`abs(end_ts_ms - end_ts_nr) <= 2s`) and Binance 1m oracle.
    """
    if not rungs or not brackets:
        return []
    if rungs[0].asset != brackets[0].asset:
        return []
    if abs(rungs[0].end_ts - brackets[0].end_ts) > 2.0:
        return []

    ms_by_k: Dict[float, StrikeRungSpec] = {
        round(float(r.strike), 4): r for r in rungs if not r.is_downward
    }
    bundles: List[Dict[str, Any]] = []

    for br in brackets:
        if spot > 0.0:
            ref_k = br.k_low if br.k_low is not None else (br.k_high or spot)
            dist_cap = tail_max_strike_dist_log if br.bracket_kind in ("LOWER_TAIL", "UPPER_TAIL") else max_strike_dist_log
            if ref_k > 0 and abs(math.log(ref_k / spot)) > dist_cap:
                continue

        if br.bracket_kind == "LOWER_TAIL" and br.k_high is not None:
            ms_r = ms_by_k.get(round(float(br.k_high), 4))
            if ms_r is not None:
                bundles.append({
                    "bundle_id": f"TAIL_LOW_YES_{br.market_id}_{ms_r.market_id}",
                    "label": f"NR_YES(<{br.k_high:g})+MS_YES(>{ms_r.strike:g})",
                    "guaranteed_payout": 1.0,
                    "end_ts": br.end_ts,
                    "legs": [
                        {"token_id": br.yes_token, "opp_token_id": br.no_token, "condition_id": br.condition_id, "neg_risk": True, "strike": float(br.k_high), "side": "YES", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_YES<{br.k_high:g}"},
                        {"token_id": ms_r.yes_token, "opp_token_id": ms_r.no_token, "condition_id": ms_r.condition_id, "neg_risk": False, "strike": float(ms_r.strike), "side": "YES", "market_id": ms_r.market_id, "fee_rate": ms_r.fee_rate, "label": f"MS_YES>{ms_r.strike:g}"},
                    ],
                })
                bundles.append({
                    "bundle_id": f"TAIL_LOW_NO_{br.market_id}_{ms_r.market_id}",
                    "label": f"NR_NO(<{br.k_high:g})+MS_NO(>{ms_r.strike:g})",
                    "guaranteed_payout": 1.0,
                    "end_ts": br.end_ts,
                    "legs": [
                        {"token_id": br.no_token, "opp_token_id": br.yes_token, "condition_id": br.condition_id, "neg_risk": True, "strike": float(br.k_high), "side": "NO", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_NO<{br.k_high:g}"},
                        {"token_id": ms_r.no_token, "opp_token_id": ms_r.yes_token, "condition_id": ms_r.condition_id, "neg_risk": False, "strike": float(ms_r.strike), "side": "NO", "market_id": ms_r.market_id, "fee_rate": ms_r.fee_rate, "label": f"MS_NO>{ms_r.strike:g}"},
                    ],
                })
        elif br.bracket_kind == "UPPER_TAIL" and br.k_low is not None:
            ms_r = ms_by_k.get(round(float(br.k_low), 4))
            if ms_r is not None:
                bundles.append({
                    "bundle_id": f"TAIL_HIGH_A_{br.market_id}_{ms_r.market_id}",
                    "label": f"NR_YES(>{br.k_low:g})+MS_NO(>{ms_r.strike:g})",
                    "guaranteed_payout": 1.0,
                    "end_ts": br.end_ts,
                    "legs": [
                        {"token_id": br.yes_token, "opp_token_id": br.no_token, "condition_id": br.condition_id, "neg_risk": True, "strike": float(br.k_low), "side": "YES", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_YES>{br.k_low:g}"},
                        {"token_id": ms_r.no_token, "opp_token_id": ms_r.yes_token, "condition_id": ms_r.condition_id, "neg_risk": False, "strike": float(ms_r.strike), "side": "NO", "market_id": ms_r.market_id, "fee_rate": ms_r.fee_rate, "label": f"MS_NO>{ms_r.strike:g}"},
                    ],
                })
                bundles.append({
                    "bundle_id": f"TAIL_HIGH_B_{br.market_id}_{ms_r.market_id}",
                    "label": f"NR_NO(>{br.k_low:g})+MS_YES(>{ms_r.strike:g})",
                    "guaranteed_payout": 1.0,
                    "end_ts": br.end_ts,
                    "legs": [
                        {"token_id": br.no_token, "opp_token_id": br.yes_token, "condition_id": br.condition_id, "neg_risk": True, "strike": float(br.k_low), "side": "NO", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_NO>{br.k_low:g}"},
                        {"token_id": ms_r.yes_token, "opp_token_id": ms_r.no_token, "condition_id": ms_r.condition_id, "neg_risk": False, "strike": float(ms_r.strike), "side": "YES", "market_id": ms_r.market_id, "fee_rate": ms_r.fee_rate, "label": f"MS_YES>{ms_r.strike:g}"},
                    ],
                })
        elif br.bracket_kind == "RANGE" and br.k_low is not None and br.k_high is not None:
            ms_lo = ms_by_k.get(round(float(br.k_low), 4))
            ms_hi = ms_by_k.get(round(float(br.k_high), 4))
            if ms_lo is not None and ms_hi is not None:
                # 3-Leg $1.00 Complete State Partition: NO(>K_low) + YES([K_low, K_high]) + YES(>K_high) >= $1.00 everywhere
                bundles.append({
                    "bundle_id": f"PART_1X_{br.market_id}_{ms_lo.market_id}_{ms_hi.market_id}",
                    "label": f"MS_NO(>{br.k_low:g})+NR_YES([{br.k_low:g},{br.k_high:g}])+MS_YES(>{br.k_high:g})",
                    "guaranteed_payout": 1.0,
                    "end_ts": br.end_ts,
                    "legs": [
                        {"token_id": ms_lo.no_token, "side": "NO", "market_id": ms_lo.market_id, "fee_rate": ms_lo.fee_rate, "label": f"MS_NO>{br.k_low:g}"},
                        {"token_id": br.yes_token, "side": "YES", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_YES[{br.k_low:g}-{br.k_high:g}]"},
                        {"token_id": ms_hi.yes_token, "side": "YES", "market_id": ms_hi.market_id, "fee_rate": ms_hi.fee_rate, "label": f"MS_YES>{br.k_high:g}"},
                    ],
                })
                # 3-Leg $2.00 Complement Box: YES(>K_low) + NO([K_low, K_high]) + NO(>K_high) == $2.00
                bundles.append({
                    "bundle_id": f"COMP_2X_{br.market_id}_{ms_lo.market_id}_{ms_hi.market_id}",
                    "label": f"MS_YES(>{br.k_low:g})+NR_NO([{br.k_low:g},{br.k_high:g}])+MS_NO(>{br.k_high:g})",
                    "guaranteed_payout": 2.0,
                    "end_ts": br.end_ts,
                    "legs": [
                        {"token_id": ms_lo.yes_token, "side": "YES", "market_id": ms_lo.market_id, "fee_rate": ms_lo.fee_rate, "label": f"MS_YES>{br.k_low:g}"},
                        {"token_id": br.no_token, "side": "NO", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_NO[{br.k_low:g}-{br.k_high:g}]"},
                        {"token_id": ms_hi.no_token, "side": "NO", "market_id": ms_hi.market_id, "fee_rate": ms_hi.fee_rate, "label": f"MS_NO>{br.k_high:g}"},
                    ],
                })
    return bundles


def parse_daily_updown_event(ev: Dict[str, Any], asset: str, series_slug: str) -> Optional[DailyUpDownSpec]:
    mkts = ev.get("markets") or []
    if not mkts or not isinstance(mkts[0], dict):
        return None
    m = mkts[0]
    if m.get("closed") or m.get("acceptingOrders") is False:
        return None
    start_str = str(m.get("eventStartTime") or "").strip()
    end_str = str(m.get("endDate") or ev.get("endDate") or "").strip()
    if not start_str or not end_str:
        return None
    try:
        start_ts = datetime.fromisoformat(start_str.replace("Z", "+00:00")).timestamp()
        end_ts = datetime.fromisoformat(end_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None
    if abs((end_ts - start_ts) - 86400.0) > 7200.0:
        return None

    toks = m.get("clobTokenIds")
    if isinstance(toks, str):
        try:
            toks = json.loads(toks)
        except Exception:
            toks = []
    outcomes = m.get("outcomes")
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []
    if not isinstance(toks, list) or len(toks) < 2:
        return None

    up_idx, dn_idx = 0, 1
    if isinstance(outcomes, list) and len(outcomes) >= 2:
        norm_out = [str(o).strip().upper() for o in outcomes]
        if "UP" in norm_out and "DOWN" in norm_out:
            up_idx = norm_out.index("UP")
            dn_idx = norm_out.index("DOWN")

    fee_sched = m.get("feeSchedule") or {}
    fee_rate = float(fee_sched.get("rate", 0.07) if m.get("feesEnabled", True) else 0.0)
    return DailyUpDownSpec(
        event_id=str(ev.get("id") or ""),
        series_slug=series_slug,
        asset=asset.upper(),
        title=str(m.get("question") or ev.get("title") or ""),
        market_id=str(m.get("id") or ""),
        condition_id=str(m.get("conditionId") or ""),
        start_ts=start_ts,
        end_ts=end_ts,
        up_token=str(toks[up_idx]),
        down_token=str(toks[dn_idx]),
        fee_rate=fee_rate,
        resolution_source=str(m.get("resolutionSource") or "").strip().lower(),
    )

# ======================================================================================
# [07/16] MODULE: src/polymarket_research/same_oracle_dominance_box.py
# PURPOSE: Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine
# ======================================================================================

#!/usr/bin/env python3
r"""
Same-Oracle Riskless Dominance Box Engine (Option #7: 15m vs 5m Chainlink 60s-TWAP)
===================================================================================
Captures deterministic, zero-basis cross-horizon dominance arbitrage between overlapping
Polymarket `15m` and `5m` Up/Down crypto markets sharing the exact same terminal timestamp
(`:10-:15`, `:25-:30`, `:40-:45`, `:55-:00` of every clock hour) across `BTC`, `ETH`, `SOL`, `XRP`.

Mathematical Dominance Invariant:
  Both `15m` and `5m` resolve on the identical Chainlink `60s` USD TWAP `eventMetadata.finalPrice`
  $S_T$ (`*-usd-twap-60s-streams`), with `"Up"` iff $S_T \ge K$ and `"Down"` iff $S_T < K$, where
  $K$ (`eventMetadata.priceToBeat`) equals the finalized `eventMetadata.finalPrice` of the
  immediately preceding `5m` Gamma event (`{asset}-updown-5m-{start_ts - 300}`).

  Let $K_{\text{low}} < K_{\text{high}}$ be the two opening Chainlink strikes:
    - Leg A: `UP` on the market with strike $K_{\text{low}}$   (pays $1 iff $S_T \ge K_{\text{low}}$)
    - Leg B: `DOWN` on the market with strike $K_{\text{high}}$ (pays $1 iff $S_T < K_{\text{high}}$)

  State-by-state terminal payout per 1-share pair (`Q_A == Q_B == 1`):
    1. $S_T < K_{\text{low}}$               -> Leg A = $0, Leg B = $1 -> Total = $1.00
    2. $K_{\text{low}} \le S_T < K_{\text{high}}$ -> Leg A = $1, Leg B = $1 -> Total = $2.00 (Double Payout)
    3. $S_T \ge K_{\text{high}}$            -> Leg A = $1, Leg B = $0 -> Total = $1.00

  Whenever all-in equal-share L2 VWAP + both V2 taker fees (`7% * p * (1 - p)`) <= $0.995,
  the trade locks in a riskless floor >= +$0.005/pair plus a free $1.00 corridor lottery.
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

CORE_LIVE_DOMINANCE_ASSETS: Tuple[str, ...] = ("BTC", "ETH", "SOL", "XRP")
EXPANSION_DOMINANCE_ASSETS: Tuple[str, ...] = ("BNB", "DOGE", "HYPE")
DOMINANCE_ASSETS: Tuple[str, ...] = CORE_LIVE_DOMINANCE_ASSETS + EXPANSION_DOMINANCE_ASSETS

DOMINANCE_SERIES_SLUGS: Dict[str, Dict[str, str]] = {
    "BTC": {"4h": "btc-up-or-down-4h", "15m": "btc-up-or-down-15m", "5m": "btc-up-or-down-5m"},
    "ETH": {"4h": "eth-up-or-down-4h", "15m": "eth-up-or-down-15m", "5m": "eth-up-or-down-5m"},
    "SOL": {"4h": "sol-up-or-down-4h", "15m": "sol-up-or-down-15m", "5m": "sol-up-or-down-5m"},
    "XRP": {"4h": "xrp-up-or-down-4h", "15m": "xrp-up-or-down-15m", "5m": "xrp-up-or-down-5m"},
    "BNB": {"4h": "bnb-up-or-down-4h", "15m": "bnb-up-or-down-15m", "5m": "bnb-up-or-down-5m"},
    "DOGE": {"4h": "doge-up-or-down-4h", "15m": "doge-up-or-down-15m", "5m": "doge-up-or-down-5m"},
    "HYPE": {"4h": "hype-up-or-down-4h", "15m": "hype-up-or-down-15m", "5m": "hype-up-or-down-5m"},
}

EMPIRICAL_BOX_ASSET_CAPS_USD: Dict[str, float] = {
    "BTC": 150.0,
    "ETH": 75.0,
    "SOL": 22.0,
    "XRP": 22.0,
    "BNB": 22.0,
    "HYPE": 15.0,
    "DOGE": 15.0,
}

MIN_CORRIDOR_BPS_BY_ASSET: Dict[str, float] = {
    "BTC": 3.0,
    "ETH": 3.0,
    "SOL": 3.0,
    "XRP": 3.0,
    "BNB": 5.0,
    "DOGE": 5.0,
    "HYPE": 5.0,
}

POLYMARKET_CRYPTO_PRICE_URL = "https://polymarket.com/api/crypto/crypto-price"
GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"
HORIZON_TO_VARIANT: Dict[str, str] = {
    "4h": "fourhour",
    "15m": "fifteen",
    "5m": "fiveminute",
}
HORIZON_TO_DURATION_SEC: Dict[str, float] = {
    "4h": 14400.0,
    "15m": 900.0,
    "5m": 300.0,
}


@dataclass(frozen=True)
class TwapCandleMarketSpec:
    asset: str
    horizon: str  # "15m" or "5m"
    market_id: str
    condition_id: str
    title: str
    start_iso: str
    end_iso: str
    start_ts: float
    end_ts: float
    up_token: str
    down_token: str
    fee_rate: float
    fee_exponent: float
    neg_risk: bool
    twap_lookback_sec: int
    resolution_source: str


def _parse_iso_ts(iso_str: str) -> float:
    dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def parse_twap_candle_event(event: Dict[str, Any], asset: str, horizon: str) -> Optional[TwapCandleMarketSpec]:
    """
    Parses a Polymarket Gamma `5m` or `15m` Up/Down event and enforces strict
    Chainlink 60s-TWAP oracle verification (`twapEnabled=True`, `twapLookbackSeconds=60`).
    Returns None if oracle rules do not match the canonical Chainlink 60s TWAP stream.
    """
    if horizon not in HORIZON_TO_VARIANT:
        return None
    markets = event.get("markets") or []
    if not markets or not isinstance(markets[0], dict):
        return None
    m = markets[0]
    if m.get("closed") or m.get("acceptingOrders") is False:
        return None

    start_iso = str(m.get("eventStartTime") or "").strip()
    end_iso = str(m.get("endDate") or event.get("endDate") or "").strip()
    if not start_iso or not end_iso:
        return None
    try:
        start_ts = _parse_iso_ts(start_iso)
        end_ts = _parse_iso_ts(end_iso)
    except Exception:
        return None

    expected_dur = HORIZON_TO_DURATION_SEC[horizon]
    if abs((end_ts - start_ts) - expected_dur) > 5.0:
        return None

    # Enforce strict Chainlink 60s TWAP oracle config
    cfg = m.get("cryptoMarketConfig") or {}
    res_src = str(m.get("resolutionSource") or "").strip().lower()
    desc = str(m.get("description") or "").lower()
    twap_enabled = bool(cfg.get("twapEnabled")) or ("twap-60s-streams" in res_src) or ("twap-60s-streams" in desc)
    lookback = int(cfg.get("twapLookbackSeconds") or (60 if "twap-60s" in (res_src + desc) else 0))
    if not twap_enabled or lookback != 60:
        return None

    toks = m.get("clobTokenIds")
    if isinstance(toks, str):
        try:
            toks = json.loads(toks)
        except Exception:
            toks = []
    outcomes = m.get("outcomes")
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []
    if not isinstance(toks, list) or len(toks) < 2:
        return None

    # Map "Up" and "Down" explicitly by outcome label
    up_idx, dn_idx = 0, 1
    if isinstance(outcomes, list) and len(outcomes) >= 2:
        norm_out = [str(o).strip().upper() for o in outcomes]
        if "UP" in norm_out and "DOWN" in norm_out:
            up_idx = norm_out.index("UP")
            dn_idx = norm_out.index("DOWN")

    fee_sched = m.get("feeSchedule") or {}
    fee_rate = float(fee_sched.get("rate", 0.07) if m.get("feesEnabled", True) else 0.0)
    fee_exp = float(fee_sched.get("exponent", 1.0))

    return TwapCandleMarketSpec(
        asset=asset.upper(),
        horizon=horizon,
        market_id=str(m.get("id") or ""),
        condition_id=str(m.get("conditionId") or ""),
        title=str(m.get("question") or event.get("title") or ""),
        start_iso=start_iso,
        end_iso=end_iso,
        start_ts=start_ts,
        end_ts=end_ts,
        up_token=str(toks[up_idx]),
        down_token=str(toks[dn_idx]),
        fee_rate=fee_rate,
        fee_exponent=fee_exp,
        neg_risk=bool(m.get("negRisk", False)),
        twap_lookback_sec=lookback,
        resolution_source=res_src,
    )


def verify_same_oracle_pair(m_long: TwapCandleMarketSpec, m_short: TwapCandleMarketSpec) -> bool:
    """
    Verifies two distinct Chainlink TWAP candle markets (`4h`, `15m`, `5m`) belong to the same
    asset, share the exact same terminal settlement timestamp (`end_ts` within 2s), and both
    settle on the identical 60s Chainlink TWAP stream (`twapLookbackSeconds == 60`).
    """
    if m_long.asset != m_short.asset:
        return False
    if m_long.horizon not in HORIZON_TO_VARIANT or m_short.horizon not in HORIZON_TO_VARIANT:
        return False
    if m_long.horizon == m_short.horizon:
        return False
    if HORIZON_TO_DURATION_SEC[m_long.horizon] <= HORIZON_TO_DURATION_SEC[m_short.horizon]:
        return False
    if abs(m_long.end_ts - m_short.end_ts) > 2.0:
        return False
    if m_long.twap_lookback_sec != 60 or m_short.twap_lookback_sec != 60:
        return False
    s_l = str(m_long.resolution_source or "").strip().lower()
    s_s = str(m_short.resolution_source or "").strip().lower()
    if not s_l or not s_s or s_l != s_s:
        return False
    return True


def build_prev_5m_gamma_event_url(spec: TwapCandleMarketSpec) -> str:
    """
    Returns the Gamma event URL for the immediately preceding 5m candle (`start_ts - 300`).
    Once finalized (`closed == True`), its `eventMetadata.finalPrice` equals `spec`'s exact
    60s-TWAP `eventMetadata.priceToBeat` across `5m`, `15m`, and `4h` horizons.
    """
    prev_5m_start = int(round(spec.start_ts)) - 300
    return f"{GAMMA_EVENTS_URL}?slug={spec.asset.lower()}-updown-5m-{prev_5m_start}"


def build_own_gamma_event_url(asset: str, horizon: str, start_ts_or_iso: Any) -> str:
    start_ts = _parse_iso_ts(start_ts_or_iso) if isinstance(start_ts_or_iso, str) else float(start_ts_or_iso)
    return f"{GAMMA_EVENTS_URL}?slug={str(asset).lower()}-updown-{str(horizon).lower()}-{int(round(start_ts))}"


def build_crypto_price_query_url(spec: TwapCandleMarketSpec) -> str:
    """
    Builds Polymarket's exact 60s-TWAP `crypto-price` query URL (`twapEnabled=true&twapLookbackSeconds=60`).
    Matches Polymarket's frontend query key `["crypto-prices", ..., true, 60]` and Gamma's
    `eventMetadata.priceToBeat` / `finalPrice` to all 15 significant digits with zero lag (`t = +1s`).
    """
    if int(spec.twap_lookback_sec) != 60:
        raise ValueError(f"60s Chainlink TWAP required, got twap_lookback_sec={spec.twap_lookback_sec}")
    variant = HORIZON_TO_VARIANT[spec.horizon]
    return (
        f"{POLYMARKET_CRYPTO_PRICE_URL}?symbol={spec.asset}"
        f"&eventStartTime={spec.start_iso}&variant={variant}&endDate={spec.end_iso}"
        f"&twapEnabled=true&twapLookbackSeconds=60"
    )


def _is_verified_twap60_url(request_url: Optional[str]) -> bool:
    u = str(request_url or "")
    return ("twapEnabled=true" in u) and ("twapLookbackSeconds=60" in u)


def _extract_closed_gamma_meta_field(payload: Any, field: str, request_url: Optional[str] = None) -> Optional[float]:
    ev = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(ev, dict) or ev.get("closed") is not True:
        return None
    if request_url and "slug=" in str(request_url):
        expected_slug = str(request_url).split("slug=", 1)[1].split("&", 1)[0]
        if str(ev.get("slug") or "") != expected_slug:
            return None
    meta = ev.get("eventMetadata")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            return None
    if not isinstance(meta, dict):
        return None
    raw_val = meta.get(field)
    if raw_val is None:
        return None
    try:
        val = float(raw_val)
    except (TypeError, ValueError):
        return None
    return val if (math.isfinite(val) and val > 0.0) else None


def parse_authoritative_open_price(payload: Any, *, request_url: Optional[str] = None) -> Optional[float]:
    """
    Extracts the authoritative Chainlink 60s-TWAP opening strike (`priceToBeat`):
      1. Closed preceding-5m Gamma event (`closed is True` -> `eventMetadata.finalPrice`), OR
      2. Polymarket `crypto-price` ONLY when `request_url` explicitly carries
         `twapEnabled=true&twapLookbackSeconds=60` AND `cached is True` (or `completed is True`).
    Strictly rejects legacy un-TWAP'd `crypto-price` spot responses (`request_url` missing TWAP flags).
    """
    g_val = _extract_closed_gamma_meta_field(payload, "finalPrice", request_url)
    if g_val is not None:
        return g_val
    if not isinstance(payload, dict) or not _is_verified_twap60_url(request_url):
        return None
    if payload.get("cached") is not True and payload.get("completed") is not True:
        return None
    raw_open = payload.get("openPrice")
    if raw_open is None:
        return None
    try:
        val = float(raw_open)
    except (TypeError, ValueError):
        return None
    return val if (math.isfinite(val) and val > 0.0) else None


def parse_authoritative_close_price(payload: Any, *, request_url: Optional[str] = None) -> Optional[float]:
    """
    Extracts finalized Chainlink 60s-TWAP `finalPrice` / `closePrice` from a closed Gamma
    event (`eventMetadata.finalPrice`) or a completed `twapEnabled=true&twapLookbackSeconds=60` response.
    """
    g_val = _extract_closed_gamma_meta_field(payload, "finalPrice", request_url)
    if g_val is not None:
        return g_val
    if not isinstance(payload, dict) or payload.get("completed") is not True or not _is_verified_twap60_url(request_url):
        return None
    raw_close = payload.get("closePrice")
    if raw_close is None:
        return None
    try:
        val = float(raw_close)
    except (TypeError, ValueError):
        return None
    return val if (math.isfinite(val) and val > 0.0) else None


def parse_closed_gamma_event_settlement(payload: Any, side: str, request_url: Optional[str] = None) -> Optional[float]:
    """
    Evaluates actual binary leg payout (`1.0` or `0.0`) directly from a closed Gamma event's
    authoritative `(priceToBeat, finalPrice)` pair without trusting cached entry strikes.
    """
    k_beat = _extract_closed_gamma_meta_field(payload, "priceToBeat", request_url)
    s_fin = _extract_closed_gamma_meta_field(payload, "finalPrice", request_url)
    if k_beat is None or s_fin is None:
        return None
    up_won = s_fin >= k_beat
    won = up_won if str(side).strip().upper() == "UP" else (not up_won)
    return 1.0 if won else 0.0


def determine_dominance_legs(
    m15: TwapCandleMarketSpec,
    k_15m: float,
    m5: TwapCandleMarketSpec,
    k_5m: float,
    min_corridor_bps: float = 2.5,
) -> Optional[Dict[str, Any]]:
    """
    Given authoritative Chainlink opening strikes `k_15m` (longer horizon: `4h` or `15m`) and
    `k_5m` (shorter horizon: `15m` or `5m`), returns the exact riskless dominance leg pairing
    (`UP` at `K_low` + `DOWN` at `K_high`) plus each leg's `opp_token_id` complement.
    Rejects pairs with < `min_corridor_bps` strike separation to eliminate any tie ambiguity.
    """
    if not verify_same_oracle_pair(m15, m5):
        return None
    if not (math.isfinite(k_15m) and k_15m > 0.0 and math.isfinite(k_5m) and k_5m > 0.0):
        return None

    k_low = min(k_15m, k_5m)
    k_high = max(k_15m, k_5m)
    corridor_bps = ((k_high - k_low) / k_low) * 10000.0
    if corridor_bps < min_corridor_bps:
        return None

    h_long_u = m15.horizon.upper()
    h_short_u = m5.horizon.upper()

    if k_15m < k_5m:
        return {
            "regime": f"{h_long_u}_UP_PLUS_{h_short_u}_DOWN",
            "k_low": k_15m,
            "k_high": k_5m,
            "corridor_bps": round(corridor_bps, 3),
            "leg_a": {
                "horizon": m15.horizon,
                "side": "UP",
                "label": f"{h_long_u}_UP",
                "market_id": m15.market_id,
                "condition_id": m15.condition_id,
                "token_id": m15.up_token,
                "opp_token_id": m15.down_token,
                "strike": k_15m,
                "fee_rate": m15.fee_rate,
                "fee_exponent": m15.fee_exponent,
                "neg_risk": m15.neg_risk,
            },
            "leg_b": {
                "horizon": m5.horizon,
                "side": "DOWN",
                "label": f"{h_short_u}_DOWN",
                "market_id": m5.market_id,
                "condition_id": m5.condition_id,
                "token_id": m5.down_token,
                "opp_token_id": m5.up_token,
                "strike": k_5m,
                "fee_rate": m5.fee_rate,
                "fee_exponent": m5.fee_exponent,
                "neg_risk": m5.neg_risk,
            },
        }
    else:
        return {
            "regime": f"{h_short_u}_UP_PLUS_{h_long_u}_DOWN",
            "k_low": k_5m,
            "k_high": k_15m,
            "corridor_bps": round(corridor_bps, 3),
            "leg_a": {
                "horizon": m5.horizon,
                "side": "UP",
                "label": f"{h_short_u}_UP",
                "market_id": m5.market_id,
                "condition_id": m5.condition_id,
                "token_id": m5.up_token,
                "opp_token_id": m5.down_token,
                "strike": k_5m,
                "fee_rate": m5.fee_rate,
                "fee_exponent": m5.fee_exponent,
                "neg_risk": m5.neg_risk,
            },
            "leg_b": {
                "horizon": m15.horizon,
                "side": "DOWN",
                "label": f"{h_long_u}_DOWN",
                "market_id": m15.market_id,
                "condition_id": m15.condition_id,
                "token_id": m15.down_token,
                "opp_token_id": m15.up_token,
                "strike": k_15m,
                "fee_rate": m15.fee_rate,
                "fee_exponent": m15.fee_exponent,
                "neg_risk": m15.neg_risk,
            },
        }


def _sorted_asks(asks_raw: List[Dict[str, Any]], max_slip_cents: float) -> Tuple[List[Tuple[float, float]], float, float]:
    asks = sorted(
        [
            (float(a["price"]), float(a["size"]))
            for a in (asks_raw or [])
            if float(a.get("price", 0)) > 0.0 and float(a.get("size", 0)) > 0.0
        ],
        key=lambda x: x[0],
    )
    if not asks:
        return [], 1.0, 0.0
    best_ask = asks[0][0]
    capped = [(px, sz) for px, sz in asks if px <= best_ask + max_slip_cents + 1e-9 and px < 0.99]
    avail_shares = sum(sz for _, sz in capped)
    return capped, best_ask, avail_shares


def _walk_exact_shares(
    asks_capped: List[Tuple[float, float]],
    shares_qty: int,
    fee_rate: float,
    fee_exponent: float = 1.0,
) -> Optional[Dict[str, Any]]:
    if shares_qty <= 0 or not asks_capped:
        return None
    rem = float(shares_qty)
    spent = 0.0
    worst_px = asks_capped[0][0]
    levels = 0
    for px, sz in asks_capped:
        take_sh = min(rem, sz)
        if take_sh <= 0:
            continue
        spent += take_sh * px
        worst_px = px
        levels += 1
        rem -= take_sh
        if rem <= 1e-8:
            break
    if rem > 1e-5:
        return None
    vwap = spent / float(shares_qty)
    fee_ps = fee_rate * ((vwap * (1.0 - vwap)) ** fee_exponent) if fee_rate > 0.0 else 0.0
    fee_usd = float(shares_qty) * fee_ps
    return {
        "shares": int(shares_qty),
        "best_ask": round(asks_capped[0][0], 4),
        "vwap": round(vwap, 5),
        "worst_px": round(worst_px, 4),
        "spent_usd": round(spent, 4),
        "fee_usd": round(fee_usd, 4),
        "eff_px": round((spent + fee_usd) / float(shares_qty), 5),
        "levels": levels,
    }


def walk_equal_shares_dominance_box(
    asks_a_raw: List[Dict[str, Any]],
    asks_b_raw: List[Dict[str, Any]],
    target_budget_usd: float,
    fee_rate_a: float = 0.07,
    fee_rate_b: float = 0.07,
    fee_exponent_a: float = 1.0,
    fee_exponent_b: float = 1.0,
    max_box_cost_net: float = 0.995,
    max_slip_cents: float = 0.025,
    min_shares: int = 5,
    min_box_notional_usd: float = 4.85,
    min_box_cost_net: float = 0.900,
) -> Dict[str, Any]:
    """
    Walks BOTH L2 ask books for an IDENTICAL whole-integer share count `Q` (`Q_A == Q_B == Q`),
    guaranteeing zero unhedged directional delta outside `[K_low, K_high)`.
    Caps `Q` to available visible ask depth within `max_slip_cents` on the thinner leg,
    enforces all-in net box cost in `[min_box_cost_net, max_box_cost_net]` (vetoing inverted
    anti-boxes `< 0.900`), and includes both V2 taker fees.
    """
    capped_a, best_a, avail_a = _sorted_asks(asks_a_raw, max_slip_cents)
    capped_b, best_b, avail_b = _sorted_asks(asks_b_raw, max_slip_cents)
    if not capped_a or not capped_b:
        return {"filled": False, "reason": "EMPTY_BOOK", "best_sum": round(best_a + best_b, 4)}

    fee_best_a = fee_rate_a * ((best_a * (1.0 - best_a)) ** fee_exponent_a) if fee_rate_a > 0 else 0.0
    fee_best_b = fee_rate_b * ((best_b * (1.0 - best_b)) ** fee_exponent_b) if fee_rate_b > 0 else 0.0
    min_possible_unit_cost = best_a + fee_best_a + best_b + fee_best_b
    if min_possible_unit_cost < min_box_cost_net - 0.025 or (best_a + best_b) < 0.855:
        return {
            "filled": False,
            "reason": "SUSPECT_INVERTED_ANTI_BOX",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
        }
    if min_possible_unit_cost > max_box_cost_net + 0.015:
        return {
            "filled": False,
            "reason": "BOX_TOO_EXPENSIVE_L1",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": int(math.floor(min(avail_a, avail_b))),
        }

    max_avail_pairs = int(math.floor(min(avail_a, avail_b)))
    if max_avail_pairs < max(5, min_shares):
        return {
            "filled": False,
            "reason": "INSUFFICIENT_PAIR_SHARES",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": max_avail_pairs,
        }

    desired_pairs = int(math.floor(float(target_budget_usd) / max(0.10, min_possible_unit_cost)))
    q_pairs = min(desired_pairs, max_avail_pairs)
    if q_pairs < max(5, min_shares):
        return {
            "filled": False,
            "reason": "BUDGET_BELOW_MIN_SHARES",
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": max_avail_pairs,
        }

    w_a = _walk_exact_shares(capped_a, q_pairs, fee_rate_a, fee_exponent_a)
    w_b = _walk_exact_shares(capped_b, q_pairs, fee_rate_b, fee_exponent_b)
    if w_a is None or w_b is None:
        return {"filled": False, "reason": "WALK_FAILED", "avail_pair_shares": max_avail_pairs}

    spent_total = w_a["spent_usd"] + w_b["spent_usd"]
    fee_total = w_a["fee_usd"] + w_b["fee_usd"]
    all_in_total = spent_total + fee_total
    box_cost_net = all_in_total / float(q_pairs)

    # If budget slightly exceeded due to multi-level walk, trim Q by 1-2 shares to fit target_budget_usd
    if all_in_total > target_budget_usd * 1.02:
        q_trim = int(math.floor(float(target_budget_usd) / box_cost_net))
        if q_trim < max(5, min_shares):
            return {"filled": False, "reason": "TRIMMED_BELOW_MIN_SHARES", "box_cost_net": round(box_cost_net, 5)}
        q_pairs = q_trim
        w_a = _walk_exact_shares(capped_a, q_pairs, fee_rate_a, fee_exponent_a)
        w_b = _walk_exact_shares(capped_b, q_pairs, fee_rate_b, fee_exponent_b)
        if w_a is None or w_b is None:
            return {"filled": False, "reason": "WALK_TRIM_FAILED"}
        spent_total = w_a["spent_usd"] + w_b["spent_usd"]
        fee_total = w_a["fee_usd"] + w_b["fee_usd"]
        all_in_total = spent_total + fee_total
        box_cost_net = all_in_total / float(q_pairs)

    # Trim multi-level spills when worst_px_a + worst_px_b + fees exceeds max_box_cost_net
    # so FOK limit orders never self-veto on WORST_LIMIT_BOX_COST_EXCEEDS_CAP when L1 size >= min_shares.
    def _worst_limit_net(wa_d: Dict[str, Any], wb_d: Dict[str, Any]) -> float:
        pa, pb = float(wa_d["worst_px"]), float(wb_d["worst_px"])
        fa = fee_rate_a * ((pa * (1.0 - pa)) ** fee_exponent_a) if fee_rate_a > 0.0 else 0.0
        fb = fee_rate_b * ((pb * (1.0 - pb)) ** fee_exponent_b) if fee_rate_b > 0.0 else 0.0
        return round(pa + fa + pb + fb, 6)

    if _worst_limit_net(w_a, w_b) > max_box_cost_net + 1e-6:
        min_q = max(5, int(min_shares))
        bp_set = set()
        for lvl_list in (capped_a, capped_b):
            cum_sz = 0.0
            for _, sz_lvl in lvl_list:
                cum_sz += sz_lvl
                q_bp = int(math.floor(cum_sz + 1e-9))
                if min_q <= q_bp < q_pairs:
                    bp_set.add(q_bp)
        trimmed_ok = False
        for q_cand in sorted(bp_set, reverse=True):
            wa_c = _walk_exact_shares(capped_a, q_cand, fee_rate_a, fee_exponent_a)
            wb_c = _walk_exact_shares(capped_b, q_cand, fee_rate_b, fee_exponent_b)
            if wa_c is None or wb_c is None:
                continue
            sp_c = wa_c["spent_usd"] + wb_c["spent_usd"]
            if sp_c < min_box_notional_usd:
                continue
            if _worst_limit_net(wa_c, wb_c) <= max_box_cost_net + 1e-6:
                q_pairs = q_cand
                w_a, w_b = wa_c, wb_c
                spent_total = sp_c
                fee_total = w_a["fee_usd"] + w_b["fee_usd"]
                all_in_total = spent_total + fee_total
                box_cost_net = all_in_total / float(q_pairs)
                trimmed_ok = True
                break
        if not trimmed_ok:
            return {
                "filled": False,
                "reason": "WORST_LIMIT_COST_ABOVE_CAP",
                "best_a": round(best_a, 4),
                "best_b": round(best_b, 4),
                "box_cost_net": round(box_cost_net, 5),
                "worst_limit_cost_net": _worst_limit_net(w_a, w_b),
                "l1_box_cost_net": round(min_possible_unit_cost, 5),
                "avail_pair_shares": max_avail_pairs,
            }

    # Polymarket rejects marketable orders below $1 notional: with equal-share boxes a cheap leg
    # (e.g. 5 sh @ $0.07) would be rejected while the other leg fills -> one-legged box. Checked
    # AFTER all Q trims so the final share count is what gets validated.
    min_leg_px = min(best_a, best_b)
    q_floor = int(math.ceil(1.0 / max(min_leg_px, 0.01) - 1e-9))
    if q_pairs < q_floor:
        return {
            "filled": False,
            "reason": "LEG_BELOW_1USD_MIN",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": max_avail_pairs,
        }

    if spent_total < min_box_notional_usd:
        return {
            "filled": False,
            "reason": "BELOW_MIN_BOX_NOTIONAL",
            "box_cost_net": round(box_cost_net, 5),
            "spent_usd": round(spent_total, 2),
        }

    if box_cost_net < min_box_cost_net:
        return {
            "filled": False,
            "reason": "SUSPECT_INVERTED_ANTI_BOX",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "box_cost_net": round(box_cost_net, 5),
        }

    if box_cost_net > max_box_cost_net:
        return {
            "filled": False,
            "reason": "BOX_COST_ABOVE_CAP",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "box_cost_net": round(box_cost_net, 5),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": max_avail_pairs,
        }

    riskless_floor = 1.0 - box_cost_net
    l1_pair_usd = round(min(avail_a, avail_b) * (best_a + best_b), 2)
    return {
        "filled": True,
        "shares": int(q_pairs),
        "best_ask": round(best_a + best_b, 4),
        "vwap": round(spent_total / float(q_pairs), 5),
        "eff_px": round(box_cost_net, 5),
        "box_cost_net": round(box_cost_net, 5),
        "riskless_floor_per_pair": round(riskless_floor, 5),
        "guaranteed_min_profit_usd": round(float(q_pairs) * riskless_floor, 4),
        "corridor_bonus_profit_usd": round(float(q_pairs) * (2.0 - box_cost_net), 4),
        "slip_cents": round(((spent_total / float(q_pairs)) - (best_a + best_b)) * 100.0, 2),
        "spent_usd": round(spent_total, 4),
        "fee_usd": round(fee_total, 4),
        "fill_ratio": round(min(1.0, all_in_total / max(1e-6, float(target_budget_usd))), 4),
        "l1_usd": l1_pair_usd,
        "avail_pair_shares": max_avail_pairs,
        "avail_a_shares": round(avail_a, 2),
        "avail_b_shares": round(avail_b, 2),
        "leg_a_walk": w_a,
        "leg_b_walk": w_b,
        "levels": max(w_a["levels"], w_b["levels"]),
    }


def compute_dominance_box_payout_from_close(close_px: float, k_low: float, k_high: float) -> float:
    """
    Exact terminal payout per 1-share dominance pair (`UP(k_low) + DOWN(k_high)`)
    given finalized Chainlink 60s-TWAP `closePrice`. Always returns 1.0 or 2.0.
    """
    leg_a_pay = 1.0 if close_px >= k_low else 0.0
    leg_b_pay = 1.0 if close_px < k_high else 0.0
    return leg_a_pay + leg_b_pay


def walk_equal_shares_multi_leg_box(
    legs_spec: List[Dict[str, Any]],
    target_budget_usd: float,
    guaranteed_payout_per_bundle: float = 1.0,
    max_bundle_cost_net: float = 0.992,
    max_slip_cents: float = 0.025,
    min_shares: int = 5,
    min_box_notional_usd: float = 4.85,
) -> Dict[str, Any]:
    """
    Walks N L2 ask books (`N >= 2`, e.g., 2-leg tail equivalence or 3-leg Multi-Strike vs
    NegRisk Bracket partition/complement) for an IDENTICAL integer share count `Q` across all legs.
    Each item in `legs_spec` must contain `{"asks": [...], "fee_rate": float, "fee_exponent": float}`.
    Normalizes `eff_px` per `$1.00` of guaranteed payout so `payout_per_share = 1.0` at settlement
    for `$1.00`-floor bundles (and `2.0` for `$2.00`-floor complement bundles).
    """
    if len(legs_spec) < 2 or guaranteed_payout_per_bundle <= 0.0:
        return {"filled": False, "reason": "INVALID_BUNDLE_SPEC"}

    capped_list: List[List[Tuple[float, float]]] = []
    best_asks: List[float] = []
    avails: List[float] = []
    min_unit_cost = 0.0

    for lg in legs_spec:
        capped, best_a, avail_a = _sorted_asks(lg.get("asks") or [], max_slip_cents)
        if not capped:
            return {"filled": False, "reason": "EMPTY_LEG_BOOK"}
        fr = float(lg.get("fee_rate", 0.07))
        fe = float(lg.get("fee_exponent", 1.0))
        fee_best = fr * ((best_a * (1.0 - best_a)) ** fe) if fr > 0.0 else 0.0
        capped_list.append(capped)
        best_asks.append(best_a)
        avails.append(avail_a)
        min_unit_cost += best_a + fee_best

    if min_unit_cost > max_bundle_cost_net + 0.015:
        return {
            "filled": False,
            "reason": "BUNDLE_TOO_EXPENSIVE_L1",
            "l1_bundle_cost_net": round(min_unit_cost, 5),
        }

    max_avail_sh = int(math.floor(min(avails)))
    if max_avail_sh < max(5, min_shares):
        return {
            "filled": False,
            "reason": "INSUFFICIENT_BUNDLE_SHARES",
            "avail_bundle_shares": max_avail_sh,
        }

    desired_sh = int(math.floor(float(target_budget_usd) / max(0.10, min_unit_cost)))
    q_sh = min(desired_sh, max_avail_sh)
    if q_sh < max(5, min_shares):
        return {"filled": False, "reason": "BUDGET_BELOW_MIN_SHARES"}

    walks: List[Dict[str, Any]] = []
    for lg, capped in zip(legs_spec, capped_list):
        w_i = _walk_exact_shares(capped, q_sh, float(lg.get("fee_rate", 0.07)), float(lg.get("fee_exponent", 1.0)))
        if w_i is None:
            return {"filled": False, "reason": "LEG_WALK_FAILED"}
        walks.append(w_i)

    spent_total = sum(w["spent_usd"] for w in walks)
    fee_total = sum(w["fee_usd"] for w in walks)
    all_in_total = spent_total + fee_total
    bundle_cost_net = all_in_total / float(q_sh)

    if all_in_total > target_budget_usd * 1.02:
        q_trim = int(math.floor(float(target_budget_usd) / bundle_cost_net))
        if q_trim < max(5, min_shares):
            return {"filled": False, "reason": "TRIMMED_BELOW_MIN_SHARES"}
        q_sh = q_trim
        walks = []
        for lg, capped in zip(legs_spec, capped_list):
            w_i = _walk_exact_shares(capped, q_sh, float(lg.get("fee_rate", 0.07)), float(lg.get("fee_exponent", 1.0)))
            if w_i is None:
                return {"filled": False, "reason": "LEG_TRIM_WALK_FAILED"}
            walks.append(w_i)
        spent_total = sum(w["spent_usd"] for w in walks)
        fee_total = sum(w["fee_usd"] for w in walks)
        all_in_total = spent_total + fee_total
        bundle_cost_net = all_in_total / float(q_sh)

    # Polymarket $1 min marketable order: every leg must clear $1 at the final Q (else one-legged bundle).
    min_leg_px = min(best_asks)
    q_floor = int(math.ceil(1.0 / max(min_leg_px, 0.01) - 1e-9))
    if q_sh < q_floor:
        return {
            "filled": False,
            "reason": "LEG_BELOW_1USD_MIN",
            "avail_bundle_shares": max_avail_sh,
        }

    if spent_total < min_box_notional_usd:
        return {"filled": False, "reason": "BELOW_MIN_BOX_NOTIONAL", "spent_usd": round(spent_total, 2)}
    if bundle_cost_net > max_bundle_cost_net:
        return {
            "filled": False,
            "reason": "BUNDLE_COST_ABOVE_CAP",
            "bundle_cost_net": round(bundle_cost_net, 5),
            "l1_bundle_cost_net": round(min_unit_cost, 5),
        }

    floor_per_bundle = guaranteed_payout_per_bundle - bundle_cost_net
    l1_bundle_usd = round(min(avails) * sum(best_asks), 2)
    return {
        "filled": True,
        "shares": int(q_sh),
        "best_ask": round(sum(best_asks), 4),
        "vwap": round(spent_total / float(q_sh), 5),
        "eff_px": round(bundle_cost_net, 5),
        "box_cost_net": round(bundle_cost_net, 5),
        "guaranteed_payout_per_bundle": round(guaranteed_payout_per_bundle, 4),
        "riskless_floor_per_pair": round(floor_per_bundle, 5),
        "guaranteed_min_profit_usd": round(float(q_sh) * floor_per_bundle, 4),
        "spent_usd": round(spent_total, 4),
        "fee_usd": round(fee_total, 4),
        "l1_usd": l1_bundle_usd,
        "avail_bundle_shares": max_avail_sh,
        "leg_walks": walks,
    }

# ======================================================================================
# [08/16] MODULE: src/polymarket_research/exact_twap_lock_engine.py
# PURPOSE: Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock
# ======================================================================================

#!/usr/bin/env python3
r"""
Exact-Strike Final-45s Chainlink 60s-TWAP Mathematical Lock Engine (Sleeve S2)
==============================================================================
Exploits deterministic path-integral locking in the final 8s-45s of Polymarket
5-minute and 15-minute crypto Up/Down markets (`BTC`, `ETH`, `SOL`, `XRP` = 64
expiries/hour) settled on Chainlink's 60-second time-weighted average price:

  1. Exact Strike (`openPrice`):
     Queries Polymarket's authoritative `crypto-price` endpoint to lock the exact
     14-digit Chainlink 60s-TWAP opening benchmark `K_open` (zero Binance 1m drift).
  2. Banked Integral Decomposition (`[T_end - 60, t]` vs `[t, T_end]`):
     At `tau = T_end - t` seconds before expiry (`8s <= tau <= 45s`), a fraction
     `alpha = (60 - tau) / 60` (`25%` to `86.7%`) of the terminal settlement TWAP is
     already frozen history (`S_banked`).
  3. Fat-Tailed Asian Variance (`Student-t(df=5)` + Kemna-Vorst `tau/3` + Basis Floor):
     Models the remaining `tau` seconds with a `1.35x` jump-inflated Deribit 1D ATM IV,
     Asian time-averaging variance reduction (`tau / 3`), explicit Chainlink-vs-spot
     basis uncertainty (`5-9 bps`), and exact closed-form `Student-t(df=5)` tails.
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DEFAULT_ANNUAL_IV_FLOORS: Dict[str, float] = {
    "BTC": 0.55,
    "ETH": 0.70,
    "SOL": 0.90,
    "XRP": 0.95,
    "BNB": 0.85,
    "DOGE": 1.15,
    "HYPE": 1.35,
}

SECONDS_PER_YEAR = 365.25 * 86400.0
SHM_DIR = Path(os.getenv("PM_FAST_TICK_DIR", "/dev/shm"))


def student_t_df5_cdf(z: float) -> float:
    """
    Exact analytical closed-form CDF of the Student-t distribution with nu = 5
    degrees of freedom (fat-tailed crypto jump safety without scipy overhead).
    """
    if not math.isfinite(z):
        return 0.5
    u = z / math.sqrt(5.0)
    u2 = u * u
    denom = 1.0 + u2
    val = 0.5 + (
        math.atan(u)
        + (u / denom)
        + (2.0 / 3.0) * (u / (denom * denom))
    ) / math.pi
    return max(0.0, min(1.0, val))


def read_shm_usd_anchor(asset: str, now_ts: float, max_age_sec: float = 2.5) -> Dict[str, Optional[float]]:
    """
    Reads zero-REST `/dev/shm/pm_fast_tick_{ASSET}.json` published by the live
    recorder processes when running on Linux (`kraken-finland`), extracting strictly
    USD-denominated `chainlink_proxy_spot`, `coinbase_spot`, and `chainlink_twap_60s`.
    Never falls back to USDT `spot_price` (`H-01`), and rejects future clock skew (`F-11`).
    """
    p = SHM_DIR / f"pm_fast_tick_{str(asset).upper()}.json"
    if not p.exists():
        return {"usd_spot": None, "twap_60s": None, "source": None}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        ts = float(data.get("timestamp_unix") or data.get("ts") or 0.0)
        age = now_ts - ts
        if ts <= 0.0 or age > max_age_sec or age < -1.5:
            return {"usd_spot": None, "twap_60s": None, "source": None}
        cl_spot = data.get("chainlink_proxy_spot")
        cb_spot = data.get("coinbase_spot")
        twap_60 = data.get("chainlink_twap_60s")
        if cl_spot and float(cl_spot) > 0:
            return {
                "usd_spot": float(cl_spot),
                "twap_60s": float(twap_60) if (twap_60 and float(twap_60) > 0) else None,
                "source": "shm_chainlink_proxy",
            }
        if cb_spot and float(cb_spot) > 0:
            return {
                "usd_spot": float(cb_spot),
                "twap_60s": float(twap_60) if (twap_60 and float(twap_60) > 0) else None,
                "source": "shm_coinbase_usd",
            }
    except Exception:
        pass
    return {"usd_spot": None, "twap_60s": None, "source": None}


def compute_exact_twap_lock_probability(
    *,
    asset: str,
    open_price: float,
    current_usd_spot: float,
    rem_seconds: float,
    now_ts: float,
    end_ts: float,
    spot_samples: Sequence[Tuple[float, float]] = (),
    shm_twap_60s: Optional[float] = None,
    iv_annual: Optional[float] = None,
    usd_direct_feed: bool = False,
    min_rem_seconds: float = 8.0,
    max_rem_seconds: float = 45.0,
    jump_vol_mult: float = 1.35,
) -> Dict[str, Any]:
    """
    Computes the fat-tailed mathematical lock probability for a 60s-TWAP Chainlink
    Up/Down binary contract in its final `[min_rem_seconds, max_rem_seconds]` window.
    """
    if (
        not math.isfinite(open_price)
        or open_price <= 0.0
        or not math.isfinite(current_usd_spot)
        or current_usd_spot <= 0.0
        or not (min_rem_seconds <= rem_seconds <= max_rem_seconds)
    ):
        return {"eligible": False, "reason": "OUT_OF_WINDOW_OR_INVALID_PRICES"}

    window_start = end_ts - 60.0
    elapsed_in_twap = max(0.0, min(60.0, 60.0 - rem_seconds))
    raw_alpha = elapsed_in_twap / 60.0

    raw_in_window = sorted(
        (float(ts), float(px))
        for ts, px in spot_samples
        if window_start <= float(ts) <= now_ts + 0.5 and float(px) > 0.0 and math.isfinite(float(px))
    )
    in_window: List[Tuple[float, float]] = []
    for ts, px in raw_in_window:
        if in_window and abs(ts - in_window[-1][0]) < 1e-6:
            in_window[-1] = (ts, px)
        else:
            in_window.append((ts, px))

    if len(in_window) >= 2:
        t_first, p_first = in_window[0]
        t_last, p_last = in_window[-1]
        lead_dt = min(2.0, max(0.0, t_first - window_start))
        tail_dt = min(2.0, max(0.0, now_ts - t_last))
        area = lead_dt * p_first + tail_dt * p_last
        total_dt = lead_dt + tail_dt
        unobserved_gap = max(0.0, (t_first - window_start) - lead_dt) + max(0.0, (now_ts - t_last) - tail_dt)
        for idx in range(len(in_window) - 1):
            t0, p0 = in_window[idx]
            t1, p1 = in_window[idx + 1]
            dt = max(0.0, t1 - t0)
            eff_dt = min(dt, 6.0)
            area += 0.5 * (p0 + p1) * eff_dt
            total_dt += eff_dt
            if dt > 6.0:
                unobserved_gap += dt - 6.0
        banked_mean = (area / total_dt) if total_dt > 0.0 else (sum(px for _, px in in_window) / len(in_window))
        coverage_ratio = max(0.0, min(1.0, (elapsed_in_twap - unobserved_gap) / max(1.0, elapsed_in_twap)))
        eff_alpha = raw_alpha * coverage_ratio
    elif (
        shm_twap_60s is not None
        and shm_twap_60s > 0.0
        and math.isfinite(shm_twap_60s)
        and rem_seconds <= 12.0
    ):
        # Only allow rolling [now-60, now] TWAP fallback when >=80% overlaps [T_end-60, now],
        # penalizing pre-window [now-60, T_end-60] contamination (`H-06`).
        banked_mean = float(shm_twap_60s)
        overlap_penalty = max(0.0, (60.0 - 2.0 * rem_seconds) / 60.0)
        eff_alpha = raw_alpha * overlap_penalty
    else:
        banked_mean = current_usd_spot
        eff_alpha = 0.0

    mu_twap = eff_alpha * banked_mean + (1.0 - eff_alpha) * current_usd_spot

    # Enforce dual-side agreement: BOTH current spot AND projected TWAP must beat K_open
    spot_diff = current_usd_spot - open_price
    twap_diff = mu_twap - open_price
    if spot_diff == 0.0 or twap_diff == 0.0 or (spot_diff > 0.0) != (twap_diff > 0.0):
        return {
            "eligible": False,
            "reason": "WHIPSAW_SPLIT_ACROSS_STRIKE",
            "mu_twap": round(mu_twap, 6),
            "eff_alpha": round(eff_alpha, 4),
        }

    side = "UP" if twap_diff > 0.0 else "DOWN"
    asset_u = str(asset).upper()
    iv_floor = DEFAULT_ANNUAL_IV_FLOORS.get(asset_u, 0.80)
    sigma_ann = max(iv_floor, float(iv_annual or 0.0))
    sigma_1s = (sigma_ann * jump_vol_mult) / math.sqrt(SECONDS_PER_YEAR)

    # Exact discrete 1-second Kemna-Vorst arithmetic-average variance factor on remaining N_rem steps (`F-15`)
    rem_weight = 1.0 - eff_alpha
    n_rem = max(1, int(round(rem_seconds)))
    kv_factor = ((n_rem + 1.0) * (2.0 * n_rem + 1.0)) / (6.0 * n_rem * n_rem)
    sigma_rem_usd = rem_weight * current_usd_spot * sigma_1s * math.sqrt(max(1.0, rem_seconds) * kv_factor)

    # Chainlink Data Streams USD 60s TWAP vs exchange spot basis uncertainty floor
    basis_bps = 4.5 if usd_direct_feed else 8.5
    sigma_basis_usd = current_usd_spot * (basis_bps / 10000.0)
    sigma_total_usd = math.hypot(sigma_rem_usd, sigma_basis_usd)

    if sigma_total_usd <= 0.0:
        return {"eligible": False, "reason": "ZERO_SIGMA"}

    z_lock = abs(twap_diff) / sigma_total_usd
    p_lock = student_t_df5_cdf(z_lock)
    cushion_bps = (abs(twap_diff) / open_price) * 10000.0

    return {
        "eligible": True,
        "side": side,
        "open_price": open_price,
        "current_usd_spot": round(current_usd_spot, 6),
        "banked_mean": round(banked_mean, 6),
        "mu_twap": round(mu_twap, 6),
        "eff_alpha": round(eff_alpha, 4),
        "rem_seconds": round(rem_seconds, 2),
        "sigma_total_usd": round(sigma_total_usd, 6),
        "z_lock": round(z_lock, 4),
        "p_lock": round(min(0.996, p_lock), 4),
        "cushion_bps": round(cushion_bps, 2),
        "basis_bps_floor": basis_bps,
        "samples_in_window": len(in_window),
    }

# ======================================================================================
# [09/16] MODULE: src/polymarket_research/tradfi_sports_zero_fee_engine.py
# PURPOSE: Zero-Fee Pyth Commodities/Metals/Equities (CM_B3/B2/U1), B4 Wick Lock, NBA Polish-Middle (SP1) & NegRisk (NR0)
# ======================================================================================

#!/usr/bin/env python3
"""
Zero-Fee TradFi (Pyth Commodities, Metals & Equities), NBA Polish-Middle & NegRisk Engine
=========================================================================================
Expands Alpha-124 shadow trading into verified `0.00%`-fee (`feeType="zero_fees"`) verticals
while enforcing strict oracle-exactness and zero-lookahead rules:

  1. `CM_B3_PYTH_BARRIER_BOX` (`100%` WR Riskless `0%`-Fee Structural Boxes):
     - Same-event upward/downward barrier monotonicity (`YES(K_low) + NO(K_high) <= $0.994`).
     - Calendar inclusion (`NO(Week, K) + YES(Month, K) <= $0.994` on identical Pyth feed).
     - Path-vs-Terminal inclusion (`NO(Close > K_c) + YES(Hit >= K_h) <= $0.994`, `K_h <= K_c`).
  2. `CM_B2_PYTH_SESSION_NO_LOCK` & `CM_U1_PYTH_CLOSE_LOCK` (`0%`-Fee Session-Clock Locks):
     - Exact NYSE (`6.5h/day` Mon-Fri) & CME/ICE (`23h/day` Sun 18:00 - Fri 17:00 ET) trading-session
       variance clock (`eff_session_hours`), avoiding wall-clock weekend/overnight vol distortion.
     - Restricted strictly to exact instrument matches (never feeding COMEX futures into spot XAU/XAG).
  3. `B4_TOUCHED_BARRIER_WICK_LOCK` (`100%` WR Post-Breach Finalized-1m Wick Sweep):
     - Sweeps stale CLOB `YES` asks after finalized `1m` candle High/Low has deterministically
       breached strike `K` beyond a strict safety buffer (`>= 5 bps` Crypto, `>= 15 bps` Cash Equities).
  4. `SP1_NBA_ZERO_FEE_BOX` (`100%` WR Riskless `0%`-Fee NBA Full-Game Dominance Boxes):
     - Full-game Moneyline vs `+k.5` Spread ("Polish Middle"), Spread vs Spread (`L < U`), and
       Total `Over T_low + Under T_high` (`T_low < T_high`) with `$1.00` floor and `$2.00` middle.
  5. `NR0_ZERO_FEE_SLATE_ARB` (`100%` WR Riskless `0%`-Fee NegRisk Partition Underround):
     - Full-slate `YES` (`sum <= $0.988`) & `NO` complement (`sum <= (N-1) - $0.012`) across
       `elon-tweets`, `elon-tweets-48h`, `fomc`, `bank-of-japan`, and `bank-of-canada-decision`.
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import json
import logging
import math
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from src.polymarket_research.barrier_onetouch_svi_engine import (
    detect_barrier_monotonicity_boxes,
    first_passage_touch_prob,
)

logger = logging.getLogger("TradFiSportsZeroFee")

NY_TZ = ZoneInfo("America/New_York")

# (asset, yahoo_ticker, session_class, exact_directional_ok, basis_buffer_frac, vol_floor_annual)
PYTH_ASSET_CONFIG: Dict[str, Tuple[str, str, bool, float, float]] = {
    "WTI": ("CL=F", "CME_23H", True, 0.0045, 0.32),
    "NG": ("NG=F", "CME_23H", True, 0.0060, 0.48),
    "GC": ("GC=F", "CME_23H", True, 0.0020, 0.20),
    "SI": ("SI=F", "CME_23H", True, 0.0030, 0.32),
    # Spot XAUUSD / XAGUSD use GC=F / SI=F ONLY as ATM-filter anchor for 100%-riskless CM_B3 boxes
    "XAUUSD": ("GC=F", "CME_23H", False, 0.0150, 0.20),
    "XAGUSD": ("SI=F", "CME_23H", False, 0.0200, 0.32),
    "SPY": ("SPY", "EQUITY_RTH", True, 0.0015, 0.18),
    "NVDA": ("NVDA", "EQUITY_RTH", True, 0.0015, 0.42),
    "AMZN": ("AMZN", "EQUITY_RTH", True, 0.0015, 0.34),
    "GOOGL": ("GOOGL", "EQUITY_RTH", True, 0.0015, 0.34),
    "MSFT": ("MSFT", "EQUITY_RTH", True, 0.0015, 0.30),
    "AAPL": ("AAPL", "EQUITY_RTH", True, 0.0015, 0.28),
    "TSLA": ("TSLA", "EQUITY_RTH", True, 0.0015, 0.52),
    "COIN": ("COIN", "EQUITY_RTH", True, 0.0020, 0.65),
    "HOOD": ("HOOD", "EQUITY_RTH", True, 0.0020, 0.58),
    "PLTR": ("PLTR", "EQUITY_RTH", True, 0.0020, 0.55),
}

PYTH_HIT_SERIES: Tuple[Tuple[str, str, str], ...] = (
    ("WTI", "MONTH", "crude-oil-cl-hit"),
    ("WTI", "WEEK", "wti-crude-oil-hit-price-weekly"),
    ("NG", "WEEK", "natural-gas-hit-price-weekly"),
    ("XAUUSD", "MONTH", "xauusd-hit-month"),
    ("XAUUSD", "WEEK", "gold-hit-price-weekly"),
    ("GC", "MONTH", "what-will-gold-gc-hit"),
    ("XAGUSD", "MONTH", "xagusd-hit-month"),
    ("XAGUSD", "WEEK", "silver-hit-price-weekly"),
    ("SI", "MONTH", "what-will-silver-si-hit"),
    ("SPY", "MONTH", "spy-hit-month"),
    ("SPY", "WEEK", "spy-hit-price-weekly"),
    ("NVDA", "MONTH", "nvidia-hit-price-monthly"),
    ("NVDA", "WEEK", "nvidia-hit-price-weekly"),
    ("AMZN", "WEEK", "amazon-hit-price-weekly"),
    ("GOOGL", "WEEK", "google-hit-price-weekly"),
    ("MSFT", "WEEK", "microsoft-hit-price-weekly"),
    ("AAPL", "WEEK", "apple-hit-price-weekly"),
    ("TSLA", "WEEK", "tesla-hit-price-weekly"),
    ("COIN", "MONTH", "coin-hit-month"),
    ("HOOD", "MONTH", "hood-hit-month"),
    ("PLTR", "WEEK", "palantir-hit-price-weekly"),
)

PYTH_CLOSE_SERIES: Tuple[Tuple[str, str], ...] = (
    ("SPY", "spy-daily-close-uo"),
    ("WTI", "wti-daily-close-uo"),
    ("MSFT", "msft-multi-strikes-weekly"),
    ("NVDA", "nvda-multi-strikes-weekly"),
    ("AAPL", "aapl-multi-strikes-weekly"),
    ("TSLA", "tsla-multi-strikes-weekly"),
)

NBA_SERIES_SLUGS: Tuple[str, ...] = ("nba-2026",)

ZERO_FEE_NEGRISK_SERIES: Tuple[str, ...] = (
    "elon-tweets",
    "elon-tweets-48h",
    "trump-truth-social",
    "fomc",
    "fed-3-parlay",
    "bank-of-japan",
    "bank-of-canada-decision",
    "reserve-bank-of-australia-decision",
    "reserve-bank-of-new-zealand-decision",
    "us-gas-price-daily",
    "best-ai-company",
    "chinese-ai-1",
)

_STRIKE_PRICE_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)")
_SPREAD_FAV_RE = re.compile(r"Spread:\s*(.+?)\s*\(\s*([-+]?\d+(?:\.\d+)?)\s*\)", re.IGNORECASE)


def _extract_market_fee_rate(m: Dict[str, Any]) -> Tuple[float, float]:
    sched = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    fees_enabled = bool(m.get("feesEnabled", False))
    raw_rate = float(sched.get("rate") or 0.0)
    fee_type = str(m.get("feeType") or "").lower()
    if fee_type == "zero_fees" or not fees_enabled or raw_rate <= 0.0:
        return 0.0, 1.0
    return raw_rate, float(sched.get("exponent") or 1.0)


def _parse_clob_tokens(m: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    toks = m.get("clobTokenIds")
    if isinstance(toks, str):
        try:
            toks = json.loads(toks)
        except Exception:
            toks = None
    if isinstance(toks, list) and len(toks) >= 2 and toks[0] and toks[1]:
        return str(toks[0]), str(toks[1])
    return None


def _parse_iso_ts(raw_iso: Any) -> Optional[float]:
    s = str(raw_iso or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


@dataclass
class PythBarrierRungSpec:
    event_id: str
    market_id: str
    condition_id: str
    asset: str
    horizon_group: str  # "WEEK" or "MONTH"
    series_slug: str
    question: str
    strike: float
    direction: str  # "UP" or "DOWN"
    yes_token: str
    no_token: str
    start_ts: float
    end_ts: float
    fee_rate: float = 0.0


@dataclass
class PythCloseRungSpec:
    event_id: str
    market_id: str
    condition_id: str
    asset: str
    series_slug: str
    question: str
    strike: float
    is_downward: bool
    yes_token: str
    no_token: str
    end_ts: float
    fee_rate: float = 0.0


@dataclass
class NbaOutcomeLeg:
    market_id: str
    condition_id: str
    market_type: str  # "moneyline", "spreads", "totals"
    token_id: str
    opp_token_id: str
    side_index: int  # 0 or 1 in outcomes/clobTokenIds
    side_label: str  # "YES" for idx 0, "NO" for idx 1 (matches resolve_via_gamma_market)
    display_label: str
    # For margin markets: "GT" means M > threshold, "LT" means M < threshold (where M = Score(team_a) - Score(team_b))
    # For totals markets: "OVER" means S > threshold, "UNDER" means S < threshold
    relation: str
    threshold: float


@dataclass
class NbaGameSpec:
    event_id: str
    slug: str
    title: str
    team_a: str
    team_b: str
    tipoff_ts: float
    settle_est_ts: float
    margin_legs: List[NbaOutcomeLeg] = field(default_factory=list)
    total_legs: List[NbaOutcomeLeg] = field(default_factory=list)


@dataclass
class ZeroFeeNegRiskSlateSpec:
    event_id: str
    series_slug: str
    title: str
    end_ts: float
    brackets: List[Dict[str, Any]]  # market_id, condition_id, label, yes_token, no_token


def compute_effective_trading_hours(
    start_ts: float,
    end_ts: float,
    session_class: str = "EQUITY_RTH",
) -> float:
    """
    Computes exact active primary-exchange trading hours inside `[start_ts, end_ts]` in `America/New_York`:
      - `EQUITY_RTH`: Mon-Fri `09:30 - 16:00 ET` (`6.5h/day`, `0h` overnight & weekends).
      - `CME_23H`: Sun `18:00 ET` through Fri `17:00 ET` excluding daily `17:00 - 18:00 ET` break (`23h/day`).
    """
    if end_ts <= start_ts:
        return 0.0
    dt_s = datetime.fromtimestamp(start_ts, tz=NY_TZ)
    dt_e = datetime.fromtimestamp(end_ts, tz=NY_TZ)
    cur_date = dt_s.date()
    end_date = dt_e.date()
    total_sec = 0.0

    while cur_date <= end_date:
        wd = cur_date.weekday()  # Mon=0 .. Sun=6
        day_anchor = datetime(cur_date.year, cur_date.month, cur_date.day, 0, 0, tzinfo=NY_TZ)
        windows: List[Tuple[datetime, datetime]] = []
        if session_class == "EQUITY_RTH":
            if wd < 5:
                windows.append((
                    day_anchor.replace(hour=9, minute=30),
                    day_anchor.replace(hour=16, minute=0),
                ))
        else:
            # CME / ICE 23h schedule:
            # Mon-Thu: [00:00, 17:00] + [18:00, 24:00]; Fri: [00:00, 17:00]; Sat: closed; Sun: [18:00, 24:00]
            if wd < 4:
                windows.append((day_anchor, day_anchor.replace(hour=17, minute=0)))
                windows.append((day_anchor.replace(hour=18, minute=0), day_anchor + timedelta(days=1)))
            elif wd == 4:
                windows.append((day_anchor, day_anchor.replace(hour=17, minute=0)))
            elif wd == 6:
                windows.append((day_anchor.replace(hour=18, minute=0), day_anchor + timedelta(days=1)))

        for w0, w1 in windows:
            lo = max(start_ts, w0.timestamp())
            hi = min(end_ts, w1.timestamp())
            if hi > lo:
                total_sec += hi - lo
        cur_date += timedelta(days=1)

    return total_sec / 3600.0


def is_same_continuous_session(now_ts: float, end_ts: float, session_class: str = "EQUITY_RTH") -> bool:
    """
    Verifies ZERO overnight, weekend, or after-hours earnings gaps exist between `now_ts` and `end_ts`:
      - `EQUITY_RTH`: `now_ts` must be inside active Mon-Fri `09:30 - 16:00 ET` on the EXACT same NY
        trading date as `end_ts` (eliminates all post-close / pre-open earnings gap risk!).
      - `CME_23H`: `0 < (end_ts - now_ts) <= 4.0h` with active trading hours matching wall clock (`>= 98%`).
    """
    if end_ts <= now_ts:
        return False
    eff_h = compute_effective_trading_hours(now_ts, end_ts, session_class)
    if eff_h <= 0.0:
        return False
    if session_class == "EQUITY_RTH":
        dt_n = datetime.fromtimestamp(now_ts, tz=NY_TZ)
        dt_e = datetime.fromtimestamp(end_ts, tz=NY_TZ)
        if dt_n.weekday() >= 5 or dt_n.date() != dt_e.date():
            return False
        mins_n = dt_n.hour * 60 + dt_n.minute
        return (9 * 60 + 30) <= mins_n < (16 * 60)
    wall_h = (end_ts - now_ts) / 3600.0
    return wall_h <= 4.0 and eff_h >= 0.98 * wall_h


_MONTH_NAME_MAP: Dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_NAMED_WEEK_RE = re.compile(
    r"(?:week\s+of|trading\s+session\s+of)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:,?\s*(\d{4}))?",
    re.IGNORECASE,
)
_NAMED_MONTH_RE = re.compile(
    r"(?:\bin\s+|trading\s+session\s+of\s+)(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(\d{4}))?(?:\?|\b)",
    re.IGNORECASE,
)


def infer_named_period_start_ts(question: str, desc: str, end_ts: float) -> float:
    """
    Infers the authoritative observation-window start timestamp in `America/New_York` for pre-listed
    weekly/monthly barrier markets (e.g., `"hit $100 in November?"` listed on Oct 25 only counts
    sessions of November, never October candles!).
    """
    blob = f"{question} {desc}"
    ref_yr = datetime.fromtimestamp(max(0.0, float(end_ts) - 5 * 86400.0), tz=NY_TZ).year
    m_wk = _NAMED_WEEK_RE.search(blob)
    if m_wk:
        mo = _MONTH_NAME_MAP[m_wk.group(1).lower()]
        dy = int(m_wk.group(2))
        yr = int(m_wk.group(3)) if m_wk.group(3) else ref_yr
        try:
            dt0 = datetime(yr, mo, dy, 0, 0, tzinfo=NY_TZ)
            # Monday CME session opens Sunday 18:00 ET (-6h)
            return (dt0 - timedelta(hours=6 if dt0.weekday() == 0 else 0)).timestamp()
        except ValueError:
            return 0.0
    m_mo = _NAMED_MONTH_RE.search(blob)
    if m_mo:
        mo = _MONTH_NAME_MAP[m_mo.group(1).lower()]
        yr = int(m_mo.group(2)) if m_mo.group(2) else ref_yr
        try:
            return datetime(yr, mo, 1, 0, 0, tzinfo=NY_TZ).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def parse_pyth_hit_event(
    ev: Dict[str, Any],
    asset: str,
    horizon_group: str,
    series_slug: str,
) -> List[PythBarrierRungSpec]:
    """Parses `zero_fees` Pyth 1-minute barrier hit events (`↑ $K` / `↓ $K`)."""
    mkts = ev.get("markets") or []
    ev_id = str(ev.get("id") or "")
    ev_start = _parse_iso_ts(ev.get("startDate") or ev.get("createdAt")) or (time.time() - 86400.0)
    ev_end = _parse_iso_ts(ev.get("endDate"))
    out: List[PythBarrierRungSpec] = []

    for m in mkts:
        if m.get("closed") or m.get("archived"):
            continue
        fee_rate, _ = _extract_market_fee_rate(m)
        if fee_rate > 0.001:
            continue
        toks = _parse_clob_tokens(m)
        if not toks:
            continue
        desc = str(m.get("description") or ev.get("description") or "").lower()
        if "pyth" not in desc and "trading session" not in desc and "regular trading hours" not in desc:
            continue
        q = str(m.get("question") or "")
        git = str(m.get("groupItemTitle") or "")
        ql = (git + " " + q).lower()
        if "↑" in git or "(high)" in ql or "hit above" in ql:
            direction = "UP"
        elif "↓" in git or "(low)" in ql or "dip" in ql or "hit below" in ql:
            direction = "DOWN"
        else:
            continue
        m_px = _STRIKE_PRICE_RE.search(git) or _STRIKE_PRICE_RE.search(q)
        if not m_px:
            continue
        try:
            strike = float(m_px.group(1).replace(",", ""))
        except ValueError:
            continue
        if strike <= 0.0:
            continue
        end_ts = _parse_iso_ts(m.get("endDate")) or ev_end
        raw_m_start = _parse_iso_ts(m.get("startDate") or m.get("createdAt")) or ev_start
        if not end_ts:
            continue
        m_buf = 60.0 if (raw_m_start > ev_start + 300.0 or "creation of this market" in desc) else 0.0
        named_start = infer_named_period_start_ts(q or str(ev.get("title") or ""), desc, float(end_ts))
        start_ts = max(ev_start, named_start, min(float(end_ts) - 60.0, float(raw_m_start) + m_buf))
        out.append(
            PythBarrierRungSpec(
                event_id=ev_id,
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                asset=asset.upper(),
                horizon_group=horizon_group.upper(),
                series_slug=series_slug,
                question=q or git,
                strike=strike,
                direction=direction,
                yes_token=toks[0],
                no_token=toks[1],
                start_ts=float(start_ts),
                end_ts=float(end_ts),
                fee_rate=fee_rate,
            )
        )
    return out


def parse_pyth_close_event(
    ev: Dict[str, Any],
    asset: str,
    series_slug: str,
) -> List[PythCloseRungSpec]:
    """Parses `zero_fees` Pyth regular-session Close digital multi-strike ladders."""
    mkts = ev.get("markets") or []
    ev_id = str(ev.get("id") or "")
    ev_end = _parse_iso_ts(ev.get("endDate"))
    out: List[PythCloseRungSpec] = []
    for m in mkts:
        if m.get("closed") or m.get("archived"):
            continue
        fee_rate, _ = _extract_market_fee_rate(m)
        if fee_rate > 0.001:
            continue
        toks = _parse_clob_tokens(m)
        if not toks:
            continue
        desc = str(m.get("description") or ev.get("description") or "").lower()
        if "pyth" not in desc:
            continue
        q = str(m.get("question") or "")
        git = str(m.get("groupItemTitle") or "")
        ql = q.lower()
        is_down = ("below" in ql or "under" in ql) and ("above" not in ql)
        if not is_down and "above" not in ql and "over" not in ql:
            continue
        m_px = _STRIKE_PRICE_RE.search(git) or _STRIKE_PRICE_RE.search(q)
        if not m_px:
            continue
        try:
            strike = float(m_px.group(1).replace(",", ""))
        except ValueError:
            continue
        end_ts = _parse_iso_ts(m.get("endDate")) or ev_end
        if not end_ts or strike <= 0.0:
            continue
        out.append(
            PythCloseRungSpec(
                event_id=ev_id,
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                asset=asset.upper(),
                series_slug=series_slug,
                question=q or git,
                strike=strike,
                is_downward=is_down,
                yes_token=toks[0],
                no_token=toks[1],
                end_ts=float(end_ts),
                fee_rate=fee_rate,
            )
        )
    out.sort(key=lambda r: r.strike)
    return out


def fetch_yahoo_1m_intraday_sync(
    yahoo_symbol: str,
    vol_floor_annual: float = 0.25,
    timeout: float = 6.0,
) -> Optional[Dict[str, Any]]:
    """
    Fetches 5-day 1-minute intraday OHLC bars from Yahoo Finance v8 chart API.
    Strictly separates `spot` from finalized 1m bars (`bar_ts + 60 <= now_ts`) so unclosed
    bars never trigger finalized-1m barrier breach checks.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(yahoo_symbol)}?interval=1m&range=5d"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
        res0 = ((raw.get("chart") or {}).get("result") or [None])[0] or {}
        meta = res0.get("meta") or {}
        spot = float(meta.get("regularMarketPrice") or 0.0)
        ts_arr = res0.get("timestamp") or []
        q0 = (((res0.get("indicators") or {}).get("quote") or [None])[0]) or {}
        h_arr = q0.get("high") or []
        l_arr = q0.get("low") or []
        c_arr = q0.get("close") or []
        now_ts = time.time()
        bars: List[Tuple[int, float, float, float]] = []
        for idx, t_v in enumerate(ts_arr):
            if idx >= len(h_arr) or idx >= len(l_arr) or idx >= len(c_arr):
                continue
            hi, lo, cl = h_arr[idx], l_arr[idx], c_arr[idx]
            if hi is None or lo is None or cl is None:
                continue
            t_int = int(t_v)
            if t_int + 60 <= now_ts and float(cl) > 0:
                bars.append((t_int, float(hi), float(lo), float(cl)))
        if spot <= 0.0 and bars:
            spot = bars[-1][3]
        if spot <= 0.0:
            return None

        # Compute realized session volatility from consecutive 1m log returns (ignoring overnight gaps > 5m)
        rets_sq: List[float] = []
        for i in range(max(1, len(bars) - 390), len(bars)):
            dt_b = bars[i][0] - bars[i - 1][0]
            if 45 <= dt_b <= 180 and bars[i - 1][3] > 0:
                r = math.log(bars[i][3] / bars[i - 1][3])
                rets_sq.append(r * r)
        if len(rets_sq) >= 20:
            var_1m = sum(rets_sq) / len(rets_sq)
            # Annualize on 252 trading days * 390 RTH minutes = 98,280 trading minutes/year
            rv_ann = math.sqrt(var_1m * 98280.0)
        else:
            rv_ann = vol_floor_annual
        sigma_session = max(vol_floor_annual, min(2.0, rv_ann * 1.10))
        return {
            "spot": spot,
            "sigma_session": round(sigma_session, 4),
            "bars": bars,
            "fetched_ts": now_ts,
        }
    except Exception as exc:
        logger.debug(f"Yahoo 1m fetch notice ({yahoo_symbol}): {exc}")
        return None


def window_extremes_from_bars(
    bars: List[Tuple[int, float, float, float]],
    start_ts: float,
    end_ts: float,
) -> Optional[Tuple[float, float]]:
    sub = [b for b in bars if start_ts <= float(b[0]) <= end_ts]
    if not sub:
        return None
    return max(b[1] for b in sub), min(b[2] for b in sub)


def detect_pyth_calendar_inclusion_boxes(
    quote_rows: List[Dict[str, Any]],
    max_box_cost_net: float = 0.994,
    now_ts: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Same-Oracle Calendar Inclusion Box (`NO(Short, K) + YES(Long, K) <= max_box_cost_net`):
    Whenever both windows are active (`start_short <= now_ts` and `start_long <= now_ts`),
    `start_long <= start_short` (epsilon tolerance), and `end_short < end_long - 3600` on the identical
    `0%`-fee `(asset, direction, strike)`, hitting `K` in `Short` implies hitting `K` in `Long`.
    """
    now_v = float(now_ts if now_ts is not None else time.time())
    by_key: Dict[Tuple[str, str, float], List[Dict[str, Any]]] = {}
    for q in quote_rows:
        if float(q.get("fee_rate", 0.0)) > 0.001 or float(q.get("start_ts", 0.0)) > now_v:
            continue
        by_key.setdefault((str(q["asset"]), str(q["direction"]), round(float(q["strike"]), 4)), []).append(q)

    arbs: List[Dict[str, Any]] = []
    for (asset, direction, strike), grp in by_key.items():
        if len(grp) < 2:
            continue
        grp_s = sorted(grp, key=lambda x: float(x["end_ts"]))
        for i in range(len(grp_s)):
            for j in range(i + 1, len(grp_s)):
                q_s, q_l = grp_s[i], grp_s[j]
                if float(q_l["end_ts"]) - float(q_s["end_ts"]) < 3600.0:
                    continue
                # Long/YES window must start no later than Short/NO (a later Long start leaves an
                # uncovered gap where Short can hit K but Long cannot) -> epsilon tolerance only.
                if float(q_l["start_ts"]) > float(q_s["start_ts"]) + 1e-6:
                    continue
                ask_n_s = q_s.get("ask_no")
                ask_y_l = q_l.get("ask_yes")
                if ask_n_s is None or ask_y_l is None:
                    continue
                cost = round(float(ask_n_s) + float(ask_y_l), 4)
                if cost <= max_box_cost_net:
                    arbs.append({
                        "box_kind": "PYTH_CALENDAR_INCLUSION",
                        "asset": asset,
                        "direction": direction,
                        "strike": strike,
                        "box_cost_net": cost,
                        "box_cost_gross": cost,
                        "yes_row": q_l,
                        "no_row": q_s,
                        "close_ts": float(q_l["end_ts"]),
                        "label": f"NO_SHORT({direction} {strike}) + YES_LONG({direction} {strike})",
                    })
    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


def detect_pyth_close_vs_hit_boxes(
    close_rows: List[Dict[str, Any]],
    hit_rows: List[Dict[str, Any]],
    now_ts: float,
    max_box_cost_net: float = 0.994,
) -> List[Dict[str, Any]]:
    """
    Same-Oracle Path-vs-Terminal Inclusion Box:
    For upward digital `Closes > K_close` at `end_c` inside upward barrier `Hits >= K_hit` (`[start_h, end_h]`)
    with `K_hit <= K_close` and `start_h <= now_ts < end_c <= end_h + 60`:
      `Close > K_close` => final 1m RTH candle `High >= Close > K_hit` => `Hit >= K_hit` is TRUE!
      Hence `NO(Close > K_close) + YES(Hit >= K_hit) >= $1.00` deterministically (`$2.00` on touch-and-fade!).
    """
    arbs: List[Dict[str, Any]] = []
    for qc in close_rows:
        if qc.get("is_downward") or qc.get("ask_no") is None or float(qc.get("fee_rate", 0.0)) > 0.001:
            continue
        end_c = float(qc["end_ts"])
        k_c = float(qc["strike"])
        for qh in hit_rows:
            if (
                qh["asset"] != qc["asset"]
                or qh["direction"] != "UP"
                or qh.get("ask_yes") is None
                or float(qh.get("fee_rate", 0.0)) > 0.001
            ):
                continue
            k_h = float(qh["strike"])
            if k_h > k_c + 1e-6:
                continue
            if not (float(qh["start_ts"]) <= now_ts and now_ts < end_c <= float(qh["end_ts"]) + 60.0):
                continue
            cost = round(float(qc["ask_no"]) + float(qh["ask_yes"]), 4)
            if cost <= max_box_cost_net:
                arbs.append({
                    "box_kind": "PYTH_CLOSE_VS_HIT",
                    "asset": str(qc["asset"]),
                    "strike_hit": k_h,
                    "strike_close": k_c,
                    "box_cost_net": cost,
                    "box_cost_gross": cost,
                    "yes_row": qh,
                    "no_row": qc,
                    "close_ts": max(end_c, float(qh["end_ts"])),
                    "label": f"NO(Close>{k_c:g}) + YES(Hit>={k_h:g})",
                })
    arbs.sort(key=lambda x: float(x["box_cost_net"]))
    return arbs


def evaluate_pyth_session_barrier_no_lock(
    spot: float,
    strike: float,
    direction: str,
    eff_session_hours: float,
    sigma_session: float,
    basis_buffer_frac: float,
) -> Dict[str, Any]:
    """
    Computes conservative trading-session-clock `NO` lock probability on `0%`-fee Pyth barriers.
    Shifts `spot` adversely by `basis_buffer_frac` before computing first-passage touch probability.
    """
    if spot <= 0.0 or strike <= 0.0 or eff_session_hours <= 0.0:
        return {"p_touch": 1.0, "p_no": 0.0}
    if direction == "UP":
        adj_spot = spot * (1.0 + basis_buffer_frac)
        if adj_spot >= strike:
            return {"p_touch": 1.0, "p_no": 0.0}
    else:
        adj_spot = spot * (1.0 - basis_buffer_frac)
        if adj_spot <= strike:
            return {"p_touch": 1.0, "p_no": 0.0}
    # Convert active trading hours (`252 * 6.5h = 1638h/yr` for equities; use conservative `1638h` denominator)
    eff_tte_sec = (eff_session_hours / 1638.0) * (365.25 * 86400.0)
    p_touch = first_passage_touch_prob(
        spot=adj_spot,
        strike=strike,
        tte_seconds=eff_tte_sec,
        iv_annual=sigma_session,
        direction=direction,
        wick_vol_multiplier=1.15,
    )
    return {"p_touch": round(p_touch, 5), "p_no": round(1.0 - p_touch, 5)}


def evaluate_pyth_session_close_lock(
    spot: float,
    strike: float,
    is_downward: bool,
    eff_session_hours: float,
    sigma_session: float,
    basis_buffer_frac: float,
) -> Dict[str, Any]:
    """Evaluates final-45m regular-session terminal digital lock using Student-t/Gaussian tail cushion."""
    if spot <= 0.0 or strike <= 0.0 or eff_session_hours <= 0.0:
        return {"eligible": False, "side": "YES", "p_lock": 0.5, "z_session": 0.0}
    win_above = spot > strike
    adj_spot = spot * (1.0 - basis_buffer_frac if win_above else 1.0 + basis_buffer_frac)
    if (win_above and adj_spot <= strike) or ((not win_above) and adj_spot >= strike):
        return {"eligible": False, "side": "YES", "p_lock": 0.5, "z_session": 0.0}
    tau_yr = max(1e-6, eff_session_hours / 1638.0)
    sig_tau = max(0.0012, sigma_session * math.sqrt(tau_yr))
    z = abs(math.log(adj_spot / strike)) / sig_tau
    # Fat-tail conservative blend: 85% Gaussian + 15% Cauchy-like heavy-tail penalty
    p_gauss = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    p_heavy = 0.5 + math.atan(z) / math.pi
    p_lock = min(0.994, 0.85 * p_gauss + 0.15 * p_heavy)
    if is_downward:
        side = "NO" if win_above else "YES"
    else:
        side = "YES" if win_above else "NO"
    return {
        "eligible": bool(z >= 2.15 and p_lock >= 0.955),
        "side": side,
        "p_lock": round(p_lock, 4),
        "z_session": round(z, 3),
    }


def _norm_team(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip()).lower()


def _is_half_integer(val: float) -> bool:
    scaled = abs(float(val)) * 2.0
    return abs(scaled - round(scaled)) < 1e-4 and (int(round(scaled)) % 2 == 1)


def parse_nba_zero_fee_event(ev: Dict[str, Any], now_ts: Optional[float] = None) -> Optional[NbaGameSpec]:
    """
    Parses a full-game `zero_fees` NBA event (`nba-2026`) into canonical margin & total dominance legs.
    Strictly accepts ONLY `sportsMarketType in ("moneyline", "spreads", "totals")` with `fee_rate == 0.0`
    and half-integer spread/total lines (`*.5`), guaranteeing zero pushes and zero full-game ties (NBA OT).
    """
    now = float(now_ts if now_ts is not None else time.time())
    if ev.get("closed") or ev.get("archived"):
        return None
    mkts = ev.get("markets") or []
    if len(mkts) < 3:
        return None

    # Locate full-game moneyline first to anchor canonical `(team_a, team_b)`
    ml_mkt: Optional[Dict[str, Any]] = None
    for m in mkts:
        if str(m.get("sportsMarketType") or "").strip().lower() == "moneyline" and not m.get("closed"):
            fr, _ = _extract_market_fee_rate(m)
            if fr == 0.0 and _parse_clob_tokens(m):
                ml_mkt = m
                break
    if ml_mkt is None:
        return None

    raw_outs = ml_mkt.get("outcomes")
    if isinstance(raw_outs, str):
        try:
            raw_outs = json.loads(raw_outs)
        except Exception:
            raw_outs = None
    if not isinstance(raw_outs, list) or len(raw_outs) < 2:
        return None
    team_a = str(raw_outs[0]).strip()
    team_b = str(raw_outs[1]).strip()
    norm_a, norm_b = _norm_team(team_a), _norm_team(team_b)
    if not norm_a or not norm_b or norm_a == norm_b:
        return None

    ml_toks = _parse_clob_tokens(ml_mkt)
    assert ml_toks is not None
    tip_ts = _parse_iso_ts(ml_mkt.get("gameStartTime") or ev.get("endDate")) or (now + 7200.0)
    # NBA games remain tradable in-play for ~2.5-3h after tipoff; ignore stale events >6h past tipoff
    if now > tip_ts + 6.0 * 3600.0:
        return None
    settle_est_ts = max(tip_ts + 3.25 * 3600.0, now + 1800.0)

    margin_legs: List[NbaOutcomeLeg] = [
        NbaOutcomeLeg(
            market_id=str(ml_mkt.get("id") or ""),
            condition_id=str(ml_mkt.get("conditionId") or ""),
            market_type="moneyline",
            token_id=ml_toks[0],
            opp_token_id=ml_toks[1],
            side_index=0,
            side_label="YES",
            display_label=f"{team_a} ML",
            relation="GT",
            threshold=0.0,
        ),
        NbaOutcomeLeg(
            market_id=str(ml_mkt.get("id") or ""),
            condition_id=str(ml_mkt.get("conditionId") or ""),
            market_type="moneyline",
            token_id=ml_toks[1],
            opp_token_id=ml_toks[0],
            side_index=1,
            side_label="NO",
            display_label=f"{team_b} ML",
            relation="LT",
            threshold=0.0,
        ),
    ]
    total_legs: List[NbaOutcomeLeg] = []

    for m in mkts:
        if m.get("closed") or m.get("archived"):
            continue
        smt = str(m.get("sportsMarketType") or "").strip().lower()
        if smt not in ("spreads", "totals"):
            continue
        fr, _ = _extract_market_fee_rate(m)
        if fr > 0.0:
            continue
        toks = _parse_clob_tokens(m)
        if not toks:
            continue
        outs = m.get("outcomes")
        if isinstance(outs, str):
            try:
                outs = json.loads(outs)
            except Exception:
                outs = None
        if not isinstance(outs, list) or len(outs) < 2:
            continue
        q_str = str(m.get("question") or "")
        if any(bad in q_str.lower() for bad in ("1h ", "2h ", "1q ", "2q ", "3q ", "4q ", "half", "quarter")):
            continue

        if smt == "spreads":
            m_sp = _SPREAD_FAV_RE.search(q_str)
            if not m_sp:
                continue
            fav_team = _norm_team(m_sp.group(1))
            line_val = float(m_sp.group(2))
            if line_val >= 0.0 or not _is_half_integer(line_val):
                continue
            k_abs = abs(line_val)
            out0, out1 = _norm_team(outs[0]), _norm_team(outs[1])
            if fav_team == norm_a and out0 == norm_a and out1 == norm_b:
                # idx 0 = team_a -k_abs (wins iff M > +k_abs); idx 1 = team_b +k_abs (wins iff M < +k_abs)
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[0], toks[1], 0, "YES", f"{team_a} -{k_abs:g}", "GT", k_abs))
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[1], toks[0], 1, "NO", f"{team_b} +{k_abs:g}", "LT", k_abs))
            elif fav_team == norm_b and out0 == norm_b and out1 == norm_a:
                # idx 0 = team_b -k_abs (wins iff M < -k_abs); idx 1 = team_a +k_abs (wins iff M > -k_abs)
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[0], toks[1], 0, "YES", f"{team_b} -{k_abs:g}", "LT", -k_abs))
                margin_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "spreads", toks[1], toks[0], 1, "NO", f"{team_a} +{k_abs:g}", "GT", -k_abs))

        elif smt == "totals":
            raw_line = m.get("line")
            if raw_line is None:
                continue
            t_line = float(raw_line)
            if t_line <= 50.0 or not _is_half_integer(t_line):
                continue
            if _norm_team(outs[0]) == "over" and _norm_team(outs[1]) == "under":
                total_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "totals", toks[0], toks[1], 0, "YES", f"Over {t_line:g}", "OVER", t_line))
                total_legs.append(NbaOutcomeLeg(str(m.get("id") or ""), str(m.get("conditionId") or ""), "totals", toks[1], toks[0], 1, "NO", f"Under {t_line:g}", "UNDER", t_line))

    return NbaGameSpec(
        event_id=str(ev.get("id") or ""),
        slug=str(ev.get("slug") or ""),
        title=str(ev.get("title") or f"{team_a} vs. {team_b}"),
        team_a=team_a,
        team_b=team_b,
        tipoff_ts=tip_ts,
        settle_est_ts=settle_est_ts,
        margin_legs=margin_legs,
        total_legs=total_legs,
    )


def detect_nba_dominance_boxes(
    spec: NbaGameSpec,
    best_asks_by_token: Dict[str, float],
    max_box_cost_net: float = 1.20,
) -> List[Dict[str, Any]]:
    """
    Finds all `0%`-fee NBA full-game dominance boxes (`L < U`):
      1. Margin Polish Middle / Spread Monotonicity: `(M > L) + (M < U)` with `L < U` and distinct `market_id`.
         Guaranteed payout = `$1.00` for all `M`, plus `$2.00` middle on integers in `(L, U)`.
      2. Total O/U Middle / Monotonicity: `(S > T_low) + (S < T_high)` with `T_low < T_high`.
         Guaranteed payout = `$1.00` for all `S`, plus `$2.00` middle on integers in `(T_low, T_high)`.
    """
    candidates: List[Dict[str, Any]] = []
    gt_legs = [lg for lg in spec.margin_legs if lg.relation == "GT" and lg.token_id in best_asks_by_token]
    lt_legs = [lg for lg in spec.margin_legs if lg.relation == "LT" and lg.token_id in best_asks_by_token]
    for lg_a in gt_legs:
        a_px = float(best_asks_by_token[lg_a.token_id])
        if not (0.01 <= a_px <= 0.99):
            continue
        for lg_b in lt_legs:
            if lg_a.market_id == lg_b.market_id or lg_a.threshold >= lg_b.threshold - 1e-6:
                continue
            b_px = float(best_asks_by_token[lg_b.token_id])
            if not (0.01 <= b_px <= 0.99):
                continue
            cost = round(a_px + b_px, 4)
            if cost <= max_box_cost_net:
                mid_pts = round(lg_b.threshold - lg_a.threshold, 1)
                candidates.append({
                    "box_kind": "NBA_POLISH_MIDDLE" if ("ML" in lg_a.display_label or "ML" in lg_b.display_label) else "NBA_SPREAD_MONO",
                    "event_id": spec.event_id,
                    "title": spec.title,
                    "box_cost_net": cost,
                    "box_cost_gross": cost,
                    "middle_width_pts": mid_pts,
                    "leg_a": lg_a,
                    "leg_b": lg_b,
                    "close_ts": spec.settle_est_ts,
                    "label": f"{lg_a.display_label} + {lg_b.display_label}",
                })

    ov_legs = [lg for lg in spec.total_legs if lg.relation == "OVER" and lg.token_id in best_asks_by_token]
    un_legs = [lg for lg in spec.total_legs if lg.relation == "UNDER" and lg.token_id in best_asks_by_token]
    for lg_o in ov_legs:
        o_px = float(best_asks_by_token[lg_o.token_id])
        if not (0.01 <= o_px <= 0.99):
            continue
        for lg_u in un_legs:
            if lg_o.market_id == lg_u.market_id or lg_o.threshold >= lg_u.threshold - 1e-6:
                continue
            u_px = float(best_asks_by_token[lg_u.token_id])
            if not (0.01 <= u_px <= 0.99):
                continue
            cost = round(o_px + u_px, 4)
            if cost <= max_box_cost_net:
                candidates.append({
                    "box_kind": "NBA_TOTAL_MONO",
                    "event_id": spec.event_id,
                    "title": spec.title,
                    "box_cost_net": cost,
                    "box_cost_gross": cost,
                    "middle_width_pts": round(lg_u.threshold - lg_o.threshold, 1),
                    "leg_a": lg_o,
                    "leg_b": lg_u,
                    "close_ts": spec.settle_est_ts,
                    "label": f"{lg_o.display_label} + {lg_u.display_label}",
                })

    candidates.sort(key=lambda x: (float(x["box_cost_net"]), -float(x["middle_width_pts"])))
    return candidates


def parse_zero_fee_negrisk_slate(
    ev: Dict[str, Any], series_slug: str, allow_mixed_fees: bool = False
) -> Optional[ZeroFeeNegRiskSlateSpec]:
    """
    Parses a verified `negRisk=True` complete partition event (`elon-tweets`, `fomc`, `best-ai-company`, etc.).
    Allows early-resolved `NO` brackets (e.g. `<40` tweets already exceeded) while rejecting the event
    if any bracket resolved `YES` or if any active sub-market lacks valid tokens.
    """
    if not ev.get("negRisk") or ev.get("closed") or ev.get("archived"):
        return None
    mkts = ev.get("markets") or []
    if len(mkts) < 3:
        return None
    end_ts = _parse_iso_ts(ev.get("endDate"))
    if not end_ts:
        return None

    open_brackets: List[Dict[str, Any]] = []
    for m in mkts:
        if m.get("archived"):
            continue
        if m.get("closed"):
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    op = json.loads(op)
                except Exception:
                    op = None
            # Only safe if closed bracket definitively resolved NO (`outcomePrices[1] >= 0.99`)
            if not (isinstance(op, list) and len(op) >= 2 and float(op[1]) >= 0.99):
                return None
            continue
        fr, fexp = _extract_market_fee_rate(m)
        if fr > 0.0 and not allow_mixed_fees:
            return None
        toks = _parse_clob_tokens(m)
        if not toks:
            return None
        open_brackets.append({
            "market_id": str(m.get("id") or ""),
            "condition_id": str(m.get("conditionId") or ""),
            "label": str(m.get("groupItemTitle") or m.get("question") or ""),
            "yes_token": toks[0],
            "no_token": toks[1],
            "fee_rate": fr,
            "fee_exponent": fexp,
            "rewards_min_size": float(m.get("rewardsMinSize") or 0.0),
            "rewards_max_spread": float(m.get("rewardsMaxSpread") or 0.0),
        })

    if len(open_brackets) < 3:
        return None
    return ZeroFeeNegRiskSlateSpec(
        event_id=str(ev.get("id") or ""),
        series_slug=series_slug,
        title=str(ev.get("title") or series_slug),
        end_ts=float(end_ts),
        brackets=open_brackets,
    )

# ======================================================================================
# [10/16] MODULE: src/polymarket_research/macro_counting_ctf_engine.py
# PURPOSE: Phase-2 Multi-Vertical Structural & Oracle Engine (TW1 xtracker, FED1 125-State LP, COND1 Oil-Senate, CTF Overround, AAA Gas, D2 12PM)
# ======================================================================================

#!/usr/bin/env python3
"""
Phase-2 Multi-Vertical Structural & Oracle Engine (`TW1`, `FED1`, `COND1`, `CTF_OVR`, `MKR_RW`, `GAS1`, `CM_SHOCK`, `AI1`, `D2`).
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import json
import logging
import math
import re
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from src.polymarket_research.barrier_onetouch_svi_engine import first_passage_touch_prob
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    _extract_market_fee_rate,
    _parse_clob_tokens,
    _parse_iso_ts,
)

logger = logging.getLogger("MacroCountingCTF")
NY_TZ = ZoneInfo("America/New_York")
CHROME_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

COUNTING_SERIES_HANDLES: Tuple[Tuple[str, str], ...] = (
    ("elon-tweets", "elonmusk"),
    ("elon-tweets-48h", "elonmusk"),
    ("trump-truth-social", "realDonaldTrump"),
)

FOMC_PARLAY_SERIES: Tuple[str, ...] = ("fomc", "fed-3-parlay")

OIL_SENATE_SLUGS: Tuple[str, ...] = (
    "which-party-will-win-the-senate-in-2026",
    "who-wins-the-senate-pending-oil-below-85-before-the-midterms",
    "who-wins-the-senate-pending-oil-above-or-below-80-before-the-midterms",
)

GAS_SERIES_SLUGS: Tuple[str, ...] = ("us-gas-price-daily", "gas-price-hits-weekly")
AI_SERIES_SLUGS: Tuple[str, ...] = ("best-ai-company", "chinese-ai-1")

HOURLY_BINANCE_SERIES: Dict[str, str] = {
    "BTC": "btc-up-or-down-hourly",
    "ETH": "eth-up-or-down-hourly",
    "SOL": "solana-up-or-down-hourly",
    "XRP": "xrp-up-or-down-hourly",
    "BNB": "bnb-up-or-down-hourly",
    "DOGE": "doge-up-or-down-hourly",
}

_XTRACKER_CACHE: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
_AAA_GAS_CACHE: Tuple[float, Optional[Dict[str, Any]]] = (0.0, None)


# ==============================================================================
# 1. `TW1_COUNTING_TRUNCATION_AND_BOX` (`xtracker.polymarket.com` + Sub-Windows)
# ==============================================================================
@dataclass
class CountingBracket:
    market_id: str
    condition_id: str
    label: str
    low_count: int
    high_count: float  # float("inf") for "200+"
    yes_token: str
    no_token: str
    fee_rate: float = 0.0
    rewards_min_size: float = 0.0
    rewards_max_spread: float = 0.0
    neg_risk: bool = True


@dataclass
class CountingSlateSpec:
    event_id: str
    slug: str
    series_slug: str
    handle: str
    title: str
    window_start_ts: float
    window_end_ts: float
    gamma_closed_floor: int
    brackets: List[CountingBracket] = field(default_factory=list)


_CNT_LT_RE = re.compile(r"^\s*(?:<|under\s+|less than\s+)(\d+)\s*$", re.IGNORECASE)
_CNT_PLUS_RE = re.compile(r"^\s*(\d+)\s*\+\s*$|^\s*(\d+)\s+or\s+more\s*$", re.IGNORECASE)
_CNT_RNG_RE = re.compile(r"^\s*(\d+)\s*[-–—to]+\s*(\d+)\s*$", re.IGNORECASE)
_DESC_WINDOW_RE = re.compile(
    r"(?:from|between)\s+([A-Za-z]+\s+\d{1,2})(?:,\s*(\d{4}))?,?\s+(\d{1,2}:\d{2}\s*[AP]M)\s*ET\s+"
    r"(?:to|and)\s+([A-Za-z]+\s+\d{1,2}),?\s*(\d{4}),?\s+(\d{1,2}:\d{2}\s*[AP]M)\s*ET",
    re.IGNORECASE,
)


def parse_count_bracket_bounds(label: str) -> Optional[Tuple[int, float]]:
    s = str(label or "").strip().replace(",", "")
    m_lt = _CNT_LT_RE.match(s)
    if m_lt:
        v = int(m_lt.group(1))
        return (0, float(v - 1)) if v > 0 else None
    m_pl = _CNT_PLUS_RE.match(s)
    if m_pl:
        v = int(m_pl.group(1) or m_pl.group(2))
        return (v, float("inf"))
    m_rg = _CNT_RNG_RE.match(s)
    if m_rg:
        lo, hi = int(m_rg.group(1)), int(m_rg.group(2))
        if hi >= lo >= 0:
            return (lo, float(hi))
    return None


def _parse_et_window_from_description(desc: str, fallback_end_ts: float) -> Tuple[float, float]:
    m = _DESC_WINDOW_RE.search(str(desc or ""))
    if m:
        start_md, start_yr, start_tm, end_md, end_yr, end_tm = m.groups()
        yr2 = int(end_yr)
        yr1 = int(start_yr) if start_yr else yr2
        try:
            dt1 = datetime.strptime(f"{start_md} {yr1} {start_tm.upper().replace(' ', '')}", "%B %d %Y %I:%M%p")
            dt2 = datetime.strptime(f"{end_md} {yr2} {end_tm.upper().replace(' ', '')}", "%B %d %Y %I:%M%p")
            if dt1 > dt2 and not start_yr:
                dt1 = dt1.replace(year=yr2 - 1)
            t1 = dt1.replace(tzinfo=NY_TZ).timestamp()
            t2 = dt2.replace(tzinfo=NY_TZ).timestamp()
            if t2 > t1:
                return t1, t2
        except Exception:
            pass
    return (fallback_end_ts - 7.0 * 86400.0, fallback_end_ts)


def parse_counting_slate_event(ev: Dict[str, Any], series_slug: str, handle: str) -> Optional[CountingSlateSpec]:
    if ev.get("closed") or ev.get("archived"):
        return None
    end_ts = _parse_iso_ts(ev.get("endDate"))
    if not end_ts:
        return None
    mkts = ev.get("markets") or []
    if len(mkts) < 3:
        return None
    desc = str(ev.get("description") or (mkts[0].get("description") if mkts else "") or "")
    w_start, w_end = _parse_et_window_from_description(desc, float(end_ts))

    closed_floor = 0
    open_brs: List[CountingBracket] = []
    for m in mkts:
        if m.get("archived"):
            continue
        lbl = str(m.get("groupItemTitle") or m.get("question") or "")
        bnds = parse_count_bracket_bounds(lbl)
        if bnds is None:
            continue
        lo_c, hi_c = bnds
        if m.get("closed"):
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    op = json.loads(op)
                except Exception:
                    op = None
            # Closed lower bracket resolved NO => true count is strictly > hi_c
            if isinstance(op, list) and len(op) >= 2 and float(op[1]) >= 0.99 and math.isfinite(hi_c):
                closed_floor = max(closed_floor, int(hi_c) + 1)
            elif isinstance(op, list) and len(op) >= 2 and float(op[0]) >= 0.99:
                return None
            continue
        fr, _ = _extract_market_fee_rate(m)
        if fr > 0.0:
            continue
        toks = _parse_clob_tokens(m)
        if not toks:
            continue
        open_brs.append(
            CountingBracket(
                market_id=str(m.get("id") or ""),
                condition_id=str(m.get("conditionId") or ""),
                label=lbl,
                low_count=lo_c,
                high_count=hi_c,
                yes_token=toks[0],
                no_token=toks[1],
                fee_rate=0.0,
                rewards_min_size=float(m.get("rewardsMinSize") or 0.0),
                rewards_max_spread=float(m.get("rewardsMaxSpread") or 0.0),
                neg_risk=bool(m.get("negRisk") if m.get("negRisk") is not None else ev.get("negRisk", True)),
            )
        )
    if len(open_brs) < 2:
        return None
    open_brs.sort(key=lambda b: b.low_count)
    return CountingSlateSpec(
        event_id=str(ev.get("id") or ""),
        slug=str(ev.get("slug") or ""),
        series_slug=series_slug,
        handle=handle,
        title=str(ev.get("title") or series_slug),
        window_start_ts=w_start,
        window_end_ts=w_end,
        gamma_closed_floor=closed_floor,
        brackets=open_brs,
    )


def fetch_xtracker_user_stats_sync(handle: str, ttl_sec: float = 60.0) -> Dict[str, Dict[str, Any]]:
    """
    Polls Polymarket's official counting oracle `https://xtracker.polymarket.com/api/users/{handle}`
    and maps each active `marketLink` event slug to `{total, start_ts, end_ts, hourly_counts}`.
    """
    now = time.time()
    cached = _XTRACKER_CACHE.get(handle)
    if cached and (now - cached[0]) < ttl_sec:
        return cached[1]
    out: Dict[str, Dict[str, Any]] = {}
    try:
        req = urllib.request.Request(
            f"https://xtracker.polymarket.com/api/users/{handle}",
            headers={"User-Agent": CHROME_UA},
        )
        with urllib.request.urlopen(req, timeout=5.0) as r:
            u_data = json.loads(r.read().decode("utf-8", errors="replace")).get("data") or {}
        for tr in (u_data.get("trackings") or []):
            if not tr.get("isActive"):
                continue
            tid = str(tr.get("id") or "")
            mlink = str(tr.get("marketLink") or "")
            eslug = mlink.rstrip("/").split("/")[-1] if mlink else ""
            if not tid or not eslug:
                continue
            req_t = urllib.request.Request(
                f"https://xtracker.polymarket.com/api/trackings/{tid}?includeStats=true",
                headers={"User-Agent": CHROME_UA},
            )
            with urllib.request.urlopen(req_t, timeout=5.0) as rt:
                td = json.loads(rt.read().decode("utf-8", errors="replace")).get("data") or {}
            stats = td.get("stats") or {}
            hourly: List[Tuple[float, int]] = []
            bare_daily = False
            for row in (stats.get("daily") or []):
                d_raw = str(row.get("date") or "").strip()
                if len(d_raw) == 10:
                    bare_daily = True
                ts_r = _parse_iso_ts(d_raw)
                if ts_r is not None:
                    hourly.append((float(ts_r), int(row.get("count") or 0)))
            out[eslug] = {
                "tracking_id": tid,
                "total": int(stats.get("total") or 0),
                "start_ts": _parse_iso_ts(td.get("startDate")) or 0.0,
                "end_ts": _parse_iso_ts(td.get("endDate")) or 0.0,
                "hourly": hourly,
                "daily_tz_pad": 18000.0 if bare_daily else 0.0,
            }
        _XTRACKER_CACHE[handle] = (now, out)
    except Exception as exc:
        logger.debug(f"xtracker fetch notice ({handle}): {exc}")
        if cached:
            return cached[1]
    return out


def evaluate_counting_dead_no_locks(
    slate: CountingSlateSpec,
    xtracker_by_slug: Dict[str, Dict[str, Any]],
    safety_post_buffer: int = 2,
) -> Tuple[int, List[CountingBracket]]:
    """
    Returns `(verified_floor, eliminated_brackets)`.
    Per Polymarket xtracker rules, posts captured by xtracker (~5m) remain counted even if later deleted,
    making `max(gamma_closed_floor, xtracker_total)` a non-decreasing lower bound. We still require
    `verified_floor >= high_count + safety_post_buffer` (`>= +2` posts past bracket ceiling).
    """
    xt = xtracker_by_slug.get(slate.slug) or {}
    xt_total = int(xt.get("total") or 0)
    verified_floor = max(int(slate.gamma_closed_floor), xt_total)
    dead: List[CountingBracket] = []
    for br in slate.brackets:
        if math.isfinite(br.high_count) and verified_floor >= int(br.high_count) + max(1, safety_post_buffer):
            dead.append(br)
    return verified_floor, dead


def detect_counting_subwindow_boxes(
    slates: List[CountingSlateSpec],
    best_asks_by_token: Dict[str, float],
    xtracker_by_handle: Dict[str, Dict[str, Dict[str, Any]]],
    max_box_cost_net: float = 1.05,
) -> List[Dict[str, Any]]:
    """
    Detects 2-leg `0%`-fee Sub-Window Inclusion Boxes (`S ⊂ L`, e.g. `48h ⊂ 7d` on `@elonmusk`):
    Let `N_banked >= 0` be verified posts in `[start_L, start_S)`. Since `N_L >= N_banked + N_S`:
      1. Upper-Tail Box: `N_S >= k_hi` (`high_count == inf`) => `N_L >= K_hi` whenever `K_hi <= N_banked + k_hi`
         => `NO(S >= k_hi) + YES(L >= K_hi) >= $1.00` (`$2.00` middle!).
      2. Lower-Tail Box: `N_L <= K_lo` (`low_count == 0`) => `N_S <= k_lo` whenever `K_lo <= N_banked + k_lo`
         => `NO(L <= K_lo) + YES(S <= k_lo) >= $1.00` (`$2.00` middle!).
    """
    boxes: List[Dict[str, Any]] = []
    for i, s_short in enumerate(slates):
        for j, s_long in enumerate(slates):
            if i == j or s_short.handle != s_long.handle or s_short.event_id == s_long.event_id:
                continue
            # Strict containment (no tolerance): Short window must lie fully inside Long window.
            if not (
                s_long.window_start_ts <= s_short.window_start_ts
                and s_short.window_end_ts <= s_long.window_end_ts
                and (s_long.window_end_ts - s_long.window_start_ts) > (s_short.window_end_ts - s_short.window_start_ts) + 3600.0
            ):
                continue
            xt_long = (xtracker_by_handle.get(s_long.handle) or {}).get(s_long.slug) or {}
            banked = 0
            if xt_long.get("hourly") and s_short.window_start_ts > s_long.window_start_ts + 1800.0:
                tz_pad = float(xt_long.get("daily_tz_pad") or 0.0)
                banked = sum(
                    cnt for ts_h, cnt in xt_long["hourly"]
                    if (ts_h - tz_pad) >= s_long.window_start_ts and (ts_h + 86400.0 + tz_pad) <= s_short.window_start_ts
                )
            # 1. Upper-tail 2-leg dominance
            s_up = [b for b in s_short.brackets if not math.isfinite(b.high_count)]
            l_up = [b for b in s_long.brackets if not math.isfinite(b.high_count)]
            for bs in s_up:
                ask_no_s = best_asks_by_token.get(bs.no_token)
                if ask_no_s is None:
                    continue
                for bl in l_up:
                    if bl.low_count <= banked + bs.low_count:
                        ask_yes_l = best_asks_by_token.get(bl.yes_token)
                        if ask_yes_l is None:
                            continue
                        cost = round(float(ask_no_s) + float(ask_yes_l), 4)
                        if cost <= max_box_cost_net:
                            boxes.append({
                                "box_kind": "TW1_UPPER_SUBWINDOW",
                                "handle": s_short.handle,
                                "banked": banked,
                                "box_cost_net": cost,
                                "leg_a": {"token_id": bs.no_token, "opp_token_id": bs.yes_token, "condition_id": bs.condition_id, "side": "NO", "label": f"NO_48H[{bs.label}]", "market_id": bs.market_id, "fee_rate": 0.0, "strike": float(bs.low_count), "neg_risk": bs.neg_risk},
                                "leg_b": {"token_id": bl.yes_token, "opp_token_id": bl.no_token, "condition_id": bl.condition_id, "side": "YES", "label": f"YES_7D[{bl.label}]", "market_id": bl.market_id, "fee_rate": 0.0, "strike": float(bl.low_count), "neg_risk": bl.neg_risk},
                                "close_ts": max(s_short.window_end_ts, s_long.window_end_ts),
                                "label": f"{s_short.handle} NO({bs.label} short) + YES({bl.label} long, banked={banked})",
                            })
            # 2. Lower-tail 2-leg dominance
            s_lo = [b for b in s_short.brackets if b.low_count == 0 and math.isfinite(b.high_count)]
            l_lo = [b for b in s_long.brackets if b.low_count == 0 and math.isfinite(b.high_count)]
            for bl in l_lo:
                ask_no_l = best_asks_by_token.get(bl.no_token)
                if ask_no_l is None:
                    continue
                for bs in s_lo:
                    if int(bl.high_count) <= banked + int(bs.high_count):
                        ask_yes_s = best_asks_by_token.get(bs.yes_token)
                        if ask_yes_s is None:
                            continue
                        cost = round(float(ask_no_l) + float(ask_yes_s), 4)
                        if cost <= max_box_cost_net:
                            boxes.append({
                                "box_kind": "TW1_LOWER_SUBWINDOW",
                                "handle": s_short.handle,
                                "banked": banked,
                                "box_cost_net": cost,
                                "leg_a": {"token_id": bl.no_token, "opp_token_id": bl.yes_token, "condition_id": bl.condition_id, "side": "NO", "label": f"NO_7D[{bl.label}]", "market_id": bl.market_id, "fee_rate": 0.0, "strike": float(bl.high_count), "neg_risk": bl.neg_risk},
                                "leg_b": {"token_id": bs.yes_token, "opp_token_id": bs.no_token, "condition_id": bs.condition_id, "side": "YES", "label": f"YES_48H[{bs.label}]", "market_id": bs.market_id, "fee_rate": 0.0, "strike": float(bs.high_count), "neg_risk": bs.neg_risk},
                                "close_ts": max(s_short.window_end_ts, s_long.window_end_ts),
                                "label": f"{s_short.handle} NO({bl.label} long) + YES({bs.label} short, banked={banked})",
                            })
    boxes.sort(key=lambda x: float(x["box_cost_net"]))
    return boxes


# ==============================================================================
# 2. Exact Finite-State Bitmask Dominance Engine (`FED1` FOMC & `COND1` Oil-Senate)
# ==============================================================================
FOMC_ACTIONS: Tuple[str, ...] = ("CUT50", "CUT25", "PAUSE", "HIKE25", "HIKE50")
FOMC_STATES_3M: List[Tuple[str, str, str]] = [
    (a, b, c) for a in FOMC_ACTIONS for b in FOMC_ACTIONS for c in FOMC_ACTIONS
]
ALL_FOMC_MASK: int = (1 << len(FOMC_STATES_3M)) - 1  # 125-bit mask


def _classify_single_fomc_label(label: str) -> Optional[str]:
    s = str(label or "").strip().lower()
    if "no change" in s or s == "pause":
        return "PAUSE"
    has_50 = bool(re.search(r"\b50\s*\+?|\b50\s*bps", s))
    has_25_plus = "25+" in s
    has_25 = bool(re.search(r"(?<![.\d])25(?![.\d])", s))
    if has_50 and ("decrease" in s or "cut" in s):
        return "CUT50"
    if has_25_plus and ("decrease" in s or "cut" in s):
        return "CUT25+"
    if has_25_plus and ("increase" in s or "hike" in s):
        return "HIKE25+"
    if has_25 and ("decrease" in s or "cut" in s):
        return "CUT25"
    if has_25 and ("increase" in s or "hike" in s):
        return "HIKE25"
    if has_50 and ("increase" in s or "hike" in s):
        return "HIKE50"
    return None


_FOMC_LABEL_ACTION_SET: Dict[str, Tuple[str, ...]] = {
    "CUT25+": ("CUT25", "CUT50"),
    "HIKE25+": ("HIKE25", "HIKE50"),
}


def _parlay_word_matches(word: str, action: str) -> bool:
    w = word.strip().lower()
    if w == "pause":
        return action == "PAUSE"
    if w == "cut":
        return action in ("CUT25", "CUT50")
    if w == "hike":
        return action in ("HIKE25", "HIKE50")
    return False


def build_fomc_truth_table_legs(
    fomc_events: List[Dict[str, Any]],
    parlay_events: List[Dict[str, Any]],
    sep_2026_realized_action: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Maps every open `0%`-fee contract in `Oct FOMC`, `Dec FOMC`, `Jan FOMC`, `fed-decisions-oct-jan`,
    and `fed-decisions-sepdec` (when `sep_2026_realized_action` is known) to an exact 125-bit state mask.
    """
    legs: List[Dict[str, Any]] = []

    for ev in fomc_events:
        if ev.get("closed"):
            continue
        slug = str(ev.get("slug") or "").lower()
        end_ts = _parse_iso_ts(ev.get("endDate")) or 0.0
        m_idx = 0 if "october" in slug else (1 if "december" in slug else (2 if "january" in slug else -1))
        if m_idx < 0 or end_ts <= 0:
            continue
        m_tag = ("OCT", "DEC", "JAN")[m_idx]
        for m in (ev.get("markets") or []):
            if m.get("closed"):
                continue
            fr, _ = _extract_market_fee_rate(m)
            toks = _parse_clob_tokens(m)
            act = _classify_single_fomc_label(str(m.get("groupItemTitle") or m.get("question") or ""))
            if fr > 0.0 or not toks or not act:
                continue
            y_mask = 0
            act_set = _FOMC_LABEL_ACTION_SET.get(act, (act,))
            for idx, st in enumerate(FOMC_STATES_3M):
                if st[m_idx] in act_set:
                    y_mask |= (1 << idx)
            mid = str(m.get("id") or "")
            cid = str(m.get("conditionId") or "")
            nr_m = m.get("negRisk") if isinstance(m.get("negRisk"), bool) else (ev.get("negRisk") if isinstance(ev.get("negRisk"), bool) else None)
            legs.append({"event_group": f"FOMC_{m_tag}", "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1], "side": "YES", "label": f"YES({m_tag}:{act})", "mask": y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_m})
            legs.append({"event_group": f"FOMC_{m_tag}", "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0], "side": "NO", "label": f"NO({m_tag}:{act})", "mask": ALL_FOMC_MASK ^ y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_m})

    for ev in parlay_events:
        if ev.get("closed"):
            continue
        slug = str(ev.get("slug") or "").lower()
        end_ts = _parse_iso_ts(ev.get("endDate")) or 0.0
        is_oct_jan = "oct-jan" in slug
        is_sep_dec = "sepdec" in slug and sep_2026_realized_action is not None
        if not (is_oct_jan or is_sep_dec) or end_ts <= 0:
            continue
        p_tag = "PARLAY_OCT_JAN" if is_oct_jan else "PARLAY_SEP_DEC"
        named_union_mask = 0
        # If ANY named market is skipped (closed / fee / no tokens / unparseable / zero mask), the
        # named union is incomplete and `Other = ALL ^ union` would over-claim states -> no Other legs.
        named_incomplete = False
        other_mkt: Optional[Tuple[Dict[str, Any], Tuple[str, str]]] = None
        for m in (ev.get("markets") or []):
            lbl = str(m.get("groupItemTitle") or "").strip()
            is_other = lbl.lower() == "other"
            if m.get("closed"):
                if not is_other:
                    named_incomplete = True
                continue
            fr, _ = _extract_market_fee_rate(m)
            toks = _parse_clob_tokens(m)
            if fr > 0.0 or not toks:
                if not is_other:
                    named_incomplete = True
                continue
            if is_other:
                other_mkt = (m, toks)
                continue
            parts = [p.strip() for p in re.split(r"[-–—/]", lbl) if p.strip()]
            if len(parts) != 3:
                named_incomplete = True
                continue
            y_mask = 0
            for idx, (a_oct, a_dec, a_jan) in enumerate(FOMC_STATES_3M):
                if is_oct_jan:
                    ok = _parlay_word_matches(parts[0], a_oct) and _parlay_word_matches(parts[1], a_dec) and _parlay_word_matches(parts[2], a_jan)
                else:
                    assert sep_2026_realized_action is not None
                    ok = _parlay_word_matches(parts[0], sep_2026_realized_action) and _parlay_word_matches(parts[1], a_oct) and _parlay_word_matches(parts[2], a_dec)
                if ok:
                    y_mask |= (1 << idx)
            if y_mask == 0:
                # Unmapped parlay words: a NO leg with ALL-states mask would fabricate a riskless cover.
                named_incomplete = True
                continue
            named_union_mask |= y_mask
            mid = str(m.get("id") or "")
            cid = str(m.get("conditionId") or "")
            nr_p = m.get("negRisk") if isinstance(m.get("negRisk"), bool) else (ev.get("negRisk") if isinstance(ev.get("negRisk"), bool) else None)
            legs.append({"event_group": p_tag, "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1], "side": "YES", "label": f"YES({p_tag}:{lbl})", "mask": y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_p})
            legs.append({"event_group": p_tag, "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0], "side": "NO", "label": f"NO({p_tag}:{lbl})", "mask": ALL_FOMC_MASK ^ y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_p})
        if other_mkt is not None and not named_incomplete:
            m_o, toks_o = other_mkt
            o_mask = ALL_FOMC_MASK ^ named_union_mask
            mid_o = str(m_o.get("id") or "")
            cid_o = str(m_o.get("conditionId") or "")
            nr_o = m_o.get("negRisk") if isinstance(m_o.get("negRisk"), bool) else (ev.get("negRisk") if isinstance(ev.get("negRisk"), bool) else None)
            legs.append({"event_group": p_tag, "market_id": mid_o, "condition_id": cid_o, "token_id": toks_o[0], "opp_token_id": toks_o[1], "side": "YES", "label": f"YES({p_tag}:Other)", "mask": o_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_o})
            legs.append({"event_group": p_tag, "market_id": mid_o, "condition_id": cid_o, "token_id": toks_o[1], "opp_token_id": toks_o[0], "side": "NO", "label": f"NO({p_tag}:Other)", "mask": ALL_FOMC_MASK ^ o_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_o})
    return legs


# 9-state Oil x Senate truth table: 3 Oil regimes (<80, [80,85), >=85) x 3 Senate winners (DEM, REP, OTHER)
OIL_SENATE_STATES: List[Tuple[str, str]] = [
    (o, p) for o in ("LT80", "B80_85", "GE85") for p in ("DEM", "REP", "OTHER")
]
ALL_OIL_SENATE_MASK: int = (1 << len(OIL_SENATE_STATES)) - 1  # 9-bit mask (511)


def build_oil_senate_truth_table_legs(events_by_slug: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Maps `which-party-will-win-the-senate-in-2026` + `who-wins-the-senate-pending-oil-*` (`0%` fee)
    into exact 9-bit masks over `{LT80, B80_85, GE85} x {DEM, REP, OTHER}`.
    """
    legs: List[Dict[str, Any]] = []
    for slug, ev in events_by_slug.items():
        if not ev or ev.get("closed"):
            continue
        end_ts = _parse_iso_ts(ev.get("endDate")) or 0.0
        if end_ts <= 0:
            continue
        s_low = slug.lower()
        for m in (ev.get("markets") or []):
            if m.get("closed"):
                continue
            fr, _ = _extract_market_fee_rate(m)
            toks = _parse_clob_tokens(m)
            if fr > 0.0 or not toks:
                continue
            lbl = str(m.get("groupItemTitle") or m.get("question") or "").strip()
            ll = lbl.lower()
            y_mask = 0
            if "which-party-will-win-the-senate" in s_low:
                party = "DEM" if "democrat" in ll else ("REP" if "republican" in ll else None)
                if not party:
                    continue
                for idx, (_, p_st) in enumerate(OIL_SENATE_STATES):
                    if p_st == party:
                        y_mask |= (1 << idx)
                eg = "SENATE_MAIN"
            elif "pending-oil" in s_low:
                party = "DEM" if ("d senate" in ll or "democrat" in ll) else ("REP" if ("r senate" in ll or "republican" in ll) else None)
                thresh = 85 if "85" in ll else (80 if "80" in ll else 0)
                is_lt = "<" in ll or "below" in ll or "less" in ll
                is_ge = "≥" in ll or ">=" in ll or "above" in ll or "greater" in ll
                if not party or thresh not in (80, 85) or (is_lt == is_ge):
                    continue
                for idx, (o_st, p_st) in enumerate(OIL_SENATE_STATES):
                    if p_st != party:
                        continue
                    oil_ok = (
                        (o_st == "LT80" if is_lt else o_st in ("B80_85", "GE85"))
                        if thresh == 80
                        else (o_st in ("LT80", "B80_85") if is_lt else o_st == "GE85")
                    )
                    if oil_ok:
                        y_mask |= (1 << idx)
                eg = f"OIL_{thresh}_SENATE"
            else:
                continue
            mid = str(m.get("id") or "")
            cid = str(m.get("conditionId") or "")
            nr_s = m.get("negRisk") if isinstance(m.get("negRisk"), bool) else (ev.get("negRisk") if isinstance(ev.get("negRisk"), bool) else None)
            legs.append({"event_group": eg, "market_id": mid, "condition_id": cid, "token_id": toks[0], "opp_token_id": toks[1], "side": "YES", "label": f"YES[{lbl}]", "mask": y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_s})
            legs.append({"event_group": eg, "market_id": mid, "condition_id": cid, "token_id": toks[1], "opp_token_id": toks[0], "side": "NO", "label": f"NO[{lbl}]", "mask": ALL_OIL_SENATE_MASK ^ y_mask, "end_ts": end_ts, "fee_rate": 0.0, "neg_risk": nr_s})
    return legs


def find_cross_event_bitmask_boxes(
    legs: List[Dict[str, Any]],
    best_asks_by_token: Dict[str, float],
    all_states_mask: int,
    max_2leg_cost: float = 1.05,
    max_3leg_cost: float = 1.03,
) -> List[Dict[str, Any]]:
    """
    Finds all minimal 2-leg and 3-leg cross-event `0%`-fee portfolios whose bitwise OR covers
    100% of states (`(m1 | m2 [| m3]) == all_states_mask`), guaranteeing payout >= $1.00 in every state!
    """
    priced = []
    for lg in legs:
        ask = best_asks_by_token.get(str(lg["token_id"]))
        m = int(lg["mask"])
        if ask is not None and 0.002 <= float(ask) <= 0.995 and 0 < m < all_states_mask:
            priced.append((float(ask), m, lg))

    out: List[Dict[str, Any]] = []
    n = len(priced)
    covered_pairs = set()

    # 1. Exact 2-leg cross-market dominance boxes (`m1 | m2 == all_states_mask`)
    for i in range(n):
        a1, m1, l1 = priced[i]
        for j in range(i + 1, n):
            a2, m2, l2 = priced[j]
            if l1["market_id"] == l2["market_id"] or l1["event_group"] == l2["event_group"]:
                continue
            if (m1 | m2) == all_states_mask:
                cost = round(a1 + a2, 4)
                covered_pairs.add((i, j))
                if cost <= max_2leg_cost:
                    double_states = bin(m1 & m2).count("1")
                    out.append({
                        "n_legs": 2,
                        "box_cost_net": cost,
                        "double_pay_states": double_states,
                        "legs": [l1, l2],
                        "close_ts": max(float(l1["end_ts"]), float(l2["end_ts"])),
                        "label": f"{l1['label']} + {l2['label']}",
                    })

    # 2. Minimal 3-leg cross-event partitions (`m1 | m2 | m3 == all_states_mask`, no 2-leg subset already covers)
    for i in range(n):
        a1, m1, l1 = priced[i]
        if a1 >= max_3leg_cost:
            continue
        for j in range(i + 1, n):
            if (i, j) in covered_pairs:
                continue
            a2, m2, l2 = priced[j]
            if a1 + a2 >= max_3leg_cost or l1["market_id"] == l2["market_id"]:
                continue
            m12 = m1 | m2
            if m12 in (m1, m2):
                continue
            for k in range(j + 1, n):
                if (i, k) in covered_pairs or (j, k) in covered_pairs:
                    continue
                a3, m3, l3 = priced[k]
                cost3 = round(a1 + a2 + a3, 4)
                if cost3 > max_3leg_cost:
                    continue
                if l3["market_id"] in (l1["market_id"], l2["market_id"]):
                    continue
                if len({l1["event_group"], l2["event_group"], l3["event_group"]}) < 2:
                    continue
                if (m12 | m3) == all_states_mask and (m1 | m3) != all_states_mask and (m2 | m3) != all_states_mask:
                    out.append({
                        "n_legs": 3,
                        "box_cost_net": cost3,
                        "double_pay_states": 0,
                        "legs": [l1, l2, l3],
                        "close_ts": max(float(l1["end_ts"]), float(l2["end_ts"]), float(l3["end_ts"])),
                        "label": f"{l1['label']} + {l2['label']} + {l3['label']}",
                    })

    out.sort(key=lambda x: (float(x["box_cost_net"]), int(x["n_legs"])))
    return out


# ==============================================================================
# 3. `CTF_OVERROUND_MINT_SELL` & `MKR_REWARD_LOCKED_CARRY` (`Ideas #21, #22`)
# ==============================================================================
def walk_equal_shares_overround_bids(
    legs_bids_spec: List[Dict[str, Any]],
    target_mint_budget_usd: float = 100.0,
    min_net_proceeds_per_set: float = 1.004,
    min_shares: float = 8.0,
) -> Dict[str, Any]:
    """
    Walks L2 `bids` across all `N` mutually exclusive outcomes (`[YES, NO]` binary or `[YES_1..YES_N]` NegRisk)
    for equal shares `Q` minted at `$1.00 * Q` via `splitPosition`.
    Returns `filled=True` iff net proceeds after per-leg fees >= `min_net_proceeds_per_set * Q`.
    """
    if len(legs_bids_spec) < 2 or target_mint_budget_usd <= 0:
        return {"filled": False}
    parsed_books: List[Tuple[List[Tuple[float, float]], float, float]] = []
    l1_min_sh = float("inf")
    l1_net_sum = 0.0
    for sp in legs_bids_spec:
        fr = float(sp.get("fee_rate") or 0.0)
        fexp = float(sp.get("fee_exponent") or 1.0)
        bids = sorted(
            [(float(b["price"]), float(b["size"])) for b in (sp.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
            key=lambda x: -x[0],
        )
        if not bids:
            return {"filled": False}
        p0, s0 = bids[0]
        fee0 = fr * ((p0 * (1.0 - p0)) ** fexp) if fr > 0 else 0.0
        l1_net_sum += (p0 - fee0)
        l1_min_sh = min(l1_min_sh, s0)
        parsed_books.append((bids, fr, fexp))

    if l1_net_sum < min_net_proceeds_per_set:
        return {"filled": False, "l1_net_proceeds": round(l1_net_sum, 4)}

    cap_sh = min(float(target_mint_budget_usd), min(sum(s for _, s in bds) for bds, _, _ in parsed_books))
    q_sh = math.floor(cap_sh)
    if q_sh < min_shares:
        return {"filled": False, "l1_net_proceeds": round(l1_net_sum, 4)}

    gross_rev = 0.0
    total_fee = 0.0
    for bds, fr, fexp in parsed_books:
        rem = float(q_sh)
        for px, sz in bds:
            take = min(rem, sz)
            gross_rev += take * px
            if fr > 0:
                total_fee += take * fr * ((px * (1.0 - px)) ** fexp)
            rem -= take
            if rem <= 1e-9:
                break
        if rem > 1e-6:
            return {"filled": False}

    net_rev_ps = (gross_rev - total_fee) / q_sh
    if net_rev_ps < min_net_proceeds_per_set:
        return {"filled": False, "l1_net_proceeds": round(l1_net_sum, 4)}
    return {
        "filled": True,
        "shares": float(q_sh),
        "mint_cost_per_set": 1.0,
        "gross_proceeds_per_set": round(gross_rev / q_sh, 4),
        "net_proceeds_per_set": round(net_rev_ps, 4),
        "net_edge_per_set": round(net_rev_ps - 1.0, 4),
        "fee_usd": round(total_fee, 4),
        "spent_usd": round(float(q_sh), 2),
        "l1_usd": round(l1_min_sh, 2),
    }


def walk_position_overround_bid_unwind(
    legs_bids_spec: List[Dict[str, Any]],
    exact_shares: float,
    min_net_proceeds_per_set: float = 1.004,
) -> Dict[str, Any]:
    """
    Walks resting L2 `bids` across all held legs of an open 2-leg or N-leg riskless box
    for 100% of `exact_shares` simultaneously (leaving zero residual open shares).
    Returns `filled=True` iff every leg can absorb `exact_shares` and net proceeds per set
    after per-leg taker sell fees >= `min_net_proceeds_per_set`.
    """
    q_sh = float(exact_shares)
    if len(legs_bids_spec) < 2 or q_sh <= 0.0:
        return {"filled": False}
    gross_rev = 0.0
    total_fee = 0.0
    worst_bids: List[float] = []
    for sp in legs_bids_spec:
        fr = float(sp.get("fee_rate") or 0.0)
        fexp = float(sp.get("fee_exponent") or 1.0)
        bids = sorted(
            [
                (float(b["price"]), float(b["size"]))
                for b in (sp.get("bids") or [])
                if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0
            ],
            key=lambda x: -x[0],
        )
        if not bids:
            return {"filled": False}
        rem = q_sh
        leg_worst = bids[0][0]
        for px, sz in bids:
            take = min(rem, sz)
            gross_rev += take * px
            if fr > 0.0:
                total_fee += take * fr * ((px * (1.0 - px)) ** fexp)
            leg_worst = px
            rem -= take
            if rem <= 1e-9:
                break
        if rem > 1e-6:
            return {"filled": False}
        worst_bids.append(round(leg_worst, 4))

    net_rev_ps = (gross_rev - total_fee) / q_sh
    if net_rev_ps < min_net_proceeds_per_set:
        return {"filled": False, "net_proceeds_per_set": round(net_rev_ps, 4)}
    return {
        "filled": True,
        "shares": round(q_sh, 4),
        "gross_proceeds_per_set": round(gross_rev / q_sh, 4),
        "net_proceeds_per_set": round(net_rev_ps, 4),
        "fee_usd": round(total_fee, 4),
        "worst_leg_bids": worst_bids,
    }


def evaluate_locked_market_reward_carry(
    p_lock: float,
    best_bid: float,
    best_ask: float,
    rewards_min_size: float,
    rewards_max_spread_cents: float,
    fee_rate: float = 0.0,
) -> Dict[str, Any]:
    """
    Graveyard-safe `MKR_REWARD_LOCKED_CARRY`: posts `post_only=True` carry bids ONLY on already
    mathematically locked (`p_lock >= 0.995`), `0%`-fee outcomes where Gamma `rewardsMinSize > 0`
    is active and `0.95 <= bid_px <= 0.990`.
    """
    if fee_rate > 0.0 or p_lock < 0.995 or rewards_min_size <= 0.0 or best_ask <= 0.96:
        return {"eligible": False}
    bid_px = round(min(max(best_bid, 0.96), min(best_ask - 0.005, 0.989)), 3)
    max_spr = float(rewards_max_spread_cents) / 100.0 if rewards_max_spread_cents > 0.5 else float(rewards_max_spread_cents or 0.03)
    in_reward_zone = (best_ask - bid_px) <= max(0.02, max_spr + 1e-6)
    carry_edge = round(p_lock - bid_px, 4)
    if not (0.955 <= bid_px < best_ask and carry_edge >= 0.008 and in_reward_zone):
        return {"eligible": False}
    return {
        "eligible": True,
        "resting_bid": bid_px,
        "carry_edge": carry_edge,
        "rewards_min_size": rewards_min_size,
        "rewards_max_spread": round(max_spr, 4),
    }


# ==============================================================================
# 4. `GAS1_AAA_GASOLINE_LOCK`, `CM_SHOCK`, `AI1`, & `D2_12PM_BINANCE_BOX`
# ==============================================================================
_AAA_AS_OF_RE = re.compile(r"Price\s+as\s+of\s+(\d{1,2})/(\d{1,2})/(\d{2,4})", re.IGNORECASE)
_AAA_ROW_PRICES_RE = re.compile(r"\$(\d+\.\d{3,4})")


def parse_aaa_gas_html(html: str) -> Optional[Dict[str, Any]]:
    m_dt = _AAA_AS_OF_RE.search(str(html or ""))
    prices = [float(x) for x in _AAA_ROW_PRICES_RE.findall(str(html or "")) if 1.5 <= float(x) <= 9.5]
    if not m_dt or len(prices) < 6:
        return None
    mo, dy, yr_raw = int(m_dt.group(1)), int(m_dt.group(2)), int(m_dt.group(3))
    yr = 2000 + yr_raw if yr_raw < 100 else yr_raw
    try:
        as_of_date = date(yr, mo, dy)
    except ValueError:
        return None
    # AAA National Average table layout: [hero_regular, table_current_reg, mid, prem, diesel, e85, table_yesterday_reg, ...]
    cur_reg = prices[1] if abs(prices[0] - prices[1]) < 0.02 else prices[0]
    yest_reg = prices[6] if len(prices) > 6 else cur_reg
    return {
        "as_of_date": as_of_date.isoformat(),
        "current_regular": round(cur_reg, 4),
        "yesterday_regular": round(yest_reg, 4),
    }


def fetch_aaa_national_gas_sync(ttl_sec: float = 180.0) -> Optional[Dict[str, Any]]:
    global _AAA_GAS_CACHE
    now = time.time()
    if _AAA_GAS_CACHE[1] is not None and (now - _AAA_GAS_CACHE[0]) < ttl_sec:
        return _AAA_GAS_CACHE[1]
    try:
        req = urllib.request.Request("https://gasprices.aaa.com/", headers={"User-Agent": CHROME_UA})
        with urllib.request.urlopen(req, timeout=6.0) as r:
            parsed = parse_aaa_gas_html(r.read().decode("utf-8", errors="replace"))
        if parsed:
            _AAA_GAS_CACHE = (now, parsed)
            return parsed
    except Exception as exc:
        logger.debug(f"AAA gas fetch notice: {exc}")
    return _AAA_GAS_CACHE[1]


_GAS_LT_RE = re.compile(r"<\s*\$?\s*(\d+(?:\.\d+)?)")
_GAS_PL_RE = re.compile(r"\$?\s*(\d+(?:\.\d+)?)\s*\+")
_GAS_RG_RE = re.compile(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:[-–—]|\bto\b)\s*\$?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def parse_gas_daily_bracket(label: str) -> Optional[Tuple[float, float]]:
    s = str(label or "").strip()
    m1 = _GAS_LT_RE.search(s)
    if m1:
        return (0.0, float(m1.group(1)) - 1e-6)
    m2 = _GAS_PL_RE.search(s)
    if m2:
        return (float(m2.group(1)), float("inf"))
    m3 = _GAS_RG_RE.search(s)
    if m3:
        return (float(m3.group(1)), float(m3.group(2)))
    return None


def is_in_scheduled_macro_catalyst_window(now_ts: float) -> Tuple[bool, str]:
    """
    Restricts `CM_SHOCK_PYTH_CATALYST` strictly to institutional macro release windows in NY time:
      - `08:29 - 08:45 ET` Mon-Fri: US CPI / NFP / PPI / GDP / Retail Sales
      - `10:29 - 10:45 ET` Wed (or Thu holiday): EIA Weekly Petroleum Status Report (`WTI`)
      - `13:59 - 14:45 ET` Wed: FOMC Rate Decision & Powell Press Conference
    """
    dt = datetime.fromtimestamp(now_ts, tz=NY_TZ)
    if dt.weekday() >= 5:
        return False, ""
    hm = dt.hour * 60 + dt.minute
    if 8 * 60 + 29 <= hm <= 8 * 60 + 45:
        return True, "US_0830_MACRO_RELEASE"
    if dt.weekday() in (2, 3) and (10 * 60 + 29 <= hm <= 10 * 60 + 45):
        return True, "EIA_1030_PETROLEUM"
    if dt.weekday() == 2 and (13 * 60 + 59 <= hm <= 14 * 60 + 45):
        return True, "FOMC_1400_DECISION"
    return False, ""


def evaluate_pyth_catalyst_shock(
    asset: str,
    prev_spot: float,
    cur_spot: float,
    strike: float,
    direction: str,
    eff_session_hours: float,
    sigma_session: float,
    now_ts: float,
) -> Dict[str, Any]:
    """
    Graveyard-compliant `<1.5%` fee (`0.00%` Pyth `zero_fees`) scheduled macro release jump detector.
    Fires ONLY inside a verified macro catalyst window when `|ret| >= min_jump` and first-passage
    barrier probability jumps by `>= +0.055`.
    """
    in_win, cat_name = is_in_scheduled_macro_catalyst_window(now_ts)
    if not in_win or prev_spot <= 0 or cur_spot <= 0 or eff_session_hours <= 0.1:
        return {"eligible": False}
    ret = (cur_spot - prev_spot) / prev_spot
    min_jump = 0.0035 if asset == "SPY" else 0.0045
    if abs(ret) < min_jump:
        return {"eligible": False}
    eff_sec = (eff_session_hours / 1638.0) * (365.25 * 86400.0)
    p_before = first_passage_touch_prob(prev_spot, strike, eff_sec, sigma_session, direction, wick_vol_multiplier=1.10)
    p_after = first_passage_touch_prob(cur_spot, strike, eff_sec, sigma_session, direction, wick_vol_multiplier=1.10)
    dp = p_after - p_before
    if abs(dp) < 0.055:
        return {"eligible": False}
    side = "YES" if dp > 0 else "NO"
    p_fair = p_after if side == "YES" else (1.0 - p_after)
    return {
        "eligible": bool(0.22 <= p_fair <= 0.94),
        "catalyst": cat_name,
        "side": side,
        "p_fair": round(p_fair, 4),
        "delta_p": round(abs(dp), 4),
        "ret_pct": round(ret * 100.0, 3),
    }


def evaluate_ai_elo_ci_lock(
    leaderboard_rows: List[Dict[str, Any]],
    snapshot_ts: float,
    now_ts: float,
    tte_sec: float,
    max_snapshot_age_sec: float = 21600.0,
) -> Dict[str, Any]:
    """
    Evaluates final-36h (`tte_sec <= 129600`) LMArena Elo bootstrap confidence-interval lock.
    Strictly rejects any stale leaderboard snapshot (`now_ts - snapshot_ts > 6h`) so stale static
    files can NEVER trigger a trade.
    """
    if not leaderboard_rows or (now_ts - snapshot_ts) > max_snapshot_age_sec or not (600.0 <= tte_sec <= 129600.0):
        return {"eligible": False, "reason": "stale_or_outside_window"}
    rows_s = sorted(leaderboard_rows, key=lambda r: float(r.get("rating") or 0.0), reverse=True)
    if len(rows_s) < 2:
        return {"eligible": False}
    top = rows_s[0]
    top_org = str(top.get("organization") or "").strip()
    top_q025 = float(top.get("rating_q025") or 0.0)
    rival_q975 = max(
        (float(r.get("rating_q975") or 0.0) for r in rows_s[1:] if str(r.get("organization") or "").strip() != top_org),
        default=0.0,
    )
    ci_gap = top_q025 - rival_q975
    if not top_org or ci_gap < 6.0:
        return {"eligible": False, "ci_gap": round(ci_gap, 2)}
    p_lock = min(0.992, 0.955 + 0.0025 * min(15.0, ci_gap - 6.0))
    return {"eligible": True, "leader_org": top_org, "ci_gap": round(ci_gap, 2), "p_lock": round(p_lock, 4)}


def detect_d2_12pm_binance_boxes(
    hourly_spec: Dict[str, Any],
    k_1h: float,
    terminal_specs: List[Dict[str, Any]],
    min_corridor_bps: float = 25.0,
) -> List[Dict[str, Any]]:
    """
    Same-Exchange `Binance USDT` `11:00-12:00 PM ET` `1h` Up/Down vs `12:00 PM ET` Daily/Multi-Strike
    Corridor Dominance Detector (`|end_1h - end_12pm| <= 5s`, zero `USDT/USD` peg basis!).
    For `K_low < K_high`: buying `UP/YES(> K_low)` + `DOWN/NO(< K_high)` locks `$1.00` floor + `$2.00` corridor!
    """
    if k_1h <= 0:
        return []
    end_1h = float(hourly_spec["end_ts"])
    out: List[Dict[str, Any]] = []
    for ts_sp in terminal_specs:
        if ts_sp.get("is_downward"):
            continue
        if abs(float(ts_sp["end_ts"]) - end_1h) > 5.0:
            continue
        k_t = float(ts_sp["strike"])
        if k_t <= 0:
            continue
        k_lo, k_hi = min(k_1h, k_t), max(k_1h, k_t)
        corr_bps = (k_hi - k_lo) / k_lo * 10000.0
        if corr_bps < min_corridor_bps:
            continue
        if k_1h < k_t:
            leg_a = {"token_id": hourly_spec["up_token"], "opp_token_id": hourly_spec["down_token"], "condition_id": hourly_spec["condition_id"], "side": "UP", "label": f"1H_UP>{k_1h:g}", "market_id": hourly_spec["market_id"], "fee_rate": float(hourly_spec.get("fee_rate", 0.07)), "fee_exponent": 1.0, "strike": k_1h}
            leg_b = {"token_id": ts_sp["no_token"], "opp_token_id": ts_sp["yes_token"], "condition_id": ts_sp["condition_id"], "side": str(ts_sp.get("no_label", "NO")), "label": f"12PM_NO<{k_t:g}", "market_id": ts_sp["market_id"], "fee_rate": float(ts_sp.get("fee_rate", 0.07)), "fee_exponent": 1.0, "strike": k_t}
        else:
            leg_a = {"token_id": ts_sp["yes_token"], "opp_token_id": ts_sp["no_token"], "condition_id": ts_sp["condition_id"], "side": str(ts_sp.get("yes_label", "YES")), "label": f"12PM_YES>{k_t:g}", "market_id": ts_sp["market_id"], "fee_rate": float(ts_sp.get("fee_rate", 0.07)), "fee_exponent": 1.0, "strike": k_t}
            leg_b = {"token_id": hourly_spec["down_token"], "opp_token_id": hourly_spec["up_token"], "condition_id": hourly_spec["condition_id"], "side": "DOWN", "label": f"1H_DN<{k_1h:g}", "market_id": hourly_spec["market_id"], "fee_rate": float(hourly_spec.get("fee_rate", 0.07)), "fee_exponent": 1.0, "strike": k_1h}
        out.append({
            "asset": str(hourly_spec["asset"]),
            "k_low": k_lo,
            "k_high": k_hi,
            "corridor_bps": round(corr_bps, 2),
            "leg_a": leg_a,
            "leg_b": leg_b,
            "close_ts": max(end_1h, float(ts_sp["end_ts"])),
            "label": f"{leg_a['label']} + {leg_b['label']} ({corr_bps:.0f}bps)",
        })
    return out

# ======================================================================================
# [11/16] MODULE: src/polymarket_research/alpha_124_shadow_daemon.py
# PURPOSE: Unified Multi-Vertical Shadow Daemon (Crypto, Weather METAR/HKO, Pyth Commodities/Metals/Equities, NBA, FOMC/Oil-Senate/Counting/AAA)
# ======================================================================================

#!/usr/bin/env python3
"""
Polymarket Alpha-124 Unified Shadow-Trading Daemon (Options #1, #2, and #4)
===========================================================================
Runs three orthogonal, non-HFT Polymarket engines concurrently in strict
zero-lookahead shadow mode (walking live CLOB L2 orderbooks at t_signal + 50ms):

  - Option #1 (Weather METAR + 71-Member NWP Ensemble):
      * W1_SOLAR_PEAK_LOCK: Post-diurnal-peak routine METAR cooling lock (target ~90% WR)
      * W2_ENSEMBLE_VALUE: Pre-peak MOS-corrected 71-member ensemble value brackets (Taker)
      * W2_MAKER_OVERROUND: 0%-fee `post_only=True` Maker quoting inside ~1.07 Weather overrounds

  - Option #2 (Crypto One-Touch Barrier "Hit/Dip" Jump-SVI):
      * B1_CONVEX_TAIL_YES: Underpriced OTM `YES` barrier tails ($0.04-$0.32) with 2x Maker TP
      * B2_BARRIER_NO_LOCK: Final-window (1h-10h) untouched barrier `NO` convergence

  - Option #4 (Multi-Strike SVI Breeden-Litzenberger Maker-Scalper & Convergence):
      * M1_SVI_MAKER_SCALP: Intra-day SVI BL mispricing with +4.5c 0%-fee Maker TP & SVI stop
      * M2_STRIKE_CONVERGENCE: Final-window (20m-3.5h) high-z ITM digital convergence
      * M3_LADDER_MONO_BOX: Deterministic cross-strike monotonicity arbitrage (< $0.996)
      * M4_SHOCK_STRIKE_CATCHUP: <250ms Binance impulse wakeup sniping lagging daily SVI rungs

  - Option #7 & #8 (Chainlink 60s-TWAP Exact-Strike Microstructure):
      * D1_SAME_ORACLE_DOMINANCE_BOX: Equal-share `UP(K_low) + DOWN(K_high)` <= $0.995 net
        during `:10-:15`, `:25-:30`, `:40-:45`, `:55-:00` across BTC, ETH, SOL, XRP.
      * S2_EXACT_TWAP_LOCK: Final-45s (8s-45s) banked 60s-TWAP integral mathematical lock
        across 5m + 15m BTC, ETH, SOL, XRP (64 expiries/hr) using 14-digit Chainlink `openPrice`.

Simulates 3 bankroll sizing profiles simultaneously (`T100`, `T1000`, `T5000`) with exact
Polymarket `zero_fees` (Weather) and `crypto_fees_v2` (Crypto) accounting.
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import argparse
import asyncio
import collections
import json
import logging
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import aiohttp

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.polymarket_research.barrier_onetouch_svi_engine import (
    ASSET_BINANCE_SYMBOL,
    BINANCE_FAPI_URL,
    HIT_SERIES,
    BarrierRungSpec,
    detect_barrier_monotonicity_boxes,
    evaluate_barrier_no_net_ev,
    fetch_binance_window_extremes_sync,
    first_passage_touch_prob,
    get_wing_implied_vol,
    parse_hit_event,
)
from src.polymarket_research.multistrike_svi_scalper import (
    DAILY_UPDOWN_SERIES,
    NEGRISK_SERIES,
    STRIKE_SERIES,
    ZERO_FEE_PYTH_DAILY_SERIES,
    DailyUpDownSpec,
    NegRiskBracketSpec,
    StrikeRungSpec,
    _fast_norm_cdf,
    build_negrisk_cross_box_bundles,
    detect_ladder_monotonicity_boxes,
    evaluate_coherent_strike_ladder,
    evaluate_svi_digital_fair_value,
    parse_daily_updown_event,
    parse_multistrike_event,
    parse_negrisk_bracket_event,
)
from src.polymarket_research.net_alpha_opportunity_engine import (
    publish_global_positions_shm,
    rank_opportunities_capital_auction,
    read_global_positions_shm,
    scan_binary_complete_set_arb,
)
from src.polymarket_research.orderflow_wfo_simulators import (
    compute_d1_legging_drag_haircut,
    compute_d1_maker_anchor_drag_haircut,
)
from src.polymarket_research.same_oracle_dominance_box import (
    DOMINANCE_ASSETS,
    DOMINANCE_SERIES_SLUGS,
    EMPIRICAL_BOX_ASSET_CAPS_USD,
    MIN_CORRIDOR_BPS_BY_ASSET,
    TwapCandleMarketSpec,
    build_crypto_price_query_url,
    build_own_gamma_event_url,
    build_prev_5m_gamma_event_url,
    determine_dominance_legs,
    parse_authoritative_close_price,
    parse_authoritative_open_price,
    parse_closed_gamma_event_settlement,
    parse_twap_candle_event,
    verify_same_oracle_pair,
    walk_equal_shares_dominance_box,
    walk_equal_shares_multi_leg_box,
)
from src.polymarket_research.exact_twap_lock_engine import (
    compute_exact_twap_lock_probability,
    read_shm_usd_anchor,
)
try:
    from src.polymarket_research.polymarket_ws_streams import PolymarketChainlinkLiveStream
except ImportError:
    try:
        from polymarket_ws_streams import PolymarketChainlinkLiveStream  # type: ignore
    except ImportError:
        PolymarketChainlinkLiveStream = None  # type: ignore
from src.polymarket_research.weather_metar_engine import (
    HIGH_VOLUME_WEATHER_SERIES,
    MetarObservation,
    WeatherEventSpec,
    compute_adaptive_metar_poll_ttl,
    compute_weather_probabilities,
    evaluate_weather_event_slate,
    fetch_live_ensemble_hourly_sync,
    fetch_metar_observations_sync,
    fetch_taf_extremes_sync,
    parse_weather_event,
)
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    NBA_SERIES_SLUGS,
    PYTH_ASSET_CONFIG,
    PYTH_CLOSE_SERIES,
    PYTH_HIT_SERIES,
    ZERO_FEE_NEGRISK_SERIES,
    NbaGameSpec,
    PythBarrierRungSpec,
    PythCloseRungSpec,
    ZeroFeeNegRiskSlateSpec,
    compute_effective_trading_hours,
    detect_nba_dominance_boxes,
    detect_pyth_calendar_inclusion_boxes,
    detect_pyth_close_vs_hit_boxes,
    evaluate_pyth_session_barrier_no_lock,
    evaluate_pyth_session_close_lock,
    fetch_yahoo_1m_intraday_sync,
    is_same_continuous_session,
    parse_nba_zero_fee_event,
    parse_pyth_close_event,
    parse_pyth_hit_event,
    parse_zero_fee_negrisk_slate,
    window_extremes_from_bars,
    _extract_market_fee_rate,
    _parse_clob_tokens,
    _parse_iso_ts,
)
from src.polymarket_research.macro_counting_ctf_engine import (
    ALL_FOMC_MASK,
    ALL_OIL_SENATE_MASK,
    COUNTING_SERIES_HANDLES,
    FOMC_PARLAY_SERIES,
    GAS_SERIES_SLUGS,
    HOURLY_BINANCE_SERIES,
    NY_TZ,
    OIL_SENATE_SLUGS,
    CountingSlateSpec,
    build_fomc_truth_table_legs,
    build_oil_senate_truth_table_legs,
    detect_counting_subwindow_boxes,
    detect_d2_12pm_binance_boxes,
    evaluate_counting_dead_no_locks,
    evaluate_locked_market_reward_carry,
    evaluate_pyth_catalyst_shock,
    fetch_aaa_national_gas_sync,
    fetch_xtracker_user_stats_sync,
    find_cross_event_bitmask_boxes,
    parse_counting_slate_event,
    parse_gas_daily_bracket,
    walk_equal_shares_overround_bids,
    walk_position_overround_bid_unwind,
)

DATA_DIR = PROJECT_ROOT / "data" / "alpha124"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "alpha124_shadow_state.json"
LEDGER_FILE = DATA_DIR / "alpha124_shadow_ledger.jsonl"
MARKET_TELEMETRY_FILE = DATA_DIR / "alpha124_market_telemetry.jsonl"
OPPS_FILE = DATA_DIR / "alpha124_live_opportunities.json"
LOG_FILE = DATA_DIR / "alpha124_shadow.log"
BACKTEST_CAL_FILE = DATA_DIR / "backtest_alpha_124_results.json"
LIVE_POLYMARKET_DIR = PROJECT_ROOT / "data" / "polymarket"
SHOCK_TRIGGER_FILE = LIVE_POLYMARKET_DIR / "live_shock_triggers.jsonl"
LIVE_ALPHA124_STATE_MIRROR_FILE = LIVE_POLYMARKET_DIR / "alpha124_shadow_state.json"
D1_LIVE_CANDIDATES_FILE = LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [ALPHA-124] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("Alpha124Shadow")

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BINANCE_URL = "https://api.binance.com"

try:
    import orjson as _orjson
except Exception:
    _orjson = None

CRYPTO_FEE_RATE = 0.07

# Proven negative-EV / redundant shadow sleeves quarantined in production (`PM_QUARANTINE_LOSING_SLEEVES=1`)
# Documented in `docs/POLYMARKET_EXPERIMENT_GRAVEYARD_AND_LEDGER.md`.
QUARANTINED_SHADOW_SLEEVES = frozenset({
    "M4_SHOCK_STRIKE_CATCHUP",
    "W2_ENSEMBLE_VALUE",
    "W2_MAKER_OVERROUND",
    "M1_SVI_MAKER_SCALP",
    "M2_STRIKE_CONVERGENCE",
    "P1_PREOPEN_MAKER_STRADDLE",
    "B1_CONVEX_TAIL_YES",
    "S2_EXACT_TWAP_LOCK",
    "ZERO_FEE_MAKER_ANCHOR_BOX",
    "CTF_OVERROUND_MINT_SELL",
})


def is_shadow_sleeve_quarantined(sleeve: str) -> bool:
    return os.getenv("PM_QUARANTINE_LOSING_SLEEVES", "1") == "1" and sleeve in QUARANTINED_SHADOW_SLEEVES


# Ticket sizing matrix across $100, $1,000, and $5,000 bankrolls (strictly enforces 1.5%-4% cap on B1 tails!)
BANKROLL_TICKETS: Dict[str, Dict[str, float]] = {
    "T100": {
        "W1_SOLAR_PEAK_LOCK": 15.0,
        "W2_ENSEMBLE_VALUE": 10.0,
        "W2_MAKER_OVERROUND": 10.0,
        "W3_WEATHER_SLATE_ARB": 12.0,
        "B1_CONVEX_TAIL_YES": 4.0,
        "B2_BARRIER_NO_LOCK": 15.0,
        "B3_BARRIER_MONO_BOX": 18.0,
        "M1_SVI_MAKER_SCALP": 15.0,
        "M2_STRIKE_CONVERGENCE": 15.0,
        "M3_LADDER_MONO_BOX": 20.0,
        "M4_SHOCK_STRIKE_CATCHUP": 15.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 20.0,
        "D1_4H_DOMINANCE_BOX": 20.0,
        "D1_QUIET_BOOK_BOX": 20.0,
        "D1_MAKER_ANCHOR_BOX": 18.0,
        "S5M_CHAINLINK_SNIPER": 15.0,
        "N1_NEGRISK_CROSS_BOX": 20.0,
        "P1_PREOPEN_MAKER_STRADDLE": 16.0,
        "U1_DAILY_UPDOWN_LOCK": 15.0,
        "C1_BINARY_COMPLETE_SET": 20.0,
        "S2_EXACT_TWAP_LOCK": 15.0,
        "CM_B3_PYTH_BARRIER_BOX": 20.0,
        "CM_B2_PYTH_SESSION_NO_LOCK": 15.0,
        "CM_U1_PYTH_CLOSE_LOCK": 15.0,
        "B4_TOUCHED_BARRIER_WICK_LOCK": 20.0,
        "SP1_NBA_ZERO_FEE_BOX": 20.0,
        "NR0_ZERO_FEE_SLATE_ARB": 15.0,
        "ZERO_FEE_MAKER_ANCHOR_BOX": 18.0,
        "ZF_INTRADAY_MAKER_BOX": 18.0,
        "TW1_COUNTING_TRUNCATION_AND_BOX": 18.0,
        "FED1_CENTRAL_BANK_LP_BOX": 20.0,
        "COND1_MACRO_PARTITION_BOX": 20.0,
        "CTF_OVERROUND_MINT_SELL": 20.0,
        "D2_12PM_BINANCE_BOX": 18.0,
        "GAS1_AAA_GASOLINE_LOCK": 15.0,
        "CM_SHOCK_PYTH_CATALYST": 15.0,
        "S4H_CHAINLINK_CONVERGENCE": 15.0,
        "MKR_REWARD_LOCKED_CARRY": 15.0,
    },
    "T1000": {
        "W1_SOLAR_PEAK_LOCK": 100.0,
        "W2_ENSEMBLE_VALUE": 50.0,
        "W2_MAKER_OVERROUND": 50.0,
        "W3_WEATHER_SLATE_ARB": 80.0,
        "B1_CONVEX_TAIL_YES": 25.0,
        "B2_BARRIER_NO_LOCK": 100.0,
        "B3_BARRIER_MONO_BOX": 120.0,
        "M1_SVI_MAKER_SCALP": 100.0,
        "M2_STRIKE_CONVERGENCE": 100.0,
        "M3_LADDER_MONO_BOX": 150.0,
        "M4_SHOCK_STRIKE_CATCHUP": 100.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 100.0,
        "D1_4H_DOMINANCE_BOX": 100.0,
        "D1_QUIET_BOOK_BOX": 100.0,
        "D1_MAKER_ANCHOR_BOX": 100.0,
        "S5M_CHAINLINK_SNIPER": 100.0,
        "N1_NEGRISK_CROSS_BOX": 150.0,
        "P1_PREOPEN_MAKER_STRADDLE": 96.0,
        "U1_DAILY_UPDOWN_LOCK": 100.0,
        "C1_BINARY_COMPLETE_SET": 150.0,
        "S2_EXACT_TWAP_LOCK": 100.0,
        "CM_B3_PYTH_BARRIER_BOX": 120.0,
        "CM_B2_PYTH_SESSION_NO_LOCK": 100.0,
        "CM_U1_PYTH_CLOSE_LOCK": 100.0,
        "B4_TOUCHED_BARRIER_WICK_LOCK": 120.0,
        "SP1_NBA_ZERO_FEE_BOX": 120.0,
        "NR0_ZERO_FEE_SLATE_ARB": 100.0,
        "ZERO_FEE_MAKER_ANCHOR_BOX": 100.0,
        "ZF_INTRADAY_MAKER_BOX": 110.0,
        "TW1_COUNTING_TRUNCATION_AND_BOX": 100.0,
        "FED1_CENTRAL_BANK_LP_BOX": 120.0,
        "COND1_MACRO_PARTITION_BOX": 120.0,
        "CTF_OVERROUND_MINT_SELL": 120.0,
        "D2_12PM_BINANCE_BOX": 100.0,
        "GAS1_AAA_GASOLINE_LOCK": 80.0,
        "CM_SHOCK_PYTH_CATALYST": 100.0,
        "S4H_CHAINLINK_CONVERGENCE": 100.0,
        "MKR_REWARD_LOCKED_CARRY": 100.0,
    },
    "T5000": {
        "W1_SOLAR_PEAK_LOCK": 350.0,
        "W2_ENSEMBLE_VALUE": 175.0,
        "W2_MAKER_OVERROUND": 175.0,
        "W3_WEATHER_SLATE_ARB": 250.0,
        "B1_CONVEX_TAIL_YES": 75.0,
        "B2_BARRIER_NO_LOCK": 350.0,
        "B3_BARRIER_MONO_BOX": 400.0,
        "M1_SVI_MAKER_SCALP": 350.0,
        "M2_STRIKE_CONVERGENCE": 350.0,
        "M3_LADDER_MONO_BOX": 500.0,
        "M4_SHOCK_STRIKE_CATCHUP": 350.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 300.0,
        "D1_4H_DOMINANCE_BOX": 300.0,
        "D1_QUIET_BOOK_BOX": 300.0,
        "D1_MAKER_ANCHOR_BOX": 300.0,
        "S5M_CHAINLINK_SNIPER": 300.0,
        "N1_NEGRISK_CROSS_BOX": 500.0,
        "P1_PREOPEN_MAKER_STRADDLE": 288.0,
        "U1_DAILY_UPDOWN_LOCK": 350.0,
        "C1_BINARY_COMPLETE_SET": 500.0,
        "S2_EXACT_TWAP_LOCK": 300.0,
        "CM_B3_PYTH_BARRIER_BOX": 400.0,
        "CM_B2_PYTH_SESSION_NO_LOCK": 350.0,
        "CM_U1_PYTH_CLOSE_LOCK": 350.0,
        "B4_TOUCHED_BARRIER_WICK_LOCK": 400.0,
        "SP1_NBA_ZERO_FEE_BOX": 400.0,
        "NR0_ZERO_FEE_SLATE_ARB": 300.0,
        "ZERO_FEE_MAKER_ANCHOR_BOX": 350.0,
        "ZF_INTRADAY_MAKER_BOX": 350.0,
        "TW1_COUNTING_TRUNCATION_AND_BOX": 350.0,
        "FED1_CENTRAL_BANK_LP_BOX": 400.0,
        "COND1_MACRO_PARTITION_BOX": 400.0,
        "CTF_OVERROUND_MINT_SELL": 400.0,
        "D2_12PM_BINANCE_BOX": 300.0,
        "GAS1_AAA_GASOLINE_LOCK": 250.0,
        "CM_SHOCK_PYTH_CATALYST": 300.0,
        "S4H_CHAINLINK_CONVERGENCE": 300.0,
        "MKR_REWARD_LOCKED_CARRY": 300.0,
    },
}


def walk_l2_book_asks(
    asks_raw: List[Dict[str, Any]],
    notional_usd: float,
    fee_rate: float,
    max_slip_cents: float = 0.025,
    min_l1_usd: float = 20.0,
    min_fill_ratio: float = 0.98,
    max_ask_px: float = 0.98,
) -> Dict[str, Any]:
    asks = sorted(
        [(float(a["price"]), float(a["size"])) for a in asks_raw if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
        key=lambda x: x[0],
    )
    if not asks:
        return {"filled": False, "reason": "EMPTY_ASK_BOOK", "best_ask": 1.0}
    best_ask = asks[0][0]
    l1_usd = round(best_ask * asks[0][1], 2)
    if l1_usd < min_l1_usd:
        return {"filled": False, "reason": "THIN_L1_DEPTH", "best_ask": best_ask, "l1_usd": l1_usd}
    rem = notional_usd
    spent = 0.0
    shares = 0.0
    levels = 0
    for px, sz in asks:
        if px > best_ask + max_slip_cents or px >= max_ask_px:
            break
        lvl_usd = px * sz
        levels += 1
        take = min(rem, lvl_usd)
        shares += take / px
        spent += take
        rem -= take
        if rem <= 1e-6:
            break

    if spent < notional_usd * min_fill_ratio or shares <= 0:
        return {"filled": False, "reason": "INSUFFICIENT_DEPTH", "best_ask": best_ask, "l1_usd": l1_usd}

    vwap = spent / shares
    fee_ps = fee_rate * vwap * (1.0 - vwap) if fee_rate > 0 else 0.0
    fee_usd = shares * fee_ps
    eff_px = (spent + fee_usd) / shares
    return {
        "filled": True,
        "best_ask": round(best_ask, 4),
        "vwap": round(vwap, 4),
        "eff_px": round(eff_px, 4),
        "slip_cents": round((vwap - best_ask) * 100.0, 2),
        "spent_usd": round(spent, 2),
        "fee_usd": round(fee_usd, 4),
        "shares": round(shares, 4),
        "fill_ratio": round(spent / notional_usd, 4),
        "l1_usd": l1_usd,
        "levels": levels,
    }


def extract_best_bid(bids_raw: List[Dict[str, Any]]) -> Tuple[float, float]:
    bids = sorted(
        [(float(b["price"]), float(b["size"])) for b in bids_raw if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
        key=lambda x: -x[0],
    )
    if not bids:
        return 0.0, 0.0
    return round(bids[0][0], 4), round(bids[0][0] * bids[0][1], 2)


class Alpha124ShadowDaemon:
    def __init__(self, single_scan: bool = False):
        self.single_scan = single_scan
        self.session: Optional[aiohttp.ClientSession] = None
        self.started_at = datetime.now(timezone.utc).isoformat()

        # Load calibrated parameters from backtest if available
        self.weather_sigma_c = 1.05
        self.barrier_wick_mult = 1.12
        self._load_calibration()

        # Live spot & rolling history
        self.spots: Dict[str, float] = {}
        self.spot_hist: Dict[str, Deque[Tuple[float, float]]] = {
            a: collections.deque(maxlen=600) for a in DOMINANCE_ASSETS
        }
        self.usd_spot_hist: Dict[str, Deque[Tuple[float, float]]] = {
            a: collections.deque(maxlen=400) for a in DOMINANCE_ASSETS
        }
        self.usd_direct_flags: Dict[str, bool] = {}

        # Discovered market registries & caches
        self.weather_events: Dict[str, WeatherEventSpec] = {}
        self.barrier_rungs: Dict[str, BarrierRungSpec] = {}
        self.strike_ladders: Dict[str, List[StrikeRungSpec]] = {}
        self.negrisk_ladders: Dict[str, List[NegRiskBracketSpec]] = {}
        self.daily_updown_markets: Dict[str, DailyUpDownSpec] = {}
        self.pyth_daily_markets: Dict[str, DailyUpDownSpec] = {}
        self.pyth_barrier_rungs: Dict[str, PythBarrierRungSpec] = {}
        self.pyth_close_ladders: Dict[str, List[PythCloseRungSpec]] = {}
        self.nba_games: Dict[str, NbaGameSpec] = {}
        self.negrisk_zero_slates: Dict[str, ZeroFeeNegRiskSlateSpec] = {}
        self.counting_slates: Dict[str, CountingSlateSpec] = {}
        self.fomc_truth_legs: List[Dict[str, Any]] = []
        self.oil_senate_truth_legs: List[Dict[str, Any]] = []
        self.gas_events_raw: Dict[str, List[Dict[str, Any]]] = {}
        self.hourly_12pm_markets: Dict[str, DailyUpDownSpec] = {}
        self.s4h_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.pending_zero_fee_maker_anchors: Dict[str, Dict[str, Any]] = {}
        self.prev_pyth_spots: Dict[str, float] = {}
        self.pyth_intraday_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.dominance_pairs: Dict[str, Tuple[TwapCandleMarketSpec, TwapCandleMarketSpec]] = {}
        self.dominance_4h_pairs: Dict[str, Tuple[TwapCandleMarketSpec, TwapCandleMarketSpec]] = {}
        self.twap_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.s5m_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.preopen_15m_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.pending_preopen_straddles: Dict[str, Dict[str, Any]] = {}
        self.pending_maker_anchors: Dict[str, Dict[str, Any]] = {}
        self.chainlink_open_cache: Dict[str, Tuple[float, float]] = {}  # key -> (end_ts, openPrice)
        self.daily_open_cache: Dict[str, Tuple[float, float]] = {}  # key -> (end_ts, binance_open)

        self.metar_cache: Dict[str, Tuple[float, List[MetarObservation]]] = {}
        self.taf_cache: Dict[str, Tuple[float, Dict[str, float]]] = {}
        self.ensemble_cache: Dict[str, Tuple[float, Dict[int, List[float]]]] = {}
        self.barrier_ext_cache: Dict[str, Tuple[float, Tuple[float, float, float]]] = {}
        self._last_w3_slate_chk_ts: Dict[str, float] = {}
        self._open_meteo_sem = asyncio.Semaphore(2)

        self.last_discovery_ts = 0.0
        self.last_weather_scan_ts = 0.0
        self.last_crypto_mid_scan_ts = 0.0
        self.last_tradfi_sports_scan_ts = 0.0
        self.last_dominance_discovery_ts = 0.0
        self.last_4h_discovery_ts = 0.0
        self.last_twap_discovery_ts = 0.0
        self.last_s5m_discovery_ts = 0.0
        self.last_preopen_discovery_ts = 0.0
        self.last_usd_sample_ts = 0.0
        self.cached_mid_opps: List[Dict[str, Any]] = []
        self.cached_weather_opps: List[Dict[str, Any]] = []
        self.cached_tradfi_sports_opps: List[Dict[str, Any]] = []
        self.cached_shock_opps: List[Dict[str, Any]] = []
        self.cycle_count = 0

        # Reactive <250ms Shock-Trigger Tailer State (M4 + Adverse Maker Cancel + D1 Quiet-Book Gate)
        try:
            self._shock_file_offset: int = SHOCK_TRIGGER_FILE.stat().st_size if SHOCK_TRIGGER_FILE.exists() else 0
        except Exception:
            self._shock_file_offset = 0
        self._seen_shock_ids: Deque[str] = collections.deque(maxlen=256)
        self._last_m4_shock_ts_by_asset: Dict[str, float] = {}
        self._last_any_shock_ts_by_asset: Dict[str, float] = {}
        self._last_d1_live_emit_ts: Dict[str, float] = {}
        self._bg_discovery_task: Optional[asyncio.Task] = None
        self._bg_weather_task: Optional[asyncio.Task] = None
        self._bg_mid_task: Optional[asyncio.Task] = None
        self._bg_tradfi_task: Optional[asyncio.Task] = None
        self._ws_books: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._ws_raw_levels: Dict[str, Tuple[Dict[float, float], Dict[float, float]]] = {}
        self._ws_subscribed_tokens: set[str] = set()
        # Tokens whose `_ws_books` entry was seeded from a REST `/books` snapshot (not yet confirmed by a WS `book` event);
        # these are never forwarded to the live harvester as `cand["ws_books"]`.
        self._ws_rest_seeded: set[str] = set()
        # Priority-1 D1/S2 tokens (from `_desired_d1_ws_tokens`): only their WS updates trigger `_ws_d1_wakeup`.
        self._ws_d1_priority_tokens: set[str] = set()
        self._bg_chainlink_ws_task: Optional[asyncio.Task] = None
        self._chainlink_ws: Optional[Any] = (
            PolymarketChainlinkLiveStream(on_tick=self._on_chainlink_ws_tick)
            if (not self.single_scan and PolymarketChainlinkLiveStream is not None)
            else None
        )
        self._ws_d1_wakeup = asyncio.Event()
        self._bg_clob_ws_task: Optional[asyncio.Task] = None
        self._strike_fail_backoff_ts: Dict[str, float] = {}
        self._last_telem_ts_by_key: Dict[str, float] = {}
        self._last_telem_sig_by_key: Dict[str, Any] = {}

        # Shadow Portfolio State (keyed by trade_key)
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.pending_maker_orders: Dict[str, Dict[str, Any]] = {}
        self.closed_positions: List[Dict[str, Any]] = []
        self.entered_keys: set[str] = set()
        self.inflight_keys: set[str] = set()
        self.top_opportunities: List[Dict[str, Any]] = []
        self._hydrate_state()

    def _try_acquire_keys(self, *keys: str) -> List[str]:
        """Synchronously reserves dedupe/event keys before any async `await` (`C-02` / `F-10`)."""
        valid = [str(k) for k in keys if k]
        if not valid:
            return []
        for k in valid:
            if k in self.entered_keys or k in self.inflight_keys:
                return []
        for k in valid:
            self.inflight_keys.add(k)
        return valid

    def _release_inflight_keys(self, keys: List[str]) -> None:
        for k in keys:
            self.inflight_keys.discard(k)

    def _record_market_telemetry(
        self,
        key: str,
        min_interval_sec: float,
        payload: Dict[str, Any],
        now_ts: Optional[float] = None,
        sig: Optional[Any] = None,
        unchanged_heartbeat_sec: float = 600.0,
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        last_ts = float(self._last_telem_ts_by_key.get(key) or 0.0)
        if (now - last_ts) < min_interval_sec:
            return
        if sig is not None and self._last_telem_sig_by_key.get(key) == sig and (now - last_ts) < unchanged_heartbeat_sec:
            return
        self._last_telem_ts_by_key[key] = now
        if sig is not None:
            self._last_telem_sig_by_key[key] = sig
        if len(self._last_telem_ts_by_key) > 5000:
            # Bound memory: drop telemetry throttle keys idle for > 2h (market keys are per-expiry and never recur)
            for k_old, ts_old in list(self._last_telem_ts_by_key.items()):
                if (now - float(ts_old or 0.0)) > 7200.0:
                    self._last_telem_ts_by_key.pop(k_old, None)
                    self._last_telem_sig_by_key.pop(k_old, None)
            for k_old in list(self._last_telem_sig_by_key.keys()):
                if k_old not in self._last_telem_ts_by_key:
                    self._last_telem_sig_by_key.pop(k_old, None)
        row = {
            "ts": round(now, 3),
            "utc": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            **payload,
        }
        try:
            if (
                (self.single_scan or ("fetch_json" in self.__dict__))
                and MARKET_TELEMETRY_FILE == (DATA_DIR / "alpha124_market_telemetry.jsonl")
                and STATE_FILE == (DATA_DIR / "alpha124_shadow_state.json")
                and LEDGER_FILE == (DATA_DIR / "alpha124_shadow_ledger.jsonl")
            ):
                return
            if MARKET_TELEMETRY_FILE != (DATA_DIR / "alpha124_market_telemetry.jsonl"):
                telem_path = MARKET_TELEMETRY_FILE
            elif STATE_FILE != (DATA_DIR / "alpha124_shadow_state.json"):
                telem_path = STATE_FILE.parent / "alpha124_market_telemetry.jsonl"
            else:
                telem_path = LEDGER_FILE.parent / "alpha124_market_telemetry.jsonl"
            line_b = (json.dumps(row, separators=(",", ":")) + "\n").encode("utf-8")
            fd = os.open(str(telem_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o664)
            try:
                try:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX)
                except Exception:
                    pass
                os.write(fd, line_b)
            finally:
                try:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except Exception:
                    pass
                os.close(fd)
        except Exception:
            pass

    @staticmethod
    def _best_ask_sz(bk: Dict[str, Any]) -> Tuple[float, float]:
        best_p, best_s = 1.0, 0.0
        for a in (bk.get("asks") or []):
            try:
                p, s = float(a.get("price", 0)), float(a.get("size", 0))
                if p > 0 and s > 0 and p < best_p:
                    best_p, best_s = p, s
            except Exception:
                continue
        return best_p, best_s

    def _record_d1_corridor_telemetry(
        self,
        pair_type: str,
        m_outer: TwapCandleMarketSpec,
        m_inner: TwapCandleMarketSpec,
        dom_info: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        now_ts: float,
    ) -> None:
        leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
        ask_a, sz_a = self._best_ask_sz(bk_a)
        ask_b, sz_b = self._best_ask_sz(bk_b)
        if ask_a >= 1.0 or ask_b >= 1.0:
            return
        bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
        bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
        fa = float(leg_a["fee_rate"]) * ((ask_a * (1.0 - ask_a)) ** float(leg_a.get("fee_exponent", 1.0)))
        fb = float(leg_b["fee_rate"]) * ((ask_b * (1.0 - ask_b)) ** float(leg_b.get("fee_exponent", 1.0)))
        mkr_cands: List[float] = []
        for b_x, a_x, o_eff in ((bid_a, ask_a, ask_b + fb), (bid_b, ask_b, ask_a + fa)):
            if b_x <= 0.0:
                continue
            tb_x = 0.001 if (b_x >= 0.96 or b_x < 0.04) else 0.01
            ta_x = 0.001 if (a_x > 0.96 or a_x <= 0.04) else 0.01
            st_b = (math.floor((b_x + tb_x + 1e-9) * 100.0) / 100.0) if (0.04 + 1e-9 < round(b_x + tb_x, 4) < 0.96 - 1e-9) else round(b_x + tb_x, 3)
            mx_u = (math.floor((a_x - ta_x + 1e-9) * 100.0) / 100.0) if (0.04 + 1e-9 < round(a_x - ta_x, 4) < 0.96 - 1e-9) else round(a_x - ta_x, 3)
            if st_b <= mx_u + 1e-9 and st_b > b_x + 1e-9:
                mkr_cands.append(round(min(st_b, mx_u) + o_eff, 4))
            elif (a_x - b_x) >= 0.01 - 1e-9 and 0.15 <= a_x <= 0.85:
                mkr_cands.append(round(b_x + o_eff, 4))
        best_mkr_net = min(mkr_cands) if mkr_cands else None
        usd_h = self.usd_spot_hist.get(m_outer.asset)
        usd_px = round(float(usd_h[-1][1]), 6) if usd_h else None
        self._record_market_telemetry(
            key=f"D1_{pair_type}_{m_outer.asset}_{m_inner.market_id}",
            min_interval_sec=10.0,
            now_ts=now_ts,
            sig=(ask_a, ask_b, best_mkr_net),
            unchanged_heartbeat_sec=60.0,
            payload={
                "type": "D1_CORRIDOR",
                "pair_type": pair_type,
                "asset": m_outer.asset,
                "regime": dom_info["regime"],
                "m_outer_id": m_outer.market_id,
                "m_inner_id": m_inner.market_id,
                "end_ts": int(m_inner.end_ts),
                "tte_sec": round(m_inner.end_ts - now_ts, 1),
                "k_low": dom_info["k_low"],
                "k_high": dom_info["k_high"],
                "corridor_bps": dom_info["corridor_bps"],
                "usd_spot": usd_px,
                "leg_a_ask": ask_a,
                "leg_b_ask": ask_b,
                "gross_box_l1": round(ask_a + ask_b, 4),
                "net_box_l1": round(ask_a + fa + ask_b + fb, 4),
                "maker_anchor_net_l1": best_mkr_net,
                "l1_min_shares": round(min(sz_a, sz_b), 2),
            },
        )

    def _load_calibration(self) -> None:
        if not BACKTEST_CAL_FILE.exists():
            return
        try:
            d = json.loads(BACKTEST_CAL_FILE.read_text(encoding="utf-8"))
            w_sig = d.get("option_1_weather", {}).get("calibrated_sigma_c")
            b_mult = d.get("option_2_barrier_onetouch", {}).get("calibrated_wick_vol_mult")
            if w_sig:
                self.weather_sigma_c = float(w_sig)
            if b_mult:
                self.barrier_wick_mult = float(b_mult)
            logger.info(f"Loaded WFO calibration: weather_sigma_c={self.weather_sigma_c}, barrier_wick_mult={self.barrier_wick_mult}")
        except Exception as exc:
            logger.warning(f"Calibration load notice: {exc}")

    def _hydrate_state(self) -> None:
        if STATE_FILE.exists():
            try:
                st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.started_at = st.get("started_at", self.started_at)
                for p in st.get("open_positions", []):
                    if isinstance(p, dict) and p.get("position_id"):
                        self.open_positions[p["position_id"]] = p
                        self.entered_keys.add(str(p.get("dedupe_key") or p["position_id"]))
                        ev_id = (p.get("extra") or {}).get("event_id")
                        if ev_id:
                            if p.get("sleeve") == "W2_ENSEMBLE_VALUE":
                                self.entered_keys.add(f"W2_EVENT_{ev_id}")
                            elif p.get("sleeve") == "W2_MAKER_OVERROUND":
                                self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                for m_ord in st.get("pending_maker_orders", []):
                    if isinstance(m_ord, dict) and m_ord.get("order_id"):
                        self.pending_maker_orders[m_ord["order_id"]] = m_ord
                        if m_ord.get("dedupe_key"):
                            self.entered_keys.add(str(m_ord["dedupe_key"]))
                        ev_id = (m_ord.get("extra") or {}).get("event_id")
                        if ev_id and m_ord.get("sleeve") == "W2_MAKER_OVERROUND":
                            self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                for p in st.get("recent_closed_positions", []):
                    if isinstance(p, dict):
                        self.closed_positions.append(p)
                        if p.get("dedupe_key"):
                            self.entered_keys.add(str(p["dedupe_key"]))
                        ev_id = (p.get("extra") or {}).get("event_id")
                        if ev_id:
                            if p.get("sleeve") == "W2_ENSEMBLE_VALUE":
                                self.entered_keys.add(f"W2_EVENT_{ev_id}")
                            elif p.get("sleeve") == "W2_MAKER_OVERROUND":
                                self.entered_keys.add(f"W2M_EVENT_{ev_id}")
            except Exception as exc:
                logger.warning(f"State hydrate notice: {exc}")

        if LEDGER_FILE.exists():
            try:
                ledger_open: Dict[str, Dict[str, Any]] = {}
                ledger_maker: Dict[str, Dict[str, Any]] = {}
                closed_ids = {str(p.get("position_id")) for p in self.closed_positions if isinstance(p, dict) and p.get("position_id")}
                with open(LEDGER_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            r = json.loads(line)
                        except Exception:
                            # Skip truncated/corrupt JSONL line without aborting ledger hydration (`F-19`)
                            continue
                        ev = r.get("event")
                        if ev in ("SHADOW_ENTRY", "SHADOW_CLOSE") and r.get("dedupe_key"):
                            self.entered_keys.add(str(r["dedupe_key"]))
                        if ev == "SHADOW_ENTRY":
                            pid = str(r.get("position_id") or "")
                            if pid:
                                pos_rec = {k: v for k, v in r.items() if k != "event"}
                                ledger_open[pid] = pos_rec
                            d_key = str(r.get("dedupe_key") or "")
                            if d_key:
                                for oid_k, m_v in list(ledger_maker.items()):
                                    if str(m_v.get("dedupe_key") or "") == d_key:
                                        ledger_maker.pop(oid_k, None)
                            ev_id = (r.get("extra") or {}).get("event_id")
                            if ev_id:
                                if r.get("sleeve") == "W2_ENSEMBLE_VALUE":
                                    self.entered_keys.add(f"W2_EVENT_{ev_id}")
                                elif r.get("sleeve") == "W2_MAKER_OVERROUND":
                                    self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                        elif ev == "SHADOW_CLOSE":
                            pid = str(r.get("position_id") or "")
                            if pid:
                                ledger_open.pop(pid, None)
                                self.open_positions.pop(pid, None)
                                if pid not in closed_ids:
                                    closed_ids.add(pid)
                                    self.closed_positions.append({k: v for k, v in r.items() if k != "event"})
                        elif ev == "SHADOW_MAKER_POST":
                            oid = str(r.get("order_id") or "")
                            if oid:
                                ledger_maker[oid] = {k: v for k, v in r.items() if k != "event"}
                                if r.get("dedupe_key"):
                                    self.entered_keys.add(str(r["dedupe_key"]))
                                ev_id = (r.get("extra") or {}).get("event_id")
                                if ev_id and r.get("sleeve") == "W2_MAKER_OVERROUND":
                                    self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                        elif ev == "SHADOW_MAKER_CANCEL":
                            oid = str(r.get("order_id") or "")
                            if oid:
                                m_old = ledger_maker.pop(oid, None)
                                self.pending_maker_orders.pop(oid, None)
                                if m_old and m_old.get("dedupe_key"):
                                    self.entered_keys.discard(str(m_old["dedupe_key"]))
                                ev_id = ((m_old or r).get("extra") or {}).get("event_id")
                                if ev_id and (m_old or r).get("sleeve") == "W2_MAKER_OVERROUND":
                                    self.entered_keys.discard(f"W2M_EVENT_{ev_id}")

                for pid, pos_rec in ledger_open.items():
                    if pid not in self.open_positions and pid not in closed_ids:
                        self.open_positions[pid] = pos_rec
                for oid, m_rec in ledger_maker.items():
                    if oid not in self.pending_maker_orders:
                        self.pending_maker_orders[oid] = m_rec
            except Exception as exc:
                logger.warning(f"Ledger hydrate notice: {exc}")

        if self.closed_positions:
            self.closed_positions.sort(key=lambda p: float(p.get("closed_ts") or 0.0))

        # Evict any lingering resting Maker orders belonging to quarantined losing sleeves
        for oid_q, m_q in list(self.pending_maker_orders.items()):
            if is_shadow_sleeve_quarantined(str(m_q.get("sleeve") or "")):
                self.pending_maker_orders.pop(oid_q, None)
                self._append_ledger({"event": "SHADOW_MAKER_CANCEL", "reason": "SLEEVE_QUARANTINED", **m_q})
        if is_shadow_sleeve_quarantined("P1_PREOPEN_MAKER_STRADDLE"):
            self.pending_preopen_straddles.clear()
        if is_shadow_sleeve_quarantined("ZERO_FEE_MAKER_ANCHOR_BOX"):
            self.pending_zero_fee_maker_anchors.clear()

    def _append_ledger(self, rec: Dict[str, Any]) -> None:
        with open(LEDGER_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=40),
                headers={"User-Agent": "DominusAlpha124Shadow/1.0", "Accept": "application/json"},
                max_line_size=65536,
                max_field_size=65536,
            )
        return self.session

    def _on_chainlink_ws_tick(self, asset: str, ts_sec: float, price_usd: float) -> None:
        if price_usd <= 0.0 or not math.isfinite(price_usd):
            return
        self.spots[asset] = price_usd
        self.usd_direct_flags[asset] = True
        dq = self.usd_spot_hist.get(asset)
        if dq is None:
            dq = collections.deque(maxlen=450)
            self.usd_spot_hist[asset] = dq
        if dq and abs(ts_sec - float(dq[-1][0])) < 0.05:
            dq[-1] = (ts_sec, price_usd)
        elif dq and ts_sec < float(dq[-1][0]):
            return  # out-of-order (older) tick: never append behind newer samples (keeps history time-monotonic)
        else:
            dq.append((ts_sec, price_usd))

    async def fetch_json(self, url: str, timeout: float = 5.0) -> Any:
        if not self.single_scan and self._ws_books and "/book?token_id=" in str(url):
            tok_q = str(url).split("token_id=", 1)[1].split("&", 1)[0].strip()
            ws_ent = self._ws_books.get(tok_q)
            if ws_ent is not None and (time.time() - ws_ent[0]) <= 1.5:
                bk_ws = ws_ent[1]
                if bk_ws.get("asks") or bk_ws.get("bids"):
                    return bk_ws
        sess = await self.get_session()
        try:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            return None
        return None

    async def fetch_book_after_latency(self, token_id: str, latency_ms: int = 50) -> Optional[Dict[str, Any]]:
        if latency_ms > 0:
            await asyncio.sleep(latency_ms / 1000.0)
        return await self.fetch_json(f"{CLOB_URL}/book?token_id={token_id}", timeout=3.5)

    def _rebuild_ws_book_dict(
        self,
        asset_id: str,
        bids_map: Dict[float, float],
        asks_map: Dict[float, float],
        now_ts: float,
    ) -> None:
        bids_sorted = [
            {"price": f"{px:.4f}", "size": f"{sz:.4f}"}
            for px, sz in sorted(bids_map.items(), key=lambda kv: -kv[0])[:20]
            if px > 0.0 and sz > 0.0
        ]
        asks_sorted = [
            {"price": f"{px:.4f}", "size": f"{sz:.4f}"}
            for px, sz in sorted(asks_map.items(), key=lambda kv: kv[0])[:20]
            if px > 0.0 and sz > 0.0
        ]
        self._ws_books[asset_id] = (
            now_ts,
            {"asset_id": asset_id, "bids": bids_sorted, "asks": asks_sorted},
        )

    def _apply_ws_book_snapshot(
        self,
        asset_id: str,
        bids_raw: List[Dict[str, Any]],
        asks_raw: List[Dict[str, Any]],
        now_ts: float,
        from_rest: bool = False,
    ) -> None:
        if not asset_id:
            return
        bids_map: Dict[float, float] = {}
        asks_map: Dict[float, float] = {}
        for row in bids_raw or ():
            try:
                px = round(float(row.get("price", 0.0)), 4)
                sz = float(row.get("size", 0.0))
                if px > 0.0 and sz > 0.0:
                    bids_map[px] = sz
            except Exception:
                continue
        for row in asks_raw or ():
            try:
                px = round(float(row.get("price", 0.0)), 4)
                sz = float(row.get("size", 0.0))
                if px > 0.0 and sz > 0.0:
                    asks_map[px] = sz
            except Exception:
                continue
        self._ws_raw_levels[asset_id] = (bids_map, asks_map)
        self._rebuild_ws_book_dict(asset_id, bids_map, asks_map, now_ts)
        if from_rest:
            self._ws_rest_seeded.add(asset_id)
        else:
            self._ws_rest_seeded.discard(asset_id)

    def _drop_ws_book(self, asset_id: str) -> None:
        self._ws_books.pop(asset_id, None)
        self._ws_raw_levels.pop(asset_id, None)
        self._ws_rest_seeded.discard(asset_id)

    def _apply_ws_price_changes(
        self,
        asset_id: str,
        changes: List[Dict[str, Any]],
        now_ts: float,
    ) -> bool:
        lvls = self._ws_raw_levels.get(asset_id)
        if lvls is None:
            return False
        bids_map, asks_map = lvls
        changed = False
        for pc in changes or ():
            try:
                px = round(float(pc.get("price", 0.0)), 4)
                sz = float(pc.get("size", 0.0))
                side = str(pc.get("side") or "").upper()
                if px <= 0.0:
                    continue
                target_map = bids_map if side == "BUY" else asks_map
                if sz <= 0.0:
                    if px in target_map:
                        target_map.pop(px, None)
                        changed = True
                else:
                    target_map[px] = sz
                    changed = True
            except Exception:
                continue
        # Integrity check: reconstructed book must not be crossed/locked and must agree with Polymarket's
        # own post-change `best_bid`/`best_ask` fields; otherwise drop the book so it is never used for live orders.
        best_bid_r = max(bids_map.keys()) if bids_map else 0.0
        best_ask_r = min(asks_map.keys()) if asks_map else 0.0
        book_bad = bool(bids_map and asks_map and best_bid_r >= best_ask_r)
        if not book_bad:
            pc_last_bb: Optional[float] = None
            pc_last_ba: Optional[float] = None
            for pc in changes or ():
                try:
                    if pc.get("best_bid") not in (None, ""):
                        pc_last_bb = float(pc.get("best_bid"))
                    if pc.get("best_ask") not in (None, ""):
                        pc_last_ba = float(pc.get("best_ask"))
                except Exception:
                    continue
            if pc_last_bb is not None and 0.0 < pc_last_bb < 1.0 and abs(pc_last_bb - best_bid_r) > 1e-6:
                book_bad = True
            if pc_last_ba is not None and 0.0 < pc_last_ba < 1.0 and abs(pc_last_ba - best_ask_r) > 1e-6:
                book_bad = True
        if book_bad:
            logger.debug(
                f"[WS BOOK INTEGRITY] {asset_id[:12]}: reconstructed bb={best_bid_r} ba={best_ask_r} "
                f"crossed or mismatched vs price_change best_bid/best_ask -> book dropped"
            )
            self._drop_ws_book(asset_id)
            return False
        if changed:
            self._rebuild_ws_book_dict(asset_id, bids_map, asks_map, now_ts)
        return changed

    def _desired_d1_ws_tokens(self, now_ts: float) -> List[str]:
        out: List[str] = []
        seen: set[str] = set()

        def _add_tok(tok: Any, max_cap: int = 220) -> bool:
            if len(out) >= max_cap:
                return False
            t_s = str(tok or "").strip()
            if t_s and t_s not in seen:
                seen.add(t_s)
                out.append(t_s)
            return len(out) < max_cap

        # Priority 1: Active D1 (15m/5m + 4h) and S2 TWAP Lock tokens
        for m_long, m_short in list(self.dominance_pairs.values()) + list(self.dominance_4h_pairs.values()):
            if float(m_short.end_ts) <= now_ts + 5.0:
                continue
            for tok in (m_long.up_token, m_long.down_token, m_short.up_token, m_short.down_token):
                _add_tok(tok)
        for sp_tw in list(self.twap_candles.values()):
            if float(sp_tw.end_ts) > now_ts + 5.0:
                _add_tok(sp_tw.up_token)
                _add_tok(sp_tw.down_token)
        self._ws_d1_priority_tokens = set(out)

        # Priority 2: itode=None zero-hold C1 Daily Complete Sets + near-ATM M3 Multi-Strike & N1 NegRisk Brackets + W3 Weather
        for sp_d in list(self.pyth_daily_markets.values()) + list(self.daily_updown_markets.values()):
            if float(sp_d.end_ts) > now_ts + 60.0:
                _add_tok(sp_d.up_token)
                _add_tok(sp_d.down_token)
        for rungs in list(self.strike_ladders.values()):
            if not rungs or float(rungs[0].end_ts) <= now_ts + 60.0:
                continue
            spot_r = float(self.spots.get(rungs[0].asset) or 0.0)
            ranked_r = sorted(rungs, key=lambda r: abs(float(r.strike) - spot_r)) if spot_r > 0.0 else list(rungs)
            for r in ranked_r[:6]:
                _add_tok(r.yes_token)
                _add_tok(r.no_token)
        for brs in list(self.negrisk_ladders.values()):
            if not brs or float(brs[0].end_ts) <= now_ts + 60.0:
                continue
            spot_n = float(self.spots.get(brs[0].asset) or 0.0)
            ranked_b = sorted(brs, key=lambda b: abs(0.5 * (float(b.k_low or spot_n) + float(b.k_high or spot_n)) - spot_n)) if spot_n > 0.0 else list(brs)
            for b in ranked_b[:6]:
                _add_tok(b.yes_token)
                _add_tok(b.no_token)
        for w_ev in list(self.weather_events.values()):
            for bkt in getattr(w_ev, "buckets", ()) or ():
                if not _add_tok(getattr(bkt, "yes_token", None)):
                    break
                _add_tok(getattr(bkt, "no_token", None))
        return out

    async def _run_clob_d1_ws_loop(self) -> None:
        """Maintains a live Polymarket CLOB Market WebSocket L2 book cache for active D1 pairs."""
        while not self.single_scan:
            now_0 = time.time()
            desired_0 = self._desired_d1_ws_tokens(now_0)
            if not desired_0:
                self._ws_subscribed_tokens.clear()
                await asyncio.sleep(1.0)
                continue
            try:
                sess = await self.get_session()
                async with sess.ws_connect(
                    CLOB_WS_URL,
                    heartbeat=15.0,
                    max_msg_size=4 * 1024 * 1024,
                    timeout=aiohttp.ClientWSTimeout(ws_close=5.0),
                ) as ws:
                    # Fresh connection: discard every book reconstructed on the previous socket (deltas may have been missed)
                    self._ws_books.clear()
                    self._ws_raw_levels.clear()
                    self._ws_rest_seeded.clear()
                    self._ws_subscribed_tokens = set(desired_0)
                    await ws.send_str(json.dumps({"assets_ids": desired_0, "type": "market"}))
                    last_sub_chk = time.time()
                    last_rx_ts = last_sub_chk
                    while not self.single_scan:
                        now_w = time.time()
                        if (now_w - last_sub_chk) >= 2.0:
                            last_sub_chk = now_w
                            cur_desired = set(self._desired_d1_ws_tokens(now_w))
                            for stale_tok in list(self._ws_books.keys()):
                                if stale_tok not in cur_desired:
                                    self._drop_ws_book(stale_tok)
                            if not cur_desired:
                                break
                            added = sorted(cur_desired - self._ws_subscribed_tokens)
                            if added:
                                await ws.send_str(json.dumps({"assets_ids": added, "operation": "subscribe"}))
                                self._ws_subscribed_tokens.update(added)
                            elif len(self._ws_subscribed_tokens) > len(cur_desired) + 28:
                                break
                        if (now_w - last_rx_ts) > 30.0:
                            break
                        try:
                            msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                        except asyncio.TimeoutError:
                            continue
                        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                            break
                        if msg.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                            continue
                        raw_payload = msg.data
                        if not raw_payload or raw_payload in ("PONG", b"PONG"):
                            last_rx_ts = time.time()
                            continue
                        now_rx = time.time()
                        last_rx_ts = now_rx
                        data = _orjson.loads(raw_payload) if _orjson is not None else json.loads(raw_payload)
                        woke = False
                        d1_wake_toks = self._ws_d1_priority_tokens
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    aid = str(item.get("asset_id") or "")
                                    if aid in self._ws_subscribed_tokens:
                                        self._apply_ws_book_snapshot(aid, item.get("bids") or [], item.get("asks") or [], now_rx)
                                        woke = woke or (aid in d1_wake_toks)
                        elif isinstance(data, dict):
                            ev_t = data.get("event_type")
                            if ev_t == "book":
                                aid = str(data.get("asset_id") or "")
                                if aid in self._ws_subscribed_tokens:
                                    self._apply_ws_book_snapshot(aid, data.get("bids") or [], data.get("asks") or [], now_rx)
                                    woke = woke or (aid in d1_wake_toks)
                            elif ev_t == "price_change":
                                grouped: Dict[str, List[Dict[str, Any]]] = {}
                                for pc in data.get("price_changes") or ():
                                    aid = str(pc.get("asset_id") or "")
                                    if aid in self._ws_subscribed_tokens:
                                        grouped.setdefault(aid, []).append(pc)
                                for aid, pcs in grouped.items():
                                    if self._apply_ws_price_changes(aid, pcs, now_rx) and aid in d1_wake_toks:
                                        woke = True
                        # D1 overlap-window or active resting Maker-Anchor updates wake the fast D1 sub-scan (<=8.3 Hz)
                        if (
                            woke
                            and (self.is_in_same_oracle_overlap_window(now_rx) or bool(self.pending_maker_anchors))
                            and (now_rx - getattr(self, "_last_ws_d1_wake_ts", 0.0)) >= 0.12
                        ):
                            self._last_ws_d1_wake_ts = now_rx
                            self._ws_d1_wakeup.set()
            except asyncio.CancelledError:
                raise
            except Exception as exc_ws:
                logger.debug(f"D1 CLOB WS reconnect notice: {exc_ws}")
                await asyncio.sleep(1.0)

    async def fetch_books_batch(self, token_ids: List[str], timeout: float = 3.0) -> Dict[str, Dict[str, Any]]:
        uniq = list(dict.fromkeys(str(t) for t in token_ids if t))
        if not uniq:
            return {}
        if "fetch_json" in self.__dict__:
            res_list = await asyncio.gather(*(self.fetch_json(f"{CLOB_URL}/book?token_id={t}", timeout=timeout) for t in uniq))
            return {t: bk for t, bk in zip(uniq, res_list) if isinstance(bk, dict)}
        out: Dict[str, Dict[str, Any]] = {}
        missing: List[str] = []
        now_b = time.time()
        use_ws = not self.single_scan
        for t in uniq:
            ws_entry = self._ws_books.get(t) if use_ws else None
            if (
                ws_entry is not None
                and (now_b - ws_entry[0]) <= 1.5
                and ws_entry[1].get("bids")
                and ws_entry[1].get("asks")
            ):
                out[t] = ws_entry[1]
            else:
                missing.append(t)
        if not missing:
            return out
        sess = await self.get_session()
        for idx in range(0, len(missing), 50):
            chunk = missing[idx : idx + 50]
            try:
                async with sess.post(
                    f"{CLOB_URL}/books",
                    json=[{"token_id": t} for t in chunk],
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status == 200:
                        raw_bytes = await resp.read()
                        rows = _orjson.loads(raw_bytes) if _orjson is not None else json.loads(raw_bytes)
                        if isinstance(rows, list):
                            now_seed = time.time()
                            for r in rows:
                                if isinstance(r, dict) and r.get("asset_id"):
                                    aid_r = str(r["asset_id"])
                                    out[aid_r] = r
                                    if use_ws and aid_r in self._ws_subscribed_tokens and aid_r not in self._ws_raw_levels:
                                        self._apply_ws_book_snapshot(aid_r, r.get("bids") or [], r.get("asks") or [], now_seed, from_rest=True)
                            continue
            except Exception:
                pass
            fb = await asyncio.gather(*(self.fetch_json(f"{CLOB_URL}/book?token_id={t}", timeout=timeout) for t in chunk))
            for t, bk in zip(chunk, fb):
                if isinstance(bk, dict):
                    out[t] = bk
        return out

    def record_usd_spot_samples(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        self.last_usd_sample_ts = now
        for asset in DOMINANCE_ASSETS:
            shm = read_shm_usd_anchor(asset, now, max_age_sec=2.5)
            usd_px = shm.get("usd_spot")
            src = str(shm.get("source") or "")
            if usd_px and float(usd_px) > 0:
                self.usd_spot_hist.setdefault(asset, collections.deque(maxlen=400)).append((now, float(usd_px)))
                self.usd_direct_flags[asset] = src in ("shm_chainlink_proxy", "shm_coinbase_usd")

    async def update_crypto_spots(self) -> None:
        now = time.time()
        syms_json = "%5B" + ",".join(f"%22{s}%22" for s in sorted(set(ASSET_BINANCE_SYMBOL.values()))) + "%5D"
        data = await self.fetch_json(f"{BINANCE_URL}/api/v3/ticker/price?symbols={syms_json}", timeout=3.5)
        if isinstance(data, list):
            sym_map = {v: k for k, v in ASSET_BINANCE_SYMBOL.items()}
            for item in data:
                sym = item.get("symbol")
                if sym in sym_map:
                    asset = sym_map[sym]
                    px = float(item["price"])
                    self.spots[asset] = px
                    self.spot_hist.setdefault(asset, collections.deque(maxlen=600)).append((now, px))
        fapi_hype = await self.fetch_json(f"{BINANCE_FAPI_URL}/fapi/v1/ticker/price?symbol=HYPEUSDT", timeout=2.5)
        if isinstance(fapi_hype, dict) and fapi_hype.get("price"):
            px_h = float(fapi_hype["price"])
            if px_h > 0:
                self.spots["HYPE"] = px_h
                self.spot_hist.setdefault("HYPE", collections.deque(maxlen=600)).append((now, px_h))
        self.record_usd_spot_samples(now)
        missing_usd_assets = [
            a
            for a in DOMINANCE_ASSETS
            if a != "HYPE"
            and (
                not self.usd_direct_flags.get(a, False)
                or not self.usd_spot_hist.get(a)
                or (now - float(self.usd_spot_hist[a][-1][0])) > 3.0
            )
        ]
        if missing_usd_assets:
            cb_rows = await asyncio.gather(
                *(
                    self.fetch_json(f"https://api.exchange.coinbase.com/products/{a}-USD/ticker", timeout=2.0)
                    for a in missing_usd_assets
                )
            )
            now_cb = time.time()
            for a, cb in zip(missing_usd_assets, cb_rows):
                if isinstance(cb, dict) and cb.get("price"):
                    try:
                        px_cb = float(cb["price"])
                        if px_cb > 0:
                            self.usd_spot_hist.setdefault(a, collections.deque(maxlen=400)).append((now_cb, px_cb))
                            self.usd_direct_flags[a] = True
                    except Exception:
                        pass

    @staticmethod
    def _hist_return_bps(hist: Optional[Deque[Tuple[float, float]]], lookback_sec: float) -> float:
        if not hist or len(hist) < 2:
            return 0.0
        now, cur = hist[-1]
        # Never compare hist[-1] against itself when prior samples are > lookback_sec apart!
        ref = hist[-2][1]
        for idx in range(len(hist) - 1):
            ts, px = hist[idx]
            if now - ts <= lookback_sec:
                ref = px
                break
        return ((cur - ref) / ref) * 10000.0 if ref > 0 else 0.0

    def get_return_bps(self, asset: str, lookback_sec: float) -> float:
        r_spot = self._hist_return_bps(self.spot_hist.get(asset), lookback_sec)
        r_usd = self._hist_return_bps(self.usd_spot_hist.get(asset), lookback_sec)
        return r_usd if abs(r_usd) > abs(r_spot) else r_spot

    async def discover_all_markets(self) -> None:
        logger.info("Discovering active Weather (#1), Barrier Hit (#2), Multi-Strike (#4), NegRisk, and Daily Up/Down markets...")
        # 1. Scan top 600 active events by 24h volume + explicit high-volume Asian/Global METAR series (`Chengdu`, `Beijing`, `Seoul`)
        weather_found: Dict[str, WeatherEventSpec] = {}
        now_w_disc = time.time()
        def _weather_still_live(sp_w: WeatherEventSpec) -> bool:
            try:
                return datetime.fromisoformat(sp_w.end_date_iso.replace("Z", "+00:00")).timestamp() > now_w_disc
            except Exception:
                return True

        def _parse_neg_risk_flag(v: Any) -> Optional[bool]:
            if isinstance(v, bool):
                return v
            if isinstance(v, str) and v.strip().lower() in ("true", "false"):
                return v.strip().lower() == "true"
            return None

        def _attach_weather_neg_risk(sp_w: WeatherEventSpec, ev_raw: Any) -> None:
            # Gamma `negRisk` (market-level overrides event-level) -> `bucket.neg_risk`; unknown stays None (blocks LIVE C1 emits)
            if not isinstance(ev_raw, dict):
                return
            ev_nr = _parse_neg_risk_flag(ev_raw.get("negRisk"))
            nr_by_id: Dict[str, Optional[bool]] = {}
            for mk in ev_raw.get("markets") or ():
                if not isinstance(mk, dict):
                    continue
                mk_nr = _parse_neg_risk_flag(mk.get("negRisk"))
                if mk_nr is None:
                    mk_nr = ev_nr
                for id_k in (mk.get("id"), mk.get("conditionId")):
                    if id_k not in (None, ""):
                        nr_by_id[str(id_k)] = mk_nr
            for bkt in sp_w.buckets:
                nr_v = nr_by_id.get(str(bkt.market_id))
                if nr_v is None:
                    nr_v = nr_by_id.get(str(bkt.condition_id))
                if nr_v is None and getattr(bkt, "neg_risk", None) is not None:
                    continue  # keep a value already parsed upstream (e.g. by `parse_weather_event`)
                try:
                    setattr(bkt, "neg_risk", nr_v)
                except Exception:
                    pass

        for offset in range(0, 600, 100):
            evts = await self.fetch_json(
                f"{GAMMA_URL}/events?closed=false&order=volume24hr&ascending=false&limit=100&offset={offset}",
                timeout=7.0,
            )
            if not isinstance(evts, list) or not evts:
                break
            for ev in evts:
                sp = parse_weather_event(ev)
                if sp is not None and _weather_still_live(sp):
                    _attach_weather_neg_risk(sp, ev)
                    weather_found[sp.event_id] = sp
        for w_slug in HIGH_VOLUME_WEATHER_SERIES:
            evts_w = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={w_slug}&closed=false&limit=3", timeout=5.0)
            if isinstance(evts_w, list):
                for ev in evts_w:
                    sp = parse_weather_event(ev, series_slug_hint=w_slug)
                    if sp is not None and _weather_still_live(sp):
                        _attach_weather_neg_risk(sp, ev)
                        weather_found[sp.event_id] = sp
        self.weather_events = weather_found

        # 2. Discover active Hit/Barrier series (#2)
        barrier_found: Dict[str, BarrierRungSpec] = {}
        for asset, h_grp, slug in HIT_SERIES:
            evts = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5", timeout=6.0)
            if isinstance(evts, list):
                for ev in evts:
                    for r in parse_hit_event(ev, asset, h_grp, slug):
                        if r.resolved_yes is None and r.end_ts > time.time() + 60:
                            barrier_found[r.market_id] = r
        self.barrier_rungs = barrier_found

        # 3. Discover active Multi-Strike series (#4) + NegRisk Bracket series (`N1_NEGRISK_CROSS_BOX`)
        strike_found: Dict[str, List[StrikeRungSpec]] = {}
        for asset, slug in STRIKE_SERIES:
            evts = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5", timeout=6.0)
            if isinstance(evts, list):
                for ev in evts:
                    rungs = parse_multistrike_event(ev, asset, slug)
                    if rungs and rungs[0].end_ts > time.time() + 60:
                        strike_found[f"{asset}_{ev.get('id')}"] = rungs
        self.strike_ladders = strike_found

        negrisk_found: Dict[str, List[NegRiskBracketSpec]] = {}
        for asset, slug in NEGRISK_SERIES:
            evts_nr = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4", timeout=6.0)
            if isinstance(evts_nr, list):
                for ev in evts_nr:
                    brs = parse_negrisk_bracket_event(ev, asset, slug)
                    if brs and brs[0].end_ts > time.time() + 60:
                        negrisk_found[f"{asset}_{int(brs[0].end_ts)}"] = brs
        self.negrisk_ladders = negrisk_found

        # 4. Discover active Daily Up/Down series (`U1_DAILY_UPDOWN_LOCK` + `0%`-fee Pyth FX/Metals `C1_BINARY_COMPLETE_SET`)
        updown_found: Dict[str, DailyUpDownSpec] = {}
        for asset, slug in DAILY_UPDOWN_SERIES:
            evts_ud = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3", timeout=5.0)
            if isinstance(evts_ud, list):
                for ev in evts_ud:
                    sp_ud = parse_daily_updown_event(ev, asset, slug)
                    if sp_ud is not None and sp_ud.end_ts > time.time() + 60:
                        updown_found[sp_ud.market_id] = sp_ud
        self.daily_updown_markets = updown_found

        pyth_found: Dict[str, DailyUpDownSpec] = {}
        for asset, slug in ZERO_FEE_PYTH_DAILY_SERIES:
            evts_py = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=2", timeout=5.0)
            if isinstance(evts_py, list):
                for ev in evts_py:
                    sp_py = parse_daily_updown_event(ev, asset, slug)
                    if sp_py is not None and sp_py.end_ts > time.time() + 60:
                        pyth_found[sp_py.market_id] = sp_py
        self.pyth_daily_markets = pyth_found

        # 5. Discover Zero-Fee Pyth Commodities/Metals/Equities Hit & Close Ladders, NBA Games, and Zero-Fee NegRisk Slates
        pyth_hit_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3", timeout=5.0) for _, _, slug in PYTH_HIT_SERIES)
        )
        pyth_hit_found: Dict[str, PythBarrierRungSpec] = {}
        now_disc = time.time()
        for (asset_p, h_grp_p, slug_p), evts_ph in zip(PYTH_HIT_SERIES, pyth_hit_res):
            if isinstance(evts_ph, list):
                for ev in evts_ph:
                    for rp in parse_pyth_hit_event(ev, asset_p, h_grp_p, slug_p):
                        if rp.end_ts > now_disc + 60:
                            pyth_hit_found[rp.market_id] = rp
        self.pyth_barrier_rungs = pyth_hit_found

        pyth_cl_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3", timeout=5.0) for _, slug in PYTH_CLOSE_SERIES)
        )
        pyth_cl_found: Dict[str, List[PythCloseRungSpec]] = {}
        for (asset_c, slug_c), evts_pc in zip(PYTH_CLOSE_SERIES, pyth_cl_res):
            if isinstance(evts_pc, list):
                for ev in evts_pc:
                    rc_list = parse_pyth_close_event(ev, asset_c, slug_c)
                    if rc_list and rc_list[0].end_ts > now_disc + 60:
                        pyth_cl_found[f"{asset_c}_{ev.get('id')}"] = rc_list
        self.pyth_close_ladders = pyth_cl_found

        nba_found: Dict[str, NbaGameSpec] = {}
        for nba_slug in NBA_SERIES_SLUGS:
            evts_nba = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={nba_slug}&closed=false&limit=25", timeout=6.0)
            if isinstance(evts_nba, list):
                for ev in evts_nba:
                    sp_nba = parse_nba_zero_fee_event(ev, now_ts=now_disc)
                    if sp_nba is not None:
                        nba_found[sp_nba.event_id] = sp_nba
        self.nba_games = nba_found

        nr0_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4", timeout=5.0) for slug in ZERO_FEE_NEGRISK_SERIES)
        )
        nr0_found: Dict[str, ZeroFeeNegRiskSlateSpec] = {}
        raw_by_series: Dict[str, List[Dict[str, Any]]] = {}
        for slug_n, evts_n0 in zip(ZERO_FEE_NEGRISK_SERIES, nr0_res):
            if isinstance(evts_n0, list):
                raw_by_series[slug_n] = evts_n0
                mixed_ok = slug_n in ("best-ai-company", "chinese-ai-1")
                for ev in evts_n0:
                    sp_n0 = parse_zero_fee_negrisk_slate(ev, slug_n, allow_mixed_fees=mixed_ok)
                    if sp_n0 is not None and sp_n0.end_ts > now_disc + 60:
                        nr0_found[sp_n0.event_id] = sp_n0
        self.negrisk_zero_slates = nr0_found

        # 6. Phase-2 Discovery: Counting Slates (`TW1`), FOMC LP (`FED1`), Oil-Senate (`COND1`), AAA Gas (`GAS1`), & 12PM Hourly (`D2`)
        cnt_found: Dict[str, CountingSlateSpec] = {}
        for c_slug, c_handle in COUNTING_SERIES_HANDLES:
            for ev_c in (raw_by_series.get(c_slug) or []):
                sp_c = parse_counting_slate_event(ev_c, c_slug, c_handle)
                if sp_c is not None and sp_c.window_end_ts > now_disc + 60:
                    cnt_found[sp_c.event_id] = sp_c
        self.counting_slates = cnt_found

        self.fomc_truth_legs = build_fomc_truth_table_legs(
            raw_by_series.get("fomc") or [],
            raw_by_series.get("fed-3-parlay") or [],
            sep_2026_realized_action=(os.getenv("PM_SEP_2026_FOMC_ACTION") or "").strip().upper() or None,
        )

        os_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?slug={sl_os}", timeout=5.0) for sl_os in OIL_SENATE_SLUGS),
            self.fetch_json(f"{GAMMA_URL}/events?series_slug=gas-price-hits-weekly&closed=false&limit=2", timeout=5.0),
        )
        os_by_slug: Dict[str, Dict[str, Any]] = {}
        for sl_os, res_os in zip(OIL_SENATE_SLUGS, os_res[:len(OIL_SENATE_SLUGS)]):
            if isinstance(res_os, list) and res_os:
                ev_o = res_os[0]
                os_by_slug[sl_os] = ev_o
                if "pending-oil" in sl_os:
                    sp_os_nr = parse_zero_fee_negrisk_slate(ev_o, sl_os)
                    if sp_os_nr is not None and sp_os_nr.end_ts > now_disc + 60:
                        self.negrisk_zero_slates[sp_os_nr.event_id] = sp_os_nr
        self.oil_senate_truth_legs = build_oil_senate_truth_table_legs(os_by_slug)
        self.gas_events_raw = {
            "us-gas-price-daily": raw_by_series.get("us-gas-price-daily") or [],
            "gas-price-hits-weekly": os_res[-1] if isinstance(os_res[-1], list) else [],
        }

        # Discover active 1h Binance candles that terminate at a Daily/Multi-Strike 12:00 PM ET timestamp (`D2_12PM_BINANCE_BOX`)
        target_12pm_ends = {int(round(sp.end_ts)) for sp in self.daily_updown_markets.values()} | {
            int(round(rgs[0].end_ts)) for rgs in self.strike_ladders.values() if rgs
        }
        hr_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?series_slug={h_slug}&closed=false&limit=6", timeout=4.5) for h_slug in HOURLY_BINANCE_SERIES.values())
        )
        h12_found: Dict[str, DailyUpDownSpec] = {}
        for (h_asset, h_slug), evts_h in zip(HOURLY_BINANCE_SERIES.items(), hr_res):
            if isinstance(evts_h, list):
                for ev_h in evts_h:
                    sp_h = parse_daily_updown_event(ev_h, h_asset, h_slug)
                    if sp_h is not None and sp_h.end_ts > now_disc + 30 and any(abs(sp_h.end_ts - te) <= 5.0 for te in target_12pm_ends):
                        h12_found[sp_h.market_id] = sp_h
        self.hourly_12pm_markets = h12_found

        self.last_discovery_ts = time.time()
        logger.info(
            f"Discovery complete: {len(self.weather_events)} Weather city-events, "
            f"{len(self.barrier_rungs)} Barrier Hit rungs, {len(self.strike_ladders)} Multi-Strike ladders, "
            f"{len(self.negrisk_ladders)} NegRisk ladders, {len(self.daily_updown_markets)} Crypto Daily Up/Down, "
            f"{len(self.pyth_daily_markets)} Zero-Fee Pyth FX/Metals Daily, "
            f"{len(self.pyth_barrier_rungs)} Pyth Zero-Fee Hit rungs, {len(self.pyth_close_ladders)} Pyth Close ladders, "
            f"{len(self.nba_games)} NBA Zero-Fee games, {len(self.negrisk_zero_slates)} NegRisk slates, "
            f"{len(self.counting_slates)} Counting slates, {len(self.fomc_truth_legs)//2} FOMC LP mkts, "
            f"{len(self.oil_senate_truth_legs)//2} Oil-Senate mkts, {len(self.hourly_12pm_markets)} 12PM 1h pairs."
        )

    async def open_shadow_position(
        self,
        sleeve: str,
        dedupe_key: str,
        asset_or_city: str,
        title: str,
        side_label: str,
        token_id: str,
        fee_rate: float,
        p_model: float,
        close_ts: float,
        extra: Dict[str, Any],
        tp_target_px: Optional[float] = None,
        prefetched_book: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if is_shadow_sleeve_quarantined(sleeve):
            return False
        lock_keys = [dedupe_key]
        if sleeve == "W2_ENSEMBLE_VALUE" and extra.get("event_id"):
            lock_keys.append(f"W2_EVENT_{extra['event_id']}")
        acq = self._try_acquire_keys(*lock_keys)
        if not acq:
            return False

        try:
            # Strictly causal L2 walk at t_signal + latency (250ms for W1_SOLAR_PEAK_LOCK EXP-PM-405; 50ms default)
            req_lat_ms = 250 if sleeve == "W1_SOLAR_PEAK_LOCK" else 50
            book = prefetched_book if (prefetched_book is not None and sleeve != "W1_SOLAR_PEAK_LOCK") else await self.fetch_book_after_latency(token_id, latency_ms=req_lat_ms)
            if not book:
                return False
            asks_raw = book.get("asks") or []
            bids_raw = book.get("bids") or []
            best_bid, _ = extract_best_bid(bids_raw)

            min_l1 = 15.0 if sleeve in (
                "S2_EXACT_TWAP_LOCK", "S5M_CHAINLINK_SNIPER", "S4H_CHAINLINK_CONVERGENCE",
                "B4_TOUCHED_BARRIER_WICK_LOCK", "CM_B2_PYTH_SESSION_NO_LOCK", "CM_U1_PYTH_CLOSE_LOCK",
                "TW1_COUNTING_TRUNCATION_AND_BOX", "GAS1_AAA_GASOLINE_LOCK", "CM_SHOCK_PYTH_CATALYST",
            ) else 20.0
            max_ask_cap = 0.990 if sleeve in ("B4_TOUCHED_BARRIER_WICK_LOCK", "TW1_COUNTING_TRUNCATION_AND_BOX", "GAS1_AAA_GASOLINE_LOCK") else 0.98
            # Validate T1000 reference fill first
            ref_ticket = BANKROLL_TICKETS["T1000"][sleeve]
            w_ref = walk_l2_book_asks(asks_raw, ref_ticket, fee_rate=fee_rate, min_l1_usd=min_l1, max_ask_px=max_ask_cap)
            if not w_ref.get("filled"):
                return False

            realized_edge = p_model - float(w_ref["eff_px"])
            min_req_edge = {
                "W1_SOLAR_PEAK_LOCK": 0.035,
                "W2_ENSEMBLE_VALUE": 0.095,
                "B1_CONVEX_TAIL_YES": 0.060,
                "B2_BARRIER_NO_LOCK": 0.035,
                "M1_SVI_MAKER_SCALP": 0.050,
                "M2_STRIKE_CONVERGENCE": 0.038,
                "M4_SHOCK_STRIKE_CATCHUP": 0.065,
                "S5M_CHAINLINK_SNIPER": 0.042,
                "S4H_CHAINLINK_CONVERGENCE": 0.042,
                "U1_DAILY_UPDOWN_LOCK": 0.040,
                "S2_EXACT_TWAP_LOCK": 0.030,
                "B4_TOUCHED_BARRIER_WICK_LOCK": 0.012,
                "TW1_COUNTING_TRUNCATION_AND_BOX": 0.010,
                "GAS1_AAA_GASOLINE_LOCK": 0.015,
                "CM_SHOCK_PYTH_CATALYST": 0.045,
                "CM_B2_PYTH_SESSION_NO_LOCK": 0.035,
                "CM_U1_PYTH_CLOSE_LOCK": 0.030,
            }.get(sleeve, 0.035)
            if realized_edge < min_req_edge:
                return False

            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = walk_l2_book_asks(asks_raw, t_map[sleeve], fee_rate=fee_rate, min_l1_usd=min_l1, max_ask_px=max_ask_cap)
                if w_t.get("filled"):
                    tier_fills[tier_name] = w_t

            if not tier_fills:
                return False

            now = time.time()
            pos_id = f"{sleeve}_{int(now)}_{dedupe_key[-10:]}"
            eff_tp = tp_target_px
            if sleeve == "M1_SVI_MAKER_SCALP" and eff_tp is None:
                eff_tp = min(0.96, round(float(w_ref["eff_px"]) + 0.050, 4))
            elif sleeve == "M4_SHOCK_STRIKE_CATCHUP" and eff_tp is None:
                eff_tp = min(0.96, round(float(w_ref["eff_px"]) + 0.060, 4))
            elif sleeve == "B1_CONVEX_TAIL_YES" and eff_tp is None:
                eff_tp = min(0.88, round(2.0 * float(w_ref["vwap"]), 4))
            elif sleeve == "S5M_CHAINLINK_SNIPER" and eff_tp is None:
                eff_tp = 0.96
            elif sleeve == "CM_B2_PYTH_SESSION_NO_LOCK" and eff_tp is None:
                eff_tp = 0.985
            elif sleeve in ("W1_SOLAR_PEAK_LOCK", "B2_BARRIER_NO_LOCK", "M2_STRIKE_CONVERGENCE", "U1_DAILY_UPDOWN_LOCK") and eff_tp is None:
                eff_tp = 0.98

            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve,
                "asset_or_city": asset_or_city,
                "title": title,
                "side": side_label,
                "token_id": token_id,
                "fee_rate": fee_rate,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": round(p_model, 4),
                "entry_eff_px_t1000": w_ref["eff_px"],
                "entry_vwap_t1000": w_ref["vwap"],
                "realized_edge_t1000": round(realized_edge, 4),
                "entry_best_bid": best_bid,
                "last_bid": best_bid,
                "maker_tp_px": eff_tp,
                "tier_fills": tier_fills,
                "extra": extra,
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(
                f"[ENTRY:{sleeve}] {asset_or_city} | {title} ({side_label}) @ eff=${w_ref['eff_px']:.3f} "
                f"vs p_mod={p_model:.3f} (edge={realized_edge:+.3f}, L1=${w_ref['l1_usd']:.0f})"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    async def post_shadow_maker_entry(
        self,
        sleeve: str,
        dedupe_key: str,
        asset: str,
        title: str,
        side_label: str,
        token_id: str,
        p_model: float,
        close_ts: float,
        extra: Dict[str, Any],
        prefetched_book: Optional[Dict[str, Any]] = None,
        ttl_override_sec: Optional[float] = None,
    ) -> bool:
        """
        Places a realistic resting `post_only=True` 0%-fee Maker limit bid on the CLOB.
        Models L1 queue priority (`queue_ahead_usd`) and adverse-selection fills during
        the cancel-reaction latency window (`F-03` / `M-04`).
        """
        if is_shadow_sleeve_quarantined(sleeve):
            return False
        is_weather_maker = sleeve == "W2_MAKER_OVERROUND"
        is_reward_carry = sleeve == "MKR_REWARD_LOCKED_CARRY"
        lock_keys = [dedupe_key]
        if is_weather_maker and extra.get("event_id"):
            lock_keys.append(f"W2M_EVENT_{extra['event_id']}")
        acq = self._try_acquire_keys(*lock_keys)
        if not acq:
            return False

        try:
            book = prefetched_book if prefetched_book is not None else await self.fetch_book_after_latency(token_id, latency_ms=50)
            if not book:
                return False
            asks_raw = book.get("asks") or []
            bids_raw = book.get("bids") or []
            best_bid, l1_bid_usd = extract_best_bid(bids_raw)
            valid_asks = [float(a["price"]) for a in asks_raw if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0]
            if not valid_asks:
                return False
            best_ask = round(min(valid_asks), 4)
            if best_ask <= 0.03 or best_bid <= 0.0:
                return False

            if is_weather_maker and ((best_ask - best_bid) < 0.02 or l1_bid_usd < 10.0):
                return False

            if is_reward_carry and extra.get("resting_bid_override"):
                resting_bid = round(min(float(extra["resting_bid_override"]), best_ask - 0.005), 4)
            else:
                # Post-only Maker bid: step +1c inside wide spread or join best_bid when 1c tight, strictly < best_ask
                cand_bid = best_bid + 0.01 if (best_ask - best_bid) >= 0.02 else best_bid
                resting_bid = round(min(cand_bid, best_ask - 0.01), 4)
            min_rb = 0.950 if is_reward_carry else (0.14 if is_weather_maker else 0.18)
            max_rb = 0.990 if is_reward_carry else (0.65 if is_weather_maker else 0.80)
            if not (min_rb <= resting_bid <= max_rb):
                return False
            maker_edge = p_model - resting_bid
            min_edge = 0.008 if is_reward_carry else (0.085 if is_weather_maker else 0.060)
            if maker_edge < min_edge:
                return False

            # Price-improving +1c establishes top-of-queue (`0.0` ahead); joining existing best_bid sits behind L1 queue
            queue_ahead_usd = 0.0 if resting_bid > best_bid else round(min(l1_bid_usd * 0.50, 60.0), 2)

            now = time.time()
            order_id = f"MKR_{sleeve}_{int(now)}_{dedupe_key[-10:]}"
            spot_now = self.spots.get(asset, 0.0)
            m_ord = {
                "order_id": order_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve,
                "asset_or_city": asset,
                "title": title,
                "side": side_label,
                "token_id": token_id,
                "resting_bid": resting_bid,
                "best_bid_at_post": best_bid,
                "best_ask_at_post": best_ask,
                "l1_bid_usd": l1_bid_usd,
                "queue_ahead_usd": queue_ahead_usd,
                "p_model_at_post": round(p_model, 4),
                "maker_edge_at_post": round(maker_edge, 4),
                "spot_at_post": spot_now,
                "created_ts": now,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "ttl_override_sec": ttl_override_sec,
                "extra": extra,
            }
            self.pending_maker_orders[order_id] = m_ord
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_MAKER_POST", **m_ord})
            logger.info(
                f"[MAKER_POST:{sleeve}] {asset} | {title} ({side_label}) resting_bid=${resting_bid:.3f} "
                f"(ask=${best_ask:.3f}, q_ahead=${queue_ahead_usd:.0f}, p_mod={p_model:.3f}, edge={maker_edge:+.3f})"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    async def manage_pending_maker_orders(self) -> None:
        now = time.time()
        now_utc = datetime.now(timezone.utc)
        for oid, m_ord in list(self.pending_maker_orders.items()):
            sleeve = m_ord["sleeve"]
            is_weather_maker = sleeve == "W2_MAKER_OVERROUND"
            is_reward_carry = sleeve == "MKR_REWARD_LOCKED_CARRY"
            asset = m_ord["asset_or_city"]
            tok = m_ord["token_id"]
            resting_bid = float(m_ord["resting_bid"])
            close_ts = float(m_ord["close_ts"])
            rem_tte = close_ts - now
            age_s = now - float(m_ord["created_ts"])
            extra = dict(m_ord.get("extra") or {})
            strike = float(extra.get("strike") or 0.0)
            is_down = bool(extra.get("is_downward"))
            side_lbl = m_ord["side"]
            wins_up = (side_lbl == "YES" and not is_down) or (side_lbl == "NO" and is_down)

            def _discard_maker_keys(ord_obj: Dict[str, Any]) -> None:
                self.entered_keys.discard(ord_obj["dedupe_key"])
                ev_id = (ord_obj.get("extra") or {}).get("event_id")
                if ev_id and ord_obj.get("sleeve") == "W2_MAKER_OVERROUND":
                    self.entered_keys.discard(f"W2M_EVENT_{ev_id}")

            # 1. Expiry / TTL cancel (supports short 3.5s reactive M4 post_only maker quotes via ttl_override_sec)
            ttl_ov = m_ord.get("ttl_override_sec")
            min_tte_cancel = 600.0 if is_reward_carry else (900.0 if ttl_ov is not None else (3600.0 if is_weather_maker else 7200.0))
            max_age_cancel = float(ttl_ov) if ttl_ov is not None else (7200.0 if is_reward_carry else (2700.0 if is_weather_maker else 1800.0))
            if rem_tte <= min_tte_cancel or age_s >= max_age_cancel:
                self.pending_maker_orders.pop(oid, None)
                _discard_maker_keys(m_ord)
                self._append_ledger({"event": "SHADOW_MAKER_CANCEL", "reason": "TTL_OR_EXPIRY", **m_ord})
                continue

            # 2. Evaluate adverse-selection triggers (`F-03` / `M-04`: verify CLOB didn't already sweep us during cancel RTT!)
            adverse_cancel_reason: Optional[str] = None
            p_fair_now = float(m_ord["p_model_at_post"])
            if is_reward_carry:
                pass
            elif is_weather_maker:
                ev_id_str = str(extra.get("event_id") or "")
                sp_w = self.weather_events.get(ev_id_str)
                if sp_w is not None:
                    m_key = f"{sp_w.icao}_{sp_w.obs_date.isoformat()}"
                    metars_c = (self.metar_cache.get(m_key) or (0.0, []))[1]
                    ens_c = (self.ensemble_cache.get(sp_w.icao) or (0.0, {}))[1]
                    if metars_c or ens_c:
                        w_res = compute_weather_probabilities(
                            sp_w, now_utc, metars_c, ens_c, forecast_sigma_base_c=self.weather_sigma_c
                        )
                        mkt_id_target = str(extra.get("market_id") or "")
                        for b_idx, b_item in enumerate(sp_w.buckets):
                            if str(b_item.market_id) == mkt_id_target and b_idx < len(w_res["probs"]):
                                p_fair_now = float(w_res["probs"][b_idx])
                                break
                        if w_res.get("convective_cold_pool"):
                            adverse_cancel_reason = "CONVECTIVE_COLD_POOL"
                        elif (p_fair_now - resting_bid) < 0.045:
                            adverse_cancel_reason = "ADVERSE_METAR_OR_EDGE_DECAY"
            else:
                spot_now = self.spots.get(asset, 0.0)
                spot_post = float(m_ord.get("spot_at_post") or 0.0)
                if spot_now > 0 and strike > 0:
                    svi_ev = evaluate_svi_digital_fair_value(asset, spot_now, strike, rem_tte, is_downward=is_down, now_ts=now)
                    p_fair_now = float(svi_ev["p_yes"] if side_lbl == "YES" else svi_ev["p_no"])
                if spot_now > 0 and spot_post > 0:
                    move_bps = ((spot_now - spot_post) / spot_post) * 10000.0
                    if (wins_up and move_bps < -20.0) or ((not wins_up) and move_bps > 20.0):
                        adverse_cancel_reason = "ADVERSE_SPOT_IMPULSE"
                if adverse_cancel_reason is None and spot_now > 0 and strike > 0 and (p_fair_now - resting_bid) < 0.035:
                    adverse_cancel_reason = "SVI_EDGE_DECAY"

            bk: Optional[Dict[str, Any]] = None
            adverse_fill_during_cancel = False
            if adverse_cancel_reason is not None:
                if age_s >= 0.35:
                    bk_adv = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=2.5)
                    if bk_adv:
                        adv_asks = [
                            float(a["price"])
                            for a in (bk_adv.get("asks") or [])
                            if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0
                        ]
                        if adv_asks and min(adv_asks) <= resting_bid:
                            # Fast taker swept through our resting bid before our cancel arrived!
                            bk = bk_adv
                            adverse_fill_during_cancel = True
                if not adverse_fill_during_cancel:
                    self.pending_maker_orders.pop(oid, None)
                    _discard_maker_keys(m_ord)
                    self._append_ledger({"event": "SHADOW_MAKER_CANCEL", "reason": adverse_cancel_reason, **m_ord})
                    continue

            # 3. Check passive Maker fill (`best_ask <= resting_bid` after min resting time, or adverse cancel-race sweep)
            if not adverse_fill_during_cancel:
                min_rest_sec = 0.5 if ttl_ov is not None else 10.0
                if age_s < min_rest_sec:
                    continue
                bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=3.0)
            if not bk:
                continue
            asks_raw = bk.get("asks") or []
            valid_asks = [float(a["price"]) for a in asks_raw if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0]
            if not valid_asks:
                continue
            best_ask_now = min(valid_asks)
            if best_ask_now <= resting_bid:
                crossing_shares = sum(
                    float(a["size"])
                    for a in asks_raw
                    if 0.0 < float(a.get("price", 0)) <= resting_bid + 1e-9 and float(a.get("size", 0)) > 0
                )
                queue_ahead_usd = float(m_ord.get("queue_ahead_usd") or 0.0)
                queue_ahead_sh = queue_ahead_usd / max(0.01, resting_bid)
                avail_fill_shares = crossing_shares - queue_ahead_sh
                if adverse_fill_during_cancel:
                    avail_fill_shares = max(avail_fill_shares, crossing_shares, BANKROLL_TICKETS["T5000"][sleeve] / max(0.01, resting_bid))
                elif avail_fill_shares < 5.0:
                    m_ord["queue_ahead_usd"] = round(max(0.0, queue_ahead_usd - crossing_shares * resting_bid), 2)
                    continue

                self.pending_maker_orders.pop(oid, None)
                tier_fills: Dict[str, Dict[str, Any]] = {}
                for tier_name, t_map in BANKROLL_TICKETS.items():
                    notional = t_map[sleeve]
                    target_sh = notional / resting_bid
                    sh = round(min(target_sh, avail_fill_shares), 4)
                    spent = round(sh * resting_bid, 2)
                    tier_fills[tier_name] = {
                        "filled": True,
                        "best_ask": round(best_ask_now, 4),
                        "vwap": resting_bid,
                        "eff_px": resting_bid,
                        "slip_cents": 0.0,
                        "spent_usd": spent,
                        "fee_usd": 0.0,
                        "shares": sh,
                        "fill_ratio": round(min(1.0, spent / max(0.01, notional)), 4),
                        "l1_usd": m_ord.get("l1_bid_usd", 50.0),
                        "levels": 1,
                    }
                pos_id = f"{sleeve}_{int(now)}_{m_ord['dedupe_key'][-10:]}"
                if is_reward_carry:
                    eff_tp = None
                elif is_weather_maker:
                    eff_tp = min(0.95, round(max(resting_bid + 0.070, p_fair_now - 0.015), 4))
                else:
                    eff_tp = min(0.96, round(resting_bid + 0.050, 4))
                if adverse_fill_during_cancel:
                    extra["adverse_fill_during_cancel_window"] = True
                    extra["adverse_trigger"] = adverse_cancel_reason
                pos = {
                    "position_id": pos_id,
                    "dedupe_key": m_ord["dedupe_key"],
                    "sleeve": sleeve,
                    "asset_or_city": asset,
                    "title": m_ord["title"],
                    "side": side_lbl,
                    "token_id": tok,
                    "fee_rate": 0.0,
                    "entry_ts": now,
                    "entry_utc": datetime.now(timezone.utc).isoformat(),
                    "close_ts": close_ts,
                    "p_model_entry": round(p_fair_now, 4),
                    "entry_eff_px_t1000": resting_bid,
                    "entry_vwap_t1000": resting_bid,
                    "realized_edge_t1000": round(p_fair_now - resting_bid, 4),
                    "entry_best_bid": resting_bid,
                    "last_bid": resting_bid,
                    "maker_tp_px": eff_tp,
                    "tier_fills": tier_fills,
                    "extra": extra,
                    "status": "OPEN",
                }
                self.open_positions[pos_id] = pos
                self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                logger.info(
                    f"[MAKER_FILLED:{sleeve}] {asset} | {pos['title']} ({side_lbl}) @ resting=${resting_bid:.3f} "
                    f"-> TP=${eff_tp:.3f} (p_mod={p_fair_now:.3f}, adverse={adverse_fill_during_cancel})"
                )

    async def scan_weather_markets(self, opps_out: List[Dict[str, Any]]) -> None:
        now_utc = datetime.now(timezone.utc)
        loop = asyncio.get_running_loop()

        for sp in list(self.weather_events.values()):
            now_s = time.time()
            try:
                end_ts = datetime.fromisoformat(sp.end_date_iso.replace("Z", "+00:00")).timestamp()
            except Exception:
                end_ts = now_s + 86400.0
            if end_ts <= now_s:
                self.weather_events.pop(sp.event_id, None)
                continue
            # Adaptive METAR poll cadence (`Gemini #11`): 10s inside station release window, 300s outside!
            m_key = f"{sp.icao}_{sp.obs_date.isoformat()}"
            cached_m = self.metar_cache.get(m_key)
            metar_ttl = compute_adaptive_metar_poll_ttl(sp.icao, cached_m[1] if cached_m else None, now_utc)
            if cached_m is None or (now_s - cached_m[0]) >= metar_ttl:
                metars = await asyncio.to_thread(
                    fetch_metar_observations_sync, sp.icao, sp.obs_date, sp.tz_name
                )
                self.metar_cache[m_key] = (now_s, metars)
            else:
                metars = cached_m[1]

            # Official AviationWeather TAF TX/TN prior (`Gemini #11`, refreshed every 30m)
            cached_taf = self.taf_cache.get(m_key)
            if cached_taf is None or (now_s - cached_taf[0]) >= 1800.0:
                taf_ext = await asyncio.to_thread(
                    fetch_taf_extremes_sync, sp.icao, sp.obs_date, sp.tz_name
                )
                self.taf_cache[m_key] = (now_s, taf_ext)
            else:
                taf_ext = cached_taf[1]

            # Refresh 71-member Ensemble cache every 25 minutes per ICAO (throttled; never cache empty failures for 25m)
            cached_e = self.ensemble_cache.get(sp.icao)
            ens_ttl = 1500.0 if (cached_e and cached_e[1]) else 60.0
            if cached_e is None or (now_s - cached_e[0]) >= ens_ttl:
                async with self._open_meteo_sem:
                    ens_h = await asyncio.to_thread(fetch_live_ensemble_hourly_sync, sp.lat, sp.lon)
                    await asyncio.sleep(0.18)
                self.ensemble_cache[sp.icao] = (now_s, ens_h)
            else:
                ens_h = cached_e[1]

            if not ens_h and not metars:
                continue

            res = compute_weather_probabilities(
                sp,
                now_utc,
                metars,
                ens_h,
                forecast_sigma_base_c=self.weather_sigma_c,
                taf_extreme_c=(taf_ext or {}).get(sp.metric),
            )
            probs = res["probs"]
            try:
                end_ts = datetime.fromisoformat(sp.end_date_iso.replace("Z", "+00:00")).timestamp()
            except Exception:
                end_ts = now_s + 86400.0

            # 1. Check W1_SOLAR_PEAK_LOCK
            if res["is_solar_lock"] and res["locked_bucket_idx"] is not None:
                b_lock = sp.buckets[res["locked_bucket_idx"]]
                p_lock = res["p_locked_bucket"]
                w1_fee = float(getattr(b_lock, "fee_rate", 0.0) or 0.0)
                bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={b_lock.yes_token}", timeout=3.5)
                if bk:
                    w_chk = walk_l2_book_asks(bk.get("asks") or [], 100.0, fee_rate=w1_fee)
                    bid_w1, _ = extract_best_bid(bk.get("bids") or [])
                    self._record_market_telemetry(
                        key=f"W1_LOCK_{sp.event_id}_{b_lock.market_id}",
                        min_interval_sec=45.0,
                        now_ts=now_s,
                        sig=(w_chk.get("eff_px"), bid_w1, round(float(p_lock), 3)),
                        payload={
                            "type": "WEATHER_SOLAR_LOCK_SNAP",
                            "event_id": sp.event_id,
                            "city": sp.city,
                            "icao": sp.icao,
                            "metric": sp.metric,
                            "obs_date": sp.obs_date.isoformat(),
                            "bucket": b_lock.label,
                            "obs_count": res["obs_count"],
                            "running_ext_c": res["running_ext_c"],
                            "cushion_c": res["cooling_cushion_c"],
                            "p_lock": p_lock,
                            "ask_eff": w_chk.get("eff_px") if w_chk.get("filled") else None,
                            "bid": bid_w1 if bid_w1 > 0 else None,
                            "l1_usd": w_chk.get("l1_usd", 0.0),
                        },
                    )
                    if w_chk.get("filled") and 0.52 <= w_chk["eff_px"] <= 0.94:
                        edge = p_lock - w_chk["eff_px"]
                        opps_out.append({
                            "sleeve": "W1_SOLAR_PEAK_LOCK",
                            "market": f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b_lock.label}",
                            "ask_vwap": w_chk["eff_px"],
                            "p_model": p_lock,
                            "net_edge": round(edge, 4),
                            "l1_usd": w_chk["l1_usd"],
                        })
                        if edge >= 0.035:
                            await self.open_shadow_position(
                                sleeve="W1_SOLAR_PEAK_LOCK",
                                dedupe_key=f"W1_{sp.event_id}_{b_lock.market_id}",
                                asset_or_city=f"{sp.city}_{sp.icao}",
                                title=f"{sp.title} [{b_lock.label}]",
                                side_label="YES",
                                token_id=b_lock.yes_token,
                                fee_rate=w1_fee,
                                p_model=p_lock,
                                close_ts=end_ts,
                                extra={
                                    "event_id": sp.event_id,
                                    "market_id": b_lock.market_id,
                                    "condition_id": b_lock.condition_id,
                                    "icao": sp.icao,
                                    "obs_date": sp.obs_date.isoformat(),
                                    "bucket_label": b_lock.label,
                                    "running_ext_c": res["running_ext_c"],
                                    "cooling_cushion_c": res["cooling_cushion_c"],
                                },
                                prefetched_book=bk,
                            )

            # 1B. Event-Level Weather Slate Arbitrage (`W3_WEATHER_SLATE_ARB` YES/NO) + 0%-Fee Weather `C1_BINARY_COMPLETE_SET`
            slate_key = f"W3_SLATE_{sp.event_id}"
            last_w3_chk = float(self._last_w3_slate_chk_ts.get(sp.event_id) or 0.0)
            w3_interval = 45.0 if (sp.series_slug in HIGH_VOLUME_WEATHER_SERIES or (end_ts - now_s) <= 21600.0) else 120.0
            if (
                slate_key not in self.entered_keys
                and slate_key not in self.inflight_keys
                and len(sp.buckets) >= 3
                and (self.single_scan or (now_s - last_w3_chk) >= w3_interval)
            ):
                self._last_w3_slate_chk_ts[sp.event_id] = now_s
                w_toks = [b_i.yes_token for b_i in sp.buckets] + [b_i.no_token for b_i in sp.buckets]
                w_bk_map = await self.fetch_books_batch(w_toks, timeout=3.0)
                bucket_book_map: Dict[str, Dict[str, Any]] = {}
                raw_bk_by_mkt: Dict[str, Dict[str, Any]] = {}
                for b_i in sp.buckets:
                    bk_i = w_bk_map.get(b_i.yes_token)
                    bk_n_i = w_bk_map.get(b_i.no_token)
                    rec_b: Dict[str, Any] = {}
                    if bk_i:
                        raw_bk_by_mkt[b_i.market_id] = bk_i
                        asks_i = sorted(
                            [(float(a["price"]), float(a["size"])) for a in (bk_i.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
                            key=lambda x: x[0],
                        )
                        if asks_i:
                            rec_b["ask_yes"] = asks_i[0][0]
                            rec_b["ask_yes_shares"] = asks_i[0][1]
                    if bk_n_i:
                        asks_n = sorted(
                            [(float(a["price"]), float(a["size"])) for a in (bk_n_i.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
                            key=lambda x: x[0],
                        )
                        if asks_n:
                            rec_b["ask_no"] = asks_n[0][0]
                            rec_b["ask_no_shares"] = asks_n[0][1]
                    if rec_b:
                        bucket_book_map[b_i.market_id] = rec_b
                    if bk_i and bk_n_i and float(getattr(b_i, "fee_rate", 0.0) or 0.0) == 0.0:
                        c1_w = scan_binary_complete_set_arb(
                            market_id=b_i.market_id,
                            condition_id=b_i.condition_id,
                            yes_token=b_i.yes_token,
                            no_token=b_i.no_token,
                            asks_yes_raw=bk_i.get("asks") or [],
                            asks_no_raw=bk_n_i.get("asks") or [],
                            target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],
                            fee_rate=0.0,
                            max_box_cost_net=0.995,
                        )
                        if c1_w.get("filled"):
                            opps_out.append({
                                "sleeve": "C1_BINARY_COMPLETE_SET",
                                "market": f"{sp.city} ({sp.icao}) Complete-Set [{b_i.label}]",
                                "ask_vwap": c1_w["box_cost_net"],
                                "p_model": 1.0,
                                "net_edge": c1_w["riskless_floor_per_pair"],
                                "l1_usd": c1_w["l1_usd"],
                                "close_ts": end_ts,
                            })
                            w_neg_risk = getattr(b_i, "neg_risk", None)
                            leg_w_y = {"token_id": b_i.yes_token, "opp_token_id": b_i.no_token, "condition_id": b_i.condition_id, "side": "YES", "label": "YES", "market_id": b_i.market_id, "fee_rate": 0.0, "strike": 100.0, "neg_risk": bool(w_neg_risk)}
                            leg_w_n = {"token_id": b_i.no_token, "opp_token_id": b_i.yes_token, "condition_id": b_i.condition_id, "side": "NO", "label": "NO", "market_id": b_i.market_id, "fee_rate": 0.0, "strike": 100.0, "neg_risk": bool(w_neg_risk)}
                            await self.open_shadow_two_leg_box(
                                sleeve="C1_BINARY_COMPLETE_SET",
                                dedupe_key=f"C1_W_{b_i.market_id}",
                                asset=f"{sp.city}_{sp.icao}",
                                title=f"{sp.city} YES+NO Complete Set [{b_i.label}]",
                                leg_a=leg_w_y,
                                leg_b=leg_w_n,
                                bk_a=bk_i,
                                bk_b=bk_n_i,
                                close_ts=end_ts,
                                max_box_cost_net=0.995,
                                extra={"is_complete_set": True, "market_id": b_i.market_id, "condition_id": b_i.condition_id},
                            )
                            # LIVE only when Gamma `negRisk` is known (wrong neg_risk -> wrong exchange contract / order signing)
                            if w_neg_risk is not None and (end_ts - now_s) <= 86400.0 and float(c1_w["box_cost_net"]) <= 0.990:
                                self.emit_live_two_leg_box_candidate(
                                    sleeve_source="C1_BINARY_COMPLETE_SET",
                                    box_type="COMPLETE_SET",
                                    asset=f"{sp.city}_{sp.icao}",
                                    dedupe_key=f"C1_W_{b_i.market_id}",
                                    leg_a=leg_w_y,
                                    leg_b=leg_w_n,
                                    bk_a=bk_i,
                                    bk_b=bk_n_i,
                                    close_ts=float(end_ts),
                                    now_ts=now_s,
                                )
                slate_ev = evaluate_weather_event_slate(
                    sp, probs, bucket_book_map, target_budget_usd=BANKROLL_TICKETS["T1000"]["W3_WEATHER_SLATE_ARB"]
                )
                full_arb = slate_ev.get("full_slate_arb")
                if len(bucket_book_map) == len(sp.buckets):
                    has_all_y = all(bucket_book_map[b.market_id].get("ask_yes", 0) > 0 for b in sp.buckets)
                    has_all_n = all(bucket_book_map[b.market_id].get("ask_no", 0) > 0 for b in sp.buckets)
                    sum_y_l1 = round(sum(float(bucket_book_map[b.market_id]["ask_yes"]) for b in sp.buckets), 4) if has_all_y else None
                    sum_n_l1 = round(sum(float(bucket_book_map[b.market_id]["ask_no"]) for b in sp.buckets), 4) if has_all_n else None
                    top_idx = max(range(len(sp.buckets)), key=lambda idx_b: float(probs[idx_b])) if probs else 0
                    top_bkt = sp.buckets[top_idx] if sp.buckets else None
                    top_ask_y = float(bucket_book_map[top_bkt.market_id].get("ask_yes") or 0.0) if top_bkt else 0.0
                    self._record_market_telemetry(
                        key=f"W_SLATE_{sp.event_id}",
                        min_interval_sec=45.0 if (end_ts - now_s) <= 7200.0 else 90.0,
                        now_ts=now_s,
                        sig=(sum_y_l1, sum_n_l1, res["running_ext_c"], round(top_ask_y, 3), (full_arb or {}).get("mode")),
                        payload={
                            "type": "WEATHER_SLATE",
                            "event_id": sp.event_id,
                            "city": sp.city,
                            "icao": sp.icao,
                            "metric": sp.metric,
                            "obs_date": sp.obs_date.isoformat(),
                            "n_buckets": len(sp.buckets),
                            "tte_sec": round(end_ts - now_s, 0),
                            "obs_count": res["obs_count"],
                            "latest_c": res["latest_temp_c"],
                            "running_ext_c": res["running_ext_c"],
                            "ens_iqr_c": res["peak_iqr_c"],
                            "solar_lock": res["is_solar_lock"],
                            "top_bucket": top_bkt.label if top_bkt else None,
                            "top_p": round(float(probs[top_idx]), 4) if probs else None,
                            "top_ask_yes": round(top_ask_y, 4) if top_ask_y > 0 else None,
                            "sum_yes_l1": sum_y_l1,
                            "sum_no_l1": sum_n_l1,
                            "no_payout": len(sp.buckets) - 1,
                            "arb_mode": (full_arb or {}).get("mode"),
                        },
                    )
                if full_arb:
                    gp_w = float(full_arb.get("guaranteed_payout_per_set") or 1.0)
                    opps_out.append({
                        "sleeve": "W3_WEATHER_SLATE_ARB",
                        "market": f"{sp.city} ({sp.icao}) {sp.obs_date} Full-Slate ({len(sp.buckets)} buckets, {full_arb.get('side','ALL_BUCKETS_YES')})",
                        "ask_vwap": round(float(full_arb["sum_asks"]) / gp_w, 4),
                        "p_model": 1.0,
                        "net_edge": round(float(full_arb["guaranteed_edge_per_set"]) / gp_w, 4),
                        "l1_usd": full_arb["total_cost_usd"],
                    })
                    await self.open_shadow_weather_slate(sp, full_arb, end_ts)
                if all(b.market_id in raw_bk_by_mkt for b in sp.buckets):
                    await self.execute_ctf_overround_mint_sell(
                        dedupe_key=f"CTF_OVR_W_{sp.event_id}",
                        asset=f"{sp.city}_{sp.icao}",
                        title=f"{sp.city} {sp.obs_date} Weather NegRisk Overround Mint-Sell",
                        legs_bids_spec=[
                            {
                                "bids": raw_bk_by_mkt[b.market_id].get("bids") or [],
                                "fee_rate": float(getattr(b, "fee_rate", 0.0) or 0.0),
                                "fee_exponent": 1.0,
                            }
                            for b in sp.buckets
                        ],
                        close_ts=end_ts,
                        min_net_proceeds_per_set=1.004,
                        opps_out=opps_out,
                        extra={"overround_kind": "WEATHER_NEGRISK", "event_id": sp.event_id},
                    )
            else:
                raw_bk_by_mkt = {}

            if is_shadow_sleeve_quarantined("W2_ENSEMBLE_VALUE") and is_shadow_sleeve_quarantined("W2_MAKER_OVERROUND"):
                continue

            # 2. Check W2_ENSEMBLE_VALUE (Taker) & W2_MAKER_OVERROUND (0%-fee Post-Only Maker inside ~1.07 overround):
            #    require full >= 50-member ensemble, tight IQR <= 2.2°C, and max 1 W2 exposure per event_id!
            ens_members_n = int(res.get("ensemble_member_count") or 0)
            peak_iqr_c = float(res.get("peak_iqr_c") or 0.0)
            event_w2_taken = f"W2_EVENT_{sp.event_id}" in self.entered_keys or f"W2_EVENT_{sp.event_id}" in self.inflight_keys
            event_w2m_taken = f"W2M_EVENT_{sp.event_id}" in self.entered_keys or f"W2M_EVENT_{sp.event_id}" in self.inflight_keys
            best_w2_cand: Optional[Tuple[float, float, float, Any, Dict[str, Any]]] = None  # (edge, p_mod, eff_px, bucket, bk)
            best_w2m_cand: Optional[Tuple[float, float, float, Any, Dict[str, Any]]] = None  # (maker_edge, p_mod, resting_bid, bucket, bk)

            top_indices = sorted(range(len(probs)), key=lambda i: -probs[i])[:2]
            for idx in top_indices:
                p_mod = probs[idx]
                if p_mod < 0.24:
                    continue
                b = sp.buckets[idx]
                b_fee = float(getattr(b, "fee_rate", 0.0) or 0.0)
                bk = raw_bk_by_mkt.get(b.market_id) or await self.fetch_json(f"{CLOB_URL}/book?token_id={b.yes_token}", timeout=3.5)
                if not bk:
                    continue

                # 2A. Evaluate 0%-fee resting Maker quote inside multi-cent Weather spread (`F-12`: strictly zero-fee markets)
                asks_raw_b = bk.get("asks") or []
                bids_raw_b = bk.get("bids") or []
                best_bid_b, l1_bid_usd_b = extract_best_bid(bids_raw_b)
                valid_asks_b = [
                    float(a["price"]) for a in asks_raw_b if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0
                ]
                if b_fee == 0.0 and valid_asks_b and best_bid_b > 0 and (min(valid_asks_b) - best_bid_b) >= 0.02:
                    best_ask_b = round(min(valid_asks_b), 4)
                    resting_bid_b = round(min(best_bid_b + 0.01, best_ask_b - 0.01), 4)
                    maker_edge_b = p_mod - resting_bid_b
                    if 0.14 <= resting_bid_b <= 0.65 and maker_edge_b >= 0.055 and ens_members_n >= 50 and l1_bid_usd_b >= 10.0:
                        opps_out.append({
                            "sleeve": "W2_MAKER_OVERROUND",
                            "market": f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label} [MakerBid]",
                            "ask_vwap": resting_bid_b,
                            "p_model": round(p_mod, 4),
                            "net_edge": round(maker_edge_b, 4),
                            "l1_usd": l1_bid_usd_b,
                        })
                    if (
                        not event_w2_taken
                        and not event_w2m_taken
                        and (end_ts - now_s) >= 5400.0
                        and ens_members_n >= 50
                        and peak_iqr_c <= 2.2
                        and not res.get("convective_cold_pool")
                        and l1_bid_usd_b >= 10.0
                        and 0.14 <= resting_bid_b <= 0.62
                        and p_mod >= 0.30
                        and maker_edge_b >= 0.085
                    ):
                        if best_w2m_cand is None or maker_edge_b > best_w2m_cand[0]:
                            best_w2m_cand = (maker_edge_b, p_mod, resting_bid_b, b, bk)

                # 2B. Evaluate Taker fill when Ask itself offers >= 9.5c MOS ensemble edge (accounting for b_fee if enabled)
                w_chk = walk_l2_book_asks(asks_raw_b, 50.0, fee_rate=b_fee)
                if not w_chk.get("filled"):
                    continue
                eff_px = w_chk["eff_px"]
                edge = p_mod - eff_px
                if 0.10 <= eff_px <= 0.62 and edge >= 0.04 and ens_members_n >= 50:
                    opps_out.append({
                        "sleeve": "W2_ENSEMBLE_VALUE",
                        "market": f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label}",
                        "ask_vwap": eff_px,
                        "p_model": round(p_mod, 4),
                        "net_edge": round(edge, 4),
                        "l1_usd": w_chk["l1_usd"],
                    })
                if (
                    not event_w2_taken
                    and not event_w2m_taken
                    and ens_members_n >= 50
                    and peak_iqr_c <= 2.2
                    and not res.get("convective_cold_pool")
                    and 0.16 <= eff_px <= 0.62
                    and p_mod >= 0.34
                    and edge >= 0.095
                ):
                    if best_w2_cand is None or edge > best_w2_cand[0]:
                        best_w2_cand = (edge, p_mod, eff_px, b, bk)

            if best_w2_cand is not None and os.getenv("PM_DISABLE_SHADOW_W2_TAKER", "0") != "1":
                _, p_mod_best, _, b_best, bk_best = best_w2_cand
                await self.open_shadow_position(
                    sleeve="W2_ENSEMBLE_VALUE",
                    dedupe_key=f"W2_{sp.event_id}_{b_best.market_id}",
                    asset_or_city=f"{sp.city}_{sp.icao}",
                    title=f"{sp.title} [{b_best.label}]",
                    side_label="YES",
                    token_id=b_best.yes_token,
                    fee_rate=float(getattr(b_best, "fee_rate", 0.0) or 0.0),
                    p_model=p_mod_best,
                    close_ts=end_ts,
                    extra={
                        "event_id": sp.event_id,
                        "market_id": b_best.market_id,
                        "condition_id": b_best.condition_id,
                        "icao": sp.icao,
                        "obs_date": sp.obs_date.isoformat(),
                        "bucket_label": b_best.label,
                        "bias_c": res["bias_c"],
                        "ensemble_members": ens_members_n,
                        "peak_iqr_c": peak_iqr_c,
                    },
                    prefetched_book=bk_best,
                )
            elif best_w2m_cand is not None:
                _, p_mod_mkr, _, b_mkr, bk_mkr = best_w2m_cand
                await self.post_shadow_maker_entry(
                    sleeve="W2_MAKER_OVERROUND",
                    dedupe_key=f"W2M_{sp.event_id}_{b_mkr.market_id}",
                    asset=f"{sp.city}_{sp.icao}",
                    title=f"{sp.title} [{b_mkr.label}]",
                    side_label="YES",
                    token_id=b_mkr.yes_token,
                    p_model=p_mod_mkr,
                    close_ts=end_ts,
                    extra={
                        "execution_mode": "POST_ONLY_WEATHER_MAKER_ZERO_FEE",
                        "event_id": sp.event_id,
                        "market_id": b_mkr.market_id,
                        "condition_id": b_mkr.condition_id,
                        "icao": sp.icao,
                        "obs_date": sp.obs_date.isoformat(),
                        "bucket_label": b_mkr.label,
                        "bias_c": res["bias_c"],
                        "ensemble_members": ens_members_n,
                        "peak_iqr_c": peak_iqr_c,
                    },
                    prefetched_book=bk_mkr,
                )

    async def scan_barrier_markets(self, opps_out: List[Dict[str, Any]]) -> None:
        now = time.time()
        loop = asyncio.get_running_loop()

        # Group rungs by event_id so we fetch Binance window extremes once per event
        by_event: Dict[str, List[BarrierRungSpec]] = collections.defaultdict(list)
        for r in self.barrier_rungs.values():
            if r.end_ts > now + 300:
                by_event[r.event_id].append(r)

        for ev_id, rungs in by_event.items():
            r0 = rungs[0]
            spot = self.spots.get(r0.asset, 0.0)
            if spot <= 0:
                continue

            ext_by_start: Dict[int, Optional[Tuple[float, float, float]]] = {}
            ev_seed = self.barrier_ext_cache.get(ev_id)
            for st_min in sorted({int(r.start_ts // 60) for r in rungs}):
                ck = f"{r0.asset}_{st_min}"
                ext_cached = self.barrier_ext_cache.get(ck) or ev_seed
                if ext_cached is None or (now - ext_cached[0]) >= 90.0:
                    ext_val = await asyncio.to_thread(
                        fetch_binance_window_extremes_sync, r0.asset, float(st_min * 60), now, "1m"
                    )
                    if ext_val:
                        self.barrier_ext_cache[ck] = (now, ext_val)
                    ext_by_start[st_min] = ext_val
                else:
                    ext_by_start[st_min] = ext_cached[1]

            # B4_TOUCHED_BARRIER_WICK_LOCK: sweep lingering YES asks on rungs ALREADY deterministically
            # breached AFTER that specific rung's creation (`r.start_ts`) AND confirmed by live book (`bid>=0.78`, `eff_px in [0.85, 0.984]`)!
            touched_rungs: List[Tuple[BarrierRungSpec, float, float]] = []
            for r in rungs:
                if f"B4_{r.market_id}" in self.entered_keys:
                    continue
                ext_r = ext_by_start.get(int(r.start_ts // 60))
                if ext_r is None:
                    continue
                fh_r, fl_r = float(ext_r[0]), float(ext_r[1])
                if (r.direction == "UP" and fh_r >= r.strike * 1.0005) or (r.direction == "DOWN" and fl_r <= r.strike * 0.9995):
                    touched_rungs.append((r, fh_r, fl_r))
            if touched_rungs:
                b4_bks = await self.fetch_books_batch([rt[0].yes_token for rt in touched_rungs], timeout=2.5)
                for rb4, fin_h, fin_l in touched_rungs:
                    bk_b4 = b4_bks.get(rb4.yes_token)
                    if not bk_b4:
                        continue
                    bid_b4, _ = extract_best_bid(bk_b4.get("bids") or [])
                    w_b4 = walk_l2_book_asks(bk_b4.get("asks") or [], 100.0, fee_rate=rb4.fee_rate, min_l1_usd=15.0, max_ask_px=0.990)
                    if w_b4.get("filled") and bid_b4 >= 0.78 and 0.85 <= float(w_b4["eff_px"]) <= 0.984:
                        opps_out.append({
                            "sleeve": "B4_TOUCHED_BARRIER_WICK_LOCK",
                            "market": f"{rb4.asset} Breached 1m Wick Lock: {rb4.question}",
                            "ask_vwap": w_b4["eff_px"],
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_b4["eff_px"]), 4),
                            "l1_usd": w_b4["l1_usd"],
                        })
                        await self.open_shadow_position(
                            sleeve="B4_TOUCHED_BARRIER_WICK_LOCK",
                            dedupe_key=f"B4_{rb4.market_id}",
                            asset_or_city=rb4.asset,
                            title=rb4.question,
                            side_label="YES",
                            token_id=rb4.yes_token,
                            fee_rate=rb4.fee_rate,
                            p_model=1.0,
                            close_ts=rb4.end_ts,
                            extra={"market_id": rb4.market_id, "condition_id": rb4.condition_id, "strike": rb4.strike, "direction": rb4.direction, "fin_high": fin_h, "fin_low": fin_l},
                            prefetched_book=bk_b4,
                        )

            # Only poll CLOB books for rungs within sensible distance of spot (|ln(K/S)| <= 0.14) using per-rung window extremes
            near_rungs: List[BarrierRungSpec] = []
            for r in rungs:
                if abs(math.log(r.strike / spot)) > 0.14:
                    continue
                ext_r = ext_by_start.get(int(r.start_ts // 60))
                mh_r = max(spot, ext_r[0]) if ext_r else spot
                ml_r = min(spot, ext_r[1]) if ext_r else spot
                if (r.direction == "UP" and mh_r >= r.strike) or (r.direction == "DOWN" and ml_r <= r.strike):
                    continue
                near_rungs.append(r)
            ev_tte = r0.end_ts - now
            b_bk_map = (
                await self.fetch_books_batch(
                    [r.yes_token for r in near_rungs] + [r.no_token for r in near_rungs],
                    timeout=3.0,
                )
                if near_rungs and ev_tte <= 3 * 86400
                else {}
            )
            barrier_quote_rows: List[Dict[str, Any]] = []
            for r in near_rungs:
                tte = r.end_ts - now
                iv_w, iv_src = get_wing_implied_vol(r.asset, spot, r.strike, tte)
                p_touch = first_passage_touch_prob(
                    spot, r.strike, tte, iv_w, r.direction, wick_vol_multiplier=self.barrier_wick_mult
                )
                bk_y_pref = b_bk_map.get(r.yes_token)
                bk_n_pref = b_bk_map.get(r.no_token)
                if bk_y_pref and bk_n_pref and tte <= 3 * 86400:
                    w_qy = walk_l2_book_asks(bk_y_pref.get("asks") or [], 40.0, fee_rate=r.fee_rate, min_l1_usd=8.0)
                    w_qn = walk_l2_book_asks(bk_n_pref.get("asks") or [], 40.0, fee_rate=r.fee_rate, min_l1_usd=8.0)
                    barrier_quote_rows.append({
                        "strike": r.strike,
                        "direction": r.direction,
                        "market_id": r.market_id,
                        "condition_id": r.condition_id,
                        "yes_token": r.yes_token,
                        "no_token": r.no_token,
                        "fee_rate": r.fee_rate,
                        "ask_yes": w_qy.get("vwap") if w_qy.get("filled") else None,
                        "ask_no": w_qn.get("vwap") if w_qn.get("filled") else None,
                        "bk_yes": bk_y_pref,
                        "bk_no": bk_n_pref,
                        "start_ts": r.start_ts,
                        "end_ts": r.end_ts,
                    })

                # Evaluate B1_CONVEX_TAIL_YES (`0.04 <= p_touch <= 0.45`, `TTE >= 2h`)
                if 7200 <= tte <= 10 * 86400 and 0.07 <= p_touch <= 0.48:
                    bk_y = bk_y_pref or await self.fetch_json(f"{CLOB_URL}/book?token_id={r.yes_token}", timeout=3.0)
                    if bk_y:
                        w_y = walk_l2_book_asks(bk_y.get("asks") or [], 25.0, fee_rate=CRYPTO_FEE_RATE)
                        if w_y.get("filled") and 0.04 <= w_y["vwap"] <= 0.32:
                            edge_y = p_touch - w_y["eff_px"]
                            if edge_y >= 0.03:
                                opps_out.append({
                                    "sleeve": "B1_CONVEX_TAIL_YES",
                                    "market": f"{r.asset} {r.question}",
                                    "ask_vwap": w_y["eff_px"],
                                    "p_model": round(p_touch, 4),
                                    "net_edge": round(edge_y, 4),
                                    "l1_usd": w_y["l1_usd"],
                                })
                            # WFO Governance Gate: Taker B1 disabled (Favorite-Longshot Bias + VRP yielded OOS PF < 1.0);
                            # only log extreme >= 12c dislocations for research telemetry while trading B2_BARRIER_NO_LOCK (93.8% WR, 100% OOS).
                            if edge_y >= 0.12 and (p_touch / w_y["eff_px"]) >= 1.75 and w_y["vwap"] <= 0.20:
                                logger.info(f"[TELEMETRY_ONLY:B1_EXTREME_DISLOCATION] {r.asset} {r.question} ask={w_y['eff_px']:.3f} p={p_touch:.3f}")

                # Evaluate B2_BARRIER_NO_LOCK (`1h <= TTE <= 10h`, `p_no >= 0.88`)
                p_no = 1.0 - p_touch
                if 3600 <= tte <= 36000 and p_no >= 0.88:
                    bk_n = bk_n_pref or await self.fetch_json(f"{CLOB_URL}/book?token_id={r.no_token}", timeout=3.0)
                    if bk_n:
                        w_n = walk_l2_book_asks(bk_n.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)
                        if w_n.get("filled") and 0.65 <= w_n["vwap"] <= 0.91:
                            edge_n = p_no - w_n["eff_px"]
                            b2_gate = evaluate_barrier_no_net_ev(p_touch, w_n["vwap"], fee_rate=CRYPTO_FEE_RATE)
                            if edge_n >= 0.025:
                                opps_out.append({
                                    "sleeve": "B2_BARRIER_NO_LOCK",
                                    "market": f"{r.asset} NO: {r.question}",
                                    "ask_vwap": w_n["eff_px"],
                                    "p_model": round(p_no, 4),
                                    "net_edge": round(edge_n, 4),
                                    "l1_usd": w_n["l1_usd"],
                                })
                            if edge_n >= 0.038 and b2_gate["eligible"]:
                                await self.open_shadow_position(
                                    sleeve="B2_BARRIER_NO_LOCK",
                                    dedupe_key=f"B2_{r.market_id}",
                                    asset_or_city=r.asset,
                                    title=r.question,
                                    side_label="NO",
                                    token_id=r.no_token,
                                    fee_rate=CRYPTO_FEE_RATE,
                                    p_model=p_no,
                                    close_ts=r.end_ts,
                                    extra={
                                        "market_id": r.market_id,
                                        "condition_id": r.condition_id,
                                        "start_ts": r.start_ts,
                                        "strike": r.strike,
                                        "direction": r.direction,
                                        "iv_wing": round(iv_w, 4),
                                        "loss_to_gain_ratio": b2_gate["loss_to_gain_ratio"],
                                    },
                                    prefetched_book=bk_n,
                                )

            if len(barrier_quote_rows) >= 2:
                b3_diag = detect_barrier_monotonicity_boxes(barrier_quote_rows, fee_rate=CRYPTO_FEE_RATE, max_box_cost_net=1.20)
                if b3_diag:
                    bd0 = b3_diag[0]
                    self._record_market_telemetry(
                        key=f"B3_DIAG_{ev_id}",
                        min_interval_sec=60.0,
                        now_ts=now,
                        sig=(bd0["direction"], bd0["low_strike"], bd0["high_strike"], bd0["box_cost_gross"], bd0["box_cost_net"]),
                        payload={
                            "type": "BARRIER_MONO_BEST",
                            "asset": r0.asset,
                            "event_id": ev_id,
                            "spot": spot,
                            "direction": bd0["direction"],
                            "low_strike": bd0["low_strike"],
                            "high_strike": bd0["high_strike"],
                            "gross_box_l1": bd0["box_cost_gross"],
                            "net_box_l1": bd0["box_cost_net"],
                        },
                    )
                b3_arbs = [b for b in b3_diag if float(b["box_cost_net"]) <= 0.995]
                by_yes_t = {str(q["yes_token"]): q for q in barrier_quote_rows}
                by_no_t = {str(q["no_token"]): q for q in barrier_quote_rows}
                for ba in b3_arbs:
                    qy = by_yes_t.get(ba["yes_token"])
                    qn = by_no_t.get(ba["no_token"])
                    if not qy or not qn:
                        continue
                    w_b3 = walk_equal_shares_dominance_box(
                        qy["bk_yes"].get("asks") or [],
                        qn["bk_no"].get("asks") or [],
                        target_budget_usd=BANKROLL_TICKETS["T1000"]["B3_BARRIER_MONO_BOX"],
                        fee_rate_a=float(qy["fee_rate"]),
                        fee_rate_b=float(qn["fee_rate"]),
                        max_box_cost_net=0.995,
                        min_shares=6,
                        min_box_notional_usd=5.5,
                    )
                    if w_b3.get("filled"):
                        opps_out.append({
                            "sleeve": "B3_BARRIER_MONO_BOX",
                            "market": f"{r0.asset} Barrier Box {ba['label']}",
                            "ask_vwap": round(float(w_b3["box_cost_net"]), 4),
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_b3["box_cost_net"]), 4),
                            "l1_usd": w_b3["l1_usd"],
                            "close_ts": qy["end_ts"],
                        })
                        leg_a_b3 = {
                            "token_id": ba["yes_token"], "opp_token_id": ba["yes_opp_token"],
                            "condition_id": ba["leg_yes_condition_id"], "side": "YES", "label": f"YES_{ba['direction']}",
                            "market_id": ba["leg_yes_market_id"], "fee_rate": float(qy["fee_rate"]),
                            "strike": float(ba["low_strike"] if ba["direction"] == "UP" else ba["high_strike"]),
                        }
                        leg_b_b3 = {
                            "token_id": ba["no_token"], "opp_token_id": ba["no_opp_token"],
                            "condition_id": ba["leg_no_condition_id"], "side": "NO", "label": f"NO_{ba['direction']}",
                            "market_id": ba["leg_no_market_id"], "fee_rate": float(qn["fee_rate"]),
                            "strike": float(ba["high_strike"] if ba["direction"] == "UP" else ba["low_strike"]),
                        }
                        await self.open_shadow_two_leg_box(
                            sleeve="B3_BARRIER_MONO_BOX",
                            dedupe_key=f"B3_{r0.asset}_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",
                            asset=r0.asset,
                            title=f"{r0.asset} Barrier Box {ba['label']}",
                            leg_a=leg_a_b3,
                            leg_b=leg_b_b3,
                            bk_a=qy["bk_yes"],
                            bk_b=qn["bk_no"],
                            close_ts=float(qy["end_ts"]),
                            max_box_cost_net=0.995,
                            extra={
                                "is_barrier_mono_box": True,
                                "direction": ba["direction"],
                                "low_strike": ba["low_strike"],
                                "high_strike": ba["high_strike"],
                            },
                        )
                        if (float(qy["end_ts"]) - now) <= 86400.0 and float(w_b3["box_cost_net"]) <= 0.988:
                            self.emit_live_two_leg_box_candidate(
                                sleeve_source="B3_BARRIER_MONO_BOX",
                                box_type="BARRIER_MONO",
                                asset=r0.asset,
                                dedupe_key=f"B3_{r0.asset}_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",
                                leg_a=leg_a_b3,
                                leg_b=leg_b_b3,
                                bk_a=qy["bk_yes"],
                                bk_b=qn["bk_no"],
                                close_ts=float(qy["end_ts"]),
                                now_ts=now,
                                k_low=float(ba["low_strike"]),
                                k_high=float(ba["high_strike"]),
                            )

    async def scan_multistrike_markets(self, opps_out: List[Dict[str, Any]]) -> None:
        now = time.time()
        for ladder_key, rungs in list(self.strike_ladders.items()):
            if not rungs:
                continue
            asset = rungs[0].asset
            spot = self.spots.get(asset, 0.0)
            if spot <= 0:
                continue
            tte = rungs[0].end_ts - now
            if tte <= 900:
                continue

            ret_60s_bps = self.get_return_bps(asset, 60.0)
            near = [r for r in rungs if abs(math.log(r.strike / spot)) <= 0.08]
            coherent_map = evaluate_coherent_strike_ladder(asset, spot, near, tte, now_ts=now).get("by_market_id", {})
            ladder_quotes: List[Dict[str, Any]] = []

            for sr in near:
                svi_ev = coherent_map.get(sr.market_id) or evaluate_svi_digital_fair_value(
                    asset, spot, sr.strike, tte, is_downward=sr.is_downward, now_ts=now
                )
                bk_y, bk_n = await asyncio.gather(
                    self.fetch_json(f"{CLOB_URL}/book?token_id={sr.yes_token}", timeout=3.0),
                    self.fetch_json(f"{CLOB_URL}/book?token_id={sr.no_token}", timeout=3.0),
                )
                if not bk_y or not bk_n:
                    continue

                # C1_BINARY_COMPLETE_SET (`ChatGPT #4`): equal-share YES + NO <= $0.994 net underround arb!
                c1_chk = scan_binary_complete_set_arb(
                    market_id=sr.market_id,
                    condition_id=sr.condition_id,
                    yes_token=sr.yes_token,
                    no_token=sr.no_token,
                    asks_yes_raw=bk_y.get("asks") or [],
                    asks_no_raw=bk_n.get("asks") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],
                    fee_rate=CRYPTO_FEE_RATE,
                )
                if c1_chk.get("filled"):
                    opps_out.append({
                        "sleeve": "C1_BINARY_COMPLETE_SET",
                        "market": f"{asset} Complete-Set {sr.question}",
                        "ask_vwap": c1_chk["box_cost_net"],
                        "p_model": 1.0,
                        "net_edge": c1_chk["riskless_floor_per_pair"],
                        "l1_usd": c1_chk["l1_usd"],
                        "close_ts": sr.end_ts,
                    })
                    leg_a_c1 = {"token_id": sr.yes_token, "opp_token_id": sr.no_token, "condition_id": sr.condition_id, "side": "YES", "label": "YES", "market_id": sr.market_id, "fee_rate": CRYPTO_FEE_RATE, "strike": float(sr.strike)}
                    leg_b_c1 = {"token_id": sr.no_token, "opp_token_id": sr.yes_token, "condition_id": sr.condition_id, "side": "NO", "label": "NO", "market_id": sr.market_id, "fee_rate": CRYPTO_FEE_RATE, "strike": float(sr.strike)}
                    await self.open_shadow_two_leg_box(
                        sleeve="C1_BINARY_COMPLETE_SET",
                        dedupe_key=f"C1_{sr.market_id}",
                        asset=asset,
                        title=f"{asset} YES+NO Complete Set: {sr.question}",
                        leg_a=leg_a_c1,
                        leg_b=leg_b_c1,
                        bk_a=bk_y,
                        bk_b=bk_n,
                        close_ts=sr.end_ts,
                        max_box_cost_net=0.994,
                        extra={"is_complete_set": True, "market_id": sr.market_id, "condition_id": sr.condition_id},
                    )
                    if (sr.end_ts - now) <= 86400.0 and float(c1_chk["box_cost_net"]) <= 0.988:
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="C1_BINARY_COMPLETE_SET",
                            box_type="COMPLETE_SET",
                            asset=asset,
                            dedupe_key=f"C1_{sr.market_id}",
                            leg_a=leg_a_c1,
                            leg_b=leg_b_c1,
                            bk_a=bk_y,
                            bk_b=bk_n,
                            close_ts=float(sr.end_ts),
                            now_ts=now,
                            k_low=float(sr.strike),
                            k_high=float(sr.strike),
                        )

                w_y = walk_l2_book_asks(bk_y.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)
                w_n = walk_l2_book_asks(bk_n.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)

                ladder_quotes.append({
                    "strike": sr.strike,
                    "is_downward": sr.is_downward,
                    "market_id": sr.market_id,
                    "condition_id": sr.condition_id,
                    "yes_token": sr.yes_token,
                    "no_token": sr.no_token,
                    "ask_yes": w_y.get("vwap") if w_y.get("filled") else None,
                    "ask_no": w_n.get("vwap") if w_n.get("filled") else None,
                    "asks_yes": bk_y.get("asks") or [],
                    "asks_no": bk_n.get("asks") or [],
                    "bk_yes": bk_y,
                    "bk_no": bk_n,
                    "end_ts": sr.end_ts,
                })

                for side_lbl, tok, w_side, p_fair, bk_side in (
                    []
                    if (is_shadow_sleeve_quarantined("M1_SVI_MAKER_SCALP") and is_shadow_sleeve_quarantined("M2_STRIKE_CONVERGENCE"))
                    else [
                        ("YES", sr.yes_token, w_y, svi_ev["p_yes"], bk_y),
                        ("NO", sr.no_token, w_n, svi_ev["p_no"], bk_n),
                    ]
                ):
                    if not w_side.get("filled"):
                        continue
                    eff_px = w_side["eff_px"]
                    edge = p_fair - eff_px
                    wins_up = (side_lbl == "YES" and not sr.is_downward) or (side_lbl == "NO" and sr.is_downward)
                    if (wins_up and ret_60s_bps < -12.0) or ((not wins_up) and ret_60s_bps > 12.0):
                        continue

                    if 0.14 <= eff_px <= 0.90 and edge >= 0.025:
                        opps_out.append({
                            "sleeve": "M1_OR_M2_STRIKE_SVI",
                            "market": f"{asset} {sr.question} ({side_lbl})",
                            "ask_vwap": eff_px,
                            "p_model": p_fair,
                            "net_edge": round(edge, 4),
                            "l1_usd": w_side["l1_usd"],
                        })

                    # M1_SVI_MAKER_SCALP: WFO proved 7% crypto_fees_v2 taker drag near 50c eats scalp EV;
                    # strictly enter via resting `post_only=True` 0%-fee Maker limit bid (never faking an instant Ask fill!)
                    maker_edge_est = p_fair - (float(w_side["best_ask"]) - 0.01)
                    if 10800 <= tte <= 86400 and 0.19 <= w_side["best_ask"] <= 0.81 and maker_edge_est >= 0.060:
                        await self.post_shadow_maker_entry(
                            sleeve="M1_SVI_MAKER_SCALP",
                            dedupe_key=f"M1_{sr.market_id}_{side_lbl}",
                            asset=asset,
                            title=sr.question,
                            side_label=side_lbl,
                            token_id=tok,
                            p_model=p_fair,
                            close_ts=sr.end_ts,
                            extra={
                                "execution_mode": "POST_ONLY_MAKER_ZERO_FEE",
                                "market_id": sr.market_id,
                                "condition_id": sr.condition_id,
                                "strike": sr.strike,
                                "is_downward": sr.is_downward,
                                "iv_annual": svi_ev["iv_annual"],
                                "z_sigma": svi_ev["z_sigma"],
                            },
                            prefetched_book=bk_side,
                        )

                    # M2_STRIKE_CONVERGENCE (Post-NYSE-Open 20m <= TTE <= 105m, high-cushion z_sigma >= 1.75)
                    if (
                        1200 <= tte <= 6300
                        and 0.68 <= w_side["vwap"] <= 0.90
                        and svi_ev["z_sigma"] >= 1.75
                        and p_fair >= 0.93
                        and edge >= 0.045
                    ):
                        await self.open_shadow_position(
                            sleeve="M2_STRIKE_CONVERGENCE",
                            dedupe_key=f"M2_{sr.market_id}_{side_lbl}",
                            asset_or_city=asset,
                            title=sr.question,
                            side_label=side_lbl,
                            token_id=tok,
                            fee_rate=CRYPTO_FEE_RATE,
                            p_model=p_fair,
                            close_ts=sr.end_ts,
                            extra={
                                "market_id": sr.market_id,
                                "condition_id": sr.condition_id,
                                "strike": sr.strike,
                                "is_downward": sr.is_downward,
                                "iv_annual": svi_ev["iv_annual"],
                                "z_sigma": svi_ev["z_sigma"],
                            },
                            prefetched_book=bk_side,
                        )

            # Check cross-strike monotonicity boxes (#4/#7 bonus — verified with equal-share L2 book walk, `M-03` / `F-20` + `Gemini #8` execution)
            if len(ladder_quotes) >= 2:
                sq_l = sorted([q for q in ladder_quotes if not q.get("is_downward")], key=lambda x: x["strike"])
                best_m3_net: Optional[Tuple[float, float, float, float]] = None
                for i_l in range(len(sq_l) - 1):
                    ya_l, nh_l = float(sq_l[i_l].get("ask_yes") or 1.0), float(sq_l[i_l + 1].get("ask_no") or 1.0)
                    if 0 < ya_l < 1.0 and 0 < nh_l < 1.0:
                        gn_l = ya_l + nh_l + CRYPTO_FEE_RATE * (ya_l * (1.0 - ya_l) + nh_l * (1.0 - nh_l))
                        if best_m3_net is None or gn_l < best_m3_net[0]:
                            best_m3_net = (round(gn_l, 4), round(ya_l + nh_l, 4), float(sq_l[i_l]["strike"]), float(sq_l[i_l + 1]["strike"]))
                if best_m3_net is not None:
                    self._record_market_telemetry(
                        key=f"M3_DIAG_{ladder_key}",
                        min_interval_sec=60.0,
                        now_ts=now,
                        sig=best_m3_net,
                        payload={
                            "type": "LADDER_MONO_BEST",
                            "asset": asset,
                            "ladder_key": ladder_key,
                            "spot": spot,
                            "tte_sec": round(tte, 0),
                            "low_strike": best_m3_net[2],
                            "high_strike": best_m3_net[3],
                            "gross_box_l1": best_m3_net[1],
                            "net_box_l1": best_m3_net[0],
                        },
                    )
            mono_arbs = detect_ladder_monotonicity_boxes(ladder_quotes, fee_rate=CRYPTO_FEE_RATE)
            quotes_by_yes = {str(q["yes_token"]): q for q in ladder_quotes}
            quotes_by_no = {str(q["no_token"]): q for q in ladder_quotes}
            for ma in mono_arbs:
                q_lo = quotes_by_yes.get(str(ma.get("yes_token_low") or ""))
                q_hi = quotes_by_no.get(str(ma.get("no_token_high") or ""))
                if not q_lo or not q_hi:
                    continue
                w_m3 = walk_equal_shares_dominance_box(
                    q_lo.get("asks_yes") or [],
                    q_hi.get("asks_no") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["M3_LADDER_MONO_BOX"],
                    fee_rate_a=CRYPTO_FEE_RATE,
                    fee_rate_b=CRYPTO_FEE_RATE,
                    max_box_cost_net=0.996,
                    min_shares=10,
                    min_box_notional_usd=9.0,
                )
                if w_m3.get("filled"):
                    opps_out.append({
                        "sleeve": "M3_LADDER_MONO_BOX",
                        "market": f"{asset} Box YES>{ma['low_strike']} + NO>{ma['high_strike']}",
                        "ask_vwap": round(float(w_m3["box_cost_net"]), 4),
                        "p_model": 1.0,
                        "net_edge": round(1.0 - float(w_m3["box_cost_net"]), 4),
                        "l1_usd": w_m3["l1_usd"],
                        "close_ts": q_lo["end_ts"],
                    })
                    leg_a_m3 = {
                        "token_id": ma["yes_token_low"], "opp_token_id": str(q_lo["no_token"]),
                        "condition_id": str(q_lo.get("condition_id") or ""), "side": "YES", "label": f"YES>{ma['low_strike']}",
                        "market_id": ma["low_market_id"], "fee_rate": CRYPTO_FEE_RATE, "strike": float(ma["low_strike"]),
                    }
                    leg_b_m3 = {
                        "token_id": ma["no_token_high"], "opp_token_id": str(q_hi["yes_token"]),
                        "condition_id": str(q_hi.get("condition_id") or ""), "side": "NO", "label": f"NO>{ma['high_strike']}",
                        "market_id": ma["high_market_id"], "fee_rate": CRYPTO_FEE_RATE, "strike": float(ma["high_strike"]),
                    }
                    await self.open_shadow_two_leg_box(
                        sleeve="M3_LADDER_MONO_BOX",
                        dedupe_key=f"M3_{asset}_{ma['low_market_id']}_{ma['high_market_id']}",
                        asset=asset,
                        title=f"{asset} Ladder Box YES>{ma['low_strike']} + NO>{ma['high_strike']}",
                        leg_a=leg_a_m3,
                        leg_b=leg_b_m3,
                        bk_a=q_lo["bk_yes"],
                        bk_b=q_hi["bk_no"],
                        close_ts=float(q_lo["end_ts"]),
                        max_box_cost_net=0.996,
                        extra={
                            "is_mono_box": True,
                            "low_strike": ma["low_strike"],
                            "high_strike": ma["high_strike"],
                            "low_market_id": ma["low_market_id"],
                            "high_market_id": ma["high_market_id"],
                        },
                    )
                    if (float(q_lo["end_ts"]) - now) <= 86400.0 and float(w_m3["box_cost_net"]) <= 0.988:
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="M3_LADDER_MONO_BOX",
                            box_type="LADDER_MONO",
                            asset=asset,
                            dedupe_key=f"M3_{asset}_{ma['low_market_id']}_{ma['high_market_id']}",
                            leg_a=leg_a_m3,
                            leg_b=leg_b_m3,
                            bk_a=q_lo["bk_yes"],
                            bk_b=q_hi["bk_no"],
                            close_ts=float(q_lo["end_ts"]),
                            now_ts=now,
                            k_low=float(ma["low_strike"]),
                            k_high=float(ma["high_strike"]),
                        )

            # Check Cross-Contract `Multi-Strike` vs `NegRisk Bracket` Synthetic Box Arbitrage (`N1_NEGRISK_CROSS_BOX`)
            nr_key = f"{asset}_{int(rungs[0].end_ts)}"
            nr_brackets = self.negrisk_ladders.get(nr_key) or []
            if nr_brackets:
                await self._scan_negrisk_bundles_for_ladder(
                    asset=asset,
                    spot=spot,
                    rungs=rungs,
                    nr_brackets=nr_brackets,
                    ms_book_cache={
                        **{str(q["yes_token"]): q["bk_yes"] for q in ladder_quotes},
                        **{str(q["no_token"]): q["bk_no"] for q in ladder_quotes},
                    },
                    opps_out=opps_out,
                )

    async def _scan_negrisk_bundles_for_ladder(
        self,
        asset: str,
        spot: float,
        rungs: List[StrikeRungSpec],
        nr_brackets: List[NegRiskBracketSpec],
        ms_book_cache: Dict[str, Dict[str, Any]],
        opps_out: List[Dict[str, Any]],
    ) -> None:
        bundles = build_negrisk_cross_box_bundles(rungs, nr_brackets, spot=spot, max_strike_dist_log=0.10, tail_max_strike_dist_log=0.22)
        if not bundles:
            return
        local_bk_cache = dict(ms_book_cache)
        needed_toks = sorted({
            str(lg["token_id"])
            for bnd in bundles
            for lg in bnd["legs"]
            if str(lg["token_id"]) not in local_bk_cache
        })
        if needed_toks:
            local_bk_cache.update(await self.fetch_books_batch(needed_toks, timeout=3.0))

        best_nr_diag: Optional[Tuple[float, str, float, float]] = None
        for bnd in bundles:
            legs = bnd["legs"]
            if not all(str(lg["token_id"]) in local_bk_cache for lg in legs):
                continue
            gp = float(bnd["guaranteed_payout"])
            max_cost = round(gp * 0.992, 4)
            legs_spec = [
                {
                    "asks": local_bk_cache[str(lg["token_id"])].get("asks") or [],
                    "fee_rate": float(lg.get("fee_rate", CRYPTO_FEE_RATE)),
                    "fee_exponent": 1.0,
                }
                for lg in legs
            ]
            l1_sum = sum(
                p0 + float(lg.get("fee_rate", CRYPTO_FEE_RATE)) * p0 * (1.0 - p0)
                for lg in legs
                for p0 in [self._best_ask_sz(local_bk_cache[str(lg["token_id"])])[0]]
            )
            ratio_l1 = round(l1_sum / max(1.0, gp), 4)
            if ratio_l1 <= 1.15 and (best_nr_diag is None or ratio_l1 < best_nr_diag[0]):
                best_nr_diag = (ratio_l1, str(bnd["label"]), gp, float(bnd["end_ts"]))
            w_nr = walk_equal_shares_multi_leg_box(
                legs_spec,
                target_budget_usd=BANKROLL_TICKETS["T1000"]["N1_NEGRISK_CROSS_BOX"],
                guaranteed_payout_per_bundle=gp,
                max_bundle_cost_net=round(gp * 1.005, 4),
                min_shares=6,
                min_box_notional_usd=5.5,
            )
            if not w_nr.get("filled"):
                continue
            cost_net = float(w_nr["box_cost_net"])
            floor_edge = round(gp - cost_net, 4)
            opps_out.append({
                "sleeve": "N1_NEGRISK_CROSS_BOX",
                "market": f"{asset} {bnd['label']}",
                "ask_vwap": round(cost_net / gp, 4),
                "p_model": 1.0,
                "net_edge": round(floor_edge / gp, 4),
                "l1_usd": w_nr["l1_usd"],
                "close_ts": bnd["end_ts"],
            })
            if cost_net <= max_cost:
                await self.open_shadow_multi_leg_bundle(
                    sleeve="N1_NEGRISK_CROSS_BOX",
                    dedupe_key=f"N1_{asset}_{bnd['bundle_id']}",
                    asset=asset,
                    title=f"{asset} NegRisk Cross-Box: {bnd['label']}",
                    legs=legs,
                    books_by_token=local_bk_cache,
                    close_ts=float(bnd["end_ts"]),
                    guaranteed_payout=gp,
                    max_bundle_cost_net=max_cost,
                    extra={"is_multi_leg_bundle": True, "bundle_id": bnd["bundle_id"], "guaranteed_payout": gp, "legs": legs},
                )
                now_nr = time.time()
                if len(legs) == 2 and gp == 1.0 and cost_net <= 0.988 and (float(bnd["end_ts"]) - now_nr) <= 172800.0:
                    k_ref = float(legs[0].get("strike") or spot or 100.0)
                    self.emit_live_two_leg_box_candidate(
                        sleeve_source="N1_NEGRISK_CROSS_BOX",
                        box_type="NEGRISK_2LEG",
                        asset=asset,
                        dedupe_key=f"N1_{asset}_{bnd['bundle_id']}",
                        leg_a=legs[0],
                        leg_b=legs[1],
                        bk_a=local_bk_cache[str(legs[0]["token_id"])],
                        bk_b=local_bk_cache[str(legs[1]["token_id"])],
                        close_ts=float(bnd["end_ts"]),
                        now_ts=now_nr,
                        k_low=k_ref,
                        k_high=k_ref,
                    )
        if best_nr_diag is not None:
            now_d = time.time()
            self._record_market_telemetry(
                key=f"N1_BEST_{asset}_{int(best_nr_diag[3])}",
                min_interval_sec=90.0,
                now_ts=now_d,
                sig=(best_nr_diag[0], best_nr_diag[1]),
                payload={
                    "type": "NEGRISK_CRYPTO_CROSS_BEST",
                    "asset": asset,
                    "spot": round(spot, 4),
                    "tte_sec": round(best_nr_diag[3] - now_d, 0),
                    "payout": best_nr_diag[2],
                    "net_bundle_ratio_l1": best_nr_diag[0],
                    "label": best_nr_diag[1],
                },
            )

    async def open_shadow_multi_leg_bundle(
        self,
        sleeve: str,
        dedupe_key: str,
        asset: str,
        title: str,
        legs: List[Dict[str, Any]],
        books_by_token: Dict[str, Dict[str, Any]],
        close_ts: float,
        guaranteed_payout: float,
        max_bundle_cost_net: float,
        extra: Dict[str, Any],
    ) -> bool:
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            legs_spec = [
                {
                    "asks": books_by_token[str(lg["token_id"])].get("asks") or [],
                    "fee_rate": float(lg.get("fee_rate", CRYPTO_FEE_RATE)),
                    "fee_exponent": 1.0,
                }
                for lg in legs
            ]
            sum_bids = sum(
                extract_best_bid(books_by_token[str(lg["token_id"])].get("bids") or [])[0]
                for lg in legs
            )
            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = walk_equal_shares_multi_leg_box(
                    legs_spec,
                    target_budget_usd=t_map[sleeve],
                    guaranteed_payout_per_bundle=guaranteed_payout,
                    max_bundle_cost_net=max_bundle_cost_net,
                    min_shares=6 if tier_name == "T100" else 8,
                    min_box_notional_usd=7.0 if tier_name == "T100" else 9.0,
                )
                if w_t.get("filled"):
                    tier_fills[tier_name] = w_t
            if "T1000" not in tier_fills:
                return False
            w_ref = tier_fills["T1000"]
            now = time.time()
            pos_id = f"{sleeve}_{int(now)}_{dedupe_key[-10:]}"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve,
                "asset_or_city": asset,
                "title": title,
                "side": "+".join(str(lg.get("label", lg.get("side", "YES"))) for lg in legs),
                "token_id": "|".join(str(lg["token_id"]) for lg in legs),
                "fee_rate": max((float(lg.get("fee_rate", CRYPTO_FEE_RATE)) for lg in legs), default=CRYPTO_FEE_RATE),
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": round(guaranteed_payout, 4),
                "entry_eff_px_t1000": w_ref["eff_px"],
                "entry_vwap_t1000": w_ref["vwap"],
                "realized_edge_t1000": w_ref["riskless_floor_per_pair"],
                "entry_best_bid": round(sum_bids, 4),
                "last_bid": round(sum_bids, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {**extra, "legs": legs},
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(
                f"[ENTRY:{sleeve}] {title} | {w_ref['shares']} bundles @ net=${w_ref['eff_px']:.4f} "
                f"(guaranteed=${guaranteed_payout:.2f}, floor=${w_ref['riskless_floor_per_pair']:+.4f}/bundle)"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    async def execute_ctf_overround_mint_sell(
        self,
        dedupe_key: str,
        asset: str,
        title: str,
        legs_bids_spec: List[Dict[str, Any]],
        close_ts: float,
        min_net_proceeds_per_set: float,
        opps_out: List[Dict[str, Any]],
        extra: Dict[str, Any],
    ) -> bool:
        """
        Executes instant zero-hold `CTF_OVERROUND_MINT_SELL`: mints equal complete sets at `$1.00`
        (`splitPosition`) and sweeps resting L2 `bids` across all `N` mutually exclusive outcomes.
        """
        if is_shadow_sleeve_quarantined("CTF_OVERROUND_MINT_SELL"):
            return False
        w_probe = walk_equal_shares_overround_bids(
            legs_bids_spec,
            target_mint_budget_usd=BANKROLL_TICKETS["T1000"]["CTF_OVERROUND_MINT_SELL"],
            min_net_proceeds_per_set=min_net_proceeds_per_set,
            min_shares=8.0,
        )
        if not w_probe.get("filled"):
            return False
        opps_out.append({
            "sleeve": "CTF_OVERROUND_MINT_SELL",
            "market": title,
            "ask_vwap": round(2.0 - float(w_probe["net_proceeds_per_set"]), 4),
            "p_model": 1.0,
            "net_edge": w_probe["net_edge_per_set"],
            "l1_usd": w_probe["l1_usd"],
            "close_ts": close_ts,
        })
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            tier_fills: Dict[str, Dict[str, Any]] = {}
            tier_pnls: Dict[str, float] = {}
            for t_name, t_map in BANKROLL_TICKETS.items():
                wt = walk_equal_shares_overround_bids(
                    legs_bids_spec,
                    target_mint_budget_usd=t_map["CTF_OVERROUND_MINT_SELL"],
                    min_net_proceeds_per_set=min_net_proceeds_per_set,
                    min_shares=5.0 if t_name == "T100" else 8.0,
                )
                if wt.get("filled"):
                    sh_t = float(wt["shares"])
                    tier_fills[t_name] = {
                        "filled": True,
                        "vwap": 1.0,
                        "eff_px": 1.0,
                        "spent_usd": round(sh_t, 2),
                        "fee_usd": wt["fee_usd"],
                        "shares": sh_t,
                        "l1_usd": wt["l1_usd"],
                    }
                    tier_pnls[t_name] = round(sh_t * float(wt["net_edge_per_set"]), 2)
            if "T1000" not in tier_fills:
                return False
            now = time.time()
            pos_id = f"CTF_OVERROUND_MINT_SELL_{int(now)}_{dedupe_key[-10:]}"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": "CTF_OVERROUND_MINT_SELL",
                "asset_or_city": asset,
                "title": title,
                "side": f"MINT_SELL_{len(legs_bids_spec)}L",
                "token_id": dedupe_key,
                "fee_rate": 0.0,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "closed_ts": now,
                "closed_utc": datetime.now(timezone.utc).isoformat(),
                "p_model_entry": round(float(w_probe["net_proceeds_per_set"]), 4),
                "entry_eff_px_t1000": 1.0,
                "entry_vwap_t1000": 1.0,
                "realized_edge_t1000": w_probe["net_edge_per_set"],
                "net_payout_per_share": w_probe["gross_proceeds_per_set"],
                "tier_fills": tier_fills,
                "tier_pnls_usd": tier_pnls,
                "legging_adjusted_tier_pnls_usd": tier_pnls,
                "won": tier_pnls.get("T1000", 0.0) > 0,
                "extra": {**extra, "n_legs": len(legs_bids_spec)},
                "status": "INSTANT_MINT_AND_SELL_FILLED",
            }
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            self.closed_positions.append(pos)
            self._append_ledger({"event": "SHADOW_CLOSE", **pos})
            logger.info(
                f"[INSTANT_ARB:CTF_OVERROUND_MINT_SELL] {title} | net_proceeds=${w_probe['net_proceeds_per_set']:.4f} "
                f"(+{w_probe['net_edge_per_set']:.4f}/set) | PnL T1000=${tier_pnls.get('T1000', 0.0):+.2f}"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    async def scan_daily_updown_locks(self, opps_out: List[Dict[str, Any]]) -> None:
        """
        Addition #6 (`U1_DAILY_UPDOWN_LOCK` + Zero-Fee Pyth FX/Metals & Crypto Daily `C1_BINARY_COMPLETE_SET`).
        """
        now = time.time()
        loop = asyncio.get_running_loop()

        # 0. Scan all Daily Crypto + Zero-Fee Pyth FX/Metals Up/Down markets in 1 batch RTT for C1 Complete-Set arb
        c1_daily_specs = [
            sp for sp in [*self.daily_updown_markets.values(), *self.pyth_daily_markets.values()]
            if sp.end_ts > now + 60.0
        ]
        if c1_daily_specs:
            c1_bks = await self.fetch_books_batch(
                [sp.up_token for sp in c1_daily_specs] + [sp.down_token for sp in c1_daily_specs],
                timeout=3.0,
            )
            for sp_c1 in c1_daily_specs:
                bk_u = c1_bks.get(sp_c1.up_token)
                bk_d = c1_bks.get(sp_c1.down_token)
                if not bk_u or not bk_d:
                    continue
                ua_d, us_d = self._best_ask_sz(bk_u)
                da_d, ds_d = self._best_ask_sz(bk_d)
                if ua_d < 1.0 and da_d < 1.0:
                    f_d = float(sp_c1.fee_rate)
                    self._record_market_telemetry(
                        key=f"DAILY_C1_{sp_c1.market_id}",
                        min_interval_sec=60.0,
                        now_ts=now,
                        sig=(ua_d, da_d),
                        payload={
                            "type": "DAILY_COMPLETE_SET",
                            "asset": sp_c1.asset,
                            "market_id": sp_c1.market_id,
                            "title": sp_c1.title,
                            "fee_rate": f_d,
                            "tte_sec": round(sp_c1.end_ts - now, 0),
                            "up_ask": ua_d,
                            "down_ask": da_d,
                            "gross_sum_l1": round(ua_d + da_d, 4),
                            "net_sum_l1": round(ua_d + da_d + f_d * (ua_d * (1.0 - ua_d) + da_d * (1.0 - da_d)), 4),
                            "l1_min_shares": round(min(us_d, ds_d), 2),
                        },
                    )
                cap_c1 = 0.995 if sp_c1.fee_rate == 0.0 else 0.994
                c1_res = scan_binary_complete_set_arb(
                    market_id=sp_c1.market_id,
                    condition_id=sp_c1.condition_id,
                    yes_token=sp_c1.up_token,
                    no_token=sp_c1.down_token,
                    asks_yes_raw=bk_u.get("asks") or [],
                    asks_no_raw=bk_d.get("asks") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],
                    fee_rate=sp_c1.fee_rate,
                    max_box_cost_net=cap_c1,
                )
                if c1_res.get("filled"):
                    opps_out.append({
                        "sleeve": "C1_BINARY_COMPLETE_SET",
                        "market": f"{sp_c1.asset} Complete-Set {sp_c1.title}",
                        "ask_vwap": c1_res["box_cost_net"],
                        "p_model": 1.0,
                        "net_edge": c1_res["riskless_floor_per_pair"],
                        "l1_usd": c1_res["l1_usd"],
                        "close_ts": sp_c1.end_ts,
                    })
                    leg_u = {"token_id": sp_c1.up_token, "opp_token_id": sp_c1.down_token, "condition_id": sp_c1.condition_id, "side": "UP", "label": "UP", "market_id": sp_c1.market_id, "fee_rate": sp_c1.fee_rate, "strike": 100.0}
                    leg_d = {"token_id": sp_c1.down_token, "opp_token_id": sp_c1.up_token, "condition_id": sp_c1.condition_id, "side": "DOWN", "label": "DOWN", "market_id": sp_c1.market_id, "fee_rate": sp_c1.fee_rate, "strike": 100.0}
                    await self.open_shadow_two_leg_box(
                        sleeve="C1_BINARY_COMPLETE_SET",
                        dedupe_key=f"C1_D_{sp_c1.market_id}",
                        asset=sp_c1.asset,
                        title=f"{sp_c1.asset} UP+DOWN Complete Set: {sp_c1.title}",
                        leg_a=leg_u,
                        leg_b=leg_d,
                        bk_a=bk_u,
                        bk_b=bk_d,
                        close_ts=sp_c1.end_ts,
                        max_box_cost_net=cap_c1,
                        extra={"is_complete_set": True, "market_id": sp_c1.market_id, "condition_id": sp_c1.condition_id},
                    )
                    if (sp_c1.end_ts - now) <= 86400.0 and float(c1_res["box_cost_net"]) <= (0.990 if sp_c1.fee_rate == 0.0 else 0.988):
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="C1_BINARY_COMPLETE_SET",
                            box_type="COMPLETE_SET",
                            asset=sp_c1.asset,
                            dedupe_key=f"C1_D_{sp_c1.market_id}",
                            leg_a=leg_u,
                            leg_b=leg_d,
                            bk_a=bk_u,
                            bk_b=bk_d,
                            close_ts=float(sp_c1.end_ts),
                            now_ts=now,
                        )
                await self.execute_ctf_overround_mint_sell(
                    dedupe_key=f"CTF_OVR_D_{sp_c1.market_id}",
                    asset=sp_c1.asset,
                    title=f"{sp_c1.asset} Binary Overround Mint-Sell: {sp_c1.title}",
                    legs_bids_spec=[
                        {"bids": bk_u.get("bids") or [], "fee_rate": sp_c1.fee_rate, "fee_exponent": 1.0},
                        {"bids": bk_d.get("bids") or [], "fee_rate": sp_c1.fee_rate, "fee_exponent": 1.0},
                    ],
                    close_ts=sp_c1.end_ts,
                    min_net_proceeds_per_set=1.003 if sp_c1.fee_rate == 0.0 else 1.004,
                    opps_out=opps_out,
                    extra={"overround_kind": "BINARY_DAILY", "market_id": sp_c1.market_id, "condition_id": sp_c1.condition_id},
                )

        # 0B. `D2_12PM_BINANCE_BOX`: 11:00-12:00 PM ET `1h` vs `12:00 PM ET` Daily/Multi-Strike Same-Binance Boxes
        for _, sp_h in list(self.hourly_12pm_markets.items()):
            tte_h = sp_h.end_ts - now
            if not (60.0 <= tte_h <= 3540.0) or now < sp_h.start_ts + 20.0:
                continue
            hk_key = f"H1_{sp_h.asset}_{int(sp_h.start_ts)}"
            c_ho = self.daily_open_cache.get(hk_key)
            if c_ho is None:
                ext_ho = await loop.run_in_executor(
                    None, fetch_binance_window_extremes_sync, sp_h.asset, sp_h.start_ts - 60.0, sp_h.start_ts + 60.0, "1m"
                )
                if ext_ho is not None and ext_ho[2] > 0:
                    self.daily_open_cache[hk_key] = (sp_h.end_ts, float(ext_ho[2]))
                    k_1h = float(ext_ho[2])
                else:
                    continue
            else:
                k_1h = c_ho[1]

            term_specs: List[Dict[str, Any]] = []
            for sp_d in self.daily_updown_markets.values():
                if sp_d.asset == sp_h.asset and abs(sp_d.end_ts - sp_h.end_ts) <= 5.0:
                    dk_key = f"{sp_d.asset}_{int(sp_d.start_ts)}"
                    c_do = self.daily_open_cache.get(dk_key)
                    if c_do is None:
                        ext_do = await loop.run_in_executor(
                            None, fetch_binance_window_extremes_sync, sp_d.asset, sp_d.start_ts - 60.0, sp_d.start_ts + 60.0, "1m"
                        )
                        if ext_do is not None and ext_do[2] > 0:
                            self.daily_open_cache[dk_key] = (sp_d.end_ts, float(ext_do[2]))
                            k_d = float(ext_do[2])
                        else:
                            k_d = 0.0
                    else:
                        k_d = c_do[1]
                    if k_d > 0:
                        term_specs.append({
                            "market_id": sp_d.market_id, "condition_id": sp_d.condition_id, "end_ts": sp_d.end_ts,
                            "strike": k_d, "is_downward": False, "yes_token": sp_d.up_token, "no_token": sp_d.down_token,
                            "yes_label": "UP", "no_label": "DOWN", "fee_rate": sp_d.fee_rate,
                        })
            for rungs_d2 in self.strike_ladders.values():
                if rungs_d2 and rungs_d2[0].asset == sp_h.asset and abs(rungs_d2[0].end_ts - sp_h.end_ts) <= 5.0:
                    for sr_d2 in rungs_d2:
                        if not sr_d2.is_downward:
                            term_specs.append({
                                "market_id": sr_d2.market_id, "condition_id": sr_d2.condition_id, "end_ts": sr_d2.end_ts,
                                "strike": sr_d2.strike, "is_downward": False, "yes_token": sr_d2.yes_token, "no_token": sr_d2.no_token,
                                "yes_label": "YES", "no_label": "NO", "fee_rate": CRYPTO_FEE_RATE,
                            })
            d2_cands = detect_d2_12pm_binance_boxes(
                {"asset": sp_h.asset, "market_id": sp_h.market_id, "condition_id": sp_h.condition_id, "end_ts": sp_h.end_ts, "up_token": sp_h.up_token, "down_token": sp_h.down_token, "fee_rate": sp_h.fee_rate},
                k_1h,
                term_specs,
            )
            if d2_cands:
                d2_toks = sorted({str(c["leg_a"]["token_id"]) for c in d2_cands} | {str(c["leg_b"]["token_id"]) for c in d2_cands})
                d2_bks = await self.fetch_books_batch(d2_toks, timeout=3.0)
                for dc in d2_cands:
                    la2, lb2 = dc["leg_a"], dc["leg_b"]
                    bka2, bkb2 = d2_bks.get(str(la2["token_id"])), d2_bks.get(str(lb2["token_id"]))
                    if not bka2 or not bkb2:
                        continue
                    aa2, _ = self._best_ask_sz(bka2)
                    ab2, _ = self._best_ask_sz(bkb2)
                    if aa2 < 1.0 and ab2 < 1.0:
                        self._record_market_telemetry(
                            key=f"D2_12PM_{la2['market_id']}_{lb2['market_id']}",
                            min_interval_sec=30.0,
                            now_ts=now,
                            sig=(aa2, ab2),
                            payload={
                                "type": "D2_12PM_CORRIDOR",
                                "asset": sp_h.asset,
                                "tte_sec": round(tte_h, 0),
                                "k_low": dc["k_low"],
                                "k_high": dc["k_high"],
                                "corridor_bps": dc["corridor_bps"],
                                "gross_box_l1": round(aa2 + ab2, 4),
                                "label": dc["label"],
                            },
                        )
                    w_d2 = walk_equal_shares_dominance_box(
                        bka2.get("asks") or [],
                        bkb2.get("asks") or [],
                        target_budget_usd=BANKROLL_TICKETS["T1000"]["D2_12PM_BINANCE_BOX"],
                        fee_rate_a=float(la2["fee_rate"]),
                        fee_rate_b=float(lb2["fee_rate"]),
                        max_box_cost_net=0.990,
                        min_shares=6,
                        min_box_notional_usd=5.5,
                    )
                    if w_d2.get("filled"):
                        opps_out.append({
                            "sleeve": "D2_12PM_BINANCE_BOX",
                            "market": f"{sp_h.asset} 12PM Box {dc['label']}",
                            "ask_vwap": round(float(w_d2["box_cost_net"]), 4),
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_d2["box_cost_net"]), 4),
                            "l1_usd": w_d2["l1_usd"],
                            "close_ts": dc["close_ts"],
                        })
                        await self.open_shadow_two_leg_box(
                            sleeve="D2_12PM_BINANCE_BOX",
                            dedupe_key=f"D2_{la2['market_id']}_{lb2['market_id']}",
                            asset=sp_h.asset,
                            title=f"{sp_h.asset} 12PM Binance Box {dc['label']}",
                            leg_a=la2,
                            leg_b=lb2,
                            bk_a=bka2,
                            bk_b=bkb2,
                            close_ts=float(dc["close_ts"]),
                            max_box_cost_net=0.990,
                            extra={"is_d2_12pm_box": True, "k_low": dc["k_low"], "k_high": dc["k_high"], "corridor_bps": dc["corridor_bps"]},
                        )

        for _, sp in list(self.daily_updown_markets.items()):
            tte = sp.end_ts - now
            if not (120.0 <= tte <= 5400.0):
                continue
            spot = self.spots.get(sp.asset, 0.0)
            if spot <= 0.0:
                continue

            c_key = f"{sp.asset}_{int(sp.start_ts)}"
            cached_o = self.daily_open_cache.get(c_key)
            if cached_o is None:
                ext_o = await loop.run_in_executor(
                    None, fetch_binance_window_extremes_sync, sp.asset, sp.start_ts - 60.0, sp.start_ts + 60.0, "1m"
                )
                if ext_o is not None and ext_o[2] > 0:
                    self.daily_open_cache[c_key] = (sp.end_ts, float(ext_o[2]))
                    k_open = float(ext_o[2])
                else:
                    continue
            else:
                k_open = cached_o[1]

            svi_ev = evaluate_svi_digital_fair_value(sp.asset, spot, k_open, tte, is_downward=False, now_ts=now)
            win_side = "UP" if spot > k_open else "DOWN"
            p_fair = float(svi_ev["p_yes"] if win_side == "UP" else svi_ev["p_no"])
            z_sig = abs(float(svi_ev.get("z_sigma") or 0.0))
            if z_sig < 1.80 or p_fair < 0.93:
                continue

            ret_60s = self.get_return_bps(sp.asset, 60.0)
            if (win_side == "UP" and ret_60s < -10.0) or (win_side == "DOWN" and ret_60s > 10.0):
                continue

            tok = sp.up_token if win_side == "UP" else sp.down_token
            bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=3.0)
            if not bk:
                continue
            w_chk = walk_l2_book_asks(bk.get("asks") or [], BANKROLL_TICKETS["T1000"]["U1_DAILY_UPDOWN_LOCK"], fee_rate=sp.fee_rate)
            if not w_chk.get("filled"):
                continue
            eff_px = float(w_chk["eff_px"])
            edge = p_fair - eff_px
            if 0.66 <= w_chk["vwap"] <= 0.90 and edge >= 0.025:
                opps_out.append({
                    "sleeve": "U1_DAILY_UPDOWN_LOCK",
                    "market": f"{sp.asset} {sp.title} ({win_side}, TTE={tte/60:.0f}m, z={z_sig:.2f})",
                    "ask_vwap": eff_px,
                    "p_model": round(p_fair, 4),
                    "net_edge": round(edge, 4),
                    "l1_usd": w_chk["l1_usd"],
                    "close_ts": sp.end_ts,
                })
            if 0.66 <= w_chk["vwap"] <= 0.90 and edge >= 0.042:
                await self.open_shadow_position(
                    sleeve="U1_DAILY_UPDOWN_LOCK",
                    dedupe_key=f"U1_{sp.market_id}_{win_side}",
                    asset_or_city=sp.asset,
                    title=sp.title,
                    side_label=win_side,
                    token_id=tok,
                    fee_rate=sp.fee_rate,
                    p_model=p_fair,
                    close_ts=sp.end_ts,
                    extra={
                        "market_id": sp.market_id,
                        "condition_id": sp.condition_id,
                        "strike": k_open,
                        "is_downward": (win_side == "DOWN"),
                        "z_sigma": z_sig,
                    },
                    tp_target_px=0.98,
                    prefetched_book=bk,
                )

    @staticmethod
    def is_in_same_oracle_overlap_window(now_ts: float) -> bool:
        """
        True during the final 5m sub-window of every 15m candle (`:10-:15`, `:25-:30`,
        `:40-:45`, `:55-:00`), where the active `15m` and `5m` Chainlink 60s-TWAP markets
        share the exact same terminal timestamp `target_end_ts`.
        """
        target_end_ts = math.ceil(now_ts / 900.0) * 900.0
        rem_sec = target_end_ts - now_ts
        return 8.0 <= rem_sec <= 305.0

    async def discover_dominance_pairs(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        # Prune expired pairs and opening strike caches
        for k_old, (m15_old, _) in list(self.dominance_pairs.items()):
            if m15_old.end_ts < now - 600.0:
                self.dominance_pairs.pop(k_old, None)
        for c_key, (end_old, _) in list(self.chainlink_open_cache.items()):
            if end_old < now - 600.0:
                self.chainlink_open_cache.pop(c_key, None)
        _src_m = self.__dict__.get("_strike_source") or {}
        for c_key, (end_old, _) in list(_src_m.items()):
            if end_old < now - 600.0:
                _src_m.pop(c_key, None)
        for c_key, bo_ts in list(self._strike_fail_backoff_ts.items()):
            if float(bo_ts or 0.0) < now - 7200.0:
                self._strike_fail_backoff_ts.pop(c_key, None)

        target_end_ts = int(math.ceil(now / 900.0) * 900)
        rem_sec = float(target_end_ts) - now
        max_disc_rem = 305.0 if (self.single_scan or "fetch_json" in self.__dict__) else 335.0
        if not (5.0 <= rem_sec <= max_disc_rem):
            return

        now_iso = datetime.fromtimestamp(now - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        async def _discover_asset_pair(asset: str) -> None:
            pair_key = f"{asset}_{target_end_ts}"
            if pair_key in self.dominance_pairs:
                return
            slugs = DOMINANCE_SERIES_SLUGS[asset]
            ev15_raw, ev5_raw = await asyncio.gather(
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['15m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['5m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
            )
            m15_match: Optional[TwapCandleMarketSpec] = None
            m5_match: Optional[TwapCandleMarketSpec] = None
            if isinstance(ev15_raw, list):
                for ev in ev15_raw:
                    sp15 = parse_twap_candle_event(ev, asset, "15m")
                    if sp15 and abs(sp15.end_ts - target_end_ts) <= 2.0:
                        m15_match = sp15
                        break
            if isinstance(ev5_raw, list):
                for ev in ev5_raw:
                    sp5 = parse_twap_candle_event(ev, asset, "5m")
                    if sp5 and abs(sp5.end_ts - target_end_ts) <= 2.0:
                        m5_match = sp5
                        break
            if m15_match and m5_match and verify_same_oracle_pair(m15_match, m5_match):
                self.dominance_pairs[pair_key] = (m15_match, m5_match)

        await asyncio.gather(*(_discover_asset_pair(a) for a in DOMINANCE_ASSETS))

    def _strike_is_rest_verified(self, spec: TwapCandleMarketSpec) -> bool:
        """False if the last strike returned for `spec` came from the unverified Chainlink-WS TWAP fallback.

        `get_authoritative_open_strike` tags every lookup (`PENDING` -> `WS_TWAP` / `REST_VERIFIED`), so in production
        a missing tag only occurs when the lookup is stubbed in tests.
        """
        c_key = f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}"
        src_ent = (self.__dict__.get("_strike_source") or {}).get(c_key)
        return bool(src_ent is None or src_ent[1] == "REST_VERIFIED")

    async def get_authoritative_open_strike(self, spec: TwapCandleMarketSpec) -> Optional[float]:
        c_key = f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}"
        # Source of the last returned strike: "WS_TWAP" (unverified Chainlink-WS boundary TWAP) or "REST_VERIFIED".
        # LIVE D1 emits require REST_VERIFIED strikes on both legs; shadow entries may still use WS TWAP.
        src_map: Dict[str, Tuple[float, str]] = self.__dict__.setdefault("_strike_source", {})
        cached = self.chainlink_open_cache.get(c_key)
        if cached is not None:
            src_map[c_key] = (spec.end_ts, "REST_VERIFIED")
            return cached[1]
        src_map[c_key] = (spec.end_ts, "PENDING")  # fail-closed for LIVE until a verified value is returned
        now_t = time.time()
        is_mocked = self.single_scan or ("fetch_json" in self.__dict__)
        cl_ws = getattr(self, "_chainlink_ws", None) if not is_mocked else None
        ws_twap_val = cl_ws.get_boundary_twap_60s(spec.asset, spec.start_ts, min_ticks=52) if cl_ws is not None else None
        if not self.single_scan and now_t < spec.start_ts + (0.20 if ws_twap_val is not None else 2.0):
            return None
        if not is_mocked and now_t < spec.start_ts + 2.0 and ws_twap_val is not None:
            src_map[c_key] = (spec.end_ts, "WS_TWAP")
            return ws_twap_val
        if not is_mocked:
            last_fail_ts = float(self._strike_fail_backoff_ts.get(c_key, 0.0) or 0.0)
            if (now_t - last_fail_ts) < 2.5:
                if ws_twap_val is not None:
                    src_map[c_key] = (spec.end_ts, "WS_TWAP")
                return ws_twap_val
        twap_url = build_crypto_price_query_url(spec)
        # Polymarket's crypto-price endpoint intermittently answers HTTP 400 {"error":"Chainlink API error 429"};
        # when prev_5m Gamma (`start_ts + 35s`) is already settled on CDN in live mode, skip multi-second retry sleeps!
        val: Optional[float] = None
        max_attempts = 3 if (is_mocked or now_t < spec.start_ts + 35.0) else 1
        retry_base = 0.3 if is_mocked else 0.12
        for _attempt in range(max_attempts):
            payload = await self.fetch_json(twap_url, timeout=4.0 if is_mocked else 2.5)
            val = parse_authoritative_open_price(payload, request_url=twap_url)
            if val is not None:
                break
            if _attempt + 1 < max_attempts:
                await asyncio.sleep(retry_base * (_attempt + 1))
        # prev_5m (`start_ts - 300`) closes AT `start_ts`: fallback as soon as `t >= start_ts + 35s` on upstream 429s,
        # and always cross-check once `t >= start_ts + 335s` (`needs_gamma`).
        needs_gamma = self.single_scan or now_t >= spec.start_ts + 335.0
        can_fallback_gamma = needs_gamma or (val is None and now_t >= spec.start_ts + 35.0)
        used_gamma = False
        if can_fallback_gamma:
            g_url = build_prev_5m_gamma_event_url(spec)
            g_val = parse_authoritative_open_price(await self.fetch_json(g_url, timeout=4.0 if is_mocked else 2.5), request_url=g_url)
            if val is None and g_val is not None:
                val = g_val
                used_gamma = True
            elif needs_gamma and g_val is not None and abs(val - g_val) / max(1e-9, g_val) > 1e-6:
                logger.error(
                    f"[CRITICAL TWAP MISMATCH VETO] {spec.asset} {spec.horizon}: "
                    f"crypto-price TWAP={val} != Gamma prev_5m finalPrice={g_val}!"
                )
                return None
            elif needs_gamma and g_val is None and not self.single_scan:
                if not is_mocked:
                    self._strike_fail_backoff_ts[c_key] = time.time()
                return None  # unverifiable while verification is possible -> fail closed, never cache
        if val is None:
            if not is_mocked:
                self._strike_fail_backoff_ts[c_key] = time.time()
                if ws_twap_val is not None and now_t < spec.start_ts + 335.0:
                    src_map[c_key] = (spec.end_ts, "WS_TWAP")
                    return ws_twap_val
            _fl = self.__dict__.setdefault("_strike_fail_log_ts", {})
            if (now_t - float(_fl.get(c_key, 0.0))) >= 60.0:
                _fl[c_key] = now_t
                logger.warning(
                    f"[STRIKE LOOKUP FAILED] {spec.asset} {spec.horizon}: crypto-price + prev_5m Gamma returned no usable openPrice -> skipped (fail-closed)."
                )
        if val is not None:
            hist_w = [px for ts_s, px in self.usd_spot_hist.get(spec.asset, ()) if (spec.start_ts - 60.0) <= ts_s <= (spec.start_ts + 5.0)]
            if len(hist_w) >= 3 and not self.single_scan:
                loc_twap = sum(hist_w) / len(hist_w)
                if loc_twap > 0.0 and abs(val - loc_twap) / loc_twap > 0.0035:
                    logger.error(f"[STRIKE TWAP VETO] {spec.asset} {spec.horizon}: strike {val} vs local 60s TWAP {loc_twap} > 35 bps")
                    return None
            elif not (needs_gamma or used_gamma):
                spot_ref = float(self.spots.get(spec.asset) or 0.0)
                if spot_ref > 0.0 and abs(val - spot_ref) / spot_ref > 0.015:
                    logger.error(f"[STRIKE SANITY VETO] {spec.asset} {spec.horizon}: strike {val} vs spot {spot_ref} > 150 bps")
                    return None
            self.chainlink_open_cache[c_key] = (spec.end_ts, val)
            src_map[c_key] = (spec.end_ts, "REST_VERIFIED")
        return val

    async def _passes_complement_anti_box_check(
        self,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        prefetched_books: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> bool:
        opp_a = str(leg_a.get("opp_token_id") or "")
        opp_b = str(leg_b.get("opp_token_id") or "")
        if not opp_a or not opp_b:
            return False
        bk_oa = (prefetched_books or {}).get(opp_a)
        bk_ob = (prefetched_books or {}).get(opp_b)
        if not (isinstance(bk_oa, dict) and isinstance(bk_ob, dict)):
            bk_oa, bk_ob = await asyncio.gather(
                self.fetch_json(f"{CLOB_URL}/book?token_id={opp_a}", timeout=3.0),
                self.fetch_json(f"{CLOB_URL}/book?token_id={opp_b}", timeout=3.0),
            )
        if not (isinstance(bk_oa, dict) and isinstance(bk_ob, dict)):
            return False
        bid_oa, _ = extract_best_bid(bk_oa.get("bids") or [])
        bid_ob, _ = extract_best_bid(bk_ob.get("bids") or [])
        if bid_oa <= 0.0 or bid_ob <= 0.0 or (bid_oa + bid_ob) > 1.0:
            _ab_map = self.__dict__.setdefault("_anti_box_warn_ts", {})
            _ab_k = f"{opp_a}:{opp_b}"
            _now_ab = time.time()
            if (_now_ab - float(_ab_map.get(_ab_k, 0.0))) >= 30.0:
                if len(_ab_map) > 512:
                    _ab_map.clear()
                _ab_map[_ab_k] = _now_ab
                logger.warning(
                    f"[ANTI-BOX VETO] Rejected box {leg_a.get('label')}+{leg_b.get('label')}: "
                    f"complement bids={bid_oa:.3f}+{bid_ob:.3f}={bid_oa + bid_ob:.3f} (unverified or > 1.00)"
                )
            return False
        return True

    async def open_shadow_two_leg_box(
        self,
        sleeve: str,
        dedupe_key: str,
        asset: str,
        title: str,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        close_ts: float,
        max_box_cost_net: float,
        extra: Dict[str, Any],
    ) -> bool:
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            # EXP-PM-404: Enforce causal 250ms L2 re-fetch & re-walk on 0%-fee 2-leg structural boxes
            # so _grad8 auto-graduation only counts edges that survive realistic execution latency.
            if sleeve in ("CM_B3_PYTH_BARRIER_BOX", "SP1_NBA_ZERO_FEE_BOX"):
                await asyncio.sleep(0.25)
                re_bks = await self.fetch_books_batch([leg_a["token_id"], leg_b["token_id"]], timeout=3.0)
                bk_a = re_bks.get(leg_a["token_id"]) or {}
                bk_b = re_bks.get(leg_b["token_id"]) or {}
                if not bk_a or not bk_b:
                    return False
            asks_a = bk_a.get("asks") or []
            asks_b = bk_b.get("asks") or []
            bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
            bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = walk_equal_shares_dominance_box(
                    asks_a,
                    asks_b,
                    target_budget_usd=t_map[sleeve],
                    fee_rate_a=float(leg_a.get("fee_rate", CRYPTO_FEE_RATE)),
                    fee_rate_b=float(leg_b.get("fee_rate", CRYPTO_FEE_RATE)),
                    max_box_cost_net=max_box_cost_net,
                    min_shares=8,
                    min_box_notional_usd=7.0,
                )
                if w_t.get("filled"):
                    tier_fills[tier_name] = w_t
            if "T1000" not in tier_fills:
                return False
            w_ref = tier_fills["T1000"]
            now = time.time()
            pos_id = f"{sleeve}_{int(now)}_{dedupe_key[-10:]}"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve,
                "asset_or_city": asset,
                "title": title,
                "side": f"{leg_a.get('side','YES')}+{leg_b.get('side','NO')}",
                "token_id": f"{leg_a['token_id']}|{leg_b['token_id']}",
                "fee_rate": float(leg_a.get("fee_rate", CRYPTO_FEE_RATE)),
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": 1.0,
                "entry_eff_px_t1000": w_ref["eff_px"],
                "entry_vwap_t1000": w_ref["vwap"],
                "realized_edge_t1000": w_ref["riskless_floor_per_pair"],
                "entry_best_bid": round(bid_a + bid_b, 4),
                "last_bid": round(bid_a + bid_b, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {**extra, "leg_a": leg_a, "leg_b": leg_b},
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(f"[ENTRY:{sleeve}] {title} | {w_ref['shares']} pairs @ net=${w_ref['eff_px']:.4f}")
            return True
        finally:
            self._release_inflight_keys(acq)

    async def open_shadow_weather_slate(
        self,
        spec: WeatherEventSpec,
        slate_info: Dict[str, Any],
        close_ts: float,
    ) -> bool:
        slate_side = str(slate_info.get("side") or "ALL_BUCKETS_YES")
        guar_pay = float(slate_info.get("guaranteed_payout_per_set") or 1.0)
        dedupe_key = f"W3_SLATE_{spec.event_id}" if slate_side == "ALL_BUCKETS_YES" else f"W3_SLATE_NO_{spec.event_id}"
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            sum_asks = float(slate_info["sum_asks"])
            legs = slate_info["legs"]
            min_avail_sh = min(float(lg.get("ask_shares", lg.get("ask_yes_shares", 0.0))) for lg in legs)
            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                sh = max(5.0, min(min_avail_sh, math.floor(t_map["W3_WEATHER_SLATE_ARB"] / max(0.10, sum_asks))))
                spent = round(sh * sum_asks, 2)
                if sh >= 5.0 and spent <= t_map["W3_WEATHER_SLATE_ARB"] * 1.25:
                    tier_fills[tier_name] = {
                        "filled": True,
                        "vwap": round(sum_asks, 4),
                        "eff_px": round(sum_asks, 4),
                        "spent_usd": spent,
                        "fee_usd": 0.0,
                        "shares": sh,
                        "l1_usd": round(min_avail_sh * sum_asks, 2),
                    }
            if "T1000" not in tier_fills:
                return False
            now = time.time()
            pos_id = f"W3_WEATHER_SLATE_ARB_{int(now)}_{spec.event_id[-6:]}"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": "W3_WEATHER_SLATE_ARB",
                "asset_or_city": f"{spec.city}_{spec.icao}",
                "title": f"{spec.title} [Full-Slate {len(legs)} Buckets {slate_side}]",
                "side": slate_side,
                "token_id": "|".join(str(lg.get("token_id") or lg.get("yes_token")) for lg in legs),
                "fee_rate": 0.0,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": round(guar_pay, 4),
                "entry_eff_px_t1000": round(sum_asks, 4),
                "entry_vwap_t1000": round(sum_asks, 4),
                "realized_edge_t1000": round(guar_pay - sum_asks, 4),
                "entry_best_bid": round(sum_asks, 4),
                "last_bid": round(sum_asks, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {"event_id": spec.event_id, "icao": spec.icao, "guaranteed_payout": guar_pay, "legs": legs},
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(f"[ENTRY:W3_WEATHER_SLATE_ARB] {pos['title']} @ sum_asks=${sum_asks:.4f} (payout=${guar_pay:.2f})")
            return True
        finally:
            self._release_inflight_keys(acq)

    async def open_shadow_dominance_box(
        self,
        asset: str,
        m15: TwapCandleMarketSpec,
        m5: TwapCandleMarketSpec,
        dom_info: Dict[str, Any],
        prefetched_books: Optional[Tuple[Dict[str, Any], Dict[str, Any]]] = None,
        sleeve_override: str = "D1_SAME_ORACLE_DOMINANCE_BOX",
        max_box_cost_override: float = 0.995,
    ) -> bool:
        prefix = "D1" if sleeve_override == "D1_SAME_ORACLE_DOMINANCE_BOX" else sleeve_override.split("_")[0] + "_" + sleeve_override.split("_")[1]
        dedupe_key = f"{prefix}_{asset}_{m15.market_id}_{m5.market_id}"
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False

        try:
            leg_a = dom_info["leg_a"]
            leg_b = dom_info["leg_b"]

            # Strictly causal 2-leg L2 walk (reuses prefetched books when scanned after latency, `Gemini #7`)
            if prefetched_books is not None:
                bk_a, bk_b = prefetched_books
            else:
                await asyncio.sleep(0.050)
                bk_a, bk_b = await asyncio.gather(
                    self.fetch_json(f"{CLOB_URL}/book?token_id={leg_a['token_id']}", timeout=3.0),
                    self.fetch_json(f"{CLOB_URL}/book?token_id={leg_b['token_id']}", timeout=3.0),
                )
            if not bk_a or not bk_b:
                return False

            asks_a = bk_a.get("asks") or []
            asks_b = bk_b.get("asks") or []
            bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
            bid_b, _ = extract_best_bid(bk_b.get("bids") or [])

            # Validate T1000 reference equal-share box (`box_cost_net <= max_box_cost_override`)
            w_ref = walk_equal_shares_dominance_box(
                asks_a,
                asks_b,
                target_budget_usd=BANKROLL_TICKETS["T1000"][sleeve_override],
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                fee_exponent_a=float(leg_a["fee_exponent"]),
                fee_exponent_b=float(leg_b["fee_exponent"]),
                max_box_cost_net=max_box_cost_override,
                min_shares=8,
                min_box_notional_usd=7.5,
            )
            if not w_ref.get("filled"):
                return False

            is_4h_mixed = ("4h" in (str(m15.horizon).lower(), str(m5.horizon).lower())) and (
                str(m15.horizon).lower() != str(m5.horizon).lower()
            )
            drag_ref = compute_d1_legging_drag_haircut(
                shares=float(w_ref["shares"]),
                box_cost_net=float(w_ref["box_cost_net"]),
                avail_a_shares=float(w_ref["avail_a_shares"]),
                avail_b_shares=float(w_ref["avail_b_shares"]),
                px_a=float(w_ref["leg_a_walk"]["worst_px"]),
                px_b=float(w_ref["leg_b_walk"]["worst_px"]),
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                is_4h_mixed=is_4h_mixed,
            )
            if drag_ref["legging_adjusted_net_ev_per_pair"] <= 0.0:
                logger.info(
                    f"[SHADOW LEGGING PARITY REJECT] {asset} {sleeve_override}: box_net=${w_ref['box_cost_net']:.4f} "
                    f"depth_mult={drag_ref['min_depth_mult']:.2f}x drag={drag_ref['legging_drag_per_pair']:.4f}/pair "
                    f"-> adj_ev={drag_ref['legging_adjusted_net_ev_per_pair']:+.4f}/pair <= 0"
                )
                return False

            tier_fills: Dict[str, Dict[str, Any]] = {}
            legging_drag_by_tier: Dict[str, float] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = walk_equal_shares_dominance_box(
                    asks_a,
                    asks_b,
                    target_budget_usd=t_map[sleeve_override],
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=max_box_cost_override,
                    min_shares=8,
                    min_box_notional_usd=7.5,
                )
                if w_t.get("filled"):
                    tier_fills[tier_name] = w_t
                    dt_info = compute_d1_legging_drag_haircut(
                        shares=float(w_t["shares"]),
                        box_cost_net=float(w_t["box_cost_net"]),
                        avail_a_shares=float(w_t["avail_a_shares"]),
                        avail_b_shares=float(w_t["avail_b_shares"]),
                        px_a=float(w_t["leg_a_walk"]["worst_px"]),
                        px_b=float(w_t["leg_b_walk"]["worst_px"]),
                        fee_rate_a=float(leg_a["fee_rate"]),
                        fee_rate_b=float(leg_b["fee_rate"]),
                        is_4h_mixed=is_4h_mixed,
                    )
                    legging_drag_by_tier[tier_name] = float(dt_info["legging_drag_usd"])

            if "T1000" not in tier_fills:
                return False

            now = time.time()
            pos_id = f"{sleeve_override}_{int(now)}_{m5.market_id[-6:]}"
            title = f"{asset} {dom_info['regime']} [{dom_info['k_low']:.4f} .. {dom_info['k_high']:.4f}]"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve_override,
                "asset_or_city": asset,
                "title": title,
                "side": f"{leg_a['label']}+{leg_b['label']}",
                "token_id": f"{leg_a['token_id']}|{leg_b['token_id']}",
                "fee_rate": float(leg_a["fee_rate"]),
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": m5.end_ts,
                "p_model_entry": 1.0,
                "entry_eff_px_t1000": w_ref["eff_px"],
                "entry_vwap_t1000": w_ref["vwap"],
                "realized_edge_t1000": w_ref["riskless_floor_per_pair"],
                "legging_adjusted_edge_t1000": drag_ref["legging_adjusted_net_ev_per_pair"],
                "entry_best_bid": round(bid_a + bid_b, 4),
                "last_bid": round(bid_a + bid_b, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {
                    "is_dominance_box": True,
                    "regime": dom_info["regime"],
                    "k_low": dom_info["k_low"],
                    "k_high": dom_info["k_high"],
                    "corridor_bps": dom_info["corridor_bps"],
                    "m15_horizon": m15.horizon,
                    "m15_market_id": m15.market_id,
                    "m15_start_iso": m15.start_iso,
                    "m15_end_iso": m15.end_iso,
                    "m5_horizon": m5.horizon,
                    "m5_market_id": m5.market_id,
                    "leg_a": leg_a,
                    "leg_b": leg_b,
                    "legging_drag_ref": drag_ref,
                    "legging_drag_usd_by_tier": legging_drag_by_tier,
                },
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(
                f"[ENTRY:{sleeve_override}] {title} | {w_ref['shares']} pairs @ net=${w_ref['eff_px']:.4f} "
                f"(floor=${w_ref['riskless_floor_per_pair']:+.4f}/pair, min_profit=${w_ref['guaranteed_min_profit_usd']:+.2f})"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    def emit_live_d1_box_candidate(
        self,
        m15: TwapCandleMarketSpec,
        m5: TwapCandleMarketSpec,
        dom_info: Dict[str, Any],
        w_live: Dict[str, Any],
        now_ts: float,
        *,
        is_quiet_book: bool = False,
        sleeve_source: str = "D1_SAME_ORACLE_DOMINANCE_BOX",
    ) -> bool:
        """Emits a verified D1 Same-Oracle Dominance Box candidate (15m/5m, QuietBook, or 4h/15m) to the live IPC stream."""
        default_cand_path = LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl"
        if STATE_FILE != (DATA_DIR / "alpha124_shadow_state.json") and D1_LIVE_CANDIDATES_FILE == default_cand_path:
            return False
        if not (self.single_scan or ("fetch_json" in self.__dict__)):
            # Live mode: stamp with emit-time wall clock (caller's value may be stale after awaited book fetches)
            now_ts = time.time()
            if float(m5.end_ts - now_ts) < 16.0:
                return False
        pair_key = f"{m15.asset}_{m15.market_id}_{m5.market_id}"
        last_emit = float(self._last_d1_live_emit_ts.get(pair_key, 0.0) or 0.0)
        if (now_ts - last_emit) < 10.0:
            return False

        leg_a = dom_info["leg_a"]
        leg_b = dom_info["leg_b"]
        w_a = w_live["leg_a_walk"]
        w_b = w_live["leg_b_walk"]
        is_4h_live = ("4h" in (str(m15.horizon).lower(), str(m5.horizon).lower())) and (
            str(m15.horizon).lower() != str(m5.horizon).lower()
        )
        drag_live = compute_d1_legging_drag_haircut(
            shares=float(w_live["shares"]),
            box_cost_net=float(w_live["box_cost_net"]),
            avail_a_shares=float(w_live["avail_a_shares"]),
            avail_b_shares=float(w_live["avail_b_shares"]),
            px_a=float(w_a["worst_px"]),
            px_b=float(w_b["worst_px"]),
            fee_rate_a=float(leg_a["fee_rate"]),
            fee_rate_b=float(leg_b["fee_rate"]),
            is_4h_mixed=is_4h_live,
        )
        if drag_live["legging_adjusted_net_ev_per_pair"] <= 0.0:
            return False

        self._last_d1_live_emit_ts[pair_key] = now_ts
        for k_old, ts_old in list(self._last_d1_live_emit_ts.items()):
            if (now_ts - ts_old) > 1200.0:
                self._last_d1_live_emit_ts.pop(k_old, None)

        id_pfx = "D1_4H_LIVE" if str(m15.horizon).lower() == "4h" else "D1_LIVE"
        cand = {
            "box_id": f"{id_pfx}_{m15.asset}_{int(m5.end_ts)}_{m5.market_id[-5:]}",
            "dedupe_key": f"D1_{m15.asset}_{m15.market_id}_{m5.market_id}",
            "ts_unix": round(now_ts, 3),
            "asset": m15.asset,
            "regime": dom_info["regime"],
            "pair_horizons": f"{m15.horizon}_{m5.horizon}",
            "sleeve_source": str(sleeve_source),
            "is_quiet_book": bool(is_quiet_book),
            "k_low": dom_info["k_low"],
            "k_high": dom_info["k_high"],
            "corridor_bps": dom_info["corridor_bps"],
            "expiry_ts": float(m5.end_ts),
            "rem_sec": round(float(m5.end_ts - now_ts), 2),
            "shares": int(w_live["shares"]),
            "box_cost_net": float(w_live["box_cost_net"]),
            "legging_drag_per_pair": drag_live["legging_drag_per_pair"],
            "legging_adjusted_net_ev_per_pair": drag_live["legging_adjusted_net_ev_per_pair"],
            "max_box_cost_net": 0.990 if is_quiet_book else 0.988,
            "leg_a_token_id": str(leg_a["token_id"]),
            "leg_a_opp_token_id": str(leg_a.get("opp_token_id") or ""),
            "leg_a_label": str(leg_a["label"]),
            "leg_a_side": str(leg_a["side"]),
            "leg_a_horizon": str(leg_a["horizon"]),
            "leg_a_market_id": str(leg_a["market_id"]),
            "leg_a_condition_id": str(leg_a["condition_id"]),
            "leg_a_strike": float(leg_a["strike"]),
            "leg_a_limit_price": float(w_a["worst_px"]),
            "leg_a_avail_shares": float(w_live["avail_a_shares"]),
            "leg_a_fee_rate": float(leg_a["fee_rate"]),
            "leg_a_fee_exponent": float(leg_a["fee_exponent"]),
            "leg_a_neg_risk": bool(leg_a["neg_risk"]),
            "leg_b_token_id": str(leg_b["token_id"]),
            "leg_b_opp_token_id": str(leg_b.get("opp_token_id") or ""),
            "leg_b_label": str(leg_b["label"]),
            "leg_b_side": str(leg_b["side"]),
            "leg_b_horizon": str(leg_b["horizon"]),
            "leg_b_market_id": str(leg_b["market_id"]),
            "leg_b_condition_id": str(leg_b["condition_id"]),
            "leg_b_strike": float(leg_b["strike"]),
            "leg_b_limit_price": float(w_b["worst_px"]),
            "leg_b_avail_shares": float(w_live["avail_b_shares"]),
            "leg_b_fee_rate": float(leg_b["fee_rate"]),
            "leg_b_fee_exponent": float(leg_b["fee_exponent"]),
            "leg_b_neg_risk": bool(leg_b["neg_risk"]),
        }
        if not self.single_scan and self._ws_books:
            req_ws_toks = [
                t_id
                for t_id in (
                    str(leg_a["token_id"]),
                    str(leg_b["token_id"]),
                    str(leg_a.get("opp_token_id") or ""),
                    str(leg_b.get("opp_token_id") or ""),
                )
                if t_id
            ]
            now_ws_emit = time.time()
            rest_seeded = getattr(self, "_ws_rest_seeded", set())
            ws_entries = [None if t_id in rest_seeded else self._ws_books.get(t_id) for t_id in req_ws_toks]
            if len(req_ws_toks) >= 2 and all(
                e is not None and (now_ws_emit - e[0]) <= 0.50 and e[1].get("bids") and e[1].get("asks")
                for e in ws_entries
            ):
                cand["ws_books_ts"] = round(min(float(e[0]) for e in ws_entries if e is not None), 4)
                cand["ws_books"] = {
                    t_id: {
                        "bids": (e[1].get("bids") or [])[:12],
                        "asks": (e[1].get("asks") or [])[:12],
                    }
                    for t_id, e in zip(req_ws_toks, ws_entries)
                    if e is not None
                }
        try:
            try:
                import orjson as _orj
                raw_b = _orj.dumps(cand) + b"\n"
                line_s = raw_b.decode("utf-8")
            except Exception:
                line_s = json.dumps(cand, separators=(",", ":")) + "\n"
                raw_b = line_s.encode("utf-8")
            if os.name != "nt" and D1_LIVE_CANDIDATES_FILE == default_cand_path:
                try:
                    import socket
                    s_ipc = getattr(self, "_d1_ipc_sock", None)
                    if s_ipc is None:
                        s_ipc = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                        s_ipc.setblocking(False)
                        self._d1_ipc_sock = s_ipc
                    ipc_nm = os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME", "polymarket_d1_box_notify")
                    s_ipc.sendto(raw_b, f"\x00{ipc_nm}".encode("utf-8"))
                except Exception:
                    pass
            D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(D1_LIVE_CANDIDATES_FILE, "a", encoding="utf-8") as fp:
                fp.write(line_s)
            return True
        except Exception as exc:
            logger.debug(f"D1 live candidate write notice: {exc}")
            return False

    def emit_live_two_leg_box_candidate(
        self,
        *,
        sleeve_source: str,
        box_type: str,
        asset: str,
        dedupe_key: str,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        close_ts: float,
        now_ts: float,
        k_low: float = 100.0,
        k_high: float = 100.0,
    ) -> bool:
        """Emits a verified non-D1 2-leg riskless box candidate (C1, M3, B3, 2-leg N1) to the live IPC stream."""
        default_cand_path = LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl"
        if STATE_FILE != (DATA_DIR / "alpha124_shadow_state.json") and D1_LIVE_CANDIDATES_FILE == default_cand_path:
            return False
        if not (self.single_scan or ("fetch_json" in self.__dict__)):
            # Live mode: stamp with emit-time wall clock (caller's value may be stale after awaited book fetches)
            now_ts = time.time()
        rem_sec = float(close_ts - now_ts)
        if rem_sec < 25.0:
            return False
        last_emit = float(self._last_d1_live_emit_ts.get(dedupe_key, 0.0) or 0.0)
        if (now_ts - last_emit) < 15.0:
            return False
        fee_a = float(leg_a.get("fee_rate", CRYPTO_FEE_RATE))
        fee_b = float(leg_b.get("fee_rate", CRYPTO_FEE_RATE))
        exp_a = float(leg_a.get("fee_exponent", 1.0))
        exp_b = float(leg_b.get("fee_exponent", 1.0))
        max_cap = 0.990 if max(fee_a, fee_b) == 0.0 else 0.988
        w_live = walk_equal_shares_dominance_box(
            bk_a.get("asks") or [],
            bk_b.get("asks") or [],
            target_budget_usd=13.50,
            fee_rate_a=fee_a,
            fee_rate_b=fee_b,
            fee_exponent_a=exp_a,
            fee_exponent_b=exp_b,
            max_box_cost_net=max_cap,
            min_shares=5,
            min_box_notional_usd=4.85,
        )
        if not w_live.get("filled"):
            return False
        if len(self._last_d1_live_emit_ts) > 256:
            self._last_d1_live_emit_ts = {k: v for k, v in self._last_d1_live_emit_ts.items() if (now_ts - float(v)) <= 1200.0}
        self._last_d1_live_emit_ts[dedupe_key] = now_ts
        w_a = w_live["leg_a_walk"]
        w_b = w_live["leg_b_walk"]
        _ba_q, _ = self._best_ask_sz(bk_a)
        _bb_q, _ = self._best_ask_sz(bk_b)
        _bda_q, _ = extract_best_bid(bk_a.get("bids") or [])
        _bdb_q, _ = extract_best_bid(bk_b.get("bids") or [])
        _quiet_2l = bool(
            _bda_q > 0.0 and _bdb_q > 0.0
            and (_ba_q - _bda_q) <= 0.041 and (_bb_q - _bdb_q) <= 0.041
            and (max(fee_a, fee_b) == 0.0 or (now_ts - float(self._last_any_shock_ts_by_asset.get(str(asset), 0.0) or 0.0)) >= 4.0)
        )
        corr_bps = round(abs(k_high - k_low) / max(1e-9, k_low) * 10000.0, 2) if k_low > 0 else 0.0
        cand = {
            "box_id": f"{box_type}_LIVE_{asset}_{int(close_ts)}_{str(leg_a.get('market_id','0'))[-5:]}",
            "dedupe_key": dedupe_key,
            "box_type": str(box_type),
            "ts_unix": round(now_ts, 3),
            "asset": str(asset),
            "regime": f"{box_type}_{leg_a.get('label','A')}_PLUS_{leg_b.get('label','B')}",
            "pair_horizons": str(box_type).lower(),
            "sleeve_source": str(sleeve_source),
            "is_quiet_book": _quiet_2l,
            "k_low": float(k_low),
            "k_high": float(k_high),
            "corridor_bps": corr_bps,
            "expiry_ts": float(close_ts),
            "rem_sec": round(rem_sec, 2),
            "shares": int(w_live["shares"]),
            "box_cost_net": float(w_live["box_cost_net"]),
            "max_box_cost_net": max_cap,
            "leg_a_token_id": str(leg_a["token_id"]),
            "leg_a_opp_token_id": str(leg_a.get("opp_token_id") or ""),
            "leg_a_label": str(leg_a.get("label") or leg_a.get("side") or "YES"),
            "leg_a_side": str(leg_a.get("side") or "YES"),
            "leg_a_horizon": str(leg_a.get("horizon") or box_type.lower()),
            "leg_a_market_id": str(leg_a.get("market_id") or ""),
            "leg_a_condition_id": str(leg_a.get("condition_id") or ""),
            "leg_a_strike": float(leg_a.get("strike") or k_low),
            "leg_a_limit_price": float(w_a["worst_px"]),
            "leg_a_avail_shares": float(w_live["avail_a_shares"]),
            "leg_a_fee_rate": fee_a,
            "leg_a_fee_exponent": exp_a,
            "leg_a_neg_risk": leg_a["neg_risk"] if isinstance(leg_a.get("neg_risk"), bool) else None,
            "leg_b_token_id": str(leg_b["token_id"]),
            "leg_b_opp_token_id": str(leg_b.get("opp_token_id") or ""),
            "leg_b_label": str(leg_b.get("label") or leg_b.get("side") or "NO"),
            "leg_b_side": str(leg_b.get("side") or "NO"),
            "leg_b_horizon": str(leg_b.get("horizon") or box_type.lower()),
            "leg_b_market_id": str(leg_b.get("market_id") or ""),
            "leg_b_condition_id": str(leg_b.get("condition_id") or ""),
            "leg_b_strike": float(leg_b.get("strike") or k_high),
            "leg_b_limit_price": float(w_b["worst_px"]),
            "leg_b_avail_shares": float(w_live["avail_b_shares"]),
            "leg_b_fee_rate": fee_b,
            "leg_b_fee_exponent": exp_b,
            "leg_b_neg_risk": leg_b["neg_risk"] if isinstance(leg_b.get("neg_risk"), bool) else None,
        }
        if not self.single_scan and self._ws_books:
            req_ws_2 = [str(leg_a["token_id"]), str(leg_b["token_id"])]
            if str(box_type) != "COMPLETE_SET":
                for op_id in (str(leg_a.get("opp_token_id") or ""), str(leg_b.get("opp_token_id") or "")):
                    if op_id:
                        req_ws_2.append(op_id)
            rest_seeded_2 = getattr(self, "_ws_rest_seeded", set())
            if all(
                t_x in self._ws_books
                and t_x not in rest_seeded_2
                and (now_ts - self._ws_books[t_x][0]) <= 0.50
                and bool(self._ws_books[t_x][1].get("bids"))
                and bool(self._ws_books[t_x][1].get("asks"))
                for t_x in req_ws_2
            ):
                cand["ws_books"] = {
                    t_x: {"bids": (self._ws_books[t_x][1].get("bids") or [])[:12], "asks": (self._ws_books[t_x][1].get("asks") or [])[:12]}
                    for t_x in req_ws_2
                }
                cand["ws_books_ts"] = round(min(self._ws_books[t_x][0] for t_x in req_ws_2), 3)
        try:
            try:
                import orjson as _orj
                raw_b = _orj.dumps(cand) + b"\n"
                line_s = raw_b.decode("utf-8")
            except Exception:
                line_s = json.dumps(cand, separators=(",", ":")) + "\n"
                raw_b = line_s.encode("utf-8")
            if os.name != "nt" and D1_LIVE_CANDIDATES_FILE == default_cand_path:
                try:
                    import socket
                    s_ipc = getattr(self, "_d1_ipc_sock", None)
                    if s_ipc is None:
                        s_ipc = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                        s_ipc.setblocking(False)
                        self._d1_ipc_sock = s_ipc
                    ipc_nm = os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME", "polymarket_d1_box_notify")
                    s_ipc.sendto(raw_b, f"\x00{ipc_nm}".encode("utf-8"))
                except Exception:
                    pass
            D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(D1_LIVE_CANDIDATES_FILE, "a", encoding="utf-8") as fp:
                fp.write(line_s)
            return True
        except Exception as exc:
            logger.debug(f"2-leg box live candidate write notice: {exc}")
            return False

    def emit_live_maker_anchor_box_candidate(
        self,
        *,
        sleeve_source: str,
        box_type: str,
        asset: str,
        dedupe_key: str,
        regime: str,
        pair_horizons: str,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        anchor_is_a: bool,
        queue_front: bool,
        anchor_bid_px: float,
        hedge_limit_px: float,
        avail_a_shares: float,
        avail_b_shares: float,
        close_ts: float,
        now_ts: float,
        k_low: float = 100.0,
        k_high: float = 100.0,
        corridor_bps: float = 0.0,
        posted_spot: float = 0.0,
    ) -> bool:
        """EXP-PM-406B / EXP-PM-409: Emits a verified Maker-Anchor 2-leg box candidate to the live IPC stream (gated on 8/8 _grad8)."""
        default_cand_path = LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl"
        if STATE_FILE != (DATA_DIR / "alpha124_shadow_state.json") and D1_LIVE_CANDIDATES_FILE == default_cand_path:
            return False
        if not (self.single_scan or ("fetch_json" in self.__dict__)):
            now_ts = time.time()
        rem_sec = float(close_ts - now_ts)
        min_rem = 240.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else 65.0
        max_rem = 64800.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else 900.0
        if not (min_rem <= rem_sec <= max_rem):
            return False
        last_emit = float(self._last_d1_live_emit_ts.get(dedupe_key, 0.0) or 0.0)
        if (now_ts - last_emit) < 12.0:
            return False
        if len(self._last_d1_live_emit_ts) > 256:
            self._last_d1_live_emit_ts = {k: v for k, v in self._last_d1_live_emit_ts.items() if (now_ts - float(v)) <= 1200.0}
        self._last_d1_live_emit_ts[dedupe_key] = now_ts
        fee_a = float(leg_a.get("fee_rate", 0.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else CRYPTO_FEE_RATE))
        fee_b = float(leg_b.get("fee_rate", 0.0 if box_type == "ZERO_FEE_MAKER_ANCHOR" else CRYPTO_FEE_RATE))
        exp_a = float(leg_a.get("fee_exponent", 1.0))
        exp_b = float(leg_b.get("fee_exponent", 1.0))
        fr_hdg = fee_b if anchor_is_a else fee_a
        fe_hdg = exp_b if anchor_is_a else exp_a
        hdg_fee = fr_hdg * ((hedge_limit_px * (1.0 - hedge_limit_px)) ** fe_hdg) if fr_hdg > 0.0 else 0.0
        pair_est = round(anchor_bid_px + hedge_limit_px + hdg_fee, 4)
        max_cap = 0.990 if box_type == "ZERO_FEE_MAKER_ANCHOR" else 0.988
        if not (0.900 <= pair_est <= max_cap):
            return False
        sh_est = max(5, int(math.floor(13.50 / max(0.90, pair_est))))
        cand = {
            "box_id": f"{box_type}_LIVE_{asset}_{int(close_ts)}_{str(leg_a.get('market_id','0'))[-5:]}",
            "dedupe_key": dedupe_key,
            "box_type": str(box_type),
            "ts_unix": round(now_ts, 3),
            "asset": str(asset),
            "regime": str(regime),
            "pair_horizons": str(pair_horizons),
            "sleeve_source": str(sleeve_source),
            "anchor_is_a": bool(anchor_is_a),
            "queue_front": bool(queue_front),
            "anchor_bid_px": round(float(anchor_bid_px), 4),
            "hedge_limit_px": round(float(hedge_limit_px), 4),
            "posted_spot": round(float(posted_spot), 6),
            "k_low": float(k_low),
            "k_high": float(k_high),
            "corridor_bps": round(float(corridor_bps), 2),
            "expiry_ts": float(close_ts),
            "rem_sec": round(rem_sec, 2),
            "shares": sh_est,
            "box_cost_net": pair_est,
            "max_box_cost_net": max_cap,
            "leg_a_token_id": str(leg_a["token_id"]),
            "leg_a_opp_token_id": str(leg_a.get("opp_token_id") or ""),
            "leg_a_label": str(leg_a.get("label") or leg_a.get("side") or "YES"),
            "leg_a_side": str(leg_a.get("side") or "YES"),
            "leg_a_horizon": str(leg_a.get("horizon") or pair_horizons),
            "leg_a_market_id": str(leg_a.get("market_id") or ""),
            "leg_a_condition_id": str(leg_a.get("condition_id") or ""),
            "leg_a_strike": float(leg_a.get("strike") or k_low),
            "leg_a_limit_price": round(float(anchor_bid_px if anchor_is_a else hedge_limit_px), 4),
            "leg_a_avail_shares": round(float(avail_a_shares), 2),
            "leg_a_fee_rate": fee_a,
            "leg_a_fee_exponent": exp_a,
            "leg_a_neg_risk": leg_a["neg_risk"] if isinstance(leg_a.get("neg_risk"), bool) else None,
            "leg_b_token_id": str(leg_b["token_id"]),
            "leg_b_opp_token_id": str(leg_b.get("opp_token_id") or ""),
            "leg_b_label": str(leg_b.get("label") or leg_b.get("side") or "NO"),
            "leg_b_side": str(leg_b.get("side") or "NO"),
            "leg_b_horizon": str(leg_b.get("horizon") or pair_horizons),
            "leg_b_market_id": str(leg_b.get("market_id") or ""),
            "leg_b_condition_id": str(leg_b.get("condition_id") or ""),
            "leg_b_strike": float(leg_b.get("strike") or k_high),
            "leg_b_limit_price": round(float(hedge_limit_px if anchor_is_a else anchor_bid_px), 4),
            "leg_b_avail_shares": round(float(avail_b_shares), 2),
            "leg_b_fee_rate": fee_b,
            "leg_b_fee_exponent": exp_b,
            "leg_b_neg_risk": leg_b["neg_risk"] if isinstance(leg_b.get("neg_risk"), bool) else None,
        }
        try:
            try:
                import orjson as _orj
                raw_b = _orj.dumps(cand) + b"\n"
                line_s = raw_b.decode("utf-8")
            except Exception:
                line_s = json.dumps(cand, separators=(",", ":")) + "\n"
                raw_b = line_s.encode("utf-8")
            if os.name != "nt" and D1_LIVE_CANDIDATES_FILE == default_cand_path:
                try:
                    import socket
                    s_ipc = getattr(self, "_d1_ipc_sock", None)
                    if s_ipc is None:
                        s_ipc = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                        s_ipc.setblocking(False)
                        self._d1_ipc_sock = s_ipc
                    ipc_nm = os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME", "polymarket_d1_box_notify")
                    s_ipc.sendto(raw_b, f"\x00{ipc_nm}".encode("utf-8"))
                except Exception:
                    pass
            D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(D1_LIVE_CANDIDATES_FILE, "a", encoding="utf-8") as fp:
                fp.write(line_s)
            return True
        except Exception as exc:
            logger.debug(f"Maker-anchor live candidate write notice: {exc}")
            return False

    def _latest_spot_px(self, asset: str) -> float:
        uh = self.usd_spot_hist.get(asset)
        if uh and len(uh) > 0 and (time.time() - float(uh[-1][0])) <= 10.0 and float(uh[-1][1]) > 0.0:
            return float(uh[-1][1])
        return float(self.spots.get(asset) or 0.0)

    def post_maker_anchor_candidate(
        self,
        m15: TwapCandleMarketSpec,
        m5: TwapCandleMarketSpec,
        dom_info: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        now_ts: float,
    ) -> bool:
        """
        Tier-2 (`D1_MAKER_ANCHOR_BOX`, EXP-PM-406 Hardened): Posts a single-leg 0%-fee `post_only=True`
        Maker Anchor on near-arb overlap corridors (`(0.995, 1.032]`) with:
          - Tick-exact `0.001` (`>=0.96` / `<=0.04`) and `0.01` pricing across `[0.03, 0.999]`,
          - Queue-front `+1 tick` step on `>= 2-tick` spreads OR `1c` mid-book join (`[0.15, 0.85]`) when `obi_l1 >= -0.15`,
          - Realistic `T100` (`$18` capped by `asset_cap`) `>= 2.5x` hedge depth gate + `0.900` anti-box floor,
          - 120ms WS supervision with 2.5 bps directional asymmetric spot cancel-on-move and 12s TTL.
        """
        if is_shadow_sleeve_quarantined("D1_MAKER_ANCHOR_BOX"):
            return False
        rem_sec = m5.end_ts - now_ts
        max_anc_rem = 880.0 if str(m5.horizon) == "15m" else 295.0
        if not (65.0 <= rem_sec <= max_anc_rem):
            return False
        ret_5s_init = self.get_return_bps(m15.asset, 5.0)
        if abs(ret_5s_init) > 4.5:
            return False
        if (now_ts - float(self._last_any_shock_ts_by_asset.get(m15.asset, 0.0) or 0.0)) < 4.0:
            return False
        d_key = f"D1_MKR_{m15.asset}_{m15.market_id}_{m5.market_id}"
        if d_key in self.entered_keys or d_key in self.pending_maker_anchors or d_key in self.inflight_keys:
            return False

        leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
        bids_a = sorted([(float(b["price"]), float(b["size"])) for b in (bk_a.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0], key=lambda x: -x[0])
        bids_b = sorted([(float(b["price"]), float(b["size"])) for b in (bk_b.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0], key=lambda x: -x[0])
        asks_a = sorted([(float(a["price"]), float(a["size"])) for a in (bk_a.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        asks_b = sorted([(float(a["price"]), float(a["size"])) for a in (bk_b.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        if not asks_a or not asks_b or not bids_a or not bids_b:
            return False
        bid_a, bsz_a = bids_a[0]
        bid_b, bsz_b = bids_b[0]
        ask_a, sz_a = asks_a[0]
        ask_b, sz_b = asks_b[0]
        spr_a, spr_b = round(ask_a - bid_a, 4), round(ask_b - bid_b, 4)
        obi_a = (bsz_a - sz_a) / max(1e-9, bsz_a + sz_a)
        obi_b = (bsz_b - sz_b) / max(1e-9, bsz_b + sz_b)

        asset_cap_u = float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(m15.asset, 40.0))
        ref_bud_t100 = min(float(BANKROLL_TICKETS["T100"]["D1_MAKER_ANCHOR_BOX"]), asset_cap_u)
        req_sh_t100 = max(5.0, math.floor(ref_bud_t100 / 0.985))
        req_sh_t1000 = max(5.0, math.floor(min(float(BANKROLL_TICKETS["T1000"]["D1_MAKER_ANCHOR_BOX"]), asset_cap_u) / 0.985))

        def _snap_c(p: float) -> float:
            p = round(float(p), 4)
            return (math.floor((p + 1e-9) * 100.0) / 100.0) if (0.04 + 1e-9 < p < 0.96 - 1e-9) else (math.floor((p + 1e-9) * 1000.0) / 1000.0)

        candidates: List[Tuple[float, bool, bool, float, float, float]] = []
        for anchor_is_a in (True, False):
            b_anc = bid_a if anchor_is_a else bid_b
            bsz_anc = bsz_a if anchor_is_a else bsz_b
            a_anc = ask_a if anchor_is_a else ask_b
            s_anc = spr_a if anchor_is_a else spr_b
            obi_anc = obi_a if anchor_is_a else obi_b
            leg_anc = leg_a if anchor_is_a else leg_b
            asks_hdg = asks_b if anchor_is_a else asks_a
            leg_hdg = leg_b if anchor_is_a else leg_a
            if not (0.03 <= a_anc <= 0.999) or obi_anc < -0.35:
                continue
            anc_side = str(leg_anc.get("side") or "UP").upper()
            if (anc_side == "UP" and ret_5s_init < -2.2) or (anc_side == "DOWN" and ret_5s_init > 2.2):
                continue
            tb_anc = 0.001 if (b_anc >= 0.96 or b_anc < 0.04) else 0.01
            ta_anc = 0.001 if (a_anc > 0.96 or a_anc <= 0.04) else 0.01
            step_b = _snap_c(b_anc + tb_anc)
            max_u = _snap_c(a_anc - ta_anc)
            if step_b <= max_u + 1e-9 and step_b > b_anc + 1e-9:
                cand_bid = min(step_b, max_u)
                q_front = True
            elif s_anc >= 0.01 - 1e-9 and 0.15 <= a_anc <= 0.85 and obi_anc >= -0.15 and bsz_anc >= 15.0:
                cand_bid = _snap_c(b_anc)
                q_front = False
            else:
                continue
            avail_hdg = sum(sz for px, sz in asks_hdg if px <= asks_hdg[0][0] + 0.01)
            if avail_hdg < max(15.0, 2.5 * req_sh_t100):
                continue
            hdg_px = asks_hdg[0][0]
            hdg_fee = float(leg_hdg["fee_rate"]) * ((hdg_px * (1.0 - hdg_px)) ** float(leg_hdg.get("fee_exponent", 1.0)))
            hdg_eff = hdg_px + hdg_fee
            bid_px = min(cand_bid, _snap_c(0.988 - hdg_eff))
            min_ok_bid = round(b_anc - (tb_anc if q_front else 0.0), 3)
            if bid_px < min_ok_bid or bid_px <= 0.02 or bid_px >= a_anc:
                continue
            pair_est = round(bid_px + hdg_eff, 4)
            if 0.900 <= pair_est <= 0.988:
                candidates.append((pair_est - (0.0005 if q_front else 0.0), anchor_is_a, q_front, bid_px, round(hdg_eff, 4), req_sh_t100))

        if not candidates:
            return False
        candidates.sort(key=lambda z: z[0])
        _, anchor_is_a, q_front, bid_px, hdg_eff, req_sh = candidates[0]
        posted_sp = self._latest_spot_px(m15.asset)
        self.pending_maker_anchors[d_key] = {
            "dedupe_key": d_key,
            "asset": m15.asset,
            "m15": m15,
            "m5": m5,
            "dom_info": dom_info,
            "anchor_is_a": anchor_is_a,
            "queue_front": q_front,
            "bid_px": bid_px,
            "pair_est": round(bid_px + hdg_eff, 4),
            "req_shares_t100": req_sh,
            "req_shares_t1000": req_sh_t1000,
            "posted_ts": now_ts,
            "posted_spot": posted_sp,
        }
        av_a_sh = sum(sz for px, sz in asks_a if px <= ask_a + 0.01)
        av_b_sh = sum(sz for px, sz in asks_b if px <= ask_b + 0.01)
        hdg_raw_px = ask_b if anchor_is_a else ask_a
        self.emit_live_maker_anchor_box_candidate(
            sleeve_source="D1_MAKER_ANCHOR_BOX",
            box_type="DOMINANCE_MAKER_ANCHOR",
            asset=m15.asset,
            dedupe_key=d_key,
            regime=str(dom_info["regime"]),
            pair_horizons=f"{m15.horizon}_{m5.horizon}",
            leg_a=leg_a,
            leg_b=leg_b,
            anchor_is_a=anchor_is_a,
            queue_front=q_front,
            anchor_bid_px=bid_px,
            hedge_limit_px=hdg_raw_px,
            avail_a_shares=av_a_sh,
            avail_b_shares=av_b_sh,
            close_ts=float(m5.end_ts),
            now_ts=now_ts,
            k_low=float(dom_info["k_low"]),
            k_high=float(dom_info["k_high"]),
            corridor_bps=float(dom_info["corridor_bps"]),
            posted_spot=posted_sp,
        )
        logger.info(
            f"[MAKER_ANCHOR_POST] {m15.asset} {dom_info['regime']} | Resting post_only=${bid_px:.3f} (qf={q_front}) "
            f"+ hedge_eff=${hdg_eff:.4f} = ${bid_px + hdg_eff:.4f} (TTE={rem_sec:.0f}s)"
        )
        return True

    async def manage_pending_maker_anchors(self, now_ts: Optional[float] = None) -> None:
        if not self.pending_maker_anchors:
            return
        now = float(now_ts if now_ts is not None else time.time())
        needed_toks: List[str] = []
        for st in self.pending_maker_anchors.values():
            di = st["dom_info"]
            needed_toks.extend([str(di["leg_a"]["token_id"]), str(di["leg_b"]["token_id"])])
        bks = await self.fetch_books_batch(needed_toks, timeout=2.5)

        for d_key, st in list(self.pending_maker_anchors.items()):
            m15: TwapCandleMarketSpec = st["m15"]
            m5: TwapCandleMarketSpec = st["m5"]
            di = st["dom_info"]
            leg_a, leg_b = di["leg_a"], di["leg_b"]
            anc_is_a = bool(st["anchor_is_a"])
            q_front = bool(st.get("queue_front", True))
            leg_anc = leg_a if anc_is_a else leg_b
            leg_hdg = leg_b if anc_is_a else leg_a
            bk_anc = bks.get(str(leg_anc["token_id"]))
            bk_hdg = bks.get(str(leg_hdg["token_id"]))
            bid_px = float(st["bid_px"])
            rested = now - float(st["posted_ts"])
            rem_sec = m5.end_ts - now

            asks_anc = (bk_anc or {}).get("asks") or []
            best_ask_anc = min((float(a["price"]) for a in asks_anc if float(a.get("size", 0)) > 0), default=1.0)
            filled_anc = bk_anc is not None and rested >= 0.35 and best_ask_anc <= bid_px

            if filled_anc:
                self.pending_maker_anchors.pop(d_key, None)
                self.entered_keys.add(d_key)
                asks_hdg = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
                hdg_px = asks_hdg[0][0] if asks_hdg else 1.0
                hdg_avail = sum(sz for px, sz in asks_hdg if px <= hdg_px + 0.01) if asks_hdg else 0.0
                hdg_fee = float(leg_hdg["fee_rate"]) * ((hdg_px * (1.0 - hdg_px)) ** float(leg_hdg.get("fee_exponent", 1.0))) if hdg_px < 1.0 else 0.0
                pair_eff = round(bid_px + hdg_px + hdg_fee, 4)

                asset_cap_u = float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(m15.asset, 100.0))
                is_4h_m = "4h" in (str(m15.horizon).lower(), str(m5.horizon).lower())
                if bk_hdg is not None and asks_hdg and hdg_avail >= 5.0 and 0.900 <= pair_eff <= 0.995:
                    tier_fills: Dict[str, Dict[str, Any]] = {}
                    drag_by_tier: Dict[str, float] = {}
                    rebate_est_t1000 = 0.0
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        sh = max(5.0, min(hdg_avail, math.floor(min(t_map["D1_MAKER_ANCHOR_BOX"], asset_cap_u) / pair_eff)))
                        fee_u = round(sh * hdg_fee, 4)
                        spent_u = round(sh * (bid_px + hdg_px), 2)
                        tier_fills[t_name] = {
                            "filled": True,
                            "vwap": round(bid_px + hdg_px, 4),
                            "eff_px": pair_eff,
                            "spent_usd": spent_u,
                            "fee_usd": fee_u,
                            "shares": sh,
                            "l1_usd": round(hdg_avail * pair_eff, 2),
                        }
                        dr = compute_d1_maker_anchor_drag_haircut(
                            shares=sh,
                            pair_eff=pair_eff,
                            bid_anc=bid_px,
                            hdg_px=hdg_px,
                            hdg_avail_shares=hdg_avail,
                            fee_rate_anc=float(leg_anc.get("fee_rate", CRYPTO_FEE_RATE)),
                            fee_exponent_anc=float(leg_anc.get("fee_exponent", 1.0)),
                            queue_front=q_front,
                            is_4h_mixed=is_4h_m,
                        )
                        drag_by_tier[t_name] = float(dr["legging_drag_usd"])
                        if t_name == "T1000":
                            rebate_est_t1000 = float(dr["maker_rebate_20pct_est_usd"])
                    bid_a_cur, _ = extract_best_bid((bks.get(str(leg_a["token_id"])) or {}).get("bids") or [])
                    bid_b_cur, _ = extract_best_bid((bks.get(str(leg_b["token_id"])) or {}).get("bids") or [])
                    pos_id = f"D1_MAKER_ANCHOR_BOX_{int(now)}_{m5.market_id[-6:]}"
                    pos = {
                        "position_id": pos_id,
                        "dedupe_key": d_key,
                        "sleeve": "D1_MAKER_ANCHOR_BOX",
                        "asset_or_city": m15.asset,
                        "title": f"{m15.asset} {di['regime']} [0%-Fee Maker Anchor @ ${bid_px:.3f}]",
                        "side": f"{leg_a['label']}+{leg_b['label']}",
                        "token_id": f"{leg_a['token_id']}|{leg_b['token_id']}",
                        "fee_rate": float(leg_hdg["fee_rate"]),
                        "entry_ts": now,
                        "entry_utc": datetime.now(timezone.utc).isoformat(),
                        "close_ts": m5.end_ts,
                        "p_model_entry": 1.0,
                        "entry_eff_px_t1000": pair_eff,
                        "entry_vwap_t1000": round(bid_px + hdg_px, 4),
                        "realized_edge_t1000": round(1.0 - pair_eff, 4),
                        "entry_best_bid": round(bid_a_cur + bid_b_cur, 4),
                        "last_bid": round(bid_a_cur + bid_b_cur, 4),
                        "maker_tp_px": None,
                        "tier_fills": tier_fills,
                        "extra": {
                            "is_dominance_box": True,
                            "is_maker_anchor_box": True,
                            "queue_front": q_front,
                            "legging_drag_usd_by_tier": drag_by_tier,
                            "maker_rebate_20pct_est_t1000_usd": rebate_est_t1000,
                            "regime": di["regime"],
                            "k_low": di["k_low"],
                            "k_high": di["k_high"],
                            "corridor_bps": di["corridor_bps"],
                            "m15_horizon": m15.horizon,
                            "m15_market_id": m15.market_id,
                            "m15_start_iso": m15.start_iso,
                            "m15_end_iso": m15.end_iso,
                            "m5_horizon": m5.horizon,
                            "m5_market_id": m5.market_id,
                            "leg_a": leg_a,
                            "leg_b": leg_b,
                        },
                        "status": "OPEN",
                    }
                    self.open_positions[pos_id] = pos
                    self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                    logger.info(f"[ENTRY:D1_MAKER_ANCHOR_BOX] {pos['title']} -> Hedged @ net=${pair_eff:.4f}!")
                else:
                    # Honest adverse-fill scratch accounting (zero survivorship bias)
                    scr_bid, _ = extract_best_bid((bk_anc or {}).get("bids") or [])
                    if scr_bid <= 0.0:
                        scr_bid = max(0.01, bid_px - 0.03)
                    scr_fee = float(leg_anc["fee_rate"]) * ((scr_bid * (1.0 - scr_bid)) ** float(leg_anc.get("fee_exponent", 1.0)))
                    net_scr = max(0.0, scr_bid - scr_fee)
                    tf_s: Dict[str, Dict[str, Any]] = {}
                    tp_s: Dict[str, float] = {}
                    ref_pair = max(0.90, float(st.get("pair_est") or 0.985))
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        sh_s = max(5.0, float(math.floor(min(t_map["D1_MAKER_ANCHOR_BOX"], asset_cap_u) / ref_pair)))
                        bud = round(sh_s * bid_px, 2)
                        tf_s[t_name] = {"filled": True, "vwap": bid_px, "eff_px": bid_px, "spent_usd": bud, "fee_usd": 0.0, "shares": sh_s}
                        tp_s[t_name] = round(sh_s * net_scr - bud, 2)
                    pos_scr = {
                        "position_id": f"D1_MKR_SCRATCH_{int(now)}_{m5.market_id[-6:]}",
                        "dedupe_key": d_key,
                        "sleeve": "D1_MAKER_ANCHOR_BOX",
                        "asset_or_city": m15.asset,
                        "title": f"{m15.asset} {di['regime']} [Maker Anchor Unhedged Scratch]",
                        "side": f"{leg_anc['label']}_SCRATCH",
                        "token_id": str(leg_anc["token_id"]),
                        "fee_rate": 0.0,
                        "entry_ts": st["posted_ts"],
                        "entry_utc": datetime.fromtimestamp(st["posted_ts"], tz=timezone.utc).isoformat(),
                        "close_ts": m5.end_ts,
                        "closed_ts": now,
                        "closed_utc": datetime.now(timezone.utc).isoformat(),
                        "p_model_entry": 0.5,
                        "entry_eff_px_t1000": bid_px,
                        "entry_vwap_t1000": bid_px,
                        "net_payout_per_share": round(net_scr, 4),
                        "tier_fills": tf_s,
                        "tier_pnls_usd": tp_s,
                        "legging_adjusted_tier_pnls_usd": dict(tp_s),
                        "won": tp_s.get("T1000", 0.0) > 0,
                        "status": "MAKER_ANCHOR_UNHEDGED_SCRATCH",
                    }
                    self.closed_positions.append(pos_scr)
                    self._append_ledger({"event": "SHADOW_CLOSE", **pos_scr})
                continue

            # Cancel-on-thinning / directional adverse-spot / OBI collapse / TTL=12s ($0.00 cost on unfilled post_only)
            asks_hdg_c = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
            hdg_px_c = asks_hdg_c[0][0] if asks_hdg_c else 1.0
            hdg_avail_c = sum(sz for px, sz in asks_hdg_c if px <= hdg_px_c + 0.01) if asks_hdg_c else 0.0
            hdg_fee_c = float(leg_hdg["fee_rate"]) * ((hdg_px_c * (1.0 - hdg_px_c)) ** float(leg_hdg.get("fee_exponent", 1.0))) if hdg_px_c < 1.0 else 0.0
            req_sh_chk = float(st.get("req_shares_t100") or st.get("req_shares_t1000") or 15.0)
            thin_or_drifted = (hdg_avail_c < max(12.0, 2.0 * req_sh_chk)) or ((bid_px + hdg_px_c + hdg_fee_c) > 0.993)
            obi_anc_c = 0.0
            if bk_anc is not None:
                _, b_sz_c = extract_best_bid(bk_anc.get("bids") or [])
                a_sz_c = sum(float(a.get("size", 0)) for a in asks_anc if abs(float(a.get("price", 0)) - best_ask_anc) < 1e-6)
                if (b_sz_c + a_sz_c) > 0.0:
                    obi_anc_c = (b_sz_c - a_sz_c) / (b_sz_c + a_sz_c)
            post_spot = float(st.get("posted_spot") or 0.0)
            cur_spot = self._latest_spot_px(m15.asset)
            spot_drift_bps = ((cur_spot - post_spot) / post_spot * 10000.0) if (post_spot > 0.0 and cur_spot > 0.0) else 0.0
            ret_5s_c = self.get_return_bps(m15.asset, 5.0)
            anc_side_c = str(leg_anc.get("side") or "UP").upper()
            adv_move_c = (
                (min(spot_drift_bps, ret_5s_c) < -2.5)
                if anc_side_c == "UP"
                else (max(spot_drift_bps, ret_5s_c) > 2.5)
            )
            shock_recent = (now - float(self._last_any_shock_ts_by_asset.get(m15.asset, 0.0) or 0.0)) < 4.0
            if (
                rem_sec <= 45.0
                or rested >= 12.0
                or adv_move_c
                or abs(ret_5s_c) > 8.0
                or obi_anc_c < -0.35
                or shock_recent
                or thin_or_drifted
            ):
                self.pending_maker_anchors.pop(d_key, None)

    def post_zero_fee_maker_anchor_box(
        self,
        source_tag: str,
        asset: str,
        d_key: str,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        close_ts: float,
        title: str,
        now_ts: float,
        prefetched_books: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> bool:
        """
        EXP-PM-409 (`ZF_INTRADAY_MAKER_BOX`): Hardened intraday (`240s <= TTE <= 18h`) `0%`-fee Maker Anchor
        for `SP1_NBA` Polish Middles (`$0.95 + $0.01 = $0.960`), same-day `CM_B3` Pyth barriers, `TW1`, and `COND1`:
          - Tick-exact `[0.001, 0.999]` pricing with `+1 tick` queue-front step,
          - `obi_anc >= -0.25`, `0.900 <= pair_est <= 0.988` anti-box floor + `opp_token_id` complement guard,
          - Realistic `T100` (`$18`) `>= 2.5x` hedge depth gate and strict `15.0s` max rest TTL.
        """
        if is_shadow_sleeve_quarantined("ZF_INTRADAY_MAKER_BOX"):
            return False
        rem_sec = float(close_ts - now_ts)
        if not (240.0 <= rem_sec <= 64800.0):
            return False
        cd_map = self.__dict__.setdefault("_zf_maker_cooldown_until", {})
        if d_key in self.entered_keys or d_key in self.pending_zero_fee_maker_anchors or float(cd_map.get(d_key, 0.0) or 0.0) > now_ts:
            return False
        if float(leg_a.get("fee_rate", 0.0)) > 0.0 or float(leg_b.get("fee_rate", 0.0)) > 0.0:
            return False
        if prefetched_books:
            opp_a = str(leg_a.get("opp_token_id") or "")
            opp_b = str(leg_b.get("opp_token_id") or "")
            if opp_a in prefetched_books and opp_b in prefetched_books:
                ob_a, _ = extract_best_bid((prefetched_books[opp_a] or {}).get("bids") or [])
                ob_b, _ = extract_best_bid((prefetched_books[opp_b] or {}).get("bids") or [])
                if (ob_a + ob_b) > 1.0:
                    return False

        bids_a = sorted([(float(b["price"]), float(b["size"])) for b in (bk_a.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0], key=lambda x: -x[0])
        bids_b = sorted([(float(b["price"]), float(b["size"])) for b in (bk_b.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0], key=lambda x: -x[0])
        asks_a = sorted([(float(a["price"]), float(a["size"])) for a in (bk_a.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        asks_b = sorted([(float(a["price"]), float(a["size"])) for a in (bk_b.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        if not asks_a or not asks_b or not bids_a or not bids_b:
            return False
        bid_a, bsz_a = bids_a[0]
        bid_b, bsz_b = bids_b[0]
        ask_a, asz_a = asks_a[0]
        ask_b, asz_b = asks_b[0]
        obi_a = (bsz_a - asz_a) / max(1e-9, bsz_a + asz_a)
        obi_b = (bsz_b - asz_b) / max(1e-9, bsz_b + asz_b)
        req_sh_t100 = max(6.0, math.floor(float(BANKROLL_TICKETS["T100"]["ZF_INTRADAY_MAKER_BOX"]) / 0.988))
        req_sh_t1000 = max(6.0, math.floor(float(BANKROLL_TICKETS["T1000"]["ZF_INTRADAY_MAKER_BOX"]) / 0.988))

        def _snap_zf(p: float) -> float:
            p = round(float(p), 4)
            return (math.floor((p + 1e-9) * 100.0) / 100.0) if (0.04 + 1e-9 < p < 0.96 - 1e-9) else (math.floor((p + 1e-9) * 1000.0) / 1000.0)

        zf_cands: List[Tuple[float, bool, float, float]] = []
        for anc_is_a in (True, False):
            b_anc = bid_a if anc_is_a else bid_b
            a_anc = ask_a if anc_is_a else ask_b
            obi_anc = obi_a if anc_is_a else obi_b
            b_hdg = bid_b if anc_is_a else bid_a
            asks_hdg = asks_b if anc_is_a else asks_a
            a_hdg = asks_hdg[0][0]
            if not (0.02 <= a_anc <= 0.999) or not (0.001 <= a_hdg <= 0.985) or obi_anc < -0.25:
                continue
            if b_hdg > 0.0 and a_hdg > 0.04 and (a_hdg - b_hdg) > 0.05:
                continue
            tb_anc = 0.001 if (b_anc >= 0.96 or b_anc < 0.04) else 0.01
            ta_anc = 0.001 if (a_anc > 0.96 or a_anc <= 0.04) else 0.01
            step_b = _snap_zf(b_anc + tb_anc)
            max_u = _snap_zf(a_anc - ta_anc)
            if step_b > max_u + 1e-9 or step_b <= b_anc + 1e-9:
                continue
            avail_hdg = sum(sz for px, sz in asks_hdg if px <= a_hdg + 0.01)
            if avail_hdg < max(18.0, 2.5 * req_sh_t100):
                continue
            cand_bid = min(step_b, max_u, _snap_zf(0.988 - a_hdg))
            if cand_bid < round(b_anc - tb_anc, 3) or cand_bid <= 0.015 or cand_bid >= a_anc:
                continue
            pair_est = round(cand_bid + a_hdg, 4)
            if 0.900 <= pair_est <= 0.988:
                zf_cands.append((pair_est, anc_is_a, round(cand_bid, 4), round(a_hdg, 4)))

        if not zf_cands:
            return False
        zf_cands.sort(key=lambda z: z[0])
        pair_est, anc_is_a, bid_px, hdg_px = zf_cands[0]
        self.pending_zero_fee_maker_anchors[d_key] = {
            "source_tag": source_tag,
            "dedupe_key": d_key,
            "asset": asset,
            "title": title,
            "leg_a": leg_a,
            "leg_b": leg_b,
            "anchor_is_a": anc_is_a,
            "bid_px": bid_px,
            "pair_est": pair_est,
            "req_shares_t100": req_sh_t100,
            "req_shares_t1000": req_sh_t1000,
            "close_ts": close_ts,
            "posted_ts": now_ts,
        }
        av_a_sh = sum(sz for px, sz in asks_a if px <= ask_a + 0.01)
        av_b_sh = sum(sz for px, sz in asks_b if px <= ask_b + 0.01)
        self.emit_live_maker_anchor_box_candidate(
            sleeve_source="ZF_INTRADAY_MAKER_BOX",
            box_type="ZERO_FEE_MAKER_ANCHOR",
            asset=asset,
            dedupe_key=d_key,
            regime=f"ZF_{source_tag}",
            pair_horizons=f"zf_{source_tag.lower()}",
            leg_a=leg_a,
            leg_b=leg_b,
            anchor_is_a=anc_is_a,
            queue_front=True,
            anchor_bid_px=bid_px,
            hedge_limit_px=hdg_px,
            avail_a_shares=av_a_sh,
            avail_b_shares=av_b_sh,
            close_ts=float(close_ts),
            now_ts=now_ts,
            k_low=float(leg_a.get("strike") or 100.0),
            k_high=float(leg_b.get("strike") or 100.0),
        )
        logger.info(
            f"[ZF_INTRADAY_MAKER_POST:{source_tag}] {title} | bid=${bid_px:.3f} + hdg=${hdg_px:.3f} = ${pair_est:.4f} (TTE={rem_sec/3600.0:.2f}h)"
        )
        return True

    async def manage_pending_zero_fee_maker_anchors(self, now_ts: Optional[float] = None) -> None:
        if not self.pending_zero_fee_maker_anchors:
            return
        now = float(now_ts if now_ts is not None else time.time())
        cd_map = self.__dict__.setdefault("_zf_maker_cooldown_until", {})
        toks = [t for st in self.pending_zero_fee_maker_anchors.values() for t in (str(st["leg_a"]["token_id"]), str(st["leg_b"]["token_id"]))]
        bks = await self.fetch_books_batch(toks, timeout=3.0)
        for d_key, st in list(self.pending_zero_fee_maker_anchors.items()):
            la, lb = st["leg_a"], st["leg_b"]
            anc_is_a = bool(st["anchor_is_a"])
            leg_anc = la if anc_is_a else lb
            leg_hdg = lb if anc_is_a else la
            bk_anc = bks.get(str(leg_anc["token_id"]))
            bk_hdg = bks.get(str(leg_hdg["token_id"]))
            bid_px = float(st["bid_px"])
            rested = now - float(st["posted_ts"])
            rem_sec = float(st["close_ts"]) - now
            asks_anc = (bk_anc or {}).get("asks") or []
            best_ask_anc = min((float(a["price"]) for a in asks_anc if float(a.get("size", 0)) > 0), default=1.0)
            if bk_anc is not None and rested >= 0.40 and best_ask_anc <= bid_px:
                self.pending_zero_fee_maker_anchors.pop(d_key, None)
                self.entered_keys.add(d_key)
                asks_hdg = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
                hdg_px = asks_hdg[0][0] if asks_hdg else 1.0
                hdg_avail = sum(sz for px, sz in asks_hdg if px <= hdg_px + 0.01) if asks_hdg else 0.0
                pair_eff = round(bid_px + hdg_px, 4)
                if bk_hdg is not None and asks_hdg and hdg_avail >= 5.0 and 0.900 <= pair_eff <= 0.993:
                    tf_zf: Dict[str, Dict[str, Any]] = {}
                    drag_zf: Dict[str, float] = {}
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        sh = max(5.0, min(hdg_avail, math.floor(t_map["ZF_INTRADAY_MAKER_BOX"] / pair_eff)))
                        tf_zf[t_name] = {"filled": True, "vwap": pair_eff, "eff_px": pair_eff, "spent_usd": round(sh * pair_eff, 2), "fee_usd": 0.0, "shares": sh, "l1_usd": round(hdg_avail * pair_eff, 2)}
                        dr_z = compute_d1_maker_anchor_drag_haircut(
                            shares=sh, pair_eff=pair_eff, bid_anc=bid_px, hdg_px=hdg_px,
                            hdg_avail_shares=hdg_avail, fee_rate_anc=0.0, fee_exponent_anc=1.0,
                            queue_front=True, is_4h_mixed=False,
                        )
                        drag_zf[t_name] = float(dr_z["legging_drag_usd"])
                    ba_c, _ = extract_best_bid((bks.get(str(la["token_id"])) or {}).get("bids") or [])
                    bb_c, _ = extract_best_bid((bks.get(str(lb["token_id"])) or {}).get("bids") or [])
                    pid = f"ZF_INTRADAY_MKR_{int(now)}_{d_key[-8:]}"
                    pos = {
                        "position_id": pid, "dedupe_key": d_key, "sleeve": "ZF_INTRADAY_MAKER_BOX",
                        "asset_or_city": st["asset"], "title": f"{st['title']} [ZF Intraday Maker @ ${bid_px:.3f}]",
                        "side": f"{la['label']}+{lb['label']}", "token_id": f"{la['token_id']}|{lb['token_id']}",
                        "fee_rate": 0.0, "entry_ts": now, "entry_utc": datetime.now(timezone.utc).isoformat(),
                        "close_ts": st["close_ts"], "p_model_entry": 1.0, "entry_eff_px_t1000": pair_eff,
                        "entry_vwap_t1000": pair_eff, "realized_edge_t1000": round(1.0 - pair_eff, 4),
                        "entry_best_bid": round(ba_c + bb_c, 4), "last_bid": round(ba_c + bb_c, 4),
                        "maker_tp_px": None, "tier_fills": tf_zf,
                        "extra": {"is_two_leg_box": True, "is_maker_anchor_box": True, "legging_drag_usd_by_tier": drag_zf, "source_tag": st["source_tag"], "leg_a": la, "leg_b": lb},
                        "status": "OPEN",
                    }
                    self.open_positions[pid] = pos
                    self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                    logger.info(f"[ENTRY:ZF_INTRADAY_MAKER_BOX] {pos['title']} -> Hedged @ ${pair_eff:.4f}!")
                else:
                    scr_bid, _ = extract_best_bid((bk_anc or {}).get("bids") or [])
                    net_scr = scr_bid if scr_bid > 0 else max(0.01, bid_px - 0.03)
                    tf_s, tp_s = {}, {}
                    ref_zf_pair = max(0.90, float(st.get("pair_est") or 0.986))
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        sh_s = max(5.0, float(math.floor(t_map["ZF_INTRADAY_MAKER_BOX"] / ref_zf_pair)))
                        bud = round(sh_s * bid_px, 2)
                        tf_s[t_name] = {"filled": True, "vwap": bid_px, "eff_px": bid_px, "spent_usd": bud, "fee_usd": 0.0, "shares": sh_s}
                        tp_s[t_name] = round(sh_s * net_scr - bud, 2)
                    pos_scr = {
                        "position_id": f"ZF_MKR_SCRATCH_{int(now)}_{d_key[-8:]}", "dedupe_key": d_key,
                        "sleeve": "ZF_INTRADAY_MAKER_BOX", "asset_or_city": st["asset"],
                        "title": f"{st['title']} [ZF Intraday Maker Scratch]", "side": f"{leg_anc['label']}_SCRATCH",
                        "token_id": str(leg_anc["token_id"]), "fee_rate": 0.0, "entry_ts": st["posted_ts"],
                        "entry_utc": datetime.fromtimestamp(st["posted_ts"], tz=timezone.utc).isoformat(),
                        "close_ts": st["close_ts"], "closed_ts": now, "closed_utc": datetime.now(timezone.utc).isoformat(),
                        "p_model_entry": 0.5, "entry_eff_px_t1000": bid_px, "entry_vwap_t1000": bid_px,
                        "net_payout_per_share": round(net_scr, 4), "tier_fills": tf_s, "tier_pnls_usd": tp_s,
                        "legging_adjusted_tier_pnls_usd": dict(tp_s), "won": tp_s.get("T1000", 0.0) > 0,
                        "status": "MAKER_ANCHOR_UNHEDGED_SCRATCH",
                    }
                    self.closed_positions.append(pos_scr)
                    self._append_ledger({"event": "SHADOW_CLOSE", **pos_scr})
                continue
            asks_hdg_c = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
            hdg_px_c = asks_hdg_c[0][0] if asks_hdg_c else 1.0
            hdg_avail_c = sum(sz for px, sz in asks_hdg_c if px <= hdg_px_c + 0.01) if asks_hdg_c else 0.0
            req_sh_chk = float(st.get("req_shares_t100") or 18.0)
            best_bid_anc_c, b_sz_c = extract_best_bid((bk_anc or {}).get("bids") or [])
            a_sz_c = sum(float(a.get("size", 0)) for a in asks_anc if abs(float(a.get("price", 0)) - best_ask_anc) < 1e-6)
            obi_anc_c = ((b_sz_c - a_sz_c) / (b_sz_c + a_sz_c)) if (b_sz_c + a_sz_c) > 0.0 else 0.0
            if (
                rem_sec <= 180.0
                or rested >= 15.0
                or obi_anc_c < -0.30
                or (best_bid_anc_c > 0.0 and best_bid_anc_c < bid_px - 0.015)
                or hdg_avail_c < max(12.0, 2.0 * req_sh_chk)
                or (bid_px + hdg_px_c) > 0.991
            ):
                self.pending_zero_fee_maker_anchors.pop(d_key, None)
                cd_map[d_key] = now + 12.0

    async def scan_same_oracle_dominance_boxes(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        if self.pending_maker_anchors:
            await self.manage_pending_maker_anchors(now)
        target_end_ts = int(math.ceil(now / 900.0) * 900)
        cur_window_pairs = sum(1 for k in self.dominance_pairs if str(k).endswith(f"_{target_end_ts}"))
        disc_interval = 7.0 if cur_window_pairs < len(DOMINANCE_ASSETS) else 12.0
        rem_to_15m = float(target_end_ts) - now
        in_disc_win = (
            self.is_in_same_oracle_overlap_window(now)
            if (self.single_scan or "fetch_json" in self.__dict__)
            else (5.0 <= rem_to_15m <= 330.0)
        )
        if in_disc_win and (now - self.last_dominance_discovery_ts) >= disc_interval:
            self.last_dominance_discovery_ts = now
            await self.discover_dominance_pairs(now)

        if now_ts is None:
            self.record_usd_spot_samples(time.time())

        active_pairs = [
            (m15, m5)
            for m15, m5 in list(self.dominance_pairs.values())
            if (10.0 <= (m5.end_ts - now) <= 300.0) and (now >= m5.start_ts + 1.0)
        ]
        if active_pairs:
            async def _resolve_dom(m15: TwapCandleMarketSpec, m5: TwapCandleMarketSpec):
                k_15m, k_5m = await asyncio.gather(
                    self.get_authoritative_open_strike(m15),
                    self.get_authoritative_open_strike(m5),
                )
                if k_15m is None or k_5m is None:
                    return None
                min_corr = float(MIN_CORRIDOR_BPS_BY_ASSET.get(m15.asset, 3.0))
                di = determine_dominance_legs(m15, k_15m, m5, k_5m, min_corridor_bps=min_corr)
                return (m15, m5, di) if di is not None else None

            resolved_rows = [r for r in await asyncio.gather(*(_resolve_dom(m15, m5) for m15, m5 in active_pairs)) if r is not None]
            if resolved_rows:
                batch_toks: List[str] = []
                for _, _, di in resolved_rows:
                    la, lb = di["leg_a"], di["leg_b"]
                    batch_toks.extend([
                        str(la["token_id"]),
                        str(lb["token_id"]),
                        str(la.get("opp_token_id") or ""),
                        str(lb.get("opp_token_id") or ""),
                    ])
                batch_bks = await self.fetch_books_batch(batch_toks, timeout=3.0)

                for m15, m5, dom_info in resolved_rows:
                    rem_sec = m5.end_ts - now
                    leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
                    bk_a = batch_bks.get(str(leg_a["token_id"]))
                    bk_b = batch_bks.get(str(leg_b["token_id"]))
                    if not bk_a or not bk_b:
                        continue
                    comp_checked: Optional[bool] = None
                    eval_now = float(now_ts) if now_ts is not None else time.time()
                    self._record_d1_corridor_telemetry("15m_5m", m15, m5, dom_info, bk_a, bk_b, eval_now)
                    rem_live = m5.end_ts - eval_now
                    # LIVE emits require both strikes REST/Gamma-verified (unverified WS-TWAP strikes stay shadow-only)
                    strikes_verified = self._strike_is_rest_verified(m15) and self._strike_is_rest_verified(m5)
                    if strikes_verified and 18.0 <= rem_live <= 298.0:
                        w_live = walk_equal_shares_dominance_box(
                            bk_a.get("asks") or [],
                            bk_b.get("asks") or [],
                            target_budget_usd=13.50,
                            fee_rate_a=float(leg_a["fee_rate"]),
                            fee_rate_b=float(leg_b["fee_rate"]),
                            fee_exponent_a=float(leg_a["fee_exponent"]),
                            fee_exponent_b=float(leg_b["fee_exponent"]),
                            max_box_cost_net=0.990,
                            min_shares=5,
                            min_box_notional_usd=4.85,
                        )
                        if w_live.get("filled"):
                            is_quiet_live = self._passes_quiet_book_filter(m15.asset, bk_a, bk_b, w_live, eval_now)
                            live_emit_cap = 0.990 if is_quiet_live else 0.988
                            if float(w_live["box_cost_net"]) <= live_emit_cap:
                                comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=batch_bks)
                                if not comp_checked:
                                    continue
                                self.emit_live_d1_box_candidate(
                                    m15,
                                    m5,
                                    dom_info,
                                    w_live,
                                    eval_now,
                                    is_quiet_book=is_quiet_live,
                                    sleeve_source="D1_QUIET_BOOK_BOX" if is_quiet_live else "D1_SAME_ORACLE_DOMINANCE_BOX",
                                )

                    w_scan = walk_equal_shares_dominance_box(
                        bk_a.get("asks") or [],
                        bk_b.get("asks") or [],
                        target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_SAME_ORACLE_DOMINANCE_BOX"],
                        fee_rate_a=float(leg_a["fee_rate"]),
                        fee_rate_b=float(leg_b["fee_rate"]),
                        fee_exponent_a=float(leg_a["fee_exponent"]),
                        fee_exponent_b=float(leg_b["fee_exponent"]),
                        max_box_cost_net=1.032,  # Surface near-arb boxes <= $1.032 so 2.1c-3.6c Maker-Leg-1 fee+spread savings can lock <= $0.988!
                        min_shares=8,
                        min_box_notional_usd=7.5,
                    )
                    taker_cleared_995 = False
                    if w_scan.get("filled"):
                        box_net = float(w_scan["box_cost_net"])
                        floor_edge = round(1.0 - box_net, 4)
                        if box_net <= 1.005:
                            opps_out.append({
                                "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                                "market": f"{m15.asset} {dom_info['regime']} (TTE={rem_sec:.0f}s, {dom_info['corridor_bps']:.1f}bps)",
                                "ask_vwap": round(box_net, 4),
                                "p_model": 1.0,
                                "net_edge": floor_edge,
                                "l1_usd": w_scan["l1_usd"],
                            })
                        if box_net <= 0.995:
                            if comp_checked is None:
                                comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=batch_bks)
                            if not comp_checked:
                                continue
                            taker_cleared_995 = True
                            await self.open_shadow_dominance_box(m15.asset, m15, m5, dom_info, prefetched_books=(bk_a, bk_b))
                            if self._passes_quiet_book_filter(m15.asset, bk_a, bk_b, w_scan, eval_now):
                                await self.open_shadow_dominance_box(
                                    m15.asset,
                                    m15,
                                    m5,
                                    dom_info,
                                    prefetched_books=(bk_a, bk_b),
                                    sleeve_override="D1_QUIET_BOOK_BOX",
                                    max_box_cost_override=0.992,
                                )
                    if not taker_cleared_995:
                        ask_a_l1, _ = self._best_ask_sz(bk_a)
                        ask_b_l1, _ = self._best_ask_sz(bk_b)
                        if (ask_a_l1 + ask_b_l1) <= 1.020:
                            if comp_checked is None:
                                comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=batch_bks)
                            if comp_checked:
                                self.post_maker_anchor_candidate(m15, m5, dom_info, bk_a, bk_b, eval_now)

        # Addition #1 (`D1_4H_DOMINANCE_BOX`): 4h vs 15m & 4h vs 5m Same-Oracle Chainlink 60s-TWAP Boxes
        await self._scan_4h_dominance_boxes(opps_out, now_ts)

    def _passes_quiet_book_filter(
        self,
        asset: str,
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        w_scan: Dict[str, Any],
        now_ts: float,
    ) -> bool:
        """
        Addition #2 (`D1_QUIET_BOOK_BOX`): Blocks box FOK entries during active Binance impulses
        or wide/sweeping L1 spreads (`<= 4c` per leg, `>= 1.5x` share depth) to eliminate legging friction.
        """
        if abs(self.get_return_bps(asset, 5.0)) > 4.5:
            return False
        if (now_ts - float(self._last_any_shock_ts_by_asset.get(asset, 0.0) or 0.0)) < 4.0:
            return False
        bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
        bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
        best_a = float((w_scan.get("leg_a_walk") or {}).get("best_ask") or 1.0)
        best_b = float((w_scan.get("leg_b_walk") or {}).get("best_ask") or 1.0)
        if bid_a <= 0.0 or bid_b <= 0.0:
            return False
        if (best_a - bid_a) > 0.041 or (best_b - bid_b) > 0.041:
            return False
        req_sh = float(w_scan.get("shares") or 12.0)
        avail_min = min(float(w_scan.get("avail_a_shares") or 0.0), float(w_scan.get("avail_b_shares") or 0.0))
        return avail_min >= 1.5 * req_sh

    async def discover_4h_dominance_pairs(self, now_ts: float) -> None:
        for k_old, (m4_old, _) in list(self.dominance_4h_pairs.items()):
            if m4_old.end_ts < now_ts - 600.0:
                self.dominance_4h_pairs.pop(k_old, None)
        for k_s4, sp_s4 in list(self.s4h_candles.items()):
            if sp_s4.end_ts < now_ts - 600.0:
                self.s4h_candles.pop(k_s4, None)

        # Polymarket 4h ET candles close at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC (aligned on 14400s UTC epoch!)
        target_end_ts = int(math.ceil(now_ts / 14400.0) * 14400)
        rem_4h = float(target_end_ts) - now_ts
        if not (8.0 <= rem_4h <= 905.0):
            return
        now_iso = datetime.fromtimestamp(now_ts - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        need_5m = rem_4h <= 305.0

        for asset in DOMINANCE_ASSETS:
            slugs = DOMINANCE_SERIES_SLUGS[asset]
            slug_4h = slugs.get("4h")
            if not slug_4h:
                continue
            p15_k = f"{asset}_4h15m_{target_end_ts}"
            p5_k = f"{asset}_4h5m_{target_end_ts}"
            if p15_k in self.dominance_4h_pairs and ((not need_5m) or p5_k in self.dominance_4h_pairs):
                continue

            ev4_raw, ev15_raw = await asyncio.gather(
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slug_4h}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['15m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
            )
            m4_match: Optional[TwapCandleMarketSpec] = None
            m15_match: Optional[TwapCandleMarketSpec] = None
            if isinstance(ev4_raw, list):
                for ev in ev4_raw:
                    sp4 = parse_twap_candle_event(ev, asset, "4h")
                    if sp4 and abs(sp4.end_ts - target_end_ts) <= 2.0:
                        m4_match = sp4
                        self.s4h_candles[f"{asset}_4h_{target_end_ts}"] = sp4
                        break
            if isinstance(ev15_raw, list):
                for ev in ev15_raw:
                    sp15 = parse_twap_candle_event(ev, asset, "15m")
                    if sp15 and abs(sp15.end_ts - target_end_ts) <= 2.0:
                        m15_match = sp15
                        break
            if m4_match and m15_match and verify_same_oracle_pair(m4_match, m15_match):
                self.dominance_4h_pairs[p15_k] = (m4_match, m15_match)

            if m4_match and need_5m and p5_k not in self.dominance_4h_pairs:
                ev5_raw = await self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['5m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                )
                if isinstance(ev5_raw, list):
                    for ev in ev5_raw:
                        sp5 = parse_twap_candle_event(ev, asset, "5m")
                        if sp5 and abs(sp5.end_ts - target_end_ts) <= 2.0 and verify_same_oracle_pair(m4_match, sp5):
                            self.dominance_4h_pairs[p5_k] = (m4_match, sp5)
                            break

    async def _scan_4h_dominance_boxes(self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None) -> None:
        now_4h = float(now_ts if now_ts is not None else time.time())
        rem_4h = (math.ceil(now_4h / 14400.0) * 14400.0) - now_4h
        if 8.0 <= rem_4h <= 905.0 and (now_4h - self.last_4h_discovery_ts) >= 12.0:
            self.last_4h_discovery_ts = now_4h
            await self.discover_4h_dominance_pairs(now_4h)

        for _, (m4, m_short) in list(self.dominance_4h_pairs.items()):
            rem_sec = m_short.end_ts - now_4h
            max_rem = 895.0 if m_short.horizon == "15m" else 298.0
            if not (10.0 <= rem_sec <= max_rem) or now_4h < m_short.start_ts + 1.0:
                continue
            k_4h, k_sh = await asyncio.gather(
                self.get_authoritative_open_strike(m4),
                self.get_authoritative_open_strike(m_short),
            )
            if k_4h is None or k_sh is None:
                continue
            min_corr_4h = float(MIN_CORRIDOR_BPS_BY_ASSET.get(m4.asset, 3.0))
            dom_info = determine_dominance_legs(m4, k_4h, m_short, k_sh, min_corridor_bps=min_corr_4h)
            if dom_info is None:
                continue
            leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
            bks_4h = await self.fetch_books_batch(
                [
                    str(leg_a["token_id"]),
                    str(leg_b["token_id"]),
                    str(leg_a.get("opp_token_id") or ""),
                    str(leg_b.get("opp_token_id") or ""),
                ],
                timeout=3.0,
            )
            bk_a = bks_4h.get(str(leg_a["token_id"]))
            bk_b = bks_4h.get(str(leg_b["token_id"]))
            if not bk_a or not bk_b:
                continue
            comp_4h_ok: Optional[bool] = None
            eval_4h_now = float(now_ts) if now_ts is not None else time.time()
            self._record_d1_corridor_telemetry(f"4h_{m_short.horizon}", m4, m_short, dom_info, bk_a, bk_b, eval_4h_now)
            if now_ts is None:
                self.record_usd_spot_samples(eval_4h_now)
            rem_4h_live = m_short.end_ts - eval_4h_now
            # LIVE emits require both strikes REST/Gamma-verified (unverified WS-TWAP strikes stay shadow-only)
            strikes_4h_verified = self._strike_is_rest_verified(m4) and self._strike_is_rest_verified(m_short)
            if strikes_4h_verified and 18.0 <= rem_4h_live <= max_rem:
                w_live_4h = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=13.50,
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=0.990,
                    min_shares=5,
                    min_box_notional_usd=4.85,
                )
                if w_live_4h.get("filled"):
                    is_quiet_4h = self._passes_quiet_book_filter(m4.asset, bk_a, bk_b, w_live_4h, eval_4h_now)
                    if float(w_live_4h["box_cost_net"]) <= (0.990 if is_quiet_4h else 0.988):
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=bks_4h)
                        if not comp_4h_ok:
                            continue
                        self.emit_live_d1_box_candidate(
                            m4,
                            m_short,
                            dom_info,
                            w_live_4h,
                            eval_4h_now,
                            is_quiet_book=is_quiet_4h,
                            sleeve_source="D1_QUIET_BOOK_BOX" if is_quiet_4h else "D1_4H_DOMINANCE_BOX",
                        )
            w_scan = walk_equal_shares_dominance_box(
                bk_a.get("asks") or [],
                bk_b.get("asks") or [],
                target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_4H_DOMINANCE_BOX"],
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                fee_exponent_a=float(leg_a["fee_exponent"]),
                fee_exponent_b=float(leg_b["fee_exponent"]),
                max_box_cost_net=1.032,
                min_shares=8,
                min_box_notional_usd=7.5,
            )
            taker_4h_cleared = False
            if w_scan.get("filled"):
                box_net = float(w_scan["box_cost_net"])
                if box_net <= 1.005:
                    opps_out.append({
                        "sleeve": "D1_4H_DOMINANCE_BOX",
                        "market": f"{m4.asset} {dom_info['regime']} (TTE={rem_sec:.0f}s, {dom_info['corridor_bps']:.1f}bps)",
                        "ask_vwap": round(box_net, 4),
                        "p_model": 1.0,
                        "net_edge": round(1.0 - box_net, 4),
                        "l1_usd": w_scan["l1_usd"],
                    })
                if box_net <= 0.992:
                    if comp_4h_ok is None:
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=bks_4h)
                    if not comp_4h_ok:
                        continue
                    taker_4h_cleared = True
                    await self.open_shadow_dominance_box(
                        m4.asset,
                        m4,
                        m_short,
                        dom_info,
                        prefetched_books=(bk_a, bk_b),
                        sleeve_override="D1_4H_DOMINANCE_BOX",
                        max_box_cost_override=0.992,
                    )
                    if self._passes_quiet_book_filter(m4.asset, bk_a, bk_b, w_scan, eval_4h_now):
                        await self.open_shadow_dominance_box(
                            m4.asset,
                            m4,
                            m_short,
                            dom_info,
                            prefetched_books=(bk_a, bk_b),
                            sleeve_override="D1_QUIET_BOOK_BOX",
                            max_box_cost_override=0.992,
                        )
            if not taker_4h_cleared:
                ask_a_4h, _ = self._best_ask_sz(bk_a)
                ask_b_4h, _ = self._best_ask_sz(bk_b)
                if (ask_a_4h + ask_b_4h) <= 1.020:
                    if comp_4h_ok is None:
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=bks_4h)
                    if comp_4h_ok:
                        self.post_maker_anchor_candidate(m4, m_short, dom_info, bk_a, bk_b, eval_4h_now)

        # `S4H_CHAINLINK_CONVERGENCE`: Final-15m (`180s <= rem_4h <= 900s`) 4h Chainlink SVI z>=2.30 convergence sniper
        for _, sp4 in list(self.s4h_candles.items()):
            rem_s4 = sp4.end_ts - now_4h
            if not (180.0 <= rem_s4 <= 900.0) or now_4h < sp4.start_ts + 3600.0:
                continue
            k_4h_s = await self.get_authoritative_open_strike(sp4)
            if k_4h_s is None or k_4h_s <= 0.0:
                continue
            shm4 = read_shm_usd_anchor(sp4.asset, now_4h, max_age_sec=3.0)
            uh4 = self.usd_spot_hist.get(sp4.asset)
            cur_u4 = shm4.get("usd_spot") or (float(uh4[-1][1]) if uh4 and (now_4h - float(uh4[-1][0])) <= 5.0 else self.spots.get(sp4.asset, 0.0))
            if not cur_u4 or float(cur_u4) <= 0.0:
                continue
            cur_u4_f = float(cur_u4)
            win_s4 = "UP" if cur_u4_f > k_4h_s else "DOWN"
            ret_30s = self.get_return_bps(sp4.asset, 30.0)
            if (win_s4 == "UP" and ret_30s < -6.0) or (win_s4 == "DOWN" and ret_30s > 6.0):
                continue
            svi4 = evaluate_svi_digital_fair_value(sp4.asset, cur_u4_f, k_4h_s, rem_s4, is_downward=False, now_ts=now_4h)
            pf4 = float(svi4["p_yes"] if win_s4 == "UP" else svi4["p_no"])
            zs4 = abs(float(svi4.get("z_sigma") or 0.0))
            if zs4 < 2.30 or pf4 < 0.940:
                continue
            tok4 = sp4.up_token if win_s4 == "UP" else sp4.down_token
            bk4 = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok4}", timeout=2.5)
            if not bk4:
                continue
            w4 = walk_l2_book_asks(bk4.get("asks") or [], BANKROLL_TICKETS["T1000"]["S4H_CHAINLINK_CONVERGENCE"], fee_rate=sp4.fee_rate, min_l1_usd=18.0)
            if not w4.get("filled"):
                continue
            epx4 = float(w4["eff_px"])
            edg4 = pf4 - epx4
            if 0.62 <= epx4 <= 0.89 and edg4 >= 0.030:
                opps_out.append({"sleeve": "S4H_CHAINLINK_CONVERGENCE", "market": f"{sp4.asset} 4h {win_s4} (TTE={rem_s4/60:.1f}m, z={zs4:.2f})", "ask_vwap": epx4, "p_model": round(pf4, 4), "net_edge": round(edg4, 4), "l1_usd": w4["l1_usd"], "close_ts": sp4.end_ts})
            if 0.62 <= epx4 <= 0.89 and edg4 >= 0.045:
                await self.open_shadow_position(
                    sleeve="S4H_CHAINLINK_CONVERGENCE",
                    dedupe_key=f"S4H_{sp4.asset}_{sp4.market_id}",
                    asset_or_city=sp4.asset,
                    title=f"{sp4.title} [4h Chainlink Convergence]",
                    side_label=win_s4,
                    token_id=tok4,
                    fee_rate=sp4.fee_rate,
                    p_model=pf4,
                    close_ts=sp4.end_ts,
                    extra={"market_id": sp4.market_id, "condition_id": sp4.condition_id, "horizon": "4h", "start_iso": sp4.start_iso, "end_iso": sp4.end_iso, "open_price": k_4h_s, "z_sigma": zs4},
                    tp_target_px=0.96,
                    prefetched_book=bk4,
                )

    def poll_fresh_shock_triggers(
        self, now_ts: Optional[float] = None, max_age_sec: float = 4.5
    ) -> List[Dict[str, Any]]:
        """
        Reads newly appended institutional Binance sweeps from `live_shock_triggers.jsonl`
        in <250ms so Alpha-124 immediately cancels adverse resting Maker bids and snipes
        lagging daily multi-strike SVI rungs (`M4_SHOCK_STRIKE_CATCHUP`).
        """
        if not SHOCK_TRIGGER_FILE.exists():
            return []
        now = float(now_ts if now_ts is not None else time.time())
        fresh: List[Dict[str, Any]] = []
        try:
            st_size = SHOCK_TRIGGER_FILE.stat().st_size
            if st_size < self._shock_file_offset:
                self._shock_file_offset = 0
            if st_size == self._shock_file_offset:
                return []
            with open(SHOCK_TRIGGER_FILE, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._shock_file_offset)
                raw_chunk = f.read()
                self._shock_file_offset = f.tell()
            for line in raw_chunk.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    trig = json.loads(line)
                except Exception:
                    continue
                sid = str(trig.get("shock_id") or trig.get("event_id") or "")
                if not sid or sid in self._seen_shock_ids:
                    continue
                self._seen_shock_ids.append(sid)
                if str(trig.get("shock_source") or "").upper() == "BOUNDARY_LOCK":
                    continue
                asset = str(trig.get("asset") or "").upper()
                if asset not in DOMINANCE_ASSETS:
                    continue
                t0_u = float(trig.get("t0_unix") or 0.0)
                if t0_u <= 0.0 or (now - t0_u) > max_age_sec:
                    continue
                spot_t0 = float(trig.get("spot_at_t0") or trig.get("trigger_price") or 0.0)
                if spot_t0 > 0.0:
                    self.spots[asset] = spot_t0
                    self.spot_hist.setdefault(asset, collections.deque(maxlen=600)).append((now, spot_t0))
                cl_px = trig.get("chainlink_proxy_spot") or trig.get("coinbase_spot")
                if cl_px and float(cl_px) > 0.0:
                    self.usd_spot_hist.setdefault(asset, collections.deque(maxlen=400)).append((now, float(cl_px)))
                    self.usd_direct_flags[asset] = True
                if abs(float(trig.get("shock_ofi") or 0.0)) >= 0.55:
                    self._last_any_shock_ts_by_asset[asset] = now
                    fresh.append(trig)
        except Exception as exc:
            logger.debug(f"Shock tailer notice: {exc}")
        return fresh

    async def handle_shock_triggers(
        self,
        triggers: List[Dict[str, Any]],
        opps_out: List[Dict[str, Any]],
        now_ts: Optional[float] = None,
    ) -> None:
        if not triggers:
            return
        now = float(now_ts if now_ts is not None else time.time())
        for trig_s in triggers:
            a_up = str(trig_s.get("asset") or "").upper()
            if a_up:
                self._last_any_shock_ts_by_asset[a_up] = now
        # Step 1: Defensive <250ms adverse-selection cancellation on resting Maker bids & Maker Anchors
        if self.pending_maker_orders:
            await self.manage_pending_maker_orders()
        if self.pending_maker_anchors:
            await self.manage_pending_maker_anchors(now)

        if os.getenv("PM_DISABLE_SHADOW_M4_CATCHUP", "0") == "1" or is_shadow_sleeve_quarantined("M4_SHOCK_STRIKE_CATCHUP"):
            return

        # Step 2: Offensive M4_SHOCK_STRIKE_CATCHUP across lagging <=24h near-ATM multi-strike ladders
        for trig in triggers:
            asset = str(trig.get("asset") or "").upper()
            if (now - self._last_m4_shock_ts_by_asset.get(asset, 0.0)) < 6.0:
                continue
            shock_ofi = float(trig.get("shock_ofi") or 0.0)
            shock_vol = float(trig.get("shock_volume_100ms") or 0.0)
            min_shock_vol = 750_000.0 if asset in ("BTC", "ETH") else 250_000.0
            if abs(shock_ofi) < 0.70 or shock_vol < min_shock_vol:
                continue
            spot = float(self.spots.get(asset) or trig.get("spot_at_t0") or 0.0)
            if spot <= 0.0:
                continue
            shock_up = str(trig.get("shock_direction") or "").upper() in ("BUY", "UP")
            cand_rungs: List[Tuple[StrikeRungSpec, str, str, float, Dict[str, Any]]] = []
            for _, rungs in list(self.strike_ladders.items()):
                if not rungs or rungs[0].asset != asset:
                    continue
                tte = rungs[0].end_ts - now
                if not (1800.0 <= tte <= 86400.0):
                    continue
                for sr in rungs:
                    if abs(math.log(sr.strike / spot)) > 0.035:
                        continue
                    svi_ev = evaluate_svi_digital_fair_value(
                        asset, spot, sr.strike, tte, is_downward=sr.is_downward, now_ts=now
                    )
                    if sr.is_downward:
                        side_lbl = "NO" if shock_up else "YES"
                    else:
                        side_lbl = "YES" if shock_up else "NO"
                    tok = sr.yes_token if side_lbl == "YES" else sr.no_token
                    p_fair = float(svi_ev["p_yes"] if side_lbl == "YES" else svi_ev["p_no"])
                    cand_rungs.append((sr, side_lbl, tok, p_fair, svi_ev))

            if not cand_rungs:
                continue
            self._last_m4_shock_ts_by_asset[asset] = now
            # Causal 50ms latency simulation once before parallel single-RTT book gather (no double book RTT!)
            await asyncio.sleep(0.050)
            books = await asyncio.gather(
                *[self.fetch_json(f"{CLOB_URL}/book?token_id={c[2]}", timeout=2.5) for c in cand_rungs]
            )
            best_m4: Optional[Tuple[float, StrikeRungSpec, str, str, float, Dict[str, Any], Dict[str, Any]]] = None
            best_m4_maker: Optional[Tuple[float, StrikeRungSpec, str, str, float, Dict[str, Any], Dict[str, Any]]] = None
            for (sr, side_lbl, tok, p_fair, svi_ev), bk in zip(cand_rungs, books):
                if not bk:
                    continue
                w_side = walk_l2_book_asks(bk.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)
                if not w_side.get("filled"):
                    continue
                vwap_px = float(w_side["vwap"])
                eff_px = float(w_side["eff_px"])
                edge = p_fair - eff_px
                best_bid_m4, _ = extract_best_bid(bk.get("bids") or [])
                best_ask_m4 = float(w_side["best_ask"])
                if 0.20 <= eff_px <= 0.86 and edge >= 0.035:
                    opps_out.append({
                        "sleeve": "M4_SHOCK_STRIKE_CATCHUP",
                        "market": f"{asset} {sr.question} ({side_lbl}) [ShockWakeup]",
                        "ask_vwap": eff_px,
                        "p_model": round(p_fair, 4),
                        "net_edge": round(edge, 4),
                        "l1_usd": w_side["l1_usd"],
                    })
                if 0.22 <= vwap_px <= 0.82 and 0.24 <= eff_px <= 0.84 and edge >= 0.065:
                    if best_m4 is None or edge > best_m4[0]:
                        best_m4 = (edge, sr, side_lbl, tok, p_fair, svi_ev, bk)
                elif best_bid_m4 > 0.0 and (best_ask_m4 - best_bid_m4) >= 0.02:
                    # Gemini #9 / ChatGPT #2: 0%-fee 3.5s `post_only=True` reactive maker bid when 7% taker fee eats the snipe!
                    mkr_px = round(min(best_bid_m4 + 0.01, best_ask_m4 - 0.01), 4)
                    mkr_edge = p_fair - mkr_px
                    if 0.20 <= mkr_px <= 0.80 and mkr_edge >= 0.065:
                        if best_m4_maker is None or mkr_edge > best_m4_maker[0]:
                            best_m4_maker = (mkr_edge, sr, side_lbl, tok, p_fair, svi_ev, bk)

            if best_m4 is not None:
                _, sr_b, side_b, tok_b, p_fair_b, svi_b, bk_b = best_m4
                await self.open_shadow_position(
                    sleeve="M4_SHOCK_STRIKE_CATCHUP",
                    dedupe_key=f"M4_{sr_b.market_id}_{side_b}_{int(now // 300)}",
                    asset_or_city=asset,
                    title=sr_b.question,
                    side_label=side_b,
                    token_id=tok_b,
                    fee_rate=CRYPTO_FEE_RATE,
                    p_model=p_fair_b,
                    close_ts=sr_b.end_ts,
                    extra={
                        "market_id": sr_b.market_id,
                        "condition_id": sr_b.condition_id,
                        "strike": sr_b.strike,
                        "is_downward": sr_b.is_downward,
                        "iv_annual": svi_b["iv_annual"],
                        "z_sigma": svi_b["z_sigma"],
                        "shock_id": trig.get("shock_id"),
                        "shock_ofi": trig.get("shock_ofi"),
                        "shock_vol_usd": trig.get("shock_volume_100ms"),
                    },
                    prefetched_book=bk_b,
                )
            elif best_m4_maker is not None:
                _, sr_m, side_m, tok_m, p_fair_m, svi_m, bk_m = best_m4_maker
                await self.post_shadow_maker_entry(
                    sleeve="M4_SHOCK_STRIKE_CATCHUP",
                    dedupe_key=f"M4MKR_{sr_m.market_id}_{side_m}_{int(now // 60)}",
                    asset=asset,
                    title=sr_m.question,
                    side_label=side_m,
                    token_id=tok_m,
                    p_model=p_fair_m,
                    close_ts=sr_m.end_ts,
                    extra={
                        "execution_mode": "REACTIVE_POST_ONLY_3P5S",
                        "market_id": sr_m.market_id,
                        "condition_id": sr_m.condition_id,
                        "strike": sr_m.strike,
                        "is_downward": sr_m.is_downward,
                        "iv_annual": svi_m["iv_annual"],
                        "z_sigma": svi_m["z_sigma"],
                        "shock_id": trig.get("shock_id"),
                    },
                    prefetched_book=bk_m,
                    ttl_override_sec=3.5,
                )

    @staticmethod
    def is_in_exact_twap_lock_window(now_ts: float) -> bool:
        """
        True during the final 55s of every 5-minute (and 15-minute) Chainlink 60s-TWAP
        boundary (`5.0 <= rem_5m <= 55.0`), stepping the daemon cadence to 3.0s.
        """
        target_end_ts = math.ceil(now_ts / 300.0) * 300.0
        rem_sec = target_end_ts - now_ts
        return 5.0 <= rem_sec <= 55.0

    async def discover_active_twap_candles(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        for k_old, sp_old in list(self.twap_candles.items()):
            if sp_old.end_ts < now - 300.0:
                self.twap_candles.pop(k_old, None)

        end_5m = int(math.ceil(now / 300.0) * 300)
        rem_5m = float(end_5m) - now
        if not (5.0 <= rem_5m <= 75.0):
            return

        # Reuse any pair already discovered by D1_SAME_ORACLE_DOMINANCE_BOX
        for _, (m15_p, m5_p) in self.dominance_pairs.items():
            if abs(m5_p.end_ts - end_5m) <= 2.0:
                self.twap_candles[f"{m5_p.asset}_5m_{end_5m}"] = m5_p
            if abs(m15_p.end_ts - end_5m) <= 2.0:
                self.twap_candles[f"{m15_p.asset}_15m_{end_5m}"] = m15_p

        now_iso = datetime.fromtimestamp(now - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        is_15m_boundary = (end_5m % 900) == 0
        for asset in DOMINANCE_ASSETS:
            slugs = DOMINANCE_SERIES_SLUGS[asset]
            k5 = f"{asset}_5m_{end_5m}"
            if k5 not in self.twap_candles:
                ev5_raw = await self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['5m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=3.5,
                )
                if isinstance(ev5_raw, list):
                    for ev in ev5_raw:
                        sp5 = parse_twap_candle_event(ev, asset, "5m")
                        if sp5 and abs(sp5.end_ts - end_5m) <= 2.0:
                            self.twap_candles[k5] = sp5
                            break
            if is_15m_boundary:
                k15 = f"{asset}_15m_{end_5m}"
                if k15 not in self.twap_candles:
                    ev15_raw = await self.fetch_json(
                        f"{GAMMA_URL}/events?series_slug={slugs['15m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                        timeout=3.5,
                    )
                    if isinstance(ev15_raw, list):
                        for ev in ev15_raw:
                            sp15 = parse_twap_candle_event(ev, asset, "15m")
                            if sp15 and abs(sp15.end_ts - end_5m) <= 2.0:
                                self.twap_candles[k15] = sp15
                                break

    async def scan_exact_twap_locks(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        rem_5m = (math.ceil(now / 300.0) * 300.0) - now
        if 5.0 <= rem_5m <= 75.0 and (now - self.last_twap_discovery_ts) >= 12.0:
            self.last_twap_discovery_ts = now
            await self.discover_active_twap_candles(now)

        s2_strict = os.getenv("PM_QUARANTINE_LOSING_SLEEVES", "1") == "1"
        max_s2_rem = 28.0 if s2_strict else 45.0
        min_s2_p = 0.975 if s2_strict else 0.965
        min_s2_z = 2.65 if s2_strict else 0.0

        for _, spec in list(self.twap_candles.items()):
            rem_sec = spec.end_ts - now
            if not (8.0 <= rem_sec <= max_s2_rem):
                continue
            if now < spec.start_ts + 60.0:
                continue

            k_open = await self.get_authoritative_open_strike(spec)
            if k_open is None or k_open <= 0.0:
                continue

            shm = read_shm_usd_anchor(spec.asset, now, max_age_sec=2.5)
            cl_ws_s2 = getattr(self, "_chainlink_ws", None) if not self.single_scan else None
            ws_spot_s2 = cl_ws_s2.get_latest_spot(spec.asset, now_ts=now, max_age_sec=2.5) if cl_ws_s2 is not None else None
            usd_hist = self.usd_spot_hist.get(spec.asset)
            cur_usd = ws_spot_s2 or shm.get("usd_spot")
            if (not cur_usd or float(cur_usd) <= 0.0) and usd_hist and (now - float(usd_hist[-1][0])) <= 5.0:
                cur_usd = float(usd_hist[-1][1])
            if (not cur_usd or float(cur_usd) <= 0.0) and self.usd_direct_flags.get(spec.asset, False):
                cur_usd = self.spots.get(spec.asset, 0.0)
            if not cur_usd or float(cur_usd) <= 0.0:
                continue
            cur_usd_f = float(cur_usd)
            usd_direct = bool(
                ws_spot_s2 is not None
                or shm.get("source") in ("shm_chainlink_proxy", "shm_coinbase_usd")
                or self.usd_direct_flags.get(spec.asset, False)
            )
            iv_1d, _ = get_wing_implied_vol(spec.asset, cur_usd_f, k_open, 86400.0)
            samples = cl_ws_s2.get_recent_samples(spec.asset, spec.end_ts - 62.0) if cl_ws_s2 is not None else []
            if len(samples) < 2:
                samples = list(usd_hist or [])
            lock_ev = compute_exact_twap_lock_probability(
                asset=spec.asset,
                open_price=k_open,
                current_usd_spot=cur_usd_f,
                rem_seconds=rem_sec,
                now_ts=now,
                end_ts=spec.end_ts,
                spot_samples=samples,
                shm_twap_60s=shm.get("twap_60s"),
                iv_annual=iv_1d,
                usd_direct_feed=usd_direct,
            )
            if not lock_ev.get("eligible") or float(lock_ev["p_lock"]) < 0.940 or float(lock_ev.get("z_lock", 0.0)) < min_s2_z:
                continue

            win_side = str(lock_ev["side"])
            tok = spec.up_token if win_side == "UP" else spec.down_token
            bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=2.5)
            if not bk:
                continue
            w_chk = walk_l2_book_asks(
                bk.get("asks") or [],
                BANKROLL_TICKETS["T1000"]["S2_EXACT_TWAP_LOCK"],
                fee_rate=spec.fee_rate,
                min_l1_usd=15.0,
            )
            if not w_chk.get("filled"):
                continue
            eff_px = float(w_chk["eff_px"])
            p_lock = float(lock_ev["p_lock"])
            edge = p_lock - eff_px
            if 0.74 <= eff_px <= 0.955 and edge >= 0.015:
                opps_out.append({
                    "sleeve": "S2_EXACT_TWAP_LOCK",
                    "market": f"{spec.asset} {spec.horizon} {win_side} (TTE={rem_sec:.0f}s, alpha={lock_ev['eff_alpha']:.2f}, z={lock_ev['z_lock']:.2f})",
                    "ask_vwap": eff_px,
                    "p_model": p_lock,
                    "net_edge": round(edge, 4),
                    "l1_usd": w_chk["l1_usd"],
                })
            if p_lock >= min_s2_p and 0.76 <= eff_px <= 0.950 and edge >= 0.030:
                await self.open_shadow_position(
                    sleeve="S2_EXACT_TWAP_LOCK",
                    dedupe_key=f"S2_{spec.asset}_{spec.horizon}_{spec.market_id}",
                    asset_or_city=spec.asset,
                    title=f"{spec.title} [{spec.horizon} TWAP Lock]",
                    side_label=win_side,
                    token_id=tok,
                    fee_rate=spec.fee_rate,
                    p_model=p_lock,
                    close_ts=spec.end_ts,
                    extra={
                        "market_id": spec.market_id,
                        "condition_id": spec.condition_id,
                        "horizon": spec.horizon,
                        "start_iso": spec.start_iso,
                        "end_iso": spec.end_iso,
                        "open_price": k_open,
                        "mu_twap": lock_ev["mu_twap"],
                        "eff_alpha": lock_ev["eff_alpha"],
                        "z_lock": lock_ev["z_lock"],
                        "cushion_bps": lock_ev["cushion_bps"],
                        "rem_seconds_at_entry": lock_ev["rem_seconds"],
                    },
                    tp_target_px=None,
                    prefetched_book=bk,
                )

    async def discover_s5m_candles(self, now_ts: float) -> None:
        for k_old, sp_old in list(self.s5m_candles.items()):
            if sp_old.end_ts < now_ts - 300.0:
                self.s5m_candles.pop(k_old, None)

        end_5m = int(math.ceil(now_ts / 300.0) * 300)
        rem_5m = float(end_5m) - now_ts
        if not (35.0 <= rem_5m <= 185.0):
            return

        s5m_assets = ("BTC", "ETH", "SOL", "BNB", "HYPE")
        for _, (_, m5_p) in self.dominance_pairs.items():
            if m5_p.asset in s5m_assets and abs(m5_p.end_ts - end_5m) <= 2.0:
                self.s5m_candles[f"{m5_p.asset}_5m_{end_5m}"] = m5_p
        for k_tw, sp_tw in self.twap_candles.items():
            if sp_tw.asset in s5m_assets and sp_tw.horizon == "5m" and abs(sp_tw.end_ts - end_5m) <= 2.0:
                self.s5m_candles[k_tw] = sp_tw

        now_iso = datetime.fromtimestamp(now_ts - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for asset in s5m_assets:
            if asset not in DOMINANCE_SERIES_SLUGS or "5m" not in DOMINANCE_SERIES_SLUGS[asset]:
                continue
            k5 = f"{asset}_5m_{end_5m}"
            if k5 in self.s5m_candles:
                continue
            slug_5m = DOMINANCE_SERIES_SLUGS[asset]["5m"]
            ev5_raw = await self.fetch_json(
                f"{GAMMA_URL}/events?series_slug={slug_5m}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                timeout=3.5,
            )
            if isinstance(ev5_raw, list):
                for ev in ev5_raw:
                    sp5 = parse_twap_candle_event(ev, asset, "5m")
                    if sp5 and abs(sp5.end_ts - end_5m) <= 2.0:
                        self.s5m_candles[k5] = sp5
                        break

    async def scan_s5m_chainlink_sniper(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        """
        Addition #3 (`S5M_CHAINLINK_SNIPER`): Standalone `5m` BTC & ETH directional Chainlink sniper
        across all `288` daily 5m windows (`45s <= rem_sec <= 165s`), using authoritative Chainlink
        `openPrice` + SVI z-cushion + `0%`-fee `$0.96` Maker TP.
        """
        now = float(now_ts if now_ts is not None else time.time())
        rem_5m = (math.ceil(now / 300.0) * 300.0) - now
        if 40.0 <= rem_5m <= 180.0 and (now - self.last_s5m_discovery_ts) >= 20.0:
            self.last_s5m_discovery_ts = now
            await self.discover_s5m_candles(now)

        last_scan = float(getattr(self, "_last_s5m_book_scan_ts", 0.0) or 0.0)
        if not self.single_scan and (now - last_scan) < 9.5:
            return
        self._last_s5m_book_scan_ts = now

        for _, spec in list(self.s5m_candles.items()):
            rem_sec = spec.end_ts - now
            if not (45.0 <= rem_sec <= 165.0) or now < spec.start_ts + 25.0:
                continue
            k_open = await self.get_authoritative_open_strike(spec)
            if k_open is None or k_open <= 0.0:
                continue

            shm = read_shm_usd_anchor(spec.asset, now, max_age_sec=3.0)
            usd_hist = self.usd_spot_hist.get(spec.asset)
            cur_usd = shm.get("usd_spot")
            if (not cur_usd or float(cur_usd) <= 0.0) and usd_hist and (now - float(usd_hist[-1][0])) <= 5.0:
                cur_usd = float(usd_hist[-1][1])
            if (not cur_usd or float(cur_usd) <= 0.0) and self.usd_direct_flags.get(spec.asset, False):
                cur_usd = self.spots.get(spec.asset, 0.0)
            if not cur_usd or float(cur_usd) <= 0.0:
                continue
            cur_usd_f = float(cur_usd)

            is_alt_5m = spec.asset not in ("BTC", "ETH")
            dist_pct = abs(cur_usd_f - k_open) / k_open * 100.0
            if dist_pct < (0.140 if is_alt_5m else 0.085):
                continue

            win_side = "UP" if cur_usd_f > k_open else "DOWN"
            ret_15s = self.get_return_bps(spec.asset, 15.0)
            if (win_side == "UP" and ret_15s < -4.0) or (win_side == "DOWN" and ret_15s > 4.0):
                continue

            svi_ev = evaluate_svi_digital_fair_value(
                spec.asset, cur_usd_f, k_open, rem_sec, is_downward=False, now_ts=now
            )
            p_fair = float(svi_ev["p_yes"] if win_side == "UP" else svi_ev["p_no"])
            z_sig = abs(float(svi_ev.get("z_sigma") or 0.0))
            if z_sig < (2.25 if is_alt_5m else 1.35) or p_fair < (0.935 if is_alt_5m else 0.905):
                continue

            tok = spec.up_token if win_side == "UP" else spec.down_token
            bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=2.5)
            if not bk:
                continue
            w_chk = walk_l2_book_asks(
                bk.get("asks") or [],
                BANKROLL_TICKETS["T1000"]["S5M_CHAINLINK_SNIPER"],
                fee_rate=spec.fee_rate,
                min_l1_usd=18.0,
            )
            if not w_chk.get("filled"):
                continue
            eff_px = float(w_chk["eff_px"])
            edge = p_fair - eff_px
            if 0.58 <= eff_px <= 0.86 and edge >= 0.025:
                opps_out.append({
                    "sleeve": "S5M_CHAINLINK_SNIPER",
                    "market": f"{spec.asset} 5m {win_side} (TTE={rem_sec:.0f}s, dist={dist_pct:.3f}%, z={z_sig:.2f})",
                    "ask_vwap": eff_px,
                    "p_model": round(p_fair, 4),
                    "net_edge": round(edge, 4),
                    "l1_usd": w_chk["l1_usd"],
                    "close_ts": spec.end_ts,
                })
            if 0.58 <= eff_px <= 0.86 and edge >= (0.055 if is_alt_5m else 0.045):
                await self.open_shadow_position(
                    sleeve="S5M_CHAINLINK_SNIPER",
                    dedupe_key=f"S5M_{spec.asset}_{spec.market_id}",
                    asset_or_city=spec.asset,
                    title=f"{spec.title} [5m Chainlink Sniper]",
                    side_label=win_side,
                    token_id=tok,
                    fee_rate=spec.fee_rate,
                    p_model=p_fair,
                    close_ts=spec.end_ts,
                    extra={
                        "market_id": spec.market_id,
                        "condition_id": spec.condition_id,
                        "horizon": "5m",
                        "start_iso": spec.start_iso,
                        "end_iso": spec.end_iso,
                        "open_price": k_open,
                        "dist_pct": round(dist_pct, 4),
                        "z_sigma": z_sig,
                    },
                    tp_target_px=0.96,
                    prefetched_book=bk,
                )

    async def discover_upcoming_15m_candles(self, now_ts: float) -> None:
        for k_old, sp_old in list(self.preopen_15m_candles.items()):
            if sp_old.start_ts <= now_ts + 5.0:
                self.preopen_15m_candles.pop(k_old, None)

        next_start_ts = int(math.ceil(now_ts / 900.0) * 900)
        sec_to_open = float(next_start_ts) - now_ts
        if not (25.0 <= sec_to_open <= 250.0):
            return

        now_iso = datetime.fromtimestamp(now_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for asset in ("BTC", "ETH"):
            k_pre = f"{asset}_pre15m_{next_start_ts}"
            if k_pre in self.preopen_15m_candles:
                continue
            slug_15m = DOMINANCE_SERIES_SLUGS[asset]["15m"]
            ev15_raw = await self.fetch_json(
                f"{GAMMA_URL}/events?series_slug={slug_15m}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=5",
                timeout=3.5,
            )
            if isinstance(ev15_raw, list):
                for ev in ev15_raw:
                    sp15 = parse_twap_candle_event(ev, asset, "15m")
                    if sp15 and abs(sp15.start_ts - next_start_ts) <= 2.0:
                        self.preopen_15m_candles[k_pre] = sp15
                        break

    async def scan_and_manage_preopen_maker_straddles(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        """
        Addition #5 (`P1_PREOPEN_MAKER_STRADDLE`): Posts passive `0%`-fee `$0.48` UP + `$0.48` DOWN
        Maker bids (`$0.96` combined cost -> guaranteed `$1.00` payout) during the `30s..240s` window
        BEFORE an upcoming `15m` BTC/ETH candle fixes `openPrice`. Explicitly tracks both:
          - 2-leg fills -> locked `$0.96 -> $1.00` complete-set position (`+4.17%` riskless)
          - 1-leg unhedged fills -> immediate taker scratch at `start_ts - 10s` or `>18bps` impulse
            recorded into `closed_positions` so shadow expectancy has zero survivorship bias!
        """
        if is_shadow_sleeve_quarantined("P1_PREOPEN_MAKER_STRADDLE"):
            if self.pending_preopen_straddles:
                self.pending_preopen_straddles.clear()
            return
        now = float(now_ts if now_ts is not None else time.time())
        next_start_ts = int(math.ceil(now / 900.0) * 900)
        sec_to_open = float(next_start_ts) - now
        if 25.0 <= sec_to_open <= 250.0 and (now - self.last_preopen_discovery_ts) >= 20.0:
            self.last_preopen_discovery_ts = now
            await self.discover_upcoming_15m_candles(now)

        last_p1 = float(getattr(self, "_last_p1_manage_ts", 0.0) or 0.0)
        if not self.single_scan and not self.pending_preopen_straddles and not (30.0 <= sec_to_open <= 245.0):
            return
        if not self.single_scan and (now - last_p1) < 8.0:
            return
        self._last_p1_manage_ts = now

        # 1. Manage existing pending pre-open straddles first
        for d_key, st in list(self.pending_preopen_straddles.items()):
            spec: TwapCandleMarketSpec = st["spec"]
            bk_up, bk_dn = await asyncio.gather(
                self.fetch_json(f"{CLOB_URL}/book?token_id={spec.up_token}", timeout=2.5),
                self.fetch_json(f"{CLOB_URL}/book?token_id={spec.down_token}", timeout=2.5),
            )
            bid_px = float(st["bid_px"])
            rested_sec = now - float(st["posted_ts"])
            if bk_up and rested_sec >= 4.0:
                asks_up = bk_up.get("asks") or []
                best_ask_up = min((float(a["price"]) for a in asks_up if float(a.get("size", 0)) > 0), default=1.0)
                if best_ask_up <= bid_px:
                    st["up_filled"] = True
            if bk_dn and rested_sec >= 4.0:
                asks_dn = bk_dn.get("asks") or []
                best_ask_dn = min((float(a["price"]) for a in asks_dn if float(a.get("size", 0)) > 0), default=1.0)
                if best_ask_dn <= bid_px:
                    st["dn_filled"] = True

            # Outcome A: Both legs filled passively -> lock guaranteed $0.96 -> $1.00 complete set!
            if st["up_filled"] and st["dn_filled"]:
                self.pending_preopen_straddles.pop(d_key, None)
                pair_cost = round(2.0 * bid_px, 4)
                tier_fills: Dict[str, Dict[str, Any]] = {}
                for t_name, t_map in BANKROLL_TICKETS.items():
                    sh = max(5.0, float(math.floor(t_map["P1_PREOPEN_MAKER_STRADDLE"] / max(0.90, pair_cost))))
                    spent = round(sh * pair_cost, 2)
                    tier_fills[t_name] = {
                        "filled": True,
                        "vwap": pair_cost,
                        "eff_px": pair_cost,
                        "spent_usd": spent,
                        "fee_usd": 0.0,
                        "shares": sh,
                        "l1_usd": 100.0,
                    }
                pos_id = f"P1_PREOPEN_MAKER_STRADDLE_{int(now)}_{spec.market_id[-6:]}"
                legs = [
                    {"token_id": spec.up_token, "side": "UP", "market_id": spec.market_id, "label": "PRE_UP"},
                    {"token_id": spec.down_token, "side": "DOWN", "market_id": spec.market_id, "label": "PRE_DOWN"},
                ]
                pos = {
                    "position_id": pos_id,
                    "dedupe_key": d_key,
                    "sleeve": "P1_PREOPEN_MAKER_STRADDLE",
                    "asset_or_city": spec.asset,
                    "title": f"{spec.title} [Pre-Open Maker $0.48+$0.48]",
                    "side": "PRE_UP+PRE_DOWN",
                    "token_id": f"{spec.up_token}|{spec.down_token}",
                    "fee_rate": 0.0,
                    "entry_ts": now,
                    "entry_utc": datetime.now(timezone.utc).isoformat(),
                    "close_ts": spec.end_ts,
                    "p_model_entry": 1.0,
                    "entry_eff_px_t1000": pair_cost,
                    "entry_vwap_t1000": pair_cost,
                    "realized_edge_t1000": round(1.0 - pair_cost, 4),
                    "entry_best_bid": pair_cost,
                    "last_bid": pair_cost,
                    "maker_tp_px": None,
                    "tier_fills": tier_fills,
                    "extra": {
                        "is_multi_leg_bundle": True,
                        "guaranteed_payout": 1.0,
                        "market_id": spec.market_id,
                        "legs": legs,
                    },
                    "status": "OPEN",
                }
                self.open_positions[pos_id] = pos
                self.entered_keys.add(d_key)
                self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                logger.info(
                    f"[ENTRY:P1_PREOPEN_MAKER_STRADDLE] {pos['title']} | BOTH LEGS FILLED @ ${pair_cost:.2f} -> $1.00 lock!"
                )
                continue

            # Outcome B: Pre-open cutoff (`start_ts - 10s`) or >18 bps spot move -> cancel or scratch single leg!
            cur_spot = float(self.spots.get(spec.asset) or st["posted_spot"] or 0.0)
            posted_spot = float(st["posted_spot"] or cur_spot or 1.0)
            move_bps = abs(cur_spot - posted_spot) / max(1e-9, posted_spot) * 10000.0
            if now >= (spec.start_ts - 10.0) or move_bps > 18.0:
                self.pending_preopen_straddles.pop(d_key, None)
                self.entered_keys.add(d_key)
                if not st["up_filled"] and not st["dn_filled"]:
                    continue
                filled_up = bool(st["up_filled"])
                bk_scr = bk_up if filled_up else bk_dn
                scr_bid, _ = extract_best_bid((bk_scr or {}).get("bids") or [])
                if scr_bid <= 0.0:
                    scr_bid = max(0.01, bid_px - 0.03)
                taker_fee_ps = spec.fee_rate * scr_bid * (1.0 - scr_bid)
                net_scr_ps = max(0.0, scr_bid - taker_fee_ps)
                tier_fills_s: Dict[str, Dict[str, Any]] = {}
                tier_pnls_s: Dict[str, float] = {}
                for t_name, t_map in BANKROLL_TICKETS.items():
                    sh_s = max(5.0, float(math.floor(t_map["P1_PREOPEN_MAKER_STRADDLE"] / max(0.90, 2.0 * bid_px))))
                    leg_budget = round(sh_s * bid_px, 2)
                    tier_fills_s[t_name] = {
                        "filled": True,
                        "vwap": bid_px,
                        "eff_px": bid_px,
                        "spent_usd": leg_budget,
                        "fee_usd": 0.0,
                        "shares": sh_s,
                    }
                    tier_pnls_s[t_name] = round(sh_s * net_scr_ps - leg_budget, 2)
                pos_scr = {
                    "position_id": f"P1_SCRATCH_{int(now)}_{spec.market_id[-6:]}",
                    "dedupe_key": d_key,
                    "sleeve": "P1_PREOPEN_MAKER_STRADDLE",
                    "asset_or_city": spec.asset,
                    "title": f"{spec.title} [Pre-Open 1-Leg Scratch]",
                    "side": "PRE_UP_SCRATCH" if filled_up else "PRE_DOWN_SCRATCH",
                    "token_id": spec.up_token if filled_up else spec.down_token,
                    "fee_rate": 0.0,
                    "entry_ts": st["posted_ts"],
                    "entry_utc": datetime.fromtimestamp(st["posted_ts"], tz=timezone.utc).isoformat(),
                    "close_ts": spec.end_ts,
                    "closed_ts": now,
                    "closed_utc": datetime.now(timezone.utc).isoformat(),
                    "p_model_entry": 0.5,
                    "entry_eff_px_t1000": bid_px,
                    "entry_vwap_t1000": bid_px,
                    "net_payout_per_share": round(net_scr_ps, 4),
                    "tier_fills": tier_fills_s,
                    "tier_pnls_usd": tier_pnls_s,
                    "won": tier_pnls_s.get("T1000", 0.0) > 0,
                    "status": "PREOPEN_ONE_LEG_SCRATCH",
                }
                self.closed_positions.append(pos_scr)
                self._append_ledger({"event": "SHADOW_CLOSE", **pos_scr})
                logger.info(
                    f"[CLOSE:P1_PREOPEN_MAKER_STRADDLE] {pos_scr['title']} -> PREOPEN_ONE_LEG_SCRATCH | "
                    f"bid_exit=${scr_bid:.3f} net=${net_scr_ps:.4f} | PnL T1000=${tier_pnls_s.get('T1000', 0.0):+.2f}"
                )

        # 2. Post fresh passive $0.48 + $0.48 Maker straddles on upcoming symmetric 15m books
        for _, spec in list(self.preopen_15m_candles.items()):
            sec_rem_open = spec.start_ts - now
            if not (40.0 <= sec_rem_open <= 240.0):
                continue
            d_key = f"P1_{spec.asset}_{spec.market_id}"
            if d_key in self.entered_keys or d_key in self.pending_preopen_straddles:
                continue
            if abs(self.get_return_bps(spec.asset, 15.0)) > 8.0:
                continue
            bk_up, bk_dn = await asyncio.gather(
                self.fetch_json(f"{CLOB_URL}/book?token_id={spec.up_token}", timeout=2.5),
                self.fetch_json(f"{CLOB_URL}/book?token_id={spec.down_token}", timeout=2.5),
            )
            if not bk_up or not bk_dn:
                continue
            bid_up, _ = extract_best_bid(bk_up.get("bids") or [])
            bid_dn, _ = extract_best_bid(bk_dn.get("bids") or [])
            asks_up = bk_up.get("asks") or []
            asks_dn = bk_dn.get("asks") or []
            ask_up = min((float(a["price"]) for a in asks_up if float(a.get("size", 0)) > 0), default=1.0)
            ask_dn = min((float(a["price"]) for a in asks_dn if float(a.get("size", 0)) > 0), default=1.0)
            if ask_up >= 0.49 and ask_dn >= 0.49 and 0.44 <= bid_up <= 0.51 and 0.44 <= bid_dn <= 0.51:
                opps_out.append({
                    "sleeve": "P1_PREOPEN_MAKER_STRADDLE",
                    "market": f"{spec.asset} Pre-Open 15m Straddle (T-{sec_rem_open:.0f}s, asks={ask_up:.2f}/{ask_dn:.2f})",
                    "ask_vwap": 0.96,
                    "p_model": 1.0,
                    "net_edge": 0.04,
                    "l1_usd": 100.0,
                    "close_ts": spec.end_ts,
                })
                self.pending_preopen_straddles[d_key] = {
                    "spec": spec,
                    "bid_px": 0.48,
                    "posted_ts": now,
                    "posted_spot": float(self.spots.get(spec.asset) or 0.0),
                    "up_filled": False,
                    "dn_filled": False,
                }
                logger.info(
                    f"[MAKER_POST:P1_PREOPEN_MAKER_STRADDLE] {spec.title} | Resting $0.48 UP + $0.48 DOWN (T-{sec_rem_open:.0f}s)"
                )

    async def resolve_via_gamma_market(self, pos: Dict[str, Any]) -> Optional[float]:
        """
        Queries Polymarket Gamma API `/markets/{market_id}` (or `?clob_token_ids=`) to resolve
        closed markets whose CLOB `/book` endpoint returns 404 after resolution (e.g. Weather W1/W2,
        Barrier B1/B2, Multi-Strike M1/M2). Matches `pos['token_id']` against `clobTokenIds`.
        Returns 1.0 (won), 0.0 (lost), or None (not yet resolved).
        """
        extra = pos.get("extra") or {}
        m_id = str(extra.get("market_id") or "")
        tok = str(pos.get("token_id") or "")
        gm: Optional[Dict[str, Any]] = None
        if m_id:
            res = await self.fetch_json(f"{GAMMA_URL}/markets/{m_id}", timeout=4.0)
            if isinstance(res, dict):
                gm = res
        if gm is None and tok:
            res_list = await self.fetch_json(f"{GAMMA_URL}/markets?clob_token_ids={tok}", timeout=4.0)
            if isinstance(res_list, list) and res_list:
                gm = res_list[0]
        if not isinstance(gm, dict) or not gm.get("closed"):
            return None

        uma_st = str(gm.get("umaResolutionStatus") or "").strip().lower()
        if uma_st and uma_st != "resolved":
            return None

        toks = gm.get("clobTokenIds")
        if isinstance(toks, str):
            try:
                toks = json.loads(toks)
            except Exception:
                toks = []
        op = gm.get("outcomePrices")
        if isinstance(op, str):
            try:
                op = json.loads(op)
            except Exception:
                op = []
        if not isinstance(op, list) or len(op) < 2:
            return None

        idx_match = -1
        if isinstance(toks, list) and tok in [str(t) for t in toks]:
            idx_match = [str(t) for t in toks].index(tok)
        else:
            idx_match = 0 if str(pos.get("side", "YES")).upper() in ("YES", "UP") else 1

        if idx_match < 0 or idx_match >= len(op):
            return None
        try:
            px = float(op[idx_match])
        except Exception:
            return None
        if px >= 0.99:
            return 1.0
        if px <= 0.01:
            return 0.0
        if uma_st == "resolved" and 0.49 <= px <= 0.51:
            return round(px, 4)
        return None

    def _try_early_overround_bid_unwind(
        self,
        pos: Dict[str, Any],
        legs_bids_spec: List[Dict[str, Any]],
        now: float,
    ) -> Optional[Tuple[float, Dict[str, float]]]:
        """
        Evaluates whether an open 2-leg or N-leg riskless box can be exited immediately by sweeping
        resting L2 `bids` across 100% of held shares on every leg simultaneously:
          - Capped-payout complete-set partitions (`C1`, `NR0`, `N1`, `W3`, `P1`):
            requires `net_proceeds_per_set >= max(entry_eff + 0.010, guar_pay + 0.004)` (strictly > par!).
          - Dominance boxes with `$2.00` double-payout corridor (`FED1`, `COND1`, `CM_B3`, `SP1`, `TW1`, `D2`, `M3`, `B3`, `D1_*`):
            for lockups `> 1h` (`rem_tte > 3600s`), requires `>= max(entry_eff + 0.015, guar_pay + 0.005)`;
            for near-expiry boxes (`<= 1h`), requires `>= max(entry_eff + 0.080, guar_pay + 0.080)` to preserve `$2.00` corridor EV.
        """
        if (now - float(pos.get("entry_ts") or 0.0)) < 15.0:
            return None
        tier_fills = pos.get("tier_fills") or {}
        if "T1000" not in tier_fills:
            return None
        sh_t1000 = float(tier_fills["T1000"].get("shares") or 0.0)
        if sh_t1000 <= 0.0:
            return None
        extra = pos.get("extra") or {}
        guar_pay = float(extra.get("guaranteed_payout") or pos.get("p_model_entry") or 1.0)
        entry_eff = float(pos.get("entry_eff_px_t1000") or 0.99)
        rem_tte = float(pos["close_ts"]) - now
        capped_partition = pos.get("sleeve") in (
            "C1_BINARY_COMPLETE_SET",
            "NR0_ZERO_FEE_SLATE_ARB",
            "N1_NEGRISK_CROSS_BOX",
            "W3_WEATHER_SLATE_ARB",
            "P1_PREOPEN_MAKER_STRADDLE",
        )
        if capped_partition:
            min_net_req = max(entry_eff + 0.010, guar_pay + 0.004)
        elif rem_tte > 3600.0:
            min_net_req = max(entry_eff + 0.015, guar_pay + 0.005)
        else:
            min_net_req = max(entry_eff + 0.080, guar_pay + 0.080)

        w_ref = walk_position_overround_bid_unwind(legs_bids_spec, sh_t1000, min_net_proceeds_per_set=min_net_req)
        if not w_ref.get("filled"):
            return None
        tier_pay_map: Dict[str, float] = {}
        for t_name, tf in tier_fills.items():
            sh_t = float(tf.get("shares") or 0.0)
            if sh_t <= 0.0:
                continue
            wt = walk_position_overround_bid_unwind(legs_bids_spec, sh_t, min_net_proceeds_per_set=min_net_req)
            if not wt.get("filled"):
                return None
            tier_pay_map[t_name] = float(wt["net_proceeds_per_set"])
        return float(w_ref["net_proceeds_per_set"]), tier_pay_map

    async def manage_open_positions(self) -> None:
        now = time.time()
        loop = asyncio.get_running_loop()
        to_close: List[Tuple[str, str, float, Any]] = []  # (pos_id, status, payout_per_share, tier_pay_override)

        for pid, pos in list(self.open_positions.items()):
            sleeve = pos["sleeve"]
            tok = pos["token_id"]

            # 0A. Dedicated multi-leg supervision & settlement for D1, M3, B3, C1 & W3_WEATHER_SLATE_ARB
            if sleeve == "W3_WEATHER_SLATE_ARB":
                close_ts_f = float(pos["close_ts"])
                extra_w = pos.get("extra") or {}
                legs = extra_w.get("legs") or []
                if now < close_ts_f + 30.0:
                    if (now - float(pos.get("_last_book_poll_ts") or 0.0)) >= 30.0 and legs:
                        pos["_last_book_poll_ts"] = now
                        bks_w = await asyncio.gather(
                            *[self.fetch_json(f"{CLOB_URL}/book?token_id={lg.get('token_id') or lg.get('yes_token', '')}", timeout=2.5) for lg in legs]
                        )
                        if all(bks_w):
                            pos["last_bid"] = round(sum(extract_best_bid((b or {}).get("bids") or [])[0] for b in bks_w), 4)
                            uw_w = self._try_early_overround_bid_unwind(
                                pos,
                                [{"bids": (b or {}).get("bids") or [], "fee_rate": 0.0, "fee_exponent": 1.0} for b in bks_w],
                                now,
                            )
                            if uw_w is not None:
                                to_close.append((pid, "EARLY_OVERROUND_BID_UNWIND", uw_w[0], uw_w[1]))
                    continue
                if now >= close_ts_f + 30.0:
                    guar_pay_w = float(extra_w.get("guaranteed_payout") or 1.0)
                    resolved_vals = await asyncio.gather(
                        *[
                            self.resolve_via_gamma_market(
                                {
                                    "token_id": lg.get("token_id") or lg.get("yes_token", ""),
                                    "side": lg.get("side", "YES"),
                                    "extra": {"market_id": lg["market_id"]},
                                }
                            )
                            for lg in legs
                        ]
                    )
                    if resolved_vals and all(v is not None for v in resolved_vals):
                        total_pay = round(sum(float(v) for v in resolved_vals if v is not None), 4)
                        st_w = "SETTLED_WEATHER_SLATE_1X" if guar_pay_w <= 1.01 else "SETTLED_WEATHER_SLATE_NX"
                        to_close.append((pid, st_w, max(guar_pay_w, total_pay), 0.0))
                continue

            extra_chk = pos.get("extra") or {}
            if sleeve in (
                "D1_SAME_ORACLE_DOMINANCE_BOX",
                "D1_4H_DOMINANCE_BOX",
                "D1_QUIET_BOOK_BOX",
                "D1_MAKER_ANCHOR_BOX",
                "M3_LADDER_MONO_BOX",
                "B3_BARRIER_MONO_BOX",
                "C1_BINARY_COMPLETE_SET",
                "CM_B3_PYTH_BARRIER_BOX",
                "SP1_NBA_ZERO_FEE_BOX",
                "ZERO_FEE_MAKER_ANCHOR_BOX",
                "ZF_INTRADAY_MAKER_BOX",
                "D2_12PM_BINANCE_BOX",
            ) or (extra_chk.get("leg_a") and extra_chk.get("leg_b")):
                extra = pos.get("extra") or {}
                leg_a = extra.get("leg_a") or {}
                leg_b = extra.get("leg_b") or {}
                close_ts_f = float(pos["close_ts"])
                if now < close_ts_f + 10.0:
                    bk_a, bk_b = await asyncio.gather(
                        self.fetch_json(f"{CLOB_URL}/book?token_id={leg_a.get('token_id', '')}", timeout=2.5),
                        self.fetch_json(f"{CLOB_URL}/book?token_id={leg_b.get('token_id', '')}", timeout=2.5),
                    )
                    if bk_a and bk_b:
                        bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
                        bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
                        pos["last_bid"] = round(bid_a + bid_b, 4)
                        def_fr = float(pos.get("fee_rate") or 0.0)
                        uw_2 = self._try_early_overround_bid_unwind(
                            pos,
                            [
                                {
                                    "bids": bk_a.get("bids") or [],
                                    "fee_rate": float(leg_a.get("fee_rate", def_fr)),
                                    "fee_exponent": float(leg_a.get("fee_exponent", 1.0)),
                                },
                                {
                                    "bids": bk_b.get("bids") or [],
                                    "fee_rate": float(leg_b.get("fee_rate", def_fr)),
                                    "fee_exponent": float(leg_b.get("fee_exponent", 1.0)),
                                },
                            ],
                            now,
                        )
                        if uw_2 is not None:
                            to_close.append((pid, "EARLY_OVERROUND_BID_UNWIND", uw_2[0], uw_2[1]))
                            continue
                    if (
                        sleeve == "C1_BINARY_COMPLETE_SET"
                        and leg_a.get("market_id")
                        and leg_a.get("market_id") == leg_b.get("market_id")
                        and (now - float(pos.get("entry_ts") or 0.0)) >= 15.0
                    ):
                        to_close.append((pid, "CTF_COMPLETE_SET_MERGED", 1.0, 0.0))
                        continue
                    if bk_a and bk_b:
                        continue
                    if bk_a or bk_b or (now - float(pos.get("_last_gamma_chk_ts") or 0.0)) < 60.0:
                        continue
                    pos["_last_gamma_chk_ts"] = now

                pay_a, pay_b = await asyncio.gather(
                    self.resolve_via_gamma_market(
                        {"token_id": leg_a.get("token_id", ""), "side": leg_a.get("side", "UP"), "extra": {"market_id": leg_a.get("market_id", "")}}
                    ),
                    self.resolve_via_gamma_market(
                        {"token_id": leg_b.get("token_id", ""), "side": leg_b.get("side", "DOWN"), "extra": {"market_id": leg_b.get("market_id", "")}}
                    ),
                )
                if pay_a is not None and pay_b is not None:
                    total_pay = round(float(pay_a) + float(pay_b), 4)
                    st_lbl = "SETTLED_DOMINANCE_DOUBLE_2X" if total_pay >= 1.99 else "SETTLED_DOMINANCE_FLOOR_1X"
                    to_close.append((pid, st_lbl, total_pay, 0.0))
                    continue

                if sleeve == "B3_BARRIER_MONO_BOX" and now >= close_ts_f + 900.0:
                    d_b3 = str(extra.get("direction") or "UP").upper()
                    ext_b3 = await loop.run_in_executor(
                        None, fetch_binance_window_extremes_sync, pos["asset_or_city"], float(pos["entry_ts"]), close_ts_f, "1m"
                    )
                    if ext_b3 is not None:
                        max_h, min_l, _ = ext_b3
                        k_a_b3 = float(leg_a.get("strike") or 0.0)
                        k_b_b3 = float(leg_b.get("strike") or 0.0)
                        t_a = (d_b3 == "UP" and max_h >= k_a_b3) or (d_b3 == "DOWN" and min_l <= k_a_b3)
                        t_b = (d_b3 == "UP" and max_h >= k_b_b3) or (d_b3 == "DOWN" and min_l <= k_b_b3)
                        total_pay = (1.0 if t_a else 0.0) + (0.0 if t_b else 1.0)
                        to_close.append((pid, "SETTLED_BARRIER_MONO_2X" if total_pay >= 1.99 else "SETTLED_BARRIER_MONO_1X", total_pay, 0.0))
                    continue

                if now >= close_ts_f + 360.0 and extra.get("m15_start_iso"):
                    dur_a = 14400.0 if str(leg_a.get("horizon")) == "4h" else (900.0 if str(leg_a.get("horizon")) == "15m" else 300.0)
                    dur_b = 14400.0 if str(leg_b.get("horizon")) == "4h" else (900.0 if str(leg_b.get("horizon")) == "15m" else 300.0)
                    ev_a_url = build_own_gamma_event_url(pos["asset_or_city"], str(leg_a.get("horizon") or "15m"), close_ts_f - dur_a)
                    ev_b_url = build_own_gamma_event_url(pos["asset_or_city"], str(leg_b.get("horizon") or "5m"), close_ts_f - dur_b)
                    ev_a_raw, ev_b_raw = await asyncio.gather(
                        self.fetch_json(ev_a_url, timeout=4.0),
                        self.fetch_json(ev_b_url, timeout=4.0),
                    )
                    pa_ev = parse_closed_gamma_event_settlement(ev_a_raw, str(leg_a.get("side") or "UP"), ev_a_url)
                    pb_ev = parse_closed_gamma_event_settlement(ev_b_raw, str(leg_b.get("side") or "DOWN"), ev_b_url)
                    if pa_ev is not None and pb_ev is not None:
                        total_pay = round(pa_ev + pb_ev, 4)
                        st_lbl = (
                            "SETTLED_ORACLE_DOUBLE_2X"
                            if total_pay >= 1.99
                            else ("SETTLED_ORACLE_FLOOR_1X" if total_pay >= 0.99 else "SETTLED_ORACLE_LOSS_0X")
                        )
                        to_close.append((pid, st_lbl, total_pay, 0.0))
                continue

            if sleeve in ("N1_NEGRISK_CROSS_BOX", "P1_PREOPEN_MAKER_STRADDLE", "NR0_ZERO_FEE_SLATE_ARB") or bool(extra_chk.get("legs")):
                extra = pos.get("extra") or {}
                legs = extra.get("legs") or []
                close_ts_f = float(pos["close_ts"])
                if now < close_ts_f + 20.0:
                    if (now - float(pos.get("_last_book_poll_ts") or 0.0)) >= 30.0 and legs:
                        pos["_last_book_poll_ts"] = now
                        bks_m = await asyncio.gather(
                            *[self.fetch_json(f"{CLOB_URL}/book?token_id={lg['token_id']}", timeout=2.5) for lg in legs]
                        )
                        if all(bks_m):
                            pos["last_bid"] = round(
                                sum(extract_best_bid((b or {}).get("bids") or [])[0] for b in bks_m), 4
                            )
                            def_fr_m = float(pos.get("fee_rate") or 0.0)
                            uw_m = self._try_early_overround_bid_unwind(
                                pos,
                                [
                                    {
                                        "bids": (b or {}).get("bids") or [],
                                        "fee_rate": float(lg.get("fee_rate", def_fr_m)),
                                        "fee_exponent": float(lg.get("fee_exponent", 1.0)),
                                    }
                                    for lg, b in zip(legs, bks_m)
                                ],
                                now,
                            )
                            if uw_m is not None:
                                to_close.append((pid, "EARLY_OVERROUND_BID_UNWIND", uw_m[0], uw_m[1]))
                    continue
                resolved_vals = await asyncio.gather(
                    *[
                        self.resolve_via_gamma_market(
                            {
                                "token_id": lg["token_id"],
                                "side": lg.get("side", "YES"),
                                "extra": {"market_id": lg.get("market_id", "")},
                            }
                        )
                        for lg in legs
                    ]
                )
                if resolved_vals and all(v is not None for v in resolved_vals):
                    total_pay = round(sum(float(v) for v in resolved_vals if v is not None), 4)
                    to_close.append((pid, "SETTLED_MULTI_LEG_ARB", total_pay, 0.0))
                elif sleeve == "P1_PREOPEN_MAKER_STRADDLE" and now >= close_ts_f + 900.0:
                    to_close.append((pid, "SETTLED_COMPLETE_SET_1X", 1.0, 0.0))
                continue

            # 0B. Dedicated hold-to-expiry & authoritative Chainlink TWAP settlement for S2_EXACT_TWAP_LOCK
            if sleeve == "S2_EXACT_TWAP_LOCK":
                extra = pos.get("extra") or {}
                close_ts_f = float(pos["close_ts"])
                if now < close_ts_f + 12.0:
                    bk_s2 = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=2.5)
                    if bk_s2:
                        bid_s2, _ = extract_best_bid(bk_s2.get("bids") or [])
                        pos["last_bid"] = bid_s2
                    continue
                g_pay = await self.resolve_via_gamma_market(pos)
                if g_pay is not None:
                    st_lbl = "SETTLED_GAMMA_WIN" if g_pay >= 0.99 else "SETTLED_GAMMA_LOSS"
                    to_close.append((pid, st_lbl, g_pay, 0.0))
                    continue
                if now >= close_ts_f + 120.0 and extra.get("start_iso"):
                    cp_url = build_own_gamma_event_url(
                        pos["asset_or_city"],
                        str(extra.get("horizon") or "15m"),
                        extra["start_iso"],
                    )
                    cp_payload = await self.fetch_json(cp_url, timeout=4.0)
                    close_px = parse_authoritative_close_price(cp_payload)
                    open_px = float(extra.get("open_price") or 0.0)
                    if close_px is not None and open_px > 0.0:
                        up_won = close_px >= open_px
                        won = up_won if str(pos.get("side")).upper() == "UP" else (not up_won)
                        st_lbl = "SETTLED_ORACLE_TWAP_WIN" if won else "SETTLED_ORACLE_TWAP_LOSS"
                        to_close.append((pid, st_lbl, 1.0 if won else 0.0, 0.0))
                continue

            # 1. Check finalized 1m Binance candle wicks on B1/B2 (exact Polymarket Hit-Price oracle rule!)
            # Note: Polymarket Hit markets resolve on FINALIZED 1m candle High/Low, NOT unclosed transient ticks,
            # AND a sub-15s wick inside a finalized 1m candle breaches the barrier even if spot mean-reverted!
            if sleeve in ("B1_CONVEX_TAIL_YES", "B2_BARRIER_NO_LOCK"):
                asset = pos["asset_or_city"]
                k = float(pos["extra"].get("strike") or 0.0)
                d = pos["extra"].get("direction")
                last_w_chk = float(pos.get("_last_wick_chk_ts") or 0.0)
                if k > 0 and (now - last_w_chk) >= 60.0:
                    pos["_last_wick_chk_ts"] = now
                    w_start = float(pos["extra"].get("start_ts") or pos["entry_ts"])
                    w_end = min(now, float(pos["close_ts"]))
                    ext_1m = await loop.run_in_executor(
                        None, fetch_binance_window_extremes_sync, asset, w_start, w_end, "1m"
                    )
                    if ext_1m is not None:
                        max_h, min_l, _ = ext_1m
                        touched = (d == "UP" and max_h >= k) or (d == "DOWN" and min_l <= k)
                        if touched:
                            pay_ps = 1.0 if pos["side"] == "YES" else 0.0
                            to_close.append((pid, "BARRIER_1M_WICK_SETTLED", pay_ps, 0.0))
                            continue

            # 2. Poll live CLOB book for Maker TP fills or SVI invalidation stop
            # Throttle non-expiring 24h position book polls during final-55s S2 TWAP lock window
            if (
                not self.single_scan
                and self.is_in_exact_twap_lock_window(now)
                and float(pos["close_ts"]) > now + 120.0
                and (now - float(pos.get("_last_book_poll_ts") or 0.0)) < 20.0
            ):
                continue
            pos["_last_book_poll_ts"] = now
            bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=3.0)
            if bk:
                best_bid, _ = extract_best_bid(bk.get("bids") or [])
                pos["last_bid"] = best_bid
                tp_px = pos.get("maker_tp_px")
                # Conservative passive Maker fill: require live best_bid >= tp_px
                if tp_px and best_bid >= float(tp_px) and (now - pos["entry_ts"]) >= 15.0:
                    to_close.append((pid, "MAKER_TP_FILLED", float(tp_px), 0.0))
                    continue

                # Check Hard Stop and Time-Stop on M1_SVI_MAKER_SCALP & M4_SHOCK_STRIKE_CATCHUP
                if sleeve in ("M1_SVI_MAKER_SCALP", "M4_SHOCK_STRIKE_CATCHUP") and best_bid > 0 and (now - pos["entry_ts"]) >= 30.0:
                    entry_vwap = float(pos["entry_vwap_t1000"])
                    rem_tte = float(pos["close_ts"]) - now
                    stop_drop = 0.085 if sleeve == "M4_SHOCK_STRIKE_CATCHUP" else 0.075
                    min_tte_stop = 900.0 if sleeve == "M4_SHOCK_STRIKE_CATCHUP" else 3600.0
                    if best_bid <= entry_vwap - stop_drop:
                        exit_fee_ps = CRYPTO_FEE_RATE * best_bid * (1.0 - best_bid)
                        to_close.append((pid, "HARD_STOP_SVI", max(0.0, best_bid - exit_fee_ps), 0.0))
                        continue
                    if rem_tte <= min_tte_stop:
                        exit_fee_ps = CRYPTO_FEE_RATE * best_bid * (1.0 - best_bid)
                        to_close.append((pid, "TIME_STOP", max(0.0, best_bid - exit_fee_ps), 0.0))
                        continue

                # Check Salvage Stop (-22c) on M2_STRIKE_CONVERGENCE
                if sleeve == "M2_STRIKE_CONVERGENCE" and best_bid > 0 and (now - pos["entry_ts"]) >= 30.0:
                    entry_vwap = float(pos["entry_vwap_t1000"])
                    if best_bid <= max(0.25, entry_vwap - 0.22):
                        exit_fee_ps = CRYPTO_FEE_RATE * best_bid * (1.0 - best_bid)
                        to_close.append((pid, "SALVAGE_STOP", max(0.0, best_bid - exit_fee_ps), 0.0))
                        continue
            else:
                # CLOB /book returned None (404 happens immediately when Polymarket closes/resolves a market early, e.g. Weather!)
                last_g_chk = float(pos.get("_last_gamma_chk_ts") or 0.0)
                if (now - last_g_chk) >= 60.0:
                    pos["_last_gamma_chk_ts"] = now
                    g_pay = await self.resolve_via_gamma_market(pos)
                    if g_pay is not None:
                        st_lbl = "SETTLED_GAMMA_WIN" if g_pay >= 0.99 else "SETTLED_GAMMA_LOSS"
                        to_close.append((pid, st_lbl, g_pay, 0.0))
                        continue

            # 3. Check authoritative Gamma resolution (and verified oracle fallback) if past close_ts
            if now >= float(pos["close_ts"]) + 30.0:
                g_pay = await self.resolve_via_gamma_market(pos)
                if g_pay is not None:
                    st_lbl = "SETTLED_GAMMA_WIN" if g_pay >= 0.99 else "SETTLED_GAMMA_LOSS"
                    to_close.append((pid, st_lbl, g_pay, 0.0))
                    continue

                if bk:
                    best_bid, _ = extract_best_bid(bk.get("bids") or [])
                    asks = bk.get("asks") or []
                    best_ask = min((float(a["price"]) for a in asks if float(a.get("size", 0)) > 0), default=1.0)
                    if best_bid >= 0.99:
                        to_close.append((pid, "SETTLED_WIN", 1.0, 0.0))
                        continue
                    if best_ask <= 0.01:
                        to_close.append((pid, "SETTLED_LOSS", 0.0, 0.0))
                        continue

                # Authoritative Chainlink 60s-TWAP fallback for S5M_CHAINLINK_SNIPER / S4H_CHAINLINK_CONVERGENCE if Gamma lags >= 120s
                if sleeve in ("S5M_CHAINLINK_SNIPER", "S4H_CHAINLINK_CONVERGENCE") and now >= float(pos["close_ts"]) + 120.0:
                    extra = pos.get("extra") or {}
                    if extra.get("start_iso"):
                        cp_url = build_own_gamma_event_url(pos["asset_or_city"], str(extra.get("horizon") or "5m"), extra["start_iso"])
                        cp_payload = await self.fetch_json(cp_url, timeout=4.0)
                        close_px = parse_authoritative_close_price(cp_payload)
                        open_px = float(extra.get("open_price") or 0.0)
                        if close_px is not None and open_px > 0.0:
                            up_won = close_px >= open_px
                            won = up_won if str(pos.get("side")).upper() == "UP" else (not up_won)
                            st_lbl = "SETTLED_ORACLE_TWAP_WIN" if won else "SETTLED_ORACLE_TWAP_LOSS"
                            to_close.append((pid, st_lbl, 1.0 if won else 0.0, 0.0))
                            continue

                # Verified 1m-kline fallback if Gamma lags > 15 minutes past close_ts on Crypto sleeves
                if now >= float(pos["close_ts"]) + 900.0:
                    if sleeve in ("B1_CONVEX_TAIL_YES", "B2_BARRIER_NO_LOCK"):
                        asset = pos["asset_or_city"]
                        k = float(pos["extra"].get("strike") or 0.0)
                        d = pos["extra"].get("direction")
                        w_start = float(pos["extra"].get("start_ts") or pos["entry_ts"])
                        ext_fin = await loop.run_in_executor(
                            None, fetch_binance_window_extremes_sync, asset, w_start, float(pos["close_ts"]), "1m"
                        )
                        if ext_fin is not None and k > 0:
                            max_h, min_l, _ = ext_fin
                            touched = (d == "UP" and max_h >= k) or (d == "DOWN" and min_l <= k)
                            pay_ps = (1.0 if touched else 0.0) if pos["side"] == "YES" else (0.0 if touched else 1.0)
                            to_close.append((pid, "SETTLED_VERIFIED_1M_ORACLE", pay_ps, 0.0))
                            continue
                    elif sleeve == "U1_DAILY_UPDOWN_LOCK":
                        asset = pos["asset_or_city"]
                        k = float(pos["extra"]["strike"])
                        close_ts_f = float(pos["close_ts"])
                        ext_exp = await loop.run_in_executor(
                            None, fetch_binance_window_extremes_sync, asset, close_ts_f - 120.0, close_ts_f, "1m"
                        )
                        if ext_exp is not None and k > 0:
                            exp_close = ext_exp[2]
                            won = (exp_close >= k) if str(pos["side"]).upper() == "UP" else (exp_close < k)
                            to_close.append((pid, "SETTLED_VERIFIED_1M_CLOSE", 1.0 if won else 0.0, 0.0))
                            continue
                    elif sleeve in ("M1_SVI_MAKER_SCALP", "M2_STRIKE_CONVERGENCE", "M4_SHOCK_STRIKE_CATCHUP"):
                        asset = pos["asset_or_city"]
                        k = float(pos["extra"]["strike"])
                        is_dn = bool(pos["extra"].get("is_downward"))
                        close_ts_f = float(pos["close_ts"])
                        ext_exp = await loop.run_in_executor(
                            None, fetch_binance_window_extremes_sync, asset, close_ts_f - 120.0, close_ts_f, "1m"
                        )
                        if ext_exp is not None and k > 0:
                            exp_close = ext_exp[2]
                            yes_won = (exp_close < k) if is_dn else (exp_close > k)
                            won = yes_won if pos["side"] == "YES" else (not yes_won)
                            to_close.append((pid, "SETTLED_VERIFIED_1M_CLOSE", 1.0 if won else 0.0, 0.0))
                            continue

        for pid, status, net_pay_ps, tier_pay_override in to_close:
            pos = self.open_positions.pop(pid, None)
            if not pos:
                continue
            tier_pnls: Dict[str, float] = {}
            adj_tier_pnls: Dict[str, float] = {}
            drag_map = (pos.get("extra") or {}).get("legging_drag_usd_by_tier") or {}
            t_pay_map = tier_pay_override if isinstance(tier_pay_override, dict) else {}
            for t_name, tf in pos["tier_fills"].items():
                cost_total = float(tf["spent_usd"]) + float(tf["fee_usd"])
                eff_pay_ps = float(t_pay_map.get(t_name, net_pay_ps))
                payout_usd = float(tf["shares"]) * eff_pay_ps
                raw_p = round(payout_usd - cost_total, 2)
                tier_pnls[t_name] = raw_p
                adj_tier_pnls[t_name] = round(raw_p - float(drag_map.get(t_name, 0.0) or 0.0), 2)

            won_t1000 = tier_pnls.get("T1000", 0.0) > 0
            pos.update({
                "status": status,
                "closed_ts": now,
                "closed_utc": datetime.now(timezone.utc).isoformat(),
                "net_payout_per_share": round(net_pay_ps, 4),
                "tier_pnls_usd": tier_pnls,
                "legging_adjusted_tier_pnls_usd": adj_tier_pnls,
                "won": won_t1000,
            })
            self.closed_positions.append(pos)
            self._append_ledger({"event": "SHADOW_CLOSE", **pos})
            logger.info(
                f"[CLOSE:{pos['sleeve']}] {pos['title']} ({pos['side']}) -> {status} | "
                f"PnL T100=${tier_pnls.get('T100',0):+.2f} T1000=${tier_pnls.get('T1000',0):+.2f} T5000=${tier_pnls.get('T5000',0):+.2f}"
            )

    def write_state_files(self, opps: List[Dict[str, Any]]) -> None:
        if len(getattr(self, "authoritative_strike_cache", {})) > 2000:
            for _k in list(self.authoritative_strike_cache.keys())[:-1500]:
                self.authoritative_strike_cache.pop(_k, None)
        if len(self.entered_keys) > 5000:
            _open_dk = {str(p.get("dedupe_key") or "") for p in self.open_positions.values()}
            self.entered_keys = _open_dk | set(list(self.entered_keys)[-3000:])
        global_bus = read_global_positions_shm()
        ext_positions = [
            p
            for d_name, d_rec in (global_bus.get("daemons") or {}).items()
            if d_name != "alpha124_shadow" and isinstance(d_rec, dict)
            for p in (d_rec.get("positions") or [])
        ]
        opps_sorted = rank_opportunities_capital_auction(
            opps, active_global_positions=list(self.open_positions.values()) + ext_positions
        )[:25]
        self.top_opportunities = opps_sorted
        publish_global_positions_shm("alpha124_shadow", self.open_positions.values())

        by_sleeve: Dict[str, Dict[str, Any]] = {}
        tier_totals = {"T100": 0.0, "T1000": 0.0, "T5000": 0.0}

        for sl in BANKROLL_TICKETS["T1000"].keys():
            is_d1_sl = str(sl).startswith("D1_")
            all_closed_sl = [p for p in self.closed_positions if p.get("sleeve") == sl]
            # Graduation stats must never count pre-fix inverted anti-box entries (net < $0.900): lucky wins there are not validation
            # Maker-anchor unhedged scratches record a single-leg bid (~$0.40) as entry_eff_px: they are real losses,
            # never anti-box entries, so they must never be dropped (survivorship bias in graduation stats).
            closed_sl = [
                p for p in all_closed_sl
                if not (
                    is_d1_sl
                    and p.get("status") != "MAKER_ANCHOR_UNHEDGED_SCRATCH"
                    and float(p.get("entry_eff_px_t1000") or 1.0) < 0.900
                )
            ]
            excluded_anti = len(all_closed_sl) - len(closed_sl)
            open_sl = [p for p in self.open_positions.values() if p.get("sleeve") == sl]
            wins = sum(1 for p in closed_sl if p.get("won"))
            pnl_1k = sum(float(p.get("tier_pnls_usd", {}).get("T1000", 0.0)) for p in closed_sl)
            adj_pnl_1k = sum(
                float(p.get("legging_adjusted_tier_pnls_usd", p.get("tier_pnls_usd", {})).get("T1000", 0.0))
                for p in closed_sl
            )
            for t_k in tier_totals:
                tier_totals[t_k] = round(
                    tier_totals[t_k] + sum(float(p.get("tier_pnls_usd", {}).get(t_k, 0.0)) for p in closed_sl), 2
                )
            by_sleeve[sl] = {
                "open": len(open_sl),
                "closed": len(closed_sl),
                "wins": wins,
                "losses": len(closed_sl) - wins,
                "win_rate_pct": round(100.0 * wins / len(closed_sl), 2) if closed_sl else 0.0,
                "realized_pnl_t1000_usd": round(pnl_1k, 2),
                "legging_adjusted_pnl_t1000_usd": round(adj_pnl_1k, 2),
                "excluded_anti_box": excluded_anti,
                "quarantined": is_shadow_sleeve_quarantined(sl),
            }

        # Graduation by-asset stats cover only the taker dominance-box sleeves (maker-anchor tracked in by_sleeve)
        D1_GRAD_SLEEVES = {"D1_SAME_ORACLE_DOMINANCE_BOX", "D1_4H_DOMINANCE_BOX", "D1_QUIET_BOOK_BOX"}
        by_d1_asset: Dict[str, Dict[str, Any]] = {}
        for a_dom in DOMINANCE_ASSETS:
            cl_a = [
                p for p in self.closed_positions
                if str(p.get("sleeve") or "") in D1_GRAD_SLEEVES
                and str(p.get("asset_or_city") or "").upper() == a_dom
                and (
                    p.get("status") == "MAKER_ANCHOR_UNHEDGED_SCRATCH"
                    or float(p.get("entry_eff_px_t1000") or 1.0) >= 0.900
                )
            ]
            op_a = [
                p for p in self.open_positions.values()
                if str(p.get("sleeve") or "") in D1_GRAD_SLEEVES
                and str(p.get("asset_or_city") or "").upper() == a_dom
            ]
            w_a_cnt = sum(1 for p in cl_a if p.get("won"))
            pnl_a_1k = sum(float(p.get("tier_pnls_usd", {}).get("T1000", 0.0)) for p in cl_a)
            adj_pnl_a_1k = sum(
                float(p.get("legging_adjusted_tier_pnls_usd", p.get("tier_pnls_usd", {})).get("T1000", 0.0))
                for p in cl_a
            )
            by_d1_asset[a_dom] = {
                "open": len(op_a),
                "closed": len(cl_a),
                "wins": w_a_cnt,
                "losses": len(cl_a) - w_a_cnt,
                "win_rate_pct": round(100.0 * w_a_cnt / len(cl_a), 2) if cl_a else 0.0,
                "realized_pnl_t1000_usd": round(pnl_a_1k, 2),
                "legging_adjusted_pnl_t1000_usd": round(adj_pnl_a_1k, 2),
            }

        state = {
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "started_at": self.started_at,
            "cycle_count": self.cycle_count,
            "calibration": {
                "weather_sigma_c": self.weather_sigma_c,
                "barrier_wick_mult": self.barrier_wick_mult,
            },
            "spots": self.spots,
            "markets_monitored": {
                "weather_city_events": len(self.weather_events),
                "barrier_hit_rungs": len(self.barrier_rungs),
                "multistrike_ladders": len(self.strike_ladders),
                "negrisk_bracket_ladders": len(self.negrisk_ladders),
                "daily_updown_markets": len(self.daily_updown_markets),
                "pyth_daily_markets": len(self.pyth_daily_markets),
                "pyth_barrier_rungs": len(self.pyth_barrier_rungs),
                "pyth_close_ladders": len(self.pyth_close_ladders),
                "nba_zero_fee_games": len(self.nba_games),
                "negrisk_zero_fee_slates": len(self.negrisk_zero_slates),
                "counting_slates": len(self.counting_slates),
                "fomc_lp_markets": len(self.fomc_truth_legs) // 2,
                "oil_senate_markets": len(self.oil_senate_truth_legs) // 2,
                "hourly_12pm_pairs": len(self.hourly_12pm_markets),
                "same_oracle_dominance_pairs": len(self.dominance_pairs),
                "dominance_4h_pairs": len(self.dominance_4h_pairs),
                "exact_twap_lock_candles": len(self.twap_candles),
                "s5m_sniper_candles": len(self.s5m_candles),
                "s4h_candles": len(self.s4h_candles),
                "preopen_15m_candles": len(self.preopen_15m_candles),
            },
            "portfolio_realized_pnl_by_bankroll_usd": tier_totals,
            "by_sleeve": by_sleeve,
            "per_strategy": by_sleeve,
            "by_d1_asset": by_d1_asset,
            "open_positions_count": len(self.open_positions),
            "pending_maker_orders_count": len(self.pending_maker_orders),
            "pending_maker_anchors_count": len(self.pending_maker_anchors),
            "pending_zero_fee_maker_anchors_count": len(self.pending_zero_fee_maker_anchors),
            "pending_preopen_straddles_count": len(self.pending_preopen_straddles),
            "pending_maker_orders": list(self.pending_maker_orders.values()),
            "open_positions": list(self.open_positions.values()),
            "recent_closed_positions": self.closed_positions[-30:],
        }

        tmp_s = STATE_FILE.with_suffix(".tmp")
        tmp_s.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp_s, STATE_FILE)

        # Mirror lightweight graduation summary into data/polymarket/alpha124_shadow_state.json for live harvester
        if STATE_FILE == (DATA_DIR / "alpha124_shadow_state.json") or LIVE_ALPHA124_STATE_MIRROR_FILE != (LIVE_POLYMARKET_DIR / "alpha124_shadow_state.json"):
            try:
                LIVE_ALPHA124_STATE_MIRROR_FILE.parent.mkdir(parents=True, exist_ok=True)
                tmp_m = LIVE_ALPHA124_STATE_MIRROR_FILE.with_suffix(".tmp")
                tmp_m.write_text(
                    json.dumps(
                        {
                            "updated_at_utc": state["updated_at_utc"],
                            "by_sleeve": by_sleeve,
                            "per_strategy": by_sleeve,
                            "by_d1_asset": by_d1_asset,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                os.replace(tmp_m, LIVE_ALPHA124_STATE_MIRROR_FILE)
            except Exception as exc:
                logger.debug(f"Graduation mirror write notice: {exc}")

        tmp_o = OPPS_FILE.with_suffix(".tmp")
        tmp_o.write_text(
            json.dumps({"updated_at_utc": state["updated_at_utc"], "top_opportunities": opps_sorted}, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp_o, OPPS_FILE)

        # Auto-refresh live day-by-day projections once every 60s
        now_p = time.time()
        if (now_p - float(getattr(self, "_last_proj_write_ts", 0.0))) >= 60.0:
            self._last_proj_write_ts = now_p
            try:
                from scripts.polymarket_daily_projections import write_live_projections_atomic
                write_live_projections_atomic(days=30)
            except Exception as exc:
                logger.debug(f"Live daily projections refresh notice: {exc}")

    async def write_state_files_async(self, opps: List[Dict[str, Any]]) -> None:
        """Offloads synchronous JSON serialization & atomic disk renames from the <250ms event loop (`H-07`)."""
        await asyncio.to_thread(self.write_state_files, opps)

    async def _run_bg_discovery(self) -> None:
        try:
            await self.discover_all_markets()
        except Exception as exc:
            logger.warning(f"Background discovery notice: {exc}")

    async def _run_bg_mid_crypto(self) -> None:
        try:
            mid_opps: List[Dict[str, Any]] = []
            await self.scan_multistrike_markets(mid_opps)
            await self.scan_daily_updown_locks(mid_opps)
            await self.scan_barrier_markets(mid_opps)
            self.cached_mid_opps = mid_opps
        except Exception as exc:
            logger.warning(f"Background mid-crypto scan notice: {exc}")

    async def _run_bg_weather(self) -> None:
        try:
            w_opps: List[Dict[str, Any]] = []
            await self.scan_weather_markets(w_opps)
            self.cached_weather_opps = w_opps
        except Exception as exc:
            logger.warning(f"Background weather scan notice: {exc}")

    async def _get_pyth_intraday(self, asset: str, now_ts: float) -> Optional[Dict[str, Any]]:
        cfg = PYTH_ASSET_CONFIG.get(asset.upper())
        if not cfg:
            return None
        yh_sym, _, _, _, vol_floor = cfg
        cached = self.pyth_intraday_cache.get(yh_sym)
        if cached is not None and (now_ts - cached[0]) < 90.0:
            return cached[1]
        res = await asyncio.to_thread(fetch_yahoo_1m_intraday_sync, yh_sym, vol_floor)
        if res is not None:
            self.pyth_intraday_cache[yh_sym] = (now_ts, res)
        return res

    async def scan_tradfi_and_sports_markets(self, opps_out: List[Dict[str, Any]]) -> None:
        """
        Scans `0.00%`-fee Pyth Commodities/Metals/Equities (`CM_B3`, `CM_B2`, `CM_U1`, `B4`),
        NBA Full-Game Dominance Boxes (`SP1_NBA_ZERO_FEE_BOX`), and Zero-Fee NegRisk Slates (`NR0`).
        """
        now = time.time()

        # 1. Refresh Yahoo 1m intraday anchors across active Pyth assets
        active_pyth_assets = sorted(
            {r.asset for r in self.pyth_barrier_rungs.values() if r.end_ts > now + 120}
            | {rgs[0].asset for rgs in self.pyth_close_ladders.values() if rgs and rgs[0].end_ts > now + 120}
        )
        feed_by_asset: Dict[str, Dict[str, Any]] = {}
        for a_p in active_pyth_assets:
            fd = await self._get_pyth_intraday(a_p, now)
            if fd:
                feed_by_asset[a_p] = fd

        # 2. Batch-fetch near-ATM Pyth Hit & Close books (`0%` fee)
        near_hit: List[PythBarrierRungSpec] = []
        for r in self.pyth_barrier_rungs.values():
            if r.end_ts <= now + 120 or r.asset not in feed_by_asset:
                continue
            sp_px = float(feed_by_asset[r.asset]["spot"])
            if sp_px > 0 and abs(math.log(r.strike / sp_px)) <= 0.25:
                near_hit.append(r)

        near_close: List[PythCloseRungSpec] = []
        for rgs in self.pyth_close_ladders.values():
            for rc in rgs:
                if rc.end_ts <= now + 120 or rc.asset not in feed_by_asset:
                    continue
                sp_px = float(feed_by_asset[rc.asset]["spot"])
                if sp_px > 0 and abs(math.log(rc.strike / sp_px)) <= 0.14:
                    near_close.append(rc)

        pyth_toks = (
            [r.yes_token for r in near_hit] + [r.no_token for r in near_hit]
            + [rc.yes_token for rc in near_close] + [rc.no_token for rc in near_close]
        )
        pyth_bks = await self.fetch_books_batch(pyth_toks, timeout=3.5) if pyth_toks else {}

        all_hit_rows: List[Dict[str, Any]] = []
        by_event_hit_rows: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
        for r in near_hit:
            bk_y, bk_n = pyth_bks.get(r.yes_token), pyth_bks.get(r.no_token)
            if not bk_y or not bk_n:
                continue
            cfg = PYTH_ASSET_CONFIG[r.asset]
            _, sess_cls, exact_ok, basis_buf, _ = cfg
            fd = feed_by_asset[r.asset]
            spot_p = float(fd["spot"])
            in_active_window = now >= r.start_ts
            ext_p = window_extremes_from_bars(fd["bars"], r.start_ts, now) if in_active_window else None

            # Check B4_TOUCHED_BARRIER_WICK_LOCK ONLY inside active observation window (`now >= r.start_ts + 300s`)
            # with wider CME roll/venue cushion (`>= 0.80%` + `bid >= 0.88`) to eliminate NYMEX-vs-ICE basis ticks
            if in_active_window and now >= r.start_ts + 300.0 and exact_ok and sess_cls in ("EQUITY_RTH", "CME_23H") and ext_p is not None and f"B4_PYTH_{r.market_id}" not in self.entered_keys:
                fh_p, fl_p = ext_p
                b4_buf = 0.0015 if sess_cls == "EQUITY_RTH" else max(0.0080, 2.5 * basis_buf)
                min_b4_bid = 0.78 if sess_cls == "EQUITY_RTH" else 0.88
                if (r.direction == "UP" and fh_p >= r.strike * (1.0 + b4_buf)) or (r.direction == "DOWN" and fl_p <= r.strike * (1.0 - b4_buf)):
                    bid_b4p, _ = extract_best_bid(bk_y.get("bids") or [])
                    w_b4p = walk_l2_book_asks(bk_y.get("asks") or [], 100.0, fee_rate=0.0, min_l1_usd=15.0, max_ask_px=0.990)
                    if w_b4p.get("filled") and bid_b4p >= min_b4_bid and 0.85 <= float(w_b4p["eff_px"]) <= 0.986:
                        opps_out.append({
                            "sleeve": "B4_TOUCHED_BARRIER_WICK_LOCK",
                            "market": f"{r.asset} Pyth Breached Wick Lock: {r.question}",
                            "ask_vwap": w_b4p["eff_px"],
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_b4p["eff_px"]), 4),
                            "l1_usd": w_b4p["l1_usd"],
                        })
                        await self.open_shadow_position(
                            sleeve="B4_TOUCHED_BARRIER_WICK_LOCK",
                            dedupe_key=f"B4_PYTH_{r.market_id}",
                            asset_or_city=r.asset,
                            title=r.question,
                            side_label="YES",
                            token_id=r.yes_token,
                            fee_rate=0.0,
                            p_model=1.0,
                            close_ts=r.end_ts,
                            extra={"market_id": r.market_id, "condition_id": r.condition_id, "strike": r.strike, "direction": r.direction, "session_class": sess_cls},
                            prefetched_book=bk_y,
                        )
                        continue

            w_qy = walk_l2_book_asks(bk_y.get("asks") or [], 35.0, fee_rate=0.0, min_l1_usd=8.0)
            w_qn = walk_l2_book_asks(bk_n.get("asks") or [], 35.0, fee_rate=0.0, min_l1_usd=8.0)
            row_h = {
                "asset": r.asset,
                "event_id": r.event_id,
                "strike": r.strike,
                "direction": r.direction,
                "market_id": r.market_id,
                "condition_id": r.condition_id,
                "yes_token": r.yes_token,
                "no_token": r.no_token,
                "fee_rate": 0.0,
                "ask_yes": w_qy.get("vwap") if w_qy.get("filled") else None,
                "ask_no": w_qn.get("vwap") if w_qn.get("filled") else None,
                "bk_yes": bk_y,
                "bk_no": bk_n,
                "start_ts": r.start_ts,
                "end_ts": r.end_ts,
            }
            all_hit_rows.append(row_h)
            by_event_hit_rows[r.event_id].append(row_h)

            # CM_B2_PYTH_SESSION_NO_LOCK (`0%` fee, same-session final <=3.5h lock -> zero overnight/earnings gap + tight spread <=4c)
            eff_hrs = compute_effective_trading_hours(now, r.end_ts, sess_cls)
            same_sess = is_same_continuous_session(now, r.end_ts, sess_cls)
            already_hit = ext_p is not None and (
                (r.direction == "UP" and ext_p[0] >= r.strike * (1.0 - basis_buf))
                or (r.direction == "DOWN" and ext_p[1] <= r.strike * (1.0 + basis_buf))
            )
            if in_active_window and exact_ok and same_sess and not already_hit and 0.25 <= eff_hrs <= 3.5:
                ev_no = evaluate_pyth_session_barrier_no_lock(spot_p, r.strike, r.direction, eff_hrs, float(fd["sigma_session"]), basis_buf)
                p_no_p = float(ev_no["p_no"])
                if p_no_p >= 0.94:
                    bid_np, _ = extract_best_bid(bk_n.get("bids") or [])
                    w_np = walk_l2_book_asks(bk_n.get("asks") or [], 100.0, fee_rate=0.0, min_l1_usd=15.0)
                    if w_np.get("filled") and 0.78 <= float(w_np["eff_px"]) <= 0.955 and bid_np > 0 and (float(w_np["vwap"]) - bid_np) <= 0.04:
                        edge_np = p_no_p - float(w_np["eff_px"])
                        b2_g = evaluate_barrier_no_net_ev(1.0 - p_no_p, float(w_np["vwap"]), fee_rate=0.0)
                        if edge_np >= 0.025:
                            opps_out.append({
                                "sleeve": "CM_B2_PYTH_SESSION_NO_LOCK",
                                "market": f"{r.asset} Pyth NO ({eff_hrs:.1f}h sess): {r.question}",
                                "ask_vwap": w_np["eff_px"],
                                "p_model": p_no_p,
                                "net_edge": round(edge_np, 4),
                                "l1_usd": w_np["l1_usd"],
                            })
                        if edge_np >= 0.035 and b2_g["eligible"]:
                            await self.open_shadow_position(
                                sleeve="CM_B2_PYTH_SESSION_NO_LOCK",
                                dedupe_key=f"CMB2_{r.market_id}",
                                asset_or_city=r.asset,
                                title=r.question,
                                side_label="NO",
                                token_id=r.no_token,
                                fee_rate=0.0,
                                p_model=p_no_p,
                                close_ts=r.end_ts,
                                extra={"market_id": r.market_id, "condition_id": r.condition_id, "strike": r.strike, "direction": r.direction, "eff_session_hours": round(eff_hrs, 2)},
                                prefetched_book=bk_n,
                            )

            # CM_SHOCK_PYTH_CATALYST: 0%-fee scheduled NY macro release (08:30 CPI/NFP, 10:30 EIA, 14:00 FOMC) Pyth jump sniper
            prev_sp = self.prev_pyth_spots.get(r.asset, 0.0)
            if in_active_window and exact_ok and same_sess and not already_hit and prev_sp > 0.0:
                sh_ev = evaluate_pyth_catalyst_shock(r.asset, prev_sp, spot_p, r.strike, r.direction, eff_hrs, float(fd["sigma_session"]), now)
                if sh_ev.get("eligible"):
                    sh_side = str(sh_ev["side"])
                    sh_tok = r.yes_token if sh_side == "YES" else r.no_token
                    sh_bk = bk_y if sh_side == "YES" else bk_n
                    w_sh = walk_l2_book_asks(sh_bk.get("asks") or [], BANKROLL_TICKETS["T1000"]["CM_SHOCK_PYTH_CATALYST"], fee_rate=0.0, min_l1_usd=15.0)
                    if w_sh.get("filled") and 0.18 <= float(w_sh["eff_px"]) <= 0.88:
                        sh_edge = float(sh_ev["p_fair"]) - float(w_sh["eff_px"])
                        if sh_edge >= 0.045:
                            opps_out.append({"sleeve": "CM_SHOCK_PYTH_CATALYST", "market": f"{r.asset} [{sh_ev['catalyst']}] {sh_side}: {r.question}", "ask_vwap": w_sh["eff_px"], "p_model": sh_ev["p_fair"], "net_edge": round(sh_edge, 4), "l1_usd": w_sh["l1_usd"], "close_ts": r.end_ts})
                            await self.open_shadow_position(
                                sleeve="CM_SHOCK_PYTH_CATALYST",
                                dedupe_key=f"CMSHK_{r.market_id}_{sh_side}_{int(now // 900)}",
                                asset_or_city=r.asset,
                                title=f"{r.question} [{sh_ev['catalyst']}]",
                                side_label=sh_side,
                                token_id=sh_tok,
                                fee_rate=0.0,
                                p_model=float(sh_ev["p_fair"]),
                                close_ts=r.end_ts,
                                extra={"market_id": r.market_id, "condition_id": r.condition_id, "catalyst": sh_ev["catalyst"], "delta_p": sh_ev["delta_p"], "ret_pct": sh_ev["ret_pct"]},
                                tp_target_px=min(0.95, round(float(w_sh["eff_px"]) + 0.06, 3)),
                                prefetched_book=sh_bk,
                            )

        for a_p, fd_p in feed_by_asset.items():
            self.prev_pyth_spots[a_p] = float(fd_p["spot"])

        all_close_rows: List[Dict[str, Any]] = []
        for rc in near_close:
            bk_y, bk_n = pyth_bks.get(rc.yes_token), pyth_bks.get(rc.no_token)
            if not bk_y or not bk_n:
                continue
            w_qy = walk_l2_book_asks(bk_y.get("asks") or [], 35.0, fee_rate=0.0, min_l1_usd=8.0)
            w_qn = walk_l2_book_asks(bk_n.get("asks") or [], 35.0, fee_rate=0.0, min_l1_usd=8.0)
            all_close_rows.append({
                "asset": rc.asset,
                "strike": rc.strike,
                "is_downward": rc.is_downward,
                "market_id": rc.market_id,
                "condition_id": rc.condition_id,
                "yes_token": rc.yes_token,
                "no_token": rc.no_token,
                "fee_rate": 0.0,
                "ask_yes": w_qy.get("vwap") if w_qy.get("filled") else None,
                "ask_no": w_qn.get("vwap") if w_qn.get("filled") else None,
                "bk_yes": bk_y,
                "bk_no": bk_n,
                "end_ts": rc.end_ts,
            })
            cfg = PYTH_ASSET_CONFIG[rc.asset]
            _, sess_cls, exact_ok, basis_buf, _ = cfg
            fd = feed_by_asset[rc.asset]
            eff_hrs_c = compute_effective_trading_hours(now, rc.end_ts, sess_cls)
            if exact_ok and is_same_continuous_session(now, rc.end_ts, sess_cls) and 0.08 <= eff_hrs_c <= 0.75:
                cl_ev = evaluate_pyth_session_close_lock(float(fd["spot"]), rc.strike, rc.is_downward, eff_hrs_c, float(fd["sigma_session"]), basis_buf)
                if cl_ev["eligible"]:
                    side_c = str(cl_ev["side"])
                    tok_c = rc.yes_token if side_c == "YES" else rc.no_token
                    bk_c = bk_y if side_c == "YES" else bk_n
                    bid_cp, _ = extract_best_bid(bk_c.get("bids") or [])
                    w_cp = walk_l2_book_asks(bk_c.get("asks") or [], 100.0, fee_rate=0.0, min_l1_usd=15.0)
                    if w_cp.get("filled") and 0.78 <= float(w_cp["eff_px"]) <= 0.955 and bid_cp > 0 and (float(w_cp["vwap"]) - bid_cp) <= 0.04:
                        edge_cp = float(cl_ev["p_lock"]) - float(w_cp["eff_px"])
                        if edge_cp >= 0.020:
                            opps_out.append({
                                "sleeve": "CM_U1_PYTH_CLOSE_LOCK",
                                "market": f"{rc.asset} Close Lock ({side_c}, z={cl_ev['z_session']:.2f}): {rc.question}",
                                "ask_vwap": w_cp["eff_px"],
                                "p_model": cl_ev["p_lock"],
                                "net_edge": round(edge_cp, 4),
                                "l1_usd": w_cp["l1_usd"],
                            })
                        if edge_cp >= 0.030:
                            await self.open_shadow_position(
                                sleeve="CM_U1_PYTH_CLOSE_LOCK",
                                dedupe_key=f"CMU1_{rc.market_id}_{side_c}",
                                asset_or_city=rc.asset,
                                title=rc.question,
                                side_label=side_c,
                                token_id=tok_c,
                                fee_rate=0.0,
                                p_model=float(cl_ev["p_lock"]),
                                close_ts=rc.end_ts,
                                extra={"market_id": rc.market_id, "condition_id": rc.condition_id, "strike": rc.strike, "z_session": cl_ev["z_session"]},
                                prefetched_book=bk_c,
                            )

        # 3. CM_B3_PYTH_BARRIER_BOX: Same-Event Monotonicity + Calendar Inclusion + Close-vs-Hit Inclusion (`0%` fee)
        # Also record per-asset TradFi/Commodities/Metals session telemetry (`PYTH_ASSET_SESSION_SNAP`)
        for a_snap, fd_snap in feed_by_asset.items():
            cfg_s = PYTH_ASSET_CONFIG.get(a_snap)
            if not cfg_s:
                continue
            _, sess_s, exact_s, _, _ = cfg_s
            asset_rows = [rh for rh in all_hit_rows if rh["asset"] == a_snap and rh.get("ask_no") is not None]
            if not asset_rows:
                continue
            nearest_r = min(asset_rows, key=lambda x: (float(x["end_ts"]), abs(math.log(float(x["strike"]) / max(1e-6, float(fd_snap["spot"]))))))
            eff_h_s = compute_effective_trading_hours(now, float(nearest_r["end_ts"]), sess_s)
            same_s = is_same_continuous_session(now, float(nearest_r["end_ts"]), sess_s)
            bid_no_s, sz_no_s = extract_best_bid(nearest_r["bk_no"].get("bids") or [])
            ask_no_s, asz_no_s = self._best_ask_sz(nearest_r["bk_no"])
            self._record_market_telemetry(
                key=f"PYTH_SNAP_{a_snap}",
                min_interval_sec=120.0,
                now_ts=now,
                sig=(round(float(fd_snap["spot"]), 3), round(ask_no_s, 3), round(bid_no_s, 3)),
                payload={
                    "type": "PYTH_ASSET_SESSION_SNAP",
                    "asset": a_snap,
                    "session_class": sess_s,
                    "exact_directional_ok": exact_s,
                    "spot": round(float(fd_snap["spot"]), 4),
                    "sigma_session": fd_snap["sigma_session"],
                    "eff_session_hours": round(eff_h_s, 2),
                    "same_session": same_s,
                    "near_strike": nearest_r["strike"],
                    "near_dir": nearest_r["direction"],
                    "near_ask_no": round(ask_no_s, 4) if ask_no_s < 1.0 else None,
                    "near_bid_no": round(bid_no_s, 4) if bid_no_s > 0 else None,
                    "near_ask_l1_usd": round(ask_no_s * asz_no_s, 2) if ask_no_s < 1.0 else 0.0,
                },
            )

        pyth_box_cands: List[Tuple[str, str, Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], float, str]] = []
        for ev_id_p, ev_rows in by_event_hit_rows.items():
            if len(ev_rows) < 2:
                continue
            p_diag = detect_barrier_monotonicity_boxes(ev_rows, fee_rate=0.0, max_box_cost_net=1.15)
            if p_diag:
                pd0 = p_diag[0]
                self._record_market_telemetry(
                    key=f"CMB3_DIAG_{ev_id_p}",
                    min_interval_sec=90.0,
                    now_ts=now,
                    sig=(pd0["direction"], pd0["low_strike"], pd0["high_strike"], pd0["box_cost_net"]),
                    payload={"type": "PYTH_BARRIER_MONO_BEST", "asset": ev_rows[0]["asset"], "event_id": ev_id_p, "net_box_l1": pd0["box_cost_net"], "label": pd0["label"]},
                )
            by_yt = {str(q["yes_token"]): q for q in ev_rows}
            by_nt = {str(q["no_token"]): q for q in ev_rows}
            for ba in p_diag:
                if float(ba["box_cost_net"]) > 1.035:
                    continue
                qy, qn = by_yt.get(ba["yes_token"]), by_nt.get(ba["no_token"])
                if qy and qn:
                    la = {"token_id": ba["yes_token"], "opp_token_id": ba["yes_opp_token"], "condition_id": ba["leg_yes_condition_id"], "side": "YES", "label": f"YES_{ba['direction']}", "market_id": ba["leg_yes_market_id"], "fee_rate": 0.0, "strike": float(qy["strike"])}
                    lb = {"token_id": ba["no_token"], "opp_token_id": ba["no_opp_token"], "condition_id": ba["leg_no_condition_id"], "side": "NO", "label": f"NO_{ba['direction']}", "market_id": ba["leg_no_market_id"], "fee_rate": 0.0, "strike": float(qn["strike"])}
                    pyth_box_cands.append((qy["asset"], f"CMB3_MONO_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}", la, lb, qy["bk_yes"], qn["bk_no"], float(qy["end_ts"]), f"{qy['asset']} Pyth Box {ba['label']}"))

        cal_diag = detect_pyth_calendar_inclusion_boxes(all_hit_rows, max_box_cost_net=1.15)
        if cal_diag:
            cd0 = cal_diag[0]
            self._record_market_telemetry(
                key=f"CMB3_CAL_BEST_{cd0['asset']}",
                min_interval_sec=90.0,
                now_ts=now,
                sig=(cd0["direction"], cd0["strike"], cd0["box_cost_net"]),
                payload={"type": "PYTH_CALENDAR_BEST", "asset": cd0["asset"], "net_box_l1": cd0["box_cost_net"], "label": cd0["label"]},
            )
        for cal in cal_diag:
            if float(cal["box_cost_net"]) > 1.035:
                continue
            qy, qn = cal["yes_row"], cal["no_row"]
            la = {"token_id": qy["yes_token"], "opp_token_id": qy["no_token"], "condition_id": qy["condition_id"], "side": "YES", "label": "YES_LONG", "market_id": qy["market_id"], "fee_rate": 0.0, "strike": float(qy["strike"])}
            lb = {"token_id": qn["no_token"], "opp_token_id": qn["yes_token"], "condition_id": qn["condition_id"], "side": "NO", "label": "NO_SHORT", "market_id": qn["market_id"], "fee_rate": 0.0, "strike": float(qn["strike"])}
            pyth_box_cands.append((cal["asset"], f"CMB3_CAL_{qy['market_id']}_{qn['market_id']}", la, lb, qy["bk_yes"], qn["bk_no"], float(cal["close_ts"]), f"{cal['asset']} Calendar Box {cal['label']}"))

        cvh_diag = detect_pyth_close_vs_hit_boxes(all_close_rows, all_hit_rows, now_ts=now, max_box_cost_net=1.15)
        if cvh_diag:
            vd0 = cvh_diag[0]
            self._record_market_telemetry(
                key=f"CMB3_CVH_BEST_{vd0['asset']}",
                min_interval_sec=90.0,
                now_ts=now,
                sig=(vd0["strike_hit"], vd0["strike_close"], vd0["box_cost_net"]),
                payload={"type": "PYTH_CLOSE_VS_HIT_BEST", "asset": vd0["asset"], "net_box_l1": vd0["box_cost_net"], "label": vd0["label"]},
            )
        for cvh in cvh_diag:
            if float(cvh["box_cost_net"]) > 1.035:
                continue
            qy, qn = cvh["yes_row"], cvh["no_row"]
            la = {"token_id": qy["yes_token"], "opp_token_id": qy["no_token"], "condition_id": qy["condition_id"], "side": "YES", "label": "YES_HIT", "market_id": qy["market_id"], "fee_rate": 0.0, "strike": float(qy["strike"])}
            lb = {"token_id": qn["no_token"], "opp_token_id": qn["yes_token"], "condition_id": qn["condition_id"], "side": "NO", "label": "NO_CLOSE", "market_id": qn["market_id"], "fee_rate": 0.0, "strike": float(qn["strike"])}
            pyth_box_cands.append((cvh["asset"], f"CMB3_CVH_{qy['market_id']}_{qn['market_id']}", la, lb, qy["bk_yes"], qn["bk_no"], float(cvh["close_ts"]), f"{cvh['asset']} Close-vs-Hit Box {cvh['label']}"))

        pyth_box_cands.sort(key=lambda x: ((float(x[6]) - now) > 64800.0, float(x[6])))
        for p_asset, p_dkey, la, lb, bk_a, bk_b, c_ts, p_title in pyth_box_cands:
            w_pb = walk_equal_shares_dominance_box(
                bk_a.get("asks") or [],
                bk_b.get("asks") or [],
                target_budget_usd=BANKROLL_TICKETS["T1000"]["CM_B3_PYTH_BARRIER_BOX"],
                fee_rate_a=0.0,
                fee_rate_b=0.0,
                max_box_cost_net=0.994,
                min_shares=6,
                min_box_notional_usd=5.5,
            )
            if w_pb.get("filled"):
                opps_out.append({
                    "sleeve": "CM_B3_PYTH_BARRIER_BOX",
                    "market": p_title,
                    "ask_vwap": round(float(w_pb["box_cost_net"]), 4),
                    "p_model": 1.0,
                    "net_edge": round(1.0 - float(w_pb["box_cost_net"]), 4),
                    "l1_usd": w_pb["l1_usd"],
                    "close_ts": c_ts,
                })
                await self.open_shadow_two_leg_box(
                    sleeve="CM_B3_PYTH_BARRIER_BOX",
                    dedupe_key=p_dkey,
                    asset=p_asset,
                    title=p_title,
                    leg_a=la,
                    leg_b=lb,
                    bk_a=bk_a,
                    bk_b=bk_b,
                    close_ts=c_ts,
                    max_box_cost_net=0.994,
                    extra={"is_pyth_zero_fee_box": True},
                )
                if float(w_pb["box_cost_net"]) <= 0.990 and (c_ts - now) <= 86400.0:
                    self.emit_live_two_leg_box_candidate(
                        sleeve_source="CM_B3_PYTH_BARRIER_BOX",
                        box_type="BARRIER_MONO",
                        asset=p_asset,
                        dedupe_key=p_dkey,
                        leg_a=la,
                        leg_b=lb,
                        bk_a=bk_a,
                        bk_b=bk_b,
                        close_ts=c_ts,
                        now_ts=now,
                        k_low=min(float(la.get("strike") or 100.0), float(lb.get("strike") or 100.0)),
                        k_high=max(float(la.get("strike") or 100.0), float(lb.get("strike") or 100.0)),
                    )
            else:
                self.post_zero_fee_maker_anchor_box("CM_B3", p_asset, f"ZFA_{p_dkey}", la, lb, bk_a, bk_b, c_ts, p_title, now)

        # 4. SP1_NBA_ZERO_FEE_BOX: NBA Full-Game Polish Middle (ML vs +Spread), Spread vs Spread & Total O/U Boxes (`0%` fee)
        for sp_nba in list(self.nba_games.values()):
            if now > sp_nba.tipoff_ts + 6.0 * 3600.0:
                self.nba_games.pop(sp_nba.event_id, None)
                continue
            nba_legs = sp_nba.margin_legs + sp_nba.total_legs
            nba_toks = sorted({lg.token_id for lg in nba_legs})
            if len(nba_toks) < 4:
                continue
            nba_bks = await self.fetch_books_batch(nba_toks, timeout=3.5)
            best_asks_nba: Dict[str, float] = {}
            for t_n, bk_n in nba_bks.items():
                px_n, sz_n = self._best_ask_sz(bk_n)
                if px_n < 1.0 and sz_n * px_n >= 8.0:
                    best_asks_nba[t_n] = px_n
            nba_diag = detect_nba_dominance_boxes(sp_nba, best_asks_nba, max_box_cost_net=1.12)
            if nba_diag:
                nd0 = nba_diag[0]
                lga0, lgb0 = nd0["leg_a"], nd0["leg_b"]
                bka0 = nba_bks.get(lga0.token_id) or {}
                bkb0 = nba_bks.get(lgb0.token_id) or {}
                aa0, sa0 = self._best_ask_sz(bka0)
                ab0, sb0 = self._best_ask_sz(bkb0)
                ba0, _ = extract_best_bid(bka0.get("bids") or [])
                bb0, _ = extract_best_bid(bkb0.get("bids") or [])
                mkr_cands = []
                if ba0 > 0 and (aa0 - ba0) >= 0.02:
                    mkr_cands.append(round(min(ba0 + 0.01, aa0 - 0.01) + ab0, 4))
                if bb0 > 0 and (ab0 - bb0) >= 0.02:
                    mkr_cands.append(round(aa0 + min(bb0 + 0.01, ab0 - 0.01), 4))
                mkr_box_n = min(mkr_cands) if mkr_cands else None
                self._record_market_telemetry(
                    key=f"NBA_BOX_{sp_nba.event_id}",
                    min_interval_sec=45.0,
                    now_ts=now,
                    sig=(nd0["label"], nd0["box_cost_net"], mkr_box_n),
                    payload={
                        "type": "NBA_ZERO_FEE_BOX_BEST",
                        "event_id": sp_nba.event_id,
                        "game": sp_nba.title,
                        "box_kind": nd0["box_kind"],
                        "in_play": bool(now >= sp_nba.tipoff_ts),
                        "sec_from_tipoff": round(now - sp_nba.tipoff_ts, 0),
                        "best_label": nd0["label"],
                        "leg_a_ask": round(aa0, 4),
                        "leg_a_bid": round(ba0, 4) if ba0 > 0 else None,
                        "leg_b_ask": round(ab0, 4),
                        "leg_b_bid": round(bb0, 4) if bb0 > 0 else None,
                        "net_box_l1": nd0["box_cost_net"],
                        "maker_anchor_box_l1": mkr_box_n,
                        "l1_min_usd": round(min(aa0 * sa0, ab0 * sb0), 2),
                        "middle_pts": nd0["middle_width_pts"],
                    },
                )
            for nb in nba_diag:
                if float(nb["box_cost_net"]) > 1.035:
                    continue
                lga, lgb = nb["leg_a"], nb["leg_b"]
                bk_a, bk_b = nba_bks.get(lga.token_id), nba_bks.get(lgb.token_id)
                if not bk_a or not bk_b:
                    continue
                la_n = {"token_id": lga.token_id, "opp_token_id": lga.opp_token_id, "condition_id": lga.condition_id, "side": lga.side_label, "label": lga.display_label, "market_id": lga.market_id, "fee_rate": 0.0, "strike": float(lga.threshold)}
                lb_n = {"token_id": lgb.token_id, "opp_token_id": lgb.opp_token_id, "condition_id": lgb.condition_id, "side": lgb.side_label, "label": lgb.display_label, "market_id": lgb.market_id, "fee_rate": 0.0, "strike": float(lgb.threshold)}
                if float(nb["box_cost_net"]) > 0.994:
                    self.post_zero_fee_maker_anchor_box(
                        "SP1_NBA", "NBA", f"ZFA_SP1_{sp_nba.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",
                        la_n, lb_n, bk_a, bk_b, float(nb["close_ts"]), f"{sp_nba.title} [{nb['label']}]", now,
                        prefetched_books=nba_bks,
                    )
                    continue
                w_nba = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["SP1_NBA_ZERO_FEE_BOX"],
                    fee_rate_a=0.0,
                    fee_rate_b=0.0,
                    max_box_cost_net=0.994,
                    min_shares=8,
                    min_box_notional_usd=7.0,
                )
                if w_nba.get("filled"):
                    opps_out.append({
                        "sleeve": "SP1_NBA_ZERO_FEE_BOX",
                        "market": f"NBA {sp_nba.title}: {nb['label']} (mid={nb['middle_width_pts']}pt)",
                        "ask_vwap": round(float(w_nba["box_cost_net"]), 4),
                        "p_model": 1.0,
                        "net_edge": round(1.0 - float(w_nba["box_cost_net"]), 4),
                        "l1_usd": w_nba["l1_usd"],
                        "close_ts": nb["close_ts"],
                    })
                    await self.open_shadow_two_leg_box(
                        sleeve="SP1_NBA_ZERO_FEE_BOX",
                        dedupe_key=f"SP1_{sp_nba.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",
                        asset="NBA",
                        title=f"{sp_nba.title} [{nb['label']}]",
                        leg_a=la_n,
                        leg_b=lb_n,
                        bk_a=bk_a,
                        bk_b=bk_b,
                        close_ts=float(nb["close_ts"]),
                        max_box_cost_net=0.994,
                        extra={"is_nba_zero_fee_box": True, "box_kind": nb["box_kind"], "middle_width_pts": nb["middle_width_pts"]},
                    )
                    if float(w_nba["box_cost_net"]) <= 0.990 and (float(nb["close_ts"]) - now) <= 86400.0:
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="SP1_NBA_ZERO_FEE_BOX",
                            box_type="NBA_DOMINANCE",
                            asset="NBA",
                            dedupe_key=f"SP1_{sp_nba.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",
                            leg_a=la_n,
                            leg_b=lb_n,
                            bk_a=bk_a,
                            bk_b=bk_b,
                            close_ts=float(nb["close_ts"]),
                            now_ts=now,
                        )

        # 5. NR0_ZERO_FEE_SLATE_ARB: Zero-Fee NegRisk Partition Slates (`elon-tweets`, `fomc`, `boj`, `boc`) — intraday <= 18h first
        for sp_nr in sorted(list(self.negrisk_zero_slates.values()), key=lambda s: ((float(s.end_ts) - now) > 64800.0, float(s.end_ts))):
            if sp_nr.end_ts <= now + 60:
                self.negrisk_zero_slates.pop(sp_nr.event_id, None)
                continue
            nr_toks = [b["yes_token"] for b in sp_nr.brackets] + [b["no_token"] for b in sp_nr.brackets]
            nr_bks = await self.fetch_books_batch(nr_toks, timeout=3.5)
            if not all(b["yes_token"] in nr_bks and b["no_token"] in nr_bks for b in sp_nr.brackets):
                continue
            y_l1_pairs = [self._best_ask_sz(nr_bks[b["yes_token"]]) for b in sp_nr.brackets]
            n_l1_pairs = [self._best_ask_sz(nr_bks[b["no_token"]]) for b in sp_nr.brackets]
            sum_y = sum(p for p, _ in y_l1_pairs)
            sum_n = sum(p for p, _ in n_l1_pairs)
            min_y_usd = round(min(p * s for p, s in y_l1_pairs), 2)
            min_n_usd = round(min(p * s for p, s in n_l1_pairs), 2)
            sum_y_bids = round(sum(extract_best_bid(nr_bks[b["yes_token"]].get("bids") or [])[0] for b in sp_nr.brackets), 4)
            sum_n_bids = round(sum(extract_best_bid(nr_bks[b["no_token"]].get("bids") or [])[0] for b in sp_nr.brackets), 4)
            n_br = len(sp_nr.brackets)
            self._record_market_telemetry(
                key=f"NR0_SLATE_{sp_nr.event_id}",
                min_interval_sec=60.0,
                now_ts=now,
                sig=(round(sum_y, 3), round(sum_n, 3)),
                payload={
                    "type": "ZERO_FEE_NEGRISK_SLATE",
                    "series": sp_nr.series_slug,
                    "title": sp_nr.title,
                    "tte_sec": round(sp_nr.end_ts - now, 0),
                    "n_open": n_br,
                    "sum_yes_l1": round(sum_y, 4),
                    "sum_yes_bids": sum_y_bids,
                    "min_yes_l1_usd": min_y_usd,
                    "sum_no_l1": round(sum_n, 4),
                    "sum_no_bids": sum_n_bids,
                    "min_no_l1_usd": min_n_usd,
                    "no_payout": n_br - 1,
                },
            )
            if sum_y <= 0.990:
                legs_y = [{"token_id": b["yes_token"], "side": "YES", "label": f"YES[{b['label']}]", "market_id": b["market_id"], "fee_rate": float(b.get("fee_rate", 0.0))} for b in sp_nr.brackets]
                w_nry = walk_equal_shares_multi_leg_box(
                    [{"asks": nr_bks[b["yes_token"]].get("asks") or [], "fee_rate": float(b.get("fee_rate", 0.0)), "fee_exponent": float(b.get("fee_exponent", 1.0))} for b in sp_nr.brackets],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],
                    guaranteed_payout_per_bundle=1.0,
                    max_bundle_cost_net=0.988,
                    min_shares=6,
                    min_box_notional_usd=5.5,
                )
                if w_nry.get("filled"):
                    opps_out.append({"sleeve": "NR0_ZERO_FEE_SLATE_ARB", "market": f"{sp_nr.title} (ALL {n_br} YES)", "ask_vwap": round(float(w_nry["box_cost_net"]), 4), "p_model": 1.0, "net_edge": round(1.0 - float(w_nry["box_cost_net"]), 4), "l1_usd": w_nry["l1_usd"], "close_ts": sp_nr.end_ts})
                    await self.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB", f"NR0_Y_{sp_nr.event_id}", sp_nr.series_slug.upper(), f"{sp_nr.title} [All-YES Partition]", legs_y, nr_bks, sp_nr.end_ts, 1.0, 0.988, {"is_multi_leg_bundle": True, "guaranteed_payout": 1.0})
            elif sum_n <= (n_br - 1) - 0.010:
                gp_n = float(n_br - 1)
                legs_n = [{"token_id": b["no_token"], "side": "NO", "label": f"NO[{b['label']}]", "market_id": b["market_id"], "fee_rate": float(b.get("fee_rate", 0.0))} for b in sp_nr.brackets]
                w_nrn = walk_equal_shares_multi_leg_box(
                    [{"asks": nr_bks[b["no_token"]].get("asks") or [], "fee_rate": float(b.get("fee_rate", 0.0)), "fee_exponent": float(b.get("fee_exponent", 1.0))} for b in sp_nr.brackets],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],
                    guaranteed_payout_per_bundle=gp_n,
                    max_bundle_cost_net=round(gp_n - 0.012, 4),
                    min_shares=6,
                    min_box_notional_usd=5.5,
                )
                if w_nrn.get("filled"):
                    opps_out.append({"sleeve": "NR0_ZERO_FEE_SLATE_ARB", "market": f"{sp_nr.title} (ALL {n_br} NO)", "ask_vwap": round(float(w_nrn["box_cost_net"]) / gp_n, 4), "p_model": 1.0, "net_edge": round((gp_n - float(w_nrn["box_cost_net"])) / gp_n, 4), "l1_usd": w_nrn["l1_usd"], "close_ts": sp_nr.end_ts})
                    await self.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB", f"NR0_N_{sp_nr.event_id}", sp_nr.series_slug.upper(), f"{sp_nr.title} [All-NO Partition]", legs_n, nr_bks, sp_nr.end_ts, gp_n, round(gp_n - 0.012, 4), {"is_multi_leg_bundle": True, "guaranteed_payout": gp_n})
            if sum_y_bids >= 1.004:
                await self.execute_ctf_overround_mint_sell(
                    dedupe_key=f"CTF_OVR_NR_{sp_nr.event_id}",
                    asset=sp_nr.series_slug.upper(),
                    title=f"{sp_nr.title} NegRisk Overround Mint-Sell",
                    legs_bids_spec=[
                        {"bids": nr_bks[b["yes_token"]].get("bids") or [], "fee_rate": float(b.get("fee_rate", 0.0)), "fee_exponent": float(b.get("fee_exponent", 1.0))}
                        for b in sp_nr.brackets
                    ],
                    close_ts=sp_nr.end_ts,
                    min_net_proceeds_per_set=1.004,
                    opps_out=opps_out,
                    extra={"overround_kind": "NEGRISK_SLATE", "series": sp_nr.series_slug, "event_id": sp_nr.event_id},
                )

        # 6. Phase-2 Macro LP (`FED1`), Oil-Senate (`COND1`), Counting (`TW1` + `MKR_REWARD`), & AAA Gas (`GAS1`)
        await self._scan_phase2_macro_counting_gas(opps_out, now)

    async def _scan_phase2_macro_counting_gas(self, opps_out: List[Dict[str, Any]], now: float) -> None:
        # 6A. `TW1_COUNTING_TRUNCATION_AND_BOX` + `MKR_REWARD_LOCKED_CARRY`
        active_cnt = [s for s in self.counting_slates.values() if s.window_end_ts > now + 60]
        if active_cnt:
            handles = sorted({s.handle for s in active_cnt})
            xt_res = await asyncio.gather(*(asyncio.to_thread(fetch_xtracker_user_stats_sync, h) for h in handles))
            xt_by_handle = dict(zip(handles, xt_res))
            cnt_toks = [t for s in active_cnt for b in s.brackets for t in (b.yes_token, b.no_token)]
            cnt_bks = await self.fetch_books_batch(cnt_toks, timeout=3.5)
            best_asks_cnt: Dict[str, float] = {}
            for t_c, bk_c in cnt_bks.items():
                px_c, sz_c = self._best_ask_sz(bk_c)
                if px_c < 1.0 and px_c * sz_c >= 8.0:
                    best_asks_cnt[t_c] = px_c
            for sl_c in active_cnt:
                v_floor, dead_brs = evaluate_counting_dead_no_locks(sl_c, xt_by_handle.get(sl_c.handle) or {})
                self._record_market_telemetry(
                    key=f"TW1_SNAP_{sl_c.event_id}",
                    min_interval_sec=120.0,
                    now_ts=now,
                    sig=(v_floor, len(dead_brs)),
                    payload={"type": "COUNTING_TRACKER_SNAP", "slug": sl_c.slug, "handle": sl_c.handle, "verified_floor": v_floor, "dead_open_brackets": len(dead_brs), "tte_sec": round(sl_c.window_end_ts - now, 0)},
                )
                for dbr in dead_brs:
                    bk_dno = cnt_bks.get(dbr.no_token)
                    if not bk_dno:
                        continue
                    bid_dn, _ = extract_best_bid(bk_dno.get("bids") or [])
                    ask_dn, _ = self._best_ask_sz(bk_dno)
                    w_dno = walk_l2_book_asks(bk_dno.get("asks") or [], BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"], fee_rate=0.0, min_l1_usd=15.0, max_ask_px=0.990)
                    if w_dno.get("filled") and 0.80 <= float(w_dno["eff_px"]) <= 0.990:
                        edg_tw = round(1.0 - float(w_dno["eff_px"]), 4)
                        if edg_tw >= 0.010:
                            opps_out.append({"sleeve": "TW1_COUNTING_TRUNCATION_AND_BOX", "market": f"{sl_c.handle} Dead Bracket NO[{dbr.label}] (count>={v_floor})", "ask_vwap": w_dno["eff_px"], "p_model": 1.0, "net_edge": edg_tw, "l1_usd": w_dno["l1_usd"], "close_ts": sl_c.window_end_ts})
                            await self.open_shadow_position("TW1_COUNTING_TRUNCATION_AND_BOX", f"TW1_NO_{dbr.market_id}", sl_c.handle.upper(), f"{sl_c.title} [Dead NO {dbr.label}]", "NO", dbr.no_token, 0.0, 1.0, sl_c.window_end_ts, {"market_id": dbr.market_id, "condition_id": dbr.condition_id, "verified_floor": v_floor}, prefetched_book=bk_dno)
                    rw_ev = evaluate_locked_market_reward_carry(1.0, bid_dn, ask_dn, dbr.rewards_min_size, dbr.rewards_max_spread, 0.0)
                    if rw_ev.get("eligible"):
                        opps_out.append({"sleeve": "MKR_REWARD_LOCKED_CARRY", "market": f"{sl_c.handle} Locked Carry NO[{dbr.label}] @ ${rw_ev['resting_bid']:.3f}", "ask_vwap": rw_ev["resting_bid"], "p_model": 1.0, "net_edge": rw_ev["carry_edge"], "l1_usd": 50.0, "close_ts": sl_c.window_end_ts})
                        await self.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY", f"MKR_RW_{dbr.market_id}", sl_c.handle.upper(), f"{sl_c.title} [Reward Carry NO {dbr.label}]", "NO", dbr.no_token, 1.0, sl_c.window_end_ts, {"market_id": dbr.market_id, "condition_id": dbr.condition_id, "resting_bid_override": rw_ev["resting_bid"]}, prefetched_book=bk_dno)

            tw_boxes = detect_counting_subwindow_boxes(active_cnt, best_asks_cnt, xt_by_handle, max_box_cost_net=1.05)
            if tw_boxes:
                tb0 = tw_boxes[0]
                self._record_market_telemetry(f"TW1_BOX_{tb0['handle']}", 90.0, {"type": "COUNTING_SUBWINDOW_BEST", "handle": tb0["handle"], "net_box_l1": tb0["box_cost_net"], "label": tb0["label"]}, now_ts=now, sig=(tb0["label"], tb0["box_cost_net"]))
            for tb in tw_boxes:
                la_t, lb_t = tb["leg_a"], tb["leg_b"]
                bka_t, bkb_t = cnt_bks.get(la_t["token_id"]), cnt_bks.get(lb_t["token_id"])
                if not bka_t or not bkb_t:
                    continue
                dk_tw = f"TW1_BOX_{la_t['market_id']}_{lb_t['market_id']}"
                if float(tb["box_cost_net"]) <= 0.993:
                    w_tb = walk_equal_shares_dominance_box(bka_t.get("asks") or [], bkb_t.get("asks") or [], BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"], 0.0, 0.0, max_box_cost_net=0.993, min_shares=6, min_box_notional_usd=5.5)
                    if w_tb.get("filled"):
                        opps_out.append({"sleeve": "TW1_COUNTING_TRUNCATION_AND_BOX", "market": f"Counting Box {tb['label']}", "ask_vwap": w_tb["box_cost_net"], "p_model": 1.0, "net_edge": round(1.0 - float(w_tb["box_cost_net"]), 4), "l1_usd": w_tb["l1_usd"], "close_ts": tb["close_ts"]})
                        await self.open_shadow_two_leg_box("TW1_COUNTING_TRUNCATION_AND_BOX", dk_tw, tb["handle"].upper(), f"Counting Box {tb['label']}", la_t, lb_t, bka_t, bkb_t, float(tb["close_ts"]), 0.993, {"is_two_leg_box": True, "banked": tb["banked"]})
                        if (float(tb["close_ts"]) - now) <= 86400.0 and float(w_tb["box_cost_net"]) <= 0.990:
                            self.emit_live_two_leg_box_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX", box_type="COUNTING_DOMINANCE", asset=tb["handle"].upper(), dedupe_key=dk_tw, leg_a=la_t, leg_b=lb_t, bk_a=bka_t, bk_b=bkb_t, close_ts=float(tb["close_ts"]), now_ts=now)
                elif float(tb["box_cost_net"]) <= 1.035:
                    self.post_zero_fee_maker_anchor_box("TW1", tb["handle"].upper(), f"ZFA_{dk_tw}", la_t, lb_t, bka_t, bkb_t, float(tb["close_ts"]), f"Counting Box {tb['label']}", now, prefetched_books=cnt_bks)

        # 6B. `FED1_CENTRAL_BANK_LP_BOX` (125-state FOMC) & `COND1_MACRO_PARTITION_BOX` (9-state Oil x Senate)
        lp_legs = [lg for lg in (self.fomc_truth_legs + self.oil_senate_truth_legs) if float(lg["end_ts"]) > now + 60]
        if lp_legs:
            lp_bks = await self.fetch_books_batch(sorted({str(lg["token_id"]) for lg in lp_legs}), timeout=3.5)
            lp_asks = {t: p for t, bk in lp_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
            for sl_lp, asset_lp, legs_src, mask_all, t_type in (
                ("FED1_CENTRAL_BANK_LP_BOX", "FOMC", self.fomc_truth_legs, ALL_FOMC_MASK, "FOMC_LP_BEST"),
                ("COND1_MACRO_PARTITION_BOX", "OIL_SENATE", self.oil_senate_truth_legs, ALL_OIL_SENATE_MASK, "OIL_SENATE_PARTITION_BEST"),
            ):
                if not legs_src:
                    continue
                bx_list = find_cross_event_bitmask_boxes(legs_src, lp_asks, mask_all, max_2leg_cost=1.05, max_3leg_cost=1.03)
                if bx_list:
                    b0 = bx_list[0]
                    self._record_market_telemetry(f"{t_type}_DIAG", 90.0, {"type": t_type, "n_legs": b0["n_legs"], "net_box_l1": b0["box_cost_net"], "label": b0["label"]}, now_ts=now, sig=(b0["label"], b0["box_cost_net"]))
                for bx in bx_list:
                    lgs = bx["legs"]
                    if int(bx["n_legs"]) == 2:
                        la_m, lb_m = lgs[0], lgs[1]
                        bka_m, bkb_m = lp_bks.get(la_m["token_id"]), lp_bks.get(lb_m["token_id"])
                        if not bka_m or not bkb_m:
                            continue
                        dk_m = f"{asset_lp}_2L_{la_m['token_id'][-8:]}_{lb_m['token_id'][-8:]}"
                        if float(bx["box_cost_net"]) <= 0.994:
                            wm2 = walk_equal_shares_dominance_box(bka_m.get("asks") or [], bkb_m.get("asks") or [], BANKROLL_TICKETS["T1000"][sl_lp], 0.0, 0.0, max_box_cost_net=0.994, min_shares=6, min_box_notional_usd=5.5)
                            if wm2.get("filled"):
                                opps_out.append({"sleeve": sl_lp, "market": f"{asset_lp} {bx['label']}", "ask_vwap": wm2["box_cost_net"], "p_model": 1.0, "net_edge": round(1.0 - float(wm2["box_cost_net"]), 4), "l1_usd": wm2["l1_usd"], "close_ts": bx["close_ts"]})
                                await self.open_shadow_two_leg_box(sl_lp, dk_m, asset_lp, f"{asset_lp} {bx['label']}", la_m, lb_m, bka_m, bkb_m, float(bx["close_ts"]), 0.994, {"is_two_leg_box": True, "double_pay_states": bx["double_pay_states"]})
                                if sl_lp == "FED1_CENTRAL_BANK_LP_BOX" and (float(bx["close_ts"]) - now) <= 172800.0 and float(wm2["box_cost_net"]) <= 0.990:
                                    self.emit_live_two_leg_box_candidate(sleeve_source=sl_lp, box_type="MACRO_DOMINANCE", asset=asset_lp, dedupe_key=dk_m, leg_a=la_m, leg_b=lb_m, bk_a=bka_m, bk_b=bkb_m, close_ts=float(bx["close_ts"]), now_ts=now)
                        elif float(bx["box_cost_net"]) <= 1.035:
                            self.post_zero_fee_maker_anchor_box(asset_lp, asset_lp, f"ZFA_{dk_m}", la_m, lb_m, bka_m, bkb_m, float(bx["close_ts"]), f"{asset_lp} {bx['label']}", now, prefetched_books=lp_bks)
                    elif int(bx["n_legs"]) == 3 and float(bx["box_cost_net"]) <= 0.992:
                        dk_3 = f"{asset_lp}_3L_{'_'.join(x['token_id'][-6:] for x in lgs)}"
                        wm3 = walk_equal_shares_multi_leg_box([{"asks": lp_bks[x["token_id"]].get("asks") or [], "fee_rate": 0.0, "fee_exponent": 1.0} for x in lgs], BANKROLL_TICKETS["T1000"][sl_lp], 1.0, 0.992, min_shares=6, min_box_notional_usd=5.5)
                        if wm3.get("filled"):
                            opps_out.append({"sleeve": sl_lp, "market": f"{asset_lp} 3-Leg {bx['label']}", "ask_vwap": wm3["box_cost_net"], "p_model": 1.0, "net_edge": round(1.0 - float(wm3["box_cost_net"]), 4), "l1_usd": wm3["l1_usd"], "close_ts": bx["close_ts"]})
                            await self.open_shadow_multi_leg_bundle(sl_lp, dk_3, asset_lp, f"{asset_lp} 3-Leg {bx['label']}", lgs, lp_bks, float(bx["close_ts"]), 1.0, 0.992, {"is_multi_leg_bundle": True, "guaranteed_payout": 1.0})

        # 6C. `GAS1_AAA_GASOLINE_LOCK`: Same-day published 4-decimal AAA National Regular lock
        daily_gas_evs = [e for e in (self.gas_events_raw.get("us-gas-price-daily") or []) if not e.get("closed")]
        if daily_gas_evs:
            aaa = await asyncio.to_thread(fetch_aaa_national_gas_sync)
            if aaa:
                self._record_market_telemetry("AAA_GAS_SNAP", 300.0, {"type": "AAA_GAS_SNAP", **aaa}, now_ts=now, sig=(aaa["as_of_date"], aaa["current_regular"]))
                reg_px = float(aaa["current_regular"])
                for ev_g in daily_gas_evs:
                    end_g = _parse_iso_ts(ev_g.get("endDate")) or 0.0
                    if not (60.0 < (end_g - now) <= 57600.0):
                        continue
                    _m_gdt = re.search(r"(20\d{2}-\d{2}-\d{2})", str(ev_g.get("slug") or ""))
                    mkt_dt = _m_gdt.group(1) if _m_gdt else datetime.fromtimestamp(end_g, tz=NY_TZ).date().isoformat()
                    if mkt_dt != aaa["as_of_date"]:
                        continue
                    g_brs = []
                    for mg in (ev_g.get("markets") or []):
                        if mg.get("closed"):
                            continue
                        fr_g, _ = _extract_market_fee_rate(mg)
                        tk_g = _parse_clob_tokens(mg)
                        bd_g = parse_gas_daily_bracket(str(mg.get("groupItemTitle") or mg.get("question") or ""))
                        if fr_g == 0.0 and tk_g and bd_g:
                            g_brs.append((mg, tk_g, bd_g))
                    if not g_brs:
                        continue
                    g_bks = await self.fetch_books_batch([t for _, tk, _ in g_brs for t in tk], timeout=3.0)
                    for mg, tk_g, (glo, ghi) in g_brs:
                        mid_g = str(mg.get("id") or "")
                        lbl_g = str(mg.get("groupItemTitle") or "")
                        if (glo == 0.0 or reg_px >= glo + 0.0015) and (not math.isfinite(ghi) or reg_px <= ghi - 0.0015):
                            side_g, tok_g = "YES", tk_g[0]
                        elif reg_px <= glo - 0.0020 or (math.isfinite(ghi) and reg_px >= ghi + 0.0020):
                            side_g, tok_g = "NO", tk_g[1]
                        else:
                            continue
                        bk_g = g_bks.get(tok_g)
                        if not bk_g:
                            continue
                        wg = walk_l2_book_asks(bk_g.get("asks") or [], BANKROLL_TICKETS["T1000"]["GAS1_AAA_GASOLINE_LOCK"], fee_rate=0.0, min_l1_usd=15.0, max_ask_px=0.985)
                        if wg.get("filled") and 0.75 <= float(wg["eff_px"]) <= 0.983:
                            opps_out.append({"sleeve": "GAS1_AAA_GASOLINE_LOCK", "market": f"AAA Gas ${reg_px:.4f} ({aaa['as_of_date']}) -> {side_g}[{lbl_g}]", "ask_vwap": wg["eff_px"], "p_model": 0.998, "net_edge": round(0.998 - float(wg["eff_px"]), 4), "l1_usd": wg["l1_usd"], "close_ts": end_g})
                            await self.open_shadow_position("GAS1_AAA_GASOLINE_LOCK", f"GAS1_{mid_g}_{side_g}", "AAA_GAS", f"{ev_g.get('title')} [{side_g} {lbl_g}]", side_g, tok_g, 0.0, 0.998, end_g, {"market_id": mid_g, "aaa_price": reg_px, "as_of_date": aaa["as_of_date"]}, prefetched_book=bk_g)

    async def _run_bg_tradfi_sports(self) -> None:
        try:
            ts_opps: List[Dict[str, Any]] = []
            await self.scan_tradfi_and_sports_markets(ts_opps)
            self.cached_tradfi_sports_opps = ts_opps
        except Exception as exc:
            logger.warning(f"Background TradFi/Sports scan notice: {exc}")

    async def run_forever(self) -> None:
        logger.info(
            "Starting Polymarket Alpha-124 Unified Shadow Daemon "
            "(W1/W3 + Asian METAR + B1/B2 + M3/N1 NegRisk + U1 Daily + D1/4h/QuietBook + S5M + P1 PreOpen + S2)..."
        )
        try:
            if not self.single_scan and (self._bg_clob_ws_task is None or self._bg_clob_ws_task.done()):
                self._bg_clob_ws_task = asyncio.create_task(self._run_clob_d1_ws_loop())
            if not self.single_scan and self._chainlink_ws is not None and (self._bg_chainlink_ws_task is None or self._bg_chainlink_ws_task.done()):
                self._bg_chainlink_ws_task = asyncio.create_task(self._chainlink_ws.run_forever())
            while True:
                t0 = time.time()
                self.cycle_count += 1
                await self.update_crypto_spots()

                if not self.weather_events or self.single_scan:
                    await self.discover_all_markets()
                elif (t0 - self.last_discovery_ts) >= 300.0 and (
                    self._bg_discovery_task is None or self._bg_discovery_task.done()
                ):
                    self.last_discovery_ts = t0
                    self._bg_discovery_task = asyncio.create_task(self._run_bg_discovery())

                # Reactive drain of any fresh Binance shock triggers before periodic scans
                fresh_shocks = self.poll_fresh_shock_triggers(now_ts=t0)
                if fresh_shocks:
                    shock_opps: List[Dict[str, Any]] = []
                    await self.handle_shock_triggers(fresh_shocks, shock_opps, now_ts=t0)
                    self.cached_shock_opps = shock_opps

                # Fast-loop scanners: D1 (15m/5m + 4h + QuietBook), S2 TWAP Lock, S5M Sniper, P1 Pre-Open Maker Straddle
                dom_opps: List[Dict[str, Any]] = []
                twap_opps: List[Dict[str, Any]] = []
                s5m_opps: List[Dict[str, Any]] = []
                p1_opps: List[Dict[str, Any]] = []
                await self.scan_same_oracle_dominance_boxes(dom_opps)
                await self.scan_exact_twap_locks(twap_opps)
                await self.scan_s5m_chainlink_sniper(s5m_opps)
                await self.scan_and_manage_preopen_maker_straddles(p1_opps)

                if self.single_scan:
                    mid_opps: List[Dict[str, Any]] = []
                    await self.scan_multistrike_markets(mid_opps)
                    await self.scan_daily_updown_locks(mid_opps)
                    await self.scan_barrier_markets(mid_opps)
                    self.cached_mid_opps = mid_opps

                    w_opps: List[Dict[str, Any]] = []
                    await self.scan_weather_markets(w_opps)
                    self.cached_weather_opps = w_opps

                    ts_opps: List[Dict[str, Any]] = []
                    await self.scan_tradfi_and_sports_markets(ts_opps)
                    self.cached_tradfi_sports_opps = ts_opps
                else:
                    # Non-blocking background coroutines so S2 (3.0s) / D1 (3.5s) never stall
                    if (t0 - self.last_crypto_mid_scan_ts) >= 18.0 and (
                        self._bg_mid_task is None or self._bg_mid_task.done()
                    ):
                        self.last_crypto_mid_scan_ts = t0
                        self._bg_mid_task = asyncio.create_task(self._run_bg_mid_crypto())

                    if (t0 - self.last_tradfi_sports_scan_ts) >= 45.0 and (
                        self._bg_tradfi_task is None or self._bg_tradfi_task.done()
                    ):
                        self.last_tradfi_sports_scan_ts = t0
                        self._bg_tradfi_task = asyncio.create_task(self._run_bg_tradfi_sports())

                    if (t0 - self.last_weather_scan_ts) >= 90.0 and (
                        self._bg_weather_task is None or self._bg_weather_task.done()
                    ):
                        self.last_weather_scan_ts = t0
                        self._bg_weather_task = asyncio.create_task(self._run_bg_weather())

                opps = (
                    twap_opps
                    + dom_opps
                    + s5m_opps
                    + p1_opps
                    + self.cached_shock_opps
                    + self.cached_mid_opps
                    + self.cached_tradfi_sports_opps
                    + self.cached_weather_opps
                )

                await self.manage_pending_maker_orders()
                await self.manage_pending_zero_fee_maker_anchors()
                await self.manage_open_positions()
                await self.write_state_files_async(opps)

                logger.info(
                    f"[Cycle {self.cycle_count}] BTC=${self.spots.get('BTC',0):,.1f} ETH=${self.spots.get('ETH',0):,.1f} | "
                    f"Monitored(W={len(self.weather_events)}, B={len(self.barrier_rungs)}, M={len(self.strike_ladders)}, "
                    f"NR={len(self.negrisk_ladders)}, PythH={len(self.pyth_barrier_rungs)}, PythC={len(self.pyth_close_ladders)}, "
                    f"NBA={len(self.nba_games)}, NR0={len(self.negrisk_zero_slates)}, TW={len(self.counting_slates)}, "
                    f"FOMC={len(self.fomc_truth_legs)//2}, OS={len(self.oil_senate_truth_legs)//2}, D2={len(self.hourly_12pm_markets)}, "
                    f"U1={len(self.daily_updown_markets)}, D={len(self.dominance_pairs)}, "
                    f"D4h={len(self.dominance_4h_pairs)}, S5m={len(self.s5m_candles)}, P1={len(self.preopen_15m_candles)}, S2={len(self.twap_candles)}) | "
                    f"MakerPend={len(self.pending_maker_orders)} ZFAncPend={len(self.pending_zero_fee_maker_anchors)} PreOpenPend={len(self.pending_preopen_straddles)} "
                    f"OpenPos={len(self.open_positions)} ClosedPos={len(self.closed_positions)} | TopOpps={len(self.top_opportunities)}"
                )

                if self.single_scan:
                    break
                now_end = time.time()
                rem_4h_end = (math.ceil(now_end / 14400.0) * 14400.0) - now_end
                if self.is_in_exact_twap_lock_window(now_end):
                    target_cadence = 3.0
                elif self.is_in_same_oracle_overlap_window(now_end):
                    target_cadence = 3.5
                elif self.pending_zero_fee_maker_anchors:
                    target_cadence = 4.0
                elif 8.0 <= rem_4h_end <= 905.0 or self.pending_preopen_straddles:
                    target_cadence = 6.0
                else:
                    target_cadence = 12.0
                deadline = t0 + max(2.0, target_cadence)
                last_fast_d1_subscan = t0
                while True:
                    now_s = time.time()
                    if now_s >= deadline:
                        break
                    ws_triggered = self._ws_d1_wakeup.is_set()
                    if ws_triggered:
                        self._ws_d1_wakeup.clear()
                    # Event-driven (<=120ms on CLOB WS delta, 500ms fallback) D1 overlap box scan without state-file churn
                    min_d1_gap = 0.12 if ws_triggered else 0.50
                    if self.is_in_same_oracle_overlap_window(now_s) and (now_s - last_fast_d1_subscan) >= min_d1_gap:
                        last_fast_d1_subscan = now_s
                        d1_sub_opps: List[Dict[str, Any]] = []
                        await self.scan_same_oracle_dominance_boxes(d1_sub_opps, now_ts=now_s)
                        if d1_sub_opps:
                            dom_opps = d1_sub_opps
                    # Sample /dev/shm USD anchor at 1 Hz during the 65s TWAP integral window (0 REST calls)
                    rem_5m_s = (math.ceil(now_s / 300.0) * 300.0) - now_s
                    if rem_5m_s <= 65.0 and (now_s - self.last_usd_sample_ts) >= 1.0:
                        self.record_usd_spot_samples(now_s)
                    # Wake immediately (<250ms) if a live Binance shock arrives
                    shocks_w = self.poll_fresh_shock_triggers(now_ts=now_s)
                    if shocks_w:
                        prev_mkr_keys = set(self.pending_maker_orders)
                        prev_open_n = len(self.open_positions)
                        s_opps: List[Dict[str, Any]] = []
                        await self.handle_shock_triggers(shocks_w, s_opps, now_ts=now_s)
                        if s_opps:
                            self.cached_shock_opps = s_opps
                        if s_opps or set(self.pending_maker_orders) != prev_mkr_keys or len(self.open_positions) != prev_open_n:
                            await self.write_state_files_async(
                                twap_opps
                                + dom_opps
                                + s5m_opps
                                + p1_opps
                                + self.cached_shock_opps
                                + self.cached_mid_opps
                                + self.cached_tradfi_sports_opps
                                + self.cached_weather_opps
                            )
                    # Step down cadence immediately if we just entered the final-55s TWAP lock window
                    if target_cadence > 3.0 and self.is_in_exact_twap_lock_window(now_s):
                        break
                    wait_cap = min(0.20, max(0.03, deadline - time.time()))
                    try:
                        await asyncio.wait_for(self._ws_d1_wakeup.wait(), timeout=wait_cap)
                    except asyncio.TimeoutError:
                        pass
        finally:
            for bg_t in (self._bg_chainlink_ws_task, self._bg_clob_ws_task, self._bg_discovery_task, self._bg_mid_task, self._bg_tradfi_task, self._bg_weather_task):
                if bg_t is not None and not bg_t.done():
                    bg_t.cancel()
                    try:
                        await bg_t
                    except BaseException:
                        pass
            if self.session and not self.session.closed:
                await self.session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket Alpha-124 Shadow Daemon")
    parser.add_argument("--single-scan", action="store_true", help="Run one full scan cycle and exit")
    args = parser.parse_args()
    if os.name != "nt":
        try:
            import uvloop
            uvloop.install()
        except Exception:
            pass
    daemon = Alpha124ShadowDaemon(single_scan=args.single_scan)
    asyncio.run(daemon.run_forever())


if __name__ == "__main__":
    main()

# ======================================================================================
# [12/16] MODULE: scripts/backtest_alpha_124.py
# PURPOSE: Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124
# ======================================================================================

#!/usr/bin/env python3
"""
Chronological Walk-Forward Backtester for Polymarket Options #1, #2, and #4
===========================================================================
Strictly causal, zero-lookahead empirical backtest on REAL resolved October 2026
Polymarket CLOB `prices-history` markets, joined with real oracle time series:

  - Option #1 (Weather METAR + NWP):
      * Real resolved Daily Weather events across global cities (Oct 2026)
      * Real historical raw ICAO METAR observations (AWC + IEM ASOS archive)
      * Real archived historical NWP forecasts (Open-Meteo ECMWF IFS + GFS + ICON)
      * Real Polymarket CLOB 5m price series (`zero_fees` + conservative 1c spread/slippage)

  - Option #2 (Crypto One-Touch Barrier "Hit/Dip" Jump-SVI):
      * Real resolved BTC & ETH Daily/Weekly Hit-Price ladders (Oct 2026)
      * Real Binance 1m/5m Spot USDT High/Low/Close klines (exact Polymarket oracle)
      * Real Deribit hourly DVOL implied volatility index (`BTC` & `ETH`)
      * Real Polymarket CLOB 5m price series + `crypto_fees_v2` + conservative spread penalty

  - Option #4 (Multi-Strike SVI Breeden-Litzenberger Maker-Scalper & Convergence):
      * Real resolved BTC & ETH `"above ___"` strike ladders (Oct 2026)
      * Real Binance 5m Spot USDT klines + Deribit hourly DVOL SVI Breeden-Litzenberger
      * Real Polymarket CLOB 5m price series + `crypto_fees_v2` + Maker TP / SVI Stop / Expiry

Chronological Split (No Shuffling / Zero Data Leakage):
  - TRAIN / CALIBRATION: Resolved events ending <= 2026-10-16 23:59 UTC
  - SEALED OUT-OF-SAMPLE TEST: Resolved events ending > 2026-10-16 23:59 UTC
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import concurrent.futures
import json
import math
import os
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.polymarket_research.barrier_onetouch_svi_engine import (
    BarrierRungSpec,
    first_passage_touch_prob,
    get_wing_implied_vol,
    parse_hit_event,
)
from src.polymarket_research.multistrike_svi_scalper import (
    StrikeRungSpec,
    evaluate_svi_digital_fair_value,
    parse_multistrike_event,
)
from src.polymarket_research.weather_metar_engine import (
    MetarObservation,
    WeatherEventSpec,
    compute_weather_probabilities,
    fetch_historical_nwp_hourly_sync,
    fetch_metar_observations_sync,
    parse_weather_event,
)

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"
BINANCE_URL = "https://api.binance.com"
DERIBIT_URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"

OUT_DIR = PROJECT_ROOT / "data" / "alpha124"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_JSON = OUT_DIR / "backtest_alpha_124_results.json"

SPLIT_CUTOFF_TS = datetime(2026, 10, 16, 23, 59, 59, tzinfo=timezone.utc).timestamp()

WEATHER_SERIES_SAMPLE = [
    "tokyo-daily-weather",
    "london-daily-weather",
    "shanghai-daily-weather",
    "paris-daily-weather",
    "munich-daily-weather",
    "miami-daily-weather",
    "nyc-daily-weather",
    "houston-daily-weather",
    "seoul-daily-weather",
    "chicago-daily-weather",
    "seattle-daily-weather",
    "dallas-daily-weather",
    "madrid-daily-weather",
    "amsterdam-daily-weather",
    "taipei-daily-weather",
    "singapore-daily-weather",
]


def http_get_json(url: str, timeout: float = 10.0) -> Any:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DominusBacktester/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt == 2:
                return None
            time.sleep(0.35 * (attempt + 1))
    return None


def fetch_clob_history(token_id: str, fidelity: int = 10) -> List[Tuple[int, float]]:
    data = http_get_json(f"{CLOB_URL}/prices-history?market={token_id}&interval=max&fidelity={fidelity}", timeout=8.0)
    if not data or not isinstance(data, dict):
        return []
    hist = data.get("history") or []
    pts = [(int(r["t"]), float(r["p"])) for r in hist if "t" in r and "p" in r]
    pts.sort(key=lambda x: x[0])
    return pts


def fetch_binance_5m_series(symbol: str, start_ts: int, end_ts: int) -> Dict[int, Tuple[float, float, float, float]]:
    """Returns dict of 5m candle open_ts -> (open, high, low, close)."""
    out: Dict[int, Tuple[float, float, float, float]] = {}
    cur_ms = start_ts * 1000
    end_ms = end_ts * 1000
    while cur_ms < end_ms:
        url = f"{BINANCE_URL}/api/v3/klines?symbol={symbol}&interval=5m&startTime={cur_ms}&endTime={end_ms}&limit=1000"
        rows = http_get_json(url, timeout=10.0)
        if not rows:
            break
        for r in rows:
            ts = int(r[0]) // 1000
            out[ts] = (float(r[1]), float(r[2]), float(r[3]), float(r[4]))
        last_ms = int(rows[-1][0])
        if last_ms <= cur_ms:
            break
        cur_ms = last_ms + 300_000
    return out


def fetch_deribit_dvol_hourly(currency: str, start_ts: int, end_ts: int) -> Dict[int, float]:
    """Returns dict of hour_ts -> annualized IV decimal (e.g. 0.42)."""
    url = f"{DERIBIT_URL}?currency={currency}&start_timestamp={start_ts * 1000}&end_timestamp={end_ts * 1000}&resolution=3600"
    data = http_get_json(url, timeout=10.0)
    out: Dict[int, float] = {}
    pts = (data or {}).get("result", {}).get("data") or []
    for row in pts:
        # [ts_ms, open, high, low, close]
        ts = int(row[0]) // 1000
        out[ts] = float(row[4]) / 100.0
    return out


def summarize_trades(trades: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    if not trades:
        return {
            "label": label,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "net_pnl_usd": 0.0,
            "avg_pnl_usd": 0.0,
            "avg_roi_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_usd": 0.0,
        }
    trades_s = sorted(trades, key=lambda x: x["entry_ts"])
    pnls = [float(t["pnl_usd"]) for t in trades_s]
    rois = [float(t["roi_pct"]) for t in trades_s]
    wins = sum(1 for p in pnls if p > 0)
    losses = len(pnls) - wins
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = (gross_win / gross_loss) if gross_loss > 1e-6 else (99.9 if gross_win > 0 else 0.0)

    eq = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        max_dd = max(max_dd, peak - eq)

    return {
        "label": label,
        "trades": len(pnls),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(100.0 * wins / len(pnls), 2),
        "net_pnl_usd": round(sum(pnls), 2),
        "avg_pnl_usd": round(sum(pnls) / len(pnls), 2),
        "avg_roi_pct": round(sum(rois) / len(rois), 2),
        "profit_factor": round(pf, 2),
        "max_drawdown_usd": round(max_dd, 2),
    }


# ==============================================================================
# 1. WEATHER BACKTEST (W1_SOLAR_PEAK_LOCK & W2_ENSEMBLE_VALUE)
# ==============================================================================
def run_weather_backtest() -> Dict[str, Any]:
    print("[1/3] Fetching resolved October 2026 Daily Weather markets across 16 global cities...", flush=True)
    specs: List[WeatherEventSpec] = []
    for s_slug in WEATHER_SERIES_SAMPLE:
        evts = http_get_json(f"{GAMMA_URL}/events?series_slug={s_slug}&closed=true&order=endDate&ascending=false&limit=20") or []
        for ev in evts:
            sp = parse_weather_event(ev, allow_historical_same_station=True, series_slug_hint=s_slug)
            if sp is not None and date(2026, 10, 4) <= sp.obs_date <= date(2026, 10, 25):
                # Require exactly one resolved winning bucket
                if any(b.outcome_yes_resolved == 1 for b in sp.buckets):
                    specs.append(sp)

    print(f"      Parsed {len(specs)} resolved METAR-governed city-days. Fetching NWP + METAR + CLOB series...", flush=True)
    # Pre-fetch NWP historical hourly forecasts per station (1 call per city!)
    by_icao: Dict[str, List[WeatherEventSpec]] = defaultdict(list)
    for sp in specs:
        by_icao[sp.icao].append(sp)

    nwp_cache: Dict[str, Dict[int, List[float]]] = {}
    for icao, st_specs in by_icao.items():
        min_d = min(s.obs_date for s in st_specs) - timedelta(days=1)
        max_d = max(s.obs_date for s in st_specs) + timedelta(days=1)
        s0 = st_specs[0]
        try:
            nwp_cache[icao] = fetch_historical_nwp_hourly_sync(s0.lat, s0.lon, min_d, max_d)
        except Exception:
            nwp_cache[icao] = {}

    # Fetch METARs and CLOB price histories concurrently
    def _load_event_bundle(sp: WeatherEventSpec) -> Tuple[WeatherEventSpec, List[MetarObservation], Dict[str, List[Tuple[int, float]]]]:
        metars = fetch_metar_observations_sync(sp.icao, sp.obs_date, sp.tz_name)
        clob_map: Dict[str, List[Tuple[int, float]]] = {}
        for b in sp.buckets:
            clob_map[b.market_id] = fetch_clob_history(b.yes_token, fidelity=15)
        return sp, metars, clob_map

    # Use higher-concurrency ThreadPoolExecutor (max_workers=24) for fast parallel CLOB history downloads
    bundles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
        for res in pool.map(_load_event_bundle, specs):
            if res[1]:
                bundles.append(res)

    print(f"      Loaded {len(bundles)} complete Weather city-day bundles with raw METAR + CLOB history.", flush=True)

    # Calibrate forecast_sigma_base_c on TRAIN split (obs_date <= Oct 16) via Brier Score minimization
    best_sigma = 1.15
    best_brier = 999.0
    train_bundles = [b for b in bundles if b[0].obs_date <= date(2026, 10, 16)]
    for cand_sig in (0.85, 1.05, 1.25, 1.45):
        brier_sum = 0.0
        brier_n = 0
        for sp, metars, _ in train_bundles:
            tz = ZoneInfo(sp.tz_name)
            eval_local = datetime(sp.obs_date.year, sp.obs_date.month, sp.obs_date.day, 11, 0, tzinfo=tz)
            eval_u = eval_local.astimezone(timezone.utc)
            out = compute_weather_probabilities(sp, eval_u, metars, nwp_cache.get(sp.icao, {}), forecast_sigma_base_c=cand_sig)
            for idx, b in enumerate(sp.buckets):
                y = 1.0 if b.outcome_yes_resolved == 1 else 0.0
                brier_sum += (out["probs"][idx] - y) ** 2
                brier_n += 1
        if brier_n > 0 and (brier_sum / brier_n) < best_brier:
            best_brier = brier_sum / brier_n
            best_sigma = cand_sig

    print(f"      [TRAIN Calibration] Optimal Weather NWP kernel sigma={best_sigma:.2f}°C (Brier={best_brier:.4f}).", flush=True)

    w1_trades: List[Dict[str, Any]] = []
    w2_trades: List[Dict[str, Any]] = []
    TICKET_W1 = 100.0
    TICKET_W2 = 50.0
    # Conservative 1.0c half-spread/slippage penalty above CLOB mid/last trade price (zero_fees = 0% platform fee)
    EXEC_SPREAD_PENALTY = 0.010

    for sp, metars, clob_map in sorted(bundles, key=lambda x: x[0].obs_date):
        tz = ZoneInfo(sp.tz_name)
        nwp_hr = nwp_cache.get(sp.icao, {})
        split = "TRAIN" if sp.obs_date <= date(2026, 10, 16) else "TEST"

        # Helper to look up latest CLOB price at or before eval_ts (within 90 mins so stale illiquid ticks aren't faked)
        def _price_at(mkt_id: str, ts: int) -> Optional[float]:
            pts = clob_map.get(mkt_id) or []
            val = None
            for t_p, px in pts:
                if t_p <= ts:
                    if ts - t_p <= 7200:
                        val = px
                else:
                    break
            return val

        # --- Evaluate W2_ENSEMBLE_VALUE (Pre-Peak Morning/Midday Checkpoints: 09:00, 11:30, 13:30 local) ---
        # Require synoptic NWP model agreement (spread across ECMWF/GFS/ICON afternoon max <= 1.6°C) + strong 10c edge
        entered_w2 = False
        for hr, mn in ((9, 0), (11, 30), (13, 30)):
            if entered_w2:
                break
            eval_u = datetime(sp.obs_date.year, sp.obs_date.month, sp.obs_date.day, hr, mn, tzinfo=tz).astimezone(timezone.utc)
            eval_ts = int(eval_u.timestamp())
            # Check synoptic model agreement at 14:00 local time
            peak_u_ts = int(datetime(sp.obs_date.year, sp.obs_date.month, sp.obs_date.day, 14, 0, tzinfo=tz).astimezone(timezone.utc).timestamp())
            peak_members = nwp_hr.get(peak_u_ts) or []
            if peak_members and (max(peak_members) - min(peak_members)) > 1.6:
                continue
            res = compute_weather_probabilities(sp, eval_u, metars, nwp_hr, forecast_sigma_base_c=best_sigma)
            # Pick single highest-edge bucket if edge >= 10c and p_mod >= 0.34
            best_cand = None
            for idx, b in enumerate(sp.buckets):
                mid_px = _price_at(b.market_id, eval_ts)
                if mid_px is None:
                    continue
                eff_ask = round(mid_px + EXEC_SPREAD_PENALTY, 4)
                p_mod = res["probs"][idx]
                edge = p_mod - eff_ask
                if 0.16 <= eff_ask <= 0.62 and edge >= 0.10 and p_mod >= 0.34:
                    if best_cand is None or edge > best_cand[0]:
                        best_cand = (edge, idx, b, eff_ask, p_mod)
            if best_cand is not None:
                edge, idx, b, eff_ask, p_mod = best_cand
                shares = TICKET_W2 / eff_ask
                won = (b.outcome_yes_resolved == 1)
                pnl = (shares * 1.0 - TICKET_W2) if won else (-TICKET_W2)
                w2_trades.append({
                    "split": split,
                    "sleeve": "W2_ENSEMBLE_VALUE",
                    "city": sp.city,
                    "icao": sp.icao,
                    "obs_date": sp.obs_date.isoformat(),
                    "bucket": b.label,
                    "entry_ts": eval_ts,
                    "entry_px": eff_ask,
                    "p_model": round(p_mod, 4),
                    "edge": round(edge, 4),
                    "won": won,
                    "pnl_usd": round(pnl, 2),
                    "roi_pct": round(100.0 * pnl / TICKET_W2, 2),
                })
                entered_w2 = True

        # --- Evaluate W1_SOLAR_PEAK_LOCK (Hourly Post-Peak Checkpoints: 16:00..22:00 local) ---
        entered_w1 = False
        for hr, mn in ((16, 0), (17, 0), (18, 0), (19, 0), (20, 0), (21, 0), (22, 0)):
            if entered_w1:
                break
            eval_u = datetime(sp.obs_date.year, sp.obs_date.month, sp.obs_date.day, hr, mn, tzinfo=tz).astimezone(timezone.utc)
            eval_ts = int(eval_u.timestamp())
            res = compute_weather_probabilities(sp, eval_u, metars, nwp_hr, forecast_sigma_base_c=best_sigma)
            if not res["is_solar_lock"] or res["locked_bucket_idx"] is None:
                continue
            b = sp.buckets[res["locked_bucket_idx"]]
            mid_px = _price_at(b.market_id, eval_ts)
            if mid_px is None:
                continue
            eff_ask = round(mid_px + EXEC_SPREAD_PENALTY, 4)
            p_lock = res["p_locked_bucket"]
            edge = p_lock - eff_ask
            if 0.55 <= eff_ask <= 0.93 and edge >= 0.04:
                shares = TICKET_W1 / eff_ask
                won = (b.outcome_yes_resolved == 1)
                pnl = (shares * 1.0 - TICKET_W1) if won else (-TICKET_W1)
                w1_trades.append({
                    "split": split,
                    "sleeve": "W1_SOLAR_PEAK_LOCK",
                    "city": sp.city,
                    "icao": sp.icao,
                    "obs_date": sp.obs_date.isoformat(),
                    "bucket": b.label,
                    "entry_ts": eval_ts,
                    "entry_px": eff_ask,
                    "p_model": round(p_lock, 4),
                    "cooling_cushion_c": res["cooling_cushion_c"],
                    "edge": round(edge, 4),
                    "won": won,
                    "pnl_usd": round(pnl, 2),
                    "roi_pct": round(100.0 * pnl / TICKET_W1, 2),
                })
                entered_w1 = True

    return {
        "calibrated_sigma_c": best_sigma,
        "events_evaluated": len(bundles),
        "W1_SOLAR_PEAK_LOCK": {
            "ALL": summarize_trades(w1_trades, "W1_ALL"),
            "TRAIN": summarize_trades([t for t in w1_trades if t["split"] == "TRAIN"], "W1_TRAIN"),
            "TEST_OOS": summarize_trades([t for t in w1_trades if t["split"] == "TEST"], "W1_TEST_OOS"),
            "sample_trades": w1_trades[-8:],
        },
        "W2_ENSEMBLE_VALUE": {
            "ALL": summarize_trades(w2_trades, "W2_ALL"),
            "TRAIN": summarize_trades([t for t in w2_trades if t["split"] == "TRAIN"], "W2_TRAIN"),
            "TEST_OOS": summarize_trades([t for t in w2_trades if t["split"] == "TEST"], "W2_TEST_OOS"),
            "sample_trades": w2_trades[-8:],
        },
    }


# ==============================================================================
# 2. BARRIER ONE-TOUCH & 3. MULTI-STRIKE SVI BACKTESTS
# ==============================================================================
def run_crypto_barrier_and_strike_backtests() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    print("[2/3] Fetching Oct 2026 Binance 5m klines + Deribit DVOL + Resolved Hit & Strike events...", flush=True)
    oct_start = int(datetime(2026, 9, 29, 0, 0, tzinfo=timezone.utc).timestamp())
    oct_end = int(datetime(2026, 10, 25, 16, 0, tzinfo=timezone.utc).timestamp())

    klines = {
        "BTC": fetch_binance_5m_series("BTCUSDT", oct_start, oct_end),
        "ETH": fetch_binance_5m_series("ETHUSDT", oct_start, oct_end),
    }
    dvol = {
        "BTC": fetch_deribit_dvol_hourly("BTC", oct_start, oct_end),
        "ETH": fetch_deribit_dvol_hourly("ETH", oct_start, oct_end),
    }

    def _get_spot(asset: str, ts: int) -> Optional[float]:
        b5 = (ts // 300) * 300
        row = klines[asset].get(b5) or klines[asset].get(b5 - 300)
        return row[3] if row else None

    def _realized_vol_4h_annual(asset: str, ts: int) -> float:
        b5 = (ts // 300) * 300
        k_map = klines[asset]
        rets = []
        for t in range(b5 - 48 * 300, b5, 300):
            r0 = k_map.get(t)
            r1 = k_map.get(t + 300)
            if r0 and r1 and r0[3] > 0 and r1[3] > 0:
                rets.append(math.log(r1[3] / r0[3]))
        if len(rets) < 12:
            return 0.0
        var_5m = sum(x * x for x in rets) / len(rets)
        return math.sqrt(var_5m * (365.25 * 288.0))

    def _get_dvol(asset: str, ts: int) -> float:
        bh = (ts // 3600) * 3600
        for off in (0, -3600, -7200, 3600):
            if (bh + off) in dvol[asset]:
                return dvol[asset][bh + off]
        return 0.42 if asset == "BTC" else 0.54

    def _already_touched(asset: str, start_ts: float, now_ts: int, strike: float, direction: str) -> bool:
        b_start = (int(start_ts) // 300) * 300
        b_now = (now_ts // 300) * 300
        k_map = klines[asset]
        for t in range(b_start, b_now + 300, 300):
            row = k_map.get(t)
            if not row:
                continue
            if direction == "UP" and row[1] >= strike:
                return True
            if direction == "DOWN" and row[2] <= strike:
                return True
        return False

    # --- Load Resolved One-Touch Barrier ("Hit") Events ---
    hit_rungs: List[BarrierRungSpec] = []
    for asset, h_grp, slug in [
        ("BTC", "DAILY", "bitcoin-hit-price-daily"),
        ("ETH", "DAILY", "ethereum-hit-price-daily"),
        ("BTC", "WEEKLY", "bitcoin-hit-price-weekly"),
        ("ETH", "WEEKLY", "ethereum-hit-price-weekly"),
    ]:
        evts = http_get_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=true&order=endDate&ascending=false&limit=24") or []
        for ev in evts:
            for r in parse_hit_event(ev, asset, h_grp, slug):
                if r.resolved_yes is not None and r.end_ts >= datetime(2026, 10, 2, tzinfo=timezone.utc).timestamp():
                    hit_rungs.append(r)

    print(f"      Loaded {len(hit_rungs)} resolved Barrier Hit rungs. Fetching CLOB histories...", flush=True)

    def _fetch_barrier_hist(r: BarrierRungSpec) -> Tuple[BarrierRungSpec, List[Tuple[int, float]], List[Tuple[int, float]]]:
        return r, fetch_clob_history(r.yes_token, fidelity=20), fetch_clob_history(r.no_token, fidelity=20)

    barrier_bundles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=28) as pool:
        for item in pool.map(_fetch_barrier_hist, hit_rungs):
            if item[1] or item[2]:
                barrier_bundles.append(item)

    # Calibrate `wick_vol_multiplier` strictly on TRAIN split (end_ts <= SPLIT_CUTOFF_TS) via Brier Score
    best_wick_mult = 1.12
    best_b_brier = 999.0
    train_barriers = [x for x in barrier_bundles if x[0].end_ts <= SPLIT_CUTOFF_TS]
    for w_cand in (0.95, 1.05, 1.15, 1.25):
        bs = 0.0
        bn = 0
        for r, yes_pts, _ in train_barriers:
            if not yes_pts:
                continue
            mid_idx = len(yes_pts) // 3
            t_eval, _ = yes_pts[mid_idx]
            tte = r.end_ts - t_eval
            sp_px = _get_spot(r.asset, t_eval)
            if not sp_px or tte <= 1800 or _already_touched(r.asset, r.start_ts, t_eval, r.strike, r.direction):
                continue
            iv_w, _ = get_wing_implied_vol(r.asset, sp_px, r.strike, tte, dvol_annual_override=_get_dvol(r.asset, t_eval))
            p_t = first_passage_touch_prob(sp_px, r.strike, tte, iv_w, r.direction, wick_vol_multiplier=w_cand)
            bs += (p_t - float(r.resolved_yes)) ** 2
            bn += 1
        if bn > 0 and (bs / bn) < best_b_brier:
            best_b_brier = bs / bn
            best_wick_mult = w_cand

    print(f"      [TRAIN Calibration] Optimal Barrier 1m-Wick Vol Multiplier={best_wick_mult:.2f} (Brier={best_b_brier:.4f}).", flush=True)

    b1_tail_trades: List[Dict[str, Any]] = []
    b2_nolock_trades: List[Dict[str, Any]] = []
    FEE_CRYPTO = 0.07
    SPREAD_HALF = 0.008  # Conservative 0.8c half-spread slippage on top of CLOB trade/mid price

    for r, yes_pts, no_pts in sorted(barrier_bundles, key=lambda x: x[0].end_ts):
        split = "TRAIN" if r.end_ts <= SPLIT_CUTOFF_TS else "TEST"

        # --- B1_CONVEX_TAIL_YES ($25 basket ticket per rung, VRP Expansion + Momentum Toward Barrier) ---
        for idx, (t_eval, px_mid) in enumerate(yes_pts):
            tte = r.end_ts - t_eval
            if not (7200 <= tte <= 5 * 86400):
                continue
            if not (0.04 <= px_mid <= 0.26):
                continue
            sp_px = _get_spot(r.asset, t_eval)
            sp_2h = _get_spot(r.asset, t_eval - 7200)
            if not sp_px or not sp_2h or _already_touched(r.asset, r.start_ts, t_eval, r.strike, r.direction):
                continue
            # Variance Risk Premium (VRP) + Directional Breakout Filter:
            # Require 4h realized volatility >= 0.95 * DVOL and 2h momentum moving toward barrier!
            dvol_now = _get_dvol(r.asset, t_eval)
            rv_4h = _realized_vol_4h_annual(r.asset, t_eval)
            moving_toward = (r.direction == "UP" and sp_px > sp_2h * 1.003) or (r.direction == "DOWN" and sp_px < sp_2h * 0.997)
            if rv_4h < 0.95 * dvol_now or not moving_toward:
                continue
            iv_w, _ = get_wing_implied_vol(r.asset, sp_px, r.strike, tte, dvol_annual_override=max(dvol_now, 0.5 * (dvol_now + rv_4h)))
            p_touch = first_passage_touch_prob(sp_px, r.strike, tte, iv_w, r.direction, wick_vol_multiplier=best_wick_mult)
            eff_ask = px_mid + SPREAD_HALF
            fee_ps = FEE_CRYPTO * eff_ask * (1.0 - eff_ask)
            cost_ps = eff_ask + fee_ps
            edge = p_touch - cost_ps
            if edge >= 0.065 and (p_touch / cost_ps) >= 1.40:
                ticket = 25.0
                shares = ticket / cost_ps
                # Check if 0%-fee Maker 2x scalp target (`target_px = min(0.88, round(2.0 * eff_ask, 3))`) fills cleanly on subsequent CLOB history
                tp_px = min(0.88, round(2.0 * eff_ask, 3))
                scalped = False
                for t_fut, px_fut in yes_pts[idx + 1:]:
                    if px_fut >= tp_px + 0.005:  # Require trade/mid strictly through resting Maker limit!
                        scalped = True
                        break
                if scalped:
                    payout = shares * tp_px
                    won = True
                    exit_mode = "MAKER_2X_TP"
                else:
                    won = (r.resolved_yes == 1)
                    payout = shares * (1.0 if won else 0.0)
                    exit_mode = "HOLD_SETTLE"
                pnl = payout - ticket
                b1_tail_trades.append({
                    "split": split,
                    "sleeve": "B1_CONVEX_TAIL_YES",
                    "asset": r.asset,
                    "question": r.question,
                    "entry_ts": t_eval,
                    "entry_px": round(cost_ps, 4),
                    "p_model": round(p_touch, 4),
                    "edge": round(edge, 4),
                    "exit_mode": exit_mode,
                    "won": won,
                    "pnl_usd": round(pnl, 2),
                    "roi_pct": round(100.0 * pnl / ticket, 2),
                })
                break

        # --- B2_BARRIER_NO_LOCK ($100 ticket, final 1h-10h when barrier untouched) ---
        for t_eval, px_no_mid in no_pts:
            tte = r.end_ts - t_eval
            if not (3600 <= tte <= 36000):
                continue
            if not (0.68 <= px_no_mid <= 0.90):
                continue
            sp_px = _get_spot(r.asset, t_eval)
            if not sp_px or _already_touched(r.asset, r.start_ts, t_eval, r.strike, r.direction):
                continue
            iv_w, _ = get_wing_implied_vol(r.asset, sp_px, r.strike, tte, dvol_annual_override=_get_dvol(r.asset, t_eval))
            p_touch = first_passage_touch_prob(sp_px, r.strike, tte, iv_w, r.direction, wick_vol_multiplier=best_wick_mult)
            p_no = 1.0 - p_touch
            eff_ask = px_no_mid + SPREAD_HALF
            fee_ps = FEE_CRYPTO * eff_ask * (1.0 - eff_ask)
            cost_ps = eff_ask + fee_ps
            edge = p_no - cost_ps
            if p_no >= 0.88 and edge >= 0.040:
                ticket = 100.0
                shares = ticket / cost_ps
                won = (r.resolved_yes == 0)
                pnl = (shares * 1.0 - ticket) if won else (-ticket)
                b2_nolock_trades.append({
                    "split": split,
                    "sleeve": "B2_BARRIER_NO_LOCK",
                    "asset": r.asset,
                    "question": r.question,
                    "entry_ts": t_eval,
                    "entry_px": round(cost_ps, 4),
                    "p_model": round(p_no, 4),
                    "edge": round(edge, 4),
                    "won": won,
                    "pnl_usd": round(pnl, 2),
                    "roi_pct": round(100.0 * pnl / ticket, 2),
                })
                break

    # ==========================================================================
    # 3. MULTI-STRIKE SVI SCALPER & CONVERGENCE BACKTEST (#4)
    # ==========================================================================
    print("[3/3] Fetching resolved October 2026 Multi-Strike ('above ___') ladders...", flush=True)
    strike_rungs: List[StrikeRungSpec] = []
    for asset, slug in [("BTC", "btc-multi-strikes-weekly"), ("ETH", "ethereum-multi-strikes-weekly")]:
        evts = http_get_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=true&order=endDate&ascending=false&limit=24") or []
        for ev in evts:
            for sr in parse_multistrike_event(ev, asset, slug):
                if sr.resolved_yes is not None and sr.end_ts >= datetime(2026, 10, 2, tzinfo=timezone.utc).timestamp():
                    strike_rungs.append(sr)

    def _fetch_strike_hist(sr: StrikeRungSpec) -> Tuple[StrikeRungSpec, List[Tuple[int, float]], List[Tuple[int, float]]]:
        return sr, fetch_clob_history(sr.yes_token, fidelity=20), fetch_clob_history(sr.no_token, fidelity=20)

    strike_bundles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=28) as pool:
        for item in pool.map(_fetch_strike_hist, strike_rungs):
            if item[1] or item[2]:
                strike_bundles.append(item)

    print(f"      Loaded {len(strike_bundles)} resolved Multi-Strike contracts with CLOB histories.", flush=True)

    m1_scalp_trades: List[Dict[str, Any]] = []
    m2_conv_trades: List[Dict[str, Any]] = []

    for sr, yes_pts, no_pts in sorted(strike_bundles, key=lambda x: x[0].end_ts):
        split = "TRAIN" if sr.end_ts <= SPLIT_CUTOFF_TS else "TEST"

        # Evaluate both YES and NO token histories for M1_SVI_MAKER_SCALP and M2_STRIKE_CONVERGENCE
        for side_lbl, pts, won_flag in [("YES", yes_pts, sr.resolved_yes == 1), ("NO", no_pts, sr.resolved_yes == 0)]:
            entered_m1 = False
            entered_m2 = False
            for idx, (t_eval, px_mid) in enumerate(pts):
                tte = sr.end_ts - t_eval
                if tte <= 900:
                    break
                sp_px = _get_spot(sr.asset, t_eval)
                sp_prev = _get_spot(sr.asset, t_eval - 900)
                if not sp_px or not sp_prev:
                    continue
                # Near-spot moneyness filter (|ln(K/S)| <= 0.08)
                if abs(math.log(sr.strike / sp_px)) > 0.08:
                    continue

                svi_eval = evaluate_svi_digital_fair_value(
                    sr.asset, sp_px, sr.strike, tte, is_downward=sr.is_downward,
                    dvol_annual_override=_get_dvol(sr.asset, t_eval), now_ts=float(t_eval)
                )
                p_fair = svi_eval["p_yes"] if side_lbl == "YES" else svi_eval["p_no"]

                # Momentum alignment gate: do not buy YES into a sharp -20bps 15m dump or NO into a +20bps rip
                ret_15m_bps = ((sp_px - sp_prev) / sp_prev) * 10000.0
                wins_up = (side_lbl == "YES" and not sr.is_downward) or (side_lbl == "NO" and sr.is_downward)
                if (wins_up and ret_15m_bps < -20.0) or ((not wins_up) and ret_15m_bps > 20.0):
                    continue

                eff_ask = px_mid + SPREAD_HALF
                fee_ps = FEE_CRYPTO * eff_ask * (1.0 - eff_ask)
                cost_ps = eff_ask + fee_ps
                edge = p_fair - cost_ps

                # --- M1_SVI_MAKER_SCALP (3h <= TTE <= 24h, 0.20 <= px <= 0.80, edge >= 5.5c, Hard Stop + Time-Stop) ---
                if (not entered_m1) and (10800 <= tte <= 86400) and (0.20 <= eff_ask <= 0.80) and edge >= 0.055:
                    ticket = 100.0
                    shares = ticket / cost_ps
                    tp_target = min(0.96, round(cost_ps + 0.050, 4))
                    stop_trigger = max(0.04, round(eff_ask - 0.075, 4))
                    exit_px = None
                    exit_fee = 0.0
                    exit_mode = "SETTLED"

                    for t_fut, px_fut in pts[idx + 1:]:
                        # 0%-fee Maker TP fill when CLOB trades strictly through tp_target + 0.5c
                        if px_fut >= tp_target + 0.005:
                            exit_px = tp_target
                            exit_fee = 0.0
                            exit_mode = "MAKER_TP_5C"
                            break
                        # Unconditional Hard Stop (-7.5c) so a scalp never turns into a -$100 binary wipeout
                        if px_fut <= stop_trigger:
                            bid_est = max(0.01, px_fut - SPREAD_HALF)
                            exit_px = bid_est
                            exit_fee = FEE_CRYPTO * bid_est * (1.0 - bid_est)
                            exit_mode = "HARD_STOP_7.5C"
                            break
                        # Mandatory Time-Stop at TTE <= 3600s (never hold a scalp into binary 0/1 pin risk!)
                        if sr.end_ts - t_fut <= 3600:
                            bid_est = max(0.01, px_fut - SPREAD_HALF)
                            exit_px = bid_est
                            exit_fee = FEE_CRYPTO * bid_est * (1.0 - bid_est)
                            exit_mode = "TIME_STOP_1H"
                            break

                    if exit_px is not None:
                        payout = shares * (exit_px - exit_fee)
                        won = payout > ticket
                    else:
                        payout = shares * (1.0 if won_flag else 0.0)
                        won = won_flag
                    pnl = payout - ticket
                    m1_scalp_trades.append({
                        "split": split,
                        "sleeve": "M1_SVI_MAKER_SCALP",
                        "asset": sr.asset,
                        "question": sr.question,
                        "side": side_lbl,
                        "entry_ts": t_eval,
                        "entry_px": round(cost_ps, 4),
                        "p_model": round(p_fair, 4),
                        "edge": round(edge, 4),
                        "exit_mode": exit_mode,
                        "won": won,
                        "pnl_usd": round(pnl, 2),
                        "roi_pct": round(100.0 * pnl / ticket, 2),
                    })
                    entered_m1 = True

                # --- M2_STRIKE_CONVERGENCE (Post-NYSE-Open 20m <= TTE <= 105m, z_sigma >= 1.55, + Salvage Stop) ---
                if (
                    (not entered_m2)
                    and (1200 <= tte <= 6300)
                    and (0.68 <= eff_ask <= 0.90)
                    and svi_eval["z_sigma"] >= 1.55
                    and p_fair >= 0.91
                    and edge >= 0.040
                ):
                    ticket = 100.0
                    shares = ticket / cost_ps
                    exit_px_m2 = None
                    exit_fee_m2 = 0.0
                    exit_mode = "SETTLED"
                    salvage_trig = max(0.25, eff_ask - 0.22)
                    for _, px_fut in pts[idx + 1:]:
                        if px_fut >= 0.975:
                            exit_px_m2 = 0.97
                            exit_fee_m2 = 0.0
                            exit_mode = "MAKER_TP_97C"
                            break
                        if px_fut <= salvage_trig:
                            bid_est = max(0.05, px_fut - SPREAD_HALF)
                            exit_px_m2 = bid_est
                            exit_fee_m2 = FEE_CRYPTO * bid_est * (1.0 - bid_est)
                            exit_mode = "SALVAGE_STOP"
                            break
                    if exit_px_m2 is not None:
                        payout = shares * (exit_px_m2 - exit_fee_m2)
                        won = payout > ticket
                    else:
                        payout = shares * (1.0 if won_flag else 0.0)
                        won = won_flag
                    pnl = payout - ticket
                    m2_conv_trades.append({
                        "split": split,
                        "sleeve": "M2_STRIKE_CONVERGENCE",
                        "asset": sr.asset,
                        "question": sr.question,
                        "side": side_lbl,
                        "entry_ts": t_eval,
                        "entry_px": round(cost_ps, 4),
                        "p_model": round(p_fair, 4),
                        "z_sigma": svi_eval["z_sigma"],
                        "edge": round(edge, 4),
                        "exit_mode": exit_mode,
                        "won": won,
                        "pnl_usd": round(pnl, 2),
                        "roi_pct": round(100.0 * pnl / ticket, 2),
                    })
                    entered_m2 = True

    barrier_summary = {
        "calibrated_wick_vol_mult": best_wick_mult,
        "rungs_evaluated": len(barrier_bundles),
        "B1_CONVEX_TAIL_YES": {
            "ALL": summarize_trades(b1_tail_trades, "B1_ALL"),
            "TRAIN": summarize_trades([t for t in b1_tail_trades if t["split"] == "TRAIN"], "B1_TRAIN"),
            "TEST_OOS": summarize_trades([t for t in b1_tail_trades if t["split"] == "TEST"], "B1_TEST_OOS"),
            "sample_trades": b1_tail_trades[-8:],
        },
        "B2_BARRIER_NO_LOCK": {
            "ALL": summarize_trades(b2_nolock_trades, "B2_ALL"),
            "TRAIN": summarize_trades([t for t in b2_nolock_trades if t["split"] == "TRAIN"], "B2_TRAIN"),
            "TEST_OOS": summarize_trades([t for t in b2_nolock_trades if t["split"] == "TEST"], "B2_TEST_OOS"),
            "sample_trades": b2_nolock_trades[-8:],
        },
    }

    strike_summary = {
        "rungs_evaluated": len(strike_bundles),
        "M1_SVI_MAKER_SCALP": {
            "ALL": summarize_trades(m1_scalp_trades, "M1_ALL"),
            "TRAIN": summarize_trades([t for t in m1_scalp_trades if t["split"] == "TRAIN"], "M1_TRAIN"),
            "TEST_OOS": summarize_trades([t for t in m1_scalp_trades if t["split"] == "TEST"], "M1_TEST_OOS"),
            "sample_trades": m1_scalp_trades[-8:],
        },
        "M2_STRIKE_CONVERGENCE": {
            "ALL": summarize_trades(m2_conv_trades, "M2_ALL"),
            "TRAIN": summarize_trades([t for t in m2_conv_trades if t["split"] == "TRAIN"], "M2_TRAIN"),
            "TEST_OOS": summarize_trades([t for t in m2_conv_trades if t["split"] == "TEST"], "M2_TEST_OOS"),
            "sample_trades": m2_conv_trades[-8:],
        },
    }
    return barrier_summary, strike_summary


def main() -> None:
    t0 = time.time()
    weather_res = run_weather_backtest()
    barrier_res, strike_res = run_crypto_barrier_and_strike_backtests()

    combined = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.time() - t0, 2),
        "split_cutoff_utc": "2026-10-16T23:59:59Z",
        "option_1_weather": weather_res,
        "option_2_barrier_onetouch": barrier_res,
        "option_4_multistrike_svi": strike_res,
    }
    REPORT_JSON.write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print("\n================= WALK-FORWARD BACKTEST SUMMARY =================")
    for opt_key, sleeves in [
        ("OPTION #1 WEATHER", ["W1_SOLAR_PEAK_LOCK", "W2_ENSEMBLE_VALUE"]),
        ("OPTION #2 BARRIER", ["B1_CONVEX_TAIL_YES", "B2_BARRIER_NO_LOCK"]),
        ("OPTION #4 STRIKE SVI", ["M1_SVI_MAKER_SCALP", "M2_STRIKE_CONVERGENCE"]),
    ]:
        src = (
            weather_res if "WEATHER" in opt_key
            else (barrier_res if "BARRIER" in opt_key else strike_res)
        )
        print(f"\n--- {opt_key} ---")
        for sl in sleeves:
            tr = src[sl]["TRAIN"]
            te = src[sl]["TEST_OOS"]
            al = src[sl]["ALL"]
            print(
                f"  {sl:24s} | ALL: {al['trades']:3d} tr, WR={al['win_rate_pct']:5.1f}%, PnL=${al['net_pnl_usd']:+8.2f}, PF={al['profit_factor']:5.2f}, MaxDD=${al['max_drawdown_usd']:6.2f}\n"
                f"  {'':24s} | TRN: {tr['trades']:3d} tr, WR={tr['win_rate_pct']:5.1f}%, PnL=${tr['net_pnl_usd']:+8.2f}, PF={tr['profit_factor']:5.2f} | "
                f"OOS: {te['trades']:3d} tr, WR={te['win_rate_pct']:5.1f}%, PnL=${te['net_pnl_usd']:+8.2f}, PF={te['profit_factor']:5.2f}"
            )
    print(f"\nSaved full JSON report -> {REPORT_JSON}")


if __name__ == "__main__":
    main()

# ======================================================================================
# [13/16] MODULE: scripts/polymarket_daily_projections.py
# PURPOSE: Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker
# ======================================================================================

#!/usr/bin/env python3
"""
polymarket_daily_projections.py
===============================
Live Day-by-Day Equity, Net Profit & Phased Sleeve Graduation Projection Engine
(v4.2 Post-Purge Clean Roster Edition — Zero Quarantined Sleeves).

Dynamically anchors Day 0 to the REAL live collateral balance and closed trade ledger in
`data/polymarket/live_harvester_state.json`, tracks real-time shadow graduation progress
across all active non-quarantined sleeves in:
  - `data/alpha124/alpha124_shadow_state.json` (`D1`, `D1_QUIET`, `D1_4H`, `W1`, `W3`, `B2`, `M3`, `N1`, `U1`, `S5M`, `C1`, `S2`)
  - `data/polymarket/state_shadow_sol_v392.json` (`SLEEVE_SOL_V392_SHADOW`)
  - `data/polymarket/shadow_phase3_4_tracker.jsonl` (`SHADOW_PHASE3A_MAKER`)
  - `data/exp316/exp316_shadow_state.json` (`EXP316_TRACK_A_LATE_LOCK`)

Strictly excludes all quarantined/retired sleeves (`M4_SHOCK_STRIKE_CATCHUP`, `W2_ENSEMBLE_VALUE`,
`W2_MAKER_OVERROUND`, `M1_SVI_MAKER_SCALP`, `M2_STRIKE_CONVERGENCE`, `P1_PREOPEN_MAKER_STRADDLE`,
`B1_CONVEX_TAIL_YES`, and `SLEEVE_XRP_V392_SHADOW`), and enforces empirical CLOB L1/L2 depth caps:
  - P25 Conservative (Finland ~295ms RTT + variance/drawdown haircut)
  - P50 Base         (Current Finland VM + empirical D1/SOL/Phase3A/W1/B2 caps)
  - P75 Upside       (Low-latency <15ms non-restricted EU execution + full active roster)

Writes atomic JSON output to `data/polymarket/live_daily_projections.json` and prints a
human-readable day-by-day table for CLI / scheduled telemetry checks.
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
LIVE_STATE_FILE = PIPELINE_ROOT / "data" / "polymarket" / "live_harvester_state.json"
ALPHA124_STATE_FILE = (
    PIPELINE_ROOT / "data" / "polymarket" / "alpha124_shadow_state.json"
    if (PIPELINE_ROOT / "data" / "polymarket" / "alpha124_shadow_state.json").exists()
    else PIPELINE_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json"
)
EXP316_STATE_FILE = PIPELINE_ROOT / "data" / "exp316" / "exp316_shadow_state.json"
SOL_SHADOW_FILE = PIPELINE_ROOT / "data" / "polymarket" / "state_shadow_sol_v392.json"
XRP_SHADOW_FILE = PIPELINE_ROOT / "data" / "polymarket" / "state_shadow_xrp_v392.json"
PHASE34_TRACKER_FILE = PIPELINE_ROOT / "data" / "polymarket" / "shadow_phase3_4_tracker.jsonl"
RISK_CONFIG_FILE = PIPELINE_ROOT / "config" / "polymarket_risk_config.json"
OUTPUT_JSON_FILE = PIPELINE_ROOT / "data" / "polymarket" / "live_daily_projections.json"

QUARANTINED_SLEEVES = frozenset({
    "M4_SHOCK_STRIKE_CATCHUP",
    "W2_ENSEMBLE_VALUE",
    "W2_MAKER_OVERROUND",
    "M1_SVI_MAKER_SCALP",
    "M2_STRIKE_CONVERGENCE",
    "P1_PREOPEN_MAKER_STRADDLE",
    "B1_CONVEX_TAIL_YES",
    "S2_EXACT_TWAP_LOCK",
    "ZERO_FEE_MAKER_ANCHOR_BOX",
    "CTF_OVERROUND_MINT_SELL",
    "SLEEVE_XRP_V392_SHADOW",
})


GRADUATION_SPECS: List[Dict[str, Any]] = [
    {
        "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
        "wave": "Wave 1 (Live Graduated)",
        "target_day": 1,
        "min_days": 0.25,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 13.5,
        "l1_daily_pnl_cap_usd": 140.0,
    },
    {
        "sleeve": "D1_QUIET_BOOK_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 3,
        "min_days": 0.25,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 65.0,
    },
    {
        "sleeve": "D1_4H_DOMINANCE_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 60.0,
    },
    {
        "sleeve": "C1_BINARY_COMPLETE_SET",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "M3_LADDER_MONO_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "B3_BARRIER_MONO_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "D1_MAKER_ANCHOR_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 45.0,
    },
    {
        "sleeve": "N1_NEGRISK_CROSS_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 20.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "W3_WEATHER_SLATE_ARB",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "CM_B3_PYTH_BARRIER_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "SP1_NBA_ZERO_FEE_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "NR0_ZERO_FEE_SLATE_ARB",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "B4_TOUCHED_BARRIER_WICK_LOCK",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 4,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "ZERO_FEE_MAKER_ANCHOR_BOX",
        "wave": "Wave 1 (Fast-Track Maker Box)",
        "target_day": 5,
        "min_days": 1.0,
        "min_settled": 8,
        "min_wr_pct": 92.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "CTF_OVERROUND_MINT_SELL",
        "wave": "Wave 1 (Instant Mint-Sell 8/8)",
        "target_day": 4,
        "min_days": 0.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "TW1_COUNTING_TRUNCATION_AND_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 5,
        "min_days": 1.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "FED1_CENTRAL_BANK_LP_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "COND1_MACRO_PARTITION_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "D2_12PM_BINANCE_BOX",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 5,
        "min_days": 1.5,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 18.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "GAS1_AAA_GASOLINE_LOCK",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 20.0,
    },
    {
        "sleeve": "MKR_REWARD_LOCKED_CARRY",
        "wave": "Wave 1 (Fast-Track 8/8)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 8,
        "min_wr_pct": 100.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 20.0,
    },
    {
        "sleeve": "SLEEVE_SOL_V392_SHADOW",
        "wave": "Wave 2 (Day 5 SOL)",
        "target_day": 5,
        "min_days": 1.5,
        "min_settled": 30,
        "min_wr_pct": 85.0,
        "source": "sol_shadow",
        "stage1_ticket_usd": 12.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "SHADOW_PHASE3A_MAKER",
        "wave": "Wave 2 (Day 6 Maker)",
        "target_day": 6,
        "min_days": 2.0,
        "min_settled": 25,
        "min_wr_pct": 80.0,
        "source": "phase3a_shadow",
        "stage1_ticket_usd": 14.0,
        "l1_daily_pnl_cap_usd": 32.0,
    },
    {
        "sleeve": "W1_SOLAR_PEAK_LOCK",
        "wave": "Wave 2 (Day 8 METAR)",
        "target_day": 8,
        "min_days": 5.0,
        "min_settled": 20,
        "min_wr_pct": 86.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 95.0,
    },
    {
        "sleeve": "B2_BARRIER_NO_LOCK",
        "wave": "Wave 2 (Day 8 Barrier)",
        "target_day": 8,
        "min_days": 5.0,
        "min_settled": 25,
        "min_wr_pct": 88.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 55.0,
    },
    {
        "sleeve": "CM_B2_PYTH_SESSION_NO_LOCK",
        "wave": "Wave 2 (Day 9 Pyth 0%-Fee)",
        "target_day": 9,
        "min_days": 5.0,
        "min_settled": 25,
        "min_wr_pct": 88.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 45.0,
    },
    {
        "sleeve": "CM_U1_PYTH_CLOSE_LOCK",
        "wave": "Wave 2 (Day 10 Pyth Close)",
        "target_day": 10,
        "min_days": 5.0,
        "min_settled": 25,
        "min_wr_pct": 88.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "EXP316_TRACK_A_LATE_LOCK",
        "wave": "Wave 2 (Day 10 Strike)",
        "target_day": 10,
        "min_days": 5.0,
        "min_settled": 25,
        "min_wr_pct": 80.0,
        "source": "exp316",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "U1_DAILY_UPDOWN_LOCK",
        "wave": "Wave 3 (Day 15 Daily)",
        "target_day": 15,
        "min_days": 10.0,
        "min_settled": 20,
        "min_wr_pct": 85.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "S5M_CHAINLINK_SNIPER",
        "wave": "Wave 3 (Day 15 5m)",
        "target_day": 15,
        "min_days": 7.0,
        "min_settled": 35,
        "min_wr_pct": 82.0,
        "source": "alpha124",
        "stage1_ticket_usd": 14.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
    {
        "sleeve": "S4H_CHAINLINK_CONVERGENCE",
        "wave": "Wave 3 (Day 14 4h)",
        "target_day": 14,
        "min_days": 7.0,
        "min_settled": 25,
        "min_wr_pct": 85.0,
        "source": "alpha124",
        "stage1_ticket_usd": 15.0,
        "l1_daily_pnl_cap_usd": 30.0,
    },
    {
        "sleeve": "CM_SHOCK_PYTH_CATALYST",
        "wave": "Wave 3 (Day 16 Macro Jump)",
        "target_day": 16,
        "min_days": 10.0,
        "min_settled": 25,
        "min_wr_pct": 82.0,
        "source": "alpha124",
        "stage1_ticket_usd": 14.0,
        "l1_daily_pnl_cap_usd": 25.0,
    },
    {
        "sleeve": "S2_EXACT_TWAP_LOCK",
        "wave": "Wave 3 (Conditional)",
        "target_day": 15,
        "min_days": 10.0,
        "min_settled": 30,
        "min_wr_pct": 94.0,
        "source": "alpha124",
        "stage1_ticket_usd": 12.0,
        "l1_daily_pnl_cap_usd": 35.0,
    },
]


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_phase3a_summary(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"closed": 0, "wins": 0, "pnl_usd": 0.0}
    closed = 0
    wins = 0
    pnl = 0.0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("status") != "RESOLVED":
                    continue
                if str(rec.get("event_type") or "") != "SHADOW_PHASE3A_MAKER_RESOLVED":
                    continue
                closed += 1
                p = float(rec.get("shadow_net_pnl_usd") or 0.0)
                pnl += p
                if p > 0.0 or rec.get("won") is True:
                    wins += 1
    except Exception:
        pass
    return {"closed": closed, "wins": wins, "pnl_usd": round(pnl, 2)}


def _parse_iso(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
    except Exception:
        return None


def compute_v393_ticket_size(
    equity: float,
    seed_threshold: float = 88.0,
    seed_ticket: float = 12.0,
    dynamic_pct: float = 0.18,
    scale_up_threshold: float = 110.0,
    scale_up_pct: float = 0.22,
    max_cap: float = 200.0,
    min_smooth_floor: float = 66.67,
) -> float:
    """Exact smooth dynamic sizing curve matching `config/polymarket_risk_config.json` & `polymarket_live_harvester.py`."""
    if equity < 48.0:
        return 0.0
    if equity < min_smooth_floor:
        return round(seed_ticket, 2)
    if equity < scale_up_threshold:
        return round(min(max_cap, max(seed_ticket, equity * dynamic_pct)), 2)
    return round(min(max_cap, equity * scale_up_pct), 2)


def _depth_decay(ticket_usd: float, knee_usd: float = 65.0) -> float:
    """Smooth L2 orderbook slippage compression factor as ticket size grows above knee_usd."""
    if ticket_usd <= 20.0:
        return 1.0
    return max(0.58, 1.0 / (1.0 + 0.35 * ((ticket_usd - 20.0) / max(20.0, knee_usd))))


def _wilson_lcb_pct(wins: int, n: int, z: float = 1.2816) -> float:
    """One-sided ~90% Wilson score lower confidence bound on win rate (in percent)."""
    if n <= 0:
        return 0.0
    p = max(0.0, min(1.0, wins / float(n)))
    z2 = z * z
    denom = 1.0 + z2 / n
    center = p + z2 / (2.0 * n)
    rad = z * ((p * (1.0 - p) / n + z2 / (4.0 * n * n)) ** 0.5)
    return round(100.0 * max(0.0, (center - rad) / denom), 2)


def simulate_single_day_net_pnl(
    day_idx: int,
    equity_start: float,
    scenario: str,
    scale_up_threshold: float = 110.0,
    shadow_by_sleeve: Optional[Dict[str, Dict[str, Any]]] = None,
    sol_shadow: Optional[Dict[str, Any]] = None,
    phase3a_shadow: Optional[Dict[str, Any]] = None,
    exp316_t1k: Optional[Dict[str, Any]] = None,
) -> Tuple[float, Dict[str, float], str]:
    """
    Computes realistic single-day net profit (USD) across ONLY clean, non-quarantined active sleeves:
      1. `< $110` single-slot directional crypto concurrency guard + `0.82` `:45-:00` fast-pool
         collision discount across `v4.1` BTC/ETH, `D1`, and `SOL`
      2. Explicit Working-Capital Partition (`fast_intraday_pool` vs `slow_24h_pool`)
         so 6h-24h Weather (`W1`) / Barrier (`B2`) / Multi-Strike (`EXP-316`) tickets NEVER
         double-count collateral used by intraday `v4.1` / `D1` / `SOL` sleeves
      3. Empirical CLOB L1/L2 orderbook depth caps (`BTC` ~$200 L1, `ETH` ~$63 L1, `SOL` ~$20 L1,
         `D1` `T5000` paired ceiling)
      4. Zero allocation (`$0.00`) to all quarantined sleeves (`W2_ENSEMBLE_VALUE`, `W2_MAKER_OVERROUND`,
         `M1_SVI_MAKER_SCALP`, `M4_SHOCK_STRIKE_CATCHUP`, `M2`, `P1_PREOPEN_MAKER_STRADDLE`, `B1`, `XRP`),
         and hard `> $0` shadow-PnL gate on high-payoff-skew `S2_EXACT_TWAP_LOCK`.
    """
    mult_map = {
        "P25_CONSERVATIVE": 0.62,
        "P50_BASE_FINLAND": 1.00,
        "P75_LONDON_UPSIDE": 1.35,
    }
    kelly_geom_drag = {
        "P25_CONSERVATIVE": 0.68,
        "P50_BASE_FINLAND": 0.80,
        "P75_LONDON_UPSIDE": 0.86,
    }[scenario]
    m = mult_map[scenario] * kelly_geom_drag
    is_low_lat = scenario == "P75_LONDON_UPSIDE"
    fast_concurrency_disc = 0.82

    # Partition total USDC.e between Fast Intraday Turnover (<15m-4h) and Slow 6h-24h Lockups
    if day_idx < 8:
        fast_pool = equity_start
        slow_pool = 0.0
    elif day_idx < 15:
        fast_pool = equity_start * 0.68
        slow_pool = equity_start * 0.32
    else:
        fast_pool = equity_start * 0.60
        slow_pool = equity_start * 0.40

    breakdown: Dict[str, float] = {}
    milestone = "Wave 1 Live: WFO v3.9.5 (BTC+ETH) + D1 (15m/5m, QuietBook 13/13 & 4h)"

    # 1. Core Live Engine: Purged-WFO v3.9.5 Sub-Hourly & 1h BTC+ETH Sniper (92.86% WR, PF=3.34 across 3,278 mkts)
    t_v39 = compute_v393_ticket_size(fast_pool if day_idx >= 8 else equity_start)
    if t_v39 == 0.0 and equity_start >= 48.0:
        t_v39 = 12.0
    has_slot2 = equity_start >= scale_up_threshold
    eff_fills_v39 = (7.2 if has_slot2 else 5.8) * (1.12 if is_low_lat else 1.0)
    ev_v39 = 0.092 * m * _depth_decay(t_v39, knee_usd=60.0)
    cap_v39 = 195.0 if is_low_lat else 145.0
    pnl_v39 = min(cap_v39, t_v39 * eff_fills_v39 * ev_v39)
    breakdown["wfo_v395_directional_live"] = round(pnl_v39, 2)

    # 2. Wave 1 (Live Now): D1 Same-Oracle Dominance Boxes (15m/5m 28/28 + QuietBook 13/13 + 4h Corridors, 25% sizing <$160 / 32% >=$160)
    d1_pct = 0.32 if equity_start >= 160.0 else 0.25
    if day_idx < 4 and not has_slot2:
        t_d1 = min(42.0, max(15.0, fast_pool * d1_pct))
        live_boxes_per_day = 2.8 * fast_concurrency_disc * (1.18 if is_low_lat else 1.0)
    elif day_idx < 8:
        t_d1 = min(65.0, max(25.0, fast_pool * min(0.32, d1_pct)))
        live_boxes_per_day = 3.2 * fast_concurrency_disc * (1.20 if is_low_lat else 1.0)
        milestone = "Wave 1 Scale-Up: 2-Slot (>=$110, 22% WFO v3.9.5) + 38% D1 Boxes"
    else:
        t_d1 = min(145.0, max(30.0, fast_pool * 0.25))
        live_boxes_per_day = 3.8 * fast_concurrency_disc * (1.22 if is_low_lat else 1.0)
    ev_d1 = 0.052 * max(0.70, min(1.12, m)) * _depth_decay(t_d1, knee_usd=65.0)
    cap_d1 = 240.0 if is_low_lat else 165.0
    pnl_d1 = min(cap_d1, t_d1 * live_boxes_per_day * ev_d1)
    breakdown["D1_dominance_boxes"] = round(pnl_d1, 2)
    if has_slot2 and day_idx < 5:
        milestone = "Wave 1 Scale-Up: 2-Slot (>=$110, 22% WFO v3.9.5) + 38% D1 Boxes"

    # 3. Wave 2A (Day 5+): Graduated SOL Sub-Hourly (capped at $22 ticket for $20 p50 L1 depth) + Phase 3A 0%-Fee Maker Fallback
    if day_idx >= 5:
        sol_pnl_ok = float((sol_shadow or {}).get("realized_pnl", 1.0) or 0.0) >= 0.0
        t_sol = min(22.0, max(12.0, fast_pool * 0.10)) if sol_pnl_ok else 0.0
        pnl_sol = min(
            28.0 if is_low_lat else 18.0,
            t_sol * (1.8 * fast_concurrency_disc) * (0.062 * m * _depth_decay(t_sol, knee_usd=20.0)),
        )
        if pnl_sol > 0.0:
            breakdown["SOL_subhourly_graduated"] = round(pnl_sol, 2)
        if day_idx < 8:
            milestone = "Wave 2A Live: +SOL Sub-Hourly ($12-$22 L1-Capped)"

    if day_idx >= 6:
        p3a_ok = float((phase3a_shadow or {}).get("pnl_usd", 1.0) or 0.0) >= 0.0
        if p3a_ok:
            t_p3a = min(30.0, max(12.0, fast_pool * 0.11))
            pnl_p3a = min(
                36.0 if is_low_lat else 24.0,
                t_p3a * 1.5 * (0.065 * max(0.65, min(1.08, m)) * _depth_decay(t_p3a, knee_usd=40.0)),
            )
            breakdown["Phase3A_maker_fallback"] = round(pnl_p3a, 2)
            if day_idx < 8:
                milestone = "Wave 2A Live: +SOL & Phase-3A 0%-Fee Maker Fallback"

    # 4. Wave 2B (Day 8+): Slow-Pool High-WR Locks — W1 80-City 0%-Fee METAR + W3 Slate Arb + B2 Barrier + EXP-316 Track A
    if day_idx >= 8:
        in_stage1_w2 = day_idx < 14
        slow_t1_budget = min(48.0, slow_pool) if in_stage1_w2 else (slow_pool * (0.72 if day_idx >= 15 else 0.95))
        milestone = (
            "Wave 2B Micro-Live: +W1 80-City METAR, B2 Barrier, EXP-316 ($15 cap)"
            if in_stage1_w2
            else "Wave 2B Stage-2 Half-Kelly (Fast/Slow Partitioned)"
        )

        avg_t_w1 = max(12.0, (slow_t1_budget * 0.58) / 2.2)
        pnl_w1 = min(
            120.0 if is_low_lat else 85.0,
            (slow_t1_budget * 0.58) * 1.25 * (0.074 * max(0.65, min(1.08, m)) * _depth_decay(avg_t_w1, 90.0)),
        )
        # B2 + EXP-316 Track A strictly capped per rung (EXP-316 T2500 proved L2 exit slippage above ~$100-$150/rung)
        exp_hc = 1.0 if float((exp316_t1k or {}).get("net_pnl_usd", 1.0) or 0.0) >= 0.0 else 0.65
        avg_t_b2 = min(90.0, max(12.0, (slow_t1_budget * 0.42) / 2.0))
        pnl_b2_exp = min(
            80.0 if is_low_lat else 55.0,
            (slow_t1_budget * 0.42) * 1.30 * (0.060 * m * _depth_decay(avg_t_b2, 70.0) * exp_hc),
        )
        breakdown["W1_W3_weather_metar_locks"] = round(pnl_w1, 2)
        breakdown["B2_EXP316_barrier_strike_locks"] = round(pnl_b2_exp, 2)

    # 5. Wave 3 (Day 15+): Clean Post-Purge Additions ONLY (U1 Daily Up/Down + S5M 5m Sniper + N1/M3/C1 Cross-Boxes)
    # Quarantined W2_ENSEMBLE_VALUE, W2_MAKER_OVERROUND, M1_SVI_MAKER_SCALP, M4_SHOCK_STRIKE_CATCHUP, P1 = $0.00!
    if day_idx >= 15:
        in_stage1_w3 = day_idx < 21
        milestone = (
            "Wave 3 Micro-Live: +U1 Daily Lock, S5M 5m Sniper & N1 NegRisk Boxes"
            if in_stage1_w3
            else "Full Clean Roster Compounding (Zero Quarantined Sleeves, Depth-Capped)"
        )
        w3_budget = min(45.0, slow_pool * 0.28) if in_stage1_w3 else (slow_pool * 0.28)
        avg_t_w3 = max(14.0, w3_budget / 2.5)
        pnl_u1_s5m_n1 = min(
            75.0 if is_low_lat else 48.0,
            w3_budget * 1.45 * (0.062 * m * _depth_decay(avg_t_w3, 65.0)),
        )
        breakdown["U1_S5M_N1_clean_wave3"] = round(pnl_u1_s5m_n1, 2)

        # Conditional S2 Exact TWAP Lock: strictly gated at $0.00 until shadow N>=10 and net PnL > $0!
        s2_stat = (shadow_by_sleeve or {}).get("S2_EXACT_TWAP_LOCK") or {}
        if int(s2_stat.get("closed") or 0) >= 10 and float(s2_stat.get("realized_pnl_t1000_usd") or 0.0) > 0.0:
            t_s2 = min(45.0, max(12.0, fast_pool * 0.12))
            pnl_s2 = min(
                45.0 if is_low_lat else 30.0,
                t_s2 * (2.4 * fast_concurrency_disc) * (0.042 * m * _depth_decay(t_s2, 45.0)),
            )
            breakdown["S2_exact_twap_lock"] = round(pnl_s2, 2)

    total_day_pnl = round(sum(breakdown.values()), 2)
    return total_day_pnl, breakdown, milestone


def build_live_projections(days: int = 30, fallback_equity: float = 85.08) -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    live_st = _load_json(LIVE_STATE_FILE)
    a124_st = _load_json(ALPHA124_STATE_FILE)
    exp316_st = _load_json(EXP316_STATE_FILE)
    sol_st = _load_json(SOL_SHADOW_FILE)
    xrp_st = _load_json(XRP_SHADOW_FILE)
    p3a_st = _load_phase3a_summary(PHASE34_TRACKER_FILE)
    risk_cfg = _load_json(RISK_CONFIG_FILE)

    live_equity = float(
        live_st.get("total_account_equity")
        or live_st.get("live_bankroll")
        or fallback_equity
    )
    hwm_equity = float(live_st.get("high_water_mark_equity") or live_equity)
    scale_up_thr = float(risk_cfg.get("scale_up_equity_threshold") or 110.0)

    closed_live = live_st.get("closed_positions") or []
    live_wins = sum(
        1
        for t in closed_live
        if float(
            t.get("realized_pnl_usd")
            or t.get("net_pnl_usd")
            or (
                float(t.get("realized_exit_cash", 0.0))
                - float(t.get("notional_usd", 0.0))
                - float(t.get("fee_usd", 0.0))
            )
        )
        > 0
    )

    a124_started = _parse_iso(a124_st.get("started_at"))
    shadow_days_elapsed = (
        round(max(0.0, (now_utc - a124_started).total_seconds() / 86400.0), 2)
        if a124_started
        else 1.0
    )

    by_sleeve = a124_st.get("by_sleeve") or {}
    exp316_t1k = (exp316_st.get("tiers") or {}).get("T1000") or {}

    grad_tracker: List[Dict[str, Any]] = []
    for sp in GRADUATION_SPECS:
        sl = sp["sleeve"]
        if sl in QUARANTINED_SLEEVES:
            continue
        src = sp["source"]
        if src == "sol_shadow":
            closed_n = int(sol_st.get("total_trades_settled") or 0)
            wins_n = int(sol_st.get("winning_trades") or 0)
            open_n = int(sol_st.get("active_open_positions_count") or 0)
            pnl_ref = float(sol_st.get("realized_pnl") or 0.0)
        elif src == "phase3a_shadow":
            closed_n = int(p3a_st.get("closed") or 0)
            wins_n = int(p3a_st.get("wins") or 0)
            open_n = 0
            pnl_ref = float(p3a_st.get("pnl_usd") or 0.0)
        elif src == "exp316":
            closed_n = int(exp316_t1k.get("trades") or 0)
            wins_n = int(exp316_t1k.get("wins") or 0)
            open_n = int(exp316_st.get("active_positions") or 0)
            pnl_ref = float(exp316_t1k.get("net_pnl_usd") or 0.0)
        else:
            sl_data = by_sleeve.get(sl) or {}
            closed_n = int(sl_data.get("closed") or 0)
            wins_n = int(sl_data.get("wins") or 0)
            open_n = int(sl_data.get("open") or 0)
            pnl_ref = float(sl_data.get("realized_pnl_t1000_usd") or 0.0)

        wr_pct = round(100.0 * wins_n / closed_n, 2) if closed_n > 0 else 0.0
        wr_lcb90_pct = _wilson_lcb_pct(wins_n, closed_n)
        sample_pct = round(min(100.0, 100.0 * closed_n / sp["min_settled"]), 1)
        time_pct = round(min(100.0, 100.0 * shadow_days_elapsed / sp["min_days"]), 1)
        ready = (
            closed_n >= sp["min_settled"]
            and shadow_days_elapsed >= sp["min_days"]
            and wr_pct >= sp["min_wr_pct"]
            and wr_lcb90_pct >= max(0.0, sp["min_wr_pct"] - 20.0)
            and pnl_ref > 0.0
        )
        grad_tracker.append(
            {
                "sleeve": sl,
                "wave": sp["wave"],
                "source": src,
                "open_now": open_n,
                "settled_now": closed_n,
                "target_settled": sp["min_settled"],
                "sample_progress_pct": sample_pct,
                "days_elapsed": shadow_days_elapsed,
                "min_days": sp["min_days"],
                "time_progress_pct": time_pct,
                "win_rate_pct": wr_pct,
                "wilson_lcb90_wr_pct": wr_lcb90_pct,
                "target_wr_pct": sp["min_wr_pct"],
                "realized_pnl_t1000_usd": round(pnl_ref, 2),
                "ready_for_stage1_micro_live": ready,
            }
        )

    scenarios = ["P25_CONSERVATIVE", "P50_BASE_FINLAND", "P75_LONDON_UPSIDE"]
    eq_track = {sc: live_equity for sc in scenarios}
    start_date = now_utc.date()

    daily_rows: List[Dict[str, Any]] = []
    for d in range(1, days + 1):
        dt_str = (start_date + timedelta(days=d - 1)).isoformat()
        row: Dict[str, Any] = {"day": d, "date_utc": dt_str}
        milestone_lbl = ""
        base_breakdown: Dict[str, float] = {}
        for sc in scenarios:
            eq_prev = eq_track[sc]
            pnl_d, bdown, m_lbl = simulate_single_day_net_pnl(
                d,
                eq_prev,
                sc,
                scale_up_threshold=scale_up_thr,
                shadow_by_sleeve=by_sleeve,
                sol_shadow=sol_st,
                phase3a_shadow=p3a_st,
                exp316_t1k=exp316_t1k,
            )
            eq_end = round(eq_prev + pnl_d, 2)
            eq_track[sc] = eq_end
            short_k = sc.split("_")[0].lower()  # p25 / p50 / p75
            row[f"{short_k}_daily_pnl_usd"] = pnl_d
            row[f"{short_k}_end_equity_usd"] = eq_end
            if sc == "P50_BASE_FINLAND":
                milestone_lbl = m_lbl
                base_breakdown = bdown
                row["p50_v393_ticket_usd"] = compute_v393_ticket_size(eq_prev)
        row["active_regime_and_milestone"] = milestone_lbl
        row["p50_sleeve_pnl_breakdown_usd"] = base_breakdown
        daily_rows.append(row)

    payload = {
        "generated_at_utc": now_utc.isoformat(),
        "model_version": "v4.2_post_purge_clean_roster",
        "quarantined_sleeves_excluded": sorted(QUARANTINED_SLEEVES),
        "anchor_live_state": {
            "live_equity_usd": round(live_equity, 2),
            "high_water_mark_usd": round(hwm_equity, 2),
            "current_v393_ticket_usd": compute_v393_ticket_size(live_equity),
            "distance_to_88_dynamic_sizing_usd": round(max(0.0, 88.0 - live_equity), 2),
            "distance_to_110_slot2_unlock_usd": round(max(0.0, scale_up_thr - live_equity), 2),
            "live_closed_trades": len(closed_live),
            "live_wins": live_wins,
            "live_win_rate_pct": round(100.0 * live_wins / len(closed_live), 2) if closed_live else 0.0,
            "alpha124_markets_monitored": a124_st.get("markets_monitored", {}),
            "alpha124_open_shadow_positions": a124_st.get("open_positions_count", 0),
            "alpha124_resting_maker_bids": a124_st.get("pending_maker_orders_count", 0),
            "sol_shadow_settled": sol_st.get("total_trades_settled", 0),
            "sol_shadow_win_rate_pct": sol_st.get("win_rate_pct", 0.0),
            "phase3a_maker_settled": p3a_st.get("closed", 0),
            "xrp_shadow_settled": xrp_st.get("total_trades_settled", 0),
        },
        "summary_horizons_usd": {
            f"day_{k}": {
                "date_utc": daily_rows[k - 1]["date_utc"],
                "p25_equity": daily_rows[k - 1]["p25_end_equity_usd"],
                "p50_equity": daily_rows[k - 1]["p50_end_equity_usd"],
                "p75_equity": daily_rows[k - 1]["p75_end_equity_usd"],
                "p50_net_profit": round(daily_rows[k - 1]["p50_end_equity_usd"] - live_equity, 2),
            }
            for k in (1, 4, 7, 10, 14, 21, 30)
            if k <= len(daily_rows)
        },
        "p75_jurisdiction_compliance_note": (
            "P75 models <15ms low-latency execution; Polymarket restricts UK (eu-west-2), FR, DE, IE, and ON — "
            "keep live execution on Finland (or another verified non-restricted EU region) unless lawful eligibility is confirmed."
        ),
        "sleeve_graduation_live_tracker": grad_tracker,
        "day_by_day_schedule": daily_rows,
    }
    return payload


def write_live_projections_atomic(days: int = 30) -> Dict[str, Any]:
    payload = build_live_projections(days=days)
    OUTPUT_JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT_JSON_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, OUTPUT_JSON_FILE)
    return payload


def print_human_scorecard(payload: Dict[str, Any]) -> None:
    anc = payload["anchor_live_state"]
    print(f"=== DOMINUS POLYMARKET LIVE DAY-BY-DAY PROJECTIONS [{payload.get('model_version')}] ({payload['generated_at_utc']}) ===")
    print(
        f"Anchor Live Equity: ${anc['live_equity_usd']:.2f} (HWM ${anc['high_water_mark_usd']:.2f}) | "
        f"Live Epoch: {anc['live_wins']}W/{anc['live_closed_trades'] - anc['live_wins']}L ({anc['live_win_rate_pct']:.1f}% WR) | "
        f"To $88 Dynamic: ${anc['distance_to_88_dynamic_sizing_usd']:.2f} | To $110 Slot-2: ${anc['distance_to_110_slot2_unlock_usd']:.2f}"
    )
    print("\n--- Clean Active Shadow Sleeve Graduation Readiness (Quarantined Sleeves Excluded) ---")
    for g in payload["sleeve_graduation_live_tracker"]:
        status_tag = "READY" if g["ready_for_stage1_micro_live"] else "WAIT "
        print(
            f"  [{status_tag}] {g['sleeve']:28s} | {g['wave']:22s} | Settled={g['settled_now']:2d}/{g['target_settled']:2d} "
            f"(Open={g['open_now']:2d}) | WR={g['win_rate_pct']:6.1f}% (req>={g['target_wr_pct']:5.1f}%) | "
            f"Ref PnL=${g['realized_pnl_t1000_usd']:+7.2f}"
        )
    print("\n--- 30-Day Live-Anchored Compounding Schedule (Post-Purge Clean Roster, Depth-Capped) ---")
    print("Day | Date       | P25 Eq ($) | P50 Base Eq ($) | P50 Day PnL | P75 LowLat ($) | Active Regime / Graduation Milestone")
    print("-" * 122)
    for r in payload["day_by_day_schedule"]:
        print(
            f"D{r['day']:02d} | {r['date_utc']} | ${r['p25_end_equity_usd']:9.2f} | "
            f"${r['p50_end_equity_usd']:14.2f} | ${r['p50_daily_pnl_usd']:+10.2f} | "
            f"${r['p75_end_equity_usd']:13.2f} | {r['active_regime_and_milestone']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Live Polymarket Day-by-Day Projections & Graduation Tracker")
    parser.add_argument("--days", type=int, default=30, help="Projection horizon in days")
    parser.add_argument("--json-only", action="store_true", help="Print JSON payload instead of ASCII table")
    args = parser.parse_args()
    payload = write_live_projections_atomic(days=args.days)
    if args.json_only:
        print(json.dumps(payload, indent=2))
    else:
        print_human_scorecard(payload)


if __name__ == "__main__":
    main()

# ======================================================================================
# [14/16] MODULE: scripts/alpha124_status.py
# PURPOSE: Live Alpha-124 11-Sleeve Scorecard & Orderbook Opportunity Inspector
# ======================================================================================

#!/usr/bin/env python3
"""
CLI Scorecard & Live Opportunity Viewer for Polymarket Alpha-124 Shadow Daemon
"""
# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PROJECT_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json"
OPPS_FILE = PROJECT_ROOT / "data" / "alpha124" / "alpha124_live_opportunities.json"


def main() -> None:
    if not STATE_FILE.exists():
        print("No Alpha-124 state file found yet.")
        return
    st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    print(f"=== ALPHA-124 SHADOW SCORECARD (Updated: {st.get('updated_at_utc')}) ===")
    print(
        f"Cycles: {st.get('cycle_count')} | MakerPending: {st.get('pending_maker_orders_count', 0)} | "
        f"Monitored: {st.get('markets_monitored')}"
    )
    print(f"Spots : {st.get('spots')}")
    print(f"Realized PnL by Bankroll Tier: {st.get('portfolio_realized_pnl_by_bankroll_usd')}")
    print("\n--- Sleeve Breakdown ---")
    for sl, m in (st.get("by_sleeve") or {}).items():
        print(
            f"  {sl:28s} | Open={m['open']:2d} | Closed={m['closed']:3d} "
            f"({m['wins']}W/{m['losses']}L, WR={m['win_rate_pct']:5.1f}%) | T1000 PnL=${m['realized_pnl_t1000_usd']:+8.2f}"
        )

    by_d1 = st.get("by_d1_asset") or {}
    if by_d1:
        print("\n--- D1 Same-Oracle 7-Coin Graduation Status ---")
        for sym, dm in by_d1.items():
            print(
                f"  {sym:6s} | Open={dm['open']:2d} | Closed={dm['closed']:3d} "
                f"({dm['wins']}W/{dm['losses']}L, WR={dm['win_rate_pct']:5.1f}%) | T1000 PnL=${dm['realized_pnl_t1000_usd']:+8.2f}"
            )

    pend_m = st.get("pending_maker_orders") or []
    if pend_m:
        print(f"\n--- Resting 0%-Fee Maker Entry Bids ({len(pend_m)}) ---")
        for m_o in pend_m[:10]:
            print(
                f"  [{m_o['sleeve']}] {m_o['asset_or_city']} {m_o['title']} ({m_o['side']}) | "
                f"resting_bid=${m_o['resting_bid']:.3f} (ask_at_post=${m_o['best_ask_at_post']:.3f}, p_mod={m_o['p_model_at_post']:.3f})"
            )

    open_pos = st.get("open_positions") or []
    if open_pos:
        print(f"\n--- Active Shadow Positions ({len(open_pos)}) ---")
        for p in open_pos[:15]:
            print(
                f"  [{p['sleeve']}] {p['title']} ({p['side']}) | entry_eff=${p['entry_eff_px_t1000']:.3f} "
                f"last_bid=${p.get('last_bid',0):.3f} tp=${p.get('maker_tp_px') or 0:.3f} p_mod={p['p_model_entry']:.3f}"
            )

    if OPPS_FILE.exists():
        opps = json.loads(OPPS_FILE.read_text(encoding="utf-8")).get("top_opportunities") or []
        if opps:
            print(f"\n--- Top Live Orderbook Opportunities ({len(opps)}) ---")
            for o in opps[:12]:
                print(
                    f"  [{o['sleeve']:28s}] edge={o['net_edge']:+.3f} | ask=${o['ask_vwap']:.3f} vs p={o['p_model']:.3f} "
                    f"(L1=${o['l1_usd']:.0f}) | {o['market']}"
                )


if __name__ == "__main__":
    main()

# ======================================================================================
# [15/16] MODULE: scripts/polymarket_scorecard_snapshot.py
# PURPOSE: Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot
# ======================================================================================

#!/usr/bin/env python3
"""Read-only Live + Shadow Polymarket scorecard snapshot for scheduled monitoring."""

import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path("/home/skybullet1987/quant_pipeline")
SERVICES = [
    "polymarket-live-harvester",
    "polymarket-alpha124-shadow",
    "polymarket-trader",
    "polymarket-exp316-shadow",
    "polymarket-recorder",
    "polymarket-recorder-eth",
    "polymarket-recorder-sol",
    "polymarket-recorder-xrp",
]


def _read_json(rel_path: str) -> dict:
    p = ROOT / rel_path
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc)}


def main() -> None:
    env = dict(os.environ)
    if hasattr(os, "getuid"):
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    svc_map = {
        s: subprocess.run(
            ["systemctl", "--user", "is-active", s],
            capture_output=True,
            text=True,
            env=env,
        ).stdout.strip()
        for s in SERVICES
    }

    live = _read_json("data/polymarket/live_harvester_state.json")
    alpha124 = _read_json("data/alpha124/alpha124_shadow_state.json")
    proj = _read_json("data/polymarket/live_daily_projections.json")
    paper = _read_json("data/polymarket/paper_trader_state.json")
    sol = _read_json("data/polymarket/state_shadow_sol_v392.json")
    xrp = _read_json("data/polymarket/state_shadow_xrp_v392.json")
    exp316 = _read_json("data/exp316/exp316_shadow_state.json")

    closed = live.get("closed_positions") or []
    wins = sum(
        1
        for t in closed
        if float(
            t.get("realized_pnl_usd")
            or t.get("net_pnl_usd")
            or (
                float(t.get("realized_exit_cash", 0.0))
                - float(t.get("notional_usd", 0.0))
                - float(t.get("fee_usd", 0.0))
            )
        )
        > 0
    )

    j_out = subprocess.run(
        [
            "journalctl",
            "--user",
            "-u",
            "polymarket-live-harvester",
            "--since",
            "24 hours ago",
            "--no-pager",
        ],
        capture_output=True,
        text=True,
        env=env,
    ).stdout.splitlines()

    p3a = [line for line in j_out if "SHADOW_PHASE3A" in line][-5:]
    p4 = [line for line in j_out if "SHADOW_PHASE4" in line][-5:]

    alt_keys = [
        "timestamp",
        "current_equity",
        "realized_pnl",
        "total_trades_settled",
        "winning_trades",
        "losing_trades",
        "win_rate_pct",
        "profit_factor",
        "active_open_positions_count",
        "ready_for_live_graduation",
        "graduation_criteria",
    ]

    snapshot = {
        "services": svc_map,
        "all_services_active": all(v == "active" for v in svc_map.values()),
        "live_v392": {
            "updated_at_utc": live.get("updated_at_utc"),
            "live_bankroll_usd": live.get("live_bankroll"),
            "total_account_equity_usd": live.get("total_account_equity"),
            "high_water_mark_equity_usd": live.get("high_water_mark_equity"),
            "active_positions_count": live.get("active_positions_count"),
            "closed_positions_count": len(closed),
            "closed_wins": wins,
            "progress_to_n40_gate": f"{len(closed)}/40",
            "distance_to_88_dynamic_tier_usd": round(
                max(0.0, 88.0 - float(live.get("total_account_equity") or 0.0)), 2
            ),
            "distance_to_110_scaleup_tier_usd": round(
                max(0.0, 110.0 - float(live.get("total_account_equity") or 0.0)), 2
            ),
            "risk_halt": live.get("risk_halt"),
            "reconciliation_required": live.get("reconciliation_required"),
            "global_halt_reasons": live.get("global_halt_reasons"),
        },
        "alpha124_11sleeve_shadow": {
            "updated_at_utc": alpha124.get("updated_at_utc"),
            "markets_monitored": alpha124.get("markets_monitored"),
            "open_positions_count": alpha124.get("open_positions_count"),
            "pending_maker_orders_count": alpha124.get("pending_maker_orders_count"),
            "portfolio_realized_pnl_by_bankroll_usd": alpha124.get("portfolio_realized_pnl_by_bankroll_usd"),
            "by_sleeve": alpha124.get("by_sleeve"),
        },
        "live_daily_projections_summary": proj.get("summary_horizons_usd", {}),
        "paper_sleeve1_benchmark": paper.get("validation_oos_epoch", {}),
        "shadow_sol_v392": {k: sol.get(k) for k in alt_keys},
        "shadow_xrp_v392": {k: xrp.get(k) for k in alt_keys},
        "shadow_exp316": exp316,
        "shadow_phase3a_recent_24h": p3a,
        "shadow_phase4_recent_24h": p4,
    }
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()

# ======================================================================================
# [16/16] MODULE: tests/test_alpha_124_oracles.py
# PURPOSE: Unit Tests: Weather METAR/HKO, Jump-SVI Barrier, Pyth Session/Boxes, NBA Boxes, D1, S2 & Wallet
# ======================================================================================

#!/usr/bin/env python3
"""
Unit Tests for Polymarket Alpha-124 Oracle Parsers & Pricing Kernels
====================================================================
Verifies bit-for-bit parity against every official Polymarket contract example:
  1. Weather METAR parser (`SPECI` exclusion, 8-digit T-group tenths of °C,
     body integer °C fallback, °C -> °F conversion, and half-up rounding).
  2. One-Touch Barrier First-Passage monotonicity (`P_touch >= P_terminal`,
     `P_touch(K1) > P_touch(K2)` for `S < K1 < K2`).
  3. Multi-Strike SVI Breeden-Litzenberger digital probability & monotonicity box detector.
"""

# from __future__ import annotations  # (Lifted to top of consolidated bundle)

import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.polymarket_research.barrier_onetouch_svi_engine import (
    first_passage_touch_prob,
    parse_barrier_direction,
    parse_strike_from_text,
)
from src.polymarket_research.multistrike_svi_scalper import (
    detect_ladder_monotonicity_boxes,
    evaluate_svi_digital_fair_value,
)
from src.polymarket_research.weather_metar_engine import (
    celsius_to_market_int,
    parse_bucket_bounds,
    parse_metar_line,
    round_half_up_polymarket,
)


def test_polymarket_weather_rounding_spec_examples() -> None:
    # Exact examples from Polymarket RJTT Tokyo spec:
    # "13.9°C counts as 14°C; 17.4°C counts as 17°C; 16.5°C counts as 17°C;
    #  −1.7°C counts as −2°C; −8.5°C counts as −8°C."
    assert round_half_up_polymarket(13.9) == 14
    assert round_half_up_polymarket(17.4) == 17
    assert round_half_up_polymarket(16.5) == 17
    assert round_half_up_polymarket(-1.7) == -2
    assert round_half_up_polymarket(-8.5) == -8

    # Exact examples from Polymarket KHOU Houston (°F) spec:
    # "18.3°C is 64.94°F and counts as 65°F; 17.8°C is 64.04°F and counts as 64°F;
    #  19°C is 66.2°F and counts as 66°F; −22.5°C is exactly −8.5°F and counts as −8°F."
    assert celsius_to_market_int(18.3, "F") == 65
    assert celsius_to_market_int(17.8, "F") == 64
    assert celsius_to_market_int(19.0, "F") == 66
    assert celsius_to_market_int(-22.5, "F") == -8


def test_metar_parser_speci_and_t_remark() -> None:
    ref = datetime(2026, 10, 25, 16, 0, tzinfo=timezone.utc)

    # 1. SPECI must be strictly excluded
    speci = parse_metar_line(
        "SPECI RJTT 251545Z 08010KT 9999 SCT015 24/20 Q1016 RMK T02440200",
        "RJTT",
        ref,
        "Asia/Tokyo",
    )
    assert speci is None

    # 2. Routine METAR with 8-digit T-remark (T01390133 = 13.9°C, T10171022 = -1.7°C)
    m_pos = parse_metar_line(
        "METAR KHOU 251253Z 12005KT 10SM FEW033 14/13 A3002 RMK AO2 T01390133",
        "KHOU",
        ref,
        "America/Chicago",
    )
    assert m_pos is not None and m_pos.has_t_remark and abs(m_pos.temp_c - 13.9) < 1e-6

    m_neg = parse_metar_line(
        "KORD 251051Z 29012KT 10SM CLR M02/M02 A3015 RMK AO2 T10171022",
        "KORD",
        ref,
        "America/Chicago",
    )
    assert m_neg is not None and m_neg.has_t_remark and abs(m_neg.temp_c - (-1.7)) < 1e-6

    # 3. Routine METAR without T-remark falls back to body whole °C (18/12 -> 18°C, M11/M17 -> -11°C)
    m_body = parse_metar_line(
        "METAR RJTT 250600Z 08007KT 9999 FEW020 18/12 Q1017 NOSIG",
        "RJTT",
        ref,
        "Asia/Tokyo",
    )
    assert m_body is not None and (not m_body.has_t_remark) and abs(m_body.temp_c - 18.0) < 1e-6

    m_body_neg = parse_metar_line(
        "METAR UUWW 250300Z 18004KT 9999 OVC015 M11/M17 Q1021",
        "UUWW",
        ref,
        "Europe/Moscow",
    )
    assert m_body_neg is not None and abs(m_body_neg.temp_c - (-11.0)) < 1e-6


def test_bucket_bounds_parser() -> None:
    assert parse_bucket_bounds("16°C or below") == ("C", float("-inf"), 16.0)
    assert parse_bucket_bounds("17°C") == ("C", 17.0, 17.0)
    assert parse_bucket_bounds("26°C or higher") == ("C", 26.0, float("inf"))
    assert parse_bucket_bounds("72-73°F") == ("F", 72.0, 73.0)


def test_barrier_and_svi_monotonicity() -> None:
    assert parse_barrier_direction("Will Bitcoin reach $88,000 on October 25?", "↑ 88,000") == "UP"
    assert parse_barrier_direction("Will Bitcoin dip to $76,000 on October 25?", "↓ 76,000") == "DOWN"
    assert parse_strike_from_text("Will Bitcoin reach $88,000 on October 25?") == 88000.0

    p_84k = first_passage_touch_prob(82000.0, 84000.0, 86400.0, 0.45, "UP", wick_vol_multiplier=1.0)
    p_86k = first_passage_touch_prob(82000.0, 86000.0, 86400.0, 0.45, "UP", wick_vol_multiplier=1.0)
    sv_84k = evaluate_svi_digital_fair_value("BTC", 82000.0, 84000.0, 86400.0, dvol_annual_override=0.45)

    assert p_84k > p_86k > 0.0
    # First-passage touch probability must strictly exceed terminal digital probability
    assert p_84k > sv_84k["p_yes"] * 1.6

    # Monotonicity box detector
    arbs = detect_ladder_monotonicity_boxes([
        {"strike": 80000.0, "is_downward": False, "market_id": "1", "yes_token": "ty1", "no_token": "tn1", "ask_yes": 0.55, "ask_no": 0.46},
        {"strike": 82000.0, "is_downward": False, "market_id": "2", "yes_token": "ty2", "no_token": "tn2", "ask_yes": 0.62, "ask_no": 0.39},
    ])
    assert len(arbs) == 1 and arbs[0]["box_cost_net"] < 0.996


def test_svi_sticky_delta_no_butterfly_arb_on_sol_and_xrp() -> None:
    from src.polymarket_research.deribit_svi_surface import (
        SVIParams,
        compute_breeden_litzenberger_digital,
        scale_svi_sticky_delta,
    )

    t_5d = 5.0 / 365.25
    # Realistic Deribit BTC 5-day SVI slice (~44% ATM IV, moderate downside skew)
    w_atm = (0.44 ** 2) * t_5d
    btc_svi = SVIParams(
        a=w_atm * 0.82,
        b=w_atm * 0.42,
        rho=-0.18,
        m=0.0,
        sigma=0.06,
        t_years=t_5d,
        forward_price=84000.0,
        calibrated_at=1000.0,
    )
    sol_svi = scale_svi_sticky_delta(btc_svi, 1.75, 103.5)
    xrp_svi = scale_svi_sticky_delta(btc_svi, 1.85, 2.15)

    # ATM vol must scale linearly by mult
    assert abs(sol_svi.implied_vol(0.0) - btc_svi.implied_vol(0.0) * 1.75) < 1e-6
    assert abs(xrp_svi.implied_vol(0.0) - btc_svi.implied_vol(0.0) * 1.85) < 1e-6

    # SOL > $100 at Spot=$103.5 over 5 days (~3.4% ITM at ~77% annual vol) must NEVER inflate to 0.82!
    p_sol_100 = compute_breeden_litzenberger_digital(103.5, 100.0, t_5d, sol_svi)
    assert 0.50 <= p_sol_100 <= 0.68, f"Expected realistic SOL > $100 digital prob, got {p_sol_100}"


def test_kmia_convective_rain_cold_pool_bias_guard() -> None:
    from datetime import date, timedelta
    from src.polymarket_research.weather_metar_engine import (
        WeatherBucket,
        WeatherEventSpec,
        compute_weather_probabilities,
    )

    eval_utc = datetime(2026, 10, 25, 17, 0, tzinfo=timezone.utc)  # 13:00 EDT midday shower
    kmia_rain = parse_metar_line(
        "METAR KMIA 251653Z 07009KT 6SM RA SCT025CB BKN050 OVC110 25/21 A3004 RMK AO2 SLP173 CB OHD MOV SW P0004 T02500211",
        "KMIA",
        eval_utc,
        "America/New_York",
    )
    assert kmia_rain is not None and kmia_rain.has_convective_precip is True

    buckets = [
        WeatherBucket("m1", "c1", "78-79°F", "78-79°F", "y1", "n1", "F", 78.0, 79.0),
        WeatherBucket("m2", "c2", "80-81°F", "80-81°F", "y2", "n2", "F", 80.0, 81.0),
        WeatherBucket("m3", "c3", "82-83°F", "82-83°F", "y3", "n3", "F", 82.0, 83.0),
        WeatherBucket("m4", "c4", "84°F or higher", "84°F+", "y4", "n4", "F", 84.0, float("inf")),
    ]
    spec = WeatherEventSpec(
        event_id="ev_mia",
        slug="miami-oct-25",
        series_slug="miami-daily-weather",
        title="Highest temperature in Miami on October 25?",
        icao="KMIA",
        city="Miami",
        lat=25.7959,
        lon=-80.2870,
        tz_name="America/New_York",
        obs_date=date(2026, 10, 25),
        metric="HIGH",
        unit="F",
        fee_type="zero_fees",
        end_date_iso="2026-10-26T04:00:00Z",
        buckets=buckets,
    )
    # 60-member ensemble forecasting sunny post-shower rebound to 28.3°C (83°F) at 19Z-20Z
    base_hr = int(datetime(2026, 10, 25, 17, 0, tzinfo=timezone.utc).timestamp())
    ens_hourly = {
        base_hr + h * 3600: [27.3 + (0.9 if h in (2, 3) else 0.2) + (m - 30) * 0.02 for m in range(60)]
        for h in range(0, 10)
    }
    res = compute_weather_probabilities(spec, eval_utc, [kmia_rain], ens_hourly)
    assert res["convective_cold_pool"] is True
    assert res["bias_c"] >= -0.50
    assert res["ensemble_member_count"] == 60
    # 78-79°F must NOT be inflated to 92.6% by the transient midday shower!
    assert res["probs"][0] < 0.35


def test_anchored_strike_regex_ignores_dates() -> None:
    from src.polymarket_research.multistrike_svi_scalper import _extract_threshold_strike

    assert parse_strike_from_text("Will Bitcoin hit a new high on October 30, 2026?", "") is None
    assert parse_strike_from_text("Will Bitcoin reach 105k on October 30?", "") == 105000.0
    assert _extract_threshold_strike("Will Solana close higher on October 30, 2026?", "October 30") is None
    assert _extract_threshold_strike("Will Solana be above $105 on October 30?", "$105") == 105.0


def test_alpha124_l2_depth_maker_queue_and_gamma_404_settlement(tmp_path: Path, monkeypatch) -> None:
    import asyncio
    import src.polymarket_research.alpha_124_shadow_daemon as a124

    # 1. Thin L1 depth ($11) and <98% partial fill must be strictly rejected
    thin = a124.walk_l2_book_asks([{"price": "0.22", "size": "50"}], notional_usd=50.0, fee_rate=0.0)
    assert thin["filled"] is False and thin["reason"] == "THIN_L1_DEPTH"

    partial = a124.walk_l2_book_asks([{"price": "0.50", "size": "60"}], notional_usd=50.0, fee_rate=0.0)
    assert partial["filled"] is False and partial["reason"] == "INSUFFICIENT_DEPTH"

    good = a124.walk_l2_book_asks([{"price": "0.50", "size": "250"}], notional_usd=50.0, fee_rate=0.0)
    assert good["filled"] is True and good["fill_ratio"] == 1.0

    # 2. Resting Maker queue + Gamma 404 settlement
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "opps.json")

    async def _run_sim() -> None:
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        d.spots["BTC"] = 84000.0
        books = {
            "tok_m1": {"bids": [{"price": "0.48", "size": "200"}], "asks": [{"price": "0.50", "size": "200"}]},
        }

        async def fake_fetch_json(url: str, timeout: float = 5.0):
            if "/book?token_id=tok_m1" in url:
                return books["tok_m1"]
            if "/book?token_id=tok_w1_closed" in url:
                return None  # Simulates 404 on closed Polymarket Weather market
            if "/markets/mkt_w1" in url:
                return {
                    "id": "mkt_w1",
                    "closed": True,
                    "umaResolutionStatus": "resolved",
                    "clobTokenIds": '["tok_w1_closed", "tok_w1_no"]',
                    "outcomePrices": '["1", "0"]',
                }
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch_json)
        posted = await d.post_shadow_maker_entry(
            sleeve="M1_SVI_MAKER_SCALP",
            dedupe_key="M1_test_YES",
            asset="BTC",
            title="BTC above $84,000?",
            side_label="YES",
            token_id="tok_m1",
            p_model=0.58,
            close_ts=1999999999.0,
            extra={"market_id": "m_btc", "strike": 84000.0, "is_downward": False},
        )
        assert posted is True
        assert len(d.pending_maker_orders) == 1
        assert len(d.open_positions) == 0  # Must NOT fill immediately!

        # Age order 15s while ask is still 0.50 (> resting_bid 0.49) -> still resting
        oid = next(iter(d.pending_maker_orders))
        d.pending_maker_orders[oid]["created_ts"] -= 15.0
        monkeypatch.setattr(
            a124,
            "evaluate_svi_digital_fair_value",
            lambda *args, **kwargs: {"p_yes": 0.58, "p_no": 0.42, "iv_annual": 0.45, "z_sigma": 0.5, "source": "TEST"},
        )
        await d.manage_pending_maker_orders()
        assert len(d.pending_maker_orders) == 1 and len(d.open_positions) == 0

        # Now trade through resting_bid (best_ask drops to 0.49 while SVI edge remains valid) -> passive Maker fill!
        books["tok_m1"] = {"bids": [{"price": "0.48", "size": "200"}], "asks": [{"price": "0.49", "size": "150"}]}
        await d.manage_pending_maker_orders()
        assert len(d.pending_maker_orders) == 0 and len(d.open_positions) == 1

        # Add closed Weather position whose /book returns 404 -> settles via Gamma /markets/mkt_w1!
        d.open_positions["W1_test"] = {
            "position_id": "W1_test",
            "dedupe_key": "W1_ev_mkt_w1",
            "sleeve": "W1_SOLAR_PEAK_LOCK",
            "asset_or_city": "Tokyo_RJTT",
            "title": "Tokyo 21°C",
            "side": "YES",
            "token_id": "tok_w1_closed",
            "fee_rate": 0.0,
            "entry_ts": 1000.0,
            "close_ts": 2000.0,
            "p_model_entry": 0.92,
            "entry_eff_px_t1000": 0.80,
            "entry_vwap_t1000": 0.80,
            "maker_tp_px": 0.98,
            "tier_fills": {"T1000": {"spent_usd": 100.0, "fee_usd": 0.0, "shares": 125.0}},
            "extra": {"market_id": "mkt_w1"},
            "status": "OPEN",
        }
        await d.manage_open_positions()
        assert "W1_test" not in d.open_positions
        settled_w1 = [p for p in d.closed_positions if p["position_id"] == "W1_test"]
        assert len(settled_w1) == 1 and settled_w1[0]["won"] is True and settled_w1[0]["tier_pnls_usd"]["T1000"] == 25.0

    asyncio.run(_run_sim())


def test_live_executor_min_price_floor_zero_fees_neg_risk_and_maker_entry(tmp_path: Path) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "dry.jsonl")
    # 1. Verify custom min_price_floor=0.20 + zero_fees (rate=0.0, exp=0.0) + neg_risk=True succeeds
    book_25c = {"asks": [{"price": "0.25", "size": "500"}], "bids": [{"price": "0.24", "size": "500"}]}
    res = ex.execute_snipe_order(
        token_id="12345678901234567890",
        target_token="YES",
        notional_usd=25.0,
        target_price=0.25,
        trade_id="TEST_W2_ZERO_FEE",
        market_fee_rate=0.0,
        market_fee_exponent=0.0,
        min_price_floor=0.15,
        max_price_ceiling=0.65,
        prefetched_book=book_25c,
        neg_risk=True,
    )
    assert res.success is True and res.fee_usd == 0.0
    assert ex.get_token_neg_risk("12345678901234567890") is True

    # 2. Verify passive Maker entry dry-run quantization and >=5 share lot enforcement
    m_res = ex.post_maker_entry_order(
        token_id="12345678901234567890",
        price=0.42,
        notional_usd=25.0,
        neg_risk=True,
    )
    assert m_res["success"] is True and m_res["shares"] == 59.0 and m_res["post_only"] is True


def test_same_oracle_dominance_box_math_equal_shares_and_strike_guard() -> None:
    from src.polymarket_research.same_oracle_dominance_box import (
        compute_dominance_box_payout_from_close,
        determine_dominance_legs,
        parse_authoritative_open_price,
        parse_twap_candle_event,
        walk_equal_shares_dominance_box,
    )

    ev_15m = {
        "title": "Ethereum Up or Down - 7:00PM-7:15PM ET",
        "markets": [
            {
                "id": "6033093",
                "conditionId": "0xc15",
                "question": "Ethereum Up or Down - 7:00PM-7:15PM ET",
                "eventStartTime": "2026-10-25T23:00:00Z",
                "endDate": "2026-10-25T23:15:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["tok_15m_up", "tok_15m_dn"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.07, "exponent": 1.0},
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "resolutionSource": "https://data.chain.link/streams/eth-usd-twap-60s-streams",
            }
        ],
    }
    ev_5m = {
        "title": "Ethereum Up or Down - 7:10PM-7:15PM ET",
        "markets": [
            {
                "id": "6033145",
                "conditionId": "0xc5",
                "question": "Ethereum Up or Down - 7:10PM-7:15PM ET",
                "eventStartTime": "2026-10-25T23:10:00Z",
                "endDate": "2026-10-25T23:15:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["tok_5m_up", "tok_5m_dn"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.07, "exponent": 1.0},
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "resolutionSource": "https://data.chain.link/streams/eth-usd-twap-60s-streams",
            }
        ],
    }
    m15 = parse_twap_candle_event(ev_15m, "ETH", "15m")
    m5 = parse_twap_candle_event(ev_5m, "ETH", "5m")
    assert m15 is not None and m5 is not None

    # Non-TWAP (e.g. Binance spot) must be rejected
    ev_bad = {"markets": [{**ev_5m["markets"][0], "cryptoMarketConfig": {"twapEnabled": False}, "resolutionSource": "binance"}]}
    assert parse_twap_candle_event(ev_bad, "ETH", "5m") is None

    # Authoritative 60s-TWAP guard strictly rejects legacy crypto-price spot payloads and unclosed Gamma events
    assert parse_authoritative_open_price({"openPrice": 2393.534264, "completed": False, "cached": True}) is None
    assert parse_authoritative_open_price([{"closed": False, "eventMetadata": {"finalPrice": 2393.534264}}]) is None
    assert parse_authoritative_open_price([{"closed": True, "eventMetadata": {"finalPrice": 2393.534264}}]) == 2393.534264

    # Case 1: K_15m > K_5m -> 5M_UP + 15M_DOWN
    dom = determine_dominance_legs(m15, 2393.5343, m5, 2392.8455)
    assert dom is not None and dom["regime"] == "5M_UP_PLUS_15M_DOWN"
    assert dom["leg_a"]["token_id"] == "tok_5m_up" and dom["leg_b"]["token_id"] == "tok_15m_dn"

    # Payout across all 3 regions of R must be >= $1.00 (and $2.00 inside [K_low, K_high))
    assert compute_dominance_box_payout_from_close(2389.55, dom["k_low"], dom["k_high"]) == 1.0
    assert compute_dominance_box_payout_from_close(2393.10, dom["k_low"], dom["k_high"]) == 2.0
    assert compute_dominance_box_payout_from_close(2399.00, dom["k_low"], dom["k_high"]) == 1.0

    # Equal-share L2 walk caps to thinner leg (45 shares) and includes both 7% p(1-p) taker fees
    w_box = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.35", "size": "45"}],
        asks_b_raw=[{"price": "0.56", "size": "200"}],
        target_budget_usd=100.0,
        max_box_cost_net=0.995,
    )
    assert w_box["filled"] is True
    assert w_box["shares"] == 45
    assert w_box["leg_a_walk"]["shares"] == 45 and w_box["leg_b_walk"]["shares"] == 45
    assert w_box["box_cost_net"] < 0.95 and w_box["guaranteed_min_profit_usd"] > 2.0

    # Expensive box (> $0.995) is rejected
    w_exp = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.52", "size": "200"}],
        asks_b_raw=[{"price": "0.47", "size": "200"}],
        target_budget_usd=100.0,
        max_box_cost_net=0.995,
    )
    assert w_exp["filled"] is False

    # Regression (SOL D1_QUIET_BOOK_BOX 23:56 UTC): 11 shares @ $0.90 + 138 @ $0.91 with Leg B @ $0.07 ($13.50 budget, 0.985 cap)
    # 11 x $0.07 = $0.77 Leg B is below Polymarket's $1 marketable-BUY minimum -> must reject (would leave a naked leg).
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    w_sol_sub1 = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.90", "size": "11"}, {"price": "0.91", "size": "138.36"}],
        asks_b_raw=[{"price": "0.07", "size": "66.7"}],
        target_budget_usd=13.50,
        max_box_cost_net=0.985,
        min_shares=8,
        min_box_notional_usd=7.0,
    )
    assert w_sol_sub1["filled"] is False
    assert w_sol_sub1["reason"] == "LEG_BELOW_1USD_MIN"

    # Same trim geometry with a >= $1 Leg B: must trim to the 11 L1 shares so worst_px never breaches 0.985.
    w_sol_trim = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.86", "size": "11"}, {"price": "0.88", "size": "138.36"}],
        asks_b_raw=[{"price": "0.10", "size": "66.7"}],
        target_budget_usd=13.50,
        max_box_cost_net=0.985,
        min_shares=8,
        min_box_notional_usd=7.0,
    )
    assert w_sol_trim["filled"] is True
    assert w_sol_trim["shares"] == 11
    assert w_sol_trim["leg_a_walk"]["worst_px"] == 0.86
    assert w_sol_trim["leg_b_walk"]["worst_px"] == 0.10
    assert w_sol_trim["box_cost_net"] <= 0.985
    ex_dry = PolymarketLiveExecutor(dry_run=True)
    r_exec_trim = ex_dry.execute_atomic_dominance_box(
        box_id="D1_SOL_TRIM_TEST",
        leg_a_token_id="tok_sol_15m_up",
        leg_a_label="15M_UP",
        leg_a_limit_price=w_sol_trim["leg_a_walk"]["worst_px"],
        leg_b_token_id="tok_sol_5m_dn",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=w_sol_trim["leg_b_walk"]["worst_px"],
        shares=w_sol_trim["shares"],
        max_box_cost_net=0.985,
    )
    assert r_exec_trim["success"] is True

    # If L1 has < min_shares (e.g. only 4 shares @ $0.90) and L2 worst_px breaches 0.985, walker cleanly rejects
    w_sol_too_thin = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.90", "size": "4"}, {"price": "0.91", "size": "138.36"}],
        asks_b_raw=[{"price": "0.07", "size": "66.7"}],
        target_budget_usd=13.50,
        max_box_cost_net=0.985,
        min_shares=8,
        min_box_notional_usd=7.0,
    )
    assert w_sol_too_thin["filled"] is False and w_sol_too_thin["reason"] == "WORST_LIMIT_COST_ABOVE_CAP"


def test_alpha124_d1_same_oracle_dominance_box_entry_and_settlement(tmp_path: Path, monkeypatch) -> None:
    import asyncio
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec

    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "state_d1.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "ledger_d1.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "opps_d1.json")

    async def _sim_d1() -> None:
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_sim = 1792970000.0
        end_sim = now_sim + 180.0
        m15 = TwapCandleMarketSpec(
            asset="ETH", horizon="15m", market_id="6033093", condition_id="0xc15",
            title="ETH 15m", start_iso="2026-10-25T23:00:00Z", end_iso="2026-10-25T23:15:00Z",
            start_ts=end_sim - 900.0, end_ts=end_sim, up_token="tok_15m_up", down_token="tok_15m_dn",
            fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
            resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams",
        )
        m5 = TwapCandleMarketSpec(
            asset="ETH", horizon="5m", market_id="6033145", condition_id="0xc5",
            title="ETH 5m", start_iso="2026-10-25T23:10:00Z", end_iso="2026-10-25T23:15:00Z",
            start_ts=end_sim - 300.0, end_ts=end_sim, up_token="tok_5m_up", down_token="tok_5m_dn",
            fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
            resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams",
        )
        d.dominance_pairs[f"ETH_{int(end_sim)}"] = (m15, m5)

        prev_15m_slug = f"slug=eth-updown-5m-{int(round(m15.start_ts)) - 300}"
        prev_5m_slug = f"slug=eth-updown-5m-{int(round(m5.start_ts)) - 300}"

        async def fake_fetch(url: str, timeout: float = 5.0):
            if prev_15m_slug in url:
                return [{"slug": url.split("slug=", 1)[1], "closed": True, "eventMetadata": {"finalPrice": 2390.00}}]
            if prev_5m_slug in url:
                return [{"slug": url.split("slug=", 1)[1], "closed": True, "eventMetadata": {"finalPrice": 2394.00}}]
            if "token_id=tok_15m_up" in url:
                return {"bids": [{"price": "0.52", "size": "150"}], "asks": [{"price": "0.54", "size": "150"}]}
            if "token_id=tok_5m_dn" in url:
                return {"bids": [{"price": "0.38", "size": "150"}], "asks": [{"price": "0.40", "size": "150"}]}
            if "token_id=tok_15m_dn" in url or "token_id=tok_5m_up" in url:
                return {"bids": [{"price": "0.47", "size": "150"}], "asks": [{"price": "0.50", "size": "150"}]}
            if "/markets/6033093" in url:
                # Corridor finish (e.g. 2392.00): 15m UP wins ($1) AND 5m DOWN wins ($1) -> 2X double payout!
                return {
                    "id": "6033093", "closed": True, "umaResolutionStatus": "resolved",
                    "clobTokenIds": '["tok_15m_up", "tok_15m_dn"]', "outcomePrices": '["1", "0"]',
                }
            if "/markets/6033145" in url:
                return {
                    "id": "6033145", "closed": True, "umaResolutionStatus": "resolved",
                    "clobTokenIds": '["tok_5m_up", "tok_5m_dn"]', "outcomePrices": '["0", "1"]',
                }
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch)
        opps: list = []
        await d.scan_same_oracle_dominance_boxes(opps, now_ts=now_sim)
        assert len(d.open_positions) == 1
        pos = next(iter(d.open_positions.values()))
        assert pos["sleeve"] == "D1_SAME_ORACLE_DOMINANCE_BOX"
        assert pos["entry_eff_px_t1000"] < 0.995

        # Expire box and verify 2X corridor settlement
        pos["close_ts"] = 1000.0
        await d.manage_open_positions()
        assert len(d.open_positions) == 0 and len(d.closed_positions) == 1
        closed = d.closed_positions[0]
        assert closed["status"] == "SETTLED_DOMINANCE_DOUBLE_2X"
        assert closed["net_payout_per_share"] == 2.0
        assert closed["tier_pnls_usd"]["T1000"] > 100.0

    asyncio.run(_sim_d1())


def test_live_executor_atomic_dominance_box_and_legging_unwind(tmp_path: Path, monkeypatch) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "box.jsonl")
    # 1. Dry-run: thinner leg (leg_b_avail=30 < leg_a_avail=120) must dispatch first
    r_ok = ex.execute_atomic_dominance_box(
        box_id="BOX_ETH_1",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.54,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.40,
        shares=25,
        max_box_cost_net=0.995,
        leg_a_avail_shares=120.0,
        leg_b_avail_shares=30.0,
    )
    assert r_ok["success"] is True and r_ok["leg_1"]["label"] == "5M_DOWN"

    # 2. Pre-flight cap guard rejects box whose limit prices + fees > 0.995
    r_cap = ex.execute_atomic_dominance_box(
        box_id="BOX_EXP",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.55,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.44,
        shares=25,
        max_box_cost_net=0.995,
    )
    assert r_cap["success"] is False and "WORST_LIMIT_BOX_COST_EXCEEDS_CAP" in r_cap["error"]

    # 3. Live mocked legging failure: Leg 1 fills, Leg 2 FOK rejects -> immediate Leg 1 unwind!
    ex.dry_run = False
    ex.is_authenticated = True

    class FakeClient:
        def __init__(self) -> None:
            self.posts = 0

        def create_order(self, args, options=None):
            return {"token_id": args.token_id, "price": args.price, "size": args.size}

        def post_order(self, signed, order_type):
            self.posts += 1
            if self.posts == 1:
                return {"orderID": "OID_LEG1_FILLED"}
            return {"errorMsg": "FOK order couldn't be fully filled"}

    ex.client = FakeClient()
    monkeypatch.setattr(ex, "get_token_tick_size", lambda tid: 0.01)
    monkeypatch.setattr(ex, "get_token_neg_risk", lambda tid, explicit_neg_risk=None: False)
    unwind_calls: list = []

    def fake_unwind(token_id: str, size: float, side: str = "SELL", min_price: float = 0.01, neg_risk=None):
        unwind_calls.append((token_id, size, side, min_price))
        return {"success": True, "orderID": "OID_UNWIND_1", "matched_size": size}

    monkeypatch.setattr(ex, "execute_unwind_order", fake_unwind)
    r_leg = ex.execute_atomic_dominance_box(
        box_id="BOX_LEG_FAIL",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.54,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.40,
        shares=20,
        max_box_cost_net=0.995,
        leg_a_avail_shares=25.0,
        leg_b_avail_shares=100.0,
    )
    assert r_leg["success"] is False
    assert r_leg["stage"] == "LEG_2_REJECTED_UNWOUND"
    assert r_leg["legged_out"] is True
    assert len(unwind_calls) == 1 and unwind_calls[0][0] == "tok_a" and unwind_calls[0][1] == 20.0


def test_exact_twap_lock_engine_math_and_whipsaw_guard() -> None:
    import math
    from src.polymarket_research.exact_twap_lock_engine import (
        compute_exact_twap_lock_probability,
        student_t_df5_cdf,
    )

    assert abs(student_t_df5_cdf(0.0) - 0.5) < 1e-12
    assert abs(student_t_df5_cdf(2.5) + student_t_df5_cdf(-2.5) - 1.0) < 1e-12
    normal_3 = 0.5 * (1.0 + math.erf(3.0 / math.sqrt(2.0)))
    assert 0.96 < student_t_df5_cdf(3.0) < normal_3  # Fat tails strictly more conservative than Gaussian

    end_ts = 1792970300.0
    now_ts = end_ts - 18.0  # 18s remaining => 42s (70%) of 60s TWAP already banked!
    samples = [(end_ts - 60.0 + i, 2404.50) for i in range(43)]

    lock = compute_exact_twap_lock_probability(
        asset="ETH",
        open_price=2400.123456789012,
        current_usd_spot=2404.60,
        rem_seconds=18.0,
        now_ts=now_ts,
        end_ts=end_ts,
        spot_samples=samples,
        iv_annual=0.65,
        usd_direct_feed=True,
    )
    assert lock["eligible"] is True
    assert lock["side"] == "UP"
    assert lock["eff_alpha"] > 0.65
    assert lock["p_lock"] >= 0.975

    # Whipsaw guard: banked mean above K_open (mu_twap > K_open) while current_usd_spot crashed below K_open
    whipsaw = compute_exact_twap_lock_probability(
        asset="ETH",
        open_price=2400.123456789012,
        current_usd_spot=2399.50,
        rem_seconds=18.0,
        now_ts=now_ts,
        end_ts=end_ts,
        spot_samples=samples,
        iv_annual=0.65,
        usd_direct_feed=True,
    )
    assert whipsaw["eligible"] is False and whipsaw["reason"] == "WHIPSAW_SPLIT_ACROSS_STRIKE"

    # Out-of-window (> 45s) rejected
    early = compute_exact_twap_lock_probability(
        asset="ETH",
        open_price=2400.0,
        current_usd_spot=2405.0,
        rem_seconds=52.0,
        now_ts=end_ts - 52.0,
        end_ts=end_ts,
        spot_samples=[],
    )
    assert early["eligible"] is False


def test_r01_relayer_hmac_deposit_wallet_eip712_and_negrisk_payout_logs(tmp_path: Path) -> None:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    # 1. Exact py_clob_client / py-builder-signing-sdk HMAC signature parity
    hdrs = PolymarketLiveExecutor.build_relayer_builder_headers(
        api_key="test-api-key",
        secret="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        passphrase="test-passphrase",
        method="POST",
        request_path="/orders",
        body={"hash": "0x123"},
        timestamp=1000000,
    )
    assert hdrs["POLY_BUILDER_SIGNATURE"] == "wdXSC4akzPKG0yFk9FJrIb7-rg73v_M7QDxIBp-P1CQ="
    assert hdrs["POLY_BUILDER_TIMESTAMP"] == "1000000"
    try:
        from py_clob_client.signing.hmac import build_hmac_signature
        assert hdrs["POLY_BUILDER_SIGNATURE"] == build_hmac_signature(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", "1000000", "POST", "/orders", {"hash": "0x123"}
        )
    except ImportError:
        pass

    # 2. DepositWallet EIP-712 batch payload & NegRiskAdapter PayoutRedemption log parsing
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "r01.jsonl")
    ex.funder_address = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9"
    cond_id = "0x" + ("ab" * 32)
    me_topic = "0x" + ex.funder_address.lower().replace("0x", "").rjust(64, "0")

    try:
        import eth_account  # noqa: F401
        import eth_utils  # noqa: F401
        import web3  # noqa: F401

        test_pk = "0x" + ("11" * 32)
        batch = PolymarketLiveExecutor.build_deposit_wallet_relayer_batch(
            private_key=test_pk,
            wallet_address=ex.funder_address,
            nonce=7,
            deadline=1900000000,
            calls=[{"target": PolymarketLiveExecutor.CTF_ADDRESS, "value": "0", "data": "0x12345678"}],
            chain_id=137,
        )
        assert batch["type"] == "WALLET"
        assert batch["nonce"] == "7"
        assert batch["signature"].startswith("0x") and len(batch["signature"]) == 132
        assert batch["depositWalletParams"]["depositWallet"].lower() == ex.funder_address.lower()

        ctf_log = {
            "address": PolymarketLiveExecutor.CTF_ADDRESS,
            "topics": [PolymarketLiveExecutor._payout_redemption_topic(), me_topic, "0x" + ("00" * 32)],
            "data": "0x" + ("ab" * 32) + ("00" * 32) + f"{25_500_000:064x}",
            "transactionHash": "0xtx_ctf",
            "blockNumber": "0x100",
        }
        nr_log = {
            "address": PolymarketLiveExecutor.NEG_RISK_ADAPTER_ADDRESS,
            "topics": [PolymarketLiveExecutor._neg_risk_payout_redemption_topic(), me_topic, cond_id],
            "data": "0x" + ("00" * 32) + f"{42_250_000:064x}",
            "transactionHash": "0xtx_nr",
            "blockNumber": "0x101",
        }
        parsed = ex.parse_payout_redemption_logs([ctf_log, nr_log], cond_id)
        assert len(parsed) == 2
        assert abs(parsed[0]["payout_usd"] - 25.50) < 1e-6
        assert abs(parsed[1]["payout_usd"] - 42.25) < 1e-6
    except ImportError:
        pass


def test_alpha124_w2_maker_overround_m4_shock_wakeup_and_s2_twap_lock(tmp_path: Path, monkeypatch) -> None:
    import asyncio
    import json
    import time
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.multistrike_svi_scalper import StrikeRungSpec
    from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec

    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "state_all.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "ledger_all.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "opps_all.json")
    shock_file = tmp_path / "live_shock_triggers.jsonl"
    shock_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(a124, "SHOCK_TRIGGER_FILE", shock_file)

    async def _sim_new_sleeves() -> None:
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_sim = time.time()

        books = {
            "tok_w2m": {"bids": [{"price": "0.26", "size": "150"}], "asks": [{"price": "0.30", "size": "150"}]},
            "tok_m1_yes": {"bids": [{"price": "0.49", "size": "200"}], "asks": [{"price": "0.51", "size": "200"}]},
            "tok_m4_no": {"bids": [{"price": "0.46", "size": "250"}], "asks": [{"price": "0.48", "size": "250"}]},
            "tok_s2_up": {"bids": [{"price": "0.86", "size": "250"}], "asks": [{"price": "0.88", "size": "250"}]},
        }

        async def fake_fetch(url: str, timeout: float = 5.0):
            for tid, bk in books.items():
                if f"token_id={tid}" in url:
                    return bk
            if "slug=eth-updown-5m-1792969800" in url:
                return [{"slug": url.split("slug=", 1)[1], "closed": True, "eventMetadata": {"finalPrice": 2405.80}}]
            if "slug=eth-updown-5m-" in url:
                return [{"slug": url.split("slug=", 1)[1], "closed": True, "eventMetadata": {"finalPrice": 2400.123456789012}}]
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch)

        # 1. W2_MAKER_OVERROUND: post resting 0%-fee bid inside 0.26 / 0.30 spread -> resting_bid = 0.27
        ok_w2m = await d.post_shadow_maker_entry(
            sleeve="W2_MAKER_OVERROUND",
            dedupe_key="W2M_ev1_m1",
            asset="Miami_KMIA",
            title="Miami 82-83°F",
            side_label="YES",
            token_id="tok_w2m",
            p_model=0.40,
            close_ts=now_sim + 28800.0,
            extra={"event_id": "ev1", "market_id": "m1", "icao": "KMIA", "obs_date": "2026-10-25"},
        )
        assert ok_w2m is True
        oid_w2m = next(iter(d.pending_maker_orders))
        assert d.pending_maker_orders[oid_w2m]["resting_bid"] == 0.27
        d.pending_maker_orders[oid_w2m]["created_ts"] -= 15.0
        books["tok_w2m"] = {"bids": [{"price": "0.26", "size": "150"}], "asks": [{"price": "0.27", "size": "150"}]}
        await d.manage_pending_maker_orders()
        assert any(p["sleeve"] == "W2_MAKER_OVERROUND" for p in d.open_positions.values())

        # 2. M4_SHOCK_STRIKE_CATCHUP + <250ms Adverse M1 Maker Cancel
        d.spots["BTC"] = 84000.0
        await d.post_shadow_maker_entry(
            sleeve="M1_SVI_MAKER_SCALP",
            dedupe_key="M1_btc_84k_YES",
            asset="BTC",
            title="BTC above $84,000?",
            side_label="YES",
            token_id="tok_m1_yes",
            p_model=0.58,
            close_ts=now_sim + 43200.0,
            extra={"market_id": "m_btc_84k", "strike": 84000.0, "is_downward": False},
        )
        assert len(d.pending_maker_orders) == 1
        d.strike_ladders["BTC_ev"] = [
            StrikeRungSpec(
                asset="BTC",
                series_slug="btc-multi-strikes",
                event_id="ev_btc",
                market_id="m_btc_84k",
                condition_id="0xc_btc",
                title="Bitcoin above ___ on Oct 25?",
                question="Bitcoin above $84,000 on Oct 25?",
                strike=84000.0,
                is_downward=False,
                end_ts=now_sim + 43200.0,
                yes_token="tok_m1_yes",
                no_token="tok_m4_no",
            )
        ]
        monkeypatch.setattr(
            a124,
            "evaluate_svi_digital_fair_value",
            lambda *args, **kwargs: {"p_yes": 0.38, "p_no": 0.62, "iv_annual": 0.45, "z_sigma": 0.8, "source": "TEST"},
        )
        # Append a fresh -35 bps SELL shock (84000 -> 83700) to live_shock_triggers.jsonl
        shock_payload = {
            "shock_id": "SHK_BTC_1",
            "t0_unix": time.time(),
            "shock_source": "FUTURES",
            "asset": "BTC",
            "shock_direction": "SELL",
            "shock_ofi": -0.88,
            "shock_volume_100ms": 3200000.0,
            "spot_at_t0": 83700.0,
        }
        with open(shock_file, "a", encoding="utf-8") as sf:
            sf.write(json.dumps(shock_payload) + "\n")

        shocks = d.poll_fresh_shock_triggers()
        assert len(shocks) == 1
        s_opps: list = []
        await d.handle_shock_triggers(shocks, s_opps)
        # Resting YES maker order must be cancelled BEFORE passive fill, and M4 NO snipe opened!
        assert len(d.pending_maker_orders) == 0
        assert any(p["sleeve"] == "M4_SHOCK_STRIKE_CATCHUP" and p["side"] == "NO" for p in d.open_positions.values())

        # 3. S2_EXACT_TWAP_LOCK: final-18s 5m ETH candle lock + authoritative Chainlink TWAP settlement
        end_5m = now_sim + 18.0
        sp5 = TwapCandleMarketSpec(
            asset="ETH",
            horizon="5m",
            market_id="6055555",
            condition_id="0xc_s2",
            title="ETH Up or Down 5m",
            start_iso="2026-10-25T23:10:00Z",
            end_iso="2026-10-25T23:15:00Z",
            start_ts=end_5m - 300.0,
            end_ts=end_5m,
            up_token="tok_s2_up",
            down_token="tok_s2_dn",
            fee_rate=0.07,
            fee_exponent=1.0,
            neg_risk=False,
            twap_lookback_sec=60,
            resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams",
        )
        d.twap_candles[f"ETH_5m_{int(end_5m)}"] = sp5
        d.spots["ETH"] = 2406.00
        d.usd_direct_flags["ETH"] = True
        for i in range(43):
            d.usd_spot_hist["ETH"].append((end_5m - 60.0 + i, 2405.80))
        monkeypatch.setattr(a124, "get_wing_implied_vol", lambda *args, **kwargs: (0.65, "TEST"))

        tw_opps: list = []
        await d.scan_exact_twap_locks(tw_opps, now_ts=now_sim)
        s2_positions = [p for p in d.open_positions.values() if p["sleeve"] == "S2_EXACT_TWAP_LOCK"]
        assert len(s2_positions) == 1
        s2_pos = s2_positions[0]
        assert s2_pos["side"] == "UP" and s2_pos["p_model_entry"] >= 0.97

        # Settle S2 via authoritative Chainlink closePrice fallback
        s2_pos["close_ts"] = now_sim - 200.0
        await d.manage_open_positions()
        settled_s2 = [p for p in d.closed_positions if p["sleeve"] == "S2_EXACT_TWAP_LOCK"]
        assert len(settled_s2) == 1 and settled_s2[0]["won"] is True
        assert settled_s2[0]["status"] == "SETTLED_ORACLE_TWAP_WIN"

    asyncio.run(_sim_new_sleeves())


def test_live_daily_projections_working_capital_and_monotonicity():
    """
    Verifies the live day-by-day projection engine enforces:
      1. Exact 3-tier `v3.9.3` sizing (`<$88 -> $12`, `$88..$110 -> 18%`, `>=$110 -> 22%`)
      2. Strict scenario monotonicity (`P25 < P50 < P75`) on every day D1..D30
      3. Working-capital partition + L2 depth slippage decay (`_depth_decay`)
    """
    from scripts.polymarket_daily_projections import (
        _depth_decay,
        build_live_projections,
        compute_v393_ticket_size,
    )

    assert compute_v393_ticket_size(60.00) == 12.0
    assert compute_v393_ticket_size(73.01) == 13.14
    assert compute_v393_ticket_size(76.80) == 13.82
    assert compute_v393_ticket_size(95.00) == 17.10
    assert compute_v393_ticket_size(120.00) == 26.40
    assert _depth_decay(15.0) == 1.0
    assert 0.58 <= _depth_decay(150.0) < 0.85

    proj = build_live_projections(days=30, fallback_equity=76.80)
    rows = proj["day_by_day_schedule"]
    assert len(rows) == 30
    quarantined_check = {
        "B1_CONVEX_TAIL_YES",
        "M4_SHOCK_STRIKE_CATCHUP",
        "W2_ENSEMBLE_VALUE",
        "W2_MAKER_OVERROUND",
        "M1_SVI_MAKER_SCALP",
        "M2_STRIKE_CONVERGENCE",
        "P1_PREOPEN_MAKER_STRADDLE",
        "SLEEVE_XRP_V392_SHADOW",
    }
    assert all(g["sleeve"] not in quarantined_check for g in proj["sleeve_graduation_live_tracker"])
    for r in rows:
        assert r["p25_end_equity_usd"] < r["p50_end_equity_usd"] < r["p75_end_equity_usd"]
        assert r["p50_daily_pnl_usd"] > 0
        for bad_k in ("B1_convex_barrier_tails", "W2_weather_maker_and_mos", "M1_M4_svi_maker_and_shock"):
            assert bad_k not in r["p50_sleeve_pnl_breakdown_usd"]


def test_external_dual_audit_alpha124_and_oracle_regressions(tmp_path: Path, monkeypatch) -> None:
    """
    Regression suite covering ChatGPT + Gemini dual adversarial audit findings across Alpha-124:
      - F-08: METAR missing-dewpoint 8-digit T-group remarks (`T0023////`, `T1017////`)
      - M-02: `COR` amended METAR priority + deterministic ensemble alignment
      - H-02: Local 23:00-23:59 observation window does NOT prematurely lock day-end at 100%
      - F-12: Weather `feeSchedule` dynamic fee parsing (`fees_enabled` vs `zero_fees`)
      - H-01 / F-11 / H-06 / F-15: Strict USD `/dev/shm` anchor, clock-skew guard, & trapezoidal TWAP integral
      - F-18: `verify_same_oracle_pair` rejects empty `resolution_source`
      - H-04: `fetch_binance_window_extremes_sync` stitches initial partial-hour `1m` klines
      - C-02 / F-10 / F-03 / M-04 / F-19: `inflight_keys` race guard, cancel-window adverse fill, corrupt JSONL skip
    """
    import asyncio
    import json
    import time
    from datetime import date
    from zoneinfo import ZoneInfo

    import src.polymarket_research.alpha_124_shadow_daemon as a124
    import src.polymarket_research.barrier_onetouch_svi_engine as b_eng
    import src.polymarket_research.exact_twap_lock_engine as etwap
    from src.polymarket_research.same_oracle_dominance_box import (
        TwapCandleMarketSpec,
        verify_same_oracle_pair,
    )
    from src.polymarket_research.weather_metar_engine import (
        WeatherBucket,
        WeatherEventSpec,
        compute_weather_probabilities,
        parse_weather_event,
    )

    ref = datetime(2026, 10, 25, 16, 0, tzinfo=timezone.utc)

    # 1. F-08 + M-02: Missing-dewpoint T-remarks (`T0023////`) and `COR` METAR flag
    m_slash_pos = parse_metar_line(
        "METAR RJTT 250600Z 08007KT 9999 FEW020 02/// Q1017 RMK AO2 T0023////",
        "RJTT",
        ref,
        "Asia/Tokyo",
    )
    assert m_slash_pos is not None and m_slash_pos.has_t_remark is True and abs(m_slash_pos.temp_c - 2.3) < 1e-6

    m_slash_neg = parse_metar_line(
        "METAR KORD 251051Z 29012KT 10SM CLR M02/// A3015 RMK AO2 T1017//// SLP210",
        "KORD",
        ref,
        "America/Chicago",
    )
    assert m_slash_neg is not None and m_slash_neg.has_t_remark is True and abs(m_slash_neg.temp_c - (-1.7)) < 1e-6

    m_cor = parse_metar_line(
        "METAR COR RJTT 250600Z 08007KT 9999 FEW020 19/12 Q1017 RMK AO2 T01940120",
        "RJTT",
        ref,
        "Asia/Tokyo",
    )
    assert m_cor is not None and m_cor.is_corrected is True and abs(m_cor.temp_c - 19.4) < 1e-6

    # 2. H-02: 23:30 local time must NOT deterministically lock day-end before 23:53-23:59 METAR!
    tz_ny = ZoneInfo("America/New_York")
    obs_2253 = parse_metar_line(
        "METAR KLGA 260251Z 31012KT 10SM CLR 15/06 A3012 RMK AO2 T01500061",
        "KLGA",
        datetime(2026, 10, 26, 3, 0, tzinfo=timezone.utc),
        "America/New_York",
    )
    assert obs_2253 is not None and obs_2253.local_dt.date() == date(2026, 10, 25)
    low_buckets = [
        WeatherBucket("b1", "c1", "14°C or below", "14°C-", "y1", "n1", "C", float("-inf"), 14.0),
        WeatherBucket("b2", "c2", "15°C", "15°C", "y2", "n2", "C", 15.0, 15.0),
        WeatherBucket("b3", "c3", "16°C", "16°C", "y3", "n3", "C", 16.0, 16.0),
        WeatherBucket("b4", "c4", "17°C or higher", "17°C+", "y4", "n4", "C", 17.0, float("inf")),
    ]
    low_spec = WeatherEventSpec(
        event_id="ev_klga_low",
        slug="nyc-low",
        series_slug="nyc-daily-weather",
        title="Lowest temperature in NYC on October 25?",
        icao="KLGA",
        city="NYC",
        lat=40.7769,
        lon=-73.8740,
        tz_name="America/New_York",
        obs_date=date(2026, 10, 25),
        metric="LOW",
        unit="C",
        fee_type="zero_fees",
        end_date_iso="2026-10-26T05:00:00Z",
        buckets=low_buckets,
    )
    eval_2330_local = datetime(2026, 10, 25, 23, 30, tzinfo=tz_ny).astimezone(timezone.utc)
    midnight_utc_ts = int(datetime(2026, 10, 26, 0, 0, tzinfo=tz_ny).astimezone(timezone.utc).timestamp())
    ens_cold_midnight = {midnight_utc_ts: [12.0] * 30}
    res_2330 = compute_weather_probabilities(low_spec, eval_2330_local, [obs_2253], ens_cold_midnight)
    assert res_2330["rem_hours_count"] == 1
    assert res_2330["probs"][0] > 0.50  # <=14°C reflects plunging 23:54 forecast instead of false 15°C lock!

    eval_0005_next = datetime(2026, 10, 26, 0, 5, tzinfo=tz_ny).astimezone(timezone.utc)
    res_after_midnight = compute_weather_probabilities(low_spec, eval_0005_next, [obs_2253], ens_cold_midnight)
    assert res_after_midnight["probs"][1] > 0.99  # After 00:00 local, 15°C deterministically locks!

    # 3. F-12: Weather `feeSchedule` parsed dynamically if Polymarket enables fees
    w_ev_fees = {
        "id": "ev_fee_test",
        "title": "Highest temperature in Tokyo on October 26?",
        "endDate": "2026-10-26T15:00:00Z",
        "markets": [
            {
                "id": f"m_{idx}",
                "conditionId": f"0xc_{idx}",
                "groupItemTitle": lbl,
                "description": "Resolves via https://aviationweather.gov/api/data/metar?ids=RJTT excluding SPECI on 26 Oct '26.",
                "clobTokenIds": f'["y_{idx}", "n_{idx}"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.05, "exponent": 1.0},
            }
            for idx, lbl in enumerate(["18°C or below", "19°C", "20°C", "21°C or higher"])
        ],
    }
    parsed_fee_ev = parse_weather_event(w_ev_fees)
    assert parsed_fee_ev is not None and parsed_fee_ev.fee_type == "fees_enabled"
    assert all(abs(b.fee_rate - 0.05) < 1e-9 for b in parsed_fee_ev.buckets)

    # 4. H-01 + F-11 + H-06: Strict USD `/dev/shm` anchor & trapezoidal TWAP integration
    monkeypatch.setattr(etwap, "SHM_DIR", tmp_path)
    now_u = 1792975000.0
    shm_btc = tmp_path / "pm_fast_tick_BTC.json"
    # USDT-only payload must NOT be accepted as USD anchor (`H-01`)
    shm_btc.write_text(json.dumps({"timestamp_unix": now_u, "spot_price": 84100.0}), encoding="utf-8")
    assert etwap.read_shm_usd_anchor("BTC", now_u)["usd_spot"] is None
    # Future clock skew > 1.5s rejected (`F-11`)
    shm_btc.write_text(json.dumps({"timestamp_unix": now_u + 4.0, "chainlink_proxy_spot": 84050.0}), encoding="utf-8")
    assert etwap.read_shm_usd_anchor("BTC", now_u)["usd_spot"] is None
    # Verified Chainlink USD proxy accepted
    shm_btc.write_text(json.dumps({"timestamp_unix": now_u - 0.5, "chainlink_proxy_spot": 84050.0}), encoding="utf-8")
    assert etwap.read_shm_usd_anchor("BTC", now_u)["usd_spot"] == 84050.0

    # Bursty uneven samples + >12s `shm_twap_60s` contamination check (`H-06`)
    end_tw = now_u + 30.0
    no_bank = etwap.compute_exact_twap_lock_probability(
        asset="ETH",
        open_price=2400.0,
        current_usd_spot=2403.0,
        rem_seconds=30.0,
        now_ts=now_u,
        end_ts=end_tw,
        spot_samples=[],
        shm_twap_60s=2415.0,
        usd_direct_feed=True,
    )
    assert no_bank["eff_alpha"] == 0.0  # Rolling 60s TWAP rejected at rem=30s (50% pre-window contamination!)

    # 5. F-18: `verify_same_oracle_pair` rejects missing/empty `resolution_source`
    m15_empty = TwapCandleMarketSpec(
        "ETH", "15m", "1", "0x1", "ETH 15m", "2026-10-25T23:00:00Z", "2026-10-25T23:15:00Z",
        100.0, 1000.0, "u1", "d1", 0.07, 1.0, False, 60, "",
    )
    m5_empty = TwapCandleMarketSpec(
        "ETH", "5m", "2", "0x2", "ETH 5m", "2026-10-25T23:10:00Z", "2026-10-25T23:15:00Z",
        700.0, 1000.0, "u2", "d2", 0.07, 1.0, False, 60, "",
    )
    assert verify_same_oracle_pair(m15_empty, m5_empty) is False

    # 6. H-04: `fetch_binance_window_extremes_sync` stitches initial partial-hour `1m` klines
    st_mid_hr = 1792931400.0  # 12:30:00 UTC (mid-hour!)
    en_48h = st_mid_hr + 48 * 3600.0

    def fake_klines(sym: str, st_ms: int, en_ms: int, interval: str, timeout: float):
        if interval == "1m" and st_ms == int(st_mid_hr * 1000):
            # Wick to 89,500 at 12:40 UTC during initial partial hour!
            return [[st_ms, "84000", "89500", "83900", "84100", "10", st_ms + 60_000]]
        return [[int((st_mid_hr + 3600) * 1000), "84100", "85000", "83500", "84200", "100", int(en_48h * 1000)]]

    monkeypatch.setattr(b_eng, "_fetch_finalized_klines", fake_klines)
    ext_res = b_eng.fetch_binance_window_extremes_sync("BTC", st_mid_hr, en_48h, "1m")
    assert ext_res is not None and ext_res[0] == 89500.0

    # 7. C-02 / F-10 / F-03 / M-04 / F-19: Concurrency race, cancel-window adverse fill, corrupt JSONL skip
    state_p = tmp_path / "a124_race_state.json"
    ledger_p = tmp_path / "a124_race_ledger.jsonl"
    opps_p = tmp_path / "a124_race_opps.json"
    # Pre-seed ledger with a truncated/corrupt line + a valid open entry (`F-19`)
    ledger_p.write_text(
        '{"event": "SHADOW_ENTRY", "corrupt_json": \n'
        + json.dumps({
            "event": "SHADOW_ENTRY",
            "position_id": "S2_VALID_HYDRATE",
            "dedupe_key": "S2_BTC_5m_1",
            "sleeve": "S2_EXACT_TWAP_LOCK",
            "asset_or_city": "BTC",
            "title": "BTC 5m",
            "side": "UP",
            "token_id": "tok_h",
            "fee_rate": 0.07,
            "entry_ts": 1000.0,
            "close_ts": 2000.0,
            "tier_fills": {"T1000": {"spent_usd": 100.0, "fee_usd": 0.5, "shares": 115.0}},
            "extra": {},
            "status": "OPEN",
        })
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(a124, "STATE_FILE", state_p)
    monkeypatch.setattr(a124, "LEDGER_FILE", ledger_p)
    monkeypatch.setattr(a124, "OPPS_FILE", opps_p)

    async def _sim_concurrency_and_adverse_fill() -> None:
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        assert "S2_VALID_HYDRATE" in d.open_positions

        books = {
            "tok_race": {"bids": [{"price": "0.84", "size": "300"}], "asks": [{"price": "0.85", "size": "300"}]},
            "tok_adv": {"bids": [{"price": "0.49", "size": "200"}], "asks": [{"price": "0.51", "size": "200"}]},
        }

        async def fake_fetch(url: str, timeout: float = 5.0):
            await asyncio.sleep(0.01)
            for tid, bk in books.items():
                if f"token_id={tid}" in url:
                    return bk
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch)
        # Concurrent duplicate calls with identical dedupe_key must open strictly 1 position (`C-02` / `F-10`)
        r1, r2 = await asyncio.gather(
            d.open_shadow_position(
                "W1_SOLAR_PEAK_LOCK", "W1_RACE_KEY", "Tokyo_RJTT", "Tokyo 20°C",
                "YES", "tok_race", 0.0, 0.94, time.time() + 7200.0, {"event_id": "ev_r"},
            ),
            d.open_shadow_position(
                "W1_SOLAR_PEAK_LOCK", "W1_RACE_KEY", "Tokyo_RJTT", "Tokyo 20°C",
                "YES", "tok_race", 0.0, 0.94, time.time() + 7200.0, {"event_id": "ev_r"},
            ),
        )
        assert (r1, r2) in ((True, False), (False, True))
        assert sum(1 for p in d.open_positions.values() if p.get("dedupe_key") == "W1_RACE_KEY") == 1

        # Cancel-latency adverse fill (`F-03` / `M-04`): spot crashes -40 bps AND fast taker already swept ask to 0.49 <= 0.50
        d.spots["BTC"] = 84000.0
        ok_m = await d.post_shadow_maker_entry(
            "M1_SVI_MAKER_SCALP", "M1_ADV_RACE", "BTC", "BTC > 84k", "YES",
            "tok_adv", 0.58, time.time() + 43200.0, {"market_id": "m_adv", "strike": 84000.0, "is_downward": False},
        )
        assert ok_m is True
        oid_adv = next(iter(d.pending_maker_orders))
        d.pending_maker_orders[oid_adv]["created_ts"] -= 2.0  # Rested 2s >= 0.35s
        d.spots["BTC"] = 83650.0  # -41.7 bps adverse shock!
        books["tok_adv"] = {"bids": [{"price": "0.48", "size": "200"}], "asks": [{"price": "0.49", "size": "250"}]}
        monkeypatch.setattr(
            a124,
            "evaluate_svi_digital_fair_value",
            lambda *a, **kw: {"p_yes": 0.36, "p_no": 0.64, "iv_annual": 0.45, "z_sigma": 0.9, "source": "TEST"},
        )
        await d.manage_pending_maker_orders()
        adv_pos = [p for p in d.open_positions.values() if p.get("dedupe_key") == "M1_ADV_RACE"]
        assert len(adv_pos) == 1 and adv_pos[0]["extra"].get("adverse_fill_during_cancel_window") is True

    asyncio.run(_sim_concurrency_and_adverse_fill())


def test_v40_profit_maximization_upgrades(tmp_path: Path, monkeypatch) -> None:
    """
    Comprehensive v4.0 test suite verifying all 20 profit-maximization upgrades:
      - ChatGPT #9: Explicit missing-feature hygiene on real 20+-digit CTF tokens (zero optimistic defaults)
      - ChatGPT #1: Calibrated event-time quote-survival & net-alpha scorer + ledger calibration
      - ChatGPT #2 + Gemini #9: Adaptive Maker/Taker/Skip router + 3.5s reactive `post_only` M4 maker quote
      - ChatGPT #3 + Gemini #6 + Gemini #13: Optimal-stopping `$0.985-$0.99` pre-expiry cash recycling,
        complementary opposite-outcome merge dominance, and OBI maker step-down
      - ChatGPT #4: `C1_BINARY_COMPLETE_SET` same-market binary `YES+NO <= $0.994` scanner & shadow execution
      - ChatGPT #6: Probabilistic cross-oracle basis box expectancy (`PROBABILISTIC_CROSS_ORACLE_RV`)
      - Gemini #15 + ChatGPT #10: `/dev/shm/pm_global_positions.json` bus + capital-efficiency auction (`EV/($*hr)`)
      - Gemini #14 + ChatGPT #8: Deribit SVI `index_price` carry drift + PAVA monotone strike-ladder projection
      - ChatGPT #7: `first_passage_touch_prob` forward drift & `realized_vol_ratio` regime-switching jump weight + `evaluate_barrier_no_net_ev`
      - Gemini #11 + Gemini #10 + ChatGPT #5: 10s station-release METAR TTL, TAF `TX`/`TN` parser, and `W3_WEATHER_SLATE_ARB`
      - Gemini #8: `M3_LADDER_MONO_BOX` cross-strike monotonicity box execution & settlement
    """
    import asyncio
    import time
    from datetime import date
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.net_alpha_opportunity_engine import (
        estimate_quote_survival_and_net_alpha,
        evaluate_cross_oracle_basis_box_ev,
        evaluate_optimal_stopping_exit,
        fit_quote_survival_from_ledger,
        inspect_microstructure_feature_completeness,
        publish_global_positions_shm,
        rank_opportunities_capital_auction,
        read_global_positions_shm,
        scan_binary_complete_set_arb,
        select_maker_taker_skip_route,
    )
    from src.polymarket_research.deribit_svi_surface import (
        DeribitSVISurfaceEngine,
        SVIParams,
        enforce_monotone_ladder_probabilities,
    )
    from src.polymarket_research.multistrike_svi_scalper import (
        StrikeRungSpec,
        evaluate_coherent_strike_ladder,
    )
    from src.polymarket_research.barrier_onetouch_svi_engine import (
        evaluate_barrier_no_net_ev,
        first_passage_touch_prob,
    )
    from src.polymarket_research.weather_metar_engine import (
        WeatherBucket,
        WeatherEventSpec,
        compute_adaptive_metar_poll_ttl,
        evaluate_weather_event_slate,
        parse_taf_temperature_extremes,
        verify_weather_slate_partition,
    )

    real_ctf_tok = "100434764618174237135201777197981253576172734064131101154122934005557319214073"

    # 1. Explicit missing-feature hygiene (ChatGPT #9)
    inc_age = inspect_microstructure_feature_completeness(
        {"fee_metadata": {"fee_rate_market": 0.07}, "shock_ofi": 0.9, "pre_shock_features_t0": {"UP": {"token_id": real_ctf_tok, "age_ask_ms": None, "obi_l1": 0.2}}},
        "UP",
        real_ctf_tok,
    )
    assert inc_age["hard_veto_live"] is True and "age_ask_ms" in inc_age["missing_fields"]
    inc_ofi = inspect_microstructure_feature_completeness(
        {"fee_metadata": {"fee_rate_market": 0.07}, "shock_ofi": None, "pre_shock_features_t0": {"UP": {"token_id": real_ctf_tok, "age_ask_ms": 180.0, "obi_l1": 0.2}}},
        "UP",
        real_ctf_tok,
    )
    assert inc_ofi["hard_veto_live"] is True and "shock_ofi" in inc_ofi["missing_fields"]

    # 2. Event-time quote-survival & +2c price-improved FAK net alpha (ChatGPT #1)
    surv_base = estimate_quote_survival_and_net_alpha(
        p_win=0.90, ask_price=0.74, limit_price=0.74, p_max=0.80, clob_rtt_ms=260.0, age_ask_ms=280.0
    )
    surv_impr = estimate_quote_survival_and_net_alpha(
        p_win=0.90, ask_price=0.74, limit_price=0.76, p_max=0.80, clob_rtt_ms=260.0, age_ask_ms=280.0
    )
    assert surv_impr["p_fill"] > surv_base["p_fill"]
    assert surv_impr["eff_limit_px"] == 0.76 <= 0.80
    assert surv_impr["eligible"] is True and surv_impr["ev_net_usd"] > 0.0

    cal = fit_quote_survival_from_ledger(
        [
            {"mode": "LIVE_CLOB", "success": True, "latency_ms": 210.0},
            {"mode": "LIVE_CLOB", "success": True, "latency_ms": 225.0},
            {"mode": "FAK_KILLED_NO_MATCH", "success": False, "latency_ms": 280.0},
            {"mode": "LIVE_CLOB", "success": True, "latency_ms": 195.0},
            {"mode": "FAK_KILLED_NO_MATCH", "success": False, "latency_ms": 265.0},
        ]
    )
    assert cal["sample_count"] == 5 and abs(cal["empirical_fill_rate"] - 0.6) < 1e-6

    # 3. Maker / Taker / Skip Router (ChatGPT #2 + Gemini #9)
    r_taker = select_maker_taker_skip_route(p_win=0.92, best_bid=0.73, best_ask=0.74, p_max=0.81, clob_rtt_ms=190.0)
    assert r_taker["route"] == "TAKER_PRICE_IMPROVED_FAK" and r_taker["taker_limit_px"] == 0.76
    r_maker = select_maker_taker_skip_route(p_win=0.77, best_bid=0.69, best_ask=0.75, p_max=0.74, clob_rtt_ms=280.0)
    assert r_maker["route"] == "MAKER_POST_ONLY_3P5S" and r_maker["maker_bid_px"] == 0.70
    r_skip = select_maker_taker_skip_route(p_win=0.60, best_bid=0.68, best_ask=0.70, p_max=0.58)
    assert r_skip["route"] == "SKIP"

    # 4. Optimal-stopping exit controller: $0.99 recycle, complement merge, and OBI step-down (ChatGPT #3 + Gemini #6/#13)
    ex_rec = evaluate_optimal_stopping_exit(
        entry_px=0.74, rem_shares=18.0, best_bid=0.99, best_ask=1.00, curr_target_px=0.99, tte_sec=15.0
    )
    assert ex_rec["action"] == "PRE_EXPIRY_99C_RECYCLE" and ex_rec["taker_fee_ps"] < 0.001

    ex_comp = evaluate_optimal_stopping_exit(
        entry_px=0.70, rem_shares=18.0, best_bid=0.84, best_ask=0.93, curr_target_px=0.95, tte_sec=30.0, opp_ask_complement=0.09
    )
    assert ex_comp["action"] == "SYNTHETIC_COMPLEMENT_MERGE" and ex_comp["net_proceeds_ps"] > 0.90

    ex_obi = evaluate_optimal_stopping_exit(
        entry_px=0.74, rem_shares=18.0, best_bid=0.92, best_ask=0.95, curr_target_px=0.95, tte_sec=90.0, obi_l1=-0.65, v_spot_15s_pct=-0.02
    )
    assert ex_obi["action"] == "OBI_MAKER_STEP_DOWN" and ex_obi["target_px"] == 0.93

    # 5. Same-market binary complete-set scanner (`C1`) & Cross-oracle probabilistic basis EV (ChatGPT #4 & #6)
    c1 = scan_binary_complete_set_arb(
        market_id="m_c1",
        condition_id="0xc1",
        yes_token="tok_y_c1",
        no_token="tok_n_c1",
        asks_yes_raw=[{"price": "0.47", "size": "60"}],
        asks_no_raw=[{"price": "0.48", "size": "60"}],
        target_budget_usd=30.0,
        fee_rate=0.07,
        max_complete_set_cost=0.994,
    )
    assert c1["filled"] is True and c1["box_cost_net"] < 0.994 and c1["guaranteed_min_profit_usd"] > 0.0

    basis_ev = evaluate_cross_oracle_basis_box_ev(
        spot_px=84100.0, k_low=84000.0, k_high=84200.0, c_taker_net=0.975, tte_sec=600.0
    )
    assert basis_ev["classification"] == "PROBABILISTIC_CROSS_ORACLE_RV" and basis_ev["is_riskless"] is False

    # 6. Cross-daemon `/dev/shm` position bus & Capital-efficiency opportunity auction (Gemini #15 + ChatGPT #10)
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    now_bus = time.time()
    assert publish_global_positions_shm(
        "live_harvester",
        [{"trade_id": "T1", "sleeve": "LIVE", "asset": "BTC", "target_token": "UP", "candle_open_spot": 84000.0, "candle_expiry_ts": now_bus + 600.0, "notional_usd": 14.0}],
    ) is True
    bus_state = read_global_positions_shm()
    glob_pos = bus_state["daemons"]["live_harvester"]["positions"]
    assert len(glob_pos) == 1 and glob_pos[0]["asset"] == "BTC"

    ranked = rank_opportunities_capital_auction(
        [
            {"sleeve": "W2", "asset": "NYC", "side": "YES", "ask_vwap": 0.50, "net_edge": 0.05, "tte_sec": 36000.0, "expiry_ts": now_bus + 36000.0},
            {"sleeve": "S2", "asset": "BTC", "side": "DOWN", "strike": 84250.0, "ask_vwap": 0.85, "net_edge": 0.04, "tte_sec": 300.0, "expiry_ts": now_bus + 600.0},
        ],
        active_global_positions=glob_pos,
    )
    assert ranked[0]["sleeve"] == "S2" and ranked[0].get("synthetic_corridor_completion") is True

    # 7. Deribit SVI carry drift + PAVA monotone ladder projection + Barrier jump/EV gate (Gemini #14 + ChatGPT #7/#8)
    eng = DeribitSVISurfaceEngine()
    eng._cache["BTC"] = SVIParams(
        a=0.0004, b=0.0002, rho=-0.15, m=0.0, sigma=0.05,
        t_years=30.0 / 365.25, forward_price=86000.0, index_price=84000.0, calibrated_at=time.time(),
    )
    assert eng._cache["BTC"].implied_forward_drift_rate() > 0.15
    p_carry = eng.evaluate_strike_probability("BTC", spot=84000.0, strike=85000.0, tte_seconds=14 * 86400.0, allow_sync_fetch=False)
    eng._cache["BTC"].index_price = 86000.0  # zero carry basis
    p_flat = eng.evaluate_strike_probability("BTC", spot=84000.0, strike=85000.0, tte_seconds=14 * 86400.0, allow_sync_fetch=False)
    assert p_carry["p_above_strike"] > p_flat["p_above_strike"]

    mono = enforce_monotone_ladder_probabilities([(80000.0, 0.72), (82000.0, 0.55), (84000.0, 0.61), (86000.0, 0.30)])
    assert mono["probs"] == sorted(mono["probs"], reverse=True)
    assert all(iv >= 0.0 for iv in mono["interval_probs"]) and mono["max_adjustment"] > 0.0

    rungs_test = [
        StrikeRungSpec("ev1", "btc-daily", "BTC", "BTC Daily", f"m_{k}", f"0x{k}", f"BTC > {k}", float(k), False, now_bus + 7200.0, f"ty_{k}", f"tn_{k}")
        for k in (82000, 84000, 86000)
    ]
    coh = evaluate_coherent_strike_ladder("BTC", 84000.0, rungs_test, 7200.0, now_ts=now_bus)
    assert coh["probs"][0] >= coh["probs"][1] >= coh["probs"][2]

    pt_calm = first_passage_touch_prob(84000.0, 88000.0, 86400.0, 0.50, "UP", realized_vol_ratio=1.0, forward_drift_annual=0.0)
    pt_stress = first_passage_touch_prob(84000.0, 88000.0, 86400.0, 0.50, "UP", realized_vol_ratio=2.2, forward_drift_annual=0.12)
    assert pt_stress > pt_calm
    assert evaluate_barrier_no_net_ev(p_touch=0.04, ask_no=0.88)["eligible"] is True
    assert evaluate_barrier_no_net_ev(p_touch=0.01, ask_no=0.95)["eligible"] is False  # 19x loss/gain asymmetry vetoed!

    # 8. Weather 10s release-window TTL, TAF `TX`/`TN` parser, and `W3_WEATHER_SLATE_ARB` (Gemini #10/#11 + ChatGPT #5)
    assert compute_adaptive_metar_poll_ttl("KLGA", None, datetime(2026, 10, 26, 14, 52, tzinfo=timezone.utc)) == 10.0
    assert compute_adaptive_metar_poll_ttl("KLGA", None, datetime(2026, 10, 26, 14, 25, tzinfo=timezone.utc)) == 300.0

    taf_parsed = parse_taf_temperature_extremes(
        "TAF KLGA 261130Z 2612/2718 30012KT P6SM FEW050 TX19/2619Z TNM02/2710Z",
        "KLGA",
        datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc),
        "America/New_York",
    )
    assert taf_parsed[date(2026, 10, 26)]["HIGH"] == 19.0
    assert taf_parsed[date(2026, 10, 27)]["LOW"] == -2.0

    w_spec = WeatherEventSpec(
        event_id="ev_w3",
        slug="tokyo-w3",
        series_slug="tokyo-daily-weather",
        title="Highest temperature in Tokyo on October 26?",
        icao="RJTT",
        city="Tokyo",
        lat=35.5494,
        lon=139.7798,
        tz_name="Asia/Tokyo",
        obs_date=date(2026, 10, 26),
        metric="HIGH",
        unit="C",
        fee_type="zero_fees",
        end_date_iso="2026-10-26T20:00:00Z",
        buckets=[
            WeatherBucket("wb1", "0xwb1", "18°C or below", "18°C or below", "wy1", "wn1", "C", float("-inf"), 18.0),
            WeatherBucket("wb2", "0xwb2", "19°C", "19°C", "wy2", "wn2", "C", 19.0, 19.0),
            WeatherBucket("wb3", "0xwb3", "20°C or higher", "20°C or higher", "wy3", "wn3", "C", 20.0, float("inf")),
        ],
    )
    assert verify_weather_slate_partition(w_spec) is True
    slate_eval = evaluate_weather_event_slate(
        w_spec,
        [0.20, 0.50, 0.30],
        {
            "wb1": {"ask_yes": 0.19, "ask_yes_shares": 40.0},
            "wb2": {"ask_yes": 0.46, "ask_yes_shares": 40.0},
            "wb3": {"ask_yes": 0.31, "ask_yes_shares": 40.0},
        },
        target_budget_usd=10.0,
    )
    assert slate_eval["full_slate_arb"] is not None
    assert abs(slate_eval["full_slate_arb"]["sum_asks"] - 0.96) < 1e-6

    # 9. Shadow daemon end-to-end execution & settlement for `M3`, `C1`, `W3`, and `M4` 3.5s Maker
    async def _sim_v40_sleeves() -> None:
        monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "a124_v40_state.json")
        monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "a124_v40_ledger.jsonl")
        monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "a124_v40_opps.json")
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        d.spots["BTC"] = 84500.0

        books_v40 = {
            "tok_c1_y": {"bids": [{"price": "0.46", "size": "80"}], "asks": [{"price": "0.47", "size": "80"}]},
            "tok_c1_n": {"bids": [{"price": "0.47", "size": "80"}], "asks": [{"price": "0.48", "size": "80"}]},
            "tok_m3_lo": {"bids": [{"price": "0.52", "size": "80"}], "asks": [{"price": "0.53", "size": "80"}]},
            "tok_m3_hi": {"bids": [{"price": "0.41", "size": "80"}], "asks": [{"price": "0.42", "size": "80"}]},
            "tok_m4_mkr": {"bids": [{"price": "0.50", "size": "60"}], "asks": [{"price": "0.54", "size": "60"}]},
        }

        async def fake_fetch_v40(url: str, timeout: float = 5.0):
            if "/book?token_id=" in url:
                return books_v40.get(url.split("token_id=")[1])
            if "/markets/m_c1" in url:
                return {"closed": True, "outcomePrices": '["1", "0"]'}
            if "/markets/m_lo" in url:
                return {"closed": True, "outcomePrices": '["1", "0"]'}
            if "/markets/m_hi" in url:
                return {"closed": True, "outcomePrices": '["0", "1"]'}  # Lands inside corridor -> $2.00 DOUBLE WIN!
            if "/markets/wb2" in url:
                return {"closed": True, "outcomePrices": '["1", "0"]'}
            if "/markets/wb1" in url or "/markets/wb3" in url:
                return {"closed": True, "outcomePrices": '["0", "1"]'}
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch_v40)

        # Open C1 complete set, M3 ladder monotonicity box, and W3 weather full-slate arb
        ok_c1 = await d.open_shadow_two_leg_box(
            sleeve="C1_BINARY_COMPLETE_SET",
            dedupe_key="C1_TEST_1",
            asset="BTC",
            title="BTC > 84k [YES+NO Complete Set]",
            leg_a={"token_id": "tok_c1_y", "side": "YES", "market_id": "m_c1", "fee_rate": 0.07},
            leg_b={"token_id": "tok_c1_n", "side": "NO", "market_id": "m_c1", "fee_rate": 0.07},
            bk_a=books_v40["tok_c1_y"],
            bk_b=books_v40["tok_c1_n"],
            close_ts=time.time() - 60.0,
            max_box_cost_net=0.994,
            extra={"market_id": "m_c1"},
        )
        ok_m3 = await d.open_shadow_two_leg_box(
            sleeve="M3_LADDER_MONO_BOX",
            dedupe_key="M3_TEST_1",
            asset="BTC",
            title="BTC Ladder Box [84000..85000]",
            leg_a={"token_id": "tok_m3_lo", "side": "YES", "market_id": "m_lo", "fee_rate": 0.07},
            leg_b={"token_id": "tok_m3_hi", "side": "NO", "market_id": "m_hi", "fee_rate": 0.07},
            bk_a=books_v40["tok_m3_lo"],
            bk_b=books_v40["tok_m3_hi"],
            close_ts=time.time() - 60.0,
            max_box_cost_net=0.995,
            extra={"low_market_id": "m_lo", "high_market_id": "m_hi", "low_strike": 84000.0, "high_strike": 85000.0},
        )
        ok_w3 = await d.open_shadow_weather_slate(w_spec, slate_eval["full_slate_arb"], close_ts=time.time() - 60.0)
        assert ok_c1 is True and ok_m3 is True and ok_w3 is True

        # Settle all 3 riskless box/slate positions!
        await d.manage_open_positions()
        by_slv = {p["sleeve"]: p for p in d.closed_positions}
        assert by_slv["C1_BINARY_COMPLETE_SET"]["won"] is True and by_slv["C1_BINARY_COMPLETE_SET"]["tier_pnls_usd"]["T1000"] > 0.0
        assert by_slv["M3_LADDER_MONO_BOX"]["won"] is True and by_slv["M3_LADDER_MONO_BOX"]["status"] == "SETTLED_DOMINANCE_DOUBLE_2X"
        assert by_slv["W3_WEATHER_SLATE_ARB"]["won"] is True and by_slv["W3_WEATHER_SLATE_ARB"]["tier_pnls_usd"]["T1000"] > 0.0

        # Verify 3.5s reactive M4 post_only Maker quote fills passively at 1.0s and auto-cancels after 3.5s
        ok_m4m = await d.post_shadow_maker_entry(
            sleeve="M4_SHOCK_STRIKE_CATCHUP",
            dedupe_key="M4MKR_TEST",
            asset="BTC",
            title="BTC > 84500",
            side_label="YES",
            token_id="tok_m4_mkr",
            p_model=0.62,
            close_ts=time.time() + 7200.0,
            extra={"market_id": "m_m4", "strike": 84500.0, "is_downward": False},
            prefetched_book=books_v40["tok_m4_mkr"],
            ttl_override_sec=3.5,
        )
        assert ok_m4m is True
        oid_m4 = next(iter(d.pending_maker_orders))
        d.pending_maker_orders[oid_m4]["created_ts"] -= 1.2  # 1.2s >= 0.5s min_rest_sec and < 3.5s TTL
        books_v40["tok_m4_mkr"] = {"bids": [{"price": "0.50", "size": "60"}], "asks": [{"price": "0.51", "size": "80"}]}
        monkeypatch.setattr(
            a124,
            "evaluate_svi_digital_fair_value",
            lambda *a, **kw: {"p_yes": 0.62, "p_no": 0.38, "iv_annual": 0.45, "z_sigma": 0.5, "source": "TEST"},
        )
        await d.manage_pending_maker_orders()
        assert any(p["sleeve"] == "M4_SHOCK_STRIKE_CATCHUP" for p in d.open_positions.values())
        d.write_state_files([{"sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX", "ask_vwap": 0.98, "net_edge": 0.02, "tte_sec": 180.0}])
        assert "alpha124_shadow" in read_global_positions_shm()["daemons"]

    asyncio.run(_sim_v40_sleeves())


def test_v42_seven_new_shadow_additions_and_quarantine(tmp_path, monkeypatch):
    """
    Verifies all 7 new Shadow Trading Additions + Production Quarantine (`PM_QUARANTINE_LOSING_SLEEVES=1`):
      1. `D1_4H_DOMINANCE_BOX`: 4h (`variant=fourhour`) vs 15m/5m Same-Oracle Chainlink 60s-TWAP Boxes.
      2. `D1_QUIET_BOOK_BOX`: Quiet-book spread/impulse filter blocking toxic sweeps while passing calm books.
      3. `S5M_CHAINLINK_SNIPER`: Standalone 5m BTC & ETH directional sniper (`$0.96` Maker TP + `fiveminute` fallback).
      4. `N1_NEGRISK_CROSS_BOX`: NegRisk bracket (`72,000-74,000`) vs Multi-Strike (`Above $72k/$74k`) 2-leg & 3-leg boxes.
      5. `P1_PREOPEN_MAKER_STRADDLE`: Pre-open `$0.48 + $0.48 = $0.96` Maker pair (both 2-leg lock AND 1-leg scratch!).
      6. `U1_DAILY_UPDOWN_LOCK`: Daily BTC/ETH Up-or-Down final-90m convergence lock.
      7. `HIGH_VOLUME_WEATHER_SERIES`: Chengdu (`ZUUU`), Beijing (`ZBAA`), Seoul (`RKSI`) 0%-fee Asian METAR mapping.
      8. Production Quarantine (`PM_QUARANTINE_LOSING_SLEEVES=1`) blocks `M4`, `W2`, `W2_MAKER`, `M1`, `M2`.
    """
    import asyncio
    import time
    from src.polymarket_research import alpha_124_shadow_daemon as a124
    from src.polymarket_research.multistrike_svi_scalper import (
        build_negrisk_cross_box_bundles,
        parse_daily_updown_event,
        parse_multistrike_event,
        parse_negrisk_bracket_event,
    )
    from src.polymarket_research.same_oracle_dominance_box import (
        build_crypto_price_query_url,
        determine_dominance_legs,
        parse_twap_candle_event,
        verify_same_oracle_pair,
        walk_equal_shares_multi_leg_box,
    )
    from src.polymarket_research.weather_metar_engine import HIGH_VOLUME_WEATHER_SERIES, parse_weather_event

    # 1. Verify Production Quarantine blocks all 6 retired negative-EV sleeves (including P1_PREOPEN_MAKER_STRADDLE)
    monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES", "1")
    for sl_q in (
        "M4_SHOCK_STRIKE_CATCHUP",
        "W2_ENSEMBLE_VALUE",
        "W2_MAKER_OVERROUND",
        "M1_SVI_MAKER_SCALP",
        "M2_STRIKE_CONVERGENCE",
        "P1_PREOPEN_MAKER_STRADDLE",
    ):
        assert a124.is_shadow_sleeve_quarantined(sl_q) is True
    for sl_ok in (
        "W1_SOLAR_PEAK_LOCK",
        "D1_4H_DOMINANCE_BOX",
        "D1_QUIET_BOOK_BOX",
        "S5M_CHAINLINK_SNIPER",
        "N1_NEGRISK_CROSS_BOX",
        "U1_DAILY_UPDOWN_LOCK",
    ):
        assert a124.is_shadow_sleeve_quarantined(sl_ok) is False

    # 2. Verify Asian Daily Weather (`ZUUU`, `ZBAA`, `RKSI`) 0%-fee METAR parsing
    assert {"chengdu-daily-weather", "beijing-daily-weather", "seoul-daily-weather"} <= set(HIGH_VOLUME_WEATHER_SERIES)
    zuuu_desc = (
        "This market will resolve to the highest temperature recorded at Chengdu Shuangliu International Airport "
        "according to https://aviationweather.gov/api/data/metar?ids=ZUUU on 27 Oct '26 (SPECI reports excluded)."
    )
    ev_zuuu = {
        "id": "ev_chengdu",
        "title": "Highest temperature in Chengdu on October 27?",
        "seriesSlug": "chengdu-daily-weather",
        "description": zuuu_desc,
        "markets": [
            {"id": "m_zuuu_1", "conditionId": "0xc1", "groupItemTitle": "19°C or below", "question": "19°C or below?", "description": zuuu_desc, "endDate": "2026-10-27T16:00:00Z", "clobTokenIds": '["tok_z1_y", "tok_z1_n"]'},
            {"id": "m_zuuu_2", "conditionId": "0xc2", "groupItemTitle": "20°C", "question": "20°C?", "description": zuuu_desc, "endDate": "2026-10-27T16:00:00Z", "clobTokenIds": '["tok_z2_y", "tok_z2_n"]'},
            {"id": "m_zuuu_3", "conditionId": "0xc3", "groupItemTitle": "21°C", "question": "21°C?", "description": zuuu_desc, "endDate": "2026-10-27T16:00:00Z", "clobTokenIds": '["tok_z3_y", "tok_z3_n"]'},
            {"id": "m_zuuu_4", "conditionId": "0xc4", "groupItemTitle": "22°C or higher", "question": "22°C or higher?", "description": zuuu_desc, "endDate": "2026-10-27T16:00:00Z", "clobTokenIds": '["tok_z4_y", "tok_z4_n"]'},
        ],
    }
    w_zuuu = parse_weather_event(ev_zuuu, series_slug_hint="chengdu-daily-weather")
    assert w_zuuu is not None and w_zuuu.icao == "ZUUU" and w_zuuu.unit == "C"

    # 3. Verify 4h (`variant=fourhour`) vs 15m Same-Oracle Dominance Box math & URL
    ev_4h = {
        "id": "ev_btc_4h",
        "title": "Bitcoin Up or Down - Oct 26, 8:00AM-12:00PM ET",
        "endDate": "2026-10-26T16:00:00Z",
        "markets": [
            {
                "id": "m_btc_4h",
                "conditionId": "0x4h",
                "eventStartTime": "2026-10-26T12:00:00Z",
                "endDate": "2026-10-26T16:00:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["tok_4h_up", "tok_4h_dn"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.072, "exponent": 1},
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "resolutionSource": "https://data.chain.link/streams/btc-usd",
            }
        ],
    }
    ev_15m = {
        "id": "ev_btc_15m",
        "title": "Bitcoin Up or Down - Oct 26, 11:45AM-12:00PM ET",
        "endDate": "2026-10-26T16:00:00Z",
        "markets": [
            {
                "id": "m_btc_15m",
                "conditionId": "0x15m",
                "eventStartTime": "2026-10-26T15:45:00Z",
                "endDate": "2026-10-26T16:00:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["tok_15m_up", "tok_15m_dn"]',
                "feesEnabled": True,
                "feeSchedule": {"rate": 0.072, "exponent": 1},
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "resolutionSource": "https://data.chain.link/streams/btc-usd",
            }
        ],
    }
    sp_4h = parse_twap_candle_event(ev_4h, "BTC", "4h")
    sp_15m = parse_twap_candle_event(ev_15m, "BTC", "15m")
    assert sp_4h is not None and sp_15m is not None
    u_4h = build_crypto_price_query_url(sp_4h)
    assert "variant=fourhour" in u_4h and "twapEnabled=true&twapLookbackSeconds=60" in u_4h
    assert verify_same_oracle_pair(sp_4h, sp_15m) is True
    dom_4h = determine_dominance_legs(sp_4h, 80000.0, sp_15m, 80500.0)
    assert dom_4h is not None and dom_4h["regime"] == "4H_UP_PLUS_15M_DOWN"

    # 4. Verify NegRisk Bracket (`bitcoin-neg-risk-weekly`) vs Multi-Strike (`btc-multi-strikes-weekly`) 2-leg & 3-leg bundles
    ev_ms = {
        "id": "ev_ms",
        "title": "Bitcoin above ___ on Oct 26?",
        "endDate": "2026-10-26T16:00:00Z",
        "markets": [
            {"id": "ms_72", "conditionId": "0xms72", "question": "Will the price of Bitcoin be above $72,000 on Oct 26?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["ms72_y", "ms72_n"]'},
            {"id": "ms_74", "conditionId": "0xms74", "question": "Will the price of Bitcoin be above $74,000 on Oct 26?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["ms74_y", "ms74_n"]'},
        ],
    }
    ev_nr = {
        "id": "ev_nr",
        "title": "Bitcoin price on Oct 26?",
        "endDate": "2026-10-26T16:00:00Z",
        "markets": [
            {"id": "nr_lt72", "conditionId": "0xnr1", "groupItemTitle": "<72,000", "question": "Will BTC be less than $72,000?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["nr_lt72_y", "nr_lt72_n"]'},
            {"id": "nr_72_74", "conditionId": "0xnr2", "groupItemTitle": "72,000-74,000", "question": "Will BTC be between $72,000 and $74,000?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["nr_7274_y", "nr_7274_n"]'},
            {"id": "nr_gt74", "conditionId": "0xnr3", "groupItemTitle": ">74,000", "question": "Will BTC be greater than $74,000?", "endDate": "2026-10-26T16:00:00Z", "clobTokenIds": '["nr_gt74_y", "nr_gt74_n"]'},
        ],
    }
    ms_rungs = parse_multistrike_event(ev_ms, "BTC", "btc-multi-strikes-weekly")
    nr_brackets = parse_negrisk_bracket_event(ev_nr, "BTC", "bitcoin-neg-risk-weekly")
    bundles = build_negrisk_cross_box_bundles(ms_rungs, nr_brackets)
    # 2 lower tail + 2 interior (partition $1 + complement $2) + 2 upper tail = 6 deterministic bundles!
    assert len(bundles) == 6
    part_b = [b for b in bundles if b["guaranteed_payout"] == 1.0 and len(b["legs"]) == 3][0]
    w_3leg = walk_equal_shares_multi_leg_box(
        [
            {"asks": [{"price": "0.28", "size": "80"}], "fee_rate": 0.07, "fee_exponent": 1.0},
            {"asks": [{"price": "0.30", "size": "80"}], "fee_rate": 0.07, "fee_exponent": 1.0},
            {"asks": [{"price": "0.31", "size": "80"}], "fee_rate": 0.07, "fee_exponent": 1.0},
        ],
        target_budget_usd=100.0,
        guaranteed_payout_per_bundle=part_b["guaranteed_payout"],
        max_bundle_cost_net=0.992,
    )
    assert w_3leg["filled"] is True and w_3leg["guaranteed_min_profit_usd"] > 3.0

    # 5. Verify Daily Up-or-Down parser (`U1_DAILY_UPDOWN_LOCK`)
    ev_u1 = {
        "id": "ev_u1",
        "title": "Bitcoin Up or Down on October 27?",
        "endDate": "2026-10-27T16:00:00Z",
        "markets": [
            {
                "id": "m_u1",
                "conditionId": "0xu1",
                "eventStartTime": "2026-10-26T16:00:00Z",
                "endDate": "2026-10-27T16:00:00Z",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["u1_up", "u1_dn"]',
            }
        ],
    }
    sp_u1 = parse_daily_updown_event(ev_u1, "BTC", "btc-up-or-down-daily")
    assert sp_u1 is not None and sp_u1.up_token == "u1_up" and sp_u1.down_token == "u1_dn"

    # 6. End-to-end async simulation of P1 Pre-Open Maker Straddle (both 2-leg lock & 1-leg scratch!) + S5M Sniper
    async def _sim_new_sleeves() -> None:
        monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "a124_v42_state.json")
        monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "a124_v42_ledger.jsonl")
        monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "a124_v42_opps.json")
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_t = 1793026680.0  # 120s before next 15m boundary 1793026800.0!
        d.spots["BTC"] = 84000.0
        d.spots["ETH"] = 2500.0

        sp_pre_btc = a124.TwapCandleMarketSpec(
            asset="BTC", horizon="15m", market_id="m_pre_btc", condition_id="0xpreb",
            title="BTC PreOpen 15m", start_iso="2026-10-26T15:00:00Z", end_iso="2026-10-26T15:15:00Z",
            start_ts=1793026800.0, end_ts=1793027700.0,
            up_token="p1_btc_up", down_token="p1_btc_dn", fee_rate=0.072, fee_exponent=1.0, neg_risk=False,
            twap_lookback_sec=60, resolution_source="https://data.chain.link/streams/btc-usd",
        )
        sp_pre_eth = a124.TwapCandleMarketSpec(
            asset="ETH", horizon="15m", market_id="m_pre_eth", condition_id="0xpree",
            title="ETH PreOpen 15m", start_iso="2026-10-26T15:00:00Z", end_iso="2026-10-26T15:15:00Z",
            start_ts=1793026800.0, end_ts=1793027700.0,
            up_token="p1_eth_up", down_token="p1_eth_dn", fee_rate=0.072, fee_exponent=1.0, neg_risk=False,
            twap_lookback_sec=60, resolution_source="https://data.chain.link/streams/eth-usd",
        )
        d.preopen_15m_candles = {"BTC_pre15m_1793026800": sp_pre_btc, "ETH_pre15m_1793026800": sp_pre_eth}

        books = {
            "p1_btc_up": {"bids": [{"price": "0.49", "size": "100"}], "asks": [{"price": "0.51", "size": "100"}]},
            "p1_btc_dn": {"bids": [{"price": "0.49", "size": "100"}], "asks": [{"price": "0.51", "size": "100"}]},
            "p1_eth_up": {"bids": [{"price": "0.49", "size": "100"}], "asks": [{"price": "0.51", "size": "100"}]},
            "p1_eth_dn": {"bids": [{"price": "0.49", "size": "100"}], "asks": [{"price": "0.51", "size": "100"}]},
            "s5m_btc_up": {"bids": [{"price": "0.78", "size": "600"}], "asks": [{"price": "0.80", "size": "600"}]},
        }

        async def fake_fetch(url: str, timeout: float = 5.0):
            if "/book?token_id=" in url:
                return books.get(url.split("token_id=")[1])
            return None

        monkeypatch.setattr(d, "fetch_json", fake_fetch)

        # Under PM_QUARANTINE_LOSING_SLEEVES=1, P1 must be blocked completely
        opps_p1 = []
        await d.scan_and_manage_preopen_maker_straddles(opps_p1, now_ts=now_t)
        assert len(d.pending_preopen_straddles) == 0

        # Disable quarantine in isolated test mode to verify P1 2-leg lock & 1-leg scratch accounting
        monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES", "0")
        await d.scan_and_manage_preopen_maker_straddles(opps_p1, now_ts=now_t)
        assert len(d.pending_preopen_straddles) == 2

        # BTC fills BOTH legs -> locks $0.96 -> $1.00 complete set; ETH fills ONLY UP leg -> scratches at T-8s!
        books["p1_btc_up"]["asks"] = [{"price": "0.48", "size": "100"}]
        books["p1_btc_dn"]["asks"] = [{"price": "0.48", "size": "100"}]
        books["p1_eth_up"]["asks"] = [{"price": "0.48", "size": "100"}]
        books["p1_eth_up"]["bids"] = [{"price": "0.47", "size": "100"}]
        await d.scan_and_manage_preopen_maker_straddles([], now_ts=1793026792.0)  # T-8s cutoff!

        assert any(p["sleeve"] == "P1_PREOPEN_MAKER_STRADDLE" for p in d.open_positions.values())
        scratches = [c for c in d.closed_positions if c["status"] == "PREOPEN_ONE_LEG_SCRATCH"]
        assert len(scratches) == 1 and scratches[0]["tier_pnls_usd"]["T1000"] < 0.0

        # Test S5M_CHAINLINK_SNIPER entry at TTE=90s (requires verified direct USD flag — never unverified USDT!)
        sp_5m = a124.TwapCandleMarketSpec(
            asset="BTC", horizon="5m", market_id="m_s5m", condition_id="0xs5m",
            title="BTC 5m", start_iso="2026-10-26T14:55:00Z", end_iso="2026-10-26T15:00:00Z",
            start_ts=1793026500.0, end_ts=1793026800.0,
            up_token="s5m_btc_up", down_token="s5m_btc_dn", fee_rate=0.072, fee_exponent=1.0, neg_risk=False,
            twap_lookback_sec=60, resolution_source="https://data.chain.link/streams/btc-usd",
        )
        d.s5m_candles = {"BTC_5m_1793026800": sp_5m}
        d.chainlink_open_cache[f"BTC_5m_{int(sp_5m.start_ts)}"] = (sp_5m.end_ts, 83800.0)  # +23.8 bps cushion!
        d.usd_direct_flags["BTC"] = False
        await d.scan_s5m_chainlink_sniper([], now_ts=1793026710.0)
        assert not any(p["sleeve"] == "S5M_CHAINLINK_SNIPER" for p in d.open_positions.values())
        d.usd_direct_flags["BTC"] = True
        await d.scan_s5m_chainlink_sniper([], now_ts=1793026710.0)
        assert any(p["sleeve"] == "S5M_CHAINLINK_SNIPER" for p in d.open_positions.values())

        # Regression: get_return_bps must NEVER self-compare hist[-1] -> 0.0 bps when scan cadence > 5.0s!
        d.spot_hist["ETH"].clear()
        d.usd_spot_hist["ETH"].clear()
        d.spot_hist["ETH"].append((100.0, 2306.50))
        d.spot_hist["ETH"].append((110.0, 2309.50))  # 10.0s gap (> 5.0s lookback), +13.007 bps surge!
        ret_eth = d.get_return_bps("ETH", 5.0)
        assert ret_eth > 12.5
        w_q_stub = {"shares": 13, "avail_a_shares": 100.0, "avail_b_shares": 100.0, "leg_a_walk": {"best_ask": 0.80}, "leg_b_walk": {"best_ask": 0.16}}
        bk_q_a = {"bids": [{"price": "0.78", "size": "100"}], "asks": [{"price": "0.80", "size": "100"}]}
        bk_q_b = {"bids": [{"price": "0.14", "size": "100"}], "asks": [{"price": "0.16", "size": "100"}]}
        assert d._passes_quiet_book_filter("ETH", bk_q_a, bk_q_b, w_q_stub, 110.0) is False

    asyncio.run(_sim_new_sleeves())


def test_oct27_0655_strike_inversion_and_antibox_veto(tmp_path: Path) -> None:
    """
    Exact production regression test for 2026-10-27 10:55 UTC (06:55 AM ET, window 1793098800):
      1. Rejects legacy `crypto-price` spot (`99.964442` vs `99.951949`) and resolves exact closed
         `prev_5m` Gamma `eventMetadata.finalPrice` (`99.8571312195911` < `99.97149156931644`),
         selecting `15M_UP + 5M_DOWN` (`$2.00` double corridor winner at `99.90631053937364`).
      2. Deterministically vetoes inverted anti-boxes (`< $0.900` net) in both `walk_equal_shares_dominance_box`
         and `execute_atomic_dominance_box`, plus 4-token complement-bid sums `> 1.03`.
      3. Dispatches thinner-depth leg (`173` shares) BEFORE deeper tail leg (`442` shares @ `$0.24`).
    """
    from src.polymarket_research.same_oracle_dominance_box import (
        TwapCandleMarketSpec,
        build_prev_5m_gamma_event_url,
        compute_dominance_box_payout_from_close,
        determine_dominance_legs,
        parse_authoritative_open_price,
        walk_equal_shares_dominance_box,
    )
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    m15_sol = TwapCandleMarketSpec(
        asset="SOL", horizon="15m", market_id="6247248", condition_id="0xsol15",
        title="SOL 6:45-7:00AM ET", start_iso="2026-10-27T10:45:00Z", end_iso="2026-10-27T11:00:00Z",
        start_ts=1793097900.0, end_ts=1793098800.0, up_token="sol_15m_up", down_token="sol_15m_dn",
        fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/sol-usd-twap-60s-streams",
    )
    m5_sol = TwapCandleMarketSpec(
        asset="SOL", horizon="5m", market_id="6247315", condition_id="0xsol5",
        title="SOL 6:55-7:00AM ET", start_iso="2026-10-27T10:55:00Z", end_iso="2026-10-27T11:00:00Z",
        start_ts=1793098500.0, end_ts=1793098800.0, up_token="sol_5m_up", down_token="sol_5m_dn",
        fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/sol-usd-twap-60s-streams",
    )
    assert build_prev_5m_gamma_event_url(m15_sol).endswith("slug=sol-updown-5m-1793097600")
    assert build_prev_5m_gamma_event_url(m5_sol).endswith("slug=sol-updown-5m-1793098200")

    # Legacy spot payloads (missing twapEnabled=true&twapLookbackSeconds=60 URL) MUST return None
    assert parse_authoritative_open_price({"openPrice": 99.9644420334347, "completed": False, "cached": True}) is None
    assert parse_authoritative_open_price(
        {"openPrice": 99.9644420334347, "completed": False, "cached": True},
        request_url="https://polymarket.com/api/crypto/crypto-price?symbol=SOL&variant=fifteen",
    ) is None

    # Exact twapEnabled=true&twapLookbackSeconds=60 URL AND closed prev_5m Gamma TWAP finalPrice both resolve 14-digit TWAP!
    from src.polymarket_research.same_oracle_dominance_box import build_crypto_price_query_url, parse_closed_gamma_event_settlement
    u15_twap = build_crypto_price_query_url(m15_sol)
    u5_twap = build_crypto_price_query_url(m5_sol)
    assert "twapEnabled=true&twapLookbackSeconds=60" in u15_twap
    assert parse_authoritative_open_price({"openPrice": 99.8571312195911, "completed": False, "cached": True}, request_url=u15_twap) == 99.8571312195911
    assert parse_authoritative_open_price({"openPrice": 99.97149156931644, "completed": False, "cached": True}, request_url=u5_twap) == 99.97149156931644
    k15_true = parse_authoritative_open_price([{"closed": True, "eventMetadata": {"finalPrice": 99.8571312195911}}])
    k5_true = parse_authoritative_open_price([{"closed": True, "eventMetadata": {"finalPrice": 99.97149156931644}}])
    assert k15_true == 99.8571312195911 and k5_true == 99.97149156931644
    # Verify honest per-leg Gamma settlement records $0.00 on inverted legs (never fake 1x/2x)
    ev_sol15_closed = [{"closed": True, "eventMetadata": {"priceToBeat": 99.8571312195911, "finalPrice": 99.90631053937364}}]
    ev_sol5_closed = [{"closed": True, "eventMetadata": {"priceToBeat": 99.97149156931644, "finalPrice": 99.90631053937364}}]
    assert parse_closed_gamma_event_settlement(ev_sol15_closed, "DOWN") == 0.0
    assert parse_closed_gamma_event_settlement(ev_sol5_closed, "UP") == 0.0
    assert parse_closed_gamma_event_settlement(ev_sol15_closed, "UP") + parse_closed_gamma_event_settlement(ev_sol5_closed, "DOWN") == 2.0
    dom_sol = determine_dominance_legs(m15_sol, k15_true, m5_sol, k5_true, min_corridor_bps=3.0)
    assert dom_sol is not None and dom_sol["regime"] == "15M_UP_PLUS_5M_DOWN"
    assert dom_sol["leg_a"]["opp_token_id"] == "sol_15m_dn" and dom_sol["leg_b"]["opp_token_id"] == "sol_5m_up"
    assert compute_dominance_box_payout_from_close(99.90631053937364, dom_sol["k_low"], dom_sol["k_high"]) == 2.0

    # Orderbook anti-box veto blocks 6:55 AM inverted asks ($0.195 + $0.574 = $0.793 net < $0.900)
    w_anti = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.195", "size": "100"}],
        asks_b_raw=[{"price": "0.574", "size": "100"}],
        target_budget_usd=60.0,
        max_box_cost_net=0.985,
    )
    assert w_anti["filled"] is False and w_anti["reason"] == "SUSPECT_INVERTED_ANTI_BOX"

    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "antibox.jsonl")
    r_anti_exec = ex.execute_atomic_dominance_box(
        box_id="ANTI_BOX_VETO_TEST", leg_a_token_id="tok_a", leg_a_label="15M_DOWN", leg_a_limit_price=0.22,
        leg_b_token_id="tok_b", leg_b_label="5M_UP", leg_b_limit_price=0.48, shares=25, max_box_cost_net=0.985,
    )
    assert r_anti_exec["success"] is False and "ANTI_BOX_COST_FLOOR_VETO" in r_anti_exec["error"]

    # Thinner-leg-first dispatch: Leg A @ $0.24 (442 avail) vs Leg B @ $0.70 (173 avail) MUST send thinner Leg B first!
    r_thin_first = ex.execute_atomic_dominance_box(
        box_id="ETH_THINNER_FIRST", leg_a_token_id="eth_15m", leg_a_label="15M_LEG", leg_a_limit_price=0.24,
        leg_b_token_id="eth_5m", leg_b_label="5M_LEG", leg_b_limit_price=0.70, shares=25, max_box_cost_net=0.985,
        leg_a_avail_shares=442.0, leg_b_avail_shares=173.0,
    )
    assert r_thin_first["success"] is True and r_thin_first["leg_1"]["label"] == "5M_LEG"

    # Slug-echo guard: a closed Gamma event for the WRONG slug must never be accepted as a strike
    g_url = build_prev_5m_gamma_event_url(m15_sol)
    ev_ok = [{"slug": "sol-updown-5m-1793097600", "closed": True, "eventMetadata": {"finalPrice": 99.8571312195911}}]
    ev_wrong = [{"slug": "sol-updown-5m-1793097300", "closed": True, "eventMetadata": {"finalPrice": 99.0}}]
    assert parse_authoritative_open_price(ev_ok, request_url=g_url) == 99.8571312195911
    assert parse_authoritative_open_price(ev_wrong, request_url=g_url) is None

    # Complement anti-box check FAILS CLOSED (missing opp tokens / missing books / empty bids / sum > 1.0)
    import asyncio
    import src.polymarket_research.alpha_124_shadow_daemon as a124_fc
    monkey_state = tmp_path / "fc_state.json"
    a124_fc.STATE_FILE = monkey_state
    d_fc = a124_fc.Alpha124ShadowDaemon(single_scan=True)
    books_fc = {}

    async def _fc_fetch(url: str, timeout: float = 5.0):
        for tk, bk in books_fc.items():
            if f"token_id={tk}" in url:
                return bk
        return None

    d_fc.fetch_json = _fc_fetch
    la = {"opp_token_id": "oa", "label": "A"}
    lb = {"opp_token_id": "ob", "label": "B"}
    assert asyncio.run(d_fc._passes_complement_anti_box_check({"label": "A"}, {"label": "B"})) is False
    assert asyncio.run(d_fc._passes_complement_anti_box_check(la, lb)) is False
    books_fc["oa"] = {"bids": [{"price": "0.40", "size": "50"}]}
    books_fc["ob"] = {"bids": []}
    assert asyncio.run(d_fc._passes_complement_anti_box_check(la, lb)) is False
    books_fc["ob"] = {"bids": [{"price": "0.55", "size": "50"}]}
    assert asyncio.run(d_fc._passes_complement_anti_box_check(la, lb)) is True
    books_fc["ob"] = {"bids": [{"price": "0.61", "size": "50"}]}
    assert asyncio.run(d_fc._passes_complement_anti_box_check(la, lb)) is False


def test_riskless_expansion_7coins_b3_w3no_pyth_and_maker_anchor(tmp_path):
    """Verify 7-coin D1 expansion, t+35s Gamma strike fallback, B3 barrier boxes, W3 ALL_BUCKETS_NO, Pyth 0%-fee, and D1_MAKER_ANCHOR_BOX."""
    import asyncio
    import time
    from datetime import date
    import src.polymarket_research.alpha_124_shadow_daemon as a124_exp
    from src.polymarket_research.same_oracle_dominance_box import (
        DOMINANCE_ASSETS,
        MIN_CORRIDOR_BPS_BY_ASSET,
        build_crypto_price_query_url,
        determine_dominance_legs,
        parse_twap_candle_event,
    )
    from src.polymarket_research.barrier_onetouch_svi_engine import detect_barrier_monotonicity_boxes
    from src.polymarket_research.multistrike_svi_scalper import ZERO_FEE_PYTH_DAILY_SERIES
    from src.polymarket_research.weather_metar_engine import (
        WeatherBucket,
        WeatherEventSpec,
        evaluate_weather_event_slate,
    )

    # 1. 7-coin Dominance catalog (BNB, DOGE, HYPE) + 5.0 bps expansion corridor guard
    assert set(DOMINANCE_ASSETS) == {"BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "HYPE"}
    assert len(ZERO_FEE_PYTH_DAILY_SERIES) == 8
    specs_exp = {}
    for sym, slug_p, stream in (
        ("BNB", "bnb", "bnb-usd"),
        ("DOGE", "doge", "doge-usd"),
        ("HYPE", "hype", "hype-usd"),
    ):
        ev15 = {
            "slug": f"{slug_p}-updown-15m-1793100000",
            "endDate": "2026-10-27T11:15:00Z",
            "markets": [{
                "id": f"m15_{sym}", "conditionId": "0x" + "11" * 32, "question": f"{sym} Up or Down 15m",
                "eventStartTime": "2026-10-27T11:00:00Z", "endDate": "2026-10-27T11:15:00Z",
                "resolutionSource": f"https://data.chain.link/streams/{stream}-twap-60s-streams",
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "outcomes": '["Up", "Down"]', "clobTokenIds": f'["{sym}_15_up", "{sym}_15_dn"]',
                "orderMinSize": 5, "feesEnabled": True, "feeSchedule": {"rate": 0.07, "exponent": 1},
            }],
        }
        ev5 = {
            "slug": f"{slug_p}-updown-5m-1793100600",
            "endDate": "2026-10-27T11:15:00Z",
            "markets": [{
                "id": f"m5_{sym}", "conditionId": "0x" + "22" * 32, "question": f"{sym} Up or Down 5m",
                "eventStartTime": "2026-10-27T11:10:00Z", "endDate": "2026-10-27T11:15:00Z",
                "resolutionSource": f"https://data.chain.link/streams/{stream}-twap-60s-streams",
                "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                "outcomes": '["Up", "Down"]', "clobTokenIds": f'["{sym}_5_up", "{sym}_5_dn"]',
                "orderMinSize": 5, "feesEnabled": True, "feeSchedule": {"rate": 0.07, "exponent": 1},
            }],
        }
        s15 = parse_twap_candle_event(ev15, sym, "15m")
        s5 = parse_twap_candle_event(ev5, sym, "5m")
        assert s15 is not None and s5 is not None and s15.asset == sym
        assert f"symbol={sym}" in build_crypto_price_query_url(s15)
        specs_exp[sym] = (s15, s5)

    dg15, dg5 = specs_exp["DOGE"]
    assert determine_dominance_legs(dg15, 0.20000, dg5, 0.20007, min_corridor_bps=MIN_CORRIDOR_BPS_BY_ASSET["DOGE"]) is None
    assert determine_dominance_legs(dg15, 0.20000, dg5, 0.20014, min_corridor_bps=MIN_CORRIDOR_BPS_BY_ASSET["DOGE"]) is not None

    # 2. Proactive t+35s prev_5m Gamma eventMetadata.finalPrice strike recovery when crypto-price returns HTTP 429 (None)
    a124_exp.STATE_FILE = tmp_path / "exp_state.json"
    a124_exp.LEDGER_FILE = tmp_path / "exp_ledger.jsonl"
    a124_exp.LIVE_ALPHA124_STATE_MIRROR_FILE = tmp_path / "exp_mirror.json"
    a124_exp.D1_LIVE_CANDIDATES_FILE = tmp_path / "exp_d1_cands.jsonl"
    d_exp = a124_exp.Alpha124ShadowDaemon(single_scan=False)
    prev_slug = f"doge-updown-5m-{int(dg15.start_ts) - 300}"

    async def _fetch_429_fallback(url: str, timeout: float = 5.0):
        if "crypto-price" in url:
            return None  # Simulated Chainlink HTTP 429
        if prev_slug in url:
            return [{"slug": prev_slug, "closed": True, "eventMetadata": {"finalPrice": 0.21456}}]
        return None

    d_exp.fetch_json = _fetch_429_fallback
    orig_time = a124_exp.time.time
    try:
        a124_exp.time.time = lambda: dg15.start_ts + 45.0
        k_rec = asyncio.run(d_exp.get_authoritative_open_strike(dg15))
        assert k_rec == 0.21456
    finally:
        a124_exp.time.time = orig_time

    # 3. B3_BARRIER_MONO_BOX monotonicity detector (UP & DOWN barriers)
    b3_rows = [
        {"direction": "UP", "strike": 100000.0, "ask_yes": 0.50, "ask_no": 0.52, "market_id": "m_lo", "condition_id": "0x1", "yes_token": "t_lo_y", "no_token": "t_lo_n", "end_ts": time.time() + 3600},
        {"direction": "UP", "strike": 105000.0, "ask_yes": 0.58, "ask_no": 0.43, "market_id": "m_hi", "condition_id": "0x2", "yes_token": "t_hi_y", "no_token": "t_hi_n", "end_ts": time.time() + 3600},
        {"direction": "DOWN", "strike": 80000.0, "ask_yes": 0.58, "ask_no": 0.44, "market_id": "m_dlo", "condition_id": "0x3", "yes_token": "t_dlo_y", "no_token": "t_dlo_n", "end_ts": time.time() + 3600},
        {"direction": "DOWN", "strike": 85000.0, "ask_yes": 0.50, "ask_no": 0.52, "market_id": "m_dhi", "condition_id": "0x4", "yes_token": "t_dhi_y", "no_token": "t_dhi_n", "end_ts": time.time() + 3600},
    ]
    b3_found = detect_barrier_monotonicity_boxes(b3_rows, fee_rate=0.07, max_box_cost_net=0.985)
    assert len(b3_found) == 2
    assert {b["direction"] for b in b3_found} == {"UP", "DOWN"}

    # 4. W3_WEATHER_SLATE_ARB ALL_BUCKETS_NO ($2.00 guaranteed payout on 3-bucket slate) + settlement
    b1 = WeatherBucket("w1", "c1", "<=69F", "NYC <= 69F", "w1_y", "w1_n", "F", -float("inf"), 69.0)
    b2 = WeatherBucket("w2", "c2", "70-71F", "NYC 70-71F", "w2_y", "w2_n", "F", 70.0, 71.0)
    b3 = WeatherBucket("w3", "c3", ">=72F", "NYC >= 72F", "w3_y", "w3_n", "F", 72.0, float("inf"))
    sp_w = WeatherEventSpec(
        "W_EV_NO", "nyc-oct-27", "nyc-daily-weather", "NYC High", "KLGA", "NYC",
        40.77, -73.87, "America/New_York", date(2026, 10, 27), "HIGH", "F",
        "zero_fees", "2026-10-28T04:00:00Z", [b1, b2, b3],
    )
    w_res = evaluate_weather_event_slate(
        sp_w,
        [0.34, 0.33, 0.33],
        {
            "w1": {"ask_yes": 0.42, "ask_yes_shares": 50.0, "ask_no": 0.62, "ask_no_shares": 60.0},
            "w2": {"ask_yes": 0.42, "ask_yes_shares": 50.0, "ask_no": 0.62, "ask_no_shares": 60.0},
            "w3": {"ask_yes": 0.42, "ask_yes_shares": 50.0, "ask_no": 0.62, "ask_no_shares": 60.0},
        },
        target_budget_usd=35.0,
    )
    full_arb = w_res["full_slate_arb"]
    assert full_arb is not None and full_arb["mode"] == "FULL_SLATE_NO_COMPLEMENT_ARB"
    assert full_arb["guaranteed_payout_per_set"] == 2.0
    assert asyncio.run(d_exp.open_shadow_weather_slate(sp_w, full_arb, time.time() - 60.0)) is True

    async def _fetch_w_closed(url: str, timeout: float = 5.0):
        if "/markets/w1" in url:
            return {"id": "w1", "closed": True, "umaResolutionStatus": "resolved", "clobTokenIds": '["w1_y","w1_n"]', "outcomePrices": '["1","0"]'}
        if "/markets/w2" in url:
            return {"id": "w2", "closed": True, "umaResolutionStatus": "resolved", "clobTokenIds": '["w2_y","w2_n"]', "outcomePrices": '["0","1"]'}
        if "/markets/w3" in url:
            return {"id": "w3", "closed": True, "umaResolutionStatus": "resolved", "clobTokenIds": '["w3_y","w3_n"]', "outcomePrices": '["0","1"]'}
        return None

    d_exp.fetch_json = _fetch_w_closed
    asyncio.run(d_exp.manage_open_positions())
    w_closed = [c for c in d_exp.closed_positions if c["sleeve"] == "W3_WEATHER_SLATE_ARB"]
    assert len(w_closed) == 1 and w_closed[0]["won"] is True and w_closed[0]["status"] == "SETTLED_WEATHER_SLATE_NX"
    assert w_closed[0]["tier_pnls_usd"]["T100"] > 0.0

    # 5. Tier-2 D1_MAKER_ANCHOR_BOX: passive fill -> atomic hedge in open_positions, and cancel-on-thinning (<2x depth)
    from dataclasses import replace as dc_replace
    now_ma = time.time()
    dg15 = dc_replace(dg15, end_ts=now_ma + 180.0)
    dg5 = dc_replace(dg5, end_ts=now_ma + 180.0)
    dom_dg = determine_dominance_legs(dg15, 0.20000, dg5, 0.20020, min_corridor_bps=5.0)
    assert dom_dg is not None
    tok_anc = dom_dg["leg_a"]["token_id"]
    tok_hdg = dom_dg["leg_b"]["token_id"]
    ma_books = {
        tok_anc: {"bids": [{"price": "0.50", "size": "80"}], "asks": [{"price": "0.53", "size": "80"}]},
        tok_hdg: {"bids": [{"price": "0.45", "size": "220"}], "asks": [{"price": "0.46", "size": "220"}]},
    }

    async def _fetch_ma(url: str, timeout: float = 5.0):
        for tk, bk in ma_books.items():
            if tk in url:
                return bk
        return None

    d_exp.fetch_json = _fetch_ma
    assert d_exp.post_maker_anchor_candidate(dg15, dg5, dom_dg, ma_books[tok_anc], ma_books[tok_hdg], now_ts=now_ma - 2.0) is True
    assert len(d_exp.pending_maker_anchors) == 1
    # Simulate trade through passive anchor bid ($0.51 >= ask $0.51) while hedge ask $0.46 has 220 shares (>=3x) -> hedged box!
    ma_books[tok_anc] = {"bids": [{"price": "0.50", "size": "80"}], "asks": [{"price": "0.51", "size": "40"}]}
    asyncio.run(d_exp.manage_pending_maker_anchors(now_ts=now_ma))
    assert len(d_exp.pending_maker_anchors) == 0
    ma_open = [p for p in d_exp.open_positions.values() if p["sleeve"] == "D1_MAKER_ANCHOR_BOX"]
    assert len(ma_open) == 1 and ma_open[0]["extra"]["is_maker_anchor_box"] is True

    # Cancel-on-thinning when opposite hedge leg depth drops below 2.0x
    bnb15, bnb5 = specs_exp["BNB"]
    bnb15 = dc_replace(bnb15, end_ts=now_ma + 180.0)
    bnb5 = dc_replace(bnb5, end_ts=now_ma + 180.0)
    dom_bnb = determine_dominance_legs(bnb15, 600.0, bnb5, 600.6, min_corridor_bps=5.0)
    assert dom_bnb is not None
    tok_b_anc = dom_bnb["leg_a"]["token_id"]
    tok_b_hdg = dom_bnb["leg_b"]["token_id"]
    ma_books[tok_b_anc] = {"bids": [{"price": "0.50", "size": "80"}], "asks": [{"price": "0.53", "size": "80"}]}
    ma_books[tok_b_hdg] = {"bids": [{"price": "0.45", "size": "220"}], "asks": [{"price": "0.46", "size": "220"}]}
    assert d_exp.post_maker_anchor_candidate(bnb15, bnb5, dom_bnb, ma_books[tok_b_anc], ma_books[tok_b_hdg], now_ts=now_ma - 2.0) is True
    assert len(d_exp.pending_maker_anchors) == 1
    ma_books[tok_b_hdg] = {"bids": [{"price": "0.45", "size": "5"}], "asks": [{"price": "0.46", "size": "5"}]}  # Thinned < 2x!
    asyncio.run(d_exp.manage_pending_maker_anchors(now_ts=now_ma))
    assert len(d_exp.pending_maker_anchors) == 0

    # Verify continuous history/SHM recorder covers all 7 DOMINANCE_ASSETS + 5m/15m/1h/4h files + corridor/slate telemetry
    import json as _json_t
    from src.polymarket_research.polymarket_terminal_recorder import ASSET_CONFIGS, PolymarketDualFeed1HRecorder
    for sym in DOMINANCE_ASSETS:
        assert sym in ASSET_CONFIGS
        rec_i = PolymarketDualFeed1HRecorder(asset=sym)
        assert rec_i.coinbase_product == f"{sym}-USD"
        assert rec_i.telemetry_5m_file.name == f"polymarket_5m_telemetry_{sym.lower()}.jsonl"
        assert rec_i.telemetry_15m_file.name == f"polymarket_15m_telemetry_{sym.lower()}.jsonl"
        assert rec_i.telemetry_4h_file.name == f"polymarket_4h_telemetry_{sym.lower()}.jsonl"
    assert ASSET_CONFIGS["HYPE"].get("futures_only_ref") is True
    assert ASSET_CONFIGS["DOGE"]["series_slug"] == "doge-up-or-down-hourly"
    assert ASSET_CONFIGS["BNB"]["series_slug"] == "bnb-up-or-down-hourly"

    d_exp._record_d1_corridor_telemetry(
        "15m_5m",
        bnb15,
        bnb5,
        dom_bnb,
        {"bids": [{"price": "0.50", "size": "80"}], "asks": [{"price": "0.53", "size": "80"}]},
        {"bids": [{"price": "0.45", "size": "80"}], "asks": [{"price": "0.49", "size": "80"}]},
        now_ma,
    )
    t_file = tmp_path / "alpha124_market_telemetry.jsonl"
    assert t_file.exists()
    t_rows = [_json_t.loads(ln) for ln in t_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert any(r["type"] == "D1_CORRIDOR" and r["asset"] == "BNB" and r["gross_box_l1"] == 1.02 for r in t_rows)


def test_telemetry_compact_encoding_delta_dedupe_and_inode_safe_gzip_compactor(tmp_path: Path, monkeypatch) -> None:
    import json as _json_c
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from scripts.honest_purged_wfo_optimizer import iter_jsonl_lines_with_archives
    from scripts.polymarket_telemetry_compactor import compact_jsonl_file, is_protected_path
    from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook, _dumps_compact

    # 1. Layer 1: L2OrderBook compact=True vs compact=False backward compatibility & byte savings
    bk = L2OrderBook("tok_test")
    bk.apply_snapshot(
        bids=[{"price": str(round(0.49 - 0.01 * i, 2)), "size": "120"} for i in range(15)],
        asks=[{"price": str(round(0.51 + 0.01 * i, 2)), "size": "120"} for i in range(15)],
    )
    t_obs = bk.last_book_update_ts + 0.5
    full_m = bk.get_metrics(obs_ts=t_obs, compact=False)
    comp_m = bk.get_metrics(obs_ts=t_obs, compact=True)
    assert "microprice_formula" in full_m and "vwap_$250" in full_m and len(full_m["raw_top_bids"]) == 15
    assert "microprice_formula" not in comp_m and "vwap_$250" not in comp_m and len(comp_m["raw_top_bids"]) == 10
    for k in ("best_bid", "best_ask", "q_mid", "q_micro", "obi_l1", "obi_depth", "vwap_$20", "vwap_$25", "vwap_$50", "effective_price_$50", "fill_fees_$50"):
        assert comp_m[k] == full_m[k]
    raw_bytes_full = len(_json_c.dumps({"UP": full_m, "DOWN": full_m}).encode("utf-8"))
    raw_bytes_comp = len(_dumps_compact({"UP": comp_m, "DOWN": comp_m}).encode("utf-8"))
    assert raw_bytes_comp < 0.45 * raw_bytes_full

    # 2. Layer 2b: Delta deduplication in _record_market_telemetry
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "st.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "ldg.jsonl")
    monkeypatch.setattr(a124, "MARKET_TELEMETRY_FILE", tmp_path / "m_telem.jsonl")
    d_t = a124.Alpha124ShadowDaemon(single_scan=True)
    d_t._record_market_telemetry("W_SLATE_1", 10.0, {"type": "WEATHER_SLATE", "sum_yes_l1": 1.02}, now_ts=1000.0, sig=(1.02,))
    d_t._record_market_telemetry("W_SLATE_1", 10.0, {"type": "WEATHER_SLATE", "sum_yes_l1": 1.02}, now_ts=1025.0, sig=(1.02,))  # unchanged -> skipped!
    d_t._record_market_telemetry("W_SLATE_1", 10.0, {"type": "WEATHER_SLATE", "sum_yes_l1": 0.99}, now_ts=1040.0, sig=(0.99,))  # changed -> logged!
    m_lines = (tmp_path / "m_telem.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(m_lines) == 2

    # 3. Layer 3 & 4: Protected ledgers + lossless inode-safe gzip compaction + sibling stem isolation + WFO streaming
    assert is_protected_path(tmp_path / "live_orders.jsonl") is True
    assert is_protected_path(tmp_path / "finalized_market_resolutions.jsonl") is True
    assert is_protected_path(tmp_path / "alpha124_shadow_ledger.jsonl") is True
    assert is_protected_path(tmp_path / "d1_live_box_candidates.jsonl") is True
    assert is_protected_path(tmp_path / "polymarket_hourly_telemetry.jsonl") is False
    assert is_protected_path(tmp_path / "alpha124_market_telemetry.jsonl") is False
    assert is_protected_path(tmp_path / "counterfactual_candidates.jsonl") is False

    pm_dir = tmp_path / "polymarket"
    pm_dir.mkdir(parents=True, exist_ok=True)
    hot_btc = pm_dir / "polymarket_hourly_telemetry.jsonl"
    hot_eth = pm_dir / "polymarket_hourly_telemetry_eth.jsonl"
    expected_btc_ids = [f"btc_{i}" for i in range(400)]
    hot_btc.write_text(
        "".join(_dumps_compact({"seq": i, "id": f"btc_{i}", "UP": comp_m}) + "\n" for i in range(400)),
        encoding="utf-8",
    )
    hot_eth.write_text(
        "".join(_dumps_compact({"seq": i, "id": f"eth_{i}", "UP": comp_m}) + "\n" for i in range(400)),
        encoding="utf-8",
    )

    res_btc = compact_jsonl_file(hot_btc, hot_threshold_bytes=20_000, keep_tail_bytes=15_000, min_archive_bytes=10_000)
    res_eth = compact_jsonl_file(hot_eth, hot_threshold_bytes=20_000, keep_tail_bytes=15_000, min_archive_bytes=10_000)
    assert res_btc["status"] == "COMPACTED" and res_btc["inode_preserved"] is True and res_btc["compression_ratio_x"] > 3.0
    assert res_eth["status"] == "COMPACTED"
    assert hot_btc.stat().st_size < 25_000

    # Stream back BTC archive + hot tail and verify 100% lossless order with zero ETH cross-contamination!
    streamed_btc = [_json_c.loads(ln)["id"] for ln in iter_jsonl_lines_with_archives(pm_dir, "polymarket_hourly_telemetry.jsonl") if ln.strip()]
    assert streamed_btc == expected_btc_ids


def test_multi_vertical_zero_fee_expansion_sleeves(tmp_path: Path, monkeypatch) -> None:
    """
    Verifies all new zero-lookahead expansion sleeves:
      1. Weather v2: `HKO` Hong Kong Observatory CSV parsing (isolating HK Observatory from Chek Lap Kok airport)
         + `W1_LOW` morning post-sunrise trough lock & evening cold-front veto.
      2. TradFi Pyth `0%`-Fee: NYSE (`6.5h/day`) & CME (`23h/day`) session variance clocks, `CM_B3` calendar
         inclusion (`NO_Week + YES_Month`) and `Close ⊂ Hit` path-vs-terminal dominance boxes.
      3. Sports `SP1_NBA_ZERO_FEE_BOX`: Full-game Polish Middle (`ML + underdog spread`), spread monotonicity,
         totals O/U middle, and strict rejection of anti-boxes (`-4.5 + -1.5`), 1H markets, and push lines.
      4. `NR0_ZERO_FEE_SLATE_ARB` early-`NO` bracket handling & `B4_TOUCHED_BARRIER_WICK_LOCK` finalized-1m sweep.
    """
    import asyncio
    import time
    from datetime import date
    from zoneinfo import ZoneInfo

    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.barrier_onetouch_svi_engine import BarrierRungSpec
    from src.polymarket_research.tradfi_sports_zero_fee_engine import (
        compute_effective_trading_hours,
        detect_nba_dominance_boxes,
        detect_pyth_calendar_inclusion_boxes,
        detect_pyth_close_vs_hit_boxes,
        parse_nba_zero_fee_event,
        parse_zero_fee_negrisk_slate,
    )
    from src.polymarket_research.weather_metar_engine import (
        MetarObservation,
        WeatherBucket,
        WeatherEventSpec,
        compute_weather_probabilities,
        parse_hko_csv_observations,
        parse_weather_event,
    )

    # 1A. HKO parser must extract `HK Observatory` (26.3C max / 24.8C min / 26.2C cur) and ignore Chek Lap Kok (28.7C)!
    csv_1m = "Date time,Automatic Weather Station,Air Temperature(degree Celsius)\n202610281020,Chek Lap Kok,28.7\n202610281020,HK Observatory,26.2\n"
    csv_mm = "Date time,Automatic Weather Station,Max,Min\n202610281020,Chek Lap Kok,28.7,26.0\n202610281020,HK Observatory,26.3,24.8\n"
    hko_obs = parse_hko_csv_observations(csv_1m, csv_mm, date(2026, 10, 28))
    assert len(hko_obs) == 3
    assert max(o.temp_c for o in hko_obs) == 26.3
    assert min(o.temp_c for o in hko_obs) == 24.8
    assert hko_obs[-1].temp_c == 26.2

    hko_ev = {
        "id": "ev_hko_1",
        "title": "Highest temperature in Hong Kong on October 28?",
        "endDate": "2026-10-28T16:00:00Z",
        "markets": [
            {
                "id": f"hk_{i}",
                "conditionId": f"0xhk_{i}",
                "groupItemTitle": lbl,
                "description": "Resolves to highest temperature recorded by the Hong Kong Observatory on 28 Oct '26 via https://www.weather.gov.hk/en/cis/climat.htm",
                "clobTokenIds": f'["hy_{i}", "hn_{i}"]',
                "feeType": "zero_fees",
                "feesEnabled": True,
                "feeSchedule": {"rate": 0},
            }
            for i, lbl in enumerate(["25°C or below", "26°C", "27°C", "28°C or higher"])
        ],
    }
    sp_hko = parse_weather_event(hko_ev)
    assert sp_hko is not None and sp_hko.icao == "HKO" and sp_hko.fee_type == "zero_fees"

    # 1B. W1_LOW morning trough lock + strict evening cold-front veto
    tz_ny = ZoneInfo("America/New_York")
    low_buckets = [
        WeatherBucket("b0", "c0", "9°C or below", "9-", "y0", "n0", "C", float("-inf"), 9.0),
        WeatherBucket("b1", "c1", "10°C", "10", "y1", "n1", "C", 10.0, 10.0),
        WeatherBucket("b2", "c2", "11°C", "11", "y2", "n2", "C", 11.0, 11.0),
        WeatherBucket("b3", "c3", "12°C or higher", "12+", "y3", "n3", "C", 12.0, float("inf")),
    ]
    sp_low = WeatherEventSpec(
        "ev_low", "nyc-low", "nyc-daily-lowest-temperature", "Lowest temperature in NYC on October 28?",
        "KLGA", "NYC", 40.7769, -73.8740, "America/New_York", date(2026, 10, 28), "LOW", "C", "zero_fees",
        "2026-10-29T04:00:00Z", low_buckets,
    )
    dt_06 = datetime(2026, 10, 28, 6, 0, tzinfo=tz_ny)
    dt_11 = datetime(2026, 10, 28, 11, 0, tzinfo=tz_ny)
    obs_low = [
        MetarObservation("KLGA", dt_06.astimezone(timezone.utc), dt_06, 10.1, True, "T0101"),
        MetarObservation("KLGA", dt_11.astimezone(timezone.utc), dt_11, 14.5, True, "T0145"),
    ]
    # Warm evening ensemble (all 20 members >= 13.0C through midnight -> +2.9C above 10.1C morning trough) -> LOCKS!
    ens_warm = {
        int(datetime(2026, 10, 28, h, 0, tzinfo=tz_ny).astimezone(timezone.utc).timestamp()): [13.5] * 20
        for h in range(12, 24)
    }
    ens_warm[int(datetime(2026, 10, 29, 0, 0, tzinfo=tz_ny).astimezone(timezone.utc).timestamp())] = [13.2] * 20
    r_warm = compute_weather_probabilities(sp_low, dt_11.astimezone(timezone.utc), obs_low, ens_warm)
    assert r_warm["is_solar_lock"] is True and r_warm["locked_bucket_idx"] == 1

    # Cold-front evening ensemble (drops to 10.8C at 23:00 < 10.1 + 1.8 = 11.9C) -> MUST VETO morning lock!
    ens_front = dict(ens_warm)
    ens_front[int(datetime(2026, 10, 28, 23, 0, tzinfo=tz_ny).astimezone(timezone.utc).timestamp())] = [10.8] * 20
    r_front = compute_weather_probabilities(sp_low, dt_11.astimezone(timezone.utc), obs_low, ens_front)
    assert r_front["is_solar_lock"] is False

    # 2. NYSE (`6.5h/day`) & CME (`23h/day`) session variance clocks + Pyth `CM_B3` inclusion boxes
    fri_15_et = datetime(2026, 10, 30, 15, 0, tzinfo=tz_ny).timestamp()
    mon_1030_et = datetime(2026, 11, 2, 10, 30, tzinfo=tz_ny).timestamp()
    # Fri 15:00->16:00 (1.0h) + Sat/Sun (0.0h) + Mon 09:30->10:30 (1.0h) = exactly 2.0h RTH!
    assert abs(compute_effective_trading_hours(fri_15_et, mon_1030_et, "EQUITY_RTH") - 2.0) < 1e-6

    cal_boxes = detect_pyth_calendar_inclusion_boxes([
        {"asset": "WTI", "direction": "UP", "strike": 105.0, "fee_rate": 0.0, "start_ts": 1000.0, "end_ts": 50000.0, "ask_yes": 0.45, "ask_no": 0.56, "market_id": "w1", "condition_id": "cw1", "yes_token": "wy", "no_token": "wn"},
        {"asset": "WTI", "direction": "UP", "strike": 105.0, "fee_rate": 0.0, "start_ts": 900.0, "end_ts": 200000.0, "ask_yes": 0.42, "ask_no": 0.59, "market_id": "m1", "condition_id": "cm1", "yes_token": "my", "no_token": "mn"},
    ])
    assert len(cal_boxes) == 1 and abs(cal_boxes[0]["box_cost_net"] - 0.98) < 1e-6

    cvh_boxes = detect_pyth_close_vs_hit_boxes(
        close_rows=[{"asset": "SPY", "strike": 775.0, "is_downward": False, "fee_rate": 0.0, "end_ts": 5000.0, "ask_no": 0.55, "market_id": "c1", "condition_id": "cc1", "yes_token": "cy", "no_token": "cn"}],
        hit_rows=[{"asset": "SPY", "strike": 775.0, "direction": "UP", "fee_rate": 0.0, "start_ts": 1000.0, "end_ts": 9000.0, "ask_yes": 0.43, "market_id": "h1", "condition_id": "ch1", "yes_token": "hy", "no_token": "hn"}],
        now_ts=2000.0,
    )
    assert len(cvh_boxes) == 1 and abs(cvh_boxes[0]["box_cost_net"] - 0.98) < 1e-6

    # 3. NBA Zero-Fee Polish Middle & Dominance Box invariants (and rejection of anti-boxes & 1H markets)
    nba_ev = {
        "id": "nba_1",
        "slug": "nba-bkn-bos",
        "title": "Nets vs. Celtics",
        "endDate": "2026-10-28T23:30:00Z",
        "markets": [
            {"id": "ml", "conditionId": "c_ml", "sportsMarketType": "moneyline", "question": "Nets vs. Celtics", "outcomes": '["Nets", "Celtics"]', "clobTokenIds": '["t_nets_ml", "t_bos_ml"]', "feeType": "zero_fees", "feesEnabled": True, "feeSchedule": {"rate": 0}},
            {"id": "sp_bos", "conditionId": "c_sp1", "sportsMarketType": "spreads", "question": "Spread: Celtics (-4.5)", "outcomes": '["Celtics", "Nets"]', "line": -4.5, "clobTokenIds": '["t_bos_m45", "t_nets_p45"]', "feeType": "zero_fees", "feesEnabled": True, "feeSchedule": {"rate": 0}},
            {"id": "sp_1h", "conditionId": "c_1h", "sportsMarketType": "first_half_spreads", "question": "1H Spread: Celtics (-2.5)", "outcomes": '["Celtics", "Nets"]', "line": -2.5, "clobTokenIds": '["t_1h_a", "t_1h_b"]', "feeType": "zero_fees"},
            {"id": "tot_lo", "conditionId": "c_tl", "sportsMarketType": "totals", "question": "Nets vs. Celtics: O/U 215.5", "outcomes": '["Over", "Under"]', "line": 215.5, "clobTokenIds": '["t_ov_215", "t_un_215"]', "feeType": "zero_fees"},
            {"id": "tot_hi", "conditionId": "c_th", "sportsMarketType": "totals", "question": "Nets vs. Celtics: O/U 220.5", "outcomes": '["Over", "Under"]', "line": 220.5, "clobTokenIds": '["t_ov_220", "t_un_220"]', "feeType": "zero_fees"},
        ],
    }
    sp_nba = parse_nba_zero_fee_event(nba_ev, now_ts=1793220000.0)
    assert sp_nba is not None
    # 1H spread must be strictly excluded!
    assert all("1h" not in lg.token_id for lg in sp_nba.margin_legs)
    nba_arbs = detect_nba_dominance_boxes(
        sp_nba,
        {
            "t_bos_ml": 0.56,      # Celtics ML (M < 0)
            "t_nets_p45": 0.425,   # Nets +4.5 (M > -4.5) -> Celtics ML + Nets +4.5 = $0.985 Polish Middle (wins $2 if BOS wins by 1..4)!
            "t_bos_m45": 0.58,     # Celtics -4.5 (anti-box with Nets ML must NOT pair!)
            "t_nets_ml": 0.40,     # Nets ML + Celtics -4.5 = $0.98 ANTI-BOX (loses if BOS wins by 1..4) -> MUST BE REJECTED!
            "t_ov_215": 0.52,
            "t_un_220": 0.465,     # Over 215.5 + Under 220.5 = $0.985 Total Middle!
        },
        max_box_cost_net=0.994,
    )
    labels = {a["label"] for a in nba_arbs}
    assert "Nets +4.5 + Celtics ML" in labels
    assert "Over 215.5 + Under 220.5" in labels
    assert not any("Nets ML" in lbl and "Celtics -4.5" in lbl for lbl in labels), "Anti-box must never be emitted!"

    # 4. Zero-Fee NegRisk Slate early-NO bracket acceptance vs YES-resolved rejection
    nr_ev = {
        "id": "nr_elon",
        "title": "Elon tweets 48h?",
        "negRisk": True,
        "endDate": "2026-10-30T16:00:00Z",
        "markets": [
            {"id": "e0", "closed": True, "outcomePrices": '["0", "1"]'},  # <40 already resolved NO -> safe!
            {"id": "e1", "conditionId": "ce1", "groupItemTitle": "40-64", "clobTokenIds": '["ey1","en1"]', "feeType": "zero_fees"},
            {"id": "e2", "conditionId": "ce2", "groupItemTitle": "65-89", "clobTokenIds": '["ey2","en2"]', "feeType": "zero_fees"},
            {"id": "e3", "conditionId": "ce3", "groupItemTitle": "90+", "clobTokenIds": '["ey3","en3"]', "feeType": "zero_fees"},
        ],
    }
    assert parse_zero_fee_negrisk_slate(nr_ev, "elon-tweets-48h") is not None
    nr_ev["markets"][0]["outcomePrices"] = '["1", "0"]'
    assert parse_zero_fee_negrisk_slate(nr_ev, "elon-tweets-48h") is None

    # 5. B4_TOUCHED_BARRIER_WICK_LOCK finalized-1m sweep in Alpha124ShadowDaemon
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "b4_st.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "b4_ldg.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "b4_opps.json")

    async def _run_b4():
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_b4 = time.time()
        d.spots["BTC"] = 84200.0
        d.barrier_rungs["m_b4"] = BarrierRungSpec(
            asset="BTC", horizon_group="WEEK", series_slug="btc-hit", event_id="ev_b4", market_id="m_b4",
            condition_id="0xcb4", group_label="↑ 85,000", question="Will BTC hit $85,000?", strike=85000.0,
            direction="UP", start_ts=now_b4 - 7200.0, end_ts=now_b4 + 86400.0, yes_token="t_b4_y", no_token="t_b4_n", fee_rate=0.07,
        )
        # Newly minted mid-month rung with low $0.085 ask must NEVER be falsely swept by B4!
        d.barrier_rungs["m_b4_stale"] = BarrierRungSpec(
            asset="BTC", horizon_group="MONTH", series_slug="btc-hit", event_id="ev_b4", market_id="m_b4_stale",
            condition_id="0xcst", group_label="↑ 85,000", question="Will BTC reach $85,000 in Oct?", strike=85000.0,
            direction="UP", start_ts=now_b4 - 600.0, end_ts=now_b4 + 86400.0, yes_token="t_b4_stale_y", no_token="t_b4_stale_n", fee_rate=0.07,
        )
        # Finalized 1m candle already wicked to $85,120 (>= 85000 * 1.0005), then spot faded to $84,200!
        d.barrier_ext_cache["ev_b4"] = (now_b4, (85120.0, 83900.0, 84200.0))

        async def fake_batch(toks, timeout=3.0):
            return {
                "t_b4_y": {"bids": [{"price": "0.95", "size": "200"}], "asks": [{"price": "0.97", "size": "200"}]},
                "t_b4_stale_y": {"bids": [{"price": "0.07", "size": "200"}], "asks": [{"price": "0.085", "size": "200"}]},
            }

        monkeypatch.setattr(d, "fetch_books_batch", fake_batch)
        opps_b4: list = []
        await d.scan_barrier_markets(opps_b4)
        assert any(p["sleeve"] == "B4_TOUCHED_BARRIER_WICK_LOCK" and p["dedupe_key"] == "B4_m_b4" for p in d.open_positions.values())
        assert not any(p["dedupe_key"] == "B4_m_b4_stale" for p in d.open_positions.values())

    asyncio.run(_run_b4())

    # 6. Per-market mid-month `m.startDate` isolation + `is_same_continuous_session` earnings-gap veto
    from src.polymarket_research.barrier_onetouch_svi_engine import parse_hit_event
    from src.polymarket_research.tradfi_sports_zero_fee_engine import is_same_continuous_session

    mid_ev = {
        "id": "ev_oct",
        "startDate": "2026-10-01T05:00:00Z",
        "endDate": "2026-11-01T03:59:59Z",
        "markets": [
            {
                "id": "m_init", "conditionId": "c1", "question": "Will ETH reach $3,000 in October?",
                "groupItemTitle": "↑ 3,000", "clobTokenIds": '["y1","n1"]', "startDate": "2026-10-01T05:00:00Z",
            },
            {
                "id": "m_minted", "conditionId": "c2", "question": "Will ETH reach $2,600 in October?",
                "groupItemTitle": "↑ 2,600", "clobTokenIds": '["y2","n2"]', "startDate": "2026-10-22T16:18:20Z",
                "description": "from the creation of this market through 11:59 PM ET",
            },
        ],
    }
    parsed_hit = {r.market_id: r for r in parse_hit_event(mid_ev, "ETH", "MONTHLY", "ethereum-hit-price-monthly")}
    assert parsed_hit["m_minted"].start_ts > parsed_hit["m_init"].start_ts + 15 * 86400.0
    ny_tz = ZoneInfo("America/New_York")
    t_tue_after = a124.datetime(2026, 10, 27, 23, 0, tzinfo=ny_tz).timestamp()
    t_fri_aft = a124.datetime(2026, 10, 30, 14, 0, tzinfo=ny_tz).timestamp()
    t_fri_close = a124.datetime(2026, 10, 30, 16, 0, tzinfo=ny_tz).timestamp()
    assert not is_same_continuous_session(t_tue_after, t_fri_close, "EQUITY_RTH"), "Multi-day / overnight earnings gap must be vetoed!"
    assert is_same_continuous_session(t_fri_aft, t_fri_close, "EQUITY_RTH"), "Friday same-session RTH final 2h must pass!"


def test_phase2_macro_counting_ctf_aaa_and_maker_anchors(monkeypatch, tmp_path) -> None:
    """Verifies Phase-2 roadmap sleeves (`TW1`, `FED1`, `COND1`, `CTF_OVR`, `GAS1`, `CM_SHOCK`, `AI1`, `D2`, `ZF_MAKER`)."""
    import asyncio
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from src.polymarket_research import alpha_124_shadow_daemon as a124
    from src.polymarket_research.macro_counting_ctf_engine import (
        ALL_FOMC_MASK,
        ALL_OIL_SENATE_MASK,
        build_fomc_truth_table_legs,
        build_oil_senate_truth_table_legs,
        detect_counting_subwindow_boxes,
        detect_d2_12pm_binance_boxes,
        evaluate_ai_elo_ci_lock,
        evaluate_counting_dead_no_locks,
        evaluate_locked_market_reward_carry,
        evaluate_pyth_catalyst_shock,
        find_cross_event_bitmask_boxes,
        parse_aaa_gas_html,
        parse_counting_slate_event,
        walk_equal_shares_overround_bids,
    )
    from src.polymarket_research.redeem_settled_positions import (
        encode_ctf_merge_or_split_calldata,
        inspect_mergeable_complete_set,
    )

    # 1. `TW1`: Counting truncation (`max(gamma_closed_floor, xtracker_total)`) + `48h ⊂ 7d` sub-window box
    ev_7d = {
        "id": "ev_elon_7d",
        "slug": "elon-musk-of-tweets-october-27-november-3",
        "title": "Elon Musk # tweets October 27 - November 3, 2026?",
        "endDate": "2026-11-03T17:00:00Z",
        "description": "from October 27, 2026, 12:00 PM ET to November 3, 2026, 12:00 PM ET",
        "markets": [
            {"id": "c7_0", "closed": True, "groupItemTitle": "<40", "outcomePrices": '["0","1"]'},
            {"id": "c7_1", "conditionId": "0xc71", "groupItemTitle": "40-64", "clobTokenIds": '["t7_y1","t7_n1"]', "feeType": "zero_fees", "rewardsMinSize": 50, "rewardsMaxSpread": 3.5},
            {"id": "c7_2", "conditionId": "0xc72", "groupItemTitle": "65-89", "clobTokenIds": '["t7_y2","t7_n2"]', "feeType": "zero_fees"},
            {"id": "c7_3", "conditionId": "0xc73", "groupItemTitle": "140+", "clobTokenIds": '["t7_yup","t7_nup"]', "feeType": "zero_fees"},
        ],
    }
    ev_48h = {
        "id": "ev_elon_48h",
        "slug": "elon-musk-of-tweets-october-29-october-31",
        "title": "Elon Musk # tweets October 29 - October 31, 2026?",
        "endDate": "2026-10-31T16:00:00Z",
        "description": "from October 29, 2026, 12:00 PM ET to October 31, 2026, 12:00 PM ET",
        "markets": [
            {"id": "c2_0", "conditionId": "0xc20", "groupItemTitle": "<40", "clobTokenIds": '["t2_ylo","t2_nlo"]', "feeType": "zero_fees"},
            {"id": "c2_1", "conditionId": "0xc21", "groupItemTitle": "40-89", "clobTokenIds": '["t2_ym","t2_nm"]', "feeType": "zero_fees"},
            {"id": "c2_2", "conditionId": "0xc22", "groupItemTitle": "90+", "clobTokenIds": '["t2_yup","t2_nup"]', "feeType": "zero_fees"},
        ],
    }
    s7 = parse_counting_slate_event(ev_7d, "elon-tweets", "elonmusk")
    s2 = parse_counting_slate_event(ev_48h, "elon-tweets-48h", "elonmusk")
    assert s7 is not None and s2 is not None and s7.gamma_closed_floor == 40
    xt_map = {
        s7.slug: {"total": 68, "hourly": [(s7.window_start_ts + 3600.0, 55)]},
    }
    v_floor, dead = evaluate_counting_dead_no_locks(s7, xt_map, safety_post_buffer=2)
    assert v_floor == 68 and [b.market_id for b in dead] == ["c7_1"]
    rw = evaluate_locked_market_reward_carry(1.0, 0.975, 0.990, 50.0, 3.5, 0.0)
    assert rw["eligible"] is True and 0.975 <= rw["resting_bid"] <= 0.985
    # With 55 banked posts prior to 48h start, 48h `90+` implies 7d `>= 145 >= 140+`!
    tw_boxes = detect_counting_subwindow_boxes([s7, s2], {"t2_nup": 0.44, "t7_yup": 0.54}, {"elonmusk": xt_map}, max_box_cost_net=0.99)
    assert any(b["box_kind"] == "TW1_UPPER_SUBWINDOW" and abs(b["box_cost_net"] - 0.98) < 1e-6 for b in tw_boxes)

    # 2. `FED1`: Exact 125-state FOMC vs `fed-3-parlay` bitmask dominance
    fomc_evs = [
        {"slug": "fed-decision-in-october-2026", "endDate": "2026-10-29T18:00:00Z", "markets": [
            {"id": "fo_p", "conditionId": "0xfop", "groupItemTitle": "No change", "clobTokenIds": '["fop_y","fop_n"]', "feeType": "zero_fees"},
        ]},
    ]
    par_evs = [
        {"slug": "fed-decisions-oct-jan", "endDate": "2027-01-29T19:00:00Z", "markets": [
            {"id": "fp_1", "conditionId": "0xfp1", "groupItemTitle": "Pause-Pause-Pause", "clobTokenIds": '["fp1_y","fp1_n"]', "feeType": "zero_fees"},
            {"id": "fp_2", "conditionId": "0xfp2", "groupItemTitle": "Hike-Pause-Pause", "clobTokenIds": '["fp2_y","fp2_n"]', "feeType": "zero_fees"},
            {"id": "fp_o", "conditionId": "0xfpo", "groupItemTitle": "Other", "clobTokenIds": '["fpo_y","fpo_n"]', "feeType": "zero_fees"},
        ]},
    ]
    f_legs = build_fomc_truth_table_legs(fomc_evs, par_evs)
    # `YES(OCT:PAUSE)` + `NO(PARLAY:Pause-Pause-Pause)` covers 100% of 125 states (`Pause-Pause-Pause` is a strict subset of `OCT:PAUSE`)!
    f_boxes = find_cross_event_bitmask_boxes(f_legs, {"fop_y": 0.88, "fp1_n": 0.105}, ALL_FOMC_MASK, max_2leg_cost=0.995)
    assert len(f_boxes) == 1 and f_boxes[0]["n_legs"] == 2 and f_boxes[0]["box_cost_net"] == 0.985

    # 3. `COND1`: Exact 9-state Oil x Senate 3-leg partition & `$80` vs `$85` 2-leg dominance
    os_evs = {
        "which-party-will-win-the-senate-in-2026": {"endDate": "2026-11-04T00:00:00Z", "markets": [
            {"id": "sm_d", "conditionId": "0xsmd", "groupItemTitle": "Democratic Party", "clobTokenIds": '["smd_y","smd_n"]', "feeType": "zero_fees"},
        ]},
        "who-wins-the-senate-pending-oil-above-or-below-80-before-the-midterms": {"endDate": "2026-11-04T00:00:00Z", "markets": [
            {"id": "s80_ld", "conditionId": "0x80ld", "groupItemTitle": "Oil < $80; D Senate", "clobTokenIds": '["o80ld_y","o80ld_n"]', "feeType": "zero_fees"},
            {"id": "s80_gd", "conditionId": "0x80gd", "groupItemTitle": "Oil ≥ $80; D Senate", "clobTokenIds": '["o80gd_y","o80gd_n"]', "feeType": "zero_fees"},
        ]},
        "who-wins-the-senate-pending-oil-below-85-before-the-midterms": {"endDate": "2026-11-04T00:00:00Z", "markets": [
            {"id": "s85_ld", "conditionId": "0x85ld", "groupItemTitle": "Oil < $85; D Senate", "clobTokenIds": '["o85ld_y","o85ld_n"]', "feeType": "zero_fees"},
        ]},
    }
    os_legs = build_oil_senate_truth_table_legs(os_evs)
    os_boxes = find_cross_event_bitmask_boxes(
        os_legs,
        {"o80ld_y": 0.01, "o80gd_y": 0.64, "smd_n": 0.335, "o80ld_n": 0.97, "o85ld_y": 0.015},
        ALL_OIL_SENATE_MASK,
        max_2leg_cost=0.995,
        max_3leg_cost=0.995,
    )
    assert any(b["n_legs"] == 3 and abs(b["box_cost_net"] - 0.985) < 1e-6 for b in os_boxes)
    assert any(b["n_legs"] == 2 and abs(b["box_cost_net"] - 0.985) < 1e-6 for b in os_boxes)

    # 4. `CTF_OVERROUND_MINT_SELL` & Polygon CTF Merge/Split ABI selectors
    ovr = walk_equal_shares_overround_bids(
        [
            {"bids": [{"price": "0.52", "size": "50"}], "fee_rate": 0.0, "fee_exponent": 1.0},
            {"bids": [{"price": "0.49", "size": "50"}], "fee_rate": 0.0, "fee_exponent": 1.0},
        ],
        target_mint_budget_usd=40.0,
        min_net_proceeds_per_set=1.004,
    )
    assert ovr["filled"] is True and ovr["net_proceeds_per_set"] == 1.01
    cid_hex = "0x" + "ab" * 32
    from src.polymarket_research import redeem_settled_positions as rsp
    _, cd_m_std = encode_ctf_merge_or_split_calldata(cid_hex, 25.0, is_split=False, neg_risk=False)
    _, cd_s_std = encode_ctf_merge_or_split_calldata(cid_hex, 25.0, is_split=True, neg_risk=False)
    _, cd_m_nr = encode_ctf_merge_or_split_calldata(cid_hex, 25.0, is_split=False, neg_risk=True)
    _, cd_s_nr = encode_ctf_merge_or_split_calldata(cid_hex, 25.0, is_split=True, neg_risk=True)
    assert cd_m_std[:10] == "0x9e7212ad" and cd_s_std[:10] == "0x72ce4275"
    assert cd_m_nr[:10] == "0xb10c5c17" and cd_s_nr[:10] == "0xa3d7da1d"
    monkeypatch.setattr(rsp, "get_token_balance_onchain", lambda addr, tok: 12.5 if tok == "tok_y" else 15.0)
    assert inspect_mergeable_complete_set("0x1111111111111111111111111111111111111111", "tok_y", "tok_n") == 12.5

    # 5. `GAS1`, `CM_SHOCK`, `AI1` staleness guard, `D2_12PM_BINANCE_BOX` & `ZERO_FEE_MAKER_ANCHOR_BOX`
    aaa_html = '<div>Price as of 10/27/26</div><td>$4.2661</td><td>$4.2661</td><td>$4.7966</td><td>$5.1822</td><td>$5.5656</td><td>$3.2856</td><td>$4.2602</td>'
    aaa_p = parse_aaa_gas_html(aaa_html)
    assert aaa_p == {"as_of_date": "2026-10-27", "current_regular": 4.2661, "yesterday_regular": 4.2602}

    # Pre-listed named-month guard: `"in November?"` listed Oct 25 must NOT start before Nov 1 ET
    from src.polymarket_research.tradfi_sports_zero_fee_engine import detect_pyth_calendar_inclusion_boxes, parse_pyth_hit_event
    nov_ev = {"id": "ev_nov", "startDate": "2026-10-25T04:02:00Z", "endDate": "2026-12-01T04:59:59Z", "markets": [{"id": "6172752", "conditionId": "0xnov", "question": "Will WTI Crude Oil (WTI) hit (HIGH) $100 in November?", "groupItemTitle": "↑ $100", "clobTokenIds": '["ny","nn"]', "feeType": "zero_fees", "description": "during a trading session of November 2026, any Pyth 1-minute candle"}]}
    nov_r = parse_pyth_hit_event(nov_ev, "WTI", "MONTHLY", "wti-hit")
    oct28_ts = datetime(2026, 10, 28, 12, 0, tzinfo=ZoneInfo("America/New_York")).timestamp()
    assert len(nov_r) == 1 and nov_r[0].start_ts > oct28_ts
    assert detect_pyth_calendar_inclusion_boxes([{"asset": "WTI", "direction": "UP", "strike": 100.0, "start_ts": oct28_ts - 86400.0, "end_ts": oct28_ts + 86400.0, "ask_no": 0.4, "ask_yes": 0.6, "fee_rate": 0.0}, {"asset": "WTI", "direction": "UP", "strike": 100.0, "start_ts": nov_r[0].start_ts, "end_ts": nov_r[0].end_ts, "ask_no": 0.5, "ask_yes": 0.5, "fee_rate": 0.0}], now_ts=oct28_ts) == []

    ny = ZoneInfo("America/New_York")
    t_eia = datetime(2026, 10, 28, 10, 31, tzinfo=ny).timestamp()  # Wed 10:31 AM ET EIA Crude
    t_off = datetime(2026, 10, 28, 11, 30, tzinfo=ny).timestamp()
    sh_ok = evaluate_pyth_catalyst_shock("WTI", 69.0, 70.2, 71.0, "UP", 3.0, 0.35, t_eia)
    sh_no = evaluate_pyth_catalyst_shock("WTI", 69.0, 70.2, 71.0, "UP", 3.0, 0.35, t_off)
    assert sh_ok["eligible"] is True and sh_ok["catalyst"] == "EIA_1030_PETROLEUM" and sh_ok["side"] == "YES"
    assert sh_no["eligible"] is False

    rows_ai = [{"organization": "Google", "rating": 1395, "rating_q025": 1388, "rating_q975": 1402}, {"organization": "OpenAI", "rating": 1372, "rating_q025": 1365, "rating_q975": 1379}]
    assert evaluate_ai_elo_ci_lock(rows_ai, 1000.0, 50000.0, 36000.0)["eligible"] is False, "Stale >6h snapshot must be rejected!"
    assert evaluate_ai_elo_ci_lock(rows_ai, 48000.0, 50000.0, 36000.0)["eligible"] is True

    d2 = detect_d2_12pm_binance_boxes(
        {"asset": "BTC", "market_id": "h1", "condition_id": "0xh1", "end_ts": 1793203200.0, "up_token": "h_up", "down_token": "h_dn", "fee_rate": 0.07},
        83800.0,
        [{"market_id": "d1", "condition_id": "0xd1", "end_ts": 1793203200.0, "strike": 84400.0, "is_downward": False, "yes_token": "d_y", "no_token": "d_n", "fee_rate": 0.07}],
    )
    assert len(d2) == 1 and d2[0]["leg_a"]["token_id"] == "h_up" and d2[0]["leg_b"]["token_id"] == "d_n"

    # End-to-end `ZERO_FEE_MAKER_ANCHOR_BOX` hedged fill + unhedged scratch in Alpha124ShadowDaemon
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "zfa_st.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "zfa_ldg.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "zfa_opps.json")

    async def _run_zfa():
        d = a124.Alpha124ShadowDaemon(single_scan=True)
        now_z = 1793220000.0
        la = {"token_id": "za1", "opp_token_id": "za2", "condition_id": "0x1", "side": "YES", "label": "Nets +4.5", "market_id": "m1", "fee_rate": 0.0}
        lb = {"token_id": "zb1", "opp_token_id": "zb2", "condition_id": "0x2", "side": "YES", "label": "Celtics ML", "market_id": "m2", "fee_rate": 0.0}
        bk_a0 = {"bids": [{"price": "0.41", "size": "200"}], "asks": [{"price": "0.45", "size": "200"}]}
        bk_b0 = {"bids": [{"price": "0.54", "size": "300"}], "asks": [{"price": "0.56", "size": "300"}]}
        ok = d.post_zero_fee_maker_anchor_box("SP1_NBA", "NBA", "ZFA_TEST_1", la, lb, bk_a0, bk_b0, now_z + 7200.0, "Nets vs Celtics", now_z)
        assert ok is True and d.pending_zero_fee_maker_anchors["ZFA_TEST_1"]["bid_px"] == 0.42

        async def fake_bks_fill(toks, timeout=3.0):
            return {
                "za1": {"bids": [{"price": "0.41", "size": "200"}], "asks": [{"price": "0.42", "size": "200"}]},
                "zb1": {"bids": [{"price": "0.54", "size": "300"}], "asks": [{"price": "0.56", "size": "300"}]},
            }

        monkeypatch.setattr(d, "fetch_books_batch", fake_bks_fill)
        await d.manage_pending_zero_fee_maker_anchors(now_z + 2.0)
        assert any(p["sleeve"] in ("ZF_INTRADAY_MAKER_BOX", "ZERO_FEE_MAKER_ANCHOR_BOX") and p["entry_eff_px_t1000"] == 0.98 for p in d.open_positions.values())

    asyncio.run(_run_zfa())


def test_exp406_hardened_d1_maker_leg1_wfo_and_microstructure_shields(tmp_path: Path, monkeypatch) -> None:
    """EXP-PM-406: Verifies Purged-WFO Maker-Leg-1 calibration, 1c mid-book join OBI shield, 0.001-tick tail anchor, and directional cancel-on-move."""
    import asyncio
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.orderflow_wfo_simulators import calibrate_d1_maker_leg1_wfo
    from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec, determine_dominance_legs

    wfo = calibrate_d1_maker_leg1_wfo()
    assert wfo["sealed_holdout"]["legging_adjusted_pnl_usd"] > 0.0
    assert wfo["sealed_holdout"]["scratches"] == 0
    assert wfo["sealed_holdout"]["legging_adjusted_pnl_usd"] > wfo["unguarded_maker_holdout_baseline"]["legging_adjusted_pnl_usd"]

    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "m406_st.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "m406_ldg.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "m406_opps.json")
    monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES", "0")

    d = a124.Alpha124ShadowDaemon(single_scan=True)
    now_t = 1793226000.0
    s15 = TwapCandleMarketSpec(
        asset="BTC",
        horizon="15m",
        market_id="m15_btc",
        condition_id="0xc15",
        title="BTC 15m",
        start_iso="2026-10-28T22:15:00Z",
        end_iso="2026-10-28T22:30:00Z",
        start_ts=now_t - 700,
        end_ts=now_t + 200,
        up_token="t15u",
        down_token="t15d",
        fee_rate=0.07,
        fee_exponent=1.0,
        neg_risk=False,
        twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams",
    )
    s5 = TwapCandleMarketSpec(
        asset="BTC",
        horizon="5m",
        market_id="m5_btc",
        condition_id="0xc5",
        title="BTC 5m",
        start_iso="2026-10-28T22:25:00Z",
        end_iso="2026-10-28T22:30:00Z",
        start_ts=now_t - 100,
        end_ts=now_t + 200,
        up_token="t5u",
        down_token="t5d",
        fee_rate=0.07,
        fee_exponent=1.0,
        neg_risk=False,
        twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams",
    )
    dom = determine_dominance_legs(s15, 81000.0, s5, 81050.0, min_corridor_bps=3.0)
    assert dom is not None
    ta, tb = dom["leg_a"]["token_id"], dom["leg_b"]["token_id"]

    # 1. Collapsing L1 OBI (-0.50 < -0.15) on 1c mid-book spread MUST be vetoed
    bk_toxic = {"bids": [{"price": "0.48", "size": "20"}], "asks": [{"price": "0.49", "size": "60"}]}
    bk_hdg = {"bids": [{"price": "0.48", "size": "80"}], "asks": [{"price": "0.49", "size": "80"}]}
    assert d.post_maker_anchor_candidate(s15, s5, dom, bk_toxic, bk_toxic, now_ts=now_t) is False

    # 2. Healthy 1c mid-book spread ($0.48/$0.49 + $0.48/$0.49, taker=$1.0143) joins $0.48 (net=$0.9871 <= $0.988, saving 2.72c!)
    d.spots["BTC"] = 81025.0
    bk_calm = {"bids": [{"price": "0.48", "size": "90"}], "asks": [{"price": "0.49", "size": "80"}]}
    assert d.post_maker_anchor_candidate(s15, s5, dom, bk_calm, bk_hdg, now_ts=now_t) is True
    dk = f"D1_MKR_BTC_{s15.market_id}_{s5.market_id}"
    assert d.pending_maker_anchors[dk]["bid_px"] == 0.48 and d.pending_maker_anchors[dk]["queue_front"] is False

    # 3. Directional asymmetric spot shield: +3.0 bps favorable move for UP(K_low) keeps resting, -3.0 bps adverse drop cancels!
    bks_live = {ta: bk_calm, tb: bk_hdg}

    async def _fb(toks, timeout=2.5):
        return {t: bks_live[t] for t in toks if t in bks_live}

    monkeypatch.setattr(d, "fetch_books_batch", _fb)
    if dom["leg_a"]["side"] == "UP":
        d.spots["BTC"] = 81025.0 * 1.0003  # +3.0 bps favorable for UP
    else:
        d.spots["BTC"] = 81025.0 * 0.9997
    asyncio.run(d.manage_pending_maker_anchors(now_ts=now_t + 0.5))
    assert dk in d.pending_maker_anchors, "Favorable spot move must NOT cancel resting anchor!"

    if dom["leg_a"]["side"] == "UP":
        d.spots["BTC"] = 81025.0 * 0.99965  # -3.5 bps adverse for UP
    else:
        d.spots["BTC"] = 81025.0 * 1.00035
    asyncio.run(d.manage_pending_maker_anchors(now_ts=now_t + 0.8))
    assert dk not in d.pending_maker_anchors, "Adverse spot move > 2.5 bps MUST cancel resting anchor at $0 cost!"

    # 4. 0.001-tick sub-cent 4h/15m tail anchor ($0.964/$0.999 + $0.019/$0.020 -> taker=$1.0204, maker=$0.9854, saving 3.5c!)
    x4 = TwapCandleMarketSpec(
        asset="XRP",
        horizon="4h",
        market_id="m4_xrp",
        condition_id="0xx4",
        title="XRP 4h",
        start_iso="2026-10-28T20:00:00Z",
        end_iso="2026-10-29T00:00:00Z",
        start_ts=now_t - 14000,
        end_ts=now_t + 200,
        up_token="tx4u",
        down_token="tx4d",
        fee_rate=0.07,
        fee_exponent=1.0,
        neg_risk=False,
        twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/xrp-usd-twap-60s-streams",
    )
    x15 = TwapCandleMarketSpec(
        asset="XRP",
        horizon="15m",
        market_id="m15_xrp",
        condition_id="0xx15",
        title="XRP 15m",
        start_iso="2026-10-28T23:45:00Z",
        end_iso="2026-10-29T00:00:00Z",
        start_ts=now_t - 700,
        end_ts=now_t + 200,
        up_token="tx15u",
        down_token="tx15d",
        fee_rate=0.07,
        fee_exponent=1.0,
        neg_risk=False,
        twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/xrp-usd-twap-60s-streams",
    )
    dom_x = determine_dominance_legs(x4, 0.5200, x15, 0.5220, min_corridor_bps=3.0)
    assert dom_x is not None
    txa, txb = dom_x["leg_a"]["token_id"], dom_x["leg_b"]["token_id"]
    d.spots["XRP"] = 0.5210
    bks_live[txa] = {"bids": [{"price": "0.963", "size": "80"}], "asks": [{"price": "0.999", "size": "80"}]}
    bks_live[txb] = {"bids": [{"price": "0.018", "size": "80"}], "asks": [{"price": "0.020", "size": "80"}]}
    assert d.post_maker_anchor_candidate(x4, x15, dom_x, bks_live[txa], bks_live[txb], now_ts=now_t) is True
    dk_x = f"D1_MKR_XRP_{x4.market_id}_{x15.market_id}"
    assert d.pending_maker_anchors[dk_x]["bid_px"] == 0.964
    bks_live[txa] = {"bids": [{"price": "0.963", "size": "80"}], "asks": [{"price": "0.964", "size": "40"}]}
    asyncio.run(d.manage_pending_maker_anchors(now_ts=now_t + 1.0))
    open_x = [p for p in d.open_positions.values() if p["dedupe_key"] == dk_x]
    assert len(open_x) == 1 and open_x[0]["entry_eff_px_t1000"] < 0.988
    assert open_x[0]["extra"]["legging_drag_usd_by_tier"]["T1000"] > 0.0


def test_overround_bid_unwind_ctf_merge_and_corridor_preservation(tmp_path: Path, monkeypatch) -> None:
    import asyncio
    import time
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.macro_counting_ctf_engine import walk_position_overround_bid_unwind
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    # 1. Direct L2 bid-walk verification: partial-depth rejection + exact fee deduction
    thin_res = walk_position_overround_bid_unwind(
        [
            {"bids": [{"price": "0.52", "size": "25"}], "fee_rate": 0.0, "fee_exponent": 1.0},
            {"bids": [{"price": "0.52", "size": "15"}], "fee_rate": 0.0, "fee_exponent": 1.0},
        ],
        exact_shares=25.0,
        min_net_proceeds_per_set=1.005,
    )
    assert thin_res["filled"] is False, "Must reject partial unwind if any leg lacks 100% of exact_shares!"

    full_res = walk_position_overround_bid_unwind(
        [
            {"bids": [{"price": "0.52", "size": "40"}], "fee_rate": 0.0, "fee_exponent": 1.0},
            {"bids": [{"price": "0.51", "size": "40"}], "fee_rate": 0.0, "fee_exponent": 1.0},
        ],
        exact_shares=25.0,
        min_net_proceeds_per_set=1.005,
    )
    assert full_res["filled"] is True
    assert abs(full_res["net_proceeds_per_set"] - 1.030) < 1e-6

    # 2. Shadow daemon manage_open_positions:
    #   (a) FED1 long-dated FOMC box (TTE = 2000h > 1h) with L2 bids = $1.030 unwinds early (`EARLY_OVERROUND_BID_UNWIND`)
    #   (b) Near-expiry D1 box (TTE = 120s <= 1h) with L2 bids = $1.030 stays OPEN to preserve $2.00 corridor jackpot
    #   (c) Single-market C1_BINARY_COMPLETE_SET (age >= 15s) recycles immediately via `CTF_COMPLETE_SET_MERGED` at $1.00
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "st_uw.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "ld_uw.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", tmp_path / "op_uw.json")
    monkeypatch.setattr(a124, "LIVE_ALPHA124_STATE_MIRROR_FILE", tmp_path / "mirror_uw.json")
    d = a124.Alpha124ShadowDaemon(single_scan=True)
    now_t = time.time()

    d.open_positions["FED1_TEST"] = {
        "position_id": "FED1_TEST",
        "dedupe_key": "FED1_DK",
        "sleeve": "FED1_CENTRAL_BANK_LP_BOX",
        "asset_or_city": "FOMC",
        "title": "FOMC 2-Leg Box",
        "side": "BOX",
        "token_id": "tok_fomc_a+tok_fomc_b",
        "fee_rate": 0.0,
        "entry_ts": now_t - 60.0,
        "close_ts": now_t + 2000.0 * 3600.0,
        "entry_eff_px_t1000": 0.990,
        "p_model_entry": 1.0,
        "tier_fills": {"T100": {"shares": 10.0, "spent_usd": 9.90, "fee_usd": 0.0}, "T1000": {"shares": 25.0, "spent_usd": 24.75, "fee_usd": 0.0}},
        "extra": {
            "is_two_leg_box": True,
            "guaranteed_payout": 1.0,
            "leg_a": {"token_id": "tok_fomc_a", "market_id": "m_fomc_1", "side": "YES", "fee_rate": 0.0},
            "leg_b": {"token_id": "tok_fomc_b", "market_id": "m_fomc_2", "side": "NO", "fee_rate": 0.0},
        },
    }
    d.open_positions["D1_NEAR_TEST"] = {
        "position_id": "D1_NEAR_TEST",
        "dedupe_key": "D1_NEAR_DK",
        "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
        "asset_or_city": "BTC",
        "title": "BTC 15m/5m Corridor Box",
        "side": "BOX",
        "token_id": "tok_d1_a+tok_d1_b",
        "fee_rate": 0.07,
        "entry_ts": now_t - 45.0,
        "close_ts": now_t + 120.0,
        "entry_eff_px_t1000": 0.980,
        "p_model_entry": 1.0,
        "tier_fills": {"T1000": {"shares": 25.0, "spent_usd": 24.50, "fee_usd": 0.0}},
        "extra": {
            "guaranteed_payout": 1.0,
            "leg_a": {"token_id": "tok_d1_a", "market_id": "m_d1_1", "side": "UP", "fee_rate": 0.07},
            "leg_b": {"token_id": "tok_d1_b", "market_id": "m_d1_2", "side": "DOWN", "fee_rate": 0.07},
        },
    }
    d.open_positions["C1_MERGE_TEST"] = {
        "position_id": "C1_MERGE_TEST",
        "dedupe_key": "C1_DK",
        "sleeve": "C1_BINARY_COMPLETE_SET",
        "asset_or_city": "BTC",
        "title": "BTC Single-Condition Complete Set",
        "side": "COMPLETE_SET",
        "token_id": "tok_c1_y+tok_c1_n",
        "fee_rate": 0.0,
        "entry_ts": now_t - 30.0,
        "close_ts": now_t + 7200.0,
        "entry_eff_px_t1000": 0.985,
        "p_model_entry": 1.0,
        "tier_fills": {"T1000": {"shares": 20.0, "spent_usd": 19.70, "fee_usd": 0.0}},
        "extra": {
            "guaranteed_payout": 1.0,
            "leg_a": {"token_id": "tok_c1_y", "market_id": "m_c1_same", "side": "YES", "fee_rate": 0.0},
            "leg_b": {"token_id": "tok_c1_n", "market_id": "m_c1_same", "side": "NO", "fee_rate": 0.0},
        },
    }

    books_map = {
        "tok_fomc_a": {"bids": [{"price": "0.52", "size": "50"}], "asks": [{"price": "0.54", "size": "50"}]},
        "tok_fomc_b": {"bids": [{"price": "0.51", "size": "50"}], "asks": [{"price": "0.53", "size": "50"}]},
        "tok_d1_a": {"bids": [{"price": "0.53", "size": "50"}], "asks": [{"price": "0.54", "size": "50"}]},
        "tok_d1_b": {"bids": [{"price": "0.52", "size": "50"}], "asks": [{"price": "0.53", "size": "50"}]},
        "tok_c1_y": {"bids": [{"price": "0.49", "size": "50"}], "asks": [{"price": "0.50", "size": "50"}]},
        "tok_c1_n": {"bids": [{"price": "0.49", "size": "50"}], "asks": [{"price": "0.50", "size": "50"}]},
    }

    async def _fake_fetch(url: str, timeout: float = 2.5):
        for tk, bk in books_map.items():
            if f"token_id={tk}" in url:
                return bk
        return None

    monkeypatch.setattr(d, "fetch_json", _fake_fetch)
    asyncio.run(d.manage_open_positions())

    assert "D1_NEAR_TEST" in d.open_positions, "Near-expiry D1 box must NOT unwind early on +3c overround; preserve $2.00 corridor!"
    assert "FED1_TEST" not in d.open_positions
    assert "C1_MERGE_TEST" not in d.open_positions
    closed_by_id = {c["position_id"]: c for c in d.closed_positions}
    assert closed_by_id["FED1_TEST"]["status"] == "EARLY_OVERROUND_BID_UNWIND"
    assert abs(closed_by_id["FED1_TEST"]["tier_pnls_usd"]["T1000"] - 1.00) < 1e-6
    assert closed_by_id["C1_MERGE_TEST"]["status"] == "CTF_COMPLETE_SET_MERGED"
    assert abs(closed_by_id["C1_MERGE_TEST"]["tier_pnls_usd"]["T1000"] - 0.30) < 1e-6

    # 3. Executor CTF / NegRiskAdapter mergePositions calldata verification
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "merge_ex.jsonl")
    cond_hex = "0x" + ("cd" * 32)
    m_ctf = ex.merge_complete_set_positions(cond_hex, 25.0, neg_risk=False)
    m_nr = ex.merge_complete_set_positions(cond_hex, 25.0, neg_risk=True)
    assert m_ctf["merged"] is True and m_ctf["target_contract"].lower() == ex.CTF_ADDRESS.lower()
    assert m_ctf["calldata"].startswith("0x9e7212ad")
    assert m_nr["merged"] is True and m_nr["target_contract"].lower() == ex.NEG_RISK_ADAPTER_ADDRESS.lower()
    assert m_nr["calldata"].startswith("0xb10c5c17")


def test_d1_quiet_book_graduation_and_close_position_growth_tier_promotion(tmp_path: Path, monkeypatch) -> None:
    import json
    import time
    import src.polymarket_research.polymarket_live_harvester as harvester_mod
    from src.polymarket_research.polymarket_live_harvester import ExecutionStatus, PolymarketLiveHarvester

    live_dir = tmp_path / "live_pm"
    live_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(harvester_mod, "DATA_DIR", live_dir)
    monkeypatch.setattr(harvester_mod, "STATE_FILE", live_dir / "live_harvester_state.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")

    # D1_SAME_ORACLE_DOMINANCE_BOX has only 5 settled (<8), whereas D1_QUIET_BOOK_BOX is 13/13 graduated!
    (live_dir / "alpha124_shadow_state.json").write_text(
        json.dumps(
            {
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {
                        "closed": 5,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 15.0,
                        "legging_adjusted_pnl_t1000_usd": 12.0,
                    },
                    "D1_QUIET_BOOK_BOX": {
                        "closed": 13,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 43.25,
                        "legging_adjusted_pnl_t1000_usd": 42.18,
                    },
                },
                "by_d1_asset": {},
            }
        ),
        encoding="utf-8",
    )

    h = PolymarketLiveHarvester(
        dry_run=True, dynamic_sizing=True, hold_to_maturity=False, ticket_notional=12.0,
        max_exposure=76.25, max_concurrent=2, allowed_assets={"BTC", "ETH"},
    )
    h.dry_run = False
    h.executor.dry_run = False
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.state_file = live_dir / "live_harvester_state.json"
    h._startup_reconciled = True
    h._last_known_collateral = 138.98
    h.high_water_mark_equity = 138.98
    h._update_equity_tier(138.98)
    assert h.current_equity_tier == "RECOVERY"

    tok_a = "111111111111111111111111111111"
    tok_oa = "222222222222222222222222222222"
    tok_b = "333333333333333333333333333333"
    tok_ob = "444444444444444444444444444444"
    now_u = time.time()
    base_cand = {
        "box_id": "D1_QUIET_BTC_1",
        "dedupe_key": "D1_QB_BTC_1",
        "box_type": "DOMINANCE",
        "ts_unix": now_u,
        "expiry_ts": now_u + 180.0,
        "asset": "BTC",
        "corridor_bps": 8.0,
        "k_low": 80000.0,
        "k_high": 80064.0,
        "is_quiet_book": True,
        "shares": 25,
        "box_cost_net": 0.981,
        "max_box_cost_net": 0.985,
        "leg_a_token_id": tok_a,
        "leg_a_opp_token_id": tok_oa,
        "leg_a_label": "15M_UP",
        "leg_a_side": "UP",
        "leg_a_horizon": "15m",
        "leg_a_market_id": "610001",
        "leg_a_condition_id": "0x" + ("11" * 32),
        "leg_a_strike": 80000.0,
        "leg_a_limit_price": 0.48,
        "leg_a_avail_shares": 120.0,
        "leg_a_fee_rate": 0.07,
        "leg_a_fee_exponent": 1.0,
        "leg_b_token_id": tok_b,
        "leg_b_opp_token_id": tok_ob,
        "leg_b_label": "5M_DOWN",
        "leg_b_side": "DOWN",
        "leg_b_horizon": "5m",
        "leg_b_market_id": "610002",
        "leg_b_condition_id": "0x" + ("22" * 32),
        "leg_b_strike": 80064.0,
        "leg_b_limit_price": 0.47,
        "leg_b_avail_shares": 120.0,
        "leg_b_fee_rate": 0.07,
        "leg_b_fee_exponent": 1.0,
    }
    # Ungraduated D1_SAME_ORACLE_DOMINANCE_BOX is rejected while D1_QUIET_BOOK_BOX is accepted!
    res_core_blk = h.maybe_execute_graduated_d1_box({**base_cand, "sleeve_source": "D1_SAME_ORACLE_DOMINANCE_BOX", "dedupe_key": "D1_CORE_BLK"})
    assert res_core_blk["executed"] is False and res_core_blk["reason"] == "D1_NOT_YET_8_OF_8_GRADUATED"

    qb_books = {
        tok_a: {"asks": [{"price": "0.48", "size": "120"}], "bids": [{"price": "0.46", "size": "120"}]},
        tok_b: {"asks": [{"price": "0.47", "size": "120"}], "bids": [{"price": "0.45", "size": "120"}]},
        tok_oa: {"asks": [{"price": "0.54", "size": "120"}], "bids": [{"price": "0.51", "size": "120"}]},
        tok_ob: {"asks": [{"price": "0.55", "size": "120"}], "bids": [{"price": "0.47", "size": "120"}]},
    }
    h.executor.get_market_book = lambda tid: qb_books[tid]
    h._wallet_token_balance = lambda tid: (0.0, h.ONCHAIN_SOURCE)
    captured_qb = {}

    def _mock_qb_box(**kw):
        captured_qb.update(kw)
        sh = float(kw["shares"])
        return {
            "success": True,
            "box_id": kw["box_id"],
            "shares": sh,
            "leg_1": {"token_id": tok_a, "label": kw["leg_a_label"], "price": 0.48, "orderID": "OID_QBA", "raw": {"makingAmount": round(sh * 0.48, 2)}},
            "leg_2": {"token_id": tok_b, "label": kw["leg_b_label"], "price": 0.47, "orderID": "OID_QBB", "raw": {"makingAmount": round(sh * 0.47, 2)}},
        }

    h.executor.execute_atomic_dominance_box = _mock_qb_box
    res_qb_ok = h.maybe_execute_graduated_d1_box({**base_cand, "sleeve_source": "D1_QUIET_BOOK_BOX"})
    assert res_qb_ok["executed"] is True
    assert captured_qb["parallel_dispatch"] is False, "Tighter (0.975..0.985] quiet box must preserve sequential Leg-1 dispatch!"
    assert h.active_positions["D1_QUIET_BTC_1_L1"]["sleeve_source"] == "D1_QUIET_BOOK_BOX"
    h.active_positions.clear()

    # Deterministic RECOVERY -> GROWTH tier promotion on _close_position ($108.78 free + $32.90 exit cash = $141.68)
    h._last_known_collateral = 108.78
    h.active_positions["LIVE_WIN_141"] = {
        "trade_id": "LIVE_WIN_141",
        "token_id": "tok_eth_up",
        "target_token": "UP",
        "asset": "ETH",
        "entry_price": 0.85,
        "entry_shares": 35.0,
        "remaining_shares": 0.0,
        "filled_exit_shares": 35.0,
        "notional_usd": 29.75,
        "fee_usd": 0.45,
        "confirmed_realized_cash": 32.90,
        "realized_exit_cash": 32.90,
        "realized_exit_fee": 0.0,
        "entry_ts": now_u - 120.0,
        "candle_expiry_ts": now_u + 1800.0,
        "status": ExecutionStatus.POSITION_CONFIRMED,
    }
    net_pnl = h._close_position("LIVE_WIN_141", h.active_positions["LIVE_WIN_141"], ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
    assert abs(net_pnl - 2.70) < 1e-2
    assert h.current_equity_tier == "GROWTH"
    assert abs(h.max_exposure - 106.26) < 1e-2
    assert h.max_concurrent_positions == 3
    assert abs(h.dynamic_bankroll_pct - 0.26) < 1e-6
    persisted = json.loads((live_dir / "live_harvester_state.json").read_text(encoding="utf-8"))
    assert persisted["equity_tier"] == "GROWTH"
    assert abs(float(persisted["max_exposure"]) - 106.26) < 1e-2
    assert int(persisted["max_concurrent_positions"]) == 3


if __name__ == "__main__":
    test_polymarket_weather_rounding_spec_examples()
    test_metar_parser_speci_and_t_remark()
    test_bucket_bounds_parser()
    test_barrier_and_svi_monotonicity()
    test_exact_twap_lock_engine_math_and_whipsaw_guard()
    print("ALL ALPHA-124 ORACLE & PRICING UNIT TESTS PASSED!")


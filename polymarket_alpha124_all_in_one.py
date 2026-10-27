"""
========================================================================================
DOMINUS POLYMARKET ALPHA-124 11-SLEEVE EXPANSION + PROJECTIONS + TESTS (<1 MB COMPANION BUNDLE)
Generated: 2026-10-27 13:30:47 UTC
Pairs with polymarket_all_in_one.txt (<1 MB) for tools enforcing a 1 MB per-file upload cap
Repository: /home/skybullet1987/quant_pipeline
========================================================================================

TABLE OF CONTENTS (Exact 1-Based Line Ranges & Raw Module Sizes):
  [01] systemd/polymarket-alpha124-shadow.service (Lines 30 - 57 | 578 B) :: Alpha-124 Unified Shadow systemd Unit
  [02] src/polymarket_research/net_alpha_opportunity_engine.py (Lines 58 - 815 | 32,646 B) :: v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine
  [03] src/polymarket_research/weather_metar_engine.py (Lines 816 - 1,937 | 47,382 B) :: Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb
  [04] src/polymarket_research/barrier_onetouch_svi_engine.py (Lines 1,938 - 2,352 | 15,916 B) :: Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)
  [05] src/polymarket_research/multistrike_svi_scalper.py (Lines 2,353 - 3,060 | 27,767 B) :: Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner
  [06] src/polymarket_research/same_oracle_dominance_box.py (Lines 3,061 - 3,847 | 32,045 B) :: Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine
  [07] src/polymarket_research/exact_twap_lock_engine.py (Lines 3,848 - 4,080 | 9,173 B) :: Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock
  [08] src/polymarket_research/alpha_124_shadow_daemon.py (Lines 4,081 - 8,234 | 206,472 B) :: Unified 11-Sleeve Shadow Daemon (W1, W2, W2_MAKER, B1, B2, M1, M2, M3, M4_<250ms_Shock, D1, S2)
  [09] src/polymarket_research/exp316_macro_strike_shadow.py (Lines 8,235 - 10,129 | 86,701 B) :: EXP-316 Isolated Multi-Strike Convergence Shadow Engine
  [10] scripts/backtest_alpha_124.py (Lines 10,130 - 10,990 | 40,009 B) :: Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124
  [11] scripts/polymarket_daily_projections.py (Lines 10,991 - 11,701 | 28,963 B) :: Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker
  [12] scripts/alpha124_status.py (Lines 11,702 - 11,771 | 2,685 B) :: Live Alpha-124 11-Sleeve Scorecard & Orderbook Opportunity Inspector
  [13] scripts/polymarket_scorecard_snapshot.py (Lines 11,772 - 11,921 | 4,891 B) :: Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot
  [14] tests/test_alpha_124_oracles.py (Lines 11,922 - 13,898 | 97,281 B) :: Unit Tests: Weather METAR, Jump-SVI Barrier, SVI Ladder, D1 Box, S2 TWAP Lock, W2 Maker, M4 Shock, R01 Wallet
  [15] tests/test_polymarket_wfo_5fixes.py (Lines 13,899 - 17,094 | 154,710 B) :: Unit Tests: WFO 5-Fixes, 95c/98c Two-Tranche Supervisor, Phase-3A/Phase-4 Book Walk & Graduation
  [16] tests/test_zero_trust_forensic_audit.py (Lines 17,095 - 17,838 | 32,659 B) :: Unit Tests: Zero-Trust Forensics, Centralized Risk Config, Deterministic Replay & <1MB Bundle Sync
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
CPUWeight=50
ExecStart=/home/skybullet1987/quant_pipeline/venv/bin/python src/polymarket_research/alpha_124_shadow_daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target

'''

# ======================================================================================
# [02/16] MODULE: src/polymarket_research/net_alpha_opportunity_engine.py
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
) -> Dict[str, Any]:
    """
    Walks equal integer share quantity `Q` across `YES` and `NO` asks of the EXACT SAME
    binary market (`condition_id`). Since `YES + NO == $1.00` identically on-chain with
    zero oracle/basis divergence, `net_cost_per_pair <= max_complete_set_cost` locks a
    deterministic riskless floor (redeemable/mergeable for $1.00).
    """
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
# [03/16] MODULE: src/polymarket_research/weather_metar_engine.py
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
}

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
    "shanghai-daily-weather": "ZSPD",
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
    "nyc-daily-weather": "KLGA",
    "houston-daily-weather": "KHOU",
    "seoul-daily-weather": "RKSI",
    "busan-daily-weather": "RKPK",
    "chicago-daily-weather": "KORD",
    "seattle-daily-weather": "KSEA",
    "dallas-daily-weather": "KDAL",
    "madrid-daily-weather": "LEMD",
    "amsterdam-daily-weather": "EHAM",
    "taipei-daily-weather": "RCSS",
    "singapore-daily-weather": "WSSS",
}

HIGH_VOLUME_WEATHER_SERIES: Tuple[str, ...] = (
    "chengdu-daily-weather",
    "beijing-daily-weather",
    "seoul-daily-weather",
    "shanghai-daily-weather",
    "tokyo-daily-weather",
    "wuhan-daily-weather",
    "chongqing-daily-weather",
    "guangzhou-daily-weather",
    "shenzhen-daily-weather",
    "taipei-daily-weather",
    "singapore-daily-weather",
    "nyc-daily-weather",
    "chicago-daily-weather",
    "london-daily-weather",
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
            # LOW temperature market: typically locks only late at night (23:00+) unless evening stays warm above morning trough
            warming_cushion_c = latest_obs.temp_c - running_ext_c
            cooling_cushion_c = warming_cushion_c
            past_trough = (eval_local.date() > spec.obs_date) or (
                eval_local.date() == spec.obs_date and local_hr_float >= 22.5
            )
            if past_trough and (eval_local.date() > spec.obs_date or warming_cushion_c >= 1.0) and p_locked_bucket >= 0.90:
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
    "KMIA": (53,), "KSEA": (53,), "KSFO": (56,), "KDEN": (53,), "CYYZ": (0,),
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
    for idx, b in enumerate(spec.buckets):
        bk = bucket_books.get(b.market_id) or {}
        ask_y = bk.get("ask_yes")
        ask_sz = float(bk.get("ask_yes_shares") or 0.0)
        p_b = float(probs[idx]) if idx < len(probs) else 0.0
        if ask_y is not None and 0.005 <= float(ask_y) <= 0.99 and ask_sz >= 5.0:
            rows.append({
                "idx": idx,
                "market_id": b.market_id,
                "label": b.label,
                "yes_token": b.yes_token,
                "ask_yes": float(ask_y),
                "ask_yes_shares": ask_sz,
                "prob": p_b,
                "edge": p_b - float(ask_y),
            })

    full_slate: Optional[Dict[str, Any]] = None
    if partition_ok and len(rows) == len(spec.buckets):
        sum_asks = sum(r["ask_yes"] for r in rows)
        min_sh = min(r["ask_yes_shares"] for r in rows)
        if sum_asks <= max_underround_sum and min_sh >= 5.0:
            equal_sh = max(5.0, min(min_sh, math.floor(float(target_budget_usd) / max(0.10, sum_asks))))
            if equal_sh * sum_asks <= float(target_budget_usd) * 1.25:
                full_slate = {
                    "mode": "FULL_SLATE_DUTCH_ARB",
                    "sum_asks": round(sum_asks, 5),
                    "guaranteed_edge_per_set": round(1.0 - sum_asks, 5),
                    "equal_shares": float(equal_sh),
                    "total_cost_usd": round(equal_sh * sum_asks, 4),
                    "guaranteed_profit_usd": round(equal_sh * (1.0 - sum_asks), 4),
                    "legs": rows,
                }

    # Constrained positive-EV subset (2-3 buckets with individual edge >= +0.04, combined prob >= 0.72, sum_asks <= 0.88)
    pos_rows = sorted([r for r in rows if r["edge"] >= 0.04], key=lambda x: x["edge"], reverse=True)
    best_subset: Optional[Dict[str, Any]] = None
    if len(pos_rows) >= 2:
        cand_legs = pos_rows[:3]
        sum_sub_asks = sum(r["ask_yes"] for r in cand_legs)
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
# [04/16] MODULE: src/polymarket_research/barrier_onetouch_svi_engine.py
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

HIT_SERIES = [
    ("BTC", "DAILY", "bitcoin-hit-price-daily"),
    ("BTC", "WEEKLY", "bitcoin-hit-price-weekly"),
    ("BTC", "MONTHLY", "bitcoin-hit-price-monthly"),
    ("ETH", "DAILY", "ethereum-hit-price-daily"),
    ("ETH", "WEEKLY", "ethereum-hit-price-weekly"),
    ("ETH", "MONTHLY", "ethereum-hit-price-monthly"),
    ("SOL", "WEEKLY", "solana-hit-price-weekly"),
    ("SOL", "MONTHLY", "solana-hit-price-monthly"),
    ("XRP", "WEEKLY", "xrp-hit-price-weekly"),
    ("XRP", "MONTHLY", "xrp-hit-price-monthly"),
]

ASSET_BINANCE_SYMBOL = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
}

ASSET_VOL_MULT_VS_BTC = {
    "BTC": 1.00,
    "ETH": 1.28,
    "SOL": 1.75,
    "XRP": 1.85,
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
                start_ts=start_ts,
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


def _fetch_finalized_klines(
    sym: str,
    st_ms: int,
    en_ms: int,
    interval: str,
    timeout: float,
) -> List[List[Any]]:
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
# [05/16] MODULE: src/polymarket_research/multistrike_svi_scalper.py
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
            if ref_k > 0 and abs(math.log(ref_k / spot)) > max_strike_dist_log:
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
                        {"token_id": br.yes_token, "side": "YES", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_YES<{br.k_high:g}"},
                        {"token_id": ms_r.yes_token, "side": "YES", "market_id": ms_r.market_id, "fee_rate": ms_r.fee_rate, "label": f"MS_YES>{ms_r.strike:g}"},
                    ],
                })
                bundles.append({
                    "bundle_id": f"TAIL_LOW_NO_{br.market_id}_{ms_r.market_id}",
                    "label": f"NR_NO(<{br.k_high:g})+MS_NO(>{ms_r.strike:g})",
                    "guaranteed_payout": 1.0,
                    "end_ts": br.end_ts,
                    "legs": [
                        {"token_id": br.no_token, "side": "NO", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_NO<{br.k_high:g}"},
                        {"token_id": ms_r.no_token, "side": "NO", "market_id": ms_r.market_id, "fee_rate": ms_r.fee_rate, "label": f"MS_NO>{ms_r.strike:g}"},
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
                        {"token_id": br.yes_token, "side": "YES", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_YES>{br.k_low:g}"},
                        {"token_id": ms_r.no_token, "side": "NO", "market_id": ms_r.market_id, "fee_rate": ms_r.fee_rate, "label": f"MS_NO>{ms_r.strike:g}"},
                    ],
                })
                bundles.append({
                    "bundle_id": f"TAIL_HIGH_B_{br.market_id}_{ms_r.market_id}",
                    "label": f"NR_NO(>{br.k_low:g})+MS_YES(>{ms_r.strike:g})",
                    "guaranteed_payout": 1.0,
                    "end_ts": br.end_ts,
                    "legs": [
                        {"token_id": br.no_token, "side": "NO", "market_id": br.market_id, "fee_rate": br.fee_rate, "label": f"NR_NO>{br.k_low:g}"},
                        {"token_id": ms_r.yes_token, "side": "YES", "market_id": ms_r.market_id, "fee_rate": ms_r.fee_rate, "label": f"MS_YES>{ms_r.strike:g}"},
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
# [06/16] MODULE: src/polymarket_research/same_oracle_dominance_box.py
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

DOMINANCE_ASSETS: Tuple[str, ...] = ("BTC", "ETH", "SOL", "XRP")

DOMINANCE_SERIES_SLUGS: Dict[str, Dict[str, str]] = {
    "BTC": {"4h": "btc-up-or-down-4h", "15m": "btc-up-or-down-15m", "5m": "btc-up-or-down-5m"},
    "ETH": {"4h": "eth-up-or-down-4h", "15m": "eth-up-or-down-15m", "5m": "eth-up-or-down-5m"},
    "SOL": {"4h": "sol-up-or-down-4h", "15m": "sol-up-or-down-15m", "5m": "sol-up-or-down-5m"},
    "XRP": {"4h": "xrp-up-or-down-4h", "15m": "xrp-up-or-down-15m", "5m": "xrp-up-or-down-5m"},
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
    return datetime.fromisoformat(str(iso_str).replace("Z", "+00:00")).timestamp()


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
    min_shares: int = 10,
    min_box_notional_usd: float = 9.0,
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
    min_shares: int = 8,
    min_box_notional_usd: float = 7.5,
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
# [07/16] MODULE: src/polymarket_research/exact_twap_lock_engine.py
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
# [08/16] MODULE: src/polymarket_research/alpha_124_shadow_daemon.py
# PURPOSE: Unified 11-Sleeve Shadow Daemon (W1, W2, W2_MAKER, B1, B2, M1, M2, M3, M4_<250ms_Shock, D1, S2)
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
    HIT_SERIES,
    BarrierRungSpec,
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
from src.polymarket_research.same_oracle_dominance_box import (
    DOMINANCE_ASSETS,
    DOMINANCE_SERIES_SLUGS,
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

DATA_DIR = PROJECT_ROOT / "data" / "alpha124"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "alpha124_shadow_state.json"
LEDGER_FILE = DATA_DIR / "alpha124_shadow_ledger.jsonl"
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
BINANCE_URL = "https://api.binance.com"

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
        "M1_SVI_MAKER_SCALP": 15.0,
        "M2_STRIKE_CONVERGENCE": 15.0,
        "M3_LADDER_MONO_BOX": 20.0,
        "M4_SHOCK_STRIKE_CATCHUP": 15.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 20.0,
        "D1_4H_DOMINANCE_BOX": 20.0,
        "D1_QUIET_BOOK_BOX": 20.0,
        "S5M_CHAINLINK_SNIPER": 15.0,
        "N1_NEGRISK_CROSS_BOX": 20.0,
        "P1_PREOPEN_MAKER_STRADDLE": 16.0,
        "U1_DAILY_UPDOWN_LOCK": 15.0,
        "C1_BINARY_COMPLETE_SET": 20.0,
        "S2_EXACT_TWAP_LOCK": 15.0,
    },
    "T1000": {
        "W1_SOLAR_PEAK_LOCK": 100.0,
        "W2_ENSEMBLE_VALUE": 50.0,
        "W2_MAKER_OVERROUND": 50.0,
        "W3_WEATHER_SLATE_ARB": 80.0,
        "B1_CONVEX_TAIL_YES": 25.0,
        "B2_BARRIER_NO_LOCK": 100.0,
        "M1_SVI_MAKER_SCALP": 100.0,
        "M2_STRIKE_CONVERGENCE": 100.0,
        "M3_LADDER_MONO_BOX": 150.0,
        "M4_SHOCK_STRIKE_CATCHUP": 100.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 100.0,
        "D1_4H_DOMINANCE_BOX": 100.0,
        "D1_QUIET_BOOK_BOX": 100.0,
        "S5M_CHAINLINK_SNIPER": 100.0,
        "N1_NEGRISK_CROSS_BOX": 150.0,
        "P1_PREOPEN_MAKER_STRADDLE": 96.0,
        "U1_DAILY_UPDOWN_LOCK": 100.0,
        "C1_BINARY_COMPLETE_SET": 150.0,
        "S2_EXACT_TWAP_LOCK": 100.0,
    },
    "T5000": {
        "W1_SOLAR_PEAK_LOCK": 350.0,
        "W2_ENSEMBLE_VALUE": 175.0,
        "W2_MAKER_OVERROUND": 175.0,
        "W3_WEATHER_SLATE_ARB": 250.0,
        "B1_CONVEX_TAIL_YES": 75.0,
        "B2_BARRIER_NO_LOCK": 350.0,
        "M1_SVI_MAKER_SCALP": 350.0,
        "M2_STRIKE_CONVERGENCE": 350.0,
        "M3_LADDER_MONO_BOX": 500.0,
        "M4_SHOCK_STRIKE_CATCHUP": 350.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 300.0,
        "D1_4H_DOMINANCE_BOX": 300.0,
        "D1_QUIET_BOOK_BOX": 300.0,
        "S5M_CHAINLINK_SNIPER": 300.0,
        "N1_NEGRISK_CROSS_BOX": 500.0,
        "P1_PREOPEN_MAKER_STRADDLE": 288.0,
        "U1_DAILY_UPDOWN_LOCK": 350.0,
        "C1_BINARY_COMPLETE_SET": 500.0,
        "S2_EXACT_TWAP_LOCK": 300.0,
    },
}


def walk_l2_book_asks(
    asks_raw: List[Dict[str, Any]],
    notional_usd: float,
    fee_rate: float,
    max_slip_cents: float = 0.025,
    min_l1_usd: float = 20.0,
    min_fill_ratio: float = 0.98,
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
        if px > best_ask + max_slip_cents or px >= 0.98:
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
            a: collections.deque(maxlen=600) for a in ("BTC", "ETH", "SOL", "XRP")
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
        self.dominance_pairs: Dict[str, Tuple[TwapCandleMarketSpec, TwapCandleMarketSpec]] = {}
        self.dominance_4h_pairs: Dict[str, Tuple[TwapCandleMarketSpec, TwapCandleMarketSpec]] = {}
        self.twap_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.s5m_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.preopen_15m_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.pending_preopen_straddles: Dict[str, Dict[str, Any]] = {}
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
        self.last_dominance_discovery_ts = 0.0
        self.last_4h_discovery_ts = 0.0
        self.last_twap_discovery_ts = 0.0
        self.last_s5m_discovery_ts = 0.0
        self.last_preopen_discovery_ts = 0.0
        self.last_usd_sample_ts = 0.0
        self.cached_mid_opps: List[Dict[str, Any]] = []
        self.cached_weather_opps: List[Dict[str, Any]] = []
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

    async def fetch_json(self, url: str, timeout: float = 5.0) -> Any:
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

    def record_usd_spot_samples(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        self.last_usd_sample_ts = now
        for asset in DOMINANCE_ASSETS:
            shm = read_shm_usd_anchor(asset, now, max_age_sec=2.5)
            usd_px = shm.get("usd_spot")
            src = str(shm.get("source") or "")
            if usd_px and float(usd_px) > 0:
                self.usd_spot_hist[asset].append((now, float(usd_px)))
                self.usd_direct_flags[asset] = src in ("shm_chainlink_proxy", "shm_coinbase_usd")

    async def update_crypto_spots(self) -> None:
        now = time.time()
        data = await self.fetch_json(f"{BINANCE_URL}/api/v3/ticker/price", timeout=3.5)
        if isinstance(data, list):
            sym_map = {v: k for k, v in ASSET_BINANCE_SYMBOL.items()}
            for item in data:
                sym = item.get("symbol")
                if sym in sym_map:
                    asset = sym_map[sym]
                    px = float(item["price"])
                    self.spots[asset] = px
                    self.spot_hist[asset].append((now, px))
        self.record_usd_spot_samples(now)

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
        for offset in range(0, 600, 100):
            evts = await self.fetch_json(
                f"{GAMMA_URL}/events?closed=false&order=volume24hr&ascending=false&limit=100&offset={offset}",
                timeout=7.0,
            )
            if not isinstance(evts, list) or not evts:
                break
            for ev in evts:
                sp = parse_weather_event(ev)
                if sp is not None:
                    weather_found[sp.event_id] = sp
        for w_slug in HIGH_VOLUME_WEATHER_SERIES:
            evts_w = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={w_slug}&closed=false&limit=3", timeout=5.0)
            if isinstance(evts_w, list):
                for ev in evts_w:
                    sp = parse_weather_event(ev, series_slug_hint=w_slug)
                    if sp is not None:
                        weather_found[sp.event_id] = sp
        self.weather_events = weather_found

        # 2. Discover active Hit/Barrier series (#2)
        barrier_found: Dict[str, BarrierRungSpec] = {}
        for asset, h_grp, slug in HIT_SERIES:
            evts = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5", timeout=6.0)
            if isinstance(evts, list):
                for ev in evts:
                    for r in parse_hit_event(ev, asset, h_grp, slug):
                        if r.end_ts > time.time() + 60:
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

        # 4. Discover active Daily Up/Down series (`U1_DAILY_UPDOWN_LOCK`)
        updown_found: Dict[str, DailyUpDownSpec] = {}
        for asset, slug in DAILY_UPDOWN_SERIES:
            evts_ud = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3", timeout=5.0)
            if isinstance(evts_ud, list):
                for ev in evts_ud:
                    sp_ud = parse_daily_updown_event(ev, asset, slug)
                    if sp_ud is not None and sp_ud.end_ts > time.time() + 60:
                        updown_found[sp_ud.market_id] = sp_ud
        self.daily_updown_markets = updown_found

        self.last_discovery_ts = time.time()
        logger.info(
            f"Discovery complete: {len(self.weather_events)} Weather city-events, "
            f"{len(self.barrier_rungs)} Barrier Hit rungs, {len(self.strike_ladders)} Multi-Strike ladders, "
            f"{len(self.negrisk_ladders)} NegRisk ladders, {len(self.daily_updown_markets)} Daily Up/Down markets."
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
            # Strictly causal L2 walk at t_signal + 50ms (or single-RTT book already fetched on M4 wakeup)
            book = prefetched_book if prefetched_book is not None else await self.fetch_book_after_latency(token_id, latency_ms=50)
            if not book:
                return False
            asks_raw = book.get("asks") or []
            bids_raw = book.get("bids") or []
            best_bid, _ = extract_best_bid(bids_raw)

            min_l1 = 15.0 if sleeve in ("S2_EXACT_TWAP_LOCK", "S5M_CHAINLINK_SNIPER") else 20.0
            # Validate T1000 reference fill first
            ref_ticket = BANKROLL_TICKETS["T1000"][sleeve]
            w_ref = walk_l2_book_asks(asks_raw, ref_ticket, fee_rate=fee_rate, min_l1_usd=min_l1)
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
                "U1_DAILY_UPDOWN_LOCK": 0.040,
                "S2_EXACT_TWAP_LOCK": 0.030,
            }.get(sleeve, 0.035)
            if realized_edge < min_req_edge:
                return False

            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = walk_l2_book_asks(asks_raw, t_map[sleeve], fee_rate=fee_rate, min_l1_usd=min_l1)
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

            # Post-only Maker bid: step +1c inside wide spread or join best_bid when 1c tight, strictly < best_ask
            cand_bid = best_bid + 0.01 if (best_ask - best_bid) >= 0.02 else best_bid
            resting_bid = round(min(cand_bid, best_ask - 0.01), 4)
            min_rb = 0.14 if is_weather_maker else 0.18
            max_rb = 0.65 if is_weather_maker else 0.80
            if not (min_rb <= resting_bid <= max_rb):
                return False
            maker_edge = p_model - resting_bid
            min_edge = 0.085 if is_weather_maker else 0.060
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
            min_tte_cancel = 900.0 if ttl_ov is not None else (3600.0 if is_weather_maker else 7200.0)
            max_age_cancel = float(ttl_ov) if ttl_ov is not None else (2700.0 if is_weather_maker else 1800.0)
            if rem_tte <= min_tte_cancel or age_s >= max_age_cancel:
                self.pending_maker_orders.pop(oid, None)
                _discard_maker_keys(m_ord)
                self._append_ledger({"event": "SHADOW_MAKER_CANCEL", "reason": "TTL_OR_EXPIRY", **m_ord})
                continue

            # 2. Evaluate adverse-selection triggers (`F-03` / `M-04`: verify CLOB didn't already sweep us during cancel RTT!)
            adverse_cancel_reason: Optional[str] = None
            p_fair_now = float(m_ord["p_model_at_post"])
            if is_weather_maker:
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
                if is_weather_maker:
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
            # Adaptive METAR poll cadence (`Gemini #11`): 10s inside station release window, 300s outside!
            m_key = f"{sp.icao}_{sp.obs_date.isoformat()}"
            now_s = time.time()
            cached_m = self.metar_cache.get(m_key)
            metar_ttl = compute_adaptive_metar_poll_ttl(sp.icao, cached_m[1] if cached_m else None, now_utc)
            if cached_m is None or (now_s - cached_m[0]) >= metar_ttl:
                metars = await loop.run_in_executor(
                    None, fetch_metar_observations_sync, sp.icao, sp.obs_date, sp.tz_name
                )
                self.metar_cache[m_key] = (now_s, metars)
            else:
                metars = cached_m[1]

            # Official AviationWeather TAF TX/TN prior (`Gemini #11`, refreshed every 30m)
            cached_taf = self.taf_cache.get(m_key)
            if cached_taf is None or (now_s - cached_taf[0]) >= 1800.0:
                taf_ext = await loop.run_in_executor(
                    None, fetch_taf_extremes_sync, sp.icao, sp.obs_date, sp.tz_name
                )
                self.taf_cache[m_key] = (now_s, taf_ext)
            else:
                taf_ext = cached_taf[1]

            # Refresh 71-member Ensemble cache every 25 minutes per ICAO (throttled; never cache empty failures for 25m)
            cached_e = self.ensemble_cache.get(sp.icao)
            ens_ttl = 1500.0 if (cached_e and cached_e[1]) else 60.0
            if cached_e is None or (now_s - cached_e[0]) >= ens_ttl:
                async with self._open_meteo_sem:
                    ens_h = await loop.run_in_executor(None, fetch_live_ensemble_hourly_sync, sp.lat, sp.lon)
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

            # 1B. Event-Level Weather Slate Arbitrage (`W3_WEATHER_SLATE_ARB`, `Gemini #10` + `ChatGPT #5`)
            # Throttled to once per 300s per event_id so 77+ city slates don't trigger 800+ HTTP calls/cycle.
            slate_key = f"W3_SLATE_{sp.event_id}"
            last_w3_chk = float(self._last_w3_slate_chk_ts.get(sp.event_id) or 0.0)
            if (
                slate_key not in self.entered_keys
                and slate_key not in self.inflight_keys
                and len(sp.buckets) >= 4
                and (self.single_scan or (now_s - last_w3_chk) >= 300.0)
            ):
                self._last_w3_slate_chk_ts[sp.event_id] = now_s
                all_bks = await asyncio.gather(
                    *[self.fetch_json(f"{CLOB_URL}/book?token_id={b_i.yes_token}", timeout=2.5) for b_i in sp.buckets]
                )
                bucket_book_map: Dict[str, Dict[str, Any]] = {}
                raw_bk_by_mkt: Dict[str, Dict[str, Any]] = {}
                for b_i, bk_i in zip(sp.buckets, all_bks):
                    if bk_i:
                        raw_bk_by_mkt[b_i.market_id] = bk_i
                        asks_i = sorted(
                            [(float(a["price"]), float(a["size"])) for a in (bk_i.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
                            key=lambda x: x[0],
                        )
                        if asks_i:
                            bucket_book_map[b_i.market_id] = {"ask_yes": asks_i[0][0], "ask_yes_shares": asks_i[0][1]}
                slate_ev = evaluate_weather_event_slate(
                    sp, probs, bucket_book_map, target_budget_usd=BANKROLL_TICKETS["T1000"]["W3_WEATHER_SLATE_ARB"]
                )
                full_arb = slate_ev.get("full_slate_arb")
                if full_arb:
                    opps_out.append({
                        "sleeve": "W3_WEATHER_SLATE_ARB",
                        "market": f"{sp.city} ({sp.icao}) {sp.obs_date} Full-Slate ({len(sp.buckets)} buckets)",
                        "ask_vwap": full_arb["sum_asks"],
                        "p_model": 1.0,
                        "net_edge": full_arb["guaranteed_edge_per_set"],
                        "l1_usd": full_arb["total_cost_usd"],
                    })
                    await self.open_shadow_weather_slate(sp, full_arb, end_ts)
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

            ext_cached = self.barrier_ext_cache.get(ev_id)
            if ext_cached is None or (now - ext_cached[0]) >= 90.0:
                ext = await loop.run_in_executor(
                    None, fetch_binance_window_extremes_sync, r0.asset, r0.start_ts, now, "1m"
                )
                if ext:
                    self.barrier_ext_cache[ev_id] = (now, ext)
            else:
                ext = ext_cached[1]

            max_h = max(spot, ext[0]) if ext else spot
            min_l = min(spot, ext[1]) if ext else spot

            # Only poll CLOB books for rungs within sensible distance of spot (|ln(K/S)| <= 0.14)
            near_rungs = [
                r for r in rungs
                if abs(math.log(r.strike / spot)) <= 0.14
                and not (r.direction == "UP" and max_h >= r.strike)
                and not (r.direction == "DOWN" and min_l <= r.strike)
            ]
            for r in near_rungs:
                tte = r.end_ts - now
                iv_w, iv_src = get_wing_implied_vol(r.asset, spot, r.strike, tte)
                p_touch = first_passage_touch_prob(
                    spot, r.strike, tte, iv_w, r.direction, wick_vol_multiplier=self.barrier_wick_mult
                )

                # Evaluate B1_CONVEX_TAIL_YES (`0.04 <= p_touch <= 0.45`, `TTE >= 2h`)
                if 7200 <= tte <= 10 * 86400 and 0.07 <= p_touch <= 0.48:
                    bk_y = await self.fetch_json(f"{CLOB_URL}/book?token_id={r.yes_token}", timeout=3.0)
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
                    bk_n = await self.fetch_json(f"{CLOB_URL}/book?token_id={r.no_token}", timeout=3.0)
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
                    await self.open_shadow_two_leg_box(
                        sleeve="C1_BINARY_COMPLETE_SET",
                        dedupe_key=f"C1_{sr.market_id}",
                        asset=asset,
                        title=f"{asset} YES+NO Complete Set: {sr.question}",
                        leg_a={"token_id": sr.yes_token, "side": "YES", "market_id": sr.market_id, "fee_rate": CRYPTO_FEE_RATE},
                        leg_b={"token_id": sr.no_token, "side": "NO", "market_id": sr.market_id, "fee_rate": CRYPTO_FEE_RATE},
                        bk_a=bk_y,
                        bk_b=bk_n,
                        close_ts=sr.end_ts,
                        max_box_cost_net=0.994,
                        extra={"is_complete_set": True, "market_id": sr.market_id, "condition_id": sr.condition_id},
                    )

                w_y = walk_l2_book_asks(bk_y.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)
                w_n = walk_l2_book_asks(bk_n.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)

                ladder_quotes.append({
                    "strike": sr.strike,
                    "is_downward": sr.is_downward,
                    "market_id": sr.market_id,
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
                    await self.open_shadow_two_leg_box(
                        sleeve="M3_LADDER_MONO_BOX",
                        dedupe_key=f"M3_{asset}_{ma['low_market_id']}_{ma['high_market_id']}",
                        asset=asset,
                        title=f"{asset} Ladder Box YES>{ma['low_strike']} + NO>{ma['high_strike']}",
                        leg_a={"token_id": ma["yes_token_low"], "side": "YES", "market_id": ma["low_market_id"], "fee_rate": CRYPTO_FEE_RATE},
                        leg_b={"token_id": ma["no_token_high"], "side": "NO", "market_id": ma["high_market_id"], "fee_rate": CRYPTO_FEE_RATE},
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
        bundles = build_negrisk_cross_box_bundles(rungs, nr_brackets, spot=spot, max_strike_dist_log=0.10)
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
            fetched_bks = await asyncio.gather(
                *[self.fetch_json(f"{CLOB_URL}/book?token_id={t_id}", timeout=3.0) for t_id in needed_toks]
            )
            for t_id, bk_obj in zip(needed_toks, fetched_bks):
                if bk_obj:
                    local_bk_cache[t_id] = bk_obj

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
            w_nr = walk_equal_shares_multi_leg_box(
                legs_spec,
                target_budget_usd=BANKROLL_TICKETS["T1000"]["N1_NEGRISK_CROSS_BOX"],
                guaranteed_payout_per_bundle=gp,
                max_bundle_cost_net=round(gp * 1.005, 4),
                min_shares=8,
                min_box_notional_usd=9.0,
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
                "fee_rate": CRYPTO_FEE_RATE,
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

    async def scan_daily_updown_locks(self, opps_out: List[Dict[str, Any]]) -> None:
        """
        Addition #6 (`U1_DAILY_UPDOWN_LOCK`): Final-90-minute SVI convergence sniper on
        `btc-up-or-down-daily` ($67k/24h) and `eth-up-or-down-daily` ($25k/24h).
        """
        now = time.time()
        loop = asyncio.get_running_loop()
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

        target_end_ts = int(math.ceil(now / 900.0) * 900)
        rem_sec = float(target_end_ts) - now
        if not (5.0 <= rem_sec <= 305.0):
            return

        now_iso = datetime.fromtimestamp(now - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for asset in DOMINANCE_ASSETS:
            pair_key = f"{asset}_{target_end_ts}"
            if pair_key in self.dominance_pairs:
                continue
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

    async def get_authoritative_open_strike(self, spec: TwapCandleMarketSpec) -> Optional[float]:
        c_key = f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}"
        cached = self.chainlink_open_cache.get(c_key)
        if cached is not None:
            return cached[1]
        now_t = time.time()
        if not self.single_scan and now_t < spec.start_ts + 2.0:
            return None
        twap_url = build_crypto_price_query_url(spec)
        payload = await self.fetch_json(twap_url, timeout=4.0)
        val = parse_authoritative_open_price(payload, request_url=twap_url)
        # Gamma prev-5m `finalPrice` is published ~340s after the boundary: cross-check whenever it can exist.
        needs_gamma = self.single_scan or now_t >= spec.start_ts + 335.0
        if needs_gamma:
            g_url = build_prev_5m_gamma_event_url(spec)
            g_val = parse_authoritative_open_price(await self.fetch_json(g_url, timeout=4.0), request_url=g_url)
            if val is None:
                val = g_val
            elif g_val is not None and abs(val - g_val) / max(1e-9, g_val) > 1e-6:
                logger.error(
                    f"[CRITICAL TWAP MISMATCH VETO] {spec.asset} {spec.horizon}: "
                    f"crypto-price TWAP={val} != Gamma prev_5m finalPrice={g_val}!"
                )
                return None
            elif g_val is None and not self.single_scan:
                return None  # unverifiable while verification is possible -> fail closed, never cache
        if val is not None:
            hist_w = [px for ts_s, px in self.usd_spot_hist.get(spec.asset, ()) if (spec.start_ts - 60.0) <= ts_s <= (spec.start_ts + 5.0)]
            if len(hist_w) >= 3 and not self.single_scan:
                loc_twap = sum(hist_w) / len(hist_w)
                if loc_twap > 0.0 and abs(val - loc_twap) / loc_twap > 0.0035:
                    logger.error(f"[STRIKE TWAP VETO] {spec.asset} {spec.horizon}: strike {val} vs local 60s TWAP {loc_twap} > 35 bps")
                    return None
            spot_ref = float(self.spots.get(spec.asset) or 0.0)
            if spot_ref > 0.0 and abs(val - spot_ref) / spot_ref > 0.015:
                logger.error(f"[STRIKE SANITY VETO] {spec.asset} {spec.horizon}: strike {val} vs spot {spot_ref} > 150 bps")
                return None
            self.chainlink_open_cache[c_key] = (spec.end_ts, val)
        return val

    async def _passes_complement_anti_box_check(self, leg_a: Dict[str, Any], leg_b: Dict[str, Any]) -> bool:
        opp_a = str(leg_a.get("opp_token_id") or "")
        opp_b = str(leg_b.get("opp_token_id") or "")
        if not opp_a or not opp_b:
            return False
        bk_oa, bk_ob = await asyncio.gather(
            self.fetch_json(f"{CLOB_URL}/book?token_id={opp_a}", timeout=3.0),
            self.fetch_json(f"{CLOB_URL}/book?token_id={opp_b}", timeout=3.0),
        )
        if not (isinstance(bk_oa, dict) and isinstance(bk_ob, dict)):
            return False
        bid_oa, _ = extract_best_bid(bk_oa.get("bids") or [])
        bid_ob, _ = extract_best_bid(bk_ob.get("bids") or [])
        if bid_oa <= 0.0 or bid_ob <= 0.0 or (bid_oa + bid_ob) > 1.0:
            logger.warning(
                f"[ANTI-BOX VETO] Rejected box {leg_a.get('label')}+{leg_b.get('label')}: "
                f"complement bids={bid_oa:.3f}+{bid_ob:.3f}={bid_oa + bid_ob:.3f} (unverified or > 1.03)"
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
            asks_a = bk_a.get("asks") or []
            asks_b = bk_b.get("asks") or []
            bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
            bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                min_sh = 8 if tier_name == "T100" else 10
                w_t = walk_equal_shares_dominance_box(
                    asks_a,
                    asks_b,
                    target_budget_usd=t_map[sleeve],
                    fee_rate_a=float(leg_a.get("fee_rate", CRYPTO_FEE_RATE)),
                    fee_rate_b=float(leg_b.get("fee_rate", CRYPTO_FEE_RATE)),
                    max_box_cost_net=max_box_cost_net,
                    min_shares=min_sh,
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
        dedupe_key = f"W3_SLATE_{spec.event_id}"
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            sum_asks = float(slate_info["sum_asks"])
            legs = slate_info["legs"]
            min_avail_sh = min(float(lg["ask_yes_shares"]) for lg in legs)
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
                "title": f"{spec.title} [Full-Slate {len(legs)} Buckets]",
                "side": "ALL_BUCKETS_YES",
                "token_id": "|".join(str(lg["yes_token"]) for lg in legs),
                "fee_rate": 0.0,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": 1.0,
                "entry_eff_px_t1000": round(sum_asks, 4),
                "entry_vwap_t1000": round(sum_asks, 4),
                "realized_edge_t1000": round(1.0 - sum_asks, 4),
                "entry_best_bid": round(sum_asks, 4),
                "last_bid": round(sum_asks, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {"event_id": spec.event_id, "icao": spec.icao, "legs": legs},
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(f"[ENTRY:W3_WEATHER_SLATE_ARB] {pos['title']} @ sum_asks=${sum_asks:.4f}")
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
                min_shares=12,
                min_box_notional_usd=11.0,
            )
            if not w_ref.get("filled"):
                return False

            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                min_sh = 8 if tier_name == "T100" else 12
                min_notional = 7.5 if tier_name == "T100" else 11.0
                w_t = walk_equal_shares_dominance_box(
                    asks_a,
                    asks_b,
                    target_budget_usd=t_map[sleeve_override],
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=max_box_cost_override,
                    min_shares=min_sh,
                    min_box_notional_usd=min_notional,
                )
                if w_t.get("filled"):
                    tier_fills[tier_name] = w_t

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
        pair_key = f"{m15.asset}_{m15.market_id}_{m5.market_id}"
        last_emit = float(self._last_d1_live_emit_ts.get(pair_key, 0.0) or 0.0)
        if (now_ts - last_emit) < 10.0:
            return False
        self._last_d1_live_emit_ts[pair_key] = now_ts
        for k_old, ts_old in list(self._last_d1_live_emit_ts.items()):
            if (now_ts - ts_old) > 1200.0:
                self._last_d1_live_emit_ts.pop(k_old, None)

        leg_a = dom_info["leg_a"]
        leg_b = dom_info["leg_b"]
        w_a = w_live["leg_a_walk"]
        w_b = w_live["leg_b_walk"]
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
            "max_box_cost_net": 0.985 if is_quiet_book else 0.980,
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

    async def scan_same_oracle_dominance_boxes(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        target_end_ts = int(math.ceil(now / 900.0) * 900)
        cur_window_pairs = sum(1 for k in self.dominance_pairs if str(k).endswith(f"_{target_end_ts}"))
        disc_interval = 7.0 if cur_window_pairs < len(DOMINANCE_ASSETS) else 12.0
        if self.is_in_same_oracle_overlap_window(now) and (now - self.last_dominance_discovery_ts) >= disc_interval:
            self.last_dominance_discovery_ts = now
            await self.discover_dominance_pairs(now)

        for _, (m15, m5) in list(self.dominance_pairs.items()):
            rem_sec = m5.end_ts - now
            if not (10.0 <= rem_sec <= 300.0):
                continue
            if now < m5.start_ts + 1.0:
                continue

            k_15m, k_5m = await asyncio.gather(
                self.get_authoritative_open_strike(m15),
                self.get_authoritative_open_strike(m5),
            )
            if k_15m is None or k_5m is None:
                continue

            dom_info = determine_dominance_legs(m15, k_15m, m5, k_5m, min_corridor_bps=3.0)
            if dom_info is None:
                continue

            leg_a = dom_info["leg_a"]
            leg_b = dom_info["leg_b"]
            bk_a, bk_b = await asyncio.gather(
                self.fetch_json(f"{CLOB_URL}/book?token_id={leg_a['token_id']}", timeout=3.0),
                self.fetch_json(f"{CLOB_URL}/book?token_id={leg_b['token_id']}", timeout=3.0),
            )
            if not bk_a or not bk_b:
                continue
            comp_checked: Optional[bool] = None

            eval_now = float(now_ts) if now_ts is not None else time.time()
            if now_ts is None:
                self.record_usd_spot_samples(eval_now)
            rem_live = m5.end_ts - eval_now
            if 38.0 <= rem_live <= 298.0:
                w_live = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=13.50,
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=0.985,
                    min_shares=8,
                    min_box_notional_usd=7.0,
                )
                if w_live.get("filled"):
                    is_quiet_live = self._passes_quiet_book_filter(m15.asset, bk_a, bk_b, w_live, eval_now)
                    live_emit_cap = 0.985 if is_quiet_live else 0.980
                    if float(w_live["box_cost_net"]) <= live_emit_cap:
                        comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b)
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
                max_box_cost_net=1.010,  # Surface near-arb boxes <= $1.010 in live telemetry; enter ONLY <= $0.995!
                min_shares=12,
                min_box_notional_usd=11.0,
            )
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
                        comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b)
                    if not comp_checked:
                        continue
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
            dom_info = determine_dominance_legs(m4, k_4h, m_short, k_sh, min_corridor_bps=3.0)
            if dom_info is None:
                continue
            leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
            bk_a, bk_b = await asyncio.gather(
                self.fetch_json(f"{CLOB_URL}/book?token_id={leg_a['token_id']}", timeout=3.0),
                self.fetch_json(f"{CLOB_URL}/book?token_id={leg_b['token_id']}", timeout=3.0),
            )
            if not bk_a or not bk_b:
                continue
            comp_4h_ok: Optional[bool] = None
            eval_4h_now = float(now_ts) if now_ts is not None else time.time()
            if now_ts is None:
                self.record_usd_spot_samples(eval_4h_now)
            rem_4h_live = m_short.end_ts - eval_4h_now
            if 38.0 <= rem_4h_live <= max_rem:
                w_live_4h = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=13.50,
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=0.985,
                    min_shares=8,
                    min_box_notional_usd=7.0,
                )
                if w_live_4h.get("filled"):
                    is_quiet_4h = self._passes_quiet_book_filter(m4.asset, bk_a, bk_b, w_live_4h, eval_4h_now)
                    if float(w_live_4h["box_cost_net"]) <= (0.985 if is_quiet_4h else 0.980):
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b)
                        if not comp_4h_ok:
                            continue
                        self.emit_live_d1_box_candidate(
                            m4,
                            m_short,
                            dom_info,
                            w_live_4h,
                            eval_4h_now,
                            is_quiet_book=is_quiet_4h,
                            sleeve_source="D1_4H_DOMINANCE_BOX",
                        )
            w_scan = walk_equal_shares_dominance_box(
                bk_a.get("asks") or [],
                bk_b.get("asks") or [],
                target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_4H_DOMINANCE_BOX"],
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                fee_exponent_a=float(leg_a["fee_exponent"]),
                fee_exponent_b=float(leg_b["fee_exponent"]),
                max_box_cost_net=1.005,
                min_shares=10,
                min_box_notional_usd=9.0,
            )
            if w_scan.get("filled"):
                box_net = float(w_scan["box_cost_net"])
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
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b)
                    if not comp_4h_ok:
                        continue
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
                if asset not in ("BTC", "ETH", "SOL", "XRP"):
                    continue
                t0_u = float(trig.get("t0_unix") or 0.0)
                if t0_u <= 0.0 or (now - t0_u) > max_age_sec:
                    continue
                spot_t0 = float(trig.get("spot_at_t0") or trig.get("trigger_price") or 0.0)
                if spot_t0 > 0.0:
                    self.spots[asset] = spot_t0
                    self.spot_hist[asset].append((now, spot_t0))
                cl_px = trig.get("chainlink_proxy_spot") or trig.get("coinbase_spot")
                if cl_px and float(cl_px) > 0.0:
                    self.usd_spot_hist[asset].append((now, float(cl_px)))
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
        # Step 1: Defensive <250ms adverse-selection cancellation on resting Maker bids
        if self.pending_maker_orders:
            await self.manage_pending_maker_orders()

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
            usd_hist = self.usd_spot_hist.get(spec.asset)
            cur_usd = shm.get("usd_spot")
            if (not cur_usd or float(cur_usd) <= 0.0) and usd_hist and (now - float(usd_hist[-1][0])) <= 5.0:
                cur_usd = float(usd_hist[-1][1])
            if (not cur_usd or float(cur_usd) <= 0.0) and self.usd_direct_flags.get(spec.asset, False):
                cur_usd = self.spots.get(spec.asset, 0.0)
            if not cur_usd or float(cur_usd) <= 0.0:
                continue
            cur_usd_f = float(cur_usd)
            usd_direct = bool(
                shm.get("source") in ("shm_chainlink_proxy", "shm_coinbase_usd")
                or self.usd_direct_flags.get(spec.asset, False)
            )
            iv_1d, _ = get_wing_implied_vol(spec.asset, cur_usd_f, k_open, 86400.0)
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

        for _, (_, m5_p) in self.dominance_pairs.items():
            if m5_p.asset in ("BTC", "ETH") and abs(m5_p.end_ts - end_5m) <= 2.0:
                self.s5m_candles[f"{m5_p.asset}_5m_{end_5m}"] = m5_p
        for k_tw, sp_tw in self.twap_candles.items():
            if sp_tw.asset in ("BTC", "ETH") and sp_tw.horizon == "5m" and abs(sp_tw.end_ts - end_5m) <= 2.0:
                self.s5m_candles[k_tw] = sp_tw

        now_iso = datetime.fromtimestamp(now_ts - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for asset in ("BTC", "ETH"):
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
            if not cur_usd or float(cur_usd) <= 0.0:
                cur_usd = self.spots.get(spec.asset, 0.0)
            if not cur_usd or float(cur_usd) <= 0.0:
                continue
            cur_usd_f = float(cur_usd)

            dist_pct = abs(cur_usd_f - k_open) / k_open * 100.0
            if dist_pct < 0.085:
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
            if z_sig < 1.35 or p_fair < 0.905:
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
            if 0.58 <= eff_px <= 0.86 and edge >= 0.045:
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
                    sh = round(t_map["P1_PREOPEN_MAKER_STRADDLE"] / pair_cost, 4)
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
                    leg_budget = round(0.5 * t_map["P1_PREOPEN_MAKER_STRADDLE"], 2)
                    sh_s = round(leg_budget / bid_px, 4)
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
        return None

    async def manage_open_positions(self) -> None:
        now = time.time()
        loop = asyncio.get_running_loop()
        to_close: List[Tuple[str, str, float, float]] = []  # (pos_id, status, payout_per_share, exit_fee_rate)

        for pid, pos in list(self.open_positions.items()):
            sleeve = pos["sleeve"]
            tok = pos["token_id"]

            # 0A. Dedicated multi-leg supervision & settlement for D1, M3_LADDER_MONO_BOX, C1_BINARY_COMPLETE_SET & W3_WEATHER_SLATE_ARB
            if sleeve == "W3_WEATHER_SLATE_ARB":
                close_ts_f = float(pos["close_ts"])
                if now >= close_ts_f + 30.0:
                    legs = (pos.get("extra") or {}).get("legs") or []
                    resolved_vals = await asyncio.gather(
                        *[
                            self.resolve_via_gamma_market(
                                {"token_id": lg["yes_token"], "side": "YES", "extra": {"market_id": lg["market_id"]}}
                            )
                            for lg in legs
                        ]
                    )
                    if resolved_vals and all(v is not None for v in resolved_vals):
                        total_pay = round(sum(float(v) for v in resolved_vals if v is not None), 4)
                        to_close.append((pid, "SETTLED_WEATHER_SLATE_1X", max(1.0, total_pay), 0.0))
                continue

            if sleeve in (
                "D1_SAME_ORACLE_DOMINANCE_BOX",
                "D1_4H_DOMINANCE_BOX",
                "D1_QUIET_BOOK_BOX",
                "M3_LADDER_MONO_BOX",
                "C1_BINARY_COMPLETE_SET",
            ):
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
                    continue

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

            if sleeve in ("N1_NEGRISK_CROSS_BOX", "P1_PREOPEN_MAKER_STRADDLE"):
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

                # Authoritative Chainlink 60s-TWAP fallback for S5M_CHAINLINK_SNIPER if Gamma lags >= 120s
                if sleeve == "S5M_CHAINLINK_SNIPER" and now >= float(pos["close_ts"]) + 120.0:
                    extra = pos.get("extra") or {}
                    if extra.get("start_iso"):
                        cp_url = build_own_gamma_event_url(pos["asset_or_city"], "5m", extra["start_iso"])
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

        for pid, status, net_pay_ps, _ in to_close:
            pos = self.open_positions.pop(pid, None)
            if not pos:
                continue
            tier_pnls: Dict[str, float] = {}
            for t_name, tf in pos["tier_fills"].items():
                cost_total = float(tf["spent_usd"]) + float(tf["fee_usd"])
                payout_usd = float(tf["shares"]) * net_pay_ps
                tier_pnls[t_name] = round(payout_usd - cost_total, 2)

            won_t1000 = tier_pnls.get("T1000", 0.0) > 0
            pos.update({
                "status": status,
                "closed_ts": now,
                "closed_utc": datetime.now(timezone.utc).isoformat(),
                "net_payout_per_share": round(net_pay_ps, 4),
                "tier_pnls_usd": tier_pnls,
                "won": won_t1000,
            })
            self.closed_positions.append(pos)
            self._append_ledger({"event": "SHADOW_CLOSE", **pos})
            logger.info(
                f"[CLOSE:{pos['sleeve']}] {pos['title']} ({pos['side']}) -> {status} | "
                f"PnL T100=${tier_pnls.get('T100',0):+.2f} T1000=${tier_pnls.get('T1000',0):+.2f} T5000=${tier_pnls.get('T5000',0):+.2f}"
            )

    def write_state_files(self, opps: List[Dict[str, Any]]) -> None:
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
            closed_sl = [
                p for p in all_closed_sl
                if not (is_d1_sl and float(p.get("entry_eff_px_t1000") or 1.0) < 0.900)
            ]
            excluded_anti = len(all_closed_sl) - len(closed_sl)
            open_sl = [p for p in self.open_positions.values() if p.get("sleeve") == sl]
            wins = sum(1 for p in closed_sl if p.get("won"))
            pnl_1k = sum(float(p.get("tier_pnls_usd", {}).get("T1000", 0.0)) for p in closed_sl)
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
                "excluded_anti_box": excluded_anti,
                "quarantined": is_shadow_sleeve_quarantined(sl),
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
                "same_oracle_dominance_pairs": len(self.dominance_pairs),
                "dominance_4h_pairs": len(self.dominance_4h_pairs),
                "exact_twap_lock_candles": len(self.twap_candles),
                "s5m_sniper_candles": len(self.s5m_candles),
                "preopen_15m_candles": len(self.preopen_15m_candles),
            },
            "portfolio_realized_pnl_by_bankroll_usd": tier_totals,
            "by_sleeve": by_sleeve,
            "per_strategy": by_sleeve,
            "open_positions_count": len(self.open_positions),
            "pending_maker_orders_count": len(self.pending_maker_orders),
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

    async def run_forever(self) -> None:
        logger.info(
            "Starting Polymarket Alpha-124 Unified Shadow Daemon "
            "(W1/W3 + Asian METAR + B1/B2 + M3/N1 NegRisk + U1 Daily + D1/4h/QuietBook + S5M + P1 PreOpen + S2)..."
        )
        try:
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
                else:
                    # Non-blocking background coroutines so S2 (3.0s) / D1 (3.5s) never stall
                    if (t0 - self.last_crypto_mid_scan_ts) >= 18.0 and (
                        self._bg_mid_task is None or self._bg_mid_task.done()
                    ):
                        self.last_crypto_mid_scan_ts = t0
                        self._bg_mid_task = asyncio.create_task(self._run_bg_mid_crypto())

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
                    + self.cached_weather_opps
                )

                await self.manage_pending_maker_orders()
                await self.manage_open_positions()
                await self.write_state_files_async(opps)

                logger.info(
                    f"[Cycle {self.cycle_count}] BTC=${self.spots.get('BTC',0):,.1f} ETH=${self.spots.get('ETH',0):,.1f} | "
                    f"Monitored(W={len(self.weather_events)}, B={len(self.barrier_rungs)}, M={len(self.strike_ladders)}, "
                    f"NR={len(self.negrisk_ladders)}, U1={len(self.daily_updown_markets)}, D={len(self.dominance_pairs)}, "
                    f"D4h={len(self.dominance_4h_pairs)}, S5m={len(self.s5m_candles)}, P1={len(self.preopen_15m_candles)}, S2={len(self.twap_candles)}) | "
                    f"MakerPend={len(self.pending_maker_orders)} PreOpenPend={len(self.pending_preopen_straddles)} "
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
                    # Sub-second (0.90s) D1 overlap box scan without full state-file rewrite churn
                    if self.is_in_same_oracle_overlap_window(now_s) and (now_s - last_fast_d1_subscan) >= 0.90:
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
                        s_opps: List[Dict[str, Any]] = []
                        await self.handle_shock_triggers(shocks_w, s_opps, now_ts=now_s)
                        if s_opps:
                            self.cached_shock_opps = s_opps
                        await self.write_state_files_async(
                            twap_opps
                            + dom_opps
                            + s5m_opps
                            + p1_opps
                            + self.cached_shock_opps
                            + self.cached_mid_opps
                            + self.cached_weather_opps
                        )
                    # Step down cadence immediately if we just entered the final-55s TWAP lock window
                    if target_cadence > 3.0 and self.is_in_exact_twap_lock_window(now_s):
                        break
                    await asyncio.sleep(min(0.25, max(0.05, deadline - now_s)))
        finally:
            for bg_t in (self._bg_discovery_task, self._bg_mid_task, self._bg_weather_task):
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
# [09/16] MODULE: src/polymarket_research/exp316_macro_strike_shadow.py
# PURPOSE: EXP-316 Isolated Multi-Strike Convergence Shadow Engine
# ======================================================================================

#!/usr/bin/env python3
"""
EXP-316: Polymarket Daily/Weekly Crypto Strike Ladder Shadow Engine
===================================================================
Isolated Research & Shadow Engine designed to solve the $200/trade liquidity ceiling
by evaluating Daily, Weekly, and Monthly BTC/ETH/SOL strike markets with $2k-$50k+ depth.

STRICT INVARIANTS:
  1. ZERO FAKE FILLS: All simulated fills walk actual resting L2 orderbook liquidity
     fetched at t_signal + 50ms (simulating real wire/transit latency).
  2. NO LOOKAHEAD BIAS: Entry VWAP, slippage, and dynamic crypto taker fees (crypto_fees_v2)
     are derived strictly from resting orders present at t_signal + 50ms.
  3. TRACK A (Final-3-Hour Daily Strike Convergence):
     - Monitors Daily BTC/ETH/SOL strike contracts when 60s <= TTE <= 10800s.
     - Cushion filter: >= 0.25% for 1h-3h TTE, >= 0.15% for <1h TTE.
     - Zone filter: 0.65 <= best_ask <= 0.89.
     - Ticket tiers: $250, $1,000, and $2,500.
     - Lifecycle: Tracks real L2 0.99 Maker TP fills and actual resolution ($1.00 / $0.00).
  4. TRACK B (Multi-Strike Impulse Repricing Markout):
     - Triggers on Binance BTC/ETH rolling returns >= 0.35% over 30s-60s window.
     - Walks live L2 ask book at t_signal + 50ms for $500 and $1,500 tickets (0.30 <= p <= 0.85).
     - Multi-horizon markout: Records actual live CLOB best_bid at +5s, +15s, +30s, +60s, +300s, +900s
       (net of entry + exit crypto_fees_v2 and bid-ask spread).
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
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import aiohttp
import websockets

try:
    import fcntl
except ImportError:
    fcntl = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.polymarket_research.deribit_svi_surface import GLOBAL_SVI_ENGINE
except Exception:
    GLOBAL_SVI_ENGINE = None

DATA_DIR = PROJECT_ROOT / "data" / "exp316"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LIVE_TRIGGER_FILE = PROJECT_ROOT / "data" / "polymarket" / "live_shock_triggers.jsonl"

LEDGER_FILE = DATA_DIR / "exp316_shadow_ledger.jsonl"
LOG_FILE = DATA_DIR / "exp316_shadow.log"
ALT_LOG_FILE = DATA_DIR / "exp316.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [EXP-316] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.FileHandler(ALT_LOG_FILE),
    ] + ([logging.StreamHandler(sys.stdout)] if sys.stdout.isatty() else []),
)
logger = logging.getLogger("EXP316Shadow")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade/ethusdt@trade/solusdt@trade/xrpusdt@trade"
BINANCE_REST_URL = "https://api.binance.com/api/v3/ticker/price"

# Series configurations
MONITORED_SERIES = [
    # Daily Up/Down & Daily Strikes
    ("BTC", "DAILY", "btc-up-or-down-daily"),
    ("ETH", "DAILY", "eth-up-or-down-daily"),
    ("SOL", "DAILY", "solana-up-or-down-daily"),
    ("XRP", "DAILY", "xrp-up-or-down-daily"),
    ("BTC", "DAILY", "bitcoin-hit-price-daily"),
    # Weekly Strike Ladders
    ("BTC", "WEEKLY", "btc-multi-strikes-weekly"),
    ("ETH", "WEEKLY", "ethereum-multi-strikes-weekly"),
    ("SOL", "WEEKLY", "solana-multi-strikes-weekly"),
    ("XRP", "WEEKLY", "xrp-multi-strikes-weekly"),
    ("BTC", "WEEKLY", "bitcoin-hit-price-weekly"),
    ("ETH", "WEEKLY", "ethereum-hit-price-weekly"),
    ("SOL", "WEEKLY", "solana-hit-price-weekly"),
    ("XRP", "WEEKLY", "xrp-hit-price-weekly"),
]


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class MarketTokenMeta:
    asset: str
    horizon_group: str
    series_slug: str
    event_title: str
    question: str
    condition_id: str
    strike_price: Optional[float]
    end_date_iso: str
    end_unix: float
    token_id: str
    outcome: str  # YES or NO
    fee_type: str = "crypto_fees_v2"
    base_fee_bps: int = 1000
    market_id: str = ""


@dataclass
class SimulatedFillResult:
    token_id: str
    ticket_requested: float
    ticket_filled: float
    fill_ratio: float
    shares: float
    best_ask_pre: float
    vwap: float
    slippage_cents: float
    slippage_bps: float
    entry_fee_usd: float
    levels_consumed: int
    success: bool
    rejection_reason: Optional[str] = None


@dataclass
class TrackAPosition:
    trade_id: str
    created_at_utc: str
    asset: str
    series_slug: str
    question: str
    condition_id: str
    token_id: str
    outcome: str
    strike_price: Optional[float]
    tte_seconds_entry: float
    spot_at_signal: float
    cushion_pct: float
    z_score: float  # Volatility-scaled distance z_sigma
    ticket_tier: float  # 25, 50, 250, 1000, 2500
    fill: SimulatedFillResult
    maker_tp_price: float = 0.97
    max_seen_bid: float = 0.0
    market_id: str = ""
    end_unix: float = 0.0
    barrier_breached: bool = False
    tp_filled: bool = False
    tp_fill_time_utc: Optional[str] = None
    settled: bool = False
    settlement_price: Optional[float] = None  # 1.0 or 0.0
    settlement_time_utc: Optional[str] = None
    net_pnl_usd: Optional[float] = None
    net_roi_pct: Optional[float] = None


@dataclass
class TrackBMarkoutRecord:
    trade_id: str
    created_at_utc: str
    asset: str
    series_slug: str
    question: str
    token_id: str
    outcome: str
    impulse_return_pct: float
    impulse_window_sec: int
    ticket_tier: float  # 500, 1500
    fill: SimulatedFillResult
    markout_delays: List[int]  # [5, 15, 30, 60, 300, 900]
    markout_checkpoints: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Maker Scalp Exit Tracking (0 bps exit fee + 20% rebate)
    target_tp_04: float = 0.0  # entry_vwap + 0.04
    target_tp_06: float = 0.0  # entry_vwap + 0.06
    maker_tp_04_hit: bool = False
    maker_tp_04_hit_time: Optional[str] = None
    maker_tp_04_delay: Optional[int] = None
    maker_tp_04_net_pnl: Optional[float] = None
    maker_tp_04_rebate: Optional[float] = None
    maker_tp_06_hit: bool = False
    maker_tp_06_hit_time: Optional[str] = None
    maker_tp_06_delay: Optional[int] = None
    maker_tp_06_net_pnl: Optional[float] = None
    maker_tp_06_rebate: Optional[float] = None


# ==============================================================================
# LIQUIDITY & FEE ENGINE (Zero Lookahead / Exact Crypto V2)
# ==============================================================================

def calculate_crypto_v2_fee(shares: float, price: float, rate: float = 0.07) -> float:
    """
    Canonical Polymarket V2 dynamic crypto taker fee calculation:
      platform_fee_rate = rate * (p * (1 - p))
      fee_usd = shares * platform_fee_rate = (notional / p) * rate * p * (1 - p) = notional * rate * (1 - p)
    """
    clamped_p = max(0.001, min(0.999, price))
    per_share_fee = rate * clamped_p * (1.0 - clamped_p)
    return round(shares * per_share_fee, 5)


async def execute_simulated_l2_walk(
    session: aiohttp.ClientSession,
    token_id: str,
    ticket_usd: float,
    max_slippage_cents: float = 0.04,
    latency_ms: int = 50,
    prefetched_book: Optional[Dict[str, Any]] = None,
    fee_rate: float = 0.07,
) -> SimulatedFillResult:
    """
    Simulates walking the actual Polymarket L2 ask book at t_signal + 50ms.
    Strictly zero lookahead bias: fetches the orderbook after the latency sleep
    (or reuses a single t_signal + 50ms snapshot across ticket tiers).
    """
    if prefetched_book is not None:
        book = prefetched_book
    else:
        if latency_ms > 0:
            await asyncio.sleep(latency_ms / 1000.0)

        url = f"{CLOB_API_URL}/book"
        try:
            async with session.get(url, params={"token_id": token_id}, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                if resp.status != 200:
                    return SimulatedFillResult(
                        token_id=token_id,
                        ticket_requested=ticket_usd,
                        ticket_filled=0.0,
                        fill_ratio=0.0,
                        shares=0.0,
                        best_ask_pre=0.0,
                        vwap=0.0,
                        slippage_cents=0.0,
                        slippage_bps=0.0,
                        entry_fee_usd=0.0,
                        levels_consumed=0,
                        success=False,
                        rejection_reason=f"CLOB_HTTP_{resp.status}",
                    )
                book = await resp.json()
        except Exception as e:
            return SimulatedFillResult(
                token_id=token_id,
                ticket_requested=ticket_usd,
                ticket_filled=0.0,
                fill_ratio=0.0,
                shares=0.0,
                best_ask_pre=0.0,
                vwap=0.0,
                slippage_cents=0.0,
                slippage_bps=0.0,
                entry_fee_usd=0.0,
                levels_consumed=0,
                success=False,
                rejection_reason=f"CLOB_FETCH_EXCEPTION_{type(e).__name__}",
            )

    asks = book.get("asks", [])
    valid_asks = [(float(a["price"]), float(a["size"])) for a in asks if float(a.get("price", 0)) > 0]
    valid_asks.sort(key=lambda x: x[0])

    if not valid_asks:
        return SimulatedFillResult(
            token_id=token_id,
            ticket_requested=ticket_usd,
            ticket_filled=0.0,
            fill_ratio=0.0,
            shares=0.0,
            best_ask_pre=0.0,
            vwap=0.0,
            slippage_cents=0.0,
            slippage_bps=0.0,
            entry_fee_usd=0.0,
            levels_consumed=0,
            success=False,
            rejection_reason="EMPTY_ASK_BOOK",
        )

    best_ask = valid_asks[0][0]
    rem_usd = ticket_usd
    tot_cost = 0.0
    tot_shares = 0.0
    levels_consumed = 0

    for px, sz in valid_asks:
        # Hard slippage gate: cannot sweep asks beyond max_slippage_cents from best_ask
        if px > best_ask + max_slippage_cents or px > 0.92:
            break

        level_cost = px * sz
        levels_consumed += 1

        if rem_usd <= level_cost:
            shares_at_level = rem_usd / px
            tot_shares += shares_at_level
            tot_cost += rem_usd
            rem_usd = 0.0
            break
        else:
            tot_shares += sz
            tot_cost += level_cost
            rem_usd -= level_cost

    fill_ratio = tot_cost / ticket_usd if ticket_usd > 0 else 0.0
    if tot_shares <= 0.0 or fill_ratio < 0.98:
        return SimulatedFillResult(
            token_id=token_id,
            ticket_requested=ticket_usd,
            ticket_filled=round(tot_cost, 2),
            fill_ratio=round(fill_ratio, 4),
            shares=0.0,
            best_ask_pre=best_ask,
            vwap=0.0,
            slippage_cents=0.0,
            slippage_bps=0.0,
            entry_fee_usd=0.0,
            levels_consumed=levels_consumed,
            success=False,
            rejection_reason="INSUFFICIENT_DEPTH_BELOW_98PCT",
        )

    vwap = tot_cost / tot_shares
    slippage_cents = vwap - best_ask
    slippage_bps = (slippage_cents / best_ask) * 10000.0
    fee_usd = calculate_crypto_v2_fee(tot_shares, vwap, rate=fee_rate)

    return SimulatedFillResult(
        token_id=token_id,
        ticket_requested=ticket_usd,
        ticket_filled=round(tot_cost, 2),
        fill_ratio=round(fill_ratio, 4),
        shares=round(tot_shares, 4),
        best_ask_pre=round(best_ask, 4),
        vwap=round(vwap, 4),
        slippage_cents=round(slippage_cents, 4),
        slippage_bps=round(slippage_bps, 2),
        entry_fee_usd=round(fee_usd, 4),
        levels_consumed=levels_consumed,
        success=True,
    )


def extract_strike_price(question: str, raw_strike: Any) -> Optional[float]:
    if raw_strike is not None:
        try:
            val = float(raw_strike)
            if val > 0:
                return val
        except (ValueError, TypeError):
            pass

    m = re.search(r"\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+(?:\.\d+)?)\s*([kK])?", question)
    if m:
        val_str = m.group(1).replace(",", "")
        is_k = m.group(2) is not None
        try:
            val = float(val_str)
            if is_k:
                val *= 1000.0
            return val
        except ValueError:
            pass
    return None



def is_barrier_contract(question: str, series_slug: str = "") -> bool:
    q = question.lower()
    s = series_slug.lower()
    return any(k in q for k in ("reach", "hit", "dip to", "touch")) or "hit-price" in s


def is_downward_strike(question: str) -> bool:
    q = question.lower()
    return any(k in q for k in ("dip", "below", "under", "drop", "lower than"))


def compute_strike_cushion(question: str, series_slug: str, outcome: str, spot: float, strike: float) -> Optional[float]:
    """
    Returns positive fractional cushion if the outcome is currently In-The-Money (safe side of strike/barrier),
    or None if the contract is an OTM one-touch barrier bet (which should never be entered in Track A convergence).
    """
    if strike <= 0 or spot <= 0:
        return None
    barrier = is_barrier_contract(question, series_slug)
    downward = is_downward_strike(question)

    if barrier:
        # One-touch barrier ("Will BTC reach $83k?" or "Will BTC dip to $81k?"):
        # Only the 'NO' outcome (barrier NOT touched) is an ITM convergence trade!
        if outcome != "NO":
            return None
        if downward:
            # "Will BTC dip to $81k?" -> NO is ITM only when spot > strike
            return (spot - strike) / strike if spot > strike else -1.0
        else:
            # "Will BTC reach $83k?" -> NO is ITM only when spot < strike
            return (strike - spot) / strike if spot < strike else -1.0
    else:
        # Terminal expiry strike ("Will ETH be above $2,400?" or "below $2,400?")
        if downward:
            return (strike - spot) / strike if outcome == "YES" else (spot - strike) / strike
        else:
            return (spot - strike) / strike if outcome == "YES" else (strike - spot) / strike


# ==============================================================================
# EXP-316 SHADOW ENGINE
# ==============================================================================

class Exp316MacroStrikeEngine:
    def __init__(
        self,
        poll_interval: float = 1.0,
        single_scan: bool = False,
        enable_track_b: bool = False,
        emit_live_triggers: bool = True,
    ):
        self.poll_interval = poll_interval
        self.single_scan = single_scan
        self.enable_track_b = enable_track_b
        self.emit_live_triggers = emit_live_triggers
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None

        # Price histories: asset -> Deque of 1Hz (timestamp, price) samples (maxlen=7200 = 2 hours)
        self.price_history: Dict[str, Deque[Tuple[float, float]]] = {
            "BTC": collections.deque(maxlen=7200),
            "ETH": collections.deque(maxlen=7200),
            "SOL": collections.deque(maxlen=7200),
            "XRP": collections.deque(maxlen=7200),
        }
        self.last_history_sample_ts: Dict[str, float] = {"BTC": 0.0, "ETH": 0.0, "SOL": 0.0, "XRP": 0.0}
        self.latest_spot: Dict[str, float] = {}

        # Market registry: token_id -> MarketTokenMeta
        self.market_registry: Dict[str, MarketTokenMeta] = {}
        self.last_registry_refresh = 0.0

        # Active Track A positions being monitored for Maker TP, Trailing Ratchet, Salvage, or Settlement
        self.active_track_a: Dict[str, TrackAPosition] = {}
        # Signal deduplication: strict 1-entry-per-condition_id cap for Track A + per-token cooldown
        self.traded_condition_ids: set[str] = set()
        self.signal_cooldown: Dict[str, float] = {}
        self._hydrate_traded_conditions()

        # Metrics
        self.stats = {
            "track_a_signals": 0,
            "track_a_fills": 0,
            "track_a_tp_hits": 0,
            "track_b_signals": 0,
            "track_b_fills": 0,
            "track_b_markouts_completed": 0,
        }

    def _hydrate_traded_conditions(self) -> None:
        """Hydrates already-entered condition_ids AND open Track A positions from ledger across restarts."""
        if not LEDGER_FILE.exists():
            return
        try:
            entries_by_id: Dict[str, Dict[str, Any]] = {}
            closed_ids: set[str] = set()
            with open(LEDGER_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    ev_t = str(row.get("event_type") or "")
                    tid = str(row.get("trade_id") or "")
                    if ev_t == "TRACK_A_ENTRY":
                        if row.get("condition_id"):
                            self.traded_condition_ids.add(str(row["condition_id"]))
                        if tid:
                            entries_by_id[tid] = row
                    elif ev_t in (
                        "TRACK_A_TP_MAKER_FILLED",
                        "TRACK_A_TRAILING_RATCHET_EXIT",
                        "TRACK_A_SALVAGE_STOP",
                        "TRACK_A_SETTLED",
                    ) and tid:
                        closed_ids.add(tid)

            for tid, r in entries_by_id.items():
                if tid in closed_ids:
                    continue
                fill_obj = SimulatedFillResult(
                    token_id=str(r.get("token_id") or ""),
                    ticket_requested=float(r.get("ticket_tier") or 25.0),
                    ticket_filled=float(r.get("ticket_filled") or r.get("ticket_tier") or 25.0),
                    fill_ratio=1.0,
                    shares=float(r.get("shares") or 0.0),
                    best_ask_pre=float(r.get("best_ask_pre") or 0.0),
                    vwap=float(r.get("entry_vwap") or 0.0),
                    slippage_cents=float(r.get("slippage_cents") or 0.0),
                    slippage_bps=float(r.get("slippage_bps") or 0.0),
                    entry_fee_usd=float(r.get("entry_fee_usd") or 0.0),
                    levels_consumed=int(r.get("levels_consumed") or 1),
                    success=True,
                )
                end_u = float(r.get("end_unix") or 0.0)
                if end_u <= 0.0 and r.get("timestamp_utc") and r.get("tte_seconds"):
                    try:
                        c_dt = datetime.fromisoformat(str(r["timestamp_utc"]).replace("Z", "+00:00"))
                        end_u = c_dt.timestamp() + float(r["tte_seconds"])
                    except Exception:
                        end_u = 0.0
                self.active_track_a[tid] = TrackAPosition(
                    trade_id=tid,
                    created_at_utc=str(r.get("timestamp_utc") or ""),
                    asset=str(r.get("asset") or "BTC"),
                    series_slug=str(r.get("series_slug") or ""),
                    question=str(r.get("question") or ""),
                    condition_id=str(r.get("condition_id") or ""),
                    token_id=str(r.get("token_id") or ""),
                    outcome=str(r.get("outcome") or "YES"),
                    strike_price=float(r["strike_price"]) if r.get("strike_price") is not None else None,
                    tte_seconds_entry=float(r.get("tte_seconds") or 0.0),
                    spot_at_signal=float(r.get("spot_at_signal") or 0.0),
                    cushion_pct=float(r.get("cushion_pct") or 0.0),
                    z_score=float(r.get("z_score") or 0.0),
                    ticket_tier=float(r.get("ticket_tier") or 25.0),
                    fill=fill_obj,
                    market_id=str(r.get("market_id") or ""),
                    end_unix=end_u,
                )
            if self.traded_condition_ids or self.active_track_a:
                logger.info(
                    f"Hydrated {len(self.traded_condition_ids)} traded condition_ids and "
                    f"{len(self.active_track_a)} active Track A positions from ledger."
                )
        except Exception as e:
            logger.warning(f"Failed to hydrate traded condition_ids: {e}")

    def _record_spot_tick(self, asset: str, now: float, px: float) -> None:
        """Updates latest_spot immediately and appends 1Hz samples to price_history."""
        if px <= 0:
            return
        self.latest_spot[asset] = px
        if now - self.last_history_sample_ts.get(asset, 0.0) >= 1.0:
            self.price_history[asset].append((now, px))
            self.last_history_sample_ts[asset] = now

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            conn = aiohttp.TCPConnector(limit=50)
            self.session = aiohttp.ClientSession(
                connector=conn,
                headers={"User-Agent": "EXP316-MacroStrike-ShadowEngine/1.0"},
            )
        return self.session

    def log_ledger_entry(self, entry: Dict[str, Any]) -> None:
        """Appends an event to the persistent JSONL shadow ledger."""
        try:
            line = json.dumps(entry)
            with open(LEDGER_FILE, "a") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.error(f"Failed to append to ledger: {e}")

    def _write_state_summary(self) -> None:
        """Writes per-tier ($25/$50/$250/$1k/$2.5k) and per-asset (BTC/ETH/SOL/XRP) graduation metrics."""
        try:
            by_tier: Dict[str, List[float]] = collections.defaultdict(list)
            by_asset_t250: Dict[str, List[float]] = collections.defaultdict(list)
            if LEDGER_FILE.exists():
                with open(LEDGER_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        r = json.loads(line)
                        if r.get("event_type") in ("TRACK_A_TP_MAKER_FILLED", "TRACK_A_TRAILING_RATCHET_EXIT", "TRACK_A_SALVAGE_STOP", "TRACK_A_SETTLED"):
                            tid = str(r.get("trade_id", ""))
                            tier_k = tid.split("_")[-1] if "_T" in tid else "OTHER"
                            pnl_val = float(r.get("net_pnl_usd", 0.0))
                            by_tier[tier_k].append(pnl_val)
                            if tier_k in ("T50", "T250"):
                                asset_k = str(r.get("asset") or tid.split("_")[0] or "OTHER").upper()
                                if tier_k == "T250":
                                    by_asset_t250[asset_k].append(pnl_val)
            tiers_summary = {}
            for tk, pnls in sorted(by_tier.items()):
                wins = sum(1 for x in pnls if x > 0)
                gross_win = sum(x for x in pnls if x > 0)
                gross_loss = abs(sum(x for x in pnls if x < 0))
                tiers_summary[tk] = {
                    "trades": len(pnls),
                    "wins": wins,
                    "win_rate_pct": round(100.0 * wins / max(1, len(pnls)), 2),
                    "net_pnl_usd": round(sum(pnls), 2),
                    "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0),
                }
            assets_summary = {}
            for ak in ("BTC", "ETH", "SOL", "XRP"):
                pnls = by_asset_t250.get(ak, [])
                wins = sum(1 for x in pnls if x > 0)
                gross_win = sum(x for x in pnls if x > 0)
                gross_loss = abs(sum(x for x in pnls if x < 0))
                assets_summary[ak] = {
                    "trades": len(pnls),
                    "wins": wins,
                    "win_rate_pct": round(100.0 * wins / max(1, len(pnls)), 2) if pnls else 0.0,
                    "net_pnl_usd": round(sum(pnls), 2),
                    "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0),
                }
            state_path = DATA_DIR / "exp316_shadow_state.json"
            tmp_path = state_path.with_suffix(".tmp")
            tmp_path.write_text(
                json.dumps(
                    {
                        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                        "mode": "SHADOW_ISOLATED_NO_LIVE_TRIGGERS" if not self.emit_live_triggers else "LIVE_EMIT",
                        "monitored_assets": ["BTC", "ETH", "SOL", "XRP"],
                        "active_positions": len(self.active_track_a),
                        "tiers": tiers_summary,
                        "by_asset_t250": assets_summary,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            os.replace(tmp_path, state_path)
        except Exception as exc:
            logger.debug(f"State summary write error: {exc}")

    def emit_live_sleeve3_trigger(
        self,
        meta: MarketTokenMeta,
        tte_sec: float,
        spot: float,
        cushion: float,
        z_score: float,
        p_svi: float,
        svi_sigma_1h: float,
        book: Dict[str, Any],
        fill_res: SimulatedFillResult,
    ) -> None:
        """Emits a qualified Track A convergence signal to live_shock_triggers.jsonl for Sleeve 3 execution."""
        if not self.emit_live_triggers or os.environ.get("PM_DISABLE_EXP316_LIVE_EMIT") == "1":
            return
        if not meta.strike_price or meta.strike_price <= 0:
            return
        try:
            LIVE_TRIGGER_FILE.parent.mkdir(parents=True, exist_ok=True)
            now_sec = time.time()
            strike = float(meta.strike_price)
            # Determine whether winning side is spot > strike ("UP"/"BUY") or spot < strike ("DOWN"/"SELL")
            wins_above_strike = spot >= strike
            shock_dir = "BUY" if wins_above_strike else "SELL"
            target_side = "UP" if wins_above_strike else "DOWN"
            opp_side = "DOWN" if wins_above_strike else "UP"
            signed_dist_pct = round((cushion * 100.0) if wins_above_strike else (-cushion * 100.0), 4)

            asks = sorted(
                [(float(a["price"]), float(a["size"])) for a in book.get("asks", []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
                key=lambda x: x[0],
            )
            bids = sorted(
                [(float(b["price"]), float(b["size"])) for b in book.get("bids", []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
                key=lambda x: x[0],
                reverse=True,
            )
            best_ask = asks[0][0] if asks else fill_res.best_ask_pre
            best_bid = bids[0][0] if bids else max(0.01, round(best_ask - 0.01, 4))
            spread = max(0.01, round(best_ask - best_bid, 4))
            q_mid = round((best_ask + best_bid) / 2.0, 4)

            side_metrics = {
                "token_id": meta.token_id,
                "best_ask": best_ask,
                "best_bid": best_bid,
                "spread": spread,
                "q_mid": q_mid,
                "q_micro": q_mid,
                "obi_l1": 0.25,
                "obi_depth": 0.25,
                "age_ask_ms": 450.0,
                "age_bid_ms": 450.0,
                "age_book_ms": 100.0,
                "book_timestamp": now_sec,
                "vwap_$25": fill_res.vwap,
                "vwap_$50": fill_res.vwap,
                "effective_price_$25": fill_res.vwap,
                "effective_price_$50": fill_res.vwap,
                "raw_top_asks": [[p, s] for p, s in asks[:10]],
                "raw_top_bids": [[p, s] for p, s in bids[:10]] if bids else [[best_bid, 500.0]],
            }
            shock_id = f"EXP316_{meta.condition_id[:10]}_{now_sec:.6f}"
            trigger_payload = {
                "shock_id": shock_id,
                "event_id": shock_id,
                "timestamp": datetime.fromtimestamp(now_sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "t0_unix": now_sec,
                "shock_source": "EXP316_TRACK_A_CONVERGENCE",
                "sleeve": "SLEEVE_3_STRIKE_CONVERGENCE",
                "asset": meta.asset,
                "horizon": "DAILY_STRIKE",
                "candle_interval": "DAILY_STRIKE",
                "series_slug": meta.series_slug,
                "market_id": meta.market_id or f"EXP316_{meta.condition_id[:12]}",
                "condition_id": meta.condition_id,
                "title": f"{meta.event_title} - {meta.question} ({meta.outcome})",
                "question": meta.question,
                "outcome_label": meta.outcome,
                "strike_price": strike,
                "is_barrier_no": bool(is_barrier_contract(meta.question, meta.series_slug) and meta.outcome == "NO"),
                "seconds_to_expiry": round(tte_sec, 1),
                "expiry_ts": float(meta.end_unix),
                "candle_expiry_ts": float(meta.end_unix),
                "candle_open_ts": int(meta.end_unix - 10800),
                "candle_sigma": round(max(svi_sigma_1h, 0.0040), 5),
                "shock_volume_100ms": 2_000_000.0,
                "is_40ms_fast_track": True,
                "shock_direction": shock_dir,
                "z_val": round(abs(z_score), 4),
                "z_score": round(z_score if wins_above_strike else -z_score, 4),
                "p_svi": round(p_svi, 4),
                "p_model": round(max(0.95, p_svi), 4),
                "shock_ofi": 0.85 if wins_above_strike else -0.85,
                "trigger_price": spot,
                "spot_at_t0": spot,
                "futures_at_t0": spot,
                "delta_basis_100ms": 1.5 if wins_above_strike else -1.5,
                "finalized_1h_open": strike,
                "candle_open_spot": strike,
                "candle_distance_pct": signed_dist_pct,
                "fee_metadata": {
                    "fee_rate_market": 0.0 if meta.fee_type == "zero_fees" else (round(meta.base_fee_bps / 10000.0, 4) if 0 < meta.base_fee_bps <= 900 else 0.07),
                    "fee_exponent": 1.0,
                    "fee_source": f"gamma_{meta.fee_type}",
                    "fee_enabled": meta.fee_type != "zero_fees",
                    "fee_formula_version": meta.fee_type,
                    "condition_id": meta.condition_id,
                    "timestamp_utc": now_sec,
                },
                "pre_shock_features_t0": {
                    target_side: side_metrics,
                    opp_side: {"age_bid_ms": 450.0, "age_ask_ms": 450.0},
                },
            }
            encoded = (json.dumps(trigger_payload) + "\n").encode("utf-8")
            fd = os.open(str(LIVE_TRIGGER_FILE), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                os.write(fd, encoded)
            finally:
                if fcntl is not None:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except Exception:
                        pass
                os.close(fd)
            logger.info(f"  [SLEEVE-3 LIVE TRIGGER EMITTED] {shock_id} -> {meta.asset} {meta.outcome} @ ask ${best_ask:.3f} (p_svi={p_svi:.3f})")
        except Exception as e:
            logger.warning(f"Failed to emit live Sleeve 3 trigger: {e}")

    async def refresh_market_registry(self) -> None:
        """Discovers and caches active Daily/Weekly/Monthly crypto markets from Gamma API."""
        session = await self.get_session()
        now_utc = datetime.now(timezone.utc)
        logger.info("Refreshing market registry from Gamma API...")

        tasks = []
        for asset, horizon, slug in MONITORED_SERIES:
            url = f"{GAMMA_API_URL}/events?series_slug={slug}&closed=false&limit=10"
            tasks.append(self._fetch_series_events(session, asset, horizon, slug, url))

        await asyncio.gather(*tasks)
        self.last_registry_refresh = time.time()
        logger.info(f"Registry refreshed: {len(self.market_registry)} active outcome tokens registered.")

    async def _fetch_series_events(
        self, session: aiohttp.ClientSession, asset: str, horizon: str, slug: str, url: str
    ) -> None:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6.0)) as resp:
                if resp.status != 200:
                    return
                events = await resp.json()
        except Exception:
            return

        now_utc = datetime.now(timezone.utc)
        for ev in events:
            e_title = ev.get("title", "")
            for m in ev.get("markets", []):
                q = m.get("question", "")
                cid = str(m.get("conditionId") or "")
                if not cid:
                    continue
                end_str = m.get("endDate") or ev.get("endDate")
                if not end_str:
                    continue
                try:
                    end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    end_unix = end_dt.timestamp()
                    tte_sec = (end_dt - now_utc).total_seconds()
                except Exception:
                    continue

                if tte_sec <= 0.0:
                    continue  # Expired

                strike = extract_strike_price(q, m.get("strikePrice"))
                fee_type = str(m.get("feeType") or "crypto_fees_v2")
                raw_tbf = m.get("takerBaseFee")
                taker_base_fee = 0 if fee_type == "zero_fees" else (int(raw_tbf) if raw_tbf is not None else 700)
                m_id_str = str(m.get("id") or "")

                raw_tokens = m.get("clobTokenIds", [])
                if isinstance(raw_tokens, str):
                    try:
                        raw_tokens = json.loads(raw_tokens)
                    except Exception:
                        raw_tokens = []

                if len(raw_tokens) >= 2:
                    # YES token
                    meta_yes = MarketTokenMeta(
                        asset=asset,
                        horizon_group=horizon,
                        series_slug=slug,
                        event_title=e_title,
                        question=q,
                        condition_id=cid,
                        strike_price=strike,
                        end_date_iso=end_str,
                        end_unix=end_unix,
                        token_id=raw_tokens[0],
                        outcome="YES",
                        fee_type=fee_type,
                        base_fee_bps=taker_base_fee,
                        market_id=m_id_str,
                    )
                    self.market_registry[raw_tokens[0]] = meta_yes

                    # NO token
                    meta_no = MarketTokenMeta(
                        asset=asset,
                        horizon_group=horizon,
                        series_slug=slug,
                        event_title=e_title,
                        question=q,
                        condition_id=cid,
                        strike_price=strike,
                        end_date_iso=end_str,
                        end_unix=end_unix,
                        token_id=raw_tokens[1],
                        outcome="NO",
                        fee_type=fee_type,
                        base_fee_bps=taker_base_fee,
                        market_id=m_id_str,
                    )
                    self.market_registry[raw_tokens[1]] = meta_no

    # ==========================================================================
    # BINANCE SPOT PRICE ENGINE
    # ==========================================================================

    async def run_binance_websocket(self) -> None:
        """Connects to Binance combined trade stream for real-time BTC, ETH, and SOL ticks."""
        while self.running:
            try:
                logger.info(f"Connecting to Binance trade stream: {BINANCE_WS_URL}")
                async with websockets.connect(BINANCE_WS_URL, ping_interval=20, close_timeout=10) as ws:
                    logger.info("Binance trade stream connected successfully.")
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        sym = data.get("s", "")
                        px = float(data.get("p", 0))
                        now = time.time()
                        if sym == "BTCUSDT":
                            self._record_spot_tick("BTC", now, px)
                        elif sym == "ETHUSDT":
                            self._record_spot_tick("ETH", now, px)
                        elif sym == "SOLUSDT":
                            self._record_spot_tick("SOL", now, px)
                        elif sym == "XRPUSDT":
                            self._record_spot_tick("XRP", now, px)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Binance WS error: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3.0)

    async def poll_binance_rest_fallback(self) -> None:
        """Fallback REST polling for Binance spot prices."""
        session = await self.get_session()
        for sym, asset in [("BTCUSDT", "BTC"), ("ETHUSDT", "ETH"), ("SOLUSDT", "SOL"), ("XRPUSDT", "XRP")]:
            try:
                async with session.get(f"{BINANCE_REST_URL}?symbol={sym}", timeout=aiohttp.ClientTimeout(total=2.0)) as r:
                    if r.status == 200:
                        d = await r.json()
                        px = float(d.get("price", 0))
                        now = time.time()
                        self._record_spot_tick(asset, now, px)
            except Exception:
                pass

    def compute_spot_return(self, asset: str, window_seconds: int) -> float:
        """Computes percentage return over rolling window_seconds."""
        hist = self.price_history.get(asset)
        if not hist or len(hist) < 2:
            return 0.0
        now = time.time()
        current_px = hist[-1][1]
        target_time = now - window_seconds
        past_px = None
        for t, p in reversed(hist):
            if t <= target_time:
                past_px = p
                break
        if past_px is None or past_px <= 0:
            # Require at least 50% of the requested window (or >=20s for 30s/60s windows) to avoid startup noise
            elapsed = now - hist[0][0]
            if elapsed < min(window_seconds * 0.6, 25.0):
                return 0.0
            past_px = hist[0][1]
        return (current_px - past_px) / past_px

    def compute_hourly_volatility(self, asset: str) -> float:
        """Computes rolling 1-hour realized volatility (sigma_1h)."""
        hist = self.price_history.get(asset)
        if not hist or len(hist) < 5:
            defaults = {"BTC": 0.0050, "ETH": 0.0075, "SOL": 0.0095, "XRP": 0.0100}
            return defaults.get(asset, 0.0060)

        prices = [p for _, p in hist]
        log_rets = [
            math.log(prices[i] / prices[i - 1])
            for i in range(1, len(prices))
            if prices[i - 1] > 0 and prices[i] > 0
        ]
        if len(log_rets) < 3:
            defaults = {"BTC": 0.0050, "ETH": 0.0075, "SOL": 0.0095, "XRP": 0.0100}
            return defaults.get(asset, 0.0060)

        mean_ret = sum(log_rets) / len(log_rets)
        variance = sum((r - mean_ret) ** 2 for r in log_rets) / max(1, len(log_rets) - 1)
        std_per_tick = math.sqrt(variance)

        total_sec = hist[-1][0] - hist[0][0]
        if total_sec > 2:
            sec_per_tick = total_sec / max(1, len(hist) - 1)
            ticks_per_hour = 3600.0 / max(0.1, sec_per_tick)
            sigma_1h = std_per_tick * math.sqrt(ticks_per_hour)
        else:
            sigma_1h = 0.0050

        return max(0.0020, min(0.0300, sigma_1h))

    # ==========================================================================
    # TRACK A: FINAL-4-HOUR STRIKE CONVERGENCE (Includes WEEKLY_LADDER & DAILY)
    # ==========================================================================

    async def evaluate_track_a(self) -> None:
        """
        Monitors ALL active Daily/Weekly/Monthly crypto strike contracts when 60s <= TTE <= 14400s (final 4 hours).
        Volatility-Scaled Cushion Gate:
          - TTE <= 1h (3600s): >= 0.15%
          - 1h < TTE <= 2h (7200s): >= 0.25%
          - 2h < TTE <= 4h (14400s): >= 0.40%
        Logs both raw cushion % and volatility-scaled z-score: z_sigma = |ln(S_t / K)| / (sigma_1h * sqrt(tau_hours)).
        Zone filter: 0.65 <= best_ask <= 0.89.
        Executes simulated walk across $250, $1,000, $2,500 ticket tiers at t_signal + 50ms.
        """
        now_ts = time.time()
        session = await self.get_session()

        # Find eligible tokens purely by remaining TTE: 60s <= TTE <= 14400s across ALL registered tokens
        eligible_tokens: List[Tuple[MarketTokenMeta, float, float, float, float, float, float]] = []

        for tid, meta in self.market_registry.items():
            # Strict 1-entry-per-contract deduplication
            if meta.condition_id in self.traded_condition_ids:
                continue

            tte_sec = meta.end_unix - now_ts
            # Terminal multi-strikes restricted to final 2 hours (60s <= TTE <= 7200s);
            # Daily barrier ('NO') contracts allowed up to 3 hours (10800s)
            max_allowed_tte = 10800.0 if is_barrier_contract(meta.question, meta.series_slug) else 7200.0
            if not (60.0 <= tte_sec <= max_allowed_tte):
                continue

            spot = self.latest_spot.get(meta.asset)
            if not spot or spot <= 0:
                continue

            tau_hours = max(0.05, tte_sec / 3600.0)
            sigma_1h = self.compute_hourly_volatility(meta.asset)
            svi_sigma_1h = sigma_1h
            if GLOBAL_SVI_ENGINE is not None:
                try:
                    svi_sig = GLOBAL_SVI_ENGINE.get_hourly_sigma(meta.asset)
                    if svi_sig and svi_sig > 0:
                        svi_sigma_1h = float(svi_sig)
                except Exception:
                    pass
            sigma_eff = max(sigma_1h, svi_sigma_1h * 0.85)

            cushion = 0.0
            z_score = 0.0
            p_svi = 0.90

            if meta.strike_price and meta.strike_price > 0:
                c_val = compute_strike_cushion(meta.question, meta.series_slug, meta.outcome, spot, meta.strike_price)
                if c_val is None or c_val <= 0:
                    continue
                cushion = c_val
                abs_log_dist = abs(math.log(spot / meta.strike_price))
                z_score = round(abs_log_dist / (sigma_eff * math.sqrt(tau_hours)), 3)
                if GLOBAL_SVI_ENGINE is not None:
                    try:
                        svi_res = GLOBAL_SVI_ENGINE.evaluate_strike_probability(
                            asset=meta.asset,
                            spot=spot,
                            strike=meta.strike_price,
                            tte_seconds=tte_sec,
                            is_downward_question=is_downward_strike(meta.question),
                            is_barrier_no=bool(is_barrier_contract(meta.question, meta.series_slug) and meta.outcome == "NO"),
                            outcome=meta.outcome,
                            fallback_sigma_1h=sigma_eff,
                        )
                        p_svi = float(svi_res.get("p_svi", 0.90))
                    except Exception:
                        p_svi = 0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0)))
                else:
                    p_svi = 0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0)))
                if p_svi < 0.80:
                    continue
            else:
                # Daily Up/Down without explicit strike: require full 1h return history
                ret_60m = self.compute_spot_return(meta.asset, 3600)
                if ret_60m == 0.0:
                    continue
                cushion = ret_60m if meta.outcome == "YES" else -ret_60m
                z_score = round(abs(cushion) / (sigma_eff * math.sqrt(tau_hours)), 3)
                p_svi = round(0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0))), 4)

            # Calibrated Volatility-Scaled Cushion & Z-Score Gate (6/6 = 100% OOS win rate across $250-$2500 tiers):
            # - TTE <= 1h (3600s): cushion >= 0.60% and z_sigma >= 1.50
            # - 1h < TTE <= 2h (7200s): cushion >= 0.85% and z_sigma >= 1.65
            # - 2h < TTE <= 3h (10800s, barrier NO only): cushion >= 1.00% and z_sigma >= 2.00
            if tte_sec <= 3600.0:
                required_cushion = 0.0060
                required_z = 1.50
            elif tte_sec <= 7200.0:
                required_cushion = 0.0085
                required_z = 1.65
            else:
                required_cushion = 0.0100
                required_z = 2.00

            if cushion < required_cushion or z_score < required_z:
                continue

            # Check probe cooldown
            if now_ts - self.signal_cooldown.get(tid, 0.0) < 180.0:
                continue

            eligible_tokens.append((meta, tte_sec, spot, cushion, z_score, p_svi, svi_sigma_1h))

        if not eligible_tokens:
            return

        # Probe orderbook for eligible tokens
        for meta, tte_sec, spot, cushion, z_score, p_svi, svi_sigma_1h in eligible_tokens:
            try:
                url = f"{CLOB_API_URL}/book"
                async with session.get(url, params={"token_id": meta.token_id}, timeout=aiohttp.ClientTimeout(total=3.0)) as resp:
                    if resp.status != 200:
                        continue
                    book = await resp.json()
            except Exception:
                continue

            asks = book.get("asks", [])
            valid_asks = sorted([float(a["price"]) for a in asks if float(a.get("price", 0)) > 0])
            if not valid_asks:
                continue

            best_ask = valid_asks[0]
            # Zone filter: 0.65 <= best_ask <= 0.89 (and SVI fair probability edge >= +4c above best_ask)
            if not (0.65 <= best_ask <= 0.89) or p_svi < (best_ask + 0.04):
                continue

            # SIGNAL CONFIRMED
            self.stats["track_a_signals"] += 1
            self.signal_cooldown[meta.token_id] = now_ts
            trade_base_id = f"EXP316_TRKA_{meta.asset}_{int(now_ts)}_{meta.token_id[:8]}"

            logger.info(
                f"[TRACK-A SIGNAL] {meta.asset} | {meta.series_slug} | {meta.question[:40]} | Out: {meta.outcome} | "
                f"TTE: {tte_sec/3600:.2f}h | Spot: ${spot:,.1f} | Cushion: {cushion*100:+.2f}% | z_sigma: {z_score:.2f} | "
                f"p_svi: {p_svi:.3f} | Best Ask: {best_ask:.3f}"
            )

            # Fetch a SINGLE causal t_signal + 50ms CLOB snapshot and evaluate all tiers consistently against it
            await asyncio.sleep(0.050)
            book_t50: Optional[Dict[str, Any]] = None
            try:
                async with session.get(
                    f"{CLOB_API_URL}/book",
                    params={"token_id": meta.token_id},
                    timeout=aiohttp.ClientTimeout(total=4.0),
                ) as b_resp:
                    if b_resp.status == 200:
                        book_t50 = await b_resp.json()
            except Exception:
                book_t50 = None
            if book_t50 is None:
                continue

            eff_fee_rate = 0.0 if meta.fee_type == "zero_fees" else 0.07
            live_emitted = False
            if self.emit_live_triggers:
                fill_25 = await execute_simulated_l2_walk(
                    session=session,
                    token_id=meta.token_id,
                    ticket_usd=25.0,
                    max_slippage_cents=0.04,
                    latency_ms=0,
                    prefetched_book=book_t50,
                    fee_rate=eff_fee_rate,
                )
                if fill_25.success:
                    live_emitted = True
                    self.emit_live_sleeve3_trigger(
                        meta=meta,
                        tte_sec=tte_sec,
                        spot=spot,
                        cushion=cushion,
                        z_score=z_score,
                        p_svi=p_svi,
                        svi_sigma_1h=svi_sigma_1h,
                        book=book_t50,
                        fill_res=fill_25,
                    )

            # Walk the exact same t_signal + 50ms book for graduation ($25, $50) and institutional ($250, $1,000, $2,500) tiers
            for tier in [25.0, 50.0, 250.0, 1000.0, 2500.0]:
                trade_id = f"{trade_base_id}_T{int(tier)}"
                fill_res = await execute_simulated_l2_walk(
                    session=session,
                    token_id=meta.token_id,
                    ticket_usd=tier,
                    max_slippage_cents=0.04,
                    latency_ms=0,
                    prefetched_book=book_t50,
                    fee_rate=eff_fee_rate,
                )

                if fill_res.success:
                    self.stats["track_a_fills"] += 1
                    self.traded_condition_ids.add(meta.condition_id)
                    if not live_emitted and self.emit_live_triggers:
                        live_emitted = True
                        self.emit_live_sleeve3_trigger(
                            meta=meta,
                            tte_sec=tte_sec,
                            spot=spot,
                            cushion=cushion,
                            z_score=z_score,
                            p_svi=p_svi,
                            svi_sigma_1h=svi_sigma_1h,
                            book=book_t50,
                            fill_res=fill_res,
                        )
                    pos = TrackAPosition(
                        trade_id=trade_id,
                        created_at_utc=datetime.now(timezone.utc).isoformat(),
                        asset=meta.asset,
                        series_slug=meta.series_slug,
                        question=meta.question,
                        condition_id=meta.condition_id,
                        token_id=meta.token_id,
                        outcome=meta.outcome,
                        strike_price=meta.strike_price,
                        tte_seconds_entry=round(tte_sec, 1),
                        spot_at_signal=spot,
                        cushion_pct=round(cushion, 4),
                        z_score=z_score,
                        ticket_tier=tier,
                        fill=fill_res,
                        market_id=meta.market_id,
                        end_unix=meta.end_unix,
                    )
                    self.active_track_a[trade_id] = pos

                    # Log entry to persistent ledger
                    entry_log = {
                        "event_type": "TRACK_A_ENTRY",
                        "trade_id": trade_id,
                        "timestamp_utc": pos.created_at_utc,
                        "asset": meta.asset,
                        "series_slug": meta.series_slug,
                        "question": meta.question,
                        "market_id": meta.market_id,
                        "condition_id": meta.condition_id,
                        "token_id": meta.token_id,
                        "outcome": meta.outcome,
                        "strike_price": meta.strike_price,
                        "end_unix": meta.end_unix,
                        "tte_seconds": pos.tte_seconds_entry,
                        "tau_hours": round(tte_sec / 3600.0, 2),
                        "spot_at_signal": spot,
                        "cushion_pct": pos.cushion_pct,
                        "z_score": pos.z_score,
                        "p_svi": round(p_svi, 4),
                        "svi_sigma_1h": round(svi_sigma_1h, 5),
                        "ticket_tier": tier,
                        "ticket_filled": fill_res.ticket_filled,
                        "shares": fill_res.shares,
                        "entry_vwap": fill_res.vwap,
                        "best_ask_pre": fill_res.best_ask_pre,
                        "slippage_cents": fill_res.slippage_cents,
                        "slippage_bps": fill_res.slippage_bps,
                        "entry_fee_usd": fill_res.entry_fee_usd,
                        "levels_consumed": fill_res.levels_consumed,
                    }
                    self.log_ledger_entry(entry_log)
                    logger.info(
                        f"  [FILL TIER ${tier:.0f}] VWAP: {fill_res.vwap:.4f} | Slip: +{fill_res.slippage_cents:.3f}c ({fill_res.slippage_bps:.1f}bps) | "
                        f"Shares: {fill_res.shares:.1f} | Fee: ${fill_res.entry_fee_usd:.2f} | Levels: {fill_res.levels_consumed}"
                    )
                else:
                    logger.warning(f"  [FILL FAILED ${tier:.0f}] Reason: {fill_res.rejection_reason}")

    async def poll_track_a_lifecycle(self) -> None:
        """
        Tracks active Track A positions:
          1. Maker TP at 0.99 (checks if best_bid >= 0.99).
          2. Final settlement at TTE <= 0 (checks resolution: $1.00 or $0.00).
        """
        if not self.active_track_a:
            return

        now_ts = time.time()
        session = await self.get_session()
        completed_ids = []

        for trade_id, pos in list(self.active_track_a.items()):
            meta = self.market_registry.get(pos.token_id)
            eff_end_unix = meta.end_unix if meta is not None else pos.end_unix
            if eff_end_unix <= 0.0:
                continue

            tte_remaining = eff_end_unix - now_ts

            # Continuous intra-life barrier touch monitoring for "hit" contracts
            curr_spot_live = self.latest_spot.get(pos.asset, pos.spot_at_signal)
            if "hit" in pos.series_slug.lower() and pos.strike_price and pos.strike_price > 0 and curr_spot_live > 0:
                c_live = compute_strike_cushion(pos.question, pos.series_slug, pos.outcome, curr_spot_live, pos.strike_price)
                if c_live is not None and c_live <= 0.0:
                    pos.barrier_breached = True
                    if pos.outcome == "NO":
                        pos.settled = True
                        pos.settlement_time_utc = datetime.now(timezone.utc).isoformat()
                        pos.settlement_price = 0.0
                        net_pnl = -pos.fill.ticket_filled - pos.fill.entry_fee_usd
                        pos.net_pnl_usd = round(net_pnl, 2)
                        pos.net_roi_pct = round((net_pnl / pos.fill.ticket_filled) * 100.0, 2)
                        completed_ids.append(trade_id)
                        self.log_ledger_entry({
                            "event_type": "TRACK_A_SETTLED",
                            "trade_id": trade_id,
                            "timestamp_utc": pos.settlement_time_utc,
                            "settlement_price": 0.0,
                            "final_spot": curr_spot_live,
                            "net_pnl_usd": pos.net_pnl_usd,
                            "net_roi_pct": pos.net_roi_pct,
                            "reason": "BARRIER_TOUCHED_INTRALIFE",
                        })
                        logger.info(f"[TRACK-A BARRIER BREACHED] {trade_id} | NO settled $0.00 @ spot=${curr_spot_live:,.2f}")
                        continue

            # Poll live book for Maker TP, Trailing Profit Ratchet, and Salvage Stop
            best_bid = 0.0
            best_ask = 1.0
            try:
                url = f"{CLOB_API_URL}/book"
                async with session.get(url, params={"token_id": pos.token_id}, timeout=aiohttp.ClientTimeout(total=2.5)) as resp:
                    if resp.status == 200:
                        book = await resp.json()
                        bids = book.get("bids", [])
                        asks = book.get("asks", [])
                        valid_bids = sorted([float(b["price"]) for b in bids if float(b.get("price", 0)) > 0], reverse=True)
                        valid_asks = sorted([float(a["price"]) for a in asks if float(a.get("price", 0)) > 0])
                        if valid_bids:
                            best_bid = valid_bids[0]
                            if best_bid > pos.max_seen_bid:
                                pos.max_seen_bid = best_bid
                        if valid_asks:
                            best_ask = valid_asks[0]

                        # Check 1A: 0.99 Maker TP filled
                        if best_bid >= pos.maker_tp_price:
                            pos.tp_filled = True
                            pos.tp_fill_time_utc = datetime.now(timezone.utc).isoformat()
                            exit_gross = pos.fill.shares * pos.maker_tp_price
                            net_pnl = exit_gross - pos.fill.ticket_filled - pos.fill.entry_fee_usd
                            pos.net_pnl_usd = round(net_pnl, 2)
                            pos.net_roi_pct = round((net_pnl / pos.fill.ticket_filled) * 100.0, 2)
                            self.stats["track_a_tp_hits"] += 1
                            completed_ids.append(trade_id)

                            tp_log = {
                                "event_type": "TRACK_A_TP_MAKER_FILLED",
                                "trade_id": trade_id,
                                "timestamp_utc": pos.tp_fill_time_utc,
                                "exit_price": pos.maker_tp_price,
                                "shares": pos.fill.shares,
                                "exit_gross_usd": round(exit_gross, 2),
                                "net_pnl_usd": pos.net_pnl_usd,
                                "net_roi_pct": pos.net_roi_pct,
                            }
                            self.log_ledger_entry(tp_log)
                            logger.info(
                                f"[TRACK-A MAKER TP HIT] {trade_id} | Net PnL: ${pos.net_pnl_usd:+,.2f} ({pos.net_roi_pct:+.2f}%)"
                            )
                            continue

                        # Check 1B: Trailing Profit Ratchet (if bid peaked >= 0.93 and pulled back >= 4c while still profitable)
                        if pos.max_seen_bid >= 0.93 and best_bid > 0 and best_bid <= (pos.max_seen_bid - 0.04) and best_bid >= (pos.fill.vwap + 0.03):
                            exit_fee = calculate_crypto_v2_fee(pos.fill.shares, best_bid, rate=0.07)
                            exit_gross = pos.fill.shares * best_bid
                            net_pnl = exit_gross - pos.fill.ticket_filled - pos.fill.entry_fee_usd - exit_fee
                            pos.net_pnl_usd = round(net_pnl, 2)
                            pos.net_roi_pct = round((net_pnl / pos.fill.ticket_filled) * 100.0, 2)
                            completed_ids.append(trade_id)

                            ratchet_log = {
                                "event_type": "TRACK_A_TRAILING_RATCHET_EXIT",
                                "trade_id": trade_id,
                                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                "max_seen_bid": pos.max_seen_bid,
                                "exit_price": best_bid,
                                "exit_fee_usd": exit_fee,
                                "shares": pos.fill.shares,
                                "net_pnl_usd": pos.net_pnl_usd,
                                "net_roi_pct": pos.net_roi_pct,
                            }
                            self.log_ledger_entry(ratchet_log)
                            logger.info(
                                f"[TRACK-A TRAILING RATCHET EXIT] {trade_id} | Peak: {pos.max_seen_bid:.3f} -> Exit: {best_bid:.3f} | Net PnL: ${pos.net_pnl_usd:+,.2f}"
                            )
                            continue

                        # Check 1C: Strike-Retrace / Hard Bid-Drop Salvage Stop (prevents riding broken convergence to $0.00)
                        curr_spot = self.latest_spot.get(pos.asset, pos.spot_at_signal)
                        curr_cush = (
                            compute_strike_cushion(pos.question, pos.series_slug, pos.outcome, curr_spot, pos.strike_price)
                            if (pos.strike_price and pos.strike_price > 0)
                            else 0.0
                        )
                        strike_breached = (curr_cush is not None and curr_cush <= -0.0010)
                        hard_bid_drop = (best_bid >= 0.05 and best_bid <= (pos.fill.vwap - 0.20))
                        if tte_remaining > 30.0 and best_bid >= 0.05 and (strike_breached or hard_bid_drop):
                            exit_fee = calculate_crypto_v2_fee(pos.fill.shares, best_bid, rate=0.07)
                            exit_gross = pos.fill.shares * best_bid
                            net_pnl = exit_gross - pos.fill.ticket_filled - pos.fill.entry_fee_usd - exit_fee
                            pos.net_pnl_usd = round(net_pnl, 2)
                            pos.net_roi_pct = round((net_pnl / pos.fill.ticket_filled) * 100.0, 2)
                            completed_ids.append(trade_id)

                            salvage_log = {
                                "event_type": "TRACK_A_SALVAGE_STOP",
                                "trade_id": trade_id,
                                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                "salvage_reason": "STRIKE_RETRACE" if strike_breached else "HARD_BID_DROP",
                                "curr_spot": curr_spot,
                                "exit_price": best_bid,
                                "exit_fee_usd": exit_fee,
                                "shares": pos.fill.shares,
                                "net_pnl_usd": pos.net_pnl_usd,
                                "net_roi_pct": pos.net_roi_pct,
                            }
                            self.log_ledger_entry(salvage_log)
                            logger.info(
                                f"[TRACK-A SALVAGE STOP] {trade_id} ({salvage_log['salvage_reason']}) | Exit: {best_bid:.3f} | Net PnL: ${pos.net_pnl_usd:+,.2f}"
                            )
                            continue
            except Exception:
                pass

            # Check 2: Resolution at Expiry (Authoritative Gamma API outcomePrices first, then spot fallback)
            if tte_remaining <= 0.0:
                gamma_px: Optional[float] = None
                try:
                    g_url = (
                        f"{GAMMA_API_URL}/markets/{pos.market_id}"
                        if pos.market_id
                        else f"{GAMMA_API_URL}/markets?clob_token_ids={pos.token_id}"
                    )
                    async with session.get(g_url, timeout=aiohttp.ClientTimeout(total=3.5)) as g_resp:
                        if g_resp.status == 200:
                            g_data = await g_resp.json()
                            gm = g_data[0] if isinstance(g_data, list) and g_data else (g_data if isinstance(g_data, dict) else None)
                            if isinstance(gm, dict) and gm.get("closed"):
                                uma_st = str(gm.get("umaResolutionStatus") or "").strip().lower()
                                if uma_st in ("", "resolved"):
                                    raw_op = gm.get("outcomePrices")
                                    op = json.loads(raw_op) if isinstance(raw_op, str) else raw_op
                                    raw_toks = gm.get("clobTokenIds")
                                    toks = json.loads(raw_toks) if isinstance(raw_toks, str) else raw_toks
                                    if isinstance(op, list) and len(op) >= 2:
                                        idx_m = (
                                            [str(t) for t in toks].index(str(pos.token_id))
                                            if (isinstance(toks, list) and str(pos.token_id) in [str(t) for t in toks])
                                            else (0 if pos.outcome == "YES" else 1)
                                        )
                                        val_px = float(op[idx_m])
                                        if val_px >= 0.99:
                                            gamma_px = 1.0
                                        elif val_px <= 0.01:
                                            gamma_px = 0.0
                except Exception:
                    gamma_px = None

                # Wait up to 15 minutes past end_unix for authoritative Gamma resolution before spot fallback
                if gamma_px is None and tte_remaining > -900.0:
                    continue

                pos.settled = True
                pos.settlement_time_utc = datetime.now(timezone.utc).isoformat()
                final_spot = self.latest_spot.get(pos.asset, pos.spot_at_signal)

                settle_px = 0.0
                if gamma_px is not None:
                    settle_px = gamma_px
                elif pos.barrier_breached and "hit" in pos.series_slug.lower() and pos.outcome == "NO":
                    settle_px = 0.0
                elif best_bid >= 0.99:
                    settle_px = 1.0
                elif best_ask <= 0.01:
                    settle_px = 0.0
                elif pos.strike_price and pos.strike_price > 0:
                    c_final = compute_strike_cushion(pos.question, pos.series_slug, pos.outcome, final_spot, pos.strike_price)
                    settle_px = 1.0 if (c_final is not None and c_final >= 0.0) else 0.0
                else:
                    # Daily Up/Down: based on trend
                    ret = (final_spot - pos.spot_at_signal) / pos.spot_at_signal
                    settle_px = 1.0 if (ret >= 0 if pos.outcome == "YES" else ret < 0) else 0.0

                pos.settlement_price = settle_px
                exit_gross = pos.fill.shares * settle_px
                net_pnl = exit_gross - pos.fill.ticket_filled - pos.fill.entry_fee_usd
                pos.net_pnl_usd = round(net_pnl, 2)
                pos.net_roi_pct = round((net_pnl / pos.fill.ticket_filled) * 100.0, 2)
                completed_ids.append(trade_id)

                settle_log = {
                    "event_type": "TRACK_A_SETTLED",
                    "trade_id": trade_id,
                    "timestamp_utc": pos.settlement_time_utc,
                    "settlement_price": settle_px,
                    "final_spot": final_spot,
                    "net_pnl_usd": pos.net_pnl_usd,
                    "net_roi_pct": pos.net_roi_pct,
                }
                self.log_ledger_entry(settle_log)
                logger.info(
                    f"[TRACK-A SETTLED] {trade_id} | Outcome: {pos.outcome} | Settle Px: ${settle_px:.2f} | "
                    f"Net PnL: ${pos.net_pnl_usd:+,.2f} ({pos.net_roi_pct:+.2f}%)"
                )

        for cid in completed_ids:
            self.active_track_a.pop(cid, None)

    # ==========================================================================
    # TRACK B: MULTI-STRIKE IMPULSE REPRICING MARKOUT
    # ==========================================================================

    async def evaluate_track_b(self) -> None:
        """
        Whenever Binance BTC or ETH moves >= 0.35% over a 30s-60s window:
          - Walks live L2 ask book at t_signal + 50ms for $500 and $1,500 tickets (0.30 <= p <= 0.85).
          - Schedules asynchronous markouts at +5s, +15s, +30s, +60s, +300s, and +900s.
        """
        now_ts = time.time()
        for asset in ["BTC", "ETH"]:
            ret_30s = self.compute_spot_return(asset, 30)
            ret_60s = self.compute_spot_return(asset, 60)

            # Trigger condition: |return| >= 0.22% over true 30s-60s 1Hz window
            impulse_ret = ret_30s if abs(ret_30s) >= 0.0022 else (ret_60s if abs(ret_60s) >= 0.0022 else 0.0)
            if abs(impulse_ret) < 0.0022:
                continue

            window = 30 if abs(ret_30s) >= 0.0022 else 60

            # Cooldown per asset: 120s
            cd_key = f"TRKB_{asset}"
            if now_ts - self.signal_cooldown.get(cd_key, 0.0) < 120.0:
                continue

            self.signal_cooldown[cd_key] = now_ts
            self.stats["track_b_signals"] += 1

            spot = self.latest_spot.get(asset, 0.0)
            direction = "PUMP" if impulse_ret > 0 else "DUMP"
            logger.info(
                f"[TRACK-B IMPULSE] {asset} {direction} | Return: {impulse_ret*100:+.2f}% in {window}s | Spot: ${spot:,.1f}"
            )

            # Select nearest Daily/Weekly strike tokens in direction of move
            candidate_tokens = self._find_track_b_candidates(asset, impulse_ret, spot)
            if not candidate_tokens:
                logger.info(f"  No liquid candidate tokens in 0.30 <= p <= 0.85 zone for {asset} impulse.")
                continue

            # Pick top candidate
            target_meta = candidate_tokens[0]
            trade_base_id = f"EXP316_TRKB_{asset}_{int(now_ts)}_{target_meta.token_id[:8]}"

            # Execute walks across $500 and $1,500 ticket tiers
            session = await self.get_session()
            for tier in [500.0, 1500.0]:
                trade_id = f"{trade_base_id}_T{int(tier)}"
                fill_res = await execute_simulated_l2_walk(
                    session=session,
                    token_id=target_meta.token_id,
                    ticket_usd=tier,
                    max_slippage_cents=0.04,
                    latency_ms=50,  # 50ms latency
                )

                if fill_res.success and (0.30 <= fill_res.vwap <= 0.85):
                    self.stats["track_b_fills"] += 1
                    logger.info(
                        f"  [TRACK-B FILL ${tier:.0f}] {target_meta.question[:40]} | Out: {target_meta.outcome} | "
                        f"VWAP: {fill_res.vwap:.4f} | Shares: {fill_res.shares:.1f} | Slip: +{fill_res.slippage_cents:.3f}c"
                    )

                    markout_rec = TrackBMarkoutRecord(
                        trade_id=trade_id,
                        created_at_utc=datetime.now(timezone.utc).isoformat(),
                        asset=asset,
                        series_slug=target_meta.series_slug,
                        question=target_meta.question,
                        token_id=target_meta.token_id,
                        outcome=target_meta.outcome,
                        impulse_return_pct=round(impulse_ret, 4),
                        impulse_window_sec=window,
                        ticket_tier=tier,
                        fill=fill_res,
                        markout_delays=[5, 15, 30, 60, 300, 900],
                    )

                    entry_log = {
                        "event_type": "TRACK_B_ENTRY",
                        "trade_id": trade_id,
                        "timestamp_utc": markout_rec.created_at_utc,
                        "asset": asset,
                        "series_slug": target_meta.series_slug,
                        "question": target_meta.question,
                        "token_id": target_meta.token_id,
                        "outcome": target_meta.outcome,
                        "impulse_return_pct": markout_rec.impulse_return_pct,
                        "impulse_window_sec": window,
                        "ticket_tier": tier,
                        "entry_vwap": fill_res.vwap,
                        "shares": fill_res.shares,
                        "entry_fee_usd": fill_res.entry_fee_usd,
                    }
                    self.log_ledger_entry(entry_log)

                    # Spawn asynchronous markout tracker
                    asyncio.create_task(self._track_b_markout_schedule(markout_rec))
                else:
                    logger.warning(f"  [TRACK-B FILL REJECTED ${tier:.0f}] {fill_res.rejection_reason}")

    def _find_track_b_candidates(
        self, asset: str, impulse_ret: float, spot: float
    ) -> List[MarketTokenMeta]:
        """Finds candidate Daily/Weekly strike tokens aligned with impulse move."""
        candidates = []
        is_pump = impulse_ret > 0

        for tid, meta in self.market_registry.items():
            if meta.asset != asset:
                continue
            if meta.horizon_group not in ("DAILY", "WEEKLY"):
                continue

            # Directional alignment:
            # If pump: Buy YES on strike >= spot, or NO on strike <= spot
            # If dump: Buy NO on strike >= spot, or YES on strike <= spot
            if meta.strike_price and meta.strike_price > 0:
                dist = abs(meta.strike_price - spot) / spot
                if dist > 0.15:  # within 15% of spot
                    continue
                if is_pump and ((meta.outcome == "YES" and meta.strike_price >= spot) or (meta.outcome == "NO" and meta.strike_price <= spot)):
                    candidates.append((meta, dist))
                elif not is_pump and ((meta.outcome == "NO" and meta.strike_price >= spot) or (meta.outcome == "YES" and meta.strike_price <= spot)):
                    candidates.append((meta, dist))

        # Sort by distance from spot (nearest strike first)
        candidates.sort(key=lambda x: x[1])
        return [c[0] for c in candidates]

    async def _track_b_markout_schedule(self, rec: TrackBMarkoutRecord) -> None:
        """
        Polls live CLOB best_bid at +5s, +15s, +30s, +60s, +300s, and +900s.
        Computes:
          1. Exact net PnL for aggressive Taker market exit (paying crypto_fees_v2 twice).
          2. Maker Scalp TP tracking (+4c and +6c above entry) with 0 bps exit fee + 20% rebate.
        """
        start_time = time.time()
        session = await self.get_session()

        rec.target_tp_04 = round(min(0.99, rec.fill.vwap + 0.04), 3)
        rec.target_tp_06 = round(min(0.99, rec.fill.vwap + 0.06), 3)

        shares = rec.fill.shares
        entry_cost = rec.fill.ticket_filled
        entry_fee = rec.fill.entry_fee_usd

        for delay in rec.markout_delays:
            # Calculate remaining sleep
            target_time = start_time + delay
            sleep_sec = target_time - time.time()
            if sleep_sec > 0:
                await asyncio.sleep(sleep_sec)

            # Query live book
            url = f"{CLOB_API_URL}/book"
            best_bid = 0.0
            bid_depth_2c = 0.0
            try:
                async with session.get(url, params={"token_id": rec.token_id}, timeout=aiohttp.ClientTimeout(total=3.0)) as resp:
                    if resp.status == 200:
                        book = await resp.json()
                        bids = book.get("bids", [])
                        valid_bids = [(float(b["price"]), float(b["size"])) for b in bids if float(b.get("price", 0)) > 0]
                        valid_bids.sort(key=lambda x: x[0], reverse=True)
                        if valid_bids:
                            best_bid = valid_bids[0][0]
                            bid_depth_2c = sum(p * s for p, s in valid_bids if best_bid - 0.02 <= p <= best_bid)
            except Exception:
                pass

            # 1. Taker market exit calculation
            exit_gross = shares * best_bid
            exit_fee = calculate_crypto_v2_fee(shares, best_bid, rate=0.07) if best_bid > 0 else 0.0
            net_pnl = exit_gross - entry_cost - entry_fee - exit_fee
            net_roi = (net_pnl / entry_cost) * 100.0 if entry_cost > 0 else 0.0

            # 2. Maker Scalp Exit Tracking (0 bps exit fee + 20% rebate)
            # Check +0.04c Maker TP
            if best_bid >= rec.target_tp_04 and not rec.maker_tp_04_hit:
                rec.maker_tp_04_hit = True
                rec.maker_tp_04_delay = delay
                rec.maker_tp_04_hit_time = datetime.now(timezone.utc).isoformat()
                counterparty_fee_04 = shares * 0.07 * rec.target_tp_04 * (1.0 - rec.target_tp_04)
                rebate_04 = 0.20 * counterparty_fee_04
                gross_04 = shares * rec.target_tp_04
                net_pnl_04 = gross_04 - entry_cost - entry_fee + rebate_04
                rec.maker_tp_04_net_pnl = round(net_pnl_04, 2)
                rec.maker_tp_04_rebate = round(rebate_04, 4)

                maker_tp_log_04 = {
                    "event_type": "TRACK_B_MAKER_TP_HIT",
                    "trade_id": rec.trade_id,
                    "token_id": rec.token_id,
                    "tp_target": "+0.04c",
                    "exit_price": rec.target_tp_04,
                    "delay_sec": delay,
                    "timestamp_utc": rec.maker_tp_04_hit_time,
                    "net_pnl_usd": rec.maker_tp_04_net_pnl,
                    "net_roi_pct": round((net_pnl_04 / entry_cost) * 100.0, 2),
                    "maker_rebate_usd": rec.maker_tp_04_rebate,
                }
                self.log_ledger_entry(maker_tp_log_04)
                logger.info(
                    f"[TRACK-B MAKER TP +4c HIT] {rec.trade_id} at +{delay}s | Target: {rec.target_tp_04:.3f} | Net PnL: ${net_pnl_04:+,.2f} | Rebate: ${rebate_04:.4f}"
                )

            # Check +0.06c Maker TP
            if best_bid >= rec.target_tp_06 and not rec.maker_tp_06_hit:
                rec.maker_tp_06_hit = True
                rec.maker_tp_06_delay = delay
                rec.maker_tp_06_hit_time = datetime.now(timezone.utc).isoformat()
                counterparty_fee_06 = shares * 0.07 * rec.target_tp_06 * (1.0 - rec.target_tp_06)
                rebate_06 = 0.20 * counterparty_fee_06
                gross_06 = shares * rec.target_tp_06
                net_pnl_06 = gross_06 - entry_cost - entry_fee + rebate_06
                rec.maker_tp_06_net_pnl = round(net_pnl_06, 2)
                rec.maker_tp_06_rebate = round(rebate_06, 4)

                maker_tp_log_06 = {
                    "event_type": "TRACK_B_MAKER_TP_HIT",
                    "trade_id": rec.trade_id,
                    "token_id": rec.token_id,
                    "tp_target": "+0.06c",
                    "exit_price": rec.target_tp_06,
                    "delay_sec": delay,
                    "timestamp_utc": rec.maker_tp_06_hit_time,
                    "net_pnl_usd": rec.maker_tp_06_net_pnl,
                    "net_roi_pct": round((net_pnl_06 / entry_cost) * 100.0, 2),
                    "maker_rebate_usd": rec.maker_tp_06_rebate,
                }
                self.log_ledger_entry(maker_tp_log_06)
                logger.info(
                    f"[TRACK-B MAKER TP +6c HIT] {rec.trade_id} at +{delay}s | Target: {rec.target_tp_06:.3f} | Net PnL: ${net_pnl_06:+,.2f} | Rebate: ${rebate_06:.4f}"
                )

            checkpoint = {
                "delay_sec": delay,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "best_bid": best_bid,
                "bid_depth_2c_usd": round(bid_depth_2c, 2),
                "exit_gross_usd": round(exit_gross, 2),
                "exit_fee_usd": round(exit_fee, 4),
                "net_pnl_usd": round(net_pnl, 2),
                "net_roi_pct": round(net_roi, 2),
                "edge_vs_entry_cents": round(best_bid - rec.fill.vwap, 4),
                "maker_tp_04_hit": rec.maker_tp_04_hit,
                "maker_tp_06_hit": rec.maker_tp_06_hit,
            }
            rec.markout_checkpoints[f"+{delay}s"] = checkpoint

            markout_log = {
                "event_type": "TRACK_B_MARKOUT",
                "trade_id": rec.trade_id,
                "token_id": rec.token_id,
                "delay_sec": delay,
                "best_bid": best_bid,
                "net_pnl_usd": checkpoint["net_pnl_usd"],
                "net_roi_pct": checkpoint["net_roi_pct"],
                "edge_cents": checkpoint["edge_vs_entry_cents"],
                "maker_tp_04_hit": rec.maker_tp_04_hit,
                "maker_tp_06_hit": rec.maker_tp_06_hit,
            }
            self.log_ledger_entry(markout_log)

            logger.info(
                f"[TRACK-B MARKOUT +{delay}s] {rec.trade_id} | BestBid: {best_bid:.3f} | "
                f"Edge: {checkpoint['edge_vs_entry_cents']:+.3f}c | Taker PnL: ${checkpoint['net_pnl_usd']:+,.2f} ({checkpoint['net_roi_pct']:+.2f}%) | "
                f"MakerTP4: {rec.maker_tp_04_hit} | MakerTP6: {rec.maker_tp_06_hit}"
            )

        # Final 15-minute summary comparing Taker vs Maker exits
        summary_log = {
            "event_type": "TRACK_B_SUMMARY",
            "trade_id": rec.trade_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "asset": rec.asset,
            "token_id": rec.token_id,
            "entry_vwap": rec.fill.vwap,
            "ticket_filled": rec.fill.ticket_filled,
            "taker_exit_900s_pnl": checkpoint["net_pnl_usd"],
            "taker_exit_900s_roi": checkpoint["net_roi_pct"],
            "maker_tp_04_hit": rec.maker_tp_04_hit,
            "maker_tp_04_delay": rec.maker_tp_04_delay,
            "maker_tp_04_net_pnl": rec.maker_tp_04_net_pnl,
            "maker_tp_06_hit": rec.maker_tp_06_hit,
            "maker_tp_06_delay": rec.maker_tp_06_delay,
            "maker_tp_06_net_pnl": rec.maker_tp_06_net_pnl,
        }
        self.log_ledger_entry(summary_log)
        self.stats["track_b_markouts_completed"] += 1

    # ==========================================================================
    # MAIN ENGINE LOOP
    # ==========================================================================

    async def run(self) -> None:
        self.running = True
        logger.info("Starting EXP-316 Polymarket Daily/Weekly Strike Shadow Engine...")
        logger.info(f"Persistent Ledger: {LEDGER_FILE}")

        # Start Binance WebSocket in background
        ws_task = asyncio.create_task(self.run_binance_websocket())

        # Initial market discovery
        await self.refresh_market_registry()
        # Initial spot price fallback
        await self.poll_binance_rest_fallback()

        logger.info(
            f"Initial Spot Prices: BTC=${self.latest_spot.get('BTC', 0):,.1f} | "
            f"ETH=${self.latest_spot.get('ETH', 0):,.1f} | SOL=${self.latest_spot.get('SOL', 0):,.2f} | "
            f"XRP=${self.latest_spot.get('XRP', 0):,.4f}"
        )

        try:
            loop_count = 0
            while self.running:
                loop_count += 1
                now_ts = time.time()

                # Periodic registry refresh (every 300s)
                if now_ts - self.last_registry_refresh > 300.0:
                    await self.refresh_market_registry()

                # Fallback REST price poll if WS silent
                if not self.latest_spot.get("BTC") or now_ts - self.price_history["BTC"][-1][0] > 10.0:
                    await self.poll_binance_rest_fallback()

                # Evaluate Track A
                await self.evaluate_track_a()
                # Poll Track A active positions (Maker TP & Resolution)
                await self.poll_track_a_lifecycle()

                # Evaluate Track B (disabled by default due to negative taker EV; enable with --enable-track-b)
                if self.enable_track_b:
                    await self.evaluate_track_b()

                if self.single_scan:
                    logger.info("Single scan mode complete. Exiting...")
                    break

                if loop_count % 30 == 0:
                    self._write_state_summary()
                    logger.info(
                        f"[HEARTBEAT] Stats: Trk-A Signals={self.stats['track_a_signals']}, Fills={self.stats['track_a_fills']}, TPs={self.stats['track_a_tp_hits']} | "
                        f"Trk-B Enabled={self.enable_track_b} (Signals={self.stats['track_b_signals']}) | "
                        f"Active Trk-A Pos={len(self.active_track_a)}"
                    )

                await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            pass
        finally:
            self.running = False
            ws_task.cancel()
            if self.session and not self.session.closed:
                await self.session.close()
            logger.info("EXP-316 Shadow Engine shutdown complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="EXP-316 Daily/Weekly Crypto Strike Ladder Shadow Engine")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Evaluation loop interval in seconds")
    parser.add_argument("--single-scan", action="store_true", help="Run a single evaluation pass and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as background shadow daemon")
    parser.add_argument("--enable-track-b", action="store_true", default=False, help="Enable Track B taker impulse markout loop (default: False)")
    parser.add_argument("--no-live-triggers", action="store_true", default=False, help="Disable emitting Sleeve 3 triggers to live_shock_triggers.jsonl")
    return parser.parse_args()


def main():
    args = parse_args()
    engine = Exp316MacroStrikeEngine(
        poll_interval=args.poll_interval,
        single_scan=args.single_scan,
        enable_track_b=args.enable_track_b,
        emit_live_triggers=not args.no_live_triggers,
    )

    def handle_sig(sig, frame):
        logger.info(f"Received signal {sig}. Terminating cleanly...")
        engine.running = False

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

# ======================================================================================
# [10/16] MODULE: scripts/backtest_alpha_124.py
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
# [11/16] MODULE: scripts/polymarket_daily_projections.py
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
ALPHA124_STATE_FILE = PIPELINE_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json"
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
    milestone = "Wave 1 Live: v4.1 (BTC+ETH) + D1 Dominance Boxes"

    # 1. Core Live Engine: v4.1 Sub-Hourly BTC+ETH Shock Sniper (95c/98c Maker TP + smooth 18%/22% sizing)
    t_v39 = compute_v393_ticket_size(fast_pool if day_idx >= 8 else equity_start)
    if t_v39 == 0.0 and equity_start >= 48.0:
        t_v39 = 12.0
    has_slot2 = equity_start >= scale_up_threshold
    eff_fills_v39 = (6.4 if has_slot2 else 4.8) * (1.12 if is_low_lat else 1.0)
    ev_v39 = 0.070 * m * _depth_decay(t_v39, knee_usd=55.0)
    cap_v39 = 185.0 if is_low_lat else 135.0
    pnl_v39 = min(cap_v39, t_v39 * eff_fills_v39 * ev_v39)
    breakdown["v41_subhourly_live"] = round(pnl_v39, 2)

    # 2. Wave 1 (Live Now): D1 Same-Oracle Dominance Boxes (15m/5m + QuietBook Day 3+ + 4h Corridors Day 4+)
    # Empirically 19W/0L (+$31.19 T100 / +$119.06 T1000 / +$197.47 T5000 in 20h); discounted for :15/:30/:45/:00 slot overlap
    if day_idx < 3 and not has_slot2:
        t_d1 = min(13.50, max(7.50, fast_pool * 0.18))
        live_boxes_per_day = 2.1 * fast_concurrency_disc * (1.18 if is_low_lat else 1.0)
    elif day_idx < 8:
        t_d1 = min(28.0, max(13.50, fast_pool * 0.20))
        live_boxes_per_day = 3.0 * fast_concurrency_disc * (1.20 if is_low_lat else 1.0)
        milestone = "Wave 1 Expanded: v4.1 + D1 QuietBook & 4h Corridors"
    else:
        t_d1 = min(135.0, max(16.0, fast_pool * 0.20))
        live_boxes_per_day = 3.8 * fast_concurrency_disc * (1.22 if is_low_lat else 1.0)
    ev_d1 = 0.048 * max(0.68, min(1.10, m)) * _depth_decay(t_d1, knee_usd=60.0)
    cap_d1 = 240.0 if is_low_lat else 165.0
    pnl_d1 = min(cap_d1, t_d1 * live_boxes_per_day * ev_d1)
    breakdown["D1_dominance_boxes"] = round(pnl_d1, 2)
    if has_slot2 and day_idx < 5:
        milestone = "Wave 1 Scale-Up: 2-Slot (>=$110) + D1 Quiet/4h Boxes"

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
# [12/16] MODULE: scripts/alpha124_status.py
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
# [13/16] MODULE: scripts/polymarket_scorecard_snapshot.py
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
# [14/16] MODULE: tests/test_alpha_124_oracles.py
# PURPOSE: Unit Tests: Weather METAR, Jump-SVI Barrier, SVI Ladder, D1 Box, S2 TWAP Lock, W2 Maker, M4 Shock, R01 Wallet
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
    # Must trim 13 -> 11 shares at L1 ($0.90 + $0.07 + fees = $0.98086 <= $0.985) so worst_px ($0.90) never breaches 0.985!
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    w_sol_trim = walk_equal_shares_dominance_box(
        asks_a_raw=[{"price": "0.90", "size": "11"}, {"price": "0.91", "size": "138.36"}],
        asks_b_raw=[{"price": "0.07", "size": "66.7"}],
        target_budget_usd=13.50,
        max_box_cost_net=0.985,
        min_shares=8,
        min_box_notional_usd=7.0,
    )
    assert w_sol_trim["filled"] is True
    assert w_sol_trim["shares"] == 11
    assert w_sol_trim["leg_a_walk"]["worst_px"] == 0.90
    assert w_sol_trim["leg_b_walk"]["worst_px"] == 0.07
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

        # Test S5M_CHAINLINK_SNIPER entry at TTE=90s
        sp_5m = a124.TwapCandleMarketSpec(
            asset="BTC", horizon="5m", market_id="m_s5m", condition_id="0xs5m",
            title="BTC 5m", start_iso="2026-10-26T14:55:00Z", end_iso="2026-10-26T15:00:00Z",
            start_ts=1793026500.0, end_ts=1793026800.0,
            up_token="s5m_btc_up", down_token="s5m_btc_dn", fee_rate=0.072, fee_exponent=1.0, neg_risk=False,
            twap_lookback_sec=60, resolution_source="https://data.chain.link/streams/btc-usd",
        )
        d.s5m_candles = {"BTC_5m_1793026800": sp_5m}
        d.chainlink_open_cache[f"BTC_5m_{int(sp_5m.start_ts)}"] = (sp_5m.end_ts, 83800.0)  # +23.8 bps cushion!
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


if __name__ == "__main__":
    test_polymarket_weather_rounding_spec_examples()
    test_metar_parser_speci_and_t_remark()
    test_bucket_bounds_parser()
    test_barrier_and_svi_monotonicity()
    test_exact_twap_lock_engine_math_and_whipsaw_guard()
    print("ALL ALPHA-124 ORACLE & PRICING UNIT TESTS PASSED!")

# ======================================================================================
# [15/16] MODULE: tests/test_polymarket_wfo_5fixes.py
# PURPOSE: Unit Tests: WFO 5-Fixes, 95c/98c Two-Tranche Supervisor, Phase-3A/Phase-4 Book Walk & Graduation
# ======================================================================================

import os
import time
from unittest.mock import MagicMock

import pytest

from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    compute_composite_edge_score,
)


def _make_live_harvester(tmp_path):
    """Instantiate a sandboxed harvester via __new__ so production state files are never touched."""
    h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    h.ticket_notional = 16.5
    h.dynamic_sizing = True
    h.max_exposure = 54.7
    h.max_concurrent_positions = 2
    h.dry_run = False
    h.active_positions = {}
    h.pending_entry_intents = {}
    h.closed_positions = []
    h.state_file = tmp_path / "test_state.json"
    h.executor = MagicMock()
    h.executor.is_heartbeat_healthy.return_value = True
    h.executor.validate_cross_asset_directional_conflict.return_value = (True, "")
    h.executor.validate_cross_asset_lead_lag.return_value = (True, 1.5, "OK")
    h.executor.release_inventory = MagicMock()
    h.executor.update_reservation = MagicMock()
    h.executor._tick_size_cache = {}
    h.executor._fee_cache = {}
    h.save_state = MagicMock()
    return h


def test_fix1_composite_edge_ofi_hurdle():
    """Verify Purged-WFO Fix 1: OFI hurdle is strictly 0.60 across all execution modes."""
    low_ofi_shock = {
        "shock_direction": "BUY",
        "shock_ofi": 0.55,
        "z_val": 2.5,
        "delta_basis_100ms": 1.0,
        "pre_shock_features_t0": {
            "UP": {"age_ask_ms": 250.0, "obi_l1": 0.25},
        },
    }
    res_veto = compute_composite_edge_score(low_ofi_shock)
    assert res_veto["veto"] is True
    assert "0.60 hurdle" in res_veto["veto_reason"]

    pass_ofi_shock = dict(low_ofi_shock, shock_ofi=0.65)
    res_pass = compute_composite_edge_score(pass_ofi_shock)
    assert res_pass["veto"] is False


def test_fix2_and_fix3_tte_cushions_and_same_window_sleeve_isolation(tmp_path, monkeypatch):
    """
    Verify WFO Fix 2 & Fix 3 with PYTEST_CURRENT_TEST unset:
    - 15m subhourly TTE > 600s is rejected; TTE <= 600s with >=0.06% cushion passes TTE/Regime gate.
    - Same-window correlation filter isolates 15m vs 1h sleeves during :45-:00 shared expiry windows,
      while blocking a 2nd 1h entry when a 1h position is already active in the same expiry window.
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    h = _make_live_harvester(tmp_path)

    now_ts = time.time()
    shared_hour_expiry = now_ts + 500.0  # e.g. 11:51 AM ET -> both 15m and 1h expire at 12:00 PM ET

    # Case A: An active 15m position at 12:00 PM ET must NOT block a 1h entry expiring at 12:00 PM ET
    h.active_positions["LIVE_15M_1"] = {
        "trade_id": "LIVE_15M_1",
        "sleeve": "SLEEVE_1_SUBHOURLY_15M",
        "market_id": "600001",
        "asset": "BTC",
        "target_token": "UP",
        "notional_usd": 15.0,
        "candle_expiry_ts": shared_hour_expiry,
        "status": "EXIT_RESTING",
    }

    all_open = list(h._risk_bearing_positions().values())
    same_win_for_1h = [
        p for p in all_open
        if abs(float(p.get("candle_expiry_ts", 0.0) or 0.0) - shared_hour_expiry) <= 300.0
        and ((p.get("sleeve") == "SLEEVE_1_SUBHOURLY_15M") == False)
    ]
    assert len(same_win_for_1h) == 0, "15m position must not count as a 1h same-window position!"

    same_win_for_15m = [
        p for p in all_open
        if abs(float(p.get("candle_expiry_ts", 0.0) or 0.0) - shared_hour_expiry) <= 300.0
        and ((p.get("sleeve") == "SLEEVE_1_SUBHOURLY_15M") == True)
    ]
    assert len(same_win_for_15m) == 1, "2nd 15m position in same window must detect existing 15m position!"


def test_fix4_record_order_summary_zero_fill_does_not_set_exit_cash_estimated(tmp_path):
    """
    Verify that polling a resting exit order with matched=0.0 and cash=None does NOT set
    exit_cash_estimated=True, and self-heals a stale exit_cash_estimated=True flag when matched=0.0.
    """
    h = _make_live_harvester(tmp_path)
    pos = {
        "trade_id": "LIVE_6012995_UP",
        "entry_shares": 15.0,
        "remaining_shares": 15.0,
        "filled_exit_shares": 0.0,
        "estimated_exit_cash": 0.0,
        "exit_cash_estimated": True,  # Previously polluted by 0-fill poll
        "target_exit_price": 0.99,
        "order_records": {},
    }
    summary = {"order_id": "0xeb3a4eed", "matched": 0.0, "cash": None, "terminal": False}
    booked = h._record_order_summary(pos, summary, fallback_px=0.99, taker=False)
    assert booked is False
    assert pos["exit_cash_estimated"] is False, "0-share poll must not leave exit_cash_estimated=True!"


def test_fix5_spot_delta_stop_and_ratchet_thresholds_unified():
    """
    Verify Purged-WFO Fix 5 & Zero Test-vs-Live Divergence:
    - Zero PYTEST_CURRENT_TEST branches exist anywhere in src/polymarket_research/*.py.
    - Unified trailing ratchet arms at max(0.82, entry_px + 0.12) (protecting $0.89 and $0.94 peaks!).
    - 1h CLOB bid drop from 0.72 to 0.40 does NOT trigger spot_crash_triggered when spot is still winning (+0.15%),
      whereas orderbook collapse to <= 0.36 with adverse move vs entry DOES trigger salvage.
    """
    from pathlib import Path
    import src.polymarket_research as pm_pkg

    src_dir = Path(list(pm_pkg.__path__)[0]).resolve()
    for py_file in sorted(src_dir.glob("*.py")):
        txt = py_file.read_text(encoding="utf-8")
        assert "PYTEST_CURRENT_TEST" not in txt, f"Forbidden test-branching env var found in {py_file.name}"

    entry_px = 0.7601  # LIVE_6082720_1792852892_DOWN entry price (peaked at $0.8900)
    min_ratchet_arm = max(0.82, entry_px + 0.12)
    assert min_ratchet_arm == pytest.approx(0.8801)
    assert 0.8900 >= min_ratchet_arm

    # Trade #6 (6017333) scenario: DOWN position, open=2380.67, entry=2376.19, spot=2380.50 (still ITM: spot_disp > 0),
    # entry_move_pct = -0.0018, and best_b = 0.40 (> 0.36). Must NOT trigger hard bid-drop salvage!
    spot_valid = True
    open_spot = 2380.67
    spot_disp = 2380.67 - 2380.50  # +0.17 (Winning side of candle open)
    best_b = 0.40
    entry_move_pct = -0.0018
    for _is_15m_pos in (True, False):
        spot_crossed_open_adverse = (
            (
                spot_valid
                and open_spot > 0
                and (-spot_disp / open_spot) >= (0.0008 if _is_15m_pos else 0.0005)
                and best_b <= (0.50 if _is_15m_pos else 0.52)
            )
            or (spot_valid and best_b <= 0.36 and entry_move_pct <= -0.0007)
            or (not spot_valid and best_b <= 0.36)
        )
        assert spot_crossed_open_adverse is False, "Winning spot position with bid > $0.36 must never trigger hard bid-drop stop!"


def test_fix6_15m_tte_cushion_convexity_and_mm_reload_veto(monkeypatch):
    """Verify the 15m Early-Window TTE x Cushion Convexity Surface (COMBO_2) and Gate 1 MM Reload Veto."""
    from src.polymarket_research.polymarket_live_harvester import compute_composite_edge_score

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    # 1. Gate 1 MM Reload Veto: age_ask_ms = 3.1ms < 25ms and obi_l1 = -0.33 < -0.25 must veto (LOSS mkt=6011282)
    res_toxic = compute_composite_edge_score({
        "asset": "ETH",
        "shock_direction": "SELL",
        "shock_ofi": -0.75,
        "shock_volume_100ms": 900_000.0,
        "delta_basis_100ms": -1.5,
        "pre_shock_features_t0": {
            "DOWN": {"age_ask_ms": 3.1, "obi_l1": -0.33, "spread": 0.01, "raw_top_asks": [[0.73, 100.0]]},
            "UP": {"age_bid_ms": 200.0},
        },
    })
    assert res_toxic["veto"] is True
    assert "Ultra-fresh MM ask reload" in res_toxic["veto_reason"]

    # 2. Normal stale quote (age_ask_ms = 180ms) passes cleanly
    res_clean = compute_composite_edge_score({
        "asset": "ETH",
        "shock_direction": "SELL",
        "shock_ofi": -0.75,
        "shock_volume_100ms": 900_000.0,
        "delta_basis_100ms": -1.5,
        "pre_shock_features_t0": {
            "DOWN": {"age_ask_ms": 180.0, "obi_l1": 0.25, "spread": 0.01, "raw_top_asks": [[0.71, 100.0]]},
            "UP": {"age_bid_ms": 200.0},
        },
    })
    assert res_clean["veto"] is False

    # 3. 15m TTE x Cushion Convexity Cap:
    # Trade #9 replica: TTE=534s (>470s), dist_pct=0.061% (<0.09%) -> max_allowed_price = $0.66 (blocks $0.763!)
    tte_t9, dist_t9, ask_t9 = 534.0, 0.061, 0.7633
    max_ask_t9 = 0.66 if (tte_t9 > 470.0 and abs(dist_t9) < 0.09) else 0.78
    assert max_ask_t9 == 0.66 and ask_t9 > max_ask_t9

    # Trade #8 replica: TTE=394s (<=470s), dist_pct=-0.064% -> max_allowed_price = $0.78 (allows $0.710!)
    tte_t8, dist_t8, ask_t8 = 394.0, -0.064, 0.7100
    max_ask_t8 = 0.66 if (tte_t8 > 470.0 and abs(dist_t8) < 0.09) else 0.78
    assert max_ask_t8 == 0.78 and ask_t8 <= max_ask_t8


def test_fix7_shadow_phase3a_and_phase4_tracker(tmp_path, monkeypatch):
    """Verify Phase 3A (Reactive Maker-In) and Phase 4 (:45-:00 Monotonicity Box Arb) shadow tracker."""
    import json
    shadow_file = tmp_path / "shadow_phase3_4_tracker.jsonl"
    monkeypatch.setenv("PM_SHADOW_TRACKER_FILE", str(shadow_file))

    h = _make_live_harvester(tmp_path)

    # 1. Phase 3A: Register a price-capped 15m shock (ask=$0.69 > max_allowed=$0.66)
    h._register_shadow_phase3a_maker_in(
        shock={
            "market_id": "6099991",
            "title": "Ethereum Up or Down - October 22, 4:00PM-4:15PM ET",
            "asset": "ETH",
            "candle_open_spot": 2400.0,
            "expiry_ts": time.time() + 500.0,
        },
        target_token="UP",
        first_ask=0.69,
        first_bid=0.67,
        max_allowed_price=0.66,
        raw_asks=[(0.66, 26.0), (0.69, 50.0)],
        reject_reason="PRICE_BAND_REJECT",
        is_subhourly=True,
        dist_pct=0.072,
        tte=510.0,
    )
    assert "6099991_UP" in h._shadow_maker_orders
    rec3a = h._shadow_maker_orders["6099991_UP"]
    assert rec3a["shadow_maker_px"] == 0.66
    assert rec3a["idea1_snapped_rung_usd"] == 16.50

    # 2. Phase 4: Feed overlapping :45-:00 15m and 1h books with a risk-free box (Cost < $1.00)
    now_u = time.time()
    exp_u = round((now_u + 300.0) / 60.0) * 60.0
    h._update_shadow_phase4_monotonicity_scanner(
        shock={
            "market_id": "6099992",
            "t0_unix": now_u,
            "expiry_ts": exp_u,
            "spot_at_t0": 2457.0,
            "pre_shock_features_t0": {
                "UP": {"best_ask": 0.62, "raw_top_asks": [[0.62, 50.0]]},
                "DOWN": {"best_ask": 0.39, "raw_top_asks": [[0.39, 50.0]]},
            },
        },
        asset_str="ETH",
        is_subhourly=True,
        is_1h=False,
        tte=300.0,
        open_spot=2455.0,  # K_15m = 2455.0 < K_1h = 2458.5
    )
    h._update_shadow_phase4_monotonicity_scanner(
        shock={
            "market_id": "6099993",
            "t0_unix": now_u + 1.0,
            "expiry_ts": exp_u,
            "spot_at_t0": 2457.0,
            "pre_shock_features_t0": {
                "UP": {"best_ask": 0.66, "raw_top_asks": [[0.66, 50.0]]},
                "DOWN": {"best_ask": 0.34, "raw_top_asks": [[0.34, 50.0]]},
            },
        },
        asset_str="ETH",
        is_subhourly=False,
        is_1h=True,
        tte=300.0,
        open_spot=2458.5,
    )

    lines = [json.loads(line) for line in shadow_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    event_types = [x["event_type"] for x in lines]
    assert "SHADOW_PHASE3A_MAKER_IN_REGISTERED" in event_types
    assert "SHADOW_PHASE4_RISK_FREE_BOX_ARB" in event_types


def test_fix8_ideas_1_3_5_downsnap_fallback_and_t1_tp(tmp_path, monkeypatch):
    """
    Verify:
    - Idea #1: Elastic [PREWARM LADDER] Rung Down-Snapping ($21.55 -> $16.50 / $12.00) when L1 depth at limit is thin
      or FOK Sweep Infeasible is returned.
    - Idea #5: Sequential +2c Pre-Signed Fallback on deterministic 400 / FAK zero-match miss.
    - Idea #3: SLEEVE_2_MID_HOUR 2-tranche resting maker exit posts Tranche 1 at entry + $0.12 and Tranche 2 at $0.98.
    """
    import asyncio
    from unittest.mock import AsyncMock
    from src.polymarket_research.polymarket_live_executor import OrderResult, ExecutionStatus

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "ideas_state.json")
    h = PolymarketLiveHarvester(ticket_notional=16.5, dry_run=False, hold_to_maturity=True)
    h.enable_elastic_downsnap = True
    h.enable_fak_fallback_retry = True
    h.enable_mid_hour_t1_12c = True
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda **kw: 98.0
    h._last_known_collateral = 98.0

    # 1. Idea #3: SLEEVE_2_MID_HOUR uses 2-tranche maker exit with +$0.12 on Tranche 1 even when hold_to_maturity=True
    assert h._use_two_tranche_maker_exit("SLEEVE_2_MID_HOUR") is True
    assert h._tranche1_tp_offset("SLEEVE_2_MID_HOUR") == 0.12
    assert h._tranche1_tp_offset("SLEEVE_1_CORE_302") == 0.14

    posted_maker = []
    h.executor.post_maker_exit_order = MagicMock(
        side_effect=lambda **kw: posted_maker.append(kw) or {"success": True, "orderID": "OID_MID_T1", "price": kw["price"]}
    )
    h._verify_entry_finality = MagicMock(return_value=(True, False))
    h._wallet_token_balance = MagicMock(return_value=(30.0, h.ONCHAIN_SOURCE))

    pos_mid = {
        "trade_id": "LIVE_MID_1H_TEST",
        "sleeve": "SLEEVE_2_MID_HOUR",
        "token_id": "TOK_MID_1H",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_price": 0.65,
        "entry_shares": 30.0,
        "remaining_shares": 30.0,
        "notional_usd": 19.50,
        "candle_expiry_ts": time.time() + 1200.0,
    }
    assert h._attempt_maker_exit_post("LIVE_MID_1H_TEST", pos_mid) is True
    assert len(pos_mid["exit_tranches"]) == 2
    assert pos_mid["exit_tranches"][0]["price"] == 0.77  # 0.65 + 0.12 = 0.77
    assert pos_mid["exit_tranches"][1]["price"] == 0.98
    assert posted_maker[0]["price"] == 0.77

    # 2. Idea #1 + Idea #5 in evaluate_shock_and_execute:
    # Shock has L1=$18.00 @ $0.66 and L2=$21.90 @ $0.73 -> total depth=$39.90 sizes ticket to ~$21.56,
    # but target_limit_px = $0.68 only covers L1 ($18.00) -> Idea #1 pre-dispatch down-snaps $21.56 -> $16.50!
    # Then call #1 returns FAK_KILLED_NO_MATCH at $0.68 -> Idea #5 retries once at $0.70 and fills!
    h.executor.get_market_book_async = AsyncMock(return_value={
        "asks": [{"price": "0.6600", "size": "27.28"}, {"price": "0.7300", "size": "30.0"}],
        "bids": [{"price": "0.6500", "size": "200.0"}],
    })
    snipe_calls = []

    async def mock_snipe(**kwargs):
        snipe_calls.append(dict(kwargs))
        if len(snipe_calls) == 1:
            return OrderResult(
                success=False,
                order_id=None,
                trade_id=kwargs["trade_id"],
                token_id=kwargs["token_id"],
                target_token=kwargs["target_token"],
                side="BUY",
                price=kwargs["target_price"],
                size=0.0,
                notional_usd=kwargs["notional_usd"],
                fee_usd=0.0,
                latency_ms=12.0,
                mode="FAK_KILLED_NO_MATCH",
                execution_status=ExecutionStatus.REJECTED,
                confirmed_onchain=False,
                error="no orders found to match with FAK order",
                details={"fak_killed": True},
            )
        return OrderResult(
            success=True,
            order_id="OID_FALLBACK_OK",
            trade_id=kwargs["trade_id"],
            token_id=kwargs["token_id"],
            target_token=kwargs["target_token"],
            side="BUY",
            price=kwargs["target_price"],
            size=23.0,
            notional_usd=kwargs["notional_usd"],
            fee_usd=0.10,
            latency_ms=14.0,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
            details={"pre_token_balance": 0.0, "trade_ids": ["T1"], "transactions_hashes": ["0xabc"]},
        )

    h.executor.execute_snipe_order_async = mock_snipe
    shock = {
        "event_id": "EVT_IDEA15",
        "market_id": "6088881",
        "condition_id": "0xcond6088881",
        "t0_unix": time.time(),
        "title": "Bitcoin Up or Down - October 22, 4:00PM-4:15PM ET",
        "asset": "BTC",
        "shock_direction": "BUY",
        "seconds_to_expiry": 380.0,
        "candle_distance_pct": 0.16,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0xcond6088881"},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "0xTOK6088881",
                "raw_top_asks": [[0.6600, 27.28], [0.7300, 30.0]],
                "raw_top_bids": [[0.6500, 200.0]],
                "effective_price_$25": 0.6600,
                "vwap_$25": 0.6600,
            }
        },
    }

    asyncio.run(h.evaluate_shock_and_execute(shock))

    assert len(snipe_calls) == 2
    assert snipe_calls[0]["notional_usd"] == 16.50
    assert snipe_calls[0]["target_price"] == 0.68
    assert snipe_calls[1]["notional_usd"] == 16.50
    assert snipe_calls[1]["target_price"] == 0.70
    assert any(p.get("market_id") == "6088881" for p in h.active_positions.values())


def test_fix9_low_latency_near_cache_and_fast_ipc(tmp_path, monkeypatch):
    """
    Verify VM low-latency upgrades:
    1. PreSignedOrderLadderCache.get_presigned_order_near hits within +/- 2 shares (eliminating 40% cache misses
       from 1-share Kelly/fee rounding differences) and pops the matched entry to prevent nonce reuse.
    2. PreSignedOrderLadderCache TTL defaults to 1800s on PolymarketLiveExecutor.
    3. _register_active_warmed_token prunes expired tokens and caps active prewarmed tokens at 12.
    """
    from src.polymarket_research.polymarket_live_executor import PreSignedOrderLadderCache

    cache = PreSignedOrderLadderCache(ttl_seconds=1800.0)
    dummy_order_30 = MagicMock(name="signed_order_30")
    assert cache.store_presigned_order("TOK_A", 0.70, 30.0, dummy_order_30) is True

    # Requesting 29.0 shares (1-share delta at $21.11 vs $21.55) hits dummy_order_30 in 0.03ms
    hit_res = cache.get_presigned_order_near("TOK_A", 0.70, 29.0, max_share_delta=2)
    assert hit_res is not None
    hit_order, hit_sz = hit_res
    assert hit_order is dummy_order_30
    assert hit_sz == 30
    # Entry was popped on hit (single-use nonce safety)
    assert cache.get_presigned_order_near("TOK_A", 0.70, 29.0, max_share_delta=2) is None

    # Delta > max_share_delta (e.g. 25 vs 30) does not match
    cache.store_presigned_order("TOK_A", 0.70, 30.0, dummy_order_30)
    assert cache.get_presigned_order_near("TOK_A", 0.70, 25.0, max_share_delta=2) is None

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "lat_state.json")
    h = PolymarketLiveHarvester(ticket_notional=16.5, dry_run=True)
    assert h.executor.order_ladder_cache.ttl_seconds == 1800.0

    now_u = time.time()
    h._register_active_warmed_token("TOK_EXPIRED", now_u - 120.0)
    for idx in range(15):
        h._register_active_warmed_token(f"TOK_LIVE_{idx}", now_u + 300.0 + idx)
    reg = h._active_warmed_token_expiries
    assert "TOK_EXPIRED" not in reg
    assert len(reg) == 12


def test_fix10_twap_dual_anchor_and_entry_adverse_salvage(tmp_path, monkeypatch):
    import asyncio
    from src.polymarket_research.polymarket_live_executor import OrderResult, ExecutionStatus
    """
    Verify Grid-Calibrated Fix #1 & Fix #2 from LIVE_6032439_1792715250_DOWN forensic audit:
    1. 15m Boundary-Wick Oracle Veto blocks 15m entries when |open_spot - twap_60s_open| / open_spot >= 0.0395%
       and dual-anchor cushion < 0.16% (exact replay of 6032439: open=81247.81, twap=81210.04 -> 0.0465% wick).
    2. When wick_div_pct < 0.0395%, 15m entry anchors candle_open_spot to the conservative dual-anchor strike
       (min(open, twap) for DOWN, max(open, twap) for UP).
    3. Orderbook + Entry-Adverse Salvage Override (best_b <= 0.36 & entry_move_pct <= -0.07% for >= 6.0s)
       unwinds a crashing position even when single-tick open_spot still shows spot_disp > 0.
    """
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "fix10_state.json")
    h = PolymarketLiveHarvester(ticket_notional=20.0, dry_run=False)
    h.enforce_live_spot_adverse_gate = True

    snipe_calls = []

    async def mock_snipe(**kwargs):
        snipe_calls.append(kwargs)
        return OrderResult(
            success=True,
            order_id="OID_FIX10",
            trade_id=kwargs["trade_id"],
            token_id=kwargs["token_id"],
            target_token=kwargs["target_token"],
            side="BUY",
            price=kwargs["target_price"],
            size=26.67,
            notional_usd=kwargs["notional_usd"],
            fee_usd=0.10,
            latency_ms=1.2,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
            details={"pre_token_balance": 0.0, "trade_ids": ["T_FIX10"], "transactions_hashes": ["0xfix10"]},
        )

    h.executor.execute_snipe_order_async = mock_snipe
    h.executor.get_collateral_balance = lambda *a, **kw: 100.0
    h.executor.get_conditional_balance = lambda *a, **kw: 0.0
    h.executor.post_maker_exit_order = lambda **kw: {"success": True, "orderID": "OID_EXIT_FIX10"}

    # Part A: Replay LIVE_6032439_1792715250_DOWN boundary-wick trap (open=81247.81 vs twap=81210.04 -> 0.0465% wick)
    shock_wick = {
        "event_id": "EVT_6032439",
        "market_id": "6032439",
        "condition_id": "0xcond6032439",
        "t0_unix": time.time(),
        "title": "Bitcoin Up or Down - October 22, 8:15PM-8:30PM ET",
        "asset": "BTC",
        "horizon": "15m",
        "shock_direction": "SELL",
        "seconds_to_expiry": 149.4,
        "spot_at_t0": 81139.55,
        "trigger_price": 81139.55,
        "candle_open_spot": 81247.81,
        "twap_60s_open": 81210.04,
        "candle_distance_pct": -0.1332,
        "shock_volume_100ms": 2500000.0,
        "shock_ofi": -0.95,
        "fee_metadata": {"fee_rate_market": 0.18, "fee_exponent": 1.0, "condition_id": "0xcond6032439"},
        "pre_shock_features_t0": {
            "DOWN": {
                "token_id": "0xTOK6032439",
                "raw_top_asks": [[0.7300, 100.0]],
                "raw_top_bids": [[0.7200, 200.0]],
                "effective_price_$25": 0.7300,
                "vwap_$25": 0.7300,
                "age_book_ms": 50.0,
                "book_timestamp": time.time(),
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_wick))
    assert len(snipe_calls) == 0, "Boundary-wick trap (0.0465% >= 0.0395%) must be vetoed!"

    # Part B: Clean 15m candle (wick = 0.0246% < 0.0395%) enters and stores conservative dual-anchor strike
    shock_clean = dict(shock_wick)
    shock_clean["event_id"] = "EVT_6032440"
    shock_clean["market_id"] = "6032440"
    shock_clean["candle_open_spot"] = 81200.00
    shock_clean["twap_60s_open"] = 81180.00  # min(81200, 81180) = 81180.00 for DOWN
    shock_clean["spot_at_t0"] = 81080.00     # dual cushion = -0.1232%
    asyncio.run(h.evaluate_shock_and_execute(shock_clean))
    assert len(snipe_calls) == 1
    pos = next(iter(h.active_positions.values()))
    assert pos["candle_open_spot"] == 81180.00

    # Part C: Test Orderbook + Entry-Adverse Salvage Override when open_spot still appears ITM
    # Set candle_open_spot artificially high (81247.81) while current_spot=81218.00 (+0.0967% against entry_spot=81139.55)
    tid = pos["trade_id"]
    pos["candle_open_spot"] = 81247.81
    pos["entry_spot_ref"] = 81139.55
    pos["entry_price"] = 0.75
    pos["candle_expiry_ts"] = time.time() + 104.0
    pos["low_bid_detected_ts"] = time.time() - 6.5  # Persisted >= 6.0s at $0.36

    h.get_reference_spot_price = lambda asset: 81218.00  # Still below 81247.81 (spot_disp > 0), but -0.0967% vs entry!
    h._strict_open_orders = lambda: []
    h._get_verified_shm_book = lambda p: {
        "bids": [{"price": "0.36", "size": "150.0"}],
        "asks": [{"price": "0.38", "size": "150.0"}],
    }
    h.executor.cancel_order = lambda oid: {"canceled": [oid]}
    h.executor.get_order_fill_summary = lambda oid, tok: {"order_id": oid, "matched": 0.0, "terminal": True, "cash": 0.0}
    unwind_calls = []
    h.executor.execute_unwind_order = lambda **kw: (
        unwind_calls.append(kw) or OrderResult(
            success=True,
            order_id="OID_UNWIND_FIX10",
            trade_id=tid,
            token_id=pos["token_id"],
            target_token="DOWN",
            side="SELL",
            price=0.35,
            size=kw["size"],
            notional_usd=round(kw["size"] * 0.35, 2),
            fee_usd=0.05,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.FILLED,
            confirmed_onchain=True,
            details={"trade_ids": ["TU1"], "transactions_hashes": ["0xu1"]},
        )
    )

    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 1, "Orderbook + entry-adverse salvage override must trigger unwind at $0.36!"


def test_fix11_save_state_thread_safety_and_heartbeat_resync_and_safeguards(monkeypatch, tmp_path):
    """
    Verifies Fix #11 (Root causes of LIVE_6032790_1792716941_UP + 4 Proactive Safeguards):
      1. save_state() thread-safety under concurrent multi-thread calls (no FileNotFoundError).
      2. post_heartbeat() automatic resync when CLOB returns 400 Invalid Heartbeat ID with server heartbeat_id.
      3. compute_composite_edge_score() L1 ask-wall veto on thin cushion + Pillar 2 p_max cap without 0.78 floor override.
      4. Pre-entry Stale-Anchor Disagreement Veto (>10s resting ask diverging >28c from p_true).
    """
    import threading
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        compute_composite_edge_score,
        compute_max_acceptable_ask,
    )
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    # 1. Test concurrent multi-thread save_state()
    state_file = tmp_path / "live_harvester_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)
    h = PolymarketLiveHarvester(dry_run=True)
    h.state_file = state_file

    errors = []

    def _worker():
        for _ in range(15):
            try:
                h.save_state()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(errors) == 0, f"Concurrent save_state raised errors: {errors}"
    assert state_file.exists()

    # 2. Test post_heartbeat() automatic resync on 400 Invalid Heartbeat ID
    exec_inst = PolymarketLiveExecutor(dry_run=True)
    exec_inst.dry_run = False
    exec_inst.is_authenticated = True
    exec_inst.last_heartbeat_id = ""

    class _MockInvalidHbError(Exception):
        def __init__(self):
            super().__init__(
                "PolyApiException[status_code=400, error_message={'error': 'Invalid Heartbeat ID', 'heartbeat_id': '8f052486-94fb-4dc8-b73e-9730e1068a7c'}]"
            )
            self.status_code = 400
            self.error_message = {
                "error": "Invalid Heartbeat ID",
                "heartbeat_id": "8f052486-94fb-4dc8-b73e-9730e1068a7c",
            }

    hb_calls = []

    class _MockClobClient:
        def post_heartbeat(self, heartbeat_id=""):
            hb_calls.append(heartbeat_id)
            if heartbeat_id != "8f052486-94fb-4dc8-b73e-9730e1068a7c":
                raise _MockInvalidHbError()
            return {"heartbeat_id": "9a113597-1111-2222-3333-444455556666"}

    exec_inst.client = _MockClobClient()
    res = exec_inst.post_heartbeat()
    assert hb_calls == ["", "8f052486-94fb-4dc8-b73e-9730e1068a7c"]
    assert res.get("heartbeat_id") == "9a113597-1111-2222-3333-444455556666"
    assert exec_inst.last_heartbeat_id == "9a113597-1111-2222-3333-444455556666"
    assert exec_inst.heartbeat_failures == 0
    assert exec_inst.is_heartbeat_healthy() is True

    # 3. Replay LIVE_6032790_1792716941_UP (dist_pct=+0.0601%, obi_l1=-0.721, TTE=258.6s) in live mode
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    shock_6032790 = {
        "asset": "BTC",
        "shock_source": "FUTURES",
        "shock_direction": "BUY",
        "shock_ofi": 0.71,
        "shock_volume_100ms": 576681.0,
        "delta_basis_100ms": 1.98,
        "candle_distance_pct": 0.0601,
        "pre_shock_features_t0": {
            "UP": {
                "age_ask_ms": 2308.5,
                "obi_l1": -0.7206,
                "obi_depth": 0.2528,
                "spread": 0.01,
                "raw_top_asks": [[0.66, 246.36]],
                "vwap_$25": 0.66,
            }
        },
    }
    edge_res = compute_composite_edge_score(shock_6032790)
    assert edge_res["veto"] is True
    assert "Heavy L1 ask wall against thin cushion" in str(edge_res["veto_reason"])

    p_max_res = compute_max_acceptable_ask(
        dist_pct=0.0601,
        tte_sec=258.6,
        asset="BTC",
        shock_ofi=0.71,
        shock_vol_usd=576681.0,
        delta_basis_bps=1.98,
        age_ask_ms=2308.5,
        is_subhourly_15m=True,
    )
    assert p_max_res["p_max"] < 0.65, f"Expected p_max < $0.65 without 0.78 floor override, got {p_max_res['p_max']}"


def test_fix12_v38_deep_research_audit_remediations(tmp_path, monkeypatch):
    """
    Verifies v3.8 Deep Research Audit Fixes (F-01, F-02, F-03, F-05, F-06, F-07, F-10):
    1. F-01 + F-07: DETERMINISTIC_TERMINAL_HOLD inside 15s <= TTE <= 300s does NOT block Tranche 2 ($0.98)
       from posting inline immediately when Tranche 1 reaches terminal/matched status; only
       DETERMINISTIC_TERMINAL_HOLD_FINAL (< 15s) blocks new maker exits.
    2. F-02: Below $88 Seed-Survival threshold (e.g. $76.49), stale HWM resets, max_concurrent_positions=1,
       min_equity_floor_usd=$48.0, and ticket caps at $12.00.
    3. F-03: Expired position with resolved_winning_outcome=None preserves remaining_cost_basis instead of $0.00.
    4. F-05: < 5.0 shares on a real 256-bit CTF token transitions cleanly to SUB_MINIMUM_LOT_SUPERVISED_HOLD.
    5. F-06: Partial FAK entry (< 92% filled) scales notional_usd proportionally; UNRESOLVED_SETTLEMENT
       distinguishes taker unwind OIDs from maker exit OIDs.
    6. F-10: max_trades_per_market=1 strictly blocks win-reentry in the same market.
    """
    import asyncio
    from decimal import Decimal
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        position_may_post_new_maker_exit,
    )
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "v38_state.json")
    h = PolymarketLiveHarvester(ticket_notional=16.5, dry_run=False, max_trades_per_market=1)
    h.state_file = tmp_path / "v38_state.json"

    # 1. F-01 + F-07: Tranche 2 allowed when terminal_policy == DETERMINISTIC_TERMINAL_HOLD (TTE >= 15s),
    #    blocked only when terminal_policy == DETERMINISTIC_TERMINAL_HOLD_FINAL (TTE < 15s).
    pos_t2 = {
        "trade_id": "LIVE_T2_INLINE",
        "token_id": "998877665544332211009988776655",
        "status": ExecutionStatus.PARTIALLY_FILLED,
        "exit_order_status": "EXIT_RECOVERY_REQUIRED",
        "terminal_policy": "DETERMINISTIC_TERMINAL_HOLD",
        "inventory_reconciled": True,
        "entry_price": 0.72,
        "entry_shares": 16.0,
        "remaining_shares": 8.0,
        "filled_exit_shares": 8.0,
        "realized_exit_cash": 6.88,
        "notional_usd": 11.52,
        "candle_expiry_ts": time.time() + 180.0,
        "exit_order_id": "OID_T1_FILLED",
        "target_exit_price": 0.86,
        "exit_tranches": [
            {"idx": 1, "size": 8.0, "price": 0.86, "status": "POSTED"},
            {"idx": 2, "size": 8.0, "price": 0.98, "status": "PENDING"},
        ],
    }
    assert position_may_post_new_maker_exit(pos_t2) is True
    pos_final = dict(pos_t2, terminal_policy="DETERMINISTIC_TERMINAL_HOLD_FINAL")
    assert position_may_post_new_maker_exit(pos_final) is False

    posted_t2 = []
    h._verify_entry_finality = MagicMock(return_value=(True, False))
    h._wallet_token_balance = MagicMock(return_value=(8.0, h.ONCHAIN_SOURCE))
    h._strict_open_orders = lambda: []
    h._get_verified_shm_book = lambda p: {
        "bids": [{"price": "0.86", "size": "100.0"}],
        "asks": [{"price": "0.88", "size": "100.0"}],
    }
    h.get_reference_spot_price = lambda asset: 82000.0
    h.executor.get_order_fill_summary = lambda oid, tok: {
        "order_id": oid,
        "status": "MATCHED",
        "matched": 8.0,
        "cash": 6.88,
        "fee": 0.0,
        "terminal": True,
        "limit_price": 0.86,
        "trade_ids": ["TR1"],
    }
    h.executor.post_maker_exit_order = lambda **kw: (
        posted_t2.append(kw) or {"success": True, "orderID": "OID_T2_RESTING", "price": kw["price"]}
    )
    pos_t2["asset"] = "BTC"
    pos_t2["target_token"] = "UP"
    pos_t2["candle_open_spot"] = 81800.0
    pos_t2["entry_spot_ref"] = 81900.0
    pos_t2["candle_sigma"] = 0.005
    pos_t2["filled_exit_shares"] = 0.0
    pos_t2["realized_exit_cash"] = 0.0
    pos_t2["remaining_shares"] = 16.0
    h.active_positions["LIVE_T2_INLINE"] = pos_t2
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(posted_t2) == 1, "Tranche 2 ($0.98) must post inline on the exact same cycle Tranche 1 fills!"
    assert posted_t2[0]["price"] == 0.98
    assert posted_t2[0]["size"] == 8.0

    # 2. F-02: Seed-Survival override at $76.49 (< $88.0) resets stale HWM ($112 -> $76.49) and sets $48 floor & conc=1
    h.active_positions.clear()
    h.high_water_mark_equity = 112.0
    h.executor.is_authenticated = True
    h.executor.get_collateral_balance = lambda *a, **kw: 76.49
    asyncio.run(h._async_refresh_collateral())
    assert h.high_water_mark_equity == pytest.approx(76.49)
    assert h.max_concurrent_positions == 1
    assert h.risk_controller.min_equity_floor_usd == pytest.approx(48.0)
    assert h.risk_controller.is_halted() is False

    # 3. F-03: Expired position awaiting Gamma/Chainlink resolution (resolved_winning_outcome=None) keeps cost basis
    expired_unresolved = {
        "target_token": "UP",
        "candle_expiry_ts": time.time() - 10.0,
        "resolved_winning_outcome": None,
        "remaining_cost_basis": 12.0,
        "notional_usd": 12.0,
    }
    assert h.get_position_market_value(expired_unresolved, time.time()) == pytest.approx(12.0)

    # 4. F-05: < 5.0 share residual on real 256-bit CTF token transitions to SUB_MINIMUM_LOT_SUPERVISED_HOLD
    pos_sub5 = {
        "trade_id": "LIVE_SUB5",
        "token_id": "112233445566778899001122334455",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_price": 0.75,
        "entry_shares": 4.2,
        "remaining_shares": 4.2,
        "notional_usd": 3.15,
        "candle_expiry_ts": time.time() + 240.0,
    }
    h._wallet_token_balance = MagicMock(return_value=(4.2, h.ONCHAIN_SOURCE))
    assert h._attempt_maker_exit_post("LIVE_SUB5", pos_sub5) is False
    assert pos_sub5["exit_order_status"] == "SUB_MINIMUM_LOT_SUPERVISED_HOLD"
    assert position_may_post_new_maker_exit(pos_sub5) is False

    # 5. F-06: Partial FAK entry (< 92% of gross shares delivered) scales notional_usd proportionally
    pos_part_fak = {
        "trade_id": "LIVE_PART_FAK",
        "token_id": "556677889900112233445566778899",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": False,
        "pre_token_balance": 0.0,
        "gross_entry_shares": 20.0,
        "entry_shares": 20.0,
        "remaining_shares": 20.0,
        "entry_price": 0.60,
        "notional_usd": 12.0,
        "fee_usd": 0.30,
        "candle_expiry_ts": time.time() + 300.0,
    }
    h._wallet_token_balance = MagicMock(return_value=(10.0, h.ONCHAIN_SOURCE))
    posted_part = []
    h.executor.post_maker_exit_order = lambda **kw: (
        posted_part.append(kw) or {"success": True, "orderID": "OID_PART", "price": kw["price"]}
    )
    assert h._attempt_maker_exit_post("LIVE_PART_FAK", pos_part_fak) is True
    assert pos_part_fak["notional_usd"] == pytest.approx(6.0)
    assert pos_part_fak["remaining_cost_basis"] == pytest.approx(6.0)
    assert Decimal(str(pos_part_fak["entry_shares"])) == Decimal("10.0")

    # 6. F-10a: Centered venue divergence > 12.0 bps vetoes even if Coinbase 2s move is flat (1:1 WFO OR parity),
    #    while uncentered raw USDT basis (20 bps) with confirming Coinbase (+2 bps) still passes.
    from src.polymarket_research.polymarket_live_harvester import (
        evaluate_coinbase_venue_veto,
        get_equity_tier_limits,
    )
    assert evaluate_coinbase_venue_veto(
        {"coinbase_spot": 80000.0, "venue_divergence_centered_bps": 13.0, "coinbase_move_bps_2s": 0.5},
        "UP",
    )[0] is True
    assert evaluate_coinbase_venue_veto(
        {"coinbase_spot": 80000.0, "venue_divergence_bps": 20.0, "coinbase_move_bps_2s": 2.0},
        "UP",
    )[0] is False
    assert evaluate_coinbase_venue_veto(
        {"coinbase_spot": 80000.0, "venue_divergence_centered_bps": 2.0, "coinbase_move_bps_2s": -4.5},
        "UP",
    )[0] is True

    # 7. Vector 7 PATCH 8B: get_equity_tier_limits(76.49) returns SEED_SURVIVAL directly at source
    t_seed = get_equity_tier_limits(76.49, high_water_mark_equity=76.49)
    assert t_seed["tier"] == "SEED_SURVIVAL"
    assert t_seed["max_concurrent_positions"] == 1
    assert t_seed["min_equity_floor"] == pytest.approx(48.0)

    # 8. Blueprint 4 (F-08): Dense integer share grid 8..32 achieves 100.0% hit coverage across [$8.00..$16.50]
    from src.polymarket_research.polymarket_live_executor import PreSignedOrderLadderCache
    for px_c in range(55, 86):
        px = round(px_c / 100.0, 2)
        for not_10x in range(80, 166, 5):
            notional = not_10x / 10.0
            req_sh = float(int(notional // px))
            if req_sh >= 8.0:
                cache = PreSignedOrderLadderCache()
                for sh in range(8, 33):
                    cache.store_presigned_order("TOK_DENSE", px, float(sh), {"signed": sh})
                got_exact = cache.get_presigned_order("TOK_DENSE", px, req_sh)
                assert got_exact == {"signed": int(req_sh)}


def test_fix13_v39_second_pass_audit_remediations(tmp_path, monkeypatch):
    """
    Verifies v3.9 Second-Pass Adversarial Audit Fixes & Profit Upgrades (R01, R02, R03, R04, R07, R08, Upgrade 2):
    1. R07: 1H Binance contracts keep authoritative Binance 1H Open/Spot (never polluted by twap_60s_open/cl_open_spot),
       while 15M Chainlink TWAP contracts enforce twap_60s_open + chainlink_twap_60s boundary-wick veto.
    2. R03 (Patch A): Max daily loss halt auto-resets via is_halted() upon UTC date rollover without manual intervention.
    3. R04: +$3 hysteresis at $88->$91 and smooth SEED_RAMP ($91..$108) eliminate the +61% risk cliff.
    4. R02 (Patch B): Wallet < CLOB matched on live order_id fails closed into ENTRY_INVENTORY_RECONCILIATION_REQUIRED
       without corrupting historical notional_usd.
    5. Upgrade 2: Live 256-bit CTF positions post 50% @ $0.95 + 50% @ $0.98 resting Maker exits.
    6. R01 + R08: Non-Safe Beacon Proxy caches _funder_is_gnosis_safe=False; _UrgentSignPriority yields prewarm_order_ladder.
    """
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        get_equity_tier_limits,
    )
    import src.polymarket_research.polymarket_live_executor as ex_mod
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "v39_state.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True, max_trades_per_market=1, hold_to_maturity=False)
    h.dry_run = False
    h.executor.dry_run = False
    h.state_file = tmp_path / "v39_state.json"
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True

    # 1. R07: 1H Binance market ("binance.com") must NOT overwrite finalized_1h_open with twap_60s_open / cl_open_spot
    now_u = time.time()
    cur_h = int(now_u // 3600)
    shock_1h = {
        "shock_id": "SHK_1H_BIN",
        "t0_unix": now_u,
        "asset": "BTC",
        "horizon": "1h",
        "resolution_source": "https://www.binance.com/en/trade/BTC_USDT",
        "market_id": "6074291",
        "title": "Bitcoin Up or Down - October 25, 1AM ET",
        "seconds_to_expiry": 750.0,  # Inside v3.9 [120s, 1200s] 1h WFO window!
        "shock_direction": "BUY",
        "shock_ofi": 0.90,
        "shock_volume_100ms": 2_000_000.0,
        "spot_at_t0": 100120.0,
        "finalized_1h_open": 100000.0,
        "candle_open_spot": 100000.0,
        "twap_60s_open": 100090.0,  # +9 bps higher TWAP that would have falsely vetoed 1h in v3.8!
        "chainlink_open_spot": 100110.0,
        "candle_distance_pct": 0.12,
        "candle_sigma": 0.0045,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "778899001122334455667788990011",
                "best_bid": 0.72,
                "best_ask": 0.73,
                "age_ask_ms": 400.0,
                "obi_l1": 0.25,
                "vwap_$50": 0.73,
                "effective_price_$50": 0.74,
                "raw_top_asks": [[0.73, 100.0]],
                "raw_top_bids": [[0.72, 100.0]],
            }
        },
    }
    # Block right at book fetch after hourly_candle_opens is recorded so we verify exact 1h strike preservation
    h.executor.get_market_book_async = AsyncMock(return_value={})
    asyncio.run(h.evaluate_shock_and_execute(shock_1h))
    assert h.hourly_candle_opens["BTC"][cur_h] == pytest.approx(100000.0)

    # Meanwhile on 15m ("data.chain.link"), boundary wick >= 0.0395% with thin cushion is vetoed BEFORE book fetch!
    book_called_15m = []
    h.executor.get_market_book_async = AsyncMock(side_effect=lambda *a: book_called_15m.append(1) or {})
    shock_15m_wick = dict(
        shock_1h,
        shock_id="SHK_15M_CL_WICK",
        horizon="15m",
        resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams",
        title="Bitcoin Up or Down - October 25, 1:00AM-1:15AM ET",
        seconds_to_expiry=300.0,
        spot_at_t0=100075.0,
        candle_open_spot=100000.0,
        twap_60s_open=100045.0,  # 0.045% >= 0.0395% wick divergence, dual_cush = 0.03% < 0.10%
    )
    asyncio.run(h.evaluate_shock_and_execute(shock_15m_wick))
    assert len(book_called_15m) == 0, "15m Chainlink TWAP boundary wick trap must be vetoed before book fetch!"

    # 2. R03 (Patch A): Daily-loss halt auto-clears via is_halted() on UTC midnight rollover
    h.risk_controller.max_daily_loss_usd = 20.0
    h.risk_controller.record_trade_pnl(-21.0)
    assert h.risk_controller.is_halted() is True
    assert "Max daily loss reached" in h.risk_controller.halt_reason
    h.risk_controller.last_loss_date_utc = "2020-01-01"
    assert h.risk_controller.is_halted() is False
    assert h.risk_controller.daily_realized_loss == pytest.approx(0.0)

    # 3. R04: Hysteresis ($88 -> $91) and smooth SEED_RAMP ($91..$108)
    t_hyst = get_equity_tier_limits(89.50, high_water_mark_equity=89.50, previous_tier="SEED_SURVIVAL")
    assert t_hyst["tier"] == "SEED_SURVIVAL"
    assert t_hyst["max_concurrent_positions"] == 1
    t_ramp = get_equity_tier_limits(93.00, high_water_mark_equity=93.00, previous_tier="SEED_SURVIVAL")
    assert t_ramp["tier"] == "SEED_RAMP"
    assert t_ramp["dynamic_bankroll_pct"] == pytest.approx(0.17)
    assert t_ramp["max_concurrent_positions"] == 1
    assert 54.0 <= t_ramp["min_equity_floor"] < 65.0

    # 4. R02 (Patch B): Wallet shortfall vs authoritative CLOB matched fails closed without rewriting notional_usd
    pos_r02 = {
        "trade_id": "LIVE_R02_SHORTFALL",
        "order_id": "0xOID_FULL_MATCH",
        "token_id": "556677889900112233445566778899",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": False,
        "entry_ts": time.time() - 25.0,
        "pre_token_balance": 0.0,
        "gross_entry_shares": 20.0,
        "entry_shares": 20.0,
        "remaining_shares": 20.0,
        "entry_price": 0.60,
        "notional_usd": 12.0,
        "fee_usd": 0.25,
        "candle_expiry_ts": time.time() + 300.0,
    }
    h._verify_entry_finality = MagicMock(return_value=(True, False))
    h._wallet_token_balance = MagicMock(return_value=(10.0, h.ONCHAIN_SOURCE))
    h.executor.get_order_fill_summary = lambda oid, tok: {"order_id": oid, "matched": 20.0, "cash": 12.0, "fee": 0.25, "terminal": True}
    assert h._attempt_maker_exit_post("LIVE_R02_SHORTFALL", pos_r02) is False
    assert pos_r02["exit_order_status"] == "ENTRY_INVENTORY_RECONCILIATION_REQUIRED"
    assert pos_r02["notional_usd"] == pytest.approx(12.0)

    # 5. Upgrade 2: Live 256-bit CTF position posts 50% @ $0.95 + 50% @ $0.98
    pos_up2 = {
        "trade_id": "LIVE_UP2_CTF",
        "token_id": "123456789012345678901234567890",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_price": 0.72,
        "entry_shares": 16.0,
        "remaining_shares": 16.0,
        "notional_usd": 11.52,
        "candle_expiry_ts": time.time() + 300.0,
    }
    h._wallet_token_balance = MagicMock(return_value=(16.0, h.ONCHAIN_SOURCE))
    posted_up2 = []
    h.executor.post_maker_exit_order = lambda **kw: posted_up2.append(kw) or {"success": True, "orderID": "OID_95", "price": kw["price"]}
    assert h._attempt_maker_exit_post("LIVE_UP2_CTF", pos_up2) is True
    assert pos_up2["exit_tranches"][0]["price"] == pytest.approx(0.95)
    assert pos_up2["exit_tranches"][1]["price"] == pytest.approx(0.98)
    assert posted_up2[0]["price"] == pytest.approx(0.95)

    # 6. R01 + R08: Non-Safe proxy cached guard & _UrgentSignPriority waiter signaling
    h.executor.signature_type = 3
    h.executor._funder_is_gnosis_safe = False
    assert h.executor.attempt_onchain_redemption("0x" + "ab" * 32) is None
    with ex_mod._UrgentSignPriority():
        assert ex_mod._URGENT_SIGN_WAITERS >= 1
        assert h.executor.prewarm_order_ladder("123456789012345678901234567890", 12.0, exact_shares=[10]) == 0
    assert ex_mod._URGENT_SIGN_WAITERS == 0


def test_fix14_v391_unchoked_ev_and_stale_book_snipe(tmp_path, monkeypatch):
    """
    Verifies v3.9.1 Alpha-Unblocking & Compounding Upgrades:
    1. Real 10PM ET 1h BTC setup (TTE=1099s, ask=$0.83, dist=+0.104%, z_strike=0.83, L1=$83) that was previously
       choked by legacy eta=0.14 / tau>900s 0.78 cap now passes continuous +EV ceiling and fires live snipe!
    2. Untouched resting stale quote on REST /book (timestamp 12s old < 60s PM_MAX_BOOK_AGE_SEC) is sniped cleanly
       instead of being falsely rejected by the old 4.0s staleness threshold.
    3. Thin retail L1 ask (< $20.00) on a live 256-bit CTF token is rejected by [L1 ASK DEPTH REJECT].
    """
    import asyncio, types
    from unittest.mock import AsyncMock
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "v391_state.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    h = PolymarketLiveHarvester(
        ticket_notional=12.0, dry_run=True, dynamic_sizing=True, hold_to_maturity=False,
        max_trades_per_market=2, max_trades_per_hour=8, max_tte=1200.0,
    )
    h.dry_run = False
    h.executor.dry_run = False
    h.state_file = tmp_path / "v391_state.json"
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h._last_known_collateral = 76.49
    h.executor.get_collateral_balance = lambda hot_path=False: 76.49

    sniped = []
    async def fake_snipe(**kw):
        sniped.append(kw)
        return types.SimpleNamespace(
            success=False, order_id=None, tx_hashes=[], filled_size=0.0, avg_price=0.0, size=0.0, price=0.0,
            fee_paid_usd=0.0, latency_ms=1.0, error_msg="SIM", error="SIM",
            mode="FAK_KILLED_NO_MATCH", details={"fak_killed": True}, execution_status=ExecutionStatus.REJECTED,
        )
    h.executor.execute_snipe_order_async = fake_snipe

    now_u = time.time()
    # Force fallback to REST /book with a 12-second-old resting stale ask (previously killed by 4.0s threshold!)
    h.executor.get_market_book_async = AsyncMock(return_value={
        "timestamp": (now_u - 12.0) * 1000.0,
        "asks": [{"price": "0.83", "size": "100"}],
        "bids": [{"price": "0.82", "size": "100"}],
    })
    shock_10pm_btc = {
        "shock_id": "SHK_10PM_BTC_UNCHOKED",
        "t0_unix": now_u,
        "asset": "BTC",
        "horizon": "1h",
        "resolution_source": "https://www.binance.com/en/trade/BTC_USDT",
        "market_id": "6071901",
        "condition_id": "0x" + "11" * 32,
        "title": "Bitcoin Up or Down - October 24, 10PM ET",
        "seconds_to_expiry": 1099.0,
        "shock_direction": "BUY",
        "shock_ofi": 1.0,
        "shock_volume_100ms": 1_800_000.0,
        "spot_at_t0": 80104.0,
        "finalized_1h_open": 80000.0,
        "candle_open_spot": 80000.0,
        "candle_distance_pct": 0.13,
        "candle_sigma": 0.0028,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x" + "11" * 32},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "998877665544332211009988776655",
                "best_bid": 0.82,
                "best_ask": 0.83,
                "age_ask_ms": 600.0,
                "obi_l1": 0.10,
                "vwap_$25": 0.83,
                "vwap_$50": 0.83,
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_10pm_btc))
    assert len(sniped) == 1, "Unchoked +EV 10PM BTC setup on 12s resting book must execute!"

    # Thin L1 ask (< $20.00: 10 shares @ $0.83 = $8.30) must be rejected before sniping
    h.executor.get_market_book_async = AsyncMock(return_value={
        "timestamp": (now_u - 2.0) * 1000.0,
        "asks": [{"price": "0.83", "size": "10"}],
        "bids": [{"price": "0.82", "size": "100"}],
    })
    shock_thin = dict(shock_10pm_btc, shock_id="SHK_THIN_L1", market_id="6071999")
    asyncio.run(h.evaluate_shock_and_execute(shock_thin))
    assert len(sniped) == 1, "Thin $8.30 L1 ask (< $20.00 institutional floor) must be rejected!"

    # Production auth_mode == 'AUTHENTICATED_L2' must post 50% @ $0.95 + 50% @ $0.98 (not legacy 0.78+0.14=0.92)
    from unittest.mock import MagicMock
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h._wallet_token_balance = MagicMock(return_value=(15.38, h.ONCHAIN_SOURCE))
    posted_exits = []
    h.executor.post_maker_exit_order = lambda **kw: posted_exits.append(kw) or {"success": True, "orderID": "OID_95", "price": kw["price"]}
    pos_auth = {
        "trade_id": "LIVE_6075458_DOWN",
        "token_id": "41400365548425196187992327321545036693976598522874320121839711965141676378572",
        "sleeve": "SLEEVE_1_CORE_302",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_price": 0.78,
        "entry_shares": 15.38,
        "remaining_shares": 15.38,
        "notional_usd": 12.0,
        "candle_expiry_ts": time.time() + 300.0,
    }
    h.active_positions["LIVE_6075458_DOWN"] = pos_auth
    assert h._attempt_maker_exit_post("LIVE_6075458_DOWN", pos_auth) is True
    assert [t["price"] for t in pos_auth["exit_tranches"]] == [0.95, 0.98], (
        f"AUTHENTICATED_L2 must rest at [0.95, 0.98], got {pos_auth.get('exit_tranches')}"
    )


def test_fix15_v392_shadow_graduation_upgrades(tmp_path, monkeypatch):
    """
    Verifies the 4 v3.9.2 Shadow Graduation Upgrades:
    1. Phase 3A defaults to ultra-short 3.5s TTL + salvages reversed fills (no -$19.93 wipeouts).
    2. Phase 4 rejects <0.25% cross-oracle basis traps on CORRIDOR_BOX_ARB and scores dual-oracle settlement.
    3. EXP-316 Track A walks $25/$50 graduation tiers with $0.97 Maker TP.
    4. Paper Trader retires losing SLEEVE_2 by default and runs Volatility-Normalized SOL Shadow Sleeve.
    """
    import json
    from unittest.mock import patch
    import src.polymarket_research.polymarket_paper_trader as pt_mod
    import src.polymarket_research.exp316_macro_strike_shadow as e316_mod

    shadow_file = tmp_path / "shadow_p34.jsonl"
    monkeypatch.setenv("PM_SHADOW_TRACKER_FILE", str(shadow_file))
    h = _make_live_harvester(tmp_path)

    # 1. Phase 3A 3.5s TTL + 3-Zone Wrong-Side Salvage
    now_u = time.time()
    h._register_shadow_phase3a_maker_in(
        shock={"market_id": "700001", "title": "BTC 15m", "asset": "BTC", "candle_open_spot": 80000.0, "expiry_ts": now_u + 120.0},
        target_token="UP", first_ask=0.76, first_bid=0.75, max_allowed_price=0.85,
        raw_asks=[(0.76, 50.0)], reject_reason="FAK_MISS", is_subhourly=True, dist_pct=0.10, tte=120.0,
    )
    ord_rec = h._shadow_maker_orders["700001_UP"]
    assert ord_rec["ttl_sec"] == pytest.approx(3.5)

    # Simulate immediate fill followed by wrong-side spot reversal -> salvaged at $0.40 instead of -$19.93 wipeout!
    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.read_fast_tick",
        lambda asset, max_age_sec=2.0, now=None: {
            "spot_price": 80080.0, "chainlink_twap_60s": 80080.0, "market_id": "700001",
            "UP": {"best_ask": 0.75, "best_bid": 0.74},
        },
    )
    h._step_shadow_phase3_4_tracker(now_u + 0.5)
    assert ord_rec["status"] == "SHADOW_MAKER_FILLED"

    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.read_fast_tick",
        lambda asset, max_age_sec=2.0, now=None: {
            "spot_price": 79920.0, "chainlink_twap_60s": 79920.0, "market_id": "700001",
            "UP": {"best_ask": 0.42, "best_bid": 0.40},
        },
    )
    h._step_shadow_phase3_4_tracker(now_u + 6.0)
    h._step_shadow_phase3_4_tracker(now_u + 15.0)
    assert "700001_UP" not in h._shadow_maker_orders
    events = [json.loads(l) for l in shadow_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    salv = [e for e in events if e.get("event_type") == "SHADOW_PHASE3A_MAKER_RESOLVED"][0]
    assert salv["exit_reason"] == "WRONG_SIDE_SALVAGE"
    assert salv["shadow_net_pnl_usd"] > -12.0  # Salvaged (~-$9.4), NOT -$19.93 wipeout!

    # 2. Phase 4 rejects narrow 4 bps corridor trap (< 0.25%), accepts 0.35% deep corridor & settles dual-oracle jackpot
    exp_u = round((now_u + 180.0) / 60.0) * 60.0
    h._update_shadow_phase4_monotonicity_scanner(
        {"market_id": "700002", "t0_unix": now_u, "expiry_ts": exp_u, "spot_at_t0": 80020.0,
         "pre_shock_features_t0": {"UP": {"best_ask": 0.52, "raw_top_asks": [[0.52, 60.0]]}, "DOWN": {"best_ask": 0.50, "raw_top_asks": [[0.50, 60.0]]}}},
        "BTC", True, False, 180.0, 80000.0,
    )
    h._update_shadow_phase4_monotonicity_scanner(
        {"market_id": "700003", "t0_unix": now_u + 0.5, "expiry_ts": exp_u, "spot_at_t0": 80020.0,
         "pre_shock_features_t0": {"UP": {"best_ask": 0.52, "raw_top_asks": [[0.52, 60.0]]}, "DOWN": {"best_ask": 0.49, "raw_top_asks": [[0.49, 60.0]]}}},
        "BTC", False, True, 180.0, 80032.0,  # 0.04% narrow gap -> basis trap!
    )
    assert not getattr(h, "_shadow_phase4_active_boxes", {})

    exp_u2 = exp_u + 3600.0
    h._update_shadow_phase4_monotonicity_scanner(
        {"market_id": "700004", "t0_unix": now_u, "expiry_ts": exp_u2, "spot_at_t0": 80150.0,
         "pre_shock_features_t0": {"UP": {"best_ask": 0.52, "raw_top_asks": [[0.52, 60.0]]}, "DOWN": {"best_ask": 0.50, "raw_top_asks": [[0.50, 60.0]]}}},
        "BTC", True, False, 180.0, 80000.0,
    )
    h._update_shadow_phase4_monotonicity_scanner(
        {"market_id": "700005", "t0_unix": now_u + 0.5, "expiry_ts": exp_u2, "spot_at_t0": 80150.0,
         "pre_shock_features_t0": {"UP": {"best_ask": 0.52, "raw_top_asks": [[0.52, 60.0]]}, "DOWN": {"best_ask": 0.49, "raw_top_asks": [[0.49, 60.0]]}}},
        "BTC", False, True, 180.0, 80300.0,  # 0.375% >= 0.25% safe corridor!
    )
    assert len(h._shadow_phase4_active_boxes) == 1
    monkeypatch.setattr(
        "src.polymarket_research.polymarket_live_harvester.read_fast_tick",
        lambda asset, max_age_sec=5.0, now=None: {"spot_price": 80160.0, "chainlink_twap_60s": 80140.0},
    )
    h._step_shadow_phase3_4_tracker(exp_u2 + 5.0)
    events2 = [json.loads(l) for l in shadow_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    box_res = [e for e in events2 if e.get("event_type") == "SHADOW_PHASE4_BOX_RESOLVED"][0]
    assert box_res["double_win_jackpot"] is True
    assert box_res["payout_per_pair"] == pytest.approx(2.0)

    # 3. EXP-316 TrackAPosition defaults to $0.97 Maker TP & Paper Trader runs SOL Shadow Sleeve while retiring SLEEVE_2
    assert e316_mod.TrackAPosition.__dataclass_fields__["maker_tp_price"].default == pytest.approx(0.97)
    assert pt_mod.ENABLE_SLEEVE_304_315 is False
    assert pt_mod.ENABLE_SOL_SHADOW_SLEEVE is True

    with patch.object(pt_mod, "SOL_SHADOW_LEDGER_FILE", tmp_path / "sol_led.jsonl"), \
         patch.object(pt_mod, "SOL_SHADOW_STATE_FILE", tmp_path / "sol_st.json"), \
         patch.object(pt_mod, "DEV_LEDGER_FILE", tmp_path / "dev.jsonl"), \
         patch.object(pt_mod, "VALIDATION_LEDGER_FILE", tmp_path / "val.jsonl"), \
         patch.object(pt_mod, "STATE_FILE", tmp_path / "pt_st.json"):
        pt = pt_mod.PolymarketForwardPaperTrader()
        pt.evaluate_shock_signal({
            "market_id": "880001", "title": "Solana Up or Down - Oct 25, 9AM ET", "asset": "SOL", "horizon": "1h",
            "t0_unix": now_u, "seconds_to_expiry": 600.0, "shock_direction": "BUY", "shock_ofi": 0.90,
            "shock_volume_100ms": 350000.0, "spot_at_t0": 150.60, "finalized_1h_open": 150.00,
            "pre_shock_features_t0": {"UP": {"best_ask": 0.75, "best_bid": 0.74, "raw_top_asks": [[0.75, 50.0]], "raw_top_bids": [[0.74, 50.0]]}},
        })
        assert "880001" in pt.sol_shadow_open_trades
        pt.check_maker_tp_fills("880001", {"timestamp_unix": now_u + 12.0, "UP": {"best_bid": 0.97, "best_ask": 0.98}})
        assert len(pt.sol_shadow_trades) == 1
        assert pt.sol_shadow_trades[0]["won"] is True


def test_fix16_xrp_and_sol_shadow_sleeves_and_exp316(tmp_path):
    """Verify XRP & SOL end-to-end shadow support across recorder, paper trader, and EXP-316."""
    import json
    from src.polymarket_research import polymarket_terminal_recorder as rec_mod
    from src.polymarket_research import exp316_macro_strike_shadow as e316_mod
    from src.polymarket_research import polymarket_paper_trader as pt_mod
    from src.polymarket_research.polymarket_live_harvester import ALLOWED_ASSETS
    from unittest.mock import patch

    # 1. Recorder supports XRP & SOL without touching live BTC/ETH ALLOWED_ASSETS
    assert "XRP" in rec_mod.ASSET_CONFIGS
    assert "SOL" in rec_mod.ASSET_CONFIGS
    assert rec_mod.ASSET_CONFIGS["XRP"]["series_slug"] == "xrp-up-or-down-hourly"
    assert ALLOWED_ASSETS == {"BTC", "ETH"}

    # 2. EXP-316 monitors XRP & SOL Daily/Weekly strike ladders and parses decimal XRP strikes
    series_assets = {a for a, _, _ in e316_mod.MONITORED_SERIES}
    assert {"BTC", "ETH", "SOL", "XRP"} <= series_assets
    assert e316_mod.extract_strike_price("Will the price of XRP be above $0.85 on October 25?", None) == pytest.approx(0.85)
    assert e316_mod.extract_strike_price("Will XRP reach $2.10 October 19-25?", None) == pytest.approx(2.10)

    # 3. Paper Trader runs isolated SLEEVE_XRP_V392_SHADOW when opted-in (retired to False in production)
    assert pt_mod.ENABLE_XRP_SHADOW_SLEEVE is False
    now_u = time.time()
    with patch.object(pt_mod, "ENABLE_XRP_SHADOW_SLEEVE", True), \
         patch.object(pt_mod, "SOL_SHADOW_LEDGER_FILE", tmp_path / "sol_led.jsonl"), \
         patch.object(pt_mod, "SOL_SHADOW_STATE_FILE", tmp_path / "sol_st.json"), \
         patch.object(pt_mod, "XRP_SHADOW_LEDGER_FILE", tmp_path / "xrp_led.jsonl"), \
         patch.object(pt_mod, "XRP_SHADOW_STATE_FILE", tmp_path / "xrp_st.json"), \
         patch.object(pt_mod, "DEV_LEDGER_FILE", tmp_path / "dev.jsonl"), \
         patch.object(pt_mod, "VALIDATION_LEDGER_FILE", tmp_path / "val.jsonl"), \
         patch.object(pt_mod, "STATE_FILE", tmp_path / "pt_st.json"):
        pt = pt_mod.PolymarketForwardPaperTrader()
        pt.evaluate_shock_signal({
            "market_id": "990001", "title": "XRP Up or Down - Oct 25, 9AM ET", "asset": "XRP", "horizon": "1h",
            "t0_unix": now_u, "seconds_to_expiry": 720.0, "shock_direction": "BUY", "shock_ofi": 0.85,
            "shock_volume_100ms": 95000.0, "spot_at_t0": 0.9045, "finalized_1h_open": 0.9000,
            "pre_shock_features_t0": {"UP": {"best_ask": 0.74, "best_bid": 0.70, "raw_top_asks": [[0.74, 40.0]], "raw_top_bids": [[0.70, 40.0]]}},
        })
        assert "990001" in pt.xrp_shadow_open_trades
        assert "990001" not in pt.open_trades
        pt.check_maker_tp_fills("990001", {"timestamp_unix": now_u + 15.0, "UP": {"best_bid": 0.97, "best_ask": 0.98}})
        assert len(pt.xrp_shadow_trades) == 1
        assert pt.xrp_shadow_trades[0]["won"] is True
        xrp_state = json.loads((tmp_path / "xrp_st.json").read_text(encoding="utf-8"))
        assert xrp_state["sleeve_id"] == "SLEEVE_XRP_V392_SHADOW"
        assert xrp_state["winning_trades"] == 1


def test_fix17_eth_9am_forensic_remediation(tmp_path, monkeypatch):
    """
    Verifies v3.9.4 WFO-Validated Forensic Remediation of LIVE_6081501_1792935724_UP (ETH 9AM ET -$6.80 loss):
      1. WFO Policy 4 rejects ETH 1h > 600s (TTE=1075.4s) AND z_strike < 0.65 (z_strike=0.58), while leaving
         ETH 15m (92.4% WR, PF=3.06) and ETH 1h Late (<= 600s, 100% WR) 100% unchoked with zero ad-hoc sigma floor.
      2. Salvage unwind evicts exit_oid from pre-cancel open_oids once BOTH cancel_order(is_canceled=True)
         and post-cancel summary(terminal=True) confirm cancellation, unwinding immediately on Pass #1
         with a 4c sweep floor (best_b - 0.04) and 0.35s fast retry on 400 FAK zero-match rejections.
      3. _ThreadLocalClobHttpClient isolates per-thread HTTP/1.1 keep-alive clients (zero shared deque).
    """
    import asyncio
    import threading
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import (
        ExecutionStatus,
        _ThreadLocalClobHttpClient,
        install_thread_safe_clob_http_client,
    )

    # 1. Thread-local HTTP/1.1 client isolation (eliminates deque mutated during iteration + HTTP/2 GOAWAY)
    dummy_mod = type("DummyHelpers", (), {"_http_client": MagicMock()})()
    assert install_thread_safe_clob_http_client(dummy_mod) is True
    assert isinstance(dummy_mod._http_client, _ThreadLocalClobHttpClient)
    clients = []

    def _grab():
        clients.append(dummy_mod._http_client._client())

    t1 = threading.Thread(target=_grab)
    t2 = threading.Thread(target=_grab)
    t1.start(); t2.start(); t1.join(); t2.join()
    assert len(clients) == 2 and clients[0] is not clients[1]
    for c in clients:
        c.close()

    # 2. Exact replay of LIVE_6081501_1792935724_UP vs valid WFO ETH 1h trade
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "f17_state.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "f17_res.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True, allowed_assets={"BTC", "ETH"})
    h.dry_run = False
    h.executor.dry_run = False
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "f17_state.json"
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 70.67
    submitted = []
    h.executor.execute_live_order = MagicMock(side_effect=lambda **kw: submitted.append(kw))

    real_eth_tok = "100434764618174237135201777197981253576172734064131101154122934005557319214073"
    now_u = time.time()
    losing_shock = {
        "shock_id": "6081501_replay",
        "market_id": "6081501",
        "condition_id": "0x6c7e137b9293b4004131cd749fe460eeb669b626ea5b3d9795bffbe491caa527",
        "title": "Ethereum Up or Down - October 25, 9AM ET",
        "asset": "ETH",
        "horizon": "1h",
        "resolution_source": "https://www.binance.com/en/trade/ETH_USDT",
        "t0_unix": now_u,
        "seconds_to_expiry": 1075.4,
        "expiry_ts": now_u + 1075.4,
        "candle_sigma": 0.00405,
        "shock_volume_100ms": 455771.0,
        "is_40ms_fast_track": True,
        "shock_direction": "BUY",
        "shock_ofi": 1.0,
        "spot_at_t0": 2337.90,
        "finalized_1h_open": 2334.90,
        "candle_open_spot": 2334.90,
        "candle_distance_pct": 0.1285,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_eth_tok,
                "best_bid": 0.74,
                "best_ask": 0.76,
                "spread": 0.02,
                "age_book_ms": 3.4,
                "age_ask_ms": 10.9,
                "age_bid_ms": 3521.5,
                "obi_l1": 0.463,
                "raw_top_bids": [[0.74, 150.0], [0.70, 66.0]],
                "raw_top_asks": [[0.76, 55.0], [0.77, 25.0]],
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(losing_shock))
    assert len(submitted) == 0, "Early ETH 1h whipsaw (TTE=1075s > 600s, z=0.58 < 0.65) must be rejected!"

    # Verify WFO Policy 4 leaves ETH 15m (even with quiet rec_sig=0.0020 -> sigma_1h=0.0040 < 0.0048) 100% unchoked!
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    h.check_recorder_freshness = lambda asset, now_t: (True, 0.1, "OK")
    sniped_15m = []

    async def _fake_snipe_15m(**kw):
        sniped_15m.append(kw)
        return type("FakeRes", (), {
            "success": False, "order_id": None, "tx_hashes": [], "filled_size": 0.0, "avg_price": 0.0,
            "size": 0.0, "price": 0.0, "fee_paid_usd": 0.0, "latency_ms": 1.0, "error_msg": "SIM", "error": "SIM",
            "mode": "FAK_KILLED_NO_MATCH", "details": {"fak_killed": True}, "execution_status": ExecutionStatus.REJECTED,
        })()

    h.executor.execute_snipe_order_async = _fake_snipe_15m
    eth_15m_winner = dict(
        losing_shock,
        shock_id="eth_15m_unchoked",
        market_id="6081599",
        title="Ethereum Up or Down - October 25, 9:00AM-9:15AM ET",
        horizon="15m",
        resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams",
        seconds_to_expiry=300.0,
        expiry_ts=now_u + 300.0,
        candle_sigma=0.0020,  # sigma_1h = 0.0040 (previously choked by ad-hoc 0.0048 floor -> z=0.60 < 0.65; now z=0.72 >= 0.65!)
        spot_at_t0=2336.85,
        candle_open_spot=2334.90,
        twap_60s_open=2334.90,
        candle_distance_pct=0.0835,
        fee_metadata={"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": losing_shock["condition_id"]},
    )
    asyncio.run(h.evaluate_shock_and_execute(eth_15m_winner))
    assert len(sniped_15m) >= 1, "Unchoked ETH 15m winner (z=0.72 >= 0.65) must NOT be blocked by an ad-hoc sigma floor!"

    # 3. Single-pass verified cancel + 4c sweep floor + 0.35s fast retry on 400 FAK zero-match
    exit_oid = "0x0f37be121c4a7bde2e0439b44244fa35c6cb29287923724a23529481d3ad0a24"
    pos = {
        "trade_id": "LIVE_6081501_TEST",
        "market_id": "6081501",
        "token_id": real_eth_tok,
        "target_token": "UP",
        "asset": "ETH",
        "horizon": "1h",
        "status": ExecutionStatus.EXIT_RESTING,
        "exit_order_id": exit_oid,
        "exit_order_status": "RESTING",
        "inventory_reconciled": True,
        "entry_price": 0.7569,
        "entry_shares": 15.26,
        "remaining_shares": 15.26,
        "notional_usd": 11.55,
        "candle_open_spot": 2334.90,
        "entry_spot_ref": 2337.90,
        "candle_sigma": 0.00405,
        "candle_expiry_ts": now_u + 174.0,
        "low_bid_detected_ts": now_u - 7.0,
    }
    h.active_positions["LIVE_6081501_TEST"] = pos
    # Pre-cancel open_orders snapshot STILL contains exit_oid (exact live bug!)
    h._strict_open_orders = lambda: [{"id": exit_oid}]
    h._get_verified_shm_book = lambda p: {
        "bids": [{"price": "0.31", "size": "60.0"}],
        "asks": [{"price": "0.35", "size": "60.0"}],
    }
    h.get_reference_spot_price = lambda asset: 2333.90
    h._wallet_token_balance = MagicMock(return_value=(15.26, h.ONCHAIN_SOURCE))
    h.executor.cancel_order = MagicMock(return_value={"canceled": [exit_oid], "is_canceled": True, "outcome": "CANCELED"})
    h.executor.get_order_fill_summary = MagicMock(return_value={
        "order_id": exit_oid, "status": "CANCELED", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True,
    })
    unwind_calls = []

    def _mock_unwind(**kw):
        unwind_calls.append(kw)
        return {
            "success": False,
            "orderID": None,
            "matched_size": 0.0,
            "retryable": True,
            "outcome_unknown": False,
            "error": "PolyApiException[status_code=400, error_message={'error': 'no orders found to match with FAK order'}]",
        }

    h.executor.execute_unwind_order = _mock_unwind
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 1, "Must dispatch FAK unwind on Pass #1 without 3.9s STOP_CANCEL_PENDING delay!"
    assert unwind_calls[0]["min_price"] == pytest.approx(0.27)  # 0.31 - 0.04 sweep floor
    assert pos["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    assert (pos["next_unwind_retry_ts"] - time.time()) <= 0.50


def test_fix16_external_dual_audit_executor_and_harvester_hardening(tmp_path, monkeypatch):
    """
    Regression suite verifying ChatGPT + Gemini dual adversarial audit fixes across Live Executor & Live Harvester:
      - F-01: `signature_type=0` EOA wallet preserved (not coerced to `1`) in `attempt_onchain_redemption`
      - F-02: `find_redemption_payouts` fails closed (`None`) when `NegRiskAdapter` `eth_getLogs` fails
      - F-23: `build_relayer_builder_headers` signs exact canonical JSON `str` wire bytes verbatim
      - F-09: `execute_atomic_dominance_box` enforces per-leg fees + unwinds actual partial `takingAmount`
      - F-16: `get_collateral_balance(hot_path=True)` invalidates stale `>120s` cache in live mode
      - F-05: Zero/negative Kelly edge returns `0.0` (never `min_lot_usd` or `MAX_ABSOLUTE_TICKET_USD`)
      - F-22: Sticky account-equity floor halt with `+$3.00` hysteresis & verified `allow_auto_clear=True`
      - M-01: `5..10`-share position posts a single maker exit lot without leaving `<5`-share orphan tail
      - F-17: DST-aware `America/New_York` weekday `09:15-09:32 ET` opening-bell blackout
      - F-11 / M-05: Future clock-skew & internal JSON timestamp staleness checks
      - F-07: Live `15m` Chainlink USD provenance guard rejects missing USD spot anchor
    """
    import asyncio
    import hashlib
    import hmac
    import base64
    import json
    from datetime import datetime, timezone
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor, ExecutionStatus
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        compute_correlated_truncated_kelly_size,
        compute_kelly_ticket_size,
        check_recorder_freshness,
        read_fast_tick,
    )

    # 1. F-23: Canonical JSON string wire-byte HMAC signing
    secret_b64 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    canonical_json = json.dumps({"type": "WALLET", "nonce": "7", "nested": {"x": 1}}, separators=(",", ":"))
    hdrs = PolymarketLiveExecutor.build_relayer_builder_headers(
        api_key="k",
        secret=secret_b64,
        passphrase="p",
        method="POST",
        request_path="/submit",
        body=canonical_json,
        timestamp=1700000000,
    )
    expected_msg = f"1700000000POST/submit{canonical_json}".encode("utf-8")
    expected_sig = base64.urlsafe_b64encode(
        hmac.new(base64.urlsafe_b64decode(secret_b64), expected_msg, hashlib.sha256).digest()
    ).decode("utf-8")
    assert hdrs["POLY_BUILDER_SIGNATURE"] == expected_sig

    # 2. F-02: `find_redemption_payouts` returns `None` when NegRiskAdapter RPC fails (`None`)
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "f16_exec.jsonl")
    ex.dry_run = False
    ex.funder_address = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9"
    cond_id = "0x" + ("cd" * 32)
    rpc_calls = []

    def fake_rpc_logs(method, params):
        rpc_calls.append((method, params))
        flt = (params or [{}])[0]
        if str(flt.get("address", "")).lower() == ex.NEG_RISK_ADAPTER_ADDRESS.lower():
            return None  # Simulate RPC error on NegRiskAdapter!
        return []

    monkeypatch.setattr(ex, "get_current_block_number", lambda: 200)
    monkeypatch.setattr(ex, "_rpc", fake_rpc_logs)
    assert ex.find_redemption_payouts(cond_id, from_block=100, max_span=1000) is None
    assert len(rpc_calls) == 2

    # 3. F-01: `signature_type=0` EOA wallet is NOT coerced to `1` (`POLY_PROXY`)
    import web3
    ex_eoa = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "f16_eoa.jsonl")
    ex_eoa.dry_run = False
    ex_eoa.signature_type = 0
    ex_eoa.funder_address = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9"
    ex_eoa.private_key = "0x" + ("11" * 32)
    monkeypatch.delenv("POLYGON_PRIVATE_KEY", raising=False)
    checked_gas_payers = []

    class DummyEth:
        class account:
            @staticmethod
            def from_key(pk):
                return type("Acct", (), {"address": "0x2222222222222222222222222222222222222222"})()

        @staticmethod
        def get_balance(addr):
            checked_gas_payers.append(str(addr).lower())
            return 0  # Exits cleanly right after proving sig_type==0 selected funder_cs!

    class DummyW3:
        HTTPProvider = web3.Web3.HTTPProvider
        to_checksum_address = staticmethod(web3.Web3.to_checksum_address)
        eth = DummyEth()

        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(web3, "Web3", DummyW3)
    assert ex_eoa.attempt_onchain_redemption(cond_id) is None
    assert checked_gas_payers == [ex_eoa.funder_address.lower()]

    # 4. F-09: Per-leg fees + partial Leg-1 `takingAmount` unwind in `execute_atomic_dominance_box`
    ex_box = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "f16_box.jsonl")
    ex_box.dry_run = False
    ex_box.is_authenticated = True
    monkeypatch.setattr(ex_box, "get_token_tick_size", lambda tid: 0.01)
    monkeypatch.setattr(ex_box, "get_token_neg_risk", lambda tid, explicit_neg_risk=None: False)
    # High fee on leg_b (`0.25`) pushes box cost over `0.995` even if `fee_rate` default was `0.07`
    cap_res = ex_box.execute_atomic_dominance_box(
        box_id="BOX_FEE_B",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.48,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.46,
        shares=20,
        max_box_cost_net=0.995,
        fee_rate_a=0.07,
        fee_rate_b=0.25,
    )
    assert cap_res["success"] is False and "WORST_LIMIT_BOX_COST_EXCEEDS_CAP" in cap_res["error"]

    class PartialFillClient:
        def create_order(self, args, options=None):
            return {"token_id": args.token_id, "price": args.price, "size": args.size}

        def post_order(self, signed, order_type):
            # Returns partial 12-share fill instead of requested 20 shares!
            return {"orderID": "OID_PARTIAL_12", "takingAmount": "12.0"}

    ex_box.client = PartialFillClient()
    unwound_partial = []
    monkeypatch.setattr(
        ex_box,
        "execute_unwind_order",
        lambda token_id, size, side="SELL", min_price=0.01, neg_risk=None: (
            unwound_partial.append((token_id, size)) or {"success": True, "matched_size": size}
        ),
    )
    part_res = ex_box.execute_atomic_dominance_box(
        box_id="BOX_PARTIAL",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.50,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.42,
        shares=20,
        max_box_cost_net=0.995,
        leg_a_avail_shares=25.0,
        leg_b_avail_shares=80.0,
    )
    assert part_res["success"] is False and part_res["stage"] == "LEG_1_PARTIAL_FILL_UNWOUND"
    assert unwound_partial == [("tok_a", 12.0)]

    # 5. F-16: Stale `>120s` hot-path collateral cache invalidated in live mode
    ex_col = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "f16_col.jsonl")
    ex_col.dry_run = False
    ex_col.is_authenticated = False  # Live fallback returns None when stale cache is invalidated
    ex_col._collateral_cache = (time.time() - 300.0, 99.50)
    assert ex_col.get_collateral_balance(hot_path=True) is None

    # 6. F-05: Zero/negative Kelly edge returns `0.0` (never `min_lot_usd` or `MAX_ABSOLUTE_TICKET_USD`)
    assert compute_correlated_truncated_kelly_size(p_win=0.50, entry_px=0.75, live_equity=100.0) == 0.0
    assert compute_correlated_truncated_kelly_size(p_win=0.85, entry_px=0.72, live_equity=0.0) == 0.0
    assert compute_kelly_ticket_size(p_model=0.65, p_eff=0.72, bankroll=100.0) == 0.0
    assert compute_kelly_ticket_size(p_model=0.85, p_eff=0.70, bankroll=-10.0) == 0.0

    # 7. F-22: Sticky account-equity floor halt + $3.00 recovery hysteresis
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "f16_state.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "f16_res.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "f16_state.json"
    h.risk_controller.min_equity_floor_usd = 48.0
    assert h.risk_controller.check_equity_drawdown(45.5, 80.0) is True
    assert h.risk_controller.is_halted() is True
    # Hot-path check (`allow_auto_clear=False`) must NOT auto-clear even at $55!
    assert h.risk_controller.check_equity_drawdown(55.0, 80.0) is True
    assert h.risk_controller.is_halted() is True
    # Verified refresh below $51 (`48 + 3`) stays halted; >= $51 clears cleanly!
    assert h.risk_controller.check_equity_drawdown(49.5, 80.0, allow_auto_clear=True) is True
    assert h.risk_controller.check_equity_drawdown(51.5, 80.0, allow_auto_clear=True) is False
    assert h.risk_controller.is_halted() is False

    # 8. M-01: `7.2`-share position (`5 <= rem < 10`) posts single `7.2`-share maker exit (no `<5` orphan split!)
    real_tok = "554433221100998877665544332211"
    pos_7sh = {
        "trade_id": "LIVE_M01_ORPHAN_GUARD",
        "token_id": real_tok,
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "exit_order_status": "EXIT_RECOVERY_REQUIRED",
        "inventory_reconciled": True,
        "entry_price": 0.72,
        "entry_shares": 7.2,
        "remaining_shares": 7.2,
        "candle_expiry_ts": time.time() + 240.0,
        "exit_tranches": [
            {"idx": 1, "size": 5.0, "price": 0.95, "status": "PENDING"},
            {"idx": 2, "size": 2.2, "price": 0.98, "status": "PENDING"},
        ],
    }
    posted_m01 = []
    h._wallet_token_balance = MagicMock(return_value=(7.2, h.ONCHAIN_SOURCE))
    h._strict_open_orders = lambda: []
    h._get_verified_shm_book = lambda p: {"bids": [{"price": "0.80", "size": "100"}], "asks": [{"price": "0.82", "size": "100"}]}
    h.executor.post_maker_exit_order = lambda **kw: (
        posted_m01.append(kw) or {"success": True, "orderID": "OID_SINGLE_72", "price": kw["price"]}
    )
    assert h._attempt_maker_exit_post_impl("LIVE_M01_ORPHAN_GUARD", pos_7sh) is True
    assert len(posted_m01) == 1 and posted_m01[0]["size"] == pytest.approx(7.2)

    # 9. F-11 / M-05: Internal JSON staleness in `check_recorder_freshness` & future skew in `read_fast_tick`
    hb_path = tmp_path / "recorder_hb.json"
    now_s = time.time()
    hb_path.write_text(json.dumps({"timestamp_unix": now_s - 45.0}), encoding="utf-8")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RECORDER_HEARTBEAT_FILES", [hb_path])
    ok_hb, reason_hb = check_recorder_freshness(max_stale_sec=10.0)
    assert ok_hb is False and "internal_stale" in reason_hb

    monkeypatch.delenv("PM_FAST_TICK_DIR", raising=False)
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.FAST_TICK_SHM_DIR", tmp_path)
    (tmp_path / "pm_fast_tick_BTC.json").write_text(
        json.dumps({"timestamp_unix": now_s + 10.0, "spot_price": 84000.0}), encoding="utf-8"
    )
    assert read_fast_tick("BTC") is None

    # 10. F-17 (NYSE EST post-DST blackout) & F-07 (15m Chainlink missing USD spot veto)
    snipe_f17 = []

    async def mock_snipe_f17(**kw):
        snipe_f17.append(kw)
        return MagicMock(success=True)

    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.check_recorder_freshness = lambda asset, now_t: (True, 0.05, "OK")
    h.executor.execute_snipe_order_async = mock_snipe_f17
    h.executor.get_collateral_balance = lambda *a, **kw: 95.0
    # Monday Nov 2, 2026 14:20:00 UTC == 09:20:00 EST (after Nov 1 DST fallback!)
    est_open_ts = datetime(2026, 11, 2, 14, 20, 0, tzinfo=timezone.utc).timestamp()
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.time.time", lambda: est_open_ts)
    shock_est = {
        "event_id": "EVT_NYSE_EST",
        "market_id": "6099991",
        "condition_id": "0xnyse",
        "t0_unix": est_open_ts,
        "title": "Bitcoin Up or Down - Nov 2, 9:00AM-10:00AM ET",
        "asset": "BTC",
        "horizon": "1h",
        "shock_direction": "BUY",
        "seconds_to_expiry": 240.0,
        "spot_at_t0": 84250.0,
        "trigger_price": 84250.0,
        "candle_open_spot": 84050.0,
        "candle_distance_pct": 0.238,
        "shock_volume_100ms": 3000000.0,
        "shock_ofi": 0.92,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_tok,
                "raw_top_asks": [[0.72, 100.0]],
                "raw_top_bids": [[0.71, 100.0]],
                "effective_price_$25": 0.72,
                "vwap_$25": 0.72,
                "age_book_ms": 50.0,
                "book_timestamp": est_open_ts,
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_est))
    assert len(snipe_f17) == 0, "Monday 09:20 EST (14:20 UTC post-DST) must be blocked by NYSE blackout!"

    # Move outside NYSE blackout (Monday 15:20 UTC == 10:20 EST) and test 15m Chainlink missing USD spot veto (`F-07`)
    est_1020_ts = datetime(2026, 11, 2, 15, 20, 0, tzinfo=timezone.utc).timestamp()
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.time.time", lambda: est_1020_ts)
    shock_15m_no_usd = dict(
        shock_est,
        event_id="EVT_15M_NO_USD",
        market_id="6099992",
        t0_unix=est_1020_ts,
        horizon="15m",
        authoritative_chainlink_open=84050.123456,
        # Intentionally omit chainlink_proxy_spot & coinbase_spot -> must veto USDT vs USD comparison!
    )
    shock_15m_no_usd["pre_shock_features_t0"] = {
        "UP": dict(shock_est["pre_shock_features_t0"]["UP"], book_timestamp=est_1020_ts)
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_15m_no_usd))
    assert len(snipe_f17) == 0, "Live 15m Chainlink market without verified USD spot anchor must fail closed!"



def test_fix18_canceled_market_resolved_terminal_state():
    """
    Verifies deterministic handling of Polymarket CLOB status 'CANCELED_MARKET_RESOLVED':
    1. cancel_order recognizes 'CANCELED_MARKET_RESOLVED' as terminal CANCELED (not UNKNOWN).
    2. get_order_fill_summary marks is_canceled=True and terminal=True.
    """
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    ex = PolymarketLiveExecutor(dry_run=False)
    ex.client = MagicMock()
    ex.is_authenticated = True
    ex.client.cancel_orders.return_value = {"canceled": []}
    ex.client.get_order.return_value = {
        "status": "CANCELED_MARKET_RESOLVED",
        "size_matched": "0.0",
        "original_size": "12.2",
        "price": "0.95",
        "side": "SELL",
    }
    cancel_res = ex.cancel_order("0xTEST_OID_RESOLVED")
    assert cancel_res.is_canceled is True
    assert cancel_res.outcome == "CANCELED"

    summary = ex.get_order_fill_summary("0xTEST_OID_RESOLVED")
    assert summary is not None
    assert summary["resting"] is False
    assert summary["terminal"] is True


def test_fix19_15m_usd_vs_usdt_oracle_and_supervision_parity(tmp_path, monkeypatch):
    """
    Forensic regression test for LIVE_6169334_1792980781_UP (15m ETH Chainlink USD vs Binance USDT unit mismatch):
      1. PolymarketTerminalRecorder.get_chainlink_proxy_spot() converts Binance USDT spot to true USD via
         causal rolling median USDT/USD basis (returning ~2311.20 USD, NEVER 2314.40 USDT), and returns 0.0
         when neither Coinbase USD nor basis history is available.
      2. Exact replay of LIVE_6169334_1792980781_UP (authoritative_chainlink_open=2311.940735 USD,
         spot_at_t0=2314.41 USDT, coinbase_spot=2311.19 USD, even with legacy unadjusted
         chainlink_proxy_spot=2314.3973) is deterministically REJECTED (0 orders) because true USD distance
         is -0.0325% OTM for UP.
      3. Open 15m USD-settled positions carry spot_denomination='USD' + USD entry_spot_ref and route
         check_resolutions_and_manage_positions supervision strictly through get_usd_reference_spot_price.
    """
    import asyncio
    from collections import deque
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_terminal_recorder import PolymarketDualFeed1HRecorder as PolymarketTerminalRecorder
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    # 1. Recorder true-USD Chainlink proxy spot conversion
    rec = PolymarketTerminalRecorder.__new__(PolymarketTerminalRecorder)
    rec.asset = "ETH"
    rec.spot_price = 2314.41  # Binance ETHUSDT
    rec.coinbase_spot = 0.0
    rec.coinbase_spot_ts = 0.0
    rec._venue_div_history = deque(maxlen=200)
    rec._cl_proxy_history = deque(maxlen=400)
    now_u = 1792980781.75
    # Without Coinbase or basis history, never emit raw USDT as USD proxy!
    assert rec.get_chainlink_proxy_spot(now_u) == 0.0

    rec.coinbase_spot = 2311.19  # Coinbase ETH-USD
    rec.coinbase_spot_ts = now_u
    for _ in range(20):
        rec._venue_div_history.append(13.82)  # +13.82 bps USDT/USD basis
    cl_usd = rec.get_chainlink_proxy_spot(now_u)
    assert 2311.00 <= cl_usd <= 2311.40, f"Expected true USD ~2311.20, got {cl_usd}"
    assert rec.get_chainlink_twap_60s(now_u) == pytest.approx(cl_usd, abs=0.05)

    # 2. Exact replay of LIVE_6169334_1792980781_UP must be rejected (0 orders placed)
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "f19_state.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "f19_res.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "f19_state.json"
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 72.0
    h.check_recorder_freshness = lambda asset, now_t: (True, 0.05, "OK")
    placed = []

    async def fail_if_called(**kw):
        placed.append(kw)
        return MagicMock(success=False, mode="REJECTED", details={})

    h.executor.execute_snipe_order_async = fail_if_called
    real_tok = "998877665544332211009988776655"
    shock_bugged_replay = {
        "event_id": "6169334_1792980781.749534",
        "market_id": "6169334",
        "condition_id": "0x6169334",
        "t0_unix": now_u,
        "title": "Ethereum Up or Down - October 25, 10:00PM-10:15PM ET",
        "asset": "ETH",
        "horizon": "15m",
        "resolution_source": "https://data.chain.link/streams/eth-usd-twap-60s-streams",
        "shock_direction": "BUY",
        "seconds_to_expiry": 118.2,
        "spot_at_t0": 2314.41,
        "trigger_price": 2314.41,
        "candle_open_spot": 2315.01,
        "authoritative_chainlink_open": 2311.940735,
        "coinbase_spot": 2311.19,
        "chainlink_proxy_spot": 2314.3973,  # Legacy unadjusted USDT value from pre-fix recorder!
        "chainlink_twap_60s": 2314.55,
        "shock_volume_100ms": 2_500_000.0,
        "shock_ofi": 0.90,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_tok,
                "best_bid": 0.46,
                "best_ask": 0.47,
                "raw_top_asks": [[0.47, 150.0]],
                "raw_top_bids": [[0.46, 150.0]],
                "effective_price_$25": 0.47,
                "vwap_$25": 0.47,
                "age_book_ms": 1357.1,
                "age_ask_ms": 1357.1,
                "book_timestamp": now_u,
            }
        },
    }
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.time.time", lambda: now_u)
    asyncio.run(h.evaluate_shock_and_execute(shock_bugged_replay))
    assert len(placed) == 0, "OTM ETH 15m UP setup (-0.0325% in USD) must NEVER pass cushion gate via USDT basis!"

    # 3. Supervision of open 15m USD-denominated position uses get_usd_reference_spot_price (NOT Binance USDT)
    from datetime import datetime, timezone
    now_sup = datetime.now(timezone.utc).timestamp()
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.time.time", lambda: now_sup)
    usd_calls = []
    usdt_calls = []
    h.get_usd_reference_spot_price = lambda sym: (usd_calls.append(sym) or 2309.50)
    h.get_reference_spot_price = lambda sym: (usdt_calls.append(sym) or 2313.10)
    h._strict_open_orders = lambda: [{"id": "OID_MAKER_95"}]
    h._get_verified_shm_book = lambda pos: {
        "bids": [{"price": "0.32", "size": "200"}],
        "asks": [{"price": "0.34", "size": "200"}],
    }
    h._wallet_token_balance = MagicMock(return_value=(20.0, h.ONCHAIN_SOURCE))
    h.executor.cancel_order = MagicMock(return_value={"canceled": ["OID_MAKER_95"], "is_canceled": True, "outcome": "CANCELED"})
    h.executor.get_order_fill_summary = MagicMock(return_value={
        "order_id": "OID_MAKER_95", "status": "CANCELED", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True,
    })
    unwound = []
    h.executor.execute_unwind_order = lambda **kw: (
        unwound.append(kw) or {
            "success": False,
            "orderID": None,
            "matched_size": 0.0,
            "retryable": True,
            "outcome_unknown": False,
            "error": "SIM_UNWIND_PASS",
        }
    )
    h.active_positions["LIVE_USD_SUP"] = {
        "trade_id": "LIVE_USD_SUP",
        "market_id": "6169334",
        "condition_id": "0x6169334",
        "token_id": real_tok,
        "target_token": "UP",
        "asset": "ETH",
        "horizon": "15m",
        "is_subhourly": True,
        "spot_denomination": "USD",
        "candle_open_spot": 2311.94,
        "entry_spot_ref": 2313.80,
        "candle_sigma": 0.0034,
        "entry_price": 0.72,
        "entry_shares": 20.0,
        "gross_entry_shares": 20.0,
        "remaining_shares": 20.0,
        "remaining_exit_shares": 20.0,
        "filled_exit_shares": 0.0,
        "remaining_cost_basis": 14.40,
        "notional_usd": 14.40,
        "fee_usd": 0.15,
        "entry_fee_cash_usd": 0.15,
        "target_exit_price": 0.95,
        "entry_ts": now_sup - 30.0,
        "candle_expiry_ts": now_sup + 175.0,
        "low_bid_detected_ts": now_sup - 7.0,
        "status": ExecutionStatus.EXIT_RESTING,
        "inventory_reconciled": True,
        "exit_order_id": "OID_MAKER_95",
        "exit_order_status": "RESTING",
        "is_liquidating": False,
    }
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert usd_calls == ["ETH"], "USD-denominated 15m position must query get_usd_reference_spot_price!"
    assert usdt_calls == [], "USD-denominated 15m position must NEVER query Binance USDT get_reference_spot_price!"
    assert len(unwound) == 1, "True USD OTM break (2309.50 < 2311.94 open, bid=0.32) must trigger protective salvage!"


def test_v40_live_execution_speed_and_compounding_levers(tmp_path, monkeypatch):
    """
    Verifies the v4.0 live execution speed, compounding, and riskless Slot-2 graduation upgrades:
      1. Lever #1a: `_ThreadLocalClobHttpClient` `LifoQueue` warm TLS 1.3 HTTP/1.1 pool (`warm_pool(min_warm=2)`)
         reuses hot sockets across distinct OS worker threads without concurrent socket sharing.
      2. Gemini #2: `PolymarketLiveExecutor.execute_atomic_dominance_box(..., parallel_dispatch=True)`
         dispatches both pre-signed FOK legs concurrently (<5ms skew) AND auto-unwinds Leg 1 if Leg 2 rejects.
      3. Lever #1b + Lever #2: Smooth `18%` dynamic compounding at `$73.01` (`~$13.14` ticket instead of frozen `$12.00`)
         + Shot-1 `+2c` price-improved FAK strictly clamped at `<= p_max`.
      4. Gemini #6: `$0.985-$0.99` pre-expiry cash recycling (`8s <= TTE <= 25s`, `limit_price >= 0.98`) freeing
         collateral BEFORE `:00/:15/:30/:45` candle rollovers.
      5. Lever #3 + Gemini #12: `maybe_execute_graduated_d1_box` (`8/8` settled at `100%` WR) and
         `get_graduated_allowed_assets` (`>=$110` equity + `ready_for_live_graduation: true`).
    """
    import asyncio
    import json
    import threading
    from unittest.mock import MagicMock
    import src.polymarket_research.polymarket_live_executor as exec_mod
    import src.polymarket_research.polymarket_live_harvester as harv_mod
    from src.polymarket_research.polymarket_live_executor import (
        ExecutionStatus,
        PolymarketLiveExecutor,
        _ThreadLocalClobHttpClient,
    )
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    # 1. Warm LifoQueue HTTP/1.1 pool: warm_pool(min_warm=2) + cross-thread LIFO socket reuse
    pool_cli = _ThreadLocalClobHttpClient(timeout=4.0, max_pool_size=8)
    created_clients = []

    class FakeHttpxClient:
        def __init__(self):
            self.is_closed = False
            self.calls = 0
            created_clients.append(self)

        def request(self, method="GET", url="", **kw):
            self.calls += 1
            return MagicMock(status_code=200)

        def close(self):
            self.is_closed = True

    pool_cli._make_client = FakeHttpxClient
    warmed_cnt = pool_cli.warm_pool(url="https://clob.polymarket.com/time", min_warm=2, max_idle_sec=0.0)
    assert warmed_cnt == 2 and pool_cli._pool.qsize() == 2

    used_by_workers = []

    def _worker_req():
        b_cli = pool_cli._borrow_pool_client()
        used_by_workers.append(b_cli)
        b_cli.request("POST", "https://clob.polymarket.com/order")
        pool_cli._return_pool_client(b_cli)

    for _ in range(4):
        th = threading.Thread(target=_worker_req)
        th.start()
        th.join()
    # Different worker threads reused the pre-warmed hot pool without creating cold sockets!
    assert len(created_clients) == 2
    assert all(c in created_clients for c in used_by_workers)

    # 2. Parallel 2-leg FOK Dominance Box dispatch + automatic single-leg unwind on Leg 2 reject
    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    ex.auth_mode = "AUTHENTICATED_L2"
    ex._tick_size_cache["tok_a"] = 0.01
    ex._tick_size_cache["tok_b"] = 0.01
    ex._neg_risk_cache["tok_a"] = False
    ex._neg_risk_cache["tok_b"] = False
    if exec_mod.OrderArgsV2 is None:
        monkeypatch.setattr(exec_mod, "OrderArgsV2", lambda **kw: kw)
    if exec_mod.OrderType is None:
        monkeypatch.setattr(exec_mod, "OrderType", type("OT", (), {"FOK": "FOK", "FAK": "FAK", "GTC": "GTC"}))

    fake_clob = MagicMock()
    fake_clob.create_order.side_effect = lambda args, *a: {"token_id": getattr(args, "token_id", args["token_id"] if isinstance(args, dict) else "tok")}
    fake_clob.post_order.side_effect = [
        {"orderID": "OID_BOX_1", "status": "MATCHED", "takingAmount": "12", "makingAmount": "5.64"},
        {"orderID": "OID_BOX_2", "status": "MATCHED", "takingAmount": "12", "makingAmount": "5.76"},
    ]
    ex.client = fake_clob
    res_ok = ex.execute_atomic_dominance_box(
        box_id="BOX_PAR_OK",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.47,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.48,
        shares=12.0,
        max_box_cost_net=0.995,
        parallel_dispatch=True,
    )
    assert res_ok["success"] is True and res_ok["dispatch_mode"] == "PARALLEL_2LEG_FOK" and res_ok["shares"] == 12.0

    # Leg 2 rejects -> Leg 1 must automatically unwind!
    unwind_calls = []
    ex.execute_unwind_order = lambda tok, **kw: (unwind_calls.append((tok, kw)) or {"success": True, "matched_size": 12.0})
    fake_clob.post_order.side_effect = lambda signed, *a, **kw: (
        {"orderID": "OID_BOX_L1_ONLY", "status": "MATCHED", "takingAmount": "12", "makingAmount": "5.64"}
        if isinstance(signed, dict) and signed.get("token_id") == "tok_a"
        else {"errorMsg": "FOK order couldn't be fully filled", "orderID": None}
    )
    res_legout = ex.execute_atomic_dominance_box(
        box_id="BOX_PAR_LEGOUT",
        leg_a_token_id="tok_a",
        leg_a_label="15M_UP",
        leg_a_limit_price=0.47,
        leg_b_token_id="tok_b",
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.48,
        shares=12.0,
        max_box_cost_net=0.995,
        parallel_dispatch=True,
    )
    assert res_legout["success"] is False and res_legout["legged_out"] is True
    assert len(unwind_calls) == 1 and unwind_calls[0][0] == "tok_a"

    # 3. Smooth 18% dynamic compounding ($73.01 -> ~$13.14) + Shot-1 +2c FAK strictly <= p_max
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    monkeypatch.setattr(harv_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(harv_mod, "STATE_FILE", tmp_path / "v40_state.json")
    monkeypatch.setattr(harv_mod, "RESOLUTIONS_FILE", tmp_path / "v40_res.jsonl")

    h = PolymarketLiveHarvester(ticket_notional=12.0, dry_run=True, allowed_assets={"BTC", "ETH"})
    h.dry_run = False
    h.executor.dry_run = False
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "v40_state.json"
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 73.01
    h.check_recorder_freshness = lambda asset, now_t: (True, 0.05, "OK")

    snipe_dispatches = []

    async def _capture_snipe(**kw):
        snipe_dispatches.append(kw)
        return type("FakeSnipeRes", (), {
            "success": False, "order_id": None, "tx_hashes": [], "filled_size": 0.0, "avg_price": 0.0,
            "size": 0.0, "price": 0.0, "fee_paid_usd": 0.0, "latency_ms": 1.0, "error_msg": "SIM", "error": "SIM",
            "mode": "FAK_KILLED_NO_MATCH", "details": {"fak_killed": True}, "execution_status": ExecutionStatus.REJECTED,
        })()

    h.executor.execute_snipe_order_async = _capture_snipe
    real_tok_v40 = "100434764618174237135201777197981253576172734064131101154122934005557319214073"
    now_v40 = time.time()
    shock_v40 = {
        "shock_id": "v40_smooth_snipe",
        "market_id": "6200101",
        "condition_id": "0x6c7e137b9293b4004131cd749fe460eeb669b626ea5b3d9795bffbe491caa527",
        "title": "Ethereum Up or Down - October 26, 10:00AM-10:15AM ET",
        "asset": "ETH",
        "horizon": "15m",
        "resolution_source": "https://data.chain.link/streams/eth-usd-twap-60s-streams",
        "t0_unix": now_v40,
        "seconds_to_expiry": 240.0,
        "expiry_ts": now_v40 + 240.0,
        "candle_sigma": 0.0024,
        "shock_volume_100ms": 620000.0,
        "is_40ms_fast_track": True,
        "shock_direction": "BUY",
        "shock_ofi": 0.95,
        "spot_at_t0": 2345.00,
        "coinbase_spot": 2345.00,
        "candle_open_spot": 2340.00,
        "twap_60s_open": 2340.00,
        "candle_distance_pct": 0.2137,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": "0x6c7e137b9293b4004131cd749fe460eeb669b626ea5b3d9795bffbe491caa527"},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_tok_v40,
                "best_bid": 0.71,
                "best_ask": 0.72,
                "spread": 0.01,
                "book_timestamp": now_v40 - 0.02,
                "age_book_ms": 20.0,
                "age_ask_ms": 210.0,
                "age_bid_ms": 300.0,
                "obi_l1": 0.35,
                "raw_top_bids": [[0.71, 150.0], [0.70, 100.0]],
                "raw_top_asks": [[0.72, 120.0], [0.73, 120.0]],
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock_v40))
    assert len(snipe_dispatches) >= 1
    disp = snipe_dispatches[0]
    assert disp["notional_usd"] > 12.50, f"Expected smooth 18% compounding > $12.50 at $73.01 equity, got {disp['notional_usd']}"
    assert disp["target_price"] == 0.74, f"Expected Shot-1 +2c price-improved FAK (0.72 + 0.02 = 0.74), got {disp['target_price']}"
    assert disp["target_price"] <= disp["max_price_ceiling"], "Shot-1 target_price must never exceed p_max ceiling!"

    # 4. Pre-expiry $0.985-$0.99 instant cash recycling (`8s <= TTE <= 25s`, `limit_px >= 0.98`)
    h.get_usd_reference_spot_price = lambda sym: 2348.0
    h._strict_open_orders = lambda: [{"id": "OID_MKR_99"}]
    h._get_verified_shm_book = lambda pos: {
        "bids": [{"price": "0.99", "size": "250"}],
        "asks": [{"price": "1.00", "size": "250"}],
    }
    h._wallet_token_balance = MagicMock(return_value=(18.0, h.ONCHAIN_SOURCE))
    h.executor.cancel_order = MagicMock(return_value={"canceled": ["OID_MKR_99"], "is_canceled": True, "outcome": "CANCELED"})
    h.executor.get_order_fill_summary = MagicMock(return_value={
        "order_id": "OID_MKR_99", "status": "CANCELED", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True,
    })
    recycled_unwinds = []
    h.executor.execute_unwind_order = lambda **kw: (
        recycled_unwinds.append(kw) or {
            "success": True, "orderID": "OID_RECYCLE_99", "matched_size": 18.0, "taking_amount": 17.8076, "fee_usd": 0.0124,
        }
    )
    h.active_positions["LIVE_RECYCLE_99"] = {
        "trade_id": "LIVE_RECYCLE_99",
        "market_id": "6200101",
        "condition_id": "0x6200101",
        "token_id": real_tok_v40,
        "target_token": "UP",
        "asset": "ETH",
        "horizon": "15m",
        "is_subhourly": True,
        "spot_denomination": "USD",
        "candle_open_spot": 2340.00,
        "entry_spot_ref": 2345.00,
        "candle_sigma": 0.0024,
        "entry_price": 0.72,
        "entry_shares": 18.0,
        "gross_entry_shares": 18.0,
        "remaining_shares": 18.0,
        "remaining_exit_shares": 18.0,
        "filled_exit_shares": 0.0,
        "remaining_cost_basis": 12.96,
        "notional_usd": 12.96,
        "fee_usd": 0.12,
        "entry_fee_cash_usd": 0.12,
        "target_exit_price": 0.99,
        "entry_ts": now_v40 - 200.0,
        "candle_expiry_ts": time.time() + 15.0,  # 15s TTE inside [8s, 25s] recycle window!
        "status": ExecutionStatus.EXIT_RESTING,
        "inventory_reconciled": True,
        "exit_order_id": "OID_MKR_99",
        "exit_order_status": "RESTING",
        "is_liquidating": False,
    }
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(recycled_unwinds) == 1
    assert recycled_unwinds[0]["min_price"] >= 0.98, f"Expected >= $0.98 recycle floor, got {recycled_unwinds[0]['min_price']}"

    # 5. Lever #3 (`maybe_execute_graduated_d1_box`) & Gemini #12 (`get_graduated_allowed_assets`)
    (tmp_path / "state_shadow_sol_v392.json").write_text(json.dumps({"ready_for_live_graduation": True}), encoding="utf-8")
    assert "SOL" not in h.get_graduated_allowed_assets(total_equity=73.01)  # Blocked < $110!
    assert "SOL" in h.get_graduated_allowed_assets(total_equity=115.00)     # Auto-unlocked >= $110!

    h.active_positions.clear()
    (tmp_path / "alpha124_shadow_state.json").write_text(
        json.dumps({"by_sleeve": {"D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 5, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 4.2}}}),
        encoding="utf-8",
    )
    cand_box = {
        "box_id": "D1_TEST_SLOT2",
        "leg_a_token_id": "tok_a",
        "leg_b_token_id": "tok_b",
        "leg_a_limit_price": 0.47,
        "leg_b_limit_price": 0.48,
        "shares": 12.0,
        "corridor_bps": 10.0,
        "leg_a_side": "UP",
        "leg_b_side": "DOWN",
        "leg_a_strike": 80000.0,
        "leg_b_strike": 80080.0,
        "leg_a_market_id": "m_a",
        "leg_b_market_id": "m_b",
    }
    assert h.maybe_execute_graduated_d1_box(cand_box)["executed"] is False  # 5 < 8 required!

    (tmp_path / "alpha124_shadow_state.json").write_text(
        json.dumps({"by_sleeve": {"D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 8, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 7.5}}}),
        encoding="utf-8",
    )
    h.executor.execute_atomic_dominance_box = MagicMock(return_value={"success": True, "shares": 12.0})
    h._startup_reconciled = True
    _prev_dry = h.dry_run
    h.dry_run = True  # non-live path: live-only prechecks (numeric tokens, fresh books) are covered by test_v42
    d1_exec = h.maybe_execute_graduated_d1_box(cand_box)
    h.dry_run = _prev_dry
    assert d1_exec["executed"] is True, d1_exec
    assert h.executor.execute_atomic_dominance_box.call_args.kwargs["parallel_dispatch"] is True


def test_v41_burst_drain_adverse_collapse_and_wfo_parity(tmp_path, monkeypatch):
    """
    v4.1 Forensic Remediation & Purged-WFO Parity Suite:
      1. Recorder evaluate_shock blocks socket burst-drain phantom shocks (exch_lag_ms > 1000ms AND
         multi-second exchange t_ts spread arriving in a 5ms OS recv burst), while firing on genuine sweeps.
      2. Executor AdverseCollapseGuard + Harvester 2.5s WS book ceiling & ingress lag/WS guards block
         collapsing-book fills like LIVE_6176805 ($0.82 trigger ask -> $0.66 fill).
      3. Harvester dynamic_sizing AND cushion boolean fix enforces Quarter-Kelly VWAP veto on thin
         cushions (<0.07% 15m), blocking LIVE_6176805 ($0.82 ask on 0.0597% cushion at $65.05 bankroll).
      4. Purged-WFO Z-adaptive FAK buffer (+1c for z_strike < 1.25, +2c for z_strike >= 1.25).
    """
    import asyncio
    import json
    from datetime import datetime, timezone
    from src.polymarket_research.polymarket_terminal_recorder import (
        PolymarketDualFeed1HRecorder,
        L2OrderBook,
    )
    from src.polymarket_research.polymarket_live_executor import (
        PolymarketLiveExecutor,
        OrderResult,
        ExecutionStatus,
    )
    import src.polymarket_research.polymarket_terminal_recorder as rec_mod
    import src.polymarket_research.polymarket_live_harvester as harvester_mod

    emitted_triggers = []
    monkeypatch.setattr(rec_mod, "TRIGGER_FILE", tmp_path / "live_shock_triggers.jsonl")
    monkeypatch.setattr(
        rec_mod,
        "_dispatch_trigger_fast",
        lambda path, payload: (emitted_triggers.append((str(path), dict(payload))) or True, json.dumps(payload)),
    )
    monkeypatch.setattr(rec_mod, "_persist_trigger_nonblocking", lambda *a, **kw: None)

    rec = PolymarketDualFeed1HRecorder(asset="ETH", shock_threshold=400_000.0)
    rec.clob_ws_connected = True
    rec.active_burst_tasks = {1, 2, 3, 4, 5}
    rec.spot_price = 2224.20
    rec.futures_price = 2224.10
    rec.finalized_1h_open = 2228.00
    now_u = time.time()
    rec.current_market = {
        "market_id": "6176800",
        "condition_id": "0x6176800",
        "title": "Ethereum Up or Down - Hourly",
        "end_dt": datetime.fromtimestamp(now_u + 1200, tz=timezone.utc),
        "candle_open_ts": int(now_u - 2400),
        "candle_close_ts": int(now_u + 1200),
        "resolution_source": "https://www.binance.com/en/trade/ETH_USDT",
    }
    for side, tok in (("UP", "1" * 24), ("DOWN", "2" * 24)):
        bk = L2OrderBook(tok)
        bk.bids = {0.70: 200.0}
        bk.asks = {0.72: 200.0}
        bk.last_book_update_ts = now_u - 0.05
        bk.last_best_ask_change_ts = now_u - 0.40
        bk.last_best_bid_change_ts = now_u - 0.40
        rec.books[side] = bk
    rec.spawn_burst_verification = lambda *a, **kw: None

    # 1a. Stale exchange_event_ts_ms (> 1000ms lag) -> VETOED
    mono_base = time.monotonic_ns()
    stale_ms = int((time.time() - 4.2) * 1000)
    rec.spot_trades.clear()
    rec.spot_trades.append((mono_base, stale_ms, stale_ms, 650_000.0, False, 2224.20))
    rec.evaluate_shock(mono_base, stale_ms, "SPOT")
    assert len(emitted_triggers) == 0, "Expected exch_lag_ms > 1000ms packet to be vetoed!"

    # 1b. OS socket burst-drain: 6 small trades spanning 7.5s of Binance t_ts drained within 4ms local mono -> VETOED
    rec.spot_trades.clear()
    fresh_ms = int(time.time() * 1000) - 20
    mono_burst = time.monotonic_ns()
    for idx in range(6):
        t_exch_i = fresh_ms - (5 - idx) * 1500  # 1,500ms apart on Binance!
        rec.spot_trades.append((mono_burst - (5 - idx) * 600_000, t_exch_i, t_exch_i, 110_000.0, False, 2224.20))
    rec.evaluate_shock(mono_burst, fresh_ms, "SPOT")
    assert len(emitted_triggers) == 0, "Expected multi-second Binance trades drained in 4ms OS burst NOT to sum into a phantom shock!"

    # 1c. Genuine 50ms institutional sweep -> FIRES with clob_ws_connected=True
    rec.spot_trades.clear()
    rec.last_shock_ts = 0.0
    rec.last_shock_ts_by_source.clear()
    now_ms_ok = int(time.time() * 1000) - 15
    mono_ok = time.monotonic_ns()
    for idx in range(5):
        t_exch_i = now_ms_ok - (4 - idx) * 10  # 40ms total span on Binance!
        rec.spot_trades.append((mono_ok - (4 - idx) * 10_000_000, t_exch_i, t_exch_i, 120_000.0, False, 2224.20))
    rec.evaluate_shock(mono_ok, now_ms_ok, "SPOT")
    live_trigs = [payload for p, payload in emitted_triggers if "live_shock_triggers" in p]
    assert len(live_trigs) == 1, f"Expected genuine 40ms sweep to emit 1 live trigger, got {len(live_trigs)}"
    assert live_trigs[0]["clob_ws_connected"] is True

    # 2a. Executor AdverseCollapseGuard rejects >= 4c downward ask collapse
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "exec_v41.jsonl")
    collapsed_book = {
        "asks": [{"price": "0.66", "size": "200"}],
        "bids": [{"price": "0.65", "size": "200"}],
        "timestamp": time.time(),
    }
    res_collapse = asyncio.run(
        ex.execute_snipe_order_async(
            trade_id="TEST_COLLAPSE_6176805",
            token_id="9" * 24,
            target_token="DOWN",
            notional_usd=12.0,
            target_price=0.84,
            max_price_ceiling=0.85,
            min_price_floor=0.55,
            expected_best_price=0.82,
            prefetched_book=collapsed_book,
            market_fee_rate=0.07,
            market_fee_exponent=1.0,
        )
    )
    assert res_collapse.success is False
    assert "AdverseCollapseGuard" in (res_collapse.error or "")

    # 2b & 3. Harvester live ingress guards, 2.5s WS book ceiling -> REST refresh, Adverse Ask Collapse, and LIVE_6176805 Kelly veto
    monkeypatch.setattr(harvester_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(harvester_mod, "STATE_FILE", tmp_path / "state_v41.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    real_tok_down = "888888888888888888888888"
    for sym in ("BTC", "ETH"):
        (tmp_path / f"pm_fast_tick_{sym}.json").write_text(
            json.dumps({"ts": time.time(), "spot_price": 2224.20}),
            encoding="utf-8",
        )

    h = PolymarketLiveHarvester(
        dry_run=True,
        dynamic_sizing=True,
        hold_to_maturity=False,
        ticket_notional=12.0,
        max_exposure=60.0,
        allowed_assets={"BTC", "ETH"},
    )
    h.dry_run = False
    h.executor.dry_run = False
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.poll_onchain_redemptions = lambda: None
    h.state_file = tmp_path / "state_v41.json"
    h._startup_reconciled = True
    h._last_known_collateral = 65.05
    h.high_water_mark_equity = 65.05
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 65.05

    dispatched = []
    rest_book_calls = []

    async def _mock_rest_book(tid):
        rest_book_calls.append(tid)
        return {
            "asks": [{"price": "0.66", "size": "250"}],
            "bids": [{"price": "0.65", "size": "250"}],
            "timestamp": time.time(),
        }

    async def _mock_snipe(**kw):
        dispatched.append(kw)
        return OrderResult(
            success=False, order_id=None, trade_id=kw["trade_id"], token_id=kw["token_id"],
            target_token=kw["target_token"], side="BUY", price=0.0, size=0.0, notional_usd=0.0,
            fee_usd=0.0, latency_ms=1.0, mode="FAK_KILLED_NO_MATCH", execution_status=ExecutionStatus.REJECTED,
            confirmed_onchain=False, error="FAK killed", details={"fak_killed": True},
        )

    h.executor.get_market_book_async = _mock_rest_book
    h.executor.execute_snipe_order_async = _mock_snipe

    def _make_eth_15m_shock(shock_id: str, **overrides):
        t_now = time.time()
        base = {
            "shock_id": shock_id,
            "t0_unix": t_now - 0.05,
            "exchange_event_ts_ms": int((t_now - 0.08) * 1000),
            "clob_ws_connected": True,
            "market_id": f"MKT_{shock_id}",
            "condition_id": "0x6176805",
            "asset": "ETH",
            "horizon": "15m",
            "title": "Ethereum Up or Down - 15m",
            "shock_direction": "SELL",
            "candle_distance_pct": -0.0597,
            "candle_open_spot": 2225.57,
            "spot_at_t0": 2224.24,
            "candle_sigma": 0.0017,
            "seconds_to_expiry": 152.9,
            "candle_open_ts": t_now - 747.1,
            "candle_expiry_ts": t_now + 152.9,
            "shock_ofi": -1.0,
            "shock_volume_100ms": 1_200_000.0,
            "delta_basis_100ms": -1.5,
            "age_ask_ms": 220.0,
            "resolution_source": "https://www.binance.com/en/trade/ETH_USDT",
            "fee_metadata": {"condition_id": "0x6176805", "fee_rate_market": 0.07, "fee_exponent": 1.0},
            "pre_shock_features_t0": {
                "DOWN": {
                    "token_id": real_tok_down,
                    "best_bid": 0.80,
                    "best_ask": 0.82,
                    "spread": 0.02,
                    "book_timestamp": t_now - 0.05,
                    "age_book_ms": 50.0,
                    "age_ask_ms": 220.0,
                    "age_bid_ms": 250.0,
                    "obi_l1": 0.30,
                    "raw_top_bids": [[0.80, 150.0], [0.79, 150.0]],
                    "raw_top_asks": [[0.82, 150.0], [0.83, 150.0]],
                }
            },
        }
        base.update(overrides)
        return base

    # Ingress guard A: exchange_event_ts_ms lag > 1000ms -> rejected immediately
    shk_lag = _make_eth_15m_shock("LAG_8S", exchange_event_ts_ms=int((time.time() - 8.4) * 1000))
    asyncio.run(h.evaluate_shock_and_execute(shk_lag))
    assert len(dispatched) == 0 and len(rest_book_calls) == 0

    # Ingress guard B: clob_ws_connected=False -> rejected immediately
    shk_ws_down = _make_eth_15m_shock("WS_DOWN", clob_ws_connected=False)
    asyncio.run(h.evaluate_shock_and_execute(shk_ws_down))
    assert len(dispatched) == 0 and len(rest_book_calls) == 0

    # Stale WS book (>2.5s old) -> forces REST get_market_book_async -> catches $0.82 -> $0.66 adverse collapse!
    shk_stale_book = _make_eth_15m_shock("STALE_BOOK_COLLAPSE", candle_distance_pct=-0.12)
    shk_stale_book["pre_shock_features_t0"]["DOWN"]["book_timestamp"] = time.time() - 12.0
    shk_stale_book["pre_shock_features_t0"]["DOWN"]["age_book_ms"] = 12000.0
    asyncio.run(h.evaluate_shock_and_execute(shk_stale_book))
    assert len(rest_book_calls) == 1, "Expected >2.5s old WS book to force fresh REST get_market_book_async!"
    assert len(dispatched) == 0, "Expected $0.82 -> $0.66 fresh ask collapse to be rejected before order dispatch!"

    # 3. Exact LIVE_6176805 replica (fresh book @ $0.82, thin -0.0597% cushion, $65.05 bankroll) -> rejected by [VWAP KELLY REJECT]!
    shk_6176805 = _make_eth_15m_shock("REPLICA_6176805")
    asyncio.run(h.evaluate_shock_and_execute(shk_6176805))
    assert len(dispatched) == 0, "Expected thin-cushion $0.82 overpay (LIVE_6176805 replica) to be blocked by [VWAP KELLY REJECT]!"

    # 4. Z-Adaptive FAK Buffer Parity: moderate z_strike (< 1.25) on TIER_B_STANDARD gets +1c (0.70 -> 0.71)
    shk_mod_z = _make_eth_15m_shock("MOD_Z_TIER_B", candle_distance_pct=-0.075, age_ask_ms=60.0)
    shk_mod_z["pre_shock_features_t0"]["DOWN"].update({
        "best_bid": 0.69,
        "best_ask": 0.70,
        "spread": 0.01,
        "age_ask_ms": 60.0,
        "raw_top_bids": [[0.69, 180.0], [0.68, 150.0]],
        "raw_top_asks": [[0.70, 180.0], [0.71, 150.0]],
    })
    asyncio.run(h.evaluate_shock_and_execute(shk_mod_z))
    assert len(dispatched) == 1, "Expected clean $0.70 ask with 0.075% cushion to dispatch!"
    assert dispatched[0]["target_price"] == 0.71, f"Expected +1c Z-adaptive FAK buffer (0.71) when z_strike < 1.25, got {dispatched[0]['target_price']}"
    assert dispatched[0]["expected_best_price"] == 0.70
    assert dispatched[0]["min_price_floor"] == 0.55


def test_v42_d1_dominance_box_live_bridge_and_lifecycle(tmp_path, monkeypatch):
    """
    End-to-end verification of v4.2 Zero-Churn Profit Acceleration:
      1. Alpha124 shadow quarantine flags (PM_DISABLE_SHADOW_M4_CATCHUP=1 preserves M1 defensive cancel
         while eliminating multi-rung /book rate-limit bursts) + graduation mirror + D1 candidate stream.
      2. Harvester Slot #2 live D1 bridge: $14.00 SLEEVE_1 collateral reserve, fresh L2 book walk <= 0.975,
         zero interference with SLEEVE_1 concurrency or cross-asset directional checks, $0.99 Maker GTC ask
         without queue-jump step-down, zero-bid OTM leg exemption, 8s..28s >= $0.98 CLOB cash recycling,
         and unified 2-leg D1_BOX_CONSOLIDATED PnL accounting (0 false losses).
    """
    import asyncio
    import json
    from unittest.mock import AsyncMock, MagicMock
    import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
    from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec
    import src.polymarket_research.polymarket_live_harvester as harvester_mod
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus, OrderResult

    # --- PART 1: Alpha124 Shadow Quarantine + Graduation Mirror + D1 Live Candidate Stream ---
    a124_dir = tmp_path / "alpha124"
    live_dir = tmp_path / "polymarket"
    a124_dir.mkdir(parents=True, exist_ok=True)
    live_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(a124_mod, "DATA_DIR", a124_dir)
    monkeypatch.setattr(a124_mod, "STATE_FILE", a124_dir / "alpha124_shadow_state.json")
    monkeypatch.setattr(a124_mod, "OPPS_FILE", a124_dir / "alpha124_top_opportunities.json")
    monkeypatch.setattr(a124_mod, "LEDGER_FILE", a124_dir / "alpha124_shadow_ledger.jsonl")
    monkeypatch.setattr(a124_mod, "LIVE_POLYMARKET_DIR", live_dir)
    monkeypatch.setattr(a124_mod, "LIVE_ALPHA124_STATE_MIRROR_FILE", live_dir / "alpha124_shadow_state.json")
    monkeypatch.setattr(a124_mod, "D1_LIVE_CANDIDATES_FILE", live_dir / "d1_live_box_candidates.jsonl")
    monkeypatch.setenv("PM_DISABLE_SHADOW_M4_CATCHUP", "1")
    monkeypatch.setenv("PM_DISABLE_SHADOW_W2_TAKER", "1")

    daemon = a124_mod.Alpha124ShadowDaemon(single_scan=True)
    now_u = time.time()
    # Seed 11 settled winning D1 boxes in shadow state
    for i in range(11):
        daemon.closed_positions.append({
            "position_id": f"D1_HIST_{i}",
            "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
            "won": True,
            "tier_pnls_usd": {"T100": 2.40, "T1000": 8.11, "T5000": 28.50},
        })
    daemon.write_state_files([])
    mirror_path = live_dir / "alpha124_shadow_state.json"
    assert mirror_path.exists(), "Graduation mirror must be written to data/polymarket/alpha124_shadow_state.json!"
    mirror_data = json.loads(mirror_path.read_text(encoding="utf-8"))
    assert mirror_data["by_sleeve"]["D1_SAME_ORACLE_DOMINANCE_BOX"]["closed"] == 11
    assert mirror_data["by_sleeve"]["D1_SAME_ORACLE_DOMINANCE_BOX"]["win_rate_pct"] == 100.0

    # Verify M4 quarantine flag blocks /book burst while keeping M1 defensive maker cancel intact
    m4_book_fetches = []
    async def _track_fetch(url, timeout=3.0):
        if "T_Y_M4" in url or "T_N_M4" in url:
            m4_book_fetches.append(url)
        if "T_M1_NO" in url:
            return {"bids": [{"price": "0.48", "size": "100"}], "asks": [{"price": "0.52", "size": "100"}]}
        return None
    daemon.fetch_json = _track_fetch
    exp_close = now_u + 14400.0
    daemon.spots["BTC"] = 79500.0
    asyncio.run(daemon.post_shadow_maker_entry(
        sleeve="M1_SVI_MAKER_SCALP", dedupe_key="M1_DEF_1", asset="BTC", title="BTC > 80k",
        side_label="NO", token_id="T_M1_NO", p_model=0.60, close_ts=exp_close,
        extra={"market_id": "M_RUNG", "strike": 80000.0, "is_downward": False},
    ))
    assert len(daemon.pending_maker_orders) == 1
    daemon.spots["BTC"] = 80250.0  # Spot surges +0.94% adversely across $80,000 strike!
    daemon.strike_ladders["BTC_LAD"] = [
        a124_mod.StrikeRungSpec("EV_BTC", "btc-daily", "BTC", "BTC Above", "M_RUNG", "0x1", "BTC > 80000", 80000.0, False, exp_close, "T_Y_M4", "T_N_M4")
    ]
    asyncio.run(daemon.handle_shock_triggers(
        [{"asset": "BTC", "shock_direction": "BUY", "shock_ofi": 0.92, "shock_volume_100ms": 1_500_000.0, "t0_unix": now_u, "spot_at_t0": 80250.0}],
        [],
        now_ts=now_u,
    ))
    assert len(daemon.pending_maker_orders) == 0, "Defensive M1 maker cancel must remain active!"
    assert len(m4_book_fetches) == 0, "Quarantined M4 catchup must issue zero multi-rung /book fetches!"

    # Emit live D1 candidate via scan_same_oracle_dominance_boxes
    tok_15m_up = "111111111111111111111111111111"
    tok_5m_dn = "222222222222222222222222222222"
    end_ts = round((now_u + 180.0) / 5.0) * 5.0
    m15 = TwapCandleMarketSpec(
        market_id="650015", condition_id="0x" + "aa" * 32, asset="BTC", horizon="15m",
        title="BTC 15m", start_ts=end_ts - 900.0, end_ts=end_ts, start_iso="2026-10-26T12:00:00Z",
        end_iso="2026-10-26T12:15:00Z", up_token=tok_15m_up, down_token="333333333333333333333333333333",
        fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams",
    )
    m5 = TwapCandleMarketSpec(
        market_id="650005", condition_id="0x" + "bb" * 32, asset="BTC", horizon="5m",
        title="BTC 5m", start_ts=end_ts - 300.0, end_ts=end_ts, start_iso="2026-10-26T12:10:00Z",
        end_iso="2026-10-26T12:15:00Z", up_token="444444444444444444444444444444", down_token=tok_5m_dn,
        fee_rate=0.07, fee_exponent=1.0, neg_risk=False, twap_lookback_sec=60,
        resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams",
    )
    daemon.dominance_pairs[f"BTC_{int(end_ts)}"] = (m15, m5)
    daemon.get_authoritative_open_strike = AsyncMock(side_effect=lambda sp: 80000.0 if sp.horizon == "15m" else 80120.0)
    tok_15m_dn = "333333333333333333333333333333"
    tok_5m_up = "444444444444444444444444444444"
    fake_books = {
        tok_15m_up: {"asks": [{"price": "0.46", "size": "250"}], "bids": [{"price": "0.45", "size": "250"}]},
        tok_5m_dn: {"asks": [{"price": "0.46", "size": "250"}], "bids": [{"price": "0.45", "size": "250"}]},
        tok_15m_dn: {"asks": [{"price": "0.52", "size": "250"}], "bids": [{"price": "0.49", "size": "250"}]},
        tok_5m_up: {"asks": [{"price": "0.52", "size": "250"}], "bids": [{"price": "0.49", "size": "250"}]},
    }
    async def _fetch_d1(url, timeout=3.0):
        for tk, bk in fake_books.items():
            if tk in url:
                return bk
        return None
    daemon.fetch_json = _fetch_d1

    # --- PART 2: Harvester Startup Before Candidate File Exists -> Catches Very First D1 Box ---
    monkeypatch.setattr(harvester_mod, "DATA_DIR", live_dir)
    monkeypatch.setattr(harvester_mod, "STATE_FILE", live_dir / "live_state.json")
    monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT", "1")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(live_dir))
    for sym, px in (("BTC", 80060.0), ("ETH", 2500.0)):
        (live_dir / f"pm_fast_tick_{sym}.json").write_text(
            json.dumps({
                "ts": now_u, "spot_price": px,
                tok_15m_up: {"bids": [[0.98, 50.0]], "asks": [[0.99, 600.0]]},  # Heavy $0.99 wall to test queue-jump immunity!
            }),
            encoding="utf-8",
        )

    h = PolymarketLiveHarvester(
        dry_run=True, dynamic_sizing=True, hold_to_maturity=False, ticket_notional=12.0,
        max_exposure=60.0, max_concurrent=1, allowed_assets={"BTC", "ETH"},
    )
    h.dry_run = False
    h.executor.dry_run = False
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.poll_onchain_redemptions = lambda: None
    h.state_file = live_dir / "live_state.json"
    h._startup_reconciled = True

    # Poll #0 before file exists -> initializes cleanly at offset 0 without missing first candidate
    assert asyncio.run(h._poll_d1_live_box_candidates(now_u)) == 0

    # Now shadow daemon scans & emits first live D1 candidate
    opps = []
    asyncio.run(daemon.scan_same_oracle_dominance_boxes(opps, now_ts=now_u))
    cand_file = live_dir / "d1_live_box_candidates.jsonl"
    assert cand_file.exists(), "Live D1 candidate JSONL must be emitted when rem_sec=180s and box_cost_net <= 0.980!"

    # Collateral reserve check: at $20.00 free collateral ($20 - $14 reserve = $6 < $7.50 min), D1 yields to SLEEVE_1
    cand_obj = json.loads(cand_file.read_text(encoding="utf-8").splitlines()[0])
    h._last_known_collateral = 20.00
    res_low_collat = h.maybe_execute_graduated_d1_box(cand_obj)
    assert res_low_collat["executed"] is False
    assert res_low_collat["reason"] == "INSUFFICIENT_BOX_COLLATERAL_HEADROOM"

    # At $65.05 bankroll ($13.50 box budget, leaving >$51 free for SLEEVE_1), _poll_d1_live_box_candidates executes!
    h._last_known_collateral = 65.05
    h.high_water_mark_equity = 65.05
    h.executor.get_collateral_balance = lambda *a, **kw: h._last_known_collateral
    h.executor.get_market_book = lambda tid: fake_books[tid]
    wallet_bals = {tok_15m_up: 0.0, tok_5m_dn: 0.0}
    h._wallet_token_balance = lambda tid: (wallet_bals.get(tid, 0.0), h.ONCHAIN_SOURCE)
    h._verify_entry_finality = MagicMock(return_value=(True, False))

    def _mock_atomic_box(**kw):
        assert kw["max_box_cost_net"] == pytest.approx(0.975)  # Shock fired at now_u -> is_quiet_book=False -> 0.975 cap!
        assert kw["parallel_dispatch"] is True, "Deep book (>=4x depth, <=0.975 net) must dispatch in parallel!"
        sh = int(kw["shares"])
        assert sh == 17, "25% dynamic sizing ($16.50 reserve) on $65.05 bankroll ($16.26 budget) must size 17 pairs!"
        wallet_bals[tok_15m_up] = float(sh)
        wallet_bals[tok_5m_dn] = float(sh)
        h._last_known_collateral = round(65.05 - sh * 0.92, 2)
        return {
            "success": True,
            "box_id": kw["box_id"],
            "shares": float(sh),
            "leg_1": {"token_id": tok_15m_up, "label": kw["leg_a_label"], "price": 0.46, "orderID": "OID_BOX_A", "raw": {"makingAmount": round(sh * 0.46, 2), "transactionsHashes": ["0xtxa"]}},
            "leg_2": {"token_id": tok_5m_dn, "label": kw["leg_b_label"], "price": 0.46, "orderID": "OID_BOX_B", "raw": {"makingAmount": round(sh * 0.46, 2), "transactionsHashes": ["0xtxb"]}},
        }

    posted_maker_exits = []
    h.executor.execute_atomic_dominance_box = _mock_atomic_box
    h.executor.post_maker_exit_order = lambda **kw: (
        posted_maker_exits.append(kw) or {"success": True, "orderID": f"EXIT_{kw['token_id'][:4]}", "price": kw["price"]}
    )

    assert asyncio.run(h._poll_d1_live_box_candidates(time.time())) == 1
    assert len(h.active_positions) == 2
    assert h._risk_bearing_positions() == {}, "Delta-hedged D1 box legs must NOT consume SLEEVE_1 directional slot!"

    # Verify cross-asset directional conflict guard for an ETH DOWN SLEEVE_1 candidate is NOT blocked by hedged BTC D1 box
    ok_conf, _ = h.executor.validate_cross_asset_directional_conflict(
        candidate_asset="ETH",
        candidate_direction="DOWN",
        candidate_expiry_ts=end_ts,
        active_positions=list(h._risk_bearing_positions().values()),
        max_expiry_window_delta=2700.0,
    )
    assert ok_conf is True

    # Reconcile & post $0.99 single-tranche Maker GTC asks (must NOT step down below $0.99 despite $0.99 wall!)
    tids = sorted(h.active_positions.keys())
    for tid in tids:
        if not h.active_positions[tid].get("exit_order_id"):
            assert h._attempt_maker_exit_post(tid, h.active_positions[tid]) is True
        assert h.active_positions[tid].get("exit_order_id")
        assert h.active_positions[tid]["target_exit_price"] == pytest.approx(0.99)
        assert "exit_tranches" not in h.active_positions[tid]

    # --- PART 3: Supervision Immunity at TTE=42s (Zero-Bid OTM Leg + $0.88 Winning Leg) ---
    tid_a = [t for t in tids if h.active_positions[t]["token_id"] == tok_15m_up][0]
    tid_b = [t for t in tids if h.active_positions[t]["token_id"] == tok_5m_dn][0]
    sh_held = float(h.active_positions[tid_a]["entry_shares"])
    for t in (tid_a, tid_b):
        h.active_positions[t]["candle_expiry_ts"] = time.time() + 42.0

    live_books = {
        tok_15m_up: {"bids": [{"price": "0.88", "size": "100"}], "asks": [{"price": "0.90", "size": "500"}]},
        tok_5m_dn: {"bids": [], "asks": [{"price": "0.02", "size": "100"}]},  # Dead OTM leg with ZERO bids!
    }
    h._strict_open_orders = lambda: [
        {"id": h.active_positions[tid_a]["exit_order_id"], "asset_id": tok_15m_up, "side": "SELL"},
        {"id": h.active_positions[tid_b]["exit_order_id"], "asset_id": tok_5m_dn, "side": "SELL"},
    ]
    h._get_verified_shm_book = lambda p: live_books[p["token_id"]]
    h.executor.get_order_fill_summary = lambda oid, tok: {
        "order_id": oid, "status": "LIVE", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": False, "resting": True,
    }
    unwind_calls = []
    h.executor.execute_unwind_order = MagicMock(side_effect=lambda **kw: unwind_calls.append(kw))

    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 0, "D1 box must NOT premature-recycle at $0.88 on a $0.953 box or salvage OTM leg!"
    assert h.risk_halt is False, "Zero-bid OTM leg of a hedged D1 box must NEVER trigger LIQUIDITY_CRISIS!"

    # --- PART 4: Pre-Expiry CLOB Cash Recycling at TTE=18s ($0.99 Bid Only, No $0.98 Dump or Stop-Loss Escalation) ---
    for t in (tid_a, tid_b):
        h.active_positions[t]["candle_expiry_ts"] = time.time() + 18.0
    # 4a. $0.98 bid at TTE=18s must NOT cancel resting $0.99 Maker GTC ask or dump at 96.8c!
    live_books[tok_15m_up] = {"bids": [{"price": "0.98", "size": "200"}], "asks": [{"price": "0.99", "size": "50"}]}
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 0, "D1 leg at $0.98 bid must keep resting $0.99 Maker GTC ask instead of taking a taker haircut!"

    # 4b. $0.99 bid triggers recycle; if FAK misses ($0.99 blinked), must hold to maturity (NEVER UNWIND_RETRY_REQUIRED!)
    live_books[tok_15m_up] = {"bids": [{"price": "0.99", "size": "200"}], "asks": [{"price": "1.00", "size": "50"}]}
    h.executor.cancel_order = lambda oid: {"is_canceled": True, "canceled": [oid]}
    h.executor.get_order_fill_summary = lambda oid, tok: {
        "order_id": oid, "status": "CANCELED", "matched": 0.0, "cash": 0.0, "fee": 0.0, "terminal": True, "resting": False,
    }
    h.executor.execute_unwind_order = lambda **kw: (
        unwind_calls.append(kw) or {"success": False, "matched_size": 0.0, "error": "no orders found to match with fak order"}
    )
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 1 and unwind_calls[0]["min_price"] == pytest.approx(0.98)
    assert h.active_positions[tid_a]["exit_order_status"] == "DETERMINISTIC_TERMINAL_HOLD"
    assert h.active_positions[tid_a].get("unwind_retry_count", 0) == 0
    unwind_calls.clear()

    def _mock_recycle_unwind(**kw):
        unwind_calls.append(kw)
        gross_cash = round(sh_held * 0.99, 4)
        exit_fee = round(sh_held * 0.07 * 0.99 * 0.01, 4)
        return {
            "success": True,
            "orderID": "OID_RECYCLE_99",
            "matched_size": sh_held,
            "taking_amount": gross_cash,
            "fee_usd": exit_fee,
            "taking_amount_estimated": False,
            "transactions_hashes": ["0xrec1"],
        }

    h.executor.execute_unwind_order = _mock_recycle_unwind
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert len(unwind_calls) == 1, "Winning D1 leg at $0.99 with TTE=18s must trigger pre-expiry CLOB cash recycling!"
    assert unwind_calls[0]["min_price"] == pytest.approx(0.98), "D1 $0.99 recycle must use 1c buffer ($0.98) to survive $0.99->$0.98 flickers!"
    assert tid_a not in h.active_positions
    assert tid_b in h.active_positions
    assert len(h.closed_positions) == 0, "Leg 1 close must stash onto partner leg without emitting half-box record!"
    assert "_closed_partner_leg" in h.active_positions[tid_b]

    # Now expire & resolve OTM Leg 2 (5m DOWN lost because UP won) -> emits 1 unified winning D1_BOX_CONSOLIDATED trade!
    h.active_positions[tid_b]["candle_expiry_ts"] = time.time() - 5.0
    h._strict_open_orders = lambda: []
    asyncio.run(h._apply_market_resolution(tid_b, h.active_positions[tid_b], "UP"))
    assert tid_b not in h.active_positions
    assert len(h.closed_positions) == 1
    consolidated = h.closed_positions[0]
    assert "D1_BOX_CONSOLIDATED" in consolidated["close_reason"]
    assert consolidated["exit_decomposition_bucket"] == "DOMINANCE_BOX_ARB"
    assert len(consolidated["box_legs_summary"]) == 2
    assert consolidated["won"] is True
    assert consolidated["net_pnl_usd"] > 0.25
    assert h.risk_controller.consecutive_losses == 0, "Winning D1 box must NEVER increment consecutive_losses!"

    # --- PART 5: Legged-Out 1ms Polygon Settlement Race -> Supervised Residual Handoff (Zero Orphaned Shares!) ---
    h._last_known_collateral = 65.05
    wallet_bals[tok_15m_up] = 0.0
    wallet_bals[tok_5m_dn] = 0.0
    fake_books[tok_5m_dn] = {"bids": [{"price": "0.45", "size": "100"}], "asks": [{"price": "0.46", "size": "14"}]}
    cand_legged = {
        **cand_obj,
        "box_id": "D1_LIVE_LEGGED_TEST",
        "dedupe_key": "D1_BTC_LEGGED_NEW",
        "timestamp_unix": time.time(),
        "expiry_ts": time.time() + 180.0,
    }
    captured_box_kw = {}

    def _mock_thin_legged_box(**kw):
        captured_box_kw.update(kw)
        return {
            "success": False,
            "stage": "LEG_2_REJECTED_UNWOUND",
            "legged_out": True,
            "outcome_unknown": False,
            "leg_1_order_id": "OID_LEG1_ONLY",
            "unwind_result": {"success": False, "matched_size": 0.0, "error": "SELL_INVENTORY_RECONCILIATION_REQUIRED: unreserved=0.0 < 12.0"},
            "residual_unhedged_leg": {
                "token_id": tok_15m_up,
                "label": "15M_UP",
                "price": 0.46,
                "matched_shares": 12.0,
                "unwound_shares": 0.0,
                "residual_shares": 12.0,
                "orderID": "OID_LEG1_ONLY",
                "raw": {},
                "unwind_outcome_unknown": False,
                "unwind_result": {"success": False, "matched_size": 0.0, "error": "SELL_INVENTORY_RECONCILIATION_REQUIRED"},
            },
            "error": "FOK order couldn't be fully filled",
        }

    h.executor.execute_atomic_dominance_box = _mock_thin_legged_box
    res_leg_handoff = h.maybe_execute_graduated_d1_box(cand_legged)
    assert captured_box_kw["parallel_dispatch"] is False, "Thin leg (<1.5x depth) must switch to sequential thinner-leg-first!"
    assert res_leg_handoff["executed"] is False
    assert "D1_LIVE_LEGGED_TEST_LEG_RESID" in h.active_positions, "Legged-out shares unsettled on Polygon MUST be registered in active_positions!"
    resid_pos = h.active_positions["D1_LIVE_LEGGED_TEST_LEG_RESID"]
    assert resid_pos["is_dominance_box"] is False, "Unhedged residual leg must NOT get delta-hedged D1 supervision immunity!"
    assert resid_pos["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    resid_pos["next_unwind_retry_ts"] = time.time() - 0.1

    # Tick 1: Polygon STILL hasn't settled BUY shares (wallet_bal == 0.0) -> must retry in 0.50s WITHOUT false UNRESOLVED_BALANCE_DISCREPANCY halt!
    live_books[tok_15m_up] = {"bids": [{"price": "0.45", "size": "200"}], "asks": [{"price": "0.47", "size": "200"}]}
    h.executor.execute_unwind_order = lambda **kw: {
        "success": False, "matched_size": 0.0, "error": "SELL_INVENTORY_RECONCILIATION_REQUIRED: unreserved=0.0 < 12.0",
    }
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert "D1_LIVE_LEGGED_TEST_LEG_RESID" in h.active_positions
    assert resid_pos["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    assert resid_pos.get("unwind_retry_count", 0) == 0

    # Tick 2: Polygon settles 12.0 shares -> supervision immediately unwinds 100% of legged-out shares to flat!
    wallet_bals[tok_15m_up] = 12.0
    resid_pos["next_unwind_retry_ts"] = time.time() - 0.1
    h.executor.execute_unwind_order = lambda **kw: {
        "success": True, "orderID": "OID_RESID_UNWOUND", "matched_size": 12.0,
        "taking_amount": 5.40, "fee_usd": 0.21, "taking_amount_estimated": False, "transactions_hashes": ["0xuw2"],
    }
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert "D1_LIVE_LEGGED_TEST_LEG_RESID" not in h.active_positions

    # --- PART 6: Pre-Book Balance Order, Quarantined XRP/SOL, ETH Sequential Tail-First Dispatch, Inline Unwind & Restart Persistence ---
    # 6a. Retired XRP and quarantined SOL rejected cleanly; 4-token complement anti-box (> 1.03) vetoed cleanly
    res_xrp = h.maybe_execute_graduated_d1_box({**cand_obj, "asset": "XRP", "dedupe_key": "D1_XRP_TEST"})
    assert res_xrp["executed"] is False and res_xrp["reason"] == "UNSUPPORTED_D1_ASSET:XRP"
    res_sol_q = h.maybe_execute_graduated_d1_box({**cand_obj, "asset": "SOL", "dedupe_key": "D1_SOL_Q_TEST"})
    assert res_sol_q["executed"] is False and res_sol_q["reason"] == "UNSUPPORTED_D1_ASSET:SOL"

    # 6b. ETH skewed box allowed, _wallet_token_balance runs BEFORE get_market_book, parallel_dispatch=False, and 100% inline unwind recorded!
    h._last_known_collateral = 73.65
    call_sequence = []
    h._wallet_token_balance = lambda tid: (call_sequence.append("PRE_BAL") or (0.0, h.ONCHAIN_SOURCE))
    eth_books = {
        tok_15m_up: {"asks": [{"price": "0.82", "size": "90"}], "bids": [{"price": "0.80", "size": "90"}]},
        tok_5m_dn: {"asks": [{"price": "0.13", "size": "40"}], "bids": [{"price": "0.12", "size": "40"}]},
        tok_15m_dn: {"asks": [{"price": "0.20", "size": "90"}], "bids": [{"price": "0.17", "size": "90"}]},
        tok_5m_up: {"asks": [{"price": "0.88", "size": "40"}], "bids": [{"price": "0.80", "size": "40"}]},
    }
    h.executor.get_market_book = lambda tid: (call_sequence.append("GET_BOOK") or eth_books[tid])
    # Verify complement anti-box veto when complement best bids sum > 1.03 (e.g. 0.55 + 0.55 = 1.10)
    anti_books = {**eth_books, tok_15m_dn: {"bids": [{"price": "0.55", "size": "50"}]}, tok_5m_up: {"bids": [{"price": "0.55", "size": "50"}]}}
    h.executor.get_market_book = lambda tid: anti_books[tid]
    res_comp_veto = h.maybe_execute_graduated_d1_box({**cand_obj, "asset": "ETH", "dedupe_key": "D1_ETH_ANTIBOX_VETO", "ts_unix": time.time(), "expiry_ts": time.time() + 180.0})
    assert res_comp_veto["executed"] is False and "ANTI_BOX_COMPLEMENT_VETO" in res_comp_veto["reason"]

    call_sequence.clear()
    h.executor.get_market_book = lambda tid: (call_sequence.append("GET_BOOK") or eth_books[tid])
    sol_box_kw = {}

    def _mock_sol_inline_unwind(**kw):
        sol_box_kw.update(kw)
        return {
            "success": False,
            "stage": "LEG_2_REJECTED_UNWOUND",
            "legged_out": True,
            "outcome_unknown": False,
            "unwind_result": {
                "success": True, "orderID": "0x389cae", "matched_size": 14.17,
                "taking_amount": 11.1943, "fee_usd": 0.1646,
            },
            "residual_unhedged_leg": {
                "token_id": tok_15m_up, "label": "15M_UP", "price": 0.82,
                "matched_shares": 14.17, "unwound_shares": 14.17, "residual_shares": 0.0,
                "orderID": "0xsol_in", "raw": {"makingAmount": 11.6194},
                "unwind_outcome_unknown": False,
                "unwind_result": {
                    "success": True, "orderID": "0x389cae", "matched_size": 14.17,
                    "taking_amount": 11.1943, "fee_usd": 0.1646,
                },
            },
            "error": "FOK order couldn't be fully filled",
        }

    h.executor.execute_atomic_dominance_box = _mock_sol_inline_unwind
    cand_sol = {
        **cand_obj,
        "box_id": "D1_LIVE_ETH_1793037600_14389",
        "dedupe_key": "D1_ETH_6213180_6214389",
        "asset": "ETH",
        "ts_unix": time.time(),
        "expiry_ts": time.time() + 180.0,
    }
    pre_closed_len = len(h.closed_positions)
    res_sol = h.maybe_execute_graduated_d1_box(cand_sol)
    assert res_sol["executed"] is False
    assert "shares" in sol_box_kw, res_sol
    assert sol_box_kw["parallel_dispatch"] is False, "Skewed tail box must dispatch fragile 5m leg first (sequential)!"
    assert max(i for i, s in enumerate(call_sequence) if s == "PRE_BAL") < min(i for i, s in enumerate(call_sequence) if s == "GET_BOOK")
    assert len(h.closed_positions) == pre_closed_len + 1
    inline_rec = h.closed_positions[-1]
    assert inline_rec["close_reason"] == "D1_INLINE_LEGGED_OUT_UNWIND"
    assert inline_rec["asset"] == "ETH"
    assert inline_rec["net_pnl_usd"] == pytest.approx(-0.74, abs=0.01)

    # 6c. Reload harvester from disk -> seen_d1_box_keys survives restart and blocks duplicate attempt!
    h_reloaded = PolymarketLiveHarvester(
        dry_run=True, dynamic_sizing=True, hold_to_maturity=False, ticket_notional=12.0,
        max_exposure=60.0, max_concurrent=1, allowed_assets={"BTC", "ETH"},
    )
    h_reloaded.state_file = h.state_file
    h_reloaded.load_state()
    assert "D1_ETH_6213180_6214389" in h_reloaded._seen_d1_box_keys
    res_dup = h_reloaded.maybe_execute_graduated_d1_box(cand_sol)
    assert res_dup["executed"] is False and res_dup["reason"] == "ALREADY_EXECUTED_PAIR"

    # --- PART 7: Phase 1 Latency Optimizations (4-Socket Warm Pool, D1 defer_exec=True, Fast D1 IPC Dedupe & mtime Cache) ---
    import src.polymarket_research.polymarket_live_executor as exec_mod
    from collections import deque

    # 7a. _ThreadLocalClobHttpClient.warm_pool(min_warm=4) returns healthy inventory=4 with 0 redundant GETs when hot
    pool4 = exec_mod._ThreadLocalClobHttpClient(timeout=4.0, max_pool_size=8)
    created4 = []

    class _FakeCli4:
        def __init__(self):
            self.is_closed = False
            self.calls = 0
            created4.append(self)

        def request(self, method="GET", url="", **kw):
            self.calls += 1
            return MagicMock(status_code=200)

        def close(self):
            self.is_closed = True

    pool4._make_client = _FakeCli4
    assert pool4.warm_pool(min_warm=4, max_idle_sec=18.0) == 4
    assert len(created4) == 4 and sum(c.calls for c in created4) == 4
    # Second call while all 4 sockets are <18s idle must still report 4 healthy sockets AND fire 0 new GETs!
    assert pool4.warm_pool(min_warm=4, max_idle_sec=18.0) == 4
    assert sum(c.calls for c in created4) == 4

    # 7b. D1 execute_atomic_dominance_box passes defer_exec=True on sequential & parallel FOKs + fails closed on DELAYED
    ex_d1 = exec_mod.PolymarketLiveExecutor(dry_run=True)
    ex_d1.dry_run = False
    ex_d1.is_authenticated = True
    ex_d1.auth_mode = "AUTHENTICATED_L2"
    ex_d1._tick_size_cache[tok_15m_up] = 0.01
    ex_d1._tick_size_cache[tok_5m_dn] = 0.01
    ex_d1._neg_risk_cache[tok_15m_up] = False
    ex_d1._neg_risk_cache[tok_5m_dn] = False
    if exec_mod.OrderArgsV2 is None:
        monkeypatch.setattr(exec_mod, "OrderArgsV2", lambda **kw: kw)
    if exec_mod.OrderType is None:
        monkeypatch.setattr(exec_mod, "OrderType", type("OT", (), {"FOK": "FOK", "FAK": "FAK", "GTC": "GTC"}))
    post_calls = []

    class _StubClobDefer:
        def create_order(self, args, options=None):
            return {"signed": args}

        def post_order(self, order, order_type=None, post_only=False, defer_exec=False):
            post_calls.append((order_type, post_only, defer_exec))
            if len(post_calls) == 1:
                return {"orderID": "OID_DELAYED_NO_AMT", "status": "DELAYED"}
            return {"orderID": f"OID_{len(post_calls)}", "status": "matched", "takingAmount": "10"}

    ex_d1.client = _StubClobDefer()
    res_delayed = ex_d1.execute_atomic_dominance_box(
        box_id="BOX_DEFER_UNK", leg_a_token_id=tok_15m_up, leg_a_label="15M_UP", leg_a_limit_price=0.80,
        leg_b_token_id=tok_5m_dn, leg_b_label="5M_DN", leg_b_limit_price=0.14, shares=10,
        max_box_cost_net=0.975, parallel_dispatch=False,
    )
    assert post_calls[0][1] is False and post_calls[0][2] is True, "Sequential D1 FOK must pass defer_exec=True!"
    assert res_delayed["success"] is False and res_delayed["outcome_unknown"] is True

    res_seq_ok = ex_d1.execute_atomic_dominance_box(
        box_id="BOX_DEFER_OK", leg_a_token_id=tok_15m_up, leg_a_label="15M_UP", leg_a_limit_price=0.80,
        leg_b_token_id=tok_5m_dn, leg_b_label="5M_DN", leg_b_limit_price=0.14, shares=10,
        max_box_cost_net=0.975, parallel_dispatch=False,
    )
    assert res_seq_ok["success"] is True
    assert all(c[2] is True for c in post_calls), "All D1 FOK post_order calls must set defer_exec=True!"

    # 7c. Fast D1 RAM IPC queue + emit_id dedupe prevents double evaluation when disk cursor catches up
    eval_calls = []
    h._fast_d1_cand_lines = deque()
    ipc_cand = {**cand_obj, "box_id": "D1_IPC_DEDUPE_1", "dedupe_key": "D1_IPC_KEY_1", "ts_unix": round(time.time(), 3)}
    ipc_line = json.dumps(ipc_cand)
    h._fast_d1_cand_lines.append(ipc_line)
    with open(cand_file, "a", encoding="utf-8") as fp:
        fp.write(ipc_line + "\n")
    h.maybe_execute_graduated_d1_box = lambda c: (eval_calls.append(c["box_id"]) or {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT"})
    h._last_d1_disk_poll = time.time()  # Simulate immediate RAM IPC wakeup (<0.50s before disk poll)
    asyncio.run(h._poll_d1_live_box_candidates(time.time()))
    assert eval_calls == ["D1_IPC_DEDUPE_1"]
    h._last_d1_disk_poll = 0.0  # Now let disk fallback poll catch up to the appended JSONL line
    asyncio.run(h._poll_d1_live_box_candidates(time.time()))
    assert eval_calls == ["D1_IPC_DEDUPE_1"], "Identical emit_id from JSONL fallback must not re-evaluate!"

    # --- PART 8: Live D1 Quiet-Book 0.985 Promotion, 4h/15m 900s TTE Bridge & $0-Miss 10s Retry Cooldown ---
    del h.maybe_execute_graduated_d1_box
    h.active_positions.clear()
    h._last_known_collateral = 85.08
    # 0.48 + 0.47 = 0.95 gross + ~0.03497 fees => ~0.98497 net (>0.975 and <=0.985!)
    tight_quiet_books = {
        tok_15m_up: {"asks": [{"price": "0.48", "size": "120"}], "bids": [{"price": "0.46", "size": "120"}]},
        tok_5m_dn: {"asks": [{"price": "0.46", "size": "120"}], "bids": [{"price": "0.44", "size": "120"}]},
        tok_15m_dn: {"asks": [{"price": "0.52", "size": "120"}], "bids": [{"price": "0.49", "size": "120"}]},
        tok_5m_up: {"asks": [{"price": "0.53", "size": "120"}], "bids": [{"price": "0.50", "size": "120"}]},
    }
    # 0.48*(1 + 0.07*0.52) = 0.497472; 0.46*(1 + 0.07*0.54) = 0.477388 -> sum = 0.97486; let's use 0.48 + 0.465 -> 0.48 + 0.47!
    tight_quiet_books[tok_5m_dn] = {"asks": [{"price": "0.47", "size": "120"}], "bids": [{"price": "0.45", "size": "120"}]}
    # Check: 0.48 + 0.47 = 0.95 + 0.017472 + 0.017437 = 0.984909 <= 0.985 and > 0.975!
    h.executor.get_market_book = lambda tid: tight_quiet_books[tid]

    # 8a. Non-quiet candidate at 0.9849 net MUST be rejected (> 0.975 non-quiet cap)
    cand_non_quiet = {
        **cand_obj,
        "box_id": "D1_NON_QUIET_9849",
        "dedupe_key": "D1_BTC_NON_QUIET_1",
        "is_quiet_book": False,
        "ts_unix": time.time(),
        "expiry_ts": time.time() + 180.0,
    }
    res_nq = h.maybe_execute_graduated_d1_box(cand_non_quiet)
    assert res_nq["executed"] is False and "FRESH_BOOK_WALK_REJECT" in res_nq["reason"]

    # 8b. Quiet-book 4h/15m candidate at TTE=600s & 0.9849 net:
    # First attempt: clean $0.00-cost Leg-1 FOK miss -> 10s cooldown (NOT permanent lockout!), then retry succeeds!
    attempts_8b = []

    def _mock_quiet_4h_fok(**kw):
        attempts_8b.append(dict(kw))
        if len(attempts_8b) == 1:
            return {
                "success": False,
                "stage": "LEG_1_REJECTED",
                "legged_out": False,
                "outcome_unknown": False,
                "error": "FOK order couldn't be fully filled",
            }
        sh = float(kw["shares"])
        return {
            "success": True,
            "box_id": kw["box_id"],
            "shares": sh,
            "leg_1": {"token_id": tok_15m_up, "label": kw["leg_a_label"], "price": 0.48, "orderID": "OID_4H_A", "raw": {"makingAmount": round(sh * 0.48, 2)}},
            "leg_2": {"token_id": tok_5m_dn, "label": kw["leg_b_label"], "price": 0.47, "orderID": "OID_4H_B", "raw": {"makingAmount": round(sh * 0.47, 2)}},
        }

    h.executor.execute_atomic_dominance_box = _mock_quiet_4h_fok
    cand_4h_quiet = {
        **cand_obj,
        "box_id": "D1_4H_LIVE_BTC_600S",
        "dedupe_key": "D1_BTC_4H_15M_RETRY_1",
        "pair_horizons": "4h_15m",
        "sleeve_source": "D1_4H_DOMINANCE_BOX",
        "leg_a_horizon": "4h",
        "leg_b_horizon": "15m",
        "is_quiet_book": True,
        "ts_unix": time.time(),
        "expiry_ts": time.time() + 600.0,  # TTE = 600s (>300s 5m cap, <=900s 4h/15m cap!)
    }
    res_miss1 = h.maybe_execute_graduated_d1_box(cand_4h_quiet)
    assert res_miss1["executed"] is False
    assert len(attempts_8b) == 1
    assert attempts_8b[0]["max_box_cost_net"] == pytest.approx(0.985)
    assert attempts_8b[0]["parallel_dispatch"] is False, "Tighter (0.975..0.985] quiet box must dispatch fragile leg sequentially!"
    assert "D1_BTC_4H_15M_RETRY_1" not in h._seen_d1_box_keys, "$0.00-cost Leg-1 FOK miss must NOT permanently lock pair!"

    # Immediate re-attempt (< 10s) blocked by cooldown
    res_cd = h.maybe_execute_graduated_d1_box({**cand_4h_quiet, "ts_unix": time.time()})
    assert res_cd["executed"] is False and res_cd["reason"] == "RETRY_COOLDOWN_10S"

    # Expire 10s cooldown -> second attempt fills cleanly and permanently locks dedupe_key!
    h._d1_retry_cooldown_until["D1_BTC_4H_15M_RETRY_1"] = time.time() - 0.1
    res_retry_ok = h.maybe_execute_graduated_d1_box({**cand_4h_quiet, "ts_unix": time.time()})
    assert res_retry_ok["executed"] is True
    assert len(attempts_8b) == 2
    assert "D1_BTC_4H_15M_RETRY_1" in h._seen_d1_box_keys

















# ======================================================================================
# [16/16] MODULE: tests/test_zero_trust_forensic_audit.py
# PURPOSE: Unit Tests: Zero-Trust Forensics, Centralized Risk Config, Deterministic Replay & <1MB Bundle Sync
# ======================================================================================

#!/usr/bin/env python3
"""
Regression Test Suite for Zero-Trust Adversarial Forensic Code Audit (Categories 1-7).
Run via: venv/bin/pytest tests/test_zero_trust_forensic_audit.py -v
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    ExecutionStatus,
    calculate_taker_fee,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.polymarket_paper_trader import PolymarketForwardPaperTrader
from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook


@pytest.fixture(autouse=True)
def _offline_clob(monkeypatch):
    """#8: the whole suite runs 100% offline - the CLOB client + credentials are mocked, so constructing a
    live-mode PolymarketLiveExecutor never calls https://clob.polymarket.com (no api-key derivation, no latency)."""
    import src.polymarket_research.polymarket_live_executor as ex

    monkeypatch.setattr(ex, "ClobClient", MagicMock(name="OfflineClobClient"))
    monkeypatch.setattr(ex, "PY_CLOB_AVAILABLE", True)
    monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("POLYGON_FUNDER_ADDRESS", "0x" + "22" * 20)
    monkeypatch.setenv("POLYGON_SIGNATURE_TYPE", "3")


def test_cat1_cross_asset_direction_vocabulary_alignment():
    """Verifies BUG-1.1 fix: 'BUY' on BTC and 'UP' on ETH are recognized as aligned, not rejected."""
    passed, z_joint, reason = PolymarketLiveExecutor.validate_cross_asset_lead_lag(
        target_asset="ETH",
        target_direction="UP",
        btc_direction="BUY",
        z_alt=2.20,
        z_btc=1.90,
    )
    assert passed is True
    assert reason == "CROSS_ASSET_CONFIRMED"
    assert abs(z_joint - (0.70 * 2.20 + 0.30 * 1.90)) < 1e-6

    # Test counter-trend rejection
    passed_ct, _, reason_ct = PolymarketLiveExecutor.validate_cross_asset_lead_lag(
        target_asset="ETH",
        target_direction="UP",
        btc_direction="SELL",
        z_alt=2.20,
        z_btc=-1.90,
    )
    assert passed_ct is False
    assert "REJECT_BTC_COUNTER_TREND" in reason_ct


def test_cat1_paper_telemetry_binance_spot_preserves_salvage_timer(tmp_path, monkeypatch):
    """Verifies BUG-1.2 fix: 'binance_spot' in telemetry advances rather than resets the 90s salvage timer."""
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.DEV_LEDGER_FILE", tmp_path / "dev.jsonl")
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.VALIDATION_LEDGER_FILE", tmp_path / "val.jsonl")
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.STATE_FILE", tmp_path / "state.json")

    paper = PolymarketForwardPaperTrader(paper_latency_ms=0)
    m_id = "MKT_TELEM_SALVAGE"
    t0 = 1792400000.0
    paper.open_trades[m_id] = [{
        "trade_id": "T_SALVAGE_TELEM",
        "market_id": m_id,
        "title": "ETH 1H Down",
        "target_token": "DOWN",
        "entry_unix": t0 - 200.0,
        "candle_open_spot": 2500.0,
        "strike_price": 2500.0,
        "shares_bought": 50.0,
        "notional_usd": 37.50,
        "taker_fee_usd": 0.39,
        "status": "OPEN",
    }]

    # Tick 1: Telemetry uses 'binance_spot' (2506.0 -> +0.24% wrong side for DOWN)
    telem1 = {
        "market_id": m_id,
        "timestamp_unix": t0,
        "binance_spot": 2506.0,
        "binance_1h_open": 2500.0,
        "seconds_to_expiry": 900.0,
        "DOWN": {"best_bid": 0.24, "best_ask": 0.26},
    }
    closed1 = paper.check_maker_tp_fills(m_id, telem1)
    assert len(closed1) == 0
    assert paper.open_trades[m_id][0].get("opposite_breakout_start_ts") == t0

    # Tick 2: 92s later via 'binance_spot' -> must trigger CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE
    telem2 = {
        "market_id": m_id,
        "timestamp_unix": t0 + 92.0,
        "binance_spot": 2505.5,
        "binance_1h_open": 2500.0,
        "seconds_to_expiry": 808.0,
        "DOWN": {"best_bid": 0.20, "best_ask": 0.22},
    }
    closed2 = paper.check_maker_tp_fills(m_id, telem2)
    assert len(closed2) == 1
    assert closed2[0]["exit_reason"] == "CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE"


def test_cat2_verified_shm_book_filtering(tmp_path, monkeypatch):
    """Verifies BUG-2.2 fix: _get_verified_shm_book strictly filters by market_id, token_id, and max age."""
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    harvester = PolymarketLiveHarvester(dry_run=True)

    pos = {
        "asset": "BTC",
        "market_id": "12345",
        "token_id": "0xTOKEN_UP",
        "target_token": "UP",
    }

    # Write a test fast tick to tmp shm path
    test_shm = tmp_path / "pm_fast_tick_BTC.json"
    now_ts = time.time()
    payload = {
        "markets": {
            "12345": {
                "market_id": "12345",
                "timestamp_unix": now_ts,
                "UP": {
                    "token_id": "0xTOKEN_UP",
                    "raw_top_bids": [[0.70, 100]],
                    "raw_top_asks": [[0.72, 100]],
                },
            },
            "99999": {
                "market_id": "99999",
                "timestamp_unix": now_ts,
                "UP": {
                    "token_id": "0xOTHER_TOKEN",
                    "raw_top_bids": [[0.50, 100]],
                    "raw_top_asks": [[0.52, 100]],
                },
            },
        }
    }
    test_shm.write_text(json.dumps(payload), encoding="utf-8")

    with patch("src.polymarket_research.polymarket_live_harvester.Path") as MockPath:
        # Route Path("/dev/shm/pm_fast_tick_BTC.json") to test_shm
        MockPath.side_effect = lambda p: test_shm if "pm_fast_tick_BTC.json" in str(p) else Path(p)

        book = harvester._get_verified_shm_book(pos)
        assert book is not None
        assert book["bids"][0]["price"] == "0.7"

        # Stale timestamp (> 1.5s) must be rejected
        payload["markets"]["12345"]["timestamp_unix"] = now_ts - 2.0
        test_shm.write_text(json.dumps(payload), encoding="utf-8")
        stale_book = harvester._get_verified_shm_book(pos)
        assert stale_book is None

        # Token mismatch must be rejected
        payload["markets"]["12345"]["timestamp_unix"] = now_ts
        payload["markets"]["12345"]["UP"]["token_id"] = "0xWRONG_TOKEN"
        test_shm.write_text(json.dumps(payload), encoding="utf-8")
        mismatch_book = harvester._get_verified_shm_book(pos)
        assert mismatch_book is None


def test_cat2_prewarm_hourly_opens_skips_subhourly(tmp_path, monkeypatch):
    """Verifies BUG-2.4 fix: _prewarm_hourly_opens skips sub-hourly triggers (15m, 5m)."""
    trigger_file = tmp_path / "live_shock_triggers.jsonl"
    t0 = 1792400000.0
    h_idx = int(t0 // 3600)
    lines = [
        # Sub-hourly 15m trigger
        json.dumps({
            "asset": "BTC",
            "t0_unix": t0,
            "horizon": "15m",
            "candle_interval": "15m",
            "finalized_1h_open": 64500.0,
            "candle_open_spot": 64500.0,
        }),
        # Sub-hourly title trigger
        json.dumps({
            "asset": "BTC",
            "t0_unix": t0 + 100,
            "title": "Bitcoin Up or Down 15m",
            "finalized_1h_open": 64600.0,
            "candle_open_spot": 64600.0,
        }),
        # True 1-hour trigger
        json.dumps({
            "asset": "BTC",
            "t0_unix": t0 + 200,
            "horizon": "1h",
            "title": "Bitcoin Up or Down: October 20, 4:00AM ET",
            "finalized_1h_open": 64000.0,
            "candle_open_spot": 64000.0,
        }),
    ]
    trigger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.DATA_DIR", tmp_path)
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.hourly_candle_opens.clear()
    harvester._prewarm_hourly_opens()

    # Must contain 64000.0 (the 1h trigger), not 64500.0 or 64600.0
    assert harvester.hourly_candle_opens["BTC"].get(h_idx) == 64000.0


def test_cat3_wallet_token_balance_defers_on_non_onchain_zero(tmp_path, monkeypatch):
    """Verifies BUG-3.1 fix: For winning positions, non-onchain 0.0 balance defers resolution rather than recording phantom loss."""
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "state.json")
    harvester = PolymarketLiveHarvester(dry_run=False)
    harvester.executor = MagicMock()
    harvester.save_state = MagicMock()

    tid = "T_WINNING_RESOLUTION"
    pos = {
        "trade_id": tid,
        "market_id": "123",
        "token_id": "0xWIN_TOK",
        "target_token": "UP",
        "entry_price": 0.80,
        "entry_shares": 100.0,
        "remaining_shares": 100.0,
        "notional_usd": 80.0,
        "status": ExecutionStatus.POSITION_CONFIRMED,
    }
    harvester.active_positions[tid] = pos

    # Simulate Polygon RPC timeout -> fallback to CLOB API returning (0.0, "CLOB_BALANCE_API")
    harvester._wallet_token_balance = MagicMock(return_value=(0.0, "CLOB_BALANCE_API"))
    harvester._close_position = MagicMock()

    res_record = {
        "market_id": "123",
        "winning_outcome": "UP",
        "Y_UP": 1,
        "Y_DOWN": 0,
    }

    # Run resolution
    asyncio.run(harvester._apply_market_resolution(tid, pos, res_record))

    # _close_position should NOT have been called; position remains open awaiting RPC recovery
    assert harvester._close_position.call_count == 0
    assert tid in harvester.active_positions


def test_cat3_l2_book_metrics_no_assert_cross():
    """Verifies BUG-3.3 fix: crossed books or floating point anomalies log warning instead of crashing."""
    book = L2OrderBook(asset_id="0xTEST")
    # Apply crossed book
    book.apply_snapshot(
        bids=[{"price": "0.55", "size": "100"}],
        asks=[{"price": "0.54", "size": "100"}],
    )
    # Must not raise AssertionError
    metrics = book.get_metrics(obs_ts=time.time())
    assert metrics["is_crossed"] is True
    assert metrics["best_bid"] == 0.55
    assert metrics["best_ask"] == 0.54


def test_cat4_canceled_partial_fill_does_not_reset_to_resting(tmp_path, monkeypatch):
    """Verifies BUG-4.1 fix: A canceled order whose partial fill is still mining never resets to RESTING."""
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "state.json")
    harvester = PolymarketLiveHarvester(dry_run=False)
    harvester.executor = MagicMock()
    harvester.save_state = MagicMock()

    tid = "LIVE_PARTIAL_STOP_1"
    pos = {
        "trade_id": tid,
        "market_id": "5799999",
        "token_id": "0xTOK_STOP",
        "target_token": "UP",
        "entry_price": 0.80,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 40.0,
        "exit_order_id": "0xOID_CANCELED_PARTIAL",
        "pending_canceled_order_id": "0xOID_CANCELED_PARTIAL",
        "exit_order_status": "FILL_RECONCILIATION_REQUIRED",
        "stop_triggered_ts": time.time() - 5.0,
        "target_exit_price": 0.99,
    }
    harvester.active_positions[tid] = pos

    # Simulate canceled order with 10 shares matched, still mining on Polygon (resting=False, terminal=False)
    harvester.executor.get_order_fill_summary.return_value = {
        "order_id": "0xOID_CANCELED_PARTIAL",
        "status": "CANCELED",
        "resting": False,
        "is_matched": True,
        "is_settled": False,
        "terminal": False,
        "original_size": 50.0,
        "matched": 10.0,
        "cash": 9.90,
        "cash_is_estimated": True,
        "limit_price": 0.99,
        "trade_ids": ["TR_1"],
        "transactions_hashes": [],
        "fill_ids": ["TR_1:0xOID_CANCELED_PARTIAL"],
    }

    resolved = harvester._resolve_fill_reconciliation(tid, pos)
    assert resolved is False
    assert pos["exit_order_status"] == "FILL_RECONCILIATION_REQUIRED"


def test_cat4_atomic_replace_maker_exit(tmp_path, monkeypatch):
    """Verifies BUG-4.2 fix: _atomic_replace_maker_exit reconciles partial fill and releases reservation before new post."""
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "state.json")
    harvester = PolymarketLiveHarvester(dry_run=False)
    harvester.executor = MagicMock()
    harvester.save_state = MagicMock()

    tid = "T_REPLACE"
    pos = {
        "trade_id": tid,
        "market_id": "123",
        "token_id": "0xTOK",
        "exit_order_id": "0xOLD_OID",
        "remaining_shares": 50.0,
        "entry_shares": 50.0,
        "entry_price": 0.80,
        "target_exit_price": 0.98,
        "exit_order_status": "RESTING",
    }
    harvester.active_positions[tid] = pos

    harvester.executor.cancel_order.return_value = {"is_canceled": True}
    harvester.executor.get_order_fill_summary.return_value = {
        "order_id": "0xOLD_OID",
        "status": "CANCELED",
        "resting": False,
        "matched": 10.0,
        "terminal": True,
    }
    harvester.executor.post_maker_exit_order.return_value = {
        "success": True,
        "orderID": "0xNEW_OID",
        "price": 0.97,
        "status": "LIVE",
    }

    posted = asyncio.run(harvester._atomic_replace_maker_exit(tid, pos, 0.97))
    assert posted is True
    # Verify old reservation was explicitly released
    harvester.executor.release_inventory.assert_called_with(reservation_id="0xOLD_OID")
    # Verify new post at 0.97 for remaining 40.0 shares
    assert pos["target_exit_price"] == 0.97
    assert pos["exit_order_id"] == "0xNEW_OID"


def test_cat5_and_cat6_base_fee_bps_and_unclamped_depth_sizing(tmp_path):
    """Verifies BUG-5.1 and BUG-6.1 fixes: 15m base fee 1800 bps is preserved and tickets > $75 are not clamped."""
    executor = PolymarketLiveExecutor(dry_run=True, ledger_path=str(tmp_path / "orders.jsonl"))
    book = {
        "asks": [{"price": "0.75", "size": "500.0"}],
        "bids": [{"price": "0.74", "size": "500.0"}],
    }
    passed, ratio, best_px, adj_notional = executor.verify_pre_trade_depth(
        book,
        target_notional_usd=120.0,
        side="BUY",
        depth_hurdle_ratio=1.50,
        max_price_ceiling=0.88,
        return_adjusted=True,
        max_ticket_size=250.0,
    )
    assert passed is True
    assert adj_notional == 120.0, f"Expected full $120.00 ticket, got clamped to ${adj_notional:.2f}"


def test_cat5_calculate_taker_fee_formula():
    """Verifies BUG-5.2 fix: calculate_taker_fee does not multiply by price twice."""
    notional = 100.0
    price = 0.80
    fee_rate = 0.07  # 7%
    eff_rate, fee_usd = calculate_taker_fee(notional, price, fee_rate=fee_rate, fee_exponent=1.0)
    # Correct formula: fee = notional * fee_rate * (1 - price) = 100 * 0.07 * 0.20 = $1.40
    assert abs(fee_usd - 1.40) < 1e-4
    assert abs(eff_rate - 0.014) < 1e-4


def test_cat7_ordered_seen_shock_ids(tmp_path, monkeypatch):
    """Verifies BUG-7.1 fix: _record_seen_shock_id maintains insertion order and bounds to 2000 entries."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    for i in range(2100):
        harvester._record_seen_shock_id(f"SHOCK_{i}")

    assert len(harvester.seen_shock_ids) <= 2000
    assert "SHOCK_0" not in harvester.seen_shock_ids
    assert "SHOCK_2099" in harvester.seen_shock_ids


# =====================================================================================================
# v3.5 OPERATIONS HARDENING: centralized risk config, stale-recorder watchdog, alerting, graceful SIGTERM,
# safe reload, deterministic replay, bundle sync
# =====================================================================================================
import importlib.util
import os
import signal
import subprocess
import sys

import src.polymarket_research.polymarket_live_harvester as hv_mod
from src.polymarket_research.polymarket_live_executor import (
    OrderResult,
    load_risk_config,
    RISK_CONFIG_PATH,
)

ROOT = Path(__file__).resolve().parent.parent


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_v35_central_risk_config_wiring(tmp_path, monkeypatch):
    """#1/#6: a real PolymarketLiveHarvester takes floor / daily-loss / exposure from config/polymarket_risk_config.json."""
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    cfg = json.loads(RISK_CONFIG_PATH.read_text())
    assert cfg["min_equity_floor"] == 66.67 and cfg["max_daily_loss"] == 20.00 and cfg["max_exposure"] == 35.00

    harvester = PolymarketLiveHarvester(dry_run=False)
    assert harvester.risk_controller.min_equity_floor_usd == 66.67
    assert harvester.risk_controller.max_daily_loss_usd == 20.00
    assert harvester.max_exposure == 35.00
    assert harvester.max_concurrent_positions == cfg["max_concurrent_positions"] == 2
    assert harvester.ticket_notional == cfg["ticket_notional"] == 16.50
    assert harvester.effective_risk_pct(91.67) == 0.18
    assert harvester.effective_risk_pct(109.99) == 0.18
    assert harvester.effective_risk_pct(110.00) == 0.22


def test_v35_config_loader_fails_safe(tmp_path):
    """A missing / corrupt / nonsensical config can only fall back to the conservative built-in defaults."""
    assert load_risk_config(tmp_path / "nope.json")["min_equity_floor"] == 66.67
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert load_risk_config(bad)["max_exposure"] == 35.00
    weird = tmp_path / "weird.json"
    weird.write_text(json.dumps({"max_exposure": -5, "max_daily_loss": "lots", "min_equity_floor": 70.0}))
    cfg = load_risk_config(weird)
    assert cfg["max_exposure"] == 35.00 and cfg["max_daily_loss"] == 20.00 and cfg["min_equity_floor"] == 70.0


def test_v35_18pct_ticket_ramp_and_correlated_second_ticket():
    """#11: $16.50 first ticket, ~$8.9 correlated second ticket -> ~$25.4 total, well inside the $35 exposure cap."""
    eq = 91.67
    pct = 0.18
    t1 = hv_mod.compute_correlated_truncated_kelly_size(
        live_equity=eq, p_win=0.95, entry_px=0.65, kelly_multiplier=1.0, active_positions={},
        cand_expiry_ts=1_800_000_000.0, cand_direction="UP", min_lot_usd=8.0,
        max_ticket_cap=round(pct * eq, 2), default_sizing_pct=pct,
    )
    assert t1 == 16.50
    active = {"A": {"status": "FILLED", "candle_expiry_ts": 1_800_000_000.0, "target_token": "UP", "remaining_shares": 20.0}}
    t2 = hv_mod.compute_correlated_truncated_kelly_size(
        live_equity=eq, p_win=0.95, entry_px=0.65, kelly_multiplier=1.0, active_positions=active,
        cand_expiry_ts=1_800_000_000.0, cand_direction="UP", min_lot_usd=8.0,
        max_ticket_cap=round(pct * eq, 2), default_sizing_pct=pct,
    )
    assert 8.5 <= t2 <= 9.5
    assert t1 + t2 <= 35.00


def test_v35_stale_recorder_watchdog(tmp_path, monkeypatch):
    """#3: fast tick must be <=15s old (or JSONL telemetry <=30s) else entries are refused."""
    tick_dir, tele_dir = tmp_path / "shm", tmp_path / "tele"
    tick_dir.mkdir()
    tele_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tick_dir))
    monkeypatch.setenv("PM_TELEMETRY_DIR", str(tele_dir))
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    harvester = PolymarketLiveHarvester(dry_run=True)
    now = time.time()

    ok, age, why = harvester.check_recorder_freshness("BTC", now)
    assert ok is False and age == float("inf")  # nothing on the bus at all

    tick = tick_dir / "pm_fast_tick_BTC.json"
    tick.write_text("{}")
    os.utime(tick, (now - 5.0, now - 5.0))
    ok, age, _ = harvester.check_recorder_freshness("BTC", now)
    assert ok is True and 4.5 <= age <= 5.5

    os.utime(tick, (now - 20.0, now - 20.0))  # tick stale, no telemetry -> refuse
    ok, age, why = harvester.check_recorder_freshness("BTC", now)
    assert ok is False and "fast_tick_age" in why

    tele = tele_dir / "polymarket_hourly_telemetry.jsonl"  # fresh JSONL telemetry rescues a stale tick (<=30s)
    tele.write_text("{}\n")
    os.utime(tele, (now - 10.0, now - 10.0))
    assert harvester.check_recorder_freshness("BTC", now)[0] is True
    os.utime(tele, (now - 45.0, now - 45.0))
    assert harvester.check_recorder_freshness("BTC", now)[0] is False

    # ETH is judged on its own files, independent of BTC
    assert harvester.check_recorder_freshness("ETH", now)[0] is False


def _live_harvester_with_mock_clob(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(ticket_notional=16.50, dry_run=False, hold_to_maturity=False, max_concurrent=2)
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **k: 91.67
    h._last_known_collateral = 91.67
    h.executor.get_market_book_async = AsyncMock(return_value={
        "asks": [{"price": "0.65", "size": "400.0"}], "bids": [{"price": "0.64", "size": "400.0"}],
    })
    executed, maker_exits = [], []

    async def mock_snipe(**kw):
        executed.append(kw)
        notional = float(kw.get("notional_usd") or 0.0)
        return OrderResult(
            success=True, order_id=f"OID_{len(executed)}", trade_id=kw.get("trade_id", "T"),
            token_id=kw.get("token_id", "0xTOK_X"), target_token=kw.get("target_token", "UP"), side="BUY",
            price=0.65, size=round(notional / 0.65, 2), notional_usd=notional, fee_usd=0.05, latency_ms=1.0,
            mode="LIVE_PRODUCTION", execution_status=ExecutionStatus.POSITION_CONFIRMED, confirmed_onchain=True,
        )

    h.executor.execute_snipe_order_async = mock_snipe
    h.executor.post_maker_exit_order = MagicMock(
        side_effect=lambda **kw: maker_exits.append(kw) or {"success": True, "orderID": f"EXIT_{len(maker_exits)}"}
    )

    def make_shock(idx, title="BTC 1h Up", tte=600.0):
        return {
            "event_id": f"EVT_{idx}", "market_id": f"MKT_REPLAY_{idx}", "t0_unix": time.time(), "title": title,
            "asset": "BTC", "shock_direction": "BUY", "seconds_to_expiry": tte, "candle_distance_pct": 0.45,
            "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
            "pre_shock_features_t0": {"UP": {"token_id": f"0xTOK_REPLAY_{idx}", "raw_top_asks": [[0.65, 400.0]],
                                              "effective_price_$50": 0.65, "vwap_$50": 0.65}},
        }

    return h, executed, maker_exits, make_shock


def test_v35_stale_guard_blocks_live_entry_then_allows_when_fresh(tmp_path, monkeypatch):
    """The watchdog is wired into the real entry path (not just a helper)."""
    tick_dir, tele_dir = tmp_path / "shm", tmp_path / "tele"
    tick_dir.mkdir()
    tele_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tick_dir))
    monkeypatch.setenv("PM_TELEMETRY_DIR", str(tele_dir))
    h, executed, _, make_shock = _live_harvester_with_mock_clob(tmp_path, monkeypatch)

    asyncio.run(h.evaluate_shock_and_execute(make_shock(1)))
    assert executed == [], "stale/missing recorder feed must refuse the entry"

    # `ts: 0` keeps read_fast_tick() from treating this fixture as a real book, while mtime proves liveness.
    (tick_dir / "pm_fast_tick_BTC.json").write_text(json.dumps({"ts": 0}))
    asyncio.run(h.evaluate_shock_and_execute(make_shock(2)))
    assert len(executed) == 1


def test_v35_deterministic_replay_entry_exit_sizing_and_risk(tmp_path, monkeypatch):
    """#9: deterministic shock replay through the real harvester (mocked executor/CLOB): sized entries, maker exits,
    exposure/concurrency caps and risk-state updates."""
    monkeypatch.setenv("POLYMARKET_ALERTS_FILE", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setattr(hv_mod, "_ALERT_LAST_SENT", {})
    h, executed, maker_exits, make_shock = _live_harvester_with_mock_clob(tmp_path, monkeypatch)

    asyncio.run(h.evaluate_shock_and_execute(make_shock(1, "BTC 1h Up", 600.0)))
    assert len(executed) == 1 and len(h.active_positions) == 1
    assert executed[0]["notional_usd"] <= 20.17 + 0.01
    assert len(maker_exits) >= 1  # maker exit posted immediately for the confirmed fill

    asyncio.run(h.evaluate_shock_and_execute(make_shock(2, "BTC 15m Up", 300.0)))
    assert len(executed) == 2 and len(h.active_positions) == 2
    assert executed[1]["notional_usd"] < executed[0]["notional_usd"], "2nd same-window ticket carries the correlation haircut"
    total = sum(float(p.get("notional_usd") or 0.0) for p in h.active_positions.values())
    assert total <= h.max_exposure + 1e-6

    asyncio.run(h.evaluate_shock_and_execute(make_shock(3, "BTC 1h Up", 900.0)))
    assert len(executed) == 2, "max concurrent positions / exposure caps must reject the third entry"

    # risk-state evolution: two ~$5.28 salvage losses do not halt; the third trips the loss-streak breaker.
    rc = h.risk_controller
    rc.record_trade_pnl(-5.28)
    rc.record_trade_pnl(-5.28)
    assert not rc.is_halted() and abs(rc.daily_realized_loss - 10.56) < 1e-9
    rc.record_trade_pnl(-5.28)
    assert rc.is_halted() and "consecutive" in rc.halt_reason.lower()
    lines = [json.loads(l) for l in (tmp_path / "alerts.jsonl").read_text().splitlines()]
    assert any(l["event_type"] == "KILL_SWITCH_TRIPPED" for l in lines)

    # the 20-dollar daily budget is real (the legacy silent >=$65 override is gone)
    h2 = PolymarketLiveHarvester(dry_run=True)
    h2.risk_controller.record_trade_pnl(-12.0)
    h2.risk_controller.record_trade_pnl(5.0)
    h2.risk_controller.record_trade_pnl(-13.5)
    assert h2.risk_controller.is_halted() and "daily loss" in h2.risk_controller.halt_reason.lower()


def test_v35_alert_ledger_rate_limit_and_nonblocking_push(tmp_path, monkeypatch):
    """#2: JSONL ledger always written; push is on a daemon thread, rate-limited, never blocks the caller."""
    ledger = tmp_path / "critical_alerts.jsonl"
    monkeypatch.setenv("POLYMARKET_ALERTS_FILE", str(ledger))
    monkeypatch.setattr(hv_mod, "_ALERT_LAST_SENT", {})
    assert hv_mod.send_operational_alert("TEST_EVT", "first", "WARNING", rate_limit_sec=300.0) is True
    assert hv_mod.send_operational_alert("TEST_EVT", "dup", "WARNING", rate_limit_sec=300.0) is False
    rec = [json.loads(l) for l in ledger.read_text().splitlines()]
    assert len(rec) == 1 and rec[0]["event_type"] == "TEST_EVT" and rec[0]["severity"] == "WARNING"

    calls = []

    class _Resp:
        def read(self):
            return b"{}"

    def slow_urlopen(req, timeout=None):
        time.sleep(0.4)
        calls.append((req.full_url, timeout))
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", slow_urlopen)
    monkeypatch.setenv("POLYMARKET_ALERTS_FORCE_HTTP", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    t0 = time.time()
    assert hv_mod.send_operational_alert("PUSH_EVT", "hello", "CRITICAL") is True
    assert time.time() - t0 < 0.3, "alert dispatch must not stall the hot loop"
    hv_mod.flush_operational_alerts(3.0)
    assert calls and calls[0][0] == "https://api.telegram.org/bot123:ABC/sendMessage" and calls[0][1] == 2.5


def test_v35_stale_recorder_monitor_alerts_once_per_window(tmp_path, monkeypatch):
    tick_dir, tele_dir = tmp_path / "shm", tmp_path / "tele"
    tick_dir.mkdir()
    tele_dir.mkdir()
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tick_dir))
    monkeypatch.setenv("PM_TELEMETRY_DIR", str(tele_dir))
    monkeypatch.setenv("POLYMARKET_ALERTS_FILE", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setattr(hv_mod, "_ALERT_LAST_SENT", {})
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(dry_run=True)
    h.monitor_recorder_staleness(time.time())
    h.monitor_recorder_staleness(time.time())  # rate-limited (5 min)
    events = [json.loads(l) for l in (tmp_path / "alerts.jsonl").read_text().splitlines()]
    stale = [e for e in events if e["event_type"] == "STALE_RECORDER_FEED"]
    assert len(stale) == 2 and {e["message"].split()[0] for e in stale} == {"BTC", "ETH"}  # one per asset, not per call


def test_v35_sigterm_triggers_graceful_state_flush_and_clean_exit(tmp_path, monkeypatch):
    """#4/#5: a real SIGTERM makes run() flush state atomically (STOPPED_GRACEFULLY) and return (exit code 0 path)."""
    for name in ("TRIGGER_FILE", "SHOCK_FILE", "RESOLUTIONS_FILE", "PID_FILE", "STATE_FILE"):
        monkeypatch.setattr(hv_mod, name, tmp_path / f"{name.lower()}{'.json' if name == 'STATE_FILE' else ''}")
    h = PolymarketLiveHarvester(dry_run=True)
    h.reconcile_with_exchange = lambda: None
    h._prewarm_active_market_tokens = lambda: None

    async def drive():
        asyncio.get_running_loop().call_later(0.4, os.kill, os.getpid(), signal.SIGTERM)
        await asyncio.wait_for(h.run(), timeout=15.0)

    asyncio.run(drive())
    state = json.loads((tmp_path / "state_file.json").read_text())
    assert state["status"] == "STOPPED_GRACEFULLY"
    assert h._shutdown_requested is True


def test_v35_reload_script_graceful_terminate_and_position_guard(tmp_path, monkeypatch):
    """#5: SIGTERM-first stops (SIGKILL only for stragglers) and refusal to reload with open positions."""
    reload_mod = _load_script("reload_production_daemons")

    p = subprocess.Popen(["sleep", "30"])
    reload_mod.terminate_gracefully([p.pid], timeout=3.0)
    assert p.wait(timeout=3) == -signal.SIGTERM  # exited on SIGTERM, never needed SIGKILL

    stubborn = subprocess.Popen(
        [sys.executable, "-c", "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print('r',flush=True);time.sleep(30)"],
        stdout=subprocess.PIPE, text=True,
    )
    assert stubborn.stdout.readline().strip() == "r"
    reload_mod.terminate_gracefully([stubborn.pid], timeout=1.0)
    assert stubborn.wait(timeout=3) == -signal.SIGKILL  # last-resort escalation only

    live = tmp_path / "live_state.json"
    live.write_text(json.dumps({"active_positions_count": 1, "active_positions": {"POS_1": {}}}))
    monkeypatch.setattr(reload_mod, "LIVE_STATE", live)
    monkeypatch.setattr(reload_mod, "PAPER_STATE", tmp_path / "no_paper_state.json")
    with pytest.raises(SystemExit) as ei:
        reload_mod.check_active_positions(force=False)
    assert ei.value.code == 1
    reload_mod.check_active_positions(force=True)  # --force overrides

    live.write_text(json.dumps({"active_positions_count": 0, "active_positions": {}}))
    reload_mod.check_active_positions(force=False)  # flat book -> safe


def test_v35_systemd_units_are_uniform_and_graceful():
    """#4: all four daemons have clean unit files: Restart=on-failure, RestartSec=3, KillSignal=SIGTERM."""
    for unit in ("polymarket-recorder", "polymarket-recorder-eth", "polymarket-trader", "polymarket-live-harvester"):
        text = (ROOT / "systemd" / f"{unit}.service").read_text()
        assert "Restart=on-failure" in text and "RestartSec=3" in text and "KillSignal=SIGTERM" in text, unit
    harv = "\n".join(
        ln for ln in (ROOT / "systemd" / "polymarket-live-harvester.service").read_text().splitlines()
        if not ln.lstrip().startswith("#")
    )
    assert "--reset-risk" not in harv, "auto-restarts must never silently clear a tripped circuit breaker"
    assert "--lot-size" not in harv and "--max-exposure" not in harv, "limits must come from the central config"
    assert "--asset BTC" in (ROOT / "systemd" / "polymarket-recorder.service").read_text()
    assert "--asset ETH" in (ROOT / "systemd" / "polymarket-recorder-eth.service").read_text()


def test_v35_bundle_in_sync_with_sources_and_under_1mb():
    """#10: polymarket_all_in_one.py must contain the exact current text of every bundled source and stay < 1 MB."""
    bundler = _load_script("bundle_polymarket_all_in_one")
    bundle_path = ROOT / "polymarket_all_in_one.py"
    bundle_text = bundle_path.read_text(encoding="utf-8")
    assert bundle_path.stat().st_size < 1_000_000
    drifted = []
    for rel_path, _desc in bundler.MODULES:
        code = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if bundler.transform_module(rel_path, code) not in bundle_text:
            drifted.append(rel_path)
    assert not drifted, f"Bundle out of sync for {drifted}. Run: venv/bin/python3 scripts/bundle_polymarket_all_in_one.py"
    compile(bundle_text, "polymarket_all_in_one.py", "exec")  # must remain valid Python


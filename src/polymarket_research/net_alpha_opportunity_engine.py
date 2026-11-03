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

from __future__ import annotations

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
    _empty_ask_with_valid_bid = bool(
        float(tf.get("best_ask") or 0.0) >= 0.995
        and float(tf.get("ask_size_l1") or 0.0) <= 0.0
        and tf.get("age_bid_ms") is not None
    )
    if tf.get("age_ask_ms") is None and not is_special and not _empty_ask_with_valid_bid:
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


def infer_polymarket_tick_size(price_hint: float) -> float:
    px = float(price_hint or 0.0)
    if (0.0 < px < 0.04) or px >= 0.96:
        return 0.001
    return 0.01


def compute_capital_velocity_ev(
    net_edge_per_share: float,
    expected_hold_seconds: float = 300.0,
    *,
    fill_prob: float = 1.0,
    early_recycle_factor: float = 1.0,
    net_cost_per_share: float = 1.0,
) -> float:
    """Capital-Velocity EV (`(net_edge / net_cost) * fill_prob / (expected_hold_seconds * early_recycle_factor)`)."""
    cost = max(0.05, float(net_cost_per_share or 1.0))
    eff_hold = max(10.0, float(expected_hold_seconds or 300.0) * max(0.10, float(early_recycle_factor or 1.0)))
    fp = max(0.01, min(1.0, float(fill_prob if fill_prob is not None else 1.0)))
    return (float(net_edge_per_share or 0.0) / cost) * fp / eff_hold


def compute_smart_maker_bid(
    best_bid: float,
    best_ask: float,
    max_cap_px: Optional[float] = None,
    min_floor_px: float = 0.001,
    obi_l1: float = 0.0,
    tick_size: Optional[float] = None,
    *,
    max_ceiling: Optional[float] = None,
    max_bid_px: Optional[float] = None,
    min_floor: Optional[float] = None,
) -> Tuple[Optional[float], bool]:
    """
    Tick-aware Maker bid placement:
      - Uses 0.001 tick in <0.04 / >=0.96 tail zones, else 0.01.
      - Pennies `best_bid + 1 tick` (`queue_front=True`) when spread >= 2 ticks and within `max_cap_px`.
      - Passively joins `best_bid` (`queue_front=False`) on 1-tick spread unless `obi_l1 < -0.35`.
    """
    def _num_val(v: Any, dflt: float = 0.0) -> float:
        return float(v) if (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)) else dflt

    eff_max = _num_val(
        max_cap_px if max_cap_px is not None else (max_ceiling if max_ceiling is not None else (max_bid_px if max_bid_px is not None else 0.99)),
        0.99,
    )
    eff_min = _num_val(min_floor if min_floor is not None else min_floor_px, 0.001)
    ba = _num_val(best_ask, 0.0)
    bb = _num_val(best_bid, 0.0)
    obi_v = _num_val(obi_l1, 0.0)
    ts_v = _num_val(tick_size, 0.0)
    ref_px = ba if ba > 0.0 else eff_max
    tick = ts_v if ts_v > 0.0 else infer_polymarket_tick_size(ref_px)
    digits = 3 if tick < 0.009 else 2
    max_non_cross = (ba - tick) if ba > tick else eff_max
    cap_raw = min(eff_max, max_non_cross)
    cap = round(math.floor((cap_raw + 1e-9) / tick) * tick, digits)
    if cap < eff_min - 1e-9 or cap <= 0.0:
        return None, False
    if bb > 0.0:
        spread = (ba - bb) if ba > bb else 0.0
        penny = round(bb + tick, digits)
        if spread >= (2.0 * tick - 1e-9) and penny <= cap + 1e-9:
            return min(cap, penny), True
        if bb <= cap + 1e-9:
            if 0.0 < spread <= (tick + 1e-9) and obi_v < -0.35:
                return None, False
            return round(min(cap, bb), digits), False
    return cap, True


def _walk_bid_levels_net(
    bids: Iterable[Dict[str, Any]],
    target_shares: float,
    fee_rate: float = 0.0,
    fee_exp: float = 1.0,
) -> Tuple[bool, float, float, float, float]:
    lvls: List[Tuple[float, float]] = []
    total_depth = 0.0
    for r in bids or ():
        if not isinstance(r, dict):
            continue
        try:
            px = float(r.get("price") or 0.0)
            sz = float(r.get("size") or 0.0)
        except (TypeError, ValueError):
            continue
        if px > 0.0 and sz > 0.0:
            lvls.append((px, sz))
            total_depth += sz
    if not lvls or target_shares <= 0.0 or total_depth + 1e-9 < target_shares:
        return False, 0.0, 0.0, 0.0, total_depth
    lvls.sort(key=lambda x: -x[0])
    rem = float(target_shares)
    gross_usd = 0.0
    net_usd = 0.0
    worst_px = lvls[0][0]
    for px, sz in lvls:
        take = min(rem, sz)
        if take <= 0.0:
            break
        fee_ps = compute_category_taker_fee_per_share(px, fee_rate=fee_rate, fee_exponent=fee_exp)
        gross_usd += take * px
        net_usd += take * max(0.0, px - fee_ps)
        worst_px = px
        rem -= take
        if rem <= 1e-7:
            break
    if rem > 1e-5:
        return False, 0.0, 0.0, 0.0, total_depth
    return True, gross_usd / target_shares, net_usd / target_shares, worst_px, total_depth


def walk_dual_leg_overround_bids(
    bids_a: Iterable[Dict[str, Any]],
    bids_b: Iterable[Dict[str, Any]],
    target_shares: float,
    fee_rate_a: float = 0.0,
    fee_exp_a: float = 1.0,
    fee_rate_b: float = 0.0,
    fee_exp_b: float = 1.0,
    min_depth_mult: float = 1.25,
) -> Dict[str, Any]:
    """Walks L2 bids on both box legs for `target_shares` and returns net proceeds + FOK floor prices."""
    sh = float(target_shares or 0.0)
    ok_a, gross_a, net_a, min_px_a, depth_a = _walk_bid_levels_net(bids_a, sh, fee_rate_a, fee_exp_a)
    ok_b, gross_b, net_b, min_px_b, depth_b = _walk_bid_levels_net(bids_b, sh, fee_rate_b, fee_exp_b)
    depth_ok = ok_a and ok_b and depth_a >= sh * min_depth_mult and depth_b >= sh * min_depth_mult
    return {
        "fillable": bool(depth_ok and min_px_a > 0.0 and min_px_b > 0.0),
        "gross_sum_per_share": round(gross_a + gross_b, 6),
        "net_sum_per_share": round(net_a + net_b, 6),
        "min_px_a": round(min_px_a, 4),
        "min_px_b": round(min_px_b, 4),
        "depth_a": round(depth_a, 4),
        "depth_b": round(depth_b, 4),
    }


# ==============================================================================
# 8. V3.9.5 GUARDED COMPLEMENT MERGE, 15M->5M CORRIDOR & 60MS TOURNAMENT
# ==============================================================================

def evaluate_guarded_complement_merge(
    *,
    rem_shares: float,
    opp_ask: float,
    opp_ask_size: float = 0.0,
    opp_ask_size_l1: Optional[float] = None,
    curr_maker_tp_px: Optional[float] = None,
    fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
    min_net_proceeds_ps: float = 0.9820,
    max_opp_ask: float = 0.015,
    min_marketable_usd: float = 1.00,
) -> Dict[str, Any]:
    """
    Guarded `OPP <= $0.015` synthetic complement-merge evaluator (`hold_98`-safe).
    Enforces all three live execution invariants:
      1. Strict No-Overbuy Loss Guard: if `rem_shares * opp_ask < $1.00` forces buying extra
         unmergeable `OPP` shares to meet Polymarket's `$1.00` marketable minimum, exact net
         proceeds `(rem_shares * $1.00 - req_opp_shares * (opp_ask + fee)) / rem_shares` must
         STILL exceed `min_net_proceeds_ps` (`$0.9820` > `$0.9800` Maker TP). Blocks the 20-share
         `$0.9465/sh` over-buy loss trap!
      2. Sub-Penny Tick Size (`0.001`) below `$0.04` via `infer_polymarket_tick_size`.
      3. Atomic Execution Plan: `1) FAK_BUY_OPP -> 2) CONFIRM_OPP_FILL -> 3) CANCEL_MAKER_TP -> 4) MERGE_CTF`.
    """
    if opp_ask_size_l1 is not None and opp_ask_size <= 0.0:
        opp_ask_size = float(opp_ask_size_l1)
    if curr_maker_tp_px is not None:
        min_net_proceeds_ps = max(float(min_net_proceeds_ps), float(curr_maker_tp_px) + 0.0020)
    sh = float(rem_shares or 0.0)
    ask = float(opp_ask or 0.0)
    if sh < 5.0 or not (0.001 <= ask <= float(max_opp_ask)):
        return {"approved": False, "reason": "OUT_OF_OPP_PRICE_BAND_OR_SUB_LOT"}

    min_sh_for_notional = math.ceil((float(min_marketable_usd) / ask) * 100.0) / 100.0
    req_opp_shares = max(sh, min_sh_for_notional)
    excess_unmerged_shares = max(0.0, round(req_opp_shares - sh, 4))
    if opp_ask_size > 0.0 and float(opp_ask_size) + 1e-6 < req_opp_shares:
        return {"approved": False, "reason": "INSUFFICIENT_OPP_ASK_DEPTH", "req_opp_shares": req_opp_shares}

    fee_ps = compute_category_taker_fee_per_share(ask, fee_rate=fee_rate, fee_exponent=fee_exponent)
    total_opp_cost = req_opp_shares * (ask + fee_ps)
    merged_gross_usd = sh * 1.0
    net_proceeds_usd = merged_gross_usd - total_opp_cost
    net_proceeds_ps = net_proceeds_usd / sh
    tick = infer_polymarket_tick_size(ask)

    if net_proceeds_ps < float(min_net_proceeds_ps):
        return {
            "approved": False,
            "reason": "OVERBUY_DILUTION_BELOW_MAKER_98_HURDLE",
            "net_proceeds_ps": round(net_proceeds_ps, 5),
            "req_opp_shares": round(req_opp_shares, 2),
            "excess_unmerged_shares": excess_unmerged_shares,
        }

    return {
        "approved": True,
        "opp_ask": round(ask, 4),
        "tick_size": f"{tick:.3f}" if tick < 0.009 else f"{tick:.2f}",
        "req_opp_shares": round(req_opp_shares, 2),
        "merge_pairs": round(sh, 2),
        "excess_unmerged_shares": excess_unmerged_shares,
        "total_opp_cost_usd": round(total_opp_cost, 4),
        "net_proceeds_ps": round(net_proceeds_ps, 5),
        "atomic_sequence": ("FAK_BUY_OPP", "CONFIRM_OPP_FILL", "CANCEL_RESTING_MAKER_TP", "MERGE_CTF_POSITIONS"),
    }


def evaluate_d1_15m_to_5m_corridor_conversion(
    pos_15m: Dict[str, Any],
    snap_5m: Optional[Dict[str, Any]],
    *,
    now_ts: Optional[float] = None,
    fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
    max_total_box_cost: float = 0.975,
    min_corridor_bps: float = 1.5,
) -> Dict[str, Any]:
    """
    Evaluates converting a single-leg open `15m` position entering its final `300s` into a
    risk-free Same-Oracle Dominance Corridor (`$1.00` guaranteed floor + `$2.00` corridor jackpot)
    using the overlapping child `5m` contract sharing the exact Chainlink 60s-TWAP settlement timestamp.
    """
    if not isinstance(pos_15m, dict) or not isinstance(snap_5m, dict):
        return {"eligible": False, "reason": "MISSING_5M_SNAPSHOT"}
    side_15 = str(pos_15m.get("target_token") or "").upper()
    if side_15 not in ("UP", "DOWN"):
        return {"eligible": False, "reason": "INVALID_SIDE"}
    rem_sh = float(pos_15m.get("remaining_shares") or 0.0)
    entry_px_15 = float(pos_15m.get("entry_price") or 0.0)
    fee_15_usd = float(pos_15m.get("fee_usd") or 0.0)
    k_15 = float(pos_15m.get("candle_open_spot") or 0.0)
    exp_15 = float(pos_15m.get("candle_expiry_ts") or 0.0)
    t_now = float(now_ts) if now_ts is not None else 0.0
    if t_now > 0.0 and exp_15 > 0.0 and not (15.0 <= (exp_15 - t_now) <= 295.0):
        return {"eligible": False, "reason": "OUTSIDE_FINAL_5M_WINDOW"}
    if rem_sh < 5.0 or entry_px_15 <= 0.0 or k_15 <= 0.0:
        return {"eligible": False, "reason": "INVALID_15M_POSITION"}

    k_5 = float(
        snap_5m.get("authoritative_chainlink_open")
        or snap_5m.get("finalized_open")
        or snap_5m.get("finalized_15m_open")
        or 0.0
    )
    if k_5 <= 0.0:
        return {"eligible": False, "reason": "MISSING_5M_STRIKE"}

    if side_15 == "UP":
        corridor_bps = ((k_5 - k_15) / k_15) * 10000.0
        opp_side_5 = "DOWN"
    else:
        corridor_bps = ((k_15 - k_5) / k_15) * 10000.0
        opp_side_5 = "UP"

    if corridor_bps < float(min_corridor_bps):
        return {"eligible": False, "reason": "NO_DOMINANCE_CORRIDOR", "corridor_bps": round(corridor_bps, 2)}

    bk_5 = snap_5m.get(opp_side_5) or {}
    ask_5 = float(bk_5.get("best_ask") or 1.0)
    ask_sz_5 = float(bk_5.get("ask_size_l1") or 0.0)
    tok_5 = str(bk_5.get("token_id") or "")
    mkt_5 = str(snap_5m.get("market_id") or "")
    if not (0.01 <= ask_5 <= 0.90) or ask_sz_5 < rem_sh * 1.15 or (rem_sh * ask_5) < 1.00 or not tok_5:
        return {"eligible": False, "reason": "INSUFFICIENT_5M_LIQUIDITY_OR_TOKEN"}

    fee_5_ps = compute_category_taker_fee_per_share(ask_5, fee_rate=fee_rate, fee_exponent=fee_exponent)
    cost_15_ps = entry_px_15 + (fee_15_usd / max(rem_sh, 1e-6))
    total_box_cost = cost_15_ps + ask_5 + fee_5_ps
    if total_box_cost > float(max_total_box_cost):
        return {
            "eligible": False,
            "reason": "BOX_COST_EXCEEDS_CEILING",
            "total_box_cost_ps": round(total_box_cost, 4),
            "corridor_bps": round(corridor_bps, 2),
        }

    locked_floor_ps = 1.0 - total_box_cost
    return {
        "eligible": True,
        "market_id_5m": mkt_5,
        "token_id_5m": tok_5,
        "opp_side_5m": opp_side_5,
        "shares": round(rem_sh, 2),
        "ask_5m": round(ask_5, 4),
        "fee_5m_ps": round(fee_5_ps, 5),
        "k_15": k_15,
        "k_5": k_5,
        "corridor_bps": round(corridor_bps, 2),
        "total_box_cost_ps": round(total_box_cost, 4),
        "locked_floor_ps": round(locked_floor_ps, 4),
        "locked_floor_pnl_usd": round(rem_sh * locked_floor_ps, 2),
        "corridor_jackpot_pnl_usd": round(rem_sh * (2.0 - total_box_cost), 2),
    }


def rank_microbatch_shock_tournament(
    shocks: List[Dict[str, Any]],
    active_positions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Ranks simultaneous multi-asset shocks arriving within a `60ms` micro-batch window by
    `EV_net_per_dollar * kelly_multiplier` (+ synthetic corridor completion bonus), preventing
    a lower-conviction altcoin tick from locking out a higher-EV BTC/ETH shock 12ms later.
    """
    if len(shocks) <= 1:
        return list(shocks)

    def _score_shock(s: Dict[str, Any]) -> Tuple[float, float]:
        s_dir = str(s.get("shock_direction") or "BUY").upper()
        side = "UP" if s_dir in ("BUY", "UP") else "DOWN"
        pre = (s.get("pre_shock_features_t0") or {}).get(side) or {}
        ask = float(pre.get("best_ask") or pre.get("vwap_$25") or pre.get("effective_price_$25") or 0.70)
        ask = max(0.05, min(0.95, ask))
        dist_pct = abs(float(s.get("candle_distance_pct") or 0.0))
        tte = max(30.0, float(s.get("seconds_to_expiry") or 300.0))
        asset = str(s.get("asset") or "BTC").upper()
        rec_sig = float(s.get("candle_sigma") or 0.0)
        hz = str(s.get("horizon") or "").lower()
        sig_1h = (
            rec_sig * (2.0 if "15m" in hz else (math.sqrt(12.0) if hz in ("5m", "5min", "300s") or "-5m" in hz else 1.0))
            if rec_sig > 0.0
            else (0.0050 if asset == "BTC" else (0.0068 if asset == "ETH" else 0.0090))
        )
        sig_rem = max(0.00025, sig_1h * math.sqrt(tte / 3600.0))
        ofi = min(1.0, abs(float(s.get("shock_ofi") if s.get("shock_ofi") is not None else 0.85)))
        z_eff = (dist_pct / 100.0) / sig_rem + 0.35 * ofi
        p_win = 0.5 * (1.0 + math.erf(z_eff / math.sqrt(2.0)))
        fee_ps = compute_category_taker_fee_per_share(ask, 0.07, 1.0)
        exp_val = p_win * 0.98 + (1.0 - p_win) * 0.36
        ev_per_dollar = (exp_val - ask - fee_ps) / (ask + fee_ps)
        age_ms = float(pre.get("age_ask_ms") if pre.get("age_ask_ms") is not None else 300.0)
        k_mult = 1.15 if age_ms >= 250.0 else 1.00
        liq_bonus = 0.015 if asset == "BTC" else (0.008 if asset == "ETH" else 0.0)
        score = (ev_per_dollar * k_mult) + liq_bonus
        if active_positions:
            util = compute_capital_efficiency_utility(
                {
                    "asset": asset,
                    "side": side,
                    "expiry_ts": s.get("candle_expiry_ts") or s.get("expiry_ts") or 0.0,
                    "strike": s.get("candle_open_spot") or 0.0,
                    "net_edge": max(0.0, exp_val - ask - fee_ps),
                    "ask_vwap": ask,
                    "p_model": p_win,
                    "tte_sec": tte,
                },
                active_global_positions=active_positions,
            )
            score += float(util.get("corridor_completion_bonus") or 0.0) - float(util.get("corr_penalty") or 0.0)
        return (round(score, 6), z_eff)

    return sorted(shocks, key=_score_shock, reverse=True)

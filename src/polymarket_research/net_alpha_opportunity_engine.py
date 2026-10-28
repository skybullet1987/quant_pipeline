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

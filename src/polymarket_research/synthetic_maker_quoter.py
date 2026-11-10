"""
Stage D Continuous State-Space Implied Synthetic Maker Quoter & Riskless-PAA Shield
(`src/polymarket_research/synthetic_maker_quoter.py`).

Implements:
  1. `compute_synthetic_maker_quote`: Fee-exact (`0%` & `crypto_fees_v2` + `20%` Maker rebate),
     tick-exact (`0.001` / `0.01`) `#1` FIFO Synthetic Maker quote solver across `D1`, `AFF1`,
     `SP3`, `CAL1`, and `NEGRISK` (`NO`-pair & `convertPositions`).
  2. `evaluate_resting_synthetic_quote_tick`: Sub-millisecond WS L2 tick evaluator with
     asymmetric hysteresis:
       - `0 ms` instant retreat (`CANCEL_ADVERSE`) on 1-tick hedge-ask drift, hedge depth cushion
         erosion (`< 2.5x`), anchor OBI sweep toxicity (`< -0.35` or 3:1 ask-compression), spot/perp
         drift (`>= 2.5 bps`), or live sports clock unfreezing without deep cushion.
       - `500 ms` debounced `#1` FIFO advance (`REPEG_FIFO1`) when outbid or when hedge-ask improvement
         opens room to claim sole top-of-book FIFO priority without queue-churn.
  3. `MakerAnchorUnwindBreaker` & `is_maker_anchor_live_permitted`: Stage D Class-A `$0.50`
     cumulative leg-out unwind circuit breaker + `RISKLESS_PAA` governance firewall.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR
import json
import logging
import math
from pathlib import Path
import threading
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger("SyntheticMakerQuoter")


def _sf(val: Any, default: float = 0.0) -> float:
    if val is None or isinstance(val, bool) or val == "":
        return default
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def extract_sorted_book_levels(
    book: Optional[Mapping[str, Any]],
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """Returns `(bids_desc, asks_asc)` as `[(price, size), ...]` filtering invalid/zero levels."""
    if not isinstance(book, Mapping):
        return [], []
    bids: List[Tuple[float, float]] = []
    asks: List[Tuple[float, float]] = []
    for b in book.get("bids") or ():
        px = _sf(b.get("price") if isinstance(b, Mapping) else (b[0] if isinstance(b, (list, tuple)) and b else 0.0))
        sz = _sf(b.get("size") if isinstance(b, Mapping) else (b[1] if isinstance(b, (list, tuple)) and len(b) > 1 else 0.0))
        if 0.0 < px < 1.0 and sz > 0.0:
            bids.append((px, sz))
    for a in book.get("asks") or ():
        px = _sf(a.get("price") if isinstance(a, Mapping) else (a[0] if isinstance(a, (list, tuple)) and a else 0.0))
        sz = _sf(a.get("size") if isinstance(a, Mapping) else (a[1] if isinstance(a, (list, tuple)) and len(a) > 1 else 0.0))
        if 0.0 < px <= 1.0 and sz > 0.0:
            asks.append((px, sz))
    bids.sort(key=lambda r: r[0], reverse=True)
    asks.sort(key=lambda r: r[0])
    return bids, asks


def infer_clob_tick_size(
    price_hint: float,
    levels: Optional[Sequence[Tuple[float, float]]] = None,
    explicit_tick: float = 0.0,
) -> float:
    """Infers exact Polymarket CLOB tick size (`0.001` vs `0.01`)."""
    if 0.0005 <= float(explicit_tick or 0.0) <= 0.0015:
        return 0.001
    if 0.005 <= float(explicit_tick or 0.0) <= 0.015:
        return 0.01
    if levels:
        for px, _ in levels[:6]:
            if abs(round(px * 100.0) - (px * 100.0)) > 1e-4:
                return 0.001
    p = float(price_hint or 0.50)
    if p <= 0.04 + 1e-9 or p >= 0.96 - 1e-9:
        return 0.001
    return 0.01


def floor_to_clob_tick(raw_px: float, tick_size: float = 0.01) -> float:
    """Quantizes `raw_px` strictly DOWNWARD (`ROUND_FLOOR`) to an exact multiple of `tick_size`."""
    if raw_px <= 0.0:
        return 0.0
    tk_dec = Decimal("0.001") if float(tick_size or 0.01) <= 0.0015 else Decimal("0.01")
    px_dec = Decimal(f"{float(raw_px):.8f}") + Decimal("0.00000001")
    q = (px_dec / tk_dec).to_integral_value(rounding=ROUND_FLOOR) * tk_dec
    return float(q)


def compute_taker_fee_haircut(price: float, fee_rate: float, fee_exponent: float = 1.0) -> Tuple[float, float]:
    """
    Returns `(fee_per_share_usd, share_haircut_fraction)` under Polymarket's exact curve:
      `fee_per_share = fee_rate * (p * (1 - p)) ** fee_exponent`
      `net_unit_cost = p / (1 - h)` where `h = fee_per_share / p`.
    """
    p = float(price or 0.0)
    fr = max(0.0, float(fee_rate or 0.0))
    fe = max(0.5, float(fee_exponent or 1.0))
    if fr <= 0.0 or not (0.0 < p < 1.0):
        return 0.0, 0.0
    fee_ps = fr * ((p * (1.0 - p)) ** fe)
    h = min(0.50, max(0.0, fee_ps / max(p, 1e-9)))
    return fee_ps, h


def compute_net_taker_hedge_cost(
    asks: Sequence[Tuple[float, float]],
    target_net_shares: float,
    fee_rate: float = 0.0,
    fee_exponent: float = 1.0,
    cushion_band: float = 0.01,
) -> Dict[str, Any]:
    """
    Walks L2 asks to acquire `target_net_shares` net of Polymarket share-fee deduction,
    and measures total available hedge cushion within `best_ask + cushion_band`.
    """
    if not asks or target_net_shares <= 0.0:
        return {"fillable": False, "avail_band_shares": 0.0, "best_ask": 1.0, "net_unit_cost": 9.9}

    best_ask = float(asks[0][0])
    band = max(0.002 if (best_ask <= 0.04 or best_ask >= 0.96) else 0.01, float(cushion_band))
    avail_band = sum(float(sz) for px, sz in asks if float(px) <= best_ask + band + 1e-9)

    rem_net = float(target_net_shares)
    gross_cost = 0.0
    gross_sh = 0.0
    worst_px = best_ask
    for px, sz in asks:
        p = float(px)
        s = float(sz)
        if p <= 0.0 or p >= 1.0 or s <= 0.0:
            continue
        _, h = compute_taker_fee_haircut(p, fee_rate, fee_exponent)
        net_s_avail = s * (1.0 - h)
        if net_s_avail <= 1e-9:
            continue
        take_net = min(rem_net, net_s_avail)
        take_gross = take_net / (1.0 - h)
        gross_cost += take_gross * p
        gross_sh += take_gross
        worst_px = p
        rem_net -= take_net
        if rem_net <= 1e-6:
            break

    if rem_net > 1e-5:
        return {
            "fillable": False,
            "avail_band_shares": round(avail_band, 4),
            "best_ask": best_ask,
            "net_unit_cost": 9.9,
        }

    net_unit = gross_cost / max(float(target_net_shares), 1e-9)
    return {
        "fillable": True,
        "best_ask": round(best_ask, 4),
        "worst_walk_ask": round(worst_px, 4),
        "gross_shares_needed": round(gross_sh, 4),
        "net_unit_cost": round(net_unit, 6),
        "avail_band_shares": round(avail_band, 4),
    }


def compute_synthetic_maker_quote(
    *,
    family: str,
    leg_a: Mapping[str, Any],
    leg_b: Mapping[str, Any],
    book_a: Optional[Mapping[str, Any]],
    book_b: Optional[Mapping[str, Any]],
    opp_book_a: Optional[Mapping[str, Any]] = None,
    opp_book_b: Optional[Mapping[str, Any]] = None,
    target_shares: float = 12.0,
    max_box_cost_net: float = 0.990,
    safety_margin: float = 0.0,
    min_hedge_depth_mult: float = 4.0,
    min_abs_hedge_shares: float = 18.0,
    min_anchor_obi: float = -0.20,
    max_join_queue_usd: float = 35.0,
    maker_rebate_share: float = 0.20,
    include_rebate_in_cap: bool = False,
    is_sports_live_clock_running: bool = False,
    live_clock_min_depth_mult: float = 5.5,
) -> Dict[str, Any]:
    """
    Computes the optimal `#1` FIFO passive `post_only=True` Synthetic Maker quote across
    `(Leg A = Maker, Leg B = Taker Hedge)` and `(Leg B = Maker, Leg A = Taker Hedge)`.
    """
    fam = str(family or "GENERIC").strip().upper()
    sh_req = max(5.0, float(target_shares or 12.0))

    bids_a, asks_a = extract_sorted_book_levels(book_a)
    bids_b, asks_b = extract_sorted_book_levels(book_b)
    if not bids_a or not asks_a or not bids_b or not asks_b:
        return {"eligible": False, "reason": "EMPTY_L2_BOOK"}

    # Complement anti-box sanity check (blocks synthetic stale-mirror traps)
    if opp_book_a is not None and opp_book_b is not None:
        opp_bids_a, _ = extract_sorted_book_levels(opp_book_a)
        opp_bids_b, _ = extract_sorted_book_levels(opp_book_b)
        ob_a = opp_bids_a[0][0] if opp_bids_a else 0.0
        ob_b = opp_bids_b[0][0] if opp_bids_b else 0.0
        if (
            (ob_a > 0.0 and asks_a[0][0] + ob_a > 1.015)
            or (ob_b > 0.0 and asks_b[0][0] + ob_b > 1.015)
            or (ob_a + ob_b > 1.160)
        ):
            return {"eligible": False, "reason": "ANTI_BOX_COMPLEMENT_VETO"}

    eff_depth_mult = float(min_hedge_depth_mult)
    if is_sports_live_clock_running and fam in {"AFF1", "SP3", "SPORTS_CORRIDOR"}:
        if live_clock_min_depth_mult <= 0.0:
            return {"eligible": False, "reason": "SPORTS_LIVE_CLOCK_UNFROZEN"}
        eff_depth_mult = max(eff_depth_mult, float(live_clock_min_depth_mult))

    candidates: List[Tuple[Tuple[int, float, float], Dict[str, Any]]] = []
    reject_reasons: List[str] = []

    for anchor_is_a in (True, False):
        anc_meta = leg_a if anchor_is_a else leg_b
        hdg_meta = leg_b if anchor_is_a else leg_a
        bids_anc, asks_anc = (bids_a, asks_a) if anchor_is_a else (bids_b, asks_b)
        bids_hdg, asks_hdg = (bids_b, asks_b) if anchor_is_a else (bids_a, asks_a)

        best_bid_anc, bid_sz_anc = bids_anc[0]
        best_ask_anc, ask_sz_anc = asks_anc[0]
        best_bid_hdg = bids_hdg[0][0]
        best_ask_hdg = asks_hdg[0][0]

        if not (0.015 <= best_ask_anc <= 0.999) or not (0.001 <= best_ask_hdg <= 0.988):
            reject_reasons.append("PRICE_OUT_OF_RANGE")
            continue

        # Reject wide/illiquid hedge books (> 5c spread outside tail zones)
        if best_bid_hdg > 0.0 and 0.04 < best_ask_hdg < 0.96 and (best_ask_hdg - best_bid_hdg) > 0.05 + 1e-9:
            reject_reasons.append("HEDGE_SPREAD_TOO_WIDE")
            continue

        obi_anc = (bid_sz_anc - ask_sz_anc) / max(1e-9, bid_sz_anc + ask_sz_anc)
        if obi_anc < float(min_anchor_obi):
            reject_reasons.append("ANCHOR_OBI_TOXIC")
            continue

        fr_hdg = _sf(hdg_meta.get("fee_rate"), 0.0)
        fe_hdg = _sf(hdg_meta.get("fee_exponent"), 1.0)
        fr_anc = _sf(anc_meta.get("fee_rate"), 0.0)
        fe_anc = _sf(anc_meta.get("fee_exponent"), 1.0)

        hdg_walk = compute_net_taker_hedge_cost(asks_hdg, sh_req, fee_rate=fr_hdg, fee_exponent=fe_hdg)
        req_depth = max(float(min_abs_hedge_shares), eff_depth_mult * sh_req)
        if not hdg_walk["fillable"] or float(hdg_walk["avail_band_shares"]) < req_depth - 1e-6:
            reject_reasons.append("INSUFFICIENT_HEDGE_DEPTH_CUSHION")
            continue

        net_hdg_cost = float(hdg_walk["net_unit_cost"])
        tk_bid = infer_clob_tick_size(best_bid_anc, bids_anc, _sf(anc_meta.get("tick_size"), 0.0))
        tk_ask = infer_clob_tick_size(best_ask_anc, asks_anc, _sf(anc_meta.get("tick_size"), 0.0))

        # Estimate Maker rebate on crypto fee-bearing anchor leg (20% of taker equivalent fee)
        est_reb_ref, _ = compute_taker_fee_haircut(best_bid_anc, fr_anc, fe_anc)
        reb_credit = (float(maker_rebate_share) * est_reb_ref) if (include_rebate_in_cap and fr_anc > 0.0) else 0.0

        raw_max_bid = float(max_box_cost_net) + reb_credit - net_hdg_cost - max(0.0, float(safety_margin))
        max_maker_bid = floor_to_clob_tick(raw_max_bid, tk_bid)
        max_non_crossing = floor_to_clob_tick(best_ask_anc - tk_ask, tk_ask)
        step_ahead_bid = floor_to_clob_tick(best_bid_anc + tk_bid + 1e-7, tk_bid)

        fifo_rank1 = False
        queue_ahead_usd = 0.0
        if step_ahead_bid <= min(max_non_crossing, max_maker_bid) + 1e-9 and step_ahead_bid > best_bid_anc + 1e-9:
            cand_bid = min(step_ahead_bid, max_non_crossing, max_maker_bid)
            fifo_rank1 = True
        elif best_bid_anc <= min(max_non_crossing, max_maker_bid) + 1e-9:
            q_usd = sum(px * sz for px, sz in bids_anc if abs(px - best_bid_anc) < 1e-6)
            if q_usd > float(max_join_queue_usd) + 1e-6 or obi_anc < -0.10:
                reject_reasons.append("QUEUE_TOO_DEEP_TO_JOIN")
                continue
            cand_bid = floor_to_clob_tick(min(best_bid_anc, max_maker_bid), tk_bid)
            if cand_bid < best_bid_anc - 1e-9:
                reject_reasons.append("BELOW_TOP_BID")
                continue
            fifo_rank1 = False
            queue_ahead_usd = round(q_usd, 2)
        else:
            reject_reasons.append("IMPLIED_BID_BELOW_BOOK")
            continue

        if cand_bid <= 0.010 or cand_bid >= best_ask_anc - 1e-9:
            reject_reasons.append("INVALID_CANDIDATE_BID")
            continue

        taker_eq_fee_anc, _ = compute_taker_fee_haircut(cand_bid, fr_anc, fe_anc)
        rebate_ps = round(float(maker_rebate_share) * taker_eq_fee_anc, 6) if fr_anc > 0.0 else 0.0
        pair_cost_net = round(cand_bid + net_hdg_cost, 4)
        pair_cost_after_rebate = round(pair_cost_net - rebate_ps, 4)

        if not (0.850 <= (pair_cost_after_rebate if include_rebate_in_cap else pair_cost_net) <= float(max_box_cost_net) + 1e-6):
            reject_reasons.append("PAIR_COST_OUT_OF_BAND")
            continue

        hdg_depth_ratio = round(float(hdg_walk["avail_band_shares"]) / sh_req, 2)
        quote_doc = {
            "eligible": True,
            "family": fam,
            "anchor_is_a": anchor_is_a,
            "anchor_token_id": str(anc_meta.get("token_id") or ""),
            "hedge_token_id": str(hdg_meta.get("token_id") or ""),
            "anchor_bid_px": round(cand_bid, 4),
            "anchor_tick_size": tk_bid,
            "best_bid_anchor": round(best_bid_anc, 4),
            "best_ask_anchor": round(best_ask_anc, 4),
            "hedge_best_ask": round(best_ask_hdg, 4),
            "hedge_walk_ask": round(float(hdg_walk["worst_walk_ask"]), 4),
            "hedge_net_unit_cost": round(net_hdg_cost, 4),
            "hedge_avail_shares": round(float(hdg_walk["avail_band_shares"]), 2),
            "hedge_depth_ratio": hdg_depth_ratio,
            "pair_cost_net": pair_cost_net,
            "pair_cost_after_rebate": pair_cost_after_rebate,
            "maker_rebate_per_share": rebate_ps,
            "fifo_rank1": fifo_rank1,
            "queue_ahead_usd": queue_ahead_usd,
            "obi_anchor": round(obi_anc, 4),
            "target_shares": sh_req,
        }
        # Prefer #1 FIFO first, then lowest net pair cost, then deepest hedge ratio
        sort_key = (0 if fifo_rank1 else 1, pair_cost_after_rebate, -hdg_depth_ratio)
        candidates.append((sort_key, quote_doc))

    if not candidates:
        return {"eligible": False, "reason": reject_reasons[0] if reject_reasons else "NO_VIABLE_QUOTE"}

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def evaluate_resting_synthetic_quote_tick(
    *,
    posted_bid_px: float,
    posted_shares: float,
    anchor_book: Optional[Mapping[str, Any]],
    hedge_book: Optional[Mapping[str, Any]],
    hedge_fee_rate: float = 0.0,
    hedge_fee_exponent: float = 1.0,
    max_entry_box_cost_net: float = 0.990,
    max_keep_box_cost_net: float = 0.992,
    min_keep_depth_mult: float = 2.5,
    min_keep_obi: float = -0.35,
    rem_tte_sec: float = 300.0,
    min_rem_tte_sec: float = 45.0,
    adverse_spot_bps: float = 0.0,
    max_adverse_spot_bps: float = 2.5,
    perp_precancel_triggered: bool = False,
    is_sports_live_clock_running: bool = False,
    live_clock_min_depth_mult: float = 5.0,
    advance_since_mono: Optional[float] = None,
    now_mono: Optional[float] = None,
    advance_debounce_sec: float = 0.50,
    repeg_count: int = 0,
    max_repegs: int = 4,
) -> Dict[str, Any]:
    """
    Sub-millisecond evaluation of a resting Synthetic Maker order against live WS L2 books:
      - `CANCEL_ADVERSE` (`0 ms` debounce): Immediate retreat on any toxicity, depth loss, or cost breach.
      - `REPEG_FIFO1` (`advance_debounce_sec` debounce): Sticky `#1` FIFO step-up when outbid or hedge improves.
      - `HOLD`: Preserve `#1` FIFO time priority.
    """
    now_m = float(now_mono if now_mono is not None else time.monotonic())
    sh = max(5.0, float(posted_shares or 5.0))
    bid_px = float(posted_bid_px)

    if rem_tte_sec <= float(min_rem_tte_sec):
        return {"action": "CANCEL_ADVERSE", "reason": "TTE_FLOOR_REACHED", "advance_since_mono": None}
    if perp_precancel_triggered:
        return {"action": "CANCEL_ADVERSE", "reason": "PERP_LEADLAG_PRECANCEL", "advance_since_mono": None}
    if float(adverse_spot_bps or 0.0) >= float(max_adverse_spot_bps):
        return {"action": "CANCEL_ADVERSE", "reason": f"SPOT_ADVERSE_{adverse_spot_bps:.2f}BPS", "advance_since_mono": None}

    bids_anc, asks_anc = extract_sorted_book_levels(anchor_book)
    _, asks_hdg = extract_sorted_book_levels(hedge_book)
    if not asks_hdg:
        return {"action": "CANCEL_ADVERSE", "reason": "HEDGE_BOOK_EMPTY", "advance_since_mono": None}

    hdg_walk = compute_net_taker_hedge_cost(asks_hdg, sh, fee_rate=hedge_fee_rate, fee_exponent=hedge_fee_exponent)
    req_keep_mult = (
        max(float(min_keep_depth_mult), float(live_clock_min_depth_mult))
        if is_sports_live_clock_running
        else float(min_keep_depth_mult)
    )
    if is_sports_live_clock_running and live_clock_min_depth_mult <= 0.0:
        return {"action": "CANCEL_ADVERSE", "reason": "SPORTS_CLOCK_UNFROZEN", "advance_since_mono": None}
    if not hdg_walk["fillable"] or float(hdg_walk["avail_band_shares"]) < max(12.0, req_keep_mult * sh) - 1e-6:
        return {"action": "CANCEL_ADVERSE", "reason": "HEDGE_DEPTH_BELOW_FLOOR", "advance_since_mono": None}

    cur_pair_cost = round(bid_px + float(hdg_walk["net_unit_cost"]), 4)
    if cur_pair_cost > float(max_keep_box_cost_net) + 1e-6:
        return {"action": "CANCEL_ADVERSE", "reason": f"PAIR_COST_DRIFT:{cur_pair_cost:.4f}", "advance_since_mono": None}

    if bids_anc and asks_anc:
        best_bid_anc, bid_sz_anc = bids_anc[0]
        best_ask_anc, ask_sz_anc = asks_anc[0]
        tk_anc = infer_clob_tick_size(bid_px, bids_anc)
        obi_anc = (bid_sz_anc - ask_sz_anc) / max(1e-9, bid_sz_anc + ask_sz_anc)
        if obi_anc < float(min_keep_obi):
            return {"action": "CANCEL_ADVERSE", "reason": f"ANCHOR_OBI_SWEEP:{obi_anc:.2f}", "advance_since_mono": None}
        # Ask-compression sweep shield: ask collapsed right onto our bid + 1 tick with >= 3x size
        if best_ask_anc <= bid_px + tk_anc + 1e-6 and ask_sz_anc >= 3.0 * max(1.0, bid_sz_anc):
            return {"action": "CANCEL_ADVERSE", "reason": "ASK_COMPRESSION_SWEEP_IMMINENT", "advance_since_mono": None}
        if best_bid_anc > 0.0 and best_bid_anc < bid_px - (2.0 * tk_anc) - 1e-6:
            return {"action": "CANCEL_ADVERSE", "reason": "ANCHOR_BID_SUPPORT_PULLED", "advance_since_mono": None}

        # Check sticky #1 FIFO step-up opportunity (outbid OR >= 2-tick hedge improvement)
        if int(repeg_count) < int(max_repegs) and best_ask_anc > best_bid_anc + tk_anc - 1e-6:
            max_new_bid = floor_to_clob_tick(float(max_entry_box_cost_net) - float(hdg_walk["net_unit_cost"]), tk_anc)
            max_non_cross = floor_to_clob_tick(best_ask_anc - tk_anc, tk_anc)
            is_outbid = best_bid_anc > bid_px + 1e-6
            hedge_improved_2t = max_new_bid >= bid_px + (2.0 * tk_anc) - 1e-6 and bid_px < best_bid_anc + 1e-6
            if is_outbid or hedge_improved_2t:
                step_px = floor_to_clob_tick(best_bid_anc + tk_anc + 1e-7, tk_anc)
                target_px = min(step_px, max_non_cross, max_new_bid)
                if target_px > bid_px + 1e-6 and target_px >= best_bid_anc - 1e-6 and target_px < best_ask_anc - 1e-6:
                    since_m = float(advance_since_mono) if advance_since_mono is not None else now_m
                    if (now_m - since_m) >= float(advance_debounce_sec) - 1e-6:
                        return {
                            "action": "REPEG_FIFO1",
                            "reason": "OUTBID_STEP_FIFO1" if is_outbid else "HEDGE_IMPROVED_STEP_FIFO1",
                            "repeg_bid_px": round(target_px, 4),
                            "pair_cost_net": round(target_px + float(hdg_walk["net_unit_cost"]), 4),
                            "advance_since_mono": None,
                        }
                    return {
                        "action": "HOLD",
                        "reason": "DEBOUNCING_ADVANCE",
                        "pair_cost_net": cur_pair_cost,
                        "advance_since_mono": since_m,
                    }

    return {
        "action": "HOLD",
        "reason": "FIFO_VALID",
        "pair_cost_net": cur_pair_cost,
        "hedge_avail_shares": round(float(hdg_walk["avail_band_shares"]), 2),
        "advance_since_mono": None,
    }


class MakerAnchorUnwindBreaker:
    """
    Stage D Class-A Micro-Canary Unwind-Bleed Circuit Breaker (`max_unwind_loss_usd = $0.50`).
    Tracks realized leg-out unwind P&L per sleeve and fail-closes any sleeve whose net unwind
    bleed reaches `-max_unwind_loss_usd`.
    """

    def __init__(self, max_unwind_loss_usd: float = 0.50, state_path: Optional[Path] = None) -> None:
        self.max_unwind_loss_usd = max(0.05, float(max_unwind_loss_usd))
        self.state_path = Path(state_path) if state_path is not None else None
        self._lock = threading.Lock()
        self._by_sleeve: Dict[str, Dict[str, Any]] = {}
        if self.state_path is not None and self.state_path.exists():
            try:
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(raw.get("by_sleeve"), dict):
                    self._by_sleeve = dict(raw["by_sleeve"])
            except Exception:
                pass

    def _persist_locked(self) -> None:
        if self.state_path is None:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(
                    {
                        "updated_at_ts": round(time.time(), 3),
                        "max_unwind_loss_usd": self.max_unwind_loss_usd,
                        "by_sleeve": self._by_sleeve,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            tmp.replace(self.state_path)
        except Exception as exc:
            logger.debug("MakerAnchorUnwindBreaker persist skipped: %s", exc)

    def record_unwind_pnl(self, sleeve: str, net_pnl_usd: float, max_loss_override: Optional[float] = None) -> Dict[str, Any]:
        sl = str(sleeve or "D1_MAKER_ANCHOR_BOX").strip().upper()
        cap = max(0.05, float(max_loss_override if max_loss_override is not None else self.max_unwind_loss_usd))
        pnl = _sf(net_pnl_usd, 0.0)
        with self._lock:
            rec = dict(self._by_sleeve.get(sl) or {"unwind_count": 0, "net_unwind_pnl_usd": 0.0, "halted": False})
            rec["unwind_count"] = int(rec.get("unwind_count", 0)) + 1
            rec["net_unwind_pnl_usd"] = round(float(rec.get("net_unwind_pnl_usd", 0.0)) + pnl, 4)
            rec["last_ts"] = round(time.time(), 3)
            if float(rec["net_unwind_pnl_usd"]) <= -cap + 1e-9:
                rec["halted"] = True
                rec["halt_reason"] = f"UNWIND_BLEED_BREAKER:{rec['net_unwind_pnl_usd']:+.4f}<=-{cap:.2f}"
            self._by_sleeve[sl] = rec
            self._persist_locked()
            return dict(rec)

    def is_halted(self, sleeve: str, max_loss_override: Optional[float] = None) -> Tuple[bool, str]:
        sl = str(sleeve or "D1_MAKER_ANCHOR_BOX").strip().upper()
        cap = max(0.05, float(max_loss_override if max_loss_override is not None else self.max_unwind_loss_usd))
        with self._lock:
            rec = self._by_sleeve.get(sl) or {}
            net_u = float(rec.get("net_unwind_pnl_usd", 0.0) or 0.0)
            if bool(rec.get("halted")) or net_u <= -cap + 1e-9:
                return True, str(rec.get("halt_reason") or f"UNWIND_BLEED_BREAKER:{net_u:+.4f}<=-{cap:.2f}")
            return False, ""


def is_maker_anchor_live_permitted(
    sleeve_source: str,
    riskless_boxes_cfg: Optional[Mapping[str, Any]],
    *,
    unwind_breaker: Optional[MakerAnchorUnwindBreaker] = None,
) -> Tuple[bool, str]:
    """
    Enforces `RISKLESS_PAA` live governance on 2-leg Maker-Anchor execution:
      1. Blocks any sleeve in `paused_riskless_sleeves` (`SP3`, `SOC1`, `SOC2`, etc.).
      2. Enforces `enable_d1_rebate_maker_canary` / `enable_two_leg_maker_anchor_boxes`.
      3. Enforces Stage D `$0.50` cumulative unwind-bleed circuit breaker.
    """
    sl = str(sleeve_source or "D1_MAKER_ANCHOR_BOX").strip().upper()
    rb = riskless_boxes_cfg if isinstance(riskless_boxes_cfg, Mapping) else {}
    paused: Iterable[Any] = rb.get("paused_riskless_sleeves") or ()
    paused_set = {str(x).strip().upper() for x in paused if x}
    if sl in paused_set:
        return False, f"PAUSED_RISKLESS_SLEEVE:{sl}"

    is_rebate_mg = sl == "D1_REBATE_MACHINE_GUN"
    enabled = bool(rb.get("enable_d1_rebate_maker_canary", False)) if is_rebate_mg else bool(rb.get("enable_two_leg_maker_anchor_boxes", False))
    if not enabled:
        return False, "MAKER_ANCHOR_DISABLED_BY_RISKLESS_PAA"

    if unwind_breaker is not None:
        cap = _sf(rb.get("synthetic_maker_unwind_breaker_usd"), 0.50)
        halted, h_reason = unwind_breaker.is_halted(sl, max_loss_override=cap if cap > 0.0 else None)
        if halted:
            return False, h_reason
    return True, "OK"

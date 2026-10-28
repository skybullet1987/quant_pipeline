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

from __future__ import annotations

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

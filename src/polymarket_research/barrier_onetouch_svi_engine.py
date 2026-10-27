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

from __future__ import annotations

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

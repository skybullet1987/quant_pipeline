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

from __future__ import annotations

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


def student_t_df4_cdf(z: float) -> float:
    """Exact analytical closed-form CDF of standard Student-t (nu = 4, Var = 2)."""
    if not math.isfinite(z):
        return 0.5
    z2 = z * z
    s = math.sqrt(4.0 + z2)
    val = 0.5 + (z / (2.0 * s)) * (1.0 + (2.0 / (4.0 + z2)))
    return max(0.0, min(1.0, val))


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


def compute_unit_variance_student_t_cdf(z: float, df: float = 4.0) -> float:
    """
    Unit-variance Student-t CDF (`Var(X) = 1.0`) for `X = T * sqrt((df - 2) / df)`, so
    `P(X <= z) = F_{t_df}(z * sqrt(df / (df - 2)))`.
    When `df <= 0` or `inf`, returns standard Gaussian `Phi(z)`.
    Resolves the unstandardized `Var(t_4) = 2` pricing paradox so tail kurtosis `df` is cleanly
    decoupled from post-shock volatility inflation (`jump_vol_mult`).
    """
    if not math.isfinite(z):
        return 0.5
    if df <= 0.0 or not math.isfinite(df) or df >= 120.0:
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    df_eff = max(2.05, float(df))
    t_std = z * math.sqrt(df_eff / (df_eff - 2.0))
    if abs(df_eff - 4.0) < 1e-6:
        return student_t_df4_cdf(t_std)
    if abs(df_eff - 5.0) < 1e-6:
        return student_t_df5_cdf(t_std)
    # Peizer-Pratt / Hill normal-approximation transform for general df > 2 (error < 1e-4 for df >= 3)
    a = df_eff - 0.5
    b = 48.0 * a * a
    z_norm = math.copysign(math.sqrt(a * math.log1p((t_std * t_std) / df_eff)), t_std)
    z_corr = z_norm + (z_norm ** 3 + 3.0 * z_norm) / b
    return max(0.0, min(1.0, 0.5 * (1.0 + math.erf(z_corr / math.sqrt(2.0)))))


def compute_kemna_vorst_twap_sigma_rem(
    sigma_1h: float,
    tte_sec: float,
    window_sec: float = 60.0,
) -> float:
    """
    Exact C^1-continuous remaining volatility of a `window_sec` (60s) arithmetic TWAP settlement price:
      - `tau >= W`: `sigma_1s * sqrt(tau - 2W/3)`  (`tau - 40` for `W = 60s`)
      - `0 < tau < W`: `sigma_1s * sqrt(tau^3 / (3 * W^2))`  (`tau^3 / 10800` for `W = 60s`)
    Both value and first derivative match continuously at `tau = W`.
    """
    sig_h = max(1e-6, float(sigma_1h))
    w = max(1.0, float(window_sec))
    tau = max(0.25, float(tte_sec))
    sigma_1s = sig_h / 60.0
    if tau >= w:
        eff_var_s = max(0.1, tau - (2.0 * w / 3.0))
    else:
        eff_var_s = (tau * tau * tau) / (3.0 * w * w)
    return sigma_1s * math.sqrt(eff_var_s)


def should_suppress_final60s_twap_salvage(
    *,
    side: str,
    strike_open: float,
    current_spot: float,
    twap_locked_mean: Optional[float],
    tte_sec: float,
    sigma_1h: float,
    twap_locked_weight: Optional[float] = None,
    z_lock_floor: float = 1.25,
    window_sec: float = 60.0,
) -> Tuple[bool, float]:
    """
    Prevents false `pre_expiry_otm_salvage` market dumps during the final 60s of a Chainlink TWAP
    15m/5m candle when a transient 1s spot wick crosses `strike_open` even though `(60 - tau)/60`
    of the settlement TWAP is already banked safely ITM (`z_twap >= z_lock_floor`).
    """
    w = max(1.0, float(window_sec))
    tau = float(tte_sec)
    if (
        not (0.0 < tau < w)
        or strike_open <= 0.0
        or current_spot <= 0.0
        or twap_locked_mean is None
        or float(twap_locked_mean) <= 0.0
    ):
        return False, 0.0
    raw_w = max(0.0, min(1.0, (w - tau) / w))
    w_locked = max(0.0, min(raw_w, float(twap_locked_weight))) if twap_locked_weight is not None else raw_w
    if w_locked < 0.15:
        return False, 0.0
    proj_twap = w_locked * float(twap_locked_mean) + (1.0 - w_locked) * float(current_spot)
    sign = 1.0 if str(side).upper() in ("UP", "BUY", "YES") else -1.0
    cush_twap = sign * (proj_twap - float(strike_open)) / float(strike_open)
    if cush_twap <= 0.0:
        return False, round(cush_twap / 1e-4, 4)
    sig_rem = max(0.00005, compute_kemna_vorst_twap_sigma_rem(sigma_1h, tau, window_sec=w))
    # Add 2.5 bps Chainlink-vs-proxy basis floor inside final 60s so proxy noise cannot overstate lock
    sig_tot = math.hypot(sig_rem, 0.00025)
    z_twap = round(cush_twap / sig_tot, 4)
    return (z_twap >= float(z_lock_floor)), z_twap


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

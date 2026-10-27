#!/usr/bin/env python3
"""
S9: Deribit SVI Implied Volatility Surface & Breeden-Litzenberger Digital Probability Engine
============================================================================================
Provides real-time, non-blocking options-implied volatility (sigma_1h) and skew-aware
Breeden-Litzenberger risk-neutral digital probabilities P(S_T > K) = -e^(rT) * dC/dK
for Polymarket sub-hourly (15m/1h) and daily/weekly strike ladder contracts (EXP-316).
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

logger = logging.getLogger("DeribitSVISurface")

DERIBIT_PUBLIC_URL = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"

DEFAULT_SIGMA_1H = {
    "BTC": 0.0050,
    "ETH": 0.0068,
    "SOL": 0.0095,
    "XRP": 0.0100,
}

ASSET_VOL_MULT_VS_BTC = {
    "BTC": 1.00,
    "ETH": 1.28,
    "SOL": 1.75,
    "XRP": 1.85,
}


def _tte_horizon_bucket(target_tte_sec: Optional[float]) -> str:
    """Buckets target TTE so sub-hourly, daily, weekly, and monthly contracts calibrate to matching Deribit expiries."""
    if target_tte_sec is None or target_tte_sec <= 43200.0:
        return "0DTE"
    if target_tte_sec <= 216000.0:  # <= 2.5 days
        return "DAILY"
    if target_tte_sec <= 950400.0:  # <= 11 days
        return "WEEKLY"
    return "MONTHLY"


@dataclass
class SVIParams:
    a: float
    b: float
    rho: float
    m: float
    sigma: float
    t_years: float
    forward_price: float
    calibrated_at: float
    index_price: float = 0.0

    def implied_forward_drift_rate(self) -> float:
        """Extracts annualized futures/forward carry drift `r_impl = ln(F_T / I_0) / T` (clamped to [-0.30, +0.40])."""
        if self.index_price <= 0.0 or self.forward_price <= 0.0 or self.t_years <= 1e-6:
            return 0.0
        raw_r = math.log(self.forward_price / self.index_price) / max(1e-4, self.t_years)
        return max(-0.30, min(0.40, raw_r))

    def total_variance(self, k: float) -> float:
        val = self.a + self.b * (self.rho * (k - self.m) + math.sqrt((k - self.m) ** 2 + self.sigma ** 2))
        return max(1e-8, val)

    def implied_vol(self, k: float, t_override: Optional[float] = None) -> float:
        t_eff = max(1e-6, t_override if t_override is not None else self.t_years)
        if t_override is not None and self.t_years > 1e-6:
            # Square-root standardized-moneyness scaling (Gatheral power-law skew decay ~ 1/sqrt(T)):
            # prevents steep 0DTE raw-k smile slopes from inflating multi-day digital probabilities.
            t_ratio = t_eff / self.t_years
            k_scale = max(0.25, min(2.0, 1.0 / math.sqrt(max(0.05, t_ratio))))
            w_unit = self.total_variance(k * k_scale) / self.t_years
            return max(0.10, min(3.00, math.sqrt(max(1e-8, w_unit))))
        w = self.total_variance(k)
        return max(0.10, min(3.00, math.sqrt(w / t_eff)))


def scale_svi_sticky_delta(base_svi: SVIParams, vol_mult: float, forward_price: float) -> SVIParams:
    """
    Exact sticky-delta SVI transformation for proxy assets (SOL, XRP) without native liquid Deribit chains:
      sigma_alt(k) = M * sigma_base(k / M)
      => w_alt(k) = (M^2 * a) + (M * b) * [rho * (k - M*m) + sqrt((k - M*m)^2 + (M*sigma)^2)]
    Preserves standardized skew d(sigma)/dz and butterfly no-arbitrage.
    """
    m_val = max(0.5, float(vol_mult))
    return SVIParams(
        a=base_svi.a * (m_val ** 2),
        b=base_svi.b * m_val,
        rho=base_svi.rho,
        m=base_svi.m * m_val,
        sigma=base_svi.sigma * m_val,
        t_years=base_svi.t_years,
        forward_price=forward_price,
        calibrated_at=base_svi.calibrated_at,
    )


def black_scholes_call(F: float, K: float, T: float, sigma: float, r: float = 0.0) -> float:
    if T <= 0.0 or sigma <= 0.0 or K <= 0.0 or F <= 0.0:
        return max(0.0, F - K) * math.exp(-r * max(0.0, T))
    sqrt_t = math.sqrt(T)
    vol_sqrt_t = sigma * sqrt_t
    d1 = (math.log(F / K) + 0.5 * (sigma ** 2) * T) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    return math.exp(-r * T) * (F * float(norm.cdf(d1)) - K * float(norm.cdf(d2)))


def compute_breeden_litzenberger_digital(
    F: float,
    K: float,
    T_years: float,
    svi: SVIParams,
    r: float = 0.0,
) -> float:
    """
    Extracts risk-neutral digital probability P(S_T > K) = -e^(rT) * dC/dK
    accounting for the SVI volatility smile slope d(sigma)/dK, with Gatheral
    butterfly-arbitrage / density monotonicity bounds around Black-Scholes N(d2).
    """
    if F <= 0.0 or K <= 0.0:
        return 0.5
    T_eff = max(1e-6, T_years)
    dK = max(1e-5, K * 0.001)
    k_mid = math.log(K / F)
    k_up = math.log((K + dK) / F)
    k_dn = math.log(max(1e-8, K - dK) / F)
    sigma_mid = svi.implied_vol(k_mid, t_override=T_eff)
    sigma_up = svi.implied_vol(k_up, t_override=T_eff)
    sigma_dn = svi.implied_vol(k_dn, t_override=T_eff)
    c_up = black_scholes_call(F, K + dK, T_eff, sigma_up, r)
    c_dn = black_scholes_call(F, max(1e-8, K - dK), T_eff, sigma_dn, r)
    dC_dK = (c_up - c_dn) / (2.0 * dK)
    p_rnd = -math.exp(r * T_eff) * dC_dK

    # Anchor check against local N(d2) so noisy OTM wing quotes never create >8c phantom skew arbitrage
    vol_sqrt_t = max(1e-6, sigma_mid * math.sqrt(T_eff))
    d2_mid = (math.log(F / K) + (r - 0.5 * (sigma_mid ** 2)) * T_eff) / vol_sqrt_t
    p_bs_d2 = float(norm.cdf(d2_mid))
    p_bounded = max(p_bs_d2 - 0.08, min(p_bs_d2 + 0.08, float(p_rnd)))
    return max(0.0001, min(0.9999, p_bounded))


def fit_svi_slice(
    log_moneyness: List[float],
    mark_ivs: List[float],
    t_years: float,
    forward_price: float,
) -> SVIParams:
    """Fits Gatheral SVI parameters (a, b, rho, m, sigma) with Roger Lee / butterfly no-arbitrage bounds."""
    t_eff = max(1e-5, float(t_years))
    if len(log_moneyness) < 4:
        atm_iv = float(np.median(mark_ivs)) if mark_ivs else 0.55
        w_atm = (atm_iv ** 2) * t_eff
        return SVIParams(
            a=w_atm * 0.85,
            b=w_atm * 0.30,
            rho=-0.10,
            m=0.0,
            sigma=0.05,
            t_years=t_eff,
            forward_price=forward_price,
            calibrated_at=time.time(),
        )

    k_arr = np.array(log_moneyness, dtype=float)
    w_obs = (np.array(mark_ivs, dtype=float) ** 2) * t_eff
    order = np.argsort(k_arr)
    w_atm_est = max(1e-7, float(np.interp(0.0, k_arr[order], w_obs[order])))
    # Gatheral no-butterfly-arbitrage wing bound scaled to slice tenor (prevents runaway 0DTE b/T slope)
    max_b_no_arb = min(0.50, max(1e-4, 3.5 * math.sqrt(w_atm_est * t_eff)))

    def loss(params: np.ndarray) -> float:
        a, b, rho, m, sig = params
        w_model = a + b * (rho * (k_arr - m) + np.sqrt((k_arr - m) ** 2 + sig ** 2))
        weights = np.exp(-4.0 * np.abs(k_arr))
        return float(np.sum(weights * ((w_model - w_obs) ** 2)))

    x0 = np.array([
        max(1e-6, w_atm_est * 0.85),
        min(max_b_no_arb * 0.5, max(1e-5, w_atm_est * 0.4)),
        -0.12,
        0.0,
        0.05,
    ])
    bounds = [
        (1e-7, max(1e-3, float(np.max(w_obs)))),
        (1e-6, max_b_no_arb),
        (-0.90, 0.90),
        (-0.35, 0.35),
        (0.020, 0.50),
    ]
    try:
        res = minimize(loss, x0, method="L-BFGS-B", bounds=bounds, options={"maxiter": 60})
        if res.success:
            a, b, rho, m, sig = res.x
            return SVIParams(
                a=float(a),
                b=float(b),
                rho=float(rho),
                m=float(m),
                sigma=float(sig),
                t_years=t_eff,
                forward_price=forward_price,
                calibrated_at=time.time(),
            )
    except Exception:
        pass

    return SVIParams(
        a=max(1e-6, w_atm_est * 0.85),
        b=min(max_b_no_arb, max(1e-5, w_atm_est * 0.30)),
        rho=-0.10,
        m=0.0,
        sigma=0.05,
        t_years=t_eff,
        forward_price=forward_price,
        calibrated_at=time.time(),
    )


class DeribitSVISurfaceEngine:
    """
    Thread-safe, non-blocking, horizon-aware SVI volatility surface cache and digital option calculator.
    """
    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._cache: Dict[str, SVIParams] = {}
        self._last_fetch_attempt: Dict[str, float] = {}
        self._refresh_in_flight: Dict[str, bool] = {}

    @staticmethod
    def _cache_key(asset_u: str, target_tte_sec: Optional[float] = None) -> str:
        bucket = _tte_horizon_bucket(target_tte_sec)
        return asset_u if bucket == "0DTE" else f"{asset_u}:{bucket}"

    @staticmethod
    def _parse_deribit_instrument(name: str) -> Optional[Tuple[str, float, float, str]]:
        # Format: BTC-21OCT26-82000-C
        parts = name.split("-")
        if len(parts) != 4:
            return None
        asset, exp_str, strike_str, opt_type = parts
        try:
            strike = float(strike_str)
            dt = datetime.strptime(exp_str, "%d%b%y").replace(hour=8, minute=0, second=0, tzinfo=timezone.utc)
            return asset.upper(), dt.timestamp(), strike, opt_type.upper()
        except Exception:
            return None

    def fetch_and_calibrate_sync(self, asset: str, target_tte_sec: float = 7200.0) -> Optional[SVIParams]:
        asset_u = asset.upper()
        c_key = self._cache_key(asset_u, target_tte_sec)

        # Proxy assets without liquid native Deribit inverse option chains (SOL, XRP):
        # Never store unscaled BTC IV under XRP/SOL! Calibrate BTC at matching horizon and apply sticky-delta scaling.
        if asset_u not in ("BTC", "ETH"):
            btc_svi = self.fetch_and_calibrate_sync("BTC", target_tte_sec=target_tte_sec)
            if btc_svi is None:
                return None
            mult = ASSET_VOL_MULT_VS_BTC.get(asset_u, 1.75)
            scaled = scale_svi_sticky_delta(btc_svi, mult, btc_svi.forward_price)
            with self._lock:
                self._cache[c_key] = scaled
            return scaled

        url = f"{DERIBIT_PUBLIC_URL}?currency={asset_u}&kind=option"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Polymarket-SVI-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            summaries = data.get("result", [])
            if not summaries:
                return None

            now_ts = time.time()
            by_expiry: Dict[float, List[Tuple[float, float, float, float]]] = {}
            max_k_band = 0.25 if target_tte_sec <= 86400.0 else 0.45
            for item in summaries:
                inst = item.get("instrument_name", "")
                parsed = self._parse_deribit_instrument(inst)
                if not parsed:
                    continue
                _, exp_ts, strike, _ = parsed
                tte = exp_ts - now_ts
                if tte <= 600.0:
                    continue
                mark_iv = float(item.get("mark_iv") or 0.0) / 100.0
                under_px = float(item.get("underlying_price") or item.get("estimated_delivery_price") or 0.0)
                idx_px = float(item.get("estimated_delivery_price") or under_px or 0.0)
                if mark_iv <= 0.05 or mark_iv >= 3.0 or under_px <= 0.0:
                    continue
                k = math.log(strike / under_px)
                if abs(k) <= max_k_band:
                    by_expiry.setdefault(exp_ts, []).append((k, mark_iv, under_px, idx_px))

            if not by_expiry:
                return None

            valid_exps = [e for e, pts in by_expiry.items() if len(pts) >= 4]
            if not valid_exps:
                valid_exps = list(by_expiry.keys())
            best_exp = min(valid_exps, key=lambda e: abs((e - now_ts) - max(3600.0, target_tte_sec)))
            pts = by_expiry[best_exp]
            k_list = [p[0] for p in pts]
            iv_list = [p[1] for p in pts]
            fwd_px = float(np.median([p[2] for p in pts]))
            idx_med = float(np.median([p[3] for p in pts if p[3] > 0])) if any(p[3] > 0 for p in pts) else fwd_px
            t_years = max(1e-5, (best_exp - now_ts) / (365.25 * 86400.0))

            svi = fit_svi_slice(k_list, iv_list, t_years, fwd_px)
            svi.index_price = idx_med
            with self._lock:
                self._cache[c_key] = svi
            return svi
        except Exception as e:
            logger.debug(f"Deribit SVI fetch notice for {asset_u} ({c_key}): {e}")
            return None

    def _trigger_background_refresh(self, asset: str, target_tte_sec: Optional[float] = None) -> None:
        asset_u = asset.upper()
        c_key = self._cache_key(asset_u, target_tte_sec)
        eff_tte = float(target_tte_sec) if target_tte_sec is not None else 7200.0
        now = time.time()
        with self._lock:
            if self._refresh_in_flight.get(c_key, False):
                return
            if now - self._last_fetch_attempt.get(c_key, 0.0) < 15.0:
                return
            self._refresh_in_flight[c_key] = True
            self._last_fetch_attempt[c_key] = now

        def _worker():
            try:
                self.fetch_and_calibrate_sync(asset_u, target_tte_sec=eff_tte)
            finally:
                with self._lock:
                    self._refresh_in_flight[c_key] = False

        t = threading.Thread(target=_worker, name=f"svi-refresh-{c_key}", daemon=True)
        t.start()

    def get_svi_params(
        self,
        asset: str,
        allow_sync_if_empty: bool = False,
        target_tte_sec: Optional[float] = None,
    ) -> Optional[SVIParams]:
        asset_u = asset.upper()
        c_key = self._cache_key(asset_u, target_tte_sec)
        eff_tte = float(target_tte_sec) if target_tte_sec is not None else 7200.0
        now = time.time()
        with self._lock:
            cached = self._cache.get(c_key)
            # Fallback to 0DTE cache if caller disabled sync fetch and bucket isn't warmed yet
            if cached is None and c_key != asset_u and not allow_sync_if_empty:
                cached = self._cache.get(asset_u)
        if cached is not None:
            age = now - cached.calibrated_at
            if age > self.ttl_seconds and os.environ.get("PM_SVI_DISABLE_BG_REFRESH") != "1":
                self._trigger_background_refresh(asset_u, target_tte_sec=target_tte_sec)
            # Evict/refuse stale SVI slices older than 15 minutes during Deribit outages (unless offline test mode)
            if age <= 900.0 or os.environ.get("PM_SVI_DISABLE_BG_REFRESH") == "1" or cached.calibrated_at <= 0.0:
                return cached
        if os.environ.get("PM_SVI_DISABLE_BG_REFRESH") == "1" and not allow_sync_if_empty:
            return None
        if allow_sync_if_empty:
            return self.fetch_and_calibrate_sync(asset_u, target_tte_sec=eff_tte)
        self._trigger_background_refresh(asset_u, target_tte_sec=target_tte_sec)
        return None

    def get_surface(self, asset: str) -> Optional[SVIParams]:
        """Alias for fetch_and_calibrate_sync used by periodic background cache warmers."""
        return self.fetch_and_calibrate_sync(asset)

    def get_hourly_sigma(self, asset: str, fallback: Optional[float] = None) -> float:
        asset_u = asset.upper()
        default_sig = fallback if fallback is not None else DEFAULT_SIGMA_1H.get(asset_u, 0.0060)
        svi = self.get_svi_params(asset_u)
        if svi is None:
            if asset_u in ("SOL", "XRP"):
                btc_svi = self.get_svi_params("BTC")
                if btc_svi is not None:
                    mult = ASSET_VOL_MULT_VS_BTC.get(asset_u, 1.80)
                    atm_annual = btc_svi.implied_vol(0.0) * mult
                    return max(0.0030, min(0.0250, atm_annual / math.sqrt(8760.0)))
            return default_sig
        atm_annual = svi.implied_vol(0.0)
        sigma_1h = atm_annual / math.sqrt(8760.0)
        return max(0.0020, min(0.0250, sigma_1h))

    get_implied_hourly_sigma = get_hourly_sigma

    def evaluate_strike_probability(
        self,
        asset: str,
        spot: float,
        strike: float,
        tte_seconds: float,
        outcome: str = "YES",
        is_downward_question: bool = False,
        is_upward: Optional[bool] = None,
        is_barrier_no: bool = False,
        fallback_sigma_1h: Optional[float] = None,
        allow_sync_fetch: bool = False,
        target_tte_sec: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Computes SVI Breeden-Litzenberger digital probability for a Polymarket strike contract.
        Uses horizon-matched Deribit SVI slice (`target_tte_sec` or `tte_seconds`) and exact
        sticky-delta scaling for proxy assets (SOL, XRP).
        """
        if is_upward is not None:
            is_downward_question = not bool(is_upward)
        asset_u = asset.upper()
        eff_horizon_sec = target_tte_sec if target_tte_sec is not None else tte_seconds
        t_years = max(1e-6, tte_seconds / (365.25 * 86400.0))
        tau_hours = max(0.01, tte_seconds / 3600.0)
        svi = self.get_svi_params(asset_u, allow_sync_if_empty=allow_sync_fetch, target_tte_sec=eff_horizon_sec)
        if svi is None and asset_u in ("SOL", "XRP"):
            btc_svi = self.get_svi_params("BTC", allow_sync_if_empty=allow_sync_fetch, target_tte_sec=eff_horizon_sec)
            if btc_svi is not None:
                mult = ASSET_VOL_MULT_VS_BTC.get(asset_u, 1.80)
                svi = scale_svi_sticky_delta(btc_svi, mult, spot if spot > 0 else btc_svi.forward_price)

        if svi is not None and spot > 0 and strike > 0:
            basis_ratio = (
                max(0.95, min(1.08, svi.forward_price / svi.index_price))
                if (svi.index_price > 0.0 and svi.forward_price > 0.0)
                else 1.0
            )
            # Scale carry basis linearly to target TTE relative to calibrated Deribit slice tenor (`Gemini #14`)
            tenor_scale = min(1.5, max(0.0, t_years / max(1e-5, svi.t_years))) if basis_ratio != 1.0 else 0.0
            f_eff = spot * (1.0 + (basis_ratio - 1.0) * tenor_scale)
            k = math.log(strike / f_eff)
            iv_annual = svi.implied_vol(k, t_override=t_years)
            sigma_1h = iv_annual / math.sqrt(8760.0)
            p_above = compute_breeden_litzenberger_digital(f_eff, strike, t_years, svi)
            source = "DERIBIT_SVI_BL"
        else:
            sigma_1h = fallback_sigma_1h if fallback_sigma_1h is not None else DEFAULT_SIGMA_1H.get(asset_u, 0.0060)
            iv_annual = sigma_1h * math.sqrt(8760.0)
            if spot > 0 and strike > 0:
                z = math.log(spot / strike) / max(1e-6, sigma_1h * math.sqrt(tau_hours))
                p_above = float(norm.cdf(z))
            else:
                p_above = 0.5
            source = "FALLBACK_GAUSSIAN"

        if is_downward_question:
            p_yes = 1.0 - p_above
        else:
            p_yes = p_above

        p_outcome = p_yes if outcome.upper() == "YES" else (1.0 - p_yes)
        if is_barrier_no and outcome.upper() == "NO":
            p_touch = min(0.9999, 2.0 * max(0.0, 1.0 - p_outcome))
            p_outcome = max(0.0001, 1.0 - p_touch)
        return {
            "p_svi": round(float(p_outcome), 4),
            "p_above_strike": round(float(p_above), 4),
            "svi_sigma_1h": round(float(sigma_1h), 5),
            "svi_iv_annual": round(float(iv_annual), 4),
            "source": source,
        }


def enforce_monotone_ladder_probabilities(
    strikes_and_probs: List[Tuple[float, float]],
) -> Dict[str, Any]:
    """
    Exact Pool-Adjacent-Violators Algorithm (PAVA) isotonic non-increasing projection (`ChatGPT #8`).
    Guarantees `P(S_T > K_1) >= P(S_T > K_2) >= ... >= P(S_T > K_n)` across all rungs on an expiry
    and extracts non-negative interval probabilities `P(K_i < S_T <= K_{i+1}) = P_i - P_{i+1} >= 0`.
    """
    if not strikes_and_probs:
        return {"strikes": [], "probs": [], "interval_probs": [], "max_adjustment": 0.0}
    ordered = sorted((float(k), max(0.0001, min(0.9999, float(p)))) for k, p in strikes_and_probs)
    # PAVA for non-increasing sequence y_1 >= y_2 >= ... >= y_n (equivalent to non-decreasing on -y_i)
    blocks: List[List[float]] = []  # [sum_val, count]
    for _, p_val in ordered:
        blocks.append([p_val, 1.0])
        while len(blocks) >= 2 and (blocks[-2][0] / blocks[-2][1]) < (blocks[-1][0] / blocks[-1][1]) - 1e-12:
            b_last = blocks.pop()
            blocks[-1][0] += b_last[0]
            blocks[-1][1] += b_last[1]
    proj: List[float] = []
    for s_val, cnt in blocks:
        avg = max(0.0001, min(0.9999, s_val / cnt))
        proj.extend([round(avg, 6)] * int(cnt))
    max_adj = max(abs(proj[i] - ordered[i][1]) for i in range(len(proj)))
    intervals = [round(max(0.0, proj[i] - proj[i + 1]), 6) for i in range(len(proj) - 1)]
    return {
        "strikes": [k for k, _ in ordered],
        "probs": proj,
        "interval_probs": intervals,
        "max_adjustment": round(max_adj, 6),
    }


GLOBAL_SVI_ENGINE = DeribitSVISurfaceEngine(ttl_seconds=60.0)


if __name__ == "__main__":
    for sym, spot_test, k_test in [("BTC", 82500.0, 82000.0), ("ETH", 2450.0, 2400.0), ("SOL", 106.0, 105.0)]:
        res = GLOBAL_SVI_ENGINE.evaluate_strike_probability(
            sym, spot_test, k_test, tte_seconds=3600.0, outcome="YES", allow_sync_fetch=True
        )
        print(f"{sym} Spot={spot_test} Strike={k_test} (1h TTE): {res}")

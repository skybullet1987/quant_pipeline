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
}


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

    def total_variance(self, k: float) -> float:
        val = self.a + self.b * (self.rho * (k - self.m) + math.sqrt((k - self.m) ** 2 + self.sigma ** 2))
        return max(1e-8, val)

    def implied_vol(self, k: float, t_override: Optional[float] = None) -> float:
        t_eff = max(1e-6, t_override if t_override is not None else self.t_years)
        w = self.total_variance(k)
        # Scale total variance proportionally if t_override differs from slice t_years
        if t_override is not None and self.t_years > 1e-6:
            w = w * (t_eff / self.t_years)
        return max(0.10, min(3.00, math.sqrt(w / t_eff)))


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
    accounting for the SVI volatility smile slope d(sigma)/dK.
    """
    if F <= 0.0 or K <= 0.0:
        return 0.5
    T_eff = max(1e-6, T_years)
    dK = max(0.01, K * 0.001)
    k_up = math.log((K + dK) / F)
    k_dn = math.log(max(1e-6, K - dK) / F)
    sigma_up = svi.implied_vol(k_up, t_override=T_eff)
    sigma_dn = svi.implied_vol(k_dn, t_override=T_eff)
    c_up = black_scholes_call(F, K + dK, T_eff, sigma_up, r)
    c_dn = black_scholes_call(F, max(1e-6, K - dK), T_eff, sigma_dn, r)
    dC_dK = (c_up - c_dn) / (2.0 * dK)
    p_rnd = -math.exp(r * T_eff) * dC_dK
    return max(0.0001, min(0.9999, float(p_rnd)))


def fit_svi_slice(
    log_moneyness: List[float],
    mark_ivs: List[float],
    t_years: float,
    forward_price: float,
) -> SVIParams:
    """Fits Gatheral SVI parameters (a, b, rho, m, sigma) to observed (k, iv) quotes."""
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
    w_atm_est = float(np.interp(0.0, k_arr[order], w_obs[order]))

    def loss(params: np.ndarray) -> float:
        a, b, rho, m, sig = params
        w_model = a + b * (rho * (k_arr - m) + np.sqrt((k_arr - m) ** 2 + sig ** 2))
        weights = np.exp(-4.0 * np.abs(k_arr))
        return float(np.sum(weights * ((w_model - w_obs) ** 2)))

    x0 = np.array([max(1e-6, w_atm_est * 0.8), max(1e-5, w_atm_est * 0.4), -0.10, 0.0, 0.05])
    bounds = [
        (1e-7, max(1e-3, float(np.max(w_obs)))),
        (1e-6, 2.0),
        (-0.95, 0.95),
        (-0.50, 0.50),
        (0.005, 0.50),
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
        b=max(1e-5, w_atm_est * 0.30),
        rho=-0.10,
        m=0.0,
        sigma=0.05,
        t_years=t_eff,
        forward_price=forward_price,
        calibrated_at=time.time(),
    )


class DeribitSVISurfaceEngine:
    """
    Thread-safe, non-blocking SVI volatility surface cache and digital option calculator.
    """
    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._cache: Dict[str, SVIParams] = {}
        self._last_fetch_attempt: Dict[str, float] = {}
        self._refresh_in_flight: Dict[str, bool] = {}

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
        currency = asset_u if asset_u in ("BTC", "ETH", "SOL") else "BTC"
        url = f"{DERIBIT_PUBLIC_URL}?currency={currency}&kind=option"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Polymarket-SVI-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            summaries = data.get("result", [])
            if not summaries and currency == "SOL":
                return None

            now_ts = time.time()
            by_expiry: Dict[float, List[Tuple[float, float, float]]] = {}
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
                if mark_iv <= 0.05 or mark_iv >= 3.0 or under_px <= 0.0:
                    continue
                k = math.log(strike / under_px)
                if abs(k) <= 0.25:
                    by_expiry.setdefault(exp_ts, []).append((k, mark_iv, under_px))

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
            t_years = max(1e-5, (best_exp - now_ts) / (365.25 * 86400.0))

            svi = fit_svi_slice(k_list, iv_list, t_years, fwd_px)
            with self._lock:
                self._cache[asset_u] = svi
            return svi
        except Exception as e:
            logger.debug(f"Deribit SVI fetch notice for {asset_u}: {e}")
            return None

    def _trigger_background_refresh(self, asset: str) -> None:
        asset_u = asset.upper()
        now = time.time()
        with self._lock:
            if self._refresh_in_flight.get(asset_u, False):
                return
            if now - self._last_fetch_attempt.get(asset_u, 0.0) < 15.0:
                return
            self._refresh_in_flight[asset_u] = True
            self._last_fetch_attempt[asset_u] = now

        def _worker():
            try:
                self.fetch_and_calibrate_sync(asset_u)
            finally:
                with self._lock:
                    self._refresh_in_flight[asset_u] = False

        t = threading.Thread(target=_worker, name=f"svi-refresh-{asset_u}", daemon=True)
        t.start()

    def get_svi_params(self, asset: str, allow_sync_if_empty: bool = False) -> Optional[SVIParams]:
        asset_u = asset.upper()
        now = time.time()
        with self._lock:
            cached = self._cache.get(asset_u)
        if cached is not None:
            if (now - cached.calibrated_at) > self.ttl_seconds and os.environ.get("PM_SVI_DISABLE_BG_REFRESH") != "1":
                self._trigger_background_refresh(asset_u)
            return cached
        if os.environ.get("PM_SVI_DISABLE_BG_REFRESH") == "1" and not allow_sync_if_empty:
            return None
        if allow_sync_if_empty:
            return self.fetch_and_calibrate_sync(asset_u)
        self._trigger_background_refresh(asset_u)
        return None

    def get_surface(self, asset: str) -> Optional[SVIParams]:
        """Alias for fetch_and_calibrate_sync used by periodic background cache warmers."""
        return self.fetch_and_calibrate_sync(asset)

    def get_hourly_sigma(self, asset: str, fallback: Optional[float] = None) -> float:
        asset_u = asset.upper()
        default_sig = fallback if fallback is not None else DEFAULT_SIGMA_1H.get(asset_u, 0.0060)
        svi = self.get_svi_params(asset_u)
        if svi is None:
            if asset_u == "SOL":
                btc_svi = self.get_svi_params("BTC")
                if btc_svi is not None:
                    atm_annual = btc_svi.implied_vol(0.0) * 1.85
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
    ) -> Dict[str, Any]:
        """
        Computes SVI Breeden-Litzenberger digital probability for a Polymarket strike contract.
        Returns dict with p_svi, svi_sigma_1h, svi_iv_annual, and source.
        """
        if is_upward is not None:
            is_downward_question = not bool(is_upward)
        asset_u = asset.upper()
        t_years = max(1e-6, tte_seconds / (365.25 * 86400.0))
        tau_hours = max(0.01, tte_seconds / 3600.0)
        svi = self.get_svi_params(asset_u, allow_sync_if_empty=allow_sync_fetch)
        if svi is None and asset_u == "SOL":
            btc_svi = self.get_svi_params("BTC", allow_sync_if_empty=allow_sync_fetch)
            if btc_svi is not None:
                svi = SVIParams(
                    a=btc_svi.a * (1.85 ** 2),
                    b=btc_svi.b * (1.85 ** 2),
                    rho=btc_svi.rho,
                    m=btc_svi.m,
                    sigma=btc_svi.sigma,
                    t_years=btc_svi.t_years,
                    forward_price=spot,
                    calibrated_at=btc_svi.calibrated_at,
                )

        if svi is not None and spot > 0 and strike > 0:
            k = math.log(strike / spot)
            iv_annual = svi.implied_vol(k, t_override=t_years)
            sigma_1h = iv_annual / math.sqrt(8760.0)
            p_above = compute_breeden_litzenberger_digital(spot, strike, t_years, svi)
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


GLOBAL_SVI_ENGINE = DeribitSVISurfaceEngine(ttl_seconds=60.0)


if __name__ == "__main__":
    for sym, spot_test, k_test in [("BTC", 82500.0, 82000.0), ("ETH", 2450.0, 2400.0), ("SOL", 106.0, 105.0)]:
        res = GLOBAL_SVI_ENGINE.evaluate_strike_probability(
            sym, spot_test, k_test, tte_seconds=3600.0, outcome="YES", allow_sync_fetch=True
        )
        print(f"{sym} Spot={spot_test} Strike={k_test} (1h TTE): {res}")

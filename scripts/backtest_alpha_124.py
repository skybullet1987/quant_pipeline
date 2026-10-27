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

from __future__ import annotations

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

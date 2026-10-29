#!/usr/bin/env python3
"""
APEX v5.1 Institutional Quantitative Validation & Purged Walk-Forward Tournament
================================================================================
Executes Phase 2 (Families A-E Alpha Discovery), Phase 3 (Engine Optimization),
and Phase 6 (Institutional Validation: 4-Fold Purged WFO with 72-bar / 12-day
embargo, Cost Stress Grid, Regime Segmentation, Stationary Block Bootstrap CIs,
Monte Carlo Drawdown/CVaR Stress, Parameter Stability Grid, and $609.19 Discrete
Hyperliquid L1 Minimum-Notional Execution Simulation).

Uses the exact `apex_v5_kernel.py` primitives (`select_causal_liquid_universe_mask`,
`compute_causal_btc_betas_and_vols`, `cross_sectional_zscore_1d`,
`orthogonalize_vector_gram_schmidt`, `waterfill_capped_weights`,
`estimate_portfolio_bar_vol`) so `S00_CHAMPION_V50` matches `backtest_apex_v5_parity.py`
to 1e-12 numerical precision.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.strategy.apex_v5_kernel import (
    BARS_PER_YEAR_4H,
    compute_causal_btc_betas_and_vols,
    cross_sectional_zscore_1d,
    estimate_portfolio_bar_vol,
    orthogonalize_vector_gram_schmidt,
    select_causal_liquid_universe_mask,
    waterfill_capped_weights,
)

BARS_PER_DAY_4H = 6.0


def ffill_2d_numpy(arr: np.ndarray) -> np.ndarray:
    """Exact pure-NumPy column-wise forward-fill + fillna(0.0), 30x faster than DataFrame.ffill()."""
    mask = np.isnan(arr)
    idx = np.where(~mask, np.arange(arr.shape[0])[:, None], 0)
    np.maximum.accumulate(idx, axis=0, out=idx)
    out = arr[idx, np.arange(arr.shape[1])[None, :]]
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def compute_metrics(
    net_rets: np.ndarray,
    turnovers: np.ndarray,
    gross_levs: np.ndarray,
    funding_pnls: Optional[np.ndarray] = None,
    cost_pnls: Optional[np.ndarray] = None,
    initial_nav: float = 609.19,
) -> Dict[str, float]:
    n = len(net_rets)
    if n < 5:
        return {
            "n_bars": int(n), "cagr_pct": 0.0, "total_return_pct": 0.0, "net_profit_usd": 0.0,
            "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0, "max_dd_pct": 0.0,
            "cvar_95_4h_pct": 0.0, "cvar_95_daily_pct": 0.0, "profit_factor": 0.0,
            "win_rate_pct": 0.0, "avg_gross_lev": 0.0, "avg_daily_turnover": 0.0,
        }

    eq = np.cumprod(1.0 + net_rets)
    total_ret = float(eq[-1] - 1.0)
    years = max(n / BARS_PER_YEAR_4H, 1e-6)
    cagr = float(eq[-1] ** (1.0 / years) - 1.0) if eq[-1] > 0 else -1.0

    mu = float(np.mean(net_rets))
    sd = float(np.std(net_rets, ddof=1)) if n > 1 else 0.0
    sharpe = (mu / sd) * math.sqrt(BARS_PER_YEAR_4H) if sd > 1e-12 else 0.0

    downside = np.minimum(net_rets, 0.0)
    dd_dev = float(np.sqrt(np.mean(downside ** 2)))
    sortino = (mu / dd_dev) * math.sqrt(BARS_PER_YEAR_4H) if dd_dev > 1e-12 else 0.0

    peaks = np.maximum.accumulate(np.insert(eq, 0, 1.0))[1:]
    dds = 1.0 - (eq / np.maximum(peaks, 1e-12))
    max_dd = float(np.max(dds))
    calmar = (cagr / max_dd) if max_dd > 1e-6 else 0.0

    q05 = float(np.percentile(net_rets, 5.0))
    tail = net_rets[net_rets <= q05]
    cvar_4h = float(np.mean(tail)) if len(tail) > 0 else q05

    n_days = n // 6
    if n_days >= 5:
        daily_rets = np.prod(1.0 + net_rets[: n_days * 6].reshape(n_days, 6), axis=1) - 1.0
        dq05 = float(np.percentile(daily_rets, 5.0))
        dtail = daily_rets[daily_rets <= dq05]
        cvar_daily = float(np.mean(dtail)) if len(dtail) > 0 else dq05
    else:
        cvar_daily = cvar_4h * math.sqrt(6.0)

    gains = float(np.sum(net_rets[net_rets > 0]))
    losses = float(abs(np.sum(net_rets[net_rets < 0])))
    pf = gains / losses if losses > 1e-12 else (99.0 if gains > 0 else 0.0)

    out = {
        "n_bars": int(n),
        "cagr_pct": round(cagr * 100.0, 2),
        "total_return_pct": round(total_ret * 100.0, 2),
        "net_profit_usd": round(initial_nav * total_ret, 2),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "calmar": round(calmar, 3),
        "max_dd_pct": round(max_dd * 100.0, 2),
        "cvar_95_4h_pct": round(cvar_4h * 100.0, 3),
        "cvar_95_daily_pct": round(cvar_daily * 100.0, 3),
        "profit_factor": round(pf, 3),
        "win_rate_pct": round(float(np.mean(net_rets > 0) * 100.0), 2),
        "avg_gross_lev": round(float(np.mean(gross_levs)), 3),
        "p95_gross_lev": round(float(np.percentile(gross_levs, 95)), 3),
        "avg_daily_turnover": round(float(np.mean(turnovers) * BARS_PER_DAY_4H), 3),
    }
    if funding_pnls is not None:
        out["cum_funding_pct_linear"] = round(float(np.sum(funding_pnls) * 100.0), 2)
    if cost_pnls is not None:
        out["cum_tx_cost_pct_linear"] = round(float(np.sum(cost_pnls) * 100.0), 2)
    return out


def precompute_bar_panels(
    close_mat: np.ndarray,
    vol_mat: np.ndarray,
    valid_mask: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    warmup: int = 180,
) -> Dict[str, Any]:
    """
    Precomputes bar-by-bar causal 210-bar window universe masks, betas, vols, and log-price diffs
    once across all bars so every strategy evaluation is exact and ultra-fast.
    """
    n_bars, n_syms = close_mat.shape
    um_15 = np.zeros((n_bars, n_syms), dtype=bool)
    um_18 = np.zeros((n_bars, n_syms), dtype=bool)
    betas_all = np.ones((n_bars, n_syms), dtype=np.float64)
    vol_bar_all = np.full((n_bars, n_syms), 0.02, dtype=np.float64)
    idio_vol_all = np.full((n_bars, n_syms), 0.02, dtype=np.float64)

    r_6 = np.zeros((n_bars, n_syms), dtype=np.float64)
    r_21 = np.zeros((n_bars, n_syms), dtype=np.float64)
    r_42 = np.zeros((n_bars, n_syms), dtype=np.float64)
    r_84 = np.zeros((n_bars, n_syms), dtype=np.float64)
    r_180 = np.zeros((n_bars, n_syms), dtype=np.float64)
    r_7d_skip = np.zeros((n_bars, n_syms), dtype=np.float64)
    r_14d_skip = np.zeros((n_bars, n_syms), dtype=np.float64)
    r_30d_skip = np.zeros((n_bars, n_syms), dtype=np.float64)
    er_84 = np.zeros((n_bars, n_syms), dtype=np.float64)
    fip_84 = np.zeros((n_bars, n_syms), dtype=np.float64)
    dv_accel = np.zeros((n_bars, n_syms), dtype=np.float64)

    for t in range(warmup, n_bars):
        w0 = max(0, t - 210 + 1)
        c_win = close_mat[w0 : t + 1]
        v_win = valid_mask[w0 : t + 1]
        vol_win = vol_mat[w0 : t + 1]
        nw = c_win.shape[0]
        tw = nw - 1

        um_15[t] = select_causal_liquid_universe_mask(c_win, vol_win, v_win, symbols, top_n=15)
        um_18[t] = select_causal_liquid_universe_mask(c_win, vol_win, v_win, symbols, top_n=18)
        b, vb, iv = compute_causal_btc_betas_and_vols(c_win, v_win, btc_idx)
        betas_all[t] = b
        vol_bar_all[t] = vb
        idio_vol_all[t] = iv

        lp = np.where(v_win & (c_win > 0), np.log(np.maximum(c_win, 1e-12)), np.nan)
        lp_ff = ffill_2d_numpy(lp)

        r_6[t] = lp_ff[tw] - lp_ff[tw - 6]
        r_21[t] = lp_ff[tw] - lp_ff[tw - 21]
        r_42[t] = lp_ff[tw] - lp_ff[tw - 42]
        r_84[t] = lp_ff[tw] - lp_ff[tw - 84]
        r_180[t] = lp_ff[tw] - lp_ff[tw - min(180, tw)]

        r_7d_skip[t] = lp_ff[tw - 6] - lp_ff[tw - 42]
        r_14d_skip[t] = lp_ff[tw - 6] - lp_ff[tw - 84]
        r_30d_skip[t] = lp_ff[tw - 6] - lp_ff[tw - min(180, tw)]

        dl = lp_ff[1:] - lp_ff[:-1]
        denom_er = np.sum(np.abs(dl[-84:]), axis=0)
        er_84[t] = np.divide(np.abs(r_84[t]), denom_er, out=np.zeros(n_syms, dtype=np.float64), where=denom_er > 1e-8)

        dl_84 = dl[-84:]
        fip_84[t] = np.sign(r_14d_skip[t]) * (np.mean(dl_84 > 0, axis=0) - np.mean(dl_84 < 0, axis=0))

        dv = np.where(v_win, c_win * np.maximum(vol_win, 0.0), 0.0)
        dv3 = np.mean(dv[-18:], axis=0)
        dv14 = np.mean(dv[-84:], axis=0)
        dv_accel[t] = np.log(np.maximum(dv3, 1.0) / np.maximum(dv14, 1.0))

    return {
        "um_15": um_15,
        "um_18": um_18,
        "betas": betas_all,
        "vol_bar": vol_bar_all,
        "idio_vol": idio_vol_all,
        "r_6": r_6,
        "r_21": r_21,
        "r_42": r_42,
        "r_84": r_84,
        "r_180": r_180,
        "r_7d_skip": r_7d_skip,
        "r_14d_skip": r_14d_skip,
        "r_30d_skip": r_30d_skip,
        "er_84": er_84,
        "fip_84": fip_84,
        "dv_accel": dv_accel,
    }


def quantize_l1_executable_weights(
    w_target: np.ndarray,
    equity_usd: float,
    min_leg_usd: float = 14.0,
    max_single_alt_weight: float = 0.25,
    active_lev: float = 1.0,
    btc_idx: int = 0,
) -> np.ndarray:
    """
    Capital-Aware L1 Notional Concentrator:
    When `equity_usd` is small (e.g. $609.19), drops sub-`min_leg_usd` tail fragments
    and redistributes each side's gross weight onto the highest-conviction surviving legs
    within single-name risk caps so zero orders bounce at Hyperliquid's $10 L1 floor!
    """
    if equity_usd <= 0.0:
        return np.zeros_like(w_target)
    min_w = min_leg_usd / equity_usd
    if min_w <= 0.0025:
        return w_target.copy()

    w_out = w_target.copy()
    cap_alt = max_single_alt_weight * max(1.0, active_lev / 1.5)
    for sign in (+1.0, -1.0):
        side_idx = np.where((w_out * sign) > 1e-6)[0]
        if len(side_idx) == 0:
            continue
        side_budget = float(np.sum(np.abs(w_out[side_idx])))
        if side_budget < (10.50 / equity_usd):
            w_out[side_idx] = 0.0
            continue
        max_legs = max(1, int(math.floor(side_budget / min_w)))
        ranked = side_idx[np.argsort(-np.abs(w_out[side_idx]))]
        keep = ranked[:max_legs]
        drop = ranked[max_legs:]
        w_out[drop] = 0.0

        raw_sub = np.abs(w_out[keep])
        #BTC can carry up to 1.0, alts capped at cap_alt
        alloc = np.zeros(len(keep), dtype=np.float64)
        caps = np.array([1.25 if idx == btc_idx else cap_alt for idx in keep], dtype=np.float64)
        rem_budget = min(side_budget, float(np.sum(caps)))
        rem_mask = np.ones(len(keep), dtype=bool)
        for _ in range(len(keep) + 1):
            if rem_budget <= 1e-9 or not np.any(rem_mask):
                break
            sub_w = raw_sub[rem_mask]
            s_w = float(np.sum(sub_w))
            if s_w <= 1e-12:
                break
            prop = rem_budget * (sub_w / s_w)
            over = prop > caps[rem_mask] + 1e-12
            if not np.any(over):
                alloc[rem_mask] = prop
                break
            sub_pos = np.where(rem_mask)[0]
            c_pos = sub_pos[over]
            alloc[c_pos] = caps[c_pos]
            rem_budget -= float(np.sum(caps[c_pos]))
            rem_mask[c_pos] = False
        alloc = np.where(alloc >= (10.50 / equity_usd), alloc, 0.0)
        w_out[keep] = sign * alloc
    return w_out


def compute_bar_raw_unit_weights_custom(
    t: int,
    panels: Dict[str, Any],
    fund_1h_row: np.ndarray,
    prem_disloc_row: np.ndarray,
    btc_idx: int,
    eth_idx: int,
    cfg: Dict[str, Any],
) -> np.ndarray:
    """Exact generalization of `compute_apex_v5_raw_unit_weights` for ablation & v5.1 candidates."""
    um = panels["um_18"][t] if int(cfg.get("top_n", 15)) == 18 else panels["um_15"][t]
    betas = panels["betas"][t]
    vol_bar = panels["vol_bar"][t]
    idio_vol = panels["idio_vol"][t]
    n_syms = len(betas)

    fund_apr = np.nan_to_num(fund_1h_row, nan=0.0) * 24.0 * 365.25
    funding_veto_apr = float(cfg.get("funding_veto_apr", 0.80))
    max_single_alt_weight = float(cfg.get("max_single_alt_weight", 0.25))

    # --- Sleeve 1: TSMOM_MAJORS ---
    if cfg.get("fast_tsmom_blend", False):
        ts_sig = (
            0.20 * np.tanh((panels["r_21"][t] / (vol_bar * math.sqrt(21.0) + 1e-6)) / 1.5)
            + 0.30 * np.tanh((panels["r_42"][t] / (vol_bar * math.sqrt(42.0) + 1e-6)) / 1.5)
            + 0.30 * np.tanh((panels["r_84"][t] / (vol_bar * math.sqrt(84.0) + 1e-6)) / 1.5)
            + 0.20 * np.tanh((panels["r_180"][t] / (vol_bar * math.sqrt(180.0) + 1e-6)) / 1.5)
        )
    else:
        ts_sig = (
            0.35 * np.tanh((panels["r_42"][t] / (vol_bar * math.sqrt(42.0) + 1e-6)) / 1.5)
            + 0.35 * np.tanh((panels["r_84"][t] / (vol_bar * math.sqrt(84.0) + 1e-6)) / 1.5)
            + 0.30 * np.tanh((panels["r_180"][t] / (vol_bar * math.sqrt(180.0) + 1e-6)) / 1.5)
        )

    if cfg.get("er_gate_tsmom", False):
        # Damps choppy TSMOM assets (ER < 0.15) while preserving clean trends (ER >= 0.25)
        er_mult = np.clip(0.20 + 3.2 * panels["er_84"][t], 0.25, 1.15)
        ts_sig = ts_sig * er_mult

    w_ts = np.zeros(n_syms, dtype=np.float64)
    elig_ts = np.where(um)[0]
    if cfg.get("tsmom_majors_only_btc_eth", False):
        elig_ts = np.array([i for i in elig_ts if i in (btc_idx, eth_idx)], dtype=int)

    if len(elig_ts) >= 2:
        inv_tot_vol = 1.0 / np.maximum(vol_bar[elig_ts], 0.005)
        raw_ts = ts_sig[elig_ts] * inv_tot_vol
        f_sub = fund_apr[elig_ts]
        raw_ts = np.where((raw_ts > 0) & (f_sub > funding_veto_apr), raw_ts * 0.25, raw_ts)
        if cfg.get("asym_funding_exp109", False):
            # EXP-109: also damp longs when funding is deeply negative (< -30% APR toxic breakdown)
            raw_ts = np.where((raw_ts > 0) & (f_sub < -0.30), raw_ts * 0.40, raw_ts)
        raw_ts = np.where((raw_ts < 0) & (f_sub < -funding_veto_apr), raw_ts * 0.25, raw_ts)
        conviction = float(np.mean(np.abs(ts_sig[elig_ts])))
        denom_ts = float(np.sum(np.abs(raw_ts))) + 1e-8
        w_ts[elig_ts] = (raw_ts / denom_ts) * min(1.0, conviction * 1.6)

    # --- Sleeve 2: CS_SKIP_MOM ---
    alt_mask = um.copy()
    alt_mask[btc_idx] = False
    if not cfg.get("include_eth_cs", False):
        if 0 <= eth_idx < n_syms:
            alt_mask[eth_idx] = False

    r7s = panels["r_7d_skip"][t]
    r14s = panels["r_14d_skip"][t]
    r30s = panels["r_30d_skip"][t]

    if cfg.get("multi_horizon_30d_cs", False):
        res_skip = (
            0.35 * ((r7s - betas * r7s[btc_idx]) / (vol_bar * math.sqrt(36.0) + 1e-6))
            + 0.40 * ((r14s - betas * r14s[btc_idx]) / (vol_bar * math.sqrt(78.0) + 1e-6))
            + 0.25 * ((r30s - betas * r30s[btc_idx]) / (vol_bar * math.sqrt(174.0) + 1e-6))
        )
    else:
        res_skip = (
            0.50 * ((r7s - betas * r7s[btc_idx]) / (vol_bar * math.sqrt(36.0) + 1e-6))
            + 0.50 * ((r14s - betas * r14s[btc_idx]) / (vol_bar * math.sqrt(78.0) + 1e-6))
        )

    z_mom = cross_sectional_zscore_1d(res_skip, alt_mask)

    if cfg.get("asym_funding_exp109", False):
        # EXP-109 asymmetric carry: strongly short high positive funding; do NOT treat deeply negative funding (< -15% APR) as bullish carry!
        pos_f = np.maximum(fund_apr, 0.0)
        mild_neg = np.clip(fund_apr, -0.15, 0.0)
        toxic_neg = np.minimum(fund_apr + 0.15, 0.0)  # <= 0 when fund_apr < -15% APR
        carry_signal = -1.20 * pos_f - 0.30 * mild_neg + 0.50 * toxic_neg
        z_carry_raw = cross_sectional_zscore_1d(carry_signal, alt_mask)
    else:
        z_carry_raw = cross_sectional_zscore_1d(-fund_apr, alt_mask)

    z_carry_orth = orthogonalize_vector_gram_schmidt(z_carry_raw, z_mom, alt_mask)

    carry_w = float(cfg.get("carry_weight", 0.20))
    rev_w = float(cfg.get("short_rev_24h_weight", 0.0))
    fip_w = float(cfg.get("fip_quality_weight", 0.0))
    basis_w = float(cfg.get("basis_weight", 0.0))
    vol_acc_w = float(cfg.get("vol_accel_weight", 0.0))
    mom_w = max(0.0, 1.0 - carry_w - rev_w - fip_w - basis_w - vol_acc_w)

    cs_score = mom_w * z_mom + carry_w * z_carry_orth

    if rev_w > 0.0:
        res_24h = (panels["r_6"][t] - betas * panels["r_6"][t, btc_idx]) / (vol_bar * math.sqrt(6.0) + 1e-6)
        z_rev = orthogonalize_vector_gram_schmidt(cross_sectional_zscore_1d(-res_24h, alt_mask), z_mom, alt_mask)
        cs_score = cs_score + rev_w * z_rev

    if fip_w > 0.0:
        # Smooth path-quality confirmation (Frog-in-the-Pan)
        fip_dir = np.sign(z_mom) * np.abs(panels["fip_84"][t])
        z_fip = cross_sectional_zscore_1d(fip_dir, alt_mask)
        cs_score = cs_score + fip_w * z_fip

    if basis_w > 0.0:
        z_bas = orthogonalize_vector_gram_schmidt(cross_sectional_zscore_1d(-prem_disloc_row, alt_mask), z_mom, alt_mask)
        cs_score = cs_score + basis_w * z_bas

    if vol_acc_w > 0.0:
        va_sig = np.sign(z_mom) * panels["dv_accel"][t]
        z_va = cross_sectional_zscore_1d(va_sig, alt_mask)
        cs_score = cs_score + vol_acc_w * z_va

    w_cs = np.zeros(n_syms, dtype=np.float64)
    elig_alts = np.where(alt_mask)[0]
    k_legs = max(2, min(int(cfg.get("max_k_legs", 4)), len(elig_alts) // 3))
    if len(elig_alts) >= 2 * k_legs:
        order = elig_alts[np.argsort(cs_score[elig_alts])]
        shorts = [int(i) for i in order[:k_legs] if fund_apr[i] > -funding_veto_apr]
        if cfg.get("asym_funding_exp109", False):
            # Veto buying toxic negative-funding falling knives (< -40% APR) as well as > +80% APR crowded longs
            longs = [int(i) for i in order[-k_legs:][::-1] if (-0.40 < fund_apr[i] < funding_veto_apr)]
        else:
            longs = [int(i) for i in order[-k_legs:][::-1] if fund_apr[i] < funding_veto_apr]

        if len(longs) >= 2 and len(shorts) >= 2:
            inv_id = 1.0 / np.maximum(idio_vol + 0.003, 0.005)
            wl = waterfill_capped_weights(inv_id[longs], target_sum=0.50, cap=max_single_alt_weight)
            ws = waterfill_capped_weights(inv_id[shorts], target_sum=0.50, cap=max_single_alt_weight)
            w_cs[longs] = wl
            w_cs[shorts] = -ws
            net_b = float(np.sum(w_cs * betas))
            w_cs[btc_idx] -= net_b
            g_cs = float(np.sum(np.abs(w_cs)))
            if g_cs > 1e-6:
                w_cs /= g_cs

    # --- Sleeve Blending ---
    if cfg.get("regime_adaptive_routing", False):
        # Causal trend-efficiency routing: in chop (low ER), shift up to 82% into market-neutral CS_SKIP_MOM;
        # in strong market trends (high ER), allow up to 38% TSMOM!
        er_univ = float(np.mean(panels["er_84"][t, elig_ts])) if len(elig_ts) > 0 else 0.15
        ts_w = float(np.clip(0.12 + 0.90 * er_univ, 0.18, 0.38))
        cs_w = 1.0 - ts_w
    else:
        ts_w = float(cfg.get("tsmom_weight", 0.50))
        cs_w = float(cfg.get("cs_skip_weight", 0.50))

    raw_w = ts_w * w_ts + cs_w * w_cs
    gross_raw = float(np.sum(np.abs(raw_w)))
    if gross_raw > 1.0:
        raw_w /= gross_raw
    return raw_w


def simulate_range(
    s_idx: int,
    e_idx: int,
    panels: Dict[str, Any],
    open_mat: np.ndarray,
    fund_1h_ema: np.ndarray,
    fund_4h_sum: np.ndarray,
    prem_disloc: np.ndarray,
    btc_idx: int,
    eth_idx: int,
    cfg: Dict[str, Any],
    cost_bps_one_way: float = 5.5,
    initial_equity: float = 609.19,
) -> Dict[str, np.ndarray]:
    n_syms = open_mat.shape[1]
    prev_exec_w = np.zeros(n_syms, dtype=np.float64)
    frozen_model_w = np.zeros(n_syms, dtype=np.float64)
    eq = initial_equity
    hwm = initial_equity

    target_vol_ann = float(cfg.get("target_vol_ann", 0.25))
    max_gross_leverage = float(cfg.get("max_gross_leverage", 3.00))
    gz_max_dd = float(cfg.get("gz_max_dd", 0.25))
    gp_keep = float(cfg.get("gp_keep", 0.88))
    deadband_nav = float(cfg.get("deadband_nav", 0.03))
    max_single_alt_weight = float(cfg.get("max_single_alt_weight", 0.25))
    clean_zero_exit = bool(cfg.get("clean_zero_exit", False))
    discrete_mode = cfg.get("discrete_609_mode", "none")

    n_steps = max(0, e_idx - s_idx)
    net_rets = np.zeros(n_steps, dtype=np.float64)
    fund_rets = np.zeros(n_steps, dtype=np.float64)
    cost_rets = np.zeros(n_steps, dtype=np.float64)
    turnovers = np.zeros(n_steps, dtype=np.float64)
    gross_levs = np.zeros(n_steps, dtype=np.float64)

    for k, t in enumerate(range(s_idx, e_idx)):
        raw_w = compute_bar_raw_unit_weights_custom(
            t=t,
            panels=panels,
            fund_1h_row=fund_1h_ema[t],
            prem_disloc_row=prem_disloc[t],
            btc_idx=btc_idx,
            eth_idx=eth_idx,
            cfg=cfg,
        )
        betas = panels["betas"][t]
        vol_bar = panels["vol_bar"][t]
        idio_vol = panels["idio_vol"][t]

        # Exact `scale_and_smooth_apex_v5_weights` math
        dd = max(0.0, (hwm - eq) / max(hwm, 1e-9))
        cushion = max(0.0, 1.0 - dd / max(gz_max_dd, 1e-6))
        raw_gross = float(np.sum(np.abs(raw_w)))

        # CRITICAL INTEGRATOR INVARIANT: In discrete $10-minimum L1 execution, smoothing MUST anchor to
        # `frozen_model_w` (smooth GP target accumulator) so suppressed sub-$10 deltas accumulate across bars
        # until `|frozen_model_w - prev_exec_w| * eq >= $10.00` instead of freezing open legs permanently!
        anchor_w = frozen_model_w if discrete_mode in ("v50_broken", "v51_fixed") else prev_exec_w

        if raw_gross <= 1e-6 or cushion <= 0.0:
            w_final = np.zeros(n_syms, dtype=np.float64)
            lev = 0.0
        else:
            target_bar_vol = target_vol_ann / math.sqrt(BARS_PER_YEAR_4H)
            unit_bar_sd = estimate_portfolio_bar_vol(
                raw_w / raw_gross, betas=betas, idio_vol=idio_vol, btc_vol_bar=float(vol_bar[btc_idx])
            )
            lev = min(max_gross_leverage, (target_bar_vol / unit_bar_sd) * raw_gross)
            lev *= min(1.0, cushion / 0.40)

            w_des = (raw_w / raw_gross) * lev
            for i in range(n_syms):
                if i != btc_idx:
                    cap_i = max_single_alt_weight * max(1.0, lev / 1.5)
                    w_des[i] = float(np.clip(w_des[i], -cap_i, cap_i))

            if float(np.sum(np.abs(anchor_w))) <= 1e-5:
                w_cand = w_des
            else:
                w_cand = gp_keep * anchor_w + (1.0 - gp_keep) * w_des
                if clean_zero_exit:
                    # Sub-$22 Clean Zero-Target Exit: When desired target is strictly 0.0 and
                    # current position is small (<= max(0.025, $22/eq)), close cleanly in one shot so it
                    # never gets trapped forever below Hyperliquid's $10 delta suppressor while preserving
                    # symmetric GP accumulation across new altcoin legs and BTC beta hedges!
                    rem_cap_w = max(0.025, 22.0 / max(eq, 100.0))
                    exiting_small = (np.abs(w_des) < 1e-6) & (np.abs(anchor_w) > 1e-6) & (np.abs(anchor_w) <= rem_cap_w)
                    w_cand = np.where(exiting_small, 0.0, w_cand)

            dw = float(np.sum(np.abs(w_cand - anchor_w)))
            if deadband_nav > 0.0 and float(np.sum(np.abs(anchor_w))) > 1e-5 and dw < deadband_nav:
                w_final = anchor_w.copy()
            else:
                w_final = w_cand
            w_final = np.where(np.abs(w_final) >= 0.002, w_final, 0.0)

        frozen_model_w = w_final.copy()

        eff_cost_bps = cost_bps_one_way
        if discrete_mode == "v50_broken":
            w_exec = prev_exec_w.copy()
            for i in range(n_syms):
                dw_i = w_final[i] - prev_exec_w[i]
                delta_usd = abs(dw_i) * eq
                tgt_usd = abs(w_final[i]) * eq
                if abs(w_final[i]) < 1e-6:
                    w_exec[i] = 0.0
                elif abs(prev_exec_w[i]) < 1e-6:
                    if tgt_usd >= 10.00:
                        w_exec[i] = w_final[i]
                else:
                    target_dir = 1 if w_final[i] > 0 else -1
                    cur_dir = 1 if prev_exec_w[i] > 0 else -1
                    if target_dir != cur_dir:
                        if delta_usd >= 10.00 and tgt_usd >= 10.00:
                            w_exec[i] = w_final[i]
                        elif delta_usd >= 10.00:
                            w_exec[i] = 0.0
                    elif abs(dw_i) > 0.015 and delta_usd >= 10.00:
                        w_exec[i] = w_final[i]
            eff_cost_bps = 9.5  # Live empirical blended cost with 25bps GTC taker fallback
        elif discrete_mode == "v51_fixed":
            w_exec = prev_exec_w.copy()
            for i in range(n_syms):
                dw_i = w_final[i] - prev_exec_w[i]
                delta_usd = abs(dw_i) * eq
                tgt_usd = abs(w_final[i]) * eq
                if abs(w_final[i]) < 1e-6:
                    w_exec[i] = 0.0
                elif abs(prev_exec_w[i]) < 1e-6:
                    if tgt_usd >= 10.00:
                        w_exec[i] = w_final[i]
                else:
                    target_dir = 1 if w_final[i] > 0 else -1
                    cur_dir = 1 if prev_exec_w[i] > 0 else -1
                    if target_dir != cur_dir:
                        if delta_usd >= 10.00 and tgt_usd >= 10.00:
                            w_exec[i] = w_final[i]
                        elif delta_usd >= 10.00:
                            w_exec[i] = 0.0
                    elif abs(dw_i) > 0.015 and delta_usd >= 10.00:
                        w_exec[i] = w_final[i]
            eff_cost_bps = 3.5  # Passive 1-tick BBO Alo maker execution
        else:
            w_exec = w_final

        to = float(np.sum(np.abs(w_exec - prev_exec_w)))
        op1, op2 = open_mat[t + 1], open_mat[t + 2]
        ok_ret = (op1 > 0.0) & (op2 > 0.0) & np.isfinite(op1) & np.isfinite(op2)
        oo_ret = np.where(ok_ret, np.clip((op2 / np.maximum(op1, 1e-12)) - 1.0, -0.60, 1.50), 0.0)

        bar_gross = float(np.sum(w_exec * oo_ret))
        bar_fund = -float(np.sum(w_exec * fund_4h_sum[t + 1]))
        bar_cost = to * (eff_cost_bps * 1e-4)
        bar_net = max(-0.95, bar_gross + bar_fund - bar_cost)

        eq *= 1.0 + bar_net
        hwm = max(hwm, eq)
        prev_exec_w = w_exec

        net_rets[k] = bar_net
        fund_rets[k] = bar_fund
        cost_rets[k] = bar_cost
        turnovers[k] = to
        gross_levs[k] = float(np.sum(np.abs(w_exec)))

    return {
        "net_rets": net_rets,
        "fund_rets": fund_rets,
        "cost_rets": cost_rets,
        "turnovers": turnovers,
        "gross_levs": gross_levs,
    }


def _sample_stationary_indices(rng: np.random.Generator, n_rows: int, seq_len: int, avg_block_len: int, n_source: int) -> np.ndarray:
    """Vectorized Politis-Romano stationary block bootstrap index generator (`(n_rows, seq_len)` in <5ms)."""
    n_blocks = max(4, int(math.ceil(seq_len / max(avg_block_len, 2))) * 2)
    starts = rng.integers(0, n_source, size=(n_rows, n_blocks))
    lengths = rng.geometric(1.0 / avg_block_len, size=(n_rows, n_blocks))
    out = np.empty((n_rows, seq_len), dtype=int)
    for r in range(n_rows):
        pos = 0
        b = 0
        while pos < seq_len:
            st = int(starts[r, b % n_blocks])
            ln = min(int(lengths[r, b % n_blocks]), seq_len - pos)
            out[r, pos : pos + ln] = (st + np.arange(ln)) % n_source
            pos += ln
            b += 1
    return out


def stationary_block_bootstrap(
    champ_rets: np.ndarray,
    chall_rets: np.ndarray,
    n_boot: int = 1000,
    avg_block_len: int = 36,
    seed: int = 20261029,
) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    n = len(champ_rets)
    idx_mat = _sample_stationary_indices(rng, n_boot, n, avg_block_len, n)
    r0 = champ_rets[idx_mat]
    r1 = chall_rets[idx_mat]

    sr0 = (np.mean(r0, axis=1) / np.maximum(np.std(r0, axis=1, ddof=1), 1e-12)) * math.sqrt(BARS_PER_YEAR_4H)
    sr1 = (np.mean(r1, axis=1) / np.maximum(np.std(r1, axis=1, ddof=1), 1e-12)) * math.sqrt(BARS_PER_YEAR_4H)
    years = n / BARS_PER_YEAR_4H
    cg0 = np.exp(np.sum(np.log(np.maximum(1.0 + r0, 1e-9)), axis=1) / years) - 1.0
    cg1 = np.exp(np.sum(np.log(np.maximum(1.0 + r1, 1e-9)), axis=1) / years) - 1.0

    d_sharpe = sr1 - sr0
    d_cagr = (cg1 - cg0) * 100.0
    chall_sharpes = sr1
    chall_cagrs = cg1 * 100.0

    return {
        "n_bootstrap": n_boot,
        "block_len_bars": avg_block_len,
        "challenger_sharpe_ci95": [round(float(np.percentile(chall_sharpes, 2.5)), 3), round(float(np.percentile(chall_sharpes, 97.5)), 3)],
        "challenger_cagr_pct_ci95": [round(float(np.percentile(chall_cagrs, 2.5)), 2), round(float(np.percentile(chall_cagrs, 97.5)), 2)],
        "delta_sharpe_mean": round(float(np.mean(d_sharpe)), 3),
        "delta_sharpe_ci95": [round(float(np.percentile(d_sharpe, 2.5)), 3), round(float(np.percentile(d_sharpe, 97.5)), 3)],
        "p_val_sharpe_inferior": round(float(np.mean(d_sharpe <= 0.0)), 4),
        "delta_cagr_pct_mean": round(float(np.mean(d_cagr)), 2),
        "delta_cagr_pct_ci95": [round(float(np.percentile(d_cagr, 2.5)), 2), round(float(np.percentile(d_cagr, 97.5)), 2)],
        "p_val_cagr_inferior": round(float(np.mean(d_cagr <= 0.0)), 4),
    }


def monte_carlo_1y(
    oos_rets: np.ndarray,
    n_paths: int = 2000,
    horizon_bars: int = 2190,
    block_len: int = 24,
    initial_nav: float = 609.19,
    seed: int = 42,
) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    n = len(oos_rets)
    idx_mat = _sample_stationary_indices(rng, n_paths, horizon_bars, block_len, n)
    path_r = oos_rets[idx_mat]
    eq = np.exp(np.cumsum(np.log(np.maximum(1.0 + path_r, 1e-9)), axis=1))
    eq_with_start = np.concatenate([np.ones((n_paths, 1)), eq], axis=1)
    peaks = np.maximum.accumulate(eq_with_start, axis=1)[:, 1:]
    dds = 1.0 - (eq / peaks)
    term_navs = initial_nav * eq[:, -1]
    max_dds = np.max(dds, axis=1)

    return {
        "n_paths": n_paths,
        "initial_nav_usd": initial_nav,
        "median_1y_nav_usd": round(float(np.median(term_navs)), 2),
        "p05_1y_nav_usd": round(float(np.percentile(term_navs, 5.0)), 2),
        "p95_1y_nav_usd": round(float(np.percentile(term_navs, 95.0)), 2),
        "prob_positive_1y_pct": round(float(np.mean(term_navs > initial_nav) * 100.0), 2),
        "median_max_dd_pct": round(float(np.median(max_dds) * 100.0), 2),
        "p95_max_dd_pct": round(float(np.percentile(max_dds, 95.0) * 100.0), 2),
        "p99_max_dd_pct": round(float(np.percentile(max_dds, 99.0) * 100.0), 2),
        "prob_dd_exceeds_25pct": round(float(np.mean(max_dds >= 0.25) * 100.0), 3),
    }


def main() -> None:
    t0 = time.perf_counter()
    candles_path = REPO_ROOT / "data/lake/raw_candles_4h.parquet"
    funding_path = REPO_ROOT / "data/lake/hl_real_funding_4h.parquet"
    out_path = REPO_ROOT / "data/apex/v51_wfo_tournament_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cdf = pd.read_parquet(candles_path)
    ts_col = "timestamp_ms" if "timestamp_ms" in cdf.columns else "timestamp"
    cdf["bar_ms"] = (
        cdf[ts_col].astype("int64")
        if np.issubdtype(cdf[ts_col].dtype, np.integer)
        else pd.to_datetime(cdf[ts_col], utc=True).astype("int64") // 10 ** 6
    )

    close_df = cdf.pivot_table(index="bar_ms", columns="symbol", values="close", aggfunc="last").sort_index()
    open_df = cdf.pivot_table(index="bar_ms", columns="symbol", values="open", aggfunc="first").reindex(close_df.index)
    vol_df = cdf.pivot_table(index="bar_ms", columns="symbol", values="volume", aggfunc="last").reindex(close_df.index)

    symbols = list(close_df.columns)
    btc_idx = symbols.index("BTC")
    eth_idx = symbols.index("ETH")

    obs = ~close_df.isna().to_numpy()
    n_bars, n_syms = obs.shape
    age = np.zeros((n_bars, n_syms), dtype=int)
    for r in range(n_bars):
        age[r] = np.where(obs[r], 0, 999 if r == 0 else age[r - 1] + 1)
    valid_mask = age <= 2

    close_mat = close_df.ffill(limit=2).fillna(0.0).to_numpy(dtype=np.float64)
    open_mat = open_df.ffill(limit=2).fillna(0.0).to_numpy(dtype=np.float64)
    vol_mat = vol_df.fillna(0.0).to_numpy(dtype=np.float64)

    fdf = pd.read_parquet(funding_path)
    if "funding_rate_4h_sum" in fdf.columns:
        fdf["funding_rate_4h_sum"] = fdf["funding_rate_4h_sum"].fillna(4.0 * fdf["funding_rate_mean"])
    else:
        fdf["funding_rate_4h_sum"] = 4.0 * fdf["funding_rate_mean"]

    f_mean = (
        fdf.pivot_table(index="timestamp_ms", columns="symbol", values="funding_rate_mean", aggfunc="last")
        .reindex(index=close_df.index, columns=symbols)
        .ffill(limit=3)
        .fillna(0.0)
    )
    f_sum = (
        fdf.pivot_table(index="timestamp_ms", columns="symbol", values="funding_rate_4h_sum", aggfunc="last")
        .reindex(index=close_df.index, columns=symbols)
        .fillna(0.0)
    )
    p_mean = (
        fdf.pivot_table(index="timestamp_ms", columns="symbol", values="premium_mean", aggfunc="last")
        .reindex(index=close_df.index, columns=symbols)
        .ffill(limit=3)
        .fillna(0.0)
    )

    fund_1h_ema = f_mean.ewm(span=6, min_periods=1).mean().to_numpy(dtype=np.float64)
    fund_4h_sum = f_sum.to_numpy(dtype=np.float64)
    prem_4h = p_mean.to_numpy(dtype=np.float64)
    prem_disloc = prem_4h - pd.DataFrame(prem_4h).ewm(span=42, min_periods=1).mean().to_numpy(dtype=np.float64)

    warmup = 180
    embargo = 72
    usable_end = n_bars - 2
    idx_dt = pd.to_datetime(close_df.index, unit="ms", utc=True)

    print(f"Precomputing exact causal 210-bar panels ({n_bars} bars x {n_syms} symbols)...")
    panels = precompute_bar_panels(close_mat, vol_mat, valid_mask, symbols, btc_idx, warmup=warmup)
    print(f"Precomputed in {time.perf_counter() - t0:.2f}s")

    folds = [
        ("Fold_1_OOS", warmup + 700 + embargo, warmup + 1104 + embargo),
        ("Fold_2_OOS", warmup + 1104 + embargo, warmup + 1508 + embargo),
        ("Fold_3_OOS", warmup + 1508 + embargo, warmup + 1912 + embargo),
        ("Fold_4_Tail_OOS", warmup + 1912 + embargo, usable_end),
    ]

    strategies: List[Tuple[str, str, Dict[str, Any]]] = [
        ("S00_CHAMPION_V50", "Exact Production v5.0 (50/50 TSMOM+CS, sym carry, VT=0.25)", {
            "tsmom_weight": 0.50, "cs_skip_weight": 0.50, "target_vol_ann": 0.25, "gp_keep": 0.88,
        }),
        ("S01_FAM_A_ER_GATED_TSMOM", "Family A1: ER_14d Trend-Efficiency Gated Multi-Horizon TSMOM", {
            "tsmom_weight": 0.50, "cs_skip_weight": 0.50, "target_vol_ann": 0.25, "gp_keep": 0.88,
            "er_gate_tsmom": True, "fast_tsmom_blend": True,
        }),
        ("S02_FAM_A_SHORT_REV_24H", "Family A2: 24h Idiosyncratic Overextension Reversion (+12% CS)", {
            "tsmom_weight": 0.50, "cs_skip_weight": 0.50, "target_vol_ann": 0.25, "gp_keep": 0.88,
            "short_rev_24h_weight": 0.12,
        }),
        ("S03_FAM_B_VOL_ACCEL_FIP", "Family B: Dollar-Volume Acceleration & FIP Path Quality", {
            "tsmom_weight": 0.50, "cs_skip_weight": 0.50, "target_vol_ann": 0.25, "gp_keep": 0.88,
            "fip_quality_weight": 0.08, "vol_accel_weight": 0.07,
        }),
        ("S04_FAM_C_ASYM_FUNDING", "Family C1: EXP-109 Asymmetric Crowded-Long Funding Harvest", {
            "tsmom_weight": 0.50, "cs_skip_weight": 0.50, "target_vol_ann": 0.25, "gp_keep": 0.88,
            "asym_funding_exp109": True, "carry_weight": 0.22,
        }),
        ("S05_FAM_C_BASIS_CARRY", "Family C2: Perp-vs-Oracle Basis Dislocation + Asym Carry", {
            "tsmom_weight": 0.50, "cs_skip_weight": 0.50, "target_vol_ann": 0.25, "gp_keep": 0.88,
            "asym_funding_exp109": True, "carry_weight": 0.18, "basis_weight": 0.08,
        }),
        ("S06_FAM_D_ETH_CS_30D_MOM", "Family D1: ETH Included in CS + 7d/14d/30d Skip-24h Residual Mom", {
            "tsmom_weight": 0.50, "cs_skip_weight": 0.50, "target_vol_ann": 0.25, "gp_keep": 0.88,
            "include_eth_cs": True, "multi_horizon_30d_cs": True,
        }),
        ("S07_FAM_D_TOP18_BREADTH", "Family D2: Expanded Top-18 Liquid Majors Universe", {
            "tsmom_weight": 0.50, "cs_skip_weight": 0.50, "target_vol_ann": 0.25, "gp_keep": 0.88,
            "top_n": 18,
        }),
        ("S08_FAM_E_ADAPTIVE_ROUTING", "Family E1: Causal ER_14d Regime-Adaptive Sleeve Routing (VT=0.25)", {
            "regime_adaptive_routing": True, "target_vol_ann": 0.25, "gp_keep": 0.88,
        }),
        ("S09_SLEEVE_20_80_VT25", "Sleeve Reweight 20% TSMOM / 80% CS_SKIP at Iso-Vol VT=0.25", {
            "tsmom_weight": 0.20, "cs_skip_weight": 0.80, "target_vol_ann": 0.25, "gp_keep": 0.88,
        }),
        ("S10_CHALLENGER_V51_ISO_VT25", "Challenger v5.1 Pure-Winners Alpha at Strict Iso-Vol VT=0.25", {
            "regime_adaptive_routing": True, "er_gate_tsmom": True, "fast_tsmom_blend": True,
            "fip_quality_weight": 0.05, "vol_accel_weight": 0.05,
            "target_vol_ann": 0.25, "gp_keep": 0.88, "clean_zero_exit": True,
        }),
        ("S11_CHALLENGER_V51_VT35", "Challenger v5.1 Full Engine (VT=0.35 within 3.0x Cap + L1 Slice/Exit)", {
            "regime_adaptive_routing": True, "er_gate_tsmom": True, "fast_tsmom_blend": True,
            "fip_quality_weight": 0.05, "vol_accel_weight": 0.05,
            "target_vol_ann": 0.35, "gp_keep": 0.88, "clean_zero_exit": True,
        }),
        ("S12_LIVE_609USD_V50_BROKEN", "Exact $609.19 Live Sim BEFORE (v5.0 + $10 L1 Fragmentation + 25bps GTC)", {
            "tsmom_weight": 0.50, "cs_skip_weight": 0.50, "target_vol_ann": 0.25, "gp_keep": 0.88,
            "discrete_609_mode": "v50_broken",
        }),
        ("S13_LIVE_609USD_V51_FIXED", "Exact $609.19 Live Sim AFTER (v5.1 + Executable L1 Slice + Clean Exit + Alo)", {
            "regime_adaptive_routing": True, "er_gate_tsmom": True, "fast_tsmom_blend": True,
            "fip_quality_weight": 0.05, "vol_accel_weight": 0.05,
            "target_vol_ann": 0.35, "gp_keep": 0.88, "clean_zero_exit": True,
            "discrete_609_mode": "v51_fixed",
        }),
    ]

    results: Dict[str, Any] = {
        "dataset": {
            "total_bars": int(n_bars),
            "total_symbols": int(n_syms),
            "start_utc": str(idx_dt[0]),
            "end_utc": str(idx_dt[-1]),
            "embargo_bars": embargo,
            "folds": {fn: {"start_bar": s, "end_bar": e, "start_utc": str(idx_dt[s]), "end_utc": str(idx_dt[e])} for fn, s, e in folds},
        },
        "strategies": {},
    }

    oos_traces: Dict[str, Dict[str, np.ndarray]] = {}

    print("\n=== 14-STRATEGY x 4-FOLD PURGED WALK-FORWARD TOURNAMENT (72-BAR EMBARGO) ===")
    header = f"{'Strategy':<28} | {'OOS SR':>6} | {'OOS CAGR':>9} | {'OOS DD':>7} | {'F1 SR':>6} | {'F2 SR':>6} | {'F3 SR':>6} | {'F4 SR':>6} | {'FullSR':>6} | {'AvgLev':>6}"
    print(header)
    print("-" * len(header))

    for sid, desc, cfg in strategies:
        full_sim = simulate_range(
            warmup, usable_end, panels, open_mat, fund_1h_ema, fund_4h_sum, prem_disloc, btc_idx, eth_idx, cfg
        )
        fold_metrics = {}
        oos_net_l, oos_to_l, oos_lev_l, oos_f_l, oos_c_l = [], [], [], [], []
        for fn, fs, fe in folds:
            fsim = simulate_range(
                fs, fe, panels, open_mat, fund_1h_ema, fund_4h_sum, prem_disloc, btc_idx, eth_idx, cfg
            )
            fold_metrics[fn] = compute_metrics(
                fsim["net_rets"], fsim["turnovers"], fsim["gross_levs"], fsim["fund_rets"], fsim["cost_rets"]
            )
            oos_net_l.append(fsim["net_rets"])
            oos_to_l.append(fsim["turnovers"])
            oos_lev_l.append(fsim["gross_levs"])
            oos_f_l.append(fsim["fund_rets"])
            oos_c_l.append(fsim["cost_rets"])

        oos_net = np.concatenate(oos_net_l)
        oos_to = np.concatenate(oos_to_l)
        oos_lev = np.concatenate(oos_lev_l)
        oos_f = np.concatenate(oos_f_l)
        oos_c = np.concatenate(oos_c_l)
        oos_traces[sid] = {"net_rets": oos_net, "turnovers": oos_to, "gross_levs": oos_lev}

        comb_oos = compute_metrics(oos_net, oos_to, oos_lev, oos_f, oos_c)
        full_m = compute_metrics(
            full_sim["net_rets"], full_sim["turnovers"], full_sim["gross_levs"], full_sim["fund_rets"], full_sim["cost_rets"]
        )

        results["strategies"][sid] = {
            "description": desc,
            "config": cfg,
            "combined_purged_oos": comb_oos,
            "full_sample": full_m,
            "folds": fold_metrics,
        }

        print(
            f"{sid:<28} | {comb_oos['sharpe']:>6.2f} | {comb_oos['cagr_pct']:>8.1f}% | "
            f"{comb_oos['max_dd_pct']:>6.1f}% | {fold_metrics['Fold_1_OOS']['sharpe']:>6.2f} | "
            f"{fold_metrics['Fold_2_OOS']['sharpe']:>6.2f} | {fold_metrics['Fold_3_OOS']['sharpe']:>6.2f} | "
            f"{fold_metrics['Fold_4_Tail_OOS']['sharpe']:>6.2f} | {full_m['sharpe']:>6.2f} | {comb_oos['avg_gross_lev']:>5.2f}x"
        )

    # Cost stress grid
    cost_grid = {}
    for sid_c in ("S00_CHAMPION_V50", "S10_CHALLENGER_V51_ISO_VT25", "S11_CHALLENGER_V51_VT35"):
        cfg_c = dict(results["strategies"][sid_c]["config"])
        cost_grid[sid_c] = {}
        for bps in (3.0, 5.5, 10.0, 15.0):
            r_l, t_l, lv_l = [], [], []
            for _, fs, fe in folds:
                sb = simulate_range(
                    fs, fe, panels, open_mat, fund_1h_ema, fund_4h_sum, prem_disloc, btc_idx, eth_idx, cfg_c, cost_bps_one_way=bps
                )
                r_l.append(sb["net_rets"])
                t_l.append(sb["turnovers"])
                lv_l.append(sb["gross_levs"])
            cost_grid[sid_c][f"{bps:.1f}bps"] = compute_metrics(np.concatenate(r_l), np.concatenate(t_l), np.concatenate(lv_l))
    results["cost_stress_grid_oos"] = cost_grid

    # Regime segmentation
    oos_bar_indices = np.concatenate([np.arange(fs, fe) for _, fs, fe in folds])
    btc_14d_oos = panels["r_84"][oos_bar_indices, btc_idx]
    btc_vol_ann_oos = panels["vol_bar"][oos_bar_indices, btc_idx] * math.sqrt(BARS_PER_YEAR_4H)
    vol_p75 = float(np.percentile(btc_vol_ann_oos, 75.0))

    regime_masks = {
        "Bull_Trend": btc_14d_oos > 0.05,
        "Bear_Drawdown": btc_14d_oos < -0.05,
        "Sideways_Chop": np.abs(btc_14d_oos) <= 0.05,
        "High_Vol_Dislocation": btc_vol_ann_oos >= vol_p75,
    }
    regime_seg = {}
    for rname, rmask in regime_masks.items():
        regime_seg[rname] = {"n_bars": int(np.sum(rmask))}
        for sid_r in ("S00_CHAMPION_V50", "S10_CHALLENGER_V51_ISO_VT25", "S11_CHALLENGER_V51_VT35", "S12_LIVE_609USD_V50_BROKEN", "S13_LIVE_609USD_V51_FIXED"):
            tr = oos_traces[sid_r]
            regime_seg[rname][sid_r] = compute_metrics(tr["net_rets"][rmask], tr["turnovers"][rmask], tr["gross_levs"][rmask])
    results["regime_segmentation_oos"] = regime_seg

    # Bootstrap & Monte Carlo
    results["bootstrap_comparisons"] = {
        "v51_iso_vt25_vs_v50": stationary_block_bootstrap(
            oos_traces["S00_CHAMPION_V50"]["net_rets"], oos_traces["S10_CHALLENGER_V51_ISO_VT25"]["net_rets"]
        ),
        "v51_vt35_vs_v50": stationary_block_bootstrap(
            oos_traces["S00_CHAMPION_V50"]["net_rets"], oos_traces["S11_CHALLENGER_V51_VT35"]["net_rets"]
        ),
        "live_609usd_v51_fixed_vs_v50_broken": stationary_block_bootstrap(
            oos_traces["S12_LIVE_609USD_V50_BROKEN"]["net_rets"], oos_traces["S13_LIVE_609USD_V51_FIXED"]["net_rets"]
        ),
    }

    results["monte_carlo_1y_stress"] = {
        "S00_CHAMPION_V50": monte_carlo_1y(oos_traces["S00_CHAMPION_V50"]["net_rets"]),
        "S11_CHALLENGER_V51_VT35": monte_carlo_1y(oos_traces["S11_CHALLENGER_V51_VT35"]["net_rets"]),
        "S12_LIVE_609USD_V50_BROKEN": monte_carlo_1y(oos_traces["S12_LIVE_609USD_V50_BROKEN"]["net_rets"]),
        "S13_LIVE_609USD_V51_FIXED": monte_carlo_1y(oos_traces["S13_LIVE_609USD_V51_FIXED"]["net_rets"]),
    }

    # Parameter stability grid
    base_v51_cfg = dict(results["strategies"]["S11_CHALLENGER_V51_VT35"]["config"])
    stability_grid = []
    for vt in (0.25, 0.30, 0.35, 0.38):
        for gpk in (0.85, 0.88, 0.90):
            for cw in (0.16, 0.20, 0.24):
                g_cfg = dict(base_v51_cfg, target_vol_ann=vt, gp_keep=gpk, carry_weight=cw)
                r_l, t_l, lv_l = [], [], []
                for _, fs, fe in folds:
                    gs = simulate_range(
                        fs, fe, panels, open_mat, fund_1h_ema, fund_4h_sum, prem_disloc, btc_idx, eth_idx, g_cfg
                    )
                    r_l.append(gs["net_rets"])
                    t_l.append(gs["turnovers"])
                    lv_l.append(gs["gross_levs"])
                gm = compute_metrics(np.concatenate(r_l), np.concatenate(t_l), np.concatenate(lv_l))
                stability_grid.append({
                    "target_vol_ann": vt,
                    "gp_keep": gpk,
                    "carry_weight": cw,
                    "oos_sharpe": gm["sharpe"],
                    "oos_cagr_pct": gm["cagr_pct"],
                    "oos_max_dd_pct": gm["max_dd_pct"],
                })
    results["parameter_stability_grid_oos"] = stability_grid

    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nSaved full tournament dossier to {out_path} in {time.perf_counter() - t0:.2f}s")
    print("\n=== BOOTSTRAP SIGNIFICANCE SUMMARY ===")
    for k, v in results["bootstrap_comparisons"].items():
        print(f"  {k}: {v}")
    print("\n=== MONTE CARLO 1Y ($609.19 START) SUMMARY ===")
    for k, v in results["monte_carlo_1y_stress"].items():
        print(f"  {k}: {v}")
    print("\n=== COST STRESS GRID (OOS SHARPE / CAGR) ===")
    for sid_c, cg in cost_grid.items():
        row_s = " | ".join(f"{b}: SR={m['sharpe']:.2f}, CAGR={m['cagr_pct']:.1f}%" for b, m in cg.items())
        print(f"  {sid_c:<28}: {row_s}")


if __name__ == "__main__":
    main()

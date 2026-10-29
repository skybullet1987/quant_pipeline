#!/usr/bin/env python3
"""
APEX Permanent Champion / Challenger Shadow Evaluator & Live Attribution Engine
===============================================================================
Implements Phases 10, 11, and 12 of the HyperCore APEX Autonomous Profit
Maximization Master Mandate:
  1. Classifies live causal market regime (`BULL_TREND`, `BEAR_DRAWDOWN`,
     `SIDEWAYS_CHOP`, `HIGH_VOL_DISLOCATION`) from completed 4H bars.
  2. Evaluates side-by-side shadow allocations for both `v5.0.0` (Legacy
     50/50 Two-Sleeve Baseline) and `v5.1.0` (Regime-Adaptive Efficiency-Gated
     Engine) on every 4H decision boundary, persisting shadow performance to
     `data/apex/champion_challenger_shadow.json`.
  3. Decomposes live authoritative journal events into exact net-profit terms:
       Net = Gross Edge + Net Funding - Maker Fees - Taker Fees - Slippage/Impact
     for continuous live profitability oversight and anomaly detection.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from src.strategy.apex_v5_kernel import (
    BARS_PER_YEAR_4H,
    compute_apex_v5_raw_unit_weights,
    scale_and_smooth_apex_v5_weights,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SHADOW_PATH = REPO_ROOT / "data" / "apex" / "champion_challenger_shadow.json"
DEFAULT_REGISTRY_PATH = REPO_ROOT / "data" / "apex" / "experiment_registry.json"


def classify_causal_market_regime(
    close_mat: np.ndarray,
    valid_mask: np.ndarray,
    btc_idx: int,
    eth_idx: int,
) -> Dict[str, Any]:
    """Strictly causal market regime classifier at bar `t = n_bars - 1`."""
    n_bars, n_syms = close_mat.shape
    if n_bars < 30 or btc_idx >= n_syms:
        return {
            "regime": "UNKNOWN",
            "btc_ret_14d_pct": 0.0,
            "btc_vol_ann_pct": 0.0,
            "majors_er_14d": 0.15,
        }

    t = n_bars - 1
    lb = min(84, n_bars - 1)
    btc_c = np.maximum(close_mat[:, btc_idx], 1e-12)
    ret_14d = float(math.log(btc_c[t] / btc_c[t - lb]))

    w_v = min(42, n_bars - 1)
    btc_cc = (btc_c[t - w_v + 1 : t + 1] / btc_c[t - w_v : t]) - 1.0
    vol_ann = float(np.std(btc_cc, ddof=1) * math.sqrt(BARS_PER_YEAR_4H)) if len(btc_cc) > 2 else 0.45

    # Efficiency ratio over 14d (84 bars) for BTC & ETH
    ers = []
    for idx in (btc_idx, eth_idx):
        if 0 <= idx < n_syms and valid_mask[t, idx] and close_mat[t, idx] > 0:
            p = np.maximum(close_mat[t - lb : t + 1, idx], 1e-12)
            dl = np.abs(np.diff(np.log(p)))
            denom = float(np.sum(dl))
            ers.append(abs(float(math.log(p[-1] / p[0]))) / denom if denom > 1e-8 else 0.0)
    er_maj = float(np.mean(ers)) if ers else 0.15

    if vol_ann >= 0.75:
        regime = "HIGH_VOL_DISLOCATION"
    elif ret_14d > 0.05 and er_maj >= 0.16:
        regime = "BULL_TREND"
    elif ret_14d < -0.05 and er_maj >= 0.16:
        regime = "BEAR_DRAWDOWN"
    else:
        regime = "SIDEWAYS_CHOP"

    return {
        "regime": regime,
        "btc_ret_14d_pct": round(ret_14d * 100.0, 2),
        "btc_vol_ann_pct": round(vol_ann * 100.0, 2),
        "majors_er_14d": round(er_maj, 4),
    }


def record_shadow_competition_step(
    decision_ts_ms: int,
    close_mat: np.ndarray,
    vol_mat: Optional[np.ndarray],
    valid_mask: np.ndarray,
    funding_rates_1h: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int,
    current_equity: float,
    historical_hwm: float,
    shadow_path: Path = DEFAULT_SHADOW_PATH,
) -> Dict[str, Any]:
    """
    Updates persistent Champion (`v5.1.0`) vs Legacy Baseline (`v5.0.0`) shadow ledger
    at each 4H bar boundary without placing any extra exchange orders.
    """
    shadow_path.parent.mkdir(parents=True, exist_ok=True)
    state: Dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "last_decision_ts_ms": 0,
        "bars_tracked": 0,
        "tracks": {
            "v5_0_baseline_vt25": {"nav": 1000.0, "hwm": 1000.0, "cum_turnover": 0.0, "weights": {}},
            "v5_1_adaptive_vt25_isovol": {"nav": 1000.0, "hwm": 1000.0, "cum_turnover": 0.0, "weights": {}},
            "v5_1_production_vt35": {"nav": 1000.0, "hwm": 1000.0, "cum_turnover": 0.0, "weights": {}},
        },
        "history": [],
    }
    if shadow_path.exists():
        try:
            loaded = json.loads(shadow_path.read_text())
            if isinstance(loaded, dict) and "tracks" in loaded:
                state = loaded
        except Exception:
            pass

    if int(state.get("last_decision_ts_ms", 0)) == int(decision_ts_ms):
        return state

    n_bars, n_syms = close_mat.shape
    sym_idx = {s: i for i, s in enumerate(symbols)}

    # Settle previous bar mark-to-close return if a prior bar was recorded
    if int(state.get("last_decision_ts_ms", 0)) > 0 and n_bars >= 2:
        c_prev = close_mat[-2]
        c_curr = close_mat[-1]
        bar_rets = np.where((c_prev > 0) & (c_curr > 0), (c_curr / np.maximum(c_prev, 1e-12)) - 1.0, 0.0)
        fund_4h = np.nan_to_num(funding_rates_1h, nan=0.0) * 4.0
        for t_name, trk in state["tracks"].items():
            w_prev_map = trk.get("weights", {})
            w_vec = np.array([float(w_prev_map.get(s, 0.0)) for s in symbols], dtype=np.float64)
            gross_r = float(np.sum(w_vec * bar_rets))
            fund_r = -float(np.sum(w_vec * fund_4h))
            net_r = max(-0.95, gross_r + fund_r)
            trk["nav"] = round(float(trk.get("nav", 1000.0)) * (1.0 + net_r), 4)
            trk["hwm"] = round(max(float(trk.get("hwm", 1000.0)), trk["nav"]), 4)

    regime_info = classify_causal_market_regime(close_mat, valid_mask, btc_idx, eth_idx)

    configs = {
        "v5_0_baseline_vt25": {"v51_adaptive": False, "vt": 0.25},
        "v5_1_adaptive_vt25_isovol": {"v51_adaptive": True, "vt": 0.25},
        "v5_1_production_vt35": {"v51_adaptive": True, "vt": 0.35},
    }

    step_summary: Dict[str, Any] = {
        "decision_ts_ms": int(decision_ts_ms),
        "timestamp_utc": datetime.fromtimestamp(decision_ts_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "regime": regime_info,
        "tracks": {},
    }

    for t_name, cfg in configs.items():
        trk = state["tracks"][t_name]
        prev_map = trk.get("weights", {})
        prev_w = np.array([float(prev_map.get(s, 0.0)) for s in symbols], dtype=np.float64)
        if cfg["v51_adaptive"]:
            rw, betas, vb, iv, _, _ = compute_apex_v5_raw_unit_weights(
                close_mat=close_mat,
                valid_mask=valid_mask,
                funding_rates_1h=funding_rates_1h,
                symbols=symbols,
                btc_idx=btc_idx,
                eth_idx=eth_idx,
                vol_mat=vol_mat,
                regime_adaptive_routing=True,
                er_gate_tsmom=True,
                fast_tsmom_blend=True,
                fip_quality_weight=0.05,
                vol_accel_weight=0.05,
            )
            wf, ag, _ = scale_and_smooth_apex_v5_weights(
                raw_w=rw,
                prev_w=prev_w,
                betas=betas,
                vol_bar=vb,
                idio_vol=iv,
                btc_idx=btc_idx,
                current_equity=float(trk.get("nav", current_equity)),
                historical_hwm=float(trk.get("hwm", historical_hwm)),
                target_vol_ann=cfg["vt"],
                clean_zero_exit=True,
            )
        else:
            rw, betas, vb, iv, _, _ = compute_apex_v5_raw_unit_weights(
                close_mat=close_mat,
                valid_mask=valid_mask,
                funding_rates_1h=funding_rates_1h,
                symbols=symbols,
                btc_idx=btc_idx,
                eth_idx=eth_idx,
                vol_mat=vol_mat,
            )
            wf, ag, _ = scale_and_smooth_apex_v5_weights(
                raw_w=rw,
                prev_w=prev_w,
                betas=betas,
                vol_bar=vb,
                idio_vol=iv,
                btc_idx=btc_idx,
                current_equity=float(trk.get("nav", current_equity)),
                historical_hwm=float(trk.get("hwm", historical_hwm)),
                target_vol_ann=cfg["vt"],
            )

        to = float(np.sum(np.abs(wf - prev_w)))
        trk["nav"] = round(float(trk.get("nav", 1000.0)) * (1.0 - to * 0.00035), 4)
        trk["cum_turnover"] = round(float(trk.get("cum_turnover", 0.0)) + to, 4)
        trk["weights"] = {symbols[i]: round(float(wf[i]), 5) for i in range(n_syms) if abs(wf[i]) >= 0.002}
        step_summary["tracks"][t_name] = {
            "nav": trk["nav"],
            "gross_lev": round(ag, 3),
            "n_legs": len(trk["weights"]),
            "turnover": round(to, 4),
        }

    state["last_decision_ts_ms"] = int(decision_ts_ms)
    state["bars_tracked"] = int(state.get("bars_tracked", 0)) + 1
    state["latest_regime"] = regime_info
    hist = list(state.get("history", []))
    hist.append(step_summary)
    state["history"] = hist[-180:]  # Retain rolling 30 days of 4H shadow history

    tmp = shadow_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(shadow_path)
    return state


def compute_live_profitability_decomposition(journal_path: Path, state_path: Path) -> Dict[str, Any]:
    """
    Computes exact realized/unrealized economic PnL attribution from authoritative journal:
      Net = Gross Price PnL + Net Funding - Maker Fees - Taker Fees + Unrealized Mark Delta
    """
    maker_fees = 0.0
    taker_fees = 0.0
    maker_vol = 0.0
    taker_vol = 0.0
    delay_slip_usd = 0.0
    impact_slip_usd = 0.0
    n_maker = 0
    n_taker = 0

    if journal_path.exists():
        with open(journal_path, "r") as jf:
            for line in jf:
                s = line.strip()
                if not s:
                    continue
                try:
                    ev = json.loads(s)
                except Exception:
                    continue
                if ev.get("event_type") == "IMPLEMENTATION_AUDIT_RECORD":
                    p = ev.get("payload", {})
                    if str(p.get("mode", "")).upper() == "DRY_RUN":
                        continue
                    px = float(p.get("actual_fill_price", 0.0))
                    sz = float(p.get("filled_size", 0.0))
                    ntl = px * sz
                    fee = float(p.get("exchange_fee_usdc", 0.0))
                    otype = str(p.get("order_type", ""))
                    if "ALO" in otype or "MAKER" in otype:
                        n_maker += 1
                        maker_fees += fee
                        maker_vol += ntl
                    else:
                        n_taker += 1
                        taker_fees += fee
                        taker_vol += ntl
                    delay_slip_usd += ntl * float(p.get("delay_slippage_bps", 0.0)) * 1e-4
                    impact_slip_usd += ntl * float(p.get("execution_impact_bps", 0.0)) * 1e-4

    st = {}
    if state_path.exists():
        try:
            st = json.loads(state_path.read_text())
        except Exception:
            st = {}

    acct = st.get("accounting_ledger", {})
    eq_b = st.get("equity", {})
    realized = float(acct.get("cumulative_realized_trade_pnl", 0.0))
    funding = float(acct.get("cumulative_funding_pnl", 0.0))
    fees = float(acct.get("cumulative_exchange_fees", 0.0))
    unreal = float(acct.get("unrealized_mark_pnl", 0.0))

    return {
        "nav_usd": float(eq_b.get("current_strategy_equity", 0.0)),
        "active_leverage": float(eq_b.get("active_leverage", 0.0)),
        "realized_gross_trade_pnl_usd": round(realized, 4),
        "net_funding_pnl_usd": round(funding, 4),
        "total_exchange_fees_usd": round(fees, 4),
        "maker_fees_usd": round(maker_fees, 4),
        "taker_fees_usd": round(taker_fees, 4),
        "maker_volume_usd": round(maker_vol, 2),
        "taker_volume_usd": round(taker_vol, 2),
        "maker_fill_count": n_maker,
        "taker_fill_count": n_taker,
        "estimated_delay_slippage_usd": round(delay_slip_usd, 4),
        "estimated_exec_impact_usd": round(impact_slip_usd, 4),
        "unrealized_mark_pnl_usd": round(unreal, 4),
    }

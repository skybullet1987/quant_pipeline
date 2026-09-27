import sys
import warnings
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
from scipy.stats import spearmanr
from sklearn.covariance import LedoitWolf

from src.backtest.backtest_models import OnlineMicrostructureHMM, Position
from src.backtest.backtest_matured_ir import compute_ensemble_alpha
from src.backtest.backtest_optimizers import compute_hrp_from_cov, compute_null_space_carry
from src.signals.funding_forecaster import forecast_hourly_funding

def evaluate_controlled_experiment(
    df: pl.DataFrame, preds_12: dict, preds_48: dict, preds_168: dict, hmm_data: dict,
    cfg_name: str, deadband_thresh: float = 0.0, s2_mode: str = "0.5x",
    friction_bps: float = 0.0, max_gross_lev: float = 1.75, disaster_stop_atr: float = 3.5
) -> dict:
    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42

    capital = 1000.0
    equity_curve = [capital]
    bar_returns, delta_w_executed, closed_trade_pnls = [], [], []
    positions, matured_ic_hist = {}, {"12h": [], "48h": [], "168h": []}
    hmm = OnlineMicrostructureHMM()
    last_reb, fee_rate = 0, friction_bps / 10000.0

    tot_turnover, rebalances, prop_orders, supp_orders = 0.0, 0, 0, 0
    gross_pnl, fees_paid, s2_pnl = 0.0, 0.0, 0.0
    s2_bars_tot, s2_bars_inv, worst_4h = 0, 0, 0.0

    target_map = {"12h": ("target_12h_alpha", 3), "48h": ("target_48h_drift", 12), "168h": ("target_168h_trend", 42)}

    for grp in range(start_eval_grp, total_grps - 1):
        if grp not in preds_12: continue
        c_pan, n_pan = df.filter(pl.col("group_id") == grp), df.filter(pl.col("group_id") == grp + 1)
        if c_pan.height == 0 or n_pan.height == 0: continue

        c_rows = {r["symbol"]: r for r in c_pan.iter_rows(named=True)}
        n_rows = {r["symbol"]: r for r in n_pan.iter_rows(named=True)}
        symbols = list(c_rows.keys())

        if grp in hmm_data: hmm.fit_from_training_observations(hmm_data[grp])
        b_row = c_pan.filter(pl.col("symbol") == "BTC")
        b_vol = float(b_row.select("vol_yang_zhang").to_series()[0]) if len(b_row) > 0 else 0.03
        obs = np.array([b_vol, float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0]), 0.002])
        _, hmm_lev, dom_state = hmm.filter_step(obs)

        for h_name, (t_col, dly) in target_map.items():
            mg = grp - dly
            if mg in preds_12:
                old_p = preds_12[mg] if h_name == "12h" else (preds_48[mg] if h_name == "48h" else preds_168[mg])
                p_tgts = {r["symbol"]: r.get(t_col) for r in df.filter(pl.col("group_id") == mg).to_dicts() if r.get(t_col) is not None}
                cmn = [s for s in old_p if s in p_tgts]
                if len(cmn) >= 20:
                    ic, _ = spearmanr([old_p[s] for s in cmn], [p_tgts[s] for s in cmn])
                    if not np.isnan(ic): matured_ic_hist[h_name].append(ic)

        p12_a = np.array([preds_12[grp][s] for s in symbols])
        p48_a = np.array([preds_48[grp][s] for s in symbols])
        p168_a = np.array([preds_168[grp][s] for s in symbols])
        alpha_v = compute_ensemble_alpha(p12_a, p48_a, p168_a, matured_ic_hist, use_dynamic_ir=True)
        alpha_dict = {s: v for s, v in zip(symbols, alpha_v)}

        bar_gross, bar_fees, stopped = 0.0, 0.0, []
        for sym, pos in list(positions.items()):
            if sym not in n_rows or sym not in c_rows: continue
            pc, nhi, nlo, ncl = c_rows[sym]["close"], n_rows[sym]["high"], n_rows[sym]["low"], n_rows[sym]["close"]
            sl = pos.entry_px - (disaster_stop_atr * pos.atr) if pos.is_long else pos.entry_px + (disaster_stop_atr * pos.atr)

            if (pos.is_long and nlo <= sl) or (not pos.is_long and nhi >= sl):
                epx = min(pc, sl) if pos.is_long else max(pc, sl)
                raw_pnl = (epx - pc) / pc if pos.is_long else (pc - epx) / pc
                fee = capital * abs(pos.weight) * max(0.00045, fee_rate)
                bar_gross += capital * abs(pos.weight) * raw_pnl
                bar_fees += fee
                closed_trade_pnls.append((epx - pos.entry_px)/pos.entry_px if pos.is_long else (pos.entry_px - epx)/pos.entry_px)
                stopped.append(sym)
            else:
                raw_pnl = (ncl - pc) / pc if pos.is_long else (pc - ncl) / pc
                bar_gross += capital * abs(pos.weight) * raw_pnl

        for s in stopped: del positions[s]

        if s2_mode == "0x" and dom_state == 2 and len(positions) > 0:
            to_s2 = sum(abs(p.weight) for p in positions.values())
            f_s2 = to_s2 * fee_rate * capital
            bar_fees += f_s2; fees_paid += f_s2; tot_turnover += to_s2 * capital
            for s, pos in positions.items():
                p_now = c_rows[s]["close"]
                closed_trade_pnls.append((p_now - pos.entry_px)/pos.entry_px if pos.is_long else (pos.entry_px - p_now)/pos.entry_px)
            positions.clear()

        if dom_state == 2:
            s2_bars_tot += 1
            if len(positions) > 0: s2_bars_inv += 1

        if (grp - last_reb) >= 6 or last_reb == 0:
            last_reb = grp
            rebalances += 1
            if s2_mode == "0x" and dom_state == 2:
                tgt_w = {}
            else:
                hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
                piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
                v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]
                if len(v_cols) >= 15:
                    shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
                    a_sub = np.array([alpha_dict[s] for s in v_cols])
                    b_sub = np.array([c_rows[s]["beta_btc"] for s in v_cols])
                    m_yz = float(c_pan.select(pl.mean("vol_yang_zhang")).to_series()[0])
                    v_scale = float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.60))
                    t_lev = float(np.clip(hmm_lev * (max_gross_lev / 1.50) * v_scale, 0.50, max_gross_lev))

                    w_mom = compute_hrp_from_cov(shrunk_cov, a_sub, t_lev, top_k=5)
                    if dom_state == 0: w_mom[w_mom < 0] *= 0.35
                    carry_y = np.array([forecast_hourly_funding(float(c_rows[s]["basis_spread"]), float(c_rows[s]["volume_zscore_72h"]), float(c_rows[s]["ret_4h"]), float(c_rows[s]["basis_spread"]))[1] for s in v_cols])
                    w_car = compute_null_space_carry(shrunk_cov, carry_y, a_sub, b_sub, target_carry_leverage=0.40)
                    w_comb = w_mom + w_car
                    g_exp = np.sum(np.abs(w_comb))
                    if g_exp > max_gross_lev: w_comb *= (max_gross_lev / g_exp)
                    w_comb = np.clip(w_comb, -0.30, 0.30)
                    tgt_w = {v_cols[i]: float(w_comb[i]) for i in range(len(v_cols)) if abs(w_comb[i]) > 0.005}
                else: tgt_w = {}

            all_s = set(list(tgt_w.keys()) + list(positions.keys()))
            exec_w = {}
            for s in all_s:
                wt, wc = tgt_w.get(s, 0.0), positions[s].weight if s in positions else 0.0
                dw = wt - wc
                if abs(dw) > 0.005:
                    prop_orders += 1
                    if abs(dw) < deadband_thresh:
                        supp_orders += 1
                        we = wc
                    else:
                        we = wt
                        delta_w_executed.append(abs(dw))
                else: we = wc
                if abs(we) > 0.005: exec_w[s] = we

            turnover = 0.0
            for s in all_s:
                we, wc = exec_w.get(s, 0.0), positions[s].weight if s in positions else 0.0
                turnover += abs(we - wc)
                if abs(we) < 0.005 and s in positions:
                    pos = positions[s]
                    pn = c_rows[s]["close"]
                    closed_trade_pnls.append((pn - pos.entry_px)/pos.entry_px if pos.is_long else (pos.entry_px - pn)/pos.entry_px)
                    del positions[s]
                elif abs(we) >= 0.005 and (s not in positions or (we * wc < 0)):
                    rc = c_rows.get(s)
                    if rc:
                        px, atr = rc["close"], rc["atr_14"]
                        isl = we > 0
                        sl = px - (disaster_stop_atr * atr) if isl else px + (disaster_stop_atr * atr)
                        positions[s] = Position(s, isl, we, px, atr, sl, px, px, "INITIAL", grp)
                elif s in positions: positions[s].weight = we

            f_reb = turnover * fee_rate * capital
            bar_fees += f_reb; fees_paid += f_reb; tot_turnover += turnover * capital

        d_pnl = bar_gross - bar_fees
        gross_pnl += bar_gross
        if dom_state == 2: s2_pnl += d_pnl
        ret_4h = d_pnl / equity_curve[-1]
        capital += d_pnl
        equity_curve.append(capital)
        bar_returns.append(ret_4h)
        worst_4h = min(worst_4h, ret_4h)

    r_arr = np.array(bar_returns)
    eq_arr = np.array(equity_curve)
    days = (len(r_arr) * 4.0) / 24.0
    cagr = float(((capital / 1000.0) ** (365.25 / days) - 1.0) * 100.0) if days > 0 else 0.0
    sharpe = float((np.mean(r_arr) / (np.std(r_arr) + 1e-8)) * np.sqrt(2190))
    neg_r = r_arr[r_arr < 0]
    sortino = float((np.mean(r_arr) / (np.std(neg_r) + 1e-8)) * np.sqrt(2190)) if len(neg_r) > 0 else sharpe
    mdd = float(np.min((eq_arr - np.maximum.accumulate(eq_arr)) / np.maximum.accumulate(eq_arr)) * 100.0)
    pf = float(abs(np.sum(r_arr[r_arr > 0])) / (abs(np.sum(r_arr[r_arr < 0])) + 1e-8))

    return {
        "config": cfg_name, "deadband": deadband_thresh, "s2_mode": s2_mode, "friction_bps": friction_bps,
        "turnover_usd": tot_turnover, "turnover_mult": tot_turnover / 1000.0, "rebalances": rebalances,
        "suppressed_pct": (supp_orders / prop_orders * 100.0) if prop_orders > 0 else 0.0,
        "avg_delta_w": float(np.mean(delta_w_executed)) if len(delta_w_executed) > 0 else 0.0,
        "gross_pnl": gross_pnl, "fees_paid": fees_paid, "net_pnl": capital - 1000.0, "ending_cap": capital,
        "cagr": cagr, "sharpe": sharpe, "sortino": sortino, "mdd": mdd, "calmar": abs(cagr/mdd) if mdd != 0 else 0.0,
        "pf": pf, "s2_pnl": s2_pnl, "s2_time_pct": (s2_bars_inv / s2_bars_tot * 100.0) if s2_bars_tot > 0 else 0.0,
        "worst_4h": worst_4h * 100.0, "worst_trade": (min(closed_trade_pnls) * 100.0) if len(closed_trade_pnls) > 0 else 0.0,
        "returns": r_arr
    }

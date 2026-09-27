import sys
import warnings
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
import pandas as pd
from scipy.stats import spearmanr
from sklearn.covariance import LedoitWolf

from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.backtest_models import OnlineMicrostructureHMM, Position
from src.backtest.backtest_matured_ir import compute_ensemble_alpha
from src.backtest.backtest_optimizers import compute_hrp_from_cov, compute_null_space_carry
from src.backtest.run_fast_institutional_matrix import precompute_rolling_predictions
from src.signals.funding_forecaster import forecast_hourly_funding

MMR_MAP = {"BTC": 0.02, "ETH": 0.02, "SOL": 0.05, "AVAX": 0.05, "NEAR": 0.05, "SUI": 0.05}
DEFAULT_MMR = 0.10

def evaluate_frontier_v2(
    df: pl.DataFrame, preds_12: dict, preds_48: dict, preds_168: dict, hmm_data: dict,
    forced_s0_gross: float, friction_bps: float = 2.0, disaster_stop_atr: float = 3.5,
    deadband: float = 0.050, n_boot: int = 1000
) -> dict:
    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42

    capital = 1000.0
    equity_curve = [capital]
    bar_returns, gross_all, gross_s0 = [], [], []
    positions, matured_ic_hist = {}, {"12h": [], "48h": [], "168h": []}
    hmm = OnlineMicrostructureHMM()
    last_reb, fee_rate = 0, friction_bps / 10000.0
    worst_4h = 0.0
    is_liquidated = False
    liquidation_bar = None
    min_margin_buffer = 999.0  # (Equity / Notional) - MMR

    target_map = {"12h": ("target_12h_alpha", 3), "48h": ("target_48h_drift", 12), "168h": ("target_168h_trend", 42)}

    eval_bars = 0
    for grp in range(start_eval_grp, total_grps - 1):
        eval_bars += 1
        if is_liquidated:
            equity_curve.append(0.0)
            bar_returns.append(0.0)
            gross_all.append(0.0)
            continue

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
        _, _, dom_state = hmm.filter_step(obs)

        # Dynamic IC
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

        # 1. Intrabar Stops & Adverse Margin Verification
        bar_gross, bar_fees, stopped = 0.0, 0.0, []
        worst_intrabar_loss = 0.0
        tot_notional = 0.0
        weighted_mmr_sum = 0.0

        for sym, pos in list(positions.items()):
            if sym not in n_rows or sym not in c_rows: continue
            pc, nhi, nlo, ncl = c_rows[sym]["close"], n_rows[sym]["high"], n_rows[sym]["low"], n_rows[sym]["close"]
            sl = pos.entry_px - (disaster_stop_atr * pos.atr) if pos.is_long else pos.entry_px + (disaster_stop_atr * pos.atr)
            pos_notional = abs(pos.weight) * capital
            tot_notional += pos_notional
            mmr = MMR_MAP.get(sym, DEFAULT_MMR)
            weighted_mmr_sum += pos_notional * mmr

            if pos.is_long:
                adverse_px = nlo
                if adverse_px <= sl:
                    epx = min(pc, sl)
                    worst_intrabar_loss += pos_notional * ((epx - pc) / pc)
                    stopped.append(sym)
                else:
                    worst_intrabar_loss += pos_notional * ((adverse_px - pc) / pc)
                raw_pnl = (min(pc, sl) - pc) / pc if nlo <= sl else (ncl - pc) / pc
            else:
                adverse_px = nhi
                if adverse_px >= sl:
                    epx = max(pc, sl)
                    worst_intrabar_loss += pos_notional * ((pc - epx) / pc)
                    stopped.append(sym)
                else:
                    worst_intrabar_loss += pos_notional * ((pc - adverse_px) / pc)
                raw_pnl = (pc - max(pc, sl)) / pc if nhi >= sl else (pc - ncl) / pc

            bar_gross += pos_notional * raw_pnl
            if sym in stopped:
                bar_fees += pos_notional * max(0.00045, fee_rate)

        for s in stopped: del positions[s]

        # Margin Buffer Tracking
        if tot_notional > 0:
            port_mmr = weighted_mmr_sum / tot_notional
            intrabar_equity = capital + worst_intrabar_loss
            margin_ratio = intrabar_equity / tot_notional
            buf = margin_ratio - port_mmr
            min_margin_buffer = min(min_margin_buffer, buf)

            if intrabar_equity <= weighted_mmr_sum:
                is_liquidated = True
                liquidation_bar = eval_bars
                capital = 0.0
                equity_curve.append(0.0)
                bar_returns.append(-1.0)
                gross_all.append(0.0)
                continue

        # 2. S2 Cash Choke
        if dom_state == 2 and len(positions) > 0:
            to_s2 = sum(abs(p.weight) for p in positions.values())
            bar_fees += to_s2 * fee_rate * capital
            positions.clear()

        # 3. 24H Rebalance Cycle
        if (grp - last_reb) >= 6 or last_reb == 0:
            last_reb = grp
            if dom_state == 2:
                tgt_w = {}
            else:
                hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
                piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
                v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]
                if len(v_cols) >= 15:
                    shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
                    a_sub = np.array([alpha_dict[s] for s in v_cols])
                    b_sub = np.array([c_rows[s]["beta_btc"] for s in v_cols])

                    target_gross = forced_s0_gross if dom_state == 0 else 1.25
                    w_mom = compute_hrp_from_cov(shrunk_cov, a_sub, target_gross, top_k=5)
                    if dom_state == 0:
                        w_mom[w_mom < 0] *= 0.35

                    carry_y = np.array([forecast_hourly_funding(float(c_rows[s]["basis_spread"]), float(c_rows[s]["volume_zscore_72h"]), float(c_rows[s]["ret_4h"]), float(c_rows[s]["basis_spread"]))[1] for s in v_cols])
                    w_car = compute_null_space_carry(shrunk_cov, carry_y, a_sub, b_sub, target_carry_leverage=0.20)
                    w_comb = w_mom + w_car

                    curr_g = np.sum(np.abs(w_comb))
                    if curr_g > 1e-4:
                        w_comb = w_comb * (target_gross / curr_g)

                    tgt_w = {v_cols[i]: float(w_comb[i]) for i in range(len(v_cols)) if abs(w_comb[i]) > 0.005}
                else: tgt_w = {}

            all_s = set(list(tgt_w.keys()) + list(positions.keys()))
            exec_w = {}
            for s in all_s:
                wt, wc = tgt_w.get(s, 0.0), positions[s].weight if s in positions else 0.0
                dw = wt - wc
                if abs(dw) > 0.005:
                    we = wc if abs(dw) < deadband else wt
                else: we = wc
                if abs(we) > 0.005: exec_w[s] = we

            turnover = 0.0
            for s in all_s:
                we, wc = exec_w.get(s, 0.0), positions[s].weight if s in positions else 0.0
                turnover += abs(we - wc)
                if abs(we) < 0.005 and s in positions:
                    del positions[s]
                elif abs(we) >= 0.005 and (s not in positions or (we * wc < 0)):
                    rc = c_rows.get(s)
                    if rc:
                        px, atr = rc["close"], rc["atr_14"]
                        isl = we > 0
                        sl = px - (disaster_stop_atr * atr) if isl else px + (disaster_stop_atr * atr)
                        positions[s] = Position(s, isl, we, px, atr, sl, px, px, "INITIAL", grp)
                elif s in positions: positions[s].weight = we

            bar_fees += turnover * fee_rate * capital

        d_pnl = bar_gross - bar_fees
        ret_4h = d_pnl / equity_curve[-1] if equity_curve[-1] > 0 else 0.0
        capital += d_pnl
        equity_curve.append(capital)
        bar_returns.append(ret_4h)

        current_g = sum(abs(p.weight) for p in positions.values())
        gross_all.append(current_g)
        if dom_state == 0:
            gross_s0.append(current_g)
        worst_4h = min(worst_4h, ret_4h)

    r_arr = np.array(bar_returns)
    eq_arr = np.array(equity_curve)
    days = (len(r_arr) * 4.0) / 24.0

    if is_liquidated or capital <= 10.0:
        return {
            "Forced S0": f"{forced_s0_gross:.2f}x", "E[G|S0]": f"{np.mean(gross_s0):.2f}x" if len(gross_s0)>0 else "N/A",
            "E[G]": f"{np.mean(gross_all):.2f}x", "Ending $": "$0", "Actual Ret": "-100.0%", "CAGR": "-100.0%",
            "Sharpe": "0.00", "Max DD": "-100.0%", "Worst 4H": "-100.0%",
            "Min Buf": f"{min_margin_buffer*100:.1f}%", "Liq Bar": f"Bar {liquidation_bar}/{eval_bars}",
            "Boot Med": "-100.0%", "P(DD>30%)": "100.0%", "P(DD>40%)": "100.0%", "P(Ruin)": "100.0%",
            "Status": "LIQUIDATED"
        }

    actual_ret = ((capital - 1000.0) / 1000.0) * 100.0
    cagr = float(((capital / 1000.0) ** (365.25 / days) - 1.0) * 100.0) if days > 0 else 0.0
    sharpe = float((np.mean(r_arr) / (np.std(r_arr) + 1e-8)) * np.sqrt(2190))
    mdd = float(np.min((eq_arr - np.maximum.accumulate(eq_arr)) / np.maximum.accumulate(eq_arr)) * 100.0)
    calmar = abs(cagr / mdd) if mdd != 0 else 0.0

    # Block Bootstrap
    N, block_len = len(r_arr), 12
    n_blocks = N // block_len
    boot_cagrs, boot_mdds = [], []
    np.random.seed(42)

    for _ in range(n_boot):
        start_idx = np.random.randint(0, N, size=n_blocks)
        sampled = []
        for idx in start_idx:
            sampled.extend([r_arr[(idx + k) % N] for k in range(block_len)])
        s_arr = np.array(sampled[:N])
        cum_eq = np.cumprod(1.0 + s_arr)
        end_eq = cum_eq[-1]
        b_cagr = float(((end_eq) ** (365.25 / days) - 1.0) * 100.0) if end_eq > 0 else -100.0
        b_mdd = float(np.min((cum_eq - np.maximum.accumulate(cum_eq)) / np.maximum.accumulate(cum_eq)) * 100.0)
        boot_cagrs.append(b_cagr); boot_mdds.append(b_mdd)

    b_cagrs, b_mdds = np.array(boot_cagrs), np.array(boot_mdds)

    return {
        "Forced S0": f"{forced_s0_gross:.2f}x", "E[G|S0]": f"{np.mean(gross_s0):.2f}x",
        "E[G]": f"{np.mean(gross_all):.2f}x", "Ending $": f"${capital:,.0f}",
        "Actual Ret": f"{actual_ret:>+6.1f}%", "CAGR": f"{cagr:>+6.1f}%",
        "Sharpe": f"{sharpe:.2f}", "Max DD": f"{mdd:>5.1f}%", "Worst 4H": f"{worst_4h*100:>5.2f}%",
        "Min Buf": f"{min_margin_buffer*100:>4.1f}%", "Liq Bar": "None",
        "Boot Med": f"{np.percentile(b_cagrs, 50):>+6.1f}%",
        "P(DD>30%)": f"{(np.sum(b_mdds < -30.0)/n_boot)*100:.1f}%",
        "P(DD>40%)": f"{(np.sum(b_mdds < -40.0)/n_boot)*100:.1f}%",
        "P(Ruin)": f"{(np.sum(b_cagrs <= -90.0)/n_boot)*100:.1f}%",
        "Status": "SURVIVED"
    }

def main():
    print("=" * 125)
    print("       LEVERAGE FRONTIER V2: LIQUIDATION CLIFF & PRODUCTION MULTI-FRICTION MATRIX       ")
    print("=" * 125)
    df, _, _ = load_and_prepare_panel()
    p12, p48, p168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    # TRACK 1: FINE-GRAINED CLIFF SWEEP (6.0x -> 8.0x @ +2 BPS)
    print("\n" + "-" * 125)
    print(" [TRACK 1] LIQUIDATION CLIFF PINPOINT SWEEP (6.00x -> 8.00x in 0.25x Steps @ +2 bps)")
    print("-" * 125)
    cliff_grid = [6.00, 6.25, 6.50, 6.75, 7.00, 7.25, 7.50, 7.75, 8.00]
    t1_rows = []
    for lev in cliff_grid:
        r = evaluate_frontier_v2(df, p12, p48, p168, hmm_data, forced_s0_gross=lev, friction_bps=2.0)
        t1_rows.append(r)
        print(f" • S0 {lev:.2f}x (E[G|S0]: {r['E[G|S0]']}): Ending {r['Ending $']} | MaxDD {r['Max DD']} | MinBuf {r['Min Buf']} [{r['Status']}]")

    print("\n" + pd.DataFrame(t1_rows).to_string(index=False))

    # TRACK 2: CANDIDATE PRODUCTION MATRIX UNDER MULTI-TIER FRICTION
    print("\n" + "-" * 125)
    print(" [TRACK 2] PRODUCTION CANDIDATE MULTI-FRICTION MATRIX (Candidate Tiers x [2, 5, 10, 15] bps)")
    print("-" * 125)
    candidate_levs = [1.75, 2.00, 2.50, 3.00, 4.00]
    frictions = [2.0, 5.0, 10.0, 15.0]
    t2_rows = []

    for f in frictions:
        for lev in candidate_levs:
            r = evaluate_frontier_v2(df, p12, p48, p168, hmm_data, forced_s0_gross=lev, friction_bps=f)
            t2_rows.append({
                "Friction": f"{f:>4.0f} bps", "S0 Target": f"{lev:.2f}x", "E[G|S0]": r["E[G|S0]"],
                "Ending $": r["Ending $"], "Actual Ret": r["Actual Ret"], "CAGR": r["CAGR"],
                "Sharpe": r["Sharpe"], "Max DD": r["Max DD"], "Min Buf": r["Min Buf"],
                "P(DD>30%)": r["P(DD>30%)"], "P(DD>40%)": r["P(DD>40%)"], "P(Ruin)": r["P(Ruin)"]
            })

    print("\n" + pd.DataFrame(t2_rows).to_string(index=False))
    print("=" * 125 + "\n")

if __name__ == "__main__":
    main()

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
from src.backtest.backtest_positions import evaluate_intrabar_stops, sync_positions
from src.backtest.backtest_optimizers import compute_hrp_from_cov, compute_null_space_carry
from src.backtest.run_fast_institutional_matrix import precompute_rolling_predictions
from src.signals.funding_forecaster import forecast_hourly_funding

def run_a0_simulation(
    df: pl.DataFrame,
    preds_12: dict,
    preds_48: dict,
    preds_168: dict,
    hmm_data: dict,
    max_gross_lev: float = 1.75,
    friction_bps: float = 15.0,  # Total roundtrip fee + slippage (bps)
    s0_short_mult: float = 0.35,
    carry_lev: float = 0.40
) -> dict:
    total_grps = df.select("group_id").max().to_series()[0]
    start_eval_grp = int(total_grps * 0.60) + 42

    capital = 1000.0
    equity_curve = [capital]
    bar_returns = []
    positions = {}
    hmm = OnlineMicrostructureHMM()
    last_reb = 0
    matured_ic_hist = {"12h": [], "48h": [], "168h": []}
    target_map = {"12h": ("target_12h_alpha", 3), "48h": ("target_48h_drift", 12), "168h": ("target_168h_trend", 42)}

    # Telemetry logging
    bar_regimes = []
    btc_regimes = []
    gross_exposures = []
    worst_4h_loss = 0.0

    fee_factor = (friction_bps / 10000.0)

    for grp in range(start_eval_grp, total_grps - 1):
        if grp not in preds_12: continue
        c_pan = df.filter(pl.col("group_id") == grp)
        n_pan = df.filter(pl.col("group_id") == grp + 1)
        if c_pan.height == 0 or n_pan.height == 0: continue

        c_rows = {r["symbol"]: r for r in c_pan.iter_rows(named=True)}
        n_rows = {r["symbol"]: r for r in n_pan.iter_rows(named=True)}
        symbols = list(c_rows.keys())

        if grp in hmm_data:
            hmm.fit_from_training_observations(hmm_data[grp])

        b_row = c_pan.filter(pl.col("symbol") == "BTC")
        b_vol = float(b_row.select("vol_yang_zhang").to_series()[0]) if len(b_row) > 0 else 0.03
        b_ret168 = float(b_row.select("ret_168h").to_series()[0]) if len(b_row) > 0 else 0.0
        obs = np.array([b_vol, float(c_pan.select(pl.mean("volume_zscore_72h")).to_series()[0]), 0.002])
        _, hmm_lev, dom_state = hmm.filter_step(obs)

        # BTC Trend Classification for Track 3
        if b_ret168 > 0.04: btc_state = "BULL"
        elif b_ret168 < -0.04: btc_state = "BEAR"
        else: btc_state = "CHOP"

        # Matured IC Updates
        for h_name, (t_col, delay) in target_map.items():
            mat_grp = grp - delay
            if mat_grp in preds_12:
                old_p = preds_12[mat_grp] if h_name == "12h" else (preds_48[mat_grp] if h_name == "48h" else preds_168[mat_grp])
                past_panel = df.filter(pl.col("group_id") == mat_grp).to_dicts()
                past_targets = {r["symbol"]: r.get(t_col) for r in past_panel if r.get(t_col) is not None}
                common = [s for s in old_p if s in past_targets]
                if len(common) >= 20:
                    ic, _ = spearmanr([old_p[s] for s in common], [past_targets[s] for s in common])
                    if not np.isnan(ic): matured_ic_hist[h_name].append(ic)

        p12_arr = np.array([preds_12[grp][s] for s in symbols])
        p48_arr = np.array([preds_48[grp][s] for s in symbols])
        p168_arr = np.array([preds_168[grp][s] for s in symbols])
        alpha_vec = compute_ensemble_alpha(p12_arr, p48_arr, p168_arr, matured_ic_hist, use_dynamic_ir=True)
        alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

        # Intrabar stops (Mark-to-Market including wicks)
        bar_pnl, stopped = evaluate_intrabar_stops(positions, c_rows, n_rows, capital, use_ratchet=False, disaster_stop_atr=3.5)
        for s in stopped: del positions[s]

        # 24H Rebalance (Every 6 bars)
        rebal_fee = 0.0
        if (grp - last_reb) >= 6 or last_reb == 0:
            last_reb = grp
            hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
            piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
            v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]

            if len(v_cols) >= 15:
                shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
                a_sub = np.array([alpha_dict[s] for s in v_cols])
                b_sub = np.array([c_rows[s]["beta_btc"] for s in v_cols])
                m_yz = float(c_pan.select(pl.mean("vol_yang_zhang")).to_series()[0])

                vol_scaler = float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.60))
                target_lev = float(np.clip(hmm_lev * (max_gross_lev / 1.50) * vol_scaler, 0.50, max_gross_lev))

                w_mom = compute_hrp_from_cov(shrunk_cov, a_sub, target_lev, top_k=5)
                if dom_state == 0:
                    w_mom[w_mom < 0] *= s0_short_mult

                carry_y = np.array([forecast_hourly_funding(float(c_rows[s]["basis_spread"]), float(c_rows[s]["volume_zscore_72h"]), float(c_rows[s]["ret_4h"]), float(c_rows[s]["basis_spread"]))[1] for s in v_cols])
                w_car = compute_null_space_carry(shrunk_cov, carry_y, a_sub, b_sub, target_carry_leverage=carry_lev)

                w_comb = w_mom + w_car
                g_exp = np.sum(np.abs(w_comb))
                if g_exp > max_gross_lev:
                    w_comb *= (max_gross_lev / g_exp)
                w_comb = np.clip(w_comb, -0.30, 0.30)

                tgt = {v_cols[i]: float(w_comb[i]) for i in range(len(v_cols)) if abs(w_comb[i]) > 0.005}
                turnover = sync_positions(tgt, positions, c_rows, grp, disaster_stop_atr=3.5)
                rebal_fee = turnover * fee_factor * capital

        d_pnl = bar_pnl - rebal_fee
        ret_4h = d_pnl / equity_curve[-1]
        capital += d_pnl
        equity_curve.append(capital)
        bar_returns.append(ret_4h)
        bar_regimes.append(dom_state)
        btc_regimes.append(btc_state)
        gross_exposures.append(sum(abs(p.weight) for p in positions.values()))
        worst_4h_loss = min(worst_4h_loss, ret_4h)

    r_arr = np.array(bar_returns)
    eq_arr = np.array(equity_curve)
    days = (len(r_arr) * 4.0) / 24.0
    cagr = float(((capital / 1000.0) ** (365.25 / days) - 1.0) * 100.0) if days > 0 else 0.0
    sharpe = float((np.mean(r_arr) / (np.std(r_arr) + 1e-8)) * np.sqrt(2190))
    neg_rets = r_arr[r_arr < 0]
    sortino = float((np.mean(r_arr) / (np.std(neg_rets) + 1e-8)) * np.sqrt(2190)) if len(neg_rets) > 0 else sharpe
    mdd = float(np.min((eq_arr - np.maximum.accumulate(eq_arr)) / np.maximum.accumulate(eq_arr)) * 100.0)
    pf = float(abs(np.sum(r_arr[r_arr > 0])) / (abs(np.sum(r_arr[r_arr < 0])) + 1e-8))

    return {
        "cagr": cagr, "sharpe": sharpe, "sortino": sortino, "mdd": mdd,
        "calmar": abs(cagr / mdd) if mdd != 0 else 0.0, "pf": pf,
        "end_capital": capital, "returns": r_arr, "bar_regimes": np.array(bar_regimes),
        "btc_regimes": np.array(btc_regimes), "worst_4h": worst_4h_loss * 100.0,
        "avg_gross": float(np.mean(gross_exposures)), "days": days
    }

def run_stress_suite():
    print("=" * 95)
    print("      A0 EMPIRICAL DOMINANCE VALIDATION & STRESS-TEST SUITE (4 TRACKS)       ")
    print("=" * 95)
    df, unique_ts, grp_to_ts = load_and_prepare_panel()
    p12, p48, p168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    # -------------------------------------------------------------
    # TRACK 1: LEVERAGE LADDER
    # -------------------------------------------------------------
    print("\n" + "-" * 95)
    print(" [TRACK 1] LEVERAGE LADDER SWEEP (1.75x -> 3.00x Gross Ceiling)")
    print("-" * 95)
    lev_levels = [1.75, 2.00, 2.25, 2.50, 2.75, 3.00]
    track1_rows = []
    base_res = None

    for lev in lev_levels:
        res = run_a0_simulation(df, p12, p48, p168, hmm_data, max_gross_lev=lev, friction_bps=15.0)
        if lev == 1.75: base_res = res
        track1_rows.append({
            "Gross Ceiling": f"{lev:.2f}x",
            "Avg Realized": f"{res['avg_gross']:.2f}x",
            "CAGR": f"{res['cagr']:>+6.1f}%",
            "Sharpe": f"{res['sharpe']:.2f}",
            "Sortino": f"{res['sortino']:.2f}",
            "Max DD": f"{res['mdd']:>5.1f}%",
            "Calmar": f"{res['calmar']:.2f}",
            "Worst 4H": f"{res['worst_4h']:>5.2f}%",
            "Ending $": f"${res['end_capital']:,.0f}"
        })
    print(pd.DataFrame(track1_rows).to_string(index=False))

    # -------------------------------------------------------------
    # TRACK 2: FRICTION SENSITIVITY STRESS
    # -------------------------------------------------------------
    print("\n" + "-" * 95)
    print(" [TRACK 2] EXECUTION FRICTION STRESS (15 bps -> 100 bps Roundtrip Slippage & Fees)")
    print("-" * 95)
    frictions = [15.0, 25.0, 35.0, 50.0, 75.0, 100.0]
    track2_rows = []
    for f in frictions:
        res = run_a0_simulation(df, p12, p48, p168, hmm_data, max_gross_lev=1.75, friction_bps=f)
        track2_rows.append({
            "Roundtrip Friction": f"{f:>4.0f} bps",
            "CAGR": f"{res['cagr']:>+6.1f}%",
            "Sharpe": f"{res['sharpe']:.2f}",
            "Max DD": f"{res['mdd']:>5.1f}%",
            "Calmar": f"{res['calmar']:.2f}",
            "Profit Factor": f"{res['pf']:.2f}",
            "Ending $": f"${res['end_capital']:,.0f}"
        })
    print(pd.DataFrame(track2_rows).to_string(index=False))

    # -------------------------------------------------------------
    # TRACK 3: REGIME DECOMPOSITION (A0 at 1.75x)
    # -------------------------------------------------------------
    print("\n" + "-" * 95)
    print(" [TRACK 3] REGIME PERFORMANCE ATTRIBUTION (A0 Baseline 1.75x)")
    print("-" * 95)
    r_arr = base_res["returns"]
    b_regs = base_res["btc_regimes"]
    h_regs = base_res["bar_regimes"]

    track3_rows = []
    # BTC Macro Regimes
    for r_type in ["BULL", "CHOP", "BEAR"]:
        mask = (b_regs == r_type)
        sub_r = r_arr[mask]
        if len(sub_r) > 10:
            sh = float((np.mean(sub_r) / (np.std(sub_r) + 1e-8)) * np.sqrt(2190))
            cum = float((np.prod(1.0 + sub_r) - 1.0) * 100.0)
            track3_rows.append({
                "Regime Category": f"BTC {r_type}",
                "4H Bars": len(sub_r),
                "Period PnL": f"{cum:>+6.1f}%",
                "Sub-Sharpe": f"{sh:>5.2f}",
                "Win Rate": f"{(np.sum(sub_r > 0)/len(sub_r))*100:.1f}%"
            })
    # HMM Internal Regimes
    for s_id, name in [(0, "S0 (Bull Expansion)"), (1, "S1 (Chop / Reversal)"), (2, "S2 (Crisis Vol)")]:
        mask = (h_regs == s_id)
        sub_r = r_arr[mask]
        if len(sub_r) > 10:
            sh = float((np.mean(sub_r) / (np.std(sub_r) + 1e-8)) * np.sqrt(2190))
            cum = float((np.prod(1.0 + sub_r) - 1.0) * 100.0)
            track3_rows.append({
                "Regime Category": f"HMM {name}",
                "4H Bars": len(sub_r),
                "Period PnL": f"{cum:>+6.1f}%",
                "Sub-Sharpe": f"{sh:>5.2f}",
                "Win Rate": f"{(np.sum(sub_r > 0)/len(sub_r))*100:.1f}%"
            })
    print(pd.DataFrame(track3_rows).to_string(index=False))

    # -------------------------------------------------------------
    # TRACK 4: CIRCULAR BLOCK BOOTSTRAP RESAMPLING
    # -------------------------------------------------------------
    print("\n" + "-" * 95)
    print(" [TRACK 4] CIRCULAR BLOCK BOOTSTRAP (2,000 Resamples | Block Size = 12 Bars / 48H)")
    print("-" * 95)
    N = len(r_arr)
    block_len = 12
    n_blocks = N // block_len
    n_boot = 2000

    boot_cagrs = []
    boot_sharpes = []
    boot_mdds = []

    np.random.seed(42)
    for _ in range(n_boot):
        start_indices = np.random.randint(0, N, size=n_blocks)
        sampled_rets = []
        for idx in start_indices:
            block = [r_arr[(idx + k) % N] for k in range(block_len)]
            sampled_rets.extend(block)

        s_arr = np.array(sampled_rets[:N])
        cum_eq = np.cumprod(1.0 + s_arr)
        end_eq = cum_eq[-1]

        days = (N * 4.0) / 24.0
        b_cagr = float(((end_eq) ** (365.25 / days) - 1.0) * 100.0) if end_eq > 0 else -100.0
        b_sh = float((np.mean(s_arr) / (np.std(s_arr) + 1e-8)) * np.sqrt(2190))
        b_mdd = float(np.min((cum_eq - np.maximum.accumulate(cum_eq)) / np.maximum.accumulate(cum_eq)) * 100.0)

        boot_cagrs.append(b_cagr)
        boot_sharpes.append(b_sh)
        boot_mdds.append(b_mdd)

    b_cagrs = np.array(boot_cagrs)
    b_sharpes = np.array(boot_sharpes)
    b_mdds = np.array(boot_mdds)

    print(f" • Median Annualized CAGR  : {np.percentile(b_cagrs, 50):>+6.1f}%  (5th%: {np.percentile(b_cagrs, 5):>+6.1f}% | 95th%: {np.percentile(b_cagrs, 95):>+6.1f}%)")
    print(f" • Median Sharpe Ratio     : {np.percentile(b_sharpes, 50):.2f}    (5th%: {np.percentile(b_sharpes, 5):.2f}    | 95th%: {np.percentile(b_sharpes, 95):.2f})")
    print(f" • Median Max Drawdown     : {np.percentile(b_mdds, 50):>5.1f}%   (5th%: {np.percentile(b_mdds, 5):>5.1f}%   | 95th%: {np.percentile(b_mdds, 95):>5.1f}%)")
    print(f" • Probability of Loss P(CAGR < 0) : {(np.sum(b_cagrs < 0) / n_boot) * 100.0:.2f}%")
    print(f" • Tail Risk P(Max DD > -20.0%)    : {(np.sum(b_mdds < -20.0) / n_boot) * 100.0:.2f}%")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    run_stress_suite()

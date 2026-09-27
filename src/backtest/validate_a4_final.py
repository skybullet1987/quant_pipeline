import sys
import warnings
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.run_fast_institutional_matrix import precompute_rolling_predictions
from src.backtest.controlled_sim import evaluate_controlled_experiment

def main():
    print("=" * 100)
    print("      A4 FINAL VALIDATION: 5.0% DEADBAND + S2 CASH CHOKE (FRICTION & BOOTSTRAP)      ")
    print("=" * 100)
    df, _, _ = load_and_prepare_panel()
    p12, p48, p168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    # 1. Friction Ladder for A4
    print("\n" + "-" * 100)
    print(" [TRACK 1] A4 FRICTION SWEEP: [-1, 0, 2, 5, 10, 15] BPS")
    print("-" * 100)
    frictions = [-1.0, 0.0, 2.0, 5.0, 10.0, 15.0]
    t1_rows = []

    for f in frictions:
        r = evaluate_controlled_experiment(
            df, p12, p48, p168, hmm_data, "A4",
            deadband_thresh=0.050, s2_mode="0x", friction_bps=f
        )
        t1_rows.append({
            "Friction": f"{f:>+4.0f} bps",
            "CAGR": f"{r['cagr']:>+6.1f}%",
            "Sharpe": f"{r['sharpe']:>5.2f}",
            "Sortino": f"{r['sortino']:>5.2f}",
            "Max DD": f"{r['mdd']:>5.1f}%",
            "Calmar": f"{r['calmar']:>5.2f}",
            "Profit Factor": f"{r['pf']:>4.2f}",
            "Ending $": f"${r['ending_cap']:,.0f}",
            "Fees Paid": f"${r['fees_paid']:>+5.0f}"
        })
    print(pd.DataFrame(t1_rows).to_string(index=False))

    # 2. Circular Block Bootstrap (2,000 Resamples)
    print("\n" + "-" * 100)
    print(" [TRACK 2] A4 CIRCULAR BLOCK BOOTSTRAP (2,000 Resamples | 48H Blocks)")
    print("-" * 100)
    boot_frictions = [-1.0, 0.0, 2.0, 5.0, 10.0]
    t2_rows = []

    for f in boot_frictions:
        res = evaluate_controlled_experiment(
            df, p12, p48, p168, hmm_data, "A4",
            deadband_thresh=0.050, s2_mode="0x", friction_bps=f
        )
        r_arr = res["returns"]
        N = len(r_arr)
        block_len, n_boot = 12, 2000
        n_blocks = N // block_len

        boot_cagrs, boot_sharpes, boot_mdds = [], [], []
        np.random.seed(42)

        for _ in range(n_boot):
            start_indices = np.random.randint(0, N, size=n_blocks)
            sampled = []
            for idx in start_indices:
                sampled.extend([r_arr[(idx + k) % N] for k in range(block_len)])
            s_arr = np.array(sampled[:N])
            cum_eq = np.cumprod(1.0 + s_arr)
            end_eq = cum_eq[-1]
            days = (N * 4.0) / 24.0
            b_cagr = float(((end_eq) ** (365.25 / days) - 1.0) * 100.0) if end_eq > 0 else -100.0
            b_sh = float((np.mean(s_arr) / (np.std(s_arr) + 1e-8)) * np.sqrt(2190))
            b_mdd = float(np.min((cum_eq - np.maximum.accumulate(cum_eq)) / np.maximum.accumulate(cum_eq)) * 100.0)
            boot_cagrs.append(b_cagr); boot_sharpes.append(b_sh); boot_mdds.append(b_mdd)

        b_cagrs, b_sharpes, b_mdds = np.array(boot_cagrs), np.array(boot_sharpes), np.array(boot_mdds)
        t2_rows.append({
            "Friction": f"{f:>+4.0f} bps",
            "Median CAGR": f"{np.percentile(b_cagrs, 50):>+6.1f}%",
            "5th% CAGR": f"{np.percentile(b_cagrs, 5):>+6.1f}%",
            "95th% CAGR": f"{np.percentile(b_cagrs, 95):>+6.1f}%",
            "Median Sharpe": f"{np.percentile(b_sharpes, 50):.2f}",
            "Median MaxDD": f"{np.percentile(b_mdds, 50):>5.1f}%",
            "P(CAGR < 0)": f"{(np.sum(b_cagrs < 0) / n_boot) * 100.0:.1f}%",
            "P(DD > -20%)": f"{(np.sum(b_mdds < -20.0) / n_boot) * 100.0:.1f}%"
        })

    print(pd.DataFrame(t2_rows).to_string(index=False))
    print("=" * 100 + "\n")

if __name__ == "__main__":
    main()

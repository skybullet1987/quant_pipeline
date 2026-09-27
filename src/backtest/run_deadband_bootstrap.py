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
    print("      [TRACK 3] A3 CIRCULAR BLOCK BOOTSTRAP (2,000 RESAMPLES | 48H BLOCKS)      ")
    print("=" * 100)
    df, _, _ = load_and_prepare_panel()
    p12, p48, p168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    boot_frictions = [-1.0, 0.0, 2.0, 5.0, 10.0]
    t3_rows = []

    for f in boot_frictions:
        res = evaluate_controlled_experiment(df, p12, p48, p168, hmm_data, "A3", deadband_thresh=0.035, s2_mode="0x", friction_bps=f)
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
        t3_rows.append({
            "Friction": f"{f:>+4.0f} bps", "Median CAGR": f"{np.percentile(b_cagrs, 50):>+6.1f}%",
            "5th% CAGR": f"{np.percentile(b_cagrs, 5):>+6.1f}%", "95th% CAGR": f"{np.percentile(b_cagrs, 95):>+6.1f}%",
            "Median Sharpe": f"{np.percentile(b_sharpes, 50):.2f}", "Median MaxDD": f"{np.percentile(b_mdds, 50):>5.1f}%",
            "P(CAGR < 0)": f"{(np.sum(b_cagrs < 0) / n_boot) * 100.0:.1f}%",
            "P(DD > -20%)": f"{(np.sum(b_mdds < -20.0) / n_boot) * 100.0:.1f}%"
        })

    print(pd.DataFrame(t3_rows).to_string(index=False))
    print("=" * 100 + "\n")

if __name__ == "__main__":
    main()

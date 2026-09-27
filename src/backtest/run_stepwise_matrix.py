import sys
import warnings
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import pandas as pd
from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.run_fast_institutional_matrix import precompute_rolling_predictions
from src.backtest.stepwise_convex_engine import evaluate_stepwise_trial

def main():
    print("=" * 115)
    print("       A4 STEPWISE ISOLATION MATRIX: LEVERAGE, DE-HEDGING & CONCENTRATION (+2 BPS)       ")
    print("=" * 115)
    df, unique_ts, grp_to_ts = load_and_prepare_panel()
    p12, p48, p168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    ladder = [
        ("A4.0 Control (1.75x, 65/35, K=5)", 1.75, 0.35, 5, 4),
        ("A4.1 Leverage 2.25x (65/35, K=5)", 2.25, 0.35, 5, 4),
        ("A4.2 Leverage 2.75x (65/35, K=5)", 2.75, 0.35, 5, 4),
        ("A4.3 De-Hedge 85/15 (2.75x, K=5)", 2.75, 0.15, 5, 4),
        ("A4.4 Concentration K=3 (2.75x, 85/15)", 2.75, 0.15, 3, 2),
        ("A4.5 Full Aggressive (3.25x, 85/15, K=3)", 3.25, 0.15, 3, 2),
    ]

    results = []
    for label, lev, short_mult, kl, ks in ladder:
        res = evaluate_stepwise_trial(
            df, p12, p48, p168, hmm_data, label,
            s0_lev=lev, s0_short_gate=short_mult,
            k_long=kl, k_short=ks, deadband=0.050, friction_bps=2.0
        )
        results.append(res)
        print(f" • Completed: {label}")

    res_df = pd.DataFrame(results)
    print("\n" + "=" * 115)
    print("                         STEPWISE ABLATION DIAGNOSTIC TABLE                                  ")
    print("=" * 115)
    print(res_df.to_string(index=False))
    print("=" * 115 + "\n")

if __name__ == "__main__":
    main()

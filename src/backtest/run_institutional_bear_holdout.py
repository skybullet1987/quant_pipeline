import sys
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

import pandas as pd
from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.bear_predictions import precompute_bear_holdout_predictions
from src.backtest.bear_evaluator import evaluate_bear_tier

def main():
    print("=" * 115)
    print("     INSTITUTIONAL BEAR MARKET HOLDOUT (15.2M BURN-IN | SEP 2025 -> APR 2026 BTC -36%)    ")
    print("=" * 115)
    df, _, _ = load_and_prepare_panel()
    start_eval, end_eval = 2768, 4083

    preds_12, preds_48, preds_168, hmm_data = precompute_bear_holdout_predictions(
        df, start_eval=start_eval, end_eval=end_eval, retrain_step=42
    )

    candidate_levs = [1.00, 1.75, 2.00, 2.50, 3.00]
    results = []

    print("\n" + "-" * 115)
    print(" [EVALUATION] EXECUTING CANDIDATE TIERS ON UNTOUCHED BEAR DATES")
    print("-" * 115)

    for lev in candidate_levs:
        r = evaluate_bear_tier(
            df, preds_12, preds_48, preds_168, hmm_data,
            start_grp=start_eval, end_grp=end_eval, forced_s0_gross=lev, friction_bps=2.0
        )
        results.append(r)
        print(f" • S0 Target {lev:.2f}x (E[G|S0]: {r['E[G|S0]']}): Ending {r['Ending $']} ({r['Actual Ret']}) | Sharpe {r['Sharpe']} | MaxDD {r['Max DD']} [{r['Status']}]")

    print("\n" + "=" * 115)
    print("                 INSTITUTIONAL BEAR MARKET HOLDOUT RESULTS TABLE                           ")
    print("=" * 115)
    print(pd.DataFrame(results).to_string(index=False))
    print("=" * 115 + "\n")

if __name__ == "__main__":
    main()

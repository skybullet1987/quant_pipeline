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
from src.backtest.controlled_sim import evaluate_controlled_experiment

def main():
    print("=" * 100)
    print("      A0 FACTORIAL TURNOVER & S2 CHOKE EXPERIMENT (TRACKS 1 & 2)      ")
    print("=" * 100)
    df, unique_ts, grp_to_ts = load_and_prepare_panel()
    p12, p48, p168, hmm_data = precompute_rolling_predictions(df, retrain_step=42)

    # 1. FACTORIAL COMPARISON (0 BPS BASELINE)
    print("\n" + "-" * 100)
    print(" [TRACK 1] FACTORIAL MATRIX: TURNOVER SUPPRESSION & S2 CASH CHOKE (0 BPS)")
    print("-" * 100)
    variants = [
        ("A0. Control", 0.000, "0.5x"),
        ("A1. Deadband 3.5%", 0.035, "0.5x"),
        ("A2. S2 Cash Choke", 0.000, "0x"),
        ("A3. Deadband 3.5% + S2 Choke", 0.035, "0x"),
        ("A4. Deadband 5.0% + S2 Choke", 0.050, "0x"),
        ("A5. Deadband 7.5% + S2 Choke", 0.075, "0x")
    ]
    t1_rows = []
    for label, db, s2 in variants:
        r = evaluate_controlled_experiment(df, p12, p48, p168, hmm_data, label, deadband_thresh=db, s2_mode=s2, friction_bps=0.0)
        t1_rows.append({
            "Variant": label, "Turnover": f"${r['turnover_usd']:,.0f}", "Mult": f"{r['turnover_mult']:.1f}x",
            "Suppressed": f"{r['suppressed_pct']:.1f}%", "Gross PnL": f"${r['gross_pnl']:>+5.0f}",
            "CAGR": f"{r['cagr']:>+6.1f}%", "Sharpe": f"{r['sharpe']:.2f}", "Sortino": f"{r['sortino']:.2f}",
            "Max DD": f"{r['mdd']:>5.1f}%", "Calmar": f"{r['calmar']:.2f}", "S2 PnL": f"${r['s2_pnl']:>+5.0f}",
            "Worst 4H": f"{r['worst_4h']:>5.2f}%", "Worst Trade": f"{r['worst_trade']:>5.1f}%"
        })
    print(pd.DataFrame(t1_rows).to_string(index=False))

    # 2. FRICTION BREAKEVEN LADDER
    print("\n" + "-" * 100)
    print(" [TRACK 2] FRICTION BREAKEVEN LADDER: A0 CONTROL VS A3 ([-1, 0, 2, 5, 10, 15] BPS)")
    print("-" * 100)
    frictions = [-1.0, 0.0, 2.0, 5.0, 10.0, 15.0]
    t2_rows = []
    for f in frictions:
        r_a0 = evaluate_controlled_experiment(df, p12, p48, p168, hmm_data, "A0", deadband_thresh=0.000, s2_mode="0.5x", friction_bps=f)
        r_a3 = evaluate_controlled_experiment(df, p12, p48, p168, hmm_data, "A3", deadband_thresh=0.035, s2_mode="0x", friction_bps=f)
        t2_rows.append({
            "Friction": f"{f:>+4.0f} bps", "A0 CAGR": f"{r_a0['cagr']:>+6.1f}%", "A0 Sharpe": f"{r_a0['sharpe']:>5.2f}",
            "A0 MaxDD": f"{r_a0['mdd']:>5.1f}%", "A0 Ending": f"${r_a0['ending_cap']:,.0f}", "|": "|",
            "A3 CAGR": f"{r_a3['cagr']:>+6.1f}%", "A3 Sharpe": f"{r_a3['sharpe']:>5.2f}", "A3 MaxDD": f"{r_a3['mdd']:>5.1f}%",
            "A3 Ending": f"${r_a3['ending_cap']:,.0f}", "A3 Fees": f"${r_a3['fees_paid']:>+5.0f}"
        })
    print(pd.DataFrame(t2_rows).to_string(index=False))
    print("=" * 100 + "\n")

if __name__ == "__main__":
    main()

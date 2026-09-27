import sys
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.backtest_engine import simulate_walkforward

def run_experiment_matrix():
    print("=" * 85)
    print("       INSTITUTIONAL WALK-FORWARD MATRIX (MATURED LABELS + LW COV)        ")
    print("=" * 85)
    df, unique_ts, grp_to_ts = load_and_prepare_panel()

    configs = [
        ("1. Fixed Horizon (30/45/25) + Static 1.5x Lev + No Ratchet", False, False, False),
        ("2. Matured Dynamic IR + Static 1.5x Lev + No Ratchet", True, False, False),
        ("3. Matured Dynamic IR + 3-State HMM Governor + Static Stops", True, False, True),
        ("4. Full Architecture (Dynamic IR + HMM Governor + Full Ratchet)", True, True, True)
    ]

    for label, use_ir, use_ratchet, use_hmm in configs:
        res = simulate_walkforward(df, grp_to_ts, use_ir, use_ratchet, use_hmm, retrain_step=42, rebalance_holding_bars=6, top_k=5)
        print(f"\n--> {label}")
        print(f"    • OOS Test Horizon     : {res['start_ts']} to {res['end_ts']} ({res['days']:.1f} days / {res['bars']} bars)")
        print(f"    • Out-of-Sample Sharpe : {res['sharpe']:.2f}")
        print(f"    • Annualized CAGR      : {res['cagr']:,.1f}% (Ending Capital: ${res['end_cap']:,.2f})")
        print(f"    • Maximum Drawdown     : {res['max_dd']:.2f}%")
        print(f"    • Profit Factor        : {res['pf']:.2f} | 4H Win Rate: {res['win_rate']:.1f}%")

    print("\n" + "=" * 85)

if __name__ == "__main__":
    run_experiment_matrix()

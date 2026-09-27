import sys
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.backtest.backtest_data import load_and_prepare_panel
from src.backtest.backtest_engine import simulate_walkforward

def run_experiment_matrix():
    print("=" * 90)
    print("    INSTITUTIONAL WALK-FORWARD MATRIX (BENCHMARK 0 -> FULL ARCHITECTURE)     ")
    print("=" * 90)
    df, unique_ts, grp_to_ts = load_and_prepare_panel()

    configs = [
        ("B0. Benchmark 0 (Naive EW Top-5, 1.0x Gross, No HRP, No Carry, No HMM)", False, False, False, False, False),
        ("B1. + Ledoit-Wolf HRP Allocation (1.5x Gross)", False, False, False, True, False),
        ("B2. + Null-Space Carry Overlay", False, False, False, True, True),
        ("B3. + Matured Dynamic IC-IR Stability Horizon Weighting", True, False, False, True, True),
        ("B4. + Empirically Fitted 3-State HMM Regime Governor", True, False, True, True, True),
        ("B5. + Intrabar Dynamic Ratchet & Chandelier Stops (Full Production)", True, True, True, True, True)
    ]

    for label, use_ir, use_ratchet, use_hmm, use_hrp, use_carry in configs:
        res = simulate_walkforward(
            df, grp_to_ts, config_name=label,
            use_dynamic_ir=use_ir, use_ratchet=use_ratchet, use_hmm=use_hmm,
            use_hrp=use_hrp, use_carry=use_carry, retrain_step=42, rebalance_holding_bars=6, top_k=5
        )
        print(f"\n--> {res['config']}")
        print(f"    • Out-of-Sample Sharpe : {res['sharpe']:.2f} | Profit Factor: {res['pf']:.2f}")
        print(f"    • Annualized CAGR      : {res['cagr']:,.1f}% (Ending Capital: ${res['end_cap']:,.2f})")
        print(f"    • Maximum Drawdown     : {res['max_dd']:.2f}% | 4H Win Rate: {res['win_rate']:.1f}%")

    print("\n" + "=" * 90)

if __name__ == "__main__":
    run_experiment_matrix()

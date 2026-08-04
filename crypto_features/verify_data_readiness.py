import pandas as pd
from google.cloud import bigquery
import sys
import warnings

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"

def run_suite():
    client = bigquery.Client(project=PROJECT_ID)
    passed_all = True
    
    print("========================================================")
    print("      INSTITUTIONAL PRE-TRAINING DATA INTEGRITY SUITE   ")
    print("========================================================\n")

    # ------------------------------------------------------------------------
    # ASSERTION 1: OHLC Geometry Integrity
    # ------------------------------------------------------------------------
    q_ohlc = f"""
        SELECT 
            COUNT(1) AS total_bars,
            COUNTIF(high < open OR high < close OR low > open OR low > close) AS invalid_ohlc_bars
        FROM `{PROJECT_ID}.market_data.stg_1m_cleaned`
    """
    try:
        df_ohlc = client.query(q_ohlc).to_dataframe()
        invalid = df_ohlc['invalid_ohlc_bars'].iloc[0]
        total = df_ohlc['total_bars'].iloc[0]
        
        print("[ASSERTION 1] OHLC Bar Geometry Test:")
        print(f"  - Total Scanned Bars: {total:,}")
        if invalid == 0:
            print("  -> PASSED: 100% of candles satisfy high/low bounds.\n")
        else:
            print(f"  -> FAILED: Found {invalid:,} corrupt OHLC bars!\n")
            passed_all = False
    except Exception as e:
        print(f"  -> FAILED: Could not query stg_1m_cleaned: {e}\n")
        passed_all = False

    # ------------------------------------------------------------------------
    # ASSERTION 2: Path Resolution & Exit Reason States
    # ------------------------------------------------------------------------
    q_states = f"""
        SELECT 
            exit_reason,
            COUNT(1) AS count,
            AVG(exact_gross_return) AS avg_return,
            COUNTIF(exact_gross_return IS NULL OR entry_price IS NULL) AS null_values
        FROM `{PROJECT_ID}.market_data.fct_exact_path_resolution`
        GROUP BY exit_reason
    """
    try:
        df_states = client.query(q_states).to_dataframe()
        print("[ASSERTION 2] Exit State & Null Integrity Test:")
        print(df_states.to_string(index=False))
        
        nulls = df_states['null_values'].sum()
        valid_reasons = {'TP_HIT', 'SL_HIT', 'TIMEOUT', 'DATA_ERROR'}
        found_reasons = set(df_states['exit_reason'].unique())
        invalid_reasons = found_reasons - valid_reasons

        if nulls == 0 and len(invalid_reasons) == 0:
            print("  -> PASSED: Zero NULLs found and all states are valid.\n")
        else:
            print(f"  -> FAILED: Invalid exit states or NULL values detected! ({invalid_reasons})\n")
            passed_all = False

        # Check TIMEOUT return dynamics
        timeout_row = df_states[df_states['exit_reason'] == 'TIMEOUT']
        if not timeout_row.empty:
            avg_timeout_ret = timeout_row['avg_return'].values[0]
            if abs(avg_timeout_ret) > 0.0001:
                print(f"  -> TIMEOUT Check: Valid dynamic path evaluation (Avg Yield: {avg_timeout_ret:.4%}).\n")
            else:
                print("  -> WARNING: TIMEOUT returns appear static or uncalculated!\n")

    except Exception as e:
        print(f"  -> FAILED: Could not query fct_exact_path_resolution: {e}\n")
        passed_all = False

    # ------------------------------------------------------------------------
    # ASSERTION 3: Target Barrier Symmetry Check
    # ------------------------------------------------------------------------
    try:
        tp_ret = df_states[df_states['exit_reason'] == 'TP_HIT']['avg_return'].values
        sl_ret = df_states[df_states['exit_reason'] == 'SL_HIT']['avg_return'].values

        print("[ASSERTION 3] Barrier Symmetry Test (+1.5 / -1.5 ATR):")
        if len(tp_ret) > 0 and len(sl_ret) > 0:
            tp_val = abs(tp_ret[0])
            sl_val = abs(sl_ret[0])
            delta = abs(tp_val - sl_val)
            print(f"  - Avg TP Gross Return: {tp_ret[0]:.4%}")
            print(f"  - Avg SL Gross Return: {sl_ret[0]:.4%}")
            print(f"  - Delta: {delta:.4%}")

            if delta <= 0.0005:
                print("  -> PASSED: Targets are strictly symmetric within 0.05% tolerance.\n")
            else:
                print("  -> FAILED: Asymmetry detected between upper/lower barriers!\n")
                passed_all = False
    except Exception as e:
        print(f"  -> FAILED: Symmetry evaluation error: {e}\n")
        passed_all = False

    # ------------------------------------------------------------------------
    # ASSERTION 4: Same-Bar Collision Check
    # ------------------------------------------------------------------------
    q_collisions = f"""
        SELECT 
            COUNT(1) AS total_trades,
            COUNTIF(exit_time = signal_time) AS collisions
        FROM `{PROJECT_ID}.market_data.fct_exact_path_resolution`
    """
    try:
        df_col = client.query(q_collisions).to_dataframe()
        tot_trades = df_col['total_trades'].iloc[0]
        collisions = df_col['collisions'].iloc[0]
        col_pct = (collisions / tot_trades) * 100 if tot_trades > 0 else 0

        print("[ASSERTION 4] Same-Bar Collision Test:")
        print(f"  - Total Trades: {tot_trades:,}")
        print(f"  - Same-Bar Collisions: {collisions:,} ({col_pct:.2f}%)")

        if col_pct < 1.0:
            print("  -> PASSED: Same-bar collision rate is under threshold (< 1.0%).\n")
        else:
            print("  -> FAILED: Collision rate exceeds safety tolerance (> 1.0%).\n")
            passed_all = False
    except Exception as e:
        print(f"  -> FAILED: Collision check error: {e}\n")
        passed_all = False

    # ------------------------------------------------------------------------
    # FINAL VERDICT
    # ------------------------------------------------------------------------
    print("========================================================")
    if passed_all:
        print("  [PASSED] DATA IS CLEAN, SYMMETRIC & READY FOR ML")
    else:
        print("  [FAILED] DO NOT TRAIN MODELS - FIX DATA ISSUES FIRST")
    print("========================================================")

if __name__ == "__main__":
    run_suite()

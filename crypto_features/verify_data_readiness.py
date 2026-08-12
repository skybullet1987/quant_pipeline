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

    except Exception as e:
        print(f"  -> FAILED: Could not query fct_exact_path_resolution: {e}\n")
        passed_all = False

    # ------------------------------------------------------------------------
    # ASSERTION 3: Target Barrier ATR Symmetry Check
    # ------------------------------------------------------------------------
    q_atr_sym = f"""
        SELECT 
            AVG(ABS(target_price_1_5_atr - entry_price) / NULLIF(atr_20, 0)) AS avg_tp_atr_multiple,
            AVG(ABS(entry_price - stop_loss_1_5_atr) / NULLIF(atr_20, 0)) AS avg_sl_atr_multiple
        FROM `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
        INNER JOIN `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
            ON p.signal_time = f.timestamp AND p.ticker = f.ticker
        WHERE p.exit_reason IN ('TP_HIT', 'SL_HIT')
    """
    try:
        df_sym = client.query(q_atr_sym).to_dataframe()
        tp_mult = df_sym['avg_tp_atr_multiple'].iloc[0]
        sl_mult = df_sym['avg_sl_atr_multiple'].iloc[0]
        delta_mult = abs(tp_mult - sl_mult)

        print("[ASSERTION 3] Barrier ATR Multiple Symmetry Test (Target: 1.5x ATR):")
        print(f"  - Avg TP ATR Multiple: {tp_mult:.4f}x")
        print(f"  - Avg SL ATR Multiple: {sl_mult:.4f}x")
        print(f"  - Multiple Delta: {delta_mult:.4f}")

        if delta_mult <= 0.01:
            print("  -> PASSED: ATR barriers are mathematically symmetric (1.5x / 1.5x).\n")
        else:
            print("  -> FAILED: Asymmetry detected in ATR barrier construction!\n")
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

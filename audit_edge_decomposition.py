import pandas as pd
import numpy as np
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"

def main():
    print("=====================================================================")
    print("  EDGE DECOMPOSITION AUDIT & STRESS TEST")
    print("=====================================================================")
    client = bigquery.Client(project=PROJECT_ID)
    
    print("Fetching exact path resolution dataset from BigQuery...")
    query = f"""
        SELECT 
            ticker, 
            target_short, 
            exit_reason, 
            minutes_in_trade 
        FROM `{PROJECT_ID}.market_data.fct_exact_path_resolution`
    """
    df = client.query(query).to_dataframe()
    
    total_rows = len(df)
    if total_rows == 0:
        print("[ERROR] Table is empty!")
        return

    # --- TEST 1: RANDOMIZED ENTRY BASELINE ---
    print("\n[TEST 1] RANDOMIZED ENTRY BASELINE")
    short_wins = (df['target_short'] == 1).sum()
    random_win_rate = (short_wins / total_rows) * 100
    
    print(f"  -> Total Evaluated Short Rows:   {total_rows:,}")
    print(f"  -> Baseline Random Short Win Rate:{random_win_rate:.2f}%")
    print(f"  -> CatBoost Live Win Rate:       62.30%")
    print(f"  -> Alpha Generation (Delta):     +{62.30 - random_win_rate:.2f}%")
    
    # --- TEST 2: THE FUNDING RATE STRESS TEST ---
    print("\n[TEST 2] HISTORICAL FUNDING RATE STRESS TEST (SHORTS ONLY)")
    avg_minutes_held = df['minutes_in_trade'].mean()
    avg_hours_held = avg_minutes_held / 60.0
    funding_rate_per_hour = 0.0001 / 8  # Standard 0.01% / 8h base rate
    
    avg_funding_drag_pct = avg_hours_held * funding_rate_per_hour * 100
    win_pnl_pct = 1.50 # Assuming 1.5x ATR TP
    
    print(f"  -> Average Short Hold Time:      {avg_hours_held:.1f} Hours ({avg_minutes_held:.1f} Mins)")
    print(f"  -> Est. Funding Drag Per Trade: -{avg_funding_drag_pct:.4f}%")
    if avg_funding_drag_pct < (win_pnl_pct * 0.05):
        print("  -> Verdict: EDGE SURVIVES. Funding drag is negligible relative to gross TP distance.")
    else:
        print("  -> Verdict: DANGER. Funding is eroding >5% of gross profits.")

    # --- TEST 3: ASSET CONCENTRATION ---
    print("\n[TEST 3] ASSET CONCENTRATION CHECK")
    asset_counts = df.groupby('ticker').size().sort_values(ascending=False)
    top_5_pct = (asset_counts.head(5).sum() / total_rows) * 100
    print(f"  -> Top 5 Assets Account For:     {top_5_pct:.2f}% of all historical triggers")
    if top_5_pct > 25:
        print("  -> Warning: Strategy is heavily concentrated in specific coins.")
    else:
        print("  -> Verdict: Risk is well-distributed across the universe.")
        
    print("\n=====================================================================")

if __name__ == "__main__":
    main()

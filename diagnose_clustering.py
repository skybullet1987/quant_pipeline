import pandas as pd
import numpy as np

FILE_PATH = "raw_executed_signals.parquet"
MAX_HOLD_MINUTES = 30 # From HORIZON logic in relabel_tbm.py

def analyze_signal_clustering():
    print("Loading extracted signal data...")
    df = pd.read_parquet(FILE_PATH)
    
    # Crucial pre-sort for episodic detection
    df = df.sort_values(by=['ticker', 'timestamp']).reset_index(drop=True)

    print("\n========================================================")
    print("              SIGNAL CLUSTERING DIAGNOSTICS             ")
    print("========================================================")

    # ---------------------------------------------------------
    # 1. TRADE EPISODES & CLUSTERING IDENTIFICATION
    # ---------------------------------------------------------
    # If the same ticker fires the same direction <= 30 minutes 
    # of a previous trade, we flag it as the same "Episode".
    df['time_diff'] = df.groupby(['ticker', 'direction'])['timestamp'].diff()
    df['is_new_episode'] = (df['time_diff'] > pd.Timedelta(minutes=MAX_HOLD_MINUTES)) | df['time_diff'].isna()
    
    # Generate unique Episode IDs
    df['episode_idx'] = df.groupby(['ticker', 'direction'])['is_new_episode'].cumsum()
    df['global_episode_id'] = df['ticker'] + "_" + df['direction'] + "_ep" + df['episode_idx'].astype(str)

    episode_stats = df.groupby('global_episode_id').agg(
        trade_count=('timestamp', 'count'),
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max'),
        avg_prob=('calibrated_prob', 'mean'),
        direction=('direction', 'first'),
        ticker=('ticker', 'first')
    ).reset_index()

    episode_stats['persistence_minutes'] = (episode_stats['end_time'] - episode_stats['start_time']).dt.total_seconds() / 60.0

    total_raw_trades = len(df)
    unique_episodes = len(episode_stats)
    
    clustered_trades = len(df[df['time_diff'] <= pd.Timedelta(minutes=MAX_HOLD_MINUTES)])
    clustering_pct = clustered_trades / total_raw_trades if total_raw_trades > 0 else 0

    print(f"Total Raw Signals Fired:     {total_raw_trades:,}")
    print(f"Independent Trade Episodes:  {unique_episodes:,}")
    print(f"Clustered Entry Rate:        {clustering_pct:.2%}")
    print(f"Average Trades per Episode:  {episode_stats['trade_count'].mean():.2f}")
    print(f"Max Trades in One Episode:   {episode_stats['trade_count'].max()}")

    # ---------------------------------------------------------
    # 2. SIGNAL PERSISTENCE
    # ---------------------------------------------------------
    print("\n--- Signal Persistence (Consecutive Overlap) ---")
    multi_trade_episodes = episode_stats[episode_stats['trade_count'] > 1]
    
    if len(multi_trade_episodes) > 0:
        print(f"Average Cluster Duration:    {multi_trade_episodes['persistence_minutes'].mean():.2f} minutes")
        print(f"Maximum Cluster Duration:    {multi_trade_episodes['persistence_minutes'].max():.2f} minutes")
    else:
        print("No multi-trade episodes detected.")

    # ---------------------------------------------------------
    # 3. CONCURRENT POSITIONS (TIME-SERIES SIMULATION)
    # ---------------------------------------------------------
    print("\n--- Time-Series Simulation (Concurrent Positions) ---")
    
    # Flatten the timeline into an entry (+1) and exit (-1) event log
    events = []
    for _, row in df.iterrows():
        events.append({'time': row['timestamp'], 'change': 1})
        events.append({'time': row['timestamp'] + pd.Timedelta(minutes=MAX_HOLD_MINUTES), 'change': -1})

    events_df = pd.DataFrame(events).sort_values('time')
    
    # Cumulative sum creates a minute-by-minute snapshot of capital utilization depth
    events_df['concurrent_positions'] = events_df['change'].cumsum()

    max_concurrent = events_df['concurrent_positions'].max()
    p99_concurrent = events_df['concurrent_positions'].quantile(0.99)
    p95_concurrent = events_df['concurrent_positions'].quantile(0.95)

    print(f"Maximum Simultaneous Trades: {max_concurrent}")
    print(f"99th Percentile Concurrency: {p99_concurrent:.1f} trades")
    print(f"95th Percentile Concurrency: {p95_concurrent:.1f} trades")

    print("\n========================================================")
    print("Next Steps Required for Simulator:")
    print("1. Convert `sum()` based PnL logic to stateful Fraction-Kelly loops.")
    print("2. Implement first-in, lock-out logic per ticker (Episode Collapse).")
    print("3. Add Margin Capacity limits to properly bound daily Variance.")

if __name__ == "__main__":
    analyze_signal_clustering()

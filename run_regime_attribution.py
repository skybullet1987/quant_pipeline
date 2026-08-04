import pandas as pd
import numpy as np

SIGNALS_FILE = "raw_executed_signals.parquet"
FEATURE_FILE = "feature_matrix_symmetric.parquet"
STARTING_CAPITAL = 1000.0
EXTRA_SLIPPAGE_AND_FEE_BPS = 0.0006  # 10 bps total friction
MAX_DOLLAR_PER_TRADE = 250000.0

def run_attribution_and_gating():
    print("Loading datasets for Regime Attribution Analysis...")
    try:
        signals = pd.read_parquet(SIGNALS_FILE)
        features = pd.read_parquet(FEATURE_FILE)
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    signals['timestamp'] = pd.to_datetime(signals['timestamp'], utc=True)
    features['timestamp'] = pd.to_datetime(features['timestamp'], utc=True)

    # ---------------------------------------------------------
    # 1. EXTRACT MACRO & REGIME INDICATORS FROM FEATURE MATRIX
    # ---------------------------------------------------------
    print("Building Macro Regime Indicators (BTC Trend, Volatility Percentile, HMM)...")
    
    # Extract BTC for Trend & Volatility Baselines
    btc_df = features[features['ticker'].str.contains('BTC', case=False, na=False)].copy()
    if btc_df.empty:
        btc_df = features[features['ticker'] == features['ticker'].iloc[0]].copy()

    btc_df = btc_df.sort_values('timestamp').drop_duplicates('timestamp')
    
    # Estimate BTC 50-period SMA & 30-day Rolling Volatility
    close_col = [c for c in btc_df.columns if 'close' in c.lower() or 'price' in c.lower()]
    close_col = close_col[0] if close_col else 'close'
    
    btc_df['btc_sma50'] = btc_df[close_col].rolling(50, min_periods=10).mean()
    btc_df['btc_trend_above'] = btc_df[close_col] > btc_df['btc_sma50']
    
    atr_col = [c for c in btc_df.columns if 'atr' in c.lower()]
    if atr_col:
        btc_df['volatility_metric'] = btc_df[atr_col[0]]
    else:
        btc_df['volatility_metric'] = btc_df[close_col].pct_change().abs().rolling(1440).mean()

    # Calculate Rolling Volatility Percentile
    btc_df['vol_percentile'] = btc_df['volatility_metric'].rolling(10080, min_periods=1440).rank(pct=True)

    # HMM State Extraction (Fallback to volatility regime if explicit HMM column is missing)
    hmm_col = [c for c in btc_df.columns if 'hmm' in c.lower() and 'state' in c.lower()]
    if hmm_col:
        btc_df['hmm_state'] = btc_df[hmm_col[0]]
    else:
        # Proxy HMM states by Volatility Percentiles: 0 = Low, 1 = Normal, 2 = Expansion
        btc_df['hmm_state'] = pd.qcut(btc_df['volatility_metric'].rank(method='first'), q=3, labels=[0, 1, 2])

    macro_regimes = btc_df[['timestamp', 'btc_trend_above', 'vol_percentile', 'hmm_state']].copy()

    # Merge Regimes onto Signals
    merged = pd.merge_asof(
        signals.sort_values('timestamp'),
        macro_regimes.sort_values('timestamp'),
        on='timestamp',
        direction='backward'
    )
    
    merged['net_return'] = merged['realized_return'] - EXTRA_SLIPPAGE_AND_FEE_BPS

    # ---------------------------------------------------------
    # EXPERIMENT 1: REGIME ATTRIBUTION MATRIX
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("                EXPERIMENT 1: REGIME ATTRIBUTION MATRIX                ")
    print("="*80)
    
    # Volatility Buckets
    merged['vol_bucket'] = pd.cut(merged['vol_percentile'], bins=[-0.01, 0.30, 0.70, 1.01], labels=['Low (<30%)', 'Normal (30-70%)', 'Expansion (>70%)'])

    attribution_vol = merged.groupby('vol_bucket', observed=False).agg(
        Trades=('net_return', 'count'),
        Win_Rate=('net_return', lambda x: (x > 0).mean()),
        Avg_EV_bps=('net_return', lambda x: x.mean() * 10000),
        Total_Return=('net_return', 'sum')
    )
    print("\n[1. PERFORMANCE BY VOLATILITY PERCENTILE]")
    print(attribution_vol.to_string())

    attribution_hmm = merged.groupby('hmm_state', observed=False).agg(
        Trades=('net_return', 'count'),
        Win_Rate=('net_return', lambda x: (x > 0).mean()),
        Avg_EV_bps=('net_return', lambda x: x.mean() * 10000),
        Total_Return=('net_return', 'sum')
    )
    print("\n[2. PERFORMANCE BY HMM STATE / REGIME]")
    print(attribution_hmm.to_string())

    attribution_trend = merged.groupby('btc_trend_above', observed=False).agg(
        Trades=('net_return', 'count'),
        Win_Rate=('net_return', lambda x: (x > 0).mean()),
        Avg_EV_bps=('net_return', lambda x: x.mean() * 10000),
        Total_Return=('net_return', 'sum')
    )
    attribution_trend.index = ['BTC Below SMA50', 'BTC Above SMA50']
    print("\n[3. PERFORMANCE BY BTC TREND ALIGNMENT]")
    print(attribution_trend.to_string())

    # ---------------------------------------------------------
    # EXPERIMENT 2: HMM & VOLATILITY GATING SIMULATIONS
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("            EXPERIMENT 2: REGIME GATING SIMULATION COMPARISON          ")
    print("="*80)

    gates = {
        "Baseline (No Gate)": merged,
        "Gate 1 (Vol > 50th Percentile)": merged[merged['vol_percentile'] >= 0.50],
        "Gate 2 (HMM Expansion / State 2)": merged[merged['hmm_state'] == 2],
        "Gate 3 (Vol > 50th + BTC Trend Aligned)": merged[(merged['vol_percentile'] >= 0.50) & (merged['btc_trend_above'] == True)]
    }

    results = []

    for name, df_gate in gates.items():
        if len(df_gate) == 0:
            continue
            
        realized_capital = STARTING_CAPITAL
        available_capital = STARTING_CAPITAL
        open_positions = []
        trade_log = []
        active_ticker_states = {}
        active_days = set()

        df_gate = df_gate.sort_values(by=['timestamp', 'calibrated_prob'], ascending=[True, False]).reset_index(drop=True)

        for idx, row in df_gate.iterrows():
            ts = row['timestamp']
            ticker = row['ticker']
            p = row['calibrated_prob']
            ret = row['net_return']
            exit_time = ts + pd.Timedelta(minutes=30)

            # Process Exits
            still_open = []
            for pos in open_positions:
                if ts >= pos['exit_time']:
                    profit = pos['notional_size'] * pos['realized_return']
                    realized_capital += profit
                    available_capital += (pos['margin_tied'] + profit)
                    if pos['ticker'] in active_ticker_states and active_ticker_states[pos['ticker']] == pos['exit_time']:
                        del active_ticker_states[pos['ticker']]
                    trade_log.append(profit)
                else:
                    still_open.append(pos)
            open_positions = still_open

            if ticker in active_ticker_states and ts < active_ticker_states[ticker]:
                continue
            if len(open_positions) >= 5:
                continue

            if p > 0.51:
                kelly_f = p - ((1 - p) / 1.0)
                trade_notional_pct = min(kelly_f * 0.5 * 3.0, 2.0)
                notional_size = min(realized_capital * trade_notional_pct, MAX_DOLLAR_PER_TRADE)
                margin_required = notional_size / 10.0

                if available_capital >= margin_required and notional_size > 10.0:
                    available_capital -= margin_required
                    open_positions.append({
                        'entry_time': ts, 'exit_time': exit_time, 'ticker': ticker,
                        'notional_size': notional_size, 'margin_tied': margin_required,
                        'realized_return': ret
                    })
                    active_ticker_states[ticker] = exit_time
                    active_days.add(ts.date())

        # Finalize stats
        t_df = pd.Series(trade_log)
        total_trades = len(t_df)
        win_rate = (t_df > 0).mean() if total_trades > 0 else 0
        
        start_ts = merged['timestamp'].min()
        end_ts = merged['timestamp'].max()
        total_days = max((end_ts - start_ts).days, 1)
        years = total_days / 365.25
        
        cagr = (realized_capital / STARTING_CAPITAL) ** (1 / years) - 1
        num_active_days = len(active_days)
        pct_time_active = (num_active_days / total_days) * 100
        
        # Return on Active Days
        active_years = max(num_active_days / 365.25, 0.01)
        return_on_active_days = (realized_capital / STARTING_CAPITAL) ** (1 / active_years) - 1

        results.append({
            "Gating Strategy": name,
            "Executed Trades": f"{total_trades:,}",
            "Win Rate": f"{win_rate:.2%}",
            "Final Capital": f"${realized_capital:,.2f}",
            "Annual CAGR": f"{cagr:.2%}",
            "Active Days": f"{num_active_days} ({pct_time_active:.1f}%)",
            "Return on Active Days": f"{return_on_active_days:.2%}"
        })

    summary_df = pd.DataFrame(results).set_index("Gating Strategy")
    print("\n[COMPARATIVE SIMULATION SUMMARY]")
    print(summary_df.to_string())
    print("="*80)

if __name__ == "__main__":
    run_attribution_and_gating()

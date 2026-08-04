import pandas as pd
import numpy as np

SIGNALS_FILE = "raw_executed_signals.parquet"
FEATURE_FILE = "feature_matrix_symmetric.parquet"
STARTING_CAPITAL = 1000.0
EXTRA_SLIPPAGE_AND_FEE_BPS = 0.0006  # 10 bps total friction
MAX_DOLLAR_PER_TRADE = 250000.0

def run_state0_ban():
    print("Loading datasets...")
    signals = pd.read_parquet(SIGNALS_FILE)
    features = pd.read_parquet(FEATURE_FILE)

    signals['timestamp'] = pd.to_datetime(signals['timestamp'], utc=True)
    features['timestamp'] = pd.to_datetime(features['timestamp'], utc=True)

    # Build HMM / Volatility Proxy
    btc_df = features[features['ticker'].str.contains('BTC', case=False, na=False)].copy()
    if btc_df.empty:
        btc_df = features[features['ticker'] == features['ticker'].iloc[0]].copy()

    btc_df = btc_df.sort_values('timestamp').drop_duplicates('timestamp')
    close_col = [c for c in btc_df.columns if 'close' in c.lower() or 'price' in c.lower()][0]
    atr_col = [c for c in btc_df.columns if 'atr' in c.lower()]
    
    if atr_col:
        btc_df['volatility_metric'] = btc_df[atr_col[0]]
    else:
        btc_df['volatility_metric'] = btc_df[close_col].pct_change().abs().rolling(1440).mean()

    # Proxy HMM states: 0 = Low (Bottom 33%), 1 = Normal (Middle 33%), 2 = Expansion (Top 33%)
    btc_df['hmm_state'] = pd.qcut(btc_df['volatility_metric'].rank(method='first'), q=3, labels=[0, 1, 2])
    
    macro_regimes = btc_df[['timestamp', 'hmm_state']].copy()

    merged = pd.merge_asof(
        signals.sort_values('timestamp'),
        macro_regimes.sort_values('timestamp'),
        on='timestamp',
        direction='backward'
    )
    merged['net_return'] = merged['realized_return'] - EXTRA_SLIPPAGE_AND_FEE_BPS

    # FILTER: Exclude HMM State 0
    filtered_signals = merged[merged['hmm_state'] != 0].copy()

    realized_capital = STARTING_CAPITAL
    available_capital = STARTING_CAPITAL
    open_positions = []
    trade_log = []
    daily_snapshots = []
    active_ticker_states = {}

    filtered_signals = filtered_signals.sort_values(by=['timestamp', 'calibrated_prob'], ascending=[True, False]).reset_index(drop=True)

    current_date = None
    for idx, row in filtered_signals.iterrows():
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
                trade_log.append({'profit': profit, 'ts': ts})
            else:
                still_open.append(pos)
        open_positions = still_open

        if current_date is None or ts.date() > current_date:
            current_date = ts.date()
            daily_snapshots.append({'date': current_date, 'equity': realized_capital})

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

    t_df = pd.DataFrame(trade_log)
    eq_df = pd.DataFrame(daily_snapshots).set_index('date')
    
    total_trades = len(t_df)
    win_rate = (t_df['profit'] > 0).mean()
    
    total_days = max((merged['timestamp'].max() - merged['timestamp'].min()).days, 1)
    years = total_days / 365.25
    cagr = (realized_capital / STARTING_CAPITAL) ** (1 / years) - 1

    eq_df['daily_return'] = eq_df['equity'].pct_change().fillna(0)
    sharpe = (eq_df['daily_return'].mean() / eq_df['daily_return'].std()) * np.sqrt(365) if eq_df['daily_return'].std() > 0 else 0
    
    eq_df['cum_max'] = eq_df['equity'].cummax()
    max_dd = ((eq_df['equity'] - eq_df['cum_max']) / eq_df['cum_max']).min()

    # Monthly Breakdown
    eq_df.index = pd.to_datetime(eq_df.index)
    monthly_eq = eq_df['equity'].resample('ME').last()
    monthly_ret = monthly_eq.pct_change().fillna((monthly_eq.iloc[0] - STARTING_CAPITAL) / STARTING_CAPITAL)
    monthly_matrix = pd.DataFrame({'Return': monthly_ret})
    monthly_matrix['Year'] = monthly_matrix.index.year
    monthly_matrix['Month'] = monthly_matrix.index.strftime('%b')
    monthly_pivot = monthly_matrix.pivot(index='Year', columns='Month', values='Return')

    print("\n" + "="*65)
    print("      STATE 0 BAN SIMULATION REPORT (ONLY STATES 1 & 2)       ")
    print("="*65)
    print(f"Starting Capital:            ${STARTING_CAPITAL:,.2f}")
    print(f"Final Capital:               ${realized_capital:,.2f}")
    print(f"Annualized CAGR:             {cagr:.2%}")
    print(f"Sharpe Ratio:                {sharpe:.2f}")
    print(f"Maximum Drawdown:            {max_dd:.2%}")
    print(f"Total Trades Executed:       {total_trades:,}")
    print(f"Win Rate:                    {win_rate:.2%}")
    print("-" * 65)
    print("\nMONTHLY RETURNS BREAKDOWN (%):")
    print((monthly_pivot * 100).round(2).to_string())
    print("="*65)

if __name__ == "__main__":
    run_state0_ban()

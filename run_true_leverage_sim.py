import pandas as pd
import numpy as np

SIGNALS_FILE = "raw_executed_signals.parquet"
FEATURE_FILE = "feature_matrix_symmetric.parquet"
STARTING_CAPITAL = 1000.0
EXTRA_SLIPPAGE_AND_FEE_BPS = 0.0006  # 10 bps friction
MAX_DOLLAR_PER_TRADE = 250000.0

def run_leveraged_variant(merged_df, effective_leverage_cap, label):
    realized_capital = STARTING_CAPITAL
    available_capital = STARTING_CAPITAL
    open_positions = []
    trade_log = []
    daily_snapshots = []
    active_ticker_states = {}

    # Strict temporal order
    df = merged_df.sort_values(by=['timestamp', 'calibrated_prob'], ascending=[True, False]).reset_index(drop=True)
    current_date = None

    for idx, row in df.iterrows():
        ts = row['timestamp']
        ticker = row['ticker']
        p = row['calibrated_prob']
        ret = row['realized_return'] - EXTRA_SLIPPAGE_AND_FEE_BPS
        exit_time = ts + pd.Timedelta(minutes=30)

        # 1. Process Exits
        still_open = []
        for pos in open_positions:
            if ts >= pos['exit_time']:
                profit = pos['notional_size'] * pos['realized_return']
                realized_capital += profit
                available_capital += (pos['margin_tied'] + profit)
                if pos['ticker'] in active_ticker_states and active_ticker_states[pos['ticker']] == pos['exit_time']:
                    del active_ticker_states[pos['ticker']]
                
                if realized_capital <= 0:
                    print(f"\n[!] REKT: Account Liquidated at {ts} under {label}!")
                    return
                trade_log.append({'profit': profit, 'ts': ts})
            else:
                still_open.append(pos)
        open_positions = still_open

        if current_date is None or ts.date() > current_date:
            current_date = ts.date()
            daily_snapshots.append({'date': current_date, 'equity': realized_capital})

        # 2. Position State Lock-out
        if ticker in active_ticker_states and ts < active_ticker_states[ticker]:
            continue
        if len(open_positions) >= 5:
            continue

        # 3. Position Sizing scaled by Effective Leverage Cap
        kelly_f = p - ((1 - p) / 1.0)
        
        # Scale position up to effective_leverage_cap (e.g. 5x or 10x account equity)
        trade_notional_pct = min(kelly_f * 1.0 * effective_leverage_cap, effective_leverage_cap)
        raw_notional = realized_capital * trade_notional_pct
        notional_size = min(raw_notional, MAX_DOLLAR_PER_TRADE)
        
        # 10x Cross-Margin Requirement
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
    win_rate = (t_df['profit'] > 0).mean() if total_trades > 0 else 0
    
    total_days = max((df['timestamp'].max() - df['timestamp'].min()).days, 1)
    years = total_days / 365.25
    cagr = (realized_capital / STARTING_CAPITAL) ** (1 / years) - 1

    eq_df['daily_return'] = eq_df['equity'].pct_change().fillna(0)
    sharpe = (eq_df['daily_return'].mean() / eq_df['daily_return'].std()) * np.sqrt(365) if eq_df['daily_return'].std() > 0 else 0
    
    eq_df['cum_max'] = eq_df['equity'].cummax()
    max_dd = ((eq_df['equity'] - eq_df['cum_max']) / eq_df['cum_max']).min()

    eq_df.index = pd.to_datetime(eq_df.index)
    monthly_eq = eq_df['equity'].resample('ME').last()
    monthly_ret = monthly_eq.pct_change().fillna((monthly_eq.iloc[0] - STARTING_CAPITAL) / STARTING_CAPITAL)
    monthly_matrix = pd.DataFrame({'Return': monthly_ret})
    monthly_matrix['Year'] = monthly_matrix.index.year
    monthly_matrix['Month'] = monthly_matrix.index.strftime('%b')
    monthly_pivot = monthly_matrix.pivot(index='Year', columns='Month', values='Return')

    print("\n" + "="*65)
    print(f"      TRUE EFFECTIVE LEVERAGE REPORT: {label.upper()}      ")
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

def main():
    print("Loading datasets for True Effective Leverage Test...")
    signals = pd.read_parquet(SIGNALS_FILE)
    features = pd.read_parquet(FEATURE_FILE)

    signals['timestamp'] = pd.to_datetime(signals['timestamp'], utc=True)
    features['timestamp'] = pd.to_datetime(features['timestamp'], utc=True)

    # Attach Volatility Percentile
    btc_df = features[features['ticker'].str.contains('BTC', case=False, na=False)].copy()
    if btc_df.empty:
        btc_df = features[features['ticker'] == features['ticker'].iloc[0]].copy()

    btc_df = btc_df.sort_values('timestamp').drop_duplicates('timestamp')
    close_col = [c for c in btc_df.columns if 'close' in c.lower() or 'price' in c.lower()][0]
    atr_col = [c for c in btc_df.columns if 'atr' in c.lower()]
    
    if atr_col:
        btc_df['vol_metric'] = btc_df[atr_col[0]]
    else:
        btc_df['vol_metric'] = btc_df[close_col].pct_change().abs().rolling(1440).mean()

    btc_df['vol_percentile'] = btc_df['vol_metric'].rolling(10080, min_periods=1440).rank(pct=True)
    macro_regimes = btc_df[['timestamp', 'vol_percentile']].copy()

    merged = pd.merge_asof(
        signals.sort_values('timestamp'),
        macro_regimes.sort_values('timestamp'),
        on='timestamp',
        direction='backward'
    )

    # Filter for Top 25% Volatility Regimes Only (Test B Filter)
    df_vol75 = merged[merged['vol_percentile'] >= 0.75].copy()

    # Run at 5x Effective Leverage
    run_leveraged_variant(df_vol75, 5.0, "5x Effective Position Leverage")

    # Run at 10x Effective Leverage
    run_leveraged_variant(df_vol75, 10.0, "10x Effective Position Leverage")

if __name__ == "__main__":
    main()

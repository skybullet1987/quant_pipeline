import pandas as pd
import numpy as np

SIGNAL_FILE = "raw_executed_signals.parquet"
STARTING_CAPITAL = 1000.0

# --- REAL-WORLD FRICTION & LEVERAGE CONSTRAINTS ---
EXTRA_SLIPPAGE_AND_FEE_BPS = 0.0006   # Adds +6 bps (bringing total roundtrip cost to 10 bps / 0.10%)
MAX_CONCURRENT_POSITIONS = 5
PAYOFF_RATIO = 1.0  

KELLY_FRACTION = 0.5                  # Half-Kelly for institutional risk control
NOTIONAL_LEVERAGE_SCALAR = 3.0        # Exposure multiplier
MAX_NOTIONAL_PER_TRADE = 2.0          # Max 200% account value per trade
EXCHANGE_MAX_LEVERAGE = 10.0          # Realistic DEX Cross-Margin limit (10x)
MAX_DOLLAR_PER_TRADE = 250000.0       # $250k order book liquidity cap per trade

def run_stateful_simulation():
    print(f"Loading {SIGNAL_FILE}...")
    try:
        df = pd.read_parquet(SIGNAL_FILE)
    except FileNotFoundError:
        print(f"Error: {SIGNAL_FILE} not found.")
        return
    
    # Chronological sort for strict temporal simulation
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.sort_values(by=['timestamp', 'calibrated_prob'], ascending=[True, False]).reset_index(drop=True)
    
    realized_capital = STARTING_CAPITAL
    available_capital = STARTING_CAPITAL
    
    open_positions = []
    trade_log = []
    daily_snapshots = []
    
    # Position State Tracker: ticker -> exit_time
    active_ticker_states = {}
    
    total_volume_traded = 0.0
    start_ts = df['timestamp'].min()
    end_ts = df['timestamp'].max()
    total_sim_days = max((end_ts - start_ts).days, 1)
    
    print(f"Running Realistic Engine (10 bps Friction | 10x Max Lev | $250k Cap)...")
    current_date = None
    
    for idx, row in df.iterrows():
        ts = row['timestamp']
        ticker = row['ticker']
        p = row['calibrated_prob']
        
        # Apply extra +6 bps fee/slippage penalty
        ret = row['realized_return'] - EXTRA_SLIPPAGE_AND_FEE_BPS
        
        minutes_in_trade = row.get('minutes_in_trade', 30)
        if pd.isna(minutes_in_trade) or minutes_in_trade <= 0:
            minutes_in_trade = 30
            
        exit_time = ts + pd.Timedelta(minutes=minutes_in_trade)

        # ---------------------------------------------------------
        # 1. PROCESS DYNAMIC EXITS & RELEASE POSITION STATES
        # ---------------------------------------------------------
        still_open = []
        for pos in open_positions:
            if ts >= pos['exit_time']:
                profit = pos['notional_size'] * pos['realized_return']
                realized_capital += profit
                available_capital += (pos['margin_tied'] + profit)
                
                # Release Ticker State
                if pos['ticker'] in active_ticker_states and active_ticker_states[pos['ticker']] == pos['exit_time']:
                    del active_ticker_states[pos['ticker']]
                
                # Check for Account Liquidation
                if realized_capital <= 0:
                    print(f"\n[!] REKT: Account Liquidated at {ts}!")
                    return
                
                trade_log.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': pos['exit_time'],
                    'ticker': pos['ticker'],
                    'direction': pos['direction'],
                    'notional_size': pos['notional_size'],
                    'margin_tied': pos['margin_tied'],
                    'realized_return': pos['realized_return'],
                    'profit': profit,
                    'holding_minutes': (pos['exit_time'] - pos['entry_time']).total_seconds() / 60.0
                })
            else:
                still_open.append(pos)
        open_positions = still_open

        # Daily Snapshot
        if current_date is None or ts.date() > current_date:
            current_date = ts.date()
            margin_in_use = sum(p['margin_tied'] for p in open_positions)
            daily_snapshots.append({
                'date': current_date, 
                'equity': realized_capital,
                'margin_in_use': margin_in_use,
                'concurrent_positions': len(open_positions)
            })

        # ---------------------------------------------------------
        # 2. POSITION STATE CHECK (Ignore if already in position)
        # ---------------------------------------------------------
        if ticker in active_ticker_states:
            if ts < active_ticker_states[ticker]:
                continue  

        # ---------------------------------------------------------
        # 3. MARGIN & CAPACITY CHECKS
        # ---------------------------------------------------------
        if len(open_positions) >= MAX_CONCURRENT_POSITIONS:
            continue

        # ---------------------------------------------------------
        # 4. KELLY SIZING WITH LIQUIDITY & LEVERAGE CAPS
        # ---------------------------------------------------------
        if p > 0.51:
            kelly_f = p - ((1 - p) / PAYOFF_RATIO)
            trade_notional_pct = min(kelly_f * KELLY_FRACTION * NOTIONAL_LEVERAGE_SCALAR, MAX_NOTIONAL_PER_TRADE)
            
            # Sizing bounded by Account Percentage AND Hard Dollar Cap ($250k)
            raw_notional = realized_capital * trade_notional_pct
            notional_size = min(raw_notional, MAX_DOLLAR_PER_TRADE)
            
            margin_required = notional_size / EXCHANGE_MAX_LEVERAGE
            
            if available_capital >= margin_required and notional_size > 10.0:
                available_capital -= margin_required
                
                open_positions.append({
                    'entry_time': ts,
                    'exit_time': exit_time,
                    'ticker': ticker,
                    'direction': row['direction'],
                    'prob': p,
                    'notional_size': notional_size,
                    'margin_tied': margin_required,
                    'realized_return': ret
                })
                
                active_ticker_states[ticker] = exit_time
                total_volume_traded += notional_size

    # Close open positions on final tick
    for pos in open_positions:
        profit = pos['notional_size'] * pos['realized_return']
        realized_capital += profit
        trade_log.append({
            'entry_time': pos['entry_time'],
            'exit_time': pos['exit_time'],
            'ticker': pos['ticker'],
            'direction': pos['direction'],
            'notional_size': pos['notional_size'],
            'margin_tied': pos['margin_tied'],
            'realized_return': pos['realized_return'],
            'profit': profit,
            'holding_minutes': (pos['exit_time'] - pos['entry_time']).total_seconds() / 60.0
        })

    # ---------------------------------------------------------
    # INSTITUTIONAL PERFORMANCE REPORT
    # ---------------------------------------------------------
    trades_df = pd.DataFrame(trade_log)
    eq_df = pd.DataFrame(daily_snapshots).drop_duplicates(subset=['date'], keep='last').set_index('date')
    
    if len(trades_df) == 0:
        print("No valid trades executed under these strict constraints.")
        return

    years = max(total_sim_days / 365.25, 0.1)
    cagr = (realized_capital / STARTING_CAPITAL) ** (1 / years) - 1
    
    eq_df['daily_return'] = eq_df['equity'].pct_change().fillna(0)
    daily_mean = eq_df['daily_return'].mean()
    daily_std = eq_df['daily_return'].std()
    
    sharpe = (daily_mean / daily_std) * np.sqrt(365) if daily_std > 0 else 0.0
    
    downside_std = eq_df[eq_df['daily_return'] < 0]['daily_return'].std()
    sortino = (daily_mean / downside_std) * np.sqrt(365) if downside_std > 0 else 0.0

    eq_df['cum_max'] = eq_df['equity'].cummax()
    eq_df['drawdown'] = (eq_df['equity'] - eq_df['cum_max']) / eq_df['cum_max']
    max_drawdown = eq_df['drawdown'].min()

    gross_profits = trades_df[trades_df['profit'] > 0]['profit'].sum()
    gross_losses = abs(trades_df[trades_df['profit'] < 0]['profit'].sum())
    profit_factor = gross_profits / gross_losses if gross_losses > 0 else np.inf

    avg_margin_in_use = eq_df['margin_in_use'].mean()
    return_on_margin = (gross_profits - gross_losses) / avg_margin_in_use if avg_margin_in_use > 0 else 0.0
    avg_concurrent_pos = eq_df['concurrent_positions'].mean()
    max_concurrent_pos = eq_df['concurrent_positions'].max()

    avg_holding_time_min = trades_df['holding_minutes'].mean()
    portfolio_turnover = total_volume_traded / STARTING_CAPITAL

    eq_df.index = pd.to_datetime(eq_df.index)
    monthly_eq = eq_df['equity'].resample('ME').last()
    monthly_ret = monthly_eq.pct_change().fillna((monthly_eq.iloc[0] - STARTING_CAPITAL) / STARTING_CAPITAL)
    monthly_matrix = pd.DataFrame({'Return': monthly_ret})
    monthly_matrix['Year'] = monthly_matrix.index.year
    monthly_matrix['Month'] = monthly_matrix.index.strftime('%b')
    monthly_pivot = monthly_matrix.pivot(index='Year', columns='Month', values='Return')

    print("\n" + "="*65)
    print("      REALISTIC DEX EXECUTION REPORT (10 BPS FRICTION)       ")
    print("="*65)
    print(f"Starting Capital:            ${STARTING_CAPITAL:,.2f}")
    print(f"Final Capital:               ${realized_capital:,.2f}")
    print(f"Annualized CAGR:             {cagr:.2%}")
    print(f"Sharpe Ratio:                {sharpe:.2f}")
    print(f"Sortino Ratio:               {sortino:.2f}")
    print(f"Maximum Drawdown:            {max_drawdown:.2%}")
    print(f"Profit Factor:               {profit_factor:.2f}")
    print("-" * 65)
    print(f"Total Trades Executed:       {len(trades_df):,}")
    print(f"Win Rate:                    {(trades_df['profit'] > 0).mean():.2%}")
    print(f"Avg Holding Time:            {avg_holding_time_min:.1f} minutes")
    print(f"Portfolio Turnover:          {portfolio_turnover:.1f}x")
    print(f"Avg Concurrent Positions:    {avg_concurrent_pos:.2f}")
    print(f"Max Concurrent Positions:    {max_concurrent_pos}")
    print(f"Return on Avg Margin:        {return_on_margin:.2%}")
    print("-" * 65)
    print("\nMONTHLY RETURNS BREAKDOWN (%):")
    print((monthly_pivot * 100).round(2).to_string())
    print("="*65)

if __name__ == "__main__":
    run_stateful_simulation()

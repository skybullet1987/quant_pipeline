import re

with open('run_production_backtest.py', 'r') as f:
    content = f.read()

replacement_block = """
    print("\\n========================================================")
    print("      PRODUCTION SIMULATOR: PERCENTILE SWEEP            ")
    print("========================================================")
    
    # Only look at setups that actually made it through the primary experts
    valid_setups = test_df[test_df['meta_prob'] > 0].copy()
    
    if len(valid_setups) == 0:
        print("No setups passed the primary experts.")
        return

    percentiles = [99.0, 95.0, 90.0, 80.0]
    
    for p in percentiles:
        threshold = np.percentile(valid_setups['meta_prob'], p)
        signals = valid_setups[valid_setups['meta_prob'] >= threshold].copy()
        signals = signals.sort_values('timestamp').reset_index(drop=True)
        
        raw_atr_pct = signals['atr_20'] / signals['close']
        fair_loss_ret = np.clip(signals['exact_gross_return'], -1.50 * raw_atr_pct, 0.0)

        signals['gross_ret'] = np.where(
            signals['exit_reason'] == 'TP_HIT',
            1.50 * raw_atr_pct,
            fair_loss_ret 
        )
        
        signals['net_ret'] = np.where(
            signals['exit_reason'] == 'TP_HIT',
            signals['gross_ret'] - WIN_FRICTION,
            signals['gross_ret'] - LOSS_FRICTION
        )

        starting_capital = 10000.0
        current_capital = starting_capital
        portfolio_history = []
        
        signals['date'] = signals['timestamp'].dt.date
        daily_signals = signals.groupby('date')
        MAX_DAILY_EXPOSURE = 0.20 
        
        for date, day_data in daily_signals:
            trade_count = len(day_data)
            if trade_count > 5:
                day_data = day_data.nlargest(5, 'meta_prob')
                trade_count = 5
                
            weight_per_trade = MAX_DAILY_EXPOSURE / trade_count
            daily_return = (day_data['net_ret'] * weight_per_trade).sum()
            
            current_capital *= (1 + daily_return)
            portfolio_history.append({'date': date, 'daily_return': daily_return, 'capital': current_capital})
            
        port_df = pd.DataFrame(portfolio_history)
        
        if len(port_df) > 0:
            total_days = (port_df['date'].iloc[-1] - port_df['date'].iloc[0]).days
            years = max(total_days / 365.25, 0.1)
            
            cagr = (current_capital / starting_capital) ** (1 / years) - 1
            daily_std = port_df['daily_return'].std()
            sharpe = (port_df['daily_return'].mean() / daily_std) * np.sqrt(365) if daily_std > 0 else 0.0
                
            port_df['cum_max'] = port_df['capital'].cummax()
            max_dd = ((port_df['capital'] - port_df['cum_max']) / port_df['cum_max']).min()
            win_rate = (signals['net_ret'] > 0).mean()
            
            print(f"--- Top {100-p:.0f}% of Signals (Prob >= {threshold:.4f}) ---")
            print(f"  Total Trades: {len(signals)}")
            print(f"  Win Rate: {win_rate:.2%}")
            print(f"  Final Capital: ${current_capital:,.2f}")
            print(f"  CAGR: {cagr:.2%}")
            print(f"  Max Drawdown: {max_dd:.2%}")
            print(f"  Sharpe: {sharpe:.2f}\\n")
"""

# Replace everything from the print statement down to the end of the main function
content = re.sub(r'print\("\\n={56}"\).*?(?=if __name__ == "__main__":)', replacement_block, content, flags=re.DOTALL)

with open('run_production_backtest.py', 'w') as f:
    f.write(content)


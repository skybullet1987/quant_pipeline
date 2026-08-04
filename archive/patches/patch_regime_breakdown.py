import re

with open('simulate_production_engine.py', 'r') as file:
    content = file.read()

# 1. Track hmm_regime in open_positions
old_open_pos = "'minutes_in_trade': row['minutes_in_trade']"
new_open_pos = "'minutes_in_trade': row['minutes_in_trade'], 'hmm_regime': row['hmm_regime']"
content = content.replace(old_open_pos, new_open_pos)

# 2. Track hmm_regime in trade_log
old_trade_log = "trade_log.append({'profit': profit, 'net_ret': pos['net_ret']})"
new_trade_log = "trade_log.append({'profit': profit, 'net_ret': pos['net_ret'], 'hmm_regime': pos['hmm_regime']})"
content = content.replace(old_trade_log, new_trade_log)

# 3. Add per-regime summary printout at the end
old_print_block = 'print(f"  - Annualized Sharpe Ratio: {sharpe:.2f}")'
new_print_block = """print(f"  - Annualized Sharpe Ratio: {sharpe:.2f}")
        
        if not trade_df.empty and 'hmm_regime' in trade_df.columns:
            print("\\n--------------------------------------------------------")
            print("            PER-REGIME PERFORMANCE BREAKDOWN           ")
            print("--------------------------------------------------------")
            reg_df = trade_df.groupby('hmm_regime').agg(
                Trades=('net_ret', 'count'),
                Win_Rate=('net_ret', lambda x: f"{(x > 0).mean():.2%}"),
                Total_Profit=('profit', lambda x: f"${x.sum():,.2f}"),
                Avg_Net_Ret=('net_ret', lambda x: f"{x.mean():.2%}")
            )
            print(reg_df.to_string())"""

content = content.replace(old_print_block, new_print_block)

with open('simulate_production_engine.py', 'w') as file:
    file.write(content)

print("Simulator patched with per-regime analytics.")

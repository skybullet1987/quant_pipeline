import re

with open('simulate_production_engine.py', 'r') as file:
    content = file.read()

# Add the new ATR and entry price columns to the BigQuery SELECT statement
old_select = r'SELECT f\.\*, p\.exit_time, p\.exit_reason, p\.exact_gross_return, p\.minutes_in_trade'
new_select = r'SELECT f.*, p.exit_time, p.exit_reason, p.exact_gross_return, p.minutes_in_trade, p.entry_price, p.target_price_3_atr, p.stop_loss_1_5_atr'

content = re.sub(old_select, new_select, content)

with open('simulate_production_engine.py', 'w') as file:
    file.write(content)

print("SQL query patched. Launching final matrix test...")

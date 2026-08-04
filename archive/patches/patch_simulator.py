import re

with open('simulate_production_engine.py', 'r') as file:
    content = file.read()

# Replace the hardcoded Kelly fraction and risk rules block
new_params = """    MAX_CONCURRENT_POSITIONS = 5
    KELLY_FRACTION = 0.25 
    MAX_RISK_PER_TRADE = 0.05 
    
    # Friction Constants
    WIN_FRICTION = 0.0047
    LOSS_FRICTION = 0.0062"""

content = re.sub(r'    MAX_CONCURRENT_POSITIONS = 5\n.*?MAX_RISK_PER_TRADE = 0.05', new_params, content, flags=re.DOTALL)

# Replace the static 0.58 threshold with dynamic EV
old_entry_loop = """                # Only take setups where true historical probability > 53%
                if p > 0.58 and len(open_positions) < MAX_CONCURRENT_POSITIONS:
                    kelly_f = p - ((1 - p) / PAYOFF_RATIO)"""

new_entry_loop = """                # Dynamic EV Calculation
                # Reconstruct gross targets based on the 3.0 vs 1.5 ATR math
                gross_win_pct = (row['target_price_3_atr'] - row['entry_price']) / row['entry_price']
                gross_loss_pct = (row['entry_price'] - row['stop_loss_1_5_atr']) / row['entry_price']
                
                net_win_pct = gross_win_pct - WIN_FRICTION
                net_loss_pct = gross_loss_pct + LOSS_FRICTION
                
                # Calculate Expected Value
                expected_value = (p * net_win_pct) - ((1 - p) * net_loss_pct)
                
                # Only execute if mathematically profitable
                if expected_value > 0 and len(open_positions) < MAX_CONCURRENT_POSITIONS:
                    # Calculate true dynamic payoff ratio for Kelly sizing
                    dynamic_payoff_ratio = net_win_pct / net_loss_pct
                    kelly_f = p - ((1 - p) / dynamic_payoff_ratio)"""

content = content.replace(old_entry_loop, new_entry_loop)

with open('simulate_production_engine.py', 'w') as file:
    file.write(content)

print("Simulator patched with Dynamic EV.")

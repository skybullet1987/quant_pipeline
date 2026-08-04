with open('simulate_production_engine.py', 'r') as file:
    content = file.read()

# Add hard regime filter to entry condition
old_cond = "if expected_value > 0 and p > 0.55 and len(open_positions) < MAX_CONCURRENT_POSITIONS:"
new_cond = "if expected_value > 0 and p > 0.55 and str(row['hmm_regime']) in ['0', '4'] and len(open_positions) < MAX_CONCURRENT_POSITIONS:"

content = content.replace(old_cond, new_cond)

with open('simulate_production_engine.py', 'w') as file:
    file.write(content)

print("HMM Gatekeeper applied (Restricted to Regimes 0 and 4).")

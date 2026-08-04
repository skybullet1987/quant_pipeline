with open('simulate_production_engine.py', 'r') as file:
    content = file.read()

# Inject the dual-lock: p > 0.55 AND expected_value > 0
old_condition = "if expected_value > 0 and len(open_positions) < MAX_CONCURRENT_POSITIONS:"
new_condition = "if expected_value > 0 and p > 0.55 and len(open_positions) < MAX_CONCURRENT_POSITIONS:"

content = content.replace(old_condition, new_condition)

with open('simulate_production_engine.py', 'w') as file:
    file.write(content)

print("Dual-lock applied. Launching constraint test...")

import re

with open('simulate_production_engine.py', 'r') as file:
    content = file.read()

# 1. Remove the variables from where we incorrectly placed them down below
content = re.sub(r'\s*# Friction Constants\s*WIN_FRICTION = [\d\.]+\s*LOSS_FRICTION = [\d\.]+', '', content)

# 2. Inject them safely at the very top of the main function
content = content.replace('def main():', 'def main():\n    WIN_FRICTION = 0.0047\n    LOSS_FRICTION = 0.0062')

with open('simulate_production_engine.py', 'w') as file:
    file.write(content)

print("Scope fixed. Launching simulation...")

import re

with open('train_production_models.py', 'r') as f:
    content = f.read()

# 1. Force the GaussianHMM to strictly 3 states
content = re.sub(r'n_components=\d+', 'n_components=3', content)

# 2. Force the CatBoost expert loop to only iterate through Regimes 0, 1, and 2
content = re.sub(r"for regime in \[[^\]]+\]:", "for regime in ['0', '1', '2']:", content)

with open('train_production_models.py', 'w') as f:
    f.write(content)

print("Surgical Regex Patch Applied. Forcing 3-State compilation...")

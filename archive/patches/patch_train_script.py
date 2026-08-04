with open('train_production_models.py', 'r') as f:
    content = f.read()

# 1. Crush the HMM state space down to 3
content = content.replace("n_components=4", "n_components=3")

# 2. Update the CatBoost expert loop to only train Regimes 0, 1, and 2
content = content.replace("for regime in ['0', '1', '2', '3']:", "for regime in ['0', '1', '2']:")

with open('train_production_models.py', 'w') as f:
    f.write(content)
    
print("Successfully patched train_production_models.py for strict 3-State HMM.")

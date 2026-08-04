import re

with open('train_production_models.py', 'r') as f:
    content = f.read()

# 1. Nuke any HMM_STATES or N_COMPONENTS constant at the top of the file
content = re.sub(r'HMM_STATES\s*=\s*\d+', 'HMM_STATES = 3', content)

# 2. Aggressively rewrite the GaussianHMM initialization line entirely
content = re.sub(r'GaussianHMM\([^)]+\)', 'GaussianHMM(n_components=3, covariance_type="full", n_iter=500, random_state=42)', content)

with open('train_production_models.py', 'w') as f:
    f.write(content)

print("Aggressive 3-State Override Applied. Compiling...")

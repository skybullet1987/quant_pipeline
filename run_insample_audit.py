with open('simulate_production_engine.py', 'r') as f:
    content = f.read()

# 1. Flip the time split: use the first 85% (Training) instead of the last 15% (OOS)
content = content.replace("test_ts = timestamps[split_idx + purge_bars :]", "test_ts = timestamps[:split_idx]")

# 2. Remove the hard regime gatekeeper we just added so we can see all regimes fail/succeed
content = content.replace("and str(row['hmm_regime']) in ['0', '4'] ", "")

with open('audit_insample_engine.py', 'w') as f:
    f.write(content)

print("In-Sample Simulator generated. Launching historical audit...")
print("(This may take a minute as it is processing the massive 85% training block)")

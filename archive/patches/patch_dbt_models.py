import os

res_filter = """
) AS base_query
WHERE entry_price > 0.000001
  AND stop_loss_1_5_atr > 0
  AND exact_gross_return BETWEEN -0.99 AND 2.0
"""

feat_filter = """
) AS base_query
WHERE close > 0.000001
  AND atr_20 < (close * 0.5)
"""

def apply_subquery_wrapper(filepath, filter_sql):
    with open(filepath, 'r') as f:
        content = f.read().strip()
        
    if ") AS base_query" in content:
        print(f"Skipping {filepath} (already patched).")
        return
        
    # Wrap original SQL safely in a subquery
    new_content = f"SELECT * FROM (\n{content}\n{filter_sql}"
    
    with open(filepath, 'w') as f:
        f.write(new_content)
    print(f"Successfully patched: {filepath}")

found_res = False
found_feat = False

for root, dirs, files in os.walk('.'):
    # Skip python environments or heavy hidden dirs
    if 'venv' in root or '.git' in root or 'target' in root:
        continue
        
    for file in files:
        if file == 'fct_exact_path_resolution.sql':
            apply_subquery_wrapper(os.path.join(root, file), res_filter)
            found_res = True
        elif file == 'fct_4h_features_tbm.sql':
            apply_subquery_wrapper(os.path.join(root, file), feat_filter)
            found_feat = True

if not found_res: print("Warning: Could not find fct_exact_path_resolution.sql")
if not found_feat: print("Warning: Could not find fct_4h_features_tbm.sql")
print("\nSQL Patching Complete. Ready for dbt rebuild.")

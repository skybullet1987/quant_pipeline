import os

file_path = "/home/skybullet1987/quant_pipeline/crypto_features/models/fct_4h_features_tbm.sql"

with open(file_path, "r") as f:
    content = f.read()

# 1. Update the configuration block
if "materialized='table'" in content:
    content = content.replace(
        "materialized='table'", 
        "materialized='incremental',\n    unique_key=['timestamp', 'ticker']"
    )

# 2. Inject the incremental lookback filter into the raw_4h CTE
target_str = "WHERE timestamp IS NOT NULL"
incremental_logic = """WHERE timestamp IS NOT NULL
  {% if is_incremental() %}
    AND timestamp >= TIMESTAMP_SUB((SELECT MAX(timestamp) FROM {{ this }}), INTERVAL 25 DAY)
  {% endif %}"""

if "{% if is_incremental() %}" not in content:
    content = content.replace(target_str, incremental_logic, 1)

with open(file_path, "w") as f:
    f.write(content)

print("[SUCCESS] fct_4h_features_tbm.sql has been upgraded to an incremental model.")

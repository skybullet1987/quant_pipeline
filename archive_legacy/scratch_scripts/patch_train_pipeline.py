#!/usr/bin/env python3
import json
import shutil
import py_compile
from datetime import datetime, timezone

TARGET_FILE = "train_production_models.py"
BACKUP_FILE = f"train_production_models.py.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

shutil.copyfile(TARGET_FILE, BACKUP_FILE)
print(f"[BACKUP] Created: {BACKUP_FILE}")

with open("production_models/feature_schema_clean.json", "r") as f:
    schema = json.load(f)

clean_features = schema["feature_names"]
clean_cat_cols = schema["categorical_features"]

with open(TARGET_FILE, "r") as f:
    code = f.read()

# Replace hardcoded feature lists if defined at the top
feat_decl = f"""# --- CLEAN 25-FEATURE PRODUCTION SCHEMA ---
ALL_FEATURES = {json.dumps(clean_features, indent=4)}

ALL_CAT_COLS = {json.dumps(clean_cat_cols, indent=4)}
"""

# Replace all_features definition or update feature_names list
if "ALL_FEATURES =" in code or "all_features =" in code:
    import re
    code = re.sub(r"(?i)all_features\s*=\s*\[.*?\]", f"all_features = {json.dumps(clean_features)}", code, flags=re.DOTALL)
    code = re.sub(r"(?i)all_cat_cols\s*=\s*\[.*?\]", f"all_cat_cols = {json.dumps(clean_cat_cols)}", code, flags=re.DOTALL)
else:
    # Insert near top of file
    import_idx = code.find("import ")
    code = code[:import_idx] + feat_decl + "\n" + code[import_idx:]

with open(TARGET_FILE, "w") as f:
    f.write(code)

py_compile.compile(TARGET_FILE, doraise=True)
print("[SUCCESS] Patched and validated train_production_models.py with clean 25-feature schema.")

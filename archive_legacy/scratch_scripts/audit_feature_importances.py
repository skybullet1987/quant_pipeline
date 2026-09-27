#!/usr/bin/env python3
import os
import pandas as pd
from catboost import CatBoostClassifier

MODEL_DIR = "production_models"
expert_files = [f for f in os.listdir(MODEL_DIR) if f.endswith("_expert.cbm")]

importance_data = {}

for ef in sorted(expert_files):
    model_path = os.path.join(MODEL_DIR, ef)
    model = CatBoostClassifier()
    model.load_model(model_path)
    
    importances = model.get_feature_importance()
    model_features = model.feature_names_
    model_name = ef.replace(".cbm", "")
    importance_data[model_name] = pd.Series(importances, index=model_features)

df_imp = pd.DataFrame(importance_data)
df_imp["Mean_Importance"] = df_imp.mean(axis=1)
df_imp = df_imp.sort_values("Mean_Importance", ascending=False)

print("\n" + "=" * 85)
print("             TOP 20 ALPHA DRIVERS ACROSS REGIME EXPERTS")
print("=" * 85)
print(df_imp[["Mean_Importance"]].head(20).to_string(formatters={"Mean_Importance": "{:.2f}%".format}))

print("\n" + "=" * 85)
print("             BOTTOM 5 CANDIDATES FOR NOISE PRUNING")
print("=" * 85)
print(df_imp[["Mean_Importance"]].tail(5).to_string(formatters={"Mean_Importance": "{:.2f}%".format}))
print("=" * 85 + "\n")

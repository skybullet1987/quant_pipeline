import pandas as pd
import numpy as np
from optimizer_cache import load_and_cache_dataset

train_bars, train_dict, oos_bars, oos_dict = load_and_cache_dataset(270, 90)
all_dicts = train_dict + oos_dict

records = []
for b_idx, b_dict in enumerate(all_dicts):
    for sym, r in b_dict.items():
        records.append({
            "ticker": sym,
            "regime": r["regime"],
            "p_long": r["p_long"],
            "p_short": r["p_short"],
            "p_chop": r["p_chop"],
            "close": r["close"],
            "high": r["high"],
            "low": r["low"],
            "atr": r["atr"]
        })

df = pd.DataFrame(records)

print("\n" + "=" * 80)
print("             CATBOOST PROBABILITY DISTRIBUTION & DECILE BREAKDOWN             ")
print("=" * 80)

print("\n1. SUMMARY QUANTILES:")
print(df[["p_long", "p_short", "p_chop"]].quantile([0.50, 0.75, 0.90, 0.95, 0.99]))

df["p_long_bucket"] = pd.qcut(df["p_long"], q=5, duplicates="drop")
df["p_short_bucket"] = pd.qcut(df["p_short"], q=5, duplicates="drop")

print("\n2. LONG PROBABILITY BUCKET COUNTS:")
print(df["p_long_bucket"].value_axis() if hasattr(df["p_long_bucket"], "value_axis") else df["p_long_bucket"].value_counts().sort_index())

print("\n3. SHORT PROBABILITY BUCKET COUNTS:")
print(df["p_short_bucket"].value_counts().sort_index())
print("=" * 80)

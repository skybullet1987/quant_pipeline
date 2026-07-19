import pandas as pd
from google.cloud import bigquery
from catboost import CatBoostRanker, Pool

# --- Configuration ---
PROJECT_ID = "parnasa-498503"
MODEL_PATH = "/home/skybullet1987/quant_pipeline/live_model.cbm"

print("1. Fetching Feature Matrix from BigQuery...")
bq_client = bigquery.Client(project=PROJECT_ID)

# We pull the data, sorting by timestamp to ensure chronological grouping for the Ranker
query = f"""
    SELECT 
        timestamp,
        ticker,
        vol_norm_momentum_15m,
        cross_sectional_momentum_rank,
        target_forward_return_15m
    FROM `{PROJECT_ID}.market_data.features_matrix`
    WHERE target_forward_return_15m IS NOT NULL
    ORDER BY timestamp ASC
"""
df = bq_client.query(query).to_dataframe()

print(f"   Successfully loaded {len(df)} rows.")

print("2. Preparing Data for YetiRank...")
# CatBoost requires groups to be sequential. 
# We map timestamps to a group ID.
group_ids = df.groupby('timestamp').ngroup()

# Define features (X) and target (y)
X = df[['vol_norm_momentum_15m', 'cross_sectional_momentum_rank']]
y = df['target_forward_return_15m']

# Create the CatBoost Pool
train_pool = Pool(
    data=X,
    label=y,
    group_id=group_ids
)

print("3. Initializing CatBoostRanker...")
# YetiRank optimizes the ranking quality.
# We use a modest iteration count and learning rate to prevent overfitting the noisy crypto data.
model = CatBoostRanker(
    loss_function='YetiRank',
    iterations=500,
    learning_rate=0.05,
    depth=6,
    train_dir='/tmp/catboost_info',
    verbose=50
)

print("4. Training Model (This may take a few minutes)...")
model.fit(train_pool)

print(f"5. Saving production model to {MODEL_PATH}")
model.save_model(MODEL_PATH)
print("Training Complete. Model is ready for live execution.")

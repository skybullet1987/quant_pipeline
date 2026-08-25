from typing import List
import lightgbm as lgb
import polars as pl

class CrossSectionalLambdaRanker:
    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names
        self.model = None

    def fit(self, train_df: pl.DataFrame, val_df: pl.DataFrame = None):
        train_clean = train_df.drop_nulls(subset=self.feature_names + ["ranking_target"])
        train_groups = train_clean.group_by("timestamp", maintain_order=True).len()["len"].to_numpy()
        X_train = train_clean.select(self.feature_names).to_numpy()
        y_train = train_clean["ranking_target"].to_numpy()

        train_data = lgb.Dataset(X_train, label=y_train, group=train_groups)
        valid_data = None

        if val_df is not None:
            val_clean = val_df.drop_nulls(subset=self.feature_names + ["ranking_target"])
            val_groups = val_clean.group_by("timestamp", maintain_order=True).len()["len"].to_numpy()
            X_val = val_clean.select(self.feature_names).to_numpy()
            y_val = val_clean["ranking_target"].to_numpy()
            valid_data = lgb.Dataset(X_val, label=y_val, group=val_groups, reference=train_data)

        params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [3, 5],
            "learning_rate": 0.03,
            "num_leaves": 31,
            "min_data_in_leaf": 50,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 1,
            "verbosity": -1,
            "random_state": 42
        }

        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=600,
            valid_sets=[valid_data] if valid_data else None,
            callbacks=[lgb.early_stopping(stopping_rounds=40, verbose=False)] if valid_data else []
        )

    def predict_ranks(self, df: pl.DataFrame) -> pl.Series:
        X = df.select(self.feature_names).fill_nan(0.0).fill_null(0.0).to_numpy()
        raw_scores = self.model.predict(X)
        return pl.Series("predicted_rank_score", raw_scores)

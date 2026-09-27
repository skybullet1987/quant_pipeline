import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.linear_model import Ridge

class CrossSectionalAlphaRanker:
    def __init__(self, objective: str = "lambdarank", top_k: int = 10):
        self.objective = objective
        self.top_k = top_k
        self.model = None

    @staticmethod
    def residualize_returns(df: pl.DataFrame, window: int = 36) -> pl.DataFrame:
        sym_col = "symbol" if "symbol" in df.columns else "ticker"
        ts_col = "timestamp_4h" if "timestamp_4h" in df.columns else "timestamp_ms" if "timestamp_ms" in df.columns else "timestamp"
        
        # Ensure ret_4h exists
        if "ret_4h" not in df.columns:
            df = df.sort([sym_col, ts_col]).with_columns(
                (pl.col("close") / pl.col("close").shift(1).over(sym_col) - 1.0).alias("ret_4h")
            )

        # BTC return resolution
        btc_col = None
        for candidate in ["btc_ret", "btc_ret_4h", "btc_ret_1h"]:
            if candidate in df.columns:
                btc_col = candidate
                break

        # Fallback if BTC return column missing
        if btc_col is None:
            btc_sub = df.filter(pl.col(sym_col).is_in(["BTC", "BTCUSDT", "BTC-PERP"])).select([ts_col, pl.col("ret_4h").alias("btc_ret")]).unique(subset=[ts_col])
            if btc_sub.height > 0:
                df = df.join(btc_sub, on=ts_col, how="left")
                btc_col = "btc_ret"
            else:
                # If no BTC ticker found, synthesize market mean return
                mkt_ret = df.group_by(ts_col).agg(pl.col("ret_4h").mean().alias("btc_ret"))
                df = df.join(mkt_ret, on=ts_col, how="left")
                btc_col = "btc_ret"

        # Optional ETH return
        eth_col = None
        for candidate in ["eth_ret", "eth_ret_4h"]:
            if candidate in df.columns:
                eth_col = candidate
                break

        # Vectorized rolling beta computation: Cov(r_i, r_btc) / Var(r_btc)
        df = df.sort([sym_col, ts_col]).with_columns([
            (
                (
                    (pl.col("ret_4h") * pl.col(btc_col)).rolling_mean(window_size=window).over(sym_col) -
                    (pl.col("ret_4h").rolling_mean(window_size=window).over(sym_col) * pl.col(btc_col).rolling_mean(window_size=window).over(sym_col))
                ) /
                (
                    (pl.col(btc_col) ** 2).rolling_mean(window_size=window).over(sym_col) -
                    (pl.col(btc_col).rolling_mean(window_size=window).over(sym_col) ** 2) + 1e-8
                )
            ).fill_null(1.0).alias("_rolling_beta")
        ])

        df = df.with_columns(
            (pl.col("ret_4h") - pl.col("_rolling_beta") * pl.col(btc_col)).alias("residual_return")
        ).drop(["_rolling_beta"])

        return df

    def train_lambdarank(
        self,
        train_df: pl.DataFrame,
        feature_cols: list[str],
        label_col: str = "forward_res_decile"
    ):
        ts_col = "timestamp_4h" if "timestamp_4h" in train_df.columns else "timestamp_ms" if "timestamp_ms" in train_df.columns else "timestamp"
        train_df = train_df.sort(ts_col)
        groups = train_df.group_by(ts_col, maintain_order=True).len()["len"].to_numpy()
        
        # Ensure available feature columns
        valid_cols = [c for c in feature_cols if c in train_df.columns]
        if not valid_cols:
            raise ValueError(f"No valid feature columns found in {feature_cols}")

        X = train_df.select(valid_cols).to_pandas().fillna(0.0)
        y = train_df.select(label_col).to_pandas().to_numpy().ravel()

        train_data = lgb.Dataset(X, label=y, group=groups)
        params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [self.top_k],
            "learning_rate": 0.03,
            "num_leaves": 31,
            "min_data_in_leaf": max(5, min(20, len(X) // 10)),
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 1,
            "verbose": -1,
            "random_state": 42
        }

        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=100
        )
        return self

    def rank_universe(self, current_df: pl.DataFrame, feature_cols: list[str]) -> pl.DataFrame:
        if self.model is None:
            raise ValueError("Model is not trained.")
        
        valid_cols = [c for c in feature_cols if c in current_df.columns]
        X = current_df.select(valid_cols).to_pandas().fillna(0.0)
        scores = self.model.predict(X)
        
        ranked_df = current_df.with_columns([
            pl.Series(name="predicted_score", values=scores),
            pl.Series(name="predicted_rank_score", values=scores),
            pl.Series(name="alpha_score", values=scores),
        ]).sort("predicted_score", descending=True)
        
        n_assets = len(ranked_df)
        decile_size = max(1, n_assets // 10)
        
        return ranked_df.with_columns([
            pl.Series(name="rank", values=np.arange(1, n_assets + 1)),
            pl.when(pl.int_range(0, n_assets) < decile_size)
            .then(pl.lit("LONG_D10"))
            .when(pl.int_range(0, n_assets) >= (n_assets - decile_size))
            .then(pl.lit("SHORT_D1"))
            .otherwise(pl.lit("NEUTRAL"))
            .alias("basket_assignment")
        ])

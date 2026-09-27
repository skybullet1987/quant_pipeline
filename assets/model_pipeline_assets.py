import os
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from dagster import asset, AssetExecutionContext, Output, MetadataValue
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
MODEL_PATH = os.path.expanduser("~/quant_pipeline/models/artifacts/catboost_macro_interaction_v2.cbm")
EXCLUDE_TICKERS = ["PAXGUSD", "USDCUSD", "USDTUSD", "FDUSDUSD", "EURUSD", "TUSDUSD"]

FEATURE_COLS = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p", "macro_expansion_score", "expansion_quintile"
]

AUDIT_COLS = [
    "timestamp", "ticker", "close", "atr_20", "mom_24h", "dist_ema20_atr",
    "macro_expansion_score", "expansion_quintile", "p_long", "active_hurdle",
    "is_eligible", "execution_action"
]


@asset(group_name="ml_execution")
def fct_4h_model_signals(context: AssetExecutionContext) -> Output[pd.DataFrame]:
    """Scores latest 4H bar features with CatBoost v2 and calibrated P95 regime hurdles."""
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
    SELECT *
    FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    WHERE timestamp = (
        SELECT MAX(timestamp) 
        FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    )
    """
    df_live = client.query(query).to_dataframe()
    if df_live.empty:
        context.log.warning("No data found for latest 4H bar.")
        return Output(pd.DataFrame(), metadata={"status": "NO_DATA"})

    latest_ts = str(df_live["timestamp"].iloc[0])
    context.log.info(f"Scoring {len(df_live)} assets for bar: {latest_ts}")

    # Universe hygiene: Filter pegged and stable assets
    df_live = df_live[~df_live["ticker"].isin(EXCLUDE_TICKERS)].copy()

    model = CatBoostClassifier()
    model.load_model(MODEL_PATH)

    df_features = df_live.dropna(subset=FEATURE_COLS).copy()
    df_features["p_long"] = model.predict_proba(df_features[FEATURE_COLS])[:, 1]

    # P95 Calibrated Dynamic Hurdles
    df_features["active_hurdle"] = np.where(
        df_features["expansion_quintile"] == 1, 0.4493,
        np.where(df_features["expansion_quintile"] == 5, 0.4893, 0.5500)
    )
    df_features["is_eligible"] = df_features["p_long"] >= df_features["active_hurdle"]
    df_features["execution_action"] = np.where(df_features["is_eligible"], "DISPATCH_TRADE", "PRESERVE_CASH")

    scored_df = df_features.sort_values("p_long", ascending=False).reset_index(drop=True)
    top_candidate = scored_df.iloc[0]

    # Persist audit record to BigQuery
    dest_table = f"{PROJECT_ID}.market_data.fct_4h_model_signals"
    audit_df = scored_df[AUDIT_COLS].copy()

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        time_partitioning=bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY, field="timestamp")
    )
    client.load_table_from_dataframe(audit_df, dest_table, job_config=job_config).result()

    metadata = {
        "timestamp": latest_ts,
        "regime": f"Q{int(top_candidate['expansion_quintile'])}",
        "macro_expansion_score": float(top_candidate["macro_expansion_score"]),
        "top_ticker": str(top_candidate["ticker"]),
        "top_p_long": float(top_candidate["p_long"]),
        "active_hurdle": float(top_candidate["active_hurdle"]),
        "action": str(top_candidate["execution_action"]),
        "eligible_count": int(scored_df["is_eligible"].sum())
    }

    return Output(scored_df, metadata=metadata)


@asset(deps=[fct_4h_model_signals], group_name="ml_execution")
def dispatched_trading_orders(context: AssetExecutionContext) -> Output[dict]:
    """Evaluates top candidates against risk parameters and routes shadow/live orders."""
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
    SELECT *
    FROM `{PROJECT_ID}.market_data.fct_4h_model_signals`
    WHERE timestamp = (
        SELECT MAX(timestamp) 
        FROM `{PROJECT_ID}.market_data.fct_4h_model_signals`
    )
    ORDER BY p_long DESC
    """
    df_signals = client.query(query).to_dataframe()
    if df_signals.empty:
        return Output({}, metadata={"status": "NO_SIGNALS"})

    latest_bar = str(df_signals["timestamp"].iloc[0])
    regime = int(df_signals["expansion_quintile"].iloc[0])
    macro_score = float(df_signals["macro_expansion_score"].iloc[0])

    eligible = df_signals[df_signals["is_eligible"] == True].head(2)

    if eligible.empty:
        context.log.info(f"[{latest_bar} | Q{regime}] No candidates cleared active hurdle. Capital preserved in 100% Cash.")
        return Output(
            {"action": "PRESERVE_CASH", "orders": []},
            metadata={"status": "100% Cash Preserved", "regime": f"Q{regime}", "macro_score": macro_score}
        )

    dispatched = []
    for rank, (_, row) in enumerate(eligible.iterrows(), 1):
        ticker = row["ticker"]
        entry_price = float(row["close"])
        atr = float(row["atr_20"])
        p_long = float(row["p_long"])
        hurdle = float(row["active_hurdle"])

        stop_loss = round(entry_price - (1.0 * atr), 4)
        take_profit = round(entry_price + (1.8 * atr), 4)

        order_data = {
            "rank": rank,
            "ticker": ticker,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "p_long": p_long,
            "hurdle": hurdle,
            "mode": "SHADOW_AUDIT"
        }
        dispatched.append(order_data)
        context.log.info(
            f"DISPATCH [{ticker}]: P={p_long:.4f} >= {hurdle:.4f} | Entry=${entry_price:,.4f} | "
            f"SL=${stop_loss:,.4f} | TP=${take_profit:,.4f} (Horizon: 72H)"
        )

    return Output(
        {"action": "DISPATCH_TRADE", "orders": dispatched},
        metadata={
            "dispatched_count": len(dispatched),
            "orders": MetadataValue.json(dispatched)
        }
    )

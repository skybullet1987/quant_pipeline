import os
import polars as pl
from dagster import asset, AssetExecutionContext
from google.cloud import bigquery

from src.models.hmm_regime import HMMRegimeGovernor
from src.models.ranker import CrossSectionalAlphaRanker
from src.portfolio.risk_governor import MacroRiskGovernor
from src.portfolio.allocator import DollarNeutralRiskParityAllocator
from src.execution.hyperliquid_executor import HyperliquidExecutionEngine

@asset(group_name="quantitative_alpha")
def feature_mart_4h(context: AssetExecutionContext) -> pl.DataFrame:
    client = bigquery.Client(project=os.getenv("GCP_PROJECT"))
    query = """
        SELECT * FROM `quant_marts.fct_4h_features_production`
        WHERE timestamp_4h >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
        ORDER BY timestamp_4h ASC
    """
    df_pd = client.query(query).to_dataframe()
    return pl.from_pandas(df_pd)

@asset(group_name="quantitative_alpha")
def portfolio_rebalance_orders(context: AssetExecutionContext, feature_mart_4h: pl.DataFrame) -> pl.DataFrame:
    macro_df = feature_mart_4h.group_by("timestamp_4h").agg([
        pl.col("ret_4h").std().alias("csd"),
        (pl.col("close_4h") > pl.col("open_4h")).mean().alias("breadth"),
        pl.col("btc_ret").first().alias("btc_ret")
    ]).sort("timestamp_4h")
    
    hmm_features = macro_df.select(["csd", "breadth", "btc_ret"]).to_numpy()
    hmm_gov = HMMRegimeGovernor().fit(hmm_features[:-1])
    active_state, omega_h = hmm_gov.compute_regime_entropy(hmm_features[-1])
    
    latest_macro = macro_df.tail(1)
    macro_risk = MacroRiskGovernor()
    macro_scale = macro_risk.compute_macro_governor(
        breadth=float(latest_macro["breadth"][0]),
        cross_sectional_dispersion=float(latest_macro["csd"][0]),
        volatility_zscore=0.0,
        omega_h=omega_h
    )
    
    ranker = CrossSectionalAlphaRanker()
    res_df = ranker.residualize_returns(feature_mart_4h)
    latest_ts = res_df["timestamp_4h"].max()
    current_snapshot = res_df.filter(pl.col("timestamp_4h") == latest_ts)
    
    feat_cols = ["residual_return", "sigma_gk_20p", "vcr_20_120", "mom_acc"]
    
    train_snapshot = res_df.filter(pl.col("timestamp_4h") < latest_ts).with_columns(
        (pl.col("residual_return") > 0).cast(pl.Int32).alias("forward_res_decile")
    )
    ranker.train_lambdarank(train_snapshot, feat_cols)
    ranked = ranker.rank_universe(current_snapshot, feat_cols)
    
    allocator = DollarNeutralRiskParityAllocator()
    total_nav = float(os.getenv("ACCOUNT_NAV_USD", "100000"))
    allocated_orders = allocator.allocate(ranked, total_nav_usd=total_nav, macro_scalar=macro_scale)
    
    context.log.info(f"Generated {len(allocated_orders)} portfolio allocation orders. Macro Scale: {macro_scale:.2f}")
    return allocated_orders

@asset(group_name="quantitative_alpha")
def execute_hyperliquid_alo(context: AssetExecutionContext, portfolio_rebalance_orders: pl.DataFrame) -> dict:
    executor = HyperliquidExecutionEngine(
        base_url=os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz"),
        master_vault_address=os.getenv("HYPERLIQUID_VAULT_ADDRESS"),
        agent_private_key=os.getenv("HYPERLIQUID_AGENT_KEY")
    )
    
    order_list = []
    for row in portfolio_rebalance_orders.iter_rows(named=True):
        order_list.append({
            "asset_idx": row.get("asset_idx", 0),
            "is_buy": (row["order_side"] == "BUY"),
            "limit_price": row["close_4h"],
            "size_qty": row["target_qty"]
        })
        
    result = executor.dispatch_batch_alo_orders(order_list)
    context.log.info(f"Execution response: {result}")
    return result

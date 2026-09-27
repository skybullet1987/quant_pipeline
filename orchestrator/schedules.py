from dagster import ScheduleDefinition, define_asset_job

alpha_rebalance_job = define_asset_job(
    "alpha_4h_rebalance_job", 
    selection=["feature_mart_4h", "portfolio_rebalance_orders", "execute_hyperliquid_alo"]
)

rebalance_schedule = ScheduleDefinition(
    job=alpha_rebalance_job,
    cron_schedule="1 0,4,8,12,16,20 * * *",
    execution_timezone="UTC"
)

from dagster import (
    Definitions,
    define_asset_job,
    ScheduleDefinition,
    load_assets_from_modules,
    AssetSelection
)
from assets import model_pipeline_assets

ml_assets = load_assets_from_modules([model_pipeline_assets])

# Select all assets in the ml_execution asset group
execution_job = define_asset_job(
    name="run_4h_quant_pipeline",
    selection=AssetSelection.groups("ml_execution")
)

# 4H execution schedule: 5 minutes past every 4-hour bar UTC
four_hour_schedule = ScheduleDefinition(
    job=execution_job,
    cron_schedule="5 0,4,8,12,16,20 * * *",
    execution_timezone="UTC"
)

defs = Definitions(
    assets=[*ml_assets],
    jobs=[execution_job],
    schedules=[four_hour_schedule],
)

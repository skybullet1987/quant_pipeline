import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", force=True)

PROJECT_ID = "parnasa-498503"
TABLE_ID = f"{PROJECT_ID}.market_data.fct_timesfm_forecasts"

def run_daily_forecast():
    client = bigquery.Client(project=PROJECT_ID)
    
    sql = f"""
    INSERT INTO `{TABLE_ID}`
    SELECT 
        ticker, 
        forecast_timestamp, 
        forecast_value, 
        confidence_level, 
        prediction_interval_lower_bound, 
        prediction_interval_upper_bound,
        SAFE_DIVIDE(prediction_interval_upper_bound - prediction_interval_lower_bound, 3.92) AS standard_error
    FROM AI.FORECAST(
      TABLE `{PROJECT_ID}.market_data.stg_densified_ohlcv`,
      data_col => 'close',
      timestamp_col => 'timestamp',
      id_cols => ['ticker'],
      model => 'TimesFM 2.5',
      horizon => 18
    )
    """
    
    logging.info("Executing daily TimesFM 2.5 batch forecast...")
    job = client.query(sql)
    job.result()
    logging.info("Daily TimesFM forecast successfully appended!")

if __name__ == "__main__":
    run_daily_forecast()

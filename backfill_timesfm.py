import logging
import time
from datetime import datetime, timedelta
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", force=True)

PROJECT_ID = "parnasa-498503"
TABLE_ID = f"{PROJECT_ID}.market_data.fct_timesfm_forecasts"

def run_historical_backfill():
    client = bigquery.Client(project=PROJECT_ID)
    
    # 1. Initialize the target table
    logging.info("Initializing fct_timesfm_forecasts table...")
    init_sql = f"""
    CREATE OR REPLACE TABLE `{TABLE_ID}` (
        ticker STRING,
        forecast_timestamp TIMESTAMP,
        forecast_value FLOAT64,
        confidence_level FLOAT64,
        prediction_interval_lower_bound FLOAT64,
        prediction_interval_upper_bound FLOAT64,
        standard_error FLOAT64
    ) PARTITION BY DATE(forecast_timestamp) CLUSTER BY ticker;
    """
    client.query(init_sql).result()
    
    # 2. Get date boundaries
    bounds_sql = f"SELECT MIN(timestamp) as min_ts, MAX(timestamp) as max_ts FROM `{PROJECT_ID}.market_data.stg_densified_ohlcv`"
    bounds = list(client.query(bounds_sql).result())[0]
    
    start_date = bounds.min_ts + timedelta(days=60)
    end_date = bounds.max_ts
    
    current_cutoff = start_date
    step_days = 7
    horizon = step_days * 6  # 4H candles = 6 per day. Horizon = 42
    
    logging.info(f"Starting rolling backfill from {start_date} to {end_date}")
    logging.info(f"Step: {step_days} days | Horizon: {horizon} periods")
    
    # 3. Rolling backfill loop
    while current_cutoff < end_date:
        cutoff_str = current_cutoff.strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"Generating forecasts for cutoff: {cutoff_str} ...")
        
        insert_sql = f"""
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
          (SELECT * FROM `{PROJECT_ID}.market_data.stg_densified_ohlcv` WHERE timestamp <= TIMESTAMP('{cutoff_str}')),
          data_col => 'close',
          timestamp_col => 'timestamp',
          id_cols => ['ticker'],
          model => 'TimesFM 2.5',
          horizon => {horizon}
        )
        """
        try:
            client.query(insert_sql).result()
        except Exception as e:
            logging.error(f"Error at cutoff {cutoff_str}: {e}")
            logging.info("Cooling down before retry...")
            time.sleep(15)
            client.query(insert_sql).result()
            
        current_cutoff += timedelta(days=step_days)
        time.sleep(1)

    logging.info("Full rolling TimesFM backfill complete!")

if __name__ == "__main__":
    run_historical_backfill()

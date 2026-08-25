import polars as pl
from google.cloud import bigquery
from src.config import settings

class BigQueryDataLoader:
    def __init__(self, project_id: str = settings.gcp_project_id):
        self.client = bigquery.Client(project=project_id)

    def load_ohlcv_universe(self, days: int = 365) -> pl.DataFrame:
        query = f"""
            SELECT 
                timestamp,
                UPPER(ticker) AS ticker,
                CAST(open AS FLOAT64) AS open,
                CAST(high AS FLOAT64) AS high,
                CAST(low AS FLOAT64) AS low,
                CAST(close AS FLOAT64) AS close,
                CAST(volume AS FLOAT64) AS volume
            FROM `{settings.gcp_project_id}.{settings.bq_dataset}.fct_4h_features_production`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
            ORDER BY timestamp ASC, ticker ASC
        """
        arrow_table = self.client.query(query).to_arrow()
        return pl.from_arrow(arrow_table)

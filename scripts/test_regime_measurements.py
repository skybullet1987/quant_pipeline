from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import polars as pl
from pipeline.research.regime_engine import compute_bocd_hazard_numba, ContinuousRegimeClassifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_regime_extraction():
    df = (
        pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")
        .unique(subset=["symbol", "bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
    )
    
    btc_df = df.filter(pl.col("symbol") == "BTC").sort("bucket_timestamp_utc")
    logger.info("Computing BOCD hazard and 3-State HMM posteriors on unique BTC 4H series (%d bars)...", btc_df.height)

    returns = btc_df["log_ret"].to_numpy().astype(float)
    volatility = btc_df["rolling_24h_volatility"].to_numpy().astype(float)

    # Numba BOCD Hazard
    hazard_probs = compute_bocd_hazard_numba(returns)

    # Continuous HMM
    classifier = ContinuousRegimeClassifier()
    posteriors = classifier.fit_predict_posteriors(returns, volatility)

    btc_enriched = btc_df.with_columns([
        pl.Series("p_hazard", hazard_probs.flatten().astype(float)),
        pl.Series("p_chop", posteriors[:, 0].flatten().astype(float)),
        pl.Series("p_trend", posteriors[:, 1].flatten().astype(float)),
        pl.Series("p_expansion", posteriors[:, 2].flatten().astype(float)),
    ])

    out_path = "/tmp/lake/features/btc_regime_state_4h.parquet"
    btc_enriched.write_parquet(out_path, compression="zstd")
    logger.info("Enriched regime state written -> %s", out_path)


if __name__ == "__main__":
    run_regime_extraction()

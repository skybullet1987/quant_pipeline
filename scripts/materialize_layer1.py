"""
Executes full Dagster Layer 1 Data Fabric materialization locally.
Validates GCS/Binance -> DQG Gate -> Regime Extraction -> MLflow Model Registration.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is present in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dagster import materialize
from pipeline.definitions import all_assets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline():
    logger.info("Initiating Layer 1 Data Fabric materialization...")
    result = materialize(all_assets)
    
    if result.success:
        logger.info("Successfully materialized all %d Layer 1 assets.", len(all_assets))
        for event in result.all_node_events:
            if event.is_step_success:
                logger.info("Step OK: %s", event.step_key)
    else:
        logger.error("Layer 1 Asset materialization encountered failures.")
        raise RuntimeError("Materialization failed.")


if __name__ == "__main__":
    run_pipeline()

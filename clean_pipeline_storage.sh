#!/usr/bin/env bash
DAGSTER_STORAGE="/home/skybullet1987/dagster_home/storage"
PROJECT_DIR="/home/skybullet1987/quant_pipeline"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting pipeline storage cleanup..."

# Prune Dagster run artifacts older than 14 days
if [ -d "$DAGSTER_STORAGE/history/runs" ]; then
    find "$DAGSTER_STORAGE/history/runs" -type f -mtime +14 -delete
    find "$DAGSTER_STORAGE/history/runs" -type d -empty -delete
fi

# Prune old backtest CSVs older than 30 days
find "$PROJECT_DIR" -maxdepth 1 -name "legacy_*.csv" -mtime +30 -delete

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Storage cleanup completed."

"""
Data Quality Gate (DQG) Engine.
Audits partitions for timestamp monotonicity, crossed/locked order books,
spread degradation, size anomalies, and stale feeds.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import polars as pl


class DQGState(str, Enum):
    VALID = "VALID"
    TEMP_LOCKED = "TEMP_LOCKED"
    CROSSED_INVALID = "CROSSED_INVALID"
    FUNDING_MISSING = "FUNDING_MISSING"
    STALE_FEED = "STALE_FEED"


@dataclass(frozen=True)
class DQGReport:
    total_records: int
    valid_records: int
    state_breakdown: dict[DQGState, int]
    max_gap_ms: int
    is_partition_accepted: bool
    rejection_reason: str | None = None


class DataQualityGate:
    def __init__(
        self,
        max_allowed_gap_ms: int = 5000,
        max_spread_pct: float = 0.05,
        max_crossed_ratio_tol: float = 0.0001
    ):
        self.max_allowed_gap_ms = max_allowed_gap_ms
        self.max_spread_pct = max_spread_pct
        self.max_crossed_ratio_tol = max_crossed_ratio_tol

    def validate_l2_snapshots(self, df: pl.DataFrame | pl.LazyFrame) -> tuple[pl.DataFrame, DQGReport]:
        lazy_df = df.lazy() if isinstance(df, pl.DataFrame) else df

        annotated = lazy_df.with_columns([
            (pl.col("timestamp_ms") - pl.col("timestamp_ms").shift(1)).fill_null(0).alias("delta_t_ms"),
            (pl.col("best_ask") - pl.col("best_bid")).alias("spread_absolute"),
            ((pl.col("best_ask") - pl.col("best_bid")) / pl.col("best_bid")).alias("spread_relative"),
        ]).with_columns(
            pl.when(pl.col("spread_absolute") < 0.0)
            .then(pl.lit(DQGState.CROSSED_INVALID.value))
            .when(pl.col("spread_absolute") == 0.0)
            .then(pl.lit(DQGState.TEMP_LOCKED.value))
            .when(pl.col("delta_t_ms") > self.max_allowed_gap_ms)
            .then(pl.lit(DQGState.STALE_FEED.value))
            .when((pl.col("spread_relative") > self.max_spread_pct) | (pl.col("best_bid") <= 0.0))
            .then(pl.lit(DQGState.CROSSED_INVALID.value))
            .otherwise(pl.lit(DQGState.VALID.value))
            .alias("dqg_state")
        )

        evaluated_df = annotated.collect(engine="streaming")

        counts = evaluated_df["dqg_state"].value_counts().to_dicts()
        state_map = {DQGState(r["dqg_state"]): r["count"] for r in counts}
        total_rows = evaluated_df.height
        valid_rows = state_map.get(DQGState.VALID, 0)
        crossed_rows = state_map.get(DQGState.CROSSED_INVALID, 0)
        
        max_gap = int(evaluated_df["delta_t_ms"].max() or 0)
        crossed_ratio = crossed_rows / total_rows if total_rows > 0 else 0.0
        is_accepted = (crossed_ratio <= self.max_crossed_ratio_tol) and (total_rows > 0)
        
        reason = None
        if not is_accepted:
            reason = f"Crossed book ratio {crossed_ratio:.6f} exceeded tolerance {self.max_crossed_ratio_tol}"

        report = DQGReport(
            total_records=total_rows,
            valid_records=valid_rows,
            state_breakdown=state_map,
            max_gap_ms=max_gap,
            is_partition_accepted=is_accepted,
            rejection_reason=reason
        )

        return evaluated_df, report

    def validate_trades(self, df: pl.DataFrame | pl.LazyFrame) -> tuple[pl.DataFrame, DQGReport]:
        lazy_df = df.lazy() if isinstance(df, pl.DataFrame) else df

        annotated = lazy_df.with_columns([
            (pl.col("timestamp_ms") - pl.col("timestamp_ms").shift(1)).fill_null(0).alias("delta_t_ms")
        ]).with_columns(
            pl.when(pl.col("delta_t_ms") < 0)
            .then(pl.lit(DQGState.CROSSED_INVALID.value))
            .when((pl.col("price") <= 0.0) | (pl.col("size") <= 0.0))
            .then(pl.lit(DQGState.CROSSED_INVALID.value))
            .when(pl.col("delta_t_ms") > self.max_allowed_gap_ms)
            .then(pl.lit(DQGState.STALE_FEED.value))
            .otherwise(pl.lit(DQGState.VALID.value))
            .alias("dqg_state")
        )

        evaluated_df = annotated.collect(engine="streaming")
        counts = evaluated_df["dqg_state"].value_counts().to_dicts()
        state_map = {DQGState(r["dqg_state"]): r["count"] for r in counts}
        total_rows = evaluated_df.height
        valid_rows = state_map.get(DQGState.VALID, 0)

        report = DQGReport(
            total_records=total_rows,
            valid_records=valid_rows,
            state_breakdown=state_map,
            max_gap_ms=int(evaluated_df["delta_t_ms"].max() or 0),
            is_partition_accepted=(valid_rows / total_rows >= 0.999) if total_rows > 0 else False,
            rejection_reason=None if total_rows > 0 else "Empty dataframe"
        )
        return evaluated_df, report

"""
Data Quality Gate (DQG) for Trade and Order Book streams.
Enforces tick monotonicity, detects crossed books, and filters corrupted records.
"""
from __future__ import annotations

from dataclasses import dataclass
import polars as pl


@dataclass(frozen=True)
class DQGAuditResult:
    total_records: int
    valid_records: int
    violating_records: int
    max_gap_ms: int = 0


class DataQualityGate:
    def __init__(self, max_allowed_gap_ms: int = 60_000):
        self.max_allowed_gap_ms = max_allowed_gap_ms

    def audit_and_clean_trade_stream(
        self, df: pl.DataFrame
    ) -> tuple[pl.DataFrame, DQGAuditResult]:
        total = df.height
        if total == 0:
            empty_clean = df.with_columns([
                pl.Series("delta_t_ms", [], dtype=pl.Int64),
                pl.Series("dqg_state", [], dtype=pl.Utf8),
            ])
            return empty_clean, DQGAuditResult(0, 0, 0, 0)

        # 1. Base validity: positive price, positive size, non-null fields
        base_valid_mask = (
            (pl.col("price") > 0.0)
            & (pl.col("size") > 0.0)
            & pl.col("timestamp_ms").is_not_null()
            & pl.col("symbol").is_not_null()
        )

        df_sorted = df.sort("timestamp_ms")
        
        # 2. Monotonicity & temporal gap calculation
        df_annotated = df_sorted.with_columns([
            (pl.col("timestamp_ms") - pl.col("timestamp_ms").shift(1).fill_null(pl.col("timestamp_ms").first()))
            .cast(pl.Int64)
            .alias("delta_t_ms"),
            pl.when(base_valid_mask)
            .then(pl.lit("VALID"))
            .otherwise(pl.lit("CORRUPT"))
            .alias("dqg_state"),
        ])

        df_clean = df_annotated.filter(pl.col("dqg_state") == "VALID")
        valid_count = df_clean.height
        violating_count = total - valid_count
        max_gap = int(df_clean["delta_t_ms"].max() or 0) if valid_count > 0 else 0

        audit = DQGAuditResult(
            total_records=total,
            valid_records=valid_count,
            violating_records=violating_count,
            max_gap_ms=max_gap,
        )
        return df_clean, audit

    @staticmethod
    def is_crossed_book(best_bid: float, best_ask: float) -> bool:
        """Returns True if best bid >= best ask (crossed/locked market anomaly)."""
        return bool(best_bid >= best_ask)

    @staticmethod
    def check_trade_monotonicity(timestamps: list[int] | pl.Series) -> bool:
        """Validates strictly non-decreasing timestamp sequence."""
        if isinstance(timestamps, list):
            ts_series = pl.Series(timestamps)
        else:
            ts_series = timestamps
        diffs = ts_series.diff().fill_null(0)
        return bool((diffs >= 0).all())

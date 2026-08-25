from typing import Generator, Tuple
import polars as pl

class PurgedWalkForwardCV:
    def __init__(self, n_splits: int = 4, purge_bars: int = 18):
        self.n_splits = n_splits
        self.purge_bars = purge_bars

    def split(self, df: pl.DataFrame) -> Generator[Tuple[pl.DataFrame, pl.DataFrame], None, None]:
        timestamps = df.select("timestamp").unique().sort("timestamp")["timestamp"].to_list()
        n_bars = len(timestamps)
        chunk_size = n_bars // (self.n_splits + 1)

        for i in range(1, self.n_splits + 1):
            train_end_idx = i * chunk_size
            test_start_idx = train_end_idx + self.purge_bars
            test_end_idx = min((i + 1) * chunk_size, n_bars - 1)

            if test_start_idx >= test_end_idx:
                break

            train_ts_max = timestamps[train_end_idx]
            test_ts_min = timestamps[test_start_idx]
            test_ts_max = timestamps[test_end_idx]

            train_df = df.filter(pl.col("timestamp") <= train_ts_max)
            test_df = df.filter((pl.col("timestamp") >= test_ts_min) & (pl.col("timestamp") <= test_ts_max))

            yield train_df, test_df

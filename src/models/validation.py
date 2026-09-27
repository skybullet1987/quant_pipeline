from typing import Generator
import polars as pl

class PurgedWalkForwardCV:
    def __init__(self, n_splits: int = 5, embargo_hours: int = 72, step_hours: int = 4):
        self.n_splits = n_splits
        self.embargo_periods = embargo_hours // step_hours

    def split(self, df: pl.DataFrame) -> Generator[tuple[pl.DataFrame, pl.DataFrame], None, None]:
        timestamps = df.select("timestamp_4h").unique().sort("timestamp_4h")["timestamp_4h"].to_list()
        n_times = len(timestamps)
        
        test_size = (n_times - self.embargo_periods) // (self.n_splits + 1)
        
        for i in range(1, self.n_splits + 1):
            train_end_idx = test_size * i
            test_start_idx = train_end_idx + self.embargo_periods
            test_end_idx = test_start_idx + test_size
            
            if test_end_idx > n_times:
                break
                
            train_cutoff = timestamps[train_end_idx]
            test_start = timestamps[test_start_idx]
            test_end = timestamps[test_end_idx - 1]
            
            train_df = df.filter(pl.col("timestamp_4h") <= train_cutoff)
            test_df = df.filter(
                (pl.col("timestamp_4h") >= test_start) & 
                (pl.col("timestamp_4h") <= test_end)
            )
            
            yield train_df, test_df

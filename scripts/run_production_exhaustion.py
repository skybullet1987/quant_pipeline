"""
Full-scale NautilusTrader Backtest for Asymmetric Exhaustion Alpha.
"""
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import polars as pl
from sklearn.linear_model import RidgeCV
import lightgbm as lgb
from catboost import CatBoostRegressor

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, RiskEngineConfig
from nautilus_trader.model.currencies import Currency, USD
from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.enums import (
    AccountType, AggregationSource, BarAggregation, OmsType, OrderStatus, PriceType
)
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity

from src.features.orthogonal_library import compute_orthogonal_features
from src.strategy.asymmetric_exhaustion_strategy import (
    AsymmetricExhaustionStrategy, AsymmetricExhaustionConfig
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def generate_exhaustion_alphas(df: pl.DataFrame) -> pd.DataFrame:
    """Generates out-of-fold exhaustion alphas using the full orthogonal feature library."""
    logger.info("Computing orthogonal feature families...")
    feat_df = compute_orthogonal_features(df)

    market_mean = (
        feat_df.group_by("bucket_timestamp_utc")
        .agg(pl.col("fwd_ret_24h").mean().alias("mkt_fwd_24h"))
    )

    pdf = (
        feat_df.join(market_mean, on="bucket_timestamp_utc")
        .with_columns([
            (pl.col("fwd_ret_24h") - pl.col("mkt_fwd_24h")).alias("target_excess_24h")
        ])
        .to_pandas()
    )

    feature_cols = [
        "cs_rank_ret_24h", "cs_rank_ret_72h", "cs_mom_acceleration_24_72",
        "cs_dist_to_universe_median_24h", "beta_btc_7d", "idio_residual_ret_btc_24h",
        "garman_klass_vol_ratio_24h", "normalized_atr_24h", "bollinger_keltner_squeeze_ratio_20",
        "clv_4h", "lower_wick_absorption_ratio_4h", "upper_wick_ratio_4h",
        "intrabar_wick_imbalance_4h", "cs_rank_volume_pct_24h",
        "interaction_mom_squeeze_24h", "interaction_breakout_thrust", "interaction_tbm_score",
    ]

    pdf = pdf.dropna(subset=feature_cols + ["target_excess_24h"])
    timestamps = pd.Series(pdf["bucket_timestamp_utc"].unique()).sort_values().reset_index(drop=True)

    logger.info("Training Out-of-Fold Exhaustion Ensemble (%d timestamps)...", len(timestamps))
    pdf["alpha_pred"] = 0.0

    for s in range(2160, len(timestamps), 720):
        e = min(s + 720, len(timestamps))
        tr_times = set(timestamps.iloc[:s])
        te_times = set(timestamps.iloc[s:e])

        tr_mask = pdf["bucket_timestamp_utc"].isin(tr_times)
        te_mask = pdf["bucket_timestamp_utc"].isin(te_times)

        X_tr = pdf.loc[tr_mask, feature_cols].values
        y_tr = pdf.loc[tr_mask, "target_excess_24h"].values
        X_te = pdf.loc[te_mask, feature_cols].values

        if len(X_te) == 0 or len(X_tr) == 0:
            continue

        ridge = RidgeCV(alphas=np.logspace(-2, 3, 10)).fit(X_tr, y_tr)
        lgbm = lgb.LGBMRegressor(n_estimators=40, max_depth=4, num_leaves=15, learning_rate=0.03, random_state=42, n_jobs=-1, verbose=-1).fit(X_tr, y_tr)
        cat = CatBoostRegressor(iterations=40, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0).fit(X_tr, y_tr)

        # Inverted prediction: Highest score = Q1 (Best Longs); Lowest score = Q5 (Best Shorts)
        raw_pred = 0.20 * ridge.predict(X_te) + 0.40 * lgbm.predict(X_te) + 0.40 * cat.predict(X_te)
        pdf.loc[te_mask, "alpha_pred"] = -raw_pred

    return pdf.pivot(index="bucket_timestamp_utc", columns="symbol", values="alpha_pred").fillna(0.0)


def create_instrument(symbol_str: str, venue: Venue) -> CryptoPerpetual:
    return CryptoPerpetual(
        instrument_id=InstrumentId(Symbol(f"{symbol_str}-USD-PERP"), venue),
        raw_symbol=Symbol(symbol_str),
        base_currency=Currency.from_str(symbol_str) if symbol_str != "USD" else USD,
        quote_currency=USD,
        settlement_currency=USD,
        is_inverse=False,
        price_precision=6,
        size_precision=4,
        price_increment=Price.from_str("0.000001"),
        size_increment=Quantity.from_str("0.0001"),
        lot_size=Quantity.from_str("0.0001"),
        max_quantity=Quantity.from_str("10000000.0"),
        min_quantity=Quantity.from_str("0.0001"),
        max_price=Price.from_str("1000000.0"),
        min_price=Price.from_str("0.000001"),
        margin_init=Decimal("0.05"),
        margin_maint=Decimal("0.025"),
        maker_fee=Decimal("0.0000"),
        taker_fee=Decimal("0.00035"),
        ts_event=0,
        ts_init=0,
    )


def run_pipeline():
    logger.info("Loading feature panel and BTC regime data...")
    raw_df = (
        pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")
        .unique(["symbol", "bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
    )
    regime_df = (
        pl.read_parquet("/tmp/lake/features/btc_regime_state_4h.parquet")
        .unique(["bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
        .to_pandas()
        .set_index("bucket_timestamp_utc")
    )

    alpha_df = generate_exhaustion_alphas(raw_df)

    symbols = raw_df["symbol"].unique().to_list()
    venue = Venue("HYPERLIQUID")
    bar_spec = BarSpecification(4, BarAggregation.HOUR, PriceType.LAST)

    engine = BacktestEngine(
        BacktestEngineConfig(
            trader_id="HYPERLIQUID-PROD-01",
            logging=LoggingConfig(log_level="WARNING"),
            risk_engine=RiskEngineConfig(
                max_order_submit_rate="50000/1s",
                max_order_modify_rate="50000/1s",
            ),
        )
    )

    initial_capital = 500.0
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(initial_capital, USD)],
    )

    instruments, ids_str = {}, []
    for s in symbols:
        inst = create_instrument(s, venue)
        instruments[s] = inst
        ids_str.append(str(inst.id))
        engine.add_instrument(inst)

    logger.info("Streaming %d bar events...", raw_df.height)
    pdf = raw_df.sort("bucket_timestamp_utc").to_pandas()
    bars = [
        Bar(
            BarType(instruments[r.symbol].id, bar_spec, AggregationSource.EXTERNAL),
            Price.from_str(f"{r.open:.6f}"),
            Price.from_str(f"{r.high:.6f}"),
            Price.from_str(f"{r.low:.6f}"),
            Price.from_str(f"{r.close:.6f}"),
            Quantity.from_str(f"{max(r.volume, 0.0001):.4f}"),
            int(pd.Timestamp(r.bucket_timestamp_utc).value),
            int(pd.Timestamp(r.bucket_timestamp_utc).value),
        )
        for r in pdf.itertuples()
    ]
    engine.add_data(bars)

    strat_cfg = AsymmetricExhaustionConfig(
        instrument_ids=ids_str,
        top_k=5,
        target_long_leverage=1.50,
        target_short_leverage=1.50,
        initial_cash=initial_capital,
    )
    engine.add_strategy(AsymmetricExhaustionStrategy(strat_cfg, alpha_df, regime_df))

    logger.info("Executing Asymmetric Exhaustion Simulation (2021-2026)...")
    engine.run()

    account = engine.portfolio.account(venue)
    final_bal = account.balance_total().as_double()
    filled = len(
        [
            o
            for o in engine.cache.orders()
            if o.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)
        ]
    )

    print("\n" + "=" * 70)
    print("   ASYMMETRIC EXHAUSTION NAUTILUS SIMULATION RESULTS ($500 CAPITAL)")
    print("=" * 70)
    print(f"Total Universe Symbols:      {len(symbols):12d}")
    print(f"Total Orders Filled:         {filled:12d}")
    print(f"Starting Capital:            ${initial_capital:12,.2f}")
    print(f"Final Account Balance:       ${final_bal:12,.2f}")
    print(f"Net PnL:                     ${final_bal - initial_capital:12,.2f}")
    print(f"Net Return:                  {((final_bal - initial_capital) / initial_capital) * 100:11.2f}%")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline()

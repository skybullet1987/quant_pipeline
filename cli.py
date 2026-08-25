import typer
from rich.console import Console
from rich.table import Table
import polars as pl

from src.config import settings
from src.data.bq_loader import BigQueryDataLoader
from src.features.engine import FeatureEngineeringEngine
from src.models.ranker import CrossSectionalLambdaRanker
from src.models.validation import PurgedWalkForwardCV
from src.portfolio.risk_governor import ContinuousRiskGovernor
from src.portfolio.allocator import DollarNeutralPortfolioAllocator
from src.execution.hyperliquid_executor import HyperliquidMakerExecutor

app = typer.Typer(help="Institutional Crypto Quant Engine CLI")
console = Console()

FEATURE_COLS = [
    "mom_24h", "mom_7d", "gk_vol_20p", "vol_compression_ratio",
    "dist_to_120p_high", "residual_momentum_zscore", "beta_btc"
]

@app.command()
def backtest(days: int = 365):
    """Runs Purged Walk-Forward Cross-Validation across historical 4H dataset."""
    console.print(f"[bold blue]--> Loading {days} days from BigQuery ({settings.bq_dataset})...[/bold blue]")
    loader = BigQueryDataLoader()
    df_raw = loader.load_ohlcv_universe(days=days)
    
    console.print("[bold yellow]--> Engineering Vectorized Polars Features & Residuals...[/bold yellow]")
    engine = FeatureEngineeringEngine(forward_horizon_bars=settings.forward_horizon_bars)
    df_feat = engine.compute_ohlcv_features(df_raw)
    df_res = engine.residualize_against_market(df_feat)
    df_target = engine.construct_ranking_targets(df_res)

    console.print("[bold green]--> Executing 4-Fold Purged Walk-Forward Cross-Validation...[/bold green]")
    cv = PurgedWalkForwardCV(n_splits=4, purge_bars=settings.purge_embargo_bars)
    
    table = Table(title="Purged Walk-Forward Ranking Performance")
    table.add_column("Fold", style="cyan")
    table.add_column("Train Bars", justify="right")
    table.add_column("Test Bars", justify="right")
    table.add_column("Top/Bottom Spread (Ann. bps)", justify="right", style="green")

    for idx, (train_df, test_df) in enumerate(cv.split(df_target), 1):
        ranker = CrossSectionalLambdaRanker(feature_names=FEATURE_COLS)
        ranker.fit(train_df, test_df)
        test_scored = test_df.with_columns(ranker.predict_ranks(test_df))
        
        test_clean = test_scored.drop_nulls(subset=["fwd_residual_ret", "ranking_target"])
        q4_ret = test_clean.filter(pl.col("ranking_target") == 4)["fwd_residual_ret"].mean() or 0.0
        q0_ret = test_clean.filter(pl.col("ranking_target") == 0)["fwd_residual_ret"].mean() or 0.0
        spread_bps = (q4_ret - q0_ret) * 10000.0

        table.add_row(f"Fold {idx}", f"{len(train_df):,}", f"{len(test_df):,}", f"{spread_bps:+.1f} bps")

    console.print(table)

@app.command()
def execute(dry_run: bool = True):
    """Executes live 4H portfolio cycle on Hyperliquid."""
    console.print("[bold magenta]--> Pulling live universe state & computing targets...[/bold magenta]")
    loader = BigQueryDataLoader()
    df_raw = loader.load_ohlcv_universe(days=30)
    
    engine = FeatureEngineeringEngine(forward_horizon_bars=settings.forward_horizon_bars)
    df_feat = engine.compute_ohlcv_features(df_raw)
    df_res = engine.residualize_against_market(df_feat)
    
    latest_ts = df_res["timestamp"].max()
    bar_df = df_res.filter(pl.col("timestamp") == latest_ts)

    ranker = CrossSectionalLambdaRanker(feature_names=FEATURE_COLS)
    ranker.fit(engine.construct_ranking_targets(df_res))
    bar_scored = bar_df.with_columns(ranker.predict_ranks(bar_df))

    macro_omega = ContinuousRiskGovernor.compute_exposure_scalar(bar_scored)
    allocator = DollarNeutralPortfolioAllocator(
        top_quantile=settings.top_quantile_selection,
        max_gross_leverage=settings.max_gross_leverage
    )

    orders = allocator.generate_orders(bar_scored, equity_usd=1000.0, macro_omega=macro_omega)

    console.print(f"\n[bold]Macro Risk Governor Omega:[/] {macro_omega:.2f}")
    console.print(f"[bold]Target Gross Leverage:[/] {orders['effective_gross_leverage']:.2f}x")
    console.print(f"[bold]Net Dollar Imbalance:[/] ${orders['net_dollar_exposure']:.2f}\n")

    if dry_run:
        console.print("[yellow][DRY RUN] Generated Long Basket:[/yellow]")
        for o in orders["long_basket"]:
            console.print(f"  • BUY  {o['ticker']:<8} | ${o['notional_usd']:>7.2f} @ ${o['price']:.4f}")
        console.print("[yellow][DRY RUN] Generated Short Basket:[/yellow]")
        for o in orders["short_basket"]:
            console.print(f"  • SELL {o['ticker']:<8} | ${o['notional_usd']:>7.2f} @ ${o['price']:.4f}")
    else:
        executor = HyperliquidMakerExecutor()
        executor.execute_post_only_rebalance(orders["long_basket"] + orders["short_basket"])

if __name__ == "__main__":
    app()

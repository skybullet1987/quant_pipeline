import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   EXPERIMENT 6: CONVEX TAIL DETECTOR & CONDITIONAL SKEWNESS AUDIT")
print("=" * 96)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

# 1. Forward Max Excursions over next 24H and 72H
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-24).over("symbol") / pl.col("close") - 1.0).alias("ret_fwd_24h"),
    (pl.col("close").shift(-72).over("symbol") / pl.col("close") - 1.0).alias("ret_fwd_72h"),
    # Rolling ATR proxy using Yang-Zhang volatility
    (pl.col("vol_yang_zhang") * pl.col("close")).alias("atr_proxy_1h")
])

# Max favorable and adverse excursion over next 24 hours
df = df.with_columns([
    ((pl.col("high").rolling_max(24).over("symbol").shift(-24) / pl.col("close")) - 1.0).alias("mfe_24h"),
    ((pl.col("low").rolling_min(24).over("symbol").shift(-24) / pl.col("close")) - 1.0).alias("mae_24h")
])

# 2. Candidate Convex Trigger Signals
df = df.with_columns([
    # Volume Shock
    (pl.col("volume_zscore_72h") > 2.2).alias("cond_vol_shock"),
    # Volatility / Range Expansion
    ((pl.col("vol_yang_zhang") / (pl.col("vol_yang_zhang").rolling_mean(72).over("symbol") + 1e-5)) > 1.6).alias("cond_range_expansion"),
    # Momentum Breakout
    (pl.col("ret_24h") > 0.08).alias("cond_mom_breakout"),
    # Funding Dislocation (High retail crowding)
    (pl.col("funding_apr") > 0.35).alias("cond_funding_spike")
])

valid = df.filter(
    (pl.col("dollar_volume_1h") > 50_000) &
    pl.col("mfe_24h").is_not_null() &
    pl.col("mae_24h").is_not_null() &
    pl.col("vol_yang_zhang").is_not_null()
)

print(f"[+] Total Audited Candidate Bars: {valid.height:,}")

# Baseline Unconditional Distribution
base_fwd = valid["ret_fwd_24h"].to_numpy()
base_mfe = valid["mfe_24h"].to_numpy()
base_mae = valid["mae_24h"].to_numpy()

def audit_trigger(name, filter_expr):
    subset = valid.filter(filter_expr)
    n = subset.height
    if n < 50:
        print(f"[-] {name}: Insufficient sample size (N={n})")
        return

    fwd = subset["ret_fwd_24h"].to_numpy()
    mfe = subset["mfe_24h"].to_numpy()
    mae = subset["mae_24h"].to_numpy()

    mean_ret = np.mean(fwd) * 100
    skew = float(subset.select(pl.col("ret_fwd_24h").skew()).to_numpy()[0, 0])
    
    # Asymmetry Ratio: Probability of > +10% gain vs < -5% loss
    p_gain_10 = np.mean(mfe > 0.10) * 100
    p_loss_5 = np.mean(mae < -0.05) * 100
    asym_ratio = p_gain_10 / (p_loss_5 + 1e-5)

    # Tail Outliers: Frequency of +25% runners
    p_gain_25 = np.mean(mfe > 0.25) * 100

    print(f"{name:<35} | N={n:>5} | Mean 24H: {mean_ret:>+5.2f}% | Skew: {skew:>+4.2f} | P(MFE>10%): {p_gain_10:>4.1f}% | P(MAE<-5%): {p_loss_5:>4.1f}% | Asym: {asym_ratio:>4.2f} | P(MFE>25%): {p_gain_25:>4.1f}%")

print("\n" + "=" * 96)
print("       CONDITIONAL SKEWNESS & ASYMMETRIC TAIL PAYOFF AUDIT (24H HORIZON)")
print("=" * 96)
print(f"{'Trigger Strategy':<35} | {'Samples':<7} | {'Mean 24H':<13} | {'Skew':<10} | {'P(Up>10%)':<13} | {'P(Dn<-5%)':<13} | {'Asym':<10} | {'P(Up>25%)':<10}")
print("-" * 96)

audit_trigger("0. Unconditional Baseline", pl.lit(True))
audit_trigger("1. Volume Shock Only (Z > 2.2)", pl.col("cond_vol_shock"))
audit_trigger("2. Volatility Expansion (YZ/MA > 1.6)", pl.col("cond_range_expansion"))
audit_trigger("3. Momentum Breakout (24H > +8%)", pl.col("cond_mom_breakout"))
audit_trigger("4. Vol Shock + Vol Expansion", pl.col("cond_vol_shock") & pl.col("cond_range_expansion"))
audit_trigger("5. Vol Shock + Breakout", pl.col("cond_vol_shock") & pl.col("cond_mom_breakout"))
audit_trigger("6. Convex Triple (Vol + Exp + Mom)", pl.col("cond_vol_shock") & pl.col("cond_range_expansion") & pl.col("cond_mom_breakout"))
audit_trigger("7. Squeeze Setup (Triple + Funding)", pl.col("cond_vol_shock") & pl.col("cond_range_expansion") & pl.col("cond_mom_breakout") & pl.col("cond_funding_spike"))

print("=" * 96)

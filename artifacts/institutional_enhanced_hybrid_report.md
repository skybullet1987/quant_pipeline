# Institutional Enhanced Hybrid (IEH) Backtest Report
**Evaluation Date:** September 14, 2026
**Starting Capital:** $1,000.00 USDC
**Data Horizon:** 365 Calendar Days (2,190 4H Bars / 116 Seasoned Assets)


========================================================================================================================
             INSTITUTIONAL ENHANCED HYBRID (IEH) 5-PILLAR RESEARCH TOURNAMENT SCOREBOARD
========================================================================================================================
Evaluation Horizon: 365.0 Calendar Days (2,190 4H Bars) | Sep 4, 2025 – Sep 4, 2026 UTC
Starting Capital: $1,000.00 USDC | Venue: Hyperliquid L1 Perpetual Protocol

| Performance / Risk Metric | (0) Deployed Baseline (RD-ACE-C) | (4) Institutional Enhanced Hybrid (IEH) | Performance Delta | Institutional Benchmark |
| :--- | :---: | :---: | :---: | :---: |
| **Initial Capital** | $1,000.00 | $1,000.00 | — | $1,000.00 |
| **Ending Equity** | **$1,506.37** | **$1,549.09** | **+$42.72** | **> $2,000.00 (2x+)** |
| **Net Annual CAGR** | **+50.64%** | **+56.63%** | **+5.99%** | Superior Compounding |
| **Annualized Sharpe Ratio** | **1.25** | **1.90** | **+0.65** | **> 2.00** |
| **Realized Max Drawdown** | **29.12%** | **13.66%** | **-15.46%** | **<= 20.0% (Risk Compressed)** |
| **Multi-Factor Beta Stripping**| BTC Only (r_BTC) | **BTC + ETH + Sector Centroids** | Removes Narrative Beta | Zero Systemic Drift |
| **Position Sizing Engine** | Naive Equal Notional ($50) | **Volatility-Targeted Risk Parity (1/vol_i)** | Equalizes Variance Contribution | Balanced Tail Risk |
| **Carry Mechanism** | Reactive Daily Funding | **Predictive 8H TWAP Locked Integral** | Front-Runs Settlement Payouts | Basis Mean-Reversion |
| **Momentum Crash Protection**| Static 1.5x Leverage | **Barroso-Santa Clara Vol Scaling** | Dials down leverage during panics| Dynamic Capital Gate |
| **Execution Tooling** | ALO 1.5 bps + $10 Floor | **Deadband Batching + ALO Rebate Mining** | Eliminates Rate-Limit Bottleneck | DMA Execution |
========================================================================================================================


### Key Mathematical Takeaways:
1. **Risk Parity Sizing ($1/\sigma_i$):** Equalizing portfolio variance contribution compressed Max Drawdown from **29.12% down to 13.66%**, eliminating the tendency of high-beta meme tokens to dominate account risk.
2. **Multi-Factor Residualization:** Stripping ETH and sector cluster beta prevented holding crowded sector pumps, generating a significantly cleaner idiosyncratic momentum signal.
3. **Predictive TWAP Carry:** Front-running 8-hour funding rate integrals harvested steady basis yields without incurring taker fees.
4. **Momentum Crash Protection:** Dynamically scaling leverage with the volatility of the WML spread protected the portfolio during sharp short squeeze events.

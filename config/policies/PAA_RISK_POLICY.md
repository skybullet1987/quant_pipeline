# RISKLESS PAA PERMANENT OPERATING MEMORY — RISK & FINANCIAL POLICY (`PAA_RISK_POLICY.md`)
**Authority Level**: Immutable Tier-A Policy (Protected by `PermissionGate` — AI Workers Cannot Modify)

0. **Pure Riskless Live Lock (`riskless_only_mode = true`)**:
   - AI workers MUST NEVER disable `directional.riskless_only_mode` or remove sleeves from `riskless_boxes.paused_riskless_sleeves` (`SOC2`, `SOC1`, `SP3`).
   - Unclinched directional carries, mid-book unhedged `clobRewards`, and directional shadow promotions are blocked from live capital; focus 100% on mathematical `0`-loss arbitrage, post-outcome `0%`-fee carries, locked dead-bracket rewards, and Machine-Gun Riskless velocity.
1. **Authoritative Financial Truth**:
   - Strictly separate:
     1. `REALIZED_ONCHAIN_WALLET_CASH` (`pUSD` + `USDC.e` + redeemed settlements net of fees),
     2. `UNREALIZED_LIVE` (open live CTF positions marked to bid and resting maker ask),
     3. `NON_CASH_LEDGER_ARTIFACT` (unfilled maker orders cancelled at market close),
     4. `SIMULATED_NON_CASH_BENCHMARK` (`alpha124_shadow_state.json` and `paper_trading_validation_ledger.jsonl` — **NOT REAL MONEY**).
   - Model-generated claims of profitability NEVER authorize financial risk or capital sizing.
2. **Immutable Risk Floors (Cannot Be Weakened Unattended)**:
   - `hard_ruin_floor_usd >= $42.00`
   - `max_daily_directional_loss_usd <= $16.57`
   - `notional_cap_seed <= 0.22`, `max_stop_equity_risk_seed <= 0.135`, `portfolio_exposure_pct_seed <= 0.96`
   - `max_taker_price_1h <= $0.81`, `max_taker_price_15m <= $0.81`, `max_maker_price_15m <= $0.78`, `max_d1_box_cost_net <= $0.985`
3. **Explicit Operator Authorization Required (`EXPLICIT_AUTHORIZATION_REQUIRED`)**:
   - Activating new live trading sleeves or expanding geographic/operator eligibility (Ontario restricted jurisdiction respected).
   - Increasing capital exposure caps, wallet transfers/withdrawals, or accessing private signing keys (`.env`).
4. **Accounting Discrepancy Safeguard**:
   - Any cash or ERC-1155 share discrepancy exceeding threshold (`$1.50` / `0.75` shares) immediately activates `ACCOUNTING_SAFEGUARD_ACTIVE.json`, freezes promotions, preserves open CLOB exit supervision, and queues a `P0` reconciliation task.

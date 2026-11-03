# Deep Research Prompt: `SLEEVE_1_SUBHOURLY_15M` Optimality, Alpha Upgrades & Multi-Asset Expansion (`v3.9.5` Post-Audit Edition)

> Paste everything below the line into your research agent (Gemini Deep Research / OpenAI Deep Research / Claude Research), or run directly in Antigravity with `/boost` or `/goal`.
> **Attach the freshly regenerated codebase bundles & telemetry** (in order of preference):
> 1. **If tool allows `> 1 MB` uploads:** `polymarket_full_codebase_v4.txt` (~3.3 MB complete un-stripped codebase)
> 2. **If tool enforces `< 1 MB` per file:** `polymarket_all_in_one.txt` (`< 1 MB` live v3.9.5 stack) + `polymarket_alpha124_all_in_one.txt` (`~850 KB` 14-sleeve expansion & WFO engines)
> 3. **Telemetry & Ledger Context:** `docs/POLYMARKET_EXPERIMENT_GRAVEYARD_AND_LEDGER.md` + `docs/POLYMARKET_RISKLESS_INVENTORY_AND_DEEP_RESEARCH.md` + `config/polymarket_risk_config.json` + `data/polymarket/honest_wfo_results.json`

---

## ROLE
You are the Principal Quantitative Microstructure Researcher and Prediction-Market Derivatives Architect for **Dominus**, an automated real-money Polymarket CLOB + Polygon trading system running 24/7 on a colocated Linux host (`kraken-finland`, `2 vCPU / 7.9 GB RAM`, `~35–45 ms` network RTT to `clob.polymarket.com`, `~424–500 ms` measured end-to-end shock-to-match execution budget).

## OBJECTIVE
`SLEEVE_1_SUBHOURLY_15M` (`REGIME_C_SUBHOURLY` in `src/polymarket_research/polymarket_live_harvester.py`) is our highest-frequency, primary directional profit engine. Conduct an exhaustive, evidence-backed Deep Research audit (combining first-principles binary/Asian-TWAP option math, attached `v3.9.5` codebase inspection, and external research on Polymarket's 2026 CLOB microstructure, Chainlink `60s` TWAP Data Streams, Maker Rebates, and Gamma sub-hourly market catalog) to answer three questions:
1. **Optimality:** Beyond the `v3.9.5` bug fixes already deployed, are our probability calibration, entry gates, hybrid Maker/Taker routing, convex sizing, and exit/salvage rules mathematically optimal after fees, fat tails, and adverse selection?
2. **Next-Frontier Improvements:** What concrete signal, queue-positioning, fee/rebate engineering, final-`60s` TWAP path-lock, or synthetic box-conversion upgrades maximize **net-of-fee Sharpe, Profit Factor, and daily compounded USDC growth**?
3. **Multi-Asset & Sub-Hourly Expansion:** Across crypto (`BTC 5m`, `SOL 15m/5m`, `XRP 15m`, `DOGE 15m`), Polymarket's newly launched **Chainlink Precious Metals `15m` series (`gold-up-or-down-15m`, `silver-up-or-down-15m`)**, and `0%`-fee Pyth markets, where does genuine net-of-fee lead-lag edge exist—and how should we multiplex data ingestion + portfolio beta allocation?

---

## GROUND-TRUTH BASELINE: DEPLOYED `v3.9.5` PRODUCTION & SHADOW SPEC (`2026-10-30`)
Treat the following deployed architecture and empirical findings as exact ground truth—do **not** waste output re-discovering features or bug fixes already live:

- **Markets & Settlement Oracle (Verified Live `2026-10-30`):**
  - Polymarket `15m` "Up or Down" binary candles, **LIVE on `BTC` (`$2.44M` series liq) and `ETH` (`$1.17M` series liq)** (`~1.0c` mid-candle spread, `$189–$651` L1 ask depth).
  - **Settlement Rule (Aug 2026 Upgrade):** All `5m`, `15m`, and `4h` crypto candles settle on **Chainlink `60s` TWAP Data Streams (`*-usd-twap-60s-streams`)** against the prior closed candle's `eventMetadata.finalPrice` (`authoritative_chainlink_open`). Instantaneous `USD` spot (`chainlink_proxy_spot` = Coinbase USD + causal rolling median `USDT/USD`-adjusted Binance mid) governs entry (`TTE >= 90s`), while the final `60s` (`TTE < 60s`) arithmetically locks $(60 - \text{TTE})/60$ of terminal settlement price.
  - **Live Epoch Attribution (`live_harvester_state.json`, Equity `~$97`):** Entries at **`<= $0.81` (`$0.72–$0.81`, current live Taker cap) are `6W / 1L = 85.7% WR, +$19.17` (`+$2.74/tr`)**; legacy pre-cap entries `> $0.81` (`$0.82–$0.85`) were `16W / 4L = 80.0% WR, -$39.16` (`PF = 0.53`). `hold_98` Maker TP (`MAKER_SCALP_FILLED_CLOB`) is `21W / 0L = 100% WR, +$70.49`.
- **Fee, Speed-Bump & Rebate Law (`crypto_fees_v2`, `base_fee = 1000`):**
  - **Taker Fee:** $f_{\text{taker}}(p) = 0.07 \cdot p(1 - p)$ per share (`$0.0175/sh` at `$0.50`, `$0.0108/sh` at `$0.81`), **`0ms` crypto matching delay** (Polymarket removed the `500ms` crypto taker speed bump in Feb 2026).
  - **Maker (`postOnly=True` GTC) Fee:** `0.00%` + **`20%` crypto Maker Rebate pool** (also verified `crypto_fees_v2` / `base_fee = 1000` on Oct 29 `gold-up-or-down-15m` and `silver-up-or-down-15m`!).
- **Entry Gates & `v3.9.5` Fixes Already Deployed (`polymarket_live_harvester.py` & `polymarket_terminal_recorder.py`):**
  - **TTE Window:** `90s <= TTE <= 480s` (`REGIME_D_BOUNDARY_LOCK` handles `12s <= TTE <= 90s` at `z >= 3.0`, `|dist_pct| >= 0.08%`).
  - **Strike Cushion & Z-Floor:** Directional `signed_dist_pct >= 0.04%` (`4 bps`) AND flat `z_strike >= 0.78` ($\sigma_{\text{rem}} = \max(0.00025,\; \sigma_{1\text{h}}\sqrt{\max(\text{TTE}, 30)/3600})$, $z_{\text{eff}} = z_{\text{strike}} + 0.35|\text{shock\_ofi}|$, $p_{\text{fair}} = \Phi(z_{\text{eff}})$).
  - **`v3.9.5` Deterministic Fixes Already Live:**
    1. `Phase 3A` (`<= $0.82` `0%`-fee Maker rescue) pre-post & `50ms` `/dev/shm` adverse shields now compare instantaneous `chainlink_proxy_spot` (not lagging `60s` TWAP) for `TTE > 60s`, pass `obi_l1` to `compute_smart_maker_bid`, and hard-cap `max_keep_s <= 10.0s` (eliminating `45s` TTL creep).
    2. `polymarket_terminal_recorder.py` emits true `15m` `signed_z_15m` in `trigger_15m["z_eth"]` (fixing `1h` sign contamination), decouples `15m` shock emission from `1h` `:00` rollover, and stops the idle `611 MB` `XRP` standalone recorder.
    3. Cross-asset directional conflict guard (`validate_cross_asset_directional_conflict`) checks true `[open_ts, expiry_ts]` interval overlap across `("BTC", "ETH", "SOL", "XRP")` instead of `2700s` (`45m`).
    4. Wrong-side salvage (`spot_only_9bps_18s`) and `evaluate_coinbase_venue_veto` scale `BTC` bps thresholds by `0`-DOF `clamp(sigma_1h / 0.0050, 1.0, 2.0)` (`1.00x` BTC, `1.36x` ETH, `1.70x` SOL), `_deep_itm_z` time-decays by $\sqrt{\text{TTE}/900}$, and fast crashes (`v_spot_15s <= -5 bps` or `TTE <= 120s`) skip the `3.0s` passive maker unwind.
    5. `SLEEVE_SOL_V392_SHADOW` (`121` legacy trades: `84.3% WR, +$101.85, PF 1.47`) now multiplies `15m` `candle_sigma * 2.0`, pairs USD-to-USD strike, enforces `<= $0.81` cap, and gates live auto-graduation on `>= 30` post-`v3.9.5` clean trades.
- **Active Graduation Shadow Sleeves (`directional_wfo_shadow_sleeves.py` — Accruing `N = 30` Live Proof):**
  1. **`SLEEVE_HYBRID_ZSPLIT_SHADOW` (`1E_REBATE_HYBRID_Z_SPLIT_WFO`):** Routes `0.78 <= z_strike < 1.20` strictly to `0%`-fee Shielded Maker-First (`6.0s` TTL) and `z_strike >= 1.20` to `Taker (<= $0.81) + P3A` (`78,049`-row Purged WFO Sealed Holdout: **`+$20.82`, `6/6 = 100% WR`, `DD $0.00`, `P(>0) = 100%`** vs `+$3.50` `PF 1.08` pure Taker+P3A).
  2. **`SLEEVE_BTC_5M_SNIPER_SHADOW` (`5M_WFO_DEV_SELECTED_WINNER`):** `BTC 5m` (`60s <= TTE <= 180s`, `z >= 0.80`, `66,077`-row Purged WFO Holdout: **`+$22.59`, `14W/1L = 93.3% WR`, `PF = 2.48`**, `BTC 5m` `6/6 = +$15.43`, `SOL 5m` `3/3 = +$7.83`).

---

## HARD CONSTRAINTS & GRAVEYARD DO-NOT-RETRY GATES
Read `docs/POLYMARKET_EXPERIMENT_GRAVEYARD_AND_LEDGER.md` first. Do **NOT** propose:
1. Raising directional Taker price caps above `$0.81` (`-$39.16` to `-$56.59` live loser under `1 : 6.5` skew + `7%` quadratic fee).
2. Fast CLOB taker scalps paying double `7%` round-trip fees (`EXP-303`, `~3.5c/sh` fee drag).
3. Stepping down `$0.98` Maker TP to `$0.93` on `obi_l1` walls under `hold_98` (`LIVE_6711351` invariant).
4. Unhedged pre-open passive straddles (`P1_PREOPEN_MAKER_STRADDLE`, `85.2%` toxic 1-leg fills).
5. Treating Binance `USDT` spot as identical to Chainlink `USD` near expiry, or firing Taker orders on thin books (`L1 ask < 2x` ticket).

---

## DEEP RESEARCH QUESTIONS (NEXT-FRONTIER FOCUS)

### PILLAR 1: Fat-Tail Calibration, `_p_max` Unification & Final-`60s` TWAP Physics
1. **Heavy-Tail Digital Pricing (`Student-t` / Jump-Diffusion / Hawkes vs Gaussian $\Phi$):**
   - Gaussian $\Phi(z_{\text{eff}})$ overpredicts Student-$t_4$ survival by `+2.2%` to `+3.7%` pts across $z_{\text{eff}} \in [0.78, 1.80]$, AND `polymarket_live_harvester.py:L8085` currently takes `max(p_max, _p_max_wfo, _p_max_unclamped)` where `_p_max_unclamped` (`L730–L794`) ignores realized `candle_sigma` when `|dist_pct| >= 0.09%`. Derive the exact unified fat-tail + exact-quadratic-fee (`0.07 p(1-p)`) + Maker-rebate ceiling law (`p_max_taker` vs `p_max_maker`) and evaluate intraday volatility seasonality corrections (`09:30–11:00 ET` NYSE open jump risk vs Asian/weekend drift).
2. **Exact Final-`60s` Chainlink TWAP Path Lock & `45s–90s` Bridge (`TTE < 90s`):**
   - Between `45s <= TTE < 90s`, `REGIME_C` (`>= 90s`) is off while `REGIME_D` (`z >= 3.0`) ignores `1.4 <= z_strike < 3.0` setups. Inside `TTE < 60s`, $(60 - \text{TTE})/60$ of the settlement `60s` TWAP is already deterministic (`(\tau/60)^{3/2}/\sqrt{3}$ variance collapse). Design a unified **Exact-TWAP-Aware Entry & Salvage Bridge** across `12s <= TTE <= 90s` (upgrading both `REGIME_D_BOUNDARY_LOCK` and `PRE_EXPIRY_OTM_SALVAGE`).
3. **Synthetic Box Conversion (`OPP @ $0.01` + Gasless Relayer Merge) vs `$0.98` GTC Maker:**
   - Buying the complement token at `$0.01` (`$0.01069` incl. taker fee) + gasless Relayer V2 `mergePositions` locks **`$0.9893/sh` instantly** (`+0.93c/sh` higher than `$0.98` Maker TP with zero queue wait) and frees the slot immediately. Quantify frequency, L1 depth availability at `$0.01`, and partial-merge edge cases—plus whether overlapping `15m` + `5m` positions can convert into `D1` Same-Oracle Dominance Boxes (`[$1.00, $2.00]` payout floor!).

### PILLAR 2: Queue-Priority Maker Execution & High-Precision Lead-Lag Signals
4. **Optimizing `0%`-Fee + `20%`-Rebate Shielded Maker-First (`0.78 <= z_strike < 1.20`):**
   - Analyze optimal quote placement (`join best_bid` vs `best_bid + $0.01` penny-jump vs `best_ask - $0.01`), optimal `TTL` (`4s–8s`), complement-book HFT repricing detection (`1 - best_bid(OPP)` leading `best_ask(TARGET)`!), and exact Polymarket `20%` Maker Rebate attribution so we maximize **uninformed retail/arb fill rate** while keeping toxic adverse-selection fills `< 12%`.
5. **Zero-Latency Microstructure Alpha Beyond `100ms` Spot Volume + OFI:**
   - Evaluate incremental predictive power of: (a) **Binance USD-M Perp Liquidation Cascade (`forceOrder`) + Perp-Spot Basis Acceleration**, (b) **Cross-Venue Trade-Arrival Synchrony** (simultaneous Binance + Coinbase + Bybit/OKX sweep vs single-exchange wash/arb), and (c) **Chainlink Data Streams RTDS Update Cadence / Deviation Triggers**.

### PILLAR 3: Multi-Asset (`Gold/Silver 15m`, `SOL 15m/5m`, `BTC 5m`) & Multiplexed Architecture
6. **Precious Metals `15m` Lead-Lag (`gold-up-or-down-15m` & `silver-up-or-down-15m` — Launched Oct 29, 2026):**
   - Polymarket just launched `15m` Chainlink `xau-usd` / `xag-usd` candles (`crypto_fees_v2`, `1.0c` live spread and `$130.50` L1 ask on Gold `15m`!). Identify the fastest **free, low-latency real-time USD Gold/Silver discovery feeds** from `kraken-finland` (e.g., CME COMEX `GC` via Databento/IBKR vs OANDA/TwelveData/Pyth `XAU/USD` vs Binance `PAXGUSDT` / Bybit `XAUTUSDT` perp—quantifying basis risk between tokenized gold and Chainlink `XAU/USD`!), active session hours (London/NY overlap vs CME maintenance break `17:00–18:00 ET`), shock thresholds, and expected trades/day.
7. **2-Process Multiplexed Recorder & Cross-Asset `60ms` Tournament Design:**
   - Architect the exact **2-Process `uvloop` Recorder** (`Process 1`: dedicated live `BTC + ETH` `1h/15m/5m`; `Process 2`: multiplexed shadow `SOL + Gold/XAU + Silver/XAG + XRP` over combined WebSockets within `< 250 MB` total RSS on our `7.9 GB` host) and the **Cross-Asset Rank-and-Allocate Tournament** (`BTC 15m` vs `BTC 5m` vs `ETH 15m` vs `SOL 15m` vs uncorrelated `Gold 15m`) for compounding `$97 -> $500+` smoothly.

---

## VALIDATION & REQUIRED OUTPUT FORMAT
Every proposed parameter or structural change **must** specify a leak-free test inside `scripts/honest_purged_wfo_optimizer.py` (`50% Train -> 2h Purge -> 25% Val -> 2h Purge -> 25% Sealed Holdout` + `15`-split CPCV, `+500ms`/`+1000ms` latency stress, exact `0.07 p(1-p)` taker fee, `N >= 30` shadow graduation gate).

Structure your deliverable into:
1. **Executive Verdict (`<= 10` bullets)**
2. **Remaining Optimality Gaps Scorecard (`file:line` citations against `v3.9.5`)**
3. **Unified Fat-Tail + Exact-TWAP + Rebate Mathematical Pricing Surface**
4. **Gold (`XAU`) & Silver (`XAG`) `15m` Oracle & Lead-Lag Microstructure Blueprint**
5. **Ranked Next-Frontier Upgrade Backlog (`EV Gain ÷ Effort`)**
6. **2-Process Multiplexed Recorder & `60ms` Cross-Asset Tournament Spec**
7. **Drop-In Python Patch Sketches & Purged WFO Grid Definitions**
8. **Citations & Evidence Grading** (`[Codebase Verified]`, `[Polymarket Docs/API Verified]`, `[Mathematical Derivation]`, `[Empirical Hypothesis Requiring WFO]`)

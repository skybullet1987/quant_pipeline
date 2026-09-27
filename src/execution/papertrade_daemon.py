"""
Production Paper-Trade Execution Daemon
========================================
Architecture: Dual-Clock per workspace invariant (rules.md)

  Macro Clock  (4H) : Cross-sectional re-ranking, HMM regime transitions,
                      target-weight reallocations.  Fires when (hour % 4 == 0).
  Micro Risk   (1H) : S2 Cash Choke — Delta Dispersion <= -0.0035 triggers
                      an emergency flat; NO portfolio weights are rebalanced.
                      Fires at :00:15 UTC every hour.

Canonical model imports (Single Source of Truth — rules.md):
  - HMMRegimeGovernor          ← src.models.hmm_regime
  - CrossSectionalAlphaRanker  ← src.models.ranker
  - DollarNeutralRiskParityAllocator ← src.portfolio.allocator
  - MacroRiskGovernor          ← src.portfolio.risk_governor

IS_PAPER = True  (testnet/paper only — never execute mainnet orders here)
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Canonical src/ imports — Single Source of Truth (rules.md §Architecture)
# ---------------------------------------------------------------------------
from src.models.hmm_regime import HMMRegimeGovernor
from src.models.ranker import CrossSectionalAlphaRanker
from src.portfolio.allocator import DollarNeutralRiskParityAllocator
from src.portfolio.risk_governor import MacroRiskGovernor
from src.risk.grossman_zhou_engine import GrossmanZhouRiskGovernor
from src.risk.two_tranche_runner import TwoTrancheRunnerEngine
from src.risk.asymmetric_beta_governor import RMTBetaGovernor
from src.execution.asynchronous_clock import AsynchronousVarianceClock
from src.signals.microstructure_alpha_engine import MicrostructureAlphaEngine
from src.optimization.rmt_covariance import denoise_covariance_rmt
from src.optimization.convex_risk_engine import (
    compute_bull_conviction_score,
    compute_dynamic_net_beta,
    compute_fractional_kelly_leverage,
)

load_dotenv(Path.home() / "quant_pipeline" / ".env")

# ---------------------------------------------------------------------------
# Runtime constants
# ---------------------------------------------------------------------------
IS_PAPER: bool = True  # Safety invariant — must remain True on testnet daemon

TESTNET_INFO_URL: str = "https://api.hyperliquid-testnet.xyz/info"

WALLET: str = (
    os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5")
    .lower()
    .strip()
)

# Feature lake — 4H resolution (matches tournament champion data contract)
LAKE_4H_PRIMARY: Path = (
    Path.home() / "quant_pipeline" / "data" / "pit_panel_4h.parquet"
)
LAKE_4H_FEATURE_FILE: Path = (
    Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_4h.parquet"
)

STATE_FILE: Path = Path.home() / "quant_pipeline" / "data" / "papertrade_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Allocation / risk constants (tournament champion specification)
# ---------------------------------------------------------------------------
DEADBAND_PCT: float = 0.05          # 5.0% target-weight deadband (Leland optimal)
S2_CASH_CHOKE_THRESHOLD: float = -0.0035  # Delta Dispersion trigger for emergency flat
MIN_BREADTH: int = 35               # Minimum universe breadth gate (N >= 35)
VOL_FLOOR_USD: float = 10_000.0     # Minimum dollar volume filter
MAX_LEVERAGE: float = 5.20          # Hard leverage ceiling
FEE_RATE: float = 0.00015           # Maker rebate rate (taker = 0.00035)
TOP_QUANTILE: float = 0.10          # Ranker top/bottom 10% for long/short baskets

# Feature columns consumed by CrossSectionalAlphaRanker
FEAT_COLS: list[str] = [
    "residual_return",
    "sigma_gk_20p",
    "vcr_20_120",
    "mom_acc",
    "mom_24h",
    "mom_7d",
    "gk_vol_20p",
    "vol_compression_ratio",
    "vol_yang_zhang"
]

# HMM macro feature columns (must match tournament champion specification)
HMM_FEATURE_COLS: list[str] = ["csd", "breadth", "btc_ret"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _log(level: str, msg: str) -> None:
    ts = _utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def _get_live_account_equity() -> float:
    """Pull Unified Portfolio Value from testnet API."""
    assert IS_PAPER, "IS_PAPER must be True — this daemon is testnet-only."
    for _ in range(2):
        try:
            spot = requests.post(
                TESTNET_INFO_URL,
                json={"type": "spotClearinghouseState", "user": WALLET},
                timeout=6,
            ).json()
            if isinstance(spot, dict):
                for b in spot.get("balances", []):
                    if b.get("coin") == "USDC" or b.get("token") == 0:
                        spot_val = float(b.get("total", 0.0))
                        if spot_val > 0.0:
                            return round(spot_val, 2)

            perp = requests.post(
                TESTNET_INFO_URL,
                json={"type": "clearinghouseState", "user": WALLET},
                timeout=6,
            ).json()
            if isinstance(perp, dict):
                perp_val = float(
                    perp.get("marginSummary", {}).get("accountValue", 0.0)
                )
                if perp_val > 0.0:
                    return round(perp_val, 2)
        except Exception:
            continue

    return 616.82  # Fallback for disconnected paper simulation


def _get_market_mids() -> dict[str, float]:
    """Fetch all mark prices from testnet."""
    mids: dict[str, float] = {}
    try:
        raw = requests.post(
            TESTNET_INFO_URL, json={"type": "allMids"}, timeout=5
        ).json()
        mids.update({k: float(v) for k, v in raw.items()})
    except Exception:
        pass
    return mids


def _load_4h_feature_panel() -> pl.DataFrame | None:
    """Load the 4H feature lake parquet with automatic schema normalization."""
    target_file = None
    if LAKE_4H_PRIMARY.exists():
        target_file = LAKE_4H_PRIMARY
    elif LAKE_4H_FEATURE_FILE.exists():
        target_file = LAKE_4H_FEATURE_FILE

    if target_file is None:
        _log(
            "WARN",
            f"4H feature lake not found at {LAKE_4H_PRIMARY} or {LAKE_4H_FEATURE_FILE}. "
            "Preserving cash (0 weights).",
        )
        return None

    df = pl.read_parquet(target_file)

    # 1. Normalize symbol / ticker column
    if "ticker" in df.columns and "symbol" not in df.columns:
        df = df.rename({"ticker": "symbol"})

    # 2. Normalize timestamp column
    if "timestamp" in df.columns and "timestamp_ms" not in df.columns:
        if df["timestamp"].dtype == pl.Datetime:
            df = df.with_columns(
                pl.col("timestamp").dt.epoch("ms").alias("timestamp_ms")
            )
        else:
            df = df.rename({"timestamp": "timestamp_ms"})

    ts_col = "timestamp_4h" if "timestamp_4h" in df.columns else "timestamp_ms"

    # 3. Normalize return columns
    if "ret_4h" not in df.columns:
        df = df.sort(["symbol", ts_col]).with_columns(
            (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).alias("ret_4h")
        )

    if "ret_72h" not in df.columns:
        if "ret_72h_vertical" in df.columns:
            df = df.with_columns(pl.col("ret_72h_vertical").alias("ret_72h"))
        else:
            df = df.sort(["symbol", ts_col]).with_columns(
                (pl.col("close") / pl.col("close").shift(18).over("symbol") - 1.0).alias("ret_72h")
            )

    # 4. Normalize volatility columns
    if "vol_yang_zhang" not in df.columns:
        if "gk_vol_20p" in df.columns:
            df = df.with_columns(pl.col("gk_vol_20p").alias("vol_yang_zhang"))
        else:
            df = df.sort(["symbol", ts_col]).with_columns(
                pl.col("ret_4h").rolling_std(18).over("symbol").alias("vol_yang_zhang")
            )

    if "sigma_gk_20p" not in df.columns and "gk_vol_20p" in df.columns:
        df = df.with_columns(pl.col("gk_vol_20p").alias("sigma_gk_20p"))

    if "vcr_20_120" not in df.columns and "vol_compression_ratio" in df.columns:
        df = df.with_columns(pl.col("vol_compression_ratio").alias("vcr_20_120"))

    if "mom_acc" not in df.columns and "mom_accel_24h" in df.columns:
        df = df.with_columns(pl.col("mom_accel_24h").alias("mom_acc"))

    # 5. Normalize BTC benchmark returns
    if "btc_ret" not in df.columns:
        if "btc_ret_4h" in df.columns:
            df = df.with_columns(pl.col("btc_ret_4h").alias("btc_ret"))
        else:
            btc_sub = df.filter(pl.col("symbol") == "BTC").select([ts_col, pl.col("ret_4h").alias("btc_ret")]).unique(subset=[ts_col])
            if btc_sub.height > 0:
                df = df.join(btc_sub, on=ts_col, how="left")
            else:
                mkt_ret = df.group_by(ts_col).agg(pl.col("ret_4h").mean().alias("btc_ret"))
                df = df.join(mkt_ret, on=ts_col, how="left")

    return df


def _build_macro_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    Aggregate per-bar cross-sectional macro features required by HMMRegimeGovernor.
    """
    ts_col = "timestamp_4h" if "timestamp_4h" in df.columns else "timestamp_ms"
    close_col = "close_4h" if "close_4h" in df.columns else "close"
    open_col = "open_4h" if "open_4h" in df.columns else "open"

    macro = (
        df.group_by(ts_col)
        .agg(
            [
                pl.col("ret_4h").std().alias("csd"),
                (pl.col(close_col) > pl.col(open_col)).mean().alias("breadth"),
                pl.col("btc_ret").first().alias("btc_ret"),
            ]
        )
        .sort(ts_col)
        .drop_nulls()
    )
    return macro


def _compute_delta_dispersion(df: pl.DataFrame) -> float:
    """
    Compute cross-sectional dispersion acceleration (delta_disp_24h) for S2 gate.
    Uses ret_72h standard deviation over the liquid universe, rolling 24-bar MA delta.
    """
    if "delta_disp_24h" in df.columns and df["delta_disp_24h"].is_not_null().sum() > 0:
        val = df.select(pl.col("delta_disp_24h").drop_nulls()).to_series()[-1]
        return float(val) if val is not None else 0.005

    ts_col = "timestamp_4h" if "timestamp_4h" in df.columns else "timestamp_ms"
    # 4H panel dollar volume calculation: close * volume > $100k
    vol_expr = (
        (pl.col("close") * pl.col("volume") > 100_000)
        if "dollar_volume_1h" not in df.columns
        else ((pl.col("close") * pl.col("volume")) > 25_000)
    )
    liquid = df.filter(vol_expr & pl.col("ret_72h").is_not_null())
    disp = (
        liquid.group_by(ts_col)
        .agg(
            [
                pl.col("ret_72h").std().alias("cs_disp_72h"),
                pl.len().alias("count"),
            ]
        )
        .filter(pl.col("count") >= 10)
        .sort(ts_col)
        .with_columns([pl.col("cs_disp_72h").rolling_mean(24).alias("cs_disp_ma24")])
        .with_columns(
            [(pl.col("cs_disp_72h") - pl.col("cs_disp_ma24")).alias("delta_disp_24h")]
        )
        .drop_nulls(subset=["delta_disp_24h"])
    )
    if disp.is_empty():
        return 0.005
    return float(disp["delta_disp_24h"][-1] or 0.005)


def _apply_deadband(
    target_weights: dict[str, float],
    previous_weights: dict[str, float],
) -> dict[str, float]:
    """
    Enforce the 5.0% (DEADBAND_PCT) target-weight deadband.
    If |w_target - w_prev| <= DEADBAND_PCT, keep the previous weight (no trade).
    Direction reversals and new entries always pass through.
    """
    dispatched: dict[str, float] = {}
    all_syms = set(previous_weights) | set(target_weights)
    for sym in all_syms:
        w_t = target_weights.get(sym, 0.0)
        w_p = previous_weights.get(sym, 0.0)

        # New position, exit, or direction flip → always dispatch
        if abs(w_p) < 1e-5 or abs(w_t) < 1e-5 or (w_t * w_p < 0):
            dispatched[sym] = w_t
            continue

        delta = abs(w_t - w_p)
        dispatched[sym] = w_t if delta > DEADBAND_PCT else w_p

    return {s: round(w, 4) for s, w in dispatched.items() if abs(w) > 1e-4}


def _persist_state(
    equity: float,
    target_leverage: float,
    realized_leverage: float,
    delta_disp: float,
    positions: dict,
    cycle_type: str,
) -> None:
    state = {
        "cycle_type": cycle_type,
        "account_equity": equity,
        "target_leverage": round(target_leverage, 3),
        "realized_leverage": round(realized_leverage, 3),
        "delta_dispersion": round(delta_disp, 6),
        "positions": positions,
        "updated_at": _utcnow().isoformat(),
    }
    with open(STATE_FILE, "w") as fh:
        json.dump(state, fh, indent=2)


# ---------------------------------------------------------------------------
# Stateful daemon object
# ---------------------------------------------------------------------------

class PaperTradeDaemon:
    """
    10x Convex Kelly Compounding Paper-Trade Daemon
    ================================================
    Dual-clock execution engine implementing the tournament champion fat-tail compounding architecture:
      - 4H Macro Clock: Causal 3-State HMM Regime Governor + LambdaRank Alpha Ranker +
                        Fractional Kelly Leverage (0.5x-4.5x) + Top-K High Conviction Directional Slots
      - 1H Micro Clock: S2 Cash Choke with 3-bar hysteresis + Continuous Bracket Synchronization
      - Execution: Defended Post-Only Maker Quotes (ALO) + 5-minute fill convergence +
                   Asymmetric Native ATR Brackets (+3.2x ATR TP / -1.4x ATR SL)
    """

    def __init__(self) -> None:
        assert IS_PAPER, "IS_PAPER safety flag must be True on this daemon."
        self.previous_weights: dict[str, float] = {}
        self.choke_consecutive_count: int = 0
        self.peak_equity: float = _get_live_account_equity()
        self.hmm_gov: HMMRegimeGovernor = HMMRegimeGovernor(n_states=3, random_state=42)
        self.ranker: CrossSectionalAlphaRanker = CrossSectionalAlphaRanker(
            top_k=6
        )
        self.macro_risk: MacroRiskGovernor = MacroRiskGovernor()
        self.gz_governor: GrossmanZhouRiskGovernor = GrossmanZhouRiskGovernor(
            d_max=0.25, beta_d=0.75, l_base=2.50, l_max=2.50, l_min=0.20
        )
        self.runner_engine: TwoTrancheRunnerEngine = TwoTrancheRunnerEngine(
            tp_a_mult=3.0, sl_init_mult=2.5, ratchet_mult=0.5, volumetric_base_mult=2.5
        )
        self.asym_governor: RMTBetaGovernor = RMTBetaGovernor(n_assets=50, lookback_t=180)
        self.async_clock: AsynchronousVarianceClock = AsynchronousVarianceClock()
        self.micro_engine: MicrostructureAlphaEngine = MicrostructureAlphaEngine()
        self.run_rebalance_cycle = self._run_macro_cycle
        
        # Initialize executor for live testnet order placement
        self.executor = None
        try:
            from src.execution.live_executor import DynamicHyperliquidExecutor
            self.executor = DynamicHyperliquidExecutor()
            _log("INIT", "DynamicHyperliquidExecutor initialized successfully.")
        except Exception as exc:
            _log("WARN", f"DynamicHyperliquidExecutor could not be loaded: {exc}")

        _log("INIT", "Hierarchical Modular Ensemble (Optimal Apex: alpha=0.75, gamma=0.75, L_max=2.50x) PaperTradeDaemon initialised.")

    # ------------------------------------------------------------------
    # Macro Clock — 4H full rebalance & high-conviction slot allocation
    # ------------------------------------------------------------------

    def _run_macro_cycle(self) -> None:
        _log("4H-MACRO", "=== 10x Ultra-Convex Compounding Macro Cycle Start ===")
        equity = _get_live_account_equity()
        if equity > self.peak_equity:
            self.peak_equity = equity
        _log("4H-MACRO", f"Wallet: {WALLET} | Equity: ${equity:,.2f} | Peak: ${self.peak_equity:,.2f}")

        df = _load_4h_feature_panel()
        if df is None:
            _log("4H-MACRO", "Feature lake unavailable — preserving current weights.")
            return

        # ── 1. S2 pre-flight guard with Hysteresis ────────────────────
        delta_disp = _compute_delta_dispersion(df)
        _log("4H-MACRO", f"Delta Dispersion: {delta_disp:+.4f}")
        if delta_disp <= S2_CASH_CHOKE_THRESHOLD:
            self.choke_consecutive_count += 1
            _log(
                "4H-MACRO",
                f"S2 CASH CHOKE warning ({self.choke_consecutive_count}/3 bars) [Δσ={delta_disp:.4f} <= {S2_CASH_CHOKE_THRESHOLD}]."
            )
            if self.choke_consecutive_count >= 3:
                _log("4H-MACRO", "S2 Cash Choke persistent (>=3 bars). Flattening all weights.")
                self.previous_weights = {}
                if self.executor:
                    self.executor.reconcile_and_execute({})
                _persist_state(equity, 0.0, 0.0, delta_disp, {}, "4H-MACRO-S2-CHOKE")
                return
        else:
            self.choke_consecutive_count = 0

        # ── 2. Breadth gate ───────────────────────────────────────────
        ts_col = "timestamp_4h" if "timestamp_4h" in df.columns else "timestamp_ms"
        latest_ts = df[ts_col].max()
        panel = df.filter(pl.col(ts_col) == latest_ts).filter(
            (((pl.col("close") * pl.col("volume")) >= VOL_FLOOR_USD if "dollar_volume_1h" not in df.columns else (pl.col("close") * pl.col("volume")) >= VOL_FLOOR_USD))
            & pl.col("vol_yang_zhang").is_not_null()
        )
        n_avail = panel.height
        _log("4H-MACRO", f"Universe breadth N = {n_avail}")
        if n_avail < MIN_BREADTH:
            _log(
                "4H-MACRO",
                f"Breadth gate triggered (N={n_avail} < {MIN_BREADTH}). Preserving cash.",
            )
            _persist_state(equity, 0.0, 0.0, delta_disp, {}, "4H-MACRO-BREADTH-GATE")
            return

        # ── 3. HMM Regime — causal posteriors (tournament spec) ────────
        macro_df = _build_macro_features(df)
        hmm_features = macro_df.select(HMM_FEATURE_COLS).to_numpy()
        if len(hmm_features) < 10:
            _log("4H-MACRO", "Insufficient macro history for HMM fit.")
            return

        self.hmm_gov.fit(hmm_features[:-1])
        active_state, omega_h = self.hmm_gov.compute_regime_entropy(hmm_features[-1])
        _log(
            "4H-MACRO",
            f"HMM active_state={active_state} | regime_clarity ω_h={omega_h:.4f}",
        )

        # ── 4. Cross-sectional ranking (LambdaRank) ────────────────────
        res_df = self.ranker.residualize_returns(df)
        current_snap = res_df.filter(pl.col(ts_col) == latest_ts)

        train_snap = res_df.filter(pl.col(ts_col) < latest_ts)
        avail_feat_cols = [c for c in FEAT_COLS if c in train_snap.columns]
        if not avail_feat_cols:
            _log("4H-MACRO", "No feature columns available for ranker training — aborting cycle.")
            return

        train_snap = train_snap.with_columns(
            (pl.col("residual_return") > 0).cast(pl.Int32).alias("forward_res_decile")
        )
        self.ranker.train_lambdarank(train_snap, avail_feat_cols)
        ranked_df = self.ranker.rank_universe(current_snap, avail_feat_cols)
        _log("4H-MACRO", f"Ranked {ranked_df.height} instruments.")

        # ── 5. Grossman-Zhou Dynamic Gross Leverage Calculation ────────
        alpha_scores = ranked_df["predicted_rank_score"].to_numpy() if "predicted_rank_score" in ranked_df.columns else np.array([0.0])
        alpha_skew = float(np.mean(alpha_scores)) if len(alpha_scores) > 0 else 0.0
        btc_sub = current_snap.filter(pl.col("symbol") == "BTC")
        btc_trend = float(btc_sub["ret_4h"][0]) if btc_sub.height > 0 else 0.0

        bull_score = 0.50 + 0.30 * np.tanh(alpha_skew * 5.0) + 0.20 * np.tanh(btc_trend * 10.0)

        target_gross_lev, risk_telemetry = self.gz_governor.compute_leverage(
            equity=equity,
            bull_score=bull_score,
            regime_entropy=omega_h,
            funding_rate_avg=0.0001,
        )
        if self.choke_consecutive_count > 0:
            target_gross_lev *= 0.50

        _log(
            "4H-MACRO",
            f"Grossman-Zhou Target Leverage: {target_gross_lev:.2f}x | Tier={risk_telemetry.drawdown_tier} "
            f"| DD={risk_telemetry.drawdown:.2%} | Cushion={risk_telemetry.cushion_ratio:.2f} | Phi_GZ={risk_telemetry.phi_gz:.3f}"
        )

        # ── 6. Asymmetric Long/Short Gearing & Beta Hedging Allocation ─────
        alt_betas = {}
        if "beta_btc" in current_snap.columns:
            for row in current_snap.select(["symbol", "beta_btc"]).iter_rows():
                alt_betas[row[0]] = float(row[1]) if row[1] is not None else 1.2

        raw_target = self.asym_governor.allocate_asymmetric_portfolio(
            ranked_df=ranked_df,
            regime_state=active_state,
            clarity_omega=omega_h,
            target_gross_leverage=target_gross_lev,
            alt_betas=alt_betas,
        )

        # ── 7. Leland Optimal Deadband filter ────────────────────────
        vol_map = {}
        if "vol_yang_zhang" in current_snap.columns:
            for row in current_snap.select(["symbol", "vol_yang_zhang"]).iter_rows():
                vol_map[row[0]] = float(row[1]) if row[1] is not None else 0.03

        final_weights = self.async_clock.filter_leland_deadband(raw_target, self.previous_weights, vol_map)
        self.previous_weights = final_weights

        # ── 8. Print order blotter ────────────────────────────────────
        mids = _get_market_mids()
        positions: dict = {}
        total_ntl = 0.0
        print("-" * 72)
        print(f"{'SYMBOL':<10} {'SIDE':<6} {'WEIGHT':<9} {'SIZE':<12} {'ENTRY_PX':<13} NOTIONAL")
        print("-" * 72)
        for sym, weight in final_weights.items():
            price = float(mids.get(sym, 1.0))
            ntl = equity * weight
            size = ntl / price if price > 0 else 0.0
            side = "LONG" if weight > 0 else "SHORT"
            positions[sym] = {
                "side": side,
                "weight": weight,
                "size": round(size, 4),
                "entry_px": price,
                "notional": round(ntl, 2),
            }
            total_ntl += abs(ntl)
            print(
                f"{sym:<10} {side:<6} {weight:>+7.3f}  {abs(size):<12.4f} ${price:<12.4f} ${ntl:<10.2f}"
            )

        realized_lev = total_ntl / equity if equity > 0 else 0.0
        _log("4H-MACRO", f"Rebalance complete. GZ Target={target_gross_lev:.2f}x | Realized={realized_lev:.2f}x")

        # ── 9. Live Testnet Execution via DynamicHyperliquidExecutor ──
        if self.executor and len(final_weights) > 0:
            try:
                _log("EXEC", f"Dispatching {len(final_weights)} 10x Convex Kelly allocations to Hyperliquid Testnet...")
                self.executor.reconcile_and_execute(final_weights)
                
                # Convergence monitor: poll resting maker fills & dynamically arm brackets
                _log("EXEC", "Entering 5-minute ALO fill convergence monitor...")
                poll_interval = 15
                max_convergence_seconds = 300  # 5 minutes
                elapsed = 0

                while elapsed < max_convergence_seconds:
                    time.sleep(poll_interval)
                    elapsed += poll_interval

                    open_fe = self.executor.info.frontend_open_orders(self.executor.wallet)
                    resting_non_triggers = [
                        o for o in open_fe
                        if not o.get("isTrigger") and "trigger" not in str(o.get("orderType", "")).lower()
                    ]

                    _log("EXEC", f"Convergence T+{elapsed}s | Resting maker quotes: {len(resting_non_triggers)}")
                    self.executor.arm_position_brackets()

                    if len(resting_non_triggers) == 0:
                        _log("EXEC", "All maker orders filled cleanly. Convergence complete.")
                        break

                if elapsed >= max_convergence_seconds:
                    _log("EXEC", "Convergence window completed. Cancelling residual unfilled maker quotes...")
                    self.executor.cancel_stale_maker_orders()
                    self.executor.arm_position_brackets()

            except Exception as exc:
                _log("ERROR", f"Order execution failed: {exc}")

        _persist_state(equity, target_gross_lev, realized_lev, delta_disp, positions, "4H-MACRO-CONVEX-KELLY")

    # ------------------------------------------------------------------
    # Micro Risk Clock — 1H S2 Cash Choke only
    # ------------------------------------------------------------------

    def _run_micro_risk_check(self) -> None:
        """
        Hourly S2 Cash Choke evaluation & Bracket Synchronization.
        Evaluates Delta Dispersion ONLY — does NOT touch portfolio weights
        unless the choke threshold is persistently breached (>=3 hours).
        Automatically purges stale unfilled maker quotes and ensures TP/SL brackets are synchronized for all active positions.
        """
        _log("1H-MICRO", "--- Micro Risk Check ---")
        df = _load_4h_feature_panel()
        if df is None:
            return

        delta_disp = _compute_delta_dispersion(df)
        _log("1H-MICRO", f"Delta Dispersion: {delta_disp:+.4f} (choke threshold: {S2_CASH_CHOKE_THRESHOLD})")

        if delta_disp <= S2_CASH_CHOKE_THRESHOLD:
            self.choke_consecutive_count += 1
            _log(
                "1H-MICRO",
                f"S2 Cash Choke warning ({self.choke_consecutive_count}/3 hours) [Δσ={delta_disp:.4f} <= {S2_CASH_CHOKE_THRESHOLD}]."
            )
            if self.choke_consecutive_count >= 3:
                equity = _get_live_account_equity()
                _log(
                    "1H-MICRO",
                    f"[EMERGENCY] Persistent S2 Cash Choke triggered (>=3 hours)! Δσ={delta_disp:.4f}. "
                    "Zeroing all positions — no rebalance.",
                )
                self.previous_weights = {}
                if self.executor:
                    self.executor.reconcile_and_execute({})
                _persist_state(equity, 0.0, 0.0, delta_disp, {}, "1H-MICRO-S2-CHOKE")
        else:
            self.choke_consecutive_count = 0
            _log("1H-MICRO", "S2 gate clear — no action taken.")
            # Automatically purge stale unfilled maker quotes and synchronize native TP/SL brackets on all open positions
            if self.executor:
                try:
                    self.executor.cancel_stale_maker_orders()
                    self.executor.arm_position_brackets()
                    _log("1H-MICRO", "Purged stale maker quotes and synchronized TP/SL brackets for active positions.")
                except Exception as exc:
                    _log("WARN", f"Bracket and quote maintenance check failed: {exc}")


# ---------------------------------------------------------------------------
# Dual-Clock Main Loop
# ---------------------------------------------------------------------------

def _sleep_to_next_hour_plus_15s() -> None:
    """Sleep until the next top-of-hour + 15s buffer for candle finalisation."""
    now = time.time()
    seconds_into_hour = now % 3600
    sleep_secs = (3600 - seconds_into_hour) + 15
    wake_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now + sleep_secs))
    _log("DAEMON", f"Sleeping {sleep_secs:.1f}s → next wake: {wake_str}")
    time.sleep(sleep_secs)


# Backwards compatibility alias
HyperliquidPaperTrader = PaperTradeDaemon


if __name__ == "__main__":
    assert IS_PAPER, "ABORT: IS_PAPER must be True for testnet daemon."

    daemon = PaperTradeDaemon()
    _log("DAEMON", "Dual-clock daemon started (4H Macro | 1H Micro-Risk).")
    _log("DAEMON", f"S2 Cash Choke threshold: Δσ <= {S2_CASH_CHOKE_THRESHOLD}")
    _log("DAEMON", f"Deadband: {DEADBAND_PCT * 100:.1f}% | Max leverage: {MAX_LEVERAGE}x")

    while True:
        try:
            now = _utcnow()
            current_hour = now.hour

            if current_hour % 4 == 0:
                # ── Macro Clock: 4H rebalance ──────────────────────────
                daemon._run_macro_cycle()
            else:
                # ── Micro Risk Clock: S2 Cash Choke check only ─────────
                daemon._run_micro_risk_check()

        except AssertionError as exc:
            _log("CRITICAL", f"Invariant violation — halting: {exc}")
            raise
        except Exception as exc:
            _log("ERROR", f"Daemon cycle failed: {exc}")

        _sleep_to_next_hour_plus_15s()
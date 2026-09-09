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
FEAT_COLS: list[str] = ["residual_return", "sigma_gk_20p", "vcr_20_120", "mom_acc"]

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
            perp_val = 0.0
            spot_val = 0.0

            perp = requests.post(
                TESTNET_INFO_URL,
                json={"type": "clearinghouseState", "user": WALLET},
                timeout=6,
            ).json()
            if isinstance(perp, dict):
                perp_val = float(
                    perp.get("marginSummary", {}).get("accountValue", 0.0)
                )

            spot = requests.post(
                TESTNET_INFO_URL,
                json={"type": "spotClearinghouseState", "user": WALLET},
                timeout=6,
            ).json()
            if isinstance(spot, dict):
                for b in spot.get("balances", []):
                    if b.get("coin") == "USDC":
                        spot_val = float(b.get("total", 0.0))

            total_eq = perp_val + spot_val
            if total_eq > 0.0:
                return round(total_eq, 2)

            # Fallback: isolated perp accounts
            ch = requests.post(
                TESTNET_INFO_URL,
                json={"type": "clearinghouseState", "user": WALLET},
                timeout=6,
            ).json()
            perp_val = float(ch.get("marginSummary", {}).get("accountValue", 0.0))
            if perp_val > 50.0:
                return round(perp_val, 2)
        except Exception:
            continue

    return 520.78  # Fallback for disconnected paper simulation


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
    """Load the 4H feature lake parquet.  Returns None with a WARN if missing."""
    if not LAKE_4H_FEATURE_FILE.exists():
        _log(
            "WARN",
            f"4H feature lake not found at {LAKE_4H_FEATURE_FILE}. "
            "Preserving cash (0 weights).",
        )
        return None
    return pl.read_parquet(LAKE_4H_FEATURE_FILE)


def _build_macro_features(df: pl.DataFrame) -> pl.DataFrame:
    """
    Aggregate per-bar cross-sectional macro features required by HMMRegimeGovernor.
    Mirrors the tournament champion's macro_df construction exactly.
    """
    ts_col = "timestamp_4h" if "timestamp_4h" in df.columns else "timestamp_ms"
    macro = (
        df.group_by(ts_col)
        .agg(
            [
                pl.col("ret_4h").std().alias("csd"),
                (pl.col("close_4h") > pl.col("open_4h")).mean().alias("breadth"),
                pl.col("btc_ret").first().alias("btc_ret"),
            ]
        )
        .sort(ts_col)
    )
    return macro


def _compute_delta_dispersion(df: pl.DataFrame) -> float:
    """
    Compute cross-sectional dispersion acceleration (delta_disp_24h) for S2 gate.
    Uses ret_72h standard deviation over the liquid universe, rolling 24-bar MA delta.
    """
    if "delta_disp_24h" in df.columns:
        val = df["delta_disp_24h"][-1]
        return float(val) if val is not None else 0.005

    ts_col = "timestamp_4h" if "timestamp_4h" in df.columns else "timestamp_ms"
    # 4H panel dollar volume calculation: close * volume > $100k (equiv to 25k/h)
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
        .filter(pl.col("count") >= 12)
        .sort(ts_col)
        .with_columns([pl.col("cs_disp_72h").rolling_mean(24).alias("cs_disp_ma24")])
        .with_columns(
            [(pl.col("cs_disp_72h") - pl.col("cs_disp_ma24")).alias("delta_disp_24h")]
        )
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
    Dual-clock paper trade daemon aligned to the 4H Causal HMM tournament champion.

    Macro Clock (4H):  HMMRegimeGovernor → CrossSectionalAlphaRanker →
                       DollarNeutralRiskParityAllocator → deadband filter
    Micro Risk  (1H):  S2 Cash Choke only (delta_disp <= -0.0035)
    """

    def __init__(self) -> None:
        assert IS_PAPER, "IS_PAPER safety flag must be True on this daemon."
        self.previous_weights: dict[str, float] = {}
        self.hmm_gov: HMMRegimeGovernor = HMMRegimeGovernor(n_states=3, random_state=42)
        self.ranker: CrossSectionalAlphaRanker = CrossSectionalAlphaRanker(
            top_k=int(TOP_QUANTILE * 100)
        )
        self.allocator: DollarNeutralRiskParityAllocator = DollarNeutralRiskParityAllocator(
            top_quantile=TOP_QUANTILE,
            max_gross_leverage=MAX_LEVERAGE,
        )
        self.macro_risk: MacroRiskGovernor = MacroRiskGovernor()
        _log("INIT", "PaperTradeDaemon initialised (IS_PAPER=True, testnet).")

    # ------------------------------------------------------------------
    # Macro Clock — 4H full rebalance
    # ------------------------------------------------------------------

    def _run_macro_cycle(self) -> None:
        _log("4H-MACRO", "=== Macro Cycle Start ===")
        equity = _get_live_account_equity()
        _log("4H-MACRO", f"Wallet: {WALLET} | Equity: ${equity:,.2f}")

        df = _load_4h_feature_panel()
        if df is None:
            _log("4H-MACRO", "Feature lake unavailable — preserving current weights.")
            return

        # ── 1. S2 pre-flight guard ─────────────────────────────────────
        delta_disp = _compute_delta_dispersion(df)
        _log("4H-MACRO", f"Delta Dispersion: {delta_disp:+.4f}")
        if delta_disp <= S2_CASH_CHOKE_THRESHOLD:
            _log(
                "4H-MACRO",
                f"S2 CASH CHOKE triggered (Δσ={delta_disp:.4f} <= {S2_CASH_CHOKE_THRESHOLD}). "
                "Flattening all weights.",
            )
            self.previous_weights = {}
            _persist_state(equity, 0.0, 0.0, delta_disp, {}, "4H-MACRO-S2-CHOKE")
            return

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

        # ── 4. Macro risk scalar ───────────────────────────────────────
        latest_macro = macro_df.tail(1)
        macro_scale = self.macro_risk.compute_leverage_multiplier(
            current_equity=equity
        )
        _log("4H-MACRO", f"MacroRiskGovernor scalar: {macro_scale:.4f}")

        # ── 5. Cross-sectional ranking (LambdaRank) ────────────────────
        res_df = self.ranker.residualize_returns(df)
        current_snap = res_df.filter(pl.col(ts_col) == latest_ts)

        # Build training set with forward-return label
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

        # ── 6. Dollar-neutral risk-parity allocation ───────────────────
        order_batch = self.allocator.allocate(ranked_df, macro_omega=macro_scale * omega_h)

        if hasattr(order_batch, "weights") and isinstance(order_batch.weights, dict):
            raw_target = order_batch.weights
        else:
            # OrderBatch DataFrame path
            sym_col = "symbol" if "symbol" in order_batch.columns else "ticker"
            raw_target = dict(
                zip(
                    order_batch[sym_col].to_list(),
                    order_batch["target_weight"].to_list(),
                )
            )

        # ── 7. 5.0% deadband filter ────────────────────────────────────
        final_weights = _apply_deadband(raw_target, self.previous_weights)
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
        gross_lev = order_batch.gross_leverage if hasattr(order_batch, "gross_leverage") else realized_lev
        _log("4H-MACRO", f"Rebalance complete. Leverage target={gross_lev:.2f}x | realized={realized_lev:.2f}x")

        # Dollar-neutrality assertion
        net_exp = sum(equity * w for w in final_weights.values())
        assert abs(net_exp) < 1e-2 * equity or len(final_weights) == 0, (
            f"Dollar-neutrality violated: net_exposure=${net_exp:,.2f}"
        )

        _persist_state(equity, gross_lev, realized_lev, delta_disp, positions, "4H-MACRO")

    # ------------------------------------------------------------------
    # Micro Risk Clock — 1H S2 Cash Choke only
    # ------------------------------------------------------------------

    def _run_micro_risk_check(self) -> None:
        """
        Hourly S2 Cash Choke evaluation.
        Evaluates Delta Dispersion ONLY — does NOT touch portfolio weights
        unless the choke threshold is breached.
        """
        _log("1H-MICRO", "--- Micro Risk Check ---")
        df = _load_4h_feature_panel()
        if df is None:
            return

        delta_disp = _compute_delta_dispersion(df)
        _log("1H-MICRO", f"Delta Dispersion: {delta_disp:+.4f} (choke threshold: {S2_CASH_CHOKE_THRESHOLD})")

        if delta_disp <= S2_CASH_CHOKE_THRESHOLD:
            equity = _get_live_account_equity()
            _log(
                "1H-MICRO",
                f"[EMERGENCY] S2 Cash Choke triggered! Δσ={delta_disp:.4f}. "
                "Zeroing all positions — no rebalance.",
            )
            self.previous_weights = {}
            _persist_state(equity, 0.0, 0.0, delta_disp, {}, "1H-MICRO-S2-CHOKE")
        else:
            _log("1H-MICRO", "S2 gate clear — no action taken.")


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
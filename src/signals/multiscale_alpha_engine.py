import sys
import warnings
from pathlib import Path
from typing import Dict, Tuple, List

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf
from catboost import CatBoost

from src.backtest.backtest_models import OnlineMicrostructureHMM
from src.backtest.backtest_matured_ir import compute_ensemble_alpha
from src.backtest.backtest_optimizers import compute_hrp_from_cov, compute_null_space_carry
from src.signals.funding_forecaster import forecast_hourly_funding
from src.config import STRATEGY_CONFIG

FEATURE_COLS = [
    "ret_4h", "ret_24h", "ret_72h", "ret_168h",
    "volume_zscore_72h", "basis_spread", "vol_yang_zhang", "beta_btc"
]

class ProductionMultiScaleEngine:
    def __init__(self, m12: CatBoost = None, m48: CatBoost = None, m168: CatBoost = None):
        self.m12 = m12
        self.m48 = m48
        self.m168 = m168

    def generate_target_portfolio(
        self,
        df: pl.DataFrame,
        target_grp: int,
        preds_12_cache: Dict[int, dict] = None,
        preds_48_cache: Dict[int, dict] = None,
        preds_168_cache: Dict[int, dict] = None,
        matured_ic_hist: Dict[str, List[float]] = None,
        max_bull_lev: float = STRATEGY_CONFIG.portfolio.max_bull_leverage,
        s0_short_mult: float = STRATEGY_CONFIG.portfolio.s0_short_multiplier,
        carry_lev: float = STRATEGY_CONFIG.portfolio.target_carry_leverage,
        top_k: int = STRATEGY_CONFIG.portfolio.top_k_conviction,
        retrain_step: int = STRATEGY_CONFIG.regime_model.retrain_step_bars
    ) -> Tuple[Dict[str, float], dict]:
        cur_panel = df.filter(pl.col("group_id") == target_grp)
        if cur_panel.height == 0:
            return {}, {"status": "EMPTY_PANEL"}

        cur_rows = {r["symbol"]: r for r in cur_panel.iter_rows(named=True)}
        symbols = list(cur_rows.keys())

        # 1. Synchronize HMM Training Boundary & Sequential Markov Step
        block_start_grp = target_grp - ((target_grp - 1315) % retrain_step) if target_grp >= 1315 else target_grp
        train_end_grp = block_start_grp - 42
        train_start_grp = max(0, train_end_grp - 1080)

        hmm = OnlineMicrostructureHMM()
        btc_tr = df.filter((pl.col("symbol") == "BTC") & (pl.col("group_id") >= train_start_grp) & (pl.col("group_id") < train_end_grp)).sort("group_id")
        if btc_tr.height >= 100:
            hmm_obs = np.column_stack([
                btc_tr["vol_yang_zhang"].to_numpy(),
                btc_tr["volume_zscore_72h"].to_numpy(),
                btc_tr["basis_spread"].to_numpy()
            ])
            hmm.fit_from_training_observations(hmm_obs)

        # Step gamma sequentially from block_start_grp to target_grp
        for g in range(block_start_grp, target_grp + 1):
            pan_g = df.filter(pl.col("group_id") == g)
            b_g = pan_g.filter(pl.col("symbol") == "BTC")
            b_vol_g = float(b_g.select("vol_yang_zhang").to_series()[0]) if len(b_g) > 0 else 0.03
            obs_g = np.array([b_vol_g, float(pan_g.select(pl.mean("volume_zscore_72h")).to_series()[0]), 0.002])
            _, hmm_lev, dom_state = hmm.filter_step(obs_g)

        # 2. YetiRank Inference & Dynamic Alpha Scoring
        X_live = cur_panel.select(FEATURE_COLS).to_pandas()
        p12_arr = np.array([preds_12_cache[target_grp][s] for s in symbols]) if (preds_12_cache and target_grp in preds_12_cache) else self.m12.predict(X_live)
        p48_arr = np.array([preds_48_cache[target_grp][s] for s in symbols]) if (preds_48_cache and target_grp in preds_48_cache) else self.m48.predict(X_live)
        p168_arr = np.array([preds_168_cache[target_grp][s] for s in symbols]) if (preds_168_cache and target_grp in preds_168_cache) else self.m168.predict(X_live)

        alpha_vec = compute_ensemble_alpha(p12_arr, p48_arr, p168_arr, matured_ic_hist if matured_ic_hist is not None else {"12h":[],"48h":[],"168h":[]}, use_dynamic_ir=True)
        alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

        # 3. Covariance Estimation across Exactly 168 Discrete Bars
        hist = df.filter((pl.col("group_id") <= target_grp) & (pl.col("group_id") > target_grp - 168))
        piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
        v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]

        if len(v_cols) < 15:
            return {}, {"status": "INSUFFICIENT_UNIVERSE_DEPTH"}

        shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
        m_yz = float(cur_panel.select(pl.mean("vol_yang_zhang")).to_series()[0])
        vol_scaler = float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.60))

        target_lev = float(np.clip(hmm_lev * (max_bull_lev / 1.50) * vol_scaler, 0.50, max_bull_lev))

        # 4. Momentum & Orthogonal Carry Allocation
        a_sub = np.array([alpha_dict[s] for s in v_cols])
        b_sub = np.array([cur_rows[s]["beta_btc"] for s in v_cols])
        
        w_mom = compute_hrp_from_cov(shrunk_cov, a_sub, target_lev, top_k=top_k)
        if dom_state == 0:
            w_mom[w_mom < 0] *= s0_short_mult

        if carry_lev > 0:
            carry_y = np.array([forecast_hourly_funding(float(cur_rows[s]["basis_spread"]), float(cur_rows[s]["volume_zscore_72h"]), float(cur_rows[s]["ret_4h"]), float(cur_rows[s]["basis_spread"]))[1] for s in v_cols])
            w_car = compute_null_space_carry(shrunk_cov, carry_y, a_sub, b_sub, target_carry_leverage=carry_lev)
        else:
            w_car = np.zeros(len(v_cols))

        # 5. Master Portfolio Bounding
        w_comb = w_mom + w_car
        g_exp = np.sum(np.abs(w_comb))
        if g_exp > max_bull_lev:
            w_comb *= (max_bull_lev / g_exp)
        w_comb = np.clip(w_comb, -0.30, 0.30)

        target_weights = {v_cols[i]: float(w_comb[i]) for i in range(len(v_cols)) if abs(w_comb[i]) > 0.005}

        diagnostics = {
            "group_id": target_grp,
            "dominant_regime": dom_state,
            "target_gross_leverage": target_lev,
            "active_positions": len(target_weights),
            "gross_exposure": float(np.sum(np.abs(list(target_weights.values())))),
            "net_exposure": float(np.sum(list(target_weights.values())))
        }
        return target_weights, diagnostics

    def compute_live_targets(self, lake_file: Path = None) -> tuple[dict, dict]:
        """Canonical entrypoint invoked by Dagster dynamic_multiscale_alpha asset."""
        from pathlib import Path
        import polars as pl
        from catboost import CatBoost

        models_dir = Path.home() / "quant_pipeline" / "data" / "models"
        if self.m12 is None:
            self.m12 = CatBoost()
            self.m12.load_model(str(models_dir / "catboost_12h_reversion.cbm"))
        if self.m48 is None:
            self.m48 = CatBoost()
            self.m48.load_model(str(models_dir / "catboost_48h_drift.cbm"))
        if self.m168 is None:
            self.m168 = CatBoost()
            self.m168.load_model(str(models_dir / "catboost_168h_trend.cbm"))

        lake_path = lake_file or (Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_4h.parquet")
        df = pl.read_parquet(lake_path)
        
        # Ensure group_id exists by dense-ranking distinct 4H timestamps
        if "group_id" not in df.columns:
            unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
                pl.int_range(0, pl.len()).alias("group_id")
            )
            df = df.join(unique_ts, on="timestamp_ms", how="left")

        latest_grp = int(df.select(pl.max("group_id")).to_series()[0])

        # Execute institutional holdout architecture from centralized config
        target_weights, diag = self.generate_target_portfolio(
            df=df,
            target_grp=latest_grp,
            max_bull_lev=STRATEGY_CONFIG.portfolio.max_bull_leverage,
            s0_short_mult=STRATEGY_CONFIG.portfolio.s0_short_multiplier,
            carry_lev=STRATEGY_CONFIG.portfolio.target_carry_leverage,
            top_k=STRATEGY_CONFIG.portfolio.top_k_conviction,
            retrain_step=STRATEGY_CONFIG.regime_model.retrain_step_bars
        )

        # Map metadata keys required by Dagster asset definitions
        diag["dynamic_leverage"] = diag.get("target_gross_leverage", 2.00)
        diag["regime"] = diag.get("dominant_regime", 0)

        return target_weights, diag

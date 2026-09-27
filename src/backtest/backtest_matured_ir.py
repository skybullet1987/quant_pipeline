import numpy as np
import polars as pl
from scipy.stats import spearmanr
from typing import Dict, List

def process_matured_predictions(
    pred_ledger: Dict[str, Dict[int, dict]],
    matured_ic_history: Dict[str, List[float]],
    grp: int,
    cur_panel: pl.DataFrame,
    df: pl.DataFrame
):
    """P0 FIX: Evaluates matured predictions against exact residualized alpha targets."""
    target_col_map = {"12h": ("target_12h_alpha", 3), "48h": ("target_48h_drift", 12), "168h": ("target_168h_trend", 42)}

    for horizon, (target_col, delay) in target_col_map.items():
        mature_grp = grp - delay
        if mature_grp in pred_ledger[horizon]:
            old_preds = pred_ledger[horizon][mature_grp]
            # Fetch the actual realized point-in-time target row from group mature_grp
            past_panel = df.filter(pl.col("group_id") == mature_grp).to_dicts()
            past_targets = {r["symbol"]: r.get(target_col) for r in past_panel if r.get(target_col) is not None}
            
            common = [s for s in old_preds if s in past_targets]
            if len(common) >= 20:
                y_target = [past_targets[s] for s in common]
                y_pred = [old_preds[s] for s in common]
                ic, _ = spearmanr(y_pred, y_target)
                if not np.isnan(ic):
                    matured_ic_history[horizon].append(ic)
            del pred_ledger[horizon][mature_grp]

def compute_ensemble_alpha(p12: np.ndarray, p48: np.ndarray, p168: np.ndarray, matured_ic_history: Dict[str, List[float]], use_dynamic_ir: bool) -> np.ndarray:
    if use_dynamic_ir and len(matured_ic_history["168h"]) >= 5:
        # Calculate Rolling IC-IR Stability Score
        ir_12 = max(0.02, float(np.mean(matured_ic_history["12h"][-30:]) / (np.std(matured_ic_history["12h"][-30:]) + 1e-6)))
        ir_48 = max(0.02, float(np.mean(matured_ic_history["48h"][-30:]) / (np.std(matured_ic_history["48h"][-30:]) + 1e-6)))
        ir_168 = max(0.02, float(np.mean(matured_ic_history["168h"][-30:]) / (np.std(matured_ic_history["168h"][-30:]) + 1e-6)))
        raw_w = np.array([ir_12**2, ir_48**2, ir_168**2]) / (ir_12**2 + ir_48**2 + ir_168**2 + 1e-8)
        norm_w = np.clip(raw_w, 0.10, 0.60)
        norm_w /= np.sum(norm_w)
        return (norm_w[0] * p12) + (norm_w[1] * p48) + (norm_w[2] * p168)
    return (0.30 * p12) + (0.45 * p48) + (0.25 * p168)

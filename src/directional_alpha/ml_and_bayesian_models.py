"""Pure-Python Statistical, Bayesian & Calibrated ML Models for Polymarket Directional Alpha.

Strictly zero-numpy / zero-pandas stdlib implementation supporting both:
- `.venv\\Scripts\\python.exe` (Python 3.12.10)
- `C:\\Program Files\\LibreOffice\\program\\python.exe` (Python 3.12.14)

Anti-Leakage & ML Best-Practices Guarantees (RT-07 / RT-01 / RT-06):
1. `CausalFeaturePreprocessor` fits missing-value medians, missingness indicators,
   bounded nominal one-hot encodings, and mean/std standardization STRICTLY on the
   training split (`fit_split_tag == "TRAIN_ONLY"`), raising if transformed before fit.
2. All probability models anchor on or benchmark against market-implied log-odds
   `logit(p_market)` with explicit L2 / empirical-Bayes shrinkage so noisy slices
   revert smoothly toward market efficiency rather than overfitting small samples.
3. Calibration (`PlattCalibrator`, `IsotonicCalibrator` via exact Pool-Adjacent-Violators)
   is fit exclusively on an inner chronological validation slice of the Training split.
4. `ContextualHedgeAllocator` updates expert weights at time `t` ONLY from trades whose
   realized exit/settlement timestamp satisfies `exit_ts <= t` (zero look-ahead into
   open positions).
"""

from __future__ import annotations

import bisect
import collections
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


EPS_PROB = 1e-6


def clip_prob(p: float, eps: float = EPS_PROB) -> float:
    """Clamps a probability strictly inside `(eps, 1 - eps)`."""
    if math.isnan(p) or math.isinf(p):
        return 0.5
    return max(eps, min(1.0 - eps, float(p)))


def logit(p: float) -> float:
    """ Safe log-odds transform `log(p / (1 - p))`."""
    pc = clip_prob(p, 1e-5)
    return math.log(pc / (1.0 - pc))


def sigmoid(z: float) -> float:
    """Numerically stable logistic sigmoid."""
    if math.isnan(z):
        return 0.5
    zc = max(-30.0, min(30.0, float(z)))
    if zc >= 0.0:
        ez = math.exp(-zc)
        return 1.0 / (1.0 + ez)
    ez = math.exp(zc)
    return ez / (1.0 + ez)


# ==============================================================================
# 1. PROPER SCORING RULES, CALIBRATION & CLASSIFICATION DIAGNOSTICS
# ==============================================================================


def brier_score(probs: Sequence[float], outcomes: Sequence[int]) -> float:
    """Mean squared probability error `mean((p_i - y_i)^2)`."""
    n = min(len(probs), len(outcomes))
    if n == 0:
        return 0.0
    total = 0.0
    for i in range(n):
        diff = clip_prob(probs[i]) - float(outcomes[i])
        total += diff * diff
    return total / n


def brier_skill_score(
    model_probs: Sequence[float],
    baseline_probs: Sequence[float],
    outcomes: Sequence[int],
) -> float:
    """Brier Skill Score `1 - BS_model / BS_baseline` (>0 means beats market baseline)."""
    bs_base = brier_score(baseline_probs, outcomes)
    if bs_base <= 1e-12:
        return 0.0
    bs_mod = brier_score(model_probs, outcomes)
    return 1.0 - (bs_mod / bs_base)


def log_loss(probs: Sequence[float], outcomes: Sequence[float], eps: float = 1e-6) -> float:
    """Bernoulli cross-entropy loss `-mean(y*log(p) + (1-y)*log(1-p))` supporting continuous [0, 1] payouts."""
    n = min(len(probs), len(outcomes))
    if n == 0:
        return 0.0
    total = 0.0
    for i in range(n):
        p = clip_prob(probs[i], eps)
        y = max(0.0, min(1.0, float(outcomes[i])))
        total -= y * math.log(p) + (1.0 - y) * math.log(1.0 - p)
    return total / n


def expected_calibration_error(
    probs: Sequence[float],
    outcomes: Sequence[float],
    n_bins: int = 10,
) -> Dict[str, Any]:
    """Computes Expected Calibration Error (ECE) and reliability curve bins."""
    n = min(len(probs), len(outcomes))
    if n == 0:
        return {"ece": 0.0, "max_ce": 0.0, "n_samples": 0, "bins": []}
    k = max(2, int(n_bins))
    bin_preds: List[List[float]] = [[] for _ in range(k)]
    bin_ys: List[List[float]] = [[] for _ in range(k)]
    for i in range(n):
        p = clip_prob(probs[i])
        idx = min(k - 1, int(p * k))
        bin_preds[idx].append(p)
        bin_ys[idx].append(max(0.0, min(1.0, float(outcomes[i]))))

    ece = 0.0
    max_ce = 0.0
    bins_out: List[Dict[str, Any]] = []
    for b in range(k):
        cnt = len(bin_preds[b])
        lo = b / k
        hi = (b + 1) / k
        if cnt == 0:
            bins_out.append(
                {
                    "bin_index": b,
                    "bin_lo": round(lo, 4),
                    "bin_hi": round(hi, 4),
                    "count": 0,
                    "mean_pred": None,
                    "empirical_freq": None,
                    "abs_gap": 0.0,
                }
            )
            continue
        mp = sum(bin_preds[b]) / cnt
        ef = sum(bin_ys[b]) / cnt
        gap = abs(mp - ef)
        ece += (cnt / n) * gap
        if gap > max_ce:
            max_ce = gap
        bins_out.append(
            {
                "bin_index": b,
                "bin_lo": round(lo, 4),
                "bin_hi": round(hi, 4),
                "count": cnt,
                "mean_pred": round(mp, 5),
                "empirical_freq": round(ef, 5),
                "abs_gap": round(gap, 5),
            }
        )
    return {
        "ece": round(ece, 6),
        "max_ce": round(max_ce, 6),
        "n_samples": n,
        "bins": bins_out,
    }


def confusion_and_classification_metrics(
    probs: Sequence[float],
    outcomes: Sequence[int],
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Confusion matrix + precision/recall/F1/accuracy diagnostics."""
    n = min(len(probs), len(outcomes))
    tp = fp = tn = fn = 0
    for i in range(n):
        pred = 1 if clip_prob(probs[i]) >= threshold else 0
        y = 1 if int(outcomes[i]) == 1 else 0
        if pred == 1 and y == 1:
            tp += 1
        elif pred == 1 and y == 0:
            fp += 1
        elif pred == 0 and y == 0:
            tn += 1
        else:
            fn += 1
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2.0 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    acc = (tp + tn) / n if n > 0 else 0.0
    return {
        "n": n,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": round(acc, 5),
        "precision": round(prec, 5),
        "recall": round(rec, 5),
        "f1": round(f1, 5),
    }


# ==============================================================================
# 2. STRICT TRAIN-ONLY FEATURE PREPROCESSOR (RT-07 / ML Best Practices)
# ==============================================================================


@dataclass
class CausalFeaturePreprocessor:
    """Leak-free numeric + categorical feature pipeline fit strictly on Train data.

    - Tracks missing-value frequency per feature.
    - Adds binary `is_missing_<col>` indicators for numeric columns with missingness
      (or all specified `missing_indicator_cols`) so missingness is informative.
    - Imputes missing numeric values with Train median (defaulting to 0.0 if all missing).
    - Standardizes numeric columns using Train mean/std, clipped to `[-clip_z, +clip_z]`.
    - Encodes nominal columns via bounded top-K one-hot encoding + `OTHER` fallback.
    """

    numeric_cols: List[str]
    categorical_cols: List[str] = field(default_factory=list)
    max_categories_per_col: int = 12
    clip_z: float = 6.0
    always_emit_missing_indicators: bool = True

    fitted: bool = field(default=False, init=False)
    fit_split_tag: str = field(default="UNFITTED", init=False)
    fit_row_count: int = field(default=0, init=False)
    fit_max_timestamp: Optional[float] = field(default=None, init=False)

    num_medians: Dict[str, float] = field(default_factory=dict, init=False)
    num_means: Dict[str, float] = field(default_factory=dict, init=False)
    num_stds: Dict[str, float] = field(default_factory=dict, init=False)
    missing_rates: Dict[str, float] = field(default_factory=dict, init=False)
    cat_vocab: Dict[str, List[str]] = field(default_factory=dict, init=False)
    output_feature_names: List[str] = field(default_factory=list, init=False)

    def fit(
        self,
        records: Sequence[Dict[str, Any]],
        split_tag: str = "TRAIN_ONLY",
        timestamp_col: str = "entry_ts",
    ) -> "CausalFeaturePreprocessor":
        if split_tag != "TRAIN_ONLY":
            raise ValueError(
                f"RT-07 violation: CausalFeaturePreprocessor must be fit on 'TRAIN_ONLY', got {split_tag!r}"
            )
        n = len(records)
        self.fit_row_count = n
        self.fit_split_tag = split_tag
        max_ts: Optional[float] = None
        for r in records:
            ts_val = r.get(timestamp_col)
            if ts_val is not None:
                ts_f = float(ts_val)
                if max_ts is None or ts_f > max_ts:
                    max_ts = ts_f
        self.fit_max_timestamp = max_ts

        self.num_medians.clear()
        self.num_means.clear()
        self.num_stds.clear()
        self.missing_rates.clear()
        self.cat_vocab.clear()
        self.output_feature_names = []

        for col in self.numeric_cols:
            vals: List[float] = []
            miss_cnt = 0
            for r in records:
                v = r.get(col)
                if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                    miss_cnt += 1
                else:
                    try:
                        vf = float(v)
                        if math.isnan(vf) or math.isinf(vf):
                            miss_cnt += 1
                        else:
                            vals.append(vf)
                    except (TypeError, ValueError):
                        miss_cnt += 1
            self.missing_rates[col] = (miss_cnt / n) if n > 0 else 0.0
            med = statistics.median(vals) if vals else 0.0
            self.num_medians[col] = float(med)
            imputed = vals + [med] * miss_cnt if n > 0 else [0.0]
            mu = sum(imputed) / len(imputed)
            var = sum((x - mu) ** 2 for x in imputed) / max(1, len(imputed))
            sd = math.sqrt(var)
            self.num_means[col] = float(mu)
            self.num_stds[col] = float(sd) if sd > 1e-8 else 1.0
            self.output_feature_names.append(col)
            if self.always_emit_missing_indicators or miss_cnt > 0:
                self.output_feature_names.append(f"is_missing_{col}")

        for ccol in self.categorical_cols:
            counts: collections.Counter[str] = collections.Counter()
            miss_c = 0
            for r in records:
                raw = r.get(ccol)
                if raw is None or str(raw).strip() == "":
                    miss_c += 1
                    counts["__MISSING__"] += 1
                else:
                    counts[str(raw).strip().upper()] += 1
            self.missing_rates[ccol] = (miss_c / n) if n > 0 else 0.0
            top_cats = [k for k, _ in counts.most_common(self.max_categories_per_col)]
            if "__OTHER__" not in top_cats:
                top_cats.append("__OTHER__")
            self.cat_vocab[ccol] = top_cats
            for tok in top_cats:
                self.output_feature_names.append(f"{ccol}=={tok}")

        self.fitted = True
        return self

    def transform_one(self, record: Dict[str, Any]) -> List[float]:
        if not self.fitted:
            raise RuntimeError("CausalFeaturePreprocessor.transform_one called before fit()!")
        vec: List[float] = []
        for col in self.numeric_cols:
            v = record.get(col)
            is_miss = 0.0
            if v is None:
                is_miss = 1.0
                vf = self.num_medians[col]
            else:
                try:
                    vf = float(v)
                    if math.isnan(vf) or math.isinf(vf):
                        is_miss = 1.0
                        vf = self.num_medians[col]
                except (TypeError, ValueError):
                    is_miss = 1.0
                    vf = self.num_medians[col]
            z = (vf - self.num_means[col]) / self.num_stds[col]
            z = max(-self.clip_z, min(self.clip_z, z))
            vec.append(z)
            if self.always_emit_missing_indicators or f"is_missing_{col}" in self.output_feature_names:
                if f"is_missing_{col}" in self.output_feature_names:
                    vec.append(is_miss)

        for ccol in self.categorical_cols:
            raw = record.get(ccol)
            val_s = "__MISSING__" if (raw is None or str(raw).strip() == "") else str(raw).strip().upper()
            vocab = self.cat_vocab[ccol]
            matched = val_s if val_s in vocab else "__OTHER__"
            for tok in vocab:
                vec.append(1.0 if tok == matched else 0.0)
        return vec

    def transform(self, records: Sequence[Dict[str, Any]]) -> List[List[float]]:
        return [self.transform_one(r) for r in records]

    def summary(self) -> Dict[str, Any]:
        return {
            "fitted": self.fitted,
            "fit_split_tag": self.fit_split_tag,
            "fit_row_count": self.fit_row_count,
            "fit_max_timestamp": self.fit_max_timestamp,
            "n_output_features": len(self.output_feature_names),
            "missing_rates": {k: round(v, 5) for k, v in self.missing_rates.items()},
        }


# ==============================================================================
# 3. PILLAR 4A: BAYESIAN BETA-BINOMIAL & SEQUENTIAL LOG-ODDS KALMAN UPDATER
# ==============================================================================


class BayesianBetaCalibrationModel:
    """Hierarchical Empirical-Bayes Beta-Binomial probability calibrator.

    Buckets contracts by `(category, price_bucket, horizon_bucket)` on the Training
    set, anchoring each cell on a market-implied Beta prior of effective sample size
    `prior_strength` centered on the cell's average market price:
        alpha_post = prior_strength * p_mkt_bar + sum_w_yes
        beta_post  = prior_strength * (1 - p_mkt_bar) + sum_w_no
    Uses cluster-inverse weights (`1 / cluster_size`) so correlated multi-outcome legs
    cannot artificially shrink epistemic variance (`RT-06`).
    """

    def __init__(self, prior_strength: float = 24.0, n_price_bins: int = 10) -> None:
        self.prior_strength = max(2.0, float(prior_strength))
        self.n_price_bins = max(4, int(n_price_bins))
        self._cells: Dict[Tuple[str, int, str], Tuple[float, float, float]] = {}
        self._cat_cells: Dict[Tuple[str, int], Tuple[float, float, float]] = {}
        self._global_cells: Dict[int, Tuple[float, float, float]] = {}
        self.fitted = False

    def _p_bin(self, p_mkt: float) -> int:
        return min(self.n_price_bins - 1, max(0, int(clip_prob(p_mkt) * self.n_price_bins)))

    @staticmethod
    def _h_bucket(tte_hours: float) -> str:
        if tte_hours <= 6.0:
            return "SHORT_6H"
        if tte_hours <= 72.0:
            return "MED_3D"
        return "LONG_3D_PLUS"

    def fit(
        self,
        records: Sequence[Dict[str, Any]],
        outcomes: Sequence[int],
        sample_weights: Optional[Sequence[float]] = None,
    ) -> "BayesianBetaCalibrationModel":
        n = min(len(records), len(outcomes))
        w_arr = list(sample_weights) if sample_weights is not None else [1.0] * n
        cell_acc: Dict[Tuple[str, int, str], List[float]] = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
        cat_acc: Dict[Tuple[str, int], List[float]] = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
        glob_acc: Dict[int, List[float]] = collections.defaultdict(lambda: [0.0, 0.0, 0.0])

        for i in range(n):
            r = records[i]
            w = max(0.01, float(w_arr[i]))
            p_m = clip_prob(float(r.get("p_market", 0.5)))
            cat = str(r.get("category", "OTHER")).upper()
            tte_h = float(r.get("tte_hours", 24.0) or 24.0)
            pb = self._p_bin(p_m)
            hb = self._h_bucket(tte_h)
            y = 1.0 if int(outcomes[i]) == 1 else 0.0

            for store, key in (
                (cell_acc, (cat, pb, hb)),
                (cat_acc, (cat, pb)),
                (glob_acc, pb),
            ):
                acc = store[key]  # [sum_w_y, sum_w_n, sum_w_pm]
                acc[0] += w * y
                acc[1] += w * (1.0 - y)
                acc[2] += w * p_m

        self._cells = {k: (v[0], v[1], v[2]) for k, v in cell_acc.items()}
        self._cat_cells = {k: (v[0], v[1], v[2]) for k, v in cat_acc.items()}
        self._global_cells = {k: (v[0], v[1], v[2]) for k, v in glob_acc.items()}
        self.fitted = True
        return self

    def predict_with_uncertainty(self, record: Dict[str, Any]) -> Tuple[float, float]:
        """Returns `(p_posterior, sigma_epistemic)`."""
        p_m = clip_prob(float(record.get("p_market", 0.5)))
        if not self.fitted:
            return p_m, 0.08
        cat = str(record.get("category", "OTHER")).upper()
        tte_h = float(record.get("tte_hours", 24.0) or 24.0)
        pb = self._p_bin(p_m)
        hb = self._h_bucket(tte_h)

        # Hierarchical shrinkage: Global bin -> Category bin -> Full (Cat, Bin, Horizon) cell
        g_y, g_n, g_pm = self._global_cells.get(pb, (0.0, 0.0, 0.0))
        g_tot = g_y + g_n
        if g_tot > 1.0:
            g_mkt_bar = g_pm / g_tot
            g_rate = (self.prior_strength * g_mkt_bar + g_y) / (self.prior_strength + g_tot)
            delta_glob = logit(g_rate) - logit(g_mkt_bar)
        else:
            delta_glob = 0.0

        c_y, c_n, c_pm = self._cat_cells.get((cat, pb), (0.0, 0.0, 0.0))
        c_tot = c_y + c_n
        prior_cat_p = sigmoid(logit(p_m) + 0.5 * delta_glob)
        if c_tot > 1.0:
            c_mkt_bar = c_pm / c_tot
            prior_anchor = sigmoid(logit(c_mkt_bar) + 0.5 * delta_glob)
            c_rate = (self.prior_strength * prior_anchor + c_y) / (self.prior_strength + c_tot)
            delta_cat = logit(c_rate) - logit(c_mkt_bar)
        else:
            delta_cat = 0.5 * delta_glob

        s_y, s_n, s_pm = self._cells.get((cat, pb, hb), (0.0, 0.0, 0.0))
        s_tot = s_y + s_n
        if s_tot > 0.5:
            s_mkt_bar = s_pm / s_tot
            cell_anchor = sigmoid(logit(s_mkt_bar) + delta_cat)
            alpha_eff = self.prior_strength * cell_anchor + s_y
            beta_eff = self.prior_strength * (1.0 - cell_anchor) + s_n
            cell_rate = alpha_eff / (alpha_eff + beta_eff)
            delta_cell = logit(cell_rate) - logit(s_mkt_bar)
            eff_n = self.prior_strength + s_tot
        else:
            delta_cell = delta_cat
            eff_n = self.prior_strength + 0.5 * c_tot

        # Apply learned calibration shift in log-odds space around exact current p_m
        p_post = sigmoid(logit(p_m) + max(-0.85, min(0.85, delta_cell)))
        var_post = (p_post * (1.0 - p_post)) / (eff_n + 1.0)
        sigma_p = math.sqrt(max(1e-6, var_post))
        return clip_prob(p_post), min(0.25, max(0.005, sigma_p))


class SequentialLogOddsKalman:
    """1D Causal Log-Odds Kalman Filter separating information drift from spread bounce."""

    def __init__(
        self,
        process_var_per_hour: float = 0.035,
        base_obs_var: float = 0.06,
    ) -> None:
        self.process_var_per_hour = max(1e-5, float(process_var_per_hour))
        self.base_obs_var = max(1e-5, float(base_obs_var))

    def filter_trajectory(
        self,
        timestamps: Sequence[float],
        prices: Sequence[float],
        spreads: Optional[Sequence[float]] = None,
    ) -> Tuple[List[float], List[float], List[float]]:
        """Runs strictly causal forward pass returning `(filtered_p, kalman_velocity, sigma_p)`."""
        n = min(len(timestamps), len(prices))
        if n == 0:
            return [], [], []
        out_p: List[float] = []
        out_vel: List[float] = []
        out_sig: List[float] = []

        theta = logit(prices[0])
        var_state = 0.08
        vel = 0.0

        for i in range(n):
            z_obs = logit(prices[i])
            sp = float(spreads[i]) if (spreads is not None and i < len(spreads)) else 0.02
            p_cur = clip_prob(prices[i])
            # Convert price-space spread noise into log-odds variance via delta method: d(logit)/dp = 1/(p(1-p))
            jac = 1.0 / max(0.03, p_cur * (1.0 - p_cur))
            r_obs = self.base_obs_var + ((0.5 * max(0.005, sp) * jac) ** 2)

            if i > 0:
                dt_h = max(1.0 / 3600.0, (float(timestamps[i]) - float(timestamps[i - 1])) / 3600.0)
                q_proc = self.process_var_per_hour * min(48.0, dt_h)
                var_pred = var_state + q_proc
                k_gain = var_pred / (var_pred + r_obs)
                innov = z_obs - theta
                prev_theta = theta
                theta = theta + k_gain * innov
                var_state = max(1e-5, (1.0 - k_gain) * var_pred)
                inst_vel = (theta - prev_theta) / max(0.05, math.sqrt(dt_h))
                vel = 0.65 * vel + 0.35 * inst_vel
            else:
                var_state = r_obs * 0.5
                vel = 0.0

            pf = sigmoid(theta)
            sig_p = pf * (1.0 - pf) * math.sqrt(var_state)
            out_p.append(pf)
            out_vel.append(vel)
            out_sig.append(min(0.25, max(0.005, sig_p)))
        return out_p, out_vel, out_sig


# ==============================================================================
# 4. PROBABILITY CALIBRATORS: PLATT SIGMOID & POOL-ADJACENT-VIOLATORS ISOTONIC
# ==============================================================================


class PlattCalibrator:
    """2-parameter Platt scaling in log-odds space `sigmoid(a * logit(p) + b)`."""

    def __init__(self, l2_reg: float = 1e-2, max_iter: int = 40) -> None:
        self.l2_reg = max(1e-5, float(l2_reg))
        self.max_iter = max(5, int(max_iter))
        self.a: float = 1.0
        self.b: float = 0.0
        self.fitted: bool = False

    def fit(
        self,
        raw_probs: Sequence[float],
        outcomes: Sequence[int],
        sample_weights: Optional[Sequence[float]] = None,
    ) -> "PlattCalibrator":
        n = min(len(raw_probs), len(outcomes))
        if n < 12:
            self.a, self.b, self.fitted = 1.0, 0.0, True
            return self
        zs = [logit(p) for p in raw_probs[:n]]
        ys = [1.0 if int(y) == 1 else 0.0 for y in outcomes[:n]]
        ws = [max(0.01, float(sample_weights[i])) if sample_weights is not None else 1.0 for i in range(n)]

        # 2x2 damped Newton steps around identity (a=1, b=0)
        a, b = 1.0, 0.0
        for _ in range(self.max_iter):
            g_a = self.l2_reg * (a - 1.0)
            g_b = self.l2_reg * b
            h_aa = self.l2_reg
            h_ab = 0.0
            h_bb = self.l2_reg
            for i in range(n):
                p = sigmoid(a * zs[i] + b)
                w_i = ws[i]
                err = p - ys[i]
                g_a += w_i * err * zs[i]
                g_b += w_i * err
                curvature = w_i * max(1e-5, p * (1.0 - p))
                h_aa += curvature * zs[i] * zs[i]
                h_ab += curvature * zs[i]
                h_bb += curvature
            det = h_aa * h_bb - h_ab * h_ab
            if abs(det) <= 1e-10:
                break
            da = (h_bb * g_a - h_ab * g_b) / det
            db = (-h_ab * g_a + h_aa * g_b) / det
            a = max(0.15, min(3.0, a - 0.5 * da))
            b = max(-1.5, min(1.5, b - 0.5 * db))
            if abs(da) + abs(db) < 1e-5:
                break
        self.a, self.b, self.fitted = a, b, True
        return self

    def transform_one(self, p: float) -> float:
        if not self.fitted:
            return clip_prob(p)
        return clip_prob(sigmoid(self.a * logit(p) + self.b))

    def transform(self, probs: Sequence[float]) -> List[float]:
        return [self.transform_one(p) for p in probs]


class IsotonicCalibrator:
    """Exact pure-Python Pool-Adjacent-Violators Algorithm (PAVA) isotonic calibrator."""

    def __init__(self, min_samples: int = 25, laplace_smooth: float = 0.5) -> None:
        self.min_samples = max(8, int(min_samples))
        self.laplace_smooth = max(0.0, float(laplace_smooth))
        self._xs: List[float] = []
        self._ys: List[float] = []
        self.fitted: bool = False

    def fit(
        self,
        raw_probs: Sequence[float],
        outcomes: Sequence[int],
        sample_weights: Optional[Sequence[float]] = None,
    ) -> "IsotonicCalibrator":
        n = min(len(raw_probs), len(outcomes))
        if n < self.min_samples:
            self._xs = [0.0, 1.0]
            self._ys = [0.0, 1.0]
            self.fitted = True
            return self
        ws = [max(0.01, float(sample_weights[i])) if sample_weights is not None else 1.0 for i in range(n)]
        order = sorted(range(n), key=lambda idx: clip_prob(raw_probs[idx]))

        # Each block: [x_min, x_max, sum_wy, sum_w]
        blocks: List[List[float]] = []
        for idx in order:
            px = clip_prob(raw_probs[idx])
            w = ws[idx]
            # Mild shrink toward px on tiny blocks prevents 0.0 / 1.0 boundary collapse
            wy = w * (1.0 if int(outcomes[idx]) == 1 else 0.0) + self.laplace_smooth * px
            wt = w + self.laplace_smooth
            if blocks and abs(blocks[-1][1] - px) < 1e-7:
                blocks[-1][1] = px
                blocks[-1][2] += wy
                blocks[-1][3] += wt
            else:
                blocks.append([px, px, wy, wt])

            while len(blocks) >= 2:
                v_prev = blocks[-2][2] / blocks[-2][3]
                v_curr = blocks[-1][2] / blocks[-1][3]
                if v_prev <= v_curr + 1e-12:
                    break
                b_last = blocks.pop()
                blocks[-1][1] = b_last[1]
                blocks[-1][2] += b_last[2]
                blocks[-1][3] += b_last[3]

        xs: List[float] = []
        ys: List[float] = []
        for b in blocks:
            mid_x = 0.5 * (b[0] + b[1])
            val_y = clip_prob(b[2] / b[3], 1e-3)
            xs.append(mid_x)
            ys.append(val_y)
        self._xs = xs
        self._ys = ys
        self.fitted = True
        return self

    def transform_one(self, p: float) -> float:
        px = clip_prob(p)
        if not self.fitted or not self._xs:
            return px
        if len(self._xs) == 1:
            return clip_prob(0.5 * px + 0.5 * self._ys[0])
        pos = bisect.bisect_left(self._xs, px)
        if pos <= 0:
            return self._ys[0]
        if pos >= len(self._xs):
            return self._ys[-1]
        x0, x1 = self._xs[pos - 1], self._xs[pos]
        y0, y1 = self._ys[pos - 1], self._ys[pos]
        if x1 - x0 <= 1e-9:
            return 0.5 * (y0 + y1)
        alpha = (px - x0) / (x1 - x0)
        return clip_prob(y0 + alpha * (y1 - y0))

    def transform(self, probs: Sequence[float]) -> List[float]:
        return [self.transform_one(p) for p in probs]


# ==============================================================================
# 5. PILLAR 4B: PURE-PYTHON L2 LOGISTIC REGRESSION (MARKET-OFFSET RESIDUAL)
# ==============================================================================


class RegularizedLogisticRegression:
    """Pure-Python L2-regularized Bernoulli Logistic Regression with Market Log-Odds Offset.

    Models:
        `logit(P(Y=1 | x, p_mkt)) = logit(p_mkt) + b + w^T x`   (when `use_market_offset=True`)
    so `w = 0, b = 0` recovers exact market-implied efficiency (`p_hat == p_mkt`)!
    Strong L2 penalty `l2_lambda` ensures features only move `p_hat` away from `p_mkt`
    when backed by genuine Training evidence. Also estimates diagonal Laplace posterior
    weight variance `diag(H^-1)` to provide per-prediction epistemic `sigma_p`!
    """

    def __init__(
        self,
        l2_lambda: float = 5.0,
        learning_rate: float = 0.08,
        max_epochs: int = 120,
        use_market_offset: bool = True,
        calibration: str = "platt",  # "none" | "platt" | "isotonic"
    ) -> None:
        self.l2_lambda = max(1e-4, float(l2_lambda))
        self.learning_rate = max(1e-4, float(learning_rate))
        self.max_epochs = max(10, int(max_epochs))
        self.use_market_offset = bool(use_market_offset)
        self.calibration = str(calibration).lower()

        self.weights: List[float] = []
        self.bias: float = 0.0
        self._weight_vars: List[float] = []
        self._bias_var: float = 0.01
        self._calibrator: Optional[Any] = None
        self.fitted: bool = False

    def fit(
        self,
        X: Sequence[Sequence[float]],
        outcomes: Sequence[int],
        market_probs: Optional[Sequence[float]] = None,
        sample_weights: Optional[Sequence[float]] = None,
    ) -> "RegularizedLogisticRegression":
        n = min(len(X), len(outcomes))
        if n == 0:
            self.weights = []
            self.bias = 0.0
            self.fitted = True
            return self
        d = len(X[0])
        # Reserve final 20% of chronological Training rows for post-hoc calibration if n >= 40
        if self.calibration in ("platt", "isotonic") and n >= 40:
            n_core = max(20, int(0.80 * n))
        else:
            n_core = n

        w = [0.0] * d
        b = 0.0
        ws = [max(0.01, float(sample_weights[i])) if sample_weights is not None else 1.0 for i in range(n)]
        offsets = [
            logit(market_probs[i]) if (self.use_market_offset and market_probs is not None) else 0.0
            for i in range(n)
        ]
        ys = [1.0 if int(outcomes[i]) == 1 else 0.0 for i in range(n)]
        w_sum_core = max(1.0, sum(ws[:n_core]))

        # Adaptive diagonal Hessian preconditioned batch updates (fast & monotone convergence)
        for epoch in range(self.max_epochs):
            grad_w = [self.l2_lambda * w[j] for j in range(d)]
            grad_b = 0.25 * self.l2_lambda * b
            hess_w = [self.l2_lambda for _ in range(d)]
            hess_b = 0.25 * self.l2_lambda

            for i in range(n_core):
                xi = X[i]
                z = offsets[i] + b
                for j in range(d):
                    z += w[j] * xi[j]
                p = sigmoid(z)
                wi = ws[i]
                err = wi * (p - ys[i])
                curv = wi * max(1e-4, p * (1.0 - p))
                grad_b += err
                hess_b += curv
                for j in range(d):
                    xij = xi[j]
                    if xij != 0.0:
                        grad_w[j] += err * xij
                        hess_w[j] += curv * xij * xij

            step_scale = min(0.65, self.learning_rate * math.sqrt(w_sum_core / 50.0) + 0.25 / (1.0 + 0.05 * epoch))
            max_delta = 0.0
            db = step_scale * (grad_b / max(1e-6, hess_b))
            b = max(-2.5, min(2.5, b - db))
            max_delta = max(max_delta, abs(db))
            for j in range(d):
                dw = step_scale * (grad_w[j] / max(1e-6, hess_w[j]))
                w[j] = max(-2.5, min(2.5, w[j] - dw))
                if abs(dw) > max_delta:
                    max_delta = abs(dw)
            if max_delta < 1e-5:
                break

        # Compute diagonal Laplace inverse Hessian for epistemic uncertainty
        hess_diag = [self.l2_lambda for _ in range(d)]
        hess_b_final = 0.25 * self.l2_lambda
        for i in range(n_core):
            xi = X[i]
            z = offsets[i] + b + sum(w[j] * xi[j] for j in range(d))
            p = sigmoid(z)
            curv = ws[i] * max(1e-4, p * (1.0 - p))
            hess_b_final += curv
            for j in range(d):
                hess_diag[j] += curv * xi[j] * xi[j]

        self.weights = w
        self.bias = b
        self._weight_vars = [1.0 / max(1e-4, hd) for hd in hess_diag]
        self._bias_var = 1.0 / max(1e-4, hess_b_final)
        self.fitted = True

        # Inner chronological calibration on [n_core : n] (still strictly inside Train!)
        self._calibrator = None
        if n > n_core:
            raw_cal = [
                self._raw_prob_one(X[i], market_probs[i] if market_probs is not None else 0.5)
                for i in range(n_core, n)
            ]
            y_cal = outcomes[n_core:n]
            w_cal = ws[n_core:n]
            if self.calibration == "isotonic" and len(raw_cal) >= 25:
                self._calibrator = IsotonicCalibrator().fit(raw_cal, y_cal, w_cal)
            elif self.calibration in ("platt", "isotonic"):
                self._calibrator = PlattCalibrator(l2_reg=0.1).fit(raw_cal, y_cal, w_cal)
        return self

    def _raw_prob_one(self, x: Sequence[float], p_market: float = 0.5) -> float:
        off = logit(p_market) if self.use_market_offset else 0.0
        d = min(len(self.weights), len(x))
        z = off + self.bias + sum(self.weights[j] * float(x[j]) for j in range(d))
        return clip_prob(sigmoid(z))

    def predict_with_uncertainty(self, x: Sequence[float], p_market: float = 0.5) -> Tuple[float, float]:
        if not self.fitted:
            return clip_prob(p_market), 0.08
        p_raw = self._raw_prob_one(x, p_market)
        p_cal = self._calibrator.transform_one(p_raw) if self._calibrator is not None else p_raw
        d = min(len(self._weight_vars), len(x))
        var_z = self._bias_var + sum(self._weight_vars[j] * (float(x[j]) ** 2) for j in range(d))
        sigma_p = p_cal * (1.0 - p_cal) * math.sqrt(max(1e-6, var_z))
        return clip_prob(p_cal), min(0.25, max(0.005, sigma_p))

    def predict_proba(
        self,
        X: Sequence[Sequence[float]],
        market_probs: Optional[Sequence[float]] = None,
    ) -> List[float]:
        return [
            self.predict_with_uncertainty(
                X[i],
                market_probs[i] if (market_probs is not None and i < len(market_probs)) else 0.5,
            )[0]
            for i in range(len(X))
        ]

    def feature_importances(self, feature_names: Optional[Sequence[str]] = None) -> List[Tuple[str, float]]:
        names = (
            list(feature_names)
            if (feature_names is not None and len(feature_names) == len(self.weights))
            else [f"f_{j}" for j in range(len(self.weights))]
        )
        pairs = [(names[j], round(self.weights[j], 6)) for j in range(len(self.weights))]
        pairs.sort(key=lambda kv: abs(kv[1]), reverse=True)
        return pairs


# ==============================================================================
# 6. PILLAR 4C: HISTOGRAM GRADIENT-BOOSTED SHALLOW TREES & REGIME ENSEMBLE
# ==============================================================================


@dataclass
class _TreeNode:
    is_leaf: bool
    leaf_value: float = 0.0
    feature_idx: int = -1
    threshold: float = 0.0
    gain: float = 0.0
    left: Optional["_TreeNode"] = None
    right: Optional["_TreeNode"] = None

    def predict(self, x: Sequence[float]) -> float:
        node = self
        while not node.is_leaf:
            val = float(x[node.feature_idx]) if node.feature_idx < len(x) else 0.0
            node = node.left if (val <= node.threshold and node.left is not None) else node.right  # type: ignore[assignment]
            if node is None:
                return 0.0
        return node.leaf_value


class GradientBoostedProbTrees:
    """Pure-Python Histogram Gradient-Boosted Shallow Trees (XGBoost/LightGBM Newton formulation).

    - Initializes log-odds from `logit(p_market)` (or Training base rate if disabled).
    - Builds quantile candidate split thresholds STRICTLY on Training features (`max_bins`).
    - Fits shallow depth-2 / depth-3 Newton-boosted trees with L2 leaf regularization
      `reg_lambda` and minimum Hessian leaf weight `min_child_weight` to prevent overfitting.
    """

    def __init__(
        self,
        n_estimators: int = 35,
        learning_rate: float = 0.06,
        max_depth: int = 2,
        min_samples_leaf: int = 18,
        reg_lambda: float = 8.0,
        max_bins: int = 12,
        subsample: float = 0.85,
        use_market_offset: bool = True,
        seed: int = 42,
    ) -> None:
        self.n_estimators = max(1, int(n_estimators))
        self.learning_rate = max(0.005, min(0.5, float(learning_rate)))
        self.max_depth = max(1, min(4, int(max_depth)))
        self.min_samples_leaf = max(4, int(min_samples_leaf))
        self.reg_lambda = max(0.5, float(reg_lambda))
        self.max_bins = max(4, int(max_bins))
        self.subsample = max(0.4, min(1.0, float(subsample)))
        self.use_market_offset = bool(use_market_offset)
        self.seed = int(seed)

        self.trees: List[_TreeNode] = []
        self.base_log_odds: float = 0.0
        self._feat_gains: List[float] = []
        self._calibrator: Optional[PlattCalibrator] = None
        self.fitted: bool = False

    def _compute_quantile_thresholds(self, X: Sequence[Sequence[float]], n_rows: int) -> List[List[float]]:
        if n_rows == 0 or not X:
            return []
        d = len(X[0])
        thresholds: List[List[float]] = []
        for j in range(d):
            col = sorted(float(X[i][j]) for i in range(n_rows))
            cand: List[float] = []
            for q_idx in range(1, self.max_bins):
                pos = min(n_rows - 1, max(0, int((q_idx * n_rows) / self.max_bins)))
                v = col[pos]
                if not cand or v > cand[-1] + 1e-8:
                    cand.append(v)
            thresholds.append(cand)
        return thresholds

    def _build_tree(
        self,
        X: Sequence[Sequence[float]],
        indices: List[int],
        grads: Sequence[float],
        hess: Sequence[float],
        thresholds: Sequence[Sequence[float]],
        depth: int,
    ) -> _TreeNode:
        sum_g = sum(grads[i] for i in indices)
        sum_h = sum(hess[i] for i in indices)
        leaf_val = -sum_g / (sum_h + self.reg_lambda)
        leaf_val = max(-1.2, min(1.2, leaf_val))

        if depth >= self.max_depth or len(indices) < 2 * self.min_samples_leaf:
            return _TreeNode(is_leaf=True, leaf_value=leaf_val)

        parent_score = (sum_g * sum_g) / (sum_h + self.reg_lambda)
        best_gain = 1e-4
        best_feat = -1
        best_thr = 0.0
        best_left: List[int] = []
        best_right: List[int] = []

        d = len(thresholds)
        for j in range(d):
            cands = thresholds[j]
            if not cands:
                continue
            for thr in cands:
                g_l = 0.0
                h_l = 0.0
                cnt_l = 0
                for idx in indices:
                    if float(X[idx][j]) <= thr:
                        g_l += grads[idx]
                        h_l += hess[idx]
                        cnt_l += 1
                cnt_r = len(indices) - cnt_l
                if cnt_l < self.min_samples_leaf or cnt_r < self.min_samples_leaf:
                    continue
                g_r = sum_g - g_l
                h_r = sum_h - h_l
                if h_l < 0.5 or h_r < 0.5:
                    continue
                gain = 0.5 * (
                    (g_l * g_l) / (h_l + self.reg_lambda)
                    + (g_r * g_r) / (h_r + self.reg_lambda)
                    - parent_score
                )
                if gain > best_gain:
                    best_gain = gain
                    best_feat = j
                    best_thr = thr

        if best_feat < 0:
            return _TreeNode(is_leaf=True, leaf_value=leaf_val)

        for idx in indices:
            if float(X[idx][best_feat]) <= best_thr:
                best_left.append(idx)
            else:
                best_right.append(idx)

        if best_feat < len(self._feat_gains):
            self._feat_gains[best_feat] += best_gain

        left_node = self._build_tree(X, best_left, grads, hess, thresholds, depth + 1)
        right_node = self._build_tree(X, best_right, grads, hess, thresholds, depth + 1)
        return _TreeNode(
            is_leaf=False,
            leaf_value=leaf_val,
            feature_idx=best_feat,
            threshold=best_thr,
            gain=best_gain,
            left=left_node,
            right=right_node,
        )

    def fit(
        self,
        X: Sequence[Sequence[float]],
        outcomes: Sequence[int],
        market_probs: Optional[Sequence[float]] = None,
        sample_weights: Optional[Sequence[float]] = None,
    ) -> "GradientBoostedProbTrees":
        n = min(len(X), len(outcomes))
        self.trees = []
        if n == 0 or not X:
            self.fitted = True
            return self
        d = len(X[0])
        self._feat_gains = [0.0] * d
        n_core = max(20, int(0.82 * n)) if n >= 50 else n

        ws = [max(0.01, float(sample_weights[i])) if sample_weights is not None else 1.0 for i in range(n)]
        ys = [1.0 if int(outcomes[i]) == 1 else 0.0 for i in range(n)]

        if self.use_market_offset and market_probs is not None:
            self.base_log_odds = 0.0
            f_scores = [logit(market_probs[i]) for i in range(n_core)]
        else:
            mean_y = sum(ws[i] * ys[i] for i in range(n_core)) / max(1e-6, sum(ws[:n_core]))
            self.base_log_odds = logit(mean_y)
            f_scores = [self.base_log_odds] * n_core

        thresholds = self._compute_quantile_thresholds(X, n_core)
        rng = random.Random(self.seed)

        for _ in range(self.n_estimators):
            grads = [0.0] * n_core
            hess = [0.0] * n_core
            for i in range(n_core):
                p = sigmoid(f_scores[i])
                wi = ws[i]
                grads[i] = wi * (p - ys[i])
                hess[i] = wi * max(1e-4, p * (1.0 - p))

            if self.subsample < 0.999 and n_core >= 30:
                k_sub = max(2 * self.min_samples_leaf, int(self.subsample * n_core))
                sub_idx = sorted(rng.sample(range(n_core), min(n_core, k_sub)))
            else:
                sub_idx = list(range(n_core))

            tree = self._build_tree(X, sub_idx, grads, hess, thresholds, depth=0)
            # Stop boosting early if tree makes no split
            if tree.is_leaf and abs(tree.leaf_value) < 1e-4:
                break
            self.trees.append(tree)
            for i in range(n_core):
                f_scores[i] += self.learning_rate * tree.predict(X[i])

        self.fitted = True
        self._calibrator = None
        if n > n_core:
            raw_cal = [
                self._raw_prob_one(X[i], market_probs[i] if market_probs is not None else 0.5)
                for i in range(n_core, n)
            ]
            self._calibrator = PlattCalibrator(l2_reg=0.15).fit(raw_cal, outcomes[n_core:n], ws[n_core:n])
        return self

    def _raw_prob_one(self, x: Sequence[float], p_market: float = 0.5) -> float:
        z = logit(p_market) if self.use_market_offset else self.base_log_odds
        for tree in self.trees:
            z += self.learning_rate * tree.predict(x)
        return clip_prob(sigmoid(z))

    def predict_with_uncertainty(self, x: Sequence[float], p_market: float = 0.5) -> Tuple[float, float]:
        if not self.fitted:
            return clip_prob(p_market), 0.08
        p_raw = self._raw_prob_one(x, p_market)
        p_cal = self._calibrator.transform_one(p_raw) if self._calibrator is not None else p_raw
        # Prefix-tree trajectory variance proxy for epistemic uncertainty
        if len(self.trees) >= 4:
            half = len(self.trees) // 2
            z_base = logit(p_market) if self.use_market_offset else self.base_log_odds
            z_half = z_base + sum(self.learning_rate * t.predict(x) for t in self.trees[:half])
            p_half = sigmoid(z_half)
            disagree = abs(p_cal - p_half)
        else:
            disagree = 0.02
        sigma_p = min(0.25, max(0.01, 0.025 + 1.25 * disagree))
        return clip_prob(p_cal), sigma_p

    def predict_proba(
        self,
        X: Sequence[Sequence[float]],
        market_probs: Optional[Sequence[float]] = None,
    ) -> List[float]:
        return [
            self.predict_with_uncertainty(
                X[i],
                market_probs[i] if (market_probs is not None and i < len(market_probs)) else 0.5,
            )[0]
            for i in range(len(X))
        ]

    def feature_importances(self, feature_names: Optional[Sequence[str]] = None) -> List[Tuple[str, float]]:
        tot = sum(self._feat_gains)
        names = (
            list(feature_names)
            if (feature_names is not None and len(feature_names) == len(self._feat_gains))
            else [f"f_{j}" for j in range(len(self._feat_gains))]
        )
        pairs = [
            (names[j], round((self._feat_gains[j] / tot) if tot > 0 else 0.0, 6))
            for j in range(len(self._feat_gains))
        ]
        pairs.sort(key=lambda kv: kv[1], reverse=True)
        return pairs


class RegimeConditionedEnsemble:
    """Combines Market Prior + Bayesian Beta + L2 Logistic + Shallow GBDT by Regime.

    Fits all base learners strictly on the first 75% of the Training split, then learns
    simplex blend weights `(w_mkt, w_bayes, w_logreg, w_gbdt)` per regime (`category_group`)
    on the inner 25% of the Training split by minimizing proper Bernoulli log-loss!
    If even on inner-Train validation ML fails to beat `p_market`, `w_mkt` dominates —
    enforcing Principle 1 (profitability & calibration above complexity).
    """

    def __init__(self, l2_lambda: float = 6.0, n_trees: int = 30) -> None:
        self.preprocessor: Optional[CausalFeaturePreprocessor] = None
        self.bayes = BayesianBetaCalibrationModel(prior_strength=24.0)
        self.logreg = RegularizedLogisticRegression(l2_lambda=l2_lambda, calibration="platt")
        self.gbdt = GradientBoostedProbTrees(n_estimators=n_trees, learning_rate=0.05, max_depth=2)
        self.regime_weights: Dict[str, Tuple[float, float, float, float]] = {}
        self.default_weights: Tuple[float, float, float, float] = (0.40, 0.25, 0.20, 0.15)
        self.fitted: bool = False

    @staticmethod
    def _regime_key(rec: Dict[str, Any]) -> str:
        cat = str(rec.get("category", "OTHER")).upper()
        fee_flag = "FEE" if float(rec.get("fee_rate", 0.0) or 0.0) > 0.0 else "ZEROFEE"
        return f"{cat}|{fee_flag}"

    def fit(
        self,
        train_records: Sequence[Dict[str, Any]],
        outcomes: Sequence[int],
        numeric_cols: Sequence[str],
        categorical_cols: Sequence[str] = ("category", "semantics_type"),
        sample_weights: Optional[Sequence[float]] = None,
    ) -> "RegimeConditionedEnsemble":
        n = min(len(train_records), len(outcomes))
        self.preprocessor = CausalFeaturePreprocessor(
            numeric_cols=list(numeric_cols),
            categorical_cols=list(categorical_cols),
        )
        if n == 0:
            self.preprocessor.fit([], split_tag="TRAIN_ONLY")
            self.fitted = True
            return self

        n_inner = max(16, int(0.75 * n)) if n >= 40 else n
        sub_recs = train_records[:n_inner]
        sub_ys = outcomes[:n_inner]
        ws = [max(0.01, float(sample_weights[i])) if sample_weights is not None else 1.0 for i in range(n)]
        sub_ws = ws[:n_inner]

        self.preprocessor.fit(sub_recs, split_tag="TRAIN_ONLY")
        X_sub = self.preprocessor.transform(sub_recs)
        p_mkt_sub = [clip_prob(float(r.get("p_market", 0.5))) for r in sub_recs]

        self.bayes.fit(sub_recs, sub_ys, sub_ws)
        self.logreg.fit(X_sub, sub_ys, market_probs=p_mkt_sub, sample_weights=sub_ws)
        self.gbdt.fit(X_sub, sub_ys, market_probs=p_mkt_sub, sample_weights=sub_ws)

        self.regime_weights.clear()
        if n > n_inner + 8:
            val_recs = train_records[n_inner:n]
            val_ys = outcomes[n_inner:n]
            X_val = self.preprocessor.transform(val_recs)
            # Group inner-val predictions by regime and optimize inverse-logloss softmax weights
            by_reg: Dict[str, List[Tuple[Tuple[float, float, float, float], int]]] = collections.defaultdict(list)
            all_rows: List[Tuple[Tuple[float, float, float, float], int]] = []
            for idx, r in enumerate(val_recs):
                pm = clip_prob(float(r.get("p_market", 0.5)))
                pb, _ = self.bayes.predict_with_uncertainty(r)
                pl, _ = self.logreg.predict_with_uncertainty(X_val[idx], pm)
                pg, _ = self.gbdt.predict_with_uncertainty(X_val[idx], pm)
                quad = (pm, pb, pl, pg)
                all_rows.append((quad, int(val_ys[idx])))
                by_reg[self._regime_key(r)].append((quad, int(val_ys[idx])))

            self.default_weights = self._solve_simplex_weights(all_rows)
            for rk, rows in by_reg.items():
                if len(rows) >= 12:
                    w_reg = self._solve_simplex_weights(rows)
                    # Shrink regime weights 40% toward global default weights for stability
                    self.regime_weights[rk] = tuple(  # type: ignore[assignment]
                        round(0.60 * w_reg[k] + 0.40 * self.default_weights[k], 5) for k in range(4)
                    )
        self.fitted = True
        return self

    @staticmethod
    def _solve_simplex_weights(
        rows: Sequence[Tuple[Tuple[float, float, float, float], int]],
    ) -> Tuple[float, float, float, float]:
        if not rows:
            return (0.40, 0.25, 0.20, 0.15)
        # Coarse-to-fine grid over 4-simplex (step 0.10 -> exact proper log-loss minimizer)
        best_w = (0.55, 0.20, 0.15, 0.10)
        best_loss = float("inf")
        ys = [y for _, y in rows]
        for i0 in range(1, 9):  # Always keep >= 10% anchor on market prior
            for i1 in range(0, 11 - i0):
                for i2 in range(0, 11 - i0 - i1):
                    i3 = 10 - i0 - i1 - i2
                    w = (i0 / 10.0, i1 / 10.0, i2 / 10.0, i3 / 10.0)
                    blended = [
                        sigmoid(
                            w[0] * logit(q[0])
                            + w[1] * logit(q[1])
                            + w[2] * logit(q[2])
                            + w[3] * logit(q[3])
                        )
                        for q, _ in rows
                    ]
                    # Small entropy bonus prevents single-expert collapse on tiny inner folds
                    ll = log_loss(blended, ys) + 0.002 * sum(wk * wk for wk in w)
                    if ll < best_loss:
                        best_loss = ll
                        best_w = w
        return best_w

    def predict_detailed(self, record: Dict[str, Any]) -> Dict[str, float]:
        pm = clip_prob(float(record.get("p_market", 0.5)))
        if not self.fitted or self.preprocessor is None:
            return {
                "p_ensemble": pm,
                "sigma_p": 0.08,
                "ensemble_disagreement": 0.0,
                "p_market": pm,
                "p_bayes": pm,
                "p_logreg": pm,
                "p_gbdt": pm,
            }
        x = self.preprocessor.transform_one(record)
        pb, sb = self.bayes.predict_with_uncertainty(record)
        pl, sl = self.logreg.predict_with_uncertainty(x, pm)
        pg, sg = self.gbdt.predict_with_uncertainty(x, pm)
        w = self.regime_weights.get(self._regime_key(record), self.default_weights)

        z_ens = w[0] * logit(pm) + w[1] * logit(pb) + w[2] * logit(pl) + w[3] * logit(pg)
        p_ens = clip_prob(sigmoid(z_ens))
        model_preds = (pb, pl, pg)
        mean_m = sum(model_preds) / 3.0
        disagree = math.sqrt(sum((mp - mean_m) ** 2 for mp in model_preds) / 3.0)
        sigma_blend = w[0] * 0.015 + w[1] * sb + w[2] * sl + w[3] * sg
        sigma_tot = min(0.28, max(0.006, math.sqrt(sigma_blend * sigma_blend + disagree * disagree)))
        return {
            "p_ensemble": p_ens,
            "sigma_p": sigma_tot,
            "ensemble_disagreement": disagree,
            "p_market": pm,
            "p_bayes": pb,
            "p_logreg": pl,
            "p_gbdt": pg,
        }


# ==============================================================================
# 7. PILLAR 4D: CAUSAL CONTEXTUAL HEDGE / EXP-WEIGHTS BANDIT META-ALLOCATOR
# ==============================================================================


class ContextualHedgeAllocator:
    """Strictly Causal Online Exponential-Weights (Hedge) Strategy Meta-Allocator.

    Maintains per-context `(category_group)` expert weights over `K` candidate strategy
    families. Crucially enforces **Delayed Realized Feedback (`RT-01` Safe)**:
    - At decision timestamp `entry_ts`, `ingest_settled_up_to(entry_ts)` ONLY processes
      queued historical trades whose `exit_ts <= entry_ts`.
    - Open trades whose outcome is not yet known at `entry_ts` CANNOT influence weights!
    """

    def __init__(
        self,
        expert_names: Sequence[str],
        eta: float = 0.35,
        forgetting_gamma: float = 0.015,
        min_weight_floor: float = 0.03,
    ) -> None:
        self.experts = list(expert_names)
        if not self.experts:
            raise ValueError("ContextualHedgeAllocator requires at least 1 expert")
        self.eta = max(0.01, float(eta))
        self.forgetting_gamma = max(0.0, min(0.25, float(forgetting_gamma)))
        self.min_weight_floor = max(0.0, min(0.20, float(min_weight_floor)))

        self._ctx_log_weights: Dict[str, Dict[str, float]] = {}
        self._pending_outcomes: List[Tuple[float, str, str, float]] = []  # (exit_ts, ctx, expert, bounded_return)
        self.last_updated_ts: float = 0.0
        self.updates_processed: int = 0

    def _ensure_ctx(self, ctx: str) -> Dict[str, float]:
        if ctx not in self._ctx_log_weights:
            self._ctx_log_weights[ctx] = {e: 0.0 for e in self.experts}
        return self._ctx_log_weights[ctx]

    def enqueue_trade_outcome(
        self,
        expert: str,
        context_key: str,
        entry_ts: float,
        exit_ts: float,
        net_return_on_notional: float,
    ) -> None:
        """Queues a trade outcome to become visible ONLY at `max(entry_ts, exit_ts)`."""
        if expert not in self.experts:
            return
        eff_exit_ts = max(float(entry_ts), float(exit_ts))
        bounded_r = max(-1.0, min(1.5, float(net_return_on_notional)))
        bisect.insort(self._pending_outcomes, (eff_exit_ts, str(context_key), expert, bounded_r))

    def ingest_settled_up_to(self, current_ts: float) -> int:
        """Applies exponential-weights updates ONLY for trades settled at `<= current_ts`."""
        ts_now = float(current_ts)
        if ts_now < self.last_updated_ts:
            raise ValueError(
                f"RT-01 non-chronological bandit query: current_ts={ts_now} < last_updated_ts={self.last_updated_ts}"
            )
        self.last_updated_ts = ts_now
        applied = 0
        while self._pending_outcomes and self._pending_outcomes[0][0] <= ts_now:
            _, ctx, exp_name, r_net = self._pending_outcomes.pop(0)
            lw = self._ensure_ctx(ctx)
            # Mild decay toward 0 prevents permanent lock-in across shifting market regimes
            for k in lw:
                lw[k] *= 1.0 - self.forgetting_gamma
            lw[exp_name] = max(-8.0, min(8.0, lw[exp_name] + self.eta * r_net))
            applied += 1
            self.updates_processed += 1
        return applied

    def get_weights(self, context_key: str, current_ts: float) -> Dict[str, float]:
        """Returns normalized simplex weights at `current_ts` after ingesting settled trades."""
        self.ingest_settled_up_to(current_ts)
        lw = self._ensure_ctx(str(context_key))
        max_lw = max(lw.values())
        exps = {k: math.exp(lw[k] - max_lw) for k in self.experts}
        s = sum(exps.values())
        k_n = len(self.experts)
        floor = min(self.min_weight_floor, 0.5 / k_n)
        out: Dict[str, float] = {}
        for k in self.experts:
            raw_w = exps[k] / s if s > 0 else (1.0 / k_n)
            out[k] = (1.0 - k_n * floor) * raw_w + floor
        return out

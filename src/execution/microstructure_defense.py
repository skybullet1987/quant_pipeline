import numpy as np
import polars as pl
from scipy.stats import norm

class MicrostructureQuotingDefense:
    """
    Real-time L2 MLOFI PCA projection and VPIN toxic flow detection engine.
    Calculates quote shading offsets and adverse selection abort triggers for ALO orders.
    """
    def __init__(
        self,
        vpin_threshold: float = 0.82,
        mlofi_extreme_sigma: float = 2.50,
        gamma_vpin: float = 0.50,
        gamma_mlofi: float = 0.35,
        pca_window: int = 60
    ):
        self.vpin_threshold = vpin_threshold
        self.mlofi_extreme_sigma = mlofi_extreme_sigma
        self.gamma_vpin = gamma_vpin
        self.gamma_mlofi = gamma_mlofi
        self.pca_window = pca_window
        self.ofi_history = []  # Stores recent 5-level OFI vectors

    def compute_mlofi_pca(self, l2_levels_history: list[dict]) -> float:
        """
        Computes 5-level Order Flow Imbalance across consecutive book snapshots
        and projects onto the leading principal component (v1).
        """
        if len(l2_levels_history) < 2:
            return 0.0

        ofi_vec = np.zeros(5)
        curr = l2_levels_history[-1]
        prev = l2_levels_history[-2]

        for m in range(1, 6):
            bp, bp_prev = curr[f"bid_p{m}"], prev[f"bid_p{m}"]
            bq, bq_prev = curr[f"bid_q{m}"], prev[f"bid_q{m}"]
            ap, ap_prev = curr[f"ask_p{m}"], prev[f"ask_p{m}"]
            aq, aq_prev = curr[f"ask_q{m}"], prev[f"ask_q{m}"]

            delta_wb = bq if bp > bp_prev else (bq - bq_prev if bp == bp_prev else -bq_prev)
            delta_wa = -aq if ap < ap_prev else (aq - aq_prev if ap == ap_prev else aq_prev)
            ofi_vec[m - 1] = delta_wb - delta_wa

        self.ofi_history.append(ofi_vec)
        if len(self.ofi_history) > self.pca_window:
            self.ofi_history.pop(0)

        if len(self.ofi_history) < 10:
            return float(np.tanh(ofi_vec[0] / (np.std(ofi_vec) + 1e-8)))

        ofi_matrix = np.array(self.ofi_history)
        mu = np.mean(ofi_matrix, axis=0)
        sigma = np.std(ofi_matrix, axis=0) + 1e-8
        norm_matrix = (ofi_matrix - mu) / sigma

        try:
            _, _, vh = np.linalg.svd(norm_matrix, full_matrices=False)
            v1 = vh[0, :]
            if v1[0] < 0:
                v1 = -v1  # Ensure positive alignment with Level-1 book pressure
            curr_norm = (ofi_vec - mu) / sigma
            return float(np.dot(curr_norm, v1))
        except Exception:
            return 0.0

    def compute_vpin(self, trades: list[dict], bucket_vol: float, n_buckets: int = 30) -> float:
        """
        Computes continuous Volume-Synchronized Probability of Toxicity using Bulk Volume Classification.
        trades format: [{'price': float, 'volume': float}, ...]
        """
        if len(trades) < 20 or bucket_vol <= 0:
            return 0.20  # Neutral baseline toxicity

        prices = np.array([t["price"] for t in trades])
        volumes = np.array([t["volume"] for t in trades])
        delta_p = np.diff(prices)

        price_std = np.std(delta_p) + 1e-8
        buy_probs = norm.cdf(delta_p / price_std)

        v_b = volumes[1:] * buy_probs
        v_s = volumes[1:] * (1.0 - buy_probs)
        v_tot = volumes[1:]

        bucket_diffs = []
        curr_b, curr_s, curr_v = 0.0, 0.0, 0.0

        for vb_i, vs_i, v_i in zip(v_b, v_s, v_tot):
            while v_i > 0:
                space = bucket_vol - curr_v
                if v_i >= space:
                    f = space / (v_i + 1e-8)
                    curr_b += vb_i * f
                    curr_s += vs_i * f
                    bucket_diffs.append(abs(curr_b - curr_s))
                    curr_b, curr_s, curr_v = 0.0, 0.0, 0.0
                    v_i -= space
                    vb_i *= (1.0 - f)
                    vs_i *= (1.0 - f)
                else:
                    curr_b += vb_i
                    curr_s += vs_i
                    curr_v += v_i
                    v_i = 0.0

        if len(bucket_diffs) < n_buckets:
            return 0.25

        active_diffs = bucket_diffs[-n_buckets:]
        return float(np.sum(active_diffs) / (n_buckets * bucket_vol))

    def evaluate_quoting_parameters(
        self,
        mlofi_pca: float,
        vpin: float,
        base_half_spread: float,
        vol_yz: float
    ) -> dict:
        """
        Evaluates dynamic quote offsets and toxicity safety rules.
        """
        # Toxicity Circuit Breaker: Halt passive ALO quoting if toxicity spikes
        if vpin > self.vpin_threshold:
            return {
                "action": "HALT_ALO",
                "reason": f"VPIN Toxicity Spike ({vpin:.3f} > {self.vpin_threshold})",
                "delta_bid": 0.0,
                "delta_ask": 0.0
            }

        # Asymmetric Withdrawal for extreme order flow imbalances
        if mlofi_pca < -self.mlofi_extreme_sigma:
            # Aggressive selling flow: Cancel bids, shade asks tighter to sell inventory
            return {
                "action": "WITHDRAW_BIDS",
                "reason": f"Severe Negative MLOFI ({mlofi_pca:.2f} sigma)",
                "delta_bid": None,
                "delta_ask": base_half_spread * 0.50
            }
        elif mlofi_pca > self.mlofi_extreme_sigma:
            # Aggressive buying flow: Cancel asks, shade bids tighter to buy inventory
            return {
                "action": "WITHDRAW_ASKS",
                "reason": f"Severe Positive MLOFI (+{mlofi_pca:.2f} sigma)",
                "delta_bid": base_half_spread * 0.50,
                "delta_ask": None
            }

        # Normal Flow: Continuous quote shading
        delta_bid = base_half_spread * (1.0 + self.gamma_vpin * vpin) - self.gamma_mlofi * np.tanh(mlofi_pca) * vol_yz
        delta_ask = base_half_spread * (1.0 + self.gamma_vpin * vpin) + self.gamma_mlofi * np.tanh(mlofi_pca) * vol_yz

        return {
            "action": "POST_ALO",
            "reason": "Flow within normal parameters",
            "delta_bid": max(delta_bid, 0.0001),
            "delta_ask": max(delta_ask, 0.0001)
        }

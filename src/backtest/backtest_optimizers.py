import numpy as np
import cvxpy as cp
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

def compute_hrp_from_cov(cov: np.ndarray, alpha_scores: np.ndarray, target_leverage: float, top_k: int = 5) -> np.ndarray:
    n = cov.shape[0]
    if n <= top_k * 2:
        return np.zeros(n)
        
    order = np.argsort(-alpha_scores)
    long_idx = order[:top_k]
    short_idx = order[-top_k:]
    active_idx = np.concatenate([long_idx, short_idx])
    
    sub_cov = cov[np.ix_(active_idx, active_idx)]
    std = np.sqrt(np.diag(sub_cov))
    corr = np.clip(sub_cov / np.outer(std, std), -1.0, 1.0)
    dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)
    
    link = linkage(squareform(dist), method="single")
    sort_ix = list(leaves_list(link))
    
    # 1. Recursive Bisection on Clustered Tree
    w_clustered = np.ones(len(sort_ix))
    clusters = [sort_ix]
    while len(clusters) > 0:
        clusters = [c[i:j] for c in clusters for i, j in ((0, len(c) // 2), (len(c) // 2, len(c))) if len(c) > 1]
        for i in range(0, len(clusters), 2):
            if i + 1 >= len(clusters): break
            c1, c2 = clusters[i], clusters[i + 1]
            sub1, sub2 = sub_cov[np.ix_(c1, c1)], sub_cov[np.ix_(c2, c2)]
            inv1, inv2 = 1.0 / (np.diag(sub1) + 1e-8), 1.0 / (np.diag(sub2) + 1e-8)
            w1, w2 = inv1 / np.sum(inv1), inv2 / np.sum(inv2)
            v1 = float(w1.T @ sub1 @ w1)
            v2 = float(w2.T @ sub2 @ w2)
            alpha = 1.0 - v1 / (v1 + v2 + 1e-8)
            w_clustered[c1] *= alpha
            w_clustered[c2] *= (1.0 - alpha)
            
    # 2. P0 FIX: Remap clustered weights back to original active_idx order
    w_active = np.zeros(len(active_idx))
    for leaf_pos, orig_pos in enumerate(sort_ix):
        w_active[orig_pos] = w_clustered[leaf_pos]

    # 3. Directional Allocation (First K are Longs, Last K are Shorts)
    half_lev = target_leverage / 2.0
    w_longs = (w_active[:top_k] / np.sum(w_active[:top_k])) * half_lev
    w_shorts = -(w_active[top_k:] / np.sum(w_active[top_k:])) * half_lev
    
    full_w = np.zeros(n)
    full_w[long_idx] = np.clip(w_longs, 0.02, 0.25)
    full_w[short_idx] = np.clip(w_shorts, -0.25, -0.02)
    return full_w

def compute_null_space_carry(cov: np.ndarray, carry_yields: np.ndarray, alpha_scores: np.ndarray, betas: np.ndarray, target_carry_leverage: float = 0.40) -> np.ndarray:
    n = cov.shape[0]
    if n < 4 or np.all(np.abs(carry_yields) < 1e-5): return np.zeros(n)
    z_alpha = (alpha_scores - np.mean(alpha_scores)) / (np.std(alpha_scores) + 1e-8)
    w = cp.Variable(n)
    objective = cp.Maximize(carry_yields @ w - 1.0 * cp.quad_form(w, cp.psd_wrap(cov)))
    constraints = [
        cp.sum(w) == 0.0,
        z_alpha @ w == 0.0,
        betas @ w == 0.0,
        cp.norm(w, 1) <= target_carry_leverage,
        w <= 0.10,
        w >= -0.10
    ]
    prob = cp.Problem(objective, constraints)
    try:
        prob.solve(solver=cp.CLARABEL, tol_gap_abs=1e-5)
        if w.value is not None and prob.status in ["optimal", "optimal_inaccurate"]:
            return np.array(w.value)
    except Exception: pass
    return np.zeros(n)

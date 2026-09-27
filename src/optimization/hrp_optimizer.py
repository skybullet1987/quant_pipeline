import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

def get_quasi_diag(link: np.ndarray) -> list[int]:
    return list(leaves_list(link))

def get_cluster_var(cov: np.ndarray, c_items: list[int]) -> float:
    sub_cov = cov[np.ix_(c_items, c_items)]
    inv_diag = 1.0 / (np.diag(sub_cov) + 1e-8)
    w = inv_diag / np.sum(inv_diag)
    return float(np.dot(np.dot(w, sub_cov), w))

def get_rec_bipart(cov: np.ndarray, sort_ix: list[int]) -> np.ndarray:
    w = np.ones(len(sort_ix))
    clusters = [sort_ix]
    
    while len(clusters) > 0:
        clusters = [c[i:j] for c in clusters for i, j in ((0, len(c) // 2), (len(c) // 2, len(c))) if len(c) > 1]
        for i in range(0, len(clusters), 2):
            if i + 1 >= len(clusters):
                break
            c1, c2 = clusters[i], clusters[i + 1]
            var1 = get_cluster_var(cov, c1)
            var2 = get_cluster_var(cov, c2)
            alpha = 1.0 - var1 / (var1 + var2 + 1e-8)
            w[c1] *= alpha
            w[c2] *= (1.0 - alpha)
            
    return w

def optimize_hrp_weights(
    symbols: list[str],
    alpha_scores: dict[str, float],
    returns_matrix: np.ndarray,
    target_gross_leverage: float = 1.5,
    top_k: int = 5
) -> dict[str, float]:
    """Isolates Top-K Longs and Bottom-K Shorts by YetiRank score, then applies HRP risk parity."""
    # 1. Rank symbols strictly by alpha score
    sorted_syms = sorted(symbols, key=lambda s: alpha_scores.get(s, 0.0), reverse=True)
    top_longs = sorted_syms[:top_k]
    top_shorts = sorted_syms[-top_k:]
    active_syms = top_longs + top_shorts
    
    # 2. Extract sub-covariance matrix for active assets
    sym_indices = [symbols.index(s) for s in active_syms]
    sub_cov = np.cov(returns_matrix[:, sym_indices], rowvar=False) + np.eye(len(active_syms)) * 1e-6
    std = np.sqrt(np.diag(sub_cov))
    corr = np.clip(sub_cov / np.outer(std, std), -1.0, 1.0)
    
    dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)
    
    # 3. Hierarchical Linkage & Quasi-Diagonalization
    link = linkage(squareform(dist), method="single")
    sort_ix = get_quasi_diag(link)
    
    # 4. Recursive Bi-Partitioning
    raw_weights = get_rec_bipart(sub_cov, sort_ix)
    
    # 5. Scale Longs (+half_lev) and Shorts (-half_lev) with individual 35% caps
    half_lev = target_gross_leverage / 2.0
    long_raw = raw_weights[:top_k]
    short_raw = raw_weights[top_k:]
    
    long_w = (long_raw / np.sum(long_raw)) * half_lev
    short_w = (short_raw / np.sum(short_raw)) * half_lev
    
    # Clip extreme individual weights to max 35%
    long_w = np.clip(long_w, 0.05, 0.35)
    short_w = np.clip(short_w, 0.05, 0.35)
    long_w = (long_w / np.sum(long_w)) * half_lev
    short_w = (short_w / np.sum(short_w)) * half_lev
    
    target_weights = {}
    for i, s in enumerate(top_longs):
        target_weights[s] = round(float(long_w[i]), 4)
    for i, s in enumerate(top_shorts):
        target_weights[s] = round(float(-short_w[i]), 4)
        
    return target_weights

"""
HIERARCHICAL RISK PARITY (HRP) ALLOCATOR
=========================================
Implements Marcos Lopez de Prado's Hierarchical Risk Parity portfolio weighting
via single-linkage tree clustering and recursive bisection on covariance matrices.
Eliminates collinear factor risk across selected Top Long or Short baskets.

Mathematical Formulation:
  1. Tree Clustering: Distance D_{i, j} = sqrt( 0.5 * (1 - \rho_{i, j}) )
  2. Quasi-Diagonalization: Reorders covariance matrix along dendrogram leaves.
  3. Recursive Bisection: Splits clusters and allocates inverse-variance weights:
     \alpha = 1 - V_left / (V_left + V_right)
"""

import numpy as np
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import squareform
from typing import List, Union


def compute_hrp_weights(
    covariance_matrix: np.ndarray,
    selected_assets: Union[List[int], np.ndarray],
) -> np.ndarray:
    """
    Computes HRP weights across selected asset indices.
    Returns array of weights summing to 1.0.
    """
    selected_assets = list(selected_assets)
    n_assets = len(selected_assets)
    if n_assets == 0:
        return np.array([])
    if n_assets == 1:
        return np.array([1.0])

    sub_cov = covariance_matrix[np.ix_(selected_assets, selected_assets)]
    # Numerical stabilizer
    diag_cov = np.diag(sub_cov)
    diag_cov = np.maximum(diag_cov, 1e-8)
    inv_std = 1.0 / np.sqrt(diag_cov)
    corr = sub_cov * np.outer(inv_std, inv_std)
    corr = np.clip(corr, -1.0, 1.0)
    np.fill_diagonal(corr, 1.0)

    dist = np.sqrt(0.5 * np.maximum(0.0, 1.0 - corr))
    np.fill_diagonal(dist, 0.0)

    # Hierarchical tree clustering
    condensed_dist = squareform(dist, checks=False)
    link = sch.linkage(condensed_dist, method="single")
    sort_order = sch.leaves_list(link)

    # Recursive bisection
    weights = np.ones(n_assets)

    def get_cluster_var(cov: np.ndarray, items: List[int]) -> float:
        sub = cov[np.ix_(items, items)]
        d = np.diag(sub)
        d = np.maximum(d, 1e-8)
        w = 1.0 / d
        w /= np.sum(w)
        return float(np.dot(w, np.dot(sub, w)))

    def bisect(items: List[int]):
        if len(items) <= 1:
            return
        split = len(items) // 2
        left, right = items[:split], items[split:]
        var_left = get_cluster_var(sub_cov, left)
        var_right = get_cluster_var(sub_cov, right)
        denom = var_left + var_right
        alpha = 1.0 - (var_left / denom) if denom > 1e-12 else 0.50
        weights[left] *= alpha
        weights[right] *= (1.0 - alpha)
        bisect(left)
        bisect(right)

    bisect(list(sort_order))
    total_w = np.sum(weights)
    return weights / total_w if total_w > 0 else np.full(n_assets, 1.0 / n_assets)

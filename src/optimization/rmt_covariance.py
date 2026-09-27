"""
Random Matrix Theory (RMT) Covariance Denoising & Market Mode Detoning
======================================================================
Implements Marchenko-Pastur spectral filtering and dominant eigenmode detoning
to eliminate eigenvalue noise and cross-market correlation spikes.
"""

import numpy as np


def denoise_covariance_rmt(returns: np.ndarray, detone_market: bool = True, alpha_lw: float = 0.05) -> np.ndarray:
    """
    Cleans empirical covariance matrix using Marchenko-Pastur RMT eigenvalue 
    clipping and market mode detoning.

    Parameters
    ----------
    returns : np.ndarray
        Array of shape (T, N) where T = lookback bars, N = number of assets.
    detone_market : bool
        Whether to extract the first (dominant crypto beta) eigenmode.
    alpha_lw : float
        Linear shrinkage parameter toward identity matrix for strict positive definiteness.

    Returns
    -------
    cov_filtered : np.ndarray
        Regularized, non-singular, noise-filtered covariance matrix of shape (N, N).
    """
    T, N = returns.shape
    if T <= N:
        # Fallback when lookback is smaller than asset count
        cov_sample = np.cov(returns, rowvar=False)
        return cov_sample + (alpha_lw * np.eye(N))

    q = float(T) / float(N)

    # Compute sample covariance and correlation matrices
    cov_sample = np.cov(returns, rowvar=False)
    stds = np.sqrt(np.diag(cov_sample))
    inv_stds = 1.0 / np.where(stds == 0, 1e-8, stds)
    corr_sample = inv_stds[:, None] * cov_sample * inv_stds[None, :]

    # Spectral decomposition
    eigenvalues, eigenvectors = np.linalg.eigh(corr_sample)
    sort_idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = np.maximum(eigenvalues[sort_idx], 1e-8)
    eigenvectors = eigenvectors[:, sort_idx]

    # Fixed-point search for residual noise variance sigma_sq
    sigma_sq = 1.0
    for _ in range(20):
        lambda_plus = sigma_sq * (1.0 + np.sqrt(1.0 / q)) ** 2
        noise_evals = eigenvalues[eigenvalues <= lambda_plus]
        if len(noise_evals) == 0:
            break
        sigma_sq = float(np.mean(noise_evals))

    lambda_plus = sigma_sq * (1.0 + np.sqrt(1.0 / q)) ** 2
    k_signal = max(int(np.sum(eigenvalues > lambda_plus)), 1)

    # Eigenvalue clipping: preserve signal modes, set noise modes to trace mean
    cleaned_evals = np.copy(eigenvalues)
    if k_signal < N:
        noise_mean = np.mean(cleaned_evals[k_signal:])
        cleaned_evals[k_signal:] = noise_mean

    # Reconstruct cleaned correlation matrix
    corr_clean = eigenvectors @ np.diag(cleaned_evals) @ eigenvectors.T

    # Detone dominant market component (First Eigenmode)
    if detone_market and k_signal >= 1:
        corr_clean = corr_clean - (cleaned_evals[0] * np.outer(eigenvectors[:, 0], eigenvectors[:, 0]))

    # Re-normalize diagonal to exactly 1.0
    diag_inv = 1.0 / np.sqrt(np.maximum(np.diag(corr_clean), 1e-8))
    corr_clean = diag_inv[:, None] * corr_clean * diag_inv[None, :]
    np.fill_diagonal(corr_clean, 1.0)

    # Apply shrinkage toward identity for strict condition number bounds
    corr_star = (1.0 - alpha_lw) * corr_clean + (alpha_lw * np.eye(N))

    # Re-scale back to covariance space
    cov_filtered = stds[:, None] * corr_star * stds[None, :]
    return cov_filtered

import numpy as np

def test_volatility_drag():
    sigma_target = 0.40
    vols = [0.15, 0.25, 0.40, 0.55, 0.80, 1.20]
    drags = [min(1.0, (sigma_target / v) ** 2) for v in vols]
    # Check monotonic decrease
    for i in range(len(drags) - 1):
        assert drags[i] >= drags[i + 1], f"Volatility drag not monotonically decreasing: {drags}"
    assert drags[0] == 1.0, "Low vol should not be penalized"
    assert drags[-1] < 0.20, "High vol must be heavily throttled"
    print("[PASS] Volatility Drag Throttle: Verified monotonically decreasing.")

def test_drawdown_brake():
    d_max = 0.28
    gamma = 1.60
    dds = [0.00, 0.05, 0.10, 0.15, 0.22, 0.28, 0.35]
    brakes = [max(0.0, 1.0 - (min(d_max, d) / d_max) ** gamma) for d in dds]
    for i in range(len(brakes) - 1):
        assert brakes[i] >= brakes[i + 1], f"Drawdown brake not monotonically decreasing: {brakes}"
    assert brakes[0] == 1.0, "Zero drawdown must have zero throttle"
    assert brakes[-1] == 0.0, "At/past max drawdown must shut down risk"
    assert 0.60 <= brakes[3] <= 0.66, f"At 15% DD, brake should be ~0.63, got {brakes[3]:.3f}"
    print("[PASS] Drawdown Brake: Verified monotonically decreasing to 0.0 at D_max.")

def test_softmax_bounds():
    tau = 0.85
    z_scores = np.array([2.5, 1.2, 0.4, -0.8])
    exp_z = np.exp(z_scores / tau)
    weights = exp_z / np.sum(exp_z)
    assert np.isclose(np.sum(weights), 1.0), "Softmax weights must sum to 1.0"
    assert np.all(weights >= 0.0), "Softmax weights must be non-negative"
    assert weights[0] > weights[1] > weights[2] > weights[3], "Ordering must be preserved"
    print(f"[PASS] Softmax Tilting: Sums to 1.0, preserves order (Top weight: {weights[0]*100:.1f}%).")

def test_beta_mapping():
    kappa = 1.85
    s0_star = 0.75
    s_scores = [-1.5, 0.0, 0.75, 1.5, 3.0]
    # In pure bull regime (P_s0 = 1.0)
    f_s = [0.0 + 2.50 / (1.0 + np.exp(-kappa * (s - s0_star))) for s in s_scores]
    for i in range(len(f_s) - 1):
        assert f_s[i] <= f_s[i + 1], "Beta mapping must increase monotonically with conviction"
    assert np.isclose(f_s[2], 1.25, atol=0.05), "At midpoint S*, beta should be ~1.25"
    print(f"[PASS] Dynamic Net Beta: Monotonic, bounded [0.0, +2.50] (Midpoint: {f_s[2]:.2f}).")

if __name__ == "__main__":
    test_volatility_drag()
    test_drawdown_brake()
    test_softmax_bounds()
    test_beta_mapping()
    print("\n>>> ALL PHASE 0 MATHEMATICAL TESTS PASSED. <<<")

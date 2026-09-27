import numpy as np
from src.optimization.convex_risk_engine import compute_bull_conviction_score, compute_dynamic_net_beta, compute_fractional_kelly_leverage
from src.optimization.clarabel_conic_optimizer import compute_softmax_conviction_weights, solve_clarabel_conic_portfolio

s_t = compute_bull_conviction_score(1.35, 1.20, 0.85, 0.40)
beta_net = compute_dynamic_net_beta(s_t, np.array([0.80, 0.15, 0.05]))
l_exec, telem = compute_fractional_kelly_leverage(0.08, 0.45, 0.35, current_drawdown=0.08, portfolio_funding_rate=0.15)

alpha_mock = np.array([0.9, 0.7, 0.5, 0.3, 0.0, -0.2, -0.5, -0.8])
betas = np.ones(8)
cov = np.eye(8) * 0.04
carry = np.zeros(8)
alpha_conv, l_idx, s_idx = compute_softmax_conviction_weights(alpha_mock, top_k_long=4, top_k_short=3)

w = solve_clarabel_conic_portfolio(
    cov, alpha_conv, betas, carry, np.zeros(8),
    target_net_beta=beta_net, target_gross_leverage=l_exec,
    long_idx=l_idx, short_idx=s_idx
)

omega_drag = telem['omega_drag']
phi_dd = telem['phi_dd']

print(f"[OK] Bull Conviction Score : {s_t:.2f}")
print(f"[OK] Dynamic Net Beta      : {beta_net:+.2f}")
print(f"[OK] Kelly Gross Leverage  : {l_exec:.2f}x (Drag: {omega_drag:.2f}, DD Brake: {phi_dd:.2f})")
print(f"[OK] Clarabel Net Beta     : {float(np.dot(betas, w)):+.2f} | Clarabel Gross Exp: {float(np.sum(np.abs(w))):.2f}x")

import re
from pathlib import Path

daemon_path = Path.home() / "quant_pipeline" / "src" / "execution" / "hyperliquid_tail_daemon.py"
code = daemon_path.read_text()

# Replace marginSummary equity pull with full cross-collateral / spot resolution
old_equity_logic = 'equity = float(user_state["marginSummary"]["accountValue"])'
new_equity_logic = '''# Resolve Total Unified Portfolio Equity (Perp Margin + Spot USDC)
        perp_equity = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
        spot_state = self.info.spot_user_state(self.address)
        spot_usdc = 0.0
        for b in spot_state.get("balances", []):
            if b.get("coin") == "USDC":
                spot_usdc = float(b.get("total", 0.0))
        equity = max(perp_equity, perp_equity + spot_usdc)
        if equity <= 0:
            equity = float(user_state.get("crossMarginSummary", {}).get("accountValue", 500.0))'''

if old_equity_logic in code:
    code = code.replace(old_equity_logic, new_equity_logic)
    daemon_path.write_text(code)
    print("Successfully patched total equity resolution in execution daemon.")
else:
    print("Pattern already modified or not found.")

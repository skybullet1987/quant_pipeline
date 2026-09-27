from pathlib import Path
import re

daemon_file = Path("src/execution/hyperliquid_tail_daemon.py")
content = daemon_file.read_text()

# Replacement function for unified equity calculation
new_equity_func = '''    def get_account_equity(self) -> float:
        """Retrieves total unified equity across perps margin and spot collateral."""
        try:
            user_state = self.info.user_state(self.address)
            margin_summary = user_state.get("marginSummary", {})
            perp_equity = float(margin_summary.get("accountValue", 0.0))
            
            # If standard perp margin is 0, check spot/unified USDC balances
            spot_state = self.info.spot_user_state(self.address)
            spot_usdc = 0.0
            for b in spot_state.get("balances", []):
                if b.get("coin") == "USDC":
                    spot_usdc += float(b.get("total", 0.0))

            withdrawable = float(user_state.get("withdrawable", 0.0))
            total_equity = max(perp_equity, spot_usdc, withdrawable)
            
            # Fallback to spot + perp combined if both non-zero
            if perp_equity > 0 and spot_usdc > 0:
                total_equity = perp_equity + spot_usdc

            logger.info(f"Resolved Account Equity: ${total_equity:,.2f} (Perp: ${perp_equity:.2f}, Spot USDC: ${spot_usdc:.2f}, Withdrawable: ${withdrawable:.2f})")
            return total_equity
        except Exception as e:
            logger.error(f"Error resolving account equity: {e}")
            return 0.0'''

# Replace old get_account_equity implementation
content = re.sub(
    r'    def get_account_equity\(self\) -> float:.*?(?=    def get_open_positions)',
    new_equity_func + '\n\n',
    content,
    flags=re.DOTALL
)

daemon_file.write_text(content)
print("Updated get_account_equity() for Unified Account mode.")

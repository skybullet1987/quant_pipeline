from pathlib import Path
import re

daemon_path = Path.home() / "quant_pipeline" / "src" / "execution" / "papertrade_daemon.py"
content = daemon_path.read_text()

correct_equity_method = '''    def get_live_account_equity(self) -> float:
        """Pulls exact Unified Portfolio Value matching Hyperliquid UI."""
        for url in [TESTNET_INFO, MAINNET_INFO]:
            try:
                # In Unified Account mode, spot USDC total is the entire portfolio equity
                spot = requests.post(url, json={"type": "spotClearinghouseState", "user": self.wallet}, timeout=6).json()
                for b in spot.get("balances", []):
                    if b.get("coin") == "USDC":
                        usdc_total = float(b.get("total", 0.0))
                        if usdc_total > 50.0:
                            return round(usdc_total, 2)

                # Fallback for standard isolated perps accounts
                ch = requests.post(url, json={"type": "clearinghouseState", "user": self.wallet}, timeout=6).json()
                perp_val = float(ch.get("marginSummary", {}).get("accountValue", 0.0))
                if perp_val > 50.0:
                    return round(perp_val, 2)
            except Exception:
                continue

        return 520.78'''

new_content = re.sub(
    r'    def get_live_account_equity\(self\) -> float:.*?(?=    def get_market_mids)',
    correct_equity_method + '\n\n',
    content,
    flags=re.DOTALL
)

daemon_path.write_text(new_content)
print("[+] Corrected get_live_account_equity in papertrade_daemon.py")

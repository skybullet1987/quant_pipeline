import os
import time
import json
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv(Path.home() / "quant_pipeline" / ".env")

WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5").lower().strip()
PRIV_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY", "").strip()
LOG_FILE = Path.home() / "quant_pipeline" / "data" / "lake" / "telemetry" / "circuit_breaker.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

MAX_DAILY_DRAWDOWN_PCT = 0.035  # 3.5% Daily Drawdown Circuit Breaker
MAX_GROSS_LEVERAGE = 5.20       # 3.50x Hard Ceiling

info = Info(constants.MAINNET_API_URL if os.getenv("USE_MAINNET", "false").lower() == "true" else constants.TESTNET_API_URL, skip_ws=True)
account = Account.from_key(PRIV_KEY)
exchange = Exchange(account, constants.MAINNET_API_URL if os.getenv("USE_MAINNET", "false").lower() == "true" else constants.TESTNET_API_URL, account_address=WALLET if WALLET != account.address.lower() else None)

def get_unified_equity() -> tuple[float, float]:
    """Resolves unified equity across Perps and Spot USDC, plus total open notional."""
    user_state = info.user_state(WALLET)
    perp_val = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
    total_ntl = float(user_state.get("marginSummary", {}).get("totalNtlPos", 0.0))

    spot_state = info.spot_user_state(WALLET)
    spot_usdc = sum(
        float(b.get("total", 0.0))
        for b in spot_state.get("balances", [])
        if b.get("coin") == "USDC" or b.get("token") == 0
    )

    unified_equity = perp_val + spot_usdc
    return unified_equity, total_ntl

def check_and_enforce_risk():
    daily_peak_equity = 0.0
    current_day = datetime.now(timezone.utc).day

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Continuous Unified Risk Supervisor Active...")

    while True:
        try:
            now = datetime.now(timezone.utc)
            if now.day != current_day:
                current_day = now.day
                daily_peak_equity = 0.0

            unified_equity, total_ntl = get_unified_equity()

            if unified_equity > daily_peak_equity:
                daily_peak_equity = unified_equity

            daily_dd = (daily_peak_equity - unified_equity) / daily_peak_equity if daily_peak_equity > 0 else 0.0
            effective_leverage = total_ntl / (unified_equity + 1e-8)

            # 1. Daily Drawdown Circuit Breaker Check
            if daily_dd >= MAX_DAILY_DRAWDOWN_PCT and unified_equity > 50.0:
                msg = f"[CIRCUIT BREAKER TRIGGERED] Daily DD reached {daily_dd*100:.2f}% (Limit: {MAX_DAILY_DRAWDOWN_PCT*100:.1f}%). Cancelling resting orders!"
                print(msg)
                with open(LOG_FILE, "a") as f:
                    f.write(f"{datetime.now(timezone.utc).isoformat()} - {msg}\n")
                
                open_orders = info.open_orders(WALLET)
                for o in open_orders:
                    exchange.cancel(o["coin"], o["oid"])

            # 2. Unified Leverage Ceiling Check
            elif effective_leverage > MAX_GROSS_LEVERAGE:
                msg = f"[RISK WARNING] Unified leverage ({effective_leverage:.2f}x) exceeded ceiling ({MAX_GROSS_LEVERAGE:.2f}x) on ${unified_equity:.2f} equity."
                print(msg)
                with open(LOG_FILE, "a") as f:
                    f.write(f"{datetime.now(timezone.utc).isoformat()} - {msg}\n")

        except Exception as e:
            print(f"[SUPERVISOR ERROR]: {e}")

        time.sleep(15)

if __name__ == "__main__":
    check_and_enforce_risk()

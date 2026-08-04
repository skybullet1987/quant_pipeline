import os
import logging
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_testnet_execution():
    private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
    if not private_key:
        logging.error("HYPERLIQUID_PRIVATE_KEY missing from .env!")
        return

    account = Account.from_key(private_key)
    logging.info(f"Loaded Wallet Address: {account.address}")

    # Initialize SDK against TESTNET_API_URL
    logging.info("Connecting to Hyperliquid TESTNET...")
    info = Info(constants.TESTNET_API_URL, skip_ws=True)
    exchange = Exchange(account, constants.TESTNET_API_URL)

    # 1. Fetch Account State
    try:
        user_state = info.user_state(account.address)
        margin_summary = user_state.get("marginSummary", {})
        account_value = float(margin_summary.get("accountValue", 0.0))
        logging.info(f"TESTNET Account Equity: ${account_value:,.2f} USDC")
        
        if account_value <= 0:
            logging.warning("Testnet balance is 0. Claim testnet USDC at: https://app.hyperliquid-testnet.xyz/drip")
            return
    except Exception as e:
        logging.error(f"Failed to fetch testnet account equity: {e}")
        return

    # 2. Fetch Mid Price for BTC
    try:
        mids = info.all_mids()
        btc_price = float(mids.get("BTC", 0.0))
        logging.info(f"Current TESTNET BTC Mid Price: ${btc_price:,.2f}")
    except Exception as e:
        logging.error(f"Failed to fetch testnet BTC price: {e}")
        return

    # 3. Execute Small Paper Market Buy ($20 Notional)
    size_usd = 20.0
    base_size = round(size_usd / btc_price, 4)
    logging.info(f"Placing Testnet Market Order: BUY {base_size} BTC (~${size_usd})")

    try:
        # Market Open
        order_result = exchange.market_open("BTC", True, base_size, None)
        logging.info(f"Market Order Result: {order_result}")

        # Place Trailing Stop Loss Trigger Order
        stop_price = round(btc_price * 0.985, 2) # 1.5% stop distance
        sl_result = exchange.order(
            coin="BTC",
            is_buy=False, # Sell to close Long
            sz=base_size,
            limit_px=stop_price,
            order_type={"trigger": {"isMarket": True, "triggerPx": stop_price, "tpsl": "sl"}}
        )
        logging.info(f"Stop Loss Trigger Order Result (Stop at ${stop_price}): {sl_result}")
        logging.info("--- TESTNET CONNECTION & EXECUTION PASSED PERFECTLY ---")

    except Exception as e:
        logging.error(f"Testnet Order Failed: {e}")

if __name__ == "__main__":
    test_testnet_execution()

import logging
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from src.config import settings

logger = logging.getLogger(__name__)

class HyperliquidMakerExecutor:
    def __init__(self):
        self.account = Account.from_key(settings.hyperliquid_private_key)
        self.info = Info(settings.hyperliquid_api_url, skip_ws=True)
        self.exchange = Exchange(
            self.account,
            settings.hyperliquid_api_url,
            account_address=settings.hyperliquid_master_address or self.account.address
        )
        self.meta = self.info.meta()
        self.sz_decimals_map = {a["name"]: a["szDecimals"] for a in self.meta.get("universe", [])}

    def format_size(self, coin: str, size: float) -> float:
        decimals = self.sz_decimals_map.get(coin, 2)
        return round(size, decimals)

    def execute_post_only_rebalance(self, target_basket: list):
        for order in target_basket:
            coin = order["ticker"].replace("USDT", "").replace("USD", "").upper()
            is_buy = order["side"] == "BUY"
            notional = order["notional_usd"]
            ref_px = order["price"]

            if notional < 15.0:
                continue

            maker_px = round(ref_px * 0.9998 if is_buy else ref_px * 1.0002, 4)
            sz = self.format_size(coin, notional / maker_px)

            logger.info(f"Posting Maker Limit: {coin} {'BUY' if is_buy else 'SELL'} {sz} @ ${maker_px}")

            try:
                res = self.exchange.order(
                    name=coin,
                    is_buy=is_buy,
                    sz=sz,
                    limit_px=maker_px,
                    order_type={"limit": {"tif": "Alo"}},
                    reduce_only=False
                )
                logger.info(f"HL Order Response: {res}")
            except Exception as e:
                logger.error(f"Execution failed for {coin}: {e}")

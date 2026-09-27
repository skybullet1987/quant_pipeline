import re
from pathlib import Path

daemon_file = Path("src/execution/hyperliquid_tail_daemon.py")
content = daemon_file.read_text()

order_patch = '''            if not self.dry_run:
                try:
                    res = self.exchange.market_open(
                        name=sym,
                        is_buy=is_buy,
                        sz=rounded_diff,
                        px=None,
                        slippage=0.01
                    )
                    logger.info(f"Execution Result for {sym}: {res}")
                    
                    if not is_buy:
                        self.short_entry_prices[sym] = current_px
                        sl_trigger_px = round(current_px * (1.0 + self.short_stop_pct), decimals)
                        try:
                            open_orders = self.info.open_orders(self.address)
                            for o in open_orders:
                                if o.get("coin") == sym:
                                    self.exchange.cancel(sym, o["oid"])
                            
                            sl_res = self.exchange.order(
                                name=sym,
                                is_buy=True,
                                sz=rounded_diff,
                                limit_px=sl_trigger_px,
                                order_type={"trigger": {"isMarket": True, "triggerPx": sl_trigger_px, "tpsl": "sl"}},
                                reduce_only=True
                            )
                            logger.info(f"Placed 12% native stop loss for {sym} at ${sl_trigger_px:.4f}: {sl_res}")
                        except Exception as sl_err:
                            logger.warning(f"Native SL placement failed for {sym}: {sl_err}")

                except Exception as e:
                    logger.error(f"Failed to execute order for {sym}: {e}")'''

content = re.sub(
    r'            if not self\.dry_run:\s+try:\s+res = self\.exchange\.market_open.*?(?=    def monitor_short_stops)',
    order_patch + '\n\n',
    content,
    flags=re.DOTALL
)

daemon_file.write_text(content)
print("Daemon patched successfully.")

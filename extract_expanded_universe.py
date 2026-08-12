import json
import requests
import logging
from hyperliquid.info import Info
from hyperliquid.utils import constants

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_hyperliquid_mainnet_universe():
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    meta = info.meta()
    hl_coins = {}
    for asset in meta.get("universe", []):
        raw_name = asset["name"]
        clean_name = raw_name.upper()
        
        # Normalize Hyperliquid low-denomination multipliers
        if clean_name.startswith("1000000"): base_coin = clean_name[7:]
        elif clean_name.startswith("1000"): base_coin = clean_name[4:]
        elif clean_name.startswith("K") and clean_name not in ["KAVA", "KNC"]: base_coin = clean_name[1:]
        else: base_coin = clean_name
            
        hl_coins[base_coin] = raw_name
    return hl_coins

def get_binance_futures_universe():
    res = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo").json()
    binance_coins = set()
    for symbol_info in res.get("symbols", []):
        if symbol_info.get("quoteAsset") == "USDT" and symbol_info.get("status") == "TRADING":
            binance_coins.add(symbol_info.get("baseAsset").upper())
    return binance_coins

if __name__ == "__main__":
    hl_map = get_hyperliquid_mainnet_universe()
    binance_coins = get_binance_futures_universe()
    
    intersecting_bases = sorted(list(set(hl_map.keys()).intersection(binance_coins)))
    
    logging.info(f"Discovered {len(intersecting_bases)} overlapping markets for ELT pipeline.")
    
    with open("expanded_universe.json", "w") as f:
        json.dump(intersecting_bases, f, indent=4)
    logging.info("Saved to expanded_universe.json. Feed this into your Binance historical extraction script.")

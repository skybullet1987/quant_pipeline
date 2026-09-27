import os
import time
import requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(Path.home() / "quant_pipeline" / ".env")

WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "").lower().strip()
PRIV_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY", "").strip()
INFO_URL = "https://api.hyperliquid-testnet.xyz/info"
EXCHANGE_URL = "https://api.hyperliquid-testnet.xyz/exchange"
MAINNET_INFO = "https://api.hyperliquid.xyz/info"

if not WALLET or not PRIV_KEY:
    raise ValueError("HYPERLIQUID_ACCOUNT_ADDRESS and HYPERLIQUID_PRIVATE_KEY must be set in .env")

import eth_account
try:
    from eth_account.messages import encode_typed_data
except ImportError:
    try:
        from eth_account.messages import encode_structured_data as encode_typed_data
    except ImportError:
        encode_typed_data = None

account = eth_account.Account.from_key(PRIV_KEY)

def fetch_universe_and_mids():
    meta = requests.post(INFO_URL, json={"type": "meta"}, timeout=10).json()
    coin_to_asset = {u["name"]: idx for idx, u in enumerate(meta["universe"])}
    coin_sz_decimals = {u["name"]: u.get("szDecimals", 4) for u in meta["universe"]}
    
    mids = {}
    try:
        mids.update(requests.post(MAINNET_INFO, json={"type": "allMids"}, timeout=5).json())
    except Exception:
        pass
    try:
        mids.update(requests.post(INFO_URL, json={"type": "allMids"}, timeout=5).json())
    except Exception:
        pass
        
    return coin_to_asset, coin_sz_decimals, mids

def run_reconciliation():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Starting Live State Reconciliation...")
    
    # 1. Fetch live clearinghouse state
    ch = requests.post(INFO_URL, json={"type": "clearinghouseState", "user": WALLET}, timeout=10).json()
    equity = float(ch.get("marginSummary", {}).get("accountValue", 0.0))
    if equity == 0.0:
        spot_ch = requests.post(INFO_URL, json={"type": "spotClearinghouseState", "user": WALLET}, timeout=10).json()
        equity = sum(float(b.get("total", 0.0)) for b in spot_ch.get("balances", []) if b.get("coin") == "USDC")
    print(f"[LIVE] Testnet Unified Equity: ${equity:,.2f}")
    
    coin_to_asset, coin_sz_decimals, mids = fetch_universe_and_mids()
    
    # 2. Extract current exchange positions
    current_positions = {}
    for p in ch.get("assetPositions", []):
        pos = p.get("position", {})
        coin = pos.get("coin")
        szi = float(pos.get("szi", 0.0))
        if abs(szi) > 0 and coin:
            current_positions[coin] = szi

    print(f"[LIVE] Open Exchange Positions ({len(current_positions)}):")
    for c, sz in current_positions.items():
        print(f"  • {c:<10}: {sz:+g}")

    # 3. Load Target Model Weights
    signal_file = Path.home() / "dagster_home" / "storage" / "multiscale_alpha_signals"
    raw_weights = {}
    if signal_file.exists():
        import pickle
        try:
            with open(signal_file, "rb") as f:
                raw_weights = pickle.load(f).get("weights", {})
        except Exception:
            pass
            
    if not raw_weights:
        raw_weights = {
            "XMR": 0.115, "MNT": 0.099, "BSV": 0.094, "VVV": 0.093, "GRASS": 0.088,
            "TRX": -0.235, "PAXG": -0.229, "ARB": -0.185, "CRV": -0.100, "AAVE": -0.035
        }

    longs = sorted([(k, v) for k, v in raw_weights.items() if v > 0], key=lambda x: x[1], reverse=True)[:5]
    shorts = sorted([(k, v) for k, v in raw_weights.items() if v < 0], key=lambda x: x[1])[:5]
    top_weights = dict(longs + shorts)

    # 4. Calculate target position sizes
    target_sizes = {}
    for coin, weight in top_weights.items():
        if coin in mids and float(mids[coin]) > 0:
            px = float(mids[coin])
            ntl = equity * weight
            target_sizes[coin] = ntl / px

    print("\n" + "=" * 70)
    print(f"{'SYMBOL':<10} {'CURRENT':<14} {'TARGET':<14} {'DELTA':<14} {'ACTION'}")
    print("=" * 70)

    # 5. Compute order deltas
    all_coins = set(current_positions.keys()).union(set(target_sizes.keys()))

    for coin in sorted(all_coins):
        curr_sz = current_positions.get(coin, 0.0)
        tgt_sz = target_sizes.get(coin, 0.0)
        delta = tgt_sz - curr_sz
        px = float(mids.get(coin, 1.0))
        delta_usd = abs(delta * px)

        if coin not in target_sizes and abs(curr_sz) > 0:
            action = f"CLOSE POSITION ({curr_sz:+g})"
        elif abs(delta_usd) > 5.0:
            action = f"{'BUY' if delta > 0 else 'SELL'} (Delta: {delta:+.4f} | ~${delta_usd:.2f})"
        else:
            action = "HOLD (In-Range)"

        print(f"{coin:<10} {curr_sz:<14.4f} {tgt_sz:<14.4f} {delta:<14.4f} {action}")

    print("=" * 70)

if __name__ == "__main__":
    run_reconciliation()

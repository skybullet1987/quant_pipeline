import sys
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.config import settings
from src.execution.exchange_gateway import HyperliquidGateway
from src.execution.state_manager import StateManager

MASTER_WALLET = "0x9703B71686219D34869e8FB89a93263f9e0d50A5"

def main():
    print("=" * 80)
    print("         HYPERLIQUID TESTNET ACCOUNT AUDIT & FRESH RESTART RESET        ")
    print("=" * 80)

    secret_key = (
        getattr(settings, "hl_secret_key", None) 
        or getattr(settings, "hyperliquid_private_key", None)
        or getattr(settings, "secret_key", None)
    )

    gw = HyperliquidGateway(secret_key=secret_key, account_address=MASTER_WALLET, testnet=True)
    sm = StateManager()

    print(f" • Connected to Network:  Hyperliquid Testnet ({gw.base_url})")
    print(f" • Master Wallet Address: {gw.account_address}")
    if gw.wallet:
        print(f" • Agent Signer Address:  {gw.wallet.address}")

    # 1. Audit Current State
    equity, cash, positions = gw.get_account_state()
    open_orders = gw.get_open_orders()

    print("\n--- [1] CURRENT STATE BEFORE RESET ---")
    print(f" • Unified Portfolio Value: ${equity:,.2f} USDC")
    print(f" • Available Cash:          ${cash:,.2f} USDC")
    print(f" • Open Positions ({len(positions)}):")
    for sym, pos in positions.items():
        print(f"    - {sym:<8}: Size: {pos['size']:<8} | Entry: {pos['entry_px']:<10} | uPnL: ${pos['unrealized_pnl']:+.2f}")
    print(f" • Open Resting Orders:     {len(open_orders)}")

    # 2. Cancel Resting Orders
    if len(open_orders) > 0 and gw.exchange:
        print("\n--- [2] CANCELING OPEN RESTING ORDERS ---")
        canceled = gw.cancel_all_open_orders()
        print(f" • Successfully canceled {canceled} orders.")
    else:
        print("\n--- [2] CANCELING OPEN RESTING ORDERS ---")
        print(" • No resting orders to cancel.")

    # 3. Flatten All Open Positions
    if len(positions) > 0 and gw.exchange:
        print("\n--- [3] FLATTENING ALL 8 POSITIONS TO CASH ---")
        close_res = gw.close_all_positions()
        for r in close_res:
            print(f" • Flattened {r['symbol']:<8} ({r['size']:<8}): {r['res']}")
    else:
        print("\n--- [3] FLATTENING ALL 8 POSITIONS TO CASH ---")
        print(" • No open positions to flatten or exchange signer not configured.")

    # 4. Wipe Local Database State
    print("\n--- [4] RESETTING LOCAL STATE DATABASE ---")
    sm.clear_all_positions()
    sm.set_meta("latest_target_weights", {})
    sm.set_meta("last_rebalance_utc", None)
    sm.set_meta("last_equity", equity)
    print(" • SQLite state.db positions table cleared.")
    print(" • Metadata and target weights reset to clean state.")

    # 5. Final Confirmation
    final_eq, final_cash, final_pos = gw.get_account_state()
    final_ord = gw.get_open_orders()

    print("\n" + "=" * 80)
    print("                         POST-RESET AUDIT SUMMARY                               ")
    print("=" * 80)
    print(f" • Clean Starting Equity:        ${final_eq:,.2f} USDC")
    print(f" • Available Cash:               ${final_cash:,.2f} USDC")
    print(f" • Open Positions:               {len(final_pos)} (Target: 0)")
    print(f" • Active Orders:                {len(final_ord)} (Target: 0)")
    print(f" • Ready for Fresh Deployment:   {'YES' if len(final_pos) == 0 and len(final_ord) == 0 else 'CHECK REJECTIONS'}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()

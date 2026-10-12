import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from collections import defaultdict
from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

OUR_OWNER = "cefbaf69-16ff-ccac-6ec1-7daa9d515356"
OUR_ADDR = "0x013a2474454fbd8738cff6a7f204ef1bc377f4e9"

def main():
    # 1. Fetch fresh trades from CLOB
    executor = PolymarketLiveExecutor(dry_run=False)
    raw_trades = []
    if executor.client:
        try:
            raw_trades = executor.client.get_trades()
            print(f"Fetched {len(raw_trades)} live raw trades from CLOB API.")
            with open("data/polymarket/clob_raw_trades.json", "w") as f:
                json.dump(raw_trades, f, indent=2)
        except Exception as e:
            print(f"Error fetching live trades: {e}, falling back to cache")
            with open("data/polymarket/clob_raw_trades.json") as f:
                raw_trades = json.load(f)
    else:
        with open("data/polymarket/clob_raw_trades.json") as f:
            raw_trades = json.load(f)

    # 2. Parse every fill
    fills = []
    for t in raw_trades:
        match_time = int(t.get("match_time", 0))
        t_utc = datetime.fromtimestamp(match_time, timezone.utc).isoformat()
        trader_side = t.get("trader_side")
        asset_id = str(t.get("asset_id"))
        market = t.get("market")
        tx_hash = t.get("transaction_hash")

        if trader_side == "TAKER":
            if t.get("owner") == OUR_OWNER or str(t.get("maker_address", "")).lower() == OUR_ADDR:
                side = t.get("side")
                size = Decimal(str(t.get("size")))
                price = Decimal(str(t.get("price")))
                # fee_rate_bps in polymarket: taker fee
                raw_bps = t.get("fee_rate_bps")
                bps = Decimal(str(raw_bps)) if raw_bps else Decimal("0")
                fee = (size * price * bps) / Decimal("10000")
                fills.append({
                    "id": t.get("id"),
                    "match_time": match_time,
                    "time_utc": t_utc,
                    "asset_id": asset_id,
                    "market": market,
                    "role": "TAKER",
                    "side": side,
                    "size": size,
                    "price": price,
                    "gross_cash": size * price,
                    "fee": fee,
                    "tx_hash": tx_hash,
                })
        elif trader_side == "MAKER":
            for mo in t.get("maker_orders", []):
                if mo.get("owner") == OUR_OWNER or str(mo.get("maker_address", "")).lower() == OUR_ADDR:
                    side = mo.get("side")
                    size = Decimal(str(mo.get("matched_amount")))
                    price = Decimal(str(mo.get("price")))
                    raw_bps = mo.get("fee_rate_bps")
                    bps = Decimal(str(raw_bps)) if raw_bps else Decimal("0")
                    fee = (size * price * bps) / Decimal("10000")
                    fills.append({
                        "id": t.get("id"),
                        "match_time": match_time,
                        "time_utc": t_utc,
                        "asset_id": asset_id,
                        "market": market,
                        "role": "MAKER",
                        "side": side,
                        "size": size,
                        "price": price,
                        "gross_cash": size * price,
                        "fee": fee,
                        "tx_hash": tx_hash,
                    })

    fills.sort(key=lambda x: x["match_time"])
    print(f"Total individual fills for our account: {len(fills)}")

    with open("data/polymarket/live_harvester_state.json") as f:
        harvester_state = json.load(f)
    closed = harvester_state.get("closed_positions", [])

    # Group fills by asset_id (token_id)
    fills_by_token = defaultdict(list)
    for f in fills:
        fills_by_token[f["asset_id"]].append(f)

    print("\n" + "="*120)
    print("AUTHORITATIVE FILL-LEVEL RECONCILIATION FOR ALL 20 POSITIONS")
    print("="*120)
    header = f"{'#':<2} | {'Mkt ID':<7} | {'Asset':<4} | {'Target':<4} | {'Entry UTC':<20} | {'Buy Shrs':<8} | {'Buy Cash':<8} | {'Sell Shrs':<8} | {'Sell Cash':<8} | {'Fees':<6} | {'Gross PnL':<9} | {'Net PnL':<8} | {'Close Reason'}"
    print(header)
    print("-" * 120)

    total_gross_pnl = Decimal("0")
    total_net_pnl = Decimal("0")
    total_fees = Decimal("0")
    total_buys = Decimal("0")
    total_sells = Decimal("0")

    trade_reconciliation = []

    for idx, p in enumerate(closed):
        mkt_id = str(p.get("market_id"))
        tok_id = str(p.get("token_id"))
        target = p.get("target_token")
        asset = p.get("asset")
        entry_utc = p.get("entry_time_utc", "")[:19]
        reason = p.get("close_reason")

        t_fills = fills_by_token.get(tok_id, [])
        buy_shrs = sum(f["size"] for f in t_fills if f["side"] == "BUY")
        buy_cash = sum(f["gross_cash"] for f in t_fills if f["side"] == "BUY")
        buy_fees = sum(f["fee"] for f in t_fills if f["side"] == "BUY")

        sell_shrs = sum(f["size"] for f in t_fills if f["side"] == "SELL")
        sell_cash = sum(f["gross_cash"] for f in t_fills if f["side"] == "SELL")
        sell_fees = sum(f["fee"] for f in t_fills if f["side"] == "SELL")

        # Check if resolved at maturity on-chain
        payout_usd = Decimal(str(p.get("payout_usd", 0.0)))
        state_net = Decimal(str(p.get("net_pnl_usd", 0.0)))

        # If trade resolved at maturity on-chain with payout, but no CLOB sell fill
        # e.g. MARKET_RESOLVED
        if sell_shrs == 0 and payout_usd > 0:
            effective_sell_cash = payout_usd
            effective_sell_shrs = buy_shrs
        else:
            effective_sell_cash = sell_cash
            effective_sell_shrs = sell_shrs

        trade_fees = buy_fees + sell_fees
        # Also check harvester fee_usd if recorded
        h_fee = Decimal(str(p.get("fee_usd", 0.0))) + Decimal(str(p.get("realized_exit_fee", 0.0)))

        gross_pnl = effective_sell_cash - buy_cash
        net_pnl = gross_pnl - h_fee

        total_buys += buy_cash
        total_sells += effective_sell_cash
        total_fees += h_fee
        total_gross_pnl += gross_pnl
        total_net_pnl += net_pnl

        trade_reconciliation.append({
            "index": idx + 1,
            "market_id": mkt_id,
            "asset": asset,
            "target": target,
            "entry_utc": entry_utc,
            "buy_shrs": float(buy_shrs),
            "buy_cash": float(buy_cash),
            "sell_shrs": float(effective_sell_shrs),
            "sell_cash": float(effective_sell_cash),
            "fee": float(h_fee),
            "gross_pnl": float(gross_pnl),
            "net_pnl": float(net_pnl),
            "state_net": float(state_net),
            "reason": reason,
        })

        asset_str = str(asset or "N/A")
        target_str = str(target or "N/A")
        print(f"{idx+1:<2} | {mkt_id:<7} | {asset_str:<4} | {target_str:<4} | {entry_utc:<20} | {buy_shrs:<8.2f} | ${buy_cash:<7.2f} | {effective_sell_shrs:<8.2f} | ${effective_sell_cash:<7.2f} | ${h_fee:<5.2f} | ${gross_pnl:<+8.2f} | ${net_pnl:<+7.2f} | {reason}")

    print("-" * 120)
    print(f"TOTALS ACROSS ALL 20 TRADES:")
    print(f"Total Gross Buys:       ${total_buys:.2f}")
    print(f"Total Gross Sells:      ${total_sells:.2f}")
    print(f"Total Gross Trading PnL:${total_gross_pnl:.2f}")
    print(f"Total Fees Paid:        ${total_fees:.2f}")
    print(f"Total Net Trading PnL:  ${total_net_pnl:.2f}")

    # Now trades 14-20
    cutoff = datetime(2026, 10, 12, 5, 16, 0, tzinfo=timezone.utc)
    t14_20 = [t for t in trade_reconciliation if datetime.fromisoformat(t["entry_utc"].replace("Z", "+00:00") if "+" in t["entry_utc"] else t["entry_utc"] + "+00:00") >= cutoff]

    print("\n" + "="*120)
    print("DETAILED BREAKDOWN: TRADES 14-20 (SINCE 05:16 UTC)")
    print("="*120)
    t14_buys = sum(Decimal(str(t["buy_cash"])) for t in t14_20)
    t14_sells = sum(Decimal(str(t["sell_cash"])) for t in t14_20)
    t14_gross = sum(Decimal(str(t["gross_pnl"])) for t in t14_20)
    t14_fees = sum(Decimal(str(t["fee"])) for t in t14_20)
    t14_net = sum(Decimal(str(t["net_pnl"])) for t in t14_20)
    t14_state_net = sum(Decimal(str(t["state_net"])) for t in t14_20)

    for t in t14_20:
        print(f"Trade #{t['index']} (Mkt {t['market_id']}): Buy=${t['buy_cash']:.2f}, Sell=${t['sell_cash']:.2f}, Gross=${t['gross_pnl']:+.2f}, Fee=${t['fee']:.2f}, Net=${t['net_pnl']:+.2f} (State Net=${t['state_net']:+.2f}) | {t['reason']}")

    print("-" * 120)
    print(f"Trades 14-20 Gross PnL:      ${t14_gross:.2f}")
    print(f"Trades 14-20 Fees:           ${t14_fees:.2f}")
    print(f"Trades 14-20 Net Trading PnL:${t14_net:.2f}")
    print(f"Trades 14-20 State Net PnL:  ${t14_state_net:.2f}")

    # Check live collateral balance
    current_collat = executor.get_collateral_balance()
    print(f"\nLive Verified Collateral Balance: ${current_collat:.6f}")

if __name__ == "__main__":
    main()

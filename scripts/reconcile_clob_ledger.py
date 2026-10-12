import json
import os
from datetime import datetime, timezone
from collections import defaultdict

OUR_OWNER = "cefbaf69-16ff-ccac-6ec1-7daa9d515356"
OUR_ADDR = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9".lower()

def parse_our_fills(trades):
    fills = []
    for t in trades:
        t_time = datetime.fromtimestamp(int(t.get('match_time', 0)), timezone.utc).isoformat()
        trader_side = t.get('trader_side')
        asset_id = str(t.get('asset_id'))
        market = t.get('market')
        tx_hash = t.get('transaction_hash')

        if trader_side == 'TAKER':
            if t.get('owner') == OUR_OWNER:
                side = t.get('side') # BUY or SELL
                size = float(t.get('size'))
                price = float(t.get('price'))
                fee_rate_bps = float(t.get('fee_rate_bps') or 0.0)
                fee_usd = (size * price * fee_rate_bps) / 10000.0
                cash_flow = -size * price if side == 'BUY' else size * price
                fills.append({
                    'trade_id': t.get('id'),
                    'time_utc': t_time,
                    'timestamp': int(t.get('match_time', 0)),
                    'role': 'TAKER',
                    'side': side,
                    'size': size,
                    'price': price,
                    'cash_flow': cash_flow,
                    'fee_usd': fee_usd,
                    'asset_id': asset_id,
                    'market': market,
                    'tx_hash': tx_hash,
                })
        elif trader_side == 'MAKER':
            for mo in t.get('maker_orders', []):
                if mo.get('owner') == OUR_OWNER or str(mo.get('maker_address', '')).lower() == OUR_ADDR:
                    side = mo.get('side')
                    size = float(mo.get('matched_amount'))
                    price = float(mo.get('price'))
                    fee_rate_bps = float(mo.get('fee_rate_bps') or 0.0)
                    fee_usd = (size * price * fee_rate_bps) / 10000.0
                    cash_flow = -size * price if side == 'BUY' else size * price
                    fills.append({
                        'trade_id': t.get('id'),
                        'time_utc': t_time,
                        'timestamp': int(t.get('match_time', 0)),
                        'role': 'MAKER',
                        'side': side,
                        'size': size,
                        'price': price,
                        'cash_flow': cash_flow,
                        'fee_usd': fee_usd,
                        'asset_id': asset_id,
                        'market': market,
                        'tx_hash': tx_hash,
                    })
    fills.sort(key=lambda x: x['timestamp'])
    return fills

def main():
    with open('data/polymarket/clob_raw_trades.json') as f:
        trades = json.load(f)

    with open('data/polymarket/live_harvester_state.json') as f:
        harvester_state = json.load(f)

    fills = parse_our_fills(trades)
    fills_by_asset = defaultdict(list)
    for f in fills:
        fills_by_asset[f['asset_id']].append(f)

    closed_pos = harvester_state.get('closed_positions', [])

    print("==========================================================================================")
    print("ALL 20 CLOSED TRADES - COMPLETE LEDGER RECONCILIATION")
    print("==========================================================================================")
    print(f"{'#':<2} | {'Mkt ID':<7} | {'Entry UTC':<20} | {'Side':<4} | {'Buys $':<7} | {'Sells $':<7} | {'Net Cash':<9} | {'Harv PnL':<9} | {'Harv Reason'}")
    print("-" * 110)

    for i, p in enumerate(closed_pos):
        tok = str(p.get('token_id'))
        a_fills = fills_by_asset.get(tok, [])
        b_usd = sum(-f['cash_flow'] for f in a_fills if f['side'] == 'BUY')
        s_usd = sum(f['cash_flow'] for f in a_fills if f['side'] == 'SELL')
        net_cash = s_usd - b_usd
        h_pnl = float(p.get('net_pnl_usd', 0.0))
        m_id = str(p.get('market_id'))
        ent_time = p.get('entry_time_utc', '')[:19]
        tgt = p.get('target_token')
        reason = p.get('close_reason')
        print(f"{i+1:<2} | {m_id:<7} | {ent_time:<20} | {tgt:<4} | ${b_usd:<6.2f} | ${s_usd:<6.2f} | ${net_cash:<+8.2f} | ${h_pnl:<+8.2f} | {reason}")

    # Now let's calculate the 7 trades after 05:16 UTC
    cutoff = datetime(2026, 10, 12, 5, 16, 0, tzinfo=timezone.utc)
    after_trades = [p for p in closed_pos if datetime.fromisoformat(p['entry_time_utc']) >= cutoff]

    print("\n==========================================================================================")
    print("RECONCILIATION OF ACCOUNT MOVEMENT SINCE 05:16 UTC (OCT 12)")
    print("Initial Collateral at 05:16 UTC: $273.23")
    print("Current Collateral:              $249.24")
    print("Actual Account Movement:         -$23.99")
    print("==========================================================================================")

    tot_after_buys = 0.0
    tot_after_sells = 0.0
    tot_after_harv_pnl = 0.0

    for p in after_trades:
        tok = str(p.get('token_id'))
        a_fills = fills_by_asset.get(tok, [])
        b_usd = sum(-f['cash_flow'] for f in a_fills if f['side'] == 'BUY')
        s_usd = sum(f['cash_flow'] for f in a_fills if f['side'] == 'SELL')
        tot_after_buys += b_usd
        tot_after_sells += s_usd
        h_pnl = float(p.get('net_pnl_usd', 0.0))
        tot_after_harv_pnl += h_pnl
        net_cash = s_usd - b_usd
        print(f"Mkt {p.get('market_id')}: Buys=${b_usd:.2f}, Sells=${s_usd:.2f} -> Net Cash Flow=${net_cash:+.2f} | Harvester Logged PnL=${h_pnl:+.2f}")

    net_after_cash = tot_after_sells - tot_after_buys
    print("-" * 80)
    print(f"Sum of Net Cash Flows on CLOB:     ${net_after_cash:+.2f}")
    print(f"Account Movement ($249.24 - $273.23): -$23.99")
    print(f"Discrepancy with Cash Movement:    ${net_after_cash - (-23.99):+.2f}")
    print(f"Sum of Harvester Logged PnL:       ${tot_after_harv_pnl:+.2f}")
    print(f"Harvester Logging Distortion:      ${tot_after_harv_pnl - net_after_cash:+.2f}")

if __name__ == '__main__':
    main()

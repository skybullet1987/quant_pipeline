import json

def clean_state():
    with open('data/polymarket/live_harvester_state.json') as f:
        state = json.load(f)

    for p in state['closed_positions']:
        mid = str(p.get('market_id'))
        if mid == '5482092':
            p['won'] = False
            p['payout_usd'] = 19.81
            p['realized_exit_cash'] = 19.81
            p['filled_exit_shares'] = 47.16
            p['remaining_shares'] = 0.0039
            p['remaining_exit_shares'] = 0.0039
            p['close_reason'] = 'ADVERSE_STOP_LOSS_UNWIND'
            p['net_pnl_usd'] = round(19.81 - p['notional_usd'] - p['fee_usd'], 2)
        elif mid == '5483810':
            p['won'] = False
            p['payout_usd'] = 9.30
            p['realized_exit_cash'] = 9.30
            p['filled_exit_shares'] = 16.04
            p['remaining_shares'] = 0.0082
            p['remaining_exit_shares'] = 0.0082
            p['close_reason'] = 'ADVERSE_STOP_LOSS_UNWIND'
            p['net_pnl_usd'] = round(9.30 - p['notional_usd'] - p['fee_usd'], 2)
        elif mid == '5485046':
            p['won'] = False
            p['payout_usd'] = 22.67
            p['realized_exit_cash'] = 22.67
            p['filled_exit_shares'] = 40.48
            p['remaining_shares'] = 0.0068
            p['remaining_exit_shares'] = 0.0068
            p['close_reason'] = 'ADVERSE_STOP_LOSS_UNWIND'
            p['net_pnl_usd'] = round(22.67 - p['notional_usd'] - p['fee_usd'], 2)

    tot_pnl = sum(p['net_pnl_usd'] for p in state['closed_positions'])
    wins = [p for p in state['closed_positions'] if p['won']]
    losses = [p for p in state['closed_positions'] if not p['won']]
    win_pnl = sum(p['net_pnl_usd'] for p in wins)
    loss_pnl = sum(p['net_pnl_usd'] for p in losses)

    print(f"Total trades: {len(state['closed_positions'])}")
    print(f"Profitable trades: {len(wins)} | Win PnL: +{win_pnl:.2f}")
    print(f"Losing trades:     {len(losses)} | Loss PnL: {loss_pnl:.2f}")
    print(f"Net Realized PnL:  {tot_pnl:.2f}")

    with open('data/polymarket/live_harvester_state.json', 'w') as f:
        json.dump(state, f, indent=2)
    print("Successfully saved data/polymarket/live_harvester_state.json with reconciled trade outcomes.")

if __name__ == '__main__':
    clean_state()

import json
from decimal import Decimal

with open('data/polymarket/clob_raw_trades.json') as f:
    trades = json.load(f)

with open('data/polymarket/live_harvester_state.json') as f:
    state = json.load(f)

mkt_map = {}
for p in state['closed_positions']:
    mkt_map[str(p.get('token_id'))] = str(p.get('market_id'))

target_markets_13 = {'5406281', '5412962', '5414643', '5459784', '5459749', '5466895', '5466896', '5469116', '5469117', '5476434', '5476433', '5477110', '5478990'}

events_13 = []
OUR_OWNER = 'cefbaf69-16ff-ccac-6ec1-7daa9d515356'
OUR_ADDR = '0x013a2474454fbd8738cff6a7f204ef1bc377f4e9'

for t in trades:
    asset_id = str(t.get('asset_id'))
    if asset_id in mkt_map and mkt_map[asset_id] in target_markets_13:
        ts = int(t.get('match_time', 0))
        if t.get('trader_side') == 'TAKER' and (t.get('owner') == OUR_OWNER or str(t.get('maker_address', '')).lower() == OUR_ADDR):
            s = Decimal(str(t.get('size')))
            p = Decimal(str(t.get('price')))
            side = t.get('side')
            cash = -s * p if side == 'BUY' else s * p
            events_13.append((ts, mkt_map[asset_id], 'TAKER', side, s, p, cash))
        elif t.get('trader_side') == 'MAKER':
            for mo in t.get('maker_orders', []):
                if mo.get('owner') == OUR_OWNER or str(mo.get('maker_address', '')).lower() == OUR_ADDR:
                    s = Decimal(str(mo.get('matched_amount')))
                    p = Decimal(str(mo.get('price')))
                    side = mo.get('side')
                    cash = -s * p if side == 'BUY' else s * p
                    events_13.append((ts, mkt_map[asset_id], 'MAKER', side, s, p, cash))

tot_cash_13 = sum(e[6] for e in events_13)
print("Events for trades 1-13:", len(events_13))
print("Total net cash flow on CLOB for trades 1-13:", float(tot_cash_13))

# On-chain redemptions:
# Market 5459749: won UP (+37.05)
# Market 5469117: won DOWN (+19.34)
# Market 5476434: won UP (+27.59)
tot_cash_with_redemptions = tot_cash_13 + Decimal("37.05") + Decimal("19.34") + Decimal("27.59")
print("Total net cash with redemptions for trades 1-13:", float(tot_cash_with_redemptions))

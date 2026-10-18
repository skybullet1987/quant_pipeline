#!/usr/bin/env python3
import json
import time
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('data/polymarket')
resolutions = {str(json.loads(l)['market_id']): json.loads(l) for l in open(DATA_DIR / 'finalized_market_resolutions.jsonl') if l.strip()}
triggers = []
candidate_mids = set()
for l in open(DATA_DIR / 'live_shock_triggers.jsonl'):
    if not l.strip(): continue
    r = json.loads(l)
    mid = str(r.get('market_id'))
    if mid not in resolutions: continue
    s_dir = r.get('shock_direction')
    if not s_dir: continue
    target = 'UP' if s_dir == 'BUY' else 'DOWN'
    feat = r.get('pre_shock_features_t0', {}).get(target, {})
    ask = float(feat.get('best_ask', 0.0) or 0.0)
    bid = float(feat.get('best_bid', 0.0) or 0.0)
    candidate_mids.add(mid)
    triggers.append({
        'market_id': mid, 'asset': r.get('asset', 'BTC'),
        't0_unix': float(r.get('t0_unix', 0.0)), 'seconds_to_expiry': float(r.get('seconds_to_expiry', 0.0)),
        'target_token': target, 'ask_price': ask, 'bid_price': bid,
        'candle_distance_pct': float(r.get('candle_distance_pct', 0.0)),
    })
triggers.sort(key=lambda x: x['t0_unix'])

telemetry = defaultdict(list)
for l in open(DATA_DIR / 'polymarket_hourly_telemetry.jsonl'):
    if not l.strip(): continue
    r = json.loads(l)
    mid = str(r.get('market_id'))
    if mid in candidate_mids:
        telemetry[mid].append((
            float(r.get('timestamp_unix', 0.0)), float(r.get('binance_spot', 0.0)), float(r.get('candle_distance_pct', 0.0)),
            float(r.get('UP', {}).get('best_bid', 0.0) or 0.0), float(r.get('UP', {}).get('best_ask', 0.0) or 0.0),
            float(r.get('DOWN', {}).get('best_bid', 0.0) or 0.0), float(r.get('DOWN', {}).get('best_ask', 0.0) or 0.0),
        ))
for mid in telemetry: telemetry[mid].sort(key=lambda x: x[0])

def test_dynamic(max_tte, cushion_25m, cushion_40m, conc=2):
    trades = []
    active = []
    traded = set()
    for trig in triggers:
        mid = trig['market_id']
        if mid in traded: continue
        t0 = trig['t0_unix']
        active = [p for p in active if p['expiry'] > t0]
        if len(active) >= conc: continue
        if any(p['asset'] == trig['asset'] for p in active): continue
        tte = trig['seconds_to_expiry']
        if tte > max_tte or tte < 120.0: continue
        ask = trig['ask_price']
        if ask < 0.72 or ask > 0.88: continue
        req_cushion = cushion_40m if tte > 1500.0 else cushion_25m
        dist = trig['candle_distance_pct']
        target = trig['target_token']
        if abs(dist) < req_cushion: continue
        if target == 'UP' and dist < req_cushion: continue
        if target == 'DOWN' and dist > -req_cushion: continue
        # NYSE blackout
        dt_hr = int(time.strftime('%H', time.gmtime(t0)))
        dt_mn = int(time.strftime('%M', time.gmtime(t0)))
        if dt_hr == 13 and dt_mn >= 30: continue
        
        res = resolutions[mid]
        winning = res.get('winning_outcome')
        telem = telemetry.get(mid, [])
        post = [pt for pt in telem if pt[0] >= t0]
        exit_px = None
        # Policy B stop
        start_adv = None
        for pt in post:
            adv = (pt[2] <= -0.05) if target == 'UP' else (pt[2] >= 0.05)
            if adv:
                if start_adv is None: start_adv = pt[0]
                elif pt[0] - start_adv >= 15.0:
                    b_stop = pt[3] if target == 'UP' else pt[5]
                    exit_px = max(0.40, min(0.65, b_stop if b_stop > 0.01 else 0.45))
                    break
            else: start_adv = None
        if exit_px is None:
            for pt in post:
                ta = pt[4] if target == 'UP' else pt[6]
                tb = pt[3] if target == 'UP' else pt[5]
                if ta >= 0.99 or tb >= 0.99:
                    exit_px = 0.99
                    break
        if exit_px is None:
            exit_px = 1.00 if target == winning else 0.00
        pnl = (25.0 / ask) * exit_px - 25.0
        trades.append({'won': pnl > 0, 'pnl': pnl})
        traded.add(mid)
        active.append({'asset': trig['asset'], 'expiry': t0 + tte})
    wins = [t for t in trades if t['won']]
    losses = [t for t in trades if not t['won']]
    wr = len(wins) / len(trades) * 100 if trades else 0
    gp = sum(t['pnl'] for t in wins)
    gl = abs(sum(t['pnl'] for t in losses))
    pf = gp / gl if gl > 0 else 999
    # max dd
    cum = peak = mdd = 0
    for t in trades:
        cum += t['pnl']
        if cum > peak: peak = cum
        if peak - cum > mdd: mdd = peak - cum
    print(f"MaxTTE={max_tte:4.0f}s ({max_tte/60:4.1f}m) | C_25m={cushion_25m:.2f}% | C_early={cushion_40m:.2f}% | Trades={len(trades):3d} | WR={wr:5.1f}% | PF={pf:4.2f} | MDD=${mdd:6.2f} | PnL=+${sum(t['pnl'] for t in trades):6.2f}")

print("--- Dynamic Cushion Scaling Evaluation ---")
test_dynamic(1500, 0.15, 0.15)
test_dynamic(1800, 0.15, 0.20)
test_dynamic(2100, 0.15, 0.25)
test_dynamic(2400, 0.15, 0.25)
test_dynamic(2400, 0.15, 0.30)
test_dynamic(2700, 0.15, 0.30)
test_dynamic(2400, 0.15, 0.25, conc=1)
test_dynamic(2400, 0.15, 0.30, conc=1)

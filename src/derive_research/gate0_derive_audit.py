"""
Gate 0 Audit: Derive (Lyra v3) 0DTE / Short-Dated Options & Debit Spread Microstructure
Evaluates:
  1. Instrument availability for nearest expiry (0DTE / 1DTE)
  2. Outright Call/Put executable bid-ask spreads, depth, and fee friction
  3. Vertical Debit Spread economics: Width, Net Debit, Bid-Ask Compression, Max Payoff Ratio
  4. Fee structure & capital requirements
"""

import sys
import json
import time
import datetime
import requests
from typing import Dict, List, Any, Optional

DERIVE_API_BASE = "https://api.lyra.finance/public"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def get_all_active_options(currency: str = "BTC") -> List[Dict[str, Any]]:
    """Fetch all active options for a currency."""
    all_instruments = []
    page = 1
    while True:
        payload = {
            "expired": False,
            "instrument_type": "option",
            "currency": currency,
            "page": page,
            "page_size": 100
        }
        try:
            r = requests.post(f"{DERIVE_API_BASE}/get_all_instruments", json=payload, headers=HEADERS, timeout=10)
            data = r.json().get("result", {})
            instruments = data.get("instruments", [])
            if not instruments:
                break
            all_instruments.extend(instruments)
            if len(instruments) < 100:
                break
            page += 1
        except Exception as e:
            print(f"Error fetching page {page} for {currency}: {e}")
            break
    return all_instruments

def get_ticker(instrument_name: str) -> Optional[Dict[str, Any]]:
    """Fetch ticker with bid, ask, sizes, and Greeks."""
    payload = {"instrument_name": instrument_name}
    try:
        r = requests.post(f"{DERIVE_API_BASE}/get_ticker", json=payload, headers=HEADERS, timeout=5)
        res = r.json()
        if "result" in res:
            return res["result"]
        return None
    except Exception as e:
        return None

def run_audit(currency: str = "BTC"):
    print(f"\n=======================================================")
    print(f"   GATE 0 DERIVE AUDIT: {currency} SHORT-DATED OPTIONS")
    print(f"=======================================================")
    
    start_t = time.time()
    instruments = get_all_active_options(currency)
    print(f"Total active {currency} options found: {len(instruments)}")
    
    if not instruments:
        print(f"No active instruments found for {currency}.")
        return

    # Group by expiry
    expiries: Dict[int, List[Dict[str, Any]]] = {}
    for inst in instruments:
        details = inst.get("option_details", {})
        exp = details.get("expiry")
        if exp:
            expiries.setdefault(exp, []).append(inst)

    sorted_exp = sorted(expiries.keys())
    now_ts = int(time.time())
    
    # Filter for future expiries
    future_exp = [e for e in sorted_exp if e > now_ts]
    if not future_exp:
        print("No future expiries found!")
        return

    nearest_exp = future_exp[0]
    time_to_exp_hours = (nearest_exp - now_ts) / 3600.0
    exp_dt = datetime.datetime.fromtimestamp(nearest_exp, datetime.timezone.utc)
    
    print(f"Nearest Expiry: {exp_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} ({time_to_exp_hours:.1f} hours away)")
    contracts = expiries[nearest_exp]
    print(f"Strikes available for nearest expiry: {len(contracts)}")

    # Sample underlying spot price from first available ticker
    sample_ticker = get_ticker(contracts[0]["instrument_name"])
    if not sample_ticker:
        print("Failed to fetch sample ticker.")
        return

    index_price = float(sample_ticker.get("index_price", 0))
    print(f"Current {currency} Spot/Index Price: ${index_price:,.2f}")
    
    # Fetch tickers for all contracts in nearest expiry
    tickers = []
    print(f"\nSampling orderbook data for {len(contracts)} contracts...")
    for idx, inst in enumerate(contracts):
        name = inst["instrument_name"]
        tick = get_ticker(name)
        if tick:
            tickers.append((inst, tick))
        time.sleep(0.05) # Rate limit courtesy

    print(f"Retrieved {len(tickers)} valid tickers.\n")
    
    # Separate Calls and Puts
    calls = []
    puts = []
    for inst, tick in tickers:
        opt_type = inst["option_details"]["option_type"]
        strike = float(inst["option_details"]["strike"])
        bid_p = float(tick.get("best_bid_price", 0))
        ask_p = float(tick.get("best_ask_price", 0))
        bid_s = float(tick.get("best_bid_amount", 0))
        ask_s = float(tick.get("best_ask_amount", 0))
        mark_p = float(tick.get("mark_price", 0))
        pricing = tick.get("option_pricing", {}) or {}
        delta = float(pricing.get("delta", 0))
        iv = float(pricing.get("iv", 0))
        
        row = {
            "name": inst["instrument_name"],
            "strike": strike,
            "type": opt_type,
            "bid": bid_p,
            "ask": ask_p,
            "bid_size": bid_s,
            "ask_size": ask_s,
            "mark": mark_p,
            "delta": delta,
            "iv": iv
        }
        if opt_type == "C":
            calls.append(row)
        else:
            puts.append(row)

    calls.sort(key=lambda x: x["strike"])
    puts.sort(key=lambda x: x["strike"])

    # --- PIVOT A: OUTRIGHT OPTIONS EVALUATION ---
    print("-------------------------------------------------------------------------------")
    print(f"PIVOT A: OUTRIGHT OPTIONS NEAR-THE-MONEY ({currency})")
    print("-------------------------------------------------------------------------------")
    print(f"{'Instrument':<26} {'Strike':<8} {'Bid':<8} {'Ask':<8} {'Mark':<8} {'Spread %':<10} {'Bid$ Depth':<12} {'Ask$ Depth':<12}")
    
    liquid_calls = []
    for c in calls:
        # Near the money (+/- 10%)
        if 0.90 * index_price <= c["strike"] <= 1.10 * index_price:
            spread_pct = ((c["ask"] - c["bid"]) / c["mark"] * 100.0) if (c["mark"] > 0 and c["bid"] > 0) else 999.0
            bid_usd = c["bid"] * c["bid_size"] if currency == "USD" else c["bid"] * c["bid_size"] # premium is in USDC
            ask_usd = c["ask"] * c["ask_size"]
            print(f"{c['name']:<26} {c['strike']:<8.0f} {c['bid']:<8.1f} {c['ask']:<8.1f} {c['mark']:<8.1f} {spread_pct:<9.1f}% ${bid_usd:<11.1f} ${ask_usd:<11.1f}")
            if c["bid"] > 0 and c["ask"] > 0 and c["ask_size"] > 0:
                liquid_calls.append(c)

    # --- PIVOT B: ATOMIC VERTICAL DEBIT SPREADS EVALUATION ---
    print("\n-------------------------------------------------------------------------------")
    print(f"PIVOT B: ATOMIC VERTICAL CALL DEBIT SPREADS (BULL CALL SPREADS)")
    print("-------------------------------------------------------------------------------")
    print(f"{'Spread Pair':<32} {'Width':<8} {'Debit(Ask-Bid)':<15} {'Debit(Mid)':<12} {'Max Payoff':<12} {'Max Multiplier':<14} {'Exec Frictions'}")
    
    spread_candidates = []
    for i in range(len(liquid_calls)):
        for j in range(i + 1, min(i + 4, len(liquid_calls))):
            c_long = liquid_calls[i]
            c_short = liquid_calls[j]
            width = c_short["strike"] - c_long["strike"]
            if width <= 0:
                continue
            
            # Legging/Cross-book debit: Buy long at Ask, Sell short at Bid
            exec_debit = c_long["ask"] - c_short["bid"]
            
            # Fair mid debit:
            mid_long = (c_long["ask"] + c_long["bid"]) / 2.0
            mid_short = (c_short["ask"] + c_short["bid"]) / 2.0
            mid_debit = mid_long - mid_short
            
            if exec_debit > 0 and exec_debit < width:
                max_profit = width - exec_debit
                max_mult = width / exec_debit
                spread_candidates.append({
                    "pair": f"{int(c_long['strike'])}/{int(c_short['strike'])} C",
                    "long": c_long["name"],
                    "short": c_short["name"],
                    "width": width,
                    "exec_debit": exec_debit,
                    "mid_debit": mid_debit,
                    "max_profit": max_profit,
                    "max_mult": max_mult,
                    "spread_friction": (exec_debit - mid_debit) / mid_debit * 100.0 if mid_debit > 0 else 0.0
                })

    spread_candidates.sort(key=lambda x: x["max_mult"], reverse=True)
    for s in spread_candidates[:10]:
        print(f"{s['pair']:<32} ${s['width']:<7.0f} ${s['exec_debit']:<14.2f} ${s['mid_debit']:<11.2f} ${s['max_profit']:<11.2f} {s['max_mult']:<13.2f}x {s['spread_friction']:<6.1f}%")

    print("\n-------------------------------------------------------------------------------")
    print(f"AUDIT SUMMARY FOR {currency}:")
    print(f"  Total Valid Pairs Found: {len(spread_candidates)}")
    if spread_candidates:
        top = spread_candidates[0]
        print(f"  Top Asymmetric Spread: {top['pair']} -> Max Payout {top['max_mult']:.2f}x (Risk ${top['exec_debit']:.2f} to make ${top['max_profit']:.2f})")
    print(f"  Execution time: {time.time() - start_t:.1f}s")
    print("===============================================================================\n")

if __name__ == "__main__":
    curr = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    run_audit(curr)

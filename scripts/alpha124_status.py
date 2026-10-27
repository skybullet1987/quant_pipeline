#!/usr/bin/env python3
"""
CLI Scorecard & Live Opportunity Viewer for Polymarket Alpha-124 Shadow Daemon
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PROJECT_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json"
OPPS_FILE = PROJECT_ROOT / "data" / "alpha124" / "alpha124_live_opportunities.json"


def main() -> None:
    if not STATE_FILE.exists():
        print("No Alpha-124 state file found yet.")
        return
    st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    print(f"=== ALPHA-124 SHADOW SCORECARD (Updated: {st.get('updated_at_utc')}) ===")
    print(
        f"Cycles: {st.get('cycle_count')} | MakerPending: {st.get('pending_maker_orders_count', 0)} | "
        f"Monitored: {st.get('markets_monitored')}"
    )
    print(f"Spots : {st.get('spots')}")
    print(f"Realized PnL by Bankroll Tier: {st.get('portfolio_realized_pnl_by_bankroll_usd')}")
    print("\n--- Sleeve Breakdown ---")
    for sl, m in (st.get("by_sleeve") or {}).items():
        print(
            f"  {sl:28s} | Open={m['open']:2d} | Closed={m['closed']:3d} "
            f"({m['wins']}W/{m['losses']}L, WR={m['win_rate_pct']:5.1f}%) | T1000 PnL=${m['realized_pnl_t1000_usd']:+8.2f}"
        )

    pend_m = st.get("pending_maker_orders") or []
    if pend_m:
        print(f"\n--- Resting 0%-Fee Maker Entry Bids ({len(pend_m)}) ---")
        for m_o in pend_m[:10]:
            print(
                f"  [{m_o['sleeve']}] {m_o['asset_or_city']} {m_o['title']} ({m_o['side']}) | "
                f"resting_bid=${m_o['resting_bid']:.3f} (ask_at_post=${m_o['best_ask_at_post']:.3f}, p_mod={m_o['p_model_at_post']:.3f})"
            )

    open_pos = st.get("open_positions") or []
    if open_pos:
        print(f"\n--- Active Shadow Positions ({len(open_pos)}) ---")
        for p in open_pos[:15]:
            print(
                f"  [{p['sleeve']}] {p['title']} ({p['side']}) | entry_eff=${p['entry_eff_px_t1000']:.3f} "
                f"last_bid=${p.get('last_bid',0):.3f} tp=${p.get('maker_tp_px') or 0:.3f} p_mod={p['p_model_entry']:.3f}"
            )

    if OPPS_FILE.exists():
        opps = json.loads(OPPS_FILE.read_text(encoding="utf-8")).get("top_opportunities") or []
        if opps:
            print(f"\n--- Top Live Orderbook Opportunities ({len(opps)}) ---")
            for o in opps[:12]:
                print(
                    f"  [{o['sleeve']:28s}] edge={o['net_edge']:+.3f} | ask=${o['ask_vwap']:.3f} vs p={o['p_model']:.3f} "
                    f"(L1=${o['l1_usd']:.0f}) | {o['market']}"
                )


if __name__ == "__main__":
    main()

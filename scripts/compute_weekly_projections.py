def project(start_bal, win_rate, win_size_pct, loss_size_pct, trades_per_wk=70, n_weeks=8):
    bal = start_bal
    rows = []
    for wk in range(1, n_weeks + 1):
        start_wk = bal
        ticket = min(37.50, bal * 0.12)
        w_dollar = ticket * win_size_pct
        l_dollar = ticket * loss_size_pct
        ev_trade = win_rate * w_dollar - (1.0 - win_rate) * l_dollar
        wk_pnl = ev_trade * trades_per_wk
        bal += wk_pnl
        gain_pct = ((bal - start_bal) / start_bal) * 100.0
        rows.append((wk, start_wk, ticket, wk_pnl, bal, gain_pct))
    return rows

print("=== BASELINE (78% Win Rate, 70 trades/wk) ===")
for r in project(248.59, 0.78, 0.10, 0.25):
    print(f"Week {r[0]}: Start=${r[1]:.2f} | Ticket=${r[2]:.2f} | Weekly PnL=+${r[3]:.2f} | End=${r[4]:.2f} (+{r[5]:.1f}%)")

print("\n=== CONSERVATIVE (74% Win Rate, 70 trades/wk) ===")
for r in project(248.59, 0.74, 0.10, 0.25):
    print(f"Week {r[0]}: Start=${r[1]:.2f} | Ticket=${r[2]:.2f} | Weekly PnL=+${r[3]:.2f} | End=${r[4]:.2f} (+{r[5]:.1f}%)")

print("\n=== HIGH CONVICTION (82% Win Rate, 70 trades/wk) ===")
for r in project(248.59, 0.82, 0.10, 0.25):
    print(f"Week {r[0]}: Start=${r[1]:.2f} | Ticket=${r[2]:.2f} | Weekly PnL=+${r[3]:.2f} | End=${r[4]:.2f} (+{r[5]:.1f}%)")

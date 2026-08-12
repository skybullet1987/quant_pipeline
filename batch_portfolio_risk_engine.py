import pandas as pd
import numpy as np

class BatchPortfolioRiskEngine:
    def __init__(self, global_risk_cap=0.05, max_leverage=10.0, kelly_fraction=0.50):
        """
        4-Stage Batch Portfolio Risk Engine
        Stage 1: EV Gate Filtering
        Stage 2: EV Density Ranking
        Stage 3: Portfolio Risk Allocation (5% Global Adverse Risk Cap)
        Stage 4: Approved Execution Payload
        """
        self.global_risk_cap = global_risk_cap
        self.max_leverage = max_leverage
        self.kelly_fraction = kelly_fraction

    def evaluate_batch(self, candidate_signals, current_open_risk_pct=0.0):
        """
        Processes all candidate signals from a single 15-minute tick simultaneously.
        
        candidate_signals: List of dicts containing:
            ['ticker', 'prob', 'entry_price', 'atr', 'c_entry', 'c_tp', 'c_sl', 'direction']
        """
        if not candidate_signals:
            return []

        # --- STAGE 1: EV Gate & Parameter Prep ---
        valid_candidates = []
        for cand in candidate_signals:
            price, atr = cand['entry_price'], cand['atr']
            p = cand['prob']
            c_entry, c_tp, c_sl = cand['c_entry'], cand['c_tp'], cand['c_sl']
            
            if price <= 0 or atr <= 0: continue
            
            r_dist = (1.50 * atr) / price
            net_win = r_dist - c_entry - c_tp
            net_loss = r_dist + c_entry + c_sl
            ev = (p * net_win) - ((1.0 - p) * net_loss)
            
            if ev <= 0 or net_win <= 0:
                continue # Block negative EV setups
                
            dynamic_payoff = net_win / net_loss if net_loss > 0 else 1.0
            kelly_f = p - ((1.0 - p) / dynamic_payoff)
            
            target_notional_pct = min(kelly_f * self.kelly_fraction * self.max_leverage, 2.0)
            target_risk_pct = target_notional_pct * net_loss
            
            # EV Density Metric: Expected Return per Unit of Adverse Risk
            ev_density = ev / net_loss if net_loss > 0 else 0.0
            
            valid_candidates.append({
                'ticker': cand['ticker'],
                'direction': cand['direction'],
                'ev': ev,
                'ev_density': ev_density,
                'net_win': net_win,
                'net_loss': net_loss,
                'target_notional_pct': target_notional_pct,
                'target_risk_pct': target_risk_pct
            })

        if not valid_candidates:
            return []

        # --- STAGE 2: EV Density Ranking (Highest Efficiency First) ---
        ranked_candidates = sorted(valid_candidates, key=lambda x: x['ev_density'], reverse=True)

        # --- STAGE 3: Portfolio Risk Budget Allocation ---
        remaining_budget = max(0.0, self.global_risk_cap - current_open_risk_pct)
        allocated_trades = []

        for cand in ranked_candidates:
            if remaining_budget <= 0.0005:
                # Risk budget exhausted for this tick
                break
                
            req_risk = cand['target_risk_pct']
            
            if req_risk <= remaining_budget:
                allocated_notional_pct = cand['target_notional_pct']
                allocated_risk_pct = req_risk
                remaining_budget -= req_risk
            else:
                # Pro-rate trade size to fill exact remaining budget
                scale_factor = remaining_budget / req_risk
                allocated_notional_pct = cand['target_notional_pct'] * scale_factor
                allocated_risk_pct = remaining_budget
                remaining_budget = 0.0

            cand['approved_notional_pct'] = allocated_notional_pct
            cand['approved_risk_pct'] = allocated_risk_pct
            allocated_trades.append(cand)

        return allocated_trades

# --- VERIFICATION TEST ---
if __name__ == "__main__":
    engine = BatchPortfolioRiskEngine(global_risk_cap=0.05)
    
    mock_candidates = [
        {'ticker': 'BOMEUSD', 'prob': 0.72, 'entry_price': 0.01, 'atr': 0.0005, 'c_entry': 0.0016, 'c_tp': 0.0012, 'c_sl': 0.0022, 'direction': 'SHORT'},
        {'ticker': 'ICPUSD',  'prob': 0.78, 'entry_price': 8.50, 'atr': 0.35,   'c_entry': 0.0016, 'c_tp': 0.0012, 'c_sl': 0.0022, 'direction': 'SHORT'},
        {'ticker': 'BTCUSD',  'prob': 0.68, 'entry_price': 64000,'atr': 1200.0, 'c_entry': 0.0007, 'c_tp': 0.0005, 'c_sl': 0.0010, 'direction': 'SHORT'},
    ]
    
    approved = engine.evaluate_batch(mock_candidates, current_open_risk_pct=0.015) # Assume 1.5% already active
    
    print("="*75)
    print("🧪 4-STAGE BATCH RISK ENGINE VERIFICATION OUTPUT")
    print("="*75)
    for trade in approved:
        print(f"Ticker: {trade['ticker']:<8} | Rank EV Density: {trade['ev_density']:.4f} | Approved Notional %: {trade['approved_notional_pct']*100:.2f}% | Approved Risk %: {trade['approved_risk_pct']*100:.2f}%")
    print("="*75)

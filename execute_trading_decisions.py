import argparse
import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
client = bigquery.Client(project=PROJECT_ID)

def get_latest_signals():
    query = f"""
    SELECT 
        timestamp,
        ticker,
        close,
        atr_20,
        dist_ema20_atr,
        macro_expansion_score,
        expansion_quintile,
        p_long,
        active_hurdle,
        is_eligible,
        execution_action
    FROM `{PROJECT_ID}.market_data.fct_4h_model_signals`
    WHERE timestamp = (
        SELECT MAX(timestamp) 
        FROM `{PROJECT_ID}.market_data.fct_4h_model_signals`
    )
    ORDER BY p_long DESC
    """
    return client.query(query).to_dataframe()

def dispatch_decisions(live_mode: bool = False, max_positions: int = 2):
    df_signals = get_latest_signals()
    if df_signals.empty:
        print("[!] No signals available to process.")
        return

    latest_bar = df_signals["timestamp"].iloc[0]
    regime = df_signals["expansion_quintile"].iloc[0]
    macro_score = df_signals["macro_expansion_score"].iloc[0]

    print(f"\n================= EXECUTION DISPATCHER ({'LIVE TRADING' if live_mode else 'SHADOW AUDIT'}) =================")
    print(f"Bar Timestamp    : {latest_bar}")
    print(f"Market Regime    : Q{regime} (Macro Expansion Score: {macro_score:.4f})")

    eligible = df_signals[df_signals["is_eligible"] == True].head(max_positions)

    if eligible.empty:
        print("[*] Market Veto Active: No candidates crossed active regime hurdle. Portfolio in 100% Cash.")
        return

    print(f"[*] Found {len(eligible)} qualified setup(s) for dispatch:\n")

    for rank, (_, row) in enumerate(eligible.iterrows(), 1):
        ticker = row["ticker"]
        entry_price = float(row["close"])
        atr = float(row["atr_20"])
        p_long = float(row["p_long"])
        hurdle = float(row["active_hurdle"])

        stop_loss = round(entry_price - (1.0 * atr), 4)
        take_profit = round(entry_price + (1.8 * atr), 4)
        risk_per_unit = entry_price - stop_loss
        reward_risk_ratio = (take_profit - entry_price) / max(risk_per_unit, 1e-6)

        print(f"--- [Order #{rank}] {ticker} ---")
        print(f"  Model Conviction : P(Long) = {p_long:.4f} (Hurdle: {hurdle:.2f})")
        print(f"  Entry Price      : ${entry_price:,.4f}")
        print(f"  Stop Loss (-1.0R): ${stop_loss:,.4f}")
        print(f"  Take Profit(+1.8R): ${take_profit:,.4f}")
        print(f"  Max Hold Horizon : 72 Hours (18 4H Bars)")
        print(f"  Risk/Reward Ratio: {reward_risk_ratio:.2f}")

        if live_mode:
            print(f"  >> [ACTION] DISPATCHED LIVE MARKET ORDER: BUY {ticker}")
        else:
            print(f"  >> [SHADOW] Simulated entry logged. No exchange capital committed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quant Pipeline Order Dispatcher")
    parser.add_argument("--live", action="store_true", help="Enable real exchange order routing")
    args = parser.parse_args()

    dispatch_decisions(live_mode=args.live)

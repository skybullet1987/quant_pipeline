import os
import sys
import joblib
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
PROD_MODELS_DIR = "models/prod"
INITIAL_CAPITAL = 1000.0

def load_data(total_days=270):
    print(f"--> Pulling {total_days} days of multi-table data from BigQuery...")
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*,
            COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
            COALESCE(t.tfm_slope, 0.0) AS tfm_slope,
            COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t 
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l 
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {total_days} DAY)
        ORDER BY f.timestamp ASC, f.ticker ASC
    """
    df = client.query(query).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    if "atr" not in df.columns:
        df["atr"] = df["atr_20"].fillna(df["close"] * 0.02) if "atr_20" in df.columns else df["close"] * 0.02
    if "market_breadth" not in df.columns:
        df["market_breadth"] = df["market_breadth_sma20"] if "market_breadth_sma20" in df.columns else 0.50
    if "btc_ret_4h" not in df.columns: df["btc_ret_4h"] = 0.0

    print("--> Pre-computing HMM & CatBoost Probabilities...")
    hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
    hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")
    cat_set = set(joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/cat_cols.pkl") else [])

    models_l, models_s = {}, {}
    for r in [0, 1, 2]:
        lp, sp = f"{PROD_MODELS_DIR}/regime_{r}_long_expert.cbm", f"{PROD_MODELS_DIR}/regime_{r}_short_expert.cbm"
        if os.path.exists(lp): models_l[str(r)] = CatBoostClassifier().load_model(lp)
        if os.path.exists(sp): models_s[str(r)] = CatBoostClassifier().load_model(sp)

    fb_l = models_l.get("1", next(iter(models_l.values()), None))
    fb_s = models_s.get("2", next(iter(models_s.values()), None))

    for c in hmm_feats: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0) if c in df.columns else 0.0
    probs = hmm_model.predict_proba(hmm_scaler.transform(df[hmm_feats]))[:, canonical_order]
    df["p_chop"] = probs[:, 0]
    df["regime"] = probs.argmax(axis=1).astype(str)

    df["p_long"], df["p_short"] = 0.50, 0.50
    for reg_val, group_idx in df.groupby("regime").groups.items():
        reg_str = str(reg_val)
        sub = df.loc[group_idx].copy()
        ml, ms = models_l.get(reg_str, fb_l), models_s.get(reg_str, fb_s)

        for c in ml.feature_names_:
            if c in ["hmm_regime", "regime"]: sub[c] = reg_str
            elif c in cat_set: sub[c] = sub[c].fillna("missing").astype(str)
            else: sub[c] = pd.to_numeric(sub[c], errors="coerce").fillna(0.0) if c in sub.columns else 0.0
        df.loc[group_idx, "p_long"] = ml.predict_proba(Pool(sub[ml.feature_names_], cat_features=[c for c in ml.feature_names_ if c in cat_set]))[:, 1]

        for c in ms.feature_names_:
            if c in ["hmm_regime", "regime"]: sub[c] = reg_str
            elif c in cat_set: sub[c] = sub[c].fillna("missing").astype(str)
            else: sub[c] = pd.to_numeric(sub[c], errors="coerce").fillna(0.0) if c in sub.columns else 0.0
        df.loc[group_idx, "p_short"] = ms.predict_proba(Pool(sub[ms.feature_names_], cat_features=[c for c in ms.feature_names_ if c in cat_set]))[:, 1]

    unique_bars = sorted(df["timestamp"].unique())
    keep_cols = ["ticker", "high", "low", "close", "atr", "p_long", "p_short", "p_chop", "regime", "btc_ret_4h", "market_breadth", "timestamp"]
    df_mini = df[keep_cols]
    dict_bars = [{r["ticker"]: r for r in df_mini[df_mini["timestamp"] == ts].to_dict("records")} for ts in unique_bars]
    
    return unique_bars, dict_bars

def simulate_10x_engine(unique_bars, dict_bars, cfg, friction_bps=12.0):
    equity = INITIAL_CAPITAL
    open_pos, cooldowns, trades, curve = {}, {}, [], []

    risk_pct = cfg["risk_pct"]            # e.g. 2.5% equity risk per trade
    max_slot_pct = cfg["max_slot_pct"]    # e.g. 65% max notional per slot
    max_slots = cfg["max_slots"]          # e.g. 4 slots total (2.5x gross leverage)
    tp1_atr = cfg["tp1_atr"]              # e.g. 2.4x ATR for 50% partial TP
    sl_atr = cfg["sl_atr"]                # e.g. 1.4x ATR initial stop
    trail_atr = cfg["trail_atr"]          # e.g. 1.8x ATR trailing buffer on remaining 50%
    max_hold_bars = cfg["max_hold_bars"]  # e.g. 12 bars (48 hours)

    for b_idx, b_dict in enumerate(dict_bars):
        b_ts = unique_bars[b_idx]
        closed = []

        # 1. Manage Active Positions (Partial TP + Dynamic Trailing Runner)
        for sym, pos in list(open_pos.items()):
            r = b_dict.get(sym)
            if not r: continue
            h, l, c = r["high"], r["low"], r["close"]
            atr = pos["atr"]

            # Step A: Check Partial Take-Profit (50% size exit)
            if not pos["tp1_taken"]:
                if pos["is_buy"] and h >= pos["entry_px"] + (tp1_atr * atr):
                    pos["tp1_taken"] = True
                    p_size = pos["size"] * 0.50
                    p_exit = pos["entry_px"] + (tp1_atr * atr)
                    p_gross = (p_exit - pos["entry_px"]) * p_size
                    p_fee = (p_exit * p_size + pos["entry_px"] * p_size) * (friction_bps / 10000.0 / 2.0)
                    p_net = p_gross - p_fee
                    equity += p_net
                    pos["size"] -= p_size
                    pos["sl_px"] = max(pos["sl_px"], pos["entry_px"] + (0.2 * atr)) # Lock profit
                    trades.append({"ticker": sym, "side": "LONG", "net": p_net, "type": "TP1", "win": True})

                elif not pos["is_buy"] and l <= pos["entry_px"] - (tp1_atr * atr):
                    pos["tp1_taken"] = True
                    p_size = pos["size"] * 0.50
                    p_exit = pos["entry_px"] - (tp1_atr * atr)
                    p_gross = (pos["entry_px"] - p_exit) * p_size
                    p_fee = (p_exit * p_size + pos["entry_px"] * p_size) * (friction_bps / 10000.0 / 2.0)
                    p_net = p_gross - p_fee
                    equity += p_net
                    pos["size"] -= p_size
                    pos["sl_px"] = min(pos["sl_px"], pos["entry_px"] - (0.2 * atr))
                    trades.append({"ticker": sym, "side": "SHORT", "net": p_net, "type": "TP1", "win": True})

            # Step B: Dynamic ATR Trailing Stop for the Runner
            if pos["tp1_taken"]:
                if pos["is_buy"]:
                    pos["sl_px"] = max(pos["sl_px"], h - (trail_atr * atr))
                else:
                    pos["sl_px"] = min(pos["sl_px"], l + (trail_atr * atr))

            # Step C: Check Final Stop or Time Expiration
            hit_sl, hit_time, exit_px = False, False, c
            if pos["is_buy"] and l <= pos["sl_px"]:
                hit_sl, exit_px = True, pos["sl_px"]
            elif not pos["is_buy"] and h >= pos["sl_px"]:
                hit_sl, exit_px = True, pos["sl_px"]

            if not hit_sl and (b_idx - pos["entry_b_idx"]) >= max_hold_bars:
                hit_time, exit_px = True, c

            if hit_sl or hit_time:
                rem_size = pos["size"]
                rem_gross = ((exit_px - pos["entry_px"]) if pos["is_buy"] else (pos["entry_px"] - exit_px)) * rem_size
                rem_fee = (exit_px * rem_size + pos["entry_px"] * rem_size) * (friction_bps / 10000.0 / 2.0)
                rem_net = rem_gross - rem_fee
                equity += rem_net
                trades.append({
                    "ticker": sym, "side": "LONG" if pos["is_buy"] else "SHORT",
                    "net": rem_net, "type": "SL" if hit_sl else "TIME", "win": rem_net > 0
                })
                closed.append(sym)
                cooldowns[sym] = b_ts

        for s in closed: del open_pos[s]

        # 2. Cross-Sectional Relative Conviction Gating (Top 2 Snipers Only)
        free_slots = max(0, max_slots - len(open_pos))
        long_c = sum(1 for p in open_pos.values() if p["is_buy"])
        short_c = sum(1 for p in open_pos.values() if not p["is_buy"])

        if free_slots > 0 and equity > 50.0 and b_dict:
            first_v = next(iter(b_dict.values()))
            b_ret4h, breadth = first_v["btc_ret_4h"], first_v["market_breadth"]
            is_bull_t = (b_ret4h >= 0.025 and breadth >= 0.60)

            cands = []
            for sym, r in b_dict.items():
                pl, ps, pc, px, atr = r["p_long"], r["p_short"], r["p_chop"], r["close"], r["atr"]
                if px <= 0 or atr <= 0 or cooldowns.get(sym) == b_ts or sym in open_pos: continue
                if pc >= 0.40: continue  # Skip flat chop

                # Sniper Conviction Score
                l_score = (pl - 0.58) if (0.58 <= pl <= 0.68) else -1.0
                s_score = (ps - 0.45) if (0.45 <= ps <= 0.58 and not is_bull_t) else -1.0

                if l_score > 0 and l_score >= s_score:
                    ev = (pl * (tp1_atr * atr / px)) - ((1.0 - pl) * (sl_atr * atr / px))
                    cands.append({"sym": sym, "is_buy": True, "score": l_score, "ev": ev, "px": px, "atr": atr})
                elif s_score > 0:
                    ev = (ps * (tp1_atr * atr / px)) - ((1.0 - ps) * (sl_atr * atr / px))
                    cands.append({"sym": sym, "is_buy": False, "score": s_score, "ev": ev, "px": px, "atr": atr})

            # Pick TOP 1 or 2 highest-scoring setups across all 207 assets
            ranked = sorted(cands, key=lambda x: x["score"], reverse=True)
            alloc = 0
            for cand in ranked:
                if alloc >= 2 or len(open_pos) >= max_slots: break
                is_buy = cand["is_buy"]
                if is_buy and long_c >= 3: continue
                if not is_buy and short_c >= 3: continue

                # True Geometric Compounding Sizing
                stop_dist = sl_atr * cand["atr"]
                target_notional = min(equity * max_slot_pct, (equity * risk_pct * cand["px"]) / max(1e-6, stop_dist))
                tokens = target_notional / cand["px"]

                if tokens <= 0 or target_notional < 20.0: continue

                open_pos[cand["sym"]] = {
                    "is_buy": is_buy, "entry_px": cand["px"], "entry_b_idx": b_idx,
                    "size": tokens, "atr": cand["atr"], "tp1_taken": False,
                    "sl_px": cand["px"] - stop_dist if is_buy else cand["px"] + stop_dist
                }
                if is_buy: long_c += 1
                else: short_c += 1
                alloc += 1

        curve.append(equity)

    df_t = pd.DataFrame(trades)
    e_end = curve[-1]
    tot_ret = ((e_end - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100.0
    mult = e_end / INITIAL_CAPITAL
    peak = pd.Series(curve).cummax()
    max_dd = ((pd.Series(curve) - peak) / peak).min() * 100.0
    wins = df_t[df_t["net"] > 0]["net"].sum() if not df_t.empty else 0.0
    loss = abs(df_t[df_t["net"] <= 0]["net"].sum()) if not df_t.empty else 1.0
    pf = wins / loss
    wr = df_t["win"].mean() * 100.0 if not df_t.empty else 0.0

    return tot_ret, mult, max_dd, pf, wr, len(df_t), e_end

configs = [
    {
        "name": "10x Compounding Core (2.5% Risk / 65% Slot / 4 Slots / 2.4x TP1 + Runner)",
        "risk_pct": 0.025, "max_slot_pct": 0.65, "max_slots": 4,
        "tp1_atr": 2.4, "sl_atr": 1.4, "trail_atr": 1.8, "max_hold_bars": 12
    },
    {
        "name": "High-Octane Runner (3.0% Risk / 75% Slot / 5 Slots / 2.6x TP1 + Runner)",
        "risk_pct": 0.030, "max_slot_pct": 0.75, "max_slots": 5,
        "tp1_atr": 2.6, "sl_atr": 1.4, "trail_atr": 2.0, "max_hold_bars": 14
    },
    {
        "name": "Convexity Sniper (2.2% Risk / 60% Slot / 4 Slots / 2.2x TP1 + Runner)",
        "risk_pct": 0.022, "max_slot_pct": 0.60, "max_slots": 4,
        "tp1_atr": 2.2, "sl_atr": 1.4, "trail_atr": 1.6, "max_hold_bars": 10
    }
]

unique_bars, dict_bars = load_data(270)

print("\n" + "=" * 110)
print("             10x COMPOUNDING ARCHITECTURE: CROSS-SECTIONAL SNIPER + RUNNER ENGINE             ")
print("=" * 110)

results = []
for c in configs:
    # Full 270d continuous compounding
    tot_ret, mult, dd, pf, wr, n_tr, e_end = simulate_10x_engine(unique_bars, dict_bars, c, friction_bps=12.0)
    # Friction stress test at 25 bps
    s_ret, s_mult, s_dd, s_pf, _, _, s_end = simulate_10x_engine(unique_bars, dict_bars, c, friction_bps=25.0)

    results.append({
        "Strategy Config": c["name"],
        "Multiple": f"{mult:>6.2f}x",
        "Total Return": f"{tot_ret:>+8.1f}%",
        "End Equity": f"${e_end:>9.2f}",
        "Max Drawdown": f"{dd:>6.1f}%",
        "Profit Factor": round(pf, 2),
        "Win Rate": f"{wr:>5.1f}%",
        "Trades": n_tr,
        "Stress 25bps": f"{s_mult:.2f}x (${s_end:.0f})"
    })

print(pd.DataFrame(results).to_string(index=False))
print("=" * 110)

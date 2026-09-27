import os
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
    df_m = df[keep_cols]
    dict_bars = [{r["ticker"]: r for r in df_m[df_m["timestamp"] == ts].to_dict("records")} for ts in unique_bars]
    return unique_bars, dict_bars

def simulate_pure_convexity(unique_bars, dict_bars, cfg, friction_bps=12.0):
    equity = INITIAL_CAPITAL
    open_pos, cooldowns, trades, curve = {}, {}, [], []

    tp_mult = cfg["tp_mult"]
    sl_mult = cfg["sl_mult"]
    risk_pct = cfg["risk_pct"]
    max_slot_pct = cfg["max_slot_pct"]
    max_slots = cfg["max_slots"]
    max_hold_bars = cfg["max_hold_bars"]
    ratchet_trigger = cfg["ratchet_trigger"]

    for b_idx, b_dict in enumerate(dict_bars):
        b_ts = unique_bars[b_idx]
        closed = []

        # 1. Manage Active Positions (Full Size Asymmetric Run)
        for sym, pos in list(open_pos.items()):
            r = b_dict.get(sym)
            if not r: continue
            h, l, c = r["high"], r["low"], r["close"]
            atr = pos["atr"]

            # Profit Ratchet: Move SL to +0.5x ATR once price reaches +1.8x ATR
            if pos["is_buy"]:
                if (h - pos["entry_px"]) >= (ratchet_trigger * atr):
                    pos["sl_px"] = max(pos["sl_px"], pos["entry_px"] + (0.50 * atr))
                hit_sl = (l <= pos["sl_px"])
                hit_tp = (h >= pos["tp_px"])
                exit_px = pos["sl_px"] if hit_sl else (pos["tp_px"] if hit_tp else c)
            else:
                if (pos["entry_px"] - l) >= (ratchet_trigger * atr):
                    pos["sl_px"] = min(pos["sl_px"], pos["entry_px"] - (0.50 * atr))
                hit_sl = (h >= pos["sl_px"])
                hit_tp = (l <= pos["tp_px"])
                exit_px = pos["sl_px"] if hit_sl else (pos["tp_px"] if hit_tp else c)

            hit_time = (not hit_tp and not hit_sl and (b_idx - pos["entry_b_idx"]) >= max_hold_bars)

            if hit_tp or hit_sl or hit_time:
                gross = ((exit_px - pos["entry_px"]) if pos["is_buy"] else (pos["entry_px"] - exit_px)) * pos["size"]
                fee = (pos["notional"] + (exit_px * pos["size"])) * (friction_bps / 10000.0 / 2.0)
                net = gross - fee
                equity += net
                trades.append({
                    "ticker": sym, "side": "LONG" if pos["is_buy"] else "SHORT",
                    "net": net, "type": "TP" if hit_tp else ("SL" if hit_sl else "TIME"), "win": net > 0
                })
                closed.append(sym)
                cooldowns[sym] = b_ts

        for s in closed: del open_pos[s]

        # 2. Strict Regime-Filtered Sniper Entry
        free_slots = max(0, max_slots - len(open_pos))
        long_c = sum(1 for p in open_pos.values() if p["is_buy"])
        short_c = sum(1 for p in open_pos.values() if not p["is_buy"])

        if free_slots > 0 and equity > 50.0 and b_dict:
            first_v = next(iter(b_dict.values()))
            regime = str(first_v["regime"])
            p_chop = first_v["p_chop"]

            # Macro Rule: In Bull (0), only Long. In Bear (2), only Short. In Chop (1), sit in cash.
            if p_chop < 0.35:
                cands = []
                for sym, r in b_dict.items():
                    pl, ps, px, atr = r["p_long"], r["p_short"], r["close"], r["atr"]
                    if px <= 0 or atr <= 0 or cooldowns.get(sym) == b_ts or sym in open_pos: continue

                    if regime == "0" and (0.58 <= pl <= 0.68):
                        score = pl - 0.58
                        cands.append({"sym": sym, "is_buy": True, "score": score, "px": px, "atr": atr})
                    elif regime == "2" and (0.45 <= ps <= 0.58):
                        score = ps - 0.45
                        cands.append({"sym": sym, "is_buy": False, "score": score, "px": px, "atr": atr})

                ranked = sorted(cands, key=lambda x: x["score"], reverse=True)
                alloc = 0
                for cand in ranked:
                    if alloc >= 1 or len(open_pos) >= max_slots: break
                    is_buy = cand["is_buy"]
                    if (is_buy and long_c >= max_slots) or (not is_buy and short_c >= max_slots): continue

                    stop_dist = sl_mult * cand["atr"]
                    raw_tokens = (equity * risk_pct) / max(1e-6, stop_dist)
                    target_notional = min(equity * max_slot_pct, raw_tokens * cand["px"])
                    tokens = target_notional / cand["px"]

                    if tokens <= 0 or target_notional < 20.0: continue

                    open_pos[cand["sym"]] = {
                        "is_buy": is_buy, "entry_px": cand["px"], "entry_b_idx": b_idx,
                        "size": tokens, "notional": target_notional, "atr": cand["atr"],
                        "tp_px": cand["px"] + (tp_mult * cand["atr"]) if is_buy else cand["px"] - (tp_mult * cand["atr"]),
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
        "name": "Convexity 1 (3.2x TP / 1.4x SL / Ratchet 1.8x / 2.5% Risk / 60% Slot)",
        "tp_mult": 3.2, "sl_mult": 1.4, "ratchet_trigger": 1.8,
        "risk_pct": 0.025, "max_slot_pct": 0.60, "max_slots": 4, "max_hold_bars": 12
    },
    {
        "name": "Convexity 2 (3.5x TP / 1.4x SL / Ratchet 2.0x / 3.0% Risk / 70% Slot)",
        "tp_mult": 3.5, "sl_mult": 1.4, "ratchet_trigger": 2.0,
        "risk_pct": 0.030, "max_slot_pct": 0.70, "max_slots": 4, "max_hold_bars": 14
    },
    {
        "name": "Convexity 3 (3.0x TP / 1.3x SL / Ratchet 1.6x / 2.5% Risk / 65% Slot)",
        "tp_mult": 3.0, "sl_mult": 1.3, "ratchet_trigger": 1.6,
        "risk_pct": 0.025, "max_slot_pct": 0.65, "max_slots": 4, "max_hold_bars": 10
    }
]

unique_bars, dict_bars = load_data(270)

print("\n" + "=" * 110)
print("             FAT-TAIL CONVEXITY ENGINE: TRUE MULTI-X COMPOUNDING EVALUATION             ")
print("=" * 110)

results = []
for c in configs:
    tot_ret, mult, dd, pf, wr, n_tr, e_end = simulate_pure_convexity(unique_bars, dict_bars, c, friction_bps=12.0)
    s_ret, s_mult, s_dd, s_pf, _, _, s_end = simulate_pure_convexity(unique_bars, dict_bars, c, friction_bps=25.0)

    results.append({
        "Configuration": c["name"],
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

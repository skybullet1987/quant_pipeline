import sys
import optuna
import numpy as np
import pandas as pd
from tactical_regime import TacticalRegimeEngine
from optimizer_cache import load_and_cache_dataset
from optimizer_sim import simulate_policy_fast

optuna.logging.set_verbosity(optuna.logging.WARNING)

def run_pipeline(trials=150, total_days=270, oos_days=90):
    train_bars, train_dict, oos_bars, oos_dict = load_and_cache_dataset(total_days, oos_days)
    tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)
    records = []

    def objective(trial):
        params = {
            "sl_atr_mult": trial.suggest_float("sl_atr_mult", 1.20, 1.60, step=0.10),
            "tp_atr_mult": trial.suggest_float("tp_atr_mult", 2.50, 4.20, step=0.10),
            "risk_budget_pct": trial.suggest_float("risk_budget_pct", 0.010, 0.018, step=0.002),
            "max_slot_equity_pct": trial.suggest_float("max_slot_equity_pct", 0.25, 0.45, step=0.05),
            "max_longs": trial.suggest_int("max_longs", 2, 3),
            "max_shorts": trial.suggest_int("max_shorts", 2, 3),
            "max_net_imbalance": trial.suggest_int("max_net_imbalance", 1, 2),
            "max_hold_bars": trial.suggest_int("max_hold_bars", 8, 18),
            "long_hurdle_boost": trial.suggest_float("long_hurdle_boost", 0.02, 0.14, step=0.02),
            "short_hurdle_boost": trial.suggest_float("short_hurdle_boost", -0.02, 0.04, step=0.01),
            "chop_filter_threshold": trial.suggest_float("chop_filter_threshold", 0.35, 0.50, step=0.05),
            "max_trades_per_bar": 1,
            "btc_bull_veto_pct": trial.suggest_float("btc_bull_veto_pct", 0.015, 0.030, step=0.005)
        }
        score, ret, cagr, dd, pf, wr, n_tr, e_end, t_pnl = simulate_policy_fast(params, train_bars, train_dict, tactical_engine, 12.0)
        records.append({"trial": trial.number, "score": score, "is_return": ret, "is_cagr": cagr, "is_max_dd": dd, "is_pf": pf, **params})
        return score

    print(f"--> Optimizing {trials} Trials in-memory...")
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=trials)

    df_top = pd.DataFrame(records).sort_values(by="score", ascending=False).head(10)
    print("\n" + "=" * 90 + "\nSTAGE 2-5: OOS, STABILITY & FRICTION VALIDATION\n" + "=" * 90)

    val_res = []
    for _, row in df_top.iterrows():
        p = {k: row[k] for k in ["tp_atr_mult", "sl_atr_mult", "risk_budget_pct", "max_slot_equity_pct", "max_longs", "max_shorts", "max_net_imbalance", "max_hold_bars", "long_hurdle_boost", "short_hurdle_boost", "chop_filter_threshold", "max_trades_per_bar", "btc_bull_veto_pct"]}
        
        _, oos_ret, oos_cagr, oos_dd, oos_pf, oos_wr, oos_tr, oos_eq, _ = simulate_policy_fast(p, oos_bars, oos_dict, tactical_engine, 12.0)
        
        # Stability Test
        stab_scores = []
        for tp_j in [p["tp_atr_mult"] * 0.9, p["tp_atr_mult"] * 1.1]:
            for sl_j in [p["sl_atr_mult"] * 0.9, p["sl_atr_mult"] * 1.1]:
                jp = dict(p, tp_atr_mult=round(tp_j, 2), sl_atr_mult=round(sl_j, 2))
                _, _, _, _, j_pf, _, _, _, _ = simulate_policy_fast(jp, train_bars, train_dict, tactical_engine, 12.0)
                stab_scores.append(j_pf)
        stab_ratio = min(1.0, np.mean(stab_scores) / max(1e-4, row["is_pf"]))

        # Friction Ladder
        f_pfs = [simulate_policy_fast(p, oos_bars, oos_dict, tactical_engine, f)[4] for f in [12.0, 20.0, 35.0, 50.0]]
        champ_score = ((oos_cagr / max(1.0, abs(oos_dd))) * 0.35) + (oos_pf * 15.0) + (np.mean(stab_scores) * 10.0) + (10.0 if (f_pfs[0] >= 1.05 and f_pfs[1] >= 1.05) else -30.0)

        val_res.append({
            "trial": int(row["trial"]), "champ_score": round(champ_score, 2),
            "is_ret": f"{row['is_return']:>+6.1f}%", "oos_ret": f"{oos_ret:>+6.1f}%",
            "oos_dd": f"{oos_dd:>5.1f}%", "oos_pf": round(oos_pf, 2), "stab": f"{stab_ratio*100:.0f}%",
            "pf_20bps": round(f_pfs[1], 2), "tp": p["tp_atr_mult"], "sl": p["sl_atr_mult"],
            "risk": f"{p['risk_budget_pct']*100:.1f}%", "side": f"L:{p['max_longs']}/S:{p['max_shorts']}", "hold": p["max_hold_bars"]
        })

    df_champ = pd.DataFrame(val_res).sort_values(by="champ_score", ascending=False)
    df_champ.to_csv("champion_policy_rankings.csv", index=False)
    print(df_champ.to_string(index=False))
    print("=" * 90)
    print(f"\n[WINNING CHAMPION POLICY]: Trial #{df_champ.iloc[0]['trial']}")

if __name__ == "__main__":
    t = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    run_pipeline(trials=t)

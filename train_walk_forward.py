import gc
import json
import warnings
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

warnings.filterwarnings('ignore')

PARQUET_FILE = "feature_matrix_symmetric.parquet"
PARAMS_FILE = "production_models/optimal_params_symmetric.json"
OUTPUT_SIGNALS_FILE = "raw_executed_signals.parquet"
DEX_ROUNDTRIP_FEE_BPS = 0.0004

def select_best_calibrator(raw_probs, y_true):
    if len(np.unique(y_true)) < 2:
        return LogisticRegression().fit(np.zeros((len(y_true),1)), y_true), "Platt"
    y_bin = (y_true == 1).astype(int)
    
    platt = LogisticRegression(C=1.0, solver='lbfgs')
    platt.fit(raw_probs.reshape(-1, 1), y_bin)
    platt_probs = platt.predict_proba(raw_probs.reshape(-1, 1))[:, 1]
    platt_brier = brier_score_loss(y_bin, platt_probs)
    
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(raw_probs, y_bin)
    iso_probs = iso.predict(raw_probs)
    iso_brier = brier_score_loss(y_bin, iso_probs)
    
    return (iso, "Isotonic") if iso_brier < platt_brier else (platt, "Platt")

def predict_calibrated(calibrator, cal_type, raw_probs):
    if "Platt" in cal_type:
        return calibrator.predict_proba(raw_probs.reshape(-1, 1))[:, 1]
    return calibrator.predict(raw_probs)

def optimize_threshold(y_calib, cal_probs, vol_calib, fee_bps):
    best_thresh = 1.0  
    max_ev = 0.0
    for t in np.linspace(0.05, 0.95, 91):
        mask = cal_probs >= t
        if mask.sum() < 5: continue
        pnl = np.where(y_calib[mask] == 1, 1.5 * vol_calib[mask], -1.5 * vol_calib[mask]) - fee_bps
        total_ev = pnl.sum()
        if total_ev > max_ev:
            max_ev, best_thresh = total_ev, t
    return best_thresh

def bootstrap_sharpe(daily_pnl, n_bootstraps=1000):
    pnl_array = daily_pnl.values
    if len(pnl_array) < 3 or np.std(pnl_array) == 0: return 0.0, 0.0, 0.0
    sharpes = []
    for _ in range(n_bootstraps):
        samp = np.random.choice(pnl_array, size=len(pnl_array), replace=True)
        std = np.std(samp)
        if std > 0: sharpes.append((np.mean(samp) / std) * np.sqrt(365))
    if not sharpes: return 0.0, 0.0, 0.0
    return np.mean(sharpes), np.percentile(sharpes, 2.5), np.percentile(sharpes, 97.5)

def run_diagnostic_evaluator():
    print(f"Loading {PARAMS_FILE}...")
    with open(PARAMS_FILE, "r") as f:
        opt_params = json.load(f)
    
    long_params = opt_params['long_model']
    short_params = opt_params['short_model']
    long_params.update({'verbose': 0, 'random_seed': 42})
    short_params.update({'verbose': 0, 'random_seed': 42})

    print(f"Loading Symmetric Matrix ({PARQUET_FILE})...")
    df = pd.read_parquet(PARQUET_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    for col in [c for c in df.columns if c.endswith('_y')]:
        base_col = col[:-2]
        df[base_col] = df[col]
        df = df.drop(columns=[f"{base_col}_x", col], errors='ignore')

    df['ticker'] = df['ticker'].astype(str)
    df['hour_of_day'] = df['timestamp'].dt.hour.astype(str)
    df['day_of_week'] = df['timestamp'].dt.dayofweek.astype(str)
    
    exclude_cols = ['timestamp', 'ticker', 'hour_of_day', 'day_of_week', 'target_tbm', 'tbm_realized_return']
    base_features = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]
    cat_features = ['ticker', 'hour_of_day', 'day_of_week']
    all_features = base_features + cat_features
    
    start_date = df['timestamp'].min()
    end_date = df['timestamp'].max()
    
    print(f"Executing Walk-Forward with Optimized Params on {len(base_features)} Features...")
    
    train_months, calib_months, test_months = 6, 1, 1
    current_start = start_date
    fold = 1
    all_executed_signals = []
    
    while current_start + pd.DateOffset(months=train_months + calib_months + test_months) <= end_date:
        train_end = current_start + pd.DateOffset(months=train_months)
        calib_end = train_end + pd.DateOffset(months=calib_months)
        test_end = calib_end + pd.DateOffset(months=test_months)
        
        train_mask = (df['timestamp'] >= current_start) & (df['timestamp'] + pd.Timedelta(minutes=30) < train_end)
        calib_mask = (df['timestamp'] >= train_end + pd.Timedelta(minutes=30)) & (df['timestamp'] + pd.Timedelta(minutes=30) < calib_end)
        test_mask = (df['timestamp'] >= calib_end + pd.Timedelta(minutes=30)) & (df['timestamp'] <= test_end)
        
        train_df, calib_df, test_df = df[train_mask].copy(), df[calib_mask].copy(), df[test_mask].copy()
        
        if len(train_df) < 1000 or len(calib_df) < 100 or len(test_df) < 100:
            current_start += pd.DateOffset(months=1)
            continue
            
        print(f"\n================ FOLD {fold} | Test Month: {calib_end.strftime('%Y-%m')} ================")
        
        y_train_long = (train_df['target_tbm'] == 1).astype(int)
        y_calib_long = (calib_df['target_tbm'] == 1).astype(int)
        
        y_train_short = (train_df['target_tbm'] == -1).astype(int)
        y_calib_short = (calib_df['target_tbm'] == -1).astype(int)
        
        pool_tr_long = Pool(train_df[all_features], label=y_train_long, cat_features=cat_features)
        pool_ca_long = Pool(calib_df[all_features], label=y_calib_long, cat_features=cat_features)
        
        pool_tr_short = Pool(train_df[all_features], label=y_train_short, cat_features=cat_features)
        pool_ca_short = Pool(calib_df[all_features], label=y_calib_short, cat_features=cat_features)
        
        pool_te = Pool(test_df[all_features], cat_features=cat_features)
        
        lp = long_params.copy()
        lp['scale_pos_weight'] = (len(y_train_long) - sum(y_train_long)) / (sum(y_train_long) + 1e-8)
        model_long = CatBoostClassifier(**lp)
        model_long.fit(pool_tr_long, eval_set=pool_ca_long, early_stopping_rounds=30, use_best_model=True)
        
        sp = short_params.copy()
        sp['scale_pos_weight'] = (len(y_train_short) - sum(y_train_short)) / (sum(y_train_short) + 1e-8)
        model_short = CatBoostClassifier(**sp)
        model_short.fit(pool_tr_short, eval_set=pool_ca_short, early_stopping_rounds=30, use_best_model=True)
        
        cal_long_raw = model_long.predict_proba(pool_ca_long)[:, 1]
        calibrator_long, type_l = select_best_calibrator(cal_long_raw, y_calib_long)
        cal_long_prob = predict_calibrated(calibrator_long, type_l, cal_long_raw)
        
        cal_short_raw = model_short.predict_proba(pool_ca_short)[:, 1]
        calibrator_short, type_s = select_best_calibrator(cal_short_raw, y_calib_short)
        cal_short_prob = predict_calibrated(calibrator_short, type_s, cal_short_raw)
        
        vol_calib = calib_df['realized_vol_30m'].values
        thresh_long = optimize_threshold(y_calib_long, cal_long_prob, vol_calib, fee_bps=DEX_ROUNDTRIP_FEE_BPS)
        thresh_short = optimize_threshold(y_calib_short, cal_short_prob, vol_calib, fee_bps=DEX_ROUNDTRIP_FEE_BPS)
        
        test_df['prob_long'] = predict_calibrated(calibrator_long, type_l, model_long.predict_proba(pool_te)[:, 1])
        test_df['prob_short'] = predict_calibrated(calibrator_short, type_s, model_short.predict_proba(pool_te)[:, 1])
        
        sig_long = test_df['prob_long'] >= thresh_long
        sig_short = test_df['prob_short'] >= thresh_short
        
        conflict = sig_long & sig_short
        sig_long.loc[conflict] = False
        sig_short.loc[conflict] = False
        
        traded_indices = np.where(sig_long | sig_short)[0]
        test_df_traded = test_df.iloc[traded_indices].copy()
        
        if len(test_df_traded) > 0:
            returns = []
            for idx, row in test_df_traded.iterrows():
                is_l = sig_long.loc[idx]
                tbm, vol = row['target_tbm'], row['realized_vol_30m']
                ret_vert = row['tbm_realized_return']
                
                if is_l:
                    if tbm == 1: ret = (1.5 * vol) - DEX_ROUNDTRIP_FEE_BPS
                    elif tbm == -1: ret = (-1.5 * vol) - DEX_ROUNDTRIP_FEE_BPS
                    else: ret = ret_vert - DEX_ROUNDTRIP_FEE_BPS
                else:
                    if tbm == -1: ret = (1.5 * vol) - DEX_ROUNDTRIP_FEE_BPS
                    elif tbm == 1: ret = (-1.5 * vol) - DEX_ROUNDTRIP_FEE_BPS
                    else: ret = -ret_vert - DEX_ROUNDTRIP_FEE_BPS
                returns.append(ret)
                
                all_executed_signals.append({
                    'timestamp': row['timestamp'],
                    'ticker': row['ticker'],
                    'direction': 'LONG' if is_l else 'SHORT',
                    'calibrated_prob': row['prob_long'] if is_l else row['prob_short'],
                    'target_hit': tbm,
                    'realized_return': ret
                })
                
            test_df_traded['pnl'] = returns
            test_df_traded['date'] = test_df_traded['timestamp'].dt.date
            
            long_count, short_count = sum(sig_long), sum(sig_short)
            daily_pnl = test_df_traded.groupby('date')['pnl'].sum()
            all_dates = pd.date_range(test_df['timestamp'].min().date(), test_df['timestamp'].max().date())
            daily_pnl = daily_pnl.reindex(all_dates.date, fill_value=0.0)
            
            mean_sharpe, ci_low, ci_high = bootstrap_sharpe(daily_pnl)
            ev_bps = np.mean(returns) * 10000
        else:
            long_count, short_count, ev_bps, mean_sharpe, ci_low, ci_high = 0, 0, 0, 0, 0, 0
            
        print(f"Executed Trades: {len(test_df_traded)} (Longs: {long_count} | Shorts: {short_count})")
        print(f"Expected Value: {ev_bps:.2f} bps | Daily Sharpe: {mean_sharpe:.2f}")
        
        current_start += pd.DateOffset(months=1)
        fold += 1
        
        del train_df, calib_df, test_df, model_long, model_short
        gc.collect()

    print("\n========================================================")
    print("                EXPORTING SIGNAL ANATOMY                ")
    print("========================================================")
    signals_df = pd.DataFrame(all_executed_signals)
    signals_df.to_parquet(OUTPUT_SIGNALS_FILE, index=False)
    print(f"[SUCCESS] Exported {len(signals_df):,} raw executed signals to {OUTPUT_SIGNALS_FILE}")

if __name__ == "__main__":
    run_diagnostic_evaluator()

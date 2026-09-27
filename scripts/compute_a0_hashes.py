import sys
import json
import hashlib
import numpy as np
from pathlib import Path

PIPELINE_ROOT = Path("/home/skybullet1987/quant_pipeline")
sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine

def main():
    print("Loading data lake...")
    loader = InstitutionalCompoundingEngine()
    _, _, cached_data = loader.load_and_preprocess_data()

    # 1. Data fingerprint
    data_hasher = hashlib.sha256()
    for k in sorted(cached_data.keys()):
        val = cached_data[k]
        if isinstance(val, np.ndarray):
            data_hasher.update(k.encode("utf-8"))
            data_hasher.update(val.tobytes())
        elif isinstance(val, list):
            data_hasher.update(k.encode("utf-8"))
            data_hasher.update(json.dumps(val).encode("utf-8"))
    data_fingerprint = data_hasher.hexdigest()
    print(f"data_fingerprint:    {data_fingerprint}")

    # 2. Config hash
    config_dict = {
        "engine": "InstitutionalCompoundingEngine",
        "fixed_leverage": 3.0,
        "turnover_lambda": 0.85,
        "two_tranche_enabled": False,
        "pyramid_ratio": 0.0,
        "mode_layer": "EXP103_CAUSAL_A0",
        "initial_capital": 10000.0,
        "target_universe_size": 16,
    }
    config_hash = hashlib.sha256(json.dumps(config_dict, sort_keys=True).encode("utf-8")).hexdigest()
    print(f"config_hash:         {config_hash}")

    # Run A0
    print("Running A0 baseline...")
    engine = InstitutionalCompoundingEngine(
        fixed_leverage=3.0,
        turnover_lambda=0.85,
        two_tranche_enabled=False,
        pyramid_ratio=0.0
    )
    res = engine.run(cached_data)

    # 3. Equity curve hash
    eq_arr = res["equity_curve"]
    equity_curve_hash = hashlib.sha256(eq_arr.tobytes()).hexdigest()
    print(f"equity_curve_hash:   {equity_curve_hash}")

    # 4. Fill ledger hash
    trade_log = res["trade_log"]
    trade_log_str = json.dumps(trade_log, sort_keys=True, default=str)
    fill_ledger_hash = hashlib.sha256(trade_log_str.encode("utf-8")).hexdigest()
    print(f"fill_ledger_hash:    {fill_ledger_hash}")

    # 5. Event stream hash
    audit_log = res["audit_log"]
    audit_log_str = json.dumps(audit_log, sort_keys=True, default=str)
    event_stream_hash = hashlib.sha256(audit_log_str.encode("utf-8")).hexdigest()
    print(f"event_stream_hash:   {event_stream_hash}")

    # Save to json file
    manifest = {
        "data_fingerprint": data_fingerprint,
        "config_hash": config_hash,
        "equity_curve_hash": equity_curve_hash,
        "fill_ledger_hash": fill_ledger_hash,
        "event_stream_hash": event_stream_hash,
        "ending_equity": float(res["ending_equity"]),
        "equity_multiple": float(res["ending_equity"] / 10000.0),
        "cagr_pct": float(res["net_cagr"]),
        "sharpe_ratio": float(res["sharpe"]),
        "sortino_ratio": float(res["sortino"]),
        "calmar_ratio": float(res["calmar"]),
        "max_drawdown_pct": float(res["max_drawdown"]),
        "total_trades": int(res["total_trades"]),
        "total_turnover_nav": float(res["total_turnover_nav"]),
        "avg_turnover_per_bar": float(res["avg_turnover_per_bar"]),
        "total_fees_usdc": float(res["cost_breakdown"]["maker_fees_usd"] + res["cost_breakdown"]["taker_fees_usd"]),
        "maker_fees_usdc": float(res["cost_breakdown"]["maker_fees_usd"]),
        "taker_fees_usdc": float(res["cost_breakdown"]["taker_fees_usd"]),
        "base_slippage_usdc": float(res["cost_breakdown"]["base_slippage_usd"]),
        "market_impact_usdc": float(res["cost_breakdown"]["market_impact_usd"]),
        "funding_pnl_usdc": float(res["cost_breakdown"]["funding_pnl_usd"]),
        "total_traded_volume_usd": float(res["cost_breakdown"]["total_traded_volume_usd"]),
        "max_gross_exposure": float(res["max_post_pyramid_gross"]),
        "max_position_weight": float(res["max_post_pyramid_weight"]),
        "total_bars_audited": int(res["invariants_audited"]),
    }

    out_file = PIPELINE_ROOT / "data" / "a0_golden_manifest.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote full manifest to {out_file}")

if __name__ == "__main__":
    main()

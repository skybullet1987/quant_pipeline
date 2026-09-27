import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   EXPERIMENT 2: FUNDING CARRY AUTOPSY & ADVERSE SELECTION BENCHMARK")
print("=" * 96)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

BARS_PER_YEAR = 24 * 365
FEE_RATE = 0.00015  # 1.5 bps ALO maker
REBAL_CLOCK = 8     # 8-hour carry rebalance cadence (low turnover)
K_ASSETS = 6

# Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h"),
    (pl.col("funding_rate") > 0).cast(pl.Float64).rolling_mean(window_size=168).over("symbol").fill_null(0.5).alias("funding_persistence_7d")
])

valid_counts = df.filter(pl.col("dollar_volume_1h") > 25_000).group_by("group_id").len()
active_grps = sorted(valid_counts.filter(pl.col("len") >= 35)["group_id"].to_list())

MODES = [
    "1. Naive Carry (Top/Bottom 6)",
    "2. Persistent Carry (7d > 85%)",
    "3. Trend-Filtered Carry",
    "4. Beta-Neutral Trend-Filtered"
]

navs = [10_000.0] * 4
turnovers = [0.0] * 4
prev_w = [{}, {}, {}, {}]
returns_hist = [[], [], [], []]
funding_collected = [[], [], [], []]
price_pnls = [[], [], [], []]
fees_paid = [[], [], [], []]

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

for idx, grp in enumerate(active_grps[:-1]):
    cur_panel = df.filter(pl.col("group_id") == grp)
    valid_panel = cur_panel.filter(
        (pl.col("dollar_volume_1h") > 25_000) &
        pl.col("funding_rate").is_not_null() &
        pl.col("vol_yang_zhang").is_not_null()
    )
    if valid_panel.height < 35:
        continue

    returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
    funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
    beta_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["beta_btc"].to_list()))

    is_rebal = (idx % REBAL_CLOCK == 0)

    for m in range(4):
        if is_rebal:
            if m == 0:
                # Mode 1: Naive highest / lowest funding
                sorted_df = valid_panel.sort("funding_rate", descending=True)
                shorts = sorted_df.head(K_ASSETS)["symbol"].to_list()
                longs = sorted_df.tail(K_ASSETS)["symbol"].to_list()

            elif m == 1:
                # Mode 2: Persistent funding filter
                pers_df = valid_panel.filter(pl.col("funding_persistence_7d") >= 0.80)
                if pers_df.height >= (K_ASSETS * 2):
                    sorted_df = pers_df.sort("funding_rate", descending=True)
                    shorts = sorted_df.head(K_ASSETS)["symbol"].to_list()
                    longs = sorted_df.tail(K_ASSETS)["symbol"].to_list()
                else:
                    sorted_df = valid_panel.sort("funding_rate", descending=True)
                    shorts = sorted_df.head(K_ASSETS)["symbol"].to_list()
                    longs = sorted_df.tail(K_ASSETS)["symbol"].to_list()

            elif m == 2:
                # Mode 3: Trend-Filtered Carry (avoid shorting positive momentum tokens)
                # Short candidates must have ret_24h <= 0 or below median momentum
                short_pool = valid_panel.filter(pl.col("ret_24h") <= 0.01).sort("funding_rate", descending=True)
                long_pool = valid_panel.filter(pl.col("ret_24h") >= -0.01).sort("funding_rate", descending=False)
                shorts = short_pool.head(K_ASSETS)["symbol"].to_list()
                longs = long_pool.head(K_ASSETS)["symbol"].to_list()

            elif m == 3:
                # Mode 4: Beta-Neutral Trend-Filtered
                short_pool = valid_panel.filter(pl.col("ret_24h") <= 0.01).sort("funding_rate", descending=True)
                long_pool = valid_panel.filter(pl.col("ret_24h") >= -0.01).sort("funding_rate", descending=False)
                shorts = short_pool.head(K_ASSETS)["symbol"].to_list()
                longs = long_pool.head(K_ASSETS)["symbol"].to_list()

            raw_w = {}
            for s in longs: raw_w[s] = 1.0 / len(longs)
            for s in shorts: raw_w[s] = -1.0 / len(shorts)

            if m == 3 and len(longs) > 0 and len(shorts) > 0:
                # Adjust short weights so portfolio beta to BTC is zero
                l_beta = np.mean([safe_val(beta_map, s, 1.0) for s in longs])
                s_beta = np.mean([safe_val(beta_map, s, 1.0) for s in shorts])
                if s_beta > 0.1:
                    beta_ratio = l_beta / s_beta
                    for s in shorts: raw_w[s] *= beta_ratio

            # Run at 1.5x gross exposure
            scale = 1.50 / sum(abs(w) for w in raw_w.values()) if raw_w else 1.0
            raw_target = {s: w * scale for s, w in raw_w.items()}
        else:
            raw_target = prev_w[m]

        all_syms = set(prev_w[m].keys()).union(raw_target.keys())
        to = sum(abs(raw_target.get(s, 0.0) - prev_w[m].get(s, 0.0)) for s in all_syms)
        turnovers[m] += to
        cost = to * FEE_RATE

        # Hourly Funding Cash Flow:
        # Long position: receives negative funding, pays positive funding (-w * f)
        # Short position: receives positive funding, pays negative funding (-w * f since w < 0)
        fund_flow = sum(-raw_target.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in raw_target)
        p_pnl = sum(raw_target.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in raw_target)

        net_pnl = p_pnl + fund_flow - cost
        navs[m] *= (1.0 + net_pnl)
        returns_hist[m].append(net_pnl)
        funding_collected[m].append(fund_flow)
        price_pnls[m].append(p_pnl)
        fees_paid[m].append(cost)
        prev_w[m] = raw_target

print("\n" + "=" * 96)
print("             EXPERIMENT 2 RESULTS: NET CARRY AUTOPSY (1.5x GROSS)")
print("=" * 96)
headers = ["Metric", MODES[0], MODES[1], MODES[2], MODES[3]]
print(f"{headers[0]:<28} | {headers[1]:<14} | {headers[2]:<14} | {headers[3]:<14} | {headers[4]:<15}")
print("-" * 96)

def calc_metrics(nav, rets, to, funds, prices, fees):
    r = np.array(rets)
    total_ret = (nav / 10_000.0) - 1.0
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    ann_mult = BARS_PER_YEAR / len(r)
    return {
        "mult": nav / 10_000.0,
        "cagr": cagr,
        "sharpe": sharpe,
        "vol": vol,
        "mdd": mdd,
        "to_ann": to * ann_mult,
        "fund_ann": sum(funds) * ann_mult,
        "price_ann": sum(prices) * ann_mult,
        "fees_ann": sum(fees) * ann_mult
    }

metrics = [calc_metrics(navs[i], returns_hist[i], turnovers[i], funding_collected[i], price_pnls[i], fees_paid[i]) for i in range(4)]

print(f"{'Terminal Multiple':<28} | {metrics[0]['mult']:>13.2f}x | {metrics[1]['mult']:>13.2f}x | {metrics[2]['mult']:>13.2f}x | {metrics[3]['mult']:>14.2f}x")
print(f"{'Net Annualized CAGR':<28} | {metrics[0]['cagr']*100:>+12.1f}% | {metrics[1]['cagr']*100:>+12.1f}% | {metrics[2]['cagr']*100:>+12.1f}% | {metrics[3]['cagr']*100:>+13.1f}%")
print(f"{'Net Sharpe Ratio':<28} | {metrics[0]['sharpe']:>14.2f} | {metrics[1]['sharpe']:>14.2f} | {metrics[2]['sharpe']:>14.2f} | {metrics[3]['sharpe']:>15.2f}")
print(f"{'Max Drawdown':<28} | {metrics[0]['mdd']*100:>13.1f}% | {metrics[1]['mdd']*100:>13.1f}% | {metrics[2]['mdd']*100:>13.1f}% | {metrics[3]['mdd']*100:>14.1f}%")
print(f"{'Realized Volatility':<28} | {metrics[0]['vol']*100:>13.1f}% | {metrics[1]['vol']*100:>13.1f}% | {metrics[2]['vol']*100:>13.1f}% | {metrics[3]['vol']*100:>14.1f}%")
print(f"{'Annualized Turnover':<28} | {metrics[0]['to_ann']:>13.0f}x | {metrics[1]['to_ann']:>13.0f}x | {metrics[2]['to_ann']:>13.0f}x | {metrics[3]['to_ann']:>14.0f}x")
print("-" * 96)
print(f"{'Ann. Funding Harvest':<28} | {metrics[0]['fund_ann']*100:>+12.1f}% | {metrics[1]['fund_ann']*100:>+12.1f}% | {metrics[2]['fund_ann']*100:>+12.1f}% | {metrics[3]['fund_ann']*100:>+13.1f}%")
print(f"{'Ann. Price Drift PnL':<28} | {metrics[0]['price_ann']*100:>+12.1f}% | {metrics[1]['price_ann']*100:>+12.1f}% | {metrics[2]['price_ann']*100:>+12.1f}% | {metrics[3]['price_ann']*100:>+13.1f}%")
print(f"{'Ann. Trading Fees Paid':<28} | {metrics[0]['fees_ann']*100:>12.1f}% | {metrics[1]['fees_ann']*100:>12.1f}% | {metrics[2]['fees_ann']*100:>12.1f}% | {metrics[3]['fees_ann']*100:>13.1f}%")
print("=" * 96)

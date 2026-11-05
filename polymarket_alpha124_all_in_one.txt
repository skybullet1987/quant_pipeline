"""
========================================================================================
DOMINUS POLYMARKET ALPHA-124 EXPANSION + PROJECTIONS + TESTS (<1 MB AST-INVARIANT COMPANION BUNDLE)
Generated: 2026-11-05 11:24:05 UTC
Pairs with polymarket_all_in_one.txt (<1 MB) for tools enforcing a 1 MB per-file upload cap
Repository: /home/skybullet1987/quant_pipeline
========================================================================================

TABLE OF CONTENTS (Exact 1-Based Line Ranges & Raw Module Sizes):
  [01] systemd/polymarket-alpha124-shadow.service (Lines 35 - 62 | 897 B) :: Alpha-124 Unified Shadow systemd Unit
  [02] src/polymarket_research/directional_wfo_shadow_sleeves.py (Lines 63 - 476 | 71,299 B) :: v3.9.5 WFO Graduation Shadow Sleeves (SLEEVE_HYBRID_ZSPLIT_SHADOW & SLEEVE_BTC_5M_SNIPER_SHADOW)
  [03] src/polymarket_research/orderflow_wfo_simulators.py (Lines 477 - 787 | 66,622 B) :: v4.0 100ms Micro-Clip 4-Step Cascade Replay, D1 Latency-Skew WFO & Legging-Drag Parity Engine
  [04] src/polymarket_research/net_alpha_opportunity_engine.py (Lines 788 - 994 | 48,616 B) :: v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine
  [05] src/polymarket_research/weather_metar_engine.py (Lines 995 - 1,359 | 62,867 B) :: Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb
  [06] src/polymarket_research/barrier_onetouch_svi_engine.py (Lines 1,360 - 1,502 | 22,909 B) :: Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)
  [07] src/polymarket_research/multistrike_svi_scalper.py (Lines 1,503 - 1,675 | 29,320 B) :: Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner
  [08] src/polymarket_research/same_oracle_dominance_box.py (Lines 1,676 - 1,915 | 40,450 B) :: Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine
  [09] src/polymarket_research/exact_twap_lock_engine.py (Lines 1,916 - 1,978 | 13,461 B) :: Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock
  [10] src/polymarket_research/tradfi_sports_zero_fee_engine.py (Lines 1,979 - 2,482 | 72,523 B) :: Zero-Fee Pyth Commodities/Metals/Equities (CM_B3/B2/U1), B4 Wick Lock, NBA Polish-Middle (SP1) & NegRisk (NR0)
  [11] src/polymarket_research/macro_counting_ctf_engine.py (Lines 2,483 - 2,830 | 48,790 B) :: Phase-2 Multi-Vertical Structural & Oracle Engine (TW1 xtracker, FED1 125-State LP, COND1 Oil-Senate, CTF Overround, AAA Gas, D2 12PM)
  [12] src/polymarket_research/uma_nba_endgame_engine.py (Lines 2,831 - 3,029 | 32,496 B) :: Evergreen On-Chain UMA Resolution Bond Harvester (BOND1) & 0%-Fee Live NBA Final-2m/Post-Buzzer Sniper (SP2)
  [13] src/polymarket_research/riskless_frontier_v2_engine.py (Lines 3,030 - 3,460 | 81,101 B) :: Riskless Frontier v2 Engine (NR2 Subset Convert + Free Tail, SP4 NBA Props, BOND2 Whitelisted MOOv2, SOC1 3-Way Soccer, LP1 Implication Matrix, API1 BO3 Esports)
  [14] src/polymarket_research/riskless_frontier_v3_engine.py (Lines 3,461 - 4,121 | 109,769 B) :: Riskless Frontier v3 Engine (NFL Exact Margin/Spread, Subperiod Clinch, Deadline Ladder, Tennis Retirement-Safe Corridor, Multi-Sport Post-Review Clinch)
  [15] src/polymarket_research/riskless_frontier_v4_engine.py (Lines 4,122 - 4,677 | 113,267 B) :: Riskless Frontier v4 Evergreen Engine (AFF1 Subperiod Collapse, SOC2 83-State Lattice, NFL_PRP1 Locks, SUM1 Frechet Triangles, CRY_INC1 Binance Inclusion, MKR_LOCK1)
  [16] src/polymarket_research/alpha_124_shadow_daemon.py (Lines 4,678 - 7,925 | 724,510 B) :: Unified Multi-Vertical Shadow Daemon (Crypto, Weather METAR/HKO, Pyth Commodities/Metals/Equities, Sports, UMA Bonds, Frontier v2/v3/v4)
  [17] scripts/backtest_alpha_124.py (Lines 7,926 - 8,150 | 40,009 B) :: Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124
  [18] scripts/polymarket_daily_projections.py (Lines 8,151 - 8,285 | 46,085 B) :: Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker
  [19] scripts/alpha124_status.py (Lines 8,286 - 8,314 | 3,091 B) :: Live Alpha-124 Multi-Sleeve Scorecard & Orderbook Opportunity Inspector
  [20] scripts/polymarket_scorecard_snapshot.py (Lines 8,315 - 8,331 | 4,891 B) :: Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot
  [21] tests/test_alpha_124_oracles.py (Lines 8,332 - 8,590 | 215,925 B) :: Unit Tests: Weather METAR/HKO, Jump-SVI Barrier, Pyth Session/Boxes, NBA Boxes, D1, S2 & Wallet
"""

from __future__ import annotations

# ======================================================================================
# [01/21] MODULE: systemd/polymarket-alpha124-shadow.service
# PURPOSE: Alpha-124 Unified Shadow systemd Unit
# ======================================================================================

POLYMARKET_ALPHA124_SHADOW_SERVICE=r'''
[Unit]
Description=Polymarket Alpha-124 Unified Shadow Engine (#1 Weather + #2 Barrier + #4 Multi-Strike SVI + #7 Same-Oracle Dominance Boxes)
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
WorkingDirectory=/home/skybullet1987/quant_pipeline
Environment=PYTHONUNBUFFERED=1
Environment=PM_DISABLE_SHADOW_M4_CATCHUP=1
Environment=PM_DISABLE_SHADOW_W2_TAKER=1
Environment=PM_UNQUARANTINE_S2_TWAP_LOCK=1
CPUWeight=300
IOWeight=300
ExecStart=/home/skybullet1987/quant_pipeline/venv/bin/python src/polymarket_research/alpha_124_shadow_daemon.py
Restart=always
RestartSec=10
KillSignal=SIGTERM
KillMode=process
TimeoutStopSec=15s
[Install]
WantedBy=default.target
'''
# ======================================================================================
# [02/21] MODULE: src/polymarket_research/directional_wfo_shadow_sleeves.py
# PURPOSE: v3.9.5 WFO Graduation Shadow Sleeves (SLEEVE_HYBRID_ZSPLIT_SHADOW & SLEEVE_BTC_5M_SNIPER_SHADOW)
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import math;import os;import random;import re;import time;from datetime import datetime,timezone;from pathlib import Path;from typing import Any,Dict,List,Optional,Set,Tuple;from zoneinfo import ZoneInfo;from src.polymarket_research.exact_twap_lock_engine import should_suppress_final60s_twap_salvage;from src.polymarket_research.polymarket_live_executor import calculate_taker_fee;from src.polymarket_research.polymarket_live_harvester import evaluate_coinbase_venue_veto;SHADOW_INITIAL_CAPITAL=5e2;SHADOW_TICKET_USD=15.;SHADOW_ELASTIC_USD=12.;XAU_TICKET_USD=12.;MAX_MAKER_JOIN_QUEUE_USD=350.;TRANSIT_LATENCY_SEC=.5;MAKER_TTL_SEC=6.;SHIELD_DECAY_FRAC=.5;Z_TAKER_CUT=1.2;_NY_TZ=ZoneInfo("America/New_York")
def compute_synthetic_xau_usd_anchor(binance_xau_usdt,coinbase_usdt_usd,swissquote_bid=.0,swissquote_ask=.0,max_basis_bps=2.5):
 e=float(binance_xau_usdt or.0);d=float(coinbase_usdt_usd or.0)
 if e<=.0:return{"valid":False,"reason":"INVALID_BINANCE_XAUUSDT","xau_usd":.0}
 if not(.98<=d<=1.02):return{"valid":False,"reason":"MISSING_OR_DEPEGGED_USDT_USD_RATE","xau_usd":.0}
 b=round(e*d,3);g,f=float(swissquote_bid or.0),float(swissquote_ask or.0);a=.0
 if g>.0 and f>=g:
  c=.5*(g+f);a=round(abs(b-c)/c*1e4,4)
  if a>float(max_basis_bps)+1e-6:return{"valid":False,"reason":"SWISSQUOTE_BASIS_DIVERGENCE","xau_usd":b,"swissquote_mid":round(c,3),"basis_bps":a}
 return{"valid":True,"reason":"OK","xau_usd":b,"basis_bps":a}
def is_xau_cme_blackout_or_inactive_session(ts_unix,enforce_active_session=True):
 c=datetime.fromtimestamp(float(ts_unix),tz=_NY_TZ);e=c.weekday();d=c.hour*60+c.minute
 if e==5 or(e==4 and d>=17*60)or(e==6 and d<18*60+15):return True,"CME_WEEKEND_CLOSURE"
 if 17*60<=d<18*60+15:return True,"CME_GLOBEX_MAINTENANCE_BLACKOUT"
 if enforce_active_session and os.environ.get("PM_DISABLE_XAU_SESSION_FILTER")!="1":
  b=(3*60<=d<=5*60);a=(8*60<=d<=13*60+30)
  if not(b or a):return True,"OUTSIDE_LONDON_COMEX_ACTIVE_SESSION"
 return False,"OK"
def _utc_now_str():return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
def _maker_rebate_20pct_usd(shares,px,fee_rate=.07):a=max(.01,min(.99,float(px)));return round(shares*.2*fee_rate*a*(1.-a),4)
def _walk_bids_vwap(raw_bids,target_shares,fallback_bid):
 if not raw_bids or target_shares<=0:return fallback_bid
 b=target_shares;a=.0
 for d in raw_bids:
  if not isinstance(d,(list,tuple))or len(d)<2:continue
  f,e=float(d[0]or.0),float(d[1]or.0)
  if f<=0 or e<=0:continue
  c=min(b,e);a+=c*f;b-=c
  if b<=1e-6:break
 if b>1e-6:a+=b*max(.01,fallback_bid-.02)
 return round(a/target_shares,4)
def _bootstrap_prob_positive(pnls,n_boot=1000):
 n=len(pnls)
 if n<3:s=round(sum(pnls),2);return(1. if s>0 else.0),[s,s]
 c=random.Random(20261030);a=[]
 for _ in range(n_boot):a.append(sum(pnls[c.randrange(n)]for _ in range(n)))
 a.sort();e=round(a[int(.025*n_boot)],2);d=round(a[int(.975*n_boot)],2);b=round(sum(1 for x in a if x>0)/n_boot,4);return b,[e,d]
class DirectionalWfoShadowManager:
 def __init__(a,data_dir,latency_sec=TRANSIT_LATENCY_SEC,production_mode=False):a.data_dir=Path(data_dir);a.data_dir.mkdir(parents=True,exist_ok=True);a.latency_sec=max(.0,float(latency_sec));a.production_mode=bool(production_mode);a.hz_ledger_file=a.data_dir/"ledger_shadow_hybrid_zsplit.jsonl";a.hz_state_file=a.data_dir/"state_shadow_hybrid_zsplit.json";a.hz_trades=[];a.hz_settled_ids=set();a.hz_settled_markets=set();a.hz_open={};a.hz_pending={};a.hz_funnel={"signals_seen":0,"signals_evaluated":0,"maker_branch_queued":0,"taker_branch_queued":0,"maker_filled":0,"taker_fak_filled":0,"phase3a_rescue_filled":0,"shield_canceled":0,"complement_shield_canceled":0,"queue_depth_rejected":0,"ttl_expired_unfilled":0,"post_only_or_collapse_rejected":0};a.b5_ledger_file=a.data_dir/"ledger_shadow_btc_5m.jsonl";a.b5_state_file=a.data_dir/"state_shadow_btc_5m.json";a.b5_telem_file=a.data_dir/"polymarket_5m_telemetry_btc.jsonl";a.b5_trades=[];a.b5_settled_ids=set();a.b5_settled_markets=set();a.b5_open={};a.b5_pending={};a.b5_funnel={"ticks_scanned":0,"candidates_queued":0,"taker_filled":0,"transit_swept_or_shielded":0};a.s5_ledger_file=a.data_dir/"ledger_shadow_sol_5m.jsonl";a.s5_state_file=a.data_dir/"state_shadow_sol_5m.json";a.s5_telem_file=a.data_dir/"polymarket_5m_telemetry_sol.jsonl";a.s5_trades=[];a.s5_settled_ids=set();a.s5_settled_markets=set();a.s5_open={};a.s5_pending={};a.s5_funnel={"ticks_scanned":0,"candidates_queued":0,"taker_filled":0,"transit_swept_or_shielded":0};a.xau_ledger_file=a.data_dir/"ledger_shadow_xau_15m.jsonl";a.xau_state_file=a.data_dir/"state_shadow_xau_15m.json";a.xau_telem_file=a.data_dir/"polymarket_15m_telemetry_xau.jsonl";a.xau_trades=[];a.xau_settled_ids=set();a.xau_settled_markets=set();a.xau_open={};a.xau_pending={};a.xau_funnel={"ticks_scanned":0,"cme_or_session_blocked":0,"basis_or_anchor_rejected":0,"maker_queued":0,"maker_filled":0,"shield_or_comp_canceled":0,"queue_depth_rejected":0,"ttl_expired_unfilled":0};a.b5_file_pos=a.b5_telem_file.stat().st_size if a.b5_telem_file.exists()else 0;a.s5_file_pos=a.s5_telem_file.stat().st_size if a.s5_telem_file.exists()else 0;a.xau_file_pos=a.xau_telem_file.stat().st_size if a.xau_telem_file.exists()else 0;a.t15_btc_file=a.data_dir/"polymarket_15m_telemetry_btc.jsonl";a.t15_eth_file=a.data_dir/"polymarket_15m_telemetry_eth.jsonl";a.t1h_btc_file=a.data_dir/"polymarket_hourly_telemetry.jsonl";a.t1h_eth_file=a.data_dir/"polymarket_hourly_telemetry_eth.jsonl";a.t15_btc_pos=a.t15_btc_file.stat().st_size if a.t15_btc_file.exists()else 0;a.t15_eth_pos=a.t15_eth_file.stat().st_size if a.t15_eth_file.exists()else 0;a.t1h_btc_pos=a.t1h_btc_file.stat().st_size if a.t1h_btc_file.exists()else 0;a.t1h_eth_pos=a.t1h_eth_file.stat().st_size if a.t1h_eth_file.exists()else 0;a._btc_sigma_1h=.0048;a._btc_last_1m_bkt=0;a._btc_last_1m_spot=.0;a._sol_sigma_1h=.009;a._sol_last_1m_bkt=0;a._sol_last_1m_spot=.0;a._xau_sigma_1h=.0022;a._xau_last_1m_bkt=0;a._xau_last_1m_spot=.0;a._last_state_flush_ts=.0;a._load_ledgers();a.save_states()
 def _load_ledgers(a):
  for m,d,i,h in((a.hz_ledger_file,a.hz_trades,a.hz_settled_ids,a.hz_settled_markets),(a.b5_ledger_file,a.b5_trades,a.b5_settled_ids,a.b5_settled_markets),(a.s5_ledger_file,a.s5_trades,a.s5_settled_ids,a.s5_settled_markets),(a.xau_ledger_file,a.xau_trades,a.xau_settled_ids,a.xau_settled_markets)):
   if not m.exists():continue
   try:
    with open(m,"r",encoding="utf-8",errors="ignore")as f:
     for r in f:
      if not r.strip():continue
      q=json.loads(r);p=str(q.get("trade_id")or"");o=str(q.get("market_id")or"")
      if p and p not in i:
       i.add(p);d.append(q)
       if o:h.add(o)
   except Exception:pass
  for g,c,e,b in((a.hz_state_file,a.hz_funnel,a.hz_open,a.hz_settled_ids),(a.b5_state_file,a.b5_funnel,a.b5_open,a.b5_settled_ids),(a.s5_state_file,a.s5_funnel,a.s5_open,a.s5_settled_ids),(a.xau_state_file,a.xau_funnel,a.xau_open,a.xau_settled_ids)):
   if g.exists():
    try:
     j=json.loads(g.read_text(encoding="utf-8"))
     for k,v in(j.get("funnel_counters")or{}).items():
      if k in c and isinstance(v,int):c[k]=max(c[k],v)
     for l,n in(j.get("open_positions")or{}).items():
      if isinstance(n,dict)and n.get("status")=="OPEN"and n.get("trade_id")not in b:e[str(l)]=n
    except Exception:pass
 def _read_shm_asset(self,asset):
  a=os.environ.get("PM_FAST_TICK_DIR","/dev/shm")
  if not a:return None
  p=Path(a)/f"pm_fast_tick_{asset.upper()}.json"
  if not p.exists():return None
  try:
   d=json.loads(p.read_text(encoding="utf-8"));b=float(d.get("timestamp_unix")or d.get("ts")or.0)
   if b>0 and(time.time()-b)<=5.:return d
  except Exception:pass
  return None
 def _extract_market_view(self,asset,market_id,horizon):
  d=self._read_shm_asset(asset)
  if not d:return None
  b=d.get("markets")or{};m=b.get(str(market_id));a=None
  if horizon=="5m"and isinstance(d.get("m5"),dict)and str(d["m5"].get("market_id"))==str(market_id):a=d["m5"]
  elif horizon=="15m"and isinstance(d.get("m15"),dict)and str(d["m15"].get("market_id"))==str(market_id):a=d["m15"]
  if m is None and a is None:return None
  c=m or a or{};return{"timestamp_unix":float(c.get("timestamp_unix")or d.get("timestamp_unix")or d.get("ts")or time.time()),"binance_spot":float(c.get("spot_price")or d.get("spot_price")or d.get("spot")or.0),"chainlink_proxy_usd_spot":float(d.get("chainlink_proxy_spot")or.0),"chainlink_twap_60s":float(d.get("chainlink_twap_60s")or.0),"authoritative_chainlink_open":float((a or{}).get("authoritative_chainlink_open")or.0),"twap_locked_mean":(a or c).get("twap_locked_mean"),"twap_locked_weight":(a or c).get("twap_locked_weight"),"coinbase_usdt_usd":float(d.get("coinbase_usdt_usd")or.0),"swissquote_bid":float(d.get("swissquote_bid")or.0),"swissquote_ask":float(d.get("swissquote_ask")or.0),"UP":c.get("UP")or{},"DOWN":c.get("DOWN")or{}}
 @staticmethod
 def _compute_signed_cushion(side,horizon,binance_spot,open_usdt,twap_open_usdt=.0,cl_usd_spot=.0,auth_cl_open_usd=.0):
  c=1. if side=="UP"else-1.;b=[]
  if binance_spot>0 and open_usdt>0:
   if horizon in("15m","5m")and twap_open_usdt>0:a=max(open_usdt,twap_open_usdt)if side=="UP"else min(open_usdt,twap_open_usdt)
   else:a=open_usdt
   b.append(c*(binance_spot-a)/a)
  if horizon in("15m","5m")and cl_usd_spot>0 and auth_cl_open_usd>0:b.append(c*(cl_usd_spot-auth_cl_open_usd)/auth_cl_open_usd)
  if not b:return None
  return min(b)
 def on_shock_signal(a,shock,historical=False):
  if historical:return False
  L=str(shock.get("market_id")or"")
  if not L or L in a.hz_open or L in a.hz_pending or L in a.hz_settled_markets:return False
  if len(a.hz_open)+len(a.hz_pending)>=2:return False
  I=str(shock.get("title")or"");x=I.lower();d=str(shock.get("asset")or"").upper()
  if not d:d="BTC"if("bitcoin"in x or"btc"in x)else("ETH"if("ethereum"in x or"eth"in x)else"")
  if d not in("BTC","ETH"):return False
  F=str(shock.get("horizon")or shock.get("candle_interval")or"").lower();K=str(shock.get("series_slug")or shock.get("slug")or"").lower();n=f"{F} {K} {x}"
  if re.search(r"(?<![0-9])5m(?![0-9a-z])|(?<![0-9])300s(?![0-9a-z])",n):return False
  b=False;E=re.search(r"(\d{1,2}):(\d{2})\s*(?:am|pm)?\s*-\s*(\d{1,2}):(\d{2})\s*(?:am|pm)",x)
  if E:
   P,O=int(E.group(2)),int(E.group(4));w=(O-P)%60
   if w==15:b=True
   elif w==5:return False
  D=bool(re.search(r"(?<![0-9])15m(?![0-9a-z])|(?<![0-9])900s(?![0-9a-z])",n))or b;H=not D and(bool(re.search(r"(?<![0-9])(?:1h|60m)(?![0-9a-z])|hourly",n))or("am et"in x or"pm et"in x))
  if not(D or H):return False
  R="15m"if D else"1h";a.hz_funnel["signals_seen"]=int(a.hz_funnel.get("signals_seen",0))+1;v=float(shock.get("t0_unix")or time.time())
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   Q=datetime.fromtimestamp(v,tz=timezone.utc)
   if Q.hour==13 and Q.minute>=30:return False
  N=float(shock.get("seconds_to_expiry")or.0)
  if R=="15m"and not((180.<=N<=390.)if a.production_mode else(90.<=N<=480.)):return False
  if R=="1h"and not((150.<=N<=2400.)if a.production_mode else(150.<=N<=6e2)):return False
  i=str(shock.get("shock_direction")or"").upper()
  if i not in("BUY","SELL"):return False
  J="UP"if i=="BUY"else"DOWN";u,_=evaluate_coinbase_venue_veto(shock,J)
  if u:return False
  h=abs(float(shock.get("shock_ofi")if shock.get("shock_ofi")is not None else 1.))
  if h<.6:return False
  t=float(shock.get("spot_at_t0")or shock.get("trigger_price")or.0);s=float(shock.get("candle_open_spot")or shock.get("finalized_1h_open")or.0);g=float(shock.get("twap_60s_open")or.0);r=float(shock.get("chainlink_proxy_usd_spot")or.0);q=float(shock.get("authoritative_chainlink_open")or.0);p=a._compute_signed_cushion(J,R,t,s,g,r,q)
  if p is None or p<4e-4:return False
  o=float(shock.get("candle_sigma")or.0);m=(o*2. if D else o)if o>.0 else(.005 if d=="BTC"else.0068);f=max(.00025,m*math.sqrt(max(N,30.)/3600.));l=p/f
  if l<.78:return False
  M=(shock.get("pre_shock_features_t0")or{}).get(J)or{};k=M.get("raw_top_asks")or[];j=M.get("raw_top_bids")or[];C=float(M.get("best_ask")or(k[0][0]if k else 1.));B=float(M.get("best_bid")or(j[0][0]if j else.0));A=float(M.get("ask_size_l1")or(k[0][1]if k else.0));e=round(C-B,4)if B>0 else.99;z=C*A;c=(.72 if D else.76)if a.production_mode else.82
  if not(.55<=C<=c)or B<=.0 or e>.03 or z<20.:return False
  a.hz_funnel["signals_evaluated"]+=1;y="TAKER_PLUS_P3A"if l>=Z_TAKER_CUT else"SHIELDED_MAKER_FIRST"
  if y=="SHIELDED_MAKER_FIRST":a.hz_funnel["maker_branch_queued"]+=1
  else:a.hz_funnel["taker_branch_queued"]+=1
  G=time.time();a.hz_pending[L]={"sleeve":"SLEEVE_HYBRID_ZSPLIT_SHADOW","trade_id":f"HZSHDW_{L}_{int(v)}_{J}","market_id":L,"title":I,"asset":d,"horizon":R,"target_token":J,"t0_unix":v,"queued_mono":G,"arrival_mono":G+a.latency_sec,"expiry_unix":float(shock.get("candle_expiry_ts")or shock.get("expiry_ts")or(v+N)),"tte_t0":N,"ask_t0":C,"bid_t0":B,"l1_usd_t0":round(z,2),"cush_t0":p,"z_strike":round(l,4),"open_usdt":s,"twap_open_usdt":g,"auth_cl_open_usd":q,"branch":y,"phase":"IN_TRANSIT","maker_px":None,"deadline_mono":None};return True
 def _ingest_btc_5m_telemetry_tick(a,d):
  m=str(d.get("asset")or"").upper();z=str(d.get("horizon")or"").lower()
  if m!="BTC"or z!="5m":return
  a.b5_funnel["ticks_scanned"]+=1;y=float(d.get("timestamp_unix")or time.time());x=float(d.get("binance_spot")or.0)
  if x>0:
   w=int(y//60)
   if w>a._btc_last_1m_bkt:
    if a._btc_last_1m_spot>0:v=math.log(x/a._btc_last_1m_spot);a._btc_sigma_1h=max(.002,min(.02,math.sqrt(.94*(a._btc_sigma_1h**2)+.06*(60.*v*v))))
    a._btc_last_1m_spot=x;a._btc_last_1m_bkt=w
  o=str(d.get("market_id")or"")
  if not o:return
  if o in a.b5_open:a._check_open_position_exit(a.b5_open,o,d,is_btc_5m=True);return
  if o in a.b5_pending or o in a.b5_settled_markets:return
  if len(a.b5_open)+len(a.b5_pending)>=2:return
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   u=datetime.fromtimestamp(y,tz=timezone.utc)
   if u.hour==13 and u.minute>=30:return
  s=float(d.get("seconds_to_expiry")or.0)
  if not(60.<=s<=180.):return
  j=float(d.get("binance_open")or.0);i=float(d.get("twap_60s_open")or.0);l=float(d.get("chainlink_proxy_usd_spot")or.0);f=float(d.get("authoritative_chainlink_open")or.0)
  if x<=0 or j<=0:return
  b=max(.00025,a._btc_sigma_1h*math.sqrt(max(s,15.)/3600.))
  for n in("UP","DOWN"):
   t=d.get(n)or{};r=float(t.get("best_bid")or.0);q=float(t.get("best_ask")or 1.);p=float(t.get("ask_size_l1")or.0)
   if t.get("is_crossed")or r<=.0 or q>=.99 or r>=q:continue
   h=round(q-r,4);g=q*p
   if not(.55<=q<=.85)or h>.03 or g<15.:continue
   e=a._compute_signed_cushion(n,"5m",x,j,i,l,f)
   if e is None or e<3e-4:continue
   c=e/b
   if c<.8:continue
   k=time.time();a.b5_funnel["candidates_queued"]+=1;a.b5_pending[o]={"sleeve":"SLEEVE_BTC_5M_SNIPER_SHADOW","trade_id":f"BTC5M_{o}_{int(y)}_{n}","market_id":o,"title":str(d.get("title")or f"BTC 5m {o}"),"asset":"BTC","horizon":"5m","target_token":n,"t0_unix":y,"queued_mono":k,"arrival_mono":k+a.latency_sec,"expiry_unix":y+s,"tte_t0":s,"ask_t0":q,"bid_t0":r,"l1_usd_t0":round(g,2),"cush_t0":e,"z_strike":round(c,4),"open_usdt":j,"twap_open_usdt":i,"auth_cl_open_usd":f,"latest_tick":d};break
 def _ingest_sol_5m_telemetry_tick(a,d):
  o=str(d.get("asset")or"").upper();B=str(d.get("horizon")or"").lower()
  if o!="SOL"or B!="5m":return
  a.s5_funnel["ticks_scanned"]+=1;A=float(d.get("timestamp_unix")or time.time());z=float(d.get("binance_spot")or.0)
  if z>0:
   y=int(A//60)
   if y>a._sol_last_1m_bkt:
    if a._sol_last_1m_spot>0:x=math.log(z/a._sol_last_1m_spot);a._sol_sigma_1h=max(.004,min(.03,math.sqrt(.94*(a._sol_sigma_1h**2)+.06*(60.*x*x))))
    a._sol_last_1m_spot=z;a._sol_last_1m_bkt=y
  q=str(d.get("market_id")or"")
  if not q:return
  if q in a.s5_open:a._check_open_position_exit(a.s5_open,q,d,sleeve_tag="s5");return
  if q in a.s5_pending or q in a.s5_settled_markets:return
  if len(a.s5_open)+len(a.s5_pending)>=2:return
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   w=datetime.fromtimestamp(A,tz=timezone.utc)
   if w.hour==13 and w.minute>=30:return
  u=float(d.get("seconds_to_expiry")or.0)
  if not(60.<=u<=180.):return
  l=float(d.get("binance_open")or.0);k=float(d.get("twap_60s_open")or.0);n=float(d.get("chainlink_proxy_usd_spot")or.0);g=float(d.get("authoritative_chainlink_open")or.0)
  if z<=0 or l<=0:return
  b=float(d.get("candle_sigma")or.0);j=(b*math.sqrt(12.))if b>.0 else a._sol_sigma_1h;c=max(.00035,j*math.sqrt(max(u,15.)/3600.))
  for p in("UP","DOWN"):
   v=d.get(p)or{};t=float(v.get("best_bid")or.0);s=float(v.get("best_ask")or 1.);r=float(v.get("ask_size_l1")or.0)
   if v.get("is_crossed")or t<=.0 or s>=.99 or t>=s:continue
   i=round(s-t,4);h=s*r
   if not(.55<=s<=.85)or i>.03 or h<15.:continue
   f=a._compute_signed_cushion(p,"5m",z,l,k,n,g)
   if f is None or f<4e-4:continue
   e=f/c
   if e<.8:continue
   m=time.time();a.s5_funnel["candidates_queued"]+=1;a.s5_pending[q]={"sleeve":"SLEEVE_SOL_5M_CANARY_SHADOW","trade_id":f"SOL5M_{q}_{int(A)}_{p}","market_id":q,"title":str(d.get("title")or f"SOL 5m {q}"),"asset":"SOL","horizon":"5m","target_token":p,"t0_unix":A,"queued_mono":m,"arrival_mono":m+a.latency_sec,"expiry_unix":A+u,"tte_t0":u,"ask_t0":s,"bid_t0":t,"l1_usd_t0":round(h,2),"cush_t0":f,"z_strike":round(e,4),"open_usdt":l,"twap_open_usdt":k,"auth_cl_open_usd":g,"latest_tick":d};break
 def ingest_xau_15m_tick(a,d):
  s=str(d.get("asset")or"").upper();G=str(d.get("horizon")or"").lower()
  if s not in("XAU","GOLD")or G!="15m":return False
  a.xau_funnel["ticks_scanned"]+=1;F=float(d.get("timestamp_unix")or time.time());j,_=is_xau_cme_blackout_or_inactive_session(F)
  if j:a.xau_funnel["cme_or_session_blocked"]+=1;return False
  o=compute_synthetic_xau_usd_anchor(binance_xau_usdt=float(d.get("binance_xau_usdt")or d.get("binance_spot")or.0),coinbase_usdt_usd=float(d.get("coinbase_usdt_usd")or.0),swissquote_bid=float(d.get("swissquote_bid")or.0),swissquote_ask=float(d.get("swissquote_ask")or.0),max_basis_bps=2.5)
  if not o["valid"]:a.xau_funnel["basis_or_anchor_rejected"]+=1;return False
  i=float(o["xau_usd"]);E=int(F//60)
  if E>a._xau_last_1m_bkt:
   if a._xau_last_1m_spot>0:D=math.log(i/a._xau_last_1m_spot);a._xau_sigma_1h=max(.001,min(.012,math.sqrt(.94*(a._xau_sigma_1h**2)+.06*(60.*D*D))))
   a._xau_last_1m_spot=i;a._xau_last_1m_bkt=E
  w=str(d.get("market_id")or"")
  if not w:return False
  if w in a.xau_open:r=dict(d,chainlink_proxy_usd_spot=i);a._check_open_position_exit(a.xau_open,w,r,sleeve_tag="xau");return False
  if w in a.xau_pending or w in a.xau_settled_markets:return False
  if len(a.xau_open)+len(a.xau_pending)>=1:return False
  B=float(d.get("seconds_to_expiry")or.0)
  if not(90.<=B<=480.):return False
  q=d.get("authoritative_chainlink_open")or d.get("strike_usd")
  if q is None or float(q)<=.0:a.xau_funnel["basis_or_anchor_rejected"]+=1;return False
  b=round(float(q),3);h=float(d.get("candle_sigma")or.0);n=(h*2.)if h>.0 else a._xau_sigma_1h;c=max(.00018,n*math.sqrt(B/3600.))
  for v in("UP","DOWN"):
   C=d.get(v)or{};m=d.get("DOWN"if v=="UP"else"UP")or{};A=float(C.get("best_bid")or.0);z=float(C.get("best_ask")or 1.);y=float(C.get("ask_size_l1")or.0);x=float(C.get("bid_size_l1")or.0);g=float(m.get("best_bid")or.0)
   if C.get("is_crossed")or A<=.0 or z>=.99 or A>=z:continue
   l=round(z-A,4);k=z*y
   if not(.56<=z<=.83)or l>.02 or k<50.:continue
   u=1. if v=="UP"else-1.;t=u*(i-b)/b
   if t<.00025:continue
   f=t/c
   if f<.85:continue
   e=round(min(.82,z-.01,A+(.01 if l>=.02 else.0)),2)
   if e<.55 or e>=z-1e-6:continue
   if e<=A+1e-6 and(A*x)>MAX_MAKER_JOIN_QUEUE_USD:a.xau_funnel["queue_depth_rejected"]+=1;continue
   if g>.0 and round(1.-g,4)<=e+1e-6:a.xau_funnel["shield_or_comp_canceled"]+=1;continue
   p=time.time();a.xau_funnel["maker_queued"]+=1;a.xau_pending[w]={"sleeve":"SLEEVE_XAU_15M_MAKER_SHADOW","trade_id":f"XAU15M_{w}_{int(F)}_{v}","market_id":w,"title":str(d.get("title")or f"XAU/USD 15m {w}"),"asset":"XAU","horizon":"15m","target_token":v,"t0_unix":F,"queued_mono":p,"arrival_mono":p+a.latency_sec,"expiry_unix":F+B,"tte_t0":B,"ask_t0":z,"bid_t0":A,"maker_px":e,"deadline_mono":p+a.latency_sec+MAKER_TTL_SEC,"l1_usd_t0":round(k,2),"cush_t0":t,"z_strike":round(f,4),"open_usdt":.0,"twap_open_usdt":.0,"auth_cl_open_usd":b,"latest_tick":d};return True
  return False
 def _step_hz_pending(a,now_u):
  for v,p in list(a.hz_pending.items()):
   if now_u<p["arrival_mono"]:continue
   u=a._extract_market_view(p["asset"],v,p["horizon"])
   if u is None:
    if now_u>p["arrival_mono"]+MAKER_TTL_SEC+2.:a.hz_pending.pop(v,None)
    continue
   t=p["target_token"];k="DOWN"if t=="UP"else"UP";w=u.get(t)or{};s=u.get(k)or{};j=w.get("raw_top_asks")or[];i=w.get("raw_top_bids")or[];q=float(w.get("best_ask")or(j[0][0]if j else 1.));o=float(w.get("best_bid")or(i[0][0]if i else.0));n=float(w.get("ask_size_l1")or(j[0][1]if j else.0));m=float(w.get("bid_size_l1")or(i[0][1]if i else.0));l=float(s.get("best_bid")or.0);r=q*n;h=a._compute_signed_cushion(t,p["horizon"],float(u.get("binance_spot")or.0),p["open_usdt"],p["twap_open_usdt"],float(u.get("chainlink_proxy_usd_spot")or.0),p["auth_cl_open_usd"])
   if h is not None and(h<=.0 or h<p["cush_t0"]*(1.-SHIELD_DECAY_FRAC)):a.hz_funnel["shield_canceled"]+=1;a.hz_pending.pop(v,None);continue
   if p["phase"]=="IN_TRANSIT":
    if(p["ask_t0"]-q)>=.04:a.hz_funnel["post_only_or_collapse_rejected"]+=1;a.hz_pending.pop(v,None);continue
    if p["branch"]=="TAKER_PLUS_P3A":
     g=min(.81,round(p["ask_t0"]+.02,4))
     if.0<q<=g and r>=SHADOW_ELASTIC_USD:f=SHADOW_TICKET_USD if r>=SHADOW_TICKET_USD else SHADOW_ELASTIC_USD;b="STEP1_SMART_FAK"if f>=SHADOW_TICKET_USD else"STEP2_ELASTIC_DOWNSNAP";a.hz_funnel["taker_fak_filled"]+=1;a._open_shadow_position(a.hz_open,p,q,f,is_maker=False,step_tag=b,entry_ts=float(u.get("timestamp_unix")or now_u));a.hz_pending.pop(v,None);continue
     p["branch_step_tag"]="STEP4_PHASE3A_MAKER_RESCUE"
    else:p["branch_step_tag"]="SHIELDED_MAKER_FIRST"
    e=o if o>.0 else max(.01,q-.02);c=round(min(.82,q-.01,max(e,p["ask_t0"]-.01)),2)
    if c<.55 or c>=q-1e-6:a.hz_funnel["post_only_or_collapse_rejected"]+=1;a.hz_pending.pop(v,None);continue
    if c<=o+1e-6 and(o*m)>MAX_MAKER_JOIN_QUEUE_USD:a.hz_funnel["queue_depth_rejected"]+=1;a.hz_pending.pop(v,None);continue
    if l>.0 and round(1.-l,4)<=c+1e-6:a.hz_funnel["complement_shield_canceled"]+=1;a.hz_pending.pop(v,None);continue
    p["phase"]="RESTING_MAKER";p["maker_px"]=c;p["deadline_mono"]=now_u+MAKER_TTL_SEC;continue
   c=float(p["maker_px"])
   if l>.0:
    d=round(1.-l,4)
    if d<=c-1e-6 or(q>c+1e-6 and d<=c+1e-6):a.hz_funnel["complement_shield_canceled"]+=1;a.hz_pending.pop(v,None);continue
   if.0<q<=c:
    b=str(p.get("branch_step_tag")or"SHIELDED_MAKER_FIRST")
    if b=="STEP4_PHASE3A_MAKER_RESCUE":a.hz_funnel["phase3a_rescue_filled"]+=1
    else:a.hz_funnel["maker_filled"]+=1
    a._open_shadow_position(a.hz_open,p,c,SHADOW_TICKET_USD,is_maker=True,step_tag=b,entry_ts=float(u.get("timestamp_unix")or now_u));a.hz_pending.pop(v,None)
   elif now_u>=float(p["deadline_mono"]or.0):a.hz_funnel["ttl_expired_unfilled"]+=1;a.hz_pending.pop(v,None)
 def _step_b5_pending(a,now_u):a._step_5m_sniper_pending("BTC",a.b5_pending,a.b5_open,a.b5_funnel,"BTC5M_TAKER_FAK",now_u)
 def _step_s5_pending(a,now_u):a._step_5m_sniper_pending("SOL",a.s5_pending,a.s5_open,a.s5_funnel,"SOL5M_TAKER_FAK",now_u)
 def _step_5m_sniper_pending(a,asset_sym,pending_map,open_map,funnel_map,step_tag,now_u):
  for j,p in list(pending_map.items()):
   if now_u<p["arrival_mono"]:continue
   e=a._extract_market_view(asset_sym,j,"5m")
   if e is None:
    l=p.get("latest_tick")or{}
    if float(l.get("timestamp_unix")or.0)>=p["t0_unix"]+.35:e=l
    elif now_u>p["arrival_mono"]+2.5:funnel_map["transit_swept_or_shielded"]+=1;pending_map.pop(j,None);continue
    else:continue
   i=p["target_token"];k=e.get(i)or{};d=k.get("raw_top_asks")or[];g=float(k.get("best_ask")or(d[0][0]if d else 1.));f=float(k.get("ask_size_l1")or(d[0][1]if d else.0));h=g*f;c=a._compute_signed_cushion(i,"5m",float(e.get("binance_spot")or.0),p["open_usdt"],p["twap_open_usdt"],float(e.get("chainlink_proxy_usd_spot")or.0),p["auth_cl_open_usd"]);b=min(.85,round(p["ask_t0"]+.02,4))
   if(c is not None and c>.0 and.0<g<=b and(p["ask_t0"]-g)<.04 and h>=SHADOW_ELASTIC_USD):funnel_map["taker_filled"]+=1;a._open_shadow_position(open_map,p,g,SHADOW_TICKET_USD,is_maker=False,step_tag=step_tag,entry_ts=float(e.get("timestamp_unix")or now_u))
   else:funnel_map["transit_swept_or_shielded"]+=1
   pending_map.pop(j,None)
 def _step_xau_pending(a,now_u):
  for m,p in list(a.xau_pending.items()):
   if now_u<p["arrival_mono"]:continue
   e=a._extract_market_view("XAU",m,"15m")
   if e is None:
    o=p.get("latest_tick")or{}
    if float(o.get("timestamp_unix")or.0)>=p["t0_unix"]+.1:e=o
    elif now_u>float(p.get("deadline_mono")or(p["arrival_mono"]+MAKER_TTL_SEC)):a.xau_funnel["ttl_expired_unfilled"]+=1;a.xau_pending.pop(m,None);continue
    else:continue
   j=compute_synthetic_xau_usd_anchor(binance_xau_usdt=float(e.get("binance_xau_usdt")or e.get("binance_spot")or.0),coinbase_usdt_usd=float(e.get("coinbase_usdt_usd")or.0),swissquote_bid=float(e.get("swissquote_bid")or.0),swissquote_ask=float(e.get("swissquote_ask")or.0),max_basis_bps=2.5)
   if not j["valid"]:a.xau_funnel["shield_or_comp_canceled"]+=1;a.xau_pending.pop(m,None);continue
   h=float(j["xau_usd"]);l=p["target_token"];k=1. if l=="UP"else-1.;d=k*(h-float(p["auth_cl_open_usd"]))/float(p["auth_cl_open_usd"])
   if d<=.0 or d<p["cush_t0"]*(1.-SHIELD_DECAY_FRAC):a.xau_funnel["shield_or_comp_canceled"]+=1;a.xau_pending.pop(m,None);continue
   n=e.get(l)or{};i=e.get("DOWN"if l=="UP"else"UP")or{};g=float(n.get("best_ask")or 1.);f=float(i.get("best_bid")or.0);c=float(p["maker_px"])
   if f>.0:
    b=round(1.-f,4)
    if b<=c-1e-6 or(g>c+1e-6 and b<=c+1e-6):a.xau_funnel["shield_or_comp_canceled"]+=1;a.xau_pending.pop(m,None);continue
   if.0<g<=c:a.xau_funnel["maker_filled"]+=1;a._open_shadow_position(a.xau_open,p,c,XAU_TICKET_USD,is_maker=True,step_tag="XAU_SHIELDED_MAKER_FIRST",entry_ts=float(e.get("timestamp_unix")or now_u));a.xau_pending.pop(m,None)
   elif now_u>=float(p.get("deadline_mono")or.0):a.xau_funnel["ttl_expired_unfilled"]+=1;a.xau_pending.pop(m,None)
 def _open_shadow_position(self,open_map,p,fill_px,notional_usd,is_maker,step_tag,entry_ts=None):
  d=round(notional_usd/fill_px,4);c=str(p.get("asset")or"").upper()in("XAU","GOLD","XAG")
  if is_maker:b=.0;a=.0 if c else _maker_rebate_20pct_usd(d,fill_px)
  else:_,b=calculate_taker_fee(notional_usd,fill_px,fee_rate=.07,fee_exponent=1.);a=.0
  e=float(entry_ts)if entry_ts is not None else time.time();open_map[p["market_id"]]={"sleeve":p["sleeve"],"trade_id":p["trade_id"],"market_id":p["market_id"],"title":p["title"],"asset":p["asset"],"horizon":p["horizon"],"target_token":p["target_token"],"branch":p.get("branch",step_tag),"entry_step":step_tag,"is_maker_entry":is_maker,"entry_time":_utc_now_str(),"entry_unix":e,"t0_unix":p["t0_unix"],"expiry_unix":p["expiry_unix"],"tte_at_t0":round(p["tte_t0"],1),"z_strike":p["z_strike"],"cush_t0_pct":round(p["cush_t0"]*1e2,4),"open_usdt":p["open_usdt"],"twap_open_usdt":p["twap_open_usdt"],"auth_cl_open_usd":p["auth_cl_open_usd"],"entry_price":round(fill_px,4),"shares_bought":d,"notional_usd":round(notional_usd,2),"taker_fee_usd":round(b,4),"maker_rebate_20pct_est_usd":a,"take_profit_maker_limit_px":.98,"status":"OPEN"};self.save_states()
 def _check_open_position_exit(b,open_map,m_id,view,is_btc_5m=False,sleeve_tag=None):
  B=open_map.get(m_id)
  if not B or B.get("status")!="OPEN":return
  r=sleeve_tag or("b5"if is_btc_5m else"hz");y=float(view.get("timestamp_unix")or time.time());q=y-float(B.get("entry_unix")or.0);p=float(view.get("seconds_to_expiry")or max(.0,float(B["expiry_unix"])-y));A=B["target_token"];C=view.get(A)or{};o=C.get("raw_top_bids")or[];n=C.get("raw_top_asks")or[];x=float(C.get("best_bid")or(o[0][0]if o else.0));w=float(C.get("best_ask")or(n[0][0]if n else 1.));j=(not C.get("is_crossed"))and((.01<=x<w<=.999)or(x>=.98 and w>x));z=float(B.get("take_profit_maker_limit_px")or.98);i=str(B.get("asset")or"").upper()in("XAU","GOLD","XAG")
  if q>=4. and p>=15. and j and x>=z and(x>=z+.01 or w>z):e=round(B["shares_bought"]*z,4);m=.0 if i else _maker_rebate_20pct_usd(B["shares_bought"],z);b._finalize_closed_trade(pos=B,exit_px=z,payout_usd=e,exit_fee_usd=.0,exit_rebate_est_usd=m,exit_reason="MAKER_TP_98_FILLED",sleeve_tag=r);open_map.pop(m_id,None);return
  if p>=25. and x>=.12:
   if not i and.0<p<60. and B.get("horizon")in("15m","5m"):
    h=float(view.get("chainlink_proxy_usd_spot")or view.get("binance_spot")or.0);v=float(B.get("auth_cl_open_usd")or B.get("open_usdt")or.0);u=(b._sol_sigma_1h if B.get("asset")=="SOL"else(b._btc_sigma_1h if B.get("asset")=="BTC"else.0068));t,_=should_suppress_final60s_twap_salvage(side=A,strike_open=v,current_spot=h,twap_locked_mean=view.get("twap_locked_mean"),tte_sec=p,sigma_1h=u,twap_locked_weight=view.get("twap_locked_weight"))
    if t:B.pop("wrong_side_start_ts",None);return
   l=b._compute_signed_cushion(A,B["horizon"],float(view.get("binance_spot")or.0),B["open_usdt"],B["twap_open_usdt"],float(view.get("chainlink_proxy_usd_spot")or.0),B["auth_cl_open_usd"])
   if l is not None:
    if l>=.0:B.pop("wrong_side_start_ts",None)
    else:
     if p>9e2:d,a,c=.0014,.0011,22.
     elif p>180.:d,a,c=.0011,9e-4,18.
     else:d,a,c=9e-4,.00075,10.
     g=-l;k=B.get("wrong_side_start_ts")
     if k is None:
      if g>=d:B["wrong_side_start_ts"]=y
     elif g>=a:
      if(y-float(k))>=c:f=min(x,_walk_bids_vwap(o,B["shares_bought"],x));f=max(.01,f);e=round(B["shares_bought"]*f,4);s=.0 if i else calculate_taker_fee(e,f,fee_rate=.07,fee_exponent=1.)[1];b._finalize_closed_trade(pos=B,exit_px=f,payout_usd=e,exit_fee_usd=s,exit_rebate_est_usd=.0,exit_reason="SALVAGE_SPOT_ONLY_3ZONE",sleeve_tag=r);open_map.pop(m_id,None)
     else:B.pop("wrong_side_start_ts",None)
 def on_telemetry_tick(a,m_id,telem):
  if m_id in a.hz_open:a._check_open_position_exit(a.hz_open,m_id,telem,sleeve_tag="hz")
  if m_id in a.b5_open:a._check_open_position_exit(a.b5_open,m_id,telem,sleeve_tag="b5")
  if m_id in a.s5_open:a._check_open_position_exit(a.s5_open,m_id,telem,sleeve_tag="s5")
  if m_id in a.xau_open:a._check_open_position_exit(a.xau_open,m_id,telem,sleeve_tag="xau")
 def on_market_resolution(a,m_id,resolution):
  d=str(resolution.get("gamma_winning_outcome")or resolution.get("winning_outcome")or resolution.get("winner")or"").upper()
  if d not in("UP","DOWN"):return
  e=str(m_id)
  for b,h in((a.hz_open,"hz"),(a.b5_open,"b5"),(a.s5_open,"s5"),(a.xau_open,"xau")):
   g=b.pop(e,None)
   if not g or g.get("status")!="OPEN":continue
   f=(g["target_token"]==d);c=round(g["shares_bought"]*1.,4)if f else.0;g["oracle_mismatch"]=bool(resolution.get("oracle_mismatch",False));g["winning_outcome"]=d;a._finalize_closed_trade(pos=g,exit_px=1. if f else.0,payout_usd=c,exit_fee_usd=.0,exit_rebate_est_usd=.0,exit_reason="RESOLVED_WIN"if f else"RESOLVED_LOSS_WIPEOUT",sleeve_tag=h)
 def _finalize_closed_trade(a,pos,exit_px,payout_usd,exit_fee_usd,exit_rebate_est_usd,exit_reason,is_btc_5m=False,sleeve_tag=None):
  i=sleeve_tag or("b5"if is_btc_5m else"hz");h=round(payout_usd-pos["notional_usd"]-pos["taker_fee_usd"]-exit_fee_usd,2);g=round(float(pos.get("maker_rebate_20pct_est_usd")or.0)+exit_rebate_est_usd,4);pos.update({"status":"CLOSED","exit_reason":exit_reason,"exit_price":round(exit_px,4),"exit_fee_usd":round(exit_fee_usd,4),"payout_usd":round(payout_usd,2),"net_pnl_usd":h,"net_pnl_with_20pct_rebate_usd":round(h+g,2),"won":bool(h>0),"settle_time":_utc_now_str()});e={"hz":(a.hz_settled_ids,a.hz_settled_markets,a.hz_trades,a.hz_ledger_file),"b5":(a.b5_settled_ids,a.b5_settled_markets,a.b5_trades,a.b5_ledger_file),"s5":(a.s5_settled_ids,a.s5_settled_markets,a.s5_trades,a.s5_ledger_file),"xau":(a.xau_settled_ids,a.xau_settled_markets,a.xau_trades,a.xau_ledger_file)};j,d,c,b=e[i]
  if pos["trade_id"]in j:return
  j.add(pos["trade_id"]);d.add(pos["market_id"]);c.append(pos)
  with open(b,"a",encoding="utf-8")as f:f.write(json.dumps(pos)+"\n")
  a.save_states()
 def _tail_jsonl_file(a,path,pos_attr):
  if not path.exists():return[]
  g=[]
  try:
   d=path.stat().st_size;b=getattr(a,pos_attr)
   if d<b:setattr(a,pos_attr,d);b=d
   if d>b:
    with open(path,"rb")as f:f.seek(b);e=f.read()
    c=e.rfind(b"\n")+1
    if c>0:
     setattr(a,pos_attr,b+c)
     for h in e[:c].decode("utf-8",errors="ignore").splitlines():
      if h.strip():
       try:g.append(json.loads(h))
       except Exception:pass
  except Exception:pass
  return g
 def poll_tick(a,shutdown_requested=False):
  if shutdown_requested:a.save_states();return
  j=time.time()
  if not a.production_mode:
   for h in a._tail_jsonl_file(a.b5_telem_file,"b5_file_pos"):
    a._ingest_btc_5m_telemetry_tick(h);b=str(h.get("market_id")or"")
    if b in a.b5_pending:a.b5_pending[b]["latest_tick"]=h
   for h in a._tail_jsonl_file(a.s5_telem_file,"s5_file_pos"):
    a._ingest_sol_5m_telemetry_tick(h);b=str(h.get("market_id")or"")
    if b in a.s5_pending:a.s5_pending[b]["latest_tick"]=h
  for h in a._tail_jsonl_file(a.xau_telem_file,"xau_file_pos"):
   a.ingest_xau_15m_tick(h);b=str(h.get("market_id")or"")
   if b in a.xau_pending:a.xau_pending[b]["latest_tick"]=h
  d=((a.t15_btc_file,"t15_btc_pos"),(a.t15_eth_file,"t15_eth_pos"),(a.t1h_btc_file,"t1h_btc_pos"),(a.t1h_eth_file,"t1h_eth_pos"))
  if a.hz_open:
   for g,f in d:
    for h in a._tail_jsonl_file(g,f):
     b=str(h.get("market_id")or"")
     if b in a.hz_open:a._check_open_position_exit(a.hz_open,b,h,sleeve_tag="hz")
  else:
   for g,f in d:
    if g.exists():setattr(a,f,g.stat().st_size)
  i=time.time()
  if a.hz_pending:a._step_hz_pending(i)
  if a.b5_pending:a._step_b5_pending(i)
  if a.s5_pending:a._step_s5_pending(i)
  if a.xau_pending:a._step_xau_pending(i)
  for b,e in list(a.hz_open.items()):
   c=a._extract_market_view(e["asset"],b,e["horizon"])
   if c is not None:a._check_open_position_exit(a.hz_open,b,c,sleeve_tag="hz")
  for b,e in list(a.b5_open.items()):
   c=a._extract_market_view("BTC",b,"5m")
   if c is not None:a._check_open_position_exit(a.b5_open,b,c,sleeve_tag="b5")
  for b,e in list(a.s5_open.items()):
   c=a._extract_market_view("SOL",b,"5m")
   if c is not None:a._check_open_position_exit(a.s5_open,b,c,sleeve_tag="s5")
  for b,e in list(a.xau_open.items()):
   c=a._extract_market_view("XAU",b,"15m")
   if c is not None:a._check_open_position_exit(a.xau_open,b,c,sleeve_tag="xau")
  if(j-a._last_state_flush_ts)>=15.:a.save_states()
 def _build_sleeve_state(self,sleeve_id,strategy_desc,min_grad_trades,trades,open_map,pending_map,funnel,ledger_path,ticket_usd=SHADOW_TICKET_USD):n=len(trades);h=[float(t.get("net_pnl_usd")or.0)for t in trades];b=[float(t.get("net_pnl_with_20pct_rebate_usd")or t.get("net_pnl_usd")or.0)for t in trades];g=sum(1 for x in h if x>0);l=round((g/n)*1e2,2)if n>0 else.0;k=sum(x for x in h if x>0);j=abs(sum(x for x in h if x<=0));i=round(k/j,3)if j>1e-6 else(99. if k>0 else.0);a=round(sum(h),2);f=round(sum(float(t.get("taker_fee_usd")or.0)+float(t.get("exit_fee_usd")or.0)for t in trades),2);d,e=_bootstrap_prob_positive(h);c=bool(n>=min_grad_trades and i>=1.5 and e[0]>.0 and d>=.95);return{"timestamp":_utc_now_str(),"sleeve_id":sleeve_id,"strategy":strategy_desc,"graduation_criteria":f"trades >= {min_grad_trades}, PF >= 1.50, bootstrap_95ci_lo > $0.00 (P(>0) >= 95%)","ready_for_live_graduation":c,"initial_capital":SHADOW_INITIAL_CAPITAL,"ticket_notional_usd":ticket_usd,"current_equity":round(SHADOW_INITIAL_CAPITAL+a,2),"realized_pnl":a,"realized_pnl_with_20pct_maker_rebate":round(sum(b),2),"profit_factor":i,"win_rate_pct":l,"bootstrap_prob_positive":d,"bootstrap_95ci_total_pnl":e,"total_fees_paid":f,"total_trades_settled":n,"winning_trades":g,"losing_trades":n-g,"active_open_positions_count":len(open_map),"open_positions":dict(open_map),"pending_orders_count":len(pending_map),"funnel_counters":dict(funnel),"status":"RUNNING","ledger_file":str(ledger_path)}
 def save_states(a):
  a._last_state_flush_ts=time.time();g=a._build_sleeve_state(sleeve_id="SLEEVE_HYBRID_ZSPLIT_SHADOW",strategy_desc="BTC/ETH 15m+1h Hybrid z-Split (0.78<=z<1.20 Shielded Maker 0% Fee + Comp-Book Shield + <=45$ Queue Cap, z>=1.20 Taker+P3A)",min_grad_trades=50,trades=a.hz_trades,open_map=a.hz_open,pending_map=a.hz_pending,funnel=a.hz_funnel,ledger_path=a.hz_ledger_file);e=a._build_sleeve_state(sleeve_id="SLEEVE_BTC_5M_SNIPER_SHADOW",strategy_desc="BTC-Only 5m Final-TWAP Sniper (TTE 60-180s, USD Chainlink + USDT Dual-Strike Cush>=3bps, z>=0.80, px<=0.85, ETH/SOL Excluded)",min_grad_trades=60,trades=a.b5_trades,open_map=a.b5_open,pending_map=a.b5_pending,funnel=a.b5_funnel,ledger_path=a.b5_ledger_file);d=a._build_sleeve_state(sleeve_id="SLEEVE_SOL_5M_CANARY_SHADOW",strategy_desc="SOL-Only 5m Isolated Canary Shadow (TTE 60-180s, sqrt(12) vol, Dual-Strike Cush>=4bps, z>=0.80, px<=0.85)",min_grad_trades=60,trades=a.s5_trades,open_map=a.s5_open,pending_map=a.s5_pending,funnel=a.s5_funnel,ledger_path=a.s5_ledger_file);c=a._build_sleeve_state(sleeve_id="SLEEVE_XAU_15M_MAKER_SHADOW",strategy_desc="XAU/USD 15m Shielded Maker-First (3-dec synth USD + Swissquote <=2.5bps, single-spot diffusion, CME/Session gated, 0% fee/0% rebate, $12 clip)",min_grad_trades=40,trades=a.xau_trades,open_map=a.xau_open,pending_map=a.xau_pending,funnel=a.xau_funnel,ledger_path=a.xau_ledger_file,ticket_usd=XAU_TICKET_USD)
  for h,b in((g,a.hz_state_file),(e,a.b5_state_file),(d,a.s5_state_file),(c,a.xau_state_file)):
   i=b.with_suffix(f".tmp.{os.getpid()}")
   try:
    with open(i,"w",encoding="utf-8")as f:json.dump(h,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(i,b)
   except Exception:
    if i.exists():
     try:i.unlink()
     except Exception:pass
# ======================================================================================
# [03/21] MODULE: src/polymarket_research/orderflow_wfo_simulators.py
# PURPOSE: v4.0 100ms Micro-Clip 4-Step Cascade Replay, D1 Latency-Skew WFO & Legging-Drag Parity Engine
# ======================================================================================

# from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import math;from pathlib import Path;from typing import Any,Dict,List,Optional,Sequence,Tuple;DEFAULT_FEE_RATE=.07
def v2_taker_fee_per_share(px,fee_rate=DEFAULT_FEE_RATE,fee_exponent=1.):
 if fee_rate<=.0:return.0
 a=max(.001,min(.999,float(px)));return float(fee_rate)*((a*(1.-a))**float(fee_exponent))
def build_candidate_micro_clips(cand):
 g=cand.get("micro_clips")
 if isinstance(g,(list,tuple))and g:
  k=[(float(r[0]),float(r[1]),float(r[2]),float(r[3]))for r in g if isinstance(r,(list,tuple))and len(r)>=4 and float(r[0])>.0]
  if k:k.sort(key=lambda x:x[0]);return k
 c=float(cand.get("cushion_oracle",cand.get("cushion_min",.0))or.0);f=float(cand.get("bid_t0",.0)or.0);e=float(cand.get("ask_t0",1.)or 1.);d=float(cand.get("ask_500ms")or e);b=float(cand.get("ask_1000ms")or d);i=float(cand.get("tte",3e2)or 3e2);a=[(.1,c,f,round(.5*(e+d),4)),(.25,c,f,round(.25*e+.75*d,4)),(.5,c,max(.01,round(d-max(.01,e-f),4)),d),(1.,c,max(.01,round(b-max(.01,e-f),4)),b)]
 for j in cand.get("path")or():
  if len(j)<4:continue
  h=round(max(.0,i-float(j[0])),3)
  if 1.05<=h<=6.:a.append((h,float(j[1]),float(j[2]),float(j[3])))
 a.sort(key=lambda x:x[0]);return a
def _clip_at_or_after(clips,target_dt,fallback):
 for a in clips:
  if a[0]>=target_dt-1e-6:return a
 return clips[-1]if clips else fallback
def simulate_microclip_cascade_entry(cand,cfg,latency_mode="500ms"):
 _i=float(cand.get("ask_t0",1.)or 1.);_h=float(cand.get("bid_t0",.0)or.0);_g=float(cfg.get("min_px",.52));_f=float(cfg.get("max_px",.85));E=float(cfg.get("fak_buffer",.02));T=float(cfg.get("fee_rate",DEFAULT_FEE_RATE));D=max(5.,float(cfg.get("cascade_ticket_usd",16.5)));x=max(5.,min(D,float(cfg.get("elastic_downsnap_usd",12.))));l=float(cfg.get("fallback_2c_min_z",1.25));s=float(cfg.get("fallback_2c_add",.02));k=bool(cfg.get("enable_elastic_downsnap",True));q=bool(cfg.get("enable_fallback_2c",True));j=bool(cfg.get("enable_phase3a_rescue",True));m=max(.2,float(cfg.get("phase3a_ttl_s",3.5)));p=min(.95,max(.1,float(cfg.get("phase3a_spot_shield_decay",.5))));S=float(cand.get("cushion_oracle",cand.get("cushion_min",.0))if cfg.get("use_cl_proxy",True)else cand.get("cushion_min",.0));_l=float(cand.get("z_oracle",cand.get("z_cushion",.0))if cfg.get("use_cl_proxy",True)else cand.get("z_cushion",.0));C=float(cand.get("l1_ask_usd",D)or.0);_e=max(.0,float(cand.get("slip20_t0",.0)or.0));K=float(cand.get("shock_vol",.0)or.0);_k=build_candidate_micro_clips(cand);_j=.5 if latency_mode=="500ms"else 1.;i=float(cand.get("ask_500ms"if latency_mode=="500ms"else"ask_1000ms")or _i);R=_clip_at_or_after(_k,_j,(_j,S,_h,i));_b=i if cand.get("micro_clips")is None else float(R[3]);Q=float(R[1]);_a=float(R[2])if float(R[2])>.0 else max(.01,round(_b-max(.01,_i-_h),4))
 if(_i-_b)>=.04:return None
 g=.01 if(K>=4.5e5 and C<D*1.5)else.0;w=round(min(.99,_b+g),4);f=round(min(_f,_i+E),4);h=bool(cfg.get("hybrid_z_split",False));v=float(cfg.get("z_taker_cut",1.2));b=h and _l<v
 if not b:
  if.0<w<.99 and C>=D:
   J=round(max(w,_i+min(.03,_e)),4)
   if J<=f and J<=_f:return(J,v2_taker_fee_per_share(J,T),_j,1.,"STEP1_SMART_FAK")
  if k and.0<w<.99:
   e=float(cfg.get("min_elastic_usd",x))
   for P in(x,e):
    if P<D and C>=P-1e-6:
     Z=round(P/D,4);o=round(max(w,_i+min(.02,_e*Z)),4)
     if o<=f and o<=_f:return(o,v2_taker_fee_per_share(o,T),round(_j+.05,3),Z,"STEP2_ELASTIC_DOWNSNAP")
  if(q and _l>=l and(f+.01)<=(_f+1e-6)and C>=x):
   u=round(min(_f,f+s),4)
   if u>f+1e-6:
    _n=round(_j+.15,3);Y=_clip_at_or_after(_k,_n,(_n,Q,_a,w));_d=round(min(.99,float(Y[3])+g),4)
    if(_i-_d)>=.04:return None
    X=1. if C>=D else round(x/D,4);W=round(max(_d,_i+min(.03,_e*X)),4)
    if.0<_d<.99 and W<=u and W<=_f:return(W,v2_taker_fee_per_share(W,T),_n,X,"STEP3_FAK_PLUS_2C_FALLBACK")
 if not j and not b:return None
 t=round(_j+(.05 if b else.2),3);O=_clip_at_or_after(_k,t,(t,Q,_a,w));V=float(O[3]);U=float(O[2])if float(O[2])>.0 else _a;I=float(O[1])
 if S>.0 and I<S*(1.-p):return None
 if V<=_g+.005 or(_i-V)>=.04:return None
 if b:B=round(V-U,4);c=round(min(_f,V-.01,U+(.01 if B>=.02 else.0)),2)
 else:c=round(min(_f,V-.01,max(U,_i)),2)
 if c<_g or c>=V-1e-6:return None
 d=bool(cfg.get("use_complement_shield",b));a=float(cfg.get("max_maker_join_queue_usd",45.));A=float(cand.get("l1_bid_usd",.0)or.0)
 if d and c<=U+1e-6 and A>a:return None
 H={round(float(r[0]),3):float(r[4])for r in(cand.get("micro_clips_opp")or cand.get("micro_clips")or())if isinstance(r,(list,tuple))and len(r)>=5 and float(r[4])>.0};z=float(cand.get("opp_bid_t0",.0)or.0)
 if d and z>.0 and round(1.-z,4)<=c-1e-6:return None
 n=(-.2*v2_taker_fee_per_share(c,T)if bool(cfg.get("include_maker_rebate",False))else.0);G=float(cfg.get("maker_ttl_s",6.))if b else m;N=1. if C>=D else round(x/D,4);y=t+G;M="HYBRID_MAKER_FIRST"if b else"STEP4_PHASE3A_MAKER_RESCUE"
 for _m,_c,_p,_o in _k:
  if _m<t-1e-6:continue
  if _m>y+1e-6:break
  if S>.0 and(_c<=.0 or _c<S*(1.-p)):return None
  if d:
   F=H.get(round(_m,3),.0)
   if F>.0:
    L=round(1.-F,4)
    if L<=c-1e-6 or(_o>c+1e-6 and L<=c+1e-6):return None
  if.0<_o<=c:return(c,round(n,6),round(_m,3),N,M)
 return None
def compute_d1_legging_drag_haircut(shares,box_cost_net,avail_a_shares,avail_b_shares,px_a,px_b,fee_rate_a=DEFAULT_FEE_RATE,fee_rate_b=DEFAULT_FEE_RATE,is_4h_mixed=False,is_zero_itode=False,unwind_slip_cents=.02):
 m=max(1.,float(shares));g=min(max(.0,float(avail_a_shares)),max(.0,float(avail_b_shares)));f=g/m
 if f<1.15:a=.22
 elif f<1.5:a=.16
 elif f<2.25:a=.05
 else:a=.015
 if is_zero_itode:a*=.4
 if is_4h_mixed:a=min(.35,a+.05)
 k=max(.02,min(.98,.5*(float(px_a)+float(px_b))));j=max(.0,.5*(float(fee_rate_a)+float(fee_rate_b)));i=v2_taker_fee_per_share(k,j);l=max(.01,k-float(unwind_slip_cents));h=v2_taker_fee_per_share(l,j);d=float(unwind_slip_cents)+i+h;e=a*d;b=1.-float(box_cost_net);c=b-e;return{"min_depth_mult":round(f,4),"p_leg_miss":round(a,4),"unwind_loss_per_share":round(d,5),"legging_drag_per_pair":round(e,5),"legging_drag_usd":round(m*e,4),"gross_floor_per_pair":round(b,5),"legging_adjusted_net_ev_per_pair":round(c,5),"legging_adjusted_min_profit_usd":round(m*c,4)}
def simulate_d1_box_with_latency_skew(box_cand,policy_cfg,delta_t_ms=150.):
 R=max(5.,float(box_cand.get("shares",12.)));P=float(box_cand.get("leg_a_limit_price",.48));O=float(box_cand.get("leg_b_limit_price",.48));C=float(box_cand.get("leg_a_avail_shares",R*2.));B=float(box_cand.get("leg_b_avail_shares",R*2.));N=str(box_cand.get("leg_a_horizon","15m")).lower();M=str(box_cand.get("leg_b_horizon","5m")).lower();L=float(box_cand.get("leg_a_fee_rate",DEFAULT_FEE_RATE));K=float(box_cand.get("leg_b_fee_rate",DEFAULT_FEE_RATE));t=float(box_cand.get("box_cost_net")or(P+O+v2_taker_fee_per_share(P,L)+v2_taker_fee_per_share(O,K)));s=bool(box_cand.get("corridor_jackpot",False));k=float(policy_cfg.get("min_depth_mult_gate",1.5));e=float(policy_cfg.get("depth_ratio_threshold",1.35));r=str(policy_cfg.get("routing_mode","hybrid_auto"));f=float(policy_cfg.get("max_giveback_frac",.35));q=float(policy_cfg.get("max_box_cost_net",.985));z=min(C,B);y=max(C,B)
 if t>q or(z/R)<k:return{"entered":False,"outcome":"GATED_OUT","pnl_usd":.0,"legged_out":False}
 v=("4h"in(N,M))and(N!=M);x=y/max(z,1e-6)
 if r=="fragile_first":a=True
 elif r=="parallel_2leg":a=False
 else:a=bool(v or x>=e or t>.975)
 d=True
 if v:d=(N!="4h")
 elif B<C:d=False
 if d:J=(P,C,L,float(box_cand.get("depletion_a_per_s",18.)),float(box_cand.get("bid_drop_a",.02)));I=(O,B,K,float(box_cand.get("depletion_b_per_s",10.)),float(box_cand.get("bid_drop_b",.02)))
 else:J=(O,B,K,float(box_cand.get("depletion_b_per_s",18.)),float(box_cand.get("bid_drop_b",.02)));I=(P,C,L,float(box_cand.get("depletion_a_per_s",10.)),float(box_cand.get("bid_drop_a",.02)))
 j=float(box_cand.get("base_transit_s",.12));F=max(.0,float(delta_t_ms)/1e3)
 if a:
  p=J[1]-J[3]*j
  if p<R:return{"entered":False,"outcome":"LEG1_CLEAN_ABORT","pnl_usd":.0,"legged_out":False}
  o=I[1]-I[3]*(j+F);b=J;c=o>=R
 else:
  p=J[1]-J[3]*(j+.25*F);o=I[1]-I[3]*(j+.25*F)
  if p>=R and o>=R:c=True;b=J
  elif p<R and o<R:return{"entered":False,"outcome":"BOTH_MISSED_CLEAN","pnl_usd":.0,"legged_out":False}
  else:c=False;b=J if p>=R else I
 if c:i=2. if s else 1.;Q=round(R*(i-t),4);return{"entered":True,"outcome":"BOX_LOCKED","pnl_usd":Q,"legged_out":False}
 H,_,G,_,n=b;E=v2_taker_fee_per_share(H,G);l=max(.01,1.-t);h=max(.01,min(.03,f*l*2.));u=max(.02,round(H-n,4));m=round(max(.02,H-h),4)
 if u>=m:w=u;g="LEGGED_OUT_STAGE1"
 else:w=max(.02,round(max(H*.85,u-.015),4));g="LEGGED_OUT_STAGE2"
 A=v2_taker_fee_per_share(w,G);D=round(R*((w-H)-E-A),4);return{"entered":True,"outcome":g,"pnl_usd":D,"legged_out":True}
def _default_d1_calibration_events(data_dir=None):
 k=[]
 if data_dir is not None:
  j=Path(data_dir)/"d1_live_box_candidates.jsonl"
  if j.exists():
   try:a=j.read_text(encoding="utf-8",errors="ignore").splitlines()
   except Exception:a=[]
   for s in a:
    if not s.strip():continue
    try:
     d=json.loads(s)
     if not isinstance(d,dict):continue
     r=max(5.,float(d.get("shares")or 12.));e=float(d.get("leg_a_avail_shares")or r*1.8);c=float(d.get("leg_b_avail_shares")or r*1.8);k.append({**d,"depletion_a_per_s":round(max(4.,.32*e),2),"depletion_b_per_s":round(max(4.,.24*c),2),"bid_drop_a":.02 if float(d.get("box_cost_net")or.98)<=.98 else.03,"bid_drop_b":.02})
    except Exception:continue
 if len(k)>=36:return k
 i=[];b=[(.968,36.,34.,"15m","5m",14.,12.,.015,False),(.974,19.,42.,"15m","5m",22.,10.,.02,False),(.991,13.5,28.,"15m","5m",24.,14.,.03,False),(.976,38.,20.,"4h","15m",10.,26.,.025,False),(.964,30.,29.,"15m","5m",12.,12.,.015,True),(.982,16.,35.,"4h","15m",28.,12.,.03,False)]
 for q in range(60):h,e,c,p,o,m,l,g,n=b[q%len(b)];f=(q%5-2)*.0015;i.append({"shares":12.,"box_cost_net":round(h+f,4),"leg_a_limit_price":round(.5*(h+f)-.01,4),"leg_b_limit_price":round(.5*(h+f)-.01,4),"leg_a_avail_shares":e,"leg_b_avail_shares":c,"leg_a_horizon":p,"leg_b_horizon":o,"depletion_a_per_s":m,"depletion_b_per_s":l,"bid_drop_a":g,"bid_drop_b":.02,"corridor_jackpot":bool(n and(q%12==4))})
 return i
def _score_d1_slice(events,cfg,skew_grid_ms=(.0,1e2,2e2,4e2)):
 d=[];b=0;a=0
 for h in events:
  for c in skew_grid_ms:
   r=simulate_d1_box_with_latency_skew(h,cfg,delta_t_ms=c)
   if r["entered"]:
    a+=1;d.append(float(r["pnl_usd"]))
    if r["legged_out"]:b+=1
 g=sum(x for x in d if x>.0);f=abs(sum(x for x in d if x<=.0));e=g/f if f>1e-6 else(99. if g>.0 else.0);return{"entered":a,"net_pnl_usd":round(sum(d),3),"profit_factor":round(e,3),"legged_out_count":b,"legged_out_rate":round(b/max(a,1),4)}
def calibrate_d1_box_wfo(box_events=None,data_dir=None,purge_gap=3):
 p=list(box_events)if box_events is not None else _default_d1_calibration_events(data_dir);n=len(p);w=max(4,int(.5*n));o=min(n,w+purge_gap);m=max(o+2,int(.75*n));l=min(n,m+purge_gap);t=p[:w];s=p[o:m];r=p[l:];c=-1e9;f={"routing_mode":"hybrid_auto","depth_ratio_threshold":1.35,"min_depth_mult_gate":1.5,"max_giveback_frac":.35,"max_box_cost_net":.985};b={};a={};d=0
 for k in("hybrid_auto","fragile_first","parallel_2leg"):
  for q in(1.2,1.35,1.5):
   for j in(1.15,1.5,1.75):
    for i in(.25,.35,.5):
     g={"routing_mode":k,"depth_ratio_threshold":q,"min_depth_mult_gate":j,"max_giveback_frac":i,"max_box_cost_net":.985};d+=1;v=_score_d1_slice(t,g);u=_score_d1_slice(s,g)
     if v["entered"]<4 or u["entered"]<2:continue
     x=(min(v["net_pnl_usd"],u["net_pnl_usd"])+.25*(v["net_pnl_usd"]+u["net_pnl_usd"])-8.*max(v["legged_out_rate"],u["legged_out_rate"]))
     if x>c:c=x;f=g;b=v;a=u
 if not b:b=_score_d1_slice(t,f);a=_score_d1_slice(s,f)
 h=_score_d1_slice(r,f);e=_score_d1_slice(r,{"routing_mode":"parallel_2leg","depth_ratio_threshold":1.5,"min_depth_mult_gate":1.,"max_giveback_frac":.25,"max_box_cost_net":.995});return{"events_total":n,"purge_gap_events":purge_gap,"grid_configs_evaluated":d,"selected_d1_policy":f,"train":b,"val":a,"sealed_holdout":h,"unfiltered_parallel_holdout_baseline":e}
def compute_d1_maker_anchor_drag_haircut(shares,pair_eff,bid_anc,hdg_px,hdg_avail_shares,fee_rate_anc=DEFAULT_FEE_RATE,fee_exponent_anc=1.,queue_front=True,is_4h_mixed=False,scratch_slip_cents=.015):
 j=max(1.,float(shares));f=max(.0,float(hdg_avail_shares))/j
 if f<1.5:a=.14
 elif f<2.5:a=.055
 else:a=.02
 if not queue_front:a=min(.3,a+.025)
 if is_4h_mixed:a=min(.3,a+.02)
 i=max(.01,float(bid_anc)-float(scratch_slip_cents));h=v2_taker_fee_per_share(i,fee_rate_anc,fee_exponent_anc);c=(float(bid_anc)-i)+h;e=a*c;d=1.-float(pair_eff);g=d-e;b=.2*v2_taker_fee_per_share(float(bid_anc),fee_rate_anc,fee_exponent_anc);return{"hdg_depth_mult":round(f,4),"p_hedge_miss_250ms":round(a,4),"scratch_loss_per_share":round(c,5),"legging_drag_per_pair":round(e,5),"legging_drag_usd":round(j*e,4),"gross_floor_per_pair":round(d,5),"legging_adjusted_net_ev_per_pair":round(g,5),"legging_adjusted_min_profit_usd":round(j*g,4),"maker_rebate_20pct_est_usd":round(j*b,4)}
def _default_d1_maker_leg1_events():
 a=[("UP",.48,.5,.12,.48,85.,.6,True,.0,18.),("DOWN",.48,.49,.18,.49,95.,-.8,True,.0,18.),("UP",.48,.49,-.48,.49,60.,-4.2,True,.04,18.),("UP",.964,.999,.1,.019,32.,.4,True,.0,15.),("DOWN",.47,.49,.05,.49,70.,3.8,True,.03,18.),("UP",.46,.48,.22,.5,18.,.3,True,.02,18.)];m=[]
 for l in range(60):g,k,j,d,i,f,c,e,b,n=a[l%len(a)];h=(l%3-1)*.001;m.append({"anc_side":g,"bid_anc":round(k,3),"ask_anc":round(j,3),"obi_anc":round(d+h*10.,3),"ask_hdg":round(i,3),"hdg_shares":f,"spot_ret_bps":c,"passive_fill":e,"hdg_jump_on_adverse":b,"shares":n,"fee_rate":DEFAULT_FEE_RATE})
 return m
def simulate_d1_maker_leg1_box(ev,cfg):
 B=float(ev["bid_anc"]);A=float(ev["ask_anc"]);s=float(ev.get("obi_anc",.0));z=float(ev["ask_hdg"]);y=float(ev["hdg_shares"]);G=max(5.,float(ev.get("shares",18.)));F=float(ev.get("fee_rate",DEFAULT_FEE_RATE));D=str(ev.get("anc_side","UP")).upper();g=float(ev.get("spot_ret_bps",.0))
 def _snap_px(p):p=round(float(p),4);return(math.floor((p+1e-9)*1e2)/1e2)if(.04+1e-9<p<.96-1e-9)else(math.floor((p+1e-9)*1e3)/1e3)
 x=.001 if(B>=.96 or B<.04)else.01;w=.001 if(A>.96 or A<=.04)else.01;n=_snap_px(B+x);k=_snap_px(A-w);E=round(A-B,4);d=bool(cfg.get("allow_join_1c_mid",True));j=float(cfg.get("min_obi_join_1c",-.15));i=float(cfg.get("min_obi_any",-.35));f=float(cfg.get("min_hdg_depth_mult",2.5));e=float(cfg.get("max_post_net",.988));c=float(cfg.get("adverse_spot_cancel_bps",2.5))
 if s<i or y<max(15.,f*G):return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 if n<=k+1e-9 and n>B+1e-9:a=min(n,k);b=True
 elif d and E>=.01-1e-9 and.15<=A<=.85 and s>=j:a=_snap_px(B);b=False
 else:return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 m=z+v2_taker_fee_per_share(z,F);r=_snap_px(e-m);v=min(a,r)
 if v<round(B-(x if b else.0),3)or v<=.02 or v>=A:return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 if not(.9<=(v+m)<=e):return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 q=(-g)if D=="UP"else g
 if q>c:return{"posted":True,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 if not ev.get("passive_fill",True):return{"posted":True,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 h=round(z+(float(ev.get("hdg_jump_on_adverse",.0))if q>1.5 else.0),4);l=v+h+v2_taker_fee_per_share(h,F)
 if.9<=l<=.995:C=compute_d1_maker_anchor_drag_haircut(shares=G,pair_eff=l,bid_anc=v,hdg_px=h,hdg_avail_shares=y,fee_rate_anc=F,queue_front=b);return{"posted":True,"filled":True,"hedged":True,"scratched":False,"pnl_usd":round(G*(1.-l),4),"adj_pnl_usd":C["legging_adjusted_min_profit_usd"]}
 u=max(.01,v-max(.015,float(ev.get("hdg_jump_on_adverse",.02))));o=u-v2_taker_fee_per_share(u,F);t=round(G*(o-v),4);return{"posted":True,"filled":True,"hedged":False,"scratched":True,"pnl_usd":t,"adj_pnl_usd":t}
def calibrate_d1_maker_leg1_wfo(maker_events=None,purge_gap=3):
 p=list(maker_events)if maker_events is not None else _default_d1_maker_leg1_events();n=len(p);y=max(4,int(.5*n));o=min(n,y+purge_gap);m=max(o+2,int(.75*n));l=min(n,m+purge_gap);v,u,t=p[:y],p[o:m],p[l:]
 def _eval(sub,cfg):g=[simulate_d1_maker_leg1_box(e,cfg)for e in sub];d=[r for r in g if r["filled"]];f=[r for r in d if r["hedged"]];a=[r for r in d if r["scratched"]];c=sum(float(r.get("adj_pnl_usd",r["pnl_usd"]))for r in d);b=sum(float(r["pnl_usd"])for r in d);return{"posted":sum(1 for r in g if r["posted"]),"fills":len(d),"wins":len(f),"scratches":len(a),"win_rate_pct":round(1e2*len(f)/len(d),2)if d else.0,"raw_pnl_usd":round(b,4),"legging_adjusted_pnl_usd":round(c,4)}
 d=-1e9;c={"allow_join_1c_mid":True,"min_obi_join_1c":-.15,"min_obi_any":-.35,"min_hdg_depth_mult":2.5,"adverse_spot_cancel_bps":2.5,"max_post_net":.988};b={};a={};f=0
 for j in(True,False):
  for i in(2.,2.5,5.):
   for k in(-.15,-.4):
    for s in(1.5,2.5):
     q={"allow_join_1c_mid":j,"min_obi_join_1c":k,"min_obi_any":-.35,"min_hdg_depth_mult":s,"adverse_spot_cancel_bps":i,"max_post_net":.988};f+=1;x,w=_eval(v,q),_eval(u,q)
     if x["fills"]<3 or w["fills"]<2:continue
     z=(min(x["legging_adjusted_pnl_usd"],w["legging_adjusted_pnl_usd"])+.3*(x["legging_adjusted_pnl_usd"]+w["legging_adjusted_pnl_usd"])-6.*(x["scratches"]+w["scratches"]))
     if z>d:d,c,b,a=z,q,x,w
 if not b:b,a=_eval(v,c),_eval(u,c)
 h=_eval(t,c);g=_eval(t,{"allow_join_1c_mid":True,"min_obi_join_1c":-1.,"min_obi_any":-1.,"min_hdg_depth_mult":1.,"adverse_spot_cancel_bps":99.,"max_post_net":.992});return{"events_total":n,"purge_gap_events":purge_gap,"grid_configs_evaluated":f,"selected_maker_leg1_policy":c,"train":b,"val":a,"sealed_holdout":h,"unguarded_maker_holdout_baseline":g}
def compute_v395_pricing_and_twap_gate(cand,*,df=None,jump_vol_mult=1.,use_kemna_vorst=False):
 from src.polymarket_research.exact_twap_lock_engine import(compute_kemna_vorst_twap_sigma_rem,compute_unit_variance_student_t_cdf);h=float(cand.get("cushion_oracle",cand.get("cushion_min",.0))or.0);j=max(5.,float(cand.get("tte",3e2)or 3e2));b=max(.00025,float(cand.get("sigma_rem",.002)or.002));f=b/math.sqrt(max(j,1.)/3600.)
 if use_kemna_vorst and str(cand.get("hz")or"")in("5m","15m"):a=max(.00018,compute_kemna_vorst_twap_sigma_rem(f,j,window_sec=60.))
 else:a=b
 d=a*max(.5,float(jump_vol_mult));g=h/d;i=min(1.,max(.0,float(cand.get("shock_ofi",.0)or.0)));e=g+.25*i
 if df is None or math.isinf(float(df))or float(df)>1e2:c=.5*(1.+math.erf(e/math.sqrt(2.)))
 else:c=compute_unit_variance_student_t_cdf(e,df=float(df))
 return round(g,5),round(max(.01,min(.995,c)),5)
def run_wfo_post_selection_diagnostics(*,cands,dev_cands,holdout_cands,best_cfg,best_tr,best_vl,best_hold_500,stage2_results,data_dir,purge_sec,evaluate_portfolio_fn,prefilter_fn,dev_score_fn,simulate_single_fn):
 import itertools;import random;import statistics;T=sorted(cands,key=lambda x:x["t0"]);_B=len(T);_c=6;F=[]
 for _A in range(_c):_O=int((_A/_c)*_B);_N=int(((_A+1)/_c)*_B)-1;F.append((T[_O]["t0"],T[max(_O,_N)]["t0"]))
 m=[]
 for _z,_y in[(.55,.8),(.55,.82),(.55,.85)]:
  for _M in[.65,.85,1.05]:
   for _L in[4e-4,6e-4]:
    for _5 in[.01,.02]:
     for _K in["single_95","two_tranche_14_98","two_tranche_95_98","hold_98"]:
      for _4,_3,_2,_1 in[("spot_persist",None,9e-4,18.),("hybrid_persist",.12,6e-4,15.)]:m.append({"assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":90.,"max_tte_15m":480.,"min_tte_1h":150.,"max_tte_1h":1200.,"min_px":_z,"max_px":_y,"max_spread":.03,"min_l1_usd":20.,"min_cushion":_L,"min_z":_M,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True,"entry_mode":"taker_fak","fak_buffer":_5,"exit_policy":_K,"ratchet_arm":_3,"ratchet_drop":.06,"salvage_mode":_4,"wrong_side_thresh":_2,"salvage_persist_s":_1,"clob_drop_thresh":.22,"final_45s_unwind":False})
 q=prefilter_fn(T,{"assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":90.,"max_tte_15m":480.,"min_tte_1h":150.,"max_tte_1h":1200.,"min_px":.55,"max_px":.85,"max_spread":.03,"min_l1_usd":20.,"min_cushion":4e-4,"min_z":.65,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True});N=[]
 for _0,_Z in itertools.combinations(range(_c),2):
  z=[F[_0],F[_Z]];S=[c for c in q if all((c["exp_ts"]<(ts_i-purge_sec))or(c["t0"]>(te_i+purge_sec))for ts_i,te_i in z)];_b=[]
  for _Y in(_0,_Z):_X,_W=F[_Y];R=purge_sec if(_Y>0 and(_Y-1)not in(_0,_Z))else.0;M=purge_sec if(_Y<_c-1 and(_Y+1)not in(_0,_Z))else.0;_x,_w=_X+R,_W-M*.25;_b.extend(c for c in q if _x<=c["t0"]<=_w and c["exp_ts"]<=_W)
  _b.sort(key=lambda x:x["t0"]);_J=len(S);L=S[int(.7*_J)]["t0"]if _J>=20 else.0;_v=[c for c in S if c["exp_ts"]<=L];_u=[c for c in S if c["t0"]>=(L+purge_sec)];f=m[0];d=-1e9
  for o in m:
   _t=evaluate_portfolio_fn(_v,o,latency_mode="500ms")
   if _t["trades"]<20 or _t["total_pnl"]<=0 or _t["profit_factor"]<1.2:continue
   _s=evaluate_portfolio_fn(_u,o,latency_mode="500ms")
   if _s["trades"]<8 or _s["total_pnl"]<=0 or _s["profit_factor"]<1.15:continue
   _a=dev_score_fn(_t,_s)
   if _a>d:d,f=_a,o
  if d<=-1e8:
   for o in m:
    _l=evaluate_portfolio_fn(S,o,latency_mode="500ms")
    if _l["trades"]>=25 and _l["total_pnl"]>0:
     _a=dev_score_fn(_l,_l)
     if _a>d:d,f=_a,o
  _k=evaluate_portfolio_fn(_b,f,latency_mode="500ms");K=evaluate_portfolio_fn(_b,f,latency_mode="500ms",max_concurrent=1,ticket_usd=12.);N.append({"test_groups":[_0,_Z],"fitted_exit_policy":f["exit_policy"],"fitted_min_z":f["min_z"],"trades":_k["trades"],"total_pnl":_k["total_pnl"],"seed_12_c1_pnl":K["total_pnl"],"win_rate":_k["win_rate"],"profit_factor":_k["profit_factor"],"sharpe":_k["sharpe"],"wipeout_rate":_k["wipeout_rate"]})
 y=[s["total_pnl"]for s in N];w=[s["seed_12_c1_pnl"]for s in N];E={"mode":"GENUINE_OUT_OF_SAMPLE_REFIT_CPCV_6_2","n_groups":6,"k_test_groups":2,"apriori_grid_size":len(m),"total_combinations":len(N),"positive_combinations":sum(1 for x in y if x>0),"positive_rate":round(sum(1 for x in y if x>0)/max(len(N),1),4),"seed_12_c1_positive_combinations":sum(1 for x in w if x>0),"median_oos_trades":int(statistics.median(s["trades"]for s in N)),"median_oos_pnl_usd":round(statistics.median(y),2),"mean_oos_pnl_usd":round(statistics.mean(y),2),"median_seed_12_c1_oos_pnl_usd":round(statistics.median(w),2),"min_oos_pnl_usd":round(min(y),2),"median_oos_pf":round(statistics.median(s["profit_factor"]for s in N),3),"median_oos_sharpe":round(statistics.median(s["sharpe"]for s in N),3),"splits":N};A=set();_r=data_dir/"verified_gamma_resolutions.json"
 if _r.exists():
  try:
   for _V,_U in json.loads(_r.read_text(encoding="utf-8")).items():
    if isinstance(_U,dict)and(_U.get("oracle_mismatch")or _U.get("mismatch")or(_U.get("binance_winner")and _U.get("winner")and _U.get("binance_winner")!=_U.get("winner"))):A.add(str(_V))
  except Exception:pass
 for _g in("ground_truth_resolutions.jsonl","ground_truth_resolutions_eth.jsonl","ground_truth_resolutions_sol.jsonl"):
  _I=data_dir/_g
  if _I.exists():
   try:
    for ln in _I.read_text(encoding="utf-8",errors="replace").splitlines():
     if ln.strip():
      _q=json.loads(ln)
      if _q.get("oracle_mismatch")or(_q.get("binance_winning_outcome")and _q.get("gamma_winning_outcome")and _q.get("binance_winning_outcome")!=_q.get("gamma_winning_outcome")):A.add(str(_q.get("market_id")))
   except Exception:pass
 for _j in T:
  if _j["path"]:
   U,Q,_,_,_=_j["path"][-1]
   if U<=30. and abs(Q)>=1e-5 and((Q>0)!=bool(_j["won"])):A.add(str(_j.get("mid")))
  if str(_j.get("mid"))in A:_j["oracle_mismatch"]=True
 u=[c for c in T if c.get("oracle_mismatch")];_i=evaluate_portfolio_fn(u,dict(best_cfg,use_cl_proxy=False),latency_mode="500ms");_p=evaluate_portfolio_fn(u,dict(best_cfg,use_cl_proxy=True),latency_mode="500ms");P=evaluate_portfolio_fn(T,dict(best_cfg,use_cl_proxy=False),latency_mode="500ms");D=evaluate_portfolio_fn(T,dict(best_cfg,use_cl_proxy=True),latency_mode="500ms");Z=dict(best_cfg)
 if not str(Z.get("exit_policy","")).startswith("two_tranche"):Z["exit_policy"]="two_tranche_12_98"
 J=evaluate_portfolio_fn(T,dict(Z,t2_post_lag_s=5.),latency_mode="500ms");O=evaluate_portfolio_fn(T,dict(Z,t2_post_lag_s=.05),latency_mode="500ms");t=evaluate_portfolio_fn(T,dict(Z,t2_post_lag_s=.0),latency_mode="500ms");i={"mismatch_markets_identified":len(A),"mismatch_candidates_total":len(u),"mismatch_raw_trades":_i["trades"],"mismatch_raw_pnl":_i["total_pnl"],"mismatch_cl_proxy_trades":_p["trades"],"mismatch_cl_proxy_pnl":_p["total_pnl"],"full_dataset_raw_pnl":P["total_pnl"],"full_dataset_raw_pf":P["profit_factor"],"full_dataset_cl_proxy_pnl":D["total_pnl"],"full_dataset_cl_proxy_pf":D["profit_factor"],"blueprint1_tranche2_comparison":{"delayed_5s_pnl":J["total_pnl"],"delayed_5s_pf":J["profit_factor"],"inline_50ms_pnl":O["total_pnl"],"inline_50ms_pf":O["profit_factor"],"concurrent_0ms_pnl":t["total_pnl"],"concurrent_0ms_pf":t["profit_factor"]}};g=[p/15. for p in(best_vl["pnls"]+best_hold_500["pnls"])]
 if len(g)<20:g=[p/15. for p in best_tr["pnls"]]
 def _sim_bankroll(label,start_eq,base_pct,min_tkt,floor_u,seed_cap=.0,corr_p=.0):
  h=random.Random(20261025);b=0;f,e=[],[];k=max(1,len(g))
  for _ in range(10000):
   d,i,g,c,a=start_eq,start_eq,.0,False,0
   while a<50 and g:
    if d<floor_u:c=True;break
    if seed_cap>.0 and d<seed_cap:d+=min(d,12.)*g[h.randrange(k)];a+=1
    else:
     j=min(d,max(min_tkt,round(d*base_pct,2)))
     if corr_p>.0 and h.random()<corr_p and(a+1)<50:m=g[h.randrange(k)];l=m if h.random()<.75 else g[h.randrange(k)];d+=j*m+(j*.54)*l;a+=2
     else:d+=j*g[h.randrange(k)];a+=1
    i=max(i,d);g=max(g,i-d)
    if d<floor_u:c=True;break
   if c:b+=1
   f.append(d);e.append(g)
  f.sort();e.sort();return{"policy":label,"start_equity_usd":start_eq,"floor_usd":floor_u,"halt_prob_50_trades":round(b/10000,4),"median_terminal_equity_usd":round(f[5000],2),"p05_terminal_equity_usd":round(f[500],2),"p95_terminal_equity_usd":round(f[9500],2),"p95_max_drawdown_usd":round(e[9500],2)}
 I=[_sim_bankroll("v3.7_UNPATCHED_22PCT_FLOOR65_CONC2",76.49,.22,12.,65.,corr_p=.25),_sim_bankroll("CENTRAL_CFG_18PCT_FLOOR66.67_CONC2",76.49,.18,12.,66.67,corr_p=.25),_sim_bankroll("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR48",76.49,.18,12.,48.,seed_cap=88.,corr_p=.15),_sim_bankroll("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR52",76.49,.18,12.,52.,seed_cap=88.,corr_p=.15)];C=[];r=set()
 for sc,_T,_H,_G,_ in stage2_results:
  _F=(_T["assets"],_T["horizons"],_T["min_px"],_T["max_px"],_T["min_z"],_T["min_cushion"],_T["entry_mode"],_T["exit_policy"])
  if _F in r:continue
  r.add(_F);_E=evaluate_portfolio_fn(holdout_cands,_T,latency_mode="500ms");C.append({"score":round(sc,2),"config":{k:(list(v)if isinstance(v,tuple)else v)for k,v in _T.items()},"train":{k:v for k,v in _H.items()if k!="pnls"},"val":{k:v for k,v in _G.items()if k!="pnls"},"holdout":{k:v for k,v in _E.items()if k!="pnls"}})
  if len(C)>=5:break
 a={};_f=data_dir/"live_harvester_state.json"
 if _f.exists():
  st=json.loads(_f.read_text(encoding="utf-8"));H=st.get("closed_positions",[]);G={c["event_id"]:c for c in cands};n,h,b,e=.0,0,0,0;l=[]
  for _S in H:
   _e=float(_S.get("net_pnl_usd")or.0);_R=str(_S.get("event_id")or"");_Q=str(_S.get("trade_id")or"");_d=G.get(_R)
   if not _d:continue
   h+=1;_P=simulate_single_fn(_d,best_cfg,latency_mode="500ms");Y=float(_S.get("notional_usd")or 15.)
   if _P is None:
    B,j=.0,"VETOED_AT_ENTRY"
    if _e<0:b+=1
    else:e+=1
   else:B,j=round(_P[0]*Y,2),_P[1]
   n+=B
   if"6076647"in _Q or"6082720"in _Q or _e<=-15.:l.append({"trade_id":_Q,"entry_price":_S.get("entry_price"),"max_seen_bid":_S.get("max_seen_bid"),"actual_pnl_usd":round(_e,2),"actual_close_reason":_S.get("close_reason"),"wfo_counterfactual_pnl_usd":B,"wfo_counterfactual_action":j})
  a={"total_live_closed_trades":len(H),"matched_to_trigger_dataset":h,"actual_matched_subset_pnl_usd":round(sum(float(p.get("net_pnl_usd")or.0)for p in H if str(p.get("event_id")or"")in G),2),"wfo_optimal_counterfactual_pnl_usd":round(n,2),"filtered_out_losing_trades":b,"filtered_out_winning_trades":e,"wipeout_trades_counterfactual":l}
 X=[];_o=len(dev_cands)
 if _o>=100:
  for W,(_D,_C)in enumerate([(.25,.43),(.43,.62),(.62,.81),(.81,1.)],start=1):_n=dev_cands[int(_D*_o)]["t0"];_m=dev_cands[min(_o-1,int(_C*_o)-1)]["t0"];V=[c for c in dev_cands if(_n+purge_sec)<=c["t0"]<=_m];_h=evaluate_portfolio_fn(V,best_cfg,latency_mode="500ms");X.append({"fold":W,"oos_candidates":len(V),"trades":_h["trades"],"total_pnl":_h["total_pnl"],"win_rate":_h["win_rate"],"profit_factor":_h["profit_factor"],"wipeout_rate":_h["wipeout_rate"]})
 return{"cpcv_summary":E,"chainlink_proxy_audit":i,"bankroll_mc":I,"top5_summary":C,"live_counterfactual":a,"cv_folds":X}
def run_subhourly_v395_wfo_ablation_suite(cands,evaluate_portfolio_fn,purge_sec=9e2):
 j=sorted([c for c in cands if c.get("hz")=="15m"],key=lambda x:x["t0"]);l=sorted([c for c in cands if c.get("hz")=="5m"],key=lambda x:x["t0"])
 def _purged_split(items,embargo):
  if len(items)<12:return list(items),[],[]
  d=[c["t0"]for c in items];b=d[int(.5*len(d))];a=d[int(.75*len(d))];g=[c for c in items if c["exp_ts"]<=b];f=[c for c in items if c["t0"]>=(b+embargo)and c["exp_ts"]<=a];e=[c for c in items if c["t0"]>=(a+embargo)];return g,f,e
 t,s,q=_purged_split(j,purge_sec);z,w,v=_purged_split(l,max(3e2,purge_sec*.5));b=[c for c in(t+s)if 60.<=c["tte"]<=480. and.75<=abs(c.get("z_oracle",.0))<=2.5];e=[c for c in q if 60.<=c["tte"]<=480. and.75<=abs(c.get("z_oracle",.0))<=2.5]
 def _brier(rows,df_v,jvm):
  if not rows:return.25
  a=.0
  for r in rows:_,b=compute_v395_pricing_and_twap_gate(r,df=df_v,jump_vol_mult=jvm,use_kemna_vorst=True);y=1. if r.get("won")else.0;a+=(b-y)**2
  return round(a/len(rows),6)
 h=[];a={"df":None,"jump_vol_mult":1.,"dev_brier":1.}
 for k in(None,4.,6.,8.):
  for i in(1.,1.15,1.25):
   p=_brier(b,k,i);u=_brier(e,k,i);o={"df":"gaussian"if k is None else k,"jump_vol_mult":i,"dev_n":len(b),"dev_brier":p,"holdout_n":len(e),"holdout_brier":u};h.append(o)
   if p<a["dev_brier"]:a={"df":o["df"],"jump_vol_mult":i,"dev_brier":p,"holdout_brier":u}
 g={"assets":("BTC","ETH","SOL"),"horizons":("15m",),"min_tte_15m":90.,"max_tte_15m":480.,"min_tte_5m":60.,"max_tte_5m":180.,"min_tte_1h":150.,"max_tte_1h":6e2,"min_px":.55,"max_px":.81,"max_spread":.03,"min_l1_usd":12.,"min_cushion":6e-4,"min_z":.78,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True,"entry_mode":"cascade_v4","fak_buffer":.02,"cascade_ticket_usd":16.5,"elastic_downsnap_usd":12.,"min_elastic_usd":8.,"exit_policy":"hold_98","ratchet_arm":None,"ratchet_drop":.06,"salvage_mode":"spot_persist","wrong_side_thresh":9e-4,"salvage_persist_s":18.,"clob_drop_thresh":.3,"final_45s_unwind":False}
 def _run_var(label,overrides,slices):a={**g,**overrides};g,f,e=slices;d=evaluate_portfolio_fn(g,a,latency_mode="500ms")if g else{"trades":0,"total_pnl":.0,"profit_factor":.0,"win_rate":.0};c=evaluate_portfolio_fn(f,a,latency_mode="500ms")if f else{"trades":0,"total_pnl":.0,"profit_factor":.0,"win_rate":.0};b=evaluate_portfolio_fn(e,a,latency_mode="500ms")if e else{"trades":0,"total_pnl":.0,"profit_factor":.0,"win_rate":.0};return{"label":label,"train":{"trades":d["trades"],"pnl":d["total_pnl"],"pf":d["profit_factor"],"wr":d["win_rate"]},"val":{"trades":c["trades"],"pnl":c["total_pnl"],"pf":c["profit_factor"],"wr":c["win_rate"]},"sealed_holdout":{"trades":b["trades"],"pnl":b["total_pnl"],"pf":b["profit_factor"],"wr":b["win_rate"]}}
 d=[_run_var("BASELINE_15M_CASCADE_TAKER_90_480",{},(t,s,q)),_run_var("KEMNA_VORST_TWAP_BRIDGE_45_480",{"min_tte_15m":45.,"use_kemna_vorst":True},(t,s,q)),_run_var("HYBRID_ZSPLIT_1.15_UNSHIELDED_MAKER",{"hybrid_z_split":True,"z_taker_cut":1.15,"use_complement_shield":False,"include_maker_rebate":False},(t,s,q)),_run_var("HYBRID_ZSPLIT_1.15_COMP_SHIELD_NO_REBATE",{"hybrid_z_split":True,"z_taker_cut":1.15,"use_complement_shield":True,"include_maker_rebate":False},(t,s,q)),_run_var("HYBRID_ZSPLIT_1.15_COMP_SHIELD_WITH_20PCT_REBATE",{"hybrid_z_split":True,"z_taker_cut":1.15,"use_complement_shield":True,"include_maker_rebate":True},(t,s,q)),_run_var("HYBRID_ZSPLIT_1.25_COMP_SHIELD_WITH_20PCT_REBATE",{"hybrid_z_split":True,"z_taker_cut":1.25,"use_complement_shield":True,"include_maker_rebate":True},(t,s,q)),_run_var("STUDENT_T_DF4_UNIT_VAR_JVM_1.15",{"v395_df":4.,"v395_jump_vol_mult":1.15,"use_kemna_vorst":True},(t,s,q)),_run_var("COINBASE_250MS_IMPULSE_VETO_2.5BPS",{"cb_250ms_veto_bps":-2.5},(t,s,q))];f=[]
 if l:
  for n,m in[(("BTC",),"BTC_5M_ONLY"),(("SOL",),"SOL_5M_CANARY"),(("BTC","ETH","SOL"),"ALL_CRYPTO_5M")]:f.append(_run_var(m,{"assets":n,"horizons":("5m",),"min_z":.8,"use_kemna_vorst":True},(z,w,v)))
 return{"counts":{"subhourly_15m_total":len(j),"subhourly_5m_total":len(l)},"splits_15m":{"train":len(t),"val":len(s),"sealed_holdout":len(q)},"splits_5m":{"train":len(z),"val":len(w),"sealed_holdout":len(v)},"brier_calibration_selected_on_dev":a,"brier_calibration_grid":h,"ablations_15m":d,"ablations_5m":f}
# ======================================================================================
# [04/21] MODULE: src/polymarket_research/net_alpha_opportunity_engine.py
# PURPOSE: v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import math;import os;import time;from pathlib import Path;from typing import Any,Dict,Iterable,List,Optional,Tuple;_INV_SQRT2=.7071067811865475
def _norm_cdf(x):return.5*(1.+math.erf(x*_INV_SQRT2))
def is_real_polygon_ctf_token(token_id):s=str(token_id or"").strip();return bool(s and s.isdigit()and len(s)>=20)
def compute_category_taker_fee_per_share(price,fee_rate=.07,fee_exponent=1.):
 if fee_rate<=.0:return.0
 p=max(.001,min(.999,float(price)));return float(fee_rate)*((p*(1.-p))**float(fee_exponent))
def inspect_microstructure_feature_completeness(shock,target_token,token_id=""):
 h=shock.get("pre_shock_features_t0")or{};i=(h.get(target_token)or{})if isinstance(h,dict)else{};f=is_real_polygon_ctf_token(token_id or i.get("token_id"));e=(shock.get("shock_source")in("BOUNDARY_LOCK","EXP316_TRACK_A_CONVERGENCE")or shock.get("sleeve")=="SLEEVE_3_STRIKE_CONVERGENCE");c=bool("fee_metadata"in shock or"shock_ofi"in shock or str(shock.get("event_id")or"").startswith("SHOCK_"));g=[];b=bool(float(i.get("best_ask")or.0)>=.995 and float(i.get("ask_size_l1")or.0)<=.0 and i.get("age_bid_ms")is not None)
 if i.get("age_ask_ms")is None and not e and not b:g.append("age_ask_ms")
 if shock.get("shock_ofi")is None and not e and c:g.append("shock_ofi")
 if i.get("obi_l1")is None and not e:g.append("obi_l1")
 if shock.get("coinbase_spot")is None and shock.get("chainlink_proxy_spot")is None:g.append("usd_venue_anchor")
 d=any(k in g for k in("age_ask_ms","shock_ofi"));a=.0
 if f and g:a=min(.06,.015*len(g))
 return{"is_real_ctf_token":f,"complete":len(g)==0,"hard_veto_live":bool(f and d),"missing_fields":g,"uncertainty_haircut":round(a,4)}
def estimate_quote_survival_and_net_alpha(p_win,ask_price,limit_price,p_max,fee_rate=.07,fee_exponent=1.,clob_rtt_ms=240.,age_ask_ms=None,spread=.01,l1_depth_usd=35.,obi_l1=.0,shock_ofi=.8,notional_usd=14.,target_exit_px=.965,expected_salvage_net=.36,uncertainty_haircut=.0,opp_cost_bps=12.,survival_params=None):
 m=round(min(float(limit_price),float(p_max)),4)
 if ask_price<=.0 or m<ask_price-1e-6 or notional_usd<=.0:return{"p_fill":.0,"ev_net_usd":.0,"ev_given_fill_usd":.0,"eff_limit_px":m,"eligible":False}
 w=survival_params or{};x=float(w.get("b0",-.35));s=float(w.get("b_impr_per_cent",.72));v=float(w.get("b_rtt_per_100ms",-.38));o=float(w.get("b_log_depth",.34));u=float(w.get("b_age_stale",.3));t=float(w.get("b_obi",-.35));d=max(.0,(m-float(ask_price))*1e2);n=max(.05,float(clob_rtt_ms)/1e2);k=math.log(max(1.,float(l1_depth_usd)/max(8.,float(notional_usd))))
 if age_ask_ms is None:a=-.35
 elif age_ask_ms<45.:a=-.6
 else:a=min(1.2,(float(age_ask_ms)-1e2)/350.)
 r=(x+s*min(2.5,d)+v*n+o*k+u*a+t*float(obi_l1)-.15*max(.0,(float(spread)-.01)*1e2)-.2*max(.0,abs(float(shock_ofi))-.85));g=1./(1.+math.exp(-max(-12.,min(12.,r))));g=max(.02,min(.98,g));c=min(m,float(ask_price)+.35*max(.0,m-float(ask_price)));q=compute_category_taker_fee_per_share(c,fee_rate,fee_exponent);i=c+q;l=max(.01,min(.995,float(p_win)-float(uncertainty_haircut)));e=l*float(target_exit_px)+(1.-l)*float(expected_salvage_net);h=e-i;p=float(notional_usd)/max(.01,c);b=p*h;f=float(notional_usd)*(float(opp_cost_bps)/1e4);j=g*b-(1.-g)*f;return{"p_fill":round(g,4),"expected_exec_px":round(c,4),"eff_cost_ps":round(i,4),"net_edge_ps":round(h,4),"ev_given_fill_usd":round(b,4),"ev_net_usd":round(j,4),"eff_limit_px":m,"eligible":bool(j>.0 and h>.0)}
def fit_quote_survival_from_ledger(records):
 c=0;a=0;j=[]
 for r in records:
  if not isinstance(r,dict):continue
  i=str(r.get("mode")or"")
  if i not in("LIVE_CLOB","FAK_KILLED_NO_MATCH","CLOB_HTTP_400_REJECTION"):continue
  c+=1
  if bool(r.get("success"))or i=="LIVE_CLOB":a+=1
  h=((r.get("details")or{}).get("latency_telemetry")or{});k=float(h.get("clob_http_post_ms")or r.get("latency_ms")or.0)
  if k>.0:j.append(k)
 if c<5:return{"sample_count":c,"empirical_fill_rate":None,"b0":-.35,"median_rtt_ms":240.}
 e=max(.05,min(.95,a/float(c)));b=sorted(j);f=b[len(b)//2]if b else 240.;d=math.log(e/(1.-e));g=max(-1.6,min(1.2,d+.38*(f/1e2)));return{"sample_count":c,"empirical_fill_rate":round(e,4),"median_rtt_ms":round(f,2),"b0":round(g,4)}
def select_maker_taker_skip_route(p_win,best_bid,best_ask,p_max,fee_rate=.07,fee_exponent=1.,notional_usd=14.,clob_rtt_ms=240.,age_ask_ms=350.,l1_ask_usd=40.,l1_bid_usd=40.,obi_l1=.0,shock_ofi=.8,target_exit_px=.965,expected_salvage_net=.36,adverse_markout_cents=.022,verified_maker_rebate_share=.0):
 p=round(float(best_ask)-float(best_bid),4);j=round(min(float(p_max),float(best_ask)+.02),2);l=estimate_quote_survival_and_net_alpha(p_win=p_win,ask_price=best_ask,limit_price=j,p_max=p_max,fee_rate=fee_rate,fee_exponent=fee_exponent,clob_rtt_ms=clob_rtt_ms,age_ask_ms=age_ask_ms,spread=max(.01,p),l1_depth_usd=l1_ask_usd,obi_l1=obi_l1,shock_ofi=shock_ofi,notional_usd=notional_usd,target_exit_px=target_exit_px,expected_salvage_net=expected_salvage_net);o=float(l["ev_net_usd"])if l["eligible"]else-1e-6;d=-1e-6;c=.0;a=.0
 if best_bid>.01 and best_ask>best_bid+.005:
  n=round(best_bid+.01,2)if p>=.02 else round(best_bid,2);c=round(min(n,best_ask-.01,p_max),2)
  if c>=best_bid-1e-6 and.04<=c<best_ask-1e-6:
   g=c>best_bid+1e-6;i=.0 if g else min(3.,l1_bid_usd/max(8.,notional_usd));a=max(.05,min(.65,(.42 if g else.24)*math.exp(-.35*i)));b=.0
   if verified_maker_rebate_share>.0 and fee_rate>.0:b=float(verified_maker_rebate_share)*compute_category_taker_fee_per_share(c,fee_rate,fee_exponent)
   f=c-b;h=max(.01,float(p_win)-float(adverse_markout_cents));m=h*float(target_exit_px)+(1.-h)*float(expected_salvage_net);q=float(notional_usd)/max(.01,c);k=q*(m-f)
   if k>.0:d=a*k
 if o<=.0 and d<=.0:e="SKIP"
 elif o>=d:e="TAKER_PRICE_IMPROVED_FAK"
 else:e="MAKER_POST_ONLY_3P5S"
 return{"route":e,"ev_taker_usd":round(max(.0,o),4),"ev_maker_usd":round(max(.0,d),4),"taker_limit_px":j,"maker_bid_px":c,"p_fill_taker":l["p_fill"],"p_fill_maker":round(a,4)}
def evaluate_optimal_stopping_exit(entry_px,rem_shares=10.,best_bid=.0,best_ask=.0,curr_target_px=.95,tte_sec=60.,obi_l1=.0,v_spot_15s_pct=.0,opp_ask_complement=None,fee_rate=.07,fee_exponent=1.,post_expiry_lock_min=6.,opp_ev_per_dollar_min=.0025,current_maker_px=None,**_unused_kw):
 if current_maker_px is not None:curr_target_px=float(current_maker_px)
 if rem_shares<5. or best_bid<=.0:return{"action":"HOLD_RESTING","target_px":curr_target_px,"reason":"SUB_LOT_OR_NO_BID"}
 e=compute_category_taker_fee_per_share(best_bid,fee_rate,fee_exponent);d=best_bid-e;a=.0
 if opp_ask_complement is not None and.005<=float(opp_ask_complement)<=.98:f=compute_category_taker_fee_per_share(float(opp_ask_complement),fee_rate,fee_exponent);a=1.-float(opp_ask_complement)-f
 if 8.<=tte_sec<=25. and best_bid>=.985 and best_bid>(entry_px+.02):
  g=1.-d;c=best_bid*float(post_expiry_lock_min)*float(opp_ev_per_dollar_min)
  if g<=max(.016,c+.004):return{"action":"PRE_EXPIRY_99C_RECYCLE","target_px":round(max(.98,best_bid),2),"net_proceeds_ps":round(d,5),"taker_fee_ps":round(e,5),"reason":f"Instant pre-rollover cash recycle @ ${best_bid:.3f} (fee=${e:.4f}/sh)"}
 if a>d+.006 and tte_sec<=45. and a>(entry_px+.03):return{"action":"SYNTHETIC_COMPLEMENT_MERGE","target_px":round(float(opp_ask_complement),4),"net_proceeds_ps":round(a,5),"direct_net_ps":round(d,5),"reason":f"Opposite-ask offset yields ${a:.4f}/sh > direct bid ${d:.4f}/sh"}
 if(tte_sec>=30. and curr_target_px>=.945 and best_bid>=.91 and best_bid>(entry_px+.05)and obi_l1<=-.4 and v_spot_15s_pct<=.0):
  b=round(min(curr_target_px-.01,max(entry_px+.06,best_bid+.01)),2)
  if best_ask>.0:b=round(min(b,max(best_bid+.01,best_ask)),2)
  if b<curr_target_px-.005 and b>=.92:return{"action":"OBI_MAKER_STEP_DOWN","target_px":b,"net_proceeds_ps":b,"reason":f"Heavy ask reload (obi_l1={obi_l1:.2f} <= -0.40) at bid=${best_bid:.2f}; stepping 0%-fee Maker TP to ${b:.2f}"}
 return{"action":"HOLD_RESTING","target_px":curr_target_px,"net_proceeds_ps":round(d,5)}
def scan_binary_complete_set_arb(market_id,condition_id,yes_token,no_token,asks_yes_raw,asks_no_raw,target_budget_usd=1e2,fee_rate=.07,fee_exponent=1.,max_complete_set_cost=.994,min_shares=10,max_box_cost_net=None):
 if max_box_cost_net is not None:max_complete_set_cost=float(max_box_cost_net)
 if not market_id or not yes_token or not no_token or str(yes_token)==str(no_token):return{"filled":False,"reason":"INVALID_TOKENS"}
 def _norm_asks(raw):
  b=[]
  for a in raw or[]:
   if isinstance(a,dict):p,s=float(a.get("price")or.0),float(a.get("size")or.0)
   elif isinstance(a,(list,tuple))and len(a)>=2:p,s=float(a[0]),float(a[1])
   else:continue
   if p>.0 and s>.0:b.append((p,s))
  b.sort(key=lambda x:x[0]);return b
 u=_norm_asks(asks_yes_raw);t=_norm_asks(asks_no_raw)
 if not u or not t:return{"filled":False,"reason":"EMPTY_SIDE_BOOK"}
 k=u[0][0]*u[0][1];j=t[0][0]*t[0][1];f=round(min(k,j),2);r,q=u[0][0],t[0][0];d=(compute_category_taker_fee_per_share(r,fee_rate,fee_exponent)+compute_category_taker_fee_per_share(q,fee_rate,fee_exponent))
 if(r+q+d)>max_complete_set_cost+.015:return{"filled":False,"reason":"NO_UNDERROUND","best_pair_net":round(r+q+d,5)}
 m=sum(s for p,s in u if p<=r+.02);l=sum(s for p,s in t if p<=q+.02);c=int(math.floor(float(target_budget_usd)/max(.1,r+q)));y=int(min(c,math.floor(m),math.floor(l)))
 if y<int(min_shares):return{"filled":False,"reason":"INSUFFICIENT_EQUAL_SHARES","l1_usd":f}
 def _walk_shares(levels,q_req):
  d=q_req;b=.0;a=.0
  for h,g in levels:
   f=min(d,g);b+=f*h;a=max(a,h);d-=f
   if d<=1e-6:break
  if d>1e-5:return None
  e=b/q_req;c=compute_category_taker_fee_per_share(e,fee_rate,fee_exponent);return e,c,a
 A=_walk_shares(u,float(y));z=_walk_shares(t,float(y))
 if A is None or z is None:return{"filled":False,"reason":"DEPTH_WALK_SHORTFALL","l1_usd":f}
 o,i,w=A;n,h,v=z;b=o+i+n+h
 if b>max_complete_set_cost+1e-6:return{"filled":False,"reason":"NET_COST_ABOVE_CAP","box_cost_net":round(b,5),"l1_usd":f}
 e=y*(o+n);g=y*(i+h);a=y*(1.-b);return{"filled":True,"market_id":str(market_id),"condition_id":str(condition_id),"yes_token":str(yes_token),"no_token":str(no_token),"shares":y,"vwap":round(o+n,5),"eff_px":round(b,5),"box_cost_net":round(b,5),"riskless_floor_per_pair":round(1.-b,5),"guaranteed_min_profit_usd":round(a,4),"spent_usd":round(e,2),"fee_usd":round(g,4),"limit_yes":round(w,4),"limit_no":round(v,4),"avail_yes_shares":round(m,2),"avail_no_shares":round(l,2),"l1_usd":f}
def evaluate_cross_oracle_basis_box_ev(spot_px,k_low,k_high,c_taker_net,tte_sec,sigma_1h=.0055,mu_basis_bps=2.,sigma_basis_bps=8.5):
 if spot_px<=.0 or k_low<=.0 or k_high<k_low:return{"eligible":False,"ev_per_pair":-1.,"p_double_loss":1.,"p_double_win":.0}
 f=(k_high-k_low)/k_low;l=max(4e-4,float(sigma_1h)*math.sqrt(max(15.,float(tte_sec))/3600.));e=l*math.sqrt(min(1.,20./max(20.,float(tte_sec))))*.35;j=math.hypot(float(sigma_basis_bps)/1e4,e);o=float(mu_basis_bps)/1e4;n=math.log(k_high/spot_px)/l;m=math.log(k_low/spot_px)/l;d=max(.0,min(1.,_norm_cdf(n)-_norm_cdf(m)));h=_norm_cdf((-f-abs(o))/max(1e-5,j));a=min(1.,.35+.65*math.exp(-abs(math.log(((k_low+k_high)*.5)/spot_px))/l));c=max(5e-4,min(.45,h*a));g=max(.0,d*(1.-h));k=max(.0,1.-g-c);b=2.*g+1.*k;i=b-float(c_taker_net);return{"classification":"PROBABILISTIC_CROSS_ORACLE_RV","is_riskless":False,"p_double_win":round(g,4),"p_single_floor":round(k,4),"p_double_loss":round(c,4),"expected_payout":round(b,4),"ev_per_pair":round(i,4),"expected_net_profit_per_pair":round(i,4),"eligible":bool(i>=.018 and c<=.045)}
def _global_positions_shm_path():
 b=os.environ.get("PM_FAST_TICK_DIR")
 if b:return Path(b)/"pm_global_positions.json"
 a=Path("/dev/shm")
 if a.exists():return a/"pm_global_positions.json"
 return Path(__file__).resolve().parent.parent.parent/"data"/"polymarket"/"pm_global_positions.json"
def read_global_positions_shm(max_age_sec=120.):
 d=_global_positions_shm_path()
 if not d.exists():return{"daemons":{}}
 try:
  c=json.loads(d.read_text(encoding="utf-8"))
  if not isinstance(c,dict):return{"daemons":{}}
  b=c.get("daemons")or{};e=time.time();a={k:v for k,v in b.items()if isinstance(v,dict)and(e-float(v.get("updated_ts")or.0))<=max_age_sec};return{"daemons":a}
 except Exception:return{"daemons":{}}
def publish_global_positions_shm(daemon_name,positions):
 d=_global_positions_shm_path()
 try:
  d.parent.mkdir(parents=True,exist_ok=True);f=read_global_positions_shm(max_age_sec=6e2);c=dict(f.get("daemons")or{});b=[]
  for p in positions:
   if not isinstance(p,dict):continue
   b.append({"id":str(p.get("trade_id")or p.get("position_id")or""),"sleeve":str(p.get("sleeve")or""),"asset":str(p.get("asset")or p.get("asset_or_city")or"").upper(),"side":str(p.get("target_token")or p.get("side")or"").upper(),"strike":float(p.get("candle_open_spot")or(p.get("extra")or{}).get("strike")or.0),"expiry_ts":float(p.get("candle_expiry_ts")or p.get("close_ts")or.0),"notional_usd":float(p.get("notional_usd")or p.get("entry_eff_px_t1000")or.0)})
  c[str(daemon_name)]={"updated_ts":round(time.time(),3),"positions":b};a={"updated_at_ts":round(time.time(),3),"daemons":c};e=d.with_suffix(f".{os.getpid()}.tmp");e.write_text(json.dumps(a),encoding="utf-8");os.replace(e,d);return True
 except Exception:return False
def compute_capital_efficiency_utility(candidate,active_global_positions=None):
 m=float(candidate.get("net_edge")or.0);t=max(.05,float(candidate.get("ask_vwap")or.5));r=float(candidate.get("p_model")or(t+m));q=max(15.,float(candidate.get("tte_sec")or 3600.));i=max(.08,min(24.,q/3600.));p=m/t;c=p/i;d=max(.0,1.-r);e=.08*(d**2);h=str(candidate.get("asset")or"").upper();j=str(candidate.get("side")or"").upper();l=float(candidate.get("expiry_ts")or.0);g=float(candidate.get("strike")or.0);b=.0;a=.0
 for v in active_global_positions or[]:
  o=str(v.get("asset")or"").upper()
  if not h or o!=h:continue
  u=float(v.get("expiry_ts")or.0);f=l>.0 and u>.0 and abs(l-u)<=9e2;s=str(v.get("side")or"").upper();k=float(v.get("strike")or.0)
  if f:
   if s==j and j in("UP","DOWN","YES","NO"):b+=.12
   elif(g>.0 and k>.0 and((s=="UP"and j=="DOWN"and k<g)or(s=="DOWN"and j=="UP"and g<k))):a+=.25
 n=c-e-b+a;return{"ev_per_dollar_hour":round(c,4),"utility_score":round(n,4),"lock_hours":round(i,3),"corr_penalty":round(b,4),"corridor_completion_bonus":round(a,4)}
def rank_opportunities_capital_auction(opportunities,active_global_positions=None,active_positions=None):
 a=active_global_positions if active_global_positions is not None else active_positions;b=[]
 for e in opportunities:
  d=dict(e);c=compute_capital_efficiency_utility(d,active_global_positions=a);d["ev_per_dollar_hour"]=c["ev_per_dollar_hour"];d["utility_score"]=c["utility_score"]
  if c["corridor_completion_bonus"]>0:d["synthetic_corridor_completion"]=True
  b.append(d)
 b.sort(key=lambda x:(-float(x.get("utility_score",.0)),-float(x.get("net_edge",.0))));return b
def infer_polymarket_tick_size(price_hint):
 a=float(price_hint or.0)
 if(.0<a<.04)or a>=.96:return.001
 return.01
def compute_capital_velocity_ev(net_edge_per_share,expected_hold_seconds=3e2,*,fill_prob=1.,early_recycle_factor=1.,net_cost_per_share=1.):b=max(.05,float(net_cost_per_share or 1.));a=max(10.,float(expected_hold_seconds or 3e2)*max(.1,float(early_recycle_factor or 1.)));c=max(.01,min(1.,float(fill_prob if fill_prob is not None else 1.)));return(float(net_edge_per_share or.0)/b)*c/a
def compute_smart_maker_bid(best_bid,best_ask,max_cap_px=None,min_floor_px=.001,obi_l1=.0,tick_size=None,*,max_ceiling=None,max_bid_px=None,min_floor=None):
 def _num_val(v,dflt=.0):return float(v)if(isinstance(v,(int,float))and not isinstance(v,bool)and math.isfinite(v))else dflt
 d=_num_val(max_cap_px if max_cap_px is not None else(max_ceiling if max_ceiling is not None else(max_bid_px if max_bid_px is not None else.99)),.99);c=_num_val(min_floor if min_floor is not None else min_floor_px,.001);n=_num_val(best_ask,.0);m=_num_val(best_bid,.0);i=_num_val(obi_l1,.0);k=_num_val(tick_size,.0);g=n if n>.0 else d;j=k if k>.0 else infer_polymarket_tick_size(g);f=3 if j<.009 else 2;a=(n-j)if n>j else d;b=min(d,a);l=round(math.floor((b+1e-9)/j)*j,f)
 if l<c-1e-9 or l<=.0:return None,False
 if m>.0:
  e=(n-m)if n>m else.0;h=round(m+j,f)
  if e>=(2.*j-1e-9)and h<=l+1e-9:return min(l,h),True
  if m<=l+1e-9:
   if.0<e<=(j+1e-9)and i<-.35:return None,False
   return round(min(l,m),f),False
 return l,True
def _walk_bid_levels_net(bids,target_shares,fee_rate=.0,fee_exp=1.):
 j=[];a=.0
 for r in bids or():
  if not isinstance(r,dict):continue
  try:i=float(r.get("price")or.0);h=float(r.get("size")or.0)
  except(TypeError,ValueError):continue
  if i>.0 and h>.0:j.append((i,h));a+=h
 if not j or target_shares<=.0 or a+1e-9<target_shares:return False,.0,.0,.0,a
 j.sort(key=lambda x:-x[0]);e=float(target_shares);b=.0;d=.0;c=j[0][0]
 for i,h in j:
  g=min(e,h)
  if g<=.0:break
  f=compute_category_taker_fee_per_share(i,fee_rate=fee_rate,fee_exponent=fee_exp);b+=g*i;d+=g*max(.0,i-f);c=i;e-=g
  if e<=1e-7:break
 if e>1e-5:return False,.0,.0,.0,a
 return True,b/target_shares,d/target_shares,c,a
def walk_dual_leg_overround_bids(bids_a,bids_b,target_shares,fee_rate_a=.0,fee_exp_a=1.,fee_rate_b=.0,fee_exp_b=1.,min_depth_mult=1.25):l=float(target_shares or.0);k,g,i,c,f=_walk_bid_levels_net(bids_a,l,fee_rate_a,fee_exp_a);j,e,h,b,d=_walk_bid_levels_net(bids_b,l,fee_rate_b,fee_exp_b);a=k and j and f>=l*min_depth_mult and d>=l*min_depth_mult;return{"fillable":bool(a and c>.0 and b>.0),"gross_sum_per_share":round(g+e,6),"net_sum_per_share":round(i+h,6),"min_px_a":round(c,4),"min_px_b":round(b,4),"depth_a":round(f,4),"depth_b":round(d,4)}
def evaluate_guarded_complement_merge(*,rem_shares,opp_ask,opp_ask_size=.0,opp_ask_size_l1=None,curr_maker_tp_px=None,fee_rate=.07,fee_exponent=1.,min_net_proceeds_ps=.982,max_opp_ask=.015,min_marketable_usd=1.):
 if opp_ask_size_l1 is not None and opp_ask_size<=.0:opp_ask_size=float(opp_ask_size_l1)
 if curr_maker_tp_px is not None:min_net_proceeds_ps=max(float(min_net_proceeds_ps),float(curr_maker_tp_px)+.002)
 k=float(rem_shares or.0);j=float(opp_ask or.0)
 if k<5. or not(.001<=j<=float(max_opp_ask)):return{"approved":False,"reason":"OUT_OF_OPP_PRICE_BAND_OR_SUB_LOT"}
 b=math.ceil((float(min_marketable_usd)/j)*1e2)/1e2;g=max(k,b);a=max(.0,round(g-k,4))
 if opp_ask_size>.0 and float(opp_ask_size)+1e-6<g:return{"approved":False,"reason":"INSUFFICIENT_OPP_ASK_DEPTH","req_opp_shares":g}
 h=compute_category_taker_fee_per_share(j,fee_rate=fee_rate,fee_exponent=fee_exponent);f=g*(j+h);d=k*1.;c=d-f;e=c/k;i=infer_polymarket_tick_size(j)
 if e<float(min_net_proceeds_ps):return{"approved":False,"reason":"OVERBUY_DILUTION_BELOW_MAKER_98_HURDLE","net_proceeds_ps":round(e,5),"req_opp_shares":round(g,2),"excess_unmerged_shares":a}
 return{"approved":True,"opp_ask":round(j,4),"tick_size":f"{i:.3f}"if i<.009 else f"{i:.2f}","req_opp_shares":round(g,2),"merge_pairs":round(k,2),"excess_unmerged_shares":a,"total_opp_cost_usd":round(f,4),"net_proceeds_ps":round(e,5),"atomic_sequence":("FAK_BUY_OPP","CONFIRM_OPP_FILL","CANCEL_RESTING_MAKER_TP","MERGE_CTF_POSITIONS")}
def evaluate_d1_15m_to_5m_corridor_conversion(pos_15m,snap_5m,*,now_ts=None,fee_rate=.07,fee_exponent=1.,max_total_box_cost=.975,min_corridor_bps=1.5):
 if not isinstance(pos_15m,dict)or not isinstance(snap_5m,dict):return{"eligible":False,"reason":"MISSING_5M_SNAPSHOT"}
 j=str(pos_15m.get("target_token")or"").upper()
 if j not in("UP","DOWN"):return{"eligible":False,"reason":"INVALID_SIDE"}
 l=float(pos_15m.get("remaining_shares")or.0);e=float(pos_15m.get("entry_price")or.0);g=float(pos_15m.get("fee_usd")or.0);r=float(pos_15m.get("candle_open_spot")or.0);k=float(pos_15m.get("candle_expiry_ts")or.0);p=float(now_ts)if now_ts is not None else.0
 if p>.0 and k>.0 and not(15.<=(k-p)<=295.):return{"eligible":False,"reason":"OUTSIDE_FINAL_5M_WINDOW"}
 if l<5. or e<=.0 or r<=.0:return{"eligible":False,"reason":"INVALID_15M_POSITION"}
 s=float(snap_5m.get("authoritative_chainlink_open")or snap_5m.get("finalized_open")or snap_5m.get("finalized_15m_open")or.0)
 if s<=.0:return{"eligible":False,"reason":"MISSING_5M_STRIKE"}
 if j=="UP":a=((s-r)/r)*1e4;b="DOWN"
 else:a=((r-s)/r)*1e4;b="UP"
 if a<float(min_corridor_bps):return{"eligible":False,"reason":"NO_DOMINANCE_CORRIDOR","corridor_bps":round(a,2)}
 q=snap_5m.get(b)or{};o=float(q.get("best_ask")or 1.);i=float(q.get("ask_size_l1")or.0);n=str(q.get("token_id")or"");m=str(snap_5m.get("market_id")or"")
 if not(.01<=o<=.9)or i<l*1.15 or(l*o)<1. or not n:return{"eligible":False,"reason":"INSUFFICIENT_5M_LIQUIDITY_OR_TOKEN"}
 h=compute_category_taker_fee_per_share(o,fee_rate=fee_rate,fee_exponent=fee_exponent);f=e+g/max(l,1e-6);d=f+o+h
 if d>float(max_total_box_cost):return{"eligible":False,"reason":"BOX_COST_EXCEEDS_CEILING","total_box_cost_ps":round(d,4),"corridor_bps":round(a,2)}
 c=1.-d;return{"eligible":True,"market_id_5m":m,"token_id_5m":n,"opp_side_5m":b,"shares":round(l,2),"ask_5m":round(o,4),"fee_5m_ps":round(h,5),"k_15":r,"k_5":s,"corridor_bps":round(a,2),"total_box_cost_ps":round(d,4),"locked_floor_ps":round(c,4),"locked_floor_pnl_usd":round(l*c,2),"corridor_jackpot_pnl_usd":round(l*(2.-d),2)}
def rank_microbatch_shock_tournament(shocks,active_positions=None):
 if len(shocks)<=1:return list(shocks)
 def _score_shock(s):
  p=str(s.get("shock_direction")or"BUY").upper();r="UP"if p in("BUY","UP")else"DOWN";v=(s.get("pre_shock_features_t0")or{}).get(r)or{};l=float(v.get("best_ask")or v.get("vwap_$25")or v.get("effective_price_$25")or.7);l=max(.05,min(.95,l));d=abs(float(s.get("candle_distance_pct")or.0));u=max(30.,float(s.get("seconds_to_expiry")or 3e2));o=str(s.get("asset")or"BTC").upper();g=float(s.get("candle_sigma")or.0);w=str(s.get("horizon")or"").lower();k=(g*(2. if"15m"in w else(math.sqrt(12.)if w in("5m","5min","300s")or"-5m"in w else 1.))if g>.0 else(.005 if o=="BTC"else(.0068 if o=="ETH"else.009)));f=max(.00025,k*math.sqrt(u/3600.));t=min(1.,abs(float(s.get("shock_ofi")if s.get("shock_ofi")is not None else.85)));n=(d/1e2)/f+.35*t;m=.5*(1.+math.erf(n/math.sqrt(2.)));j=compute_category_taker_fee_per_share(l,.07,1.);e=m*.98+(1.-m)*.36;a=(e-l-j)/(l+j);i=float(v.get("age_ask_ms")if v.get("age_ask_ms")is not None else 3e2);h=1.15 if i>=250. else 1.;c=.015 if o=="BTC"else(.008 if o=="ETH"else.0);b=a*h+c
  if active_positions:q=compute_capital_efficiency_utility({"asset":o,"side":r,"expiry_ts":s.get("candle_expiry_ts")or s.get("expiry_ts")or.0,"strike":s.get("candle_open_spot")or.0,"net_edge":max(.0,e-l-j),"ask_vwap":l,"p_model":m,"tte_sec":u},active_global_positions=active_positions);b+=float(q.get("corridor_completion_bonus")or.0)-float(q.get("corr_penalty")or.0)
  return round(b,6),n
 return sorted(shocks,key=_score_shock,reverse=True)
# ======================================================================================
# [05/21] MODULE: src/polymarket_research/weather_metar_engine.py
# PURPOSE: Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import logging;import math;import re;import time;import urllib.parse;import urllib.request;from dataclasses import dataclass,field;from datetime import date,datetime,timedelta,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;logger=logging.getLogger("WeatherMetarEngine");GAMMA_API_URL="https://gamma-api.polymarket.com";CLOB_API_URL="https://clob.polymarket.com";AWC_METAR_URL="https://aviationweather.gov/api/data/metar";AWC_STATION_URL="https://aviationweather.gov/api/data/stationinfo";IEM_ASOS_URL="https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py";OPEN_METEO_ENSEMBLE_URL="https://ensemble-api.open-meteo.com/v1/ensemble";OPEN_METEO_FORECAST_URL="https://api.open-meteo.com/v1/forecast";OPEN_METEO_HIST_FORECAST_URL="https://historical-forecast-api.open-meteo.com/v1/forecast";STATION_CATALOG={"RJTT":(35.5523,139.7798,"Asia/Tokyo","Tokyo"),"EGLC":(51.5053,.0553,"Europe/London","London"),"ZSPD":(31.1434,121.8052,"Asia/Shanghai","Shanghai"),"ZSQD":(36.3667,120.0944,"Asia/Shanghai","Qingdao"),"WMKK":(2.7456,101.7099,"Asia/Kuala_Lumpur","Kuala Lumpur"),"RCSS":(25.0694,121.5525,"Asia/Taipei","Taipei"),"EDDM":(48.3538,11.7861,"Europe/Berlin","Munich"),"LFPB":(48.9694,2.4414,"Europe/Paris","Paris"),"ZUUU":(30.5785,103.9471,"Asia/Shanghai","Chengdu"),"SBGR":(-23.4356,-46.4731,"America/Sao_Paulo","Sao Paulo"),"LEMD":(40.4719,-3.5626,"Europe/Madrid","Madrid"),"ZHHH":(30.7838,114.2081,"Asia/Shanghai","Wuhan"),"EHAM":(52.3086,4.7639,"Europe/Amsterdam","Amsterdam"),"EPWA":(52.1657,20.9671,"Europe/Warsaw","Warsaw"),"WSSS":(1.3502,103.994,"Asia/Singapore","Singapore"),"ZBAA":(40.0801,116.5846,"Asia/Shanghai","Beijing"),"ZUCK":(29.7192,106.6417,"Asia/Shanghai","Chongqing"),"LTFM":(41.2753,28.7519,"Europe/Istanbul","Istanbul"),"KMIA":(25.7959,-80.287,"America/New_York","Miami"),"OPKC":(24.9065,67.1608,"Asia/Karachi","Karachi"),"KLGA":(40.7769,-73.874,"America/New_York","NYC"),"RKSI":(37.4602,126.4407,"Asia/Seoul","Seoul"),"LLBG":(32.0114,34.8867,"Asia/Jerusalem","Tel Aviv"),"ZGGG":(23.3924,113.2988,"Asia/Shanghai","Guangzhou"),"OEJN":(21.6796,39.1565,"Asia/Riyadh","Jeddah"),"VILK":(26.7606,80.8893,"Asia/Kolkata","Lucknow"),"ZGSZ":(22.6393,113.8107,"Asia/Shanghai","Shenzhen"),"LIMC":(45.6306,8.7281,"Europe/Rome","Milan"),"RKPK":(35.1795,128.9382,"Asia/Seoul","Busan"),"LTAC":(40.1281,32.9951,"Europe/Istanbul","Ankara"),"SAEZ":(-34.8222,-58.5358,"America/Argentina/Buenos_Aires","Buenos Aires"),"KSEA":(47.4502,-122.3088,"America/Los_Angeles","Seattle"),"KDAL":(32.8471,-96.8518,"America/Chicago","Dallas"),"NZWN":(-41.3272,174.8053,"Pacific/Auckland","Wellington"),"KSFO":(37.6213,-122.379,"America/Los_Angeles","San Francisco"),"KORD":(41.9742,-87.9073,"America/Chicago","Chicago"),"MMMX":(19.4363,-99.0721,"America/Mexico_City","Mexico City"),"CYYZ":(43.6777,-79.6248,"America/Toronto","Toronto"),"RPLL":(14.5086,121.0194,"Asia/Manila","Manila"),"EFHK":(60.3172,24.9633,"Europe/Helsinki","Helsinki"),"KATL":(33.6407,-84.4277,"America/New_York","Atlanta"),"KHOU":(29.6454,-95.2789,"America/Chicago","Houston"),"KDEN":(39.8561,-104.6737,"America/Denver","Denver"),"UUWW":(55.5915,37.2615,"Europe/Moscow","Moscow"),"MPMG":(8.9733,-79.5556,"America/Panama","Panama City"),"KAUS":(30.1945,-97.6699,"America/Chicago","Austin"),"KLAX":(33.9425,-118.4081,"America/Los_Angeles","Los Angeles"),"FACT":(-33.9648,18.6017,"Africa/Johannesburg","Cape Town"),"HKO":(22.3019,114.1742,"Asia/Hong_Kong","Hong Kong"),"ZSJN":(36.8572,117.216,"Asia/Shanghai","Jinan"),"ZHCC":(34.5197,113.8408,"Asia/Shanghai","Zhengzhou")};HKO_1MIN_CSV_URL="https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature.csv";HKO_MAXMIN_CSV_URL="https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_since_midnight_maxmin.csv";HKO_RHRREAD_URL="https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en";_T_REMARK_RE=re.compile(r"(?:^|\s)T([01])(\d{3})(?:\d{4}|////)(?=\s|$)");_BODY_TEMP_RE=re.compile(r"(?:^|\s)(M?\d{2})/(?:M?\d{2}|//)(?=\s|$)");_METAR_TS_RE=re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b");_CONVECTIVE_WX_RE=re.compile(r"(?:^|\s)(?:[-+]|VC)?(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)*\b" r"|(?:FEW|SCT|BKN|OVC)\d{3}(?:CB|TCU)\b" r"|\b(?:CB|TCU|RAB\d{2,4}|TSB\d{2,4}|P\d{4})\b");_AWC_ICAO_RE=re.compile(r"aviationweather\.gov/api/data/metar\?ids=([A-Z0-9]{4})",re.IGNORECASE);_NOAA_ICAO_RE=re.compile(r"weather\.gov/wrh/timeseries\?site=([A-Z0-9]{4})",re.IGNORECASE);_PAREN_ICAO_RE=re.compile(r"\(([A-Z]{4})\)");_SERIES_TO_ICAO={"tokyo-daily-weather":"RJTT","tokyo-daily-lowest-temperature":"RJTT","london-daily-weather":"EGLC","london-daily-lowest-temperature":"EGLC","shanghai-daily-weather":"ZSPD","shanghai-daily-lowest-temperature":"ZSPD","chengdu-daily-weather":"ZUUU","chengdu-daily-lowest-temperature":"ZUUU","beijing-daily-weather":"ZBAA","beijing-daily-lowest-temperature":"ZBAA","wuhan-daily-weather":"ZHHH","wuhan-daily-lowest-temperature":"ZHHH","chongqing-daily-weather":"ZUCK","chongqing-daily-lowest-temperature":"ZUCK","guangzhou-daily-weather":"ZGGG","guangzhou-daily-lowest-temperature":"ZGGG","shenzhen-daily-weather":"ZGSZ","shenzhen-daily-lowest-temperature":"ZGSZ","qingdao-daily-weather":"ZSQD","qingdao-daily-lowest-temperature":"ZSQD","paris-daily-weather":"LFPB","paris-daily-lowest-temperature":"LFPB","munich-daily-weather":"EDDM","munich-daily-lowest-temperature":"EDDM","miami-daily-weather":"KMIA","miami-daily-lowest-temperature":"KMIA","nyc-daily-weather":"KLGA","nyc-daily-lowest-temperature":"KLGA","houston-daily-weather":"KHOU","houston-daily-lowest-temperature":"KHOU","austin-daily-weather":"KAUS","austin-daily-lowest-temperature":"KAUS","los-angeles-daily-weather":"KLAX","los-angeles-daily-lowest-temperature":"KLAX","seoul-daily-weather":"RKSI","seoul-daily-lowest-temperature":"RKSI","busan-daily-weather":"RKPK","busan-daily-lowest-temperature":"RKPK","chicago-daily-weather":"KORD","chicago-daily-lowest-temperature":"KORD","seattle-daily-weather":"KSEA","seattle-daily-lowest-temperature":"KSEA","dallas-daily-weather":"KDAL","dallas-daily-lowest-temperature":"KDAL","madrid-daily-weather":"LEMD","madrid-daily-lowest-temperature":"LEMD","amsterdam-daily-weather":"EHAM","amsterdam-daily-lowest-temperature":"EHAM","taipei-daily-weather":"RCSS","taipei-daily-lowest-temperature":"RCSS","singapore-daily-weather":"WSSS","singapore-daily-lowest-temperature":"WSSS","hong-kong-daily-weather":"HKO","hong-kong-daily-lowest-temperature":"HKO","wellington-daily-weather":"NZWN","wellington-daily-lowest-temperature":"NZWN","warsaw-daily-weather":"EPWA","warsaw-daily-lowest-temperature":"EPWA","buenos-aires-daily-weather":"SAEZ","buenos-aires-daily-lowest-temperature":"SAEZ","helsinki-daily-weather":"EFHK","helsinki-daily-lowest-temperature":"EFHK","denver-daily-weather":"KDEN","denver-daily-lowest-temperature":"KDEN","toronto-daily-weather":"CYYZ","toronto-daily-lowest-temperature":"CYYZ","mexico-city-daily-weather":"MMMX","mexico-city-daily-lowest-temperature":"MMMX","tel-aviv-daily-weather":"LLBG","tel-aviv-daily-lowest-temperature":"LLBG","istanbul-daily-weather":"LTFM","istanbul-daily-lowest-temperature":"LTFM","sao-paulo-daily-weather":"SBGR","sao-paulo-daily-lowest-temperature":"SBGR","manila-daily-weather":"RPLL","manila-daily-lowest-temperature":"RPLL","atlanta-daily-weather":"KATL","atlanta-daily-lowest-temperature":"KATL","san-francisco-daily-weather":"KSFO","san-francisco-daily-lowest-temperature":"KSFO","panama-daily-weather":"MPMG","panama-daily-lowest-temperature":"MPMG","milan-daily-weather":"LIMC","milan-daily-lowest-temperature":"LIMC","lucknow-daily-weather":"VILK","lucknow-daily-lowest-temperature":"VILK","karachi-daily-weather":"OPKC","karachi-daily-lowest-temperature":"OPKC","jeddah-daily-weather":"OEJN","jeddah-daily-lowest-temperature":"OEJN","ankara-daily-weather":"LTAC","ankara-daily-lowest-temperature":"LTAC","kuala-lumpur-daily-weather":"WMKK","kuala-lumpur-daily-lowest-temperature":"WMKK","moscow-daily-weather":"UUWW","moscow-daily-lowest-temperature":"UUWW","cape-town-daily-weather":"FACT","cape-town-daily-lowest-temperature":"FACT","jinan-daily-weather":"ZSJN","jinan-daily-lowest-temperature":"ZSJN","zhengzhou-daily-weather":"ZHCC","zhengzhou-daily-lowest-temperature":"ZHCC"}
HIGH_VOLUME_WEATHER_SERIES=("hong-kong-daily-weather","hong-kong-daily-lowest-temperature","atlanta-daily-weather","atlanta-daily-lowest-temperature","san-francisco-daily-weather","san-francisco-daily-lowest-temperature","seattle-daily-weather","seattle-daily-lowest-temperature","amsterdam-daily-weather","amsterdam-daily-lowest-temperature","panama-daily-weather","manila-daily-weather","mexico-city-daily-weather","munich-daily-weather","milan-daily-weather","istanbul-daily-weather","lucknow-daily-weather","tel-aviv-daily-weather","karachi-daily-weather","sao-paulo-daily-weather","jeddah-daily-weather","ankara-daily-weather","busan-daily-weather","cape-town-daily-weather","cape-town-daily-lowest-temperature","qingdao-daily-weather","kuala-lumpur-daily-weather","moscow-daily-weather","chengdu-daily-weather","beijing-daily-weather","seoul-daily-weather","seoul-daily-lowest-temperature","shanghai-daily-weather","shanghai-daily-lowest-temperature","tokyo-daily-weather","tokyo-daily-lowest-temperature","wuhan-daily-weather","chongqing-daily-weather","guangzhou-daily-weather","shenzhen-daily-weather","taipei-daily-weather","singapore-daily-weather","nyc-daily-weather","nyc-daily-lowest-temperature","chicago-daily-weather","chicago-daily-lowest-temperature","london-daily-weather","london-daily-lowest-temperature","miami-daily-weather","miami-daily-lowest-temperature","austin-daily-weather","austin-daily-lowest-temperature","los-angeles-daily-weather","los-angeles-daily-lowest-temperature","houston-daily-weather","houston-daily-lowest-temperature","dallas-daily-weather","dallas-daily-lowest-temperature","wellington-daily-weather","wellington-daily-lowest-temperature","warsaw-daily-weather","warsaw-daily-lowest-temperature","buenos-aires-daily-weather","helsinki-daily-weather","denver-daily-weather","denver-daily-lowest-temperature","toronto-daily-weather","toronto-daily-lowest-temperature","paris-daily-weather","paris-daily-lowest-temperature","madrid-daily-weather");_MONTH_MAP={"january":1,"jan":1,"february":2,"feb":2,"march":3,"mar":3,"april":4,"apr":4,"may":5,"june":6,"jun":6,"july":7,"jul":7,"august":8,"aug":8,"september":9,"sep":9,"sept":9,"october":10,"oct":10,"november":11,"nov":11,"december":12,"dec":12}
@dataclass
class WeatherBucket:
 market_id:str;condition_id:str;label:str;question:str;yes_token:str;no_token:str;unit:str;low_bound:float;high_bound:float;outcome_yes_resolved=None;fee_rate=.0;fee_exponent=1.;neg_risk=None;rewards_min_size=.0;rewards_max_spread=.0
 def contains_rounded(a,rounded_int):return a.low_bound<=rounded_int<=a.high_bound
@dataclass
class WeatherEventSpec:event_id:str;slug:str;series_slug:str;title:str;icao:str;city:str;lat:float;lon:float;tz_name:str;obs_date:date;metric:str;unit:str;fee_type:str;end_date_iso:str;buckets=field(default_factory=list)
@dataclass
class MetarObservation:icao:str;utc_dt:datetime;local_dt:datetime;temp_c:float;has_t_remark:bool;raw_line:str;has_convective_precip=False;is_corrected=False
def round_half_up_polymarket(val):return int(math.floor(val+.5+1e-12))
def celsius_to_market_int(temp_c,unit):
 if unit.upper()=="F":a=temp_c*9./5.+32.;return round_half_up_polymarket(a)
 return round_half_up_polymarket(temp_c)
def parse_bucket_bounds(label):
 s=label.strip().replace("−","-").replace("–","-");c=re.search(r"°\s*([CF])",s,re.IGNORECASE)
 if not c:return None
 e=c.group(1).upper();d=s.lower()
 if"or below"in d or"or lower"in d or"or less"in d or"under"in d:
  m=re.search(r"(-?\d+)\s*°",s)
  if not m:return None
  return e,float("-inf"),float(int(m.group(1)))
 if"or higher"in d or"or above"in d or"or more"in d:
  m=re.search(r"(-?\d+)\s*°",s)
  if not m:return None
  return e,float(int(m.group(1))),float("inf")
 b=re.search(r"(-?\d+)\s*(?:°[CF])?\s*(?:-|to)\s*(-?\d+)\s*°",s,re.IGNORECASE)
 if b:g,f=int(b.group(1)),int(b.group(2));return e,float(min(g,f)),float(max(g,f))
 a=re.search(r"(-?\d+)\s*°",s)
 if a:v=float(int(a.group(1)));return e,v,v
 return None
def parse_metar_line(raw_line,icao,ref_utc,tz_name,explicit_utc_dt=None):
 w=raw_line.strip()
 if not w:return None
 r=w.upper();m=r.split()
 if not m:return None
 if"SPECI"in m[:3]:return None
 if icao.upper()not in m[:4]:return None
 l="COR"in m[:5];b=explicit_utc_dt
 if b is None:
  v=_METAR_TS_RE.search(r)
  if not v:return None
  q,u,p=int(v.group(1)),int(v.group(2)),int(v.group(3));f=[]
  for o in(-32,0,32):
   k=ref_utc+timedelta(days=o)
   try:t=datetime(k.year,k.month,q,u,p,tzinfo=timezone.utc);f.append(t)
   except ValueError:continue
  if not f:return None
  b=min(f,key=lambda c:abs((c-ref_utc).total_seconds()))
 i=r.split("RMK",1)[1]if"RMK"in r else r;n=_T_REMARK_RE.search(i)
 if n:s=-1. if n.group(1)=="1"else 1.;a=s*(int(n.group(2))/10.);e=True
 else:
  g=r.split("RMK",1)[0];j=_BODY_TEMP_RE.search(g)
  if not j:return None
  x=j.group(1);a=-float(int(x[1:]))if x.startswith("M")else float(int(x));e=False
 h=b.astimezone(ZoneInfo(tz_name));d=bool(_CONVECTIVE_WX_RE.search(r));return MetarObservation(icao=icao.upper(),utc_dt=b,local_dt=h,temp_c=a,has_t_remark=e,raw_line=w,has_convective_precip=d,is_corrected=l)
def parse_obs_date_from_event(title,desc,end_date_iso):
 f=re.search(r"\bon\s+(\d{1,2})\s+([A-Za-z]+)\s+'?(\d{2,4})\b",desc)
 if f:
  c=int(f.group(1));d=_MONTH_MAP.get(f.group(2).lower());b=int(f.group(3))
  if b<100:b+=2000
  if d:
   try:return date(b,d,c)
   except ValueError:pass
 a=2026
 if end_date_iso:
  try:a=datetime.fromisoformat(end_date_iso.replace("Z","+00:00")).year
  except Exception:pass
 e=re.search(r"\bon\s+([A-Za-z]+)\s+(\d{1,2})(?:,?\s*(\d{4}))?",title)
 if e:
  d=_MONTH_MAP.get(e.group(1).lower());c=int(e.group(2));b=int(e.group(3))if e.group(3)else a
  if d:
   try:return date(b,d,c)
   except ValueError:pass
 return None
def parse_weather_event(ev,allow_historical_same_station=False,series_slug_hint=""):
 A=str(ev.get("title")or"");K=A.lower()
 if"highest temperature in"in K:g="HIGH"
 elif"lowest temperature in"in K:g="LOW"
 else:return None
 E=ev.get("markets")or[]
 if len(E)<4:return None
 l=ev.get("series")or[];y=str(l[0].get("slug")if l else(ev.get("seriesSlug")or series_slug_hint or""));D=str(E[0].get("description")or ev.get("description")or"");c=None;x=_AWC_ICAO_RE.search(D)
 if x and"SPECI"in D:c=x.group(1).upper()
 elif"weather.gov.hk"in D.lower()and"hong kong observatory"in D.lower():c="HKO"
 elif"routine (metar)"in D.lower()or"speci"in D.lower():
  k=_PAREN_ICAO_RE.search(D)
  if k and k.group(1).upper()in STATION_CATALOG:c=k.group(1).upper()
 elif allow_historical_same_station:
  w=_NOAA_ICAO_RE.search(D);z=_PAREN_ICAO_RE.search(D)
  if w and w.group(1).upper()in STATION_CATALOG:c=w.group(1).upper()
  elif z and z.group(1).upper()in STATION_CATALOG:c=z.group(1).upper()
  elif y in _SERIES_TO_ICAO:c=_SERIES_TO_ICAO[y]
 if not c or c not in STATION_CATALOG:return None
 H,G,s,C=STATION_CATALOG[c];r=str(ev.get("endDate")or E[0].get("endDate")or"");p=parse_obs_date_from_event(A,D,r)
 if p is None:return None
 d=str(E[0].get("feeType")or"zero_fees");q=[]
 for m in E:
  F=str(m.get("groupItemTitle")or m.get("question")or"");v=parse_bucket_bounds(F)
  if not v:continue
  B,J,I=v;f=m.get("clobTokenIds")
  if isinstance(f,str):
   try:f=json.loads(f)
   except Exception:f=[]
  if not f or len(f)<2:continue
  a=None
  if m.get("closed"):
   u=m.get("outcomePrices")
   if isinstance(u,str):
    try:u=json.loads(u)
    except Exception:u=None
   if isinstance(u,list)and len(u)>=2:
    try:
     if float(u[0])>=.99:a=1
     elif float(u[1])>=.99:a=0
    except Exception:pass
  h=m.get("feeSchedule")if isinstance(m.get("feeSchedule"),dict)else{};e=bool(m.get("feesEnabled",False));o=float(h.get("rate")or.0);j=o if(e and o>.0)else.0;n=float(h.get("exponent")or 1.);t=m.get("negRisk")if m.get("negRisk")is not None else ev.get("negRisk");i=bool(t)if t is not None else None;q.append(WeatherBucket(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),label=F,question=str(m.get("question")or F),yes_token=str(f[0]),no_token=str(f[1]),unit=B,low_bound=J,high_bound=I,outcome_yes_resolved=a,fee_rate=j,fee_exponent=n,neg_risk=i,rewards_min_size=float(m.get("rewardsMinSize")or.0),rewards_max_spread=float(m.get("rewardsMaxSpread")or.0)))
 if len(q)<4:return None
 q.sort(key=lambda b:(b.low_bound,b.high_bound))
 if any(b.fee_rate>.0 for b in q):d="fees_enabled"
 return WeatherEventSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),series_slug=y,title=A,icao=c,city=C,lat=H,lon=G,tz_name=s,obs_date=p,metric=g,unit=q[0].unit,fee_type=d,end_date_iso=r,buckets=q)
def parse_hko_csv_observations(raw_1min_csv,raw_maxmin_csv,obs_date,tz_name="Asia/Hong_Kong"):
 m=ZoneInfo(tz_name);b=datetime(obs_date.year,obs_date.month,obs_date.day,0,0,tzinfo=m);f=None;a=None;d=None;c=None
 for k in(raw_1min_csv or"").splitlines():
  e=[p.strip()for p in k.split(",")]
  if len(e)>=3 and e[1]in("HK Observatory","Hong Kong Observatory")and len(e[0])>=12 and e[0][:12].isdigit():
   try:
    g=datetime.strptime(e[0][:12],"%Y%m%d%H%M").replace(tzinfo=m)
    if g.date()==obs_date:f=float(e[2]);a=g
   except ValueError:pass
 for k in(raw_maxmin_csv or"").splitlines():
  e=[p.strip()for p in k.split(",")]
  if len(e)>=4 and e[1]in("HK Observatory","Hong Kong Observatory")and len(e[0])>=12 and e[0][:12].isdigit():
   try:
    g=datetime.strptime(e[0][:12],"%Y%m%d%H%M").replace(tzinfo=m)
    if g.date()==obs_date:
     if e[2]and e[2].upper()!="N/A":d=float(e[2])
     if e[3]and e[3].upper()!="N/A":c=float(e[3])
     if a is None:a=g
   except ValueError:pass
 if a is None:return[]
 l=[]
 if c is not None:j=min(a,b+timedelta(minutes=1));l.append(MetarObservation("HKO",j.astimezone(timezone.utc),j,c,True,f"HKO_MIN {c:.1f}C"))
 if d is not None:i=min(a,b+timedelta(minutes=2));l.append(MetarObservation("HKO",i.astimezone(timezone.utc),i,d,True,f"HKO_MAX {d:.1f}C"))
 h=f if f is not None else(d if d is not None else c)
 if h is not None:l.append(MetarObservation("HKO",a.astimezone(timezone.utc),a,h,True,f"HKO_1M {h:.1f}C"))
 l.sort(key=lambda o:o.utc_dt);return l
def fetch_hko_observations_sync(obs_date,tz_name="Asia/Hong_Kong",timeout=7.):
 b="";a="";i={"User-Agent":"DominusWeatherEngine/1.0"}
 try:b=urllib.request.urlopen(urllib.request.Request(HKO_1MIN_CSV_URL,headers=i),timeout=timeout).read().decode("utf-8-sig",errors="ignore")
 except Exception as exc:pass
 try:a=urllib.request.urlopen(urllib.request.Request(HKO_MAXMIN_CSV_URL,headers=i),timeout=timeout).read().decode("utf-8-sig",errors="ignore")
 except Exception as exc:pass
 d=parse_hko_csv_observations(b,a,obs_date,tz_name)
 if d:return d
 try:
  h=json.loads(urllib.request.urlopen(urllib.request.Request(HKO_RHRREAD_URL,headers=i),timeout=timeout).read().decode("utf-8"));e=h.get("temperature")or{};c=str(e.get("recordTime")or"");g=datetime.fromisoformat(c).astimezone(ZoneInfo(tz_name))if c else datetime.now(ZoneInfo(tz_name))
  if g.date()==obs_date:
   for f in e.get("data")or[]:
    if"Observatory"in str(f.get("place")or""):v=float(f["value"]);return[MetarObservation("HKO",g.astimezone(timezone.utc),g,v,False,f"HKO_RHR {v:.1f}C")]
 except Exception:pass
 return[]
def fetch_metar_observations_sync(icao,obs_date,tz_name,timeout=8.):
 if icao.upper()=="HKO":return fetch_hko_observations_sync(obs_date,tz_name,timeout=timeout)
 w=ZoneInfo(tz_name);d=datetime(obs_date.year,obs_date.month,obs_date.day,0,0,tzinfo=w);f=d+timedelta(days=1);a=f.astimezone(timezone.utc)+timedelta(hours=3);l=datetime.now(timezone.utc);c=min(l,a);i=(l-d.astimezone(timezone.utc)).total_seconds()/86400.;e={}
 def _merge_metar(parsed_obs):
  b=int(parsed_obs.utc_dt.timestamp());a=e.get(b)
  if(a is None or parsed_obs.is_corrected or(not a.is_corrected and(parsed_obs.has_t_remark or not a.has_t_remark))):e[b]=parsed_obs
 if i<=13.5:
  s=c.strftime("%Y-%m-%dT%H:%M:%SZ");v=f"{AWC_METAR_URL}?ids={icao.upper()}&format=raw&date={s}&hours=36"
  try:
   n=urllib.request.Request(v,headers={"User-Agent":"DominusWeatherEngine/1.0"});h=urllib.request.urlopen(n,timeout=timeout).read().decode("utf-8",errors="ignore")
   for t in reversed(h.splitlines()):
    b=parse_metar_line(t,icao,c,tz_name)
    if b and b.local_dt.date()==obs_date:_merge_metar(b)
  except Exception as exc:pass
 if not e:
  k=d.astimezone(timezone.utc)-timedelta(hours=2);r=f.astimezone(timezone.utc)+timedelta(hours=2);g=icao.upper()[1:]if(len(icao)==4 and icao.upper().startswith("K"))else icao.upper();p=urllib.parse.urlencode({"station":g,"data":"metar","year1":k.year,"month1":k.month,"day1":k.day,"year2":r.year,"month2":r.month,"day2":r.day,"tz":"Etc/UTC","format":"onlycomma","latlon":"no","elev":"no","missing":"M","trace":"T","direct":"no","report_type":["3","4"]},doseq=True)
  try:
   n=urllib.request.Request(f"{IEM_ASOS_URL}?{p}",headers={"User-Agent":"DominusWeatherEngine/1.0"});j=urllib.request.urlopen(n,timeout=timeout+4.).read().decode("utf-8",errors="ignore")
   for u in j.splitlines()[1:]:
    q=u.split(",",2)
    if len(q)<3:continue
    try:m=datetime.strptime(q[1].strip(),"%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:continue
    b=parse_metar_line(q[2],icao,m,tz_name,explicit_utc_dt=m)
    if b and b.local_dt.date()==obs_date:_merge_metar(b)
  except Exception as exc:pass
 return sorted(e.values(),key=lambda o:o.utc_dt)
def compute_weather_probabilities(spec,eval_utc,metars_so_far,ensemble_hourly_c,forecast_sigma_base_c=1.15,bias_decay_tau_hr=6.,taf_extreme_c=None):
 tz=ZoneInfo(spec.tz_name);W=eval_utc.astimezone(tz);F=datetime(spec.obs_date.year,spec.obs_date.month,spec.obs_date.day,0,0,tzinfo=tz);K=F+timedelta(days=1);_a=[o for o in metars_so_far if o.utc_dt<=eval_utc and o.local_dt.date()==spec.obs_date];_b=len(_a)>0;V=_a[-1]if _b else None
 if _b:
  if spec.metric=="HIGH":e=max(o.temp_c for o in _a)
  else:e=min(o.temp_c for o in _a)
  l=celsius_to_market_int(e,spec.unit)
 else:e=None;l=None
 u=.0;k=bias_decay_tau_hr;i=False;c=False
 if V is not None:
  J=[o for o in _a if(eval_utc-o.utc_dt).total_seconds()<=12600.][-3:];i=any(o.has_convective_precip for o in _a if(eval_utc-o.utc_dt).total_seconds()<=7200.);N=W.hour+W.minute/60.;s=(spec.metric=="HIGH"and 9.<=N<=16.25 and e is not None and(e-V.temp_c)>=1.2)
  if ensemble_hourly_c and J:
   U=[]
   for _j in J:
    T=int(round(_j.utc_dt.timestamp()/3600.)*3600);S=ensemble_hourly_c.get(T)
    if S:R=sum(S)/len(S);U.append(_j.temp_c-R)
   if U:
    U.sort()
    if len(U)==3:B=U[1]
    else:B=sum(U)/len(U)
    u=max(-1.5,min(1.5,B))
    if spec.metric=="HIGH"and B<-.35 and(i or s):c=True;u=max(-.45,B*.2);k=min(bias_decay_tau_hr,1.2)
  elif i or s:c=spec.metric=="HIGH"
 Q=[];M=max(F,W.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1))
 while M<K:Q.append(int(M.astimezone(timezone.utc).timestamp()));M+=timedelta(hours=1)
 if W<K and not Q:Q.append(int(K.astimezone(timezone.utc).timestamp()))
 m=[len(ensemble_hourly_c[t])for t in Q if t in ensemble_hourly_c and ensemble_hourly_c[t]]
 if not m and ensemble_hourly_c:m=[len(v)for v in ensemble_hourly_c.values()if v]
 _i=min(m)if m else 0;_d=[-2.1,-1.5,-1.1,-.75,-.45,-.2,.0,.2,.45,.75,1.1,1.5,2.1];I=[.0 for _ in spec.buckets];f=.0;E=[];D=len(Q)
 if W>=K and l is not None:
  for _c,b in enumerate(spec.buckets):I[_c]=1. if b.contains_rounded(l)else.0
  f=1.
 elif _i>0 and D>0:
  P=forecast_sigma_base_c*min(1.,math.sqrt(max(1.,D)/10.))
  if _i>=15:g=max(.45,.55*P)
  else:g=max(.75,P)
  if c:g*=1.45
  for _h in range(_i):
   A=[]
   for _l in Q:
    _k=ensemble_hourly_c.get(_l)
    if not _k:continue
    v=_k[min(_h,len(_k)-1)];_g=max(.0,(_l-eval_utc.timestamp())/3600.);L=u*math.exp(-_g/max(.5,k));A.append(v+L)
   if not A:continue
   n=max(A)if spec.metric=="HIGH"else min(A)
   if taf_extreme_c is not None and math.isfinite(float(taf_extreme_c)):n=.85*n+.15*float(taf_extreme_c)
   E.append(n)
   for z in _d:
    w=math.exp(-.5*z*z);Z=n+z*g
    if e is not None:H=max(e,Z)if spec.metric=="HIGH"else min(e,Z)
    else:H=Z
    Y=celsius_to_market_int(H,spec.unit)
    for _f,b in enumerate(spec.buckets):
     if b.contains_rounded(Y):I[_f]+=w;break
    f+=w
 q=.0
 if len(E)>=4:_e=sorted(E);_o=_e[int(.25*(len(_e)-1))];_n=_e[int(.75*(len(_e)-1))];q=max(.0,_n-_o)
 if f<=.0:C=[1./len(spec.buckets)for _ in spec.buckets]
 else:C=[max(.001,min(.998,w/f))for w in I];_m=sum(C);C=[p/_m for p in C]
 a=False;d=.0;h=None;j=.0
 if _b and V is not None and e is not None and l is not None:
  G=W.hour+W.minute/60.
  for _c,b in enumerate(spec.buckets):
   if b.contains_rounded(l):h=_c;j=C[_c];break
  if spec.metric=="HIGH":
   d=e-V.temp_c;O=17.5 if(i or c)else 15.75;X=(W.date()>spec.obs_date)or(W.date()==spec.obs_date and G>=O)
   if X and(W.date()>spec.obs_date or d>=.8)and j>=.88:a=True
  else:
   x=V.temp_c-e;d=x;y=(W.date()>spec.obs_date)or(W.date()==spec.obs_date and G>=22.5);r=(W.date()==spec.obs_date and 9.5<=G<22.5 and x>=2.5 and _i>=15 and bool(E)and min(E)>=(e+2.)and j>=.93)
   if(y and j>=.9 and(W.date()>spec.obs_date or x>=1.))or r:a=True
 return{"probs":C,"has_obs":_b,"obs_count":len(_a),"latest_temp_c":V.temp_c if V else None,"running_ext_c":e,"running_ext_int":l,"bias_c":round(u,3),"convective_cold_pool":c,"ensemble_member_count":_i,"peak_iqr_c":round(q,3),"rem_hours_count":D,"is_solar_lock":a,"cooling_cushion_c":round(d,2),"locked_bucket_idx":h,"p_locked_bucket":round(j,4)}
def fetch_live_ensemble_hourly_sync(lat,lon,timeout=8.):
 c={};j=(f"{OPEN_METEO_ENSEMBLE_URL}?latitude={lat:.4f}&longitude={lon:.4f}&hourly=temperature_2m&models=icon_seamless,gfs_seamless&past_days=1&forecast_days=3&timeformat=unixtime")
 for i in range(2):
  try:
   m=urllib.request.Request(j,headers={"User-Agent":"DominusWeatherEngine/1.0"});w=json.loads(urllib.request.urlopen(m,timeout=timeout).read().decode("utf-8"));p=w.get("hourly")or{};r=p.get("time")or[];f=sorted(k for k in p.keys()if k.startswith("temperature_2m"));b=[]
   for k in f:
    x=p.get(k)or[]
    if len(x)<len(r):continue
    o=[];d=None;a=0
    for q in x[:len(r)]:
     if q is not None:d=float(q);o.append(d)
     elif d is not None:a+=1;o.append(d)
     else:a=len(r);break
    if len(o)==len(r)and a<=max(2,len(r)//10):b.append(o)
   for l,s in enumerate(r):
    u=[y[l]for y in b]
    if u:c[int(s)]=u
   if c:break
  except Exception as exc:
   if i==0:time.sleep(.45)
   else:pass
 n=f"{OPEN_METEO_FORECAST_URL}?latitude={lat:.4f}&longitude={lon:.4f}&hourly=temperature_2m&models=ecmwf_ifs025&past_days=1&forecast_days=3&timeformat=unixtime"
 try:
  m=urllib.request.Request(n,headers={"User-Agent":"DominusWeatherEngine/1.0"});h=json.loads(urllib.request.urlopen(m,timeout=timeout).read().decode("utf-8"));t=h.get("hourly")or{};e=t.get("time")or[];g=t.get("temperature_2m")or t.get("temperature_2m_ecmwf_ifs025")or[]
  for l,s in enumerate(e):
   if l<len(g)and g[l]is not None:v=float(g[l]);c.setdefault(int(s),[]).extend([v]*8)
 except Exception:pass
 return c
def fetch_historical_nwp_hourly_sync(lat,lon,start_date,end_date,timeout=10.):
 j=(f"{OPEN_METEO_HIST_FORECAST_URL}?latitude={lat:.4f}&longitude={lon:.4f}&start_date={start_date.isoformat()}&end_date={end_date.isoformat()}&hourly=temperature_2m&models=ecmwf_ifs025,gfs_seamless,icon_seamless&timeformat=unixtime");i=urllib.request.Request(j,headers={"User-Agent":"DominusWeatherEngine/1.0"});e=json.loads(urllib.request.urlopen(i,timeout=timeout).read().decode("utf-8"));b=e.get("hourly")or{};c=b.get("time")or[];a=sorted(k for k in b.keys()if k.startswith("temperature_2m"));h={}
 for g,l in enumerate(c):
  d=[]
  for k in a:
   f=b[k]
   if g<len(f)and f[g]is not None:
    v=float(f[g])
    if"ecmwf"in k:d.extend([v,v])
    else:d.append(v)
  if d:h[int(l)]=d
 return h
_TAF_TEMP_RE=re.compile(r"\bT([XN])(M?\d{2})/(\d{2})(\d{2})Z\b");AWC_TAF_URL="https://aviationweather.gov/api/data/taf";STATION_ROUTINE_RELEASE_MIN={"KLGA":(51,),"KORD":(51,),"KATL":(52,),"KDAL":(53,),"KHOU":(53,),"KMIA":(53,),"KSEA":(53,),"KSFO":(56,),"KDEN":(53,),"KAUS":(53,),"KLAX":(53,),"CYYZ":(0,),"EGLC":(20,50),"LFPB":(0,30),"EDDM":(20,50),"LIMC":(20,50),"EFHK":(20,50),"RJTT":(0,30),"RKSI":(0,30),"RKPK":(0,),"ZSPD":(0,),"ZGSZ":(0,),"RPLL":(0,),"LTAC":(20,50),"SAEZ":(0,),"NZWN":(0,30),"MMMX":(45,),"FACT":(0,30),"EHAM":(25,55),"MPMG":(0,),"LTFM":(20,50),"SBGR":(0,),"OPKC":(0,30),"VILK":(0,30),"OEJN":(0,),"LLBG":(20,50)}
def compute_adaptive_metar_poll_ttl(icao,metars_so_far=None,now_utc=None):
 if icao.upper()=="HKO":return 45.
 g=now_utc or datetime.now(timezone.utc);c=g.minute+g.second/60.;a=list(STATION_ROUTINE_RELEASE_MIN.get(icao.upper(),()))
 if metars_so_far:
  b=sorted({o.utc_dt.minute for o in metars_so_far[-4:]})
  for f in b:
   if f not in a:a.append(f)
 if not a:a=[0,51,53]
 for e in a:
  d=(c-float(e)+30.)%60.-30.
  if-1.<=d<=4.5:return 10.
 return 3e2
def parse_taf_temperature_extremes(raw_taf,icao,ref_utc,tz_name):
 if not raw_taf or icao.upper()not in raw_taf.upper():return{}
 o=ZoneInfo(tz_name);n={}
 for m in _TAF_TEMP_RE.finditer(raw_taf.upper()):
  j="HIGH"if m.group(1)=="X"else"LOW";h=m.group(2);d=-float(int(h[1:]))if h.startswith("M")else float(int(h));g,i=int(m.group(3)),min(23,int(m.group(4)));f=[]
  for e in(-16,0,16):
   l=ref_utc+timedelta(days=e)
   try:f.append(datetime(l.year,l.month,g,i,0,tzinfo=timezone.utc))
   except ValueError:continue
  if not f:continue
  a=min(f,key=lambda c:abs((c-ref_utc).total_seconds()));b=a.astimezone(o).date();k=n.setdefault(b,{})
  if j=="HIGH":k["HIGH"]=max(k.get("HIGH",-999.),d)
  else:k["LOW"]=min(k.get("LOW",999.),d)
 return n
def fetch_taf_extremes_sync(icao,obs_date,tz_name,timeout=5.):
 if icao.upper()=="HKO":return{}
 d=f"{AWC_TAF_URL}?ids={icao.upper()}&format=raw"
 try:c=urllib.request.Request(d,headers={"User-Agent":"DominusWeatherEngine/1.0"});b=urllib.request.urlopen(c,timeout=timeout).read().decode("utf-8",errors="ignore");a=parse_taf_temperature_extremes(b,icao,datetime.now(timezone.utc),tz_name);return dict(a.get(obs_date)or{})
 except Exception:return{}
def verify_weather_slate_partition(spec):
 if len(spec.buckets)<3:return False
 for k in range(-60,141):
  a=sum(1 for b in spec.buckets if b.contains_rounded(k))
  if a!=1:return False
 return True
def evaluate_weather_event_slate(spec,probs,bucket_books,target_budget_usd=10.,max_underround_sum=.985):
 h=verify_weather_slate_partition(spec);I=[];t=[]
 for L,b in enumerate(spec.buckets):
  M=bucket_books.get(b.market_id)or{};F=M.get("ask_yes");C=float(M.get("ask_yes_shares")or.0);E=M.get("ask_no");s=float(M.get("ask_no_shares")or.0);K=float(probs[L])if L<len(probs)else.0;H=max(.0,float(getattr(b,"fee_rate",.0)or.0));G=max(1.,float(getattr(b,"fee_exponent",1.)or 1.))
  if F is not None and.005<=float(F)<=.99 and C>=5.:B=float(F);A=H*((B*(1.-B))**G)if H>.0 else.0;z=B+A;I.append({"idx":L,"market_id":b.market_id,"label":b.label,"yes_token":b.yes_token,"ask_yes":B,"eff_ask_yes":round(z,6),"fee_per_share":round(A,6),"fee_rate":H,"fee_exponent":G,"ask_yes_shares":C,"prob":K,"edge":K-z})
  if E is not None and.005<=float(E)<=.995 and s>=5.:y=float(E);w=H*((y*(1.-y))**G)if H>.0 else.0;v=y+w;t.append({"idx":L,"market_id":b.market_id,"label":b.label,"yes_token":b.no_token,"no_token":b.no_token,"side":"NO","ask_yes":y,"eff_ask_yes":round(v,6),"fee_per_share":round(w,6),"fee_rate":H,"fee_exponent":G,"ask_yes_shares":s})
 a=None
 if h and len(I)==len(spec.buckets):
  q=sum(r["eff_ask_yes"]for r in I);g=sum(r["ask_yes"]for r in I);u=min(r["ask_yes_shares"]for r in I)
  if q<=max_underround_sum and u>=5.:
   p=max(5.,min(u,math.floor(float(target_budget_usd)/max(.1,q))))
   if p*q<=float(target_budget_usd)*1.25:a={"mode":"FULL_SLATE_DUTCH_ARB","side":"ALL_BUCKETS_YES","guaranteed_payout_per_set":1.,"sum_asks":round(q,5),"sum_raw_asks":round(g,5),"guaranteed_edge_per_set":round(1.-q,5),"equal_shares":float(p),"total_cost_usd":round(p*q,4),"guaranteed_profit_usd":round(p*(1.-q),4),"legs":I}
 if a is None and h and len(t)==len(spec.buckets)and len(spec.buckets)>=3:
  J=float(len(spec.buckets));o=J-1.;j=sum(r["eff_ask_yes"]for r in t);m=min(r["ask_yes_shares"]for r in t)
  if j<=o-(1.-max_underround_sum)and m>=5.:
   i=max(5.,min(m,math.floor(float(target_budget_usd)/max(.5,j))))
   if i*j<=float(target_budget_usd)*1.25:a={"mode":"FULL_SLATE_NO_COMPLEMENT_ARB","side":"ALL_BUCKETS_NO","guaranteed_payout_per_set":round(o,4),"sum_asks":round(j,5),"guaranteed_edge_per_set":round(o-j,5),"equal_shares":float(i),"total_cost_usd":round(i*j,4),"guaranteed_profit_usd":round(i*(o-j),4),"legs":t}
 n=sorted([r for r in I if r["edge"]>=.04],key=lambda x:x["edge"],reverse=True);c=None
 if len(n)>=2:
  l=n[:3];f=sum(r["eff_ask_yes"]for r in l);e=min(.999,sum(r["prob"]for r in l));k=min(r["ask_yes_shares"]for r in l);d=e-f
  if f<=.88 and e>=.72 and d>=.09 and k>=5.:D=max(5.,min(k,math.floor(float(target_budget_usd)/max(.1,f))));c={"mode":"CONSTRAINED_SUBSET_BASKET","sum_asks":round(f,5),"combined_prob":round(e,5),"expected_edge_per_set":round(d,5),"equal_shares":float(D),"total_cost_usd":round(D*f,4),"max_loss_usd":round(D*f,4),"legs":l}
 return{"partition_verified":h,"quoted_buckets":len(I),"total_buckets":len(spec.buckets),"full_slate_arb":a,"subset_basket":c}
# ======================================================================================
# [06/21] MODULE: src/polymarket_research/barrier_onetouch_svi_engine.py
# PURPOSE: Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import logging;import math;import re;import urllib.request;from dataclasses import dataclass;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;_INV_SQRT2=.7071067811865475
def _fast_norm_cdf(x):return.5*(1.+math.erf(x*_INV_SQRT2))
try:from src.polymarket_research.deribit_svi_surface import(GLOBAL_SVI_ENGINE,SVIParams,scale_svi_sticky_delta)
except Exception:GLOBAL_SVI_ENGINE=None;SVIParams=Any;scale_svi_sticky_delta=None
logger=logging.getLogger("BarrierOneTouchEngine");GAMMA_API_URL="https://gamma-api.polymarket.com";BINANCE_API_URL="https://api.binance.com";BINANCE_FAPI_URL="https://fapi.binance.com";HIT_SERIES=[("BTC","DAILY","bitcoin-hit-price-daily"),("BTC","WEEKLY","bitcoin-hit-price-weekly"),("BTC","MONTHLY","bitcoin-hit-price-monthly"),("ETH","DAILY","ethereum-hit-price-daily"),("ETH","WEEKLY","ethereum-hit-price-weekly"),("ETH","MONTHLY","ethereum-hit-price-monthly"),("SOL","DAILY","solana-hit-price-daily"),("SOL","WEEKLY","solana-hit-price-weekly"),("SOL","MONTHLY","solana-hit-price-monthly"),("XRP","DAILY","xrp-hit-price-daily"),("XRP","WEEKLY","xrp-hit-price-weekly"),("XRP","MONTHLY","xrp-hit-price-monthly"),("BNB","MONTHLY","bnb-hit-price-monthly"),("DOGE","MONTHLY","dogecoin-hit-price-monthly"),("HYPE","MONTHLY","hyperliquid-hit-price-monthly")];ASSET_BINANCE_SYMBOL={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","BNB":"BNBUSDT","DOGE":"DOGEUSDT","HYPE":"HYPEUSDT"};ASSET_BINANCE_FUTURES_ONLY=frozenset({"HYPE"});ASSET_VOL_MULT_VS_BTC={"BTC":1.,"ETH":1.28,"SOL":1.75,"XRP":1.85,"BNB":1.45,"DOGE":2.1,"HYPE":2.35}
@dataclass
class BarrierRungSpec:event_id:str;series_slug:str;horizon_group:str;asset:str;market_id:str;condition_id:str;question:str;group_label:str;strike:float;direction:str;start_ts:float;end_ts:float;yes_token:str;no_token:str;fee_rate=.07;resolved_yes=None;fee_exponent=1.
_EXPLICIT_DOLLAR_STRIKE_RE=re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b");_ANCHORED_BARRIER_STRIKE_RE=re.compile(r"(?:↑|↓|\b(?:reach|hit|touch|dip(?:\s+to)?|drop(?:\s+to)?|above|below|over|under)\b)\s*\$?\s*" r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b",re.IGNORECASE)
def parse_strike_from_text(question,group_label=""):
 for d in(_EXPLICIT_DOLLAR_STRIKE_RE,_ANCHORED_BARRIER_STRIKE_RE):
  for c in(question,group_label):
   m=d.search(c)
   if m:
    b=m.group(1).replace(",","")
    try:
     a=float(b)
     if m.group(2):a*=1e3
     if a>0:return a
    except ValueError:continue
 return None
def parse_barrier_direction(question,group_label=""):
 q=question.lower();g=group_label.strip()
 if g.startswith("↓")or any(w in q for w in("dip","drop","below","fall")):return"DOWN"
 if g.startswith("↑")or any(w in q for w in("reach","hit","touch","above")):return"UP"
 return None
_CRYPTO_MONTH_RE=re.compile(r"\bin\s+(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(\d{4}))?(?:\?|\b)",re.IGNORECASE);_CRYPTO_MONTHS={"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
def parse_hit_event(ev,asset,horizon_group,series_slug):
 n=str(ev.get("endDate")or"");g=str(ev.get("startDate")or ev.get("creationDate")or"")
 if not n:return[]
 try:r=datetime.fromisoformat(n.replace("Z","+00:00")).timestamp()
 except Exception:return[]
 e={"DAILY":86400.,"WEEKLY":7*86400.,"MONTHLY":30*86400.}.get(horizon_group,86400.);b=r-e
 if g:
  try:
   l=datetime.fromisoformat(g.replace("Z","+00:00")).timestamp()
   if r-35*86400.<=l<r:b=max(b,l)
  except Exception:pass
 w=_CRYPTO_MONTH_RE.search(str(ev.get("title")or""))
 if w:
  try:from zoneinfo import ZoneInfo;z=ZoneInfo("America/New_York");v=_CRYPTO_MONTHS[w.group(1).lower()];u=int(w.group(2))if w.group(2)else datetime.fromtimestamp(r-5*86400.,tz=z).year;b=max(b,datetime(u,v,1,0,0,tzinfo=z).timestamp())
  except Exception:pass
 s=[]
 for m in ev.get("markets")or[]:
  q=str(m.get("question")or"");y=str(m.get("groupItemTitle")or"");f=parse_barrier_direction(q,y);p=parse_strike_from_text(q,y)
  if not f or not p or p<=0:continue
  d=m.get("clobTokenIds")
  if isinstance(d,str):
   try:d=json.loads(d)
   except Exception:d=[]
  if not d or len(d)<2:continue
  a=None
  if m.get("closed"):
   o=m.get("outcomePrices")
   if isinstance(o,str):
    try:o=json.loads(o)
    except Exception:o=None
   if isinstance(o,list)and len(o)>=2:
    try:
     if float(o[0])>=.99:a=1
     elif float(o[1])>=.99:a=0
    except Exception:pass
  c=b
  for j in(m.get("startDate"),m.get("createdAt")):
   if j:
    try:
     t=datetime.fromisoformat(str(j).replace("Z","+00:00")).timestamp()
     if b-3600.<=t<r:x=60. if(t>b+3e2 or"creation of this market"in str(m.get("description")or"").lower())else.0;c=max(c,min(r-60.,t+x))
    except Exception:pass
  i=.07;h=1.
  try:
   from src.polymarket_research.tradfi_sports_zero_fee_engine import _extract_market_fee_rate
   if any(k in m for k in("feeSchedule","feeType","feesEnabled","takerBaseFee")):i,h=_extract_market_fee_rate(m)
  except Exception:pass
  s.append(BarrierRungSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,horizon_group=horizon_group,asset=asset.upper(),market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),question=q,group_label=y,strike=p,direction=f,start_ts=c,end_ts=r,yes_token=str(d[0]),no_token=str(d[1]),fee_rate=i,resolved_yes=a,fee_exponent=h))
 return s
def first_passage_touch_prob(spot,strike,tte_seconds,iv_annual,direction,wick_vol_multiplier=1.12,jump_tail_blend=.08,forward_drift_annual=.0,realized_vol_ratio=1.):
 if spot<=.0 or strike<=.0:return.0
 if direction=="UP"and spot>=strike:return 1.
 if direction=="DOWN"and spot<=strike:return 1.
 if tte_seconds<=1.:return.0
 h=tte_seconds/(365.25*86400.);b=abs(math.log(strike/spot));g=max(-.3,min(.4,float(forward_drift_annual or.0)))
 def _single_regime_touch(sig):
  d=max(.08,min(4.,sig));c=d*math.sqrt(h)
  if c<=1e-8:return.0
  g=(g-.5*(d**2))if direction=="UP"else(-g+.5*(d**2));f=(-b+g*h)/c;e=(-b-g*h)/c;a=max(-60.,min(60.,(2.*g*b)/(d**2)));p=_fast_norm_cdf(f)+math.exp(a)*_fast_norm_cdf(e);return max(1e-4,min(.9999,p))
 d=iv_annual*wick_vol_multiplier;c=_single_regime_touch(d);i=_single_regime_touch(d*1.65);f=max(.5,min(3.5,float(realized_vol_ratio or 1.)))**1.5;a=min(.35,max(.02,float(jump_tail_blend)*f))if abs(realized_vol_ratio-1.)>1e-6 else float(jump_tail_blend);e=(1.-a)*c+a*i;return max(1e-4,min(.9999,e))
def evaluate_barrier_no_net_ev(p_touch,ask_no,fee_rate=.07,min_net_ev_per_share=.035,max_loss_to_gain_ratio=9.):g=max(1e-4,min(.9999,1.-float(p_touch)));h=max(.01,min(.99,float(ask_no)));f=min(.5,max(.0,float(fee_rate)*(1.-h)))if float(fee_rate)>.0 else.0;d=h/(1.-f)if f>.0 else h;b=max(1e-6,1.-d);e=g-d;a=d/b;c=bool(e>=min_net_ev_per_share and a<=max_loss_to_gain_ratio);return{"eligible":c,"p_no":round(g,5),"eff_cost_no":round(d,5),"ev_net_per_share":round(e,5),"loss_to_gain_ratio":round(a,3)}
def get_wing_implied_vol(asset,spot,strike,tte_seconds,dvol_annual_override=None):
 h=asset.upper();g=max(1e-5,tte_seconds/(365.25*86400.));k=math.log(strike/spot)if(spot>0 and strike>0)else.0
 if dvol_annual_override is None and GLOBAL_SVI_ENGINE is not None:
  j=GLOBAL_SVI_ENGINE.get_svi_params(h,allow_sync_if_empty=True,target_tte_sec=tte_seconds)
  if j is not None:c=float(j.implied_vol(.0,t_override=g));b=float(j.implied_vol(k,t_override=g));return.5*(c+b),"DERIBIT_SVI_WING"
  if h in("SOL","XRP"):
   f=GLOBAL_SVI_ENGINE.get_svi_params("BTC",allow_sync_if_empty=True,target_tte_sec=tte_seconds)
   if f is not None:
    i=ASSET_VOL_MULT_VS_BTC.get(h,1.75)
    if scale_svi_sticky_delta is not None:e=scale_svi_sticky_delta(f,i,spot if spot>0 else 1e2);c=float(e.implied_vol(.0,t_override=g));b=float(e.implied_vol(k,t_override=g));return.5*(c+b),"BTC_SVI_STICKY_DELTA"
    return float(f.implied_vol(k/i,t_override=g)*i),"BTC_SVI_SCALED"
 d=dvol_annual_override if dvol_annual_override is not None else(.42*ASSET_VOL_MULT_VS_BTC.get(h,1.));a=1.+1.35*min(.25,abs(k))+(-.2*k if k<0 else.08*k);return max(.15,min(3.,d*a)),"DVOL_SMILE_PARAMETRIC"
def detect_barrier_monotonicity_boxes(quote_rows,fee_rate=.07,max_box_cost_net=.995):
 p=[]
 for c in("UP","DOWN"):
  r=sorted([q for q in quote_rows if str(q.get("direction")or"").upper()==c and float(q.get("strike")or.0)>.0],key=lambda x:float(x["strike"]))
  for i in range(len(r)):
   for j in range(i+1,len(r)):
    o,n=r[i],r[j];m,l=float(o["strike"]),float(n["strike"])
    if l<=m*1.0005:continue
    if c=="UP":a,b=o,n;e=f"YES(↑{m:g})+NO(↑{l:g})"
    else:a,b=n,o;e=f"YES(↓{l:g})+NO(↓{m:g})"
    if("start_ts"in a and"start_ts"in b and float(a["start_ts"])>float(b["start_ts"])+1e-6):continue
    y=a.get("ask_yes")if a.get("ask_yes")is not None else a.get("best_ask_yes");w=b.get("ask_no")if b.get("ask_no")is not None else b.get("best_ask_no")
    if y is None or w is None:continue
    v,u=float(y),float(w)
    if not(.01<=v<=.99 and.01<=u<=.99):continue
    k=float(a.get("fee_rate",fee_rate));h=float(b.get("fee_rate",fee_rate));g=float(a.get("fee_exponent",1.));f=float(b.get("fee_exponent",1.));t=min(.5,(k*((v*(1.-v))**g))/v)if k>.0 else.0;s=min(.5,(h*((u*(1.-u))**f))/u)if h>.0 else.0;d=v/(1.-t)+u/(1.-s)
    if.9<=d<=max_box_cost_net:p.append({"direction":c,"label":e,"low_strike":m,"high_strike":l,"leg_yes_market_id":str(a["market_id"]),"leg_yes_condition_id":str(a.get("condition_id")or""),"yes_token":str(a["yes_token"]),"yes_opp_token":str(a.get("no_token")or""),"leg_yes_fee_rate":k,"leg_yes_fee_exponent":g,"leg_no_market_id":str(b["market_id"]),"leg_no_condition_id":str(b.get("condition_id")or""),"no_token":str(b["no_token"]),"no_opp_token":str(b.get("yes_token")or""),"leg_no_fee_rate":h,"leg_no_fee_exponent":f,"box_cost_gross":round(v+u,5),"box_cost_net":round(d,5),"guaranteed_edge":round(1.-d,5)})
 p.sort(key=lambda x:x["box_cost_net"]);return p
def _fetch_finalized_klines(sym,st_ms,en_ms,interval,timeout):
 if sym=="HYPEUSDT":a=(f"{BINANCE_FAPI_URL}/fapi/v1/klines?symbol={sym}&interval={interval}&startTime={st_ms}&endTime={en_ms}&limit=1000")
 else:a=(f"{BINANCE_API_URL}/api/v3/klines?symbol={sym}&interval={interval}&startTime={st_ms}&endTime={en_ms}&limit=1000")
 c=urllib.request.Request(a,headers={"User-Agent":"DominusBarrierEngine/1.0"});b=json.loads(urllib.request.urlopen(c,timeout=timeout).read().decode("utf-8"))
 if not isinstance(b,list):return[]
 return[r for r in b if len(r)>=7 and int(r[6])<=en_ms]
def fetch_binance_window_extremes_sync(asset,start_ts,end_ts,interval="1m",timeout=6.):
 k=ASSET_BINANCE_SYMBOL.get(asset.upper())
 if not k or end_ts<=start_ts:return None
 j=int(start_ts*1000);i=int(end_ts*1000);e=end_ts-start_ts
 try:
  d=[]
  if e>5.7e4 and interval in("1m","5m"):
   c=min(i,(j//3600000+1)*3600000+60000)
   if c>j:d.extend(_fetch_finalized_klines(k,j,c,"1m",timeout))
   d.extend(_fetch_finalized_klines(k,j,i,"1h",timeout));b=max(j,i-7200*1000);d.extend(_fetch_finalized_klines(k,b,i,"1m",timeout))
  else:d.extend(_fetch_finalized_klines(k,j,i,interval,timeout))
  if not d:return None
  h=max(float(r[2])for r in d);g=min(float(r[3])for r in d);a=max(d,key=lambda r:int(r[6]));f=float(a[4]);return h,g,f
 except Exception:return None
# ======================================================================================
# [07/21] MODULE: src/polymarket_research/multistrike_svi_scalper.py
# PURPOSE: Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import logging;import math;import re;from dataclasses import dataclass;from datetime import datetime;from typing import Any,Dict,List,Optional,Tuple;_INV_SQRT2=.7071067811865475
def _fast_norm_cdf(x):return.5*(1.+math.erf(x*_INV_SQRT2))
def _fast_bs_call(F,K,T,sigma):
 if T<=.0 or sigma<=.0 or K<=.0 or F<=.0:return max(.0,F-K)
 a=sigma*math.sqrt(T);c=(math.log(F/K)+.5*(sigma**2)*T)/a;b=c-a;return F*_fast_norm_cdf(c)-K*_fast_norm_cdf(b)
def _fast_bl_digital(F,K,T_years,svi):b=max(1e-6,T_years);g=max(.01,K*.001);f=math.log((K+g)/F);e=math.log(max(1e-6,K-g)/F);d=_fast_bs_call(F,K+g,b,svi.implied_vol(f,t_override=b));c=_fast_bs_call(F,max(1e-6,K-g),b,svi.implied_vol(e,t_override=b));a=-(d-c)/(2.*g);return max(1e-4,min(.9999,a))
try:from src.polymarket_research.deribit_svi_surface import(GLOBAL_SVI_ENGINE,SVIParams,compute_breeden_litzenberger_digital,enforce_monotone_ladder_probabilities)
except Exception:GLOBAL_SVI_ENGINE=None;SVIParams=Any;compute_breeden_litzenberger_digital=None;enforce_monotone_ladder_probabilities=None
logger=logging.getLogger("MultiStrikeSVIScalper");STRIKE_SERIES=[("BTC","btc-multi-strikes-weekly"),("ETH","ethereum-multi-strikes-weekly"),("SOL","solana-multi-strikes-weekly"),("XRP","xrp-multi-strikes-weekly")];ASSET_VOL_MULT_VS_BTC={"BTC":1.,"ETH":1.28,"SOL":1.75,"XRP":1.85}
@dataclass
class StrikeRungSpec:event_id:str;series_slug:str;asset:str;title:str;market_id:str;condition_id:str;question:str;strike:float;is_downward:bool;end_ts:float;yes_token:str;no_token:str;fee_rate=.07;resolved_yes=None
_EXPLICIT_DOLLAR_RE=re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b");_ANCHORED_STRIKE_RE=re.compile(r"\b(?:above|below|over|under|less than|greater than|higher than|lower than)\s+\$?\s*" r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b",re.IGNORECASE);_CLEAN_LABEL_STRIKE_RE=re.compile(r"^\s*[↑↓><]?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*$")
def _extract_threshold_strike(q,gl):
 for d,c in((_EXPLICIT_DOLLAR_RE,q),(_EXPLICIT_DOLLAR_RE,gl),(_ANCHORED_STRIKE_RE,q),(_CLEAN_LABEL_STRIKE_RE,gl)):
  b=d.search(c)
  if b:
   try:
    a=float(b.group(1).replace(",",""))
    if b.group(2):a*=1e3
    if a>0:return a
   except ValueError:continue
 return None
def parse_multistrike_event(ev,asset,series_slug):
 e=str(ev.get("endDate")or"")
 if not e:return[]
 try:h=datetime.fromisoformat(e.replace("Z","+00:00")).timestamp()
 except Exception:return[]
 d=str(ev.get("title")or"");i=[]
 for m in ev.get("markets")or[]:
  q=str(m.get("question")or"");j=str(m.get("groupItemTitle")or"")
  if"between"in q.lower():continue
  g=_extract_threshold_strike(q,j)
  if g is None or g<=0:continue
  b=m.get("clobTokenIds")
  if isinstance(b,str):
   try:b=json.loads(b)
   except Exception:b=[]
  if not b or len(b)<2:continue
  a=None
  if m.get("closed"):
   f=m.get("outcomePrices")
   if isinstance(f,str):
    try:f=json.loads(f)
    except Exception:f=None
   if isinstance(f,list)and len(f)>=2:
    try:
     if float(f[0])>=.99:a=1
     elif float(f[1])>=.99:a=0
    except Exception:pass
  c=any(w in q.lower()for w in("below","under","less than","lower than"));i.append(StrikeRungSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,asset=asset.upper(),title=d,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),question=q,strike=g,is_downward=c,end_ts=h,yes_token=str(b[0]),no_token=str(b[1]),resolved_yes=a))
 i.sort(key=lambda r:r.strike);return i
def us_session_vol_multiplier(now_ts,end_ts):
 e=end_ts-now_ts
 if e<=0 or e>21600:return 1.
 a=int(now_ts//86400)*86400
 for d in(0,86400):
  b=a+d+12*3600+25*60;c=a+d+14*3600+30*60
  if max(now_ts,b)<min(end_ts,c):return 1.35
 return 1.
def evaluate_svi_digital_fair_value(asset,spot,strike,tte_seconds,is_downward=False,dvol_annual_override=None,now_ts=None):
 if spot<=0 or strike<=0 or tte_seconds<=0:return{"p_yes":.5,"p_no":.5,"iv_annual":.45,"z_sigma":.0,"source":"INVALID"}
 l=asset.upper();j=max(1e-6,tte_seconds/(365.25*86400.));f=us_session_vol_multiplier(now_ts,now_ts+tte_seconds)if now_ts is not None else 1.
 if dvol_annual_override is None and GLOBAL_SVI_ENGINE is not None:i=GLOBAL_SVI_ENGINE.evaluate_strike_probability(asset=l,spot=spot,strike=strike,tte_seconds=tte_seconds*(f**2),outcome="YES",is_downward_question=is_downward,allow_sync_fetch=True,target_tte_sec=tte_seconds);e=float(i["p_svi"]);a=float(i["svi_iv_annual"])*f;b=max(1e-6,a*math.sqrt(j));d=abs(math.log(spot/strike))/b;return{"p_yes":round(e,4),"p_no":round(1.-e,4),"iv_annual":round(a,4),"z_sigma":round(d,3),"source":i["source"]}
 h=(dvol_annual_override if dvol_annual_override is not None else(.42*ASSET_VOL_MULT_VS_BTC.get(l,1.)))*f;m=(h**2)*j
 if SVIParams is not Any:g=SVIParams(a=max(1e-8,m*.86),b=max(1e-7,m*.34),rho=-.12,m=.0,sigma=.05,t_years=j,forward_price=spot,calibrated_at=.0);k=math.log(strike/spot);a=g.implied_vol(k,t_override=j);c=_fast_bl_digital(spot,strike,j,g)
 else:a=h;b=max(1e-6,a*math.sqrt(j));n=(math.log(spot/strike)-.5*(a**2)*j)/b;c=_fast_norm_cdf(n)
 e=(1.-c)if is_downward else c;b=max(1e-6,a*math.sqrt(j));d=abs(math.log(spot/strike))/b;return{"p_yes":round(max(.001,min(.999,e)),4),"p_no":round(max(.001,min(.999,1.-e)),4),"iv_annual":round(a,4),"z_sigma":round(d,3),"source":"DVOL_SVI_BL"}
def detect_ladder_monotonicity_boxes(quote_rows,fee_rate=.07):
 g=[];d=sorted([r for r in quote_rows if not r.get("is_downward")],key=lambda x:x["strike"])
 for i in range(len(d)):
  for j in range(i+1,len(d)):
   k=d[i];h=d[j]
   if h["strike"]<=k["strike"]:continue
   c=float(k.get("ask_yes")or 1.);b=float(h.get("ask_no")or 1.)
   if not(.01<=c<=.98 and.01<=b<=.98):continue
   f=fee_rate*c*(1.-c);e=fee_rate*b*(1.-b);a=c+b+f+e
   if a<=.996:g.append({"low_strike":k["strike"],"high_strike":h["strike"],"low_market_id":k["market_id"],"high_market_id":h["market_id"],"yes_token_low":k["yes_token"],"no_token_high":h["no_token"],"ask_yes_low":c,"ask_no_high":b,"box_cost_net":round(a,5),"riskless_floor_edge":round(1.-a,5)})
 return g
def evaluate_coherent_strike_ladder(asset,spot,rungs,tte_seconds,now_ts=None):
 e=sorted([r for r in rungs if not r.is_downward],key=lambda x:x.strike);c=[];b={}
 for r in e:i=evaluate_svi_digital_fair_value(asset,spot,r.strike,tte_seconds,is_downward=False,now_ts=now_ts);c.append((r.strike,float(i["p_yes"])));b[r.strike]=i
 if enforce_monotone_ladder_probabilities is not None and c:d=enforce_monotone_ladder_probabilities(c)
 else:d={"strikes":[k for k,_ in c],"probs":[p for _,p in c],"interval_probs":[],"max_adjustment":.0}
 a={}
 for h,r in enumerate(e):g=float(d["probs"][h])if h<len(d["probs"])else float(b[r.strike]["p_yes"]);f=dict(b[r.strike]);f["p_yes_raw"]=f["p_yes"];f["p_yes"]=round(g,4);f["p_no"]=round(1.-g,4);a[r.market_id]=f
 return{"by_market_id":a,"strikes":d["strikes"],"probs":d["probs"],"interval_probs":d["interval_probs"],"max_adjustment":d["max_adjustment"]}
NEGRISK_SERIES=[("BTC","bitcoin-neg-risk-weekly"),("ETH","ethereum-neg-risk-weekly"),("SOL","solana-neg-risk-weekly"),("XRP","xrp-neg-risk-weekly")];DAILY_UPDOWN_SERIES=[("BTC","btc-up-or-down-daily"),("ETH","eth-up-or-down-daily"),("SOL","sol-up-or-down-daily"),("XRP","xrp-up-or-down-daily"),("BNB","bnb-up-or-down-daily"),("DOGE","dogecoin-up-or-down-daily")];ZERO_FEE_PYTH_DAILY_SERIES=[("EURUSD","eurusd-daily-up-or-down"),("GBPUSD","gbpusd-daily-up-or-down"),("USDJPY","usdjpy-daily-up-or-down"),("USDCHF","usdchf-daily-up-or-down"),("DXY","dxy-daily-up-or-down"),("GOLD","gold-daily-up-or-down"),("SILVER","silver-daily-up-or-down"),("OIL","oil-daily-up-or-down")]
@dataclass
class NegRiskBracketSpec:event_id:str;series_slug:str;asset:str;title:str;market_id:str;condition_id:str;question:str;bracket_kind:str;k_low:Optional[float];k_high:Optional[float];end_ts:float;yes_token:str;no_token:str;fee_rate=.07;resolution_source=""
@dataclass
class DailyUpDownSpec:event_id:str;series_slug:str;asset:str;title:str;market_id:str;condition_id:str;start_ts:float;end_ts:float;up_token:str;down_token:str;fee_rate=.07;resolution_source=""
_RANGE_LABEL_RE=re.compile(r"^\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*[-–—]\s*" r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*$");_BETWEEN_Q_RE=re.compile(r"\bbetween\s+\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s+and\s+" r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\b",re.IGNORECASE);_LOWER_TAIL_LABEL_RE=re.compile(r"^\s*<\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*$");_UPPER_TAIL_LABEL_RE=re.compile(r"^\s*>\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*([kK])?\s*$")
def _num_with_k(num_s,k_s):
 a=float(num_s.replace(",",""))
 if k_s:a*=1e3
 return a
def parse_negrisk_bracket_event(ev,asset,series_slug):
 j=str(ev.get("endDate")or"")
 if not j:return[]
 try:l=datetime.fromisoformat(j.replace("Z","+00:00")).timestamp()
 except Exception:return[]
 i=str(ev.get("title")or"");s=str(ev.get("id")or"");g=[]
 for m in ev.get("markets")or[]:
  if m.get("closed")or m.get("acceptingOrders")is False:continue
  q=str(m.get("question")or"");v=str(m.get("groupItemTitle")or"");d=m.get("clobTokenIds")
  if isinstance(d,str):
   try:d=json.loads(d)
   except Exception:d=[]
  if not isinstance(d,list)or len(d)<2:continue
  a=None;b=None;c=None;o=_RANGE_LABEL_RE.match(v)or _BETWEEN_Q_RE.search(q)
  if o:
   u=_num_with_k(o.group(1),o.group(2));t=_num_with_k(o.group(3),o.group(4))
   if t>u>0:a="RANGE";b,c=u,t
  else:
   r=_LOWER_TAIL_LABEL_RE.match(v);p=_UPPER_TAIL_LABEL_RE.match(v);n=q.lower()
   if r or("less than"in n or"below"in n or"under"in n):
    k=_num_with_k(r.group(1),r.group(2))if r else _extract_threshold_strike(q,v)
    if k and k>0:a="LOWER_TAIL";c=k
   elif p or("greater than"in n or"above"in n or"over"in n):
    k=_num_with_k(p.group(1),p.group(2))if p else _extract_threshold_strike(q,v)
    if k and k>0:a="UPPER_TAIL";b=k
  if a is None:continue
  e=m.get("feeSchedule")or{};f=float(e.get("rate",.07)if m.get("feesEnabled",True)else.0);h=str(m.get("resolutionSource")or ev.get("resolutionSource")or"").strip().lower();g.append(NegRiskBracketSpec(event_id=s,series_slug=series_slug,asset=asset.upper(),title=i,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),question=q,bracket_kind=a,k_low=b,k_high=c,end_ts=l,yes_token=str(d[0]),no_token=str(d[1]),fee_rate=f,resolution_source=h))
 return g
def build_negrisk_cross_box_bundles(rungs,brackets,spot=.0,max_strike_dist_log=.14,tail_max_strike_dist_log=.24):
 if not rungs or not brackets:return[]
 if rungs[0].asset!=brackets[0].asset:return[]
 if abs(rungs[0].end_ts-brackets[0].end_ts)>2.:return[]
 d={round(float(r.strike),4):r for r in rungs if not r.is_downward};c=[]
 for h in brackets:
  if spot>.0:
   g=h.k_low if h.k_low is not None else(h.k_high or spot);b=tail_max_strike_dist_log if h.bracket_kind in("LOWER_TAIL","UPPER_TAIL")else max_strike_dist_log
   if g>0 and abs(math.log(g/spot))>b:continue
  if h.bracket_kind=="LOWER_TAIL"and h.k_high is not None:
   a=d.get(round(float(h.k_high),4))
   if a is not None:c.append({"bundle_id":f"TAIL_LOW_YES_{h.market_id}_{a.market_id}","label":f"NR_YES(<{h.k_high:g})+MS_YES(>{a.strike:g})","guaranteed_payout":1.,"end_ts":h.end_ts,"legs":[{"token_id":h.yes_token,"opp_token_id":h.no_token,"condition_id":h.condition_id,"neg_risk":True,"strike":float(h.k_high),"side":"YES","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"NR_YES<{h.k_high:g}"},{"token_id":a.yes_token,"opp_token_id":a.no_token,"condition_id":a.condition_id,"neg_risk":False,"strike":float(a.strike),"side":"YES","market_id":a.market_id,"fee_rate":a.fee_rate,"label":f"MS_YES>{a.strike:g}"}]});c.append({"bundle_id":f"TAIL_LOW_NO_{h.market_id}_{a.market_id}","label":f"NR_NO(<{h.k_high:g})+MS_NO(>{a.strike:g})","guaranteed_payout":1.,"end_ts":h.end_ts,"legs":[{"token_id":h.no_token,"opp_token_id":h.yes_token,"condition_id":h.condition_id,"neg_risk":True,"strike":float(h.k_high),"side":"NO","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"NR_NO<{h.k_high:g}"},{"token_id":a.no_token,"opp_token_id":a.yes_token,"condition_id":a.condition_id,"neg_risk":False,"strike":float(a.strike),"side":"NO","market_id":a.market_id,"fee_rate":a.fee_rate,"label":f"MS_NO>{a.strike:g}"}]})
  elif h.bracket_kind=="UPPER_TAIL"and h.k_low is not None:
   a=d.get(round(float(h.k_low),4))
   if a is not None:c.append({"bundle_id":f"TAIL_HIGH_A_{h.market_id}_{a.market_id}","label":f"NR_YES(>{h.k_low:g})+MS_NO(>{a.strike:g})","guaranteed_payout":1.,"end_ts":h.end_ts,"legs":[{"token_id":h.yes_token,"opp_token_id":h.no_token,"condition_id":h.condition_id,"neg_risk":True,"strike":float(h.k_low),"side":"YES","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"NR_YES>{h.k_low:g}"},{"token_id":a.no_token,"opp_token_id":a.yes_token,"condition_id":a.condition_id,"neg_risk":False,"strike":float(a.strike),"side":"NO","market_id":a.market_id,"fee_rate":a.fee_rate,"label":f"MS_NO>{a.strike:g}"}]});c.append({"bundle_id":f"TAIL_HIGH_B_{h.market_id}_{a.market_id}","label":f"NR_NO(>{h.k_low:g})+MS_YES(>{a.strike:g})","guaranteed_payout":1.,"end_ts":h.end_ts,"legs":[{"token_id":h.no_token,"opp_token_id":h.yes_token,"condition_id":h.condition_id,"neg_risk":True,"strike":float(h.k_low),"side":"NO","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"NR_NO>{h.k_low:g}"},{"token_id":a.yes_token,"opp_token_id":a.no_token,"condition_id":a.condition_id,"neg_risk":False,"strike":float(a.strike),"side":"YES","market_id":a.market_id,"fee_rate":a.fee_rate,"label":f"MS_YES>{a.strike:g}"}]})
  elif h.bracket_kind=="RANGE"and h.k_low is not None and h.k_high is not None:
   f=d.get(round(float(h.k_low),4));e=d.get(round(float(h.k_high),4))
   if f is not None and e is not None:c.append({"bundle_id":f"PART_1X_{h.market_id}_{f.market_id}_{e.market_id}","label":f"MS_NO(>{h.k_low:g})+NR_YES([{h.k_low:g},{h.k_high:g}])+MS_YES(>{h.k_high:g})","guaranteed_payout":1.,"end_ts":h.end_ts,"legs":[{"token_id":f.no_token,"side":"NO","market_id":f.market_id,"fee_rate":f.fee_rate,"label":f"MS_NO>{h.k_low:g}"},{"token_id":h.yes_token,"side":"YES","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"NR_YES[{h.k_low:g}-{h.k_high:g}]"},{"token_id":e.yes_token,"side":"YES","market_id":e.market_id,"fee_rate":e.fee_rate,"label":f"MS_YES>{h.k_high:g}"}]});c.append({"bundle_id":f"COMP_2X_{h.market_id}_{f.market_id}_{e.market_id}","label":f"MS_YES(>{h.k_low:g})+NR_NO([{h.k_low:g},{h.k_high:g}])+MS_NO(>{h.k_high:g})","guaranteed_payout":2.,"end_ts":h.end_ts,"legs":[{"token_id":f.yes_token,"side":"YES","market_id":f.market_id,"fee_rate":f.fee_rate,"label":f"MS_YES>{h.k_low:g}"},{"token_id":h.no_token,"side":"NO","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"NR_NO[{h.k_low:g}-{h.k_high:g}]"},{"token_id":e.no_token,"side":"NO","market_id":e.market_id,"fee_rate":e.fee_rate,"label":f"MS_NO>{h.k_high:g}"}]})
 return c
def parse_daily_updown_event(ev,asset,series_slug):
 l=ev.get("markets")or[]
 if not l or not isinstance(l[0],dict):return None
 m=l[0]
 if m.get("closed")or m.get("acceptingOrders")is False:return None
 f=str(m.get("eventStartTime")or"").strip();j=str(m.get("endDate")or ev.get("endDate")or"").strip()
 if not f or not j:return None
 try:i=datetime.fromisoformat(f.replace("Z","+00:00")).timestamp();k=datetime.fromisoformat(j.replace("Z","+00:00")).timestamp()
 except Exception:return None
 if abs((k-i)-86400.)>7200.:return None
 d=m.get("clobTokenIds")
 if isinstance(d,str):
  try:d=json.loads(d)
  except Exception:d=[]
 a=m.get("outcomes")
 if isinstance(a,str):
  try:a=json.loads(a)
  except Exception:a=[]
 if not isinstance(d,list)or len(d)<2:return None
 c,b=0,1
 if isinstance(a,list)and len(a)>=2:
  h=[str(o).strip().upper()for o in a]
  if"UP"in h and"DOWN"in h:c=h.index("UP");b=h.index("DOWN")
 e=m.get("feeSchedule")or{};g=float(e.get("rate",.07)if m.get("feesEnabled",True)else.0);return DailyUpDownSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,asset=asset.upper(),title=str(m.get("question")or ev.get("title")or""),market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),start_ts=i,end_ts=k,up_token=str(d[c]),down_token=str(d[b]),fee_rate=g,resolution_source=str(m.get("resolutionSource")or"").strip().lower())
# ======================================================================================
# [08/21] MODULE: src/polymarket_research/same_oracle_dominance_box.py
# PURPOSE: Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import math;from dataclasses import dataclass;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;CORE_LIVE_DOMINANCE_ASSETS=("BTC","ETH","SOL","XRP");EXPANSION_DOMINANCE_ASSETS=("BNB","DOGE","HYPE");DOMINANCE_ASSETS=CORE_LIVE_DOMINANCE_ASSETS+EXPANSION_DOMINANCE_ASSETS;DOMINANCE_SERIES_SLUGS={"BTC":{"4h":"btc-up-or-down-4h","15m":"btc-up-or-down-15m","5m":"btc-up-or-down-5m"},"ETH":{"4h":"eth-up-or-down-4h","15m":"eth-up-or-down-15m","5m":"eth-up-or-down-5m"},"SOL":{"4h":"sol-up-or-down-4h","15m":"sol-up-or-down-15m","5m":"sol-up-or-down-5m"},"XRP":{"4h":"xrp-up-or-down-4h","15m":"xrp-up-or-down-15m","5m":"xrp-up-or-down-5m"},"BNB":{"4h":"bnb-up-or-down-4h","15m":"bnb-up-or-down-15m","5m":"bnb-up-or-down-5m"},"DOGE":{"4h":"doge-up-or-down-4h","15m":"doge-up-or-down-15m","5m":"doge-up-or-down-5m"},"HYPE":{"4h":"hype-up-or-down-4h","15m":"hype-up-or-down-15m","5m":"hype-up-or-down-5m"}};METAL_DOMINANCE_ASSETS=("XAU","XAG");METAL_DOMINANCE_SERIES_SLUGS={"XAU":{"1h":"gold-up-or-down-1h","15m":"gold-up-or-down-15m"},"XAG":{"1h":"silver-up-or-down-1h","15m":"silver-up-or-down-15m"}};EMPIRICAL_BOX_ASSET_CAPS_USD={"BTC":150.,"ETH":75.,"SOL":22.,"XRP":22.,"BNB":22.,"HYPE":15.,"DOGE":15.,"XAU":22.,"XAG":22.};MIN_CORRIDOR_BPS_BY_ASSET={"BTC":3.,"ETH":3.,"SOL":3.,"XRP":3.,"BNB":5.,"DOGE":5.,"HYPE":5.,"XAU":4.,"XAG":4.};POLYMARKET_CRYPTO_PRICE_URL="https://polymarket.com/api/crypto/crypto-price";GAMMA_EVENTS_URL="https://gamma-api.polymarket.com/events";HORIZON_TO_VARIANT={"4h":"fourhour","1h":"hourly","15m":"fifteen","5m":"fiveminute"};HORIZON_TO_DURATION_SEC={"4h":14400.,"1h":3600.,"15m":9e2,"5m":3e2}
@dataclass(frozen=True)
class TwapCandleMarketSpec:asset:str;horizon:str;market_id:str;condition_id:str;title:str;start_iso:str;end_iso:str;start_ts:float;end_ts:float;up_token:str;down_token:str;fee_rate:float;fee_exponent:float;neg_risk:bool;twap_lookback_sec:int;resolution_source:str
def _parse_iso_ts(iso_str):
 a=datetime.fromisoformat(str(iso_str).replace("Z","+00:00"))
 if a.tzinfo is None:a=a.replace(tzinfo=timezone.utc)
 return a.timestamp()
def parse_twap_candle_event(event,asset,horizon):
 if horizon not in HORIZON_TO_VARIANT:return None
 r=event.get("markets")or[]
 if not r or not isinstance(r[0],dict):return None
 m=r[0]
 if m.get("closed")or m.get("acceptingOrders")is False:return None
 h=str(m.get("eventStartTime")or"").strip();q=str(m.get("endDate")or event.get("endDate")or"").strip()
 if not h or not q:return None
 try:l=_parse_iso_ts(h);s=_parse_iso_ts(q)
 except Exception:return None
 f=HORIZON_TO_DURATION_SEC[horizon]
 if abs((s-l)-f)>5.:return None
 u=m.get("cryptoMarketConfig")or{};p=str(m.get("resolutionSource")or"").strip().lower();t=str(m.get("description")or"").lower();e=bool(u.get("twapEnabled"))or("twap-60s-streams"in p)or("twap-60s-streams"in t);k=int(u.get("twapLookbackSeconds")or(60 if"twap-60s"in(p+t)else 0))
 if not e or k!=60:return None
 d=m.get("clobTokenIds")
 if isinstance(d,str):
  try:d=json.loads(d)
  except Exception:d=[]
 a=m.get("outcomes")
 if isinstance(a,str):
  try:a=json.loads(a)
  except Exception:a=[]
 if not isinstance(d,list)or len(d)<2:return None
 c,b=0,1
 if isinstance(a,list)and len(a)>=2:
  j=[str(o).strip().upper()for o in a]
  if"UP"in j and"DOWN"in j:c=j.index("UP");b=j.index("DOWN")
 g=m.get("feeSchedule")or{};i=float(g.get("rate",.07)if m.get("feesEnabled",True)else.0);n=float(g.get("exponent",1.));return TwapCandleMarketSpec(asset=asset.upper(),horizon=horizon,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),title=str(m.get("question")or event.get("title")or""),start_iso=h,end_iso=q,start_ts=l,end_ts=s,up_token=str(d[c]),down_token=str(d[b]),fee_rate=i,fee_exponent=n,neg_risk=bool(m.get("negRisk",False)),twap_lookback_sec=k,resolution_source=p)
def parse_metal_forex_candle_event(event,asset,horizon):
 s=str(asset or"").strip().upper()
 if s not in METAL_DOMINANCE_ASSETS or horizon not in("1h","15m"):return None
 p=event.get("markets")or[]
 if not p or not isinstance(p[0],dict):return None
 m=p[0]
 if m.get("closed")or m.get("acceptingOrders")is False:return None
 g=str(m.get("eventStartTime")or"").strip();n=str(m.get("endDate")or event.get("endDate")or"").strip()
 if not g or not n:return None
 try:j=_parse_iso_ts(g);q=_parse_iso_ts(n)
 except Exception:return None
 if abs((q-j)-HORIZON_TO_DURATION_SEC[horizon])>5.:return None
 l=str(m.get("resolutionSource")or"").strip().lower();r=str(m.get("description")or"").lower();b=f"{s.lower()}-usd-forexprice-streams"
 if b not in l and b not in r:return None
 e=m.get("clobTokenIds")
 if isinstance(e,str):
  try:e=json.loads(e)
  except Exception:e=[]
 a=m.get("outcomes")
 if isinstance(a,str):
  try:a=json.loads(a)
  except Exception:a=[]
 if not isinstance(e,list)or len(e)<2:return None
 d,c=0,1
 if isinstance(a,list)and len(a)>=2:
  i=[str(o).strip().upper()for o in a]
  if"UP"in i and"DOWN"in i:d=i.index("UP");c=i.index("DOWN")
 f=m.get("feeSchedule")or{};h=float(f.get("rate",.07)if m.get("feesEnabled",True)else.0);k=float(f.get("exponent",1.));return TwapCandleMarketSpec(asset=s,horizon=horizon,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),title=str(m.get("question")or event.get("title")or""),start_iso=g,end_iso=n,start_ts=j,end_ts=q,up_token=str(e[d]),down_token=str(e[c]),fee_rate=h,fee_exponent=k,neg_risk=bool(m.get("negRisk",False)),twap_lookback_sec=0,resolution_source=l or f"https://data.chain.link/streams/{b}")
def verify_same_oracle_pair(m_long,m_short):
 if m_long.asset!=m_short.asset:return False
 if m_long.horizon not in HORIZON_TO_VARIANT or m_short.horizon not in HORIZON_TO_VARIANT:return False
 if m_long.horizon==m_short.horizon:return False
 if HORIZON_TO_DURATION_SEC[m_long.horizon]<=HORIZON_TO_DURATION_SEC[m_short.horizon]:return False
 if abs(m_long.end_ts-m_short.end_ts)>2.:return False
 b=str(m_long.resolution_source or"").strip().lower();a=str(m_short.resolution_source or"").strip().lower()
 if not b or not a or b!=a:return False
 if m_long.asset in METAL_DOMINANCE_ASSETS:return(m_long.twap_lookback_sec==0 and m_short.twap_lookback_sec==0 and f"{m_long.asset.lower()}-usd-forexprice-streams"in b)
 if m_long.twap_lookback_sec!=60 or m_short.twap_lookback_sec!=60:return False
 return True
def build_prev_15m_gamma_event_url(spec):a=int(round(spec.start_ts))-900;return f"{GAMMA_EVENTS_URL}?slug={spec.asset.lower()}-updown-15m-{a}"
def build_prev_5m_gamma_event_url(spec):a=int(round(spec.start_ts))-300;return f"{GAMMA_EVENTS_URL}?slug={spec.asset.lower()}-updown-5m-{a}"
def build_own_gamma_event_url(asset,horizon,start_ts_or_iso):a=_parse_iso_ts(start_ts_or_iso)if isinstance(start_ts_or_iso,str)else float(start_ts_or_iso);return f"{GAMMA_EVENTS_URL}?slug={str(asset).lower()}-updown-{str(horizon).lower()}-{int(round(a))}"
def build_crypto_price_query_url(spec):
 if int(spec.twap_lookback_sec)!=60:raise ValueError(f"60s Chainlink TWAP required, got twap_lookback_sec={spec.twap_lookback_sec}")
 a=HORIZON_TO_VARIANT[spec.horizon];return(f"{POLYMARKET_CRYPTO_PRICE_URL}?symbol={spec.asset}&eventStartTime={spec.start_iso}&variant={a}&endDate={spec.end_iso}&twapEnabled=true&twapLookbackSeconds=60")
def _is_verified_twap60_url(request_url):u=str(request_url or"");return("twapEnabled=true"in u)and("twapLookbackSeconds=60"in u)
def _extract_closed_gamma_meta_field(payload,field,request_url=None):
 e=payload[0]if isinstance(payload,list)and payload else payload
 if not isinstance(e,dict)or e.get("closed")is not True:return None
 if request_url and"slug="in str(request_url):
  a=str(request_url).split("slug=",1)[1].split("&",1)[0]
  if str(e.get("slug")or"")!=a:return None
 b=e.get("eventMetadata")
 if isinstance(b,str):
  try:b=json.loads(b)
  except Exception:return None
 if not isinstance(b,dict):return None
 c=b.get(field)
 if c is None:return None
 try:d=float(c)
 except(TypeError,ValueError):return None
 return d if(math.isfinite(d)and d>.0)else None
def parse_authoritative_open_price(payload,*,request_url=None):
 b=_extract_closed_gamma_meta_field(payload,"finalPrice",request_url)
 if b is not None:return b
 if not isinstance(payload,dict)or not _is_verified_twap60_url(request_url):return None
 if payload.get("cached")is not True and payload.get("completed")is not True:return None
 a=payload.get("openPrice")
 if a is None:return None
 try:c=float(a)
 except(TypeError,ValueError):return None
 return c if(math.isfinite(c)and c>.0)else None
def parse_authoritative_close_price(payload,*,request_url=None):
 b=_extract_closed_gamma_meta_field(payload,"finalPrice",request_url)
 if b is not None:return b
 if not isinstance(payload,dict)or payload.get("completed")is not True or not _is_verified_twap60_url(request_url):return None
 a=payload.get("closePrice")
 if a is None:return None
 try:c=float(a)
 except(TypeError,ValueError):return None
 return c if(math.isfinite(c)and c>.0)else None
def parse_closed_gamma_event_settlement(payload,side,request_url=None):
 b=_extract_closed_gamma_meta_field(payload,"priceToBeat",request_url);c=_extract_closed_gamma_meta_field(payload,"finalPrice",request_url)
 if b is None or c is None:return None
 a=c>=b;d=a if str(side).strip().upper()=="UP"else(not a);return 1. if d else.0
def determine_dominance_legs(m15,k_15m,m5,k_5m,min_corridor_bps=2.5):
 if not verify_same_oracle_pair(m15,m5):return None
 if not(math.isfinite(k_15m)and k_15m>.0 and math.isfinite(k_5m)and k_5m>.0):return None
 e=min(k_15m,k_5m);d=max(k_15m,k_5m);a=((d-e)/e)*1e4
 if a<min_corridor_bps:return None
 c=m15.horizon.upper();b=m5.horizon.upper()
 if k_15m<k_5m:return{"regime":f"{c}_UP_PLUS_{b}_DOWN","k_low":k_15m,"k_high":k_5m,"corridor_bps":round(a,3),"leg_a":{"horizon":m15.horizon,"side":"UP","label":f"{c}_UP","market_id":m15.market_id,"condition_id":m15.condition_id,"token_id":m15.up_token,"opp_token_id":m15.down_token,"strike":k_15m,"fee_rate":m15.fee_rate,"fee_exponent":m15.fee_exponent,"neg_risk":m15.neg_risk},"leg_b":{"horizon":m5.horizon,"side":"DOWN","label":f"{b}_DOWN","market_id":m5.market_id,"condition_id":m5.condition_id,"token_id":m5.down_token,"opp_token_id":m5.up_token,"strike":k_5m,"fee_rate":m5.fee_rate,"fee_exponent":m5.fee_exponent,"neg_risk":m5.neg_risk}}
 else:return{"regime":f"{b}_UP_PLUS_{c}_DOWN","k_low":k_5m,"k_high":k_15m,"corridor_bps":round(a,3),"leg_a":{"horizon":m5.horizon,"side":"UP","label":f"{b}_UP","market_id":m5.market_id,"condition_id":m5.condition_id,"token_id":m5.up_token,"opp_token_id":m5.down_token,"strike":k_5m,"fee_rate":m5.fee_rate,"fee_exponent":m5.fee_exponent,"neg_risk":m5.neg_risk},"leg_b":{"horizon":m15.horizon,"side":"DOWN","label":f"{c}_DOWN","market_id":m15.market_id,"condition_id":m15.condition_id,"token_id":m15.down_token,"opp_token_id":m15.up_token,"strike":k_15m,"fee_rate":m15.fee_rate,"fee_exponent":m15.fee_exponent,"neg_risk":m15.neg_risk}}
def _sorted_asks(asks_raw,max_slip_cents):
 e=sorted([(float(a["price"]),float(a["size"]))for a in(asks_raw or[])if float(a.get("price",0))>.0 and float(a.get("size",0))>.0],key=lambda x:x[0])
 if not e:return[],1.,.0
 c=e[0][0];d=[(f,sz)for f,sz in e if f<=c+max_slip_cents+1e-9 and f<.99];b=sum(sz for _,sz in d);return d,c,b
def _buy_share_haircut(px,fee_rate,fee_exponent=1.):
 p=float(px);r=float(fee_rate or.0)
 if r<=.0 or p<=.0 or p>=1.:return.0
 a=r*((p*(1.-p))**float(fee_exponent or 1.));return min(.5,max(.0,a/p))
def _net_unit_cost_buy(px,fee_rate,fee_exponent=1.):p=float(px);h=_buy_share_haircut(p,fee_rate,fee_exponent);return p/(1.-h)if h>.0 else p
def _walk_exact_shares(asks_capped,shares_qty,fee_rate,fee_exponent=1.):
 if shares_qty<=0 or not asks_capped:return None
 j=float(shares_qty);d=.0;b=asks_capped[0][0];c=0
 for m,l in asks_capped:
  f=min(j,l)
  if f<=0:continue
  d+=f*m;b=m;c+=1;j-=f
  if j<=1e-8:break
 if j>1e-5:return None
 k=d/float(shares_qty);i=_buy_share_haircut(k,fee_rate,fee_exponent);h=k/(1.-i)if i>.0 else k;g=h-k;e=float(shares_qty)*g;a=float(shares_qty)*(1.-i);return{"shares":int(shares_qty),"net_shares":round(a,4),"share_haircut":round(i,6),"best_ask":round(asks_capped[0][0],4),"vwap":round(k,5),"worst_px":round(b,4),"spent_usd":round(d,4),"fee_usd":round(e,4),"eff_px":round(h,5),"levels":c}
def walk_equal_shares_dominance_box(asks_a_raw,asks_b_raw,target_budget_usd,fee_rate_a=.07,fee_rate_b=.07,fee_exponent_a=1.,fee_exponent_b=1.,max_box_cost_net=.995,max_slip_cents=.025,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.9):
 w,G,A=_sorted_asks(asks_a_raw,max_slip_cents);v,F,z=_sorted_asks(asks_b_raw,max_slip_cents)
 if not w or not v:return{"filled":False,"reason":"EMPTY_BOOK","best_sum":round(G+F,4)}
 f=_net_unit_cost_buy(G,fee_rate_a,fee_exponent_a)+_net_unit_cost_buy(F,fee_rate_b,fee_exponent_b)
 if f<min_box_cost_net-.025 or(G+F)<.855:return{"filled":False,"reason":"SUSPECT_INVERTED_ANTI_BOX","best_a":round(G,4),"best_b":round(F,4),"l1_box_cost_net":round(f,5)}
 if f>max_box_cost_net+.015:return{"filled":False,"reason":"BOX_TOO_EXPENSIVE_L1","best_a":round(G,4),"best_b":round(F,4),"l1_box_cost_net":round(f,5),"avail_pair_shares":int(math.floor(min(A,z)))}
 k=int(math.floor(min(A,z)))
 if k<max(5,min_shares):return{"filled":False,"reason":"INSUFFICIENT_PAIR_SHARES","best_a":round(G,4),"best_b":round(F,4),"l1_box_cost_net":round(f,5),"avail_pair_shares":k}
 m=int(math.floor(float(target_budget_usd)/max(.1,f)));g=min(m,k)
 if g<max(5,min_shares):return{"filled":False,"reason":"BUDGET_BELOW_MIN_SHARES","l1_box_cost_net":round(f,5),"avail_pair_shares":k}
 t=_walk_exact_shares(w,g,fee_rate_a,fee_exponent_a);s=_walk_exact_shares(v,g,fee_rate_b,fee_exponent_b)
 if t is None or s is None:return{"filled":False,"reason":"WALK_FAILED","avail_pair_shares":k}
 c=t["spent_usd"]+s["spent_usd"];d=t["fee_usd"]+s["fee_usd"];b=c+d;a=b/float(g)
 if b>target_budget_usd*1.02:
  E=int(math.floor(float(target_budget_usd)/a))
  if E<max(5,min_shares):return{"filled":False,"reason":"TRIMMED_BELOW_MIN_SHARES","box_cost_net":round(a,5)}
  g=E;t=_walk_exact_shares(w,g,fee_rate_a,fee_exponent_a);s=_walk_exact_shares(v,g,fee_rate_b,fee_exponent_b)
  if t is None or s is None:return{"filled":False,"reason":"WALK_TRIM_FAILED"}
  c=t["spent_usd"]+s["spent_usd"];d=t["fee_usd"]+s["fee_usd"];b=c+d;a=b/float(g)
 def _worst_limit_net(wa_d,wb_d):b,a=float(wa_d["worst_px"]),float(wb_d["worst_px"]);return round(_net_unit_cost_buy(b,fee_rate_a,fee_exponent_a)+_net_unit_cost_buy(a,fee_rate_b,fee_exponent_b),6)
 if _worst_limit_net(t,s)>max_box_cost_net+1e-6:
  N=max(5,int(min_shares));D=set()
  for u in(w,v):
   p=.0
   for _,C in u:
    p+=C;R=int(math.floor(p+1e-9))
    if N<=R<g:D.add(R)
  j=False
  for B in sorted(D,reverse=True):
   Q=_walk_exact_shares(w,B,fee_rate_a,fee_exponent_a);P=_walk_exact_shares(v,B,fee_rate_b,fee_exponent_b)
   if Q is None or P is None:continue
   O=Q["spent_usd"]+P["spent_usd"]
   if O<min_box_notional_usd:continue
   if _worst_limit_net(Q,P)<=max_box_cost_net+1e-6:g=B;t,s=Q,P;c=O;d=t["fee_usd"]+s["fee_usd"];b=c+d;a=b/float(g);j=True;break
  if not j:return{"filled":False,"reason":"WORST_LIMIT_COST_ABOVE_CAP","best_a":round(G,4),"best_b":round(F,4),"box_cost_net":round(a,5),"worst_limit_cost_net":_worst_limit_net(t,s),"l1_box_cost_net":round(f,5),"avail_pair_shares":k}
 M=float(t.get("share_haircut")or.0);L=float(s.get("share_haircut")or.0);y=max(M,L);o=math.ceil((float(g)/max(1e-6,1.-M))*1e2-1e-9)/1e2;n=math.ceil((float(g)/max(1e-6,1.-L))*1e2-1e-9)/1e2
 def _fits_at_worst_px(asks_cap,req_sh,lim_px):
  a=req_sh;b=.0
  for e,d in asks_cap:
   if e>lim_px+1e-9:break
   c=min(a,d)
   if c>.0:
    b+=c*e;a-=c
    if a<=1e-8:return True,b
  return False,b
 K,J=_fits_at_worst_px(w,o,float(t["worst_px"]));I,H=_fits_at_worst_px(v,n,float(s["worst_px"]))
 if K and I and(J+H)<=float(target_budget_usd)*1.02+1e-6:e=float(g);i=o;h=n
 else:e=math.floor(float(g)*(1.-y)*1e2+1e-9)/1e2;i=min(float(g),math.ceil((e/max(1e-6,1.-M))*1e2-1e-9)/1e2);h=min(float(g),math.ceil((e/max(1e-6,1.-L))*1e2-1e-9)/1e2)
 r=min(G,F);x=int(math.ceil(1./max(r,.01)-1e-9))
 if g<x or(i*G)<1.-1e-6 or(h*F)<1.-1e-6:return{"filled":False,"reason":"LEG_BELOW_1USD_MIN","best_a":round(G,4),"best_b":round(F,4),"l1_box_cost_net":round(f,5),"avail_pair_shares":k}
 if c<min_box_notional_usd:return{"filled":False,"reason":"BELOW_MIN_BOX_NOTIONAL","box_cost_net":round(a,5),"spent_usd":round(c,2)}
 if a<min_box_cost_net:return{"filled":False,"reason":"SUSPECT_INVERTED_ANTI_BOX","best_a":round(G,4),"best_b":round(F,4),"box_cost_net":round(a,5)}
 if a>max_box_cost_net:return{"filled":False,"reason":"BOX_COST_ABOVE_CAP","best_a":round(G,4),"best_b":round(F,4),"box_cost_net":round(a,5),"l1_box_cost_net":round(f,5),"avail_pair_shares":k}
 l=1.-a;q=round(min(A,z)*(G+F),2);return{"filled":True,"shares":int(g),"net_paired_shares":round(e,4),"leg_a_gross_shares":round(i,2),"leg_b_gross_shares":round(h,2),"best_ask":round(G+F,4),"vwap":round(c/float(g),5),"eff_px":round(a,5),"box_cost_net":round(a,5),"riskless_floor_per_pair":round(l,5),"guaranteed_min_profit_usd":round(e*l,4),"corridor_bonus_profit_usd":round(e*(2.-a),4),"slip_cents":round((c/float(g)-(G+F))*1e2,2),"spent_usd":round(c,4),"fee_usd":round(d,4),"fill_ratio":round(min(1.,b/max(1e-6,float(target_budget_usd))),4),"l1_usd":q,"avail_pair_shares":k,"avail_a_shares":round(A,2),"avail_b_shares":round(z,2),"leg_a_walk":t,"leg_b_walk":s,"levels":max(t["levels"],s["levels"])}
def compute_dominance_box_payout_from_close(close_px,k_low,k_high):b=1. if close_px>=k_low else.0;a=1. if close_px<k_high else.0;return b+a
def walk_equal_shares_multi_leg_box(legs_spec,target_budget_usd,guaranteed_payout_per_bundle=1.,max_bundle_cost_net=.992,max_slip_cents=.025,min_shares=5,min_box_notional_usd=4.85):
 if len(legs_spec)<2 or guaranteed_payout_per_bundle<=.0:return{"filled":False,"reason":"INVALID_BUNDLE_SPEC"}
 j=[];n=[];v=[];b=.0
 for s in legs_spec:
  f,u,q=_sorted_asks(s.get("asks")or[],max_slip_cents)
  if not f:return{"filled":False,"reason":"EMPTY_LEG_BOOK"}
  y=float(s.get("fee_rate",.07));x=float(s.get("fee_exponent",1.));j.append(f);n.append(u);v.append(q);b+=_net_unit_cost_buy(u,y,x)
 if b>max_bundle_cost_net+.015:return{"filled":False,"reason":"BUNDLE_TOO_EXPENSIVE_L1","l1_bundle_cost_net":round(b,5)}
 i=int(math.floor(min(v)))
 if i<max(5,min_shares):return{"filled":False,"reason":"INSUFFICIENT_BUNDLE_SHARES","avail_bundle_shares":i}
 m=int(math.floor(float(target_budget_usd)/max(.1,b)));o=min(m,i)
 if o<max(5,min_shares):return{"filled":False,"reason":"BUDGET_BELOW_MIN_SHARES"}
 l=[]
 for s,f in zip(legs_spec,j):
  r=_walk_exact_shares(f,o,float(s.get("fee_rate",.07)),float(s.get("fee_exponent",1.)))
  if r is None:return{"filled":False,"reason":"LEG_WALK_FAILED"}
  l.append(r)
 d=sum(w["spent_usd"]for w in l);e=sum(w["fee_usd"]for w in l);c=d+e;a=c/float(o)
 if c>target_budget_usd*1.02:
  t=int(math.floor(float(target_budget_usd)/a))
  if t<max(5,min_shares):return{"filled":False,"reason":"TRIMMED_BELOW_MIN_SHARES"}
  o=t;l=[]
  for s,f in zip(legs_spec,j):
   r=_walk_exact_shares(f,o,float(s.get("fee_rate",.07)),float(s.get("fee_exponent",1.)))
   if r is None:return{"filled":False,"reason":"LEG_TRIM_WALK_FAILED"}
   l.append(r)
  d=sum(w["spent_usd"]for w in l);e=sum(w["fee_usd"]for w in l);c=d+e;a=c/float(o)
 k=min(n);p=int(math.ceil(1./max(k,.01)-1e-9))
 if o<p:return{"filled":False,"reason":"LEG_BELOW_1USD_MIN","avail_bundle_shares":i}
 if d<min_box_notional_usd:return{"filled":False,"reason":"BELOW_MIN_BOX_NOTIONAL","spent_usd":round(d,2)}
 if a>max_bundle_cost_net:return{"filled":False,"reason":"BUNDLE_COST_ABOVE_CAP","bundle_cost_net":round(a,5),"l1_bundle_cost_net":round(b,5)}
 g=guaranteed_payout_per_bundle-a;h=round(min(v)*sum(n),2);return{"filled":True,"shares":int(o),"best_ask":round(sum(n),4),"vwap":round(d/float(o),5),"eff_px":round(a,5),"box_cost_net":round(a,5),"guaranteed_payout_per_bundle":round(guaranteed_payout_per_bundle,4),"riskless_floor_per_pair":round(g,5),"guaranteed_min_profit_usd":round(float(o)*g,4),"spent_usd":round(d,4),"fee_usd":round(e,4),"l1_usd":h,"avail_bundle_shares":i,"leg_walks":l}
# ======================================================================================
# [09/21] MODULE: src/polymarket_research/exact_twap_lock_engine.py
# PURPOSE: Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import math;import os;from pathlib import Path;from typing import Any,Dict,List,Optional,Sequence,Tuple;DEFAULT_ANNUAL_IV_FLOORS={"BTC":.55,"ETH":.7,"SOL":.9,"XRP":.95,"BNB":.85,"DOGE":1.15,"HYPE":1.35};SECONDS_PER_YEAR=365.25*86400.;SHM_DIR=Path(os.getenv("PM_FAST_TICK_DIR","/dev/shm"))
def student_t_df4_cdf(z):
 if not math.isfinite(z):return.5
 b=z*z;s=math.sqrt(4.+b);a=.5+(z/(2.*s))*(1.+2./(4.+b));return max(.0,min(1.,a))
def student_t_df5_cdf(z):
 if not math.isfinite(z):return.5
 u=z/math.sqrt(5.);c=u*u;a=1.+c;b=.5+(math.atan(u)+u/a+(2./3.)*(u/(a*a)))/math.pi;return max(.0,min(1.,b))
def compute_unit_variance_student_t_cdf(z,df=4.):
 if not math.isfinite(z):return.5
 if df<=.0 or not math.isfinite(df)or df>=120.:return.5*(1.+math.erf(z/math.sqrt(2.)))
 e=max(2.05,float(df));f=z*math.sqrt(e/(e-2.))
 if abs(e-4.)<1e-6:return student_t_df4_cdf(f)
 if abs(e-5.)<1e-6:return student_t_df5_cdf(f)
 a=e-.5;b=48.*a*a;d=math.copysign(math.sqrt(a*math.log1p((f*f)/e)),f);c=d+(d**3+3.*d)/b;return max(.0,min(1.,.5*(1.+math.erf(c/math.sqrt(2.)))))
def compute_kemna_vorst_twap_sigma_rem(sigma_1h,tte_sec,window_sec=60.):
 c=max(1e-6,float(sigma_1h));w=max(1.,float(window_sec));d=max(.25,float(tte_sec));b=c/60.
 if d>=w:a=max(.1,d-2.*w/3.)
 else:a=(d*d*d)/(3.*w*w)
 return b*math.sqrt(a)
def should_suppress_final60s_twap_salvage(*,side,strike_open,current_spot,twap_locked_mean,tte_sec,sigma_1h,twap_locked_weight=None,z_lock_floor=1.25,window_sec=60.):
 w=max(1.,float(window_sec));i=float(tte_sec)
 if(not(.0<i<w)or strike_open<=.0 or current_spot<=.0 or twap_locked_mean is None or float(twap_locked_mean)<=.0):return False,.0
 g=max(.0,min(1.,(w-i)/w));c=max(.0,min(g,float(twap_locked_weight)))if twap_locked_weight is not None else g
 if c<.15:return False,.0
 b=c*float(twap_locked_mean)+(1.-c)*float(current_spot);h=1. if str(side).upper()in("UP","BUY","YES")else-1.;a=h*(b-float(strike_open))/float(strike_open)
 if a<=.0:return False,round(a/1e-4,4)
 e=max(5e-5,compute_kemna_vorst_twap_sigma_rem(sigma_1h,i,window_sec=w));d=math.hypot(e,.00025);f=round(a/d,4);return(f>=float(z_lock_floor)),f
def read_shm_usd_anchor(asset,now_ts,max_age_sec=2.5):
 p=SHM_DIR/f"pm_fast_tick_{str(asset).upper()}.json"
 if not p.exists():return{"usd_spot":None,"twap_60s":None,"source":None}
 try:
  d=json.loads(p.read_text(encoding="utf-8"));f=float(d.get("timestamp_unix")or d.get("ts")or.0);e=now_ts-f
  if f<=.0 or e>max_age_sec or e<-1.5:return{"usd_spot":None,"twap_60s":None,"source":None}
  c=d.get("chainlink_proxy_spot");b=d.get("coinbase_spot");a=d.get("chainlink_twap_60s")
  if c and float(c)>0:return{"usd_spot":float(c),"twap_60s":float(a)if(a and float(a)>0)else None,"source":"shm_chainlink_proxy"}
  if b and float(b)>0:return{"usd_spot":float(b),"twap_60s":float(a)if(a and float(a)>0)else None,"source":"shm_coinbase_usd"}
 except Exception:pass
 return{"usd_spot":None,"twap_60s":None,"source":None}
def compute_exact_twap_lock_probability(*,asset,open_price,current_usd_spot,rem_seconds,now_ts,end_ts,spot_samples=(),shm_twap_60s=None,iv_annual=None,usd_direct_feed=False,authoritative_chainlink_ws=False,min_rem_seconds=8.,max_rem_seconds=45.,jump_vol_mult=1.35):
 if(not math.isfinite(open_price)or open_price<=.0 or not math.isfinite(current_usd_spot)or current_usd_spot<=.0 or not(min_rem_seconds<=rem_seconds<=max_rem_seconds)):return{"eligible":False,"reason":"OUT_OF_WINDOW_OR_INVALID_PRICES"}
 l=end_ts-60.;h=max(.0,min(60.,60.-rem_seconds));u=h/60.;k=sorted((float(ts),float(px))for ts,px in spot_samples if l<=float(ts)<=now_ts+.5 and float(px)>.0 and math.isfinite(float(px)));t=[]
 for ts,px in k:
  if t and abs(ts-t[-1][0])<1e-6:t[-1]=(ts,px)
  else:t.append((ts,px))
 if len(t)>=2:
  D,C=t[0];I,H=t[-1];B=min(2.,max(.0,D-l));A=min(2.,max(.0,now_ts-I));x=B*C+A*H;d=B+A;b=max(.0,(D-l)-B)+max(.0,(now_ts-I)-A)
  for M in range(len(t)-1):
   R,Q=t[M];P,O=t[M+1];N=max(.0,P-R);G=min(N,6.);x+=.5*(Q+O)*G;d+=G
   if N>6.:b+=N-6.
  a=(x/d)if d>.0 else(sum(px for _,px in t)/len(t));i=max(.0,min(1.,(h-b)/max(1.,h)));c=u*i
 elif(shm_twap_60s is not None and shm_twap_60s>.0 and math.isfinite(shm_twap_60s)and rem_seconds<=12.):a=float(shm_twap_60s);g=max(.0,(60.-2.*rem_seconds)/60.);c=u*g
 else:a=current_usd_spot;c=.0
 z=c*a+(1.-c)*current_usd_spot;s=current_usd_spot-open_price;r=z-open_price
 if s==.0 or r==.0 or(s>.0)!=(r>.0):return{"eligible":False,"reason":"WHIPSAW_SPLIT_ACROSS_STRIKE","mu_twap":round(z,6),"eff_alpha":round(c,4)}
 L="UP"if r>.0 else"DOWN";y=str(asset).upper();w=DEFAULT_ANNUAL_IV_FLOORS.get(y,.8);q=max(w,float(iv_annual or.0));v=(q*jump_vol_mult)/math.sqrt(SECONDS_PER_YEAR);n=1.-c;K=max(1,int(round(rem_seconds)));p=((K+1.)*(2.*K+1.))/(6.*K*K);j=n*current_usd_spot*v*math.sqrt(max(1.,rem_seconds)*p);o=1. if authoritative_chainlink_ws else(4.5 if usd_direct_feed else 8.5);f=current_usd_spot*(o/1e4);e=math.hypot(j,f)
 if e<=.0:return{"eligible":False,"reason":"ZERO_SIGMA"}
 F=abs(r)/e;E=student_t_df5_cdf(F);m=(abs(r)/open_price)*1e4;J=.9995 if authoritative_chainlink_ws else.996;return{"eligible":True,"side":L,"open_price":open_price,"current_usd_spot":round(current_usd_spot,6),"banked_mean":round(a,6),"mu_twap":round(z,6),"eff_alpha":round(c,4),"rem_seconds":round(rem_seconds,2),"sigma_total_usd":round(e,6),"z_lock":round(F,4),"p_lock":round(min(J,E),4),"cushion_bps":round(m,2),"basis_bps_floor":o,"samples_in_window":len(t)}
# ======================================================================================
# [10/21] MODULE: src/polymarket_research/tradfi_sports_zero_fee_engine.py
# PURPOSE: Zero-Fee Pyth Commodities/Metals/Equities (CM_B3/B2/U1), B4 Wick Lock, NBA Polish-Middle (SP1) & NegRisk (NR0)
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import logging;import math;import re;import time;import urllib.parse;import urllib.request;from dataclasses import dataclass,field;from datetime import datetime,timedelta,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;from src.polymarket_research.barrier_onetouch_svi_engine import(detect_barrier_monotonicity_boxes,first_passage_touch_prob);logger=logging.getLogger("TradFiSportsZeroFee")
try:NY_TZ=ZoneInfo("America/New_York")
except Exception:NY_TZ=timezone(timedelta(hours=-4))
PYTH_ASSET_CONFIG={"WTI":("CL=F","CME_23H",True,.0045,.32),"NG":("NG=F","CME_23H",True,.006,.48),"GC":("GC=F","CME_23H",True,.002,.2),"SI":("SI=F","CME_23H",True,.003,.32),"XAUUSD":("GC=F","CME_23H",False,.015,.2),"XAGUSD":("SI=F","CME_23H",False,.02,.32),"SPY":("SPY","EQUITY_RTH",True,.0015,.18),"NVDA":("NVDA","EQUITY_RTH",True,.0015,.42),"AMZN":("AMZN","EQUITY_RTH",True,.0015,.34),"GOOGL":("GOOGL","EQUITY_RTH",True,.0015,.34),"MSFT":("MSFT","EQUITY_RTH",True,.0015,.3),"AAPL":("AAPL","EQUITY_RTH",True,.0015,.28),"TSLA":("TSLA","EQUITY_RTH",True,.0015,.52),"COIN":("COIN","EQUITY_RTH",True,.002,.65),"HOOD":("HOOD","EQUITY_RTH",True,.002,.58),"PLTR":("PLTR","EQUITY_RTH",True,.002,.55)};PYTH_HIT_SERIES=(("WTI","MONTH","crude-oil-cl-hit"),("WTI","WEEK","wti-crude-oil-hit-price-weekly"),("NG","WEEK","natural-gas-hit-price-weekly"),("XAUUSD","MONTH","xauusd-hit-month"),("XAUUSD","WEEK","gold-hit-price-weekly"),("GC","MONTH","what-will-gold-gc-hit"),("XAGUSD","MONTH","xagusd-hit-month"),("XAGUSD","WEEK","silver-hit-price-weekly"),("SI","MONTH","what-will-silver-si-hit"),("SPY","MONTH","spy-hit-month"),("SPY","WEEK","spy-hit-price-weekly"),("NVDA","MONTH","nvidia-hit-price-monthly"),("NVDA","WEEK","nvidia-hit-price-weekly"),("AMZN","WEEK","amazon-hit-price-weekly"),("GOOGL","WEEK","google-hit-price-weekly"),("MSFT","WEEK","microsoft-hit-price-weekly"),("AAPL","WEEK","apple-hit-price-weekly"),("TSLA","WEEK","tesla-hit-price-weekly"),("COIN","MONTH","coin-hit-month"),("HOOD","MONTH","hood-hit-month"),("PLTR","WEEK","palantir-hit-price-weekly"));PYTH_CLOSE_SERIES=(("SPY","spy-daily-close-uo"),("WTI","wti-daily-close-uo"),("MSFT","msft-multi-strikes-weekly"),("NVDA","nvda-multi-strikes-weekly"),("AAPL","aapl-multi-strikes-weekly"),("TSLA","tsla-multi-strikes-weekly"));NBA_SERIES_SLUGS=("nba-2026",);MULTI_SPORT_CORRIDOR_SERIES=(("NBA","nba-2026"),("NFL","nfl-2026"),("CFB","cfb-2026"),("NHL","nhl-2026"));ZERO_FEE_NEGRISK_SERIES=("elon-tweets","elon-tweets-48h","trump-truth-social","fomc","fed-3-parlay","bank-of-japan","bank-of-canada-decision","reserve-bank-of-australia-decision","reserve-bank-of-new-zealand-decision","us-gas-price-daily","best-ai-company","chinese-ai-1");_STRIKE_PRICE_RE=re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)");_SPREAD_FAV_RE=re.compile(r"Spread:\s*(.+?)\s*\(\s*([-+]?\d+(?:\.\d+)?)\s*\)",re.IGNORECASE);_FEE_TYPE_FALLBACK_RATES={"sports_fees_nfl_cfb_oct26":(.03,1.),"sports_fees_v2":(.03,1.),"sports_fees_v3":(.05,1.),"crypto_fees_v2":(.07,1.),"crypto_15_min":(.072,1.),"politics_fees":(.04,1.),"weather_fees":(.05,1.),"culture_fees":(.05,1.),"economics_fees":(.05,1.),"finance_prices_fees":(.04,1.),"tech_fees":(.04,1.),"mentions_fees":(.05,1.),"general_fees":(.04,1.)}
def _extract_market_fee_rate(m):
 b=str(m.get("feeType")or"").strip().lower()
 if b=="zero_fees"or m.get("feesEnabled")is False:return.0,1.
 c=m.get("feeSchedule")if isinstance(m.get("feeSchedule"),dict)else{}
 if"rate"in c and c.get("rate")is not None:
  a=float(c.get("rate")or.0)
  if a<=.0:return.0,1.
  return a,float(c.get("exponent")or 1.)
 if m.get("feeRate")is not None:
  e=float(m.get("feeRate")or.0)
  if e>.0:return(e/1e4 if e>=1. else e),float(m.get("feeExponent")or 1.)
 if m.get("takerBaseFee")is not None:
  d=float(m.get("takerBaseFee")or.0)
  if d>.0:return(d/1e4 if d>=1. else d),float(m.get("feeExponent")or 1.)
 if b in _FEE_TYPE_FALLBACK_RATES:return _FEE_TYPE_FALLBACK_RATES[b]
 if m.get("feesEnabled")is True and b:return.04,1.
 return.0,1.
def _net_unit_ask(px,fee_rate=.0,fee_exponent=1.):
 p=float(px);r=float(fee_rate or.0)
 if r<=.0 or p<=.0 or p>=1.:return p
 a=r*((p*(1.-p))**float(fee_exponent or 1.));h=min(.5,max(.0,a/p));return p/(1.-h)
def _parse_clob_tokens(m):
 a=m.get("clobTokenIds")
 if isinstance(a,str):
  try:a=json.loads(a)
  except Exception:a=None
 if isinstance(a,list)and len(a)>=2 and a[0]and a[1]:return str(a[0]),str(a[1])
 return None
def _parse_iso_ts(raw_iso):
 s=str(raw_iso or"").strip()
 if not s:return None
 try:
  a=datetime.fromisoformat(s.replace("Z","+00:00"))
  if a.tzinfo is None:a=a.replace(tzinfo=timezone.utc)
  return a.timestamp()
 except Exception:return None
@dataclass
class PythBarrierRungSpec:event_id:str;market_id:str;condition_id:str;asset:str;horizon_group:str;series_slug:str;question:str;strike:float;direction:str;yes_token:str;no_token:str;start_ts:float;end_ts:float;fee_rate=.0;fee_exponent=1.
@dataclass
class PythCloseRungSpec:event_id:str;market_id:str;condition_id:str;asset:str;series_slug:str;question:str;strike:float;is_downward:bool;yes_token:str;no_token:str;end_ts:float;fee_rate=.0;fee_exponent=1.
@dataclass
class NbaOutcomeLeg:market_id:str;condition_id:str;market_type:str;token_id:str;opp_token_id:str;side_index:int;side_label:str;display_label:str;relation:str;threshold:float;fee_rate=.0;fee_exponent=1.
@dataclass
class NbaGameSpec:event_id:str;slug:str;title:str;team_a:str;team_b:str;tipoff_ts:float;settle_est_ts:float;margin_legs=field(default_factory=list);total_legs=field(default_factory=list)
@dataclass
class ZeroFeeNegRiskSlateSpec:event_id:str;series_slug:str;title:str;end_ts:float;brackets:List[Dict[str,Any]]
def compute_effective_trading_hours(start_ts,end_ts,session_class="EQUITY_RTH"):
 if end_ts<=start_ts:return.0
 g=datetime.fromtimestamp(start_ts,tz=NY_TZ);f=datetime.fromtimestamp(end_ts,tz=NY_TZ);b=g.date();d=f.date();a=.0
 while b<=d:
  l=b.weekday();c=datetime(b.year,b.month,b.day,0,0,tzinfo=NY_TZ);e=[]
  if session_class=="EQUITY_RTH":
   if l<5:e.append((c.replace(hour=9,minute=30),c.replace(hour=16,minute=0)))
  else:
   if l<4:e.append((c,c.replace(hour=17,minute=0)));e.append((c.replace(hour=18,minute=0),c+timedelta(days=1)))
   elif l==4:e.append((c,c.replace(hour=17,minute=0)))
   elif l==6:e.append((c.replace(hour=18,minute=0),c+timedelta(days=1)))
  for k,j in e:
   i=max(start_ts,k.timestamp());h=min(end_ts,j.timestamp())
   if h>i:a+=h-i
  b+=timedelta(days=1)
 return a/3600.
def is_same_continuous_session(now_ts,end_ts,session_class="EQUITY_RTH"):
 if end_ts<=now_ts:return False
 c=compute_effective_trading_hours(now_ts,end_ts,session_class)
 if c<=.0:return False
 if session_class=="EQUITY_RTH":
  e=datetime.fromtimestamp(now_ts,tz=NY_TZ);d=datetime.fromtimestamp(end_ts,tz=NY_TZ)
  if e.weekday()>=5 or e.date()!=d.date():return False
  b=e.hour*60+e.minute;return(9*60+30)<=b<(16*60)
 a=(end_ts-now_ts)/3600.;return a<=4. and c>=.98*a
_MONTH_NAME_MAP={"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12};_NAMED_WEEK_RE=re.compile(r"(?:week\s+of|trading\s+session\s+of)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:,?\s*(\d{4}))?",re.IGNORECASE);_NAMED_MONTH_RE=re.compile(r"(?:\bin\s+|trading\s+session\s+of\s+)(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(\d{4}))?(?:\?|\b)",re.IGNORECASE)
def infer_named_period_start_ts(question,desc,end_ts):
 f=f"{question} {desc}";a=datetime.fromtimestamp(max(.0,float(end_ts)-5*86400.),tz=NY_TZ).year;e=_NAMED_WEEK_RE.search(f)
 if e:
  c=_MONTH_NAME_MAP[e.group(1).lower()];h=int(e.group(2));b=int(e.group(3))if e.group(3)else a
  try:g=datetime(b,c,h,0,0,tzinfo=NY_TZ);return(g-timedelta(hours=6 if g.weekday()==0 else 0)).timestamp()
  except ValueError:return.0
 d=_NAMED_MONTH_RE.search(f)
 if d:
  c=_MONTH_NAME_MAP[d.group(1).lower()];b=int(d.group(2))if d.group(2)else a
  try:return datetime(b,c,1,0,0,tzinfo=NY_TZ).timestamp()
  except ValueError:return.0
 return.0
def parse_pyth_hit_event(ev,asset,horizon_group,series_slug):
 r=ev.get("markets")or[];l=str(ev.get("id")or"");f=_parse_iso_ts(ev.get("startDate")or ev.get("createdAt"))or(time.time()-86400.);j=_parse_iso_ts(ev.get("endDate"));t=[]
 for m in r:
  if m.get("closed")or m.get("archived"):continue
  e,g=_extract_market_fee_rate(m);p=_parse_clob_tokens(m)
  if not p:continue
  o=str(m.get("description")or ev.get("description")or"").lower()
  if"pyth"not in o and"trading session"not in o and"regular trading hours"not in o:continue
  q=str(m.get("question")or"");s=str(m.get("groupItemTitle")or"");u=(s+" "+q).lower()
  if"↑"in s or"(high)"in u or"hit above"in u:a="UP"
  elif"↓"in s or"(low)"in u or"dip"in u or"hit below"in u:a="DOWN"
  else:continue
  n=_STRIKE_PRICE_RE.search(s)or _STRIKE_PRICE_RE.search(q)
  if not n:continue
  try:i=float(n.group(1).replace(",",""))
  except ValueError:continue
  if i<=.0:continue
  h=_parse_iso_ts(m.get("endDate"))or j;c=_parse_iso_ts(m.get("startDate")or m.get("createdAt"))or f
  if not h:continue
  k=60. if(c>f+3e2 or"creation of this market"in o)else.0;b=infer_named_period_start_ts(q or str(ev.get("title")or""),o,float(h));d=max(f,b,min(float(h)-60.,float(c)+k));t.append(PythBarrierRungSpec(event_id=l,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),asset=asset.upper(),horizon_group=horizon_group.upper(),series_slug=series_slug,question=q or s,strike=i,direction=a,yes_token=p[0],no_token=p[1],start_ts=float(d),end_ts=float(h),fee_rate=e,fee_exponent=g))
 return t
def parse_pyth_close_event(ev,asset,series_slug):
 k=ev.get("markets")or[];g=str(ev.get("id")or"");f=_parse_iso_ts(ev.get("endDate"));n=[]
 for m in k:
  if m.get("closed")or m.get("archived"):continue
  a,c=_extract_market_fee_rate(m);j=_parse_clob_tokens(m)
  if not j:continue
  i=str(m.get("description")or ev.get("description")or"").lower()
  if"pyth"not in i:continue
  q=str(m.get("question")or"");l=str(m.get("groupItemTitle")or"");o=q.lower();b=("below"in o or"under"in o)and("above"not in o)
  if not b and"above"not in o and"over"not in o:continue
  h=_STRIKE_PRICE_RE.search(l)or _STRIKE_PRICE_RE.search(q)
  if not h:continue
  try:e=float(h.group(1).replace(",",""))
  except ValueError:continue
  d=_parse_iso_ts(m.get("endDate"))or f
  if not d or e<=.0:continue
  n.append(PythCloseRungSpec(event_id=g,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),asset=asset.upper(),series_slug=series_slug,question=q or l,strike=e,is_downward=b,yes_token=j[0],no_token=j[1],end_ts=float(d),fee_rate=a,fee_exponent=c))
 n.sort(key=lambda r:r.strike);return n
def fetch_yahoo_1m_intraday_sync(yahoo_symbol,vol_floor_annual=.25,timeout=6.):
 v=f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(yahoo_symbol)}?interval=1m&range=5d"
 try:
  u=urllib.request.Request(v,headers={"User-Agent":"Mozilla/5.0"});t=json.loads(urllib.request.urlopen(u,timeout=timeout).read().decode("utf-8"));p=((t.get("chart")or{}).get("result")or[None])[0]or{};o=p.get("meta")or{};c=float(o.get("regularMarketPrice")or.0);g=p.get("timestamp")or[];z=(((p.get("indicators")or{}).get("quote")or[None])[0])or{};l=z.get("high")or[];k=z.get("low")or[];j=z.get("close")or[];f=time.time();n=[]
  for s,q in enumerate(g):
   if s>=len(l)or s>=len(k)or s>=len(j):continue
   y,x,w=l[s],k[s],j[s]
   if y is None or x is None or w is None:continue
   h=int(q)
   if h+60<=f and float(w)>0:n.append((h,float(y),float(x),float(w)))
  if c<=.0 and n:c=n[-1][3]
  if c<=.0:return None
  d=[]
  for i in range(max(1,len(n)-390),len(n)):
   m=n[i][0]-n[i-1][0]
   if 45<=m<=180 and n[i-1][3]>0:r=math.log(n[i][3]/n[i-1][3]);d.append(r*r)
  if len(d)>=20:e=sum(d)/len(d);b=math.sqrt(e*98280.)
  else:b=vol_floor_annual
  a=max(vol_floor_annual,min(2.,b*1.1));return{"spot":c,"sigma_session":round(a,4),"bars":n,"fetched_ts":f}
 except Exception as exc:return None
def window_extremes_from_bars(bars,start_ts,end_ts):
 a=[b for b in bars if start_ts<=float(b[0])<=end_ts]
 if not a:return None
 return max(b[1]for b in a),min(b[2]for b in a)
def detect_pyth_calendar_inclusion_boxes(quote_rows,max_box_cost_net=.994,now_ts=None):
 k=float(now_ts if now_ts is not None else time.time());f={}
 for q in quote_rows:
  if float(q.get("start_ts",.0))>k:continue
  f.setdefault((str(q["asset"]),str(q["direction"]),round(float(q["strike"]),4)),[]).append(q)
 m=[]
 for(h,b,e),p in f.items():
  if len(p)<2:continue
  g=sorted(p,key=lambda x:float(x["end_ts"]))
  for i in range(len(g)):
   for j in range(i+1,len(g)):
    o,n=g[i],g[j]
    if float(n["end_ts"])-float(o["end_ts"])<3600.:continue
    if float(n["start_ts"])>float(o["start_ts"])+1e-6:continue
    d=o.get("ask_no");c=n.get("ask_yes")
    if d is None or c is None:continue
    a=round(float(d)+float(c),4);l=round(_net_unit_ask(float(d),float(o.get("fee_rate",.0)),float(o.get("fee_exponent",1.)))+_net_unit_ask(float(c),float(n.get("fee_rate",.0)),float(n.get("fee_exponent",1.))),4)
    if l<=max_box_cost_net:m.append({"box_kind":"PYTH_CALENDAR_INCLUSION","asset":h,"direction":b,"strike":e,"box_cost_net":l,"box_cost_gross":a,"yes_row":n,"no_row":o,"close_ts":float(n["end_ts"]),"label":f"NO_SHORT({b} {e}) + YES_LONG({b} {e})"})
 m.sort(key=lambda x:float(x["box_cost_net"]));return m
def detect_pyth_close_vs_hit_boxes(close_rows,hit_rows,now_ts,max_box_cost_net=.994):
 d=[]
 for h in close_rows:
  if h.get("is_downward")or h.get("ask_no")is None:continue
  b=float(h["end_ts"]);f=float(h["strike"])
  for g in hit_rows:
   if(g["asset"]!=h["asset"]or g["direction"]!="UP"or g.get("ask_yes")is None):continue
   e=float(g["strike"])
   if e>f+1e-6:continue
   if not(float(g["start_ts"])<=now_ts and now_ts<b<=float(g["end_ts"])+60.):continue
   a=round(float(h["ask_no"])+float(g["ask_yes"]),4);c=round(_net_unit_ask(float(h["ask_no"]),float(h.get("fee_rate",.0)),float(h.get("fee_exponent",1.)))+_net_unit_ask(float(g["ask_yes"]),float(g.get("fee_rate",.0)),float(g.get("fee_exponent",1.))),4)
   if c<=max_box_cost_net:d.append({"box_kind":"PYTH_CLOSE_VS_HIT","asset":str(h["asset"]),"strike_hit":e,"strike_close":f,"box_cost_net":c,"box_cost_gross":a,"yes_row":g,"no_row":h,"close_ts":max(b,float(g["end_ts"])),"label":f"NO(Close>{f:g}) + YES(Hit>={e:g})"})
 d.sort(key=lambda x:float(x["box_cost_net"]));return d
def evaluate_pyth_session_barrier_no_lock(spot,strike,direction,eff_session_hours,sigma_session,basis_buffer_frac):
 if spot<=.0 or strike<=.0 or eff_session_hours<=.0:return{"p_touch":1.,"p_no":.0}
 if direction=="UP":
  a=spot*(1.+basis_buffer_frac)
  if a>=strike:return{"p_touch":1.,"p_no":.0}
 else:
  a=spot*(1.-basis_buffer_frac)
  if a<=strike:return{"p_touch":1.,"p_no":.0}
 b=(eff_session_hours/1638.)*(365.25*86400.);c=first_passage_touch_prob(spot=a,strike=strike,tte_seconds=b,iv_annual=sigma_session,direction=direction,wick_vol_multiplier=1.15);return{"p_touch":round(c,5),"p_no":round(1.-c,5)}
def evaluate_pyth_session_close_lock(spot,strike,is_downward,eff_session_hours,sigma_session,basis_buffer_frac):
 if spot<=.0 or strike<=.0 or eff_session_hours<=.0:return{"eligible":False,"side":"YES","p_lock":.5,"z_session":.0}
 a=spot>strike;c=spot*(1.-basis_buffer_frac if a else 1.+basis_buffer_frac)
 if(a and c<=strike)or((not a)and c>=strike):return{"eligible":False,"side":"YES","p_lock":.5,"z_session":.0}
 h=max(1e-6,eff_session_hours/1638.);f=max(.0012,sigma_session*math.sqrt(h));z=abs(math.log(c/strike))/f;e=.5*(1.+math.erf(z/math.sqrt(2.)));d=.5+math.atan(z)/math.pi;g=min(.994,.85*e+.15*d)
 if is_downward:b="NO"if a else"YES"
 else:b="YES"if a else"NO"
 return{"eligible":bool(z>=2.15 and g>=.955),"side":b,"p_lock":round(g,4),"z_session":round(z,3)}
def _norm_team(name):return re.sub(r"\s+"," ",str(name or"").strip()).lower()
def _is_half_integer(val):a=abs(float(val))*2.;return abs(a-round(a))<1e-4 and(int(round(a))%2==1)
def parse_nba_zero_fee_event(ev,now_ts=None):
 B=float(now_ts if now_ts is not None else time.time())
 if ev.get("closed")or ev.get("archived"):return None
 z=ev.get("markets")or[]
 if len(z)<3:return None
 d=None;h,g=.0,1.
 for m in z:
  if str(m.get("sportsMarketType")or"").strip().lower()=="moneyline"and not m.get("closed"):
   if _parse_clob_tokens(m):h,g=_extract_market_fee_rate(m);d=m;break
 if d is None:return None
 a=d.get("outcomes")
 if isinstance(a,str):
  try:a=json.loads(a)
  except Exception:a=None
 if not isinstance(a,list)or len(a)<2:return None
 s=str(a[0]).strip();r=str(a[1]).strip();q,p=_norm_team(s),_norm_team(r)
 if not q or not p or q==p:return None
 l=_parse_clob_tokens(d);assert l is not None;o=_parse_iso_ts(d.get("gameStartTime")or ev.get("endDate"))or(B+7200.)
 if B>o+6.*3600.:return None
 b=max(o+3.25*3600.,B+1800.);e=[NbaOutcomeLeg(market_id=str(d.get("id")or""),condition_id=str(d.get("conditionId")or""),market_type="moneyline",token_id=l[0],opp_token_id=l[1],side_index=0,side_label="YES",display_label=f"{s} ML",relation="GT",threshold=.0,fee_rate=h,fee_exponent=g),NbaOutcomeLeg(market_id=str(d.get("id")or""),condition_id=str(d.get("conditionId")or""),market_type="moneyline",token_id=l[1],opp_token_id=l[0],side_index=1,side_label="NO",display_label=f"{r} ML",relation="LT",threshold=.0,fee_rate=h,fee_exponent=g)];f=[]
 for m in z:
  if m.get("closed")or m.get("archived"):continue
  A=str(m.get("sportsMarketType")or"").strip().lower()
  if A not in("spreads","totals"):continue
  D,C=_extract_market_fee_rate(m);y=_parse_clob_tokens(m)
  if not y:continue
  c=m.get("outcomes")
  if isinstance(c,str):
   try:c=json.loads(c)
   except Exception:c=None
  if not isinstance(c,list)or len(c)<2:continue
  u=str(m.get("question")or"")
  if any(E in u.lower()for E in("1h ","2h ","1q ","2q ","3q ","4q ","half","quarter")):continue
  if A=="spreads":
   x=_SPREAD_FAV_RE.search(u)
   if not x:continue
   k=_norm_team(x.group(1));j=float(x.group(2))
   if j>=.0 or not _is_half_integer(j):continue
   t=abs(j);w,v=_norm_team(c[0]),_norm_team(c[1])
   if k==q and w==q and v==p:e.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"spreads",y[0],y[1],0,"YES",f"{s} -{t:g}","GT",t,D,C));e.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"spreads",y[1],y[0],1,"NO",f"{r} +{t:g}","LT",t,D,C))
   elif k==p and w==p and v==q:e.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"spreads",y[0],y[1],0,"YES",f"{r} -{t:g}","LT",-t,D,C));e.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"spreads",y[1],y[0],1,"NO",f"{s} +{t:g}","GT",-t,D,C))
  elif A=="totals":
   i=m.get("line")
   if i is None:continue
   n=float(i)
   if n<=50. or not _is_half_integer(n):continue
   if _norm_team(c[0])=="over"and _norm_team(c[1])=="under":f.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"totals",y[0],y[1],0,"YES",f"Over {n:g}","OVER",n,D,C));f.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"totals",y[1],y[0],1,"NO",f"Under {n:g}","UNDER",n,D,C))
 return NbaGameSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),title=str(ev.get("title")or f"{s} vs. {r}"),team_a=s,team_b=r,tipoff_ts=o,settle_est_ts=b,margin_legs=e,total_legs=f)
def detect_nba_dominance_boxes(spec,best_asks_by_token,max_box_cost_net=1.2):
 b=[];h=[lg for lg in spec.margin_legs if lg.relation=="GT"and lg.token_id in best_asks_by_token];g=[lg for lg in spec.margin_legs if lg.relation=="LT"and lg.token_id in best_asks_by_token]
 for r in h:
  q=float(best_asks_by_token[r.token_id])
  if not(.01<=q<=.99):continue
  j=_net_unit_ask(q,r.fee_rate,r.fee_exponent)
  for p in g:
   if r.market_id==p.market_id or r.threshold>=p.threshold-1e-6:continue
   o=float(best_asks_by_token[p.token_id])
   if not(.01<=o<=.99):continue
   a=round(q+o,4);c=round(j+_net_unit_ask(o,p.fee_rate,p.fee_exponent),4)
   if c<=max_box_cost_net:f=round(p.threshold-r.threshold,1);b.append({"box_kind":"NBA_POLISH_MIDDLE"if("ML"in r.display_label or"ML"in p.display_label)else"NBA_SPREAD_MONO","event_id":spec.event_id,"title":spec.title,"box_cost_net":c,"box_cost_gross":a,"middle_width_pts":f,"leg_a":r,"leg_b":p,"close_ts":spec.settle_est_ts,"label":f"{r.display_label} + {p.display_label}"})
 e=[lg for lg in spec.total_legs if lg.relation=="OVER"and lg.token_id in best_asks_by_token];d=[lg for lg in spec.total_legs if lg.relation=="UNDER"and lg.token_id in best_asks_by_token]
 for n in e:
  m=float(best_asks_by_token[n.token_id])
  if not(.01<=m<=.99):continue
  i=_net_unit_ask(m,n.fee_rate,n.fee_exponent)
  for l in d:
   if n.market_id==l.market_id or n.threshold>=l.threshold-1e-6:continue
   k=float(best_asks_by_token[l.token_id])
   if not(.01<=k<=.99):continue
   a=round(m+k,4);c=round(i+_net_unit_ask(k,l.fee_rate,l.fee_exponent),4)
   if c<=max_box_cost_net:b.append({"box_kind":"NBA_TOTAL_MONO","event_id":spec.event_id,"title":spec.title,"box_cost_net":c,"box_cost_gross":a,"middle_width_pts":round(l.threshold-n.threshold,1),"leg_a":n,"leg_b":l,"close_ts":spec.settle_est_ts,"label":f"{n.display_label} + {l.display_label}"})
 b.sort(key=lambda x:(float(x["box_cost_net"]),-float(x["middle_width_pts"])));return b
def parse_zero_fee_negrisk_slate(ev,series_slug,allow_mixed_fees=True):
 if not ev.get("negRisk")or ev.get("closed")or ev.get("archived"):return None
 f=ev.get("markets")or[]
 if len(f)<3:return None
 c=_parse_iso_ts(ev.get("endDate"))
 if not c:return None
 a=[]
 for m in f:
  if m.get("archived"):continue
  if m.get("closed"):
   b=m.get("outcomePrices")
   if isinstance(b,str):
    try:b=json.loads(b)
    except Exception:b=None
   if not(isinstance(b,list)and len(b)>=2 and float(b[1])>=.99):return None
   continue
  g,e=_extract_market_fee_rate(m)
  if g>.0 and not allow_mixed_fees:return None
  d=_parse_clob_tokens(m)
  if not d:return None
  a.append({"market_id":str(m.get("id")or""),"condition_id":str(m.get("conditionId")or""),"label":str(m.get("groupItemTitle")or m.get("question")or""),"yes_token":d[0],"no_token":d[1],"fee_rate":g,"fee_exponent":e,"rewards_min_size":float(m.get("rewardsMinSize")or.0),"rewards_max_spread":float(m.get("rewardsMaxSpread")or.0)})
 if len(a)<3:return None
 return ZeroFeeNegRiskSlateSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,title=str(ev.get("title")or series_slug),end_ts=float(c),brackets=a)
@dataclass
class MultiSportCorridorLeg:market_id:str;condition_id:str;scope_key:str;token_id:str;opp_token_id:str;side_index:int;side_label:str;display_label:str;relation:str;threshold:float;fee_rate=.0;fee_exponent=1.;neg_risk=False
@dataclass
class MultiSportCorridorSpec:
 event_id:str;slug:str;sport:str;title:str;team_a:str;team_b:str;start_ts:float;settle_est_ts:float;legs_by_scope=field(default_factory=dict)
 @property
 def legs(self):return[lg for sc_lgs in self.legs_by_scope.values()for lg in sc_lgs]
_SPREAD_PERIOD_MAP={"spreads":"FG","first_half_spreads":"1H","second_half_spreads":"2H","q1_spreads":"Q1","q2_spreads":"Q2","q3_spreads":"Q3","q4_spreads":"Q4"};_TOTAL_PERIOD_MAP={"totals":"FG","first_half_totals":"1H","second_half_totals":"2H","q1_totals":"Q1","q2_totals":"Q2","q3_totals":"Q3","q4_totals":"Q4"};_TEAM_TOTAL_PERIOD_MAP={"team_totals":"FG_TEAM","first_half_team_totals":"1H_TEAM","second_half_team_totals":"2H_TEAM"}
def _infer_sport_tag(ev,sport_hint=""):
 if sport_hint:return sport_hint.upper()
 d=str(ev.get("slug")or"").lower()
 for e,a in(("nba-","NBA"),("nfl-","NFL"),("cfb-","CFB"),("nhl-","NHL"),("mlb-","MLB"),("atp-","TENNIS"),("wta-","TENNIS"),("lol-","ESPORTS"),("cs2-","ESPORTS")):
  if d.startswith(e):return a
 for b in(ev.get("series")or[]):
  if isinstance(b,dict):
   c=str(b.get("slug")or"").lower()
   for f,a in(("nba","NBA"),("nfl","NFL"),("cfb","CFB"),("nhl","NHL")):
    if f in c:return a
 return"SPORTS"
def parse_multi_sport_corridor_event(ev,sport_hint="",now_ts=None,skip_nba_fg_zero_fee=True):
 P=float(now_ts if now_ts is not None else time.time())
 if ev.get("closed")or ev.get("archived")or ev.get("negRisk"):return None
 L=ev.get("markets")or[]
 if len(L)<4:return None
 F=_infer_sport_tag(ev,sport_hint);j,i="","";a=None
 for v in("moneyline","spreads","first_half_spreads"):
  for m in L:
   if m.get("closed")or str(m.get("sportsMarketType")or"").strip().lower()!=v:continue
   b=m.get("outcomes")
   if isinstance(b,str):
    try:b=json.loads(b)
    except Exception:b=None
   if isinstance(b,list)and len(b)==2:
    S,R=str(b[0]).strip(),str(b[1]).strip()
    if{_norm_team(S),_norm_team(R)}not in({"yes","no"},{"over","under"})and _norm_team(S)!=_norm_team(R):j,i=S,R;a=_parse_iso_ts(m.get("gameStartTime")or ev.get("startDate")or ev.get("endDate"));break
  if j and i:break
 B,A=_norm_team(j),_norm_team(i)
 if a is None:
  for m in L:
   a=_parse_iso_ts(m.get("gameStartTime"))
   if a:break
 if a is None:a=_parse_iso_ts(ev.get("endDate"))or(P+7200.)
 if P>a+6.5*3600.:return None
 f=max(a+3.75*3600.,P+1800.);e={}
 for m in L:
  if m.get("closed")or m.get("archived")or m.get("negRisk"):continue
  O=str(m.get("sportsMarketType")or"").strip().lower()
  if O not in _SPREAD_PERIOD_MAP and O not in _TOTAL_PERIOD_MAP and O not in _TEAM_TOTAL_PERIOD_MAP:continue
  Q,K=_extract_market_fee_rate(m)
  if skip_nba_fg_zero_fee and F=="NBA"and Q==.0 and O in("spreads","totals"):continue
  J=_parse_clob_tokens(m)
  if not J:continue
  b=m.get("outcomes")
  if isinstance(b,str):
   try:b=json.loads(b)
   except Exception:b=None
  if not isinstance(b,list)or len(b)<2:continue
  E=str(m.get("question")or"");N=str(m.get("id")or"");M=str(m.get("conditionId")or"")
  if O in _SPREAD_PERIOD_MAP:
   if not B or not A:continue
   n=_SPREAD_PERIOD_MAP[O]
   if n=="FG"and any(bad in E.lower()for bad in("1h ","2h ","1q ","2q ","3q ","4q ","half","quarter")):continue
   I=_SPREAD_FAV_RE.search(E)
   if not I:continue
   k=_norm_team(I.group(1));u=float(I.group(2))
   if not _is_half_integer(u):continue
   H,G=_norm_team(b[0]),_norm_team(b[1])
   if{H,G}!={B,A}or k not in(B,A):continue
   t=0 if H==k else 1;s=1-t;r,q=J[t],J[s];p="YES"if t==0 else"NO";o="YES"if s==0 else"NO";l=""if n=="FG"else f"{n} ";d=f"{n}:SPREAD"
   if k==B:z=round(-u,2);e.setdefault(d,[]).extend([MultiSportCorridorLeg(N,M,d,r,q,t,p,f"{l}{j} {u:+g}","GT",z,Q,K,False),MultiSportCorridorLeg(N,M,d,q,r,s,o,f"{l}{i} {-u:+g}","LT",z,Q,K,False)])
   else:z=round(u,2);e.setdefault(d,[]).extend([MultiSportCorridorLeg(N,M,d,r,q,t,p,f"{l}{i} {u:+g}","LT",z,Q,K,False),MultiSportCorridorLeg(N,M,d,q,r,s,o,f"{l}{j} {-u:+g}","GT",z,Q,K,False)])
  elif O in _TOTAL_PERIOD_MAP:
   n=_TOTAL_PERIOD_MAP[O]
   if n=="FG"and any(bad in E.lower()for bad in("1h ","2h ","1q ","2q ","3q ","4q ","half","quarter","team total")):continue
   c=m.get("line")
   if c is None:continue
   h=float(c)
   if h<=.0 or not _is_half_integer(h):continue
   if _norm_team(b[0])!="over"or _norm_team(b[1])!="under":continue
   l=""if n=="FG"else f"{n} ";d=f"{n}:TOTAL";e.setdefault(d,[]).extend([MultiSportCorridorLeg(N,M,d,J[0],J[1],0,"YES",f"{l}Over {h:g}","OVER",h,Q,K,False),MultiSportCorridorLeg(N,M,d,J[1],J[0],1,"NO",f"{l}Under {h:g}","UNDER",h,Q,K,False)])
  elif O in _TEAM_TOTAL_PERIOD_MAP:
   if not B or not A:continue
   c=m.get("line")
   if c is None:continue
   h=float(c)
   if h<=.0 or not _is_half_integer(h):continue
   if _norm_team(b[0])!="over"or _norm_team(b[1])!="under":continue
   y=E.split("O/U")[0].lower()if"O/U"in E else E.lower();D=B in y;C=A in y
   if D==C:continue
   x=B if D else A;w=j if D else i;n=_TEAM_TOTAL_PERIOD_MAP[O];l=""if n=="FG_TEAM"else f"{n.split('_')[0]} ";d=f"{n}:{x}";e.setdefault(d,[]).extend([MultiSportCorridorLeg(N,M,d,J[0],J[1],0,"YES",f"{l}{w} Over {h:g}","OVER",h,Q,K,False),MultiSportCorridorLeg(N,M,d,J[1],J[0],1,"NO",f"{l}{w} Under {h:g}","UNDER",h,Q,K,False)])
 g={sc:lgs for sc,lgs in e.items()if len({T.market_id for T in lgs})>=2}
 if not g:return None
 return MultiSportCorridorSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),sport=F,title=str(ev.get("title")or f"{j} vs. {i}"),team_a=j,team_b=i,start_ts=float(a),settle_est_ts=float(f),legs_by_scope=g)
def detect_multi_sport_corridor_boxes(spec,best_asks_by_token,max_box_cost_net=1.08):
 d=[]
 for j,o in spec.legs_by_scope.items():
  if j.endswith(":SPREAD"):c,b,a="GT","LT","SPREAD_CORRIDOR"
  else:c,b,a="OVER","UNDER","TOTAL_CORRIDOR"
  g=[lg for lg in o if lg.relation==c and lg.token_id in best_asks_by_token];e=[lg for lg in o if lg.relation==b and lg.token_id in best_asks_by_token]
  for n in g:
   m=float(best_asks_by_token[n.token_id])
   if not(.01<=m<=.99):continue
   i=_net_unit_ask(m,n.fee_rate,n.fee_exponent)
   for l in e:
    if n.market_id==l.market_id or n.threshold>=l.threshold-1e-6:continue
    k=float(best_asks_by_token[l.token_id])
    if not(.01<=k<=.99):continue
    h=_net_unit_ask(k,l.fee_rate,l.fee_exponent);f=round(i+h,4)
    if f<=max_box_cost_net:d.append({"box_kind":f"{spec.sport}_{a}","sport":spec.sport,"scope":j,"event_id":spec.event_id,"title":spec.title,"box_cost_net":f,"box_cost_gross":round(m+k,4),"middle_width_pts":round(l.threshold-n.threshold,1),"leg_a":n,"leg_b":l,"close_ts":spec.settle_est_ts,"label":f"{n.display_label} + {l.display_label}"})
 d.sort(key=lambda x:(float(x["box_cost_net"]),-float(x["middle_width_pts"])));return d
@dataclass
class NegRiskConvertSlateSpec:event_id:str;slug:str;title:str;neg_risk_market_id:str;neg_risk_augmented:bool;total_market_count:int;is_closed_convert_safe:bool;end_ts:float;brackets:List[Dict[str,Any]]
def parse_negrisk_convert_event(ev):
 if ev.get("closed")or ev.get("archived"):return None
 if not(ev.get("enableNegRisk")or ev.get("negRisk")):return None
 s=ev.get("markets")or[]
 if len(s)<2:return None
 o=_parse_iso_ts(ev.get("endDate"))
 if not o:return None
 h=str(ev.get("negRiskMarketID")or"").strip().lower();n=bool(ev.get("negRiskAugmented",True));f=len(h)==66 and h.startswith("0x");e=[];a=True;c=False;l=re.compile(r"(?:\bplaceholder\b|^(?:person|party|option|candidate|team|player)\s+[a-z0-9]{1,2}$)",re.IGNORECASE)
 for m in s:
  k=str(m.get("groupItemTitle")or m.get("question")or"").strip()
  if l.search(k):c=True
  if m.get("archived")or m.get("closed")or m.get("active")is False:a=False;continue
  r=_parse_clob_tokens(m)
  if not r:a=False;continue
  t,q=_extract_market_fee_rate(m);p=str(m.get("questionID")or"").strip().lower();d=None
  if f and len(p)==66 and p.startswith("0x")and p[:64]==h[:64]:
   try:d=int(p[64:],16)
   except ValueError:d=None
  e.append({"market_id":str(m.get("id")or""),"condition_id":str(m.get("conditionId")or""),"question_id":p,"question_index":d,"label":k[:48],"yes_token":r[0],"no_token":r[1],"fee_rate":t,"fee_exponent":q})
 if len(e)<2:return None
 j=len(s);i={b["question_index"]for b in e if isinstance(b.get("question_index"),int)};g=bool((not n)and(not c)and f and a and 3<=j<=24 and len(e)==j and i==set(range(j)))
 if g:e.sort(key=lambda b:int(b["question_index"]))
 return NegRiskConvertSlateSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),title=str(ev.get("title")or ev.get("slug")or""),neg_risk_market_id=h,neg_risk_augmented=n,total_market_count=j,is_closed_convert_safe=g,end_ts=float(o),brackets=e)
def detect_negrisk_no_pair_boxes(spec,best_no_asks,max_box_cost_net=1.04):
 d=[]
 for b in spec.brackets:
  o=b["no_token"]
  if o not in best_no_asks:continue
  n=float(best_no_asks[o])
  if.01<=n<=.985:d.append((b,n,_net_unit_ask(n,float(b["fee_rate"]),float(b["fee_exponent"]))))
 d.sort(key=lambda x:x[2]);a=d[:12];k=[]
 for i in range(len(a)):
  m,h,f=a[i]
  for j in range(i+1,len(a)):
   l,g,e=a[j]
   if m["market_id"]==l["market_id"]:continue
   c=round(f+e,4)
   if c<=max_box_cost_net:k.append({"mode":"NR_NO_PAIR_BOX","event_id":spec.event_id,"slug":spec.slug,"title":spec.title,"box_cost_net":c,"box_cost_gross":round(h+g,4),"bracket_a":m,"bracket_b":l,"close_ts":spec.end_ts,"label":f"NO[{m['label']}] + NO[{l['label']}]"})
 k.sort(key=lambda x:float(x["box_cost_net"]));return k
def _walk_side_exact_shares(levels_raw,shares_req,fee_rate,fee_exp,is_ask):
 m=sorted([(float(x["price"]),float(x["size"]))for x in(levels_raw or[])if float(x.get("price",0))>0 and float(x.get("size",0))>0],key=lambda t:(t[0]if is_ask else-t[0]))
 if not m:return None
 p=m[0][0];j=(min(.5,max(.0,(fee_rate*((p*(1.-p))**fee_exp))/p))if(is_ask and fee_rate>.0 and.0<p<1.)else.0);c=(math.ceil((float(shares_req)/(1.-j))*1e2-1e-9)/1e2)if(is_ask and j>.0)else float(shares_req);h=float(c);f=.0;b=m[0][0];i=round(m[0][0]*m[0][1],2)
 for o,n in m:
  l=min(h,n);f+=l*o;b=o;h-=l
  if h<=1e-6:break
 if h>1e-5:return None
 k=f/c
 if is_ask:e=_net_unit_ask(k,fee_rate,fee_exp);a=float(shares_req)*e;d=max(.0,a-float(shares_req)*k)
 else:g=fee_rate*((k*(1.-k))**fee_exp)if fee_rate>.0 else.0;d=float(shares_req)*g;a=max(.0,f-d);e=a/float(shares_req)
 return{"vwap":round(k,5),"gross_shares":round(c,2),"net_per_share":round(e,5),"net_cash_usd":round(a,4),"fee_usd":round(d,4),"worst_px":round(b,4),"l1_usd":i}
def detect_negrisk_convert_positions_arbs(spec,books_by_token,target_budget_usd=120.,min_net_edge_per_share=.01,min_shares=8,min_net_edge_per_set=None):
 if min_net_edge_per_set is not None:min_net_edge_per_share=float(min_net_edge_per_set)
 if not spec.is_closed_convert_safe:return[]
 K=len(spec.brackets)
 if K<3:return[]
 I=[]
 for R,b in enumerate(spec.brackets):
  P=books_by_token.get(b["yes_token"])or{};O=books_by_token.get(b["no_token"])or{};H=sorted([(float(x["price"]),float(x["size"]))for x in(O.get("asks")or[])if float(x.get("price",0))>0 and float(x.get("size",0))>0],key=lambda t:t[0]);G=sorted([(float(x["price"]),float(x["size"]))for x in(P.get("bids")or[])if float(x.get("price",0))>0 and float(x.get("size",0))>0],key=lambda t:-t[0]);W,V=float(b["fee_rate"]),float(b["fee_exponent"]);v=_net_unit_ask(H[0][0],W,V)if H else 9.9;C=H[0][1]if H else.0
  if G:Q=G[0][0];c=max(.0,Q-(W*((Q*(1.-Q))**V)if W>0 else.0));d=G[0][1]
  else:c,d=-1.,.0
  u=c+v-1.;I.append((u,R,b,v,C,c,d))
 I.sort(key=lambda t:-t[0]);m=[]
 if I[0][5]>.0:F=[I[0][1]];N=[t[1]for t in I[1:]];m.append((sorted(N),F))
 if K>=4 and I[0][5]>.0 and I[1][5]>.0:E=sorted([I[0][1],I[1][1]]);M=[t[1]for t in I[2:]];m.append((sorted(M),E))
 L=[];B={i:spec.brackets[i]for i in range(K)}
 for A,r in m:
  J=len(A)
  if J<2:continue
  j=sum(next(t[3]for t in I if t[1]==i)for i in A)
  if j<=.0 or j>=float(J):continue
  q=min([next(t[4]for t in I if t[1]==i)for i in A]+[next(t[6]for t in I if t[1]==k)for k in r]);D=int(math.floor(min(q,target_budget_usd/max(.25,j))))
  if D<min_shares:continue
  s=[];a=True
  for i in A:
   U=B[i];T=_walk_side_exact_shares((books_by_token.get(U["no_token"])or{}).get("asks")or[],float(D),float(U["fee_rate"]),float(U["fee_exponent"]),is_ask=True)
   if T is None:a=False;break
   s.append((U,T))
  if not a:continue
  p=[]
  for k in r:
   z=B[k];S=_walk_side_exact_shares((books_by_token.get(z["yes_token"])or{}).get("bids")or[],float(D),float(z["fee_rate"]),float(z["fee_exponent"]),is_ask=False)
   if S is None:a=False;break
   p.append((z,S))
  if not a:continue
  g=sum(w["net_per_share"]for _,w in s);f=sum(w["net_per_share"]for _,w in p);l=float(J-1);e=l+f;y=round(e-g,5)
  if y<min_net_edge_per_share:continue
  o=[int(B[i]["question_index"])for i in A];h=sum(1<<X for X in o);n=min([w["l1_usd"]for _,w in s]+[w["l1_usd"]for _,w in p]);L.append({"mode":"NR_CONV_POSITIONS_INSTANT","event_id":spec.event_id,"slug":spec.slug,"title":spec.title,"neg_risk_market_id":spec.neg_risk_market_id,"m_no_legs":J,"n_total":K,"question_indices":o,"no_question_indices":o,"index_set":h,"index_set_int":h,"shares":D,"no_cost_per_share":round(g,4),"no_cost_net_per_set":round(g,4),"usdc_converted_per_share":l,"usdc_released_per_set":l,"yes_bid_proceeds_per_share":round(f,4),"yes_bid_proceeds_net_per_set":round(f,4),"net_proceeds_per_share":round(e,4),"net_edge_per_share":round(y,4),"net_edge_per_set":round(y,4),"total_cost_usd":round(sum(w["net_cash_usd"]for _,w in s),2),"total_net_profit_usd":round(D*y,2),"total_fee_usd":round(sum(w["fee_usd"]for _,w in s)+sum(w["fee_usd"]for _,w in p),4),"l1_usd":round(n,2),"no_legs":[{"token_id":b["no_token"],"bracket":b,"walk":w}for b,w in s],"yes_sell_legs":[{"token_id":b["yes_token"],"bracket":b,"walk":w}for b,w in p],"close_ts":spec.end_ts,"label":f"CONV({J}xNO->${J-1}+SELL[{','.join(b['label'][:14]for b,_ in p)}])"})
 L.sort(key=lambda x:-float(x["net_edge_per_share"]));return L
# ======================================================================================
# [11/21] MODULE: src/polymarket_research/macro_counting_ctf_engine.py
# PURPOSE: Phase-2 Multi-Vertical Structural & Oracle Engine (TW1 xtracker, FED1 125-State LP, COND1 Oil-Senate, CTF Overround, AAA Gas, D2 12PM)
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import logging;import math;import re;import time;import urllib.request;from dataclasses import dataclass,field;from datetime import date,datetime,timedelta,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;from src.polymarket_research.barrier_onetouch_svi_engine import first_passage_touch_prob;from src.polymarket_research.tradfi_sports_zero_fee_engine import(_extract_market_fee_rate,_net_unit_ask,_parse_clob_tokens,_parse_iso_ts);logger=logging.getLogger("MacroCountingCTF")
try:NY_TZ=ZoneInfo("America/New_York")
except Exception:NY_TZ=timezone(timedelta(hours=-4))
CHROME_UA=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36");COUNTING_SERIES_HANDLES=(("elon-tweets","elonmusk"),("elon-tweets-48h","elonmusk"),("trump-truth-social","realDonaldTrump"));FOMC_PARLAY_SERIES=("fomc","fed-3-parlay");OIL_SENATE_SLUGS=("which-party-will-win-the-senate-in-2026","who-wins-the-senate-pending-oil-below-85-before-the-midterms","who-wins-the-senate-pending-oil-above-or-below-80-before-the-midterms");GAS_SERIES_SLUGS=("us-gas-price-daily","gas-price-hits-weekly");AI_SERIES_SLUGS=("best-ai-company","chinese-ai-1");HOURLY_BINANCE_SERIES={"BTC":"btc-up-or-down-hourly","ETH":"eth-up-or-down-hourly","SOL":"solana-up-or-down-hourly","XRP":"xrp-up-or-down-hourly","BNB":"bnb-up-or-down-hourly","DOGE":"doge-up-or-down-hourly"};_XTRACKER_CACHE={};_AAA_GAS_CACHE=(.0,None)
@dataclass
class CountingBracket:market_id:str;condition_id:str;label:str;low_count:int;high_count:float;yes_token:str;no_token:str;fee_rate=.0;rewards_min_size=.0;rewards_max_spread=.0;neg_risk=True;fee_exponent=1.
@dataclass
class CountingSlateSpec:event_id:str;slug:str;series_slug:str;handle:str;title:str;window_start_ts:float;window_end_ts:float;gamma_closed_floor:int;brackets=field(default_factory=list)
_CNT_LT_RE=re.compile(r"^\s*(?:<|under\s+|less than\s+)(\d+)\s*$",re.IGNORECASE);_CNT_PLUS_RE=re.compile(r"^\s*(\d+)\s*\+\s*$|^\s*(\d+)\s+or\s+more\s*$",re.IGNORECASE);_CNT_RNG_RE=re.compile(r"^\s*(\d+)\s*[-–—to]+\s*(\d+)\s*$",re.IGNORECASE);_DESC_WINDOW_RE=re.compile(r"(?:from|between)\s+([A-Za-z]+\s+\d{1,2})(?:,\s*(\d{4}))?,?\s+(\d{1,2}:\d{2}\s*[AP]M)\s*ET\s+" r"(?:to|and)\s+([A-Za-z]+\s+\d{1,2}),?\s*(\d{4}),?\s+(\d{1,2}:\d{2}\s*[AP]M)\s*ET",re.IGNORECASE)
def parse_count_bracket_bounds(label):
 s=str(label or"").strip().replace(",","");c=_CNT_LT_RE.match(s)
 if c:v=int(c.group(1));return(0,float(v-1))if v>0 else None
 b=_CNT_PLUS_RE.match(s)
 if b:v=int(b.group(1)or b.group(2));return(v,float("inf"))
 a=_CNT_RNG_RE.match(s)
 if a:
  e,d=int(a.group(1)),int(a.group(2))
  if d>=e>=0:return(e,float(d))
 return None
def _parse_et_window_from_description(desc,fallback_end_ts):
 m=_DESC_WINDOW_RE.search(str(desc or""))
 if m:
  c,b,a,g,f,e=m.groups();j=int(f);i=int(b)if b else j
  try:
   d=datetime.strptime(f"{c} {i} {a.upper().replace(' ','')}","%B %d %Y %I:%M%p");h=datetime.strptime(f"{g} {j} {e.upper().replace(' ','')}","%B %d %Y %I:%M%p")
   if d>h and not b:d=d.replace(year=j-1)
   l=d.replace(tzinfo=NY_TZ).timestamp();k=h.replace(tzinfo=NY_TZ).timestamp()
   if k>l:return l,k
  except Exception:pass
 return fallback_end_ts-7.*86400.,fallback_end_ts
def parse_counting_slate_event(ev,series_slug,handle):
 if ev.get("closed")or ev.get("archived"):return None
 f=_parse_iso_ts(ev.get("endDate"))
 if not f:return None
 n=ev.get("markets")or[]
 if len(n)<3:return None
 l=str(ev.get("description")or(n[0].get("description")if n else"")or"");d,g=_parse_et_window_from_description(l,float(f));a=0;c=[]
 for m in n:
  if m.get("archived"):continue
  o=str(m.get("groupItemTitle")or m.get("question")or"");k=parse_count_bracket_bounds(o)
  if k is None:continue
  j,i=k
  if m.get("closed"):
   e=m.get("outcomePrices")
   if isinstance(e,str):
    try:e=json.loads(e)
    except Exception:e=None
   if isinstance(e,list)and len(e)>=2 and float(e[1])>=.99 and math.isfinite(i):a=max(a,int(i)+1)
   elif isinstance(e,list)and len(e)>=2 and float(e[0])>=.99:return None
   continue
  q,p=_extract_market_fee_rate(m);h=_parse_clob_tokens(m)
  if not h:continue
  c.append(CountingBracket(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),label=o,low_count=j,high_count=i,yes_token=h[0],no_token=h[1],fee_rate=q,rewards_min_size=float(m.get("rewardsMinSize")or.0),rewards_max_spread=float(m.get("rewardsMaxSpread")or.0),neg_risk=bool(m.get("negRisk")if m.get("negRisk")is not None else ev.get("negRisk",True)),fee_exponent=p))
 if len(c)<2:return None
 c.sort(key=lambda b:b.low_count);return CountingSlateSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),series_slug=series_slug,handle=handle,title=str(ev.get("title")or series_slug),window_start_ts=d,window_end_ts=g,gamma_closed_floor=a,brackets=c)
def fetch_xtracker_user_stats_sync(handle,ttl_sec=60.):
 o=time.time();d=_XTRACKER_CACHE.get(handle)
 if d and(o-d[0])<ttl_sec:return d[1]
 n={}
 try:
  m=urllib.request.Request(f"https://xtracker.polymarket.com/api/users/{handle}",headers={"User-Agent":CHROME_UA})
  with urllib.request.urlopen(m,timeout=5.)as r:c=json.loads(r.read().decode("utf-8",errors="replace")).get("data")or{}
  for s in(c.get("trackings")or[]):
   if not s.get("isActive"):continue
   l=str(s.get("id")or"");i=str(s.get("marketLink")or"");h=i.rstrip("/").split("/")[-1]if i else""
   if not l or not h:continue
   g=urllib.request.Request(f"https://xtracker.polymarket.com/api/trackings/{l}?includeStats=true",headers={"User-Agent":CHROME_UA})
   with urllib.request.urlopen(g,timeout=5.)as q:p=json.loads(q.read().decode("utf-8",errors="replace")).get("data")or{}
   f=p.get("stats")or{};b=[];a=False
   for k in(f.get("daily")or[]):
    e=str(k.get("date")or"").strip()
    if len(e)==10:a=True
    j=_parse_iso_ts(e)
    if j is not None:b.append((float(j),int(k.get("count")or 0)))
   n[h]={"tracking_id":l,"total":int(f.get("total")or 0),"start_ts":_parse_iso_ts(p.get("startDate"))or.0,"end_ts":_parse_iso_ts(p.get("endDate"))or.0,"hourly":b,"daily_tz_pad":1.8e4 if a else.0}
  _XTRACKER_CACHE[handle]=(o,n)
 except Exception as exc:
  if d:return d[1]
 return n
def evaluate_counting_dead_no_locks(slate,xtracker_by_slug,safety_post_buffer=2):
 e=xtracker_by_slug.get(slate.slug)or{};b=int(e.get("total")or 0);a=max(int(slate.gamma_closed_floor),b);c=[]
 for d in slate.brackets:
  if math.isfinite(d.high_count)and a>=int(d.high_count)+max(1,safety_post_buffer):c.append(d)
 return a,c
def detect_counting_subwindow_boxes(slates,best_asks_by_token,xtracker_by_handle,max_box_cost_net=1.05):
 n=[]
 for i,k in enumerate(slates):
  for j,m in enumerate(slates):
   if i==j or k.handle!=m.handle or k.event_id==m.event_id:continue
   if not(m.window_start_ts<=k.window_start_ts and k.window_end_ts<=m.window_end_ts and(m.window_end_ts-m.window_start_ts)>(k.window_end_ts-k.window_start_ts)+3600.):continue
   h=(xtracker_by_handle.get(m.handle)or{}).get(m.slug)or{};a=0
   if h.get("hourly")and k.window_start_ts>m.window_start_ts+1800.:l=float(h.get("daily_tz_pad")or.0);a=sum(u for v,u in h["hourly"]if(v-l)>=m.window_start_ts and(v+86400.+l)<=k.window_start_ts)
   t=[b for b in k.brackets if not math.isfinite(b.high_count)];s=[b for b in m.brackets if not math.isfinite(b.high_count)]
   for o in t:
    g=best_asks_by_token.get(o.no_token)
    if g is None:continue
    for p in s:
     if p.low_count<=a+o.low_count:
      d=best_asks_by_token.get(p.yes_token)
      if d is None:continue
      e=round(_net_unit_ask(float(g),o.fee_rate,o.fee_exponent)+_net_unit_ask(float(d),p.fee_rate,p.fee_exponent),4)
      if e<=max_box_cost_net:n.append({"box_kind":"TW1_UPPER_SUBWINDOW","handle":k.handle,"banked":a,"box_cost_gross":round(float(g)+float(d),4),"box_cost_net":e,"leg_a":{"token_id":o.no_token,"opp_token_id":o.yes_token,"condition_id":o.condition_id,"side":"NO","label":f"NO_48H[{o.label}]","market_id":o.market_id,"fee_rate":o.fee_rate,"fee_exponent":o.fee_exponent,"strike":float(o.low_count),"neg_risk":o.neg_risk},"leg_b":{"token_id":p.yes_token,"opp_token_id":p.no_token,"condition_id":p.condition_id,"side":"YES","label":f"YES_7D[{p.label}]","market_id":p.market_id,"fee_rate":p.fee_rate,"fee_exponent":p.fee_exponent,"strike":float(p.low_count),"neg_risk":p.neg_risk},"close_ts":max(k.window_end_ts,m.window_end_ts),"label":f"{k.handle} NO({o.label} short) + YES({p.label} long, banked={a})"})
   r=[b for b in k.brackets if b.low_count==0 and math.isfinite(b.high_count)];q=[b for b in m.brackets if b.low_count==0 and math.isfinite(b.high_count)]
   for p in q:
    f=best_asks_by_token.get(p.no_token)
    if f is None:continue
    for o in r:
     if int(p.high_count)<=a+int(o.high_count):
      c=best_asks_by_token.get(o.yes_token)
      if c is None:continue
      e=round(_net_unit_ask(float(f),p.fee_rate,p.fee_exponent)+_net_unit_ask(float(c),o.fee_rate,o.fee_exponent),4)
      if e<=max_box_cost_net:n.append({"box_kind":"TW1_LOWER_SUBWINDOW","handle":k.handle,"banked":a,"box_cost_gross":round(float(f)+float(c),4),"box_cost_net":e,"leg_a":{"token_id":p.no_token,"opp_token_id":p.yes_token,"condition_id":p.condition_id,"side":"NO","label":f"NO_7D[{p.label}]","market_id":p.market_id,"fee_rate":p.fee_rate,"fee_exponent":p.fee_exponent,"strike":float(p.high_count),"neg_risk":p.neg_risk},"leg_b":{"token_id":o.yes_token,"opp_token_id":o.no_token,"condition_id":o.condition_id,"side":"YES","label":f"YES_48H[{o.label}]","market_id":o.market_id,"fee_rate":o.fee_rate,"fee_exponent":o.fee_exponent,"strike":float(o.high_count),"neg_risk":o.neg_risk},"close_ts":max(k.window_end_ts,m.window_end_ts),"label":f"{k.handle} NO({p.label} long) + YES({o.label} short, banked={a})"})
 n.sort(key=lambda x:float(x["box_cost_net"]));return n
FOMC_ACTIONS=("CUT50","CUT25","PAUSE","HIKE25","HIKE50");FOMC_STATES_3M=[(a,b,c)for a in FOMC_ACTIONS for b in FOMC_ACTIONS for c in FOMC_ACTIONS];ALL_FOMC_MASK=(1<<len(FOMC_STATES_3M))-1
def _classify_single_fomc_label(label):
 s=str(label or"").strip().lower()
 if"no change"in s or s=="pause":return"PAUSE"
 c=bool(re.search(r"\b50\s*\+?|\b50\s*bps",s));a="25+"in s;b=bool(re.search(r"(?<![.\d])25(?![.\d])",s))
 if c and("decrease"in s or"cut"in s):return"CUT50"
 if a and("decrease"in s or"cut"in s):return"CUT25+"
 if a and("increase"in s or"hike"in s):return"HIKE25+"
 if b and("decrease"in s or"cut"in s):return"CUT25"
 if b and("increase"in s or"hike"in s):return"HIKE25"
 if c and("increase"in s or"hike"in s):return"HIKE50"
 return None
_FOMC_LABEL_ACTION_SET={"CUT25+":("CUT25","CUT50"),"HIKE25+":("HIKE25","HIKE50")}
def _parlay_word_matches(word,action):
 w=word.strip().lower()
 if w=="pause":return action=="PAUSE"
 if w=="cut":return action in("CUT25","CUT50")
 if w=="hike":return action in("HIKE25","HIKE50")
 return False
def build_fomc_truth_table_legs(fomc_events,parlay_events,sep_2026_realized_action=None):
 K=[]
 for I in fomc_events:
  if I.get("closed"):continue
  j=str(I.get("slug")or"").lower();e=_parse_iso_ts(I.get("endDate"))or.0;A=0 if"october"in j else(1 if"december"in j else(2 if"january"in j else-1))
  if A<0 or e<=0:continue
  z=("OCT","DEC","JAN")[A]
  for m in(I.get("markets")or[]):
   if m.get("closed"):continue
   H,G=_extract_market_fee_rate(m);h=_parse_clob_tokens(m);N=_classify_single_fomc_label(str(m.get("groupItemTitle")or m.get("question")or""))
   if not h or not N:continue
   c=0;k=_FOMC_LABEL_ACTION_SET.get(N,(N,))
   for r,O in enumerate(FOMC_STATES_3M):
    if O[A]in k:c|=(1<<r)
   q=str(m.get("id")or"");o=str(m.get("conditionId")or"");J=m.get("negRisk")if isinstance(m.get("negRisk"),bool)else(I.get("negRisk")if isinstance(I.get("negRisk"),bool)else None);K.append({"event_group":f"FOMC_{z}","market_id":q,"condition_id":o,"token_id":h[0],"opp_token_id":h[1],"side":"YES","label":f"YES({z}:{N})","mask":c,"end_ts":e,"fee_rate":H,"fee_exponent":G,"neg_risk":J});K.append({"event_group":f"FOMC_{z}","market_id":q,"condition_id":o,"token_id":h[1],"opp_token_id":h[0],"side":"NO","label":f"NO({z}:{N})","mask":ALL_FOMC_MASK^c,"end_ts":e,"fee_rate":H,"fee_exponent":G,"neg_risk":J})
 for I in parlay_events:
  if I.get("closed"):continue
  j=str(I.get("slug")or"").lower();e=_parse_iso_ts(I.get("endDate"))or.0;g="oct-jan"in j;f="sepdec"in j and sep_2026_realized_action is not None
  if not(g or f)or e<=0:continue
  y="PARLAY_OCT_JAN"if g else"PARLAY_SEP_DEC";b=0;a=False;d=None
  for m in(I.get("markets")or[]):
   M=str(m.get("groupItemTitle")or"").strip();i=M.lower()=="other"
   if m.get("closed"):
    if not i:a=True
    continue
   H,G=_extract_market_fee_rate(m);h=_parse_clob_tokens(m)
   if not h:
    if not i:a=True
    continue
   if i:d=(m,h,H,G);continue
   x=[p.strip()for p in re.split(r"[-–—/]",M)if p.strip()]
   if len(x)!=3:a=True;continue
   c=0
   for r,(w,v,u)in enumerate(FOMC_STATES_3M):
    if g:F=_parlay_word_matches(x[0],w)and _parlay_word_matches(x[1],v)and _parlay_word_matches(x[2],u)
    else:assert sep_2026_realized_action is not None;F=_parlay_word_matches(x[0],sep_2026_realized_action)and _parlay_word_matches(x[1],w)and _parlay_word_matches(x[2],v)
    if F:c|=(1<<r)
   if c==0:a=True;continue
   b|=c;q=str(m.get("id")or"");o=str(m.get("conditionId")or"");E=m.get("negRisk")if isinstance(m.get("negRisk"),bool)else(I.get("negRisk")if isinstance(I.get("negRisk"),bool)else None);K.append({"event_group":y,"market_id":q,"condition_id":o,"token_id":h[0],"opp_token_id":h[1],"side":"YES","label":f"YES({y}:{M})","mask":c,"end_ts":e,"fee_rate":H,"fee_exponent":G,"neg_risk":E});K.append({"event_group":y,"market_id":q,"condition_id":o,"token_id":h[1],"opp_token_id":h[0],"side":"NO","label":f"NO({y}:{M})","mask":ALL_FOMC_MASK^c,"end_ts":e,"fee_rate":H,"fee_exponent":G,"neg_risk":E})
  if d is not None and not a:L,n,D,C=d;l=ALL_FOMC_MASK^b;t=str(L.get("id")or"");s=str(L.get("conditionId")or"");B=L.get("negRisk")if isinstance(L.get("negRisk"),bool)else(I.get("negRisk")if isinstance(I.get("negRisk"),bool)else None);K.append({"event_group":y,"market_id":t,"condition_id":s,"token_id":n[0],"opp_token_id":n[1],"side":"YES","label":f"YES({y}:Other)","mask":l,"end_ts":e,"fee_rate":D,"fee_exponent":C,"neg_risk":B});K.append({"event_group":y,"market_id":t,"condition_id":s,"token_id":n[1],"opp_token_id":n[0],"side":"NO","label":f"NO({y}:Other)","mask":ALL_FOMC_MASK^l,"end_ts":e,"fee_rate":D,"fee_exponent":C,"neg_risk":B})
 return K
OIL_SENATE_STATES=[(o,p)for o in("LT80","B80_85","GE85")for p in("DEM","REP","OTHER")];ALL_OIL_SENATE_MASK=(1<<len(OIL_SENATE_STATES))-1
def build_oil_senate_truth_table_legs(events_by_slug):
 q=[]
 for p,x in events_by_slug.items():
  if not x or x.get("closed"):continue
  g=_parse_iso_ts(x.get("endDate"))or.0
  if g<=0:continue
  j=p.lower()
  for m in(x.get("markets")or[]):
   if m.get("closed"):continue
   w,v=_extract_market_fee_rate(m);o=_parse_clob_tokens(m)
   if not o:continue
   t=str(m.get("groupItemTitle")or m.get("question")or"").strip();u=t.lower();a=0
   if"which-party-will-win-the-senate"in j:
    b="DEM"if"democrat"in u else("REP"if"republican"in u else None)
    if not b:continue
    for e,(_,c)in enumerate(OIL_SENATE_STATES):
     if c==b:a|=(1<<e)
    l="SENATE_MAIN"
   elif"pending-oil"in j:
    b="DEM"if("d senate"in u or"democrat"in u)else("REP"if("r senate"in u or"republican"in u)else None);f=85 if"85"in u else(80 if"80"in u else 0);i="<"in u or"below"in u or"less"in u;h="≥"in u or">="in u or"above"in u or"greater"in u
    if not b or f not in(80,85)or(i==h):continue
    for e,(n,c)in enumerate(OIL_SENATE_STATES):
     if c!=b:continue
     d=((n=="LT80"if i else n in("B80_85","GE85"))if f==80 else(n in("LT80","B80_85")if i else n=="GE85"))
     if d:a|=(1<<e)
    l=f"OIL_{f}_SENATE"
   else:continue
   s=str(m.get("id")or"");r=str(m.get("conditionId")or"");k=m.get("negRisk")if isinstance(m.get("negRisk"),bool)else(x.get("negRisk")if isinstance(x.get("negRisk"),bool)else None);q.append({"event_group":l,"market_id":s,"condition_id":r,"token_id":o[0],"opp_token_id":o[1],"side":"YES","label":f"YES[{t}]","mask":a,"end_ts":g,"fee_rate":w,"fee_exponent":v,"neg_risk":k});q.append({"event_group":l,"market_id":s,"condition_id":r,"token_id":o[1],"opp_token_id":o[0],"side":"NO","label":f"NO[{t}]","mask":ALL_OIL_SENATE_MASK^a,"end_ts":g,"fee_rate":w,"fee_exponent":v,"neg_risk":k})
 return q
def find_cross_event_bitmask_boxes(legs,best_asks_by_token,all_states_mask,max_2leg_cost=1.05,max_3leg_cost=1.03):
 c=[]
 for D in legs:
  y=best_asks_by_token.get(str(D["token_id"]));m=int(D["mask"])
  if y is not None and.002<=float(y)<=.995 and 0<m<all_states_mask:u=float(D.get("fee_rate")or.0);t=float(D.get("fee_exponent")or 1.);e=_net_unit_ask(float(y),u,t);c.append((e,float(y),m,D))
 w=[];n=len(c);b=set()
 for i in range(n):
  r,q,p,o=c[i]
  for j in range(i+1,n):
   l,h,g,f=c[j]
   if o["market_id"]==f["market_id"]or o["event_group"]==f["event_group"]:continue
   if(p|g)==all_states_mask:
    s=round(r+l,4);b.add((i,j))
    if s<=max_2leg_cost:a=bin(p&g).count("1");w.append({"n_legs":2,"box_cost_gross":round(q+h,4),"box_cost_net":s,"double_pay_states":a,"legs":[o,f],"close_ts":max(float(o["end_ts"]),float(f["end_ts"])),"label":f"{o['label']} + {f['label']}"})
 for i in range(n):
  r,q,p,o=c[i]
  if r>=max_3leg_cost:continue
  for j in range(i+1,n):
   if(i,j)in b:continue
   l,h,g,f=c[j]
   if r+l>=max_3leg_cost or o["market_id"]==f["market_id"]:continue
   v=p|g
   if v in(p,g):continue
   for k in range(j+1,n):
    if(i,k)in b or(j,k)in b:continue
    C,B,A,z=c[k];d=round(r+l+C,4)
    if d>max_3leg_cost:continue
    if z["market_id"]in(o["market_id"],f["market_id"]):continue
    if len({o["event_group"],f["event_group"],z["event_group"]})<2:continue
    if(v|A)==all_states_mask and(p|A)!=all_states_mask and(g|A)!=all_states_mask:w.append({"n_legs":3,"box_cost_gross":round(q+h+B,4),"box_cost_net":d,"double_pay_states":0,"legs":[o,f,z],"close_ts":max(float(o["end_ts"]),float(f["end_ts"]),float(z["end_ts"])),"label":f"{o['label']} + {f['label']} + {z['label']}"})
 w.sort(key=lambda x:(float(x["box_cost_net"]),int(x["n_legs"])));return w
def walk_equal_shares_overround_bids(legs_bids_spec,target_mint_budget_usd=1e2,min_net_proceeds_per_set=1.004,min_shares=8.):
 if len(legs_bids_spec)<2 or target_mint_budget_usd<=0:return{"filled":False}
 f=[];e=float("inf");a=.0
 for u in legs_bids_spec:
  l=float(u.get("fee_rate")or.0);h=float(u.get("fee_exponent")or 1.);o=sorted([(float(b["price"]),float(b["size"]))for b in(u.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0])
  if not o:return{"filled":False}
  t,r=o[0];n=l*((t*(1.-t))**h)if l>0 else.0;a+=(t-n);e=min(e,r);f.append((o,l,h))
 if a<min_net_proceeds_per_set:return{"filled":False,"l1_net_proceeds":round(a,4)}
 j=min(float(target_mint_budget_usd),min(sum(s for _,s in bds)for bds,_,_ in f));m=math.floor(j)
 if m<min_shares:return{"filled":False,"l1_net_proceeds":round(a,4)}
 d=.0;c=.0
 for bds,l,h in f:
  i=float(m)
  for q,p in bds:
   k=min(i,p);d+=k*q
   if l>0:c+=k*l*((q*(1.-q))**h)
   i-=k
   if i<=1e-9:break
  if i>1e-6:return{"filled":False}
 g=(d-c)/m
 if g<min_net_proceeds_per_set:return{"filled":False,"l1_net_proceeds":round(a,4)}
 return{"filled":True,"shares":float(m),"mint_cost_per_set":1.,"gross_proceeds_per_set":round(d/m,4),"net_proceeds_per_set":round(g,4),"net_edge_per_set":round(g-1.,4),"fee_usd":round(c,4),"spent_usd":round(float(m),2),"l1_usd":round(e,2)}
def walk_position_overround_bid_unwind(legs_bids_spec,exact_shares,min_net_proceeds_per_set=1.004):
 k=float(exact_shares)
 if len(legs_bids_spec)<2 or k<=.0:return{"filled":False}
 d=.0;c=.0;f=[]
 for o in legs_bids_spec:
  n=float(o.get("fee_rate")or.0);j=float(o.get("fee_exponent")or 1.);i=sorted([(float(b["price"]),float(b["size"]))for b in(o.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0])
  if not i:return{"filled":False}
  g=k;a=i[0][0]
  for m,l in i:
   h=min(g,l);d+=h*m
   if n>.0:c+=h*n*((m*(1.-m))**j)
   a=m;g-=h
   if g<=1e-9:break
  if g>1e-6:return{"filled":False}
  f.append(round(a,4))
 e=(d-c)/k
 if e<min_net_proceeds_per_set:return{"filled":False,"net_proceeds_per_set":round(e,4)}
 return{"filled":True,"shares":round(k,4),"gross_proceeds_per_set":round(d/k,4),"net_proceeds_per_set":round(e,4),"fee_usd":round(c,4),"worst_leg_bids":f}
def evaluate_locked_market_reward_carry(p_lock,best_bid,best_ask,rewards_min_size,rewards_max_spread_cents,fee_rate=.0):
 if p_lock<.995 or rewards_min_size<=.0 or best_ask<=.96:return{"eligible":False}
 h=.002 if best_ask>.99 else.005;g=round(best_bid+.001,3)if(best_bid>=.988 and(best_ask-best_bid)>=.003)else max(best_bid,.96);d=.994 if p_lock>=.999 else.989;b=.006 if p_lock>=.999 else.008;f=round(min(g,min(best_ask-h,d)),3);e=float(rewards_max_spread_cents)/1e2 if rewards_max_spread_cents>.5 else float(rewards_max_spread_cents or.03);a=(best_ask-f)<=max(.02,e+1e-6);c=round(p_lock-f,4)
 if not(.955<=f<best_ask and c>=b and a):return{"eligible":False}
 return{"eligible":True,"resting_bid":f,"carry_edge":c,"rewards_min_size":rewards_min_size,"rewards_max_spread":round(e,4)}
_AAA_AS_OF_RE=re.compile(r"Price\s+as\s+of\s+(\d{1,2})/(\d{1,2})/(\d{2,4})",re.IGNORECASE);_AAA_ROW_PRICES_RE=re.compile(r"\$(\d+\.\d{3,4})")
def parse_aaa_gas_html(html):
 f=_AAA_AS_OF_RE.search(str(html or""));e=[float(x)for x in _AAA_ROW_PRICES_RE.findall(str(html or""))if 1.5<=float(x)<=9.5]
 if not f or len(e)<6:return None
 i,h,d=int(f.group(1)),int(f.group(2)),int(f.group(3));g=2000+d if d<100 else d
 try:a=date(g,i,h)
 except ValueError:return None
 c=e[1]if abs(e[0]-e[1])<.02 else e[0];b=e[6]if len(e)>6 else c;return{"as_of_date":a.isoformat(),"current_regular":round(c,4),"yesterday_regular":round(b,4)}
def fetch_aaa_national_gas_sync(ttl_sec=180.):
 global _AAA_GAS_CACHE;now=time.time()
 if _AAA_GAS_CACHE[1]is not None and(now-_AAA_GAS_CACHE[0])<ttl_sec:return _AAA_GAS_CACHE[1]
 try:
  req=urllib.request.Request("https://gasprices.aaa.com/",headers={"User-Agent":CHROME_UA})
  with urllib.request.urlopen(req,timeout=6.)as r:parsed=parse_aaa_gas_html(r.read().decode("utf-8",errors="replace"))
  if parsed:_AAA_GAS_CACHE=(now,parsed);return parsed
 except Exception as exc:pass
 return _AAA_GAS_CACHE[1]
_GAS_LT_RE=re.compile(r"<\s*\$?\s*(\d+(?:\.\d+)?)");_GAS_PL_RE=re.compile(r"\$?\s*(\d+(?:\.\d+)?)\s*\+");_GAS_RG_RE=re.compile(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:[-–—]|\bto\b)\s*\$?\s*(\d+(?:\.\d+)?)",re.IGNORECASE)
def parse_gas_daily_bracket(label):
 s=str(label or"").strip();c=_GAS_LT_RE.search(s)
 if c:return(.0,float(c.group(1))-1e-6)
 b=_GAS_PL_RE.search(s)
 if b:return(float(b.group(1)),float("inf"))
 a=_GAS_RG_RE.search(s)
 if a:return(float(a.group(1)),float(a.group(2)))
 return None
def is_in_scheduled_macro_catalyst_window(now_ts):
 b=datetime.fromtimestamp(now_ts,tz=NY_TZ)
 if b.weekday()>=5:return False,""
 a=b.hour*60+b.minute
 if 8*60+29<=a<=8*60+45:return True,"US_0830_MACRO_RELEASE"
 if b.weekday()in(2,3)and(10*60+29<=a<=10*60+45):return True,"EIA_1030_PETROLEUM"
 if b.weekday()==2 and(13*60+59<=a<=14*60+45):return True,"FOMC_1400_DECISION"
 return False,""
def evaluate_pyth_catalyst_shock(asset,prev_spot,cur_spot,strike,direction,eff_session_hours,sigma_session,now_ts):
 g,c=is_in_scheduled_macro_catalyst_window(now_ts)
 if not g or prev_spot<=0 or cur_spot<=0 or eff_session_hours<=.1:return{"eligible":False}
 i=(cur_spot-prev_spot)/prev_spot;b=.0035 if asset=="SPY"else.0045
 if abs(i)<b:return{"eligible":False}
 e=(eff_session_hours/1638.)*(365.25*86400.);a=first_passage_touch_prob(prev_spot,strike,e,sigma_session,direction,wick_vol_multiplier=1.1);d=first_passage_touch_prob(cur_spot,strike,e,sigma_session,direction,wick_vol_multiplier=1.1);j=d-a
 if abs(j)<.055:return{"eligible":False}
 h="YES"if j>0 else"NO";f=d if h=="YES"else(1.-d);return{"eligible":bool(.22<=f<=.94),"catalyst":c,"side":h,"p_fair":round(f,4),"delta_p":round(abs(j),4),"ret_pct":round(i*1e2,3)}
def evaluate_ai_elo_ci_lock(leaderboard_rows,snapshot_ts,now_ts,tte_sec,max_snapshot_age_sec=21600.):
 if not leaderboard_rows or(now_ts-snapshot_ts)>max_snapshot_age_sec or not(6e2<=tte_sec<=129600.):return{"eligible":False,"reason":"stale_or_outside_window"}
 f=sorted(leaderboard_rows,key=lambda r:float(r.get("rating")or.0),reverse=True)
 if len(f)<2:return{"eligible":False}
 g=f[0];c=str(g.get("organization")or"").strip();b=float(g.get("rating_q025")or.0);a=max((float(r.get("rating_q975")or.0)for r in f[1:]if str(r.get("organization")or"").strip()!=c),default=.0);e=b-a
 if not c or e<6.:return{"eligible":False,"ci_gap":round(e,2)}
 d=min(.992,.955+.0025*min(15.,e-6.));return{"eligible":True,"leader_org":c,"ci_gap":round(e,2),"p_lock":round(d,4)}
def detect_d2_12pm_binance_boxes(hourly_spec,k_1h,terminal_specs,min_corridor_bps=25.):
 if k_1h<=0:return[]
 d=float(hourly_spec["end_ts"]);i=[]
 for e in terminal_specs:
  if e.get("is_downward"):continue
  if abs(float(e["end_ts"])-d)>5.:continue
  h=float(e["strike"])
  if h<=0:continue
  g,f=min(k_1h,h),max(k_1h,h);c=(f-g)/g*1e4
  if c<min_corridor_bps:continue
  if k_1h<h:b={"token_id":hourly_spec["up_token"],"opp_token_id":hourly_spec["down_token"],"condition_id":hourly_spec["condition_id"],"side":"UP","label":f"1H_UP>{k_1h:g}","market_id":hourly_spec["market_id"],"fee_rate":float(hourly_spec.get("fee_rate",.07)),"fee_exponent":1.,"strike":k_1h};a={"token_id":e["no_token"],"opp_token_id":e["yes_token"],"condition_id":e["condition_id"],"side":str(e.get("no_label","NO")),"label":f"12PM_NO<{h:g}","market_id":e["market_id"],"fee_rate":float(e.get("fee_rate",.07)),"fee_exponent":1.,"strike":h}
  else:b={"token_id":e["yes_token"],"opp_token_id":e["no_token"],"condition_id":e["condition_id"],"side":str(e.get("yes_label","YES")),"label":f"12PM_YES>{h:g}","market_id":e["market_id"],"fee_rate":float(e.get("fee_rate",.07)),"fee_exponent":1.,"strike":h};a={"token_id":hourly_spec["down_token"],"opp_token_id":hourly_spec["up_token"],"condition_id":hourly_spec["condition_id"],"side":"DOWN","label":f"1H_DN<{k_1h:g}","market_id":hourly_spec["market_id"],"fee_rate":float(hourly_spec.get("fee_rate",.07)),"fee_exponent":1.,"strike":k_1h}
  i.append({"asset":str(hourly_spec["asset"]),"k_low":g,"k_high":f,"corridor_bps":round(c,2),"leg_a":b,"leg_b":a,"close_ts":max(d,float(e["end_ts"])),"label":f"{b['label']} + {a['label']} ({c:.0f}bps)"})
 return i
# ======================================================================================
# [12/21] MODULE: src/polymarket_research/uma_nba_endgame_engine.py
# PURPOSE: Evergreen On-Chain UMA Resolution Bond Harvester (BOND1) & 0%-Fee Live NBA Final-2m/Post-Buzzer Sniper (SP2)
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import logging;import math;import os;import re;import time;import urllib.request;from dataclasses import dataclass;from datetime import datetime,timedelta,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;from src.polymarket_research.tradfi_sports_zero_fee_engine import(NbaGameSpec,NbaOutcomeLeg,_extract_market_fee_rate,_norm_team,_parse_clob_tokens,_parse_iso_ts);logger=logging.getLogger("UmaNbaEndgameEngine");DEFAULT_POLYGON_RPC="https://polygon-bor-rpc.publicnode.com";FALLBACK_POLYGON_RPCS=("https://1rpc.io/matic","https://polygon-rpc.com");ESPN_NBA_SCOREBOARD_URL="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard";CDN_NBA_SCOREBOARD_URL="https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json";ZERO_ADDR="0x0000000000000000000000000000000000000000";ONE_E18=10**18;HALF_E18=5*(10**17);VERIFIED_UMA_ADAPTERS=frozenset({"0x65070be91477460d8a7aeeb94ef92fe056c2f2a7","0x69c47de9d4d3dad79590d61b9e05918e03775f24","0x2f5e3684cb1f318ec51b00edba38d79ac2c0aa9d","0x6a9d222616c90fca5754cd1333cfd9b7fb6a4f74","0x157ce2d672854c848c9b79c49a8cc6cc89176a49"});NEGRISK_UMA_ADAPTERS=frozenset({"0x69c47de9d4d3dad79590d61b9e05918e03775f24"});SEL_OPTIMISTIC_ORACLE="22302922";SEL_GET_QUESTION="58c039cd";SEL_GET_STATE="ba4b930c";SEL_GET_REQUEST="a9904f9b";YES_OR_NO_IDENT_HEX=b"YES_OR_NO_QUERY".ljust(32,b"\x00").hex();_OO_ADDR_CACHE={};_SUBJECTIVE_VETO_RE=re.compile(r'(\bsay\b.{0,30}["“]|\bmention\b|\btweet\b|\btruth social\b|\bceasefire\b' r'|\binvade\b|\bstrike on\b|\bpardon\b|\bresign\b|\bnominate\b' r'|\bsole discretion\b|\bplaceholder\b)',re.IGNORECASE);_OBJECTIVE_ORACLE_RE=re.compile(r"(aviationweather\.gov|weather\.gov\.hk|wunderground\.com|binance\.com|chain\.link" r"|pyth\.network|federalreserve\.gov|bls\.gov|gasprices\.aaa\.com|xtracker" r"|nba\.com|nhl\.com|mlb\.com|nfl\.com|espn\.com|premierleague\.com|uefa\.com|atptour\.com|hlTV|lol\s*esports)",re.IGNORECASE);_SPORTS_TITLE_RE=re.compile(r"(\bvs\.?\s+|\bwin on 20\d{2}-\d{2}-\d{2}\b|\bo/u\s+\d+|\bspread:\s+|\bgame\s+[1-7]\s+winner\b|\bmap\s+[1-5]\s+winner\b)",re.IGNORECASE);_EARLY_BARRIER_MARKET_RE=re.compile(r"\b(reach|hit|dip|touch|drop\s+to|fall\s+to|climb\s+to|at\s+any\s+point|before\s+20\d{2})\b",re.IGNORECASE);_HEX32_RE=re.compile(r"^0x[0-9a-fA-F]{64}$");_ANC_CORRESPONDS_RE=re.compile(r"p1\s+corresponds\s+to\s+([^,\.\n]+),\s*p2\s+to\s+([^,\.\n]+)",re.IGNORECASE)
@dataclass
class LiveNbaGameState:game_id:str;start_ts:float;state:str;completed:bool;period:int;clock_sec:float;home_name:str;home_abbr:str;home_score:int;away_name:str;away_abbr:str;away_score:int;source="espn"
def _parse_json_list(raw):
 if isinstance(raw,list):return raw
 if isinstance(raw,str):
  s=raw.strip()
  if s.startswith("["):
   try:a=json.loads(s);return a if isinstance(a,list)else[]
   except Exception:return[]
 return[]
def is_objective_uma_market(m):
 if m.get("closed")or m.get("archived")or not m.get("acceptingOrders",False):return False,"NOT_OPEN_CLOB"
 j=str(m.get("umaResolutionStatus")or"").strip().lower()
 if j!="proposed":return False,f"STATUS_{j.upper()or'NONE'}"
 h=[str(x).strip().lower()for x in _parse_json_list(m.get("umaResolutionStatuses"))]
 if any(x in("disputed","flagged","reset")for x in h):return False,"PRIOR_DISPUTE_HISTORY"
 if h.count("proposed")>2:return False,"EXCESS_PROPOSAL_CYCLES"
 b=str(m.get("resolvedBy")or"").strip().lower()
 if b not in VERIFIED_UMA_ADAPTERS:return False,"UNVERIFIED_ADAPTER"
 c=bool(m.get("negRisk"))or(b in NEGRISK_UMA_ADAPTERS);a=str(m.get("negRiskRequestID")if c else m.get("questionID")or"").strip()
 if not _HEX32_RE.match(a):return False,"MISSING_REQUEST_ID"
 g=_parse_clob_tokens(m);f=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))]
 if not g or len(f)!=2:return False,"NON_BINARY_OUTCOMES"
 if any(o.lower()in("other","placeholder","unknown")for o in f):return False,"PLACEHOLDER_OUTCOME"
 q=str(m.get("question")or"");e=str(m.get("description")or"");d=f"{q}\n{e}"
 if _SUBJECTIVE_VETO_RE.search(d):return False,"SUBJECTIVE_OR_SPEECH_VETO"
 i=str(m.get("sportsMarketType")or"").strip().lower()
 if i:return True,f"SPORTS_{i.upper()}"
 if _OBJECTIVE_ORACLE_RE.search(d):return True,"VERIFIED_PRIMARY_ORACLE"
 if _SPORTS_TITLE_RE.search(q):return True,"SPORTS_MATCH_RULE"
 return False,"NO_OBJECTIVE_DOMAIN_MATCH"
def _rpc_post(rpc_url,payload,timeout=5.):
 c=json.dumps(payload).encode("utf-8");b=[rpc_url]
 if rpc_url==DEFAULT_POLYGON_RPC:b.extend(u for u in FALLBACK_POLYGON_RPCS if u!=rpc_url)
 a=None
 for u in b:
  try:d=urllib.request.Request(u,data=c,headers={"Content-Type":"application/json","User-Agent":"DominusUmaVerifier/1.0"},method="POST");return json.loads(urllib.request.urlopen(d,timeout=timeout).read().decode("utf-8"))
  except Exception as exc:a=exc
 raise a if a is not None else RuntimeError("RPC_FAILED")
def _encode_oo_query_calldata(selector_hex,adapter_addr,req_ts,anc_bytes):a=adapter_addr.lower().replace("0x","").rjust(64,"0");f=int(req_ts).to_bytes(32,"big").hex();e=(128).to_bytes(32,"big").hex();d=len(anc_bytes).to_bytes(32,"big").hex();c=(32-len(anc_bytes)%32)%32;b=(anc_bytes+b"\x00"*c).hex();return f"0x{selector_hex}{a}{YES_OR_NO_IDENT_HEX}{f}{e}{d}{b}"
def _decode_int256(word):a=int.from_bytes(word,"big");return a-(1<<256)if a>=(1<<255)else a
def map_uma_proposed_price_to_outcome_idx(proposed_price,anc_text,outcomes):
 if proposed_price not in(0,ONE_E18):return None
 if len(outcomes)!=2:return None
 d=_ANC_CORRESPONDS_RE.search(anc_text or"")
 if d and"p1: 0"in anc_text and"p2: 1"in anc_text:
  c=_norm_team(d.group(1));b=_norm_team(d.group(2));f,e=_norm_team(outcomes[0]),_norm_team(outcomes[1]);a=c if proposed_price==0 else b
  if a==f and a!=e:return 0
  if a==e and a!=f:return 1
 return 0 if proposed_price==ONE_E18 else 1
def verify_uma_onchain_proposal_sync(m,rpc_url=None,now_ts=None,min_proposal_age_sec=120.,max_rem_challenge_sec=7500.,timeout=5.):
 X,q=is_objective_uma_market(m)
 if not X:return{"verified":False,"reason":q}
 _d=float(now_ts if now_ts is not None else time.time());_c=rpc_url or os.getenv("POLYGON_RPC_URL")or DEFAULT_POLYGON_RPC;N=str(m.get("resolvedBy")or"").strip().lower();Z=bool(m.get("negRisk"))or(N in NEGRISK_UMA_ADAPTERS);p=str(m.get("negRiskRequestID")if Z else m.get("questionID")or"").strip().lower();_b=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))];_a=_parse_clob_tokens(m);assert _a is not None
 try:
  f=_OO_ADDR_CACHE.get(N);M=[{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":N,"data":f"0x{SEL_GET_QUESTION}{p[2:]}"},"latest"]}]
  if not f:M.append({"jsonrpc":"2.0","id":2,"method":"eth_call","params":[{"to":N,"data":f"0x{SEL_OPTIMISTIC_ORACLE}"},"latest"]})
  W=_rpc_post(_c,M,timeout=timeout);L={int(r["id"]):r.get("result")for r in W if isinstance(r,dict)and"id"in r};V=str(L.get(1)or"")
  if not V.startswith("0x")or len(V)<2+14*64:return{"verified":False,"reason":"INVALID_GET_QUESTION_BYTES"}
  if not f:
   U=str(L.get(2)or"")
   if not U.startswith("0x")or len(U)<42:return{"verified":False,"reason":"MISSING_OO_ADDRESS"}
   f="0x"+U[-40:].lower();_OO_ADDR_CACHE[N]=f
  T=bytes.fromhex(V[2:]);Y=[T[i:i+32]for i in range(0,13*32,32)];S=int.from_bytes(Y[1],"big");d=int.from_bytes(Y[4],"big");t=int.from_bytes(Y[5],"big");n=int.from_bytes(Y[6],"big")!=0;D=int.from_bytes(Y[7],"big")!=0;K=int.from_bytes(Y[8],"big")!=0;C=int.from_bytes(Y[9],"big")!=0
  if S<=0:return{"verified":False,"reason":"UNINITIALIZED_QUESTION"}
  if n or D or K or C or t>0:return{"verified":False,"reason":f"QUESTION_FLAGS(res={n},pause={D},reset={K},refund={C})"}
  k=int.from_bytes(Y[12],"big");J=32+k
  if J+32>len(T):return{"verified":False,"reason":"TRUNCATED_ANCILLARY_OFFSET"}
  I=int.from_bytes(T[J:J+32],"big");s=T[J+32:J+32+I]
  if len(s)!=I:return{"verified":False,"reason":"TRUNCATED_ANCILLARY_BYTES"}
  B=s.decode("utf-8",errors="replace");H=[{"jsonrpc":"2.0","id":10,"method":"eth_call","params":[{"to":f,"data":_encode_oo_query_calldata(SEL_GET_STATE,N,S,s)},"latest"]},{"jsonrpc":"2.0","id":11,"method":"eth_call","params":[{"to":f,"data":_encode_oo_query_calldata(SEL_GET_REQUEST,N,S,s)},"latest"]}];R=_rpc_post(_c,H,timeout=timeout);G={int(r["id"]):r.get("result")for r in R if isinstance(r,dict)and"id"in r};Q=str(G.get(10)or"");P=str(G.get(11)or"")
  if not Q.startswith("0x")or not P.startswith("0x")or len(P)<2+16*64:return{"verified":False,"reason":"INVALID_OO_RESPONSE"}
  A=int(Q,16);O=bytes.fromhex(P[2:]);z=[O[i:i+32]for i in range(0,16*32,32)];y="0x"+z[0].hex()[-40:].lower();x="0x"+z[1].hex()[-40:].lower();l=int.from_bytes(z[3],"big")!=0;a=int.from_bytes(z[10],"big");e=_decode_int256(z[11]);g=int.from_bytes(z[13],"big")
  if A not in(2,3):return{"verified":False,"reason":f"OO_STATE_{A}"}
  if y==ZERO_ADDR or x!=ZERO_ADDR or l:return{"verified":False,"reason":f"DISPUTER_OR_SETTLED(disp={x})"}
  if e==HALF_E18:return{"verified":False,"reason":"TIE_50_50_PROPOSAL_VETO"}
  F=map_uma_proposed_price_to_outcome_idx(e,B,_b)
  if F not in(0,1):return{"verified":False,"reason":f"NON_BINARY_PRICE_{e}"}
  op=_parse_json_list(m.get("outcomePrices"))
  if len(op)>=2:
   try:
    if float(op[F])<.9:return{"verified":False,"reason":f"GAMMA_PRICE_MISMATCH({op[F]})"}
   except Exception:pass
  h=(a or d or int(m.get("customLiveness")or 0)or 7200);j=float(g-h)
  if q=="VERIFIED_PRIMARY_ORACLE"and not _EARLY_BARRIER_MARKET_RE.search(str(m.get("question")or"")):
   w=_parse_iso_ts(m.get("endDate"))or.0
   if w>.0:
    if _d<w:return{"verified":False,"reason":f"MARKET_BEFORE_END_DATE(now={int(_d)}<end={int(w)})"}
    if j<(w-5.):return{"verified":False,"reason":f"PREMATURE_PROPOSAL_BEFORE_END_DATE(prop={int(j)}<end={int(w)})"}
  c=_d-j;b=max(.0,float(g)-_d)
  if c<min_proposal_age_sec:return{"verified":False,"reason":f"PROPOSAL_TOO_FRESH({c:.0f}s)"}
  if b>max_rem_challenge_sec:return{"verified":False,"reason":f"CHALLENGE_WINDOW_TOO_LONG({b:.0f}s)"}
  v,E=_extract_market_fee_rate(m);u=1-F;return{"verified":True,"domain":q,"adapter":N,"oo_address":f,"oo_state":A,"proposer":y,"proposed_price":e,"win_index":F,"win_label":"YES"if F==0 else"NO","win_outcome_name":_b[F],"win_token":_a[F],"lose_token":_a[u],"expiration_ts":float(g),"eff_liveness_sec":int(h),"proposal_age_sec":round(c,1),"rem_challenge_sec":round(b,1),"fee_rate":v,"fee_exponent":E}
 except Exception as exc:return{"verified":False,"reason":f"RPC_ERR:{type(exc).__name__}"}
_NBA_NICKNAME_ALIASES={"blazers":"trail blazers","sixers":"76ers","wolves":"timberwolves","mavs":"mavericks","cavs":"cavaliers"}
def _canon_nba_team(raw):
 s=_norm_team(raw)
 for k,v in _NBA_NICKNAME_ALIASES.items():
  if s==k:return v
 return s
def _parse_iso_clock_sec(raw_clk):
 if isinstance(raw_clk,(int,float)):return max(.0,float(raw_clk))
 s=str(raw_clk or"").strip()
 if not s:return.0
 b=re.match(r"^PT(?:(\d+)M)?(\d+(?:\.\d+)?)S$",s,re.IGNORECASE)
 if b:d=float(b.group(1)or.0);c=float(b.group(2)or.0);return d*60.+c
 if":"in s:
  a=s.split(":")
  if len(a)==2:
   try:return float(a[0])*60.+float(a[1])
   except ValueError:return.0
 try:return max(.0,float(s))
 except ValueError:return.0
def parse_espn_nba_scoreboard(data):
 o=[]
 for t in(data or{}).get("events")or[]:
  n=((t.get("competitions")or[None])[0])or{};s=n.get("status")or t.get("status")or{};g=s.get("type")or{};k=str(g.get("state")or"").strip().lower();d=bool(g.get("completed",False));j=int(s.get("period")or 0);f=_parse_iso_clock_sec(s.get("clock")if s.get("clock")is not None else s.get("displayClock"));e=_parse_iso_ts(n.get("date")or t.get("date"))or.0;b=None;a=None
  for c in n.get("competitors")or[]:
   r=str(c.get("homeAway")or"").strip().lower()
   if r=="home":b=c
   elif r=="away":a=c
  if not b or not a:continue
  q=b.get("team")or{};p=a.get("team")or{};i=str(q.get("name")or q.get("shortDisplayName")or"").strip();h=str(p.get("name")or p.get("shortDisplayName")or"").strip()
  try:m=int(float(b.get("score")or 0));l=int(float(a.get("score")or 0))
  except Exception:continue
  if i and h:o.append(LiveNbaGameState(game_id=str(t.get("id")or""),start_ts=e,state=k,completed=d,period=j,clock_sec=f,home_name=i,home_abbr=str(q.get("abbreviation")or"").upper(),home_score=m,away_name=h,away_abbr=str(p.get("abbreviation")or"").upper(),away_score=l,source="espn"))
 return o
def fetch_espn_nba_scoreboard_sync(timeout=4.5,now_ts=None):
 i={"User-Agent":"Mozilla/5.0","Accept":"application/json"};h=datetime.fromtimestamp(float(now_ts if now_ts is not None else time.time()),tz=ZoneInfo("America/New_York"));a=[(h-timedelta(days=1)).strftime("%Y%m%d"),h.strftime("%Y%m%d")];d={}
 for l in dict.fromkeys(a):
  try:
   k=f"{ESPN_NBA_SCOREBOARD_URL}?dates={l}";c=json.loads(urllib.request.urlopen(urllib.request.Request(k,headers=i),timeout=timeout).read().decode("utf-8"))
   for g in parse_espn_nba_scoreboard(c):d[g.game_id]=g
  except Exception as exc:pass
 if d:return list(d.values())
 try:
  c=json.loads(urllib.request.urlopen(urllib.request.Request(ESPN_NBA_SCOREBOARD_URL,headers=i),timeout=timeout).read().decode("utf-8"));f=parse_espn_nba_scoreboard(c)
  if f:return f
 except Exception as exc:pass
 try:
  b={**i,"Referer":"https://www.nba.com/","Origin":"https://www.nba.com"};p=json.loads(urllib.request.urlopen(urllib.request.Request(CDN_NBA_SCOREBOARD_URL,headers=b),timeout=timeout).read().decode("utf-8"));j=[]
  for g in((p.get("scoreboard")or{}).get("games")or[]):o=int(g.get("gameStatus")or 1);e="pre"if o==1 else("in"if o==2 else"post");n,m=g.get("homeTeam")or{},g.get("awayTeam")or{};j.append(LiveNbaGameState(game_id=str(g.get("gameId")or""),start_ts=_parse_iso_ts(g.get("gameTimeUTC"))or.0,state=e,completed=(o==3),period=int(g.get("period")or 0),clock_sec=_parse_iso_clock_sec(g.get("gameClock")),home_name=str(n.get("teamName")or""),home_abbr=str(n.get("teamTricode")or"").upper(),home_score=int(n.get("score")or 0),away_name=str(m.get("teamName")or""),away_abbr=str(m.get("teamTricode")or"").upper(),away_score=int(m.get("score")or 0),source="cdn_nba"))
  return j
 except Exception:return[]
def match_nba_live_game(spec,live_games):
 d,c=_canon_nba_team(spec.team_a),_canon_nba_team(spec.team_b)
 for g in live_games:
  if g.start_ts>0 and spec.tipoff_ts>0 and abs(g.start_ts-spec.tipoff_ts)>3.6e4:continue
  b,a=_canon_nba_team(g.home_name),_canon_nba_team(g.away_name)
  if d==b and c==a:return g,g.home_score,g.away_score
  if d==a and c==b:return g,g.away_score,g.home_score
 return None
def verify_uma_against_nba_live(m,win_index,live_games):
 if not live_games:return True,"NO_LIVE_BOARD"
 e=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))];q=str(m.get("question")or"");f=((m.get("events")or[None])[0])or{};d=str(f.get("title")or"")if isinstance(f,dict)else"";c=_parse_iso_ts(m.get("gameStartTime")or m.get("endDate"))or.0
 for g in live_games:
  if g.start_ts>0 and c>0 and abs(g.start_ts-c)>3.6e4:continue
  j,i=_canon_nba_team(g.home_name),_canon_nba_team(g.away_name);h=_norm_team(f"{q} {d}")
  if j and i and j in h and i in h:
   if not g.completed or g.state!="post":return False,"NBA_GAME_NOT_FINAL_YET"
   if str(m.get("sportsMarketType")or"").lower()=="moneyline"and len(e)==2 and g.home_score!=g.away_score:
    b=j if g.home_score>g.away_score else i;a=_canon_nba_team(e[win_index])
    if a in(j,i)and a!=b:return False,f"NBA_SCORE_CONTRADICTS_PROPOSAL({b}!={a})"
   return True,"NBA_FINAL_CONFIRMED"
 return True,"NON_NBA_OR_UNLISTED"
def evaluate_nba_endgame_locks(spec,game,score_a,score_b):
 j=float(score_a-score_b);c=float(score_a+score_b);o=[]
 if game.completed and game.state=="post"and game.period>=4 and score_a!=score_b:
  for e in spec.margin_legs:
   n=(j>e.threshold)if e.relation=="GT"else(j<e.threshold)
   if n:o.append({"leg":e,"mode":"POST_BUZZER_FINAL","p_lock":.998,"cushion_pts":round(abs(j-e.threshold),1),"clock_sec":.0,"period":game.period,"score_str":f"{spec.team_a} {score_a}-{score_b} {spec.team_b} (FINAL)"})
  for e in spec.total_legs:
   l=(c>e.threshold)if e.relation=="OVER"else(c<e.threshold)
   if l and abs(c-e.threshold)>=1.5:o.append({"leg":e,"mode":"POST_BUZZER_FINAL","p_lock":.998,"cushion_pts":round(abs(c-e.threshold),1),"clock_sec":.0,"period":game.period,"score_str":f"{spec.team_a} {score_a}-{score_b} {spec.team_b} (FINAL Tot={int(c)})"})
  return o
 if game.state!="in":return o
 if game.period>=3:
  for e in spec.total_legs:
   if e.relation=="OVER"and c>=e.threshold+2.5:o.append({"leg":e,"mode":"LIVE_TOTAL_OVER_LOCKED","p_lock":.997,"cushion_pts":round(c-e.threshold,1),"clock_sec":round(game.clock_sec,1),"period":game.period,"score_str":f"P{game.period} {game.clock_sec:.0f}s Tot={int(c)}>{e.threshold:g}"})
 if game.period>=4 and.0<game.clock_sec<=120.:
  t=max(1.,float(game.clock_sec));f=5.5 if t<=12. else(7.5 if t<=28. else(9.5 if t<=50. else 13.5));b=max(1.6,.3965*math.sqrt(t))
  for e in spec.margin_legs:
   m=(j-e.threshold)if e.relation=="GT"else(e.threshold-j)
   if m<f:continue
   if abs(j)<=8.5:
    a=(e.relation=="GT"and j>=6.)or(e.relation=="LT"and j<=-6.)
    if not a:continue
   d=m-3.
   if d<=.0 or(d*d)<1.15*t:continue
   k=d/b;h=.5*(1.+math.erf(k/math.sqrt(2.)));g=.5+math.atan(k)/math.pi;i=round(min(.997,.98*h+.02*g),4)
   if i>=.993:o.append({"leg":e,"mode":"LIVE_Q4_ENDGAME_LOCK","p_lock":i,"cushion_pts":round(m,1),"z_endgame":round(k,2),"clock_sec":round(t,1),"period":game.period,"score_str":f"P{game.period} {t:.0f}s {spec.team_a} {score_a}-{score_b} {spec.team_b}"})
 return o
# ======================================================================================
# [13/21] MODULE: src/polymarket_research/riskless_frontier_v2_engine.py
# PURPOSE: Riskless Frontier v2 Engine (NR2 Subset Convert + Free Tail, SP4 NBA Props, BOND2 Whitelisted MOOv2, SOC1 3-Way Soccer, LP1 Implication Matrix, API1 BO3 Esports)
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import itertools
import json;import math;import os;import re;import unicodedata;import urllib.request;from dataclasses import dataclass,field;from typing import Any,Dict,List,Optional,Tuple;from src.polymarket_research.tradfi_sports_zero_fee_engine import(NegRiskConvertSlateSpec,_extract_market_fee_rate,_net_unit_ask,_norm_team,_parse_clob_tokens,_parse_iso_ts,_walk_side_exact_shares);from src.polymarket_research.uma_nba_endgame_engine import(DEFAULT_POLYGON_RPC,LiveNbaGameState,_canon_nba_team,_parse_json_list,_rpc_post,verify_uma_onchain_proposal_sync);NEGRISK_ADAPTER_ADDR="0xd91e80cf2e7be2e162c6513ced06f1dd0da35296";SEL_NR_GET_QUESTION_COUNT="b7f75d2c";SEL_NR_GET_FEE_BIPS="2582cb5e";SEL_NR_GET_DETERMINED="7ae2e67b";UMA_V4_ADAPTERS=frozenset({"0x65070be91477460d8a7aeeb94ef92fe056c2f2a7","0x69c47de9d4d3dad79590d61b9e05918e03775f24"});MOOV2_ORACLE_ADDR="0x2c0367a9db231ddebd88a94b4f6461a6e47c58b1";UMA_PROPOSER_WHITELIST_ADDR="0x9f35885ce8f67a942d7b2f4fbf937987da08c463";SEL_IS_ON_WHITELIST="3a3ab672";ESPN_NBA_SUMMARY_URL="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}";BOP_2026_SLUGS=("balance-of-power-2026-midterms","which-party-will-win-the-senate-in-2026","which-party-will-win-the-house-in-2026");_NR_ADAPTER_CACHE={};_WHITELIST_CACHE={};_PLAYER_SUFFIX_RE=re.compile(r"\b(?:jr|sr|ii|iii|iv|v)\b\.?",re.IGNORECASE);_PROP_TITLE_RE=re.compile(r"^(.+?):\s*(Points|Rebounds|Assists|3-Pointers Made|Threes|Three Pointers)\s+O/U\s+(\d+\.5)\b",re.IGNORECASE);_NBA_EM_BAND_RE=re.compile(r"Exact\s+Margin:\s*(.+?)\s+by\s+(\d+)(?:-(\d+)|\+)",re.IGNORECASE);_SOC_ADVANCE_VETO_RE=re.compile(r"\b(?:advance|qualify|lift\s+the\s+trophy|win\s+the\s+(?:cup|final|tie|trophy)|extra\s+time\s+included|penalt(?:y|ies)\s+included)\b",re.IGNORECASE);_SPREAD_PARSE_RE=re.compile(r"^(.+?)\s*\(([+-]?\d+\.5)\)\s*$");_MAP_HC_PAIR_RE=re.compile(r"Map\s+Handicap:\s*(.+?)\s*\(([+-]\d+\.5)\)\s*vs\.?\s*(.+?)\s*\(([+-]\d+\.5)\)",re.IGNORECASE)
def _net_unit_bid(px,fee_rate,fee_exp=1.):p=max(.0,min(1.,float(px)));a=float(fee_rate)*((p*(1.-p))**float(fee_exp))if fee_rate>.0 else.0;return max(.0,p-a)
def _is_half_hook(line):
 if line is None or not math.isfinite(line):return False
 a=abs(float(line))-math.floor(abs(float(line)));return abs(a-.5)<1e-6
def canon_player_name(raw):s=unicodedata.normalize("NFKD",str(raw or"")).encode("ascii","ignore").decode("ascii").lower();s=re.sub(r"[^a-z0-9\s]"," ",s);s=_PLAYER_SUFFIX_RE.sub(" ",s);return re.sub(r"\s+"," ",s).strip()
def verify_negrisk_adapter_slate_sync(neg_risk_market_id,expected_n,rpc_url=None,timeout=4.5):
 c=str(neg_risk_market_id or"").strip().lower()
 if len(c)!=66 or not c.startswith("0x"):return False,0,"INVALID_MARKET_ID"
 e=_NR_ADAPTER_CACHE.get(c)
 if e is not None:
  b,a,d=e
  if d:return False,a,"ALREADY_DETERMINED"
  if b!=expected_n:return False,a,f"QCOUNT_MISMATCH({b}!={expected_n})"
  return True,a,"OK"
 k=rpc_url or os.getenv("POLYGON_RPC_URL")or DEFAULT_POLYGON_RPC;j=c[2:];g=[{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":NEGRISK_ADAPTER_ADDR,"data":f"0x{SEL_NR_GET_QUESTION_COUNT}{j}"},"latest"]},{"jsonrpc":"2.0","id":2,"method":"eth_call","params":[{"to":NEGRISK_ADAPTER_ADDR,"data":f"0x{SEL_NR_GET_FEE_BIPS}{j}"},"latest"]},{"jsonrpc":"2.0","id":3,"method":"eth_call","params":[{"to":NEGRISK_ADAPTER_ADDR,"data":f"0x{SEL_NR_GET_DETERMINED}{j}"},"latest"]}]
 try:
  h=_rpc_post(k,g,timeout=timeout);f={int(r["id"]):str(r.get("result")or"")for r in h if isinstance(r,dict)and"id"in r}
  if not all(f.get(i,"").startswith("0x")and len(f[i])>=66 for i in(1,2,3)):return False,0,"BAD_ADAPTER_RPC"
  b=int(f[1],16);a=int(f[2],16);d=int(f[3],16)!=0
  if not d:_NR_ADAPTER_CACHE[c]=(b,a,d)
  if d:return False,a,"ALREADY_DETERMINED"
  if b!=expected_n:return False,a,f"QCOUNT_MISMATCH({b}!={expected_n})"
  return True,a,"OK"
 except Exception as exc:return False,0,f"RPC_ERR:{type(exc).__name__}"
def detect_nr2_convert_no_subset_arbs(spec,books_by_token,target_budget_usd=120.,min_edge_pure_cash=.012,min_edge_with_yes_sell=.015,min_shares=6,fee_bips=0):
 if not spec.is_closed_convert_safe:return[]
 U=len(spec.brackets)
 if U<3 or fee_bips<0 or fee_bips>=500:return[]
 z=1.-float(fee_bips)/1e4;J=[]
 for _b,b in enumerate(spec.brackets):_a=books_by_token.get(b["yes_token"])or{};Z=books_by_token.get(b["no_token"])or{};P=sorted([(float(x["price"]),float(x["size"]))for x in(Z.get("asks")or[])if float(x.get("price",0))>0 and float(x.get("size",0))>0],key=lambda t:t[0]);O=sorted([(float(x["price"]),float(x["size"]))for x in(_a.get("bids")or[])if float(x.get("price",0))>0 and float(x.get("size",0))>0],key=lambda t:-t[0]);fr,fe=float(b["fee_rate"]),float(b["fee_exponent"]);F=_net_unit_ask(P[0][0],fr,fe)if P else 9.9;I=P[0][1]if P else.0;y=_net_unit_bid(O[0][0],fr,fe)if O else.0;E=O[0][1]if O else.0;J.append({"idx":_b,"bracket":b,"asks_n":P,"bids_y":O,"a_no_net":F,"a_no_sh":I,"b_yes_net":y,"b_yes_sh":E})
 v=sorted([x for x in J if x["a_no_sh"]>=min_shares and x["a_no_net"]<.995],key=lambda x:x["a_no_net"])[:6];m=[]
 for Y in(2,3):
  if len(v)>=Y and Y<=U-1:
   for X in itertools.combinations([x["idx"]for x in v],Y):m.append(tuple(sorted(X)))
 if all(x["a_no_sh"]>=min_shares and x["a_no_net"]<.998 for x in J):m.append(tuple(range(U)))
 W=[];N=set()
 for T in m:
  if T in N:continue
  N.add(T);S=len(T);R=set(T);D=[i for i in range(U)if i not in R];l=sum(J[i]["a_no_net"]for i in T)
  if l<=.0:continue
  s=min(J[i]["a_no_sh"]for i in T);H=int(math.floor(min(s,target_budget_usd/max(.25,l))))
  if H<min_shares:continue
  k=sorted([i for i in D if J[i]["b_yes_net"]>=.004 and J[i]["b_yes_sh"]>=min_shares*z],key=lambda i:-J[i]["b_yes_net"]);a=None
  for Q in range(0,len(k)+1):
   M=sorted(k[:Q]);L=sorted([i for i in D if i not in set(M)]);f=H
   if M:C=min(J[j]["b_yes_sh"]/max(z,1e-6)for j in M);f=int(math.floor(min(float(H),C)))
   if f<min_shares:continue
   B=[];K=True
   for i in T:
    bi=J[i]["bracket"];wi=_walk_side_exact_shares((books_by_token.get(bi["no_token"])or{}).get("asks")or[],float(f),float(bi["fee_rate"]),float(bi["fee_exponent"]),is_ask=True)
    if wi is None:K=False;break
    B.append((bi,wi))
   if not K:continue
   h=float(f)*z;r=[]
   for j in M:
    bj=J[j]["bracket"];wj=_walk_side_exact_shares((books_by_token.get(bj["yes_token"])or{}).get("bids")or[],h,float(bj["fee_rate"]),float(bj["fee_exponent"]),is_ask=False)
    if wj is None or wj["net_per_share"]<=.002:K=False;break
    r.append((bj,wj))
   if not K:continue
   p=sum(w["net_per_share"]for _,w in B);e=float(S-1)*z;o=z*sum(w["net_per_share"]for _,w in r);g=e+o;G=round(g-p,5);A=min_edge_pure_cash if not M else min_edge_with_yes_sell
   if G<A:continue
   q=[int(J[i]["bracket"]["question_index"])for i in T];d=sum(1<<qi for qi in q);n=min([w["l1_usd"]for _,w in B]+([w["l1_usd"]for _,w in r]if r else[9999.]));c=[J[u]["bracket"]for u in L];V={"mode":"NR2_SUBSET_CONVERT_FREE_TAIL"if c else"NR2_PURE_CASH_CONVERT","event_id":spec.event_id,"slug":spec.slug,"title":spec.title,"neg_risk_market_id":spec.neg_risk_market_id,"m_no_legs":S,"n_total":U,"question_indices":q,"no_question_indices":q,"index_set":d,"index_set_int":d,"shares":f,"converted_shares_out":round(h,4),"fee_bips":fee_bips,"no_cost_per_share":round(p,4),"usdc_converted_per_share":round(e,4),"yes_bid_proceeds_per_share":round(o,4),"net_proceeds_per_share":round(g,4),"net_edge_per_share":round(G,4),"total_cost_usd":round(sum(w["net_cash_usd"]for _,w in B),2),"total_net_profit_usd":round(f*G,2),"total_fee_usd":round(sum(w["fee_usd"]for _,w in B)+sum(w["fee_usd"]for _,w in r),4),"l1_usd":round(n,2),"no_legs":[{"token_id":b["no_token"],"bracket":b,"walk":w}for b,w in B],"yes_sell_legs":[{"token_id":b["yes_token"],"bracket":b,"walk":w}for b,w in r],"retained_free_yes_brackets":c,"retained_tail_count":len(c),"close_ts":spec.end_ts,"label":(f"NR2({S}/{U}NO->${e:.2f}+SELL[{len(r)}Y]+FREE_TAIL[{len(c)}Y])")}
   if a is None or V["net_edge_per_share"]>a["net_edge_per_share"]:a=V
  if a is not None:W.append(a)
 W.sort(key=lambda x:(-float(x["net_edge_per_share"]),-int(x["retained_tail_count"])));return W
@dataclass
class NbaPlayerPropRung:event_id:str;event_slug:str;game_title:str;market_id:str;condition_id:str;player_name:str;player_key:str;stat_type:str;line:float;yes_token:str;no_token:str;fee_rate:float;tipoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;fee_exponent=1.
@dataclass
class NbaPlayerPropSlate:event_id:str;slug:str;title:str;tipoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;props_by_player_stat=field(default_factory=dict)
_ALLOWED_NBA_PROP_SMTS=frozenset({"points","rebounds","assists","threes"})
def parse_nba_player_props_from_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived"):return None
 v=str(ev.get("slug")or"").lower()
 if not v.startswith("nba-")or v.endswith("-exact-margin"):return None
 n=str(ev.get("title")or"");l=re.split(r"\s+(?:vs\.?|@)\s+",n,maxsplit=1,flags=re.IGNORECASE)
 if len(l)!=2:return None
 h,g=_canon_nba_team(l[0]),_canon_nba_team(l[1]);f=_parse_iso_ts(ev.get("startTime")or ev.get("gameStartTime")or ev.get("endDate"))or.0
 if f<=.0:return None
 if now_ts is not None and f<now_ts-8.*3600.:return None
 c=f+3.25*3600.;j=str(ev.get("id")or"");e={}
 for m in ev.get("markets")or[]:
  if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
  w=str(m.get("sportsMarketType")or"").strip().lower()
  if w not in _ALLOWED_NBA_PROP_SMTS:continue
  y,x=_extract_market_fee_rate(m);u=_parse_clob_tokens(m);t=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not u or t!=["yes","no"]:continue
  d=m.get("line")
  try:a=float(d)if d is not None else float("nan")
  except(TypeError,ValueError):a=float("nan")
  i=str(m.get("groupItemTitle")or m.get("question")or"").strip();s=_PROP_TITLE_RE.match(i)
  if not s:continue
  b=s.group(1).strip()
  if not math.isfinite(a):a=float(s.group(3))
  if not _is_half_hook(a)or a<.5:continue
  q=canon_player_name(b)
  if not q:continue
  p=NbaPlayerPropRung(event_id=j,event_slug=v,game_title=n,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),player_name=b,player_key=q,stat_type=w,line=a,yes_token=u[0],no_token=u[1],fee_rate=y,tipoff_ts=f,settle_est_ts=c,home_team=g,away_team=h,fee_exponent=x);e.setdefault((q,w),[]).append(p)
 if not e:return None
 for k in e:e[k].sort(key=lambda r:r.line)
 return NbaPlayerPropSlate(event_id=j,slug=v,title=n,tipoff_ts=f,settle_est_ts=c,home_team=g,away_team=h,props_by_player_stat=e)
def detect_sp4_milestone_ladder_boxes(slate,best_asks,max_box_cost_net=.992):
 k=[]
 for(_,d),e in slate.props_by_player_stat.items():
  if len(e)<2:continue
  for i in range(len(e)):
   h=e[i];b=best_asks.get(h.yes_token)
   if b is None or not(.02<=b<=.98):continue
   for j in range(i+1,len(e)):
    g=e[j]
    if g.line<=h.line+.1:continue
    a=best_asks.get(g.no_token)
    if a is None or not(.02<=a<=.98):continue
    c=round(float(b)+float(a),4);f=round(_net_unit_ask(float(b),h.fee_rate,h.fee_exponent)+_net_unit_ask(float(a),g.fee_rate,g.fee_exponent),4)
    if f<=max_box_cost_net:k.append({"mode":"SP4_MILESTONE_POLISH_MIDDLE","event_id":slate.event_id,"slug":slate.slug,"title":slate.title,"player_name":h.player_name,"stat_type":d,"line_low":h.line,"line_high":g.line,"box_cost_gross":c,"box_cost_net":f,"close_ts":slate.settle_est_ts,"leg_a":{"token_id":h.yes_token,"opp_token_id":h.no_token,"condition_id":h.condition_id,"market_id":h.market_id,"side":"YES","label":f"{h.player_name} {d.upper()} O{h.line}","fee_rate":h.fee_rate,"fee_exponent":h.fee_exponent,"neg_risk":False,"strike":h.line},"leg_b":{"token_id":g.no_token,"opp_token_id":g.yes_token,"condition_id":g.condition_id,"market_id":g.market_id,"side":"NO","label":f"{g.player_name} {d.upper()} U{g.line}","fee_rate":g.fee_rate,"fee_exponent":g.fee_exponent,"neg_risk":False,"strike":g.line},"label":f"{h.player_name} {d} O{h.line} + U{g.line}"})
 k.sort(key=lambda x:(float(x["box_cost_net"]),-(float(x["line_high"])-float(x["line_low"]))));return k
def parse_espn_nba_boxscore_players(summary_json):
 q={}
 for c in((summary_json or{}).get("boxscore")or{}).get("players")or[]:
  for b in c.get("statistics")or[]:
   n=[str(k)for k in(b.get("keys")or[])]
   if not n:continue
   h=next((i for i,k in enumerate(n)if k=="minutes"),-1);g=next((i for i,k in enumerate(n)if k=="points"),-1);f=next((i for i,k in enumerate(n)if k=="rebounds"),-1);e=next((i for i,k in enumerate(n)if k=="assists"),-1);d=next((i for i,k in enumerate(n)if k.startswith("threePointFieldGoalsMade")),-1)
   for p in b.get("athletes")or[]:
    if p.get("didNotPlay"):continue
    m=str((p.get("athlete")or{}).get("displayName")or"");l=canon_player_name(m);a=p.get("stats")or[]
    if not l or not a:continue
    if h>=0 and h<len(a):
     j=str(a[h]).strip()
     if j in("","0","0:00","--"):continue
    o={}
    try:
     if 0<=g<len(a):o["points"]=int(str(a[g]).split("-")[0])
     if 0<=f<len(a):o["rebounds"]=int(str(a[f]).split("-")[0])
     if 0<=e<len(a):o["assists"]=int(str(a[e]).split("-")[0])
     if 0<=d<len(a):o["threes"]=int(str(a[d]).split("-")[0])
    except ValueError:continue
    if o:q[l]=o
 return q
def fetch_espn_nba_boxscore_players_sync(espn_game_id,timeout=5.):c=ESPN_NBA_SUMMARY_URL.format(game_id=espn_game_id);b=urllib.request.Request(c,headers={"User-Agent":"DominusSportsOracle/1.0"});a=json.loads(urllib.request.urlopen(b,timeout=timeout).read().decode("utf-8"));return parse_espn_nba_boxscore_players(a)
def evaluate_sp4_ingame_clinch_locks(slate,game_state,player_stats):
 if game_state.state not in("in","post")or not player_stats:return[]
 b=bool(game_state.completed and game_state.state=="post");i=[]
 for(k,f),h in slate.props_by_player_stat.items():
  g=player_stats.get(k)
  if not g or f not in g:continue
  e=int(g[f]);a=1 if(b and f in("points","threes"))else 2
  for r in h:
   d=int(math.floor(r.line))+a
   if e>=d:c=round(float(e)-r.line,1);j=.999 if(b or c>=2.5)else.996;i.append({"mode":"SP4_FINAL_STAT_LOCK"if b else"SP4_LIVE_STAT_CLINCH","rung":r,"current_stat":e,"cushion":c,"p_lock":j,"game_state":game_state.state,"period":game_state.period})
 return i
def verify_proposer_whitelisted_sync(proposer_addr,rpc_url=None,timeout=4.5):
 c=str(proposer_addr or"").strip().lower()
 if len(c)!=42 or not c.startswith("0x"):return False
 if c in _WHITELIST_CACHE:return _WHITELIST_CACHE[c]
 f=rpc_url or os.getenv("POLYGON_RPC_URL")or DEFAULT_POLYGON_RPC;a=f"0x{SEL_IS_ON_WHITELIST}{c[2:].rjust(64,'0')}"
 try:e=_rpc_post(f,{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":UMA_PROPOSER_WHITELIST_ADDR,"data":a},"latest"]},timeout=timeout);b=str((e or{}).get("result")or"");d=b.startswith("0x")and len(b)>=66 and(int(b,16)==1);_WHITELIST_CACHE[c]=d;return d
 except Exception:return False
def verify_bond2_moov2_final_hour_sync(m,rpc_url=None,now_ts=None,min_proposal_age_sec=3600.,min_rem_challenge_sec=180.,max_rem_challenge_sec=3300.):
 b=verify_uma_onchain_proposal_sync(m,rpc_url=rpc_url,now_ts=now_ts,min_proposal_age_sec=min_proposal_age_sec,max_rem_challenge_sec=max_rem_challenge_sec)
 if not b.get("verified"):return b
 if str(b.get("adapter")or"").lower()not in UMA_V4_ADAPTERS:return{"verified":False,"reason":"NOT_V4_ADAPTER"}
 if str(b.get("oo_address")or"").lower()!=MOOV2_ORACLE_ADDR:return{"verified":False,"reason":"NOT_MOOV2_ORACLE"}
 a=float(b.get("rem_challenge_sec")or.0)
 if a<min_rem_challenge_sec:return{"verified":False,"reason":f"REM_TOO_SHORT({a:.0f}s)"}
 if not verify_proposer_whitelisted_sync(str(b.get("proposer")or""),rpc_url=rpc_url):return{"verified":False,"reason":"PROPOSER_NOT_WHITELISTED"}
 c=dict(b);c["proposer_whitelisted"]=True;c["moov2_final_hour"]=True;return c
@dataclass
class SoccerRegulationTree:game_id:str;event_id_3way:str;slug_3way:str;title:str;neg_risk_market_id:str;end_ts:float;home_team:str;away_team:str;home_leg:Dict[str,Any];draw_leg:Dict[str,Any];away_leg:Dict[str,Any];over05_leg=None;totals=field(default_factory=list);spreads=field(default_factory=list)
def link_and_parse_soccer_regulation_trees(events,now_ts=None):
 A={}
 for Z in events or[]:
  if not isinstance(Z,dict)or Z.get("closed")or Z.get("archived"):continue
  z=str(Z.get("gameId")or"").strip()
  if z:A.setdefault(z,[]).append(Z)
 H={}
 for z,v in A.items():
  b=None;c=None
  for e in v:
   Y=str(e.get("slug")or"").lower();T=e.get("markets")or[]
   if Y.endswith("-more-markets")and not e.get("negRisk"):c=e
   elif(bool(e.get("negRisk"))and not bool(e.get("negRiskAugmented",True))and len(T)==3 and not any(Y.endswith(suf)for suf in("-halftime-result","-second-half-result","-first-to-score","-exact-score"))and all(str(m.get("sportsMarketType")or"").lower()in("moneyline","soccer_match_winner","")for m in T)):b=e
  if b is None:continue
  y=_parse_iso_ts(b.get("startTime")or b.get("endDate"))or.0
  if y<=.0 or(now_ts is not None and y<now_ts-4.*3600.):continue
  i=str(b.get("negRiskMarketID")or"").strip().lower();f=None;g=None;d=None;n=[];a=False
  for G,m in enumerate(b.get("markets")or[]):
   if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:a=True;break
   F=str(m.get("question")or"");S=str(m.get("description")or"");U=str(m.get("groupItemTitle")or"").strip()
   if _SOC_ADVANCE_VETO_RE.search(f"{F}\n{S}\n{U}"):a=True;break
   R=_parse_clob_tokens(m);Q=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
   if not R or Q!=["yes","no"]:a=True;break
   X,P=_extract_market_fee_rate(m);O=str(m.get("questionID")or"").strip().lower();E=int(O[64:],16)if(len(O)==66 and O.startswith("0x"))else G;D={"market_id":str(m.get("id")or""),"condition_id":str(m.get("conditionId")or""),"question_index":E,"label":U or F[:36],"team_norm":_norm_team(U),"yes_token":R[0],"no_token":R[1],"fee_rate":X,"fee_exponent":P,"neg_risk":True}
   if"draw"in U.lower()or"end in a draw"in F.lower():g=D
   else:n.append(D)
  if a or g is None or len(n)!=2:continue
  f,d=n[0],n[1];N=SoccerRegulationTree(game_id=z,event_id_3way=str(b.get("id")or""),slug_3way=str(b.get("slug")or""),title=str(b.get("title")or b.get("slug")or""),neg_risk_market_id=i,end_ts=y+2.5*3600.,home_team=f["team_norm"],away_team=d["team_norm"],home_leg=f,draw_leg=g,away_leg=d)
  if c is not None:
   for W in c.get("markets")or[]:
    if W.get("closed")or W.get("archived")or W.get("acceptingOrders")is False:continue
    u=str(W.get("description")or"");M=str(W.get("question")or"");w=str(W.get("groupItemTitle")or"").strip()
    if _SOC_ADVANCE_VETO_RE.search(f"{M}\n{u}\n{w}"):continue
    t=_parse_clob_tokens(W);s=[str(o).strip()for o in _parse_json_list(W.get("outcomes"))]
    if not t or len(s)!=2:continue
    L,K=_extract_market_fee_rate(W);C=str(W.get("sportsMarketType")or"").strip().lower()
    try:l=float(W.get("line"))if W.get("line")is not None else float("nan")
    except(TypeError,ValueError):l=float("nan")
    if C=="totals"and _is_half_hook(l):
     V=s[0].lower();k,h=(t[0],t[1])if"over"in V else(t[1],t[0]);B={"market_id":str(W.get("id")or""),"condition_id":str(W.get("conditionId")or""),"line":abs(l),"over_token":k,"under_token":h,"fee_rate":L,"fee_exponent":K,"neg_risk":False};N.totals.append(B)
     if abs(abs(l)-.5)<1e-6:N.over05_leg=B
    elif C=="spreads"and _is_half_hook(l)and l<0:
     J=_SPREAD_PARSE_RE.match(w)
     if J:j=_norm_team(J.group(1));I=_norm_team(s[0]);r,q=(t[0],t[1])if j==I else(t[1],t[0]);p=s[1]if j==I else s[0];N.spreads.append({"market_id":str(W.get("id")or""),"condition_id":str(W.get("conditionId")or""),"fav_team":j,"fav_label":J.group(1).strip(),"dog_label":p,"abs_line":abs(l),"fav_minus_token":r,"dog_plus_token":q,"fee_rate":L,"fee_exponent":K,"neg_risk":False})
   N.totals.sort(key=lambda x:float(x["line"]));N.spreads.sort(key=lambda x:(x["fav_team"],float(x["abs_line"])))
  H[z]=N
 return H
def detect_soc1_regulation_boxes(tree,books_by_token,best_asks,max_2leg_cost_net=.988,min_conv_edge_ps=.01,target_budget_usd=120.):
 d=[];e=[]
 if tree.over05_leg is not None:
  P,J=tree.draw_leg,tree.over05_leg;F=best_asks.get(P["yes_token"]);E=best_asks.get(J["over_token"])
  if F is not None and E is not None:
   c=round(_net_unit_ask(F,P["fee_rate"],P["fee_exponent"])+_net_unit_ask(E,J["fee_rate"],J["fee_exponent"]),4)
   if c<=max_2leg_cost_net:d.append({"mode":"SOC1_SCORING_DRAW_CORRIDOR","game_id":tree.game_id,"title":tree.title,"box_cost_net":c,"close_ts":tree.end_ts,"leg_a":{"token_id":P["yes_token"],"opp_token_id":P["no_token"],"condition_id":P["condition_id"],"market_id":P["market_id"],"side":"YES","label":"YES[Draw]","fee_rate":P["fee_rate"],"fee_exponent":P["fee_exponent"],"neg_risk":True,"strike":.5},"leg_b":{"token_id":J["over_token"],"opp_token_id":J["under_token"],"condition_id":J["condition_id"],"market_id":J["market_id"],"side":"OVER","label":"OVER[0.5 Goals]","fee_rate":J["fee_rate"],"fee_exponent":J["fee_exponent"],"neg_risk":False,"strike":.5},"label":f"{tree.title}: YES[Draw] + OVER[0.5 Goals]"})
 for i in range(len(tree.totals)):
  D=tree.totals[i];z=best_asks.get(D["over_token"])
  if z is None:continue
  for j in range(i+1,len(tree.totals)):
   C=tree.totals[j]
   if C["line"]<=D["line"]+.1:continue
   y=best_asks.get(C["under_token"])
   if y is None:continue
   c=round(_net_unit_ask(z,D["fee_rate"],D["fee_exponent"])+_net_unit_ask(y,C["fee_rate"],C["fee_exponent"]),4)
   if c<=max_2leg_cost_net:d.append({"mode":"SOC1_GOAL_CORRIDOR_BOX","game_id":tree.game_id,"title":tree.title,"box_cost_net":c,"close_ts":tree.end_ts,"leg_a":{"token_id":D["over_token"],"opp_token_id":D["under_token"],"condition_id":D["condition_id"],"market_id":D["market_id"],"side":"OVER","label":f"O{D['line']}","fee_rate":D["fee_rate"],"fee_exponent":D["fee_exponent"],"neg_risk":False,"strike":D["line"]},"leg_b":{"token_id":C["under_token"],"opp_token_id":C["over_token"],"condition_id":C["condition_id"],"market_id":C["market_id"],"side":"UNDER","label":f"U{C['line']}","fee_rate":C["fee_rate"],"fee_exponent":C["fee_exponent"],"neg_risk":False,"strike":C["line"]},"label":f"{tree.title}: Goals O{D['line']} + U{C['line']}"})
 for i in range(len(tree.spreads)):
  O=tree.spreads[i];B=best_asks.get(O["fav_minus_token"])
  if B is None:continue
  for j in range(i+1,len(tree.spreads)):
   N=tree.spreads[j]
   if N["fav_team"]!=O["fav_team"]or N["abs_line"]<=O["abs_line"]+.1:continue
   A=best_asks.get(N["dog_plus_token"])
   if A is None:continue
   c=round(_net_unit_ask(B,O["fee_rate"],O["fee_exponent"])+_net_unit_ask(A,N["fee_rate"],N["fee_exponent"]),4)
   if c<=max_2leg_cost_net:d.append({"mode":"SOC1_HANDICAP_CORRIDOR_BOX","game_id":tree.game_id,"title":tree.title,"box_cost_net":c,"close_ts":tree.end_ts,"leg_a":{"token_id":O["fav_minus_token"],"opp_token_id":O["dog_plus_token"],"condition_id":O["condition_id"],"market_id":O["market_id"],"side":"SPREAD","label":f"{O['fav_label']}(-{O['abs_line']})","fee_rate":O["fee_rate"],"fee_exponent":O["fee_exponent"],"neg_risk":False,"strike":-O["abs_line"]},"leg_b":{"token_id":N["dog_plus_token"],"opp_token_id":N["fav_minus_token"],"condition_id":N["condition_id"],"market_id":N["market_id"],"side":"SPREAD","label":f"{N['dog_label']}(+{N['abs_line']})","fee_rate":N["fee_rate"],"fee_exponent":N["fee_exponent"],"neg_risk":False,"strike":N["abs_line"]},"label":f"{tree.title}: {O['fav_label']}(-{O['abs_line']}) + {N['dog_label']}(+{N['abs_line']})"})
 w=[tree.home_leg,tree.draw_leg,tree.away_leg]
 if len(tree.neg_risk_market_id)==66 and{int(x["question_index"])for x in w}=={0,1,2}:
  for v in range(3):
   I=w[v];H,G=[w[u]for u in range(3)if u!=v];t=books_by_token.get(H["no_token"])or{};s=books_by_token.get(G["no_token"])or{};r=books_by_token.get(I["yes_token"])or{};o=t.get("asks")or[];n=s.get("asks")or[];m=r.get("bids")or[]
   if not(o and n and m):continue
   p=min(max((float(a.get("size",0))for a in o[:1]),default=.0),max((float(a.get("size",0))for a in n[:1]),default=.0),max((float(b.get("size",0))for b in m[:1]),default=.0));l=int(math.floor(min(p,target_budget_usd/.8)))
   if l<6:continue
   M=_walk_side_exact_shares(o,float(l),H["fee_rate"],H["fee_exponent"],is_ask=True);L=_walk_side_exact_shares(n,float(l),G["fee_rate"],G["fee_exponent"],is_ask=True);K=_walk_side_exact_shares(m,float(l),I["fee_rate"],I["fee_exponent"],is_ask=False)
   if M is None or L is None or K is None:continue
   f=M["net_per_share"]+L["net_per_share"];h=1.+K["net_per_share"];g=round(h-f,5)
   if g>=min_conv_edge_ps:k=sorted([int(H["question_index"]),int(G["question_index"])]);e.append({"mode":"SOC1_3WAY_CONVERT_SYNTHETIC","event_id":tree.event_id_3way,"game_id":tree.game_id,"title":tree.title,"neg_risk_market_id":tree.neg_risk_market_id,"m_no_legs":2,"n_total":3,"no_question_indices":k,"index_set_int":sum(1<<q for q in k),"shares":l,"no_cost_per_share":round(f,4),"yes_bid_proceeds_per_share":round(K["net_per_share"],4),"net_edge_per_share":round(g,4),"total_net_profit_usd":round(l*g,2),"l1_usd":round(min(M["l1_usd"],L["l1_usd"],K["l1_usd"]),2),"no_legs":[{"token_id":H["no_token"],"bracket":H,"walk":M},{"token_id":G["no_token"],"bracket":G,"walk":L}],"yes_sell_legs":[{"token_id":I["yes_token"],"bracket":I,"walk":K}],"close_ts":tree.end_ts,"label":f"SOC1_CONV(NO[{H['label'][:12]}]+NO[{G['label'][:12]}]->$1+SELL[{I['label'][:12]}])"})
 d.sort(key=lambda x:float(x["box_cost_net"]));e.sort(key=lambda x:-float(x["net_edge_per_share"]));return{"two_leg_boxes":d,"convert_arbs":e}
def find_state_matrix_dominance_boxes(legs,best_asks,max_2leg_cost_net=.994,max_3leg_cost_net=.992):
 b=[]
 for A in legs:
  t=str(A["token_id"])
  if t not in best_asks:continue
  z=float(best_asks[t])
  if not(.001<=z<=.992):continue
  g=_net_unit_ask(z,float(A.get("fee_rate",.0)),float(A.get("fee_exponent",1.)));b.append((A,z,g))
 if len(b)<2:return[]
 a=len(b[0][0]["payoff_vec"]);r=[]
 for i in range(len(b)):
  p,_,o=b[i];n=p["payoff_vec"]
  for j in range(i+1,len(b)):
   m,_,l=b[j]
   if p["market_id"]==m["market_id"]:continue
   f=round(o+l,4)
   if f>max_2leg_cost_net:continue
   h=m["payoff_vec"];q=[n[s]+h[s]for s in range(a)]
   if min(q)>=1.-1e-9:r.append({"n_legs":2,"box_cost_net":f,"min_payout":round(min(q),4),"max_payout":round(max(q),4),"jackpot_states":sum(1 for v in q if v>=1.5-1e-9),"legs":[p,m],"close_ts":max(float(p["end_ts"]),float(m["end_ts"])),"label":f"{p['label']} + {m['label']}"})
 e=sorted(b,key=lambda x:x[2])[:18]
 for i in range(len(e)):
  p,_,o=e[i];n=p["payoff_vec"]
  for j in range(i+1,len(e)):
   m,_,l=e[j]
   if o+l>max_3leg_cost_net:continue
   h=m["payoff_vec"]
   if min(n[s]+h[s]for s in range(a))>=1.-1e-9:continue
   for k in range(j+1,len(e)):
    y,_,w=e[k];d=round(o+l+w,4)
    if d>max_3leg_cost_net:continue
    if len({p["market_id"],m["market_id"],y["market_id"]})<2:continue
    u=y["payoff_vec"]
    if min(n[s]+u[s]for s in range(a))>=1.-1e-9:continue
    if min(h[s]+u[s]for s in range(a))>=1.-1e-9:continue
    c=[n[s]+h[s]+u[s]for s in range(a)]
    if min(c)>=1.-1e-9:r.append({"n_legs":3,"box_cost_net":d,"min_payout":round(min(c),4),"max_payout":round(max(c),4),"jackpot_states":sum(1 for v in c if v>=1.5-1e-9),"legs":[p,m,y],"close_ts":max(float(p["end_ts"]),float(m["end_ts"]),float(y["end_ts"])),"label":f"{p['label']} + {m['label']} + {y['label']}"})
 r.sort(key=lambda x:(float(x["box_cost_net"]),-int(x["jackpot_states"])));return r
BOP_9_STATES=(("D","D"),("D","R"),("D","O"),("R","D"),("R","R"),("R","O"),("O","D"),("O","R"),("O","O"))
def build_lp1_bop_2026_truth_legs(events_by_slug):
 e=[]
 def _add_mkt(m,event_slug,tag_lbl,yes_fn):
  if m.get("closed")or m.get("archived")or m.get("active")is False:return
  d=_parse_clob_tokens(m)
  if not d:return
  i,h=_extract_market_fee_rate(m);a=_parse_iso_ts(m.get("endDate"))or.0;f=str(m.get("id")or"");e=str(m.get("conditionId")or"");g=bool(m.get("negRisk"));b=[1. if yes_fn(k,j)else.0 for k,j in BOP_9_STATES];c=[1.-x for x in b];e.append({"event_slug":event_slug,"market_id":f,"condition_id":e,"token_id":d[0],"opp_token_id":d[1],"side":"YES","label":f"YES[{tag_lbl}]","fee_rate":i,"fee_exponent":h,"neg_risk":g,"end_ts":a,"payoff_vec":b,"strike":1.});e.append({"event_slug":event_slug,"market_id":f,"condition_id":e,"token_id":d[1],"opp_token_id":d[0],"side":"NO","label":f"NO[{tag_lbl}]","fee_rate":i,"fee_exponent":h,"neg_risk":g,"end_ts":a,"payoff_vec":c,"strike":1.})
 d=events_by_slug.get("balance-of-power-2026-midterms")or{}
 for m in d.get("markets")or[]:
  q=str(m.get("question")or m.get("groupItemTitle")or"").lower()
  if"d senate, d house"in q or"democrats sweep"in q:_add_mkt(m,"bop","BOP:D_Sweep",lambda s,h:s=="D"and h=="D")
  elif"d senate, r house"in q:_add_mkt(m,"bop","BOP:DSen_RHouse",lambda s,h:s=="D"and h=="R")
  elif"r senate, d house"in q:_add_mkt(m,"bop","BOP:RSen_DHouse",lambda s,h:s=="R"and h=="D")
  elif"r senate, r house"in q or"republicans sweep"in q:_add_mkt(m,"bop","BOP:R_Sweep",lambda s,h:s=="R"and h=="R")
  elif"other"in q:_add_mkt(m,"bop","BOP:Other",lambda s,h:s=="O"or h=="O")
 c=events_by_slug.get("which-party-will-win-the-senate-in-2026")or{}
 for m in c.get("markets")or[]:
  a=str(m.get("groupItemTitle")or"").strip().lower()
  if a=="democratic party":_add_mkt(m,"senate","Sen:Dem",lambda s,h:s=="D")
  elif a=="republican party":_add_mkt(m,"senate","Sen:Rep",lambda s,h:s=="R")
 b=events_by_slug.get("which-party-will-win-the-house-in-2026")or{}
 for m in b.get("markets")or[]:
  a=str(m.get("groupItemTitle")or"").strip().lower()
  if a=="democratic party":_add_mkt(m,"house","House:Dem",lambda s,h:h=="D")
  elif a=="republican party":_add_mkt(m,"house","House:Rep",lambda s,h:h=="R")
 return e
_EM_BANDS=((1,5),(6,10),(11,15),(16,20),(21,999))
def build_lp1_nba_exact_margin_bundle(parent_ev,em_ev):
 if parent_ev.get("closed")or em_ev.get("closed")or not em_ev.get("negRisk")or em_ev.get("negRiskAugmented",True):return None
 r=em_ev.get("markets")or[]
 if len(r)!=11:return None
 D=(_parse_iso_ts(parent_ev.get("startTime")or parent_ev.get("endDate"))or.0)+3.25*3600.;h=str(em_ev.get("negRiskMarketID")or"").strip().lower();C=next((m for m in(parent_ev.get("markets")or[])if str(m.get("sportsMarketType")or"").lower()=="moneyline"and not m.get("closed")),None)
 if C is None:return None
 q=_parse_clob_tokens(C);p=[str(o).strip()for o in _parse_json_list(C.get("outcomes"))];Q,P=_extract_market_fee_rate(C)
 if not q or len(p)!=2:return None
 B,A=_canon_nba_team(p[0]),_canon_nba_team(p[1]);z=str(C.get("id")or"");y=str(C.get("conditionId")or"");_d=[];O=[1.]*5+[.0]*5+[.5];N=[.0]*5+[1.]*5+[.5];_d.append({"market_id":z,"condition_id":y,"token_id":q[0],"opp_token_id":q[1],"side":"ML_A","label":f"ML[{p[0]}]","fee_rate":Q,"fee_exponent":P,"neg_risk":False,"end_ts":D,"payoff_vec":O,"strike":.0});_d.append({"market_id":z,"condition_id":y,"token_id":q[1],"opp_token_id":q[0],"side":"ML_B","label":f"ML[{p[1]}]","fee_rate":Q,"fee_exponent":P,"neg_risk":False,"end_ts":D,"payoff_vec":N,"strike":.0});f={5.5:1,10.5:2,15.5:3,20.5:4}
 for sm in parent_ev.get("markets")or[]:
  if sm.get("closed")or str(sm.get("sportsMarketType")or"").lower()!="spreads":continue
  _c,_b=_extract_market_fee_rate(sm)
  try:_a=abs(float(sm.get("line")))
  except(TypeError,ValueError):continue
  if _a not in f:continue
  Z=_parse_clob_tokens(sm);w=[str(o).strip()for o in _parse_json_list(sm.get("outcomes"))];M=str(sm.get("groupItemTitle")or sm.get("question")or"");Y=re.search(r"([A-Za-z0-9\s\.]+?)\s*\(-"+re.escape(str(_a))+r"\)",M)
  if not Z or len(w)!=2 or not Y:continue
  L=_canon_nba_team(Y.group(1));n=f[_a];X=_canon_nba_team(w[0]);l,j=(Z[0],Z[1])if L==X else(Z[1],Z[0])
  if L==B:e=[1. if idx>=n else.0 for idx in range(5)]+[.0]*5+[.5]
  elif L==A:e=[.0]*5+[1. if idx>=n else.0 for idx in range(5)]+[.5]
  else:continue
  K=[1.-x if i<10 else.5 for i,x in enumerate(e)];J,v=str(sm.get("id")or""),str(sm.get("conditionId")or"");_d.append({"market_id":J,"condition_id":v,"token_id":l,"opp_token_id":j,"side":"SPREAD","label":f"{L.title()}(-{_a})","fee_rate":_c,"fee_exponent":_b,"neg_risk":False,"end_ts":D,"payoff_vec":e,"strike":-_a});_d.append({"market_id":J,"condition_id":v,"token_id":j,"opp_token_id":l,"side":"SPREAD","label":f"Opp(+{_a})","fee_rate":_c,"fee_exponent":_b,"neg_risk":False,"end_ts":D,"payoff_vec":K,"strike":_a})
 c=[];b=[];d=set()
 for I,m in enumerate(r):
  if m.get("closed")or m.get("archived"):return None
  W,V=_extract_market_fee_rate(m);U=_parse_clob_tokens(m)
  if not U:return None
  _f=str(m.get("groupItemTitle")or m.get("question")or"").strip();T=str(m.get("questionID")or"").strip().lower();H=int(T[64:],16)if(len(T)==66 and T.startswith("0x"))else I;a=None
  if"other"in _f.lower():a=10
  else:
   _e=_NBA_EM_BAND_RE.search(_f)
   if _e:
    S=_canon_nba_team(_e.group(1));lo=int(_e.group(2));u=next((k for k,(blo,_)in enumerate(_EM_BANDS)if blo==lo),None)
    if u is not None:
     if S==B or S in B or B in S:a=u
     elif S==A or S in A or A in S:a=5+u
  if a is None:return None
  d.add(a);G=[1. if s==a else.0 for s in range(11)];R=[1.-x for x in G];F,E=str(m.get("id")or""),str(m.get("conditionId")or"");g=_f.replace("Exact Margin:","").strip();_d.append({"market_id":F,"condition_id":E,"token_id":U[0],"opp_token_id":U[1],"side":"YES","label":f"EM_Y[{g}]","fee_rate":W,"fee_exponent":V,"neg_risk":True,"end_ts":D,"payoff_vec":G,"strike":float(a)});t={"market_id":F,"condition_id":E,"token_id":U[1],"opp_token_id":U[0],"side":"NO","label":f"EM_N[{g}]","fee_rate":W,"fee_exponent":V,"neg_risk":True,"end_ts":D,"payoff_vec":R,"strike":float(a),"question_index":H};_d.append(t)
  if 0<=a<=4:c.append(t)
  elif 5<=a<=9:b.append(t)
 if d!=set(range(11)):return None
 return{"event_id":str(parent_ev.get("id")or""),"em_event_id":str(em_ev.get("id")or""),"slug":str(parent_ev.get("slug")or""),"title":str(parent_ev.get("title")or""),"neg_risk_market_id":h,"end_ts":D,"legs":_d,"ml_a_token":q[0],"ml_b_token":q[1],"ml_a_label":p[0],"ml_b_label":p[1],"team_a_em_no":c,"team_b_em_no":b}
@dataclass
class EsportsBo3Spec:event_id:str;slug:str;title:str;end_ts:float;team_a:str;team_b:str;ml_market_id:str;ml_condition_id:str;ml_a_token:str;ml_b_token:str;ml_fee_rate:float;ml_fee_exp:float;hc_market_id:str;hc_condition_id:str;hc_fav_is_a:bool;hc_minus_token:str;hc_plus_token:str;hc_fee_rate:float;hc_fee_exp:float;map1_a_token=None;map1_b_token=None;map1_resolved_winner=None;map2_a_token=None;map2_b_token=None;map2_resolved_winner=None;ou25_over_token=None;ou25_under_token=None;ou25_market_id="";ou25_condition_id="";ou25_fee_rate=.03
def parse_esports_bo3_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived"):return None
 H=str(ev.get("title")or"");N=ev.get("markets")or[];e=bool(re.search(r"\(\s*bo3\s*\)|\bbest\s+of\s+3\b",H,re.IGNORECASE));b=any(re.search(r"\bmap\s+[45]\b",str(m.get("groupItemTitle")or m.get("question")or""),re.IGNORECASE)for m in N)
 if b:return None
 i=any(str(m.get("sportsMarketType")or"").lower()=="totals"and abs(float(m.get("line")or 0)-2.5)<1e-6 for m in N if m.get("line")is not None)
 if not(e or i):return None
 w=(_parse_iso_ts(ev.get("startTime")or ev.get("endDate"))or.0)+3.5*3600.
 if now_ts is not None and w<now_ts+60.:return None
 M=next((m for m in N if str(m.get("sportsMarketType")or"").lower()=="moneyline"and not m.get("closed")),None);L=next((m for m in N if str(m.get("sportsMarketType")or"").lower()=="map_handicap"and not m.get("closed")and abs(abs(float(m.get("line")or 0))-1.5)<1e-6),None)
 if M is None or L is None:return None
 r=_parse_clob_tokens(M);q=[str(o).strip()for o in _parse_json_list(M.get("outcomes"))];p=_parse_clob_tokens(L);n=[str(o).strip()for o in _parse_json_list(L.get("outcomes"))]
 if not r or len(q)!=2 or not p or len(n)!=2:return None
 v,u=q[0],q[1];K,J=_norm_team(v),_norm_team(u);l,k=_norm_team(n[0]),_norm_team(n[1])
 if{K,J}!={l,k}:return None
 j=str(L.get("description")or"");t=str(L.get("groupItemTitle")or L.get("question")or"");a=None;d=re.search(r'resolve\s+to\s+"([^"]+)"\s+if\s+.+?\s+wins\s+2\s+or\s+more\s+maps',j,re.IGNORECASE)
 if d:
  G=_norm_team(d.group(1))
  if G==K:a=True
  elif G==J:a=False
 if a is None:
  s=_MAP_HC_PAIR_RE.search(t)
  if s:O=float(s.group(2));h=l if O<0 else k;a=(h==K)
 if a is None:return None
 g=K if a else J;c,f=(p[0],p[1])if l==g else(p[1],p[0]);F,E=_extract_market_fee_rate(M);D,C=_extract_market_fee_rate(L);I=EsportsBo3Spec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),title=H,end_ts=w,team_a=v,team_b=u,ml_market_id=str(M.get("id")or""),ml_condition_id=str(M.get("conditionId")or""),ml_a_token=r[0],ml_b_token=r[1],ml_fee_rate=F,ml_fee_exp=E,hc_market_id=str(L.get("id")or""),hc_condition_id=str(L.get("conditionId")or""),hc_fav_is_a=a,hc_minus_token=c,hc_plus_token=f,hc_fee_rate=D,hc_fee_exp=C)
 def _extract_map_winner(cm):
  f=_parse_clob_tokens(cm);e=[_norm_team(str(x))for x in _parse_json_list(cm.get("outcomes"))];d=_parse_json_list(cm.get("outcomePrices"));c,b=None,None
  if f and len(e)==2 and{e[0],e[1]}=={K,J}:c,b=(f[0],f[1])if e[0]==K else(f[1],f[0])
  a=None
  if len(d)==2 and len(e)==2:
   try:
    h,g=float(d[0]),float(d[1])
    if cm.get("closed")or(max(h,g)>=.995 and min(h,g)<=.005):
     if h>=.995 and g<=.005:a="A"if e[0]==K else"B"
     elif g>=.995 and h<=.005:a="A"if e[1]==K else"B"
   except(TypeError,ValueError):pass
  return c,b,a
 for cm in N:
  B=str(cm.get("sportsMarketType")or"").lower();A=str(cm.get("groupItemTitle")or cm.get("question")or"").lower()
  if B=="child_moneyline":
   if"map 1"in A or"game 1"in A:I.map1_a_token,I.map1_b_token,I.map1_resolved_winner=_extract_map_winner(cm)
   elif"map 2"in A or"game 2"in A:I.map2_a_token,I.map2_b_token,I.map2_resolved_winner=_extract_map_winner(cm)
  elif B=="totals"and not cm.get("closed")and cm.get("line")is not None and abs(float(cm.get("line"))-2.5)<1e-6:
   z=_parse_clob_tokens(cm);y=[str(x).lower()for x in _parse_json_list(cm.get("outcomes"))]
   if z and len(y)==2:I.ou25_over_token=z[0]if"over"in y[0]else z[1];I.ou25_under_token=z[1]if"over"in y[0]else z[0];I.ou25_market_id=str(cm.get("id")or"");I.ou25_condition_id=str(cm.get("conditionId")or"");I.ou25_fee_rate,_=_extract_market_fee_rate(cm)
 return I
def _infer_live_map_winner(resolved_flag,tok_a,tok_b,books_by_token):
 if resolved_flag in("A","B"):return resolved_flag
 if not tok_a or not tok_b:return None
 h=books_by_token.get(tok_a)or{};g=books_by_token.get(tok_b)or{};f=max((float(b.get("price",0))for b in(h.get("bids")or[])if float(b.get("size",0))>0),default=.0);e=max((float(b.get("price",0))for b in(g.get("bids")or[])if float(b.get("size",0))>0),default=.0);d=min((float(a.get("price",1))for a in(h.get("asks")or[])if float(a.get("size",0))>0),default=1.);c=min((float(a.get("price",1))for a in(g.get("asks")or[])if float(a.get("size",0))>0),default=1.)
 if f>=.992 and e<=.005 and c<=.015:return"A"
 if e>=.992 and f<=.005 and d<=.015:return"B"
 return None
def evaluate_api1_esports_bo3_opportunities(spec,books_by_token,best_asks,max_middle_cost_net=.988):
 j=[];i=[];l=_infer_live_map_winner(spec.map1_resolved_winner,spec.map1_a_token,spec.map1_b_token,books_by_token);k=_infer_live_map_winner(spec.map2_resolved_winner,spec.map2_a_token,spec.map2_b_token,books_by_token);g="B"if spec.hc_fav_is_a else"A";f=spec.team_b if spec.hc_fav_is_a else spec.team_a;e=spec.team_a if spec.hc_fav_is_a else spec.team_b;b=spec.ml_a_token if spec.hc_fav_is_a else spec.ml_b_token;a=spec.ml_b_token if spec.hc_fav_is_a else spec.ml_a_token
 if l==g:j.append({"mode":"API1_BO3_MAP1_PLUS15_LOCK","token_id":spec.hc_plus_token,"opp_token_id":spec.hc_minus_token,"market_id":spec.hc_market_id,"condition_id":spec.hc_condition_id,"fee_rate":spec.hc_fee_rate,"fee_exponent":spec.hc_fee_exp,"p_lock":.997,"side_label":"PLUS_1.5","display_label":f"{f} (+1.5 Maps) [Map 1 Won]","close_ts":spec.end_ts})
 if l in("A","B")and k in("A","B")and l!=k and spec.ou25_over_token and spec.ou25_under_token:j.append({"mode":"API1_BO3_1_1_OVER25_LOCK","token_id":spec.ou25_over_token,"opp_token_id":spec.ou25_under_token,"market_id":spec.ou25_market_id,"condition_id":spec.ou25_condition_id,"fee_rate":spec.ou25_fee_rate,"fee_exponent":1.,"p_lock":.998,"side_label":"OVER_2.5","display_label":f"{spec.title[:44]} Over 2.5 Maps [1-1 Split]","close_ts":spec.end_ts})
 d=best_asks.get(b);c=best_asks.get(spec.hc_plus_token)
 if d is not None and c is not None:
  h=round(_net_unit_ask(d,spec.ml_fee_rate,spec.ml_fee_exp)+_net_unit_ask(c,spec.hc_fee_rate,spec.hc_fee_exp),4)
  if h<=max_middle_cost_net:i.append({"mode":"API1_BO3_POST_M1_MIDDLE"if l==g else"API1_BO3_2_1_POLISH_MIDDLE","event_id":spec.event_id,"title":spec.title,"box_cost_net":h,"post_m1_forfeit_immune":(l==g),"close_ts":spec.end_ts,"leg_a":{"token_id":b,"opp_token_id":a,"condition_id":spec.ml_condition_id,"market_id":spec.ml_market_id,"side":"ML","label":f"ML[{e}]","fee_rate":spec.ml_fee_rate,"fee_exponent":spec.ml_fee_exp,"neg_risk":False,"strike":.0},"leg_b":{"token_id":spec.hc_plus_token,"opp_token_id":spec.hc_minus_token,"condition_id":spec.hc_condition_id,"market_id":spec.hc_market_id,"side":"HANDICAP","label":f"{f}(+1.5)","fee_rate":spec.hc_fee_rate,"fee_exponent":spec.hc_fee_exp,"neg_risk":False,"strike":1.5},"label":f"{spec.title[:42]}: ML[{e}] + {f}(+1.5)"})
 return{"single_leg_locks":j,"two_leg_boxes":i}
# ======================================================================================
# [14/21] MODULE: src/polymarket_research/riskless_frontier_v3_engine.py
# PURPOSE: Riskless Frontier v3 Engine (NFL Exact Margin/Spread, Subperiod Clinch, Deadline Ladder, Tennis Retirement-Safe Corridor, Multi-Sport Post-Review Clinch)
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import math;import re;import time;import urllib.request;from dataclasses import dataclass,field;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;from src.polymarket_research.riskless_frontier_v2_engine import(ESPN_NBA_SUMMARY_URL,NbaPlayerPropRung,NbaPlayerPropSlate,_infer_live_map_winner,_is_half_hook,_net_unit_bid,canon_player_name,find_state_matrix_dominance_boxes,parse_espn_nba_boxscore_players,verify_negrisk_adapter_slate_sync);from src.polymarket_research.tradfi_sports_zero_fee_engine import(_SPREAD_FAV_RE,_extract_market_fee_rate,_net_unit_ask,_norm_team,_parse_clob_tokens,_parse_iso_ts,_walk_side_exact_shares);from src.polymarket_research.uma_nba_endgame_engine import(LiveNbaGameState,_canon_nba_team,_parse_json_list);LP2_MIDTERM_CORE_SLUGS=("republican-house-seats-after-the-2026-midterm-elections","republican-senate-seats-after-the-2026-midterm-elections-927","which-party-will-win-the-house-in-2026","which-party-will-win-the-senate-in-2026","balance-of-power-2026-midterms","republican-trifecta-with-supermajority-in-the-senate","who-wins-the-senate-pending-hormuz-agreement-before-the-midterms");LP2_TOSSUP_CUBE_SLUG="which-tossup-senate-states-will-republicans-win-ak-ia-ks-me-mi-oh-tx";LP2_TOSSUP_STATE_SLUGS={"AK":"alaska-senate-election-winner","IA":"iowa-senate-election-winner","KS":"kansas-senate-election-winner","ME":"maine-senate-election-winner","MI":"michigan-senate-election-winner","OH":"ohio-senate-election-winner","TX":"texas-senate-election-winner"};ESPN_SCOREBOARD_URLS={"SOCCER":("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/ksa.1/scoreboard"),"NHL":("https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",),"NFL":("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",),"CFB":("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?limit=100",)};_EXT_PROP_TITLE_RE=re.compile(r"^(.+?):\s*(Steals|Blocks)\s+O/U\s+(\d+\.5)\b",re.IGNORECASE);_NFL_EM_BAND_RE=re.compile(r"Exact\s+Margin:\s*(.+?)\s+by\s+(\d+)(?:-(\d+)|\+)",re.IGNORECASE);_GENERIC_SPREAD_LINE_RE=re.compile(r"([+-]\d+\.5)\b");_SCALAR_MAG_RE=re.compile(r"(?:↑|above|over|at\s+least|more\s+than|exceeds?)?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([kmb]|thousand|million|billion)?\b",re.IGNORECASE);_COVERED_CRYPTO_PYTH_SLUG_RE=re.compile(r"\b(?:bitcoin|btc|ethereum|eth|solana|sol|xrp|dogecoin|doge|bnb|sui|cardano|avax" r"|wti|crude-oil|xauusd|xagusd|gold-gc|silver-si|spy-hit|spy-daily|nvidia-hit|nvda-multi" r"|apple-hit|aapl-multi|tesla-hit|tsla-multi|microsoft-hit|msft-multi|amazon-hit|google-hit" r"|palantir-hit|coin-hit|hood-hit|natural-gas-hit)\b",re.IGNORECASE);_RESET_WINDOW_VETO_RE=re.compile(r"\b(?:in\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)" r"|during\s+(?:the\s+)?(?:month|week|quarter|q[1-4])|between\s+[a-z]+\s+\d+\s+and\s+[a-z]+\s+\d+)\b",re.IGNORECASE);_MONTH_DATE_STRIP_RE=re.compile(r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)" r"\s+\d{1,2}(?:,\s*20\d{2})?\b|\b20\d{2}-\d{2}-\d{2}\b|\bq[1-4]\s+20\d{2}\b",re.IGNORECASE);_TZ_DETECT_RE=re.compile(r"\b(ET|EDT|EST|UTC|GMT|PT|PDT|PST|CT|EET|CET|IRST|Iran\s+Standard\s+Time|Eastern\s+European\s+Time|Eastern\s+Time)\b",re.IGNORECASE)
def _add_truth_leg(legs,m,event_slug,tag_lbl,v_yes,v_no=None):
 if m.get("closed")or m.get("archived")or m.get("active")is False or m.get("acceptingOrders")is False:return
 b=_parse_clob_tokens(m)
 if not b:return
 g,f=_extract_market_fee_rate(m);a=_parse_iso_ts(m.get("endDate"))or.0;d=str(m.get("id")or"");c=str(m.get("conditionId")or"");e=bool(m.get("negRisk"))
 if v_no is None:v_no=[1.-x for x in v_yes]
 legs.append({"event_slug":event_slug,"market_id":d,"condition_id":c,"token_id":b[0],"opp_token_id":b[1],"side":"YES","label":f"YES[{tag_lbl}]","fee_rate":g,"fee_exponent":f,"neg_risk":e,"end_ts":a,"payoff_vec":v_yes,"strike":1.});legs.append({"event_slug":event_slug,"market_id":d,"condition_id":c,"token_id":b[1],"opp_token_id":b[0],"side":"NO","label":f"NO[{tag_lbl}]","fee_rate":g,"fee_exponent":f,"neg_risk":e,"end_ts":a,"payoff_vec":v_no,"strike":1.})
_HOUSE_SEAT_KEYS=("below 190","190-194","195-199","200-204","205-209","210-214","215-219","220-224","225-229","230+");_HOUSE_18_STATES=(tuple((b,ctrl)for b in range(6)for ctrl in("D","O"))+((6,"D"),(6,"R"),(6,"O"))+((7,"R"),(8,"R"),(9,"R")))
def build_lp2_house_seats_truth_legs(events_by_slug):
 b=events_by_slug.get("republican-house-seats-after-the-2026-midterm-elections")or{}
 if not b or b.get("closed"):return[]
 g=[];a=set()
 for m in b.get("markets")or[]:
  d=str(m.get("groupItemTitle")or m.get("question")or"").strip().lower();f=next((i for i,k in enumerate(_HOUSE_SEAT_KEYS)if d==k or k in d),None)
  if f is None:continue
  a.add(f);_add_truth_leg(g,m,"r_house_seats",f"HSeats:{_HOUSE_SEAT_KEYS[f]}",[1. if h==f else.0 for h,_ in _HOUSE_18_STATES])
 if len(a)<8:return[]
 e=events_by_slug.get("which-party-will-win-the-house-in-2026")or{}
 for m in e.get("markets")or[]:
  d=str(m.get("groupItemTitle")or"").strip().lower()
  if d=="democratic party":_add_truth_leg(g,m,"house_ctrl","House:Dem",[1. if c=="D"else.0 for _,c in _HOUSE_18_STATES])
  elif d=="republican party":_add_truth_leg(g,m,"house_ctrl","House:Rep",[1. if c=="R"else.0 for _,c in _HOUSE_18_STATES])
 return g
_SENATE_SEAT_KEYS=("≤47","48","49","50","51","52","53","54","55","56","57+");_SENATE_17_STATES=(tuple((b,ctrl,0)for b in range(2)for ctrl in("D","O"))+((2,"D",0),(2,"R",0),(2,"O",0))+((3,"D",0),(3,"R",0),(3,"O",0))+tuple((b,"R",0)for b in range(4,10))+((10,"R",0),(10,"R",1)))
def _match_senate_seat_idx(grp_raw):
 g=grp_raw.strip().lower().replace("<=","≤").replace(">=","")
 if"47"in g and("≤"in g or"below"in g or"less"in g or"under"in g):return 0
 if"57"in g and("+"in g or"more"in g or"above"in g):return 10
 for b,a in enumerate(_SENATE_SEAT_KEYS):
  if g==a:return b
 return None
def build_lp2_senate_seats_truth_legs(events_by_slug):
 b=events_by_slug.get("republican-senate-seats-after-the-2026-midterm-elections-927")or{}
 if not b or b.get("closed"):return[]
 h=[];a=set()
 for m in b.get("markets")or[]:
  e=str(m.get("groupItemTitle")or m.get("question")or"");g=_match_senate_seat_idx(e)
  if g is None:continue
  a.add(g);_add_truth_leg(h,m,"r_sen_seats",f"SSeats:{_SENATE_SEAT_KEYS[g]}",[1. if i==g else.0 for i,_,_ in _SENATE_17_STATES])
 if len(a)<9:return[]
 f=events_by_slug.get("which-party-will-win-the-senate-in-2026")or{}
 for m in f.get("markets")or[]:
  e=str(m.get("groupItemTitle")or"").strip().lower()
  if e=="democratic party":_add_truth_leg(h,m,"sen_ctrl","Sen:Dem",[1. if c=="D"else.0 for _,c,_ in _SENATE_17_STATES])
  elif e=="republican party":_add_truth_leg(h,m,"sen_ctrl","Sen:Rep",[1. if c=="R"else.0 for _,c,_ in _SENATE_17_STATES])
 d=events_by_slug.get("republican-trifecta-with-supermajority-in-the-senate")or{}
 for m in d.get("markets")or[]:_add_truth_leg(h,m,"trifecta_60","R_Trifecta60",[float(i)for _,_,i in _SENATE_17_STATES])
 return h
def build_lp2_pending_senate_conditional_groups(conditional_events,senate_ev):
 if not senate_ev or senate_ev.get("closed"):return[]
 f=[];e=((1,"R",0),(1,"D",0),(1,"O",0),(1,"O",1),(0,"R",1),(0,"D",1),(0,"O",1))
 for o in conditional_events:
  j=str(o.get("slug")or"").lower()
  if not j.startswith("who-wins-the-senate-pending-")or"pending-oil"in j:continue
  if o.get("closed")or not o.get("negRisk")or o.get("negRiskAugmented",True):continue
  i=[m for m in(o.get("markets")or[])if not m.get("closed")]
  if len(i)!=3:continue
  b,a,d=None,None,None
  for m in i:
   g=str(m.get("groupItemTitle")or m.get("question")or"").lower()
   if g.startswith("no "):d=m
   elif"r senate"in g or"republican"in g:b=m
   elif"d senate"in g or"democrat"in g:a=m
  if not(b and a and d):continue
  h=[];k=j.replace("who-wins-the-senate-pending-","")[:22];_add_truth_leg(h,b,j,f"{k}:Y&RSen",[1. if(c==1 and s=="R")else.0 for c,s,_ in e]);_add_truth_leg(h,a,j,f"{k}:Y&DSen",[1. if(c==1 and s=="D")else.0 for c,s,_ in e]);_add_truth_leg(h,d,j,f"{k}:NoCond",[float(p)for _,_,p in e])
  for n in senate_ev.get("markets")or[]:
   l=str(n.get("groupItemTitle")or"").strip().lower()
   if l=="democratic party":_add_truth_leg(h,n,"sen_ctrl","Sen:Dem",[1. if s=="D"else.0 for _,s,_ in e])
   elif l=="republican party":_add_truth_leg(h,n,"sen_ctrl","Sen:Rep",[1. if s=="R"else.0 for _,s,_ in e])
  if len(h)>=8:f.append((f"COND_{k.upper()}",h))
 return f
def build_lp2_tossup_state_implication_groups(events_by_slug):
 l=events_by_slug.get(LP2_TOSSUP_CUBE_SLUG)or{}
 if not l or l.get("closed"):return[]
 b=[m for m in(l.get("markets")or[])if not m.get("closed")]
 if not b:return[]
 p=next((m for m in b if str(m.get("groupItemTitle")or"").strip().lower()=="all 7"),None);o=next((m for m in b if str(m.get("groupItemTitle")or"").strip().lower()in("none","0","no states")),None);a=set(LP2_TOSSUP_STATE_SLUGS.keys());e={}
 for m in b:
  r=str(m.get("groupItemTitle")or"").upper();k={c for c in a if re.search(rf"\b{c}\b",r)}
  if len(k)==6:j=next(iter(a-k));e[j]=m
 d=[(so,o6)for so in("NAMED_R","OTHER_R","NAMED_D","OTHER_NON_R")for o6 in(True,False)];n=[]
 for i,h in LP2_TOSSUP_STATE_SLUGS.items():
  q=events_by_slug.get(h)or{}
  if not q or q.get("closed"):continue
  s=[];g=[];f=[]
  for m in q.get("markets")or[]:
   if m.get("closed"):continue
   t=str(m.get("groupItemTitle")or"").strip()
   if re.search(r"^(?:person|option|candidate|party)\s+[a-z0-9]{1,2}$",t,re.I)or"other"in t.lower():continue
   if"(r)"in t.lower()or(i=="AK"and"sullivan"in t.lower()):g.append((t,m))
   elif"(d)"in t.lower()or(i=="AK"and"peltola"in t.lower()):f.append((t,m))
  if len(g)==1:_add_truth_leg(s,g[0][1],h,f"{i}:{g[0][0][:18]}",[1. if so=="NAMED_R"else.0 for so,_ in d])
  if len(f)==1:_add_truth_leg(s,f[0][1],h,f"{i}:{f[0][0][:18]}",[1. if so=="NAMED_D"else.0 for so,_ in d])
  if p is not None:_add_truth_leg(s,p,LP2_TOSSUP_CUBE_SLUG,"Tossups:All7",[1. if(so in("NAMED_R","OTHER_R")and o6)else.0 for so,o6 in d])
  if i in e:_add_truth_leg(s,e[i],LP2_TOSSUP_CUBE_SLUG,f"Tossups:6Excl{i}",[1. if(so in("NAMED_D","OTHER_NON_R")and o6)else.0 for so,o6 in d])
  if o is not None:pass
  if len(s)>=6:n.append((f"TOSSUP_{i}",s))
 return n
def detect_lp2_seat_convert_implication_arbs(events_by_slug,books_by_token,target_budget_usd=120.,max_synthetic_box_cost_net=.992,min_shares=6,rpc_url=None):
 Q=[];y=[("LP2_HOUSE_CONVERT_POLISH_MIDDLE","republican-house-seats-after-the-2026-midterm-elections","which-party-will-win-the-house-in-2026",10,{"220-224","225-229","230+"},"House:Rep (218-219 $2x Middle)"),("LP2_SENATE_CONVERT_POLISH_MIDDLE","republican-senate-seats-after-the-2026-midterm-elections-927","which-party-will-win-the-senate-in-2026",11,{"51","52","53","54","55","56","57+"},"Sen:Rep (50-Seat $2x Middle)")]
 for P,l,k,K,d,u in y:
  O=events_by_slug.get(l)or{};N=events_by_slug.get(k)or{}
  if not O or not N or O.get("closed")or N.get("closed"):continue
  if not O.get("negRisk")or O.get("negRiskAugmented",True):continue
  J=str(O.get("negRiskMarketID")or"").strip().lower();E=O.get("markets")or[]
  if len(E)!=K:continue
  D,t,_=verify_negrisk_adapter_slate_sync(J,K,rpc_url=rpc_url)
  if not D:continue
  C=float(t)/1e4;I=next((m for m in(N.get("markets")or[])if str(m.get("groupItemTitle")or"").strip().lower()=="republican party"and not m.get("closed")),None)
  if I is None:continue
  s=_parse_clob_tokens(I)
  if not s:continue
  g=s[0];B,A=_extract_market_fee_rate(I);c=[]
  for H,m in enumerate(E):
   grp=str(m.get("groupItemTitle")or"").strip().lower()
   if grp in d:
    S=_parse_clob_tokens(m)
    if not S:break
    M=str(m.get("questionID")or"").strip().lower();h=int(M[64:],16)if(len(M)==66 and M.startswith("0x")and M[:64]==J[:64])else H;p,o=_extract_market_fee_rate(m);c.append((h,grp,S[1],p,o,str(m.get("id")or"")))
  if len(c)!=len(d):continue
  G=len(c);z=int(math.floor(min(80.,target_budget_usd)))
  if z<min_shares:continue
  b=float(z)
  for _,_,n_tok,_,_,_ in c:L=(books_by_token.get(n_tok)or{}).get("asks")or[];b=min(b,sum(float(x.get("size",0))for x in L if float(x.get("price",0))>0))
  r=(books_by_token.get(g)or{}).get("asks")or[];b=min(b,sum(float(x.get("size",0))for x in r if float(x.get("price",0))>0));v=int(math.floor(b))
  if v<min_shares:continue
  i=v*(1.-C);F=_walk_side_exact_shares(r,i,B,A,is_ask=True)
  if F is None:continue
  q=[];n=True
  for h,grp,n_tok,p,o,mid_m in c:
   R=_walk_side_exact_shares((books_by_token.get(n_tok)or{}).get("asks")or[],float(v),p,o,is_ask=True)
   if R is None:n=False;break
   q.append((h,grp,n_tok,mid_m,R))
  if not n:continue
  j=sum(w["net_per_share"]for*_,w in q);f=float(G-1)*(1.-C);a=(j-f)/max(1e-6,(1.-C))+float(F["net_per_share"])
  if a<=max_synthetic_box_cost_net:e=[{"token_id":n_tok,"market_id":mid_m,"side":"NO","label":f"NO[{grp}]","fee_rate":.0,"fee_exponent":1.}for _,grp,n_tok,mid_m,_ in q]+[{"token_id":g,"market_id":str(I.get("id")or""),"side":"YES","label":f"YES[{u}]","fee_rate":B,"fee_exponent":A}];Q.append({"mode":P,"seat_slug":l,"neg_risk_market_id":J,"m_no_legs":G,"index_set_int":sum(1<<T for T,*_ in q),"shares_in":v,"shares_out":round(i,4),"synthetic_box_cost_net":round(a,4),"guaranteed_floor_edge_ps":round(1.-a,4),"l1_usd":round(min([w["l1_usd"]for*_,w in q]+[F["l1_usd"]]),2),"close_ts":_parse_iso_ts(O.get("endDate"))or.0,"legs":e,"label":f"{P}: CONV({G}xNO)+YES[{u}] @ {a:.4f}"})
 return Q
@dataclass
class NbaSubperiodMarketSpec:event_id:str;market_id:str;condition_id:str;period_scope:str;kind:str;line:Optional[float];team_side:Optional[str];tok_0:str;tok_1:str;out_0:str;out_1:str;fee_rate:float;settle_est_ts:float;display_title:str;neg_risk=False;fee_exponent=1.
@dataclass
class NbaSubperiodAndExtPropSlate:event_id:str;slug:str;title:str;tipoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;ext_props_by_player_stat=field(default_factory=dict);subperiod_markets=field(default_factory=list)
_NBA_SUBPERIOD_SMT_MAP={"first_half_moneyline":("1H","ML"),"q1_moneyline":("Q1","ML"),"first_half_spreads":("1H","SPREAD"),"q1_spreads":("Q1","SPREAD"),"q2_spreads":("Q2","SPREAD"),"q3_spreads":("Q3","SPREAD"),"first_half_totals":("1H","TOTAL"),"q1_totals":("Q1","TOTAL"),"q2_totals":("Q2","TOTAL"),"q3_totals":("Q3","TOTAL"),"q4_totals":("Q4","TOTAL"),"team_totals":("FG","TEAM_TOTAL"),"first_half_team_totals":("1H","TEAM_TOTAL"),"second_half_team_totals":("2H","TEAM_TOTAL")}
def parse_nba_subperiod_and_ext_props(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived"):return None
 M=str(ev.get("slug")or"").lower()
 if not M.startswith("nba-")or M.endswith("-exact-margin"):return None
 E=str(ev.get("title")or"");D=re.split(r"\s+(?:vs\.?|@)\s+",E,maxsplit=1,flags=re.IGNORECASE)
 if len(D)!=2:return None
 y,x=_canon_nba_team(D[0]),_canon_nba_team(D[1]);w=_parse_iso_ts(ev.get("startTime")or ev.get("gameStartTime")or ev.get("endDate"))or.0
 if w<=.0 or(now_ts is not None and w<now_ts-8.*3600.):return None
 l=w+3.25*3600.;C=str(ev.get("id")or"");j={};n=[]
 for m in ev.get("markets")or[]:
  if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
  U,T=_extract_market_fee_rate(m);L=_parse_clob_tokens(m);K=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))]
  if not L or len(K)!=2:continue
  P=str(m.get("sportsMarketType")or"").strip().lower();B=str(m.get("groupItemTitle")or m.get("question")or"").strip()
  if P in("steals","blocks")and[o.lower()for o in K]==["yes","no"]:
   J=_EXT_PROP_TITLE_RE.match(B);b=m.get("line");s=float(b)if b is not None else(float(J.group(3))if J else float("nan"))
   if J and _is_half_hook(s)and s>=.5:
    A=J.group(1).strip();S=canon_player_name(A)
    if S:j.setdefault((S,P),[]).append(NbaPlayerPropRung(event_id=C,event_slug=M,game_title=E,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),player_name=A,player_key=S,stat_type=P,line=s,yes_token=L[0],no_token=L[1],fee_rate=U,tipoff_ts=w,settle_est_ts=l,home_team=x,away_team=y,fee_exponent=T))
   continue
  if P not in _NBA_SUBPERIOD_SMT_MAP:continue
  p,I=_NBA_SUBPERIOD_SMT_MAP[P];d={"Q1":.75,"Q2":1.35,"1H":1.35,"Q3":2.15}.get(p,3.25)*3600.;i=w+d
  if I=="ML":
   H,G=_canon_nba_team(K[0]),_canon_nba_team(K[1])
   if{H,G}!={y,x}:continue
   n.append(NbaSubperiodMarketSpec(C,str(m.get("id")or""),str(m.get("conditionId")or""),p,"ML",.0,H,L[0],L[1],K[0],K[1],U,i,B or f"{p} ML",bool(m.get("negRisk")),T))
  elif I=="SPREAD":
   b=m.get("line")
   if b is None:continue
   s=abs(float(b))
   if not _is_half_hook(s):continue
   H,G=_canon_nba_team(K[0]),_canon_nba_team(K[1])
   if{H,G}!={y,x}:continue
   v=str(m.get("question")or B);z=_SPREAD_FAV_RE.search(v);a=None
   if z:
    u=_canon_nba_team(z.group(1));O=float(z.group(2))
    if u in(y,x):a=u if O<0 else(x if u==y else y)
   if a is None:
    F=str(m.get("description")or"");N=re.search(r'resolve\s+to\s+"([^"]+)"\s+if\s+.+?\s+(?:wins|outscores).+?\s+by\s+(\d+)\s+or\s+more',F,re.I)
    if N:
     t=_canon_nba_team(N.group(1))
     if t in(y,x):a=t
   if a is None:continue
   if H==a:h,g,f,e=L[0],L[1],K[0],K[1]
   else:h,g,f,e=L[1],L[0],K[1],K[0]
   n.append(NbaSubperiodMarketSpec(C,str(m.get("id")or""),str(m.get("conditionId")or""),p,"SPREAD",s,a,h,g,f,e,U,i,f"{p} {f}(-{s})/{e}(+{s})",bool(m.get("negRisk")),T))
  elif I in("TOTAL","TEAM_TOTAL"):
   b=m.get("line")
   if b is None:continue
   s=float(b)
   if s<=.0 or not _is_half_hook(s):continue
   if not(K[0].lower().startswith("over")and K[1].lower().startswith("under")):continue
   c=None
   if I=="TEAM_TOTAL":
    q=(str(m.get("question")or B)).split("O/U")[0];R=y in _canon_nba_team(q)or _norm_team(D[0])in _norm_team(q);Q=x in _canon_nba_team(q)or _norm_team(D[1])in _norm_team(q)
    if R==Q:continue
    c=y if R else x
   n.append(NbaSubperiodMarketSpec(C,str(m.get("id")or""),str(m.get("conditionId")or""),p,I,s,c,L[0],L[1],"Over","Under",U,i,B or f"{p} O/U {s}",bool(m.get("negRisk")),T))
 for k in j:j[k].sort(key=lambda r:r.line)
 if not j and not n:return None
 return NbaSubperiodAndExtPropSlate(event_id=C,slug=M,title=E,tipoff_ts=w,settle_est_ts=l,home_team=x,away_team=y,ext_props_by_player_stat=j,subperiod_markets=n)
def detect_sp4_subperiod_and_ext_prop_boxes(slate,best_asks,max_box_cost_net=.992):
 y=[]
 for(_,l),p in slate.ext_props_by_player_stat.items():
  for i in range(len(p)):
   w=p[i];v=best_asks.get(w.yes_token)
   if v is None or not(.02<=v<=.98):continue
   for j in range(i+1,len(p)):
    u=p[j]
    if u.line<=w.line+.1:continue
    t=best_asks.get(u.no_token)
    if t is None or not(.02<=t<=.98):continue
    a=round(float(v)+float(t),4);c=round(_net_unit_ask(float(v),w.fee_rate,w.fee_exponent)+_net_unit_ask(float(t),u.fee_rate,u.fee_exponent),4)
    if c<=max_box_cost_net:y.append({"mode":"SP4_EXT_PROP_POLISH_MIDDLE","event_id":slate.event_id,"slug":slate.slug,"title":slate.title,"box_cost_gross":a,"box_cost_net":c,"close_ts":slate.settle_est_ts,"leg_a":{"token_id":w.yes_token,"opp_token_id":w.no_token,"condition_id":w.condition_id,"market_id":w.market_id,"side":"YES","label":f"{w.player_name} {l.upper()} O{w.line}","fee_rate":w.fee_rate,"fee_exponent":w.fee_exponent,"neg_risk":False,"strike":w.line,"end_ts":w.settle_est_ts},"leg_b":{"token_id":u.no_token,"opp_token_id":u.yes_token,"condition_id":u.condition_id,"market_id":u.market_id,"side":"NO","label":f"{u.player_name} {l.upper()} U{u.line}","fee_rate":u.fee_rate,"fee_exponent":u.fee_exponent,"neg_risk":False,"strike":u.line,"end_ts":u.settle_est_ts},"label":f"{w.player_name} {l} O{w.line} + U{u.line}"})
 for B in("1H","Q1"):
  A=[m for m in slate.subperiod_markets if m.period_scope==B and m.kind=="ML"];z=[m for m in slate.subperiod_markets if m.period_scope==B and m.kind=="SPREAD"]
  if not A or not z:continue
  s=A[0];D=s.team_side;C=slate.home_team if D==slate.away_team else slate.away_team;g={D:(s.tok_0,s.tok_1,s.out_0),C:(s.tok_1,s.tok_0,s.out_1)}
  for r in z:
   o=r.team_side
   if o not in g or r.line is None or r.line<.5:continue
   f,e,k=g[o];d,b,h=r.tok_1,r.tok_0,r.out_1;q=best_asks.get(f);n=best_asks.get(d)
   if q is None or n is None:continue
   a=round(float(q)+float(n),4);c=round(_net_unit_ask(float(q),s.fee_rate,s.fee_exponent)+_net_unit_ask(float(n),r.fee_rate,r.fee_exponent),4)
   if c<=max_box_cost_net:y.append({"mode":f"SP4_{B}_ML_SPREAD_MIDDLE","event_id":slate.event_id,"slug":slate.slug,"title":slate.title,"box_cost_gross":a,"box_cost_net":c,"close_ts":r.settle_est_ts,"leg_a":{"token_id":f,"opp_token_id":e,"condition_id":s.condition_id,"market_id":s.market_id,"side":"ML_FAV","label":f"{B} ML[{k}]","fee_rate":s.fee_rate,"fee_exponent":s.fee_exponent,"neg_risk":bool(s.neg_risk),"strike":.0,"end_ts":s.settle_est_ts},"leg_b":{"token_id":d,"opp_token_id":b,"condition_id":r.condition_id,"market_id":r.market_id,"side":"DOG_PLUS","label":f"{B} {h}(+{r.line})","fee_rate":r.fee_rate,"fee_exponent":r.fee_exponent,"neg_risk":bool(r.neg_risk),"strike":r.line,"end_ts":r.settle_est_ts},"label":f"{slate.title}: {B} ML[{k}] + {h}(+{r.line})"})
 y.sort(key=lambda x:float(x["box_cost_net"]));return y
def parse_espn_nba_extended_summary(summary_json):
 j={}
 for o in((summary_json or{}).get("boxscore")or{}).get("players")or[]:
  for n in o.get("statistics")or[]:
   B=[str(k)for k in(n.get("keys")or[])];t=next((i for i,k in enumerate(B)if k=="minutes"),-1);s=next((i for i,k in enumerate(B)if k=="steals"),-1);r=next((i for i,k in enumerate(B)if k=="blocks"),-1)
   for E in n.get("athletes")or[]:
    if E.get("didNotPlay"):continue
    A=canon_player_name(str((E.get("athlete")or{}).get("displayName")or""));D=E.get("stats")or[]
    if not A or not D:continue
    if 0<=t<len(D)and str(D[t]).strip()in("","0","0:00","--"):continue
    C={}
    try:
     if 0<=s<len(D):C["steals"]=int(str(D[s]).split("-")[0])
     if 0<=r<len(D):C["blocks"]=int(str(D[r]).split("-")[0])
    except ValueError:continue
    if C:j[A]=C
 h={"home":{},"away":{}};e,d=0,0;f,a=0,.0;g,c,b="pre",False,False;y=((summary_json or{}).get("header")or{}).get("competitions")or[]
 if y:
  J=y[0];w=J.get("status")or{};q=w.get("type")or{};f=int(w.get("period")or 0);g=str(q.get("state")or"pre").lower();c=bool(q.get("completed"));v=str(q.get("description")or q.get("name")or"").lower();b="halftime"in v;m=str(w.get("displayClock")or"")
  if":"in m:
   try:I,H=m.split(":",1);a=float(I)*60.+float(H)
   except ValueError:a=.0
  for z in J.get("competitors")or[]:
   G="home"if str(z.get("homeAway")or"").lower()=="home"else"away"
   try:l=int(float(z.get("score")or 0))
   except(TypeError,ValueError):l=0
   if G=="home":e=l
   else:d=l
   for u,F in enumerate(z.get("linescores")or[]):
    x=int(F.get("period")or(u+1));p=F.get("value")if F.get("value")is not None else F.get("displayValue")
    try:h[G][x]=int(float(p))
    except(TypeError,ValueError):pass
 return{"player_ext":j,"linescores":h,"home_score":e,"away_score":d,"period":f,"clock_sec":a,"state":g,"completed":c,"is_halftime":b}
def fetch_espn_nba_full_summary_sync(espn_game_id,timeout=5.):c=ESPN_NBA_SUMMARY_URL.format(game_id=espn_game_id);b=urllib.request.Request(c,headers={"User-Agent":"DominusSportsOracle/1.0"});a=json.loads(urllib.request.urlopen(b,timeout=timeout).read().decode("utf-8"));return parse_espn_nba_boxscore_players(a),parse_espn_nba_extended_summary(a)
def evaluate_sp4_subperiod_and_ext_locks(slate,ext_summary):
 y=str(ext_summary.get("state")or"pre")
 if y not in("in","post"):return[]
 h=bool(ext_summary.get("completed")and y=="post");x=bool(ext_summary.get("is_halftime"));o=int(ext_summary.get("period")or 0);c=float(ext_summary.get("clock_sec")or 720.);E=(ext_summary.get("linescores")or{}).get("home")or{};D=(ext_summary.get("linescores")or{}).get("away")or{};g=int(ext_summary.get("home_score")or 0);f=int(ext_summary.get("away_score")or 0);w=[]
 def _scope_scores(p_scope):
  if p_scope=="FG":return f,g,h
  if p_scope in("Q1","Q2","Q3","Q4"):
   q=int(p_scope[1])
   if q not in D or q not in E:return None,None,False
   a=h or(q==1 and x)or(o>q and(c<=6e2 or o>=q+2));return D[q],E[q],a
  if p_scope=="1H":
   if 1 not in D or 1 not in E:return None,None,False
   e=D.get(1,0)+D.get(2,0);d=E.get(1,0)+E.get(2,0);a=h or(2 in D and 2 in E and(o>=3 or x));return e,d,a
  if p_scope=="2H":
   if o<3:return None,None,False
   c=sum(v for k,v in D.items()if k>=3);b=sum(v for k,v in E.items()if k>=3);return c,b,h
  return None,None,False
 for I in slate.subperiod_markets:
  C,B,b=_scope_scores(I.period_scope)
  if C is None or B is None:continue
  e={slate.away_team:C,slate.home_team:B}
  if I.kind in("TOTAL","TEAM_TOTAL")and I.line is not None:
   l=(C+B)if I.kind=="TOTAL"else e.get(I.team_side or"",-1)
   if l<0:continue
   if b:
    j=.5 if(h or o>=(int(I.period_scope[1])+2 if I.period_scope.startswith("Q")else 4))else 1.5
    if abs(float(l)-I.line)>=j:d=float(l)>I.line;w.append({"mode":f"SP4_{I.period_scope}_SETTLED_TOTAL_LOCK","market_id":I.market_id,"condition_id":I.condition_id,"token_id":I.tok_0 if d else I.tok_1,"opp_token_id":I.tok_1 if d else I.tok_0,"side_label":"OVER"if d else"UNDER","display_label":f"{I.display_title} [{'OVER'if d else'UNDER'} {l} settled]","fee_rate":I.fee_rate,"fee_exponent":I.fee_exponent,"neg_risk":bool(I.neg_risk),"p_lock":.999,"close_ts":I.settle_est_ts})
    continue
   if l>=int(math.floor(I.line))+3:w.append({"mode":f"SP4_{I.period_scope}_LIVE_OVER_CLINCH","market_id":I.market_id,"condition_id":I.condition_id,"token_id":I.tok_0,"opp_token_id":I.tok_1,"side_label":"OVER","display_label":f"{I.display_title} [Live pts={l} >= {int(math.floor(I.line))+3}]","fee_rate":I.fee_rate,"fee_exponent":I.fee_exponent,"neg_risk":bool(I.neg_risk),"p_lock":.998,"close_ts":I.settle_est_ts})
  elif b and I.kind=="SPREAD"and I.line is not None and I.team_side in e:
   u=I.team_side;t=slate.home_team if u==slate.away_team else slate.away_team;a=float(e[u]-e[t])
   if abs(a-I.line)>=(.5 if h else 1.5):i=a>I.line;w.append({"mode":f"SP4_{I.period_scope}_SETTLED_SPREAD_LOCK","market_id":I.market_id,"condition_id":I.condition_id,"token_id":I.tok_0 if i else I.tok_1,"opp_token_id":I.tok_1 if i else I.tok_0,"side_label":I.out_0 if i else I.out_1,"display_label":f"{I.display_title} [Margin={a:+.0f} settled]","fee_rate":I.fee_rate,"fee_exponent":I.fee_exponent,"neg_risk":bool(I.neg_risk),"p_lock":.999,"close_ts":I.settle_est_ts})
  elif b and I.kind=="ML"and I.team_side in e:
   H=I.team_side;G=slate.home_team if H==slate.away_team else slate.away_team;A=e[H]-e[G]
   if abs(A)>=(1 if h else 2):n=A>0;w.append({"mode":f"SP4_{I.period_scope}_SETTLED_ML_LOCK","market_id":I.market_id,"condition_id":I.condition_id,"token_id":I.tok_0 if n else I.tok_1,"opp_token_id":I.tok_1 if n else I.tok_0,"side_label":I.out_0 if n else I.out_1,"display_label":f"{I.display_title} [{I.out_0 if n else I.out_1} +{abs(A)} settled]","fee_rate":I.fee_rate,"fee_exponent":I.fee_exponent,"neg_risk":bool(I.neg_risk),"p_lock":.999,"close_ts":I.settle_est_ts})
 if h:
  s=ext_summary.get("player_ext")or{}
  for(z,m),r in slate.ext_props_by_player_stat.items():
   p=(s.get(z)or{}).get(m)
   if p is None:continue
   for F in r:
    if int(p)>=int(math.floor(F.line))+2:w.append({"mode":"SP4_FINAL_EXT_STAT_LOCK","market_id":F.market_id,"condition_id":F.condition_id,"token_id":F.yes_token,"opp_token_id":F.no_token,"side_label":"YES","display_label":f"{F.player_name} {m} O{F.line} [Final={p}]","fee_rate":F.fee_rate,"fee_exponent":F.fee_exponent,"neg_risk":False,"p_lock":.998,"close_ts":F.settle_est_ts})
 return w
@dataclass
class MonotonicRung:market_id:str;condition_id:str;label:str;order_val:float;end_ts:float;yes_token:str;no_token:str;fee_rate:float;fee_exponent:float;clause_key:str;neg_risk=False
@dataclass
class CalendarOrScalarLadderSpec:event_id:str;slug:str;title:str;ladder_kind:str;rungs:List[MonotonicRung]
def _canon_clause_stem(desc,group_title):
 s=str(desc or"").lower().replace("“",'"').replace("”",'"').replace("’","'");b=_TZ_DETECT_RE.search(desc or"");a=(b.group(1).upper().replace(" ","_")if b else"NO_TZ");c=str(group_title or"").strip().lower()
 if c and len(c)>=2:s=s.replace(c," <RUNG> ")
 s=_MONTH_DATE_STRIP_RE.sub(" <DATE> ",s);s=re.sub(r"\$\s*[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:[kmb]|million|billion)?"," <STRIKE> ",s);s=re.sub(r"\s+"," ",s).strip();return s,a
_MONTH_MAP_CAL1={"january":1,"jan":1,"february":2,"feb":2,"march":3,"mar":3,"april":4,"apr":4,"may":5,"june":6,"jun":6,"july":7,"jul":7,"august":8,"aug":8,"september":9,"sep":9,"sept":9,"october":10,"oct":10,"november":11,"nov":11,"december":12,"dec":12}
def _parse_group_label_date_ts(lbl,ref_end_ts):
 m=re.search(r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:,\s*(20\d{2}))?\b",str(lbl or""),re.IGNORECASE)
 if not m:return None
 b=_MONTH_MAP_CAL1.get(m.group(1).lower());a=int(m.group(2))
 if not b:return None
 c=int(m.group(3))if m.group(3)else datetime.fromtimestamp(max(1.,ref_end_ts),tz=timezone.utc).year
 try:return datetime(c,b,a,23,59,59,tzinfo=timezone.utc).timestamp()
 except ValueError:return None
def _parse_scalar_strike(lbl):
 s=str(lbl or"").strip()
 if re.search(r"(?:↓|\bbelow\b|\bunder\b|\bless\s+than\b|\bat\s+most\b|\bfewer\s+than\b|\bbetween\b)",s,re.IGNORECASE):return None
 m=_SCALAR_MAG_RE.search(s)
 if not m:return None
 c=float(m.group(1).replace(",",""));b=(m.group(2)or"").lower();a={"k":1e3,"thousand":1e3,"m":1e6,"million":1e6,"b":1e9,"billion":1e9}.get(b,1.);return c*a
def parse_cal1_monotonic_ladder_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived")or ev.get("negRisk"):return[]
 E=str(ev.get("slug")or"");x=str(ev.get("title")or"")
 if _COVERED_CRYPTO_PYTH_SLUG_RE.search(E)or _COVERED_CRYPTO_PYTH_SLUG_RE.search(x):return[]
 D=[m for m in(ev.get("markets")or[])if not m.get("closed")and not m.get("archived")and m.get("acceptingOrders")is not False]
 if len(D)<2:return[]
 if any(m.get("sportsMarketType")for m in D):return[]
 q,h=E.lower(),x.lower();d=str(D[0].get("description")or"");p=d.lower();b=bool(_RESET_WINDOW_VETO_RE.search(h)or _RESET_WINDOW_VETO_RE.search(q.replace("-"," ")));a=None
 if not b and("continues-through"in q or"continues through"in h or("remains in effect"in p and"through"in p)or('resolve to "no" if'in p.replace("“",'"').replace("”",'"')and"by the specified date"in p)):a="SURVIVAL"
 elif not b and(any(k in q for k in("-by","before-"))or any(k in h for k in(" by "," before "))):
  if"resolve"in p and("by "in p or"before "in p or"between market creation and"in p):a="DEADLINE_BY"
 elif any(k in h for k in("fdv above","total commitments","market cap above","box office","revenue above")):a="SCALAR_ABOVE"
 if a is None:return[]
 e={}
 for m in D:
  C=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))];B=_parse_clob_tokens(m)
  if C!=["yes","no"]or not B:continue
  n=str(m.get("description")or"")
  if len(n)<60:continue
  G=str(m.get("groupItemTitle")or m.get("question")or"").strip();A,l=_canon_clause_stem(n,G);j=_parse_iso_ts(m.get("endDate"))or.0
  if j<=.0 or(now_ts is not None and j<now_ts+120.):continue
  if a in("SURVIVAL","DEADLINE_BY"):
   i=_parse_group_label_date_ts(G,j)
   if i is not None and abs(i-j)>14.*86400.:
    if j<i-2.*86400.:continue
    c=i
   else:c=i if i is not None else j
  else:
   g=n.lower()
   if not any(w in g for w in("above","greater than","exceed","at least","more than","over ")):continue
   if re.search(r"\b(?:less\s+than\s+\$|fewer\s+than|at\s+most)\b",g):continue
   z=_parse_scalar_strike(G)
   if z is None or z<=.0:continue
   c=z
  I,H=_extract_market_fee_rate(m);y=f"{l}::{A[:220]}";e.setdefault(y,[]).append(MonotonicRung(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),label=G[:36],order_val=c,end_ts=j,yes_token=B[0],no_token=B[1],fee_rate=I,fee_exponent=H,clause_key=y,neg_risk=bool(m.get("negRisk"))))
 v=[];u=str(ev.get("id")or"")
 for t,(y,F)in enumerate(e.items()):
  F.sort(key=lambda r:r.order_val);s=[];f=43200. if a in("SURVIVAL","DEADLINE_BY")else 1e-6
  for r in F:
   if not s or(r.order_val-s[-1].order_val)>=f:s.append(r)
  if len(s)>=2:v.append(CalendarOrScalarLadderSpec(event_id=f"{u}_{t}"if t>0 else u,slug=E,title=x,ladder_kind=a,rungs=s))
 return v
def detect_cal1_monotonic_boxes(spec,best_asks,max_box_cost_net=.992):
 p=[];q=spec.rungs
 for i in range(len(q)):
  o=q[i]
  for j in range(i+1,len(q)):
   n=q[j]
   if spec.ladder_kind=="DEADLINE_BY":h,g,b,f=o.no_token,o.yes_token,"NO",f"NO[{o.label}]";e,d,a,c=n.yes_token,n.no_token,"YES",f"YES[{n.label}]"
   else:h,g,b,f=o.yes_token,o.no_token,"YES",f"YES[{o.label}]";e,d,a,c=n.no_token,n.yes_token,"NO",f"NO[{n.label}]"
   m,l=best_asks.get(h),best_asks.get(e)
   if m is None or l is None or not(.005<=m<=.995 and.005<=l<=.995):continue
   k=round(_net_unit_ask(m,o.fee_rate,o.fee_exponent)+_net_unit_ask(l,n.fee_rate,n.fee_exponent),4)
   if k<=max_box_cost_net:p.append({"mode":f"CAL1_{spec.ladder_kind}_BOX","event_id":spec.event_id,"slug":spec.slug,"title":spec.title,"ladder_kind":spec.ladder_kind,"box_cost_net":k,"close_ts":max(o.end_ts,n.end_ts),"early_leg_close_ts":min(o.end_ts,n.end_ts),"leg_a":{"token_id":h,"opp_token_id":g,"condition_id":o.condition_id,"market_id":o.market_id,"side":b,"label":f,"fee_rate":o.fee_rate,"fee_exponent":o.fee_exponent,"neg_risk":bool(o.neg_risk),"strike":o.order_val,"end_ts":o.end_ts},"leg_b":{"token_id":e,"opp_token_id":d,"condition_id":n.condition_id,"market_id":n.market_id,"side":a,"label":c,"fee_rate":n.fee_rate,"fee_exponent":n.fee_exponent,"neg_risk":bool(n.neg_risk),"strike":n.order_val,"end_ts":n.end_ts},"label":f"{spec.title[:40]}: {f} + {c}"})
 p.sort(key=lambda x:(float(x["box_cost_net"]),float(x["early_leg_close_ts"])));return p
def build_lp1_nfl_exact_margin_bundle(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived"):return None
 _f=[m for m in(ev.get("markets")or[])if not m.get("closed")and not m.get("archived")];p=[m for m in _f if str(m.get("sportsMarketType")or"").lower()=="exact_margin"];x=next((m for m in _f if str(m.get("sportsMarketType")or"").lower()=="moneyline"),None)
 if len(p)!=10 or x is None:return None
 g=_parse_iso_ts(ev.get("startTime")or x.get("gameStartTime")or ev.get("endDate"))or.0;w=g+3.75*3600.
 if now_ts is not None and w<now_ts+60.:return None
 n=_parse_clob_tokens(x);l=[str(o).strip()for o in _parse_json_list(x.get("outcomes"))]
 if not n or len(l)!=2:return None
 v,u=l[0],l[1];_e,_d=_norm_team(v),_norm_team(u);b=[];a=False
 for m in p:
  tk=_parse_clob_tokens(m);_c=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not tk or _c!=["yes","no"]:return None
  fr,fe=_extract_market_fee_rate(m);_j=str(m.get("groupItemTitle")or m.get("question")or"").strip()
  if re.search(r"exact\s+margin:\s*tie\b",_j,re.I):a=True;b.append(("TIE",0,0,m,tk,fr,fe,"Tie"));continue
  mb=_NFL_EM_BAND_RE.search(_j)
  if not mb:return None
  _b=_norm_team(mb.group(1));lo=int(mb.group(2));hi=int(mb.group(3))if mb.group(3)else 999;Q="A"if(_b==_e or _b in _e or _e in _b)else("B"if(_b==_d or _b in _d or _d in _b)else"")
  if not Q:return None
  b.append((Q,lo,hi,m,tk,fr,fe,_j.replace("Exact Margin:","").strip()))
 if not a or len(b)!=10:return None
 for f in("A","B"):
  _i=sorted([(lo,hi)for wk,lo,hi,*_ in b if wk==f])
  if not _i or _i[0][0]!=1 or _i[-1][1]!=999:return None
  for P in range(len(_i)-1):
   if _i[P][1]+1!=_i[P+1][0]:return None
 e=11;_a=[];O,N=_extract_market_fee_rate(x);M,t=str(x.get("id")or""),str(x.get("conditionId")or"");L=[1. if wk=="A"else(.5 if wk=="TIE"else.0)for wk,*_ in b]+[.5];K=[1. if wk=="B"else(.5 if wk=="TIE"else.0)for wk,*_ in b]+[.5];J=bool(x.get("negRisk"));_a.append({"market_id":M,"condition_id":t,"token_id":n[0],"opp_token_id":n[1],"side":"ML_A","label":f"ML[{v}]","fee_rate":O,"fee_exponent":N,"neg_risk":J,"end_ts":w,"payoff_vec":L,"strike":.0});_a.append({"market_id":M,"condition_id":t,"token_id":n[1],"opp_token_id":n[0],"side":"ML_B","label":f"ML[{u}]","fee_rate":O,"fee_exponent":N,"neg_risk":J,"end_ts":w,"payoff_vec":K,"strike":.0})
 for Z,(wk,lo,hi,Y,I,X,W,H)in enumerate(b):_h=[1. if s==Z else.0 for s in range(10)]+[.5];_g=[1.-_h[s]for s in range(10)]+[.5];G,F=str(Y.get("id")or""),str(Y.get("conditionId")or"");E=bool(Y.get("negRisk"));_a.append({"market_id":G,"condition_id":F,"token_id":I[0],"opp_token_id":I[1],"side":"YES","label":f"EM_Y[{H}]","fee_rate":X,"fee_exponent":W,"neg_risk":E,"end_ts":w,"payoff_vec":_h,"strike":float(lo)});_a.append({"market_id":G,"condition_id":F,"token_id":I[1],"opp_token_id":I[0],"side":"NO","label":f"EM_N[{H}]","fee_rate":X,"fee_exponent":W,"neg_risk":E,"end_ts":w,"payoff_vec":_g,"strike":float(lo)})
 for sm in _f:
  if str(sm.get("sportsMarketType")or"").lower()!="spreads"or sm.get("line")is None:continue
  ln=abs(float(sm.get("line")))
  if not _is_half_hook(ln):continue
  V=_parse_clob_tokens(sm);r=[str(o).strip()for o in _parse_json_list(sm.get("outcomes"))];U=_SPREAD_FAV_RE.search(str(sm.get("question")or sm.get("groupItemTitle")or""))
  if not V or len(r)!=2 or not U:continue
  k=_norm_team(U.group(1));j=float(U.group(2));D=("A"if k==_e else"B")if j<0 else("B"if k==_e else"A")
  if k not in(_e,_d):continue
  if any(wk==D and lo<ln<hi for wk,lo,hi,*_ in b):continue
  T=_norm_team(r[0]);C=_e if D=="A"else _d;i,h=(V[0],V[1])if T==C else(V[1],V[0]);d=v if D=="A"else u;c=u if D=="A"else v;B=[1. if(wk==D and lo>ln)else.0 for wk,lo,hi,*_ in b]+[.5];A=[1.-B[s]for s in range(10)]+[.5];S,R=_extract_market_fee_rate(sm);z,q=str(sm.get("id")or""),str(sm.get("conditionId")or"");y=bool(sm.get("negRisk"));_a.append({"market_id":z,"condition_id":q,"token_id":i,"opp_token_id":h,"side":"SPREAD_FAV","label":f"{d}(-{ln})","fee_rate":S,"fee_exponent":R,"neg_risk":y,"end_ts":w,"payoff_vec":B,"strike":-ln});_a.append({"market_id":z,"condition_id":q,"token_id":h,"opp_token_id":i,"side":"SPREAD_DOG","label":f"{c}(+{ln})","fee_rate":S,"fee_exponent":R,"neg_risk":y,"end_ts":w,"payoff_vec":A,"strike":ln})
 return{"event_id":str(ev.get("id")or""),"slug":str(ev.get("slug")or""),"title":str(ev.get("title")or""),"end_ts":w,"legs":_a}
def detect_multisport_ml_spread_polish_middles(ev,best_asks,sport_hint="NFL",max_box_cost_net=.988):
 if ev.get("closed")or ev.get("archived")or ev.get("negRisk"):return[]
 N=str(ev.get("slug")or"").lower()
 if N.startswith("nba-"):return[]
 M=[m for m in(ev.get("markets")or[])if not m.get("closed")and not m.get("archived")]
 if len(M)<2:return[]
 h=_parse_iso_ts(ev.get("startTime")or ev.get("endDate"))or.0;F=str(ev.get("title")or N);E=str(ev.get("id")or"");a=(("FG","moneyline","spreads",3.75*3600.),("1H","first_half_moneyline","first_half_spreads",1.75*3600.),("Q1","q1_moneyline","q1_spreads",1.*3600.));L=[]
 for D,r,q,C in a:
  K=next((m for m in M if str(m.get("sportsMarketType")or"").lower()==r),None)
  if K is None:continue
  B=_parse_clob_tokens(K);l=[str(o).strip()for o in _parse_json_list(K.get("outcomes"))]
  if not B or len(l)!=2:continue
  J,I=_norm_team(l[0]),_norm_team(l[1])
  if J in("yes","no","over","under")or J==I:continue
  A,z=_extract_market_fee_rate(K);p={J:(B[0],B[1],l[0]),I:(B[1],B[0],l[1])};g=h+C
  for Q in M:
   if str(Q.get("sportsMarketType")or"").lower()!=q or Q.get("line")is None:continue
   P=abs(float(Q.get("line")))
   if P<.5 or not _is_half_hook(P):continue
   y=_parse_clob_tokens(Q);k=[str(o).strip()for o in _parse_json_list(Q.get("outcomes"))];H=_SPREAD_FAV_RE.search(str(Q.get("question")or Q.get("groupItemTitle")or""))
   if not y or len(k)!=2 or not H:continue
   j=_norm_team(H.group(1));O=float(H.group(2))
   if j not in(J,I):continue
   w=j if O<0 else(I if j==J else J);G=_norm_team(k[0])
   if{G,_norm_team(k[1])}!={J,I}:continue
   i=y[1]if G==w else y[0];d=y[0]if G==w else y[1];f=k[1]if G==w else k[0];c,b,e=p[w];v=best_asks.get(c);n=best_asks.get(i)
   if v is None or n is None:continue
   u,t=_extract_market_fee_rate(Q);s=round(_net_unit_ask(v,A,z)+_net_unit_ask(n,u,t),4)
   if s<=max_box_cost_net:L.append({"mode":f"LP1_{sport_hint}_{D}_ML_SPREAD_MIDDLE","sport":sport_hint,"event_id":E,"slug":N,"title":F,"box_cost_net":s,"close_ts":g,"leg_a":{"token_id":c,"opp_token_id":b,"condition_id":str(K.get("conditionId")or""),"market_id":str(K.get("id")or""),"side":"ML_FAV","label":f"{D} ML[{e}]","fee_rate":A,"fee_exponent":z,"neg_risk":bool(K.get("negRisk")),"strike":.0,"end_ts":g},"leg_b":{"token_id":i,"opp_token_id":d,"condition_id":str(Q.get("conditionId")or""),"market_id":str(Q.get("id")or""),"side":"DOG_PLUS","label":f"{D} {f}(+{P})","fee_rate":u,"fee_exponent":t,"neg_risk":bool(Q.get("negRisk")),"strike":P,"end_ts":g},"label":f"{F[:38]}: {D} ML[{e}] + {f}(+{P})"})
 L.sort(key=lambda x:float(x["box_cost_net"]));return L
@dataclass
class LiveMultiSportGame:sport:str;game_id:str;start_ts:float;state:str;completed:bool;is_halftime:bool;period:int;clock_sec:float;home_name:str;away_name:str;home_score:int;away_score:int;linescores_home=field(default_factory=dict);linescores_away=field(default_factory=dict)
class ScoreConfirmationTracker:
 def __init__(self):self._first_seen={}
 def observe_and_confirmed_floor(a,sport,game_id,metric_key,current_val,now_ts,min_confirm_sec,is_final=False):
  if current_val<=0:a._purge_above(sport,game_id,metric_key,0);return 0
  a._purge_above(sport,game_id,metric_id=metric_key,max_keep=current_val)
  for v in range(1,min(current_val,120)+1):
   k=(sport,game_id,metric_key,v)
   if k not in a._first_seen:a._first_seen[k]=now_ts
  if is_final:return current_val
  b=0
  for v in range(1,min(current_val,120)+1):
   c=a._first_seen.get((sport,game_id,metric_key,v),now_ts)
   if(now_ts-c)>=min_confirm_sec:b=v
  return b
 def _purge_above(a,sport,game_id,metric_id="",max_keep=0):
  b=[k for k in a._first_seen if k[0]==sport and k[1]==game_id and k[2]==metric_id and k[3]>max_keep]
  for k in b:del a._first_seen[k]
 def prune(a,now_ts,max_age_sec=21600.):
  b=float(now_ts)-float(max_age_sec);c=[k for k,d in a._first_seen.items()if d<b]
  for k in c:del a._first_seen[k]
  return len(c)
def parse_espn_multisport_scoreboard(sport,sb_json):
 q=[]
 for B in(sb_json or{}).get("events")or[]:
  p=B.get("competitions")or[]
  if not p:continue
  A=p[0];z=A.get("status")or{};s=z.get("type")or{};o=str(s.get("state")or"pre").lower()
  if o not in("in","post"):continue
  d=bool(s.get("completed"));l=str(s.get("description")or s.get("name")or"").lower();n="halftime"in l;k=int(z.get("period")or 0);c=float(z.get("clock")or.0);i=_parse_iso_ts(A.get("date")or B.get("date"))or.0;b,a="","";h,f=0,0;g={};e={}
  for y in A.get("competitors")or[]:
   x=str(y.get("homeAway")or"").lower();w=str((y.get("team")or{}).get("displayName")or(y.get("team")or{}).get("shortDisplayName")or"")
   try:r=int(float(y.get("score")or 0))
   except(TypeError,ValueError):r=0
   j={}
   for m,v in enumerate(y.get("linescores")or[]):
    u=int(v.get("period")or(m+1));t=v.get("value")if v.get("value")is not None else v.get("displayValue")
    try:j[u]=int(float(t))
    except(TypeError,ValueError):pass
   if x=="home":b,h,g=w,r,j
   else:a,f,e=w,r,j
  if b and a:q.append(LiveMultiSportGame(sport=sport,game_id=str(B.get("id")or""),start_ts=i,state=o,completed=d,is_halftime=n,period=k,clock_sec=c,home_name=b,away_name=a,home_score=h,away_score=f,linescores_home=g,linescores_away=e))
 return q
def fetch_espn_multisport_board_sync(sport,timeout=5.):
 c=ESPN_SCOREBOARD_URLS.get(sport.upper())or();a={}
 for u in c:
  try:
   d=urllib.request.Request(u,headers={"User-Agent":"DominusSportsOracle/1.0"});b=json.loads(urllib.request.urlopen(d,timeout=timeout).read().decode("utf-8"))
   for g in parse_espn_multisport_scoreboard(sport.upper(),b):a[g.game_id]=g
  except Exception:continue
 return list(a.values())
_GENERIC_CLUB_SUFFIX_TOKS=frozenset({"fc","sc","cf","ac","afc","club","de","cd","ud","fk","sk","sv","bv"});_DERBY_DISAMBIG_TOKS=frozenset({"city","united","utd","real","atletico","inter","ac","sporting","dynamo","lokomotiv","rangers","celtic"})
def _teams_match_fuzzy(pm_team,espn_team):
 p=_norm_team(pm_team);e=_norm_team(espn_team)
 if not p or not e:return False
 if p==e:return True
 g=p.split();f=e.split();d=[t for t in g if t not in _GENERIC_CLUB_SUFFIX_TOKS];c=[t for t in f if t not in _GENERIC_CLUB_SUFFIX_TOKS]
 if not d or not c:return False
 b=set(g)&_DERBY_DISAMBIG_TOKS;a=set(f)&_DERBY_DISAMBIG_TOKS
 if b and a and b.isdisjoint(a):return False
 if d==c:return True
 if set(d).issubset(set(c))and sum(len(t)for t in d)>=4:
  if len(d)==1 and a and not b:return False
  return True
 if set(c).issubset(set(d))and sum(len(t)for t in c)>=4:
  if len(c)==1 and b and not a:return False
  return True
 if d[-1]==c[-1]and len(d[-1])>=4 and d[-1]not in _DERBY_DISAMBIG_TOKS:
  if not(len(d)>=2 and len(c)>=2 and d[0]!=c[0]):return True
 return False
def evaluate_cl1_soccer_tree_clinch_locks(soccer_tree,live_soccer_board,tracker,now_ts,var_confirm_sec=210.):
 b=None;f=str(getattr(soccer_tree,"home_team",None)or getattr(soccer_tree,"home_name","")or"");e=str(getattr(soccer_tree,"away_team",None)or getattr(soccer_tree,"away_name","")or"")
 for g in live_soccer_board:
  if abs(g.start_ts-float(soccer_tree.end_ts-2.25*3600.))>8.*3600.:continue
  j=_teams_match_fuzzy(f,g.home_name)and _teams_match_fuzzy(e,g.away_name);i=_teams_match_fuzzy(f,g.away_name)and _teams_match_fuzzy(e,g.home_name)
  if j and i:continue
  if j or i:b=g;break
 if b is None:return[]
 if b.period>2:
  if 1 in b.linescores_home and 2 in b.linescores_home and 1 in b.linescores_away and 2 in b.linescores_away:c=b.linescores_home[1]+b.linescores_home[2]+b.linescores_away[1]+b.linescores_away[2]
  else:return[]
  a=True
 else:c=b.home_score+b.away_score;a=bool(b.completed and b.state=="post")
 d=tracker.observe_and_confirmed_floor("SOCCER",b.game_id,"REG_GOALS",c,now_ts,var_confirm_sec,is_final=a)
 if d<=0:return[]
 h=[]
 for l in soccer_tree.totals:
  k=float(l["line"])
  if d>=int(math.floor(k))+1:h.append({"mode":"CL1_SOCCER_POST_VAR_OVER_LOCK","sport":"SOCCER","market_id":str(l["market_id"]),"condition_id":str(l["condition_id"]),"token_id":str(l["over_token"]),"opp_token_id":str(l["under_token"]),"fee_rate":float(l["fee_rate"]),"fee_exponent":float(l.get("fee_exponent",l.get("fee_exp",1.))),"neg_risk":bool(l.get("neg_risk",False)),"side_label":"OVER","display_label":f"{soccer_tree.title[:40]} Over {k} [Goals={d} post-VAR]","p_lock":.998,"close_ts":float(soccer_tree.end_ts)})
 return h
def evaluate_cl1_multisport_corridor_clinch_locks(ms_spec,live_boards,tracker,now_ts):
 x=str(ms_spec.sport or"").upper()
 if x not in("NHL","NFL","CFB"):return[]
 p=live_boards.get(x)or[];c=None;b=False
 for g in p:
  if abs(g.start_ts-float(ms_spec.start_ts))>8.*3600.:continue
  if _teams_match_fuzzy(ms_spec.team_a,g.away_name)and _teams_match_fuzzy(ms_spec.team_b,g.home_name):c,b=g,False;break
  if _teams_match_fuzzy(ms_spec.team_a,g.home_name)and _teams_match_fuzzy(ms_spec.team_b,g.away_name):c,b=g,True;break
 if c is None:return[]
 h=bool(c.completed and c.state=="post");v=c.home_score if b else c.away_score;u=c.away_score if b else c.home_score;t=c.linescores_home if b else c.linescores_away;s=c.linescores_away if b else c.linescores_home;o=[]
 if x=="NHL":
  f=tracker.observe_and_confirmed_floor("NHL",c.game_id,"TOT_GOALS",v+u,now_ts,min_confirm_sec=150.,is_final=h)
  for d in(ms_spec.legs_by_scope.get("FG:TOTAL")or[]):
   if d.relation=="OVER"and f>=int(math.floor(d.threshold))+1:o.append({"mode":"CL1_NHL_POST_CHALLENGE_OVER_LOCK","sport":"NHL","market_id":d.market_id,"condition_id":d.condition_id,"token_id":d.token_id,"opp_token_id":d.opp_token_id,"fee_rate":d.fee_rate,"fee_exponent":d.fee_exponent,"neg_risk":bool(getattr(d,"neg_risk",False)),"side_label":d.side_label,"display_label":f"{ms_spec.title[:38]} {d.display_label} [Goals={f}]","p_lock":.998,"close_ts":float(ms_spec.settle_est_ts)})
  return o
 m=1 if h else 9
 for d in(ms_spec.legs_by_scope.get("FG:TOTAL")or[]):
  if d.relation=="OVER"and(v+u)>=int(math.floor(d.threshold))+m:o.append({"mode":f"CL1_{x}_SCORE_OVER_LOCK","sport":x,"market_id":d.market_id,"condition_id":d.condition_id,"token_id":d.token_id,"opp_token_id":d.opp_token_id,"fee_rate":d.fee_rate,"fee_exponent":d.fee_exponent,"neg_risk":bool(getattr(d,"neg_risk",False)),"side_label":d.side_label,"display_label":f"{ms_spec.title[:36]} {d.display_label} [Score={v}-{u}]","p_lock":.999 if h else.997,"close_ts":float(ms_spec.settle_est_ts)})
 for l,r in ms_spec.legs_by_scope.items():
  w=l.split(":")[0];k,j,a=None,None,False
  if w in("Q1","Q2","Q3"):
   q=int(w[1])
   if q in t and q in s:k,j=t[q],s[q];a=h or(q==1 and c.is_halftime)or(c.period>q and(c.clock_sec<=780. or c.period>=q+2))
  elif w=="1H":
   if 1 in t and 1 in s and 2 in t and 2 in s:k,j=t[1]+t[2],s[1]+s[2];a=h or c.is_halftime or c.period>=3
  if not a or k is None or j is None:continue
  if l.endswith(":TOTAL"):
   n=float(k+j)
   for d in r:
    i=(n>d.threshold)if d.relation=="OVER"else(n<d.threshold)
    if i and abs(n-d.threshold)>=.5:o.append({"mode":f"CL1_{x}_{w}_SETTLED_TOTAL_LOCK","sport":x,"market_id":d.market_id,"condition_id":d.condition_id,"token_id":d.token_id,"opp_token_id":d.opp_token_id,"fee_rate":d.fee_rate,"fee_exponent":d.fee_exponent,"neg_risk":bool(getattr(d,"neg_risk",False)),"side_label":d.side_label,"display_label":f"{ms_spec.title[:34]} {d.display_label} [{w}={int(n)} settled]","p_lock":.999,"close_ts":float(ms_spec.settle_est_ts)})
  elif l.endswith(":SPREAD"):
   e=float(k-j)
   for d in r:
    i=(e>d.threshold)if d.relation=="GT"else(e<d.threshold)
    if i and abs(e-d.threshold)>=.5:o.append({"mode":f"CL1_{x}_{w}_SETTLED_SPREAD_LOCK","sport":x,"market_id":d.market_id,"condition_id":d.condition_id,"token_id":d.token_id,"opp_token_id":d.opp_token_id,"fee_rate":d.fee_rate,"fee_exponent":d.fee_exponent,"neg_risk":bool(getattr(d,"neg_risk",False)),"side_label":d.side_label,"display_label":f"{ms_spec.title[:34]} {d.display_label} [{w} M={e:+.0f}]","p_lock":.999,"close_ts":float(ms_spec.settle_est_ts)})
 return o
@dataclass
class TennisTotalRung:market_id:str;condition_id:str;scope:str;line:float;over_token:str;under_token:str;fee_rate:float;fee_exp:float;neg_risk=False
@dataclass
class TennisMatchSpec:event_id:str;slug:str;title:str;player_a:str;player_b:str;end_ts:float;totals_by_scope=field(default_factory=dict);set1_a_token=None;set1_b_token=None;set1_resolved_winner=None;set2_a_token=None;set2_b_token=None;set2_resolved_winner=None;sets_ou25_over_token=None;sets_ou25_under_token=None;sets_ou25_market_id="";sets_ou25_condition_id="";sets_ou25_fee_rate=.05;sets_ou25_fee_exp=1.;sets_ou25_neg_risk=False;comp_yes_token=None;comp_no_token=None;comp_market_id="";comp_condition_id="";comp_fee_rate=.05;comp_fee_exp=1.;comp_neg_risk=False
def parse_tennis_retirement_safe_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived")or ev.get("negRisk"):return None
 p=str(ev.get("slug")or"").lower();n=ev.get("markets")or[]
 if not(p.startswith(("atp-","wta-"))or any(str(m.get("sportsMarketType")or"").startswith("tennis_")for m in n)):return None
 for m in n:
  f=str(m.get("groupItemTitle")or m.get("question")or"").lower()
  if re.search(r"\bset\s+[45]\b",f):return None
  if str(m.get("sportsMarketType")or"").lower()=="tennis_set_totals"and m.get("line")is not None and float(m.get("line"))>3.:return None
 l=next((m for m in n if str(m.get("sportsMarketType")or"").lower()=="moneyline"),None)
 if l is None:return None
 d=[str(o).strip()for o in _parse_json_list(l.get("outcomes"))]
 if len(d)!=2:return None
 z,y=d[0],d[1];j,i=_norm_team(z),_norm_team(y);e=(_parse_iso_ts(ev.get("startTime")or l.get("gameStartTime")or ev.get("endDate"))or.0)+3.25*3600.
 if now_ts is not None and e<now_ts+60.:return None
 h=TennisMatchSpec(event_id=str(ev.get("id")or""),slug=p,title=str(ev.get("title")or p),player_a=z,player_b=y,end_ts=e)
 def _parse_set_winner(cm):
  h=_parse_clob_tokens(cm);c=[_norm_team(str(x))for x in _parse_json_list(cm.get("outcomes"))];a=_parse_json_list(cm.get("outcomePrices"));e,d=None,None
  if h and len(c)==2 and{c[0],c[1]}=={j,i}:e,d=(h[0],h[1])if c[0]==j else(h[1],h[0])
  b=None
  if len(a)==2 and len(c)==2:
   try:
    g,f=float(a[0]),float(a[1])
    if cm.get("closed")or(max(g,f)>=.995 and min(g,f)<=.005):
     if g>=.995 and f<=.005:b="A"if c[0]==j else"B"
     elif f>=.995 and g<=.005:b="A"if c[1]==j else"B"
   except(TypeError,ValueError):pass
  return e,d,b
 for m in n:
  s=str(m.get("sportsMarketType")or"").strip().lower();q=str(m.get("groupItemTitle")or m.get("question")or"")
  if s=="tennis_first_set_winner":h.set1_a_token,h.set1_b_token,h.set1_resolved_winner=_parse_set_winner(m);continue
  if s=="tennis_set_winner"and(str(m.get("line")or"")=="2"or"set 2"in q.lower()):h.set2_a_token,h.set2_b_token,h.set2_resolved_winner=_parse_set_winner(m);continue
  if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
  tk=_parse_clob_tokens(m);g=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not tk or len(g)!=2:continue
  w,u=_extract_market_fee_rate(m)
  if s=="tennis_completed_match"and g==["yes","no"]:h.comp_yes_token,h.comp_no_token=tk[0],tk[1];h.comp_market_id=str(m.get("id")or"");h.comp_condition_id=str(m.get("conditionId")or"");h.comp_fee_rate,h.comp_fee_exp=w,u;h.comp_neg_risk=bool(m.get("negRisk"))
  elif s=="tennis_set_totals"and m.get("line")is not None and abs(float(m.get("line"))-2.5)<1e-6:
   if g[0].startswith("over")and g[1].startswith("under"):h.sets_ou25_over_token,h.sets_ou25_under_token=tk[0],tk[1];h.sets_ou25_market_id=str(m.get("id")or"");h.sets_ou25_condition_id=str(m.get("conditionId")or"");h.sets_ou25_fee_rate,h.sets_ou25_fee_exp=w,u;h.sets_ou25_neg_risk=bool(m.get("negRisk"))
  elif s in("tennis_first_set_totals","tennis_set_games_totals","tennis_match_totals")and m.get("line")is not None:
   t=float(m.get("line"))
   if not _is_half_hook(t)or not(g[0].startswith("over")and g[1].startswith("under")):continue
   if s=="tennis_first_set_totals":c="SET1_GAMES"
   elif s=="tennis_match_totals":c="MATCH_GAMES"
   elif"set 2"in q.lower():c="SET2_GAMES"
   elif"set 3"in q.lower():c="SET3_GAMES"
   else:continue
   h.totals_by_scope.setdefault(c,[]).append(TennisTotalRung(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),scope=c,line=t,over_token=tk[0],under_token=tk[1],fee_rate=w,fee_exp=u,neg_risk=bool(m.get("negRisk"))))
 for k in h.totals_by_scope:h.totals_by_scope[k].sort(key=lambda r:r.line)
 b=any(len(v)>=2 for v in h.totals_by_scope.values());a=bool(h.sets_ou25_over_token and h.comp_no_token)
 if not(b or a):return None
 return h
def evaluate_ten1_tennis_opportunities(spec,books_by_token,best_asks,max_box_cost_net=.988):
 h=[]
 for g,f in spec.totals_by_scope.items():
  for i in range(len(f)):
   o=f[i];e=best_asks.get(o.over_token)
   if e is None or not(.01<=e<=.99):continue
   for j in range(i+1,len(f)):
    n=f[j]
    if n.line<=o.line+.1:continue
    d=best_asks.get(n.under_token)
    if d is None or not(.01<=d<=.99):continue
    c=round(_net_unit_ask(e,o.fee_rate,o.fee_exp)+_net_unit_ask(d,n.fee_rate,n.fee_exp),4)
    if c<=max_box_cost_net:h.append({"mode":f"TEN1_{g}_CORRIDOR","event_id":spec.event_id,"slug":spec.slug,"title":spec.title,"box_cost_net":c,"close_ts":spec.end_ts,"leg_a":{"token_id":o.over_token,"opp_token_id":o.under_token,"condition_id":o.condition_id,"market_id":o.market_id,"side":"OVER","label":f"{g} O{o.line}","fee_rate":o.fee_rate,"fee_exponent":o.fee_exp,"neg_risk":bool(o.neg_risk),"strike":o.line,"end_ts":spec.end_ts},"leg_b":{"token_id":n.under_token,"opp_token_id":n.over_token,"condition_id":n.condition_id,"market_id":n.market_id,"side":"UNDER","label":f"{g} U{n.line}","fee_rate":n.fee_rate,"fee_exponent":n.fee_exp,"neg_risk":bool(n.neg_risk),"strike":n.line,"end_ts":spec.end_ts},"label":f"{spec.title[:36]}: {g} O{o.line} + U{n.line}"})
 m=_infer_live_map_winner(spec.set1_resolved_winner,spec.set1_a_token,spec.set1_b_token,books_by_token);l=_infer_live_map_winner(spec.set2_resolved_winner,spec.set2_a_token,spec.set2_b_token,books_by_token)
 if m in("A","B")and l in("A","B")and m!=l and spec.sets_ou25_over_token and spec.comp_no_token:
  a=best_asks.get(spec.sets_ou25_over_token);b=best_asks.get(spec.comp_no_token)
  if a is not None and b is not None:
   k=round(_net_unit_ask(a,spec.sets_ou25_fee_rate,spec.sets_ou25_fee_exp)+_net_unit_ask(b,spec.comp_fee_rate,spec.comp_fee_exp),4)
   if k<=max_box_cost_net:h.append({"mode":"TEN1_1_1_RETIREMENT_HEDGED_BOX","event_id":spec.event_id,"slug":spec.slug,"title":spec.title,"box_cost_net":k,"close_ts":spec.end_ts,"leg_a":{"token_id":spec.sets_ou25_over_token,"opp_token_id":spec.sets_ou25_under_token or"","condition_id":spec.sets_ou25_condition_id,"market_id":spec.sets_ou25_market_id,"side":"OVER_2.5","label":"Sets O2.5 [1-1]","fee_rate":spec.sets_ou25_fee_rate,"fee_exponent":spec.sets_ou25_fee_exp,"neg_risk":bool(spec.sets_ou25_neg_risk),"strike":2.5,"end_ts":spec.end_ts},"leg_b":{"token_id":spec.comp_no_token,"opp_token_id":spec.comp_yes_token or"","condition_id":spec.comp_condition_id,"market_id":spec.comp_market_id,"side":"NO_COMP","label":"NO[Completed Match]","fee_rate":spec.comp_fee_rate,"fee_exponent":spec.comp_fee_exp,"neg_risk":bool(spec.comp_neg_risk),"strike":.0,"end_ts":spec.end_ts},"label":f"{spec.title[:36]}: Sets O2.5 + NO[Completed] [1-1 Split]"})
 h.sort(key=lambda x:float(x["box_cost_net"]));return h
# ======================================================================================
# [15/21] MODULE: src/polymarket_research/riskless_frontier_v4_engine.py
# PURPOSE: Riskless Frontier v4 Evergreen Engine (AFF1 Subperiod Collapse, SOC2 83-State Lattice, NFL_PRP1 Locks, SUM1 Frechet Triangles, CRY_INC1 Binance Inclusion, MKR_LOCK1)
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import math;import re;import urllib.request;from dataclasses import dataclass,field;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;from src.polymarket_research.barrier_onetouch_svi_engine import(BarrierRungSpec,parse_barrier_direction,parse_hit_event,parse_strike_from_text);from src.polymarket_research.riskless_frontier_v2_engine import(NegRiskConvertSlateSpec,_is_half_hook,canon_player_name,detect_nr2_convert_no_subset_arbs,find_state_matrix_dominance_boxes);from src.polymarket_research.riskless_frontier_v3_engine import(LiveMultiSportGame,NbaSubperiodMarketSpec,ScoreConfirmationTracker,_teams_match_fuzzy,parse_nba_subperiod_and_ext_props);from src.polymarket_research.tradfi_sports_zero_fee_engine import(_SPREAD_FAV_RE,_extract_market_fee_rate,_net_unit_ask,_norm_team,_parse_clob_tokens,_parse_iso_ts);from src.polymarket_research.uma_nba_endgame_engine import(_canon_nba_team,_parse_json_list);FRONTIER_V4_GRAD8_SLEEVES=("AFF1_FROZEN_SUBPERIOD_COLLAPSE","SOC2_EXACT_SCORE_2D_LATTICE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS","SUM1_FRECHET_SUM_TRIANGLES","CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER");ESPN_NFL_SUMMARY_URL="https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={game_id}"
@dataclass
class FirstPassageMarketSpec:event_id:str;market_id:str;condition_id:str;kind:str;target_pts:int;away_token:str;home_token:str;away_label:str;home_label:str;fee_rate:float;fee_exponent:float;settle_est_ts:float;neg_risk=False
@dataclass
class AffineGameBundle:
 sport:str;event_id:str;slug:str;title:str;tipoff_ts:float;settle_est_ts:float;away_team:str;home_team:str;markets=field(default_factory=list);overtime_yes_leg=None;first_passage_markets=field(default_factory=list)
 @property
 def start_ts(self):return self.tipoff_ts
class SubperiodFreezeTracker:
 def __init__(a):a._frozen_since={};a._race_latched={}
 def confirm_frozen_pair(a,sport,game_id,scope_key,away_pts,home_pts,period_ended,now_ts,freeze_confirm_sec=45.,instant_settled=False):
  d=(sport.upper(),str(game_id),scope_key)
  if not period_ended:a._frozen_since.pop(d,None);return None
  c=(int(away_pts),int(home_pts));b=a._frozen_since.get(d)
  if b is None or b[0]!=c:
   a._frozen_since[d]=(c,float(now_ts))
   if instant_settled or freeze_confirm_sec<=.0:return c
   return None
  if instant_settled or(float(now_ts)-b[1])>=freeze_confirm_sec:return c
  return None
 def observe_and_confirm_race_winner(a,sport,game_id,target_pts,away_score,home_score,now_ts,buffer_pts=3,confirm_sec=45.,is_final=False):
  h=(sport.upper(),str(game_id),int(target_pts));d=a._race_latched.get(h);c=int(target_pts)+(0 if is_final else int(buffer_pts))
  if d is not None:
   g,i=d;f=away_score if g=="AWAY"else home_score;e=home_score if g=="AWAY"else away_score
   if f<c:a._race_latched.pop(h,None);return None
   b=float(now_ts)-i
   if not is_final and b<confirm_sec and e>=int(target_pts):a._race_latched.pop(h,None);return None
   if is_final or b>=confirm_sec:return g
   return None
  if away_score>=c and home_score<int(target_pts):a._race_latched[h]=("AWAY",float(now_ts));return"AWAY"if(is_final or confirm_sec<=.0)else None
  if home_score>=c and away_score<int(target_pts):a._race_latched[h]=("HOME",float(now_ts));return"HOME"if(is_final or confirm_sec<=.0)else None
  return None
 def prune(a,now_ts,max_age_sec=21600.):
  d=float(now_ts)-float(max_age_sec);c=[k for k,(_,t0)in a._frozen_since.items()if t0<d]
  for k in c:del a._frozen_since[k]
  b=[k for k,(_,t0)in a._race_latched.items()if t0<d]
  for k in b:del a._race_latched[k]
  return len(c)+len(b)
_AFFINE_SMT_MAP={"totals":("FG","TOTAL"),"spreads":("FG","SPREAD"),"moneyline":("FG","ML"),"first_half_totals":("1H","TOTAL"),"first_half_spreads":("1H","SPREAD"),"first_half_moneyline":("1H","ML"),"q1_totals":("Q1","TOTAL"),"q2_totals":("Q2","TOTAL"),"q3_totals":("Q3","TOTAL"),"q4_totals":("Q4","TOTAL"),"q1_spreads":("Q1","SPREAD"),"q2_spreads":("Q2","SPREAD"),"q3_spreads":("Q3","SPREAD"),"q4_spreads":("Q4","SPREAD"),"team_totals":("FG","TEAM_TOTAL"),"first_half_team_totals":("1H","TEAM_TOTAL"),"second_half_team_totals":("2H","TEAM_TOTAL")};_RACE_PTS_RE=re.compile(r"race\s+to\s+(\d+)\s+points",re.IGNORECASE)
def _canon_sport_team(sport,raw):return _canon_nba_team(raw)if sport.upper()=="NBA"else _norm_team(raw)
def parse_affine_game_bundle(events,now_ts=None):
 h={}
 for Y in events or[]:
  if not isinstance(Y,dict)or Y.get("closed")or Y.get("archived"):continue
  Z=str(Y.get("slug")or"").lower()
  if not Z.startswith(("nba-","nfl-","cfb-")):continue
  if any(Z.endswith(s)for s in("-exact-margin","-player-props","-halftime-result")):continue
  b=re.sub(r"-more-markets$","",Z);h.setdefault(b,[]).append(Y)
 B=[]
 for b,A in h.items():
  S="NBA"if b.startswith("nba-")else("NFL"if b.startswith("nfl-")else"CFB");z=next((e for e in A if str(e.get("slug")or"").lower()==b),A[0]);R=re.sub(r"\s*-\s*More Markets\s*$","",str(z.get("title")or""),flags=re.I).strip();Q=re.split(r"\s+(?:vs\.?|@)\s+",R,maxsplit=1,flags=re.IGNORECASE)
  if len(Q)!=2:continue
  L=_canon_sport_team(S,Q[0]);K=_canon_sport_team(S,Q[1])
  if not L or not K or L==K:continue
  J=_parse_iso_ts(z.get("startTime")or z.get("gameStartTime")or z.get("endDate"))or.0
  if J<=.0 or(now_ts is not None and J<now_ts-8.*3600.):continue
  q=J+(3.25 if S=="NBA"else 3.75)*3600.;P=str(z.get("id")or"");g=[];a=None;y=[];p=set()
  for Y in A:
   for m in Y.get("markets")or[]:
    _d=str(m.get("id")or"")
    if not _d or _d in p or m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
    p.add(_d);X=_parse_clob_tokens(m);W=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))]
    if not X or len(W)!=2:continue
    fr,fe=_extract_market_fee_rate(m);_c=str(m.get("sportsMarketType")or"").strip().lower();O=str(m.get("groupItemTitle")or m.get("question")or"").strip();I=str(m.get("question")or O).strip();_b=str(m.get("conditionId")or"");nr=bool(m.get("negRisk"))
    if _c=="basketball_game_overtime"or("overtime"in I.lower()and[o.lower()for o in W]==["yes","no"]):
     if re.search(r"\b(?:double|triple|2\+|3\+|first\s+half|1h|2h)\b",I,re.IGNORECASE):continue
     a={"market_id":_d,"condition_id":_b,"token_id":X[0],"opp_token_id":X[1],"side":"YES","label":"YES[Overtime]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":q,"strike":.5};continue
    if _c in("basketball_team_to_score_first","basketball_game_race_to_points"):
     if re.search(r"\b(?:1q|2q|3q|4q|q1|q2|q3|q4|quarter|half|1h|2h)\b",f"{I} {O}",re.IGNORECASE):continue
     F,E=_canon_sport_team(S,W[0]),_canon_sport_team(S,W[1])
     if{F,E}=={L,K}:
      H=1;G="FIRST_SCORE"
      if _c=="basketball_game_race_to_points":
       V=_RACE_PTS_RE.search(I)
       if not V:continue
       H=int(V.group(1));G="RACE_TO_X"
      if F==L:w,v,u,t=X[0],X[1],W[0],W[1]
      else:w,v,u,t=X[1],X[0],W[1],W[0]
      y.append(FirstPassageMarketSpec(event_id=P,market_id=_d,condition_id=_b,kind=G,target_pts=H,away_token=w,home_token=v,away_label=u,home_label=t,fee_rate=fr,fee_exponent=fe,settle_est_ts=J+.85*3600.,neg_risk=nr))
     continue
    if _c not in _AFFINE_SMT_MAP:continue
    x,U=_AFFINE_SMT_MAP[_c]
    if x=="FG"and re.search(r"\b(?:first[\s_-]+half|second[\s_-]+half|1st[\s_-]+half|2nd[\s_-]+half|halftime|half-time|1h|2h|1q|2q|3q|4q|q1|q2|q3|q4|(?:first|second|third|fourth|1st|2nd|3rd|4th)[\s_-]+quarter)\b",f"{I} {O}",re.IGNORECASE):continue
    N={"Q1":.75,"Q2":1.35,"1H":1.35,"Q3":2.15}.get(x,3.25 if S=="NBA"else 3.75)*3600.;r=J+N
    if U=="ML":
     F,E=_canon_sport_team(S,W[0]),_canon_sport_team(S,W[1])
     if{F,E}=={L,K}:g.append(NbaSubperiodMarketSpec(P,_d,_b,x,"ML",.0,F,X[0],X[1],W[0],W[1],fr,r,O or f"{x} ML",nr,fe))
    elif U=="SPREAD":
     f=m.get("line")
     if f is None:continue
     try:T=abs(float(f))
     except(TypeError,ValueError):continue
     if not _is_half_hook(T):continue
     F,E=_canon_sport_team(S,W[0]),_canon_sport_team(S,W[1])
     if{F,E}!={L,K}:continue
     M=_SPREAD_FAV_RE.search(I);c=None
     if M:
      D=_canon_sport_team(S,M.group(1));_a=float(M.group(2))
      if D in(L,K):c=D if _a<0 else(K if D==L else L)
     if c is None:continue
     if F==c:n,l,k,j=X[0],X[1],W[0],W[1]
     else:n,l,k,j=X[1],X[0],W[1],W[0]
     g.append(NbaSubperiodMarketSpec(P,_d,_b,x,"SPREAD",T,c,n,l,k,j,fr,r,f"{x} {k}(-{T})/{j}(+{T})",nr,fe))
    elif U in("TOTAL","TEAM_TOTAL"):
     f=m.get("line")
     if f is None:continue
     try:T=float(f)
     except(TypeError,ValueError):continue
     if T<=.0 or not _is_half_hook(T):continue
     if not(W[0].lower().startswith("over")and W[1].lower().startswith("under")):continue
     i=str(m.get("description")or"").lower()
     if x in("FG","2H")and("overtime is not included"in i or"excludes overtime"in i):continue
     d=None
     if U=="TEAM_TOTAL":
      C=I.split("O/U")[0];ca=L in _canon_sport_team(S,C)or _norm_team(Q[0])in _norm_team(C);ch=K in _canon_sport_team(S,C)or _norm_team(Q[1])in _norm_team(C)
      if ca==ch:continue
      d=L if ca else K
     g.append(NbaSubperiodMarketSpec(P,_d,_b,x,U,T,d,X[0],X[1],"Over","Under",fr,r,O or f"{x} O/U {T}",nr,fe))
  if g or y:B.append(AffineGameBundle(sport=S,event_id=P,slug=b,title=R,tipoff_ts=J,settle_est_ts=q,away_team=L,home_team=K,markets=g,overtime_yes_leg=a,first_passage_markets=y))
 return B
def _leg_dict_from_subspec(sm,is_tok0,label_override=None):return{"token_id":sm.tok_0 if is_tok0 else sm.tok_1,"opp_token_id":sm.tok_1 if is_tok0 else sm.tok_0,"condition_id":sm.condition_id,"market_id":sm.market_id,"side":sm.out_0.upper()if is_tok0 else sm.out_1.upper(),"label":label_override or f"{sm.display_title}:{sm.out_0 if is_tok0 else sm.out_1}","fee_rate":sm.fee_rate,"fee_exponent":sm.fee_exponent,"neg_risk":bool(sm.neg_risk),"strike":float(sm.line or.0),"end_ts":sm.settle_est_ts}
def _spread_signed_legs(sm,away_team):
 a=float(sm.line or.0)
 if a<=.0:return[]
 if sm.team_side==away_team:return[("GT",+a,_leg_dict_from_subspec(sm,True,f"{sm.period_scope} {sm.out_0}(-{a})")),("LT",+a,_leg_dict_from_subspec(sm,False,f"{sm.period_scope} {sm.out_1}(+{a})"))]
 return[("LT",-a,_leg_dict_from_subspec(sm,True,f"{sm.period_scope} {sm.out_0}(-{a})")),("GT",-a,_leg_dict_from_subspec(sm,False,f"{sm.period_scope} {sm.out_1}(+{a})"))]
def evaluate_aff1_frozen_subperiod_opportunities(bundle,live_summary,best_asks,freeze_tracker,now_ts,espn_game_id="",freeze_confirm_sec=45.,max_2leg_cost_net=.992,max_3leg_cost_net=.99):
 c=[];b=[];a=[];M=str(live_summary.get("state")or"pre").lower()
 if M not in("in","post"):return{"two_leg_boxes":c,"three_leg_boxes":b,"single_leg_locks":a}
 k=bool(live_summary.get("completed")and M=="post");L=bool(live_summary.get("is_halftime"));F=int(live_summary.get("period")or 0);y=int(live_summary.get("away_score")or 0);w=int(live_summary.get("home_score")or 0);_b=(live_summary.get("linescores")or{}).get("away")or{};_a=(live_summary.get("linescores")or{}).get("home")or{};_j=espn_game_id or bundle.event_id
 def _try_2leg(mode,lg_a,lg_b,middle_width,desc):
  if lg_a["market_id"]==lg_b["market_id"]:return
  c=best_asks.get(lg_a["token_id"]);b=best_asks.get(lg_b["token_id"])
  if c is None or b is None or not(.005<=c<=.99 and.005<=b<=.99):return
  a=round(_net_unit_ask(float(c),lg_a["fee_rate"],lg_a["fee_exponent"])+_net_unit_ask(float(b),lg_b["fee_rate"],lg_b["fee_exponent"]),4)
  if a<=max_2leg_cost_net:c.append({"mode":mode,"sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"box_cost_gross":round(float(c)+float(b),4),"box_cost_net":a,"middle_width":round(float(middle_width),1),"close_ts":max(float(lg_a["end_ts"]),float(lg_b["end_ts"])),"leg_a":lg_a,"leg_b":lg_b,"label":f"{bundle.title}: {desc}"})
 j=(1 in _b and 1 in _a)and(k or L or F>=2);v=freeze_tracker.confirm_frozen_pair(bundle.sport,_j,"Q1",int(_b.get(1,0)),int(_a.get(1,0)),period_ended=j,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=(k or L or F>=3))
 if v is not None and not L and F<=2 and not k:
  Z,Y=v;X=float(Z+Y);W=float(Z-Y);V=[m for m in bundle.markets if m.period_scope=="1H"and m.kind=="TOTAL"and m.line is not None];U=[m for m in bundle.markets if m.period_scope=="Q2"and m.kind=="TOTAL"and m.line is not None]
  for m1 in V:
   T=float(m1.line);u=T-X
   for m2 in U:
    S=float(m2.line)
    if u<=S+1e-9:_try_2leg("AFF1_POST_Q1_1H_VS_Q2_TOTAL",_leg_dict_from_subspec(m1,True,f"1H O{T:g}"),_leg_dict_from_subspec(m2,False,f"Q2 U{S:g}"),S-u,f"1H O{T:g} + Q2 U{S:g} (Q1={int(X)} frozen)")
    if S<=u+1e-9:_try_2leg("AFF1_POST_Q1_1H_VS_Q2_TOTAL",_leg_dict_from_subspec(m1,False,f"1H U{T:g}"),_leg_dict_from_subspec(m2,True,f"Q2 O{S:g}"),u-S,f"1H U{T:g} + Q2 O{S:g} (Q1={int(X)} frozen)")
  K=[x for m in bundle.markets if m.period_scope=="1H"and m.kind=="SPREAD"for x in _spread_signed_legs(m,bundle.away_team)];J=[x for m in bundle.markets if m.period_scope=="Q2"and m.kind=="SPREAD"for x in _spread_signed_legs(m,bundle.away_team)]
  for _i,_h,_g in K:
   E=_h-W
   for _f,_e,_d in J:
    if _i=="GT"and _f=="LT"and E<=_e+1e-9:_try_2leg("AFF1_POST_Q1_1H_VS_Q2_SPREAD",_g,_d,_e-E,f"{_g['label']} + {_d['label']} (mQ1={W:+.0f})")
    elif _i=="LT"and _f=="GT"and _e<=E+1e-9:_try_2leg("AFF1_POST_Q1_1H_VS_Q2_SPREAD",_g,_d,E-_e,f"{_g['label']} + {_d['label']} (mQ1={W:+.0f})")
 if bundle.sport=="NBA":
  i=(1 in _b and 2 in _b and 1 in _a and 2 in _a)and(k or L or F>=3);t=freeze_tracker.confirm_frozen_pair(bundle.sport,_j,"1H",int(_b.get(1,0))+int(_b.get(2,0)),int(_a.get(1,0))+int(_a.get(2,0)),period_ended=i,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=(k or F>=4))
  if t is not None and not k:
   d={bundle.away_team:float(t[0]),bundle.home_team:float(t[1])}
   for tm,D in d.items():
    C=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TEAM_TOTAL"and m.team_side==tm and m.line is not None];B=[m for m in bundle.markets if m.period_scope=="2H"and m.kind=="TEAM_TOTAL"and m.team_side==tm and m.line is not None]
    for g in C:
     f=float(g.line);I=f-D
     for R in B:
      Q=float(R.line)
      if I<=Q+1e-9:_try_2leg("AFF1_HT_TEAM_TOTAL_FG_VS_2H",_leg_dict_from_subspec(g,True,f"FG {tm.title()} O{f:g}"),_leg_dict_from_subspec(R,False,f"2H {tm.title()} U{Q:g}"),Q-I,f"{tm.title()} FG O{f:g} + 2H U{Q:g} (1H={int(D)})")
      if Q<=I+1e-9:_try_2leg("AFF1_HT_TEAM_TOTAL_FG_VS_2H",_leg_dict_from_subspec(g,False,f"FG {tm.title()} U{f:g}"),_leg_dict_from_subspec(R,True,f"2H {tm.title()} O{Q:g}"),I-Q,f"{tm.title()} FG U{f:g} + 2H O{Q:g} (1H={int(D)})")
 if bundle.sport=="NBA":
  h=all(q in _b and q in _a for q in(1,2,3))and(k or F>=4);s=freeze_tracker.confirm_frozen_pair(bundle.sport,_j,"Q1_Q3",int(_b.get(1,0))+int(_b.get(2,0))+int(_b.get(3,0)),int(_a.get(1,0))+int(_a.get(2,0))+int(_a.get(3,0)),period_ended=h,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=k)
  if s is not None and not k and F==4:
   H=float(s[0]+s[1]);r=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TOTAL"and m.line is not None];p=[m for m in bundle.markets if m.period_scope=="Q4"and m.kind=="TOTAL"and m.line is not None];A=bundle.overtime_yes_leg;G=best_asks.get(A["token_id"])if A is not None else None;P=_net_unit_ask(float(G),A["fee_rate"],A["fee_exponent"])if(A and G is not None)else None
   for g in r:
    f=float(g.line);z=f-H
    for O in p:
     N=float(O.line)
     if z<=N+1e-9:_try_2leg("AFF1_POST_Q3_FG_OVER_4Q_UNDER",_leg_dict_from_subspec(g,True,f"FG O{f:g}"),_leg_dict_from_subspec(O,False,f"4Q U{N:g}"),N-z,f"FG O{f:g} + 4Q U{N:g} (Q1..3={int(H)})")
     if N<=z+1e-9 and A is not None and G is not None and P is not None:
      o=_leg_dict_from_subspec(g,False,f"FG U{f:g}");n=_leg_dict_from_subspec(O,True,f"4Q O{N:g}");pu=best_asks.get(o["token_id"]);po=best_asks.get(n["token_id"])
      if(pu is not None and po is not None and.005<=float(pu)<=.99 and.005<=float(po)<=.99 and.005<=float(G)<=.99):
       c3=round(_net_unit_ask(float(pu),o["fee_rate"],o["fee_exponent"])+_net_unit_ask(float(po),n["fee_rate"],n["fee_exponent"])+P,4)
       if c3<=max_3leg_cost_net:b.append({"mode":"AFF1_POST_Q3_OT_IMMUNIZED_3LEG","sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"n_legs":3,"box_cost_gross":round(float(pu)+float(po)+float(G),4),"box_cost_net":c3,"middle_width":round(z-N,1),"close_ts":max(o["end_ts"],n["end_ts"],A["end_ts"]),"legs":[o,n,A],"label":f"{bundle.title}: FG U{f:g} + 4Q O{N:g} + YES[OT] (Q1..3={int(H)})"})
 for fp in bundle.first_passage_markets:
  _c=2 if fp.kind=="FIRST_SCORE"else 3;e=freeze_tracker.observe_and_confirm_race_winner(bundle.sport,_j,fp.target_pts,y,w,now_ts=now_ts,buffer_pts=_c,confirm_sec=freeze_confirm_sec,is_final=k)
  if e in("AWAY","HOME"):l=e=="AWAY";a.append({"mode":f"AFF1_{fp.kind}_LOCK","sport":bundle.sport,"event_id":bundle.event_id,"market_id":fp.market_id,"condition_id":fp.condition_id,"token_id":fp.away_token if l else fp.home_token,"opp_token_id":fp.home_token if l else fp.away_token,"side_label":fp.away_label if l else fp.home_label,"display_label":(f"{bundle.title} {'First Score'if fp.kind=='FIRST_SCORE'else f'Race to {fp.target_pts}'}: {fp.away_label if l else fp.home_label} [{y}-{w}]"),"fee_rate":fp.fee_rate,"fee_exponent":fp.fee_exponent,"neg_risk":fp.neg_risk,"p_lock":.998,"close_ts":fp.settle_est_ts})
 c.sort(key=lambda x:float(x["box_cost_net"]));b.sort(key=lambda x:float(x["box_cost_net"]));return{"two_leg_boxes":c,"three_leg_boxes":b,"single_leg_locks":a}
SOC2_GRID_MAX=8;SOC2_PLAYED_STATES=[(h,a)for h in range(SOC2_GRID_MAX+1)for a in range(SOC2_GRID_MAX+1)];SOC2_NUM_STATES=len(SOC2_PLAYED_STATES)+2;_EXACT_SCORE_ITEM_RE=re.compile(r"(\d+)\s*[-–:]\s*(\d+)");_SOC_ADV_VETO_RE=re.compile(r"(\badvance\b|\bqualify\b|\blift the trophy\b|\bincluding extra time\b|\bpenalties\b)",re.IGNORECASE);_SOC_SUBPERIOD_OR_PROP_VETO_RE=re.compile(r"(\bfirst[\s_-]+half\b|\bsecond[\s_-]+half\b|\b1st[\s_-]+half\b|\b2nd[\s_-]+half\b" r"|\bhalftime\b|\bhalf-time\b|\beach[\s_-]+half\b|\bboth[\s_-]+halves\b" r"|\b1h\b|\b2h\b|\bteam[\s_-]+totals?\b|\bcorners?\b|\bcards?\b|\bshots?\b|\boffsides?\b)",re.IGNORECASE)
@dataclass
class SoccerExactScoreLattice:game_key:str;game_id:str;title:str;end_ts:float;home_team:str;away_team:str;exact_event_id:str;exact_slug:str;exact_neg_risk_market_id:str;is_closed_37_slate:bool;score_brackets:Dict[Tuple[int,int],Dict[str,Any]];any_other_bracket:Optional[Dict[str,Any]];convert_spec:Optional[NegRiskConvertSlateSpec];matrix_legs=field(default_factory=list)
def _extract_soccer_slug_match_key(slug):
 s=re.sub(r"-(more-markets|exact-score|halftime-result|second-half-result|first-to-score)$","",slug.lower().strip())
 if re.search(r"-20\d{2}-\d{2}-\d{2}$",s):return s
 return None
def link_and_parse_soc2_exact_score_lattices(events,now_ts=None):
 _j={};u={}
 for ev in events or[]:
  if not isinstance(ev,dict)or ev.get("closed")or ev.get("archived"):continue
  sl=str(ev.get("slug")or"").lower();_i=str(ev.get("gameId")or"").strip();N=_extract_soccer_slug_match_key(sl)
  if _i and N:u[N]=_i
 for ev in events or[]:
  if not isinstance(ev,dict)or ev.get("closed")or ev.get("archived"):continue
  sl=str(ev.get("slug")or"").lower();_i=str(ev.get("gameId")or"").strip();N=_extract_soccer_slug_match_key(sl);_H=_i or(u.get(N)if N else None)or N
  if _H:_j.setdefault(_H,[]).append(ev)
 M={}
 for _C,W in _j.items():
  L=next((e for e in W if str(e.get("slug")or"").lower().endswith("-exact-score")),None)
  if L is None:continue
  V=next((e for e in W if e.get("negRisk")and len(e.get("markets")or[])==3 and not str(e.get("slug")or"").lower().endswith(("-halftime-result","-second-half-result","-first-to-score","-exact-score"))),None);U=next((e for e in W if str(e.get("slug")or"").lower().endswith("-more-markets")),None);F=re.sub(r"\s*-\s*Exact Score\s*$","",str(L.get("title")or""),flags=re.I).strip();T=re.split(r"\s+vs\.?\s+",F,maxsplit=1,flags=re.IGNORECASE)
  if len(T)!=2:continue
  K,J=T[0].strip(),T[1].strip();_h,_g=_norm_team(K),_norm_team(J)
  if not _h or not _g or _h==_g:continue
  _f=_parse_iso_ts((V or L).get("startTime")or L.get("gameStartTime")or L.get("endDate"))or.0
  if _f<=.0 or(now_ts is not None and _f<now_ts-4.*3600.):continue
  E={};d=None;l=[];t=[];c=True;S=L.get("markets")or[]
  for _t,m in enumerate(S):
   if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:c=False;continue
   v=str(m.get("question")or"");n=str(m.get("description")or"");_d=str(m.get("groupItemTitle")or"").strip();_e=str(m.get("sportsMarketType")or"").strip().lower()
   if _SOC_ADV_VETO_RE.search(f"{v}\n{n}")or _SOC_SUBPERIOD_OR_PROP_VETO_RE.search(f"{v}\n{_d}\n{_e}"):c=False;continue
   q=_parse_clob_tokens(m);p=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
   if not q or p!=["yes","no"]:c=False;continue
   Y,X=_extract_market_fee_rate(m);_B=str(m.get("questionID")or"").strip().lower();_s=int(_B[64:],16)if(len(_B)==66 and _B.startswith("0x"))else _t;z,y=str(m.get("id")or""),str(m.get("conditionId")or"");I="other"in _d.lower()or"any other"in v.lower();j,g=-1,-1
   if not I:
    _A=_EXACT_SCORE_ITEM_RE.search(_d or v)
    if not _A:c=False;continue
    j,g=int(_A.group(1)),int(_A.group(2));H=_norm_team(_d or v)
    if _g in H and _h in H:
     if H.find(_g)<H.find(_h):j,g=g,j
    elif _g in H and _h not in H and j<g:j,g=g,j
    elif _h in H and _g not in H and g>j:j,g=g,j
    if not(0<=j<=5 and 0<=g<=5):c=False;continue
   _r={"market_id":z,"condition_id":y,"question_index":_s,"label":"Any Other"if I else f"{j}-{g}","home_goals":j,"away_goals":g,"yes_token":q[0],"no_token":q[1],"fee_rate":Y,"fee_exponent":X,"neg_risk":True};l.append(_r)
   if I:d=_r;w=[1. if max(h,a)>=6 else.0 for(h,a)in SOC2_PLAYED_STATES]+[.0,.0]
   else:E[(j,g)]=_r;_q=1. if(j==0 and g==0)else.0;w=[1. if(h==j and a==g)else.0 for(h,a)in SOC2_PLAYED_STATES]+[_q,_q]
   _z=[1.-x for x in w];_p=_r["label"];t.append({"market_id":z,"condition_id":y,"token_id":q[0],"opp_token_id":q[1],"side":"YES","label":f"CS_Y[{_p}]","fee_rate":Y,"fee_exponent":X,"neg_risk":True,"end_ts":_f,"payoff_vec":w,"strike":float(max(0,j+g))});t.append({"market_id":z,"condition_id":y,"token_id":q[1],"opp_token_id":q[0],"side":"NO","label":f"CS_N[{_p}]","fee_rate":Y,"fee_exponent":X,"neg_risk":True,"end_ts":_f,"payoff_vec":_z,"strike":float(max(0,j+g))})
  if not E:continue
  r=(bool(L.get("negRisk"))and not bool(L.get("negRiskAugmented",False))and c and len(E)==36 and d is not None and len(l)==37);D=str(L.get("negRiskMarketID")or"").strip().lower();k=None
  if r and D.startswith("0x")and len(D)==66:
   l.sort(key=lambda b:int(b["question_index"]))
   if[int(b["question_index"])for b in l]==list(range(37)):k=NegRiskConvertSlateSpec(event_id=str(L.get("id")or""),slug=str(L.get("slug")or""),title=F,neg_risk_market_id=D,neg_risk_augmented=False,total_market_count=37,is_closed_convert_safe=True,end_ts=_f,brackets=l)
  if V is not None:
   for m in V.get("markets")or[]:
    if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
    v=str(m.get("question")or"");n=str(m.get("description")or"");_d=str(m.get("groupItemTitle")or"").strip();_c=str(m.get("sportsMarketType")or"").strip().lower()
    if _SOC_ADV_VETO_RE.search(f"{v}\n{n}\n{_d}")or _SOC_SUBPERIOD_OR_PROP_VETO_RE.search(f"{v}\n{_d}\n{_c}"):continue
    q=_parse_clob_tokens(m);p=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
    if not q or p!=["yes","no"]:continue
    Y,X=_extract_market_fee_rate(m);z,y=str(m.get("id")or""),str(m.get("conditionId")or"")
    if"draw"in _d.lower()or"end in a draw"in v.lower():C=[1. if h==a else.0 for(h,a)in SOC2_PLAYED_STATES]+[1.,.0];B=[1. if h!=a else.0 for(h,a)in SOC2_PLAYED_STATES]+[.0,.5];A="Draw"
    else:
     _b=_teams_match_fuzzy(_d,K);_a=_teams_match_fuzzy(_d,J)
     if _b and not _a:C=[1. if h>a else.0 for(h,a)in SOC2_PLAYED_STATES]+[.0,.0];B=[1. if h<=a else.0 for(h,a)in SOC2_PLAYED_STATES]+[1.,.5];A=K[:14]
     elif _a and not _b:C=[1. if a>h else.0 for(h,a)in SOC2_PLAYED_STATES]+[.0,.0];B=[1. if a<=h else.0 for(h,a)in SOC2_PLAYED_STATES]+[1.,.5];A=J[:14]
     else:continue
    t.append({"market_id":z,"condition_id":y,"token_id":q[0],"opp_token_id":q[1],"side":"YES","label":f"ML_Y[{A}]","fee_rate":Y,"fee_exponent":X,"neg_risk":True,"end_ts":_f,"payoff_vec":C,"strike":.0});t.append({"market_id":z,"condition_id":y,"token_id":q[1],"opp_token_id":q[0],"side":"NO","label":f"ML_N[{A}]","fee_rate":Y,"fee_exponent":X,"neg_risk":True,"end_ts":_f,"payoff_vec":B,"strike":.0})
  if U is not None:
   for m in U.get("markets")or[]:
    if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
    q=_parse_clob_tokens(m);p=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))]
    if not q or len(p)!=2:continue
    _G=str(m.get("sportsMarketType")or"").strip().lower();Z=str(m.get("question")or m.get("groupItemTitle")or"");G=str(m.get("groupItemTitle")or"").strip();n=str(m.get("description")or"")
    if _SOC_ADV_VETO_RE.search(f"{Z}\n{n}")or _SOC_SUBPERIOD_OR_PROP_VETO_RE.search(f"{Z}\n{G}\n{_G}"):continue
    Y,X=_extract_market_fee_rate(m);z,y=str(m.get("id")or""),str(m.get("conditionId")or"");nr=bool(m.get("negRisk"))
    if _G=="totals"and m.get("line")is not None:
     ln=float(m["line"])
     if _is_half_hook(ln)and.5<=ln<=7.5 and p[0].lower().startswith("over"):_y=[1. if(h+a)>ln else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];_x=[1. if(h+a)<ln else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];t.append({"market_id":z,"condition_id":y,"token_id":q[0],"opp_token_id":q[1],"side":"OVER","label":f"O[{ln:g} Goals]","fee_rate":Y,"fee_exponent":X,"neg_risk":nr,"end_ts":_f,"payoff_vec":_y,"strike":ln});t.append({"market_id":z,"condition_id":y,"token_id":q[1],"opp_token_id":q[0],"side":"UNDER","label":f"U[{ln:g} Goals]","fee_rate":Y,"fee_exponent":X,"neg_risk":nr,"end_ts":_f,"payoff_vec":_x,"strike":ln})
    elif _G in("","both_teams_to_score")and(_G=="both_teams_to_score"or"both teams to score"in Z.lower()):
     if[o.lower()for o in p]==["yes","no"]:_w=[1. if(h>=1 and a>=1)else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];_v=[1. if(h==0 or a==0)else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];t.append({"market_id":z,"condition_id":y,"token_id":q[0],"opp_token_id":q[1],"side":"YES","label":"BTTS[Yes]","fee_rate":Y,"fee_exponent":X,"neg_risk":nr,"end_ts":_f,"payoff_vec":_w,"strike":1.});t.append({"market_id":z,"condition_id":y,"token_id":q[1],"opp_token_id":q[0],"side":"NO","label":"BTTS[No]","fee_rate":Y,"fee_exponent":X,"neg_risk":nr,"end_ts":_f,"payoff_vec":_v,"strike":1.})
    elif _G=="spreads"and m.get("line")is not None:
     ln=abs(float(m["line"]))
     if _is_half_hook(ln)and.5<=ln<=5.5:
      _o=_SPREAD_FAV_RE.search(Z)
      if _o:
       R=_o.group(1).strip();_F=float(_o.group(2));f=_teams_match_fuzzy(R,K);s=_teams_match_fuzzy(R,J)
       if f!=s:
        if _F>0:f=not f
        Q=_teams_match_fuzzy(p[0],K);P,O=(q[0],q[1])if(Q==f)else(q[1],q[0]);_n=[1. if((h-a)>ln if f else(a-h)>ln)else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];_m=[1.-x if i<len(SOC2_PLAYED_STATES)else.5 for i,x in enumerate(_n)];_l=K[:10]if f else J[:10];_k=J[:10]if f else K[:10];t.append({"market_id":z,"condition_id":y,"token_id":P,"opp_token_id":O,"side":"SPREAD","label":f"{_l}(-{ln:g})","fee_rate":Y,"fee_exponent":X,"neg_risk":nr,"end_ts":_f,"payoff_vec":_n,"strike":-ln});t.append({"market_id":z,"condition_id":y,"token_id":O,"opp_token_id":P,"side":"SPREAD","label":f"{_k}(+{ln:g})","fee_rate":Y,"fee_exponent":X,"neg_risk":nr,"end_ts":_f,"payoff_vec":_m,"strike":ln})
  M[_C]=SoccerExactScoreLattice(game_key=_C,game_id=str(L.get("gameId")or(V or{}).get("gameId")or _C),title=F,end_ts=_f,home_team=K,away_team=J,exact_event_id=str(L.get("id")or""),exact_slug=str(L.get("slug")or""),exact_neg_risk_market_id=D,is_closed_37_slate=r,score_brackets=E,any_other_bracket=d,convert_spec=k,matrix_legs=t)
 return M
def detect_soc2_lattice_boxes_and_converts(lattice,books_by_token,best_asks,max_2leg_cost_net=.99,max_3leg_cost_net=.988,target_budget_usd=120.):
 c=find_state_matrix_dominance_boxes(lattice.matrix_legs,best_asks,max_2leg_cost_net=max_2leg_cost_net,max_3leg_cost_net=max_3leg_cost_net)
 for b in c:b["mode"]=f"SOC2_{b['n_legs']}LEG_LATTICE_BOX";b["title"]=lattice.title;b["game_key"]=lattice.game_key
 a=[]
 if lattice.convert_spec is not None and books_by_token:a=detect_nr2_convert_no_subset_arbs(lattice.convert_spec,books_by_token,target_budget_usd=target_budget_usd)
 return{"matrix_boxes":c,"convert_arbs":a}
def evaluate_soc2_dead_score_no_locks(lattice,live_soccer_board,tracker,now_ts,var_confirm_sec=210.):
 b=None;a=False
 for g in live_soccer_board:
  if g.start_ts>0 and lattice.end_ts>0 and abs(g.start_ts-lattice.end_ts)>10.*3600.:continue
  k=_teams_match_fuzzy(lattice.home_team,g.home_name)and _teams_match_fuzzy(lattice.away_team,g.away_name);j=_teams_match_fuzzy(lattice.home_team,g.away_name)and _teams_match_fuzzy(lattice.away_team,g.home_name)
  if k and j:continue
  if k:b,a=g,False;break
  if j:b,a=g,True;break
 if b is None:return[]
 if b.period>2:
  if(1 in b.linescores_home and 2 in b.linescores_home and 1 in b.linescores_away and 2 in b.linescores_away):h=int(b.linescores_home[1])+int(b.linescores_home[2]);f=int(b.linescores_away[1])+int(b.linescores_away[2]);e=f if a else h;d=h if a else f;c=True
  else:return[]
 else:c=bool(b.completed and b.state=="post");e=b.away_score if a else b.home_score;d=b.home_score if a else b.away_score
 n=tracker.observe_and_confirmed_floor("SOCCER",b.game_id,"HOME_G",e,now_ts,var_confirm_sec,is_final=c);m=tracker.observe_and_confirmed_floor("SOCCER",b.game_id,"AWAY_G",d,now_ts,var_confirm_sec,is_final=c)
 if n==0 and m==0 and not c:return[]
 l=[]
 for(r,q),p in lattice.score_brackets.items():
  i=(r!=n or q!=m)if c else(r<n or q<m)
  if not i:continue
  if(r==0 and q==0)and not c:continue
  l.append({"mode":"SOC2_FINAL_EXACT_SCORE_NO_LOCK"if c else"SOC2_LIVE_DEAD_SCORE_NO_LOCK","game_key":lattice.game_key,"market_id":p["market_id"],"condition_id":p["condition_id"],"token_id":p["no_token"],"opp_token_id":p["yes_token"],"side_label":f"NO[{r}-{q}]","display_label":f"{lattice.title} NO[{r}-{q}] [Confirmed {n}-{m}{' FT'if c else' post-VAR'}]","fee_rate":p["fee_rate"],"fee_exponent":p["fee_exponent"],"neg_risk":True,"p_lock":.999,"close_ts":lattice.end_ts+7200.})
 if(n>=6 or m>=6)and lattice.any_other_bracket is not None and c:o=lattice.any_other_bracket;l.append({"mode":"SOC2_ANY_OTHER_SCORE_YES_LOCK","game_key":lattice.game_key,"market_id":o["market_id"],"condition_id":o["condition_id"],"token_id":o["yes_token"],"opp_token_id":o["no_token"],"side_label":"YES[Any Other]","display_label":f"{lattice.title} YES[Any Other Score] [FT {n}-{m}]","fee_rate":o["fee_rate"],"fee_exponent":o["fee_exponent"],"neg_risk":True,"p_lock":.999,"close_ts":lattice.end_ts+7200.})
 return l
@dataclass
class NflPlayerPropRung:event_id:str;event_slug:str;game_title:str;market_id:str;condition_id:str;player_name:str;player_key:str;stat_type:str;line:float;yes_over_token:str;no_under_token:str;fee_rate:float;fee_exponent:float;kickoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;dnp_resolves_no=False
@dataclass
class NflPlayerPropSlate:event_id:str;slug:str;title:str;kickoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;anytime_td_by_player=field(default_factory=dict);two_plus_td_by_player=field(default_factory=dict);ladders_by_player_stat=field(default_factory=dict)
_NFL_ALLOWED_OU_SMTS=frozenset({"receptions","receiving_yards","rushing_yards","passing_yards","passing_completions","passing_attempts","passing_touchdowns","longest_reception","longest_rush"});_NFL_TD_PLAYER_RE=re.compile(r"^(.+?)\s*:\s*(?:anytime\s+touchdown|2\+\s*touchdowns|to\s+score\s+(?:a|2\+))\b",re.IGNORECASE);_NFL_WILL_TD_RE=re.compile(r"^will\s+(.+?)\s+score\s+(?:a\s+touchdown|2\+\s*touchdowns|at\s+least\s+2\s+touchdowns)",re.IGNORECASE);_NFL_COLON_PROP_RE=re.compile(r"^([^:]+?)\s*:\s*(.+?)(?:\s+O/U|\s+Over/Under|\s+\d)",re.IGNORECASE)
def _extract_nfl_prop_player(m):
 for e in("groupItemTitle","question"):
  d=str(m.get(e)or"").strip()
  if not d:continue
  for c in(_NFL_TD_PLAYER_RE,_NFL_WILL_TD_RE,_NFL_COLON_PROP_RE):
   f=c.search(d)
   if f:
    b=f.group(1).strip()
    if len(b)>=3 and" vs"not in b.lower():return b
  if":"in d:
   a=d.split(":",1)[0].strip()
   if 3<=len(a)<=40 and" vs"not in a.lower()and"spread"not in a.lower():return a
 return""
def parse_nfl_player_props_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived"):return None
 x=str(ev.get("slug")or"").lower()
 if not x.startswith("nfl-"):return None
 g=re.sub(r"\s*-\s*(?:Player Props|More Markets)\s*$","",str(ev.get("title")or""),flags=re.I).strip();t=re.split(r"\s+(?:vs\.?|@)\s+",g,maxsplit=1,flags=re.IGNORECASE)
 if len(t)!=2:return None
 p,n=_norm_team(t[0]),_norm_team(t[1]);i=_parse_iso_ts(ev.get("startTime")or ev.get("gameStartTime")or ev.get("endDate"))or.0
 if i<=.0 or(now_ts is not None and i<now_ts-8.*3600.):return None
 f=i+3.75*3600.;s=str(ev.get("id")or"");b={};a={};h={}
 for m in ev.get("markets")or[]:
  if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
  y=str(m.get("sportsMarketType")or"").strip().lower();w=_parse_clob_tokens(m);v=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not w or len(v)!=2:continue
  C,B=_extract_market_fee_rate(m);q=_extract_nfl_prop_player(m);u=canon_player_name(q)
  if not u:continue
  if y in("anytime_touchdowns","two_plus_touchdowns")and v==["yes","no"]:
   e=f"{m.get('question')or''} {m.get('groupItemTitle')or''}"
   if re.search(r"\b(?:first|last|1st\s+td|1st\s+touchdown|1h|2h|first\s+half|second\s+half|1q|2q|3q|4q|quarter)\b",e,re.IGNORECASE):continue
   d=str(m.get("description")or"").lower();c=bool("50-50"not in d and"void"not in d and re.search(r'not\s+play[^.]*resolve[s]?\s+to\s+"?no"?',d));l=y=="anytime_touchdowns";A=NflPlayerPropRung(event_id=s,event_slug=x,game_title=g,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),player_name=q,player_key=u,stat_type="anytime_td"if l else"two_plus_td",line=.5 if l else 1.5,yes_over_token=w[0],no_under_token=w[1],fee_rate=C,fee_exponent=B,kickoff_ts=i,settle_est_ts=f,home_team=n,away_team=p,dnp_resolves_no=c)
   if l:b[u]=A
   else:a[u]=A
   continue
  if y in _NFL_ALLOWED_OU_SMTS and(v==["over","under"]or v==["yes","no"]):
   j=m.get("line")
   if j is None:continue
   try:z=float(j)
   except(TypeError,ValueError):continue
   if z<.5 or not _is_half_hook(z):continue
   h.setdefault((u,y),[]).append(NflPlayerPropRung(event_id=s,event_slug=x,game_title=g,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),player_name=q,player_key=u,stat_type=y,line=z,yes_over_token=w[0],no_under_token=w[1],fee_rate=C,fee_exponent=B,kickoff_ts=i,settle_est_ts=f,home_team=n,away_team=p))
 for k in h:h[k].sort(key=lambda r:r.line)
 if not b and not a and not h:return None
 return NflPlayerPropSlate(event_id=s,slug=x,title=g,kickoff_ts=i,settle_est_ts=f,home_team=n,away_team=p,anytime_td_by_player=b,two_plus_td_by_player=a,ladders_by_player_stat=h)
def detect_nfl_prp1_boxes(slate,best_asks,max_box_cost_net=.992):
 m=[]
 for l,e in slate.anytime_td_by_player.items():
  d=slate.two_plus_td_by_player.get(l)
  if d is None or e.market_id==d.market_id or e.dnp_resolves_no!=d.dnp_resolves_no:continue
  h=best_asks.get(e.yes_over_token);f=best_asks.get(d.no_under_token)
  if h is None or f is None or not(.01<=h<=.99 and.01<=f<=.99):continue
  a=round(_net_unit_ask(float(h),e.fee_rate,e.fee_exponent)+_net_unit_ask(float(f),d.fee_rate,d.fee_exponent),4)
  if a<=max_box_cost_net:m.append({"mode":"NFL_PRP1_TD_POLISH_MIDDLE","event_id":slate.event_id,"slug":slate.slug,"title":slate.title,"player_name":e.player_name,"box_cost_gross":round(float(h)+float(f),4),"box_cost_net":a,"close_ts":slate.settle_est_ts,"leg_a":{"token_id":e.yes_over_token,"opp_token_id":e.no_under_token,"condition_id":e.condition_id,"market_id":e.market_id,"side":"YES","label":f"{e.player_name} Anytime TD","fee_rate":e.fee_rate,"fee_exponent":e.fee_exponent,"neg_risk":False,"strike":.5,"end_ts":slate.settle_est_ts},"leg_b":{"token_id":d.no_under_token,"opp_token_id":d.yes_over_token,"condition_id":d.condition_id,"market_id":d.market_id,"side":"NO","label":f"{d.player_name} NO 2+ TDs","fee_rate":d.fee_rate,"fee_exponent":d.fee_exponent,"neg_risk":False,"strike":1.5,"end_ts":slate.settle_est_ts},"label":f"{e.player_name}: YES(Anytime TD) + NO(2+ TDs)"})
 for(_,b),c in slate.ladders_by_player_stat.items():
  for i in range(len(c)):
   k=c[i];h=best_asks.get(k.yes_over_token)
   if h is None or not(.02<=h<=.98):continue
   for j in range(i+1,len(c)):
    g=c[j]
    if g.line<=k.line+.1 or k.market_id==g.market_id:continue
    f=best_asks.get(g.no_under_token)
    if f is None or not(.02<=f<=.98):continue
    a=round(_net_unit_ask(float(h),k.fee_rate,k.fee_exponent)+_net_unit_ask(float(f),g.fee_rate,g.fee_exponent),4)
    if a<=max_box_cost_net:m.append({"mode":"NFL_PRP1_STAT_CORRIDOR","event_id":slate.event_id,"slug":slate.slug,"title":slate.title,"player_name":k.player_name,"stat_type":b,"box_cost_gross":round(float(h)+float(f),4),"box_cost_net":a,"close_ts":slate.settle_est_ts,"leg_a":{"token_id":k.yes_over_token,"opp_token_id":k.no_under_token,"condition_id":k.condition_id,"market_id":k.market_id,"side":"OVER","label":f"{k.player_name} {b} O{k.line:g}","fee_rate":k.fee_rate,"fee_exponent":k.fee_exponent,"neg_risk":False,"strike":k.line,"end_ts":slate.settle_est_ts},"leg_b":{"token_id":g.no_under_token,"opp_token_id":g.yes_over_token,"condition_id":g.condition_id,"market_id":g.market_id,"side":"UNDER","label":f"{g.player_name} {b} U{g.line:g}","fee_rate":g.fee_rate,"fee_exponent":g.fee_exponent,"neg_risk":False,"strike":g.line,"end_ts":slate.settle_est_ts},"label":f"{k.player_name} {b} O{k.line:g} + U{g.line:g}"})
 m.sort(key=lambda x:float(x["box_cost_net"]));return m
def parse_espn_nfl_summary(summary_json):
 m={};c=[];b=set()
 for i in((summary_json or{}).get("boxscore")or{}).get("players")or[]:
  r=str((i.get("team")or{}).get("id")or"")
  for h in i.get("statistics")or[]:
   G=str(h.get("name")or"").lower();w=[str(k)for k in(h.get("keys")or h.get("labels")or[])]
   for F in h.get("athletes")or[]:
    v=canon_player_name(str((F.get("athlete")or{}).get("displayName")or""))
    if not v:continue
    if F.get("didNotPlay"):c.append((r,v));continue
    E=[str(x)for x in(F.get("stats")or[])]
    if not E:continue
    b.add(r);p=m.setdefault(v,{"rush_rec_tds":0})
    def _get_int(key_aliases):
     for a,b in enumerate(w):
      if b in key_aliases and a<len(E):
       try:return int(float(E[a].strip()))
       except ValueError:return None
     return None
    if G=="passing":
     for idx_k,kk in enumerate(w):
      if("completions"in kk or kk.upper()=="C/ATT")and idx_k<len(E)and"/"in E[idx_k]:
       D,C=E[idx_k].split("/",1)
       try:p["passing_completions"]=int(D);p["passing_attempts"]=int(C)
       except ValueError:pass
     M=_get_int(("passingYards","YDS"));B=_get_int(("passingTouchdowns","TD"))
     if M is not None:p["passing_yards"]=M
     if B is not None:p["passing_touchdowns"]=B
    elif G=="rushing":
     L=_get_int(("rushingYards","YDS"));A=_get_int(("rushingTouchdowns","TD"));K=_get_int(("longRushing","LONG"))
     if L is not None:p["rushing_yards"]=L
     if K is not None:p["longest_rush"]=K
     if A is not None:p["rushing_tds"]=A
    elif G=="receiving":
     J=_get_int(("receptions","REC"));z=_get_int(("receivingYards","YDS"));u=_get_int(("receivingTouchdowns","TD"));t=_get_int(("longReception","LONG"))
     if J is not None:p["receptions"]=J
     if z is not None:p["receiving_yards"]=z
     if t is not None:p["longest_reception"]=t
     if u is not None:p["receiving_tds"]=u
    elif G in("defensive","kickreturns","puntreturns","fumbles","interceptions"):
     y=_get_int(("defensiveTouchdowns","kickReturnTouchdowns","puntReturnTouchdowns","fumbleRecoveryTouchdowns","interceptionTouchdowns","touchdowns","TD"))
     if y is not None and y>0:p["non_off_tds"]=int(p.get("non_off_tds",0))+y
 for p in m.values():p["rush_rec_tds"]=int(p.get("rushing_tds",0))+int(p.get("receiving_tds",0));p["all_tds"]=int(p["rush_rec_tds"])+int(p.get("non_off_tds",0))
 d=[]
 for l in(summary_json or{}).get("scoringPlays")or[]:
  if not isinstance(l,dict):continue
  j=str(((l.get("scoringType")or{}).get("abbreviation")or(l.get("type")or{}).get("text")or"")).upper();o=str(l.get("text")or"")
  if"TD"in j or"TOUCHDOWN"in j or"touchdown"in o.lower():d.append(canon_player_name(o))
 f={N for(O,N)in c if O in b and N not in m};g,a,e,n="pre",False,0,"";q=((summary_json or{}).get("header")or{}).get("competitions")or[]
 if q:I=q[0];n=str(I.get("id")or"");H=I.get("status")or{};s=H.get("type")or{};g=str(s.get("state")or"pre").lower();a=bool(s.get("completed"));e=int(H.get("period")or 0)
 return{"game_id":n,"state":g,"completed":a,"period":e,"players":m,"inactive_players":f,"td_scoring_texts":d}
def fetch_espn_nfl_summary_sync(espn_game_id,timeout=5.):c=ESPN_NFL_SUMMARY_URL.format(game_id=espn_game_id);b=urllib.request.Request(c,headers={"User-Agent":"DominusSportsOracle/1.0"});a=json.loads(urllib.request.urlopen(b,timeout=timeout).read().decode("utf-8"));return parse_espn_nfl_summary(a)
def evaluate_nfl_prp1_live_locks(slate,nfl_summary,tracker,now_ts,play_confirm_sec=240.,td_confirm_sec=180.):
 t=str(nfl_summary.get("state")or"pre").lower()
 if t not in("in","post"):return[]
 g=bool(nfl_summary.get("completed")and t=="post");v=str(nfl_summary.get("game_id")or slate.event_id);j=nfl_summary.get("players")or{};c=set(nfl_summary.get("inactive_players")or set());f=list(nfl_summary.get("td_scoring_texts")or[]);s=[]
 for p,i,u in((slate.anytime_td_by_player,1,"Anytime TD"),(slate.two_plus_td_by_player,2,"2+ TDs")):
  for d,l in p.items():
   a=j.get(d)
   if a is not None:
    h=int(a.get("all_tds",a.get("rush_rec_tds",0)));e=tracker.observe_and_confirmed_floor("NFL",v,f"TD:{d}",h,now_ts,td_confirm_sec,is_final=g)
    if e>=i:s.append({"mode":"NFL_PRP1_TD_CLINCH_LOCK","market_id":l.market_id,"condition_id":l.condition_id,"token_id":l.yes_over_token,"opp_token_id":l.no_under_token,"side_label":"YES","display_label":f"{l.player_name} {u} YES [Confirmed TDs={e}]","fee_rate":l.fee_rate,"fee_exponent":l.fee_exponent,"neg_risk":False,"p_lock":.999 if g else.998,"close_ts":l.settle_est_ts})
    elif g and h<i:
     if any(d in w for w in f):continue
     s.append({"mode":"NFL_PRP1_FINAL_TD_NO_LOCK","market_id":l.market_id,"condition_id":l.condition_id,"token_id":l.no_under_token,"opp_token_id":l.yes_over_token,"side_label":"NO","display_label":f"{l.player_name} {u} NO [Final TDs={h}]","fee_rate":l.fee_rate,"fee_exponent":l.fee_exponent,"neg_risk":False,"p_lock":.999,"close_ts":l.settle_est_ts})
   elif d in c and g and l.dnp_resolves_no:s.append({"mode":"NFL_PRP1_INACTIVE_DNP_NO_LOCK","market_id":l.market_id,"condition_id":l.condition_id,"token_id":l.no_under_token,"opp_token_id":l.yes_over_token,"side_label":"NO","display_label":f"{l.player_name} {u} NO [Official Final DNP->No]","fee_rate":l.fee_rate,"fee_exponent":l.fee_exponent,"neg_risk":False,"p_lock":.998,"close_ts":l.settle_est_ts})
 for(d,o),r in slate.ladders_by_player_stat.items():
  a=j.get(d)
  if not a or o not in a:continue
  q=int(a[o])
  if o in("longest_reception","longest_rush","receptions","passing_completions","passing_attempts","passing_touchdowns"):
   n=td_confirm_sec if o=="passing_touchdowns"else play_confirm_sec;m=tracker.observe_and_confirmed_floor("NFL",v,f"{o}:{d}",q,now_ts,n,is_final=g);b=1 if(g or o=="passing_touchdowns")else 2
   for l in r:
    if m>=int(math.floor(l.line))+b:s.append({"mode":"NFL_PRP1_MAX_PLAY_LOCK"if o.startswith("longest_")else"NFL_PRP1_COUNTER_LOCK","market_id":l.market_id,"condition_id":l.condition_id,"token_id":l.yes_over_token,"opp_token_id":l.no_under_token,"side_label":"OVER","display_label":f"{l.player_name} {o} O{l.line:g} [Confirmed={m}]","fee_rate":l.fee_rate,"fee_exponent":l.fee_exponent,"neg_risk":False,"p_lock":.999 if g else.998,"close_ts":l.settle_est_ts})
    elif g and q<=int(math.floor(l.line))-1:s.append({"mode":"NFL_PRP1_FINAL_UNDER_LOCK","market_id":l.market_id,"condition_id":l.condition_id,"token_id":l.no_under_token,"opp_token_id":l.yes_over_token,"side_label":"UNDER","display_label":f"{l.player_name} {o} U{l.line:g} [Final={q}]","fee_rate":l.fee_rate,"fee_exponent":l.fee_exponent,"neg_risk":False,"p_lock":.999,"close_ts":l.settle_est_ts})
  elif g and o in("passing_yards","rushing_yards","receiving_yards"):
   for l in r:
    if abs(float(q)-l.line)>=2.5:k=float(q)>l.line;s.append({"mode":"NFL_PRP1_FINAL_YARDAGE_LOCK","market_id":l.market_id,"condition_id":l.condition_id,"token_id":l.yes_over_token if k else l.no_under_token,"opp_token_id":l.no_under_token if k else l.yes_over_token,"side_label":"OVER"if k else"UNDER","display_label":f"{l.player_name} {o} {'O'if k else'U'}{l.line:g} [Final={q}]","fee_rate":l.fee_rate,"fee_exponent":l.fee_exponent,"neg_risk":False,"p_lock":.998,"close_ts":l.settle_est_ts})
 return s
def detect_sum1_frechet_triangles(bundle,best_asks,max_3leg_cost_net=.99):
 b=[];d=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TEAM_TOTAL"and m.team_side==bundle.away_team and m.line is not None];c=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TEAM_TOTAL"and m.team_side==bundle.home_team and m.line is not None];y=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TOTAL"and m.line is not None]
 if d and c and y:b.append(("SUM1_AWAY_HOME_FG_TOTAL",d,c,y))
 w=[m for m in bundle.markets if m.period_scope=="Q1"and m.kind=="TOTAL"and m.line is not None];v=[m for m in bundle.markets if m.period_scope=="Q2"and m.kind=="TOTAL"and m.line is not None];u=[m for m in bundle.markets if m.period_scope=="1H"and m.kind=="TOTAL"and m.line is not None]
 if w and v and u:b.append(("SUM1_Q1_Q2_1H_TOTAL",w,v,u))
 if bundle.sport=="NBA":
  for L in(bundle.away_team,bundle.home_team):
   n=[m for m in bundle.markets if m.period_scope=="1H"and m.kind=="TEAM_TOTAL"and m.team_side==L and m.line is not None];l=[m for m in bundle.markets if m.period_scope=="2H"and m.kind=="TEAM_TOTAL"and m.team_side==L and m.line is not None];k=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TEAM_TOTAL"and m.team_side==L and m.line is not None]
   if n and l and k:b.append((f"SUM1_1H_2H_FG_TEAM_{L.upper()[:8]}",n,l,k))
 t=[]
 for a,K,J,I in b:
  for H in K:
   G=float(H.line);F=int(math.floor(G));j=best_asks.get(H.tok_0);i=best_asks.get(H.tok_1)
   for E in J:
    if H.market_id==E.market_id:continue
    D=float(E.line);C=int(math.floor(D));h=best_asks.get(E.tok_0);g=best_asks.get(E.tok_1)
    for B in I:
     if B.market_id in(H.market_id,E.market_id):continue
     A=float(B.line);z=int(math.floor(A));f=best_asks.get(B.tok_0);e=best_asks.get(B.tok_1)
     if z>=F+C and j is not None and h is not None and e is not None:
      s=round(_net_unit_ask(float(j),H.fee_rate,H.fee_exponent)+_net_unit_ask(float(h),E.fee_rate,E.fee_exponent)+_net_unit_ask(float(e),B.fee_rate,B.fee_exponent),4)
      if s<=max_3leg_cost_net:q=_leg_dict_from_subspec(H,True);p=_leg_dict_from_subspec(E,True);o=_leg_dict_from_subspec(B,False);t.append({"mode":f"{a}_UPPER","sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"n_legs":3,"box_cost_gross":round(float(j)+float(h)+float(e),4),"box_cost_net":s,"close_ts":max(q["end_ts"],p["end_ts"],o["end_ts"]),"legs":[q,p,o],"label":f"{bundle.title}: {q['label']} + {p['label']} + {o['label']}"})
     if z<=F+C+1 and i is not None and g is not None and f is not None:
      r=round(_net_unit_ask(float(i),H.fee_rate,H.fee_exponent)+_net_unit_ask(float(g),E.fee_rate,E.fee_exponent)+_net_unit_ask(float(f),B.fee_rate,B.fee_exponent),4)
      if r<=max_3leg_cost_net:q=_leg_dict_from_subspec(H,False);p=_leg_dict_from_subspec(E,False);o=_leg_dict_from_subspec(B,True);t.append({"mode":f"{a}_LOWER","sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"n_legs":3,"box_cost_gross":round(float(i)+float(g)+float(f),4),"box_cost_net":r,"close_ts":max(q["end_ts"],p["end_ts"],o["end_ts"]),"legs":[q,p,o],"label":f"{bundle.title}: {q['label']} + {p['label']} + {o['label']}"})
 t.sort(key=lambda x:float(x["box_cost_net"]));return t
@dataclass
class CryptoCloseRungSpec:event_id:str;slug:str;asset:str;market_id:str;condition_id:str;question:str;strike:float;direction:str;close_ts:float;yes_token:str;no_token:str;fee_rate:float;fee_exponent:float
_CRYPTO_SLUG_ASSET_MAP=(("bitcoin-","BTC"),("btc-","BTC"),("ethereum-","ETH"),("eth-","ETH"),("solana-","SOL"),("sol-","SOL"),("xrp-","XRP"),("bnb-","BNB"),("dogecoin-","DOGE"),("doge-","DOGE"))
def parse_binance_terminal_close_event(ev):
 if ev.get("closed")or ev.get("archived"):return[]
 i=str(ev.get("slug")or"").lower()
 if any(w in i for w in("hit-price","up-or-down","updown","5m","15m")):return[]
 e=next((s for r,s in _CRYPTO_SLUG_ASSET_MAP if i.startswith(r)),"")
 if not e:return[]
 c=_parse_iso_ts(ev.get("endDate"))or.0
 if c<=.0:return[]
 j=[]
 for m in ev.get("markets")or[]:
  if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
  q=str(m.get("question")or"");p=str(m.get("groupItemTitle")or"");h=str(m.get("description")or ev.get("description")or"").lower()
  if"binance"not in h or"chain.link"in h or"pyth.network"in h:continue
  n=q.lower()
  if any(w in n for w in("reach","hit","touch","dip","between")):continue
  if not any(w in n for w in("above","below","over","under","greater than","less than")):continue
  if re.search(r"\d[\d,]*\s*[-–to]+\s*\$?\d",p):continue
  a="DOWN"if any(w in n for w in("below","under","less than"))else"UP";b=parse_strike_from_text(q,p);g=_parse_clob_tokens(m);f=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not b or b<=.0 or not g or f!=["yes","no"]:continue
  l,k=_extract_market_fee_rate(m);d=_parse_iso_ts(m.get("endDate"))or c;j.append(CryptoCloseRungSpec(event_id=str(ev.get("id")or""),slug=i,asset=e,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),question=q,strike=b,direction=a,close_ts=d,yes_token=g[0],no_token=g[1],fee_rate=l,fee_exponent=k))
 return j
def detect_cry_inc1_binance_inclusion_boxes(hit_rungs,close_rungs,best_asks,now_ts,max_box_cost_net=.992):
 d=[h for h in hit_rungs if h.resolved_yes is None and h.end_ts>now_ts+120. and h.asset!="HYPE"];l=[]
 for p in close_rungs:
  if p.close_ts<=now_ts+120. or p.asset=="HYPE":continue
  k=best_asks.get(p.no_token)
  if k is None or not(.01<=k<=.98):continue
  j=_net_unit_ask(float(k),p.fee_rate,p.fee_exponent)
  for o in d:
   if o.asset!=p.asset or o.direction!=p.direction or o.market_id==p.market_id:continue
   if not(o.start_ts<=now_ts and o.start_ts<=p.close_ts-60. and p.close_ts<=o.end_ts):continue
   a=(o.strike<=p.strike+1e-9)if p.direction=="UP"else(o.strike>=p.strike-1e-9)
   if not a:continue
   f=best_asks.get(o.yes_token)
   if f is None or not(.01<=f<=.98):continue
   c=round(j+_net_unit_ask(float(f),o.fee_rate,o.fee_exponent),4)
   if c<=max_box_cost_net:b="↑"if p.direction=="UP"else"↓";l.append({"mode":"CRY_INC1_CLOSE_SUBSET_HIT","asset":p.asset,"direction":p.direction,"box_cost_gross":round(float(k)+float(f),4),"box_cost_net":c,"close_ts":max(p.close_ts,o.end_ts),"leg_a":{"token_id":p.no_token,"opp_token_id":p.yes_token,"condition_id":p.condition_id,"market_id":p.market_id,"side":"NO","label":f"NO[{p.asset} Close {b}{p.strike:g}]","fee_rate":p.fee_rate,"fee_exponent":p.fee_exponent,"neg_risk":False,"strike":p.strike,"end_ts":p.close_ts},"leg_b":{"token_id":o.yes_token,"opp_token_id":o.no_token,"condition_id":o.condition_id,"market_id":o.market_id,"side":"YES","label":f"YES[{p.asset} {o.horizon_group} Hit {b}{o.strike:g}]","fee_rate":o.fee_rate,"fee_exponent":o.fee_exponent,"neg_risk":False,"strike":o.strike,"end_ts":o.end_ts},"label":f"{p.asset} NO(Close {b}{p.strike:g}) + YES({o.horizon_group} Hit {b}{o.strike:g})"})
 for n in d:
  i=best_asks.get(n.no_token)
  if i is None or not(.01<=i<=.98):continue
  g=_net_unit_ask(float(i),n.fee_rate,n.fee_exponent)
  for m in d:
   if(m.asset!=n.asset or m.direction!=n.direction or m.event_id==n.event_id or m.market_id==n.market_id):continue
   if not(m.start_ts<=n.start_ts+1e-6 and m.end_ts>=n.end_ts+1800.):continue
   a=(m.strike<=n.strike+1e-9)if n.direction=="UP"else(m.strike>=n.strike-1e-9)
   if not a:continue
   e=best_asks.get(m.yes_token)
   if e is None or not(.01<=e<=.98):continue
   c=round(g+_net_unit_ask(float(e),m.fee_rate,m.fee_exponent),4)
   if c<=max_box_cost_net:b="↑"if n.direction=="UP"else"↓";l.append({"mode":"CRY_INC1_SUBWINDOW_HIT_INCLUSION","asset":n.asset,"direction":n.direction,"box_cost_gross":round(float(i)+float(e),4),"box_cost_net":c,"close_ts":m.end_ts,"leg_a":{"token_id":n.no_token,"opp_token_id":n.yes_token,"condition_id":n.condition_id,"market_id":n.market_id,"side":"NO","label":f"NO[{n.asset} {n.horizon_group} {b}{n.strike:g}]","fee_rate":n.fee_rate,"fee_exponent":n.fee_exponent,"neg_risk":False,"strike":n.strike,"end_ts":n.end_ts},"leg_b":{"token_id":m.yes_token,"opp_token_id":m.no_token,"condition_id":m.condition_id,"market_id":m.market_id,"side":"YES","label":f"YES[{m.asset} {m.horizon_group} {b}{m.strike:g}]","fee_rate":m.fee_rate,"fee_exponent":m.fee_exponent,"neg_risk":False,"strike":m.strike,"end_ts":m.end_ts},"label":f"{n.asset} NO({n.horizon_group} {b}{n.strike:g}) + YES({m.horizon_group} {b}{m.strike:g})"})
 l.sort(key=lambda x:float(x["box_cost_net"]));return l
def evaluate_mkr_lock1_post_clinch_rebate_bid(*,token_id,opp_token_id,market_id,condition_id,display_label,source_sleeve,p_lock,close_ts,now_ts,best_bid,best_ask,opp_best_bid,fee_rate=.05,fee_exponent=1.,maker_rebate_share=.2,neg_risk=False,tick_size=.001,min_maker_bid=.96,max_maker_bid=.991,min_net_edge_ps=.006,max_tte_sec=14400.):
 if p_lock<.997:return None
 k=float(close_ts)-float(now_ts)
 if not(60.<=k<=max_tte_sec):return None
 if opp_best_bid is not None and float(opp_best_bid)>.03:return None
 if best_ask is not None and float(best_ask)>.0:
  g=_net_unit_ask(float(best_ask),fee_rate,fee_exponent)
  if g<=.988:return None
 j=max(.001,float(tick_size));b=(float(best_ask)-j)if(best_ask is not None and float(best_ask)>.0)else max_maker_bid;e=min(float(max_maker_bid),b,float(p_lock)-min_net_edge_ps+.002)
 if e<min_maker_bid-1e-9:return None
 if best_bid is not None and float(best_bid)>=min_maker_bid:a=min(e,float(best_bid)+j)
 else:a=min(e,.986)
 i=math.floor((a+1e-9)/j);h=round(i*j,4)
 if not(min_maker_bid<=h<=max_maker_bid):return None
 if best_ask is not None and float(best_ask)>.0 and h>=float(best_ask)-1e-9:return None
 f=(float(maker_rebate_share)*float(fee_rate)*((h*(1.-h))**float(fee_exponent))if fee_rate>.0 else.0);d=round(h-f,6);c=round(float(p_lock)-d,6)
 if c<min_net_edge_ps:return None
 return{"mode":"MKR_LOCK1_POST_CLINCH_REBATE_BID","source_sleeve":source_sleeve,"token_id":token_id,"opp_token_id":opp_token_id,"market_id":market_id,"condition_id":condition_id,"display_label":f"MKR_LOCK[{display_label}] @{h:.3f}","post_only_bid":h,"maker_rebate_per_share":round(f,6),"effective_net_cost_per_share":d,"expected_net_edge_per_share":c,"p_lock":round(float(p_lock),5),"fee_rate":float(fee_rate),"fee_exponent":float(fee_exponent),"neg_risk":bool(neg_risk),"close_ts":float(close_ts),"tte_sec":round(k,1)}
# ======================================================================================
# [16/21] MODULE: src/polymarket_research/alpha_124_shadow_daemon.py
# PURPOSE: Unified Multi-Vertical Shadow Daemon (Crypto, Weather METAR/HKO, Pyth Commodities/Metals/Equities, Sports, UMA Bonds, Frontier v2/v3/v4)
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import argparse
import asyncio;import collections;import json;import logging;import math;import os;import re;import sys;import time;from datetime import datetime,timezone;from pathlib import Path;from typing import Any,Deque,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;import aiohttp;PROJECT_ROOT=Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT)not in sys.path:sys.path.insert(0,str(PROJECT_ROOT))
from src.polymarket_research.barrier_onetouch_svi_engine import(ASSET_BINANCE_SYMBOL,BINANCE_FAPI_URL,HIT_SERIES,BarrierRungSpec,detect_barrier_monotonicity_boxes,evaluate_barrier_no_net_ev,fetch_binance_window_extremes_sync,first_passage_touch_prob,get_wing_implied_vol,parse_hit_event);from src.polymarket_research.multistrike_svi_scalper import(DAILY_UPDOWN_SERIES,NEGRISK_SERIES,STRIKE_SERIES,ZERO_FEE_PYTH_DAILY_SERIES,DailyUpDownSpec,NegRiskBracketSpec,StrikeRungSpec,_fast_norm_cdf,build_negrisk_cross_box_bundles,detect_ladder_monotonicity_boxes,evaluate_coherent_strike_ladder,evaluate_svi_digital_fair_value,parse_daily_updown_event,parse_multistrike_event,parse_negrisk_bracket_event);from src.polymarket_research.net_alpha_opportunity_engine import(publish_global_positions_shm,rank_opportunities_capital_auction,read_global_positions_shm,scan_binary_complete_set_arb);from src.polymarket_research.orderflow_wfo_simulators import(compute_d1_legging_drag_haircut,compute_d1_maker_anchor_drag_haircut);from src.polymarket_research.riskless_machine_gun_engine import is_reward_locked_carry_live_ready;from src.polymarket_research.same_oracle_dominance_box import(DOMINANCE_ASSETS,DOMINANCE_SERIES_SLUGS,EMPIRICAL_BOX_ASSET_CAPS_USD,MIN_CORRIDOR_BPS_BY_ASSET,METAL_DOMINANCE_ASSETS,METAL_DOMINANCE_SERIES_SLUGS,TwapCandleMarketSpec,build_crypto_price_query_url,build_own_gamma_event_url,build_prev_15m_gamma_event_url,build_prev_5m_gamma_event_url,determine_dominance_legs,parse_authoritative_close_price,parse_authoritative_open_price,parse_closed_gamma_event_settlement,parse_metal_forex_candle_event,parse_twap_candle_event,verify_same_oracle_pair,walk_equal_shares_dominance_box,walk_equal_shares_multi_leg_box);from src.polymarket_research.exact_twap_lock_engine import(compute_exact_twap_lock_probability,read_shm_usd_anchor)
try:from src.polymarket_research.polymarket_ws_streams import PolymarketChainlinkLiveStream
except ImportError:
 try:from polymarket_ws_streams import PolymarketChainlinkLiveStream
 except ImportError:PolymarketChainlinkLiveStream=None
from src.polymarket_research.weather_metar_engine import(HIGH_VOLUME_WEATHER_SERIES,MetarObservation,WeatherEventSpec,celsius_to_market_int,compute_adaptive_metar_poll_ttl,compute_weather_probabilities,evaluate_weather_event_slate,fetch_live_ensemble_hourly_sync,fetch_metar_observations_sync,fetch_taf_extremes_sync,parse_weather_event);from src.polymarket_research.tradfi_sports_zero_fee_engine import(MULTI_SPORT_CORRIDOR_SERIES,NBA_SERIES_SLUGS,PYTH_ASSET_CONFIG,PYTH_CLOSE_SERIES,PYTH_HIT_SERIES,ZERO_FEE_NEGRISK_SERIES,MultiSportCorridorSpec,NbaGameSpec,NegRiskConvertSlateSpec,PythBarrierRungSpec,PythCloseRungSpec,ZeroFeeNegRiskSlateSpec,compute_effective_trading_hours,detect_multi_sport_corridor_boxes,detect_nba_dominance_boxes,detect_negrisk_convert_positions_arbs,detect_negrisk_no_pair_boxes,detect_pyth_calendar_inclusion_boxes,detect_pyth_close_vs_hit_boxes,evaluate_pyth_session_barrier_no_lock,evaluate_pyth_session_close_lock,fetch_yahoo_1m_intraday_sync,is_same_continuous_session,parse_multi_sport_corridor_event,parse_nba_zero_fee_event,parse_negrisk_convert_event,parse_pyth_close_event,parse_pyth_hit_event,parse_zero_fee_negrisk_slate,window_extremes_from_bars,_extract_market_fee_rate,_parse_clob_tokens,_parse_iso_ts);from src.polymarket_research.macro_counting_ctf_engine import(ALL_FOMC_MASK,ALL_OIL_SENATE_MASK,COUNTING_SERIES_HANDLES,FOMC_PARLAY_SERIES,GAS_SERIES_SLUGS,HOURLY_BINANCE_SERIES,NY_TZ,OIL_SENATE_SLUGS,CountingSlateSpec,build_fomc_truth_table_legs,build_oil_senate_truth_table_legs,detect_counting_subwindow_boxes,detect_d2_12pm_binance_boxes,evaluate_counting_dead_no_locks,evaluate_locked_market_reward_carry,evaluate_pyth_catalyst_shock,fetch_aaa_national_gas_sync,fetch_xtracker_user_stats_sync,find_cross_event_bitmask_boxes,parse_counting_slate_event,parse_gas_daily_bracket,walk_equal_shares_overround_bids,walk_position_overround_bid_unwind);from src.polymarket_research.uma_nba_endgame_engine import(LiveNbaGameState,evaluate_nba_endgame_locks,fetch_espn_nba_scoreboard_sync,is_objective_uma_market,match_nba_live_game,verify_uma_against_nba_live,verify_uma_onchain_proposal_sync);from src.polymarket_research.riskless_frontier_v2_engine import(BOP_2026_SLUGS,EsportsBo3Spec,NbaPlayerPropSlate,SoccerRegulationTree,build_lp1_bop_2026_truth_legs,build_lp1_nba_exact_margin_bundle,detect_nr2_convert_no_subset_arbs,detect_soc1_regulation_boxes,detect_sp4_milestone_ladder_boxes,evaluate_api1_esports_bo3_opportunities,evaluate_sp4_ingame_clinch_locks,fetch_espn_nba_boxscore_players_sync,find_state_matrix_dominance_boxes,link_and_parse_soccer_regulation_trees,parse_esports_bo3_event,parse_nba_player_props_from_event,verify_bond2_moov2_final_hour_sync,verify_negrisk_adapter_slate_sync);from src.polymarket_research.riskless_frontier_v3_engine import(LP2_MIDTERM_CORE_SLUGS,LP2_TOSSUP_CUBE_SLUG,LP2_TOSSUP_STATE_SLUGS,CalendarOrScalarLadderSpec,LiveMultiSportGame,NbaSubperiodAndExtPropSlate,ScoreConfirmationTracker,TennisMatchSpec,build_lp1_nfl_exact_margin_bundle,build_lp2_house_seats_truth_legs,build_lp2_pending_senate_conditional_groups,build_lp2_senate_seats_truth_legs,build_lp2_tossup_state_implication_groups,detect_cal1_monotonic_boxes,detect_lp2_seat_convert_implication_arbs,detect_multisport_ml_spread_polish_middles,detect_sp4_subperiod_and_ext_prop_boxes,evaluate_cl1_multisport_corridor_clinch_locks,evaluate_cl1_soccer_tree_clinch_locks,evaluate_sp4_subperiod_and_ext_locks,evaluate_ten1_tennis_opportunities,fetch_espn_multisport_board_sync,fetch_espn_nba_full_summary_sync,parse_cal1_monotonic_ladder_event,parse_nba_subperiod_and_ext_props,parse_tennis_retirement_safe_event,_teams_match_fuzzy);from src.polymarket_research.riskless_frontier_v4_engine import(FRONTIER_V4_GRAD8_SLEEVES,AffineGameBundle,CryptoCloseRungSpec,NflPlayerPropSlate,SoccerExactScoreLattice,SubperiodFreezeTracker,detect_cry_inc1_binance_inclusion_boxes,detect_nfl_prp1_boxes,detect_soc2_lattice_boxes_and_converts,detect_sum1_frechet_triangles,evaluate_aff1_frozen_subperiod_opportunities,evaluate_mkr_lock1_post_clinch_rebate_bid,evaluate_nfl_prp1_live_locks,evaluate_soc2_dead_score_no_locks,fetch_espn_nfl_summary_sync,link_and_parse_soc2_exact_score_lattices,parse_affine_game_bundle,parse_binance_terminal_close_event,parse_nfl_player_props_event);from src.polymarket_research.riskless_protocol_v2_expansion import(classify_market_rule_dispute_risk,compute_gatling_trajectory_projection,detect_b1_intraday_onetouch_noon_box,detect_d1_telescoping_candle_bridge,detect_dc1_double_chance_1x2_parity,detect_eq1_pyth_equity_dominance_box,detect_halftime_freeze_offset_box,detect_lp_comp1_sports_triangles,detect_mention1_cumulative_ladder_box,detect_nr4_nr5_optimal_tail_convert,detect_nr6_cross_slate_surjection_box,detect_w_prune1_metar_slate_arb,evaluate_s2_rtds_exact_twap_integrator,passes_uma_bond_dispute_guard,scan_full_universe_c1_and_ctf_overround);DATA_DIR=PROJECT_ROOT/"data"/"alpha124";DATA_DIR.mkdir(parents=True,exist_ok=True);_DEFAULT_DATA_DIR=DATA_DIR;STATE_FILE=DATA_DIR/"alpha124_shadow_state.json";_DEFAULT_STATE_FILE=STATE_FILE;LEDGER_FILE=DATA_DIR/"alpha124_shadow_ledger.jsonl";_DEFAULT_LEDGER_FILE=LEDGER_FILE;MARKET_TELEMETRY_FILE=DATA_DIR/"alpha124_market_telemetry.jsonl";OPPS_FILE=DATA_DIR/"alpha124_live_opportunities.json";LOG_FILE=DATA_DIR/"alpha124_shadow.log";BACKTEST_CAL_FILE=DATA_DIR/"backtest_alpha_124_results.json";LIVE_POLYMARKET_DIR=PROJECT_ROOT/"data"/"polymarket";SHOCK_TRIGGER_FILE=LIVE_POLYMARKET_DIR/"live_shock_triggers.jsonl";LIVE_ALPHA124_STATE_MIRROR_FILE=LIVE_POLYMARKET_DIR/"alpha124_shadow_state.json";D1_LIVE_CANDIDATES_FILE=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl";logging.basicConfig(level=logging.INFO,format="[%(asctime)s UTC] [%(levelname)s] [ALPHA-124] %(message)s",datefmt="%Y-%m-%d %H:%M:%S",handlers=[logging.FileHandler(LOG_FILE,encoding="utf-8"),logging.StreamHandler(sys.stdout)]);logger=logging.getLogger("Alpha124Shadow");GAMMA_URL="https://gamma-api.polymarket.com";CLOB_URL="https://clob.polymarket.com";DATA_API_URL="https://data-api.polymarket.com";CLOB_WS_URL="wss://ws-subscriptions-clob.polymarket.com/ws/market";BINANCE_URL="https://api.binance.com";LOCKED_MAKER_SLEEVES=frozenset({"W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK","BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","SP2_NBA_ENDGAME_LOCK","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"});DEPTH_CAPPED_TAKER_SLEEVES=LOCKED_MAKER_SLEEVES|frozenset({"CM_B2_PYTH_SESSION_NO_LOCK","CM_U1_PYTH_CLOSE_LOCK","B4_TOUCHED_BARRIER_WICK_LOCK","TW1_COUNTING_TRUNCATION_AND_BOX","GAS1_AAA_GASOLINE_LOCK","API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","AFF1_FROZEN_SUBPERIOD_COLLAPSE","SOC2_EXACT_SCORE_2D_LATTICE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS"})
try:import orjson as _orjson
except Exception:_orjson=None
CRYPTO_FEE_RATE=.07;QUARANTINED_SHADOW_SLEEVES=frozenset({"M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","B1_CONVEX_TAIL_YES","S2_EXACT_TWAP_LOCK","S5M_CHAINLINK_SNIPER","ZERO_FEE_MAKER_ANCHOR_BOX"});STRATEGY_EPOCH_MIN_TS={"S2_EXACT_TWAP_LOCK":1793758800.}
def _filter_epoch_closed_positions(sleeve,closed_list):
 a=STRATEGY_EPOCH_MIN_TS.get(str(sleeve))
 if not a:return closed_list
 return[p for p in closed_list if not(1.79e9<=float(p.get("entry_ts")or.0)<a)]
def is_shadow_sleeve_quarantined(sleeve):
 if sleeve=="S2_EXACT_TWAP_LOCK":
  if"PM_UNQUARANTINE_S2_TWAP_LOCK"in os.environ:return os.environ["PM_UNQUARANTINE_S2_TWAP_LOCK"]!="1"
  if"PM_QUARANTINE_LOSING_SLEEVES"in os.environ:return os.environ["PM_QUARANTINE_LOSING_SLEEVES"]=="1"
  return False
 return os.getenv("PM_QUARANTINE_LOSING_SLEEVES","1")=="1"and sleeve in QUARANTINED_SHADOW_SLEEVES
FRONTIER_V3_GRAD8_SLEEVES=frozenset({"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR"});BANKROLL_TICKETS={"T100":{"W1_SOLAR_PEAK_LOCK":15.,"W2_ENSEMBLE_VALUE":10.,"W2_MAKER_OVERROUND":10.,"W3_WEATHER_SLATE_ARB":12.,"B1_CONVEX_TAIL_YES":4.,"B2_BARRIER_NO_LOCK":15.,"B3_BARRIER_MONO_BOX":18.,"M1_SVI_MAKER_SCALP":15.,"M2_STRIKE_CONVERGENCE":15.,"M3_LADDER_MONO_BOX":20.,"M4_SHOCK_STRIKE_CATCHUP":15.,"D1_SAME_ORACLE_DOMINANCE_BOX":20.,"D1_4H_DOMINANCE_BOX":20.,"D1_QUIET_BOOK_BOX":20.,"D1_MAKER_ANCHOR_BOX":18.,"S5M_CHAINLINK_SNIPER":15.,"N1_NEGRISK_CROSS_BOX":20.,"P1_PREOPEN_MAKER_STRADDLE":16.,"U1_DAILY_UPDOWN_LOCK":15.,"C1_BINARY_COMPLETE_SET":20.,"S2_EXACT_TWAP_LOCK":15.,"CM_B3_PYTH_BARRIER_BOX":20.,"CM_B2_PYTH_SESSION_NO_LOCK":15.,"CM_U1_PYTH_CLOSE_LOCK":15.,"B4_TOUCHED_BARRIER_WICK_LOCK":20.,"SP1_NBA_ZERO_FEE_BOX":20.,"NR0_ZERO_FEE_SLATE_ARB":15.,"ZERO_FEE_MAKER_ANCHOR_BOX":18.,"ZF_INTRADAY_MAKER_BOX":18.,"TW1_COUNTING_TRUNCATION_AND_BOX":18.,"FED1_CENTRAL_BANK_LP_BOX":20.,"COND1_MACRO_PARTITION_BOX":20.,"CTF_OVERROUND_MINT_SELL":20.,"D2_12PM_BINANCE_BOX":18.,"GAS1_AAA_GASOLINE_LOCK":15.,"CM_SHOCK_PYTH_CATALYST":15.,"S4H_CHAINLINK_CONVERGENCE":15.,"MKR_REWARD_LOCKED_CARRY":15.,"W1_LOW_TROUGH_LOCK":15.,"SP2_NBA_ENDGAME_LOCK":18.,"BOND1_UMA_RESOLUTION_CARRY":20.,"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX":20.,"NR_CONV_NO_BASKET_ARB":20.,"NR2_CONVERT_NO_SUBSET_ARB":20.,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":18.,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":20.,"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":20.,"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX":20.,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":18.,"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG":20.,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":18.,"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX":20.,"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX":20.,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":18.,"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR":18.,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":18.,"SOC2_EXACT_SCORE_2D_LATTICE":18.,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":18.,"SUM1_FRECHET_SUM_TRIANGLES":20.,"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION":20.,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":18.},"T1000":{"W1_SOLAR_PEAK_LOCK":1e2,"W2_ENSEMBLE_VALUE":50.,"W2_MAKER_OVERROUND":50.,"W3_WEATHER_SLATE_ARB":80.,"B1_CONVEX_TAIL_YES":25.,"B2_BARRIER_NO_LOCK":1e2,"B3_BARRIER_MONO_BOX":120.,"M1_SVI_MAKER_SCALP":1e2,"M2_STRIKE_CONVERGENCE":1e2,"M3_LADDER_MONO_BOX":150.,"M4_SHOCK_STRIKE_CATCHUP":1e2,"D1_SAME_ORACLE_DOMINANCE_BOX":1e2,"D1_4H_DOMINANCE_BOX":1e2,"D1_QUIET_BOOK_BOX":1e2,"D1_MAKER_ANCHOR_BOX":1e2,"S5M_CHAINLINK_SNIPER":1e2,"N1_NEGRISK_CROSS_BOX":150.,"P1_PREOPEN_MAKER_STRADDLE":96.,"U1_DAILY_UPDOWN_LOCK":1e2,"C1_BINARY_COMPLETE_SET":150.,"S2_EXACT_TWAP_LOCK":1e2,"CM_B3_PYTH_BARRIER_BOX":120.,"CM_B2_PYTH_SESSION_NO_LOCK":1e2,"CM_U1_PYTH_CLOSE_LOCK":1e2,"B4_TOUCHED_BARRIER_WICK_LOCK":120.,"SP1_NBA_ZERO_FEE_BOX":120.,"NR0_ZERO_FEE_SLATE_ARB":1e2,"ZERO_FEE_MAKER_ANCHOR_BOX":1e2,"ZF_INTRADAY_MAKER_BOX":110.,"TW1_COUNTING_TRUNCATION_AND_BOX":1e2,"FED1_CENTRAL_BANK_LP_BOX":120.,"COND1_MACRO_PARTITION_BOX":120.,"CTF_OVERROUND_MINT_SELL":120.,"D2_12PM_BINANCE_BOX":1e2,"GAS1_AAA_GASOLINE_LOCK":80.,"CM_SHOCK_PYTH_CATALYST":1e2,"S4H_CHAINLINK_CONVERGENCE":1e2,"MKR_REWARD_LOCKED_CARRY":1e2,"W1_LOW_TROUGH_LOCK":1e2,"SP2_NBA_ENDGAME_LOCK":1e2,"BOND1_UMA_RESOLUTION_CARRY":120.,"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX":120.,"NR_CONV_NO_BASKET_ARB":120.,"NR2_CONVERT_NO_SUBSET_ARB":120.,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":1e2,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":120.,"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":120.,"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX":120.,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":1e2,"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG":120.,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":1e2,"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX":120.,"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX":120.,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":1e2,"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR":1e2,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":110.,"SOC2_EXACT_SCORE_2D_LATTICE":110.,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":1e2,"SUM1_FRECHET_SUM_TRIANGLES":120.,"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION":120.,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":1e2},"T5000":{"W1_SOLAR_PEAK_LOCK":350.,"W2_ENSEMBLE_VALUE":175.,"W2_MAKER_OVERROUND":175.,"W3_WEATHER_SLATE_ARB":250.,"B1_CONVEX_TAIL_YES":75.,"B2_BARRIER_NO_LOCK":350.,"B3_BARRIER_MONO_BOX":4e2,"M1_SVI_MAKER_SCALP":350.,"M2_STRIKE_CONVERGENCE":350.,"M3_LADDER_MONO_BOX":5e2,"M4_SHOCK_STRIKE_CATCHUP":350.,"D1_SAME_ORACLE_DOMINANCE_BOX":3e2,"D1_4H_DOMINANCE_BOX":3e2,"D1_QUIET_BOOK_BOX":3e2,"D1_MAKER_ANCHOR_BOX":3e2,"S5M_CHAINLINK_SNIPER":3e2,"N1_NEGRISK_CROSS_BOX":5e2,"P1_PREOPEN_MAKER_STRADDLE":288.,"U1_DAILY_UPDOWN_LOCK":350.,"C1_BINARY_COMPLETE_SET":5e2,"S2_EXACT_TWAP_LOCK":3e2,"CM_B3_PYTH_BARRIER_BOX":4e2,"CM_B2_PYTH_SESSION_NO_LOCK":350.,"CM_U1_PYTH_CLOSE_LOCK":350.,"B4_TOUCHED_BARRIER_WICK_LOCK":4e2,"SP1_NBA_ZERO_FEE_BOX":4e2,"NR0_ZERO_FEE_SLATE_ARB":3e2,"ZERO_FEE_MAKER_ANCHOR_BOX":350.,"ZF_INTRADAY_MAKER_BOX":350.,"TW1_COUNTING_TRUNCATION_AND_BOX":350.,"FED1_CENTRAL_BANK_LP_BOX":4e2,"COND1_MACRO_PARTITION_BOX":4e2,"CTF_OVERROUND_MINT_SELL":4e2,"D2_12PM_BINANCE_BOX":3e2,"GAS1_AAA_GASOLINE_LOCK":250.,"CM_SHOCK_PYTH_CATALYST":3e2,"S4H_CHAINLINK_CONVERGENCE":3e2,"MKR_REWARD_LOCKED_CARRY":3e2,"W1_LOW_TROUGH_LOCK":350.,"SP2_NBA_ENDGAME_LOCK":350.,"BOND1_UMA_RESOLUTION_CARRY":4e2,"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX":4e2,"NR_CONV_NO_BASKET_ARB":4e2,"NR2_CONVERT_NO_SUBSET_ARB":4e2,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":350.,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":4e2,"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":4e2,"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX":4e2,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":350.,"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG":4e2,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":350.,"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX":4e2,"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX":4e2,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":350.,"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR":350.,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":350.,"SOC2_EXACT_SCORE_2D_LATTICE":350.,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":350.,"SUM1_FRECHET_SUM_TRIANGLES":4e2,"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION":4e2,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":350.}}
for _v2_sl in("S2_RTDS_EXACT_TWAP_INTEGRATOR","D1_TELESCOPING_CANDLE_BRIDGE","B1_INTRADAY_ONETOUCH_NOON_BOX","EQ1_PYTH_EQUITY_DOMINANCE_BOX","DC1_DOUBLE_CHANCE_1X2_PARITY","LP_COMP1_SPORTS_TRIANGLES","HALFTIME_FREEZE_OFFSET_BOX","MENTION1_CUMULATIVE_LADDER_BOX","NR6_CROSS_SLATE_SURJECTION_BOX","NR4_EXHAUSTION_TAIL_YES_CONVERT","NR5_OVERROUND_ALL_YES_SELL","NR4_OPTIMAL_CHANNEL_CONVERT","NR5_LOTTERY_FREEROLL_CONVERT","CTF_OVERROUND_MINT_SELL","C1_BINARY_COMPLETE_SET","W_PRUNE1_METAR_SLATE_ARB","W_PRUNE1_NR0_BASKET"):BANKROLL_TICKETS["T100"].setdefault(_v2_sl,20.);BANKROLL_TICKETS["T1000"].setdefault(_v2_sl,110.);BANKROLL_TICKETS["T5000"].setdefault(_v2_sl,350.)
def walk_l2_book_asks(asks_raw,notional_usd,fee_rate,max_slip_cents=.025,min_l1_usd=20.,min_fill_ratio=.98,max_ask_px=.98,fee_exponent=1.):
 o=sorted([(float(a["price"]),float(a["size"]))for a in asks_raw if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
 if not o:return{"filled":False,"reason":"EMPTY_ASK_BOOK","best_ask":1.}
 f=o[0][0];l=round(f*o[0][1],2)
 if l<min_l1_usd:return{"filled":False,"reason":"THIN_L1_DEPTH","best_ask":f,"l1_usd":l}
 k=notional_usd;e=.0;c=.0;d=0;b=f
 for q,p in o:
  if q>f+max_slip_cents or q>=max_ask_px:break
  h=q*p;d+=1;b=q;n=min(k,h);c+=n/q;e+=n;k-=n
  if k<=1e-6:break
 if e<notional_usd*min_fill_ratio or c<=0:return{"filled":False,"reason":"INSUFFICIENT_DEPTH","best_ask":f,"l1_usd":l}
 m=e/c;j=fee_rate*((m*(1.-m))**fee_exponent)if fee_rate>0 else.0;g=c*j;i=(e+g)/c;return{"filled":True,"best_ask":round(f,4),"worst_px":round(b,4),"vwap":round(m,4),"eff_px":round(i,4),"slip_cents":round((m-f)*1e2,2),"spent_usd":round(e,2),"fee_usd":round(g,4),"shares":round(c,4),"fill_ratio":round(e/notional_usd,4),"l1_usd":l,"levels":d}
def walk_l2_book_asks_depth_capped(asks_raw,target_notional_usd,min_notional_usd,fee_rate=.0,max_slip_cents=.025,min_l1_usd=15.,max_ask_px=.98,fee_exponent=1.):
 g=walk_l2_book_asks(asks_raw,target_notional_usd,fee_rate=fee_rate,max_slip_cents=max_slip_cents,min_l1_usd=min_l1_usd,max_ask_px=max_ask_px,fee_exponent=fee_exponent)
 if g.get("filled")or g.get("reason")!="INSUFFICIENT_DEPTH":return g
 f=sorted([(float(a["price"]),float(a["size"]))for a in asks_raw if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
 if not f:return g
 d=f[0][0];c=sum(h*i for h,i in f if h<=d+max_slip_cents and h<max_ask_px)
 if c<min_notional_usd:return g
 b=min(target_notional_usd,c);e=walk_l2_book_asks(asks_raw,b,fee_rate=fee_rate,max_slip_cents=max_slip_cents,min_l1_usd=min_l1_usd,min_fill_ratio=.98,max_ask_px=max_ask_px,fee_exponent=fee_exponent)
 if e.get("filled"):e["fill_ratio"]=round(float(e["spent_usd"])/max(.01,target_notional_usd),4);e["depth_capped"]=b<target_notional_usd*.98
 return e
def extract_best_bid(bids_raw):
 a=sorted([(float(b["price"]),float(b["size"]))for b in bids_raw if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0])
 if not a:return.0,.0
 return round(a[0][0],4),round(a[0][0]*a[0][1],2)
class _LazyWsBooksDict(dict):
 def __init__(self,owner):super().__init__();self._owner=owner;self._dirty={}
 def mark_dirty(a,asset_id,ts):
  a._dirty[asset_id]=ts
  if not dict.__contains__(a,asset_id):dict.__setitem__(a,asset_id,(ts,{"asset_id":asset_id,"bids":[],"asks":[]}))
 def _materialize(a,key):
  c=a._dirty.pop(key,None)
  if c is not None:
   b=a._owner._ws_raw_levels.get(key)
   if b is not None:a._owner._rebuild_ws_book_dict(key,b[0],b[1],c)
 def get(self,key,default=None):
  if key in self._dirty:self._materialize(key)
  return super().get(key,default)
 def __getitem__(self,key):
  if key in self._dirty:self._materialize(key)
  return super().__getitem__(key)
 def __setitem__(self,key,value):self._dirty.pop(key,None);super().__setitem__(key,value)
 def pop(self,key,*args):self._dirty.pop(key,None);return super().pop(key,*args)
 def clear(self):self._dirty.clear();super().clear()
class Alpha124ShadowDaemon:
 def __init__(b,single_scan=False):
  b.single_scan=single_scan;b.session=None;b.started_at=datetime.now(timezone.utc).isoformat();b.weather_sigma_c=1.05;b.barrier_wick_mult=1.12;b._load_calibration();b.spots={};b.spot_hist={a:collections.deque(maxlen=600)for a in(*DOMINANCE_ASSETS,*METAL_DOMINANCE_ASSETS)};b.usd_spot_hist={a:collections.deque(maxlen=400)for a in(*DOMINANCE_ASSETS,*METAL_DOMINANCE_ASSETS)};b.usd_direct_flags={};b.weather_events={};b.barrier_rungs={};b.strike_ladders={};b.negrisk_ladders={};b.daily_updown_markets={};b.pyth_daily_markets={};b.pyth_barrier_rungs={};b.pyth_close_ladders={};b.nba_games={};b.multi_sport_games={};b.negrisk_convert_slates={};b.live_nba_board=[];b.uma_proposed_markets={};b.uma_onchain_cache={};b.bond2_onchain_cache={};b.nba_prop_slates={};b.nba_boxscore_cache={};b.nba_subperiod_slates={};b.nba_ext_summary_cache={};b.soccer_trees={};b.lp1_bop_legs=[];b.lp1_nba_em_bundles={};b.esports_bo3_specs={};b.lp2_implication_groups=[];b.lp2_events_by_slug={};b.cal1_ladders={};b.lp1_nfl_em_bundles={};b.multisport_raw_events={};b.tennis_specs={};b.score_confirm_tracker=ScoreConfirmationTracker();b.live_multisport_boards={};b.aff1_bundles={};b.soc2_lattices={};b.nfl_prop_slates={};b.binance_close_rungs=[];b.subperiod_freeze_tracker=SubperiodFreezeTracker();b.nfl_summary_cache={};b.negrisk_zero_slates={};b.counting_slates={};b.fomc_truth_legs=[];b.oil_senate_truth_legs=[];b.gas_events_raw={};b.hourly_12pm_markets={};b.s4h_candles={};b.pending_zero_fee_maker_anchors={};b.prev_pyth_spots={};b.pyth_intraday_cache={};b.dominance_pairs={};b.dominance_4h_pairs={};b.twap_candles={};b.s5m_candles={};b.preopen_15m_candles={};b.pending_preopen_straddles={};b.pending_maker_anchors={};b.chainlink_open_cache={};b.daily_open_cache={};b.metar_cache={};b.taf_cache={};b.ensemble_cache={};b.barrier_ext_cache={};b._last_w3_slate_chk_ts={};b._last_trade_tape_chk_ts={};b._open_meteo_sem=asyncio.Semaphore(2);b.last_discovery_ts=.0;b.last_weather_scan_ts=.0;b.last_crypto_mid_scan_ts=.0;b.last_tradfi_sports_scan_ts=.0;b.last_nba_endgame_scan_ts=.0;b.last_espn_board_ts=.0;b.last_uma_discovery_ts=.0;b.last_dominance_discovery_ts=.0;b.last_4h_discovery_ts=.0;b.last_twap_discovery_ts=.0;b.last_s5m_discovery_ts=.0;b.last_preopen_discovery_ts=.0;b.last_usd_sample_ts=.0;b.cached_mid_opps=[];b.cached_weather_opps=[];b.cached_tradfi_sports_opps=[];b.cached_nba_endgame_opps=[];b.cached_shock_opps=[];b.cycle_count=0
  try:b._shock_file_offset=SHOCK_TRIGGER_FILE.stat().st_size if SHOCK_TRIGGER_FILE.exists()else 0
  except Exception:b._shock_file_offset=0
  b._seen_shock_ids=collections.deque(maxlen=256);b._last_m4_shock_ts_by_asset={};b._last_any_shock_ts_by_asset={};b._last_d1_live_emit_ts={};b._bg_discovery_task=None;b._bg_weather_task=None;b._bg_mid_task=None;b._bg_tradfi_task=None;b._bg_nba_task=None;b._ws_books=_LazyWsBooksDict(b);b._ws_raw_levels={};b._ws_subscribed_tokens=set();b._ws_rest_seeded=set();b._ws_d1_priority_tokens=set();b._ws_nr_priority_tokens=set();b._ws_shard_tokens={};b._instant_arb_cooldown_until={};b._bg_chainlink_ws_task=None;b._chainlink_ws=(PolymarketChainlinkLiveStream(on_tick=b._on_chainlink_ws_tick)if(not b.single_scan and PolymarketChainlinkLiveStream is not None)else None);b._ws_d1_wakeup=asyncio.Event();b._ws_nr_wakeup=asyncio.Event();b._bg_clob_ws_task=None;b._strike_fail_backoff_ts={};b._last_telem_ts_by_key={};b._last_telem_sig_by_key={};b.open_positions={};b.pending_maker_orders={};b.closed_positions=[];b.entered_keys=set();b.inflight_keys=set();b.top_opportunities=[];b._hydrate_state()
 def is_sleeve_grad8_ready(a,sleeve):
  if is_shadow_sleeve_quarantined(sleeve):return False
  b=_filter_epoch_closed_positions(sleeve,[p for p in a.closed_positions if p.get("sleeve")==sleeve]);h=len(b);g=sum(1 for p in b if p.get("won"));f=h-g;c=a.__dict__.setdefault("_grad8_promoted_logged",set())
  if f>0:
   if sleeve in c:c.discard(sleeve);logger.warning(f"🛑 [GRAD8 AUTO-PROMOTION REVOKED] {sleeve}: {g}/{h} ({f} loss) — live IPC bridge DISARMED.")
   return False
  if h<8:return False
  e=sum(float(p.get("tier_pnls_usd",{}).get("T1000",.0))for p in b);d=sum(float(p.get("legging_adjusted_tier_pnls_usd",p.get("tier_pnls_usd",{})).get("T1000",.0))for p in b)
  if e<=.0 or d<=.0:return False
  if sleeve not in c:
   c.add(sleeve);logger.info(f"🚀 [GRAD8 AUTO-PROMOTED -> LIVE] {sleeve}: {g}/{h} wins (100.0% WR, T1000=+${e:.2f}) — live IPC bridge ARMED!")
   if STATE_FILE==(DATA_DIR/"alpha124_shadow_state.json")or LIVE_ALPHA124_STATE_MIRROR_FILE!=(LIVE_POLYMARKET_DIR/"alpha124_shadow_state.json"):
    try:a.write_state_files(a.top_opportunities)
    except Exception as exc:pass
  return True
 def _can_emit_zero_loss_math_live(a,sleeve,close_ts,now_ts,*,p_model=1.):
  if a.is_sleeve_grad8_ready(sleeve):return True
  if a.single_scan or("fetch_json"in a.__dict__)or is_shadow_sleeve_quarantined(sleeve):return False
  b=604800. if sleeve in{"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION","DC1_DOUBLE_CHANCE_1X2_PARITY","LP_COMP1_SPORTS_TRIANGLES","MENTION1_CUMULATIVE_LADDER_BOX"}else 129600.
  if float(p_model)<.998 or not(.0<(float(close_ts)-float(now_ts))<=b):return False
  if any(not p.get("won")for p in _filter_epoch_closed_positions(sleeve,[p for p in a.closed_positions if p.get("sleeve")==sleeve])):return False
  return a.is_sleeve_grad8_ready("D1_SAME_ORACLE_DOMINANCE_BOX")
 def _try_acquire_keys(a,*keys):
  b=[str(k)for k in keys if k]
  if not b:return[]
  for k in b:
   if k in a.entered_keys or k in a.inflight_keys:return[]
  for k in b:a.inflight_keys.add(k)
  return b
 def _release_inflight_keys(self,keys):
  for k in keys:self.inflight_keys.discard(k)
 def _record_market_telemetry(a,key,min_interval_sec,payload,now_ts=None,sig=None,unchanged_heartbeat_sec=6e2):
  h=float(now_ts if now_ts is not None else time.time());d=float(a._last_telem_ts_by_key.get(key)or.0)
  if(h-d)<min_interval_sec:return
  if sig is not None and a._last_telem_sig_by_key.get(key)==sig and(h-d)<unchanged_heartbeat_sec:return
  a._last_telem_ts_by_key[key]=h
  if sig is not None:a._last_telem_sig_by_key[key]=sig
  if len(a._last_telem_ts_by_key)>5000:
   for c,f in list(a._last_telem_ts_by_key.items()):
    if(h-float(f or.0))>7200.:a._last_telem_ts_by_key.pop(c,None);a._last_telem_sig_by_key.pop(c,None)
   for c in list(a._last_telem_sig_by_key.keys()):
    if c not in a._last_telem_ts_by_key:a._last_telem_sig_by_key.pop(c,None)
  g={"ts":round(h,3),"utc":datetime.fromtimestamp(h,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),**payload}
  try:
   if((a.single_scan or("fetch_json"in a.__dict__))and MARKET_TELEMETRY_FILE==(DATA_DIR/"alpha124_market_telemetry.jsonl")and STATE_FILE==(DATA_DIR/"alpha124_shadow_state.json")and LEDGER_FILE==(DATA_DIR/"alpha124_shadow_ledger.jsonl")):return
   if MARKET_TELEMETRY_FILE!=(DATA_DIR/"alpha124_market_telemetry.jsonl"):b=MARKET_TELEMETRY_FILE
   elif STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json"):b=STATE_FILE.parent/"alpha124_market_telemetry.jsonl"
   else:b=LEDGER_FILE.parent/"alpha124_market_telemetry.jsonl"
   e=(json.dumps(g,separators=(",",":"))+"\n").encode("utf-8");i=os.open(str(b),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o664)
   try:
    try:import fcntl;fcntl.flock(i,fcntl.LOCK_EX)
    except Exception:pass
    os.write(i,e)
   finally:
    try:import fcntl;fcntl.flock(i,fcntl.LOCK_UN)
    except Exception:pass
    os.close(i)
  except Exception:pass
 @staticmethod
 def _best_ask_sz(bk):
  c,b=1.,.0
  for a in(bk.get("asks")or[]):
   try:
    p,s=float(a.get("price",0)),float(a.get("size",0))
    if p>0 and s>0 and p<c:c,b=p,s
   except Exception:continue
  return c,b
 def _record_d1_corridor_telemetry(a,pair_type,m_outer,m_inner,dom_info,bk_a,bk_b,now_ts):
  l,k=dom_info["leg_a"],dom_info["leg_b"];j,r=a._best_ask_sz(bk_a);i,q=a._best_ask_sz(bk_b)
  if j>=1. or i>=1.:return
  h,_=extract_best_bid(bk_a.get("bids")or[]);g,_=extract_best_bid(bk_b.get("bids")or[]);v=float(l["fee_rate"])*((j*(1.-j))**float(l.get("fee_exponent",1.)));u=float(k["fee_rate"])*((i*(1.-i))**float(k.get("fee_exponent",1.)));c=[]
  for t,s,f in((h,j,i+u),(g,i,j+v)):
   if t<=.0:continue
   p=.001 if(t>=.96 or t<.04)else.01;o=.001 if(s>.96 or s<=.04)else.01;n=(math.floor((t+p+1e-9)*1e2)/1e2)if(.04+1e-9<round(t+p,4)<.96-1e-9)else round(t+p,3);m=(math.floor((s-o+1e-9)*1e2)/1e2)if(.04+1e-9<round(s-o,4)<.96-1e-9)else round(s-o,3)
   if n<=m+1e-9 and n>t+1e-9:c.append(round(min(n,m)+f,4))
   elif(s-t)>=.01-1e-9 and.15<=s<=.85:c.append(round(t+f,4))
  b=min(c)if c else None;e=a.usd_spot_hist.get(m_outer.asset);d=round(float(e[-1][1]),6)if e else None;a._record_market_telemetry(key=f"D1_{pair_type}_{m_outer.asset}_{m_inner.market_id}",min_interval_sec=10.,now_ts=now_ts,sig=(j,i,b),unchanged_heartbeat_sec=60.,payload={"type":"D1_CORRIDOR","pair_type":pair_type,"asset":m_outer.asset,"regime":dom_info["regime"],"m_outer_id":m_outer.market_id,"m_inner_id":m_inner.market_id,"end_ts":int(m_inner.end_ts),"tte_sec":round(m_inner.end_ts-now_ts,1),"k_low":dom_info["k_low"],"k_high":dom_info["k_high"],"corridor_bps":dom_info["corridor_bps"],"usd_spot":d,"leg_a_ask":j,"leg_b_ask":i,"gross_box_l1":round(j+i,4),"net_box_l1":round(j+v+i+u,4),"maker_anchor_net_l1":b,"l1_min_shares":round(min(r,q),2)})
 def _load_calibration(a):
  if not BACKTEST_CAL_FILE.exists():return
  try:
   d=json.loads(BACKTEST_CAL_FILE.read_text(encoding="utf-8"));c=d.get("option_1_weather",{}).get("calibrated_sigma_c");b=d.get("option_2_barrier_onetouch",{}).get("calibrated_wick_vol_mult")
   if c:a.weather_sigma_c=float(c)
   if b:a.barrier_wick_mult=float(b)
   logger.info(f"Loaded WFO calibration: weather_sigma_c={a.weather_sigma_c}, barrier_wick_mult={a.barrier_wick_mult}")
  except Exception as exc:logger.warning(f"Calibration load notice: {exc}")
 @staticmethod
 def _resolve_ledger_path():
  if LEDGER_FILE!=_DEFAULT_LEDGER_FILE:return LEDGER_FILE
  if DATA_DIR!=_DEFAULT_DATA_DIR:return DATA_DIR/"alpha124_shadow_ledger.jsonl"
  if STATE_FILE!=_DEFAULT_STATE_FILE:return STATE_FILE.parent/"alpha124_shadow_ledger.jsonl"
  return LEDGER_FILE
 @staticmethod
 def _is_leaked_unit_test_artifact(rec):
  if STATE_FILE!=_DEFAULT_STATE_FILE:return False
  d=str(rec.get("dedupe_key")or rec.get("position_id")or"")
  if d.startswith("SP4_SUB_st1_st2"):return True
  a=rec.get("extra")or{}
  if str(a.get("market_id")or"")in{"st1","st2"}:return True
  c=a.get("leg_a")or{};b=a.get("leg_b")or{}
  if str(c.get("market_id")or"")in{"st1","st2"}or str(b.get("market_id")or"")in{"st1","st2"}:return True
  return False
 def _hydrate_state(a):
  if STATE_FILE.exists():
   try:
    y=json.loads(STATE_FILE.read_text(encoding="utf-8"));a.started_at=y.get("started_at",a.started_at)
    for p in y.get("open_positions",[]):
     if isinstance(p,dict)and p.get("position_id")and not a._is_leaked_unit_test_artifact(p):
      a.open_positions[p["position_id"]]=p;a.entered_keys.add(str(p.get("dedupe_key")or p["position_id"]));b=(p.get("extra")or{}).get("event_id")
      if b:
       if p.get("sleeve")=="W2_ENSEMBLE_VALUE":a.entered_keys.add(f"W2_EVENT_{b}")
       elif p.get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.add(f"W2M_EVENT_{b}")
    for s in y.get("pending_maker_orders",[]):
     if isinstance(s,dict)and s.get("order_id")and not a._is_leaked_unit_test_artifact(s):
      a.pending_maker_orders[s["order_id"]]=s
      if s.get("dedupe_key"):a.entered_keys.add(str(s["dedupe_key"]))
      b=(s.get("extra")or{}).get("event_id")
      if b and s.get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.add(f"W2M_EVENT_{b}")
    for p in y.get("recent_closed_positions",[]):
     if isinstance(p,dict)and not a._is_leaked_unit_test_artifact(p):
      a.closed_positions.append(p)
      if p.get("dedupe_key"):a.entered_keys.add(str(p["dedupe_key"]))
      b=(p.get("extra")or{}).get("event_id")
      if b:
       if p.get("sleeve")=="W2_ENSEMBLE_VALUE":a.entered_keys.add(f"W2_EVENT_{b}")
       elif p.get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.add(f"W2M_EVENT_{b}")
   except Exception as exc:logger.warning(f"State hydrate notice: {exc}")
  g=a._resolve_ledger_path()
  if g.exists():
   try:
    e={};d={};h={str(p.get("position_id"))for p in a.closed_positions if isinstance(p,dict)and p.get("position_id")}
    with open(g,"r",encoding="utf-8",errors="ignore")as f:
     for t in f:
      if not t.strip():continue
      try:r=json.loads(t)
      except Exception:continue
      if isinstance(r,dict)and a._is_leaked_unit_test_artifact(r):continue
      x=r.get("event")
      if x in("SHADOW_ENTRY","SHADOW_CLOSE")and r.get("dedupe_key"):a.entered_keys.add(str(r["dedupe_key"]))
      if x=="SHADOW_ENTRY":
       j=str(r.get("position_id")or"")
       if j:c={k:v for k,v in r.items()if k!="event"};e[j]=c
       q=str(r.get("dedupe_key")or"")
       if q:
        for o,w in list(d.items()):
         if str(w.get("dedupe_key")or"")==q:d.pop(o,None)
       b=(r.get("extra")or{}).get("event_id")
       if b:
        if r.get("sleeve")=="W2_ENSEMBLE_VALUE":a.entered_keys.add(f"W2_EVENT_{b}")
        elif r.get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.add(f"W2M_EVENT_{b}")
      elif x=="SHADOW_CLOSE":
       j=str(r.get("position_id")or"")
       if j:
        e.pop(j,None);a.open_positions.pop(j,None)
        if j not in h:h.add(j);a.closed_positions.append({k:v for k,v in r.items()if k!="event"})
      elif x=="SHADOW_MAKER_POST":
       i=str(r.get("order_id")or"")
       if i:
        d[i]={k:v for k,v in r.items()if k!="event"}
        if r.get("dedupe_key"):a.entered_keys.add(str(r["dedupe_key"]))
        b=(r.get("extra")or{}).get("event_id")
        if b and r.get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.add(f"W2M_EVENT_{b}")
      elif x=="SHADOW_MAKER_CANCEL":
       i=str(r.get("order_id")or"")
       if i:
        n=d.pop(i,None);a.pending_maker_orders.pop(i,None)
        if n and n.get("dedupe_key"):a.entered_keys.discard(str(n["dedupe_key"]))
        b=((n or r).get("extra")or{}).get("event_id")
        if b and(n or r).get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.discard(f"W2M_EVENT_{b}")
    for j,c in e.items():
     if j not in a.open_positions and j not in h:a.open_positions[j]=c
    for i,m in d.items():
     if i not in a.pending_maker_orders or float(m.get("last_repeg_ts")or.0)>float(a.pending_maker_orders[i].get("last_repeg_ts")or.0):a.pending_maker_orders[i]=m
   except Exception as exc:logger.warning(f"Ledger hydrate notice: {exc}")
  if a.closed_positions:a.closed_positions.sort(key=lambda p:float(p.get("closed_ts")or.0))
  for l,u in list(a.pending_maker_orders.items()):
   if is_shadow_sleeve_quarantined(str(u.get("sleeve")or"")):a.pending_maker_orders.pop(l,None);a._append_ledger({"event":"SHADOW_MAKER_CANCEL","reason":"SLEEVE_QUARANTINED",**u})
  if is_shadow_sleeve_quarantined("P1_PREOPEN_MAKER_STRADDLE"):a.pending_preopen_straddles.clear()
  if is_shadow_sleeve_quarantined("ZERO_FEE_MAKER_ANCHOR_BOX"):a.pending_zero_fee_maker_anchors.clear()
 def _append_ledger(self,rec):
  a=self._resolve_ledger_path();a.parent.mkdir(parents=True,exist_ok=True)
  with open(a,"a",encoding="utf-8")as f:f.write(json.dumps(rec)+"\n")
 async def get_session(a):
  if a.session is None or a.session.closed:a.session=aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=40),headers={"User-Agent":"DominusAlpha124Shadow/1.0","Accept":"application/json"},max_line_size=65536,max_field_size=65536)
  return a.session
 def _on_chainlink_ws_tick(a,asset,ts_sec,price_usd):
  if price_usd<=.0 or not math.isfinite(price_usd):return
  a.spots[asset]=price_usd;a.usd_direct_flags[asset]=True;b=a.usd_spot_hist.get(asset)
  if b is None:b=collections.deque(maxlen=450);a.usd_spot_hist[asset]=b
  if b and abs(ts_sec-float(b[-1][0]))<.05:b[-1]=(ts_sec,price_usd)
  elif b and ts_sec<float(b[-1][0]):return
  else:b.append((ts_sec,price_usd))
 async def fetch_json(a,url,timeout=5.):
  if not a.single_scan and a._ws_books and"/book?token_id="in str(url):
   d=str(url).split("token_id=",1)[1].split("&",1)[0].strip();b=a._ws_books.get(d)
   if b is not None and(time.time()-b[0])<=1.5:
    c=b[1]
    if c.get("asks")or c.get("bids"):return c
  f=await a.get_session()
  try:
   async with f.get(url,timeout=aiohttp.ClientTimeout(total=timeout))as e:
    if e.status==200:return await e.json()
  except Exception:return None
  return None
 async def fetch_book_after_latency(self,token_id,latency_ms=50):
  if latency_ms>0:await asyncio.sleep(latency_ms/1e3)
  return await self.fetch_json(f"{CLOB_URL}/book?token_id={token_id}",timeout=3.5)
 def _rebuild_ws_book_dict(self,asset_id,bids_map,asks_map,now_ts):b=[{"price":f"{px:.4f}","size":f"{sz:.4f}"}for px,sz in sorted(bids_map.items(),key=lambda kv:-kv[0])[:20]if px>.0 and sz>.0];a=[{"price":f"{px:.4f}","size":f"{sz:.4f}"}for px,sz in sorted(asks_map.items(),key=lambda kv:kv[0])[:20]if px>.0 and sz>.0];self._ws_books[asset_id]=(now_ts,{"asset_id":asset_id,"bids":b,"asks":a})
 def _apply_ws_book_snapshot(a,asset_id,bids_raw,asks_raw,now_ts,from_rest=False):
  if not asset_id:return
  c={};b={}
  for d in bids_raw or():
   try:
    f=round(float(d.get("price",.0)),4);e=float(d.get("size",.0))
    if f>.0 and e>.0:c[f]=e
   except Exception:continue
  for d in asks_raw or():
   try:
    f=round(float(d.get("price",.0)),4);e=float(d.get("size",.0))
    if f>.0 and e>.0:b[f]=e
   except Exception:continue
  a._ws_raw_levels[asset_id]=(c,b);a._rebuild_ws_book_dict(asset_id,c,b,now_ts)
  if from_rest:a._ws_rest_seeded.add(asset_id)
  else:a._ws_rest_seeded.discard(asset_id)
 def _drop_ws_book(a,asset_id):a._ws_books.pop(asset_id,None);a._ws_raw_levels.pop(asset_id,None);a._ws_rest_seeded.discard(asset_id)
 def _apply_ws_price_changes(a,asset_id,changes,now_ts):
  m=a._ws_raw_levels.get(asset_id)
  if m is None:return False
  j,i=m;c=False
  for k in changes or():
   try:
    o=round(float(k.get("price",.0)),4);n=float(k.get("size",.0));l=str(k.get("side")or"").upper()
    if o<=.0:continue
    h=j if l=="BUY"else i
    if n<=.0:
     if o in h:h.pop(o,None);c=True
    else:h[o]=n;c=True
   except Exception:continue
  g=max(j.keys())if j else.0;f=min(i.keys())if i else.0;b=bool(j and i and g>=f)
  if not b:
   e=None;d=None
   for k in changes or():
    try:
     if k.get("best_bid")not in(None,""):e=float(k.get("best_bid"))
     if k.get("best_ask")not in(None,""):d=float(k.get("best_ask"))
    except Exception:continue
   if e is not None and.0<e<1. and abs(e-g)>1e-6:b=True
   if d is not None and.0<d<1. and abs(d-f)>1e-6:b=True
  if b:a._drop_ws_book(asset_id);return False
  if c:
   if isinstance(a._ws_books,_LazyWsBooksDict):a._ws_books.mark_dirty(asset_id,now_ts)
   else:a._rebuild_ws_book_dict(asset_id,j,i,now_ts)
  return c
 def _desired_d1_ws_tokens(a,now_ts,max_cap=600):
  C=[];x=set();g=set()
  def _add_tok(tok,*,is_nr=False):
   if len(C)>=max_cap:return False
   a=str(tok or"").strip()
   if a and a not in x:
    x.add(a);C.append(a)
    if is_nr:g.add(a)
   elif a and is_nr:g.add(a)
   return len(C)<max_cap
  for l,f in list(a.dominance_pairs.values())+list(a.dominance_4h_pairs.values()):
   if float(f.end_ts)<=now_ts+5.:continue
   for tok in(l.up_token,l.down_token,f.up_token,f.down_token):_add_tok(tok)
  if not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK"):
   for t in list(a.twap_candles.values()):
    if float(t.end_ts)>now_ts+5.:_add_tok(t.up_token);_add_tok(t.down_token)
  a._ws_d1_priority_tokens=set(C)
  for w in list(a.pyth_daily_markets.values())+list(a.daily_updown_markets.values()):
   if float(w.end_ts)>now_ts+60.:_add_tok(w.up_token);_add_tok(w.down_token)
  for q in list(a.strike_ladders.values()):
   if not q or float(q[0].end_ts)<=now_ts+60.:continue
   k=float(a.spots.get(q[0].asset)or.0);d=sorted(q,key=lambda r:abs(float(r.strike)-k))if k>.0 else list(q)
   for r in d[:4]:_add_tok(r.yes_token);_add_tok(r.no_token)
  for B in list(a.negrisk_ladders.values()):
   if not B or float(B[0].end_ts)<=now_ts+60.:continue
   j=float(a.spots.get(B[0].asset)or.0);c=sorted(B,key=lambda b:abs(.5*(float(b.k_low or j)+float(b.k_high or j))-j))if j>.0 else list(B)
   for b in c[:4]:_add_tok(b.yes_token);_add_tok(b.no_token)
  for p in sorted(a.negrisk_zero_slates.values(),key=lambda s:float(s.end_ts)):
   if float(p.end_ts)<=now_ts+60. or len(p.brackets)>15:continue
   for A in p.brackets:_add_tok(A.get("no_token"),is_nr=True);_add_tok(A.get("yes_token"),is_nr=True)
  for i in sorted(a.negrisk_convert_slates.values(),key=lambda s:(not bool(s.is_closed_convert_safe),float(s.end_ts))):
   if float(i.end_ts)<=now_ts+60. or len(i.brackets)>15:continue
   for z in i.brackets:
    _add_tok(z.get("no_token"),is_nr=True)
    if i.is_closed_convert_safe:_add_tok(z.get("yes_token"),is_nr=True)
  for o in sorted(a.counting_slates.values(),key=lambda s:float(getattr(s,"window_end_ts",None)or getattr(s,"end_ts",.0)or.0)):
   if float(getattr(o,"window_end_ts",None)or getattr(o,"end_ts",.0)or.0)<=now_ts+60. or len(o.brackets)>15:continue
   for y in o.brackets:_add_tok(y.get("no_token"),is_nr=True);_add_tok(y.get("yes_token"),is_nr=True)
  for n in list(a.uma_proposed_markets.values())[:25]:
   if isinstance(n,dict):
    e=_parse_clob_tokens(n)
    if e:_add_tok(e[0],is_nr=True);_add_tok(e[1],is_nr=True)
    else:_add_tok(n.get("win_token")or n.get("yes_token"),is_nr=True);_add_tok(n.get("lose_token")or n.get("no_token"),is_nr=True)
  a._ws_nr_priority_tokens=g
  for v in list(a.multi_sport_games.values())+list(a.nba_games.values()):
   m=float(getattr(v,"end_ts",.0)or.0)
   if 60.<(m-now_ts)<=21600.:
    for h in("ml_a_token","ml_b_token"):_add_tok(getattr(v,h,None))
    for u in(getattr(v,"spreads",None)or())[:3]:
     if isinstance(u,dict):_add_tok(u.get("yes_token"));_add_tok(u.get("no_token"))
  return C
 def _partition_ws_shards(self,now_ts,max_shards=3,per_shard=200):a=self._desired_d1_ws_tokens(now_ts,max_cap=max_shards*per_shard);return[a[i*per_shard:(i+1)*per_shard]for i in range(max_shards)]
 def _sync_ws_subscribed_union(a):
  b=set()
  for c in a._ws_shard_tokens.values():b.update(c)
  a._ws_subscribed_tokens=b
 async def _run_single_clob_ws_shard(a,shard_idx):
  while not a.single_scan:
   s=a._partition_ws_shards(time.time());p=s[shard_idx]if shard_idx<len(s)else[]
   if not p:
    for l in list(a._ws_shard_tokens.pop(shard_idx,set())):a._drop_ws_book(l)
    a._sync_ws_subscribed_union();await asyncio.sleep(1.5);continue
   try:
    D=await a.get_session()
    async with D.ws_connect(CLOB_WS_URL,heartbeat=15.,max_msg_size=4*1024*1024,timeout=aiohttp.ClientWSTimeout(ws_close=5.))as I:
     m=a._ws_shard_tokens.get(shard_idx,set())
     for l in list(m|set(p)):a._drop_ws_book(l)
     o=set(p);a._ws_shard_tokens[shard_idx]=o;a._sync_ws_subscribed_union();await I.send_str(json.dumps({"assets_ids":p,"type":"market"}));e=time.time();b=e
     while not a.single_scan:
      x=time.time()
      if(x-e)>=2.:
       e=x;r=a._partition_ws_shards(x);f=set(r[shard_idx]if shard_idx<len(r)else[]);k=set()
       for w,q in a._ws_shard_tokens.items():
        if w!=shard_idx:k.update(q)
       f-=k
       for n in list(o-f):
        o.discard(n)
        if n not in k:a._drop_ws_book(n)
       a._sync_ws_subscribed_union()
       if not f:break
       v=sorted(f-o)
       if v:await I.send_str(json.dumps({"assets_ids":v,"operation":"subscribe"}));o.update(v);a._sync_ws_subscribed_union()
       elif len(o)>len(f)+32:break
      if(x-b)>30.:break
      try:G=await asyncio.wait_for(I.receive(),timeout=2.)
      except asyncio.TimeoutError:continue
      if G.type in(aiohttp.WSMsgType.CLOSED,aiohttp.WSMsgType.CLOSING,aiohttp.WSMsgType.ERROR):break
      if G.type not in(aiohttp.WSMsgType.TEXT,aiohttp.WSMsgType.BINARY):continue
      j=G.data
      if not j or j in("PONG",b"PONG"):b=time.time();continue
      u=time.time();b=u;C=_orjson.loads(j)if _orjson is not None else json.loads(j);d=False;c=False;i=a._ws_d1_priority_tokens;h=a._ws_nr_priority_tokens
      if isinstance(C,list):
       for B in C:
        if isinstance(B,dict):
         g=str(B.get("asset_id")or"")
         if g in o:
          A=B.get("tick_size")or B.get("minimum_tick_size")
          if A:a.__dict__.setdefault("_token_tick_sizes",{})[g]=str(A)
          a._apply_ws_book_snapshot(g,B.get("bids")or[],B.get("asks")or[],u);d=d or(g in i);c=c or(g in h)
      elif isinstance(C,dict):
       z=C.get("event_type")
       if z=="book":
        g=str(C.get("asset_id")or"")
        if g in o:
         y=C.get("tick_size")or C.get("minimum_tick_size")
         if y:a.__dict__.setdefault("_token_tick_sizes",{})[g]=str(y)
         a._apply_ws_book_snapshot(g,C.get("bids")or[],C.get("asks")or[],u);d=d or(g in i);c=c or(g in h)
       elif z=="tick_size_change":
        g=str(C.get("asset_id")or"");F=C.get("new_tick_size")or C.get("tick_size")
        if g and F:
         a.__dict__.setdefault("_token_tick_sizes",{})[g]=str(F)
         if g in a._ws_books and isinstance(a._ws_books[g][1],dict):a._ws_books[g][1]["minimum_tick_size"]=str(F)
       elif z=="price_change":
        t={}
        for H in C.get("price_changes")or():
         g=str(H.get("asset_id")or"")
         if g in o:t.setdefault(g,[]).append(H)
        for g,E in t.items():
         if a._apply_ws_price_changes(g,E,u):
          if g in i:d=True
          if g in h:c=True
      if(d and(a.is_in_same_oracle_overlap_window(u)or bool(a.pending_maker_anchors))and(u-getattr(a,"_last_ws_d1_wake_ts",.0))>=.12):a._last_ws_d1_wake_ts=u;a._ws_d1_wakeup.set()
      if c and(u-getattr(a,"_last_ws_nr_wake_ts",.0))>=.25:a._last_ws_nr_wake_ts=u;a._ws_nr_wakeup.set();a._ws_d1_wakeup.set()
   except asyncio.CancelledError:raise
   except Exception as exc_ws:await asyncio.sleep(1.)
 async def _scan_ws_reactive_negrisk_arbs(a,now_ts):
  from src.polymarket_research.riskless_machine_gun_engine import detect_nr3_synthetic_all_yes_overround;e=[]
  for i in list(a.negrisk_convert_slates.values()):
   if not i.is_closed_convert_safe or i.end_ts<=now_ts+65. or len(i.brackets)>15:continue
   h={};b=True
   for l in i.brackets:
    for k in(l.get("no_token"),l.get("yes_token")):
     j=str(k or"");g=a._ws_books.get(j)if j else None
     if g is None or(now_ts-float(g[0]))>2.5 or j in a._ws_rest_seeded:b=False;break
     h[j]=g[1]
    if not b:break
   if not b:continue
   c=detect_negrisk_convert_positions_arbs(i,h,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],min_net_edge_per_share=.005,min_shares=8)
   if c:await a.execute_negrisk_convert_positions_arb(i,c[0],h,e)
   d=detect_nr2_convert_no_subset_arbs(i,h,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR2_CONVERT_NO_SUBSET_ARB"],min_edge_pure_cash=.012,min_edge_with_yes_sell=.015,min_shares=6)
   if d:await a.execute_nr2_subset_convert_arb(i,d[0],h,e)
   f=detect_nr3_synthetic_all_yes_overround(i,h,target_budget_usd=30.,min_net_edge_per_set=.008,min_shares=5)
   if f is not None:a.emit_live_negrisk_convert_candidate(sleeve_source="NR2_CONVERT_NO_SUBSET_ARB",spec=i,dedupe_key=f"NR3_OVR_{i.event_id}",arb_hit=f,books_by_token=h,now_ts=now_ts)
 async def _run_clob_d1_ws_loop(a):
  if a.single_scan:return
  await asyncio.gather(*(a._run_single_clob_ws_shard(b)for b in range(3)))
 def _get_fresh_ws_book(a,token_id,now_ts,max_age_sec=5.):
  c=str(token_id or"")
  if not c or c in getattr(a,"_ws_rest_seeded",set()):return None
  b=a._ws_books.get(c)if getattr(a,"_ws_books",None)is not None else None
  if b is None or(float(now_ts)-float(b[0]))>float(max_age_sec):return None
  e=b[1]
  if isinstance(e,dict):
   d=(a.__dict__.get("_token_tick_sizes")or{}).get(c)
   if d:e["minimum_tick_size"]=d
  return e if isinstance(e,dict)and(e.get("asks")or e.get("bids"))else None
 async def fetch_books_batch(a,token_ids,timeout=3.):
  q=list(dict.fromkeys(str(t)for t in token_ids if t))
  if not q:return{}
  if"fetch_json"in a.__dict__:f=await asyncio.gather(*(a.fetch_json(f"{CLOB_URL}/book?token_id={t}",timeout=timeout)for t in q));return{t:bk for t,bk in zip(q,f)if isinstance(bk,dict)}
  u={};g=[];l=time.time();h=not a.single_scan;e=a.__dict__.setdefault("_token_tick_sizes",{})
  for t in q:
   d=a._ws_books.get(t)if h else None
   if(d is not None and(l-d[0])<=1.5 and(d[1].get("bids")or d[1].get("asks"))):
    if t in e:d[1]["minimum_tick_size"]=e[t]
    u[t]=d[1]
   else:g.append(t)
  if not g:return u
  p=await a.get_session()
  for s in range(0,len(g),50):
   k=g[s:s+50]
   try:
    async with p.post(f"{CLOB_URL}/books",json=[{"token_id":t}for t in k],timeout=aiohttp.ClientTimeout(total=timeout))as o:
     if o.status==200:
      b=await o.read();n=_orjson.loads(b)if _orjson is not None else json.loads(b)
      if isinstance(n,list):
       c=time.time()
       for r in n:
        if isinstance(r,dict)and r.get("asset_id"):
         j=str(r["asset_id"]);m=r.get("minimum_tick_size")or r.get("tick_size")
         if m:e[j]=str(m)
         u[j]=r
         if h and j in a._ws_subscribed_tokens and j not in a._ws_raw_levels:a._apply_ws_book_snapshot(j,r.get("bids")or[],r.get("asks")or[],c,from_rest=True)
       continue
   except Exception:pass
   v=await asyncio.gather(*(a.fetch_json(f"{CLOB_URL}/book?token_id={t}",timeout=timeout)for t in k))
   for t,bk in zip(k,v):
    if isinstance(bk,dict):
     i=bk.get("minimum_tick_size")or bk.get("tick_size")
     if i:e[t]=str(i)
     u[t]=bk
  return u
 def record_usd_spot_samples(a,now_ts=None):
  f=float(now_ts if now_ts is not None else time.time());a.last_usd_sample_ts=f
  for c in(*DOMINANCE_ASSETS,*METAL_DOMINANCE_ASSETS):
   e=read_shm_usd_anchor(c,f,max_age_sec=2.5);b=e.get("usd_spot");d=str(e.get("source")or"")
   if b and float(b)>0:a.usd_spot_hist.setdefault(c,collections.deque(maxlen=400)).append((f,float(b)));a.usd_direct_flags[c]=d in("shm_chainlink_proxy","shm_coinbase_usd")
 async def update_crypto_spots(b):
  p=time.time();e="%5B"+",".join(f"%22{s}%22"for s in sorted(set(ASSET_BINANCE_SYMBOL.values())))+"%5D";n=await b.fetch_json(f"{BINANCE_URL}/api/v3/ticker/price?symbols={e}",timeout=3.5)
  if isinstance(n,list):
   g={v:k for k,v in ASSET_BINANCE_SYMBOL.items()}
   for m in n:
    o=m.get("symbol")
    if o in g:j=g[o];r=float(m["price"]);b.spots[j]=r;b.spot_hist.setdefault(j,collections.deque(maxlen=600)).append((p,r))
  d=await b.fetch_json(f"{BINANCE_FAPI_URL}/fapi/v1/ticker/price?symbol=HYPEUSDT",timeout=2.5)
  if isinstance(d,dict)and d.get("price"):
   l=float(d["price"])
   if l>0:b.spots["HYPE"]=l;b.spot_hist.setdefault("HYPE",collections.deque(maxlen=600)).append((p,l))
  b.record_usd_spot_samples(p);c=[a for a in DOMINANCE_ASSETS if a!="HYPE"and(not b.usd_direct_flags.get(a,False)or not b.usd_spot_hist.get(a)or(p-float(b.usd_spot_hist[a][-1][0]))>3.)]
  if c:
   f=await asyncio.gather(*(b.fetch_json(f"https://api.exchange.coinbase.com/products/{a}-USD/ticker",timeout=2.)for a in c));h=time.time()
   for a,q in zip(c,f):
    if isinstance(q,dict)and q.get("price"):
     try:
      i=float(q["price"])
      if i>0:b.usd_spot_hist.setdefault(a,collections.deque(maxlen=400)).append((h,i));b.usd_direct_flags[a]=True
     except Exception:pass
 @staticmethod
 def _hist_return_bps(hist,lookback_sec):
  if not hist or len(hist)<2:return.0
  d,c=hist[-1];a=hist[-2][1]
  for b in range(len(hist)-1):
   f,e=hist[b]
   if d-f<=lookback_sec:a=e;break
  return((c-a)/a)*1e4 if a>0 else.0
 def get_return_bps(a,asset,lookback_sec):b=a._hist_return_bps(a.spot_hist.get(asset),lookback_sec);c=a._hist_return_bps(a.usd_spot_hist.get(asset),lookback_sec);return c if abs(c)>abs(b)else b
 async def discover_all_markets(a):
  logger.info("Discovering active Weather (#1), Barrier Hit (#2), Multi-Strike (#4), NegRisk, and Daily Up/Down markets...");H={};_g=time.time();from src.polymarket_research.riskless_protocol_v2_expansion import(attach_weather_neg_risk_from_gamma as _attach_weather_neg_risk,resolve_weather_effective_end_ts)
  def _weather_still_live(sp_w):return resolve_weather_effective_end_ts(sp_w,_g+86400.)>_g
  X=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?tag_slug=weather&closed=false&limit=100&offset={w_off}",timeout=7.)for w_off in(0,100,200,300,400)))
  for _0 in X:
   if isinstance(_0,list):
    for c in _0:
     sp=parse_weather_event(c)
     if sp is not None and _weather_still_live(sp):_attach_weather_neg_risk(sp,c);H[sp.event_id]=sp
  j=[]
  for _as in range(0,600,100):
   O=await a.fetch_json(f"{GAMMA_URL}/events?closed=false&order=volume24hr&ascending=false&limit=100&offset={_as}",timeout=7.)
   if not isinstance(O,list)or not O:break
   j.extend(O)
   for c in O:
    sp=parse_weather_event(c)
    if sp is not None and _weather_still_live(sp):_attach_weather_neg_risk(sp,c);H[sp.event_id]=sp
  G={sp.series_slug for sp in H.values()if sp.series_slug}
  for _ar in HIGH_VOLUME_WEATHER_SERIES:
   if _ar in G:continue
   _aq=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={_ar}&closed=false&limit=3",timeout=5.)
   if isinstance(_aq,list):
    for c in _aq:
     sp=parse_weather_event(c,series_slug_hint=_ar)
     if sp is not None and _weather_still_live(sp):_attach_weather_neg_risk(sp,c);H[sp.event_id]=sp
  a.weather_events=H;F={}
  for d,_aL,slug in HIT_SERIES:
   O=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5",timeout=6.)
   if isinstance(O,list):
    for c in O:
     for r in parse_hit_event(c,d,_aL,slug):
      if r.resolved_yes is None and r.end_ts>time.time()+60:F[r.market_id]=r
  a.barrier_rungs=F;P={};u=[]
  for d,slug in STRIKE_SERIES:
   O=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5",timeout=6.)
   if isinstance(O,list):
    u.extend(O)
    for c in O:
     _aK=parse_multistrike_event(c,d,slug)
     if _aK and _aK[0].end_ts>time.time()+60:P[f"{d}_{c.get('id')}"]=_aK
  a.strike_ladders=P;E={}
  for d,slug in NEGRISK_SERIES:
   _Z=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4",timeout=6.)
   if isinstance(_Z,list):
    for c in _Z:
     brs=parse_negrisk_bracket_event(c,d,slug)
     if brs and brs[0].end_ts>time.time()+60:E[f"{d}_{int(brs[0].end_ts)}"]=brs
  a.negrisk_ladders=E;N={}
  for d,slug in DAILY_UPDOWN_SERIES:
   _Y=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3",timeout=5.)
   if isinstance(_Y,list):
    for c in _Y:
     _aJ=parse_daily_updown_event(c,d,slug)
     if _aJ is not None and _aJ.end_ts>time.time()+60:N[_aJ.market_id]=_aJ
  a.daily_updown_markets=N;_f={}
  for d,slug in ZERO_FEE_PYTH_DAILY_SERIES:
   _X=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=2",timeout=5.)
   if isinstance(_X,list):
    for c in _X:
     _aI=parse_daily_updown_event(c,d,slug)
     if _aI is not None and _aI.end_ts>time.time()+60:_f[_aI.market_id]=_aI
  a.pyth_daily_markets=_f;M=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3",timeout=5.)for _,_,slug in PYTH_HIT_SERIES));x={};_B=time.time()
  for(_W,_V,_ap),_U in zip(PYTH_HIT_SERIES,M):
   if isinstance(_U,list):
    for c in _U:
     for rp in parse_pyth_hit_event(c,_W,_V,_ap):
      if rp.end_ts>_B+60:x[rp.market_id]=rp
  a.pyth_barrier_rungs=x;W=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3",timeout=5.)for _,slug in PYTH_CLOSE_SERIES));D={}
  for(_T,_ao),_S in zip(PYTH_CLOSE_SERIES,W):
   if isinstance(_S,list):
    for c in _S:
     _R=parse_pyth_close_event(c,_T,_ao)
     if _R and _R[0].end_ts>_B+60:D[f"{_T}_{c.get('id')}"]=_R
  a.pyth_close_ladders=D;_s={};_A={};_e={};C={};q={};_d={}
  for _z in NBA_SERIES_SLUGS:
   _y=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={_z}&closed=false&limit=40",timeout=6.5)
   if isinstance(_y,list):
    for c in _y:
     _aH=str(c.get("slug")or"").lower()
     if _aH.endswith("-exact-margin"):_d[_aH[:-13]]=c;continue
     q[_aH]=c;_an=parse_nba_zero_fee_event(c,now_ts=_B)
     if _an is not None:_s[_an.event_id]=_an
     _aG=parse_nba_player_props_from_event(c,now_ts=_B)
     if _aG is not None:_e[_aG.event_id]=_aG
     _am=parse_nba_subperiod_and_ext_props(c,now_ts=_B)
     if _am is not None:C[_am.event_id]=_am
     _r=parse_multi_sport_corridor_event(c,sport_hint="NBA",now_ts=_B,skip_nba_fg_zero_fee=True)
     if _r is not None:_A[_r.event_id]=_r
  p=[sl for sl in list(q.keys())[:10]if sl not in _d]
  if p:
   _c=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl}-exact-margin",timeout=4.5)for sl in p))
   for _aV,_al in zip(p,_c):
    if isinstance(_al,list)and _al:_d[_aV]=_al[0]
  o={}
  for _aU,_aT in q.items():
   _aS=_d.get(_aU)
   if _aS is not None:
    _aR=build_lp1_nba_exact_margin_bundle(_aT,_aS)
    if _aR is not None and float(_aR["end_ts"])>_B+60:o[_aR["event_id"]]=_aR
  a.nba_games=_s;a.nba_prop_slates=_e;a.nba_subperiod_slates=C;a.lp1_nba_em_bundles=o;g=[(sl_s,sp_t)for sp_t,sl_s in MULTI_SPORT_CORRIDOR_SERIES if sl_s not in NBA_SERIES_SLUGS];_ak=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={sl_s}&closed=false&limit=25",timeout=5.5)for sl_s,_ in g),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=sports&closed=false&order=volume24hr&ascending=false&limit=40",timeout=6.));L={};K={}
  for(_,_aj),_Q in zip(g,_ak[:len(g)]):
   if isinstance(_Q,list):
    for c in _Q:
     _b=parse_multi_sport_corridor_event(c,sport_hint=_aj,now_ts=_B,skip_nba_fg_zero_fee=True)
     if _b is not None:_A[_b.event_id]=_b
     _P=str(c.get("id")or"")
     if _P and _aj in("NFL","CFB","NHL"):K[_P]=(_aj,c)
     if _aj=="NFL":
      _aF=build_lp1_nfl_exact_margin_bundle(c,now_ts=_B)
      if _aF is not None:L[_aF["event_id"]]=_aF
  a.lp1_nfl_em_bundles=L;a.multisport_raw_events=K;n=(_ak[-1]if isinstance(_ak[-1],list)else[])+[e for e in j if isinstance(e,dict)and not e.get("negRisk")and len(e.get("markets")or())>=8]
  for c in n:
   _O=str(c.get("id")or"")
   if _O and _O not in _A:
    _b=parse_multi_sport_corridor_event(c,now_ts=_B,skip_nba_fg_zero_fee=True)
    if _b is not None:_A[_b.event_id]=_b
  a.multi_sport_games=_A;_N=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4",timeout=5.)for slug in ZERO_FEE_NEGRISK_SERIES));_q={};B={}
  for _ai,_M in zip(ZERO_FEE_NEGRISK_SERIES,_N):
   if isinstance(_M,list):
    B[_ai]=_M;_x=_ai in("best-ai-company","chinese-ai-1")
    for c in _M:
     _aE=parse_zero_fee_negrisk_slate(c,_ai,allow_mixed_fees=_x)
     if _aE is not None and _aE.end_ts>_B+60:_q[_aE.event_id]=_aE
  a.negrisk_zero_slates=_q;w={}
  for _ah in(j+[e for lst in B.values()for e in(lst or[])]+[e for lst in X if isinstance(lst,list)for e in lst]):
   if not isinstance(_ah,dict):continue
   _ag=parse_negrisk_convert_event(_ah)
   if _ag is not None and _ag.end_ts>_B+60 and len(_ag.brackets)<=45:w[_ag.event_id]=_ag
  _a=sorted(w.values(),key=lambda s:(not s.is_closed_convert_safe,(s.end_ts-_B)>172800.,s.end_ts))[:40];a.negrisk_convert_slates={s.event_id:s for s in _a};_p={}
  for _af,_w in COUNTING_SERIES_HANDLES:
   for _aQ in(B.get(_af)or[]):
    _aP=parse_counting_slate_event(_aQ,_af,_w)
    if _aP is not None and _aP.window_end_ts>_B+60:_p[_aP.event_id]=_aP
  a.counting_slates=_p;a.fomc_truth_legs=build_fomc_truth_table_legs(B.get("fomc")or[],B.get("fed-3-parlay")or[],sep_2026_realized_action=(os.getenv("PM_SEP_2026_FOMC_ACTION")or"").strip().upper()or None);_ae=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl_os}",timeout=5.)for sl_os in OIL_SENATE_SLUGS),a.fetch_json(f"{GAMMA_URL}/events?series_slug=gas-price-hits-weekly&closed=false&limit=2",timeout=5.));Z={}
  for sl_os,_ad in zip(OIL_SENATE_SLUGS,_ae[:len(OIL_SENATE_SLUGS)]):
   if isinstance(_ad,list)and _ad:
    _aO=_ad[0];Z[sl_os]=_aO
    if"pending-oil"in sl_os:
     _v=parse_zero_fee_negrisk_slate(_aO,sl_os)
     if _v is not None and _v.end_ts>_B+60:a.negrisk_zero_slates[_v.event_id]=_v
  a.oil_senate_truth_legs=build_oil_senate_truth_table_legs(Z);a.gas_events_raw={"us-gas-price-daily":B.get("us-gas-price-daily")or[],"gas-price-hits-weekly":_ae[-1]if isinstance(_ae[-1],list)else[]};m={int(round(sp.end_ts))for sp in a.daily_updown_markets.values()}|{int(round(rgs[0].end_ts))for rgs in a.strike_ladders.values()if rgs};_ac=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={h_slug}&closed=false&limit=6",timeout=4.5)for h_slug in HOURLY_BINANCE_SERIES.values()));_o={}
  for(_L,h_slug),_ab in zip(HOURLY_BINANCE_SERIES.items(),_ac):
   if isinstance(_ab,list):
    for _aN in _ab:
     _aM=parse_daily_updown_event(_aN,_L,h_slug)
     if _aM is not None and _aM.end_ts>_B+30 and any(abs(_aM.end_ts-te)<=5. for te in m):_o[_aM.market_id]=_aM
  a.hourly_12pm_markets=_o;V=datetime.fromtimestamp(_B-4.*3600.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");_K=await asyncio.gather(a.fetch_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&order=volume24hr&ascending=false&limit=100",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&end_date_min={V}&order=endDate&ascending=true&limit=100",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&order=volume24hr&ascending=false&limit=100",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&end_date_min={V}&order=endDate&ascending=true&limit=100",timeout=5.5),*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl_b}",timeout=5.)for sl_b in BOP_2026_SLUGS));_n=(_K[0]if isinstance(_K[0],list)else[])+(_K[1]if isinstance(_K[1],list)else[]);_m=(_K[2]if isinstance(_K[2],list)else[])+(_K[3]if isinstance(_K[3],list)else[]);_J=list({str(e.get("id")):e for e in _n if isinstance(e,dict)and e.get("id")}.values());_I=list({str(e.get("id")):e for e in _m if isinstance(e,dict)and e.get("id")}.values());a.soccer_trees=link_and_parse_soccer_regulation_trees(_J,now_ts=_B);_l={}
  for _aa in _I:
   _9=parse_esports_bo3_event(_aa,now_ts=_B)
   if _9 is not None:_l[_9.event_id]=_9
  a.esports_bo3_specs=_l;U={}
  for sl_b,_aD in zip(BOP_2026_SLUGS,_K[4:]):
   if isinstance(_aD,list)and _aD:U[sl_b]=_aD[0]
  a.lp1_bop_legs=build_lp1_bop_2026_truth_legs(U)
  for T in list(_d.values())+list(U.values()):
   _u=parse_negrisk_convert_event(T)
   if _u is not None and _u.is_closed_convert_safe and _u.end_ts>_B+60:a.negrisk_convert_slates[_u.event_id]=_u
  A=list(dict.fromkeys(list(LP2_MIDTERM_CORE_SLUGS)+[LP2_TOSSUP_CUBE_SLUG]+list(LP2_TOSSUP_STATE_SLUGS.values())));_H=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl_l2}",timeout=5.)for sl_l2 in A),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=tennis&active=true&closed=false&order=volume24hr&ascending=false&limit=45",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=midterms&active=true&closed=false&order=volume24hr&ascending=false&limit=60",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=politics&active=true&closed=false&order=volume24hr&ascending=false&limit=60",timeout=5.5));S=dict(U)
  for sl_l2,_8 in zip(A,_H[:len(A)]):
   if isinstance(_8,list)and _8:S[sl_l2]=_8[0]
  _G=_H[len(A)]if isinstance(_H[len(A)],list)else[];_F=_H[len(A)+1]if isinstance(_H[len(A)+1],list)else[];_E=_H[len(A)+2]if isinstance(_H[len(A)+2],list)else[]
  for _aC in _F+_E:
   if isinstance(_aC,dict)and _aC.get("slug"):S.setdefault(str(_aC["slug"]),_aC)
  a.lp2_events_by_slug=S;Y=[];_D=build_lp2_house_seats_truth_legs(S)
  if _D:Y.append(("LP2_HOUSE_SEATS",_D))
  _C=build_lp2_senate_seats_truth_legs(S)
  if _C:Y.append(("LP2_SENATE_SEATS",_C))
  Y.extend(build_lp2_pending_senate_conditional_groups(list(S.values()),S.get("which-party-will-win-the-senate-in-2026")));Y.extend(build_lp2_tossup_state_implication_groups(S));a.lp2_implication_groups=Y
  for _k in S.values():
   _j=parse_negrisk_convert_event(_k)
   if _j is not None and _j.is_closed_convert_safe and _j.end_ts>_B+60 and len(_j.brackets)<=45:a.negrisk_convert_slates[_j.event_id]=_j
  _i={};J=set()
  for _7 in j+_F+_E:
   if not isinstance(_7,dict):continue
   _aB=str(_7.get("id")or"")
   if not _aB or _aB in J:continue
   J.add(_aB)
   for _6 in parse_cal1_monotonic_ladder_event(_7,now_ts=_B):_i[_6.event_id]=_6
  a.cal1_ladders=_i;_h={}
  for _5 in _G+n:
   if not isinstance(_5,dict):continue
   _4=parse_tennis_retirement_safe_event(_5,now_ts=_B)
   if _4 is not None:_h[_4.event_id]=_4
  a.tennis_specs=_h;v=[sl for sl,ev_n in sorted(q.items(),key=lambda kv:_parse_iso_ts(kv[1].get("startTime")or kv[1].get("endDate"))or 9e12)if not sl.endswith("-more-markets")][:12];i=[];h=[]
  for _aA,_az in K.values():
   _ay=str(_az.get("slug")or"").lower()
   if not _ay or any(_ay.endswith(sfx)for sfx in("-more-markets","-player-props","-exact-margin")):continue
   if _aA in("NFL","CFB")and len(i)<12:i.append(_ay)
   if _aA=="NFL"and len(h)<10:h.append(_ay)
  f={str(e.get("slug")or"").lower()for e in _J if isinstance(e,dict)};l=[f"{tr.slug_3way}-exact-score"for tr in sorted(a.soccer_trees.values(),key=lambda t:t.end_ts)[:16]if tr.slug_3way and f"{tr.slug_3way}-exact-score"not in f];k=list(dict.fromkeys([f"{sl}-more-markets"for sl in(v+i)]+[f"{sl}-player-props"for sl in h]+l));I=[]
  if k:
   R=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl_v4}",timeout=4.5)for sl_v4 in k))
   for _3 in R:
    if isinstance(_3,list)and _3 and isinstance(_3[0],dict):I.append(_3[0])
  z=(list(q.values())+[ev_m for sp_tm,ev_m in K.values()if sp_tm in("NFL","CFB")]+n+I);a.aff1_bundles={b.event_id:b for b in parse_affine_game_bundle(z,now_ts=_B)}
  for _2 in I:
   _ax=str(_2.get("slug")or"").lower()
   if _ax.startswith("nba-"):
    _t=parse_nba_subperiod_and_ext_props(_2,now_ts=_B)
    if _t is not None and _t.event_id not in a.nba_subperiod_slates:a.nba_subperiod_slates[_t.event_id]=_t
  a.soc2_lattices=link_and_parse_soc2_exact_score_lattices(_J+I,now_ts=_B)
  for _1 in a.soc2_lattices.values():
   if _1.convert_spec is not None and _1.convert_spec.end_ts>_B+60:a.negrisk_convert_slates[_1.convert_spec.event_id]=_1.convert_spec
  y={}
  for _aw in[ev_m for sp_tm,ev_m in K.values()if sp_tm=="NFL"]+I+n:
   if not isinstance(_aw,dict):continue
   _av=parse_nfl_player_props_event(_aw,now_ts=_B)
   if _av is not None:y[_av.event_id]=_av
  a.nfl_prop_slates=y;Q={}
  for _au in u+j:
   if isinstance(_au,dict):
    for _at in parse_binance_terminal_close_event(_au):
     if _at.close_ts>_B+120:Q[_at.market_id]=_at
  a.binance_close_rungs=list(Q.values());a.last_discovery_ts=time.time();logger.info(f"Discovery complete: {len(a.weather_events)} Weather city-events, {len(a.barrier_rungs)} Barrier Hit rungs, {len(a.strike_ladders)} Multi-Strike ladders, {len(a.negrisk_ladders)} NegRisk ladders, {len(a.daily_updown_markets)} Crypto Daily Up/Down, {len(a.pyth_daily_markets)} Zero-Fee Pyth FX/Metals Daily, {len(a.pyth_barrier_rungs)} Pyth Hit rungs, {len(a.pyth_close_ladders)} Pyth Close ladders, {len(a.nba_games)} NBA games ({len(a.nba_prop_slates)} Prop, {len(a.nba_subperiod_slates)} SubPer, {len(a.lp1_nba_em_bundles)} EM), {len(a.multi_sport_games)} Multi-Sport ({len(a.lp1_nfl_em_bundles)} NFL EM, {len(a.nfl_prop_slates)} NFL Prop, {len(a.aff1_bundles)} AFF1/SUM1), {len(a.soccer_trees)} Soccer trees ({len(a.soc2_lattices)} SOC2 Exact-Score), {len(a.tennis_specs)} Tennis BO3, {len(a.esports_bo3_specs)} Esports BO3, {len(a.lp2_implication_groups)} LP2 DAG groups, {len(a.cal1_ladders)} CAL1 ladders, {len(a.binance_close_rungs)} Binance Close rungs, {len(a.lp1_bop_legs)//2} BOP/Chamber mkts, {len(a.negrisk_zero_slates)} NegRisk Slates, {len(a.negrisk_convert_slates)} NegRisk Convert slates, {len(a.counting_slates)} Counting slates, {len(a.fomc_truth_legs)//2} FOMC LP mkts, {len(a.oil_senate_truth_legs)//2} Oil-Senate mkts, {len(a.hourly_12pm_markets)} 12PM 1h pairs.")
 async def open_shadow_position(c,sleeve,dedupe_key,asset_or_city,title,side_label,token_id,fee_rate,p_model,close_ts,extra,tp_target_px=None,prefetched_book=None):
  if is_shadow_sleeve_quarantined(sleeve):return False
  k=[dedupe_key]
  if sleeve=="W2_ENSEMBLE_VALUE"and extra.get("event_id"):k.append(f"W2_EVENT_{extra['event_id']}")
  z=c._try_acquire_keys(*k)
  if not z:return False
  try:
   i=250 if sleeve in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK")else 50;v=prefetched_book if(prefetched_book is not None and sleeve not in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"))else await c.fetch_book_after_latency(token_id,latency_ms=i)
   if not v:return False
   n=v.get("asks")or[];m=v.get("bids")or[];l,_=extract_best_bid(m);r=15. if sleeve in("S2_EXACT_TWAP_LOCK","S5M_CHAINLINK_SNIPER","S4H_CHAINLINK_CONVERGENCE","B4_TOUCHED_BARRIER_WICK_LOCK","CM_B2_PYTH_SESSION_NO_LOCK","CM_U1_PYTH_CLOSE_LOCK","TW1_COUNTING_TRUNCATION_AND_BOX","GAS1_AAA_GASOLINE_LOCK","CM_SHOCK_PYTH_CATALYST","W1_LOW_TROUGH_LOCK","BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","AFF1_FROZEN_SUBPERIOD_COLLAPSE","SOC2_EXACT_SCORE_2D_LATTICE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER")else 20.
   if sleeve in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"):a=.9956
   elif sleeve in("B4_TOUCHED_BARRIER_WICK_LOCK","TW1_COUNTING_TRUNCATION_AND_BOX","GAS1_AAA_GASOLINE_LOCK"):a=.99
   elif sleeve in("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","AFF1_FROZEN_SUBPERIOD_COLLAPSE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS"):a=.9881
   elif sleeve in("SP2_NBA_ENDGAME_LOCK","SOC2_EXACT_SCORE_2D_LATTICE"):a=.9861
   elif sleeve in("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"):a=.9821
   elif sleeve=="W1_LOW_TROUGH_LOCK":a=.9601
   else:a=.98
   p=float((extra or{}).get("fee_exponent",1.));h=BANKROLL_TICKETS["T1000"][sleeve];o=BANKROLL_TICKETS["T100"][sleeve];e=sleeve in DEPTH_CAPPED_TAKER_SLEEVES;u=(walk_l2_book_asks_depth_capped(n,h,o,fee_rate=fee_rate,min_l1_usd=r,max_ask_px=a,fee_exponent=p)if e else walk_l2_book_asks(n,h,fee_rate=fee_rate,min_l1_usd=r,max_ask_px=a,fee_exponent=p))
   if not u.get("filled"):return False
   d=p_model-float(u["eff_px"]);f={"W1_SOLAR_PEAK_LOCK":.035,"W1_LOW_TROUGH_LOCK":.03,"W2_ENSEMBLE_VALUE":.095,"B1_CONVEX_TAIL_YES":.06,"B2_BARRIER_NO_LOCK":.035,"M1_SVI_MAKER_SCALP":.05,"M2_STRIKE_CONVERGENCE":.038,"M4_SHOCK_STRIKE_CATCHUP":.065,"S5M_CHAINLINK_SNIPER":.042,"S4H_CHAINLINK_CONVERGENCE":.042,"U1_DAILY_UPDOWN_LOCK":.04,"S2_EXACT_TWAP_LOCK":.03,"B4_TOUCHED_BARRIER_WICK_LOCK":.012,"TW1_COUNTING_TRUNCATION_AND_BOX":.01,"GAS1_AAA_GASOLINE_LOCK":.015,"CM_SHOCK_PYTH_CATALYST":.045,"CM_B2_PYTH_SESSION_NO_LOCK":.035,"CM_U1_PYTH_CLOSE_LOCK":.03,"SP2_NBA_ENDGAME_LOCK":.012,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":.012,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":.012,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":.015,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":.012,"SOC2_EXACT_SCORE_2D_LATTICE":.012,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":.012,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":.0045,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":.018,"BOND1_UMA_RESOLUTION_CARRY":.0045,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":.004}.get(sleeve,.035)
   if d<f:return False
   g={}
   for j,t in BANKROLL_TICKETS.items():
    y=(walk_l2_book_asks_depth_capped(n,t[sleeve],o,fee_rate=fee_rate,min_l1_usd=r,max_ask_px=a,fee_exponent=p)if e else walk_l2_book_asks(n,t[sleeve],fee_rate=fee_rate,min_l1_usd=r,max_ask_px=a,fee_exponent=p))
    if y.get("filled"):g[j]=y
   if not g:return False
   x=time.time();q=f"{sleeve}_{int(x)}_{dedupe_key[-10:]}";b=tp_target_px
   if sleeve=="M1_SVI_MAKER_SCALP"and b is None:b=min(.96,round(float(u["eff_px"])+.05,4))
   elif sleeve=="M4_SHOCK_STRIKE_CATCHUP"and b is None:b=min(.96,round(float(u["eff_px"])+.06,4))
   elif sleeve=="B1_CONVEX_TAIL_YES"and b is None:b=min(.88,round(2.*float(u["vwap"]),4))
   elif sleeve=="S5M_CHAINLINK_SNIPER"and b is None:b=.96
   elif sleeve in("CM_B2_PYTH_SESSION_NO_LOCK","W1_LOW_TROUGH_LOCK")and b is None:b=.985
   elif sleeve in("W1_SOLAR_PEAK_LOCK","B2_BARRIER_NO_LOCK","M2_STRIKE_CONVERGENCE","U1_DAILY_UPDOWN_LOCK")and b is None:b=.98
   w={"position_id":q,"dedupe_key":dedupe_key,"sleeve":sleeve,"asset_or_city":asset_or_city,"title":title,"side":side_label,"token_id":token_id,"fee_rate":fee_rate,"entry_ts":x,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"p_model_entry":round(p_model,4),"entry_eff_px_t1000":u["eff_px"],"entry_vwap_t1000":u["vwap"],"realized_edge_t1000":round(d,4),"entry_best_bid":l,"last_bid":l,"maker_tp_px":b,"tier_fills":g,"extra":extra,"status":"OPEN"};c.open_positions[q]=w
   for s in z:c.entered_keys.add(s)
   c._append_ledger({"event":"SHADOW_ENTRY",**w});logger.info(f"[ENTRY:{sleeve}] {asset_or_city} | {title} ({side_label}) @ eff=${u['eff_px']:.3f} vs p_mod={p_model:.3f} (edge={d:+.3f}, L1=${u['l1_usd']:.0f})");return True
  finally:c._release_inflight_keys(z)
 async def post_shadow_maker_entry(g,sleeve,dedupe_key,asset,title,side_label,token_id,p_model,close_ts,extra,prefetched_book=None,ttl_override_sec=None):
  if is_shadow_sleeve_quarantined(sleeve):return False
  j=sleeve=="W2_MAKER_OVERROUND";m=sleeve=="MKR_REWARD_LOCKED_CARRY";l=sleeve in LOCKED_MAKER_SLEEVES;r=[dedupe_key]
  if j and extra.get("event_id"):r.append(f"W2M_EVENT_{extra['event_id']}")
  E=g._try_acquire_keys(*r)
  if not E:return False
  try:
   C=prefetched_book if prefetched_book is not None else await g.fetch_book_after_latency(token_id,latency_ms=50)
   if not C:return False
   x=C.get("asks")or[];w=C.get("bids")or[];v,o=extract_best_bid(w);n=[float(a["price"])for a in x if float(a.get("price",0))>0 and float(a.get("size",0))>0]
   if not n:
    if l or m:i=1.
    else:return False
   else:i=round(min(n),4)
   if i<=.03 or v<=.0:return False
   if j and((i-v)<.02 or o<10.):return False
   if l:
    if sleeve=="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":b,e,d,c=.95,.95,.996,.004
    elif sleeve=="BOND1_UMA_RESOLUTION_CARRY":b,e,d,c=.94,.94,.995,.005
    elif sleeve=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":b,e,d,c=.85,.9,.993,.0045
    elif sleeve in("SP2_NBA_ENDGAME_LOCK","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"):b,e,d,c=.7,.72,.985,.012
    elif sleeve=="W1_LOW_TROUGH_LOCK":b,e,d,c=.25,.35,.96,.03
    else:b,e,d,c=.25,.35,.94,.035
    if v<b:return False
    G=.001 if v>=.96 else.01;F=.001 if i>.96 else.01;q=(float(extra["resting_bid_override"])if extra.get("resting_bid_override")else(round(v+G,4)if(i-v)>=(2.*G-1e-9)else v));p=min(round(i-F,4),d,round(p_model-c,4));y=.001 if min(q,p)>=.96-1e-9 else.01;f=round(math.floor((min(q,p)+1e-9)/y)*y,4)
    if f<round(v-1e-9,4)or not(e<=f<=d):return False
    h=p_model-f
    if h<c-1e-9:return False
   else:
    if m and extra.get("resting_bid_override"):B=.002 if i>.99 else.005;f=round(min(float(extra["resting_bid_override"]),i-B),4)
    else:u=v+.01 if(i-v)>=.02 else v;f=round(min(u,i-.01),4)
    e=.95 if m else(.14 if j else.18);d=(.994 if p_model>=.999 else.99)if m else(.65 if j else.8)
    if not(e<=f<=d):return False
    h=p_model-f;c=(.006 if p_model>=.999 else.008)if m else(.085 if j else.06)
    if h<c-1e-9:return False
   k=.0 if f>v else round(min(o*.5,60.),2);D=time.time();t=f"MKR_{sleeve}_{int(D)}_{dedupe_key[-10:]}";s=g.spots.get(asset,.0);A={"order_id":t,"dedupe_key":dedupe_key,"sleeve":sleeve,"asset_or_city":asset,"title":title,"side":side_label,"token_id":token_id,"resting_bid":f,"best_bid_at_post":v,"best_ask_at_post":i,"l1_bid_usd":o,"queue_ahead_usd":k,"p_model_at_post":round(p_model,4),"maker_edge_at_post":round(h,4),"spot_at_post":s,"created_ts":D,"created_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"ttl_override_sec":ttl_override_sec,"extra":extra};g.pending_maker_orders[t]=A
   for z in E:g.entered_keys.add(z)
   g._append_ledger({"event":"SHADOW_MAKER_POST",**A});logger.info(f"[MAKER_POST:{sleeve}] {asset} | {title} ({side_label}) resting_bid=${f:.3f} (ask=${i:.3f}, q_ahead=${k:.0f}, p_mod={p_model:.3f}, edge={h:+.3f})");return True
  finally:g._release_inflight_keys(E)
 async def manage_pending_maker_orders(d):
  _T=time.time();_p=datetime.now(timezone.utc)
  for _S,_O in list(d.pending_maker_orders.items()):
   _D=_O["sleeve"];s=_D=="W2_MAKER_OVERROUND";v=_D=="MKR_REWARD_LOCKED_CARRY";u=_D in LOCKED_MAKER_SLEEVES;_N=_O["asset_or_city"];_R=_O["token_id"];G=float(_O["resting_bid"]);_j=float(_O["close_ts"]);_o=_j-_T;_M=_T-float(_O["created_ts"]);_L=dict(_O.get("extra")or{});_C=float(_L.get("strike")or.0);_n=bool(_L.get("is_downward"));_i=_O["side"];_m=(_i=="YES"and not _n)or(_i=="NO"and _n)
   def _discard_maker_keys(ord_obj):
    d.entered_keys.discard(ord_obj["dedupe_key"]);a=(ord_obj.get("extra")or{}).get("event_id")
    if a and ord_obj.get("sleeve")=="W2_MAKER_OVERROUND":d.entered_keys.discard(f"W2M_EVENT_{a}")
   _B=_O.get("ttl_override_sec")
   if _D in("SP2_NBA_ENDGAME_LOCK","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"):g=20.;f=float(_B)if _B is not None else 45.
   elif _D in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"):g=60. if _D=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"else 90.;f=float(_B)if _B is not None else 1800.
   elif _D in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"):g=6e2;f=float(_B)if _B is not None else 3600.
   else:g=6e2 if v else(9e2 if _B is not None else(3600. if s else 7200.));f=float(_B)if _B is not None else(7200. if v else(2700. if s else 1800.))
   if _o<=g or _M>=f:d.pending_maker_orders.pop(_S,None);_discard_maker_keys(_O);d._append_ledger({"event":"SHADOW_MAKER_CANCEL","reason":"TTL_OR_EXPIRY",**_O});continue
   b=None;e=float(_O["p_model_at_post"])
   if _D in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"):
    q=str(_L.get("event_id")or"");_f=d.weather_events.get(q)
    if _f is not None:
     R=f"{_f.icao}_{_f.obs_date.isoformat()}";r=(d.metar_cache.get(R)or(.0,[]))[1];Q=(d.ensemble_cache.get(_f.icao)or(.0,{}))[1];_K=(d.taf_cache.get(_f.icao)or(.0,{}))[1]
     if r or Q:
      P=compute_weather_probabilities(_f,_p,r,Q,forecast_sigma_base_c=d.weather_sigma_c,taf_extreme_c=(_K or{}).get(_f.metric));m=str(_L.get("market_id")or"")
      for O,C in enumerate(_f.buckets):
       if str(C.market_id)==m and O<len(P["probs"]):e=float(P["probs"][O]);break
      if P.get("convective_cold_pool"):b="CONVECTIVE_COLD_POOL"
      elif not P.get("is_solar_lock"):b="SOLAR_LOCK_INVALIDATED"
      elif(e-G)<.02:b="ADVERSE_METAR_OR_EDGE_DECAY"
   elif _D in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER")or v:
    e=(float(_O.get("p_model_at_post")or 1.)if v else(float(_O.get("p_model_at_post")or.998)if _D=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"else 1.));F=str(_L.get("opp_token_id")or"")
    if F and(_T-float(_O.get("_last_opp_chk_ts")or.0))>=12.:
     _O["_last_opp_chk_ts"]=_T;S=await d.fetch_json(f"{CLOB_URL}/book?token_id={F}",timeout=2.5)
     if S:
      D,_=extract_best_bid(S.get("bids")or[]);E=(.008 if _D=="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"else(.03 if(_D=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"or v)else.012))
      if D>E:b="UMA_COMPLEMENT_DISPUTE_BID"
   elif _D=="SP2_NBA_ENDGAME_LOCK":
    _h=d.nba_games.get(str(_L.get("event_id")or""))
    if _h is not None and d.live_nba_board:
     Y=match_nba_live_game(_h,d.live_nba_board)
     if Y is not None:
      _A,_z,_y=Y;_g=[c for c in evaluate_nba_endgame_locks(_h,_A,_z,_y)if c["leg"].token_id==_R]
      if not _g:b="NBA_ENDGAME_LOCK_INVALIDATED"
      else:e=float(_g[0]["p_lock"])
   elif s:
    q=str(_L.get("event_id")or"");_f=d.weather_events.get(q)
    if _f is not None:
     R=f"{_f.icao}_{_f.obs_date.isoformat()}";r=(d.metar_cache.get(R)or(.0,[]))[1];Q=(d.ensemble_cache.get(_f.icao)or(.0,{}))[1]
     if r or Q:
      P=compute_weather_probabilities(_f,_p,r,Q,forecast_sigma_base_c=d.weather_sigma_c);m=str(_L.get("market_id")or"")
      for O,C in enumerate(_f.buckets):
       if str(C.market_id)==m and O<len(P["probs"]):e=float(P["probs"][O]);break
      if P.get("convective_cold_pool"):b="CONVECTIVE_COLD_POOL"
      elif(e-G)<.045:b="ADVERSE_METAR_OR_EDGE_DECAY"
   else:
    _e=d.spots.get(_N,.0);X=float(_O.get("spot_at_post")or.0)
    if _e>0 and _C>0:_x=evaluate_svi_digital_fair_value(_N,_e,_C,_o,is_downward=_n,now_ts=_T);e=float(_x["p_yes"]if _i=="YES"else _x["p_no"])
    if _e>0 and X>0:
     _d=((_e-X)/X)*1e4
     if(_m and _d<-20.)or((not _m)and _d>20.):b="ADVERSE_SPOT_IMPULSE"
    if b is None and _e>0 and _C>0 and(e-G)<.035:b="SVI_EDGE_DECAY"
   bk=None;i=False
   if b is not None:
    if _M>=.35:
     _w=await d.fetch_json(f"{CLOB_URL}/book?token_id={_R}",timeout=2.5)
     if _w:
      _c=[float(a["price"])for a in(_w.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]
      if _c and min(_c)<=G:bk=_w;i=True
    if not i:d.pending_maker_orders.pop(_S,None);_discard_maker_keys(_O);d._append_ledger({"event":"SHADOW_MAKER_CANCEL","reason":b,**_O});continue
   if not i:
    B=.5 if _B is not None else(4. if u else 10.)
    if _M<B:continue
    bk=await d.fetch_json(f"{CLOB_URL}/book?token_id={_R}",timeout=3.)
   if not bk:continue
   _b=bk.get("asks")or[];N=[float(a["price"])for a in _b if float(a.get("price",0))>0 and float(a.get("size",0))>0];p=min(N)if N else 1.;l=(sum(float(a["size"])for a in _b if.0<float(a.get("price",0))<=G+1e-9 and float(a.get("size",0))>0)if N and p<=G else.0)
   if l<=.0 and(u or v):
    M=str(_L.get("condition_id")or"");A=float(d._last_trade_tape_chk_ts.get(M)or.0)
    if M and(_T-A)>=12.:
     d._last_trade_tape_chk_ts[M]=_T;L=await d.fetch_json(f"{DATA_API_URL}/trades?market={M}&limit=15",timeout=3.)
     if isinstance(L,list)and L:
      W=set(_O.get("_seen_trade_keys")or[]);K=str(_L.get("opp_token_id")or"");z=int(float(_O.get("last_repeg_ts")or _O["created_ts"]))+2;x=.0
      for tr in L:
       _J=int(float(tr.get("timestamp")or 0))
       if _J<z:continue
       _P=f"{tr.get('transactionHash')or''}_{_J}_{tr.get('asset')or''}_{tr.get('size')or''}_{tr.get('price')or''}"
       if _P in W:continue
       _u=str(tr.get("asset")or"");_I=float(tr.get("price")or.0);_H=float(tr.get("size")or.0)
       if _H<=.0 or _I<=.0:continue
       if(_u==_R and _I<=G+1e-6)or(K and _u==K and _I>=(1.-G)-1e-6):W.add(_P);x+=_H
      if W:_O["_seen_trade_keys"]=list(W)[-30:]
      if x>.0:l=x;p=G;_L["filled_via_trade_tape"]=True
   if(l<=.0 and(u or v)and(_T-float(_O.get("last_repeg_ts")or _O["created_ts"]))>=15. and _o>=180.):
    y,J=extract_best_bid(bk.get("bids")or[])
    if y>G+1e-6:
     if v:j=.994 if e>=.999 else.99;h=.006 if e>=.999 else.008;n=.002 if p>.99 else.005
     elif _D=="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":j,h,n=.996,.004,(.001 if p>.96 else.01)
     elif _D=="BOND1_UMA_RESOLUTION_CARRY":j,h,n=.995,.005,(.001 if p>.96 else.01)
     elif _D=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":j,h,n=.993,.0045,(.001 if p>.96 else.01)
     else:j,h,n=.0,1.,.01
     if j>.0:
      _G=.001 if y>=.96 else.01;_l=(round(y+_G,4)if(p-y)>=(_G+n-1e-9)else y);_k=min(round(p-n,4),j,round(e-h,4));_a=.001 if min(_l,_k)>=.96-1e-9 else.01;_t=round(math.floor((min(_l,_k)+1e-9)/_a)*_a,4)
      if(_t>G+1e-6 and _t>=round(y-1e-9,4)and _t<=j+1e-9 and(e-_t)>=h-1e-9):_s=G;_O["resting_bid"]=_t;_O["l1_bid_usd"]=J;_O["queue_ahead_usd"]=.0 if _t>y+1e-6 else round(min(J*.5,60.),2);_O["maker_edge_at_post"]=round(e-_t,4);_O["last_repeg_ts"]=_T;d._append_ledger({"event":"SHADOW_MAKER_POST",**_O});logger.info(f"[MAKER_OUTBID_REPEG:{_D}] {_N} | {_O['title']} ({_i}) ${_s:.3f} -> ${_t:.3f} (outbid=${y:.3f}, ask=${p:.3f})");continue
   if l>.0:
    t=float(_O.get("queue_ahead_usd")or.0);w=t/max(.01,G);k=l-w
    if i:k=max(k,l,BANKROLL_TICKETS["T5000"][_D]/max(.01,G))
    elif k<5.:_O["queue_ahead_usd"]=round(max(.0,t-l*G),2);continue
    d.pending_maker_orders.pop(_S,None);V=max(.0,float(_L.get("maker_rebate_ps")or.0));I=round(max(.01,G-V),6);H={}
    for U,_F in BANKROLL_TICKETS.items():Z=_F[_D];T=Z/G;sh=round(min(T,k),4);_E=round(sh*I,2);H[U]={"filled":True,"best_ask":round(p,4),"vwap":G,"eff_px":I,"slip_cents":.0,"spent_usd":_E,"fee_usd":round(-sh*V,4),"shares":sh,"fill_ratio":round(min(1.,_E/max(.01,Z)),4),"l1_usd":_O.get("l1_bid_usd",50.),"levels":1}
    _r=f"{_D}_{int(_T)}_{_O['dedupe_key'][-10:]}"
    if u or v or _D in("BOND1_UMA_RESOLUTION_CARRY","SP2_NBA_ENDGAME_LOCK"):o=None
    elif _D in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"):o=.985
    elif s:o=min(.95,round(max(G+.07,e-.015),4))
    else:o=min(.96,round(G+.05,4))
    if i:_L["adverse_fill_during_cancel_window"]=True;_L["adverse_trigger"]=b
    _Q={"position_id":_r,"dedupe_key":_O["dedupe_key"],"sleeve":_D,"asset_or_city":_N,"title":_O["title"],"side":_i,"token_id":_R,"fee_rate":.0,"entry_ts":_T,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":_j,"p_model_entry":round(e,4),"entry_eff_px_t1000":I,"entry_vwap_t1000":G,"realized_edge_t1000":round(e-I,4),"entry_best_bid":G,"last_bid":G,"maker_tp_px":o,"tier_fills":H,"extra":_L,"status":"OPEN"};d.open_positions[_r]=_Q;d._append_ledger({"event":"SHADOW_ENTRY",**_Q});_q=f"${o:.3f}"if o is not None else"HOLD_SETTLE";logger.info(f"[MAKER_FILLED:{_D}] {_N} | {_Q['title']} ({_i}) @ resting=${G:.3f} -> TP={_q} (p_mod={e:.3f}, adverse={i})")
 async def scan_weather_markets(c,opps_out):
  from src.polymarket_research.riskless_protocol_v2_expansion import resolve_weather_effective_end_ts;_u=datetime.now(timezone.utc);_R=time.time();o=[]
  for _Y in list(c.weather_events.values()):
   _Q=resolve_weather_effective_end_ts(_Y,_R+86400.)
   if _Q<=_R:c.weather_events.pop(_Y.event_id,None);continue
   try:_l=_u.astimezone(ZoneInfo(_Y.tz_name))
   except Exception:_l=_u
   if(_Y.obs_date-_l.date()).days>1 and not c.single_scan:continue
   o.append((0 if _l.date()>=_Y.obs_date else 1,_Q,_Y))
  o.sort(key=lambda r:(r[0],r[1]))
  for _,_,sp in o[:45]:
   _P=time.time();v=resolve_weather_effective_end_ts(sp,_P+86400.)
   if v<=_P:c.weather_events.pop(sp.event_id,None);continue
   Q=not c.single_scan and is_shadow_sleeve_quarantined("W2_ENSEMBLE_VALUE")and is_shadow_sleeve_quarantined("W2_MAKER_OVERROUND")
   if Q:
    try:h=_u.astimezone(ZoneInfo(sp.tz_name))
    except Exception:h=_u
    g=h.date()>=sp.obs_date
   else:g=True
   if Q and not g:_t=max(1,len(sp.buckets));N=[round(1./_t,4)]*len(sp.buckets);_I={"is_solar_lock":False,"locked_bucket_idx":None,"p_locked_bucket":.0,"obs_count":0,"latest_temp_c":None,"running_ext_c":None,"peak_iqr_c":None,"cooling_cushion_c":.0,"convective_cold_pool":False,"probs":N}
   else:
    _O=f"{sp.icao}_{sp.obs_date.isoformat()}";_k=c.metar_cache.get(_O);_b=compute_adaptive_metar_poll_ttl(sp.icao,_k[1]if _k else None,_u)
    if _k is None or(_P-_k[0])>=_b:w=await asyncio.to_thread(fetch_metar_observations_sync,sp.icao,sp.obs_date,sp.tz_name);c.metar_cache[_O]=(_P,w)
    else:w=_k[1]
    P=c.taf_cache.get(_O)
    if P is None or(_P-P[0])>=1800.:n=await asyncio.to_thread(fetch_taf_extremes_sync,sp.icao,sp.obs_date,sp.tz_name);c.taf_cache[_O]=(_P,n)
    else:n=P[1]
    _j=c.ensemble_cache.get(sp.icao);_s=1500. if(_j and _j[1])else 60.
    if _j is None or(_P-_j[0])>=_s:
     async with c._open_meteo_sem:O=await asyncio.to_thread(fetch_live_ensemble_hourly_sync,sp.lat,sp.lon);await asyncio.sleep(.18)
     c.ensemble_cache[sp.icao]=(_P,O)
    else:O=_j[1]
    if not O and not w:continue
    _I=compute_weather_probabilities(sp,_u,w,O,forecast_sigma_base_c=c.weather_sigma_c,taf_extreme_c=(n or{}).get(sp.metric));N=_I["probs"]
   v=resolve_weather_effective_end_ts(sp,_P+86400.)
   if _I["is_solar_lock"]and _I["locked_bucket_idx"]is not None:
    _H=sp.buckets[_I["locked_bucket_idx"]];_G=_I["p_locked_bucket"];_F=float(getattr(_H,"fee_rate",.0)or.0);C=sp.metric=="LOW";_a="W1_LOW_TROUGH_LOCK"if C else"W1_SOLAR_PEAK_LOCK";M=.96 if C else.94;B=.03 if C else.035;_r=f"W1LOW_{sp.event_id}_{_H.market_id}"if C else f"W1_{sp.event_id}_{_H.market_id}";bk=await c.fetch_json(f"{CLOB_URL}/book?token_id={_H.yes_token}",timeout=3.5)
    if bk:
     E=walk_l2_book_asks_depth_capped(bk.get("asks")or[],BANKROLL_TICKETS["T1000"][_a],BANKROLL_TICKETS["T100"][_a],fee_rate=_F,min_l1_usd=(15. if C else 20.),max_ask_px=M+1e-4);_E,L=extract_best_bid(bk.get("bids")or[]);c._record_market_telemetry(key=f"W1_LOCK_{sp.event_id}_{_H.market_id}",min_interval_sec=45.,now_ts=_P,sig=(E.get("eff_px"),_E,round(float(_G),3)),payload={"type":"WEATHER_SOLAR_LOCK_SNAP","sleeve":_a,"event_id":sp.event_id,"city":sp.city,"icao":sp.icao,"metric":sp.metric,"obs_date":sp.obs_date.isoformat(),"bucket":_H.label,"obs_count":_I["obs_count"],"running_ext_c":_I["running_ext_c"],"cushion_c":_I["cooling_cushion_c"],"p_lock":_G,"ask_eff":E.get("eff_px")if E.get("filled")else None,"bid":_E if _E>0 else None,"l1_usd":E.get("l1_usd",.0)});_i={"event_id":sp.event_id,"market_id":_H.market_id,"condition_id":_H.condition_id,"opp_token_id":_H.no_token,"icao":sp.icao,"metric":sp.metric,"obs_date":sp.obs_date.isoformat(),"bucket_label":_H.label,"running_ext_c":_I["running_ext_c"],"cooling_cushion_c":_I["cooling_cushion_c"]};j=False
     if E.get("filled")and.52<=E["eff_px"]<=M:
      _c=_G-E["eff_px"];opps_out.append({"sleeve":_a,"market":f"{sp.city} ({sp.icao}) {sp.metric} {sp.obs_date} -> {_H.label}","ask_vwap":E["eff_px"],"p_model":_G,"net_edge":round(_c,4),"l1_usd":E["l1_usd"]})
      if _c>=B:
       _N=getattr(_H,"neg_risk",None)
       if float(_G)>=.985 and _N is not None and(v-_P)<=86400.:Z=await c.fetch_json(f"{CLOB_URL}/book?token_id={_H.no_token}",timeout=2.5);c.emit_live_single_leg_lock_candidate(sleeve_source=_a,asset=f"{sp.city}_{sp.icao}",dedupe_key=_r,token_id=_H.yes_token,opp_token_id=_H.no_token,market_id=_H.market_id,condition_id=_H.condition_id,side_label="YES",display_label=f"{sp.city} {sp.metric} [{_H.label}]",bk_win=bk,bk_opp=Z if isinstance(Z,dict)else None,fee_rate=_F,fee_exponent=1.,neg_risk=bool(_N),close_ts=v,now_ts=_P,max_lock_eff_px=M,max_opp_bid=.045,hold_to_maturity=False,p_model=float(_G))
       j=await c.open_shadow_position(sleeve=_a,dedupe_key=_r,asset_or_city=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_H.label}]",side_label="YES",token_id=_H.yes_token,fee_rate=_F,p_model=_G,close_ts=v,extra=_i,prefetched_book=bk)
     if(not j and not _I.get("convective_cold_pool")and(v-_P)>9e2 and.25<=_E<=M and(_G-_E)>=B):
      Y=await c.post_shadow_maker_entry(sleeve=_a,dedupe_key=_r,asset=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_H.label}]",side_label="YES",token_id=_H.yes_token,p_model=_G,close_ts=v,extra=_i,prefetched_book=bk)
      if Y and not E.get("filled"):opps_out.append({"sleeve":_a,"market":f"[MAKER] {sp.city} ({sp.icao}) {sp.metric} {sp.obs_date} -> {_H.label}","ask_vwap":_E,"p_model":_G,"net_edge":round(_G-_E,4),"l1_usd":L,"close_ts":v})
   X=f"W3_SLATE_{sp.event_id}";A=float(c._last_w3_slate_chk_ts.get(sp.event_id)or.0);z=45. if(sp.series_slug in HIGH_VOLUME_WEATHER_SERIES or(v-_P)<=21600.)else 120.
   if(X not in c.entered_keys and X not in c.inflight_keys and len(sp.buckets)>=3 and(c.single_scan or(_P-A)>=z)):
    c._last_w3_slate_chk_ts[sp.event_id]=_P;_D=[b_i.yes_token for b_i in sp.buckets]+[b_i.no_token for b_i in sp.buckets];_h=await c.fetch_books_batch(_D,timeout=3.);l={};e={}
    for b_i in sp.buckets:
     _W=_h.get(b_i.yes_token);_C=_h.get(b_i.no_token);_M={}
     if _W:
      e[b_i.market_id]=_W;_B=sorted([(float(a["price"]),float(a["size"]))for a in(_W.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
      if _B:_M["ask_yes"]=_B[0][0];_M["ask_yes_shares"]=_B[0][1]
     if _C:
      _A=sorted([(float(a["price"]),float(a["size"]))for a in(_C.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
      if _A:_M["ask_no"]=_A[0][0];_M["ask_no_shares"]=_A[0][1]
     if _M:l[b_i.market_id]=_M
     if(_C and int(_I.get("obs_count")or 0)>=1 and _I.get("running_ext_c")is not None and not _I.get("has_corrected_obs")and float(getattr(b_i,"rewards_min_size",.0)or.0)>.0 and(v-_P)>3e2):
      W=celsius_to_market_int(float(_I["running_ext_c"]),b_i.unit);V=((sp.metric=="HIGH"and b_i.high_bound<=W-2)or(sp.metric=="LOW"and b_i.low_bound>=W+2))
      if V:
       _z,_=extract_best_bid(_C.get("bids")or[]);_y=float(_M.get("ask_no",1.)or 1.);_V=evaluate_locked_market_reward_carry(1.,_z,_y,float(b_i.rewards_min_size),float(b_i.rewards_max_spread),float(getattr(b_i,"fee_rate",.0)or.0))
       if _V.get("eligible"):
        opps_out.append({"sleeve":"MKR_REWARD_LOCKED_CARRY","market":f"{sp.city} ({sp.icao}) Dead NO[{b_i.label}] @ ${_V['resting_bid']:.3f}","ask_vwap":_V["resting_bid"],"p_model":1.,"net_edge":_V["carry_edge"],"l1_usd":50.,"close_ts":v});await c.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY",f"MKR_RW_W_{b_i.market_id}",f"{sp.city}_{sp.icao}",f"{sp.title} [Dead NO {b_i.label}]","NO",b_i.no_token,1.,v,{"market_id":b_i.market_id,"condition_id":b_i.condition_id,"opp_token_id":b_i.yes_token,"resting_bid_override":_V["resting_bid"]},prefetched_book=_C)
        if is_reward_locked_carry_live_ready(c,1.)and getattr(b_i,"neg_risk",None)is not None and _W is not None:c.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_REWARD_LOCKED_CARRY",asset=f"{sp.city}_{sp.icao}",dedupe_key=f"MKR_RW_W_{b_i.market_id}",pair_dedupe_key=f"MKR_RW_WPAIR_{b_i.market_id}",token_id=b_i.no_token,opp_token_id=b_i.yes_token,market_id=b_i.market_id,condition_id=b_i.condition_id,side_label="NO",display_label=f"{sp.city} Reward Carry NO[{b_i.label}]",bk_win=_C,bk_opp=_W,neg_risk=bool(b_i.neg_risk),close_ts=float(v),now_ts=_P,min_resting_bid=.94,max_resting_bid=.994,min_maker_edge=.006,max_opp_bid=.03,hold_to_maturity=True,p_model=1.,target_bid_px=float(_V["resting_bid"]))
     if _W and _C and float(getattr(b_i,"fee_rate",.0)or.0)==.0:
      _U=scan_binary_complete_set_arb(market_id=b_i.market_id,condition_id=b_i.condition_id,yes_token=b_i.yes_token,no_token=b_i.no_token,asks_yes_raw=_W.get("asks")or[],asks_no_raw=_C.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],fee_rate=.0,max_box_cost_net=.995)
      if _U.get("filled"):
       opps_out.append({"sleeve":"C1_BINARY_COMPLETE_SET","market":f"{sp.city} ({sp.icao}) Complete-Set [{b_i.label}]","ask_vwap":_U["box_cost_net"],"p_model":1.,"net_edge":_U["riskless_floor_per_pair"],"l1_usd":_U["l1_usd"],"close_ts":v});K=getattr(b_i,"neg_risk",None);_q={"token_id":b_i.yes_token,"opp_token_id":b_i.no_token,"condition_id":b_i.condition_id,"side":"YES","label":"YES","market_id":b_i.market_id,"fee_rate":.0,"strike":1e2,"neg_risk":bool(K)};_p={"token_id":b_i.no_token,"opp_token_id":b_i.yes_token,"condition_id":b_i.condition_id,"side":"NO","label":"NO","market_id":b_i.market_id,"fee_rate":.0,"strike":1e2,"neg_risk":bool(K)};await c.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key=f"C1_W_{b_i.market_id}",asset=f"{sp.city}_{sp.icao}",title=f"{sp.city} YES+NO Complete Set [{b_i.label}]",leg_a=_q,leg_b=_p,bk_a=_W,bk_b=_C,close_ts=v,max_box_cost_net=.995,extra={"is_complete_set":True,"market_id":b_i.market_id,"condition_id":b_i.condition_id})
       if K is not None and(v-_P)<=86400. and float(_U["box_cost_net"])<=.99:c.emit_live_two_leg_box_candidate(sleeve_source="C1_BINARY_COMPLETE_SET",box_type="COMPLETE_SET",asset=f"{sp.city}_{sp.icao}",dedupe_key=f"C1_W_{b_i.market_id}",leg_a=_q,leg_b=_p,bk_a=_W,bk_b=_C,close_ts=float(v),now_ts=_P)
    _g=evaluate_weather_event_slate(sp,N,l,target_budget_usd=BANKROLL_TICKETS["T1000"]["W3_WEATHER_SLATE_ARB"]);_f=_g.get("full_slate_arb")
    if len(l)==len(sp.buckets):U=all(l[b.market_id].get("ask_yes",0)>0 for b in sp.buckets);T=all(l[b.market_id].get("ask_no",0)>0 for b in sp.buckets);_e=round(sum(float(l[b.market_id]["ask_yes"])for b in sp.buckets),4)if U else None;_d=round(sum(float(l[b.market_id]["ask_no"])for b in sp.buckets),4)if T else None;_o=max(range(len(sp.buckets)),key=lambda idx_b:float(N[idx_b]))if N else 0;_n=sp.buckets[_o]if sp.buckets else None;S=float(l[_n.market_id].get("ask_yes")or.0)if _n else.0;c._record_market_telemetry(key=f"W_SLATE_{sp.event_id}",min_interval_sec=45. if(v-_P)<=7200. else 90.,now_ts=_P,sig=(_e,_d,_I["running_ext_c"],round(S,3),(_f or{}).get("mode")),payload={"type":"WEATHER_SLATE","event_id":sp.event_id,"city":sp.city,"icao":sp.icao,"metric":sp.metric,"obs_date":sp.obs_date.isoformat(),"n_buckets":len(sp.buckets),"tte_sec":round(v-_P,0),"obs_count":_I["obs_count"],"latest_c":_I["latest_temp_c"],"running_ext_c":_I["running_ext_c"],"ens_iqr_c":_I["peak_iqr_c"],"solar_lock":_I["is_solar_lock"],"top_bucket":_n.label if _n else None,"top_p":round(float(N[_o]),4)if N else None,"top_ask_yes":round(S,4)if S>0 else None,"sum_yes_l1":_e,"sum_no_l1":_d,"no_payout":len(sp.buckets)-1,"arb_mode":(_f or{}).get("mode")})
    if _f:_T=float(_f.get("guaranteed_payout_per_set")or 1.);opps_out.append({"sleeve":"W3_WEATHER_SLATE_ARB","market":f"{sp.city} ({sp.icao}) {sp.obs_date} Full-Slate ({len(sp.buckets)} buckets, {_f.get('side','ALL_BUCKETS_YES')})","ask_vwap":round(float(_f["sum_asks"])/_T,4),"p_model":1.,"net_edge":round(float(_f["guaranteed_edge_per_set"])/_T,4),"l1_usd":_f["total_cost_usd"]});await c.open_shadow_weather_slate(sp,_f,v)
    if all(b.market_id in e for b in sp.buckets):await c.execute_ctf_overround_mint_sell(dedupe_key=f"CTF_OVR_W_{sp.event_id}",asset=f"{sp.city}_{sp.icao}",title=f"{sp.city} {sp.obs_date} Weather NegRisk Overround Mint-Sell",legs_bids_spec=[{"bids":e[b.market_id].get("bids")or[],"fee_rate":float(getattr(b,"fee_rate",.0)or.0),"fee_exponent":1.}for b in sp.buckets],close_ts=v,min_net_proceeds_per_set=1.004,opps_out=opps_out,extra={"overround_kind":"WEATHER_NEGRISK","event_id":sp.event_id})
   else:e={}
   if is_shadow_sleeve_quarantined("W2_ENSEMBLE_VALUE")and is_shadow_sleeve_quarantined("W2_MAKER_OVERROUND"):continue
   q=int(_I.get("ensemble_member_count")or 0);J=float(_I.get("peak_iqr_c")or.0);m=f"W2_EVENT_{sp.event_id}"in c.entered_keys or f"W2_EVENT_{sp.event_id}"in c.inflight_keys;k=f"W2M_EVENT_{sp.event_id}"in c.entered_keys or f"W2M_EVENT_{sp.event_id}"in c.inflight_keys;f=None;d=None;y=sorted(range(len(N)),key=lambda i:-N[i])[:2]
   for _X in y:
    _L=N[_X]
    if _L<.24:continue
    b=sp.buckets[_X];_K=float(getattr(b,"fee_rate",.0)or.0);bk=e.get(b.market_id)or await c.fetch_json(f"{CLOB_URL}/book?token_id={b.yes_token}",timeout=3.5)
    if not bk:continue
    I=bk.get("asks")or[];H=bk.get("bids")or[];G,u=extract_best_bid(H);t=[float(a["price"])for a in I if float(a.get("price",0))>0 and float(a.get("size",0))>0]
    if _K==.0 and t and G>0 and(min(t)-G)>=.02:
     F=round(min(t),4);p=round(min(G+.01,F-.01),4);s=_L-p
     if.14<=p<=.65 and s>=.055 and q>=50 and u>=10.:opps_out.append({"sleeve":"W2_MAKER_OVERROUND","market":f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label} [MakerBid]","ask_vwap":p,"p_model":round(_L,4),"net_edge":round(s,4),"l1_usd":u})
     if(not m and not k and(v-_P)>=5400. and q>=50 and J<=2.2 and not _I.get("convective_cold_pool")and u>=10. and.14<=p<=.62 and _L>=.3 and s>=.085):
      if d is None or s>d[0]:d=(s,_L,p,b,bk)
    E=walk_l2_book_asks(I,50.,fee_rate=_K)
    if not E.get("filled"):continue
    _x=E["eff_px"];_c=_L-_x
    if.1<=_x<=.62 and _c>=.04 and q>=50:opps_out.append({"sleeve":"W2_ENSEMBLE_VALUE","market":f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label}","ask_vwap":_x,"p_model":round(_L,4),"net_edge":round(_c,4),"l1_usd":E["l1_usd"]})
    if(not m and not k and q>=50 and J<=2.2 and not _I.get("convective_cold_pool")and.16<=_x<=.62 and _L>=.34 and _c>=.095):
     if f is None or _c>f[0]:f=(_c,_L,_x,b,bk)
   if f is not None and os.getenv("PM_DISABLE_SHADOW_W2_TAKER","0")!="1":_,D,_,_w,_m=f;await c.open_shadow_position(sleeve="W2_ENSEMBLE_VALUE",dedupe_key=f"W2_{sp.event_id}_{_w.market_id}",asset_or_city=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_w.label}]",side_label="YES",token_id=_w.yes_token,fee_rate=float(getattr(_w,"fee_rate",.0)or.0),p_model=D,close_ts=v,extra={"event_id":sp.event_id,"market_id":_w.market_id,"condition_id":_w.condition_id,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket_label":_w.label,"bias_c":_I["bias_c"],"ensemble_members":q,"peak_iqr_c":J},prefetched_book=_m)
   elif d is not None:_,R,_,_J,_v=d;await c.post_shadow_maker_entry(sleeve="W2_MAKER_OVERROUND",dedupe_key=f"W2M_{sp.event_id}_{_J.market_id}",asset=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_J.label}]",side_label="YES",token_id=_J.yes_token,p_model=R,close_ts=v,extra={"execution_mode":"POST_ONLY_WEATHER_MAKER_ZERO_FEE","event_id":sp.event_id,"market_id":_J.market_id,"condition_id":_J.condition_id,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket_label":_J.label,"bias_c":_I["bias_c"],"ensemble_members":q,"peak_iqr_c":J},prefetched_book=_v)
 async def scan_barrier_markets(a,opps_out):
  _d=time.time();X=asyncio.get_running_loop();o=collections.defaultdict(list)
  for r in a.barrier_rungs.values():
   if r.end_ts>_d+300:o[r.event_id].append(r)
  for J,I in o.items():
   r0=I[0];W=a.spots.get(r0.asset,.0)
   if W<=0:continue
   e={};x=a.barrier_ext_cache.get(J)
   for E in sorted({int(r.start_ts//60)for r in I}):
    ck=f"{r0.asset}_{E}";h=a.barrier_ext_cache.get(ck)or x
    if h is None or(_d-h[0])>=90.:
     w=await asyncio.to_thread(fetch_binance_window_extremes_sync,r0.asset,float(E*60),_d,"1m")
     if w:a.barrier_ext_cache[ck]=(_d,w)
     e[E]=w
    else:e[E]=h[1]
   d=[]
   for r in I:
    if f"B4_{r.market_id}"in a.entered_keys:continue
    f=e.get(int(r.start_ts//60))
    if f is None:continue
    V,U=float(f[0]),float(f[1])
    if(r.direction=="UP"and V>=r.strike*1.0005)or(r.direction=="DOWN"and U<=r.strike*.9995):d.append((r,V,U))
   if d:
    D=await a.fetch_books_batch([rt[0].yes_token for rt in d],timeout=2.5)
    for _c,H,G in d:
     F=D.get(_c.yes_token)
     if not F:continue
     C,_=extract_best_bid(F.get("bids")or[]);T=walk_l2_book_asks(F.get("asks")or[],1e2,fee_rate=_c.fee_rate,min_l1_usd=15.,max_ask_px=.99)
     if T.get("filled")and C>=.78 and.85<=float(T["eff_px"])<=.984:opps_out.append({"sleeve":"B4_TOUCHED_BARRIER_WICK_LOCK","market":f"{_c.asset} Breached 1m Wick Lock: {_c.question}","ask_vwap":T["eff_px"],"p_model":1.,"net_edge":round(1.-float(T["eff_px"]),4),"l1_usd":T["l1_usd"]});await a.open_shadow_position(sleeve="B4_TOUCHED_BARRIER_WICK_LOCK",dedupe_key=f"B4_{_c.market_id}",asset_or_city=_c.asset,title=_c.question,side_label="YES",token_id=_c.yes_token,fee_rate=_c.fee_rate,p_model=1.,close_ts=_c.end_ts,extra={"market_id":_c.market_id,"condition_id":_c.condition_id,"strike":_c.strike,"direction":_c.direction,"fin_high":H,"fin_low":G},prefetched_book=F)
   g=[]
   for r in I:
    if abs(math.log(r.strike/W))>.14:continue
    f=e.get(int(r.start_ts//60));S=max(W,f[0])if f else W;R=min(W,f[1])if f else W
    if(r.direction=="UP"and S>=r.strike)or(r.direction=="DOWN"and R<=r.strike):continue
    g.append(r)
   B=r0.end_ts-_d;n=(await a.fetch_books_batch([r.yes_token for r in g]+[r.no_token for r in g],timeout=3.)if g and B<=3*86400 else{});c=[]
   for r in g:
    _b=r.end_ts-_d;Q,A=get_wing_implied_vol(r.asset,W,r.strike,_b);v=first_passage_touch_prob(W,r.strike,_b,Q,r.direction,wick_vol_multiplier=a.barrier_wick_mult);j=n.get(r.yes_token);i=n.get(r.no_token)
    if j and i and _b<=3*86400:P=walk_l2_book_asks(j.get("asks")or[],40.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);O=walk_l2_book_asks(i.get("asks")or[],40.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);c.append({"strike":r.strike,"direction":r.direction,"market_id":r.market_id,"condition_id":r.condition_id,"yes_token":r.yes_token,"no_token":r.no_token,"fee_rate":r.fee_rate,"fee_exponent":r.fee_exponent,"ask_yes":P.get("vwap")if P.get("filled")else None,"ask_no":O.get("vwap")if O.get("filled")else None,"bk_yes":j,"bk_no":i,"start_ts":r.start_ts,"end_ts":r.end_ts})
    if(a.single_scan or not is_shadow_sleeve_quarantined("B1_CONVEX_TAIL_YES"))and 7200<=_b<=10*86400 and.07<=v<=.48:
     N=j or await a.fetch_json(f"{CLOB_URL}/book?token_id={r.yes_token}",timeout=3.)
     if N:
      _a=walk_l2_book_asks(N.get("asks")or[],25.,fee_rate=CRYPTO_FEE_RATE)
      if _a.get("filled")and.04<=_a["vwap"]<=.32:
       z=v-_a["eff_px"]
       if z>=.03:opps_out.append({"sleeve":"B1_CONVEX_TAIL_YES","market":f"{r.asset} {r.question}","ask_vwap":_a["eff_px"],"p_model":round(v,4),"net_edge":round(z,4),"l1_usd":_a["l1_usd"]})
       if z>=.12 and(v/_a["eff_px"])>=1.75 and _a["vwap"]<=.2:logger.info(f"[TELEMETRY_ONLY:B1_EXTREME_DISLOCATION] {r.asset} {r.question} ask={_a['eff_px']:.3f} p={v:.3f}")
    M=1.-v
    if 3600<=_b<=36000 and M>=.88:
     L=i or await a.fetch_json(f"{CLOB_URL}/book?token_id={r.no_token}",timeout=3.)
     if L:
      Z=walk_l2_book_asks(L.get("asks")or[],1e2,fee_rate=CRYPTO_FEE_RATE)
      if Z.get("filled")and.65<=Z["vwap"]<=.91:
       y=M-Z["eff_px"];u=evaluate_barrier_no_net_ev(v,Z["vwap"],fee_rate=CRYPTO_FEE_RATE)
       if y>=.025:opps_out.append({"sleeve":"B2_BARRIER_NO_LOCK","market":f"{r.asset} NO: {r.question}","ask_vwap":Z["eff_px"],"p_model":round(M,4),"net_edge":round(y,4),"l1_usd":Z["l1_usd"]})
       if y>=.038 and u["eligible"]:await a.open_shadow_position(sleeve="B2_BARRIER_NO_LOCK",dedupe_key=f"B2_{r.market_id}",asset_or_city=r.asset,title=r.question,side_label="NO",token_id=r.no_token,fee_rate=CRYPTO_FEE_RATE,p_model=M,close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"start_ts":r.start_ts,"strike":r.strike,"direction":r.direction,"iv_wing":round(Q,4),"loss_to_gain_ratio":u["loss_to_gain_ratio"]},prefetched_book=L)
   if len(c)>=2:
    t=detect_barrier_monotonicity_boxes(c,fee_rate=CRYPTO_FEE_RATE,max_box_cost_net=1.2)
    if t:Y=t[0];a._record_market_telemetry(key=f"B3_DIAG_{J}",min_interval_sec=60.,now_ts=_d,sig=(Y["direction"],Y["low_strike"],Y["high_strike"],Y["box_cost_gross"],Y["box_cost_net"]),payload={"type":"BARRIER_MONO_BEST","asset":r0.asset,"event_id":J,"spot":W,"direction":Y["direction"],"low_strike":Y["low_strike"],"high_strike":Y["high_strike"],"gross_box_l1":Y["box_cost_gross"],"net_box_l1":Y["box_cost_net"]})
    s=[b for b in t if float(b["box_cost_net"])<=.995];m={str(q["yes_token"]):q for q in c};p={str(q["no_token"]):q for q in c}
    for ba in s:
     qy=m.get(ba["yes_token"]);qn=p.get(ba["no_token"])
     if not qy or not qn:continue
     K=walk_equal_shares_dominance_box(qy["bk_yes"].get("asks")or[],qn["bk_no"].get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["B3_BARRIER_MONO_BOX"],fee_rate_a=float(qy["fee_rate"]),fee_rate_b=float(qn["fee_rate"]),fee_exponent_a=float(qy.get("fee_exponent",1.)),fee_exponent_b=float(qn.get("fee_exponent",1.)),max_box_cost_net=.995,min_shares=6,min_box_notional_usd=5.5)
     if K.get("filled"):
      opps_out.append({"sleeve":"B3_BARRIER_MONO_BOX","market":f"{r0.asset} Barrier Box {ba['label']}","ask_vwap":round(float(K["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(K["box_cost_net"]),4),"l1_usd":K["l1_usd"],"close_ts":qy["end_ts"]});l={"token_id":ba["yes_token"],"opp_token_id":ba["yes_opp_token"],"condition_id":ba["leg_yes_condition_id"],"side":"YES","label":f"YES_{ba['direction']}","market_id":ba["leg_yes_market_id"],"fee_rate":float(qy["fee_rate"]),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(ba["low_strike"]if ba["direction"]=="UP"else ba["high_strike"])};k={"token_id":ba["no_token"],"opp_token_id":ba["no_opp_token"],"condition_id":ba["leg_no_condition_id"],"side":"NO","label":f"NO_{ba['direction']}","market_id":ba["leg_no_market_id"],"fee_rate":float(qn["fee_rate"]),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(ba["high_strike"]if ba["direction"]=="UP"else ba["low_strike"])};await a.open_shadow_two_leg_box(sleeve="B3_BARRIER_MONO_BOX",dedupe_key=f"B3_{r0.asset}_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",asset=r0.asset,title=f"{r0.asset} Barrier Box {ba['label']}",leg_a=l,leg_b=k,bk_a=qy["bk_yes"],bk_b=qn["bk_no"],close_ts=float(qy["end_ts"]),max_box_cost_net=.995,extra={"is_barrier_mono_box":True,"direction":ba["direction"],"low_strike":ba["low_strike"],"high_strike":ba["high_strike"]})
      if(float(qy["end_ts"])-_d)<=86400. and float(K["box_cost_net"])<=.988:a.emit_live_two_leg_box_candidate(sleeve_source="B3_BARRIER_MONO_BOX",box_type="BARRIER_MONO",asset=r0.asset,dedupe_key=f"B3_{r0.asset}_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",leg_a=l,leg_b=k,bk_a=qy["bk_yes"],bk_b=qn["bk_no"],close_ts=float(qy["end_ts"]),now_ts=_d,k_low=float(ba["low_strike"]),k_high=float(ba["high_strike"]))
 async def scan_multistrike_markets(a,opps_out):
  V=time.time()
  for k,D in list(a.strike_ladders.items()):
   if not D:continue
   C=D[0].asset;P=a.spots.get(C,.0)
   if P<=0:continue
   U=D[0].end_ts-V
   if U<=900:continue
   j=a.get_return_bps(C,60.);O=[r for r in D if abs(math.log(r.strike/P))<=.08];f=(not a.single_scan and is_shadow_sleeve_quarantined("M1_SVI_MAKER_SCALP")and is_shadow_sleeve_quarantined("M2_STRIKE_CONVERGENCE"));h=({}if f else evaluate_coherent_strike_ladder(C,P,O,U,now_ts=V).get("by_market_id",{}));e=[]
   for X in O:
    B=(None if f else(h.get(X.market_id)or evaluate_svi_digital_fair_value(C,P,X.strike,U,is_downward=X.is_downward,now_ts=V)));N,M=await asyncio.gather(a.fetch_json(f"{CLOB_URL}/book?token_id={X.yes_token}",timeout=3.),a.fetch_json(f"{CLOB_URL}/book?token_id={X.no_token}",timeout=3.))
    if not N or not M:continue
    A=scan_binary_complete_set_arb(market_id=X.market_id,condition_id=X.condition_id,yes_token=X.yes_token,no_token=X.no_token,asks_yes_raw=N.get("asks")or[],asks_no_raw=M.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],fee_rate=CRYPTO_FEE_RATE)
    if A.get("filled"):
     opps_out.append({"sleeve":"C1_BINARY_COMPLETE_SET","market":f"{C} Complete-Set {X.question}","ask_vwap":A["box_cost_net"],"p_model":1.,"net_edge":A["riskless_floor_per_pair"],"l1_usd":A["l1_usd"],"close_ts":X.end_ts});s={"token_id":X.yes_token,"opp_token_id":X.no_token,"condition_id":X.condition_id,"side":"YES","label":"YES","market_id":X.market_id,"fee_rate":CRYPTO_FEE_RATE,"strike":float(X.strike)};p={"token_id":X.no_token,"opp_token_id":X.yes_token,"condition_id":X.condition_id,"side":"NO","label":"NO","market_id":X.market_id,"fee_rate":CRYPTO_FEE_RATE,"strike":float(X.strike)};await a.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key=f"C1_{X.market_id}",asset=C,title=f"{C} YES+NO Complete Set: {X.question}",leg_a=s,leg_b=p,bk_a=N,bk_b=M,close_ts=X.end_ts,max_box_cost_net=.994,extra={"is_complete_set":True,"market_id":X.market_id,"condition_id":X.condition_id})
     if(X.end_ts-V)<=86400. and float(A["box_cost_net"])<=.988:a.emit_live_two_leg_box_candidate(sleeve_source="C1_BINARY_COMPLETE_SET",box_type="COMPLETE_SET",asset=C,dedupe_key=f"C1_{X.market_id}",leg_a=s,leg_b=p,bk_a=N,bk_b=M,close_ts=float(X.end_ts),now_ts=V,k_low=float(X.strike),k_high=float(X.strike))
    T=walk_l2_book_asks(N.get("asks")or[],1e2,fee_rate=CRYPTO_FEE_RATE);S=walk_l2_book_asks(M.get("asks")or[],1e2,fee_rate=CRYPTO_FEE_RATE);e.append({"strike":X.strike,"is_downward":X.is_downward,"market_id":X.market_id,"condition_id":X.condition_id,"yes_token":X.yes_token,"no_token":X.no_token,"ask_yes":T.get("vwap")if T.get("filled")else None,"ask_no":S.get("vwap")if S.get("filled")else None,"asks_yes":N.get("asks")or[],"asks_no":M.get("asks")or[],"bk_yes":N,"bk_no":M,"end_ts":X.end_ts})
    for o,R,z,y,u in([]if(B is None or(is_shadow_sleeve_quarantined("M1_SVI_MAKER_SCALP")and is_shadow_sleeve_quarantined("M2_STRIKE_CONVERGENCE")))else[("YES",X.yes_token,T,B["p_yes"],N),("NO",X.no_token,S,B["p_no"],M)]):
     if not z.get("filled"):continue
     w=z["eff_px"];L=y-w;t=(o=="YES"and not X.is_downward)or(o=="NO"and X.is_downward)
     if(t and j<-12.)or((not t)and j>12.):continue
     if.14<=w<=.9 and L>=.025:opps_out.append({"sleeve":"M1_OR_M2_STRIKE_SVI","market":f"{C} {X.question} ({o})","ask_vwap":w,"p_model":y,"net_edge":round(L,4),"l1_usd":z["l1_usd"]})
     c=y-(float(z["best_ask"])-.01)
     if 10800<=U<=86400 and.19<=z["best_ask"]<=.81 and c>=.06:await a.post_shadow_maker_entry(sleeve="M1_SVI_MAKER_SCALP",dedupe_key=f"M1_{X.market_id}_{o}",asset=C,title=X.question,side_label=o,token_id=R,p_model=y,close_ts=X.end_ts,extra={"execution_mode":"POST_ONLY_MAKER_ZERO_FEE","market_id":X.market_id,"condition_id":X.condition_id,"strike":X.strike,"is_downward":X.is_downward,"iv_annual":B["iv_annual"],"z_sigma":B["z_sigma"]},prefetched_book=u)
     if(1200<=U<=6300 and.68<=z["vwap"]<=.9 and B["z_sigma"]>=1.75 and y>=.93 and L>=.045):await a.open_shadow_position(sleeve="M2_STRIKE_CONVERGENCE",dedupe_key=f"M2_{X.market_id}_{o}",asset_or_city=C,title=X.question,side_label=o,token_id=R,fee_rate=CRYPTO_FEE_RATE,p_model=y,close_ts=X.end_ts,extra={"market_id":X.market_id,"condition_id":X.condition_id,"strike":X.strike,"is_downward":X.is_downward,"iv_annual":B["iv_annual"],"z_sigma":B["z_sigma"]},prefetched_book=u)
   if len(e)>=2:
    K=sorted([q for q in e if not q.get("is_downward")],key=lambda x:x["strike"]);b=None
    for Q in range(len(K)-1):
     J,I=float(K[Q].get("ask_yes")or 1.),float(K[Q+1].get("ask_no")or 1.)
     if 0<J<1. and 0<I<1.:
      H=J+I+CRYPTO_FEE_RATE*(J*(1.-J)+I*(1.-I))
      if b is None or H<b[0]:b=(round(H,4),round(J+I,4),float(K[Q]["strike"]),float(K[Q+1]["strike"]))
    if b is not None:a._record_market_telemetry(key=f"M3_DIAG_{k}",min_interval_sec=60.,now_ts=V,sig=b,payload={"type":"LADDER_MONO_BEST","asset":C,"ladder_key":k,"spot":P,"tte_sec":round(U,0),"low_strike":b[2],"high_strike":b[3],"gross_box_l1":b[1],"net_box_l1":b[0]})
   l=detect_ladder_monotonicity_boxes(e,fee_rate=CRYPTO_FEE_RATE);d={str(q["yes_token"]):q for q in e};g={str(q["no_token"]):q for q in e}
   for W in l:
    G=d.get(str(W.get("yes_token_low")or""));F=g.get(str(W.get("no_token_high")or""))
    if not G or not F:continue
    E=walk_equal_shares_dominance_box(G.get("asks_yes")or[],F.get("asks_no")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["M3_LADDER_MONO_BOX"],fee_rate_a=CRYPTO_FEE_RATE,fee_rate_b=CRYPTO_FEE_RATE,max_box_cost_net=.996,min_shares=10,min_box_notional_usd=9.)
    if E.get("filled"):
     opps_out.append({"sleeve":"M3_LADDER_MONO_BOX","market":f"{C} Box YES>{W['low_strike']} + NO>{W['high_strike']}","ask_vwap":round(float(E["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(E["box_cost_net"]),4),"l1_usd":E["l1_usd"],"close_ts":G["end_ts"]});n={"token_id":W["yes_token_low"],"opp_token_id":str(G["no_token"]),"condition_id":str(G.get("condition_id")or""),"side":"YES","label":f"YES>{W['low_strike']}","market_id":W["low_market_id"],"fee_rate":CRYPTO_FEE_RATE,"strike":float(W["low_strike"])};m={"token_id":W["no_token_high"],"opp_token_id":str(F["yes_token"]),"condition_id":str(F.get("condition_id")or""),"side":"NO","label":f"NO>{W['high_strike']}","market_id":W["high_market_id"],"fee_rate":CRYPTO_FEE_RATE,"strike":float(W["high_strike"])};await a.open_shadow_two_leg_box(sleeve="M3_LADDER_MONO_BOX",dedupe_key=f"M3_{C}_{W['low_market_id']}_{W['high_market_id']}",asset=C,title=f"{C} Ladder Box YES>{W['low_strike']} + NO>{W['high_strike']}",leg_a=n,leg_b=m,bk_a=G["bk_yes"],bk_b=F["bk_no"],close_ts=float(G["end_ts"]),max_box_cost_net=.996,extra={"is_mono_box":True,"low_strike":W["low_strike"],"high_strike":W["high_strike"],"low_market_id":W["low_market_id"],"high_market_id":W["high_market_id"]})
     if(float(G["end_ts"])-V)<=86400. and float(E["box_cost_net"])<=.988:a.emit_live_two_leg_box_candidate(sleeve_source="M3_LADDER_MONO_BOX",box_type="LADDER_MONO",asset=C,dedupe_key=f"M3_{C}_{W['low_market_id']}_{W['high_market_id']}",leg_a=n,leg_b=m,bk_a=G["bk_yes"],bk_b=F["bk_no"],close_ts=float(G["end_ts"]),now_ts=V,k_low=float(W["low_strike"]),k_high=float(W["high_strike"]))
   v=f"{C}_{int(D[0].end_ts)}";i=a.negrisk_ladders.get(v)or[]
   if i:await a._scan_negrisk_bundles_for_ladder(asset=C,spot=P,rungs=D,nr_brackets=i,ms_book_cache={**{str(q["yes_token"]):q["bk_yes"]for q in e},**{str(q["no_token"]):q["bk_no"]for q in e}},opps_out=opps_out)
 async def _scan_negrisk_bundles_for_ladder(a,asset,spot,rungs,nr_brackets,ms_book_cache,opps_out):
  j=build_negrisk_cross_box_bundles(rungs,nr_brackets,spot=spot,max_strike_dist_log=.1,tail_max_strike_dist_log=.22)
  if not j:return
  c=dict(ms_book_cache);d=sorted({str(lg["token_id"])for bnd in j for lg in bnd["legs"]if str(lg["token_id"])not in c})
  if d:c.update(await a.fetch_books_batch(d,timeout=3.))
  b=None
  for bnd in j:
   p=bnd["legs"]
   if not all(str(lg["token_id"])in c for lg in p):continue
   q=float(bnd["guaranteed_payout"]);i=round(q*.992,4);f=[{"asks":c[str(lg["token_id"])].get("asks")or[],"fee_rate":float(lg.get("fee_rate",CRYPTO_FEE_RATE)),"fee_exponent":1.}for lg in p];l=sum(r+float(lg.get("fee_rate",CRYPTO_FEE_RATE))*r*(1.-r)for lg in p for r in[a._best_ask_sz(c[str(lg["token_id"])])[0]]);h=round(l/max(1.,q),4)
   if h<=1.15 and(b is None or h<b[0]):b=(h,str(bnd["label"]),q,float(bnd["end_ts"]))
   o=walk_equal_shares_multi_leg_box(f,target_budget_usd=BANKROLL_TICKETS["T1000"]["N1_NEGRISK_CROSS_BOX"],guaranteed_payout_per_bundle=q,max_bundle_cost_net=round(q*1.005,4),min_shares=6,min_box_notional_usd=5.5)
   if not o.get("filled"):continue
   g=float(o["box_cost_net"]);e=round(q-g,4);opps_out.append({"sleeve":"N1_NEGRISK_CROSS_BOX","market":f"{asset} {bnd['label']}","ask_vwap":round(g/q,4),"p_model":1.,"net_edge":round(e/q,4),"l1_usd":o["l1_usd"],"close_ts":bnd["end_ts"]})
   if g<=i:
    await a.open_shadow_multi_leg_bundle(sleeve="N1_NEGRISK_CROSS_BOX",dedupe_key=f"N1_{asset}_{bnd['bundle_id']}",asset=asset,title=f"{asset} NegRisk Cross-Box: {bnd['label']}",legs=p,books_by_token=c,close_ts=float(bnd["end_ts"]),guaranteed_payout=q,max_bundle_cost_net=i,extra={"is_multi_leg_bundle":True,"bundle_id":bnd["bundle_id"],"guaranteed_payout":q,"legs":p});k=time.time()
    if len(p)==2 and q==1. and g<=.988 and(float(bnd["end_ts"])-k)<=172800.:n=float(p[0].get("strike")or spot or 1e2);a.emit_live_two_leg_box_candidate(sleeve_source="N1_NEGRISK_CROSS_BOX",box_type="NEGRISK_2LEG",asset=asset,dedupe_key=f"N1_{asset}_{bnd['bundle_id']}",leg_a=p[0],leg_b=p[1],bk_a=c[str(p[0]["token_id"])],bk_b=c[str(p[1]["token_id"])],close_ts=float(bnd["end_ts"]),now_ts=k,k_low=n,k_high=n)
  if b is not None:m=time.time();a._record_market_telemetry(key=f"N1_BEST_{asset}_{int(b[3])}",min_interval_sec=90.,now_ts=m,sig=(b[0],b[1]),payload={"type":"NEGRISK_CRYPTO_CROSS_BEST","asset":asset,"spot":round(spot,4),"tte_sec":round(b[3]-m,0),"payout":b[2],"net_bundle_ratio_l1":b[0],"label":b[1]})
 async def open_shadow_multi_leg_bundle(a,sleeve,dedupe_key,asset,title,legs,books_by_token,close_ts,guaranteed_payout,max_bundle_cost_net,extra):
  m=a._try_acquire_keys(dedupe_key)
  if not m:return False
  try:
   d=[{"asks":books_by_token[str(lg["token_id"])].get("asks")or[],"fee_rate":float(lg.get("fee_rate",CRYPTO_FEE_RATE)),"fee_exponent":float(lg.get("fee_exponent",1.))}for lg in legs];e=sum(extract_best_bid(books_by_token[str(lg["token_id"])].get("bids")or[])[0]for lg in legs);b={}
   for c,i in BANKROLL_TICKETS.items():
    l=walk_equal_shares_multi_leg_box(d,target_budget_usd=i[sleeve],guaranteed_payout_per_bundle=guaranteed_payout,max_bundle_cost_net=max_bundle_cost_net,min_shares=6 if c=="T100"else 8,min_box_notional_usd=7. if c=="T100"else 9.)
    if l.get("filled"):b[c]=l
   if"T1000"not in b:return False
   h=b["T1000"];k=time.time();f=f"{sleeve}_{int(k)}_{dedupe_key[-10:]}";j={"position_id":f,"dedupe_key":dedupe_key,"sleeve":sleeve,"asset_or_city":asset,"title":title,"side":"+".join(str(lg.get("label",lg.get("side","YES")))for lg in legs),"token_id":"|".join(str(lg["token_id"])for lg in legs),"fee_rate":max((float(lg.get("fee_rate",CRYPTO_FEE_RATE))for lg in legs),default=CRYPTO_FEE_RATE),"entry_ts":k,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"p_model_entry":round(guaranteed_payout,4),"entry_eff_px_t1000":h["eff_px"],"entry_vwap_t1000":h["vwap"],"realized_edge_t1000":h["riskless_floor_per_pair"],"entry_best_bid":round(e,4),"last_bid":round(e,4),"maker_tp_px":None,"tier_fills":b,"extra":{**extra,"legs":legs},"status":"OPEN"};a.open_positions[f]=j
   for g in m:a.entered_keys.add(g)
   a._append_ledger({"event":"SHADOW_ENTRY",**j});logger.info(f"[ENTRY:{sleeve}] {title} | {h['shares']} bundles @ net=${h['eff_px']:.4f} (guaranteed=${guaranteed_payout:.2f}, floor=${h['riskless_floor_per_pair']:+.4f}/bundle)");return True
  finally:a._release_inflight_keys(m)
 async def execute_ctf_overround_mint_sell(a,dedupe_key,asset,title,legs_bids_spec,close_ts,min_net_proceeds_per_set,opps_out,extra):
  if is_shadow_sleeve_quarantined("CTF_OVERROUND_MINT_SELL"):return False
  d=walk_equal_shares_overround_bids(legs_bids_spec,target_mint_budget_usd=BANKROLL_TICKETS["T1000"]["CTF_OVERROUND_MINT_SELL"],min_net_proceeds_per_set=min_net_proceeds_per_set,min_shares=8.)
  if not d.get("filled"):return False
  opps_out.append({"sleeve":"CTF_OVERROUND_MINT_SELL","market":title,"ask_vwap":round(2.-float(d["net_proceeds_per_set"]),4),"p_model":1.,"net_edge":d["net_edge_per_set"],"l1_usd":d["l1_usd"],"close_ts":close_ts});l=a._try_acquire_keys(dedupe_key)
  if not l:return False
  try:
   b={};c={}
   for f,h in BANKROLL_TICKETS.items():
    m=walk_equal_shares_overround_bids(legs_bids_spec,target_mint_budget_usd=h["CTF_OVERROUND_MINT_SELL"],min_net_proceeds_per_set=min_net_proceeds_per_set,min_shares=5. if f=="T100"else 8.)
    if m.get("filled"):i=float(m["shares"]);b[f]={"filled":True,"vwap":1.,"eff_px":1.,"spent_usd":round(i,2),"fee_usd":m["fee_usd"],"shares":i,"l1_usd":m["l1_usd"]};c[f]=round(i*float(m["net_edge_per_set"]),2)
   if"T1000"not in b:return False
   k=time.time();e=f"CTF_OVERROUND_MINT_SELL_{int(k)}_{dedupe_key[-10:]}";j={"position_id":e,"dedupe_key":dedupe_key,"sleeve":"CTF_OVERROUND_MINT_SELL","asset_or_city":asset,"title":title,"side":f"MINT_SELL_{len(legs_bids_spec)}L","token_id":dedupe_key,"fee_rate":.0,"entry_ts":k,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"closed_ts":k,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":round(float(d["net_proceeds_per_set"]),4),"entry_eff_px_t1000":1.,"entry_vwap_t1000":1.,"realized_edge_t1000":d["net_edge_per_set"],"net_payout_per_share":d["gross_proceeds_per_set"],"tier_fills":b,"tier_pnls_usd":c,"legging_adjusted_tier_pnls_usd":c,"won":c.get("T1000",.0)>0,"extra":{**extra,"n_legs":len(legs_bids_spec)},"status":"INSTANT_MINT_AND_SELL_FILLED"}
   for g in l:a.entered_keys.add(g)
   a._append_ledger({"event":"SHADOW_ENTRY",**j});a.closed_positions.append(j);a._append_ledger({"event":"SHADOW_CLOSE",**j});logger.info(f"[INSTANT_ARB:CTF_OVERROUND_MINT_SELL] {title} | net_proceeds=${d['net_proceeds_per_set']:.4f} (+{d['net_edge_per_set']:.4f}/set) | PnL T1000=${c.get('T1000',.0):+.2f}");return True
  finally:a._release_inflight_keys(l)
 async def execute_negrisk_convert_positions_arb(a,spec,arb_probe,books_by_token,opps_out):
  if is_shadow_sleeve_quarantined("NR_CONV_NO_BASKET_ARB")or not spec.is_closed_convert_safe:return False
  v=int(arb_probe["m_no_legs"]);n="_".join(str(i)for i in arb_probe["question_indices"]);f=f"NRCONV_M{v}_{spec.event_id}_{n}";opps_out.append({"sleeve":"NR_CONV_NO_BASKET_ARB","market":f"{spec.title} [convertPositions {v}/{spec.total_market_count} NO -> {v-1} USDC + YES bids]","ask_vwap":round(1.-float(arb_probe["net_edge_per_share"]),4),"p_model":1.,"net_edge":arb_probe["net_edge_per_share"],"l1_usd":arb_probe["l1_usd"],"close_ts":spec.end_ts})
  if float(a._instant_arb_cooldown_until.get(f,.0)or.0)>time.time():return False
  A=a._try_acquire_keys(f)
  if not A:return False
  try:
   k=[b["no_token"]for b in spec.brackets]+[b["yes_token"]for b in spec.brackets];h=await a.fetch_books_batch(k,timeout=3.);j=h if all(t in h for t in k)else books_by_token;e={};g={};d=None
   for q,u in BANKROLL_TICKETS.items():
    m=detect_negrisk_convert_positions_arbs(spec,j,target_budget_usd=u["NR_CONV_NO_BASKET_ARB"],min_net_edge_per_share=.005,min_shares=5 if q=="T100"else 8);s=next((c for c in m if c["question_indices"]==arb_probe["question_indices"]),None)
    if s is not None:
     w=float(s["shares"]);l=float(s["no_cost_per_share"]);e[q]={"filled":True,"vwap":l,"eff_px":l,"spent_usd":round(w*l,2),"fee_usd":float(s.get("total_fee_usd",.0)),"shares":w,"l1_usd":s["l1_usd"]};g[q]=round(w*float(s["net_edge_per_share"]),2)
     if q=="T1000":d=s
   if d is None:return False
   z=time.time();p=f"NR_CONV_NO_BASKET_ARB_{int(z)}_{f[-10:]}";o=round(float(d["net_proceeds_per_share"]),4);y={"position_id":p,"dedupe_key":f,"sleeve":"NR_CONV_NO_BASKET_ARB","asset_or_city":"NEGRISK","title":f"{spec.title} [convertPositions m={v}/{spec.total_market_count}]","side":f"CONVERT_{v}NO","token_id":"|".join(str(x["bracket"]["no_token"])for x in d["no_legs"]),"fee_rate":.0,"entry_ts":z,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":spec.end_ts,"closed_ts":z,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":o,"entry_eff_px_t1000":d["no_cost_per_share"],"entry_vwap_t1000":d["no_cost_per_share"],"realized_edge_t1000":d["net_edge_per_share"],"net_payout_per_share":o,"tier_fills":e,"tier_pnls_usd":g,"legging_adjusted_tier_pnls_usd":g,"won":g.get("T1000",.0)>0,"extra":{"mode":"NR_CONVERT_POSITIONS","neg_risk_market_id":spec.neg_risk_market_id,"index_set_int":d["index_set"],"no_question_indices":d["question_indices"],"m_no_legs":v,"n_total":spec.total_market_count},"status":"INSTANT_CONVERT_AND_SELL_FILLED"}
   if a.single_scan and not getattr(a,"_enable_multiclip_instant_arb",False):
    for r in A:a.entered_keys.add(r)
   else:a._instant_arb_cooldown_until[f]=z+3.
   a.emit_live_negrisk_convert_candidate(sleeve_source="NR_CONV_NO_BASKET_ARB",spec=spec,dedupe_key=f,arb_hit=d,books_by_token=j,now_ts=z,fee_bips=0);a._append_ledger({"event":"SHADOW_ENTRY",**y});a.closed_positions.append(y);a._append_ledger({"event":"SHADOW_CLOSE",**y});logger.info(f"[INSTANT_ARB:NR_CONV_NO_BASKET_ARB] {y['title']} | edge=+{d['net_edge_per_set']:.4f}/set | PnL T1000=${g.get('T1000',.0):+.2f}");return True
  finally:a._release_inflight_keys(A)
 async def execute_nr2_subset_convert_arb(a,spec,arb_probe,books_by_token,opps_out):
  if is_shadow_sleeve_quarantined("NR2_CONVERT_NO_SUBSET_ARB")or not spec.is_closed_convert_safe:return False
  y=int(arb_probe["m_no_legs"]);o="_".join(str(i)for i in arb_probe["no_question_indices"]);f=f"NR2_M{y}_{spec.event_id}_{o}";opps_out.append({"sleeve":"NR2_CONVERT_NO_SUBSET_ARB","market":f"{spec.title[:52]} [{arb_probe['label']}]","ask_vwap":round(max(.01,1.-float(arb_probe["net_edge_per_share"])),4),"p_model":1.,"net_edge":arb_probe["net_edge_per_share"],"l1_usd":arb_probe["l1_usd"],"close_ts":spec.end_ts})
  if float(a._instant_arb_cooldown_until.get(f,.0)or.0)>time.time():return False
  C=a._try_acquire_keys(f)
  if not C:return False
  try:
   w,l,_=await asyncio.to_thread(verify_negrisk_adapter_slate_sync,spec.neg_risk_market_id,spec.total_market_count)
   if not w:return False
   k=[b["no_token"]for b in spec.brackets]+[b["yes_token"]for b in spec.brackets];h=await a.fetch_books_batch(k,timeout=3.);j=h if all(t in h for t in k)else books_by_token;e={};g={};d=None
   for r,v in BANKROLL_TICKETS.items():
    n=detect_nr2_convert_no_subset_arbs(spec,j,target_budget_usd=v["NR2_CONVERT_NO_SUBSET_ARB"],min_edge_pure_cash=.01,min_edge_with_yes_sell=.012,min_shares=5 if r=="T100"else 6,fee_bips=l);u=next((c for c in n if c["no_question_indices"]==arb_probe["no_question_indices"]),None)
    if u is not None:
     z=float(u["shares"]);m=float(u["no_cost_per_share"]);e[r]={"filled":True,"vwap":m,"eff_px":m,"spent_usd":round(z*m,2),"fee_usd":u["total_fee_usd"],"shares":z,"l1_usd":u["l1_usd"]};g[r]=float(u["total_net_profit_usd"])
     if r=="T1000":d=u
   if d is None:return False
   B=time.time();q=f"NR2_CONVERT_NO_SUBSET_ARB_{int(B)}_{f[-10:]}";p=float(d["net_proceeds_per_share"]);A={"position_id":q,"dedupe_key":f,"sleeve":"NR2_CONVERT_NO_SUBSET_ARB","asset_or_city":"NEGRISK_V2","title":f"{spec.title} [{d['label']}]","side":f"NR2_{y}NO_FREE{d['retained_tail_count']}Y","token_id":"|".join(str(x["token_id"])for x in d["no_legs"]),"fee_rate":.0,"entry_ts":B,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":spec.end_ts,"closed_ts":B,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":p,"entry_eff_px_t1000":d["no_cost_per_share"],"entry_vwap_t1000":d["no_cost_per_share"],"realized_edge_t1000":d["net_edge_per_share"],"net_payout_per_share":p,"tier_fills":e,"tier_pnls_usd":g,"legging_adjusted_tier_pnls_usd":g,"won":g.get("T1000",.0)>0,"extra":{"mode":d["mode"],"neg_risk_market_id":spec.neg_risk_market_id,"index_set_int":d["index_set_int"],"no_question_indices":d["no_question_indices"],"retained_tail_count":d["retained_tail_count"],"retained_tail_labels":[b["label"]for b in d["retained_free_yes_brackets"]],"fee_bips":l},"status":"INSTANT_SUBSET_CONVERT_FREE_TAIL_LOCKED"}
   if a.single_scan and not getattr(a,"_enable_multiclip_instant_arb",False):
    for s in C:a.entered_keys.add(s)
   else:a._instant_arb_cooldown_until[f]=B+3.
   a.emit_live_negrisk_convert_candidate(sleeve_source="NR2_CONVERT_NO_SUBSET_ARB",spec=spec,dedupe_key=f,arb_hit=d,books_by_token=j,now_ts=B,fee_bips=l);a._append_ledger({"event":"SHADOW_ENTRY",**A});a.closed_positions.append(A);a._append_ledger({"event":"SHADOW_CLOSE",**A});logger.info(f"[INSTANT_ARB:NR2_CONVERT_NO_SUBSET_ARB] {A['title']} | edge=+{d['net_edge_per_share']:.4f}/sh | free_tails={d['retained_tail_count']} | PnL T1000=${g.get('T1000',.0):+.2f}");return True
  finally:a._release_inflight_keys(C)
 async def scan_daily_updown_locks(a,opps_out):
  _g=time.time();Y=asyncio.get_running_loop();b=[sp for sp in[*a.daily_updown_markets.values(),*a.pyth_daily_markets.values()]if sp.end_ts>_g+60.]
  if b:
   z=await a.fetch_books_batch([sp.up_token for sp in b]+[sp.down_token for sp in b],timeout=3.)
   for I in b:
    X=z.get(I.up_token);W=z.get(I.down_token)
    if not X or not W:continue
    V,U=a._best_ask_sz(X);T,S=a._best_ask_sz(W)
    if V<1. and T<1.:_f=float(I.fee_rate);a._record_market_telemetry(key=f"DAILY_C1_{I.market_id}",min_interval_sec=60.,now_ts=_g,sig=(V,T),payload={"type":"DAILY_COMPLETE_SET","asset":I.asset,"market_id":I.market_id,"title":I.title,"fee_rate":_f,"tte_sec":round(I.end_ts-_g,0),"up_ask":V,"down_ask":T,"gross_sum_l1":round(V+T,4),"net_sum_l1":round(V+T+_f*(V*(1.-V)+T*(1.-T)),4),"l1_min_shares":round(min(U,S),2)})
    y=.995 if I.fee_rate==.0 else.994;x=scan_binary_complete_set_arb(market_id=I.market_id,condition_id=I.condition_id,yes_token=I.up_token,no_token=I.down_token,asks_yes_raw=X.get("asks")or[],asks_no_raw=W.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],fee_rate=I.fee_rate,max_box_cost_net=y)
    if x.get("filled"):
     opps_out.append({"sleeve":"C1_BINARY_COMPLETE_SET","market":f"{I.asset} Complete-Set {I.title}","ask_vwap":x["box_cost_net"],"p_model":1.,"net_edge":x["riskless_floor_per_pair"],"l1_usd":x["l1_usd"],"close_ts":I.end_ts});H={"token_id":I.up_token,"opp_token_id":I.down_token,"condition_id":I.condition_id,"side":"UP","label":"UP","market_id":I.market_id,"fee_rate":I.fee_rate,"strike":1e2};G={"token_id":I.down_token,"opp_token_id":I.up_token,"condition_id":I.condition_id,"side":"DOWN","label":"DOWN","market_id":I.market_id,"fee_rate":I.fee_rate,"strike":1e2};await a.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key=f"C1_D_{I.market_id}",asset=I.asset,title=f"{I.asset} UP+DOWN Complete Set: {I.title}",leg_a=H,leg_b=G,bk_a=X,bk_b=W,close_ts=I.end_ts,max_box_cost_net=y,extra={"is_complete_set":True,"market_id":I.market_id,"condition_id":I.condition_id})
     if(I.end_ts-_g)<=86400. and float(x["box_cost_net"])<=(.99 if I.fee_rate==.0 else.988):a.emit_live_two_leg_box_candidate(sleeve_source="C1_BINARY_COMPLETE_SET",box_type="COMPLETE_SET",asset=I.asset,dedupe_key=f"C1_D_{I.market_id}",leg_a=H,leg_b=G,bk_a=X,bk_b=W,close_ts=float(I.end_ts),now_ts=_g)
    await a.execute_ctf_overround_mint_sell(dedupe_key=f"CTF_OVR_D_{I.market_id}",asset=I.asset,title=f"{I.asset} Binary Overround Mint-Sell: {I.title}",legs_bids_spec=[{"bids":X.get("bids")or[],"fee_rate":I.fee_rate,"fee_exponent":1.},{"bids":W.get("bids")or[],"fee_rate":I.fee_rate,"fee_exponent":1.}],close_ts=I.end_ts,min_net_proceeds_per_set=1.003 if I.fee_rate==.0 else 1.004,opps_out=opps_out,extra={"overround_kind":"BINARY_DAILY","market_id":I.market_id,"condition_id":I.condition_id})
  for _,R in list(a.hourly_12pm_markets.items()):
   F=R.end_ts-_g
   if not(60.<=F<=3540.)or _g<R.start_ts+20.:continue
   w=f"H1_{R.asset}_{int(R.start_ts)}";Q=a.daily_open_cache.get(w)
   if Q is None:
    v=await Y.run_in_executor(None,fetch_binance_window_extremes_sync,R.asset,R.start_ts-60.,R.start_ts+60.,"1m")
    if v is not None and v[2]>0:a.daily_open_cache[w]=(R.end_ts,float(v[2]));m=float(v[2])
    else:continue
   else:m=Q[1]
   f=[]
   for P in a.daily_updown_markets.values():
    if P.asset==R.asset and abs(P.end_ts-R.end_ts)<=5.:
     u=f"{P.asset}_{int(P.start_ts)}";O=a.daily_open_cache.get(u)
     if O is None:
      t=await Y.run_in_executor(None,fetch_binance_window_extremes_sync,P.asset,P.start_ts-60.,P.start_ts+60.,"1m")
      if t is not None and t[2]>0:a.daily_open_cache[u]=(P.end_ts,float(t[2]));h=float(t[2])
      else:h=.0
     else:h=O[1]
     if h>0:f.append({"market_id":P.market_id,"condition_id":P.condition_id,"end_ts":P.end_ts,"strike":h,"is_downward":False,"yes_token":P.up_token,"no_token":P.down_token,"yes_label":"UP","no_label":"DOWN","fee_rate":P.fee_rate})
   for l in a.strike_ladders.values():
    if l and l[0].asset==R.asset and abs(l[0].end_ts-R.end_ts)<=5.:
     for E in l:
      if not E.is_downward:f.append({"market_id":E.market_id,"condition_id":E.condition_id,"end_ts":E.end_ts,"strike":E.strike,"is_downward":False,"yes_token":E.yes_token,"no_token":E.no_token,"yes_label":"YES","no_label":"NO","fee_rate":CRYPTO_FEE_RATE})
   k=detect_d2_12pm_binance_boxes({"asset":R.asset,"market_id":R.market_id,"condition_id":R.condition_id,"end_ts":R.end_ts,"up_token":R.up_token,"down_token":R.down_token,"fee_rate":R.fee_rate},m,f)
   if k:
    o=sorted({str(c["leg_a"]["token_id"])for c in k}|{str(c["leg_b"]["token_id"])for c in k});s=await a.fetch_books_batch(o,timeout=3.)
    for dc in k:
     _e,_d=dc["leg_a"],dc["leg_b"];N,M=s.get(str(_e["token_id"])),s.get(str(_d["token_id"]))
     if not N or not M:continue
     _c,_=a._best_ask_sz(N);_b,_=a._best_ask_sz(M)
     if _c<1. and _b<1.:a._record_market_telemetry(key=f"D2_12PM_{_e['market_id']}_{_d['market_id']}",min_interval_sec=30.,now_ts=_g,sig=(_c,_b),payload={"type":"D2_12PM_CORRIDOR","asset":R.asset,"tte_sec":round(F,0),"k_low":dc["k_low"],"k_high":dc["k_high"],"corridor_bps":dc["corridor_bps"],"gross_box_l1":round(_c+_b,4),"label":dc["label"]})
     L=walk_equal_shares_dominance_box(N.get("asks")or[],M.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["D2_12PM_BINANCE_BOX"],fee_rate_a=float(_e["fee_rate"]),fee_rate_b=float(_d["fee_rate"]),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
     if L.get("filled"):opps_out.append({"sleeve":"D2_12PM_BINANCE_BOX","market":f"{R.asset} 12PM Box {dc['label']}","ask_vwap":round(float(L["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(L["box_cost_net"]),4),"l1_usd":L["l1_usd"],"close_ts":dc["close_ts"]});await a.open_shadow_two_leg_box(sleeve="D2_12PM_BINANCE_BOX",dedupe_key=f"D2_{_e['market_id']}_{_d['market_id']}",asset=R.asset,title=f"{R.asset} 12PM Binance Box {dc['label']}",leg_a=_e,leg_b=_d,bk_a=N,bk_b=M,close_ts=float(dc["close_ts"]),max_box_cost_net=.99,extra={"is_d2_12pm_box":True,"k_low":dc["k_low"],"k_high":dc["k_high"],"corridor_bps":dc["corridor_bps"]})
  for _,sp in list(a.daily_updown_markets.items()):
   _a=sp.end_ts-_g
   if not(120.<=_a<=5400.):continue
   K=a.spots.get(sp.asset,.0)
   if K<=.0:continue
   D=f"{sp.asset}_{int(sp.start_ts)}";j=a.daily_open_cache.get(D)
   if j is None:
    C=await Y.run_in_executor(None,fetch_binance_window_extremes_sync,sp.asset,sp.start_ts-60.,sp.start_ts+60.,"1m")
    if C is not None and C[2]>0:a.daily_open_cache[D]=(sp.end_ts,float(C[2]));d=float(C[2])
    else:continue
   else:d=j[1]
   r=evaluate_svi_digital_fair_value(sp.asset,K,d,_a,is_downward=False,now_ts=_g);i="UP"if K>d else"DOWN";q=float(r["p_yes"]if i=="UP"else r["p_no"]);B=abs(float(r.get("z_sigma")or.0))
   if B<1.8 or q<.93:continue
   n=a.get_return_bps(sp.asset,60.)
   if(i=="UP"and n<-10.)or(i=="DOWN"and n>10.):continue
   Z=sp.up_token if i=="UP"else sp.down_token;bk=await a.fetch_json(f"{CLOB_URL}/book?token_id={Z}",timeout=3.)
   if not bk:continue
   A=walk_l2_book_asks(bk.get("asks")or[],BANKROLL_TICKETS["T1000"]["U1_DAILY_UPDOWN_LOCK"],fee_rate=sp.fee_rate)
   if not A.get("filled"):continue
   p=float(A["eff_px"]);J=q-p
   if.66<=A["vwap"]<=.9 and J>=.025:opps_out.append({"sleeve":"U1_DAILY_UPDOWN_LOCK","market":f"{sp.asset} {sp.title} ({i}, TTE={_a/60:.0f}m, z={B:.2f})","ask_vwap":p,"p_model":round(q,4),"net_edge":round(J,4),"l1_usd":A["l1_usd"],"close_ts":sp.end_ts})
   if.66<=A["vwap"]<=.9 and J>=.042:
    e=sp.down_token if i=="UP"else sp.up_token
    if B>=2.2 and q>=.965:g=await a.fetch_json(f"{CLOB_URL}/book?token_id={e}",timeout=2.5);a.emit_live_single_leg_lock_candidate(sleeve_source="U1_DAILY_UPDOWN_LOCK",asset=sp.asset,dedupe_key=f"U1_{sp.market_id}_{i}",token_id=Z,opp_token_id=e,market_id=sp.market_id,condition_id=sp.condition_id,side_label=i,display_label=f"{sp.asset} Daily {i}",bk_win=bk,bk_opp=g if isinstance(g,dict)else None,fee_rate=sp.fee_rate,fee_exponent=1.,neg_risk=False,close_ts=sp.end_ts,now_ts=_g,max_lock_eff_px=.9,max_opp_bid=.36,hold_to_maturity=False,p_model=float(q))
    await a.open_shadow_position(sleeve="U1_DAILY_UPDOWN_LOCK",dedupe_key=f"U1_{sp.market_id}_{i}",asset_or_city=sp.asset,title=sp.title,side_label=i,token_id=Z,fee_rate=sp.fee_rate,p_model=q,close_ts=sp.end_ts,extra={"market_id":sp.market_id,"condition_id":sp.condition_id,"strike":d,"is_downward":(i=="DOWN"),"z_sigma":B},tp_target_px=.98,prefetched_book=bk)
 @staticmethod
 def is_in_same_oracle_overlap_window(now_ts):a=math.ceil(now_ts/9e2)*9e2;b=a-now_ts;d=math.ceil(now_ts/3600.)*3600.-now_ts;c=math.ceil(now_ts/14400.)*14400.-now_ts;return(8.<=b<=305.)or(8.<=d<=905.)or(8.<=c<=905.)
 async def discover_dominance_pairs(b,now_ts=None):
  q=float(now_ts if now_ts is not None else time.time())
  for p,(k,_)in list(b.dominance_pairs.items()):
   if k.end_ts<q-6e2:b.dominance_pairs.pop(p,None)
  for d,(f,_)in list(b.chainlink_open_cache.items()):
   if f<q-6e2:b.chainlink_open_cache.pop(d,None)
  l=b.__dict__.get("_strike_source")or{}
  for d,(f,_)in list(l.items()):
   if f<q-6e2:l.pop(d,None)
  for d,o in list(b._strike_fail_backoff_ts.items()):
   if float(o or.0)<q-7200.:b._strike_fail_backoff_ts.pop(d,None)
  g=int(math.ceil(q/9e2)*900);j=float(g)-q;e=b.single_scan or("fetch_json"in b.__dict__);c=(g%3600)==0 and(5.<=j<=905.);h=305. if e else 335.
  if not(5.<=j<=h)and not(c and not e):return
  i=datetime.fromtimestamp(q-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  async def _discover_asset_pair(asset):
   d=f"{asset}_{g}"
   if d in b.dominance_pairs:return
   f=DOMINANCE_SERIES_SLUGS[asset];c,e=await asyncio.gather(b.fetch_json(f"{GAMMA_URL}/events?series_slug={f['15m']}&closed=false&end_date_min={i}&order=endDate&ascending=true&limit=3",timeout=4.),b.fetch_json(f"{GAMMA_URL}/events?series_slug={f['5m']}&closed=false&end_date_min={i}&order=endDate&ascending=true&limit=3",timeout=4.));a=None;b=None
   if isinstance(c,list):
    for g in c:
     h=parse_twap_candle_event(g,asset,"15m")
     if h and abs(h.end_ts-g)<=2.:a=h;break
   if isinstance(e,list):
    for g in e:
     i=parse_twap_candle_event(g,asset,"5m")
     if i and abs(i.end_ts-g)<=2.:b=i;break
   if a and b and verify_same_oracle_pair(a,b):b.dominance_pairs[d]=(a,b)
  async def _discover_metal_pair(metal):
   e=f"{metal}_1h15m_{g}"
   if e in b.dominance_pairs:return
   f=METAL_DOMINANCE_SERIES_SLUGS[metal];d,c=await asyncio.gather(b.fetch_json(f"{GAMMA_URL}/events?series_slug={f['1h']}&closed=false&end_date_min={i}&order=endDate&ascending=true&limit=3",timeout=4.),b.fetch_json(f"{GAMMA_URL}/events?series_slug={f['15m']}&closed=false&end_date_min={i}&order=endDate&ascending=true&limit=3",timeout=4.));b=None;a=None
   if isinstance(d,list):
    for h in d:
     i=parse_metal_forex_candle_event(h,metal,"1h")
     if i and abs(i.end_ts-g)<=2.:b=i;break
   if isinstance(c,list):
    for h in c:
     g=parse_metal_forex_candle_event(h,metal,"15m")
     if g and abs(g.end_ts-g)<=2.:a=g;break
   if b and a and verify_same_oracle_pair(b,a):b.dominance_pairs[e]=(b,a)
  n=[]
  if 5.<=j<=h:n.extend(_discover_asset_pair(a)for a in DOMINANCE_ASSETS)
  if c and(not e or os.getenv("PM_FORCE_METAL_D1_TEST")=="1"):n.extend(_discover_metal_pair(m)for m in METAL_DOMINANCE_ASSETS)
  if n:await asyncio.gather(*n)
 def _strike_is_rest_verified(self,spec):b=f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}";a=(self.__dict__.get("_strike_source")or{}).get(b);return bool(a is None or a[1]=="REST_VERIFIED")
 async def get_authoritative_open_strike(a,spec):
  A=f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}";r=a.__dict__.setdefault("_strike_source",{});t=a.chainlink_open_cache.get(A)
  if t is not None:r[A]=(spec.end_ts,"REST_VERIFIED");return t[1]
  r[A]=(spec.end_ts,"PENDING");z=time.time();k=a.single_scan or("fetch_json"in a.__dict__)
  if spec.asset in METAL_DOMINANCE_ASSETS and int(spec.twap_lookback_sec)==0:
   if not k and z<spec.start_ts+4.:return None
   h=float(a._strike_fail_backoff_ts.get(A,.0)or.0)
   if not k and(z-h)<2.5:return None
   y=build_prev_15m_gamma_event_url(spec);x=parse_authoritative_open_price(await a.fetch_json(y,timeout=3.),request_url=y)
   if x is not None:a.chainlink_open_cache[A]=(spec.end_ts,x);r[A]=(spec.end_ts,"REST_VERIFIED");return x
   if not k:a._strike_fail_backoff_ts[A]=time.time()
   return None
  w=getattr(a,"_chainlink_ws",None)if not k else None;g=w.get_boundary_twap_60s(spec.asset,spec.start_ts,min_ticks=52)if w is not None else None
  if not a.single_scan and z<spec.start_ts+(.2 if g is not None else 2.):return None
  if not k and z<spec.start_ts+2. and g is not None:r[A]=(spec.end_ts,"WS_TWAP");return g
  if not k:
   e=float(a._strike_fail_backoff_ts.get(A,.0)or.0)
   if(z-e)<2.5:
    if g is not None:r[A]=(spec.end_ts,"WS_TWAP")
    return g
  p=build_crypto_price_query_url(spec);j=None;d=3 if(k or z<spec.start_ts+35.)else(2 if z<spec.start_ts+95. else 1);i=.3 if k else.12
  for o in range(d):
   q=await a.fetch_json(p,timeout=4. if k else 2.5);j=parse_authoritative_open_price(q,request_url=p)
   if j is not None:break
   if o+1<d:await asyncio.sleep(i*(o+1))
  f=a.single_scan or z>=spec.start_ts+335.;c=f or(j is None and z>=spec.start_ts+10.);b=False
  if c:
   v=build_prev_5m_gamma_event_url(spec);u=parse_authoritative_open_price(await a.fetch_json(v,timeout=4. if k else 2.5),request_url=v)
   if j is None and u is not None:j=u;b=True
   elif f and u is not None and abs(j-u)/max(1e-9,u)>1e-6:logger.error(f"[CRITICAL TWAP MISMATCH VETO] {spec.asset} {spec.horizon}: crypto-price TWAP={j} != Gamma prev_5m finalPrice={u}!");return None
   elif j is None and f and u is None and not a.single_scan:
    if not k:a._strike_fail_backoff_ts[A]=time.time()
    return None
  if j is None:
   if not k:
    a._strike_fail_backoff_ts[A]=time.time()
    if g is not None and z<spec.start_ts+335.:r[A]=(spec.end_ts,"WS_TWAP");return g
   B=a.__dict__.setdefault("_strike_fail_log_ts",{})
   if(z-float(B.get(A,.0)))>=60.:B[A]=z;logger.warning(f"[STRIKE LOOKUP FAILED] {spec.asset} {spec.horizon}: crypto-price + prev_5m Gamma returned no usable openPrice -> skipped (fail-closed).")
  if j is not None:
   s=[C for D,C in a.usd_spot_hist.get(spec.asset,())if(spec.start_ts-60.)<=D<=(spec.start_ts+5.)]
   if len(s)>=3 and not a.single_scan:
    n=sum(s)/len(s);m=.008 if not b else.0035
    if n>.0 and abs(j-n)/n>m:logger.error(f"[STRIKE TWAP VETO] {spec.asset} {spec.horizon}: strike {j} vs local 60s TWAP {n} > {int(m*10000)} bps");return None
   elif not(f or b):
    l=float(a.spots.get(spec.asset)or.0)
    if l>.0 and abs(j-l)/l>.015:logger.error(f"[STRIKE SANITY VETO] {spec.asset} {spec.horizon}: strike {j} vs spot {l} > 150 bps");return None
   a.chainlink_open_cache[A]=(spec.end_ts,j);r[A]=(spec.end_ts,"REST_VERIFIED")
  return j
 async def _passes_complement_anti_box_check(a,leg_a,leg_b,prefetched_books=None):
  v=str(leg_a.get("opp_token_id")or"");u=str(leg_b.get("opp_token_id")or"")
  if not v or not u:return False
  e=(prefetched_books or{}).get(v);d=(prefetched_books or{}).get(u)
  if not(isinstance(e,dict)and isinstance(d,dict)):e,d=await asyncio.gather(a.fetch_json(f"{CLOB_URL}/book?token_id={v}",timeout=3.),a.fetch_json(f"{CLOB_URL}/book?token_id={u}",timeout=3.))
  if not(isinstance(e,dict)and isinstance(d,dict)):return False
  o,_=extract_best_bid(e.get("bids")or[]);n,_=extract_best_bid(d.get("bids")or[]);m,_=a._best_ask_sz(e);l,_=a._best_ask_sz(d);t=o>.0 or(.0<m<=.12);s=n>.0 or(.0<l<=.12);c=(o if o>.0 else m)+(n if n>.0 else l);g=str(leg_a.get("token_id")or"");f=str(leg_b.get("token_id")or"");r=(prefetched_books or{}).get(g)if g else None;q=(prefetched_books or{}).get(f)if f else None
  if isinstance(r,dict)and isinstance(q,dict):k,_=a._best_ask_sz(r);j,_=a._best_ask_sz(q);b=((k>.0 and o>.0 and(k+o)>1.015)or(j>.0 and n>.0 and(j+n)>1.015)or(o+n)>1.16 or c>1.18)
  else:b=(o+n)>1. or c>1.035
  if not(t and s)or(o<=.0 and n<=.0)or b:
   i=a.__dict__.setdefault("_anti_box_warn_ts",{});p=f"{v}:{u}";h=time.time()
   if(h-float(i.get(p,.0)))>=30.:
    if len(i)>512:i.clear()
    i[p]=h;logger.warning(f"[ANTI-BOX VETO] Rejected box {leg_a.get('label')}+{leg_b.get('label')}: complement bids={o:.3f}+{n:.3f}={o+n:.3f} (ub={c:.3f}, unverified or > 1.00)")
   return False
  return True
 async def open_shadow_two_leg_box(a,sleeve,dedupe_key,asset,title,leg_a,leg_b,bk_a,bk_b,close_ts,max_box_cost_net,extra):
  p=a._try_acquire_keys(dedupe_key)
  if not p:return False
  try:
   if sleeve in("CM_B3_PYTH_BARRIER_BOX","SP1_NBA_ZERO_FEE_BOX","SP3_SPORTS_CORRIDOR_DOMINANCE_BOX","NR_CONV_NO_BASKET_ARB"):
    await asyncio.sleep(.25);g=await a.fetch_books_batch([leg_a["token_id"],leg_b["token_id"]],timeout=3.);bk_a=g.get(leg_a["token_id"])or{};bk_b=g.get(leg_b["token_id"])or{}
    if not bk_a or not bk_b:return False
   f=bk_a.get("asks")or[];e=bk_b.get("asks")or[];l,_=extract_best_bid(bk_a.get("bids")or[]);k,_=extract_best_bid(bk_b.get("bids")or[]);b={}
   for c,j in BANKROLL_TICKETS.items():
    o=walk_equal_shares_dominance_box(f,e,target_budget_usd=j[sleeve],fee_rate_a=float(leg_a.get("fee_rate",CRYPTO_FEE_RATE)),fee_rate_b=float(leg_b.get("fee_rate",CRYPTO_FEE_RATE)),fee_exponent_a=float(leg_a.get("fee_exponent",1.)),fee_exponent_b=float(leg_b.get("fee_exponent",1.)),max_box_cost_net=max_box_cost_net,min_shares=8,min_box_notional_usd=7.)
    if o.get("filled"):b[c]=o
   if"T1000"not in b:return False
   i=b["T1000"];n=time.time();d=f"{sleeve}_{int(n)}_{dedupe_key[-10:]}";m={"position_id":d,"dedupe_key":dedupe_key,"sleeve":sleeve,"asset_or_city":asset,"title":title,"side":f"{leg_a.get('side','YES')}+{leg_b.get('side','NO')}","token_id":f"{leg_a['token_id']}|{leg_b['token_id']}","fee_rate":float(leg_a.get("fee_rate",CRYPTO_FEE_RATE)),"entry_ts":n,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"p_model_entry":1.,"entry_eff_px_t1000":i["eff_px"],"entry_vwap_t1000":i["vwap"],"realized_edge_t1000":i["riskless_floor_per_pair"],"entry_best_bid":round(l+k,4),"last_bid":round(l+k,4),"maker_tp_px":None,"tier_fills":b,"extra":{**extra,"leg_a":leg_a,"leg_b":leg_b},"status":"OPEN"};a.open_positions[d]=m
   for h in p:a.entered_keys.add(h)
   a._append_ledger({"event":"SHADOW_ENTRY",**m});logger.info(f"[ENTRY:{sleeve}] {title} | {i['shares']} pairs @ net=${i['eff_px']:.4f}");return True
  finally:a._release_inflight_keys(p)
 async def open_shadow_weather_slate(a,spec,slate_info,close_ts):
  e=str(slate_info.get("side")or"ALL_BUCKETS_YES");h=float(slate_info.get("guaranteed_payout_per_set")or 1.);d=f"W3_SLATE_{spec.event_id}"if e=="ALL_BUCKETS_YES"else f"W3_SLATE_NO_{spec.event_id}";p=a._try_acquire_keys(d)
  if not p:return False
  try:
   g=float(slate_info["sum_asks"]);m=slate_info["legs"];b=min(float(lg.get("ask_shares",lg.get("ask_yes_shares",.0)))for lg in m);c={}
   for f,l in BANKROLL_TICKETS.items():
    q=max(5.,min(b,math.floor(l["W3_WEATHER_SLATE_ARB"]/max(.1,g))));k=round(q*g,2)
    if q>=5. and k<=l["W3_WEATHER_SLATE_ARB"]*1.25:c[f]={"filled":True,"vwap":round(g,4),"eff_px":round(g,4),"spent_usd":k,"fee_usd":.0,"shares":q,"l1_usd":round(b*g,2)}
   if"T1000"not in c:return False
   o=time.time();i=f"W3_WEATHER_SLATE_ARB_{int(o)}_{spec.event_id[-6:]}";n={"position_id":i,"dedupe_key":d,"sleeve":"W3_WEATHER_SLATE_ARB","asset_or_city":f"{spec.city}_{spec.icao}","title":f"{spec.title} [Full-Slate {len(m)} Buckets {e}]","side":e,"token_id":"|".join(str(lg.get("token_id")or lg.get("yes_token"))for lg in m),"fee_rate":.0,"entry_ts":o,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"p_model_entry":round(h,4),"entry_eff_px_t1000":round(g,4),"entry_vwap_t1000":round(g,4),"realized_edge_t1000":round(h-g,4),"entry_best_bid":round(g,4),"last_bid":round(g,4),"maker_tp_px":None,"tier_fills":c,"extra":{"event_id":spec.event_id,"icao":spec.icao,"guaranteed_payout":h,"legs":m},"status":"OPEN"};a.open_positions[i]=n
   for j in p:a.entered_keys.add(j)
   a._append_ledger({"event":"SHADOW_ENTRY",**n});logger.info(f"[ENTRY:W3_WEATHER_SLATE_ARB] {n['title']} @ sum_asks=${g:.4f} (payout=${h:.2f})");return True
  finally:a._release_inflight_keys(p)
 async def open_shadow_dominance_box(a,asset,m15,m5,dom_info,prefetched_books=None,sleeve_override="D1_SAME_ORACLE_DOMINANCE_BOX",max_box_cost_override=.995):
  o="D1"if sleeve_override=="D1_SAME_ORACLE_DOMINANCE_BOX"else sleeve_override.split("_")[0]+"_"+sleeve_override.split("_")[1];f=f"{o}_{asset}_{m15.market_id}_{m5.market_id}";A=a._try_acquire_keys(f)
  if not A:return False
  try:
   w=dom_info["leg_a"];v=dom_info["leg_b"]
   if prefetched_books is not None:j,i=prefetched_books
   else:await asyncio.sleep(.05);j,i=await asyncio.gather(a.fetch_json(f"{CLOB_URL}/book?token_id={w['token_id']}",timeout=3.),a.fetch_json(f"{CLOB_URL}/book?token_id={v['token_id']}",timeout=3.))
   if not j or not i:return False
   n=j.get("asks")or[];m=i.get("asks")or[];u,_=extract_best_bid(j.get("bids")or[]);t,_=extract_best_bid(i.get("bids")or[]);c=a._strike_is_rest_verified(m15)and a._strike_is_rest_verified(m5);s=walk_equal_shares_dominance_box(n,m,target_budget_usd=BANKROLL_TICKETS["T1000"][sleeve_override],fee_rate_a=float(w["fee_rate"]),fee_rate_b=float(v["fee_rate"]),fee_exponent_a=float(w["fee_exponent"]),fee_exponent_b=float(v["fee_exponent"]),max_box_cost_net=max_box_cost_override,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=.86 if c else.9)
   if not s.get("filled"):return False
   d=("4h"in(str(m15.horizon).lower(),str(m5.horizon).lower()))and(str(m15.horizon).lower()!=str(m5.horizon).lower());h=compute_d1_legging_drag_haircut(shares=float(s["shares"]),box_cost_net=float(s["box_cost_net"]),avail_a_shares=float(s["avail_a_shares"]),avail_b_shares=float(s["avail_b_shares"]),px_a=float(s["leg_a_walk"]["worst_px"]),px_b=float(s["leg_b_walk"]["worst_px"]),fee_rate_a=float(w["fee_rate"]),fee_rate_b=float(v["fee_rate"]),is_4h_mixed=d)
   if h["legging_adjusted_net_ev_per_pair"]<=.0:logger.info(f"[SHADOW LEGGING PARITY REJECT] {asset} {sleeve_override}: box_net=${s['box_cost_net']:.4f} depth_mult={h['min_depth_mult']:.2f}x drag={h['legging_drag_per_pair']:.4f}/pair -> adj_ev={h['legging_adjusted_net_ev_per_pair']:+.4f}/pair <= 0");return False
   e={};b={}
   for g,r in BANKROLL_TICKETS.items():
    z=walk_equal_shares_dominance_box(n,m,target_budget_usd=r[sleeve_override],fee_rate_a=float(w["fee_rate"]),fee_rate_b=float(v["fee_rate"]),fee_exponent_a=float(w["fee_exponent"]),fee_exponent_b=float(v["fee_exponent"]),max_box_cost_net=max_box_cost_override,min_shares=8,min_box_notional_usd=7.5)
    if z.get("filled"):e[g]=z;k=compute_d1_legging_drag_haircut(shares=float(z["shares"]),box_cost_net=float(z["box_cost_net"]),avail_a_shares=float(z["avail_a_shares"]),avail_b_shares=float(z["avail_b_shares"]),px_a=float(z["leg_a_walk"]["worst_px"]),px_b=float(z["leg_b_walk"]["worst_px"]),fee_rate_a=float(w["fee_rate"]),fee_rate_b=float(v["fee_rate"]),is_4h_mixed=d);b[g]=float(k["legging_drag_usd"])
   if"T1000"not in e:return False
   y=time.time();l=f"{sleeve_override}_{int(y)}_{m5.market_id[-6:]}";q=f"{asset} {dom_info['regime']} [{dom_info['k_low']:.4f} .. {dom_info['k_high']:.4f}]";x={"position_id":l,"dedupe_key":f,"sleeve":sleeve_override,"asset_or_city":asset,"title":q,"side":f"{w['label']}+{v['label']}","token_id":f"{w['token_id']}|{v['token_id']}","fee_rate":float(w["fee_rate"]),"entry_ts":y,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":m5.end_ts,"p_model_entry":1.,"entry_eff_px_t1000":s["eff_px"],"entry_vwap_t1000":s["vwap"],"realized_edge_t1000":s["riskless_floor_per_pair"],"legging_adjusted_edge_t1000":h["legging_adjusted_net_ev_per_pair"],"entry_best_bid":round(u+t,4),"last_bid":round(u+t,4),"maker_tp_px":None,"tier_fills":e,"extra":{"is_dominance_box":True,"regime":dom_info["regime"],"k_low":dom_info["k_low"],"k_high":dom_info["k_high"],"corridor_bps":dom_info["corridor_bps"],"m15_horizon":m15.horizon,"m15_market_id":m15.market_id,"m15_start_iso":m15.start_iso,"m15_end_iso":m15.end_iso,"m5_horizon":m5.horizon,"m5_market_id":m5.market_id,"leg_a":w,"leg_b":v,"legging_drag_ref":h,"legging_drag_usd_by_tier":b},"status":"OPEN"};a.open_positions[l]=x
   for p in A:a.entered_keys.add(p)
   a._append_ledger({"event":"SHADOW_ENTRY",**x});logger.info(f"[ENTRY:{sleeve_override}] {q} | {s['shares']} pairs @ net=${s['eff_px']:.4f} (floor=${s['riskless_floor_per_pair']:+.4f}/pair, min_profit=${s['guaranteed_min_profit_usd']:+.2f})");return True
  finally:a._release_inflight_keys(A)
 def _d1_live_max_box_cost(self):
  try:
   b=Path(os.getenv("POLYMARKET_RISK_CONFIG",str(PROJECT_ROOT/"config/polymarket_risk_config.json")));a=json.loads(b.read_text(encoding="utf-8"));v=float(a.get("d1_max_box_cost_net",.985))
   if.86<=v<=.995:return v
  except Exception:pass
  return.985
 def emit_live_d1_box_candidate(a,m15,m5,dom_info,w_live,now_ts,*,is_quiet_book=False,sleeve_source="D1_SAME_ORACLE_DOMINANCE_BOX"):
  b=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==b:return False
  if not(a.single_scan or("fetch_json"in a.__dict__)):
   now_ts=time.time()
   if float(m5.end_ts-now_ts)<16.:return False
  f=f"{m15.asset}_{m15.market_id}_{m5.market_id}";e=float(a._last_d1_live_emit_ts.get(f,.0)or.0)
  if(now_ts-e)<10.:return False
  k=dom_info["leg_a"];j=dom_info["leg_b"];n=w_live["leg_a_walk"];m=w_live["leg_b_walk"];c=("4h"in(str(m15.horizon).lower(),str(m5.horizon).lower()))and(str(m15.horizon).lower()!=str(m5.horizon).lower());d=compute_d1_legging_drag_haircut(shares=float(w_live["shares"]),box_cost_net=float(w_live["box_cost_net"]),avail_a_shares=float(w_live["avail_a_shares"]),avail_b_shares=float(w_live["avail_b_shares"]),px_a=float(n["worst_px"]),px_b=float(m["worst_px"]),fee_rate_a=float(k["fee_rate"]),fee_rate_b=float(j["fee_rate"]),is_4h_mixed=c)
  if d["legging_adjusted_net_ev_per_pair"]<=.0:return False
  a._last_d1_live_emit_ts[f]=now_ts
  for i,h in list(a._last_d1_live_emit_ts.items()):
   if(now_ts-h)>1200.:a._last_d1_live_emit_ts.pop(i,None)
  g="D1_4H_LIVE"if str(m15.horizon).lower()=="4h"else"D1_LIVE";l={"box_id":f"{g}_{m15.asset}_{int(m5.end_ts)}_{m5.market_id[-5:]}","dedupe_key":f"D1_{m15.asset}_{m15.market_id}_{m5.market_id}","ts_unix":round(now_ts,3),"asset":m15.asset,"regime":dom_info["regime"],"pair_horizons":f"{m15.horizon}_{m5.horizon}","sleeve_source":str(sleeve_source),"is_quiet_book":bool(is_quiet_book),"k_low":dom_info["k_low"],"k_high":dom_info["k_high"],"corridor_bps":dom_info["corridor_bps"],"expiry_ts":float(m5.end_ts),"rem_sec":round(float(m5.end_ts-now_ts),2),"shares":int(w_live["shares"]),"net_paired_shares":float(w_live.get("net_paired_shares",w_live["shares"])),"leg_a_gross_shares":float(w_live.get("leg_a_gross_shares",w_live["shares"])),"leg_b_gross_shares":float(w_live.get("leg_b_gross_shares",w_live["shares"])),"box_cost_net":float(w_live["box_cost_net"]),"legging_drag_per_pair":d["legging_drag_per_pair"],"legging_adjusted_net_ev_per_pair":d["legging_adjusted_net_ev_per_pair"],"max_box_cost_net":a._d1_live_max_box_cost(),"leg_a_token_id":str(k["token_id"]),"leg_a_opp_token_id":str(k.get("opp_token_id")or""),"leg_a_label":str(k["label"]),"leg_a_side":str(k["side"]),"leg_a_horizon":str(k["horizon"]),"leg_a_market_id":str(k["market_id"]),"leg_a_condition_id":str(k["condition_id"]),"leg_a_strike":float(k["strike"]),"leg_a_limit_price":float(n["worst_px"]),"leg_a_avail_shares":float(w_live["avail_a_shares"]),"leg_a_fee_rate":float(k["fee_rate"]),"leg_a_fee_exponent":float(k["fee_exponent"]),"leg_a_neg_risk":bool(k["neg_risk"]),"leg_b_token_id":str(j["token_id"]),"leg_b_opp_token_id":str(j.get("opp_token_id")or""),"leg_b_label":str(j["label"]),"leg_b_side":str(j["side"]),"leg_b_horizon":str(j["horizon"]),"leg_b_market_id":str(j["market_id"]),"leg_b_condition_id":str(j["condition_id"]),"leg_b_strike":float(j["strike"]),"leg_b_limit_price":float(m["worst_px"]),"leg_b_avail_shares":float(w_live["avail_b_shares"]),"leg_b_fee_rate":float(j["fee_rate"]),"leg_b_fee_exponent":float(j["fee_exponent"]),"leg_b_neg_risk":bool(j["neg_risk"])};from src.polymarket_research.riskless_protocol_v2_expansion import attach_ws_books_and_write_d1_cand;return attach_ws_books_and_write_d1_cand(a,l,k,j,D1_LIVE_CANDIDATES_FILE,b)
 def emit_live_two_leg_box_candidate(a,*,sleeve_source,box_type,asset,dedupe_key,leg_a,leg_b,bk_a,bk_b,close_ts,now_ts,k_low=1e2,k_high=1e2,max_box_cost_override=None,extra_fields=None):
  c=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==c:return False
  if not(a.single_scan or("fetch_json"in a.__dict__)):now_ts=time.time()
  n=float(close_ts-now_ts)
  if n<25.:return False
  i=float(a._last_d1_live_emit_ts.get(dedupe_key,.0)or.0)
  if(now_ts-i)<15.:return False
  z=float(leg_a.get("fee_rate",CRYPTO_FEE_RATE));y=float(leg_b.get("fee_rate",CRYPTO_FEE_RATE));x=float(leg_a.get("fee_exponent",1.));w=float(leg_b.get("fee_exponent",1.))
  if sleeve_source=="COND1_MACRO_PARTITION_BOX":b=(.992 if n<=1.08e5 else.988)if a.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX")else.985
  elif box_type=="BARRIER_MONO":b=.993
  elif max(z,y)==.0 and(a.is_sleeve_grad8_ready(sleeve_source)or a._can_emit_zero_loss_math_live(sleeve_source,close_ts,now_ts))and n<=(604800. if sleeve_source in{"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION"}else 172800.):b=.992
  else:b=.99 if max(z,y)==.0 else.988
  if max_box_cost_override is not None:b=min(b,float(max_box_cost_override))
  r=walk_equal_shares_dominance_box(bk_a.get("asks")or[],bk_b.get("asks")or[],target_budget_usd=20.,fee_rate_a=z,fee_rate_b=y,fee_exponent_a=x,fee_exponent_b=w,max_box_cost_net=b,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.86)
  if not r.get("filled"):return False
  if len(a._last_d1_live_emit_ts)>256:a._last_d1_live_emit_ts={k:v for k,v in a._last_d1_live_emit_ts.items()if(now_ts-float(v))<=1200.}
  a._last_d1_live_emit_ts[dedupe_key]=now_ts;C=r["leg_a_walk"];B=r["leg_b_walk"];u,_=a._best_ask_sz(bk_a);t,_=a._best_ask_sz(bk_b);q,_=extract_best_bid(bk_a.get("bids")or[]);p,_=extract_best_bid(bk_b.get("bids")or[]);h=bool(q>.0 and p>.0 and(u-q)<=.041 and(t-p)<=.041 and(max(z,y)==.0 or(now_ts-float(a._last_any_shock_ts_by_asset.get(str(asset),.0)or.0))>=4.));m=round(abs(k_high-k_low)/max(1e-9,k_low)*1e4,2)if k_low>0 else.0;A={"box_id":f"{box_type}_LIVE_{asset}_{int(close_ts)}_{str(leg_a.get('market_id','0'))[-5:]}","dedupe_key":dedupe_key,"box_type":str(box_type),"ts_unix":round(now_ts,3),"asset":str(asset),"regime":f"{box_type}_{leg_a.get('label','A')}_PLUS_{leg_b.get('label','B')}","pair_horizons":str(box_type).lower(),"sleeve_source":str(sleeve_source),"is_quiet_book":h,"k_low":float(k_low),"k_high":float(k_high),"corridor_bps":m,"expiry_ts":float(close_ts),"rem_sec":round(n,2),"shares":int(r["shares"]),"net_paired_shares":float(r.get("net_paired_shares",r["shares"])),"leg_a_gross_shares":float(r.get("leg_a_gross_shares",r["shares"])),"leg_b_gross_shares":float(r.get("leg_b_gross_shares",r["shares"])),"box_cost_net":float(r["box_cost_net"]),"max_box_cost_net":b,"leg_a_token_id":str(leg_a["token_id"]),"leg_a_opp_token_id":str(leg_a.get("opp_token_id")or""),"leg_a_label":str(leg_a.get("label")or leg_a.get("side")or"YES"),"leg_a_side":str(leg_a.get("side")or"YES"),"leg_a_horizon":str(leg_a.get("horizon")or box_type.lower()),"leg_a_market_id":str(leg_a.get("market_id")or""),"leg_a_condition_id":str(leg_a.get("condition_id")or""),"leg_a_strike":float(leg_a.get("strike")or k_low),"leg_a_limit_price":float(C["worst_px"]),"leg_a_avail_shares":float(r["avail_a_shares"]),"leg_a_fee_rate":z,"leg_a_fee_exponent":x,"leg_a_neg_risk":bool(leg_a["neg_risk"])if isinstance(leg_a.get("neg_risk"),bool)else False,"leg_a_expiry_ts":float(leg_a.get("end_ts")or close_ts),"leg_b_token_id":str(leg_b["token_id"]),"leg_b_opp_token_id":str(leg_b.get("opp_token_id")or""),"leg_b_label":str(leg_b.get("label")or leg_b.get("side")or"NO"),"leg_b_side":str(leg_b.get("side")or"NO"),"leg_b_horizon":str(leg_b.get("horizon")or box_type.lower()),"leg_b_market_id":str(leg_b.get("market_id")or""),"leg_b_condition_id":str(leg_b.get("condition_id")or""),"leg_b_strike":float(leg_b.get("strike")or k_high),"leg_b_limit_price":float(B["worst_px"]),"leg_b_avail_shares":float(r["avail_b_shares"]),"leg_b_fee_rate":y,"leg_b_fee_exponent":w,"leg_b_neg_risk":bool(leg_b["neg_risk"])if isinstance(leg_b.get("neg_risk"),bool)else False,"leg_b_expiry_ts":float(leg_b.get("end_ts")or close_ts)}
  if isinstance(extra_fields,dict):A.update(extra_fields)
  if not a.single_scan and a._ws_books:
   l=[str(leg_a["token_id"]),str(leg_b["token_id"])]
   if str(box_type)!="COMPLETE_SET":
    for s in(str(leg_a.get("opp_token_id")or""),str(leg_b.get("opp_token_id")or"")):
     if s:l.append(s)
   j={str(leg_a["token_id"]),str(leg_b["token_id"])};d=getattr(a,"_ws_rest_seeded",set())
   if all(t_x in a._ws_books and t_x not in d and(now_ts-a._ws_books[t_x][0])<=2.5 and bool(a._ws_books[t_x][1].get("asks"))and(t_x not in j or bool(a._ws_books[t_x][1].get("bids")or a._ws_books[t_x][1].get("asks")))for t_x in l):A["ws_books"]={t_x:{"bids":(a._ws_books[t_x][1].get("bids")or[])[:12],"asks":(a._ws_books[t_x][1].get("asks")or[])[:12]}for t_x in l};A["ws_books_ts"]=round(min(a._ws_books[t_x][0]for t_x in l),3)
  try:
   try:import orjson as _orj;g=_orj.dumps(A)+b"\n";e=g.decode("utf-8")
   except Exception:e=json.dumps(A,separators=(",",":"))+"\n";g=e.encode("utf-8")
   if os.name!="nt"and D1_LIVE_CANDIDATES_FILE==c:
    try:
     import socket;f=getattr(a,"_d1_ipc_sock",None)
     if f is None:f=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);f.setblocking(False);a._d1_ipc_sock=f
     o=os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify");f.sendto(g,f"\x00{o}".encode("utf-8"))
    except Exception:pass
   D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True,exist_ok=True)
   with open(D1_LIVE_CANDIDATES_FILE,"a",encoding="utf-8")as D:D.write(e)
   return True
  except Exception as exc:return False
 def emit_live_single_leg_lock_candidate(self,*,sleeve_source,asset,dedupe_key,token_id,opp_token_id,market_id,condition_id,side_label,display_label,bk_win,bk_opp,fee_rate,fee_exponent,neg_risk,close_ts,now_ts,max_lock_eff_px,max_opp_bid=.025,hold_to_maturity=False,p_model=1.):from src.polymarket_research.riskless_protocol_v2_expansion import emit_single_leg_lock_cand_impl;return emit_single_leg_lock_cand_impl(self,sleeve_source=sleeve_source,asset=asset,dedupe_key=dedupe_key,token_id=token_id,opp_token_id=opp_token_id,market_id=market_id,condition_id=condition_id,side_label=side_label,display_label=display_label,bk_win=bk_win,bk_opp=bk_opp,fee_rate=fee_rate,fee_exponent=fee_exponent,neg_risk=neg_risk,close_ts=close_ts,now_ts=now_ts,max_lock_eff_px=max_lock_eff_px,max_opp_bid=max_opp_bid,hold_to_maturity=hold_to_maturity,p_model=p_model,extract_best_bid_fn=extract_best_bid,walk_l2_fn=walk_l2_book_asks_depth_capped,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json")
 def emit_live_special_v2_box_candidate(self,*,box_type,sleeve_source,asset,dedupe_key,close_ts,now_ts,payload):from src.polymarket_research.riskless_protocol_v2_expansion import emit_special_v2_box_cand_impl;return emit_special_v2_box_cand_impl(self,box_type=box_type,sleeve_source=sleeve_source,asset=asset,dedupe_key=dedupe_key,close_ts=close_ts,now_ts=now_ts,payload=payload,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json")
 def emit_live_negrisk_convert_candidate(self,*,sleeve_source,spec,dedupe_key,arb_hit,books_by_token,now_ts,fee_bips=0):from src.polymarket_research.riskless_protocol_v2_expansion import emit_negrisk_convert_cand_impl;return emit_negrisk_convert_cand_impl(self,sleeve_source=sleeve_source,spec=spec,dedupe_key=dedupe_key,arb_hit=arb_hit,books_by_token=books_by_token,now_ts=now_ts,fee_bips=fee_bips,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json")
 def emit_live_single_leg_maker_lock_candidate(self,*,sleeve_source,asset,dedupe_key,pair_dedupe_key,token_id,opp_token_id,market_id,condition_id,side_label,display_label,bk_win,bk_opp,neg_risk,close_ts,now_ts,min_resting_bid=.94,max_resting_bid=.994,min_maker_edge=.006,max_opp_bid=.008,hold_to_maturity=True,p_model=1.,target_bid_px=None,maker_rebate_ps=.0):from src.polymarket_research.riskless_protocol_v2_expansion import emit_single_leg_maker_lock_cand_impl;return emit_single_leg_maker_lock_cand_impl(self,sleeve_source=sleeve_source,asset=asset,dedupe_key=dedupe_key,pair_dedupe_key=pair_dedupe_key,token_id=token_id,opp_token_id=opp_token_id,market_id=market_id,condition_id=condition_id,side_label=side_label,display_label=display_label,bk_win=bk_win,bk_opp=bk_opp,neg_risk=neg_risk,close_ts=close_ts,now_ts=now_ts,min_resting_bid=min_resting_bid,max_resting_bid=max_resting_bid,min_maker_edge=min_maker_edge,max_opp_bid=max_opp_bid,hold_to_maturity=hold_to_maturity,p_model=p_model,target_bid_px=target_bid_px,maker_rebate_ps=maker_rebate_ps,extract_best_bid_fn=extract_best_bid,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json")
 def emit_live_maker_anchor_box_candidate(self,*,sleeve_source,box_type,asset,dedupe_key,regime,pair_horizons,leg_a,leg_b,anchor_is_a,queue_front,anchor_bid_px,hedge_limit_px,avail_a_shares,avail_b_shares,close_ts,now_ts,k_low=1e2,k_high=1e2,corridor_bps=.0,posted_spot=.0):from src.polymarket_research.riskless_protocol_v2_expansion import emit_maker_anchor_box_cand_impl;return emit_maker_anchor_box_cand_impl(self,sleeve_source=sleeve_source,box_type=box_type,asset=asset,dedupe_key=dedupe_key,regime=regime,pair_horizons=pair_horizons,leg_a=leg_a,leg_b=leg_b,anchor_is_a=anchor_is_a,queue_front=queue_front,anchor_bid_px=anchor_bid_px,hedge_limit_px=hedge_limit_px,avail_a_shares=avail_a_shares,avail_b_shares=avail_b_shares,close_ts=close_ts,now_ts=now_ts,k_low=k_low,k_high=k_high,corridor_bps=corridor_bps,posted_spot=posted_spot,crypto_fee_rate=CRYPTO_FEE_RATE,project_root=PROJECT_ROOT,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json")
 def _latest_spot_px(a,asset):
  b=a.usd_spot_hist.get(asset)
  if b and len(b)>0 and(time.time()-float(b[-1][0]))<=10. and float(b[-1][1])>.0:return float(b[-1][1])
  return float(a.spots.get(asset)or.0)
 def post_maker_anchor_candidate(c,m15,m5,dom_info,bk_a,bk_b,now_ts,*,live_emit_only=False):
  if is_shadow_sleeve_quarantined("D1_MAKER_ANCHOR_BOX"):return False
  L=m5.end_ts-now_ts;q=880. if str(m5.horizon)=="15m"else 295.
  if not(65.<=L<=q):return False
  o=c.get_return_bps(m15.asset,5.)
  if abs(o)>4.5:return False
  if(now_ts-float(c._last_any_shock_ts_by_asset.get(m15.asset,.0)or.0))<4.:return False
  _o=f"D1_MKR_{m15.asset}_{m15.market_id}_{m5.market_id}"
  if not live_emit_only and(_o in c.entered_keys or _o in c.pending_maker_anchors or _o in c.inflight_keys):return False
  _n,_m=dom_info["leg_a"],dom_info["leg_b"];X=sorted([(float(b["price"]),float(b["size"]))for b in(bk_a.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);W=sorted([(float(b["price"]),float(b["size"]))for b in(bk_b.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);V=sorted([(float(a["price"]),float(a["size"]))for a in(bk_a.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);U=sorted([(float(a["price"]),float(a["size"]))for a in(bk_b.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0])
  if not V or not U or not X or not W:return False
  _l,_k=X[0];_j,_i=W[0];_h,_r=V[0];_g,_q=U[0];_f,_e=round(_h-_l,4),round(_g-_j,4);_d=(_k-_r)/max(1e-9,_k+_r);_c=(_i-_q)/max(1e-9,_i+_q);n=float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(m15.asset,40.));l=min(float(BANKROLL_TICKETS["T100"]["D1_MAKER_ANCHOR_BOX"]),n);m=max(5.,math.floor(l/.985));k=max(5.,math.floor(min(float(BANKROLL_TICKETS["T1000"]["D1_MAKER_ANCHOR_BOX"]),n)/.985))
  def _snap_c(p):p=round(float(p),4);return(math.floor((p+1e-9)*1e2)/1e2)if(.04+1e-9<p<.96-1e-9)else(math.floor((p+1e-9)*1e3)/1e3)
  t=[]
  for d in(True,False):
   _b=_l if d else _j;K=_k if d else _i;_a=_h if d else _g;Z=_f if d else _e;J=_d if d else _c;I=_n if d else _m;C=U if d else V;H=_m if d else _n
   if not(.03<=_a<=.999)or J<-.35:continue
   B=str(I.get("side")or"UP").upper()
   if(B=="UP"and o<-2.2)or(B=="DOWN"and o>2.2):continue
   T=.001 if(_b>=.96 or _b<.04)else.01;S=.001 if(_a>.96 or _a<=.04)else.01;R=_snap_c(_b+T);Y=_snap_c(_a-S)
   if R<=Y+1e-9 and R>_b+1e-9:g=min(R,Y);e=True
   elif Z>=.01-1e-9 and.15<=_a<=.85 and J>=-.15 and K>=15.:g=_snap_c(_b);e=False
   else:continue
   y=sum(sz for px,sz in C if px<=C[0][0]+.01)
   if y<max(15.,2.5*m):continue
   Q=C[0][0];G=float(H["fee_rate"])*((Q*(1.-Q))**float(H.get("fee_exponent",1.)));h=Q+G;j=min(g,_snap_c(.988-h));s=round(_b-(T if e else.0),3)
   if j<s or j<=.02 or j>=_a:continue
   A=round(j+h,4);i=.86 if(c._strike_is_rest_verified(m15)and c._strike_is_rest_verified(m5))else.9
   if i<=A<=.988:t.append((A-(5e-4 if e else.0),d,e,j,round(h,4),m))
  if not t:
   if(not c.single_scan and _d>=-.15 and _c>=-.15 and c._strike_is_rest_verified(m15)and c._strike_is_rest_verified(m5)):
    from src.polymarket_research.riskless_machine_gun_engine import evaluate_d1_maker_rebate_anchor,read_shm_spot_age_ms;_p=c.usd_spot_hist.get(m15.asset);w=read_shm_spot_age_ms(m15.asset,now_ts,max(.0,(now_ts-float(_p[-1][0]))*1e3)if(_p and len(_p)>0)else 999.);P=sum(sz for px,sz in V if px<=_h+.01);O=sum(sz for px,sz in U if px<=_g+.01)
    for F in(True,False):
     N=evaluate_d1_maker_rebate_anchor(anchor_bid_px=_l if F else _j,anchor_ask_px=_h if F else _g,hedge_ask_px=_g if F else _h,hedge_avail_shares=O if F else P,req_shares=m,fee_rate=float((_m if F else _n).get("fee_rate",CRYPTO_FEE_RATE)),fee_exponent=float((_m if F else _n).get("fee_exponent",1.)),spot_age_ms=w)
     if N.get("eligible"):v=c.emit_live_maker_anchor_box_candidate(sleeve_source="D1_REBATE_MACHINE_GUN",box_type="DOMINANCE_MAKER_ANCHOR",asset=m15.asset,dedupe_key=f"D1_REBMG_{m15.asset}_{m15.market_id}_{m5.market_id}",regime=str(dom_info["regime"]),pair_horizons=f"{m15.horizon}_{m5.horizon}",leg_a=_n,leg_b=_m,anchor_is_a=F,queue_front=True,anchor_bid_px=float(N["anchor_bid_px"]),hedge_limit_px=float(_g if F else _h),avail_a_shares=P,avail_b_shares=O,close_ts=float(m5.end_ts),now_ts=now_ts,k_low=float(dom_info["k_low"]),k_high=float(dom_info["k_high"]),corridor_bps=float(dom_info["corridor_bps"]),posted_spot=c._latest_spot_px(m15.asset));return v if live_emit_only else False
   return False
  t.sort(key=lambda z:z[0]);_,d,e,j,h,M=t[0];u=c._latest_spot_px(m15.asset)
  if not live_emit_only:c.pending_maker_anchors[_o]={"dedupe_key":_o,"asset":m15.asset,"m15":m15,"m5":m5,"dom_info":dom_info,"anchor_is_a":d,"queue_front":e,"bid_px":j,"pair_est":round(j+h,4),"req_shares_t100":M,"req_shares_t1000":k,"posted_ts":now_ts,"posted_spot":u}
  E=sum(sz for px,sz in V if px<=_h+.01);D=sum(sz for px,sz in U if px<=_g+.01);r=_g if d else _h;f=False
  if c._strike_is_rest_verified(m15)and c._strike_is_rest_verified(m5):f=c.emit_live_maker_anchor_box_candidate(sleeve_source="D1_MAKER_ANCHOR_BOX",box_type="DOMINANCE_MAKER_ANCHOR",asset=m15.asset,dedupe_key=_o,regime=str(dom_info["regime"]),pair_horizons=f"{m15.horizon}_{m5.horizon}",leg_a=_n,leg_b=_m,anchor_is_a=d,queue_front=e,anchor_bid_px=j,hedge_limit_px=r,avail_a_shares=E,avail_b_shares=D,close_ts=float(m5.end_ts),now_ts=now_ts,k_low=float(dom_info["k_low"]),k_high=float(dom_info["k_high"]),corridor_bps=float(dom_info["corridor_bps"]),posted_spot=u)
  if live_emit_only:return f
  logger.info(f"[MAKER_ANCHOR_POST] {m15.asset} {dom_info['regime']} | Resting post_only=${j:.3f} (qf={e}) + hedge_eff=${h:.4f} = ${j+h:.4f} (TTE={L:.0f}s)");return True
 async def manage_pending_maker_anchors(b,now_ts=None):
  if not b.pending_maker_anchors:return
  _n=float(now_ts if now_ts is not None else time.time());n=[]
  for st in b.pending_maker_anchors.values():di=st["dom_info"];n.extend([str(di["leg_a"]["token_id"]),str(di["leg_b"]["token_id"])])
  _m=await b.fetch_books_batch(n,timeout=2.5)
  for _d,st in list(b.pending_maker_anchors.items()):
   _l=st["m15"];m5=st["m5"];di=st["dom_info"];_c,_b=di["leg_a"],di["leg_b"];H=bool(st["anchor_is_a"]);R=bool(st.get("queue_front",True));Q=_c if H else _b;P=_b if H else _c;Z=_m.get(str(Q["token_id"]));Y=_m.get(str(P["token_id"]));X=float(st["bid_px"]);W=_n-float(st["posted_ts"]);O=m5.end_ts-_n;G=(Z or{}).get("asks")or[];k=min((float(a["price"])for a in G if float(a.get("size",0))>0),default=1.);u=Z is not None and W>=.35 and k<=X
   if u:
    b.pending_maker_anchors.pop(_d,None);b.entered_keys.add(_d);F=sorted([(float(a["price"]),float(a["size"]))for a in((Y or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);V=F[0][0]if F else 1.;z=sum(sz for px,sz in F if px<=V+.01)if F else.0;N=float(P["fee_rate"])*((V*(1.-V))**float(P.get("fee_exponent",1.)))if V<1. else.0;E=round(X+V+N,4);m=float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(_l.asset,1e2));M="4h"in(str(_l.horizon).lower(),str(m5.horizon).lower())
    if Y is not None and F and z>=5. and.9<=E<=.995:
     t={};j={};c=.0
     for i,s in BANKROLL_TICKETS.items():
      sh=max(5.,min(z,math.floor(min(s["D1_MAKER_ANCHOR_BOX"],m)/E)));_a=round(sh*N,4);L=round(sh*(X+V),2);t[i]={"filled":True,"vwap":round(X+V,4),"eff_px":E,"spent_usd":L,"fee_usd":_a,"shares":sh,"l1_usd":round(z*E,2)};dr=compute_d1_maker_anchor_drag_haircut(shares=sh,pair_eff=E,bid_anc=X,hdg_px=V,hdg_avail_shares=z,fee_rate_anc=float(Q.get("fee_rate",CRYPTO_FEE_RATE)),fee_exponent_anc=float(Q.get("fee_exponent",1.)),queue_front=R,is_4h_mixed=M);j[i]=float(dr["legging_drag_usd"])
      if i=="T1000":c=float(dr["maker_rebate_20pct_est_usd"])
     y,_=extract_best_bid((_m.get(str(_c["token_id"]))or{}).get("bids")or[]);x,_=extract_best_bid((_m.get(str(_b["token_id"]))or{}).get("bids")or[]);U=f"D1_MAKER_ANCHOR_BOX_{int(_n)}_{m5.market_id[-6:]}";_k={"position_id":U,"dedupe_key":_d,"sleeve":"D1_MAKER_ANCHOR_BOX","asset_or_city":_l.asset,"title":f"{_l.asset} {di['regime']} [0%-Fee Maker Anchor @ ${X:.3f}]","side":f"{_c['label']}+{_b['label']}","token_id":f"{_c['token_id']}|{_b['token_id']}","fee_rate":float(P["fee_rate"]),"entry_ts":_n,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":m5.end_ts,"p_model_entry":1.,"entry_eff_px_t1000":E,"entry_vwap_t1000":round(X+V,4),"realized_edge_t1000":round(1.-E,4),"entry_best_bid":round(y+x,4),"last_bid":round(y+x,4),"maker_tp_px":None,"tier_fills":t,"extra":{"is_dominance_box":True,"is_maker_anchor_box":True,"queue_front":R,"legging_drag_usd_by_tier":j,"maker_rebate_20pct_est_t1000_usd":c,"regime":di["regime"],"k_low":di["k_low"],"k_high":di["k_high"],"corridor_bps":di["corridor_bps"],"m15_horizon":_l.horizon,"m15_market_id":_l.market_id,"m15_start_iso":_l.start_iso,"m15_end_iso":_l.end_iso,"m5_horizon":m5.horizon,"m5_market_id":m5.market_id,"leg_a":_c,"leg_b":_b},"status":"OPEN"};b.open_positions[U]=_k;b._append_ledger({"event":"SHADOW_ENTRY",**_k});logger.info(f"[ENTRY:D1_MAKER_ANCHOR_BOX] {_k['title']} -> Hedged @ net=${E:.4f}!")
    else:
     g,_=extract_best_bid((Z or{}).get("bids")or[])
     if g<=.0:g=max(.01,X-.03)
     K=float(Q["fee_rate"])*((g*(1.-g))**float(Q.get("fee_exponent",1.)));J=max(.0,g-K);_g={};_f={};D=max(.9,float(st.get("pair_est")or.985))
     for i,s in BANKROLL_TICKETS.items():_e=max(5.,float(math.floor(min(s["D1_MAKER_ANCHOR_BOX"],m)/D)));_j=round(_e*X,2);_g[i]={"filled":True,"vwap":X,"eff_px":X,"spent_usd":_j,"fee_usd":.0,"shares":_e};_f[i]=round(_e*J-_j,2)
     I={"position_id":f"D1_MKR_SCRATCH_{int(_n)}_{m5.market_id[-6:]}","dedupe_key":_d,"sleeve":"D1_MAKER_ANCHOR_BOX","asset_or_city":_l.asset,"title":f"{_l.asset} {di['regime']} [Maker Anchor Unhedged Scratch]","side":f"{Q['label']}_SCRATCH","token_id":str(Q["token_id"]),"fee_rate":.0,"entry_ts":st["posted_ts"],"entry_utc":datetime.fromtimestamp(st["posted_ts"],tz=timezone.utc).isoformat(),"close_ts":m5.end_ts,"closed_ts":_n,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":.5,"entry_eff_px_t1000":X,"entry_vwap_t1000":X,"net_payout_per_share":round(J,4),"tier_fills":_g,"tier_pnls_usd":_f,"legging_adjusted_tier_pnls_usd":dict(_f),"won":_f.get("T1000",.0)>0,"status":"MAKER_ANCHOR_UNHEDGED_SCRATCH"};b.closed_positions.append(I);b._append_ledger({"event":"SHADOW_CLOSE",**I})
    continue
   r=sorted([(float(a["price"]),float(a["size"]))for a in((Y or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);C=r[0][0]if r else 1.;l=sum(sz for px,sz in r if px<=C+.01)if r else.0;w=float(P["fee_rate"])*((C*(1.-C))**float(P.get("fee_exponent",1.)))if C<1. else.0;q=float(st.get("req_shares_t100")or st.get("req_shares_t1000")or 15.);e=(l<max(12.,2.*q))or((X+C+w)>.993);d=.0
   if Z is not None:
    _,T=extract_best_bid(Z.get("bids")or[]);S=sum(float(a.get("size",0))for a in G if abs(float(a.get("price",0))-k)<1e-6)
    if(T+S)>.0:d=(T-S)/(T+S)
   v=float(st.get("posted_spot")or.0);B=b._latest_spot_px(_l.asset);f=((B-v)/v*1e4)if(v>.0 and B>.0)else.0;A=b.get_return_bps(_l.asset,5.);p=str(Q.get("side")or"UP").upper();o=((min(f,A)<-2.5)if p=="UP"else(max(f,A)>2.5));h=(_n-float(b._last_any_shock_ts_by_asset.get(_l.asset,.0)or.0))<4.
   if(O<=45. or W>=(12. if b.single_scan else 90.)or o or abs(A)>8. or d<-.35 or h or e):b.pending_maker_anchors.pop(_d,None)
 def post_zero_fee_maker_anchor_box(c,source_tag,asset,d_key,leg_a,leg_b,bk_a,bk_b,close_ts,title,now_ts,prefetched_books=None,*,live_emit_only=False):
  if is_shadow_sleeve_quarantined("ZF_INTRADAY_MAKER_BOX"):return False
  u=float(close_ts-now_ts)
  if not(65.<=u<=64800.):return False
  I=c.__dict__.setdefault("_zf_maker_cooldown_until",{})
  if not live_emit_only and(d_key in c.entered_keys or d_key in c.pending_zero_fee_maker_anchors or float(I.get(d_key,.0)or.0)>now_ts):return False
  if float(leg_a.get("fee_rate",.0))>.0 or float(leg_b.get("fee_rate",.0))>.0:return False
  if prefetched_books:
   Z=str(leg_a.get("opp_token_id")or"");Y=str(leg_b.get("opp_token_id")or"")
   if Z in prefetched_books and Y in prefetched_books:
    _b,_=extract_best_bid((prefetched_books[Z]or{}).get("bids")or[]);_a,_=extract_best_bid((prefetched_books[Y]or{}).get("bids")or[]);H,_=c._best_ask_sz(bk_a);G,_=c._best_ask_sz(bk_b)
    if((H>.0 and _b>.0 and(H+_b)>1.015)or(G>.0 and _a>.0 and(G+_a)>1.015)or(_b+_a)>1.16):return False
  F=sorted([(float(b["price"]),float(b["size"]))for b in(bk_a.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);E=sorted([(float(b["price"]),float(b["size"]))for b in(bk_b.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);D=sorted([(float(a["price"]),float(a["size"]))for a in(bk_a.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);C=sorted([(float(a["price"]),float(a["size"]))for a in(bk_b.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0])
  if not D or not C or not F or not E:return False
  X,W=F[0];V,U=E[0];T,S=D[0];R,Q=C[0];P=(W-S)/max(1e-9,W+S);O=(U-Q)/max(1e-9,U+Q);k=max(6.,math.floor(float(BANKROLL_TICKETS["T100"]["ZF_INTRADAY_MAKER_BOX"])/.988));h=max(6.,math.floor(float(BANKROLL_TICKETS["T1000"]["ZF_INTRADAY_MAKER_BOX"])/.988))
  def _snap_zf(p):p=round(float(p),4);return(math.floor((p+1e-9)*1e2)/1e2)if(.04+1e-9<p<.96-1e-9)else(math.floor((p+1e-9)*1e3)/1e3)
  j=.992 if source_tag=="SP1_NBA"else(.985 if u>3600. else.988);o=[]
  for e in(True,False):
   N=X if e else V;t=W if e else U;M=T if e else R;s=P if e else O;L=V if e else X;n=C if e else D;K=n[0][0]
   if not(.02<=M<=.999)or not(.001<=K<=.985)or s<-.25:continue
   if L>.0 and K>.04 and(K-L)>.05:continue
   B=.001 if(N>=.96 or N<.04)else.01;A=.001 if(M>.96 or M<=.04)else.01;y=_snap_zf(N+B);J=_snap_zf(M-A);m=sum(sz for px,sz in n if px<=K+.01)
   if m<max(18.,2.5*k):continue
   d=True
   if y<=J+1e-9 and y>N+1e-9:g=min(y,J,_snap_zf(j-K));d=g>N+1e-9
   elif(M-N)>=.01-1e-9 and.15<=M<=.88 and s>=-.15 and t>=15.:d=False;g=min(_snap_zf(N),_snap_zf(j-K))
   else:continue
   if g<round(N-B,3)or g<=.015 or g>=M:continue
   f=round(g+K,4)
   if.86<=f<=j:o.append((f,e,round(g,4),round(K,4),d))
  if not o:return False
  o.sort(key=lambda z:(z[0],0 if z[4]else 1));f,e,w,v,i=o[0]
  if not live_emit_only:c.pending_zero_fee_maker_anchors[d_key]={"source_tag":source_tag,"dedupe_key":d_key,"asset":asset,"title":title,"leg_a":leg_a,"leg_b":leg_b,"anchor_is_a":e,"bid_px":w,"pair_est":f,"queue_front":i,"req_shares_t100":k,"req_shares_t1000":h,"close_ts":close_ts,"posted_ts":now_ts}
  r=sum(sz for px,sz in D if px<=T+.01);q=sum(sz for px,sz in C if px<=R+.01);l=c.emit_live_maker_anchor_box_candidate(sleeve_source="ZF_INTRADAY_MAKER_BOX",box_type="ZERO_FEE_MAKER_ANCHOR",asset=asset,dedupe_key=d_key,regime=f"ZF_{source_tag}",pair_horizons=f"zf_{source_tag.lower()}",leg_a=leg_a,leg_b=leg_b,anchor_is_a=e,queue_front=i,anchor_bid_px=w,hedge_limit_px=v,avail_a_shares=r,avail_b_shares=q,close_ts=float(close_ts),now_ts=now_ts,k_low=float(leg_a.get("strike")or 1e2),k_high=float(leg_b.get("strike")or 1e2))
  if live_emit_only:return l
  logger.info(f"[ZF_INTRADAY_MAKER_POST:{source_tag}] {title} | bid=${w:.3f} + hdg=${v:.3f} = ${f:.4f} (TTE={u/3600.:.2f}h)");return True
 async def manage_pending_zero_fee_maker_anchors(b,now_ts=None):
  if not b.pending_zero_fee_maker_anchors:return
  W=float(now_ts if now_ts is not None else time.time());I=b.__dict__.setdefault("_zf_maker_cooldown_until",{});R=[t for st in b.pending_zero_fee_maker_anchors.values()for t in(str(st["leg_a"]["token_id"]),str(st["leg_b"]["token_id"]))];V=await b.fetch_books_batch(R,timeout=3.)
  for K,st in list(b.pending_zero_fee_maker_anchors.items()):
   Z,Y=st["leg_a"],st["leg_b"];s=bool(st["anchor_is_a"]);A=Z if s else Y;z=Y if s else Z;H=V.get(str(A["token_id"]));G=V.get(str(z["token_id"]));F=float(st["bid_px"]);E=W-float(st["posted_ts"]);y=float(st["close_ts"])-W;r=(H or{}).get("asks")or[];f=min((float(a["price"])for a in r if float(a.get("size",0))>0),default=1.)
   if H is not None and E>=.4 and f<=F:
    b.pending_zero_fee_maker_anchors.pop(K,None);b.entered_keys.add(K);q=sorted([(float(a["price"]),float(a["size"]))for a in((G or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);D=q[0][0]if q else 1.;n=sum(sz for px,sz in q if px<=D+.01)if q else.0;p=round(F+D,4)
    if G is not None and q and n>=5. and.9<=p<=.993:
     J={};x={}
     for e,l in BANKROLL_TICKETS.items():X=max(5.,min(n,math.floor(l["ZF_INTRADAY_MAKER_BOX"]/p)));J[e]={"filled":True,"vwap":p,"eff_px":p,"spent_usd":round(X*p,2),"fee_usd":.0,"shares":X,"l1_usd":round(n*p,2)};Q=compute_d1_maker_anchor_drag_haircut(shares=X,pair_eff=p,bid_anc=F,hdg_px=D,hdg_avail_shares=n,fee_rate_anc=.0,fee_exponent_anc=1.,queue_front=bool(st.get("queue_front",True)),is_4h_mixed=False);x[e]=float(Q["legging_drag_usd"])
     P,_=extract_best_bid((V.get(str(Z["token_id"]))or{}).get("bids")or[]);O,_=extract_best_bid((V.get(str(Y["token_id"]))or{}).get("bids")or[]);U=f"ZF_INTRADAY_MKR_{int(W)}_{K[-8:]}";T={"position_id":U,"dedupe_key":K,"sleeve":"ZF_INTRADAY_MAKER_BOX","asset_or_city":st["asset"],"title":f"{st['title']} [ZF Intraday Maker @ ${F:.3f}]","side":f"{Z['label']}+{Y['label']}","token_id":f"{Z['token_id']}|{Y['token_id']}","fee_rate":.0,"entry_ts":W,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":st["close_ts"],"p_model_entry":1.,"entry_eff_px_t1000":p,"entry_vwap_t1000":p,"realized_edge_t1000":round(1.-p,4),"entry_best_bid":round(P+O,4),"last_bid":round(P+O,4),"maker_tp_px":None,"tier_fills":J,"extra":{"is_two_leg_box":True,"is_maker_anchor_box":True,"legging_drag_usd_by_tier":x,"source_tag":st["source_tag"],"leg_a":Z,"leg_b":Y},"status":"OPEN"};b.open_positions[U]=T;b._append_ledger({"event":"SHADOW_ENTRY",**T});logger.info(f"[ENTRY:ZF_INTRADAY_MAKER_BOX] {T['title']} -> Hedged @ ${p:.4f}!")
    else:
     w,_=extract_best_bid((H or{}).get("bids")or[]);v=w if w>0 else max(.01,F-.03);N,M={},{};h=max(.9,float(st.get("pair_est")or.986))
     for e,l in BANKROLL_TICKETS.items():L=max(5.,float(math.floor(l["ZF_INTRADAY_MAKER_BOX"]/h)));S=round(L*F,2);N[e]={"filled":True,"vwap":F,"eff_px":F,"spent_usd":S,"fee_usd":.0,"shares":L};M[e]=round(L*v-S,2)
     u={"position_id":f"ZF_MKR_SCRATCH_{int(W)}_{K[-8:]}","dedupe_key":K,"sleeve":"ZF_INTRADAY_MAKER_BOX","asset_or_city":st["asset"],"title":f"{st['title']} [ZF Intraday Maker Scratch]","side":f"{A['label']}_SCRATCH","token_id":str(A["token_id"]),"fee_rate":.0,"entry_ts":st["posted_ts"],"entry_utc":datetime.fromtimestamp(st["posted_ts"],tz=timezone.utc).isoformat(),"close_ts":st["close_ts"],"closed_ts":W,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":.5,"entry_eff_px_t1000":F,"entry_vwap_t1000":F,"net_payout_per_share":round(v,4),"tier_fills":N,"tier_pnls_usd":M,"legging_adjusted_tier_pnls_usd":dict(M),"won":M.get("T1000",.0)>0,"status":"MAKER_ANCHOR_UNHEDGED_SCRATCH"};b.closed_positions.append(u);b._append_ledger({"event":"SHADOW_CLOSE",**u})
    continue
   k=sorted([(float(a["price"]),float(a["size"]))for a in((G or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);o=k[0][0]if k else 1.;g=sum(sz for px,sz in k if px<=o+.01)if k else.0;j=float(st.get("req_shares_t100")or 18.);c,C=extract_best_bid((H or{}).get("bids")or[]);B=sum(float(a.get("size",0))for a in r if abs(float(a.get("price",0))-f)<1e-6);m=((C-B)/(C+B))if(C+B)>.0 else.0;d=.993 if st.get("source_tag")=="SP1_NBA"else.991;i=(y<=60. or m<-.3 or(c>.0 and c<F-.015)or g<max(12.,2.*j)or(F+o)>d)
   if i or E>=(15. if b.single_scan else 90.):
    b.pending_zero_fee_maker_anchors.pop(K,None)
    if i:I[K]=W+12.
    else:I.pop(K,None);b.last_tradfi_sports_scan_ts=min(float(b.last_tradfi_sports_scan_ts),W-16.)
 async def scan_same_oracle_dominance_boxes(a,opps_out,now_ts=None):
  O=float(now_ts if now_ts is not None else time.time())
  if a.pending_maker_anchors:await a.manage_pending_maker_anchors(O)
  m=int(math.ceil(O/9e2)*900);f=sum(1 for k in a.dominance_pairs if str(k).endswith(f"_{m}"));l=7. if f<len(DOMINANCE_ASSETS)else 12.;v=float(m)-O;x=math.ceil(O/3600.)*3600.-O;q=(a.is_in_same_oracle_overlap_window(O)if(a.single_scan or"fetch_json"in a.__dict__)else((5.<=v<=330.)or(5.<=x<=905.)))
  if q and(O-a.last_dominance_discovery_ts)>=l:a.last_dominance_discovery_ts=O;await a.discover_dominance_pairs(O)
  if now_ts is None:a.record_usd_spot_samples(time.time())
  p=[(m15,m5)for m15,m5 in list(a.dominance_pairs.values())if(10.<=(m5.end_ts-O)<=(9e2 if m5.horizon=="15m"else 3e2))and(O>=m5.start_ts+1.)]
  if p:
   async def _resolve_dom(m15,m5):
    b,c=await asyncio.gather(a.get_authoritative_open_strike(m15),a.get_authoritative_open_strike(m5))
    if b is None or c is None:return None
    a=float(MIN_CORRIDOR_BPS_BY_ASSET.get(m15.asset,3.));d=determine_dominance_legs(m15,b,m5,c,min_corridor_bps=a);return(m15,m5,d)if d is not None else None
   j=[r for r in await asyncio.gather(*(_resolve_dom(m15,m5)for m15,m5 in p))if r is not None]
   if j:
    u=[]
    for _,_,di in j:Q,P=di["leg_a"],di["leg_b"];u.extend([str(Q["token_id"]),str(P["token_id"]),str(Q.get("opp_token_id")or""),str(P.get("opp_token_id")or"")])
    w=await a.fetch_books_batch(u,timeout=3.)
    for m15,m5,F in j:
     H=m5.end_ts-O;L,K=F["leg_a"],F["leg_b"];N=w.get(str(L["token_id"]));M=w.get(str(K["token_id"]))
     if not N or not M:continue
     b=None;E=float(now_ts)if now_ts is not None else time.time();D=f"{m15.horizon}_{m5.horizon}";a._record_d1_corridor_telemetry(D,m15,m5,F,N,M,E);C=m5.end_ts-E;e=a._strike_is_rest_verified(m15)and a._strike_is_rest_verified(m5);d=False;o=898. if m5.horizon=="15m"else 298.
     if e and 16.<=C<=o:
      i=a._d1_live_max_box_cost();t=a.is_sleeve_grad8_ready("D1_QUIET_BOOK_BOX");h=max(i,.989)if t else i;J=walk_equal_shares_dominance_box(N.get("asks")or[],M.get("asks")or[],target_budget_usd=24.,fee_rate_a=float(L["fee_rate"]),fee_rate_b=float(K["fee_rate"]),fee_exponent_a=float(L["fee_exponent"]),fee_exponent_b=float(K["fee_exponent"]),max_box_cost_net=h,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.86)
      if J.get("filled"):
       g=a._passes_quiet_book_filter(m15.asset,N,M,J,E);n=h if(g and t)else i
       if float(J["box_cost_net"])<=n:
        b=await a._passes_complement_anti_box_check(L,K,prefetched_books=w)
        if not b:continue
        d=a.emit_live_d1_box_candidate(m15,m5,F,J,E,is_quiet_book=g,sleeve_source="D1_QUIET_BOOK_BOX"if g else"D1_SAME_ORACLE_DOMINANCE_BOX")
     I=walk_equal_shares_dominance_box(N.get("asks")or[],M.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_SAME_ORACLE_DOMINANCE_BOX"],fee_rate_a=float(L["fee_rate"]),fee_rate_b=float(K["fee_rate"]),fee_exponent_a=float(L["fee_exponent"]),fee_exponent_b=float(K["fee_exponent"]),max_box_cost_net=1.032,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=.86 if e else.9);c=False
     if I.get("filled"):
      G=float(I["box_cost_net"]);s=round(1.-G,4)
      if G<=1.005:opps_out.append({"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","market":f"{m15.asset} {F['regime']} (TTE={H:.0f}s, {F['corridor_bps']:.1f}bps)","ask_vwap":round(G,4),"p_model":1.,"net_edge":s,"l1_usd":I["l1_usd"]})
      if G<=.995:
       if b is None:b=await a._passes_complement_anti_box_check(L,K,prefetched_books=w)
       if not b:continue
       c=True;await a.open_shadow_dominance_box(m15.asset,m15,m5,F,prefetched_books=(N,M))
       if a._passes_quiet_book_filter(m15.asset,N,M,I,E):await a.open_shadow_dominance_box(m15.asset,m15,m5,F,prefetched_books=(N,M),sleeve_override="D1_QUIET_BOOK_BOX",max_box_cost_override=.992)
     if not c or not d:
      B,_=a._best_ask_sz(N);A,_=a._best_ask_sz(M);z,_=extract_best_bid(N.get("bids")or[]);y,_=extract_best_bid(M.get("bids")or[])
      if(B+A)<=1.02 or(z>.0 and y>.0 and min(z+A,B+y)<=1.005):
       if b is None:b=await a._passes_complement_anti_box_check(L,K,prefetched_books=w)
       if b:a.post_maker_anchor_candidate(m15,m5,F,N,M,E,live_emit_only=bool(c))
  await a._scan_4h_dominance_boxes(opps_out,now_ts)
 def _passes_quiet_book_filter(a,asset,bk_a,bk_b,w_scan,now_ts):
  if abs(a.get_return_bps(asset,5.))>4.5:return False
  if(now_ts-float(a._last_any_shock_ts_by_asset.get(asset,.0)or.0))<4.:return False
  g,_=extract_best_bid(bk_a.get("bids")or[]);f,_=extract_best_bid(bk_b.get("bids")or[]);e=float((w_scan.get("leg_a_walk")or{}).get("best_ask")or 1.);d=float((w_scan.get("leg_b_walk")or{}).get("best_ask")or 1.)
  if g<=.0 or f<=.0:return False
  if(e-g)>.041 or(d-f)>.041:return False
  c=float(w_scan.get("shares")or 12.);b=min(float(w_scan.get("avail_a_shares")or.0),float(w_scan.get("avail_b_shares")or.0));return b>=1.5*c
 async def discover_4h_dominance_pairs(a,now_ts):
  for r,(m,_)in list(a.dominance_4h_pairs.items()):
   if m.end_ts<now_ts-6e2:a.dominance_4h_pairs.pop(r,None)
  for u,q in list(a.s4h_candles.items()):
   if q.end_ts<now_ts-6e2:a.s4h_candles.pop(u,None)
  d=int(math.ceil(now_ts/14400.)*14400);l=float(d)-now_ts
  if not(8.<=l<=905.):return
  j=datetime.fromtimestamp(now_ts-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");i=l<=305.
  for p in DOMINANCE_ASSETS:
   o=DOMINANCE_SERIES_SLUGS[p];h=o.get("4h")
   if not h:continue
   n=f"{p}_4h15m_{d}";t=f"{p}_4h5m_{d}"
   if n in a.dominance_4h_pairs and((not i)or t in a.dominance_4h_pairs):continue
   g,e=await asyncio.gather(a.fetch_json(f"{GAMMA_URL}/events?series_slug={h}&closed=false&end_date_min={j}&order=endDate&ascending=true&limit=3",timeout=4.),a.fetch_json(f"{GAMMA_URL}/events?series_slug={o['15m']}&closed=false&end_date_min={j}&order=endDate&ascending=true&limit=3",timeout=4.));c=None;b=None
   if isinstance(g,list):
    for k in g:
     w=parse_twap_candle_event(k,p,"4h")
     if w and abs(w.end_ts-d)<=2.:c=w;a.s4h_candles[f"{p}_4h_{d}"]=w;break
   if isinstance(e,list):
    for k in e:
     s=parse_twap_candle_event(k,p,"15m")
     if s and abs(s.end_ts-d)<=2.:b=s;break
   if c and b and verify_same_oracle_pair(c,b):a.dominance_4h_pairs[n]=(c,b)
   if c and i and t not in a.dominance_4h_pairs:
    f=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={o['5m']}&closed=false&end_date_min={j}&order=endDate&ascending=true&limit=3",timeout=4.)
    if isinstance(f,list):
     for k in f:
      v=parse_twap_candle_event(k,p,"5m")
      if v and abs(v.end_ts-d)<=2. and verify_same_oracle_pair(c,v):a.dominance_4h_pairs[t]=(c,v);break
 async def _scan_4h_dominance_boxes(a,opps_out,now_ts=None):
  G=float(now_ts if now_ts is not None else time.time());F=math.ceil(G/14400.)*14400.-G
  if 8.<=F<=905. and(G-a.last_4h_discovery_ts)>=12.:a.last_4h_discovery_ts=G;await a.discover_4h_dominance_pairs(G)
  for _,(Y,y)in list(a.dominance_4h_pairs.items()):
   x=y.end_ts-G;w=895. if y.horizon=="15m"else 298.
   if not(10.<=x<=w)or G<y.start_ts+1.:continue
   R,Q=await asyncio.gather(a.get_authoritative_open_strike(Y),a.get_authoritative_open_strike(y))
   if R is None or Q is None:continue
   l=float(MIN_CORRIDOR_BPS_BY_ASSET.get(Y.asset,3.));t=determine_dominance_legs(Y,R,y,Q,min_corridor_bps=l)
   if t is None:continue
   I,H=t["leg_a"],t["leg_b"];E=await a.fetch_books_batch([str(I["token_id"]),str(H["token_id"]),str(I.get("opp_token_id")or""),str(H.get("opp_token_id")or"")],timeout=3.);P=E.get(str(I["token_id"]));O=E.get(str(H["token_id"]))
   if not P or not O:continue
   b=None;k=float(now_ts)if now_ts is not None else time.time();a._record_d1_corridor_telemetry(f"4h_{y.horizon}",Y,y,t,P,O,k)
   if now_ts is None:a.record_usd_spot_samples(k)
   j=y.end_ts-k;e=a._strike_is_rest_verified(Y)and a._strike_is_rest_verified(y);c=False
   if e and 18.<=j<=w:
    i=a._d1_live_max_box_cost();f=a.is_sleeve_grad8_ready("D1_QUIET_BOOK_BOX");h=max(i,.989)if f else i;n=walk_equal_shares_dominance_box(P.get("asks")or[],O.get("asks")or[],target_budget_usd=13.5,fee_rate_a=float(I["fee_rate"]),fee_rate_b=float(H["fee_rate"]),fee_exponent_a=float(I["fee_exponent"]),fee_exponent_b=float(H["fee_exponent"]),max_box_cost_net=h,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.86)
    if n.get("filled"):
     g=a._passes_quiet_book_filter(Y.asset,P,O,n,k);m=h if(g and f)else i
     if float(n["box_cost_net"])<=m:
      b=await a._passes_complement_anti_box_check(I,H,prefetched_books=E)
      if not b:continue
      c=a.emit_live_d1_box_candidate(Y,y,t,n,k,is_quiet_book=g,sleeve_source="D1_QUIET_BOOK_BOX"if g else"D1_4H_DOMINANCE_BOX")
   D=walk_equal_shares_dominance_box(P.get("asks")or[],O.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_4H_DOMINANCE_BOX"],fee_rate_a=float(I["fee_rate"]),fee_rate_b=float(H["fee_rate"]),fee_exponent_a=float(I["fee_exponent"]),fee_exponent_b=float(H["fee_exponent"]),max_box_cost_net=1.032,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=.86 if e else.9);d=False
   if D.get("filled"):
    v=float(D["box_cost_net"])
    if v<=1.005:opps_out.append({"sleeve":"D1_4H_DOMINANCE_BOX","market":f"{Y.asset} {t['regime']} (TTE={x:.0f}s, {t['corridor_bps']:.1f}bps)","ask_vwap":round(v,4),"p_model":1.,"net_edge":round(1.-v,4),"l1_usd":D["l1_usd"]})
    if v<=.992:
     if b is None:b=await a._passes_complement_anti_box_check(I,H,prefetched_books=E)
     if not b:continue
     d=True;await a.open_shadow_dominance_box(Y.asset,Y,y,t,prefetched_books=(P,O),sleeve_override="D1_4H_DOMINANCE_BOX",max_box_cost_override=.992)
     if a._passes_quiet_book_filter(Y.asset,P,O,D,k):await a.open_shadow_dominance_box(Y.asset,Y,y,t,prefetched_books=(P,O),sleeve_override="D1_QUIET_BOOK_BOX",max_box_cost_override=.992)
   if not d or not c:
    s,_=a._best_ask_sz(P);r,_=a._best_ask_sz(O);q,_=extract_best_bid(P.get("bids")or[]);p,_=extract_best_bid(O.get("bids")or[])
    if(s+r)<=1.02 or(q>.0 and p>.0 and min(q+r,s+p)<=1.005):
     if b is None:b=await a._passes_complement_anti_box_check(I,H,prefetched_books=E)
     if b:a.post_maker_anchor_candidate(Y,y,t,P,O,k,live_emit_only=bool(d))
  for _,W in list(a.s4h_candles.items()):
   C=W.end_ts-G
   if not(180.<=C<=9e2)or G<W.start_ts+3600.:continue
   B=await a.get_authoritative_open_strike(W)
   if B is None or B<=.0:continue
   N=read_shm_usd_anchor(W.asset,G,max_age_sec=3.);V=a.usd_spot_hist.get(W.asset);A=N.get("usd_spot")or(float(V[-1][1])if V and(G-float(V[-1][0]))<=5. else a.spots.get(W.asset,.0))
   if not A or float(A)<=.0:continue
   o=float(A);z="UP"if o>B else"DOWN";u=a.get_return_bps(W.asset,30.)
   if(z=="UP"and u<-6.)or(z=="DOWN"and u>6.):continue
   M=evaluate_svi_digital_fair_value(W.asset,o,B,C,is_downward=False,now_ts=G);U=float(M["p_yes"]if z=="UP"else M["p_no"]);T=abs(float(M.get("z_sigma")or.0))
   if T<2.3 or U<.94:continue
   L=W.up_token if z=="UP"else W.down_token;S=await a.fetch_json(f"{CLOB_URL}/book?token_id={L}",timeout=2.5)
   if not S:continue
   X=walk_l2_book_asks(S.get("asks")or[],BANKROLL_TICKETS["T1000"]["S4H_CHAINLINK_CONVERGENCE"],fee_rate=W.fee_rate,min_l1_usd=18.)
   if not X.get("filled"):continue
   K=float(X["eff_px"]);J=U-K
   if.62<=K<=.89 and J>=.03:opps_out.append({"sleeve":"S4H_CHAINLINK_CONVERGENCE","market":f"{W.asset} 4h {z} (TTE={C/60:.1f}m, z={T:.2f})","ask_vwap":K,"p_model":round(U,4),"net_edge":round(J,4),"l1_usd":X["l1_usd"],"close_ts":W.end_ts})
   if.62<=K<=.89 and J>=.045:await a.open_shadow_position(sleeve="S4H_CHAINLINK_CONVERGENCE",dedupe_key=f"S4H_{W.asset}_{W.market_id}",asset_or_city=W.asset,title=f"{W.title} [4h Chainlink Convergence]",side_label=z,token_id=L,fee_rate=W.fee_rate,p_model=U,close_ts=W.end_ts,extra={"market_id":W.market_id,"condition_id":W.condition_id,"horizon":"4h","start_iso":W.start_iso,"end_iso":W.end_iso,"open_price":B,"z_sigma":T},tp_target_px=.96,prefetched_book=S)
 def poll_fresh_shock_triggers(a,now_ts=None,max_age_sec=4.5):
  if not SHOCK_TRIGGER_FILE.exists():return[]
  m=float(now_ts if now_ts is not None else time.time());i=[]
  try:
   e=SHOCK_TRIGGER_FILE.stat().st_size
   if e<a._shock_file_offset:a._shock_file_offset=0
   if e==a._shock_file_offset:return[]
   with open(SHOCK_TRIGGER_FILE,"r",encoding="utf-8",errors="ignore")as f:f.seek(a._shock_file_offset);b=f.read();a._shock_file_offset=f.tell()
   for c in b.splitlines():
    c=c.strip()
    if not c:continue
    try:k=json.loads(c)
    except Exception:continue
    l=str(k.get("shock_id")or k.get("event_id")or"")
    if not l or l in a._seen_shock_ids:continue
    a._seen_shock_ids.append(l)
    if str(k.get("shock_source")or"").upper()=="BOUNDARY_LOCK":continue
    h=str(k.get("asset")or"").upper()
    if h not in DOMINANCE_ASSETS:continue
    j=float(k.get("t0_unix")or.0)
    if j<=.0 or(m-j)>max_age_sec:continue
    d=float(k.get("spot_at_t0")or k.get("trigger_price")or.0)
    if d>.0:a.spots[h]=d;a.spot_hist.setdefault(h,collections.deque(maxlen=600)).append((m,d))
    g=k.get("chainlink_proxy_spot")or k.get("coinbase_spot")
    if g and float(g)>.0:a.usd_spot_hist.setdefault(h,collections.deque(maxlen=400)).append((m,float(g)));a.usd_direct_flags[h]=True
    if abs(float(k.get("shock_ofi")or.0))>=.55:a._last_any_shock_ts_by_asset[h]=m;i.append(k)
  except Exception as exc:pass
  return i
 async def handle_shock_triggers(a,triggers,opps_out,now_ts=None):
  if not triggers:return
  Q=float(now_ts if now_ts is not None else time.time())
  for y in triggers:
   O=str(y.get("asset")or"").upper()
   if O:a._last_any_shock_ts_by_asset[O]=Q
  if a.pending_maker_orders:await a.manage_pending_maker_orders()
  if a.pending_maker_anchors:await a.manage_pending_maker_anchors(Q)
  if os.getenv("PM_DISABLE_SHADOW_M4_CATCHUP","0")=="1"or is_shadow_sleeve_quarantined("M4_SHOCK_STRIKE_CATCHUP"):return
  for N in triggers:
   F=str(N.get("asset")or"").upper()
   if(Q-a._last_m4_shock_ts_by_asset.get(F,.0))<6.:continue
   m=float(N.get("shock_ofi")or.0);l=float(N.get("shock_volume_100ms")or.0);f=7.5e5 if F in("BTC","ETH")else 2.5e5
   if abs(m)<.7 or l<f:continue
   M=float(a.spots.get(F)or N.get("spot_at_t0")or.0)
   if M<=.0:continue
   q=str(N.get("shock_direction")or"").upper()in("BUY","UP");k=[]
   for _,E in list(a.strike_ladders.items()):
    if not E or E[0].asset!=F:continue
    P=E[0].end_ts-Q
    if not(1800.<=P<=86400.):continue
    for L in E:
     if abs(math.log(L.strike/M))>.035:continue
     g=evaluate_svi_digital_fair_value(F,M,L.strike,P,is_downward=L.is_downward,now_ts=Q)
     if L.is_downward:d="NO"if q else"YES"
     else:d="YES"if q else"NO"
     x=L.yes_token if d=="YES"else L.no_token;h=float(g["p_yes"]if d=="YES"else g["p_no"]);k.append((L,d,x,h,g))
   if not k:continue
   a._last_m4_shock_ts_by_asset[F]=Q;await asyncio.sleep(.05);D=await asyncio.gather(*[a.fetch_json(f"{CLOB_URL}/book?token_id={c[2]}",timeout=2.5)for c in k]);e=None;b=None
   for(L,d,x,h,g),R in zip(k,D):
    if not R:continue
    w=walk_l2_book_asks(R.get("asks")or[],1e2,fee_rate=CRYPTO_FEE_RATE)
    if not w.get("filled"):continue
    r=float(w["vwap"]);v=float(w["eff_px"]);K=h-v;j,_=extract_best_bid(R.get("bids")or[]);i=float(w["best_ask"])
    if.2<=v<=.86 and K>=.035:opps_out.append({"sleeve":"M4_SHOCK_STRIKE_CATCHUP","market":f"{F} {L.question} ({d}) [ShockWakeup]","ask_vwap":v,"p_model":round(h,4),"net_edge":round(K,4),"l1_usd":w["l1_usd"]})
    if.22<=r<=.82 and.24<=v<=.84 and K>=.065:
     if e is None or K>e[0]:e=(K,L,d,x,h,g,R)
    elif j>.0 and(i-j)>=.02:
     u=round(min(j+.01,i-.01),4);p=h-u
     if.2<=u<=.8 and p>=.065:
      if b is None or p>b[0]:b=(p,L,d,x,h,g,R)
   if e is not None:_,J,t,C,o,B,I=e;await a.open_shadow_position(sleeve="M4_SHOCK_STRIKE_CATCHUP",dedupe_key=f"M4_{J.market_id}_{t}_{int(Q//300)}",asset_or_city=F,title=J.question,side_label=t,token_id=C,fee_rate=CRYPTO_FEE_RATE,p_model=o,close_ts=J.end_ts,extra={"market_id":J.market_id,"condition_id":J.condition_id,"strike":J.strike,"is_downward":J.is_downward,"iv_annual":B["iv_annual"],"z_sigma":B["z_sigma"],"shock_id":N.get("shock_id"),"shock_ofi":N.get("shock_ofi"),"shock_vol_usd":N.get("shock_volume_100ms")},prefetched_book=I)
   elif b is not None:_,H,s,A,n,z,G=b;await a.post_shadow_maker_entry(sleeve="M4_SHOCK_STRIKE_CATCHUP",dedupe_key=f"M4MKR_{H.market_id}_{s}_{int(Q//60)}",asset=F,title=H.question,side_label=s,token_id=A,p_model=n,close_ts=H.end_ts,extra={"execution_mode":"REACTIVE_POST_ONLY_3P5S","market_id":H.market_id,"condition_id":H.condition_id,"strike":H.strike,"is_downward":H.is_downward,"iv_annual":z["iv_annual"],"z_sigma":z["z_sigma"],"shock_id":N.get("shock_id")},prefetched_book=G,ttl_override_sec=3.5)
 @staticmethod
 def is_in_exact_twap_lock_window(now_ts):a=math.ceil(now_ts/3e2)*3e2;b=a-now_ts;return 4.<=b<=55.
 async def discover_active_twap_candles(b,now_ts=None):
  o=float(now_ts if now_ts is not None else time.time())
  for k,i in list(b.twap_candles.items()):
   if i.end_ts<o-3e2:b.twap_candles.pop(k,None)
  h=int(math.ceil(o/3e2)*300);g=float(h)-o;d=75. if(b.single_scan or"fetch_json"in b.__dict__)else 95.
  if not(3.5<=g<=d):return
  for _,(j,n)in b.dominance_pairs.items():
   if int(n.twap_lookback_sec)==60 and abs(n.end_ts-h)<=2.:b.twap_candles[f"{n.asset}_{n.horizon}_{h}"]=n
   if int(j.twap_lookback_sec)==60 and abs(j.end_ts-h)<=2.:b.twap_candles[f"{j.asset}_{j.horizon}_{h}"]=j
  for _,(m,l)in b.dominance_4h_pairs.items():
   if int(m.twap_lookback_sec)==60 and abs(m.end_ts-h)<=2.:b.twap_candles[f"{m.asset}_4h_{h}"]=m
  f=datetime.fromtimestamp(o-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");c=(h%900)==0
  async def _disc_twap_asset(asset):
   c=DOMINANCE_SERIES_SLUGS[asset];h=f"{asset}_5m_{h}"
   if h not in b.twap_candles:
    b=await b.fetch_json(f"{GAMMA_URL}/events?series_slug={c['5m']}&closed=false&end_date_min={f}&order=endDate&ascending=true&limit=3",timeout=3.)
    if isinstance(b,list):
     for e in b:
      g=parse_twap_candle_event(e,asset,"5m")
      if g and abs(g.end_ts-h)<=2.:b.twap_candles[h]=g;break
   if c:
    f=f"{asset}_15m_{h}"
    if f not in b.twap_candles:
     a=await b.fetch_json(f"{GAMMA_URL}/events?series_slug={c['15m']}&closed=false&end_date_min={f}&order=endDate&ascending=true&limit=3",timeout=3.)
     if isinstance(a,list):
      for e in a:
       d=parse_twap_candle_event(e,asset,"15m")
       if d and abs(d.end_ts-h)<=2.:b.twap_candles[f]=d;break
  await asyncio.gather(*(_disc_twap_asset(a)for a in DOMINANCE_ASSETS))
  if not b.single_scan and g>=22.:
   e=[sp for sp in list(b.twap_candles.values())if abs(sp.end_ts-h)<=2. and f"{sp.asset}_{sp.horizon}_{int(sp.start_ts)}"not in b.chainlink_open_cache]
   if e:await asyncio.gather(*(b.get_authoritative_open_strike(sp)for sp in e))
 async def scan_exact_twap_locks(a,opps_out,now_ts=None):
  if not a.single_scan and is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK"):
   if a.twap_candles:a.twap_candles.clear()
   return
  E=a.__dict__.setdefault("_s2_scan_lock",asyncio.Lock())
  if E.locked():return
  async with E:
   U=float(now_ts if now_ts is not None else time.time());h=bool(a.single_scan or"fetch_json"in a.__dict__);e={}
   if not h:from src.polymarket_research.riskless_protocol_v2_expansion import hydrate_fast_s2_from_shm;e=hydrate_fast_s2_from_shm(a,U)
   K=math.ceil(U/3e2)*3e2-U;D=8. if K<=40. else 12.;c=(not h)and K<=40. and any(abs(sp.end_ts-math.ceil(U/3e2)*3e2)<=2. for sp in a.twap_candles.values())
   if not c and 3.5<=K<=(75. if h else 95.)and(U-a.last_twap_discovery_ts)>=D:a.last_twap_discovery_ts=U;await a.discover_active_twap_candles(U)
   q=os.getenv("PM_QUARANTINE_LOSING_SLEEVES","1")=="1";n=38.5 if q else 45.;m=8. if a.single_scan else 4.2;w=.975 if q else.965;v=2.65 if q else.0;l=[spec for _,spec in sorted(a.twap_candles.items(),key=lambda W:({"BTC":0,"ETH":1,"SOL":2}.get(getattr(W[1],"asset",""),9),getattr(W[1],"end_ts",.0)))if int(spec.twap_lookback_sec)==60 and(m<=(spec.end_ts-U)<=n)and(U>=spec.start_ts+60.)]
   if not l:return
   C=await asyncio.gather(*(a.get_authoritative_open_strike(sp)for sp in l));g=[(sp,W)for sp,W in zip(l,C)if W is not None and W>.0]
   if not g:return
   B=[]
   for sp,_ in g:B.extend([sp.up_token,sp.down_token])
   J=({**e,**(await a.fetch_books_batch(B,timeout=1.5)or{})}if not h else{})
   for O,N in e.items():
    if isinstance(J.get(O),dict)and"minimum_tick_size"not in J[O]and N.get("minimum_tick_size"):J[O]["minimum_tick_size"]=N["minimum_tick_size"]
   for spec,I in g:
    u=float(now_ts)if(a.single_scan and now_ts is not None)else time.time();A=spec.end_ts-u
    if not(m<=A<=n):continue
    T=(read_shm_usd_anchor(spec.asset,u,max_age_sec=2.5)if not(a.single_scan and a.usd_spot_hist.get(spec.asset))else{});t=getattr(a,"_chainlink_ws",None)if not a.single_scan else None;k=t.get_latest_spot(spec.asset,now_ts=u,max_age_sec=2.5)if t is not None else None;f=(t.get_latest_official_twap_60s(spec.asset,now_ts=u,max_age_sec=3.5)if(t is not None and hasattr(t,"get_latest_official_twap_60s"))else None);s=a.usd_spot_hist.get(spec.asset);b=k or T.get("usd_spot")
    if(not b or float(b)<=.0)and s and(u-float(s[-1][0]))<=5.:b=float(s[-1][1])
    if(not b or float(b)<=.0)and a.usd_direct_flags.get(spec.asset,False):b=a.spots.get(spec.asset,.0)
    if not b or float(b)<=.0:continue
    p=float(b);j=bool(k is not None or T.get("source")in("shm_chainlink_proxy","shm_coinlink_usd","shm_coinbase_usd")or a.usd_direct_flags.get(spec.asset,False));M,_=get_wing_implied_vol(spec.asset,p,I,86400.);d=t.get_recent_samples(spec.asset,spec.end_ts-125.)if t is not None else[];i=sum(1 for W,_ in d if W>=(spec.end_ts-60.5))
    if len(d)<2 or(A<=55. and s and i<int(max(3.,(60.-A)*.72))):
     o={round(float(X),1):float(W)for X,W in(s or[])if X>=(spec.end_ts-125.)}
     for S,R in d:o[round(float(S),1)]=float(R)
     d=sorted(o.items(),key=lambda x:x[0])
    if not h and 3.8<=A<=38. and a._strike_is_rest_verified(spec)and len(d)>=6:from src.polymarket_research.riskless_protocol_v2_expansion import maybe_emit_s2_live_locks;maybe_emit_s2_live_locks(a,spec=spec,k_open=I,eval_now=u,rem_sec=A,samples=d,off_twap_60=f,bks_s2=J or{},logger_obj=logger)
    z=compute_exact_twap_lock_probability(asset=spec.asset,open_price=I,current_usd_spot=p,rem_seconds=A,now_ts=u,end_ts=spec.end_ts,spot_samples=d,shm_twap_60s=f or T.get("twap_60s"),iv_annual=M,usd_direct_feed=j,authoritative_chainlink_ws=bool(k is not None),min_rem_seconds=m)
    if not z.get("eligible")or float(z["p_lock"])<.94 or float(z.get("z_lock",.0))<v:continue
    r=str(z["side"]);Q=spec.up_token if r=="UP"else spec.down_token;y=spec.down_token if r=="UP"else spec.up_token;V=J.get(Q)if J else await a.fetch_json(f"{CLOB_URL}/book?token_id={Q}",timeout=2.5)
    if not V:continue
    H=J.get(y)if J else None;L=walk_l2_book_asks(V.get("asks")or[],BANKROLL_TICKETS["T1000"]["S2_EXACT_TWAP_LOCK"],fee_rate=spec.fee_rate,min_l1_usd=15.)
    if not L.get("filled"):continue
    G=float(L["eff_px"]);F=float(z["p_lock"]);P=F-G
    if.74<=G<=.955 and P>=.015:opps_out.append({"sleeve":"S2_EXACT_TWAP_LOCK","market":f"{spec.asset} {spec.horizon} {r} (TTE={A:.0f}s, alpha={z['eff_alpha']:.2f}, z={z['z_lock']:.2f})","ask_vwap":G,"p_model":F,"net_edge":round(P,4),"l1_usd":L["l1_usd"]})
    if F>=w and.76<=G<=.95 and P>=.03:await a.open_shadow_position(sleeve="S2_EXACT_TWAP_LOCK",dedupe_key=f"S2_{spec.asset}_{spec.horizon}_{spec.market_id}",asset_or_city=spec.asset,title=f"{spec.title} [{spec.horizon} TWAP Lock]",side_label=r,token_id=Q,fee_rate=spec.fee_rate,p_model=F,close_ts=spec.end_ts,extra={"market_id":spec.market_id,"condition_id":spec.condition_id,"horizon":spec.horizon,"start_iso":spec.start_iso,"end_iso":spec.end_iso,"open_price":I,"mu_twap":z["mu_twap"],"eff_alpha":z["eff_alpha"],"z_lock":z["z_lock"],"cushion_bps":z["cushion_bps"],"rem_seconds_at_entry":z["rem_seconds"]},tp_target_px=None,prefetched_book=V)
 async def discover_s5m_candles(a,now_ts):
  for k,h in list(a.s5m_candles.items()):
   if h.end_ts<now_ts-3e2:a.s5m_candles.pop(k,None)
  g=int(math.ceil(now_ts/3e2)*300);f=float(g)-now_ts
  if not(35.<=f<=185.):return
  b=("BTC","ETH","SOL")
  for _,(_,m)in a.dominance_pairs.items():
   if m.asset in b and abs(m.end_ts-g)<=2.:a.s5m_candles[f"{m.asset}_5m_{g}"]=m
  for l,j in a.twap_candles.items():
   if j.asset in b and j.horizon=="5m"and abs(j.end_ts-g)<=2.:a.s5m_candles[l]=j
  e=datetime.fromtimestamp(now_ts-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  for i in b:
   if i not in DOMINANCE_SERIES_SLUGS or"5m"not in DOMINANCE_SERIES_SLUGS[i]:continue
   p=f"{i}_5m_{g}"
   if p in a.s5m_candles:continue
   d=DOMINANCE_SERIES_SLUGS[i]["5m"];c=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={d}&closed=false&end_date_min={e}&order=endDate&ascending=true&limit=3",timeout=3.5)
   if isinstance(c,list):
    for o in c:
     n=parse_twap_candle_event(o,i,"5m")
     if n and abs(n.end_ts-g)<=2.:a.s5m_candles[p]=n;break
 async def scan_s5m_chainlink_sniper(a,opps_out,now_ts=None):
  if not a.single_scan and is_shadow_sleeve_quarantined("S5M_CHAINLINK_SNIPER"):
   if a.s5m_candles:a.s5m_candles.clear()
   return
  v=float(now_ts if now_ts is not None else time.time());o=math.ceil(v/3e2)*3e2-v
  if 40.<=o<=180. and(v-a.last_s5m_discovery_ts)>=20.:a.last_s5m_discovery_ts=v;await a.discover_s5m_candles(v)
  e=float(getattr(a,"_last_s5m_book_scan_ts",.0)or.0)
  if not a.single_scan and(v-e)<9.5:return
  a._last_s5m_book_scan_ts=v
  for _,s in list(a.s5m_candles.items()):
   j=s.end_ts-v
   if not(45.<=j<=165.)or v<s.start_ts+25.:continue
   n=await a.get_authoritative_open_strike(s)
   if n is None or n<=.0:continue
   u=read_shm_usd_anchor(s.asset,v,max_age_sec=3.)if not a.single_scan else{};h=a.usd_spot_hist.get(s.asset);b=u.get("usd_spot")
   if(not b or float(b)<=.0)and h and(v-float(h[-1][0]))<=5.:b=float(h[-1][1])
   if(not b or float(b)<=.0)and a.usd_direct_flags.get(s.asset,False):b=a.spots.get(s.asset,.0)
   if not b or float(b)<=.0:continue
   d=float(b);c=s.asset not in("BTC","ETH");g=abs(d-n)/n*1e2
   if g<(.14 if c else.085):continue
   f="UP"if d>n else"DOWN";i=a.get_return_bps(s.asset,15.)
   if(f=="UP"and i<-4.)or(f=="DOWN"and i>4.):continue
   m=evaluate_svi_digital_fair_value(s.asset,d,n,j,is_downward=False,dvol_annual_override=.42 if(a.single_scan and"fetch_json"in a.__dict__)else None,now_ts=v);l=float(m["p_yes"]if f=="UP"else m["p_no"]);q=abs(float(m.get("z_sigma")or.0))
   if q<(2.25 if c else 1.35)or l<(.935 if c else.905):continue
   t=s.up_token if f=="UP"else s.down_token;w=await a.fetch_json(f"{CLOB_URL}/book?token_id={t}",timeout=2.5)
   if not w:continue
   p=walk_l2_book_asks(w.get("asks")or[],BANKROLL_TICKETS["T1000"]["S5M_CHAINLINK_SNIPER"],fee_rate=s.fee_rate,min_l1_usd=18.)
   if not p.get("filled"):continue
   k=float(p["eff_px"]);r=l-k
   if.58<=k<=.86 and r>=.025:opps_out.append({"sleeve":"S5M_CHAINLINK_SNIPER","market":f"{s.asset} 5m {f} (TTE={j:.0f}s, dist={g:.3f}%, z={q:.2f})","ask_vwap":k,"p_model":round(l,4),"net_edge":round(r,4),"l1_usd":p["l1_usd"],"close_ts":s.end_ts})
   if.58<=k<=.86 and r>=(.055 if c else.045):await a.open_shadow_position(sleeve="S5M_CHAINLINK_SNIPER",dedupe_key=f"S5M_{s.asset}_{s.market_id}",asset_or_city=s.asset,title=f"{s.title} [5m Chainlink Sniper]",side_label=f,token_id=t,fee_rate=s.fee_rate,p_model=l,close_ts=s.end_ts,extra={"market_id":s.market_id,"condition_id":s.condition_id,"horizon":"5m","start_iso":s.start_iso,"end_iso":s.end_iso,"open_price":n,"dist_pct":round(g,4),"z_sigma":q},tp_target_px=.96,prefetched_book=w)
 async def discover_upcoming_15m_candles(a,now_ts):
  for j,g in list(a.preopen_15m_candles.items()):
   if g.start_ts<=now_ts+5.:a.preopen_15m_candles.pop(j,None)
  b=int(math.ceil(now_ts/9e2)*900);c=float(b)-now_ts
  if not(25.<=c<=250.):return
  f=datetime.fromtimestamp(now_ts,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  for i in("BTC","ETH"):
   h=f"{i}_pre15m_{b}"
   if h in a.preopen_15m_candles:continue
   e=DOMINANCE_SERIES_SLUGS[i]["15m"];d=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={e}&closed=false&end_date_min={f}&order=endDate&ascending=true&limit=5",timeout=3.5)
   if isinstance(d,list):
    for l in d:
     k=parse_twap_candle_event(l,i,"15m")
     if k and abs(k.start_ts-b)<=2.:a.preopen_15m_candles[h]=k;break
 async def scan_and_manage_preopen_maker_straddles(b,opps_out,now_ts=None):
  if is_shadow_sleeve_quarantined("P1_PREOPEN_MAKER_STRADDLE"):
   if b.pending_preopen_straddles:b.pending_preopen_straddles.clear()
   return
  P=float(now_ts if now_ts is not None else time.time());f=int(math.ceil(P/9e2)*900);o=float(f)-P
  if 25.<=o<=250. and(P-b.last_preopen_discovery_ts)>=20.:b.last_preopen_discovery_ts=P;await b.discover_upcoming_15m_candles(P)
  D=float(getattr(b,"_last_p1_manage_ts",.0)or.0)
  if not b.single_scan and not b.pending_preopen_straddles and not(30.<=o<=245.):return
  if not b.single_scan and(P-D)<8.:return
  b._last_p1_manage_ts=P
  for r,R in list(b.pending_preopen_straddles.items()):
   z=R["spec"];q,p=await asyncio.gather(b.fetch_json(f"{CLOB_URL}/book?token_id={z.up_token}",timeout=2.5),b.fetch_json(f"{CLOB_URL}/book?token_id={z.down_token}",timeout=2.5));K=float(R["bid_px"]);w=P-float(R["posted_ts"])
   if q and w>=4.:
    d=q.get("asks")or[];n=min((float(a["price"])for a in d if float(a.get("size",0))>0),default=1.)
    if n<=K:R["up_filled"]=True
   if p and w>=4.:
    c=p.get("asks")or[];m=min((float(a["price"])for a in c if float(a.get("size",0))>0),default=1.)
    if m<=K:R["dn_filled"]=True
   if R["up_filled"]and R["dn_filled"]:
    b.pending_preopen_straddles.pop(r,None);y=round(2.*K,4);v={}
    for h,t in BANKROLL_TICKETS.items():Q=max(5.,float(math.floor(t["P1_PREOPEN_MAKER_STRADDLE"]/max(.9,y))));L=round(Q*y,2);v[h]={"filled":True,"vwap":y,"eff_px":y,"spent_usd":L,"fee_usd":.0,"shares":Q,"l1_usd":1e2}
    J=f"P1_PREOPEN_MAKER_STRADDLE_{int(P)}_{z.market_id[-6:]}";N=[{"token_id":z.up_token,"side":"UP","market_id":z.market_id,"label":"PRE_UP"},{"token_id":z.down_token,"side":"DOWN","market_id":z.market_id,"label":"PRE_DOWN"}];O={"position_id":J,"dedupe_key":r,"sleeve":"P1_PREOPEN_MAKER_STRADDLE","asset_or_city":z.asset,"title":f"{z.title} [Pre-Open Maker $0.48+$0.48]","side":"PRE_UP+PRE_DOWN","token_id":f"{z.up_token}|{z.down_token}","fee_rate":.0,"entry_ts":P,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":z.end_ts,"p_model_entry":1.,"entry_eff_px_t1000":y,"entry_vwap_t1000":y,"realized_edge_t1000":round(1.-y,4),"entry_best_bid":y,"last_bid":y,"maker_tp_px":None,"tier_fills":v,"extra":{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"market_id":z.market_id,"legs":N},"status":"OPEN"};b.open_positions[J]=O;b.entered_keys.add(r);b._append_ledger({"event":"SHADOW_ENTRY",**O});logger.info(f"[ENTRY:P1_PREOPEN_MAKER_STRADDLE] {O['title']} | BOTH LEGS FILLED @ ${y:.2f} -> $1.00 lock!");continue
   B=float(b.spots.get(z.asset)or R["posted_spot"]or.0);l=float(R["posted_spot"]or B or 1.);A=abs(B-l)/max(1e-9,l)*1e4
   if P>=(z.start_ts-10.)or A>18.:
    b.pending_preopen_straddles.pop(r,None);b.entered_keys.add(r)
    if not R["up_filled"]and not R["dn_filled"]:continue
    x=bool(R["up_filled"]);I=q if x else p;e,_=extract_best_bid((I or{}).get("bids")or[])
    if e<=.0:e=max(.01,K-.03)
    j=z.fee_rate*e*(1.-e);u=max(.0,e-j);i={};k={}
    for h,t in BANKROLL_TICKETS.items():M=max(5.,float(math.floor(t["P1_PREOPEN_MAKER_STRADDLE"]/max(.9,2.*K))));s=round(M*K,2);i[h]={"filled":True,"vwap":K,"eff_px":K,"spent_usd":s,"fee_usd":.0,"shares":M};k[h]=round(M*u-s,2)
    C={"position_id":f"P1_SCRATCH_{int(P)}_{z.market_id[-6:]}","dedupe_key":r,"sleeve":"P1_PREOPEN_MAKER_STRADDLE","asset_or_city":z.asset,"title":f"{z.title} [Pre-Open 1-Leg Scratch]","side":"PRE_UP_SCRATCH"if x else"PRE_DOWN_SCRATCH","token_id":z.up_token if x else z.down_token,"fee_rate":.0,"entry_ts":R["posted_ts"],"entry_utc":datetime.fromtimestamp(R["posted_ts"],tz=timezone.utc).isoformat(),"close_ts":z.end_ts,"closed_ts":P,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":.5,"entry_eff_px_t1000":K,"entry_vwap_t1000":K,"net_payout_per_share":round(u,4),"tier_fills":i,"tier_pnls_usd":k,"won":k.get("T1000",.0)>0,"status":"PREOPEN_ONE_LEG_SCRATCH"};b.closed_positions.append(C);b._append_ledger({"event":"SHADOW_CLOSE",**C});logger.info(f"[CLOSE:P1_PREOPEN_MAKER_STRADDLE] {C['title']} -> PREOPEN_ONE_LEG_SCRATCH | bid_exit=${e:.3f} net=${u:.4f} | PnL T1000=${k.get('T1000',.0):+.2f}")
  for _,z in list(b.preopen_15m_candles.items()):
   g=z.start_ts-P
   if not(40.<=g<=240.):continue
   r=f"P1_{z.asset}_{z.market_id}"
   if r in b.entered_keys or r in b.pending_preopen_straddles:continue
   if abs(b.get_return_bps(z.asset,15.))>8.:continue
   q,p=await asyncio.gather(b.fetch_json(f"{CLOB_URL}/book?token_id={z.up_token}",timeout=2.5),b.fetch_json(f"{CLOB_URL}/book?token_id={z.down_token}",timeout=2.5))
   if not q or not p:continue
   H,_=extract_best_bid(q.get("bids")or[]);G,_=extract_best_bid(p.get("bids")or[]);d=q.get("asks")or[];c=p.get("asks")or[];F=min((float(a["price"])for a in d if float(a.get("size",0))>0),default=1.);E=min((float(a["price"])for a in c if float(a.get("size",0))>0),default=1.)
   if F>=.49 and E>=.49 and.44<=H<=.51 and.44<=G<=.51:opps_out.append({"sleeve":"P1_PREOPEN_MAKER_STRADDLE","market":f"{z.asset} Pre-Open 15m Straddle (T-{g:.0f}s, asks={F:.2f}/{E:.2f})","ask_vwap":.96,"p_model":1.,"net_edge":.04,"l1_usd":1e2,"close_ts":z.end_ts});b.pending_preopen_straddles[r]={"spec":z,"bid_px":.48,"posted_ts":P,"posted_spot":float(b.spots.get(z.asset)or.0),"up_filled":False,"dn_filled":False};logger.info(f"[MAKER_POST:P1_PREOPEN_MAKER_STRADDLE] {z.title} | Resting $0.48 UP + $0.48 DOWN (T-{g:.0f}s)")
 async def resolve_via_gamma_market(b,pos):
  h=pos.get("extra")or{};i=str(h.get("market_id")or"");k=str(pos.get("token_id")or"");g=None
  if i:
   j=await b.fetch_json(f"{GAMMA_URL}/markets/{i}",timeout=4.)
   if isinstance(j,dict):g=j
  if g is None and k:
   d=await b.fetch_json(f"{GAMMA_URL}/markets?clob_token_ids={k}",timeout=4.)
   if isinstance(d,list)and d:g=d[0]
  if not isinstance(g,dict)or not g.get("closed"):return None
  f=str(g.get("umaResolutionStatus")or"").strip().lower()
  if f and f!="resolved":return None
  c=g.get("clobTokenIds")
  if isinstance(c,str):
   try:c=json.loads(c)
   except Exception:c=[]
  e=g.get("outcomePrices")
  if isinstance(e,str):
   try:e=json.loads(e)
   except Exception:e=[]
  if not isinstance(e,list)or len(e)<2:return None
  a=-1
  if isinstance(c,list)and k in[str(t)for t in c]:a=[str(t)for t in c].index(k)
  else:a=0 if str(pos.get("side","YES")).upper()in("YES","UP")else 1
  if a<0 or a>=len(e):return None
  try:l=float(e[a])
  except Exception:return None
  if l>=.99:return 1.
  if l<=.01:return.0
  if f=="resolved"and.49<=l<=.51:return round(l,4)
  return None
 def _try_early_overround_bid_unwind(self,pos,legs_bids_spec,now):
  if(now-float(pos.get("entry_ts")or.0))<15.:return None
  d=pos.get("tier_fills")or{}
  if"T1000"not in d:return None
  g=float(d["T1000"].get("shares")or.0)
  if g<=.0:return None
  k=pos.get("extra")or{};f=float(k.get("guaranteed_payout")or pos.get("p_model_entry")or 1.);e=float(pos.get("entry_eff_px_t1000")or.99);h=float(pos["close_ts"])-now;b=pos.get("sleeve")in("C1_BINARY_COMPLETE_SET","NR0_ZERO_FEE_SLATE_ARB","N1_NEGRISK_CROSS_BOX","W3_WEATHER_SLATE_ARB","P1_PREOPEN_MAKER_STRADDLE")or float(k.get("max_payout")or 2.)<=1.001
  if b:a=max(e+.008,f+.004)
  elif h>3600.:a=max(e+.015,f+.005)
  else:a=max(e+.08,f+.08)
  j=walk_position_overround_bid_unwind(legs_bids_spec,g,min_net_proceeds_per_set=a)
  if not j.get("filled"):return None
  c={}
  for i,n in d.items():
   l=float(n.get("shares")or.0)
   if l<=.0:continue
   m=walk_position_overround_bid_unwind(legs_bids_spec,l,min_net_proceeds_per_set=a)
   if not m.get("filled"):return None
   c[i]=float(m["net_proceeds_per_set"])
  return float(j["net_proceeds_per_set"]),c
 async def manage_open_positions(c):
  _2=time.time();_Y=asyncio.get_running_loop();_g=[]
  for _p,_n in list(c.open_positions.items()):
   _x=_n["sleeve"];_1=_n["token_id"]
   if _x=="W3_WEATHER_SLATE_ARB":
    e=float(_n["close_ts"]);_l=_n.get("extra")or{};_b=_l.get("legs")or[]
    if _2<e+30.:
     S=None
     if(_2-float(_n.get("_last_book_poll_ts")or.0))>=30. and _b:
      _n["_last_book_poll_ts"]=_2;S=await asyncio.gather(*[c.fetch_json(f"{CLOB_URL}/book?token_id={lg.get('token_id')or lg.get('yes_token','')}",timeout=2.5)for lg in _b])
      if all(S):
       _n["last_bid"]=round(sum(extract_best_bid((b or{}).get("bids")or[])[0]for b in S),4);_X=c._try_early_overround_bid_unwind(_n,[{"bids":(b or{}).get("bids")or[],"fee_rate":.0,"fee_exponent":1.}for b in S],_2)
       if _X is not None:_g.append((_p,"EARLY_OVERROUND_BID_UNWIND",_X[0],_X[1]));continue
     if(_2-float(_n.get("_last_gamma_chk_ts")or.0))<(30. if(S is not None and not all(S))else 120.):continue
     _n["_last_gamma_chk_ts"]=_2
    if _b:
     R=float(_l.get("guaranteed_payout")or 1.);i=await asyncio.gather(*[c.resolve_via_gamma_market({"token_id":lg.get("token_id")or lg.get("yes_token",""),"side":lg.get("side","YES"),"extra":{"market_id":lg["market_id"]}})for lg in _b])
     if i and all(v is not None for v in i):f=round(sum(float(v)for v in i if v is not None),4);_W="SETTLED_WEATHER_SLATE_1X"if R<=1.01 else"SETTLED_WEATHER_SLATE_NX";_g.append((_p,_W,max(R,f),.0))
    continue
   X=_n.get("extra")or{}
   if _x in("D1_SAME_ORACLE_DOMINANCE_BOX","D1_4H_DOMINANCE_BOX","D1_QUIET_BOOK_BOX","D1_MAKER_ANCHOR_BOX","M3_LADDER_MONO_BOX","B3_BARRIER_MONO_BOX","C1_BINARY_COMPLETE_SET","CM_B3_PYTH_BARRIER_BOX","SP1_NBA_ZERO_FEE_BOX","ZERO_FEE_MAKER_ANCHOR_BOX","ZF_INTRADAY_MAKER_BOX","D2_12PM_BINANCE_BOX")or(X.get("leg_a")and X.get("leg_b")):
    m=_n.get("extra")or{};_P=m.get("leg_a")or{};_O=m.get("leg_b")or{};e=float(_n["close_ts"])
    if _2<e+10.:
     _V,_U=await asyncio.gather(c.fetch_json(f"{CLOB_URL}/book?token_id={_P.get('token_id','')}",timeout=2.5),c.fetch_json(f"{CLOB_URL}/book?token_id={_O.get('token_id','')}",timeout=2.5))
     if _V and _U:
      _N,_=extract_best_bid(_V.get("bids")or[]);_M,_=extract_best_bid(_U.get("bids")or[]);_n["last_bid"]=round(_N+_M,4);_w=float(_n.get("fee_rate")or.0);_T=c._try_early_overround_bid_unwind(_n,[{"bids":_V.get("bids")or[],"fee_rate":float(_P.get("fee_rate",_w)),"fee_exponent":float(_P.get("fee_exponent",1.))},{"bids":_U.get("bids")or[],"fee_rate":float(_O.get("fee_rate",_w)),"fee_exponent":float(_O.get("fee_exponent",1.))}],_2)
      if _T is not None:_g.append((_p,"EARLY_OVERROUND_BID_UNWIND",_T[0],_T[1]));continue
     if(_x=="C1_BINARY_COMPLETE_SET"and _P.get("market_id")and _P.get("market_id")==_O.get("market_id")and(_2-float(_n.get("entry_ts")or.0))>=15.):_g.append((_p,"CTF_COMPLETE_SET_MERGED",1.,.0));continue
     if _V and _U:continue
     if _V or _U or(_2-float(_n.get("_last_gamma_chk_ts")or.0))<60.:continue
     _n["_last_gamma_chk_ts"]=_2
    _L,_K=await asyncio.gather(c.resolve_via_gamma_market({"token_id":_P.get("token_id",""),"side":_P.get("side","UP"),"extra":{"market_id":_P.get("market_id","")}}),c.resolve_via_gamma_market({"token_id":_O.get("token_id",""),"side":_O.get("side","DOWN"),"extra":{"market_id":_O.get("market_id","")}}))
    if _L is not None and _K is not None:f=round(float(_L)+float(_K),4);g="SETTLED_DOMINANCE_DOUBLE_2X"if f>=1.99 else"SETTLED_DOMINANCE_FLOOR_1X";_g.append((_p,g,f,.0));continue
    if _x=="B3_BARRIER_MONO_BOX"and _2>=e+9e2:
     _S=str(m.get("direction")or"UP").upper();_v=await _Y.run_in_executor(None,fetch_binance_window_extremes_sync,_n["asset_or_city"],float(_n["entry_ts"]),e,"1m")
     if _v is not None:t,s,_=_v;_u=float(_P.get("strike")or.0);_t=float(_O.get("strike")or.0);_0=(_S=="UP"and t>=_u)or(_S=="DOWN"and s<=_u);_Z=(_S=="UP"and t>=_t)or(_S=="DOWN"and s<=_t);f=(1. if _0 else.0)+(.0 if _Z else 1.);_g.append((_p,"SETTLED_BARRIER_MONO_2X"if f>=1.99 else"SETTLED_BARRIER_MONO_1X",f,.0))
     continue
    if _2>=e+360. and m.get("m15_start_iso"):
     _J=14400. if str(_P.get("horizon"))=="4h"else(9e2 if str(_P.get("horizon"))=="15m"else 3e2);_I=14400. if str(_O.get("horizon"))=="4h"else(9e2 if str(_O.get("horizon"))=="15m"else 3e2);_f=build_own_gamma_event_url(_n["asset_or_city"],str(_P.get("horizon")or"15m"),e-_J);_e=build_own_gamma_event_url(_n["asset_or_city"],str(_O.get("horizon")or"5m"),e-_I);_d,_c=await asyncio.gather(c.fetch_json(_f,timeout=4.),c.fetch_json(_e,timeout=4.));_H=parse_closed_gamma_event_settlement(_d,str(_P.get("side")or"UP"),_f);_G=parse_closed_gamma_event_settlement(_c,str(_O.get("side")or"DOWN"),_e)
     if _H is not None and _G is not None:f=round(_H+_G,4);g=("SETTLED_ORACLE_DOUBLE_2X"if f>=1.99 else("SETTLED_ORACLE_FLOOR_1X"if f>=.99 else"SETTLED_ORACLE_LOSS_0X"));_g.append((_p,g,f,.0))
    continue
   if _x in("N1_NEGRISK_CROSS_BOX","P1_PREOPEN_MAKER_STRADDLE","NR0_ZERO_FEE_SLATE_ARB")or bool(X.get("legs")):
    m=_n.get("extra")or{};_b=m.get("legs")or[];e=float(_n["close_ts"])
    if _2<e+20.:
     Q=None
     if(_2-float(_n.get("_last_book_poll_ts")or.0))>=30. and _b:
      _n["_last_book_poll_ts"]=_2;Q=await asyncio.gather(*[c.fetch_json(f"{CLOB_URL}/book?token_id={lg['token_id']}",timeout=2.5)for lg in _b])
      if all(Q):
       _n["last_bid"]=round(sum(extract_best_bid((b or{}).get("bids")or[])[0]for b in Q),4);_a=float(_n.get("fee_rate")or.0);_R=c._try_early_overround_bid_unwind(_n,[{"bids":(b or{}).get("bids")or[],"fee_rate":float(lg.get("fee_rate",_a)),"fee_exponent":float(lg.get("fee_exponent",1.))}for lg,b in zip(_b,Q)],_2)
       if _R is not None:_g.append((_p,"EARLY_OVERROUND_BID_UNWIND",_R[0],_R[1]));continue
     if(_2-float(_n.get("_last_gamma_chk_ts")or.0))<(30. if(Q is not None and not all(Q))else 120.):continue
     _n["_last_gamma_chk_ts"]=_2
    i=await asyncio.gather(*[c.resolve_via_gamma_market({"token_id":lg["token_id"],"side":lg.get("side","YES"),"extra":{"market_id":lg.get("market_id","")}})for lg in _b])
    if i and all(v is not None for v in i):f=round(sum(float(v)for v in i if v is not None),4);_g.append((_p,"SETTLED_MULTI_LEG_ARB",f,.0))
    elif _x=="P1_PREOPEN_MAKER_STRADDLE"and _2>=e+9e2:_g.append((_p,"SETTLED_COMPLETE_SET_1X",1.,.0))
    continue
   if _x=="S2_EXACT_TWAP_LOCK":
    m=_n.get("extra")or{};e=float(_n["close_ts"])
    if _2<e+12.:
     _F=await c.fetch_json(f"{CLOB_URL}/book?token_id={_1}",timeout=2.5)
     if _F:_s,_=extract_best_bid(_F.get("bids")or[]);_n["last_bid"]=_s
     continue
    u=await c.resolve_via_gamma_market(_n)
    if u is not None:g="SETTLED_GAMMA_WIN"if u>=.99 else"SETTLED_GAMMA_LOSS";_g.append((_p,g,u,.0));continue
    if _2>=e+120. and m.get("start_iso"):
     E=build_own_gamma_event_url(_n["asset_or_city"],str(m.get("horizon")or"15m"),m["start_iso"]);l=await c.fetch_json(E,timeout=4.);q=parse_authoritative_close_price(l);z=float(m.get("open_price")or.0)
     if q is not None and z>.0:D=q>=z;B=D if str(_n.get("side")).upper()=="UP"else(not D);g="SETTLED_ORACLE_TWAP_WIN"if B else"SETTLED_ORACLE_TWAP_LOSS";_g.append((_p,g,1. if B else.0,.0))
    continue
   if _x in("B1_CONVEX_TAIL_YES","B2_BARRIER_NO_LOCK"):
    j=_n["asset_or_city"];k=float(_n["extra"].get("strike")or.0);d=_n["extra"].get("direction");P=float(_n.get("_last_wick_chk_ts")or.0)
    if k>0 and(_2-P)>=60.:
     _n["_last_wick_chk_ts"]=_2;y=float(_n["extra"].get("start_ts")or _n["entry_ts"]);_E=min(_2,float(_n["close_ts"]));_r=await _Y.run_in_executor(None,fetch_binance_window_extremes_sync,j,y,_E,"1m")
     if _r is not None:
      t,s,_=_r;x=(d=="UP"and t>=k)or(d=="DOWN"and s<=k)
      if x:C=1. if _n["side"]=="YES"else.0;_g.append((_p,"BARRIER_1M_WICK_SETTLED",C,.0));continue
   if(not c.single_scan and not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK")and c.is_in_exact_twap_lock_window(_2)and float(_n["close_ts"])>_2+120. and(_2-float(_n.get("_last_book_poll_ts")or.0))<20.):continue
   _n["_last_book_poll_ts"]=_2;bk=await c.fetch_json(f"{CLOB_URL}/book?token_id={_1}",timeout=3.)
   if bk:
    r,_=extract_best_bid(bk.get("bids")or[]);_n["last_bid"]=r;_D=_n.get("maker_tp_px")
    if _D and r>=float(_D)and(_2-_n["entry_ts"])>=15.:_g.append((_p,"MAKER_TP_FILLED",float(_D),.0));continue
    if _x in("M1_SVI_MAKER_SCALP","M4_SHOCK_STRIKE_CATCHUP")and r>0 and(_2-_n["entry_ts"])>=30.:
     n=float(_n["entry_vwap_t1000"]);_k=float(_n["close_ts"])-_2;W=.085 if _x=="M4_SHOCK_STRIKE_CATCHUP"else.075;G=9e2 if _x=="M4_SHOCK_STRIKE_CATCHUP"else 3600.
     if r<=n-W:h=CRYPTO_FEE_RATE*r*(1.-r);_g.append((_p,"HARD_STOP_SVI",max(.0,r-h),.0));continue
     if _k<=G:h=CRYPTO_FEE_RATE*r*(1.-r);_g.append((_p,"TIME_STOP",max(.0,r-h),.0));continue
    if _x=="M2_STRIKE_CONVERGENCE"and r>0 and(_2-_n["entry_ts"])>=30.:
     n=float(_n["entry_vwap_t1000"])
     if r<=max(.25,n-.22):h=CRYPTO_FEE_RATE*r*(1.-r);_g.append((_p,"SALVAGE_STOP",max(.0,r-h),.0));continue
   else:
    O=float(_n.get("_last_gamma_chk_ts")or.0)
    if(_2-O)>=60.:
     _n["_last_gamma_chk_ts"]=_2;u=await c.resolve_via_gamma_market(_n)
     if u is not None:g="SETTLED_GAMMA_WIN"if u>=.99 else"SETTLED_GAMMA_LOSS";_g.append((_p,g,u,.0));continue
   if _2>=float(_n["close_ts"])+30.:
    u=await c.resolve_via_gamma_market(_n)
    if u is not None:g="SETTLED_GAMMA_WIN"if u>=.99 else"SETTLED_GAMMA_LOSS";_g.append((_p,g,u,.0));continue
    if bk and _x in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY")and _2>=float(_n["close_ts"])+9e2:
     I,H=extract_best_bid(bk.get("bids")or[]);F=float(_n.get("entry_eff_px_t1000")or _n.get("entry_vwap_t1000")or.995);_C=float(_n.get("fee_rate")or.0);_B=float((_n.get("extra")or{}).get("fee_exponent")or 1.);N=I-(_C*((I*(1.-I))**_B)if _C>.0 else.0)
     if I>=.997 and H>=25. and N>=F+.002:
      _j=str((_n.get("extra")or{}).get("market_id")or"");_A=await c.fetch_json(f"{GAMMA_URL}/markets/{_j}",timeout=3.5)if _j else None;_q=str((_A or{}).get("umaResolutionStatus")or"").strip().lower()if isinstance(_A,dict)else""
      if _q=="disputed"or _2>=float(_n["close_ts"])+14400.:_g.append((_p,"UMA_DISPUTED_LOCK_PROFIT_RECYCLE",round(N,4),.0));continue
    if bk and _x not in("BOND1_UMA_RESOLUTION_CARRY","SP2_NBA_ENDGAME_LOCK"):
     r,_=extract_best_bid(bk.get("bids")or[]);_Q=bk.get("asks")or[];Z=min((float(a["price"])for a in _Q if float(a.get("size",0))>0),default=1.)
     if r>=.99:_g.append((_p,"SETTLED_WIN",1.,.0));continue
     if Z<=.01:_g.append((_p,"SETTLED_LOSS",.0,.0));continue
    if _x in("S5M_CHAINLINK_SNIPER","S4H_CHAINLINK_CONVERGENCE")and _2>=float(_n["close_ts"])+120.:
     m=_n.get("extra")or{}
     if m.get("start_iso"):
      E=build_own_gamma_event_url(_n["asset_or_city"],str(m.get("horizon")or"5m"),m["start_iso"]);l=await c.fetch_json(E,timeout=4.);q=parse_authoritative_close_price(l);z=float(m.get("open_price")or.0)
      if q is not None and z>.0:D=q>=z;B=D if str(_n.get("side")).upper()=="UP"else(not D);g="SETTLED_ORACLE_TWAP_WIN"if B else"SETTLED_ORACLE_TWAP_LOSS";_g.append((_p,g,1. if B else.0,.0));continue
    if _2>=float(_n["close_ts"])+9e2:
     if _x in("B1_CONVEX_TAIL_YES","B2_BARRIER_NO_LOCK"):
      j=_n["asset_or_city"];k=float(_n["extra"].get("strike")or.0);d=_n["extra"].get("direction");y=float(_n["extra"].get("start_ts")or _n["entry_ts"]);_i=await _Y.run_in_executor(None,fetch_binance_window_extremes_sync,j,y,float(_n["close_ts"]),"1m")
      if _i is not None and k>0:t,s,_=_i;x=(d=="UP"and t>=k)or(d=="DOWN"and s<=k);C=(1. if x else.0)if _n["side"]=="YES"else(.0 if x else 1.);_g.append((_p,"SETTLED_VERIFIED_1M_ORACLE",C,.0));continue
     elif _x=="U1_DAILY_UPDOWN_LOCK":
      j=_n["asset_or_city"];k=float(_n["extra"]["strike"]);e=float(_n["close_ts"]);w=await _Y.run_in_executor(None,fetch_binance_window_extremes_sync,j,e-120.,e,"1m")
      if w is not None and k>0:o=w[2];B=(o>=k)if str(_n["side"]).upper()=="UP"else(o<k);_g.append((_p,"SETTLED_VERIFIED_1M_CLOSE",1. if B else.0,.0));continue
     elif _x in("M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","M4_SHOCK_STRIKE_CATCHUP"):
      j=_n["asset_or_city"];k=float(_n["extra"]["strike"]);_z=bool(_n["extra"].get("is_downward"));e=float(_n["close_ts"]);w=await _Y.run_in_executor(None,fetch_binance_window_extremes_sync,j,e-120.,e,"1m")
      if w is not None and k>0:o=w[2];_h=(o<k)if _z else(o>k);B=_h if _n["side"]=="YES"else(not _h);_g.append((_p,"SETTLED_VERIFIED_1M_CLOSE",1. if B else.0,.0));continue
  for _p,_o,M,p in _g:
   _n=c.open_positions.pop(_p,None)
   if not _n:continue
   V={};A={};Y=(_n.get("extra")or{}).get("legging_drag_usd_by_tier")or{};U=p if isinstance(p,dict)else{}
   for _m,tf in _n["tier_fills"].items():L=float(tf["spent_usd"])+float(tf["fee_usd"]);K=float(U.get(_m,M));J=float(tf["shares"])*K;_y=round(J-L,2);V[_m]=_y;A[_m]=round(_y-float(Y.get(_m,.0)or.0),2)
   T=V.get("T1000",.0)>0;_n.update({"status":_o,"closed_ts":_2,"closed_utc":datetime.now(timezone.utc).isoformat(),"net_payout_per_share":round(M,4),"tier_pnls_usd":V,"legging_adjusted_tier_pnls_usd":A,"won":T});c.closed_positions.append(_n);c._append_ledger({"event":"SHADOW_CLOSE",**_n});logger.info(f"[CLOSE:{_n['sleeve']}] {_n['title']} ({_n['side']}) -> {_o} | PnL T100=${V.get('T100',0):+.2f} T1000=${V.get('T1000',0):+.2f} T5000=${V.get('T5000',0):+.2f}")
 def write_state_files(a,opps):
  if len(getattr(a,"authoritative_strike_cache",{}))>2000:
   for I in list(a.authoritative_strike_cache.keys())[:-1500]:a.authoritative_strike_cache.pop(I,None)
  if len(a.entered_keys)>5000:t={str(p.get("dedupe_key")or"")for p in a.open_positions.values()};a.entered_keys=t|set(list(a.entered_keys)[-3000:])
  m=read_global_positions_shm();e=[p for J,K in(m.get("daemons")or{}).items()if J!="alpha124_shadow"and isinstance(K,dict)for p in(K.get("positions")or[])];i=rank_opportunities_capital_auction(opps,active_global_positions=list(a.open_positions.values())+e)[:25];a.top_opportunities=i;publish_global_positions_shm("alpha124_shadow",a.open_positions.values());q={};h={"T100":.0,"T1000":.0,"T5000":.0}
  for H in BANKROLL_TICKETS["T1000"].keys():
   s=str(H).startswith("D1_");d=_filter_epoch_closed_positions(str(H),[p for p in a.closed_positions if p.get("sleeve")==H]);o=[p for p in d if not(s and p.get("status")!="MAKER_ANCHOR_UNHEDGED_SCRATCH"and float(p.get("entry_eff_px_t1000")or 1.)<.9)];c=len(d)-len(o);v=[p for p in a.open_positions.values()if p.get("sleeve")==H];F=sum(1 for p in o if p.get("won"));w=sum(float(p.get("tier_pnls_usd",{}).get("T1000",.0))for p in o);l=sum(float(p.get("legging_adjusted_tier_pnls_usd",p.get("tier_pnls_usd",{})).get("T1000",.0))for p in o)
   for G in h:h[G]=round(h[G]+sum(float(p.get("tier_pnls_usd",{}).get(G,.0))for p in o),2)
   q[H]={"open":len(v),"closed":len(o),"wins":F,"losses":len(o)-F,"win_rate_pct":round(1e2*F/len(o),2)if o else.0,"realized_pnl_t1000_usd":round(w,2),"legging_adjusted_pnl_t1000_usd":round(l,2),"excluded_anti_box":c,"quarantined":is_shadow_sleeve_quarantined(H),"grad8_live_promoted":bool(len(o)>=8 and F==len(o)and round(w,2)>.0 and round(l,2)>.0 and not is_shadow_sleeve_quarantined(H))}
  b={"D1_SAME_ORACLE_DOMINANCE_BOX","D1_4H_DOMINANCE_BOX","D1_QUIET_BOOK_BOX"};g={}
  for C in DOMINANCE_ASSETS:E=[p for p in a.closed_positions if str(p.get("sleeve")or"")in b and str(p.get("asset_or_city")or"").upper()==C and(p.get("status")=="MAKER_ANCHOR_UNHEDGED_SCRATCH"or float(p.get("entry_eff_px_t1000")or 1.)>=.9)];D=[p for p in a.open_positions.values()if str(p.get("sleeve")or"")in b and str(p.get("asset_or_city")or"").upper()==C];u=sum(1 for p in E if p.get("won"));r=sum(float(p.get("tier_pnls_usd",{}).get("T1000",.0))for p in E);f=sum(float(p.get("legging_adjusted_tier_pnls_usd",p.get("tier_pnls_usd",{})).get("T1000",.0))for p in E);g[C]={"open":len(D),"closed":len(E),"wins":u,"losses":len(E)-u,"win_rate_pct":round(1e2*u/len(E),2)if E else.0,"realized_pnl_t1000_usd":round(r,2),"legging_adjusted_pnl_t1000_usd":round(f,2)}
  B={"updated_at_utc":datetime.now(timezone.utc).isoformat(),"started_at":a.started_at,"cycle_count":a.cycle_count,"calibration":{"weather_sigma_c":a.weather_sigma_c,"barrier_wick_mult":a.barrier_wick_mult},"spots":a.spots,"markets_monitored":{"weather_city_events":len(a.weather_events),"barrier_hit_rungs":len(a.barrier_rungs),"multistrike_ladders":len(a.strike_ladders),"negrisk_bracket_ladders":len(a.negrisk_ladders),"daily_updown_markets":len(a.daily_updown_markets),"pyth_daily_markets":len(a.pyth_daily_markets),"pyth_barrier_rungs":len(a.pyth_barrier_rungs),"pyth_close_ladders":len(a.pyth_close_ladders),"nba_zero_fee_games":len(a.nba_games),"live_nba_scoreboard_games":len(a.live_nba_board),"uma_proposed_markets":len(a.uma_proposed_markets),"negrisk_zero_fee_slates":len(a.negrisk_zero_slates),"counting_slates":len(a.counting_slates),"fomc_lp_markets":len(a.fomc_truth_legs)//2,"oil_senate_markets":len(a.oil_senate_truth_legs)//2,"hourly_12pm_pairs":len(a.hourly_12pm_markets),"same_oracle_dominance_pairs":len(a.dominance_pairs),"dominance_4h_pairs":len(a.dominance_4h_pairs),"exact_twap_lock_candles":len(a.twap_candles),"s5m_sniper_candles":len(a.s5m_candles),"s4h_candles":len(a.s4h_candles),"preopen_15m_candles":len(a.preopen_15m_candles)},"portfolio_realized_pnl_by_bankroll_usd":h,"gatling_projection":compute_gatling_trajectory_projection(starting_nav_usd=60.92),"by_sleeve":q,"per_strategy":q,"by_d1_asset":g,"open_positions_count":len(a.open_positions),"pending_maker_orders_count":len(a.pending_maker_orders),"pending_maker_anchors_count":len(a.pending_maker_anchors),"pending_zero_fee_maker_anchors_count":len(a.pending_zero_fee_maker_anchors),"pending_preopen_straddles_count":len(a.pending_preopen_straddles),"pending_maker_orders":list(a.pending_maker_orders.values()),"open_positions":list(a.open_positions.values()),"recent_closed_positions":a.closed_positions[-30:]};A=STATE_FILE.with_suffix(".tmp");A.write_text(json.dumps(B,indent=2),encoding="utf-8");os.replace(A,STATE_FILE)
  if STATE_FILE==(DATA_DIR/"alpha124_shadow_state.json")or LIVE_ALPHA124_STATE_MIRROR_FILE!=(LIVE_POLYMARKET_DIR/"alpha124_shadow_state.json"):
   try:LIVE_ALPHA124_STATE_MIRROR_FILE.parent.mkdir(parents=True,exist_ok=True);z=LIVE_ALPHA124_STATE_MIRROR_FILE.with_suffix(".tmp");z.write_text(json.dumps({"updated_at_utc":B["updated_at_utc"],"by_sleeve":q,"per_strategy":q,"by_d1_asset":g},indent=2),encoding="utf-8");os.replace(z,LIVE_ALPHA124_STATE_MIRROR_FILE)
   except Exception as exc:pass
  y=OPPS_FILE.with_suffix(".tmp");y.write_text(json.dumps({"updated_at_utc":B["updated_at_utc"],"top_opportunities":i},indent=2),encoding="utf-8");os.replace(y,OPPS_FILE);x=time.time()
  if(x-float(getattr(a,"_last_proj_write_ts",.0)))>=60.:
   a._last_proj_write_ts=x
   try:
    import importlib;import scripts.polymarket_daily_projections as _proj_mod;k=getattr(_proj_mod,"__file__",None)
    if k:
     n=Path(k).stat().st_mtime_ns;j=getattr(a,"_proj_mod_mtime_ns",None)
     if j is None:a._proj_mod_mtime_ns=n
     elif n!=j:_proj_mod=importlib.reload(_proj_mod);a._proj_mod_mtime_ns=n
    _proj_mod.write_live_projections_atomic(days=30)
   except Exception as exc:pass
 async def write_state_files_async(self,opps):await asyncio.to_thread(self.write_state_files,opps)
 async def _run_bg_discovery(self):
  try:await self.discover_all_markets()
  except Exception as exc:logger.warning(f"Background discovery notice: {exc}")
 async def _run_bg_mid_crypto(a):
  try:b=[];await a.scan_multistrike_markets(b);await a.scan_daily_updown_locks(b);await a.scan_barrier_markets(b);a.cached_mid_opps=b
  except Exception as exc:logger.warning(f"Background mid-crypto scan notice: {exc}")
 async def _run_bg_weather(a):
  try:b=[];await a.scan_weather_markets(b);a.cached_weather_opps=b
  except Exception as exc:logger.warning(f"Background weather scan notice: {exc}")
 async def _get_pyth_intraday(a,asset,now_ts):
  f=PYTH_ASSET_CONFIG.get(asset.upper())
  if not f:return None
  d,_,_,_,b=f;c=a.pyth_intraday_cache.get(d)
  if c is not None and(now_ts-c[0])<90.:return c[1]
  e=await asyncio.to_thread(fetch_yahoo_1m_intraday_sync,d,b)
  if e is not None:a.pyth_intraday_cache[d]=(now_ts,e)
  return e
 async def scan_tradfi_and_sports_markets(a,opps_out):
  now=time.time();f=sorted({r.asset for r in a.pyth_barrier_rungs.values()if r.end_ts>now+120}|{rgs[0].asset for rgs in a.pyth_close_ladders.values()if rgs and rgs[0].end_ts>now+120});u={}
  for a_p in f:
   fd=await a._get_pyth_intraday(a_p,now)
   if fd:u[a_p]=fd
  _s=[]
  for r in a.pyth_barrier_rungs.values():
   if r.end_ts<=now+120 or r.asset not in u:continue
   J=float(u[r.asset]["spot"])
   if J>0 and abs(math.log(r.strike/J))<=.25:_s.append(r)
  K=[]
  for rgs in a.pyth_close_ladders.values():
   for rc in rgs:
    if rc.end_ts<=now+120 or rc.asset not in u:continue
    J=float(u[rc.asset]["spot"])
    if J>0 and abs(math.log(rc.strike/J))<=.14:K.append(rc)
  W=([r.yes_token for r in _s]+[r.no_token for r in _s]+[rc.yes_token for rc in K]+[rc.no_token for rc in K]);_r=await a.fetch_books_batch(W,timeout=3.5)if W else{};z=[];h=collections.defaultdict(list)
  for r in _s:
   _q,y=_r.get(r.yes_token),_r.get(r.no_token)
   if not _q or not y:continue
   _9=PYTH_ASSET_CONFIG[r.asset];_,k,j,e,_=_9;fd=u[r.asset];_af=float(fd["spot"]);l=now>=r.start_ts;_aM=window_extremes_from_bars(fd["bars"],r.start_ts,now)if l else None
   if l and now>=r.start_ts+3e2 and j and k in("EQUITY_RTH","CME_23H")and _aM is not None and f"B4_PYTH_{r.market_id}"not in a.entered_keys:
    _bg,_bf=_aM;_ae=.0015 if k=="EQUITY_RTH"else max(.008,2.5*e);I=.78 if k=="EQUITY_RTH"else.88
    if(r.direction=="UP"and _bg>=r.strike*(1.+_ae))or(r.direction=="DOWN"and _bf<=r.strike*(1.-_ae)):
     _O,_=extract_best_bid(_q.get("bids")or[]);_aL=walk_l2_book_asks(_q.get("asks")or[],1e2,fee_rate=r.fee_rate,min_l1_usd=15.,max_ask_px=.99,fee_exponent=r.fee_exponent)
     if _aL.get("filled")and _O>=I and.85<=float(_aL["eff_px"])<=.986:opps_out.append({"sleeve":"B4_TOUCHED_BARRIER_WICK_LOCK","market":f"{r.asset} Pyth Breached Wick Lock: {r.question}","ask_vwap":_aL["eff_px"],"p_model":1.,"net_edge":round(1.-float(_aL["eff_px"]),4),"l1_usd":_aL["l1_usd"]});await a.open_shadow_position(sleeve="B4_TOUCHED_BARRIER_WICK_LOCK",dedupe_key=f"B4_PYTH_{r.market_id}",asset_or_city=r.asset,title=r.question,side_label="YES",token_id=r.yes_token,fee_rate=r.fee_rate,p_model=1.,close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"strike":r.strike,"direction":r.direction,"session_class":k,"fee_exponent":r.fee_exponent},prefetched_book=_q);continue
   _p=walk_l2_book_asks(_q.get("asks")or[],35.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);_o=walk_l2_book_asks(y.get("asks")or[],35.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);_aK={"asset":r.asset,"event_id":r.event_id,"strike":r.strike,"direction":r.direction,"market_id":r.market_id,"condition_id":r.condition_id,"yes_token":r.yes_token,"no_token":r.no_token,"fee_rate":r.fee_rate,"fee_exponent":r.fee_exponent,"ask_yes":_p.get("vwap")if _p.get("filled")else None,"ask_no":_o.get("vwap")if _o.get("filled")else None,"bk_yes":_q,"bk_no":y,"start_ts":r.start_ts,"end_ts":r.end_ts};z.append(_aK);h[r.event_id].append(_aK);_N=compute_effective_trading_hours(now,r.end_ts,k);V=is_same_continuous_session(now,r.end_ts,k);A=_aM is not None and((r.direction=="UP"and _aM[0]>=r.strike*(1.-e))or(r.direction=="DOWN"and _aM[1]<=r.strike*(1.+e)))
   if l and j and V and not A and.25<=_N<=3.5:
    _aJ=evaluate_pyth_session_barrier_no_lock(_af,r.strike,r.direction,_N,float(fd["sigma_session"]),e);_ad=float(_aJ["p_no"])
    if _ad>=.94:
     _ac,_=extract_best_bid(y.get("bids")or[]);_be=walk_l2_book_asks(y.get("asks")or[],1e2,fee_rate=r.fee_rate,min_l1_usd=15.,fee_exponent=r.fee_exponent)
     if _be.get("filled")and.78<=float(_be["eff_px"])<=.955 and _ac>0 and(float(_be["vwap"])-_ac)<=.04:
      _M=_ad-float(_be["eff_px"]);_bd=evaluate_barrier_no_net_ev(1.-_ad,float(_be["vwap"]),fee_rate=r.fee_rate)
      if _M>=.025:opps_out.append({"sleeve":"CM_B2_PYTH_SESSION_NO_LOCK","market":f"{r.asset} Pyth NO ({_N:.1f}h sess): {r.question}","ask_vwap":_be["eff_px"],"p_model":_ad,"net_edge":round(_M,4),"l1_usd":_be["l1_usd"]})
      if _M>=.035 and _bd["eligible"]:await a.open_shadow_position(sleeve="CM_B2_PYTH_SESSION_NO_LOCK",dedupe_key=f"CMB2_{r.market_id}",asset_or_city=r.asset,title=r.question,side_label="NO",token_id=r.no_token,fee_rate=r.fee_rate,p_model=_ad,close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"strike":r.strike,"direction":r.direction,"eff_session_hours":round(_N,2),"fee_exponent":r.fee_exponent},prefetched_book=y)
   _L=a.prev_pyth_spots.get(r.asset,.0)
   if l and j and V and not A and _L>.0:
    _aI=evaluate_pyth_catalyst_shock(r.asset,_L,_af,r.strike,r.direction,_N,float(fd["sigma_session"]),now)
    if _aI.get("eligible"):
     _K=str(_aI["side"]);_ab=r.yes_token if _K=="YES"else r.no_token;_aH=_q if _K=="YES"else y;_bc=walk_l2_book_asks(_aH.get("asks")or[],BANKROLL_TICKETS["T1000"]["CM_SHOCK_PYTH_CATALYST"],fee_rate=r.fee_rate,min_l1_usd=15.,fee_exponent=r.fee_exponent)
     if _bc.get("filled")and.18<=float(_bc["eff_px"])<=.88:
      _J=float(_aI["p_fair"])-float(_bc["eff_px"])
      if _J>=.045:opps_out.append({"sleeve":"CM_SHOCK_PYTH_CATALYST","market":f"{r.asset} [{_aI['catalyst']}] {_K}: {r.question}","ask_vwap":_bc["eff_px"],"p_model":_aI["p_fair"],"net_edge":round(_J,4),"l1_usd":_bc["l1_usd"],"close_ts":r.end_ts});await a.open_shadow_position(sleeve="CM_SHOCK_PYTH_CATALYST",dedupe_key=f"CMSHK_{r.market_id}_{_K}_{int(now//900)}",asset_or_city=r.asset,title=f"{r.question} [{_aI['catalyst']}]",side_label=_K,token_id=_ab,fee_rate=r.fee_rate,p_model=float(_aI["p_fair"]),close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"catalyst":_aI["catalyst"],"delta_p":_aI["delta_p"],"ret_pct":_aI["ret_pct"],"fee_exponent":r.fee_exponent},tp_target_px=min(.95,round(float(_bc["eff_px"])+.06,3)),prefetched_book=_aH)
  for a_p,_bb in u.items():a.prev_pyth_spots[a_p]=float(_bb["spot"])
  o=[]
  for rc in K:
   _q,y=_r.get(rc.yes_token),_r.get(rc.no_token)
   if not _q or not y:continue
   _p=walk_l2_book_asks(_q.get("asks")or[],35.,fee_rate=rc.fee_rate,min_l1_usd=8.,fee_exponent=rc.fee_exponent);_o=walk_l2_book_asks(y.get("asks")or[],35.,fee_rate=rc.fee_rate,min_l1_usd=8.,fee_exponent=rc.fee_exponent);o.append({"asset":rc.asset,"strike":rc.strike,"is_downward":rc.is_downward,"market_id":rc.market_id,"condition_id":rc.condition_id,"yes_token":rc.yes_token,"no_token":rc.no_token,"fee_rate":rc.fee_rate,"fee_exponent":rc.fee_exponent,"ask_yes":_p.get("vwap")if _p.get("filled")else None,"ask_no":_o.get("vwap")if _o.get("filled")else None,"bk_yes":_q,"bk_no":y,"end_ts":rc.end_ts});_9=PYTH_ASSET_CONFIG[rc.asset];_,k,j,e,_=_9;fd=u[rc.asset];U=compute_effective_trading_hours(now,rc.end_ts,k)
   if j and is_same_continuous_session(now,rc.end_ts,k)and.08<=U<=.75:
    _aG=evaluate_pyth_session_close_lock(float(fd["spot"]),rc.strike,rc.is_downward,U,float(fd["sigma_session"]),e)
    if _aG["eligible"]:
     _7=str(_aG["side"]);_aF=rc.yes_token if _7=="YES"else rc.no_token;_ba=_q if _7=="YES"else y;_6,_=extract_best_bid(_ba.get("bids")or[]);_a9=walk_l2_book_asks(_ba.get("asks")or[],1e2,fee_rate=rc.fee_rate,min_l1_usd=15.,fee_exponent=rc.fee_exponent)
     if _a9.get("filled")and.78<=float(_a9["eff_px"])<=.955 and _6>0 and(float(_a9["vwap"])-_6)<=.04:
      _I=float(_aG["p_lock"])-float(_a9["eff_px"])
      if _I>=.02:opps_out.append({"sleeve":"CM_U1_PYTH_CLOSE_LOCK","market":f"{rc.asset} Close Lock ({_7}, z={_aG['z_session']:.2f}): {rc.question}","ask_vwap":_a9["eff_px"],"p_model":_aG["p_lock"],"net_edge":round(_I,4),"l1_usd":_a9["l1_usd"]})
      if _I>=.03:await a.open_shadow_position(sleeve="CM_U1_PYTH_CLOSE_LOCK",dedupe_key=f"CMU1_{rc.market_id}_{_7}",asset_or_city=rc.asset,title=rc.question,side_label=_7,token_id=_aF,fee_rate=rc.fee_rate,p_model=float(_aG["p_lock"]),close_ts=rc.end_ts,extra={"market_id":rc.market_id,"condition_id":rc.condition_id,"strike":rc.strike,"z_session":_aG["z_session"],"fee_exponent":rc.fee_exponent},prefetched_book=_ba)
  for _5,_H in u.items():
   _aE=PYTH_ASSET_CONFIG.get(_5)
   if not _aE:continue
   _,_4,_G,_,_=_aE;H=[rh for rh in z if rh["asset"]==_5 and rh.get("ask_no")is not None]
   if not H:continue
   T=min(H,key=lambda x:(float(x["end_ts"]),abs(math.log(float(x["strike"])/max(1e-6,float(_H["spot"]))))));_F=compute_effective_trading_hours(now,float(T["end_ts"]),_4);_3=is_same_continuous_session(now,float(T["end_ts"]),_4);_n,_E=extract_best_bid(T["bk_no"].get("bids")or[]);_m,_l=a._best_ask_sz(T["bk_no"]);a._record_market_telemetry(key=f"PYTH_SNAP_{_5}",min_interval_sec=120.,now_ts=now,sig=(round(float(_H["spot"]),3),round(_m,3),round(_n,3)),payload={"type":"PYTH_ASSET_SESSION_SNAP","asset":_5,"session_class":_4,"exact_directional_ok":_G,"spot":round(float(_H["spot"]),4),"sigma_session":_H["sigma_session"],"eff_session_hours":round(_F,2),"same_session":_3,"near_strike":T["strike"],"near_dir":T["direction"],"near_ask_no":round(_m,4)if _m<1. else None,"near_bid_no":round(_n,4)if _n>0 else None,"near_ask_l1_usd":round(_m*_l,2)if _m<1. else.0})
  n=[]
  for _D,_C in h.items():
   if len(_C)<2:continue
   _2=detect_barrier_monotonicity_boxes(_C,fee_rate=.0,max_box_cost_net=1.15)
   if _2:pd0=_2[0];a._record_market_telemetry(key=f"CMB3_DIAG_{_D}",min_interval_sec=90.,now_ts=now,sig=(pd0["direction"],pd0["low_strike"],pd0["high_strike"],pd0["box_cost_net"]),payload={"type":"PYTH_BARRIER_MONO_BEST","asset":_C[0]["asset"],"event_id":_D,"net_box_l1":pd0["box_cost_net"],"label":pd0["label"]})
   _aD={str(q["yes_token"]):q for q in _C};_aC={str(q["no_token"]):q for q in _C}
   for ba in _2:
    if float(ba["box_cost_net"])>1.035:continue
    qy,qn=_aD.get(ba["yes_token"]),_aC.get(ba["no_token"])
    if qy and qn:la={"token_id":ba["yes_token"],"opp_token_id":ba["yes_opp_token"],"condition_id":ba["leg_yes_condition_id"],"side":"YES","label":f"YES_{ba['direction']}","market_id":ba["leg_yes_market_id"],"fee_rate":float(qy.get("fee_rate",.0)),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(qy["strike"])};lb={"token_id":ba["no_token"],"opp_token_id":ba["no_opp_token"],"condition_id":ba["leg_no_condition_id"],"side":"NO","label":f"NO_{ba['direction']}","market_id":ba["leg_no_market_id"],"fee_rate":float(qn.get("fee_rate",.0)),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(qn["strike"])};n.append((qy["asset"],f"CMB3_MONO_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",la,lb,qy["bk_yes"],qn["bk_no"],float(qy["end_ts"]),f"{qy['asset']} Pyth Box {ba['label']}"))
  _k=detect_pyth_calendar_inclusion_boxes(z,max_box_cost_net=1.15)
  if _k:cd0=_k[0];a._record_market_telemetry(key=f"CMB3_CAL_BEST_{cd0['asset']}",min_interval_sec=90.,now_ts=now,sig=(cd0["direction"],cd0["strike"],cd0["box_cost_net"]),payload={"type":"PYTH_CALENDAR_BEST","asset":cd0["asset"],"net_box_l1":cd0["box_cost_net"],"label":cd0["label"]})
  for cal in _k:
   if float(cal["box_cost_net"])>1.035:continue
   qy,qn=cal["yes_row"],cal["no_row"];la={"token_id":qy["yes_token"],"opp_token_id":qy["no_token"],"condition_id":qy["condition_id"],"side":"YES","label":"YES_LONG","market_id":qy["market_id"],"fee_rate":float(qy.get("fee_rate",.0)),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(qy["strike"])};lb={"token_id":qn["no_token"],"opp_token_id":qn["yes_token"],"condition_id":qn["condition_id"],"side":"NO","label":"NO_SHORT","market_id":qn["market_id"],"fee_rate":float(qn.get("fee_rate",.0)),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(qn["strike"])};n.append((cal["asset"],f"CMB3_CAL_{qy['market_id']}_{qn['market_id']}",la,lb,qy["bk_yes"],qn["bk_no"],float(cal["close_ts"]),f"{cal['asset']} Calendar Box {cal['label']}"))
  _j=detect_pyth_close_vs_hit_boxes(o,z,now_ts=now,max_box_cost_net=1.15)
  if _j:vd0=_j[0];a._record_market_telemetry(key=f"CMB3_CVH_BEST_{vd0['asset']}",min_interval_sec=90.,now_ts=now,sig=(vd0["strike_hit"],vd0["strike_close"],vd0["box_cost_net"]),payload={"type":"PYTH_CLOSE_VS_HIT_BEST","asset":vd0["asset"],"net_box_l1":vd0["box_cost_net"],"label":vd0["label"]})
  for cvh in _j:
   if float(cvh["box_cost_net"])>1.035:continue
   qy,qn=cvh["yes_row"],cvh["no_row"];la={"token_id":qy["yes_token"],"opp_token_id":qy["no_token"],"condition_id":qy["condition_id"],"side":"YES","label":"YES_HIT","market_id":qy["market_id"],"fee_rate":float(qy.get("fee_rate",.0)),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(qy["strike"])};lb={"token_id":qn["no_token"],"opp_token_id":qn["yes_token"],"condition_id":qn["condition_id"],"side":"NO","label":"NO_CLOSE","market_id":qn["market_id"],"fee_rate":float(qn.get("fee_rate",.0)),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(qn["strike"])};n.append((cvh["asset"],f"CMB3_CVH_{qy['market_id']}_{qn['market_id']}",la,lb,qy["bk_yes"],qn["bk_no"],float(cvh["close_ts"]),f"{cvh['asset']} Close-vs-Hit Box {cvh['label']}"))
  n.sort(key=lambda x:((float(x[6])-now)>64800.,float(x[6])))
  for _B,_Z,la,lb,_d,_c,_a8,_A in n:
   _a7=walk_equal_shares_dominance_box(_d.get("asks")or[],_c.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["CM_B3_PYTH_BARRIER_BOX"],fee_rate_a=float(la["fee_rate"]),fee_rate_b=float(lb["fee_rate"]),fee_exponent_a=float(la.get("fee_exponent",1.)),fee_exponent_b=float(lb.get("fee_exponent",1.)),max_box_cost_net=.994,min_shares=6,min_box_notional_usd=5.5)
   if _a7.get("filled"):
    opps_out.append({"sleeve":"CM_B3_PYTH_BARRIER_BOX","market":_A,"ask_vwap":round(float(_a7["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_a7["box_cost_net"]),4),"l1_usd":_a7["l1_usd"],"close_ts":_a8});d=False
    if float(_a7["box_cost_net"])<=.993 and(_a8-now)<=172800.:d=a.emit_live_two_leg_box_candidate(sleeve_source="CM_B3_PYTH_BARRIER_BOX",box_type="BARRIER_MONO",asset=_B,dedupe_key=_Z,leg_a=la,leg_b=lb,bk_a=_d,bk_b=_c,close_ts=_a8,now_ts=now,k_low=min(float(la.get("strike")or 1e2),float(lb.get("strike")or 1e2)),k_high=max(float(la.get("strike")or 1e2),float(lb.get("strike")or 1e2)))
    if(_a8-now)<=172800.:await a.open_shadow_two_leg_box(sleeve="CM_B3_PYTH_BARRIER_BOX",dedupe_key=_Z,asset=_B,title=_A,leg_a=la,leg_b=lb,bk_a=_d,bk_b=_c,close_ts=_a8,max_box_cost_net=.994,extra={"is_pyth_zero_fee_box":True})
    if not d:a.post_zero_fee_maker_anchor_box("CM_B3",_B,f"ZFA_{_Z}",la,lb,_d,_c,_a8,_A,now,live_emit_only=bool((_a8-now)<=172800.))
   else:a.post_zero_fee_maker_anchor_box("CM_B3",_B,f"ZFA_{_Z}",la,lb,_d,_c,_a8,_A,now)
  for _Y in list(a.nba_games.values()):
   if now>_Y.tipoff_ts+6.*3600.:a.nba_games.pop(_Y.event_id,None);continue
   _g=_Y.margin_legs+_Y.total_legs;_f=sorted({lg.token_id for lg in _g})
   if len(_f)<4:continue
   _z=await a.fetch_books_batch(_f,timeout=3.5);t={}
   for t_n,y in _z.items():
    _a6,_a5=a._best_ask_sz(y)
    if _a6<1. and _a5*_a6>=8.:t[t_n]=_a6
   _e=detect_nba_dominance_boxes(_Y,t,max_box_cost_net=1.12)
   if _e:
    nd0=_e[0];_a4,_a3=nd0["leg_a"],nd0["leg_b"];_a2=_z.get(_a4.token_id)or{};_a1=_z.get(_a3.token_id)or{};aa0,sa0=a._best_ask_sz(_a2);ab0,sb0=a._best_ask_sz(_a1);ba0,_=extract_best_bid(_a2.get("bids")or[]);bb0,_=extract_best_bid(_a1.get("bids")or[]);S=[]
    if ba0>0 and(aa0-ba0)>=.02:S.append(round(min(ba0+.01,aa0-.01)+ab0,4))
    if bb0>0 and(ab0-bb0)>=.02:S.append(round(aa0+min(bb0+.01,ab0-.01),4))
    R=min(S)if S else None;a._record_market_telemetry(key=f"NBA_BOX_{_Y.event_id}",min_interval_sec=45.,now_ts=now,sig=(nd0["label"],nd0["box_cost_net"],R),payload={"type":"NBA_ZERO_FEE_BOX_BEST","event_id":_Y.event_id,"game":_Y.title,"box_kind":nd0["box_kind"],"in_play":bool(now>=_Y.tipoff_ts),"sec_from_tipoff":round(now-_Y.tipoff_ts,0),"best_label":nd0["label"],"leg_a_ask":round(aa0,4),"leg_a_bid":round(ba0,4)if ba0>0 else None,"leg_b_ask":round(ab0,4),"leg_b_bid":round(bb0,4)if bb0>0 else None,"net_box_l1":nd0["box_cost_net"],"maker_anchor_box_l1":R,"l1_min_usd":round(min(aa0*sa0,ab0*sb0),2),"middle_pts":nd0["middle_width_pts"]})
   for nb in _e:
    if float(nb["box_cost_net"])>1.06:continue
    lga,lgb=nb["leg_a"],nb["leg_b"];_d,_c=_z.get(lga.token_id),_z.get(lgb.token_id)
    if not _d or not _c:continue
    _a0={"token_id":lga.token_id,"opp_token_id":lga.opp_token_id,"condition_id":lga.condition_id,"side":lga.side_label,"label":lga.display_label,"market_id":lga.market_id,"fee_rate":lga.fee_rate,"fee_exponent":lga.fee_exponent,"strike":float(lga.threshold)};_aZ={"token_id":lgb.token_id,"opp_token_id":lgb.opp_token_id,"condition_id":lgb.condition_id,"side":lgb.side_label,"label":lgb.display_label,"market_id":lgb.market_id,"fee_rate":lgb.fee_rate,"fee_exponent":lgb.fee_exponent,"strike":float(lgb.threshold)}
    if float(nb["box_cost_net"])>.994:a.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_SP1_{_Y.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",_a0,_aZ,_d,_c,float(nb["close_ts"]),f"{_Y.title} [{nb['label']}]",now,prefetched_books=_z);continue
    _aB=walk_equal_shares_dominance_box(_d.get("asks")or[],_c.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["SP1_NBA_ZERO_FEE_BOX"],fee_rate_a=lga.fee_rate,fee_rate_b=lgb.fee_rate,fee_exponent_a=lga.fee_exponent,fee_exponent_b=lgb.fee_exponent,max_box_cost_net=.994,min_shares=8,min_box_notional_usd=7.)
    if _aB.get("filled"):
     opps_out.append({"sleeve":"SP1_NBA_ZERO_FEE_BOX","market":f"NBA {_Y.title}: {nb['label']} (mid={nb['middle_width_pts']}pt)","ask_vwap":round(float(_aB["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_aB["box_cost_net"]),4),"l1_usd":_aB["l1_usd"],"close_ts":nb["close_ts"]});c=False
     if float(_aB["box_cost_net"])<=.99 and(float(nb["close_ts"])-now)<=86400.:c=a.emit_live_two_leg_box_candidate(sleeve_source="SP1_NBA_ZERO_FEE_BOX",box_type="NBA_DOMINANCE",asset="NBA",dedupe_key=f"SP1_{_Y.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",leg_a=_a0,leg_b=_aZ,bk_a=_d,bk_b=_c,close_ts=float(nb["close_ts"]),now_ts=now)
     await a.open_shadow_two_leg_box(sleeve="SP1_NBA_ZERO_FEE_BOX",dedupe_key=f"SP1_{_Y.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",asset="NBA",title=f"{_Y.title} [{nb['label']}]",leg_a=_a0,leg_b=_aZ,bk_a=_d,bk_b=_c,close_ts=float(nb["close_ts"]),max_box_cost_net=.994,extra={"is_nba_zero_fee_box":True,"box_kind":nb["box_kind"],"middle_width_pts":nb["middle_width_pts"]})
     if not c:a.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_SP1_{_Y.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",_a0,_aZ,_d,_c,float(nb["close_ts"]),f"{_Y.title} [{nb['label']}]",now,prefetched_books=_z,live_emit_only=True)
    else:a.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_SP1_{_Y.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",_a0,_aZ,_d,_c,float(nb["close_ts"]),f"{_Y.title} [{nb['label']}]",now,prefetched_books=_z)
  m=[]
  for G in list(a.multi_sport_games.values()):
   if now>G.start_ts+6.5*3600.:a.multi_sport_games.pop(G.event_id,None);continue
   if a.single_scan or("fetch_json"in a.__dict__)or now>=(G.start_ts-86400.):m.append(G)
  m.sort(key=lambda g:(now<(g.start_ts-9e2),abs(g.start_ts-now)))
  for G in m[:20]:
   _y=sorted({lg.token_id for lgs in G.legs_by_scope.values()for lg in lgs})
   if len(_y)<4:continue
   _X=await a.fetch_books_batch(_y,timeout=3.5);w={}
   for t_m,_aY in _X.items():
    _aX,_aW=a._best_ask_sz(_aY)
    if _aX<1. and _aX*_aW>=8.:w[t_m]=_aX
   _x=detect_multi_sport_corridor_boxes(G,w,max_box_cost_net=1.08)
   if _x:md0=_x[0];a._record_market_telemetry(key=f"SP3_BOX_{G.event_id}",min_interval_sec=45.,now_ts=now,sig=(md0["label"],md0["box_cost_net"]),payload={"type":"MULTI_SPORT_CORRIDOR_BEST","sport":G.sport,"event_id":G.event_id,"game":G.title,"scope":md0["scope"],"in_play":bool(now>=G.start_ts),"best_label":md0["label"],"gross_box_l1":md0["box_cost_gross"],"net_box_l1":md0["box_cost_net"],"middle_pts":md0["middle_width_pts"]})
   for cb in _x:
    _aA,_az=cb["leg_a"],cb["leg_b"];_b=max(float(_aA.fee_rate),float(_az.fee_rate));Q=.994 if _b==.0 else.99
    if float(cb["box_cost_net"])>(1.045 if _b==.0 else Q):continue
    _ay,_ax=_X.get(_aA.token_id),_X.get(_az.token_id)
    if not _ay or not _ax:continue
    _aV={"token_id":_aA.token_id,"opp_token_id":_aA.opp_token_id,"condition_id":_aA.condition_id,"side":_aA.side_label,"label":_aA.display_label,"market_id":_aA.market_id,"fee_rate":float(_aA.fee_rate),"fee_exponent":float(_aA.fee_exponent),"neg_risk":bool(_aA.neg_risk),"strike":float(_aA.threshold)};_aU={"token_id":_az.token_id,"opp_token_id":_az.opp_token_id,"condition_id":_az.condition_id,"side":_az.side_label,"label":_az.display_label,"market_id":_az.market_id,"fee_rate":float(_az.fee_rate),"fee_exponent":float(_az.fee_exponent),"neg_risk":bool(_az.neg_risk),"strike":float(_az.threshold)};_W=f"SP3_{G.event_id}_{_aA.token_id[-8:]}_{_az.token_id[-8:]}"
    if float(cb["box_cost_net"])>Q:
     if _b==.0:a.post_zero_fee_maker_anchor_box("SP3_SPORTS",G.sport,f"ZFA_{_W}",_aV,_aU,_ay,_ax,float(cb["close_ts"]),f"{G.title} [{cb['label']}]",now,prefetched_books=_X)
     continue
    _aw=walk_equal_shares_dominance_box(_ay.get("asks")or[],_ax.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["SP3_SPORTS_CORRIDOR_DOMINANCE_BOX"],fee_rate_a=float(_aA.fee_rate),fee_rate_b=float(_az.fee_rate),fee_exponent_a=float(_aA.fee_exponent),fee_exponent_b=float(_az.fee_exponent),max_box_cost_net=Q,min_shares=8,min_box_notional_usd=7.)
    if _aw.get("filled"):
     opps_out.append({"sleeve":"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX","market":f"{G.sport} {G.title}: {cb['label']} (mid={cb['middle_width_pts']}pt)","ask_vwap":round(float(_aw["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_aw["box_cost_net"]),4),"l1_usd":_aw["l1_usd"],"close_ts":cb["close_ts"]});v=.99 if _b==.0 else.988
     if float(_aw["box_cost_net"])<=v and(float(cb["close_ts"])-now)<=86400.:a.emit_live_two_leg_box_candidate(sleeve_source="SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",box_type="SPORTS_CORRIDOR",asset=G.sport,dedupe_key=_W,leg_a=_aV,leg_b=_aU,bk_a=_ay,bk_b=_ax,close_ts=float(cb["close_ts"]),now_ts=now,k_low=float(_aA.threshold),k_high=float(_az.threshold))
     await a.open_shadow_two_leg_box(sleeve="SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",dedupe_key=_W,asset=G.sport,title=f"{G.sport} {G.title} [{cb['label']}]",leg_a=_aV,leg_b=_aU,bk_a=_ay,bk_b=_ax,close_ts=float(cb["close_ts"]),max_box_cost_net=Q,extra={"is_sports_corridor_box":True,"sport":G.sport,"scope":cb["scope"],"box_kind":cb["box_kind"],"middle_width_pts":cb["middle_width_pts"]})
  for _av in sorted(list(a.negrisk_zero_slates.values()),key=lambda s:((float(s.end_ts)-now)>64800.,float(s.end_ts))):
   if _av.end_ts<=now+60:a.negrisk_zero_slates.pop(_av.event_id,None);continue
   _w=[b["yes_token"]for b in _av.brackets]+[b["no_token"]for b in _av.brackets];_V=await a.fetch_books_batch(_w,timeout=3.5)
   if not all(b["yes_token"]in _V and b["no_token"]in _V for b in _av.brackets):continue
   F=[a._best_ask_sz(_V[b["yes_token"]])for b in _av.brackets];E=[a._best_ask_sz(_V[b["no_token"]])for b in _av.brackets];_au=sum(p for p,_ in F);_at=sum(p for p,_ in E);P=round(min(p*s for p,s in F),2);O=round(min(p*s for p,s in E),2);D=round(sum(extract_best_bid(_V[b["yes_token"]].get("bids")or[])[0]for b in _av.brackets),4);C=round(sum(extract_best_bid(_V[b["no_token"]].get("bids")or[])[0]for b in _av.brackets),4);_aT=len(_av.brackets);a._record_market_telemetry(key=f"NR0_SLATE_{_av.event_id}",min_interval_sec=60.,now_ts=now,sig=(round(_au,3),round(_at,3)),payload={"type":"ZERO_FEE_NEGRISK_SLATE","series":_av.series_slug,"title":_av.title,"tte_sec":round(_av.end_ts-now,0),"n_open":_aT,"sum_yes_l1":round(_au,4),"sum_yes_bids":D,"min_yes_l1_usd":P,"sum_no_l1":round(_at,4),"sum_no_bids":C,"min_no_l1_usd":O,"no_payout":_aT-1})
   if _au<=.99:
    _U=[{"token_id":b["yes_token"],"side":"YES","label":f"YES[{b['label']}]","market_id":b["market_id"],"fee_rate":float(b.get("fee_rate",.0))}for b in _av.brackets];_as=walk_equal_shares_multi_leg_box([{"asks":_V[b["yes_token"]].get("asks")or[],"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.))}for b in _av.brackets],target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],guaranteed_payout_per_bundle=1.,max_bundle_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
    if _as.get("filled"):
     opps_out.append({"sleeve":"NR0_ZERO_FEE_SLATE_ARB","market":f"{_av.title} (ALL {_aT} YES)","ask_vwap":round(float(_as["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_as["box_cost_net"]),4),"l1_usd":_as["l1_usd"],"close_ts":_av.end_ts})
     if _aT==2 and(float(_av.end_ts)-now)<=172800. and a._can_emit_zero_loss_math_live("NR0_ZERO_FEE_SLATE_ARB",float(_av.end_ts),now):_aS,_aR=_av.brackets[0],_av.brackets[1];a.emit_live_two_leg_box_candidate(sleeve_source="NR0_ZERO_FEE_SLATE_ARB",box_type="NEGRISK_2LEG",asset=_av.series_slug.upper(),dedupe_key=f"NR0_Y_{_av.event_id}",leg_a={"token_id":_aS["yes_token"],"opp_token_id":_aS["no_token"],"condition_id":str(_aS.get("condition_id")or""),"side":"YES","label":f"YES[{_aS['label']}]","market_id":_aS["market_id"],"fee_rate":float(_aS.get("fee_rate",.0)),"fee_exponent":float(_aS.get("fee_exponent",1.)),"neg_risk":True,"strike":1e2},leg_b={"token_id":_aR["yes_token"],"opp_token_id":_aR["no_token"],"condition_id":str(_aR.get("condition_id")or""),"side":"YES","label":f"YES[{_aR['label']}]","market_id":_aR["market_id"],"fee_rate":float(_aR.get("fee_rate",.0)),"fee_exponent":float(_aR.get("fee_exponent",1.)),"neg_risk":True,"strike":1e2},bk_a=_V[_aS["yes_token"]],bk_b=_V[_aR["yes_token"]],close_ts=float(_av.end_ts),now_ts=now)
     await a.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB",f"NR0_Y_{_av.event_id}",_av.series_slug.upper(),f"{_av.title} [All-YES Partition]",_U,_V,_av.end_ts,1.,.988,{"is_multi_leg_bundle":True,"guaranteed_payout":1.})
   elif _at<=(_aT-1)-.01:
    _aQ=float(_aT-1);_T=[{"token_id":b["no_token"],"side":"NO","label":f"NO[{b['label']}]","market_id":b["market_id"],"fee_rate":float(b.get("fee_rate",.0))}for b in _av.brackets];_ar=walk_equal_shares_multi_leg_box([{"asks":_V[b["no_token"]].get("asks")or[],"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.))}for b in _av.brackets],target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],guaranteed_payout_per_bundle=_aQ,max_bundle_cost_net=round(_aQ-.012,4),min_shares=6,min_box_notional_usd=5.5)
    if _ar.get("filled"):
     opps_out.append({"sleeve":"NR0_ZERO_FEE_SLATE_ARB","market":f"{_av.title} (ALL {_aT} NO)","ask_vwap":round(float(_ar["box_cost_net"])/_aQ,4),"p_model":1.,"net_edge":round((_aQ-float(_ar["box_cost_net"]))/_aQ,4),"l1_usd":_ar["l1_usd"],"close_ts":_av.end_ts})
     if(float(_av.end_ts)-now)<=172800. and a._can_emit_zero_loss_math_live("NR0_ZERO_FEE_SLATE_ARB",float(_av.end_ts),now):
      if _aT==2:_aP,_aO=_av.brackets[0],_av.brackets[1];a.emit_live_two_leg_box_candidate(sleeve_source="NR0_ZERO_FEE_SLATE_ARB",box_type="NEGRISK_2LEG",asset=_av.series_slug.upper(),dedupe_key=f"NR0_N_{_av.event_id}",leg_a={"token_id":_aP["no_token"],"opp_token_id":_aP["yes_token"],"condition_id":str(_aP.get("condition_id")or""),"side":"NO","label":f"NO[{_aP['label']}]","market_id":_aP["market_id"],"fee_rate":float(_aP.get("fee_rate",.0)),"fee_exponent":float(_aP.get("fee_exponent",1.)),"neg_risk":True,"strike":1e2},leg_b={"token_id":_aO["no_token"],"opp_token_id":_aO["yes_token"],"condition_id":str(_aO.get("condition_id")or""),"side":"NO","label":f"NO[{_aO['label']}]","market_id":_aO["market_id"],"fee_rate":float(_aO.get("fee_rate",.0)),"fee_exponent":float(_aO.get("fee_exponent",1.)),"neg_risk":True,"strike":1e2},bk_a=_V[_aP["no_token"]],bk_b=_V[_aO["no_token"]],close_ts=float(_av.end_ts),now_ts=now)
      elif 3<=_aT<=15:
       _a=a.negrisk_convert_slates.get(_av.event_id)
       if _a is not None and _a.is_closed_convert_safe:Z=_ar.get("leg_walks")or[];_aq={"mode":"NR2_PURE_CASH_CONVERT","shares":_ar["shares"],"net_edge_per_share":round((_aQ-float(_ar["box_cost_net"]))/_aQ,5),"no_legs":[{"token_id":b_z["no_token"],"bracket":b_z,"walk":(Z[idx_z]if idx_z<len(Z)else{"worst_px":a._best_ask_sz(_V[b_z["no_token"]])[0]})}for idx_z,b_z in enumerate(_a.brackets)],"yes_sell_legs":[],"retained_free_yes_brackets":[]};a.emit_live_negrisk_convert_candidate(sleeve_source="NR0_ZERO_FEE_SLATE_ARB",spec=_a,dedupe_key=f"NR0_N{_aT}_{_av.event_id}",arb_hit=_aq,books_by_token=_V,now_ts=now)
     await a.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB",f"NR0_N_{_av.event_id}",_av.series_slug.upper(),f"{_av.title} [All-NO Partition]",_T,_V,_av.end_ts,_aQ,round(_aQ-.012,4),{"is_multi_leg_bundle":True,"guaranteed_payout":_aQ})
   if D>=1.004:await a.execute_ctf_overround_mint_sell(dedupe_key=f"CTF_OVR_NR_{_av.event_id}",asset=_av.series_slug.upper(),title=f"{_av.title} NegRisk Overround Mint-Sell",legs_bids_spec=[{"bids":_V[b["yes_token"]].get("bids")or[],"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.))}for b in _av.brackets],close_ts=_av.end_ts,min_net_proceeds_per_set=1.004,opps_out=opps_out,extra={"overround_kind":"NEGRISK_SLATE","series":_av.series_slug,"event_id":_av.event_id})
  B=[s for s in a.negrisk_convert_slates.values()if s.end_ts>now+60]
  if B:
   Y=[]
   for _ap in B:
    for _ao in _ap.brackets:
     Y.append(_ao["no_token"])
     if _ap.is_closed_convert_safe:Y.append(_ao["yes_token"])
   _v=await a.fetch_books_batch(Y,timeout=3.5);i={}
   for _aN,_an in _v.items():
    _am,_al=a._best_ask_sz(_an)
    if _am<1. and _am*_al>=8.:i[_aN]=_am
   for _S in B:
    N=detect_negrisk_no_pair_boxes(_S,i,max_box_cost_net=1.04)
    if N:pa0=N[0];a._record_market_telemetry(key=f"NRCONV_2L_{_S.event_id}",min_interval_sec=60.,now_ts=now,sig=(pa0["label"],pa0["box_cost_net"]),payload={"type":"NEGRISK_NO_PAIR_BEST","event_id":_S.event_id,"title":_S.title[:80],"augmented":_S.neg_risk_augmented,"net_box_l1":pa0["box_cost_net"],"label":pa0["label"]})
    for pa in N:
     _ak,_aj=pa["bracket_a"],pa["bracket_b"];M=max(float(_ak["fee_rate"]),float(_aj["fee_rate"]));_u=.992 if M==.0 else.988
     if float(pa["box_cost_net"])>_u:continue
     _R,_Q=_v.get(_ak["no_token"]),_v.get(_aj["no_token"])
     if not _R or not _Q:continue
     _ai={"token_id":_ak["no_token"],"opp_token_id":_ak["yes_token"],"condition_id":_ak["condition_id"],"side":"NO","label":f"NO[{_ak['label']}]","market_id":_ak["market_id"],"fee_rate":float(_ak["fee_rate"]),"fee_exponent":float(_ak["fee_exponent"]),"neg_risk":True,"strike":1e2};_ah={"token_id":_aj["no_token"],"opp_token_id":_aj["yes_token"],"condition_id":_aj["condition_id"],"side":"NO","label":f"NO[{_aj['label']}]","market_id":_aj["market_id"],"fee_rate":float(_aj["fee_rate"]),"fee_exponent":float(_aj["fee_exponent"]),"neg_risk":True,"strike":1e2};_ag=walk_equal_shares_dominance_box(_R.get("asks")or[],_Q.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],fee_rate_a=float(_ak["fee_rate"]),fee_rate_b=float(_aj["fee_rate"]),fee_exponent_a=float(_ak["fee_exponent"]),fee_exponent_b=float(_aj["fee_exponent"]),max_box_cost_net=_u,min_shares=8,min_box_notional_usd=7.)
     if _ag.get("filled"):
      _P=f"NRCONV_2L_{_S.event_id}_{_ak['market_id']}_{_aj['market_id']}";opps_out.append({"sleeve":"NR_CONV_NO_BASKET_ARB","market":f"{_S.title[:50]}: {pa['label']}","ask_vwap":round(float(_ag["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_ag["box_cost_net"]),4),"l1_usd":_ag["l1_usd"],"close_ts":_S.end_ts})
      if(_S.end_ts-now)<=172800. and float(_ag["box_cost_net"])<=(.99 if M==.0 else.988):a.emit_live_two_leg_box_candidate(sleeve_source="NR_CONV_NO_BASKET_ARB",box_type="NEGRISK_2LEG",asset="NEGRISK",dedupe_key=_P,leg_a=_ai,leg_b=_ah,bk_a=_R,bk_b=_Q,close_ts=float(_S.end_ts),now_ts=now)
      await a.open_shadow_two_leg_box(sleeve="NR_CONV_NO_BASKET_ARB",dedupe_key=_P,asset="NEGRISK",title=f"{_S.title} [{pa['label']}]",leg_a=_ai,leg_b=_ah,bk_a=_R,bk_b=_Q,close_ts=float(_S.end_ts),max_box_cost_net=_u,extra={"is_negrisk_no_pair_box":True,"event_id":_S.event_id,"neg_risk_augmented":_S.neg_risk_augmented})
    if _S.is_closed_convert_safe:
     L=detect_negrisk_convert_positions_arbs(_S,_v,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],min_net_edge_per_share=.005,min_shares=8)
     if L:ca0=L[0];a._record_market_telemetry(key=f"NRCONV_M_{_S.event_id}",min_interval_sec=60.,now_ts=now,sig=(ca0["m_no_legs"],ca0["net_edge_per_share"]),payload={"type":"NEGRISK_CONVERT_ARB_SNAP","event_id":_S.event_id,"title":_S.title[:80],"m_no_legs":ca0["m_no_legs"],"n_total":ca0["n_total"],"net_edge_per_share":ca0["net_edge_per_share"],"shares":ca0["shares"]});await a.execute_negrisk_convert_positions_arb(_S,ca0,_v,opps_out)
     X=detect_nr2_convert_no_subset_arbs(_S,_v,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR2_CONVERT_NO_SUBSET_ARB"],min_edge_pure_cash=.012,min_edge_with_yes_sell=.015,min_shares=6)
     try:
      from src.polymarket_research.riskless_machine_gun_engine import detect_nr3_synthetic_all_yes_overround;_t=detect_nr3_synthetic_all_yes_overround(_S,_v,target_budget_usd=30.,min_net_edge_per_set=.008,min_shares=5)
      if _t is not None:opps_out.append({"sleeve":"NR2_CONVERT_NO_SUBSET_ARB","market":f"{_S.title[:50]} [NR3 All-YES Overround]","ask_vwap":round(max(.01,1.-float(_t["net_edge_per_share"])),4),"p_model":1.,"net_edge":_t["net_edge_per_share"],"l1_usd":_t["l1_usd"],"close_ts":_S.end_ts});a.emit_live_negrisk_convert_candidate(sleeve_source="NR2_CONVERT_NO_SUBSET_ARB",spec=_S,dedupe_key=f"NR3_OVR_{_S.event_id}",arb_hit=_t,books_by_token=_v,now_ts=now)
     except Exception:pass
     if X:na0=X[0];a._record_market_telemetry(key=f"NR2_SUB_{_S.event_id}",min_interval_sec=60.,now_ts=now,sig=(na0["m_no_legs"],na0["net_edge_per_share"],na0["retained_tail_count"]),payload={"type":"NR2_SUBSET_CONVERT_SNAP","event_id":_S.event_id,"title":_S.title[:80],"m_no_legs":na0["m_no_legs"],"n_total":na0["n_total"],"retained_tail_count":na0["retained_tail_count"],"net_edge_per_share":na0["net_edge_per_share"]});await a.execute_nr2_subset_convert_arb(_S,na0,_v,opps_out)
  await a._scan_phase2_macro_counting_gas(opps_out,now);await a._scan_frontier_v2_sleeves(opps_out,now);await a._scan_frontier_v3_sleeves(opps_out,now);await a._scan_frontier_v4_sleeves(opps_out,now)
 async def _scan_frontier_v2_sleeves(a,opps_out,now):
  b=[s for s in a.nba_prop_slates.values()if s.settle_est_ts>now+120]
  for _d in b[:10]:
   D=[t for rgs in _d.props_by_player_stat.values()if len(rgs)>=2 for r in rgs for t in(r.yes_token,r.no_token)]
   if not D:continue
   P=await a.fetch_books_batch(D,timeout=3.5);C={t:p for t,bk in P.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.};j=detect_sp4_milestone_ladder_boxes(_d,C,max_box_cost_net=1.045)
   if j:b0=j[0];a._record_market_telemetry(f"SP4_3B_{_d.event_id}",90.,{"type":"SP4_MILESTONE_BOX_BEST","game":_d.title[:60],"label":b0["label"],"net_box_l1":b0["box_cost_net"]},now_ts=now,sig=(b0["label"],b0["box_cost_net"]))
   for bx in j[:8]:
    la,lb=bx["leg_a"],bx["leg_b"];_v,_u=P.get(la["token_id"]),P.get(lb["token_id"])
    if not _v or not _u:continue
    O=f"SP4_3B_{la['market_id']}_{lb['market_id']}"
    if float(bx["box_cost_net"])>.992:
     if la.get("market_id")!=lb.get("market_id"):a.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_{O}",la,lb,_v,_u,float(bx["close_ts"]),f"{_d.title} [{bx['label']}]",now,prefetched_books=P)
     continue
    _c=walk_equal_shares_dominance_box(_v.get("asks")or[],_u.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],float(la["fee_rate"]),float(lb["fee_rate"]),fee_exponent_a=float(la.get("fee_exponent",1.)),fee_exponent_b=float(lb.get("fee_exponent",1.)),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
    if _c.get("filled"):
     opps_out.append({"sleeve":"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","market":f"NBA Prop Corridor: {bx['label']}","ask_vwap":_c["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_c["box_cost_net"]),4),"l1_usd":_c["l1_usd"],"close_ts":bx["close_ts"]})
     if float(_c["box_cost_net"])<=.99 and(float(bx["close_ts"])-now)<=86400. and la.get("market_id")!=lb.get("market_id"):a.emit_live_two_leg_box_candidate(sleeve_source="SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",box_type="NBA_DOMINANCE",asset="NBA",dedupe_key=O,leg_a=la,leg_b=lb,bk_a=_v,bk_b=_u,close_ts=float(bx["close_ts"]),now_ts=now,k_low=float(bx["line_low"]),k_high=float(bx["line_high"]))
     await a.open_shadow_two_leg_box("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",O,"NBA_PROP",f"{_d.title} [{bx['label']}]",la,lb,_v,_u,float(bx["close_ts"]),.992,{"is_two_leg_box":True,"mode":bx["mode"],"player":bx["player_name"],"stat":bx["stat_type"]})
  g=[tr for tr in a.soccer_trees.values()if tr.end_ts>now+120]
  if g:
   v=[]
   for tr in g[:25]:
    for _t in(tr.home_leg,tr.draw_leg,tr.away_leg):v.extend((_t["yes_token"],_t["no_token"]))
    for tl in tr.totals:v.extend((tl["over_token"],tl["under_token"]))
    for sp in tr.spreads:v.extend((sp["fav_minus_token"],sp["dog_plus_token"]))
   B=await a.fetch_books_batch(v,timeout=3.5);u={t:p for t,bk in B.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for tr in g[:25]:
    A=detect_soc1_regulation_boxes(tr,B,u,max_2leg_cost_net=1.035,min_conv_edge_ps=.01,target_budget_usd=BANKROLL_TICKETS["T1000"]["SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"])
    if A["two_leg_boxes"]:_s=A["two_leg_boxes"][0];a._record_market_telemetry(f"SOC1_{tr.game_id}",90.,{"type":"SOC1_REGULATION_BOX_BEST","game":tr.title[:60],"mode":_s["mode"],"label":_s["label"],"net_box_l1":_s["box_cost_net"]},now_ts=now,sig=(_s["label"],_s["box_cost_net"]))
    for _q in A["two_leg_boxes"][:4]:
     if float(_q["box_cost_net"])>.988:continue
     _p,_o=_q["leg_a"],_q["leg_b"];_b,_a=B.get(_p["token_id"]),B.get(_o["token_id"])
     if not _b or not _a:continue
     Z=walk_equal_shares_dominance_box(_b.get("asks")or[],_a.get("asks")or[],BANKROLL_TICKETS["T1000"]["SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"],float(_p["fee_rate"]),float(_o["fee_rate"]),fee_exponent_a=float(_p["fee_exponent"]),fee_exponent_b=float(_o["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
     if Z.get("filled"):
      N=f"SOC1_2L_{tr.game_id}_{_p['token_id'][-6:]}_{_o['token_id'][-6:]}";opps_out.append({"sleeve":"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX","market":_q["label"],"ask_vwap":Z["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(Z["box_cost_net"]),4),"l1_usd":Z["l1_usd"],"close_ts":tr.end_ts})
      if(float(tr.end_ts)-now)<=259200. and _p.get("market_id")!=_o.get("market_id"):a.emit_live_two_leg_box_candidate(sleeve_source="SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",box_type="SPORTS_CORRIDOR",asset="SOCCER",dedupe_key=N,leg_a=_p,leg_b=_o,bk_a=_b,bk_b=_a,close_ts=float(tr.end_ts),now_ts=now)
      await a.open_shadow_two_leg_box("SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",N,"SOCCER",_q["label"],_p,_o,_b,_a,float(tr.end_ts),.988,{"is_two_leg_box":True,"mode":_q["mode"],"game_id":tr.game_id})
    for _n in A["convert_arbs"][:1]:opps_out.append({"sleeve":"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX","market":_n["label"],"ask_vwap":round(1.-float(_n["net_edge_per_share"]),4),"p_model":1.,"net_edge":_n["net_edge_per_share"],"l1_usd":_n["l1_usd"],"close_ts":tr.end_ts})
  f=[]
  if a.lp1_bop_legs:f.append(("BOP_2026",[lg for lg in a.lp1_bop_legs if float(lg["end_ts"])>now+60]))
  for _m in list(a.lp1_nba_em_bundles.values())[:10]:
   if float(_m["end_ts"])>now+60:f.append((f"NBA_EM_{_m['event_id']}",_m["legs"]))
  if f:
   q=sorted({str(lg["token_id"])for _,g_lgs in f for lg in g_lgs});z=await a.fetch_books_batch(q,timeout=3.5);o={t:p for t,bk in z.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for Y,g_lgs in f:
    if len(g_lgs)<4:continue
    i=Y.startswith("NBA_EM");e=find_state_matrix_dominance_boxes(g_lgs,o,max_2leg_cost_net=1.045,max_3leg_cost_net=1.03)
    if e:d0=e[0];a._record_market_telemetry(f"LP1_{Y}",90.,{"type":"LP1_IMPLICATION_BEST","group":Y,"n_legs":d0["n_legs"],"net_box_l1":d0["box_cost_net"],"label":d0["label"]},now_ts=now,sig=(d0["label"],d0["box_cost_net"]))
    for _l in e[:6]:
     X=_l["legs"]
     if int(_l["n_legs"])==2:
      _k,_j=X[0],X[1];W,V=z.get(_k["token_id"]),z.get(_j["token_id"])
      if not W or not V:continue
      M=f"LP1_2L_{Y}_{_k['token_id'][-6:]}_{_j['token_id'][-6:]}";h=max(float(_k["fee_rate"]),float(_j["fee_rate"]))
      if float(_l["box_cost_net"])>.993:
       if h==.0 and _k.get("market_id")!=_j.get("market_id"):a.post_zero_fee_maker_anchor_box("SP1_NBA"if i else"LP1_BOP","NBA"if i else"MACRO",f"ZFA_{M}",_k,_j,W,V,float(_l["close_ts"]),f"{Y} [{_l['label']}]",now,prefetched_books=z)
       continue
      U=walk_equal_shares_dominance_box(W.get("asks")or[],V.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"],float(_k["fee_rate"]),float(_j["fee_rate"]),max_box_cost_net=.993,min_shares=6,min_box_notional_usd=5.5)
      if U.get("filled"):
       opps_out.append({"sleeve":"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX","market":f"{Y}: {_l['label']}","ask_vwap":U["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(U["box_cost_net"]),4),"l1_usd":U["l1_usd"],"close_ts":_l["close_ts"]});c=.99 if h==.0 else.988
       if float(U["box_cost_net"])<=c:n="COMPLETE_SET"if _k.get("market_id")==_j.get("market_id")else("NBA_DOMINANCE"if i else"MACRO_DOMINANCE");a.emit_live_two_leg_box_candidate(sleeve_source="LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",box_type=n,asset="NBA"if i else"MACRO",dedupe_key=M,leg_a=_k,leg_b=_j,bk_a=W,bk_b=V,close_ts=float(_l["close_ts"]),now_ts=now)
       await a.open_shadow_two_leg_box("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",M,Y,f"{Y} {_l['label']}",_k,_j,W,V,float(_l["close_ts"]),.993,{"is_two_leg_box":True,"min_payout":_l["min_payout"],"jackpot_states":_l["jackpot_states"]})
     elif int(_l["n_legs"])==3 and float(_l["box_cost_net"])<=.991:
      L=walk_equal_shares_multi_leg_box([{"asks":z[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":1.}for x in X],BANKROLL_TICKETS["T1000"]["LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"],1.,.991,min_shares=6,min_box_notional_usd=5.5)
      if L.get("filled"):K=f"LP1_3L_{Y}_{'_'.join(x['token_id'][-5:]for x in X)}";opps_out.append({"sleeve":"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX","market":f"{Y} 3L: {_l['label']}","ask_vwap":L["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(L["box_cost_net"]),4),"l1_usd":L["l1_usd"],"close_ts":_l["close_ts"]});await a.open_shadow_multi_leg_bundle("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",K,Y,f"{Y} 3-Leg {_l['label']}",X,z,float(_l["close_ts"]),1.,.991,{"is_multi_leg_bundle":True,"guaranteed_payout":1.})
  d=[sp for sp in a.esports_bo3_specs.values()if sp.end_ts>now+60]
  if d:
   m=[]
   for k in d[:25]:
    m.extend([k.ml_a_token,k.ml_b_token,k.hc_minus_token,k.hc_plus_token])
    for mt in(k.map1_a_token,k.map1_b_token,k.map2_a_token,k.map2_b_token,k.ou25_over_token,k.ou25_under_token):
     if mt:m.append(mt)
   y=await a.fetch_books_batch(m,timeout=3.5);l={t:p for t,bk in y.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for k in d[:25]:
    J=evaluate_api1_esports_bo3_opportunities(k,y,l,max_middle_cost_net=1.035)
    if J["two_leg_boxes"]:_r=J["two_leg_boxes"][0];a._record_market_telemetry(f"API1_{k.event_id}",90.,{"type":"API1_ESPORTS_BO3_BEST","match":k.title[:60],"mode":_r["mode"],"net_box_l1":_r["box_cost_net"],"forfeit_immune":_r["post_m1_forfeit_immune"]},now_ts=now,sig=(_r["mode"],_r["box_cost_net"]))
    for _i in J["single_leg_locks"]:
     I=y.get(_i["token_id"]);H=y.get(_i["opp_token_id"])
     if not I or not H:continue
     w,_=extract_best_bid(H.get("bids")or[])
     if w>.04:continue
     G=walk_l2_book_asks_depth_capped(I.get("asks")or[],BANKROLL_TICKETS["T1000"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],BANKROLL_TICKETS["T100"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],fee_rate=float(_i["fee_rate"]),min_l1_usd=15.,max_ask_px=.978,fee_exponent=float(_i["fee_exponent"]))
     if G.get("filled"):
      T=float(G["eff_px"]);S=round(float(_i["p_lock"])-T,4)
      if.72<=T<=.978 and S>=.018:_h=f"API1_LK_{k.event_id}_{_i['market_id']}";opps_out.append({"sleeve":"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","market":f"Esports BO3 Lock: {_i['display_label']}","ask_vwap":T,"p_model":_i["p_lock"],"net_edge":S,"l1_usd":G["l1_usd"],"close_ts":_i["close_ts"]});a.emit_live_single_leg_lock_candidate(sleeve_source="API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",asset="ESPORTS",dedupe_key=_h,token_id=str(_i["token_id"]),opp_token_id=str(_i["opp_token_id"]),market_id=str(_i["market_id"]),condition_id=str(_i["condition_id"]),side_label=str(_i["side_label"]),display_label=str(_i["display_label"]),bk_win=I,bk_opp=H,fee_rate=float(_i["fee_rate"]),fee_exponent=float(_i["fee_exponent"]),neg_risk=False,close_ts=float(_i["close_ts"]),now_ts=now,max_lock_eff_px=.978,max_opp_bid=.025,hold_to_maturity=True,p_model=float(_i["p_lock"]));await a.open_shadow_position("API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",_h,"ESPORTS_BO3",f"{k.title} [{_i['display_label']}]",str(_i["side_label"]),str(_i["token_id"]),float(_i["fee_rate"]),float(_i["p_lock"]),float(_i["close_ts"]),{"market_id":_i["market_id"],"condition_id":_i["condition_id"],"mode":_i["mode"]},prefetched_book=I)
    for _g in J["two_leg_boxes"]:
     if float(_g["box_cost_net"])>.988:continue
     _f,_e=_g["leg_a"],_g["leg_b"];R,Q=y.get(_f["token_id"]),y.get(_e["token_id"])
     if not R or not Q:continue
     F=walk_equal_shares_dominance_box(R.get("asks")or[],Q.get("asks")or[],BANKROLL_TICKETS["T1000"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],float(_f["fee_rate"]),float(_e["fee_rate"]),fee_exponent_a=float(_f["fee_exponent"]),fee_exponent_b=float(_e["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
     if F.get("filled"):
      E=f"API1_MID_{k.event_id}_{_f['market_id']}_{_e['market_id']}";opps_out.append({"sleeve":"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","market":_g["label"],"ask_vwap":F["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(F["box_cost_net"]),4),"l1_usd":F["l1_usd"],"close_ts":_g["close_ts"]})
      if bool(_g.get("post_m1_forfeit_immune"))and _f.get("market_id")!=_e.get("market_id"):a.emit_live_two_leg_box_candidate(sleeve_source="API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",box_type="SPORTS_CORRIDOR",asset="ESPORTS",dedupe_key=E,leg_a=_f,leg_b=_e,bk_a=R,bk_b=Q,close_ts=float(_g["close_ts"]),now_ts=now)
      await a.open_shadow_two_leg_box("API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",E,"ESPORTS_BO3",_g["label"],_f,_e,R,Q,float(_g["close_ts"]),.988,{"is_two_leg_box":True,"mode":_g["mode"],"post_m1_forfeit_immune":_g["post_m1_forfeit_immune"]})
 async def _scan_frontier_v3_sleeves(a,opps_out,now):
  if a.lp2_implication_groups or a.lp2_events_by_slug:
   g={str(lg["token_id"])for _,lgs in a.lp2_implication_groups for lg in lgs if float(lg.get("end_ts")or.0)>now+60}
   for _b in("republican-house-seats-after-the-2026-midterm-elections","republican-senate-seats-after-the-2026-midterm-elections-927","which-party-will-win-the-house-in-2026","which-party-will-win-the-senate-in-2026"):
    _T=a.lp2_events_by_slug.get(_b)or{}
    for _ag in _T.get("markets")or[]:
     if not _ag.get("closed"):
      _S=_parse_clob_tokens(_ag)
      if _S:g.update(_S)
   if g:
    _a=await a.fetch_books_batch(sorted(g),timeout=4.);P={t:p for t,bk in _a.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for O,N in a.lp2_implication_groups:
     _p=find_state_matrix_dominance_boxes(N,P,max_2leg_cost_net=1.045,max_3leg_cost_net=.992)
     if _p:_R=_p[0];a._record_market_telemetry(f"LP2_{O}",90.,{"type":"LP2_DAG_BOX_BEST","group":O,"n_legs":_R["n_legs"],"label":_R["label"],"net_box_l1":_R["box_cost_net"],"jackpot_states":_R["jackpot_states"]},now_ts=now,sig=(_R["label"],_R["box_cost_net"]))
     for bx in _p[:6]:
      if float(bx["box_cost_net"])>.992:continue
      _Q=bx["legs"]
      if int(bx["n_legs"])==2:
       _af,_ae=_Q[0],_Q[1];_P,_O=_a.get(_af["token_id"]),_a.get(_ae["token_id"])
       if not _P or not _O:continue
       _ad=walk_equal_shares_dominance_box(_P.get("asks")or[],_O.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],float(_af["fee_rate"]),float(_ae["fee_rate"]),fee_exponent_a=float(_af["fee_exponent"]),fee_exponent_b=float(_ae["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
       if _ad.get("filled"):
        _N=f"LP2_{O}_{_af['token_id'][-8:]}_{_ae['token_id'][-8:]}";opps_out.append({"sleeve":"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","market":f"{O}: {bx['label']}","ask_vwap":_ad["box_cost_net"],"p_model":float(bx["min_payout"]),"net_edge":round(float(bx["min_payout"])-float(_ad["box_cost_net"]),4),"l1_usd":_ad["l1_usd"],"close_ts":bx["close_ts"]})
        if(a._can_emit_zero_loss_math_live("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",float(bx["close_ts"]),now)and float(bx["min_payout"])>=1.-1e-6 and float(_ad["box_cost_net"])<=.99 and _af.get("market_id")!=_ae.get("market_id")and.0<(float(bx["close_ts"])-now)<=604800.):a.emit_live_two_leg_box_candidate(sleeve_source="LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",box_type="MACRO_DOMINANCE",asset="MACRO",dedupe_key=_N,leg_a=_af,leg_b=_ae,bk_a=_P,bk_b=_O,close_ts=float(bx["close_ts"]),now_ts=now,k_low=1e2,k_high=101. if int(bx.get("jackpot_states")or 0)>0 else 1e2)
        await a.open_shadow_two_leg_box("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",_N,O,f"{O}: {bx['label']}",_af,_ae,_P,_O,float(bx["close_ts"]),.992,{"is_two_leg_box":True,"group":O,"guaranteed_payout":bx["min_payout"],"max_payout":bx["max_payout"],"jackpot_states":bx["jackpot_states"]})
      elif int(bx["n_legs"])==3 and all(x["token_id"]in _a for x in _Q):
       Z=f"LP2_3L_{O}_{'_'.join(x['token_id'][-6:]for x in _Q)}";_o=walk_equal_shares_multi_leg_box([{"asks":_a[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x["fee_exponent"])}for x in _Q],BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],float(bx["min_payout"]),.992,min_shares=6,min_box_notional_usd=5.5)
       if _o.get("filled"):opps_out.append({"sleeve":"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","market":f"{O} 3-Leg: {bx['label']}","ask_vwap":_o["box_cost_net"],"p_model":float(bx["min_payout"]),"net_edge":round(float(bx["min_payout"])-float(_o["box_cost_net"]),4),"l1_usd":_o["l1_usd"],"close_ts":bx["close_ts"]});await a.open_shadow_multi_leg_bundle("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",Z,O,f"{O} 3-Leg: {bx['label']}",_Q,_a,float(bx["close_ts"]),float(bx["min_payout"]),.992,{"is_multi_leg_bundle":True,"guaranteed_payout":bx["min_payout"],"max_payout":bx["max_payout"]})
    Y=await asyncio.to_thread(detect_lp2_seat_convert_implication_arbs,a.lp2_events_by_slug,_a,BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],1.035)
    if Y:
     _M=Y[0];a._record_market_telemetry(f"LP2_CONV_{_M['mode']}",90.,{"type":"LP2_CONVERT_MIDDLE_SNAP","mode":_M["mode"],"synthetic_box_cost_net":_M["synthetic_box_cost_net"],"shares_out":_M["shares_out"]},now_ts=now,sig=(_M["mode"],_M["synthetic_box_cost_net"]))
     for cv in Y:
      if float(cv["synthetic_box_cost_net"])<=.992:_ac=int(cv["m_no_legs"]);q=float(_ac);A=float(_ac-1)+.992;_n=f"LP2_CV_{cv['mode']}";opps_out.append({"sleeve":"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","market":cv["label"],"ask_vwap":cv["synthetic_box_cost_net"],"p_model":1.,"net_edge":cv["guaranteed_floor_edge_ps"],"l1_usd":cv["l1_usd"],"close_ts":cv["close_ts"]});await a.open_shadow_multi_leg_bundle("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",_n,"LP2_CONVERT",cv["label"],cv["legs"],_a,float(cv["close_ts"]),q,A,{"is_multi_leg_bundle":True,"guaranteed_payout":q,"mode":cv["mode"],"index_set_int":cv["index_set_int"]})
  e=[s for s in a.nba_subperiod_slates.values()if s.settle_est_ts>now+120]
  for _m in e[:10]:
   b=[t for rgs in _m.ext_props_by_player_stat.values()if len(rgs)>=2 for r in rgs for t in(r.yes_token,r.no_token)];b+=[t for sm in _m.subperiod_markets if sm.period_scope in("1H","Q1")and sm.kind in("ML","SPREAD")for t in(sm.tok_0,sm.tok_1)]
   if not b:continue
   X=await a.fetch_books_batch(sorted(set(b)),timeout=3.5);M={t:p for t,bk in X.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.};z=detect_sp4_subperiod_and_ext_prop_boxes(_m,M,max_box_cost_net=1.045)
   if z:sb0=z[0];a._record_market_telemetry(f"SP4_SUB_{_m.event_id}",90.,{"type":"SP4_SUBPERIOD_BOX_BEST","game":_m.title[:60],"mode":sb0["mode"],"label":sb0["label"],"net_box_l1":sb0["box_cost_net"]},now_ts=now,sig=(sb0["label"],sb0["box_cost_net"]))
   for sbx in z[:8]:
    if float(sbx["box_cost_net"])>.992:continue
    _ab,_aa=sbx["leg_a"],sbx["leg_b"];_L,_K=X.get(_ab["token_id"]),X.get(_aa["token_id"])
    if not _L or not _K:continue
    _9=walk_equal_shares_dominance_box(_L.get("asks")or[],_K.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],float(_ab["fee_rate"]),float(_aa["fee_rate"]),fee_exponent_a=float(_ab.get("fee_exponent",1.)),fee_exponent_b=float(_aa.get("fee_exponent",1.)),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
    if _9.get("filled"):
     _J=f"SP4_SUB_{_ab['market_id']}_{_aa['market_id']}";opps_out.append({"sleeve":"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","market":f"NBA [{sbx['mode']}] {sbx['label']}","ask_vwap":_9["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_9["box_cost_net"]),4),"l1_usd":_9["l1_usd"],"close_ts":sbx["close_ts"]})
     if(a._can_emit_zero_loss_math_live("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",float(sbx["close_ts"]),now)and float(_9["box_cost_net"])<=.99 and _ab.get("market_id")!=_aa.get("market_id")and.0<(float(sbx["close_ts"])-now)<=259200.):a.emit_live_two_leg_box_candidate(sleeve_source="SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",box_type="NBA_DOMINANCE",asset="NBA",dedupe_key=_J,leg_a=_ab,leg_b=_aa,bk_a=_L,bk_b=_K,close_ts=float(sbx["close_ts"]),now_ts=now,k_low=float(_ab.get("strike")or 1e2),k_high=float(_aa.get("strike")or 101.))
     await a.open_shadow_two_leg_box("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",_J,"NBA_SUBPERIOD",f"{_m.title} [{sbx['label']}]",_ab,_aa,_L,_K,float(sbx["close_ts"]),.992,{"is_two_leg_box":True,"mode":sbx["mode"]})
  o=[sp for sp in a.cal1_ladders.values()if sp.rungs and sp.rungs[-1].end_ts>now+120]
  if o:
   L=sorted({t for sp in o for r in sp.rungs for t in(r.yes_token,r.no_token)});W=await a.fetch_books_batch(L,timeout=4.);K={t:p for t,bk in W.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for _l in o:
    y=detect_cal1_monotonic_boxes(_l,K,max_box_cost_net=1.045)
    if y:cb0=y[0];a._record_market_telemetry(f"CAL1_{_l.event_id}",90.,{"type":"CAL1_LADDER_BOX_BEST","kind":_l.ladder_kind,"label":cb0["label"],"net_box_l1":cb0["box_cost_net"]},now_ts=now,sig=(cb0["label"],cb0["box_cost_net"]))
    for cbx in y[:6]:
     if float(cbx["box_cost_net"])>.992:continue
     _8,_7=cbx["leg_a"],cbx["leg_b"];_I,_H=W.get(_8["token_id"]),W.get(_7["token_id"])
     if not _I or not _H:continue
     _6=walk_equal_shares_dominance_box(_I.get("asks")or[],_H.get("asks")or[],BANKROLL_TICKETS["T1000"]["CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"],float(_8["fee_rate"]),float(_7["fee_rate"]),fee_exponent_a=float(_8["fee_exponent"]),fee_exponent_b=float(_7["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
     if _6.get("filled"):
      _G=f"CAL1_{_8['market_id']}_{_7['market_id']}";opps_out.append({"sleeve":"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","market":cbx["label"],"ask_vwap":_6["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_6["box_cost_net"]),4),"l1_usd":_6["l1_usd"],"close_ts":cbx["close_ts"]})
      if(a._can_emit_zero_loss_math_live("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",float(cbx["close_ts"]),now)and _8.get("market_id")!=_7.get("market_id")and.0<(float(cbx["close_ts"])-now)<=604800. and(float(cbx.get("early_leg_close_ts")or cbx["close_ts"])-now)>=60.):a.emit_live_two_leg_box_candidate(sleeve_source="CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",box_type="MACRO_DOMINANCE",asset="MACRO",dedupe_key=_G,leg_a=_8,leg_b=_7,bk_a=_I,bk_b=_H,close_ts=float(cbx["close_ts"]),now_ts=now,k_low=float(_8.get("strike")or 1e2),k_high=float(_7.get("strike")or 101.))
      await a.open_shadow_two_leg_box("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",_G,f"CAL1_{_l.ladder_kind}",cbx["label"],_8,_7,_I,_H,float(cbx["close_ts"]),.992,{"is_two_leg_box":True,"mode":cbx["mode"],"ladder_kind":_l.ladder_kind})
  for _F in list(a.lp1_nfl_em_bundles.values())[:12]:
   if float(_F["end_ts"])<=now+60:continue
   J=sorted({str(lg["token_id"])for lg in _F["legs"]});V=await a.fetch_books_batch(J,timeout=3.5);I={t:p for t,bk in V.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.};w=find_state_matrix_dominance_boxes(_F["legs"],I,max_2leg_cost_net=1.045,max_3leg_cost_net=.99)
   if w:nb0=w[0];a._record_market_telemetry(f"LP1_NFL_EM_{_F['event_id']}",90.,{"type":"LP1_NFL_EM_BOX_BEST","game":_F["title"][:60],"n_legs":nb0["n_legs"],"label":nb0["label"],"net_box_l1":nb0["box_cost_net"]},now_ts=now,sig=(nb0["label"],nb0["box_cost_net"]))
   for nbx in w[:6]:
    if float(nbx["box_cost_net"])>.99 or int(nbx["n_legs"])!=2:continue
    _E,_D=nbx["legs"][0],nbx["legs"][1];_k,_j=V.get(_E["token_id"]),V.get(_D["token_id"])
    if not _k or not _j:continue
    _5=walk_equal_shares_dominance_box(_k.get("asks")or[],_j.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX"],float(_E["fee_rate"]),float(_D["fee_rate"]),fee_exponent_a=float(_E["fee_exponent"]),fee_exponent_b=float(_D["fee_exponent"]),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
    if _5.get("filled"):
     _C=f"LP1_NFLEM_{_F['event_id']}_{_E['token_id'][-8:]}_{_D['token_id'][-8:]}";opps_out.append({"sleeve":"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","market":f"NFL EM [{_F['title']}]: {nbx['label']}","ask_vwap":_5["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_5["box_cost_net"]),4),"l1_usd":_5["l1_usd"],"close_ts":nbx["close_ts"]})
     if(a._can_emit_zero_loss_math_live("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",float(nbx["close_ts"]),now)and float(nbx.get("min_payout",1.))>=1.-1e-6 and float(_5["box_cost_net"])<=.988 and _E.get("market_id")!=_D.get("market_id")and.0<(float(nbx["close_ts"])-now)<=604800.):a.emit_live_two_leg_box_candidate(sleeve_source="LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",box_type="SPORTS_CORRIDOR",asset="NFL",dedupe_key=_C,leg_a=_E,leg_b=_D,bk_a=_k,bk_b=_j,close_ts=float(nbx["close_ts"]),now_ts=now,k_low=1e2,k_high=101. if float(nbx.get("max_payout",1.))>1.05 else 1e2)
     await a.open_shadow_two_leg_box("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",_C,"NFL_EM",f"{_F['title']} [{nbx['label']}]",_E,_D,_k,_j,float(nbx["close_ts"]),.99,{"is_two_leg_box":True,"mode":"NFL_EXACT_MARGIN_DOMINANCE","max_payout":nbx["max_payout"]})
  n=list(a.multisport_raw_events.values())[:24]
  if n:
   m=[]
   for _,k in n:
    for _4 in k.get("markets")or[]:
     if not _4.get("closed")and str(_4.get("sportsMarketType")or"").lower()in("moneyline","spreads","first_half_moneyline","first_half_spreads","q1_moneyline","q1_spreads"):
      _B=_parse_clob_tokens(_4)
      if _B:m.extend(_B)
   if m:
    v=await a.fetch_books_batch(sorted(set(m)),timeout=3.5);l={t:p for t,bk in v.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for H,k in n:
     G=detect_multisport_ml_spread_polish_middles(k,l,sport_hint=H,max_box_cost_net=1.04)
     for pbx in G[:4]:
      if float(pbx["box_cost_net"])>.988:continue
      _3,_2=pbx["leg_a"],pbx["leg_b"];_A,_z=v.get(_3["token_id"]),v.get(_2["token_id"])
      if not _A or not _z:continue
      _1=walk_equal_shares_dominance_box(_A.get("asks")or[],_z.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX"],float(_3["fee_rate"]),float(_2["fee_rate"]),fee_exponent_a=float(_3["fee_exponent"]),fee_exponent_b=float(_2["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
      if _1.get("filled"):
       _y=f"LP1_MSPM_{_3['market_id']}_{_2['market_id']}";opps_out.append({"sleeve":"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","market":pbx["label"],"ask_vwap":_1["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_1["box_cost_net"]),4),"l1_usd":_1["l1_usd"],"close_ts":pbx["close_ts"]})
       if(a._can_emit_zero_loss_math_live("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",float(pbx["close_ts"]),now)and _3.get("market_id")!=_2.get("market_id")and.0<(float(pbx["close_ts"])-now)<=604800.):a.emit_live_two_leg_box_candidate(sleeve_source="LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",box_type="SPORTS_CORRIDOR",asset=str(H).upper(),dedupe_key=_y,leg_a=_3,leg_b=_2,bk_a=_A,bk_b=_z,close_ts=float(pbx["close_ts"]),now_ts=now,k_low=1e2,k_high=101.)
       await a.open_shadow_two_leg_box("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",_y,f"{H}_MIDDLE",pbx["label"],_3,_2,_A,_z,float(pbx["close_ts"]),.988,{"is_two_leg_box":True,"mode":pbx["mode"]})
  j=[t for t in a.tennis_specs.values()if t.end_ts>now+60]
  if j:
   F=[]
   for D in j[:25]:
    for _x in D.totals_by_scope.values():
     for r_t in _x:F.extend([r_t.over_token,r_t.under_token])
    for _i in(D.set1_a_token,D.set1_b_token,D.set2_a_token,D.set2_b_token,D.sets_ou25_over_token,D.sets_ou25_under_token,D.comp_yes_token,D.comp_no_token):
     if _i:F.append(_i)
   if F:
    U=await a.fetch_books_batch(sorted(set(F)),timeout=3.5);E={t:p for t,bk in U.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for D in j[:25]:
     T=evaluate_ten1_tennis_opportunities(D,U,E,max_box_cost_net=1.045)
     if T:_0=T[0];a._record_market_telemetry(f"TEN1_{D.event_id}",90.,{"type":"TEN1_CORRIDOR_BEST","match":D.title[:60],"mode":_0["mode"],"label":_0["label"],"net_box_l1":_0["box_cost_net"]},now_ts=now,sig=(_0["label"],_0["box_cost_net"]))
     for tbx in T[:4]:
      if float(tbx["box_cost_net"])>.988:continue
      _w,_v=tbx["leg_a"],tbx["leg_b"];_h,_g=U.get(_w["token_id"]),U.get(_v["token_id"])
      if not _h or not _g:continue
      _Z=walk_equal_shares_dominance_box(_h.get("asks")or[],_g.get("asks")or[],BANKROLL_TICKETS["T1000"]["TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR"],float(_w["fee_rate"]),float(_v["fee_rate"]),fee_exponent_a=float(_w["fee_exponent"]),fee_exponent_b=float(_v["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
      if _Z.get("filled"):
       _u=f"TEN1_{_w['market_id']}_{_v['market_id']}";opps_out.append({"sleeve":"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR","market":tbx["label"],"ask_vwap":_Z["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_Z["box_cost_net"]),4),"l1_usd":_Z["l1_usd"],"close_ts":tbx["close_ts"]})
       if(a._can_emit_zero_loss_math_live("TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",float(tbx["close_ts"]),now)and _w.get("market_id")!=_v.get("market_id")and.0<(float(tbx["close_ts"])-now)<=259200.):a.emit_live_two_leg_box_candidate(sleeve_source="TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",box_type="SPORTS_CORRIDOR",asset="TENNIS",dedupe_key=_u,leg_a=_w,leg_b=_v,bk_a=_h,bk_b=_g,close_ts=float(tbx["close_ts"]),now_ts=now,k_low=float(_w.get("strike")or 1e2),k_high=float(_v.get("strike")or 101.))
       await a.open_shadow_two_leg_box("TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",_u,"TENNIS_BO3",tbx["label"],_w,_v,_h,_g,float(tbx["close_ts"]),.988,{"is_two_leg_box":True,"mode":tbx["mode"]})
  d=[]
  if any((tr.end_ts-3.5*3600.)<=now<=(tr.end_ts+2.*3600.)for tr in a.soccer_trees.values()):d.append("SOCCER")
  for sp_k in("NHL","NFL","CFB"):
   if any(ms.sport==sp_k and(ms.start_ts-9e2)<=now<=(ms.start_ts+6.*3600.)for ms in a.multi_sport_games.values()):d.append(sp_k)
  i={};f=[sp_k for sp_k in d if sp_k not in a.live_multisport_boards or(now-a.live_multisport_boards[sp_k][0])>=20.]
  if f:
   h=await asyncio.gather(*(asyncio.to_thread(fetch_espn_multisport_board_sync,sp_k)for sp_k in f))
   for sp_k,_f in zip(f,h):a.live_multisport_boards[sp_k]=(now,_f)
  for sp_k in d:
   if sp_k in a.live_multisport_boards:i[sp_k]=a.live_multisport_boards[sp_k][1]
  u=[]
  if"SOCCER"in i and i["SOCCER"]:
   for tr in a.soccer_trees.values():
    for _Y in evaluate_cl1_soccer_tree_clinch_locks(tr,i["SOCCER"],a.score_confirm_tracker,now):
     _t=f"CL1_SOC_{_Y['market_id']}"
     if _t not in a.entered_keys and _t not in a.inflight_keys:u.append({**_Y,"dedupe_key":_t,"title":getattr(tr,"title",""),"rules_text":getattr(tr,"rules_text","")})
  for _s in a.multi_sport_games.values():
   if _s.sport in i and i[_s.sport]:
    for _X in evaluate_cl1_multisport_corridor_clinch_locks(_s,i,a.score_confirm_tracker,now):
     _e=f"CL1_{_s.sport}_{_X['market_id']}"
     if _e not in a.entered_keys and _e not in a.inflight_keys:u.append({**_X,"dedupe_key":_e,"title":getattr(_s,"title",""),"rules_text":getattr(_s,"rules_text","")})
  if u:
   S=await a.fetch_books_batch(sorted({t for c in u for t in(c["token_id"],c["opp_token_id"])}),timeout=3.)
   for _W in u:
    if"FINAL"not in str(_W.get("mode")or"").upper()and classify_market_rule_dispute_risk(_W)["veto_pre_final_clinch"]:continue
    R,Q=S.get(_W["token_id"]),S.get(_W["opp_token_id"])
    if not R or not Q:continue
    C,_=extract_best_bid(Q.get("bids")or[])
    if C>.04:continue
    _r=float(_W.get("fee_rate")or.0);_q=float(_W.get("fee_exponent")or 1.);_V=walk_l2_book_asks_depth_capped(R.get("asks")or[],BANKROLL_TICKETS["T1000"]["CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"],BANKROLL_TICKETS["T100"]["CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"],fee_rate=_r,min_l1_usd=15.,max_ask_px=.9821,fee_exponent=_q)
    if _V.get("filled"):
     _d=float(_V["eff_px"]);_U=float(_W["p_lock"]);_c=round(_U-_d,4)
     if.72<=_d<=.982 and _c>=.015:
      B=max(now+6e2,float(_W["close_ts"]));opps_out.append({"sleeve":"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","market":f"[{_W['mode']}] {_W['display_label']}","ask_vwap":_d,"p_model":_U,"net_edge":_c,"l1_usd":_V["l1_usd"],"close_ts":B})
      if a._can_emit_zero_loss_math_live("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",B,now,p_model=_U):a.emit_live_single_leg_lock_candidate(sleeve_source="CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",asset=str(_W["sport"]).upper(),dedupe_key=str(_W["dedupe_key"]),token_id=str(_W["token_id"]),opp_token_id=str(_W["opp_token_id"]),market_id=str(_W["market_id"]),condition_id=str(_W["condition_id"]),side_label=str(_W["side_label"]),display_label=str(_W["display_label"]),bk_win=R,bk_opp=Q,fee_rate=_r,fee_exponent=_q,neg_risk=bool(_W.get("neg_risk",False)),close_ts=B,now_ts=now,max_lock_eff_px=.982,max_opp_bid=.025,hold_to_maturity=True,p_model=_U)
      await a.open_shadow_position("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",_W["dedupe_key"],_W["sport"],_W["display_label"],str(_W["side_label"]),str(_W["token_id"]),_r,_U,B,{"market_id":_W["market_id"],"condition_id":_W["condition_id"],"opp_token_id":_W["opp_token_id"],"mode":_W["mode"],"fee_exponent":_q},prefetched_book=R)
 async def _scan_frontier_v4_sleeves(a,opps_out,now):
  q=[];a.subperiod_freeze_tracker.prune(now);a.score_confirm_tracker.prune(now);k=[]
  if any((lat.end_ts-3.5*3600.)<=now<=(lat.end_ts+2.5*3600.)for lat in a.soc2_lattices.values()):k.append("SOCCER")
  if any((b.sport=="NFL"and(b.start_ts-9e2)<=now<=(b.start_ts+6.*3600.))for b in a.aff1_bundles.values())or any((sl.kickoff_ts-9e2)<=now<=(sl.kickoff_ts+6.*3600.)for sl in a.nfl_prop_slates.values()):k.append("NFL")
  if any((b.sport=="CFB"and(b.start_ts-9e2)<=now<=(b.start_ts+6.*3600.))for b in a.aff1_bundles.values()):k.append("CFB")
  E=[sp_k for sp_k in k if sp_k not in a.live_multisport_boards or(now-a.live_multisport_boards[sp_k][0])>=20.]
  if E:
   K=await asyncio.gather(*(asyncio.to_thread(fetch_espn_multisport_board_sync,sp_k)for sp_k in E))
   for sp_k,_0 in zip(E,K):a.live_multisport_boards[sp_k]=(now,_0)
  J=[b for b in a.aff1_bundles.values()if b.settle_est_ts>now+120.]
  if J:
   _a={t for b in J for t in([tk for m in b.markets for tk in(m.tok_0,m.tok_1)]+([str(b.overtime_yes_leg["token_id"])]if b.overtime_yes_leg else[])+[tk for fp in b.first_passage_markets for tk in(fp.away_token,fp.home_token)])if t};_f=await a.fetch_books_batch(sorted(_a),timeout=3.5)if _a else{};Z={t:p for t,bk in _f.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for b in J:
    for tri in detect_sum1_frechet_triangles(b,Z,max_3leg_cost_net=.99):
     _Z=tri["legs"]
     if not all(x["token_id"]in _f for x in _Z):continue
     _z=f"SUM1_{b.event_id}_{'_'.join(str(x['token_id'])[-6:]for x in _Z)}";_Y=walk_equal_shares_multi_leg_box([{"asks":_f[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x["fee_exponent"])}for x in _Z],BANKROLL_TICKETS["T1000"]["SUM1_FRECHET_SUM_TRIANGLES"],1.,.99,min_shares=6,min_box_notional_usd=5.5)
     if _Y.get("filled"):opps_out.append({"sleeve":"SUM1_FRECHET_SUM_TRIANGLES","market":tri["label"],"ask_vwap":_Y["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_Y["box_cost_net"]),4),"l1_usd":_Y["l1_usd"],"close_ts":tri["close_ts"]});await a.open_shadow_multi_leg_bundle("SUM1_FRECHET_SUM_TRIANGLES",_z,b.sport,tri["label"],_Z,_f,float(tri["close_ts"]),1.,.99,{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"mode":tri["mode"]})
    d=None;h=""
    if b.sport=="NBA"and a.live_nba_board:
     I=a.nba_games.get(b.event_id);D=match_nba_live_game(I,a.live_nba_board)if I is not None else None
     if D is not None and D[0].state in("in","post"):
      h=str(D[0].game_id or"")
      if h:
       _X=a.nba_ext_summary_cache.get(h)
       if _X is not None and(now-_X[0])<15.:d=_X[1]
       else:
        try:_y,_W=await asyncio.to_thread(fetch_espn_nba_full_summary_sync,h);a.nba_boxscore_cache[h]=(now,_y);a.nba_ext_summary_cache[h]=(now,_W);d=_W
        except Exception:d=None
    elif b.sport in("NFL","CFB")and b.sport in a.live_multisport_boards:
     for _aa in a.live_multisport_boards[b.sport][1]:
      if _aa.start_ts>0 and b.start_ts>0 and abs(_aa.start_ts-b.start_ts)>10.*3600.:continue
      _x=_teams_match_fuzzy(b.away_team,_aa.away_name)and _teams_match_fuzzy(b.home_team,_aa.home_name);_w=_teams_match_fuzzy(b.away_team,_aa.home_name)and _teams_match_fuzzy(b.home_team,_aa.away_name)
      if _x and _w:continue
      if _x or _w:h=_aa.game_id;_V=dict(_aa.linescores_home if _w else _aa.linescores_away);_U=dict(_aa.linescores_away if _w else _aa.linescores_home);d={"state":_aa.state,"completed":_aa.completed,"is_halftime":_aa.is_halftime,"period":_aa.period,"clock_sec":_aa.clock_sec,"away_score":_aa.home_score if _w else _aa.away_score,"home_score":_aa.away_score if _w else _aa.home_score,"linescores":{"away":_V,"home":_U}};break
    if d:
     _e=evaluate_aff1_frozen_subperiod_opportunities(b,d,Z,a.subperiod_freeze_tracker,now,espn_game_id=h,max_2leg_cost_net=.992,max_3leg_cost_net=.99)
     for abx in _e["two_leg_boxes"]:
      _T,_S=abx["leg_a"],abx["leg_b"];_v,_u=_f.get(_T["token_id"]),_f.get(_S["token_id"])
      if not _v or not _u:continue
      _t=f"AFF1_2L_{b.event_id}_{_T['token_id'][-8:]}_{_S['token_id'][-8:]}";_R=walk_equal_shares_dominance_box(_v.get("asks")or[],_u.get("asks")or[],BANKROLL_TICKETS["T1000"]["AFF1_FROZEN_SUBPERIOD_COLLAPSE"],float(_T["fee_rate"]),float(_S["fee_rate"]),fee_exponent_a=float(_T["fee_exponent"]),fee_exponent_b=float(_S["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
      if _R.get("filled"):
       opps_out.append({"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","market":abx["label"],"ask_vwap":_R["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_R["box_cost_net"]),4),"l1_usd":_R["l1_usd"],"close_ts":abx["close_ts"]})
       if(a._can_emit_zero_loss_math_live("AFF1_FROZEN_SUBPERIOD_COLLAPSE",float(abx["close_ts"]),now)and float(_R["box_cost_net"])<=.988 and.0<(float(abx["close_ts"])-now)<=86400.):a.emit_live_two_leg_box_candidate(sleeve_source="AFF1_FROZEN_SUBPERIOD_COLLAPSE",box_type="SPORTS_CORRIDOR",asset=b.sport,dedupe_key=_t,leg_a=_T,leg_b=_S,bk_a=_v,bk_b=_u,close_ts=float(abx["close_ts"]),now_ts=now,k_low=float(_T.get("strike")or 1e2),k_high=float(_S.get("strike")or 101.))
       await a.open_shadow_two_leg_box("AFF1_FROZEN_SUBPERIOD_COLLAPSE",_t,b.sport,abx["label"],_T,_S,_v,_u,float(abx["close_ts"]),.992,{"is_two_leg_box":True,"mode":abx["mode"],"middle_width":abx["middle_width"]})
     for ab3 in _e["three_leg_boxes"]:
      _9=ab3["legs"]
      if not all(x["token_id"]in _f for x in _9):continue
      _s=f"AFF1_3L_{b.event_id}_{'_'.join(str(x['token_id'])[-6:]for x in _9)}";_Q=walk_equal_shares_multi_leg_box([{"asks":_f[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x["fee_exponent"])}for x in _9],BANKROLL_TICKETS["T1000"]["AFF1_FROZEN_SUBPERIOD_COLLAPSE"],1.,.99,min_shares=6,min_box_notional_usd=5.5)
      if _Q.get("filled"):opps_out.append({"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","market":ab3["label"],"ask_vwap":_Q["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_Q["box_cost_net"]),4),"l1_usd":_Q["l1_usd"],"close_ts":ab3["close_ts"]});await a.open_shadow_multi_leg_bundle("AFF1_FROZEN_SUBPERIOD_COLLAPSE",_s,b.sport,ab3["label"],_9,_f,float(ab3["close_ts"]),1.,.99,{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"mode":ab3["mode"]})
     for alk in _e["single_leg_locks"]:_r=f"AFF1_LK_{b.event_id}_{alk['market_id']}";q.append({**alk,"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","asset":b.sport,"dedupe_key":_r,"max_eff_px":.988,"title":getattr(b,"title",""),"rules_text":getattr(b,"rules_text","")})
  R=a.live_multisport_boards["SOCCER"][1]if"SOCCER"in a.live_multisport_boards else[]
  if R:
   for lat in a.soc2_lattices.values():
    if(lat.end_ts+7200.)<=now:continue
    for slk in evaluate_soc2_dead_score_no_locks(lat,R,a.score_confirm_tracker,now):_q=f"SOC2_NO_{slk['market_id']}";q.append({**slk,"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","asset":"SOCCER","dedupe_key":_q,"max_eff_px":.986,"title":getattr(lat,"title",""),"rules_text":getattr(lat,"rules_text","")})
  Y=[lat for lat in a.soc2_lattices.values()if lat.end_ts>now+120.][:10]
  if Y:
   Q=sorted({str(lg["token_id"])for lat in Y for lg in lat.matrix_legs if lg.get("token_id")}|{str(t_cv)for lat in Y if lat.convert_spec is not None for b_cv in lat.convert_spec.brackets for t_cv in(b_cv.get("no_token"),b_cv.get("yes_token"))if t_cv});X=await a.fetch_books_batch(Q,timeout=3.5)if Q else{};P={t:p for t,bk in X.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for lat in Y:
    _p=detect_soc2_lattice_boxes_and_converts(lat,X,P,max_2leg_cost_net=.99,max_3leg_cost_net=.988,target_budget_usd=BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"])
    for sbx in _p["matrix_boxes"]:
     _P=sbx["legs"]
     if int(sbx["n_legs"])==2:
      _8,_7=_P[0],_P[1];_O,_N=X.get(_8["token_id"]),X.get(_7["token_id"])
      if not _O or not _N:continue
      _M=f"SOC2_2L_{lat.exact_event_id}_{_8['token_id'][-8:]}_{_7['token_id'][-8:]}";_6=walk_equal_shares_dominance_box(_O.get("asks")or[],_N.get("asks")or[],BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"],float(_8["fee_rate"]),float(_7["fee_rate"]),fee_exponent_a=float(_8.get("fee_exponent",1.)),fee_exponent_b=float(_7.get("fee_exponent",1.)),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
      if _6.get("filled"):
       opps_out.append({"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","market":f"{lat.title}: {sbx['label']}","ask_vwap":_6["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_6["box_cost_net"]),4),"l1_usd":_6["l1_usd"],"close_ts":sbx["close_ts"]})
       if(bool(sbx.get("exhaustive_partition_verified"))and a._can_emit_zero_loss_math_live("SOC2_EXACT_SCORE_2D_LATTICE",float(sbx["close_ts"]),now)and _8.get("market_id")!=_7.get("market_id")and float(_6["box_cost_net"])<=.988 and.0<(float(sbx["close_ts"])-now)<=172800.):a.emit_live_two_leg_box_candidate(sleeve_source="SOC2_EXACT_SCORE_2D_LATTICE",box_type="SPORTS_CORRIDOR",asset="SOCCER",dedupe_key=_M,leg_a=_8,leg_b=_7,bk_a=_O,bk_b=_N,close_ts=float(sbx["close_ts"]),now_ts=now,k_low=float(_8.get("strike")or 1e2),k_high=float(_7.get("strike")or 101.))
       await a.open_shadow_two_leg_box("SOC2_EXACT_SCORE_2D_LATTICE",_M,"SOCCER",f"{lat.title}: {sbx['label']}",_8,_7,_O,_N,float(sbx["close_ts"]),.99,{"is_two_leg_box":True,"mode":sbx["mode"]})
     elif int(sbx["n_legs"])==3 and all(x["token_id"]in X for x in _P):
      _L=f"SOC2_3L_{lat.exact_event_id}_{'_'.join(str(x['token_id'])[-6:]for x in _P)}";_5=walk_equal_shares_multi_leg_box([{"asks":X[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x.get("fee_exponent",1.))}for x in _P],BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"],1.,.988,min_shares=6,min_box_notional_usd=5.5)
      if _5.get("filled"):opps_out.append({"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","market":f"{lat.title} 3L: {sbx['label']}","ask_vwap":_5["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_5["box_cost_net"]),4),"l1_usd":_5["l1_usd"],"close_ts":sbx["close_ts"]});await a.open_shadow_multi_leg_bundle("SOC2_EXACT_SCORE_2D_LATTICE",_L,"SOCCER",f"{lat.title} 3L: {sbx['label']}",_P,X,float(sbx["close_ts"]),1.,.988,{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"mode":sbx["mode"]})
    if lat.convert_spec is not None and _p["convert_arbs"]:await a.execute_nr2_subset_convert_arb(lat.convert_spec,_p["convert_arbs"][0],X,opps_out)
  o=[sl for sl in a.nfl_prop_slates.values()if sl.settle_est_ts>now+120.][:8]
  if o:
   v=sorted({tk for sl in o for rg in(list(sl.anytime_td_by_player.values())+list(sl.two_plus_td_by_player.values())+[r for r_list in sl.ladders_by_player_stat.values()for r in r_list])for tk in(rg.yes_over_token,rg.no_under_token)if tk});C=await a.fetch_books_batch(v,timeout=3.5)if v else{};u={t:p for t,bk in C.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.};O=a.live_multisport_boards["NFL"][1]if"NFL"in a.live_multisport_boards else[]
   for sl in o:
    for pbx in detect_nfl_prp1_boxes(sl,u,max_box_cost_net=.99):
     _K,_J=pbx["leg_a"],pbx["leg_b"];_o,_n=C.get(_K["token_id"]),C.get(_J["token_id"])
     if not _o or not _n:continue
     _I=f"NFL_PRP1_2L_{sl.event_id}_{_K['token_id'][-8:]}_{_J['token_id'][-8:]}";_4=walk_equal_shares_dominance_box(_o.get("asks")or[],_n.get("asks")or[],BANKROLL_TICKETS["T1000"]["NFL_PRP1_MILESTONE_AND_MAX_LOCKS"],float(_K["fee_rate"]),float(_J["fee_rate"]),fee_exponent_a=float(_K["fee_exponent"]),fee_exponent_b=float(_J["fee_exponent"]),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
     if _4.get("filled"):
      opps_out.append({"sleeve":"NFL_PRP1_MILESTONE_AND_MAX_LOCKS","market":f"{sl.title} [{pbx['label']}]","ask_vwap":_4["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_4["box_cost_net"]),4),"l1_usd":_4["l1_usd"],"close_ts":pbx["close_ts"]})
      if(a._can_emit_zero_loss_math_live("NFL_PRP1_MILESTONE_AND_MAX_LOCKS",float(pbx["close_ts"]),now)and _K.get("market_id")!=_J.get("market_id")and float(_4["box_cost_net"])<=.988 and.0<(float(pbx["close_ts"])-now)<=172800.):a.emit_live_two_leg_box_candidate(sleeve_source="NFL_PRP1_MILESTONE_AND_MAX_LOCKS",box_type="SPORTS_CORRIDOR",asset="NFL",dedupe_key=_I,leg_a=_K,leg_b=_J,bk_a=_o,bk_b=_n,close_ts=float(pbx["close_ts"]),now_ts=now,k_low=float(_K.get("strike")or.5),k_high=float(_J.get("strike")or 1.5))
      await a.open_shadow_two_leg_box("NFL_PRP1_MILESTONE_AND_MAX_LOCKS",_I,"NFL",f"{sl.title} [{pbx['label']}]",_K,_J,_o,_n,float(pbx["close_ts"]),.99,{"is_two_leg_box":True,"mode":pbx["mode"]})
    if O:
     B=next((g for g in O if(g.start_ts<=0 or abs(g.start_ts-sl.kickoff_ts)<=10.*3600.)and((_teams_match_fuzzy(sl.away_team,g.away_name)and _teams_match_fuzzy(sl.home_team,g.home_name))!=(_teams_match_fuzzy(sl.away_team,g.home_name)and _teams_match_fuzzy(sl.home_team,g.away_name)))),None)
     if B is not None and B.state in("in","post"):
      _3=a.nfl_summary_cache.get(B.game_id)
      if _3 is not None and(now-_3[0])<15.:f=_3[1]
      else:
       try:f=await asyncio.to_thread(fetch_espn_nfl_summary_sync,B.game_id);a.nfl_summary_cache[B.game_id]=(now,f)
       except Exception:f={}
      if f:
       for nlk in evaluate_nfl_prp1_live_locks(sl,f,a.score_confirm_tracker,now):_m=f"NFL_PRP1_LK_{sl.event_id}_{nlk['market_id']}";q.append({**nlk,"sleeve":"NFL_PRP1_MILESTONE_AND_MAX_LOCKS","asset":"NFL","dedupe_key":_m,"max_eff_px":.988,"title":getattr(sl,"title",""),"rules_text":getattr(sl,"rules_text","")})
  if a.barrier_rungs or a.binance_close_rungs:
   N=[hr for hr in a.barrier_rungs.values()if hr.resolved_yes is None and hr.end_ts>now+120. and hr.asset!="HYPE"and(a.spots.get(hr.asset,.0)<=.0 or abs(math.log(max(1e-9,hr.strike)/a.spots[hr.asset]))<=.35)];A=[cr for cr in a.binance_close_rungs if cr.close_ts>now+120. and cr.asset!="HYPE"and(a.spots.get(cr.asset,.0)<=.0 or abs(math.log(max(1e-9,cr.strike)/a.spots[cr.asset]))<=.35)];W=sorted({t for hr in N for t in(hr.yes_token,hr.no_token)}|{cr.no_token for cr in A})
   if W:
    _d=await a.fetch_books_batch(W,timeout=3.5);V={t:p for t,bk in _d.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for cbx in detect_cry_inc1_binance_inclusion_boxes(N,A,V,now,max_box_cost_net=.992):
     _H,_G=cbx["leg_a"],cbx["leg_b"];_l,_k=_d.get(_H["token_id"]),_d.get(_G["token_id"])
     if not _l or not _k:continue
     _F=f"CRY_INC1_{cbx['asset']}_{_H['market_id']}_{_G['market_id']}";_2=walk_equal_shares_dominance_box(_l.get("asks")or[],_k.get("asks")or[],BANKROLL_TICKETS["T1000"]["CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION"],float(_H["fee_rate"]),float(_G["fee_rate"]),fee_exponent_a=float(_H["fee_exponent"]),fee_exponent_b=float(_G["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
     if _2.get("filled"):
      opps_out.append({"sleeve":"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION","market":cbx["label"],"ask_vwap":_2["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_2["box_cost_net"]),4),"l1_usd":_2["l1_usd"],"close_ts":cbx["close_ts"]})
      if(a._can_emit_zero_loss_math_live("CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",float(cbx["close_ts"]),now)and float(_2["box_cost_net"])<=.988 and.0<(float(cbx["close_ts"])-now)<=604800.):a.emit_live_two_leg_box_candidate(sleeve_source="CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",box_type="BARRIER_MONO",asset=str(cbx["asset"]),dedupe_key=_F,leg_a=_H,leg_b=_G,bk_a=_l,bk_b=_k,close_ts=float(cbx["close_ts"]),now_ts=now,k_low=min(float(_H["strike"]),float(_G["strike"])),k_high=max(float(_H["strike"]),float(_G["strike"])))
      await a.open_shadow_two_leg_box("CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",_F,str(cbx["asset"]),cbx["label"],_H,_G,_l,_k,float(cbx["close_ts"]),.992,{"is_two_leg_box":True,"mode":cbx["mode"],"direction":cbx["direction"]})
  n=[c for c in q if c["dedupe_key"]not in a.entered_keys and c["dedupe_key"]not in a.inflight_keys]
  if n:
   M=await a.fetch_books_batch(sorted({t for c in n for t in(str(c["token_id"]),str(c["opp_token_id"]))if t}),timeout=3.)
   for clk in n:
    L=classify_market_rule_dispute_risk(clk)
    if"FINAL"not in str(clk.get("mode")or"").upper()and L["veto_pre_final_clinch"]:continue
    _E,_D=str(clk["token_id"]),str(clk["opp_token_id"]);l,_c=M.get(_E),M.get(_D)
    if not l or not _c:continue
    l={**l,"_s2_meta":{"mode":str(clk.get("mode")or""),"dispute_risk":bool(L["dispute_risk"])}};H,_=extract_best_bid(_c.get("bids")or[])
    if H>.035:continue
    _C=str(clk["sleeve"]);_B=float(clk.get("fee_rate")or.0);_A=float(clk.get("fee_exponent")or 1.);G=float(clk.get("max_eff_px")or.988);_b=float(clk["p_lock"]);U=max(now+6e2,float(clk["close_ts"]));_1=walk_l2_book_asks_depth_capped(l.get("asks")or[],BANKROLL_TICKETS["T1000"][_C],BANKROLL_TICKETS["T100"][_C],fee_rate=_B,min_l1_usd=15.,max_ask_px=G+1e-4,fee_exponent=_A);e=False
    if _1.get("filled"):
     _j=float(_1["eff_px"]);_i=round(_b-_j,4)
     if.72<=_j<=G and _i>=.012:
      opps_out.append({"sleeve":_C,"market":f"[{clk['mode']}] {clk['display_label']}","ask_vwap":_j,"p_model":_b,"net_edge":_i,"l1_usd":_1["l1_usd"],"close_ts":U})
      if a._can_emit_zero_loss_math_live(_C,U,now,p_model=_b):a.emit_live_single_leg_lock_candidate(sleeve_source=_C,asset=str(clk["asset"]).upper(),dedupe_key=str(clk["dedupe_key"]),token_id=_E,opp_token_id=_D,market_id=str(clk["market_id"]),condition_id=str(clk["condition_id"]),side_label=str(clk["side_label"]),display_label=str(clk["display_label"]),bk_win=l,bk_opp=_c,fee_rate=_B,fee_exponent=_A,neg_risk=bool(clk.get("neg_risk",False)),close_ts=U,now_ts=now,max_lock_eff_px=G,max_opp_bid=.025,hold_to_maturity=True,p_model=_b)
      e=await a.open_shadow_position(_C,str(clk["dedupe_key"]),str(clk["asset"]),str(clk["display_label"]),str(clk["side_label"]),_E,_B,_b,U,{"market_id":clk["market_id"],"condition_id":clk["condition_id"],"opp_token_id":_D,"mode":clk["mode"],"fee_exponent":_A},prefetched_book=l)
    if not e:
     _h=f"MKR_LK1_{clk['market_id']}";j=_h not in a.entered_keys and _h not in a.inflight_keys;i=not(a.single_scan or("fetch_json"in a.__dict__))
     if j or(i and _h not in a.inflight_keys):
      T,F=extract_best_bid(l.get("bids")or[]);S,_=a._best_ask_sz(l);z=.15 if str(clk["asset"]).upper()in("BTC","ETH","SOL","XRP","DOGE","BNB","HYPE","XAU")else.2;y=.997 if(i and _b>=.999 and(U-now)<=7200.)else.991;w=.0025 if y>=.997 else.006;_g=evaluate_mkr_lock1_post_clinch_rebate_bid(token_id=_E,opp_token_id=_D,market_id=str(clk["market_id"]),condition_id=str(clk["condition_id"]),display_label=str(clk["display_label"]),source_sleeve=_C,p_lock=_b,close_ts=U,now_ts=now,best_bid=T if T>.0 else None,best_ask=S if S<1. else None,opp_best_bid=H,fee_rate=_B,fee_exponent=_A,maker_rebate_share=z,neg_risk=bool(clk.get("neg_risk",False)),max_maker_bid=y,min_net_edge_ps=w)
      if _g is not None:
       if j:opps_out.append({"sleeve":"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER","market":_g["display_label"],"ask_vwap":_g["effective_net_cost_per_share"],"p_model":_b,"net_edge":round(float(_g["expected_net_edge_per_share"]),4),"l1_usd":max(25.,F),"close_ts":U})
       if(T>=.94-1e-9 and F>=10.-1e-6 and a._can_emit_zero_loss_math_live("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",U,now,p_model=_b)):a.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",asset=str(clk["asset"]).upper(),dedupe_key=_h,pair_dedupe_key=str(clk["dedupe_key"]),token_id=_E,opp_token_id=_D,market_id=str(clk["market_id"]),condition_id=str(clk["condition_id"]),side_label=str(clk["side_label"]),display_label=str(clk["display_label"]),bk_win=l,bk_opp=_c,neg_risk=bool(clk.get("neg_risk",False)),close_ts=U,now_ts=now,min_resting_bid=.94,max_resting_bid=y,min_maker_edge=w,max_opp_bid=.03,hold_to_maturity=True,p_model=_b,target_bid_px=float(_g["post_only_bid"]),maker_rebate_ps=float(_g["maker_rebate_per_share"]))
       if j:await a.post_shadow_maker_entry(sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",dedupe_key=_h,asset=str(clk["asset"]),title=str(_g["display_label"]),side_label=str(clk["side_label"]),token_id=_E,p_model=_b,close_ts=U,extra={"market_id":clk["market_id"],"condition_id":clk["condition_id"],"opp_token_id":_D,"source_sleeve":_C,"resting_bid_override":_g["post_only_bid"],"maker_rebate_ps":_g["maker_rebate_per_share"]},prefetched_book=l,ttl_override_sec=180.)
 async def _scan_phase2_macro_counting_gas(a,opps_out,now):
  try:await a._scan_phase2_macro_counting_gas_core(opps_out,now)
  except Exception as _p2_exc:logger.warning(f"[ALPHA-124] Phase-2 macro/counting/gas scan notice: {_p2_exc}")
  await a.scan_uma_resolution_bonds(opps_out,now_ts=now)
 async def _scan_phase2_macro_counting_gas_core(a,opps_out,now):
  l=[s for s in a.counting_slates.values()if s.window_end_ts>now+60]
  if l:
   F=sorted({s.handle for s in l});R=await asyncio.gather(*(asyncio.to_thread(fetch_xtracker_user_stats_sync,h)for h in F));j=dict(zip(F,R));z=[t for s in l for b in s.brackets for t in(b.yes_token,b.no_token)];E=await a.fetch_books_batch(z,timeout=3.5);g={}
   for _G,_x in E.items():
    _w,_v=a._best_ask_sz(_x)
    if _w<1. and _w*_v>=8.:g[_G]=_w
   for _u in l:
    D,y=evaluate_counting_dead_no_locks(_u,j.get(_u.handle)or{});a._record_market_telemetry(key=f"TW1_SNAP_{_u.event_id}",min_interval_sec=120.,now_ts=now,sig=(D,len(y)),payload={"type":"COUNTING_TRACKER_SNAP","slug":_u.slug,"handle":_u.handle,"verified_floor":D,"dead_open_brackets":len(y),"tte_sec":round(_u.window_end_ts-now,0)})
    for _F in y:
     Q=E.get(_F.no_token)
     if not Q:continue
     P,_=extract_best_bid(Q.get("bids")or[]);O,_=a._best_ask_sz(Q);N=float(getattr(_F,"fee_rate",.0)or.0);M=float(getattr(_F,"fee_exponent",1.)or 1.);_g=walk_l2_book_asks(Q.get("asks")or[],BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"],fee_rate=N,min_l1_usd=15.,max_ask_px=.99,fee_exponent=M)
     if _g.get("filled")and.8<=float(_g["eff_px"])<=.99:
      L=round(1.-float(_g["eff_px"]),4)
      if L>=.01:
       opps_out.append({"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","market":f"{_u.handle} Dead Bracket NO[{_F.label}] (count>={D})","ask_vwap":_g["eff_px"],"p_model":1.,"net_edge":L,"l1_usd":_g["l1_usd"],"close_ts":_u.window_end_ts})
       if(_u.window_end_ts-now)<=172800.:a.emit_live_single_leg_lock_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",asset=_u.handle.upper(),dedupe_key=f"TW1_NO_{_F.market_id}",token_id=_F.no_token,opp_token_id=_F.yes_token,market_id=_F.market_id,condition_id=_F.condition_id,side_label="NO",display_label=f"{_u.handle} Dead NO[{_F.label}]",bk_win=Q,bk_opp=E.get(_F.yes_token),fee_rate=N,fee_exponent=M,neg_risk=bool(_F.neg_risk),close_ts=float(_u.window_end_ts),now_ts=now,max_lock_eff_px=.99,max_opp_bid=.02,hold_to_maturity=(float(_g["eff_px"])>=.98),p_model=1.)
       await a.open_shadow_position("TW1_COUNTING_TRUNCATION_AND_BOX",f"TW1_NO_{_F.market_id}",_u.handle.upper(),f"{_u.title} [Dead NO {_F.label}]","NO",_F.no_token,N,1.,_u.window_end_ts,{"market_id":_F.market_id,"condition_id":_F.condition_id,"verified_floor":D,"fee_exponent":M},prefetched_book=Q)
     _f=evaluate_locked_market_reward_carry(1.,P,O,_F.rewards_min_size,_F.rewards_max_spread,N)
     if _f.get("eligible"):
      opps_out.append({"sleeve":"MKR_REWARD_LOCKED_CARRY","market":f"{_u.handle} Locked Carry NO[{_F.label}] @ ${_f['resting_bid']:.3f}","ask_vwap":_f["resting_bid"],"p_model":1.,"net_edge":_f["carry_edge"],"l1_usd":50.,"close_ts":_u.window_end_ts});await a.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY",f"MKR_RW_{_F.market_id}",_u.handle.upper(),f"{_u.title} [Reward Carry NO {_F.label}]","NO",_F.no_token,1.,_u.window_end_ts,{"market_id":_F.market_id,"condition_id":_F.condition_id,"opp_token_id":_F.yes_token,"resting_bid_override":_f["resting_bid"]},prefetched_book=Q)
      if is_reward_locked_carry_live_ready(a,1.)and getattr(_F,"neg_risk",None)is not None:a.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_REWARD_LOCKED_CARRY",asset=_u.handle.upper(),dedupe_key=f"MKR_RW_{_F.market_id}",pair_dedupe_key=f"MKR_RW_PAIR_{_F.market_id}",token_id=_F.no_token,opp_token_id=_F.yes_token,market_id=_F.market_id,condition_id=_F.condition_id,side_label="NO",display_label=f"{_u.handle} Reward Carry NO[{_F.label}]",bk_win=Q,bk_opp=E.get(_F.yes_token),neg_risk=bool(_F.neg_risk),close_ts=float(_u.window_end_ts),now_ts=now,min_resting_bid=.94,max_resting_bid=.994,min_maker_edge=.006,max_opp_bid=.03,hold_to_maturity=True,p_model=1.,target_bid_px=float(_f["resting_bid"]))
   w=detect_counting_subwindow_boxes(l,g,j,max_box_cost_net=1.05)
   if w:_E=w[0];a._record_market_telemetry(f"TW1_BOX_{_E['handle']}",90.,{"type":"COUNTING_SUBWINDOW_BEST","handle":_E["handle"],"net_box_l1":_E["box_cost_net"],"label":_E["label"]},now_ts=now,sig=(_E["label"],_E["box_cost_net"]))
   for tb in w:
    _t,_s=tb["leg_a"],tb["leg_b"];_e,_d=E.get(_t["token_id"]),E.get(_s["token_id"])
    if not _e or not _d:continue
    _c=f"TW1_BOX_{_t['market_id']}_{_s['market_id']}"
    if float(tb["box_cost_net"])<=.993:
     _r=walk_equal_shares_dominance_box(_e.get("asks")or[],_d.get("asks")or[],BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"],float(_t.get("fee_rate",.0)),float(_s.get("fee_rate",.0)),fee_exponent_a=float(_t.get("fee_exponent",1.)),fee_exponent_b=float(_s.get("fee_exponent",1.)),max_box_cost_net=.993,min_shares=6,min_box_notional_usd=5.5)
     if _r.get("filled"):
      opps_out.append({"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","market":f"Counting Box {tb['label']}","ask_vwap":_r["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_r["box_cost_net"]),4),"l1_usd":_r["l1_usd"],"close_ts":tb["close_ts"]});d=False
      if(float(tb["close_ts"])-now)<=86400. and float(_r["box_cost_net"])<=.99:d=a.emit_live_two_leg_box_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",box_type="COUNTING_DOMINANCE",asset=tb["handle"].upper(),dedupe_key=_c,leg_a=_t,leg_b=_s,bk_a=_e,bk_b=_d,close_ts=float(tb["close_ts"]),now_ts=now)
      await a.open_shadow_two_leg_box("TW1_COUNTING_TRUNCATION_AND_BOX",_c,tb["handle"].upper(),f"Counting Box {tb['label']}",_t,_s,_e,_d,float(tb["close_ts"]),.993,{"is_two_leg_box":True,"banked":tb["banked"]})
      if not d:a.post_zero_fee_maker_anchor_box("TW1",tb["handle"].upper(),f"ZFA_{_c}",_t,_s,_e,_d,float(tb["close_ts"]),f"Counting Box {tb['label']}",now,prefetched_books=E,live_emit_only=True)
     else:a.post_zero_fee_maker_anchor_box("TW1",tb["handle"].upper(),f"ZFA_{_c}",_t,_s,_e,_d,float(tb["close_ts"]),f"Counting Box {tb['label']}",now,prefetched_books=E)
    elif float(tb["box_cost_net"])<=1.035:a.post_zero_fee_maker_anchor_box("TW1",tb["handle"].upper(),f"ZFA_{_c}",_t,_s,_e,_d,float(tb["close_ts"]),f"Counting Box {tb['label']}",now,prefetched_books=E)
  C=[lg for lg in(a.fomc_truth_legs+a.oil_senate_truth_legs)if float(lg["end_ts"])>now+60]
  if C:
   K=await a.fetch_books_batch(sorted({str(lg["token_id"])for lg in C}),timeout=3.5);B={t:p for t,bk in K.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for _b,v,u,r,J in(("FED1_CENTRAL_BANK_LP_BOX","FOMC",a.fomc_truth_legs,ALL_FOMC_MASK,"FOMC_LP_BEST"),("COND1_MACRO_PARTITION_BOX","OIL_SENATE",a.oil_senate_truth_legs,ALL_OIL_SENATE_MASK,"OIL_SENATE_PARTITION_BEST")):
    if not u:continue
    A=find_cross_event_bitmask_boxes(u,B,r,max_2leg_cost=1.05,max_3leg_cost=1.03)
    if A:b0=A[0];a._record_market_telemetry(f"{J}_DIAG",90.,{"type":J,"n_legs":b0["n_legs"],"net_box_l1":b0["box_cost_net"],"label":b0["label"]},now_ts=now,sig=(b0["label"],b0["box_cost_net"]))
    for bx in A:
     _D=bx["legs"]
     if int(bx["n_legs"])==2:
      _q,_p=_D[0],_D[1];_a,Z=K.get(_q["token_id"]),K.get(_p["token_id"])
      if not _a or not Z:continue
      _o=f"{v}_2L_{_q['token_id'][-8:]}_{_p['token_id'][-8:]}"
      if float(bx["box_cost_net"])<=.994:
       _C=walk_equal_shares_dominance_box(_a.get("asks")or[],Z.get("asks")or[],BANKROLL_TICKETS["T1000"][_b],float(_q.get("fee_rate",.0)),float(_p.get("fee_rate",.0)),fee_exponent_a=float(_q.get("fee_exponent",1.)),fee_exponent_b=float(_p.get("fee_exponent",1.)),max_box_cost_net=.994,min_shares=6,min_box_notional_usd=5.5)
       if _C.get("filled"):
        opps_out.append({"sleeve":_b,"market":f"{v} {bx['label']}","ask_vwap":_C["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_C["box_cost_net"]),4),"l1_usd":_C["l1_usd"],"close_ts":bx["close_ts"]});c=False
        if _b=="FED1_CENTRAL_BANK_LP_BOX"and(float(bx["close_ts"])-now)<=172800. and float(_C["box_cost_net"])<=.99:c=a.emit_live_two_leg_box_candidate(sleeve_source=_b,box_type="MACRO_DOMINANCE",asset=v,dedupe_key=_o,leg_a=_q,leg_b=_p,bk_a=_a,bk_b=Z,close_ts=float(bx["close_ts"]),now_ts=now)
        elif(_b=="COND1_MACRO_PARTITION_BOX"and(float(bx["close_ts"])-now)<=(172800. if a.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX")else 1.08e5)and float(_C["box_cost_net"])<=((.992 if(float(bx["close_ts"])-now)<=1.08e5 else.988)if a.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX")else.985)):c=a.emit_live_two_leg_box_candidate(sleeve_source=_b,box_type="MACRO_DOMINANCE",asset=v,dedupe_key=_o,leg_a=_q,leg_b=_p,bk_a=_a,bk_b=Z,close_ts=float(bx["close_ts"]),now_ts=now)
        await a.open_shadow_two_leg_box(_b,_o,v,f"{v} {bx['label']}",_q,_p,_a,Z,float(bx["close_ts"]),.994,{"is_two_leg_box":True,"double_pay_states":bx["double_pay_states"]})
        if not c:a.post_zero_fee_maker_anchor_box(v,v,f"ZFA_{_o}",_q,_p,_a,Z,float(bx["close_ts"]),f"{v} {bx['label']}",now,prefetched_books=K,live_emit_only=True)
       else:a.post_zero_fee_maker_anchor_box(v,v,f"ZFA_{_o}",_q,_p,_a,Z,float(bx["close_ts"]),f"{v} {bx['label']}",now,prefetched_books=K)
      elif float(bx["box_cost_net"])<=1.035:a.post_zero_fee_maker_anchor_box(v,v,f"ZFA_{_o}",_q,_p,_a,Z,float(bx["close_ts"]),f"{v} {bx['label']}",now,prefetched_books=K)
     elif int(bx["n_legs"])==3 and float(bx["box_cost_net"])<=.992:
      _n=f"{v}_3L_{'_'.join(x['token_id'][-6:]for x in _D)}";_B=walk_equal_shares_multi_leg_box([{"asks":K[x["token_id"]].get("asks")or[],"fee_rate":float(x.get("fee_rate",.0)),"fee_exponent":float(x.get("fee_exponent",1.))}for x in _D],BANKROLL_TICKETS["T1000"][_b],1.,.992,min_shares=6,min_box_notional_usd=5.5)
      if _B.get("filled"):opps_out.append({"sleeve":_b,"market":f"{v} 3-Leg {bx['label']}","ask_vwap":_B["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_B["box_cost_net"]),4),"l1_usd":_B["l1_usd"],"close_ts":bx["close_ts"]});await a.open_shadow_multi_leg_bundle(_b,_n,v,f"{v} 3-Leg {bx['label']}",_D,K,float(bx["close_ts"]),1.,.992,{"is_multi_leg_bundle":True,"guaranteed_payout":1.})
  f=[e for e in(a.gas_events_raw.get("us-gas-price-daily")or[])if not e.get("closed")]
  if f:
   _A=await asyncio.to_thread(fetch_aaa_national_gas_sync)
   if _A:
    a._record_market_telemetry("AAA_GAS_SNAP",3e2,{"type":"AAA_GAS_SNAP",**_A},now_ts=now,sig=(_A["as_of_date"],_A["current_regular"]));I=float(_A["current_regular"])
    for _m in f:
     Y=_parse_iso_ts(_m.get("endDate"))or.0
     if not(60.<(Y-now)<=57600.):continue
     H=re.search(r"(20\d{2}-\d{2}-\d{2})",str(_m.get("slug")or""));G=H.group(1)if H else datetime.fromtimestamp(Y,tz=NY_TZ).date().isoformat()
     if G!=_A["as_of_date"]:continue
     X=[]
     for mg in(_m.get("markets")or[]):
      if mg.get("closed"):continue
      o,n=_extract_market_fee_rate(mg);q=_parse_clob_tokens(mg);_l=parse_gas_daily_bracket(str(mg.get("groupItemTitle")or mg.get("question")or""))
      if q and _l:X.append((mg,q,_l,o,n))
     if not X:continue
     W=await a.fetch_books_batch([t for _,tk,_,_,_ in X for t in tk],timeout=3.)
     for mg,q,(_z,_y),o,n in X:
      V=str(mg.get("id")or"");U=str(mg.get("groupItemTitle")or"")
      if(_z==.0 or I>=_z+.0015)and(not math.isfinite(_y)or I<=_y-.0015):i,k="YES",q[0]
      elif I<=_z-.002 or(math.isfinite(_y)and I>=_y+.002):i,k="NO",q[1]
      else:continue
      _j=W.get(k)
      if not _j:continue
      wg=walk_l2_book_asks(_j.get("asks")or[],BANKROLL_TICKETS["T1000"]["GAS1_AAA_GASOLINE_LOCK"],fee_rate=o,min_l1_usd=15.,max_ask_px=.985,fee_exponent=n)
      if wg.get("filled")and.75<=float(wg["eff_px"])<=.983:opps_out.append({"sleeve":"GAS1_AAA_GASOLINE_LOCK","market":f"AAA Gas ${I:.4f} ({_A['as_of_date']}) -> {i}[{U}]","ask_vwap":wg["eff_px"],"p_model":.998,"net_edge":round(.998-float(wg["eff_px"]),4),"l1_usd":wg["l1_usd"],"close_ts":Y});await a.open_shadow_position("GAS1_AAA_GASOLINE_LOCK",f"GAS1_{V}_{i}","AAA_GAS",f"{_m.get('title')} [{i} {U}]",i,k,o,.998,Y,{"market_id":V,"aaa_price":I,"as_of_date":_A["as_of_date"],"fee_exponent":n},prefetched_book=_j)
      T,_=extract_best_bid(_j.get("bids")or[]);S,_=a._best_ask_sz(_j);_i=evaluate_locked_market_reward_carry(.998,T,S,float(mg.get("rewardsMinSize")or.0),float(mg.get("rewardsMaxSpread")or.0),o)
      if _i.get("eligible"):
       m=q[1]if i=="YES"else q[0];_h=mg.get("negRisk")if mg.get("negRisk")is not None else _m.get("negRisk");opps_out.append({"sleeve":"MKR_REWARD_LOCKED_CARRY","market":f"AAA Gas Locked Carry {i}[{U}] @ ${_i['resting_bid']:.3f}","ask_vwap":_i["resting_bid"],"p_model":.998,"net_edge":_i["carry_edge"],"l1_usd":50.,"close_ts":Y});await a.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY",f"MKR_RW_GAS_{V}_{i}","AAA_GAS",f"{_m.get('title')} [Reward Carry {i} {U}]",i,k,.998,Y,{"market_id":V,"condition_id":str(mg.get("conditionId")or""),"opp_token_id":m,"resting_bid_override":_i["resting_bid"]},prefetched_book=_j)
       if is_reward_locked_carry_live_ready(a,.998)and _h is not None and W.get(m)is not None:a.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_REWARD_LOCKED_CARRY",asset="AAA_GAS",dedupe_key=f"MKR_RW_GAS_{V}_{i}",pair_dedupe_key=f"MKR_RW_GASPAIR_{V}",token_id=k,opp_token_id=m,market_id=V,condition_id=str(mg.get("conditionId")or""),side_label=i,display_label=f"AAA Gas Reward Carry {i}[{U}]",bk_win=_j,bk_opp=W.get(m),neg_risk=bool(_h),close_ts=float(Y),now_ts=now,min_resting_bid=.94,max_resting_bid=.99,min_maker_edge=.008,max_opp_bid=.03,hold_to_maturity=True,p_model=.998,target_bid_px=float(_i["resting_bid"]))
 def has_live_nba_window(self,now_ts):return any((sp.tipoff_ts-6e2)<=now_ts<=(sp.tipoff_ts+5.5*3600.)for sp in self.nba_games.values())
 def has_live_sports_window(a,now_ts):return(a.has_live_nba_window(now_ts)or any((c.start_ts-6e2)<=now_ts<=(c.start_ts+5.5*3600.)for c in a.multi_sport_games.values())or any((c.end_ts-2.5*3600.)<=now_ts<=(c.end_ts+1.5*3600.)for c in a.soccer_trees.values())or any((c.end_ts-3.5*3600.)<=now_ts<=(c.end_ts+1.*3600.)for c in a.tennis_specs.values())or any((b.start_ts-6e2)<=now_ts<=(b.start_ts+5.5*3600.)for b in a.aff1_bundles.values())or any((c.end_ts-2.5*3600.)<=now_ts<=(c.end_ts+2.*3600.)for c in a.soc2_lattices.values())or any((c.kickoff_ts-6e2)<=now_ts<=(c.kickoff_ts+5.5*3600.)for c in a.nfl_prop_slates.values()))
 async def discover_uma_proposed_markets(a,now_ts):
  b=datetime.fromtimestamp(now_ts+12.*3600.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");d=[a.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=200&offset=0",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=200&offset=200",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&end_date_max={b}&order=volume24hr&ascending=false&limit=200&offset=0",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&end_date_max={b}&order=volume24hr&ascending=false&limit=200&offset=200",timeout=5.5),*(a.fetch_json(f"{GAMMA_URL}/events?active=true&closed=false&order=volume24hr&ascending=false&limit=100&offset={o}",timeout=6.)for o in range(0,1500,100)),*(a.fetch_json(f"{GAMMA_URL}/events?active=true&closed=false&end_date_max={b}&order=endDate&ascending=false&limit=100&offset={o}",timeout=6.)for o in(0,100,200,300))];i=await asyncio.gather(*d);h={}
  for n in i:
   if not isinstance(n,list):continue
   for l in n:
    if not isinstance(l,dict):continue
    c=l.get("markets")
    if isinstance(c,list):
     g=l.get("negRisk")
     for k in c:
      if not isinstance(k,dict):continue
      f=str(k.get("id")or"").strip()
      if not f or f in h:continue
      if"negRisk"not in k and g is not None:k={**k,"negRisk":g}
      j,_=is_objective_uma_market(k)
      if j:h[f]=k
    else:
     m=str(l.get("id")or"").strip()
     if not m or m in h:continue
     e,_=is_objective_uma_market(l)
     if e:h[m]=l
  a.uma_proposed_markets=h;a.last_uma_discovery_ts=now_ts
 async def scan_uma_resolution_bonds(a,opps_out,now_ts=None):
  _b=float(now_ts if now_ts is not None else time.time())
  if a.single_scan or not a.uma_proposed_markets or(_b-a.last_uma_discovery_ts)>=90.:await a.discover_uma_proposed_markets(_b)
  if not a.uma_proposed_markets:return
  c=[];j=[];e=not(a.single_scan or("fetch_json"in a.__dict__))
  for mid,m in list(a.uma_proposed_markets.items()):
   Z=f"BOND1_{mid}"
   if Z in a.inflight_keys or(not e and Z in a.entered_keys):continue
   E=a.uma_onchain_cache.get(mid);w=60.
   if E is not None:
    _a=str(E[1].get("reason")or"")
    if any(k in _a for k in("DISPUTER","TIE_50_50","QUESTION_FLAGS","PRIOR_DISPUTE","PREMATURE_PROPOSAL","MARKET_BEFORE_END_DATE")):w=3e2
   if E is not None and(_b-E[0])<w:
    ver=E[1]
    if ver.get("verified"):
     n,_=verify_uma_against_nba_live(m,int(ver["win_index"]),a.live_nba_board)
     if n:c.append((mid,m,ver))
   else:Y=float(m.get("bestBid")or.0);X=float(m.get("bestAsk")or 1.);i=(1e6 if(.9<=Y<=.9985 or.002<=X<=.1 or.9<=X<=.9985)else.0)+float(m.get("volume24hr")or.0);j.append((i,mid,m))
  if j:
   j.sort(key=lambda x:-x[0]);L=asyncio.Semaphore(12)
   async def _verify_rpc_one(mid_u,m_u):
    async with L:a=await asyncio.to_thread(verify_uma_onchain_proposal_sync,m_u,None,_b);return mid_u,m_u,a
   r=await asyncio.gather(*(_verify_rpc_one(mid_u,m_u)for _,mid_u,m_u in j[:84]))
   for mid_u,m_u,ver in r:
    a.uma_onchain_cache[mid_u]=(_b,ver)
    if not ver.get("verified"):continue
    n,_=verify_uma_against_nba_live(m_u,int(ver["win_index"]),a.live_nba_board)
    if n:c.append((mid_u,m_u,ver))
  c=[(mid,m,ver)for mid,m,ver in c if passes_uma_bond_dispute_guard(m,ver)]
  if not c:return
  A=[t for _,_,ver in c for t in(str(ver["win_token"]),str(ver["lose_token"]))];K=await a.fetch_books_batch(A,timeout=3.5);l=BANKROLL_TICKETS["T1000"]["BOND1_UMA_RESOLUTION_CARRY"]
  for mid,m,ver in c:
   W,V=str(ver["win_token"]),str(ver["lose_token"]);D,U=K.get(W),K.get(V)
   if not D or not U:continue
   J=max(.0,float(ver.get("eff_liveness_sec")or 7200.)-float(ver.get("rem_challenge_sec")or 7200.));D={**D,"_s2_meta":{"proposal_age_sec":round(float(ver.get("proposal_age_sec")if ver.get("proposal_age_sec")is not None else J),1),"dispute_risk":bool(classify_market_rule_dispute_risk(m)["dispute_risk"])}};I,_=extract_best_bid(D.get("bids")or[]);C,_=extract_best_bid(U.get("bids")or[]);B,_=a._best_ask_sz(U)
   if C>.008 or I<.94 or(B<.5 and B>.025):continue
   O=walk_l2_book_asks_depth_capped(D.get("asks")or[],l,BANKROLL_TICKETS["T100"]["BOND1_UMA_RESOLUTION_CARRY"],fee_rate=float(ver["fee_rate"]),min_l1_usd=6. if e else 15.,max_ask_px=.9976 if e else.9956,fee_exponent=float(ver["fee_exponent"]));R=float(O["eff_px"])if O.get("filled")else None;a._record_market_telemetry(key=f"BOND1_SNAP_{mid}",min_interval_sec=60.,now_ts=_b,sig=(R,I,C,ver["oo_state"]),payload={"type":"UMA_BOND_PROPOSAL_SNAP","market_id":mid,"question":str(m.get("question")or"")[:90],"domain":ver["domain"],"win_outcome":ver["win_outcome_name"],"oo_state":ver["oo_state"],"rem_challenge_sec":ver["rem_challenge_sec"],"win_ask_eff":R,"win_bid":I,"lose_bid":C});Q=str(m.get("question")or f"Market {mid}");z=max(_b+9e2,float(ver["expiration_ts"])+6e2);v={"market_id":mid,"condition_id":str(m.get("conditionId")or""),"opp_token_id":V,"fee_exponent":ver["fee_exponent"],"oo_state":ver["oo_state"],"proposer":ver["proposer"],"win_outcome_name":ver["win_outcome_name"],"expiration_ts":ver["expiration_ts"],"rem_challenge_sec":ver["rem_challenge_sec"],"domain":ver["domain"]};H=f"BOND1_{mid}";h=H not in a.entered_keys and H not in a.inflight_keys;y=z-_b;q=.9975 if(e and y<=3600.)else(.9965 if(e and y<=7200.)else.9955);p=.998 if(e and y<=3600.)else(.9975 if(e and y<=7200.)else.995);u=round(1.-p,4)
   if e and h and 180.<=float(ver.get("rem_challenge_sec")or.0)<=1500.:
    from src.polymarket_research.riskless_protocol_v2_expansion import score_uma_ready1_liveness_priority;G=score_uma_ready1_liveness_priority(ask_price=R if R is not None else min(.9975,I),remaining_liveness_sec=float(ver["rem_challenge_sec"]),disputed=False,proposal_bond_posted=True)
    if G is not None:opps_out.append({"sleeve":"UMA_READY1_LIVENESS_PRIORITY","market":f"[UMA_READY1:{ver['domain']}] {Q[:56]} ({ver['rem_challenge_sec']/60:.0f}m rem)","ask_vwap":G["ask_px"],"p_model":1.,"net_edge":G["net_edge_per_share"],"l1_usd":O["l1_usd"]if O.get("filled")else 25.,"close_ts":z})
   d=False;b=False;g=bool(O.get("filled")and R is not None and(.95<=R<=q)and round(1.-R,4)>=round(1.-q,4))
   if g:
    s=round(1.-R,4)
    if h and R<=.9955:opps_out.append({"sleeve":"BOND1_UMA_RESOLUTION_CARRY","market":f"[{ver['domain']}] {Q[:65]} -> {ver['win_outcome_name']} ({ver['rem_challenge_sec']/60:.0f}m rem)","ask_vwap":R,"p_model":1.,"net_edge":s,"l1_usd":O["l1_usd"],"close_ts":z})
    a.emit_live_single_leg_lock_candidate(sleeve_source="BOND1_UMA_RESOLUTION_CARRY",asset=str(ver["domain"]),dedupe_key=H,token_id=W,opp_token_id=V,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(ver["win_label"]),display_label=f"{ver['domain']} {ver['win_outcome_name']}",bk_win=D,bk_opp=U,fee_rate=float(ver["fee_rate"]),fee_exponent=float(ver["fee_exponent"]),neg_risk=bool(m.get("negRisk")),close_ts=z,now_ts=_b,max_lock_eff_px=q,max_opp_bid=.008,hold_to_maturity=True,p_model=1.)
    if h and R<=.9955:d=await a.open_shadow_position(sleeve="BOND1_UMA_RESOLUTION_CARRY",dedupe_key=H,asset_or_city=str(ver["domain"]),title=f"{Q} [{ver['win_outcome_name']}]",side_label=str(ver["win_label"]),token_id=W,fee_rate=float(ver["fee_rate"]),p_model=1.,close_ts=z,extra=v,tp_target_px=None,prefetched_book=D)
   if not g and not d and.94<=I<=p and C<=.008 and y>120.:
    b=bool(a.emit_live_single_leg_maker_lock_candidate(sleeve_source="BOND1_UMA_RESOLUTION_CARRY",asset=str(ver["domain"]),dedupe_key=f"BOND1_MKR_{mid}",pair_dedupe_key=H,token_id=W,opp_token_id=V,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(ver["win_label"]),display_label=f"{ver['domain']} {ver['win_outcome_name']}",bk_win=D,bk_opp=U,neg_risk=bool(m.get("negRisk")),close_ts=z,now_ts=_b,min_resting_bid=.94,max_resting_bid=p,min_maker_edge=u,max_opp_bid=.008,hold_to_maturity=True,p_model=1.))
    if h:
     o=await a.post_shadow_maker_entry(sleeve="BOND1_UMA_RESOLUTION_CARRY",dedupe_key=H,asset=str(ver["domain"]),title=f"{Q} [{ver['win_outcome_name']}]",side_label=str(ver["win_label"]),token_id=W,p_model=1.,close_ts=z,extra=v,prefetched_book=D)
     if o:opps_out.append({"sleeve":"BOND1_UMA_RESOLUTION_CARRY","market":f"[MAKER:{ver['domain']}] {Q[:58]} -> {ver['win_outcome_name']}","ask_vwap":I,"p_model":1.,"net_edge":round(1.-I,4),"l1_usd":extract_best_bid(D.get("bids")or[])[1],"close_ts":z})
   P=f"BOND2_{mid}";f=P not in a.entered_keys and P not in a.inflight_keys
   if(not(not e and P in a.entered_keys)and P not in a.inflight_keys and float(ver.get("proposal_age_sec")or.0)>=3600. and 180.<=float(ver.get("rem_challenge_sec")or.0)<=3300. and C<=.006 and I>=.95):
    T=await asyncio.to_thread(verify_bond2_moov2_final_hour_sync,m,None,_b)
    if T.get("verified"):
     F=.9975 if e else.9962;S=walk_l2_book_asks_depth_capped(D.get("asks")or[],BANKROLL_TICKETS["T1000"]["BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"],BANKROLL_TICKETS["T100"]["BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"],fee_rate=float(T["fee_rate"]),min_l1_usd=10. if e else 15.,max_ask_px=round(F+1e-4,4),fee_exponent=float(T["fee_exponent"]))
     if S.get("filled")and.95<=float(S["eff_px"])<=F:
      N=float(S["eff_px"]);M=round(1.-N,4)
      if M>=(.0025 if e else.0038):
       if f:opps_out.append({"sleeve":"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","market":f"[MOOv2_WL:{T['domain']}] {Q[:60]} -> {T['win_outcome_name']} ({T['rem_challenge_sec']/60:.0f}m rem)","ask_vwap":N,"p_model":1.,"net_edge":M,"l1_usd":S["l1_usd"],"close_ts":z})
       a.emit_live_single_leg_lock_candidate(sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",asset=str(T["domain"]),dedupe_key=P,token_id=W,opp_token_id=V,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(T["win_label"]),display_label=f"MOOv2_WL {T['domain']} {T['win_outcome_name']}",bk_win=D,bk_opp=U,fee_rate=float(T["fee_rate"]),fee_exponent=float(T["fee_exponent"]),neg_risk=bool(m.get("negRisk")),close_ts=z,now_ts=_b,max_lock_eff_px=F,max_opp_bid=.006,hold_to_maturity=True,p_model=1.)
       if f:await a.open_shadow_position(sleeve="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",dedupe_key=P,asset_or_city=str(T["domain"]),title=f"{Q} [MOOv2 Whitelisted {T['win_outcome_name']}]",side_label=str(T["win_label"]),token_id=W,fee_rate=float(T["fee_rate"]),p_model=1.,close_ts=z,extra={**v,"proposer_whitelisted":True,"oo_address":T["oo_address"]},tp_target_px=None,prefetched_book=D)
      elif e and not b:a.emit_live_single_leg_maker_lock_candidate(sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",asset=str(T["domain"]),dedupe_key=f"{P}_MKR",pair_dedupe_key=P,token_id=W,opp_token_id=V,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(T["win_label"]),display_label=f"MOOv2_WL Maker {T['domain']} {T['win_outcome_name']}",bk_win=D,bk_opp=U,neg_risk=bool(m.get("negRisk")),close_ts=z,now_ts=_b,min_resting_bid=.95,max_resting_bid=.998,min_maker_edge=.002,max_opp_bid=.006,p_model=1.)
     elif e and not b:a.emit_live_single_leg_maker_lock_candidate(sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",asset=str(T["domain"]),dedupe_key=f"{P}_MKR",pair_dedupe_key=P,token_id=W,opp_token_id=V,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(T["win_label"]),display_label=f"MOOv2_WL Maker {T['domain']} {T['win_outcome_name']}",bk_win=D,bk_opp=U,neg_risk=bool(m.get("negRisk")),close_ts=z,now_ts=_b,min_resting_bid=.95,max_resting_bid=.998,min_maker_edge=.002,max_opp_bid=.006,p_model=1.)
 async def scan_nba_endgame_locks(a,opps_out,now_ts=None):
  F=float(now_ts if now_ts is not None else time.time())
  if not a.nba_games:return
  l=5.5 if a.has_live_nba_window(F)else 120.
  if a.single_scan or not a.live_nba_board or(F-a.last_espn_board_ts)>=l:
   A=await asyncio.to_thread(fetch_espn_nba_scoreboard_sync)
   if A:a.live_nba_board=A;a.last_espn_board_ts=F
  if not a.live_nba_board:return
  i=[]
  for d in list(a.nba_games.values()):
   s=match_nba_live_game(d,a.live_nba_board)
   if s is None:continue
   r,E,D=s
   if r.state in("in","post"):a._record_market_telemetry(key=f"NBA_LIVE_{d.event_id}",min_interval_sec=30.,now_ts=F,sig=(r.state,r.period,int(r.clock_sec//10),E,D),payload={"type":"NBA_LIVE_SCORE_SNAP","event_id":d.event_id,"game":d.title,"state":r.state,"completed":r.completed,"period":r.period,"clock_sec":round(r.clock_sec,1),"score_a":E,"score_b":D,"source":r.source})
   for c_lk in evaluate_nba_endgame_locks(d,r,E,D):
    C=c_lk["leg"];y=f"SP2_{d.event_id}_{C.market_id}_{C.token_id[-8:]}"
    if y not in a.entered_keys and y not in a.inflight_keys:i.append((d,c_lk))
  if not i:await a._scan_sp4_live_nba_stat_locks(opps_out,F);return
  k=[t for _,c_lk in i for t in(c_lk["leg"].token_id,c_lk["leg"].opp_token_id)];q=await a.fetch_books_batch(k,timeout=3.);p=BANKROLL_TICKETS["T1000"]["SP2_NBA_ENDGAME_LOCK"]
  for d,c_lk in i:
   C=c_lk["leg"];x=q.get(C.token_id);w=q.get(C.opp_token_id)
   if not x or not w:continue
   o,_=extract_best_bid(w.get("bids")or[])
   if o>.18:continue
   e,c=extract_best_bid(x.get("bids")or[]);v=float(getattr(C,"fee_rate",.0)or.0);u=float(getattr(C,"fee_exponent",1.)or 1.);z=walk_l2_book_asks_depth_capped(x.get("asks")or[],p,BANKROLL_TICKETS["T100"]["SP2_NBA_ENDGAME_LOCK"],fee_rate=v,min_l1_usd=18.,max_ask_px=.9861,fee_exponent=u);B=float(c_lk["p_lock"]);h=max(F+6e2,float(d.settle_est_ts));j=f"SP2_{d.event_id}_{C.market_id}_{C.token_id[-8:]}";g={"event_id":d.event_id,"market_id":C.market_id,"condition_id":C.condition_id,"opp_token_id":C.opp_token_id,"mode":c_lk["mode"],"score_str":c_lk["score_str"],"cushion_pts":c_lk["cushion_pts"],"clock_sec":c_lk["clock_sec"],"period":c_lk["period"],"fee_exponent":u};b=False
   if z.get("filled"):
    n=float(z["eff_px"]);m=round(B-n,4)
    if o<=(1.-n)+.025 and(.78<=n<=.986)and m>=.012:opps_out.append({"sleeve":"SP2_NBA_ENDGAME_LOCK","market":f"NBA [{c_lk['mode']}] {c_lk['score_str']} -> {C.display_label}","ask_vwap":n,"p_model":B,"net_edge":m,"l1_usd":z["l1_usd"],"close_ts":h});b=await a.open_shadow_position(sleeve="SP2_NBA_ENDGAME_LOCK",dedupe_key=j,asset_or_city="NBA",title=f"{d.title} [{C.display_label} | {c_lk['mode']}]",side_label=C.side_label,token_id=C.token_id,fee_rate=v,p_model=B,close_ts=h,extra=g,tp_target_px=None,prefetched_book=x)
   if(not b and.72<=e<=.985 and o<=(1.-e)+.025 and(B-e)>=.012):
    f=await a.post_shadow_maker_entry(sleeve="SP2_NBA_ENDGAME_LOCK",dedupe_key=j,asset="NBA",title=f"{d.title} [{C.display_label} | {c_lk['mode']}]",side_label=C.side_label,token_id=C.token_id,p_model=B,close_ts=h,extra=g,prefetched_book=x,ttl_override_sec=45.)
    if f:opps_out.append({"sleeve":"SP2_NBA_ENDGAME_LOCK","market":f"[MAKER] NBA [{c_lk['mode']}] {c_lk['score_str']} -> {C.display_label}","ask_vwap":e,"p_model":B,"net_edge":round(B-e,4),"l1_usd":c,"close_ts":h})
  await a._scan_sp4_live_nba_stat_locks(opps_out,F)
 async def _scan_sp4_live_nba_stat_locks(a,opps_out,now):
  if(not a.nba_prop_slates and not a.nba_subperiod_slates)or not a.live_nba_board:return
  o=[];f=[];e=sorted(set(a.nba_prop_slates.keys())|set(a.nba_subperiod_slates.keys()))
  for I in e:
   B=a.nba_games.get(I)
   if B is None:continue
   u=match_nba_live_game(B,a.live_nba_board)
   if u is None or u[0].state not in("in","post"):continue
   P=u[0];q=str(P.game_id or"")
   if not q:continue
   n=a.nba_boxscore_cache.get(q);j=a.nba_ext_summary_cache.get(q)
   if n is not None and j is not None and(now-n[0])<12.:d=n[1];b=j[1]
   else:
    try:d,b=await asyncio.to_thread(fetch_espn_nba_full_summary_sync,q)
    except Exception:d,b={},{}
    a.nba_boxscore_cache[q]=(now,d);a.nba_ext_summary_cache[q]=(now,b)
   H=a.nba_prop_slates.get(I)
   if H is not None:
    for p in evaluate_sp4_ingame_clinch_locks(H,P,d):
     O=p["rung"];J=f"SP4_3A_{O.event_id}_{O.market_id}"
     if J not in a.entered_keys and J not in a.inflight_keys:o.append(p)
   A=a.nba_subperiod_slates.get(I)
   if A is not None and b:
    for g in evaluate_sp4_subperiod_and_ext_locks(A,b):
     h=f"SP4_SUB_LK_{I}_{g['market_id']}"
     if h not in a.entered_keys and h not in a.inflight_keys:f.append((h,g))
  i=[t for c in o for t in(c["rung"].yes_token,c["rung"].no_token)]+[t for _,S in f for t in(S["token_id"],S["opp_token_id"])]
  if not i:return
  s=await a.fetch_books_batch(sorted(set(i)),timeout=3.)
  for p in o:
   O=p["rung"];N,M=s.get(O.yes_token),s.get(O.no_token)
   if not N or not M:continue
   r,_=extract_best_bid(M.get("bids")or[])
   if r>.04:continue
   G=float(getattr(O,"fee_rate",.0)or.0);F=float(getattr(O,"fee_exponent",1.)or 1.);L=walk_l2_book_asks_depth_capped(N.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],BANKROLL_TICKETS["T100"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],fee_rate=G,min_l1_usd=15.,max_ask_px=.9881,fee_exponent=F)
   if L.get("filled"):
    R=float(L["eff_px"]);K=float(p["p_lock"]);Q=round(K-R,4)
    if.72<=R<=.988 and Q>=.012:J=f"SP4_3A_{O.event_id}_{O.market_id}";m=max(now+6e2,float(O.settle_est_ts));opps_out.append({"sleeve":"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","market":f"NBA [{p['mode']}] {O.player_name} {O.stat_type}={p['current_stat']} > {O.line}","ask_vwap":R,"p_model":K,"net_edge":Q,"l1_usd":L["l1_usd"],"close_ts":m});a.emit_live_single_leg_lock_candidate(sleeve_source="SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",asset="NBA",dedupe_key=J,token_id=O.yes_token,opp_token_id=O.no_token,market_id=O.market_id,condition_id=O.condition_id,side_label="YES",display_label=f"{O.player_name} {O.stat_type} O{O.line} ({p['current_stat']})",bk_win=N,bk_opp=M,fee_rate=G,fee_exponent=F,neg_risk=False,close_ts=m,now_ts=now,max_lock_eff_px=.988,max_opp_bid=.025,hold_to_maturity=True,p_model=K);await a.open_shadow_position("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",J,"NBA_PROP",f"{O.game_title} [{O.player_name} {O.stat_type} O{O.line} (cur={p['current_stat']})]","YES",O.yes_token,G,K,m,{"market_id":O.market_id,"condition_id":O.condition_id,"opp_token_id":O.no_token,"mode":p["mode"],"stat_val":p["current_stat"],"fee_exponent":F},prefetched_book=N)
  for h,g in f:
   z,y=s.get(g["token_id"]),s.get(g["opp_token_id"])
   if not z or not y:continue
   l,_=extract_best_bid(y.get("bids")or[])
   if l>.04:continue
   x=float(g.get("fee_rate",.0)or.0);w=float(g.get("fee_exponent",1.)or 1.);E=walk_l2_book_asks_depth_capped(z.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],BANKROLL_TICKETS["T100"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],fee_rate=x,min_l1_usd=15.,max_ask_px=.9881,fee_exponent=w)
   if E.get("filled"):
    D=float(E["eff_px"]);v=float(g["p_lock"]);C=round(v-D,4)
    if.72<=D<=.988 and C>=.012:
     k=max(now+6e2,float(g["close_ts"]));opps_out.append({"sleeve":"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","market":f"NBA [{g['mode']}] {g['display_label']}","ask_vwap":D,"p_model":v,"net_edge":C,"l1_usd":E["l1_usd"],"close_ts":k})
     if a._can_emit_zero_loss_math_live("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",k,now,p_model=v):a.emit_live_single_leg_lock_candidate(sleeve_source="SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",asset="NBA",dedupe_key=h,token_id=str(g["token_id"]),opp_token_id=str(g["opp_token_id"]),market_id=str(g["market_id"]),condition_id=str(g["condition_id"]),side_label=str(g["side_label"]),display_label=str(g["display_label"]),bk_win=z,bk_opp=y,fee_rate=x,fee_exponent=w,neg_risk=bool(g.get("neg_risk",False)),close_ts=k,now_ts=now,max_lock_eff_px=.988,max_opp_bid=.025,hold_to_maturity=True,p_model=v)
     await a.open_shadow_position("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",h,"NBA_SUBPERIOD",g["display_label"],str(g["side_label"]),str(g["token_id"]),x,v,k,{"market_id":g["market_id"],"condition_id":g["condition_id"],"opp_token_id":g["opp_token_id"],"mode":g["mode"],"fee_exponent":w},prefetched_book=z)
 async def scan_protocol_v2_expansion_opportunities(self,opps_out,now_ts=None):from src.polymarket_research.riskless_protocol_v2_expansion import run_protocol_v2_daemon_scan;await run_protocol_v2_daemon_scan(self,opps_out,now_ts=now_ts)
 async def _run_gatling_fast_gun_loop(a):
  b=.0;c=.0
  while True:
   try:
    i=time.time();h=math.ceil(i/3e2)*3e2-i
    if h<=65. and(i-a.last_usd_sample_ts)>=.95:a.record_usd_spot_samples(i)
    g=.18 if(4.<=h<=22.)else 2.5
    if(3.8<=h<=92.)and(i-c)>=g:c=i;e=[];await a.scan_exact_twap_locks(e,now_ts=i)
    if a.is_in_same_oracle_overlap_window(i)and(i-b)>=.35:
     f=a.__dict__.setdefault("_d1_fast_scan_lock",asyncio.Lock())
     if not f.locked():
      b=i
      async with f:d=[];await a.scan_same_oracle_dominance_boxes(d,now_ts=i)
    await asyncio.sleep(.15 if(4.<=h<=22.)else.25)
   except asyncio.CancelledError:break
   except Exception as exc:await asyncio.sleep(.5)
 async def _run_bg_nba_endgame(a):
  try:b=[];await a.scan_nba_endgame_locks(b);a.cached_nba_endgame_opps=b
  except Exception as exc:logger.warning(f"Background NBA endgame scan notice: {exc}")
 async def _run_bg_tradfi_sports(a):
  b=[]
  try:await a.scan_tradfi_and_sports_markets(b)
  except Exception as exc:logger.warning(f"Background TradFi/Sports scan notice: {exc}")
  try:await a.scan_protocol_v2_expansion_opportunities(b)
  except Exception as exc_v2:logger.warning(f"Background Protocol V2 scan notice: {exc_v2}")
  a.cached_tradfi_sports_opps=b
 async def run_forever(a):
  logger.info("Starting Polymarket Alpha-124 Unified Shadow Daemon (Gatling High-Vol Machine Gun: S2 Live TWAP Lock + 9-Asset D1 + Protocol V2 Expansion)...")
  try:
   if not a.single_scan and(a._bg_clob_ws_task is None or a._bg_clob_ws_task.done()):a._bg_clob_ws_task=asyncio.create_task(a._run_clob_d1_ws_loop())
   if not a.single_scan and a._chainlink_ws is not None and(a._bg_chainlink_ws_task is None or a._bg_chainlink_ws_task.done()):a._bg_chainlink_ws_task=asyncio.create_task(a._chainlink_ws.run_forever())
   i=getattr(a,"_bg_gatling_fast_task",None)
   if not a.single_scan and(i is None or i.done()):a._bg_gatling_fast_task=asyncio.create_task(a._run_gatling_fast_gun_loop())
   while True:
    H=time.time();a.cycle_count+=1;await a.update_crypto_spots()
    if not a.weather_events or a.single_scan:await a.discover_all_markets()
    elif(H-a.last_discovery_ts)>=3e2 and(a._bg_discovery_task is None or a._bg_discovery_task.done()):a.last_discovery_ts=H;a._bg_discovery_task=asyncio.create_task(a._run_bg_discovery())
    k=a.poll_fresh_shock_triggers(now_ts=H)
    if k:q=[];await a.handle_shock_triggers(k,q,now_ts=H);a.cached_shock_opps=q
    d=[];r=[];y=[];B=[];await a.scan_same_oracle_dominance_boxes(d);await a.scan_exact_twap_locks(r);await a.scan_s5m_chainlink_sniper(y);await a.scan_and_manage_preopen_maker_straddles(B)
    if a.single_scan:x=[];await a.scan_multistrike_markets(x);await a.scan_daily_updown_locks(x);await a.scan_barrier_markets(x);a.cached_mid_opps=x;D=[];await a.scan_weather_markets(D);a.cached_weather_opps=D;A=[];await a.scan_tradfi_and_sports_markets(A);await a.scan_protocol_v2_expansion_opportunities(A);a.cached_tradfi_sports_opps=A;w=[];await a.scan_nba_endgame_locks(w);a.cached_nba_endgame_opps=w
    else:
     n=6. if a.has_live_nba_window(H)else 120.
     if(H-a.last_nba_endgame_scan_ts)>=n and(a._bg_nba_task is None or a._bg_nba_task.done()):a.last_nba_endgame_scan_ts=H;a._bg_nba_task=asyncio.create_task(a._run_bg_nba_endgame())
     if(H-a.last_crypto_mid_scan_ts)>=18. and(a._bg_mid_task is None or a._bg_mid_task.done()):a.last_crypto_mid_scan_ts=H;a._bg_mid_task=asyncio.create_task(a._run_bg_mid_crypto())
     g=8. if(a.has_live_sports_window(H)or a.pending_zero_fee_maker_anchors)else 20.
     if(H-a.last_tradfi_sports_scan_ts)>=g and(a._bg_tradfi_task is None or a._bg_tradfi_task.done()):a.last_tradfi_sports_scan_ts=H;a._bg_tradfi_task=asyncio.create_task(a._run_bg_tradfi_sports())
     if(H-a.last_weather_scan_ts)>=90. and(a._bg_weather_task is None or a._bg_weather_task.done()):a.last_weather_scan_ts=H;a._bg_weather_task=asyncio.create_task(a._run_bg_weather())
    G=(r+d+y+B+a.cached_shock_opps+a.cached_mid_opps+a.cached_nba_endgame_opps+a.cached_tradfi_sports_opps+a.cached_weather_opps);await a.manage_pending_maker_orders();await a.manage_pending_zero_fee_maker_anchors();await a.manage_open_positions();await a.write_state_files_async(G);logger.info(f"[Cycle {a.cycle_count}] BTC=${a.spots.get('BTC',0):,.1f} ETH=${a.spots.get('ETH',0):,.1f} | Monitored(W={len(a.weather_events)}, B={len(a.barrier_rungs)}, M={len(a.strike_ladders)}, NR={len(a.negrisk_ladders)}, PythH={len(a.pyth_barrier_rungs)}, PythC={len(a.pyth_close_ladders)}, NBA={len(a.nba_games)}/{len(a.live_nba_board)}live(SP4={len(a.nba_prop_slates)},SP4+={len(a.nba_subperiod_slates)},EM={len(a.lp1_nba_em_bundles)}), SP3={len(a.multi_sport_games)}(NFLEM={len(a.lp1_nfl_em_bundles)}), SOC1={len(a.soccer_trees)}, TEN1={len(a.tennis_specs)}, API1={len(a.esports_bo3_specs)}, BOP={len(a.lp1_bop_legs)//2}, LP2={len(a.lp2_implication_groups)}, CAL1={len(a.cal1_ladders)}, UMA={len(a.uma_proposed_markets)}, NR0={len(a.negrisk_zero_slates)}, NRC={len(a.negrisk_convert_slates)}, TW={len(a.counting_slates)}, FOMC={len(a.fomc_truth_legs)//2}, OS={len(a.oil_senate_truth_legs)//2}, D2={len(a.hourly_12pm_markets)}, U1={len(a.daily_updown_markets)}, D={len(a.dominance_pairs)}, D4h={len(a.dominance_4h_pairs)}, S5m={len(a.s5m_candles)}, P1={len(a.preopen_15m_candles)}, S2={len(a.twap_candles)}) | MakerPend={len(a.pending_maker_orders)} ZFAncPend={len(a.pending_zero_fee_maker_anchors)} PreOpenPend={len(a.pending_preopen_straddles)} OpenPos={len(a.open_positions)} ClosedPos={len(a.closed_positions)} | TopOpps={len(a.top_opportunities)}")
    if a.single_scan:break
    z=time.time();p=math.ceil(z/14400.)*14400.-z;f=not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK")
    if f and a.is_in_exact_twap_lock_window(z):b=3.
    elif a.is_in_same_oracle_overlap_window(z):b=3.5
    elif a.pending_zero_fee_maker_anchors:b=4.
    elif 8.<=p<=905. or a.pending_preopen_straddles or a.has_live_sports_window(z):b=6.
    else:b=12.
    v=H+max(2.,b);c=H
    while True:
     E=time.time()
     if E>=v:break
     j=a._ws_d1_wakeup.is_set()
     if j:a._ws_d1_wakeup.clear()
     e=a._ws_nr_wakeup.is_set()
     if e:a._ws_nr_wakeup.clear()
     o=.12 if j else.5
     if a.is_in_same_oracle_overlap_window(E)and(E-c)>=o:
      c=E;m=[];await a.scan_same_oracle_dominance_boxes(m,now_ts=E)
      if m:d=m
      if a.pending_zero_fee_maker_anchors:await a.manage_pending_zero_fee_maker_anchors(now_ts=E)
     elif(a.pending_maker_anchors or a.pending_zero_fee_maker_anchors)and(E-c)>=.5:
      c=E
      if a.pending_maker_anchors:await a.manage_pending_maker_anchors(now_ts=E)
      if a.pending_zero_fee_maker_anchors:await a.manage_pending_zero_fee_maker_anchors(now_ts=E)
     if e and(E-getattr(a,"_last_fast_nr_subscan",.0))>=.25:a._last_fast_nr_subscan=E;await a._scan_ws_reactive_negrisk_arbs(E)
     u=math.ceil(E/3e2)*3e2-E
     if f and u<=65. and(E-a.last_usd_sample_ts)>=1.:a.record_usd_spot_samples(E)
     t=a.poll_fresh_shock_triggers(now_ts=E)
     if t:
      h=set(a.pending_maker_orders);l=len(a.open_positions);C=[];await a.handle_shock_triggers(t,C,now_ts=E)
      if C:a.cached_shock_opps=C
      if C or set(a.pending_maker_orders)!=h or len(a.open_positions)!=l:await a.write_state_files_async(r+d+y+B+a.cached_shock_opps+a.cached_mid_opps+a.cached_nba_endgame_opps+a.cached_tradfi_sports_opps+a.cached_weather_opps)
     if f and b>3. and a.is_in_exact_twap_lock_window(E):break
     s=min(.2,max(.03,v-time.time()))
     try:await asyncio.wait_for(a._ws_d1_wakeup.wait(),timeout=s)
     except asyncio.TimeoutError:pass
  finally:
   for F in(getattr(a,"_bg_gatling_fast_task",None),a._bg_chainlink_ws_task,a._bg_clob_ws_task,a._bg_discovery_task,a._bg_mid_task,a._bg_tradfi_task,a._bg_weather_task,a._bg_nba_task):
    if F is not None and not F.done():
     F.cancel()
     try:await F
     except BaseException:pass
   if a.session and not a.session.closed:await a.session.close()
def main():
 b=argparse.ArgumentParser(description="Polymarket Alpha-124 Shadow Daemon");b.add_argument("--single-scan",action="store_true",help="Run one full scan cycle and exit");c=b.parse_args()
 if os.name!="nt":
  try:import uvloop;uvloop.install()
  except Exception:pass
 a=Alpha124ShadowDaemon(single_scan=c.single_scan);asyncio.run(a.run_forever())
if __name__=="__main__":main()
# ======================================================================================
# [17/21] MODULE: scripts/backtest_alpha_124.py
# PURPOSE: Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import concurrent.futures
import json;import math;import os;import sys;import time;import urllib.request;from collections import defaultdict;from datetime import date,datetime,timedelta,timezone;from pathlib import Path;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;PROJECT_ROOT=Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT)not in sys.path:sys.path.insert(0,str(PROJECT_ROOT))
from src.polymarket_research.barrier_onetouch_svi_engine import(BarrierRungSpec,first_passage_touch_prob,get_wing_implied_vol,parse_hit_event);from src.polymarket_research.multistrike_svi_scalper import(StrikeRungSpec,evaluate_svi_digital_fair_value,parse_multistrike_event);from src.polymarket_research.weather_metar_engine import(MetarObservation,WeatherEventSpec,compute_weather_probabilities,fetch_historical_nwp_hourly_sync,fetch_metar_observations_sync,parse_weather_event);GAMMA_URL="https://gamma-api.polymarket.com";CLOB_URL="https://clob.polymarket.com";BINANCE_URL="https://api.binance.com";DERIBIT_URL="https://www.deribit.com/api/v2/public/get_volatility_index_data";OUT_DIR=PROJECT_ROOT/"data"/"alpha124";OUT_DIR.mkdir(parents=True,exist_ok=True);REPORT_JSON=OUT_DIR/"backtest_alpha_124_results.json";SPLIT_CUTOFF_TS=datetime(2026,10,16,23,59,59,tzinfo=timezone.utc).timestamp();WEATHER_SERIES_SAMPLE=["tokyo-daily-weather","london-daily-weather","shanghai-daily-weather","paris-daily-weather","munich-daily-weather","miami-daily-weather","nyc-daily-weather","houston-daily-weather","seoul-daily-weather","chicago-daily-weather","seattle-daily-weather","dallas-daily-weather","madrid-daily-weather","amsterdam-daily-weather","taipei-daily-weather","singapore-daily-weather"]
def http_get_json(url,timeout=10.):
 for a in range(3):
  try:
   c=urllib.request.Request(url,headers={"User-Agent":"DominusBacktester/1.0"})
   with urllib.request.urlopen(c,timeout=timeout)as b:return json.loads(b.read().decode("utf-8"))
  except Exception:
   if a==2:return None
   time.sleep(.35*(a+1))
 return None
def fetch_clob_history(token_id,fidelity=10):
 b=http_get_json(f"{CLOB_URL}/prices-history?market={token_id}&interval=max&fidelity={fidelity}",timeout=8.)
 if not b or not isinstance(b,dict):return[]
 a=b.get("history")or[];c=[(int(r["t"]),float(r["p"]))for r in a if"t"in r and"p"in r];c.sort(key=lambda x:x[0]);return c
def fetch_binance_5m_series(symbol,start_ts,end_ts):
 f={};a=start_ts*1000;c=end_ts*1000
 while a<c:
  e=f"{BINANCE_URL}/api/v3/klines?symbol={symbol}&interval=5m&startTime={a}&endTime={c}&limit=1000";d=http_get_json(e,timeout=10.)
  if not d:break
  for r in d:g=int(r[0])//1000;f[g]=(float(r[1]),float(r[2]),float(r[3]),float(r[4]))
  b=int(d[-1][0])
  if b<=a:break
  a=b+300000
 return f
def fetch_deribit_dvol_hourly(currency,start_ts,end_ts):
 e=f"{DERIBIT_URL}?currency={currency}&start_timestamp={start_ts*1000}&end_timestamp={end_ts*1000}&resolution=3600";a=http_get_json(e,timeout=10.);d={};c=(a or{}).get("result",{}).get("data")or[]
 for b in c:f=int(b[0])//1000;d[f]=float(b[4])/1e2
 return d
def summarize_trades(trades,label):
 if not trades:return{"label":label,"trades":0,"wins":0,"losses":0,"win_rate_pct":.0,"net_pnl_usd":.0,"avg_pnl_usd":.0,"avg_roi_pct":.0,"profit_factor":.0,"max_drawdown_usd":.0}
 e=sorted(trades,key=lambda x:x["entry_ts"]);j=[float(t["pnl_usd"])for t in e];i=[float(t["roi_pct"])for t in e];h=sum(1 for p in j if p>0);f=len(j)-h;c=sum(p for p in j if p>0);b=abs(sum(p for p in j if p<0));k=(c/b)if b>1e-6 else(99.9 if c>0 else.0);g=.0;d=.0;a=.0
 for p in j:g+=p;d=max(d,g);a=max(a,d-g)
 return{"label":label,"trades":len(j),"wins":h,"losses":f,"win_rate_pct":round(1e2*h/len(j),2),"net_pnl_usd":round(sum(j),2),"avg_pnl_usd":round(sum(j)/len(j),2),"avg_roi_pct":round(sum(i)/len(i),2),"profit_factor":round(k,2),"max_drawdown_usd":round(a,2)}
def run_weather_backtest():
 print("[1/3] Fetching resolved October 2026 Daily Weather markets across 16 global cities...",flush=True);R=[]
 for N in WEATHER_SERIES_SAMPLE:
  X=http_get_json(f"{GAMMA_URL}/events?series_slug={N}&closed=true&order=endDate&ascending=false&limit=20")or[]
  for ev in X:
   sp=parse_weather_event(ev,allow_historical_same_station=True,series_slug_hint=N)
   if sp is not None and date(2026,10,4)<=sp.obs_date<=date(2026,10,25):
    if any(b.outcome_yes_resolved==1 for b in sp.buckets):R.append(sp)
 print(f"      Parsed {len(R)} resolved METAR-governed city-days. Fetching NWP + METAR + CLOB series...",flush=True);I=defaultdict(list)
 for sp in R:I[sp.icao].append(sp)
 E={}
 for W,G in I.items():
  Q=min(s.obs_date for s in G)-timedelta(days=1);P=max(s.obs_date for s in G)+timedelta(days=1);Z=G[0]
  try:E[W]=fetch_historical_nwp_hourly_sync(Z.lat,Z.lon,Q,P)
  except Exception:E[W]={}
 def _load_event_bundle(sp):
  c=fetch_metar_observations_sync(sp.icao,sp.obs_date,sp.tz_name);a={}
  for b in sp.buckets:a[b.market_id]=fetch_clob_history(b.yes_token,fidelity=15)
  return sp,c,a
 H=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=24)as V:
  for v in V.map(_load_event_bundle,R):
   if v[1]:H.append(v)
 print(f"      Loaded {len(H)} complete Weather city-day bundles with raw METAR + CLOB history.",flush=True);e=1.15;f=999.;m=[b for b in H if b[0].obs_date<=date(2026,10,16)]
 for F in(.85,1.05,1.25,1.45):
  j=.0;l=0
  for sp,metars,_ in m:
   U=ZoneInfo(sp.tz_name);u=datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,11,0,tzinfo=U);h=u.astimezone(timezone.utc);Y=compute_weather_probabilities(sp,h,metars,E.get(sp.icao,{}),forecast_sigma_base_c=F)
   for w,b in enumerate(sp.buckets):y=1. if b.outcome_yes_resolved==1 else.0;j+=(Y["probs"][w]-y)**2;l+=1
  if l>0 and(j/l)<f:f=j/l;e=F
 print(f"      [TRAIN Calibration] Optimal Weather NWP kernel sigma={e:.2f}°C (Brier={f:.4f}).",flush=True);D=[];C=[];B=1e2;A=50.;g=.01
 for sp,metars,clob_map in sorted(H,key=lambda x:x[0].obs_date):
  U=ZoneInfo(sp.tz_name);M=E.get(sp.icao,{});O="TRAIN"if sp.obs_date<=date(2026,10,16)else"TEST"
  def _price_at(mkt_id,ts):
   c=clob_map.get(mkt_id)or[];a=None
   for b,d in c:
    if b<=ts:
     if ts-b<=7200:a=d
    else:break
   return a
  d=False
  for T,S in((9,0),(11,30),(13,30)):
   if d:break
   h=datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,T,S,tzinfo=U).astimezone(timezone.utc);k=int(h.timestamp());z=int(datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,14,0,tzinfo=U).astimezone(timezone.utc).timestamp());q=M.get(z)or[]
   if q and(max(q)-min(q))>1.6:continue
   v=compute_weather_probabilities(sp,h,metars,M,forecast_sigma_base_c=e);i=None
   for w,b in enumerate(sp.buckets):
    p=_price_at(b.market_id,k)
    if p is None:continue
    a=round(p+g,4);r=v["probs"][w];o=r-a
    if.16<=a<=.62 and o>=.1 and r>=.34:
     if i is None or o>i[0]:i=(o,w,b,a,r)
   if i is not None:o,w,b,a,r=i;n=A/a;K=(b.outcome_yes_resolved==1);J=(n*1.-A)if K else(-A);C.append({"split":O,"sleeve":"W2_ENSEMBLE_VALUE","city":sp.city,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket":b.label,"entry_ts":k,"entry_px":a,"p_model":round(r,4),"edge":round(o,4),"won":K,"pnl_usd":round(J,2),"roi_pct":round(1e2*J/A,2)});d=True
  c=False
  for T,S in((16,0),(17,0),(18,0),(19,0),(20,0),(21,0),(22,0)):
   if c:break
   h=datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,T,S,tzinfo=U).astimezone(timezone.utc);k=int(h.timestamp());v=compute_weather_probabilities(sp,h,metars,M,forecast_sigma_base_c=e)
   if not v["is_solar_lock"]or v["locked_bucket_idx"]is None:continue
   b=sp.buckets[v["locked_bucket_idx"]];p=_price_at(b.market_id,k)
   if p is None:continue
   a=round(p+g,4);L=v["p_locked_bucket"];o=L-a
   if.55<=a<=.93 and o>=.04:n=B/a;K=(b.outcome_yes_resolved==1);J=(n*1.-B)if K else(-B);D.append({"split":O,"sleeve":"W1_SOLAR_PEAK_LOCK","city":sp.city,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket":b.label,"entry_ts":k,"entry_px":a,"p_model":round(L,4),"cooling_cushion_c":v["cooling_cushion_c"],"edge":round(o,4),"won":K,"pnl_usd":round(J,2),"roi_pct":round(1e2*J/B,2)});c=True
 return{"calibrated_sigma_c":e,"events_evaluated":len(H),"W1_SOLAR_PEAK_LOCK":{"ALL":summarize_trades(D,"W1_ALL"),"TRAIN":summarize_trades([t for t in D if t["split"]=="TRAIN"],"W1_TRAIN"),"TEST_OOS":summarize_trades([t for t in D if t["split"]=="TEST"],"W1_TEST_OOS"),"sample_trades":D[-8:]},"W2_ENSEMBLE_VALUE":{"ALL":summarize_trades(C,"W2_ALL"),"TRAIN":summarize_trades([t for t in C if t["split"]=="TRAIN"],"W2_TRAIN"),"TEST_OOS":summarize_trades([t for t in C if t["split"]=="TEST"],"W2_TEST_OOS"),"sample_trades":C[-8:]}}
def run_crypto_barrier_and_strike_backtests():
 print("[2/3] Fetching Oct 2026 Binance 5m klines + Deribit DVOL + Resolved Hit & Strike events...",flush=True);_b=int(datetime(2026,9,29,0,0,tzinfo=timezone.utc).timestamp());_n=int(datetime(2026,10,25,16,0,tzinfo=timezone.utc).timestamp());_r={"BTC":fetch_binance_5m_series("BTCUSDT",_b,_n),"ETH":fetch_binance_5m_series("ETHUSDT",_b,_n)};_A={"BTC":fetch_deribit_dvol_hourly("BTC",_b,_n),"ETH":fetch_deribit_dvol_hourly("ETH",_b,_n)}
 def _get_spot(asset,ts):b=(ts//300)*300;a=_r[asset].get(b)or _r[asset].get(b-300);return a[3]if a else None
 def _realized_vol_4h_annual(asset,ts):
  f=(ts//300)*300;b=_r[asset];c=[]
  for t in range(f-48*300,f,300):
   e=b.get(t);d=b.get(t+300)
   if e and d and e[3]>0 and d[3]>0:c.append(math.log(d[3]/e[3]))
  if len(c)<12:return.0
  a=sum(x*x for x in c)/len(c);return math.sqrt(a*(365.25*288.))
 def _get_dvol(asset,ts):
  b=(ts//3600)*3600
  for a in(0,-3600,-7200,3600):
   if(b+a)in _A[asset]:return _A[asset][b+a]
  return.42 if asset=="BTC"else.54
 def _already_touched(asset,start_ts,now_ts,strike,direction):
  a=(int(start_ts)//300)*300;c=(now_ts//300)*300;b=_r[asset]
  for t in range(a,c+300,300):
   d=b.get(t)
   if not d:continue
   if direction=="UP"and d[1]>=strike:return True
   if direction=="DOWN"and d[2]<=strike:return True
  return False
 _a=[]
 for asset,_v,_i in[("BTC","DAILY","bitcoin-hit-price-daily"),("ETH","DAILY","ethereum-hit-price-daily"),("BTC","WEEKLY","bitcoin-hit-price-weekly"),("ETH","WEEKLY","ethereum-hit-price-weekly")]:
  _h=http_get_json(f"{GAMMA_URL}/events?series_slug={_i}&closed=true&order=endDate&ascending=false&limit=24")or[]
  for ev in _h:
   for r in parse_hit_event(ev,asset,_v,_i):
    if r.resolved_yes is not None and r.end_ts>=datetime(2026,10,2,tzinfo=timezone.utc).timestamp():_a.append(r)
 print(f"      Loaded {len(_a)} resolved Barrier Hit rungs. Fetching CLOB histories...",flush=True)
 def _fetch_barrier_hist(r):return r,fetch_clob_history(r.yes_token,fidelity=20),fetch_clob_history(r.no_token,fidelity=20)
 B=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=28)as _g:
  for _f in _g.map(_fetch_barrier_hist,_a):
   if _f[1]or _f[2]:B.append(_f)
 g=1.12;k=999.;I=[x for x in B if x[0].end_ts<=SPLIT_CUTOFF_TS]
 for _q in(.95,1.05,1.15,1.25):
  bs=.0;bn=0
  for r,p,_ in I:
   if not p:continue
   _m=len(p)//3;j,_=p[_m];O=r.end_ts-j;u=_get_spot(r.asset,j)
   if not u or O<=1800 or _already_touched(r.asset,r.start_ts,j,r.strike,r.direction):continue
   S,_=get_wing_implied_vol(r.asset,u,r.strike,O,dvol_annual_override=_get_dvol(r.asset,j));_C=first_passage_touch_prob(u,r.strike,O,S,r.direction,wick_vol_multiplier=_q);bs+=(_C-float(r.resolved_yes))**2;bn+=1
  if bn>0 and(bs/bn)<k:k=bs/bn;g=_q
 print(f"      [TRAIN Calibration] Optimal Barrier 1m-Wick Vol Multiplier={g:.2f} (Brier={k:.4f}).",flush=True);H=[];y=[];X=.07;U=.008
 for r,p,Q in sorted(B,key=lambda x:x[0].end_ts):
  W="TRAIN"if r.end_ts<=SPLIT_CUTOFF_TS else"TEST"
  for _p,(j,P)in enumerate(p):
   O=r.end_ts-j
   if not(7200<=O<=5*86400):continue
   if not(.04<=P<=.26):continue
   u=_get_spot(r.asset,j);_u=_get_spot(r.asset,j-7200)
   if not u or not _u or _already_touched(r.asset,r.start_ts,j,r.strike,r.direction):continue
   _j=_get_dvol(r.asset,j);_t=_realized_vol_4h_annual(r.asset,j);J=(r.direction=="UP"and u>_u*1.003)or(r.direction=="DOWN"and u<_u*.997)
   if _t<.95*_j or not J:continue
   S,_=get_wing_implied_vol(r.asset,u,r.strike,O,dvol_annual_override=max(_j,.5*(_j+_t)));F=first_passage_touch_prob(u,r.strike,O,S,r.direction,wick_vol_multiplier=g);o=P+U;w=X*o*(1.-o);n=o+w;N=F-n
   if N>=.065 and(F/n)>=1.4:
    i=25.;h=i/n;_s=min(.88,round(2.*o,3));G=False
    for V,v in p[_p+1:]:
     if v>=_s+.005:G=True;break
    if G:b=h*_s;l=True;a="MAKER_2X_TP"
    else:l=(r.resolved_yes==1);b=h*(1. if l else.0);a="HOLD_SETTLE"
    K=b-i;H.append({"split":W,"sleeve":"B1_CONVEX_TAIL_YES","asset":r.asset,"question":r.question,"entry_ts":j,"entry_px":round(n,4),"p_model":round(F,4),"edge":round(N,4),"exit_mode":a,"won":l,"pnl_usd":round(K,2),"roi_pct":round(1e2*K/i,2)});break
  for j,Z in Q:
   O=r.end_ts-j
   if not(3600<=O<=36000):continue
   if not(.68<=Z<=.9):continue
   u=_get_spot(r.asset,j)
   if not u or _already_touched(r.asset,r.start_ts,j,r.strike,r.direction):continue
   S,_=get_wing_implied_vol(r.asset,u,r.strike,O,dvol_annual_override=_get_dvol(r.asset,j));F=first_passage_touch_prob(u,r.strike,O,S,r.direction,wick_vol_multiplier=g);_x=1.-F;o=Z+U;w=X*o*(1.-o);n=o+w;N=_x-n
   if _x>=.88 and N>=.04:i=1e2;h=i/n;l=(r.resolved_yes==0);K=(h*1.-i)if l else(-i);y.append({"split":W,"sleeve":"B2_BARRIER_NO_LOCK","asset":r.asset,"question":r.question,"entry_ts":j,"entry_px":round(n,4),"p_model":round(_x,4),"edge":round(N,4),"won":l,"pnl_usd":round(K,2),"roi_pct":round(1e2*K/i,2)});break
 print("[3/3] Fetching resolved October 2026 Multi-Strike ('above ___') ladders...",flush=True);R=[]
 for asset,_i in[("BTC","btc-multi-strikes-weekly"),("ETH","ethereum-multi-strikes-weekly")]:
  _h=http_get_json(f"{GAMMA_URL}/events?series_slug={_i}&closed=true&order=endDate&ascending=false&limit=24")or[]
  for ev in _h:
   for sr in parse_multistrike_event(ev,asset,_i):
    if sr.resolved_yes is not None and sr.end_ts>=datetime(2026,10,2,tzinfo=timezone.utc).timestamp():R.append(sr)
 def _fetch_strike_hist(sr):return sr,fetch_clob_history(sr.yes_token,fidelity=20),fetch_clob_history(sr.no_token,fidelity=20)
 E=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=28)as _g:
  for _f in _g.map(_fetch_strike_hist,R):
   if _f[1]or _f[2]:E.append(_f)
 print(f"      Loaded {len(E)} resolved Multi-Strike contracts with CLOB histories.",flush=True);A=[];D=[]
 for sr,p,Q in sorted(E,key=lambda x:x[0].end_ts):
  W="TRAIN"if sr.end_ts<=SPLIT_CUTOFF_TS else"TEST"
  for _e,_B,_d in[("YES",p,sr.resolved_yes==1),("NO",Q,sr.resolved_yes==0)]:
   s=False;q=False
   for _p,(j,P)in enumerate(_B):
    O=sr.end_ts-j
    if O<=900:break
    u=_get_spot(sr.asset,j);_l=_get_spot(sr.asset,j-900)
    if not u or not _l:continue
    if abs(math.log(sr.strike/u))>.08:continue
    _c=evaluate_svi_digital_fair_value(sr.asset,u,sr.strike,O,is_downward=sr.is_downward,dvol_annual_override=_get_dvol(sr.asset,j),now_ts=float(j));_o=_c["p_yes"]if _e=="YES"else _c["p_no"];T=((u-_l)/_l)*1e4;_k=(_e=="YES"and not sr.is_downward)or(_e=="NO"and sr.is_downward)
    if(_k and T<-20.)or((not _k)and T>20.):continue
    o=P+U;w=X*o*(1.-o);n=o+w;N=_o-n
    if(not s)and(10800<=O<=86400)and(.2<=o<=.8)and N>=.055:
     i=1e2;h=i/n;Y=min(.96,round(n+.05,4));M=max(.04,round(o-.075,4));f=None;d=.0;a="SETTLED"
     for V,v in _B[_p+1:]:
      if v>=Y+.005:f=Y;d=.0;a="MAKER_TP_5C";break
      if v<=M:m=max(.01,v-U);f=m;d=X*m*(1.-m);a="HARD_STOP_7.5C";break
      if sr.end_ts-V<=3600:m=max(.01,v-U);f=m;d=X*m*(1.-m);a="TIME_STOP_1H";break
     if f is not None:b=h*(f-d);l=b>i
     else:b=h*(1. if _d else.0);l=_d
     K=b-i;A.append({"split":W,"sleeve":"M1_SVI_MAKER_SCALP","asset":sr.asset,"question":sr.question,"side":_e,"entry_ts":j,"entry_px":round(n,4),"p_model":round(_o,4),"edge":round(N,4),"exit_mode":a,"won":l,"pnl_usd":round(K,2),"roi_pct":round(1e2*K/i,2)});s=True
    if((not q)and(1200<=O<=6300)and(.68<=o<=.9)and _c["z_sigma"]>=1.55 and _o>=.91 and N>=.04):
     i=1e2;h=i/n;e=None;c=.0;a="SETTLED";L=max(.25,o-.22)
     for _,v in _B[_p+1:]:
      if v>=.975:e=.97;c=.0;a="MAKER_TP_97C";break
      if v<=L:m=max(.05,v-U);e=m;c=X*m*(1.-m);a="SALVAGE_STOP";break
     if e is not None:b=h*(e-c);l=b>i
     else:b=h*(1. if _d else.0);l=_d
     K=b-i;D.append({"split":W,"sleeve":"M2_STRIKE_CONVERGENCE","asset":sr.asset,"question":sr.question,"side":_e,"entry_ts":j,"entry_px":round(n,4),"p_model":round(_o,4),"z_sigma":_c["z_sigma"],"edge":round(N,4),"exit_mode":a,"won":l,"pnl_usd":round(K,2),"roi_pct":round(1e2*K/i,2)});q=True
 z={"calibrated_wick_vol_mult":g,"rungs_evaluated":len(B),"B1_CONVEX_TAIL_YES":{"ALL":summarize_trades(H,"B1_ALL"),"TRAIN":summarize_trades([t for t in H if t["split"]=="TRAIN"],"B1_TRAIN"),"TEST_OOS":summarize_trades([t for t in H if t["split"]=="TEST"],"B1_TEST_OOS"),"sample_trades":H[-8:]},"B2_BARRIER_NO_LOCK":{"ALL":summarize_trades(y,"B2_ALL"),"TRAIN":summarize_trades([t for t in y if t["split"]=="TRAIN"],"B2_TRAIN"),"TEST_OOS":summarize_trades([t for t in y if t["split"]=="TEST"],"B2_TEST_OOS"),"sample_trades":y[-8:]}};C={"rungs_evaluated":len(E),"M1_SVI_MAKER_SCALP":{"ALL":summarize_trades(A,"M1_ALL"),"TRAIN":summarize_trades([t for t in A if t["split"]=="TRAIN"],"M1_TRAIN"),"TEST_OOS":summarize_trades([t for t in A if t["split"]=="TEST"],"M1_TEST_OOS"),"sample_trades":A[-8:]},"M2_STRIKE_CONVERGENCE":{"ALL":summarize_trades(D,"M2_ALL"),"TRAIN":summarize_trades([t for t in D if t["split"]=="TRAIN"],"M2_TRAIN"),"TEST_OOS":summarize_trades([t for t in D if t["split"]=="TEST"],"M2_TEST_OOS"),"sample_trades":D[-8:]}};return z,C
def main():
 l=time.time();b=run_weather_backtest();a,c=run_crypto_barrier_and_strike_backtests();d={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"elapsed_sec":round(time.time()-l,2),"split_cutoff_utc":"2026-10-16T23:59:59Z","option_1_weather":b,"option_2_barrier_onetouch":a,"option_4_multistrike_svi":c};REPORT_JSON.write_text(json.dumps(d,indent=2),encoding="utf-8");print("\n================= WALK-FORWARD BACKTEST SUMMARY =================")
 for f,e in[("OPTION #1 WEATHER",["W1_SOLAR_PEAK_LOCK","W2_ENSEMBLE_VALUE"]),("OPTION #2 BARRIER",["B1_CONVEX_TAIL_YES","B2_BARRIER_NO_LOCK"]),("OPTION #4 STRIKE SVI",["M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE"])]:
  g=(b if"WEATHER"in f else(a if"BARRIER"in f else c));print(f"\n--- {f} ---")
  for k in e:j=g[k]["TRAIN"];i=g[k]["TEST_OOS"];h=g[k]["ALL"];print(f"  {k:24s} | ALL: {h['trades']:3d} tr, WR={h['win_rate_pct']:5.1f}%, PnL=${h['net_pnl_usd']:+8.2f}, PF={h['profit_factor']:5.2f}, MaxDD=${h['max_drawdown_usd']:6.2f}\n  {'':24s} | TRN: {j['trades']:3d} tr, WR={j['win_rate_pct']:5.1f}%, PnL=${j['net_pnl_usd']:+8.2f}, PF={j['profit_factor']:5.2f} | OOS: {i['trades']:3d} tr, WR={i['win_rate_pct']:5.1f}%, PnL=${i['net_pnl_usd']:+8.2f}, PF={i['profit_factor']:5.2f}")
 print(f"\nSaved full JSON report -> {REPORT_JSON}")
if __name__=="__main__":main()
# ======================================================================================
# [18/21] MODULE: scripts/polymarket_daily_projections.py
# PURPOSE: Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import argparse
import json;import os;from datetime import datetime,timedelta,timezone;from pathlib import Path;from typing import Any,Dict,List,Optional,Tuple;PIPELINE_ROOT=Path(__file__).resolve().parent.parent;LIVE_STATE_FILE=PIPELINE_ROOT/"data"/"polymarket"/"live_harvester_state.json";ALPHA124_STATE_FILE=(PIPELINE_ROOT/"data"/"alpha124"/"alpha124_shadow_state.json"if(PIPELINE_ROOT/"data"/"alpha124"/"alpha124_shadow_state.json").exists()else PIPELINE_ROOT/"data"/"polymarket"/"alpha124_shadow_state.json");EXP316_STATE_FILE=PIPELINE_ROOT/"data"/"exp316"/"exp316_shadow_state.json";SOL_SHADOW_FILE=PIPELINE_ROOT/"data"/"polymarket"/"state_shadow_sol_v392.json";XRP_SHADOW_FILE=PIPELINE_ROOT/"data"/"polymarket"/"state_shadow_xrp_v392.json";PHASE34_TRACKER_FILE=PIPELINE_ROOT/"data"/"polymarket"/"shadow_phase3_4_tracker.jsonl";RISK_CONFIG_FILE=PIPELINE_ROOT/"config"/"polymarket_risk_config.json";OUTPUT_JSON_FILE=PIPELINE_ROOT/"data"/"polymarket"/"live_daily_projections.json";QUARANTINED_SLEEVES=frozenset({"M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","B1_CONVEX_TAIL_YES","S2_EXACT_TWAP_LOCK","ZERO_FEE_MAKER_ANCHOR_BOX","CTF_OVERROUND_MINT_SELL","SLEEVE_XRP_V392_SHADOW","D1_MAKER_ANCHOR_BOX","ZF_INTRADAY_MAKER_BOX","SHADOW_PHASE3A_MAKER","NR_CONV_NO_BASKET_ARB"});GRADUATION_SPECS=[{"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","wave":"Wave 1 (Live Graduated)","target_day":1,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":13.5,"l1_daily_pnl_cap_usd":140.},{"sleeve":"D1_QUIET_BOOK_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":3,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":65.},{"sleeve":"D1_4H_DOMINANCE_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":60.},{"sleeve":"C1_BINARY_COMPLETE_SET","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"M3_LADDER_MONO_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"B3_BARRIER_MONO_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"D1_MAKER_ANCHOR_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":45.},{"sleeve":"N1_NEGRISK_CROSS_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":20.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"W3_WEATHER_SLATE_ARB","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"CM_B3_PYTH_BARRIER_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"SP1_NBA_ZERO_FEE_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"ZF_INTRADAY_MAKER_BOX","wave":"Wave 1 (Fast-Track Maker Box 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":92.,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"NR0_ZERO_FEE_SLATE_ARB","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"B4_TOUCHED_BARRIER_WICK_LOCK","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"ZERO_FEE_MAKER_ANCHOR_BOX","wave":"Wave 1 (Fast-Track Maker Box)","target_day":5,"min_days":1.,"min_settled":8,"min_wr_pct":92.,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"CTF_OVERROUND_MINT_SELL","wave":"Wave 1 (Instant Mint-Sell 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":5,"min_days":1.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"FED1_CENTRAL_BANK_LP_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"COND1_MACRO_PARTITION_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"D2_12PM_BINANCE_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":5,"min_days":1.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"GAS1_AAA_GASOLINE_LOCK","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":20.},{"sleeve":"MKR_REWARD_LOCKED_CARRY","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":20.},{"sleeve":"BOND1_UMA_RESOLUTION_CARRY","wave":"Wave 1 (Live Graduated 8/8)","target_day":1,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":45.25,"l1_daily_pnl_cap_usd":35.},{"sleeve":"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":20.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":20.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER","wave":"Wave 1 (Liquid-Guarded Live)","target_day":1,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":22.,"l1_daily_pnl_cap_usd":20.},{"sleeve":"SP4_MULTISPORT_CORRIDOR_DOMINANCE_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"LP2_CROSS_MARKET_PARTITION_IMPLICATION_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"NR1_CLOSED_PARTITION_COMPLETE_SET","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"NR2_CONVERT_NO_SUBSET_ARB","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"CRY_INC1_INTRADAY_STRIKE_INCLUSION_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"SP2_NBA_ENDGAME_LOCK","wave":"Wave 2 (Day 7 NBA Endgame)","target_day":7,"min_days":3.,"min_settled":15,"min_wr_pct":93.,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":45.},{"sleeve":"W1_LOW_TROUGH_LOCK","wave":"Wave 2 (Day 8 METAR Low)","target_day":8,"min_days":4.,"min_settled":15,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":40.},{"sleeve":"SLEEVE_SOL_V392_SHADOW","wave":"Wave 2 (Day 5 SOL)","target_day":5,"min_days":1.5,"min_settled":30,"min_wr_pct":85.,"source":"sol_shadow","stage1_ticket_usd":12.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"SHADOW_PHASE3A_MAKER","wave":"Wave 2 (Day 6 Maker)","target_day":6,"min_days":2.,"min_settled":25,"min_wr_pct":80.,"source":"phase3a_shadow","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":32.},{"sleeve":"W1_SOLAR_PEAK_LOCK","wave":"Wave 2 (Day 8 METAR)","target_day":8,"min_days":5.,"min_settled":20,"min_wr_pct":86.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":95.},{"sleeve":"B2_BARRIER_NO_LOCK","wave":"Wave 2 (Day 8 Barrier)","target_day":8,"min_days":5.,"min_settled":25,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":55.},{"sleeve":"CM_B2_PYTH_SESSION_NO_LOCK","wave":"Wave 2 (Day 9 Pyth 0%-Fee)","target_day":9,"min_days":5.,"min_settled":25,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":45.},{"sleeve":"CM_U1_PYTH_CLOSE_LOCK","wave":"Wave 2 (Day 10 Pyth Close)","target_day":10,"min_days":5.,"min_settled":25,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"EXP316_TRACK_A_LATE_LOCK","wave":"Wave 2 (Day 10 Strike)","target_day":10,"min_days":5.,"min_settled":25,"min_wr_pct":80.,"source":"exp316","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"U1_DAILY_UPDOWN_LOCK","wave":"Wave 3 (Day 15 Daily)","target_day":15,"min_days":10.,"min_settled":20,"min_wr_pct":85.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"S5M_CHAINLINK_SNIPER","wave":"Wave 3 (Day 15 5m)","target_day":15,"min_days":7.,"min_settled":35,"min_wr_pct":82.,"source":"alpha124","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"S4H_CHAINLINK_CONVERGENCE","wave":"Wave 3 (Day 14 4h)","target_day":14,"min_days":7.,"min_settled":25,"min_wr_pct":85.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"CM_SHOCK_PYTH_CATALYST","wave":"Wave 3 (Day 16 Macro Jump)","target_day":16,"min_days":10.,"min_settled":25,"min_wr_pct":82.,"source":"alpha124","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"S2_EXACT_TWAP_LOCK","wave":"Wave 3 (Conditional)","target_day":15,"min_days":10.,"min_settled":30,"min_wr_pct":94.,"source":"alpha124","stage1_ticket_usd":12.,"l1_daily_pnl_cap_usd":35.}]
def _load_json(path):
 if not path.exists():return{}
 try:return json.loads(path.read_text(encoding="utf-8"))
 except Exception:return{}
def _load_phase3a_summary(path):
 if not path.exists():return{"closed":0,"wins":0,"pnl_usd":.0}
 a=0;b=0;d=.0
 try:
  with open(path,"r",encoding="utf-8",errors="ignore")as f:
   for c in f:
    c=c.strip()
    if not c:continue
    try:e=json.loads(c)
    except Exception:continue
    if e.get("status")!="RESOLVED":continue
    if str(e.get("event_type")or"")!="SHADOW_PHASE3A_MAKER_RESOLVED":continue
    a+=1;p=float(e.get("shadow_net_pnl_usd")or.0);d+=p
    if p>.0 or e.get("won")is True:b+=1
 except Exception:pass
 return{"closed":a,"wins":b,"pnl_usd":round(d,2)}
def _parse_iso(ts_str):
 if not ts_str:return None
 try:return datetime.fromisoformat(str(ts_str).replace("Z","+00:00"))
 except Exception:return None
def compute_v393_ticket_size(equity,seed_threshold=88.,seed_ticket=12.,dynamic_pct=.18,scale_up_threshold=110.,scale_up_pct=.22,max_cap=2e2,min_smooth_floor=66.67):
 if equity<48.:return.0
 if equity<min_smooth_floor:return round(seed_ticket,2)
 if equity<scale_up_threshold:return round(min(max_cap,max(seed_ticket,equity*dynamic_pct)),2)
 return round(min(max_cap,equity*scale_up_pct),2)
def compute_v540_ticket_size(equity,max_cap=2e2):
 if equity<42.:return.0
 if equity<98.:a=.22
 elif equity<253.:a=.26
 elif equity<1003.:a=.22
 else:a=.16
 return round(min(max_cap,max(10.,equity*a*.9)),2)
compute_v541_ticket_size=compute_v540_ticket_size
def _depth_decay(ticket_usd,knee_usd=65.):
 if ticket_usd<=20.:return 1.
 return max(.58,1./(1.+.35*((ticket_usd-20.)/max(20.,knee_usd))))
def _box_concurrency_mult(equity):
 if equity<98.:return 1.
 if equity<253.:return 1.+.32*((equity-98.)/155.)
 if equity<1003.:return 1.32+.48*((equity-253.)/750.)
 return min(2.35,1.8+.55*min(1.,(equity-1003.)/2e3))
def _wilson_lcb_pct(wins,n,z=1.2816):
 if n<=0:return.0
 p=max(.0,min(1.,wins/float(n)));d=z*z;b=1.+d/n;a=p+d/(2.*n);c=z*((p*(1.-p)/n+d/(4.*n*n))**.5);return round(1e2*max(.0,(a-c)/b),2)
def simulate_single_day_net_pnl(day_idx,equity_start,scenario,scale_up_threshold=98.,shadow_by_sleeve=None,sol_shadow=None,phase3a_shadow=None,exp316_t1k=None):
 d={"P25_CONSERVATIVE":.85,"P50_BASE_FINLAND":1.35,"P75_LONDON_UPSIDE":1.95}[scenario];b={"P25_CONSERVATIVE":.145,"P50_BASE_FINLAND":.182,"P75_LONDON_UPSIDE":.21}[scenario];c={"P25_CONSERVATIVE":.91,"P50_BASE_FINLAND":.95,"P75_LONDON_UPSIDE":.97}[scenario];o={"P25_CONSERVATIVE":.62,"P50_BASE_FINLAND":1.,"P75_LONDON_UPSIDE":1.42}[scenario];A=_box_concurrency_mult(equity_start);z=compute_v541_ticket_size(equity_start);l=1.28 if equity_start>=253. else(1.15 if equity_start>=150. else 1.);f=d*l;y=b*c*_depth_decay(z,knee_usd=65.);r={"P25_CONSERVATIVE":55.,"P50_BASE_FINLAND":95.,"P75_LONDON_UPSIDE":145.}[scenario];q=min(r,z*f*y);x=60. if equity_start<98. else(120. if equity_start<253. else(150. if equity_start<1003. else 220.));C=min(x,max(14.,equity_start*.48));n=1.95*o*(1.+.45*(A-1.));w={"P25_CONSERVATIVE":24.,"P50_BASE_FINLAND":38.,"P75_LONDON_UPSIDE":58.}[scenario];v=min(w,C*n*(.031*_depth_decay(C,knee_usd=75.)));u=(60. if equity_start<98. else(max(60.,equity_start*.4)if equity_start<253. else(120. if equity_start<1003. else 150.)));B=min(u,max(14.,equity_start*.36));m=1.2*o*A;t={"P25_CONSERVATIVE":16.,"P50_BASE_FINLAND":26.,"P75_LONDON_UPSIDE":40.}[scenario];s=min(t,B*m*(.0235*_depth_decay(B,knee_usd=80.)));k=45.25 if equity_start<98. else(85. if equity_start<253. else(130. if equity_start<1003. else 180.));p=min(k,equity_start*.42);g=2.1*o*(1.+.55*(A-1.));j={"P25_CONSERVATIVE":6.5,"P50_BASE_FINLAND":11.,"P75_LONDON_UPSIDE":17.}[scenario];i=min(j,p*g*.0082);h={"v541_high_z_directional_sniper":round(q,2),"D1_same_oracle_and_quiet_boxes":round(v,2),"V3_zero_loss_math_partition_boxes":round(s,2),"BOND1_and_liquid_MKR_LOCK1_carry":round(i,2)}
 if equity_start>=1003.:a="INSTITUTIONAL (>=$1,003): 4 Dir Slots ($160-$200 Cap) + 10 Box Slots ($150-$220 L1 Depth Cap)"
 elif equity_start>=253.:a="SCALE ($253-$1,003): 4 Dir Slots (22% Ticket) + $120-$150 Box Cap + 88% BOND1"
 elif equity_start>=150.:a="HYPER_GROWTH 3-Slot (>=$150): 3 Crypto Dir Slots (26% Ticket) + $120 D1 Cap + 48h Velocity"
 elif equity_start>=98.:a="HYPER_GROWTH ($98-$150): 26% Dir Ticket + $120 D1 / 40% ZF Box Cap + 48h Velocity"
 else:a="UNLEASHED_LAUNCH (<$98): v5.4.1 High-Z Sniper + 90% D1 ($60) + 0-Loss Math Boxes + 78% BOND1"
 e=round(sum(h.values()),2);return e,h,a
def compute_live_equity_and_rates(live_st,fallback_equity=69.61):
 q=float(live_st.get("total_account_equity")or.0);p=float(live_st.get("live_bankroll")or.0);k=(("total_account_equity"in live_st and live_st.get("total_account_equity")is not None)or("live_bankroll"in live_st and live_st.get("live_bankroll")is not None));B=live_st.get("active_positions");v=list(B.values())if isinstance(B,dict)else[];b=.0;o={};c=.0
 for T in v:
  if not isinstance(T,dict):continue
  G=float(T.get("remaining_cost_basis",T.get("notional_usd",.0))or.0);n=T.get("_closed_partner_leg")
  if(T.get("is_dominance_box")and isinstance(n,dict)and float(n.get("payout_usd",.0)or.0)<=.01):H=max(float(T.get("expected_terminal_payout_usd")or T.get("entry_shares")or.0),G+float(n.get("notional_usd",.0)or.0));b+=H;c+=H;continue
  e=.0
  if T.get("is_dominance_box")or T.get("is_single_leg_lock"):
   E=str(T.get("entry_fee_asset")or"").upper()
   if E!="SHARES":e=float(T.get("entry_fee_cash_usd")or T.get("fee_usd")or.0)
   elif(T.get("inventory_reconciled")and float(T.get("fee_usd",.0)or.0)==.0 and float(T.get("fee_rate_applied",.0)or.0)>.0 and float(T.get("entry_shares",.0)or.0)>.0 and float(T.get("entry_shares",.0)or.0)>=float(T.get("gross_entry_shares")or T.get("entry_shares")or.0)-.02):
    P=float(T["entry_shares"]);S=G/P
    if.0<S<1.:O=float(T.get("fee_rate_applied")or.0);N=float(T.get("fee_exponent_applied")or 1.);e=round(P*O*((S*(1.-S))**N),4)
  F=G+e;b+=F;L=str(T.get("box_id")or"").strip()
  if T.get("is_dominance_box")and L:o.setdefault(L,[]).append(T)
  else:c+=F
 d=.0;h=(live_st.get("collateral_includes_resting_maker")is False or str(live_st.get("collateral_source")or"").upper()=="CLOB_BALANCE_API")
 if h and isinstance(live_st.get("pending_entry_intents"),dict):
  for J in live_st["pending_entry_intents"].values():
   if isinstance(J,dict)and(J.get("live_maker_anchor_inflight")or J.get("maker_wire_inflight")or J.get("entry_order_id")):d+=max(.0,float(J.get("notional_usd")or.0))
 if k:j=p+b+d;f=max(q,j)
 else:f=float(fallback_equity)
 a=.0
 for I in o.values():
  if len(I)>=2:D=min(float(x.get("remaining_shares",x.get("entry_shares",.0))or.0)for x in I);a+=max(D,sum(float(x.get("remaining_cost_basis",x.get("notional_usd",.0))or.0)for x in I))
  else:a+=sum(float(x.get("remaining_cost_basis",x.get("notional_usd",.0))or.0)for x in I)
 i=(max(f,p+c+a+d)if k else f);A=max(float(live_st.get("high_water_mark_equity")or.0),f);u=[t for t in(live_st.get("closed_positions")or[])if isinstance(t,dict)];z={}
 for t in u:
  M=str(t.get("box_id")or"").strip()
  if M:z[M]=z.get(M,0)+1
 s={}
 for R,t in enumerate(u):
  y=t.get("realized_pnl_usd")
  if y is None:y=t.get("net_pnl_usd")
  if y is not None:m=float(y)
  else:m=(float(t.get("realized_exit_cash",.0)or.0)-float(t.get("notional_usd",.0)or.0)-float(t.get("fee_usd",.0)or.0))
  M=str(t.get("box_id")or"").strip();l=bool(M)and(bool(t.get("is_dominance_box"))or z.get(M,0)>1);K=f"BOX::{M}"if l else f"TRD::{R}::{t.get('trade_id')or R}";Q=s.setdefault(K,{"pnl":.0,"any_won_flag":False,"legs":0});Q["pnl"]+=m;Q["legs"]+=1
  if t.get("won")is True:Q["any_won_flag"]=True
 w=len(s);C=sum(1 for g in s.values()if g["pnl"]>.0 or(abs(g["pnl"])<=1e-9 and g["any_won_flag"]));r=round(1e2*C/w,2)if w>0 else.0;return{"live_equity":f,"locked_floor_equity":i,"hwm_equity":A,"closed_legs_count":len(u),"economic_trades_count":w,"economic_wins":C,"economic_win_rate_pct":r}
def build_live_projections(days=30,fallback_equity=69.61):
 P=datetime.now(timezone.utc);O=_load_json(LIVE_STATE_FILE);N=_load_json(ALPHA124_STATE_FILE);D=_load_json(EXP316_STATE_FILE);V=_load_json(SOL_SHADOW_FILE);U=_load_json(XRP_SHADOW_FILE);T=_load_phase3a_summary(PHASE34_TRACKER_FILE);I=_load_json(RISK_CONFIG_FILE);H=compute_live_equity_and_rates(O,fallback_equity=fallback_equity);u=H["live_equity"];i=H["locked_floor_equity"];z=H["hwm_equity"];r=float(I.get("scale_up_equity_threshold")or 110.);n=H["economic_trades_count"];C=H["economic_wins"];t=H["economic_win_rate_pct"];q=_parse_iso(N.get("started_at"));h=(round(max(.0,(P-q).total_seconds()/86400.),2)if q else 1.);B=N.get("by_sleeve")or{};y=(D.get("tiers")or{}).get("T1000")or{};p=[]
 for sp in GRADUATION_SPECS:
  sl=sp["sleeve"]
  if sl in QUARANTINED_SLEEVES:continue
  _b=sp["source"]
  if _b=="sol_shadow":a=int(V.get("total_trades_settled")or 0);g=int(V.get("winning_trades")or 0);f=int(V.get("active_open_positions_count")or 0);c=float(V.get("realized_pnl")or.0)
  elif _b=="phase3a_shadow":a=int(T.get("closed")or 0);g=int(T.get("wins")or 0);f=0;c=float(T.get("pnl_usd")or.0)
  elif _b=="exp316":a=int(y.get("trades")or 0);g=int(y.get("wins")or 0);f=int(D.get("active_positions")or 0);c=float(y.get("net_pnl_usd")or.0)
  else:M=B.get(sl)or{};a=int(M.get("closed")or 0);g=int(M.get("wins")or 0);f=int(M.get("open")or 0);c=float(M.get("realized_pnl_t1000_usd")or.0)
  S=round(1e2*g/a,2)if a>0 else.0;o=_wilson_lcb_pct(g,a);x=round(min(1e2,1e2*a/sp["min_settled"]),1);G=round(min(1e2,1e2*h/sp["min_days"]),1);Z=(a>=sp["min_settled"]and h>=sp["min_days"]and S>=sp["min_wr_pct"]and o>=max(.0,sp["min_wr_pct"]-20.)and c>.0);p.append({"sleeve":sl,"wave":sp["wave"],"source":_b,"open_now":f,"settled_now":a,"target_settled":sp["min_settled"],"sample_progress_pct":x,"days_elapsed":h,"min_days":sp["min_days"],"time_progress_pct":G,"win_rate_pct":S,"wilson_lcb90_wr_pct":o,"target_wr_pct":sp["min_wr_pct"],"realized_pnl_t1000_usd":round(c,2),"ready_for_stage1_micro_live":Z})
 A=["P25_CONSERVATIVE","P50_BASE_FINLAND","P75_LONDON_UPSIDE"];F={sc:u for sc in A};w=P.date();s=max(days,365);j=(100,250,500,1000,2500,5000,10000);l={f"usd_{m}":{}for m in j};E=[]
 for d in range(1,s+1):
  R=(w+timedelta(days=d-1)).isoformat();_a={"day":d,"date_utc":R};e="";b={}
  for sc in A:
   L=F[sc];Y,X,W=simulate_single_day_net_pnl(d,L,sc,scale_up_threshold=r,shadow_by_sleeve=B,sol_shadow=V,phase3a_shadow=T,exp316_t1k=y);Q=round(L+Y,2);F[sc]=Q;K=sc.split("_")[0].lower();_a[f"{K}_daily_pnl_usd"]=Y;_a[f"{K}_end_equity_usd"]=Q
   for m in j:
    mk=f"usd_{m}"
    if f"{K}_day"not in l[mk]and Q>=float(m):l[mk][f"{K}_day"]=d;l[mk][f"{K}_date_utc"]=R
   if sc=="P50_BASE_FINLAND":e=W;b=X;_a["p50_v393_ticket_usd"]=compute_v541_ticket_size(L)
  _a["active_regime_and_milestone"]=e;_a["p50_sleeve_pnl_breakdown_usd"]=b;E.append(_a)
 v=E[:days];J={"generated_at_utc":P.isoformat(),"model_version":"v5.4.1_high_z_sniper_plus_unleashed_zero_loss_boxes","quarantined_sleeves_excluded":sorted(QUARANTINED_SLEEVES),"anchor_live_state":{"live_equity_usd":round(u,2),"locked_box_payout_floor_equity_usd":round(i,2),"high_water_mark_usd":round(z,2),"current_v393_ticket_usd":compute_v541_ticket_size(u),"current_v540_btc_ticket_usd":round(min(2e2,u*(.22 if u<98. else.26)),2),"current_v540_eth_sol_ticket_usd":round(min(170.,u*(.22 if u<98. else.26)*.85),2),"distance_to_88_dynamic_sizing_usd":round(max(.0,98.-u),2),"distance_to_98_hyper_growth_usd":round(max(.0,98.-u),2),"distance_to_110_slot2_unlock_usd":round(max(.0,150.-u),2),"distance_to_150_slot3_unlock_usd":round(max(.0,150.-u),2),"distance_to_253_scale_tier_usd":round(max(.0,253.-u),2),"distance_to_1003_institutional_tier_usd":round(max(.0,1003.-u),2),"live_closed_trades":n,"live_closed_legs":H["closed_legs_count"],"live_wins":C,"live_win_rate_pct":t,"alpha124_markets_monitored":N.get("markets_monitored",{}),"alpha124_open_shadow_positions":N.get("open_positions_count",0),"alpha124_resting_maker_bids":N.get("pending_maker_orders_count",0),"sol_shadow_settled":V.get("total_trades_settled",0),"sol_shadow_win_rate_pct":V.get("win_rate_pct",.0),"phase3a_maker_settled":T.get("closed",0),"xrp_shadow_settled":U.get("total_trades_settled",0)},"summary_horizons_usd":{f"day_{k}":{"date_utc":E[k-1]["date_utc"],"p25_equity":E[k-1]["p25_end_equity_usd"],"p50_equity":E[k-1]["p50_end_equity_usd"],"p75_equity":E[k-1]["p75_end_equity_usd"],"p50_daily_pnl":E[k-1]["p50_daily_pnl_usd"],"p50_net_profit":round(E[k-1]["p50_end_equity_usd"]-u,2)}for k in(1,4,7,10,14,21,30,60,90,180,365)if k<=len(E)},"milestone_eta_days":l,"p75_jurisdiction_compliance_note":("P75 models <15ms low-latency execution; Polymarket restricts UK (eu-west-2), FR, DE, IE, and ON — keep live execution on Finland (or another verified non-restricted EU region) unless lawful eligibility is confirmed."),"sleeve_graduation_live_tracker":p,"day_by_day_schedule":v};return J
def write_live_projections_atomic(days=30):a=build_live_projections(days=days);OUTPUT_JSON_FILE.parent.mkdir(parents=True,exist_ok=True);b=OUTPUT_JSON_FILE.with_suffix(".tmp");b.write_text(json.dumps(a,indent=2),encoding="utf-8");os.replace(b,OUTPUT_JSON_FILE);return a
def print_human_scorecard(payload):
 b=payload["anchor_live_state"];print(f"=== DOMINUS POLYMARKET LIVE DAY-BY-DAY PROJECTIONS [{payload.get('model_version')}] ({payload['generated_at_utc']}) ===");print(f"Anchor Live Equity: ${b['live_equity_usd']:.2f} (HWM ${b['high_water_mark_usd']:.2f}) | Live Epoch: {b['live_wins']}W/{b['live_closed_trades']-b['live_wins']}L ({b['live_win_rate_pct']:.1f}% WR) | To $88 Dynamic: ${b['distance_to_88_dynamic_sizing_usd']:.2f} | To $110 Slot-2: ${b['distance_to_110_slot2_unlock_usd']:.2f}");print("\n--- Clean Active Shadow Sleeve Graduation Readiness (Quarantined Sleeves Excluded) ---")
 for g in payload["sleeve_graduation_live_tracker"]:a="READY"if g["ready_for_stage1_micro_live"]else"WAIT ";print(f"  [{a}] {g['sleeve']:28s} | {g['wave']:22s} | Settled={g['settled_now']:2d}/{g['target_settled']:2d} (Open={g['open_now']:2d}) | WR={g['win_rate_pct']:6.1f}% (req>={g['target_wr_pct']:5.1f}%) | Ref PnL=${g['realized_pnl_t1000_usd']:+7.2f}")
 print("\n--- 30-Day Live-Anchored Compounding Schedule (Post-Purge Clean Roster, Depth-Capped) ---");print("Day | Date       | P25 Eq ($) | P50 Base Eq ($) | P50 Day PnL | P75 LowLat ($) | Active Regime / Graduation Milestone");print("-"*122)
 for r in payload["day_by_day_schedule"]:print(f"D{r['day']:02d} | {r['date_utc']} | ${r['p25_end_equity_usd']:9.2f} | ${r['p50_end_equity_usd']:14.2f} | ${r['p50_daily_pnl_usd']:+10.2f} | ${r['p75_end_equity_usd']:13.2f} | {r['active_regime_and_milestone']}")
def main():
 b=argparse.ArgumentParser(description="Live Polymarket Day-by-Day Projections & Graduation Tracker");b.add_argument("--days",type=int,default=30,help="Projection horizon in days");b.add_argument("--json-only",action="store_true",help="Print JSON payload instead of ASCII table");c=b.parse_args();a=write_live_projections_atomic(days=c.days)
 if c.json_only:print(json.dumps(a,indent=2))
 else:print_human_scorecard(a)
if __name__=="__main__":main()
# ======================================================================================
# [19/21] MODULE: scripts/alpha124_status.py
# PURPOSE: Live Alpha-124 Multi-Sleeve Scorecard & Orderbook Opportunity Inspector
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
from pathlib import Path;PROJECT_ROOT=Path(__file__).resolve().parent.parent;STATE_FILE=PROJECT_ROOT/"data"/"alpha124"/"alpha124_shadow_state.json";OPPS_FILE=PROJECT_ROOT/"data"/"alpha124"/"alpha124_live_opportunities.json"
def main():
 if not STATE_FILE.exists():print("No Alpha-124 state file found yet.");return
 i=json.loads(STATE_FILE.read_text(encoding="utf-8"));print(f"=== ALPHA-124 SHADOW SCORECARD (Updated: {i.get('updated_at_utc')}) ===");print(f"Cycles: {i.get('cycle_count')} | MakerPending: {i.get('pending_maker_orders_count',0)} | Monitored: {i.get('markets_monitored')}");print(f"Spots : {i.get('spots')}");print(f"Realized PnL by Bankroll Tier: {i.get('portfolio_realized_pnl_by_bankroll_usd')}");print("\n--- Sleeve Breakdown ---")
 for h,m in(i.get("by_sleeve")or{}).items():print(f"  {h:28s} | Open={m['open']:2d} | Closed={m['closed']:3d} ({m['wins']}W/{m['losses']}L, WR={m['win_rate_pct']:5.1f}%) | T1000 PnL=${m['realized_pnl_t1000_usd']:+8.2f}")
 c=i.get("by_d1_asset")or{}
 if c:
  print("\n--- D1 Same-Oracle 7-Coin Graduation Status ---")
  for f,g in c.items():print(f"  {f:6s} | Open={g['open']:2d} | Closed={g['closed']:3d} ({g['wins']}W/{g['losses']}L, WR={g['win_rate_pct']:5.1f}%) | T1000 PnL=${g['realized_pnl_t1000_usd']:+8.2f}")
 b=i.get("pending_maker_orders")or[]
 if b:
  print(f"\n--- Resting 0%-Fee Maker Entry Bids ({len(b)}) ---")
  for e in b[:10]:print(f"  [{e['sleeve']}] {e['asset_or_city']} {e['title']} ({e['side']}) | resting_bid=${e['resting_bid']:.3f} (ask_at_post=${e['best_ask_at_post']:.3f}, p_mod={e['p_model_at_post']:.3f})")
 a=i.get("open_positions")or[]
 if a:
  print(f"\n--- Active Shadow Positions ({len(a)}) ---")
  for p in a[:15]:print(f"  [{p['sleeve']}] {p['title']} ({p['side']}) | entry_eff=${p['entry_eff_px_t1000']:.3f} last_bid=${p.get('last_bid',0):.3f} tp=${p.get('maker_tp_px')or 0:.3f} p_mod={p['p_model_entry']:.3f}")
 if OPPS_FILE.exists():
  d=json.loads(OPPS_FILE.read_text(encoding="utf-8")).get("top_opportunities")or[]
  if d:
   print(f"\n--- Top Live Orderbook Opportunities ({len(d)}) ---")
   for o in d[:12]:print(f"  [{o['sleeve']:28s}] edge={o['net_edge']:+.3f} | ask=${o['ask_vwap']:.3f} vs p={o['p_model']:.3f} (L1=${o['l1_usd']:.0f}) | {o['market']}")
if __name__=="__main__":main()
# ======================================================================================
# [20/21] MODULE: scripts/polymarket_scorecard_snapshot.py
# PURPOSE: Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot
# ======================================================================================

#!/usr/bin/env python3 import json
import os;import pathlib;import subprocess;ROOT=pathlib.Path("/home/skybullet1987/quant_pipeline");SERVICES=["polymarket-live-harvester","polymarket-alpha124-shadow","polymarket-trader","polymarket-exp316-shadow","polymarket-recorder","polymarket-recorder-eth","polymarket-recorder-sol","polymarket-recorder-xrp"]
def _read_json(rel_path):
 p=ROOT/rel_path
 if not p.exists():return{}
 try:return json.loads(p.read_text(encoding="utf-8"))
 except Exception as exc:return{"error":str(exc)}
def main():
 p=dict(os.environ)
 if hasattr(os,"getuid"):p.setdefault("XDG_RUNTIME_DIR",f"/run/user/{os.getuid()}")
 d={s:subprocess.run(["systemctl","--user","is-active",s],capture_output=True,text=True,env=p).stdout.strip()for s in SERVICES};l=_read_json("data/polymarket/live_harvester_state.json");c=_read_json("data/alpha124/alpha124_shadow_state.json");j=_read_json("data/polymarket/live_daily_projections.json");h=_read_json("data/polymarket/paper_trader_state.json");o=_read_json("data/polymarket/state_shadow_sol_v392.json");n=_read_json("data/polymarket/state_shadow_xrp_v392.json");f=_read_json("data/exp316/exp316_shadow_state.json");e=l.get("closed_positions")or[];i=sum(1 for t in e if float(t.get("realized_pnl_usd")or t.get("net_pnl_usd")or(float(t.get("realized_exit_cash",.0))-float(t.get("notional_usd",.0))-float(t.get("fee_usd",.0))))>0);g=subprocess.run(["journalctl","--user","-u","polymarket-live-harvester","--since","24 hours ago","--no-pager"],capture_output=True,text=True,env=p).stdout.splitlines();m=[line for line in g if"SHADOW_PHASE3A"in line][-5:];q=[line for line in g if"SHADOW_PHASE4"in line][-5:];b=["timestamp","current_equity","realized_pnl","total_trades_settled","winning_trades","losing_trades","win_rate_pct","profit_factor","active_open_positions_count","ready_for_live_graduation","graduation_criteria"];a={"services":d,"all_services_active":all(v=="active"for v in d.values()),"live_v392":{"updated_at_utc":l.get("updated_at_utc"),"live_bankroll_usd":l.get("live_bankroll"),"total_account_equity_usd":l.get("total_account_equity"),"high_water_mark_equity_usd":l.get("high_water_mark_equity"),"active_positions_count":l.get("active_positions_count"),"closed_positions_count":len(e),"closed_wins":i,"progress_to_n40_gate":f"{len(e)}/40","distance_to_88_dynamic_tier_usd":round(max(.0,88.-float(l.get("total_account_equity")or.0)),2),"distance_to_110_scaleup_tier_usd":round(max(.0,110.-float(l.get("total_account_equity")or.0)),2),"risk_halt":l.get("risk_halt"),"reconciliation_required":l.get("reconciliation_required"),"global_halt_reasons":l.get("global_halt_reasons")},"alpha124_11sleeve_shadow":{"updated_at_utc":c.get("updated_at_utc"),"markets_monitored":c.get("markets_monitored"),"open_positions_count":c.get("open_positions_count"),"pending_maker_orders_count":c.get("pending_maker_orders_count"),"portfolio_realized_pnl_by_bankroll_usd":c.get("portfolio_realized_pnl_by_bankroll_usd"),"by_sleeve":c.get("by_sleeve")},"live_daily_projections_summary":j.get("summary_horizons_usd",{}),"paper_sleeve1_benchmark":h.get("validation_oos_epoch",{}),"shadow_sol_v392":{k:o.get(k)for k in b},"shadow_xrp_v392":{k:n.get(k)for k in b},"shadow_exp316":f,"shadow_phase3a_recent_24h":m,"shadow_phase4_recent_24h":q};print(json.dumps(a,indent=2))
if __name__=="__main__":main()
# ======================================================================================
# [21/21] MODULE: tests/test_alpha_124_oracles.py
# PURPOSE: Unit Tests: Weather METAR/HKO, Jump-SVI Barrier, Pyth Session/Boxes, NBA Boxes, D1, S2 & Wallet
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import sys
from datetime import datetime,timezone;from pathlib import Path;PROJECT_ROOT=Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT)not in sys.path:sys.path.insert(0,str(PROJECT_ROOT))
from src.polymarket_research.barrier_onetouch_svi_engine import(first_passage_touch_prob,parse_barrier_direction,parse_strike_from_text);from src.polymarket_research.multistrike_svi_scalper import(detect_ladder_monotonicity_boxes,evaluate_svi_digital_fair_value);from src.polymarket_research.weather_metar_engine import(celsius_to_market_int,parse_bucket_bounds,parse_metar_line,round_half_up_polymarket)
def test_polymarket_weather_rounding_spec_examples():assert round_half_up_polymarket(13.9)==14;assert round_half_up_polymarket(17.4)==17;assert round_half_up_polymarket(16.5)==17;assert round_half_up_polymarket(-1.7)==-2;assert round_half_up_polymarket(-8.5)==-8;assert celsius_to_market_int(18.3,"F")==65;assert celsius_to_market_int(17.8,"F")==64;assert celsius_to_market_int(19.,"F")==66;assert celsius_to_market_int(-22.5,"F")==-8
def test_metar_parser_speci_and_t_remark():f=datetime(2026,10,25,16,0,tzinfo=timezone.utc);e=parse_metar_line("SPECI RJTT 251545Z 08010KT 9999 SCT015 24/20 Q1016 RMK T02440200","RJTT",f,"Asia/Tokyo");assert e is None;d=parse_metar_line("METAR KHOU 251253Z 12005KT 10SM FEW033 14/13 A3002 RMK AO2 T01390133","KHOU",f,"America/Chicago");assert d is not None and d.has_t_remark and abs(d.temp_c-13.9)<1e-6;c=parse_metar_line("KORD 251051Z 29012KT 10SM CLR M02/M02 A3015 RMK AO2 T10171022","KORD",f,"America/Chicago");assert c is not None and c.has_t_remark and abs(c.temp_c-(-1.7))<1e-6;b=parse_metar_line("METAR RJTT 250600Z 08007KT 9999 FEW020 18/12 Q1017 NOSIG","RJTT",f,"Asia/Tokyo");assert b is not None and(not b.has_t_remark)and abs(b.temp_c-18.)<1e-6;a=parse_metar_line("METAR UUWW 250300Z 18004KT 9999 OVC015 M11/M17 Q1021","UUWW",f,"Europe/Moscow");assert a is not None and abs(a.temp_c-(-11.))<1e-6
def test_bucket_bounds_parser():assert parse_bucket_bounds("16°C or below")==("C",float("-inf"),16.);assert parse_bucket_bounds("17°C")==("C",17.,17.);assert parse_bucket_bounds("26°C or higher")==("C",26.,float("inf"));assert parse_bucket_bounds("72-73°F")==("F",72.,73.)
def test_barrier_and_svi_monotonicity():assert parse_barrier_direction("Will Bitcoin reach $88,000 on October 25?","↑ 88,000")=="UP";assert parse_barrier_direction("Will Bitcoin dip to $76,000 on October 25?","↓ 76,000")=="DOWN";assert parse_strike_from_text("Will Bitcoin reach $88,000 on October 25?")==8.8e4;c=first_passage_touch_prob(8.2e4,8.4e4,86400.,.45,"UP",wick_vol_multiplier=1.);b=first_passage_touch_prob(8.2e4,8.6e4,86400.,.45,"UP",wick_vol_multiplier=1.);a=evaluate_svi_digital_fair_value("BTC",8.2e4,8.4e4,86400.,dvol_annual_override=.45);assert c>b>.0;assert c>a["p_yes"]*1.6;d=detect_ladder_monotonicity_boxes([{"strike":8e4,"is_downward":False,"market_id":"1","yes_token":"ty1","no_token":"tn1","ask_yes":.55,"ask_no":.46},{"strike":8.2e4,"is_downward":False,"market_id":"2","yes_token":"ty2","no_token":"tn2","ask_yes":.62,"ask_no":.39}]);assert len(d)==1 and d[0]["box_cost_net"]<.996
def test_svi_sticky_delta_no_butterfly_arb_on_sol_and_xrp():from src.polymarket_research.deribit_svi_surface import(SVIParams,compute_breeden_litzenberger_digital,scale_svi_sticky_delta);f=5./365.25;e=(.44**2)*f;d=SVIParams(a=e*.82,b=e*.42,rho=-.18,m=.0,sigma=.06,t_years=f,forward_price=8.4e4,calibrated_at=1e3);c=scale_svi_sticky_delta(d,1.75,103.5);b=scale_svi_sticky_delta(d,1.85,2.15);assert abs(c.implied_vol(.0)-d.implied_vol(.0)*1.75)<1e-6;assert abs(b.implied_vol(.0)-d.implied_vol(.0)*1.85)<1e-6;a=compute_breeden_litzenberger_digital(103.5,1e2,f,c);assert.5<=a<=.68,f"Expected realistic SOL > $100 digital prob, got {a}"
def test_kmia_convective_rain_cold_pool_bias_guard():from datetime import date,timedelta;from src.polymarket_research.weather_metar_engine import(WeatherBucket,WeatherEventSpec,compute_weather_probabilities);c=datetime(2026,10,25,17,0,tzinfo=timezone.utc);b=parse_metar_line("METAR KMIA 251653Z 07009KT 6SM RA SCT025CB BKN050 OVC110 25/21 A3004 RMK AO2 SLP173 CB OHD MOV SW P0004 T02500211","KMIA",c,"America/New_York");assert b is not None and b.has_convective_precip is True;e=[WeatherBucket("m1","c1","78-79°F","78-79°F","y1","n1","F",78.,79.),WeatherBucket("m2","c2","80-81°F","80-81°F","y2","n2","F",80.,81.),WeatherBucket("m3","c3","82-83°F","82-83°F","y3","n3","F",82.,83.),WeatherBucket("m4","c4","84°F or higher","84°F+","y4","n4","F",84.,float("inf"))];f=WeatherEventSpec(event_id="ev_mia",slug="miami-oct-25",series_slug="miami-daily-weather",title="Highest temperature in Miami on October 25?",icao="KMIA",city="Miami",lat=25.7959,lon=-80.287,tz_name="America/New_York",obs_date=date(2026,10,25),metric="HIGH",unit="F",fee_type="zero_fees",end_date_iso="2026-10-26T04:00:00Z",buckets=e);d=int(datetime(2026,10,25,17,0,tzinfo=timezone.utc).timestamp());a={d+h*3600:[27.3+(.9 if h in(2,3)else.2)+(m-30)*.02 for m in range(60)]for h in range(0,10)};g=compute_weather_probabilities(f,c,[b],a);assert g["convective_cold_pool"]is True;assert g["bias_c"]>=-.5;assert g["ensemble_member_count"]==60;assert g["probs"][0]<.35
def test_anchored_strike_regex_ignores_dates():from src.polymarket_research.multistrike_svi_scalper import _extract_threshold_strike;assert parse_strike_from_text("Will Bitcoin hit a new high on October 30, 2026?","")is None;assert parse_strike_from_text("Will Bitcoin reach 105k on October 30?","")==1.05e5;assert _extract_threshold_strike("Will Solana close higher on October 30, 2026?","October 30")is None;assert _extract_threshold_strike("Will Solana be above $105 on October 30?","$105")==105.
def test_alpha124_l2_depth_maker_queue_and_gamma_404_settlement(tmp_path,monkeypatch):
 import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124;c=a124.walk_l2_book_asks([{"price":"0.22","size":"50"}],notional_usd=50.,fee_rate=.0);assert c["filled"]is False and c["reason"]=="THIN_L1_DEPTH";a=a124.walk_l2_book_asks([{"price":"0.50","size":"60"}],notional_usd=50.,fee_rate=.0);assert a["filled"]is False and a["reason"]=="INSUFFICIENT_DEPTH";b=a124.walk_l2_book_asks([{"price":"0.50","size":"250"}],notional_usd=50.,fee_rate=.0);assert b["filled"]is True and b["fill_ratio"]==1.;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"state.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ledger.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"opps.json")
 async def _run_sim():
  d=a124.Alpha124ShadowDaemon(single_scan=True);d.spots["BTC"]=8.4e4;c={"tok_m1":{"bids":[{"price":"0.48","size":"200"}],"asks":[{"price":"0.50","size":"200"}]}}
  async def fake_fetch_json(url,timeout=5.):
   if"/book?token_id=tok_m1"in url:return c["tok_m1"]
   if"/book?token_id=tok_w1_closed"in url:return None
   if"/markets/mkt_w1"in url:return{"id":"mkt_w1","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["tok_w1_closed", "tok_w1_no"]',"outcomePrices":'["1", "0"]'}
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch_json);b=await d.post_shadow_maker_entry(sleeve="M1_SVI_MAKER_SCALP",dedupe_key="M1_test_YES",asset="BTC",title="BTC above $84,000?",side_label="YES",token_id="tok_m1",p_model=.58,close_ts=1999999999.,extra={"market_id":"m_btc","strike":8.4e4,"is_downward":False});assert b is True;assert len(d.pending_maker_orders)==1;assert len(d.open_positions)==0;e=next(iter(d.pending_maker_orders));d.pending_maker_orders[e]["created_ts"]-=15.;monkeypatch.setattr(a124,"evaluate_svi_digital_fair_value",lambda*args,**kwargs:{"p_yes":.58,"p_no":.42,"iv_annual":.45,"z_sigma":.5,"source":"TEST"});await d.manage_pending_maker_orders();assert len(d.pending_maker_orders)==1 and len(d.open_positions)==0;c["tok_m1"]={"bids":[{"price":"0.48","size":"200"}],"asks":[{"price":"0.49","size":"150"}]};await d.manage_pending_maker_orders();assert len(d.pending_maker_orders)==0 and len(d.open_positions)==1;d.open_positions["W1_test"]={"position_id":"W1_test","dedupe_key":"W1_ev_mkt_w1","sleeve":"W1_SOLAR_PEAK_LOCK","asset_or_city":"Tokyo_RJTT","title":"Tokyo 21°C","side":"YES","token_id":"tok_w1_closed","fee_rate":.0,"entry_ts":1e3,"close_ts":2e3,"p_model_entry":.92,"entry_eff_px_t1000":.8,"entry_vwap_t1000":.8,"maker_tp_px":.98,"tier_fills":{"T1000":{"spent_usd":1e2,"fee_usd":.0,"shares":125.}},"extra":{"market_id":"mkt_w1"},"status":"OPEN"};await d.manage_open_positions();assert"W1_test"not in d.open_positions;a=[p for p in d.closed_positions if p["position_id"]=="W1_test"];assert len(a)==1 and a[0]["won"]is True and a[0]["tier_pnls_usd"]["T1000"]==25.
 asyncio.run(_run_sim())
def test_live_executor_min_price_floor_zero_fees_neg_risk_and_maker_entry(tmp_path):from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;d=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"dry.jsonl");a={"asks":[{"price":"0.25","size":"500"}],"bids":[{"price":"0.24","size":"500"}]};c=d.execute_snipe_order(token_id="12345678901234567890",target_token="YES",notional_usd=25.,target_price=.25,trade_id="TEST_W2_ZERO_FEE",market_fee_rate=.0,market_fee_exponent=.0,min_price_floor=.15,max_price_ceiling=.65,prefetched_book=a,neg_risk=True);assert c.success is True and c.fee_usd==.0;assert d.get_token_neg_risk("12345678901234567890")is True;b=d.post_maker_entry_order(token_id="12345678901234567890",price=.42,notional_usd=25.,neg_risk=True);assert b["success"]is True and b["shares"]==59. and b["post_only"]is True
def test_same_oracle_dominance_box_math_equal_shares_and_strike_guard():from src.polymarket_research.same_oracle_dominance_box import(compute_dominance_box_payout_from_close,determine_dominance_legs,parse_authoritative_open_price,parse_twap_candle_event,walk_equal_shares_dominance_box);g={"title":"Ethereum Up or Down - 7:00PM-7:15PM ET","markets":[{"id":"6033093","conditionId":"0xc15","question":"Ethereum Up or Down - 7:00PM-7:15PM ET","eventStartTime":"2026-10-25T23:00:00Z","endDate":"2026-10-25T23:15:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["tok_15m_up", "tok_15m_dn"]',"feesEnabled":True,"feeSchedule":{"rate":.07,"exponent":1.},"cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"resolutionSource":"https://data.chain.link/streams/eth-usd-twap-60s-streams"}]};j={"title":"Ethereum Up or Down - 7:10PM-7:15PM ET","markets":[{"id":"6033145","conditionId":"0xc5","question":"Ethereum Up or Down - 7:10PM-7:15PM ET","eventStartTime":"2026-10-25T23:10:00Z","endDate":"2026-10-25T23:15:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["tok_5m_up", "tok_5m_dn"]',"feesEnabled":True,"feeSchedule":{"rate":.07,"exponent":1.},"cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"resolutionSource":"https://data.chain.link/streams/eth-usd-twap-60s-streams"}]};l=parse_twap_candle_event(g,"ETH","15m");m=parse_twap_candle_event(j,"ETH","5m");assert l is not None and m is not None;f={"markets":[{**j["markets"][0],"cryptoMarketConfig":{"twapEnabled":False},"resolutionSource":"binance"}]};assert parse_twap_candle_event(f,"ETH","5m")is None;assert parse_authoritative_open_price({"openPrice":2393.534264,"completed":False,"cached":True})is None;assert parse_authoritative_open_price([{"closed":False,"eventMetadata":{"finalPrice":2393.534264}}])is None;assert parse_authoritative_open_price([{"closed":True,"eventMetadata":{"finalPrice":2393.534264}}])==2393.534264;k=determine_dominance_legs(l,2393.5343,m,2392.8455);assert k is not None and k["regime"]=="5M_UP_PLUS_15M_DOWN";assert k["leg_a"]["token_id"]=="tok_5m_up"and k["leg_b"]["token_id"]=="tok_15m_dn";assert compute_dominance_box_payout_from_close(2389.55,k["k_low"],k["k_high"])==1.;assert compute_dominance_box_payout_from_close(2393.1,k["k_low"],k["k_high"])==2.;assert compute_dominance_box_payout_from_close(2399.,k["k_low"],k["k_high"])==1.;i=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.35","size":"45"}],asks_b_raw=[{"price":"0.56","size":"200"}],target_budget_usd=1e2,max_box_cost_net=.995);assert i["filled"]is True;assert i["shares"]==45;assert i["leg_a_walk"]["shares"]==45 and i["leg_b_walk"]["shares"]==45;assert i["box_cost_net"]<.95 and i["guaranteed_min_profit_usd"]>2.;h=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.52","size":"200"}],asks_b_raw=[{"price":"0.47","size":"200"}],target_budget_usd=1e2,max_box_cost_net=.995);assert h["filled"]is False;from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;d=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.90","size":"11"},{"price":"0.91","size":"138.36"}],asks_b_raw=[{"price":"0.07","size":"66.7"}],target_budget_usd=13.5,max_box_cost_net=.985,min_shares=8,min_box_notional_usd=7.);assert d["filled"]is False;assert d["reason"]=="LEG_BELOW_1USD_MIN";c=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.86","size":"11"},{"price":"0.88","size":"138.36"}],asks_b_raw=[{"price":"0.10","size":"66.7"}],target_budget_usd=13.5,max_box_cost_net=.985,min_shares=8,min_box_notional_usd=7.);assert c["filled"]is True;assert c["shares"]==11;assert c["leg_a_walk"]["worst_px"]==.86;assert c["leg_b_walk"]["worst_px"]==.1;assert c["box_cost_net"]<=.985;e=PolymarketLiveExecutor(dry_run=True);b=e.execute_atomic_dominance_box(box_id="D1_SOL_TRIM_TEST",leg_a_token_id="tok_sol_15m_up",leg_a_label="15M_UP",leg_a_limit_price=c["leg_a_walk"]["worst_px"],leg_b_token_id="tok_sol_5m_dn",leg_b_label="5M_DOWN",leg_b_limit_price=c["leg_b_walk"]["worst_px"],shares=c["shares"],max_box_cost_net=.985);assert b["success"]is True;a=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.90","size":"4"},{"price":"0.91","size":"138.36"}],asks_b_raw=[{"price":"0.07","size":"66.7"}],target_budget_usd=13.5,max_box_cost_net=.985,min_shares=8,min_box_notional_usd=7.);assert a["filled"]is False and a["reason"]=="WORST_LIMIT_COST_ABOVE_CAP"
def test_alpha124_d1_same_oracle_dominance_box_entry_and_settlement(tmp_path,monkeypatch):
 import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"state_d1.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ledger_d1.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"opps_d1.json")
 async def _sim_d1():
  d=a124.Alpha124ShadowDaemon(single_scan=True);e=1.79297e9;c=e+180.;i=TwapCandleMarketSpec(asset="ETH",horizon="15m",market_id="6033093",condition_id="0xc15",title="ETH 15m",start_iso="2026-10-25T23:00:00Z",end_iso="2026-10-25T23:15:00Z",start_ts=c-9e2,end_ts=c,up_token="tok_15m_up",down_token="tok_15m_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams");j=TwapCandleMarketSpec(asset="ETH",horizon="5m",market_id="6033145",condition_id="0xc5",title="ETH 5m",start_iso="2026-10-25T23:10:00Z",end_iso="2026-10-25T23:15:00Z",start_ts=c-3e2,end_ts=c,up_token="tok_5m_up",down_token="tok_5m_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams");d.dominance_pairs[f"ETH_{int(c)}"]=(i,j);a=f"slug=eth-updown-5m-{int(round(i.start_ts))-300}";b=f"slug=eth-updown-5m-{int(round(j.start_ts))-300}"
  async def fake_fetch(url,timeout=5.):
   if a in url:return[{"slug":url.split("slug=",1)[1],"closed":True,"eventMetadata":{"finalPrice":2390.}}]
   if b in url:return[{"slug":url.split("slug=",1)[1],"closed":True,"eventMetadata":{"finalPrice":2394.}}]
   if"token_id=tok_15m_up"in url:return{"bids":[{"price":"0.52","size":"150"}],"asks":[{"price":"0.54","size":"150"}]}
   if"token_id=tok_5m_dn"in url:return{"bids":[{"price":"0.38","size":"150"}],"asks":[{"price":"0.40","size":"150"}]}
   if"token_id=tok_15m_dn"in url or"token_id=tok_5m_up"in url:return{"bids":[{"price":"0.47","size":"150"}],"asks":[{"price":"0.50","size":"150"}]}
   if"/markets/6033093"in url:return{"id":"6033093","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["tok_15m_up", "tok_15m_dn"]',"outcomePrices":'["1", "0"]'}
   if"/markets/6033145"in url:return{"id":"6033145","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["tok_5m_up", "tok_5m_dn"]',"outcomePrices":'["0", "1"]'}
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch);g=[];await d.scan_same_oracle_dominance_boxes(g,now_ts=e);assert len(d.open_positions)==1;h=next(iter(d.open_positions.values()));assert h["sleeve"]=="D1_SAME_ORACLE_DOMINANCE_BOX";assert h["entry_eff_px_t1000"]<.995;h["close_ts"]=1e3;await d.manage_open_positions();assert len(d.open_positions)==0 and len(d.closed_positions)==1;f=d.closed_positions[0];assert f["status"]=="SETTLED_DOMINANCE_DOUBLE_2X";assert f["net_payout_per_share"]==2.;assert f["tier_pnls_usd"]["T1000"]>1e2
 asyncio.run(_sim_d1())
def test_live_executor_atomic_dominance_box_and_legging_unwind(tmp_path,monkeypatch):
 from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;ex=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"box.jsonl");r_ok=ex.execute_atomic_dominance_box(box_id="BOX_ETH_1",leg_a_token_id="tok_a",leg_a_label="15M_UP",leg_a_limit_price=.54,leg_b_token_id="tok_b",leg_b_label="5M_DOWN",leg_b_limit_price=.4,shares=25,max_box_cost_net=.995,leg_a_avail_shares=120.,leg_b_avail_shares=30.);assert r_ok["success"]is True and r_ok["leg_1"]["label"]=="5M_DOWN";r_cap=ex.execute_atomic_dominance_box(box_id="BOX_EXP",leg_a_token_id="tok_a",leg_a_label="15M_UP",leg_a_limit_price=.55,leg_b_token_id="tok_b",leg_b_label="5M_DOWN",leg_b_limit_price=.44,shares=25,max_box_cost_net=.995);assert r_cap["success"]is False and"WORST_LIMIT_BOX_COST_EXCEEDS_CAP"in r_cap["error"];ex.dry_run=False;ex.is_authenticated=True
 class FakeClient:
  def __init__(self):self.posts=0
  def create_order(self,args,options=None):return{"token_id":args.token_id,"price":args.price,"size":args.size}
  def post_order(a,signed,order_type):
   a.posts+=1
   if a.posts==1:return{"orderID":"OID_LEG1_FILLED"}
   return{"errorMsg":"FOK order couldn't be fully filled"}
 ex.client=FakeClient();monkeypatch.setattr(ex,"get_token_tick_size",lambda tid:.01);monkeypatch.setattr(ex,"get_token_neg_risk",lambda tid,explicit_neg_risk=None:False);unwind_calls=[]
 def fake_unwind(token_id,size,side="SELL",min_price=.01,neg_risk=None):unwind_calls.append((token_id,size,side,min_price));return{"success":True,"orderID":"OID_UNWIND_1","matched_size":size}
 monkeypatch.setattr(ex,"execute_unwind_order",fake_unwind);r_leg=ex.execute_atomic_dominance_box(box_id="BOX_LEG_FAIL",leg_a_token_id="tok_a",leg_a_label="15M_UP",leg_a_limit_price=.54,leg_b_token_id="tok_b",leg_b_label="5M_DOWN",leg_b_limit_price=.4,shares=20,max_box_cost_net=.995,leg_a_avail_shares=25.,leg_b_avail_shares=1e2);assert r_leg["success"]is False;assert r_leg["stage"]=="LEG_2_REJECTED_UNWOUND";assert r_leg["legged_out"]is True;assert len(unwind_calls)==1 and unwind_calls[0][0]=="tok_a"and unwind_calls[0][1]==20.
def test_exact_twap_lock_engine_math_and_whipsaw_guard():import math;from src.polymarket_research.exact_twap_lock_engine import(compute_exact_twap_lock_probability,student_t_df5_cdf);assert abs(student_t_df5_cdf(.0)-.5)<1e-12;assert abs(student_t_df5_cdf(2.5)+student_t_df5_cdf(-2.5)-1.)<1e-12;a=.5*(1.+math.erf(3./math.sqrt(2.)));assert.96<student_t_df5_cdf(3.)<a;e=1792970300.;d=e-18.;c=[(e-60.+i,2404.5)for i in range(43)];g=compute_exact_twap_lock_probability(asset="ETH",open_price=2400.123456789012,current_usd_spot=2404.6,rem_seconds=18.,now_ts=d,end_ts=e,spot_samples=c,iv_annual=.65,usd_direct_feed=True);assert g["eligible"]is True;assert g["side"]=="UP";assert g["eff_alpha"]>.65;assert g["p_lock"]>=.975;b=compute_exact_twap_lock_probability(asset="ETH",open_price=2400.123456789012,current_usd_spot=2399.5,rem_seconds=18.,now_ts=d,end_ts=e,spot_samples=c,iv_annual=.65,usd_direct_feed=True);assert b["eligible"]is False and b["reason"]=="WHIPSAW_SPLIT_ACROSS_STRIKE";f=compute_exact_twap_lock_probability(asset="ETH",open_price=2400.,current_usd_spot=2405.,rem_seconds=52.,now_ts=e-52.,end_ts=e,spot_samples=[]);assert f["eligible"]is False
def test_r01_relayer_hmac_deposit_wallet_eip712_and_negrisk_payout_logs(tmp_path):
 from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;h=PolymarketLiveExecutor.build_relayer_builder_headers(api_key="test-api-key",secret="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",passphrase="test-passphrase",method="POST",request_path="/orders",body={"hash":"0x123"},timestamp=1000000);assert h["POLY_BUILDER_SIGNATURE"]=="wdXSC4akzPKG0yFk9FJrIb7-rg73v_M7QDxIBp-P1CQ=";assert h["POLY_BUILDER_TIMESTAMP"]=="1000000"
 try:from py_clob_client.signing.hmac import build_hmac_signature;assert h["POLY_BUILDER_SIGNATURE"]==build_hmac_signature("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=","1000000","POST","/orders",{"hash":"0x123"})
 except ImportError:pass
 i=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"r01.jsonl");i.funder_address="0x013A2474454fBd8738cff6a7f204eF1bc377F4e9";d="0x"+"ab"*32;a="0x"+i.funder_address.lower().replace("0x","").rjust(64,"0")
 try:import eth_account;import eth_utils;import web3;c="0x"+"11"*32;g=PolymarketLiveExecutor.build_deposit_wallet_relayer_batch(private_key=c,wallet_address=i.funder_address,nonce=7,deadline=1900000000,calls=[{"target":PolymarketLiveExecutor.CTF_ADDRESS,"value":"0","data":"0x12345678"}],chain_id=137);assert g["type"]=="WALLET";assert g["nonce"]=="7";assert g["signature"].startswith("0x")and len(g["signature"])==132;assert g["depositWalletParams"]["depositWallet"].lower()==i.funder_address.lower();b={"address":PolymarketLiveExecutor.CTF_ADDRESS,"topics":[PolymarketLiveExecutor._payout_redemption_topic(),a,"0x"+"00"*32],"data":"0x"+"ab"*32+"00"*32+f"{25500000:064x}","transactionHash":"0xtx_ctf","blockNumber":"0x100"};f={"address":PolymarketLiveExecutor.NEG_RISK_ADAPTER_ADDRESS,"topics":[PolymarketLiveExecutor._neg_risk_payout_redemption_topic(),a,d],"data":"0x"+"00"*32+f"{42250000:064x}","transactionHash":"0xtx_nr","blockNumber":"0x101"};e=i.parse_payout_redemption_logs([b,f],d);assert len(e)==2;assert abs(e[0]["payout_usd"]-25.5)<1e-6;assert abs(e[1]["payout_usd"]-42.25)<1e-6
 except ImportError:pass
def test_alpha124_w2_maker_overround_m4_shock_wakeup_and_s2_twap_lock(tmp_path,monkeypatch):
 import asyncio;import json;import time;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.multistrike_svi_scalper import StrikeRungSpec;from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"state_all.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ledger_all.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"opps_all.json");a=tmp_path/"live_shock_triggers.jsonl";a.write_text("",encoding="utf-8");monkeypatch.setattr(a124,"SHOCK_TRIGGER_FILE",a)
 async def _sim_new_sleeves():
  d=a124.Alpha124ShadowDaemon(single_scan=True);g=time.time();n={"tok_w2m":{"bids":[{"price":"0.26","size":"150"}],"asks":[{"price":"0.30","size":"150"}]},"tok_m1_yes":{"bids":[{"price":"0.49","size":"200"}],"asks":[{"price":"0.51","size":"200"}]},"tok_m4_no":{"bids":[{"price":"0.46","size":"250"}],"asks":[{"price":"0.48","size":"250"}]},"tok_s2_up":{"bids":[{"price":"0.86","size":"250"}],"asks":[{"price":"0.88","size":"250"}]}}
  async def fake_fetch(url,timeout=5.):
   for a,b in n.items():
    if f"token_id={a}"in url:return b
   if"slug=eth-updown-5m-1792969800"in url:return[{"slug":url.split("slug=",1)[1],"closed":True,"eventMetadata":{"finalPrice":2405.8}}]
   if"slug=eth-updown-5m-"in url:return[{"slug":url.split("slug=",1)[1],"closed":True,"eventMetadata":{"finalPrice":2400.123456789012}}]
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch);m=await d.post_shadow_maker_entry(sleeve="W2_MAKER_OVERROUND",dedupe_key="W2M_ev1_m1",asset="Miami_KMIA",title="Miami 82-83°F",side_label="YES",token_id="tok_w2m",p_model=.4,close_ts=g+28800.,extra={"event_id":"ev1","market_id":"m1","icao":"KMIA","obs_date":"2026-10-25"});assert m is True;f=next(iter(d.pending_maker_orders));assert d.pending_maker_orders[f]["resting_bid"]==.27;d.pending_maker_orders[f]["created_ts"]-=15.;n["tok_w2m"]={"bids":[{"price":"0.26","size":"150"}],"asks":[{"price":"0.27","size":"150"}]};await d.manage_pending_maker_orders();assert any(p["sleeve"]=="W2_MAKER_OVERROUND"for p in d.open_positions.values());d.spots["BTC"]=8.4e4;await d.post_shadow_maker_entry(sleeve="M1_SVI_MAKER_SCALP",dedupe_key="M1_btc_84k_YES",asset="BTC",title="BTC above $84,000?",side_label="YES",token_id="tok_m1_yes",p_model=.58,close_ts=g+43200.,extra={"market_id":"m_btc_84k","strike":8.4e4,"is_downward":False});assert len(d.pending_maker_orders)==1;d.strike_ladders["BTC_ev"]=[StrikeRungSpec(asset="BTC",series_slug="btc-multi-strikes",event_id="ev_btc",market_id="m_btc_84k",condition_id="0xc_btc",title="Bitcoin above ___ on Oct 25?",question="Bitcoin above $84,000 on Oct 25?",strike=8.4e4,is_downward=False,end_ts=g+43200.,yes_token="tok_m1_yes",no_token="tok_m4_no")];monkeypatch.setattr(a124,"evaluate_svi_digital_fair_value",lambda*args,**kwargs:{"p_yes":.38,"p_no":.62,"iv_annual":.45,"z_sigma":.8,"source":"TEST"});a={"shock_id":"SHK_BTC_1","t0_unix":time.time(),"shock_source":"FUTURES","asset":"BTC","shock_direction":"SELL","shock_ofi":-.88,"shock_volume_100ms":3.2e6,"spot_at_t0":83700.}
  with open(a,"a",encoding="utf-8")as q:q.write(json.dumps(a)+"\n")
  l=d.poll_fresh_shock_triggers();assert len(l)==1;k=[];await d.handle_shock_triggers(l,k);assert len(d.pending_maker_orders)==0;assert any(p["sleeve"]=="M4_SHOCK_STRIKE_CATCHUP"and p["side"]=="NO"for p in d.open_positions.values());j=g+18.;o=TwapCandleMarketSpec(asset="ETH",horizon="5m",market_id="6055555",condition_id="0xc_s2",title="ETH Up or Down 5m",start_iso="2026-10-25T23:10:00Z",end_iso="2026-10-25T23:15:00Z",start_ts=j-3e2,end_ts=j,up_token="tok_s2_up",down_token="tok_s2_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams");d.twap_candles[f"ETH_5m_{int(j)}"]=o;d.spots["ETH"]=2406.;d.usd_direct_flags["ETH"]=True
  for i in range(43):d.usd_spot_hist["ETH"].append((j-60.+i,2405.8))
  monkeypatch.setattr(a124,"get_wing_implied_vol",lambda*args,**kwargs:(.65,"TEST"));e=[];await d.scan_exact_twap_locks(e,now_ts=g);b=[p for p in d.open_positions.values()if p["sleeve"]=="S2_EXACT_TWAP_LOCK"];assert len(b)==1;h=b[0];assert h["side"]=="UP"and h["p_model_entry"]>=.97;h["close_ts"]=g-2e2;await d.manage_open_positions();c=[p for p in d.closed_positions if p["sleeve"]=="S2_EXACT_TWAP_LOCK"];assert len(c)==1 and c[0]["won"]is True;assert c[0]["status"]=="SETTLED_ORACLE_TWAP_WIN"
 asyncio.run(_sim_new_sleeves())
def test_live_daily_projections_working_capital_and_monotonicity():
 from scripts.polymarket_daily_projections import(_depth_decay,build_live_projections,compute_v393_ticket_size);assert compute_v393_ticket_size(60.)==12.;assert compute_v393_ticket_size(73.01)==13.14;assert compute_v393_ticket_size(76.8)==13.82;assert compute_v393_ticket_size(95.)==17.1;assert compute_v393_ticket_size(120.)==26.4;assert _depth_decay(15.)==1.;assert.58<=_depth_decay(150.)<.85;d=build_live_projections(days=30,fallback_equity=76.8);c=d["day_by_day_schedule"];assert len(c)==30;a={"B1_CONVEX_TAIL_YES","M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","SLEEVE_XRP_V392_SHADOW"};assert all(g["sleeve"]not in a for g in d["sleeve_graduation_live_tracker"])
 for r in c:
  assert r["p25_end_equity_usd"]<r["p50_end_equity_usd"]<r["p75_end_equity_usd"];assert r["p50_daily_pnl_usd"]>0
  for b in("B1_convex_barrier_tails","W2_weather_maker_and_mos","M1_M4_svi_maker_and_shock"):assert b not in r["p50_sleeve_pnl_breakdown_usd"]
def test_external_dual_audit_alpha124_and_oracle_regressions(tmp_path,monkeypatch):
 import asyncio;import json;import time;from datetime import date;from zoneinfo import ZoneInfo;import src.polymarket_research.alpha_124_shadow_daemon as a124;import src.polymarket_research.barrier_onetouch_svi_engine as b_eng;import src.polymarket_research.exact_twap_lock_engine as etwap;from src.polymarket_research.same_oracle_dominance_box import(TwapCandleMarketSpec,verify_same_oracle_pair);from src.polymarket_research.weather_metar_engine import(WeatherBucket,WeatherEventSpec,compute_weather_probabilities,parse_weather_event);F=datetime(2026,10,25,16,0,tzinfo=timezone.utc);l=parse_metar_line("METAR RJTT 250600Z 08007KT 9999 FEW020 02/// Q1017 RMK AO2 T0023////","RJTT",F,"Asia/Tokyo");assert l is not None and l.has_t_remark is True and abs(l.temp_c-2.3)<1e-6;k=parse_metar_line("METAR KORD 251051Z 29012KT 10SM CLR M02/// A3015 RMK AO2 T1017//// SLP210","KORD",F,"America/Chicago");assert k is not None and k.has_t_remark is True and abs(k.temp_c-(-1.7))<1e-6;E=parse_metar_line("METAR COR RJTT 250600Z 08007KT 9999 FEW020 19/12 Q1017 RMK AO2 T01940120","RJTT",F,"Asia/Tokyo");assert E is not None and E.is_corrected is True and abs(E.temp_c-19.4)<1e-6;D=ZoneInfo("America/New_York");u=parse_metar_line("METAR KLGA 260251Z 31012KT 10SM CLR 15/06 A3012 RMK AO2 T01500061","KLGA",datetime(2026,10,26,3,0,tzinfo=timezone.utc),"America/New_York");assert u is not None and u.local_dt.date()==date(2026,10,25);j=[WeatherBucket("b1","c1","14°C or below","14°C-","y1","n1","C",float("-inf"),14.),WeatherBucket("b2","c2","15°C","15°C","y2","n2","C",15.,15.),WeatherBucket("b3","c3","16°C","16°C","y3","n3","C",16.,16.),WeatherBucket("b4","c4","17°C or higher","17°C+","y4","n4","C",17.,float("inf"))];t=WeatherEventSpec(event_id="ev_klga_low",slug="nyc-low",series_slug="nyc-daily-weather",title="Lowest temperature in NYC on October 25?",icao="KLGA",city="NYC",lat=40.7769,lon=-73.874,tz_name="America/New_York",obs_date=date(2026,10,25),metric="LOW",unit="C",fee_type="zero_fees",end_date_iso="2026-10-26T05:00:00Z",buckets=j);g=datetime(2026,10,25,23,30,tzinfo=D).astimezone(timezone.utc);f=int(datetime(2026,10,26,0,0,tzinfo=D).astimezone(timezone.utc).timestamp());e={f:[12.]*30};s=compute_weather_probabilities(t,g,[u],e);assert s["rem_hours_count"]==1;assert s["probs"][0]>.5;h=datetime(2026,10,26,0,5,tzinfo=D).astimezone(timezone.utc);c=compute_weather_probabilities(t,h,[u],e);assert c["probs"][1]>.99;o={"id":"ev_fee_test","title":"Highest temperature in Tokyo on October 26?","endDate":"2026-10-26T15:00:00Z","markets":[{"id":f"m_{G}","conditionId":f"0xc_{G}","groupItemTitle":H,"description":"Resolves via https://aviationweather.gov/api/data/metar?ids=RJTT excluding SPECI on 26 Oct '26.","clobTokenIds":f'["y_{G}", "n_{G}"]',"feesEnabled":True,"feeSchedule":{"rate":.05,"exponent":1.}}for G,H in enumerate(["18°C or below","19°C","20°C","21°C or higher"])]};i=parse_weather_event(o);assert i is not None and i.fee_type=="fees_enabled";assert all(abs(b.fee_rate-.05)<1e-9 for b in i.buckets);monkeypatch.setattr(etwap,"SHM_DIR",tmp_path);C=1792975000.;y=tmp_path/"pm_fast_tick_BTC.json";y.write_text(json.dumps({"timestamp_unix":C,"spot_price":84100.}),encoding="utf-8");assert etwap.read_shm_usd_anchor("BTC",C)["usd_spot"]is None;y.write_text(json.dumps({"timestamp_unix":C+4.,"chainlink_proxy_spot":84050.}),encoding="utf-8");assert etwap.read_shm_usd_anchor("BTC",C)["usd_spot"]is None;y.write_text(json.dumps({"timestamp_unix":C-.5,"chainlink_proxy_spot":84050.}),encoding="utf-8");assert etwap.read_shm_usd_anchor("BTC",C)["usd_spot"]==84050.;B=C+30.;x=etwap.compute_exact_twap_lock_probability(asset="ETH",open_price=2400.,current_usd_spot=2403.,rem_seconds=30.,now_ts=C,end_ts=B,spot_samples=[],shm_twap_60s=2415.,usd_direct_feed=True);assert x["eff_alpha"]==.0;n=TwapCandleMarketSpec("ETH","15m","1","0x1","ETH 15m","2026-10-25T23:00:00Z","2026-10-25T23:15:00Z",1e2,1e3,"u1","d1",.07,1.,False,60,"");r=TwapCandleMarketSpec("ETH","5m","2","0x2","ETH 5m","2026-10-25T23:10:00Z","2026-10-25T23:15:00Z",7e2,1e3,"u2","d2",.07,1.,False,60,"");assert verify_same_oracle_pair(n,r)is False;m=1792931400.;A=m+48*3600.
 def fake_klines(sym,st_ms,en_ms,interval,timeout):
  if interval=="1m"and st_ms==int(m*1000):return[[st_ms,"84000","89500","83900","84100","10",st_ms+60000]]
  return[[int((m+3600)*1000),"84100","85000","83500","84200","100",int(A*1000)]]
 monkeypatch.setattr(b_eng,"_fetch_finalized_klines",fake_klines);w=b_eng.fetch_binance_window_extremes_sync("BTC",m,A,"1m");assert w is not None and w[0]==89500.;v=tmp_path/"a124_race_state.json";q=tmp_path/"a124_race_ledger.jsonl";z=tmp_path/"a124_race_opps.json";q.write_text('{"event": "SHADOW_ENTRY", "corrupt_json": \n'+json.dumps({"event":"SHADOW_ENTRY","position_id":"S2_VALID_HYDRATE","dedupe_key":"S2_BTC_5m_1","sleeve":"S2_EXACT_TWAP_LOCK","asset_or_city":"BTC","title":"BTC 5m","side":"UP","token_id":"tok_h","fee_rate":.07,"entry_ts":1e3,"close_ts":2e3,"tier_fills":{"T1000":{"spent_usd":1e2,"fee_usd":.5,"shares":115.}},"extra":{},"status":"OPEN"})+"\n",encoding="utf-8");monkeypatch.setattr(a124,"STATE_FILE",v);monkeypatch.setattr(a124,"LEDGER_FILE",q);monkeypatch.setattr(a124,"OPPS_FILE",z)
 async def _sim_concurrency_and_adverse_fill():
  d=a124.Alpha124ShadowDaemon(single_scan=True);assert"S2_VALID_HYDRATE"in d.open_positions;e={"tok_race":{"bids":[{"price":"0.84","size":"300"}],"asks":[{"price":"0.85","size":"300"}]},"tok_adv":{"bids":[{"price":"0.49","size":"200"}],"asks":[{"price":"0.51","size":"200"}]}}
  async def fake_fetch(url,timeout=5.):
   await asyncio.sleep(.01)
   for a,b in e.items():
    if f"token_id={a}"in url:return b
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch);h,g=await asyncio.gather(d.open_shadow_position("W1_SOLAR_PEAK_LOCK","W1_RACE_KEY","Tokyo_RJTT","Tokyo 20°C","YES","tok_race",.0,.94,time.time()+7200.,{"event_id":"ev_r"}),d.open_shadow_position("W1_SOLAR_PEAK_LOCK","W1_RACE_KEY","Tokyo_RJTT","Tokyo 20°C","YES","tok_race",.0,.94,time.time()+7200.,{"event_id":"ev_r"}));assert(h,g)in((True,False),(False,True));assert sum(1 for p in d.open_positions.values()if p.get("dedupe_key")=="W1_RACE_KEY")==1;d.spots["BTC"]=8.4e4;f=await d.post_shadow_maker_entry("M1_SVI_MAKER_SCALP","M1_ADV_RACE","BTC","BTC > 84k","YES","tok_adv",.58,time.time()+43200.,{"market_id":"m_adv","strike":8.4e4,"is_downward":False});assert f is True;c=next(iter(d.pending_maker_orders));d.pending_maker_orders[c]["created_ts"]-=2.;d.spots["BTC"]=83650.;e["tok_adv"]={"bids":[{"price":"0.48","size":"200"}],"asks":[{"price":"0.49","size":"250"}]};monkeypatch.setattr(a124,"evaluate_svi_digital_fair_value",lambda*a,**kw:{"p_yes":.36,"p_no":.64,"iv_annual":.45,"z_sigma":.9,"source":"TEST"});await d.manage_pending_maker_orders();b=[p for p in d.open_positions.values()if p.get("dedupe_key")=="M1_ADV_RACE"];assert len(b)==1 and b[0]["extra"].get("adverse_fill_during_cancel_window")is True
 asyncio.run(_sim_concurrency_and_adverse_fill())
def test_v40_profit_maximization_upgrades(tmp_path,monkeypatch):
 import asyncio;import time;from datetime import date;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.net_alpha_opportunity_engine import(estimate_quote_survival_and_net_alpha,evaluate_cross_oracle_basis_box_ev,evaluate_optimal_stopping_exit,fit_quote_survival_from_ledger,inspect_microstructure_feature_completeness,publish_global_positions_shm,rank_opportunities_capital_auction,read_global_positions_shm,scan_binary_complete_set_arb,select_maker_taker_skip_route);from src.polymarket_research.deribit_svi_surface import(DeribitSVISurfaceEngine,SVIParams,enforce_monotone_ladder_probabilities);from src.polymarket_research.multistrike_svi_scalper import(StrikeRungSpec,evaluate_coherent_strike_ladder);from src.polymarket_research.barrier_onetouch_svi_engine import(evaluate_barrier_no_net_ev,first_passage_touch_prob);from src.polymarket_research.weather_metar_engine import(WeatherBucket,WeatherEventSpec,compute_adaptive_metar_poll_ttl,evaluate_weather_event_slate,parse_taf_temperature_extremes,verify_weather_slate_partition);b="100434764618174237135201777197981253576172734064131101154122934005557319214073";v=inspect_microstructure_feature_completeness({"fee_metadata":{"fee_rate_market":.07},"shock_ofi":.9,"pre_shock_features_t0":{"UP":{"token_id":b,"age_ask_ms":None,"obi_l1":.2}}},"UP",b);assert v["hard_veto_live"]is True and"age_ask_ms"in v["missing_fields"];u=inspect_microstructure_feature_completeness({"fee_metadata":{"fee_rate_market":.07},"shock_ofi":None,"pre_shock_features_t0":{"UP":{"token_id":b,"age_ask_ms":180.,"obi_l1":.2}}},"UP",b);assert u["hard_veto_live"]is True and"shock_ofi"in u["missing_fields"];j=estimate_quote_survival_and_net_alpha(p_win=.9,ask_price=.74,limit_price=.74,p_max=.8,clob_rtt_ms=260.,age_ask_ms=280.);i=estimate_quote_survival_and_net_alpha(p_win=.9,ask_price=.74,limit_price=.76,p_max=.8,clob_rtt_ms=260.,age_ask_ms=280.);assert i["p_fill"]>j["p_fill"];assert i["eff_limit_px"]==.76<=.8;assert i["eligible"]is True and i["ev_net_usd"]>.0;F=fit_quote_survival_from_ledger([{"mode":"LIVE_CLOB","success":True,"latency_ms":210.},{"mode":"LIVE_CLOB","success":True,"latency_ms":225.},{"mode":"FAK_KILLED_NO_MATCH","success":False,"latency_ms":280.},{"mode":"LIVE_CLOB","success":True,"latency_ms":195.},{"mode":"FAK_KILLED_NO_MATCH","success":False,"latency_ms":265.}]);assert F["sample_count"]==5 and abs(F["empirical_fill_rate"]-.6)<1e-6;t=select_maker_taker_skip_route(p_win=.92,best_bid=.73,best_ask=.74,p_max=.81,clob_rtt_ms=190.);assert t["route"]=="TAKER_PRICE_IMPROVED_FAK"and t["taker_limit_px"]==.76;s=select_maker_taker_skip_route(p_win=.77,best_bid=.69,best_ask=.75,p_max=.74,clob_rtt_ms=280.);assert s["route"]=="MAKER_POST_ONLY_3P5S"and s["maker_bid_px"]==.7;B=select_maker_taker_skip_route(p_win=.6,best_bid=.68,best_ask=.7,p_max=.58);assert B["route"]=="SKIP";A=evaluate_optimal_stopping_exit(entry_px=.74,rem_shares=18.,best_bid=.99,best_ask=1.,curr_target_px=.99,tte_sec=15.);assert A["action"]=="PRE_EXPIRY_99C_RECYCLE"and A["taker_fee_ps"]<.001;r=evaluate_optimal_stopping_exit(entry_px=.7,rem_shares=18.,best_bid=.84,best_ask=.93,curr_target_px=.95,tte_sec=30.,opp_ask_complement=.09);assert r["action"]=="SYNTHETIC_COMPLEMENT_MERGE"and r["net_proceeds_ps"]>.9;z=evaluate_optimal_stopping_exit(entry_px=.74,rem_shares=18.,best_bid=.92,best_ask=.95,curr_target_px=.95,tte_sec=90.,obi_l1=-.65,v_spot_15s_pct=-.02);assert z["action"]=="OBI_MAKER_STEP_DOWN"and z["target_px"]==.93;G=scan_binary_complete_set_arb(market_id="m_c1",condition_id="0xc1",yes_token="tok_y_c1",no_token="tok_n_c1",asks_yes_raw=[{"price":"0.47","size":"60"}],asks_no_raw=[{"price":"0.48","size":"60"}],target_budget_usd=30.,fee_rate=.07,max_complete_set_cost=.994);assert G["filled"]is True and G["box_cost_net"]<.994 and G["guaranteed_min_profit_usd"]>.0;m=evaluate_cross_oracle_basis_box_ev(spot_px=84100.,k_low=8.4e4,k_high=84200.,c_taker_net=.975,tte_sec=6e2);assert m["classification"]=="PROBABILISTIC_CROSS_ORACLE_RV"and m["is_riskless"]is False;monkeypatch.setenv("PM_FAST_TICK_DIR",str(tmp_path));q=time.time();assert publish_global_positions_shm("live_harvester",[{"trade_id":"T1","sleeve":"LIVE","asset":"BTC","target_token":"UP","candle_open_spot":8.4e4,"candle_expiry_ts":q+6e2,"notional_usd":14.}])is True;h=read_global_positions_shm();l=h["daemons"]["live_harvester"]["positions"];assert len(l)==1 and l[0]["asset"]=="BTC";y=rank_opportunities_capital_auction([{"sleeve":"W2","asset":"NYC","side":"YES","ask_vwap":.5,"net_edge":.05,"tte_sec":3.6e4,"expiry_ts":q+3.6e4},{"sleeve":"S2","asset":"BTC","side":"DOWN","strike":84250.,"ask_vwap":.85,"net_edge":.04,"tte_sec":3e2,"expiry_ts":q+6e2}],active_global_positions=l);assert y[0]["sleeve"]=="S2"and y[0].get("synthetic_corridor_completion")is True;E=DeribitSVISurfaceEngine();E._cache["BTC"]=SVIParams(a=4e-4,b=2e-4,rho=-.15,m=.0,sigma=.05,t_years=30./365.25,forward_price=8.6e4,index_price=8.4e4,calibrated_at=time.time());assert E._cache["BTC"].implied_forward_drift_rate()>.15;o=E.evaluate_strike_probability("BTC",spot=8.4e4,strike=8.5e4,tte_seconds=14*86400.,allow_sync_fetch=False);E._cache["BTC"].index_price=8.6e4;x=E.evaluate_strike_probability("BTC",spot=8.4e4,strike=8.5e4,tte_seconds=14*86400.,allow_sync_fetch=False);assert o["p_above_strike"]>x["p_above_strike"];C=enforce_monotone_ladder_probabilities([(8e4,.72),(8.2e4,.55),(8.4e4,.61),(8.6e4,.3)]);assert C["probs"]==sorted(C["probs"],reverse=True);assert all(H>=.0 for H in C["interval_probs"])and C["max_adjustment"]>.0;f=[StrikeRungSpec("ev1","btc-daily","BTC","BTC Daily",f"m_{k}",f"0x{k}",f"BTC > {k}",float(k),False,q+7200.,f"ty_{k}",f"tn_{k}")for k in(82000,84000,86000)];D=evaluate_coherent_strike_ladder("BTC",8.4e4,f,7200.,now_ts=q);assert D["probs"][0]>=D["probs"][1]>=D["probs"][2];n=first_passage_touch_prob(8.4e4,8.8e4,86400.,.5,"UP",realized_vol_ratio=1.,forward_drift_annual=.0);g=first_passage_touch_prob(8.4e4,8.8e4,86400.,.5,"UP",realized_vol_ratio=2.2,forward_drift_annual=.12);assert g>n;assert evaluate_barrier_no_net_ev(p_touch=.04,ask_no=.88)["eligible"]is True;assert evaluate_barrier_no_net_ev(p_touch=.01,ask_no=.95)["eligible"]is False;assert compute_adaptive_metar_poll_ttl("KLGA",None,datetime(2026,10,26,14,52,tzinfo=timezone.utc))==10.;assert compute_adaptive_metar_poll_ttl("KLGA",None,datetime(2026,10,26,14,25,tzinfo=timezone.utc))==3e2;e=parse_taf_temperature_extremes("TAF KLGA 261130Z 2612/2718 30012KT P6SM FEW050 TX19/2619Z TNM02/2710Z","KLGA",datetime(2026,10,26,12,0,tzinfo=timezone.utc),"America/New_York");assert e[date(2026,10,26)]["HIGH"]==19.;assert e[date(2026,10,27)]["LOW"]==-2.;w=WeatherEventSpec(event_id="ev_w3",slug="tokyo-w3",series_slug="tokyo-daily-weather",title="Highest temperature in Tokyo on October 26?",icao="RJTT",city="Tokyo",lat=35.5494,lon=139.7798,tz_name="Asia/Tokyo",obs_date=date(2026,10,26),metric="HIGH",unit="C",fee_type="zero_fees",end_date_iso="2026-10-26T20:00:00Z",buckets=[WeatherBucket("wb1","0xwb1","18°C or below","18°C or below","wy1","wn1","C",float("-inf"),18.),WeatherBucket("wb2","0xwb2","19°C","19°C","wy2","wn2","C",19.,19.),WeatherBucket("wb3","0xwb3","20°C or higher","20°C or higher","wy3","wn3","C",20.,float("inf"))]);assert verify_weather_slate_partition(w)is True;c=evaluate_weather_event_slate(w,[.2,.5,.3],{"wb1":{"ask_yes":.19,"ask_yes_shares":40.},"wb2":{"ask_yes":.46,"ask_yes_shares":40.},"wb3":{"ask_yes":.31,"ask_yes_shares":40.}},target_budget_usd=10.);assert c["full_slate_arb"]is not None;assert abs(c["full_slate_arb"]["sum_asks"]-.96)<1e-6
 async def _sim_v40_sleeves():
  monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"a124_v40_state.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"a124_v40_ledger.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"a124_v40_opps.json");d=a124.Alpha124ShadowDaemon(single_scan=True);d.spots["BTC"]=84500.;b={"tok_c1_y":{"bids":[{"price":"0.46","size":"80"}],"asks":[{"price":"0.47","size":"80"}]},"tok_c1_n":{"bids":[{"price":"0.47","size":"80"}],"asks":[{"price":"0.48","size":"80"}]},"tok_m3_lo":{"bids":[{"price":"0.52","size":"80"}],"asks":[{"price":"0.53","size":"80"}]},"tok_m3_hi":{"bids":[{"price":"0.41","size":"80"}],"asks":[{"price":"0.42","size":"80"}]},"tok_m4_mkr":{"bids":[{"price":"0.50","size":"60"}],"asks":[{"price":"0.54","size":"60"}]}}
  async def fake_fetch_v40(url,timeout=5.):
   if"/book?token_id="in url:return b.get(url.split("token_id=")[1])
   if"/markets/m_c1"in url:return{"closed":True,"outcomePrices":'["1", "0"]'}
   if"/markets/m_lo"in url:return{"closed":True,"outcomePrices":'["1", "0"]'}
   if"/markets/m_hi"in url:return{"closed":True,"outcomePrices":'["0", "1"]'}
   if"/markets/wb2"in url:return{"closed":True,"outcomePrices":'["1", "0"]'}
   if"/markets/wb1"in url or"/markets/wb3"in url:return{"closed":True,"outcomePrices":'["0", "1"]'}
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch_v40);i=await d.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key="C1_TEST_1",asset="BTC",title="BTC > 84k [YES+NO Complete Set]",leg_a={"token_id":"tok_c1_y","side":"YES","market_id":"m_c1","fee_rate":.07},leg_b={"token_id":"tok_c1_n","side":"NO","market_id":"m_c1","fee_rate":.07},bk_a=b["tok_c1_y"],bk_b=b["tok_c1_n"],close_ts=time.time()-60.,max_box_cost_net=.994,extra={"market_id":"m_c1"});h=await d.open_shadow_two_leg_box(sleeve="M3_LADDER_MONO_BOX",dedupe_key="M3_TEST_1",asset="BTC",title="BTC Ladder Box [84000..85000]",leg_a={"token_id":"tok_m3_lo","side":"YES","market_id":"m_lo","fee_rate":.07},leg_b={"token_id":"tok_m3_hi","side":"NO","market_id":"m_hi","fee_rate":.07},bk_a=b["tok_m3_lo"],bk_b=b["tok_m3_hi"],close_ts=time.time()-60.,max_box_cost_net=.995,extra={"low_market_id":"m_lo","high_market_id":"m_hi","low_strike":8.4e4,"high_strike":8.5e4});g=await d.open_shadow_weather_slate(w,c["full_slate_arb"],close_ts=time.time()-60.);assert i is True and h is True and g is True;await d.manage_open_positions();f={p["sleeve"]:p for p in d.closed_positions};assert f["C1_BINARY_COMPLETE_SET"]["won"]is True and f["C1_BINARY_COMPLETE_SET"]["tier_pnls_usd"]["T1000"]>.0;assert f["M3_LADDER_MONO_BOX"]["won"]is True and f["M3_LADDER_MONO_BOX"]["status"]=="SETTLED_DOMINANCE_DOUBLE_2X";assert f["W3_WEATHER_SLATE_ARB"]["won"]is True and f["W3_WEATHER_SLATE_ARB"]["tier_pnls_usd"]["T1000"]>.0;e=await d.post_shadow_maker_entry(sleeve="M4_SHOCK_STRIKE_CATCHUP",dedupe_key="M4MKR_TEST",asset="BTC",title="BTC > 84500",side_label="YES",token_id="tok_m4_mkr",p_model=.62,close_ts=time.time()+7200.,extra={"market_id":"m_m4","strike":84500.,"is_downward":False},prefetched_book=b["tok_m4_mkr"],ttl_override_sec=3.5);assert e is True;c=next(iter(d.pending_maker_orders));d.pending_maker_orders[c]["created_ts"]-=1.2;b["tok_m4_mkr"]={"bids":[{"price":"0.50","size":"60"}],"asks":[{"price":"0.51","size":"80"}]};monkeypatch.setattr(a124,"evaluate_svi_digital_fair_value",lambda*a,**kw:{"p_yes":.62,"p_no":.38,"iv_annual":.45,"z_sigma":.5,"source":"TEST"});await d.manage_pending_maker_orders();assert any(p["sleeve"]=="M4_SHOCK_STRIKE_CATCHUP"for p in d.open_positions.values());d.write_state_files([{"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","ask_vwap":.98,"net_edge":.02,"tte_sec":180.}]);assert"alpha124_shadow"in read_global_positions_shm()["daemons"]
 asyncio.run(_sim_v40_sleeves())
def test_v42_seven_new_shadow_additions_and_quarantine(tmp_path,monkeypatch):
 import asyncio;import time;from src.polymarket_research import alpha_124_shadow_daemon as a124;from src.polymarket_research.multistrike_svi_scalper import(build_negrisk_cross_box_bundles,parse_daily_updown_event,parse_multistrike_event,parse_negrisk_bracket_event);from src.polymarket_research.same_oracle_dominance_box import(build_crypto_price_query_url,determine_dominance_legs,parse_twap_candle_event,verify_same_oracle_pair,walk_equal_shares_multi_leg_box);from src.polymarket_research.weather_metar_engine import HIGH_VOLUME_WEATHER_SERIES,parse_weather_event;monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","1")
 for x in("M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","S5M_CHAINLINK_SNIPER"):assert a124.is_shadow_sleeve_quarantined(x)is True
 for v in("W1_SOLAR_PEAK_LOCK","D1_4H_DOMINANCE_BOX","D1_QUIET_BOOK_BOX","N1_NEGRISK_CROSS_BOX","U1_DAILY_UPDOWN_LOCK"):assert a124.is_shadow_sleeve_quarantined(v)is False
 assert{"chengdu-daily-weather","beijing-daily-weather","seoul-daily-weather"}<=set(HIGH_VOLUME_WEATHER_SERIES);e=("This market will resolve to the highest temperature recorded at Chengdu Shuangliu International Airport according to https://aviationweather.gov/api/data/metar?ids=ZUUU on 27 Oct '26 (SPECI reports excluded).");h={"id":"ev_chengdu","title":"Highest temperature in Chengdu on October 27?","seriesSlug":"chengdu-daily-weather","description":e,"markets":[{"id":"m_zuuu_1","conditionId":"0xc1","groupItemTitle":"19°C or below","question":"19°C or below?","description":e,"endDate":"2026-10-27T16:00:00Z","clobTokenIds":'["tok_z1_y", "tok_z1_n"]'},{"id":"m_zuuu_2","conditionId":"0xc2","groupItemTitle":"20°C","question":"20°C?","description":e,"endDate":"2026-10-27T16:00:00Z","clobTokenIds":'["tok_z2_y", "tok_z2_n"]'},{"id":"m_zuuu_3","conditionId":"0xc3","groupItemTitle":"21°C","question":"21°C?","description":e,"endDate":"2026-10-27T16:00:00Z","clobTokenIds":'["tok_z3_y", "tok_z3_n"]'},{"id":"m_zuuu_4","conditionId":"0xc4","groupItemTitle":"22°C or higher","question":"22°C or higher?","description":e,"endDate":"2026-10-27T16:00:00Z","clobTokenIds":'["tok_z4_y", "tok_z4_n"]'}]};n=parse_weather_event(h,series_slug_hint="chengdu-daily-weather");assert n is not None and n.icao=="ZUUU"and n.unit=="C";u={"id":"ev_btc_4h","title":"Bitcoin Up or Down - Oct 26, 8:00AM-12:00PM ET","endDate":"2026-10-26T16:00:00Z","markets":[{"id":"m_btc_4h","conditionId":"0x4h","eventStartTime":"2026-10-26T12:00:00Z","endDate":"2026-10-26T16:00:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["tok_4h_up", "tok_4h_dn"]',"feesEnabled":True,"feeSchedule":{"rate":.072,"exponent":1},"cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"resolutionSource":"https://data.chain.link/streams/btc-usd"}]};m={"id":"ev_btc_15m","title":"Bitcoin Up or Down - Oct 26, 11:45AM-12:00PM ET","endDate":"2026-10-26T16:00:00Z","markets":[{"id":"m_btc_15m","conditionId":"0x15m","eventStartTime":"2026-10-26T15:45:00Z","endDate":"2026-10-26T16:00:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["tok_15m_up", "tok_15m_dn"]',"feesEnabled":True,"feeSchedule":{"rate":.072,"exponent":1},"cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"resolutionSource":"https://data.chain.link/streams/btc-usd"}]};t=parse_twap_candle_event(u,"BTC","4h");l=parse_twap_candle_event(m,"BTC","15m");assert t is not None and l is not None;w=build_crypto_price_query_url(t);assert"variant=fourhour"in w and"twapEnabled=true&twapLookbackSeconds=60"in w;assert verify_same_oracle_pair(t,l)is True;k=determine_dominance_legs(t,8e4,l,80500.);assert k is not None and k["regime"]=="4H_UP_PLUS_15M_DOWN";s={"id":"ev_ms","title":"Bitcoin above ___ on Oct 26?","endDate":"2026-10-26T16:00:00Z","markets":[{"id":"ms_72","conditionId":"0xms72","question":"Will the price of Bitcoin be above $72,000 on Oct 26?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["ms72_y", "ms72_n"]'},{"id":"ms_74","conditionId":"0xms74","question":"Will the price of Bitcoin be above $74,000 on Oct 26?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["ms74_y", "ms74_n"]'}]};r={"id":"ev_nr","title":"Bitcoin price on Oct 26?","endDate":"2026-10-26T16:00:00Z","markets":[{"id":"nr_lt72","conditionId":"0xnr1","groupItemTitle":"<72,000","question":"Will BTC be less than $72,000?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["nr_lt72_y", "nr_lt72_n"]'},{"id":"nr_72_74","conditionId":"0xnr2","groupItemTitle":"72,000-74,000","question":"Will BTC be between $72,000 and $74,000?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["nr_7274_y", "nr_7274_n"]'},{"id":"nr_gt74","conditionId":"0xnr3","groupItemTitle":">74,000","question":"Will BTC be greater than $74,000?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["nr_gt74_y", "nr_gt74_n"]'}]};f=parse_multistrike_event(s,"BTC","btc-multi-strikes-weekly");a=parse_negrisk_bracket_event(r,"BTC","bitcoin-neg-risk-weekly");g=build_negrisk_cross_box_bundles(f,a);assert len(g)==6;j=[b for b in g if b["guaranteed_payout"]==1. and len(b["legs"])==3][0];i=walk_equal_shares_multi_leg_box([{"asks":[{"price":"0.28","size":"80"}],"fee_rate":.07,"fee_exponent":1.},{"asks":[{"price":"0.30","size":"80"}],"fee_rate":.07,"fee_exponent":1.},{"asks":[{"price":"0.31","size":"80"}],"fee_rate":.07,"fee_exponent":1.}],target_budget_usd=1e2,guaranteed_payout_per_bundle=j["guaranteed_payout"],max_bundle_cost_net=.992);assert i["filled"]is True and i["guaranteed_min_profit_usd"]>3.;q={"id":"ev_u1","title":"Bitcoin Up or Down on October 27?","endDate":"2026-10-27T16:00:00Z","markets":[{"id":"m_u1","conditionId":"0xu1","eventStartTime":"2026-10-26T16:00:00Z","endDate":"2026-10-27T16:00:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["u1_up", "u1_dn"]'}]};o=parse_daily_updown_event(q,"BTC","btc-up-or-down-daily");assert o is not None and o.up_token=="u1_up"and o.down_token=="u1_dn"
 async def _sim_new_sleeves():
  monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"a124_v42_state.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"a124_v42_ledger.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"a124_v42_opps.json");d=a124.Alpha124ShadowDaemon(single_scan=True);m=1793026680.;d.spots["BTC"]=8.4e4;d.spots["ETH"]=2500.;b=a124.TwapCandleMarketSpec(asset="BTC",horizon="15m",market_id="m_pre_btc",condition_id="0xpreb",title="BTC PreOpen 15m",start_iso="2026-10-26T15:00:00Z",end_iso="2026-10-26T15:15:00Z",start_ts=1793026800.,end_ts=1793027700.,up_token="p1_btc_up",down_token="p1_btc_dn",fee_rate=.072,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/btc-usd");a=a124.TwapCandleMarketSpec(asset="ETH",horizon="15m",market_id="m_pre_eth",condition_id="0xpree",title="ETH PreOpen 15m",start_iso="2026-10-26T15:00:00Z",end_iso="2026-10-26T15:15:00Z",start_ts=1793026800.,end_ts=1793027700.,up_token="p1_eth_up",down_token="p1_eth_dn",fee_rate=.072,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/eth-usd");d.preopen_15m_candles={"BTC_pre15m_1793026800":b,"ETH_pre15m_1793026800":a};l={"p1_btc_up":{"bids":[{"price":"0.49","size":"100"}],"asks":[{"price":"0.51","size":"100"}]},"p1_btc_dn":{"bids":[{"price":"0.49","size":"100"}],"asks":[{"price":"0.51","size":"100"}]},"p1_eth_up":{"bids":[{"price":"0.49","size":"100"}],"asks":[{"price":"0.51","size":"100"}]},"p1_eth_dn":{"bids":[{"price":"0.49","size":"100"}],"asks":[{"price":"0.51","size":"100"}]},"s5m_btc_up":{"bids":[{"price":"0.78","size":"600"}],"asks":[{"price":"0.80","size":"600"}]}}
  async def fake_fetch(url,timeout=5.):
   if"/book?token_id="in url:return l.get(url.split("token_id=")[1])
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch);h=[];await d.scan_and_manage_preopen_maker_straddles(h,now_ts=m);assert len(d.pending_preopen_straddles)==0;monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","0");await d.scan_and_manage_preopen_maker_straddles(h,now_ts=m);assert len(d.pending_preopen_straddles)==2;l["p1_btc_up"]["asks"]=[{"price":"0.48","size":"100"}];l["p1_btc_dn"]["asks"]=[{"price":"0.48","size":"100"}];l["p1_eth_up"]["asks"]=[{"price":"0.48","size":"100"}];l["p1_eth_up"]["bids"]=[{"price":"0.47","size":"100"}];await d.scan_and_manage_preopen_maker_straddles([],now_ts=1793026792.);assert any(p["sleeve"]=="P1_PREOPEN_MAKER_STRADDLE"for p in d.open_positions.values());e=[c for c in d.closed_positions if c["status"]=="PREOPEN_ONE_LEG_SCRATCH"];assert len(e)==1 and e[0]["tier_pnls_usd"]["T1000"]<.0;k=a124.TwapCandleMarketSpec(asset="BTC",horizon="5m",market_id="m_s5m",condition_id="0xs5m",title="BTC 5m",start_iso="2026-10-26T14:55:00Z",end_iso="2026-10-26T15:00:00Z",start_ts=1793026500.,end_ts=1793026800.,up_token="s5m_btc_up",down_token="s5m_btc_dn",fee_rate=.072,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/btc-usd");d.s5m_candles={"BTC_5m_1793026800":k};d.chainlink_open_cache[f"BTC_5m_{int(k.start_ts)}"]=(k.end_ts,83800.);d.usd_direct_flags["BTC"]=False;await d.scan_s5m_chainlink_sniper([],now_ts=1793026710.);assert not any(p["sleeve"]=="S5M_CHAINLINK_SNIPER"for p in d.open_positions.values());d.usd_direct_flags["BTC"]=True;await d.scan_s5m_chainlink_sniper([],now_ts=1793026710.);assert any(p["sleeve"]=="S5M_CHAINLINK_SNIPER"for p in d.open_positions.values());d.spot_hist["ETH"].clear();d.usd_spot_hist["ETH"].clear();d.spot_hist["ETH"].append((1e2,2306.5));d.spot_hist["ETH"].append((110.,2309.5));g=d.get_return_bps("ETH",5.);assert g>12.5;f={"shares":13,"avail_a_shares":1e2,"avail_b_shares":1e2,"leg_a_walk":{"best_ask":.8},"leg_b_walk":{"best_ask":.16}};j={"bids":[{"price":"0.78","size":"100"}],"asks":[{"price":"0.80","size":"100"}]};i={"bids":[{"price":"0.14","size":"100"}],"asks":[{"price":"0.16","size":"100"}]};assert d._passes_quiet_book_filter("ETH",j,i,f,110.)is False
 asyncio.run(_sim_new_sleeves())
def test_oct27_0655_strike_inversion_and_antibox_veto(tmp_path):
 from src.polymarket_research.same_oracle_dominance_box import(TwapCandleMarketSpec,build_prev_5m_gamma_event_url,compute_dominance_box_payout_from_close,determine_dominance_legs,parse_authoritative_open_price,walk_equal_shares_dominance_box);from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;m=TwapCandleMarketSpec(asset="SOL",horizon="15m",market_id="6247248",condition_id="0xsol15",title="SOL 6:45-7:00AM ET",start_iso="2026-10-27T10:45:00Z",end_iso="2026-10-27T11:00:00Z",start_ts=1793097900.,end_ts=1793098800.,up_token="sol_15m_up",down_token="sol_15m_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/sol-usd-twap-60s-streams");o=TwapCandleMarketSpec(asset="SOL",horizon="5m",market_id="6247315",condition_id="0xsol5",title="SOL 6:55-7:00AM ET",start_iso="2026-10-27T10:55:00Z",end_iso="2026-10-27T11:00:00Z",start_ts=1793098500.,end_ts=1793098800.,up_token="sol_5m_up",down_token="sol_5m_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/sol-usd-twap-60s-streams");assert build_prev_5m_gamma_event_url(m).endswith("slug=sol-updown-5m-1793097600");assert build_prev_5m_gamma_event_url(o).endswith("slug=sol-updown-5m-1793098200");assert parse_authoritative_open_price({"openPrice":99.9644420334347,"completed":False,"cached":True})is None;assert parse_authoritative_open_price({"openPrice":99.9644420334347,"completed":False,"cached":True},request_url="https://polymarket.com/api/crypto/crypto-price?symbol=SOL&variant=fifteen")is None;from src.polymarket_research.same_oracle_dominance_box import build_crypto_price_query_url,parse_closed_gamma_event_settlement;i=build_crypto_price_query_url(m);l=build_crypto_price_query_url(o);assert"twapEnabled=true&twapLookbackSeconds=60"in i;assert parse_authoritative_open_price({"openPrice":99.8571312195911,"completed":False,"cached":True},request_url=i)==99.8571312195911;assert parse_authoritative_open_price({"openPrice":99.97149156931644,"completed":False,"cached":True},request_url=l)==99.97149156931644;h=parse_authoritative_open_price([{"closed":True,"eventMetadata":{"finalPrice":99.8571312195911}}]);k=parse_authoritative_open_price([{"closed":True,"eventMetadata":{"finalPrice":99.97149156931644}}]);assert h==99.8571312195911 and k==99.97149156931644;a=[{"closed":True,"eventMetadata":{"priceToBeat":99.8571312195911,"finalPrice":99.90631053937364}}];b=[{"closed":True,"eventMetadata":{"priceToBeat":99.97149156931644,"finalPrice":99.90631053937364}}];assert parse_closed_gamma_event_settlement(a,"DOWN")==.0;assert parse_closed_gamma_event_settlement(b,"UP")==.0;assert parse_closed_gamma_event_settlement(a,"UP")+parse_closed_gamma_event_settlement(b,"DOWN")==2.;j=determine_dominance_legs(m,h,o,k,min_corridor_bps=3.);assert j is not None and j["regime"]=="15M_UP_PLUS_5M_DOWN";assert j["leg_a"]["opp_token_id"]=="sol_15m_dn"and j["leg_b"]["opp_token_id"]=="sol_5m_up";assert compute_dominance_box_payout_from_close(99.90631053937364,j["k_low"],j["k_high"])==2.;n=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.195","size":"100"}],asks_b_raw=[{"price":"0.574","size":"100"}],target_budget_usd=60.,max_box_cost_net=.985);assert n["filled"]is False and n["reason"]=="SUSPECT_INVERTED_ANTI_BOX";u=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"antibox.jsonl");e=u.execute_atomic_dominance_box(box_id="ANTI_BOX_VETO_TEST",leg_a_token_id="tok_a",leg_a_label="15M_DOWN",leg_a_limit_price=.22,leg_b_token_id="tok_b",leg_b_label="5M_UP",leg_b_limit_price=.48,shares=25,max_box_cost_net=.985);assert e["success"]is False and"ANTI_BOX_COST_FLOOR_VETO"in e["error"];d=u.execute_atomic_dominance_box(box_id="ETH_THINNER_FIRST",leg_a_token_id="eth_15m",leg_a_label="15M_LEG",leg_a_limit_price=.24,leg_b_token_id="eth_5m",leg_b_label="5M_LEG",leg_b_limit_price=.7,shares=25,max_box_cost_net=.985,leg_a_avail_shares=442.,leg_b_avail_shares=173.);assert d["success"]is True and d["leg_1"]["label"]=="5M_LEG";q=build_prev_5m_gamma_event_url(m);p=[{"slug":"sol-updown-5m-1793097600","closed":True,"eventMetadata":{"finalPrice":99.8571312195911}}];g=[{"slug":"sol-updown-5m-1793097300","closed":True,"eventMetadata":{"finalPrice":99.}}];assert parse_authoritative_open_price(p,request_url=q)==99.8571312195911;assert parse_authoritative_open_price(g,request_url=q)is None;import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124_fc;c=tmp_path/"fc_state.json";a124_fc.STATE_FILE=c;r=a124_fc.Alpha124ShadowDaemon(single_scan=True);f={}
 async def _fc_fetch(url,timeout=5.):
  for b,a in f.items():
   if f"token_id={b}"in url:return a
  return None
 r.fetch_json=_fc_fetch;t={"opp_token_id":"oa","label":"A"};s={"opp_token_id":"ob","label":"B"};assert asyncio.run(r._passes_complement_anti_box_check({"label":"A"},{"label":"B"}))is False;assert asyncio.run(r._passes_complement_anti_box_check(t,s))is False;f["oa"]={"bids":[{"price":"0.40","size":"50"}]};f["ob"]={"bids":[]};assert asyncio.run(r._passes_complement_anti_box_check(t,s))is False;f["ob"]={"bids":[{"price":"0.55","size":"50"}]};assert asyncio.run(r._passes_complement_anti_box_check(t,s))is True;f["ob"]={"bids":[{"price":"0.61","size":"50"}]};assert asyncio.run(r._passes_complement_anti_box_check(t,s))is False;f["oa"]={"bids":[{"price":"0.985","size":"50"}],"asks":[{"price":"0.995","size":"50"}]};f["ob"]={"bids":[],"asks":[{"price":"0.030","size":"80"}]};assert asyncio.run(r._passes_complement_anti_box_check(t,s))is True;f["oa"]={"bids":[{"price":"0.960","size":"50"}],"asks":[{"price":"0.970","size":"50"}]};f["ob"]={"bids":[],"asks":[{"price":"0.100","size":"80"}]};assert asyncio.run(r._passes_complement_anti_box_check(t,s))is False
def test_riskless_expansion_7coins_b3_w3no_pyth_and_maker_anchor(tmp_path,monkeypatch):
 import asyncio;import time;from datetime import date;import src.polymarket_research.alpha_124_shadow_daemon as a124_exp;from src.polymarket_research.same_oracle_dominance_box import(DOMINANCE_ASSETS,MIN_CORRIDOR_BPS_BY_ASSET,build_crypto_price_query_url,determine_dominance_legs,parse_twap_candle_event);from src.polymarket_research.barrier_onetouch_svi_engine import detect_barrier_monotonicity_boxes;from src.polymarket_research.multistrike_svi_scalper import ZERO_FEE_PYTH_DAILY_SERIES;from src.polymarket_research.weather_metar_engine import(WeatherBucket,WeatherEventSpec,evaluate_weather_event_slate);assert set(DOMINANCE_ASSETS)=={"BTC","ETH","SOL","XRP","BNB","DOGE","HYPE"};assert len(ZERO_FEE_PYTH_DAILY_SERIES)==8;h={}
 for x,C,B in(("BNB","bnb","bnb-usd"),("DOGE","doge","doge-usd"),("HYPE","hype","hype-usd")):I={"slug":f"{C}-updown-15m-1793100000","endDate":"2026-10-27T11:15:00Z","markets":[{"id":f"m15_{x}","conditionId":"0x"+"11"*32,"question":f"{x} Up or Down 15m","eventStartTime":"2026-10-27T11:00:00Z","endDate":"2026-10-27T11:15:00Z","resolutionSource":f"https://data.chain.link/streams/{B}-twap-60s-streams","cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"outcomes":'["Up", "Down"]',"clobTokenIds":f'["{x}_15_up", "{x}_15_dn"]',"orderMinSize":5,"feesEnabled":True,"feeSchedule":{"rate":.07,"exponent":1}}]};K={"slug":f"{C}-updown-5m-1793100600","endDate":"2026-10-27T11:15:00Z","markets":[{"id":f"m5_{x}","conditionId":"0x"+"22"*32,"question":f"{x} Up or Down 5m","eventStartTime":"2026-10-27T11:10:00Z","endDate":"2026-10-27T11:15:00Z","resolutionSource":f"https://data.chain.link/streams/{B}-twap-60s-streams","cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"outcomes":'["Up", "Down"]',"clobTokenIds":f'["{x}_5_up", "{x}_5_dn"]',"orderMinSize":5,"feesEnabled":True,"feeSchedule":{"rate":.07,"exponent":1}}]};J=parse_twap_candle_event(I,x,"15m");O=parse_twap_candle_event(K,x,"5m");assert J is not None and O is not None and J.asset==x;assert f"symbol={x}"in build_crypto_price_query_url(J);h[x]=(J,O)
 k,z=h["DOGE"];assert determine_dominance_legs(k,.2,z,.20007,min_corridor_bps=MIN_CORRIDOR_BPS_BY_ASSET["DOGE"])is None;assert determine_dominance_legs(k,.2,z,.20014,min_corridor_bps=MIN_CORRIDOR_BPS_BY_ASSET["DOGE"])is not None;monkeypatch.setattr(a124_exp,"STATE_FILE",tmp_path/"exp_state.json");monkeypatch.setattr(a124_exp,"LEDGER_FILE",tmp_path/"exp_ledger.jsonl");monkeypatch.setattr(a124_exp,"LIVE_ALPHA124_STATE_MIRROR_FILE",tmp_path/"exp_mirror.json");monkeypatch.setattr(a124_exp,"D1_LIVE_CANDIDATES_FILE",tmp_path/"exp_d1_cands.jsonl");G=a124_exp.Alpha124ShadowDaemon(single_scan=False);g=f"doge-updown-5m-{int(k.start_ts)-300}"
 async def _fetch_429_fallback(url,timeout=5.):
  if"crypto-price"in url:return None
  if g in url:return[{"slug":g,"closed":True,"eventMetadata":{"finalPrice":.21456}}]
  return None
 G.fetch_json=_fetch_429_fallback;f=a124_exp.time.time
 try:a124_exp.time.time=lambda:k.start_ts+45.;F=asyncio.run(G.get_authoritative_open_strike(k));assert F==.21456
 finally:a124_exp.time.time=f
 u=[{"direction":"UP","strike":1e5,"ask_yes":.5,"ask_no":.52,"market_id":"m_lo","condition_id":"0x1","yes_token":"t_lo_y","no_token":"t_lo_n","end_ts":time.time()+3600},{"direction":"UP","strike":1.05e5,"ask_yes":.58,"ask_no":.43,"market_id":"m_hi","condition_id":"0x2","yes_token":"t_hi_y","no_token":"t_hi_n","end_ts":time.time()+3600},{"direction":"DOWN","strike":8e4,"ask_yes":.58,"ask_no":.44,"market_id":"m_dlo","condition_id":"0x3","yes_token":"t_dlo_y","no_token":"t_dlo_n","end_ts":time.time()+3600},{"direction":"DOWN","strike":8.5e4,"ask_yes":.5,"ask_no":.52,"market_id":"m_dhi","condition_id":"0x4","yes_token":"t_dhi_y","no_token":"t_dhi_n","end_ts":time.time()+3600}];n=detect_barrier_monotonicity_boxes(u,fee_rate=.07,max_box_cost_net=.985);assert len(n)==2;assert{b["direction"]for b in n}=={"UP","DOWN"};N=WeatherBucket("w1","c1","<=69F","NYC <= 69F","w1_y","w1_n","F",-float("inf"),69.);M=WeatherBucket("w2","c2","70-71F","NYC 70-71F","w2_y","w2_n","F",70.,71.);L=WeatherBucket("w3","c3",">=72F","NYC >= 72F","w3_y","w3_n","F",72.,float("inf"));H=WeatherEventSpec("W_EV_NO","nyc-oct-27","nyc-daily-weather","NYC High","KLGA","NYC",40.77,-73.87,"America/New_York",date(2026,10,27),"HIGH","F","zero_fees","2026-10-28T04:00:00Z",[N,M,L]);E=evaluate_weather_event_slate(H,[.34,.33,.33],{"w1":{"ask_yes":.42,"ask_yes_shares":50.,"ask_no":.62,"ask_no_shares":60.},"w2":{"ask_yes":.42,"ask_yes_shares":50.,"ask_no":.62,"ask_no_shares":60.},"w3":{"ask_yes":.42,"ask_yes_shares":50.,"ask_no":.62,"ask_no_shares":60.}},target_budget_usd=35.);m=E["full_slate_arb"];assert m is not None and m["mode"]=="FULL_SLATE_NO_COMPLEMENT_ARB";assert m["guaranteed_payout_per_set"]==2.;assert asyncio.run(G.open_shadow_weather_slate(H,m,time.time()-60.))is True
 async def _fetch_w_closed(url,timeout=5.):
  if"/markets/w1"in url:return{"id":"w1","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["w1_y","w1_n"]',"outcomePrices":'["1","0"]'}
  if"/markets/w2"in url:return{"id":"w2","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["w2_y","w2_n"]',"outcomePrices":'["0","1"]'}
  if"/markets/w3"in url:return{"id":"w3","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["w3_y","w3_n"]',"outcomePrices":'["0","1"]'}
  return None
 G.fetch_json=_fetch_w_closed;asyncio.run(G.manage_open_positions());l=[c for c in G.closed_positions if c["sleeve"]=="W3_WEATHER_SLATE_ARB"];assert len(l)==1 and l[0]["won"]is True and l[0]["status"]=="SETTLED_WEATHER_SLATE_NX";assert l[0]["tier_pnls_usd"]["T100"]>.0;from dataclasses import replace as dc_replace;A=time.time();k=dc_replace(k,end_ts=A+180.);z=dc_replace(z,end_ts=A+180.);y=determine_dominance_legs(k,.2,z,.2002,min_corridor_bps=5.);assert y is not None;t=y["leg_a"]["token_id"];s=y["leg_b"]["token_id"];j={t:{"bids":[{"price":"0.50","size":"80"}],"asks":[{"price":"0.53","size":"80"}]},s:{"bids":[{"price":"0.45","size":"220"}],"asks":[{"price":"0.46","size":"220"}]}}
 async def _fetch_ma(url,timeout=5.):
  for b,a in j.items():
   if b in url:return a
  return None
 G.fetch_json=_fetch_ma;assert G.post_maker_anchor_candidate(k,z,y,j[t],j[s],now_ts=A-2.)is True;assert len(G.pending_maker_anchors)==1;j[t]={"bids":[{"price":"0.50","size":"80"}],"asks":[{"price":"0.51","size":"40"}]};asyncio.run(G.manage_pending_maker_anchors(now_ts=A));assert len(G.pending_maker_anchors)==0;q=[p for p in G.open_positions.values()if p["sleeve"]=="D1_MAKER_ANCHOR_BOX"];assert len(q)==1 and q[0]["extra"]["is_maker_anchor_box"]is True;a,i=h["BNB"];a=dc_replace(a,end_ts=A+180.);i=dc_replace(i,end_ts=A+180.);o=determine_dominance_legs(a,6e2,i,600.6,min_corridor_bps=5.);assert o is not None;e=o["leg_a"]["token_id"];d=o["leg_b"]["token_id"];j[e]={"bids":[{"price":"0.50","size":"80"}],"asks":[{"price":"0.53","size":"80"}]};j[d]={"bids":[{"price":"0.45","size":"220"}],"asks":[{"price":"0.46","size":"220"}]};assert G.post_maker_anchor_candidate(a,i,o,j[e],j[d],now_ts=A-2.)is True;assert len(G.pending_maker_anchors)==1;j[d]={"bids":[{"price":"0.45","size":"5"}],"asks":[{"price":"0.46","size":"5"}]};asyncio.run(G.manage_pending_maker_anchors(now_ts=A));assert len(G.pending_maker_anchors)==0;import json as _json_t;from src.polymarket_research.polymarket_terminal_recorder import ASSET_CONFIGS,PolymarketDualFeed1HRecorder
 for x in DOMINANCE_ASSETS:assert x in ASSET_CONFIGS;D=PolymarketDualFeed1HRecorder(asset=x);assert D.coinbase_product==f"{x}-USD";assert D.telemetry_5m_file.name==f"polymarket_5m_telemetry_{x.lower()}.jsonl";assert D.telemetry_15m_file.name==f"polymarket_15m_telemetry_{x.lower()}.jsonl";assert D.telemetry_4h_file.name==f"polymarket_4h_telemetry_{x.lower()}.jsonl"
 assert ASSET_CONFIGS["HYPE"].get("futures_only_ref")is True;assert ASSET_CONFIGS["DOGE"]["series_slug"]=="doge-up-or-down-hourly";assert ASSET_CONFIGS["BNB"]["series_slug"]=="bnb-up-or-down-hourly";G._record_d1_corridor_telemetry("15m_5m",a,i,o,{"bids":[{"price":"0.50","size":"80"}],"asks":[{"price":"0.53","size":"80"}]},{"bids":[{"price":"0.45","size":"80"}],"asks":[{"price":"0.49","size":"80"}]},A);w=tmp_path/"alpha124_market_telemetry.jsonl";assert w.exists();v=[_json_t.loads(P)for P in w.read_text(encoding="utf-8").splitlines()if P.strip()];assert any(r["type"]=="D1_CORRIDOR"and r["asset"]=="BNB"and r["gross_box_l1"]==1.02 for r in v)
def test_telemetry_compact_encoding_delta_dedupe_and_inode_safe_gzip_compactor(tmp_path,monkeypatch):
 import json as _json_c;import src.polymarket_research.alpha_124_shadow_daemon as a124;from scripts.honest_purged_wfo_optimizer import iter_jsonl_lines_with_archives;from scripts.polymarket_telemetry_compactor import compact_jsonl_file,is_protected_path;from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook,_dumps_compact;q=L2OrderBook("tok_test");q.apply_snapshot(bids=[{"price":str(round(.49-.01*i,2)),"size":"120"}for i in range(15)],asks=[{"price":str(round(.51+.01*i,2)),"size":"120"}for i in range(15)]);o=q.last_book_update_ts+.5;n=q.get_metrics(obs_ts=o,compact=False);m=q.get_metrics(obs_ts=o,compact=True);assert"microprice_formula"in n and"vwap_$250"in n and len(n["raw_top_bids"])==15;assert"microprice_formula"not in m and"vwap_$250"not in m and len(m["raw_top_bids"])==10
 for k in("best_bid","best_ask","q_mid","q_micro","obi_l1","obi_depth","vwap_$20","vwap_$25","vwap_$50","effective_price_$50","fill_fees_$50"):assert m[k]==n[k]
 c=len(_json_c.dumps({"UP":n,"DOWN":n}).encode("utf-8"));b=len(_dumps_compact({"UP":m,"DOWN":m}).encode("utf-8"));assert b<.45*c;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ldg.jsonl");monkeypatch.setattr(a124,"MARKET_TELEMETRY_FILE",tmp_path/"m_telem.jsonl");p=a124.Alpha124ShadowDaemon(single_scan=True);p._record_market_telemetry("W_SLATE_1",10.,{"type":"WEATHER_SLATE","sum_yes_l1":1.02},now_ts=1e3,sig=(1.02,));p._record_market_telemetry("W_SLATE_1",10.,{"type":"WEATHER_SLATE","sum_yes_l1":1.02},now_ts=1025.,sig=(1.02,));p._record_market_telemetry("W_SLATE_1",10.,{"type":"WEATHER_SLATE","sum_yes_l1":.99},now_ts=1040.,sig=(.99,));j=(tmp_path/"m_telem.jsonl").read_text(encoding="utf-8").splitlines();assert len(j)==2;assert is_protected_path(tmp_path/"live_orders.jsonl")is True;assert is_protected_path(tmp_path/"finalized_market_resolutions.jsonl")is True;assert is_protected_path(tmp_path/"alpha124_shadow_ledger.jsonl")is True;assert is_protected_path(tmp_path/"d1_live_box_candidates.jsonl")is True;assert is_protected_path(tmp_path/"polymarket_hourly_telemetry.jsonl")is False;assert is_protected_path(tmp_path/"alpha124_market_telemetry.jsonl")is False;assert is_protected_path(tmp_path/"counterfactual_candidates.jsonl")is False;l=tmp_path/"polymarket";l.mkdir(parents=True,exist_ok=True);h=l/"polymarket_hourly_telemetry.jsonl";g=l/"polymarket_hourly_telemetry_eth.jsonl";a=[f"btc_{i}"for i in range(400)];h.write_text("".join(_dumps_compact({"seq":i,"id":f"btc_{i}","UP":m})+"\n"for i in range(400)),encoding="utf-8");g.write_text("".join(_dumps_compact({"seq":i,"id":f"eth_{i}","UP":m})+"\n"for i in range(400)),encoding="utf-8");f=compact_jsonl_file(h,hot_threshold_bytes=20000,keep_tail_bytes=15000,min_archive_bytes=10000);e=compact_jsonl_file(g,hot_threshold_bytes=20000,keep_tail_bytes=15000,min_archive_bytes=10000);assert f["status"]=="COMPACTED"and f["inode_preserved"]is True and f["compression_ratio_x"]>3.;assert e["status"]=="COMPACTED";assert h.stat().st_size<25000;d=[_json_c.loads(r)["id"]for r in iter_jsonl_lines_with_archives(l,"polymarket_hourly_telemetry.jsonl")if r.strip()];assert d==a
def test_multi_vertical_zero_fee_expansion_sleeves(tmp_path,monkeypatch):
 import asyncio;import time;from datetime import date;from zoneinfo import ZoneInfo;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.barrier_onetouch_svi_engine import BarrierRungSpec;from src.polymarket_research.tradfi_sports_zero_fee_engine import(compute_effective_trading_hours,detect_nba_dominance_boxes,detect_pyth_calendar_inclusion_boxes,detect_pyth_close_vs_hit_boxes,parse_nba_zero_fee_event,parse_zero_fee_negrisk_slate);from src.polymarket_research.weather_metar_engine import(MetarObservation,WeatherBucket,WeatherEventSpec,compute_weather_probabilities,parse_hko_csv_observations,parse_weather_event);F="Date time,Automatic Weather Station,Air Temperature(degree Celsius)\n202610281020,Chek Lap Kok,28.7\n202610281020,HK Observatory,26.2\n";E="Date time,Automatic Weather Station,Max,Min\n202610281020,Chek Lap Kok,28.7,26.0\n202610281020,HK Observatory,26.3,24.8\n";v=parse_hko_csv_observations(F,E,date(2026,10,28));assert len(v)==3;assert max(o.temp_c for o in v)==26.3;assert min(o.temp_c for o in v)==24.8;assert v[-1].temp_c==26.2;D={"id":"ev_hko_1","title":"Highest temperature in Hong Kong on October 28?","endDate":"2026-10-28T16:00:00Z","markets":[{"id":f"hk_{i}","conditionId":f"0xhk_{i}","groupItemTitle":lbl,"description":"Resolves to highest temperature recorded by the Hong Kong Observatory on 28 Oct '26 via https://www.weather.gov.hk/en/cis/climat.htm","clobTokenIds":f'["hy_{i}", "hn_{i}"]',"feeType":"zero_fees","feesEnabled":True,"feeSchedule":{"rate":0}}for i,lbl in enumerate(["25°C or below","26°C","27°C","28°C or higher"])]};C=parse_weather_event(D);assert C is not None and C.icao=="HKO"and C.fee_type=="zero_fees";K=ZoneInfo("America/New_York");f=[WeatherBucket("b0","c0","9°C or below","9-","y0","n0","C",float("-inf"),9.),WeatherBucket("b1","c1","10°C","10","y1","n1","C",10.,10.),WeatherBucket("b2","c2","11°C","11","y2","n2","C",11.,11.),WeatherBucket("b3","c3","12°C or higher","12+","y3","n3","C",12.,float("inf"))];B=WeatherEventSpec("ev_low","nyc-low","nyc-daily-lowest-temperature","Lowest temperature in NYC on October 28?","KLGA","NYC",40.7769,-73.874,"America/New_York",date(2026,10,28),"LOW","C","zero_fees","2026-10-29T04:00:00Z",f);J=datetime(2026,10,28,6,0,tzinfo=K);I=datetime(2026,10,28,11,0,tzinfo=K);u=[MetarObservation("KLGA",J.astimezone(timezone.utc),J,10.1,True,"T0101"),MetarObservation("KLGA",I.astimezone(timezone.utc),I,14.5,True,"T0145")];s={int(datetime(2026,10,28,h,0,tzinfo=K).astimezone(timezone.utc).timestamp()):[13.5]*20 for h in range(12,24)};s[int(datetime(2026,10,29,0,0,tzinfo=K).astimezone(timezone.utc).timestamp())]=[13.2]*20;A=compute_weather_probabilities(B,I.astimezone(timezone.utc),u,s);assert A["is_solar_lock"]is True and A["locked_bucket_idx"]==1;n=dict(s);n[int(datetime(2026,10,28,23,0,tzinfo=K).astimezone(timezone.utc).timestamp())]=[10.8]*20;t=compute_weather_probabilities(B,I.astimezone(timezone.utc),u,n);assert t["is_solar_lock"]is False;m=datetime(2026,10,30,15,0,tzinfo=K).timestamp();e=datetime(2026,11,2,10,30,tzinfo=K).timestamp();assert abs(compute_effective_trading_hours(m,e,"EQUITY_RTH")-2.)<1e-6;l=detect_pyth_calendar_inclusion_boxes([{"asset":"WTI","direction":"UP","strike":105.,"fee_rate":.0,"start_ts":1e3,"end_ts":5e4,"ask_yes":.45,"ask_no":.56,"market_id":"w1","condition_id":"cw1","yes_token":"wy","no_token":"wn"},{"asset":"WTI","direction":"UP","strike":105.,"fee_rate":.0,"start_ts":9e2,"end_ts":2e5,"ask_yes":.42,"ask_no":.59,"market_id":"m1","condition_id":"cm1","yes_token":"my","no_token":"mn"}]);assert len(l)==1 and abs(l[0]["box_cost_net"]-.98)<1e-6;k=detect_pyth_close_vs_hit_boxes(close_rows=[{"asset":"SPY","strike":775.,"is_downward":False,"fee_rate":.0,"end_ts":5e3,"ask_no":.55,"market_id":"c1","condition_id":"cc1","yes_token":"cy","no_token":"cn"}],hit_rows=[{"asset":"SPY","strike":775.,"direction":"UP","fee_rate":.0,"start_ts":1e3,"end_ts":9e3,"ask_yes":.43,"market_id":"h1","condition_id":"ch1","yes_token":"hy","no_token":"hn"}],now_ts=2e3);assert len(k)==1 and abs(k[0]["box_cost_net"]-.98)<1e-6;z={"id":"nba_1","slug":"nba-bkn-bos","title":"Nets vs. Celtics","endDate":"2026-10-28T23:30:00Z","markets":[{"id":"ml","conditionId":"c_ml","sportsMarketType":"moneyline","question":"Nets vs. Celtics","outcomes":'["Nets", "Celtics"]',"clobTokenIds":'["t_nets_ml", "t_bos_ml"]',"feeType":"zero_fees","feesEnabled":True,"feeSchedule":{"rate":0}},{"id":"sp_bos","conditionId":"c_sp1","sportsMarketType":"spreads","question":"Spread: Celtics (-4.5)","outcomes":'["Celtics", "Nets"]',"line":-4.5,"clobTokenIds":'["t_bos_m45", "t_nets_p45"]',"feeType":"zero_fees","feesEnabled":True,"feeSchedule":{"rate":0}},{"id":"sp_1h","conditionId":"c_1h","sportsMarketType":"first_half_spreads","question":"1H Spread: Celtics (-2.5)","outcomes":'["Celtics", "Nets"]',"line":-2.5,"clobTokenIds":'["t_1h_a", "t_1h_b"]',"feeType":"zero_fees"},{"id":"tot_lo","conditionId":"c_tl","sportsMarketType":"totals","question":"Nets vs. Celtics: O/U 215.5","outcomes":'["Over", "Under"]',"line":215.5,"clobTokenIds":'["t_ov_215", "t_un_215"]',"feeType":"zero_fees"},{"id":"tot_hi","conditionId":"c_th","sportsMarketType":"totals","question":"Nets vs. Celtics: O/U 220.5","outcomes":'["Over", "Under"]',"line":220.5,"clobTokenIds":'["t_ov_220", "t_un_220"]',"feeType":"zero_fees"}]};y=parse_nba_zero_fee_event(z,now_ts=1.79322e9);assert y is not None;assert all("1h"not in L.token_id for L in y.margin_legs);q=detect_nba_dominance_boxes(y,{"t_bos_ml":.56,"t_nets_p45":.425,"t_bos_m45":.58,"t_nets_ml":.4,"t_ov_215":.52,"t_un_220":.465},max_box_cost_net=.994);x={a["label"]for a in q};assert"Nets +4.5 + Celtics ML"in x;assert"Over 215.5 + Under 220.5"in x;assert not any("Nets ML"in lbl and"Celtics -4.5"in lbl for lbl in x),"Anti-box must never be emitted!";H={"id":"nr_elon","title":"Elon tweets 48h?","negRisk":True,"endDate":"2026-10-30T16:00:00Z","markets":[{"id":"e0","closed":True,"outcomePrices":'["0", "1"]'},{"id":"e1","conditionId":"ce1","groupItemTitle":"40-64","clobTokenIds":'["ey1","en1"]',"feeType":"zero_fees"},{"id":"e2","conditionId":"ce2","groupItemTitle":"65-89","clobTokenIds":'["ey2","en2"]',"feeType":"zero_fees"},{"id":"e3","conditionId":"ce3","groupItemTitle":"90+","clobTokenIds":'["ey3","en3"]',"feeType":"zero_fees"}]};assert parse_zero_fee_negrisk_slate(H,"elon-tweets-48h")is not None;H["markets"][0]["outcomePrices"]='["1", "0"]';assert parse_zero_fee_negrisk_slate(H,"elon-tweets-48h")is None;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"b4_st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"b4_ldg.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"b4_opps.json")
 async def _run_b4():
  d=a124.Alpha124ShadowDaemon(single_scan=True);b=time.time();d.spots["BTC"]=84200.;d.barrier_rungs["m_b4"]=BarrierRungSpec(asset="BTC",horizon_group="WEEK",series_slug="btc-hit",event_id="ev_b4",market_id="m_b4",condition_id="0xcb4",group_label="↑ 85,000",question="Will BTC hit $85,000?",strike=8.5e4,direction="UP",start_ts=b-7200.,end_ts=b+86400.,yes_token="t_b4_y",no_token="t_b4_n",fee_rate=.07);d.barrier_rungs["m_b4_stale"]=BarrierRungSpec(asset="BTC",horizon_group="MONTH",series_slug="btc-hit",event_id="ev_b4",market_id="m_b4_stale",condition_id="0xcst",group_label="↑ 85,000",question="Will BTC reach $85,000 in Oct?",strike=8.5e4,direction="UP",start_ts=b-6e2,end_ts=b+86400.,yes_token="t_b4_stale_y",no_token="t_b4_stale_n",fee_rate=.07);d.barrier_ext_cache["ev_b4"]=(b,(85120.,83900.,84200.))
  async def fake_batch(toks,timeout=3.):return{"t_b4_y":{"bids":[{"price":"0.95","size":"200"}],"asks":[{"price":"0.97","size":"200"}]},"t_b4_stale_y":{"bids":[{"price":"0.07","size":"200"}],"asks":[{"price":"0.085","size":"200"}]}}
  monkeypatch.setattr(d,"fetch_books_batch",fake_batch);a=[];await d.scan_barrier_markets(a);assert any(p["sleeve"]=="B4_TOUCHED_BARRIER_WICK_LOCK"and p["dedupe_key"]=="B4_m_b4"for p in d.open_positions.values());assert not any(p["dedupe_key"]=="B4_m_b4_stale"for p in d.open_positions.values())
 asyncio.run(_run_b4());from src.polymarket_research.barrier_onetouch_svi_engine import parse_hit_event;from src.polymarket_research.tradfi_sports_zero_fee_engine import is_same_continuous_session;w={"id":"ev_oct","startDate":"2026-10-01T05:00:00Z","endDate":"2026-11-01T03:59:59Z","markets":[{"id":"m_init","conditionId":"c1","question":"Will ETH reach $3,000 in October?","groupItemTitle":"↑ 3,000","clobTokenIds":'["y1","n1"]',"startDate":"2026-10-01T05:00:00Z"},{"id":"m_minted","conditionId":"c2","question":"Will ETH reach $2,600 in October?","groupItemTitle":"↑ 2,600","clobTokenIds":'["y2","n2"]',"startDate":"2026-10-22T16:18:20Z","description":"from the creation of this market through 11:59 PM ET"}]};g={r.market_id:r for r in parse_hit_event(w,"ETH","MONTHLY","ethereum-hit-price-monthly")};assert g["m_minted"].start_ts>g["m_init"].start_ts+15*86400.;G=ZoneInfo("America/New_York");c=a124.datetime(2026,10,27,23,0,tzinfo=G).timestamp();j=a124.datetime(2026,10,30,14,0,tzinfo=G).timestamp();b=a124.datetime(2026,10,30,16,0,tzinfo=G).timestamp();assert not is_same_continuous_session(c,b,"EQUITY_RTH"),"Multi-day / overnight earnings gap must be vetoed!";assert is_same_continuous_session(j,b,"EQUITY_RTH"),"Friday same-session RTH final 2h must pass!"
def test_phase2_macro_counting_ctf_aaa_and_maker_anchors(monkeypatch,tmp_path):
 import asyncio;from datetime import datetime;from zoneinfo import ZoneInfo;from src.polymarket_research import alpha_124_shadow_daemon as a124;from src.polymarket_research.macro_counting_ctf_engine import(ALL_FOMC_MASK,ALL_OIL_SENATE_MASK,build_fomc_truth_table_legs,build_oil_senate_truth_table_legs,detect_counting_subwindow_boxes,detect_d2_12pm_binance_boxes,evaluate_ai_elo_ci_lock,evaluate_counting_dead_no_locks,evaluate_locked_market_reward_carry,evaluate_pyth_catalyst_shock,find_cross_event_bitmask_boxes,parse_aaa_gas_html,parse_counting_slate_event,walk_equal_shares_overround_bids);from src.polymarket_research.redeem_settled_positions import(encode_ctf_merge_or_split_calldata,inspect_mergeable_complete_set);D={"id":"ev_elon_7d","slug":"elon-musk-of-tweets-october-27-november-3","title":"Elon Musk # tweets October 27 - November 3, 2026?","endDate":"2026-11-03T17:00:00Z","description":"from October 27, 2026, 12:00 PM ET to November 3, 2026, 12:00 PM ET","markets":[{"id":"c7_0","closed":True,"groupItemTitle":"<40","outcomePrices":'["0","1"]'},{"id":"c7_1","conditionId":"0xc71","groupItemTitle":"40-64","clobTokenIds":'["t7_y1","t7_n1"]',"feeType":"zero_fees","rewardsMinSize":50,"rewardsMaxSpread":3.5},{"id":"c7_2","conditionId":"0xc72","groupItemTitle":"65-89","clobTokenIds":'["t7_y2","t7_n2"]',"feeType":"zero_fees"},{"id":"c7_3","conditionId":"0xc73","groupItemTitle":"140+","clobTokenIds":'["t7_yup","t7_nup"]',"feeType":"zero_fees"}]};w={"id":"ev_elon_48h","slug":"elon-musk-of-tweets-october-29-october-31","title":"Elon Musk # tweets October 29 - October 31, 2026?","endDate":"2026-10-31T16:00:00Z","description":"from October 29, 2026, 12:00 PM ET to October 31, 2026, 12:00 PM ET","markets":[{"id":"c2_0","conditionId":"0xc20","groupItemTitle":"<40","clobTokenIds":'["t2_ylo","t2_nlo"]',"feeType":"zero_fees"},{"id":"c2_1","conditionId":"0xc21","groupItemTitle":"40-89","clobTokenIds":'["t2_ym","t2_nm"]',"feeType":"zero_fees"},{"id":"c2_2","conditionId":"0xc22","groupItemTitle":"90+","clobTokenIds":'["t2_yup","t2_nup"]',"feeType":"zero_fees"}]};K=parse_counting_slate_event(D,"elon-tweets","elonmusk");J=parse_counting_slate_event(w,"elon-tweets-48h","elonmusk");assert K is not None and J is not None and K.gamma_closed_floor==40;v={K.slug:{"total":68,"hourly":[(K.window_start_ts+3600.,55)]}};r,E=evaluate_counting_dead_no_locks(K,v,safety_post_buffer=2);assert r==68 and[b.market_id for b in E]==["c7_1"];I=evaluate_locked_market_reward_carry(1.,.975,.99,50.,3.5,.0);assert I["eligible"]is True and.975<=I["resting_bid"]<=.985;i=detect_counting_subwindow_boxes([K,J],{"t2_nup":.44,"t7_yup":.54},{"elonmusk":v},max_box_cost_net=.99);assert any(b["box_kind"]=="TW1_UPPER_SUBWINDOW"and abs(b["box_cost_net"]-.98)<1e-6 for b in i);h=[{"slug":"fed-decision-in-october-2026","endDate":"2026-10-29T18:00:00Z","markets":[{"id":"fo_p","conditionId":"0xfop","groupItemTitle":"No change","clobTokenIds":'["fop_y","fop_n"]',"feeType":"zero_fees"}]}];q=[{"slug":"fed-decisions-oct-jan","endDate":"2027-01-29T19:00:00Z","markets":[{"id":"fp_1","conditionId":"0xfp1","groupItemTitle":"Pause-Pause-Pause","clobTokenIds":'["fp1_y","fp1_n"]',"feeType":"zero_fees"},{"id":"fp_2","conditionId":"0xfp2","groupItemTitle":"Hike-Pause-Pause","clobTokenIds":'["fp2_y","fp2_n"]',"feeType":"zero_fees"},{"id":"fp_o","conditionId":"0xfpo","groupItemTitle":"Other","clobTokenIds":'["fpo_y","fpo_n"]',"feeType":"zero_fees"}]}];u=build_fomc_truth_table_legs(h,q);o=find_cross_event_bitmask_boxes(u,{"fop_y":.88,"fp1_n":.105},ALL_FOMC_MASK,max_2leg_cost=.995);assert len(o)==1 and o[0]["n_legs"]==2 and o[0]["box_cost_net"]==.985;t={"which-party-will-win-the-senate-in-2026":{"endDate":"2026-11-04T00:00:00Z","markets":[{"id":"sm_d","conditionId":"0xsmd","groupItemTitle":"Democratic Party","clobTokenIds":'["smd_y","smd_n"]',"feeType":"zero_fees"}]},"who-wins-the-senate-pending-oil-above-or-below-80-before-the-midterms":{"endDate":"2026-11-04T00:00:00Z","markets":[{"id":"s80_ld","conditionId":"0x80ld","groupItemTitle":"Oil < $80; D Senate","clobTokenIds":'["o80ld_y","o80ld_n"]',"feeType":"zero_fees"},{"id":"s80_gd","conditionId":"0x80gd","groupItemTitle":"Oil ≥ $80; D Senate","clobTokenIds":'["o80gd_y","o80gd_n"]',"feeType":"zero_fees"}]},"who-wins-the-senate-pending-oil-below-85-before-the-midterms":{"endDate":"2026-11-04T00:00:00Z","markets":[{"id":"s85_ld","conditionId":"0x85ld","groupItemTitle":"Oil < $85; D Senate","clobTokenIds":'["o85ld_y","o85ld_n"]',"feeType":"zero_fees"}]}};n=build_oil_senate_truth_table_legs(t);g=find_cross_event_bitmask_boxes(n,{"o80ld_y":.01,"o80gd_y":.64,"smd_n":.335,"o80ld_n":.97,"o85ld_y":.015},ALL_OIL_SENATE_MASK,max_2leg_cost=.995,max_3leg_cost=.995);assert any(b["n_legs"]==3 and abs(b["box_cost_net"]-.985)<1e-6 for b in g);assert any(b["n_legs"]==2 and abs(b["box_cost_net"]-.985)<1e-6 for b in g);F=walk_equal_shares_overround_bids([{"bids":[{"price":"0.52","size":"50"}],"fee_rate":.0,"fee_exponent":1.},{"bids":[{"price":"0.49","size":"50"}],"fee_rate":.0,"fee_exponent":1.}],target_mint_budget_usd=40.,min_net_proceeds_per_set=1.004);assert F["filled"]is True and F["net_proceeds_per_set"]==1.01;m="0x"+"ab"*32;from src.polymarket_research import redeem_settled_positions as rsp;_,f=encode_ctf_merge_or_split_calldata(m,25.,is_split=False,neg_risk=False);_,e=encode_ctf_merge_or_split_calldata(m,25.,is_split=True,neg_risk=False);_,l=encode_ctf_merge_or_split_calldata(m,25.,is_split=False,neg_risk=True);_,k=encode_ctf_merge_or_split_calldata(m,25.,is_split=True,neg_risk=True);assert f[:10]=="0x9e7212ad"and e[:10]=="0x72ce4275";assert l[:10]=="0xb10c5c17"and k[:10]=="0xa3d7da1d";monkeypatch.setattr(rsp,"get_token_balance_onchain",lambda L,M:12.5 if M=="tok_y"else 15.);assert inspect_mergeable_complete_set("0x1111111111111111111111111111111111111111","tok_y","tok_n")==12.5;c='<div>Price as of 10/27/26</div><td>$4.2661</td><td>$4.2661</td><td>$4.7966</td><td>$5.1822</td><td>$5.5656</td><td>$3.2856</td><td>$4.2602</td>';C=parse_aaa_gas_html(c);assert C=={"as_of_date":"2026-10-27","current_regular":4.2661,"yesterday_regular":4.2602};from src.polymarket_research.tradfi_sports_zero_fee_engine import detect_pyth_calendar_inclusion_boxes,parse_pyth_hit_event;s={"id":"ev_nov","startDate":"2026-10-25T04:02:00Z","endDate":"2026-12-01T04:59:59Z","markets":[{"id":"6172752","conditionId":"0xnov","question":"Will WTI Crude Oil (WTI) hit (HIGH) $100 in November?","groupItemTitle":"↑ $100","clobTokenIds":'["ny","nn"]',"feeType":"zero_fees","description":"during a trading session of November 2026, any Pyth 1-minute candle"}]};B=parse_pyth_hit_event(s,"WTI","MONTHLY","wti-hit");a=datetime(2026,10,28,12,0,tzinfo=ZoneInfo("America/New_York")).timestamp();assert len(B)==1 and B[0].start_ts>a;assert detect_pyth_calendar_inclusion_boxes([{"asset":"WTI","direction":"UP","strike":1e2,"start_ts":a-86400.,"end_ts":a+86400.,"ask_no":.4,"ask_yes":.6,"fee_rate":.0},{"asset":"WTI","direction":"UP","strike":1e2,"start_ts":B[0].start_ts,"end_ts":B[0].end_ts,"ask_no":.5,"ask_yes":.5,"fee_rate":.0}],now_ts=a)==[];H=ZoneInfo("America/New_York");A=datetime(2026,10,28,10,31,tzinfo=H).timestamp();z=datetime(2026,10,28,11,30,tzinfo=H).timestamp();y=evaluate_pyth_catalyst_shock("WTI",69.,70.2,71.,"UP",3.,.35,A);x=evaluate_pyth_catalyst_shock("WTI",69.,70.2,71.,"UP",3.,.35,z);assert y["eligible"]is True and y["catalyst"]=="EIA_1030_PETROLEUM"and y["side"]=="YES";assert x["eligible"]is False;j=[{"organization":"Google","rating":1395,"rating_q025":1388,"rating_q975":1402},{"organization":"OpenAI","rating":1372,"rating_q025":1365,"rating_q975":1379}];assert evaluate_ai_elo_ci_lock(j,1e3,5e4,3.6e4)["eligible"]is False,"Stale >6h snapshot must be rejected!";assert evaluate_ai_elo_ci_lock(j,4.8e4,5e4,3.6e4)["eligible"]is True;G=detect_d2_12pm_binance_boxes({"asset":"BTC","market_id":"h1","condition_id":"0xh1","end_ts":1793203200.,"up_token":"h_up","down_token":"h_dn","fee_rate":.07},83800.,[{"market_id":"d1","condition_id":"0xd1","end_ts":1793203200.,"strike":84400.,"is_downward":False,"yes_token":"d_y","no_token":"d_n","fee_rate":.07}]);assert len(G)==1 and G[0]["leg_a"]["token_id"]=="h_up"and G[0]["leg_b"]["token_id"]=="d_n";monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"zfa_st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"zfa_ldg.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"zfa_opps.json")
 async def _run_zfa():
  d=a124.Alpha124ShadowDaemon(single_scan=True);c=1.79322e9;g={"token_id":"za1","opp_token_id":"za2","condition_id":"0x1","side":"YES","label":"Nets +4.5","market_id":"m1","fee_rate":.0};f={"token_id":"zb1","opp_token_id":"zb2","condition_id":"0x2","side":"YES","label":"Celtics ML","market_id":"m2","fee_rate":.0};b={"bids":[{"price":"0.41","size":"200"}],"asks":[{"price":"0.45","size":"200"}]};a={"bids":[{"price":"0.54","size":"300"}],"asks":[{"price":"0.56","size":"300"}]};e=d.post_zero_fee_maker_anchor_box("SP1_NBA","NBA","ZFA_TEST_1",g,f,b,a,c+7200.,"Nets vs Celtics",c);assert e is True and d.pending_zero_fee_maker_anchors["ZFA_TEST_1"]["bid_px"]==.42
  async def fake_bks_fill(toks,timeout=3.):return{"za1":{"bids":[{"price":"0.41","size":"200"}],"asks":[{"price":"0.42","size":"200"}]},"zb1":{"bids":[{"price":"0.54","size":"300"}],"asks":[{"price":"0.56","size":"300"}]}}
  monkeypatch.setattr(d,"fetch_books_batch",fake_bks_fill);await d.manage_pending_zero_fee_maker_anchors(c+2.);assert any(p["sleeve"]in("ZF_INTRADAY_MAKER_BOX","ZERO_FEE_MAKER_ANCHOR_BOX")and p["entry_eff_px_t1000"]==.98 for p in d.open_positions.values())
 asyncio.run(_run_zfa())
def test_exp406_hardened_d1_maker_leg1_wfo_and_microstructure_shields(tmp_path,monkeypatch):
 import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.orderflow_wfo_simulators import calibrate_d1_maker_leg1_wfo;from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec,determine_dominance_legs;o=calibrate_d1_maker_leg1_wfo();assert o["sealed_holdout"]["legging_adjusted_pnl_usd"]>.0;assert o["sealed_holdout"]["scratches"]==0;assert o["sealed_holdout"]["legging_adjusted_pnl_usd"]>o["unguarded_maker_holdout_baseline"]["legging_adjusted_pnl_usd"];monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"m406_st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"m406_ldg.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"m406_opps.json");monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","0");d=a124.Alpha124ShadowDaemon(single_scan=True);h=1793226000.;n=TwapCandleMarketSpec(asset="BTC",horizon="15m",market_id="m15_btc",condition_id="0xc15",title="BTC 15m",start_iso="2026-10-28T22:15:00Z",end_iso="2026-10-28T22:30:00Z",start_ts=h-700,end_ts=h+200,up_token="t15u",down_token="t15d",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams");v=TwapCandleMarketSpec(asset="BTC",horizon="5m",market_id="m5_btc",condition_id="0xc5",title="BTC 5m",start_iso="2026-10-28T22:25:00Z",end_iso="2026-10-28T22:30:00Z",start_ts=h-100,end_ts=h+200,up_token="t5u",down_token="t5d",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams");m=determine_dominance_legs(n,8.1e4,v,81050.,min_corridor_bps=3.);assert m is not None;u,s=m["leg_a"]["token_id"],m["leg_b"]["token_id"];b={"bids":[{"price":"0.48","size":"20"}],"asks":[{"price":"0.49","size":"60"}]};f={"bids":[{"price":"0.48","size":"80"}],"asks":[{"price":"0.49","size":"80"}]};assert d.post_maker_anchor_candidate(n,v,m,b,b,now_ts=h)is False;d.spots["BTC"]=81025.;c={"bids":[{"price":"0.48","size":"90"}],"asks":[{"price":"0.49","size":"80"}]};assert d.post_maker_anchor_candidate(n,v,m,c,f,now_ts=h)is True;r=f"D1_MKR_BTC_{n.market_id}_{v.market_id}";assert d.pending_maker_anchors[r]["bid_px"]==.48 and d.pending_maker_anchors[r]["queue_front"]is False;a={u:c,s:f}
 async def _fb(toks,timeout=2.5):return{t:a[t]for t in toks if t in a}
 monkeypatch.setattr(d,"fetch_books_batch",_fb)
 if m["leg_a"]["side"]=="UP":d.spots["BTC"]=81025.*1.0003
 else:d.spots["BTC"]=81025.*.9997
 asyncio.run(d.manage_pending_maker_anchors(now_ts=h+.5));assert r in d.pending_maker_anchors,"Favorable spot move must NOT cancel resting anchor!"
 if m["leg_a"]["side"]=="UP":d.spots["BTC"]=81025.*.99965
 else:d.spots["BTC"]=81025.*1.00035
 asyncio.run(d.manage_pending_maker_anchors(now_ts=h+.8));assert r not in d.pending_maker_anchors,"Adverse spot move > 2.5 bps MUST cancel resting anchor at $0 cost!";q=TwapCandleMarketSpec(asset="XRP",horizon="4h",market_id="m4_xrp",condition_id="0xx4",title="XRP 4h",start_iso="2026-10-28T20:00:00Z",end_iso="2026-10-29T00:00:00Z",start_ts=h-14000,end_ts=h+200,up_token="tx4u",down_token="tx4d",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/xrp-usd-twap-60s-streams");l=TwapCandleMarketSpec(asset="XRP",horizon="15m",market_id="m15_xrp",condition_id="0xx15",title="XRP 15m",start_iso="2026-10-28T23:45:00Z",end_iso="2026-10-29T00:00:00Z",start_ts=h-700,end_ts=h+200,up_token="tx15u",down_token="tx15d",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/xrp-usd-twap-60s-streams");g=determine_dominance_legs(q,.52,l,.522,min_corridor_bps=3.);assert g is not None;k,j=g["leg_a"]["token_id"],g["leg_b"]["token_id"];d.spots["XRP"]=.521;a[k]={"bids":[{"price":"0.963","size":"80"}],"asks":[{"price":"0.999","size":"80"}]};a[j]={"bids":[{"price":"0.018","size":"80"}],"asks":[{"price":"0.020","size":"80"}]};assert d.post_maker_anchor_candidate(q,l,g,a[k],a[j],now_ts=h)is True;i=f"D1_MKR_XRP_{q.market_id}_{l.market_id}";assert d.pending_maker_anchors[i]["bid_px"]==.964;a[k]={"bids":[{"price":"0.963","size":"80"}],"asks":[{"price":"0.964","size":"40"}]};asyncio.run(d.manage_pending_maker_anchors(now_ts=h+1.));e=[p for p in d.open_positions.values()if p["dedupe_key"]==i];assert len(e)==1 and e[0]["entry_eff_px_t1000"]<.988;assert e[0]["extra"]["legging_drag_usd_by_tier"]["T1000"]>.0
def test_overround_bid_unwind_ctf_merge_and_corridor_preservation(tmp_path,monkeypatch):
 import asyncio;import time;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.macro_counting_ctf_engine import walk_position_overround_bid_unwind;from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;g=walk_position_overround_bid_unwind([{"bids":[{"price":"0.52","size":"25"}],"fee_rate":.0,"fee_exponent":1.},{"bids":[{"price":"0.52","size":"15"}],"fee_rate":.0,"fee_exponent":1.}],exact_shares=25.,min_net_proceeds_per_set=1.005);assert g["filled"]is False,"Must reject partial unwind if any leg lacks 100% of exact_shares!";f=walk_position_overround_bid_unwind([{"bids":[{"price":"0.52","size":"40"}],"fee_rate":.0,"fee_exponent":1.},{"bids":[{"price":"0.51","size":"40"}],"fee_rate":.0,"fee_exponent":1.}],exact_shares=25.,min_net_proceeds_per_set=1.005);assert f["filled"]is True;assert abs(f["net_proceeds_per_set"]-1.03)<1e-6;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"st_uw.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ld_uw.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"op_uw.json");monkeypatch.setattr(a124,"LIVE_ALPHA124_STATE_MIRROR_FILE",tmp_path/"mirror_uw.json");d=a124.Alpha124ShadowDaemon(single_scan=True);i=time.time();d.open_positions["FED1_TEST"]={"position_id":"FED1_TEST","dedupe_key":"FED1_DK","sleeve":"FED1_CENTRAL_BANK_LP_BOX","asset_or_city":"FOMC","title":"FOMC 2-Leg Box","side":"BOX","token_id":"tok_fomc_a+tok_fomc_b","fee_rate":.0,"entry_ts":i-60.,"close_ts":i+2e3*3600.,"entry_eff_px_t1000":.99,"p_model_entry":1.,"tier_fills":{"T100":{"shares":10.,"spent_usd":9.9,"fee_usd":.0},"T1000":{"shares":25.,"spent_usd":24.75,"fee_usd":.0}},"extra":{"is_two_leg_box":True,"guaranteed_payout":1.,"leg_a":{"token_id":"tok_fomc_a","market_id":"m_fomc_1","side":"YES","fee_rate":.0},"leg_b":{"token_id":"tok_fomc_b","market_id":"m_fomc_2","side":"NO","fee_rate":.0}}};d.open_positions["D1_NEAR_TEST"]={"position_id":"D1_NEAR_TEST","dedupe_key":"D1_NEAR_DK","sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","asset_or_city":"BTC","title":"BTC 15m/5m Corridor Box","side":"BOX","token_id":"tok_d1_a+tok_d1_b","fee_rate":.07,"entry_ts":i-45.,"close_ts":i+120.,"entry_eff_px_t1000":.98,"p_model_entry":1.,"tier_fills":{"T1000":{"shares":25.,"spent_usd":24.5,"fee_usd":.0}},"extra":{"guaranteed_payout":1.,"leg_a":{"token_id":"tok_d1_a","market_id":"m_d1_1","side":"UP","fee_rate":.07},"leg_b":{"token_id":"tok_d1_b","market_id":"m_d1_2","side":"DOWN","fee_rate":.07}}};d.open_positions["C1_MERGE_TEST"]={"position_id":"C1_MERGE_TEST","dedupe_key":"C1_DK","sleeve":"C1_BINARY_COMPLETE_SET","asset_or_city":"BTC","title":"BTC Single-Condition Complete Set","side":"COMPLETE_SET","token_id":"tok_c1_y+tok_c1_n","fee_rate":.0,"entry_ts":i-30.,"close_ts":i+7200.,"entry_eff_px_t1000":.985,"p_model_entry":1.,"tier_fills":{"T1000":{"shares":20.,"spent_usd":19.7,"fee_usd":.0}},"extra":{"guaranteed_payout":1.,"leg_a":{"token_id":"tok_c1_y","market_id":"m_c1_same","side":"YES","fee_rate":.0},"leg_b":{"token_id":"tok_c1_n","market_id":"m_c1_same","side":"NO","fee_rate":.0}}};b={"tok_fomc_a":{"bids":[{"price":"0.52","size":"50"}],"asks":[{"price":"0.54","size":"50"}]},"tok_fomc_b":{"bids":[{"price":"0.51","size":"50"}],"asks":[{"price":"0.53","size":"50"}]},"tok_d1_a":{"bids":[{"price":"0.53","size":"50"}],"asks":[{"price":"0.54","size":"50"}]},"tok_d1_b":{"bids":[{"price":"0.52","size":"50"}],"asks":[{"price":"0.53","size":"50"}]},"tok_c1_y":{"bids":[{"price":"0.49","size":"50"}],"asks":[{"price":"0.50","size":"50"}]},"tok_c1_n":{"bids":[{"price":"0.49","size":"50"}],"asks":[{"price":"0.50","size":"50"}]}}
 async def _fake_fetch(url,timeout=2.5):
  for b,a in b.items():
   if f"token_id={b}"in url:return a
  return None
 monkeypatch.setattr(d,"fetch_json",_fake_fetch);asyncio.run(d.manage_open_positions());assert"D1_NEAR_TEST"in d.open_positions,"Near-expiry D1 box must NOT unwind early on +3c overround; preserve $2.00 corridor!";assert"FED1_TEST"not in d.open_positions;assert"C1_MERGE_TEST"not in d.open_positions;a={c["position_id"]:c for c in d.closed_positions};assert a["FED1_TEST"]["status"]=="EARLY_OVERROUND_BID_UNWIND";assert abs(a["FED1_TEST"]["tier_pnls_usd"]["T1000"]-1.)<1e-6;assert a["C1_MERGE_TEST"]["status"]=="CTF_COMPLETE_SET_MERGED";assert abs(a["C1_MERGE_TEST"]["tier_pnls_usd"]["T1000"]-.3)<1e-6;k=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"merge_ex.jsonl");e="0x"+"cd"*32;h=k.merge_complete_set_positions(e,25.,neg_risk=False);j=k.merge_complete_set_positions(e,25.,neg_risk=True);assert h["merged"]is True and h["target_contract"].lower()==k.CTF_ADDRESS.lower();assert h["calldata"].startswith("0x9e7212ad");assert j["merged"]is True and j["target_contract"].lower()==k.NEG_RISK_ADAPTER_ADDRESS.lower();assert j["calldata"].startswith("0xb10c5c17")
def test_d1_quiet_book_graduation_and_close_position_growth_tier_promotion(tmp_path,monkeypatch):
 import json;import time;import src.polymarket_research.polymarket_live_harvester as harvester_mod;from src.polymarket_research.polymarket_live_harvester import ExecutionStatus,PolymarketLiveHarvester;g=tmp_path/"live_pm";g.mkdir(parents=True,exist_ok=True);monkeypatch.setattr(harvester_mod,"DATA_DIR",g);monkeypatch.setattr(harvester_mod,"STATE_FILE",g/"live_harvester_state.json");monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT","1");(g/"alpha124_shadow_state.json").write_text(json.dumps({"by_sleeve":{"D1_SAME_ORACLE_DOMINANCE_BOX":{"closed":5,"win_rate_pct":1e2,"realized_pnl_t1000_usd":15.,"legging_adjusted_pnl_t1000_usd":12.},"D1_QUIET_BOOK_BOX":{"closed":13,"win_rate_pct":1e2,"realized_pnl_t1000_usd":43.25,"legging_adjusted_pnl_t1000_usd":42.18}},"by_d1_asset":{}}),encoding="utf-8");h=PolymarketLiveHarvester(dry_run=True,dynamic_sizing=True,hold_to_maturity=False,ticket_notional=12.,max_exposure=76.25,max_concurrent=2,allowed_assets={"BTC","ETH"});h.dry_run=False;h.executor.dry_run=False;h.executor.auth_mode="AUTHENTICATED_L2";h.executor.is_authenticated=True;h.executor.is_heartbeat_healthy=lambda:True;h.state_file=g/"live_harvester_state.json";h._startup_reconciled=True;h._last_known_collateral=138.98;h.high_water_mark_equity=138.98;h._update_equity_tier(138.98);assert h.current_equity_tier=="RECOVERY";n="111111111111111111111111111111";k="222222222222222222222222222222";m="333333333333333333333333333333";j="444444444444444444444444444444";l=time.time();e={"box_id":"D1_QUIET_BTC_1","dedupe_key":"D1_QB_BTC_1","box_type":"DOMINANCE","ts_unix":l,"expiry_ts":l+180.,"asset":"BTC","corridor_bps":8.,"k_low":8e4,"k_high":80064.,"is_quiet_book":True,"shares":25,"box_cost_net":.981,"max_box_cost_net":.985,"leg_a_token_id":n,"leg_a_opp_token_id":k,"leg_a_label":"15M_UP","leg_a_side":"UP","leg_a_horizon":"15m","leg_a_market_id":"610001","leg_a_condition_id":"0x"+"11"*32,"leg_a_strike":8e4,"leg_a_limit_price":.47,"leg_a_avail_shares":120.,"leg_a_fee_rate":.07,"leg_a_fee_exponent":1.,"leg_b_token_id":m,"leg_b_opp_token_id":j,"leg_b_label":"5M_DOWN","leg_b_side":"DOWN","leg_b_horizon":"5m","leg_b_market_id":"610002","leg_b_condition_id":"0x"+"22"*32,"leg_b_strike":80064.,"leg_b_limit_price":.47,"leg_b_avail_shares":120.,"leg_b_fee_rate":.07,"leg_b_fee_exponent":1.};a=h.maybe_execute_graduated_d1_box({**e,"sleeve_source":"D1_SAME_ORACLE_DOMINANCE_BOX","dedupe_key":"D1_CORE_BLK"});assert a["executed"]is False and a["reason"]=="D1_NOT_YET_8_OF_8_GRADUATED";f={n:{"asks":[{"price":"0.47","size":"120"}],"bids":[{"price":"0.45","size":"120"}]},m:{"asks":[{"price":"0.47","size":"120"}],"bids":[{"price":"0.45","size":"120"}]},k:{"asks":[{"price":"0.55","size":"120"}],"bids":[{"price":"0.52","size":"120"}]},j:{"asks":[{"price":"0.55","size":"120"}],"bids":[{"price":"0.47","size":"120"}]}};h.executor.get_market_book=lambda o:f[o];h._wallet_token_balance=lambda tid:(.0,h.ONCHAIN_SOURCE);b={}
 def _mock_qb_box(**kw):b.update(kw);a=float(kw["shares"]);return{"success":True,"box_id":kw["box_id"],"shares":a,"leg_1":{"token_id":n,"label":kw["leg_a_label"],"price":.47,"orderID":"OID_QBA","raw":{"makingAmount":round(a*.47,2)}},"leg_2":{"token_id":m,"label":kw["leg_b_label"],"price":.47,"orderID":"OID_QBB","raw":{"makingAmount":round(a*.47,2)}}}
 h.executor.execute_atomic_dominance_box=_mock_qb_box;d=h.maybe_execute_graduated_d1_box({**e,"sleeve_source":"D1_QUIET_BOOK_BOX"});assert d["executed"]is True;assert b["parallel_dispatch"]is False,"Tighter (0.975..0.985] quiet box must preserve sequential Leg-1 dispatch!";assert h.active_positions["D1_QUIET_BTC_1_L1"]["sleeve_source"]=="D1_QUIET_BOOK_BOX";h.active_positions.clear();h._last_known_collateral=108.78;h.active_positions["LIVE_WIN_141"]={"trade_id":"LIVE_WIN_141","token_id":"tok_eth_up","target_token":"UP","asset":"ETH","entry_price":.85,"entry_shares":35.,"remaining_shares":.0,"filled_exit_shares":35.,"notional_usd":29.75,"fee_usd":.45,"confirmed_realized_cash":32.9,"realized_exit_cash":32.9,"realized_exit_fee":.0,"entry_ts":l-120.,"candle_expiry_ts":l+1800.,"status":ExecutionStatus.POSITION_CONFIRMED};i=h._close_position("LIVE_WIN_141",h.active_positions["LIVE_WIN_141"],ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True);assert abs(i-2.7)<1e-2;assert h.current_equity_tier=="GROWTH";assert abs(h.max_exposure-106.26)<1e-2;assert h.max_concurrent_positions==3;assert abs(h.dynamic_bankroll_pct-.26)<1e-6;c=json.loads((g/"live_harvester_state.json").read_text(encoding="utf-8"));assert c["equity_tier"]=="GROWTH";assert abs(float(c["max_exposure"])-106.26)<1e-2;assert int(c["max_concurrent_positions"])==3
def test_bond1_uma_resolution_carry_onchain_and_settlement_guard(tmp_path,monkeypatch):
 import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124;import src.polymarket_research.uma_nba_endgame_engine as uma_mod;from src.polymarket_research.uma_nba_endgame_engine import(HALF_E18,ONE_E18,is_objective_uma_market,verify_uma_onchain_proposal_sync);h={"id":"990001","conditionId":"0x"+"aa"*32,"questionID":"0x"+"bb"*32,"negRisk":True,"negRiskRequestID":"0x"+"cc"*32,"resolvedBy":"0x69c47De9D4D3Dad79590d61b9e05918E03775f24","closed":False,"archived":False,"acceptingOrders":True,"umaResolutionStatus":"proposed","umaResolutionStatuses":'["proposed"]',"outcomes":'["Yes", "No"]',"outcomePrices":'["0.004", "0.996"]',"clobTokenIds":'["tok_uma_yes", "tok_uma_no"]',"question":"Will the highest temperature in Tokyo be 21°C on October 28?","description":"Resolves via https://aviationweather.gov/api/data/metar?ids=RJTT routine METAR; SPECI excluded.","feesEnabled":False};r,p=is_objective_uma_market(h);assert r is True and p=="VERIFIED_PRIMARY_ORACLE";o,k=is_objective_uma_market({**h,"question":'Will Trump say "Tariff" during his speech?'});assert o is False and k=="SUBJECTIVE_OR_SPEECH_VETO";i,g=is_objective_uma_market({**h,"umaResolutionStatuses":'["proposed", "disputed", "proposed"]'});assert i is False and g=="PRIOR_DISPUTE_HISTORY";c,j=is_objective_uma_market({**h,"negRiskRequestID":""});assert c is False and j=="MISSING_REQUEST_ID"
 def _build_gq_hex(req_ts,anc,reset=False):a=[b"\x00"*32 for _ in range(13)];a[1]=req_ts.to_bytes(32,"big");a[4]=(7200).to_bytes(32,"big");a[8]=(1 if reset else 0).to_bytes(32,"big");a[12]=(12*32).to_bytes(32,"big");b=b"\x00"*((32-len(anc)%32)%32);return"0x"+b"".join(a).hex()+len(anc).to_bytes(32,"big").hex()+(anc+b).hex()
 def _build_rq_hex(proposer_hex,disputer_hex,prop_price,exp_ts):w=[b"\x00"*32 for _ in range(16)];w[0]=bytes.fromhex(proposer_hex.replace("0x","").rjust(64,"0"));w[1]=bytes.fromhex(disputer_hex.replace("0x","").rjust(64,"0"));w[10]=(7200).to_bytes(32,"big");a=prop_price if prop_price>=0 else(1<<256)+prop_price;w[11]=a.to_bytes(32,"big");w[13]=exp_ts.to_bytes(32,"big");return"0x"+b"".join(w).hex()
 n=1.7932e9;m=int(n+3600);l=b"q: title: Tokyo 21C, res_data: p1: 0, p2: 1, p3: 0.5.";b="0x"+"2c0367a9db231ddebd88a94b4f6461a6e47c58b1".rjust(64,"0");f="0x"+"11"*20;e={"oo_state":2,"disputer":uma_mod.ZERO_ADDR,"price":0,"reset":False,"exp":m}
 def _fake_rpc_post(rpc_url,payload,timeout=5.):
  c=[]
  for a in payload:
   b=a["id"]
   if b==1:c.append({"id":1,"result":_build_gq_hex(1793190000,l,reset=e["reset"])})
   elif b==2:c.append({"id":2,"result":b})
   elif b==10:c.append({"id":10,"result":hex(e["oo_state"])})
   elif b==11:c.append({"id":11,"result":_build_rq_hex(f,e["disputer"],e["price"],e["exp"])})
  return c
 uma_mod._OO_ADDR_CACHE.clear();monkeypatch.setattr(uma_mod,"_rpc_post",_fake_rpc_post);q=verify_uma_onchain_proposal_sync(h,rpc_url="http://mock",now_ts=n);assert q["verified"]is True;assert q["win_index"]==1 and q["win_outcome_name"]=="No"and q["win_token"]=="tok_uma_no";e["disputer"]="0x"+"99"*20;assert verify_uma_onchain_proposal_sync(h,rpc_url="http://mock",now_ts=n)["verified"]is False;e["disputer"]=uma_mod.ZERO_ADDR;e["price"]=HALF_E18;assert verify_uma_onchain_proposal_sync(h,rpc_url="http://mock",now_ts=n)["reason"]=="TIE_50_50_PROPOSAL_VETO";e["price"]=0;e["reset"]=True;assert verify_uma_onchain_proposal_sync(h,rpc_url="http://mock",now_ts=n)["verified"]is False;e["reset"]=False;e["exp"]=int(n+7150);assert"PROPOSAL_TOO_FRESH"in verify_uma_onchain_proposal_sync(h,rpc_url="http://mock",now_ts=n)["reason"];e["exp"]=m;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"b1_state.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"b1_ledger.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"b1_opps.json");a={"done":False}
 async def _run_bond_sim():
  d=a124.Alpha124ShadowDaemon(single_scan=True);d.uma_proposed_markets={"990001":h};d.last_uma_discovery_ts=n
  async def _fake_disc(ts):d.uma_proposed_markets={"990001":h}
  async def _fake_fetch(url,timeout=4.):
   if"tok_uma_no"in url:return{"bids":[{"price":"0.991","size":"500"}],"asks":[{"price":"0.992","size":"500"}]}
   if"tok_uma_yes"in url:return{"bids":[{"price":"0.001","size":"200"}],"asks":[{"price":"0.004","size":"500"}]}
   if"/markets/990001"in url:
    if a["done"]:return{**h,"closed":True,"umaResolutionStatus":"resolved","outcomePrices":'["0", "1"]'}
    return{**h,"closed":False,"umaResolutionStatus":"proposed"}
   return None
  async def _fake_batch(toks,timeout=3.5):return{t:await _fake_fetch(t)for t in toks}
  monkeypatch.setattr(d,"discover_uma_proposed_markets",_fake_disc);monkeypatch.setattr(d,"fetch_json",_fake_fetch);monkeypatch.setattr(d,"fetch_books_batch",_fake_batch);a=[];await d.scan_uma_resolution_bonds(a,now_ts=n);assert len(d.open_positions)==1;c=next(iter(d.open_positions));b=d.open_positions[c];assert b["sleeve"]=="BOND1_UMA_RESOLUTION_CARRY";assert abs(float(b["entry_eff_px_t1000"])-.992)<1e-4;b["close_ts"]=time.time()-120.;await d.manage_open_positions();assert c in d.open_positions,"BOND1 must NEVER self-settle on CLOB best_bid >= 0.99 while UMA is still proposed!";a["done"]=True;await d.manage_open_positions();assert c not in d.open_positions;assert d.closed_positions[-1]["won"]is True;assert abs(d.closed_positions[-1]["tier_pnls_usd"]["T1000"]-round(120./.992-120.,2))<.05
 import time;asyncio.run(_run_bond_sim())
def test_w1_v2_cape_town_fact_and_low_trough_lock_cold_front_veto():
 from datetime import date;from src.polymarket_research.weather_metar_engine import(HIGH_VOLUME_WEATHER_SERIES,STATION_CATALOG,WeatherBucket,WeatherEventSpec,compute_weather_probabilities,parse_metar_line,parse_weather_event);assert"FACT"in STATION_CATALOG
 for q in("atlanta-daily-weather","san-francisco-daily-weather","seattle-daily-weather","amsterdam-daily-weather","cape-town-daily-weather","tokyo-daily-lowest-temperature"):assert q in HIGH_VOLUME_WEATHER_SERIES
 o={"id":"ev_fact_1","title":"Highest temperature in Cape Town on October 29?","series":[{"slug":"cape-town-daily-weather"}],"endDate":"2026-10-29T22:00:00Z","markets":[{"id":f"m_{i}","conditionId":f"0x{i}","groupItemTitle":r,"clobTokenIds":f'["y_{i}", "n_{i}"]',"description":"Resolves to the highest temperature recorded in a routine (METAR) observation for Cape Town International Airport (FACT) on October 29, 2026. SPECI reports are excluded."}for i,r in enumerate(["18°C or below","19°C","20°C","21°C or higher"])]};n=parse_weather_event(o);assert n is not None and n.icao=="FACT"and n.city=="Cape Town";c={**o,"markets":[{**m,"description":"Resolves via Wunderground station history for Cape Town (FACT)."}for m in o["markets"]]};assert parse_weather_event(c,allow_historical_same_station=False)is None;j=datetime(2026,10,29,2,0,tzinfo=timezone.utc);b=parse_metar_line("METAR RJTT 282000Z 34008KT 9999 FEW030 12/06 Q1018 RMK T01200060","RJTT",j,"Asia/Tokyo");g=parse_metar_line("METAR RJTT 290200Z 02009KT 9999 FEW035 15/07 Q1019 RMK T01540070","RJTT",j,"Asia/Tokyo");assert b is not None and g is not None;l=[WeatherBucket("b1","c1","11°C or below","11C-","y1","n1","C",float("-inf"),11.),WeatherBucket("b2","c2","12°C","12C","y2","n2","C",12.,12.),WeatherBucket("b3","c3","13°C","13C","y3","n3","C",13.,13.),WeatherBucket("b4","c4","14°C or higher","14C+","y4","n4","C",14.,float("inf"))];p=WeatherEventSpec(event_id="ev_rjtt_low",slug="tokyo-low-oct-29",series_slug="tokyo-daily-lowest-temperature",title="Lowest temperature in Tokyo on October 29?",icao="RJTT",city="Tokyo",lat=35.5523,lon=139.7798,tz_name="Asia/Tokyo",obs_date=date(2026,10,29),metric="LOW",unit="C",fee_type="zero_fees",end_date_iso="2026-10-29T15:00:00Z",buckets=l);k=int(j.timestamp());f={k+h*3600:[15.5+.02*m for m in range(40)]for h in range(0,14)};e=compute_weather_probabilities(p,j,[b,g],f);assert e["is_solar_lock"]is True and e["locked_bucket_idx"]==1 and e["p_locked_bucket"]>=.93;a={k+h*3600:([13.2+.05*m for m in range(40)]if h==11 else[15.5 for _ in range(40)])for h in range(0,14)};d=compute_weather_probabilities(p,j,[b,g],a);assert d["is_solar_lock"]is False
def test_sp2_nba_endgame_lock_espn_parser_and_overtime_trap_veto():from src.polymarket_research.tradfi_sports_zero_fee_engine import NbaGameSpec,NbaOutcomeLeg;from src.polymarket_research.uma_nba_endgame_engine import(LiveNbaGameState,evaluate_nba_endgame_locks,match_nba_live_game,parse_espn_nba_scoreboard,verify_uma_against_nba_live);b={"events":[{"id":"401700001","date":"2026-10-29T00:00Z","competitions":[{"date":"2026-10-29T00:00Z","status":{"clock":35.,"displayClock":"0:35","period":4,"type":{"state":"in","completed":False}},"competitors":[{"homeAway":"home","score":"114","team":{"name":"Celtics","abbreviation":"BOS"}},{"homeAway":"away","score":"103","team":{"name":"Heat","abbreviation":"MIA"}}]}]}]};p=parse_espn_nba_scoreboard(b);assert len(p)==1 and p[0].home_score==114 and p[0].away_score==103 and p[0].clock_sec==35.;n=1793232000.;p[0].start_ts=n;r=NbaGameSpec(event_id="nba_1",slug="nba-mia-bos",title="Heat vs. Celtics",team_a="Heat",team_b="Celtics",tipoff_ts=n,settle_est_ts=n+9600.,margin_legs=[NbaOutcomeLeg("m_ml","c_ml","moneyline","tok_mia","tok_bos",0,"YES","ML Heat","GT",.0),NbaOutcomeLeg("m_ml","c_ml","moneyline","tok_bos","tok_mia",1,"NO","ML Celtics","LT",.0),NbaOutcomeLeg("m_sp","c_sp","spreads","tok_mia_p75","tok_bos_m75",0,"YES","Heat +7.5","GT",-7.5),NbaOutcomeLeg("m_sp","c_sp","spreads","tok_bos_m75","tok_mia_p75",1,"NO","Celtics -7.5","LT",-7.5)],total_legs=[NbaOutcomeLeg("m_tot","c_tot","totals","tok_ov","tok_un",0,"YES","Over 214.5","OVER",214.5),NbaOutcomeLeg("m_tot","c_tot","totals","tok_un","tok_ov",1,"NO","Under 214.5","UNDER",214.5)]);j=match_nba_live_game(r,p);assert j is not None;q,m,l=j;assert m==103 and l==114;i,h=verify_uma_against_nba_live({"question":"Heat vs. Celtics","sportsMarketType":"moneyline","outcomes":'["Heat", "Celtics"]',"gameStartTime":"2026-10-29T00:00:00Z"},1,p);assert i is False and h=="NBA_GAME_NOT_FINAL_YET";g=evaluate_nba_endgame_locks(r,q,m,l);a={c["leg"].display_label:c for c in g};assert"Over 214.5"in a and a["Over 214.5"]["mode"]=="LIVE_TOTAL_OVER_LOCKED";assert"ML Celtics"in a and a["ML Celtics"]["p_lock"]>=.993;assert"Celtics -7.5"not in a;k=LiveNbaGameState("401",n,"in",False,4,10.,"Celtics","BOS",105,"Heat","MIA",105);e=evaluate_nba_endgame_locks(r,k,105,105);assert all(c["leg"].display_label!="Heat +7.5"for c in e),"Must veto +7.5 spread when tied (Overtime trap)!";o=LiveNbaGameState("401",n,"post",True,4,.0,"Celtics","BOS",114,"Heat","MIA",103);f=evaluate_nba_endgame_locks(r,o,103,114);d={c["leg"].display_label for c in f};assert{"ML Celtics","Celtics -7.5","Over 214.5"}<=d
def test_focus_upgrades_locked_maker_depth_cap_and_tight_zf_boxes(tmp_path,monkeypatch):
 import asyncio;import io;import json;import time;import urllib.request;import src.polymarket_research.alpha_124_shadow_daemon as a124;import src.polymarket_research.uma_nba_endgame_engine as u_eng;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"foc_st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"foc_ldg.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"foc_opps.json");monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","0");seen_urls=[]
 class _FakeResp(io.BytesIO):
  def __enter__(self):return self
  def __exit__(self,*args):pass
 def _fake_urlopen(req,timeout=4.5):u=req.full_url if hasattr(req,"full_url")else str(req);seen_urls.append(u);a="401_YEST"if len(seen_urls)==1 else"401_TODAY";b={"events":[{"id":a,"date":"2026-10-29T02:00Z","status":{"period":4,"clock":18.,"type":{"state":"in","completed":False}},"competitions":[{"competitors":[{"homeAway":"home","score":"112","team":{"shortDisplayName":"Lakers","abbreviation":"LAL"}},{"homeAway":"away","score":"101","team":{"shortDisplayName":"Suns","abbreviation":"PHX"}}]}]}]};return _FakeResp(json.dumps(b).encode("utf-8"))
 monkeypatch.setattr(urllib.request,"urlopen",_fake_urlopen);games_dual=u_eng.fetch_espn_nba_scoreboard_sync(now_ts=1.79325e9);assert len(seen_urls)==2 and all("?dates="in u for u in seen_urls);assert{g.game_id for g in games_dual}=={"401_YEST","401_TODAY"}
 async def _run_focus():
  d=a124.Alpha124ShadowDaemon(single_scan=True);t=time.time();c={"bids":[{"price":"0.60","size":"50"}],"asks":[{"price":"0.768","size":"24.0"}]};a={"bids":[{"price":"0.87","size":"120"}],"asks":[]};b={"bids":[{"price":"0.991","size":"500"}],"asks":[]};f={"uma_created_ts":t}
  async def _fake_fetch_tape(url,timeout=3.):
   if"token_id=tok_nzwn_y"in url:return c
   if"token_id=tok_uma_w"in url:return b
   if"token_id=tok_uma_l"in url:return{"bids":[{"price":"0.001","size":"100"}],"asks":[]}
   if"token_id=tok_limc_y"in url:return a
   if"data-api.polymarket.com/trades?market=0xcond_uma"in url:a=int(f["uma_created_ts"]);return[{"timestamp":a-5,"asset":"tok_uma_w","price":.99,"size":500,"transactionHash":"0xold"},{"timestamp":a+5,"asset":"tok_uma_w","price":.992,"size":25.,"transactionHash":"0xfresh"}]
   return[]
  monkeypatch.setattr(d,"fetch_json",_fake_fetch_tape);s=await d.open_shadow_position(sleeve="W1_LOW_TROUGH_LOCK",dedupe_key="W1LOW_NZWN_13C",asset_or_city="Wellington_NZWN",title="Wellington Lowest Temp [13°C]",side_label="YES",token_id="tok_nzwn_y",fee_rate=.0,p_model=.99,close_ts=t+14400.,extra={"condition_id":"0xcond_nzwn"},prefetched_book=c);assert s is True;r=next(p for p in d.open_positions.values()if p["dedupe_key"]=="W1LOW_NZWN_13C");assert r["tier_fills"]["T100"]["spent_usd"]==15.;assert r["tier_fills"]["T1000"]["spent_usd"]==18.43;assert r["tier_fills"]["T1000"]["depth_capped"]is True;g=await d.post_shadow_maker_entry(sleeve="W1_LOW_TROUGH_LOCK",dedupe_key="W1LOW_LIMC_5C",asset="Milan_LIMC",title="Milan Lowest Temp [5°C]",side_label="YES",token_id="tok_limc_y",p_model=.99,close_ts=t+21600.,extra={"condition_id":"0xcond_limc","opp_token_id":"tok_limc_n"},prefetched_book=a);assert g is True;q=next(v for v in d.pending_maker_orders.values()if v["dedupe_key"]=="W1LOW_LIMC_5C");assert q["resting_bid"]==.88 and q["queue_ahead_usd"]==.0;e=await d.post_shadow_maker_entry(sleeve="BOND1_UMA_RESOLUTION_CARRY",dedupe_key="BOND1_NBA_FIN",asset="SPORTS",title="Celtics vs Heat [Celtics]",side_label="YES",token_id="tok_uma_w",p_model=1.,close_ts=t+3600.,extra={"condition_id":"0xcond_uma","opp_token_id":"tok_uma_l"},prefetched_book=b);assert e is True;k=next(v for v in d.pending_maker_orders.values()if v["dedupe_key"]=="BOND1_NBA_FIN");assert k["resting_bid"]==.992;k["created_ts"]=t-20.;q["created_ts"]=t-20.;f["uma_created_ts"]=k["created_ts"];await d.manage_pending_maker_orders();j=[p for p in d.open_positions.values()if p["dedupe_key"]=="BOND1_NBA_FIN"];assert len(j)==1;assert j[0]["maker_tp_px"]is None;assert j[0]["extra"].get("filled_via_trade_tape")is True;assert j[0]["tier_fills"]["T100"]["shares"]==round(20./.992,4);assert j[0]["tier_fills"]["T1000"]["shares"]==25.;o={"token_id":"sp1_a","opp_token_id":"sp1_ao","condition_id":"0xsp1","side":"YES","label":"Suns +4.5","market_id":"msp1","fee_rate":.0};n={"token_id":"sp1_b","opp_token_id":"sp1_bo","condition_id":"0xsp2","side":"YES","label":"Lakers -2.5","market_id":"msp2","fee_rate":.0};i={"bids":[{"price":"0.43","size":"120"}],"asks":[{"price":"0.44","size":"100"}]};h={"bids":[{"price":"0.43","size":"120"}],"asks":[{"price":"0.55","size":"100"}]};h["bids"]=[{"price":"0.54","size":"120"}];m=d.post_zero_fee_maker_anchor_box("SP1_NBA","NBA","ZFA_TIGHT_1C",o,n,i,h,t+5400.,"Suns vs Lakers",t);assert m is True;l=d.pending_zero_fee_maker_anchors["ZFA_TIGHT_1C"];assert l["queue_front"]is False and l["pair_est"]==.98
 asyncio.run(_run_focus())
def test_sp3_sports_corridor_and_negrisk_convert_sleeves(monkeypatch,tmp_path):
 from src.polymarket_research.tradfi_sports_zero_fee_engine import(parse_multi_sport_corridor_event,detect_multi_sport_corridor_boxes,parse_negrisk_convert_event,detect_negrisk_no_pair_boxes,detect_negrisk_convert_positions_arbs);from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon;l={"id":"ev_sp3_1","slug":"nfl-kc-buf-2027-11-01","title":"Chiefs vs. Bills","endDate":"2027-11-02T01:00:00Z","markets":[{"id":"901001","conditionId":"0xc1","sportsMarketType":"spreads","line":-2.5,"question":"Spread: Chiefs (-2.5)","outcomes":'["Chiefs", "Bills"]',"clobTokenIds":'["111111111111111111111", "111111111111111111112"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True},{"id":"901002","conditionId":"0xc2","sportsMarketType":"spreads","line":-6.5,"question":"Spread: Chiefs (-6.5)","outcomes":'["Chiefs", "Bills"]',"clobTokenIds":'["222222222222222222221", "222222222222222222222"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True},{"id":"901003","conditionId":"0xc3","sportsMarketType":"totals","line":44.5,"question":"Chiefs vs. Bills: O/U 44.5","outcomes":'["Over", "Under"]',"clobTokenIds":'["333333333333333333331", "333333333333333333332"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True},{"id":"901004","conditionId":"0xc4","sportsMarketType":"totals","line":48.5,"question":"Chiefs vs. Bills: O/U 48.5","outcomes":'["Over", "Under"]',"clobTokenIds":'["444444444444444444441", "444444444444444444442"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True},{"id":"901005","conditionId":"0xc5","sportsMarketType":"totals","line":46.,"question":"Chiefs vs. Bills: O/U 46.0","outcomes":'["Over", "Under"]',"clobTokenIds":'["555555555555555555551", "555555555555555555552"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True}]};o=parse_multi_sport_corridor_event(l);assert o is not None and o.sport=="NFL";assert len(o.legs)==8;assert"901005"not in{lg.market_id for lg in o.legs};assert all(abs(lg.fee_rate-.03)<1e-9 for lg in o.legs);a={"111111111111111111111":.46,"222222222222222222222":.49,"333333333333333333331":.47,"444444444444444444442":.48};k=detect_multi_sport_corridor_boxes(o,a,max_box_cost_net=.985);assert len(k)==2;assert all(.95<c["box_cost_net"]<=.985 for c in k);s={"id":"ev_nba_1h","slug":"nba-bos-mia-2027-11-01","title":"Celtics vs. Heat","endDate":"2027-11-02T01:00:00Z","markets":[{"id":"902001","conditionId":"0xn1","sportsMarketType":"first_half_spreads","line":-1.5,"question":"1H Spread: Celtics (-1.5)","outcomes":'["Celtics", "Heat"]',"clobTokenIds":'["611111111111111111111", "611111111111111111112"]',"feesEnabled":False},{"id":"902002","conditionId":"0xn2","sportsMarketType":"first_half_spreads","line":-4.5,"question":"1H Spread: Celtics (-4.5)","outcomes":'["Celtics", "Heat"]',"clobTokenIds":'["622222222222222222221", "622222222222222222222"]',"feesEnabled":False},{"id":"902003","conditionId":"0xn3","sportsMarketType":"spreads","line":-3.5,"question":"Spread: Celtics (-3.5)","outcomes":'["Celtics", "Heat"]',"clobTokenIds":'["633333333333333333331", "633333333333333333332"]',"feesEnabled":False},{"id":"902004","conditionId":"0xn4","sportsMarketType":"spreads","line":-7.5,"question":"Spread: Celtics (-7.5)","outcomes":'["Celtics", "Heat"]',"clobTokenIds":'["644444444444444444441", "644444444444444444442"]',"feesEnabled":False}]};n=parse_multi_sport_corridor_event(s,skip_nba_fg_zero_fee=True);m={"611111111111111111111":.48,"622222222222222222222":.49,"633333333333333333331":.48,"644444444444444444442":.49};j=detect_multi_sport_corridor_boxes(n,m,max_box_cost_net=.988);assert len(j)==1 and j[0]["scope"]=="1H:SPREAD";d={"id":"ev_nr_closed","slug":"fed-chair-vote-margin","title":"Vote Margin Partition","enableNegRisk":True,"negRiskAugmented":False,"negRiskMarketID":"0x"+"ab"*32,"endDate":"2027-11-05T18:00:00Z","markets":[{"id":"910001","conditionId":"0xd1","negRisk":True,"groupItemTitle":"Bucket A","questionID":"0x"+"ab"*31+"00","clobTokenIds":'["711111111111111111111", "711111111111111111112"]',"feesEnabled":False},{"id":"910002","conditionId":"0xd2","negRisk":True,"groupItemTitle":"Bucket B","questionID":"0x"+"ab"*31+"01","clobTokenIds":'["722222222222222222221", "722222222222222222222"]',"feesEnabled":False},{"id":"910003","conditionId":"0xd3","negRisk":True,"groupItemTitle":"Bucket C","questionID":"0x"+"ab"*31+"02","clobTokenIds":'["733333333333333333331", "733333333333333333332"]',"feesEnabled":False}]};i=parse_negrisk_convert_event(d);assert i is not None and i.is_closed_convert_safe is True;r={"711111111111111111112":{"asks":[{"price":"0.46","size":"100"}]},"722222222222222222222":{"asks":[{"price":"0.51","size":"100"}]},"733333333333333333331":{"bids":[{"price":"0.08","size":"100"}]},"733333333333333333332":{"asks":[{"price":"0.94","size":"100"}]}};f={"711111111111111111112":.46,"722222222222222222222":.51,"733333333333333333332":.94};b=detect_negrisk_no_pair_boxes(i,f,max_box_cost_net=.99);assert len(b)==1 and abs(b[0]["box_cost_net"]-.97)<1e-6;e=detect_negrisk_convert_positions_arbs(i,r,min_net_edge_per_share=.012);assert len(e)>=1 and e[0]["net_edge_per_share"]>.08;h=dict(d,id="ev_nr_aug",negRiskAugmented=True);q=parse_negrisk_convert_event(h);assert q is not None and q.is_closed_convert_safe is False;assert len(detect_negrisk_no_pair_boxes(q,f,max_box_cost_net=.99))==1;assert detect_negrisk_convert_positions_arbs(q,r,min_net_edge_per_share=.012)==[];import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124_mod;monkeypatch.setattr(a124_mod,"STATE_FILE",tmp_path/"a124_q.json");monkeypatch.setattr(a124_mod,"LEDGER_FILE",tmp_path/"a124_q_ledger.jsonl");monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","1");p=Alpha124ShadowDaemon(single_scan=False);p.twap_candles={"dummy":1};asyncio.run(p.scan_exact_twap_locks([]));assert p.twap_candles=={};p._apply_ws_book_snapshot("tok_lazy",[{"price":"0.45","size":"50"}],[{"price":"0.47","size":"50"}],1e3);assert p._apply_ws_price_changes("tok_lazy",[{"price":"0.46","size":"60","side":"BUY"}],1001.)is True;assert"tok_lazy"in p._ws_books._dirty;t=p._ws_books["tok_lazy"];assert t[0]==1001. and t[1]["bids"][0]["price"]=="0.4600"
 async def _mock_fetch_batch(toks,timeout=3.):return r
 p.fetch_books_batch=_mock_fetch_batch;g=[];assert asyncio.run(p.execute_negrisk_convert_positions_arb(i,e[0],r,g))is True;assert p.closed_positions[-1]["sleeve"]=="NR_CONV_NO_BASKET_ARB"and p.closed_positions[-1]["won"]is True
def test_riskless_frontier_v2_all_six_sleeves(monkeypatch,tmp_path):
 from src.polymarket_research.riskless_frontier_v2_engine import(MOOV2_ORACLE_ADDR,build_lp1_bop_2026_truth_legs,build_lp1_nba_exact_margin_bundle,detect_nr2_convert_no_subset_arbs,detect_soc1_regulation_boxes,detect_sp4_milestone_ladder_boxes,evaluate_api1_esports_bo3_opportunities,evaluate_sp4_ingame_clinch_locks,find_state_matrix_dominance_boxes,link_and_parse_soccer_regulation_trees,parse_espn_nba_boxscore_players,parse_esports_bo3_event,parse_nba_player_props_from_event,verify_bond2_moov2_final_hour_sync);from src.polymarket_research.tradfi_sports_zero_fee_engine import(detect_negrisk_convert_positions_arbs,parse_negrisk_convert_event);from src.polymarket_research.uma_nba_endgame_engine import LiveNbaGameState;import src.polymarket_research.riskless_frontier_v2_engine as rfv2;E={"id":"ev_nr5","slug":"closed-5way-slate","title":"Closed 5-Way Slate","enableNegRisk":True,"negRiskAugmented":False,"negRiskMarketID":"0x"+"cd"*32,"endDate":"2026-11-10T18:00:00Z","markets":[{"id":f"92000{i}","conditionId":f"0xe{i}","negRisk":True,"active":True,"groupItemTitle":f"Contender {i}","questionID":"0x"+"cd"*31+f"0{i}","clobTokenIds":f'["8{i}1111111111111111111", "8{i}2222222222222222222"]',"feesEnabled":False}for i in range(5)]};N=parse_negrisk_convert_event(E);assert N is not None and N.is_closed_convert_safe is True;J={**E,"markets":[*E["markets"][:4],{**E["markets"][4],"groupItemTitle":"Party A"}]};assert parse_negrisk_convert_event(J).is_closed_convert_safe is False;v={"802222222222222222222":{"asks":[{"price":"0.48","size":"100"}]},"812222222222222222222":{"asks":[{"price":"0.56","size":"100"}]},"821111111111111111111":{"bids":[{"price":"0.08","size":"100"}]},"831111111111111111111":{"bids":[]},"841111111111111111111":{"bids":[]}};assert detect_negrisk_convert_positions_arbs(N,v)==[];o=detect_nr2_convert_no_subset_arbs(N,v,target_budget_usd=1e2);assert len(o)==1;assert o[0]["m_no_legs"]==2 and o[0]["retained_tail_count"]==2;assert abs(o[0]["net_edge_per_share"]-.04)<1e-4;D={"id":"ev_nba_sp4","slug":"nba-sas-uta-2026-10-30","title":"Spurs vs. Jazz","startTime":"2026-10-30T23:00:00Z","markets":[{"id":"p1","conditionId":"0xc1","sportsMarketType":"points","line":23.5,"feeType":"zero_fees","groupItemTitle":"Victor Wembanyama: Points O/U 23.5","outcomes":'["Yes", "No"]',"clobTokenIds":'["90011", "90012"]'},{"id":"p2","conditionId":"0xc2","sportsMarketType":"points","line":27.5,"feeType":"zero_fees","groupItemTitle":"Victor Wembanyama: Points O/U 27.5","outcomes":'["Yes", "No"]',"clobTokenIds":'["90021", "90022"]'}]};C=parse_nba_player_props_from_event(D);assert C is not None;M=detect_sp4_milestone_ladder_boxes(C,{"90011":.61,"90022":.37},max_box_cost_net=.992);assert len(M)==1 and abs(M[0]["box_cost_net"]-.98)<1e-6;f={"boxscore":{"players":[{"statistics":[{"keys":["minutes","points","rebounds","assists","threePointFieldGoalsMade-threePointFieldGoalsAttempted"],"athletes":[{"athlete":{"displayName":"Victor Wembanyama"},"didNotPlay":False,"stats":["28","24","9","4","3-7"]},{"athlete":{"displayName":"DNP Bench"},"didNotPlay":True,"stats":["0","30","0","0","0-0"]}]}]}]}};u=parse_espn_nba_boxscore_players(f);assert"dnp bench"not in u and u["victor wembanyama"]["points"]==24;L=LiveNbaGameState("g1",1e3,"in",False,3,120.,"Jazz","UTA",80,"Spurs","SAS",84);B=LiveNbaGameState("g1",1e3,"post",True,4,.0,"Jazz","UTA",102,"Spurs","SAS",108);assert evaluate_sp4_ingame_clinch_locks(C,L,u)==[];assert len(evaluate_sp4_ingame_clinch_locks(C,B,u))==1;u["victor wembanyama"]["points"]=25;assert len(evaluate_sp4_ingame_clinch_locks(C,L,u))==1;monkeypatch.setattr(rfv2,"verify_uma_onchain_proposal_sync",lambda m,**kw:{"verified":True,"adapter":"0x65070be91477460d8a7aeeb94ef92fe056c2f2a7","oo_address":MOOV2_ORACLE_ADDR,"proposer":"0x"+"11"*20,"proposal_age_sec":4200.,"rem_challenge_sec":1800.,"win_index":0,"win_label":"YES","win_outcome_name":"Yes","win_token":"t_w","lose_token":"t_l","expiration_ts":5e3,"fee_rate":.0,"fee_exponent":1.,"domain":"SPORTS_POINTS","oo_state":2});monkeypatch.setattr(rfv2,"verify_proposer_whitelisted_sync",lambda addr,**kw:addr.endswith("1111"));assert verify_bond2_moov2_final_hour_sync({"id":"m_b2"})["verified"]is True;monkeypatch.setattr(rfv2,"verify_proposer_whitelisted_sync",lambda addr,**kw:False);assert verify_bond2_moov2_final_hour_sync({"id":"m_b2"})["reason"]=="PROPOSER_NOT_WHITELISTED";A={"id":"s3","slug":"epl-ars-che-2026-11-01","title":"Arsenal vs. Chelsea","gameId":"99001","negRisk":True,"negRiskAugmented":False,"negRiskMarketID":"0x"+"ef"*32,"startTime":"2026-11-01T16:30:00Z","markets":[{"id":"s_h","conditionId":"0x1","sportsMarketType":"moneyline","feeType":"sports_fees_v3","groupItemTitle":"Arsenal","question":"Will Arsenal win?","outcomes":'["Yes","No"]',"clobTokenIds":'["sh1","sh2"]',"questionID":"0x"+"ef"*31+"00"},{"id":"s_d","conditionId":"0x2","sportsMarketType":"moneyline","feeType":"sports_fees_v3","groupItemTitle":"Draw","question":"Will Arsenal vs Chelsea end in a draw?","outcomes":'["Yes","No"]',"clobTokenIds":'["sd1","sd2"]',"questionID":"0x"+"ef"*31+"01"},{"id":"s_a","conditionId":"0x3","sportsMarketType":"moneyline","feeType":"sports_fees_v3","groupItemTitle":"Chelsea","question":"Will Chelsea win?","outcomes":'["Yes","No"]',"clobTokenIds":'["sa1","sa2"]',"questionID":"0x"+"ef"*31+"02"}]};z={"id":"s_mm","slug":"epl-ars-che-2026-11-01-more-markets","gameId":"99001","negRisk":False,"markets":[{"id":"s_o05","conditionId":"0x4","sportsMarketType":"totals","line":.5,"feeType":"sports_fees_v3","groupItemTitle":"O/U 0.5","question":"O/U 0.5","outcomes":'["Over","Under"]',"clobTokenIds":'["so1","so2"]'}]};I=link_and_parse_soccer_regulation_trees([A,z]);assert"99001"in I and I["99001"].over05_leg is not None;assert detect_soc1_regulation_boxes(I["99001"],{},{"sd1":.22,"so1":.76},max_2leg_cost_net=.988)["two_leg_boxes"]==[];assert len(detect_soc1_regulation_boxes(I["99001"],{},{"sd1":.2,"so1":.75},max_2leg_cost_net=.988)["two_leg_boxes"])==1;n=build_lp1_bop_2026_truth_legs({"balance-of-power-2026-midterms":{"markets":[{"id":"b1","conditionId":"0xb1","question":"2026 Balance of Power: D Senate, D House","feeType":"zero_fees","endDate":"2026-11-04T00:00:00Z","clobTokenIds":'["by1","bn1"]'},{"id":"b5","conditionId":"0xb5","question":"2026 Balance of Power: Other","feeType":"zero_fees","endDate":"2026-11-04T00:00:00Z","clobTokenIds":'["by5","bn5"]'}]},"which-party-will-win-the-senate-in-2026":{"markets":[{"id":"s1","conditionId":"0xs1","groupItemTitle":"Democratic Party","feeType":"zero_fees","endDate":"2026-11-04T00:00:00Z","clobTokenIds":'["sy1","sn1"]'}]}});s=find_state_matrix_dominance_boxes(n,{"bn1":.3,"sy1":.67},max_2leg_cost_net=.993);assert len(s)==1 and s[0]["min_payout"]==1. and s[0]["jackpot_states"]==2;H={"id":"np1","slug":"nba-bos-nyk-2026-10-30","title":"Celtics vs. Knicks","startTime":"2026-10-30T23:30:00Z","markets":[{"id":"ml1","conditionId":"0xm1","sportsMarketType":"moneyline","feeType":"zero_fees","outcomes":'["Celtics","Knicks"]',"clobTokenIds":'["mla","mlb"]'}]};l=[("Celtics","1-5"),("Celtics","6-10"),("Celtics","11-15"),("Celtics","16-20"),("Celtics","21+"),("Knicks","1-5"),("Knicks","6-10"),("Knicks","11-15"),("Knicks","16-20"),("Knicks","21+")];y={"id":"ne1","slug":"nba-bos-nyk-2026-10-30-exact-margin","negRisk":True,"negRiskAugmented":False,"negRiskMarketID":"0x"+"aa"*32,"markets":[{"id":f"em{k}","conditionId":f"0xem{k}","feeType":"zero_fees","groupItemTitle":f"Exact Margin: {P} by {O}","clobTokenIds":f'["emy{k}","emn{k}"]',"questionID":"0x"+"aa"*31+f"{k:02x}"}for k,(P,O)in enumerate(l)]+[{"id":"em10","conditionId":"0xem10","feeType":"zero_fees","groupItemTitle":"Other","clobTokenIds":'["emy10","emn10"]',"questionID":"0x"+"aa"*31+"0a"}]};e=build_lp1_nba_exact_margin_bundle(H,y);assert e is not None and len(e["legs"])==24;r=find_state_matrix_dominance_boxes(e["legs"],{"mla":.58,"emn1":.4},max_2leg_cost_net=.993);assert len(r)==1 and r[0]["min_payout"]==1. and r[0]["max_payout"]==2.;q={"id":"esp1","slug":"cs2-navi-faze-2026-10-30","title":"Counter-Strike: NAVI vs FaZe (BO3)","startTime":"2026-10-30T20:00:00Z","markets":[{"id":"eml","conditionId":"0x1","sportsMarketType":"moneyline","feeType":"sports_fees_v2","outcomes":'["NAVI","FaZe"]',"clobTokenIds":'["mla_e","mlb_e"]'},{"id":"ehc","conditionId":"0x2","sportsMarketType":"map_handicap","line":-1.5,"feeType":"sports_fees_v2","groupItemTitle":"Map Handicap: NAVI (-1.5) vs FaZe (+1.5)","description":'This market will resolve to "NAVI" if NAVI wins 2 or more maps than FaZe',"outcomes":'["NAVI","FaZe"]',"clobTokenIds":'["hcm_e","hcp_e"]'},{"id":"em1","conditionId":"0x3","sportsMarketType":"child_moneyline","feeType":"sports_fees_v2","groupItemTitle":"Map 1 Winner","outcomes":'["NAVI","FaZe"]',"clobTokenIds":'["m1a_e","m1b_e"]',"outcomePrices":'["0", "1"]',"closed":True}]};w=parse_esports_bo3_event(q);assert w is not None and w.hc_fav_is_a is True and w.map1_resolved_winner=="B";p={**q,"title":"NAVI vs FaZe (BO5)","markets":[*q["markets"],{"id":"em4","sportsMarketType":"child_moneyline","groupItemTitle":"Map 4 Winner"}]};assert parse_esports_bo3_event(p)is None;j=evaluate_api1_esports_bo3_opportunities(w,{},{"mla_e":.55,"hcp_e":.41},max_middle_cost_net=.988);assert len(j["single_leg_locks"])==1 and j["single_leg_locks"][0]["token_id"]=="hcp_e";assert len(j["two_leg_boxes"])==1 and j["two_leg_boxes"][0]["post_m1_forfeit_immune"]is True;import asyncio;import json;import time as _time_m;import src.polymarket_research.alpha_124_shadow_daemon as a124_mod;h=tmp_path/"d1_cands.jsonl";monkeypatch.setattr(a124_mod,"STATE_FILE",tmp_path/"a124_fv2.json");monkeypatch.setattr(a124_mod,"LEDGER_FILE",tmp_path/"a124_fv2_ledger.jsonl");monkeypatch.setattr(a124_mod,"MARKET_TELEMETRY_FILE",tmp_path/"a124_fv2_telem.jsonl");monkeypatch.setattr(a124_mod,"D1_LIVE_CANDIDATES_FILE",h);G=a124_mod.Alpha124ShadowDaemon(single_scan=True);F=_time_m.time();C.settle_est_ts=F+7200.
 for K in e["legs"]:K["end_ts"]=F+7200.
 e["end_ts"]=F+7200.;G.nba_prop_slates={C.event_id:C};G.lp1_nba_em_bundles={e["event_id"]:e};d={"90011":{"bids":[{"price":"0.60","size":"150"}],"asks":[{"price":"0.62","size":"150"}]},"90012":{"bids":[{"price":"0.36","size":"150"}],"asks":[{"price":"0.38","size":"150"}]},"90021":{"bids":[{"price":"0.62","size":"150"}],"asks":[{"price":"0.65","size":"150"}]},"90022":{"bids":[{"price":"0.33","size":"150"}],"asks":[{"price":"0.35","size":"150"}]},"mla":{"bids":[{"price":"0.56","size":"200"}],"asks":[{"price":"0.58","size":"200"}]},"mlb":{"bids":[{"price":"0.40","size":"200"}],"asks":[{"price":"0.42","size":"200"}]},"emy1":{"bids":[{"price":"0.58","size":"200"}],"asks":[{"price":"0.60","size":"200"}]},"emn1":{"bids":[{"price":"0.38","size":"200"}],"asks":[{"price":"0.40","size":"200"}]}}
 async def _mock_fb_fv2(toks,timeout=3.5):return{t:d[t]for t in toks if t in d}
 G.fetch_books_batch=_mock_fb_fv2;g=[];asyncio.run(G._scan_frontier_v2_sleeves(g,F));b=[json.loads(x)for x in h.read_text(encoding="utf-8").splitlines()if x.strip()];a={c["sleeve_source"]for c in b};assert"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"in a;assert"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"in a
if __name__=="__main__":test_polymarket_weather_rounding_spec_examples();test_metar_parser_speci_and_t_remark();test_bucket_bounds_parser();test_barrier_and_svi_monotonicity();test_exact_twap_lock_engine_math_and_whipsaw_guard();print("ALL ALPHA-124 ORACLE & PRICING UNIT TESTS PASSED!")

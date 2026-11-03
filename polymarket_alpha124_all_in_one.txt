"""
========================================================================================
DOMINUS POLYMARKET ALPHA-124 EXPANSION + PROJECTIONS + TESTS (<1 MB AST-INVARIANT COMPANION BUNDLE)
Generated: 2026-11-03 01:05:40 UTC
Pairs with polymarket_all_in_one.txt (<1 MB) for tools enforcing a 1 MB per-file upload cap
Repository: /home/skybullet1987/quant_pipeline
========================================================================================

TABLE OF CONTENTS (Exact 1-Based Line Ranges & Raw Module Sizes):
  [01] systemd/polymarket-alpha124-shadow.service (Lines 35 - 61 | 854 B) :: Alpha-124 Unified Shadow systemd Unit
  [02] src/polymarket_research/directional_wfo_shadow_sleeves.py (Lines 62 - 475 | 71,299 B) :: v3.9.5 WFO Graduation Shadow Sleeves (SLEEVE_HYBRID_ZSPLIT_SHADOW & SLEEVE_BTC_5M_SNIPER_SHADOW)
  [03] src/polymarket_research/orderflow_wfo_simulators.py (Lines 476 - 786 | 66,622 B) :: v4.0 100ms Micro-Clip 4-Step Cascade Replay, D1 Latency-Skew WFO & Legging-Drag Parity Engine
  [04] src/polymarket_research/net_alpha_opportunity_engine.py (Lines 787 - 993 | 48,616 B) :: v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine
  [05] src/polymarket_research/weather_metar_engine.py (Lines 994 - 1,358 | 62,165 B) :: Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb
  [06] src/polymarket_research/barrier_onetouch_svi_engine.py (Lines 1,359 - 1,501 | 22,909 B) :: Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)
  [07] src/polymarket_research/multistrike_svi_scalper.py (Lines 1,502 - 1,674 | 29,320 B) :: Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner
  [08] src/polymarket_research/same_oracle_dominance_box.py (Lines 1,675 - 1,884 | 36,491 B) :: Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine
  [09] src/polymarket_research/exact_twap_lock_engine.py (Lines 1,885 - 1,947 | 13,314 B) :: Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock
  [10] src/polymarket_research/tradfi_sports_zero_fee_engine.py (Lines 1,948 - 2,451 | 72,523 B) :: Zero-Fee Pyth Commodities/Metals/Equities (CM_B3/B2/U1), B4 Wick Lock, NBA Polish-Middle (SP1) & NegRisk (NR0)
  [11] src/polymarket_research/macro_counting_ctf_engine.py (Lines 2,452 - 2,799 | 48,463 B) :: Phase-2 Multi-Vertical Structural & Oracle Engine (TW1 xtracker, FED1 125-State LP, COND1 Oil-Senate, CTF Overround, AAA Gas, D2 12PM)
  [12] src/polymarket_research/uma_nba_endgame_engine.py (Lines 2,800 - 2,998 | 32,496 B) :: Evergreen On-Chain UMA Resolution Bond Harvester (BOND1) & 0%-Fee Live NBA Final-2m/Post-Buzzer Sniper (SP2)
  [13] src/polymarket_research/riskless_frontier_v2_engine.py (Lines 2,999 - 3,429 | 81,101 B) :: Riskless Frontier v2 Engine (NR2 Subset Convert + Free Tail, SP4 NBA Props, BOND2 Whitelisted MOOv2, SOC1 3-Way Soccer, LP1 Implication Matrix, API1 BO3 Esports)
  [14] src/polymarket_research/riskless_frontier_v3_engine.py (Lines 3,430 - 4,090 | 109,769 B) :: Riskless Frontier v3 Engine (NFL Exact Margin/Spread, Subperiod Clinch, Deadline Ladder, Tennis Retirement-Safe Corridor, Multi-Sport Post-Review Clinch)
  [15] src/polymarket_research/riskless_frontier_v4_engine.py (Lines 4,091 - 4,644 | 112,083 B) :: Riskless Frontier v4 Evergreen Engine (AFF1 Subperiod Collapse, SOC2 83-State Lattice, NFL_PRP1 Locks, SUM1 Frechet Triangles, CRY_INC1 Binance Inclusion, MKR_LOCK1)
  [16] src/polymarket_research/alpha_124_shadow_daemon.py (Lines 4,645 - 7,754 | 682,684 B) :: Unified Multi-Vertical Shadow Daemon (Crypto, Weather METAR/HKO, Pyth Commodities/Metals/Equities, Sports, UMA Bonds, Frontier v2/v3/v4)
  [17] scripts/backtest_alpha_124.py (Lines 7,755 - 7,979 | 40,009 B) :: Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124
  [18] scripts/polymarket_daily_projections.py (Lines 7,980 - 8,067 | 33,530 B) :: Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker
  [19] scripts/alpha124_status.py (Lines 8,068 - 8,096 | 3,091 B) :: Live Alpha-124 Multi-Sleeve Scorecard & Orderbook Opportunity Inspector
  [20] scripts/polymarket_scorecard_snapshot.py (Lines 8,097 - 8,113 | 4,891 B) :: Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot
  [21] tests/test_alpha_124_oracles.py (Lines 8,114 - 8,375 | 215,820 B) :: Unit Tests: Weather METAR/HKO, Jump-SVI Barrier, Pyth Session/Boxes, NBA Boxes, D1, S2 & Wallet
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
 c=datetime.fromtimestamp(float(ts_unix),tz=_NY_TZ);wd=c.weekday();d=c.hour*60+c.minute
 if wd==5 or(wd==4 and d>=17*60)or(wd==6 and d<18*60+15):return True,"CME_WEEKEND_CLOSURE"
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
  px,sz=float(d[0]or.0),float(d[1]or.0)
  if px<=0 or sz<=0:continue
  c=min(b,sz);a+=c*px;b-=c
  if b<=1e-6:break
 if b>1e-6:a+=b*max(.01,fallback_bid-.02)
 return round(a/target_shares,4)
def _bootstrap_prob_positive(pnls,n_boot=1000):
 n=len(pnls)
 if n<3:s=round(sum(pnls),2);return(1. if s>0 else.0),[s,s]
 rng=random.Random(20261030);totals=[]
 for _ in range(n_boot):totals.append(sum(pnls[rng.randrange(n)]for _ in range(n)))
 totals.sort();lo=round(totals[int(.025*n_boot)],2);hi=round(totals[int(.975*n_boot)],2);a=round(sum(1 for x in totals if x>0)/n_boot,4);return a,[lo,hi]
class DirectionalWfoShadowManager:
 def __init__(self,data_dir,latency_sec=TRANSIT_LATENCY_SEC,production_mode=False):self.data_dir=Path(data_dir);self.data_dir.mkdir(parents=True,exist_ok=True);self.latency_sec=max(.0,float(latency_sec));self.production_mode=bool(production_mode);self.hz_ledger_file=self.data_dir/"ledger_shadow_hybrid_zsplit.jsonl";self.hz_state_file=self.data_dir/"state_shadow_hybrid_zsplit.json";self.hz_trades=[];self.hz_settled_ids=set();self.hz_settled_markets=set();self.hz_open={};self.hz_pending={};self.hz_funnel={"signals_seen":0,"signals_evaluated":0,"maker_branch_queued":0,"taker_branch_queued":0,"maker_filled":0,"taker_fak_filled":0,"phase3a_rescue_filled":0,"shield_canceled":0,"complement_shield_canceled":0,"queue_depth_rejected":0,"ttl_expired_unfilled":0,"post_only_or_collapse_rejected":0};self.b5_ledger_file=self.data_dir/"ledger_shadow_btc_5m.jsonl";self.b5_state_file=self.data_dir/"state_shadow_btc_5m.json";self.b5_telem_file=self.data_dir/"polymarket_5m_telemetry_btc.jsonl";self.b5_trades=[];self.b5_settled_ids=set();self.b5_settled_markets=set();self.b5_open={};self.b5_pending={};self.b5_funnel={"ticks_scanned":0,"candidates_queued":0,"taker_filled":0,"transit_swept_or_shielded":0};self.s5_ledger_file=self.data_dir/"ledger_shadow_sol_5m.jsonl";self.s5_state_file=self.data_dir/"state_shadow_sol_5m.json";self.s5_telem_file=self.data_dir/"polymarket_5m_telemetry_sol.jsonl";self.s5_trades=[];self.s5_settled_ids=set();self.s5_settled_markets=set();self.s5_open={};self.s5_pending={};self.s5_funnel={"ticks_scanned":0,"candidates_queued":0,"taker_filled":0,"transit_swept_or_shielded":0};self.xau_ledger_file=self.data_dir/"ledger_shadow_xau_15m.jsonl";self.xau_state_file=self.data_dir/"state_shadow_xau_15m.json";self.xau_telem_file=self.data_dir/"polymarket_15m_telemetry_xau.jsonl";self.xau_trades=[];self.xau_settled_ids=set();self.xau_settled_markets=set();self.xau_open={};self.xau_pending={};self.xau_funnel={"ticks_scanned":0,"cme_or_session_blocked":0,"basis_or_anchor_rejected":0,"maker_queued":0,"maker_filled":0,"shield_or_comp_canceled":0,"queue_depth_rejected":0,"ttl_expired_unfilled":0};self.b5_file_pos=self.b5_telem_file.stat().st_size if self.b5_telem_file.exists()else 0;self.s5_file_pos=self.s5_telem_file.stat().st_size if self.s5_telem_file.exists()else 0;self.xau_file_pos=self.xau_telem_file.stat().st_size if self.xau_telem_file.exists()else 0;self.t15_btc_file=self.data_dir/"polymarket_15m_telemetry_btc.jsonl";self.t15_eth_file=self.data_dir/"polymarket_15m_telemetry_eth.jsonl";self.t1h_btc_file=self.data_dir/"polymarket_hourly_telemetry.jsonl";self.t1h_eth_file=self.data_dir/"polymarket_hourly_telemetry_eth.jsonl";self.t15_btc_pos=self.t15_btc_file.stat().st_size if self.t15_btc_file.exists()else 0;self.t15_eth_pos=self.t15_eth_file.stat().st_size if self.t15_eth_file.exists()else 0;self.t1h_btc_pos=self.t1h_btc_file.stat().st_size if self.t1h_btc_file.exists()else 0;self.t1h_eth_pos=self.t1h_eth_file.stat().st_size if self.t1h_eth_file.exists()else 0;self._btc_sigma_1h=.0048;self._btc_last_1m_bkt=0;self._btc_last_1m_spot=.0;self._sol_sigma_1h=.009;self._sol_last_1m_bkt=0;self._sol_last_1m_spot=.0;self._xau_sigma_1h=.0022;self._xau_last_1m_bkt=0;self._xau_last_1m_spot=.0;self._last_state_flush_ts=.0;self._load_ledgers();self.save_states()
 def _load_ledgers(self):
  for l,c,h,g in((self.hz_ledger_file,self.hz_trades,self.hz_settled_ids,self.hz_settled_markets),(self.b5_ledger_file,self.b5_trades,self.b5_settled_ids,self.b5_settled_markets),(self.s5_ledger_file,self.s5_trades,self.s5_settled_ids,self.s5_settled_markets),(self.xau_ledger_file,self.xau_trades,self.xau_settled_ids,self.xau_settled_markets)):
   if not l.exists():continue
   try:
    with open(l,"r",encoding="utf-8",errors="ignore")as f:
     for ln in f:
      if not ln.strip():continue
      p=json.loads(ln);o=str(p.get("trade_id")or"");n=str(p.get("market_id")or"")
      if o and o not in h:
       h.add(o);c.append(p)
       if n:g.add(n)
   except Exception:pass
  for e,b,d,a in((self.hz_state_file,self.hz_funnel,self.hz_open,self.hz_settled_ids),(self.b5_state_file,self.b5_funnel,self.b5_open,self.b5_settled_ids),(self.s5_state_file,self.s5_funnel,self.s5_open,self.s5_settled_ids),(self.xau_state_file,self.xau_funnel,self.xau_open,self.xau_settled_ids)):
   if e.exists():
    try:
     i=json.loads(e.read_text(encoding="utf-8"))
     for k,v in(i.get("funnel_counters")or{}).items():
      if k in b and isinstance(v,int):b[k]=max(b[k],v)
     for j,m in(i.get("open_positions")or{}).items():
      if isinstance(m,dict)and m.get("status")=="OPEN"and m.get("trade_id")not in a:d[str(j)]=m
    except Exception:pass
 def _read_shm_asset(self,asset):
  a=os.environ.get("PM_FAST_TICK_DIR","/dev/shm")
  if not a:return None
  p=Path(a)/f"pm_fast_tick_{asset.upper()}.json"
  if not p.exists():return None
  try:
   d=json.loads(p.read_text(encoding="utf-8"));ts=float(d.get("timestamp_unix")or d.get("ts")or.0)
   if ts>0 and(time.time()-ts)<=5.:return d
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
 def on_shock_signal(self,shock,historical=False):
  if historical:return False
  K=str(shock.get("market_id")or"")
  if not K or K in self.hz_open or K in self.hz_pending or K in self.hz_settled_markets:return False
  if len(self.hz_open)+len(self.hz_pending)>=2:return False
  H=str(shock.get("title")or"");w=H.lower();c=str(shock.get("asset")or"").upper()
  if not c:c="BTC"if("bitcoin"in w or"btc"in w)else("ETH"if("ethereum"in w or"eth"in w)else"")
  if c not in("BTC","ETH"):return False
  E=str(shock.get("horizon")or shock.get("candle_interval")or"").lower();J=str(shock.get("series_slug")or shock.get("slug")or"").lower();m=f"{E} {J} {w}"
  if re.search(r"(?<![0-9])5m(?![0-9a-z])|(?<![0-9])300s(?![0-9a-z])",m):return False
  a=False;D=re.search(r"(\d{1,2}):(\d{2})\s*(?:am|pm)?\s*-\s*(\d{1,2}):(\d{2})\s*(?:am|pm)",w)
  if D:
   O,N=int(D.group(2)),int(D.group(4));v=(N-O)%60
   if v==15:a=True
   elif v==5:return False
  C=bool(re.search(r"(?<![0-9])15m(?![0-9a-z])|(?<![0-9])900s(?![0-9a-z])",m))or a;G=not C and(bool(re.search(r"(?<![0-9])(?:1h|60m)(?![0-9a-z])|hourly",m))or("am et"in w or"pm et"in w))
  if not(C or G):return False
  hz="15m"if C else"1h";self.hz_funnel["signals_seen"]=int(self.hz_funnel.get("signals_seen",0))+1;u=float(shock.get("t0_unix")or time.time())
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   dt=datetime.fromtimestamp(u,tz=timezone.utc)
   if dt.hour==13 and dt.minute>=30:return False
  M=float(shock.get("seconds_to_expiry")or.0)
  if hz=="15m"and not((180.<=M<=390.)if self.production_mode else(90.<=M<=480.)):return False
  if hz=="1h"and not((150.<=M<=2400.)if self.production_mode else(150.<=M<=6e2)):return False
  h=str(shock.get("shock_direction")or"").upper()
  if h not in("BUY","SELL"):return False
  I="UP"if h=="BUY"else"DOWN";t,_=evaluate_coinbase_venue_veto(shock,I)
  if t:return False
  g=abs(float(shock.get("shock_ofi")if shock.get("shock_ofi")is not None else 1.))
  if g<.6:return False
  s=float(shock.get("spot_at_t0")or shock.get("trigger_price")or.0);r=float(shock.get("candle_open_spot")or shock.get("finalized_1h_open")or.0);f=float(shock.get("twap_60s_open")or.0);q=float(shock.get("chainlink_proxy_usd_spot")or.0);p=float(shock.get("authoritative_chainlink_open")or.0);o=self._compute_signed_cushion(I,hz,s,r,f,q,p)
  if o is None or o<4e-4:return False
  n=float(shock.get("candle_sigma")or.0);l=(n*2. if C else n)if n>.0 else(.005 if c=="BTC"else.0068);e=max(.00025,l*math.sqrt(max(M,30.)/3600.));k=o/e
  if k<.78:return False
  L=(shock.get("pre_shock_features_t0")or{}).get(I)or{};j=L.get("raw_top_asks")or[];i=L.get("raw_top_bids")or[];B=float(L.get("best_ask")or(j[0][0]if j else 1.));A=float(L.get("best_bid")or(i[0][0]if i else.0));z=float(L.get("ask_size_l1")or(j[0][1]if j else.0));d=round(B-A,4)if A>0 else.99;y=B*z;b=(.72 if C else.76)if self.production_mode else.82
  if not(.55<=B<=b)or A<=.0 or d>.03 or y<20.:return False
  self.hz_funnel["signals_evaluated"]+=1;x="TAKER_PLUS_P3A"if k>=Z_TAKER_CUT else"SHIELDED_MAKER_FIRST"
  if x=="SHIELDED_MAKER_FIRST":self.hz_funnel["maker_branch_queued"]+=1
  else:self.hz_funnel["taker_branch_queued"]+=1
  F=time.time();self.hz_pending[K]={"sleeve":"SLEEVE_HYBRID_ZSPLIT_SHADOW","trade_id":f"HZSHDW_{K}_{int(u)}_{I}","market_id":K,"title":H,"asset":c,"horizon":hz,"target_token":I,"t0_unix":u,"queued_mono":F,"arrival_mono":F+self.latency_sec,"expiry_unix":float(shock.get("candle_expiry_ts")or shock.get("expiry_ts")or(u+M)),"tte_t0":M,"ask_t0":B,"bid_t0":A,"l1_usd_t0":round(y,2),"cush_t0":o,"z_strike":round(k,4),"open_usdt":r,"twap_open_usdt":f,"auth_cl_open_usd":p,"branch":x,"phase":"IN_TRANSIT","maker_px":None,"deadline_mono":None};return True
 def _ingest_btc_5m_telemetry_tick(self,d):
  l=str(d.get("asset")or"").upper();hz=str(d.get("horizon")or"").lower()
  if l!="BTC"or hz!="5m":return
  self.b5_funnel["ticks_scanned"]+=1;ts=float(d.get("timestamp_unix")or time.time());sp=float(d.get("binance_spot")or.0)
  if sp>0:
   b1=int(ts//60)
   if b1>self._btc_last_1m_bkt:
    if self._btc_last_1m_spot>0:r1=math.log(sp/self._btc_last_1m_spot);self._btc_sigma_1h=max(.002,min(.02,math.sqrt(.94*(self._btc_sigma_1h**2)+.06*(60.*r1*r1))))
    self._btc_last_1m_spot=sp;self._btc_last_1m_bkt=b1
  n=str(d.get("market_id")or"")
  if not n:return
  if n in self.b5_open:self._check_open_position_exit(self.b5_open,n,d,is_btc_5m=True);return
  if n in self.b5_pending or n in self.b5_settled_markets:return
  if len(self.b5_open)+len(self.b5_pending)>=2:return
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   dt=datetime.fromtimestamp(ts,tz=timezone.utc)
   if dt.hour==13 and dt.minute>=30:return
  r=float(d.get("seconds_to_expiry")or.0)
  if not(60.<=r<=180.):return
  i=float(d.get("binance_open")or.0);h=float(d.get("twap_60s_open")or.0);k=float(d.get("chainlink_proxy_usd_spot")or.0);e=float(d.get("authoritative_chainlink_open")or.0)
  if sp<=0 or i<=0:return
  a=max(.00025,self._btc_sigma_1h*math.sqrt(max(r,15.)/3600.))
  for m in("UP","DOWN"):
   bk=d.get(m)or{};q=float(bk.get("best_bid")or.0);p=float(bk.get("best_ask")or 1.);o=float(bk.get("ask_size_l1")or.0)
   if bk.get("is_crossed")or q<=.0 or p>=.99 or q>=p:continue
   g=round(p-q,4);f=p*o
   if not(.55<=p<=.85)or g>.03 or f<15.:continue
   c=self._compute_signed_cushion(m,"5m",sp,i,h,k,e)
   if c is None or c<3e-4:continue
   b=c/a
   if b<.8:continue
   j=time.time();self.b5_funnel["candidates_queued"]+=1;self.b5_pending[n]={"sleeve":"SLEEVE_BTC_5M_SNIPER_SHADOW","trade_id":f"BTC5M_{n}_{int(ts)}_{m}","market_id":n,"title":str(d.get("title")or f"BTC 5m {n}"),"asset":"BTC","horizon":"5m","target_token":m,"t0_unix":ts,"queued_mono":j,"arrival_mono":j+self.latency_sec,"expiry_unix":ts+r,"tte_t0":r,"ask_t0":p,"bid_t0":q,"l1_usd_t0":round(f,2),"cush_t0":c,"z_strike":round(b,4),"open_usdt":i,"twap_open_usdt":h,"auth_cl_open_usd":e,"latest_tick":d};break
 def _ingest_sol_5m_telemetry_tick(self,d):
  n=str(d.get("asset")or"").upper();hz=str(d.get("horizon")or"").lower()
  if n!="SOL"or hz!="5m":return
  self.s5_funnel["ticks_scanned"]+=1;ts=float(d.get("timestamp_unix")or time.time());sp=float(d.get("binance_spot")or.0)
  if sp>0:
   b1=int(ts//60)
   if b1>self._sol_last_1m_bkt:
    if self._sol_last_1m_spot>0:r1=math.log(sp/self._sol_last_1m_spot);self._sol_sigma_1h=max(.004,min(.03,math.sqrt(.94*(self._sol_sigma_1h**2)+.06*(60.*r1*r1))))
    self._sol_last_1m_spot=sp;self._sol_last_1m_bkt=b1
  p=str(d.get("market_id")or"")
  if not p:return
  if p in self.s5_open:self._check_open_position_exit(self.s5_open,p,d,sleeve_tag="s5");return
  if p in self.s5_pending or p in self.s5_settled_markets:return
  if len(self.s5_open)+len(self.s5_pending)>=2:return
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   dt=datetime.fromtimestamp(ts,tz=timezone.utc)
   if dt.hour==13 and dt.minute>=30:return
  t=float(d.get("seconds_to_expiry")or.0)
  if not(60.<=t<=180.):return
  k=float(d.get("binance_open")or.0);j=float(d.get("twap_60s_open")or.0);m=float(d.get("chainlink_proxy_usd_spot")or.0);f=float(d.get("authoritative_chainlink_open")or.0)
  if sp<=0 or k<=0:return
  a=float(d.get("candle_sigma")or.0);i=(a*math.sqrt(12.))if a>.0 else self._sol_sigma_1h;b=max(.00035,i*math.sqrt(max(t,15.)/3600.))
  for o in("UP","DOWN"):
   bk=d.get(o)or{};s=float(bk.get("best_bid")or.0);r=float(bk.get("best_ask")or 1.);q=float(bk.get("ask_size_l1")or.0)
   if bk.get("is_crossed")or s<=.0 or r>=.99 or s>=r:continue
   h=round(r-s,4);g=r*q
   if not(.55<=r<=.85)or h>.03 or g<15.:continue
   e=self._compute_signed_cushion(o,"5m",sp,k,j,m,f)
   if e is None or e<4e-4:continue
   c=e/b
   if c<.8:continue
   l=time.time();self.s5_funnel["candidates_queued"]+=1;self.s5_pending[p]={"sleeve":"SLEEVE_SOL_5M_CANARY_SHADOW","trade_id":f"SOL5M_{p}_{int(ts)}_{o}","market_id":p,"title":str(d.get("title")or f"SOL 5m {p}"),"asset":"SOL","horizon":"5m","target_token":o,"t0_unix":ts,"queued_mono":l,"arrival_mono":l+self.latency_sec,"expiry_unix":ts+t,"tte_t0":t,"ask_t0":r,"bid_t0":s,"l1_usd_t0":round(g,2),"cush_t0":e,"z_strike":round(c,4),"open_usdt":k,"twap_open_usdt":j,"auth_cl_open_usd":f,"latest_tick":d};break
 def ingest_xau_15m_tick(self,d):
  r=str(d.get("asset")or"").upper();hz=str(d.get("horizon")or"").lower()
  if r not in("XAU","GOLD")or hz!="15m":return False
  self.xau_funnel["ticks_scanned"]+=1;ts=float(d.get("timestamp_unix")or time.time());i,_=is_xau_cme_blackout_or_inactive_session(ts)
  if i:self.xau_funnel["cme_or_session_blocked"]+=1;return False
  n=compute_synthetic_xau_usd_anchor(binance_xau_usdt=float(d.get("binance_xau_usdt")or d.get("binance_spot")or.0),coinbase_usdt_usd=float(d.get("coinbase_usdt_usd")or.0),swissquote_bid=float(d.get("swissquote_bid")or.0),swissquote_ask=float(d.get("swissquote_ask")or.0),max_basis_bps=2.5)
  if not n["valid"]:self.xau_funnel["basis_or_anchor_rejected"]+=1;return False
  h=float(n["xau_usd"]);b1=int(ts//60)
  if b1>self._xau_last_1m_bkt:
   if self._xau_last_1m_spot>0:r1=math.log(h/self._xau_last_1m_spot);self._xau_sigma_1h=max(.001,min(.012,math.sqrt(.94*(self._xau_sigma_1h**2)+.06*(60.*r1*r1))))
   self._xau_last_1m_spot=h;self._xau_last_1m_bkt=b1
  v=str(d.get("market_id")or"")
  if not v:return False
  if v in self.xau_open:q=dict(d,chainlink_proxy_usd_spot=h);self._check_open_position_exit(self.xau_open,v,q,sleeve_tag="xau");return False
  if v in self.xau_pending or v in self.xau_settled_markets:return False
  if len(self.xau_open)+len(self.xau_pending)>=1:return False
  A=float(d.get("seconds_to_expiry")or.0)
  if not(90.<=A<=480.):return False
  p=d.get("authoritative_chainlink_open")or d.get("strike_usd")
  if p is None or float(p)<=.0:self.xau_funnel["basis_or_anchor_rejected"]+=1;return False
  a=round(float(p),3);g=float(d.get("candle_sigma")or.0);m=(g*2.)if g>.0 else self._xau_sigma_1h;b=max(.00018,m*math.sqrt(A/3600.))
  for u in("UP","DOWN"):
   bk=d.get(u)or{};l=d.get("DOWN"if u=="UP"else"UP")or{};z=float(bk.get("best_bid")or.0);y=float(bk.get("best_ask")or 1.);x=float(bk.get("ask_size_l1")or.0);w=float(bk.get("bid_size_l1")or.0);f=float(l.get("best_bid")or.0)
   if bk.get("is_crossed")or z<=.0 or y>=.99 or z>=y:continue
   k=round(y-z,4);j=y*x
   if not(.56<=y<=.83)or k>.02 or j<50.:continue
   t=1. if u=="UP"else-1.;s=t*(h-a)/a
   if s<.00025:continue
   e=s/b
   if e<.85:continue
   c=round(min(.82,y-.01,z+(.01 if k>=.02 else.0)),2)
   if c<.55 or c>=y-1e-6:continue
   if c<=z+1e-6 and(z*w)>MAX_MAKER_JOIN_QUEUE_USD:self.xau_funnel["queue_depth_rejected"]+=1;continue
   if f>.0 and round(1.-f,4)<=c+1e-6:self.xau_funnel["shield_or_comp_canceled"]+=1;continue
   o=time.time();self.xau_funnel["maker_queued"]+=1;self.xau_pending[v]={"sleeve":"SLEEVE_XAU_15M_MAKER_SHADOW","trade_id":f"XAU15M_{v}_{int(ts)}_{u}","market_id":v,"title":str(d.get("title")or f"XAU/USD 15m {v}"),"asset":"XAU","horizon":"15m","target_token":u,"t0_unix":ts,"queued_mono":o,"arrival_mono":o+self.latency_sec,"expiry_unix":ts+A,"tte_t0":A,"ask_t0":y,"bid_t0":z,"maker_px":c,"deadline_mono":o+self.latency_sec+MAKER_TTL_SEC,"l1_usd_t0":round(j,2),"cush_t0":s,"z_strike":round(e,4),"open_usdt":.0,"twap_open_usdt":.0,"auth_cl_open_usd":a,"latest_tick":d};return True
  return False
 def _step_hz_pending(self,now_u):
  for u,p in list(self.hz_pending.items()):
   if now_u<p["arrival_mono"]:continue
   t=self._extract_market_view(p["asset"],u,p["horizon"])
   if t is None:
    if now_u>p["arrival_mono"]+MAKER_TTL_SEC+2.:self.hz_pending.pop(u,None)
    continue
   s=p["target_token"];j="DOWN"if s=="UP"else"UP";bk=t.get(s)or{};r=t.get(j)or{};i=bk.get("raw_top_asks")or[];h=bk.get("raw_top_bids")or[];o=float(bk.get("best_ask")or(i[0][0]if i else 1.));n=float(bk.get("best_bid")or(h[0][0]if h else.0));m=float(bk.get("ask_size_l1")or(i[0][1]if i else.0));l=float(bk.get("bid_size_l1")or(h[0][1]if h else.0));k=float(r.get("best_bid")or.0);q=o*m;g=self._compute_signed_cushion(s,p["horizon"],float(t.get("binance_spot")or.0),p["open_usdt"],p["twap_open_usdt"],float(t.get("chainlink_proxy_usd_spot")or.0),p["auth_cl_open_usd"])
   if g is not None and(g<=.0 or g<p["cush_t0"]*(1.-SHIELD_DECAY_FRAC)):self.hz_funnel["shield_canceled"]+=1;self.hz_pending.pop(u,None);continue
   if p["phase"]=="IN_TRANSIT":
    if(p["ask_t0"]-o)>=.04:self.hz_funnel["post_only_or_collapse_rejected"]+=1;self.hz_pending.pop(u,None);continue
    if p["branch"]=="TAKER_PLUS_P3A":
     f=min(.81,round(p["ask_t0"]+.02,4))
     if.0<o<=f and q>=SHADOW_ELASTIC_USD:e=SHADOW_TICKET_USD if q>=SHADOW_TICKET_USD else SHADOW_ELASTIC_USD;a="STEP1_SMART_FAK"if e>=SHADOW_TICKET_USD else"STEP2_ELASTIC_DOWNSNAP";self.hz_funnel["taker_fak_filled"]+=1;self._open_shadow_position(self.hz_open,p,o,e,is_maker=False,step_tag=a,entry_ts=float(t.get("timestamp_unix")or now_u));self.hz_pending.pop(u,None);continue
     p["branch_step_tag"]="STEP4_PHASE3A_MAKER_RESCUE"
    else:p["branch_step_tag"]="SHIELDED_MAKER_FIRST"
    d=n if n>.0 else max(.01,o-.02);b=round(min(.82,o-.01,max(d,p["ask_t0"]-.01)),2)
    if b<.55 or b>=o-1e-6:self.hz_funnel["post_only_or_collapse_rejected"]+=1;self.hz_pending.pop(u,None);continue
    if b<=n+1e-6 and(n*l)>MAX_MAKER_JOIN_QUEUE_USD:self.hz_funnel["queue_depth_rejected"]+=1;self.hz_pending.pop(u,None);continue
    if k>.0 and round(1.-k,4)<=b+1e-6:self.hz_funnel["complement_shield_canceled"]+=1;self.hz_pending.pop(u,None);continue
    p["phase"]="RESTING_MAKER";p["maker_px"]=b;p["deadline_mono"]=now_u+MAKER_TTL_SEC;continue
   b=float(p["maker_px"])
   if k>.0:
    c=round(1.-k,4)
    if c<=b-1e-6 or(o>b+1e-6 and c<=b+1e-6):self.hz_funnel["complement_shield_canceled"]+=1;self.hz_pending.pop(u,None);continue
   if.0<o<=b:
    a=str(p.get("branch_step_tag")or"SHIELDED_MAKER_FIRST")
    if a=="STEP4_PHASE3A_MAKER_RESCUE":self.hz_funnel["phase3a_rescue_filled"]+=1
    else:self.hz_funnel["maker_filled"]+=1
    self._open_shadow_position(self.hz_open,p,b,SHADOW_TICKET_USD,is_maker=True,step_tag=a,entry_ts=float(t.get("timestamp_unix")or now_u));self.hz_pending.pop(u,None)
   elif now_u>=float(p["deadline_mono"]or.0):self.hz_funnel["ttl_expired_unfilled"]+=1;self.hz_pending.pop(u,None)
 def _step_b5_pending(self,now_u):self._step_5m_sniper_pending("BTC",self.b5_pending,self.b5_open,self.b5_funnel,"BTC5M_TAKER_FAK",now_u)
 def _step_s5_pending(self,now_u):self._step_5m_sniper_pending("SOL",self.s5_pending,self.s5_open,self.s5_funnel,"SOL5M_TAKER_FAK",now_u)
 def _step_5m_sniper_pending(self,asset_sym,pending_map,open_map,funnel_map,step_tag,now_u):
  for i,p in list(pending_map.items()):
   if now_u<p["arrival_mono"]:continue
   d=self._extract_market_view(asset_sym,i,"5m")
   if d is None:
    lt=p.get("latest_tick")or{}
    if float(lt.get("timestamp_unix")or.0)>=p["t0_unix"]+.35:d=lt
    elif now_u>p["arrival_mono"]+2.5:funnel_map["transit_swept_or_shielded"]+=1;pending_map.pop(i,None);continue
    else:continue
   h=p["target_token"];bk=d.get(h)or{};c=bk.get("raw_top_asks")or[];f=float(bk.get("best_ask")or(c[0][0]if c else 1.));e=float(bk.get("ask_size_l1")or(c[0][1]if c else.0));g=f*e;b=self._compute_signed_cushion(h,"5m",float(d.get("binance_spot")or.0),p["open_usdt"],p["twap_open_usdt"],float(d.get("chainlink_proxy_usd_spot")or.0),p["auth_cl_open_usd"]);a=min(.85,round(p["ask_t0"]+.02,4))
   if(b is not None and b>.0 and.0<f<=a and(p["ask_t0"]-f)<.04 and g>=SHADOW_ELASTIC_USD):funnel_map["taker_filled"]+=1;self._open_shadow_position(open_map,p,f,SHADOW_TICKET_USD,is_maker=False,step_tag=step_tag,entry_ts=float(d.get("timestamp_unix")or now_u))
   else:funnel_map["transit_swept_or_shielded"]+=1
   pending_map.pop(i,None)
 def _step_xau_pending(self,now_u):
  for l,p in list(self.xau_pending.items()):
   if now_u<p["arrival_mono"]:continue
   d=self._extract_market_view("XAU",l,"15m")
   if d is None:
    lt=p.get("latest_tick")or{}
    if float(lt.get("timestamp_unix")or.0)>=p["t0_unix"]+.1:d=lt
    elif now_u>float(p.get("deadline_mono")or(p["arrival_mono"]+MAKER_TTL_SEC)):self.xau_funnel["ttl_expired_unfilled"]+=1;self.xau_pending.pop(l,None);continue
    else:continue
   i=compute_synthetic_xau_usd_anchor(binance_xau_usdt=float(d.get("binance_xau_usdt")or d.get("binance_spot")or.0),coinbase_usdt_usd=float(d.get("coinbase_usdt_usd")or.0),swissquote_bid=float(d.get("swissquote_bid")or.0),swissquote_ask=float(d.get("swissquote_ask")or.0),max_basis_bps=2.5)
   if not i["valid"]:self.xau_funnel["shield_or_comp_canceled"]+=1;self.xau_pending.pop(l,None);continue
   g=float(i["xau_usd"]);k=p["target_token"];j=1. if k=="UP"else-1.;c=j*(g-float(p["auth_cl_open_usd"]))/float(p["auth_cl_open_usd"])
   if c<=.0 or c<p["cush_t0"]*(1.-SHIELD_DECAY_FRAC):self.xau_funnel["shield_or_comp_canceled"]+=1;self.xau_pending.pop(l,None);continue
   bk=d.get(k)or{};h=d.get("DOWN"if k=="UP"else"UP")or{};f=float(bk.get("best_ask")or 1.);e=float(h.get("best_bid")or.0);b=float(p["maker_px"])
   if e>.0:
    a=round(1.-e,4)
    if a<=b-1e-6 or(f>b+1e-6 and a<=b+1e-6):self.xau_funnel["shield_or_comp_canceled"]+=1;self.xau_pending.pop(l,None);continue
   if.0<f<=b:self.xau_funnel["maker_filled"]+=1;self._open_shadow_position(self.xau_open,p,b,XAU_TICKET_USD,is_maker=True,step_tag="XAU_SHIELDED_MAKER_FIRST",entry_ts=float(d.get("timestamp_unix")or now_u));self.xau_pending.pop(l,None)
   elif now_u>=float(p.get("deadline_mono")or.0):self.xau_funnel["ttl_expired_unfilled"]+=1;self.xau_pending.pop(l,None)
 def _open_shadow_position(self,open_map,p,fill_px,notional_usd,is_maker,step_tag,entry_ts=None):
  d=round(notional_usd/fill_px,4);c=str(p.get("asset")or"").upper()in("XAU","GOLD","XAG")
  if is_maker:b=.0;a=.0 if c else _maker_rebate_20pct_usd(d,fill_px)
  else:_,b=calculate_taker_fee(notional_usd,fill_px,fee_rate=.07,fee_exponent=1.);a=.0
  e=float(entry_ts)if entry_ts is not None else time.time();open_map[p["market_id"]]={"sleeve":p["sleeve"],"trade_id":p["trade_id"],"market_id":p["market_id"],"title":p["title"],"asset":p["asset"],"horizon":p["horizon"],"target_token":p["target_token"],"branch":p.get("branch",step_tag),"entry_step":step_tag,"is_maker_entry":is_maker,"entry_time":_utc_now_str(),"entry_unix":e,"t0_unix":p["t0_unix"],"expiry_unix":p["expiry_unix"],"tte_at_t0":round(p["tte_t0"],1),"z_strike":p["z_strike"],"cush_t0_pct":round(p["cush_t0"]*1e2,4),"open_usdt":p["open_usdt"],"twap_open_usdt":p["twap_open_usdt"],"auth_cl_open_usd":p["auth_cl_open_usd"],"entry_price":round(fill_px,4),"shares_bought":d,"notional_usd":round(notional_usd,2),"taker_fee_usd":round(b,4),"maker_rebate_20pct_est_usd":a,"take_profit_maker_limit_px":.98,"status":"OPEN"};self.save_states()
 def _check_open_position_exit(self,open_map,m_id,view,is_btc_5m=False,sleeve_tag=None):
  A=open_map.get(m_id)
  if not A or A.get("status")!="OPEN":return
  q=sleeve_tag or("b5"if is_btc_5m else"hz");x=float(view.get("timestamp_unix")or time.time());p=x-float(A.get("entry_unix")or.0);o=float(view.get("seconds_to_expiry")or max(.0,float(A["expiry_unix"])-x));z=A["target_token"];bk=view.get(z)or{};n=bk.get("raw_top_bids")or[];m=bk.get("raw_top_asks")or[];w=float(bk.get("best_bid")or(n[0][0]if n else.0));v=float(bk.get("best_ask")or(m[0][0]if m else 1.));i=(not bk.get("is_crossed"))and((.01<=w<v<=.999)or(w>=.98 and v>w));y=float(A.get("take_profit_maker_limit_px")or.98);h=str(A.get("asset")or"").upper()in("XAU","GOLD","XAG")
  if p>=4. and o>=15. and i and w>=y and(w>=y+.01 or v>y):d=round(A["shares_bought"]*y,4);l=.0 if h else _maker_rebate_20pct_usd(A["shares_bought"],y);self._finalize_closed_trade(pos=A,exit_px=y,payout_usd=d,exit_fee_usd=.0,exit_rebate_est_usd=l,exit_reason="MAKER_TP_98_FILLED",sleeve_tag=q);open_map.pop(m_id,None);return
  if o>=25. and w>=.12:
   if not h and.0<o<60. and A.get("horizon")in("15m","5m"):
    g=float(view.get("chainlink_proxy_usd_spot")or view.get("binance_spot")or.0);u=float(A.get("auth_cl_open_usd")or A.get("open_usdt")or.0);t=(self._sol_sigma_1h if A.get("asset")=="SOL"else(self._btc_sigma_1h if A.get("asset")=="BTC"else.0068));s,_=should_suppress_final60s_twap_salvage(side=z,strike_open=u,current_spot=g,twap_locked_mean=view.get("twap_locked_mean"),tte_sec=o,sigma_1h=t,twap_locked_weight=view.get("twap_locked_weight"))
    if s:A.pop("wrong_side_start_ts",None);return
   k=self._compute_signed_cushion(z,A["horizon"],float(view.get("binance_spot")or.0),A["open_usdt"],A["twap_open_usdt"],float(view.get("chainlink_proxy_usd_spot")or.0),A["auth_cl_open_usd"])
   if k is not None:
    if k>=.0:A.pop("wrong_side_start_ts",None)
    else:
     if o>9e2:c,a,b=.0014,.0011,22.
     elif o>180.:c,a,b=.0011,9e-4,18.
     else:c,a,b=9e-4,.00075,10.
     f=-k;j=A.get("wrong_side_start_ts")
     if j is None:
      if f>=c:A["wrong_side_start_ts"]=x
     elif f>=a:
      if(x-float(j))>=b:e=min(w,_walk_bids_vwap(n,A["shares_bought"],w));e=max(.01,e);d=round(A["shares_bought"]*e,4);r=.0 if h else calculate_taker_fee(d,e,fee_rate=.07,fee_exponent=1.)[1];self._finalize_closed_trade(pos=A,exit_px=e,payout_usd=d,exit_fee_usd=r,exit_rebate_est_usd=.0,exit_reason="SALVAGE_SPOT_ONLY_3ZONE",sleeve_tag=q);open_map.pop(m_id,None)
     else:A.pop("wrong_side_start_ts",None)
 def on_telemetry_tick(self,m_id,telem):
  if m_id in self.hz_open:self._check_open_position_exit(self.hz_open,m_id,telem,sleeve_tag="hz")
  if m_id in self.b5_open:self._check_open_position_exit(self.b5_open,m_id,telem,sleeve_tag="b5")
  if m_id in self.s5_open:self._check_open_position_exit(self.s5_open,m_id,telem,sleeve_tag="s5")
  if m_id in self.xau_open:self._check_open_position_exit(self.xau_open,m_id,telem,sleeve_tag="xau")
 def on_market_resolution(self,m_id,resolution):
  c=str(resolution.get("gamma_winning_outcome")or resolution.get("winning_outcome")or resolution.get("winner")or"").upper()
  if c not in("UP","DOWN"):return
  d=str(m_id)
  for a,g in((self.hz_open,"hz"),(self.b5_open,"b5"),(self.s5_open,"s5"),(self.xau_open,"xau")):
   f=a.pop(d,None)
   if not f or f.get("status")!="OPEN":continue
   e=(f["target_token"]==c);b=round(f["shares_bought"]*1.,4)if e else.0;f["oracle_mismatch"]=bool(resolution.get("oracle_mismatch",False));f["winning_outcome"]=c;self._finalize_closed_trade(pos=f,exit_px=1. if e else.0,payout_usd=b,exit_fee_usd=.0,exit_rebate_est_usd=.0,exit_reason="RESOLVED_WIN"if e else"RESOLVED_LOSS_WIPEOUT",sleeve_tag=g)
 def _finalize_closed_trade(self,pos,exit_px,payout_usd,exit_fee_usd,exit_rebate_est_usd,exit_reason,is_btc_5m=False,sleeve_tag=None):
  h=sleeve_tag or("b5"if is_btc_5m else"hz");g=round(payout_usd-pos["notional_usd"]-pos["taker_fee_usd"]-exit_fee_usd,2);e=round(float(pos.get("maker_rebate_20pct_est_usd")or.0)+exit_rebate_est_usd,4);pos.update({"status":"CLOSED","exit_reason":exit_reason,"exit_price":round(exit_px,4),"exit_fee_usd":round(exit_fee_usd,4),"payout_usd":round(payout_usd,2),"net_pnl_usd":g,"net_pnl_with_20pct_rebate_usd":round(g+e,2),"won":bool(g>0),"settle_time":_utc_now_str()});d={"hz":(self.hz_settled_ids,self.hz_settled_markets,self.hz_trades,self.hz_ledger_file),"b5":(self.b5_settled_ids,self.b5_settled_markets,self.b5_trades,self.b5_ledger_file),"s5":(self.s5_settled_ids,self.s5_settled_markets,self.s5_trades,self.s5_ledger_file),"xau":(self.xau_settled_ids,self.xau_settled_markets,self.xau_trades,self.xau_ledger_file)};i,c,b,a=d[h]
  if pos["trade_id"]in i:return
  i.add(pos["trade_id"]);c.add(pos["market_id"]);b.append(pos)
  with open(a,"a",encoding="utf-8")as f:f.write(json.dumps(pos)+"\n")
  self.save_states()
 def _tail_jsonl_file(self,path,pos_attr):
  if not path.exists():return[]
  e=[]
  try:
   c=path.stat().st_size;a=getattr(self,pos_attr)
   if c<a:setattr(self,pos_attr,c);a=c
   if c>a:
    with open(path,"rb")as f:f.seek(a);d=f.read()
    b=d.rfind(b"\n")+1
    if b>0:
     setattr(self,pos_attr,a+b)
     for ln in d[:b].decode("utf-8",errors="ignore").splitlines():
      if ln.strip():
       try:e.append(json.loads(ln))
       except Exception:pass
  except Exception:pass
  return e
 def poll_tick(self,shutdown_requested=False):
  if shutdown_requested:self.save_states();return
  i=time.time()
  if not self.production_mode:
   for g in self._tail_jsonl_file(self.b5_telem_file,"b5_file_pos"):
    self._ingest_btc_5m_telemetry_tick(g);a=str(g.get("market_id")or"")
    if a in self.b5_pending:self.b5_pending[a]["latest_tick"]=g
   for g in self._tail_jsonl_file(self.s5_telem_file,"s5_file_pos"):
    self._ingest_sol_5m_telemetry_tick(g);a=str(g.get("market_id")or"")
    if a in self.s5_pending:self.s5_pending[a]["latest_tick"]=g
  for g in self._tail_jsonl_file(self.xau_telem_file,"xau_file_pos"):
   self.ingest_xau_15m_tick(g);a=str(g.get("market_id")or"")
   if a in self.xau_pending:self.xau_pending[a]["latest_tick"]=g
  c=((self.t15_btc_file,"t15_btc_pos"),(self.t15_eth_file,"t15_eth_pos"),(self.t1h_btc_file,"t1h_btc_pos"),(self.t1h_eth_file,"t1h_eth_pos"))
  if self.hz_open:
   for f,e in c:
    for g in self._tail_jsonl_file(f,e):
     a=str(g.get("market_id")or"")
     if a in self.hz_open:self._check_open_position_exit(self.hz_open,a,g,sleeve_tag="hz")
  else:
   for f,e in c:
    if f.exists():setattr(self,e,f.stat().st_size)
  h=time.time()
  if self.hz_pending:self._step_hz_pending(h)
  if self.b5_pending:self._step_b5_pending(h)
  if self.s5_pending:self._step_s5_pending(h)
  if self.xau_pending:self._step_xau_pending(h)
  for a,d in list(self.hz_open.items()):
   b=self._extract_market_view(d["asset"],a,d["horizon"])
   if b is not None:self._check_open_position_exit(self.hz_open,a,b,sleeve_tag="hz")
  for a,d in list(self.b5_open.items()):
   b=self._extract_market_view("BTC",a,"5m")
   if b is not None:self._check_open_position_exit(self.b5_open,a,b,sleeve_tag="b5")
  for a,d in list(self.s5_open.items()):
   b=self._extract_market_view("SOL",a,"5m")
   if b is not None:self._check_open_position_exit(self.s5_open,a,b,sleeve_tag="s5")
  for a,d in list(self.xau_open.items()):
   b=self._extract_market_view("XAU",a,"15m")
   if b is not None:self._check_open_position_exit(self.xau_open,a,b,sleeve_tag="xau")
  if(i-self._last_state_flush_ts)>=15.:self.save_states()
 def _build_sleeve_state(self,sleeve_id,strategy_desc,min_grad_trades,trades,open_map,pending_map,funnel,ledger_path,ticket_usd=SHADOW_TICKET_USD):n=len(trades);pnls=[float(t.get("net_pnl_usd")or.0)for t in trades];b=[float(t.get("net_pnl_with_20pct_rebate_usd")or t.get("net_pnl_usd")or.0)for t in trades];g=sum(1 for x in pnls if x>0);wr=round((g/n)*1e2,2)if n>0 else.0;gw=sum(x for x in pnls if x>0);gl=abs(sum(x for x in pnls if x<=0));pf=round(gw/gl,3)if gl>1e-6 else(99. if gw>0 else.0);a=round(sum(pnls),2);f=round(sum(float(t.get("taker_fee_usd")or.0)+float(t.get("exit_fee_usd")or.0)for t in trades),2);d,e=_bootstrap_prob_positive(pnls);c=bool(n>=min_grad_trades and pf>=1.5 and e[0]>.0 and d>=.95);return{"timestamp":_utc_now_str(),"sleeve_id":sleeve_id,"strategy":strategy_desc,"graduation_criteria":f"trades >= {min_grad_trades}, PF >= 1.50, bootstrap_95ci_lo > $0.00 (P(>0) >= 95%)","ready_for_live_graduation":c,"initial_capital":SHADOW_INITIAL_CAPITAL,"ticket_notional_usd":ticket_usd,"current_equity":round(SHADOW_INITIAL_CAPITAL+a,2),"realized_pnl":a,"realized_pnl_with_20pct_maker_rebate":round(sum(b),2),"profit_factor":pf,"win_rate_pct":wr,"bootstrap_prob_positive":d,"bootstrap_95ci_total_pnl":e,"total_fees_paid":f,"total_trades_settled":n,"winning_trades":g,"losing_trades":n-g,"active_open_positions_count":len(open_map),"open_positions":dict(open_map),"pending_orders_count":len(pending_map),"funnel_counters":dict(funnel),"status":"RUNNING","ledger_file":str(ledger_path)}
 def save_states(self):
  self._last_state_flush_ts=time.time();e=self._build_sleeve_state(sleeve_id="SLEEVE_HYBRID_ZSPLIT_SHADOW",strategy_desc="BTC/ETH 15m+1h Hybrid z-Split (0.78<=z<1.20 Shielded Maker 0% Fee + Comp-Book Shield + <=45$ Queue Cap, z>=1.20 Taker+P3A)",min_grad_trades=50,trades=self.hz_trades,open_map=self.hz_open,pending_map=self.hz_pending,funnel=self.hz_funnel,ledger_path=self.hz_ledger_file);d=self._build_sleeve_state(sleeve_id="SLEEVE_BTC_5M_SNIPER_SHADOW",strategy_desc="BTC-Only 5m Final-TWAP Sniper (TTE 60-180s, USD Chainlink + USDT Dual-Strike Cush>=3bps, z>=0.80, px<=0.85, ETH/SOL Excluded)",min_grad_trades=60,trades=self.b5_trades,open_map=self.b5_open,pending_map=self.b5_pending,funnel=self.b5_funnel,ledger_path=self.b5_ledger_file);c=self._build_sleeve_state(sleeve_id="SLEEVE_SOL_5M_CANARY_SHADOW",strategy_desc="SOL-Only 5m Isolated Canary Shadow (TTE 60-180s, sqrt(12) vol, Dual-Strike Cush>=4bps, z>=0.80, px<=0.85)",min_grad_trades=60,trades=self.s5_trades,open_map=self.s5_open,pending_map=self.s5_pending,funnel=self.s5_funnel,ledger_path=self.s5_ledger_file);b=self._build_sleeve_state(sleeve_id="SLEEVE_XAU_15M_MAKER_SHADOW",strategy_desc="XAU/USD 15m Shielded Maker-First (3-dec synth USD + Swissquote <=2.5bps, single-spot diffusion, CME/Session gated, 0% fee/0% rebate, $12 clip)",min_grad_trades=40,trades=self.xau_trades,open_map=self.xau_open,pending_map=self.xau_pending,funnel=self.xau_funnel,ledger_path=self.xau_ledger_file,ticket_usd=XAU_TICKET_USD)
  for g,a in((e,self.hz_state_file),(d,self.b5_state_file),(c,self.s5_state_file),(b,self.xau_state_file)):
   h=a.with_suffix(f".tmp.{os.getpid()}")
   try:
    with open(h,"w",encoding="utf-8")as f:json.dump(g,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(h,a)
   except Exception:
    if h.exists():
     try:h.unlink()
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
 raw_mc=cand.get("micro_clips")
 if isinstance(raw_mc,(list,tuple))and raw_mc:
  j=[(float(r[0]),float(r[1]),float(r[2]),float(r[3]))for r in raw_mc if isinstance(r,(list,tuple))and len(r)>=4 and float(r[0])>.0]
  if j:j.sort(key=lambda x:x[0]);return j
 c=float(cand.get("cushion_oracle",cand.get("cushion_min",.0))or.0);f=float(cand.get("bid_t0",.0)or.0);e=float(cand.get("ask_t0",1.)or 1.);d=float(cand.get("ask_500ms")or e);b=float(cand.get("ask_1000ms")or d);h=float(cand.get("tte",3e2)or 3e2);a=[(.1,c,f,round(.5*(e+d),4)),(.25,c,f,round(.25*e+.75*d,4)),(.5,c,max(.01,round(d-max(.01,e-f),4)),d),(1.,c,max(.01,round(b-max(.01,e-f),4)),b)]
 for i in cand.get("path")or():
  if len(i)<4:continue
  g=round(max(.0,h-float(i[0])),3)
  if 1.05<=g<=6.:a.append((g,float(i[1]),float(i[2]),float(i[3])))
 a.sort(key=lambda x:x[0]);return a
def _clip_at_or_after(clips,target_dt,fallback):
 for cl in clips:
  if cl[0]>=target_dt-1e-6:return cl
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
 sh=max(1.,float(shares));g=min(max(.0,float(avail_a_shares)),max(.0,float(avail_b_shares)));f=g/sh
 if f<1.15:a=.22
 elif f<1.5:a=.16
 elif f<2.25:a=.05
 else:a=.015
 if is_zero_itode:a*=.4
 if is_4h_mixed:a=min(.35,a+.05)
 k=max(.02,min(.98,.5*(float(px_a)+float(px_b))));j=max(.0,.5*(float(fee_rate_a)+float(fee_rate_b)));i=v2_taker_fee_per_share(k,j);l=max(.01,k-float(unwind_slip_cents));h=v2_taker_fee_per_share(l,j);d=float(unwind_slip_cents)+i+h;e=a*d;b=1.-float(box_cost_net);c=b-e;return{"min_depth_mult":round(f,4),"p_leg_miss":round(a,4),"unwind_loss_per_share":round(d,5),"legging_drag_per_pair":round(e,5),"legging_drag_usd":round(sh*e,4),"gross_floor_per_pair":round(b,5),"legging_adjusted_net_ev_per_pair":round(c,5),"legging_adjusted_min_profit_usd":round(sh*c,4)}
def simulate_d1_box_with_latency_skew(box_cand,policy_cfg,delta_t_ms=150.):
 sh=max(5.,float(box_cand.get("shares",12.)));N=float(box_cand.get("leg_a_limit_price",.48));M=float(box_cand.get("leg_b_limit_price",.48));C=float(box_cand.get("leg_a_avail_shares",sh*2.));B=float(box_cand.get("leg_b_avail_shares",sh*2.));L=str(box_cand.get("leg_a_horizon","15m")).lower();K=str(box_cand.get("leg_b_horizon","5m")).lower();J=float(box_cand.get("leg_a_fee_rate",DEFAULT_FEE_RATE));I=float(box_cand.get("leg_b_fee_rate",DEFAULT_FEE_RATE));t=float(box_cand.get("box_cost_net")or(N+M+v2_taker_fee_per_share(N,J)+v2_taker_fee_per_share(M,I)));s=bool(box_cand.get("corridor_jackpot",False));k=float(policy_cfg.get("min_depth_mult_gate",1.5));e=float(policy_cfg.get("depth_ratio_threshold",1.35));r=str(policy_cfg.get("routing_mode","hybrid_auto"));f=float(policy_cfg.get("max_giveback_frac",.35));q=float(policy_cfg.get("max_box_cost_net",.985));z=min(C,B);y=max(C,B)
 if t>q or(z/sh)<k:return{"entered":False,"outcome":"GATED_OUT","pnl_usd":.0,"legged_out":False}
 v=("4h"in(L,K))and(L!=K);x=y/max(z,1e-6)
 if r=="fragile_first":a=True
 elif r=="parallel_2leg":a=False
 else:a=bool(v or x>=e or t>.975)
 d=True
 if v:d=(L!="4h")
 elif B<C:d=False
 if d:l1=(N,C,J,float(box_cand.get("depletion_a_per_s",18.)),float(box_cand.get("bid_drop_a",.02)));l2=(M,B,I,float(box_cand.get("depletion_b_per_s",10.)),float(box_cand.get("bid_drop_b",.02)))
 else:l1=(M,B,I,float(box_cand.get("depletion_b_per_s",18.)),float(box_cand.get("bid_drop_b",.02)));l2=(N,C,J,float(box_cand.get("depletion_a_per_s",10.)),float(box_cand.get("bid_drop_a",.02)))
 j=float(box_cand.get("base_transit_s",.12));F=max(.0,float(delta_t_ms)/1e3)
 if a:
  p=l1[1]-l1[3]*j
  if p<sh:return{"entered":False,"outcome":"LEG1_CLEAN_ABORT","pnl_usd":.0,"legged_out":False}
  o=l2[1]-l2[3]*(j+F);b=l1;c=o>=sh
 else:
  p=l1[1]-l1[3]*(j+.25*F);o=l2[1]-l2[3]*(j+.25*F)
  if p>=sh and o>=sh:c=True;b=l1
  elif p<sh and o<sh:return{"entered":False,"outcome":"BOTH_MISSED_CLEAN","pnl_usd":.0,"legged_out":False}
  else:c=False;b=l1 if p>=sh else l2
 if c:i=2. if s else 1.;O=round(sh*(i-t),4);return{"entered":True,"outcome":"BOX_LOCKED","pnl_usd":O,"legged_out":False}
 H,_,G,_,n=b;E=v2_taker_fee_per_share(H,G);l=max(.01,1.-t);h=max(.01,min(.03,f*l*2.));u=max(.02,round(H-n,4));m=round(max(.02,H-h),4)
 if u>=m:w=u;g="LEGGED_OUT_STAGE1"
 else:w=max(.02,round(max(H*.85,u-.015),4));g="LEGGED_OUT_STAGE2"
 A=v2_taker_fee_per_share(w,G);D=round(sh*((w-H)-E-A),4);return{"entered":True,"outcome":g,"pnl_usd":D,"legged_out":True}
def _default_d1_calibration_events(data_dir=None):
 k=[]
 if data_dir is not None:
  j=Path(data_dir)/"d1_live_box_candidates.jsonl"
  if j.exists():
   try:a=j.read_text(encoding="utf-8",errors="ignore").splitlines()
   except Exception:a=[]
   for ln in a:
    if not ln.strip():continue
    try:
     d=json.loads(ln)
     if not isinstance(d,dict):continue
     sh=max(5.,float(d.get("shares")or 12.));e=float(d.get("leg_a_avail_shares")or sh*1.8);c=float(d.get("leg_b_avail_shares")or sh*1.8);k.append({**d,"depletion_a_per_s":round(max(4.,.32*e),2),"depletion_b_per_s":round(max(4.,.24*c),2),"bid_drop_a":.02 if float(d.get("box_cost_net")or.98)<=.98 else.03,"bid_drop_b":.02})
    except Exception:continue
 if len(k)>=36:return k
 i=[];b=[(.968,36.,34.,"15m","5m",14.,12.,.015,False),(.974,19.,42.,"15m","5m",22.,10.,.02,False),(.991,13.5,28.,"15m","5m",24.,14.,.03,False),(.976,38.,20.,"4h","15m",10.,26.,.025,False),(.964,30.,29.,"15m","5m",12.,12.,.015,True),(.982,16.,35.,"4h","15m",28.,12.,.03,False)]
 for q in range(60):h,e,c,p,o,m,l,g,n=b[q%len(b)];f=(q%5-2)*.0015;i.append({"shares":12.,"box_cost_net":round(h+f,4),"leg_a_limit_price":round(.5*(h+f)-.01,4),"leg_b_limit_price":round(.5*(h+f)-.01,4),"leg_a_avail_shares":e,"leg_b_avail_shares":c,"leg_a_horizon":p,"leg_b_horizon":o,"depletion_a_per_s":m,"depletion_b_per_s":l,"bid_drop_a":g,"bid_drop_b":.02,"corridor_jackpot":bool(n and(q%12==4))})
 return i
def _score_d1_slice(events,cfg,skew_grid_ms=(.0,1e2,2e2,4e2)):
 pnls=[];b=0;a=0
 for ev in events:
  for c in skew_grid_ms:
   r=simulate_d1_box_with_latency_skew(ev,cfg,delta_t_ms=c)
   if r["entered"]:
    a+=1;pnls.append(float(r["pnl_usd"]))
    if r["legged_out"]:b+=1
 gw=sum(x for x in pnls if x>.0);gl=abs(sum(x for x in pnls if x<=.0));pf=gw/gl if gl>1e-6 else(99. if gw>.0 else.0);return{"entered":a,"net_pnl_usd":round(sum(pnls),3),"profit_factor":round(pf,3),"legged_out_count":b,"legged_out_rate":round(b/max(a,1),4)}
def calibrate_d1_box_wfo(box_events=None,data_dir=None,purge_gap=3):
 p=list(box_events)if box_events is not None else _default_d1_calibration_events(data_dir);n=len(p);w=max(4,int(.5*n));o=min(n,w+purge_gap);m=max(o+2,int(.75*n));l=min(n,m+purge_gap);t=p[:w];s=p[o:m];r=p[l:];c=-1e9;f={"routing_mode":"hybrid_auto","depth_ratio_threshold":1.35,"min_depth_mult_gate":1.5,"max_giveback_frac":.35,"max_box_cost_net":.985};b={};a={};d=0
 for k in("hybrid_auto","fragile_first","parallel_2leg"):
  for q in(1.2,1.35,1.5):
   for j in(1.15,1.5,1.75):
    for i in(.25,.35,.5):
     g={"routing_mode":k,"depth_ratio_threshold":q,"min_depth_mult_gate":j,"max_giveback_frac":i,"max_box_cost_net":.985};d+=1;v=_score_d1_slice(t,g);u=_score_d1_slice(s,g)
     if v["entered"]<4 or u["entered"]<2:continue
     sc=(min(v["net_pnl_usd"],u["net_pnl_usd"])+.25*(v["net_pnl_usd"]+u["net_pnl_usd"])-8.*max(v["legged_out_rate"],u["legged_out_rate"]))
     if sc>c:c=sc;f=g;b=v;a=u
 if not b:b=_score_d1_slice(t,f);a=_score_d1_slice(s,f)
 h=_score_d1_slice(r,f);e=_score_d1_slice(r,{"routing_mode":"parallel_2leg","depth_ratio_threshold":1.5,"min_depth_mult_gate":1.,"max_giveback_frac":.25,"max_box_cost_net":.995});return{"events_total":n,"purge_gap_events":purge_gap,"grid_configs_evaluated":d,"selected_d1_policy":f,"train":b,"val":a,"sealed_holdout":h,"unfiltered_parallel_holdout_baseline":e}
def compute_d1_maker_anchor_drag_haircut(shares,pair_eff,bid_anc,hdg_px,hdg_avail_shares,fee_rate_anc=DEFAULT_FEE_RATE,fee_exponent_anc=1.,queue_front=True,is_4h_mixed=False,scratch_slip_cents=.015):
 sh=max(1.,float(shares));f=max(.0,float(hdg_avail_shares))/sh
 if f<1.5:a=.14
 elif f<2.5:a=.055
 else:a=.02
 if not queue_front:a=min(.3,a+.025)
 if is_4h_mixed:a=min(.3,a+.02)
 i=max(.01,float(bid_anc)-float(scratch_slip_cents));h=v2_taker_fee_per_share(i,fee_rate_anc,fee_exponent_anc);c=(float(bid_anc)-i)+h;e=a*c;d=1.-float(pair_eff);g=d-e;b=.2*v2_taker_fee_per_share(float(bid_anc),fee_rate_anc,fee_exponent_anc);return{"hdg_depth_mult":round(f,4),"p_hedge_miss_250ms":round(a,4),"scratch_loss_per_share":round(c,5),"legging_drag_per_pair":round(e,5),"legging_drag_usd":round(sh*e,4),"gross_floor_per_pair":round(d,5),"legging_adjusted_net_ev_per_pair":round(g,5),"legging_adjusted_min_profit_usd":round(sh*g,4),"maker_rebate_20pct_est_usd":round(sh*b,4)}
def _default_d1_maker_leg1_events():
 a=[("UP",.48,.5,.12,.48,85.,.6,True,.0,18.),("DOWN",.48,.49,.18,.49,95.,-.8,True,.0,18.),("UP",.48,.49,-.48,.49,60.,-4.2,True,.04,18.),("UP",.964,.999,.1,.019,32.,.4,True,.0,15.),("DOWN",.47,.49,.05,.49,70.,3.8,True,.03,18.),("UP",.46,.48,.22,.5,18.,.3,True,.02,18.)];m=[]
 for l in range(60):g,k,j,d,i,f,c,e,b,sh=a[l%len(a)];h=(l%3-1)*.001;m.append({"anc_side":g,"bid_anc":round(k,3),"ask_anc":round(j,3),"obi_anc":round(d+h*10.,3),"ask_hdg":round(i,3),"hdg_shares":f,"spot_ret_bps":c,"passive_fill":e,"hdg_jump_on_adverse":b,"shares":sh,"fee_rate":DEFAULT_FEE_RATE})
 return m
def simulate_d1_maker_leg1_box(ev,cfg):
 B=float(ev["bid_anc"]);A=float(ev["ask_anc"]);s=float(ev.get("obi_anc",.0));z=float(ev["ask_hdg"]);y=float(ev["hdg_shares"]);sh=max(5.,float(ev.get("shares",18.)));fr=float(ev.get("fee_rate",DEFAULT_FEE_RATE));D=str(ev.get("anc_side","UP")).upper();g=float(ev.get("spot_ret_bps",.0))
 def _snap_px(p):p=round(float(p),4);return(math.floor((p+1e-9)*1e2)/1e2)if(.04+1e-9<p<.96-1e-9)else(math.floor((p+1e-9)*1e3)/1e3)
 x=.001 if(B>=.96 or B<.04)else.01;w=.001 if(A>.96 or A<=.04)else.01;n=_snap_px(B+x);k=_snap_px(A-w);E=round(A-B,4);d=bool(cfg.get("allow_join_1c_mid",True));j=float(cfg.get("min_obi_join_1c",-.15));i=float(cfg.get("min_obi_any",-.35));f=float(cfg.get("min_hdg_depth_mult",2.5));e=float(cfg.get("max_post_net",.988));c=float(cfg.get("adverse_spot_cancel_bps",2.5))
 if s<i or y<max(15.,f*sh):return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 if n<=k+1e-9 and n>B+1e-9:a=min(n,k);b=True
 elif d and E>=.01-1e-9 and.15<=A<=.85 and s>=j:a=_snap_px(B);b=False
 else:return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 m=z+v2_taker_fee_per_share(z,fr);r=_snap_px(e-m);v=min(a,r)
 if v<round(B-(x if b else.0),3)or v<=.02 or v>=A:return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 if not(.9<=(v+m)<=e):return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 q=(-g)if D=="UP"else g
 if q>c:return{"posted":True,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 if not ev.get("passive_fill",True):return{"posted":True,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 h=round(z+(float(ev.get("hdg_jump_on_adverse",.0))if q>1.5 else.0),4);l=v+h+v2_taker_fee_per_share(h,fr)
 if.9<=l<=.995:C=compute_d1_maker_anchor_drag_haircut(shares=sh,pair_eff=l,bid_anc=v,hdg_px=h,hdg_avail_shares=y,fee_rate_anc=fr,queue_front=b);return{"posted":True,"filled":True,"hedged":True,"scratched":False,"pnl_usd":round(sh*(1.-l),4),"adj_pnl_usd":C["legging_adjusted_min_profit_usd"]}
 u=max(.01,v-max(.015,float(ev.get("hdg_jump_on_adverse",.02))));o=u-v2_taker_fee_per_share(u,fr);t=round(sh*(o-v),4);return{"posted":True,"filled":True,"hedged":False,"scratched":True,"pnl_usd":t,"adj_pnl_usd":t}
def calibrate_d1_maker_leg1_wfo(maker_events=None,purge_gap=3):
 p=list(maker_events)if maker_events is not None else _default_d1_maker_leg1_events();n=len(p);y=max(4,int(.5*n));o=min(n,y+purge_gap);m=max(o+2,int(.75*n));l=min(n,m+purge_gap);v,u,t=p[:y],p[o:m],p[l:]
 def _eval(sub,cfg):rows=[simulate_d1_maker_leg1_box(e,cfg)for e in sub];fills=[r for r in rows if r["filled"]];d=[r for r in fills if r["hedged"]];a=[r for r in fills if r["scratched"]];c=sum(float(r.get("adj_pnl_usd",r["pnl_usd"]))for r in fills);b=sum(float(r["pnl_usd"])for r in fills);return{"posted":sum(1 for r in rows if r["posted"]),"fills":len(fills),"wins":len(d),"scratches":len(a),"win_rate_pct":round(1e2*len(d)/len(fills),2)if fills else.0,"raw_pnl_usd":round(b,4),"legging_adjusted_pnl_usd":round(c,4)}
 d=-1e9;c={"allow_join_1c_mid":True,"min_obi_join_1c":-.15,"min_obi_any":-.35,"min_hdg_depth_mult":2.5,"adverse_spot_cancel_bps":2.5,"max_post_net":.988};b={};a={};f=0
 for j in(True,False):
  for i in(2.,2.5,5.):
   for k in(-.15,-.4):
    for s in(1.5,2.5):
     q={"allow_join_1c_mid":j,"min_obi_join_1c":k,"min_obi_any":-.35,"min_hdg_depth_mult":s,"adverse_spot_cancel_bps":i,"max_post_net":.988};f+=1;x,w=_eval(v,q),_eval(u,q)
     if x["fills"]<3 or w["fills"]<2:continue
     sc=(min(x["legging_adjusted_pnl_usd"],w["legging_adjusted_pnl_usd"])+.3*(x["legging_adjusted_pnl_usd"]+w["legging_adjusted_pnl_usd"])-6.*(x["scratches"]+w["scratches"]))
     if sc>d:d,c,b,a=sc,q,x,w
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
 import itertools;import random;import statistics;all_sorted=sorted(cands,key=lambda x:x["t0"]);_m=len(all_sorted);R=6;A=[]
 for _l in range(R):_w=int((_l/R)*_m);_v=int(((_l+1)/R)*_m)-1;A.append((all_sorted[_w]["t0"],all_sorted[max(_w,_v)]["t0"]))
 l=[]
 for _k,_j in[(.55,.8),(.55,.82),(.55,.85)]:
  for _u in[.65,.85,1.05]:
   for _t in[4e-4,6e-4]:
    for _L in[.01,.02]:
     for _s in["single_95","two_tranche_14_98","two_tranche_95_98","hold_98"]:
      for _K,_J,_I,_H in[("spot_persist",None,9e-4,18.),("hybrid_persist",.12,6e-4,15.)]:l.append({"assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":90.,"max_tte_15m":480.,"min_tte_1h":150.,"max_tte_1h":1200.,"min_px":_k,"max_px":_j,"max_spread":.03,"min_l1_usd":20.,"min_cushion":_t,"min_z":_u,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True,"entry_mode":"taker_fak","fak_buffer":_L,"exit_policy":_s,"ratchet_arm":_J,"ratchet_drop":.06,"salvage_mode":_K,"wrong_side_thresh":_I,"salvage_persist_s":_H,"clob_drop_thresh":.22,"final_45s_unwind":False})
 apriori_superset=prefilter_fn(all_sorted,{"assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":90.,"max_tte_15m":480.,"min_tte_1h":150.,"max_tte_1h":1200.,"min_px":.55,"max_px":.85,"max_spread":.03,"min_l1_usd":20.,"min_cushion":4e-4,"min_z":.65,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True});cpcv_splits=[]
 for _G,_F in itertools.combinations(range(R),2):
  test_intervals=[A[_G],A[_F]];train_cpcv=[c for c in apriori_superset if all((c["exp_ts"]<(ts_i-purge_sec))or(c["t0"]>(te_i+purge_sec))for ts_i,te_i in test_intervals)];Q=[]
  for _E in(_G,_F):_D,t_e=A[_E];I=purge_sec if(_E>0 and(_E-1)not in(_G,_F))else.0;E=purge_sec if(_E<R-1 and(_E+1)not in(_G,_F))else.0;eff_s,eff_e=_D+I,t_e-E*.25;Q.extend(c for c in apriori_superset if eff_s<=c["t0"]<=eff_e and c["exp_ts"]<=t_e)
  Q.sort(key=lambda x:x["t0"]);_r=len(train_cpcv);t_cut_inner=train_cpcv[int(.7*_r)]["t0"]if _r>=20 else.0;_i=[c for c in train_cpcv if c["exp_ts"]<=t_cut_inner];_h=[c for c in train_cpcv if c["t0"]>=(t_cut_inner+purge_sec)];f=l[0];d=-1e9
  for n in l:
   _g=evaluate_portfolio_fn(_i,n,latency_mode="500ms")
   if _g["trades"]<20 or _g["total_pnl"]<=0 or _g["profit_factor"]<1.2:continue
   _f=evaluate_portfolio_fn(_h,n,latency_mode="500ms")
   if _f["trades"]<8 or _f["total_pnl"]<=0 or _f["profit_factor"]<1.15:continue
   P=dev_score_fn(_g,_f)
   if P>d:d,f=P,n
  if d<=-1e8:
   for n in l:
    _a=evaluate_portfolio_fn(train_cpcv,n,latency_mode="500ms")
    if _a["trades"]>=25 and _a["total_pnl"]>0:
     P=dev_score_fn(_a,_a)
     if P>d:d,f=P,n
  Z=evaluate_portfolio_fn(Q,f,latency_mode="500ms");D=evaluate_portfolio_fn(Q,f,latency_mode="500ms",max_concurrent=1,ticket_usd=12.);cpcv_splits.append({"test_groups":[_G,_F],"fitted_exit_policy":f["exit_policy"],"fitted_min_z":f["min_z"],"trades":Z["trades"],"total_pnl":Z["total_pnl"],"seed_12_c1_pnl":D["total_pnl"],"win_rate":Z["win_rate"],"profit_factor":Z["profit_factor"],"sharpe":Z["sharpe"],"wipeout_rate":Z["wipeout_rate"]})
 cpcv_pnls_list=[s["total_pnl"]for s in cpcv_splits];cpcv_seed_pnls=[s["seed_12_c1_pnl"]for s in cpcv_splits];z={"mode":"GENUINE_OUT_OF_SAMPLE_REFIT_CPCV_6_2","n_groups":6,"k_test_groups":2,"apriori_grid_size":len(l),"total_combinations":len(cpcv_splits),"positive_combinations":sum(1 for x in cpcv_pnls_list if x>0),"positive_rate":round(sum(1 for x in cpcv_pnls_list if x>0)/max(len(cpcv_splits),1),4),"seed_12_c1_positive_combinations":sum(1 for x in cpcv_seed_pnls if x>0),"median_oos_trades":int(statistics.median(s["trades"]for s in cpcv_splits)),"median_oos_pnl_usd":round(statistics.median(cpcv_pnls_list),2),"mean_oos_pnl_usd":round(statistics.mean(cpcv_pnls_list),2),"median_seed_12_c1_oos_pnl_usd":round(statistics.median(cpcv_seed_pnls),2),"min_oos_pnl_usd":round(min(cpcv_pnls_list),2),"median_oos_pf":round(statistics.median(s["profit_factor"]for s in cpcv_splits),3),"median_oos_sharpe":round(statistics.median(s["sharpe"]for s in cpcv_splits),3),"splits":cpcv_splits};t=set();_e=data_dir/"verified_gamma_resolutions.json"
 if _e.exists():
  try:
   for _C,_B in json.loads(_e.read_text(encoding="utf-8")).items():
    if isinstance(_B,dict)and(_B.get("oracle_mismatch")or _B.get("mismatch")or(_B.get("binance_winner")and _B.get("winner")and _B.get("binance_winner")!=_B.get("winner"))):t.add(str(_C))
  except Exception:pass
 for V in("ground_truth_resolutions.jsonl","ground_truth_resolutions_eth.jsonl","ground_truth_resolutions_sol.jsonl"):
  _q=data_dir/V
  if _q.exists():
   try:
    for ln in _q.read_text(encoding="utf-8",errors="replace").splitlines():
     if ln.strip():
      _d=json.loads(ln)
      if _d.get("oracle_mismatch")or(_d.get("binance_winning_outcome")and _d.get("gamma_winning_outcome")and _d.get("binance_winning_outcome")!=_d.get("gamma_winning_outcome")):t.add(str(_d.get("market_id")))
   except Exception:pass
 for Y in all_sorted:
  if Y["path"]:
   J,H,_,_,_=Y["path"][-1]
   if J<=30. and abs(H)>=1e-5 and((H>0)!=bool(Y["won"])):t.add(str(Y.get("mid")))
  if str(Y.get("mid"))in t:Y["oracle_mismatch"]=True
 r=[c for c in all_sorted if c.get("oracle_mismatch")];X=evaluate_portfolio_fn(r,dict(best_cfg,use_cl_proxy=False),latency_mode="500ms");_c=evaluate_portfolio_fn(r,dict(best_cfg,use_cl_proxy=True),latency_mode="500ms");G=evaluate_portfolio_fn(all_sorted,dict(best_cfg,use_cl_proxy=False),latency_mode="500ms");y=evaluate_portfolio_fn(all_sorted,dict(best_cfg,use_cl_proxy=True),latency_mode="500ms");O=dict(best_cfg)
 if not str(O.get("exit_policy","")).startswith("two_tranche"):O["exit_policy"]="two_tranche_12_98"
 C=evaluate_portfolio_fn(all_sorted,dict(O,t2_post_lag_s=5.),latency_mode="500ms");F=evaluate_portfolio_fn(all_sorted,dict(O,t2_post_lag_s=.05),latency_mode="500ms");q=evaluate_portfolio_fn(all_sorted,dict(O,t2_post_lag_s=.0),latency_mode="500ms");h={"mismatch_markets_identified":len(t),"mismatch_candidates_total":len(r),"mismatch_raw_trades":X["trades"],"mismatch_raw_pnl":X["total_pnl"],"mismatch_cl_proxy_trades":_c["trades"],"mismatch_cl_proxy_pnl":_c["total_pnl"],"full_dataset_raw_pnl":G["total_pnl"],"full_dataset_raw_pf":G["profit_factor"],"full_dataset_cl_proxy_pnl":y["total_pnl"],"full_dataset_cl_proxy_pf":y["profit_factor"],"blueprint1_tranche2_comparison":{"delayed_5s_pnl":C["total_pnl"],"delayed_5s_pf":C["profit_factor"],"inline_50ms_pnl":F["total_pnl"],"inline_50ms_pf":F["profit_factor"],"concurrent_0ms_pnl":q["total_pnl"],"concurrent_0ms_pf":q["profit_factor"]}};oos_unit_rets=[p/15. for p in(best_vl["pnls"]+best_hold_500["pnls"])]
 if len(oos_unit_rets)<20:oos_unit_rets=[p/15. for p in best_tr["pnls"]]
 def _sim_bankroll(label,start_eq,base_pct,min_tkt,floor_u,seed_cap=.0,corr_p=.0):
  g=random.Random(20261025);b=0;e,d=[],[];i=max(1,len(oos_unit_rets))
  for _ in range(10000):
   eq,pk,f,c,a=start_eq,start_eq,.0,False,0
   while a<50 and oos_unit_rets:
    if eq<floor_u:c=True;break
    if seed_cap>.0 and eq<seed_cap:eq+=min(eq,12.)*oos_unit_rets[g.randrange(i)];a+=1
    else:
     h=min(eq,max(min_tkt,round(eq*base_pct,2)))
     if corr_p>.0 and g.random()<corr_p and(a+1)<50:r1=oos_unit_rets[g.randrange(i)];r2=r1 if g.random()<.75 else oos_unit_rets[g.randrange(i)];eq+=h*r1+(h*.54)*r2;a+=2
     else:eq+=h*oos_unit_rets[g.randrange(i)];a+=1
    pk=max(pk,eq);f=max(f,pk-eq)
    if eq<floor_u:c=True;break
   if c:b+=1
   e.append(eq);d.append(f)
  e.sort();d.sort();return{"policy":label,"start_equity_usd":start_eq,"floor_usd":floor_u,"halt_prob_50_trades":round(b/10000,4),"median_terminal_equity_usd":round(e[5000],2),"p05_terminal_equity_usd":round(e[500],2),"p95_terminal_equity_usd":round(e[9500],2),"p95_max_drawdown_usd":round(d[9500],2)}
 B=[_sim_bankroll("v3.7_UNPATCHED_22PCT_FLOOR65_CONC2",76.49,.22,12.,65.,corr_p=.25),_sim_bankroll("CENTRAL_CFG_18PCT_FLOOR66.67_CONC2",76.49,.18,12.,66.67,corr_p=.25),_sim_bankroll("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR48",76.49,.18,12.,48.,seed_cap=88.,corr_p=.15),_sim_bankroll("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR52",76.49,.18,12.,52.,seed_cap=88.,corr_p=.15)];w=[];o=set()
 for sc,c_i,tr_i,vl_i,_ in stage2_results:
  _p=(c_i["assets"],c_i["horizons"],c_i["min_px"],c_i["max_px"],c_i["min_z"],c_i["min_cushion"],c_i["entry_mode"],c_i["exit_policy"])
  if _p in o:continue
  o.add(_p);ho_i=evaluate_portfolio_fn(holdout_cands,c_i,latency_mode="500ms");w.append({"score":round(sc,2),"config":{k:(list(v)if isinstance(v,tuple)else v)for k,v in c_i.items()},"train":{k:v for k,v in tr_i.items()if k!="pnls"},"val":{k:v for k,v in vl_i.items()if k!="pnls"},"holdout":{k:v for k,v in ho_i.items()if k!="pnls"}})
  if len(w)>=5:break
 a={};U=data_dir/"live_harvester_state.json"
 if U.exists():
  st=json.loads(U.read_text(encoding="utf-8"));closed_live=st.get("closed_positions",[]);cand_by_eid={c["event_id"]:c for c in cands};m,g,b,e=.0,0,0,0;j=[]
  for _A in closed_live:
   T=float(_A.get("net_pnl_usd")or.0);_z=str(_A.get("event_id")or"");_y=str(_A.get("trade_id")or"");S=cand_by_eid.get(_z)
   if not S:continue
   g+=1;_x=simulate_single_fn(S,best_cfg,latency_mode="500ms");N=float(_A.get("notional_usd")or 15.)
   if _x is None:
    u,i=.0,"VETOED_AT_ENTRY"
    if T<0:b+=1
    else:e+=1
   else:u,i=round(_x[0]*N,2),_x[1]
   m+=u
   if"6076647"in _y or"6082720"in _y or T<=-15.:j.append({"trade_id":_y,"entry_price":_A.get("entry_price"),"max_seen_bid":_A.get("max_seen_bid"),"actual_pnl_usd":round(T,2),"actual_close_reason":_A.get("close_reason"),"wfo_counterfactual_pnl_usd":u,"wfo_counterfactual_action":i})
  a={"total_live_closed_trades":len(closed_live),"matched_to_trigger_dataset":g,"actual_matched_subset_pnl_usd":round(sum(float(p.get("net_pnl_usd")or.0)for p in closed_live if str(p.get("event_id")or"")in cand_by_eid),2),"wfo_optimal_counterfactual_pnl_usd":round(m,2),"filtered_out_losing_trades":b,"filtered_out_winning_trades":e,"wipeout_trades_counterfactual":j}
 M=[];_b=len(dev_cands)
 if _b>=100:
  for L,(_o,_n)in enumerate([(.25,.43),(.43,.62),(.62,.81),(.81,1.)],start=1):t_cut=dev_cands[int(_o*_b)]["t0"];t_end=dev_cands[min(_b-1,int(_n*_b)-1)]["t0"];K=[c for c in dev_cands if(t_cut+purge_sec)<=c["t0"]<=t_end];W=evaluate_portfolio_fn(K,best_cfg,latency_mode="500ms");M.append({"fold":L,"oos_candidates":len(K),"trades":W["trades"],"total_pnl":W["total_pnl"],"win_rate":W["win_rate"],"profit_factor":W["profit_factor"],"wipeout_rate":W["wipeout_rate"]})
 return{"cpcv_summary":z,"chainlink_proxy_audit":h,"bankroll_mc":B,"top5_summary":w,"live_counterfactual":a,"cv_folds":M}
def run_subhourly_v395_wfo_ablation_suite(cands,evaluate_portfolio_fn,purge_sec=9e2):
 i=sorted([c for c in cands if c.get("hz")=="15m"],key=lambda x:x["t0"]);k=sorted([c for c in cands if c.get("hz")=="5m"],key=lambda x:x["t0"])
 def _purged_split(items,embargo):
  if len(items)<12:return list(items),[],[]
  a=[c["t0"]for c in items];t_tr=a[int(.5*len(a))];t_vl=a[int(.75*len(a))];tr=[c for c in items if c["exp_ts"]<=t_tr];vl=[c for c in items if c["t0"]>=(t_tr+embargo)and c["exp_ts"]<=t_vl];ho=[c for c in items if c["t0"]>=(t_vl+embargo)];return tr,vl,ho
 tr_15,vl_15,ho_15=_purged_split(i,purge_sec);t,s,q=_purged_split(k,max(3e2,purge_sec*.5));b=[c for c in(tr_15+vl_15)if 60.<=c["tte"]<=480. and.75<=abs(c.get("z_oracle",.0))<=2.5];e=[c for c in ho_15 if 60.<=c["tte"]<=480. and.75<=abs(c.get("z_oracle",.0))<=2.5]
 def _brier(rows,df_v,jvm):
  if not rows:return.25
  a=.0
  for r in rows:_,b=compute_v395_pricing_and_twap_gate(r,df=df_v,jump_vol_mult=jvm,use_kemna_vorst=True);y=1. if r.get("won")else.0;a+=(b-y)**2
  return round(a/len(rows),6)
 g=[];a={"df":None,"jump_vol_mult":1.,"dev_brier":1.}
 for j in(None,4.,6.,8.):
  for h in(1.,1.15,1.25):
   o=_brier(b,j,h);p=_brier(e,j,h);n={"df":"gaussian"if j is None else j,"jump_vol_mult":h,"dev_n":len(b),"dev_brier":o,"holdout_n":len(e),"holdout_brier":p};g.append(n)
   if o<a["dev_brier"]:a={"df":n["df"],"jump_vol_mult":h,"dev_brier":o,"holdout_brier":p}
 base_15m_cfg={"assets":("BTC","ETH","SOL"),"horizons":("15m",),"min_tte_15m":90.,"max_tte_15m":480.,"min_tte_5m":60.,"max_tte_5m":180.,"min_tte_1h":150.,"max_tte_1h":6e2,"min_px":.55,"max_px":.81,"max_spread":.03,"min_l1_usd":12.,"min_cushion":6e-4,"min_z":.78,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True,"entry_mode":"cascade_v4","fak_buffer":.02,"cascade_ticket_usd":16.5,"elastic_downsnap_usd":12.,"min_elastic_usd":8.,"exit_policy":"hold_98","ratchet_arm":None,"ratchet_drop":.06,"salvage_mode":"spot_persist","wrong_side_thresh":9e-4,"salvage_persist_s":18.,"clob_drop_thresh":.3,"final_45s_unwind":False}
 def _run_var(label,overrides,slices):a={**base_15m_cfg,**overrides};g,f,e=slices;d=evaluate_portfolio_fn(g,a,latency_mode="500ms")if g else{"trades":0,"total_pnl":.0,"profit_factor":.0,"win_rate":.0};c=evaluate_portfolio_fn(f,a,latency_mode="500ms")if f else{"trades":0,"total_pnl":.0,"profit_factor":.0,"win_rate":.0};b=evaluate_portfolio_fn(e,a,latency_mode="500ms")if e else{"trades":0,"total_pnl":.0,"profit_factor":.0,"win_rate":.0};return{"label":label,"train":{"trades":d["trades"],"pnl":d["total_pnl"],"pf":d["profit_factor"],"wr":d["win_rate"]},"val":{"trades":c["trades"],"pnl":c["total_pnl"],"pf":c["profit_factor"],"wr":c["win_rate"]},"sealed_holdout":{"trades":b["trades"],"pnl":b["total_pnl"],"pf":b["profit_factor"],"wr":b["win_rate"]}}
 d=[_run_var("BASELINE_15M_CASCADE_TAKER_90_480",{},(tr_15,vl_15,ho_15)),_run_var("KEMNA_VORST_TWAP_BRIDGE_45_480",{"min_tte_15m":45.,"use_kemna_vorst":True},(tr_15,vl_15,ho_15)),_run_var("HYBRID_ZSPLIT_1.15_UNSHIELDED_MAKER",{"hybrid_z_split":True,"z_taker_cut":1.15,"use_complement_shield":False,"include_maker_rebate":False},(tr_15,vl_15,ho_15)),_run_var("HYBRID_ZSPLIT_1.15_COMP_SHIELD_NO_REBATE",{"hybrid_z_split":True,"z_taker_cut":1.15,"use_complement_shield":True,"include_maker_rebate":False},(tr_15,vl_15,ho_15)),_run_var("HYBRID_ZSPLIT_1.15_COMP_SHIELD_WITH_20PCT_REBATE",{"hybrid_z_split":True,"z_taker_cut":1.15,"use_complement_shield":True,"include_maker_rebate":True},(tr_15,vl_15,ho_15)),_run_var("HYBRID_ZSPLIT_1.25_COMP_SHIELD_WITH_20PCT_REBATE",{"hybrid_z_split":True,"z_taker_cut":1.25,"use_complement_shield":True,"include_maker_rebate":True},(tr_15,vl_15,ho_15)),_run_var("STUDENT_T_DF4_UNIT_VAR_JVM_1.15",{"v395_df":4.,"v395_jump_vol_mult":1.15,"use_kemna_vorst":True},(tr_15,vl_15,ho_15)),_run_var("COINBASE_250MS_IMPULSE_VETO_2.5BPS",{"cb_250ms_veto_bps":-2.5},(tr_15,vl_15,ho_15))];f=[]
 if k:
  for m,l in[(("BTC",),"BTC_5M_ONLY"),(("SOL",),"SOL_5M_CANARY"),(("BTC","ETH","SOL"),"ALL_CRYPTO_5M")]:f.append(_run_var(l,{"assets":m,"horizons":("5m",),"min_z":.8,"use_kemna_vorst":True},(t,s,q)))
 return{"counts":{"subhourly_15m_total":len(i),"subhourly_5m_total":len(k)},"splits_15m":{"train":len(tr_15),"val":len(vl_15),"sealed_holdout":len(ho_15)},"splits_5m":{"train":len(t),"val":len(s),"sealed_holdout":len(q)},"brier_calibration_selected_on_dev":a,"brier_calibration_grid":g,"ablations_15m":d,"ablations_5m":f}
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
 g=shock.get("pre_shock_features_t0")or{};tf=(g.get(target_token)or{})if isinstance(g,dict)else{};f=is_real_polygon_ctf_token(token_id or tf.get("token_id"));e=(shock.get("shock_source")in("BOUNDARY_LOCK","EXP316_TRACK_A_CONVERGENCE")or shock.get("sleeve")=="SLEEVE_3_STRIKE_CONVERGENCE");c=bool("fee_metadata"in shock or"shock_ofi"in shock or str(shock.get("event_id")or"").startswith("SHOCK_"));missing=[];b=bool(float(tf.get("best_ask")or.0)>=.995 and float(tf.get("ask_size_l1")or.0)<=.0 and tf.get("age_bid_ms")is not None)
 if tf.get("age_ask_ms")is None and not e and not b:missing.append("age_ask_ms")
 if shock.get("shock_ofi")is None and not e and c:missing.append("shock_ofi")
 if tf.get("obi_l1")is None and not e:missing.append("obi_l1")
 if shock.get("coinbase_spot")is None and shock.get("chainlink_proxy_spot")is None:missing.append("usd_venue_anchor")
 d=any(k in missing for k in("age_ask_ms","shock_ofi"));a=.0
 if f and missing:a=min(.06,.015*len(missing))
 return{"is_real_ctf_token":f,"complete":len(missing)==0,"hard_veto_live":bool(f and d),"missing_fields":missing,"uncertainty_haircut":round(a,4)}
def estimate_quote_survival_and_net_alpha(p_win,ask_price,limit_price,p_max,fee_rate=.07,fee_exponent=1.,clob_rtt_ms=240.,age_ask_ms=None,spread=.01,l1_depth_usd=35.,obi_l1=.0,shock_ofi=.8,notional_usd=14.,target_exit_px=.965,expected_salvage_net=.36,uncertainty_haircut=.0,opp_cost_bps=12.,survival_params=None):
 m=round(min(float(limit_price),float(p_max)),4)
 if ask_price<=.0 or m<ask_price-1e-6 or notional_usd<=.0:return{"p_fill":.0,"ev_net_usd":.0,"ev_given_fill_usd":.0,"eff_limit_px":m,"eligible":False}
 w=survival_params or{};b0=float(w.get("b0",-.35));s=float(w.get("b_impr_per_cent",.72));v=float(w.get("b_rtt_per_100ms",-.38));o=float(w.get("b_log_depth",.34));u=float(w.get("b_age_stale",.3));t=float(w.get("b_obi",-.35));d=max(.0,(m-float(ask_price))*1e2);n=max(.05,float(clob_rtt_ms)/1e2);k=math.log(max(1.,float(l1_depth_usd)/max(8.,float(notional_usd))))
 if age_ask_ms is None:a=-.35
 elif age_ask_ms<45.:a=-.6
 else:a=min(1.2,(float(age_ask_ms)-1e2)/350.)
 r=(b0+s*min(2.5,d)+v*n+o*k+u*a+t*float(obi_l1)-.15*max(.0,(float(spread)-.01)*1e2)-.2*max(.0,abs(float(shock_ofi))-.85));g=1./(1.+math.exp(-max(-12.,min(12.,r))));g=max(.02,min(.98,g));c=min(m,float(ask_price)+.35*max(.0,m-float(ask_price)));q=compute_category_taker_fee_per_share(c,fee_rate,fee_exponent);i=c+q;l=max(.01,min(.995,float(p_win)-float(uncertainty_haircut)));e=l*float(target_exit_px)+(1.-l)*float(expected_salvage_net);h=e-i;p=float(notional_usd)/max(.01,c);b=p*h;f=float(notional_usd)*(float(opp_cost_bps)/1e4);j=g*b-(1.-g)*f;return{"p_fill":round(g,4),"expected_exec_px":round(c,4),"eff_cost_ps":round(i,4),"net_edge_ps":round(h,4),"ev_given_fill_usd":round(b,4),"ev_net_usd":round(j,4),"eff_limit_px":m,"eligible":bool(j>.0 and h>.0)}
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
 asks_y=_norm_asks(asks_yes_raw);asks_n=_norm_asks(asks_no_raw)
 if not asks_y or not asks_n:return{"filled":False,"reason":"EMPTY_SIDE_BOOK"}
 k=asks_y[0][0]*asks_y[0][1];j=asks_n[0][0]*asks_n[0][1];f=round(min(k,j),2);best_y,best_n=asks_y[0][0],asks_n[0][0];d=(compute_category_taker_fee_per_share(best_y,fee_rate,fee_exponent)+compute_category_taker_fee_per_share(best_n,fee_rate,fee_exponent))
 if(best_y+best_n+d)>max_complete_set_cost+.015:return{"filled":False,"reason":"NO_UNDERROUND","best_pair_net":round(best_y+best_n+d,5)}
 m=sum(s for p,s in asks_y if p<=best_y+.02);l=sum(s for p,s in asks_n if p<=best_n+.02);c=int(math.floor(float(target_budget_usd)/max(.1,best_y+best_n)));t=int(min(c,math.floor(m),math.floor(l)))
 if t<int(min_shares):return{"filled":False,"reason":"INSUFFICIENT_EQUAL_SHARES","l1_usd":f}
 def _walk_shares(levels,q_req):
  d=q_req;b=.0;a=.0
  for px,sz in levels:
   f=min(d,sz);b+=f*px;a=max(a,px);d-=f
   if d<=1e-6:break
  if d>1e-5:return None
  e=b/q_req;c=compute_category_taker_fee_per_share(e,fee_rate,fee_exponent);return e,c,a
 wy=_walk_shares(asks_y,float(t));wn=_walk_shares(asks_n,float(t))
 if wy is None or wn is None:return{"filled":False,"reason":"DEPTH_WALK_SHORTFALL","l1_usd":f}
 o,i,r=wy;n,h,q=wn;b=o+i+n+h
 if b>max_complete_set_cost+1e-6:return{"filled":False,"reason":"NET_COST_ABOVE_CAP","box_cost_net":round(b,5),"l1_usd":f}
 e=t*(o+n);g=t*(i+h);a=t*(1.-b);return{"filled":True,"market_id":str(market_id),"condition_id":str(condition_id),"yes_token":str(yes_token),"no_token":str(no_token),"shares":t,"vwap":round(o+n,5),"eff_px":round(b,5),"box_cost_net":round(b,5),"riskless_floor_per_pair":round(1.-b,5),"guaranteed_min_profit_usd":round(a,4),"spent_usd":round(e,2),"fee_usd":round(g,4),"limit_yes":round(r,4),"limit_no":round(q,4),"avail_yes_shares":round(m,2),"avail_no_shares":round(l,2),"l1_usd":f}
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
 c=_global_positions_shm_path()
 if not c.exists():return{"daemons":{}}
 try:
  b=json.loads(c.read_text(encoding="utf-8"))
  if not isinstance(b,dict):return{"daemons":{}}
  daemons=b.get("daemons")or{};now=time.time();a={k:v for k,v in daemons.items()if isinstance(v,dict)and(now-float(v.get("updated_ts")or.0))<=max_age_sec};return{"daemons":a}
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
 px=float(price_hint or.0)
 if(.0<px<.04)or px>=.96:return.001
 return.01
def compute_capital_velocity_ev(net_edge_per_share,expected_hold_seconds=3e2,*,fill_prob=1.,early_recycle_factor=1.,net_cost_per_share=1.):b=max(.05,float(net_cost_per_share or 1.));a=max(10.,float(expected_hold_seconds or 3e2)*max(.1,float(early_recycle_factor or 1.)));fp=max(.01,min(1.,float(fill_prob if fill_prob is not None else 1.)));return(float(net_edge_per_share or.0)/b)*fp/a
def compute_smart_maker_bid(best_bid,best_ask,max_cap_px=None,min_floor_px=.001,obi_l1=.0,tick_size=None,*,max_ceiling=None,max_bid_px=None,min_floor=None):
 def _num_val(v,dflt=.0):return float(v)if(isinstance(v,(int,float))and not isinstance(v,bool)and math.isfinite(v))else dflt
 d=_num_val(max_cap_px if max_cap_px is not None else(max_ceiling if max_ceiling is not None else(max_bid_px if max_bid_px is not None else.99)),.99);c=_num_val(min_floor if min_floor is not None else min_floor_px,.001);ba=_num_val(best_ask,.0);bb=_num_val(best_bid,.0);i=_num_val(obi_l1,.0);k=_num_val(tick_size,.0);g=ba if ba>.0 else d;j=k if k>.0 else infer_polymarket_tick_size(g);f=3 if j<.009 else 2;a=(ba-j)if ba>j else d;b=min(d,a);l=round(math.floor((b+1e-9)/j)*j,f)
 if l<c-1e-9 or l<=.0:return None,False
 if bb>.0:
  e=(ba-bb)if ba>bb else.0;h=round(bb+j,f)
  if e>=(2.*j-1e-9)and h<=l+1e-9:return min(l,h),True
  if bb<=l+1e-9:
   if.0<e<=(j+1e-9)and i<-.35:return None,False
   return round(min(l,bb),f),False
 return l,True
def _walk_bid_levels_net(bids,target_shares,fee_rate=.0,fee_exp=1.):
 h=[];a=.0
 for r in bids or():
  if not isinstance(r,dict):continue
  try:px=float(r.get("price")or.0);sz=float(r.get("size")or.0)
  except(TypeError,ValueError):continue
  if px>.0 and sz>.0:h.append((px,sz));a+=sz
 if not h or target_shares<=.0 or a+1e-9<target_shares:return False,.0,.0,.0,a
 h.sort(key=lambda x:-x[0]);e=float(target_shares);b=.0;d=.0;c=h[0][0]
 for px,sz in h:
  g=min(e,sz)
  if g<=.0:break
  f=compute_category_taker_fee_per_share(px,fee_rate=fee_rate,fee_exponent=fee_exp);b+=g*px;d+=g*max(.0,px-f);c=px;e-=g
  if e<=1e-7:break
 if e>1e-5:return False,.0,.0,.0,a
 return True,b/target_shares,d/target_shares,c,a
def walk_dual_leg_overround_bids(bids_a,bids_b,target_shares,fee_rate_a=.0,fee_exp_a=1.,fee_rate_b=.0,fee_exp_b=1.,min_depth_mult=1.25):sh=float(target_shares or.0);k,g,i,c,f=_walk_bid_levels_net(bids_a,sh,fee_rate_a,fee_exp_a);j,e,h,b,d=_walk_bid_levels_net(bids_b,sh,fee_rate_b,fee_exp_b);a=k and j and f>=sh*min_depth_mult and d>=sh*min_depth_mult;return{"fillable":bool(a and c>.0 and b>.0),"gross_sum_per_share":round(g+e,6),"net_sum_per_share":round(i+h,6),"min_px_a":round(c,4),"min_px_b":round(b,4),"depth_a":round(f,4),"depth_b":round(d,4)}
def evaluate_guarded_complement_merge(*,rem_shares,opp_ask,opp_ask_size=.0,opp_ask_size_l1=None,curr_maker_tp_px=None,fee_rate=.07,fee_exponent=1.,min_net_proceeds_ps=.982,max_opp_ask=.015,min_marketable_usd=1.):
 if opp_ask_size_l1 is not None and opp_ask_size<=.0:opp_ask_size=float(opp_ask_size_l1)
 if curr_maker_tp_px is not None:min_net_proceeds_ps=max(float(min_net_proceeds_ps),float(curr_maker_tp_px)+.002)
 sh=float(rem_shares or.0);j=float(opp_ask or.0)
 if sh<5. or not(.001<=j<=float(max_opp_ask)):return{"approved":False,"reason":"OUT_OF_OPP_PRICE_BAND_OR_SUB_LOT"}
 b=math.ceil((float(min_marketable_usd)/j)*1e2)/1e2;g=max(sh,b);a=max(.0,round(g-sh,4))
 if opp_ask_size>.0 and float(opp_ask_size)+1e-6<g:return{"approved":False,"reason":"INSUFFICIENT_OPP_ASK_DEPTH","req_opp_shares":g}
 h=compute_category_taker_fee_per_share(j,fee_rate=fee_rate,fee_exponent=fee_exponent);f=g*(j+h);d=sh*1.;c=d-f;e=c/sh;i=infer_polymarket_tick_size(j)
 if e<float(min_net_proceeds_ps):return{"approved":False,"reason":"OVERBUY_DILUTION_BELOW_MAKER_98_HURDLE","net_proceeds_ps":round(e,5),"req_opp_shares":round(g,2),"excess_unmerged_shares":a}
 return{"approved":True,"opp_ask":round(j,4),"tick_size":f"{i:.3f}"if i<.009 else f"{i:.2f}","req_opp_shares":round(g,2),"merge_pairs":round(sh,2),"excess_unmerged_shares":a,"total_opp_cost_usd":round(f,4),"net_proceeds_ps":round(e,5),"atomic_sequence":("FAK_BUY_OPP","CONFIRM_OPP_FILL","CANCEL_RESTING_MAKER_TP","MERGE_CTF_POSITIONS")}
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
  p=str(s.get("shock_direction")or"BUY").upper();r="UP"if p in("BUY","UP")else"DOWN";v=(s.get("pre_shock_features_t0")or{}).get(r)or{};l=float(v.get("best_ask")or v.get("vwap_$25")or v.get("effective_price_$25")or.7);l=max(.05,min(.95,l));d=abs(float(s.get("candle_distance_pct")or.0));u=max(30.,float(s.get("seconds_to_expiry")or 3e2));o=str(s.get("asset")or"BTC").upper();g=float(s.get("candle_sigma")or.0);hz=str(s.get("horizon")or"").lower();k=(g*(2. if"15m"in hz else(math.sqrt(12.)if hz in("5m","5min","300s")or"-5m"in hz else 1.))if g>.0 else(.005 if o=="BTC"else(.0068 if o=="ETH"else.009)));f=max(.00025,k*math.sqrt(u/3600.));t=min(1.,abs(float(s.get("shock_ofi")if s.get("shock_ofi")is not None else.85)));n=(d/1e2)/f+.35*t;m=.5*(1.+math.erf(n/math.sqrt(2.)));j=compute_category_taker_fee_per_share(l,.07,1.);e=m*.98+(1.-m)*.36;a=(e-l-j)/(l+j);i=float(v.get("age_ask_ms")if v.get("age_ask_ms")is not None else 3e2);h=1.15 if i>=250. else 1.;c=.015 if o=="BTC"else(.008 if o=="ETH"else.0);b=a*h+c
  if active_positions:q=compute_capital_efficiency_utility({"asset":o,"side":r,"expiry_ts":s.get("candle_expiry_ts")or s.get("expiry_ts")or.0,"strike":s.get("candle_open_spot")or.0,"net_edge":max(.0,e-l-j),"ask_vwap":l,"p_model":m,"tte_sec":u},active_global_positions=active_positions);b+=float(q.get("corridor_completion_bonus")or.0)-float(q.get("corr_penalty")or.0)
  return round(b,6),n
 return sorted(shocks,key=_score_shock,reverse=True)
# ======================================================================================
# [05/21] MODULE: src/polymarket_research/weather_metar_engine.py
# PURPOSE: Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import logging;import math;import re;import time;import urllib.parse;import urllib.request;from dataclasses import dataclass,field;from datetime import date,datetime,timedelta,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;logger=logging.getLogger("WeatherMetarEngine");GAMMA_API_URL="https://gamma-api.polymarket.com";CLOB_API_URL="https://clob.polymarket.com";AWC_METAR_URL="https://aviationweather.gov/api/data/metar";AWC_STATION_URL="https://aviationweather.gov/api/data/stationinfo";IEM_ASOS_URL="https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py";OPEN_METEO_ENSEMBLE_URL="https://ensemble-api.open-meteo.com/v1/ensemble";OPEN_METEO_FORECAST_URL="https://api.open-meteo.com/v1/forecast";OPEN_METEO_HIST_FORECAST_URL="https://historical-forecast-api.open-meteo.com/v1/forecast";STATION_CATALOG={"RJTT":(35.5523,139.7798,"Asia/Tokyo","Tokyo"),"EGLC":(51.5053,.0553,"Europe/London","London"),"ZSPD":(31.1434,121.8052,"Asia/Shanghai","Shanghai"),"ZSQD":(36.3667,120.0944,"Asia/Shanghai","Qingdao"),"WMKK":(2.7456,101.7099,"Asia/Kuala_Lumpur","Kuala Lumpur"),"RCSS":(25.0694,121.5525,"Asia/Taipei","Taipei"),"EDDM":(48.3538,11.7861,"Europe/Berlin","Munich"),"LFPB":(48.9694,2.4414,"Europe/Paris","Paris"),"ZUUU":(30.5785,103.9471,"Asia/Shanghai","Chengdu"),"SBGR":(-23.4356,-46.4731,"America/Sao_Paulo","Sao Paulo"),"LEMD":(40.4719,-3.5626,"Europe/Madrid","Madrid"),"ZHHH":(30.7838,114.2081,"Asia/Shanghai","Wuhan"),"EHAM":(52.3086,4.7639,"Europe/Amsterdam","Amsterdam"),"EPWA":(52.1657,20.9671,"Europe/Warsaw","Warsaw"),"WSSS":(1.3502,103.994,"Asia/Singapore","Singapore"),"ZBAA":(40.0801,116.5846,"Asia/Shanghai","Beijing"),"ZUCK":(29.7192,106.6417,"Asia/Shanghai","Chongqing"),"LTFM":(41.2753,28.7519,"Europe/Istanbul","Istanbul"),"KMIA":(25.7959,-80.287,"America/New_York","Miami"),"OPKC":(24.9065,67.1608,"Asia/Karachi","Karachi"),"KLGA":(40.7769,-73.874,"America/New_York","NYC"),"RKSI":(37.4602,126.4407,"Asia/Seoul","Seoul"),"LLBG":(32.0114,34.8867,"Asia/Jerusalem","Tel Aviv"),"ZGGG":(23.3924,113.2988,"Asia/Shanghai","Guangzhou"),"OEJN":(21.6796,39.1565,"Asia/Riyadh","Jeddah"),"VILK":(26.7606,80.8893,"Asia/Kolkata","Lucknow"),"ZGSZ":(22.6393,113.8107,"Asia/Shanghai","Shenzhen"),"LIMC":(45.6306,8.7281,"Europe/Rome","Milan"),"RKPK":(35.1795,128.9382,"Asia/Seoul","Busan"),"LTAC":(40.1281,32.9951,"Europe/Istanbul","Ankara"),"SAEZ":(-34.8222,-58.5358,"America/Argentina/Buenos_Aires","Buenos Aires"),"KSEA":(47.4502,-122.3088,"America/Los_Angeles","Seattle"),"KDAL":(32.8471,-96.8518,"America/Chicago","Dallas"),"NZWN":(-41.3272,174.8053,"Pacific/Auckland","Wellington"),"KSFO":(37.6213,-122.379,"America/Los_Angeles","San Francisco"),"KORD":(41.9742,-87.9073,"America/Chicago","Chicago"),"MMMX":(19.4363,-99.0721,"America/Mexico_City","Mexico City"),"CYYZ":(43.6777,-79.6248,"America/Toronto","Toronto"),"RPLL":(14.5086,121.0194,"Asia/Manila","Manila"),"EFHK":(60.3172,24.9633,"Europe/Helsinki","Helsinki"),"KATL":(33.6407,-84.4277,"America/New_York","Atlanta"),"KHOU":(29.6454,-95.2789,"America/Chicago","Houston"),"KDEN":(39.8561,-104.6737,"America/Denver","Denver"),"UUWW":(55.5915,37.2615,"Europe/Moscow","Moscow"),"MPMG":(8.9733,-79.5556,"America/Panama","Panama City"),"KAUS":(30.1945,-97.6699,"America/Chicago","Austin"),"KLAX":(33.9425,-118.4081,"America/Los_Angeles","Los Angeles"),"FACT":(-33.9648,18.6017,"Africa/Johannesburg","Cape Town"),"HKO":(22.3019,114.1742,"Asia/Hong_Kong","Hong Kong")};HKO_1MIN_CSV_URL="https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature.csv";HKO_MAXMIN_CSV_URL="https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_since_midnight_maxmin.csv";HKO_RHRREAD_URL="https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en";_T_REMARK_RE=re.compile(r"(?:^|\s)T([01])(\d{3})(?:\d{4}|////)(?=\s|$)");_BODY_TEMP_RE=re.compile(r"(?:^|\s)(M?\d{2})/(?:M?\d{2}|//)(?=\s|$)");_METAR_TS_RE=re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b");_CONVECTIVE_WX_RE=re.compile(r"(?:^|\s)(?:[-+]|VC)?(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)*\b" r"|(?:FEW|SCT|BKN|OVC)\d{3}(?:CB|TCU)\b" r"|\b(?:CB|TCU|RAB\d{2,4}|TSB\d{2,4}|P\d{4})\b");_AWC_ICAO_RE=re.compile(r"aviationweather\.gov/api/data/metar\?ids=([A-Z0-9]{4})",re.IGNORECASE);_NOAA_ICAO_RE=re.compile(r"weather\.gov/wrh/timeseries\?site=([A-Z0-9]{4})",re.IGNORECASE);_PAREN_ICAO_RE=re.compile(r"\(([A-Z]{4})\)");_SERIES_TO_ICAO={"tokyo-daily-weather":"RJTT","tokyo-daily-lowest-temperature":"RJTT","london-daily-weather":"EGLC","london-daily-lowest-temperature":"EGLC","shanghai-daily-weather":"ZSPD","shanghai-daily-lowest-temperature":"ZSPD","chengdu-daily-weather":"ZUUU","chengdu-daily-lowest-temperature":"ZUUU","beijing-daily-weather":"ZBAA","beijing-daily-lowest-temperature":"ZBAA","wuhan-daily-weather":"ZHHH","wuhan-daily-lowest-temperature":"ZHHH","chongqing-daily-weather":"ZUCK","chongqing-daily-lowest-temperature":"ZUCK","guangzhou-daily-weather":"ZGGG","guangzhou-daily-lowest-temperature":"ZGGG","shenzhen-daily-weather":"ZGSZ","shenzhen-daily-lowest-temperature":"ZGSZ","qingdao-daily-weather":"ZSQD","qingdao-daily-lowest-temperature":"ZSQD","paris-daily-weather":"LFPB","paris-daily-lowest-temperature":"LFPB","munich-daily-weather":"EDDM","munich-daily-lowest-temperature":"EDDM","miami-daily-weather":"KMIA","miami-daily-lowest-temperature":"KMIA","nyc-daily-weather":"KLGA","nyc-daily-lowest-temperature":"KLGA","houston-daily-weather":"KHOU","houston-daily-lowest-temperature":"KHOU","austin-daily-weather":"KAUS","austin-daily-lowest-temperature":"KAUS","los-angeles-daily-weather":"KLAX","los-angeles-daily-lowest-temperature":"KLAX","seoul-daily-weather":"RKSI","seoul-daily-lowest-temperature":"RKSI","busan-daily-weather":"RKPK","busan-daily-lowest-temperature":"RKPK","chicago-daily-weather":"KORD","chicago-daily-lowest-temperature":"KORD","seattle-daily-weather":"KSEA","seattle-daily-lowest-temperature":"KSEA","dallas-daily-weather":"KDAL","dallas-daily-lowest-temperature":"KDAL","madrid-daily-weather":"LEMD","madrid-daily-lowest-temperature":"LEMD","amsterdam-daily-weather":"EHAM","amsterdam-daily-lowest-temperature":"EHAM","taipei-daily-weather":"RCSS","taipei-daily-lowest-temperature":"RCSS","singapore-daily-weather":"WSSS","singapore-daily-lowest-temperature":"WSSS","hong-kong-daily-weather":"HKO","hong-kong-daily-lowest-temperature":"HKO","wellington-daily-weather":"NZWN","wellington-daily-lowest-temperature":"NZWN","warsaw-daily-weather":"EPWA","warsaw-daily-lowest-temperature":"EPWA","buenos-aires-daily-weather":"SAEZ","buenos-aires-daily-lowest-temperature":"SAEZ","helsinki-daily-weather":"EFHK","helsinki-daily-lowest-temperature":"EFHK","denver-daily-weather":"KDEN","denver-daily-lowest-temperature":"KDEN","toronto-daily-weather":"CYYZ","toronto-daily-lowest-temperature":"CYYZ","mexico-city-daily-weather":"MMMX","mexico-city-daily-lowest-temperature":"MMMX","tel-aviv-daily-weather":"LLBG","tel-aviv-daily-lowest-temperature":"LLBG","istanbul-daily-weather":"LTFM","istanbul-daily-lowest-temperature":"LTFM","sao-paulo-daily-weather":"SBGR","sao-paulo-daily-lowest-temperature":"SBGR","manila-daily-weather":"RPLL","manila-daily-lowest-temperature":"RPLL","atlanta-daily-weather":"KATL","atlanta-daily-lowest-temperature":"KATL","san-francisco-daily-weather":"KSFO","san-francisco-daily-lowest-temperature":"KSFO","panama-daily-weather":"MPMG","panama-daily-lowest-temperature":"MPMG","milan-daily-weather":"LIMC","milan-daily-lowest-temperature":"LIMC","lucknow-daily-weather":"VILK","lucknow-daily-lowest-temperature":"VILK","karachi-daily-weather":"OPKC","karachi-daily-lowest-temperature":"OPKC","jeddah-daily-weather":"OEJN","jeddah-daily-lowest-temperature":"OEJN","ankara-daily-weather":"LTAC","ankara-daily-lowest-temperature":"LTAC","kuala-lumpur-daily-weather":"WMKK","kuala-lumpur-daily-lowest-temperature":"WMKK","moscow-daily-weather":"UUWW","moscow-daily-lowest-temperature":"UUWW","cape-town-daily-weather":"FACT","cape-town-daily-lowest-temperature":"FACT"}
HIGH_VOLUME_WEATHER_SERIES=("hong-kong-daily-weather","hong-kong-daily-lowest-temperature","atlanta-daily-weather","atlanta-daily-lowest-temperature","san-francisco-daily-weather","san-francisco-daily-lowest-temperature","seattle-daily-weather","seattle-daily-lowest-temperature","amsterdam-daily-weather","amsterdam-daily-lowest-temperature","panama-daily-weather","manila-daily-weather","mexico-city-daily-weather","munich-daily-weather","milan-daily-weather","istanbul-daily-weather","lucknow-daily-weather","tel-aviv-daily-weather","karachi-daily-weather","sao-paulo-daily-weather","jeddah-daily-weather","ankara-daily-weather","busan-daily-weather","cape-town-daily-weather","cape-town-daily-lowest-temperature","qingdao-daily-weather","kuala-lumpur-daily-weather","moscow-daily-weather","chengdu-daily-weather","beijing-daily-weather","seoul-daily-weather","seoul-daily-lowest-temperature","shanghai-daily-weather","shanghai-daily-lowest-temperature","tokyo-daily-weather","tokyo-daily-lowest-temperature","wuhan-daily-weather","chongqing-daily-weather","guangzhou-daily-weather","shenzhen-daily-weather","taipei-daily-weather","singapore-daily-weather","nyc-daily-weather","nyc-daily-lowest-temperature","chicago-daily-weather","chicago-daily-lowest-temperature","london-daily-weather","london-daily-lowest-temperature","miami-daily-weather","miami-daily-lowest-temperature","austin-daily-weather","austin-daily-lowest-temperature","los-angeles-daily-weather","los-angeles-daily-lowest-temperature","houston-daily-weather","houston-daily-lowest-temperature","dallas-daily-weather","dallas-daily-lowest-temperature","wellington-daily-weather","wellington-daily-lowest-temperature","warsaw-daily-weather","warsaw-daily-lowest-temperature","buenos-aires-daily-weather","helsinki-daily-weather","denver-daily-weather","denver-daily-lowest-temperature","toronto-daily-weather","toronto-daily-lowest-temperature","paris-daily-weather","paris-daily-lowest-temperature","madrid-daily-weather");_MONTH_MAP={"january":1,"jan":1,"february":2,"feb":2,"march":3,"mar":3,"april":4,"apr":4,"may":5,"june":6,"jun":6,"july":7,"jul":7,"august":8,"aug":8,"september":9,"sep":9,"sept":9,"october":10,"oct":10,"november":11,"nov":11,"december":12,"dec":12}
@dataclass
class WeatherBucket:
 market_id:str;condition_id:str;label:str;question:str;yes_token:str;no_token:str;unit:str;low_bound:float;high_bound:float;outcome_yes_resolved=None;fee_rate=.0;fee_exponent=1.;neg_risk=None
 def contains_rounded(self,rounded_int):return self.low_bound<=rounded_int<=self.high_bound
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
 if b:lo,hi=int(b.group(1)),int(b.group(2));return e,float(min(lo,hi)),float(max(lo,hi))
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
 w=str(ev.get("title")or"");tl=w.lower()
 if"highest temperature in"in tl:g="HIGH"
 elif"lowest temperature in"in tl:g="LOW"
 else:return None
 A=ev.get("markets")or[]
 if len(A)<4:return None
 k=ev.get("series")or[];u=str(k[0].get("slug")if k else(ev.get("seriesSlug")or series_slug_hint or""));z=str(A[0].get("description")or ev.get("description")or"");c=None;t=_AWC_ICAO_RE.search(z)
 if t and"SPECI"in z:c=t.group(1).upper()
 elif"weather.gov.hk"in z.lower()and"hong kong observatory"in z.lower():c="HKO"
 elif"routine (metar)"in z.lower()or"speci"in z.lower():
  j=_PAREN_ICAO_RE.search(z)
  if j and j.group(1).upper()in STATION_CATALOG:c=j.group(1).upper()
 elif allow_historical_same_station:
  s=_NOAA_ICAO_RE.search(z);v=_PAREN_ICAO_RE.search(z)
  if s and s.group(1).upper()in STATION_CATALOG:c=s.group(1).upper()
  elif v and v.group(1).upper()in STATION_CATALOG:c=v.group(1).upper()
  elif u in _SERIES_TO_ICAO:c=_SERIES_TO_ICAO[u]
 if not c or c not in STATION_CATALOG:return None
 D,C,q,y=STATION_CATALOG[c];p=str(ev.get("endDate")or A[0].get("endDate")or"");o=parse_obs_date_from_event(w,z,p)
 if o is None:return None
 d=str(A[0].get("feeType")or"zero_fees");buckets=[]
 for m in A:
  B=str(m.get("groupItemTitle")or m.get("question")or"");r=parse_bucket_bounds(B)
  if not r:continue
  x,lo,hi=r;f=m.get("clobTokenIds")
  if isinstance(f,str):
   try:f=json.loads(f)
   except Exception:f=[]
  if not f or len(f)<2:continue
  a=None
  if m.get("closed"):
   op=m.get("outcomePrices")
   if isinstance(op,str):
    try:op=json.loads(op)
    except Exception:op=None
   if isinstance(op,list)and len(op)>=2:
    try:
     if float(op[0])>=.99:a=1
     elif float(op[1])>=.99:a=0
    except Exception:pass
  h=m.get("feeSchedule")if isinstance(m.get("feeSchedule"),dict)else{};e=bool(m.get("feesEnabled",False));n=float(h.get("rate")or.0);i=n if(e and n>.0)else.0;l=float(h.get("exponent")or 1.);buckets.append(WeatherBucket(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),label=B,question=str(m.get("question")or B),yes_token=str(f[0]),no_token=str(f[1]),unit=x,low_bound=lo,high_bound=hi,outcome_yes_resolved=a,fee_rate=i,fee_exponent=l))
 if len(buckets)<4:return None
 buckets.sort(key=lambda b:(b.low_bound,b.high_bound))
 if any(b.fee_rate>.0 for b in buckets):d="fees_enabled"
 return WeatherEventSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),series_slug=u,title=w,icao=c,city=y,lat=D,lon=C,tz_name=q,obs_date=o,metric=g,unit=buckets[0].unit,fee_type=d,end_date_iso=p,buckets=buckets)
def parse_hko_csv_observations(raw_1min_csv,raw_maxmin_csv,obs_date,tz_name="Asia/Hong_Kong"):
 tz=ZoneInfo(tz_name);b=datetime(obs_date.year,obs_date.month,obs_date.day,0,0,tzinfo=tz);f=None;a=None;d=None;c=None
 for ln in(raw_1min_csv or"").splitlines():
  e=[p.strip()for p in ln.split(",")]
  if len(e)>=3 and e[1]in("HK Observatory","Hong Kong Observatory")and len(e[0])>=12 and e[0][:12].isdigit():
   try:
    g=datetime.strptime(e[0][:12],"%Y%m%d%H%M").replace(tzinfo=tz)
    if g.date()==obs_date:f=float(e[2]);a=g
   except ValueError:pass
 for ln in(raw_maxmin_csv or"").splitlines():
  e=[p.strip()for p in ln.split(",")]
  if len(e)>=4 and e[1]in("HK Observatory","Hong Kong Observatory")and len(e[0])>=12 and e[0][:12].isdigit():
   try:
    g=datetime.strptime(e[0][:12],"%Y%m%d%H%M").replace(tzinfo=tz)
    if g.date()==obs_date:
     if e[2]and e[2].upper()!="N/A":d=float(e[2])
     if e[3]and e[3].upper()!="N/A":c=float(e[3])
     if a is None:a=g
   except ValueError:pass
 if a is None:return[]
 k=[]
 if c is not None:j=min(a,b+timedelta(minutes=1));k.append(MetarObservation("HKO",j.astimezone(timezone.utc),j,c,True,f"HKO_MIN {c:.1f}C"))
 if d is not None:i=min(a,b+timedelta(minutes=2));k.append(MetarObservation("HKO",i.astimezone(timezone.utc),i,d,True,f"HKO_MAX {d:.1f}C"))
 h=f if f is not None else(d if d is not None else c)
 if h is not None:k.append(MetarObservation("HKO",a.astimezone(timezone.utc),a,h,True,f"HKO_1M {h:.1f}C"))
 k.sort(key=lambda o:o.utc_dt);return k
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
 tz=ZoneInfo(tz_name);d=datetime(obs_date.year,obs_date.month,obs_date.day,0,0,tzinfo=tz);e=d+timedelta(days=1);a=e.astimezone(timezone.utc)+timedelta(hours=3);k=datetime.now(timezone.utc);c=min(k,a);h=(k-d.astimezone(timezone.utc)).total_seconds()/86400.;obs_by_ts={}
 def _merge_metar(parsed_obs):
  b=int(parsed_obs.utc_dt.timestamp());a=obs_by_ts.get(b)
  if(a is None or parsed_obs.is_corrected or(not a.is_corrected and(parsed_obs.has_t_remark or not a.has_t_remark))):obs_by_ts[b]=parsed_obs
 if h<=13.5:
  r=c.strftime("%Y-%m-%dT%H:%M:%SZ");u=f"{AWC_METAR_URL}?ids={icao.upper()}&format=raw&date={r}&hours=36"
  try:
   m=urllib.request.Request(u,headers={"User-Agent":"DominusWeatherEngine/1.0"});g=urllib.request.urlopen(m,timeout=timeout).read().decode("utf-8",errors="ignore")
   for s in reversed(g.splitlines()):
    b=parse_metar_line(s,icao,c,tz_name)
    if b and b.local_dt.date()==obs_date:_merge_metar(b)
  except Exception as exc:pass
 if not obs_by_ts:
  j=d.astimezone(timezone.utc)-timedelta(hours=2);q=e.astimezone(timezone.utc)+timedelta(hours=2);f=icao.upper()[1:]if(len(icao)==4 and icao.upper().startswith("K"))else icao.upper();n=urllib.parse.urlencode({"station":f,"data":"metar","year1":j.year,"month1":j.month,"day1":j.day,"year2":q.year,"month2":q.month,"day2":q.day,"tz":"Etc/UTC","format":"onlycomma","latlon":"no","elev":"no","missing":"M","trace":"T","direct":"no","report_type":["3","4"]},doseq=True)
  try:
   m=urllib.request.Request(f"{IEM_ASOS_URL}?{n}",headers={"User-Agent":"DominusWeatherEngine/1.0"});i=urllib.request.urlopen(m,timeout=timeout+4.).read().decode("utf-8",errors="ignore")
   for t in i.splitlines()[1:]:
    p=t.split(",",2)
    if len(p)<3:continue
    try:l=datetime.strptime(p[1].strip(),"%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:continue
    b=parse_metar_line(p[2],icao,l,tz_name,explicit_utc_dt=l)
    if b and b.local_dt.date()==obs_date:_merge_metar(b)
  except Exception as exc:pass
 return sorted(obs_by_ts.values(),key=lambda o:o.utc_dt)
def compute_weather_probabilities(spec,eval_utc,metars_so_far,ensemble_hourly_c,forecast_sigma_base_c=1.15,bias_decay_tau_hr=6.,taf_extreme_c=None):
 tz=ZoneInfo(spec.tz_name);S=eval_utc.astimezone(tz);D=datetime(spec.obs_date.year,spec.obs_date.month,spec.obs_date.day,0,0,tzinfo=tz);H=D+timedelta(days=1);valid_obs=[o for o in metars_so_far if o.utc_dt<=eval_utc and o.local_dt.date()==spec.obs_date];W=len(valid_obs)>0;R=valid_obs[-1]if W else None
 if W:
  if spec.metric=="HIGH":e=max(o.temp_c for o in valid_obs)
  else:e=min(o.temp_c for o in valid_obs)
  k=celsius_to_market_int(e,spec.unit)
 else:e=None;k=None
 s=.0;j=bias_decay_tau_hr;h=False;c=False
 if R is not None:
  G=[o for o in valid_obs if(eval_utc-o.utc_dt).total_seconds()<=12600.][-3:];h=any(o.has_convective_precip for o in valid_obs if(eval_utc-o.utc_dt).total_seconds()<=7200.);K=S.hour+S.minute/60.;r=(spec.metric=="HIGH"and 9.<=K<=16.25 and e is not None and(e-R.temp_c)>=1.2)
  if ensemble_hourly_c and G:
   Q=[]
   for _e in G:
    P=int(round(_e.utc_dt.timestamp()/3600.)*3600);O=ensemble_hourly_c.get(P)
    if O:N=sum(O)/len(O);Q.append(_e.temp_c-N)
   if Q:
    Q.sort()
    if len(Q)==3:A=Q[1]
    else:A=sum(Q)/len(Q)
    s=max(-1.5,min(1.5,A))
    if spec.metric=="HIGH"and A<-.35 and(h or r):c=True;s=max(-.45,A*.2);j=min(bias_decay_tau_hr,1.2)
  elif h or r:c=spec.metric=="HIGH"
 rem_hour_ts=[];J=max(D,S.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1))
 while J<H:rem_hour_ts.append(int(J.astimezone(timezone.utc).timestamp()));J+=timedelta(hours=1)
 if S<H and not rem_hour_ts:rem_hour_ts.append(int(H.astimezone(timezone.utc).timestamp()))
 l=[len(ensemble_hourly_c[t])for t in rem_hour_ts if t in ensemble_hourly_c and ensemble_hourly_c[t]]
 if not l and ensemble_hourly_c:l=[len(v)for v in ensemble_hourly_c.values()if v]
 _d=min(l)if l else 0;Y=[-2.1,-1.5,-1.1,-.75,-.45,-.2,.0,.2,.45,.75,1.1,1.5,2.1];bucket_weights=[.0 for _ in spec.buckets];total_weight=.0;C=[];B=len(rem_hour_ts)
 if S>=H and k is not None:
  for X,b in enumerate(spec.buckets):bucket_weights[X]=1. if b.contains_rounded(k)else.0
  total_weight=1.
 elif _d>0 and B>0:
  M=forecast_sigma_base_c*min(1.,math.sqrt(max(1.,B)/10.))
  if _d>=15:f=max(.45,.55*M)
  else:f=max(.75,M)
  if c:f*=1.45
  for _c in range(_d):
   y=[]
   for _g in rem_hour_ts:
    _f=ensemble_hourly_c.get(_g)
    if not _f:continue
    v=_f[min(_c,len(_f)-1)];_b=max(.0,(_g-eval_utc.timestamp())/3600.);I=s*math.exp(-_b/max(.5,j));y.append(v+I)
   if not y:continue
   m=max(y)if spec.metric=="HIGH"else min(y)
   if taf_extreme_c is not None and math.isfinite(float(taf_extreme_c)):m=.85*m+.15*float(taf_extreme_c)
   C.append(m)
   for z in Y:
    w=math.exp(-.5*z*z);V=m+z*f
    if e is not None:F=max(e,V)if spec.metric=="HIGH"else min(e,V)
    else:F=V
    U=celsius_to_market_int(F,spec.unit)
    for _a,b in enumerate(spec.buckets):
     if b.contains_rounded(U):bucket_weights[_a]+=w;break
    total_weight+=w
 n=.0
 if len(C)>=4:Z=sorted(C);_i=Z[int(.25*(len(Z)-1))];_h=Z[int(.75*(len(Z)-1))];n=max(.0,_h-_i)
 if total_weight<=.0:probs=[1./len(spec.buckets)for _ in spec.buckets]
 else:probs=[max(.001,min(.998,w/total_weight))for w in bucket_weights];s_p=sum(probs);probs=[p/s_p for p in probs]
 a=False;d=.0;g=None;i=.0
 if W and R is not None and e is not None and k is not None:
  E=S.hour+S.minute/60.
  for X,b in enumerate(spec.buckets):
   if b.contains_rounded(k):g=X;i=probs[X];break
  if spec.metric=="HIGH":
   d=e-R.temp_c;L=17.5 if(h or c)else 15.75;T=(S.date()>spec.obs_date)or(S.date()==spec.obs_date and E>=L)
   if T and(S.date()>spec.obs_date or d>=.8)and i>=.88:a=True
  else:
   u=R.temp_c-e;d=u;x=(S.date()>spec.obs_date)or(S.date()==spec.obs_date and E>=22.5);q=(S.date()==spec.obs_date and 9.5<=E<22.5 and u>=2.5 and _d>=15 and bool(C)and min(C)>=(e+2.)and i>=.93)
   if(x and i>=.9 and(S.date()>spec.obs_date or u>=1.))or q:a=True
 return{"probs":probs,"has_obs":W,"obs_count":len(valid_obs),"latest_temp_c":R.temp_c if R else None,"running_ext_c":e,"running_ext_int":k,"bias_c":round(s,3),"convective_cold_pool":c,"ensemble_member_count":_d,"peak_iqr_c":round(n,3),"rem_hours_count":B,"is_solar_lock":a,"cooling_cushion_c":round(d,2),"locked_bucket_idx":g,"p_locked_bucket":round(i,4)}
def fetch_live_ensemble_hourly_sync(lat,lon,timeout=8.):
 b={};i=(f"{OPEN_METEO_ENSEMBLE_URL}?latitude={lat:.4f}&longitude={lon:.4f}&hourly=temperature_2m&models=icon_seamless,gfs_seamless&past_days=1&forecast_days=3&timeformat=unixtime")
 for h in range(2):
  try:
   j=urllib.request.Request(i,headers={"User-Agent":"DominusWeatherEngine/1.0"});r=json.loads(urllib.request.urlopen(j,timeout=timeout).read().decode("utf-8"));hourly=r.get("hourly")or{};o=hourly.get("time")or[];e=sorted(k for k in hourly.keys()if k.startswith("temperature_2m"));aligned_series=[]
   for k in e:
    s=hourly.get(k)or[]
    if len(s)<len(o):continue
    m=[];c=None;a=0
    for n in s[:len(o)]:
     if n is not None:c=float(n);m.append(c)
     elif c is not None:a+=1;m.append(c)
     else:a=len(o);break
    if len(m)==len(o)and a<=max(2,len(o)//10):aligned_series.append(m)
   for idx,ts in enumerate(o):
    q=[series[idx]for series in aligned_series]
    if q:b[int(ts)]=q
   if b:break
  except Exception as exc:
   if h==0:time.sleep(.45)
   else:pass
 l=f"{OPEN_METEO_FORECAST_URL}?latitude={lat:.4f}&longitude={lon:.4f}&hourly=temperature_2m&models=ecmwf_ifs025&past_days=1&forecast_days=3&timeformat=unixtime"
 try:
  j=urllib.request.Request(l,headers={"User-Agent":"DominusWeatherEngine/1.0"});g=json.loads(urllib.request.urlopen(j,timeout=timeout).read().decode("utf-8"));p=g.get("hourly")or{};d=p.get("time")or[];f=p.get("temperature_2m")or p.get("temperature_2m_ecmwf_ifs025")or[]
  for idx,ts in enumerate(d):
   if idx<len(f)and f[idx]is not None:v=float(f[idx]);b.setdefault(int(ts),[]).extend([v]*8)
 except Exception:pass
 return b
def fetch_historical_nwp_hourly_sync(lat,lon,start_date,end_date,timeout=10.):
 i=(f"{OPEN_METEO_HIST_FORECAST_URL}?latitude={lat:.4f}&longitude={lon:.4f}&start_date={start_date.isoformat()}&end_date={end_date.isoformat()}&hourly=temperature_2m&models=ecmwf_ifs025,gfs_seamless,icon_seamless&timeformat=unixtime");h=urllib.request.Request(i,headers={"User-Agent":"DominusWeatherEngine/1.0"});d=json.loads(urllib.request.urlopen(h,timeout=timeout).read().decode("utf-8"));hourly=d.get("hourly")or{};b=hourly.get("time")or[];a=sorted(k for k in hourly.keys()if k.startswith("temperature_2m"));g={}
 for f,ts in enumerate(b):
  c=[]
  for k in a:
   e=hourly[k]
   if f<len(e)and e[f]is not None:
    v=float(e[f])
    if"ecmwf"in k:c.extend([v,v])
    else:c.append(v)
  if c:g[int(ts)]=c
 return g
_TAF_TEMP_RE=re.compile(r"\bT([XN])(M?\d{2})/(\d{2})(\d{2})Z\b");AWC_TAF_URL="https://aviationweather.gov/api/data/taf";STATION_ROUTINE_RELEASE_MIN={"KLGA":(51,),"KORD":(51,),"KATL":(52,),"KDAL":(53,),"KHOU":(53,),"KMIA":(53,),"KSEA":(53,),"KSFO":(56,),"KDEN":(53,),"KAUS":(53,),"KLAX":(53,),"CYYZ":(0,),"EGLC":(20,50),"LFPB":(0,30),"EDDM":(20,50),"LIMC":(20,50),"EFHK":(20,50),"RJTT":(0,30),"RKSI":(0,30),"RKPK":(0,),"ZSPD":(0,),"ZGSZ":(0,),"RPLL":(0,),"LTAC":(20,50),"SAEZ":(0,),"NZWN":(0,30),"MMMX":(45,),"FACT":(0,30),"EHAM":(25,55),"MPMG":(0,),"LTFM":(20,50),"SBGR":(0,),"OPKC":(0,30),"VILK":(0,30),"OEJN":(0,),"LLBG":(20,50)}
def compute_adaptive_metar_poll_ttl(icao,metars_so_far=None,now_utc=None):
 if icao.upper()=="HKO":return 45.
 dt=now_utc or datetime.now(timezone.utc);c=dt.minute+dt.second/60.;a=list(STATION_ROUTINE_RELEASE_MIN.get(icao.upper(),()))
 if metars_so_far:
  b=sorted({o.utc_dt.minute for o in metars_so_far[-4:]})
  for rm in b:
   if rm not in a:a.append(rm)
 if not a:a=[0,51,53]
 for e in a:
  d=(c-float(e)+30.)%60.-30.
  if-1.<=d<=4.5:return 10.
 return 3e2
def parse_taf_temperature_extremes(raw_taf,icao,ref_utc,tz_name):
 if not raw_taf or icao.upper()not in raw_taf.upper():return{}
 tz=ZoneInfo(tz_name);n={}
 for m in _TAF_TEMP_RE.finditer(raw_taf.upper()):
  j="HIGH"if m.group(1)=="X"else"LOW";h=m.group(2);d=-float(int(h[1:]))if h.startswith("M")else float(int(h));g,i=int(m.group(3)),min(23,int(m.group(4)));f=[]
  for e in(-16,0,16):
   l=ref_utc+timedelta(days=e)
   try:f.append(datetime(l.year,l.month,g,i,0,tzinfo=timezone.utc))
   except ValueError:continue
  if not f:continue
  a=min(f,key=lambda c:abs((c-ref_utc).total_seconds()));b=a.astimezone(tz).date();k=n.setdefault(b,{})
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
 h=verify_weather_slate_partition(spec);rows=[];no_rows=[]
 for I,b in enumerate(spec.buckets):
  bk=bucket_books.get(b.market_id)or{};D=bk.get("ask_yes");A=float(bk.get("ask_yes_shares")or.0);C=bk.get("ask_no");q=float(bk.get("ask_no_shares")or.0);H=float(probs[I])if I<len(probs)else.0;F=max(.0,float(getattr(b,"fee_rate",.0)or.0));E=max(1.,float(getattr(b,"fee_exponent",1.)or 1.))
  if D is not None and.005<=float(D)<=.99 and A>=5.:z=float(D);y=F*((z*(1.-z))**E)if F>.0 else.0;w=z+y;rows.append({"idx":I,"market_id":b.market_id,"label":b.label,"yes_token":b.yes_token,"ask_yes":z,"eff_ask_yes":round(w,6),"fee_per_share":round(y,6),"fee_rate":F,"fee_exponent":E,"ask_yes_shares":A,"prob":H,"edge":H-w})
  if C is not None and.005<=float(C)<=.995 and q>=5.:v=float(C);u=F*((v*(1.-v))**E)if F>.0 else.0;t=v+u;no_rows.append({"idx":I,"market_id":b.market_id,"label":b.label,"yes_token":b.no_token,"no_token":b.no_token,"side":"NO","ask_yes":v,"eff_ask_yes":round(t,6),"fee_per_share":round(u,6),"fee_rate":F,"fee_exponent":E,"ask_yes_shares":q})
 a=None
 if h and len(rows)==len(spec.buckets):
  p=sum(r["eff_ask_yes"]for r in rows);g=sum(r["ask_yes"]for r in rows);s=min(r["ask_yes_shares"]for r in rows)
  if p<=max_underround_sum and s>=5.:
   o=max(5.,min(s,math.floor(float(target_budget_usd)/max(.1,p))))
   if o*p<=float(target_budget_usd)*1.25:a={"mode":"FULL_SLATE_DUTCH_ARB","side":"ALL_BUCKETS_YES","guaranteed_payout_per_set":1.,"sum_asks":round(p,5),"sum_raw_asks":round(g,5),"guaranteed_edge_per_set":round(1.-p,5),"equal_shares":float(o),"total_cost_usd":round(o*p,4),"guaranteed_profit_usd":round(o*(1.-p),4),"legs":rows}
 if a is None and h and len(no_rows)==len(spec.buckets)and len(spec.buckets)>=3:
  G=float(len(spec.buckets));n=G-1.;j=sum(r["eff_ask_yes"]for r in no_rows);l=min(r["ask_yes_shares"]for r in no_rows)
  if j<=n-(1.-max_underround_sum)and l>=5.:
   i=max(5.,min(l,math.floor(float(target_budget_usd)/max(.5,j))))
   if i*j<=float(target_budget_usd)*1.25:a={"mode":"FULL_SLATE_NO_COMPLEMENT_ARB","side":"ALL_BUCKETS_NO","guaranteed_payout_per_set":round(n,4),"sum_asks":round(j,5),"guaranteed_edge_per_set":round(n-j,5),"equal_shares":float(i),"total_cost_usd":round(i*j,4),"guaranteed_profit_usd":round(i*(n-j),4),"legs":no_rows}
 m=sorted([r for r in rows if r["edge"]>=.04],key=lambda x:x["edge"],reverse=True);c=None
 if len(m)>=2:
  cand_legs=m[:3];f=sum(r["eff_ask_yes"]for r in cand_legs);e=min(.999,sum(r["prob"]for r in cand_legs));k=min(r["ask_yes_shares"]for r in cand_legs);d=e-f
  if f<=.88 and e>=.72 and d>=.09 and k>=5.:B=max(5.,min(k,math.floor(float(target_budget_usd)/max(.1,f))));c={"mode":"CONSTRAINED_SUBSET_BASKET","sum_asks":round(f,5),"combined_prob":round(e,5),"expected_edge_per_set":round(d,5),"equal_shares":float(B),"total_cost_usd":round(B*f,4),"max_loss_usd":round(B*f,4),"legs":cand_legs}
 return{"partition_verified":h,"quoted_buckets":len(rows),"total_buckets":len(spec.buckets),"full_slate_arb":a,"subset_basket":c}
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
 try:p=datetime.fromisoformat(n.replace("Z","+00:00")).timestamp()
 except Exception:return[]
 e={"DAILY":86400.,"WEEKLY":7*86400.,"MONTHLY":30*86400.}.get(horizon_group,86400.);b=p-e
 if g:
  try:
   l=datetime.fromisoformat(g.replace("Z","+00:00")).timestamp()
   if p-35*86400.<=l<p:b=max(b,l)
  except Exception:pass
 v=_CRYPTO_MONTH_RE.search(str(ev.get("title")or""))
 if v:
  try:from zoneinfo import ZoneInfo;ny=ZoneInfo("America/New_York");u=_CRYPTO_MONTHS[v.group(1).lower()];t=int(v.group(2))if v.group(2)else datetime.fromtimestamp(p-5*86400.,tz=ny).year;b=max(b,datetime(t,u,1,0,0,tzinfo=ny).timestamp())
  except Exception:pass
 r=[]
 for m in ev.get("markets")or[]:
  q=str(m.get("question")or"");gl=str(m.get("groupItemTitle")or"");f=parse_barrier_direction(q,gl);o=parse_strike_from_text(q,gl)
  if not f or not o or o<=0:continue
  d=m.get("clobTokenIds")
  if isinstance(d,str):
   try:d=json.loads(d)
   except Exception:d=[]
  if not d or len(d)<2:continue
  a=None
  if m.get("closed"):
   op=m.get("outcomePrices")
   if isinstance(op,str):
    try:op=json.loads(op)
    except Exception:op=None
   if isinstance(op,list)and len(op)>=2:
    try:
     if float(op[0])>=.99:a=1
     elif float(op[1])>=.99:a=0
    except Exception:pass
  c=b
  for j in(m.get("startDate"),m.get("createdAt")):
   if j:
    try:
     s=datetime.fromisoformat(str(j).replace("Z","+00:00")).timestamp()
     if b-3600.<=s<p:w=60. if(s>b+3e2 or"creation of this market"in str(m.get("description")or"").lower())else.0;c=max(c,min(p-60.,s+w))
    except Exception:pass
  i=.07;h=1.
  try:
   from src.polymarket_research.tradfi_sports_zero_fee_engine import _extract_market_fee_rate
   if any(k in m for k in("feeSchedule","feeType","feesEnabled","takerBaseFee")):i,h=_extract_market_fee_rate(m)
  except Exception:pass
  r.append(BarrierRungSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,horizon_group=horizon_group,asset=asset.upper(),market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),question=q,group_label=gl,strike=o,direction=f,start_ts=c,end_ts=p,yes_token=str(d[0]),no_token=str(d[1]),fee_rate=i,resolved_yes=a,fee_exponent=h))
 return r
def first_passage_touch_prob(spot,strike,tte_seconds,iv_annual,direction,wick_vol_multiplier=1.12,jump_tail_blend=.08,forward_drift_annual=.0,realized_vol_ratio=1.):
 if spot<=.0 or strike<=.0:return.0
 if direction=="UP"and spot>=strike:return 1.
 if direction=="DOWN"and spot<=strike:return 1.
 if tte_seconds<=1.:return.0
 t_years=tte_seconds/(365.25*86400.);b=abs(math.log(strike/spot));r_drift=max(-.3,min(.4,float(forward_drift_annual or.0)))
 def _single_regime_touch(sig):
  d=max(.08,min(4.,sig));c=d*math.sqrt(t_years)
  if c<=1e-8:return.0
  mu=(r_drift-.5*(d**2))if direction=="UP"else(-r_drift+.5*(d**2));d1=(-b+mu*t_years)/c;d2=(-b-mu*t_years)/c;a=max(-60.,min(60.,(2.*mu*b)/(d**2)));p=_fast_norm_cdf(d1)+math.exp(a)*_fast_norm_cdf(d2);return max(1e-4,min(.9999,p))
 d=iv_annual*wick_vol_multiplier;c=_single_regime_touch(d);g=_single_regime_touch(d*1.65);f=max(.5,min(3.5,float(realized_vol_ratio or 1.)))**1.5;a=min(.35,max(.02,float(jump_tail_blend)*f))if abs(realized_vol_ratio-1.)>1e-6 else float(jump_tail_blend);e=(1.-a)*c+a*g;return max(1e-4,min(.9999,e))
def evaluate_barrier_no_net_ev(p_touch,ask_no,fee_rate=.07,min_net_ev_per_share=.035,max_loss_to_gain_ratio=9.):g=max(1e-4,min(.9999,1.-float(p_touch)));px=max(.01,min(.99,float(ask_no)));f=min(.5,max(.0,float(fee_rate)*(1.-px)))if float(fee_rate)>.0 else.0;d=px/(1.-f)if f>.0 else px;b=max(1e-6,1.-d);e=g-d;a=d/b;c=bool(e>=min_net_ev_per_share and a<=max_loss_to_gain_ratio);return{"eligible":c,"p_no":round(g,5),"eff_cost_no":round(d,5),"ev_net_per_share":round(e,5),"loss_to_gain_ratio":round(a,3)}
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
 o=[]
 for direction in("UP","DOWN"):
  p=sorted([q for q in quote_rows if str(q.get("direction")or"").upper()==direction and float(q.get("strike")or.0)>.0],key=lambda x:float(x["strike"]))
  for i in range(len(p)):
   for j in range(i+1,len(p)):
    n,m=p[i],p[j];l,k=float(n["strike"]),float(m["strike"])
    if k<=l*1.0005:continue
    if direction=="UP":a,b=n,m;d=f"YES(↑{l:g})+NO(↑{k:g})"
    else:a,b=m,n;d=f"YES(↓{k:g})+NO(↓{l:g})"
    if("start_ts"in a and"start_ts"in b and float(a["start_ts"])>float(b["start_ts"])+1e-6):continue
    ay=a.get("ask_yes")if a.get("ask_yes")is not None else a.get("best_ask_yes");an=b.get("ask_no")if b.get("ask_no")is not None else b.get("best_ask_no")
    if ay is None or an is None:continue
    py,pn=float(ay),float(an)
    if not(.01<=py<=.99 and.01<=pn<=.99):continue
    h=float(a.get("fee_rate",fee_rate));g=float(b.get("fee_rate",fee_rate));f=float(a.get("fee_exponent",1.));e=float(b.get("fee_exponent",1.));hy=min(.5,(h*((py*(1.-py))**f))/py)if h>.0 else.0;hn=min(.5,(g*((pn*(1.-pn))**e))/pn)if g>.0 else.0;c=py/(1.-hy)+pn/(1.-hn)
    if.9<=c<=max_box_cost_net:o.append({"direction":direction,"label":d,"low_strike":l,"high_strike":k,"leg_yes_market_id":str(a["market_id"]),"leg_yes_condition_id":str(a.get("condition_id")or""),"yes_token":str(a["yes_token"]),"yes_opp_token":str(a.get("no_token")or""),"leg_yes_fee_rate":h,"leg_yes_fee_exponent":f,"leg_no_market_id":str(b["market_id"]),"leg_no_condition_id":str(b.get("condition_id")or""),"no_token":str(b["no_token"]),"no_opp_token":str(b.get("yes_token")or""),"leg_no_fee_rate":g,"leg_no_fee_exponent":e,"box_cost_gross":round(py+pn,5),"box_cost_net":round(c,5),"guaranteed_edge":round(1.-c,5)})
 o.sort(key=lambda x:x["box_cost_net"]);return o
def _fetch_finalized_klines(sym,st_ms,en_ms,interval,timeout):
 if sym=="HYPEUSDT":a=(f"{BINANCE_FAPI_URL}/fapi/v1/klines?symbol={sym}&interval={interval}&startTime={st_ms}&endTime={en_ms}&limit=1000")
 else:a=(f"{BINANCE_API_URL}/api/v3/klines?symbol={sym}&interval={interval}&startTime={st_ms}&endTime={en_ms}&limit=1000")
 b=urllib.request.Request(a,headers={"User-Agent":"DominusBarrierEngine/1.0"});rows=json.loads(urllib.request.urlopen(b,timeout=timeout).read().decode("utf-8"))
 if not isinstance(rows,list):return[]
 return[r for r in rows if len(r)>=7 and int(r[6])<=en_ms]
def fetch_binance_window_extremes_sync(asset,start_ts,end_ts,interval="1m",timeout=6.):
 j=ASSET_BINANCE_SYMBOL.get(asset.upper())
 if not j or end_ts<=start_ts:return None
 i=int(start_ts*1000);h=int(end_ts*1000);d=end_ts-start_ts
 try:
  combined=[]
  if d>5.7e4 and interval in("1m","5m"):
   c=min(h,(i//3600000+1)*3600000+60000)
   if c>i:combined.extend(_fetch_finalized_klines(j,i,c,"1m",timeout))
   combined.extend(_fetch_finalized_klines(j,i,h,"1h",timeout));b=max(i,h-7200*1000);combined.extend(_fetch_finalized_klines(j,b,h,"1m",timeout))
  else:combined.extend(_fetch_finalized_klines(j,i,h,interval,timeout))
  if not combined:return None
  g=max(float(r[2])for r in combined);f=min(float(r[3])for r in combined);a=max(combined,key=lambda r:int(r[6]));e=float(a[4]);return g,f,e
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
 a=sigma*math.sqrt(T);d1=(math.log(F/K)+.5*(sigma**2)*T)/a;d2=d1-a;return F*_fast_norm_cdf(d1)-K*_fast_norm_cdf(d2)
def _fast_bl_digital(F,K,T_years,svi):b=max(1e-6,T_years);dK=max(.01,K*.001);f=math.log((K+dK)/F);e=math.log(max(1e-6,K-dK)/F);d=_fast_bs_call(F,K+dK,b,svi.implied_vol(f,t_override=b));c=_fast_bs_call(F,max(1e-6,K-dK),b,svi.implied_vol(e,t_override=b));a=-(d-c)/(2.*dK);return max(1e-4,min(.9999,a))
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
 try:g=datetime.fromisoformat(e.replace("Z","+00:00")).timestamp()
 except Exception:return[]
 d=str(ev.get("title")or"");h=[]
 for m in ev.get("markets")or[]:
  q=str(m.get("question")or"");gl=str(m.get("groupItemTitle")or"")
  if"between"in q.lower():continue
  f=_extract_threshold_strike(q,gl)
  if f is None or f<=0:continue
  b=m.get("clobTokenIds")
  if isinstance(b,str):
   try:b=json.loads(b)
   except Exception:b=[]
  if not b or len(b)<2:continue
  a=None
  if m.get("closed"):
   op=m.get("outcomePrices")
   if isinstance(op,str):
    try:op=json.loads(op)
    except Exception:op=None
   if isinstance(op,list)and len(op)>=2:
    try:
     if float(op[0])>=.99:a=1
     elif float(op[1])>=.99:a=0
    except Exception:pass
  c=any(w in q.lower()for w in("below","under","less than","lower than"));h.append(StrikeRungSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,asset=asset.upper(),title=d,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),question=q,strike=f,is_downward=c,end_ts=g,yes_token=str(b[0]),no_token=str(b[1]),resolved_yes=a))
 h.sort(key=lambda r:r.strike);return h
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
 else:a=h;b=max(1e-6,a*math.sqrt(j));d2=(math.log(spot/strike)-.5*(a**2)*j)/b;c=_fast_norm_cdf(d2)
 e=(1.-c)if is_downward else c;b=max(1e-6,a*math.sqrt(j));d=abs(math.log(spot/strike))/b;return{"p_yes":round(max(.001,min(.999,e)),4),"p_no":round(max(.001,min(.999,1.-e)),4),"iv_annual":round(a,4),"z_sigma":round(d,3),"source":"DVOL_SVI_BL"}
def detect_ladder_monotonicity_boxes(quote_rows,fee_rate=.07):
 g=[];d=sorted([r for r in quote_rows if not r.get("is_downward")],key=lambda x:x["strike"])
 for i in range(len(d)):
  for j in range(i+1,len(d)):
   lo=d[i];hi=d[j]
   if hi["strike"]<=lo["strike"]:continue
   c=float(lo.get("ask_yes")or 1.);b=float(hi.get("ask_no")or 1.)
   if not(.01<=c<=.98 and.01<=b<=.98):continue
   f=fee_rate*c*(1.-c);e=fee_rate*b*(1.-b);a=c+b+f+e
   if a<=.996:g.append({"low_strike":lo["strike"],"high_strike":hi["strike"],"low_market_id":lo["market_id"],"high_market_id":hi["market_id"],"yes_token_low":lo["yes_token"],"no_token_high":hi["no_token"],"ask_yes_low":c,"ask_no_high":b,"box_cost_net":round(a,5),"riskless_floor_edge":round(1.-a,5)})
 return g
def evaluate_coherent_strike_ladder(asset,spot,rungs,tte_seconds,now_ts=None):
 d=sorted([r for r in rungs if not r.is_downward],key=lambda x:x.strike);raw_pairs=[];b={}
 for r in d:fv=evaluate_svi_digital_fair_value(asset,spot,r.strike,tte_seconds,is_downward=False,now_ts=now_ts);raw_pairs.append((r.strike,float(fv["p_yes"])));b[r.strike]=fv
 if enforce_monotone_ladder_probabilities is not None and raw_pairs:c=enforce_monotone_ladder_probabilities(raw_pairs)
 else:c={"strikes":[k for k,_ in raw_pairs],"probs":[p for _,p in raw_pairs],"interval_probs":[],"max_adjustment":.0}
 a={}
 for g,r in enumerate(d):f=float(c["probs"][g])if g<len(c["probs"])else float(b[r.strike]["p_yes"]);e=dict(b[r.strike]);e["p_yes_raw"]=e["p_yes"];e["p_yes"]=round(f,4);e["p_no"]=round(1.-f,4);a[r.market_id]=e
 return{"by_market_id":a,"strikes":c["strikes"],"probs":c["probs"],"interval_probs":c["interval_probs"],"max_adjustment":c["max_adjustment"]}
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
  q=str(m.get("question")or"");gl=str(m.get("groupItemTitle")or"");d=m.get("clobTokenIds")
  if isinstance(d,str):
   try:d=json.loads(d)
   except Exception:d=[]
  if not isinstance(d,list)or len(d)<2:continue
  a=None;b=None;c=None;o=_RANGE_LABEL_RE.match(gl)or _BETWEEN_Q_RE.search(q)
  if o:
   u=_num_with_k(o.group(1),o.group(2));t=_num_with_k(o.group(3),o.group(4))
   if t>u>0:a="RANGE";b,c=u,t
  else:
   r=_LOWER_TAIL_LABEL_RE.match(gl);p=_UPPER_TAIL_LABEL_RE.match(gl);n=q.lower()
   if r or("less than"in n or"below"in n or"under"in n):
    k=_num_with_k(r.group(1),r.group(2))if r else _extract_threshold_strike(q,gl)
    if k and k>0:a="LOWER_TAIL";c=k
   elif p or("greater than"in n or"above"in n or"over"in n):
    k=_num_with_k(p.group(1),p.group(2))if p else _extract_threshold_strike(q,gl)
    if k and k>0:a="UPPER_TAIL";b=k
  if a is None:continue
  e=m.get("feeSchedule")or{};f=float(e.get("rate",.07)if m.get("feesEnabled",True)else.0);h=str(m.get("resolutionSource")or ev.get("resolutionSource")or"").strip().lower();g.append(NegRiskBracketSpec(event_id=s,series_slug=series_slug,asset=asset.upper(),title=i,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),question=q,bracket_kind=a,k_low=b,k_high=c,end_ts=l,yes_token=str(d[0]),no_token=str(d[1]),fee_rate=f,resolution_source=h))
 return g
def build_negrisk_cross_box_bundles(rungs,brackets,spot=.0,max_strike_dist_log=.14,tail_max_strike_dist_log=.24):
 if not rungs or not brackets:return[]
 if rungs[0].asset!=brackets[0].asset:return[]
 if abs(rungs[0].end_ts-brackets[0].end_ts)>2.:return[]
 d={round(float(r.strike),4):r for r in rungs if not r.is_downward};c=[]
 for br in brackets:
  if spot>.0:
   g=br.k_low if br.k_low is not None else(br.k_high or spot);b=tail_max_strike_dist_log if br.bracket_kind in("LOWER_TAIL","UPPER_TAIL")else max_strike_dist_log
   if g>0 and abs(math.log(g/spot))>b:continue
  if br.bracket_kind=="LOWER_TAIL"and br.k_high is not None:
   a=d.get(round(float(br.k_high),4))
   if a is not None:c.append({"bundle_id":f"TAIL_LOW_YES_{br.market_id}_{a.market_id}","label":f"NR_YES(<{br.k_high:g})+MS_YES(>{a.strike:g})","guaranteed_payout":1.,"end_ts":br.end_ts,"legs":[{"token_id":br.yes_token,"opp_token_id":br.no_token,"condition_id":br.condition_id,"neg_risk":True,"strike":float(br.k_high),"side":"YES","market_id":br.market_id,"fee_rate":br.fee_rate,"label":f"NR_YES<{br.k_high:g}"},{"token_id":a.yes_token,"opp_token_id":a.no_token,"condition_id":a.condition_id,"neg_risk":False,"strike":float(a.strike),"side":"YES","market_id":a.market_id,"fee_rate":a.fee_rate,"label":f"MS_YES>{a.strike:g}"}]});c.append({"bundle_id":f"TAIL_LOW_NO_{br.market_id}_{a.market_id}","label":f"NR_NO(<{br.k_high:g})+MS_NO(>{a.strike:g})","guaranteed_payout":1.,"end_ts":br.end_ts,"legs":[{"token_id":br.no_token,"opp_token_id":br.yes_token,"condition_id":br.condition_id,"neg_risk":True,"strike":float(br.k_high),"side":"NO","market_id":br.market_id,"fee_rate":br.fee_rate,"label":f"NR_NO<{br.k_high:g}"},{"token_id":a.no_token,"opp_token_id":a.yes_token,"condition_id":a.condition_id,"neg_risk":False,"strike":float(a.strike),"side":"NO","market_id":a.market_id,"fee_rate":a.fee_rate,"label":f"MS_NO>{a.strike:g}"}]})
  elif br.bracket_kind=="UPPER_TAIL"and br.k_low is not None:
   a=d.get(round(float(br.k_low),4))
   if a is not None:c.append({"bundle_id":f"TAIL_HIGH_A_{br.market_id}_{a.market_id}","label":f"NR_YES(>{br.k_low:g})+MS_NO(>{a.strike:g})","guaranteed_payout":1.,"end_ts":br.end_ts,"legs":[{"token_id":br.yes_token,"opp_token_id":br.no_token,"condition_id":br.condition_id,"neg_risk":True,"strike":float(br.k_low),"side":"YES","market_id":br.market_id,"fee_rate":br.fee_rate,"label":f"NR_YES>{br.k_low:g}"},{"token_id":a.no_token,"opp_token_id":a.yes_token,"condition_id":a.condition_id,"neg_risk":False,"strike":float(a.strike),"side":"NO","market_id":a.market_id,"fee_rate":a.fee_rate,"label":f"MS_NO>{a.strike:g}"}]});c.append({"bundle_id":f"TAIL_HIGH_B_{br.market_id}_{a.market_id}","label":f"NR_NO(>{br.k_low:g})+MS_YES(>{a.strike:g})","guaranteed_payout":1.,"end_ts":br.end_ts,"legs":[{"token_id":br.no_token,"opp_token_id":br.yes_token,"condition_id":br.condition_id,"neg_risk":True,"strike":float(br.k_low),"side":"NO","market_id":br.market_id,"fee_rate":br.fee_rate,"label":f"NR_NO>{br.k_low:g}"},{"token_id":a.yes_token,"opp_token_id":a.no_token,"condition_id":a.condition_id,"neg_risk":False,"strike":float(a.strike),"side":"YES","market_id":a.market_id,"fee_rate":a.fee_rate,"label":f"MS_YES>{a.strike:g}"}]})
  elif br.bracket_kind=="RANGE"and br.k_low is not None and br.k_high is not None:
   f=d.get(round(float(br.k_low),4));e=d.get(round(float(br.k_high),4))
   if f is not None and e is not None:c.append({"bundle_id":f"PART_1X_{br.market_id}_{f.market_id}_{e.market_id}","label":f"MS_NO(>{br.k_low:g})+NR_YES([{br.k_low:g},{br.k_high:g}])+MS_YES(>{br.k_high:g})","guaranteed_payout":1.,"end_ts":br.end_ts,"legs":[{"token_id":f.no_token,"side":"NO","market_id":f.market_id,"fee_rate":f.fee_rate,"label":f"MS_NO>{br.k_low:g}"},{"token_id":br.yes_token,"side":"YES","market_id":br.market_id,"fee_rate":br.fee_rate,"label":f"NR_YES[{br.k_low:g}-{br.k_high:g}]"},{"token_id":e.yes_token,"side":"YES","market_id":e.market_id,"fee_rate":e.fee_rate,"label":f"MS_YES>{br.k_high:g}"}]});c.append({"bundle_id":f"COMP_2X_{br.market_id}_{f.market_id}_{e.market_id}","label":f"MS_YES(>{br.k_low:g})+NR_NO([{br.k_low:g},{br.k_high:g}])+MS_NO(>{br.k_high:g})","guaranteed_payout":2.,"end_ts":br.end_ts,"legs":[{"token_id":f.yes_token,"side":"YES","market_id":f.market_id,"fee_rate":f.fee_rate,"label":f"MS_YES>{br.k_low:g}"},{"token_id":br.no_token,"side":"NO","market_id":br.market_id,"fee_rate":br.fee_rate,"label":f"NR_NO[{br.k_low:g}-{br.k_high:g}]"},{"token_id":e.no_token,"side":"NO","market_id":e.market_id,"fee_rate":e.fee_rate,"label":f"MS_NO>{br.k_high:g}"}]})
 return c
def parse_daily_updown_event(ev,asset,series_slug):
 k=ev.get("markets")or[]
 if not k or not isinstance(k[0],dict):return None
 m=k[0]
 if m.get("closed")or m.get("acceptingOrders")is False:return None
 e=str(m.get("eventStartTime")or"").strip();i=str(m.get("endDate")or ev.get("endDate")or"").strip()
 if not e or not i:return None
 try:h=datetime.fromisoformat(e.replace("Z","+00:00")).timestamp();j=datetime.fromisoformat(i.replace("Z","+00:00")).timestamp()
 except Exception:return None
 if abs((j-h)-86400.)>7200.:return None
 c=m.get("clobTokenIds")
 if isinstance(c,str):
  try:c=json.loads(c)
  except Exception:c=[]
 outcomes=m.get("outcomes")
 if isinstance(outcomes,str):
  try:outcomes=json.loads(outcomes)
  except Exception:outcomes=[]
 if not isinstance(c,list)or len(c)<2:return None
 b,a=0,1
 if isinstance(outcomes,list)and len(outcomes)>=2:
  g=[str(o).strip().upper()for o in outcomes]
  if"UP"in g and"DOWN"in g:b=g.index("UP");a=g.index("DOWN")
 d=m.get("feeSchedule")or{};f=float(d.get("rate",.07)if m.get("feesEnabled",True)else.0);return DailyUpDownSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,asset=asset.upper(),title=str(m.get("question")or ev.get("title")or""),market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),start_ts=h,end_ts=j,up_token=str(c[b]),down_token=str(c[a]),fee_rate=f,resolution_source=str(m.get("resolutionSource")or"").strip().lower())
# ======================================================================================
# [08/21] MODULE: src/polymarket_research/same_oracle_dominance_box.py
# PURPOSE: Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import math;from dataclasses import dataclass;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;CORE_LIVE_DOMINANCE_ASSETS=("BTC","ETH","SOL","XRP");EXPANSION_DOMINANCE_ASSETS=("BNB","DOGE","HYPE");DOMINANCE_ASSETS=CORE_LIVE_DOMINANCE_ASSETS+EXPANSION_DOMINANCE_ASSETS;DOMINANCE_SERIES_SLUGS={"BTC":{"4h":"btc-up-or-down-4h","15m":"btc-up-or-down-15m","5m":"btc-up-or-down-5m"},"ETH":{"4h":"eth-up-or-down-4h","15m":"eth-up-or-down-15m","5m":"eth-up-or-down-5m"},"SOL":{"4h":"sol-up-or-down-4h","15m":"sol-up-or-down-15m","5m":"sol-up-or-down-5m"},"XRP":{"4h":"xrp-up-or-down-4h","15m":"xrp-up-or-down-15m","5m":"xrp-up-or-down-5m"},"BNB":{"4h":"bnb-up-or-down-4h","15m":"bnb-up-or-down-15m","5m":"bnb-up-or-down-5m"},"DOGE":{"4h":"doge-up-or-down-4h","15m":"doge-up-or-down-15m","5m":"doge-up-or-down-5m"},"HYPE":{"4h":"hype-up-or-down-4h","15m":"hype-up-or-down-15m","5m":"hype-up-or-down-5m"}};EMPIRICAL_BOX_ASSET_CAPS_USD={"BTC":150.,"ETH":75.,"SOL":22.,"XRP":22.,"BNB":22.,"HYPE":15.,"DOGE":15.};MIN_CORRIDOR_BPS_BY_ASSET={"BTC":3.,"ETH":3.,"SOL":3.,"XRP":3.,"BNB":5.,"DOGE":5.,"HYPE":5.};POLYMARKET_CRYPTO_PRICE_URL="https://polymarket.com/api/crypto/crypto-price";GAMMA_EVENTS_URL="https://gamma-api.polymarket.com/events";HORIZON_TO_VARIANT={"4h":"fourhour","15m":"fifteen","5m":"fiveminute"};HORIZON_TO_DURATION_SEC={"4h":14400.,"15m":9e2,"5m":3e2}
@dataclass(frozen=True)
class TwapCandleMarketSpec:asset:str;horizon:str;market_id:str;condition_id:str;title:str;start_iso:str;end_iso:str;start_ts:float;end_ts:float;up_token:str;down_token:str;fee_rate:float;fee_exponent:float;neg_risk:bool;twap_lookback_sec:int;resolution_source:str
def _parse_iso_ts(iso_str):
 dt=datetime.fromisoformat(str(iso_str).replace("Z","+00:00"))
 if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
 return dt.timestamp()
def parse_twap_candle_event(event,asset,horizon):
 if horizon not in HORIZON_TO_VARIANT:return None
 q=event.get("markets")or[]
 if not q or not isinstance(q[0],dict):return None
 m=q[0]
 if m.get("closed")or m.get("acceptingOrders")is False:return None
 g=str(m.get("eventStartTime")or"").strip();p=str(m.get("endDate")or event.get("endDate")or"").strip()
 if not g or not p:return None
 try:k=_parse_iso_ts(g);r=_parse_iso_ts(p)
 except Exception:return None
 e=HORIZON_TO_DURATION_SEC[horizon]
 if abs((r-k)-e)>5.:return None
 t=m.get("cryptoMarketConfig")or{};n=str(m.get("resolutionSource")or"").strip().lower();s=str(m.get("description")or"").lower();d=bool(t.get("twapEnabled"))or("twap-60s-streams"in n)or("twap-60s-streams"in s);j=int(t.get("twapLookbackSeconds")or(60 if"twap-60s"in(n+s)else 0))
 if not d or j!=60:return None
 c=m.get("clobTokenIds")
 if isinstance(c,str):
  try:c=json.loads(c)
  except Exception:c=[]
 outcomes=m.get("outcomes")
 if isinstance(outcomes,str):
  try:outcomes=json.loads(outcomes)
  except Exception:outcomes=[]
 if not isinstance(c,list)or len(c)<2:return None
 b,a=0,1
 if isinstance(outcomes,list)and len(outcomes)>=2:
  i=[str(o).strip().upper()for o in outcomes]
  if"UP"in i and"DOWN"in i:b=i.index("UP");a=i.index("DOWN")
 f=m.get("feeSchedule")or{};h=float(f.get("rate",.07)if m.get("feesEnabled",True)else.0);l=float(f.get("exponent",1.));return TwapCandleMarketSpec(asset=asset.upper(),horizon=horizon,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),title=str(m.get("question")or event.get("title")or""),start_iso=g,end_iso=p,start_ts=k,end_ts=r,up_token=str(c[b]),down_token=str(c[a]),fee_rate=h,fee_exponent=l,neg_risk=bool(m.get("negRisk",False)),twap_lookback_sec=j,resolution_source=n)
def verify_same_oracle_pair(m_long,m_short):
 if m_long.asset!=m_short.asset:return False
 if m_long.horizon not in HORIZON_TO_VARIANT or m_short.horizon not in HORIZON_TO_VARIANT:return False
 if m_long.horizon==m_short.horizon:return False
 if HORIZON_TO_DURATION_SEC[m_long.horizon]<=HORIZON_TO_DURATION_SEC[m_short.horizon]:return False
 if abs(m_long.end_ts-m_short.end_ts)>2.:return False
 if m_long.twap_lookback_sec!=60 or m_short.twap_lookback_sec!=60:return False
 b=str(m_long.resolution_source or"").strip().lower();a=str(m_short.resolution_source or"").strip().lower()
 if not b or not a or b!=a:return False
 return True
def build_prev_5m_gamma_event_url(spec):a=int(round(spec.start_ts))-300;return f"{GAMMA_EVENTS_URL}?slug={spec.asset.lower()}-updown-5m-{a}"
def build_own_gamma_event_url(asset,horizon,start_ts_or_iso):a=_parse_iso_ts(start_ts_or_iso)if isinstance(start_ts_or_iso,str)else float(start_ts_or_iso);return f"{GAMMA_EVENTS_URL}?slug={str(asset).lower()}-updown-{str(horizon).lower()}-{int(round(a))}"
def build_crypto_price_query_url(spec):
 if int(spec.twap_lookback_sec)!=60:raise ValueError(f"60s Chainlink TWAP required, got twap_lookback_sec={spec.twap_lookback_sec}")
 a=HORIZON_TO_VARIANT[spec.horizon];return(f"{POLYMARKET_CRYPTO_PRICE_URL}?symbol={spec.asset}&eventStartTime={spec.start_iso}&variant={a}&endDate={spec.end_iso}&twapEnabled=true&twapLookbackSeconds=60")
def _is_verified_twap60_url(request_url):u=str(request_url or"");return("twapEnabled=true"in u)and("twapLookbackSeconds=60"in u)
def _extract_closed_gamma_meta_field(payload,field,request_url=None):
 ev=payload[0]if isinstance(payload,list)and payload else payload
 if not isinstance(ev,dict)or ev.get("closed")is not True:return None
 if request_url and"slug="in str(request_url):
  a=str(request_url).split("slug=",1)[1].split("&",1)[0]
  if str(ev.get("slug")or"")!=a:return None
 b=ev.get("eventMetadata")
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
 asks=sorted([(float(a["price"]),float(a["size"]))for a in(asks_raw or[])if float(a.get("price",0))>.0 and float(a.get("size",0))>.0],key=lambda x:x[0])
 if not asks:return[],1.,.0
 best_ask=asks[0][0];capped=[(px,sz)for px,sz in asks if px<=best_ask+max_slip_cents+1e-9 and px<.99];b=sum(sz for _,sz in capped);return capped,best_ask,b
def _buy_share_haircut(px,fee_rate,fee_exponent=1.):
 p=float(px);r=float(fee_rate or.0)
 if r<=.0 or p<=.0 or p>=1.:return.0
 a=r*((p*(1.-p))**float(fee_exponent or 1.));return min(.5,max(.0,a/p))
def _net_unit_cost_buy(px,fee_rate,fee_exponent=1.):p=float(px);h=_buy_share_haircut(p,fee_rate,fee_exponent);return p/(1.-h)if h>.0 else p
def _walk_exact_shares(asks_capped,shares_qty,fee_rate,fee_exponent=1.):
 if shares_qty<=0 or not asks_capped:return None
 j=float(shares_qty);d=.0;b=asks_capped[0][0];c=0
 for px,sz in asks_capped:
  f=min(j,sz)
  if f<=0:continue
  d+=f*px;b=px;c+=1;j-=f
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
 def _worst_limit_net(wa_d,wb_d):pa,pb=float(wa_d["worst_px"]),float(wb_d["worst_px"]);return round(_net_unit_cost_buy(pa,fee_rate_a,fee_exponent_a)+_net_unit_cost_buy(pb,fee_rate_b,fee_exponent_b),6)
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
 j=[];m=[];t=[];b=.0
 for lg in legs_spec:
  f,s,p=_sorted_asks(lg.get("asks")or[],max_slip_cents)
  if not f:return{"filled":False,"reason":"EMPTY_LEG_BOOK"}
  fr=float(lg.get("fee_rate",.07));fe=float(lg.get("fee_exponent",1.));j.append(f);m.append(s);t.append(p);b+=_net_unit_cost_buy(s,fr,fe)
 if b>max_bundle_cost_net+.015:return{"filled":False,"reason":"BUNDLE_TOO_EXPENSIVE_L1","l1_bundle_cost_net":round(b,5)}
 i=int(math.floor(min(t)))
 if i<max(5,min_shares):return{"filled":False,"reason":"INSUFFICIENT_BUNDLE_SHARES","avail_bundle_shares":i}
 l=int(math.floor(float(target_budget_usd)/max(.1,b)));n=min(l,i)
 if n<max(5,min_shares):return{"filled":False,"reason":"BUDGET_BELOW_MIN_SHARES"}
 walks=[]
 for lg,f in zip(legs_spec,j):
  q=_walk_exact_shares(f,n,float(lg.get("fee_rate",.07)),float(lg.get("fee_exponent",1.)))
  if q is None:return{"filled":False,"reason":"LEG_WALK_FAILED"}
  walks.append(q)
 d=sum(w["spent_usd"]for w in walks);e=sum(w["fee_usd"]for w in walks);c=d+e;a=c/float(n)
 if c>target_budget_usd*1.02:
  r=int(math.floor(float(target_budget_usd)/a))
  if r<max(5,min_shares):return{"filled":False,"reason":"TRIMMED_BELOW_MIN_SHARES"}
  n=r;walks=[]
  for lg,f in zip(legs_spec,j):
   q=_walk_exact_shares(f,n,float(lg.get("fee_rate",.07)),float(lg.get("fee_exponent",1.)))
   if q is None:return{"filled":False,"reason":"LEG_TRIM_WALK_FAILED"}
   walks.append(q)
  d=sum(w["spent_usd"]for w in walks);e=sum(w["fee_usd"]for w in walks);c=d+e;a=c/float(n)
 k=min(m);o=int(math.ceil(1./max(k,.01)-1e-9))
 if n<o:return{"filled":False,"reason":"LEG_BELOW_1USD_MIN","avail_bundle_shares":i}
 if d<min_box_notional_usd:return{"filled":False,"reason":"BELOW_MIN_BOX_NOTIONAL","spent_usd":round(d,2)}
 if a>max_bundle_cost_net:return{"filled":False,"reason":"BUNDLE_COST_ABOVE_CAP","bundle_cost_net":round(a,5),"l1_bundle_cost_net":round(b,5)}
 g=guaranteed_payout_per_bundle-a;h=round(min(t)*sum(m),2);return{"filled":True,"shares":int(n),"best_ask":round(sum(m),4),"vwap":round(d/float(n),5),"eff_px":round(a,5),"box_cost_net":round(a,5),"guaranteed_payout_per_bundle":round(guaranteed_payout_per_bundle,4),"riskless_floor_per_pair":round(g,5),"guaranteed_min_profit_usd":round(float(n)*g,4),"spent_usd":round(d,4),"fee_usd":round(e,4),"l1_usd":h,"avail_bundle_shares":i,"leg_walks":walks}
# ======================================================================================
# [09/21] MODULE: src/polymarket_research/exact_twap_lock_engine.py
# PURPOSE: Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import math;import os;from pathlib import Path;from typing import Any,Dict,List,Optional,Sequence,Tuple;DEFAULT_ANNUAL_IV_FLOORS={"BTC":.55,"ETH":.7,"SOL":.9,"XRP":.95,"BNB":.85,"DOGE":1.15,"HYPE":1.35};SECONDS_PER_YEAR=365.25*86400.;SHM_DIR=Path(os.getenv("PM_FAST_TICK_DIR","/dev/shm"))
def student_t_df4_cdf(z):
 if not math.isfinite(z):return.5
 z2=z*z;s=math.sqrt(4.+z2);a=.5+(z/(2.*s))*(1.+2./(4.+z2));return max(.0,min(1.,a))
def student_t_df5_cdf(z):
 if not math.isfinite(z):return.5
 u=z/math.sqrt(5.);u2=u*u;a=1.+u2;b=.5+(math.atan(u)+u/a+(2./3.)*(u/(a*a)))/math.pi;return max(.0,min(1.,b))
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
  d=json.loads(p.read_text(encoding="utf-8"));ts=float(d.get("timestamp_unix")or d.get("ts")or.0);e=now_ts-ts
  if ts<=.0 or e>max_age_sec or e<-1.5:return{"usd_spot":None,"twap_60s":None,"source":None}
  c=d.get("chainlink_proxy_spot");b=d.get("coinbase_spot");a=d.get("chainlink_twap_60s")
  if c and float(c)>0:return{"usd_spot":float(c),"twap_60s":float(a)if(a and float(a)>0)else None,"source":"shm_chainlink_proxy"}
  if b and float(b)>0:return{"usd_spot":float(b),"twap_60s":float(a)if(a and float(a)>0)else None,"source":"shm_coinbase_usd"}
 except Exception:pass
 return{"usd_spot":None,"twap_60s":None,"source":None}
def compute_exact_twap_lock_probability(*,asset,open_price,current_usd_spot,rem_seconds,now_ts,end_ts,spot_samples=(),shm_twap_60s=None,iv_annual=None,usd_direct_feed=False,min_rem_seconds=8.,max_rem_seconds=45.,jump_vol_mult=1.35):
 if(not math.isfinite(open_price)or open_price<=.0 or not math.isfinite(current_usd_spot)or current_usd_spot<=.0 or not(min_rem_seconds<=rem_seconds<=max_rem_seconds)):return{"eligible":False,"reason":"OUT_OF_WINDOW_OR_INVALID_PRICES"}
 window_start=end_ts-60.;h=max(.0,min(60.,60.-rem_seconds));s=h/60.;k=sorted((float(ts),float(px))for ts,px in spot_samples if window_start<=float(ts)<=now_ts+.5 and float(px)>.0 and math.isfinite(float(px)));in_window=[]
 for ts,px in k:
  if in_window and abs(ts-in_window[-1][0])<1e-6:in_window[-1]=(ts,px)
  else:in_window.append((ts,px))
 if len(in_window)>=2:
  B,A=in_window[0];G,F=in_window[-1];z=min(2.,max(.0,B-window_start));y=min(2.,max(.0,now_ts-G));v=z*A+y*F;d=z+y;b=max(.0,(B-window_start)-z)+max(.0,(now_ts-G)-y)
  for J in range(len(in_window)-1):
   t0,p0=in_window[J];t1,p1=in_window[J+1];dt=max(.0,t1-t0);E=min(dt,6.);v+=.5*(p0+p1)*E;d+=E
   if dt>6.:b+=dt-6.
  a=(v/d)if d>.0 else(sum(px for _,px in in_window)/len(in_window));i=max(.0,min(1.,(h-b)/max(1.,h)));c=s*i
 elif(shm_twap_60s is not None and shm_twap_60s>.0 and math.isfinite(shm_twap_60s)and rem_seconds<=12.):a=float(shm_twap_60s);g=max(.0,(60.-2.*rem_seconds)/60.);c=s*g
 else:a=current_usd_spot;c=.0
 x=c*a+(1.-c)*current_usd_spot;r=current_usd_spot-open_price;q=x-open_price
 if r==.0 or q==.0 or(r>.0)!=(q>.0):return{"eligible":False,"reason":"WHIPSAW_SPLIT_ACROSS_STRIKE","mu_twap":round(x,6),"eff_alpha":round(c,4)}
 I="UP"if q>.0 else"DOWN";w=str(asset).upper();u=DEFAULT_ANNUAL_IV_FLOORS.get(w,.8);p=max(u,float(iv_annual or.0));t=(p*jump_vol_mult)/math.sqrt(SECONDS_PER_YEAR);m=1.-c;H=max(1,int(round(rem_seconds)));o=((H+1.)*(2.*H+1.))/(6.*H*H);j=m*current_usd_spot*t*math.sqrt(max(1.,rem_seconds)*o);n=4.5 if usd_direct_feed else 8.5;f=current_usd_spot*(n/1e4);e=math.hypot(j,f)
 if e<=.0:return{"eligible":False,"reason":"ZERO_SIGMA"}
 D=abs(q)/e;C=student_t_df5_cdf(D);l=(abs(q)/open_price)*1e4;return{"eligible":True,"side":I,"open_price":open_price,"current_usd_spot":round(current_usd_spot,6),"banked_mean":round(a,6),"mu_twap":round(x,6),"eff_alpha":round(c,4),"rem_seconds":round(rem_seconds,2),"sigma_total_usd":round(e,6),"z_lock":round(D,4),"p_lock":round(min(.996,C),4),"cushion_bps":round(l,2),"basis_bps_floor":n,"samples_in_window":len(in_window)}
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
  dt=datetime.fromisoformat(s.replace("Z","+00:00"))
  if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
  return dt.timestamp()
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
  wd=b.weekday();c=datetime(b.year,b.month,b.day,0,0,tzinfo=NY_TZ);e=[]
  if session_class=="EQUITY_RTH":
   if wd<5:e.append((c.replace(hour=9,minute=30),c.replace(hour=16,minute=0)))
  else:
   if wd<4:e.append((c,c.replace(hour=17,minute=0)));e.append((c.replace(hour=18,minute=0),c+timedelta(days=1)))
   elif wd==4:e.append((c,c.replace(hour=17,minute=0)))
   elif wd==6:e.append((c.replace(hour=18,minute=0),c+timedelta(days=1)))
  for w0,w1 in e:
   lo=max(start_ts,w0.timestamp());hi=min(end_ts,w1.timestamp())
   if hi>lo:a+=hi-lo
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
 d=f"{question} {desc}";a=datetime.fromtimestamp(max(.0,float(end_ts)-5*86400.),tz=NY_TZ).year;c=_NAMED_WEEK_RE.search(d)
 if c:
  mo=_MONTH_NAME_MAP[c.group(1).lower()];dy=int(c.group(2));yr=int(c.group(3))if c.group(3)else a
  try:e=datetime(yr,mo,dy,0,0,tzinfo=NY_TZ);return(e-timedelta(hours=6 if e.weekday()==0 else 0)).timestamp()
  except ValueError:return.0
 b=_NAMED_MONTH_RE.search(d)
 if b:
  mo=_MONTH_NAME_MAP[b.group(1).lower()];yr=int(b.group(2))if b.group(2)else a
  try:return datetime(yr,mo,1,0,0,tzinfo=NY_TZ).timestamp()
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
  q=str(m.get("question")or"");s=str(m.get("groupItemTitle")or"");ql=(s+" "+q).lower()
  if"↑"in s or"(high)"in ql or"hit above"in ql:a="UP"
  elif"↓"in s or"(low)"in ql or"dip"in ql or"hit below"in ql:a="DOWN"
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
  q=str(m.get("question")or"");l=str(m.get("groupItemTitle")or"");ql=q.lower();b=("below"in ql or"under"in ql)and("above"not in ql)
  if not b and"above"not in ql and"over"not in ql:continue
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
  u=urllib.request.Request(v,headers={"User-Agent":"Mozilla/5.0"});t=json.loads(urllib.request.urlopen(u,timeout=timeout).read().decode("utf-8"));p=((t.get("chart")or{}).get("result")or[None])[0]or{};o=p.get("meta")or{};c=float(o.get("regularMarketPrice")or.0);g=p.get("timestamp")or[];q0=(((p.get("indicators")or{}).get("quote")or[None])[0])or{};l=q0.get("high")or[];k=q0.get("low")or[];j=q0.get("close")or[];f=time.time();n=[]
  for s,q in enumerate(g):
   if s>=len(l)or s>=len(k)or s>=len(j):continue
   hi,lo,cl=l[s],k[s],j[s]
   if hi is None or lo is None or cl is None:continue
   h=int(q)
   if h+60<=f and float(cl)>0:n.append((h,float(hi),float(lo),float(cl)))
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
 sub=[b for b in bars if start_ts<=float(b[0])<=end_ts]
 if not sub:return None
 return max(b[1]for b in sub),min(b[2]for b in sub)
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
 for qc in close_rows:
  if qc.get("is_downward")or qc.get("ask_no")is None:continue
  b=float(qc["end_ts"]);f=float(qc["strike"])
  for qh in hit_rows:
   if(qh["asset"]!=qc["asset"]or qh["direction"]!="UP"or qh.get("ask_yes")is None):continue
   e=float(qh["strike"])
   if e>f+1e-6:continue
   if not(float(qh["start_ts"])<=now_ts and now_ts<b<=float(qh["end_ts"])+60.):continue
   a=round(float(qc["ask_no"])+float(qh["ask_yes"]),4);c=round(_net_unit_ask(float(qc["ask_no"]),float(qc.get("fee_rate",.0)),float(qc.get("fee_exponent",1.)))+_net_unit_ask(float(qh["ask_yes"]),float(qh.get("fee_rate",.0)),float(qh.get("fee_exponent",1.))),4)
   if c<=max_box_cost_net:d.append({"box_kind":"PYTH_CLOSE_VS_HIT","asset":str(qc["asset"]),"strike_hit":e,"strike_close":f,"box_cost_net":c,"box_cost_gross":a,"yes_row":qh,"no_row":qc,"close_ts":max(b,float(qh["end_ts"])),"label":f"NO(Close>{f:g}) + YES(Hit>={e:g})"})
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
 A=float(now_ts if now_ts is not None else time.time())
 if ev.get("closed")or ev.get("archived"):return None
 y=ev.get("markets")or[]
 if len(y)<3:return None
 d=None;h,g=.0,1.
 for m in y:
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
 l=_parse_clob_tokens(d);assert l is not None;o=_parse_iso_ts(d.get("gameStartTime")or ev.get("endDate"))or(A+7200.)
 if A>o+6.*3600.:return None
 b=max(o+3.25*3600.,A+1800.);e=[NbaOutcomeLeg(market_id=str(d.get("id")or""),condition_id=str(d.get("conditionId")or""),market_type="moneyline",token_id=l[0],opp_token_id=l[1],side_index=0,side_label="YES",display_label=f"{s} ML",relation="GT",threshold=.0,fee_rate=h,fee_exponent=g),NbaOutcomeLeg(market_id=str(d.get("id")or""),condition_id=str(d.get("conditionId")or""),market_type="moneyline",token_id=l[1],opp_token_id=l[0],side_index=1,side_label="NO",display_label=f"{r} ML",relation="LT",threshold=.0,fee_rate=h,fee_exponent=g)];f=[]
 for m in y:
  if m.get("closed")or m.get("archived"):continue
  z=str(m.get("sportsMarketType")or"").strip().lower()
  if z not in("spreads","totals"):continue
  fr,fe=_extract_market_fee_rate(m);x=_parse_clob_tokens(m)
  if not x:continue
  c=m.get("outcomes")
  if isinstance(c,str):
   try:c=json.loads(c)
   except Exception:c=None
  if not isinstance(c,list)or len(c)<2:continue
  q_str=str(m.get("question")or"")
  if any(bad in q_str.lower()for bad in("1h ","2h ","1q ","2q ","3q ","4q ","half","quarter")):continue
  if z=="spreads":
   w=_SPREAD_FAV_RE.search(q_str)
   if not w:continue
   k=_norm_team(w.group(1));j=float(w.group(2))
   if j>=.0 or not _is_half_integer(j):continue
   t=abs(j);v,u=_norm_team(c[0]),_norm_team(c[1])
   if k==q and v==q and u==p:e.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"spreads",x[0],x[1],0,"YES",f"{s} -{t:g}","GT",t,fr,fe));e.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"spreads",x[1],x[0],1,"NO",f"{r} +{t:g}","LT",t,fr,fe))
   elif k==p and v==p and u==q:e.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"spreads",x[0],x[1],0,"YES",f"{r} -{t:g}","LT",-t,fr,fe));e.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"spreads",x[1],x[0],1,"NO",f"{s} +{t:g}","GT",-t,fr,fe))
  elif z=="totals":
   i=m.get("line")
   if i is None:continue
   n=float(i)
   if n<=50. or not _is_half_integer(n):continue
   if _norm_team(c[0])=="over"and _norm_team(c[1])=="under":f.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"totals",x[0],x[1],0,"YES",f"Over {n:g}","OVER",n,fr,fe));f.append(NbaOutcomeLeg(str(m.get("id")or""),str(m.get("conditionId")or""),"totals",x[1],x[0],1,"NO",f"Under {n:g}","UNDER",n,fr,fe))
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
 e=ev.get("markets")or[]
 if len(e)<3:return None
 b=_parse_iso_ts(ev.get("endDate"))
 if not b:return None
 a=[]
 for m in e:
  if m.get("archived"):continue
  if m.get("closed"):
   op=m.get("outcomePrices")
   if isinstance(op,str):
    try:op=json.loads(op)
    except Exception:op=None
   if not(isinstance(op,list)and len(op)>=2 and float(op[1])>=.99):return None
   continue
  fr,d=_extract_market_fee_rate(m)
  if fr>.0 and not allow_mixed_fees:return None
  c=_parse_clob_tokens(m)
  if not c:return None
  a.append({"market_id":str(m.get("id")or""),"condition_id":str(m.get("conditionId")or""),"label":str(m.get("groupItemTitle")or m.get("question")or""),"yes_token":c[0],"no_token":c[1],"fee_rate":fr,"fee_exponent":d,"rewards_min_size":float(m.get("rewardsMinSize")or.0),"rewards_max_spread":float(m.get("rewardsMaxSpread")or.0)})
 if len(a)<3:return None
 return ZeroFeeNegRiskSlateSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,title=str(ev.get("title")or series_slug),end_ts=float(b),brackets=a)
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
   for kw,a in(("nba","NBA"),("nfl","NFL"),("cfb","CFB"),("nhl","NHL")):
    if kw in c:return a
 return"SPORTS"
def parse_multi_sport_corridor_event(ev,sport_hint="",now_ts=None,skip_nba_fg_zero_fee=True):
 N=float(now_ts if now_ts is not None else time.time())
 if ev.get("closed")or ev.get("archived")or ev.get("negRisk"):return None
 J=ev.get("markets")or[]
 if len(J)<4:return None
 D=_infer_sport_tag(ev,sport_hint);i,h="","";a=None
 for u in("moneyline","spreads","first_half_spreads"):
  for m in J:
   if m.get("closed")or str(m.get("sportsMarketType")or"").strip().lower()!=u:continue
   b=m.get("outcomes")
   if isinstance(b,str):
    try:b=json.loads(b)
    except Exception:b=None
   if isinstance(b,list)and len(b)==2:
    o0,o1=str(b[0]).strip(),str(b[1]).strip()
    if{_norm_team(o0),_norm_team(o1)}not in({"yes","no"},{"over","under"})and _norm_team(o0)!=_norm_team(o1):i,h=o0,o1;a=_parse_iso_ts(m.get("gameStartTime")or ev.get("startDate")or ev.get("endDate"));break
  if i and h:break
 A,z=_norm_team(i),_norm_team(h)
 if a is None:
  for m in J:
   a=_parse_iso_ts(m.get("gameStartTime"))
   if a:break
 if a is None:a=_parse_iso_ts(ev.get("endDate"))or(N+7200.)
 if N>a+6.5*3600.:return None
 e=max(a+3.75*3600.,N+1800.);legs_by_scope={}
 for m in J:
  if m.get("closed")or m.get("archived")or m.get("negRisk"):continue
  M=str(m.get("sportsMarketType")or"").strip().lower()
  if M not in _SPREAD_PERIOD_MAP and M not in _TOTAL_PERIOD_MAP and M not in _TEAM_TOTAL_PERIOD_MAP:continue
  fr,I=_extract_market_fee_rate(m)
  if skip_nba_fg_zero_fee and D=="NBA"and fr==.0 and M in("spreads","totals"):continue
  H=_parse_clob_tokens(m)
  if not H:continue
  b=m.get("outcomes")
  if isinstance(b,str):
   try:b=json.loads(b)
   except Exception:b=None
  if not isinstance(b,list)or len(b)<2:continue
  q_str=str(m.get("question")or"");L=str(m.get("id")or"");K=str(m.get("conditionId")or"")
  if M in _SPREAD_PERIOD_MAP:
   if not A or not z:continue
   l=_SPREAD_PERIOD_MAP[M]
   if l=="FG"and any(bad in q_str.lower()for bad in("1h ","2h ","1q ","2q ","3q ","4q ","half","quarter")):continue
   G=_SPREAD_FAV_RE.search(q_str)
   if not G:continue
   j=_norm_team(G.group(1));t=float(G.group(2))
   if not _is_half_integer(t):continue
   F,E=_norm_team(b[0]),_norm_team(b[1])
   if{F,E}!={A,z}or j not in(A,z):continue
   s=0 if F==j else 1;r=1-s;q,p=H[s],H[r];o="YES"if s==0 else"NO";n="YES"if r==0 else"NO";k=""if l=="FG"else f"{l} ";d=f"{l}:SPREAD"
   if j==A:y=round(-t,2);legs_by_scope.setdefault(d,[]).extend([MultiSportCorridorLeg(L,K,d,q,p,s,o,f"{k}{i} {t:+g}","GT",y,fr,I,False),MultiSportCorridorLeg(L,K,d,p,q,r,n,f"{k}{h} {-t:+g}","LT",y,fr,I,False)])
   else:y=round(t,2);legs_by_scope.setdefault(d,[]).extend([MultiSportCorridorLeg(L,K,d,q,p,s,o,f"{k}{h} {t:+g}","LT",y,fr,I,False),MultiSportCorridorLeg(L,K,d,p,q,r,n,f"{k}{i} {-t:+g}","GT",y,fr,I,False)])
  elif M in _TOTAL_PERIOD_MAP:
   l=_TOTAL_PERIOD_MAP[M]
   if l=="FG"and any(bad in q_str.lower()for bad in("1h ","2h ","1q ","2q ","3q ","4q ","half","quarter","team total")):continue
   c=m.get("line")
   if c is None:continue
   g=float(c)
   if g<=.0 or not _is_half_integer(g):continue
   if _norm_team(b[0])!="over"or _norm_team(b[1])!="under":continue
   k=""if l=="FG"else f"{l} ";d=f"{l}:TOTAL";legs_by_scope.setdefault(d,[]).extend([MultiSportCorridorLeg(L,K,d,H[0],H[1],0,"YES",f"{k}Over {g:g}","OVER",g,fr,I,False),MultiSportCorridorLeg(L,K,d,H[1],H[0],1,"NO",f"{k}Under {g:g}","UNDER",g,fr,I,False)])
  elif M in _TEAM_TOTAL_PERIOD_MAP:
   if not A or not z:continue
   c=m.get("line")
   if c is None:continue
   g=float(c)
   if g<=.0 or not _is_half_integer(g):continue
   if _norm_team(b[0])!="over"or _norm_team(b[1])!="under":continue
   x=q_str.split("O/U")[0].lower()if"O/U"in q_str else q_str.lower();C=A in x;B=z in x
   if C==B:continue
   w=A if C else z;v=i if C else h;l=_TEAM_TOTAL_PERIOD_MAP[M];k=""if l=="FG_TEAM"else f"{l.split('_')[0]} ";d=f"{l}:{w}";legs_by_scope.setdefault(d,[]).extend([MultiSportCorridorLeg(L,K,d,H[0],H[1],0,"YES",f"{k}{v} Over {g:g}","OVER",g,fr,I,False),MultiSportCorridorLeg(L,K,d,H[1],H[0],1,"NO",f"{k}{v} Under {g:g}","UNDER",g,fr,I,False)])
 f={sc:lgs for sc,lgs in legs_by_scope.items()if len({lg.market_id for lg in lgs})>=2}
 if not f:return None
 return MultiSportCorridorSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),sport=D,title=str(ev.get("title")or f"{i} vs. {h}"),team_a=i,team_b=h,start_ts=float(a),settle_est_ts=float(e),legs_by_scope=f)
def detect_multi_sport_corridor_boxes(spec,best_asks_by_token,max_box_cost_net=1.08):
 b=[]
 for h,legs in spec.legs_by_scope.items():
  if h.endswith(":SPREAD"):low_rel,high_rel,a="GT","LT","SPREAD_CORRIDOR"
  else:low_rel,high_rel,a="OVER","UNDER","TOTAL_CORRIDOR"
  e=[lg for lg in legs if lg.relation==low_rel and lg.token_id in best_asks_by_token];c=[lg for lg in legs if lg.relation==high_rel and lg.token_id in best_asks_by_token]
  for l in e:
   k=float(best_asks_by_token[l.token_id])
   if not(.01<=k<=.99):continue
   g=_net_unit_ask(k,l.fee_rate,l.fee_exponent)
   for j in c:
    if l.market_id==j.market_id or l.threshold>=j.threshold-1e-6:continue
    i=float(best_asks_by_token[j.token_id])
    if not(.01<=i<=.99):continue
    f=_net_unit_ask(i,j.fee_rate,j.fee_exponent);d=round(g+f,4)
    if d<=max_box_cost_net:b.append({"box_kind":f"{spec.sport}_{a}","sport":spec.sport,"scope":h,"event_id":spec.event_id,"title":spec.title,"box_cost_net":d,"box_cost_gross":round(k+i,4),"middle_width_pts":round(j.threshold-l.threshold,1),"leg_a":l,"leg_b":j,"close_ts":spec.settle_est_ts,"label":f"{l.display_label} + {j.display_label}"})
 b.sort(key=lambda x:(float(x["box_cost_net"]),-float(x["middle_width_pts"])));return b
@dataclass
class NegRiskConvertSlateSpec:event_id:str;slug:str;title:str;neg_risk_market_id:str;neg_risk_augmented:bool;total_market_count:int;is_closed_convert_safe:bool;end_ts:float;brackets:List[Dict[str,Any]]
def parse_negrisk_convert_event(ev):
 if ev.get("closed")or ev.get("archived"):return None
 if not(ev.get("enableNegRisk")or ev.get("negRisk")):return None
 r=ev.get("markets")or[]
 if len(r)<2:return None
 n=_parse_iso_ts(ev.get("endDate"))
 if not n:return None
 g=str(ev.get("negRiskMarketID")or"").strip().lower();l=bool(ev.get("negRiskAugmented",True));e=len(g)==66 and g.startswith("0x");open_brackets=[];a=True;c=False;k=re.compile(r"(?:\bplaceholder\b|^(?:person|party|option|candidate|team|player)\s+[a-z0-9]{1,2}$)",re.IGNORECASE)
 for m in r:
  j=str(m.get("groupItemTitle")or m.get("question")or"").strip()
  if k.search(j):c=True
  if m.get("archived")or m.get("closed")or m.get("active")is False:a=False;continue
  q=_parse_clob_tokens(m)
  if not q:a=False;continue
  fr,p=_extract_market_fee_rate(m);o=str(m.get("questionID")or"").strip().lower();d=None
  if e and len(o)==66 and o.startswith("0x")and o[:64]==g[:64]:
   try:d=int(o[64:],16)
   except ValueError:d=None
  open_brackets.append({"market_id":str(m.get("id")or""),"condition_id":str(m.get("conditionId")or""),"question_id":o,"question_index":d,"label":j[:48],"yes_token":q[0],"no_token":q[1],"fee_rate":fr,"fee_exponent":p})
 if len(open_brackets)<2:return None
 i=len(r);h={b["question_index"]for b in open_brackets if isinstance(b.get("question_index"),int)};f=bool((not l)and(not c)and e and a and 3<=i<=24 and len(open_brackets)==i and h==set(range(i)))
 if f:open_brackets.sort(key=lambda b:int(b["question_index"]))
 return NegRiskConvertSlateSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),title=str(ev.get("title")or ev.get("slug")or""),neg_risk_market_id=g,neg_risk_augmented=l,total_market_count=i,is_closed_convert_safe=f,end_ts=float(n),brackets=open_brackets)
def detect_negrisk_no_pair_boxes(spec,best_no_asks,max_box_cost_net=1.04):
 d=[]
 for b in spec.brackets:
  nt=b["no_token"]
  if nt not in best_no_asks:continue
  px=float(best_no_asks[nt])
  if.01<=px<=.985:d.append((b,px,_net_unit_ask(px,float(b["fee_rate"]),float(b["fee_exponent"]))))
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
 p0=m[0][0];j=(min(.5,max(.0,(fee_rate*((p0*(1.-p0))**fee_exp))/p0))if(is_ask and fee_rate>.0 and.0<p0<1.)else.0);c=(math.ceil((float(shares_req)/(1.-j))*1e2-1e-9)/1e2)if(is_ask and j>.0)else float(shares_req);h=float(c);f=.0;b=m[0][0];i=round(m[0][0]*m[0][1],2)
 for px,sz in m:
  l=min(h,sz);f+=l*px;b=px;h-=l
  if h<=1e-6:break
 if h>1e-5:return None
 k=f/c
 if is_ask:e=_net_unit_ask(k,fee_rate,fee_exp);a=float(shares_req)*e;d=max(.0,a-float(shares_req)*k)
 else:g=fee_rate*((k*(1.-k))**fee_exp)if fee_rate>.0 else.0;d=float(shares_req)*g;a=max(.0,f-d);e=a/float(shares_req)
 return{"vwap":round(k,5),"gross_shares":round(c,2),"net_per_share":round(e,5),"net_cash_usd":round(a,4),"fee_usd":round(d,4),"worst_px":round(b,4),"l1_usd":i}
def detect_negrisk_convert_positions_arbs(spec,books_by_token,target_budget_usd=120.,min_net_edge_per_share=.01,min_shares=8,min_net_edge_per_set=None):
 if min_net_edge_per_set is not None:min_net_edge_per_share=float(min_net_edge_per_set)
 if not spec.is_closed_convert_safe:return[]
 n_tot=len(spec.brackets)
 if n_tot<3:return[]
 scored=[]
 for H,b in enumerate(spec.brackets):
  bk_y=books_by_token.get(b["yes_token"])or{};bk_n=books_by_token.get(b["no_token"])or{};B=sorted([(float(x["price"]),float(x["size"]))for x in(bk_n.get("asks")or[])if float(x.get("price",0))>0 and float(x.get("size",0))>0],key=lambda t:t[0]);A=sorted([(float(x["price"]),float(x["size"]))for x in(bk_y.get("bids")or[])if float(x.get("price",0))>0 and float(x.get("size",0))>0],key=lambda t:-t[0]);fr,fe=float(b["fee_rate"]),float(b["fee_exponent"]);q=_net_unit_ask(B[0][0],fr,fe)if B else 9.9;u=B[0][1]if B else.0
  if A:G=A[0][0];c=max(.0,G-(fr*((G*(1.-G))**fe)if fr>0 else.0));d=A[0][1]
  else:c,d=-1.,.0
  p=c+q-1.;scored.append((p,H,b,q,u,c,d))
 scored.sort(key=lambda t:-t[0]);m=[]
 if scored[0][5]>.0:z=[scored[0][1]];F=[t[1]for t in scored[1:]];m.append((sorted(F),z))
 if n_tot>=4 and scored[0][5]>.0 and scored[1][5]>.0:y=sorted([scored[0][1],scored[1][1]]);E=[t[1]for t in scored[2:]];m.append((sorted(E),y))
 D=[];by_orig={i:spec.brackets[i]for i in range(n_tot)}
 for no_idxs,comp_idxs in m:
  C=len(no_idxs)
  if C<2:continue
  j=sum(next(t[3]for t in scored if t[1]==i)for i in no_idxs)
  if j<=.0 or j>=float(C):continue
  o=min([next(t[4]for t in scored if t[1]==i)for i in no_idxs]+[next(t[6]for t in scored if t[1]==k)for k in comp_idxs]);v=int(math.floor(min(o,target_budget_usd/max(.25,j))))
  if v<min_shares:continue
  no_walks=[];a=True
  for i in no_idxs:
   bi=by_orig[i];wi=_walk_side_exact_shares((books_by_token.get(bi["no_token"])or{}).get("asks")or[],float(v),float(bi["fee_rate"]),float(bi["fee_exponent"]),is_ask=True)
   if wi is None:a=False;break
   no_walks.append((bi,wi))
  if not a:continue
  yes_walks=[]
  for k in comp_idxs:
   s=by_orig[k];wk=_walk_side_exact_shares((books_by_token.get(s["yes_token"])or{}).get("bids")or[],float(v),float(s["fee_rate"]),float(s["fee_exponent"]),is_ask=False)
   if wk is None:a=False;break
   yes_walks.append((s,wk))
  if not a:continue
  g=sum(w["net_per_share"]for _,w in no_walks);f=sum(w["net_per_share"]for _,w in yes_walks);l=float(C-1);e=l+f;r=round(e-g,5)
  if r<min_net_edge_per_share:continue
  q_indices=[int(by_orig[i]["question_index"])for i in no_idxs];h=sum(1<<qi for qi in q_indices);n=min([w["l1_usd"]for _,w in no_walks]+[w["l1_usd"]for _,w in yes_walks]);D.append({"mode":"NR_CONV_POSITIONS_INSTANT","event_id":spec.event_id,"slug":spec.slug,"title":spec.title,"neg_risk_market_id":spec.neg_risk_market_id,"m_no_legs":C,"n_total":n_tot,"question_indices":q_indices,"no_question_indices":q_indices,"index_set":h,"index_set_int":h,"shares":v,"no_cost_per_share":round(g,4),"no_cost_net_per_set":round(g,4),"usdc_converted_per_share":l,"usdc_released_per_set":l,"yes_bid_proceeds_per_share":round(f,4),"yes_bid_proceeds_net_per_set":round(f,4),"net_proceeds_per_share":round(e,4),"net_edge_per_share":round(r,4),"net_edge_per_set":round(r,4),"total_cost_usd":round(sum(w["net_cash_usd"]for _,w in no_walks),2),"total_net_profit_usd":round(v*r,2),"total_fee_usd":round(sum(w["fee_usd"]for _,w in no_walks)+sum(w["fee_usd"]for _,w in yes_walks),4),"l1_usd":round(n,2),"no_legs":[{"token_id":b["no_token"],"bracket":b,"walk":w}for b,w in no_walks],"yes_sell_legs":[{"token_id":b["yes_token"],"bracket":b,"walk":w}for b,w in yes_walks],"close_ts":spec.end_ts,"label":f"CONV({C}xNO->${C-1}+SELL[{','.join(b['label'][:14]for b,_ in yes_walks)}])"})
 D.sort(key=lambda x:-float(x["net_edge_per_share"]));return D
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
  lo,hi=int(a.group(1)),int(a.group(2))
  if hi>=lo>=0:return(lo,float(hi))
 return None
def _parse_et_window_from_description(desc,fallback_end_ts):
 m=_DESC_WINDOW_RE.search(str(desc or""))
 if m:
  c,b,a,g,f,e=m.groups();j=int(f);i=int(b)if b else j
  try:
   d=datetime.strptime(f"{c} {i} {a.upper().replace(' ','')}","%B %d %Y %I:%M%p");h=datetime.strptime(f"{g} {j} {e.upper().replace(' ','')}","%B %d %Y %I:%M%p")
   if d>h and not b:d=d.replace(year=j-1)
   t1=d.replace(tzinfo=NY_TZ).timestamp();t2=h.replace(tzinfo=NY_TZ).timestamp()
   if t2>t1:return t1,t2
  except Exception:pass
 return fallback_end_ts-7.*86400.,fallback_end_ts
def parse_counting_slate_event(ev,series_slug,handle):
 if ev.get("closed")or ev.get("archived"):return None
 e=_parse_iso_ts(ev.get("endDate"))
 if not e:return None
 l=ev.get("markets")or[]
 if len(l)<3:return None
 k=str(ev.get("description")or(l[0].get("description")if l else"")or"");d,f=_parse_et_window_from_description(k,float(e));a=0;c=[]
 for m in l:
  if m.get("archived"):continue
  n=str(m.get("groupItemTitle")or m.get("question")or"");j=parse_count_bracket_bounds(n)
  if j is None:continue
  i,h=j
  if m.get("closed"):
   op=m.get("outcomePrices")
   if isinstance(op,str):
    try:op=json.loads(op)
    except Exception:op=None
   if isinstance(op,list)and len(op)>=2 and float(op[1])>=.99 and math.isfinite(h):a=max(a,int(h)+1)
   elif isinstance(op,list)and len(op)>=2 and float(op[0])>=.99:return None
   continue
  fr,fe=_extract_market_fee_rate(m);g=_parse_clob_tokens(m)
  if not g:continue
  c.append(CountingBracket(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),label=n,low_count=i,high_count=h,yes_token=g[0],no_token=g[1],fee_rate=fr,rewards_min_size=float(m.get("rewardsMinSize")or.0),rewards_max_spread=float(m.get("rewardsMaxSpread")or.0),neg_risk=bool(m.get("negRisk")if m.get("negRisk")is not None else ev.get("negRisk",True)),fee_exponent=fe))
 if len(c)<2:return None
 c.sort(key=lambda b:b.low_count);return CountingSlateSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),series_slug=series_slug,handle=handle,title=str(ev.get("title")or series_slug),window_start_ts=d,window_end_ts=f,gamma_closed_floor=a,brackets=c)
def fetch_xtracker_user_stats_sync(handle,ttl_sec=60.):
 o=time.time();d=_XTRACKER_CACHE.get(handle)
 if d and(o-d[0])<ttl_sec:return d[1]
 n={}
 try:
  m=urllib.request.Request(f"https://xtracker.polymarket.com/api/users/{handle}",headers={"User-Agent":CHROME_UA})
  with urllib.request.urlopen(m,timeout=5.)as r:c=json.loads(r.read().decode("utf-8",errors="replace")).get("data")or{}
  for tr in(c.get("trackings")or[]):
   if not tr.get("isActive"):continue
   l=str(tr.get("id")or"");i=str(tr.get("marketLink")or"");h=i.rstrip("/").split("/")[-1]if i else""
   if not l or not h:continue
   g=urllib.request.Request(f"https://xtracker.polymarket.com/api/trackings/{l}?includeStats=true",headers={"User-Agent":CHROME_UA})
   with urllib.request.urlopen(g,timeout=5.)as rt:td=json.loads(rt.read().decode("utf-8",errors="replace")).get("data")or{}
   f=td.get("stats")or{};b=[];a=False
   for k in(f.get("daily")or[]):
    e=str(k.get("date")or"").strip()
    if len(e)==10:a=True
    j=_parse_iso_ts(e)
    if j is not None:b.append((float(j),int(k.get("count")or 0)))
   n[h]={"tracking_id":l,"total":int(f.get("total")or 0),"start_ts":_parse_iso_ts(td.get("startDate"))or.0,"end_ts":_parse_iso_ts(td.get("endDate"))or.0,"hourly":b,"daily_tz_pad":1.8e4 if a else.0}
  _XTRACKER_CACHE[handle]=(o,n)
 except Exception as exc:
  if d:return d[1]
 return n
def evaluate_counting_dead_no_locks(slate,xtracker_by_slug,safety_post_buffer=2):
 xt=xtracker_by_slug.get(slate.slug)or{};b=int(xt.get("total")or 0);a=max(int(slate.gamma_closed_floor),b);c=[]
 for br in slate.brackets:
  if math.isfinite(br.high_count)and a>=int(br.high_count)+max(1,safety_post_buffer):c.append(br)
 return a,c
def detect_counting_subwindow_boxes(slates,best_asks_by_token,xtracker_by_handle,max_box_cost_net=1.05):
 h=[]
 for i,s_short in enumerate(slates):
  for j,s_long in enumerate(slates):
   if i==j or s_short.handle!=s_long.handle or s_short.event_id==s_long.event_id:continue
   if not(s_long.window_start_ts<=s_short.window_start_ts and s_short.window_end_ts<=s_long.window_end_ts and(s_long.window_end_ts-s_long.window_start_ts)>(s_short.window_end_ts-s_short.window_start_ts)+3600.):continue
   xt_long=(xtracker_by_handle.get(s_long.handle)or{}).get(s_long.slug)or{};a=0
   if xt_long.get("hourly")and s_short.window_start_ts>s_long.window_start_ts+1800.:tz_pad=float(xt_long.get("daily_tz_pad")or.0);a=sum(cnt for ts_h,cnt in xt_long["hourly"]if(ts_h-tz_pad)>=s_long.window_start_ts and(ts_h+86400.+tz_pad)<=s_short.window_start_ts)
   n=[b for b in s_short.brackets if not math.isfinite(b.high_count)];m=[b for b in s_long.brackets if not math.isfinite(b.high_count)]
   for bs in n:
    g=best_asks_by_token.get(bs.no_token)
    if g is None:continue
    for bl in m:
     if bl.low_count<=a+bs.low_count:
      d=best_asks_by_token.get(bl.yes_token)
      if d is None:continue
      e=round(_net_unit_ask(float(g),bs.fee_rate,bs.fee_exponent)+_net_unit_ask(float(d),bl.fee_rate,bl.fee_exponent),4)
      if e<=max_box_cost_net:h.append({"box_kind":"TW1_UPPER_SUBWINDOW","handle":s_short.handle,"banked":a,"box_cost_gross":round(float(g)+float(d),4),"box_cost_net":e,"leg_a":{"token_id":bs.no_token,"opp_token_id":bs.yes_token,"condition_id":bs.condition_id,"side":"NO","label":f"NO_48H[{bs.label}]","market_id":bs.market_id,"fee_rate":bs.fee_rate,"fee_exponent":bs.fee_exponent,"strike":float(bs.low_count),"neg_risk":bs.neg_risk},"leg_b":{"token_id":bl.yes_token,"opp_token_id":bl.no_token,"condition_id":bl.condition_id,"side":"YES","label":f"YES_7D[{bl.label}]","market_id":bl.market_id,"fee_rate":bl.fee_rate,"fee_exponent":bl.fee_exponent,"strike":float(bl.low_count),"neg_risk":bl.neg_risk},"close_ts":max(s_short.window_end_ts,s_long.window_end_ts),"label":f"{s_short.handle} NO({bs.label} short) + YES({bl.label} long, banked={a})"})
   l=[b for b in s_short.brackets if b.low_count==0 and math.isfinite(b.high_count)];k=[b for b in s_long.brackets if b.low_count==0 and math.isfinite(b.high_count)]
   for bl in k:
    f=best_asks_by_token.get(bl.no_token)
    if f is None:continue
    for bs in l:
     if int(bl.high_count)<=a+int(bs.high_count):
      c=best_asks_by_token.get(bs.yes_token)
      if c is None:continue
      e=round(_net_unit_ask(float(f),bl.fee_rate,bl.fee_exponent)+_net_unit_ask(float(c),bs.fee_rate,bs.fee_exponent),4)
      if e<=max_box_cost_net:h.append({"box_kind":"TW1_LOWER_SUBWINDOW","handle":s_short.handle,"banked":a,"box_cost_gross":round(float(f)+float(c),4),"box_cost_net":e,"leg_a":{"token_id":bl.no_token,"opp_token_id":bl.yes_token,"condition_id":bl.condition_id,"side":"NO","label":f"NO_7D[{bl.label}]","market_id":bl.market_id,"fee_rate":bl.fee_rate,"fee_exponent":bl.fee_exponent,"strike":float(bl.high_count),"neg_risk":bl.neg_risk},"leg_b":{"token_id":bs.yes_token,"opp_token_id":bs.no_token,"condition_id":bs.condition_id,"side":"YES","label":f"YES_48H[{bs.label}]","market_id":bs.market_id,"fee_rate":bs.fee_rate,"fee_exponent":bs.fee_exponent,"strike":float(bs.high_count),"neg_risk":bs.neg_risk},"close_ts":max(s_short.window_end_ts,s_long.window_end_ts),"label":f"{s_short.handle} NO({bl.label} long) + YES({bs.label} short, banked={a})"})
 h.sort(key=lambda x:float(x["box_cost_net"]));return h
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
 G=[]
 for ev in fomc_events:
  if ev.get("closed"):continue
  j=str(ev.get("slug")or"").lower();e=_parse_iso_ts(ev.get("endDate"))or.0;A=0 if"october"in j else(1 if"december"in j else(2 if"january"in j else-1))
  if A<0 or e<=0:continue
  z=("OCT","DEC","JAN")[A]
  for m in(ev.get("markets")or[]):
   if m.get("closed"):continue
   fr,fe=_extract_market_fee_rate(m);h=_parse_clob_tokens(m);I=_classify_single_fomc_label(str(m.get("groupItemTitle")or m.get("question")or""))
   if not h or not I:continue
   c=0;k=_FOMC_LABEL_ACTION_SET.get(I,(I,))
   for r,st in enumerate(FOMC_STATES_3M):
    if st[A]in k:c|=(1<<r)
   q=str(m.get("id")or"");o=str(m.get("conditionId")or"");F=m.get("negRisk")if isinstance(m.get("negRisk"),bool)else(ev.get("negRisk")if isinstance(ev.get("negRisk"),bool)else None);G.append({"event_group":f"FOMC_{z}","market_id":q,"condition_id":o,"token_id":h[0],"opp_token_id":h[1],"side":"YES","label":f"YES({z}:{I})","mask":c,"end_ts":e,"fee_rate":fr,"fee_exponent":fe,"neg_risk":F});G.append({"event_group":f"FOMC_{z}","market_id":q,"condition_id":o,"token_id":h[1],"opp_token_id":h[0],"side":"NO","label":f"NO({z}:{I})","mask":ALL_FOMC_MASK^c,"end_ts":e,"fee_rate":fr,"fee_exponent":fe,"neg_risk":F})
 for ev in parlay_events:
  if ev.get("closed"):continue
  j=str(ev.get("slug")or"").lower();e=_parse_iso_ts(ev.get("endDate"))or.0;g="oct-jan"in j;f="sepdec"in j and sep_2026_realized_action is not None
  if not(g or f)or e<=0:continue
  y="PARLAY_OCT_JAN"if g else"PARLAY_SEP_DEC";b=0;a=False;d=None
  for m in(ev.get("markets")or[]):
   lbl=str(m.get("groupItemTitle")or"").strip();i=lbl.lower()=="other"
   if m.get("closed"):
    if not i:a=True
    continue
   fr,fe=_extract_market_fee_rate(m);h=_parse_clob_tokens(m)
   if not h:
    if not i:a=True
    continue
   if i:d=(m,h,fr,fe);continue
   x=[p.strip()for p in re.split(r"[-–—/]",lbl)if p.strip()]
   if len(x)!=3:a=True;continue
   c=0
   for r,(w,v,u)in enumerate(FOMC_STATES_3M):
    if g:ok=_parlay_word_matches(x[0],w)and _parlay_word_matches(x[1],v)and _parlay_word_matches(x[2],u)
    else:assert sep_2026_realized_action is not None;ok=_parlay_word_matches(x[0],sep_2026_realized_action)and _parlay_word_matches(x[1],w)and _parlay_word_matches(x[2],v)
    if ok:c|=(1<<r)
   if c==0:a=True;continue
   b|=c;q=str(m.get("id")or"");o=str(m.get("conditionId")or"");E=m.get("negRisk")if isinstance(m.get("negRisk"),bool)else(ev.get("negRisk")if isinstance(ev.get("negRisk"),bool)else None);G.append({"event_group":y,"market_id":q,"condition_id":o,"token_id":h[0],"opp_token_id":h[1],"side":"YES","label":f"YES({y}:{lbl})","mask":c,"end_ts":e,"fee_rate":fr,"fee_exponent":fe,"neg_risk":E});G.append({"event_group":y,"market_id":q,"condition_id":o,"token_id":h[1],"opp_token_id":h[0],"side":"NO","label":f"NO({y}:{lbl})","mask":ALL_FOMC_MASK^c,"end_ts":e,"fee_rate":fr,"fee_exponent":fe,"neg_risk":E})
  if d is not None and not a:H,n,D,C=d;l=ALL_FOMC_MASK^b;t=str(H.get("id")or"");s=str(H.get("conditionId")or"");B=H.get("negRisk")if isinstance(H.get("negRisk"),bool)else(ev.get("negRisk")if isinstance(ev.get("negRisk"),bool)else None);G.append({"event_group":y,"market_id":t,"condition_id":s,"token_id":n[0],"opp_token_id":n[1],"side":"YES","label":f"YES({y}:Other)","mask":l,"end_ts":e,"fee_rate":D,"fee_exponent":C,"neg_risk":B});G.append({"event_group":y,"market_id":t,"condition_id":s,"token_id":n[1],"opp_token_id":n[0],"side":"NO","label":f"NO({y}:Other)","mask":ALL_FOMC_MASK^l,"end_ts":e,"fee_rate":D,"fee_exponent":C,"neg_risk":B})
 return G
OIL_SENATE_STATES=[(o,p)for o in("LT80","B80_85","GE85")for p in("DEM","REP","OTHER")];ALL_OIL_SENATE_MASK=(1<<len(OIL_SENATE_STATES))-1
def build_oil_senate_truth_table_legs(events_by_slug):
 p=[]
 for o,ev in events_by_slug.items():
  if not ev or ev.get("closed"):continue
  g=_parse_iso_ts(ev.get("endDate"))or.0
  if g<=0:continue
  j=o.lower()
  for m in(ev.get("markets")or[]):
   if m.get("closed"):continue
   fr,fe=_extract_market_fee_rate(m);n=_parse_clob_tokens(m)
   if not n:continue
   s=str(m.get("groupItemTitle")or m.get("question")or"").strip();ll=s.lower();a=0
   if"which-party-will-win-the-senate"in j:
    b="DEM"if"democrat"in ll else("REP"if"republican"in ll else None)
    if not b:continue
    for e,(_,c)in enumerate(OIL_SENATE_STATES):
     if c==b:a|=(1<<e)
    eg="SENATE_MAIN"
   elif"pending-oil"in j:
    b="DEM"if("d senate"in ll or"democrat"in ll)else("REP"if("r senate"in ll or"republican"in ll)else None);f=85 if"85"in ll else(80 if"80"in ll else 0);i="<"in ll or"below"in ll or"less"in ll;h="≥"in ll or">="in ll or"above"in ll or"greater"in ll
    if not b or f not in(80,85)or(i==h):continue
    for e,(l,c)in enumerate(OIL_SENATE_STATES):
     if c!=b:continue
     d=((l=="LT80"if i else l in("B80_85","GE85"))if f==80 else(l in("LT80","B80_85")if i else l=="GE85"))
     if d:a|=(1<<e)
    eg=f"OIL_{f}_SENATE"
   else:continue
   r=str(m.get("id")or"");q=str(m.get("conditionId")or"");k=m.get("negRisk")if isinstance(m.get("negRisk"),bool)else(ev.get("negRisk")if isinstance(ev.get("negRisk"),bool)else None);p.append({"event_group":eg,"market_id":r,"condition_id":q,"token_id":n[0],"opp_token_id":n[1],"side":"YES","label":f"YES[{s}]","mask":a,"end_ts":g,"fee_rate":fr,"fee_exponent":fe,"neg_risk":k});p.append({"event_group":eg,"market_id":r,"condition_id":q,"token_id":n[1],"opp_token_id":n[0],"side":"NO","label":f"NO[{s}]","mask":ALL_OIL_SENATE_MASK^a,"end_ts":g,"fee_rate":fr,"fee_exponent":fe,"neg_risk":k})
 return p
def find_cross_event_bitmask_boxes(legs,best_asks_by_token,all_states_mask,max_2leg_cost=1.05,max_3leg_cost=1.03):
 c=[]
 for lg in legs:
  p=best_asks_by_token.get(str(lg["token_id"]));m=int(lg["mask"])
  if p is not None and.002<=float(p)<=.995 and 0<m<all_states_mask:h=float(lg.get("fee_rate")or.0);g=float(lg.get("fee_exponent")or 1.);e=_net_unit_ask(float(p),h,g);c.append((e,float(p),m,lg))
 o=[];n=len(c);b=set()
 for i in range(n):
  a1,g1,m1,l1=c[i]
  for j in range(i+1,n):
   a2,g2,m2,l2=c[j]
   if l1["market_id"]==l2["market_id"]or l1["event_group"]==l2["event_group"]:continue
   if(m1|m2)==all_states_mask:
    f=round(a1+a2,4);b.add((i,j))
    if f<=max_2leg_cost:a=bin(m1&m2).count("1");o.append({"n_legs":2,"box_cost_gross":round(g1+g2,4),"box_cost_net":f,"double_pay_states":a,"legs":[l1,l2],"close_ts":max(float(l1["end_ts"]),float(l2["end_ts"])),"label":f"{l1['label']} + {l2['label']}"})
 for i in range(n):
  a1,g1,m1,l1=c[i]
  if a1>=max_3leg_cost:continue
  for j in range(i+1,n):
   if(i,j)in b:continue
   a2,g2,m2,l2=c[j]
   if a1+a2>=max_3leg_cost or l1["market_id"]==l2["market_id"]:continue
   l=m1|m2
   if l in(m1,m2):continue
   for k in range(j+1,n):
    if(i,k)in b or(j,k)in b:continue
    a3,g3,m3,l3=c[k];d=round(a1+a2+a3,4)
    if d>max_3leg_cost:continue
    if l3["market_id"]in(l1["market_id"],l2["market_id"]):continue
    if len({l1["event_group"],l2["event_group"],l3["event_group"]})<2:continue
    if(l|m3)==all_states_mask and(m1|m3)!=all_states_mask and(m2|m3)!=all_states_mask:o.append({"n_legs":3,"box_cost_gross":round(g1+g2+g3,4),"box_cost_net":d,"double_pay_states":0,"legs":[l1,l2,l3],"close_ts":max(float(l1["end_ts"]),float(l2["end_ts"]),float(l3["end_ts"])),"label":f"{l1['label']} + {l2['label']} + {l3['label']}"})
 o.sort(key=lambda x:(float(x["box_cost_net"]),int(x["n_legs"])));return o
def walk_equal_shares_overround_bids(legs_bids_spec,target_mint_budget_usd=1e2,min_net_proceeds_per_set=1.004,min_shares=8.):
 if len(legs_bids_spec)<2 or target_mint_budget_usd<=0:return{"filled":False}
 parsed_books=[];e=float("inf");a=.0
 for sp in legs_bids_spec:
  fr=float(sp.get("fee_rate")or.0);g=float(sp.get("fee_exponent")or 1.);m=sorted([(float(b["price"]),float(b["size"]))for b in(sp.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0])
  if not m:return{"filled":False}
  p0,s0=m[0];l=fr*((p0*(1.-p0))**g)if fr>0 else.0;a+=(p0-l);e=min(e,s0);parsed_books.append((m,fr,g))
 if a<min_net_proceeds_per_set:return{"filled":False,"l1_net_proceeds":round(a,4)}
 i=min(float(target_mint_budget_usd),min(sum(s for _,s in bds)for bds,_,_ in parsed_books));k=math.floor(i)
 if k<min_shares:return{"filled":False,"l1_net_proceeds":round(a,4)}
 d=.0;c=.0
 for bds,fr,g in parsed_books:
  h=float(k)
  for px,sz in bds:
   j=min(h,sz);d+=j*px
   if fr>0:c+=j*fr*((px*(1.-px))**g)
   h-=j
   if h<=1e-9:break
  if h>1e-6:return{"filled":False}
 f=(d-c)/k
 if f<min_net_proceeds_per_set:return{"filled":False,"l1_net_proceeds":round(a,4)}
 return{"filled":True,"shares":float(k),"mint_cost_per_set":1.,"gross_proceeds_per_set":round(d/k,4),"net_proceeds_per_set":round(f,4),"net_edge_per_set":round(f-1.,4),"fee_usd":round(c,4),"spent_usd":round(float(k),2),"l1_usd":round(e,2)}
def walk_position_overround_bid_unwind(legs_bids_spec,exact_shares,min_net_proceeds_per_set=1.004):
 k=float(exact_shares)
 if len(legs_bids_spec)<2 or k<=.0:return{"filled":False}
 d=.0;c=.0;f=[]
 for sp in legs_bids_spec:
  fr=float(sp.get("fee_rate")or.0);j=float(sp.get("fee_exponent")or 1.);i=sorted([(float(b["price"]),float(b["size"]))for b in(sp.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0])
  if not i:return{"filled":False}
  g=k;a=i[0][0]
  for px,sz in i:
   h=min(g,sz);d+=h*px
   if fr>.0:c+=h*fr*((px*(1.-px))**j)
   a=px;g-=h
   if g<=1e-9:break
  if g>1e-6:return{"filled":False}
  f.append(round(a,4))
 e=(d-c)/k
 if e<min_net_proceeds_per_set:return{"filled":False,"net_proceeds_per_set":round(e,4)}
 return{"filled":True,"shares":round(k,4),"gross_proceeds_per_set":round(d/k,4),"net_proceeds_per_set":round(e,4),"fee_usd":round(c,4),"worst_leg_bids":f}
def evaluate_locked_market_reward_carry(p_lock,best_bid,best_ask,rewards_min_size,rewards_max_spread_cents,fee_rate=.0):
 if fee_rate>.0 or p_lock<.995 or rewards_min_size<=.0 or best_ask<=.96:return{"eligible":False}
 d=round(min(max(best_bid,.96),min(best_ask-.005,.989)),3);c=float(rewards_max_spread_cents)/1e2 if rewards_max_spread_cents>.5 else float(rewards_max_spread_cents or.03);a=(best_ask-d)<=max(.02,c+1e-6);b=round(p_lock-d,4)
 if not(.955<=d<best_ask and b>=.008 and a):return{"eligible":False}
 return{"eligible":True,"resting_bid":d,"carry_edge":b,"rewards_min_size":rewards_min_size,"rewards_max_spread":round(c,4)}
_AAA_AS_OF_RE=re.compile(r"Price\s+as\s+of\s+(\d{1,2})/(\d{1,2})/(\d{2,4})",re.IGNORECASE);_AAA_ROW_PRICES_RE=re.compile(r"\$(\d+\.\d{3,4})")
def parse_aaa_gas_html(html):
 f=_AAA_AS_OF_RE.search(str(html or""));e=[float(x)for x in _AAA_ROW_PRICES_RE.findall(str(html or""))if 1.5<=float(x)<=9.5]
 if not f or len(e)<6:return None
 mo,dy,d=int(f.group(1)),int(f.group(2)),int(f.group(3));yr=2000+d if d<100 else d
 try:a=date(yr,mo,dy)
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
 s=str(label or"").strip();m1=_GAS_LT_RE.search(s)
 if m1:return(.0,float(m1.group(1))-1e-6)
 m2=_GAS_PL_RE.search(s)
 if m2:return(float(m2.group(1)),float("inf"))
 m3=_GAS_RG_RE.search(s)
 if m3:return(float(m3.group(1)),float(m3.group(2)))
 return None
def is_in_scheduled_macro_catalyst_window(now_ts):
 dt=datetime.fromtimestamp(now_ts,tz=NY_TZ)
 if dt.weekday()>=5:return False,""
 hm=dt.hour*60+dt.minute
 if 8*60+29<=hm<=8*60+45:return True,"US_0830_MACRO_RELEASE"
 if dt.weekday()in(2,3)and(10*60+29<=hm<=10*60+45):return True,"EIA_1030_PETROLEUM"
 if dt.weekday()==2 and(13*60+59<=hm<=14*60+45):return True,"FOMC_1400_DECISION"
 return False,""
def evaluate_pyth_catalyst_shock(asset,prev_spot,cur_spot,strike,direction,eff_session_hours,sigma_session,now_ts):
 g,c=is_in_scheduled_macro_catalyst_window(now_ts)
 if not g or prev_spot<=0 or cur_spot<=0 or eff_session_hours<=.1:return{"eligible":False}
 i=(cur_spot-prev_spot)/prev_spot;b=.0035 if asset=="SPY"else.0045
 if abs(i)<b:return{"eligible":False}
 e=(eff_session_hours/1638.)*(365.25*86400.);a=first_passage_touch_prob(prev_spot,strike,e,sigma_session,direction,wick_vol_multiplier=1.1);d=first_passage_touch_prob(cur_spot,strike,e,sigma_session,direction,wick_vol_multiplier=1.1);dp=d-a
 if abs(dp)<.055:return{"eligible":False}
 h="YES"if dp>0 else"NO";f=d if h=="YES"else(1.-d);return{"eligible":bool(.22<=f<=.94),"catalyst":c,"side":h,"p_fair":round(f,4),"delta_p":round(abs(dp),4),"ret_pct":round(i*1e2,3)}
def evaluate_ai_elo_ci_lock(leaderboard_rows,snapshot_ts,now_ts,tte_sec,max_snapshot_age_sec=21600.):
 if not leaderboard_rows or(now_ts-snapshot_ts)>max_snapshot_age_sec or not(6e2<=tte_sec<=129600.):return{"eligible":False,"reason":"stale_or_outside_window"}
 rows_s=sorted(leaderboard_rows,key=lambda r:float(r.get("rating")or.0),reverse=True)
 if len(rows_s)<2:return{"eligible":False}
 e=rows_s[0];top_org=str(e.get("organization")or"").strip();b=float(e.get("rating_q025")or.0);a=max((float(r.get("rating_q975")or.0)for r in rows_s[1:]if str(r.get("organization")or"").strip()!=top_org),default=.0);d=b-a
 if not top_org or d<6.:return{"eligible":False,"ci_gap":round(d,2)}
 c=min(.992,.955+.0025*min(15.,d-6.));return{"eligible":True,"leader_org":top_org,"ci_gap":round(d,2),"p_lock":round(c,4)}
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
 h=str(m.get("umaResolutionStatus")or"").strip().lower()
 if h!="proposed":return False,f"STATUS_{h.upper()or'NONE'}"
 hist=[str(x).strip().lower()for x in _parse_json_list(m.get("umaResolutionStatuses"))]
 if any(x in("disputed","flagged","reset")for x in hist):return False,"PRIOR_DISPUTE_HISTORY"
 if hist.count("proposed")>2:return False,"EXCESS_PROPOSAL_CYCLES"
 b=str(m.get("resolvedBy")or"").strip().lower()
 if b not in VERIFIED_UMA_ADAPTERS:return False,"UNVERIFIED_ADAPTER"
 c=bool(m.get("negRisk"))or(b in NEGRISK_UMA_ADAPTERS);a=str(m.get("negRiskRequestID")if c else m.get("questionID")or"").strip()
 if not _HEX32_RE.match(a):return False,"MISSING_REQUEST_ID"
 f=_parse_clob_tokens(m);outs=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))]
 if not f or len(outs)!=2:return False,"NON_BINARY_OUTCOMES"
 if any(o.lower()in("other","placeholder","unknown")for o in outs):return False,"PLACEHOLDER_OUTCOME"
 q=str(m.get("question")or"");e=str(m.get("description")or"");d=f"{q}\n{e}"
 if _SUBJECTIVE_VETO_RE.search(d):return False,"SUBJECTIVE_OR_SPEECH_VETO"
 g=str(m.get("sportsMarketType")or"").strip().lower()
 if g:return True,f"SPORTS_{g.upper()}"
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
  c=_norm_team(d.group(1));b=_norm_team(d.group(2));o0,o1=_norm_team(outcomes[0]),_norm_team(outcomes[1]);a=c if proposed_price==0 else b
  if a==o0 and a!=o1:return 0
  if a==o1 and a!=o0:return 1
 return 0 if proposed_price==ONE_E18 else 1
def verify_uma_onchain_proposal_sync(m,rpc_url=None,now_ts=None,min_proposal_age_sec=120.,max_rem_challenge_sec=7500.,timeout=5.):
 T,q=is_objective_uma_market(m)
 if not T:return{"verified":False,"reason":q}
 Z=float(now_ts if now_ts is not None else time.time());Y=rpc_url or os.getenv("POLYGON_RPC_URL")or DEFAULT_POLYGON_RPC;N=str(m.get("resolvedBy")or"").strip().lower();V=bool(m.get("negRisk"))or(N in NEGRISK_UMA_ADAPTERS);p=str(m.get("negRiskRequestID")if V else m.get("questionID")or"").strip().lower();X=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))];W=_parse_clob_tokens(m);assert W is not None
 try:
  f=_OO_ADDR_CACHE.get(N);M=[{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":N,"data":f"0x{SEL_GET_QUESTION}{p[2:]}"},"latest"]}]
  if not f:M.append({"jsonrpc":"2.0","id":2,"method":"eth_call","params":[{"to":N,"data":f"0x{SEL_OPTIMISTIC_ORACLE}"},"latest"]})
  resp_1=_rpc_post(Y,M,timeout=timeout);L={int(r["id"]):r.get("result")for r in resp_1 if isinstance(r,dict)and"id"in r};S=str(L.get(1)or"")
  if not S.startswith("0x")or len(S)<2+14*64:return{"verified":False,"reason":"INVALID_GET_QUESTION_BYTES"}
  if not f:
   R=str(L.get(2)or"")
   if not R.startswith("0x")or len(R)<42:return{"verified":False,"reason":"MISSING_OO_ADDRESS"}
   f="0x"+R[-40:].lower();_OO_ADDR_CACHE[N]=f
  gq_raw=bytes.fromhex(S[2:]);U=[gq_raw[i:i+32]for i in range(0,13*32,32)];Q=int.from_bytes(U[1],"big");d=int.from_bytes(U[4],"big");t=int.from_bytes(U[5],"big");n=int.from_bytes(U[6],"big")!=0;D=int.from_bytes(U[7],"big")!=0;K=int.from_bytes(U[8],"big")!=0;C=int.from_bytes(U[9],"big")!=0
  if Q<=0:return{"verified":False,"reason":"UNINITIALIZED_QUESTION"}
  if n or D or K or C or t>0:return{"verified":False,"reason":f"QUESTION_FLAGS(res={n},pause={D},reset={K},refund={C})"}
  k=int.from_bytes(U[12],"big");J=32+k
  if J+32>len(gq_raw):return{"verified":False,"reason":"TRUNCATED_ANCILLARY_OFFSET"}
  I=int.from_bytes(gq_raw[J:J+32],"big");s=gq_raw[J+32:J+32+I]
  if len(s)!=I:return{"verified":False,"reason":"TRUNCATED_ANCILLARY_BYTES"}
  B=s.decode("utf-8",errors="replace");H=[{"jsonrpc":"2.0","id":10,"method":"eth_call","params":[{"to":f,"data":_encode_oo_query_calldata(SEL_GET_STATE,N,Q,s)},"latest"]},{"jsonrpc":"2.0","id":11,"method":"eth_call","params":[{"to":f,"data":_encode_oo_query_calldata(SEL_GET_REQUEST,N,Q,s)},"latest"]}];resp_2=_rpc_post(Y,H,timeout=timeout);G={int(r["id"]):r.get("result")for r in resp_2 if isinstance(r,dict)and"id"in r};P=str(G.get(10)or"");O=str(G.get(11)or"")
  if not P.startswith("0x")or not O.startswith("0x")or len(O)<2+16*64:return{"verified":False,"reason":"INVALID_OO_RESPONSE"}
  A=int(P,16);rq_raw=bytes.fromhex(O[2:]);z=[rq_raw[i:i+32]for i in range(0,16*32,32)];y="0x"+z[0].hex()[-40:].lower();x="0x"+z[1].hex()[-40:].lower();l=int.from_bytes(z[3],"big")!=0;a=int.from_bytes(z[10],"big");e=_decode_int256(z[11]);g=int.from_bytes(z[13],"big")
  if A not in(2,3):return{"verified":False,"reason":f"OO_STATE_{A}"}
  if y==ZERO_ADDR or x!=ZERO_ADDR or l:return{"verified":False,"reason":f"DISPUTER_OR_SETTLED(disp={x})"}
  if e==HALF_E18:return{"verified":False,"reason":"TIE_50_50_PROPOSAL_VETO"}
  F=map_uma_proposed_price_to_outcome_idx(e,B,X)
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
    if Z<w:return{"verified":False,"reason":f"MARKET_BEFORE_END_DATE(now={int(Z)}<end={int(w)})"}
    if j<(w-5.):return{"verified":False,"reason":f"PREMATURE_PROPOSAL_BEFORE_END_DATE(prop={int(j)}<end={int(w)})"}
  c=Z-j;b=max(.0,float(g)-Z)
  if c<min_proposal_age_sec:return{"verified":False,"reason":f"PROPOSAL_TOO_FRESH({c:.0f}s)"}
  if b>max_rem_challenge_sec:return{"verified":False,"reason":f"CHALLENGE_WINDOW_TOO_LONG({b:.0f}s)"}
  v,E=_extract_market_fee_rate(m);u=1-F;return{"verified":True,"domain":q,"adapter":N,"oo_address":f,"oo_state":A,"proposer":y,"proposed_price":e,"win_index":F,"win_label":"YES"if F==0 else"NO","win_outcome_name":X[F],"win_token":W[F],"lose_token":W[u],"expiration_ts":float(g),"eff_liveness_sec":int(h),"proposal_age_sec":round(c,1),"rem_challenge_sec":round(b,1),"fee_rate":v,"fee_exponent":E}
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
 for ev in(data or{}).get("events")or[]:
  n=((ev.get("competitions")or[None])[0])or{};st=n.get("status")or ev.get("status")or{};g=st.get("type")or{};k=str(g.get("state")or"").strip().lower();d=bool(g.get("completed",False));j=int(st.get("period")or 0);f=_parse_iso_clock_sec(st.get("clock")if st.get("clock")is not None else st.get("displayClock"));e=_parse_iso_ts(n.get("date")or ev.get("date"))or.0;b=None;a=None
  for c in n.get("competitors")or[]:
   ha=str(c.get("homeAway")or"").strip().lower()
   if ha=="home":b=c
   elif ha=="away":a=c
  if not b or not a:continue
  ht=b.get("team")or{};at=a.get("team")or{};i=str(ht.get("name")or ht.get("shortDisplayName")or"").strip();h=str(at.get("name")or at.get("shortDisplayName")or"").strip()
  try:m=int(float(b.get("score")or 0));l=int(float(a.get("score")or 0))
  except Exception:continue
  if i and h:o.append(LiveNbaGameState(game_id=str(ev.get("id")or""),start_ts=e,state=k,completed=d,period=j,clock_sec=f,home_name=i,home_abbr=str(ht.get("abbreviation")or"").upper(),home_score=m,away_name=h,away_abbr=str(at.get("abbreviation")or"").upper(),away_score=l,source="espn"))
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
  b={**i,"Referer":"https://www.nba.com/","Origin":"https://www.nba.com"};sb=json.loads(urllib.request.urlopen(urllib.request.Request(CDN_NBA_SCOREBOARD_URL,headers=b),timeout=timeout).read().decode("utf-8"));j=[]
  for g in((sb.get("scoreboard")or{}).get("games")or[]):gs=int(g.get("gameStatus")or 1);e="pre"if gs==1 else("in"if gs==2 else"post");ht,at=g.get("homeTeam")or{},g.get("awayTeam")or{};j.append(LiveNbaGameState(game_id=str(g.get("gameId")or""),start_ts=_parse_iso_ts(g.get("gameTimeUTC"))or.0,state=e,completed=(gs==3),period=int(g.get("period")or 0),clock_sec=_parse_iso_clock_sec(g.get("gameClock")),home_name=str(ht.get("teamName")or""),home_abbr=str(ht.get("teamTricode")or"").upper(),home_score=int(ht.get("score")or 0),away_name=str(at.get("teamName")or""),away_abbr=str(at.get("teamTricode")or"").upper(),away_score=int(at.get("score")or 0),source="cdn_nba"))
  return j
 except Exception:return[]
def match_nba_live_game(spec,live_games):
 ca,cb=_canon_nba_team(spec.team_a),_canon_nba_team(spec.team_b)
 for g in live_games:
  if g.start_ts>0 and spec.tipoff_ts>0 and abs(g.start_ts-spec.tipoff_ts)>3.6e4:continue
  ch,cw=_canon_nba_team(g.home_name),_canon_nba_team(g.away_name)
  if ca==ch and cb==cw:return g,g.home_score,g.away_score
  if ca==cw and cb==ch:return g,g.away_score,g.home_score
 return None
def verify_uma_against_nba_live(m,win_index,live_games):
 if not live_games:return True,"NO_LIVE_BOARD"
 e=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))];q=str(m.get("question")or"");f=((m.get("events")or[None])[0])or{};d=str(f.get("title")or"")if isinstance(f,dict)else"";c=_parse_iso_ts(m.get("gameStartTime")or m.get("endDate"))or.0
 for g in live_games:
  if g.start_ts>0 and c>0 and abs(g.start_ts-c)>3.6e4:continue
  ch,cw=_canon_nba_team(g.home_name),_canon_nba_team(g.away_name);ql=_norm_team(f"{q} {d}")
  if ch and cw and ch in ql and cw in ql:
   if not g.completed or g.state!="post":return False,"NBA_GAME_NOT_FINAL_YET"
   if str(m.get("sportsMarketType")or"").lower()=="moneyline"and len(e)==2 and g.home_score!=g.away_score:
    b=ch if g.home_score>g.away_score else cw;a=_canon_nba_team(e[win_index])
    if a in(ch,cw)and a!=b:return False,f"NBA_SCORE_CONTRADICTS_PROPOSAL({b}!={a})"
   return True,"NBA_FINAL_CONFIRMED"
 return True,"NON_NBA_OR_UNLISTED"
def evaluate_nba_endgame_locks(spec,game,score_a,score_b):
 i=float(score_a-score_b);c=float(score_a+score_b);n=[]
 if game.completed and game.state=="post"and game.period>=4 and score_a!=score_b:
  for lg in spec.margin_legs:
   m=(i>lg.threshold)if lg.relation=="GT"else(i<lg.threshold)
   if m:n.append({"leg":lg,"mode":"POST_BUZZER_FINAL","p_lock":.998,"cushion_pts":round(abs(i-lg.threshold),1),"clock_sec":.0,"period":game.period,"score_str":f"{spec.team_a} {score_a}-{score_b} {spec.team_b} (FINAL)"})
  for lg in spec.total_legs:
   k=(c>lg.threshold)if lg.relation=="OVER"else(c<lg.threshold)
   if k and abs(c-lg.threshold)>=1.5:n.append({"leg":lg,"mode":"POST_BUZZER_FINAL","p_lock":.998,"cushion_pts":round(abs(c-lg.threshold),1),"clock_sec":.0,"period":game.period,"score_str":f"{spec.team_a} {score_a}-{score_b} {spec.team_b} (FINAL Tot={int(c)})"})
  return n
 if game.state!="in":return n
 if game.period>=3:
  for lg in spec.total_legs:
   if lg.relation=="OVER"and c>=lg.threshold+2.5:n.append({"leg":lg,"mode":"LIVE_TOTAL_OVER_LOCKED","p_lock":.997,"cushion_pts":round(c-lg.threshold,1),"clock_sec":round(game.clock_sec,1),"period":game.period,"score_str":f"P{game.period} {game.clock_sec:.0f}s Tot={int(c)}>{lg.threshold:g}"})
 if game.period>=4 and.0<game.clock_sec<=120.:
  t=max(1.,float(game.clock_sec));e=5.5 if t<=12. else(7.5 if t<=28. else(9.5 if t<=50. else 13.5));b=max(1.6,.3965*math.sqrt(t))
  for lg in spec.margin_legs:
   l=(i-lg.threshold)if lg.relation=="GT"else(lg.threshold-i)
   if l<e:continue
   if abs(i)<=8.5:
    a=(lg.relation=="GT"and i>=6.)or(lg.relation=="LT"and i<=-6.)
    if not a:continue
   d=l-3.
   if d<=.0 or(d*d)<1.15*t:continue
   j=d/b;g=.5*(1.+math.erf(j/math.sqrt(2.)));f=.5+math.atan(j)/math.pi;h=round(min(.997,.98*g+.02*f),4)
   if h>=.993:n.append({"leg":lg,"mode":"LIVE_Q4_ENDGAME_LOCK","p_lock":h,"cushion_pts":round(l,1),"z_endgame":round(j,2),"clock_sec":round(t,1),"period":game.period,"score_str":f"P{game.period} {t:.0f}s {spec.team_a} {score_a}-{score_b} {spec.team_b}"})
 return n
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
 h=rpc_url or os.getenv("POLYGON_RPC_URL")or DEFAULT_POLYGON_RPC;g=c[2:];f=[{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":NEGRISK_ADAPTER_ADDR,"data":f"0x{SEL_NR_GET_QUESTION_COUNT}{g}"},"latest"]},{"jsonrpc":"2.0","id":2,"method":"eth_call","params":[{"to":NEGRISK_ADAPTER_ADDR,"data":f"0x{SEL_NR_GET_FEE_BIPS}{g}"},"latest"]},{"jsonrpc":"2.0","id":3,"method":"eth_call","params":[{"to":NEGRISK_ADAPTER_ADDR,"data":f"0x{SEL_NR_GET_DETERMINED}{g}"},"latest"]}]
 try:
  resp=_rpc_post(h,f,timeout=timeout);by_id={int(r["id"]):str(r.get("result")or"")for r in resp if isinstance(r,dict)and"id"in r}
  if not all(by_id.get(i,"").startswith("0x")and len(by_id[i])>=66 for i in(1,2,3)):return False,0,"BAD_ADAPTER_RPC"
  b=int(by_id[1],16);a=int(by_id[2],16);d=int(by_id[3],16)!=0
  if not d:_NR_ADAPTER_CACHE[c]=(b,a,d)
  if d:return False,a,"ALREADY_DETERMINED"
  if b!=expected_n:return False,a,f"QCOUNT_MISMATCH({b}!={expected_n})"
  return True,a,"OK"
 except Exception as exc:return False,0,f"RPC_ERR:{type(exc).__name__}"
def detect_nr2_convert_no_subset_arbs(spec,books_by_token,target_budget_usd=120.,min_edge_pure_cash=.012,min_edge_with_yes_sell=.015,min_shares=6,fee_bips=0):
 if not spec.is_closed_convert_safe:return[]
 n_tot=len(spec.brackets)
 if n_tot<3 or fee_bips<0 or fee_bips>=500:return[]
 conv_mult=1.-float(fee_bips)/1e4;br_info=[]
 for M,b in enumerate(spec.brackets):bk_y=books_by_token.get(b["yes_token"])or{};bk_n=books_by_token.get(b["no_token"])or{};F=sorted([(float(x["price"]),float(x["size"]))for x in(bk_n.get("asks")or[])if float(x.get("price",0))>0 and float(x.get("size",0))>0],key=lambda t:t[0]);E=sorted([(float(x["price"]),float(x["size"]))for x in(bk_y.get("bids")or[])if float(x.get("price",0))>0 and float(x.get("size",0))>0],key=lambda t:-t[0]);fr,fe=float(b["fee_rate"]),float(b["fee_exponent"]);z=_net_unit_ask(F[0][0],fr,fe)if F else 9.9;C=F[0][1]if F else.0;r=_net_unit_bid(E[0][0],fr,fe)if E else.0;y=E[0][1]if E else.0;br_info.append({"idx":M,"bracket":b,"asks_n":F,"bids_y":E,"a_no_net":z,"a_no_sh":C,"b_yes_net":r,"b_yes_sh":y})
 liquid_no=sorted([x for x in br_info if x["a_no_sh"]>=min_shares and x["a_no_net"]<.995],key=lambda x:x["a_no_net"])[:6];m=[]
 for L in(2,3):
  if len(liquid_no)>=L and L<=n_tot-1:
   for K in itertools.combinations([x["idx"]for x in liquid_no],L):m.append(tuple(sorted(K)))
 if all(x["a_no_sh"]>=min_shares and x["a_no_net"]<.998 for x in br_info):m.append(tuple(range(n_tot)))
 J=[];D=set()
 for s_tup in m:
  if s_tup in D:continue
  D.add(s_tup);H=len(s_tup);s_set=set(s_tup);comp_all=[i for i in range(n_tot)if i not in s_set];l=sum(br_info[i]["a_no_net"]for i in s_tup)
  if l<=.0:continue
  q=min(br_info[i]["a_no_sh"]for i in s_tup);B=int(math.floor(min(q,target_budget_usd/max(.25,l))))
  if B<min_shares:continue
  k=sorted([i for i in comp_all if br_info[i]["b_yes_net"]>=.004 and br_info[i]["b_yes_sh"]>=min_shares*conv_mult],key=lambda i:-br_info[i]["b_yes_net"]);a=None
  for G in range(0,len(k)+1):
   l_idxs=sorted(k[:G]);u_idxs=sorted([i for i in comp_all if i not in set(l_idxs)]);f=B
   if l_idxs:v=min(br_info[j]["b_yes_sh"]/max(conv_mult,1e-6)for j in l_idxs);f=int(math.floor(min(float(B),v)))
   if f<min_shares:continue
   no_walks=[];ok=True
   for i in s_tup:
    bi=br_info[i]["bracket"];wi=_walk_side_exact_shares((books_by_token.get(bi["no_token"])or{}).get("asks")or[],float(f),float(bi["fee_rate"]),float(bi["fee_exponent"]),is_ask=True)
    if wi is None:ok=False;break
    no_walks.append((bi,wi))
   if not ok:continue
   h=float(f)*conv_mult;yes_walks=[]
   for j in l_idxs:
    bj=br_info[j]["bracket"];wj=_walk_side_exact_shares((books_by_token.get(bj["yes_token"])or{}).get("bids")or[],h,float(bj["fee_rate"]),float(bj["fee_exponent"]),is_ask=False)
    if wj is None or wj["net_per_share"]<=.002:ok=False;break
    yes_walks.append((bj,wj))
   if not ok:continue
   p=sum(w["net_per_share"]for _,w in no_walks);e=float(H-1)*conv_mult;o=conv_mult*sum(w["net_per_share"]for _,w in yes_walks);g=e+o;A=round(g-p,5);s=min_edge_pure_cash if not l_idxs else min_edge_with_yes_sell
   if A<s:continue
   q_indices=[int(br_info[i]["bracket"]["question_index"])for i in s_tup];d=sum(1<<qi for qi in q_indices);n=min([w["l1_usd"]for _,w in no_walks]+([w["l1_usd"]for _,w in yes_walks]if yes_walks else[9999.]));c=[br_info[u]["bracket"]for u in u_idxs];I={"mode":"NR2_SUBSET_CONVERT_FREE_TAIL"if c else"NR2_PURE_CASH_CONVERT","event_id":spec.event_id,"slug":spec.slug,"title":spec.title,"neg_risk_market_id":spec.neg_risk_market_id,"m_no_legs":H,"n_total":n_tot,"question_indices":q_indices,"no_question_indices":q_indices,"index_set":d,"index_set_int":d,"shares":f,"converted_shares_out":round(h,4),"fee_bips":fee_bips,"no_cost_per_share":round(p,4),"usdc_converted_per_share":round(e,4),"yes_bid_proceeds_per_share":round(o,4),"net_proceeds_per_share":round(g,4),"net_edge_per_share":round(A,4),"total_cost_usd":round(sum(w["net_cash_usd"]for _,w in no_walks),2),"total_net_profit_usd":round(f*A,2),"total_fee_usd":round(sum(w["fee_usd"]for _,w in no_walks)+sum(w["fee_usd"]for _,w in yes_walks),4),"l1_usd":round(n,2),"no_legs":[{"token_id":b["no_token"],"bracket":b,"walk":w}for b,w in no_walks],"yes_sell_legs":[{"token_id":b["yes_token"],"bracket":b,"walk":w}for b,w in yes_walks],"retained_free_yes_brackets":c,"retained_tail_count":len(c),"close_ts":spec.end_ts,"label":(f"NR2({H}/{n_tot}NO->${e:.2f}+SELL[{len(yes_walks)}Y]+FREE_TAIL[{len(c)}Y])")}
   if a is None or I["net_edge_per_share"]>a["net_edge_per_share"]:a=I
  if a is not None:J.append(a)
 J.sort(key=lambda x:(-float(x["net_edge_per_share"]),-int(x["retained_tail_count"])));return J
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
  fr,fe=_extract_market_fee_rate(m);u=_parse_clob_tokens(m);t=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
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
  p=NbaPlayerPropRung(event_id=j,event_slug=v,game_title=n,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),player_name=b,player_key=q,stat_type=w,line=a,yes_token=u[0],no_token=u[1],fee_rate=fr,tipoff_ts=f,settle_est_ts=c,home_team=g,away_team=h,fee_exponent=fe);e.setdefault((q,w),[]).append(p)
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
 o={}
 for b in((summary_json or{}).get("boxscore")or{}).get("players")or[]:
  for stat_blk in b.get("statistics")or[]:
   keys=[str(k)for k in(stat_blk.get("keys")or[])]
   if not keys:continue
   g=next((i for i,k in enumerate(keys)if k=="minutes"),-1);f=next((i for i,k in enumerate(keys)if k=="points"),-1);e=next((i for i,k in enumerate(keys)if k=="rebounds"),-1);d=next((i for i,k in enumerate(keys)if k=="assists"),-1);c=next((i for i,k in enumerate(keys)if k.startswith("threePointFieldGoalsMade")),-1)
   for n in stat_blk.get("athletes")or[]:
    if n.get("didNotPlay"):continue
    l=str((n.get("athlete")or{}).get("displayName")or"");j=canon_player_name(l);a=n.get("stats")or[]
    if not j or not a:continue
    if g>=0 and g<len(a):
     h=str(a[g]).strip()
     if h in("","0","0:00","--"):continue
    m={}
    try:
     if 0<=f<len(a):m["points"]=int(str(a[f]).split("-")[0])
     if 0<=e<len(a):m["rebounds"]=int(str(a[e]).split("-")[0])
     if 0<=d<len(a):m["assists"]=int(str(a[d]).split("-")[0])
     if 0<=c<len(a):m["threes"]=int(str(a[c]).split("-")[0])
    except ValueError:continue
    if m:o[j]=m
 return o
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
 for ev in events or[]:
  if not isinstance(ev,dict)or ev.get("closed")or ev.get("archived"):continue
  z=str(ev.get("gameId")or"").strip()
  if z:A.setdefault(z,[]).append(ev)
 H={}
 for z,v in A.items():
  b=None;c=None
  for e in v:
   sl=str(e.get("slug")or"").lower();mkts=e.get("markets")or[]
   if sl.endswith("-more-markets")and not e.get("negRisk"):c=e
   elif(bool(e.get("negRisk"))and not bool(e.get("negRiskAugmented",True))and len(mkts)==3 and not any(sl.endswith(suf)for suf in("-halftime-result","-second-half-result","-first-to-score","-exact-score"))and all(str(m.get("sportsMarketType")or"").lower()in("moneyline","soccer_match_winner","")for m in mkts)):b=e
  if b is None:continue
  y=_parse_iso_ts(b.get("startTime")or b.get("endDate"))or.0
  if y<=.0 or(now_ts is not None and y<now_ts-4.*3600.):continue
  i=str(b.get("negRiskMarketID")or"").strip().lower();f=None;g=None;d=None;n=[];a=False
  for G,m in enumerate(b.get("markets")or[]):
   if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:a=True;break
   F=str(m.get("question")or"");S=str(m.get("description")or"");T=str(m.get("groupItemTitle")or"").strip()
   if _SOC_ADVANCE_VETO_RE.search(f"{F}\n{S}\n{T}"):a=True;break
   R=_parse_clob_tokens(m);Q=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
   if not R or Q!=["yes","no"]:a=True;break
   fr,P=_extract_market_fee_rate(m);O=str(m.get("questionID")or"").strip().lower();E=int(O[64:],16)if(len(O)==66 and O.startswith("0x"))else G;D={"market_id":str(m.get("id")or""),"condition_id":str(m.get("conditionId")or""),"question_index":E,"label":T or F[:36],"team_norm":_norm_team(T),"yes_token":R[0],"no_token":R[1],"fee_rate":fr,"fee_exponent":P,"neg_risk":True}
   if"draw"in T.lower()or"end in a draw"in F.lower():g=D
   else:n.append(D)
  if a or g is None or len(n)!=2:continue
  f,d=n[0],n[1];N=SoccerRegulationTree(game_id=z,event_id_3way=str(b.get("id")or""),slug_3way=str(b.get("slug")or""),title=str(b.get("title")or b.get("slug")or""),neg_risk_market_id=i,end_ts=y+2.5*3600.,home_team=f["team_norm"],away_team=d["team_norm"],home_leg=f,draw_leg=g,away_leg=d)
  if c is not None:
   for mm in c.get("markets")or[]:
    if mm.get("closed")or mm.get("archived")or mm.get("acceptingOrders")is False:continue
    u=str(mm.get("description")or"");M=str(mm.get("question")or"");w=str(mm.get("groupItemTitle")or"").strip()
    if _SOC_ADVANCE_VETO_RE.search(f"{M}\n{u}\n{w}"):continue
    t=_parse_clob_tokens(mm);s=[str(o).strip()for o in _parse_json_list(mm.get("outcomes"))]
    if not t or len(s)!=2:continue
    L,K=_extract_market_fee_rate(mm);C=str(mm.get("sportsMarketType")or"").strip().lower()
    try:l=float(mm.get("line"))if mm.get("line")is not None else float("nan")
    except(TypeError,ValueError):l=float("nan")
    if C=="totals"and _is_half_hook(l):
     o0=s[0].lower();k,h=(t[0],t[1])if"over"in o0 else(t[1],t[0]);B={"market_id":str(mm.get("id")or""),"condition_id":str(mm.get("conditionId")or""),"line":abs(l),"over_token":k,"under_token":h,"fee_rate":L,"fee_exponent":K,"neg_risk":False};N.totals.append(B)
     if abs(abs(l)-.5)<1e-6:N.over05_leg=B
    elif C=="spreads"and _is_half_hook(l)and l<0:
     J=_SPREAD_PARSE_RE.match(w)
     if J:j=_norm_team(J.group(1));I=_norm_team(s[0]);r,q=(t[0],t[1])if j==I else(t[1],t[0]);p=s[1]if j==I else s[0];N.spreads.append({"market_id":str(mm.get("id")or""),"condition_id":str(mm.get("conditionId")or""),"fav_team":j,"fav_label":J.group(1).strip(),"dog_label":p,"abs_line":abs(l),"fav_minus_token":r,"dog_plus_token":q,"fee_rate":L,"fee_exponent":K,"neg_risk":False})
   N.totals.sort(key=lambda x:float(x["line"]));N.spreads.sort(key=lambda x:(x["fav_team"],float(x["abs_line"])))
  H[z]=N
 return H
def detect_soc1_regulation_boxes(tree,books_by_token,best_asks,max_2leg_cost_net=.988,min_conv_edge_ps=.01,target_budget_usd=120.):
 d=[];e=[]
 if tree.over05_leg is not None:
  dl,D=tree.draw_leg,tree.over05_leg;z=best_asks.get(dl["yes_token"]);y=best_asks.get(D["over_token"])
  if z is not None and y is not None:
   c=round(_net_unit_ask(z,dl["fee_rate"],dl["fee_exponent"])+_net_unit_ask(y,D["fee_rate"],D["fee_exponent"]),4)
   if c<=max_2leg_cost_net:d.append({"mode":"SOC1_SCORING_DRAW_CORRIDOR","game_id":tree.game_id,"title":tree.title,"box_cost_net":c,"close_ts":tree.end_ts,"leg_a":{"token_id":dl["yes_token"],"opp_token_id":dl["no_token"],"condition_id":dl["condition_id"],"market_id":dl["market_id"],"side":"YES","label":"YES[Draw]","fee_rate":dl["fee_rate"],"fee_exponent":dl["fee_exponent"],"neg_risk":True,"strike":.5},"leg_b":{"token_id":D["over_token"],"opp_token_id":D["under_token"],"condition_id":D["condition_id"],"market_id":D["market_id"],"side":"OVER","label":"OVER[0.5 Goals]","fee_rate":D["fee_rate"],"fee_exponent":D["fee_exponent"],"neg_risk":False,"strike":.5},"label":f"{tree.title}: YES[Draw] + OVER[0.5 Goals]"})
 for i in range(len(tree.totals)):
  w=tree.totals[i];r=best_asks.get(w["over_token"])
  if r is None:continue
  for j in range(i+1,len(tree.totals)):
   v=tree.totals[j]
   if v["line"]<=w["line"]+.1:continue
   p=best_asks.get(v["under_token"])
   if p is None:continue
   c=round(_net_unit_ask(r,w["fee_rate"],w["fee_exponent"])+_net_unit_ask(p,v["fee_rate"],v["fee_exponent"]),4)
   if c<=max_2leg_cost_net:d.append({"mode":"SOC1_GOAL_CORRIDOR_BOX","game_id":tree.game_id,"title":tree.title,"box_cost_net":c,"close_ts":tree.end_ts,"leg_a":{"token_id":w["over_token"],"opp_token_id":w["under_token"],"condition_id":w["condition_id"],"market_id":w["market_id"],"side":"OVER","label":f"O{w['line']}","fee_rate":w["fee_rate"],"fee_exponent":w["fee_exponent"],"neg_risk":False,"strike":w["line"]},"leg_b":{"token_id":v["under_token"],"opp_token_id":v["over_token"],"condition_id":v["condition_id"],"market_id":v["market_id"],"side":"UNDER","label":f"U{v['line']}","fee_rate":v["fee_rate"],"fee_exponent":v["fee_exponent"],"neg_risk":False,"strike":v["line"]},"label":f"{tree.title}: Goals O{w['line']} + U{v['line']}"})
 for i in range(len(tree.spreads)):
  s1=tree.spreads[i];t=best_asks.get(s1["fav_minus_token"])
  if t is None:continue
  for j in range(i+1,len(tree.spreads)):
   s2=tree.spreads[j]
   if s2["fav_team"]!=s1["fav_team"]or s2["abs_line"]<=s1["abs_line"]+.1:continue
   s=best_asks.get(s2["dog_plus_token"])
   if s is None:continue
   c=round(_net_unit_ask(t,s1["fee_rate"],s1["fee_exponent"])+_net_unit_ask(s,s2["fee_rate"],s2["fee_exponent"]),4)
   if c<=max_2leg_cost_net:d.append({"mode":"SOC1_HANDICAP_CORRIDOR_BOX","game_id":tree.game_id,"title":tree.title,"box_cost_net":c,"close_ts":tree.end_ts,"leg_a":{"token_id":s1["fav_minus_token"],"opp_token_id":s1["dog_plus_token"],"condition_id":s1["condition_id"],"market_id":s1["market_id"],"side":"SPREAD","label":f"{s1['fav_label']}(-{s1['abs_line']})","fee_rate":s1["fee_rate"],"fee_exponent":s1["fee_exponent"],"neg_risk":False,"strike":-s1["abs_line"]},"leg_b":{"token_id":s2["dog_plus_token"],"opp_token_id":s2["fav_minus_token"],"condition_id":s2["condition_id"],"market_id":s2["market_id"],"side":"SPREAD","label":f"{s2['dog_label']}(+{s2['abs_line']})","fee_rate":s2["fee_rate"],"fee_exponent":s2["fee_exponent"],"neg_risk":False,"strike":s2["abs_line"]},"label":f"{tree.title}: {s1['fav_label']}(-{s1['abs_line']}) + {s2['dog_label']}(+{s2['abs_line']})"})
 legs3=[tree.home_leg,tree.draw_leg,tree.away_leg]
 if len(tree.neg_risk_market_id)==66 and{int(x["question_index"])for x in legs3}=={0,1,2}:
  for idx_k in range(3):
   C=legs3[idx_k];B,A=[legs3[u]for u in range(3)if u!=idx_k];o=books_by_token.get(B["no_token"])or{};n=books_by_token.get(A["no_token"])or{};m=books_by_token.get(C["yes_token"])or{};asks_i=o.get("asks")or[];asks_j=n.get("asks")or[];bids_k=m.get("bids")or[]
   if not(asks_i and asks_j and bids_k):continue
   l=min(max((float(a.get("size",0))for a in asks_i[:1]),default=.0),max((float(a.get("size",0))for a in asks_j[:1]),default=.0),max((float(b.get("size",0))for b in bids_k[:1]),default=.0));k=int(math.floor(min(l,target_budget_usd/.8)))
   if k<6:continue
   wi=_walk_side_exact_shares(asks_i,float(k),B["fee_rate"],B["fee_exponent"],is_ask=True);wj=_walk_side_exact_shares(asks_j,float(k),A["fee_rate"],A["fee_exponent"],is_ask=True);wk=_walk_side_exact_shares(bids_k,float(k),C["fee_rate"],C["fee_exponent"],is_ask=False)
   if wi is None or wj is None or wk is None:continue
   f=wi["net_per_share"]+wj["net_per_share"];h=1.+wk["net_per_share"];g=round(h-f,5)
   if g>=min_conv_edge_ps:q_idxs=sorted([int(B["question_index"]),int(A["question_index"])]);e.append({"mode":"SOC1_3WAY_CONVERT_SYNTHETIC","event_id":tree.event_id_3way,"game_id":tree.game_id,"title":tree.title,"neg_risk_market_id":tree.neg_risk_market_id,"m_no_legs":2,"n_total":3,"no_question_indices":q_idxs,"index_set_int":sum(1<<q for q in q_idxs),"shares":k,"no_cost_per_share":round(f,4),"yes_bid_proceeds_per_share":round(wk["net_per_share"],4),"net_edge_per_share":round(g,4),"total_net_profit_usd":round(k*g,2),"l1_usd":round(min(wi["l1_usd"],wj["l1_usd"],wk["l1_usd"]),2),"no_legs":[{"token_id":B["no_token"],"bracket":B,"walk":wi},{"token_id":A["no_token"],"bracket":A,"walk":wj}],"yes_sell_legs":[{"token_id":C["yes_token"],"bracket":C,"walk":wk}],"close_ts":tree.end_ts,"label":f"SOC1_CONV(NO[{B['label'][:12]}]+NO[{A['label'][:12]}]->$1+SELL[{C['label'][:12]}])"})
 d.sort(key=lambda x:float(x["box_cost_net"]));e.sort(key=lambda x:-float(x["net_edge_per_share"]));return{"two_leg_boxes":d,"convert_arbs":e}
def find_state_matrix_dominance_boxes(legs,best_asks,max_2leg_cost_net=.994,max_3leg_cost_net=.992):
 a=[]
 for lg in legs:
  g=str(lg["token_id"])
  if g not in best_asks:continue
  px=float(best_asks[g])
  if not(.001<=px<=.992):continue
  e=_net_unit_ask(px,float(lg.get("fee_rate",.0)),float(lg.get("fee_exponent",1.)));a.append((lg,px,e))
 if len(a)<2:return[]
 n_states=len(a[0][0]["payoff_vec"]);f=[]
 for i in range(len(a)):
  la,_,ca=a[i];va=la["payoff_vec"]
  for j in range(i+1,len(a)):
   lb,_,cb=a[j]
   if la["market_id"]==lb["market_id"]:continue
   d=round(ca+cb,4)
   if d>max_2leg_cost_net:continue
   vb=lb["payoff_vec"];sums=[va[s]+vb[s]for s in range(n_states)]
   if min(sums)>=1.-1e-9:f.append({"n_legs":2,"box_cost_net":d,"min_payout":round(min(sums),4),"max_payout":round(max(sums),4),"jackpot_states":sum(1 for v in sums if v>=1.5-1e-9),"legs":[la,lb],"close_ts":max(float(la["end_ts"]),float(lb["end_ts"])),"label":f"{la['label']} + {lb['label']}"})
 c=sorted(a,key=lambda x:x[2])[:18]
 for i in range(len(c)):
  la,_,ca=c[i];va=la["payoff_vec"]
  for j in range(i+1,len(c)):
   lb,_,cb=c[j]
   if ca+cb>max_3leg_cost_net:continue
   vb=lb["payoff_vec"]
   if min(va[s]+vb[s]for s in range(n_states))>=1.-1e-9:continue
   for k in range(j+1,len(c)):
    lc,_,cc=c[k];b=round(ca+cb+cc,4)
    if b>max_3leg_cost_net:continue
    if len({la["market_id"],lb["market_id"],lc["market_id"]})<2:continue
    vc=lc["payoff_vec"]
    if min(va[s]+vc[s]for s in range(n_states))>=1.-1e-9:continue
    if min(vb[s]+vc[s]for s in range(n_states))>=1.-1e-9:continue
    sums3=[va[s]+vb[s]+vc[s]for s in range(n_states)]
    if min(sums3)>=1.-1e-9:f.append({"n_legs":3,"box_cost_net":b,"min_payout":round(min(sums3),4),"max_payout":round(max(sums3),4),"jackpot_states":sum(1 for v in sums3 if v>=1.5-1e-9),"legs":[la,lb,lc],"close_ts":max(float(la["end_ts"]),float(lb["end_ts"]),float(lc["end_ts"])),"label":f"{la['label']} + {lb['label']} + {lc['label']}"})
 f.sort(key=lambda x:(float(x["box_cost_net"]),-int(x["jackpot_states"])));return f
BOP_9_STATES=(("D","D"),("D","R"),("D","O"),("R","D"),("R","R"),("R","O"),("O","D"),("O","R"),("O","O"))
def build_lp1_bop_2026_truth_legs(events_by_slug):
 legs=[]
 def _add_mkt(m,event_slug,tag_lbl,yes_fn):
  if m.get("closed")or m.get("archived")or m.get("active")is False:return
  c=_parse_clob_tokens(m)
  if not c:return
  fr,fe=_extract_market_fee_rate(m);a=_parse_iso_ts(m.get("endDate"))or.0;e=str(m.get("id")or"");d=str(m.get("conditionId")or"");nr=bool(m.get("negRisk"));v_yes=[1. if yes_fn(s_sen,s_hse)else.0 for s_sen,s_hse in BOP_9_STATES];b=[1.-x for x in v_yes];legs.append({"event_slug":event_slug,"market_id":e,"condition_id":d,"token_id":c[0],"opp_token_id":c[1],"side":"YES","label":f"YES[{tag_lbl}]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":a,"payoff_vec":v_yes,"strike":1.});legs.append({"event_slug":event_slug,"market_id":e,"condition_id":d,"token_id":c[1],"opp_token_id":c[0],"side":"NO","label":f"NO[{tag_lbl}]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":a,"payoff_vec":b,"strike":1.})
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
 return legs
_EM_BANDS=((1,5),(6,10),(11,15),(16,20),(21,999))
def build_lp1_nba_exact_margin_bundle(parent_ev,em_ev):
 if parent_ev.get("closed")or em_ev.get("closed")or not em_ev.get("negRisk")or em_ev.get("negRiskAugmented",True):return None
 n=em_ev.get("markets")or[]
 if len(n)!=11:return None
 z=(_parse_iso_ts(parent_ev.get("startTime")or parent_ev.get("endDate"))or.0)+3.25*3600.;f=str(em_ev.get("negRiskMarketID")or"").strip().lower();ml_mkt=next((m for m in(parent_ev.get("markets")or[])if str(m.get("sportsMarketType")or"").lower()=="moneyline"and not m.get("closed")),None)
 if ml_mkt is None:return None
 l=_parse_clob_tokens(ml_mkt);j=[str(o).strip()for o in _parse_json_list(ml_mkt.get("outcomes"))];L,K=_extract_market_fee_rate(ml_mkt)
 if not l or len(j)!=2:return None
 y,w=_canon_nba_team(j[0]),_canon_nba_team(j[1]);v=str(ml_mkt.get("id")or"");u=str(ml_mkt.get("conditionId")or"");Y=[];J=[1.]*5+[.0]*5+[.5];I=[.0]*5+[1.]*5+[.5];Y.append({"market_id":v,"condition_id":u,"token_id":l[0],"opp_token_id":l[1],"side":"ML_A","label":f"ML[{j[0]}]","fee_rate":L,"fee_exponent":K,"neg_risk":False,"end_ts":z,"payoff_vec":J,"strike":.0});Y.append({"market_id":v,"condition_id":u,"token_id":l[1],"opp_token_id":l[0],"side":"ML_B","label":f"ML[{j[1]}]","fee_rate":L,"fee_exponent":K,"neg_risk":False,"end_ts":z,"payoff_vec":I,"strike":.0});d={5.5:1,10.5:2,15.5:3,20.5:4}
 for sm in parent_ev.get("markets")or[]:
  if sm.get("closed")or str(sm.get("sportsMarketType")or"").lower()!="spreads":continue
  X,W=_extract_market_fee_rate(sm)
  try:V=abs(float(sm.get("line")))
  except(TypeError,ValueError):continue
  if V not in d:continue
  U=_parse_clob_tokens(sm);t=[str(o).strip()for o in _parse_json_list(sm.get("outcomes"))];H=str(sm.get("groupItemTitle")or sm.get("question")or"");T=re.search(r"([A-Za-z0-9\s\.]+?)\s*\(-"+re.escape(str(V))+r"\)",H)
  if not U or len(t)!=2 or not T:continue
  G=_canon_nba_team(T.group(1));cut_idx=d[V];S=_canon_nba_team(t[0]);h,g=(U[0],U[1])if G==S else(U[1],U[0])
  if G==y:v_fav=[1. if idx>=cut_idx else.0 for idx in range(5)]+[.0]*5+[.5]
  elif G==w:v_fav=[.0]*5+[1. if idx>=cut_idx else.0 for idx in range(5)]+[.5]
  else:continue
  F=[1.-x if i<10 else.5 for i,x in enumerate(v_fav)];E,r=str(sm.get("id")or""),str(sm.get("conditionId")or"");Y.append({"market_id":E,"condition_id":r,"token_id":h,"opp_token_id":g,"side":"SPREAD","label":f"{G.title()}(-{V})","fee_rate":X,"fee_exponent":W,"neg_risk":False,"end_ts":z,"payoff_vec":v_fav,"strike":-V});Y.append({"market_id":E,"condition_id":r,"token_id":g,"opp_token_id":h,"side":"SPREAD","label":f"Opp(+{V})","fee_rate":X,"fee_exponent":W,"neg_risk":False,"end_ts":z,"payoff_vec":F,"strike":V})
 b=[];a=[];c=set()
 for D,m in enumerate(n):
  if m.get("closed")or m.get("archived"):return None
  R,Q=_extract_market_fee_rate(m);P=_parse_clob_tokens(m)
  if not P:return None
  _a=str(m.get("groupItemTitle")or m.get("question")or"").strip();O=str(m.get("questionID")or"").strip().lower();C=int(O[64:],16)if(len(O)==66 and O.startswith("0x"))else D;st_idx=None
  if"other"in _a.lower():st_idx=10
  else:
   Z=_NBA_EM_BAND_RE.search(_a)
   if Z:
    N=_canon_nba_team(Z.group(1));lo=int(Z.group(2));q=next((k for k,(blo,_)in enumerate(_EM_BANDS)if blo==lo),None)
    if q is not None:
     if N==y or N in y or y in N:st_idx=q
     elif N==w or N in w or w in N:st_idx=5+q
  if st_idx is None:return None
  c.add(st_idx);v_yes=[1. if s==st_idx else.0 for s in range(11)];M=[1.-x for x in v_yes];B,A=str(m.get("id")or""),str(m.get("conditionId")or"");e=_a.replace("Exact Margin:","").strip();Y.append({"market_id":B,"condition_id":A,"token_id":P[0],"opp_token_id":P[1],"side":"YES","label":f"EM_Y[{e}]","fee_rate":R,"fee_exponent":Q,"neg_risk":True,"end_ts":z,"payoff_vec":v_yes,"strike":float(st_idx)});p={"market_id":B,"condition_id":A,"token_id":P[1],"opp_token_id":P[0],"side":"NO","label":f"EM_N[{e}]","fee_rate":R,"fee_exponent":Q,"neg_risk":True,"end_ts":z,"payoff_vec":M,"strike":float(st_idx),"question_index":C};Y.append(p)
  if 0<=st_idx<=4:b.append(p)
  elif 5<=st_idx<=9:a.append(p)
 if c!=set(range(11)):return None
 return{"event_id":str(parent_ev.get("id")or""),"em_event_id":str(em_ev.get("id")or""),"slug":str(parent_ev.get("slug")or""),"title":str(parent_ev.get("title")or""),"neg_risk_market_id":f,"end_ts":z,"legs":Y,"ml_a_token":l[0],"ml_b_token":l[1],"ml_a_label":j[0],"ml_b_label":j[1],"team_a_em_no":b,"team_b_em_no":a}
@dataclass
class EsportsBo3Spec:event_id:str;slug:str;title:str;end_ts:float;team_a:str;team_b:str;ml_market_id:str;ml_condition_id:str;ml_a_token:str;ml_b_token:str;ml_fee_rate:float;ml_fee_exp:float;hc_market_id:str;hc_condition_id:str;hc_fav_is_a:bool;hc_minus_token:str;hc_plus_token:str;hc_fee_rate:float;hc_fee_exp:float;map1_a_token=None;map1_b_token=None;map1_resolved_winner=None;map2_a_token=None;map2_b_token=None;map2_resolved_winner=None;ou25_over_token=None;ou25_under_token=None;ou25_market_id="";ou25_condition_id="";ou25_fee_rate=.03
def parse_esports_bo3_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived"):return None
 H=str(ev.get("title")or"");mkts=ev.get("markets")or[];e=bool(re.search(r"\(\s*bo3\s*\)|\bbest\s+of\s+3\b",H,re.IGNORECASE));b=any(re.search(r"\bmap\s+[45]\b",str(m.get("groupItemTitle")or m.get("question")or""),re.IGNORECASE)for m in mkts)
 if b:return None
 i=any(str(m.get("sportsMarketType")or"").lower()=="totals"and abs(float(m.get("line")or 0)-2.5)<1e-6 for m in mkts if m.get("line")is not None)
 if not(e or i):return None
 w=(_parse_iso_ts(ev.get("startTime")or ev.get("endDate"))or.0)+3.5*3600.
 if now_ts is not None and w<now_ts+60.:return None
 ml_m=next((m for m in mkts if str(m.get("sportsMarketType")or"").lower()=="moneyline"and not m.get("closed")),None);hc_m=next((m for m in mkts if str(m.get("sportsMarketType")or"").lower()=="map_handicap"and not m.get("closed")and abs(abs(float(m.get("line")or 0))-1.5)<1e-6),None)
 if ml_m is None or hc_m is None:return None
 r=_parse_clob_tokens(ml_m);q=[str(o).strip()for o in _parse_json_list(ml_m.get("outcomes"))];p=_parse_clob_tokens(hc_m);n=[str(o).strip()for o in _parse_json_list(hc_m.get("outcomes"))]
 if not r or len(q)!=2 or not p or len(n)!=2:return None
 v,u=q[0],q[1];ta_n,tb_n=_norm_team(v),_norm_team(u);l,k=_norm_team(n[0]),_norm_team(n[1])
 if{ta_n,tb_n}!={l,k}:return None
 j=str(hc_m.get("description")or"");t=str(hc_m.get("groupItemTitle")or hc_m.get("question")or"");a=None;d=re.search(r'resolve\s+to\s+"([^"]+)"\s+if\s+.+?\s+wins\s+2\s+or\s+more\s+maps',j,re.IGNORECASE)
 if d:
  G=_norm_team(d.group(1))
  if G==ta_n:a=True
  elif G==tb_n:a=False
 if a is None:
  s=_MAP_HC_PAIR_RE.search(t)
  if s:s1=float(s.group(2));h=l if s1<0 else k;a=(h==ta_n)
 if a is None:return None
 g=ta_n if a else tb_n;c,f=(p[0],p[1])if l==g else(p[1],p[0]);F,E=_extract_market_fee_rate(ml_m);D,C=_extract_market_fee_rate(hc_m);I=EsportsBo3Spec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),title=H,end_ts=w,team_a=v,team_b=u,ml_market_id=str(ml_m.get("id")or""),ml_condition_id=str(ml_m.get("conditionId")or""),ml_a_token=r[0],ml_b_token=r[1],ml_fee_rate=F,ml_fee_exp=E,hc_market_id=str(hc_m.get("id")or""),hc_condition_id=str(hc_m.get("conditionId")or""),hc_fav_is_a=a,hc_minus_token=c,hc_plus_token=f,hc_fee_rate=D,hc_fee_exp=C)
 def _extract_map_winner(cm):
  f=_parse_clob_tokens(cm);e=[_norm_team(str(x))for x in _parse_json_list(cm.get("outcomes"))];d=_parse_json_list(cm.get("outcomePrices"));c,b=None,None
  if f and len(e)==2 and{e[0],e[1]}=={ta_n,tb_n}:c,b=(f[0],f[1])if e[0]==ta_n else(f[1],f[0])
  a=None
  if len(d)==2 and len(e)==2:
   try:
    p0,p1=float(d[0]),float(d[1])
    if cm.get("closed")or(max(p0,p1)>=.995 and min(p0,p1)<=.005):
     if p0>=.995 and p1<=.005:a="A"if e[0]==ta_n else"B"
     elif p1>=.995 and p0<=.005:a="A"if e[1]==ta_n else"B"
   except(TypeError,ValueError):pass
  return c,b,a
 for cm in mkts:
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
 bk_a=books_by_token.get(tok_a)or{};bk_b=books_by_token.get(tok_b)or{};f=max((float(b.get("price",0))for b in(bk_a.get("bids")or[])if float(b.get("size",0))>0),default=.0);e=max((float(b.get("price",0))for b in(bk_b.get("bids")or[])if float(b.get("size",0))>0),default=.0);d=min((float(a.get("price",1))for a in(bk_a.get("asks")or[])if float(a.get("size",0))>0),default=1.);c=min((float(a.get("price",1))for a in(bk_b.get("asks")or[])if float(a.get("size",0))>0),default=1.)
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
 fr,fe=_extract_market_fee_rate(m);a=_parse_iso_ts(m.get("endDate"))or.0;d=str(m.get("id")or"");c=str(m.get("conditionId")or"");nr=bool(m.get("negRisk"))
 if v_no is None:v_no=[1.-x for x in v_yes]
 legs.append({"event_slug":event_slug,"market_id":d,"condition_id":c,"token_id":b[0],"opp_token_id":b[1],"side":"YES","label":f"YES[{tag_lbl}]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":a,"payoff_vec":v_yes,"strike":1.});legs.append({"event_slug":event_slug,"market_id":d,"condition_id":c,"token_id":b[1],"opp_token_id":b[0],"side":"NO","label":f"NO[{tag_lbl}]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":a,"payoff_vec":v_no,"strike":1.})
_HOUSE_SEAT_KEYS=("below 190","190-194","195-199","200-204","205-209","210-214","215-219","220-224","225-229","230+");_HOUSE_18_STATES=(tuple((b,ctrl)for b in range(6)for ctrl in("D","O"))+((6,"D"),(6,"R"),(6,"O"))+((7,"R"),(8,"R"),(9,"R")))
def build_lp2_house_seats_truth_legs(events_by_slug):
 b=events_by_slug.get("republican-house-seats-after-the-2026-midterm-elections")or{}
 if not b or b.get("closed"):return[]
 e=[];a=set()
 for m in b.get("markets")or[]:
  grp=str(m.get("groupItemTitle")or m.get("question")or"").strip().lower();b_idx=next((i for i,k in enumerate(_HOUSE_SEAT_KEYS)if grp==k or k in grp),None)
  if b_idx is None:continue
  a.add(b_idx);_add_truth_leg(e,m,"r_house_seats",f"HSeats:{_HOUSE_SEAT_KEYS[b_idx]}",[1. if sb==b_idx else.0 for sb,_ in _HOUSE_18_STATES])
 if len(a)<8:return[]
 d=events_by_slug.get("which-party-will-win-the-house-in-2026")or{}
 for m in d.get("markets")or[]:
  grp=str(m.get("groupItemTitle")or"").strip().lower()
  if grp=="democratic party":_add_truth_leg(e,m,"house_ctrl","House:Dem",[1. if c=="D"else.0 for _,c in _HOUSE_18_STATES])
  elif grp=="republican party":_add_truth_leg(e,m,"house_ctrl","House:Rep",[1. if c=="R"else.0 for _,c in _HOUSE_18_STATES])
 return e
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
 g=[];a=set()
 for m in b.get("markets")or[]:
  e=str(m.get("groupItemTitle")or m.get("question")or"");b_idx=_match_senate_seat_idx(e)
  if b_idx is None:continue
  a.add(b_idx);_add_truth_leg(g,m,"r_sen_seats",f"SSeats:{_SENATE_SEAT_KEYS[b_idx]}",[1. if sb==b_idx else.0 for sb,_,_ in _SENATE_17_STATES])
 if len(a)<9:return[]
 f=events_by_slug.get("which-party-will-win-the-senate-in-2026")or{}
 for m in f.get("markets")or[]:
  e=str(m.get("groupItemTitle")or"").strip().lower()
  if e=="democratic party":_add_truth_leg(g,m,"sen_ctrl","Sen:Dem",[1. if c=="D"else.0 for _,c,_ in _SENATE_17_STATES])
  elif e=="republican party":_add_truth_leg(g,m,"sen_ctrl","Sen:Rep",[1. if c=="R"else.0 for _,c,_ in _SENATE_17_STATES])
 d=events_by_slug.get("republican-trifecta-with-supermajority-in-the-senate")or{}
 for m in d.get("markets")or[]:_add_truth_leg(g,m,"trifecta_60","R_Trifecta60",[float(tri)for _,_,tri in _SENATE_17_STATES])
 return g
def build_lp2_pending_senate_conditional_groups(conditional_events,senate_ev):
 if not senate_ev or senate_ev.get("closed"):return[]
 e=[];states_7=((1,"R",0),(1,"D",0),(1,"O",0),(1,"O",1),(0,"R",1),(0,"D",1),(0,"O",1))
 for ev in conditional_events:
  i=str(ev.get("slug")or"").lower()
  if not i.startswith("who-wins-the-senate-pending-")or"pending-oil"in i:continue
  if ev.get("closed")or not ev.get("negRisk")or ev.get("negRiskAugmented",True):continue
  h=[m for m in(ev.get("markets")or[])if not m.get("closed")]
  if len(h)!=3:continue
  b,a,d=None,None,None
  for m in h:
   g=str(m.get("groupItemTitle")or m.get("question")or"").lower()
   if g.startswith("no "):d=m
   elif"r senate"in g or"republican"in g:b=m
   elif"d senate"in g or"democrat"in g:a=m
  if not(b and a and d):continue
  f=[];j=i.replace("who-wins-the-senate-pending-","")[:22];_add_truth_leg(f,b,i,f"{j}:Y&RSen",[1. if(c==1 and s=="R")else.0 for c,s,_ in states_7]);_add_truth_leg(f,a,i,f"{j}:Y&DSen",[1. if(c==1 and s=="D")else.0 for c,s,_ in states_7]);_add_truth_leg(f,d,i,f"{j}:NoCond",[float(nc)for _,_,nc in states_7])
  for sm in senate_ev.get("markets")or[]:
   sg=str(sm.get("groupItemTitle")or"").strip().lower()
   if sg=="democratic party":_add_truth_leg(f,sm,"sen_ctrl","Sen:Dem",[1. if s=="D"else.0 for _,s,_ in states_7])
   elif sg=="republican party":_add_truth_leg(f,sm,"sen_ctrl","Sen:Rep",[1. if s=="R"else.0 for _,s,_ in states_7])
  if len(f)>=8:e.append((f"COND_{j.upper()}",f))
 return e
def build_lp2_tossup_state_implication_groups(events_by_slug):
 ev_cube=events_by_slug.get(LP2_TOSSUP_CUBE_SLUG)or{}
 if not ev_cube or ev_cube.get("closed"):return[]
 cube_mkts=[m for m in(ev_cube.get("markets")or[])if not m.get("closed")]
 if not cube_mkts:return[]
 k=next((m for m in cube_mkts if str(m.get("groupItemTitle")or"").strip().lower()=="all 7"),None);j=next((m for m in cube_mkts if str(m.get("groupItemTitle")or"").strip().lower()in("none","0","no states")),None);all_codes=set(LP2_TOSSUP_STATE_SLUGS.keys());a={}
 for m in cube_mkts:
  grp_u=str(m.get("groupItemTitle")or"").upper();h={c for c in all_codes if re.search(rf"\b{c}\b",grp_u)}
  if len(h)==6:g=next(iter(all_codes-h));a[g]=m
 states_8=[(so,o6)for so in("NAMED_R","OTHER_R","NAMED_D","OTHER_NON_R")for o6 in(True,False)];i=[]
 for f,e in LP2_TOSSUP_STATE_SLUGS.items():
  l=events_by_slug.get(e)or{}
  if not l or l.get("closed"):continue
  n=[];d=[];b=[]
  for m in l.get("markets")or[]:
   if m.get("closed"):continue
   o=str(m.get("groupItemTitle")or"").strip()
   if re.search(r"^(?:person|option|candidate|party)\s+[a-z0-9]{1,2}$",o,re.I)or"other"in o.lower():continue
   if"(r)"in o.lower()or(f=="AK"and"sullivan"in o.lower()):d.append((o,m))
   elif"(d)"in o.lower()or(f=="AK"and"peltola"in o.lower()):b.append((o,m))
  if len(d)==1:_add_truth_leg(n,d[0][1],e,f"{f}:{d[0][0][:18]}",[1. if so=="NAMED_R"else.0 for so,_ in states_8])
  if len(b)==1:_add_truth_leg(n,b[0][1],e,f"{f}:{b[0][0][:18]}",[1. if so=="NAMED_D"else.0 for so,_ in states_8])
  if k is not None:_add_truth_leg(n,k,LP2_TOSSUP_CUBE_SLUG,"Tossups:All7",[1. if(so in("NAMED_R","OTHER_R")and o6)else.0 for so,o6 in states_8])
  if f in a:_add_truth_leg(n,a[f],LP2_TOSSUP_CUBE_SLUG,f"Tossups:6Excl{f}",[1. if(so in("NAMED_D","OTHER_NON_R")and o6)else.0 for so,o6 in states_8])
  if j is not None:pass
  if len(n)>=6:i.append((f"TOSSUP_{f}",n))
 return i
def detect_lp2_seat_convert_implication_arbs(events_by_slug,books_by_token,target_budget_usd=120.,max_synthetic_box_cost_net=.992,min_shares=6,rpc_url=None):
 M=[];u=[("LP2_HOUSE_CONVERT_POLISH_MIDDLE","republican-house-seats-after-the-2026-midterm-elections","which-party-will-win-the-house-in-2026",10,{"220-224","225-229","230+"},"House:Rep (218-219 $2x Middle)"),("LP2_SENATE_CONVERT_POLISH_MIDDLE","republican-senate-seats-after-the-2026-midterm-elections-927","which-party-will-win-the-senate-in-2026",11,{"51","52","53","54","55","56","57+"},"Sen:Rep (50-Seat $2x Middle)")]
 for L,l,k,I,d,s in u:
  K=events_by_slug.get(l)or{};ev_c=events_by_slug.get(k)or{}
  if not K or not ev_c or K.get("closed")or ev_c.get("closed"):continue
  if not K.get("negRisk")or K.get("negRiskAugmented",True):continue
  H=str(K.get("negRiskMarketID")or"").strip().lower();C=K.get("markets")or[]
  if len(C)!=I:continue
  B,r,_=verify_negrisk_adapter_slate_sync(H,I,rpc_url=rpc_url)
  if not B:continue
  A=float(r)/1e4;G=next((m for m in(ev_c.get("markets")or[])if str(m.get("groupItemTitle")or"").strip().lower()=="republican party"and not m.get("closed")),None)
  if G is None:continue
  q=_parse_clob_tokens(G)
  if not q:continue
  g=q[0];z,y=_extract_market_fee_rate(G);c=[]
  for F,m in enumerate(C):
   grp=str(m.get("groupItemTitle")or"").strip().lower()
   if grp in d:
    tk=_parse_clob_tokens(m)
    if not tk:break
    J=str(m.get("questionID")or"").strip().lower();h=int(J[64:],16)if(len(J)==66 and J.startswith("0x")and J[:64]==H[:64])else F;p,o=_extract_market_fee_rate(m);c.append((h,grp,tk[1],p,o,str(m.get("id")or"")))
  if len(c)!=len(d):continue
  E=len(c);v=int(math.floor(min(80.,target_budget_usd)))
  if v<min_shares:continue
  b=float(v)
  for _,_,n_tok,_,_,_ in c:asks=(books_by_token.get(n_tok)or{}).get("asks")or[];b=min(b,sum(float(x.get("size",0))for x in asks if float(x.get("price",0))>0))
  rep_asks=(books_by_token.get(g)or{}).get("asks")or[];b=min(b,sum(float(x.get("size",0))for x in rep_asks if float(x.get("price",0))>0));t=int(math.floor(b))
  if t<min_shares:continue
  i=t*(1.-A);D=_walk_side_exact_shares(rep_asks,i,z,y,is_ask=True)
  if D is None:continue
  no_walks=[];n=True
  for h,grp,n_tok,p,o,mid_m in c:
   wn=_walk_side_exact_shares((books_by_token.get(n_tok)or{}).get("asks")or[],float(t),p,o,is_ask=True)
   if wn is None:n=False;break
   no_walks.append((h,grp,n_tok,mid_m,wn))
  if not n:continue
  j=sum(w["net_per_share"]for*_,w in no_walks);f=float(E-1)*(1.-A);a=(j-f)/max(1e-6,(1.-A))+float(D["net_per_share"])
  if a<=max_synthetic_box_cost_net:e=[{"token_id":n_tok,"market_id":mid_m,"side":"NO","label":f"NO[{grp}]","fee_rate":.0,"fee_exponent":1.}for _,grp,n_tok,mid_m,_ in no_walks]+[{"token_id":g,"market_id":str(G.get("id")or""),"side":"YES","label":f"YES[{s}]","fee_rate":z,"fee_exponent":y}];M.append({"mode":L,"seat_slug":l,"neg_risk_market_id":H,"m_no_legs":E,"index_set_int":sum(1<<qi for qi,*_ in no_walks),"shares_in":t,"shares_out":round(i,4),"synthetic_box_cost_net":round(a,4),"guaranteed_floor_edge_ps":round(1.-a,4),"l1_usd":round(min([w["l1_usd"]for*_,w in no_walks]+[D["l1_usd"]]),2),"close_ts":_parse_iso_ts(K.get("endDate"))or.0,"legs":e,"label":f"{L}: CONV({E}xNO)+YES[{s}] @ {a:.4f}"})
 return M
@dataclass
class NbaSubperiodMarketSpec:event_id:str;market_id:str;condition_id:str;period_scope:str;kind:str;line:Optional[float];team_side:Optional[str];tok_0:str;tok_1:str;out_0:str;out_1:str;fee_rate:float;settle_est_ts:float;display_title:str;neg_risk=False;fee_exponent=1.
@dataclass
class NbaSubperiodAndExtPropSlate:event_id:str;slug:str;title:str;tipoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;ext_props_by_player_stat=field(default_factory=dict);subperiod_markets=field(default_factory=list)
_NBA_SUBPERIOD_SMT_MAP={"first_half_moneyline":("1H","ML"),"q1_moneyline":("Q1","ML"),"first_half_spreads":("1H","SPREAD"),"q1_spreads":("Q1","SPREAD"),"q2_spreads":("Q2","SPREAD"),"q3_spreads":("Q3","SPREAD"),"first_half_totals":("1H","TOTAL"),"q1_totals":("Q1","TOTAL"),"q2_totals":("Q2","TOTAL"),"q3_totals":("Q3","TOTAL"),"q4_totals":("Q4","TOTAL"),"team_totals":("FG","TEAM_TOTAL"),"first_half_team_totals":("1H","TEAM_TOTAL"),"second_half_team_totals":("2H","TEAM_TOTAL")}
def parse_nba_subperiod_and_ext_props(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived"):return None
 I=str(ev.get("slug")or"").lower()
 if not I.startswith("nba-")or I.endswith("-exact-margin"):return None
 D=str(ev.get("title")or"");C=re.split(r"\s+(?:vs\.?|@)\s+",D,maxsplit=1,flags=re.IGNORECASE)
 if len(C)!=2:return None
 x,w=_canon_nba_team(C[0]),_canon_nba_team(C[1]);v=_parse_iso_ts(ev.get("startTime")or ev.get("gameStartTime")or ev.get("endDate"))or.0
 if v<=.0 or(now_ts is not None and v<now_ts-8.*3600.):return None
 l=v+3.25*3600.;B=str(ev.get("id")or"");j={};n=[]
 for m in ev.get("markets")or[]:
  if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
  fr,fe=_extract_market_fee_rate(m);H=_parse_clob_tokens(m);outs=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))]
  if not H or len(outs)!=2:continue
  L=str(m.get("sportsMarketType")or"").strip().lower();A=str(m.get("groupItemTitle")or m.get("question")or"").strip()
  if L in("steals","blocks")and[o.lower()for o in outs]==["yes","no"]:
   G=_EXT_PROP_TITLE_RE.match(A);b=m.get("line");ln=float(b)if b is not None else(float(G.group(3))if G else float("nan"))
   if G and _is_half_hook(ln)and ln>=.5:
    z=G.group(1).strip();pk=canon_player_name(z)
    if pk:j.setdefault((pk,L),[]).append(NbaPlayerPropRung(event_id=B,event_slug=I,game_title=D,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),player_name=z,player_key=pk,stat_type=L,line=ln,yes_token=H[0],no_token=H[1],fee_rate=fr,tipoff_ts=v,settle_est_ts=l,home_team=w,away_team=x,fee_exponent=fe))
   continue
  if L not in _NBA_SUBPERIOD_SMT_MAP:continue
  p,F=_NBA_SUBPERIOD_SMT_MAP[L];d={"Q1":.75,"Q2":1.35,"1H":1.35,"Q3":2.15}.get(p,3.25)*3600.;i=v+d
  if F=="ML":
   c0,c1=_canon_nba_team(outs[0]),_canon_nba_team(outs[1])
   if{c0,c1}!={x,w}:continue
   n.append(NbaSubperiodMarketSpec(B,str(m.get("id")or""),str(m.get("conditionId")or""),p,"ML",.0,c0,H[0],H[1],outs[0],outs[1],fr,i,A or f"{p} ML",bool(m.get("negRisk")),fe))
  elif F=="SPREAD":
   b=m.get("line")
   if b is None:continue
   ln=abs(float(b))
   if not _is_half_hook(ln):continue
   c0,c1=_canon_nba_team(outs[0]),_canon_nba_team(outs[1])
   if{c0,c1}!={x,w}:continue
   u=str(m.get("question")or A);y=_SPREAD_FAV_RE.search(u);a=None
   if y:
    t=_canon_nba_team(y.group(1));K=float(y.group(2))
    if t in(x,w):a=t if K<0 else(w if t==x else x)
   if a is None:
    E=str(m.get("description")or"");J=re.search(r'resolve\s+to\s+"([^"]+)"\s+if\s+.+?\s+(?:wins|outscores).+?\s+by\s+(\d+)\s+or\s+more',E,re.I)
    if J:
     s=_canon_nba_team(J.group(1))
     if s in(x,w):a=s
   if a is None:continue
   if c0==a:h,g,f,e=H[0],H[1],outs[0],outs[1]
   else:h,g,f,e=H[1],H[0],outs[1],outs[0]
   n.append(NbaSubperiodMarketSpec(B,str(m.get("id")or""),str(m.get("conditionId")or""),p,"SPREAD",ln,a,h,g,f,e,fr,i,f"{p} {f}(-{ln})/{e}(+{ln})",bool(m.get("negRisk")),fe))
  elif F in("TOTAL","TEAM_TOTAL"):
   b=m.get("line")
   if b is None:continue
   ln=float(b)
   if ln<=.0 or not _is_half_hook(ln):continue
   if not(outs[0].lower().startswith("over")and outs[1].lower().startswith("under")):continue
   c=None
   if F=="TEAM_TOTAL":
    q=(str(m.get("question")or A)).split("O/U")[0];ca=x in _canon_nba_team(q)or _norm_team(C[0])in _norm_team(q);ch=w in _canon_nba_team(q)or _norm_team(C[1])in _norm_team(q)
    if ca==ch:continue
    c=x if ca else w
   n.append(NbaSubperiodMarketSpec(B,str(m.get("id")or""),str(m.get("conditionId")or""),p,F,ln,c,H[0],H[1],"Over","Under",fr,i,A or f"{p} O/U {ln}",bool(m.get("negRisk")),fe))
 for k in j:j[k].sort(key=lambda r:r.line)
 if not j and not n:return None
 return NbaSubperiodAndExtPropSlate(event_id=B,slug=I,title=D,tipoff_ts=v,settle_est_ts=l,home_team=w,away_team=x,ext_props_by_player_stat=j,subperiod_markets=n)
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
 for per in("1H","Q1"):
  A=[m for m in slate.subperiod_markets if m.period_scope==per and m.kind=="ML"];z=[m for m in slate.subperiod_markets if m.period_scope==per and m.kind=="SPREAD"]
  if not A or not z:continue
  s=A[0];c0=s.team_side;c1=slate.home_team if c0==slate.away_team else slate.away_team;g={c0:(s.tok_0,s.tok_1,s.out_0),c1:(s.tok_1,s.tok_0,s.out_1)}
  for r in z:
   o=r.team_side
   if o not in g or r.line is None or r.line<.5:continue
   f,e,k=g[o];d,b,h=r.tok_1,r.tok_0,r.out_1;q=best_asks.get(f);n=best_asks.get(d)
   if q is None or n is None:continue
   a=round(float(q)+float(n),4);c=round(_net_unit_ask(float(q),s.fee_rate,s.fee_exponent)+_net_unit_ask(float(n),r.fee_rate,r.fee_exponent),4)
   if c<=max_box_cost_net:y.append({"mode":f"SP4_{per}_ML_SPREAD_MIDDLE","event_id":slate.event_id,"slug":slate.slug,"title":slate.title,"box_cost_gross":a,"box_cost_net":c,"close_ts":r.settle_est_ts,"leg_a":{"token_id":f,"opp_token_id":e,"condition_id":s.condition_id,"market_id":s.market_id,"side":"ML_FAV","label":f"{per} ML[{k}]","fee_rate":s.fee_rate,"fee_exponent":s.fee_exponent,"neg_risk":bool(s.neg_risk),"strike":.0,"end_ts":s.settle_est_ts},"leg_b":{"token_id":d,"opp_token_id":b,"condition_id":r.condition_id,"market_id":r.market_id,"side":"DOG_PLUS","label":f"{per} {h}(+{r.line})","fee_rate":r.fee_rate,"fee_exponent":r.fee_exponent,"neg_risk":bool(r.neg_risk),"strike":r.line,"end_ts":r.settle_est_ts},"label":f"{slate.title}: {per} ML[{k}] + {h}(+{r.line})"})
 y.sort(key=lambda x:float(x["box_cost_net"]));return y
def parse_espn_nba_extended_summary(summary_json):
 j={}
 for n in((summary_json or{}).get("boxscore")or{}).get("players")or[]:
  for stat_blk in n.get("statistics")or[]:
   keys=[str(k)for k in(stat_blk.get("keys")or[])];s=next((i for i,k in enumerate(keys)if k=="minutes"),-1);r=next((i for i,k in enumerate(keys)if k=="steals"),-1);q=next((i for i,k in enumerate(keys)if k=="blocks"),-1)
   for C in stat_blk.get("athletes")or[]:
    if C.get("didNotPlay"):continue
    z=canon_player_name(str((C.get("athlete")or{}).get("displayName")or""));B=C.get("stats")or[]
    if not z or not B:continue
    if 0<=s<len(B)and str(B[s]).strip()in("","0","0:00","--"):continue
    A={}
    try:
     if 0<=r<len(B):A["steals"]=int(str(B[r]).split("-")[0])
     if 0<=q<len(B):A["blocks"]=int(str(B[q]).split("-")[0])
    except ValueError:continue
    if A:j[z]=A
 h={"home":{},"away":{}};e,d=0,0;f,a=0,.0;g,c,b="pre",False,False;x=((summary_json or{}).get("header")or{}).get("competitions")or[]
 if x:
  c0=x[0];v=c0.get("status")or{};p=v.get("type")or{};f=int(v.get("period")or 0);g=str(p.get("state")or"pre").lower();c=bool(p.get("completed"));u=str(p.get("description")or p.get("name")or"").lower();b="halftime"in u;m=str(v.get("displayClock")or"")
  if":"in m:
   try:mm,ss=m.split(":",1);a=float(mm)*60.+float(ss)
   except ValueError:a=.0
  for y in c0.get("competitors")or[]:
   ha="home"if str(y.get("homeAway")or"").lower()=="home"else"away"
   try:l=int(float(y.get("score")or 0))
   except(TypeError,ValueError):l=0
   if ha=="home":e=l
   else:d=l
   for t,ls in enumerate(y.get("linescores")or[]):
    w=int(ls.get("period")or(t+1));o=ls.get("value")if ls.get("value")is not None else ls.get("displayValue")
    try:h[ha][w]=int(float(o))
    except(TypeError,ValueError):pass
 return{"player_ext":j,"linescores":h,"home_score":e,"away_score":d,"period":f,"clock_sec":a,"state":g,"completed":c,"is_halftime":b}
def fetch_espn_nba_full_summary_sync(espn_game_id,timeout=5.):c=ESPN_NBA_SUMMARY_URL.format(game_id=espn_game_id);b=urllib.request.Request(c,headers={"User-Agent":"DominusSportsOracle/1.0"});a=json.loads(urllib.request.urlopen(b,timeout=timeout).read().decode("utf-8"));return parse_espn_nba_boxscore_players(a),parse_espn_nba_extended_summary(a)
def evaluate_sp4_subperiod_and_ext_locks(slate,ext_summary):
 r=str(ext_summary.get("state")or"pre")
 if r not in("in","post"):return[]
 is_final=bool(ext_summary.get("completed")and r=="post");is_ht=bool(ext_summary.get("is_halftime"));period=int(ext_summary.get("period")or 0);clock_sec=float(ext_summary.get("clock_sec")or 720.);ls_h=(ext_summary.get("linescores")or{}).get("home")or{};ls_a=(ext_summary.get("linescores")or{}).get("away")or{};home_tot=int(ext_summary.get("home_score")or 0);away_tot=int(ext_summary.get("away_score")or 0);p=[]
 def _scope_scores(p_scope):
  if p_scope=="FG":return away_tot,home_tot,is_final
  if p_scope in("Q1","Q2","Q3","Q4"):
   q=int(p_scope[1])
   if q not in ls_a or q not in ls_h:return None,None,False
   a=is_final or(q==1 and is_ht)or(period>q and(clock_sec<=6e2 or period>=q+2));return ls_a[q],ls_h[q],a
  if p_scope=="1H":
   if 1 not in ls_a or 1 not in ls_h:return None,None,False
   e=ls_a.get(1,0)+ls_a.get(2,0);d=ls_h.get(1,0)+ls_h.get(2,0);a=is_final or(2 in ls_a and 2 in ls_h and(period>=3 or is_ht));return e,d,a
  if p_scope=="2H":
   if period<3:return None,None,False
   c=sum(v for k,v in ls_a.items()if k>=3);b=sum(v for k,v in ls_h.items()if k>=3);return c,b,is_final
  return None,None,False
 for sm in slate.subperiod_markets:
  w,u,b=_scope_scores(sm.period_scope)
  if w is None or u is None:continue
  d={slate.away_team:w,slate.home_team:u}
  if sm.kind in("TOTAL","TEAM_TOTAL")and sm.line is not None:
   g=(w+u)if sm.kind=="TOTAL"else d.get(sm.team_side or"",-1)
   if g<0:continue
   if b:
    f=.5 if(is_final or period>=(int(sm.period_scope[1])+2 if sm.period_scope.startswith("Q")else 4))else 1.5
    if abs(float(g)-sm.line)>=f:c=float(g)>sm.line;p.append({"mode":f"SP4_{sm.period_scope}_SETTLED_TOTAL_LOCK","market_id":sm.market_id,"condition_id":sm.condition_id,"token_id":sm.tok_0 if c else sm.tok_1,"opp_token_id":sm.tok_1 if c else sm.tok_0,"side_label":"OVER"if c else"UNDER","display_label":f"{sm.display_title} [{'OVER'if c else'UNDER'} {g} settled]","fee_rate":sm.fee_rate,"fee_exponent":sm.fee_exponent,"neg_risk":bool(sm.neg_risk),"p_lock":.999,"close_ts":sm.settle_est_ts})
    continue
   if g>=int(math.floor(sm.line))+3:p.append({"mode":f"SP4_{sm.period_scope}_LIVE_OVER_CLINCH","market_id":sm.market_id,"condition_id":sm.condition_id,"token_id":sm.tok_0,"opp_token_id":sm.tok_1,"side_label":"OVER","display_label":f"{sm.display_title} [Live pts={g} >= {int(math.floor(sm.line))+3}]","fee_rate":sm.fee_rate,"fee_exponent":sm.fee_exponent,"neg_risk":bool(sm.neg_risk),"p_lock":.998,"close_ts":sm.settle_est_ts})
  elif b and sm.kind=="SPREAD"and sm.line is not None and sm.team_side in d:
   o=sm.team_side;n=slate.home_team if o==slate.away_team else slate.away_team;a=float(d[o]-d[n])
   if abs(a-sm.line)>=(.5 if is_final else 1.5):e=a>sm.line;p.append({"mode":f"SP4_{sm.period_scope}_SETTLED_SPREAD_LOCK","market_id":sm.market_id,"condition_id":sm.condition_id,"token_id":sm.tok_0 if e else sm.tok_1,"opp_token_id":sm.tok_1 if e else sm.tok_0,"side_label":sm.out_0 if e else sm.out_1,"display_label":f"{sm.display_title} [Margin={a:+.0f} settled]","fee_rate":sm.fee_rate,"fee_exponent":sm.fee_exponent,"neg_risk":bool(sm.neg_risk),"p_lock":.999,"close_ts":sm.settle_est_ts})
  elif b and sm.kind=="ML"and sm.team_side in d:
   t0=sm.team_side;t1=slate.home_team if t0==slate.away_team else slate.away_team;t=d[t0]-d[t1]
   if abs(t)>=(1 if is_final else 2):i=t>0;p.append({"mode":f"SP4_{sm.period_scope}_SETTLED_ML_LOCK","market_id":sm.market_id,"condition_id":sm.condition_id,"token_id":sm.tok_0 if i else sm.tok_1,"opp_token_id":sm.tok_1 if i else sm.tok_0,"side_label":sm.out_0 if i else sm.out_1,"display_label":f"{sm.display_title} [{sm.out_0 if i else sm.out_1} +{abs(t)} settled]","fee_rate":sm.fee_rate,"fee_exponent":sm.fee_exponent,"neg_risk":bool(sm.neg_risk),"p_lock":.999,"close_ts":sm.settle_est_ts})
 if is_final:
  m=ext_summary.get("player_ext")or{}
  for(s,h),l in slate.ext_props_by_player_stat.items():
   j=(m.get(s)or{}).get(h)
   if j is None:continue
   for rg in l:
    if int(j)>=int(math.floor(rg.line))+2:p.append({"mode":"SP4_FINAL_EXT_STAT_LOCK","market_id":rg.market_id,"condition_id":rg.condition_id,"token_id":rg.yes_token,"opp_token_id":rg.no_token,"side_label":"YES","display_label":f"{rg.player_name} {h} O{rg.line} [Final={j}]","fee_rate":rg.fee_rate,"fee_exponent":rg.fee_exponent,"neg_risk":False,"p_lock":.998,"close_ts":rg.settle_est_ts})
 return p
@dataclass
class MonotonicRung:market_id:str;condition_id:str;label:str;order_val:float;end_ts:float;yes_token:str;no_token:str;fee_rate:float;fee_exponent:float;clause_key:str;neg_risk=False
@dataclass
class CalendarOrScalarLadderSpec:event_id:str;slug:str;title:str;ladder_kind:str;rungs:List[MonotonicRung]
def _canon_clause_stem(desc,group_title):
 s=str(desc or"").lower().replace("“",'"').replace("”",'"').replace("’","'");b=_TZ_DETECT_RE.search(desc or"");a=(b.group(1).upper().replace(" ","_")if b else"NO_TZ");gt=str(group_title or"").strip().lower()
 if gt and len(gt)>=2:s=s.replace(gt," <RUNG> ")
 s=_MONTH_DATE_STRIP_RE.sub(" <DATE> ",s);s=re.sub(r"\$\s*[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:[kmb]|million|billion)?"," <STRIKE> ",s);s=re.sub(r"\s+"," ",s).strip();return s,a
_MONTH_MAP_CAL1={"january":1,"jan":1,"february":2,"feb":2,"march":3,"mar":3,"april":4,"apr":4,"may":5,"june":6,"jun":6,"july":7,"jul":7,"august":8,"aug":8,"september":9,"sep":9,"sept":9,"october":10,"oct":10,"november":11,"nov":11,"december":12,"dec":12}
def _parse_group_label_date_ts(lbl,ref_end_ts):
 m=re.search(r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:,\s*(20\d{2}))?\b",str(lbl or""),re.IGNORECASE)
 if not m:return None
 b=_MONTH_MAP_CAL1.get(m.group(1).lower());a=int(m.group(2))
 if not b:return None
 yr=int(m.group(3))if m.group(3)else datetime.fromtimestamp(max(1.,ref_end_ts),tz=timezone.utc).year
 try:return datetime(yr,b,a,23,59,59,tzinfo=timezone.utc).timestamp()
 except ValueError:return None
def _parse_scalar_strike(lbl):
 s=str(lbl or"").strip()
 if re.search(r"(?:↓|\bbelow\b|\bunder\b|\bless\s+than\b|\bat\s+most\b|\bfewer\s+than\b|\bbetween\b)",s,re.IGNORECASE):return None
 m=_SCALAR_MAG_RE.search(s)
 if not m:return None
 c=float(m.group(1).replace(",",""));b=(m.group(2)or"").lower();a={"k":1e3,"thousand":1e3,"m":1e6,"million":1e6,"b":1e9,"billion":1e9}.get(b,1.);return c*a
def parse_cal1_monotonic_ladder_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived")or ev.get("negRisk"):return[]
 z=str(ev.get("slug")or"");t=str(ev.get("title")or"")
 if _COVERED_CRYPTO_PYTH_SLUG_RE.search(z)or _COVERED_CRYPTO_PYTH_SLUG_RE.search(t):return[]
 mkts=[m for m in(ev.get("markets")or[])if not m.get("closed")and not m.get("archived")and m.get("acceptingOrders")is not False]
 if len(mkts)<2:return[]
 if any(m.get("sportsMarketType")for m in mkts):return[]
 slug_l,title_l=z.lower(),t.lower();d=str(mkts[0].get("description")or"");l=d.lower();b=bool(_RESET_WINDOW_VETO_RE.search(title_l)or _RESET_WINDOW_VETO_RE.search(slug_l.replace("-"," ")));a=None
 if not b and("continues-through"in slug_l or"continues through"in title_l or("remains in effect"in l and"through"in l)or('resolve to "no" if'in l.replace("“",'"').replace("”",'"')and"by the specified date"in l)):a="SURVIVAL"
 elif not b and(any(k in slug_l for k in("-by","before-"))or any(k in title_l for k in(" by "," before "))):
  if"resolve"in l and("by "in l or"before "in l or"between market creation and"in l):a="DEADLINE_BY"
 elif any(k in title_l for k in("fdv above","total commitments","market cap above","box office","revenue above")):a="SCALAR_ABOVE"
 if a is None:return[]
 e={}
 for m in mkts:
  y=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))];x=_parse_clob_tokens(m)
  if y!=["yes","no"]or not x:continue
  j=str(m.get("description")or"")
  if len(j)<60:continue
  B=str(m.get("groupItemTitle")or m.get("question")or"").strip();v,i=_canon_clause_stem(j,B);h=_parse_iso_ts(m.get("endDate"))or.0
  if h<=.0 or(now_ts is not None and h<now_ts+120.):continue
  if a in("SURVIVAL","DEADLINE_BY"):
   g=_parse_group_label_date_ts(B,h)
   if g is not None and abs(g-h)>14.*86400.:
    if h<g-2.*86400.:continue
    c=g
   else:c=g if g is not None else h
  else:
   desc_ml=j.lower()
   if not any(w in desc_ml for w in("above","greater than","exceed","at least","more than","over ")):continue
   if re.search(r"\b(?:less\s+than\s+\$|fewer\s+than|at\s+most)\b",desc_ml):continue
   u=_parse_scalar_strike(B)
   if u is None or u<=.0:continue
   c=u
  fr,fe=_extract_market_fee_rate(m);ck=f"{i}::{v[:220]}";e.setdefault(ck,[]).append(MonotonicRung(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),label=B[:36],order_val=c,end_ts=h,yes_token=x[0],no_token=x[1],fee_rate=fr,fee_exponent=fe,clause_key=ck,neg_risk=bool(m.get("negRisk"))))
 s=[];q=str(ev.get("id")or"")
 for p,(ck,A)in enumerate(e.items()):
  A.sort(key=lambda r:r.order_val);n=[];f=43200. if a in("SURVIVAL","DEADLINE_BY")else 1e-6
  for r in A:
   if not n or(r.order_val-n[-1].order_val)>=f:n.append(r)
  if len(n)>=2:s.append(CalendarOrScalarLadderSpec(event_id=f"{q}_{p}"if p>0 else q,slug=z,title=t,ladder_kind=a,rungs=n))
 return s
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
 mkts=[m for m in(ev.get("markets")or[])if not m.get("closed")and not m.get("archived")];l=[m for m in mkts if str(m.get("sportsMarketType")or"").lower()=="exact_margin"];ml_mkt=next((m for m in mkts if str(m.get("sportsMarketType")or"").lower()=="moneyline"),None)
 if len(l)!=10 or ml_mkt is None:return None
 e=_parse_iso_ts(ev.get("startTime")or ml_mkt.get("gameStartTime")or ev.get("endDate"))or.0;u=e+3.75*3600.
 if now_ts is not None and u<now_ts+60.:return None
 k=_parse_clob_tokens(ml_mkt);j=[str(o).strip()for o in _parse_json_list(ml_mkt.get("outcomes"))]
 if not k or len(j)!=2:return None
 t,r=j[0],j[1];Y,X=_norm_team(t),_norm_team(r);parsed_em=[];a=False
 for m in l:
  tk=_parse_clob_tokens(m);W=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not tk or W!=["yes","no"]:return None
  fr,fe=_extract_market_fee_rate(m);_b=str(m.get("groupItemTitle")or m.get("question")or"").strip()
  if re.search(r"exact\s+margin:\s*tie\b",_b,re.I):a=True;parsed_em.append(("TIE",0,0,m,tk,fr,fe,"Tie"));continue
  mb=_NFL_EM_BAND_RE.search(_b)
  if not mb:return None
  V=_norm_team(mb.group(1));lo=int(mb.group(2));hi=int(mb.group(3))if mb.group(3)else 999;L="A"if(V==Y or V in Y or Y in V)else("B"if(V==X or V in X or X in V)else"")
  if not L:return None
  parsed_em.append((L,lo,hi,m,tk,fr,fe,_b.replace("Exact Margin:","").strip()))
 if not a or len(parsed_em)!=10:return None
 for side_chk in("A","B"):
  _a=sorted([(lo,hi)for wk,lo,hi,*_ in parsed_em if wk==side_chk])
  if not _a or _a[0][0]!=1 or _a[-1][1]!=999:return None
  for K in range(len(_a)-1):
   if _a[K][1]+1!=_a[K+1][0]:return None
 d=11;U=[];J,I=_extract_market_fee_rate(ml_mkt);H,q=str(ml_mkt.get("id")or""),str(ml_mkt.get("conditionId")or"");G=[1. if wk=="A"else(.5 if wk=="TIE"else.0)for wk,*_ in parsed_em]+[.5];F=[1. if wk=="B"else(.5 if wk=="TIE"else.0)for wk,*_ in parsed_em]+[.5];E=bool(ml_mkt.get("negRisk"));U.append({"market_id":H,"condition_id":q,"token_id":k[0],"opp_token_id":k[1],"side":"ML_A","label":f"ML[{t}]","fee_rate":J,"fee_exponent":I,"neg_risk":E,"end_ts":u,"payoff_vec":G,"strike":.0});U.append({"market_id":H,"condition_id":q,"token_id":k[1],"opp_token_id":k[0],"side":"ML_B","label":f"ML[{r}]","fee_rate":J,"fee_exponent":I,"neg_risk":E,"end_ts":u,"payoff_vec":F,"strike":.0})
 for st_i,(wk,lo,hi,T,D,S,R,C)in enumerate(parsed_em):v_y=[1. if s==st_i else.0 for s in range(10)]+[.5];Z=[1.-v_y[s]for s in range(10)]+[.5];B,A=str(T.get("id")or""),str(T.get("conditionId")or"");z=bool(T.get("negRisk"));U.append({"market_id":B,"condition_id":A,"token_id":D[0],"opp_token_id":D[1],"side":"YES","label":f"EM_Y[{C}]","fee_rate":S,"fee_exponent":R,"neg_risk":z,"end_ts":u,"payoff_vec":v_y,"strike":float(lo)});U.append({"market_id":B,"condition_id":A,"token_id":D[1],"opp_token_id":D[0],"side":"NO","label":f"EM_N[{C}]","fee_rate":S,"fee_exponent":R,"neg_risk":z,"end_ts":u,"payoff_vec":Z,"strike":float(lo)})
 for sm in mkts:
  if str(sm.get("sportsMarketType")or"").lower()!="spreads"or sm.get("line")is None:continue
  ln=abs(float(sm.get("line")))
  if not _is_half_hook(ln):continue
  Q=_parse_clob_tokens(sm);p=[str(o).strip()for o in _parse_json_list(sm.get("outcomes"))];P=_SPREAD_FAV_RE.search(str(sm.get("question")or sm.get("groupItemTitle")or""))
  if not Q or len(p)!=2 or not P:continue
  i=_norm_team(P.group(1));h=float(P.group(2));fav_w=("A"if i==Y else"B")if h<0 else("B"if i==Y else"A")
  if i not in(Y,X):continue
  if any(wk==fav_w and lo<ln<hi for wk,lo,hi,*_ in parsed_em):continue
  O=_norm_team(p[0]);y=Y if fav_w=="A"else X;g,f=(Q[0],Q[1])if O==y else(Q[1],Q[0]);c=t if fav_w=="A"else r;b=r if fav_w=="A"else t;v_fav=[1. if(wk==fav_w and lo>ln)else.0 for wk,lo,hi,*_ in parsed_em]+[.5];x=[1.-v_fav[s]for s in range(10)]+[.5];N,M=_extract_market_fee_rate(sm);w,n=str(sm.get("id")or""),str(sm.get("conditionId")or"");v=bool(sm.get("negRisk"));U.append({"market_id":w,"condition_id":n,"token_id":g,"opp_token_id":f,"side":"SPREAD_FAV","label":f"{c}(-{ln})","fee_rate":N,"fee_exponent":M,"neg_risk":v,"end_ts":u,"payoff_vec":v_fav,"strike":-ln});U.append({"market_id":w,"condition_id":n,"token_id":f,"opp_token_id":g,"side":"SPREAD_DOG","label":f"{b}(+{ln})","fee_rate":N,"fee_exponent":M,"neg_risk":v,"end_ts":u,"payoff_vec":x,"strike":ln})
 return{"event_id":str(ev.get("id")or""),"slug":str(ev.get("slug")or""),"title":str(ev.get("title")or""),"end_ts":u,"legs":U}
def detect_multisport_ml_spread_polish_middles(ev,best_asks,sport_hint="NFL",max_box_cost_net=.988):
 if ev.get("closed")or ev.get("archived")or ev.get("negRisk"):return[]
 K=str(ev.get("slug")or"").lower()
 if K.startswith("nba-"):return[]
 mkts=[m for m in(ev.get("markets")or[])if not m.get("closed")and not m.get("archived")]
 if len(mkts)<2:return[]
 h=_parse_iso_ts(ev.get("startTime")or ev.get("endDate"))or.0;E=str(ev.get("title")or K);D=str(ev.get("id")or"");a=(("FG","moneyline","spreads",3.75*3600.),("1H","first_half_moneyline","first_half_spreads",1.75*3600.),("Q1","q1_moneyline","q1_spreads",1.*3600.));J=[]
 for C,ml_smt,q,B in a:
  ml_m=next((m for m in mkts if str(m.get("sportsMarketType")or"").lower()==ml_smt),None)
  if ml_m is None:continue
  A=_parse_clob_tokens(ml_m);l=[str(o).strip()for o in _parse_json_list(ml_m.get("outcomes"))]
  if not A or len(l)!=2:continue
  I,H=_norm_team(l[0]),_norm_team(l[1])
  if I in("yes","no","over","under")or I==H:continue
  z,y=_extract_market_fee_rate(ml_m);p={I:(A[0],A[1],l[0]),H:(A[1],A[0],l[1])};g=h+B
  for sm in mkts:
   if str(sm.get("sportsMarketType")or"").lower()!=q or sm.get("line")is None:continue
   ln=abs(float(sm.get("line")))
   if ln<.5 or not _is_half_hook(ln):continue
   w=_parse_clob_tokens(sm);k=[str(o).strip()for o in _parse_json_list(sm.get("outcomes"))];G=_SPREAD_FAV_RE.search(str(sm.get("question")or sm.get("groupItemTitle")or""))
   if not w or len(k)!=2 or not G:continue
   j=_norm_team(G.group(1));L=float(G.group(2))
   if j not in(I,H):continue
   v=j if L<0 else(H if j==I else I);F=_norm_team(k[0])
   if{F,_norm_team(k[1])}!={I,H}:continue
   i=w[1]if F==v else w[0];d=w[0]if F==v else w[1];f=k[1]if F==v else k[0];c,b,e=p[v];u=best_asks.get(c);n=best_asks.get(i)
   if u is None or n is None:continue
   t,s=_extract_market_fee_rate(sm);r=round(_net_unit_ask(u,z,y)+_net_unit_ask(n,t,s),4)
   if r<=max_box_cost_net:J.append({"mode":f"LP1_{sport_hint}_{C}_ML_SPREAD_MIDDLE","sport":sport_hint,"event_id":D,"slug":K,"title":E,"box_cost_net":r,"close_ts":g,"leg_a":{"token_id":c,"opp_token_id":b,"condition_id":str(ml_m.get("conditionId")or""),"market_id":str(ml_m.get("id")or""),"side":"ML_FAV","label":f"{C} ML[{e}]","fee_rate":z,"fee_exponent":y,"neg_risk":bool(ml_m.get("negRisk")),"strike":.0,"end_ts":g},"leg_b":{"token_id":i,"opp_token_id":d,"condition_id":str(sm.get("conditionId")or""),"market_id":str(sm.get("id")or""),"side":"DOG_PLUS","label":f"{C} {f}(+{ln})","fee_rate":t,"fee_exponent":s,"neg_risk":bool(sm.get("negRisk")),"strike":ln,"end_ts":g},"label":f"{E[:38]}: {C} ML[{e}] + {f}(+{ln})"})
 J.sort(key=lambda x:float(x["box_cost_net"]));return J
@dataclass
class LiveMultiSportGame:sport:str;game_id:str;start_ts:float;state:str;completed:bool;is_halftime:bool;period:int;clock_sec:float;home_name:str;away_name:str;home_score:int;away_score:int;linescores_home=field(default_factory=dict);linescores_away=field(default_factory=dict)
class ScoreConfirmationTracker:
 def __init__(self):self._first_seen={}
 def observe_and_confirmed_floor(self,sport,game_id,metric_key,current_val,now_ts,min_confirm_sec,is_final=False):
  if current_val<=0:self._purge_above(sport,game_id,metric_key,0);return 0
  self._purge_above(sport,game_id,metric_id=metric_key,max_keep=current_val)
  for v in range(1,min(current_val,120)+1):
   k=(sport,game_id,metric_key,v)
   if k not in self._first_seen:self._first_seen[k]=now_ts
  if is_final:return current_val
  a=0
  for v in range(1,min(current_val,120)+1):
   t0=self._first_seen.get((sport,game_id,metric_key,v),now_ts)
   if(now_ts-t0)>=min_confirm_sec:a=v
  return a
 def _purge_above(self,sport,game_id,metric_id="",max_keep=0):
  a=[k for k in self._first_seen if k[0]==sport and k[1]==game_id and k[2]==metric_id and k[3]>max_keep]
  for k in a:del self._first_seen[k]
 def prune(self,now_ts,max_age_sec=21600.):
  cutoff=float(now_ts)-float(max_age_sec);a=[k for k,t0 in self._first_seen.items()if t0<cutoff]
  for k in a:del self._first_seen[k]
  return len(a)
def parse_espn_multisport_scoreboard(sport,sb_json):
 q=[]
 for ev in(sb_json or{}).get("events")or[]:
  p=ev.get("competitions")or[]
  if not p:continue
  c0=p[0];st=c0.get("status")or{};r=st.get("type")or{};o=str(r.get("state")or"pre").lower()
  if o not in("in","post"):continue
  d=bool(r.get("completed"));l=str(r.get("description")or r.get("name")or"").lower();n="halftime"in l;k=int(st.get("period")or 0);c=float(st.get("clock")or.0);i=_parse_iso_ts(c0.get("date")or ev.get("date"))or.0;b,a="","";h,f=0,0;g={};e={}
  for tm in c0.get("competitors")or[]:
   ha=str(tm.get("homeAway")or"").lower();nm=str((tm.get("team")or{}).get("displayName")or(tm.get("team")or{}).get("shortDisplayName")or"")
   try:sc=int(float(tm.get("score")or 0))
   except(TypeError,ValueError):sc=0
   j={}
   for m,ls in enumerate(tm.get("linescores")or[]):
    t=int(ls.get("period")or(m+1));s=ls.get("value")if ls.get("value")is not None else ls.get("displayValue")
    try:j[t]=int(float(s))
    except(TypeError,ValueError):pass
   if ha=="home":b,h,g=nm,sc,j
   else:a,f,e=nm,sc,j
  if b and a:q.append(LiveMultiSportGame(sport=sport,game_id=str(ev.get("id")or""),start_ts=i,state=o,completed=d,is_halftime=n,period=k,clock_sec=c,home_name=b,away_name=a,home_score=h,away_score=f,linescores_home=g,linescores_away=e))
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
 p_all=p.split();e_all=e.split();p_core=[t for t in p_all if t not in _GENERIC_CLUB_SUFFIX_TOKS];e_core=[t for t in e_all if t not in _GENERIC_CLUB_SUFFIX_TOKS]
 if not p_core or not e_core:return False
 b=set(p_all)&_DERBY_DISAMBIG_TOKS;a=set(e_all)&_DERBY_DISAMBIG_TOKS
 if b and a and b.isdisjoint(a):return False
 if p_core==e_core:return True
 if set(p_core).issubset(set(e_core))and sum(len(t)for t in p_core)>=4:
  if len(p_core)==1 and a and not b:return False
  return True
 if set(e_core).issubset(set(p_core))and sum(len(t)for t in e_core)>=4:
  if len(e_core)==1 and b and not a:return False
  return True
 if p_core[-1]==e_core[-1]and len(p_core[-1])>=4 and p_core[-1]not in _DERBY_DISAMBIG_TOKS:
  if not(len(p_core)>=2 and len(e_core)>=2 and p_core[0]!=e_core[0]):return True
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
 for tl in soccer_tree.totals:
  ln=float(tl["line"])
  if d>=int(math.floor(ln))+1:h.append({"mode":"CL1_SOCCER_POST_VAR_OVER_LOCK","sport":"SOCCER","market_id":str(tl["market_id"]),"condition_id":str(tl["condition_id"]),"token_id":str(tl["over_token"]),"opp_token_id":str(tl["under_token"]),"fee_rate":float(tl["fee_rate"]),"fee_exponent":float(tl.get("fee_exponent",tl.get("fee_exp",1.))),"neg_risk":bool(tl.get("neg_risk",False)),"side_label":"OVER","display_label":f"{soccer_tree.title[:40]} Over {ln} [Goals={d} post-VAR]","p_lock":.998,"close_ts":float(soccer_tree.end_ts)})
 return h
def evaluate_cl1_multisport_corridor_clinch_locks(ms_spec,live_boards,tracker,now_ts):
 sp=str(ms_spec.sport or"").upper()
 if sp not in("NHL","NFL","CFB"):return[]
 m=live_boards.get(sp)or[];c=None;b=False
 for g in m:
  if abs(g.start_ts-float(ms_spec.start_ts))>8.*3600.:continue
  if _teams_match_fuzzy(ms_spec.team_a,g.away_name)and _teams_match_fuzzy(ms_spec.team_b,g.home_name):c,b=g,False;break
  if _teams_match_fuzzy(ms_spec.team_a,g.home_name)and _teams_match_fuzzy(ms_spec.team_b,g.away_name):c,b=g,True;break
 if c is None:return[]
 f=bool(c.completed and c.state=="post");s=c.home_score if b else c.away_score;r=c.away_score if b else c.home_score;p=c.linescores_home if b else c.linescores_away;o=c.linescores_away if b else c.linescores_home;l=[]
 if sp=="NHL":
  e=tracker.observe_and_confirmed_floor("NHL",c.game_id,"TOT_GOALS",s+r,now_ts,min_confirm_sec=150.,is_final=f)
  for lg in(ms_spec.legs_by_scope.get("FG:TOTAL")or[]):
   if lg.relation=="OVER"and e>=int(math.floor(lg.threshold))+1:l.append({"mode":"CL1_NHL_POST_CHALLENGE_OVER_LOCK","sport":"NHL","market_id":lg.market_id,"condition_id":lg.condition_id,"token_id":lg.token_id,"opp_token_id":lg.opp_token_id,"fee_rate":lg.fee_rate,"fee_exponent":lg.fee_exponent,"neg_risk":bool(getattr(lg,"neg_risk",False)),"side_label":lg.side_label,"display_label":f"{ms_spec.title[:38]} {lg.display_label} [Goals={e}]","p_lock":.998,"close_ts":float(ms_spec.settle_est_ts)})
  return l
 j=1 if f else 9
 for lg in(ms_spec.legs_by_scope.get("FG:TOTAL")or[]):
  if lg.relation=="OVER"and(s+r)>=int(math.floor(lg.threshold))+j:l.append({"mode":f"CL1_{sp}_SCORE_OVER_LOCK","sport":sp,"market_id":lg.market_id,"condition_id":lg.condition_id,"token_id":lg.token_id,"opp_token_id":lg.opp_token_id,"fee_rate":lg.fee_rate,"fee_exponent":lg.fee_exponent,"neg_risk":bool(getattr(lg,"neg_risk",False)),"side_label":lg.side_label,"display_label":f"{ms_spec.title[:36]} {lg.display_label} [Score={s}-{r}]","p_lock":.999 if f else.997,"close_ts":float(ms_spec.settle_est_ts)})
 for i,n in ms_spec.legs_by_scope.items():
  t=i.split(":")[0];pa,pb,a=None,None,False
  if t in("Q1","Q2","Q3"):
   q=int(t[1])
   if q in p and q in o:pa,pb=p[q],o[q];a=f or(q==1 and c.is_halftime)or(c.period>q and(c.clock_sec<=780. or c.period>=q+2))
  elif t=="1H":
   if 1 in p and 1 in o and 2 in p and 2 in o:pa,pb=p[1]+p[2],o[1]+o[2];a=f or c.is_halftime or c.period>=3
  if not a or pa is None or pb is None:continue
  if i.endswith(":TOTAL"):
   k=float(pa+pb)
   for lg in n:
    h=(k>lg.threshold)if lg.relation=="OVER"else(k<lg.threshold)
    if h and abs(k-lg.threshold)>=.5:l.append({"mode":f"CL1_{sp}_{t}_SETTLED_TOTAL_LOCK","sport":sp,"market_id":lg.market_id,"condition_id":lg.condition_id,"token_id":lg.token_id,"opp_token_id":lg.opp_token_id,"fee_rate":lg.fee_rate,"fee_exponent":lg.fee_exponent,"neg_risk":bool(getattr(lg,"neg_risk",False)),"side_label":lg.side_label,"display_label":f"{ms_spec.title[:34]} {lg.display_label} [{t}={int(k)} settled]","p_lock":.999,"close_ts":float(ms_spec.settle_est_ts)})
  elif i.endswith(":SPREAD"):
   d=float(pa-pb)
   for lg in n:
    h=(d>lg.threshold)if lg.relation=="GT"else(d<lg.threshold)
    if h and abs(d-lg.threshold)>=.5:l.append({"mode":f"CL1_{sp}_{t}_SETTLED_SPREAD_LOCK","sport":sp,"market_id":lg.market_id,"condition_id":lg.condition_id,"token_id":lg.token_id,"opp_token_id":lg.opp_token_id,"fee_rate":lg.fee_rate,"fee_exponent":lg.fee_exponent,"neg_risk":bool(getattr(lg,"neg_risk",False)),"side_label":lg.side_label,"display_label":f"{ms_spec.title[:34]} {lg.display_label} [{t} M={d:+.0f}]","p_lock":.999,"close_ts":float(ms_spec.settle_est_ts)})
 return l
@dataclass
class TennisTotalRung:market_id:str;condition_id:str;scope:str;line:float;over_token:str;under_token:str;fee_rate:float;fee_exp:float;neg_risk=False
@dataclass
class TennisMatchSpec:event_id:str;slug:str;title:str;player_a:str;player_b:str;end_ts:float;totals_by_scope=field(default_factory=dict);set1_a_token=None;set1_b_token=None;set1_resolved_winner=None;set2_a_token=None;set2_b_token=None;set2_resolved_winner=None;sets_ou25_over_token=None;sets_ou25_under_token=None;sets_ou25_market_id="";sets_ou25_condition_id="";sets_ou25_fee_rate=.05;sets_ou25_fee_exp=1.;sets_ou25_neg_risk=False;comp_yes_token=None;comp_no_token=None;comp_market_id="";comp_condition_id="";comp_fee_rate=.05;comp_fee_exp=1.;comp_neg_risk=False
def parse_tennis_retirement_safe_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived")or ev.get("negRisk"):return None
 g=str(ev.get("slug")or"").lower();mkts=ev.get("markets")or[]
 if not(g.startswith(("atp-","wta-"))or any(str(m.get("sportsMarketType")or"").startswith("tennis_")for m in mkts)):return None
 for m in mkts:
  e=str(m.get("groupItemTitle")or m.get("question")or"").lower()
  if re.search(r"\bset\s+[45]\b",e):return None
  if str(m.get("sportsMarketType")or"").lower()=="tennis_set_totals"and m.get("line")is not None and float(m.get("line"))>3.:return None
 ml_m=next((m for m in mkts if str(m.get("sportsMarketType")or"").lower()=="moneyline"),None)
 if ml_m is None:return None
 c=[str(o).strip()for o in _parse_json_list(ml_m.get("outcomes"))]
 if len(c)!=2:return None
 pa,pb=c[0],c[1];pa_n,pb_n=_norm_team(pa),_norm_team(pb);d=(_parse_iso_ts(ev.get("startTime")or ml_m.get("gameStartTime")or ev.get("endDate"))or.0)+3.25*3600.
 if now_ts is not None and d<now_ts+60.:return None
 spec=TennisMatchSpec(event_id=str(ev.get("id")or""),slug=g,title=str(ev.get("title")or g),player_a=pa,player_b=pb,end_ts=d)
 def _parse_set_winner(cm):
  tk=_parse_clob_tokens(cm);b=[_norm_team(str(x))for x in _parse_json_list(cm.get("outcomes"))];a=_parse_json_list(cm.get("outcomePrices"));ta,tb=None,None
  if tk and len(b)==2 and{b[0],b[1]}=={pa_n,pb_n}:ta,tb=(tk[0],tk[1])if b[0]==pa_n else(tk[1],tk[0])
  rw=None
  if len(a)==2 and len(b)==2:
   try:
    p0,p1=float(a[0]),float(a[1])
    if cm.get("closed")or(max(p0,p1)>=.995 and min(p0,p1)<=.005):
     if p0>=.995 and p1<=.005:rw="A"if b[0]==pa_n else"B"
     elif p1>=.995 and p0<=.005:rw="A"if b[1]==pa_n else"B"
   except(TypeError,ValueError):pass
  return ta,tb,rw
 for m in mkts:
  i=str(m.get("sportsMarketType")or"").strip().lower();h=str(m.get("groupItemTitle")or m.get("question")or"")
  if i=="tennis_first_set_winner":spec.set1_a_token,spec.set1_b_token,spec.set1_resolved_winner=_parse_set_winner(m);continue
  if i=="tennis_set_winner"and(str(m.get("line")or"")=="2"or"set 2"in h.lower()):spec.set2_a_token,spec.set2_b_token,spec.set2_resolved_winner=_parse_set_winner(m);continue
  if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
  tk=_parse_clob_tokens(m);f=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not tk or len(f)!=2:continue
  fr,fe=_extract_market_fee_rate(m)
  if i=="tennis_completed_match"and f==["yes","no"]:spec.comp_yes_token,spec.comp_no_token=tk[0],tk[1];spec.comp_market_id=str(m.get("id")or"");spec.comp_condition_id=str(m.get("conditionId")or"");spec.comp_fee_rate,spec.comp_fee_exp=fr,fe;spec.comp_neg_risk=bool(m.get("negRisk"))
  elif i=="tennis_set_totals"and m.get("line")is not None and abs(float(m.get("line"))-2.5)<1e-6:
   if f[0].startswith("over")and f[1].startswith("under"):spec.sets_ou25_over_token,spec.sets_ou25_under_token=tk[0],tk[1];spec.sets_ou25_market_id=str(m.get("id")or"");spec.sets_ou25_condition_id=str(m.get("conditionId")or"");spec.sets_ou25_fee_rate,spec.sets_ou25_fee_exp=fr,fe;spec.sets_ou25_neg_risk=bool(m.get("negRisk"))
  elif i in("tennis_first_set_totals","tennis_set_games_totals","tennis_match_totals")and m.get("line")is not None:
   ln=float(m.get("line"))
   if not _is_half_hook(ln)or not(f[0].startswith("over")and f[1].startswith("under")):continue
   if i=="tennis_first_set_totals":sc="SET1_GAMES"
   elif i=="tennis_match_totals":sc="MATCH_GAMES"
   elif"set 2"in h.lower():sc="SET2_GAMES"
   elif"set 3"in h.lower():sc="SET3_GAMES"
   else:continue
   spec.totals_by_scope.setdefault(sc,[]).append(TennisTotalRung(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),scope=sc,line=ln,over_token=tk[0],under_token=tk[1],fee_rate=fr,fee_exp=fe,neg_risk=bool(m.get("negRisk"))))
 for k in spec.totals_by_scope:spec.totals_by_scope[k].sort(key=lambda r:r.line)
 b=any(len(v)>=2 for v in spec.totals_by_scope.values());a=bool(spec.sets_ou25_over_token and spec.comp_no_token)
 if not(b or a):return None
 return spec
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
 def __init__(self):self._frozen_since={};self._race_latched={}
 def confirm_frozen_pair(self,sport,game_id,scope_key,away_pts,home_pts,period_ended,now_ts,freeze_confirm_sec=45.,instant_settled=False):
  c=(sport.upper(),str(game_id),scope_key)
  if not period_ended:self._frozen_since.pop(c,None);return None
  b=(int(away_pts),int(home_pts));a=self._frozen_since.get(c)
  if a is None or a[0]!=b:
   self._frozen_since[c]=(b,float(now_ts))
   if instant_settled or freeze_confirm_sec<=.0:return b
   return None
  if instant_settled or(float(now_ts)-a[1])>=freeze_confirm_sec:return b
  return None
 def observe_and_confirm_race_winner(self,sport,game_id,target_pts,away_score,home_score,now_ts,buffer_pts=3,confirm_sec=45.,is_final=False):
  g=(sport.upper(),str(game_id),int(target_pts));c=self._race_latched.get(g);b=int(target_pts)+(0 if is_final else int(buffer_pts))
  if c is not None:
   f,t0=c;e=away_score if f=="AWAY"else home_score;d=home_score if f=="AWAY"else away_score
   if e<b:self._race_latched.pop(g,None);return None
   a=float(now_ts)-t0
   if not is_final and a<confirm_sec and d>=int(target_pts):self._race_latched.pop(g,None);return None
   if is_final or a>=confirm_sec:return f
   return None
  if away_score>=b and home_score<int(target_pts):self._race_latched[g]=("AWAY",float(now_ts));return"AWAY"if(is_final or confirm_sec<=.0)else None
  if home_score>=b and away_score<int(target_pts):self._race_latched[g]=("HOME",float(now_ts));return"HOME"if(is_final or confirm_sec<=.0)else None
  return None
 def prune(self,now_ts,max_age_sec=21600.):
  cutoff=float(now_ts)-float(max_age_sec);b=[k for k,(_,t0)in self._frozen_since.items()if t0<cutoff]
  for k in b:del self._frozen_since[k]
  a=[k for k,(_,t0)in self._race_latched.items()if t0<cutoff]
  for k in a:del self._race_latched[k]
  return len(b)+len(a)
_AFFINE_SMT_MAP={"totals":("FG","TOTAL"),"spreads":("FG","SPREAD"),"moneyline":("FG","ML"),"first_half_totals":("1H","TOTAL"),"first_half_spreads":("1H","SPREAD"),"first_half_moneyline":("1H","ML"),"q1_totals":("Q1","TOTAL"),"q2_totals":("Q2","TOTAL"),"q3_totals":("Q3","TOTAL"),"q4_totals":("Q4","TOTAL"),"q1_spreads":("Q1","SPREAD"),"q2_spreads":("Q2","SPREAD"),"q3_spreads":("Q3","SPREAD"),"q4_spreads":("Q4","SPREAD"),"team_totals":("FG","TEAM_TOTAL"),"first_half_team_totals":("1H","TEAM_TOTAL"),"second_half_team_totals":("2H","TEAM_TOTAL")};_RACE_PTS_RE=re.compile(r"race\s+to\s+(\d+)\s+points",re.IGNORECASE)
def _canon_sport_team(sport,raw):return _canon_nba_team(raw)if sport.upper()=="NBA"else _norm_team(raw)
def parse_affine_game_bundle(events,now_ts=None):
 g={}
 for ev in events or[]:
  if not isinstance(ev,dict)or ev.get("closed")or ev.get("archived"):continue
  slug=str(ev.get("slug")or"").lower()
  if not slug.startswith(("nba-","nfl-","cfb-")):continue
  if any(slug.endswith(s)for s in("-exact-margin","-player-props","-halftime-result")):continue
  base_slug=re.sub(r"-more-markets$","",slug);g.setdefault(base_slug,[]).append(ev)
 z=[]
 for base_slug,ev_list in g.items():
  O="NBA"if base_slug.startswith("nba-")else("NFL"if base_slug.startswith("nfl-")else"CFB");y=next((e for e in ev_list if str(e.get("slug")or"").lower()==base_slug),ev_list[0]);N=re.sub(r"\s*-\s*More Markets\s*$","",str(y.get("title")or""),flags=re.I).strip();M=re.split(r"\s+(?:vs\.?|@)\s+",N,maxsplit=1,flags=re.IGNORECASE)
  if len(M)!=2:continue
  H=_canon_sport_team(O,M[0]);G=_canon_sport_team(O,M[1])
  if not H or not G or H==G:continue
  F=_parse_iso_ts(y.get("startTime")or y.get("gameStartTime")or y.get("endDate"))or.0
  if F<=.0 or(now_ts is not None and F<now_ts-8.*3600.):continue
  p=F+(3.25 if O=="NBA"else 3.75)*3600.;L=str(y.get("id")or"");f=[];a=None;x=[];n=set()
  for ev in ev_list:
   for m in ev.get("markets")or[]:
    V=str(m.get("id")or"")
    if not V or V in n or m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
    n.add(V);R=_parse_clob_tokens(m);outs=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))]
    if not R or len(outs)!=2:continue
    fr,fe=_extract_market_fee_rate(m);U=str(m.get("sportsMarketType")or"").strip().lower();K=str(m.get("groupItemTitle")or m.get("question")or"").strip();E=str(m.get("question")or K).strip();T=str(m.get("conditionId")or"");nr=bool(m.get("negRisk"))
    if U=="basketball_game_overtime"or("overtime"in E.lower()and[o.lower()for o in outs]==["yes","no"]):
     if re.search(r"\b(?:double|triple|2\+|3\+|first\s+half|1h|2h)\b",E,re.IGNORECASE):continue
     a={"market_id":V,"condition_id":T,"token_id":R[0],"opp_token_id":R[1],"side":"YES","label":"YES[Overtime]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":p,"strike":.5};continue
    if U in("basketball_team_to_score_first","basketball_game_race_to_points"):
     if re.search(r"\b(?:1q|2q|3q|4q|q1|q2|q3|q4|quarter|half|1h|2h)\b",f"{E} {K}",re.IGNORECASE):continue
     c0,c1=_canon_sport_team(O,outs[0]),_canon_sport_team(O,outs[1])
     if{c0,c1}=={H,G}:
      D=1;C="FIRST_SCORE"
      if U=="basketball_game_race_to_points":
       Q=_RACE_PTS_RE.search(E)
       if not Q:continue
       D=int(Q.group(1));C="RACE_TO_X"
      if c0==H:v,u,t,r=R[0],R[1],outs[0],outs[1]
      else:v,u,t,r=R[1],R[0],outs[1],outs[0]
      x.append(FirstPassageMarketSpec(event_id=L,market_id=V,condition_id=T,kind=C,target_pts=D,away_token=v,home_token=u,away_label=t,home_label=r,fee_rate=fr,fee_exponent=fe,settle_est_ts=F+.85*3600.,neg_risk=nr))
     continue
    if U not in _AFFINE_SMT_MAP:continue
    w,P=_AFFINE_SMT_MAP[U];J={"Q1":.75,"Q2":1.35,"1H":1.35,"Q3":2.15}.get(w,3.25 if O=="NBA"else 3.75)*3600.;q=F+J
    if P=="ML":
     c0,c1=_canon_sport_team(O,outs[0]),_canon_sport_team(O,outs[1])
     if{c0,c1}=={H,G}:f.append(NbaSubperiodMarketSpec(L,V,T,w,"ML",.0,c0,R[0],R[1],outs[0],outs[1],fr,q,K or f"{w} ML",nr,fe))
    elif P=="SPREAD":
     d=m.get("line")
     if d is None:continue
     try:ln=abs(float(d))
     except(TypeError,ValueError):continue
     if not _is_half_hook(ln):continue
     c0,c1=_canon_sport_team(O,outs[0]),_canon_sport_team(O,outs[1])
     if{c0,c1}!={H,G}:continue
     I=_SPREAD_FAV_RE.search(E);b=None
     if I:
      B=_canon_sport_team(O,I.group(1));S=float(I.group(2))
      if B in(H,G):b=B if S<0 else(G if B==H else H)
     if b is None:continue
     if c0==b:l,k,j,i=R[0],R[1],outs[0],outs[1]
     else:l,k,j,i=R[1],R[0],outs[1],outs[0]
     f.append(NbaSubperiodMarketSpec(L,V,T,w,"SPREAD",ln,b,l,k,j,i,fr,q,f"{w} {j}(-{ln})/{i}(+{ln})",nr,fe))
    elif P in("TOTAL","TEAM_TOTAL"):
     d=m.get("line")
     if d is None:continue
     try:ln=float(d)
     except(TypeError,ValueError):continue
     if ln<=.0 or not _is_half_hook(ln):continue
     if not(outs[0].lower().startswith("over")and outs[1].lower().startswith("under")):continue
     h=str(m.get("description")or"").lower()
     if w in("FG","2H")and("overtime is not included"in h or"excludes overtime"in h):continue
     c=None
     if P=="TEAM_TOTAL":
      A=E.split("O/U")[0];ca=H in _canon_sport_team(O,A)or _norm_team(M[0])in _norm_team(A);ch=G in _canon_sport_team(O,A)or _norm_team(M[1])in _norm_team(A)
      if ca==ch:continue
      c=H if ca else G
     f.append(NbaSubperiodMarketSpec(L,V,T,w,P,ln,c,R[0],R[1],"Over","Under",fr,q,K or f"{w} O/U {ln}",nr,fe))
  if f or x:z.append(AffineGameBundle(sport=O,event_id=L,slug=base_slug,title=N,tipoff_ts=F,settle_est_ts=p,away_team=H,home_team=G,markets=f,overtime_yes_leg=a,first_passage_markets=x))
 return z
def _leg_dict_from_subspec(sm,is_tok0,label_override=None):return{"token_id":sm.tok_0 if is_tok0 else sm.tok_1,"opp_token_id":sm.tok_1 if is_tok0 else sm.tok_0,"condition_id":sm.condition_id,"market_id":sm.market_id,"side":sm.out_0.upper()if is_tok0 else sm.out_1.upper(),"label":label_override or f"{sm.display_title}:{sm.out_0 if is_tok0 else sm.out_1}","fee_rate":sm.fee_rate,"fee_exponent":sm.fee_exponent,"neg_risk":bool(sm.neg_risk),"strike":float(sm.line or.0),"end_ts":sm.settle_est_ts}
def _spread_signed_legs(sm,away_team):
 ln=float(sm.line or.0)
 if ln<=.0:return[]
 if sm.team_side==away_team:return[("GT",+ln,_leg_dict_from_subspec(sm,True,f"{sm.period_scope} {sm.out_0}(-{ln})")),("LT",+ln,_leg_dict_from_subspec(sm,False,f"{sm.period_scope} {sm.out_1}(+{ln})"))]
 return[("LT",-ln,_leg_dict_from_subspec(sm,True,f"{sm.period_scope} {sm.out_0}(-{ln})")),("GT",-ln,_leg_dict_from_subspec(sm,False,f"{sm.period_scope} {sm.out_1}(+{ln})"))]
def evaluate_aff1_frozen_subperiod_opportunities(bundle,live_summary,best_asks,freeze_tracker,now_ts,espn_game_id="",freeze_confirm_sec=45.,max_2leg_cost_net=.992,max_3leg_cost_net=.99):
 two_leg_boxes=[];b=[];a=[];L=str(live_summary.get("state")or"pre").lower()
 if L not in("in","post"):return{"two_leg_boxes":two_leg_boxes,"three_leg_boxes":b,"single_leg_locks":a}
 j=bool(live_summary.get("completed")and L=="post");K=bool(live_summary.get("is_halftime"));E=int(live_summary.get("period")or 0);w=int(live_summary.get("away_score")or 0);v=int(live_summary.get("home_score")or 0);ls_a=(live_summary.get("linescores")or{}).get("away")or{};ls_h=(live_summary.get("linescores")or{}).get("home")or{};_g=espn_game_id or bundle.event_id
 def _try_2leg(mode,lg_a,lg_b,middle_width,desc):
  if lg_a["market_id"]==lg_b["market_id"]:return
  pa=best_asks.get(lg_a["token_id"]);pb=best_asks.get(lg_b["token_id"])
  if pa is None or pb is None or not(.005<=pa<=.99 and.005<=pb<=.99):return
  a=round(_net_unit_ask(float(pa),lg_a["fee_rate"],lg_a["fee_exponent"])+_net_unit_ask(float(pb),lg_b["fee_rate"],lg_b["fee_exponent"]),4)
  if a<=max_2leg_cost_net:two_leg_boxes.append({"mode":mode,"sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"box_cost_gross":round(float(pa)+float(pb),4),"box_cost_net":a,"middle_width":round(float(middle_width),1),"close_ts":max(float(lg_a["end_ts"]),float(lg_b["end_ts"])),"leg_a":lg_a,"leg_b":lg_b,"label":f"{bundle.title}: {desc}"})
 i=(1 in ls_a and 1 in ls_h)and(j or K or E>=2);u=freeze_tracker.confirm_frozen_pair(bundle.sport,_g,"Q1",int(ls_a.get(1,0)),int(ls_h.get(1,0)),period_ended=i,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=(j or K or E>=3))
 if u is not None and not K and E<=2 and not j:
  Y,X=u;W=float(Y+X);V=float(Y-X);U=[m for m in bundle.markets if m.period_scope=="1H"and m.kind=="TOTAL"and m.line is not None];T=[m for m in bundle.markets if m.period_scope=="Q2"and m.kind=="TOTAL"and m.line is not None]
  for m1 in U:
   S=float(m1.line);t=S-W
   for m2 in T:
    R=float(m2.line)
    if t<=R+1e-9:_try_2leg("AFF1_POST_Q1_1H_VS_Q2_TOTAL",_leg_dict_from_subspec(m1,True,f"1H O{S:g}"),_leg_dict_from_subspec(m2,False,f"Q2 U{R:g}"),R-t,f"1H O{S:g} + Q2 U{R:g} (Q1={int(W)} frozen)")
    if R<=t+1e-9:_try_2leg("AFF1_POST_Q1_1H_VS_Q2_TOTAL",_leg_dict_from_subspec(m1,False,f"1H U{S:g}"),_leg_dict_from_subspec(m2,True,f"Q2 O{R:g}"),t-R,f"1H U{S:g} + Q2 O{R:g} (Q1={int(W)} frozen)")
  J=[x for m in bundle.markets if m.period_scope=="1H"and m.kind=="SPREAD"for x in _spread_signed_legs(m,bundle.away_team)];I=[x for m in bundle.markets if m.period_scope=="Q2"and m.kind=="SPREAD"for x in _spread_signed_legs(m,bundle.away_team)]
  for _f,_e,_d in J:
   D=_e-V
   for _c,_b,_a in I:
    if _f=="GT"and _c=="LT"and D<=_b+1e-9:_try_2leg("AFF1_POST_Q1_1H_VS_Q2_SPREAD",_d,_a,_b-D,f"{_d['label']} + {_a['label']} (mQ1={V:+.0f})")
    elif _f=="LT"and _c=="GT"and _b<=D+1e-9:_try_2leg("AFF1_POST_Q1_1H_VS_Q2_SPREAD",_d,_a,D-_b,f"{_d['label']} + {_a['label']} (mQ1={V:+.0f})")
 if bundle.sport=="NBA":
  h=(1 in ls_a and 2 in ls_a and 1 in ls_h and 2 in ls_h)and(j or K or E>=3);s=freeze_tracker.confirm_frozen_pair(bundle.sport,_g,"1H",int(ls_a.get(1,0))+int(ls_a.get(2,0)),int(ls_h.get(1,0))+int(ls_h.get(2,0)),period_ended=h,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=(j or E>=4))
  if s is not None and not j:
   c={bundle.away_team:float(s[0]),bundle.home_team:float(s[1])}
   for tm,C in c.items():
    B=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TEAM_TOTAL"and m.team_side==tm and m.line is not None];A=[m for m in bundle.markets if m.period_scope=="2H"and m.kind=="TEAM_TOTAL"and m.team_side==tm and m.line is not None]
    for f in B:
     e=float(f.line);H=e-C
     for Q in A:
      P=float(Q.line)
      if H<=P+1e-9:_try_2leg("AFF1_HT_TEAM_TOTAL_FG_VS_2H",_leg_dict_from_subspec(f,True,f"FG {tm.title()} O{e:g}"),_leg_dict_from_subspec(Q,False,f"2H {tm.title()} U{P:g}"),P-H,f"{tm.title()} FG O{e:g} + 2H U{P:g} (1H={int(C)})")
      if P<=H+1e-9:_try_2leg("AFF1_HT_TEAM_TOTAL_FG_VS_2H",_leg_dict_from_subspec(f,False,f"FG {tm.title()} U{e:g}"),_leg_dict_from_subspec(Q,True,f"2H {tm.title()} O{P:g}"),H-P,f"{tm.title()} FG U{e:g} + 2H O{P:g} (1H={int(C)})")
 if bundle.sport=="NBA":
  g=all(q in ls_a and q in ls_h for q in(1,2,3))and(j or E>=4);r=freeze_tracker.confirm_frozen_pair(bundle.sport,_g,"Q1_Q3",int(ls_a.get(1,0))+int(ls_a.get(2,0))+int(ls_a.get(3,0)),int(ls_h.get(1,0))+int(ls_h.get(2,0))+int(ls_h.get(3,0)),period_ended=g,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=j)
  if r is not None and not j and E==4:
   G=float(r[0]+r[1]);p=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TOTAL"and m.line is not None];o=[m for m in bundle.markets if m.period_scope=="Q4"and m.kind=="TOTAL"and m.line is not None];z=bundle.overtime_yes_leg;F=best_asks.get(z["token_id"])if z is not None else None;O=_net_unit_ask(float(F),z["fee_rate"],z["fee_exponent"])if(z and F is not None)else None
   for f in p:
    e=float(f.line);y=e-G
    for N in o:
     M=float(N.line)
     if y<=M+1e-9:_try_2leg("AFF1_POST_Q3_FG_OVER_4Q_UNDER",_leg_dict_from_subspec(f,True,f"FG O{e:g}"),_leg_dict_from_subspec(N,False,f"4Q U{M:g}"),M-y,f"FG O{e:g} + 4Q U{M:g} (Q1..3={int(G)})")
     if M<=y+1e-9 and z is not None and F is not None and O is not None:
      n=_leg_dict_from_subspec(f,False,f"FG U{e:g}");l=_leg_dict_from_subspec(N,True,f"4Q O{M:g}");pu=best_asks.get(n["token_id"]);po=best_asks.get(l["token_id"])
      if(pu is not None and po is not None and.005<=float(pu)<=.99 and.005<=float(po)<=.99 and.005<=float(F)<=.99):
       c3=round(_net_unit_ask(float(pu),n["fee_rate"],n["fee_exponent"])+_net_unit_ask(float(po),l["fee_rate"],l["fee_exponent"])+O,4)
       if c3<=max_3leg_cost_net:b.append({"mode":"AFF1_POST_Q3_OT_IMMUNIZED_3LEG","sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"n_legs":3,"box_cost_gross":round(float(pu)+float(po)+float(F),4),"box_cost_net":c3,"middle_width":round(y-M,1),"close_ts":max(n["end_ts"],l["end_ts"],z["end_ts"]),"legs":[n,l,z],"label":f"{bundle.title}: FG U{e:g} + 4Q O{M:g} + YES[OT] (Q1..3={int(G)})"})
 for fp in bundle.first_passage_markets:
  Z=2 if fp.kind=="FIRST_SCORE"else 3;d=freeze_tracker.observe_and_confirm_race_winner(bundle.sport,_g,fp.target_pts,w,v,now_ts=now_ts,buffer_pts=Z,confirm_sec=freeze_confirm_sec,is_final=j)
  if d in("AWAY","HOME"):k=d=="AWAY";a.append({"mode":f"AFF1_{fp.kind}_LOCK","sport":bundle.sport,"event_id":bundle.event_id,"market_id":fp.market_id,"condition_id":fp.condition_id,"token_id":fp.away_token if k else fp.home_token,"opp_token_id":fp.home_token if k else fp.away_token,"side_label":fp.away_label if k else fp.home_label,"display_label":(f"{bundle.title} {'First Score'if fp.kind=='FIRST_SCORE'else f'Race to {fp.target_pts}'}: {fp.away_label if k else fp.home_label} [{w}-{v}]"),"fee_rate":fp.fee_rate,"fee_exponent":fp.fee_exponent,"neg_risk":fp.neg_risk,"p_lock":.998,"close_ts":fp.settle_est_ts})
 two_leg_boxes.sort(key=lambda x:float(x["box_cost_net"]));b.sort(key=lambda x:float(x["box_cost_net"]));return{"two_leg_boxes":two_leg_boxes,"three_leg_boxes":b,"single_leg_locks":a}
SOC2_GRID_MAX=8;SOC2_PLAYED_STATES=[(h,a)for h in range(SOC2_GRID_MAX+1)for a in range(SOC2_GRID_MAX+1)];SOC2_NUM_STATES=len(SOC2_PLAYED_STATES)+2;_EXACT_SCORE_ITEM_RE=re.compile(r"(\d+)\s*[-–:]\s*(\d+)");_SOC_ADV_VETO_RE=re.compile(r"(\badvance\b|\bqualify\b|\blift the trophy\b|\bincluding extra time\b|\bpenalties\b)",re.IGNORECASE)
@dataclass
class SoccerExactScoreLattice:game_key:str;game_id:str;title:str;end_ts:float;home_team:str;away_team:str;exact_event_id:str;exact_slug:str;exact_neg_risk_market_id:str;is_closed_37_slate:bool;score_brackets:Dict[Tuple[int,int],Dict[str,Any]];any_other_bracket:Optional[Dict[str,Any]];convert_spec:Optional[NegRiskConvertSlateSpec];matrix_legs=field(default_factory=list)
def _extract_soccer_slug_match_key(slug):
 s=re.sub(r"-(more-markets|exact-score|halftime-result|second-half-result|first-to-score)$","",slug.lower().strip())
 if re.search(r"-20\d{2}-\d{2}-\d{2}$",s):return s
 return None
def link_and_parse_soc2_exact_score_lattices(events,now_ts=None):
 X={};p={}
 for ev in events or[]:
  if not isinstance(ev,dict)or ev.get("closed")or ev.get("archived"):continue
  sl=str(ev.get("slug")or"").lower();W=str(ev.get("gameId")or"").strip();G=_extract_soccer_slug_match_key(sl)
  if W and G:p[G]=W
 for ev in events or[]:
  if not isinstance(ev,dict)or ev.get("closed")or ev.get("archived"):continue
  sl=str(ev.get("slug")or"").lower();W=str(ev.get("gameId")or"").strip();G=_extract_soccer_slug_match_key(sl);_r=W or(p.get(G)if G else None)or G
  if _r:X.setdefault(_r,[]).append(ev)
 F={}
 for _o,ev_list in X.items():
  E=next((e for e in ev_list if str(e.get("slug")or"").lower().endswith("-exact-score")),None)
  if E is None:continue
  O=next((e for e in ev_list if e.get("negRisk")and len(e.get("markets")or[])==3 and not str(e.get("slug")or"").lower().endswith(("-halftime-result","-second-half-result","-first-to-score","-exact-score"))),None);N=next((e for e in ev_list if str(e.get("slug")or"").lower().endswith("-more-markets")),None);z=re.sub(r"\s*-\s*Exact Score\s*$","",str(E.get("title")or""),flags=re.I).strip();M=re.split(r"\s+vs\.?\s+",z,maxsplit=1,flags=re.IGNORECASE)
  if len(M)!=2:continue
  D,C=M[0].strip(),M[1].strip();V,U=_norm_team(D),_norm_team(C)
  if not V or not U or V==U:continue
  T=_parse_iso_ts((O or E).get("startTime")or E.get("gameStartTime")or E.get("endDate"))or.0
  if T<=.0 or(now_ts is not None and T<now_ts-4.*3600.):continue
  y={};d=None;conv_brackets=[];n=[];c=True;L=E.get("markets")or[]
  for _g,m in enumerate(L):
   if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:c=False;continue
   q=str(m.get("question")or"");g=str(m.get("description")or"");S=str(m.get("groupItemTitle")or"").strip()
   if _SOC_ADV_VETO_RE.search(f"{q}\n{g}"):c=False;continue
   j=_parse_clob_tokens(m);outs=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
   if not j or outs!=["yes","no"]:c=False;continue
   fr,fe=_extract_market_fee_rate(m);_n=str(m.get("questionID")or"").strip().lower();_f=int(_n[64:],16)if(len(_n)==66 and _n.startswith("0x"))else _g;s,r=str(m.get("id")or""),str(m.get("conditionId")or"");B="other"in S.lower()or"any other"in q.lower();h_sc,a_sc=-1,-1
   if not B:
    _m=_EXACT_SCORE_ITEM_RE.search(S or q)
    if not _m:c=False;continue
    h_sc,a_sc=int(_m.group(1)),int(_m.group(2));A=_norm_team(S or q)
    if U in A and V in A:
     if A.find(U)<A.find(V):h_sc,a_sc=a_sc,h_sc
    elif U in A and V not in A and h_sc<a_sc:h_sc,a_sc=a_sc,h_sc
    elif V in A and U not in A and a_sc>h_sc:h_sc,a_sc=a_sc,h_sc
    if not(0<=h_sc<=5 and 0<=a_sc<=5):c=False;continue
   _e={"market_id":s,"condition_id":r,"question_index":_f,"label":"Any Other"if B else f"{h_sc}-{a_sc}","home_goals":h_sc,"away_goals":a_sc,"yes_token":j[0],"no_token":j[1],"fee_rate":fr,"fee_exponent":fe,"neg_risk":True};conv_brackets.append(_e)
   if B:d=_e;v_yes=[1. if max(h,a)>=6 else.0 for(h,a)in SOC2_PLAYED_STATES]+[.0,.0]
   else:y[(h_sc,a_sc)]=_e;_d=1. if(h_sc==0 and a_sc==0)else.0;v_yes=[1. if(h==h_sc and a==a_sc)else.0 for(h,a)in SOC2_PLAYED_STATES]+[_d,_d]
   _l=[1.-x for x in v_yes];_c=_e["label"];n.append({"market_id":s,"condition_id":r,"token_id":j[0],"opp_token_id":j[1],"side":"YES","label":f"CS_Y[{_c}]","fee_rate":fr,"fee_exponent":fe,"neg_risk":True,"end_ts":T,"payoff_vec":v_yes,"strike":float(max(0,h_sc+a_sc))});n.append({"market_id":s,"condition_id":r,"token_id":j[1],"opp_token_id":j[0],"side":"NO","label":f"CS_N[{_c}]","fee_rate":fr,"fee_exponent":fe,"neg_risk":True,"end_ts":T,"payoff_vec":_l,"strike":float(max(0,h_sc+a_sc))})
  if not y:continue
  k=(bool(E.get("negRisk"))and not bool(E.get("negRiskAugmented",False))and c and len(y)==36 and d is not None and len(conv_brackets)==37);w=str(E.get("negRiskMarketID")or"").strip().lower();f=None
  if k and w.startswith("0x")and len(w)==66:
   conv_brackets.sort(key=lambda b:int(b["question_index"]))
   if[int(b["question_index"])for b in conv_brackets]==list(range(37)):f=NegRiskConvertSlateSpec(event_id=str(E.get("id")or""),slug=str(E.get("slug")or""),title=z,neg_risk_market_id=w,neg_risk_augmented=False,total_market_count=37,is_closed_convert_safe=True,end_ts=T,brackets=conv_brackets)
  if O is not None:
   for m in O.get("markets")or[]:
    if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
    q=str(m.get("question")or"");g=str(m.get("description")or"");S=str(m.get("groupItemTitle")or"").strip()
    if _SOC_ADV_VETO_RE.search(f"{q}\n{g}\n{S}"):continue
    j=_parse_clob_tokens(m);outs=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
    if not j or outs!=["yes","no"]:continue
    fr,fe=_extract_market_fee_rate(m);s,r=str(m.get("id")or""),str(m.get("conditionId")or"")
    if"draw"in S.lower()or"end in a draw"in q.lower():v=[1. if h==a else.0 for(h,a)in SOC2_PLAYED_STATES]+[1.,.0];u=[1. if h!=a else.0 for(h,a)in SOC2_PLAYED_STATES]+[.0,.5];t="Draw"
    else:
     R=_teams_match_fuzzy(S,D);Q=_teams_match_fuzzy(S,C)
     if R and not Q:v=[1. if h>a else.0 for(h,a)in SOC2_PLAYED_STATES]+[.0,.0];u=[1. if h<=a else.0 for(h,a)in SOC2_PLAYED_STATES]+[1.,.5];t=D[:14]
     elif Q and not R:v=[1. if a>h else.0 for(h,a)in SOC2_PLAYED_STATES]+[.0,.0];u=[1. if a<=h else.0 for(h,a)in SOC2_PLAYED_STATES]+[1.,.5];t=C[:14]
     else:continue
    n.append({"market_id":s,"condition_id":r,"token_id":j[0],"opp_token_id":j[1],"side":"YES","label":f"ML_Y[{t}]","fee_rate":fr,"fee_exponent":fe,"neg_risk":True,"end_ts":T,"payoff_vec":v,"strike":.0});n.append({"market_id":s,"condition_id":r,"token_id":j[1],"opp_token_id":j[0],"side":"NO","label":f"ML_N[{t}]","fee_rate":fr,"fee_exponent":fe,"neg_risk":True,"end_ts":T,"payoff_vec":u,"strike":.0})
  if N is not None:
   for m in N.get("markets")or[]:
    if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
    j=_parse_clob_tokens(m);outs=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))]
    if not j or len(outs)!=2:continue
    _q=str(m.get("sportsMarketType")or"").strip().lower();P=str(m.get("question")or m.get("groupItemTitle")or"");g=str(m.get("description")or"")
    if _SOC_ADV_VETO_RE.search(f"{P}\n{g}"):continue
    fr,fe=_extract_market_fee_rate(m);s,r=str(m.get("id")or""),str(m.get("conditionId")or"");nr=bool(m.get("negRisk"))
    if _q=="totals"and m.get("line")is not None:
     ln=float(m["line"])
     if _is_half_hook(ln)and.5<=ln<=7.5 and outs[0].lower().startswith("over"):_k=[1. if(h+a)>ln else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];_j=[1. if(h+a)<ln else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];n.append({"market_id":s,"condition_id":r,"token_id":j[0],"opp_token_id":j[1],"side":"OVER","label":f"O[{ln:g} Goals]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":T,"payoff_vec":_k,"strike":ln});n.append({"market_id":s,"condition_id":r,"token_id":j[1],"opp_token_id":j[0],"side":"UNDER","label":f"U[{ln:g} Goals]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":T,"payoff_vec":_j,"strike":ln})
    elif _q=="both_teams_to_score"or"both teams to score"in P.lower():
     if[o.lower()for o in outs]==["yes","no"]:_i=[1. if(h>=1 and a>=1)else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];_h=[1. if(h==0 or a==0)else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];n.append({"market_id":s,"condition_id":r,"token_id":j[0],"opp_token_id":j[1],"side":"YES","label":"BTTS[Yes]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":T,"payoff_vec":_i,"strike":1.});n.append({"market_id":s,"condition_id":r,"token_id":j[1],"opp_token_id":j[0],"side":"NO","label":"BTTS[No]","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":T,"payoff_vec":_h,"strike":1.})
    elif _q=="spreads"and m.get("line")is not None:
     ln=abs(float(m["line"]))
     if _is_half_hook(ln)and.5<=ln<=5.5:
      _b=_SPREAD_FAV_RE.search(P)
      if _b:
       K=_b.group(1).strip();_p=float(_b.group(2));fav_is_home=_teams_match_fuzzy(K,D);l=_teams_match_fuzzy(K,C)
       if fav_is_home!=l:
        if _p>0:fav_is_home=not fav_is_home
        J=_teams_match_fuzzy(outs[0],D);I,H=(j[0],j[1])if(J==fav_is_home)else(j[1],j[0]);v_fav=[1. if((h-a)>ln if fav_is_home else(a-h)>ln)else.0 for(h,a)in SOC2_PLAYED_STATES]+[.5,.5];_a=[1.-x if i<len(SOC2_PLAYED_STATES)else.5 for i,x in enumerate(v_fav)];Z=D[:10]if fav_is_home else C[:10];Y=C[:10]if fav_is_home else D[:10];n.append({"market_id":s,"condition_id":r,"token_id":I,"opp_token_id":H,"side":"SPREAD","label":f"{Z}(-{ln:g})","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":T,"payoff_vec":v_fav,"strike":-ln});n.append({"market_id":s,"condition_id":r,"token_id":H,"opp_token_id":I,"side":"SPREAD","label":f"{Y}(+{ln:g})","fee_rate":fr,"fee_exponent":fe,"neg_risk":nr,"end_ts":T,"payoff_vec":_a,"strike":ln})
  F[_o]=SoccerExactScoreLattice(game_key=_o,game_id=str(E.get("gameId")or(O or{}).get("gameId")or _o),title=z,end_ts=T,home_team=D,away_team=C,exact_event_id=str(E.get("id")or""),exact_slug=str(E.get("slug")or""),exact_neg_risk_market_id=w,is_closed_37_slate=k,score_brackets=y,any_other_bracket=d,convert_spec=f,matrix_legs=n)
 return F
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
 for(bh,ba),br in lattice.score_brackets.items():
  i=(bh!=n or ba!=m)if c else(bh<n or ba<m)
  if not i:continue
  if(bh==0 and ba==0)and not c:continue
  l.append({"mode":"SOC2_FINAL_EXACT_SCORE_NO_LOCK"if c else"SOC2_LIVE_DEAD_SCORE_NO_LOCK","game_key":lattice.game_key,"market_id":br["market_id"],"condition_id":br["condition_id"],"token_id":br["no_token"],"opp_token_id":br["yes_token"],"side_label":f"NO[{bh}-{ba}]","display_label":f"{lattice.title} NO[{bh}-{ba}] [Confirmed {n}-{m}{' FT'if c else' post-VAR'}]","fee_rate":br["fee_rate"],"fee_exponent":br["fee_exponent"],"neg_risk":True,"p_lock":.999,"close_ts":lattice.end_ts+7200.})
 if(n>=6 or m>=6)and lattice.any_other_bracket is not None and c:ao=lattice.any_other_bracket;l.append({"mode":"SOC2_ANY_OTHER_SCORE_YES_LOCK","game_key":lattice.game_key,"market_id":ao["market_id"],"condition_id":ao["condition_id"],"token_id":ao["yes_token"],"opp_token_id":ao["no_token"],"side_label":"YES[Any Other]","display_label":f"{lattice.title} YES[Any Other Score] [FT {n}-{m}]","fee_rate":ao["fee_rate"],"fee_exponent":ao["fee_exponent"],"neg_risk":True,"p_lock":.999,"close_ts":lattice.end_ts+7200.})
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
   mt=c.search(d)
   if mt:
    b=mt.group(1).strip()
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
  fr,fe=_extract_market_fee_rate(m);q=_extract_nfl_prop_player(m);u=canon_player_name(q)
  if not u:continue
  if y in("anytime_touchdowns","two_plus_touchdowns")and v==["yes","no"]:
   e=f"{m.get('question')or''} {m.get('groupItemTitle')or''}"
   if re.search(r"\b(?:first|last|1st\s+td|1st\s+touchdown|1h|2h|first\s+half|second\s+half|1q|2q|3q|4q|quarter)\b",e,re.IGNORECASE):continue
   d=str(m.get("description")or"").lower();c=bool("50-50"not in d and"void"not in d and re.search(r'not\s+play[^.]*resolve[s]?\s+to\s+"?no"?',d));l=y=="anytime_touchdowns";rg=NflPlayerPropRung(event_id=s,event_slug=x,game_title=g,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),player_name=q,player_key=u,stat_type="anytime_td"if l else"two_plus_td",line=.5 if l else 1.5,yes_over_token=w[0],no_under_token=w[1],fee_rate=fr,fee_exponent=fe,kickoff_ts=i,settle_est_ts=f,home_team=n,away_team=p,dnp_resolves_no=c)
   if l:b[u]=rg
   else:a[u]=rg
   continue
  if y in _NFL_ALLOWED_OU_SMTS and(v==["over","under"]or v==["yes","no"]):
   j=m.get("line")
   if j is None:continue
   try:ln=float(j)
   except(TypeError,ValueError):continue
   if ln<.5 or not _is_half_hook(ln):continue
   h.setdefault((u,y),[]).append(NflPlayerPropRung(event_id=s,event_slug=x,game_title=g,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),player_name=q,player_key=u,stat_type=y,line=ln,yes_over_token=w[0],no_under_token=w[1],fee_rate=fr,fee_exponent=fe,kickoff_ts=i,settle_est_ts=f,home_team=n,away_team=p))
 for k in h:h[k].sort(key=lambda r:r.line)
 if not b and not a and not h:return None
 return NflPlayerPropSlate(event_id=s,slug=x,title=g,kickoff_ts=i,settle_est_ts=f,home_team=n,away_team=p,anytime_td_by_player=b,two_plus_td_by_player=a,ladders_by_player_stat=h)
def detect_nfl_prp1_boxes(slate,best_asks,max_box_cost_net=.992):
 k=[]
 for h,e in slate.anytime_td_by_player.items():
  d=slate.two_plus_td_by_player.get(h)
  if d is None or e.market_id==d.market_id or e.dnp_resolves_no!=d.dnp_resolves_no:continue
  pa=best_asks.get(e.yes_over_token);pb=best_asks.get(d.no_under_token)
  if pa is None or pb is None or not(.01<=pa<=.99 and.01<=pb<=.99):continue
  a=round(_net_unit_ask(float(pa),e.fee_rate,e.fee_exponent)+_net_unit_ask(float(pb),d.fee_rate,d.fee_exponent),4)
  if a<=max_box_cost_net:k.append({"mode":"NFL_PRP1_TD_POLISH_MIDDLE","event_id":slate.event_id,"slug":slate.slug,"title":slate.title,"player_name":e.player_name,"box_cost_gross":round(float(pa)+float(pb),4),"box_cost_net":a,"close_ts":slate.settle_est_ts,"leg_a":{"token_id":e.yes_over_token,"opp_token_id":e.no_under_token,"condition_id":e.condition_id,"market_id":e.market_id,"side":"YES","label":f"{e.player_name} Anytime TD","fee_rate":e.fee_rate,"fee_exponent":e.fee_exponent,"neg_risk":False,"strike":.5,"end_ts":slate.settle_est_ts},"leg_b":{"token_id":d.no_under_token,"opp_token_id":d.yes_over_token,"condition_id":d.condition_id,"market_id":d.market_id,"side":"NO","label":f"{d.player_name} NO 2+ TDs","fee_rate":d.fee_rate,"fee_exponent":d.fee_exponent,"neg_risk":False,"strike":1.5,"end_ts":slate.settle_est_ts},"label":f"{e.player_name}: YES(Anytime TD) + NO(2+ TDs)"})
 for(_,b),c in slate.ladders_by_player_stat.items():
  for i in range(len(c)):
   g=c[i];pa=best_asks.get(g.yes_over_token)
   if pa is None or not(.02<=pa<=.98):continue
   for j in range(i+1,len(c)):
    f=c[j]
    if f.line<=g.line+.1 or g.market_id==f.market_id:continue
    pb=best_asks.get(f.no_under_token)
    if pb is None or not(.02<=pb<=.98):continue
    a=round(_net_unit_ask(float(pa),g.fee_rate,g.fee_exponent)+_net_unit_ask(float(pb),f.fee_rate,f.fee_exponent),4)
    if a<=max_box_cost_net:k.append({"mode":"NFL_PRP1_STAT_CORRIDOR","event_id":slate.event_id,"slug":slate.slug,"title":slate.title,"player_name":g.player_name,"stat_type":b,"box_cost_gross":round(float(pa)+float(pb),4),"box_cost_net":a,"close_ts":slate.settle_est_ts,"leg_a":{"token_id":g.yes_over_token,"opp_token_id":g.no_under_token,"condition_id":g.condition_id,"market_id":g.market_id,"side":"OVER","label":f"{g.player_name} {b} O{g.line:g}","fee_rate":g.fee_rate,"fee_exponent":g.fee_exponent,"neg_risk":False,"strike":g.line,"end_ts":slate.settle_est_ts},"leg_b":{"token_id":f.no_under_token,"opp_token_id":f.yes_over_token,"condition_id":f.condition_id,"market_id":f.market_id,"side":"UNDER","label":f"{f.player_name} {b} U{f.line:g}","fee_rate":f.fee_rate,"fee_exponent":f.fee_exponent,"neg_risk":False,"strike":f.line,"end_ts":slate.settle_est_ts},"label":f"{g.player_name} {b} O{g.line:g} + U{f.line:g}"})
 k.sort(key=lambda x:float(x["box_cost_net"]));return k
def parse_espn_nfl_summary(summary_json):
 players={};dnp_candidates=[];teams_with_active=set()
 for f in((summary_json or{}).get("boxscore")or{}).get("players")or[]:
  n=str((f.get("team")or{}).get("id")or"")
  for stat_blk in f.get("statistics")or[]:
   z=str(stat_blk.get("name")or"").lower();keys=[str(k)for k in(stat_blk.get("keys")or stat_blk.get("labels")or[])]
   for ath in stat_blk.get("athletes")or[]:
    r=canon_player_name(str((ath.get("athlete")or{}).get("displayName")or""))
    if not r:continue
    if ath.get("didNotPlay"):dnp_candidates.append((n,r));continue
    arr=[str(x)for x in(ath.get("stats")or[])]
    if not arr:continue
    teams_with_active.add(n);l=players.setdefault(r,{"rush_rec_tds":0})
    def _get_int(key_aliases):
     for a,kk in enumerate(keys):
      if kk in key_aliases and a<len(arr):
       try:return int(float(arr[a].strip()))
       except ValueError:return None
     return None
    if z=="passing":
     for idx_k,kk in enumerate(keys):
      if("completions"in kk or kk.upper()=="C/ATT")and idx_k<len(arr)and"/"in arr[idx_k]:
       y,w=arr[idx_k].split("/",1)
       try:l["passing_completions"]=int(y);l["passing_attempts"]=int(w)
       except ValueError:pass
     py=_get_int(("passingYards","YDS"));v=_get_int(("passingTouchdowns","TD"))
     if py is not None:l["passing_yards"]=py
     if v is not None:l["passing_touchdowns"]=v
    elif z=="rushing":
     ry=_get_int(("rushingYards","YDS"));u=_get_int(("rushingTouchdowns","TD"));lr=_get_int(("longRushing","LONG"))
     if ry is not None:l["rushing_yards"]=ry
     if lr is not None:l["longest_rush"]=lr
     if u is not None:l["rushing_tds"]=u
    elif z=="receiving":
     rc=_get_int(("receptions","REC"));t=_get_int(("receivingYards","YDS"));q=_get_int(("receivingTouchdowns","TD"));p=_get_int(("longReception","LONG"))
     if rc is not None:l["receptions"]=rc
     if t is not None:l["receiving_yards"]=t
     if p is not None:l["longest_reception"]=p
     if q is not None:l["receiving_tds"]=q
    elif z in("defensive","kickreturns","puntreturns","fumbles","interceptions"):
     s=_get_int(("defensiveTouchdowns","kickReturnTouchdowns","puntReturnTouchdowns","fumbleRecoveryTouchdowns","interceptionTouchdowns","touchdowns","TD"))
     if s is not None and s>0:l["non_off_tds"]=int(l.get("non_off_tds",0))+s
 for l in players.values():l["rush_rec_tds"]=int(l.get("rushing_tds",0))+int(l.get("receiving_tds",0));l["all_tds"]=int(l["rush_rec_tds"])+int(l.get("non_off_tds",0))
 b=[]
 for h in(summary_json or{}).get("scoringPlays")or[]:
  if not isinstance(h,dict):continue
  g=str(((h.get("scoringType")or{}).get("abbreviation")or(h.get("type")or{}).get("text")or"")).upper();j=str(h.get("text")or"")
  if"TD"in g or"TOUCHDOWN"in g or"touchdown"in j.lower():b.append(canon_player_name(j))
 d={pk for(tid,pk)in dnp_candidates if tid in teams_with_active and pk not in players};e,a,c,i="pre",False,0,"";m=((summary_json or{}).get("header")or{}).get("competitions")or[]
 if m:c0=m[0];i=str(c0.get("id")or"");st=c0.get("status")or{};o=st.get("type")or{};e=str(o.get("state")or"pre").lower();a=bool(o.get("completed"));c=int(st.get("period")or 0)
 return{"game_id":i,"state":e,"completed":a,"period":c,"players":players,"inactive_players":d,"td_scoring_texts":b}
def fetch_espn_nfl_summary_sync(espn_game_id,timeout=5.):c=ESPN_NFL_SUMMARY_URL.format(game_id=espn_game_id);b=urllib.request.Request(c,headers={"User-Agent":"DominusSportsOracle/1.0"});a=json.loads(urllib.request.urlopen(b,timeout=timeout).read().decode("utf-8"));return parse_espn_nfl_summary(a)
def evaluate_nfl_prp1_live_locks(slate,nfl_summary,tracker,now_ts,play_confirm_sec=240.,td_confirm_sec=180.):
 q=str(nfl_summary.get("state")or"pre").lower()
 if q not in("in","post"):return[]
 e=bool(nfl_summary.get("completed")and q=="post");s=str(nfl_summary.get("game_id")or slate.event_id);h=nfl_summary.get("players")or{};c=set(nfl_summary.get("inactive_players")or set());td_texts=list(nfl_summary.get("td_scoring_texts")or[]);p=[]
 for m,g,r in((slate.anytime_td_by_player,1,"Anytime TD"),(slate.two_plus_td_by_player,2,"2+ TDs")):
  for pkey,rg in m.items():
   a=h.get(pkey)
   if a is not None:
    f=int(a.get("all_tds",a.get("rush_rec_tds",0)));d=tracker.observe_and_confirmed_floor("NFL",s,f"TD:{pkey}",f,now_ts,td_confirm_sec,is_final=e)
    if d>=g:p.append({"mode":"NFL_PRP1_TD_CLINCH_LOCK","market_id":rg.market_id,"condition_id":rg.condition_id,"token_id":rg.yes_over_token,"opp_token_id":rg.no_under_token,"side_label":"YES","display_label":f"{rg.player_name} {r} YES [Confirmed TDs={d}]","fee_rate":rg.fee_rate,"fee_exponent":rg.fee_exponent,"neg_risk":False,"p_lock":.999 if e else.998,"close_ts":rg.settle_est_ts})
    elif e and f<g:
     if any(pkey in blob for blob in td_texts):continue
     p.append({"mode":"NFL_PRP1_FINAL_TD_NO_LOCK","market_id":rg.market_id,"condition_id":rg.condition_id,"token_id":rg.no_under_token,"opp_token_id":rg.yes_over_token,"side_label":"NO","display_label":f"{rg.player_name} {r} NO [Final TDs={f}]","fee_rate":rg.fee_rate,"fee_exponent":rg.fee_exponent,"neg_risk":False,"p_lock":.999,"close_ts":rg.settle_est_ts})
   elif pkey in c and e and rg.dnp_resolves_no:p.append({"mode":"NFL_PRP1_INACTIVE_DNP_NO_LOCK","market_id":rg.market_id,"condition_id":rg.condition_id,"token_id":rg.no_under_token,"opp_token_id":rg.yes_over_token,"side_label":"NO","display_label":f"{rg.player_name} {r} NO [Official Final DNP->No]","fee_rate":rg.fee_rate,"fee_exponent":rg.fee_exponent,"neg_risk":False,"p_lock":.998,"close_ts":rg.settle_est_ts})
 for(pkey,l),o in slate.ladders_by_player_stat.items():
  a=h.get(pkey)
  if not a or l not in a:continue
  n=int(a[l])
  if l in("longest_reception","longest_rush","receptions","passing_completions","passing_attempts","passing_touchdowns"):
   k=td_confirm_sec if l=="passing_touchdowns"else play_confirm_sec;j=tracker.observe_and_confirmed_floor("NFL",s,f"{l}:{pkey}",n,now_ts,k,is_final=e);b=1 if(e or l=="passing_touchdowns")else 2
   for rg in o:
    if j>=int(math.floor(rg.line))+b:p.append({"mode":"NFL_PRP1_MAX_PLAY_LOCK"if l.startswith("longest_")else"NFL_PRP1_COUNTER_LOCK","market_id":rg.market_id,"condition_id":rg.condition_id,"token_id":rg.yes_over_token,"opp_token_id":rg.no_under_token,"side_label":"OVER","display_label":f"{rg.player_name} {l} O{rg.line:g} [Confirmed={j}]","fee_rate":rg.fee_rate,"fee_exponent":rg.fee_exponent,"neg_risk":False,"p_lock":.999 if e else.998,"close_ts":rg.settle_est_ts})
    elif e and n<=int(math.floor(rg.line))-1:p.append({"mode":"NFL_PRP1_FINAL_UNDER_LOCK","market_id":rg.market_id,"condition_id":rg.condition_id,"token_id":rg.no_under_token,"opp_token_id":rg.yes_over_token,"side_label":"UNDER","display_label":f"{rg.player_name} {l} U{rg.line:g} [Final={n}]","fee_rate":rg.fee_rate,"fee_exponent":rg.fee_exponent,"neg_risk":False,"p_lock":.999,"close_ts":rg.settle_est_ts})
  elif e and l in("passing_yards","rushing_yards","receiving_yards"):
   for rg in o:
    if abs(float(n)-rg.line)>=2.5:i=float(n)>rg.line;p.append({"mode":"NFL_PRP1_FINAL_YARDAGE_LOCK","market_id":rg.market_id,"condition_id":rg.condition_id,"token_id":rg.yes_over_token if i else rg.no_under_token,"opp_token_id":rg.no_under_token if i else rg.yes_over_token,"side_label":"OVER"if i else"UNDER","display_label":f"{rg.player_name} {l} {'O'if i else'U'}{rg.line:g} [Final={n}]","fee_rate":rg.fee_rate,"fee_exponent":rg.fee_exponent,"neg_risk":False,"p_lock":.998,"close_ts":rg.settle_est_ts})
 return p
def detect_sum1_frechet_triangles(bundle,best_asks,max_3leg_cost_net=.99):
 b=[];d=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TEAM_TOTAL"and m.team_side==bundle.away_team and m.line is not None];c=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TEAM_TOTAL"and m.team_side==bundle.home_team and m.line is not None];u=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TOTAL"and m.line is not None]
 if d and c and u:b.append(("SUM1_AWAY_HOME_FG_TOTAL",d,c,u))
 t=[m for m in bundle.markets if m.period_scope=="Q1"and m.kind=="TOTAL"and m.line is not None];s=[m for m in bundle.markets if m.period_scope=="Q2"and m.kind=="TOTAL"and m.line is not None];r=[m for m in bundle.markets if m.period_scope=="1H"and m.kind=="TOTAL"and m.line is not None]
 if t and s and r:b.append(("SUM1_Q1_Q2_1H_TOTAL",t,s,r))
 if bundle.sport=="NBA":
  for tm in(bundle.away_team,bundle.home_team):
   n=[m for m in bundle.markets if m.period_scope=="1H"and m.kind=="TEAM_TOTAL"and m.team_side==tm and m.line is not None];l=[m for m in bundle.markets if m.period_scope=="2H"and m.kind=="TEAM_TOTAL"and m.team_side==tm and m.line is not None];k=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TEAM_TOTAL"and m.team_side==tm and m.line is not None]
   if n and l and k:b.append((f"SUM1_1H_2H_FG_TEAM_{tm.upper()[:8]}",n,l,k))
 q=[]
 for a,xs,ys,zs in b:
  for mx in xs:
   kx=float(mx.line);nx=int(math.floor(kx));j=best_asks.get(mx.tok_0);i=best_asks.get(mx.tok_1)
   for my in ys:
    if mx.market_id==my.market_id:continue
    ky=float(my.line);ny=int(math.floor(ky));h=best_asks.get(my.tok_0);g=best_asks.get(my.tok_1)
    for mz in zs:
     if mz.market_id in(mx.market_id,my.market_id):continue
     kz=float(mz.line);nz=int(math.floor(kz));f=best_asks.get(mz.tok_0);e=best_asks.get(mz.tok_1)
     if nz>=nx+ny and j is not None and h is not None and e is not None:
      p=round(_net_unit_ask(float(j),mx.fee_rate,mx.fee_exponent)+_net_unit_ask(float(h),my.fee_rate,my.fee_exponent)+_net_unit_ask(float(e),mz.fee_rate,mz.fee_exponent),4)
      if p<=max_3leg_cost_net:lx=_leg_dict_from_subspec(mx,True);ly=_leg_dict_from_subspec(my,True);lz=_leg_dict_from_subspec(mz,False);q.append({"mode":f"{a}_UPPER","sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"n_legs":3,"box_cost_gross":round(float(j)+float(h)+float(e),4),"box_cost_net":p,"close_ts":max(lx["end_ts"],ly["end_ts"],lz["end_ts"]),"legs":[lx,ly,lz],"label":f"{bundle.title}: {lx['label']} + {ly['label']} + {lz['label']}"})
     if nz<=nx+ny+1 and i is not None and g is not None and f is not None:
      o=round(_net_unit_ask(float(i),mx.fee_rate,mx.fee_exponent)+_net_unit_ask(float(g),my.fee_rate,my.fee_exponent)+_net_unit_ask(float(f),mz.fee_rate,mz.fee_exponent),4)
      if o<=max_3leg_cost_net:lx=_leg_dict_from_subspec(mx,False);ly=_leg_dict_from_subspec(my,False);lz=_leg_dict_from_subspec(mz,True);q.append({"mode":f"{a}_LOWER","sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"n_legs":3,"box_cost_gross":round(float(i)+float(g)+float(f),4),"box_cost_net":o,"close_ts":max(lx["end_ts"],ly["end_ts"],lz["end_ts"]),"legs":[lx,ly,lz],"label":f"{bundle.title}: {lx['label']} + {ly['label']} + {lz['label']}"})
 q.sort(key=lambda x:float(x["box_cost_net"]));return q
@dataclass
class CryptoCloseRungSpec:event_id:str;slug:str;asset:str;market_id:str;condition_id:str;question:str;strike:float;direction:str;close_ts:float;yes_token:str;no_token:str;fee_rate:float;fee_exponent:float
_CRYPTO_SLUG_ASSET_MAP=(("bitcoin-","BTC"),("btc-","BTC"),("ethereum-","ETH"),("eth-","ETH"),("solana-","SOL"),("sol-","SOL"),("xrp-","XRP"),("bnb-","BNB"),("dogecoin-","DOGE"),("doge-","DOGE"))
def parse_binance_terminal_close_event(ev):
 if ev.get("closed")or ev.get("archived"):return[]
 slug=str(ev.get("slug")or"").lower()
 if any(w in slug for w in("hit-price","up-or-down","updown","5m","15m")):return[]
 e=next((sym for pref,sym in _CRYPTO_SLUG_ASSET_MAP if slug.startswith(pref)),"")
 if not e:return[]
 c=_parse_iso_ts(ev.get("endDate"))or.0
 if c<=.0:return[]
 i=[]
 for m in ev.get("markets")or[]:
  if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
  q=str(m.get("question")or"");gl=str(m.get("groupItemTitle")or"");h=str(m.get("description")or ev.get("description")or"").lower()
  if"binance"not in h or"chain.link"in h or"pyth.network"in h:continue
  ql=q.lower()
  if any(w in ql for w in("reach","hit","touch","dip","between")):continue
  if not any(w in ql for w in("above","below","over","under","greater than","less than")):continue
  if re.search(r"\d[\d,]*\s*[-–to]+\s*\$?\d",gl):continue
  a="DOWN"if any(w in ql for w in("below","under","less than"))else"UP";b=parse_strike_from_text(q,gl);g=_parse_clob_tokens(m);f=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not b or b<=.0 or not g or f!=["yes","no"]:continue
  fr,fe=_extract_market_fee_rate(m);d=_parse_iso_ts(m.get("endDate"))or c;i.append(CryptoCloseRungSpec(event_id=str(ev.get("id")or""),slug=slug,asset=e,market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),question=q,strike=b,direction=a,close_ts=d,yes_token=g[0],no_token=g[1],fee_rate=fr,fee_exponent=fe))
 return i
def detect_cry_inc1_binance_inclusion_boxes(hit_rungs,close_rungs,best_asks,now_ts,max_box_cost_net=.992):
 d=[h for h in hit_rungs if h.resolved_yes is None and h.end_ts>now_ts+120. and h.asset!="HYPE"];l=[]
 for cr in close_rungs:
  if cr.close_ts<=now_ts+120. or cr.asset=="HYPE":continue
  k=best_asks.get(cr.no_token)
  if k is None or not(.01<=k<=.98):continue
  j=_net_unit_ask(float(k),cr.fee_rate,cr.fee_exponent)
  for hr in d:
   if hr.asset!=cr.asset or hr.direction!=cr.direction or hr.market_id==cr.market_id:continue
   if not(hr.start_ts<=now_ts and hr.start_ts<=cr.close_ts-60. and cr.close_ts<=hr.end_ts):continue
   a=(hr.strike<=cr.strike+1e-9)if cr.direction=="UP"else(hr.strike>=cr.strike-1e-9)
   if not a:continue
   f=best_asks.get(hr.yes_token)
   if f is None or not(.01<=f<=.98):continue
   c=round(j+_net_unit_ask(float(f),hr.fee_rate,hr.fee_exponent),4)
   if c<=max_box_cost_net:b="↑"if cr.direction=="UP"else"↓";l.append({"mode":"CRY_INC1_CLOSE_SUBSET_HIT","asset":cr.asset,"direction":cr.direction,"box_cost_gross":round(float(k)+float(f),4),"box_cost_net":c,"close_ts":max(cr.close_ts,hr.end_ts),"leg_a":{"token_id":cr.no_token,"opp_token_id":cr.yes_token,"condition_id":cr.condition_id,"market_id":cr.market_id,"side":"NO","label":f"NO[{cr.asset} Close {b}{cr.strike:g}]","fee_rate":cr.fee_rate,"fee_exponent":cr.fee_exponent,"neg_risk":False,"strike":cr.strike,"end_ts":cr.close_ts},"leg_b":{"token_id":hr.yes_token,"opp_token_id":hr.no_token,"condition_id":hr.condition_id,"market_id":hr.market_id,"side":"YES","label":f"YES[{cr.asset} {hr.horizon_group} Hit {b}{hr.strike:g}]","fee_rate":hr.fee_rate,"fee_exponent":hr.fee_exponent,"neg_risk":False,"strike":hr.strike,"end_ts":hr.end_ts},"label":f"{cr.asset} NO(Close {b}{cr.strike:g}) + YES({hr.horizon_group} Hit {b}{hr.strike:g})"})
 for hs in d:
  i=best_asks.get(hs.no_token)
  if i is None or not(.01<=i<=.98):continue
  g=_net_unit_ask(float(i),hs.fee_rate,hs.fee_exponent)
  for hl in d:
   if(hl.asset!=hs.asset or hl.direction!=hs.direction or hl.event_id==hs.event_id or hl.market_id==hs.market_id):continue
   if not(hl.start_ts<=hs.start_ts+1e-6 and hl.end_ts>=hs.end_ts+1800.):continue
   a=(hl.strike<=hs.strike+1e-9)if hs.direction=="UP"else(hl.strike>=hs.strike-1e-9)
   if not a:continue
   e=best_asks.get(hl.yes_token)
   if e is None or not(.01<=e<=.98):continue
   c=round(g+_net_unit_ask(float(e),hl.fee_rate,hl.fee_exponent),4)
   if c<=max_box_cost_net:b="↑"if hs.direction=="UP"else"↓";l.append({"mode":"CRY_INC1_SUBWINDOW_HIT_INCLUSION","asset":hs.asset,"direction":hs.direction,"box_cost_gross":round(float(i)+float(e),4),"box_cost_net":c,"close_ts":hl.end_ts,"leg_a":{"token_id":hs.no_token,"opp_token_id":hs.yes_token,"condition_id":hs.condition_id,"market_id":hs.market_id,"side":"NO","label":f"NO[{hs.asset} {hs.horizon_group} {b}{hs.strike:g}]","fee_rate":hs.fee_rate,"fee_exponent":hs.fee_exponent,"neg_risk":False,"strike":hs.strike,"end_ts":hs.end_ts},"leg_b":{"token_id":hl.yes_token,"opp_token_id":hl.no_token,"condition_id":hl.condition_id,"market_id":hl.market_id,"side":"YES","label":f"YES[{hl.asset} {hl.horizon_group} {b}{hl.strike:g}]","fee_rate":hl.fee_rate,"fee_exponent":hl.fee_exponent,"neg_risk":False,"strike":hl.strike,"end_ts":hl.end_ts},"label":f"{hs.asset} NO({hs.horizon_group} {b}{hs.strike:g}) + YES({hl.horizon_group} {b}{hl.strike:g})"})
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
from src.polymarket_research.barrier_onetouch_svi_engine import(ASSET_BINANCE_SYMBOL,BINANCE_FAPI_URL,HIT_SERIES,BarrierRungSpec,detect_barrier_monotonicity_boxes,evaluate_barrier_no_net_ev,fetch_binance_window_extremes_sync,first_passage_touch_prob,get_wing_implied_vol,parse_hit_event);from src.polymarket_research.multistrike_svi_scalper import(DAILY_UPDOWN_SERIES,NEGRISK_SERIES,STRIKE_SERIES,ZERO_FEE_PYTH_DAILY_SERIES,DailyUpDownSpec,NegRiskBracketSpec,StrikeRungSpec,_fast_norm_cdf,build_negrisk_cross_box_bundles,detect_ladder_monotonicity_boxes,evaluate_coherent_strike_ladder,evaluate_svi_digital_fair_value,parse_daily_updown_event,parse_multistrike_event,parse_negrisk_bracket_event);from src.polymarket_research.net_alpha_opportunity_engine import(publish_global_positions_shm,rank_opportunities_capital_auction,read_global_positions_shm,scan_binary_complete_set_arb);from src.polymarket_research.orderflow_wfo_simulators import(compute_d1_legging_drag_haircut,compute_d1_maker_anchor_drag_haircut);from src.polymarket_research.same_oracle_dominance_box import(DOMINANCE_ASSETS,DOMINANCE_SERIES_SLUGS,EMPIRICAL_BOX_ASSET_CAPS_USD,MIN_CORRIDOR_BPS_BY_ASSET,TwapCandleMarketSpec,build_crypto_price_query_url,build_own_gamma_event_url,build_prev_5m_gamma_event_url,determine_dominance_legs,parse_authoritative_close_price,parse_authoritative_open_price,parse_closed_gamma_event_settlement,parse_twap_candle_event,verify_same_oracle_pair,walk_equal_shares_dominance_box,walk_equal_shares_multi_leg_box);from src.polymarket_research.exact_twap_lock_engine import(compute_exact_twap_lock_probability,read_shm_usd_anchor)
try:from src.polymarket_research.polymarket_ws_streams import PolymarketChainlinkLiveStream
except ImportError:
 try:from polymarket_ws_streams import PolymarketChainlinkLiveStream
 except ImportError:PolymarketChainlinkLiveStream=None
from src.polymarket_research.weather_metar_engine import(HIGH_VOLUME_WEATHER_SERIES,MetarObservation,WeatherEventSpec,compute_adaptive_metar_poll_ttl,compute_weather_probabilities,evaluate_weather_event_slate,fetch_live_ensemble_hourly_sync,fetch_metar_observations_sync,fetch_taf_extremes_sync,parse_weather_event);from src.polymarket_research.tradfi_sports_zero_fee_engine import(MULTI_SPORT_CORRIDOR_SERIES,NBA_SERIES_SLUGS,PYTH_ASSET_CONFIG,PYTH_CLOSE_SERIES,PYTH_HIT_SERIES,ZERO_FEE_NEGRISK_SERIES,MultiSportCorridorSpec,NbaGameSpec,NegRiskConvertSlateSpec,PythBarrierRungSpec,PythCloseRungSpec,ZeroFeeNegRiskSlateSpec,compute_effective_trading_hours,detect_multi_sport_corridor_boxes,detect_nba_dominance_boxes,detect_negrisk_convert_positions_arbs,detect_negrisk_no_pair_boxes,detect_pyth_calendar_inclusion_boxes,detect_pyth_close_vs_hit_boxes,evaluate_pyth_session_barrier_no_lock,evaluate_pyth_session_close_lock,fetch_yahoo_1m_intraday_sync,is_same_continuous_session,parse_multi_sport_corridor_event,parse_nba_zero_fee_event,parse_negrisk_convert_event,parse_pyth_close_event,parse_pyth_hit_event,parse_zero_fee_negrisk_slate,window_extremes_from_bars,_extract_market_fee_rate,_parse_clob_tokens,_parse_iso_ts);from src.polymarket_research.macro_counting_ctf_engine import(ALL_FOMC_MASK,ALL_OIL_SENATE_MASK,COUNTING_SERIES_HANDLES,FOMC_PARLAY_SERIES,GAS_SERIES_SLUGS,HOURLY_BINANCE_SERIES,NY_TZ,OIL_SENATE_SLUGS,CountingSlateSpec,build_fomc_truth_table_legs,build_oil_senate_truth_table_legs,detect_counting_subwindow_boxes,detect_d2_12pm_binance_boxes,evaluate_counting_dead_no_locks,evaluate_locked_market_reward_carry,evaluate_pyth_catalyst_shock,fetch_aaa_national_gas_sync,fetch_xtracker_user_stats_sync,find_cross_event_bitmask_boxes,parse_counting_slate_event,parse_gas_daily_bracket,walk_equal_shares_overround_bids,walk_position_overround_bid_unwind);from src.polymarket_research.uma_nba_endgame_engine import(LiveNbaGameState,evaluate_nba_endgame_locks,fetch_espn_nba_scoreboard_sync,is_objective_uma_market,match_nba_live_game,verify_uma_against_nba_live,verify_uma_onchain_proposal_sync);from src.polymarket_research.riskless_frontier_v2_engine import(BOP_2026_SLUGS,EsportsBo3Spec,NbaPlayerPropSlate,SoccerRegulationTree,build_lp1_bop_2026_truth_legs,build_lp1_nba_exact_margin_bundle,detect_nr2_convert_no_subset_arbs,detect_soc1_regulation_boxes,detect_sp4_milestone_ladder_boxes,evaluate_api1_esports_bo3_opportunities,evaluate_sp4_ingame_clinch_locks,fetch_espn_nba_boxscore_players_sync,find_state_matrix_dominance_boxes,link_and_parse_soccer_regulation_trees,parse_esports_bo3_event,parse_nba_player_props_from_event,verify_bond2_moov2_final_hour_sync,verify_negrisk_adapter_slate_sync);from src.polymarket_research.riskless_frontier_v3_engine import(LP2_MIDTERM_CORE_SLUGS,LP2_TOSSUP_CUBE_SLUG,LP2_TOSSUP_STATE_SLUGS,CalendarOrScalarLadderSpec,LiveMultiSportGame,NbaSubperiodAndExtPropSlate,ScoreConfirmationTracker,TennisMatchSpec,build_lp1_nfl_exact_margin_bundle,build_lp2_house_seats_truth_legs,build_lp2_pending_senate_conditional_groups,build_lp2_senate_seats_truth_legs,build_lp2_tossup_state_implication_groups,detect_cal1_monotonic_boxes,detect_lp2_seat_convert_implication_arbs,detect_multisport_ml_spread_polish_middles,detect_sp4_subperiod_and_ext_prop_boxes,evaluate_cl1_multisport_corridor_clinch_locks,evaluate_cl1_soccer_tree_clinch_locks,evaluate_sp4_subperiod_and_ext_locks,evaluate_ten1_tennis_opportunities,fetch_espn_multisport_board_sync,fetch_espn_nba_full_summary_sync,parse_cal1_monotonic_ladder_event,parse_nba_subperiod_and_ext_props,parse_tennis_retirement_safe_event,_teams_match_fuzzy);from src.polymarket_research.riskless_frontier_v4_engine import(FRONTIER_V4_GRAD8_SLEEVES,AffineGameBundle,CryptoCloseRungSpec,NflPlayerPropSlate,SoccerExactScoreLattice,SubperiodFreezeTracker,detect_cry_inc1_binance_inclusion_boxes,detect_nfl_prp1_boxes,detect_soc2_lattice_boxes_and_converts,detect_sum1_frechet_triangles,evaluate_aff1_frozen_subperiod_opportunities,evaluate_mkr_lock1_post_clinch_rebate_bid,evaluate_nfl_prp1_live_locks,evaluate_soc2_dead_score_no_locks,fetch_espn_nfl_summary_sync,link_and_parse_soc2_exact_score_lattices,parse_affine_game_bundle,parse_binance_terminal_close_event,parse_nfl_player_props_event);DATA_DIR=PROJECT_ROOT/"data"/"alpha124";DATA_DIR.mkdir(parents=True,exist_ok=True);STATE_FILE=DATA_DIR/"alpha124_shadow_state.json";LEDGER_FILE=DATA_DIR/"alpha124_shadow_ledger.jsonl";MARKET_TELEMETRY_FILE=DATA_DIR/"alpha124_market_telemetry.jsonl";OPPS_FILE=DATA_DIR/"alpha124_live_opportunities.json";LOG_FILE=DATA_DIR/"alpha124_shadow.log";BACKTEST_CAL_FILE=DATA_DIR/"backtest_alpha_124_results.json";LIVE_POLYMARKET_DIR=PROJECT_ROOT/"data"/"polymarket";SHOCK_TRIGGER_FILE=LIVE_POLYMARKET_DIR/"live_shock_triggers.jsonl";LIVE_ALPHA124_STATE_MIRROR_FILE=LIVE_POLYMARKET_DIR/"alpha124_shadow_state.json";D1_LIVE_CANDIDATES_FILE=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl";logging.basicConfig(level=logging.INFO,format="[%(asctime)s UTC] [%(levelname)s] [ALPHA-124] %(message)s",datefmt="%Y-%m-%d %H:%M:%S",handlers=[logging.FileHandler(LOG_FILE,encoding="utf-8"),logging.StreamHandler(sys.stdout)]);logger=logging.getLogger("Alpha124Shadow");GAMMA_URL="https://gamma-api.polymarket.com";CLOB_URL="https://clob.polymarket.com";DATA_API_URL="https://data-api.polymarket.com";CLOB_WS_URL="wss://ws-subscriptions-clob.polymarket.com/ws/market";BINANCE_URL="https://api.binance.com";LOCKED_MAKER_SLEEVES=frozenset({"W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK","BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","SP2_NBA_ENDGAME_LOCK","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"});DEPTH_CAPPED_TAKER_SLEEVES=LOCKED_MAKER_SLEEVES|frozenset({"CM_B2_PYTH_SESSION_NO_LOCK","CM_U1_PYTH_CLOSE_LOCK","B4_TOUCHED_BARRIER_WICK_LOCK","TW1_COUNTING_TRUNCATION_AND_BOX","GAS1_AAA_GASOLINE_LOCK","API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","AFF1_FROZEN_SUBPERIOD_COLLAPSE","SOC2_EXACT_SCORE_2D_LATTICE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS"})
try:import orjson as _orjson
except Exception:_orjson=None
CRYPTO_FEE_RATE=.07;QUARANTINED_SHADOW_SLEEVES=frozenset({"M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","B1_CONVEX_TAIL_YES","S2_EXACT_TWAP_LOCK","S5M_CHAINLINK_SNIPER","ZERO_FEE_MAKER_ANCHOR_BOX","CTF_OVERROUND_MINT_SELL"})
def is_shadow_sleeve_quarantined(sleeve):return os.getenv("PM_QUARANTINE_LOSING_SLEEVES","1")=="1"and sleeve in QUARANTINED_SHADOW_SLEEVES
FRONTIER_V3_GRAD8_SLEEVES=frozenset({"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR"});BANKROLL_TICKETS={"T100":{"W1_SOLAR_PEAK_LOCK":15.,"W2_ENSEMBLE_VALUE":10.,"W2_MAKER_OVERROUND":10.,"W3_WEATHER_SLATE_ARB":12.,"B1_CONVEX_TAIL_YES":4.,"B2_BARRIER_NO_LOCK":15.,"B3_BARRIER_MONO_BOX":18.,"M1_SVI_MAKER_SCALP":15.,"M2_STRIKE_CONVERGENCE":15.,"M3_LADDER_MONO_BOX":20.,"M4_SHOCK_STRIKE_CATCHUP":15.,"D1_SAME_ORACLE_DOMINANCE_BOX":20.,"D1_4H_DOMINANCE_BOX":20.,"D1_QUIET_BOOK_BOX":20.,"D1_MAKER_ANCHOR_BOX":18.,"S5M_CHAINLINK_SNIPER":15.,"N1_NEGRISK_CROSS_BOX":20.,"P1_PREOPEN_MAKER_STRADDLE":16.,"U1_DAILY_UPDOWN_LOCK":15.,"C1_BINARY_COMPLETE_SET":20.,"S2_EXACT_TWAP_LOCK":15.,"CM_B3_PYTH_BARRIER_BOX":20.,"CM_B2_PYTH_SESSION_NO_LOCK":15.,"CM_U1_PYTH_CLOSE_LOCK":15.,"B4_TOUCHED_BARRIER_WICK_LOCK":20.,"SP1_NBA_ZERO_FEE_BOX":20.,"NR0_ZERO_FEE_SLATE_ARB":15.,"ZERO_FEE_MAKER_ANCHOR_BOX":18.,"ZF_INTRADAY_MAKER_BOX":18.,"TW1_COUNTING_TRUNCATION_AND_BOX":18.,"FED1_CENTRAL_BANK_LP_BOX":20.,"COND1_MACRO_PARTITION_BOX":20.,"CTF_OVERROUND_MINT_SELL":20.,"D2_12PM_BINANCE_BOX":18.,"GAS1_AAA_GASOLINE_LOCK":15.,"CM_SHOCK_PYTH_CATALYST":15.,"S4H_CHAINLINK_CONVERGENCE":15.,"MKR_REWARD_LOCKED_CARRY":15.,"W1_LOW_TROUGH_LOCK":15.,"SP2_NBA_ENDGAME_LOCK":18.,"BOND1_UMA_RESOLUTION_CARRY":20.,"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX":20.,"NR_CONV_NO_BASKET_ARB":20.,"NR2_CONVERT_NO_SUBSET_ARB":20.,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":18.,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":20.,"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":20.,"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX":20.,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":18.,"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG":20.,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":18.,"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX":20.,"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX":20.,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":18.,"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR":18.,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":18.,"SOC2_EXACT_SCORE_2D_LATTICE":18.,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":18.,"SUM1_FRECHET_SUM_TRIANGLES":20.,"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION":20.,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":18.},"T1000":{"W1_SOLAR_PEAK_LOCK":1e2,"W2_ENSEMBLE_VALUE":50.,"W2_MAKER_OVERROUND":50.,"W3_WEATHER_SLATE_ARB":80.,"B1_CONVEX_TAIL_YES":25.,"B2_BARRIER_NO_LOCK":1e2,"B3_BARRIER_MONO_BOX":120.,"M1_SVI_MAKER_SCALP":1e2,"M2_STRIKE_CONVERGENCE":1e2,"M3_LADDER_MONO_BOX":150.,"M4_SHOCK_STRIKE_CATCHUP":1e2,"D1_SAME_ORACLE_DOMINANCE_BOX":1e2,"D1_4H_DOMINANCE_BOX":1e2,"D1_QUIET_BOOK_BOX":1e2,"D1_MAKER_ANCHOR_BOX":1e2,"S5M_CHAINLINK_SNIPER":1e2,"N1_NEGRISK_CROSS_BOX":150.,"P1_PREOPEN_MAKER_STRADDLE":96.,"U1_DAILY_UPDOWN_LOCK":1e2,"C1_BINARY_COMPLETE_SET":150.,"S2_EXACT_TWAP_LOCK":1e2,"CM_B3_PYTH_BARRIER_BOX":120.,"CM_B2_PYTH_SESSION_NO_LOCK":1e2,"CM_U1_PYTH_CLOSE_LOCK":1e2,"B4_TOUCHED_BARRIER_WICK_LOCK":120.,"SP1_NBA_ZERO_FEE_BOX":120.,"NR0_ZERO_FEE_SLATE_ARB":1e2,"ZERO_FEE_MAKER_ANCHOR_BOX":1e2,"ZF_INTRADAY_MAKER_BOX":110.,"TW1_COUNTING_TRUNCATION_AND_BOX":1e2,"FED1_CENTRAL_BANK_LP_BOX":120.,"COND1_MACRO_PARTITION_BOX":120.,"CTF_OVERROUND_MINT_SELL":120.,"D2_12PM_BINANCE_BOX":1e2,"GAS1_AAA_GASOLINE_LOCK":80.,"CM_SHOCK_PYTH_CATALYST":1e2,"S4H_CHAINLINK_CONVERGENCE":1e2,"MKR_REWARD_LOCKED_CARRY":1e2,"W1_LOW_TROUGH_LOCK":1e2,"SP2_NBA_ENDGAME_LOCK":1e2,"BOND1_UMA_RESOLUTION_CARRY":120.,"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX":120.,"NR_CONV_NO_BASKET_ARB":120.,"NR2_CONVERT_NO_SUBSET_ARB":120.,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":1e2,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":120.,"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":120.,"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX":120.,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":1e2,"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG":120.,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":1e2,"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX":120.,"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX":120.,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":1e2,"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR":1e2,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":110.,"SOC2_EXACT_SCORE_2D_LATTICE":110.,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":1e2,"SUM1_FRECHET_SUM_TRIANGLES":120.,"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION":120.,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":1e2},"T5000":{"W1_SOLAR_PEAK_LOCK":350.,"W2_ENSEMBLE_VALUE":175.,"W2_MAKER_OVERROUND":175.,"W3_WEATHER_SLATE_ARB":250.,"B1_CONVEX_TAIL_YES":75.,"B2_BARRIER_NO_LOCK":350.,"B3_BARRIER_MONO_BOX":4e2,"M1_SVI_MAKER_SCALP":350.,"M2_STRIKE_CONVERGENCE":350.,"M3_LADDER_MONO_BOX":5e2,"M4_SHOCK_STRIKE_CATCHUP":350.,"D1_SAME_ORACLE_DOMINANCE_BOX":3e2,"D1_4H_DOMINANCE_BOX":3e2,"D1_QUIET_BOOK_BOX":3e2,"D1_MAKER_ANCHOR_BOX":3e2,"S5M_CHAINLINK_SNIPER":3e2,"N1_NEGRISK_CROSS_BOX":5e2,"P1_PREOPEN_MAKER_STRADDLE":288.,"U1_DAILY_UPDOWN_LOCK":350.,"C1_BINARY_COMPLETE_SET":5e2,"S2_EXACT_TWAP_LOCK":3e2,"CM_B3_PYTH_BARRIER_BOX":4e2,"CM_B2_PYTH_SESSION_NO_LOCK":350.,"CM_U1_PYTH_CLOSE_LOCK":350.,"B4_TOUCHED_BARRIER_WICK_LOCK":4e2,"SP1_NBA_ZERO_FEE_BOX":4e2,"NR0_ZERO_FEE_SLATE_ARB":3e2,"ZERO_FEE_MAKER_ANCHOR_BOX":350.,"ZF_INTRADAY_MAKER_BOX":350.,"TW1_COUNTING_TRUNCATION_AND_BOX":350.,"FED1_CENTRAL_BANK_LP_BOX":4e2,"COND1_MACRO_PARTITION_BOX":4e2,"CTF_OVERROUND_MINT_SELL":4e2,"D2_12PM_BINANCE_BOX":3e2,"GAS1_AAA_GASOLINE_LOCK":250.,"CM_SHOCK_PYTH_CATALYST":3e2,"S4H_CHAINLINK_CONVERGENCE":3e2,"MKR_REWARD_LOCKED_CARRY":3e2,"W1_LOW_TROUGH_LOCK":350.,"SP2_NBA_ENDGAME_LOCK":350.,"BOND1_UMA_RESOLUTION_CARRY":4e2,"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX":4e2,"NR_CONV_NO_BASKET_ARB":4e2,"NR2_CONVERT_NO_SUBSET_ARB":4e2,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":350.,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":4e2,"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":4e2,"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX":4e2,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":350.,"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG":4e2,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":350.,"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX":4e2,"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX":4e2,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":350.,"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR":350.,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":350.,"SOC2_EXACT_SCORE_2D_LATTICE":350.,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":350.,"SUM1_FRECHET_SUM_TRIANGLES":4e2,"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION":4e2,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":350.}}
def walk_l2_book_asks(asks_raw,notional_usd,fee_rate,max_slip_cents=.025,min_l1_usd=20.,min_fill_ratio=.98,max_ask_px=.98,fee_exponent=1.):
 o=sorted([(float(a["price"]),float(a["size"]))for a in asks_raw if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
 if not o:return{"filled":False,"reason":"EMPTY_ASK_BOOK","best_ask":1.}
 f=o[0][0];l=round(f*o[0][1],2)
 if l<min_l1_usd:return{"filled":False,"reason":"THIN_L1_DEPTH","best_ask":f,"l1_usd":l}
 k=notional_usd;e=.0;c=.0;d=0;b=f
 for px,sz in o:
  if px>f+max_slip_cents or px>=max_ask_px:break
  h=px*sz;d+=1;b=px;n=min(k,h);c+=n/px;e+=n;k-=n
  if k<=1e-6:break
 if e<notional_usd*min_fill_ratio or c<=0:return{"filled":False,"reason":"INSUFFICIENT_DEPTH","best_ask":f,"l1_usd":l}
 m=e/c;j=fee_rate*((m*(1.-m))**fee_exponent)if fee_rate>0 else.0;g=c*j;i=(e+g)/c;return{"filled":True,"best_ask":round(f,4),"worst_px":round(b,4),"vwap":round(m,4),"eff_px":round(i,4),"slip_cents":round((m-f)*1e2,2),"spent_usd":round(e,2),"fee_usd":round(g,4),"shares":round(c,4),"fill_ratio":round(e/notional_usd,4),"l1_usd":l,"levels":d}
def walk_l2_book_asks_depth_capped(asks_raw,target_notional_usd,min_notional_usd,fee_rate=.0,max_slip_cents=.025,min_l1_usd=15.,max_ask_px=.98,fee_exponent=1.):
 e=walk_l2_book_asks(asks_raw,target_notional_usd,fee_rate=fee_rate,max_slip_cents=max_slip_cents,min_l1_usd=min_l1_usd,max_ask_px=max_ask_px,fee_exponent=fee_exponent)
 if e.get("filled")or e.get("reason")!="INSUFFICIENT_DEPTH":return e
 asks=sorted([(float(a["price"]),float(a["size"]))for a in asks_raw if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
 if not asks:return e
 best_ask=asks[0][0];c=sum(px*sz for px,sz in asks if px<=best_ask+max_slip_cents and px<max_ask_px)
 if c<min_notional_usd:return e
 b=min(target_notional_usd,c);d=walk_l2_book_asks(asks_raw,b,fee_rate=fee_rate,max_slip_cents=max_slip_cents,min_l1_usd=min_l1_usd,min_fill_ratio=.98,max_ask_px=max_ask_px,fee_exponent=fee_exponent)
 if d.get("filled"):d["fill_ratio"]=round(float(d["spent_usd"])/max(.01,target_notional_usd),4);d["depth_capped"]=b<target_notional_usd*.98
 return d
def extract_best_bid(bids_raw):
 a=sorted([(float(b["price"]),float(b["size"]))for b in bids_raw if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0])
 if not a:return.0,.0
 return round(a[0][0],4),round(a[0][0]*a[0][1],2)
class _LazyWsBooksDict(dict):
 def __init__(self,owner):super().__init__();self._owner=owner;self._dirty={}
 def mark_dirty(self,asset_id,ts):
  self._dirty[asset_id]=ts
  if not dict.__contains__(self,asset_id):dict.__setitem__(self,asset_id,(ts,{"asset_id":asset_id,"bids":[],"asks":[]}))
 def _materialize(self,key):
  ts=self._dirty.pop(key,None)
  if ts is not None:
   a=self._owner._ws_raw_levels.get(key)
   if a is not None:self._owner._rebuild_ws_book_dict(key,a[0],a[1],ts)
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
 def __init__(self,single_scan=False):
  self.single_scan=single_scan;self.session=None;self.started_at=datetime.now(timezone.utc).isoformat();self.weather_sigma_c=1.05;self.barrier_wick_mult=1.12;self._load_calibration();self.spots={};self.spot_hist={a:collections.deque(maxlen=600)for a in DOMINANCE_ASSETS};self.usd_spot_hist={a:collections.deque(maxlen=400)for a in DOMINANCE_ASSETS};self.usd_direct_flags={};self.weather_events={};self.barrier_rungs={};self.strike_ladders={};self.negrisk_ladders={};self.daily_updown_markets={};self.pyth_daily_markets={};self.pyth_barrier_rungs={};self.pyth_close_ladders={};self.nba_games={};self.multi_sport_games={};self.negrisk_convert_slates={};self.live_nba_board=[];self.uma_proposed_markets={};self.uma_onchain_cache={};self.bond2_onchain_cache={};self.nba_prop_slates={};self.nba_boxscore_cache={};self.nba_subperiod_slates={};self.nba_ext_summary_cache={};self.soccer_trees={};self.lp1_bop_legs=[];self.lp1_nba_em_bundles={};self.esports_bo3_specs={};self.lp2_implication_groups=[];self.lp2_events_by_slug={};self.cal1_ladders={};self.lp1_nfl_em_bundles={};self.multisport_raw_events={};self.tennis_specs={};self.score_confirm_tracker=ScoreConfirmationTracker();self.live_multisport_boards={};self.aff1_bundles={};self.soc2_lattices={};self.nfl_prop_slates={};self.binance_close_rungs=[];self.subperiod_freeze_tracker=SubperiodFreezeTracker();self.nfl_summary_cache={};self.negrisk_zero_slates={};self.counting_slates={};self.fomc_truth_legs=[];self.oil_senate_truth_legs=[];self.gas_events_raw={};self.hourly_12pm_markets={};self.s4h_candles={};self.pending_zero_fee_maker_anchors={};self.prev_pyth_spots={};self.pyth_intraday_cache={};self.dominance_pairs={};self.dominance_4h_pairs={};self.twap_candles={};self.s5m_candles={};self.preopen_15m_candles={};self.pending_preopen_straddles={};self.pending_maker_anchors={};self.chainlink_open_cache={};self.daily_open_cache={};self.metar_cache={};self.taf_cache={};self.ensemble_cache={};self.barrier_ext_cache={};self._last_w3_slate_chk_ts={};self._last_trade_tape_chk_ts={};self._open_meteo_sem=asyncio.Semaphore(2);self.last_discovery_ts=.0;self.last_weather_scan_ts=.0;self.last_crypto_mid_scan_ts=.0;self.last_tradfi_sports_scan_ts=.0;self.last_nba_endgame_scan_ts=.0;self.last_espn_board_ts=.0;self.last_uma_discovery_ts=.0;self.last_dominance_discovery_ts=.0;self.last_4h_discovery_ts=.0;self.last_twap_discovery_ts=.0;self.last_s5m_discovery_ts=.0;self.last_preopen_discovery_ts=.0;self.last_usd_sample_ts=.0;self.cached_mid_opps=[];self.cached_weather_opps=[];self.cached_tradfi_sports_opps=[];self.cached_nba_endgame_opps=[];self.cached_shock_opps=[];self.cycle_count=0
  try:self._shock_file_offset=SHOCK_TRIGGER_FILE.stat().st_size if SHOCK_TRIGGER_FILE.exists()else 0
  except Exception:self._shock_file_offset=0
  self._seen_shock_ids=collections.deque(maxlen=256);self._last_m4_shock_ts_by_asset={};self._last_any_shock_ts_by_asset={};self._last_d1_live_emit_ts={};self._bg_discovery_task=None;self._bg_weather_task=None;self._bg_mid_task=None;self._bg_tradfi_task=None;self._bg_nba_task=None;self._ws_books=_LazyWsBooksDict(self);self._ws_raw_levels={};self._ws_subscribed_tokens=set();self._ws_rest_seeded=set();self._ws_d1_priority_tokens=set();self._bg_chainlink_ws_task=None;self._chainlink_ws=(PolymarketChainlinkLiveStream(on_tick=self._on_chainlink_ws_tick)if(not self.single_scan and PolymarketChainlinkLiveStream is not None)else None);self._ws_d1_wakeup=asyncio.Event();self._bg_clob_ws_task=None;self._strike_fail_backoff_ts={};self._last_telem_ts_by_key={};self._last_telem_sig_by_key={};self.open_positions={};self.pending_maker_orders={};self.closed_positions=[];self.entered_keys=set();self.inflight_keys=set();self.top_opportunities=[];self._hydrate_state()
 def is_sleeve_grad8_ready(self,sleeve):
  if is_shadow_sleeve_quarantined(sleeve):return False
  closed_sl=[p for p in self.closed_positions if p.get("sleeve")==sleeve];f=len(closed_sl);e=sum(1 for p in closed_sl if p.get("won"));d=f-e;a=self.__dict__.setdefault("_grad8_promoted_logged",set())
  if d>0:
   if sleeve in a:a.discard(sleeve);logger.warning(f"🛑 [GRAD8 AUTO-PROMOTION REVOKED] {sleeve}: {e}/{f} ({d} loss) — live IPC bridge DISARMED.")
   return False
  if f<8:return False
  c=sum(float(p.get("tier_pnls_usd",{}).get("T1000",.0))for p in closed_sl);b=sum(float(p.get("legging_adjusted_tier_pnls_usd",p.get("tier_pnls_usd",{})).get("T1000",.0))for p in closed_sl)
  if c<=.0 or b<=.0:return False
  if sleeve not in a:
   a.add(sleeve);logger.info(f"🚀 [GRAD8 AUTO-PROMOTED -> LIVE] {sleeve}: {e}/{f} wins (100.0% WR, T1000=+${c:.2f}) — live IPC bridge ARMED!")
   if STATE_FILE==(DATA_DIR/"alpha124_shadow_state.json")or LIVE_ALPHA124_STATE_MIRROR_FILE!=(LIVE_POLYMARKET_DIR/"alpha124_shadow_state.json"):
    try:self.write_state_files(self.top_opportunities)
    except Exception as exc:pass
  return True
 def _try_acquire_keys(self,*keys):
  a=[str(k)for k in keys if k]
  if not a:return[]
  for k in a:
   if k in self.entered_keys or k in self.inflight_keys:return[]
  for k in a:self.inflight_keys.add(k)
  return a
 def _release_inflight_keys(self,keys):
  for k in keys:self.inflight_keys.discard(k)
 def _record_market_telemetry(self,key,min_interval_sec,payload,now_ts=None,sig=None,unchanged_heartbeat_sec=6e2):
  g=float(now_ts if now_ts is not None else time.time());c=float(self._last_telem_ts_by_key.get(key)or.0)
  if(g-c)<min_interval_sec:return
  if sig is not None and self._last_telem_sig_by_key.get(key)==sig and(g-c)<unchanged_heartbeat_sec:return
  self._last_telem_ts_by_key[key]=g
  if sig is not None:self._last_telem_sig_by_key[key]=sig
  if len(self._last_telem_ts_by_key)>5000:
   for b,e in list(self._last_telem_ts_by_key.items()):
    if(g-float(e or.0))>7200.:self._last_telem_ts_by_key.pop(b,None);self._last_telem_sig_by_key.pop(b,None)
   for b in list(self._last_telem_sig_by_key.keys()):
    if b not in self._last_telem_ts_by_key:self._last_telem_sig_by_key.pop(b,None)
  f={"ts":round(g,3),"utc":datetime.fromtimestamp(g,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),**payload}
  try:
   if((self.single_scan or("fetch_json"in self.__dict__))and MARKET_TELEMETRY_FILE==(DATA_DIR/"alpha124_market_telemetry.jsonl")and STATE_FILE==(DATA_DIR/"alpha124_shadow_state.json")and LEDGER_FILE==(DATA_DIR/"alpha124_shadow_ledger.jsonl")):return
   if MARKET_TELEMETRY_FILE!=(DATA_DIR/"alpha124_market_telemetry.jsonl"):a=MARKET_TELEMETRY_FILE
   elif STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json"):a=STATE_FILE.parent/"alpha124_market_telemetry.jsonl"
   else:a=LEDGER_FILE.parent/"alpha124_market_telemetry.jsonl"
   d=(json.dumps(f,separators=(",",":"))+"\n").encode("utf-8");fd=os.open(str(a),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o664)
   try:
    try:import fcntl;fcntl.flock(fd,fcntl.LOCK_EX)
    except Exception:pass
    os.write(fd,d)
   finally:
    try:import fcntl;fcntl.flock(fd,fcntl.LOCK_UN)
    except Exception:pass
    os.close(fd)
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
 def _record_d1_corridor_telemetry(self,pair_type,m_outer,m_inner,dom_info,bk_a,bk_b,now_ts):
  k,j=dom_info["leg_a"],dom_info["leg_b"];i,q=self._best_ask_sz(bk_a);h,p=self._best_ask_sz(bk_b)
  if i>=1. or h>=1.:return
  g,_=extract_best_bid(bk_a.get("bids")or[]);f,_=extract_best_bid(bk_b.get("bids")or[]);fa=float(k["fee_rate"])*((i*(1.-i))**float(k.get("fee_exponent",1.)));fb=float(j["fee_rate"])*((h*(1.-h))**float(j.get("fee_exponent",1.)));b=[]
  for s,r,e in((g,i,h+fb),(f,h,i+fa)):
   if s<=.0:continue
   o=.001 if(s>=.96 or s<.04)else.01;n=.001 if(r>.96 or r<=.04)else.01;m=(math.floor((s+o+1e-9)*1e2)/1e2)if(.04+1e-9<round(s+o,4)<.96-1e-9)else round(s+o,3);l=(math.floor((r-n+1e-9)*1e2)/1e2)if(.04+1e-9<round(r-n,4)<.96-1e-9)else round(r-n,3)
   if m<=l+1e-9 and m>s+1e-9:b.append(round(min(m,l)+e,4))
   elif(r-s)>=.01-1e-9 and.15<=r<=.85:b.append(round(s+e,4))
  a=min(b)if b else None;d=self.usd_spot_hist.get(m_outer.asset);c=round(float(d[-1][1]),6)if d else None;self._record_market_telemetry(key=f"D1_{pair_type}_{m_outer.asset}_{m_inner.market_id}",min_interval_sec=10.,now_ts=now_ts,sig=(i,h,a),unchanged_heartbeat_sec=60.,payload={"type":"D1_CORRIDOR","pair_type":pair_type,"asset":m_outer.asset,"regime":dom_info["regime"],"m_outer_id":m_outer.market_id,"m_inner_id":m_inner.market_id,"end_ts":int(m_inner.end_ts),"tte_sec":round(m_inner.end_ts-now_ts,1),"k_low":dom_info["k_low"],"k_high":dom_info["k_high"],"corridor_bps":dom_info["corridor_bps"],"usd_spot":c,"leg_a_ask":i,"leg_b_ask":h,"gross_box_l1":round(i+h,4),"net_box_l1":round(i+fa+h+fb,4),"maker_anchor_net_l1":a,"l1_min_shares":round(min(q,p),2)})
 def _load_calibration(self):
  if not BACKTEST_CAL_FILE.exists():return
  try:
   d=json.loads(BACKTEST_CAL_FILE.read_text(encoding="utf-8"));b=d.get("option_1_weather",{}).get("calibrated_sigma_c");a=d.get("option_2_barrier_onetouch",{}).get("calibrated_wick_vol_mult")
   if b:self.weather_sigma_c=float(b)
   if a:self.barrier_wick_mult=float(a)
   logger.info(f"Loaded WFO calibration: weather_sigma_c={self.weather_sigma_c}, barrier_wick_mult={self.barrier_wick_mult}")
  except Exception as exc:logger.warning(f"Calibration load notice: {exc}")
 def _hydrate_state(self):
  if STATE_FILE.exists():
   try:
    st=json.loads(STATE_FILE.read_text(encoding="utf-8"));self.started_at=st.get("started_at",self.started_at)
    for p in st.get("open_positions",[]):
     if isinstance(p,dict)and p.get("position_id"):
      self.open_positions[p["position_id"]]=p;self.entered_keys.add(str(p.get("dedupe_key")or p["position_id"]));a=(p.get("extra")or{}).get("event_id")
      if a:
       if p.get("sleeve")=="W2_ENSEMBLE_VALUE":self.entered_keys.add(f"W2_EVENT_{a}")
       elif p.get("sleeve")=="W2_MAKER_OVERROUND":self.entered_keys.add(f"W2M_EVENT_{a}")
    for o in st.get("pending_maker_orders",[]):
     if isinstance(o,dict)and o.get("order_id"):
      self.pending_maker_orders[o["order_id"]]=o
      if o.get("dedupe_key"):self.entered_keys.add(str(o["dedupe_key"]))
      a=(o.get("extra")or{}).get("event_id")
      if a and o.get("sleeve")=="W2_MAKER_OVERROUND":self.entered_keys.add(f"W2M_EVENT_{a}")
    for p in st.get("recent_closed_positions",[]):
     if isinstance(p,dict):
      self.closed_positions.append(p)
      if p.get("dedupe_key"):self.entered_keys.add(str(p["dedupe_key"]))
      a=(p.get("extra")or{}).get("event_id")
      if a:
       if p.get("sleeve")=="W2_ENSEMBLE_VALUE":self.entered_keys.add(f"W2_EVENT_{a}")
       elif p.get("sleeve")=="W2_MAKER_OVERROUND":self.entered_keys.add(f"W2M_EVENT_{a}")
   except Exception as exc:logger.warning(f"State hydrate notice: {exc}")
  if LEDGER_FILE.exists():
   try:
    d={};c={};e={str(p.get("position_id"))for p in self.closed_positions if isinstance(p,dict)and p.get("position_id")}
    with open(LEDGER_FILE,"r",encoding="utf-8",errors="ignore")as f:
     for q in f:
      if not q.strip():continue
      try:r=json.loads(q)
      except Exception:continue
      ev=r.get("event")
      if ev in("SHADOW_ENTRY","SHADOW_CLOSE")and r.get("dedupe_key"):self.entered_keys.add(str(r["dedupe_key"]))
      if ev=="SHADOW_ENTRY":
       h=str(r.get("position_id")or"")
       if h:b={k:v for k,v in r.items()if k!="event"};d[h]=b
       n=str(r.get("dedupe_key")or"")
       if n:
        for m,t in list(c.items()):
         if str(t.get("dedupe_key")or"")==n:c.pop(m,None)
       a=(r.get("extra")or{}).get("event_id")
       if a:
        if r.get("sleeve")=="W2_ENSEMBLE_VALUE":self.entered_keys.add(f"W2_EVENT_{a}")
        elif r.get("sleeve")=="W2_MAKER_OVERROUND":self.entered_keys.add(f"W2M_EVENT_{a}")
      elif ev=="SHADOW_CLOSE":
       h=str(r.get("position_id")or"")
       if h:
        d.pop(h,None);self.open_positions.pop(h,None)
        if h not in e:e.add(h);self.closed_positions.append({k:v for k,v in r.items()if k!="event"})
      elif ev=="SHADOW_MAKER_POST":
       g=str(r.get("order_id")or"")
       if g:
        c[g]={k:v for k,v in r.items()if k!="event"}
        if r.get("dedupe_key"):self.entered_keys.add(str(r["dedupe_key"]))
        a=(r.get("extra")or{}).get("event_id")
        if a and r.get("sleeve")=="W2_MAKER_OVERROUND":self.entered_keys.add(f"W2M_EVENT_{a}")
      elif ev=="SHADOW_MAKER_CANCEL":
       g=str(r.get("order_id")or"")
       if g:
        l=c.pop(g,None);self.pending_maker_orders.pop(g,None)
        if l and l.get("dedupe_key"):self.entered_keys.discard(str(l["dedupe_key"]))
        a=((l or r).get("extra")or{}).get("event_id")
        if a and(l or r).get("sleeve")=="W2_MAKER_OVERROUND":self.entered_keys.discard(f"W2M_EVENT_{a}")
    for h,b in d.items():
     if h not in self.open_positions and h not in e:self.open_positions[h]=b
    for g,j in c.items():
     if g not in self.pending_maker_orders:self.pending_maker_orders[g]=j
   except Exception as exc:logger.warning(f"Ledger hydrate notice: {exc}")
  if self.closed_positions:self.closed_positions.sort(key=lambda p:float(p.get("closed_ts")or.0))
  for i,s in list(self.pending_maker_orders.items()):
   if is_shadow_sleeve_quarantined(str(s.get("sleeve")or"")):self.pending_maker_orders.pop(i,None);self._append_ledger({"event":"SHADOW_MAKER_CANCEL","reason":"SLEEVE_QUARANTINED",**s})
  if is_shadow_sleeve_quarantined("P1_PREOPEN_MAKER_STRADDLE"):self.pending_preopen_straddles.clear()
  if is_shadow_sleeve_quarantined("ZERO_FEE_MAKER_ANCHOR_BOX"):self.pending_zero_fee_maker_anchors.clear()
 def _append_ledger(self,rec):
  with open(LEDGER_FILE,"a",encoding="utf-8")as f:f.write(json.dumps(rec)+"\n")
 async def get_session(self):
  if self.session is None or self.session.closed:self.session=aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=40),headers={"User-Agent":"DominusAlpha124Shadow/1.0","Accept":"application/json"},max_line_size=65536,max_field_size=65536)
  return self.session
 def _on_chainlink_ws_tick(self,asset,ts_sec,price_usd):
  if price_usd<=.0 or not math.isfinite(price_usd):return
  self.spots[asset]=price_usd;self.usd_direct_flags[asset]=True;dq=self.usd_spot_hist.get(asset)
  if dq is None:dq=collections.deque(maxlen=450);self.usd_spot_hist[asset]=dq
  if dq and abs(ts_sec-float(dq[-1][0]))<.05:dq[-1]=(ts_sec,price_usd)
  elif dq and ts_sec<float(dq[-1][0]):return
  else:dq.append((ts_sec,price_usd))
 async def fetch_json(self,url,timeout=5.):
  if not self.single_scan and self._ws_books and"/book?token_id="in str(url):
   c=str(url).split("token_id=",1)[1].split("&",1)[0].strip();a=self._ws_books.get(c)
   if a is not None and(time.time()-a[0])<=1.5:
    b=a[1]
    if b.get("asks")or b.get("bids"):return b
  e=await self.get_session()
  try:
   async with e.get(url,timeout=aiohttp.ClientTimeout(total=timeout))as d:
    if d.status==200:return await d.json()
  except Exception:return None
  return None
 async def fetch_book_after_latency(self,token_id,latency_ms=50):
  if latency_ms>0:await asyncio.sleep(latency_ms/1e3)
  return await self.fetch_json(f"{CLOB_URL}/book?token_id={token_id}",timeout=3.5)
 def _rebuild_ws_book_dict(self,asset_id,bids_map,asks_map,now_ts):b=[{"price":f"{px:.4f}","size":f"{sz:.4f}"}for px,sz in sorted(bids_map.items(),key=lambda kv:-kv[0])[:20]if px>.0 and sz>.0];a=[{"price":f"{px:.4f}","size":f"{sz:.4f}"}for px,sz in sorted(asks_map.items(),key=lambda kv:kv[0])[:20]if px>.0 and sz>.0];self._ws_books[asset_id]=(now_ts,{"asset_id":asset_id,"bids":b,"asks":a})
 def _apply_ws_book_snapshot(self,asset_id,bids_raw,asks_raw,now_ts,from_rest=False):
  if not asset_id:return
  b={};a={}
  for c in bids_raw or():
   try:
    px=round(float(c.get("price",.0)),4);sz=float(c.get("size",.0))
    if px>.0 and sz>.0:b[px]=sz
   except Exception:continue
  for c in asks_raw or():
   try:
    px=round(float(c.get("price",.0)),4);sz=float(c.get("size",.0))
    if px>.0 and sz>.0:a[px]=sz
   except Exception:continue
  self._ws_raw_levels[asset_id]=(b,a);self._rebuild_ws_book_dict(asset_id,b,a,now_ts)
  if from_rest:self._ws_rest_seeded.add(asset_id)
  else:self._ws_rest_seeded.discard(asset_id)
 def _drop_ws_book(self,asset_id):self._ws_books.pop(asset_id,None);self._ws_raw_levels.pop(asset_id,None);self._ws_rest_seeded.discard(asset_id)
 def _apply_ws_price_changes(self,asset_id,changes,now_ts):
  k=self._ws_raw_levels.get(asset_id)
  if k is None:return False
  i,h=k;b=False
  for pc in changes or():
   try:
    px=round(float(pc.get("price",.0)),4);sz=float(pc.get("size",.0));j=str(pc.get("side")or"").upper()
    if px<=.0:continue
    g=i if j=="BUY"else h
    if sz<=.0:
     if px in g:g.pop(px,None);b=True
    else:g[px]=sz;b=True
   except Exception:continue
  f=max(i.keys())if i else.0;e=min(h.keys())if h else.0;a=bool(i and h and f>=e)
  if not a:
   d=None;c=None
   for pc in changes or():
    try:
     if pc.get("best_bid")not in(None,""):d=float(pc.get("best_bid"))
     if pc.get("best_ask")not in(None,""):c=float(pc.get("best_ask"))
    except Exception:continue
   if d is not None and.0<d<1. and abs(d-f)>1e-6:a=True
   if c is not None and.0<c<1. and abs(c-e)>1e-6:a=True
  if a:self._drop_ws_book(asset_id);return False
  if b:
   if isinstance(self._ws_books,_LazyWsBooksDict):self._ws_books.mark_dirty(asset_id,now_ts)
   else:self._rebuild_ws_book_dict(asset_id,i,h,now_ts)
  return b
 def _desired_d1_ws_tokens(self,now_ts):
  out=[];seen=set()
  def _add_tok(tok,max_cap=110):
   if len(out)>=max_cap:return False
   a=str(tok or"").strip()
   if a and a not in seen:seen.add(a);out.append(a)
   return len(out)<max_cap
  for e,d in list(self.dominance_pairs.values())+list(self.dominance_4h_pairs.values()):
   if float(d.end_ts)<=now_ts+5.:continue
   for tok in(e.up_token,e.down_token,d.up_token,d.down_token):_add_tok(tok)
  if not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK"):
   for g in list(self.twap_candles.values()):
    if float(g.end_ts)>now_ts+5.:_add_tok(g.up_token);_add_tok(g.down_token)
  self._ws_d1_priority_tokens=set(out)
  for h in list(self.pyth_daily_markets.values())+list(self.daily_updown_markets.values()):
   if float(h.end_ts)>now_ts+60.:_add_tok(h.up_token);_add_tok(h.down_token)
  for f in list(self.strike_ladders.values()):
   if not f or float(f[0].end_ts)<=now_ts+60.:continue
   spot_r=float(self.spots.get(f[0].asset)or.0);c=sorted(f,key=lambda r:abs(float(r.strike)-spot_r))if spot_r>.0 else list(f)
   for r in c[:4]:_add_tok(r.yes_token);_add_tok(r.no_token)
  for i in list(self.negrisk_ladders.values()):
   if not i or float(i[0].end_ts)<=now_ts+60.:continue
   spot_n=float(self.spots.get(i[0].asset)or.0);a=sorted(i,key=lambda b:abs(.5*(float(b.k_low or spot_n)+float(b.k_high or spot_n))-spot_n))if spot_n>.0 else list(i)
   for b in a[:4]:_add_tok(b.yes_token);_add_tok(b.no_token)
  return out
 async def _run_clob_d1_ws_loop(self):
  while not self.single_scan:
   n=time.time();i=self._desired_d1_ws_tokens(n)
   if not i:self._ws_subscribed_tokens.clear();await asyncio.sleep(1.);continue
   try:
    r=await self.get_session()
    async with r.ws_connect(CLOB_WS_URL,heartbeat=15.,max_msg_size=4*1024*1024,timeout=aiohttp.ClientWSTimeout(ws_close=5.))as ws:
     self._ws_books.clear();self._ws_raw_levels.clear();self._ws_rest_seeded.clear();self._ws_subscribed_tokens=set(i);await ws.send_str(json.dumps({"assets_ids":i,"type":"market"}));b=time.time();a=b
     while not self.single_scan:
      m=time.time()
      if(m-b)>=2.:
       b=m;g=set(self._desired_d1_ws_tokens(m))
       for h in list(self._ws_books.keys()):
        if h not in g:self._drop_ws_book(h)
       if not g:break
       l=sorted(g-self._ws_subscribed_tokens)
       if l:await ws.send_str(json.dumps({"assets_ids":l,"operation":"subscribe"}));self._ws_subscribed_tokens.update(l)
       elif len(self._ws_subscribed_tokens)>len(g)+28:break
      if(m-a)>30.:break
      try:t=await asyncio.wait_for(ws.receive(),timeout=2.)
      except asyncio.TimeoutError:continue
      if t.type in(aiohttp.WSMsgType.CLOSED,aiohttp.WSMsgType.CLOSING,aiohttp.WSMsgType.ERROR):break
      if t.type not in(aiohttp.WSMsgType.TEXT,aiohttp.WSMsgType.BINARY):continue
      f=t.data
      if not f or f in("PONG",b"PONG"):a=time.time();continue
      k=time.time();a=k;q=_orjson.loads(f)if _orjson is not None else json.loads(f);c=False;e=self._ws_d1_priority_tokens
      if isinstance(q,list):
       for p in q:
        if isinstance(p,dict):
         d=str(p.get("asset_id")or"")
         if d in self._ws_subscribed_tokens:self._apply_ws_book_snapshot(d,p.get("bids")or[],p.get("asks")or[],k);c=c or(d in e)
      elif isinstance(q,dict):
       o=q.get("event_type")
       if o=="book":
        d=str(q.get("asset_id")or"")
        if d in self._ws_subscribed_tokens:self._apply_ws_book_snapshot(d,q.get("bids")or[],q.get("asks")or[],k);c=c or(d in e)
       elif o=="price_change":
        j={}
        for pc in q.get("price_changes")or():
         d=str(pc.get("asset_id")or"")
         if d in self._ws_subscribed_tokens:j.setdefault(d,[]).append(pc)
        for d,s in j.items():
         if self._apply_ws_price_changes(d,s,k)and d in e:c=True
      if(c and(self.is_in_same_oracle_overlap_window(k)or bool(self.pending_maker_anchors))and(k-getattr(self,"_last_ws_d1_wake_ts",.0))>=.12):self._last_ws_d1_wake_ts=k;self._ws_d1_wakeup.set()
   except asyncio.CancelledError:raise
   except Exception as exc_ws:await asyncio.sleep(1.)
 async def fetch_books_batch(self,token_ids,timeout=3.):
  uniq=list(dict.fromkeys(str(t)for t in token_ids if t))
  if not uniq:return{}
  if"fetch_json"in self.__dict__:res_list=await asyncio.gather(*(self.fetch_json(f"{CLOB_URL}/book?token_id={t}",timeout=timeout)for t in uniq));return{t:bk for t,bk in zip(uniq,res_list)if isinstance(bk,dict)}
  l={};d=[];g=time.time();e=not self.single_scan
  for t in uniq:
   c=self._ws_books.get(t)if e else None
   if(c is not None and(g-c[0])<=1.5 and c[1].get("bids")and c[1].get("asks")):l[t]=c[1]
   else:d.append(t)
  if not d:return l
  j=await self.get_session()
  for k in range(0,len(d),50):
   chunk=d[k:k+50]
   try:
    async with j.post(f"{CLOB_URL}/books",json=[{"token_id":t}for t in chunk],timeout=aiohttp.ClientTimeout(total=timeout))as i:
     if i.status==200:
      a=await i.read();h=_orjson.loads(a)if _orjson is not None else json.loads(a)
      if isinstance(h,list):
       b=time.time()
       for r in h:
        if isinstance(r,dict)and r.get("asset_id"):
         f=str(r["asset_id"]);l[f]=r
         if e and f in self._ws_subscribed_tokens and f not in self._ws_raw_levels:self._apply_ws_book_snapshot(f,r.get("bids")or[],r.get("asks")or[],b,from_rest=True)
       continue
   except Exception:pass
   fb=await asyncio.gather(*(self.fetch_json(f"{CLOB_URL}/book?token_id={t}",timeout=timeout)for t in chunk))
   for t,bk in zip(chunk,fb):
    if isinstance(bk,dict):l[t]=bk
  return l
 def record_usd_spot_samples(self,now_ts=None):
  e=float(now_ts if now_ts is not None else time.time());self.last_usd_sample_ts=e
  for b in DOMINANCE_ASSETS:
   d=read_shm_usd_anchor(b,e,max_age_sec=2.5);a=d.get("usd_spot");c=str(d.get("source")or"")
   if a and float(a)>0:self.usd_spot_hist.setdefault(b,collections.deque(maxlen=400)).append((e,float(a)));self.usd_direct_flags[b]=c in("shm_chainlink_proxy","shm_coinbase_usd")
 async def update_crypto_spots(self):
  now=time.time();c="%5B"+",".join(f"%22{s}%22"for s in sorted(set(ASSET_BINANCE_SYMBOL.values())))+"%5D";l=await self.fetch_json(f"{BINANCE_URL}/api/v3/ticker/price?symbols={c}",timeout=3.5)
  if isinstance(l,list):
   e={v:k for k,v in ASSET_BINANCE_SYMBOL.items()}
   for j in l:
    m=j.get("symbol")
    if m in e:h=e[m];px=float(j["price"]);self.spots[h]=px;self.spot_hist.setdefault(h,collections.deque(maxlen=600)).append((now,px))
  b=await self.fetch_json(f"{BINANCE_FAPI_URL}/fapi/v1/ticker/price?symbol=HYPEUSDT",timeout=2.5)
  if isinstance(b,dict)and b.get("price"):
   i=float(b["price"])
   if i>0:self.spots["HYPE"]=i;self.spot_hist.setdefault("HYPE",collections.deque(maxlen=600)).append((now,i))
  self.record_usd_spot_samples(now);missing_usd_assets=[a for a in DOMINANCE_ASSETS if a!="HYPE"and(not self.usd_direct_flags.get(a,False)or not self.usd_spot_hist.get(a)or(now-float(self.usd_spot_hist[a][-1][0]))>3.)]
  if missing_usd_assets:
   d=await asyncio.gather(*(self.fetch_json(f"https://api.exchange.coinbase.com/products/{a}-USD/ticker",timeout=2.)for a in missing_usd_assets));f=time.time()
   for a,cb in zip(missing_usd_assets,d):
    if isinstance(cb,dict)and cb.get("price"):
     try:
      g=float(cb["price"])
      if g>0:self.usd_spot_hist.setdefault(a,collections.deque(maxlen=400)).append((f,g));self.usd_direct_flags[a]=True
     except Exception:pass
 @staticmethod
 def _hist_return_bps(hist,lookback_sec):
  if not hist or len(hist)<2:return.0
  d,c=hist[-1];a=hist[-2][1]
  for b in range(len(hist)-1):
   ts,px=hist[b]
   if d-ts<=lookback_sec:a=px;break
  return((c-a)/a)*1e4 if a>0 else.0
 def get_return_bps(self,asset,lookback_sec):a=self._hist_return_bps(self.spot_hist.get(asset),lookback_sec);b=self._hist_return_bps(self.usd_spot_hist.get(asset),lookback_sec);return b if abs(b)>abs(a)else a
 async def discover_all_markets(self):
  logger.info("Discovering active Weather (#1), Barrier Hit (#2), Multi-Strike (#4), NegRisk, and Daily Up/Down markets...");weather_found={};now_w_disc=time.time()
  def _weather_still_live(sp_w):
   try:return datetime.fromisoformat(sp_w.end_date_iso.replace("Z","+00:00")).timestamp()>now_w_disc
   except Exception:return True
  def _parse_neg_risk_flag(v):
   if isinstance(v,bool):return v
   if isinstance(v,str)and v.strip().lower()in("true","false"):return v.strip().lower()=="true"
   return None
  def _attach_weather_neg_risk(sp_w,ev_raw):
   if not isinstance(ev_raw,dict):return
   d=_parse_neg_risk_flag(ev_raw.get("negRisk"));c={}
   for mk in ev_raw.get("markets")or():
    if not isinstance(mk,dict):continue
    a=_parse_neg_risk_flag(mk.get("negRisk"))
    if a is None:a=d
    for e in(mk.get("id"),mk.get("conditionId")):
     if e not in(None,""):c[str(e)]=a
   for f in sp_w.buckets:
    b=c.get(str(f.market_id))
    if b is None:b=c.get(str(f.condition_id))
    if b is None and getattr(f,"neg_risk",None)is not None:continue
    try:setattr(f,"neg_risk",b)
    except Exception:pass
  w_tag_pages=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?tag_slug=weather&closed=false&limit=100&offset={w_off}",timeout=7.)for w_off in(0,100,200)))
  for _C in w_tag_pages:
   if isinstance(_C,list):
    for ev in _C:
     sp=parse_weather_event(ev)
     if sp is not None and _weather_still_live(sp):_attach_weather_neg_risk(sp,ev);weather_found[sp.event_id]=sp
  top_vol_events_raw=[]
  for _4 in range(0,600,100):
   y=await self.fetch_json(f"{GAMMA_URL}/events?closed=false&order=volume24hr&ascending=false&limit=100&offset={_4}",timeout=7.)
   if not isinstance(y,list)or not y:break
   top_vol_events_raw.extend(y)
   for ev in y:
    sp=parse_weather_event(ev)
    if sp is not None and _weather_still_live(sp):_attach_weather_neg_risk(sp,ev);weather_found[sp.event_id]=sp
  o={sp.series_slug for sp in weather_found.values()if sp.series_slug}
  for _3 in HIGH_VOLUME_WEATHER_SERIES:
   if _3 in o:continue
   _2=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={_3}&closed=false&limit=3",timeout=5.)
   if isinstance(_2,list):
    for ev in _2:
     sp=parse_weather_event(ev,series_slug_hint=_3)
     if sp is not None and _weather_still_live(sp):_attach_weather_neg_risk(sp,ev);weather_found[sp.event_id]=sp
  self.weather_events=weather_found;n={}
  for a,_am,slug in HIT_SERIES:
   y=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5",timeout=6.)
   if isinstance(y,list):
    for ev in y:
     for r in parse_hit_event(ev,a,_am,slug):
      if r.resolved_yes is None and r.end_ts>time.time()+60:n[r.market_id]=r
  self.barrier_rungs=n;z={};g=[]
  for a,slug in STRIKE_SERIES:
   y=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5",timeout=6.)
   if isinstance(y,list):
    g.extend(y)
    for ev in y:
     _al=parse_multistrike_event(ev,a,slug)
     if _al and _al[0].end_ts>time.time()+60:z[f"{a}_{ev.get('id')}"]=_al
  self.strike_ladders=z;m={}
  for a,slug in NEGRISK_SERIES:
   _B=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4",timeout=6.)
   if isinstance(_B,list):
    for ev in _B:
     brs=parse_negrisk_bracket_event(ev,a,slug)
     if brs and brs[0].end_ts>time.time()+60:m[f"{a}_{int(brs[0].end_ts)}"]=brs
  self.negrisk_ladders=m;x={}
  for a,slug in DAILY_UPDOWN_SERIES:
   _A=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3",timeout=5.)
   if isinstance(_A,list):
    for ev in _A:
     _ak=parse_daily_updown_event(ev,a,slug)
     if _ak is not None and _ak.end_ts>time.time()+60:x[_ak.market_id]=_ak
  self.daily_updown_markets=x;M={}
  for a,slug in ZERO_FEE_PYTH_DAILY_SERIES:
   _z=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=2",timeout=5.)
   if isinstance(_z,list):
    for ev in _z:
     _aj=parse_daily_updown_event(ev,a,slug)
     if _aj is not None and _aj.end_ts>time.time()+60:M[_aj.market_id]=_aj
  self.pyth_daily_markets=M;w=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3",timeout=5.)for _,_,slug in PYTH_HIT_SERIES));i={};now_disc=time.time()
  for(_y,_x,_1),_w in zip(PYTH_HIT_SERIES,w):
   if isinstance(_w,list):
    for ev in _w:
     for rp in parse_pyth_hit_event(ev,_y,_x,_1):
      if rp.end_ts>now_disc+60:i[rp.market_id]=rp
  self.pyth_barrier_rungs=i;G=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3",timeout=5.)for _,slug in PYTH_CLOSE_SERIES));l={}
  for(_v,_0),_u in zip(PYTH_CLOSE_SERIES,G):
   if isinstance(_u,list):
    for ev in _u:
     _t=parse_pyth_close_event(ev,_v,_0)
     if _t and _t[0].end_ts>now_disc+60:l[f"{_v}_{ev.get('id')}"]=_t
  self.pyth_close_ladders=l;W={};_e={};L={};k={};raw_nba_parents={};raw_nba_em={}
  for _d in NBA_SERIES_SLUGS:
   _c=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={_d}&closed=false&limit=40",timeout=6.5)
   if isinstance(_c,list):
    for ev in _c:
     _ai=str(ev.get("slug")or"").lower()
     if _ai.endswith("-exact-margin"):raw_nba_em[_ai[:-13]]=ev;continue
     raw_nba_parents[_ai]=ev;_Z=parse_nba_zero_fee_event(ev,now_ts=now_disc)
     if _Z is not None:W[_Z.event_id]=_Z
     _ah=parse_nba_player_props_from_event(ev,now_ts=now_disc)
     if _ah is not None:L[_ah.event_id]=_ah
     _Y=parse_nba_subperiod_and_ext_props(ev,now_ts=now_disc)
     if _Y is not None:k[_Y.event_id]=_Y
     V=parse_multi_sport_corridor_event(ev,sport_hint="NBA",now_ts=now_disc,skip_nba_fg_zero_fee=True)
     if V is not None:_e[V.event_id]=V
  missing_em_slugs=[sl for sl in list(raw_nba_parents.keys())[:10]if sl not in raw_nba_em]
  if missing_em_slugs:
   K=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?slug={sl}-exact-margin",timeout=4.5)for sl in missing_em_slugs))
   for _av,_X in zip(missing_em_slugs,K):
    if isinstance(_X,list)and _X:raw_nba_em[_av]=_X[0]
  f={}
  for _au,_at in raw_nba_parents.items():
   _as=raw_nba_em.get(_au)
   if _as is not None:
    _ar=build_lp1_nba_exact_margin_bundle(_at,_as)
    if _ar is not None and float(_ar["end_ts"])>now_disc+60:f[_ar["event_id"]]=_ar
  self.nba_games=W;self.nba_prop_slates=L;self.nba_subperiod_slates=k;self.lp1_nba_em_bundles=f;non_nba_sport_series=[(sl_s,sp_t)for sp_t,sl_s in MULTI_SPORT_CORRIDOR_SERIES if sl_s not in NBA_SERIES_SLUGS];_W=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?series_slug={sl_s}&closed=false&limit=25",timeout=5.5)for sl_s,_ in non_nba_sport_series),self.fetch_json(f"{GAMMA_URL}/events?tag_slug=sports&closed=false&order=volume24hr&ascending=false&limit=40",timeout=6.));u={};ms_raw_found={}
  for(_,_V),_s in zip(non_nba_sport_series,_W[:len(non_nba_sport_series)]):
   if isinstance(_s,list):
    for ev in _s:
     J=parse_multi_sport_corridor_event(ev,sport_hint=_V,now_ts=now_disc,skip_nba_fg_zero_fee=True)
     if J is not None:_e[J.event_id]=J
     _r=str(ev.get("id")or"")
     if _r and _V in("NFL","CFB","NHL"):ms_raw_found[_r]=(_V,ev)
     if _V=="NFL":
      _ag=build_lp1_nfl_exact_margin_bundle(ev,now_ts=now_disc)
      if _ag is not None:u[_ag["event_id"]]=_ag
  self.lp1_nfl_em_bundles=u;self.multisport_raw_events=ms_raw_found;d=(_W[-1]if isinstance(_W[-1],list)else[])+[e for e in top_vol_events_raw if isinstance(e,dict)and not e.get("negRisk")and len(e.get("markets")or())>=8]
  for ev in d:
   _q=str(ev.get("id")or"")
   if _q and _q not in _e:
    J=parse_multi_sport_corridor_event(ev,now_ts=now_disc,skip_nba_fg_zero_fee=True)
    if J is not None:_e[J.event_id]=J
  self.multi_sport_games=_e;_p=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4",timeout=5.)for slug in ZERO_FEE_NEGRISK_SERIES));U={};raw_by_series={}
  for _U,_o in zip(ZERO_FEE_NEGRISK_SERIES,_p):
   if isinstance(_o,list):
    raw_by_series[_U]=_o;_b=_U in("best-ai-company","chinese-ai-1")
    for ev in _o:
     _af=parse_zero_fee_negrisk_slate(ev,_U,allow_mixed_fees=_b)
     if _af is not None and _af.end_ts>now_disc+60:U[_af.event_id]=_af
  self.negrisk_zero_slates=U;h={}
  for _T in(top_vol_events_raw+[e for lst in raw_by_series.values()for e in(lst or[])]+[e for lst in w_tag_pages if isinstance(lst,list)for e in lst]):
   if not isinstance(_T,dict):continue
   _S=parse_negrisk_convert_event(_T)
   if _S is not None and _S.end_ts>now_disc+60 and len(_S.brackets)<=45:h[_S.event_id]=_S
  ranked_nrc=sorted(h.values(),key=lambda s:(not s.is_closed_convert_safe,(s.end_ts-now_disc)>172800.,s.end_ts))[:40];self.negrisk_convert_slates={s.event_id:s for s in ranked_nrc};T={}
  for _R,_a in COUNTING_SERIES_HANDLES:
   for _aq in(raw_by_series.get(_R)or[]):
    _ap=parse_counting_slate_event(_aq,_R,_a)
    if _ap is not None and _ap.window_end_ts>now_disc+60:T[_ap.event_id]=_ap
  self.counting_slates=T;self.fomc_truth_legs=build_fomc_truth_table_legs(raw_by_series.get("fomc")or[],raw_by_series.get("fed-3-parlay")or[],sep_2026_realized_action=(os.getenv("PM_SEP_2026_FOMC_ACTION")or"").strip().upper()or None);_Q=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?slug={sl_os}",timeout=5.)for sl_os in OIL_SENATE_SLUGS),self.fetch_json(f"{GAMMA_URL}/events?series_slug=gas-price-hits-weekly&closed=false&limit=2",timeout=5.));I={}
  for sl_os,_P in zip(OIL_SENATE_SLUGS,_Q[:len(OIL_SENATE_SLUGS)]):
   if isinstance(_P,list)and _P:
    _ao=_P[0];I[sl_os]=_ao
    if"pending-oil"in sl_os:
     Z=parse_zero_fee_negrisk_slate(_ao,sl_os)
     if Z is not None and Z.end_ts>now_disc+60:self.negrisk_zero_slates[Z.event_id]=Z
  self.oil_senate_truth_legs=build_oil_senate_truth_table_legs(I);self.gas_events_raw={"us-gas-price-daily":raw_by_series.get("us-gas-price-daily")or[],"gas-price-hits-weekly":_Q[-1]if isinstance(_Q[-1],list)else[]};target_12pm_ends={int(round(sp.end_ts))for sp in self.daily_updown_markets.values()}|{int(round(rgs[0].end_ts))for rgs in self.strike_ladders.values()if rgs};_O=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?series_slug={h_slug}&closed=false&limit=6",timeout=4.5)for h_slug in HOURLY_BINANCE_SERIES.values()));S={}
  for(_n,h_slug),_N in zip(HOURLY_BINANCE_SERIES.items(),_O):
   if isinstance(_N,list):
    for _an in _N:
     sp_h=parse_daily_updown_event(_an,_n,h_slug)
     if sp_h is not None and sp_h.end_ts>now_disc+30 and any(abs(sp_h.end_ts-te)<=5. for te in target_12pm_ends):S[sp_h.market_id]=sp_h
  self.hourly_12pm_markets=S;F=datetime.fromtimestamp(now_disc-4.*3600.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");_m=await asyncio.gather(self.fetch_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&order=volume24hr&ascending=false&limit=100",timeout=5.5),self.fetch_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&end_date_min={F}&order=endDate&ascending=true&limit=100",timeout=5.5),self.fetch_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&order=volume24hr&ascending=false&limit=100",timeout=5.5),self.fetch_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&end_date_min={F}&order=endDate&ascending=true&limit=100",timeout=5.5),*(self.fetch_json(f"{GAMMA_URL}/events?slug={sl_b}",timeout=5.)for sl_b in BOP_2026_SLUGS));soc_pages=(_m[0]if isinstance(_m[0],list)else[])+(_m[1]if isinstance(_m[1],list)else[]);esp_pages=(_m[2]if isinstance(_m[2],list)else[])+(_m[3]if isinstance(_m[3],list)else[]);soc_raw=list({str(e.get("id")):e for e in soc_pages if isinstance(e,dict)and e.get("id")}.values());_l=list({str(e.get("id")):e for e in esp_pages if isinstance(e,dict)and e.get("id")}.values());self.soccer_trees=link_and_parse_soccer_regulation_trees(soc_raw,now_ts=now_disc);R={}
  for _M in _l:
   _L=parse_esports_bo3_event(_M,now_ts=now_disc)
   if _L is not None:R[_L.event_id]=_L
  self.esports_bo3_specs=R;E={}
  for sl_b,_ae in zip(BOP_2026_SLUGS,_m[4:]):
   if isinstance(_ae,list)and _ae:E[sl_b]=_ae[0]
  self.lp1_bop_legs=build_lp1_bop_2026_truth_legs(E)
  for D in list(raw_nba_em.values())+list(E.values()):
   Y=parse_negrisk_convert_event(D)
   if Y is not None and Y.is_closed_convert_safe and Y.end_ts>now_disc+60:self.negrisk_convert_slates[Y.event_id]=Y
  lp2_slugs_all=list(dict.fromkeys(list(LP2_MIDTERM_CORE_SLUGS)+[LP2_TOSSUP_CUBE_SLUG]+list(LP2_TOSSUP_STATE_SLUGS.values())));_k=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?slug={sl_l2}",timeout=5.)for sl_l2 in lp2_slugs_all),self.fetch_json(f"{GAMMA_URL}/events?tag_slug=tennis&active=true&closed=false&order=volume24hr&ascending=false&limit=45",timeout=5.5),self.fetch_json(f"{GAMMA_URL}/events?tag_slug=midterms&active=true&closed=false&order=volume24hr&ascending=false&limit=60",timeout=5.5),self.fetch_json(f"{GAMMA_URL}/events?tag_slug=politics&active=true&closed=false&order=volume24hr&ascending=false&limit=60",timeout=5.5));C=dict(E)
  for sl_l2,_K in zip(lp2_slugs_all,_k[:len(lp2_slugs_all)]):
   if isinstance(_K,list)and _K:C[sl_l2]=_K[0]
  _j=_k[len(lp2_slugs_all)]if isinstance(_k[len(lp2_slugs_all)],list)else[];_i=_k[len(lp2_slugs_all)+1]if isinstance(_k[len(lp2_slugs_all)+1],list)else[];_h=_k[len(lp2_slugs_all)+2]if isinstance(_k[len(lp2_slugs_all)+2],list)else[]
  for _ad in _i+_h:
   if isinstance(_ad,dict)and _ad.get("slug"):C.setdefault(str(_ad["slug"]),_ad)
  self.lp2_events_by_slug=C;H=[];_g=build_lp2_house_seats_truth_legs(C)
  if _g:H.append(("LP2_HOUSE_SEATS",_g))
  _f=build_lp2_senate_seats_truth_legs(C)
  if _f:H.append(("LP2_SENATE_SEATS",_f))
  H.extend(build_lp2_pending_senate_conditional_groups(list(C.values()),C.get("which-party-will-win-the-senate-in-2026")));H.extend(build_lp2_tossup_state_implication_groups(C));self.lp2_implication_groups=H
  for Q in C.values():
   P=parse_negrisk_convert_event(Q)
   if P is not None and P.is_closed_convert_safe and P.end_ts>now_disc+60 and len(P.brackets)<=45:self.negrisk_convert_slates[P.event_id]=P
  O={};q=set()
  for _J in top_vol_events_raw+_i+_h:
   if not isinstance(_J,dict):continue
   _ac=str(_J.get("id")or"")
   if not _ac or _ac in q:continue
   q.add(_ac)
   for _I in parse_cal1_monotonic_ladder_event(_J,now_ts=now_disc):O[_I.event_id]=_I
  self.cal1_ladders=O;N={}
  for _H in _j+d:
   if not isinstance(_H,dict):continue
   _G=parse_tennis_retirement_safe_event(_H,now_ts=now_disc)
   if _G is not None:N[_G.event_id]=_G
  self.tennis_specs=N;nba_base_slugs=[sl for sl,ev_n in sorted(raw_nba_parents.items(),key=lambda kv:_parse_iso_ts(kv[1].get("startTime")or kv[1].get("endDate"))or 9e12)if not sl.endswith("-more-markets")][:12];nfl_cfb_base_slugs=[];nfl_prop_base_slugs=[]
  for _ab,_aa in ms_raw_found.values():
   sl_m4=str(_aa.get("slug")or"").lower()
   if not sl_m4 or any(sl_m4.endswith(sfx)for sfx in("-more-markets","-player-props","-exact-margin")):continue
   if _ab in("NFL","CFB")and len(nfl_cfb_base_slugs)<12:nfl_cfb_base_slugs.append(sl_m4)
   if _ab=="NFL"and len(nfl_prop_base_slugs)<10:nfl_prop_base_slugs.append(sl_m4)
  soc_exact_slugs_existing={str(e.get("slug")or"").lower()for e in soc_raw if isinstance(e,dict)};c=[f"{tr.slug_3way}-exact-score"for tr in sorted(self.soccer_trees.values(),key=lambda t:t.end_ts)[:16]if tr.slug_3way and f"{tr.slug_3way}-exact-score"not in soc_exact_slugs_existing];fv4_sibling_slugs=list(dict.fromkeys([f"{sl}-more-markets"for sl in(nba_base_slugs+nfl_cfb_base_slugs)]+[f"{sl}-player-props"for sl in nfl_prop_base_slugs]+c));p=[]
  if fv4_sibling_slugs:
   B=await asyncio.gather(*(self.fetch_json(f"{GAMMA_URL}/events?slug={sl_v4}",timeout=4.5)for sl_v4 in fv4_sibling_slugs))
   for _F in B:
    if isinstance(_F,list)and _F and isinstance(_F[0],dict):p.append(_F[0])
  aff1_src_evts=(list(raw_nba_parents.values())+[ev_m for sp_tm,ev_m in ms_raw_found.values()if sp_tm in("NFL","CFB")]+d+p);self.aff1_bundles={b.event_id:b for b in parse_affine_game_bundle(aff1_src_evts,now_ts=now_disc)}
  for _E in p:
   _9=str(_E.get("slug")or"").lower()
   if _9.startswith("nba-"):
    X=parse_nba_subperiod_and_ext_props(_E,now_ts=now_disc)
    if X is not None and X.event_id not in self.nba_subperiod_slates:self.nba_subperiod_slates[X.event_id]=X
  self.soc2_lattices=link_and_parse_soc2_exact_score_lattices(soc_raw+p,now_ts=now_disc)
  for _D in self.soc2_lattices.values():
   if _D.convert_spec is not None and _D.convert_spec.end_ts>now_disc+60:self.negrisk_convert_slates[_D.convert_spec.event_id]=_D.convert_spec
  j={}
  for _8 in[ev_m for sp_tm,ev_m in ms_raw_found.values()if sp_tm=="NFL"]+p+d:
   if not isinstance(_8,dict):continue
   _7=parse_nfl_player_props_event(_8,now_ts=now_disc)
   if _7 is not None:j[_7.event_id]=_7
  self.nfl_prop_slates=j;A={}
  for _6 in g+top_vol_events_raw:
   if isinstance(_6,dict):
    for _5 in parse_binance_terminal_close_event(_6):
     if _5.close_ts>now_disc+120:A[_5.market_id]=_5
  self.binance_close_rungs=list(A.values());self.last_discovery_ts=time.time();logger.info(f"Discovery complete: {len(self.weather_events)} Weather city-events, {len(self.barrier_rungs)} Barrier Hit rungs, {len(self.strike_ladders)} Multi-Strike ladders, {len(self.negrisk_ladders)} NegRisk ladders, {len(self.daily_updown_markets)} Crypto Daily Up/Down, {len(self.pyth_daily_markets)} Zero-Fee Pyth FX/Metals Daily, {len(self.pyth_barrier_rungs)} Pyth Hit rungs, {len(self.pyth_close_ladders)} Pyth Close ladders, {len(self.nba_games)} NBA games ({len(self.nba_prop_slates)} Prop, {len(self.nba_subperiod_slates)} SubPer, {len(self.lp1_nba_em_bundles)} EM), {len(self.multi_sport_games)} Multi-Sport ({len(self.lp1_nfl_em_bundles)} NFL EM, {len(self.nfl_prop_slates)} NFL Prop, {len(self.aff1_bundles)} AFF1/SUM1), {len(self.soccer_trees)} Soccer trees ({len(self.soc2_lattices)} SOC2 Exact-Score), {len(self.tennis_specs)} Tennis BO3, {len(self.esports_bo3_specs)} Esports BO3, {len(self.lp2_implication_groups)} LP2 DAG groups, {len(self.cal1_ladders)} CAL1 ladders, {len(self.binance_close_rungs)} Binance Close rungs, {len(self.lp1_bop_legs)//2} BOP/Chamber mkts, {len(self.negrisk_zero_slates)} NegRisk Slates, {len(self.negrisk_convert_slates)} NegRisk Convert slates, {len(self.counting_slates)} Counting slates, {len(self.fomc_truth_legs)//2} FOMC LP mkts, {len(self.oil_senate_truth_legs)//2} Oil-Senate mkts, {len(self.hourly_12pm_markets)} 12PM 1h pairs.")
 async def open_shadow_position(self,sleeve,dedupe_key,asset_or_city,title,side_label,token_id,fee_rate,p_model,close_ts,extra,tp_target_px=None,prefetched_book=None):
  if is_shadow_sleeve_quarantined(sleeve):return False
  j=[dedupe_key]
  if sleeve=="W2_ENSEMBLE_VALUE"and extra.get("event_id"):j.append(f"W2_EVENT_{extra['event_id']}")
  y=self._try_acquire_keys(*j)
  if not y:return False
  try:
   h=250 if sleeve in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK")else 50;u=prefetched_book if(prefetched_book is not None and sleeve not in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"))else await self.fetch_book_after_latency(token_id,latency_ms=h)
   if not u:return False
   m=u.get("asks")or[];l=u.get("bids")or[];k,_=extract_best_bid(l);q=15. if sleeve in("S2_EXACT_TWAP_LOCK","S5M_CHAINLINK_SNIPER","S4H_CHAINLINK_CONVERGENCE","B4_TOUCHED_BARRIER_WICK_LOCK","CM_B2_PYTH_SESSION_NO_LOCK","CM_U1_PYTH_CLOSE_LOCK","TW1_COUNTING_TRUNCATION_AND_BOX","GAS1_AAA_GASOLINE_LOCK","CM_SHOCK_PYTH_CATALYST","W1_LOW_TROUGH_LOCK","BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","AFF1_FROZEN_SUBPERIOD_COLLAPSE","SOC2_EXACT_SCORE_2D_LATTICE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER")else 20.
   if sleeve in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"):a=.9956
   elif sleeve in("B4_TOUCHED_BARRIER_WICK_LOCK","TW1_COUNTING_TRUNCATION_AND_BOX","GAS1_AAA_GASOLINE_LOCK"):a=.99
   elif sleeve in("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","AFF1_FROZEN_SUBPERIOD_COLLAPSE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS"):a=.9881
   elif sleeve in("SP2_NBA_ENDGAME_LOCK","SOC2_EXACT_SCORE_2D_LATTICE"):a=.9861
   elif sleeve in("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"):a=.9821
   elif sleeve=="W1_LOW_TROUGH_LOCK":a=.9601
   else:a=.98
   o=float((extra or{}).get("fee_exponent",1.));g=BANKROLL_TICKETS["T1000"][sleeve];n=BANKROLL_TICKETS["T100"][sleeve];d=sleeve in DEPTH_CAPPED_TAKER_SLEEVES;t=(walk_l2_book_asks_depth_capped(m,g,n,fee_rate=fee_rate,min_l1_usd=q,max_ask_px=a,fee_exponent=o)if d else walk_l2_book_asks(m,g,fee_rate=fee_rate,min_l1_usd=q,max_ask_px=a,fee_exponent=o))
   if not t.get("filled"):return False
   c=p_model-float(t["eff_px"]);e={"W1_SOLAR_PEAK_LOCK":.035,"W1_LOW_TROUGH_LOCK":.03,"W2_ENSEMBLE_VALUE":.095,"B1_CONVEX_TAIL_YES":.06,"B2_BARRIER_NO_LOCK":.035,"M1_SVI_MAKER_SCALP":.05,"M2_STRIKE_CONVERGENCE":.038,"M4_SHOCK_STRIKE_CATCHUP":.065,"S5M_CHAINLINK_SNIPER":.042,"S4H_CHAINLINK_CONVERGENCE":.042,"U1_DAILY_UPDOWN_LOCK":.04,"S2_EXACT_TWAP_LOCK":.03,"B4_TOUCHED_BARRIER_WICK_LOCK":.012,"TW1_COUNTING_TRUNCATION_AND_BOX":.01,"GAS1_AAA_GASOLINE_LOCK":.015,"CM_SHOCK_PYTH_CATALYST":.045,"CM_B2_PYTH_SESSION_NO_LOCK":.035,"CM_U1_PYTH_CLOSE_LOCK":.03,"SP2_NBA_ENDGAME_LOCK":.012,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":.012,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":.012,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":.015,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":.012,"SOC2_EXACT_SCORE_2D_LATTICE":.012,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":.012,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":.0045,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":.018,"BOND1_UMA_RESOLUTION_CARRY":.0045,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":.004}.get(sleeve,.035)
   if c<e:return False
   f={}
   for i,s in BANKROLL_TICKETS.items():
    x=(walk_l2_book_asks_depth_capped(m,s[sleeve],n,fee_rate=fee_rate,min_l1_usd=q,max_ask_px=a,fee_exponent=o)if d else walk_l2_book_asks(m,s[sleeve],fee_rate=fee_rate,min_l1_usd=q,max_ask_px=a,fee_exponent=o))
    if x.get("filled"):f[i]=x
   if not f:return False
   w=time.time();p=f"{sleeve}_{int(w)}_{dedupe_key[-10:]}";b=tp_target_px
   if sleeve=="M1_SVI_MAKER_SCALP"and b is None:b=min(.96,round(float(t["eff_px"])+.05,4))
   elif sleeve=="M4_SHOCK_STRIKE_CATCHUP"and b is None:b=min(.96,round(float(t["eff_px"])+.06,4))
   elif sleeve=="B1_CONVEX_TAIL_YES"and b is None:b=min(.88,round(2.*float(t["vwap"]),4))
   elif sleeve=="S5M_CHAINLINK_SNIPER"and b is None:b=.96
   elif sleeve in("CM_B2_PYTH_SESSION_NO_LOCK","W1_LOW_TROUGH_LOCK")and b is None:b=.985
   elif sleeve in("W1_SOLAR_PEAK_LOCK","B2_BARRIER_NO_LOCK","M2_STRIKE_CONVERGENCE","U1_DAILY_UPDOWN_LOCK")and b is None:b=.98
   v={"position_id":p,"dedupe_key":dedupe_key,"sleeve":sleeve,"asset_or_city":asset_or_city,"title":title,"side":side_label,"token_id":token_id,"fee_rate":fee_rate,"entry_ts":w,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"p_model_entry":round(p_model,4),"entry_eff_px_t1000":t["eff_px"],"entry_vwap_t1000":t["vwap"],"realized_edge_t1000":round(c,4),"entry_best_bid":k,"last_bid":k,"maker_tp_px":b,"tier_fills":f,"extra":extra,"status":"OPEN"};self.open_positions[p]=v
   for r in y:self.entered_keys.add(r)
   self._append_ledger({"event":"SHADOW_ENTRY",**v});logger.info(f"[ENTRY:{sleeve}] {asset_or_city} | {title} ({side_label}) @ eff=${t['eff_px']:.3f} vs p_mod={p_model:.3f} (edge={c:+.3f}, L1=${t['l1_usd']:.0f})");return True
  finally:self._release_inflight_keys(y)
 async def post_shadow_maker_entry(self,sleeve,dedupe_key,asset,title,side_label,token_id,p_model,close_ts,extra,prefetched_book=None,ttl_override_sec=None):
  if is_shadow_sleeve_quarantined(sleeve):return False
  i=sleeve=="W2_MAKER_OVERROUND";l=sleeve=="MKR_REWARD_LOCKED_CARRY";k=sleeve in LOCKED_MAKER_SLEEVES;q=[dedupe_key]
  if i and extra.get("event_id"):q.append(f"W2M_EVENT_{extra['event_id']}")
  B=self._try_acquire_keys(*q)
  if not B:return False
  try:
   z=prefetched_book if prefetched_book is not None else await self.fetch_book_after_latency(token_id,latency_ms=50)
   if not z:return False
   asks_raw=z.get("asks")or[];v=z.get("bids")or[];u,n=extract_best_bid(v);m=[float(a["price"])for a in asks_raw if float(a.get("price",0))>0 and float(a.get("size",0))>0]
   if not m:
    if k or l:h=1.
    else:return False
   else:h=round(min(m),4)
   if h<=.03 or u<=.0:return False
   if i and((h-u)<.02 or n<10.):return False
   if k:
    if sleeve=="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":b,e,d,c=.95,.95,.996,.004
    elif sleeve=="BOND1_UMA_RESOLUTION_CARRY":b,e,d,c=.94,.94,.995,.005
    elif sleeve=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":b,e,d,c=.85,.9,.993,.0045
    elif sleeve in("SP2_NBA_ENDGAME_LOCK","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"):b,e,d,c=.7,.72,.985,.012
    elif sleeve=="W1_LOW_TROUGH_LOCK":b,e,d,c=.25,.35,.96,.03
    else:b,e,d,c=.25,.35,.94,.035
    if u<b:return False
    tb=.001 if u>=.96 else.01;ta=.001 if h>.96 else.01;p=(float(extra["resting_bid_override"])if extra.get("resting_bid_override")else(round(u+tb,4)if(h-u)>=(2.*tb-1e-9)else u));o=min(round(h-ta,4),d,round(p_model-c,4));w=.001 if min(p,o)>=.96-1e-9 else.01;f=round(math.floor((min(p,o)+1e-9)/w)*w,4)
    if f<round(u-1e-9,4)or not(e<=f<=d):return False
    g=p_model-f
    if g<c-1e-9:return False
   else:
    if l and extra.get("resting_bid_override"):f=round(min(float(extra["resting_bid_override"]),h-.005),4)
    else:t=u+.01 if(h-u)>=.02 else u;f=round(min(t,h-.01),4)
    e=.95 if l else(.14 if i else.18);d=.99 if l else(.65 if i else.8)
    if not(e<=f<=d):return False
    g=p_model-f;c=.008 if l else(.085 if i else.06)
    if g<c:return False
   j=.0 if f>u else round(min(n*.5,60.),2);A=time.time();s=f"MKR_{sleeve}_{int(A)}_{dedupe_key[-10:]}";r=self.spots.get(asset,.0);y={"order_id":s,"dedupe_key":dedupe_key,"sleeve":sleeve,"asset_or_city":asset,"title":title,"side":side_label,"token_id":token_id,"resting_bid":f,"best_bid_at_post":u,"best_ask_at_post":h,"l1_bid_usd":n,"queue_ahead_usd":j,"p_model_at_post":round(p_model,4),"maker_edge_at_post":round(g,4),"spot_at_post":r,"created_ts":A,"created_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"ttl_override_sec":ttl_override_sec,"extra":extra};self.pending_maker_orders[s]=y
   for x in B:self.entered_keys.add(x)
   self._append_ledger({"event":"SHADOW_MAKER_POST",**y});logger.info(f"[MAKER_POST:{sleeve}] {asset} | {title} ({side_label}) resting_bid=${f:.3f} (ask=${h:.3f}, q_ahead=${j:.0f}, p_mod={p_model:.3f}, edge={g:+.3f})");return True
  finally:self._release_inflight_keys(B)
 async def manage_pending_maker_orders(self):
  _y=time.time();_d=datetime.now(timezone.utc)
  for _x,_u in list(self.pending_maker_orders.items()):
   _k=_u["sleeve"];o=_k=="W2_MAKER_OVERROUND";r=_k=="MKR_REWARD_LOCKED_CARRY";q=_k in LOCKED_MAKER_SLEEVES;_t=_u["asset_or_city"];tok=_u["token_id"];resting_bid=float(_u["resting_bid"]);Z=float(_u["close_ts"]);_c=Z-_y;_s=_y-float(_u["created_ts"]);_r=dict(_u.get("extra")or{});_j=float(_r.get("strike")or.0);_b=bool(_r.get("is_downward"));Y=_u["side"];_a=(Y=="YES"and not _b)or(Y=="NO"and _b)
   def _discard_maker_keys(ord_obj):
    self.entered_keys.discard(ord_obj["dedupe_key"]);a=(ord_obj.get("extra")or{}).get("event_id")
    if a and ord_obj.get("sleeve")=="W2_MAKER_OVERROUND":self.entered_keys.discard(f"W2M_EVENT_{a}")
   _i=_u.get("ttl_override_sec")
   if _k in("SP2_NBA_ENDGAME_LOCK","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"):f=20.;e=float(_i)if _i is not None else 45.
   elif _k in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"):f=60. if _k=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"else 90.;e=float(_i)if _i is not None else 1800.
   elif _k in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"):f=6e2;e=float(_i)if _i is not None else 3600.
   else:f=6e2 if r else(9e2 if _i is not None else(3600. if o else 7200.));e=float(_i)if _i is not None else(7200. if r else(2700. if o else 1800.))
   if _c<=f or _s>=e:self.pending_maker_orders.pop(_x,None);_discard_maker_keys(_u);self._append_ledger({"event":"SHADOW_MAKER_CANCEL","reason":"TTL_OR_EXPIRY",**_u});continue
   b=None;d=float(_u["p_model_at_post"])
   if r:pass
   elif _k in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"):
    m=str(_r.get("event_id")or"");W=self.weather_events.get(m)
    if W is not None:
     K=f"{W.icao}_{W.obs_date.isoformat()}";n=(self.metar_cache.get(K)or(.0,[]))[1];J=(self.ensemble_cache.get(W.icao)or(.0,{}))[1];_q=(self.taf_cache.get(W.icao)or(.0,{}))[1]
     if n or J:
      I=compute_weather_probabilities(W,_d,n,J,forecast_sigma_base_c=self.weather_sigma_c,taf_extreme_c=(_q or{}).get(W.metric));j=str(_r.get("market_id")or"")
      for H,x in enumerate(W.buckets):
       if str(x.market_id)==j and H<len(I["probs"]):d=float(I["probs"][H]);break
      if I.get("convective_cold_pool"):b="CONVECTIVE_COLD_POOL"
      elif not I.get("is_solar_lock"):b="SOLAR_LOCK_INVALIDATED"
      elif(d-resting_bid)<.02:b="ADVERSE_METAR_OR_EDGE_DECAY"
   elif _k in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"):
    d=float(_u.get("p_model_at_post")or.998)if _k=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"else 1.;A=str(_r.get("opp_token_id")or"")
    if A and(_y-float(_u.get("_last_opp_chk_ts")or.0))>=12.:
     _u["_last_opp_chk_ts"]=_y;L=await self.fetch_json(f"{CLOB_URL}/book?token_id={A}",timeout=2.5)
     if L:
      y,_=extract_best_bid(L.get("bids")or[]);z=(.008 if _k=="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"else(.03 if _k=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"else.012))
      if y>z:b="UMA_COMPLEMENT_DISPUTE_BID"
   elif _k=="SP2_NBA_ENDGAME_LOCK":
    sp_nba_m=self.nba_games.get(str(_r.get("event_id")or""))
    if sp_nba_m is not None and self.live_nba_board:
     R=match_nba_live_game(sp_nba_m,self.live_nba_board)
     if R is not None:
      g_st_m,sc_a_m,sc_b_m=R;X=[c for c in evaluate_nba_endgame_locks(sp_nba_m,g_st_m,sc_a_m,sc_b_m)if c["leg"].token_id==tok]
      if not X:b="NBA_ENDGAME_LOCK_INVALIDATED"
      else:d=float(X[0]["p_lock"])
   elif o:
    m=str(_r.get("event_id")or"");W=self.weather_events.get(m)
    if W is not None:
     K=f"{W.icao}_{W.obs_date.isoformat()}";n=(self.metar_cache.get(K)or(.0,[]))[1];J=(self.ensemble_cache.get(W.icao)or(.0,{}))[1]
     if n or J:
      I=compute_weather_probabilities(W,_d,n,J,forecast_sigma_base_c=self.weather_sigma_c);j=str(_r.get("market_id")or"")
      for H,x in enumerate(W.buckets):
       if str(x.market_id)==j and H<len(I["probs"]):d=float(I["probs"][H]);break
      if I.get("convective_cold_pool"):b="CONVECTIVE_COLD_POOL"
      elif(d-resting_bid)<.045:b="ADVERSE_METAR_OR_EDGE_DECAY"
   else:
    V=self.spots.get(_t,.0);Q=float(_u.get("spot_at_post")or.0)
    if V>0 and _j>0:_h=evaluate_svi_digital_fair_value(_t,V,_j,_c,is_downward=_b,now_ts=_y);d=float(_h["p_yes"]if Y=="YES"else _h["p_no"])
    if V>0 and Q>0:
     U=((V-Q)/Q)*1e4
     if(_a and U<-20.)or((not _a)and U>20.):b="ADVERSE_SPOT_IMPULSE"
    if b is None and V>0 and _j>0 and(d-resting_bid)<.035:b="SVI_EDGE_DECAY"
   bk=None;g=False
   if b is not None:
    if _s>=.35:
     bk_adv=await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}",timeout=2.5)
     if bk_adv:
      T=[float(a["price"])for a in(bk_adv.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]
      if T and min(T)<=resting_bid:bk=bk_adv;g=True
    if not g:self.pending_maker_orders.pop(_x,None);_discard_maker_keys(_u);self._append_ledger({"event":"SHADOW_MAKER_CANCEL","reason":b,**_u});continue
   if not g:
    w=.5 if _i is not None else(4. if q else 10.)
    if _s<w:continue
    bk=await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}",timeout=3.)
   if not bk:continue
   asks_raw=bk.get("asks")or[];G=[float(a["price"])for a in asks_raw if float(a.get("price",0))>0 and float(a.get("size",0))>0];l=min(G)if G else 1.;i=(sum(float(a["size"])for a in asks_raw if.0<float(a.get("price",0))<=resting_bid+1e-9 and float(a.get("size",0))>0)if G and l<=resting_bid else.0)
   if i<=.0 and q:
    F=str(_r.get("condition_id")or"");v=float(self._last_trade_tape_chk_ts.get(F)or.0)
    if F and(_y-v)>=12.:
     self._last_trade_tape_chk_ts[F]=_y;E=await self.fetch_json(f"{DATA_API_URL}/trades?market={F}&limit=15",timeout=3.)
     if isinstance(E,list)and E:
      P=set(_u.get("_seen_trade_keys")or[]);D=str(_r.get("opp_token_id")or"");u=int(float(_u["created_ts"]))+2;t=.0
      for tr in E:
       _p=int(float(tr.get("timestamp")or 0))
       if _p<u:continue
       _v=f"{tr.get('transactionHash')or''}_{_p}_{tr.get('asset')or''}_{tr.get('size')or''}_{tr.get('price')or''}"
       if _v in P:continue
       _g=str(tr.get("asset")or"");_o=float(tr.get("price")or.0);_n=float(tr.get("size")or.0)
       if _n<=.0 or _o<=.0:continue
       if(_g==tok and _o<=resting_bid+1e-6)or(D and _g==D and _o>=(1.-resting_bid)-1e-6):P.add(_v);t+=_n
      if P:_u["_seen_trade_keys"]=list(P)[-30:]
      if t>.0:i=t;l=resting_bid;_r["filled_via_trade_tape"]=True
   if i>.0:
    p=float(_u.get("queue_ahead_usd")or.0);s=p/max(.01,resting_bid);h=i-s
    if g:h=max(h,i,BANKROLL_TICKETS["T5000"][_k]/max(.01,resting_bid))
    elif h<5.:_u["queue_ahead_usd"]=round(max(.0,p-i*resting_bid),2);continue
    self.pending_maker_orders.pop(_x,None);O=max(.0,float(_r.get("maker_rebate_ps")or.0));C=round(max(.01,resting_bid-O),6);B={}
    for N,_m in BANKROLL_TICKETS.items():S=_m[_k];M=S/resting_bid;sh=round(min(M,h),4);_l=round(sh*C,2);B[N]={"filled":True,"best_ask":round(l,4),"vwap":resting_bid,"eff_px":C,"slip_cents":.0,"spent_usd":_l,"fee_usd":round(-sh*O,4),"shares":sh,"fill_ratio":round(min(1.,_l/max(.01,S)),4),"l1_usd":_u.get("l1_bid_usd",50.),"levels":1}
    _f=f"{_k}_{int(_y)}_{_u['dedupe_key'][-10:]}"
    if q or r or _k in("BOND1_UMA_RESOLUTION_CARRY","SP2_NBA_ENDGAME_LOCK"):k=None
    elif _k in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"):k=.985
    elif o:k=min(.95,round(max(resting_bid+.07,d-.015),4))
    else:k=min(.96,round(resting_bid+.05,4))
    if g:_r["adverse_fill_during_cancel_window"]=True;_r["adverse_trigger"]=b
    _w={"position_id":_f,"dedupe_key":_u["dedupe_key"],"sleeve":_k,"asset_or_city":_t,"title":_u["title"],"side":Y,"token_id":tok,"fee_rate":.0,"entry_ts":_y,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":Z,"p_model_entry":round(d,4),"entry_eff_px_t1000":C,"entry_vwap_t1000":resting_bid,"realized_edge_t1000":round(d-C,4),"entry_best_bid":resting_bid,"last_bid":resting_bid,"maker_tp_px":k,"tier_fills":B,"extra":_r,"status":"OPEN"};self.open_positions[_f]=_w;self._append_ledger({"event":"SHADOW_ENTRY",**_w});_e=f"${k:.3f}"if k is not None else"HOLD_SETTLE";logger.info(f"[MAKER_FILLED:{_k}] {_t} | {_w['title']} ({Y}) @ resting=${resting_bid:.3f} -> TP={_e} (p_mod={d:.3f}, adverse={g})")
 async def scan_weather_markets(self,opps_out):
  _l=datetime.now(timezone.utc);_G=asyncio.get_running_loop()
  for sp in list(self.weather_events.values()):
   _D=time.time()
   try:f=datetime.fromisoformat(sp.end_date_iso.replace("Z","+00:00")).timestamp()
   except Exception:f=_D+86400.
   if f<=_D:self.weather_events.pop(sp.event_id,None);continue
   J=not self.single_scan and is_shadow_sleeve_quarantined("W2_ENSEMBLE_VALUE")and is_shadow_sleeve_quarantined("W2_MAKER_OVERROUND")
   if J:
    try:g=_l.astimezone(ZoneInfo(sp.tz_name))
    except Exception:g=_l
    _c=g.hour+g.minute/60.
    if sp.metric=="LOW":c=g.date()>sp.obs_date or(g.date()==sp.obs_date and _c>=9.25)
    else:c=g.date()>sp.obs_date or(g.date()==sp.obs_date and _c>=15.25)
   else:c=True
   if J and not c:_k=max(1,len(sp.buckets));probs=[round(1./_k,4)]*len(sp.buckets);_w={"is_solar_lock":False,"locked_bucket_idx":None,"p_locked_bucket":.0,"obs_count":0,"latest_temp_c":None,"running_ext_c":None,"peak_iqr_c":None,"cooling_cushion_c":.0,"convective_cold_pool":False,"probs":probs}
   else:
    _C=f"{sp.icao}_{sp.obs_date.isoformat()}";_b=self.metar_cache.get(_C);S=compute_adaptive_metar_poll_ttl(sp.icao,_b[1]if _b else None,_l)
    if _b is None or(_D-_b[0])>=S:r=await asyncio.to_thread(fetch_metar_observations_sync,sp.icao,sp.obs_date,sp.tz_name);self.metar_cache[_C]=(_D,r)
    else:r=_b[1]
    I=self.taf_cache.get(_C)
    if I is None or(_D-I[0])>=1800.:l=await asyncio.to_thread(fetch_taf_extremes_sync,sp.icao,sp.obs_date,sp.tz_name);self.taf_cache[_C]=(_D,l)
    else:l=I[1]
    _a=self.ensemble_cache.get(sp.icao);_j=1500. if(_a and _a[1])else 60.
    if _a is None or(_D-_a[0])>=_j:
     async with self._open_meteo_sem:H=await asyncio.to_thread(fetch_live_ensemble_hourly_sync,sp.lat,sp.lon);await asyncio.sleep(.18)
     self.ensemble_cache[sp.icao]=(_D,H)
    else:H=_a[1]
    if not H and not r:continue
    _w=compute_weather_probabilities(sp,_l,r,H,forecast_sigma_base_c=self.weather_sigma_c,taf_extreme_c=(l or{}).get(sp.metric));probs=_w["probs"]
   try:f=datetime.fromisoformat(sp.end_date_iso.replace("Z","+00:00")).timestamp()
   except Exception:f=_D+86400.
   if _w["is_solar_lock"]and _w["locked_bucket_idx"]is not None:
    _v=sp.buckets[_w["locked_bucket_idx"]];_u=_w["p_locked_bucket"];_t=float(getattr(_v,"fee_rate",.0)or.0);w=sp.metric=="LOW";R="W1_LOW_TROUGH_LOCK"if w else"W1_SOLAR_PEAK_LOCK";G=.96 if w else.94;v=.03 if w else.035;_i=f"W1LOW_{sp.event_id}_{_v.market_id}"if w else f"W1_{sp.event_id}_{_v.market_id}";bk=await self.fetch_json(f"{CLOB_URL}/book?token_id={_v.yes_token}",timeout=3.5)
    if bk:
     z=walk_l2_book_asks_depth_capped(bk.get("asks")or[],BANKROLL_TICKETS["T1000"][R],BANKROLL_TICKETS["T100"][R],fee_rate=_t,min_l1_usd=(15. if w else 20.),max_ask_px=G+1e-4);_s,F=extract_best_bid(bk.get("bids")or[]);self._record_market_telemetry(key=f"W1_LOCK_{sp.event_id}_{_v.market_id}",min_interval_sec=45.,now_ts=_D,sig=(z.get("eff_px"),_s,round(float(_u),3)),payload={"type":"WEATHER_SOLAR_LOCK_SNAP","sleeve":R,"event_id":sp.event_id,"city":sp.city,"icao":sp.icao,"metric":sp.metric,"obs_date":sp.obs_date.isoformat(),"bucket":_v.label,"obs_count":_w["obs_count"],"running_ext_c":_w["running_ext_c"],"cushion_c":_w["cooling_cushion_c"],"p_lock":_u,"ask_eff":z.get("eff_px")if z.get("filled")else None,"bid":_s if _s>0 else None,"l1_usd":z.get("l1_usd",.0)});Z={"event_id":sp.event_id,"market_id":_v.market_id,"condition_id":_v.condition_id,"opp_token_id":_v.no_token,"icao":sp.icao,"metric":sp.metric,"obs_date":sp.obs_date.isoformat(),"bucket_label":_v.label,"running_ext_c":_w["running_ext_c"],"cooling_cushion_c":_w["cooling_cushion_c"]};h=False
     if z.get("filled")and.52<=z["eff_px"]<=G:
      T=_u-z["eff_px"];opps_out.append({"sleeve":R,"market":f"{sp.city} ({sp.icao}) {sp.metric} {sp.obs_date} -> {_v.label}","ask_vwap":z["eff_px"],"p_model":_u,"net_edge":round(T,4),"l1_usd":z["l1_usd"]})
      if T>=v:
       _B=getattr(_v,"neg_risk",None)
       if float(_u)>=.985 and _B is not None and(f-_D)<=86400.:Q=await self.fetch_json(f"{CLOB_URL}/book?token_id={_v.no_token}",timeout=2.5);self.emit_live_single_leg_lock_candidate(sleeve_source=R,asset=f"{sp.city}_{sp.icao}",dedupe_key=_i,token_id=_v.yes_token,opp_token_id=_v.no_token,market_id=_v.market_id,condition_id=_v.condition_id,side_label="YES",display_label=f"{sp.city} {sp.metric} [{_v.label}]",bk_win=bk,bk_opp=Q if isinstance(Q,dict)else None,fee_rate=_t,fee_exponent=1.,neg_risk=bool(_B),close_ts=f,now_ts=_D,max_lock_eff_px=G,max_opp_bid=.045,hold_to_maturity=False,p_model=float(_u))
       h=await self.open_shadow_position(sleeve=R,dedupe_key=_i,asset_or_city=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_v.label}]",side_label="YES",token_id=_v.yes_token,fee_rate=_t,p_model=_u,close_ts=f,extra=Z,prefetched_book=bk)
     if(not h and not _w.get("convective_cold_pool")and(f-_D)>9e2 and.25<=_s<=G and(_u-_s)>=v):
      P=await self.post_shadow_maker_entry(sleeve=R,dedupe_key=_i,asset=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_v.label}]",side_label="YES",token_id=_v.yes_token,p_model=_u,close_ts=f,extra=Z,prefetched_book=bk)
      if P and not z.get("filled"):opps_out.append({"sleeve":R,"market":f"[MAKER] {sp.city} ({sp.icao}) {sp.metric} {sp.obs_date} -> {_v.label}","ask_vwap":_s,"p_model":_u,"net_edge":round(_u-_s,4),"l1_usd":F,"close_ts":f})
   O=f"W3_SLATE_{sp.event_id}";u=float(self._last_w3_slate_chk_ts.get(sp.event_id)or.0);t=45. if(sp.series_slug in HIGH_VOLUME_WEATHER_SERIES or(f-_D)<=21600.)else 120.
   if(O not in self.entered_keys and O not in self.inflight_keys and len(sp.buckets)>=3 and(self.single_scan or(_D-u)>=t)):
    self._last_w3_slate_chk_ts[sp.event_id]=_D;_r=[b_i.yes_token for b_i in sp.buckets]+[b_i.no_token for b_i in sp.buckets];Y=await self.fetch_books_batch(_r,timeout=3.);bucket_book_map={};raw_bk_by_mkt={}
    for b_i in sp.buckets:
     bk_i=Y.get(b_i.yes_token);bk_n_i=Y.get(b_i.no_token);_A={}
     if bk_i:
      raw_bk_by_mkt[b_i.market_id]=bk_i;_q=sorted([(float(a["price"]),float(a["size"]))for a in(bk_i.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
      if _q:_A["ask_yes"]=_q[0][0];_A["ask_yes_shares"]=_q[0][1]
     if bk_n_i:
      _p=sorted([(float(a["price"]),float(a["size"]))for a in(bk_n_i.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
      if _p:_A["ask_no"]=_p[0][0];_A["ask_no_shares"]=_p[0][1]
     if _A:bucket_book_map[b_i.market_id]=_A
     if bk_i and bk_n_i and float(getattr(b_i,"fee_rate",.0)or.0)==.0:
      _F=scan_binary_complete_set_arb(market_id=b_i.market_id,condition_id=b_i.condition_id,yes_token=b_i.yes_token,no_token=b_i.no_token,asks_yes_raw=bk_i.get("asks")or[],asks_no_raw=bk_n_i.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],fee_rate=.0,max_box_cost_net=.995)
      if _F.get("filled"):
       opps_out.append({"sleeve":"C1_BINARY_COMPLETE_SET","market":f"{sp.city} ({sp.icao}) Complete-Set [{b_i.label}]","ask_vwap":_F["box_cost_net"],"p_model":1.,"net_edge":_F["riskless_floor_per_pair"],"l1_usd":_F["l1_usd"],"close_ts":f});E=getattr(b_i,"neg_risk",None);_h={"token_id":b_i.yes_token,"opp_token_id":b_i.no_token,"condition_id":b_i.condition_id,"side":"YES","label":"YES","market_id":b_i.market_id,"fee_rate":.0,"strike":1e2,"neg_risk":bool(E)};_g={"token_id":b_i.no_token,"opp_token_id":b_i.yes_token,"condition_id":b_i.condition_id,"side":"NO","label":"NO","market_id":b_i.market_id,"fee_rate":.0,"strike":1e2,"neg_risk":bool(E)};await self.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key=f"C1_W_{b_i.market_id}",asset=f"{sp.city}_{sp.icao}",title=f"{sp.city} YES+NO Complete Set [{b_i.label}]",leg_a=_h,leg_b=_g,bk_a=bk_i,bk_b=bk_n_i,close_ts=f,max_box_cost_net=.995,extra={"is_complete_set":True,"market_id":b_i.market_id,"condition_id":b_i.condition_id})
       if E is not None and(f-_D)<=86400. and float(_F["box_cost_net"])<=.99:self.emit_live_two_leg_box_candidate(sleeve_source="C1_BINARY_COMPLETE_SET",box_type="COMPLETE_SET",asset=f"{sp.city}_{sp.icao}",dedupe_key=f"C1_W_{b_i.market_id}",leg_a=_h,leg_b=_g,bk_a=bk_i,bk_b=bk_n_i,close_ts=float(f),now_ts=_D)
    X=evaluate_weather_event_slate(sp,probs,bucket_book_map,target_budget_usd=BANKROLL_TICKETS["T1000"]["W3_WEATHER_SLATE_ARB"]);W=X.get("full_slate_arb")
    if len(bucket_book_map)==len(sp.buckets):N=all(bucket_book_map[b.market_id].get("ask_yes",0)>0 for b in sp.buckets);M=all(bucket_book_map[b.market_id].get("ask_no",0)>0 for b in sp.buckets);V=round(sum(float(bucket_book_map[b.market_id]["ask_yes"])for b in sp.buckets),4)if N else None;U=round(sum(float(bucket_book_map[b.market_id]["ask_no"])for b in sp.buckets),4)if M else None;_f=max(range(len(sp.buckets)),key=lambda idx_b:float(probs[idx_b]))if probs else 0;_e=sp.buckets[_f]if sp.buckets else None;L=float(bucket_book_map[_e.market_id].get("ask_yes")or.0)if _e else.0;self._record_market_telemetry(key=f"W_SLATE_{sp.event_id}",min_interval_sec=45. if(f-_D)<=7200. else 90.,now_ts=_D,sig=(V,U,_w["running_ext_c"],round(L,3),(W or{}).get("mode")),payload={"type":"WEATHER_SLATE","event_id":sp.event_id,"city":sp.city,"icao":sp.icao,"metric":sp.metric,"obs_date":sp.obs_date.isoformat(),"n_buckets":len(sp.buckets),"tte_sec":round(f-_D,0),"obs_count":_w["obs_count"],"latest_c":_w["latest_temp_c"],"running_ext_c":_w["running_ext_c"],"ens_iqr_c":_w["peak_iqr_c"],"solar_lock":_w["is_solar_lock"],"top_bucket":_e.label if _e else None,"top_p":round(float(probs[_f]),4)if probs else None,"top_ask_yes":round(L,4)if L>0 else None,"sum_yes_l1":V,"sum_no_l1":U,"no_payout":len(sp.buckets)-1,"arb_mode":(W or{}).get("mode")})
    if W:_E=float(W.get("guaranteed_payout_per_set")or 1.);opps_out.append({"sleeve":"W3_WEATHER_SLATE_ARB","market":f"{sp.city} ({sp.icao}) {sp.obs_date} Full-Slate ({len(sp.buckets)} buckets, {W.get('side','ALL_BUCKETS_YES')})","ask_vwap":round(float(W["sum_asks"])/_E,4),"p_model":1.,"net_edge":round(float(W["guaranteed_edge_per_set"])/_E,4),"l1_usd":W["total_cost_usd"]});await self.open_shadow_weather_slate(sp,W,f)
    if all(b.market_id in raw_bk_by_mkt for b in sp.buckets):await self.execute_ctf_overround_mint_sell(dedupe_key=f"CTF_OVR_W_{sp.event_id}",asset=f"{sp.city}_{sp.icao}",title=f"{sp.city} {sp.obs_date} Weather NegRisk Overround Mint-Sell",legs_bids_spec=[{"bids":raw_bk_by_mkt[b.market_id].get("bids")or[],"fee_rate":float(getattr(b,"fee_rate",.0)or.0),"fee_exponent":1.}for b in sp.buckets],close_ts=f,min_net_proceeds_per_set=1.004,opps_out=opps_out,extra={"overround_kind":"WEATHER_NEGRISK","event_id":sp.event_id})
   else:raw_bk_by_mkt={}
   if is_shadow_sleeve_quarantined("W2_ENSEMBLE_VALUE")and is_shadow_sleeve_quarantined("W2_MAKER_OVERROUND"):continue
   n=int(_w.get("ensemble_member_count")or 0);D=float(_w.get("peak_iqr_c")or.0);k=f"W2_EVENT_{sp.event_id}"in self.entered_keys or f"W2_EVENT_{sp.event_id}"in self.inflight_keys;j=f"W2M_EVENT_{sp.event_id}"in self.entered_keys or f"W2M_EVENT_{sp.event_id}"in self.inflight_keys;e=None;d=None;s=sorted(range(len(probs)),key=lambda i:-probs[i])[:2]
   for _H in s:
    _z=probs[_H]
    if _z<.24:continue
    b=sp.buckets[_H];_y=float(getattr(b,"fee_rate",.0)or.0);bk=raw_bk_by_mkt.get(b.market_id)or await self.fetch_json(f"{CLOB_URL}/book?token_id={b.yes_token}",timeout=3.5)
    if not bk:continue
    asks_raw_b=bk.get("asks")or[];C=bk.get("bids")or[];B,q=extract_best_bid(C);p=[float(a["price"])for a in asks_raw_b if float(a.get("price",0))>0 and float(a.get("size",0))>0]
    if _y==.0 and p and B>0 and(min(p)-B)>=.02:
     A=round(min(p),4);m=round(min(B+.01,A-.01),4);o=_z-m
     if.14<=m<=.65 and o>=.055 and n>=50 and q>=10.:opps_out.append({"sleeve":"W2_MAKER_OVERROUND","market":f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label} [MakerBid]","ask_vwap":m,"p_model":round(_z,4),"net_edge":round(o,4),"l1_usd":q})
     if(not k and not j and(f-_D)>=5400. and n>=50 and D<=2.2 and not _w.get("convective_cold_pool")and q>=10. and.14<=m<=.62 and _z>=.3 and o>=.085):
      if d is None or o>d[0]:d=(o,_z,m,b,bk)
    z=walk_l2_book_asks(asks_raw_b,50.,fee_rate=_y)
    if not z.get("filled"):continue
    _o=z["eff_px"];T=_z-_o
    if.1<=_o<=.62 and T>=.04 and n>=50:opps_out.append({"sleeve":"W2_ENSEMBLE_VALUE","market":f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label}","ask_vwap":_o,"p_model":round(_z,4),"net_edge":round(T,4),"l1_usd":z["l1_usd"]})
    if(not k and not j and n>=50 and D<=2.2 and not _w.get("convective_cold_pool")and.16<=_o<=.62 and _z>=.34 and T>=.095):
     if e is None or T>e[0]:e=(T,_z,_o,b,bk)
   if e is not None and os.getenv("PM_DISABLE_SHADOW_W2_TAKER","0")!="1":_,y,_,_n,_d=e;await self.open_shadow_position(sleeve="W2_ENSEMBLE_VALUE",dedupe_key=f"W2_{sp.event_id}_{_n.market_id}",asset_or_city=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_n.label}]",side_label="YES",token_id=_n.yes_token,fee_rate=float(getattr(_n,"fee_rate",.0)or.0),p_model=y,close_ts=f,extra={"event_id":sp.event_id,"market_id":_n.market_id,"condition_id":_n.condition_id,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket_label":_n.label,"bias_c":_w["bias_c"],"ensemble_members":n,"peak_iqr_c":D},prefetched_book=_d)
   elif d is not None:_,K,_,_x,_m=d;await self.post_shadow_maker_entry(sleeve="W2_MAKER_OVERROUND",dedupe_key=f"W2M_{sp.event_id}_{_x.market_id}",asset=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_x.label}]",side_label="YES",token_id=_x.yes_token,p_model=K,close_ts=f,extra={"execution_mode":"POST_ONLY_WEATHER_MAKER_ZERO_FEE","event_id":sp.event_id,"market_id":_x.market_id,"condition_id":_x.condition_id,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket_label":_x.label,"bias_c":_w["bias_c"],"ensemble_members":n,"peak_iqr_c":D},prefetched_book=_m)
 async def scan_barrier_markets(self,opps_out):
  X=time.time();R=asyncio.get_running_loop();k=collections.defaultdict(list)
  for r in self.barrier_rungs.values():
   if r.end_ts>X+300:k[r.event_id].append(r)
  for D,rungs in k.items():
   r0=rungs[0];Q=self.spots.get(r0.asset,.0)
   if Q<=0:continue
   a={};s=self.barrier_ext_cache.get(D)
   for z in sorted({int(r.start_ts//60)for r in rungs}):
    ck=f"{r0.asset}_{z}";d=self.barrier_ext_cache.get(ck)or s
    if d is None or(X-d[0])>=90.:
     p=await asyncio.to_thread(fetch_binance_window_extremes_sync,r0.asset,float(z*60),X,"1m")
     if p:self.barrier_ext_cache[ck]=(X,p)
     a[z]=p
    else:a[z]=d[1]
   touched_rungs=[]
   for r in rungs:
    if f"B4_{r.market_id}"in self.entered_keys:continue
    c=a.get(int(r.start_ts//60))
    if c is None:continue
    P,O=float(c[0]),float(c[1])
    if(r.direction=="UP"and P>=r.strike*1.0005)or(r.direction=="DOWN"and O<=r.strike*.9995):touched_rungs.append((r,P,O))
   if touched_rungs:
    y=await self.fetch_books_batch([rt[0].yes_token for rt in touched_rungs],timeout=2.5)
    for W,C,B in touched_rungs:
     A=y.get(W.yes_token)
     if not A:continue
     x,_=extract_best_bid(A.get("bids")or[]);N=walk_l2_book_asks(A.get("asks")or[],1e2,fee_rate=W.fee_rate,min_l1_usd=15.,max_ask_px=.99)
     if N.get("filled")and x>=.78 and.85<=float(N["eff_px"])<=.984:opps_out.append({"sleeve":"B4_TOUCHED_BARRIER_WICK_LOCK","market":f"{W.asset} Breached 1m Wick Lock: {W.question}","ask_vwap":N["eff_px"],"p_model":1.,"net_edge":round(1.-float(N["eff_px"]),4),"l1_usd":N["l1_usd"]});await self.open_shadow_position(sleeve="B4_TOUCHED_BARRIER_WICK_LOCK",dedupe_key=f"B4_{W.market_id}",asset_or_city=W.asset,title=W.question,side_label="YES",token_id=W.yes_token,fee_rate=W.fee_rate,p_model=1.,close_ts=W.end_ts,extra={"market_id":W.market_id,"condition_id":W.condition_id,"strike":W.strike,"direction":W.direction,"fin_high":C,"fin_low":B},prefetched_book=A)
   near_rungs=[]
   for r in rungs:
    if abs(math.log(r.strike/Q))>.14:continue
    c=a.get(int(r.start_ts//60));M=max(Q,c[0])if c else Q;L=min(Q,c[1])if c else Q
    if(r.direction=="UP"and M>=r.strike)or(r.direction=="DOWN"and L<=r.strike):continue
    near_rungs.append(r)
   w=r0.end_ts-X;j=(await self.fetch_books_batch([r.yes_token for r in near_rungs]+[r.no_token for r in near_rungs],timeout=3.)if near_rungs and w<=3*86400 else{});barrier_quote_rows=[]
   for r in near_rungs:
    V=r.end_ts-X;K,v=get_wing_implied_vol(r.asset,Q,r.strike,V);o=first_passage_touch_prob(Q,r.strike,V,K,r.direction,wick_vol_multiplier=self.barrier_wick_mult);f=j.get(r.yes_token);e=j.get(r.no_token)
    if f and e and V<=3*86400:J=walk_l2_book_asks(f.get("asks")or[],40.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);I=walk_l2_book_asks(e.get("asks")or[],40.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);barrier_quote_rows.append({"strike":r.strike,"direction":r.direction,"market_id":r.market_id,"condition_id":r.condition_id,"yes_token":r.yes_token,"no_token":r.no_token,"fee_rate":r.fee_rate,"fee_exponent":r.fee_exponent,"ask_yes":J.get("vwap")if J.get("filled")else None,"ask_no":I.get("vwap")if I.get("filled")else None,"bk_yes":f,"bk_no":e,"start_ts":r.start_ts,"end_ts":r.end_ts})
    if(self.single_scan or not is_shadow_sleeve_quarantined("B1_CONVEX_TAIL_YES"))and 7200<=V<=10*86400 and.07<=o<=.48:
     H=f or await self.fetch_json(f"{CLOB_URL}/book?token_id={r.yes_token}",timeout=3.)
     if H:
      U=walk_l2_book_asks(H.get("asks")or[],25.,fee_rate=CRYPTO_FEE_RATE)
      if U.get("filled")and.04<=U["vwap"]<=.32:
       u=o-U["eff_px"]
       if u>=.03:opps_out.append({"sleeve":"B1_CONVEX_TAIL_YES","market":f"{r.asset} {r.question}","ask_vwap":U["eff_px"],"p_model":round(o,4),"net_edge":round(u,4),"l1_usd":U["l1_usd"]})
       if u>=.12 and(o/U["eff_px"])>=1.75 and U["vwap"]<=.2:logger.info(f"[TELEMETRY_ONLY:B1_EXTREME_DISLOCATION] {r.asset} {r.question} ask={U['eff_px']:.3f} p={o:.3f}")
    G=1.-o
    if 3600<=V<=36000 and G>=.88:
     F=e or await self.fetch_json(f"{CLOB_URL}/book?token_id={r.no_token}",timeout=3.)
     if F:
      T=walk_l2_book_asks(F.get("asks")or[],1e2,fee_rate=CRYPTO_FEE_RATE)
      if T.get("filled")and.65<=T["vwap"]<=.91:
       t=G-T["eff_px"];n=evaluate_barrier_no_net_ev(o,T["vwap"],fee_rate=CRYPTO_FEE_RATE)
       if t>=.025:opps_out.append({"sleeve":"B2_BARRIER_NO_LOCK","market":f"{r.asset} NO: {r.question}","ask_vwap":T["eff_px"],"p_model":round(G,4),"net_edge":round(t,4),"l1_usd":T["l1_usd"]})
       if t>=.038 and n["eligible"]:await self.open_shadow_position(sleeve="B2_BARRIER_NO_LOCK",dedupe_key=f"B2_{r.market_id}",asset_or_city=r.asset,title=r.question,side_label="NO",token_id=r.no_token,fee_rate=CRYPTO_FEE_RATE,p_model=G,close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"start_ts":r.start_ts,"strike":r.strike,"direction":r.direction,"iv_wing":round(K,4),"loss_to_gain_ratio":n["loss_to_gain_ratio"]},prefetched_book=F)
   if len(barrier_quote_rows)>=2:
    b3_diag=detect_barrier_monotonicity_boxes(barrier_quote_rows,fee_rate=CRYPTO_FEE_RATE,max_box_cost_net=1.2)
    if b3_diag:S=b3_diag[0];self._record_market_telemetry(key=f"B3_DIAG_{D}",min_interval_sec=60.,now_ts=X,sig=(S["direction"],S["low_strike"],S["high_strike"],S["box_cost_gross"],S["box_cost_net"]),payload={"type":"BARRIER_MONO_BEST","asset":r0.asset,"event_id":D,"spot":Q,"direction":S["direction"],"low_strike":S["low_strike"],"high_strike":S["high_strike"],"gross_box_l1":S["box_cost_gross"],"net_box_l1":S["box_cost_net"]})
    m=[b for b in b3_diag if float(b["box_cost_net"])<=.995];i={str(q["yes_token"]):q for q in barrier_quote_rows};l={str(q["no_token"]):q for q in barrier_quote_rows}
    for ba in m:
     qy=i.get(ba["yes_token"]);qn=l.get(ba["no_token"])
     if not qy or not qn:continue
     E=walk_equal_shares_dominance_box(qy["bk_yes"].get("asks")or[],qn["bk_no"].get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["B3_BARRIER_MONO_BOX"],fee_rate_a=float(qy["fee_rate"]),fee_rate_b=float(qn["fee_rate"]),fee_exponent_a=float(qy.get("fee_exponent",1.)),fee_exponent_b=float(qn.get("fee_exponent",1.)),max_box_cost_net=.995,min_shares=6,min_box_notional_usd=5.5)
     if E.get("filled"):
      opps_out.append({"sleeve":"B3_BARRIER_MONO_BOX","market":f"{r0.asset} Barrier Box {ba['label']}","ask_vwap":round(float(E["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(E["box_cost_net"]),4),"l1_usd":E["l1_usd"],"close_ts":qy["end_ts"]});h={"token_id":ba["yes_token"],"opp_token_id":ba["yes_opp_token"],"condition_id":ba["leg_yes_condition_id"],"side":"YES","label":f"YES_{ba['direction']}","market_id":ba["leg_yes_market_id"],"fee_rate":float(qy["fee_rate"]),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(ba["low_strike"]if ba["direction"]=="UP"else ba["high_strike"])};g={"token_id":ba["no_token"],"opp_token_id":ba["no_opp_token"],"condition_id":ba["leg_no_condition_id"],"side":"NO","label":f"NO_{ba['direction']}","market_id":ba["leg_no_market_id"],"fee_rate":float(qn["fee_rate"]),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(ba["high_strike"]if ba["direction"]=="UP"else ba["low_strike"])};await self.open_shadow_two_leg_box(sleeve="B3_BARRIER_MONO_BOX",dedupe_key=f"B3_{r0.asset}_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",asset=r0.asset,title=f"{r0.asset} Barrier Box {ba['label']}",leg_a=h,leg_b=g,bk_a=qy["bk_yes"],bk_b=qn["bk_no"],close_ts=float(qy["end_ts"]),max_box_cost_net=.995,extra={"is_barrier_mono_box":True,"direction":ba["direction"],"low_strike":ba["low_strike"],"high_strike":ba["high_strike"]})
      if(float(qy["end_ts"])-X)<=86400. and float(E["box_cost_net"])<=.988:self.emit_live_two_leg_box_candidate(sleeve_source="B3_BARRIER_MONO_BOX",box_type="BARRIER_MONO",asset=r0.asset,dedupe_key=f"B3_{r0.asset}_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",leg_a=h,leg_b=g,bk_a=qy["bk_yes"],bk_b=qn["bk_no"],close_ts=float(qy["end_ts"]),now_ts=X,k_low=float(ba["low_strike"]),k_high=float(ba["high_strike"]))
 async def scan_multistrike_markets(self,opps_out):
  R=time.time()
  for i,rungs in list(self.strike_ladders.items()):
   if not rungs:continue
   A=rungs[0].asset;spot=self.spots.get(A,.0)
   if spot<=0:continue
   Q=rungs[0].end_ts-R
   if Q<=900:continue
   h=self.get_return_bps(A,60.);L=[r for r in rungs if abs(math.log(r.strike/spot))<=.08];d=(not self.single_scan and is_shadow_sleeve_quarantined("M1_SVI_MAKER_SCALP")and is_shadow_sleeve_quarantined("M2_STRIKE_CONVERGENCE"));f=({}if d else evaluate_coherent_strike_ladder(A,spot,L,Q,now_ts=R).get("by_market_id",{}));ladder_quotes=[]
   for sr in L:
    z=(None if d else(f.get(sr.market_id)or evaluate_svi_digital_fair_value(A,spot,sr.strike,Q,is_downward=sr.is_downward,now_ts=R)));K,J=await asyncio.gather(self.fetch_json(f"{CLOB_URL}/book?token_id={sr.yes_token}",timeout=3.),self.fetch_json(f"{CLOB_URL}/book?token_id={sr.no_token}",timeout=3.))
    if not K or not J:continue
    y=scan_binary_complete_set_arb(market_id=sr.market_id,condition_id=sr.condition_id,yes_token=sr.yes_token,no_token=sr.no_token,asks_yes_raw=K.get("asks")or[],asks_no_raw=J.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],fee_rate=CRYPTO_FEE_RATE)
    if y.get("filled"):
     opps_out.append({"sleeve":"C1_BINARY_COMPLETE_SET","market":f"{A} Complete-Set {sr.question}","ask_vwap":y["box_cost_net"],"p_model":1.,"net_edge":y["riskless_floor_per_pair"],"l1_usd":y["l1_usd"],"close_ts":sr.end_ts});o={"token_id":sr.yes_token,"opp_token_id":sr.no_token,"condition_id":sr.condition_id,"side":"YES","label":"YES","market_id":sr.market_id,"fee_rate":CRYPTO_FEE_RATE,"strike":float(sr.strike)};n={"token_id":sr.no_token,"opp_token_id":sr.yes_token,"condition_id":sr.condition_id,"side":"NO","label":"NO","market_id":sr.market_id,"fee_rate":CRYPTO_FEE_RATE,"strike":float(sr.strike)};await self.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key=f"C1_{sr.market_id}",asset=A,title=f"{A} YES+NO Complete Set: {sr.question}",leg_a=o,leg_b=n,bk_a=K,bk_b=J,close_ts=sr.end_ts,max_box_cost_net=.994,extra={"is_complete_set":True,"market_id":sr.market_id,"condition_id":sr.condition_id})
     if(sr.end_ts-R)<=86400. and float(y["box_cost_net"])<=.988:self.emit_live_two_leg_box_candidate(sleeve_source="C1_BINARY_COMPLETE_SET",box_type="COMPLETE_SET",asset=A,dedupe_key=f"C1_{sr.market_id}",leg_a=o,leg_b=n,bk_a=K,bk_b=J,close_ts=float(sr.end_ts),now_ts=R,k_low=float(sr.strike),k_high=float(sr.strike))
    P=walk_l2_book_asks(K.get("asks")or[],1e2,fee_rate=CRYPTO_FEE_RATE);O=walk_l2_book_asks(J.get("asks")or[],1e2,fee_rate=CRYPTO_FEE_RATE);ladder_quotes.append({"strike":sr.strike,"is_downward":sr.is_downward,"market_id":sr.market_id,"condition_id":sr.condition_id,"yes_token":sr.yes_token,"no_token":sr.no_token,"ask_yes":P.get("vwap")if P.get("filled")else None,"ask_no":O.get("vwap")if O.get("filled")else None,"asks_yes":K.get("asks")or[],"asks_no":J.get("asks")or[],"bk_yes":K,"bk_no":J,"end_ts":sr.end_ts})
    for m,N,w,v,s in([]if(z is None or(is_shadow_sleeve_quarantined("M1_SVI_MAKER_SCALP")and is_shadow_sleeve_quarantined("M2_STRIKE_CONVERGENCE")))else[("YES",sr.yes_token,P,z["p_yes"],K),("NO",sr.no_token,O,z["p_no"],J)]):
     if not w.get("filled"):continue
     u=w["eff_px"];I=v-u;p=(m=="YES"and not sr.is_downward)or(m=="NO"and sr.is_downward)
     if(p and h<-12.)or((not p)and h>12.):continue
     if.14<=u<=.9 and I>=.025:opps_out.append({"sleeve":"M1_OR_M2_STRIKE_SVI","market":f"{A} {sr.question} ({m})","ask_vwap":u,"p_model":v,"net_edge":round(I,4),"l1_usd":w["l1_usd"]})
     b=v-(float(w["best_ask"])-.01)
     if 10800<=Q<=86400 and.19<=w["best_ask"]<=.81 and b>=.06:await self.post_shadow_maker_entry(sleeve="M1_SVI_MAKER_SCALP",dedupe_key=f"M1_{sr.market_id}_{m}",asset=A,title=sr.question,side_label=m,token_id=N,p_model=v,close_ts=sr.end_ts,extra={"execution_mode":"POST_ONLY_MAKER_ZERO_FEE","market_id":sr.market_id,"condition_id":sr.condition_id,"strike":sr.strike,"is_downward":sr.is_downward,"iv_annual":z["iv_annual"],"z_sigma":z["z_sigma"]},prefetched_book=s)
     if(1200<=Q<=6300 and.68<=w["vwap"]<=.9 and z["z_sigma"]>=1.75 and v>=.93 and I>=.045):await self.open_shadow_position(sleeve="M2_STRIKE_CONVERGENCE",dedupe_key=f"M2_{sr.market_id}_{m}",asset_or_city=A,title=sr.question,side_label=m,token_id=N,fee_rate=CRYPTO_FEE_RATE,p_model=v,close_ts=sr.end_ts,extra={"market_id":sr.market_id,"condition_id":sr.condition_id,"strike":sr.strike,"is_downward":sr.is_downward,"iv_annual":z["iv_annual"],"z_sigma":z["z_sigma"]},prefetched_book=s)
   if len(ladder_quotes)>=2:
    H=sorted([q for q in ladder_quotes if not q.get("is_downward")],key=lambda x:x["strike"]);a=None
    for M in range(len(H)-1):
     G,F=float(H[M].get("ask_yes")or 1.),float(H[M+1].get("ask_no")or 1.)
     if 0<G<1. and 0<F<1.:
      E=G+F+CRYPTO_FEE_RATE*(G*(1.-G)+F*(1.-F))
      if a is None or E<a[0]:a=(round(E,4),round(G+F,4),float(H[M]["strike"]),float(H[M+1]["strike"]))
    if a is not None:self._record_market_telemetry(key=f"M3_DIAG_{i}",min_interval_sec=60.,now_ts=R,sig=a,payload={"type":"LADDER_MONO_BEST","asset":A,"ladder_key":i,"spot":spot,"tte_sec":round(Q,0),"low_strike":a[2],"high_strike":a[3],"gross_box_l1":a[1],"net_box_l1":a[0]})
   j=detect_ladder_monotonicity_boxes(ladder_quotes,fee_rate=CRYPTO_FEE_RATE);c={str(q["yes_token"]):q for q in ladder_quotes};e={str(q["no_token"]):q for q in ladder_quotes}
   for ma in j:
    D=c.get(str(ma.get("yes_token_low")or""));C=e.get(str(ma.get("no_token_high")or""))
    if not D or not C:continue
    B=walk_equal_shares_dominance_box(D.get("asks_yes")or[],C.get("asks_no")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["M3_LADDER_MONO_BOX"],fee_rate_a=CRYPTO_FEE_RATE,fee_rate_b=CRYPTO_FEE_RATE,max_box_cost_net=.996,min_shares=10,min_box_notional_usd=9.)
    if B.get("filled"):
     opps_out.append({"sleeve":"M3_LADDER_MONO_BOX","market":f"{A} Box YES>{ma['low_strike']} + NO>{ma['high_strike']}","ask_vwap":round(float(B["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(B["box_cost_net"]),4),"l1_usd":B["l1_usd"],"close_ts":D["end_ts"]});l={"token_id":ma["yes_token_low"],"opp_token_id":str(D["no_token"]),"condition_id":str(D.get("condition_id")or""),"side":"YES","label":f"YES>{ma['low_strike']}","market_id":ma["low_market_id"],"fee_rate":CRYPTO_FEE_RATE,"strike":float(ma["low_strike"])};k={"token_id":ma["no_token_high"],"opp_token_id":str(C["yes_token"]),"condition_id":str(C.get("condition_id")or""),"side":"NO","label":f"NO>{ma['high_strike']}","market_id":ma["high_market_id"],"fee_rate":CRYPTO_FEE_RATE,"strike":float(ma["high_strike"])};await self.open_shadow_two_leg_box(sleeve="M3_LADDER_MONO_BOX",dedupe_key=f"M3_{A}_{ma['low_market_id']}_{ma['high_market_id']}",asset=A,title=f"{A} Ladder Box YES>{ma['low_strike']} + NO>{ma['high_strike']}",leg_a=l,leg_b=k,bk_a=D["bk_yes"],bk_b=C["bk_no"],close_ts=float(D["end_ts"]),max_box_cost_net=.996,extra={"is_mono_box":True,"low_strike":ma["low_strike"],"high_strike":ma["high_strike"],"low_market_id":ma["low_market_id"],"high_market_id":ma["high_market_id"]})
     if(float(D["end_ts"])-R)<=86400. and float(B["box_cost_net"])<=.988:self.emit_live_two_leg_box_candidate(sleeve_source="M3_LADDER_MONO_BOX",box_type="LADDER_MONO",asset=A,dedupe_key=f"M3_{A}_{ma['low_market_id']}_{ma['high_market_id']}",leg_a=l,leg_b=k,bk_a=D["bk_yes"],bk_b=C["bk_no"],close_ts=float(D["end_ts"]),now_ts=R,k_low=float(ma["low_strike"]),k_high=float(ma["high_strike"]))
   t=f"{A}_{int(rungs[0].end_ts)}";g=self.negrisk_ladders.get(t)or[]
   if g:await self._scan_negrisk_bundles_for_ladder(asset=A,spot=spot,rungs=rungs,nr_brackets=g,ms_book_cache={**{str(q["yes_token"]):q["bk_yes"]for q in ladder_quotes},**{str(q["no_token"]):q["bk_no"]for q in ladder_quotes}},opps_out=opps_out)
 async def _scan_negrisk_bundles_for_ladder(self,asset,spot,rungs,nr_brackets,ms_book_cache,opps_out):
  bundles=build_negrisk_cross_box_bundles(rungs,nr_brackets,spot=spot,max_strike_dist_log=.1,tail_max_strike_dist_log=.22)
  if not bundles:return
  local_bk_cache=dict(ms_book_cache);b=sorted({str(lg["token_id"])for bnd in bundles for lg in bnd["legs"]if str(lg["token_id"])not in local_bk_cache})
  if b:local_bk_cache.update(await self.fetch_books_batch(b,timeout=3.))
  a=None
  for bnd in bundles:
   legs=bnd["legs"]
   if not all(str(lg["token_id"])in local_bk_cache for lg in legs):continue
   gp=float(bnd["guaranteed_payout"]);g=round(gp*.992,4);d=[{"asks":local_bk_cache[str(lg["token_id"])].get("asks")or[],"fee_rate":float(lg.get("fee_rate",CRYPTO_FEE_RATE)),"fee_exponent":1.}for lg in legs];i=sum(p0+float(lg.get("fee_rate",CRYPTO_FEE_RATE))*p0*(1.-p0)for lg in legs for p0 in[self._best_ask_sz(local_bk_cache[str(lg["token_id"])])[0]]);f=round(i/max(1.,gp),4)
   if f<=1.15 and(a is None or f<a[0]):a=(f,str(bnd["label"]),gp,float(bnd["end_ts"]))
   l=walk_equal_shares_multi_leg_box(d,target_budget_usd=BANKROLL_TICKETS["T1000"]["N1_NEGRISK_CROSS_BOX"],guaranteed_payout_per_bundle=gp,max_bundle_cost_net=round(gp*1.005,4),min_shares=6,min_box_notional_usd=5.5)
   if not l.get("filled"):continue
   e=float(l["box_cost_net"]);c=round(gp-e,4);opps_out.append({"sleeve":"N1_NEGRISK_CROSS_BOX","market":f"{asset} {bnd['label']}","ask_vwap":round(e/gp,4),"p_model":1.,"net_edge":round(c/gp,4),"l1_usd":l["l1_usd"],"close_ts":bnd["end_ts"]})
   if e<=g:
    await self.open_shadow_multi_leg_bundle(sleeve="N1_NEGRISK_CROSS_BOX",dedupe_key=f"N1_{asset}_{bnd['bundle_id']}",asset=asset,title=f"{asset} NegRisk Cross-Box: {bnd['label']}",legs=legs,books_by_token=local_bk_cache,close_ts=float(bnd["end_ts"]),guaranteed_payout=gp,max_bundle_cost_net=g,extra={"is_multi_leg_bundle":True,"bundle_id":bnd["bundle_id"],"guaranteed_payout":gp,"legs":legs});h=time.time()
    if len(legs)==2 and gp==1. and e<=.988 and(float(bnd["end_ts"])-h)<=172800.:k=float(legs[0].get("strike")or spot or 1e2);self.emit_live_two_leg_box_candidate(sleeve_source="N1_NEGRISK_CROSS_BOX",box_type="NEGRISK_2LEG",asset=asset,dedupe_key=f"N1_{asset}_{bnd['bundle_id']}",leg_a=legs[0],leg_b=legs[1],bk_a=local_bk_cache[str(legs[0]["token_id"])],bk_b=local_bk_cache[str(legs[1]["token_id"])],close_ts=float(bnd["end_ts"]),now_ts=h,k_low=k,k_high=k)
  if a is not None:j=time.time();self._record_market_telemetry(key=f"N1_BEST_{asset}_{int(a[3])}",min_interval_sec=90.,now_ts=j,sig=(a[0],a[1]),payload={"type":"NEGRISK_CRYPTO_CROSS_BEST","asset":asset,"spot":round(spot,4),"tte_sec":round(a[3]-j,0),"payout":a[2],"net_bundle_ratio_l1":a[0],"label":a[1]})
 async def open_shadow_multi_leg_bundle(self,sleeve,dedupe_key,asset,title,legs,books_by_token,close_ts,guaranteed_payout,max_bundle_cost_net,extra):
  l=self._try_acquire_keys(dedupe_key)
  if not l:return False
  try:
   c=[{"asks":books_by_token[str(lg["token_id"])].get("asks")or[],"fee_rate":float(lg.get("fee_rate",CRYPTO_FEE_RATE)),"fee_exponent":float(lg.get("fee_exponent",1.))}for lg in legs];d=sum(extract_best_bid(books_by_token[str(lg["token_id"])].get("bids")or[])[0]for lg in legs);a={}
   for b,h in BANKROLL_TICKETS.items():
    k=walk_equal_shares_multi_leg_box(c,target_budget_usd=h[sleeve],guaranteed_payout_per_bundle=guaranteed_payout,max_bundle_cost_net=max_bundle_cost_net,min_shares=6 if b=="T100"else 8,min_box_notional_usd=7. if b=="T100"else 9.)
    if k.get("filled"):a[b]=k
   if"T1000"not in a:return False
   g=a["T1000"];j=time.time();e=f"{sleeve}_{int(j)}_{dedupe_key[-10:]}";i={"position_id":e,"dedupe_key":dedupe_key,"sleeve":sleeve,"asset_or_city":asset,"title":title,"side":"+".join(str(lg.get("label",lg.get("side","YES")))for lg in legs),"token_id":"|".join(str(lg["token_id"])for lg in legs),"fee_rate":max((float(lg.get("fee_rate",CRYPTO_FEE_RATE))for lg in legs),default=CRYPTO_FEE_RATE),"entry_ts":j,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"p_model_entry":round(guaranteed_payout,4),"entry_eff_px_t1000":g["eff_px"],"entry_vwap_t1000":g["vwap"],"realized_edge_t1000":g["riskless_floor_per_pair"],"entry_best_bid":round(d,4),"last_bid":round(d,4),"maker_tp_px":None,"tier_fills":a,"extra":{**extra,"legs":legs},"status":"OPEN"};self.open_positions[e]=i
   for f in l:self.entered_keys.add(f)
   self._append_ledger({"event":"SHADOW_ENTRY",**i});logger.info(f"[ENTRY:{sleeve}] {title} | {g['shares']} bundles @ net=${g['eff_px']:.4f} (guaranteed=${guaranteed_payout:.2f}, floor=${g['riskless_floor_per_pair']:+.4f}/bundle)");return True
  finally:self._release_inflight_keys(l)
 async def execute_ctf_overround_mint_sell(self,dedupe_key,asset,title,legs_bids_spec,close_ts,min_net_proceeds_per_set,opps_out,extra):
  if is_shadow_sleeve_quarantined("CTF_OVERROUND_MINT_SELL"):return False
  c=walk_equal_shares_overround_bids(legs_bids_spec,target_mint_budget_usd=BANKROLL_TICKETS["T1000"]["CTF_OVERROUND_MINT_SELL"],min_net_proceeds_per_set=min_net_proceeds_per_set,min_shares=8.)
  if not c.get("filled"):return False
  opps_out.append({"sleeve":"CTF_OVERROUND_MINT_SELL","market":title,"ask_vwap":round(2.-float(c["net_proceeds_per_set"]),4),"p_model":1.,"net_edge":c["net_edge_per_set"],"l1_usd":c["l1_usd"],"close_ts":close_ts});k=self._try_acquire_keys(dedupe_key)
  if not k:return False
  try:
   a={};b={}
   for e,g in BANKROLL_TICKETS.items():
    wt=walk_equal_shares_overround_bids(legs_bids_spec,target_mint_budget_usd=g["CTF_OVERROUND_MINT_SELL"],min_net_proceeds_per_set=min_net_proceeds_per_set,min_shares=5. if e=="T100"else 8.)
    if wt.get("filled"):h=float(wt["shares"]);a[e]={"filled":True,"vwap":1.,"eff_px":1.,"spent_usd":round(h,2),"fee_usd":wt["fee_usd"],"shares":h,"l1_usd":wt["l1_usd"]};b[e]=round(h*float(wt["net_edge_per_set"]),2)
   if"T1000"not in a:return False
   j=time.time();d=f"CTF_OVERROUND_MINT_SELL_{int(j)}_{dedupe_key[-10:]}";i={"position_id":d,"dedupe_key":dedupe_key,"sleeve":"CTF_OVERROUND_MINT_SELL","asset_or_city":asset,"title":title,"side":f"MINT_SELL_{len(legs_bids_spec)}L","token_id":dedupe_key,"fee_rate":.0,"entry_ts":j,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"closed_ts":j,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":round(float(c["net_proceeds_per_set"]),4),"entry_eff_px_t1000":1.,"entry_vwap_t1000":1.,"realized_edge_t1000":c["net_edge_per_set"],"net_payout_per_share":c["gross_proceeds_per_set"],"tier_fills":a,"tier_pnls_usd":b,"legging_adjusted_tier_pnls_usd":b,"won":b.get("T1000",.0)>0,"extra":{**extra,"n_legs":len(legs_bids_spec)},"status":"INSTANT_MINT_AND_SELL_FILLED"}
   for f in k:self.entered_keys.add(f)
   self._append_ledger({"event":"SHADOW_ENTRY",**i});self.closed_positions.append(i);self._append_ledger({"event":"SHADOW_CLOSE",**i});logger.info(f"[INSTANT_ARB:CTF_OVERROUND_MINT_SELL] {title} | net_proceeds=${c['net_proceeds_per_set']:.4f} (+{c['net_edge_per_set']:.4f}/set) | PnL T1000=${b.get('T1000',.0):+.2f}");return True
  finally:self._release_inflight_keys(k)
 async def execute_negrisk_convert_positions_arb(self,spec,arb_probe,books_by_token,opps_out):
  if is_shadow_sleeve_quarantined("NR_CONV_NO_BASKET_ARB")or not spec.is_closed_convert_safe:return False
  p=int(arb_probe["m_no_legs"]);h="_".join(str(i)for i in arb_probe["question_indices"]);d=f"NRCONV_M{p}_{spec.event_id}_{h}";opps_out.append({"sleeve":"NR_CONV_NO_BASKET_ARB","market":f"{spec.title} [convertPositions {p}/{spec.total_market_count} NO -> {p-1} USDC + YES bids]","ask_vwap":round(1.-float(arb_probe["net_edge_per_share"]),4),"p_model":1.,"net_edge":arb_probe["net_edge_per_share"],"l1_usd":arb_probe["l1_usd"],"close_ts":spec.end_ts});u=self._try_acquire_keys(d)
  if not u:return False
  try:
   await asyncio.sleep(.25);req_toks=[b["no_token"]for b in spec.brackets]+[b["yes_token"]for b in spec.brackets];fresh_bks=await self.fetch_books_batch(req_toks,timeout=3.);f=fresh_bks if all(t in fresh_bks for t in req_toks)else books_by_token;a={};e={};best_t1000=None
   for l,o in BANKROLL_TICKETS.items():
    cands_t=detect_negrisk_convert_positions_arbs(spec,f,target_budget_usd=o["NR_CONV_NO_BASKET_ARB"],min_net_edge_per_share=.005,min_shares=5 if l=="T100"else 8);n=next((c for c in cands_t if c["question_indices"]==arb_probe["question_indices"]),None)
    if n is not None:
     q=float(n["shares"]);g=float(n["no_cost_per_share"]);a[l]={"filled":True,"vwap":g,"eff_px":g,"spent_usd":round(q*g,2),"fee_usd":float(n.get("total_fee_usd",.0)),"shares":q,"l1_usd":n["l1_usd"]};e[l]=round(q*float(n["net_edge_per_share"]),2)
     if l=="T1000":best_t1000=n
   if best_t1000 is None:return False
   s=time.time();k=f"NR_CONV_NO_BASKET_ARB_{int(s)}_{d[-10:]}";j=round(float(best_t1000["net_proceeds_per_share"]),4);r={"position_id":k,"dedupe_key":d,"sleeve":"NR_CONV_NO_BASKET_ARB","asset_or_city":"NEGRISK","title":f"{spec.title} [convertPositions m={p}/{spec.total_market_count}]","side":f"CONVERT_{p}NO","token_id":"|".join(str(x["bracket"]["no_token"])for x in best_t1000["no_legs"]),"fee_rate":.0,"entry_ts":s,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":spec.end_ts,"closed_ts":s,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":j,"entry_eff_px_t1000":best_t1000["no_cost_per_share"],"entry_vwap_t1000":best_t1000["no_cost_per_share"],"realized_edge_t1000":best_t1000["net_edge_per_share"],"net_payout_per_share":j,"tier_fills":a,"tier_pnls_usd":e,"legging_adjusted_tier_pnls_usd":e,"won":e.get("T1000",.0)>0,"extra":{"mode":"NR_CONVERT_POSITIONS","neg_risk_market_id":spec.neg_risk_market_id,"index_set_int":best_t1000["index_set"],"no_question_indices":best_t1000["question_indices"],"m_no_legs":p,"n_total":spec.total_market_count},"status":"INSTANT_CONVERT_AND_SELL_FILLED"}
   for m in u:self.entered_keys.add(m)
   self.emit_live_negrisk_convert_candidate(sleeve_source="NR_CONV_NO_BASKET_ARB",spec=spec,dedupe_key=d,arb_hit=best_t1000,books_by_token=f,now_ts=s,fee_bips=0);self._append_ledger({"event":"SHADOW_ENTRY",**r});self.closed_positions.append(r);self._append_ledger({"event":"SHADOW_CLOSE",**r});logger.info(f"[INSTANT_ARB:NR_CONV_NO_BASKET_ARB] {r['title']} | edge=+{best_t1000['net_edge_per_set']:.4f}/set | PnL T1000=${e.get('T1000',.0):+.2f}");return True
  finally:self._release_inflight_keys(u)
 async def execute_nr2_subset_convert_arb(self,spec,arb_probe,books_by_token,opps_out):
  if is_shadow_sleeve_quarantined("NR2_CONVERT_NO_SUBSET_ARB")or not spec.is_closed_convert_safe:return False
  r=int(arb_probe["m_no_legs"]);j="_".join(str(i)for i in arb_probe["no_question_indices"]);d=f"NR2_M{r}_{spec.event_id}_{j}";opps_out.append({"sleeve":"NR2_CONVERT_NO_SUBSET_ARB","market":f"{spec.title[:52]} [{arb_probe['label']}]","ask_vwap":round(max(.01,1.-float(arb_probe["net_edge_per_share"])),4),"p_model":1.,"net_edge":arb_probe["net_edge_per_share"],"l1_usd":arb_probe["l1_usd"],"close_ts":spec.end_ts});w=self._try_acquire_keys(d)
  if not w:return False
  try:
   q,g,_=await asyncio.to_thread(verify_negrisk_adapter_slate_sync,spec.neg_risk_market_id,spec.total_market_count)
   if not q:return False
   await asyncio.sleep(.25);req_toks=[b["no_token"]for b in spec.brackets]+[b["yes_token"]for b in spec.brackets];fresh_bks=await self.fetch_books_batch(req_toks,timeout=3.);f=fresh_bks if all(t in fresh_bks for t in req_toks)else books_by_token;a={};e={};best_t1000=None
   for m,p in BANKROLL_TICKETS.items():
    cands_t=detect_nr2_convert_no_subset_arbs(spec,f,target_budget_usd=p["NR2_CONVERT_NO_SUBSET_ARB"],min_edge_pure_cash=.01,min_edge_with_yes_sell=.012,min_shares=5 if m=="T100"else 6,fee_bips=g);o=next((c for c in cands_t if c["no_question_indices"]==arb_probe["no_question_indices"]),None)
    if o is not None:
     s=float(o["shares"]);h=float(o["no_cost_per_share"]);a[m]={"filled":True,"vwap":h,"eff_px":h,"spent_usd":round(s*h,2),"fee_usd":o["total_fee_usd"],"shares":s,"l1_usd":o["l1_usd"]};e[m]=float(o["total_net_profit_usd"])
     if m=="T1000":best_t1000=o
   if best_t1000 is None:return False
   v=time.time();l=f"NR2_CONVERT_NO_SUBSET_ARB_{int(v)}_{d[-10:]}";k=float(best_t1000["net_proceeds_per_share"]);u={"position_id":l,"dedupe_key":d,"sleeve":"NR2_CONVERT_NO_SUBSET_ARB","asset_or_city":"NEGRISK_V2","title":f"{spec.title} [{best_t1000['label']}]","side":f"NR2_{r}NO_FREE{best_t1000['retained_tail_count']}Y","token_id":"|".join(str(x["token_id"])for x in best_t1000["no_legs"]),"fee_rate":.0,"entry_ts":v,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":spec.end_ts,"closed_ts":v,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":k,"entry_eff_px_t1000":best_t1000["no_cost_per_share"],"entry_vwap_t1000":best_t1000["no_cost_per_share"],"realized_edge_t1000":best_t1000["net_edge_per_share"],"net_payout_per_share":k,"tier_fills":a,"tier_pnls_usd":e,"legging_adjusted_tier_pnls_usd":e,"won":e.get("T1000",.0)>0,"extra":{"mode":best_t1000["mode"],"neg_risk_market_id":spec.neg_risk_market_id,"index_set_int":best_t1000["index_set_int"],"no_question_indices":best_t1000["no_question_indices"],"retained_tail_count":best_t1000["retained_tail_count"],"retained_tail_labels":[b["label"]for b in best_t1000["retained_free_yes_brackets"]],"fee_bips":g},"status":"INSTANT_SUBSET_CONVERT_FREE_TAIL_LOCKED"}
   for n in w:self.entered_keys.add(n)
   self.emit_live_negrisk_convert_candidate(sleeve_source="NR2_CONVERT_NO_SUBSET_ARB",spec=spec,dedupe_key=d,arb_hit=best_t1000,books_by_token=f,now_ts=v,fee_bips=g);self._append_ledger({"event":"SHADOW_ENTRY",**u});self.closed_positions.append(u);self._append_ledger({"event":"SHADOW_CLOSE",**u});logger.info(f"[INSTANT_ARB:NR2_CONVERT_NO_SUBSET_ARB] {u['title']} | edge=+{best_t1000['net_edge_per_share']:.4f}/sh | free_tails={best_t1000['retained_tail_count']} | PnL T1000=${e.get('T1000',.0):+.2f}");return True
  finally:self._release_inflight_keys(w)
 async def scan_daily_updown_locks(self,opps_out):
  now=time.time();V=asyncio.get_running_loop();c1_daily_specs=[sp for sp in[*self.daily_updown_markets.values(),*self.pyth_daily_markets.values()]if sp.end_ts>now+60.]
  if c1_daily_specs:
   w=await self.fetch_books_batch([sp.up_token for sp in c1_daily_specs]+[sp.down_token for sp in c1_daily_specs],timeout=3.)
   for F in c1_daily_specs:
    U=w.get(F.up_token);T=w.get(F.down_token)
    if not U or not T:continue
    S,R=self._best_ask_sz(U);Q,P=self._best_ask_sz(T)
    if S<1. and Q<1.:_c=float(F.fee_rate);self._record_market_telemetry(key=f"DAILY_C1_{F.market_id}",min_interval_sec=60.,now_ts=now,sig=(S,Q),payload={"type":"DAILY_COMPLETE_SET","asset":F.asset,"market_id":F.market_id,"title":F.title,"fee_rate":_c,"tte_sec":round(F.end_ts-now,0),"up_ask":S,"down_ask":Q,"gross_sum_l1":round(S+Q,4),"net_sum_l1":round(S+Q+_c*(S*(1.-S)+Q*(1.-Q)),4),"l1_min_shares":round(min(R,P),2)})
    v=.995 if F.fee_rate==.0 else.994;u=scan_binary_complete_set_arb(market_id=F.market_id,condition_id=F.condition_id,yes_token=F.up_token,no_token=F.down_token,asks_yes_raw=U.get("asks")or[],asks_no_raw=T.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],fee_rate=F.fee_rate,max_box_cost_net=v)
    if u.get("filled"):
     opps_out.append({"sleeve":"C1_BINARY_COMPLETE_SET","market":f"{F.asset} Complete-Set {F.title}","ask_vwap":u["box_cost_net"],"p_model":1.,"net_edge":u["riskless_floor_per_pair"],"l1_usd":u["l1_usd"],"close_ts":F.end_ts});E={"token_id":F.up_token,"opp_token_id":F.down_token,"condition_id":F.condition_id,"side":"UP","label":"UP","market_id":F.market_id,"fee_rate":F.fee_rate,"strike":1e2};D={"token_id":F.down_token,"opp_token_id":F.up_token,"condition_id":F.condition_id,"side":"DOWN","label":"DOWN","market_id":F.market_id,"fee_rate":F.fee_rate,"strike":1e2};await self.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key=f"C1_D_{F.market_id}",asset=F.asset,title=f"{F.asset} UP+DOWN Complete Set: {F.title}",leg_a=E,leg_b=D,bk_a=U,bk_b=T,close_ts=F.end_ts,max_box_cost_net=v,extra={"is_complete_set":True,"market_id":F.market_id,"condition_id":F.condition_id})
     if(F.end_ts-now)<=86400. and float(u["box_cost_net"])<=(.99 if F.fee_rate==.0 else.988):self.emit_live_two_leg_box_candidate(sleeve_source="C1_BINARY_COMPLETE_SET",box_type="COMPLETE_SET",asset=F.asset,dedupe_key=f"C1_D_{F.market_id}",leg_a=E,leg_b=D,bk_a=U,bk_b=T,close_ts=float(F.end_ts),now_ts=now)
    await self.execute_ctf_overround_mint_sell(dedupe_key=f"CTF_OVR_D_{F.market_id}",asset=F.asset,title=f"{F.asset} Binary Overround Mint-Sell: {F.title}",legs_bids_spec=[{"bids":U.get("bids")or[],"fee_rate":F.fee_rate,"fee_exponent":1.},{"bids":T.get("bids")or[],"fee_rate":F.fee_rate,"fee_exponent":1.}],close_ts=F.end_ts,min_net_proceeds_per_set=1.003 if F.fee_rate==.0 else 1.004,opps_out=opps_out,extra={"overround_kind":"BINARY_DAILY","market_id":F.market_id,"condition_id":F.condition_id})
  for _,O in list(self.hourly_12pm_markets.items()):
   C=O.end_ts-now
   if not(60.<=C<=3540.)or now<O.start_ts+20.:continue
   t=f"H1_{O.asset}_{int(O.start_ts)}";N=self.daily_open_cache.get(t)
   if N is None:
    s=await V.run_in_executor(None,fetch_binance_window_extremes_sync,O.asset,O.start_ts-60.,O.start_ts+60.,"1m")
    if s is not None and s[2]>0:self.daily_open_cache[t]=(O.end_ts,float(s[2]));j=float(s[2])
    else:continue
   else:j=N[1]
   d=[]
   for M in self.daily_updown_markets.values():
    if M.asset==O.asset and abs(M.end_ts-O.end_ts)<=5.:
     r=f"{M.asset}_{int(M.start_ts)}";L=self.daily_open_cache.get(r)
     if L is None:
      q=await V.run_in_executor(None,fetch_binance_window_extremes_sync,M.asset,M.start_ts-60.,M.start_ts+60.,"1m")
      if q is not None and q[2]>0:self.daily_open_cache[r]=(M.end_ts,float(q[2]));f=float(q[2])
      else:f=.0
     else:f=L[1]
     if f>0:d.append({"market_id":M.market_id,"condition_id":M.condition_id,"end_ts":M.end_ts,"strike":f,"is_downward":False,"yes_token":M.up_token,"no_token":M.down_token,"yes_label":"UP","no_label":"DOWN","fee_rate":M.fee_rate})
   for i in self.strike_ladders.values():
    if i and i[0].asset==O.asset and abs(i[0].end_ts-O.end_ts)<=5.:
     for B in i:
      if not B.is_downward:d.append({"market_id":B.market_id,"condition_id":B.condition_id,"end_ts":B.end_ts,"strike":B.strike,"is_downward":False,"yes_token":B.yes_token,"no_token":B.no_token,"yes_label":"YES","no_label":"NO","fee_rate":CRYPTO_FEE_RATE})
   d2_cands=detect_d2_12pm_binance_boxes({"asset":O.asset,"market_id":O.market_id,"condition_id":O.condition_id,"end_ts":O.end_ts,"up_token":O.up_token,"down_token":O.down_token,"fee_rate":O.fee_rate},j,d)
   if d2_cands:
    l=sorted({str(c["leg_a"]["token_id"])for c in d2_cands}|{str(c["leg_b"]["token_id"])for c in d2_cands});p=await self.fetch_books_batch(l,timeout=3.)
    for dc in d2_cands:
     _b,_a=dc["leg_a"],dc["leg_b"];K,J=p.get(str(_b["token_id"])),p.get(str(_a["token_id"]))
     if not K or not J:continue
     Z,_=self._best_ask_sz(K);Y,_=self._best_ask_sz(J)
     if Z<1. and Y<1.:self._record_market_telemetry(key=f"D2_12PM_{_b['market_id']}_{_a['market_id']}",min_interval_sec=30.,now_ts=now,sig=(Z,Y),payload={"type":"D2_12PM_CORRIDOR","asset":O.asset,"tte_sec":round(C,0),"k_low":dc["k_low"],"k_high":dc["k_high"],"corridor_bps":dc["corridor_bps"],"gross_box_l1":round(Z+Y,4),"label":dc["label"]})
     I=walk_equal_shares_dominance_box(K.get("asks")or[],J.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["D2_12PM_BINANCE_BOX"],fee_rate_a=float(_b["fee_rate"]),fee_rate_b=float(_a["fee_rate"]),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
     if I.get("filled"):opps_out.append({"sleeve":"D2_12PM_BINANCE_BOX","market":f"{O.asset} 12PM Box {dc['label']}","ask_vwap":round(float(I["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(I["box_cost_net"]),4),"l1_usd":I["l1_usd"],"close_ts":dc["close_ts"]});await self.open_shadow_two_leg_box(sleeve="D2_12PM_BINANCE_BOX",dedupe_key=f"D2_{_b['market_id']}_{_a['market_id']}",asset=O.asset,title=f"{O.asset} 12PM Binance Box {dc['label']}",leg_a=_b,leg_b=_a,bk_a=K,bk_b=J,close_ts=float(dc["close_ts"]),max_box_cost_net=.99,extra={"is_d2_12pm_box":True,"k_low":dc["k_low"],"k_high":dc["k_high"],"corridor_bps":dc["corridor_bps"]})
  for _,sp in list(self.daily_updown_markets.items()):
   X=sp.end_ts-now
   if not(120.<=X<=5400.):continue
   H=self.spots.get(sp.asset,.0)
   if H<=.0:continue
   A=f"{sp.asset}_{int(sp.start_ts)}";h=self.daily_open_cache.get(A)
   if h is None:
    z=await V.run_in_executor(None,fetch_binance_window_extremes_sync,sp.asset,sp.start_ts-60.,sp.start_ts+60.,"1m")
    if z is not None and z[2]>0:self.daily_open_cache[A]=(sp.end_ts,float(z[2]));a=float(z[2])
    else:continue
   else:a=h[1]
   o=evaluate_svi_digital_fair_value(sp.asset,H,a,X,is_downward=False,now_ts=now);g="UP"if H>a else"DOWN";n=float(o["p_yes"]if g=="UP"else o["p_no"]);y=abs(float(o.get("z_sigma")or.0))
   if y<1.8 or n<.93:continue
   k=self.get_return_bps(sp.asset,60.)
   if(g=="UP"and k<-10.)or(g=="DOWN"and k>10.):continue
   W=sp.up_token if g=="UP"else sp.down_token;bk=await self.fetch_json(f"{CLOB_URL}/book?token_id={W}",timeout=3.)
   if not bk:continue
   x=walk_l2_book_asks(bk.get("asks")or[],BANKROLL_TICKETS["T1000"]["U1_DAILY_UPDOWN_LOCK"],fee_rate=sp.fee_rate)
   if not x.get("filled"):continue
   m=float(x["eff_px"]);G=n-m
   if.66<=x["vwap"]<=.9 and G>=.025:opps_out.append({"sleeve":"U1_DAILY_UPDOWN_LOCK","market":f"{sp.asset} {sp.title} ({g}, TTE={X/60:.0f}m, z={y:.2f})","ask_vwap":m,"p_model":round(n,4),"net_edge":round(G,4),"l1_usd":x["l1_usd"],"close_ts":sp.end_ts})
   if.66<=x["vwap"]<=.9 and G>=.042:
    b=sp.down_token if g=="UP"else sp.up_token
    if y>=2.2 and n>=.965:e=await self.fetch_json(f"{CLOB_URL}/book?token_id={b}",timeout=2.5);self.emit_live_single_leg_lock_candidate(sleeve_source="U1_DAILY_UPDOWN_LOCK",asset=sp.asset,dedupe_key=f"U1_{sp.market_id}_{g}",token_id=W,opp_token_id=b,market_id=sp.market_id,condition_id=sp.condition_id,side_label=g,display_label=f"{sp.asset} Daily {g}",bk_win=bk,bk_opp=e if isinstance(e,dict)else None,fee_rate=sp.fee_rate,fee_exponent=1.,neg_risk=False,close_ts=sp.end_ts,now_ts=now,max_lock_eff_px=.9,max_opp_bid=.36,hold_to_maturity=False,p_model=float(n))
    await self.open_shadow_position(sleeve="U1_DAILY_UPDOWN_LOCK",dedupe_key=f"U1_{sp.market_id}_{g}",asset_or_city=sp.asset,title=sp.title,side_label=g,token_id=W,fee_rate=sp.fee_rate,p_model=n,close_ts=sp.end_ts,extra={"market_id":sp.market_id,"condition_id":sp.condition_id,"strike":a,"is_downward":(g=="DOWN"),"z_sigma":y},tp_target_px=.98,prefetched_book=bk)
 @staticmethod
 def is_in_same_oracle_overlap_window(now_ts):a=math.ceil(now_ts/9e2)*9e2;b=a-now_ts;return 8.<=b<=305.
 async def discover_dominance_pairs(self,now_ts=None):
  j=float(now_ts if now_ts is not None else time.time())
  for i,(f,_)in list(self.dominance_pairs.items()):
   if f.end_ts<j-6e2:self.dominance_pairs.pop(i,None)
  for b,(c,_)in list(self.chainlink_open_cache.items()):
   if c<j-6e2:self.chainlink_open_cache.pop(b,None)
  g=self.__dict__.get("_strike_source")or{}
  for b,(c,_)in list(g.items()):
   if c<j-6e2:g.pop(b,None)
  for b,h in list(self._strike_fail_backoff_ts.items()):
   if float(h or.0)<j-7200.:self._strike_fail_backoff_ts.pop(b,None)
  target_end_ts=int(math.ceil(j/9e2)*900);e=float(target_end_ts)-j;d=305. if(self.single_scan or"fetch_json"in self.__dict__)else 335.
  if not(5.<=e<=d):return
  now_iso=datetime.fromtimestamp(j-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  async def _discover_asset_pair(asset):
   d=f"{asset}_{target_end_ts}"
   if d in self.dominance_pairs:return
   f=DOMINANCE_SERIES_SLUGS[asset];c,e=await asyncio.gather(self.fetch_json(f"{GAMMA_URL}/events?series_slug={f['15m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",timeout=4.),self.fetch_json(f"{GAMMA_URL}/events?series_slug={f['5m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",timeout=4.));a=None;b=None
   if isinstance(c,list):
    for ev in c:
     g=parse_twap_candle_event(ev,asset,"15m")
     if g and abs(g.end_ts-target_end_ts)<=2.:a=g;break
   if isinstance(e,list):
    for ev in e:
     h=parse_twap_candle_event(ev,asset,"5m")
     if h and abs(h.end_ts-target_end_ts)<=2.:b=h;break
   if a and b and verify_same_oracle_pair(a,b):self.dominance_pairs[d]=(a,b)
  await asyncio.gather(*(_discover_asset_pair(a)for a in DOMINANCE_ASSETS))
 def _strike_is_rest_verified(self,spec):b=f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}";a=(self.__dict__.get("_strike_source")or{}).get(b);return bool(a is None or a[1]=="REST_VERIFIED")
 async def get_authoritative_open_strike(self,spec):
  v=f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}";o=self.__dict__.setdefault("_strike_source",{});q=self.chainlink_open_cache.get(v)
  if q is not None:o[v]=(spec.end_ts,"REST_VERIFIED");return q[1]
  o[v]=(spec.end_ts,"PENDING");u=time.time();i=self.single_scan or("fetch_json"in self.__dict__);t=getattr(self,"_chainlink_ws",None)if not i else None;f=t.get_boundary_twap_60s(spec.asset,spec.start_ts,min_ticks=52)if t is not None else None
  if not self.single_scan and u<spec.start_ts+(.2 if f is not None else 2.):return None
  if not i and u<spec.start_ts+2. and f is not None:o[v]=(spec.end_ts,"WS_TWAP");return f
  if not i:
   d=float(self._strike_fail_backoff_ts.get(v,.0)or.0)
   if(u-d)<2.5:
    if f is not None:o[v]=(spec.end_ts,"WS_TWAP")
    return f
  m=build_crypto_price_query_url(spec);h=None;c=3 if(i or u<spec.start_ts+35.)else(2 if u<spec.start_ts+95. else 1);g=.3 if i else.12
  for l in range(c):
   n=await self.fetch_json(m,timeout=4. if i else 2.5);h=parse_authoritative_open_price(n,request_url=m)
   if h is not None:break
   if l+1<c:await asyncio.sleep(g*(l+1))
  e=self.single_scan or u>=spec.start_ts+335.;b=e or(h is None and u>=spec.start_ts+10.);a=False
  if b:
   s=build_prev_5m_gamma_event_url(spec);r=parse_authoritative_open_price(await self.fetch_json(s,timeout=4. if i else 2.5),request_url=s)
   if h is None and r is not None:h=r;a=True
   elif e and r is not None and abs(h-r)/max(1e-9,r)>1e-6:logger.error(f"[CRITICAL TWAP MISMATCH VETO] {spec.asset} {spec.horizon}: crypto-price TWAP={h} != Gamma prev_5m finalPrice={r}!");return None
   elif e and r is None and not self.single_scan:
    if not i:self._strike_fail_backoff_ts[v]=time.time()
    return None
  if h is None:
   if not i:
    self._strike_fail_backoff_ts[v]=time.time()
    if f is not None and u<spec.start_ts+335.:o[v]=(spec.end_ts,"WS_TWAP");return f
   w=self.__dict__.setdefault("_strike_fail_log_ts",{})
   if(u-float(w.get(v,.0)))>=60.:w[v]=u;logger.warning(f"[STRIKE LOOKUP FAILED] {spec.asset} {spec.horizon}: crypto-price + prev_5m Gamma returned no usable openPrice -> skipped (fail-closed).")
  if h is not None:
   p=[px for ts_s,px in self.usd_spot_hist.get(spec.asset,())if(spec.start_ts-60.)<=ts_s<=(spec.start_ts+5.)]
   if len(p)>=3 and not self.single_scan:
    k=sum(p)/len(p)
    if k>.0 and abs(h-k)/k>.0035:logger.error(f"[STRIKE TWAP VETO] {spec.asset} {spec.horizon}: strike {h} vs local 60s TWAP {k} > 35 bps");return None
   elif not(e or a):
    j=float(self.spots.get(spec.asset)or.0)
    if j>.0 and abs(h-j)/j>.015:logger.error(f"[STRIKE SANITY VETO] {spec.asset} {spec.horizon}: strike {h} vs spot {j} > 150 bps");return None
   self.chainlink_open_cache[v]=(spec.end_ts,h);o[v]=(spec.end_ts,"REST_VERIFIED")
  return h
 async def _passes_complement_anti_box_check(self,leg_a,leg_b,prefetched_books=None):
  u=str(leg_a.get("opp_token_id")or"");t=str(leg_b.get("opp_token_id")or"")
  if not u or not t:return False
  d=(prefetched_books or{}).get(u);c=(prefetched_books or{}).get(t)
  if not(isinstance(d,dict)and isinstance(c,dict)):d,c=await asyncio.gather(self.fetch_json(f"{CLOB_URL}/book?token_id={u}",timeout=3.),self.fetch_json(f"{CLOB_URL}/book?token_id={t}",timeout=3.))
  if not(isinstance(d,dict)and isinstance(c,dict)):return False
  n,_=extract_best_bid(d.get("bids")or[]);m,_=extract_best_bid(c.get("bids")or[]);l,_=self._best_ask_sz(d);k,_=self._best_ask_sz(c);s=n>.0 or(.0<l<=.12);r=m>.0 or(.0<k<=.12);b=(n if n>.0 else l)+(m if m>.0 else k);f=str(leg_a.get("token_id")or"");e=str(leg_b.get("token_id")or"");q=(prefetched_books or{}).get(f)if f else None;p=(prefetched_books or{}).get(e)if e else None
  if isinstance(q,dict)and isinstance(p,dict):j,_=self._best_ask_sz(q);i,_=self._best_ask_sz(p);a=((j>.0 and n>.0 and(j+n)>1.015)or(i>.0 and m>.0 and(i+m)>1.015)or(n+m)>1.16 or b>1.18)
  else:a=(n+m)>1. or b>1.035
  if not(s and r)or(n<=.0 and m<=.0)or a:
   h=self.__dict__.setdefault("_anti_box_warn_ts",{});o=f"{u}:{t}";g=time.time()
   if(g-float(h.get(o,.0)))>=30.:
    if len(h)>512:h.clear()
    h[o]=g;logger.warning(f"[ANTI-BOX VETO] Rejected box {leg_a.get('label')}+{leg_b.get('label')}: complement bids={n:.3f}+{m:.3f}={n+m:.3f} (ub={b:.3f}, unverified or > 1.00)")
   return False
  return True
 async def open_shadow_two_leg_box(self,sleeve,dedupe_key,asset,title,leg_a,leg_b,bk_a,bk_b,close_ts,max_box_cost_net,extra):
  o=self._try_acquire_keys(dedupe_key)
  if not o:return False
  try:
   if sleeve in("CM_B3_PYTH_BARRIER_BOX","SP1_NBA_ZERO_FEE_BOX","SP3_SPORTS_CORRIDOR_DOMINANCE_BOX","NR_CONV_NO_BASKET_ARB"):
    await asyncio.sleep(.25);f=await self.fetch_books_batch([leg_a["token_id"],leg_b["token_id"]],timeout=3.);bk_a=f.get(leg_a["token_id"])or{};bk_b=f.get(leg_b["token_id"])or{}
    if not bk_a or not bk_b:return False
   e=bk_a.get("asks")or[];d=bk_b.get("asks")or[];k,_=extract_best_bid(bk_a.get("bids")or[]);j,_=extract_best_bid(bk_b.get("bids")or[]);a={}
   for b,i in BANKROLL_TICKETS.items():
    n=walk_equal_shares_dominance_box(e,d,target_budget_usd=i[sleeve],fee_rate_a=float(leg_a.get("fee_rate",CRYPTO_FEE_RATE)),fee_rate_b=float(leg_b.get("fee_rate",CRYPTO_FEE_RATE)),fee_exponent_a=float(leg_a.get("fee_exponent",1.)),fee_exponent_b=float(leg_b.get("fee_exponent",1.)),max_box_cost_net=max_box_cost_net,min_shares=8,min_box_notional_usd=7.)
    if n.get("filled"):a[b]=n
   if"T1000"not in a:return False
   h=a["T1000"];m=time.time();c=f"{sleeve}_{int(m)}_{dedupe_key[-10:]}";l={"position_id":c,"dedupe_key":dedupe_key,"sleeve":sleeve,"asset_or_city":asset,"title":title,"side":f"{leg_a.get('side','YES')}+{leg_b.get('side','NO')}","token_id":f"{leg_a['token_id']}|{leg_b['token_id']}","fee_rate":float(leg_a.get("fee_rate",CRYPTO_FEE_RATE)),"entry_ts":m,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"p_model_entry":1.,"entry_eff_px_t1000":h["eff_px"],"entry_vwap_t1000":h["vwap"],"realized_edge_t1000":h["riskless_floor_per_pair"],"entry_best_bid":round(k+j,4),"last_bid":round(k+j,4),"maker_tp_px":None,"tier_fills":a,"extra":{**extra,"leg_a":leg_a,"leg_b":leg_b},"status":"OPEN"};self.open_positions[c]=l
   for g in o:self.entered_keys.add(g)
   self._append_ledger({"event":"SHADOW_ENTRY",**l});logger.info(f"[ENTRY:{sleeve}] {title} | {h['shares']} pairs @ net=${h['eff_px']:.4f}");return True
  finally:self._release_inflight_keys(o)
 async def open_shadow_weather_slate(self,spec,slate_info,close_ts):
  d=str(slate_info.get("side")or"ALL_BUCKETS_YES");g=float(slate_info.get("guaranteed_payout_per_set")or 1.);c=f"W3_SLATE_{spec.event_id}"if d=="ALL_BUCKETS_YES"else f"W3_SLATE_NO_{spec.event_id}";n=self._try_acquire_keys(c)
  if not n:return False
  try:
   f=float(slate_info["sum_asks"]);legs=slate_info["legs"];a=min(float(lg.get("ask_shares",lg.get("ask_yes_shares",.0)))for lg in legs);b={}
   for e,k in BANKROLL_TICKETS.items():
    sh=max(5.,min(a,math.floor(k["W3_WEATHER_SLATE_ARB"]/max(.1,f))));j=round(sh*f,2)
    if sh>=5. and j<=k["W3_WEATHER_SLATE_ARB"]*1.25:b[e]={"filled":True,"vwap":round(f,4),"eff_px":round(f,4),"spent_usd":j,"fee_usd":.0,"shares":sh,"l1_usd":round(a*f,2)}
   if"T1000"not in b:return False
   m=time.time();h=f"W3_WEATHER_SLATE_ARB_{int(m)}_{spec.event_id[-6:]}";l={"position_id":h,"dedupe_key":c,"sleeve":"W3_WEATHER_SLATE_ARB","asset_or_city":f"{spec.city}_{spec.icao}","title":f"{spec.title} [Full-Slate {len(legs)} Buckets {d}]","side":d,"token_id":"|".join(str(lg.get("token_id")or lg.get("yes_token"))for lg in legs),"fee_rate":.0,"entry_ts":m,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":close_ts,"p_model_entry":round(g,4),"entry_eff_px_t1000":round(f,4),"entry_vwap_t1000":round(f,4),"realized_edge_t1000":round(g-f,4),"entry_best_bid":round(f,4),"last_bid":round(f,4),"maker_tp_px":None,"tier_fills":b,"extra":{"event_id":spec.event_id,"icao":spec.icao,"guaranteed_payout":g,"legs":legs},"status":"OPEN"};self.open_positions[h]=l
   for i in n:self.entered_keys.add(i)
   self._append_ledger({"event":"SHADOW_ENTRY",**l});logger.info(f"[ENTRY:W3_WEATHER_SLATE_ARB] {l['title']} @ sum_asks=${f:.4f} (payout=${g:.2f})");return True
  finally:self._release_inflight_keys(n)
 async def open_shadow_dominance_box(self,asset,m15,m5,dom_info,prefetched_books=None,sleeve_override="D1_SAME_ORACLE_DOMINANCE_BOX",max_box_cost_override=.995):
  n="D1"if sleeve_override=="D1_SAME_ORACLE_DOMINANCE_BOX"else sleeve_override.split("_")[0]+"_"+sleeve_override.split("_")[1];e=f"{n}_{asset}_{m15.market_id}_{m5.market_id}";z=self._try_acquire_keys(e)
  if not z:return False
  try:
   v=dom_info["leg_a"];u=dom_info["leg_b"]
   if prefetched_books is not None:i,h=prefetched_books
   else:await asyncio.sleep(.05);i,h=await asyncio.gather(self.fetch_json(f"{CLOB_URL}/book?token_id={v['token_id']}",timeout=3.),self.fetch_json(f"{CLOB_URL}/book?token_id={u['token_id']}",timeout=3.))
   if not i or not h:return False
   m=i.get("asks")or[];l=h.get("asks")or[];t,_=extract_best_bid(i.get("bids")or[]);s,_=extract_best_bid(h.get("bids")or[]);b=self._strike_is_rest_verified(m15)and self._strike_is_rest_verified(m5);r=walk_equal_shares_dominance_box(m,l,target_budget_usd=BANKROLL_TICKETS["T1000"][sleeve_override],fee_rate_a=float(v["fee_rate"]),fee_rate_b=float(u["fee_rate"]),fee_exponent_a=float(v["fee_exponent"]),fee_exponent_b=float(u["fee_exponent"]),max_box_cost_net=max_box_cost_override,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=.86 if b else.9)
   if not r.get("filled"):return False
   c=("4h"in(str(m15.horizon).lower(),str(m5.horizon).lower()))and(str(m15.horizon).lower()!=str(m5.horizon).lower());g=compute_d1_legging_drag_haircut(shares=float(r["shares"]),box_cost_net=float(r["box_cost_net"]),avail_a_shares=float(r["avail_a_shares"]),avail_b_shares=float(r["avail_b_shares"]),px_a=float(r["leg_a_walk"]["worst_px"]),px_b=float(r["leg_b_walk"]["worst_px"]),fee_rate_a=float(v["fee_rate"]),fee_rate_b=float(u["fee_rate"]),is_4h_mixed=c)
   if g["legging_adjusted_net_ev_per_pair"]<=.0:logger.info(f"[SHADOW LEGGING PARITY REJECT] {asset} {sleeve_override}: box_net=${r['box_cost_net']:.4f} depth_mult={g['min_depth_mult']:.2f}x drag={g['legging_drag_per_pair']:.4f}/pair -> adj_ev={g['legging_adjusted_net_ev_per_pair']:+.4f}/pair <= 0");return False
   d={};a={}
   for f,q in BANKROLL_TICKETS.items():
    y=walk_equal_shares_dominance_box(m,l,target_budget_usd=q[sleeve_override],fee_rate_a=float(v["fee_rate"]),fee_rate_b=float(u["fee_rate"]),fee_exponent_a=float(v["fee_exponent"]),fee_exponent_b=float(u["fee_exponent"]),max_box_cost_net=max_box_cost_override,min_shares=8,min_box_notional_usd=7.5)
    if y.get("filled"):d[f]=y;j=compute_d1_legging_drag_haircut(shares=float(y["shares"]),box_cost_net=float(y["box_cost_net"]),avail_a_shares=float(y["avail_a_shares"]),avail_b_shares=float(y["avail_b_shares"]),px_a=float(y["leg_a_walk"]["worst_px"]),px_b=float(y["leg_b_walk"]["worst_px"]),fee_rate_a=float(v["fee_rate"]),fee_rate_b=float(u["fee_rate"]),is_4h_mixed=c);a[f]=float(j["legging_drag_usd"])
   if"T1000"not in d:return False
   x=time.time();k=f"{sleeve_override}_{int(x)}_{m5.market_id[-6:]}";p=f"{asset} {dom_info['regime']} [{dom_info['k_low']:.4f} .. {dom_info['k_high']:.4f}]";w={"position_id":k,"dedupe_key":e,"sleeve":sleeve_override,"asset_or_city":asset,"title":p,"side":f"{v['label']}+{u['label']}","token_id":f"{v['token_id']}|{u['token_id']}","fee_rate":float(v["fee_rate"]),"entry_ts":x,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":m5.end_ts,"p_model_entry":1.,"entry_eff_px_t1000":r["eff_px"],"entry_vwap_t1000":r["vwap"],"realized_edge_t1000":r["riskless_floor_per_pair"],"legging_adjusted_edge_t1000":g["legging_adjusted_net_ev_per_pair"],"entry_best_bid":round(t+s,4),"last_bid":round(t+s,4),"maker_tp_px":None,"tier_fills":d,"extra":{"is_dominance_box":True,"regime":dom_info["regime"],"k_low":dom_info["k_low"],"k_high":dom_info["k_high"],"corridor_bps":dom_info["corridor_bps"],"m15_horizon":m15.horizon,"m15_market_id":m15.market_id,"m15_start_iso":m15.start_iso,"m15_end_iso":m15.end_iso,"m5_horizon":m5.horizon,"m5_market_id":m5.market_id,"leg_a":v,"leg_b":u,"legging_drag_ref":g,"legging_drag_usd_by_tier":a},"status":"OPEN"};self.open_positions[k]=w
   for o in z:self.entered_keys.add(o)
   self._append_ledger({"event":"SHADOW_ENTRY",**w});logger.info(f"[ENTRY:{sleeve_override}] {p} | {r['shares']} pairs @ net=${r['eff_px']:.4f} (floor=${r['riskless_floor_per_pair']:+.4f}/pair, min_profit=${r['guaranteed_min_profit_usd']:+.2f})");return True
  finally:self._release_inflight_keys(z)
 def _d1_live_max_box_cost(self):
  try:
   b=Path(os.getenv("POLYMARKET_RISK_CONFIG",str(PROJECT_ROOT/"config/polymarket_risk_config.json")));a=json.loads(b.read_text(encoding="utf-8"));v=float(a.get("d1_max_box_cost_net",.985))
   if.86<=v<=.995:return v
  except Exception:pass
  return.985
 def emit_live_d1_box_candidate(self,m15,m5,dom_info,w_live,now_ts,*,is_quiet_book=False,sleeve_source="D1_SAME_ORACLE_DOMINANCE_BOX"):
  a=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==a:return False
  if not(self.single_scan or("fetch_json"in self.__dict__)):
   now_ts=time.time()
   if float(m5.end_ts-now_ts)<16.:return False
  k=f"{m15.asset}_{m15.market_id}_{m5.market_id}";j=float(self._last_d1_live_emit_ts.get(k,.0)or.0)
  if(now_ts-j)<10.:return False
  leg_a=dom_info["leg_a"];leg_b=dom_info["leg_b"];r=w_live["leg_a_walk"];q=w_live["leg_b_walk"];h=("4h"in(str(m15.horizon).lower(),str(m5.horizon).lower()))and(str(m15.horizon).lower()!=str(m5.horizon).lower());i=compute_d1_legging_drag_haircut(shares=float(w_live["shares"]),box_cost_net=float(w_live["box_cost_net"]),avail_a_shares=float(w_live["avail_a_shares"]),avail_b_shares=float(w_live["avail_b_shares"]),px_a=float(r["worst_px"]),px_b=float(q["worst_px"]),fee_rate_a=float(leg_a["fee_rate"]),fee_rate_b=float(leg_b["fee_rate"]),is_4h_mixed=h)
  if i["legging_adjusted_net_ev_per_pair"]<=.0:return False
  self._last_d1_live_emit_ts[k]=now_ts
  for o,n in list(self._last_d1_live_emit_ts.items()):
   if(now_ts-n)>1200.:self._last_d1_live_emit_ts.pop(o,None)
  m="D1_4H_LIVE"if str(m15.horizon).lower()=="4h"else"D1_LIVE";p={"box_id":f"{m}_{m15.asset}_{int(m5.end_ts)}_{m5.market_id[-5:]}","dedupe_key":f"D1_{m15.asset}_{m15.market_id}_{m5.market_id}","ts_unix":round(now_ts,3),"asset":m15.asset,"regime":dom_info["regime"],"pair_horizons":f"{m15.horizon}_{m5.horizon}","sleeve_source":str(sleeve_source),"is_quiet_book":bool(is_quiet_book),"k_low":dom_info["k_low"],"k_high":dom_info["k_high"],"corridor_bps":dom_info["corridor_bps"],"expiry_ts":float(m5.end_ts),"rem_sec":round(float(m5.end_ts-now_ts),2),"shares":int(w_live["shares"]),"net_paired_shares":float(w_live.get("net_paired_shares",w_live["shares"])),"leg_a_gross_shares":float(w_live.get("leg_a_gross_shares",w_live["shares"])),"leg_b_gross_shares":float(w_live.get("leg_b_gross_shares",w_live["shares"])),"box_cost_net":float(w_live["box_cost_net"]),"legging_drag_per_pair":i["legging_drag_per_pair"],"legging_adjusted_net_ev_per_pair":i["legging_adjusted_net_ev_per_pair"],"max_box_cost_net":self._d1_live_max_box_cost(),"leg_a_token_id":str(leg_a["token_id"]),"leg_a_opp_token_id":str(leg_a.get("opp_token_id")or""),"leg_a_label":str(leg_a["label"]),"leg_a_side":str(leg_a["side"]),"leg_a_horizon":str(leg_a["horizon"]),"leg_a_market_id":str(leg_a["market_id"]),"leg_a_condition_id":str(leg_a["condition_id"]),"leg_a_strike":float(leg_a["strike"]),"leg_a_limit_price":float(r["worst_px"]),"leg_a_avail_shares":float(w_live["avail_a_shares"]),"leg_a_fee_rate":float(leg_a["fee_rate"]),"leg_a_fee_exponent":float(leg_a["fee_exponent"]),"leg_a_neg_risk":bool(leg_a["neg_risk"]),"leg_b_token_id":str(leg_b["token_id"]),"leg_b_opp_token_id":str(leg_b.get("opp_token_id")or""),"leg_b_label":str(leg_b["label"]),"leg_b_side":str(leg_b["side"]),"leg_b_horizon":str(leg_b["horizon"]),"leg_b_market_id":str(leg_b["market_id"]),"leg_b_condition_id":str(leg_b["condition_id"]),"leg_b_strike":float(leg_b["strike"]),"leg_b_limit_price":float(q["worst_px"]),"leg_b_avail_shares":float(w_live["avail_b_shares"]),"leg_b_fee_rate":float(leg_b["fee_rate"]),"leg_b_fee_exponent":float(leg_b["fee_exponent"]),"leg_b_neg_risk":bool(leg_b["neg_risk"])}
  if not self.single_scan and self._ws_books:
   d=[str(leg_a["token_id"]),str(leg_b["token_id"])];c=[t_id for t_id in(str(leg_a.get("opp_token_id")or""),str(leg_b.get("opp_token_id")or""))if t_id];req_ws_toks=d+c;now_ws_emit=time.time();rest_seeded=getattr(self,"_ws_rest_seeded",set());ws_entries=[None if t_id in rest_seeded else self._ws_books.get(t_id)for t_id in req_ws_toks]
   if len(req_ws_toks)>=2 and all(e is not None and(now_ws_emit-e[0])<=(.65 if idx<2 else 2.5)and e[1].get("bids")and e[1].get("asks")for idx,e in enumerate(ws_entries)):p["ws_books_ts"]=round(min(float(e[0])for e in ws_entries[:2]if e is not None),4);p["ws_books"]={t_id:{"bids":(e[1].get("bids")or[])[:12],"asks":(e[1].get("asks")or[])[:12]}for t_id,e in zip(req_ws_toks,ws_entries)if e is not None}
  try:
   try:import orjson as _orj;g=_orj.dumps(p)+b"\n";b=g.decode("utf-8")
   except Exception:b=json.dumps(p,separators=(",",":"))+"\n";g=b.encode("utf-8")
   if os.name!="nt"and D1_LIVE_CANDIDATES_FILE==a:
    try:
     import socket;f=getattr(self,"_d1_ipc_sock",None)
     if f is None:f=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);f.setblocking(False);self._d1_ipc_sock=f
     l=os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify");f.sendto(g,f"\x00{l}".encode("utf-8"))
    except Exception:pass
   D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True,exist_ok=True)
   with open(D1_LIVE_CANDIDATES_FILE,"a",encoding="utf-8")as fp:fp.write(b)
   return True
  except Exception as exc:return False
 def emit_live_two_leg_box_candidate(self,*,sleeve_source,box_type,asset,dedupe_key,leg_a,leg_b,bk_a,bk_b,close_ts,now_ts,k_low=1e2,k_high=1e2):
  b=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==b:return False
  if not(self.single_scan or("fetch_json"in self.__dict__)):now_ts=time.time()
  i=float(close_ts-now_ts)
  if i<25.:return False
  g=float(self._last_d1_live_emit_ts.get(dedupe_key,.0)or.0)
  if(now_ts-g)<15.:return False
  u=float(leg_a.get("fee_rate",CRYPTO_FEE_RATE));t=float(leg_b.get("fee_rate",CRYPTO_FEE_RATE));s=float(leg_a.get("fee_exponent",1.));r=float(leg_b.get("fee_exponent",1.))
  if sleeve_source=="COND1_MACRO_PARTITION_BOX":a=.985
  elif box_type=="BARRIER_MONO":a=.993
  else:a=.99 if max(u,t)==.0 else.988
  n=walk_equal_shares_dominance_box(bk_a.get("asks")or[],bk_b.get("asks")or[],target_budget_usd=13.5,fee_rate_a=u,fee_rate_b=t,fee_exponent_a=s,fee_exponent_b=r,max_box_cost_net=a,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.86)
  if not n.get("filled"):return False
  if len(self._last_d1_live_emit_ts)>256:self._last_d1_live_emit_ts={k:v for k,v in self._last_d1_live_emit_ts.items()if(now_ts-float(v))<=1200.}
  self._last_d1_live_emit_ts[dedupe_key]=now_ts;y=n["leg_a_walk"];x=n["leg_b_walk"];q,_=self._best_ask_sz(bk_a);p,_=self._best_ask_sz(bk_b);m,_=extract_best_bid(bk_a.get("bids")or[]);l,_=extract_best_bid(bk_b.get("bids")or[]);f=bool(m>.0 and l>.0 and(q-m)<=.041 and(p-l)<=.041 and(max(u,t)==.0 or(now_ts-float(self._last_any_shock_ts_by_asset.get(str(asset),.0)or.0))>=4.));h=round(abs(k_high-k_low)/max(1e-9,k_low)*1e4,2)if k_low>0 else.0;w={"box_id":f"{box_type}_LIVE_{asset}_{int(close_ts)}_{str(leg_a.get('market_id','0'))[-5:]}","dedupe_key":dedupe_key,"box_type":str(box_type),"ts_unix":round(now_ts,3),"asset":str(asset),"regime":f"{box_type}_{leg_a.get('label','A')}_PLUS_{leg_b.get('label','B')}","pair_horizons":str(box_type).lower(),"sleeve_source":str(sleeve_source),"is_quiet_book":f,"k_low":float(k_low),"k_high":float(k_high),"corridor_bps":h,"expiry_ts":float(close_ts),"rem_sec":round(i,2),"shares":int(n["shares"]),"net_paired_shares":float(n.get("net_paired_shares",n["shares"])),"leg_a_gross_shares":float(n.get("leg_a_gross_shares",n["shares"])),"leg_b_gross_shares":float(n.get("leg_b_gross_shares",n["shares"])),"box_cost_net":float(n["box_cost_net"]),"max_box_cost_net":a,"leg_a_token_id":str(leg_a["token_id"]),"leg_a_opp_token_id":str(leg_a.get("opp_token_id")or""),"leg_a_label":str(leg_a.get("label")or leg_a.get("side")or"YES"),"leg_a_side":str(leg_a.get("side")or"YES"),"leg_a_horizon":str(leg_a.get("horizon")or box_type.lower()),"leg_a_market_id":str(leg_a.get("market_id")or""),"leg_a_condition_id":str(leg_a.get("condition_id")or""),"leg_a_strike":float(leg_a.get("strike")or k_low),"leg_a_limit_price":float(y["worst_px"]),"leg_a_avail_shares":float(n["avail_a_shares"]),"leg_a_fee_rate":u,"leg_a_fee_exponent":s,"leg_a_neg_risk":bool(leg_a["neg_risk"])if isinstance(leg_a.get("neg_risk"),bool)else False,"leg_a_expiry_ts":float(leg_a.get("end_ts")or close_ts),"leg_b_token_id":str(leg_b["token_id"]),"leg_b_opp_token_id":str(leg_b.get("opp_token_id")or""),"leg_b_label":str(leg_b.get("label")or leg_b.get("side")or"NO"),"leg_b_side":str(leg_b.get("side")or"NO"),"leg_b_horizon":str(leg_b.get("horizon")or box_type.lower()),"leg_b_market_id":str(leg_b.get("market_id")or""),"leg_b_condition_id":str(leg_b.get("condition_id")or""),"leg_b_strike":float(leg_b.get("strike")or k_high),"leg_b_limit_price":float(x["worst_px"]),"leg_b_avail_shares":float(n["avail_b_shares"]),"leg_b_fee_rate":t,"leg_b_fee_exponent":r,"leg_b_neg_risk":bool(leg_b["neg_risk"])if isinstance(leg_b.get("neg_risk"),bool)else False,"leg_b_expiry_ts":float(leg_b.get("end_ts")or close_ts)}
  if not self.single_scan and self._ws_books:
   req_ws_2=[str(leg_a["token_id"]),str(leg_b["token_id"])]
   if str(box_type)!="COMPLETE_SET":
    for o in(str(leg_a.get("opp_token_id")or""),str(leg_b.get("opp_token_id")or"")):
     if o:req_ws_2.append(o)
   rest_seeded_2=getattr(self,"_ws_rest_seeded",set())
   if all(t_x in self._ws_books and t_x not in rest_seeded_2 and(now_ts-self._ws_books[t_x][0])<=.5 and bool(self._ws_books[t_x][1].get("bids"))and bool(self._ws_books[t_x][1].get("asks"))for t_x in req_ws_2):w["ws_books"]={t_x:{"bids":(self._ws_books[t_x][1].get("bids")or[])[:12],"asks":(self._ws_books[t_x][1].get("asks")or[])[:12]}for t_x in req_ws_2};w["ws_books_ts"]=round(min(self._ws_books[t_x][0]for t_x in req_ws_2),3)
  try:
   try:import orjson as _orj;e=_orj.dumps(w)+b"\n";c=e.decode("utf-8")
   except Exception:c=json.dumps(w,separators=(",",":"))+"\n";e=c.encode("utf-8")
   if os.name!="nt"and D1_LIVE_CANDIDATES_FILE==b:
    try:
     import socket;d=getattr(self,"_d1_ipc_sock",None)
     if d is None:d=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);d.setblocking(False);self._d1_ipc_sock=d
     j=os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify");d.sendto(e,f"\x00{j}".encode("utf-8"))
    except Exception:pass
   D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True,exist_ok=True)
   with open(D1_LIVE_CANDIDATES_FILE,"a",encoding="utf-8")as fp:fp.write(c)
   return True
  except Exception as exc:return False
 def emit_live_single_leg_lock_candidate(self,*,sleeve_source,asset,dedupe_key,token_id,opp_token_id,market_id,condition_id,side_label,display_label,bk_win,bk_opp,fee_rate,fee_exponent,neg_risk,close_ts,now_ts,max_lock_eff_px,max_opp_bid=.025,hold_to_maturity=False,p_model=1.):
  a=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==a:return False
  if not(self.single_scan or("fetch_json"in self.__dict__)):now_ts=time.time()
  h=float(close_ts-now_ts)
  if h<25. or not token_id or not opp_token_id:return False
  f=float(self._last_d1_live_emit_ts.get(dedupe_key,.0)or.0)
  if(now_ts-f)<15.:return False
  if isinstance(bk_opp,dict):
   g,_=extract_best_bid(bk_opp.get("bids")or[]);c,_=self._best_ask_sz(bk_win)
   if g>max_opp_bid+1e-6:return False
   if c<1. and g>.0 and(c+g)>1.015:return False
  m=walk_l2_book_asks_depth_capped(bk_win.get("asks")or[],25.,5.,fee_rate=float(fee_rate),max_slip_cents=min(.015,max(.002,float(max_lock_eff_px)-.98)),min_l1_usd=15.,max_ask_px=min(.998,float(max_lock_eff_px)+.001),fee_exponent=float(fee_exponent))
  if not m.get("filled"):return False
  j=float(m["eff_px"])
  if j>float(max_lock_eff_px)+1e-6 or float(m["shares"])<5. or(float(p_model)-j)<.0045:return False
  if len(self._last_d1_live_emit_ts)>256:self._last_d1_live_emit_ts={k:v for k,v in self._last_d1_live_emit_ts.items()if(now_ts-float(v))<=1200.}
  self._last_d1_live_emit_ts[dedupe_key]=now_ts;l={"box_id":f"LOCK1_LIVE_{asset}_{int(close_ts)}_{str(market_id or'0')[-5:]}","dedupe_key":dedupe_key,"box_type":"SINGLE_LEG_LOCK","ts_unix":round(now_ts,3),"asset":str(asset),"regime":f"SINGLE_LEG_LOCK_{str(display_label)[:48]}","pair_horizons":"single_leg_lock","sleeve_source":str(sleeve_source),"is_quiet_book":True,"expiry_ts":float(close_ts),"rem_sec":round(h,2),"shares":int(math.floor(float(m["shares"]))),"box_cost_net":j,"max_box_cost_net":float(max_lock_eff_px),"max_opp_bid":float(max_opp_bid),"hold_to_maturity":bool(hold_to_maturity),"p_model":round(float(p_model),4),"leg_a_token_id":str(token_id),"leg_a_opp_token_id":str(opp_token_id),"leg_a_label":str(display_label)[:64],"leg_a_side":str(side_label),"leg_a_horizon":"lock_1leg","leg_a_market_id":str(market_id),"leg_a_condition_id":str(condition_id),"leg_a_strike":.0,"leg_a_limit_price":float(m.get("worst_px")or m["best_ask"]),"leg_a_avail_shares":float(m["shares"]),"leg_a_fee_rate":float(fee_rate),"leg_a_fee_exponent":float(fee_exponent),"leg_a_neg_risk":bool(neg_risk),"leg_a_expiry_ts":float(close_ts)}
  try:
   try:import orjson as _orj;e=_orj.dumps(l)+b"\n";b=e.decode("utf-8")
   except Exception:b=json.dumps(l,separators=(",",":"))+"\n";e=b.encode("utf-8")
   if os.name!="nt"and D1_LIVE_CANDIDATES_FILE==a:
    try:
     import socket;d=getattr(self,"_d1_ipc_sock",None)
     if d is None:d=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);d.setblocking(False);self._d1_ipc_sock=d
     i=os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify");d.sendto(e,f"\x00{i}".encode("utf-8"))
    except Exception:pass
   D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True,exist_ok=True)
   with open(D1_LIVE_CANDIDATES_FILE,"a",encoding="utf-8")as fp:fp.write(b)
   return True
  except Exception as exc:return False
 def emit_live_negrisk_convert_candidate(self,*,sleeve_source,spec,dedupe_key,arb_hit,books_by_token,now_ts,fee_bips=0):
  c=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==c:return False
  if not(self.single_scan or("fetch_json"in self.__dict__)):now_ts=time.time()
  m=float(spec.end_ts-now_ts)
  if m<65. or not spec.is_closed_convert_safe:return False
  h=float(self._last_d1_live_emit_ts.get(dedupe_key,.0)or.0)
  if(now_ts-h)<12.:return False
  no_legs_out=[]
  for i in(arb_hit.get("no_legs")or[]):
   b=i.get("bracket")or{};w=i.get("walk")or{};p=str(i.get("token_id")or b.get("no_token")or"")
   if not p or b.get("question_index")is None:return False
   no_legs_out.append({"token_id":p,"market_id":str(b.get("market_id")or""),"condition_id":str(b.get("condition_id")or""),"question_index":int(b["question_index"]),"label":str(b.get("label")or"")[:48],"limit_price":float(w.get("worst_px")or.5),"fee_rate":float(b.get("fee_rate",.0)or.0),"fee_exponent":float(b.get("fee_exponent",1.)or 1.)})
  liquid_yes_sells=[]
  for i in(arb_hit.get("yes_sell_legs")or[]):
   b=i.get("bracket")or{};w=i.get("walk")or{};o=str(i.get("token_id")or b.get("yes_token")or"")
   if not o:return False
   liquid_yes_sells.append({"yes_token":o,"market_id":str(b.get("market_id")or""),"label":str(b.get("label")or"")[:48],"min_bid_price":float(w.get("worst_px")or.01),"fee_rate":float(b.get("fee_rate",.0)or.0),"fee_exponent":float(b.get("fee_exponent",1.)or 1.)})
  a=[{"yes_token":str(b.get("yes_token")or""),"market_id":str(b.get("market_id")or""),"question_index":int(b.get("question_index")or 0),"label":str(b.get("label")or"")[:48]}for b in(arb_hit.get("retained_free_yes_brackets")or[])];l=float(arb_hit.get("net_edge_per_share")or.0)
  if len(no_legs_out)<2 or l<(.008 if not liquid_yes_sells else.012):return False
  if len(self._last_d1_live_emit_ts)>256:self._last_d1_live_emit_ts={k:v for k,v in self._last_d1_live_emit_ts.items()if(now_ts-float(v))<=1200.}
  self._last_d1_live_emit_ts[dedupe_key]=now_ts;rel_toks=[x["token_id"]for x in no_legs_out]+[y["yes_token"]for y in liquid_yes_sells];j={t:books_by_token[t]for t in rel_toks if isinstance(books_by_token.get(t),dict)};g=str(arb_hit.get("mode")or("NR2_PURE_CASH_CONVERT"if not liquid_yes_sells and not a else"NR2_SUBSET_CONVERT_FREE_TAIL"));q={"box_id":f"NRCONV_LIVE_{spec.event_id}_{int(now_ts)}","dedupe_key":dedupe_key,"box_type":"NEGRISK_CONVERT","convert_mode":g,"ts_unix":round(now_ts,3),"asset":"NEGRISK","sleeve_source":str(sleeve_source),"neg_risk_market_id":str(spec.neg_risk_market_id),"fee_bips":int(fee_bips),"expiry_ts":float(spec.end_ts),"rem_sec":round(m,2),"shares":int(math.floor(float(arb_hit.get("shares")or 6.))),"net_edge_per_share":round(l,5),"box_cost_net":round(max(.01,1.-l),4),"leg_a_fee_rate":max((x["fee_rate"]for x in no_legs_out),default=.0),"leg_b_fee_rate":max((y["fee_rate"]for y in liquid_yes_sells),default=.0),"no_legs":no_legs_out,"liquid_yes_sells":liquid_yes_sells,"retained_tail_tokens":a,"ws_books":j if len(j)==len(rel_toks)else None,"ws_books_ts":round(now_ts,3)}
  try:
   try:import orjson as _orj;f=_orj.dumps(q)+b"\n";d=f.decode("utf-8")
   except Exception:d=json.dumps(q,separators=(",",":"))+"\n";f=d.encode("utf-8")
   if os.name!="nt"and D1_LIVE_CANDIDATES_FILE==c:
    try:
     import socket;e=getattr(self,"_d1_ipc_sock",None)
     if e is None:e=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);e.setblocking(False);self._d1_ipc_sock=e
     n=os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify");e.sendto(f,f"\x00{n}".encode("utf-8"))
    except Exception:pass
   D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True,exist_ok=True)
   with open(D1_LIVE_CANDIDATES_FILE,"a",encoding="utf-8")as fp:fp.write(d)
   return True
  except Exception as exc:return False
 def emit_live_single_leg_maker_lock_candidate(self,*,sleeve_source,asset,dedupe_key,pair_dedupe_key,token_id,opp_token_id,market_id,condition_id,side_label,display_label,bk_win,bk_opp,neg_risk,close_ts,now_ts,min_resting_bid=.94,max_resting_bid=.994,min_maker_edge=.006,max_opp_bid=.008,hold_to_maturity=True,p_model=1.,target_bid_px=None,maker_rebate_ps=.0):
  c=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==c:return False
  if not(self.single_scan or("fetch_json"in self.__dict__)):now_ts=time.time()
  u=float(close_ts-now_ts)
  if u<120. or not token_id or not opp_token_id or token_id==opp_token_id:return False
  p=float(self._last_d1_live_emit_ts.get(dedupe_key,.0)or.0)
  if(now_ts-p)<35.:return False
  if not isinstance(bk_win,dict)or not isinstance(bk_opp,dict):return False
  t,_=extract_best_bid(bk_opp.get("bids")or[])
  if t>float(max_opp_bid)+1e-6:return False
  r,l=extract_best_bid(bk_win.get("bids")or[])
  if target_bid_px is None and r<float(min_resting_bid)-1e-9:return False
  j=[float(a["price"])for a in(bk_win.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0];q=round(min(j),4)if j else 1.
  if q<1. and t>.0 and(q+t)>1.015:return False
  o=bk_win.get("minimum_tick_size")or bk_win.get("tick_size")or bk_win.get("min_tick_size")
  try:d=float(o)if o not in(None,"")else.0
  except(TypeError,ValueError):d=.0
  tb=max(.001 if r>=.96 else.01,d if d>=.01 else.0);ta=max(.001 if q>.96 else.01,d if d>=.01 else.0);x=max(.0,float(maker_rebate_ps or.0))
  if target_bid_px is not None:s=min(float(target_bid_px),round(q-ta,4),float(max_resting_bid));f=max(.001 if s>=.96-1e-9 else.01,d if d>=.01 else.0);b=round(math.floor((s+1e-9)/f)*f,4)
  else:n=round(r+tb,4)if(q-r)>=(2.*tb-1e-9)else r;m=min(round(q-ta,4),float(max_resting_bid),round(float(p_model)+x-float(min_maker_edge),4));f=max(.001 if min(n,m)>=.96-1e-9 else.01,d if d>=.01 else.0);b=round(math.floor((min(n,m)+1e-9)/f)*f,4)
  if(r>.0 and b<round(r-1e-9,4)and target_bid_px is None)or not(float(min_resting_bid)<=b<=float(max_resting_bid)):return False
  if q<1. and b>=q-1e-9:return False
  g=round(max(.001,b-x),6)
  if(float(p_model)-g)<float(min_maker_edge)-1e-9:return False
  if abs(b-r)<=1e-6 and l>350. and not(self.single_scan or("fetch_json"in self.__dict__)):return False
  if len(self._last_d1_live_emit_ts)>256:self._last_d1_live_emit_ts={k:v for k,v in self._last_d1_live_emit_ts.items()if(now_ts-float(v))<=1200.}
  self._last_d1_live_emit_ts[dedupe_key]=now_ts;y={"box_id":f"MKR_LOCK1_LIVE_{asset}_{int(close_ts)}_{str(market_id or'0')[-5:]}","dedupe_key":dedupe_key,"pair_dedupe_key":pair_dedupe_key,"box_type":"SINGLE_LEG_MAKER_LOCK","ts_unix":round(now_ts,3),"asset":str(asset),"regime":f"SINGLE_LEG_MAKER_LOCK_{str(display_label)[:44]}","pair_horizons":"single_leg_maker_lock","sleeve_source":str(sleeve_source),"is_quiet_book":True,"queue_front":bool(b>r+1e-6 or l<=50.),"expiry_ts":float(close_ts),"rem_sec":round(u,2),"shares":16,"box_cost_net":b,"max_box_cost_net":float(max_resting_bid),"anchor_bid_px":b,"min_resting_bid":float(min_resting_bid),"max_opp_bid":float(max_opp_bid),"hold_to_maturity":bool(hold_to_maturity),"p_model":round(float(p_model),4),"leg_a_token_id":str(token_id),"leg_a_opp_token_id":str(opp_token_id),"leg_a_label":str(display_label)[:64],"leg_a_side":str(side_label),"leg_a_horizon":"maker_lock_1leg","leg_a_market_id":str(market_id),"leg_a_condition_id":str(condition_id),"leg_a_strike":.0,"leg_a_limit_price":b,"leg_a_tick_size":f,"leg_a_fee_rate":.0,"leg_a_fee_exponent":1.,"leg_a_neg_risk":bool(neg_risk),"leg_a_expiry_ts":float(close_ts),"ws_books":{str(token_id):bk_win,str(opp_token_id):bk_opp},"ws_books_ts":round(now_ts,3)}
  try:
   try:import orjson as _orj;i=_orj.dumps(y)+b"\n";e=i.decode("utf-8")
   except Exception:e=json.dumps(y,separators=(",",":"))+"\n";i=e.encode("utf-8")
   if os.name!="nt"and D1_LIVE_CANDIDATES_FILE==c:
    try:
     import socket;h=getattr(self,"_d1_ipc_sock",None)
     if h is None:h=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);h.setblocking(False);self._d1_ipc_sock=h
     w=os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify");h.sendto(i,f"\x00{w}".encode("utf-8"))
    except Exception:pass
   D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True,exist_ok=True)
   with open(D1_LIVE_CANDIDATES_FILE,"a",encoding="utf-8")as fp:fp.write(e)
   return True
  except Exception as exc:return False
 def emit_live_maker_anchor_box_candidate(self,*,sleeve_source,box_type,asset,dedupe_key,regime,pair_horizons,leg_a,leg_b,anchor_is_a,queue_front,anchor_bid_px,hedge_limit_px,avail_a_shares,avail_b_shares,close_ts,now_ts,k_low=1e2,k_high=1e2,corridor_bps=.0,posted_spot=.0):
  a=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==a:return False
  if D1_LIVE_CANDIDATES_FILE==a:
   if os.environ.get("PM_DISABLE_LIVE_MAKER_ANCHOR_BOX","0")=="1":return False
   try:
    w=PIPELINE_ROOT/"config"/"polymarket_risk_config.json"
    if w.exists()and not bool(json.loads(w.read_text(encoding="utf-8")).get("enable_live_maker_anchor_boxes",True)):return False
   except Exception:pass
  if not(self.single_scan or("fetch_json"in self.__dict__)):now_ts=time.time()
  j=float(close_ts-now_ts);i=65.;h=64800. if box_type=="ZERO_FEE_MAKER_ANCHOR"else 9e2
  if not(i<=j<=h):return False
  e=float(self._last_d1_live_emit_ts.get(dedupe_key,.0)or.0)
  if(now_ts-e)<12.:return False
  u=float(leg_a.get("fee_rate",.0 if box_type=="ZERO_FEE_MAKER_ANCHOR"else CRYPTO_FEE_RATE));t=float(leg_b.get("fee_rate",.0 if box_type=="ZERO_FEE_MAKER_ANCHOR"else CRYPTO_FEE_RATE));s=float(leg_a.get("fee_exponent",1.));r=float(leg_b.get("fee_exponent",1.));o=t if anchor_is_a else u;n=r if anchor_is_a else s;q=min(.95,o*((hedge_limit_px*(1.-hedge_limit_px))**n)/max(1e-9,hedge_limit_px))if(o>.0 and.0<hedge_limit_px<1.)else.0;f=round(anchor_bid_px+hedge_limit_px/max(.05,1.-q),4);g=((.992 if str(regime)=="ZF_SP1_NBA"else(.985 if j>3600. else.99))if box_type=="ZERO_FEE_MAKER_ANCHOR"else.988)
  if not(.86<=f<=g):return False
  if len(self._last_d1_live_emit_ts)>256:self._last_d1_live_emit_ts={k:v for k,v in self._last_d1_live_emit_ts.items()if(now_ts-float(v))<=1200.}
  self._last_d1_live_emit_ts[dedupe_key]=now_ts;m=max(5,int(math.floor(13.5/max(.86,f))));x={"box_id":f"{box_type}_LIVE_{asset}_{int(close_ts)}_{str(leg_a.get('market_id','0'))[-5:]}","dedupe_key":dedupe_key,"box_type":str(box_type),"ts_unix":round(now_ts,3),"asset":str(asset),"regime":str(regime),"pair_horizons":str(pair_horizons),"sleeve_source":str(sleeve_source),"anchor_is_a":bool(anchor_is_a),"queue_front":bool(queue_front),"anchor_bid_px":round(float(anchor_bid_px),4),"hedge_limit_px":round(float(hedge_limit_px),4),"posted_spot":round(float(posted_spot),6),"k_low":float(k_low),"k_high":float(k_high),"corridor_bps":round(float(corridor_bps),2),"expiry_ts":float(close_ts),"rem_sec":round(j,2),"shares":m,"box_cost_net":f,"max_box_cost_net":g,"leg_a_token_id":str(leg_a["token_id"]),"leg_a_opp_token_id":str(leg_a.get("opp_token_id")or""),"leg_a_label":str(leg_a.get("label")or leg_a.get("side")or"YES"),"leg_a_side":str(leg_a.get("side")or"YES"),"leg_a_horizon":str(leg_a.get("horizon")or pair_horizons),"leg_a_market_id":str(leg_a.get("market_id")or""),"leg_a_condition_id":str(leg_a.get("condition_id")or""),"leg_a_strike":float(leg_a.get("strike")or k_low),"leg_a_limit_price":round(float(anchor_bid_px if anchor_is_a else hedge_limit_px),4),"leg_a_avail_shares":round(float(avail_a_shares),2),"leg_a_fee_rate":u,"leg_a_fee_exponent":s,"leg_a_neg_risk":bool(leg_a["neg_risk"])if isinstance(leg_a.get("neg_risk"),bool)else False,"leg_a_expiry_ts":float(leg_a.get("end_ts")or close_ts),"leg_b_token_id":str(leg_b["token_id"]),"leg_b_opp_token_id":str(leg_b.get("opp_token_id")or""),"leg_b_label":str(leg_b.get("label")or leg_b.get("side")or"NO"),"leg_b_side":str(leg_b.get("side")or"NO"),"leg_b_horizon":str(leg_b.get("horizon")or pair_horizons),"leg_b_market_id":str(leg_b.get("market_id")or""),"leg_b_condition_id":str(leg_b.get("condition_id")or""),"leg_b_strike":float(leg_b.get("strike")or k_high),"leg_b_limit_price":round(float(hedge_limit_px if anchor_is_a else anchor_bid_px),4),"leg_b_avail_shares":round(float(avail_b_shares),2),"leg_b_fee_rate":t,"leg_b_fee_exponent":r,"leg_b_neg_risk":bool(leg_b["neg_risk"])if isinstance(leg_b.get("neg_risk"),bool)else False,"leg_b_expiry_ts":float(leg_b.get("end_ts")or close_ts)}
  if not self.single_scan and self._ws_books:
   req_ws_m=[str(leg_a["token_id"]),str(leg_b["token_id"])]
   for p in(str(leg_a.get("opp_token_id")or""),str(leg_b.get("opp_token_id")or"")):
    if p:req_ws_m.append(p)
   rest_seeded_m=getattr(self,"_ws_rest_seeded",set())
   if all(t_x in self._ws_books and t_x not in rest_seeded_m and(now_ts-self._ws_books[t_x][0])<=(.65 if i_x<2 else 2.5)and bool(self._ws_books[t_x][1].get("bids"))and bool(self._ws_books[t_x][1].get("asks"))for i_x,t_x in enumerate(req_ws_m)):x["ws_books"]={t_x:{"bids":(self._ws_books[t_x][1].get("bids")or[])[:12],"asks":(self._ws_books[t_x][1].get("asks")or[])[:12]}for t_x in req_ws_m};x["ws_books_ts"]=round(min(self._ws_books[t_x][0]for t_x in req_ws_m[:2]),3)
  try:
   try:import orjson as _orj;d=_orj.dumps(x)+b"\n";b=d.decode("utf-8")
   except Exception:b=json.dumps(x,separators=(",",":"))+"\n";d=b.encode("utf-8")
   if os.name!="nt"and D1_LIVE_CANDIDATES_FILE==a:
    try:
     import socket;c=getattr(self,"_d1_ipc_sock",None)
     if c is None:c=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);c.setblocking(False);self._d1_ipc_sock=c
     l=os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify");c.sendto(d,f"\x00{l}".encode("utf-8"))
    except Exception:pass
   D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True,exist_ok=True)
   with open(D1_LIVE_CANDIDATES_FILE,"a",encoding="utf-8")as fp:fp.write(b)
   return True
  except Exception as exc:return False
 def _latest_spot_px(self,asset):
  uh=self.usd_spot_hist.get(asset)
  if uh and len(uh)>0 and(time.time()-float(uh[-1][0]))<=10. and float(uh[-1][1])>.0:return float(uh[-1][1])
  return float(self.spots.get(asset)or.0)
 def post_maker_anchor_candidate(self,m15,m5,dom_info,bk_a,bk_b,now_ts,*,live_emit_only=False):
  if is_shadow_sleeve_quarantined("D1_MAKER_ANCHOR_BOX"):return False
  G=m5.end_ts-now_ts;o=880. if str(m5.horizon)=="15m"else 295.
  if not(65.<=G<=o):return False
  n=self.get_return_bps(m15.asset,5.)
  if abs(n)>4.5:return False
  if(now_ts-float(self._last_any_shock_ts_by_asset.get(m15.asset,.0)or.0))<4.:return False
  _c=f"D1_MKR_{m15.asset}_{m15.market_id}_{m5.market_id}"
  if not live_emit_only and(_c in self.entered_keys or _c in self.pending_maker_anchors or _c in self.inflight_keys):return False
  _b,_a=dom_info["leg_a"],dom_info["leg_b"];N=sorted([(float(b["price"]),float(b["size"]))for b in(bk_a.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);M=sorted([(float(b["price"]),float(b["size"]))for b in(bk_b.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);asks_a=sorted([(float(a["price"]),float(a["size"]))for a in(bk_a.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);asks_b=sorted([(float(a["price"]),float(a["size"]))for a in(bk_b.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0])
  if not asks_a or not asks_b or not N or not M:return False
  Z,Y=N[0];X,W=M[0];ask_a,_e=asks_a[0];ask_b,_d=asks_b[0];V,U=round(ask_a-Z,4),round(ask_b-X,4);T=(Y-_e)/max(1e-9,Y+_e);S=(W-_d)/max(1e-9,W+_d);m=float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(m15.asset,40.));k=min(float(BANKROLL_TICKETS["T100"]["D1_MAKER_ANCHOR_BOX"]),m);l=max(5.,math.floor(k/.985));j=max(5.,math.floor(min(float(BANKROLL_TICKETS["T1000"]["D1_MAKER_ANCHOR_BOX"]),m)/.985))
  def _snap_c(p):p=round(float(p),4);return(math.floor((p+1e-9)*1e2)/1e2)if(.04+1e-9<p<.96-1e-9)else(math.floor((p+1e-9)*1e3)/1e3)
  s=[]
  for c in(True,False):
   R=Z if c else X;F=Y if c else W;Q=ask_a if c else ask_b;P=V if c else U;E=T if c else S;D=_b if c else _a;asks_hdg=asks_b if c else asks_a;C=_a if c else _b
   if not(.03<=Q<=.999)or E<-.35:continue
   w=str(D.get("side")or"UP").upper()
   if(w=="UP"and n<-2.2)or(w=="DOWN"and n>2.2):continue
   L=.001 if(R>=.96 or R<.04)else.01;K=.001 if(Q>.96 or Q<=.04)else.01;J=_snap_c(R+L);O=_snap_c(Q-K)
   if J<=O+1e-9 and J>R+1e-9:f=min(J,O);d=True
   elif P>=.01-1e-9 and.15<=Q<=.85 and E>=-.15 and F>=15.:f=_snap_c(R);d=False
   else:continue
   u=sum(sz for px,sz in asks_hdg if px<=asks_hdg[0][0]+.01)
   if u<max(15.,2.5*l):continue
   I=asks_hdg[0][0];B=float(C["fee_rate"])*((I*(1.-I))**float(C.get("fee_exponent",1.)));g=I+B;i=min(f,_snap_c(.988-g));r=round(R-(L if d else.0),3)
   if i<r or i<=.02 or i>=Q:continue
   v=round(i+g,4);h=.86 if(self._strike_is_rest_verified(m15)and self._strike_is_rest_verified(m5))else.9
   if h<=v<=.988:s.append((v-(5e-4 if d else.0),c,d,i,round(g,4),l))
  if not s:return False
  s.sort(key=lambda z:z[0]);_,c,d,i,g,H=s[0];t=self._latest_spot_px(m15.asset)
  if not live_emit_only:self.pending_maker_anchors[_c]={"dedupe_key":_c,"asset":m15.asset,"m15":m15,"m5":m5,"dom_info":dom_info,"anchor_is_a":c,"queue_front":d,"bid_px":i,"pair_est":round(i+g,4),"req_shares_t100":H,"req_shares_t1000":j,"posted_ts":now_ts,"posted_spot":t}
  A=sum(sz for px,sz in asks_a if px<=ask_a+.01);y=sum(sz for px,sz in asks_b if px<=ask_b+.01);q=ask_b if c else ask_a;e=False
  if self._strike_is_rest_verified(m15)and self._strike_is_rest_verified(m5):e=self.emit_live_maker_anchor_box_candidate(sleeve_source="D1_MAKER_ANCHOR_BOX",box_type="DOMINANCE_MAKER_ANCHOR",asset=m15.asset,dedupe_key=_c,regime=str(dom_info["regime"]),pair_horizons=f"{m15.horizon}_{m5.horizon}",leg_a=_b,leg_b=_a,anchor_is_a=c,queue_front=d,anchor_bid_px=i,hedge_limit_px=q,avail_a_shares=A,avail_b_shares=y,close_ts=float(m5.end_ts),now_ts=now_ts,k_low=float(dom_info["k_low"]),k_high=float(dom_info["k_high"]),corridor_bps=float(dom_info["corridor_bps"]),posted_spot=t)
  if live_emit_only:return e
  logger.info(f"[MAKER_ANCHOR_POST] {m15.asset} {dom_info['regime']} | Resting post_only=${i:.3f} (qf={d}) + hedge_eff=${g:.4f} = ${i+g:.4f} (TTE={G:.0f}s)");return True
 async def manage_pending_maker_anchors(self,now_ts=None):
  if not self.pending_maker_anchors:return
  _d=float(now_ts if now_ts is not None else time.time());l=[]
  for st in self.pending_maker_anchors.values():di=st["dom_info"];l.extend([str(di["leg_a"]["token_id"]),str(di["leg_b"]["token_id"])])
  _c=await self.fetch_books_batch(l,timeout=2.5)
  for V,st in list(self.pending_maker_anchors.items()):
   _b=st["m15"];m5=st["m5"];di=st["dom_info"];U,T=di["leg_a"],di["leg_b"];B=bool(st["anchor_is_a"]);L=bool(st.get("queue_front",True));K=U if B else T;J=T if B else U;R=_c.get(str(K["token_id"]));bk_hdg=_c.get(str(J["token_id"]));Q=float(st["bid_px"]);P=_d-float(st["posted_ts"]);I=m5.end_ts-_d;asks_anc=(R or{}).get("asks")or[];best_ask_anc=min((float(a["price"])for a in asks_anc if float(a.get("size",0))>0),default=1.);r=R is not None and P>=.35 and best_ask_anc<=Q
   if r:
    self.pending_maker_anchors.pop(V,None);self.entered_keys.add(V);asks_hdg=sorted([(float(a["price"]),float(a["size"]))for a in((bk_hdg or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);hdg_px=asks_hdg[0][0]if asks_hdg else 1.;w=sum(sz for px,sz in asks_hdg if px<=hdg_px+.01)if asks_hdg else.0;H=float(J["fee_rate"])*((hdg_px*(1.-hdg_px))**float(J.get("fee_exponent",1.)))if hdg_px<1. else.0;A=round(Q+hdg_px+H,4);k=float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(_b.asset,1e2));G="4h"in(str(_b.horizon).lower(),str(m5.horizon).lower())
    if bk_hdg is not None and asks_hdg and w>=5. and.9<=A<=.995:
     q={};i={};b=.0
     for h,p in BANKROLL_TICKETS.items():
      sh=max(5.,min(w,math.floor(min(p["D1_MAKER_ANCHOR_BOX"],k)/A)));S=round(sh*H,4);F=round(sh*(Q+hdg_px),2);q[h]={"filled":True,"vwap":round(Q+hdg_px,4),"eff_px":A,"spent_usd":F,"fee_usd":S,"shares":sh,"l1_usd":round(w*A,2)};dr=compute_d1_maker_anchor_drag_haircut(shares=sh,pair_eff=A,bid_anc=Q,hdg_px=hdg_px,hdg_avail_shares=w,fee_rate_anc=float(K.get("fee_rate",CRYPTO_FEE_RATE)),fee_exponent_anc=float(K.get("fee_exponent",1.)),queue_front=L,is_4h_mixed=G);i[h]=float(dr["legging_drag_usd"])
      if h=="T1000":b=float(dr["maker_rebate_20pct_est_usd"])
     v,_=extract_best_bid((_c.get(str(U["token_id"]))or{}).get("bids")or[]);u,_=extract_best_bid((_c.get(str(T["token_id"]))or{}).get("bids")or[]);O=f"D1_MAKER_ANCHOR_BOX_{int(_d)}_{m5.market_id[-6:]}";_a={"position_id":O,"dedupe_key":V,"sleeve":"D1_MAKER_ANCHOR_BOX","asset_or_city":_b.asset,"title":f"{_b.asset} {di['regime']} [0%-Fee Maker Anchor @ ${Q:.3f}]","side":f"{U['label']}+{T['label']}","token_id":f"{U['token_id']}|{T['token_id']}","fee_rate":float(J["fee_rate"]),"entry_ts":_d,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":m5.end_ts,"p_model_entry":1.,"entry_eff_px_t1000":A,"entry_vwap_t1000":round(Q+hdg_px,4),"realized_edge_t1000":round(1.-A,4),"entry_best_bid":round(v+u,4),"last_bid":round(v+u,4),"maker_tp_px":None,"tier_fills":q,"extra":{"is_dominance_box":True,"is_maker_anchor_box":True,"queue_front":L,"legging_drag_usd_by_tier":i,"maker_rebate_20pct_est_t1000_usd":b,"regime":di["regime"],"k_low":di["k_low"],"k_high":di["k_high"],"corridor_bps":di["corridor_bps"],"m15_horizon":_b.horizon,"m15_market_id":_b.market_id,"m15_start_iso":_b.start_iso,"m15_end_iso":_b.end_iso,"m5_horizon":m5.horizon,"m5_market_id":m5.market_id,"leg_a":U,"leg_b":T},"status":"OPEN"};self.open_positions[O]=_a;self._append_ledger({"event":"SHADOW_ENTRY",**_a});logger.info(f"[ENTRY:D1_MAKER_ANCHOR_BOX] {_a['title']} -> Hedged @ net=${A:.4f}!")
    else:
     f,_=extract_best_bid((R or{}).get("bids")or[])
     if f<=.0:f=max(.01,Q-.03)
     E=float(K["fee_rate"])*((f*(1.-f))**float(K.get("fee_exponent",1.)));D=max(.0,f-E);Y={};X={};z=max(.9,float(st.get("pair_est")or.985))
     for h,p in BANKROLL_TICKETS.items():W=max(5.,float(math.floor(min(p["D1_MAKER_ANCHOR_BOX"],k)/z)));Z=round(W*Q,2);Y[h]={"filled":True,"vwap":Q,"eff_px":Q,"spent_usd":Z,"fee_usd":.0,"shares":W};X[h]=round(W*D-Z,2)
     C={"position_id":f"D1_MKR_SCRATCH_{int(_d)}_{m5.market_id[-6:]}","dedupe_key":V,"sleeve":"D1_MAKER_ANCHOR_BOX","asset_or_city":_b.asset,"title":f"{_b.asset} {di['regime']} [Maker Anchor Unhedged Scratch]","side":f"{K['label']}_SCRATCH","token_id":str(K["token_id"]),"fee_rate":.0,"entry_ts":st["posted_ts"],"entry_utc":datetime.fromtimestamp(st["posted_ts"],tz=timezone.utc).isoformat(),"close_ts":m5.end_ts,"closed_ts":_d,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":.5,"entry_eff_px_t1000":Q,"entry_vwap_t1000":Q,"net_payout_per_share":round(D,4),"tier_fills":Y,"tier_pnls_usd":X,"legging_adjusted_tier_pnls_usd":dict(X),"won":X.get("T1000",.0)>0,"status":"MAKER_ANCHOR_UNHEDGED_SCRATCH"};self.closed_positions.append(C);self._append_ledger({"event":"SHADOW_CLOSE",**C})
    continue
   asks_hdg_c=sorted([(float(a["price"]),float(a["size"]))for a in((bk_hdg or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);hdg_px_c=asks_hdg_c[0][0]if asks_hdg_c else 1.;j=sum(sz for px,sz in asks_hdg_c if px<=hdg_px_c+.01)if asks_hdg_c else.0;t=float(J["fee_rate"])*((hdg_px_c*(1.-hdg_px_c))**float(J.get("fee_exponent",1.)))if hdg_px_c<1. else.0;o=float(st.get("req_shares_t100")or st.get("req_shares_t1000")or 15.);d=(j<max(12.,2.*o))or((Q+hdg_px_c+t)>.993);c=.0
   if R is not None:
    _,N=extract_best_bid(R.get("bids")or[]);M=sum(float(a.get("size",0))for a in asks_anc if abs(float(a.get("price",0))-best_ask_anc)<1e-6)
    if(N+M)>.0:c=(N-M)/(N+M)
   s=float(st.get("posted_spot")or.0);y=self._latest_spot_px(_b.asset);e=((y-s)/s*1e4)if(s>.0 and y>.0)else.0;x=self.get_return_bps(_b.asset,5.);n=str(K.get("side")or"UP").upper();m=((min(e,x)<-2.5)if n=="UP"else(max(e,x)>2.5));g=(_d-float(self._last_any_shock_ts_by_asset.get(_b.asset,.0)or.0))<4.
   if(I<=45. or P>=(12. if self.single_scan else 90.)or m or abs(x)>8. or c<-.35 or g or d):self.pending_maker_anchors.pop(V,None)
 def post_zero_fee_maker_anchor_box(self,source_tag,asset,d_key,leg_a,leg_b,bk_a,bk_b,close_ts,title,now_ts,prefetched_books=None,*,live_emit_only=False):
  if is_shadow_sleeve_quarantined("ZF_INTRADAY_MAKER_BOX"):return False
  s=float(close_ts-now_ts)
  if not(65.<=s<=64800.):return False
  E=self.__dict__.setdefault("_zf_maker_cooldown_until",{})
  if not live_emit_only and(d_key in self.entered_keys or d_key in self.pending_zero_fee_maker_anchors or float(E.get(d_key,.0)or.0)>now_ts):return False
  if float(leg_a.get("fee_rate",.0))>.0 or float(leg_b.get("fee_rate",.0))>.0:return False
  if prefetched_books:
   S=str(leg_a.get("opp_token_id")or"");R=str(leg_b.get("opp_token_id")or"")
   if S in prefetched_books and R in prefetched_books:
    U,_=extract_best_bid((prefetched_books[S]or{}).get("bids")or[]);T,_=extract_best_bid((prefetched_books[R]or{}).get("bids")or[]);D,_=self._best_ask_sz(bk_a);C,_=self._best_ask_sz(bk_b)
    if((D>.0 and U>.0 and(D+U)>1.015)or(C>.0 and T>.0 and(C+T)>1.015)or(U+T)>1.16):return False
  B=sorted([(float(b["price"]),float(b["size"]))for b in(bk_a.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);A=sorted([(float(b["price"]),float(b["size"]))for b in(bk_b.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);asks_a=sorted([(float(a["price"]),float(a["size"]))for a in(bk_a.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);asks_b=sorted([(float(a["price"]),float(a["size"]))for a in(bk_b.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0])
  if not asks_a or not asks_b or not B or not A:return False
  Q,P=B[0];O,N=A[0];ask_a,M=asks_a[0];ask_b,L=asks_b[0];K=(P-M)/max(1e-9,P+M);J=(N-L)/max(1e-9,N+L);j=max(6.,math.floor(float(BANKROLL_TICKETS["T100"]["ZF_INTRADAY_MAKER_BOX"])/.988));g=max(6.,math.floor(float(BANKROLL_TICKETS["T1000"]["ZF_INTRADAY_MAKER_BOX"])/.988))
  def _snap_zf(p):p=round(float(p),4);return(math.floor((p+1e-9)*1e2)/1e2)if(.04+1e-9<p<.96-1e-9)else(math.floor((p+1e-9)*1e3)/1e3)
  i=.992 if source_tag=="SP1_NBA"else(.985 if s>3600. else.988);m=[]
  for d in(True,False):
   I=Q if d else O;r=P if d else N;H=ask_a if d else ask_b;q=K if d else J;G=O if d else Q;asks_hdg=asks_b if d else asks_a;a_hdg=asks_hdg[0][0]
   if not(.02<=H<=.999)or not(.001<=a_hdg<=.985)or q<-.25:continue
   if G>.0 and a_hdg>.04 and(a_hdg-G)>.05:continue
   y=.001 if(I>=.96 or I<.04)else.01;w=.001 if(H>.96 or H<=.04)else.01;v=_snap_zf(I+y);F=_snap_zf(H-w);l=sum(sz for px,sz in asks_hdg if px<=a_hdg+.01)
   if l<max(18.,2.5*j):continue
   c=True
   if v<=F+1e-9 and v>I+1e-9:f=min(v,F,_snap_zf(i-a_hdg));c=f>I+1e-9
   elif(H-I)>=.01-1e-9 and.15<=H<=.88 and q>=-.15 and r>=15.:c=False;f=min(_snap_zf(I),_snap_zf(i-a_hdg))
   else:continue
   if f<round(I-y,3)or f<=.015 or f>=H:continue
   e=round(f+a_hdg,4)
   if.86<=e<=i:m.append((e,d,round(f,4),round(a_hdg,4),c))
  if not m:return False
  m.sort(key=lambda z:(z[0],0 if z[4]else 1));e,d,u,t,h=m[0]
  if not live_emit_only:self.pending_zero_fee_maker_anchors[d_key]={"source_tag":source_tag,"dedupe_key":d_key,"asset":asset,"title":title,"leg_a":leg_a,"leg_b":leg_b,"anchor_is_a":d,"bid_px":u,"pair_est":e,"queue_front":h,"req_shares_t100":j,"req_shares_t1000":g,"close_ts":close_ts,"posted_ts":now_ts}
  o=sum(sz for px,sz in asks_a if px<=ask_a+.01);n=sum(sz for px,sz in asks_b if px<=ask_b+.01);k=self.emit_live_maker_anchor_box_candidate(sleeve_source="ZF_INTRADAY_MAKER_BOX",box_type="ZERO_FEE_MAKER_ANCHOR",asset=asset,dedupe_key=d_key,regime=f"ZF_{source_tag}",pair_horizons=f"zf_{source_tag.lower()}",leg_a=leg_a,leg_b=leg_b,anchor_is_a=d,queue_front=h,anchor_bid_px=u,hedge_limit_px=t,avail_a_shares=o,avail_b_shares=n,close_ts=float(close_ts),now_ts=now_ts,k_low=float(leg_a.get("strike")or 1e2),k_high=float(leg_b.get("strike")or 1e2))
  if live_emit_only:return k
  logger.info(f"[ZF_INTRADAY_MAKER_POST:{source_tag}] {title} | bid=${u:.3f} + hdg=${t:.3f} = ${e:.4f} (TTE={s/3600.:.2f}h)");return True
 async def manage_pending_zero_fee_maker_anchors(self,now_ts=None):
  if not self.pending_zero_fee_maker_anchors:return
  O=float(now_ts if now_ts is not None else time.time());A=self.__dict__.setdefault("_zf_maker_cooldown_until",{});J=[t for st in self.pending_zero_fee_maker_anchors.values()for t in(str(st["leg_a"]["token_id"]),str(st["leg_b"]["token_id"]))];N=await self.fetch_books_batch(J,timeout=3.)
  for C,st in list(self.pending_zero_fee_maker_anchors.items()):
   la,lb=st["leg_a"],st["leg_b"];m=bool(st["anchor_is_a"]);u=la if m else lb;s=lb if m else la;z=N.get(str(u["token_id"]));bk_hdg=N.get(str(s["token_id"]));y=float(st["bid_px"]);x=O-float(st["posted_ts"]);r=float(st["close_ts"])-O;asks_anc=(z or{}).get("asks")or[];best_ask_anc=min((float(a["price"])for a in asks_anc if float(a.get("size",0))>0),default=1.)
   if z is not None and x>=.4 and best_ask_anc<=y:
    self.pending_zero_fee_maker_anchors.pop(C,None);self.entered_keys.add(C);asks_hdg=sorted([(float(a["price"]),float(a["size"]))for a in((bk_hdg or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);hdg_px=asks_hdg[0][0]if asks_hdg else 1.;k=sum(sz for px,sz in asks_hdg if px<=hdg_px+.01)if asks_hdg else.0;l=round(y+hdg_px,4)
    if bk_hdg is not None and asks_hdg and k>=5. and.9<=l<=.993:
     B={};q={}
     for d,i in BANKROLL_TICKETS.items():sh=max(5.,min(k,math.floor(i["ZF_INTRADAY_MAKER_BOX"]/l)));B[d]={"filled":True,"vwap":l,"eff_px":l,"spent_usd":round(sh*l,2),"fee_usd":.0,"shares":sh,"l1_usd":round(k*l,2)};I=compute_d1_maker_anchor_drag_haircut(shares=sh,pair_eff=l,bid_anc=y,hdg_px=hdg_px,hdg_avail_shares=k,fee_rate_anc=.0,fee_exponent_anc=1.,queue_front=bool(st.get("queue_front",True)),is_4h_mixed=False);q[d]=float(I["legging_drag_usd"])
     H,_=extract_best_bid((N.get(str(la["token_id"]))or{}).get("bids")or[]);G,_=extract_best_bid((N.get(str(lb["token_id"]))or{}).get("bids")or[]);M=f"ZF_INTRADAY_MKR_{int(O)}_{C[-8:]}";L={"position_id":M,"dedupe_key":C,"sleeve":"ZF_INTRADAY_MAKER_BOX","asset_or_city":st["asset"],"title":f"{st['title']} [ZF Intraday Maker @ ${y:.3f}]","side":f"{la['label']}+{lb['label']}","token_id":f"{la['token_id']}|{lb['token_id']}","fee_rate":.0,"entry_ts":O,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":st["close_ts"],"p_model_entry":1.,"entry_eff_px_t1000":l,"entry_vwap_t1000":l,"realized_edge_t1000":round(1.-l,4),"entry_best_bid":round(H+G,4),"last_bid":round(H+G,4),"maker_tp_px":None,"tier_fills":B,"extra":{"is_two_leg_box":True,"is_maker_anchor_box":True,"legging_drag_usd_by_tier":q,"source_tag":st["source_tag"],"leg_a":la,"leg_b":lb},"status":"OPEN"};self.open_positions[M]=L;self._append_ledger({"event":"SHADOW_ENTRY",**L});logger.info(f"[ENTRY:ZF_INTRADAY_MAKER_BOX] {L['title']} -> Hedged @ ${l:.4f}!")
    else:
     p,_=extract_best_bid((z or{}).get("bids")or[]);o=p if p>0 else max(.01,y-.03);F,E={},{};f=max(.9,float(st.get("pair_est")or.986))
     for d,i in BANKROLL_TICKETS.items():D=max(5.,float(math.floor(i["ZF_INTRADAY_MAKER_BOX"]/f)));K=round(D*y,2);F[d]={"filled":True,"vwap":y,"eff_px":y,"spent_usd":K,"fee_usd":.0,"shares":D};E[d]=round(D*o-K,2)
     n={"position_id":f"ZF_MKR_SCRATCH_{int(O)}_{C[-8:]}","dedupe_key":C,"sleeve":"ZF_INTRADAY_MAKER_BOX","asset_or_city":st["asset"],"title":f"{st['title']} [ZF Intraday Maker Scratch]","side":f"{u['label']}_SCRATCH","token_id":str(u["token_id"]),"fee_rate":.0,"entry_ts":st["posted_ts"],"entry_utc":datetime.fromtimestamp(st["posted_ts"],tz=timezone.utc).isoformat(),"close_ts":st["close_ts"],"closed_ts":O,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":.5,"entry_eff_px_t1000":y,"entry_vwap_t1000":y,"net_payout_per_share":round(o,4),"tier_fills":F,"tier_pnls_usd":E,"legging_adjusted_tier_pnls_usd":dict(E),"won":E.get("T1000",.0)>0,"status":"MAKER_ANCHOR_UNHEDGED_SCRATCH"};self.closed_positions.append(n);self._append_ledger({"event":"SHADOW_CLOSE",**n})
    continue
   asks_hdg_c=sorted([(float(a["price"]),float(a["size"]))for a in((bk_hdg or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);hdg_px_c=asks_hdg_c[0][0]if asks_hdg_c else 1.;e=sum(sz for px,sz in asks_hdg_c if px<=hdg_px_c+.01)if asks_hdg_c else.0;h=float(st.get("req_shares_t100")or 18.);b,w=extract_best_bid((z or{}).get("bids")or[]);v=sum(float(a.get("size",0))for a in asks_anc if abs(float(a.get("price",0))-best_ask_anc)<1e-6);j=((w-v)/(w+v))if(w+v)>.0 else.0;c=.993 if st.get("source_tag")=="SP1_NBA"else.991;g=(r<=60. or j<-.3 or(b>.0 and b<y-.015)or e<max(12.,2.*h)or(y+hdg_px_c)>c)
   if g or x>=(15. if self.single_scan else 90.):
    self.pending_zero_fee_maker_anchors.pop(C,None)
    if g:A[C]=O+12.
    else:A.pop(C,None);self.last_tradfi_sports_scan_ts=min(float(self.last_tradfi_sports_scan_ts),O-16.)
 async def scan_same_oracle_dominance_boxes(self,opps_out,now_ts=None):
  now=float(now_ts if now_ts is not None else time.time())
  if self.pending_maker_anchors:await self.manage_pending_maker_anchors(now)
  target_end_ts=int(math.ceil(now/9e2)*900);e=sum(1 for k in self.dominance_pairs if str(k).endswith(f"_{target_end_ts}"));i=7. if e<len(DOMINANCE_ASSETS)else 12.;n=float(target_end_ts)-now;j=(self.is_in_same_oracle_overlap_window(now)if(self.single_scan or"fetch_json"in self.__dict__)else(5.<=n<=330.))
  if j and(now-self.last_dominance_discovery_ts)>=i:self.last_dominance_discovery_ts=now;await self.discover_dominance_pairs(now)
  if now_ts is None:self.record_usd_spot_samples(time.time())
  active_pairs=[(m15,m5)for m15,m5 in list(self.dominance_pairs.values())if(10.<=(m5.end_ts-now)<=3e2)and(now>=m5.start_ts+1.)]
  if active_pairs:
   async def _resolve_dom(m15,m5):
    b,c=await asyncio.gather(self.get_authoritative_open_strike(m15),self.get_authoritative_open_strike(m5))
    if b is None or c is None:return None
    a=float(MIN_CORRIDOR_BPS_BY_ASSET.get(m15.asset,3.));di=determine_dominance_legs(m15,b,m5,c,min_corridor_bps=a);return(m15,m5,di)if di is not None else None
   h=[r for r in await asyncio.gather(*(_resolve_dom(m15,m5)for m15,m5 in active_pairs))if r is not None]
   if h:
    m=[]
    for _,_,di in h:la,lb=di["leg_a"],di["leg_b"];m.extend([str(la["token_id"]),str(lb["token_id"]),str(la.get("opp_token_id")or""),str(lb.get("opp_token_id")or"")])
    o=await self.fetch_books_batch(m,timeout=3.)
    for m15,m5,w in h:
     y=m5.end_ts-now;C,B=w["leg_a"],w["leg_b"];E=o.get(str(C["token_id"]));D=o.get(str(B["token_id"]))
     if not E or not D:continue
     a=None;v=float(now_ts)if now_ts is not None else time.time();self._record_d1_corridor_telemetry("15m_5m",m15,m5,w,E,D,v);u=m5.end_ts-v;d=self._strike_is_rest_verified(m15)and self._strike_is_rest_verified(m5);c=False
     if d and 18.<=u<=298.:
      g=self._d1_live_max_box_cost();A=walk_equal_shares_dominance_box(E.get("asks")or[],D.get("asks")or[],target_budget_usd=13.5,fee_rate_a=float(C["fee_rate"]),fee_rate_b=float(B["fee_rate"]),fee_exponent_a=float(C["fee_exponent"]),fee_exponent_b=float(B["fee_exponent"]),max_box_cost_net=g,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.86)
      if A.get("filled"):
       f=self._passes_quiet_book_filter(m15.asset,E,D,A,v)
       if float(A["box_cost_net"])<=g:
        a=await self._passes_complement_anti_box_check(C,B,prefetched_books=o)
        if not a:continue
        c=self.emit_live_d1_box_candidate(m15,m5,w,A,v,is_quiet_book=f,sleeve_source="D1_QUIET_BOOK_BOX"if f else"D1_SAME_ORACLE_DOMINANCE_BOX")
     z=walk_equal_shares_dominance_box(E.get("asks")or[],D.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_SAME_ORACLE_DOMINANCE_BOX"],fee_rate_a=float(C["fee_rate"]),fee_rate_b=float(B["fee_rate"]),fee_exponent_a=float(C["fee_exponent"]),fee_exponent_b=float(B["fee_exponent"]),max_box_cost_net=1.032,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=.86 if d else.9);b=False
     if z.get("filled"):
      x=float(z["box_cost_net"]);l=round(1.-x,4)
      if x<=1.005:opps_out.append({"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","market":f"{m15.asset} {w['regime']} (TTE={y:.0f}s, {w['corridor_bps']:.1f}bps)","ask_vwap":round(x,4),"p_model":1.,"net_edge":l,"l1_usd":z["l1_usd"]})
      if x<=.995:
       if a is None:a=await self._passes_complement_anti_box_check(C,B,prefetched_books=o)
       if not a:continue
       b=True;await self.open_shadow_dominance_box(m15.asset,m15,m5,w,prefetched_books=(E,D))
       if self._passes_quiet_book_filter(m15.asset,E,D,z,v):await self.open_shadow_dominance_box(m15.asset,m15,m5,w,prefetched_books=(E,D),sleeve_override="D1_QUIET_BOOK_BOX",max_box_cost_override=.992)
     if not b or not c:
      t,_=self._best_ask_sz(E);s,_=self._best_ask_sz(D);q,_=extract_best_bid(E.get("bids")or[]);p,_=extract_best_bid(D.get("bids")or[])
      if(t+s)<=1.02 or(q>.0 and p>.0 and min(q+s,t+p)<=1.005):
       if a is None:a=await self._passes_complement_anti_box_check(C,B,prefetched_books=o)
       if a:self.post_maker_anchor_candidate(m15,m5,w,E,D,v,live_emit_only=bool(b))
  await self._scan_4h_dominance_boxes(opps_out,now_ts)
 def _passes_quiet_book_filter(self,asset,bk_a,bk_b,w_scan,now_ts):
  if abs(self.get_return_bps(asset,5.))>4.5:return False
  if(now_ts-float(self._last_any_shock_ts_by_asset.get(asset,.0)or.0))<4.:return False
  f,_=extract_best_bid(bk_a.get("bids")or[]);e,_=extract_best_bid(bk_b.get("bids")or[]);d=float((w_scan.get("leg_a_walk")or{}).get("best_ask")or 1.);c=float((w_scan.get("leg_b_walk")or{}).get("best_ask")or 1.)
  if f<=.0 or e<=.0:return False
  if(d-f)>.041 or(c-e)>.041:return False
  b=float(w_scan.get("shares")or 12.);a=min(float(w_scan.get("avail_a_shares")or.0),float(w_scan.get("avail_b_shares")or.0));return a>=1.5*b
 async def discover_4h_dominance_pairs(self,now_ts):
  for p,(k,_)in list(self.dominance_4h_pairs.items()):
   if k.end_ts<now_ts-6e2:self.dominance_4h_pairs.pop(p,None)
  for s,o in list(self.s4h_candles.items()):
   if o.end_ts<now_ts-6e2:self.s4h_candles.pop(s,None)
  c=int(math.ceil(now_ts/14400.)*14400);j=float(c)-now_ts
  if not(8.<=j<=905.):return
  i=datetime.fromtimestamp(now_ts-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");h=j<=305.
  for n in DOMINANCE_ASSETS:
   m=DOMINANCE_SERIES_SLUGS[n];g=m.get("4h")
   if not g:continue
   l=f"{n}_4h15m_{c}";r=f"{n}_4h5m_{c}"
   if l in self.dominance_4h_pairs and((not h)or r in self.dominance_4h_pairs):continue
   f,d=await asyncio.gather(self.fetch_json(f"{GAMMA_URL}/events?series_slug={g}&closed=false&end_date_min={i}&order=endDate&ascending=true&limit=3",timeout=4.),self.fetch_json(f"{GAMMA_URL}/events?series_slug={m['15m']}&closed=false&end_date_min={i}&order=endDate&ascending=true&limit=3",timeout=4.));b=None;a=None
   if isinstance(f,list):
    for ev in f:
     u=parse_twap_candle_event(ev,n,"4h")
     if u and abs(u.end_ts-c)<=2.:b=u;self.s4h_candles[f"{n}_4h_{c}"]=u;break
   if isinstance(d,list):
    for ev in d:
     q=parse_twap_candle_event(ev,n,"15m")
     if q and abs(q.end_ts-c)<=2.:a=q;break
   if b and a and verify_same_oracle_pair(b,a):self.dominance_4h_pairs[l]=(b,a)
   if b and h and r not in self.dominance_4h_pairs:
    e=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={m['5m']}&closed=false&end_date_min={i}&order=endDate&ascending=true&limit=3",timeout=4.)
    if isinstance(e,list):
     for ev in e:
      t=parse_twap_candle_event(ev,n,"5m")
      if t and abs(t.end_ts-c)<=2. and verify_same_oracle_pair(b,t):self.dominance_4h_pairs[r]=(b,t);break
 async def _scan_4h_dominance_boxes(self,opps_out,now_ts=None):
  C=float(now_ts if now_ts is not None else time.time());B=math.ceil(C/14400.)*14400.-C
  if 8.<=B<=905. and(C-self.last_4h_discovery_ts)>=12.:self.last_4h_discovery_ts=C;await self.discover_4h_dominance_pairs(C)
  for _,(m4,u)in list(self.dominance_4h_pairs.items()):
   t=u.end_ts-C;s=895. if u.horizon=="15m"else 298.
   if not(10.<=t<=s)or C<u.start_ts+1.:continue
   N,M=await asyncio.gather(self.get_authoritative_open_strike(m4),self.get_authoritative_open_strike(u))
   if N is None or M is None:continue
   i=float(MIN_CORRIDOR_BPS_BY_ASSET.get(m4.asset,3.));p=determine_dominance_legs(m4,N,u,M,min_corridor_bps=i)
   if p is None:continue
   E,D=p["leg_a"],p["leg_b"];A=await self.fetch_books_batch([str(E["token_id"]),str(D["token_id"]),str(E.get("opp_token_id")or""),str(D.get("opp_token_id")or"")],timeout=3.);L=A.get(str(E["token_id"]));K=A.get(str(D["token_id"]))
   if not L or not K:continue
   a=None;h=float(now_ts)if now_ts is not None else time.time();self._record_d1_corridor_telemetry(f"4h_{u.horizon}",m4,u,p,L,K,h)
   if now_ts is None:self.record_usd_spot_samples(h)
   g=u.end_ts-h;d=self._strike_is_rest_verified(m4)and self._strike_is_rest_verified(u);b=False
   if d and 18.<=g<=s:
    f=self._d1_live_max_box_cost();j=walk_equal_shares_dominance_box(L.get("asks")or[],K.get("asks")or[],target_budget_usd=13.5,fee_rate_a=float(E["fee_rate"]),fee_rate_b=float(D["fee_rate"]),fee_exponent_a=float(E["fee_exponent"]),fee_exponent_b=float(D["fee_exponent"]),max_box_cost_net=f,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.86)
    if j.get("filled"):
     e=self._passes_quiet_book_filter(m4.asset,L,K,j,h)
     if float(j["box_cost_net"])<=f:
      a=await self._passes_complement_anti_box_check(E,D,prefetched_books=A)
      if not a:continue
      b=self.emit_live_d1_box_candidate(m4,u,p,j,h,is_quiet_book=e,sleeve_source="D1_QUIET_BOOK_BOX"if e else"D1_4H_DOMINANCE_BOX")
   z=walk_equal_shares_dominance_box(L.get("asks")or[],K.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_4H_DOMINANCE_BOX"],fee_rate_a=float(E["fee_rate"]),fee_rate_b=float(D["fee_rate"]),fee_exponent_a=float(E["fee_exponent"]),fee_exponent_b=float(D["fee_exponent"]),max_box_cost_net=1.032,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=.86 if d else.9);c=False
   if z.get("filled"):
    r=float(z["box_cost_net"])
    if r<=1.005:opps_out.append({"sleeve":"D1_4H_DOMINANCE_BOX","market":f"{m4.asset} {p['regime']} (TTE={t:.0f}s, {p['corridor_bps']:.1f}bps)","ask_vwap":round(r,4),"p_model":1.,"net_edge":round(1.-r,4),"l1_usd":z["l1_usd"]})
    if r<=.992:
     if a is None:a=await self._passes_complement_anti_box_check(E,D,prefetched_books=A)
     if not a:continue
     c=True;await self.open_shadow_dominance_box(m4.asset,m4,u,p,prefetched_books=(L,K),sleeve_override="D1_4H_DOMINANCE_BOX",max_box_cost_override=.992)
     if self._passes_quiet_book_filter(m4.asset,L,K,z,h):await self.open_shadow_dominance_box(m4.asset,m4,u,p,prefetched_books=(L,K),sleeve_override="D1_QUIET_BOOK_BOX",max_box_cost_override=.992)
   if not c or not b:
    o,_=self._best_ask_sz(L);n,_=self._best_ask_sz(K);m,_=extract_best_bid(L.get("bids")or[]);l,_=extract_best_bid(K.get("bids")or[])
    if(o+n)<=1.02 or(m>.0 and l>.0 and min(m+n,o+l)<=1.005):
     if a is None:a=await self._passes_complement_anti_box_check(E,D,prefetched_books=A)
     if a:self.post_maker_anchor_candidate(m4,u,p,L,K,h,live_emit_only=bool(c))
  for _,S in list(self.s4h_candles.items()):
   y=S.end_ts-C
   if not(180.<=y<=9e2)or C<S.start_ts+3600.:continue
   x=await self.get_authoritative_open_strike(S)
   if x is None or x<=.0:continue
   J=read_shm_usd_anchor(S.asset,C,max_age_sec=3.);R=self.usd_spot_hist.get(S.asset);w=J.get("usd_spot")or(float(R[-1][1])if R and(C-float(R[-1][0]))<=5. else self.spots.get(S.asset,.0))
   if not w or float(w)<=.0:continue
   k=float(w);v="UP"if k>x else"DOWN";q=self.get_return_bps(S.asset,30.)
   if(v=="UP"and q<-6.)or(v=="DOWN"and q>6.):continue
   I=evaluate_svi_digital_fair_value(S.asset,k,x,y,is_downward=False,now_ts=C);Q=float(I["p_yes"]if v=="UP"else I["p_no"]);P=abs(float(I.get("z_sigma")or.0))
   if P<2.3 or Q<.94:continue
   H=S.up_token if v=="UP"else S.down_token;O=await self.fetch_json(f"{CLOB_URL}/book?token_id={H}",timeout=2.5)
   if not O:continue
   w4=walk_l2_book_asks(O.get("asks")or[],BANKROLL_TICKETS["T1000"]["S4H_CHAINLINK_CONVERGENCE"],fee_rate=S.fee_rate,min_l1_usd=18.)
   if not w4.get("filled"):continue
   G=float(w4["eff_px"]);F=Q-G
   if.62<=G<=.89 and F>=.03:opps_out.append({"sleeve":"S4H_CHAINLINK_CONVERGENCE","market":f"{S.asset} 4h {v} (TTE={y/60:.1f}m, z={P:.2f})","ask_vwap":G,"p_model":round(Q,4),"net_edge":round(F,4),"l1_usd":w4["l1_usd"],"close_ts":S.end_ts})
   if.62<=G<=.89 and F>=.045:await self.open_shadow_position(sleeve="S4H_CHAINLINK_CONVERGENCE",dedupe_key=f"S4H_{S.asset}_{S.market_id}",asset_or_city=S.asset,title=f"{S.title} [4h Chainlink Convergence]",side_label=v,token_id=H,fee_rate=S.fee_rate,p_model=Q,close_ts=S.end_ts,extra={"market_id":S.market_id,"condition_id":S.condition_id,"horizon":"4h","start_iso":S.start_iso,"end_iso":S.end_iso,"open_price":x,"z_sigma":P},tp_target_px=.96,prefetched_book=O)
 def poll_fresh_shock_triggers(self,now_ts=None,max_age_sec=4.5):
  if not SHOCK_TRIGGER_FILE.exists():return[]
  l=float(now_ts if now_ts is not None else time.time());h=[]
  try:
   d=SHOCK_TRIGGER_FILE.stat().st_size
   if d<self._shock_file_offset:self._shock_file_offset=0
   if d==self._shock_file_offset:return[]
   with open(SHOCK_TRIGGER_FILE,"r",encoding="utf-8",errors="ignore")as f:f.seek(self._shock_file_offset);a=f.read();self._shock_file_offset=f.tell()
   for b in a.splitlines():
    b=b.strip()
    if not b:continue
    try:j=json.loads(b)
    except Exception:continue
    k=str(j.get("shock_id")or j.get("event_id")or"")
    if not k or k in self._seen_shock_ids:continue
    self._seen_shock_ids.append(k)
    if str(j.get("shock_source")or"").upper()=="BOUNDARY_LOCK":continue
    g=str(j.get("asset")or"").upper()
    if g not in DOMINANCE_ASSETS:continue
    i=float(j.get("t0_unix")or.0)
    if i<=.0 or(l-i)>max_age_sec:continue
    c=float(j.get("spot_at_t0")or j.get("trigger_price")or.0)
    if c>.0:self.spots[g]=c;self.spot_hist.setdefault(g,collections.deque(maxlen=600)).append((l,c))
    e=j.get("chainlink_proxy_spot")or j.get("coinbase_spot")
    if e and float(e)>.0:self.usd_spot_hist.setdefault(g,collections.deque(maxlen=400)).append((l,float(e)));self.usd_direct_flags[g]=True
    if abs(float(j.get("shock_ofi")or.0))>=.55:self._last_any_shock_ts_by_asset[g]=l;h.append(j)
  except Exception as exc:pass
  return h
 async def handle_shock_triggers(self,triggers,opps_out,now_ts=None):
  if not triggers:return
  N=float(now_ts if now_ts is not None else time.time())
  for w in triggers:
   L=str(w.get("asset")or"").upper()
   if L:self._last_any_shock_ts_by_asset[L]=N
  if self.pending_maker_orders:await self.manage_pending_maker_orders()
  if self.pending_maker_anchors:await self.manage_pending_maker_anchors(N)
  if os.getenv("PM_DISABLE_SHADOW_M4_CATCHUP","0")=="1"or is_shadow_sleeve_quarantined("M4_SHOCK_STRIKE_CATCHUP"):return
  for K in triggers:
   D=str(K.get("asset")or"").upper()
   if(N-self._last_m4_shock_ts_by_asset.get(D,.0))<6.:continue
   k=float(K.get("shock_ofi")or.0);j=float(K.get("shock_volume_100ms")or.0);e=7.5e5 if D in("BTC","ETH")else 2.5e5
   if abs(k)<.7 or j<e:continue
   J=float(self.spots.get(D)or K.get("spot_at_t0")or.0)
   if J<=.0:continue
   o=str(K.get("shock_direction")or"").upper()in("BUY","UP");cand_rungs=[]
   for _,C in list(self.strike_ladders.items()):
    if not C or C[0].asset!=D:continue
    M=C[0].end_ts-N
    if not(1800.<=M<=86400.):continue
    for sr in C:
     if abs(math.log(sr.strike/J))>.035:continue
     f=evaluate_svi_digital_fair_value(D,J,sr.strike,M,is_downward=sr.is_downward,now_ts=N)
     if sr.is_downward:b="NO"if o else"YES"
     else:b="YES"if o else"NO"
     v=sr.yes_token if b=="YES"else sr.no_token;g=float(f["p_yes"]if b=="YES"else f["p_no"]);cand_rungs.append((sr,b,v,g,f))
   if not cand_rungs:continue
   self._last_m4_shock_ts_by_asset[D]=N;await asyncio.sleep(.05);B=await asyncio.gather(*[self.fetch_json(f"{CLOB_URL}/book?token_id={c[2]}",timeout=2.5)for c in cand_rungs]);d=None;a=None
   for(sr,b,v,g,f),bk in zip(cand_rungs,B):
    if not bk:continue
    u=walk_l2_book_asks(bk.get("asks")or[],1e2,fee_rate=CRYPTO_FEE_RATE)
    if not u.get("filled"):continue
    p=float(u["vwap"]);t=float(u["eff_px"]);I=g-t;i,_=extract_best_bid(bk.get("bids")or[]);h=float(u["best_ask"])
    if.2<=t<=.86 and I>=.035:opps_out.append({"sleeve":"M4_SHOCK_STRIKE_CATCHUP","market":f"{D} {sr.question} ({b}) [ShockWakeup]","ask_vwap":t,"p_model":round(g,4),"net_edge":round(I,4),"l1_usd":u["l1_usd"]})
    if.22<=p<=.82 and.24<=t<=.84 and I>=.065:
     if d is None or I>d[0]:d=(I,sr,b,v,g,f,bk)
    elif i>.0 and(h-i)>=.02:
     s=round(min(i+.01,h-.01),4);n=g-s
     if.2<=s<=.8 and n>=.065:
      if a is None or n>a[0]:a=(n,sr,b,v,g,f,bk)
   if d is not None:_,H,r,A,m,z,G=d;await self.open_shadow_position(sleeve="M4_SHOCK_STRIKE_CATCHUP",dedupe_key=f"M4_{H.market_id}_{r}_{int(N//300)}",asset_or_city=D,title=H.question,side_label=r,token_id=A,fee_rate=CRYPTO_FEE_RATE,p_model=m,close_ts=H.end_ts,extra={"market_id":H.market_id,"condition_id":H.condition_id,"strike":H.strike,"is_downward":H.is_downward,"iv_annual":z["iv_annual"],"z_sigma":z["z_sigma"],"shock_id":K.get("shock_id"),"shock_ofi":K.get("shock_ofi"),"shock_vol_usd":K.get("shock_volume_100ms")},prefetched_book=G)
   elif a is not None:_,F,q,y,l,x,E=a;await self.post_shadow_maker_entry(sleeve="M4_SHOCK_STRIKE_CATCHUP",dedupe_key=f"M4MKR_{F.market_id}_{q}_{int(N//60)}",asset=D,title=F.question,side_label=q,token_id=y,p_model=l,close_ts=F.end_ts,extra={"execution_mode":"REACTIVE_POST_ONLY_3P5S","market_id":F.market_id,"condition_id":F.condition_id,"strike":F.strike,"is_downward":F.is_downward,"iv_annual":x["iv_annual"],"z_sigma":x["z_sigma"],"shock_id":K.get("shock_id")},prefetched_book=E,ttl_override_sec=3.5)
 @staticmethod
 def is_in_exact_twap_lock_window(now_ts):a=math.ceil(now_ts/3e2)*3e2;b=a-now_ts;return 5.<=b<=55.
 async def discover_active_twap_candles(self,now_ts=None):
  p=float(now_ts if now_ts is not None else time.time())
  for k,g in list(self.twap_candles.items()):
   if g.end_ts<p-3e2:self.twap_candles.pop(k,None)
  f=int(math.ceil(p/3e2)*300);e=float(f)-p
  if not(5.<=e<=75.):return
  for _,(j,m)in self.dominance_pairs.items():
   if abs(m.end_ts-f)<=2.:self.twap_candles[f"{m.asset}_5m_{f}"]=m
   if abs(j.end_ts-f)<=2.:self.twap_candles[f"{j.asset}_15m_{f}"]=j
  d=datetime.fromtimestamp(p-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");a=(f%900)==0
  for i in DOMINANCE_ASSETS:
   h=DOMINANCE_SERIES_SLUGS[i];k5=f"{i}_5m_{f}"
   if k5 not in self.twap_candles:
    c=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={h['5m']}&closed=false&end_date_min={d}&order=endDate&ascending=true&limit=3",timeout=3.5)
    if isinstance(c,list):
     for ev in c:
      o=parse_twap_candle_event(ev,i,"5m")
      if o and abs(o.end_ts-f)<=2.:self.twap_candles[k5]=o;break
   if a:
    n=f"{i}_15m_{f}"
    if n not in self.twap_candles:
     b=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={h['15m']}&closed=false&end_date_min={d}&order=endDate&ascending=true&limit=3",timeout=3.5)
     if isinstance(b,list):
      for ev in b:
       l=parse_twap_candle_event(ev,i,"15m")
       if l and abs(l.end_ts-f)<=2.:self.twap_candles[n]=l;break
 async def scan_exact_twap_locks(self,opps_out,now_ts=None):
  if not self.single_scan and is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK"):
   if self.twap_candles:self.twap_candles.clear()
   return
  y=float(now_ts if now_ts is not None else time.time());r=math.ceil(y/3e2)*3e2-y
  if 5.<=r<=75. and(y-self.last_twap_discovery_ts)>=12.:self.last_twap_discovery_ts=y;await self.discover_active_twap_candles(y)
  g=os.getenv("PM_QUARANTINE_LOSING_SLEEVES","1")=="1";e=28. if g else 45.;l=.975 if g else.965;k=2.65 if g else.0
  for _,v in list(self.twap_candles.items()):
   n=v.end_ts-y
   if not(8.<=n<=e):continue
   if y<v.start_ts+60.:continue
   q=await self.get_authoritative_open_strike(v)
   if q is None or q<=.0:continue
   x=(read_shm_usd_anchor(v.asset,y,max_age_sec=2.5)if not(self.single_scan and self.usd_spot_hist.get(v.asset))else{});j=getattr(self,"_chainlink_ws",None)if not self.single_scan else None;d=j.get_latest_spot(v.asset,now_ts=y,max_age_sec=2.5)if j is not None else None;i=self.usd_spot_hist.get(v.asset);a=d or x.get("usd_spot")
   if(not a or float(a)<=.0)and i and(y-float(i[-1][0]))<=5.:a=float(i[-1][1])
   if(not a or float(a)<=.0)and self.usd_direct_flags.get(v.asset,False):a=self.spots.get(v.asset,.0)
   if not a or float(a)<=.0:continue
   f=float(a);c=bool(d is not None or x.get("source")in("shm_chainlink_proxy","shm_coinbase_usd")or self.usd_direct_flags.get(v.asset,False));t,_=get_wing_implied_vol(v.asset,f,q,86400.);b=j.get_recent_samples(v.asset,v.end_ts-62.)if j is not None else[]
   if len(b)<2:b=list(i or[])
   m=compute_exact_twap_lock_probability(asset=v.asset,open_price=q,current_usd_spot=f,rem_seconds=n,now_ts=y,end_ts=v.end_ts,spot_samples=b,shm_twap_60s=x.get("twap_60s"),iv_annual=t,usd_direct_feed=c)
   if not m.get("eligible")or float(m["p_lock"])<.94 or float(m.get("z_lock",.0))<k:continue
   h=str(m["side"]);w=v.up_token if h=="UP"else v.down_token;bk=await self.fetch_json(f"{CLOB_URL}/book?token_id={w}",timeout=2.5)
   if not bk:continue
   s=walk_l2_book_asks(bk.get("asks")or[],BANKROLL_TICKETS["T1000"]["S2_EXACT_TWAP_LOCK"],fee_rate=v.fee_rate,min_l1_usd=15.)
   if not s.get("filled"):continue
   p=float(s["eff_px"]);o=float(m["p_lock"]);u=o-p
   if.74<=p<=.955 and u>=.015:opps_out.append({"sleeve":"S2_EXACT_TWAP_LOCK","market":f"{v.asset} {v.horizon} {h} (TTE={n:.0f}s, alpha={m['eff_alpha']:.2f}, z={m['z_lock']:.2f})","ask_vwap":p,"p_model":o,"net_edge":round(u,4),"l1_usd":s["l1_usd"]})
   if o>=l and.76<=p<=.95 and u>=.03:await self.open_shadow_position(sleeve="S2_EXACT_TWAP_LOCK",dedupe_key=f"S2_{v.asset}_{v.horizon}_{v.market_id}",asset_or_city=v.asset,title=f"{v.title} [{v.horizon} TWAP Lock]",side_label=h,token_id=w,fee_rate=v.fee_rate,p_model=o,close_ts=v.end_ts,extra={"market_id":v.market_id,"condition_id":v.condition_id,"horizon":v.horizon,"start_iso":v.start_iso,"end_iso":v.end_iso,"open_price":q,"mu_twap":m["mu_twap"],"eff_alpha":m["eff_alpha"],"z_lock":m["z_lock"],"cushion_bps":m["cushion_bps"],"rem_seconds_at_entry":m["rem_seconds"]},tp_target_px=None,prefetched_book=bk)
 async def discover_s5m_candles(self,now_ts):
  for j,g in list(self.s5m_candles.items()):
   if g.end_ts<now_ts-3e2:self.s5m_candles.pop(j,None)
  f=int(math.ceil(now_ts/3e2)*300);e=float(f)-now_ts
  if not(35.<=e<=185.):return
  a=("BTC","ETH","SOL")
  for _,(_,l)in self.dominance_pairs.items():
   if l.asset in a and abs(l.end_ts-f)<=2.:self.s5m_candles[f"{l.asset}_5m_{f}"]=l
  for k,i in self.twap_candles.items():
   if i.asset in a and i.horizon=="5m"and abs(i.end_ts-f)<=2.:self.s5m_candles[k]=i
  d=datetime.fromtimestamp(now_ts-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  for h in a:
   if h not in DOMINANCE_SERIES_SLUGS or"5m"not in DOMINANCE_SERIES_SLUGS[h]:continue
   k5=f"{h}_5m_{f}"
   if k5 in self.s5m_candles:continue
   c=DOMINANCE_SERIES_SLUGS[h]["5m"];b=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={c}&closed=false&end_date_min={d}&order=endDate&ascending=true&limit=3",timeout=3.5)
   if isinstance(b,list):
    for ev in b:
     m=parse_twap_candle_event(ev,h,"5m")
     if m and abs(m.end_ts-f)<=2.:self.s5m_candles[k5]=m;break
 async def scan_s5m_chainlink_sniper(self,opps_out,now_ts=None):
  if not self.single_scan and is_shadow_sleeve_quarantined("S5M_CHAINLINK_SNIPER"):
   if self.s5m_candles:self.s5m_candles.clear()
   return
  u=float(now_ts if now_ts is not None else time.time());n=math.ceil(u/3e2)*3e2-u
  if 40.<=n<=180. and(u-self.last_s5m_discovery_ts)>=20.:self.last_s5m_discovery_ts=u;await self.discover_s5m_candles(u)
  d=float(getattr(self,"_last_s5m_book_scan_ts",.0)or.0)
  if not self.single_scan and(u-d)<9.5:return
  self._last_s5m_book_scan_ts=u
  for _,r in list(self.s5m_candles.items()):
   i=r.end_ts-u
   if not(45.<=i<=165.)or u<r.start_ts+25.:continue
   m=await self.get_authoritative_open_strike(r)
   if m is None or m<=.0:continue
   t=read_shm_usd_anchor(r.asset,u,max_age_sec=3.)if not self.single_scan else{};g=self.usd_spot_hist.get(r.asset);a=t.get("usd_spot")
   if(not a or float(a)<=.0)and g and(u-float(g[-1][0]))<=5.:a=float(g[-1][1])
   if(not a or float(a)<=.0)and self.usd_direct_flags.get(r.asset,False):a=self.spots.get(r.asset,.0)
   if not a or float(a)<=.0:continue
   c=float(a);b=r.asset not in("BTC","ETH");f=abs(c-m)/m*1e2
   if f<(.14 if b else.085):continue
   e="UP"if c>m else"DOWN";h=self.get_return_bps(r.asset,15.)
   if(e=="UP"and h<-4.)or(e=="DOWN"and h>4.):continue
   l=evaluate_svi_digital_fair_value(r.asset,c,m,i,is_downward=False,dvol_annual_override=.42 if(self.single_scan and"fetch_json"in self.__dict__)else None,now_ts=u);k=float(l["p_yes"]if e=="UP"else l["p_no"]);p=abs(float(l.get("z_sigma")or.0))
   if p<(2.25 if b else 1.35)or k<(.935 if b else.905):continue
   s=r.up_token if e=="UP"else r.down_token;bk=await self.fetch_json(f"{CLOB_URL}/book?token_id={s}",timeout=2.5)
   if not bk:continue
   o=walk_l2_book_asks(bk.get("asks")or[],BANKROLL_TICKETS["T1000"]["S5M_CHAINLINK_SNIPER"],fee_rate=r.fee_rate,min_l1_usd=18.)
   if not o.get("filled"):continue
   j=float(o["eff_px"]);q=k-j
   if.58<=j<=.86 and q>=.025:opps_out.append({"sleeve":"S5M_CHAINLINK_SNIPER","market":f"{r.asset} 5m {e} (TTE={i:.0f}s, dist={f:.3f}%, z={p:.2f})","ask_vwap":j,"p_model":round(k,4),"net_edge":round(q,4),"l1_usd":o["l1_usd"],"close_ts":r.end_ts})
   if.58<=j<=.86 and q>=(.055 if b else.045):await self.open_shadow_position(sleeve="S5M_CHAINLINK_SNIPER",dedupe_key=f"S5M_{r.asset}_{r.market_id}",asset_or_city=r.asset,title=f"{r.title} [5m Chainlink Sniper]",side_label=e,token_id=s,fee_rate=r.fee_rate,p_model=k,close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"horizon":"5m","start_iso":r.start_iso,"end_iso":r.end_iso,"open_price":m,"dist_pct":round(f,4),"z_sigma":p},tp_target_px=.96,prefetched_book=bk)
 async def discover_upcoming_15m_candles(self,now_ts):
  for i,f in list(self.preopen_15m_candles.items()):
   if f.start_ts<=now_ts+5.:self.preopen_15m_candles.pop(i,None)
  a=int(math.ceil(now_ts/9e2)*900);b=float(a)-now_ts
  if not(25.<=b<=250.):return
  e=datetime.fromtimestamp(now_ts,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  for h in("BTC","ETH"):
   g=f"{h}_pre15m_{a}"
   if g in self.preopen_15m_candles:continue
   d=DOMINANCE_SERIES_SLUGS[h]["15m"];c=await self.fetch_json(f"{GAMMA_URL}/events?series_slug={d}&closed=false&end_date_min={e}&order=endDate&ascending=true&limit=5",timeout=3.5)
   if isinstance(c,list):
    for ev in c:
     j=parse_twap_candle_event(ev,h,"15m")
     if j and abs(j.start_ts-a)<=2.:self.preopen_15m_candles[g]=j;break
 async def scan_and_manage_preopen_maker_straddles(self,opps_out,now_ts=None):
  if is_shadow_sleeve_quarantined("P1_PREOPEN_MAKER_STRADDLE"):
   if self.pending_preopen_straddles:self.pending_preopen_straddles.clear()
   return
  M=float(now_ts if now_ts is not None else time.time());c=int(math.ceil(M/9e2)*900);l=float(c)-M
  if 25.<=l<=250. and(M-self.last_preopen_discovery_ts)>=20.:self.last_preopen_discovery_ts=M;await self.discover_upcoming_15m_candles(M)
  A=float(getattr(self,"_last_p1_manage_ts",.0)or.0)
  if not self.single_scan and not self.pending_preopen_straddles and not(30.<=l<=245.):return
  if not self.single_scan and(M-A)<8.:return
  self._last_p1_manage_ts=M
  for o,st in list(self.pending_preopen_straddles.items()):
   w=st["spec"];n,m=await asyncio.gather(self.fetch_json(f"{CLOB_URL}/book?token_id={w.up_token}",timeout=2.5),self.fetch_json(f"{CLOB_URL}/book?token_id={w.down_token}",timeout=2.5));H=float(st["bid_px"]);t=M-float(st["posted_ts"])
   if n and t>=4.:
    asks_up=n.get("asks")or[];k=min((float(a["price"])for a in asks_up if float(a.get("size",0))>0),default=1.)
    if k<=H:st["up_filled"]=True
   if m and t>=4.:
    asks_dn=m.get("asks")or[];j=min((float(a["price"])for a in asks_dn if float(a.get("size",0))>0),default=1.)
    if j<=H:st["dn_filled"]=True
   if st["up_filled"]and st["dn_filled"]:
    self.pending_preopen_straddles.pop(o,None);v=round(2.*H,4);s={}
    for e,q in BANKROLL_TICKETS.items():sh=max(5.,float(math.floor(q["P1_PREOPEN_MAKER_STRADDLE"]/max(.9,v))));I=round(sh*v,2);s[e]={"filled":True,"vwap":v,"eff_px":v,"spent_usd":I,"fee_usd":.0,"shares":sh,"l1_usd":1e2}
    G=f"P1_PREOPEN_MAKER_STRADDLE_{int(M)}_{w.market_id[-6:]}";K=[{"token_id":w.up_token,"side":"UP","market_id":w.market_id,"label":"PRE_UP"},{"token_id":w.down_token,"side":"DOWN","market_id":w.market_id,"label":"PRE_DOWN"}];L={"position_id":G,"dedupe_key":o,"sleeve":"P1_PREOPEN_MAKER_STRADDLE","asset_or_city":w.asset,"title":f"{w.title} [Pre-Open Maker $0.48+$0.48]","side":"PRE_UP+PRE_DOWN","token_id":f"{w.up_token}|{w.down_token}","fee_rate":.0,"entry_ts":M,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":w.end_ts,"p_model_entry":1.,"entry_eff_px_t1000":v,"entry_vwap_t1000":v,"realized_edge_t1000":round(1.-v,4),"entry_best_bid":v,"last_bid":v,"maker_tp_px":None,"tier_fills":s,"extra":{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"market_id":w.market_id,"legs":K},"status":"OPEN"};self.open_positions[G]=L;self.entered_keys.add(o);self._append_ledger({"event":"SHADOW_ENTRY",**L});logger.info(f"[ENTRY:P1_PREOPEN_MAKER_STRADDLE] {L['title']} | BOTH LEGS FILLED @ ${v:.2f} -> $1.00 lock!");continue
   y=float(self.spots.get(w.asset)or st["posted_spot"]or.0);i=float(st["posted_spot"]or y or 1.);x=abs(y-i)/max(1e-9,i)*1e4
   if M>=(w.start_ts-10.)or x>18.:
    self.pending_preopen_straddles.pop(o,None);self.entered_keys.add(o)
    if not st["up_filled"]and not st["dn_filled"]:continue
    u=bool(st["up_filled"]);F=n if u else m;b,_=extract_best_bid((F or{}).get("bids")or[])
    if b<=.0:b=max(.01,H-.03)
    g=w.fee_rate*b*(1.-b);r=max(.0,b-g);f={};h={}
    for e,q in BANKROLL_TICKETS.items():J=max(5.,float(math.floor(q["P1_PREOPEN_MAKER_STRADDLE"]/max(.9,2.*H))));p=round(J*H,2);f[e]={"filled":True,"vwap":H,"eff_px":H,"spent_usd":p,"fee_usd":.0,"shares":J};h[e]=round(J*r-p,2)
    z={"position_id":f"P1_SCRATCH_{int(M)}_{w.market_id[-6:]}","dedupe_key":o,"sleeve":"P1_PREOPEN_MAKER_STRADDLE","asset_or_city":w.asset,"title":f"{w.title} [Pre-Open 1-Leg Scratch]","side":"PRE_UP_SCRATCH"if u else"PRE_DOWN_SCRATCH","token_id":w.up_token if u else w.down_token,"fee_rate":.0,"entry_ts":st["posted_ts"],"entry_utc":datetime.fromtimestamp(st["posted_ts"],tz=timezone.utc).isoformat(),"close_ts":w.end_ts,"closed_ts":M,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":.5,"entry_eff_px_t1000":H,"entry_vwap_t1000":H,"net_payout_per_share":round(r,4),"tier_fills":f,"tier_pnls_usd":h,"won":h.get("T1000",.0)>0,"status":"PREOPEN_ONE_LEG_SCRATCH"};self.closed_positions.append(z);self._append_ledger({"event":"SHADOW_CLOSE",**z});logger.info(f"[CLOSE:P1_PREOPEN_MAKER_STRADDLE] {z['title']} -> PREOPEN_ONE_LEG_SCRATCH | bid_exit=${b:.3f} net=${r:.4f} | PnL T1000=${h.get('T1000',.0):+.2f}")
  for _,w in list(self.preopen_15m_candles.items()):
   d=w.start_ts-M
   if not(40.<=d<=240.):continue
   o=f"P1_{w.asset}_{w.market_id}"
   if o in self.entered_keys or o in self.pending_preopen_straddles:continue
   if abs(self.get_return_bps(w.asset,15.))>8.:continue
   n,m=await asyncio.gather(self.fetch_json(f"{CLOB_URL}/book?token_id={w.up_token}",timeout=2.5),self.fetch_json(f"{CLOB_URL}/book?token_id={w.down_token}",timeout=2.5))
   if not n or not m:continue
   E,_=extract_best_bid(n.get("bids")or[]);D,_=extract_best_bid(m.get("bids")or[]);asks_up=n.get("asks")or[];asks_dn=m.get("asks")or[];C=min((float(a["price"])for a in asks_up if float(a.get("size",0))>0),default=1.);B=min((float(a["price"])for a in asks_dn if float(a.get("size",0))>0),default=1.)
   if C>=.49 and B>=.49 and.44<=E<=.51 and.44<=D<=.51:opps_out.append({"sleeve":"P1_PREOPEN_MAKER_STRADDLE","market":f"{w.asset} Pre-Open 15m Straddle (T-{d:.0f}s, asks={C:.2f}/{B:.2f})","ask_vwap":.96,"p_model":1.,"net_edge":.04,"l1_usd":1e2,"close_ts":w.end_ts});self.pending_preopen_straddles[o]={"spec":w,"bid_px":.48,"posted_ts":M,"posted_spot":float(self.spots.get(w.asset)or.0),"up_filled":False,"dn_filled":False};logger.info(f"[MAKER_POST:P1_PREOPEN_MAKER_STRADDLE] {w.title} | Resting $0.48 UP + $0.48 DOWN (T-{d:.0f}s)")
 async def resolve_via_gamma_market(self,pos):
  d=pos.get("extra")or{};e=str(d.get("market_id")or"");g=str(pos.get("token_id")or"");gm=None
  if e:
   f=await self.fetch_json(f"{GAMMA_URL}/markets/{e}",timeout=4.)
   if isinstance(f,dict):gm=f
  if gm is None and g:
   b=await self.fetch_json(f"{GAMMA_URL}/markets?clob_token_ids={g}",timeout=4.)
   if isinstance(b,list)and b:gm=b[0]
  if not isinstance(gm,dict)or not gm.get("closed"):return None
  c=str(gm.get("umaResolutionStatus")or"").strip().lower()
  if c and c!="resolved":return None
  toks=gm.get("clobTokenIds")
  if isinstance(toks,str):
   try:toks=json.loads(toks)
   except Exception:toks=[]
  op=gm.get("outcomePrices")
  if isinstance(op,str):
   try:op=json.loads(op)
   except Exception:op=[]
  if not isinstance(op,list)or len(op)<2:return None
  a=-1
  if isinstance(toks,list)and g in[str(t)for t in toks]:a=[str(t)for t in toks].index(g)
  else:a=0 if str(pos.get("side","YES")).upper()in("YES","UP")else 1
  if a<0 or a>=len(op):return None
  try:px=float(op[a])
  except Exception:return None
  if px>=.99:return 1.
  if px<=.01:return.0
  if c=="resolved"and.49<=px<=.51:return round(px,4)
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
  for i,tf in d.items():
   l=float(tf.get("shares")or.0)
   if l<=.0:continue
   wt=walk_position_overround_bid_unwind(legs_bids_spec,l,min_net_proceeds_per_set=a)
   if not wt.get("filled"):return None
   c[i]=float(wt["net_proceeds_per_set"])
  return float(j["net_proceeds_per_set"]),c
 async def manage_open_positions(self):
  _M=time.time();_I=asyncio.get_running_loop();W=[]
  for _e,_c in list(self.open_positions.items()):
   _l=_c["sleeve"];_L=_c["token_id"]
   if _l=="W3_WEATHER_SLATE_ARB":
    c=float(_c["close_ts"]);_a=_c.get("extra")or{};legs=_a.get("legs")or[]
    if _M<c+30.:
     if(_M-float(_c.get("_last_book_poll_ts")or.0))>=30. and legs:
      _c["_last_book_poll_ts"]=_M;bks_w=await asyncio.gather(*[self.fetch_json(f"{CLOB_URL}/book?token_id={lg.get('token_id')or lg.get('yes_token','')}",timeout=2.5)for lg in legs])
      if all(bks_w):
       _c["last_bid"]=round(sum(extract_best_bid((b or{}).get("bids")or[])[0]for b in bks_w),4);_H=self._try_early_overround_bid_unwind(_c,[{"bids":(b or{}).get("bids")or[],"fee_rate":.0,"fee_exponent":1.}for b in bks_w],_M)
       if _H is not None:W.append((_e,"EARLY_OVERROUND_BID_UNWIND",_H[0],_H[1]))
     continue
    if _M>=c+30.:
     K=float(_a.get("guaranteed_payout")or 1.);resolved_vals=await asyncio.gather(*[self.resolve_via_gamma_market({"token_id":lg.get("token_id")or lg.get("yes_token",""),"side":lg.get("side","YES"),"extra":{"market_id":lg["market_id"]}})for lg in legs])
     if resolved_vals and all(v is not None for v in resolved_vals):e=round(sum(float(v)for v in resolved_vals if v is not None),4);_G="SETTLED_WEATHER_SLATE_1X"if K<=1.01 else"SETTLED_WEATHER_SLATE_NX";W.append((_e,_G,max(K,e),.0))
    continue
   P=_c.get("extra")or{}
   if _l in("D1_SAME_ORACLE_DOMINANCE_BOX","D1_4H_DOMINANCE_BOX","D1_QUIET_BOOK_BOX","D1_MAKER_ANCHOR_BOX","M3_LADDER_MONO_BOX","B3_BARRIER_MONO_BOX","C1_BINARY_COMPLETE_SET","CM_B3_PYTH_BARRIER_BOX","SP1_NBA_ZERO_FEE_BOX","ZERO_FEE_MAKER_ANCHOR_BOX","ZF_INTRADAY_MAKER_BOX","D2_12PM_BINANCE_BOX")or(P.get("leg_a")and P.get("leg_b")):
    j=_c.get("extra")or{};_A=j.get("leg_a")or{};_z=j.get("leg_b")or{};c=float(_c["close_ts"])
    if _M<c+10.:
     _F,_E=await asyncio.gather(self.fetch_json(f"{CLOB_URL}/book?token_id={_A.get('token_id','')}",timeout=2.5),self.fetch_json(f"{CLOB_URL}/book?token_id={_z.get('token_id','')}",timeout=2.5))
     if _F and _E:
      _y,_=extract_best_bid(_F.get("bids")or[]);_x,_=extract_best_bid(_E.get("bids")or[]);_c["last_bid"]=round(_y+_x,4);_k=float(_c.get("fee_rate")or.0);_D=self._try_early_overround_bid_unwind(_c,[{"bids":_F.get("bids")or[],"fee_rate":float(_A.get("fee_rate",_k)),"fee_exponent":float(_A.get("fee_exponent",1.))},{"bids":_E.get("bids")or[],"fee_rate":float(_z.get("fee_rate",_k)),"fee_exponent":float(_z.get("fee_exponent",1.))}],_M)
      if _D is not None:W.append((_e,"EARLY_OVERROUND_BID_UNWIND",_D[0],_D[1]));continue
     if(_l=="C1_BINARY_COMPLETE_SET"and _A.get("market_id")and _A.get("market_id")==_z.get("market_id")and(_M-float(_c.get("entry_ts")or.0))>=15.):W.append((_e,"CTF_COMPLETE_SET_MERGED",1.,.0));continue
     if _F and _E:continue
     if _F or _E or(_M-float(_c.get("_last_gamma_chk_ts")or.0))<60.:continue
     _c["_last_gamma_chk_ts"]=_M
    _w,_v=await asyncio.gather(self.resolve_via_gamma_market({"token_id":_A.get("token_id",""),"side":_A.get("side","UP"),"extra":{"market_id":_A.get("market_id","")}}),self.resolve_via_gamma_market({"token_id":_z.get("token_id",""),"side":_z.get("side","DOWN"),"extra":{"market_id":_z.get("market_id","")}}))
    if _w is not None and _v is not None:e=round(float(_w)+float(_v),4);f="SETTLED_DOMINANCE_DOUBLE_2X"if e>=1.99 else"SETTLED_DOMINANCE_FLOOR_1X";W.append((_e,f,e,.0));continue
    if _l=="B3_BARRIER_MONO_BOX"and _M>=c+9e2:
     _C=str(j.get("direction")or"UP").upper();_j=await _I.run_in_executor(None,fetch_binance_window_extremes_sync,_c["asset_or_city"],float(_c["entry_ts"]),c,"1m")
     if _j is not None:r,q,_=_j;_i=float(_A.get("strike")or.0);_h=float(_z.get("strike")or.0);_K=(_C=="UP"and r>=_i)or(_C=="DOWN"and q<=_i);_J=(_C=="UP"and r>=_h)or(_C=="DOWN"and q<=_h);e=(1. if _K else.0)+(.0 if _J else 1.);W.append((_e,"SETTLED_BARRIER_MONO_2X"if e>=1.99 else"SETTLED_BARRIER_MONO_1X",e,.0))
     continue
    if _M>=c+360. and j.get("m15_start_iso"):
     _u=14400. if str(_A.get("horizon"))=="4h"else(9e2 if str(_A.get("horizon"))=="15m"else 3e2);_t=14400. if str(_z.get("horizon"))=="4h"else(9e2 if str(_z.get("horizon"))=="15m"else 3e2);V=build_own_gamma_event_url(_c["asset_or_city"],str(_A.get("horizon")or"15m"),c-_u);U=build_own_gamma_event_url(_c["asset_or_city"],str(_z.get("horizon")or"5m"),c-_t);T,S=await asyncio.gather(self.fetch_json(V,timeout=4.),self.fetch_json(U,timeout=4.));_s=parse_closed_gamma_event_settlement(T,str(_A.get("side")or"UP"),V);_r=parse_closed_gamma_event_settlement(S,str(_z.get("side")or"DOWN"),U)
     if _s is not None and _r is not None:e=round(_s+_r,4);f=("SETTLED_ORACLE_DOUBLE_2X"if e>=1.99 else("SETTLED_ORACLE_FLOOR_1X"if e>=.99 else"SETTLED_ORACLE_LOSS_0X"));W.append((_e,f,e,.0))
    continue
   if _l in("N1_NEGRISK_CROSS_BOX","P1_PREOPEN_MAKER_STRADDLE","NR0_ZERO_FEE_SLATE_ARB")or bool(P.get("legs")):
    j=_c.get("extra")or{};legs=j.get("legs")or[];c=float(_c["close_ts"])
    if _M<c+20.:
     if(_M-float(_c.get("_last_book_poll_ts")or.0))>=30. and legs:
      _c["_last_book_poll_ts"]=_M;bks_m=await asyncio.gather(*[self.fetch_json(f"{CLOB_URL}/book?token_id={lg['token_id']}",timeout=2.5)for lg in legs])
      if all(bks_m):
       _c["last_bid"]=round(sum(extract_best_bid((b or{}).get("bids")or[])[0]for b in bks_m),4);def_fr_m=float(_c.get("fee_rate")or.0);_B=self._try_early_overround_bid_unwind(_c,[{"bids":(b or{}).get("bids")or[],"fee_rate":float(lg.get("fee_rate",def_fr_m)),"fee_exponent":float(lg.get("fee_exponent",1.))}for lg,b in zip(legs,bks_m)],_M)
       if _B is not None:W.append((_e,"EARLY_OVERROUND_BID_UNWIND",_B[0],_B[1]))
     continue
    resolved_vals=await asyncio.gather(*[self.resolve_via_gamma_market({"token_id":lg["token_id"],"side":lg.get("side","YES"),"extra":{"market_id":lg.get("market_id","")}})for lg in legs])
    if resolved_vals and all(v is not None for v in resolved_vals):e=round(sum(float(v)for v in resolved_vals if v is not None),4);W.append((_e,"SETTLED_MULTI_LEG_ARB",e,.0))
    elif _l=="P1_PREOPEN_MAKER_STRADDLE"and _M>=c+9e2:W.append((_e,"SETTLED_COMPLETE_SET_1X",1.,.0))
    continue
   if _l=="S2_EXACT_TWAP_LOCK":
    j=_c.get("extra")or{};c=float(_c["close_ts"])
    if _M<c+12.:
     _q=await self.fetch_json(f"{CLOB_URL}/book?token_id={_L}",timeout=2.5)
     if _q:_g,_=extract_best_bid(_q.get("bids")or[]);_c["last_bid"]=_g
     continue
    s=await self.resolve_via_gamma_market(_c)
    if s is not None:f="SETTLED_GAMMA_WIN"if s>=.99 else"SETTLED_GAMMA_LOSS";W.append((_e,f,s,.0));continue
    if _M>=c+120. and j.get("start_iso"):
     C=build_own_gamma_event_url(_c["asset_or_city"],str(j.get("horizon")or"15m"),j["start_iso"]);i=await self.fetch_json(C,timeout=4.);o=parse_authoritative_close_price(i);x=float(j.get("open_price")or.0)
     if o is not None and x>.0:B=o>=x;z=B if str(_c.get("side")).upper()=="UP"else(not B);f="SETTLED_ORACLE_TWAP_WIN"if z else"SETTLED_ORACLE_TWAP_LOSS";W.append((_e,f,1. if z else.0,.0))
    continue
   if _l in("B1_CONVEX_TAIL_YES","B2_BARRIER_NO_LOCK"):
    h=_c["asset_or_city"];k=float(_c["extra"].get("strike")or.0);d=_c["extra"].get("direction");J=float(_c.get("_last_wick_chk_ts")or.0)
    if k>0 and(_M-J)>=60.:
     _c["_last_wick_chk_ts"]=_M;w=float(_c["extra"].get("start_ts")or _c["entry_ts"]);_p=min(_M,float(_c["close_ts"]));_f=await _I.run_in_executor(None,fetch_binance_window_extremes_sync,h,w,_p,"1m")
     if _f is not None:
      r,q,_=_f;u=(d=="UP"and r>=k)or(d=="DOWN"and q<=k)
      if u:A=1. if _c["side"]=="YES"else.0;W.append((_e,"BARRIER_1M_WICK_SETTLED",A,.0));continue
   if(not self.single_scan and not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK")and self.is_in_exact_twap_lock_window(_M)and float(_c["close_ts"])>_M+120. and(_M-float(_c.get("_last_book_poll_ts")or.0))<20.):continue
   _c["_last_book_poll_ts"]=_M;bk=await self.fetch_json(f"{CLOB_URL}/book?token_id={_L}",timeout=3.)
   if bk:
    p,_=extract_best_bid(bk.get("bids")or[]);_c["last_bid"]=p;_o=_c.get("maker_tp_px")
    if _o and p>=float(_o)and(_M-_c["entry_ts"])>=15.:W.append((_e,"MAKER_TP_FILLED",float(_o),.0));continue
    if _l in("M1_SVI_MAKER_SCALP","M4_SHOCK_STRIKE_CATCHUP")and p>0 and(_M-_c["entry_ts"])>=30.:
     l=float(_c["entry_vwap_t1000"]);Z=float(_c["close_ts"])-_M;O=.085 if _l=="M4_SHOCK_STRIKE_CATCHUP"else.075;D=9e2 if _l=="M4_SHOCK_STRIKE_CATCHUP"else 3600.
     if p<=l-O:g=CRYPTO_FEE_RATE*p*(1.-p);W.append((_e,"HARD_STOP_SVI",max(.0,p-g),.0));continue
     if Z<=D:g=CRYPTO_FEE_RATE*p*(1.-p);W.append((_e,"TIME_STOP",max(.0,p-g),.0));continue
    if _l=="M2_STRIKE_CONVERGENCE"and p>0 and(_M-_c["entry_ts"])>=30.:
     l=float(_c["entry_vwap_t1000"])
     if p<=max(.25,l-.22):g=CRYPTO_FEE_RATE*p*(1.-p);W.append((_e,"SALVAGE_STOP",max(.0,p-g),.0));continue
   else:
    I=float(_c.get("_last_gamma_chk_ts")or.0)
    if(_M-I)>=60.:
     _c["_last_gamma_chk_ts"]=_M;s=await self.resolve_via_gamma_market(_c)
     if s is not None:f="SETTLED_GAMMA_WIN"if s>=.99 else"SETTLED_GAMMA_LOSS";W.append((_e,f,s,.0));continue
   if _M>=float(_c["close_ts"])+30.:
    s=await self.resolve_via_gamma_market(_c)
    if s is not None:f="SETTLED_GAMMA_WIN"if s>=.99 else"SETTLED_GAMMA_LOSS";W.append((_e,f,s,.0));continue
    if bk and _l not in("BOND1_UMA_RESOLUTION_CARRY","SP2_NBA_ENDGAME_LOCK"):
     p,_=extract_best_bid(bk.get("bids")or[]);asks=bk.get("asks")or[];R=min((float(a["price"])for a in asks if float(a.get("size",0))>0),default=1.)
     if p>=.99:W.append((_e,"SETTLED_WIN",1.,.0));continue
     if R<=.01:W.append((_e,"SETTLED_LOSS",.0,.0));continue
    if _l in("S5M_CHAINLINK_SNIPER","S4H_CHAINLINK_CONVERGENCE")and _M>=float(_c["close_ts"])+120.:
     j=_c.get("extra")or{}
     if j.get("start_iso"):
      C=build_own_gamma_event_url(_c["asset_or_city"],str(j.get("horizon")or"5m"),j["start_iso"]);i=await self.fetch_json(C,timeout=4.);o=parse_authoritative_close_price(i);x=float(j.get("open_price")or.0)
      if o is not None and x>.0:B=o>=x;z=B if str(_c.get("side")).upper()=="UP"else(not B);f="SETTLED_ORACLE_TWAP_WIN"if z else"SETTLED_ORACLE_TWAP_LOSS";W.append((_e,f,1. if z else.0,.0));continue
    if _M>=float(_c["close_ts"])+9e2:
     if _l in("B1_CONVEX_TAIL_YES","B2_BARRIER_NO_LOCK"):
      h=_c["asset_or_city"];k=float(_c["extra"].get("strike")or.0);d=_c["extra"].get("direction");w=float(_c["extra"].get("start_ts")or _c["entry_ts"]);Y=await _I.run_in_executor(None,fetch_binance_window_extremes_sync,h,w,float(_c["close_ts"]),"1m")
      if Y is not None and k>0:r,q,_=Y;u=(d=="UP"and r>=k)or(d=="DOWN"and q<=k);A=(1. if u else.0)if _c["side"]=="YES"else(.0 if u else 1.);W.append((_e,"SETTLED_VERIFIED_1M_ORACLE",A,.0));continue
     elif _l=="U1_DAILY_UPDOWN_LOCK":
      h=_c["asset_or_city"];k=float(_c["extra"]["strike"]);c=float(_c["close_ts"]);t=await _I.run_in_executor(None,fetch_binance_window_extremes_sync,h,c-120.,c,"1m")
      if t is not None and k>0:m=t[2];z=(m>=k)if str(_c["side"]).upper()=="UP"else(m<k);W.append((_e,"SETTLED_VERIFIED_1M_CLOSE",1. if z else.0,.0));continue
     elif _l in("M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","M4_SHOCK_STRIKE_CATCHUP"):
      h=_c["asset_or_city"];k=float(_c["extra"]["strike"]);_n=bool(_c["extra"].get("is_downward"));c=float(_c["close_ts"]);t=await _I.run_in_executor(None,fetch_binance_window_extremes_sync,h,c-120.,c,"1m")
      if t is not None and k>0:m=t[2];X=(m<k)if _n else(m>k);z=X if _c["side"]=="YES"else(not X);W.append((_e,"SETTLED_VERIFIED_1M_CLOSE",1. if z else.0,.0));continue
  for _e,_d,H,n in W:
   _c=self.open_positions.pop(_e,None)
   if not _c:continue
   N={};y={};Q=(_c.get("extra")or{}).get("legging_drag_usd_by_tier")or{};M=n if isinstance(n,dict)else{}
   for _b,tf in _c["tier_fills"].items():G=float(tf["spent_usd"])+float(tf["fee_usd"]);F=float(M.get(_b,H));E=float(tf["shares"])*F;_m=round(E-G,2);N[_b]=_m;y[_b]=round(_m-float(Q.get(_b,.0)or.0),2)
   L=N.get("T1000",.0)>0;_c.update({"status":_d,"closed_ts":_M,"closed_utc":datetime.now(timezone.utc).isoformat(),"net_payout_per_share":round(H,4),"tier_pnls_usd":N,"legging_adjusted_tier_pnls_usd":y,"won":L});self.closed_positions.append(_c);self._append_ledger({"event":"SHADOW_CLOSE",**_c});logger.info(f"[CLOSE:{_c['sleeve']}] {_c['title']} ({_c['side']}) -> {_d} | PnL T100=${N.get('T100',0):+.2f} T1000=${N.get('T1000',0):+.2f} T5000=${N.get('T5000',0):+.2f}")
 def write_state_files(self,opps):
  if len(getattr(self,"authoritative_strike_cache",{}))>2000:
   for _k in list(self.authoritative_strike_cache.keys())[:-1500]:self.authoritative_strike_cache.pop(_k,None)
  if len(self.entered_keys)>5000:j={str(p.get("dedupe_key")or"")for p in self.open_positions.values()};self.entered_keys=j|set(list(self.entered_keys)[-3000:])
  global_bus=read_global_positions_shm();b=[p for d_name,d_rec in(global_bus.get("daemons")or{}).items()if d_name!="alpha124_shadow"and isinstance(d_rec,dict)for p in(d_rec.get("positions")or[])];f=rank_opportunities_capital_auction(opps,active_global_positions=list(self.open_positions.values())+b)[:25];self.top_opportunities=f;publish_global_positions_shm("alpha124_shadow",self.open_positions.values());h={};e={"T100":.0,"T1000":.0,"T5000":.0}
  for sl in BANKROLL_TICKETS["T1000"].keys():
   is_d1_sl=str(sl).startswith("D1_");all_closed_sl=[p for p in self.closed_positions if p.get("sleeve")==sl];closed_sl=[p for p in all_closed_sl if not(is_d1_sl and p.get("status")!="MAKER_ANCHOR_UNHEDGED_SCRATCH"and float(p.get("entry_eff_px_t1000")or 1.)<.9)];a=len(all_closed_sl)-len(closed_sl);l=[p for p in self.open_positions.values()if p.get("sleeve")==sl];u=sum(1 for p in closed_sl if p.get("won"));m=sum(float(p.get("tier_pnls_usd",{}).get("T1000",.0))for p in closed_sl);g=sum(float(p.get("legging_adjusted_tier_pnls_usd",p.get("tier_pnls_usd",{})).get("T1000",.0))for p in closed_sl)
   for t_k in e:e[t_k]=round(e[t_k]+sum(float(p.get("tier_pnls_usd",{}).get(t_k,.0))for p in closed_sl),2)
   h[sl]={"open":len(l),"closed":len(closed_sl),"wins":u,"losses":len(closed_sl)-u,"win_rate_pct":round(1e2*u/len(closed_sl),2)if closed_sl else.0,"realized_pnl_t1000_usd":round(m,2),"legging_adjusted_pnl_t1000_usd":round(g,2),"excluded_anti_box":a,"quarantined":is_shadow_sleeve_quarantined(sl),"grad8_live_promoted":bool(len(closed_sl)>=8 and u==len(closed_sl)and round(m,2)>.0 and round(g,2)>.0 and not is_shadow_sleeve_quarantined(sl))}
  D1_GRAD_SLEEVES={"D1_SAME_ORACLE_DOMINANCE_BOX","D1_4H_DOMINANCE_BOX","D1_QUIET_BOOK_BOX"};d={}
  for a_dom in DOMINANCE_ASSETS:cl_a=[p for p in self.closed_positions if str(p.get("sleeve")or"")in D1_GRAD_SLEEVES and str(p.get("asset_or_city")or"").upper()==a_dom and(p.get("status")=="MAKER_ANCHOR_UNHEDGED_SCRATCH"or float(p.get("entry_eff_px_t1000")or 1.)>=.9)];t=[p for p in self.open_positions.values()if str(p.get("sleeve")or"")in D1_GRAD_SLEEVES and str(p.get("asset_or_city")or"").upper()==a_dom];k=sum(1 for p in cl_a if p.get("won"));i=sum(float(p.get("tier_pnls_usd",{}).get("T1000",.0))for p in cl_a);c=sum(float(p.get("legging_adjusted_tier_pnls_usd",p.get("tier_pnls_usd",{})).get("T1000",.0))for p in cl_a);d[a_dom]={"open":len(t),"closed":len(cl_a),"wins":k,"losses":len(cl_a)-k,"win_rate_pct":round(1e2*k/len(cl_a),2)if cl_a else.0,"realized_pnl_t1000_usd":round(i,2),"legging_adjusted_pnl_t1000_usd":round(c,2)}
  s={"updated_at_utc":datetime.now(timezone.utc).isoformat(),"started_at":self.started_at,"cycle_count":self.cycle_count,"calibration":{"weather_sigma_c":self.weather_sigma_c,"barrier_wick_mult":self.barrier_wick_mult},"spots":self.spots,"markets_monitored":{"weather_city_events":len(self.weather_events),"barrier_hit_rungs":len(self.barrier_rungs),"multistrike_ladders":len(self.strike_ladders),"negrisk_bracket_ladders":len(self.negrisk_ladders),"daily_updown_markets":len(self.daily_updown_markets),"pyth_daily_markets":len(self.pyth_daily_markets),"pyth_barrier_rungs":len(self.pyth_barrier_rungs),"pyth_close_ladders":len(self.pyth_close_ladders),"nba_zero_fee_games":len(self.nba_games),"live_nba_scoreboard_games":len(self.live_nba_board),"uma_proposed_markets":len(self.uma_proposed_markets),"negrisk_zero_fee_slates":len(self.negrisk_zero_slates),"counting_slates":len(self.counting_slates),"fomc_lp_markets":len(self.fomc_truth_legs)//2,"oil_senate_markets":len(self.oil_senate_truth_legs)//2,"hourly_12pm_pairs":len(self.hourly_12pm_markets),"same_oracle_dominance_pairs":len(self.dominance_pairs),"dominance_4h_pairs":len(self.dominance_4h_pairs),"exact_twap_lock_candles":len(self.twap_candles),"s5m_sniper_candles":len(self.s5m_candles),"s4h_candles":len(self.s4h_candles),"preopen_15m_candles":len(self.preopen_15m_candles)},"portfolio_realized_pnl_by_bankroll_usd":e,"by_sleeve":h,"per_strategy":h,"by_d1_asset":d,"open_positions_count":len(self.open_positions),"pending_maker_orders_count":len(self.pending_maker_orders),"pending_maker_anchors_count":len(self.pending_maker_anchors),"pending_zero_fee_maker_anchors_count":len(self.pending_zero_fee_maker_anchors),"pending_preopen_straddles_count":len(self.pending_preopen_straddles),"pending_maker_orders":list(self.pending_maker_orders.values()),"open_positions":list(self.open_positions.values()),"recent_closed_positions":self.closed_positions[-30:]};r=STATE_FILE.with_suffix(".tmp");r.write_text(json.dumps(s,indent=2),encoding="utf-8");os.replace(r,STATE_FILE)
  if STATE_FILE==(DATA_DIR/"alpha124_shadow_state.json")or LIVE_ALPHA124_STATE_MIRROR_FILE!=(LIVE_POLYMARKET_DIR/"alpha124_shadow_state.json"):
   try:LIVE_ALPHA124_STATE_MIRROR_FILE.parent.mkdir(parents=True,exist_ok=True);q=LIVE_ALPHA124_STATE_MIRROR_FILE.with_suffix(".tmp");q.write_text(json.dumps({"updated_at_utc":s["updated_at_utc"],"by_sleeve":h,"per_strategy":h,"by_d1_asset":d},indent=2),encoding="utf-8");os.replace(q,LIVE_ALPHA124_STATE_MIRROR_FILE)
   except Exception as exc:pass
  o=OPPS_FILE.with_suffix(".tmp");o.write_text(json.dumps({"updated_at_utc":s["updated_at_utc"],"top_opportunities":f},indent=2),encoding="utf-8");os.replace(o,OPPS_FILE);n=time.time()
  if(n-float(getattr(self,"_last_proj_write_ts",.0)))>=60.:
   self._last_proj_write_ts=n
   try:from scripts.polymarket_daily_projections import write_live_projections_atomic;write_live_projections_atomic(days=30)
   except Exception as exc:pass
 async def write_state_files_async(self,opps):await asyncio.to_thread(self.write_state_files,opps)
 async def _run_bg_discovery(self):
  try:await self.discover_all_markets()
  except Exception as exc:logger.warning(f"Background discovery notice: {exc}")
 async def _run_bg_mid_crypto(self):
  try:a=[];await self.scan_multistrike_markets(a);await self.scan_daily_updown_locks(a);await self.scan_barrier_markets(a);self.cached_mid_opps=a
  except Exception as exc:logger.warning(f"Background mid-crypto scan notice: {exc}")
 async def _run_bg_weather(self):
  try:a=[];await self.scan_weather_markets(a);self.cached_weather_opps=a
  except Exception as exc:logger.warning(f"Background weather scan notice: {exc}")
 async def _get_pyth_intraday(self,asset,now_ts):
  e=PYTH_ASSET_CONFIG.get(asset.upper())
  if not e:return None
  c,_,_,_,a=e;b=self.pyth_intraday_cache.get(c)
  if b is not None and(now_ts-b[0])<90.:return b[1]
  d=await asyncio.to_thread(fetch_yahoo_1m_intraday_sync,c,a)
  if d is not None:self.pyth_intraday_cache[c]=(now_ts,d)
  return d
 async def scan_tradfi_and_sports_markets(self,opps_out):
  now=time.time();e=sorted({r.asset for r in self.pyth_barrier_rungs.values()if r.end_ts>now+120}|{rgs[0].asset for rgs in self.pyth_close_ladders.values()if rgs and rgs[0].end_ts>now+120});t={}
  for _Q in e:
   fd=await self._get_pyth_intraday(_Q,now)
   if fd:t[_Q]=fd
  near_hit=[]
  for r in self.pyth_barrier_rungs.values():
   if r.end_ts<=now+120 or r.asset not in t:continue
   E=float(t[r.asset]["spot"])
   if E>0 and abs(math.log(r.strike/E))<=.25:near_hit.append(r)
  near_close=[]
  for rgs in self.pyth_close_ladders.values():
   for rc in rgs:
    if rc.end_ts<=now+120 or rc.asset not in t:continue
    E=float(t[rc.asset]["spot"])
    if E>0 and abs(math.log(rc.strike/E))<=.14:near_close.append(rc)
  Q=([r.yes_token for r in near_hit]+[r.no_token for r in near_hit]+[rc.yes_token for rc in near_close]+[rc.no_token for rc in near_close]);_g=await self.fetch_books_batch(Q,timeout=3.5)if Q else{};all_hit_rows=[];f=collections.defaultdict(list)
  for r in near_hit:
   _f,w=_g.get(r.yes_token),_g.get(r.no_token)
   if not _f or not w:continue
   _P=PYTH_ASSET_CONFIG[r.asset];_,j,i,d,_=_P;fd=t[r.asset];_V=float(fd["spot"]);k=now>=r.start_ts;_aq=window_extremes_from_bars(fd["bars"],r.start_ts,now)if k else None
   if k and now>=r.start_ts+3e2 and i and j in("EQUITY_RTH","CME_23H")and _aq is not None and f"B4_PYTH_{r.market_id}"not in self.entered_keys:
    _aQ,_aP=_aq;_U=.0015 if j=="EQUITY_RTH"else max(.008,2.5*d);D=.78 if j=="EQUITY_RTH"else.88
    if(r.direction=="UP"and _aQ>=r.strike*(1.+_U))or(r.direction=="DOWN"and _aP<=r.strike*(1.-_U)):
     _z,_=extract_best_bid(_f.get("bids")or[]);_ap=walk_l2_book_asks(_f.get("asks")or[],1e2,fee_rate=r.fee_rate,min_l1_usd=15.,max_ask_px=.99,fee_exponent=r.fee_exponent)
     if _ap.get("filled")and _z>=D and.85<=float(_ap["eff_px"])<=.986:opps_out.append({"sleeve":"B4_TOUCHED_BARRIER_WICK_LOCK","market":f"{r.asset} Pyth Breached Wick Lock: {r.question}","ask_vwap":_ap["eff_px"],"p_model":1.,"net_edge":round(1.-float(_ap["eff_px"]),4),"l1_usd":_ap["l1_usd"]});await self.open_shadow_position(sleeve="B4_TOUCHED_BARRIER_WICK_LOCK",dedupe_key=f"B4_PYTH_{r.market_id}",asset_or_city=r.asset,title=r.question,side_label="YES",token_id=r.yes_token,fee_rate=r.fee_rate,p_model=1.,close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"strike":r.strike,"direction":r.direction,"session_class":j,"fee_exponent":r.fee_exponent},prefetched_book=_f);continue
   _e=walk_l2_book_asks(_f.get("asks")or[],35.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);_d=walk_l2_book_asks(w.get("asks")or[],35.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);_ao={"asset":r.asset,"event_id":r.event_id,"strike":r.strike,"direction":r.direction,"market_id":r.market_id,"condition_id":r.condition_id,"yes_token":r.yes_token,"no_token":r.no_token,"fee_rate":r.fee_rate,"fee_exponent":r.fee_exponent,"ask_yes":_e.get("vwap")if _e.get("filled")else None,"ask_no":_d.get("vwap")if _d.get("filled")else None,"bk_yes":_f,"bk_no":w,"start_ts":r.start_ts,"end_ts":r.end_ts};all_hit_rows.append(_ao);f[r.event_id].append(_ao);_y=compute_effective_trading_hours(now,r.end_ts,j);P=is_same_continuous_session(now,r.end_ts,j);y=_aq is not None and((r.direction=="UP"and _aq[0]>=r.strike*(1.-d))or(r.direction=="DOWN"and _aq[1]<=r.strike*(1.+d)))
   if k and i and P and not y and.25<=_y<=3.5:
    _an=evaluate_pyth_session_barrier_no_lock(_V,r.strike,r.direction,_y,float(fd["sigma_session"]),d);_T=float(_an["p_no"])
    if _T>=.94:
     _S,_=extract_best_bid(w.get("bids")or[]);_aO=walk_l2_book_asks(w.get("asks")or[],1e2,fee_rate=r.fee_rate,min_l1_usd=15.,fee_exponent=r.fee_exponent)
     if _aO.get("filled")and.78<=float(_aO["eff_px"])<=.955 and _S>0 and(float(_aO["vwap"])-_S)<=.04:
      _x=_T-float(_aO["eff_px"]);_aN=evaluate_barrier_no_net_ev(1.-_T,float(_aO["vwap"]),fee_rate=r.fee_rate)
      if _x>=.025:opps_out.append({"sleeve":"CM_B2_PYTH_SESSION_NO_LOCK","market":f"{r.asset} Pyth NO ({_y:.1f}h sess): {r.question}","ask_vwap":_aO["eff_px"],"p_model":_T,"net_edge":round(_x,4),"l1_usd":_aO["l1_usd"]})
      if _x>=.035 and _aN["eligible"]:await self.open_shadow_position(sleeve="CM_B2_PYTH_SESSION_NO_LOCK",dedupe_key=f"CMB2_{r.market_id}",asset_or_city=r.asset,title=r.question,side_label="NO",token_id=r.no_token,fee_rate=r.fee_rate,p_model=_T,close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"strike":r.strike,"direction":r.direction,"eff_session_hours":round(_y,2),"fee_exponent":r.fee_exponent},prefetched_book=w)
   _w=self.prev_pyth_spots.get(r.asset,.0)
   if k and i and P and not y and _w>.0:
    _am=evaluate_pyth_catalyst_shock(r.asset,_w,_V,r.strike,r.direction,_y,float(fd["sigma_session"]),now)
    if _am.get("eligible"):
     _v=str(_am["side"]);_R=r.yes_token if _v=="YES"else r.no_token;_al=_f if _v=="YES"else w;_aM=walk_l2_book_asks(_al.get("asks")or[],BANKROLL_TICKETS["T1000"]["CM_SHOCK_PYTH_CATALYST"],fee_rate=r.fee_rate,min_l1_usd=15.,fee_exponent=r.fee_exponent)
     if _aM.get("filled")and.18<=float(_aM["eff_px"])<=.88:
      _u=float(_am["p_fair"])-float(_aM["eff_px"])
      if _u>=.045:opps_out.append({"sleeve":"CM_SHOCK_PYTH_CATALYST","market":f"{r.asset} [{_am['catalyst']}] {_v}: {r.question}","ask_vwap":_aM["eff_px"],"p_model":_am["p_fair"],"net_edge":round(_u,4),"l1_usd":_aM["l1_usd"],"close_ts":r.end_ts});await self.open_shadow_position(sleeve="CM_SHOCK_PYTH_CATALYST",dedupe_key=f"CMSHK_{r.market_id}_{_v}_{int(now//900)}",asset_or_city=r.asset,title=f"{r.question} [{_am['catalyst']}]",side_label=_v,token_id=_R,fee_rate=r.fee_rate,p_model=float(_am["p_fair"]),close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"catalyst":_am["catalyst"],"delta_p":_am["delta_p"],"ret_pct":_am["ret_pct"],"fee_exponent":r.fee_exponent},tp_target_px=min(.95,round(float(_aM["eff_px"])+.06,3)),prefetched_book=_al)
  for _Q,_aL in t.items():self.prev_pyth_spots[_Q]=float(_aL["spot"])
  n=[]
  for rc in near_close:
   _f,w=_g.get(rc.yes_token),_g.get(rc.no_token)
   if not _f or not w:continue
   _e=walk_l2_book_asks(_f.get("asks")or[],35.,fee_rate=rc.fee_rate,min_l1_usd=8.,fee_exponent=rc.fee_exponent);_d=walk_l2_book_asks(w.get("asks")or[],35.,fee_rate=rc.fee_rate,min_l1_usd=8.,fee_exponent=rc.fee_exponent);n.append({"asset":rc.asset,"strike":rc.strike,"is_downward":rc.is_downward,"market_id":rc.market_id,"condition_id":rc.condition_id,"yes_token":rc.yes_token,"no_token":rc.no_token,"fee_rate":rc.fee_rate,"fee_exponent":rc.fee_exponent,"ask_yes":_e.get("vwap")if _e.get("filled")else None,"ask_no":_d.get("vwap")if _d.get("filled")else None,"bk_yes":_f,"bk_no":w,"end_ts":rc.end_ts});_P=PYTH_ASSET_CONFIG[rc.asset];_,j,i,d,_=_P;fd=t[rc.asset];O=compute_effective_trading_hours(now,rc.end_ts,j)
   if i and is_same_continuous_session(now,rc.end_ts,j)and.08<=O<=.75:
    _ak=evaluate_pyth_session_close_lock(float(fd["spot"]),rc.strike,rc.is_downward,O,float(fd["sigma_session"]),d)
    if _ak["eligible"]:
     _O=str(_ak["side"]);_aj=rc.yes_token if _O=="YES"else rc.no_token;_aK=_f if _O=="YES"else w;_N,_=extract_best_bid(_aK.get("bids")or[]);_aJ=walk_l2_book_asks(_aK.get("asks")or[],1e2,fee_rate=rc.fee_rate,min_l1_usd=15.,fee_exponent=rc.fee_exponent)
     if _aJ.get("filled")and.78<=float(_aJ["eff_px"])<=.955 and _N>0 and(float(_aJ["vwap"])-_N)<=.04:
      _t=float(_ak["p_lock"])-float(_aJ["eff_px"])
      if _t>=.02:opps_out.append({"sleeve":"CM_U1_PYTH_CLOSE_LOCK","market":f"{rc.asset} Close Lock ({_O}, z={_ak['z_session']:.2f}): {rc.question}","ask_vwap":_aJ["eff_px"],"p_model":_ak["p_lock"],"net_edge":round(_t,4),"l1_usd":_aJ["l1_usd"]})
      if _t>=.03:await self.open_shadow_position(sleeve="CM_U1_PYTH_CLOSE_LOCK",dedupe_key=f"CMU1_{rc.market_id}_{_O}",asset_or_city=rc.asset,title=rc.question,side_label=_O,token_id=_aj,fee_rate=rc.fee_rate,p_model=float(_ak["p_lock"]),close_ts=rc.end_ts,extra={"market_id":rc.market_id,"condition_id":rc.condition_id,"strike":rc.strike,"z_session":_ak["z_session"],"fee_exponent":rc.fee_exponent},prefetched_book=_aK)
  for a_snap,fd_snap in t.items():
   _ai=PYTH_ASSET_CONFIG.get(a_snap)
   if not _ai:continue
   _,_M,_s,_,_=_ai;C=[rh for rh in all_hit_rows if rh["asset"]==a_snap and rh.get("ask_no")is not None]
   if not C:continue
   N=min(C,key=lambda x:(float(x["end_ts"]),abs(math.log(float(x["strike"])/max(1e-6,float(fd_snap["spot"]))))));_r=compute_effective_trading_hours(now,float(N["end_ts"]),_M);_L=is_same_continuous_session(now,float(N["end_ts"]),_M);_c,_q=extract_best_bid(N["bk_no"].get("bids")or[]);_b,_a=self._best_ask_sz(N["bk_no"]);self._record_market_telemetry(key=f"PYTH_SNAP_{a_snap}",min_interval_sec=120.,now_ts=now,sig=(round(float(fd_snap["spot"]),3),round(_b,3),round(_c,3)),payload={"type":"PYTH_ASSET_SESSION_SNAP","asset":a_snap,"session_class":_M,"exact_directional_ok":_s,"spot":round(float(fd_snap["spot"]),4),"sigma_session":fd_snap["sigma_session"],"eff_session_hours":round(_r,2),"same_session":_L,"near_strike":N["strike"],"near_dir":N["direction"],"near_ask_no":round(_b,4)if _b<1. else None,"near_bid_no":round(_c,4)if _c>0 else None,"near_ask_l1_usd":round(_b*_a,2)if _b<1. else.0})
  m=[]
  for _p,ev_rows in f.items():
   if len(ev_rows)<2:continue
   _K=detect_barrier_monotonicity_boxes(ev_rows,fee_rate=.0,max_box_cost_net=1.15)
   if _K:pd0=_K[0];self._record_market_telemetry(key=f"CMB3_DIAG_{_p}",min_interval_sec=90.,now_ts=now,sig=(pd0["direction"],pd0["low_strike"],pd0["high_strike"],pd0["box_cost_net"]),payload={"type":"PYTH_BARRIER_MONO_BEST","asset":ev_rows[0]["asset"],"event_id":_p,"net_box_l1":pd0["box_cost_net"],"label":pd0["label"]})
   _ah={str(q["yes_token"]):q for q in ev_rows};_ag={str(q["no_token"]):q for q in ev_rows}
   for ba in _K:
    if float(ba["box_cost_net"])>1.035:continue
    qy,qn=_ah.get(ba["yes_token"]),_ag.get(ba["no_token"])
    if qy and qn:la={"token_id":ba["yes_token"],"opp_token_id":ba["yes_opp_token"],"condition_id":ba["leg_yes_condition_id"],"side":"YES","label":f"YES_{ba['direction']}","market_id":ba["leg_yes_market_id"],"fee_rate":float(qy.get("fee_rate",.0)),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(qy["strike"])};lb={"token_id":ba["no_token"],"opp_token_id":ba["no_opp_token"],"condition_id":ba["leg_no_condition_id"],"side":"NO","label":f"NO_{ba['direction']}","market_id":ba["leg_no_market_id"],"fee_rate":float(qn.get("fee_rate",.0)),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(qn["strike"])};m.append((qy["asset"],f"CMB3_MONO_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",la,lb,qy["bk_yes"],qn["bk_no"],float(qy["end_ts"]),f"{qy['asset']} Pyth Box {ba['label']}"))
  Z=detect_pyth_calendar_inclusion_boxes(all_hit_rows,max_box_cost_net=1.15)
  if Z:cd0=Z[0];self._record_market_telemetry(key=f"CMB3_CAL_BEST_{cd0['asset']}",min_interval_sec=90.,now_ts=now,sig=(cd0["direction"],cd0["strike"],cd0["box_cost_net"]),payload={"type":"PYTH_CALENDAR_BEST","asset":cd0["asset"],"net_box_l1":cd0["box_cost_net"],"label":cd0["label"]})
  for cal in Z:
   if float(cal["box_cost_net"])>1.035:continue
   qy,qn=cal["yes_row"],cal["no_row"];la={"token_id":qy["yes_token"],"opp_token_id":qy["no_token"],"condition_id":qy["condition_id"],"side":"YES","label":"YES_LONG","market_id":qy["market_id"],"fee_rate":float(qy.get("fee_rate",.0)),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(qy["strike"])};lb={"token_id":qn["no_token"],"opp_token_id":qn["yes_token"],"condition_id":qn["condition_id"],"side":"NO","label":"NO_SHORT","market_id":qn["market_id"],"fee_rate":float(qn.get("fee_rate",.0)),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(qn["strike"])};m.append((cal["asset"],f"CMB3_CAL_{qy['market_id']}_{qn['market_id']}",la,lb,qy["bk_yes"],qn["bk_no"],float(cal["close_ts"]),f"{cal['asset']} Calendar Box {cal['label']}"))
  Y=detect_pyth_close_vs_hit_boxes(n,all_hit_rows,now_ts=now,max_box_cost_net=1.15)
  if Y:vd0=Y[0];self._record_market_telemetry(key=f"CMB3_CVH_BEST_{vd0['asset']}",min_interval_sec=90.,now_ts=now,sig=(vd0["strike_hit"],vd0["strike_close"],vd0["box_cost_net"]),payload={"type":"PYTH_CLOSE_VS_HIT_BEST","asset":vd0["asset"],"net_box_l1":vd0["box_cost_net"],"label":vd0["label"]})
  for cvh in Y:
   if float(cvh["box_cost_net"])>1.035:continue
   qy,qn=cvh["yes_row"],cvh["no_row"];la={"token_id":qy["yes_token"],"opp_token_id":qy["no_token"],"condition_id":qy["condition_id"],"side":"YES","label":"YES_HIT","market_id":qy["market_id"],"fee_rate":float(qy.get("fee_rate",.0)),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(qy["strike"])};lb={"token_id":qn["no_token"],"opp_token_id":qn["yes_token"],"condition_id":qn["condition_id"],"side":"NO","label":"NO_CLOSE","market_id":qn["market_id"],"fee_rate":float(qn.get("fee_rate",.0)),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(qn["strike"])};m.append((cvh["asset"],f"CMB3_CVH_{qy['market_id']}_{qn['market_id']}",la,lb,qy["bk_yes"],qn["bk_no"],float(cvh["close_ts"]),f"{cvh['asset']} Close-vs-Hit Box {cvh['label']}"))
  m.sort(key=lambda x:((float(x[6])-now)>64800.,float(x[6])))
  for _o,_J,la,lb,V,U,_aI,_n in m:
   _aH=walk_equal_shares_dominance_box(V.get("asks")or[],U.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["CM_B3_PYTH_BARRIER_BOX"],fee_rate_a=float(la["fee_rate"]),fee_rate_b=float(lb["fee_rate"]),fee_exponent_a=float(la.get("fee_exponent",1.)),fee_exponent_b=float(lb.get("fee_exponent",1.)),max_box_cost_net=.994,min_shares=6,min_box_notional_usd=5.5)
   if _aH.get("filled"):
    opps_out.append({"sleeve":"CM_B3_PYTH_BARRIER_BOX","market":_n,"ask_vwap":round(float(_aH["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_aH["box_cost_net"]),4),"l1_usd":_aH["l1_usd"],"close_ts":_aI});c=False
    if float(_aH["box_cost_net"])<=.993 and(_aI-now)<=172800.:c=self.emit_live_two_leg_box_candidate(sleeve_source="CM_B3_PYTH_BARRIER_BOX",box_type="BARRIER_MONO",asset=_o,dedupe_key=_J,leg_a=la,leg_b=lb,bk_a=V,bk_b=U,close_ts=_aI,now_ts=now,k_low=min(float(la.get("strike")or 1e2),float(lb.get("strike")or 1e2)),k_high=max(float(la.get("strike")or 1e2),float(lb.get("strike")or 1e2)))
    if(_aI-now)<=172800.:await self.open_shadow_two_leg_box(sleeve="CM_B3_PYTH_BARRIER_BOX",dedupe_key=_J,asset=_o,title=_n,leg_a=la,leg_b=lb,bk_a=V,bk_b=U,close_ts=_aI,max_box_cost_net=.994,extra={"is_pyth_zero_fee_box":True})
    if not c:self.post_zero_fee_maker_anchor_box("CM_B3",_o,f"ZFA_{_J}",la,lb,V,U,_aI,_n,now,live_emit_only=bool((_aI-now)<=172800.))
   else:self.post_zero_fee_maker_anchor_box("CM_B3",_o,f"ZFA_{_J}",la,lb,V,U,_aI,_n,now)
  for _I in list(self.nba_games.values()):
   if now>_I.tipoff_ts+6.*3600.:self.nba_games.pop(_I.event_id,None);continue
   nba_legs=_I.margin_legs+_I.total_legs;X=sorted({lg.token_id for lg in nba_legs})
   if len(X)<4:continue
   _m=await self.fetch_books_batch(X,timeout=3.5);o={}
   for t_n,w in _m.items():
    _aG,_aF=self._best_ask_sz(w)
    if _aG<1. and _aF*_aG>=8.:o[t_n]=_aG
   W=detect_nba_dominance_boxes(_I,o,max_box_cost_net=1.12)
   if W:
    nd0=W[0];_aE,_aD=nd0["leg_a"],nd0["leg_b"];_aC=_m.get(_aE.token_id)or{};_aB=_m.get(_aD.token_id)or{};aa0,sa0=self._best_ask_sz(_aC);ab0,sb0=self._best_ask_sz(_aB);ba0,_=extract_best_bid(_aC.get("bids")or[]);bb0,_=extract_best_bid(_aB.get("bids")or[]);M=[]
    if ba0>0 and(aa0-ba0)>=.02:M.append(round(min(ba0+.01,aa0-.01)+ab0,4))
    if bb0>0 and(ab0-bb0)>=.02:M.append(round(aa0+min(bb0+.01,ab0-.01),4))
    L=min(M)if M else None;self._record_market_telemetry(key=f"NBA_BOX_{_I.event_id}",min_interval_sec=45.,now_ts=now,sig=(nd0["label"],nd0["box_cost_net"],L),payload={"type":"NBA_ZERO_FEE_BOX_BEST","event_id":_I.event_id,"game":_I.title,"box_kind":nd0["box_kind"],"in_play":bool(now>=_I.tipoff_ts),"sec_from_tipoff":round(now-_I.tipoff_ts,0),"best_label":nd0["label"],"leg_a_ask":round(aa0,4),"leg_a_bid":round(ba0,4)if ba0>0 else None,"leg_b_ask":round(ab0,4),"leg_b_bid":round(bb0,4)if bb0>0 else None,"net_box_l1":nd0["box_cost_net"],"maker_anchor_box_l1":L,"l1_min_usd":round(min(aa0*sa0,ab0*sb0),2),"middle_pts":nd0["middle_width_pts"]})
   for nb in W:
    if float(nb["box_cost_net"])>1.06:continue
    lga,lgb=nb["leg_a"],nb["leg_b"];V,U=_m.get(lga.token_id),_m.get(lgb.token_id)
    if not V or not U:continue
    _aA={"token_id":lga.token_id,"opp_token_id":lga.opp_token_id,"condition_id":lga.condition_id,"side":lga.side_label,"label":lga.display_label,"market_id":lga.market_id,"fee_rate":lga.fee_rate,"fee_exponent":lga.fee_exponent,"strike":float(lga.threshold)};_az={"token_id":lgb.token_id,"opp_token_id":lgb.opp_token_id,"condition_id":lgb.condition_id,"side":lgb.side_label,"label":lgb.display_label,"market_id":lgb.market_id,"fee_rate":lgb.fee_rate,"fee_exponent":lgb.fee_exponent,"strike":float(lgb.threshold)}
    if float(nb["box_cost_net"])>.994:self.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_SP1_{_I.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",_aA,_az,V,U,float(nb["close_ts"]),f"{_I.title} [{nb['label']}]",now,prefetched_books=_m);continue
    _af=walk_equal_shares_dominance_box(V.get("asks")or[],U.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["SP1_NBA_ZERO_FEE_BOX"],fee_rate_a=lga.fee_rate,fee_rate_b=lgb.fee_rate,fee_exponent_a=lga.fee_exponent,fee_exponent_b=lgb.fee_exponent,max_box_cost_net=.994,min_shares=8,min_box_notional_usd=7.)
    if _af.get("filled"):
     opps_out.append({"sleeve":"SP1_NBA_ZERO_FEE_BOX","market":f"NBA {_I.title}: {nb['label']} (mid={nb['middle_width_pts']}pt)","ask_vwap":round(float(_af["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_af["box_cost_net"]),4),"l1_usd":_af["l1_usd"],"close_ts":nb["close_ts"]});a=False
     if float(_af["box_cost_net"])<=.99 and(float(nb["close_ts"])-now)<=86400.:a=self.emit_live_two_leg_box_candidate(sleeve_source="SP1_NBA_ZERO_FEE_BOX",box_type="NBA_DOMINANCE",asset="NBA",dedupe_key=f"SP1_{_I.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",leg_a=_aA,leg_b=_az,bk_a=V,bk_b=U,close_ts=float(nb["close_ts"]),now_ts=now)
     await self.open_shadow_two_leg_box(sleeve="SP1_NBA_ZERO_FEE_BOX",dedupe_key=f"SP1_{_I.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",asset="NBA",title=f"{_I.title} [{nb['label']}]",leg_a=_aA,leg_b=_az,bk_a=V,bk_b=U,close_ts=float(nb["close_ts"]),max_box_cost_net=.994,extra={"is_nba_zero_fee_box":True,"box_kind":nb["box_kind"],"middle_width_pts":nb["middle_width_pts"]})
     if not a:self.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_SP1_{_I.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",_aA,_az,V,U,float(nb["close_ts"]),f"{_I.title} [{nb['label']}]",now,prefetched_books=_m,live_emit_only=True)
    else:self.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_SP1_{_I.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",_aA,_az,V,U,float(nb["close_ts"]),f"{_I.title} [{nb['label']}]",now,prefetched_books=_m)
  l=[]
  for sp_ms in list(self.multi_sport_games.values()):
   if now>sp_ms.start_ts+6.5*3600.:self.multi_sport_games.pop(sp_ms.event_id,None);continue
   if self.single_scan or("fetch_json"in self.__dict__)or now>=(sp_ms.start_ts-86400.):l.append(sp_ms)
  l.sort(key=lambda g:(now<(g.start_ts-9e2),abs(g.start_ts-now)))
  for sp_ms in l[:20]:
   _l=sorted({lg.token_id for lgs in sp_ms.legs_by_scope.values()for lg in lgs})
   if len(_l)<4:continue
   _H=await self.fetch_books_batch(_l,timeout=3.5);v={}
   for t_m,_ay in _H.items():
    _ax,_aw=self._best_ask_sz(_ay)
    if _ax<1. and _ax*_aw>=8.:v[t_m]=_ax
   _k=detect_multi_sport_corridor_boxes(sp_ms,v,max_box_cost_net=1.08)
   if _k:md0=_k[0];self._record_market_telemetry(key=f"SP3_BOX_{sp_ms.event_id}",min_interval_sec=45.,now_ts=now,sig=(md0["label"],md0["box_cost_net"]),payload={"type":"MULTI_SPORT_CORRIDOR_BEST","sport":sp_ms.sport,"event_id":sp_ms.event_id,"game":sp_ms.title,"scope":md0["scope"],"in_play":bool(now>=sp_ms.start_ts),"best_label":md0["label"],"gross_box_l1":md0["box_cost_gross"],"net_box_l1":md0["box_cost_net"],"middle_pts":md0["middle_width_pts"]})
   for cb in _k:
    _ae,_ad=cb["leg_a"],cb["leg_b"];T=max(float(_ae.fee_rate),float(_ad.fee_rate));K=.994 if T==.0 else.99
    if float(cb["box_cost_net"])>(1.045 if T==.0 else K):continue
    _ac,_ab=_H.get(_ae.token_id),_H.get(_ad.token_id)
    if not _ac or not _ab:continue
    _av={"token_id":_ae.token_id,"opp_token_id":_ae.opp_token_id,"condition_id":_ae.condition_id,"side":_ae.side_label,"label":_ae.display_label,"market_id":_ae.market_id,"fee_rate":float(_ae.fee_rate),"fee_exponent":float(_ae.fee_exponent),"neg_risk":bool(_ae.neg_risk),"strike":float(_ae.threshold)};_au={"token_id":_ad.token_id,"opp_token_id":_ad.opp_token_id,"condition_id":_ad.condition_id,"side":_ad.side_label,"label":_ad.display_label,"market_id":_ad.market_id,"fee_rate":float(_ad.fee_rate),"fee_exponent":float(_ad.fee_exponent),"neg_risk":bool(_ad.neg_risk),"strike":float(_ad.threshold)};_G=f"SP3_{sp_ms.event_id}_{_ae.token_id[-8:]}_{_ad.token_id[-8:]}"
    if float(cb["box_cost_net"])>K:
     if T==.0:self.post_zero_fee_maker_anchor_box("SP3_SPORTS",sp_ms.sport,f"ZFA_{_G}",_av,_au,_ac,_ab,float(cb["close_ts"]),f"{sp_ms.title} [{cb['label']}]",now,prefetched_books=_H)
     continue
    _aa=walk_equal_shares_dominance_box(_ac.get("asks")or[],_ab.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["SP3_SPORTS_CORRIDOR_DOMINANCE_BOX"],fee_rate_a=float(_ae.fee_rate),fee_rate_b=float(_ad.fee_rate),fee_exponent_a=float(_ae.fee_exponent),fee_exponent_b=float(_ad.fee_exponent),max_box_cost_net=K,min_shares=8,min_box_notional_usd=7.)
    if _aa.get("filled"):
     opps_out.append({"sleeve":"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX","market":f"{sp_ms.sport} {sp_ms.title}: {cb['label']} (mid={cb['middle_width_pts']}pt)","ask_vwap":round(float(_aa["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_aa["box_cost_net"]),4),"l1_usd":_aa["l1_usd"],"close_ts":cb["close_ts"]});u=.99 if T==.0 else.988
     if float(_aa["box_cost_net"])<=u and(float(cb["close_ts"])-now)<=86400.:self.emit_live_two_leg_box_candidate(sleeve_source="SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",box_type="SPORTS_CORRIDOR",asset=sp_ms.sport,dedupe_key=_G,leg_a=_av,leg_b=_au,bk_a=_ac,bk_b=_ab,close_ts=float(cb["close_ts"]),now_ts=now,k_low=float(_ae.threshold),k_high=float(_ad.threshold))
     await self.open_shadow_two_leg_box(sleeve="SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",dedupe_key=_G,asset=sp_ms.sport,title=f"{sp_ms.sport} {sp_ms.title} [{cb['label']}]",leg_a=_av,leg_b=_au,bk_a=_ac,bk_b=_ab,close_ts=float(cb["close_ts"]),max_box_cost_net=K,extra={"is_sports_corridor_box":True,"sport":sp_ms.sport,"scope":cb["scope"],"box_kind":cb["box_kind"],"middle_width_pts":cb["middle_width_pts"]})
  for sp_nr in sorted(list(self.negrisk_zero_slates.values()),key=lambda s:((float(s.end_ts)-now)>64800.,float(s.end_ts))):
   if sp_nr.end_ts<=now+60:self.negrisk_zero_slates.pop(sp_nr.event_id,None);continue
   _j=[b["yes_token"]for b in sp_nr.brackets]+[b["no_token"]for b in sp_nr.brackets];nr_bks=await self.fetch_books_batch(_j,timeout=3.5)
   if not all(b["yes_token"]in nr_bks and b["no_token"]in nr_bks for b in sp_nr.brackets):continue
   y_l1_pairs=[self._best_ask_sz(nr_bks[b["yes_token"]])for b in sp_nr.brackets];n_l1_pairs=[self._best_ask_sz(nr_bks[b["no_token"]])for b in sp_nr.brackets];_9=sum(p for p,_ in y_l1_pairs);_8=sum(p for p,_ in n_l1_pairs);J=round(min(p*s for p,s in y_l1_pairs),2);I=round(min(p*s for p,s in n_l1_pairs),2);B=round(sum(extract_best_bid(nr_bks[b["yes_token"]].get("bids")or[])[0]for b in sp_nr.brackets),4);A=round(sum(extract_best_bid(nr_bks[b["no_token"]].get("bids")or[])[0]for b in sp_nr.brackets),4);_at=len(sp_nr.brackets);self._record_market_telemetry(key=f"NR0_SLATE_{sp_nr.event_id}",min_interval_sec=60.,now_ts=now,sig=(round(_9,3),round(_8,3)),payload={"type":"ZERO_FEE_NEGRISK_SLATE","series":sp_nr.series_slug,"title":sp_nr.title,"tte_sec":round(sp_nr.end_ts-now,0),"n_open":_at,"sum_yes_l1":round(_9,4),"sum_yes_bids":B,"min_yes_l1_usd":J,"sum_no_l1":round(_8,4),"sum_no_bids":A,"min_no_l1_usd":I,"no_payout":_at-1})
   if _9<=.99:
    _F=[{"token_id":b["yes_token"],"side":"YES","label":f"YES[{b['label']}]","market_id":b["market_id"],"fee_rate":float(b.get("fee_rate",.0))}for b in sp_nr.brackets];_7=walk_equal_shares_multi_leg_box([{"asks":nr_bks[b["yes_token"]].get("asks")or[],"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.))}for b in sp_nr.brackets],target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],guaranteed_payout_per_bundle=1.,max_bundle_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
    if _7.get("filled"):opps_out.append({"sleeve":"NR0_ZERO_FEE_SLATE_ARB","market":f"{sp_nr.title} (ALL {_at} YES)","ask_vwap":round(float(_7["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_7["box_cost_net"]),4),"l1_usd":_7["l1_usd"],"close_ts":sp_nr.end_ts});await self.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB",f"NR0_Y_{sp_nr.event_id}",sp_nr.series_slug.upper(),f"{sp_nr.title} [All-YES Partition]",_F,nr_bks,sp_nr.end_ts,1.,.988,{"is_multi_leg_bundle":True,"guaranteed_payout":1.})
   elif _8<=(_at-1)-.01:
    _as=float(_at-1);_E=[{"token_id":b["no_token"],"side":"NO","label":f"NO[{b['label']}]","market_id":b["market_id"],"fee_rate":float(b.get("fee_rate",.0))}for b in sp_nr.brackets];_6=walk_equal_shares_multi_leg_box([{"asks":nr_bks[b["no_token"]].get("asks")or[],"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.))}for b in sp_nr.brackets],target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],guaranteed_payout_per_bundle=_as,max_bundle_cost_net=round(_as-.012,4),min_shares=6,min_box_notional_usd=5.5)
    if _6.get("filled"):opps_out.append({"sleeve":"NR0_ZERO_FEE_SLATE_ARB","market":f"{sp_nr.title} (ALL {_at} NO)","ask_vwap":round(float(_6["box_cost_net"])/_as,4),"p_model":1.,"net_edge":round((_as-float(_6["box_cost_net"]))/_as,4),"l1_usd":_6["l1_usd"],"close_ts":sp_nr.end_ts});await self.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB",f"NR0_N_{sp_nr.event_id}",sp_nr.series_slug.upper(),f"{sp_nr.title} [All-NO Partition]",_E,nr_bks,sp_nr.end_ts,_as,round(_as-.012,4),{"is_multi_leg_bundle":True,"guaranteed_payout":_as})
   if B>=1.004:await self.execute_ctf_overround_mint_sell(dedupe_key=f"CTF_OVR_NR_{sp_nr.event_id}",asset=sp_nr.series_slug.upper(),title=f"{sp_nr.title} NegRisk Overround Mint-Sell",legs_bids_spec=[{"bids":nr_bks[b["yes_token"]].get("bids")or[],"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.))}for b in sp_nr.brackets],close_ts=sp_nr.end_ts,min_net_proceeds_per_set=1.004,opps_out=opps_out,extra={"overround_kind":"NEGRISK_SLATE","series":sp_nr.series_slug,"event_id":sp_nr.event_id})
  z=[s for s in self.negrisk_convert_slates.values()if s.end_ts>now+60]
  if z:
   S=[]
   for _5 in z:
    for _4 in _5.brackets:
     S.append(_4["no_token"])
     if _5.is_closed_convert_safe:S.append(_4["yes_token"])
   _i=await self.fetch_books_batch(S,timeout=3.5);h={}
   for _ar,_3 in _i.items():
    _2,_1=self._best_ask_sz(_3)
    if _2<1. and _2*_1>=8.:h[_ar]=_2
   for _D in z:
    H=detect_negrisk_no_pair_boxes(_D,h,max_box_cost_net=1.04)
    if H:pa0=H[0];self._record_market_telemetry(key=f"NRCONV_2L_{_D.event_id}",min_interval_sec=60.,now_ts=now,sig=(pa0["label"],pa0["box_cost_net"]),payload={"type":"NEGRISK_NO_PAIR_BEST","event_id":_D.event_id,"title":_D.title[:80],"augmented":_D.neg_risk_augmented,"net_box_l1":pa0["box_cost_net"],"label":pa0["label"]})
    for pa in H:
     _0,_Z=pa["bracket_a"],pa["bracket_b"];G=max(float(_0["fee_rate"]),float(_Z["fee_rate"]));_h=.992 if G==.0 else.988
     if float(pa["box_cost_net"])>_h:continue
     _C,_B=_i.get(_0["no_token"]),_i.get(_Z["no_token"])
     if not _C or not _B:continue
     _Y={"token_id":_0["no_token"],"opp_token_id":_0["yes_token"],"condition_id":_0["condition_id"],"side":"NO","label":f"NO[{_0['label']}]","market_id":_0["market_id"],"fee_rate":float(_0["fee_rate"]),"fee_exponent":float(_0["fee_exponent"]),"neg_risk":True,"strike":1e2};_X={"token_id":_Z["no_token"],"opp_token_id":_Z["yes_token"],"condition_id":_Z["condition_id"],"side":"NO","label":f"NO[{_Z['label']}]","market_id":_Z["market_id"],"fee_rate":float(_Z["fee_rate"]),"fee_exponent":float(_Z["fee_exponent"]),"neg_risk":True,"strike":1e2};_W=walk_equal_shares_dominance_box(_C.get("asks")or[],_B.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],fee_rate_a=float(_0["fee_rate"]),fee_rate_b=float(_Z["fee_rate"]),fee_exponent_a=float(_0["fee_exponent"]),fee_exponent_b=float(_Z["fee_exponent"]),max_box_cost_net=_h,min_shares=8,min_box_notional_usd=7.)
     if _W.get("filled"):
      _A=f"NRCONV_2L_{_D.event_id}_{_0['market_id']}_{_Z['market_id']}";opps_out.append({"sleeve":"NR_CONV_NO_BASKET_ARB","market":f"{_D.title[:50]}: {pa['label']}","ask_vwap":round(float(_W["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_W["box_cost_net"]),4),"l1_usd":_W["l1_usd"],"close_ts":_D.end_ts})
      if(_D.end_ts-now)<=172800. and float(_W["box_cost_net"])<=(.99 if G==.0 else.988):self.emit_live_two_leg_box_candidate(sleeve_source="NR_CONV_NO_BASKET_ARB",box_type="NEGRISK_2LEG",asset="NEGRISK",dedupe_key=_A,leg_a=_Y,leg_b=_X,bk_a=_C,bk_b=_B,close_ts=float(_D.end_ts),now_ts=now)
      await self.open_shadow_two_leg_box(sleeve="NR_CONV_NO_BASKET_ARB",dedupe_key=_A,asset="NEGRISK",title=f"{_D.title} [{pa['label']}]",leg_a=_Y,leg_b=_X,bk_a=_C,bk_b=_B,close_ts=float(_D.end_ts),max_box_cost_net=_h,extra={"is_negrisk_no_pair_box":True,"event_id":_D.event_id,"neg_risk_augmented":_D.neg_risk_augmented})
    if _D.is_closed_convert_safe:
     F=detect_negrisk_convert_positions_arbs(_D,_i,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],min_net_edge_per_share=.005,min_shares=8)
     if F:ca0=F[0];self._record_market_telemetry(key=f"NRCONV_M_{_D.event_id}",min_interval_sec=60.,now_ts=now,sig=(ca0["m_no_legs"],ca0["net_edge_per_share"]),payload={"type":"NEGRISK_CONVERT_ARB_SNAP","event_id":_D.event_id,"title":_D.title[:80],"m_no_legs":ca0["m_no_legs"],"n_total":ca0["n_total"],"net_edge_per_share":ca0["net_edge_per_share"],"shares":ca0["shares"]});await self.execute_negrisk_convert_positions_arb(_D,ca0,_i,opps_out)
     R=detect_nr2_convert_no_subset_arbs(_D,_i,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR2_CONVERT_NO_SUBSET_ARB"],min_edge_pure_cash=.012,min_edge_with_yes_sell=.015,min_shares=6)
     if R:na0=R[0];self._record_market_telemetry(key=f"NR2_SUB_{_D.event_id}",min_interval_sec=60.,now_ts=now,sig=(na0["m_no_legs"],na0["net_edge_per_share"],na0["retained_tail_count"]),payload={"type":"NR2_SUBSET_CONVERT_SNAP","event_id":_D.event_id,"title":_D.title[:80],"m_no_legs":na0["m_no_legs"],"n_total":na0["n_total"],"retained_tail_count":na0["retained_tail_count"],"net_edge_per_share":na0["net_edge_per_share"]});await self.execute_nr2_subset_convert_arb(_D,na0,_i,opps_out)
  await self._scan_phase2_macro_counting_gas(opps_out,now);await self._scan_frontier_v2_sleeves(opps_out,now);await self._scan_frontier_v3_sleeves(opps_out,now);await self._scan_frontier_v4_sleeves(opps_out,now)
 async def _scan_frontier_v2_sleeves(self,opps_out,now):
  a=[s for s in self.nba_prop_slates.values()if s.settle_est_ts>now+120]
  for sl_pr in a[:10]:
   y=[t for rgs in sl_pr.props_by_player_stat.values()if len(rgs)>=2 for r in rgs for t in(r.yes_token,r.no_token)]
   if not y:continue
   pr_bks=await self.fetch_books_batch(y,timeout=3.5);w={t:p for t,bk in pr_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.};h=detect_sp4_milestone_ladder_boxes(sl_pr,w,max_box_cost_net=1.045)
   if h:b0=h[0];self._record_market_telemetry(f"SP4_3B_{sl_pr.event_id}",90.,{"type":"SP4_MILESTONE_BOX_BEST","game":sl_pr.title[:60],"label":b0["label"],"net_box_l1":b0["box_cost_net"]},now_ts=now,sig=(b0["label"],b0["box_cost_net"]))
   for bx in h[:8]:
    la,lb=bx["leg_a"],bx["leg_b"];_n,_m=pr_bks.get(la["token_id"]),pr_bks.get(lb["token_id"])
    if not _n or not _m:continue
    J=f"SP4_3B_{la['market_id']}_{lb['market_id']}"
    if float(bx["box_cost_net"])>.992:
     if la.get("market_id")!=lb.get("market_id"):self.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_{J}",la,lb,_n,_m,float(bx["close_ts"]),f"{sl_pr.title} [{bx['label']}]",now,prefetched_books=pr_bks)
     continue
    V=walk_equal_shares_dominance_box(_n.get("asks")or[],_m.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],float(la["fee_rate"]),float(lb["fee_rate"]),fee_exponent_a=float(la.get("fee_exponent",1.)),fee_exponent_b=float(lb.get("fee_exponent",1.)),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
    if V.get("filled"):
     opps_out.append({"sleeve":"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","market":f"NBA Prop Corridor: {bx['label']}","ask_vwap":V["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(V["box_cost_net"]),4),"l1_usd":V["l1_usd"],"close_ts":bx["close_ts"]})
     if float(V["box_cost_net"])<=.99 and(float(bx["close_ts"])-now)<=86400. and la.get("market_id")!=lb.get("market_id"):self.emit_live_two_leg_box_candidate(sleeve_source="SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",box_type="NBA_DOMINANCE",asset="NBA",dedupe_key=J,leg_a=la,leg_b=lb,bk_a=_n,bk_b=_m,close_ts=float(bx["close_ts"]),now_ts=now,k_low=float(bx["line_low"]),k_high=float(bx["line_high"]))
     await self.open_shadow_two_leg_box("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",J,"NBA_PROP",f"{sl_pr.title} [{bx['label']}]",la,lb,_n,_m,float(bx["close_ts"]),.992,{"is_two_leg_box":True,"mode":bx["mode"],"player":bx["player_name"],"stat":bx["stat_type"]})
  e=[tr for tr in self.soccer_trees.values()if tr.end_ts>now+120]
  if e:
   q=[]
   for tr in e[:25]:
    for _l in(tr.home_leg,tr.draw_leg,tr.away_leg):q.extend((_l["yes_token"],_l["no_token"]))
    for tl in tr.totals:q.extend((tl["over_token"],tl["under_token"]))
    for sp in tr.spreads:q.extend((sp["fav_minus_token"],sp["dog_plus_token"]))
   soc_bks=await self.fetch_books_batch(q,timeout=3.5);o={t:p for t,bk in soc_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for tr in e[:25]:
    v=detect_soc1_regulation_boxes(tr,soc_bks,o,max_2leg_cost_net=1.035,min_conv_edge_ps=.01,target_budget_usd=BANKROLL_TICKETS["T1000"]["SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"])
    if v["two_leg_boxes"]:_k=v["two_leg_boxes"][0];self._record_market_telemetry(f"SOC1_{tr.game_id}",90.,{"type":"SOC1_REGULATION_BOX_BEST","game":tr.title[:60],"mode":_k["mode"],"label":_k["label"],"net_box_l1":_k["box_cost_net"]},now_ts=now,sig=(_k["label"],_k["box_cost_net"]))
    for _i in v["two_leg_boxes"][:4]:
     if float(_i["box_cost_net"])>.988:continue
     _h,_g=_i["leg_a"],_i["leg_b"];U,T=soc_bks.get(_h["token_id"]),soc_bks.get(_g["token_id"])
     if not U or not T:continue
     S=walk_equal_shares_dominance_box(U.get("asks")or[],T.get("asks")or[],BANKROLL_TICKETS["T1000"]["SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"],float(_h["fee_rate"]),float(_g["fee_rate"]),fee_exponent_a=float(_h["fee_exponent"]),fee_exponent_b=float(_g["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
     if S.get("filled"):
      I=f"SOC1_2L_{tr.game_id}_{_h['token_id'][-6:]}_{_g['token_id'][-6:]}";opps_out.append({"sleeve":"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX","market":_i["label"],"ask_vwap":S["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(S["box_cost_net"]),4),"l1_usd":S["l1_usd"],"close_ts":tr.end_ts})
      if(float(tr.end_ts)-now)<=259200. and _h.get("market_id")!=_g.get("market_id"):self.emit_live_two_leg_box_candidate(sleeve_source="SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",box_type="SPORTS_CORRIDOR",asset="SOCCER",dedupe_key=I,leg_a=_h,leg_b=_g,bk_a=U,bk_b=T,close_ts=float(tr.end_ts),now_ts=now)
      await self.open_shadow_two_leg_box("SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",I,"SOCCER",_i["label"],_h,_g,U,T,float(tr.end_ts),.988,{"is_two_leg_box":True,"mode":_i["mode"],"game_id":tr.game_id})
    for _f in v["convert_arbs"][:1]:opps_out.append({"sleeve":"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX","market":_f["label"],"ask_vwap":round(1.-float(_f["net_edge_per_share"]),4),"p_model":1.,"net_edge":_f["net_edge_per_share"],"l1_usd":_f["l1_usd"],"close_ts":tr.end_ts})
  lp1_groups=[]
  if self.lp1_bop_legs:lp1_groups.append(("BOP_2026",[lg for lg in self.lp1_bop_legs if float(lg["end_ts"])>now+60]))
  for _e in list(self.lp1_nba_em_bundles.values())[:10]:
   if float(_e["end_ts"])>now+60:lp1_groups.append((f"NBA_EM_{_e['event_id']}",_e["legs"]))
  if lp1_groups:
   n=sorted({str(lg["token_id"])for _,g_lgs in lp1_groups for lg in g_lgs});lp1_bks=await self.fetch_books_batch(n,timeout=3.5);m={t:p for t,bk in lp1_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for R,g_lgs in lp1_groups:
    if len(g_lgs)<4:continue
    g=R.startswith("NBA_EM");d=find_state_matrix_dominance_boxes(g_lgs,m,max_2leg_cost_net=1.045,max_3leg_cost_net=1.03)
    if d:d0=d[0];self._record_market_telemetry(f"LP1_{R}",90.,{"type":"LP1_IMPLICATION_BEST","group":R,"n_legs":d0["n_legs"],"net_box_l1":d0["box_cost_net"],"label":d0["label"]},now_ts=now,sig=(d0["label"],d0["box_cost_net"]))
    for _d in d[:6]:
     lgs_b=_d["legs"]
     if int(_d["n_legs"])==2:
      _c,_b=lgs_b[0],lgs_b[1];Q,P=lp1_bks.get(_c["token_id"]),lp1_bks.get(_b["token_id"])
      if not Q or not P:continue
      H=f"LP1_2L_{R}_{_c['token_id'][-6:]}_{_b['token_id'][-6:]}";f=max(float(_c["fee_rate"]),float(_b["fee_rate"]))
      if float(_d["box_cost_net"])>.993:
       if f==.0 and _c.get("market_id")!=_b.get("market_id"):self.post_zero_fee_maker_anchor_box("SP1_NBA"if g else"LP1_BOP","NBA"if g else"MACRO",f"ZFA_{H}",_c,_b,Q,P,float(_d["close_ts"]),f"{R} [{_d['label']}]",now,prefetched_books=lp1_bks)
       continue
      O=walk_equal_shares_dominance_box(Q.get("asks")or[],P.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"],float(_c["fee_rate"]),float(_b["fee_rate"]),max_box_cost_net=.993,min_shares=6,min_box_notional_usd=5.5)
      if O.get("filled"):
       opps_out.append({"sleeve":"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX","market":f"{R}: {_d['label']}","ask_vwap":O["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(O["box_cost_net"]),4),"l1_usd":O["l1_usd"],"close_ts":_d["close_ts"]});b=.99 if f==.0 else.988
       if float(O["box_cost_net"])<=b:l="COMPLETE_SET"if _c.get("market_id")==_b.get("market_id")else("NBA_DOMINANCE"if g else"MACRO_DOMINANCE");self.emit_live_two_leg_box_candidate(sleeve_source="LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",box_type=l,asset="NBA"if g else"MACRO",dedupe_key=H,leg_a=_c,leg_b=_b,bk_a=Q,bk_b=P,close_ts=float(_d["close_ts"]),now_ts=now)
       await self.open_shadow_two_leg_box("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",H,R,f"{R} {_d['label']}",_c,_b,Q,P,float(_d["close_ts"]),.993,{"is_two_leg_box":True,"min_payout":_d["min_payout"],"jackpot_states":_d["jackpot_states"]})
     elif int(_d["n_legs"])==3 and float(_d["box_cost_net"])<=.991:
      G=walk_equal_shares_multi_leg_box([{"asks":lp1_bks[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":1.}for x in lgs_b],BANKROLL_TICKETS["T1000"]["LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"],1.,.991,min_shares=6,min_box_notional_usd=5.5)
      if G.get("filled"):F=f"LP1_3L_{R}_{'_'.join(x['token_id'][-5:]for x in lgs_b)}";opps_out.append({"sleeve":"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX","market":f"{R} 3L: {_d['label']}","ask_vwap":G["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(G["box_cost_net"]),4),"l1_usd":G["l1_usd"],"close_ts":_d["close_ts"]});await self.open_shadow_multi_leg_bundle("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",F,R,f"{R} 3-Leg {_d['label']}",lgs_b,lp1_bks,float(_d["close_ts"]),1.,.991,{"is_multi_leg_bundle":True,"guaranteed_payout":1.})
  c=[sp for sp in self.esports_bo3_specs.values()if sp.end_ts>now+60]
  if c:
   k=[]
   for i in c[:25]:
    k.extend([i.ml_a_token,i.ml_b_token,i.hc_minus_token,i.hc_plus_token])
    for mt in(i.map1_a_token,i.map1_b_token,i.map2_a_token,i.map2_b_token,i.ou25_over_token,i.ou25_under_token):
     if mt:k.append(mt)
   esp_bks=await self.fetch_books_batch(k,timeout=3.5);j={t:p for t,bk in esp_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for i in c[:25]:
    E=evaluate_api1_esports_bo3_opportunities(i,esp_bks,j,max_middle_cost_net=1.035)
    if E["two_leg_boxes"]:_j=E["two_leg_boxes"][0];self._record_market_telemetry(f"API1_{i.event_id}",90.,{"type":"API1_ESPORTS_BO3_BEST","match":i.title[:60],"mode":_j["mode"],"net_box_l1":_j["box_cost_net"],"forfeit_immune":_j["post_m1_forfeit_immune"]},now_ts=now,sig=(_j["mode"],_j["box_cost_net"]))
    for _a in E["single_leg_locks"]:
     D=esp_bks.get(_a["token_id"]);C=esp_bks.get(_a["opp_token_id"])
     if not D or not C:continue
     u,_=extract_best_bid(C.get("bids")or[])
     if u>.04:continue
     B=walk_l2_book_asks_depth_capped(D.get("asks")or[],BANKROLL_TICKETS["T1000"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],BANKROLL_TICKETS["T100"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],fee_rate=float(_a["fee_rate"]),min_l1_usd=15.,max_ask_px=.978,fee_exponent=float(_a["fee_exponent"]))
     if B.get("filled"):
      N=float(B["eff_px"]);M=round(float(_a["p_lock"])-N,4)
      if.72<=N<=.978 and M>=.018:Z=f"API1_LK_{i.event_id}_{_a['market_id']}";opps_out.append({"sleeve":"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","market":f"Esports BO3 Lock: {_a['display_label']}","ask_vwap":N,"p_model":_a["p_lock"],"net_edge":M,"l1_usd":B["l1_usd"],"close_ts":_a["close_ts"]});self.emit_live_single_leg_lock_candidate(sleeve_source="API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",asset="ESPORTS",dedupe_key=Z,token_id=str(_a["token_id"]),opp_token_id=str(_a["opp_token_id"]),market_id=str(_a["market_id"]),condition_id=str(_a["condition_id"]),side_label=str(_a["side_label"]),display_label=str(_a["display_label"]),bk_win=D,bk_opp=C,fee_rate=float(_a["fee_rate"]),fee_exponent=float(_a["fee_exponent"]),neg_risk=False,close_ts=float(_a["close_ts"]),now_ts=now,max_lock_eff_px=.978,max_opp_bid=.025,hold_to_maturity=True,p_model=float(_a["p_lock"]));await self.open_shadow_position("API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",Z,"ESPORTS_BO3",f"{i.title} [{_a['display_label']}]",str(_a["side_label"]),str(_a["token_id"]),float(_a["fee_rate"]),float(_a["p_lock"]),float(_a["close_ts"]),{"market_id":_a["market_id"],"condition_id":_a["condition_id"],"mode":_a["mode"]},prefetched_book=D)
    for Y in E["two_leg_boxes"]:
     if float(Y["box_cost_net"])>.988:continue
     X,W=Y["leg_a"],Y["leg_b"];L,K=esp_bks.get(X["token_id"]),esp_bks.get(W["token_id"])
     if not L or not K:continue
     A=walk_equal_shares_dominance_box(L.get("asks")or[],K.get("asks")or[],BANKROLL_TICKETS["T1000"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],float(X["fee_rate"]),float(W["fee_rate"]),fee_exponent_a=float(X["fee_exponent"]),fee_exponent_b=float(W["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
     if A.get("filled"):
      z=f"API1_MID_{i.event_id}_{X['market_id']}_{W['market_id']}";opps_out.append({"sleeve":"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","market":Y["label"],"ask_vwap":A["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(A["box_cost_net"]),4),"l1_usd":A["l1_usd"],"close_ts":Y["close_ts"]})
      if bool(Y.get("post_m1_forfeit_immune"))and X.get("market_id")!=W.get("market_id"):self.emit_live_two_leg_box_candidate(sleeve_source="API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",box_type="SPORTS_CORRIDOR",asset="ESPORTS",dedupe_key=z,leg_a=X,leg_b=W,bk_a=L,bk_b=K,close_ts=float(Y["close_ts"]),now_ts=now)
      await self.open_shadow_two_leg_box("API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",z,"ESPORTS_BO3",Y["label"],X,W,L,K,float(Y["close_ts"]),.988,{"is_two_leg_box":True,"mode":Y["mode"],"post_m1_forfeit_immune":Y["post_m1_forfeit_immune"]})
 async def _scan_frontier_v3_sleeves(self,opps_out,now):
  if self.lp2_implication_groups or self.lp2_events_by_slug:
   d={str(lg["token_id"])for _,lgs in self.lp2_implication_groups for lg in lgs if float(lg.get("end_ts")or.0)>now+60}
   for Q in("republican-house-seats-after-the-2026-midterm-elections","republican-senate-seats-after-the-2026-midterm-elections-927","which-party-will-win-the-house-in-2026","which-party-will-win-the-senate-in-2026"):
    _F=self.lp2_events_by_slug.get(Q)or{}
    for _2 in _F.get("markets")or[]:
     if not _2.get("closed"):
      _E=_parse_clob_tokens(_2)
      if _E:d.update(_E)
   if d:
    lp2_bks=await self.fetch_books_batch(sorted(d),timeout=4.);J={t:p for t,bk in lp2_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for I,H in self.lp2_implication_groups:
     _d=find_state_matrix_dominance_boxes(H,J,max_2leg_cost_net=1.045,max_3leg_cost_net=.992)
     if _d:_D=_d[0];self._record_market_telemetry(f"LP2_{I}",90.,{"type":"LP2_DAG_BOX_BEST","group":I,"n_legs":_D["n_legs"],"label":_D["label"],"net_box_l1":_D["box_cost_net"],"jackpot_states":_D["jackpot_states"]},now_ts=now,sig=(_D["label"],_D["box_cost_net"]))
     for bx in _d[:6]:
      if float(bx["box_cost_net"])>.992:continue
      lgs_2=bx["legs"]
      if int(bx["n_legs"])==2:
       _1,_0=lgs_2[0],lgs_2[1];_C,_B=lp2_bks.get(_1["token_id"]),lp2_bks.get(_0["token_id"])
       if not _C or not _B:continue
       _Z=walk_equal_shares_dominance_box(_C.get("asks")or[],_B.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],float(_1["fee_rate"]),float(_0["fee_rate"]),fee_exponent_a=float(_1["fee_exponent"]),fee_exponent_b=float(_0["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
       if _Z.get("filled"):
        _A=f"LP2_{I}_{_1['token_id'][-8:]}_{_0['token_id'][-8:]}";opps_out.append({"sleeve":"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","market":f"{I}: {bx['label']}","ask_vwap":_Z["box_cost_net"],"p_model":float(bx["min_payout"]),"net_edge":round(float(bx["min_payout"])-float(_Z["box_cost_net"]),4),"l1_usd":_Z["l1_usd"],"close_ts":bx["close_ts"]})
        if(self.is_sleeve_grad8_ready("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG")and float(bx["min_payout"])>=1.-1e-6 and float(_Z["box_cost_net"])<=.99 and _1.get("market_id")!=_0.get("market_id")and.0<(float(bx["close_ts"])-now)<=604800.):self.emit_live_two_leg_box_candidate(sleeve_source="LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",box_type="MACRO_DOMINANCE",asset="MACRO",dedupe_key=_A,leg_a=_1,leg_b=_0,bk_a=_C,bk_b=_B,close_ts=float(bx["close_ts"]),now_ts=now,k_low=1e2,k_high=101. if int(bx.get("jackpot_states")or 0)>0 else 1e2)
        await self.open_shadow_two_leg_box("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",_A,I,f"{I}: {bx['label']}",_1,_0,_C,_B,float(bx["close_ts"]),.992,{"is_two_leg_box":True,"group":I,"guaranteed_payout":bx["min_payout"],"max_payout":bx["max_payout"],"jackpot_states":bx["jackpot_states"]})
      elif int(bx["n_legs"])==3 and all(x["token_id"]in lp2_bks for x in lgs_2):
       P=f"LP2_3L_{I}_{'_'.join(x['token_id'][-6:]for x in lgs_2)}";_c=walk_equal_shares_multi_leg_box([{"asks":lp2_bks[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x["fee_exponent"])}for x in lgs_2],BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],float(bx["min_payout"]),.992,min_shares=6,min_box_notional_usd=5.5)
       if _c.get("filled"):opps_out.append({"sleeve":"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","market":f"{I} 3-Leg: {bx['label']}","ask_vwap":_c["box_cost_net"],"p_model":float(bx["min_payout"]),"net_edge":round(float(bx["min_payout"])-float(_c["box_cost_net"]),4),"l1_usd":_c["l1_usd"],"close_ts":bx["close_ts"]});await self.open_shadow_multi_leg_bundle("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",P,I,f"{I} 3-Leg: {bx['label']}",lgs_2,lp2_bks,float(bx["close_ts"]),float(bx["min_payout"]),.992,{"is_multi_leg_bundle":True,"guaranteed_payout":bx["min_payout"],"max_payout":bx["max_payout"]})
    O=await asyncio.to_thread(detect_lp2_seat_convert_implication_arbs,self.lp2_events_by_slug,lp2_bks,BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],1.035)
    if O:
     _z=O[0];self._record_market_telemetry(f"LP2_CONV_{_z['mode']}",90.,{"type":"LP2_CONVERT_MIDDLE_SNAP","mode":_z["mode"],"synthetic_box_cost_net":_z["synthetic_box_cost_net"],"shares_out":_z["shares_out"]},now_ts=now,sig=(_z["mode"],_z["synthetic_box_cost_net"]))
     for cv in O:
      if float(cv["synthetic_box_cost_net"])<=.992:_Y=int(cv["m_no_legs"]);l=float(_Y);q=float(_Y-1)+.992;_b=f"LP2_CV_{cv['mode']}";opps_out.append({"sleeve":"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","market":cv["label"],"ask_vwap":cv["synthetic_box_cost_net"],"p_model":1.,"net_edge":cv["guaranteed_floor_edge_ps"],"l1_usd":cv["l1_usd"],"close_ts":cv["close_ts"]});await self.open_shadow_multi_leg_bundle("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",_b,"LP2_CONVERT",cv["label"],cv["legs"],lp2_bks,float(cv["close_ts"]),l,q,{"is_multi_leg_bundle":True,"guaranteed_payout":l,"mode":cv["mode"],"index_set_int":cv["index_set_int"]})
  b=[s for s in self.nba_subperiod_slates.values()if s.settle_est_ts>now+120]
  for sl_sub in b[:10]:
   a=[t for rgs in sl_sub.ext_props_by_player_stat.values()if len(rgs)>=2 for r in rgs for t in(r.yes_token,r.no_token)];a+=[t for sm in sl_sub.subperiod_markets if sm.period_scope in("1H","Q1")and sm.kind in("ML","SPREAD")for t in(sm.tok_0,sm.tok_1)]
   if not a:continue
   sub_bks=await self.fetch_books_batch(sorted(set(a)),timeout=3.5);G={t:p for t,bk in sub_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.};o=detect_sp4_subperiod_and_ext_prop_boxes(sl_sub,G,max_box_cost_net=1.045)
   if o:sb0=o[0];self._record_market_telemetry(f"SP4_SUB_{sl_sub.event_id}",90.,{"type":"SP4_SUBPERIOD_BOX_BEST","game":sl_sub.title[:60],"mode":sb0["mode"],"label":sb0["label"],"net_box_l1":sb0["box_cost_net"]},now_ts=now,sig=(sb0["label"],sb0["box_cost_net"]))
   for sbx in o[:8]:
    if float(sbx["box_cost_net"])>.992:continue
    _X,_W=sbx["leg_a"],sbx["leg_b"];_y,_x=sub_bks.get(_X["token_id"]),sub_bks.get(_W["token_id"])
    if not _y or not _x:continue
    _V=walk_equal_shares_dominance_box(_y.get("asks")or[],_x.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],float(_X["fee_rate"]),float(_W["fee_rate"]),fee_exponent_a=float(_X.get("fee_exponent",1.)),fee_exponent_b=float(_W.get("fee_exponent",1.)),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
    if _V.get("filled"):
     _w=f"SP4_SUB_{_X['market_id']}_{_W['market_id']}";opps_out.append({"sleeve":"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","market":f"NBA [{sbx['mode']}] {sbx['label']}","ask_vwap":_V["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_V["box_cost_net"]),4),"l1_usd":_V["l1_usd"],"close_ts":sbx["close_ts"]})
     if(self.is_sleeve_grad8_ready("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION")and float(_V["box_cost_net"])<=.99 and _X.get("market_id")!=_W.get("market_id")and.0<(float(sbx["close_ts"])-now)<=259200.):self.emit_live_two_leg_box_candidate(sleeve_source="SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",box_type="NBA_DOMINANCE",asset="NBA",dedupe_key=_w,leg_a=_X,leg_b=_W,bk_a=_y,bk_b=_x,close_ts=float(sbx["close_ts"]),now_ts=now,k_low=float(_X.get("strike")or 1e2),k_high=float(_W.get("strike")or 101.))
     await self.open_shadow_two_leg_box("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",_w,"NBA_SUBPERIOD",f"{sl_sub.title} [{sbx['label']}]",_X,_W,_y,_x,float(sbx["close_ts"]),.992,{"is_two_leg_box":True,"mode":sbx["mode"]})
  active_cal=[sp for sp in self.cal1_ladders.values()if sp.rungs and sp.rungs[-1].end_ts>now+120]
  if active_cal:
   F=sorted({t for sp in active_cal for r in sp.rungs for t in(r.yes_token,r.no_token)});cal_bks=await self.fetch_books_batch(F,timeout=4.);E={t:p for t,bk in cal_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for _a in active_cal:
    n=detect_cal1_monotonic_boxes(_a,E,max_box_cost_net=1.045)
    if n:_9=n[0];self._record_market_telemetry(f"CAL1_{_a.event_id}",90.,{"type":"CAL1_LADDER_BOX_BEST","kind":_a.ladder_kind,"label":_9["label"],"net_box_l1":_9["box_cost_net"]},now_ts=now,sig=(_9["label"],_9["box_cost_net"]))
    for _8 in n[:6]:
     if float(_8["box_cost_net"])>.992:continue
     _U,_T=_8["leg_a"],_8["leg_b"];_v,_u=cal_bks.get(_U["token_id"]),cal_bks.get(_T["token_id"])
     if not _v or not _u:continue
     _S=walk_equal_shares_dominance_box(_v.get("asks")or[],_u.get("asks")or[],BANKROLL_TICKETS["T1000"]["CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"],float(_U["fee_rate"]),float(_T["fee_rate"]),fee_exponent_a=float(_U["fee_exponent"]),fee_exponent_b=float(_T["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
     if _S.get("filled"):
      _t=f"CAL1_{_U['market_id']}_{_T['market_id']}";opps_out.append({"sleeve":"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","market":_8["label"],"ask_vwap":_S["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_S["box_cost_net"]),4),"l1_usd":_S["l1_usd"],"close_ts":_8["close_ts"]})
      if(self.is_sleeve_grad8_ready("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX")and _U.get("market_id")!=_T.get("market_id")and.0<(float(_8["close_ts"])-now)<=604800. and(float(_8.get("early_leg_close_ts")or _8["close_ts"])-now)>=60.):self.emit_live_two_leg_box_candidate(sleeve_source="CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",box_type="MACRO_DOMINANCE",asset="MACRO",dedupe_key=_t,leg_a=_U,leg_b=_T,bk_a=_v,bk_b=_u,close_ts=float(_8["close_ts"]),now_ts=now,k_low=float(_U.get("strike")or 1e2),k_high=float(_T.get("strike")or 101.))
      await self.open_shadow_two_leg_box("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",_t,f"CAL1_{_a.ladder_kind}",_8["label"],_U,_T,_v,_u,float(_8["close_ts"]),.992,{"is_two_leg_box":True,"mode":_8["mode"],"ladder_kind":_a.ladder_kind})
  for nfl_b in list(self.lp1_nfl_em_bundles.values())[:12]:
   if float(nfl_b["end_ts"])<=now+60:continue
   D=sorted({str(lg["token_id"])for lg in nfl_b["legs"]});nfl_bks=await self.fetch_books_batch(D,timeout=3.5);C={t:p for t,bk in nfl_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.};m=find_state_matrix_dominance_boxes(nfl_b["legs"],C,max_2leg_cost_net=1.045,max_3leg_cost_net=.99)
   if m:_7=m[0];self._record_market_telemetry(f"LP1_NFL_EM_{nfl_b['event_id']}",90.,{"type":"LP1_NFL_EM_BOX_BEST","game":nfl_b["title"][:60],"n_legs":_7["n_legs"],"label":_7["label"],"net_box_l1":_7["box_cost_net"]},now_ts=now,sig=(_7["label"],_7["box_cost_net"]))
   for _6 in m[:6]:
    if float(_6["box_cost_net"])>.99 or int(_6["n_legs"])!=2:continue
    _s,_r=_6["legs"][0],_6["legs"][1];Z,Y=nfl_bks.get(_s["token_id"]),nfl_bks.get(_r["token_id"])
    if not Z or not Y:continue
    _R=walk_equal_shares_dominance_box(Z.get("asks")or[],Y.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX"],float(_s["fee_rate"]),float(_r["fee_rate"]),fee_exponent_a=float(_s["fee_exponent"]),fee_exponent_b=float(_r["fee_exponent"]),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
    if _R.get("filled"):
     _q=f"LP1_NFLEM_{nfl_b['event_id']}_{_s['token_id'][-8:]}_{_r['token_id'][-8:]}";opps_out.append({"sleeve":"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","market":f"NFL EM [{nfl_b['title']}]: {_6['label']}","ask_vwap":_R["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_R["box_cost_net"]),4),"l1_usd":_R["l1_usd"],"close_ts":_6["close_ts"]})
     if(self.is_sleeve_grad8_ready("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX")and float(_6.get("min_payout",1.))>=1.-1e-6 and float(_R["box_cost_net"])<=.988 and _s.get("market_id")!=_r.get("market_id")and.0<(float(_6["close_ts"])-now)<=604800.):self.emit_live_two_leg_box_candidate(sleeve_source="LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",box_type="SPORTS_CORRIDOR",asset="NFL",dedupe_key=_q,leg_a=_s,leg_b=_r,bk_a=Z,bk_b=Y,close_ts=float(_6["close_ts"]),now_ts=now,k_low=1e2,k_high=101. if float(_6.get("max_payout",1.))>1.05 else 1e2)
     await self.open_shadow_two_leg_box("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",_q,"NFL_EM",f"{nfl_b['title']} [{_6['label']}]",_s,_r,Z,Y,float(_6["close_ts"]),.99,{"is_two_leg_box":True,"mode":"NFL_EXACT_MARGIN_DOMINANCE","max_payout":_6["max_payout"]})
  k=list(self.multisport_raw_events.values())[:24]
  if k:
   j=[]
   for _,h in k:
    for _Q in h.get("markets")or[]:
     if not _Q.get("closed")and str(_Q.get("sportsMarketType")or"").lower()in("moneyline","spreads","first_half_moneyline","first_half_spreads","q1_moneyline","q1_spreads"):
      _p=_parse_clob_tokens(_Q)
      if _p:j.extend(_p)
   if j:
    ms_pm_bks=await self.fetch_books_batch(sorted(set(j)),timeout=3.5);i={t:p for t,bk in ms_pm_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for B,h in k:
     A=detect_multisport_ml_spread_polish_middles(h,i,sport_hint=B,max_box_cost_net=1.04)
     for _5 in A[:4]:
      if float(_5["box_cost_net"])>.988:continue
      _P,_O=_5["leg_a"],_5["leg_b"];_o,_n=ms_pm_bks.get(_P["token_id"]),ms_pm_bks.get(_O["token_id"])
      if not _o or not _n:continue
      _N=walk_equal_shares_dominance_box(_o.get("asks")or[],_n.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX"],float(_P["fee_rate"]),float(_O["fee_rate"]),fee_exponent_a=float(_P["fee_exponent"]),fee_exponent_b=float(_O["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
      if _N.get("filled"):
       _m=f"LP1_MSPM_{_P['market_id']}_{_O['market_id']}";opps_out.append({"sleeve":"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","market":_5["label"],"ask_vwap":_N["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_N["box_cost_net"]),4),"l1_usd":_N["l1_usd"],"close_ts":_5["close_ts"]})
       if(self.is_sleeve_grad8_ready("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX")and _P.get("market_id")!=_O.get("market_id")and.0<(float(_5["close_ts"])-now)<=604800.):self.emit_live_two_leg_box_candidate(sleeve_source="LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",box_type="SPORTS_CORRIDOR",asset=str(B).upper(),dedupe_key=_m,leg_a=_P,leg_b=_O,bk_a=_o,bk_b=_n,close_ts=float(_5["close_ts"]),now_ts=now,k_low=1e2,k_high=101.)
       await self.open_shadow_two_leg_box("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",_m,f"{B}_MIDDLE",_5["label"],_P,_O,_o,_n,float(_5["close_ts"]),.988,{"is_two_leg_box":True,"mode":_5["mode"]})
  g=[t for t in self.tennis_specs.values()if t.end_ts>now+60]
  if g:
   z=[]
   for w in g[:25]:
    for _l in w.totals_by_scope.values():
     for _4 in _l:z.extend([_4.over_token,_4.under_token])
    for X in(w.set1_a_token,w.set1_b_token,w.set2_a_token,w.set2_b_token,w.sets_ou25_over_token,w.sets_ou25_under_token,w.comp_yes_token,w.comp_no_token):
     if X:z.append(X)
   if z:
    ten_bks=await self.fetch_books_batch(sorted(set(z)),timeout=3.5);y={t:p for t,bk in ten_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for w in g[:25]:
     N=evaluate_ten1_tennis_opportunities(w,ten_bks,y,max_box_cost_net=1.045)
     if N:_M=N[0];self._record_market_telemetry(f"TEN1_{w.event_id}",90.,{"type":"TEN1_CORRIDOR_BEST","match":w.title[:60],"mode":_M["mode"],"label":_M["label"],"net_box_l1":_M["box_cost_net"]},now_ts=now,sig=(_M["label"],_M["box_cost_net"]))
     for _3 in N[:4]:
      if float(_3["box_cost_net"])>.988:continue
      _k,_j=_3["leg_a"],_3["leg_b"];W,V=ten_bks.get(_k["token_id"]),ten_bks.get(_j["token_id"])
      if not W or not V:continue
      _L=walk_equal_shares_dominance_box(W.get("asks")or[],V.get("asks")or[],BANKROLL_TICKETS["T1000"]["TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR"],float(_k["fee_rate"]),float(_j["fee_rate"]),fee_exponent_a=float(_k["fee_exponent"]),fee_exponent_b=float(_j["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
      if _L.get("filled"):
       _i=f"TEN1_{_k['market_id']}_{_j['market_id']}";opps_out.append({"sleeve":"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR","market":_3["label"],"ask_vwap":_L["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_L["box_cost_net"]),4),"l1_usd":_L["l1_usd"],"close_ts":_3["close_ts"]})
       if(self.is_sleeve_grad8_ready("TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR")and _k.get("market_id")!=_j.get("market_id")and.0<(float(_3["close_ts"])-now)<=259200.):self.emit_live_two_leg_box_candidate(sleeve_source="TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",box_type="SPORTS_CORRIDOR",asset="TENNIS",dedupe_key=_i,leg_a=_k,leg_b=_j,bk_a=W,bk_b=V,close_ts=float(_3["close_ts"]),now_ts=now,k_low=float(_k.get("strike")or 1e2),k_high=float(_j.get("strike")or 101.))
       await self.open_shadow_two_leg_box("TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",_i,"TENNIS_BO3",_3["label"],_k,_j,W,V,float(_3["close_ts"]),.988,{"is_two_leg_box":True,"mode":_3["mode"]})
  sports_to_poll=[]
  if any((tr.end_ts-3.5*3600.)<=now<=(tr.end_ts+2.*3600.)for tr in self.soccer_trees.values()):sports_to_poll.append("SOCCER")
  for sp_k in("NHL","NFL","CFB"):
   if any(ms.sport==sp_k and(ms.start_ts-9e2)<=now<=(ms.start_ts+6.*3600.)for ms in self.multi_sport_games.values()):sports_to_poll.append(sp_k)
  f={};fetch_sp_list=[sp_k for sp_k in sports_to_poll if sp_k not in self.live_multisport_boards or(now-self.live_multisport_boards[sp_k][0])>=20.]
  if fetch_sp_list:
   e=await asyncio.gather(*(asyncio.to_thread(fetch_espn_multisport_board_sync,sp_k)for sp_k in fetch_sp_list))
   for sp_k,U in zip(fetch_sp_list,e):self.live_multisport_boards[sp_k]=(now,U)
  for sp_k in sports_to_poll:
   if sp_k in self.live_multisport_boards:f[sp_k]=self.live_multisport_boards[sp_k][1]
  cl1_cands=[]
  if"SOCCER"in f and f["SOCCER"]:
   for tr in self.soccer_trees.values():
    for _K in evaluate_cl1_soccer_tree_clinch_locks(tr,f["SOCCER"],self.score_confirm_tracker,now):
     _h=f"CL1_SOC_{_K['market_id']}"
     if _h not in self.entered_keys and _h not in self.inflight_keys:cl1_cands.append({**_K,"dedupe_key":_h})
  for _g in self.multi_sport_games.values():
   if _g.sport in f and f[_g.sport]:
    for _J in evaluate_cl1_multisport_corridor_clinch_locks(_g,f,self.score_confirm_tracker,now):
     T=f"CL1_{_g.sport}_{_J['market_id']}"
     if T not in self.entered_keys and T not in self.inflight_keys:cl1_cands.append({**_J,"dedupe_key":T})
  if cl1_cands:
   M=await self.fetch_books_batch(sorted({t for c in cl1_cands for t in(c["token_id"],c["opp_token_id"])}),timeout=3.)
   for _I in cl1_cands:
    L,K=M.get(_I["token_id"]),M.get(_I["opp_token_id"])
    if not L or not K:continue
    v,_=extract_best_bid(K.get("bids")or[])
    if v>.04:continue
    _f=float(_I.get("fee_rate")or.0);_e=float(_I.get("fee_exponent")or 1.);_H=walk_l2_book_asks_depth_capped(L.get("asks")or[],BANKROLL_TICKETS["T1000"]["CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"],BANKROLL_TICKETS["T100"]["CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"],fee_rate=_f,min_l1_usd=15.,max_ask_px=.9821,fee_exponent=_e)
    if _H.get("filled"):
     S=float(_H["eff_px"]);_G=float(_I["p_lock"]);R=round(_G-S,4)
     if.72<=S<=.982 and R>=.015:
      u=max(now+6e2,float(_I["close_ts"]));opps_out.append({"sleeve":"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","market":f"[{_I['mode']}] {_I['display_label']}","ask_vwap":S,"p_model":_G,"net_edge":R,"l1_usd":_H["l1_usd"],"close_ts":u})
      if self.is_sleeve_grad8_ready("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"):self.emit_live_single_leg_lock_candidate(sleeve_source="CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",asset=str(_I["sport"]).upper(),dedupe_key=str(_I["dedupe_key"]),token_id=str(_I["token_id"]),opp_token_id=str(_I["opp_token_id"]),market_id=str(_I["market_id"]),condition_id=str(_I["condition_id"]),side_label=str(_I["side_label"]),display_label=str(_I["display_label"]),bk_win=L,bk_opp=K,fee_rate=_f,fee_exponent=_e,neg_risk=bool(_I.get("neg_risk",False)),close_ts=u,now_ts=now,max_lock_eff_px=.982,max_opp_bid=.025,hold_to_maturity=True,p_model=_G)
      await self.open_shadow_position("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",_I["dedupe_key"],_I["sport"],_I["display_label"],str(_I["side_label"]),str(_I["token_id"]),_f,_G,u,{"market_id":_I["market_id"],"condition_id":_I["condition_id"],"opp_token_id":_I["opp_token_id"],"mode":_I["mode"],"fee_exponent":_e},prefetched_book=L)
 async def _scan_frontier_v4_sleeves(self,opps_out,now):
  v4_lock_cands=[];self.subperiod_freeze_tracker.prune(now);self.score_confirm_tracker.prune(now);v4_sports_needed=[]
  if any((lat.end_ts-3.5*3600.)<=now<=(lat.end_ts+2.5*3600.)for lat in self.soc2_lattices.values()):v4_sports_needed.append("SOCCER")
  if any((b.sport=="NFL"and(b.start_ts-9e2)<=now<=(b.start_ts+6.*3600.))for b in self.aff1_bundles.values())or any((sl.kickoff_ts-9e2)<=now<=(sl.kickoff_ts+6.*3600.)for sl in self.nfl_prop_slates.values()):v4_sports_needed.append("NFL")
  if any((b.sport=="CFB"and(b.start_ts-9e2)<=now<=(b.start_ts+6.*3600.))for b in self.aff1_bundles.values()):v4_sports_needed.append("CFB")
  stale_v4_sp=[sp_k for sp_k in v4_sports_needed if sp_k not in self.live_multisport_boards or(now-self.live_multisport_boards[sp_k][0])>=20.]
  if stale_v4_sp:
   v=await asyncio.gather(*(asyncio.to_thread(fetch_espn_multisport_board_sync,sp_k)for sp_k in stale_v4_sp))
   for sp_k,_E in zip(stale_v4_sp,v):self.live_multisport_boards[sp_k]=(now,_E)
  active_aff=[b for b in self.aff1_bundles.values()if b.settle_est_ts>now+120.]
  if active_aff:
   H={t for b in active_aff for t in([tk for m in b.markets for tk in(m.tok_0,m.tok_1)]+([str(b.overtime_yes_leg["token_id"])]if b.overtime_yes_leg else[])+[tk for fp in b.first_passage_markets for tk in(fp.away_token,fp.home_token)])if t};aff_bks=await self.fetch_books_batch(sorted(H),timeout=3.5)if H else{};G={t:p for t,bk in aff_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for b in active_aff:
    for _X in detect_sum1_frechet_triangles(b,G,max_3leg_cost_net=.99):
     t_lgs=_X["legs"]
     if not all(x["token_id"]in aff_bks for x in t_lgs):continue
     _f=f"SUM1_{b.event_id}_{'_'.join(str(x['token_id'])[-6:]for x in t_lgs)}";_D=walk_equal_shares_multi_leg_box([{"asks":aff_bks[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x["fee_exponent"])}for x in t_lgs],BANKROLL_TICKETS["T1000"]["SUM1_FRECHET_SUM_TRIANGLES"],1.,.99,min_shares=6,min_box_notional_usd=5.5)
     if _D.get("filled"):opps_out.append({"sleeve":"SUM1_FRECHET_SUM_TRIANGLES","market":_X["label"],"ask_vwap":_D["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_D["box_cost_net"]),4),"l1_usd":_D["l1_usd"],"close_ts":_X["close_ts"]});await self.open_shadow_multi_leg_bundle("SUM1_FRECHET_SUM_TRIANGLES",_f,b.sport,_X["label"],t_lgs,aff_bks,float(_X["close_ts"]),1.,.99,{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"mode":_X["mode"]})
    a=None;f=""
    if b.sport=="NBA"and self.live_nba_board:
     u=self.nba_games.get(b.event_id);l=match_nba_live_game(u,self.live_nba_board)if u is not None else None
     if l is not None and l[0].state in("in","post"):
      f=str(l[0].game_id or"")
      if f:
       _C=self.nba_ext_summary_cache.get(f)
       if _C is not None and(now-_C[0])<15.:a=_C[1]
       else:
        try:_e,_B=await asyncio.to_thread(fetch_espn_nba_full_summary_sync,f);self.nba_boxscore_cache[f]=(now,_e);self.nba_ext_summary_cache[f]=(now,_B);a=_B
        except Exception:a=None
    elif b.sport in("NFL","CFB")and b.sport in self.live_multisport_boards:
     for _N in self.live_multisport_boards[b.sport][1]:
      if _N.start_ts>0 and b.start_ts>0 and abs(_N.start_ts-b.start_ts)>10.*3600.:continue
      _d=_teams_match_fuzzy(b.away_team,_N.away_name)and _teams_match_fuzzy(b.home_team,_N.home_name);_c=_teams_match_fuzzy(b.away_team,_N.home_name)and _teams_match_fuzzy(b.home_team,_N.away_name)
      if _d and _c:continue
      if _d or _c:f=_N.game_id;_A=dict(_N.linescores_home if _c else _N.linescores_away);_z=dict(_N.linescores_away if _c else _N.linescores_home);a={"state":_N.state,"completed":_N.completed,"is_halftime":_N.is_halftime,"period":_N.period,"clock_sec":_N.clock_sec,"away_score":_N.home_score if _c else _N.away_score,"home_score":_N.away_score if _c else _N.home_score,"linescores":{"away":_A,"home":_z}};break
    if a:
     L=evaluate_aff1_frozen_subperiod_opportunities(b,a,G,self.subperiod_freeze_tracker,now,espn_game_id=f,max_2leg_cost_net=.992,max_3leg_cost_net=.99)
     for _W in L["two_leg_boxes"]:
      _y,_x=_W["leg_a"],_W["leg_b"];_b,_a=aff_bks.get(_y["token_id"]),aff_bks.get(_x["token_id"])
      if not _b or not _a:continue
      Z=f"AFF1_2L_{b.event_id}_{_y['token_id'][-8:]}_{_x['token_id'][-8:]}";_w=walk_equal_shares_dominance_box(_b.get("asks")or[],_a.get("asks")or[],BANKROLL_TICKETS["T1000"]["AFF1_FROZEN_SUBPERIOD_COLLAPSE"],float(_y["fee_rate"]),float(_x["fee_rate"]),fee_exponent_a=float(_y["fee_exponent"]),fee_exponent_b=float(_x["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
      if _w.get("filled"):
       opps_out.append({"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","market":_W["label"],"ask_vwap":_w["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_w["box_cost_net"]),4),"l1_usd":_w["l1_usd"],"close_ts":_W["close_ts"]})
       if(self.is_sleeve_grad8_ready("AFF1_FROZEN_SUBPERIOD_COLLAPSE")and float(_w["box_cost_net"])<=.988 and.0<(float(_W["close_ts"])-now)<=86400.):self.emit_live_two_leg_box_candidate(sleeve_source="AFF1_FROZEN_SUBPERIOD_COLLAPSE",box_type="SPORTS_CORRIDOR",asset=b.sport,dedupe_key=Z,leg_a=_y,leg_b=_x,bk_a=_b,bk_b=_a,close_ts=float(_W["close_ts"]),now_ts=now,k_low=float(_y.get("strike")or 1e2),k_high=float(_x.get("strike")or 101.))
       await self.open_shadow_two_leg_box("AFF1_FROZEN_SUBPERIOD_COLLAPSE",Z,b.sport,_W["label"],_y,_x,_b,_a,float(_W["close_ts"]),.992,{"is_two_leg_box":True,"mode":_W["mode"],"middle_width":_W["middle_width"]})
     for _V in L["three_leg_boxes"]:
      lgs3=_V["legs"]
      if not all(x["token_id"]in aff_bks for x in lgs3):continue
      Y=f"AFF1_3L_{b.event_id}_{'_'.join(str(x['token_id'])[-6:]for x in lgs3)}";_v=walk_equal_shares_multi_leg_box([{"asks":aff_bks[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x["fee_exponent"])}for x in lgs3],BANKROLL_TICKETS["T1000"]["AFF1_FROZEN_SUBPERIOD_COLLAPSE"],1.,.99,min_shares=6,min_box_notional_usd=5.5)
      if _v.get("filled"):opps_out.append({"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","market":_V["label"],"ask_vwap":_v["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_v["box_cost_net"]),4),"l1_usd":_v["l1_usd"],"close_ts":_V["close_ts"]});await self.open_shadow_multi_leg_bundle("AFF1_FROZEN_SUBPERIOD_COLLAPSE",Y,b.sport,_V["label"],lgs3,aff_bks,float(_V["close_ts"]),1.,.99,{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"mode":_V["mode"]})
     for _U in L["single_leg_locks"]:X=f"AFF1_LK_{b.event_id}_{_U['market_id']}";v4_lock_cands.append({**_U,"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","asset":b.sport,"dedupe_key":X,"max_eff_px":.988})
  A=self.live_multisport_boards["SOCCER"][1]if"SOCCER"in self.live_multisport_boards else[]
  if A:
   for lat in self.soc2_lattices.values():
    if(lat.end_ts+7200.)<=now:continue
    for _T in evaluate_soc2_dead_score_no_locks(lat,A,self.score_confirm_tracker,now):W=f"SOC2_NO_{_T['market_id']}";v4_lock_cands.append({**_T,"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","asset":"SOCCER","dedupe_key":W,"max_eff_px":.986})
  pre_soc2=[lat for lat in self.soc2_lattices.values()if lat.end_ts>now+120.][:10]
  if pre_soc2:
   z=sorted({str(lg["token_id"])for lat in pre_soc2 for lg in lat.matrix_legs if lg.get("token_id")}|{str(t_cv)for lat in pre_soc2 if lat.convert_spec is not None for b_cv in lat.convert_spec.brackets for t_cv in(b_cv.get("no_token"),b_cv.get("yes_token"))if t_cv});soc2_bks=await self.fetch_books_batch(z,timeout=3.5)if z else{};y={t:p for t,bk in soc2_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for lat in pre_soc2:
    V=detect_soc2_lattice_boxes_and_converts(lat,soc2_bks,y,max_2leg_cost_net=.99,max_3leg_cost_net=.988,target_budget_usd=BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"])
    for _S in V["matrix_boxes"]:
     lgs_s=_S["legs"]
     if int(_S["n_legs"])==2:
      _M,_L=lgs_s[0],lgs_s[1];_u,_t=soc2_bks.get(_M["token_id"]),soc2_bks.get(_L["token_id"])
      if not _u or not _t:continue
      _s=f"SOC2_2L_{lat.exact_event_id}_{_M['token_id'][-8:]}_{_L['token_id'][-8:]}";_K=walk_equal_shares_dominance_box(_u.get("asks")or[],_t.get("asks")or[],BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"],float(_M["fee_rate"]),float(_L["fee_rate"]),fee_exponent_a=float(_M.get("fee_exponent",1.)),fee_exponent_b=float(_L.get("fee_exponent",1.)),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
      if _K.get("filled"):
       opps_out.append({"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","market":f"{lat.title}: {_S['label']}","ask_vwap":_K["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_K["box_cost_net"]),4),"l1_usd":_K["l1_usd"],"close_ts":_S["close_ts"]})
       if(self.is_sleeve_grad8_ready("SOC2_EXACT_SCORE_2D_LATTICE")and _M.get("market_id")!=_L.get("market_id")and float(_K["box_cost_net"])<=.988 and.0<(float(_S["close_ts"])-now)<=172800.):self.emit_live_two_leg_box_candidate(sleeve_source="SOC2_EXACT_SCORE_2D_LATTICE",box_type="SPORTS_CORRIDOR",asset="SOCCER",dedupe_key=_s,leg_a=_M,leg_b=_L,bk_a=_u,bk_b=_t,close_ts=float(_S["close_ts"]),now_ts=now,k_low=float(_M.get("strike")or 1e2),k_high=float(_L.get("strike")or 101.))
       await self.open_shadow_two_leg_box("SOC2_EXACT_SCORE_2D_LATTICE",_s,"SOCCER",f"{lat.title}: {_S['label']}",_M,_L,_u,_t,float(_S["close_ts"]),.99,{"is_two_leg_box":True,"mode":_S["mode"]})
     elif int(_S["n_legs"])==3 and all(x["token_id"]in soc2_bks for x in lgs_s):
      _r=f"SOC2_3L_{lat.exact_event_id}_{'_'.join(str(x['token_id'])[-6:]for x in lgs_s)}";_J=walk_equal_shares_multi_leg_box([{"asks":soc2_bks[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x.get("fee_exponent",1.))}for x in lgs_s],BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"],1.,.988,min_shares=6,min_box_notional_usd=5.5)
      if _J.get("filled"):opps_out.append({"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","market":f"{lat.title} 3L: {_S['label']}","ask_vwap":_J["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_J["box_cost_net"]),4),"l1_usd":_J["l1_usd"],"close_ts":_S["close_ts"]});await self.open_shadow_multi_leg_bundle("SOC2_EXACT_SCORE_2D_LATTICE",_r,"SOCCER",f"{lat.title} 3L: {_S['label']}",lgs_s,soc2_bks,float(_S["close_ts"]),1.,.988,{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"mode":_S["mode"]})
    if lat.convert_spec is not None and V["convert_arbs"]:await self.execute_nr2_subset_convert_arb(lat.convert_spec,V["convert_arbs"][0],soc2_bks,opps_out)
  active_nfl_prp=[sl for sl in self.nfl_prop_slates.values()if sl.settle_est_ts>now+120.][:8]
  if active_nfl_prp:
   i=sorted({tk for sl in active_nfl_prp for rg in(list(sl.anytime_td_by_player.values())+list(sl.two_plus_td_by_player.values())+[r for r_list in sl.ladders_by_player_stat.values()for r in r_list])for tk in(rg.yes_over_token,rg.no_under_token)if tk});nfl_prp_bks=await self.fetch_books_batch(i,timeout=3.5)if i else{};h={t:p for t,bk in nfl_prp_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.};nfl_board=self.live_multisport_boards["NFL"][1]if"NFL"in self.live_multisport_boards else[]
   for sl in active_nfl_prp:
    for _R in detect_nfl_prp1_boxes(sl,h,max_box_cost_net=.99):
     _q,_p=_R["leg_a"],_R["leg_b"];U,T=nfl_prp_bks.get(_q["token_id"]),nfl_prp_bks.get(_p["token_id"])
     if not U or not T:continue
     _o=f"NFL_PRP1_2L_{sl.event_id}_{_q['token_id'][-8:]}_{_p['token_id'][-8:]}";_I=walk_equal_shares_dominance_box(U.get("asks")or[],T.get("asks")or[],BANKROLL_TICKETS["T1000"]["NFL_PRP1_MILESTONE_AND_MAX_LOCKS"],float(_q["fee_rate"]),float(_p["fee_rate"]),fee_exponent_a=float(_q["fee_exponent"]),fee_exponent_b=float(_p["fee_exponent"]),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
     if _I.get("filled"):
      opps_out.append({"sleeve":"NFL_PRP1_MILESTONE_AND_MAX_LOCKS","market":f"{sl.title} [{_R['label']}]","ask_vwap":_I["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_I["box_cost_net"]),4),"l1_usd":_I["l1_usd"],"close_ts":_R["close_ts"]})
      if(self.is_sleeve_grad8_ready("NFL_PRP1_MILESTONE_AND_MAX_LOCKS")and _q.get("market_id")!=_p.get("market_id")and float(_I["box_cost_net"])<=.988 and.0<(float(_R["close_ts"])-now)<=172800.):self.emit_live_two_leg_box_candidate(sleeve_source="NFL_PRP1_MILESTONE_AND_MAX_LOCKS",box_type="SPORTS_CORRIDOR",asset="NFL",dedupe_key=_o,leg_a=_q,leg_b=_p,bk_a=U,bk_b=T,close_ts=float(_R["close_ts"]),now_ts=now,k_low=float(_q.get("strike")or.5),k_high=float(_p.get("strike")or 1.5))
      await self.open_shadow_two_leg_box("NFL_PRP1_MILESTONE_AND_MAX_LOCKS",_o,"NFL",f"{sl.title} [{_R['label']}]",_q,_p,U,T,float(_R["close_ts"]),.99,{"is_two_leg_box":True,"mode":_R["mode"]})
    if nfl_board:
     k=next((g for g in nfl_board if(g.start_ts<=0 or abs(g.start_ts-sl.kickoff_ts)<=10.*3600.)and((_teams_match_fuzzy(sl.away_team,g.away_name)and _teams_match_fuzzy(sl.home_team,g.home_name))!=(_teams_match_fuzzy(sl.away_team,g.home_name)and _teams_match_fuzzy(sl.home_team,g.away_name)))),None)
     if k is not None and k.state in("in","post"):
      _H=self.nfl_summary_cache.get(k.game_id)
      if _H is not None and(now-_H[0])<15.:e=_H[1]
      else:
       try:e=await asyncio.to_thread(fetch_espn_nfl_summary_sync,k.game_id);self.nfl_summary_cache[k.game_id]=(now,e)
       except Exception:e={}
      if e:
       for _Q in evaluate_nfl_prp1_live_locks(sl,e,self.score_confirm_tracker,now):S=f"NFL_PRP1_LK_{sl.event_id}_{_Q['market_id']}";v4_lock_cands.append({**_Q,"sleeve":"NFL_PRP1_MILESTONE_AND_MAX_LOCKS","asset":"NFL","dedupe_key":S,"max_eff_px":.988})
  if self.barrier_rungs or self.binance_close_rungs:
   near_hits=[hr for hr in self.barrier_rungs.values()if hr.resolved_yes is None and hr.end_ts>now+120. and hr.asset!="HYPE"and(self.spots.get(hr.asset,.0)<=.0 or abs(math.log(max(1e-9,hr.strike)/self.spots[hr.asset]))<=.35)];near_closes=[cr for cr in self.binance_close_rungs if cr.close_ts>now+120. and cr.asset!="HYPE"and(self.spots.get(cr.asset,.0)<=.0 or abs(math.log(max(1e-9,cr.strike)/self.spots[cr.asset]))<=.35)];F=sorted({t for hr in near_hits for t in(hr.yes_token,hr.no_token)}|{cr.no_token for cr in near_closes})
   if F:
    cry_bks=await self.fetch_books_batch(F,timeout=3.5);E={t:p for t,bk in cry_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for _P in detect_cry_inc1_binance_inclusion_boxes(near_hits,near_closes,E,now,max_box_cost_net=.992):
     _n,_m=_P["leg_a"],_P["leg_b"];R,Q=cry_bks.get(_n["token_id"]),cry_bks.get(_m["token_id"])
     if not R or not Q:continue
     _l=f"CRY_INC1_{_P['asset']}_{_n['market_id']}_{_m['market_id']}";_G=walk_equal_shares_dominance_box(R.get("asks")or[],Q.get("asks")or[],BANKROLL_TICKETS["T1000"]["CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION"],float(_n["fee_rate"]),float(_m["fee_rate"]),fee_exponent_a=float(_n["fee_exponent"]),fee_exponent_b=float(_m["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
     if _G.get("filled"):
      opps_out.append({"sleeve":"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION","market":_P["label"],"ask_vwap":_G["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_G["box_cost_net"]),4),"l1_usd":_G["l1_usd"],"close_ts":_P["close_ts"]})
      if(self.is_sleeve_grad8_ready("CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION")and float(_G["box_cost_net"])<=.988 and.0<(float(_P["close_ts"])-now)<=604800.):self.emit_live_two_leg_box_candidate(sleeve_source="CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",box_type="BARRIER_MONO",asset=str(_P["asset"]),dedupe_key=_l,leg_a=_n,leg_b=_m,bk_a=R,bk_b=Q,close_ts=float(_P["close_ts"]),now_ts=now,k_low=min(float(_n["strike"]),float(_m["strike"])),k_high=max(float(_n["strike"]),float(_m["strike"])))
      await self.open_shadow_two_leg_box("CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",_l,str(_P["asset"]),_P["label"],_n,_m,R,Q,float(_P["close_ts"]),.992,{"is_two_leg_box":True,"mode":_P["mode"],"direction":_P["direction"]})
  pending_v4_lks=[c for c in v4_lock_cands if c["dedupe_key"]not in self.entered_keys and c["dedupe_key"]not in self.inflight_keys]
  if pending_v4_lks:
   w=await self.fetch_books_batch(sorted({t for c in pending_v4_lks for t in(str(c["token_id"]),str(c["opp_token_id"]))if t}),timeout=3.)
   for _O in pending_v4_lks:
    _k,_j=str(_O["token_id"]),str(_O["opp_token_id"]);K,J=w.get(_k),w.get(_j)
    if not K or not J:continue
    q,_=extract_best_bid(J.get("bids")or[])
    if q>.035:continue
    _i=str(_O["sleeve"]);_h=float(_O.get("fee_rate")or.0);_g=float(_O.get("fee_exponent")or 1.);o=float(_O.get("max_eff_px")or.988);I=float(_O["p_lock"]);D=max(now+6e2,float(_O["close_ts"]));_F=walk_l2_book_asks_depth_capped(K.get("asks")or[],BANKROLL_TICKETS["T1000"][_i],BANKROLL_TICKETS["T100"][_i],fee_rate=_h,min_l1_usd=15.,max_ask_px=o+1e-4,fee_exponent=_g);d=False
    if _F.get("filled"):
     P=float(_F["eff_px"]);O=round(I-P,4)
     if.72<=P<=o and O>=.012:
      opps_out.append({"sleeve":_i,"market":f"[{_O['mode']}] {_O['display_label']}","ask_vwap":P,"p_model":I,"net_edge":O,"l1_usd":_F["l1_usd"],"close_ts":D})
      if self.is_sleeve_grad8_ready(_i):self.emit_live_single_leg_lock_candidate(sleeve_source=_i,asset=str(_O["asset"]).upper(),dedupe_key=str(_O["dedupe_key"]),token_id=_k,opp_token_id=_j,market_id=str(_O["market_id"]),condition_id=str(_O["condition_id"]),side_label=str(_O["side_label"]),display_label=str(_O["display_label"]),bk_win=K,bk_opp=J,fee_rate=_h,fee_exponent=_g,neg_risk=bool(_O.get("neg_risk",False)),close_ts=D,now_ts=now,max_lock_eff_px=o,max_opp_bid=.025,hold_to_maturity=True,p_model=I)
      d=await self.open_shadow_position(_i,str(_O["dedupe_key"]),str(_O["asset"]),str(_O["display_label"]),str(_O["side_label"]),_k,_h,I,D,{"market_id":_O["market_id"],"condition_id":_O["condition_id"],"opp_token_id":_j,"mode":_O["mode"],"fee_exponent":_g},prefetched_book=K)
    if not d:
     N=f"MKR_LK1_{_O['market_id']}"
     if N not in self.entered_keys and N not in self.inflight_keys:
      C,n=extract_best_bid(K.get("bids")or[]);B,_=self._best_ask_sz(K);j=.15 if str(_O["asset"]).upper()in("BTC","ETH","SOL","XRP","DOGE","BNB","HYPE","XAU")else.2;M=evaluate_mkr_lock1_post_clinch_rebate_bid(token_id=_k,opp_token_id=_j,market_id=str(_O["market_id"]),condition_id=str(_O["condition_id"]),display_label=str(_O["display_label"]),source_sleeve=_i,p_lock=I,close_ts=D,now_ts=now,best_bid=C if C>.0 else None,best_ask=B if B<1. else None,opp_best_bid=q,fee_rate=_h,fee_exponent=_g,maker_rebate_share=j,neg_risk=bool(_O.get("neg_risk",False)))
      if M is not None:
       opps_out.append({"sleeve":"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER","market":M["display_label"],"ask_vwap":M["effective_net_cost_per_share"],"p_model":I,"net_edge":round(float(M["expected_net_edge_per_share"]),4),"l1_usd":max(25.,n),"close_ts":D})
       if self.is_sleeve_grad8_ready("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"):self.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",asset=str(_O["asset"]).upper(),dedupe_key=N,pair_dedupe_key=str(_O["dedupe_key"]),token_id=_k,opp_token_id=_j,market_id=str(_O["market_id"]),condition_id=str(_O["condition_id"]),side_label=str(_O["side_label"]),display_label=str(_O["display_label"]),bk_win=K,bk_opp=J,neg_risk=bool(_O.get("neg_risk",False)),close_ts=D,now_ts=now,min_resting_bid=.96,max_resting_bid=.991,min_maker_edge=.006,max_opp_bid=.03,hold_to_maturity=True,p_model=I,target_bid_px=float(M["post_only_bid"]),maker_rebate_ps=float(M["maker_rebate_per_share"]))
       await self.post_shadow_maker_entry(sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",dedupe_key=N,asset=str(_O["asset"]),title=str(M["display_label"]),side_label=str(_O["side_label"]),token_id=_k,p_model=I,close_ts=D,extra={"market_id":_O["market_id"],"condition_id":_O["condition_id"],"opp_token_id":_j,"source_sleeve":_i,"resting_bid_override":M["post_only_bid"],"maker_rebate_ps":M["maker_rebate_per_share"]},prefetched_book=K,ttl_override_sec=180.)
 async def _scan_phase2_macro_counting_gas(self,opps_out,now):
  active_cnt=[s for s in self.counting_slates.values()if s.window_end_ts>now+60]
  if active_cnt:
   handles=sorted({s.handle for s in active_cnt});L=await asyncio.gather(*(asyncio.to_thread(fetch_xtracker_user_stats_sync,h)for h in handles));i=dict(zip(handles,L));v=[t for s in active_cnt for b in s.brackets for t in(b.yes_token,b.no_token)];A=await self.fetch_books_batch(v,timeout=3.5);f={}
   for _t,_l in A.items():
    _k,_j=self._best_ask_sz(_l)
    if _k<1. and _k*_j>=8.:f[_t]=_k
   for _i in active_cnt:
    z,u=evaluate_counting_dead_no_locks(_i,i.get(_i.handle)or{});self._record_market_telemetry(key=f"TW1_SNAP_{_i.event_id}",min_interval_sec=120.,now_ts=now,sig=(z,len(u)),payload={"type":"COUNTING_TRACKER_SNAP","slug":_i.slug,"handle":_i.handle,"verified_floor":z,"dead_open_brackets":len(u),"tte_sec":round(_i.window_end_ts-now,0)})
    for _s in u:
     K=A.get(_s.no_token)
     if not K:continue
     J,_=extract_best_bid(K.get("bids")or[]);I,_=self._best_ask_sz(K);H=float(getattr(_s,"fee_rate",.0)or.0);G=float(getattr(_s,"fee_exponent",1.)or 1.);X=walk_l2_book_asks(K.get("asks")or[],BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"],fee_rate=H,min_l1_usd=15.,max_ask_px=.99,fee_exponent=G)
     if X.get("filled")and.8<=float(X["eff_px"])<=.99:
      F=round(1.-float(X["eff_px"]),4)
      if F>=.01:
       opps_out.append({"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","market":f"{_i.handle} Dead Bracket NO[{_s.label}] (count>={z})","ask_vwap":X["eff_px"],"p_model":1.,"net_edge":F,"l1_usd":X["l1_usd"],"close_ts":_i.window_end_ts})
       if(_i.window_end_ts-now)<=172800.:self.emit_live_single_leg_lock_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",asset=_i.handle.upper(),dedupe_key=f"TW1_NO_{_s.market_id}",token_id=_s.no_token,opp_token_id=_s.yes_token,market_id=_s.market_id,condition_id=_s.condition_id,side_label="NO",display_label=f"{_i.handle} Dead NO[{_s.label}]",bk_win=K,bk_opp=A.get(_s.yes_token),fee_rate=H,fee_exponent=G,neg_risk=bool(_s.neg_risk),close_ts=float(_i.window_end_ts),now_ts=now,max_lock_eff_px=.99,max_opp_bid=.02,hold_to_maturity=(float(X["eff_px"])>=.98),p_model=1.)
       await self.open_shadow_position("TW1_COUNTING_TRUNCATION_AND_BOX",f"TW1_NO_{_s.market_id}",_i.handle.upper(),f"{_i.title} [Dead NO {_s.label}]","NO",_s.no_token,H,1.,_i.window_end_ts,{"market_id":_s.market_id,"condition_id":_s.condition_id,"verified_floor":z,"fee_exponent":G},prefetched_book=K)
     W=evaluate_locked_market_reward_carry(1.,J,I,_s.rewards_min_size,_s.rewards_max_spread,H)
     if W.get("eligible"):opps_out.append({"sleeve":"MKR_REWARD_LOCKED_CARRY","market":f"{_i.handle} Locked Carry NO[{_s.label}] @ ${W['resting_bid']:.3f}","ask_vwap":W["resting_bid"],"p_model":1.,"net_edge":W["carry_edge"],"l1_usd":50.,"close_ts":_i.window_end_ts});await self.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY",f"MKR_RW_{_s.market_id}",_i.handle.upper(),f"{_i.title} [Reward Carry NO {_s.label}]","NO",_s.no_token,1.,_i.window_end_ts,{"market_id":_s.market_id,"condition_id":_s.condition_id,"resting_bid_override":W["resting_bid"]},prefetched_book=K)
   r=detect_counting_subwindow_boxes(active_cnt,f,i,max_box_cost_net=1.05)
   if r:_r=r[0];self._record_market_telemetry(f"TW1_BOX_{_r['handle']}",90.,{"type":"COUNTING_SUBWINDOW_BEST","handle":_r["handle"],"net_box_l1":_r["box_cost_net"],"label":_r["label"]},now_ts=now,sig=(_r["label"],_r["box_cost_net"]))
   for tb in r:
    _h,_g=tb["leg_a"],tb["leg_b"];V,U=A.get(_h["token_id"]),A.get(_g["token_id"])
    if not V or not U:continue
    T=f"TW1_BOX_{_h['market_id']}_{_g['market_id']}"
    if float(tb["box_cost_net"])<=.993:
     _f=walk_equal_shares_dominance_box(V.get("asks")or[],U.get("asks")or[],BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"],float(_h.get("fee_rate",.0)),float(_g.get("fee_rate",.0)),fee_exponent_a=float(_h.get("fee_exponent",1.)),fee_exponent_b=float(_g.get("fee_exponent",1.)),max_box_cost_net=.993,min_shares=6,min_box_notional_usd=5.5)
     if _f.get("filled"):
      opps_out.append({"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","market":f"Counting Box {tb['label']}","ask_vwap":_f["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_f["box_cost_net"]),4),"l1_usd":_f["l1_usd"],"close_ts":tb["close_ts"]});c=False
      if(float(tb["close_ts"])-now)<=86400. and float(_f["box_cost_net"])<=.99:c=self.emit_live_two_leg_box_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",box_type="COUNTING_DOMINANCE",asset=tb["handle"].upper(),dedupe_key=T,leg_a=_h,leg_b=_g,bk_a=V,bk_b=U,close_ts=float(tb["close_ts"]),now_ts=now)
      await self.open_shadow_two_leg_box("TW1_COUNTING_TRUNCATION_AND_BOX",T,tb["handle"].upper(),f"Counting Box {tb['label']}",_h,_g,V,U,float(tb["close_ts"]),.993,{"is_two_leg_box":True,"banked":tb["banked"]})
      if not c:self.post_zero_fee_maker_anchor_box("TW1",tb["handle"].upper(),f"ZFA_{T}",_h,_g,V,U,float(tb["close_ts"]),f"Counting Box {tb['label']}",now,prefetched_books=A,live_emit_only=True)
     else:self.post_zero_fee_maker_anchor_box("TW1",tb["handle"].upper(),f"ZFA_{T}",_h,_g,V,U,float(tb["close_ts"]),f"Counting Box {tb['label']}",now,prefetched_books=A)
    elif float(tb["box_cost_net"])<=1.035:self.post_zero_fee_maker_anchor_box("TW1",tb["handle"].upper(),f"ZFA_{T}",_h,_g,V,U,float(tb["close_ts"]),f"Counting Box {tb['label']}",now,prefetched_books=A)
  lp_legs=[lg for lg in(self.fomc_truth_legs+self.oil_senate_truth_legs)if float(lg["end_ts"])>now+60]
  if lp_legs:
   lp_bks=await self.fetch_books_batch(sorted({str(lg["token_id"])for lg in lp_legs}),timeout=3.5);y={t:p for t,bk in lp_bks.items()for p,s in[self._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for S,q,o,n,E in(("FED1_CENTRAL_BANK_LP_BOX","FOMC",self.fomc_truth_legs,ALL_FOMC_MASK,"FOMC_LP_BEST"),("COND1_MACRO_PARTITION_BOX","OIL_SENATE",self.oil_senate_truth_legs,ALL_OIL_SENATE_MASK,"OIL_SENATE_PARTITION_BEST")):
    if not o:continue
    w=find_cross_event_bitmask_boxes(o,y,n,max_2leg_cost=1.05,max_3leg_cost=1.03)
    if w:b0=w[0];self._record_market_telemetry(f"{E}_DIAG",90.,{"type":E,"n_legs":b0["n_legs"],"net_box_l1":b0["box_cost_net"],"label":b0["label"]},now_ts=now,sig=(b0["label"],b0["box_cost_net"]))
    for bx in w:
     lgs=bx["legs"]
     if int(bx["n_legs"])==2:
      _e,_d=lgs[0],lgs[1];R,Q=lp_bks.get(_e["token_id"]),lp_bks.get(_d["token_id"])
      if not R or not Q:continue
      _c=f"{q}_2L_{_e['token_id'][-8:]}_{_d['token_id'][-8:]}"
      if float(bx["box_cost_net"])<=.994:
       _q=walk_equal_shares_dominance_box(R.get("asks")or[],Q.get("asks")or[],BANKROLL_TICKETS["T1000"][S],float(_e.get("fee_rate",.0)),float(_d.get("fee_rate",.0)),fee_exponent_a=float(_e.get("fee_exponent",1.)),fee_exponent_b=float(_d.get("fee_exponent",1.)),max_box_cost_net=.994,min_shares=6,min_box_notional_usd=5.5)
       if _q.get("filled"):
        opps_out.append({"sleeve":S,"market":f"{q} {bx['label']}","ask_vwap":_q["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_q["box_cost_net"]),4),"l1_usd":_q["l1_usd"],"close_ts":bx["close_ts"]});a=False
        if S=="FED1_CENTRAL_BANK_LP_BOX"and(float(bx["close_ts"])-now)<=172800. and float(_q["box_cost_net"])<=.99:a=self.emit_live_two_leg_box_candidate(sleeve_source=S,box_type="MACRO_DOMINANCE",asset=q,dedupe_key=_c,leg_a=_e,leg_b=_d,bk_a=R,bk_b=Q,close_ts=float(bx["close_ts"]),now_ts=now)
        elif S=="COND1_MACRO_PARTITION_BOX"and(float(bx["close_ts"])-now)<=86400. and float(_q["box_cost_net"])<=.985:a=self.emit_live_two_leg_box_candidate(sleeve_source=S,box_type="MACRO_DOMINANCE",asset=q,dedupe_key=_c,leg_a=_e,leg_b=_d,bk_a=R,bk_b=Q,close_ts=float(bx["close_ts"]),now_ts=now)
        await self.open_shadow_two_leg_box(S,_c,q,f"{q} {bx['label']}",_e,_d,R,Q,float(bx["close_ts"]),.994,{"is_two_leg_box":True,"double_pay_states":bx["double_pay_states"]})
        if not a:self.post_zero_fee_maker_anchor_box(q,q,f"ZFA_{_c}",_e,_d,R,Q,float(bx["close_ts"]),f"{q} {bx['label']}",now,prefetched_books=lp_bks,live_emit_only=True)
       else:self.post_zero_fee_maker_anchor_box(q,q,f"ZFA_{_c}",_e,_d,R,Q,float(bx["close_ts"]),f"{q} {bx['label']}",now,prefetched_books=lp_bks)
      elif float(bx["box_cost_net"])<=1.035:self.post_zero_fee_maker_anchor_box(q,q,f"ZFA_{_c}",_e,_d,R,Q,float(bx["close_ts"]),f"{q} {bx['label']}",now,prefetched_books=lp_bks)
     elif int(bx["n_legs"])==3 and float(bx["box_cost_net"])<=.992:
      _b=f"{q}_3L_{'_'.join(x['token_id'][-6:]for x in lgs)}";_p=walk_equal_shares_multi_leg_box([{"asks":lp_bks[x["token_id"]].get("asks")or[],"fee_rate":float(x.get("fee_rate",.0)),"fee_exponent":float(x.get("fee_exponent",1.))}for x in lgs],BANKROLL_TICKETS["T1000"][S],1.,.992,min_shares=6,min_box_notional_usd=5.5)
      if _p.get("filled"):opps_out.append({"sleeve":S,"market":f"{q} 3-Leg {bx['label']}","ask_vwap":_p["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_p["box_cost_net"]),4),"l1_usd":_p["l1_usd"],"close_ts":bx["close_ts"]});await self.open_shadow_multi_leg_bundle(S,_b,q,f"{q} 3-Leg {bx['label']}",lgs,lp_bks,float(bx["close_ts"]),1.,.992,{"is_multi_leg_bundle":True,"guaranteed_payout":1.})
  d=[e for e in(self.gas_events_raw.get("us-gas-price-daily")or[])if not e.get("closed")]
  if d:
   _o=await asyncio.to_thread(fetch_aaa_national_gas_sync)
   if _o:
    self._record_market_telemetry("AAA_GAS_SNAP",3e2,{"type":"AAA_GAS_SNAP",**_o},now_ts=now,sig=(_o["as_of_date"],_o["current_regular"]));D=float(_o["current_regular"])
    for _a in d:
     P=_parse_iso_ts(_a.get("endDate"))or.0
     if not(60.<(P-now)<=57600.):continue
     C=re.search(r"(20\d{2}-\d{2}-\d{2})",str(_a.get("slug")or""));B=C.group(1)if C else datetime.fromtimestamp(P,tz=NY_TZ).date().isoformat()
     if B!=_o["as_of_date"]:continue
     g_brs=[]
     for mg in(_a.get("markets")or[]):
      if mg.get("closed"):continue
      l,k=_extract_market_fee_rate(mg);m=_parse_clob_tokens(mg);Z=parse_gas_daily_bracket(str(mg.get("groupItemTitle")or mg.get("question")or""))
      if m and Z:g_brs.append((mg,m,Z,l,k))
     if not g_brs:continue
     O=await self.fetch_books_batch([t for _,tk,_,_,_ in g_brs for t in tk],timeout=3.)
     for mg,m,(_n,_m),l,k in g_brs:
      N=str(mg.get("id")or"");M=str(mg.get("groupItemTitle")or"")
      if(_n==.0 or D>=_n+.0015)and(not math.isfinite(_m)or D<=_m-.0015):g,j="YES",m[0]
      elif D<=_n-.002 or(math.isfinite(_m)and D>=_m+.002):g,j="NO",m[1]
      else:continue
      Y=O.get(j)
      if not Y:continue
      wg=walk_l2_book_asks(Y.get("asks")or[],BANKROLL_TICKETS["T1000"]["GAS1_AAA_GASOLINE_LOCK"],fee_rate=l,min_l1_usd=15.,max_ask_px=.985,fee_exponent=k)
      if wg.get("filled")and.75<=float(wg["eff_px"])<=.983:opps_out.append({"sleeve":"GAS1_AAA_GASOLINE_LOCK","market":f"AAA Gas ${D:.4f} ({_o['as_of_date']}) -> {g}[{M}]","ask_vwap":wg["eff_px"],"p_model":.998,"net_edge":round(.998-float(wg["eff_px"]),4),"l1_usd":wg["l1_usd"],"close_ts":P});await self.open_shadow_position("GAS1_AAA_GASOLINE_LOCK",f"GAS1_{N}_{g}","AAA_GAS",f"{_a.get('title')} [{g} {M}]",g,j,l,.998,P,{"market_id":N,"aaa_price":D,"as_of_date":_o["as_of_date"],"fee_exponent":k},prefetched_book=Y)
  await self.scan_uma_resolution_bonds(opps_out,now_ts=now)
 def has_live_nba_window(self,now_ts):return any((sp.tipoff_ts-6e2)<=now_ts<=(sp.tipoff_ts+5.5*3600.)for sp in self.nba_games.values())
 def has_live_sports_window(self,now_ts):return(self.has_live_nba_window(now_ts)or any((sp.start_ts-6e2)<=now_ts<=(sp.start_ts+5.5*3600.)for sp in self.multi_sport_games.values())or any((tr.end_ts-2.5*3600.)<=now_ts<=(tr.end_ts+1.5*3600.)for tr in self.soccer_trees.values())or any((tn.end_ts-3.5*3600.)<=now_ts<=(tn.end_ts+1.*3600.)for tn in self.tennis_specs.values())or any((b.start_ts-6e2)<=now_ts<=(b.start_ts+5.5*3600.)for b in self.aff1_bundles.values())or any((lat.end_ts-2.5*3600.)<=now_ts<=(lat.end_ts+2.*3600.)for lat in self.soc2_lattices.values())or any((sl.kickoff_ts-6e2)<=now_ts<=(sl.kickoff_ts+5.5*3600.)for sl in self.nfl_prop_slates.values()))
 async def discover_uma_proposed_markets(self,now_ts):
  a=datetime.fromtimestamp(now_ts+12.*3600.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");d=await asyncio.gather(self.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=200&offset=0",timeout=5.5),self.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=200&offset=200",timeout=5.5),self.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&end_date_max={a}&order=volume24hr&ascending=false&limit=200&offset=0",timeout=5.5),self.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&end_date_max={a}&order=volume24hr&ascending=false&limit=200&offset=200",timeout=5.5));c={}
  for pg in d:
   if not isinstance(pg,list):continue
   for m in pg:
    if not isinstance(m,dict):continue
    e=str(m.get("id")or"").strip()
    if not e or e in c:continue
    b,_=is_objective_uma_market(m)
    if b:c[e]=m
  self.uma_proposed_markets=c;self.last_uma_discovery_ts=now_ts
 async def scan_uma_resolution_bonds(self,opps_out,now_ts=None):
  G=float(now_ts if now_ts is not None else time.time())
  if self.single_scan or not self.uma_proposed_markets or(G-self.last_uma_discovery_ts)>=90.:await self.discover_uma_proposed_markets(G)
  if not self.uma_proposed_markets:return
  verified_list=[]
  for u,m in list(self.uma_proposed_markets.items()):
   F=f"BOND1_{u}"
   if F in self.entered_keys or F in self.inflight_keys:continue
   n=self.uma_onchain_cache.get(u);g=45.
   if n is not None:
    rsn=str(n[1].get("reason")or"")
    if any(k in rsn for k in("DISPUTER","TIE_50_50","QUESTION_FLAGS","PRIOR_DISPUTE","PREMATURE_PROPOSAL","MARKET_BEFORE_END_DATE")):g=3e2
   if n is not None and(G-n[0])<g:ver=n[1]
   else:ver=await asyncio.to_thread(verify_uma_onchain_proposal_sync,m,None,G);self.uma_onchain_cache[u]=(G,ver)
   if not ver.get("verified"):continue
   v,_=verify_uma_against_nba_live(m,int(ver["win_index"]),self.live_nba_board)
   if not v:continue
   verified_list.append((u,m,ver))
  if not verified_list:return
  i=[t for _,_,ver in verified_list for t in(str(ver["win_token"]),str(ver["lose_token"]))];p=await self.fetch_books_batch(i,timeout=3.5);c=BANKROLL_TICKETS["T1000"]["BOND1_UMA_RESOLUTION_CARRY"]
  for u,m,ver in verified_list:
   E,D=str(ver["win_token"]),str(ver["lose_token"]);C,B=p.get(E),p.get(D)
   if not C or not B:continue
   o,_=extract_best_bid(C.get("bids")or[]);l,_=extract_best_bid(B.get("bids")or[]);j,_=self._best_ask_sz(B)
   if l>.008 or o<.94 or(j<.5 and j>.025):continue
   s=walk_l2_book_asks_depth_capped(C.get("asks")or[],c,BANKROLL_TICKETS["T100"]["BOND1_UMA_RESOLUTION_CARRY"],fee_rate=float(ver["fee_rate"]),min_l1_usd=15.,max_ask_px=.9956,fee_exponent=float(ver["fee_exponent"]));y=float(s["eff_px"])if s.get("filled")else None;self._record_market_telemetry(key=f"BOND1_SNAP_{u}",min_interval_sec=60.,now_ts=G,sig=(y,o,l,ver["oo_state"]),payload={"type":"UMA_BOND_PROPOSAL_SNAP","market_id":u,"question":str(m.get("question")or"")[:90],"domain":ver["domain"],"win_outcome":ver["win_outcome_name"],"oo_state":ver["oo_state"],"rem_challenge_sec":ver["rem_challenge_sec"],"win_ask_eff":y,"win_bid":o,"lose_bid":l});x=str(m.get("question")or f"Market {u}");h=max(G+120.,float(ver["expiration_ts"])+60.);f={"market_id":u,"condition_id":str(m.get("conditionId")or""),"opp_token_id":D,"fee_exponent":ver["fee_exponent"],"oo_state":ver["oo_state"],"proposer":ver["proposer"],"win_outcome_name":ver["win_outcome_name"],"expiration_ts":ver["expiration_ts"],"rem_challenge_sec":ver["rem_challenge_sec"],"domain":ver["domain"]};a=False;b=bool(s.get("filled")and y is not None and(.95<=y<=.9955)and round(1.-y,4)>=.0045)
   if b:e=round(1.-y,4);opps_out.append({"sleeve":"BOND1_UMA_RESOLUTION_CARRY","market":f"[{ver['domain']}] {x[:65]} -> {ver['win_outcome_name']} ({ver['rem_challenge_sec']/60:.0f}m rem)","ask_vwap":y,"p_model":1.,"net_edge":e,"l1_usd":s["l1_usd"],"close_ts":h});self.emit_live_single_leg_lock_candidate(sleeve_source="BOND1_UMA_RESOLUTION_CARRY",asset=str(ver["domain"]),dedupe_key=f"BOND1_{u}",token_id=E,opp_token_id=D,market_id=u,condition_id=str(m.get("conditionId")or""),side_label=str(ver["win_label"]),display_label=f"{ver['domain']} {ver['win_outcome_name']}",bk_win=C,bk_opp=B,fee_rate=float(ver["fee_rate"]),fee_exponent=float(ver["fee_exponent"]),neg_risk=bool(m.get("negRisk")),close_ts=h,now_ts=G,max_lock_eff_px=.9955,max_opp_bid=.008,hold_to_maturity=True,p_model=1.);a=await self.open_shadow_position(sleeve="BOND1_UMA_RESOLUTION_CARRY",dedupe_key=f"BOND1_{u}",asset_or_city=str(ver["domain"]),title=f"{x} [{ver['win_outcome_name']}]",side_label=str(ver["win_label"]),token_id=E,fee_rate=float(ver["fee_rate"]),p_model=1.,close_ts=h,extra=f,tp_target_px=None,prefetched_book=C)
   if not b and not a and.94<=o<=.994 and l<=.008 and(h-G)>120.:
    self.emit_live_single_leg_maker_lock_candidate(sleeve_source="BOND1_UMA_RESOLUTION_CARRY",asset=str(ver["domain"]),dedupe_key=f"BOND1_MKR_{u}",pair_dedupe_key=f"BOND1_{u}",token_id=E,opp_token_id=D,market_id=u,condition_id=str(m.get("conditionId")or""),side_label=str(ver["win_label"]),display_label=f"{ver['domain']} {ver['win_outcome_name']}",bk_win=C,bk_opp=B,neg_risk=bool(m.get("negRisk")),close_ts=h,now_ts=G,min_resting_bid=.94,max_resting_bid=.994,min_maker_edge=.006,max_opp_bid=.008,hold_to_maturity=True,p_model=1.);d=await self.post_shadow_maker_entry(sleeve="BOND1_UMA_RESOLUTION_CARRY",dedupe_key=f"BOND1_{u}",asset=str(ver["domain"]),title=f"{x} [{ver['win_outcome_name']}]",side_label=str(ver["win_label"]),token_id=E,p_model=1.,close_ts=h,extra=f,prefetched_book=C)
    if d:opps_out.append({"sleeve":"BOND1_UMA_RESOLUTION_CARRY","market":f"[MAKER:{ver['domain']}] {x[:58]} -> {ver['win_outcome_name']}","ask_vwap":o,"p_model":1.,"net_edge":round(1.-o,4),"l1_usd":extract_best_bid(C.get("bids")or[])[1],"close_ts":h})
   w=f"BOND2_{u}"
   if(w not in self.entered_keys and w not in self.inflight_keys and float(ver.get("proposal_age_sec")or.0)>=3600. and 180.<=float(ver.get("rem_challenge_sec")or.0)<=3300. and l<=.006 and o>=.95):
    A=await asyncio.to_thread(verify_bond2_moov2_final_hour_sync,m,None,G)
    if A.get("verified"):
     z=walk_l2_book_asks_depth_capped(C.get("asks")or[],BANKROLL_TICKETS["T1000"]["BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"],BANKROLL_TICKETS["T100"]["BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"],fee_rate=float(A["fee_rate"]),min_l1_usd=15.,max_ask_px=.9963,fee_exponent=float(A["fee_exponent"]))
     if z.get("filled")and.95<=float(z["eff_px"])<=.9962:
      r=float(z["eff_px"]);q=round(1.-r,4)
      if q>=.0038:opps_out.append({"sleeve":"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","market":f"[MOOv2_WL:{A['domain']}] {x[:60]} -> {A['win_outcome_name']} ({A['rem_challenge_sec']/60:.0f}m rem)","ask_vwap":r,"p_model":1.,"net_edge":q,"l1_usd":z["l1_usd"],"close_ts":h});self.emit_live_single_leg_lock_candidate(sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",asset=str(A["domain"]),dedupe_key=w,token_id=E,opp_token_id=D,market_id=u,condition_id=str(m.get("conditionId")or""),side_label=str(A["win_label"]),display_label=f"MOOv2_WL {A['domain']} {A['win_outcome_name']}",bk_win=C,bk_opp=B,fee_rate=float(A["fee_rate"]),fee_exponent=float(A["fee_exponent"]),neg_risk=bool(m.get("negRisk")),close_ts=h,now_ts=G,max_lock_eff_px=.995,max_opp_bid=.006,hold_to_maturity=True,p_model=1.);await self.open_shadow_position(sleeve="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",dedupe_key=w,asset_or_city=str(A["domain"]),title=f"{x} [MOOv2 Whitelisted {A['win_outcome_name']}]",side_label=str(A["win_label"]),token_id=E,fee_rate=float(A["fee_rate"]),p_model=1.,close_ts=h,extra={**f,"proposer_whitelisted":True,"oo_address":A["oo_address"]},tp_target_px=None,prefetched_book=C)
 async def scan_nba_endgame_locks(self,opps_out,now_ts=None):
  C=float(now_ts if now_ts is not None else time.time())
  if not self.nba_games:return
  j=5.5 if self.has_live_nba_window(C)else 120.
  if self.single_scan or not self.live_nba_board or(C-self.last_espn_board_ts)>=j:
   y=await asyncio.to_thread(fetch_espn_nba_scoreboard_sync)
   if y:self.live_nba_board=y;self.last_espn_board_ts=C
  if not self.live_nba_board:return
  cand_rows=[]
  for c in list(self.nba_games.values()):
   q=match_nba_live_game(c,self.live_nba_board)
   if q is None:continue
   p,B,A=q
   if p.state in("in","post"):self._record_market_telemetry(key=f"NBA_LIVE_{c.event_id}",min_interval_sec=30.,now_ts=C,sig=(p.state,p.period,int(p.clock_sec//10),B,A),payload={"type":"NBA_LIVE_SCORE_SNAP","event_id":c.event_id,"game":c.title,"state":p.state,"completed":p.completed,"period":p.period,"clock_sec":round(p.clock_sec,1),"score_a":B,"score_b":A,"source":p.source})
   for c_lk in evaluate_nba_endgame_locks(c,p,B,A):
    lg=c_lk["leg"];w=f"SP2_{c.event_id}_{lg.market_id}_{lg.token_id[-8:]}"
    if w not in self.entered_keys and w not in self.inflight_keys:cand_rows.append((c,c_lk))
  if not cand_rows:await self._scan_sp4_live_nba_stat_locks(opps_out,C);return
  i=[t for _,c_lk in cand_rows for t in(c_lk["leg"].token_id,c_lk["leg"].opp_token_id)];o=await self.fetch_books_batch(i,timeout=3.);n=BANKROLL_TICKETS["T1000"]["SP2_NBA_ENDGAME_LOCK"]
  for c,c_lk in cand_rows:
   lg=c_lk["leg"];v=o.get(lg.token_id);u=o.get(lg.opp_token_id)
   if not v or not u:continue
   m,_=extract_best_bid(u.get("bids")or[])
   if m>.18:continue
   d,b=extract_best_bid(v.get("bids")or[]);s=float(getattr(lg,"fee_rate",.0)or.0);r=float(getattr(lg,"fee_exponent",1.)or 1.);x=walk_l2_book_asks_depth_capped(v.get("asks")or[],n,BANKROLL_TICKETS["T100"]["SP2_NBA_ENDGAME_LOCK"],fee_rate=s,min_l1_usd=18.,max_ask_px=.9861,fee_exponent=r);z=float(c_lk["p_lock"]);g=max(C+6e2,float(c.settle_est_ts));h=f"SP2_{c.event_id}_{lg.market_id}_{lg.token_id[-8:]}";f={"event_id":c.event_id,"market_id":lg.market_id,"condition_id":lg.condition_id,"opp_token_id":lg.opp_token_id,"mode":c_lk["mode"],"score_str":c_lk["score_str"],"cushion_pts":c_lk["cushion_pts"],"clock_sec":c_lk["clock_sec"],"period":c_lk["period"],"fee_exponent":r};a=False
   if x.get("filled"):
    l=float(x["eff_px"]);k=round(z-l,4)
    if m<=(1.-l)+.025 and(.78<=l<=.986)and k>=.012:opps_out.append({"sleeve":"SP2_NBA_ENDGAME_LOCK","market":f"NBA [{c_lk['mode']}] {c_lk['score_str']} -> {lg.display_label}","ask_vwap":l,"p_model":z,"net_edge":k,"l1_usd":x["l1_usd"],"close_ts":g});a=await self.open_shadow_position(sleeve="SP2_NBA_ENDGAME_LOCK",dedupe_key=h,asset_or_city="NBA",title=f"{c.title} [{lg.display_label} | {c_lk['mode']}]",side_label=lg.side_label,token_id=lg.token_id,fee_rate=s,p_model=z,close_ts=g,extra=f,tp_target_px=None,prefetched_book=v)
   if(not a and.72<=d<=.985 and m<=(1.-d)+.025 and(z-d)>=.012):
    e=await self.post_shadow_maker_entry(sleeve="SP2_NBA_ENDGAME_LOCK",dedupe_key=h,asset="NBA",title=f"{c.title} [{lg.display_label} | {c_lk['mode']}]",side_label=lg.side_label,token_id=lg.token_id,p_model=z,close_ts=g,extra=f,prefetched_book=v,ttl_override_sec=45.)
    if e:opps_out.append({"sleeve":"SP2_NBA_ENDGAME_LOCK","market":f"[MAKER] NBA [{c_lk['mode']}] {c_lk['score_str']} -> {lg.display_label}","ask_vwap":d,"p_model":z,"net_edge":round(z-d,4),"l1_usd":b,"close_ts":g})
  await self._scan_sp4_live_nba_stat_locks(opps_out,C)
 async def _scan_sp4_live_nba_stat_locks(self,opps_out,now):
  if(not self.nba_prop_slates and not self.nba_subperiod_slates)or not self.live_nba_board:return
  sp4_cands=[];sp4_sub_cands=[];d=sorted(set(self.nba_prop_slates.keys())|set(self.nba_subperiod_slates.keys()))
  for F in d:
   y=self.nba_games.get(F)
   if y is None:continue
   q=match_nba_live_game(y,self.live_nba_board)
   if q is None or q[0].state not in("in","post"):continue
   K=q[0];n=str(K.game_id or"")
   if not n:continue
   l=self.nba_boxscore_cache.get(n);h=self.nba_ext_summary_cache.get(n)
   if l is not None and h is not None and(now-l[0])<12.:b=l[1];a=h[1]
   else:
    try:b,a=await asyncio.to_thread(fetch_espn_nba_full_summary_sync,n)
    except Exception:b,a={},{}
    self.nba_boxscore_cache[n]=(now,b);self.nba_ext_summary_cache[n]=(now,a)
   E=self.nba_prop_slates.get(F)
   if E is not None:
    for m in evaluate_sp4_ingame_clinch_locks(E,K,b):
     rg=m["rung"];dk=f"SP4_3A_{rg.event_id}_{rg.market_id}"
     if dk not in self.entered_keys and dk not in self.inflight_keys:sp4_cands.append(m)
   x=self.nba_subperiod_slates.get(F)
   if x is not None and a:
    for e in evaluate_sp4_subperiod_and_ext_locks(x,a):
     f=f"SP4_SUB_LK_{F}_{e['market_id']}"
     if f not in self.entered_keys and f not in self.inflight_keys:sp4_sub_cands.append((f,e))
  g=[t for c in sp4_cands for t in(c["rung"].yes_token,c["rung"].no_token)]+[t for _,slk in sp4_sub_cands for t in(slk["token_id"],slk["opp_token_id"])]
  if not g:return
  p=await self.fetch_books_batch(sorted(set(g)),timeout=3.)
  for m in sp4_cands:
   rg=m["rung"];J,I=p.get(rg.yes_token),p.get(rg.no_token)
   if not J or not I:continue
   o,_=extract_best_bid(I.get("bids")or[])
   if o>.04:continue
   D=float(getattr(rg,"fee_rate",.0)or.0);C=float(getattr(rg,"fee_exponent",1.)or 1.);H=walk_l2_book_asks_depth_capped(J.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],BANKROLL_TICKETS["T100"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],fee_rate=D,min_l1_usd=15.,max_ask_px=.9881,fee_exponent=C)
   if H.get("filled"):
    M=float(H["eff_px"]);G=float(m["p_lock"]);L=round(G-M,4)
    if.72<=M<=.988 and L>=.012:dk=f"SP4_3A_{rg.event_id}_{rg.market_id}";k=max(now+6e2,float(rg.settle_est_ts));opps_out.append({"sleeve":"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","market":f"NBA [{m['mode']}] {rg.player_name} {rg.stat_type}={m['current_stat']} > {rg.line}","ask_vwap":M,"p_model":G,"net_edge":L,"l1_usd":H["l1_usd"],"close_ts":k});self.emit_live_single_leg_lock_candidate(sleeve_source="SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",asset="NBA",dedupe_key=dk,token_id=rg.yes_token,opp_token_id=rg.no_token,market_id=rg.market_id,condition_id=rg.condition_id,side_label="YES",display_label=f"{rg.player_name} {rg.stat_type} O{rg.line} ({m['current_stat']})",bk_win=J,bk_opp=I,fee_rate=D,fee_exponent=C,neg_risk=False,close_ts=k,now_ts=now,max_lock_eff_px=.988,max_opp_bid=.025,hold_to_maturity=True,p_model=G);await self.open_shadow_position("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",dk,"NBA_PROP",f"{rg.game_title} [{rg.player_name} {rg.stat_type} O{rg.line} (cur={m['current_stat']})]","YES",rg.yes_token,D,G,k,{"market_id":rg.market_id,"condition_id":rg.condition_id,"opp_token_id":rg.no_token,"mode":m["mode"],"stat_val":m["current_stat"],"fee_exponent":C},prefetched_book=J)
  for f,e in sp4_sub_cands:
   w,v=p.get(e["token_id"]),p.get(e["opp_token_id"])
   if not w or not v:continue
   j,_=extract_best_bid(v.get("bids")or[])
   if j>.04:continue
   u=float(e.get("fee_rate",.0)or.0);s=float(e.get("fee_exponent",1.)or 1.);B=walk_l2_book_asks_depth_capped(w.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],BANKROLL_TICKETS["T100"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],fee_rate=u,min_l1_usd=15.,max_ask_px=.9881,fee_exponent=s)
   if B.get("filled"):
    A=float(B["eff_px"]);r=float(e["p_lock"]);z=round(r-A,4)
    if.72<=A<=.988 and z>=.012:
     i=max(now+6e2,float(e["close_ts"]));opps_out.append({"sleeve":"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","market":f"NBA [{e['mode']}] {e['display_label']}","ask_vwap":A,"p_model":r,"net_edge":z,"l1_usd":B["l1_usd"],"close_ts":i})
     if self.is_sleeve_grad8_ready("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"):self.emit_live_single_leg_lock_candidate(sleeve_source="SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",asset="NBA",dedupe_key=f,token_id=str(e["token_id"]),opp_token_id=str(e["opp_token_id"]),market_id=str(e["market_id"]),condition_id=str(e["condition_id"]),side_label=str(e["side_label"]),display_label=str(e["display_label"]),bk_win=w,bk_opp=v,fee_rate=u,fee_exponent=s,neg_risk=bool(e.get("neg_risk",False)),close_ts=i,now_ts=now,max_lock_eff_px=.988,max_opp_bid=.025,hold_to_maturity=True,p_model=r)
     await self.open_shadow_position("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",f,"NBA_SUBPERIOD",e["display_label"],str(e["side_label"]),str(e["token_id"]),u,r,i,{"market_id":e["market_id"],"condition_id":e["condition_id"],"opp_token_id":e["opp_token_id"],"mode":e["mode"],"fee_exponent":s},prefetched_book=w)
 async def _run_bg_nba_endgame(self):
  try:a=[];await self.scan_nba_endgame_locks(a);self.cached_nba_endgame_opps=a
  except Exception as exc:logger.warning(f"Background NBA endgame scan notice: {exc}")
 async def _run_bg_tradfi_sports(self):
  try:a=[];await self.scan_tradfi_and_sports_markets(a);self.cached_tradfi_sports_opps=a
  except Exception as exc:logger.warning(f"Background TradFi/Sports scan notice: {exc}")
 async def run_forever(self):
  logger.info("Starting Polymarket Alpha-124 Unified Shadow Daemon (W1/W3 + Asian METAR + B1/B2 + M3/N1 NegRisk + U1 Daily + D1/4h/QuietBook + S5M + P1 PreOpen + S2)...")
  try:
   if not self.single_scan and(self._bg_clob_ws_task is None or self._bg_clob_ws_task.done()):self._bg_clob_ws_task=asyncio.create_task(self._run_clob_d1_ws_loop())
   if not self.single_scan and self._chainlink_ws is not None and(self._bg_chainlink_ws_task is None or self._bg_chainlink_ws_task.done()):self._bg_chainlink_ws_task=asyncio.create_task(self._chainlink_ws.run_forever())
   while True:
    t0=time.time();self.cycle_count+=1;await self.update_crypto_spots()
    if not self.weather_events or self.single_scan:await self.discover_all_markets()
    elif(t0-self.last_discovery_ts)>=3e2 and(self._bg_discovery_task is None or self._bg_discovery_task.done()):self.last_discovery_ts=t0;self._bg_discovery_task=asyncio.create_task(self._run_bg_discovery())
    h=self.poll_fresh_shock_triggers(now_ts=t0)
    if h:n=[];await self.handle_shock_triggers(h,n,now_ts=t0);self.cached_shock_opps=n
    c=[];o=[];v=[];y=[];await self.scan_same_oracle_dominance_boxes(c);await self.scan_exact_twap_locks(o);await self.scan_s5m_chainlink_sniper(v);await self.scan_and_manage_preopen_maker_straddles(y)
    if self.single_scan:u=[];await self.scan_multistrike_markets(u);await self.scan_daily_updown_locks(u);await self.scan_barrier_markets(u);self.cached_mid_opps=u;A=[];await self.scan_weather_markets(A);self.cached_weather_opps=A;x=[];await self.scan_tradfi_and_sports_markets(x);self.cached_tradfi_sports_opps=x;t=[];await self.scan_nba_endgame_locks(t);self.cached_nba_endgame_opps=t
    else:
     k=6. if self.has_live_nba_window(t0)else 120.
     if(t0-self.last_nba_endgame_scan_ts)>=k and(self._bg_nba_task is None or self._bg_nba_task.done()):self.last_nba_endgame_scan_ts=t0;self._bg_nba_task=asyncio.create_task(self._run_bg_nba_endgame())
     if(t0-self.last_crypto_mid_scan_ts)>=18. and(self._bg_mid_task is None or self._bg_mid_task.done()):self.last_crypto_mid_scan_ts=t0;self._bg_mid_task=asyncio.create_task(self._run_bg_mid_crypto())
     e=8. if(self.has_live_sports_window(t0)or self.pending_zero_fee_maker_anchors)else 20.
     if(t0-self.last_tradfi_sports_scan_ts)>=e and(self._bg_tradfi_task is None or self._bg_tradfi_task.done()):self.last_tradfi_sports_scan_ts=t0;self._bg_tradfi_task=asyncio.create_task(self._run_bg_tradfi_sports())
     if(t0-self.last_weather_scan_ts)>=90. and(self._bg_weather_task is None or self._bg_weather_task.done()):self.last_weather_scan_ts=t0;self._bg_weather_task=asyncio.create_task(self._run_bg_weather())
    D=(o+c+v+y+self.cached_shock_opps+self.cached_mid_opps+self.cached_nba_endgame_opps+self.cached_tradfi_sports_opps+self.cached_weather_opps);await self.manage_pending_maker_orders();await self.manage_pending_zero_fee_maker_anchors();await self.manage_open_positions();await self.write_state_files_async(D);logger.info(f"[Cycle {self.cycle_count}] BTC=${self.spots.get('BTC',0):,.1f} ETH=${self.spots.get('ETH',0):,.1f} | Monitored(W={len(self.weather_events)}, B={len(self.barrier_rungs)}, M={len(self.strike_ladders)}, NR={len(self.negrisk_ladders)}, PythH={len(self.pyth_barrier_rungs)}, PythC={len(self.pyth_close_ladders)}, NBA={len(self.nba_games)}/{len(self.live_nba_board)}live(SP4={len(self.nba_prop_slates)},SP4+={len(self.nba_subperiod_slates)},EM={len(self.lp1_nba_em_bundles)}), SP3={len(self.multi_sport_games)}(NFLEM={len(self.lp1_nfl_em_bundles)}), SOC1={len(self.soccer_trees)}, TEN1={len(self.tennis_specs)}, API1={len(self.esports_bo3_specs)}, BOP={len(self.lp1_bop_legs)//2}, LP2={len(self.lp2_implication_groups)}, CAL1={len(self.cal1_ladders)}, UMA={len(self.uma_proposed_markets)}, NR0={len(self.negrisk_zero_slates)}, NRC={len(self.negrisk_convert_slates)}, TW={len(self.counting_slates)}, FOMC={len(self.fomc_truth_legs)//2}, OS={len(self.oil_senate_truth_legs)//2}, D2={len(self.hourly_12pm_markets)}, U1={len(self.daily_updown_markets)}, D={len(self.dominance_pairs)}, D4h={len(self.dominance_4h_pairs)}, S5m={len(self.s5m_candles)}, P1={len(self.preopen_15m_candles)}, S2={len(self.twap_candles)}) | MakerPend={len(self.pending_maker_orders)} ZFAncPend={len(self.pending_zero_fee_maker_anchors)} PreOpenPend={len(self.pending_preopen_straddles)} OpenPos={len(self.open_positions)} ClosedPos={len(self.closed_positions)} | TopOpps={len(self.top_opportunities)}")
    if self.single_scan:break
    w=time.time();m=math.ceil(w/14400.)*14400.-w;d=not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK")
    if d and self.is_in_exact_twap_lock_window(w):a=3.
    elif self.is_in_same_oracle_overlap_window(w):a=3.5
    elif self.pending_zero_fee_maker_anchors:a=4.
    elif 8.<=m<=905. or self.pending_preopen_straddles or self.has_live_sports_window(w):a=6.
    else:a=12.
    s=t0+max(2.,a);b=t0
    while True:
     B=time.time()
     if B>=s:break
     g=self._ws_d1_wakeup.is_set()
     if g:self._ws_d1_wakeup.clear()
     l=.12 if g else.5
     if self.is_in_same_oracle_overlap_window(B)and(B-b)>=l:
      b=B;j=[];await self.scan_same_oracle_dominance_boxes(j,now_ts=B)
      if j:c=j
      if self.pending_zero_fee_maker_anchors:await self.manage_pending_zero_fee_maker_anchors(now_ts=B)
     elif(self.pending_maker_anchors or self.pending_zero_fee_maker_anchors)and(B-b)>=.5:
      b=B
      if self.pending_maker_anchors:await self.manage_pending_maker_anchors(now_ts=B)
      if self.pending_zero_fee_maker_anchors:await self.manage_pending_zero_fee_maker_anchors(now_ts=B)
     r=math.ceil(B/3e2)*3e2-B
     if d and r<=65. and(B-self.last_usd_sample_ts)>=1.:self.record_usd_spot_samples(B)
     q=self.poll_fresh_shock_triggers(now_ts=B)
     if q:
      f=set(self.pending_maker_orders);i=len(self.open_positions);z=[];await self.handle_shock_triggers(q,z,now_ts=B)
      if z:self.cached_shock_opps=z
      if z or set(self.pending_maker_orders)!=f or len(self.open_positions)!=i:await self.write_state_files_async(o+c+v+y+self.cached_shock_opps+self.cached_mid_opps+self.cached_nba_endgame_opps+self.cached_tradfi_sports_opps+self.cached_weather_opps)
     if d and a>3. and self.is_in_exact_twap_lock_window(B):break
     p=min(.2,max(.03,s-time.time()))
     try:await asyncio.wait_for(self._ws_d1_wakeup.wait(),timeout=p)
     except asyncio.TimeoutError:pass
  finally:
   for C in(self._bg_chainlink_ws_task,self._bg_clob_ws_task,self._bg_discovery_task,self._bg_mid_task,self._bg_tradfi_task,self._bg_weather_task,self._bg_nba_task):
    if C is not None and not C.done():
     C.cancel()
     try:await C
     except BaseException:pass
   if self.session and not self.session.closed:await self.session.close()
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
 a=http_get_json(f"{CLOB_URL}/prices-history?market={token_id}&interval=max&fidelity={fidelity}",timeout=8.)
 if not a or not isinstance(a,dict):return[]
 hist=a.get("history")or[];b=[(int(r["t"]),float(r["p"]))for r in hist if"t"in r and"p"in r];b.sort(key=lambda x:x[0]);return b
def fetch_binance_5m_series(symbol,start_ts,end_ts):
 f={};a=start_ts*1000;c=end_ts*1000
 while a<c:
  e=f"{BINANCE_URL}/api/v3/klines?symbol={symbol}&interval=5m&startTime={a}&endTime={c}&limit=1000";d=http_get_json(e,timeout=10.)
  if not d:break
  for r in d:ts=int(r[0])//1000;f[ts]=(float(r[1]),float(r[2]),float(r[3]),float(r[4]))
  b=int(d[-1][0])
  if b<=a:break
  a=b+300000
 return f
def fetch_deribit_dvol_hourly(currency,start_ts,end_ts):
 e=f"{DERIBIT_URL}?currency={currency}&start_timestamp={start_ts*1000}&end_timestamp={end_ts*1000}&resolution=3600";a=http_get_json(e,timeout=10.);d={};c=(a or{}).get("result",{}).get("data")or[]
 for b in c:ts=int(b[0])//1000;d[ts]=float(b[4])/1e2
 return d
def summarize_trades(trades,label):
 if not trades:return{"label":label,"trades":0,"wins":0,"losses":0,"win_rate_pct":.0,"net_pnl_usd":.0,"avg_pnl_usd":.0,"avg_roi_pct":.0,"profit_factor":.0,"max_drawdown_usd":.0}
 trades_s=sorted(trades,key=lambda x:x["entry_ts"]);pnls=[float(t["pnl_usd"])for t in trades_s];g=[float(t["roi_pct"])for t in trades_s];f=sum(1 for p in pnls if p>0);e=len(pnls)-f;c=sum(p for p in pnls if p>0);b=abs(sum(p for p in pnls if p<0));pf=(c/b)if b>1e-6 else(99.9 if c>0 else.0);eq=.0;d=.0;a=.0
 for p in pnls:eq+=p;d=max(d,eq);a=max(a,d-eq)
 return{"label":label,"trades":len(pnls),"wins":f,"losses":e,"win_rate_pct":round(1e2*f/len(pnls),2),"net_pnl_usd":round(sum(pnls),2),"avg_pnl_usd":round(sum(pnls)/len(pnls),2),"avg_roi_pct":round(sum(g)/len(g),2),"profit_factor":round(pf,2),"max_drawdown_usd":round(a,2)}
def run_weather_backtest():
 print("[1/3] Fetching resolved October 2026 Daily Weather markets across 16 global cities...",flush=True);N=[]
 for J in WEATHER_SERIES_SAMPLE:
  Q=http_get_json(f"{GAMMA_URL}/events?series_slug={J}&closed=true&order=endDate&ascending=false&limit=20")or[]
  for ev in Q:
   sp=parse_weather_event(ev,allow_historical_same_station=True,series_slug_hint=J)
   if sp is not None and date(2026,10,4)<=sp.obs_date<=date(2026,10,25):
    if any(b.outcome_yes_resolved==1 for b in sp.buckets):N.append(sp)
 print(f"      Parsed {len(N)} resolved METAR-governed city-days. Fetching NWP + METAR + CLOB series...",flush=True);E=defaultdict(list)
 for sp in N:E[sp.icao].append(sp)
 C={}
 for P,st_specs in E.items():
  M=min(s.obs_date for s in st_specs)-timedelta(days=1);L=max(s.obs_date for s in st_specs)+timedelta(days=1);s0=st_specs[0]
  try:C[P]=fetch_historical_nwp_hourly_sync(s0.lat,s0.lon,M,L)
  except Exception:C[P]={}
 def _load_event_bundle(sp):
  c=fetch_metar_observations_sync(sp.icao,sp.obs_date,sp.tz_name);a={}
  for b in sp.buckets:a[b.market_id]=fetch_clob_history(b.yes_token,fidelity=15)
  return sp,c,a
 bundles=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=24)as O:
  for v in O.map(_load_event_bundle,N):
   if v[1]:bundles.append(v)
 print(f"      Loaded {len(bundles)} complete Weather city-day bundles with raw METAR + CLOB history.",flush=True);e=1.15;f=999.;m=[b for b in bundles if b[0].obs_date<=date(2026,10,16)]
 for D in(.85,1.05,1.25,1.45):
  j=.0;l=0
  for sp,metars,_ in m:
   tz=ZoneInfo(sp.tz_name);u=datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,11,0,tzinfo=tz);h=u.astimezone(timezone.utc);R=compute_weather_probabilities(sp,h,metars,C.get(sp.icao,{}),forecast_sigma_base_c=D)
   for w,b in enumerate(sp.buckets):y=1. if b.outcome_yes_resolved==1 else.0;j+=(R["probs"][w]-y)**2;l+=1
  if l>0 and(j/l)<f:f=j/l;e=D
 print(f"      [TRAIN Calibration] Optimal Weather NWP kernel sigma={e:.2f}°C (Brier={f:.4f}).",flush=True);w1_trades=[];w2_trades=[];B=1e2;A=50.;g=.01
 for sp,metars,clob_map in sorted(bundles,key=lambda x:x[0].obs_date):
  tz=ZoneInfo(sp.tz_name);I=C.get(sp.icao,{});K="TRAIN"if sp.obs_date<=date(2026,10,16)else"TEST"
  def _price_at(mkt_id,ts):
   c=clob_map.get(mkt_id)or[];a=None
   for b,px in c:
    if b<=ts:
     if ts-b<=7200:a=px
    else:break
   return a
  d=False
  for hr,mn in((9,0),(11,30),(13,30)):
   if d:break
   h=datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,hr,mn,tzinfo=tz).astimezone(timezone.utc);k=int(h.timestamp());z=int(datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,14,0,tzinfo=tz).astimezone(timezone.utc).timestamp());q=I.get(z)or[]
   if q and(max(q)-min(q))>1.6:continue
   v=compute_weather_probabilities(sp,h,metars,I,forecast_sigma_base_c=e);i=None
   for w,b in enumerate(sp.buckets):
    p=_price_at(b.market_id,k)
    if p is None:continue
    a=round(p+g,4);r=v["probs"][w];o=r-a
    if.16<=a<=.62 and o>=.1 and r>=.34:
     if i is None or o>i[0]:i=(o,w,b,a,r)
   if i is not None:o,w,b,a,r=i;n=A/a;G=(b.outcome_yes_resolved==1);F=(n*1.-A)if G else(-A);w2_trades.append({"split":K,"sleeve":"W2_ENSEMBLE_VALUE","city":sp.city,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket":b.label,"entry_ts":k,"entry_px":a,"p_model":round(r,4),"edge":round(o,4),"won":G,"pnl_usd":round(F,2),"roi_pct":round(1e2*F/A,2)});d=True
  c=False
  for hr,mn in((16,0),(17,0),(18,0),(19,0),(20,0),(21,0),(22,0)):
   if c:break
   h=datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,hr,mn,tzinfo=tz).astimezone(timezone.utc);k=int(h.timestamp());v=compute_weather_probabilities(sp,h,metars,I,forecast_sigma_base_c=e)
   if not v["is_solar_lock"]or v["locked_bucket_idx"]is None:continue
   b=sp.buckets[v["locked_bucket_idx"]];p=_price_at(b.market_id,k)
   if p is None:continue
   a=round(p+g,4);H=v["p_locked_bucket"];o=H-a
   if.55<=a<=.93 and o>=.04:n=B/a;G=(b.outcome_yes_resolved==1);F=(n*1.-B)if G else(-B);w1_trades.append({"split":K,"sleeve":"W1_SOLAR_PEAK_LOCK","city":sp.city,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket":b.label,"entry_ts":k,"entry_px":a,"p_model":round(H,4),"cooling_cushion_c":v["cooling_cushion_c"],"edge":round(o,4),"won":G,"pnl_usd":round(F,2),"roi_pct":round(1e2*F/B,2)});c=True
 return{"calibrated_sigma_c":e,"events_evaluated":len(bundles),"W1_SOLAR_PEAK_LOCK":{"ALL":summarize_trades(w1_trades,"W1_ALL"),"TRAIN":summarize_trades([t for t in w1_trades if t["split"]=="TRAIN"],"W1_TRAIN"),"TEST_OOS":summarize_trades([t for t in w1_trades if t["split"]=="TEST"],"W1_TEST_OOS"),"sample_trades":w1_trades[-8:]},"W2_ENSEMBLE_VALUE":{"ALL":summarize_trades(w2_trades,"W2_ALL"),"TRAIN":summarize_trades([t for t in w2_trades if t["split"]=="TRAIN"],"W2_TRAIN"),"TEST_OOS":summarize_trades([t for t in w2_trades if t["split"]=="TEST"],"W2_TEST_OOS"),"sample_trades":w2_trades[-8:]}}
def run_crypto_barrier_and_strike_backtests():
 print("[2/3] Fetching Oct 2026 Binance 5m klines + Deribit DVOL + Resolved Hit & Strike events...",flush=True);W=int(datetime(2026,9,29,0,0,tzinfo=timezone.utc).timestamp());_i=int(datetime(2026,10,25,16,0,tzinfo=timezone.utc).timestamp());klines={"BTC":fetch_binance_5m_series("BTCUSDT",W,_i),"ETH":fetch_binance_5m_series("ETHUSDT",W,_i)};dvol={"BTC":fetch_deribit_dvol_hourly("BTC",W,_i),"ETH":fetch_deribit_dvol_hourly("ETH",W,_i)}
 def _get_spot(asset,ts):b5=(ts//300)*300;a=klines[asset].get(b5)or klines[asset].get(b5-300);return a[3]if a else None
 def _realized_vol_4h_annual(asset,ts):
  b5=(ts//300)*300;b=klines[asset];rets=[]
  for t in range(b5-48*300,b5,300):
   r0=b.get(t);r1=b.get(t+300)
   if r0 and r1 and r0[3]>0 and r1[3]>0:rets.append(math.log(r1[3]/r0[3]))
  if len(rets)<12:return.0
  a=sum(x*x for x in rets)/len(rets);return math.sqrt(a*(365.25*288.))
 def _get_dvol(asset,ts):
  bh=(ts//3600)*3600
  for a in(0,-3600,-7200,3600):
   if(bh+a)in dvol[asset]:return dvol[asset][bh+a]
  return.42 if asset=="BTC"else.54
 def _already_touched(asset,start_ts,now_ts,strike,direction):
  a=(int(start_ts)//300)*300;c=(now_ts//300)*300;b=klines[asset]
  for t in range(a,c+300,300):
   d=b.get(t)
   if not d:continue
   if direction=="UP"and d[1]>=strike:return True
   if direction=="DOWN"and d[2]<=strike:return True
  return False
 V=[]
 for asset,_p,_d in[("BTC","DAILY","bitcoin-hit-price-daily"),("ETH","DAILY","ethereum-hit-price-daily"),("BTC","WEEKLY","bitcoin-hit-price-weekly"),("ETH","WEEKLY","ethereum-hit-price-weekly")]:
  _c=http_get_json(f"{GAMMA_URL}/events?series_slug={_d}&closed=true&order=endDate&ascending=false&limit=24")or[]
  for ev in _c:
   for r in parse_hit_event(ev,asset,_p,_d):
    if r.resolved_yes is not None and r.end_ts>=datetime(2026,10,2,tzinfo=timezone.utc).timestamp():V.append(r)
 print(f"      Loaded {len(V)} resolved Barrier Hit rungs. Fetching CLOB histories...",flush=True)
 def _fetch_barrier_hist(r):return r,fetch_clob_history(r.yes_token,fidelity=20),fetch_clob_history(r.no_token,fidelity=20)
 barrier_bundles=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=28)as _b:
  for _a in _b.map(_fetch_barrier_hist,V):
   if _a[1]or _a[2]:barrier_bundles.append(_a)
 g=1.12;k=999.;D=[x for x in barrier_bundles if x[0].end_ts<=SPLIT_CUTOFF_TS]
 for _l in(.95,1.05,1.15,1.25):
  bs=.0;bn=0
  for r,p,_ in D:
   if not p:continue
   _h=len(p)//3;j,_=p[_h];J=r.end_ts-j;u=_get_spot(r.asset,j)
   if not u or J<=1800 or _already_touched(r.asset,r.start_ts,j,r.strike,r.direction):continue
   N,_=get_wing_implied_vol(r.asset,u,r.strike,J,dvol_annual_override=_get_dvol(r.asset,j));_s=first_passage_touch_prob(u,r.strike,J,N,r.direction,wick_vol_multiplier=_l);bs+=(_s-float(r.resolved_yes))**2;bn+=1
  if bn>0 and(bs/bn)<k:k=bs/bn;g=_l
 print(f"      [TRAIN Calibration] Optimal Barrier 1m-Wick Vol Multiplier={g:.2f} (Brier={k:.4f}).",flush=True);b1_tail_trades=[];b2_nolock_trades=[];S=.07;P=.008
 for r,p,L in sorted(barrier_bundles,key=lambda x:x[0].end_ts):
  R="TRAIN"if r.end_ts<=SPLIT_CUTOFF_TS else"TEST"
  for _k,(j,K)in enumerate(p):
   J=r.end_ts-j
   if not(7200<=J<=5*86400):continue
   if not(.04<=K<=.26):continue
   u=_get_spot(r.asset,j);_o=_get_spot(r.asset,j-7200)
   if not u or not _o or _already_touched(r.asset,r.start_ts,j,r.strike,r.direction):continue
   _e=_get_dvol(r.asset,j);_n=_realized_vol_4h_annual(r.asset,j);E=(r.direction=="UP"and u>_o*1.003)or(r.direction=="DOWN"and u<_o*.997)
   if _n<.95*_e or not E:continue
   N,_=get_wing_implied_vol(r.asset,u,r.strike,J,dvol_annual_override=max(_e,.5*(_e+_n)));B=first_passage_touch_prob(u,r.strike,J,N,r.direction,wick_vol_multiplier=g);o=K+P;w=S*o*(1.-o);n=o+w;I=B-n
   if I>=.065 and(B/n)>=1.4:
    i=25.;h=i/n;_m=min(.88,round(2.*o,3));C=False
    for Q,v in p[_k+1:]:
     if v>=_m+.005:C=True;break
    if C:b=h*_m;l=True;a="MAKER_2X_TP"
    else:l=(r.resolved_yes==1);b=h*(1. if l else.0);a="HOLD_SETTLE"
    F=b-i;b1_tail_trades.append({"split":R,"sleeve":"B1_CONVEX_TAIL_YES","asset":r.asset,"question":r.question,"entry_ts":j,"entry_px":round(n,4),"p_model":round(B,4),"edge":round(I,4),"exit_mode":a,"won":l,"pnl_usd":round(F,2),"roi_pct":round(1e2*F/i,2)});break
  for j,U in L:
   J=r.end_ts-j
   if not(3600<=J<=36000):continue
   if not(.68<=U<=.9):continue
   u=_get_spot(r.asset,j)
   if not u or _already_touched(r.asset,r.start_ts,j,r.strike,r.direction):continue
   N,_=get_wing_implied_vol(r.asset,u,r.strike,J,dvol_annual_override=_get_dvol(r.asset,j));B=first_passage_touch_prob(u,r.strike,J,N,r.direction,wick_vol_multiplier=g);_q=1.-B;o=U+P;w=S*o*(1.-o);n=o+w;I=_q-n
   if _q>=.88 and I>=.04:i=1e2;h=i/n;l=(r.resolved_yes==0);F=(h*1.-i)if l else(-i);b2_nolock_trades.append({"split":R,"sleeve":"B2_BARRIER_NO_LOCK","asset":r.asset,"question":r.question,"entry_ts":j,"entry_px":round(n,4),"p_model":round(_q,4),"edge":round(I,4),"won":l,"pnl_usd":round(F,2),"roi_pct":round(1e2*F/i,2)});break
 print("[3/3] Fetching resolved October 2026 Multi-Strike ('above ___') ladders...",flush=True);M=[]
 for asset,_d in[("BTC","btc-multi-strikes-weekly"),("ETH","ethereum-multi-strikes-weekly")]:
  _c=http_get_json(f"{GAMMA_URL}/events?series_slug={_d}&closed=true&order=endDate&ascending=false&limit=24")or[]
  for ev in _c:
   for sr in parse_multistrike_event(ev,asset,_d):
    if sr.resolved_yes is not None and sr.end_ts>=datetime(2026,10,2,tzinfo=timezone.utc).timestamp():M.append(sr)
 def _fetch_strike_hist(sr):return sr,fetch_clob_history(sr.yes_token,fidelity=20),fetch_clob_history(sr.no_token,fidelity=20)
 A=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=28)as _b:
  for _a in _b.map(_fetch_strike_hist,M):
   if _a[1]or _a[2]:A.append(_a)
 print(f"      Loaded {len(A)} resolved Multi-Strike contracts with CLOB histories.",flush=True);m1_scalp_trades=[];m2_conv_trades=[]
 for sr,p,L in sorted(A,key=lambda x:x[0].end_ts):
  R="TRAIN"if sr.end_ts<=SPLIT_CUTOFF_TS else"TEST"
  for Z,_r,Y in[("YES",p,sr.resolved_yes==1),("NO",L,sr.resolved_yes==0)]:
   s=False;q=False
   for _k,(j,K)in enumerate(_r):
    J=sr.end_ts-j
    if J<=900:break
    u=_get_spot(sr.asset,j);_g=_get_spot(sr.asset,j-900)
    if not u or not _g:continue
    if abs(math.log(sr.strike/u))>.08:continue
    X=evaluate_svi_digital_fair_value(sr.asset,u,sr.strike,J,is_downward=sr.is_downward,dvol_annual_override=_get_dvol(sr.asset,j),now_ts=float(j));_j=X["p_yes"]if Z=="YES"else X["p_no"];O=((u-_g)/_g)*1e4;_f=(Z=="YES"and not sr.is_downward)or(Z=="NO"and sr.is_downward)
    if(_f and O<-20.)or((not _f)and O>20.):continue
    o=K+P;w=S*o*(1.-o);n=o+w;I=_j-n
    if(not s)and(10800<=J<=86400)and(.2<=o<=.8)and I>=.055:
     i=1e2;h=i/n;T=min(.96,round(n+.05,4));H=max(.04,round(o-.075,4));f=None;d=.0;a="SETTLED"
     for Q,v in _r[_k+1:]:
      if v>=T+.005:f=T;d=.0;a="MAKER_TP_5C";break
      if v<=H:m=max(.01,v-P);f=m;d=S*m*(1.-m);a="HARD_STOP_7.5C";break
      if sr.end_ts-Q<=3600:m=max(.01,v-P);f=m;d=S*m*(1.-m);a="TIME_STOP_1H";break
     if f is not None:b=h*(f-d);l=b>i
     else:b=h*(1. if Y else.0);l=Y
     F=b-i;m1_scalp_trades.append({"split":R,"sleeve":"M1_SVI_MAKER_SCALP","asset":sr.asset,"question":sr.question,"side":Z,"entry_ts":j,"entry_px":round(n,4),"p_model":round(_j,4),"edge":round(I,4),"exit_mode":a,"won":l,"pnl_usd":round(F,2),"roi_pct":round(1e2*F/i,2)});s=True
    if((not q)and(1200<=J<=6300)and(.68<=o<=.9)and X["z_sigma"]>=1.55 and _j>=.91 and I>=.04):
     i=1e2;h=i/n;e=None;c=.0;a="SETTLED";G=max(.25,o-.22)
     for _,v in _r[_k+1:]:
      if v>=.975:e=.97;c=.0;a="MAKER_TP_97C";break
      if v<=G:m=max(.05,v-P);e=m;c=S*m*(1.-m);a="SALVAGE_STOP";break
     if e is not None:b=h*(e-c);l=b>i
     else:b=h*(1. if Y else.0);l=Y
     F=b-i;m2_conv_trades.append({"split":R,"sleeve":"M2_STRIKE_CONVERGENCE","asset":sr.asset,"question":sr.question,"side":Z,"entry_ts":j,"entry_px":round(n,4),"p_model":round(_j,4),"z_sigma":X["z_sigma"],"edge":round(I,4),"exit_mode":a,"won":l,"pnl_usd":round(F,2),"roi_pct":round(1e2*F/i,2)});q=True
 y={"calibrated_wick_vol_mult":g,"rungs_evaluated":len(barrier_bundles),"B1_CONVEX_TAIL_YES":{"ALL":summarize_trades(b1_tail_trades,"B1_ALL"),"TRAIN":summarize_trades([t for t in b1_tail_trades if t["split"]=="TRAIN"],"B1_TRAIN"),"TEST_OOS":summarize_trades([t for t in b1_tail_trades if t["split"]=="TEST"],"B1_TEST_OOS"),"sample_trades":b1_tail_trades[-8:]},"B2_BARRIER_NO_LOCK":{"ALL":summarize_trades(b2_nolock_trades,"B2_ALL"),"TRAIN":summarize_trades([t for t in b2_nolock_trades if t["split"]=="TRAIN"],"B2_TRAIN"),"TEST_OOS":summarize_trades([t for t in b2_nolock_trades if t["split"]=="TEST"],"B2_TEST_OOS"),"sample_trades":b2_nolock_trades[-8:]}};z={"rungs_evaluated":len(A),"M1_SVI_MAKER_SCALP":{"ALL":summarize_trades(m1_scalp_trades,"M1_ALL"),"TRAIN":summarize_trades([t for t in m1_scalp_trades if t["split"]=="TRAIN"],"M1_TRAIN"),"TEST_OOS":summarize_trades([t for t in m1_scalp_trades if t["split"]=="TEST"],"M1_TEST_OOS"),"sample_trades":m1_scalp_trades[-8:]},"M2_STRIKE_CONVERGENCE":{"ALL":summarize_trades(m2_conv_trades,"M2_ALL"),"TRAIN":summarize_trades([t for t in m2_conv_trades if t["split"]=="TRAIN"],"M2_TRAIN"),"TEST_OOS":summarize_trades([t for t in m2_conv_trades if t["split"]=="TEST"],"M2_TEST_OOS"),"sample_trades":m2_conv_trades[-8:]}};return y,z
def main():
 t0=time.time();b=run_weather_backtest();a,c=run_crypto_barrier_and_strike_backtests();d={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"elapsed_sec":round(time.time()-t0,2),"split_cutoff_utc":"2026-10-16T23:59:59Z","option_1_weather":b,"option_2_barrier_onetouch":a,"option_4_multistrike_svi":c};REPORT_JSON.write_text(json.dumps(d,indent=2),encoding="utf-8");print("\n================= WALK-FORWARD BACKTEST SUMMARY =================")
 for f,e in[("OPTION #1 WEATHER",["W1_SOLAR_PEAK_LOCK","W2_ENSEMBLE_VALUE"]),("OPTION #2 BARRIER",["B1_CONVEX_TAIL_YES","B2_BARRIER_NO_LOCK"]),("OPTION #4 STRIKE SVI",["M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE"])]:
  g=(b if"WEATHER"in f else(a if"BARRIER"in f else c));print(f"\n--- {f} ---")
  for sl in e:tr=g[sl]["TRAIN"];te=g[sl]["TEST_OOS"];al=g[sl]["ALL"];print(f"  {sl:24s} | ALL: {al['trades']:3d} tr, WR={al['win_rate_pct']:5.1f}%, PnL=${al['net_pnl_usd']:+8.2f}, PF={al['profit_factor']:5.2f}, MaxDD=${al['max_drawdown_usd']:6.2f}\n  {'':24s} | TRN: {tr['trades']:3d} tr, WR={tr['win_rate_pct']:5.1f}%, PnL=${tr['net_pnl_usd']:+8.2f}, PF={tr['profit_factor']:5.2f} | OOS: {te['trades']:3d} tr, WR={te['win_rate_pct']:5.1f}%, PnL=${te['net_pnl_usd']:+8.2f}, PF={te['profit_factor']:5.2f}")
 print(f"\nSaved full JSON report -> {REPORT_JSON}")
if __name__=="__main__":main()
# ======================================================================================
# [18/21] MODULE: scripts/polymarket_daily_projections.py
# PURPOSE: Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker
# ======================================================================================

#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import argparse
import json;import os;from datetime import datetime,timedelta,timezone;from pathlib import Path;from typing import Any,Dict,List,Optional,Tuple;PIPELINE_ROOT=Path(__file__).resolve().parent.parent;LIVE_STATE_FILE=PIPELINE_ROOT/"data"/"polymarket"/"live_harvester_state.json";ALPHA124_STATE_FILE=(PIPELINE_ROOT/"data"/"polymarket"/"alpha124_shadow_state.json"if(PIPELINE_ROOT/"data"/"polymarket"/"alpha124_shadow_state.json").exists()else PIPELINE_ROOT/"data"/"alpha124"/"alpha124_shadow_state.json");EXP316_STATE_FILE=PIPELINE_ROOT/"data"/"exp316"/"exp316_shadow_state.json";SOL_SHADOW_FILE=PIPELINE_ROOT/"data"/"polymarket"/"state_shadow_sol_v392.json";XRP_SHADOW_FILE=PIPELINE_ROOT/"data"/"polymarket"/"state_shadow_xrp_v392.json";PHASE34_TRACKER_FILE=PIPELINE_ROOT/"data"/"polymarket"/"shadow_phase3_4_tracker.jsonl";RISK_CONFIG_FILE=PIPELINE_ROOT/"config"/"polymarket_risk_config.json";OUTPUT_JSON_FILE=PIPELINE_ROOT/"data"/"polymarket"/"live_daily_projections.json";QUARANTINED_SLEEVES=frozenset({"M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","B1_CONVEX_TAIL_YES","S2_EXACT_TWAP_LOCK","ZERO_FEE_MAKER_ANCHOR_BOX","CTF_OVERROUND_MINT_SELL","SLEEVE_XRP_V392_SHADOW","D1_MAKER_ANCHOR_BOX","ZF_INTRADAY_MAKER_BOX","SHADOW_PHASE3A_MAKER"});GRADUATION_SPECS=[{"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","wave":"Wave 1 (Live Graduated)","target_day":1,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":13.5,"l1_daily_pnl_cap_usd":140.},{"sleeve":"D1_QUIET_BOOK_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":3,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":65.},{"sleeve":"D1_4H_DOMINANCE_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":60.},{"sleeve":"C1_BINARY_COMPLETE_SET","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"M3_LADDER_MONO_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"B3_BARRIER_MONO_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"D1_MAKER_ANCHOR_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":45.},{"sleeve":"N1_NEGRISK_CROSS_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":20.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"W3_WEATHER_SLATE_ARB","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"CM_B3_PYTH_BARRIER_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"SP1_NBA_ZERO_FEE_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"ZF_INTRADAY_MAKER_BOX","wave":"Wave 1 (Fast-Track Maker Box 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":92.,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"NR0_ZERO_FEE_SLATE_ARB","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"B4_TOUCHED_BARRIER_WICK_LOCK","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"ZERO_FEE_MAKER_ANCHOR_BOX","wave":"Wave 1 (Fast-Track Maker Box)","target_day":5,"min_days":1.,"min_settled":8,"min_wr_pct":92.,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"CTF_OVERROUND_MINT_SELL","wave":"Wave 1 (Instant Mint-Sell 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":5,"min_days":1.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"FED1_CENTRAL_BANK_LP_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"COND1_MACRO_PARTITION_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"D2_12PM_BINANCE_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":5,"min_days":1.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"GAS1_AAA_GASOLINE_LOCK","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":20.},{"sleeve":"MKR_REWARD_LOCKED_CARRY","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":20.},{"sleeve":"BOND1_UMA_RESOLUTION_CARRY","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":20.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"SP2_NBA_ENDGAME_LOCK","wave":"Wave 2 (Day 7 NBA Endgame)","target_day":7,"min_days":3.,"min_settled":15,"min_wr_pct":93.,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":45.},{"sleeve":"W1_LOW_TROUGH_LOCK","wave":"Wave 2 (Day 8 METAR Low)","target_day":8,"min_days":4.,"min_settled":15,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":40.},{"sleeve":"SLEEVE_SOL_V392_SHADOW","wave":"Wave 2 (Day 5 SOL)","target_day":5,"min_days":1.5,"min_settled":30,"min_wr_pct":85.,"source":"sol_shadow","stage1_ticket_usd":12.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"SHADOW_PHASE3A_MAKER","wave":"Wave 2 (Day 6 Maker)","target_day":6,"min_days":2.,"min_settled":25,"min_wr_pct":80.,"source":"phase3a_shadow","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":32.},{"sleeve":"W1_SOLAR_PEAK_LOCK","wave":"Wave 2 (Day 8 METAR)","target_day":8,"min_days":5.,"min_settled":20,"min_wr_pct":86.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":95.},{"sleeve":"B2_BARRIER_NO_LOCK","wave":"Wave 2 (Day 8 Barrier)","target_day":8,"min_days":5.,"min_settled":25,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":55.},{"sleeve":"CM_B2_PYTH_SESSION_NO_LOCK","wave":"Wave 2 (Day 9 Pyth 0%-Fee)","target_day":9,"min_days":5.,"min_settled":25,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":45.},{"sleeve":"CM_U1_PYTH_CLOSE_LOCK","wave":"Wave 2 (Day 10 Pyth Close)","target_day":10,"min_days":5.,"min_settled":25,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"EXP316_TRACK_A_LATE_LOCK","wave":"Wave 2 (Day 10 Strike)","target_day":10,"min_days":5.,"min_settled":25,"min_wr_pct":80.,"source":"exp316","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"U1_DAILY_UPDOWN_LOCK","wave":"Wave 3 (Day 15 Daily)","target_day":15,"min_days":10.,"min_settled":20,"min_wr_pct":85.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"S5M_CHAINLINK_SNIPER","wave":"Wave 3 (Day 15 5m)","target_day":15,"min_days":7.,"min_settled":35,"min_wr_pct":82.,"source":"alpha124","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"S4H_CHAINLINK_CONVERGENCE","wave":"Wave 3 (Day 14 4h)","target_day":14,"min_days":7.,"min_settled":25,"min_wr_pct":85.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"CM_SHOCK_PYTH_CATALYST","wave":"Wave 3 (Day 16 Macro Jump)","target_day":16,"min_days":10.,"min_settled":25,"min_wr_pct":82.,"source":"alpha124","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"S2_EXACT_TWAP_LOCK","wave":"Wave 3 (Conditional)","target_day":15,"min_days":10.,"min_settled":30,"min_wr_pct":94.,"source":"alpha124","stage1_ticket_usd":12.,"l1_daily_pnl_cap_usd":35.}]
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
def _depth_decay(ticket_usd,knee_usd=65.):
 if ticket_usd<=20.:return 1.
 return max(.58,1./(1.+.35*((ticket_usd-20.)/max(20.,knee_usd))))
def _wilson_lcb_pct(wins,n,z=1.2816):
 if n<=0:return.0
 p=max(.0,min(1.,wins/float(n)));z2=z*z;b=1.+z2/n;a=p+z2/(2.*n);c=z*((p*(1.-p)/n+z2/(4.*n*n))**.5);return round(1e2*max(.0,(a-c)/b),2)
def simulate_single_day_net_pnl(day_idx,equity_start,scenario,scale_up_threshold=98.,shadow_by_sleeve=None,sol_shadow=None,phase3a_shadow=None,exp316_t1k=None):
 d={"P25_CONSERVATIVE":1.8,"P50_BASE_FINLAND":2.7,"P75_LONDON_UPSIDE":3.6}[scenario];b={"P25_CONSERVATIVE":.105,"P50_BASE_FINLAND":.13,"P75_LONDON_UPSIDE":.152}[scenario];c={"P25_CONSERVATIVE":.86,"P50_BASE_FINLAND":.92,"P75_LONDON_UPSIDE":.96}[scenario];n={"P25_CONSERVATIVE":.62,"P50_BASE_FINLAND":1.,"P75_LONDON_UPSIDE":1.45}[scenario];m=equity_start if day_idx<8 else equity_start*.76;l=.0 if day_idx<8 else equity_start*.24;v=compute_v540_ticket_size(m);k=1.24 if equity_start>=253. else(1.16 if equity_start>=150. else 1.);j=d*k;t=b*c*_depth_decay(v,knee_usd=52.);r={"P25_CONSERVATIVE":55.,"P50_BASE_FINLAND":95.,"P75_LONDON_UPSIDE":145.}[scenario];q=min(r,v*j*t);i={"v540_option_b_directional_taker":round(q,2)};h=25. if equity_start<98. else(45. if equity_start<253. else 75.);p=min(h,m*.55);g=min(9.5*n,p*(1.45*n)*.0075);i["BOND1_uma_0pct_carry"]=round(g,2);o=28. if equity_start<98. else(48. if equity_start<253. else(75. if equity_start<1003. else 120.));u=min(o,max(12.,m*.28));f=min(38.*n,u*(1.15*n)*(.036*_depth_decay(u,knee_usd=65.)));i["D1_COND1_live_grad8_boxes"]=round(f,2)
 if day_idx>=8 and l>=15.:w=min(65.,max(12.,l*.45));s=min(28.*n,w*(.95*n)*(.038*_depth_decay(w,knee_usd=60.)));i["V3_grad8_partition_and_sports_locks"]=round(s,2)
 if equity_start>=1003.:a="INSTITUTIONAL (>=$1,003): 4 Dir Slots ($160-$200 Elastic L1 Rungs) + $120 Box Cap"
 elif equity_start>=253.:a="SCALE ($253-$1,003): 4 Dir Slots (22% Ticket) + $75 BOND1/D1/COND1 Cap"
 elif equity_start>=150.:a="HYPER_GROWTH 3-Slot (>=$150): 3 Crypto Dir Slots Unlocked (26% Ticket)"
 elif equity_start>=98.:a="HYPER_GROWTH ($98-$150): 26% Dir Ticket ($23-$35) + $45 BOND1 Cap"
 else:a="UNLEASHED_LAUNCH (<$98): v5.4.0 Option B Taker-Only + BOND1/D1/COND1 8/8"
 e=round(sum(i.values()),2);return e,i,a
def build_live_projections(days=30,fallback_equity=85.08):
 E=datetime.now(timezone.utc);D=_load_json(LIVE_STATE_FILE);C=_load_json(ALPHA124_STATE_FILE);u=_load_json(EXP316_STATE_FILE);K=_load_json(SOL_SHADOW_FILE);J=_load_json(XRP_SHADOW_FILE);I=_load_phase3a_summary(PHASE34_TRACKER_FILE);x=_load_json(RISK_CONFIG_FILE);live_equity=float(D.get("total_account_equity")or D.get("live_bankroll")or fallback_equity);q=float(D.get("high_water_mark_equity")or live_equity);m=float(x.get("scale_up_equity_threshold")or 110.);closed_live=D.get("closed_positions")or[];s=sum(1 for t in closed_live if float(t.get("realized_pnl_usd")or t.get("net_pnl_usd")or(float(t.get("realized_exit_cash",.0))-float(t.get("notional_usd",.0))-float(t.get("fee_usd",.0))))>0);l=_parse_iso(C.get("started_at"));h=(round(max(.0,(E-l).total_seconds()/86400.),2)if l else 1.);r=C.get("by_sleeve")or{};p=(u.get("tiers")or{}).get("T1000")or{};j=[]
 for sp in GRADUATION_SPECS:
  sl=sp["sleeve"]
  if sl in QUARANTINED_SLEEVES:continue
  Q=sp["source"]
  if Q=="sol_shadow":a=int(K.get("total_trades_settled")or 0);g=int(K.get("winning_trades")or 0);f=int(K.get("active_open_positions_count")or 0);c=float(K.get("realized_pnl")or.0)
  elif Q=="phase3a_shadow":a=int(I.get("closed")or 0);g=int(I.get("wins")or 0);f=0;c=float(I.get("pnl_usd")or.0)
  elif Q=="exp316":a=int(p.get("trades")or 0);g=int(p.get("wins")or 0);f=int(u.get("active_positions")or 0);c=float(p.get("net_pnl_usd")or.0)
  else:B=r.get(sl)or{};a=int(B.get("closed")or 0);g=int(B.get("wins")or 0);f=int(B.get("open")or 0);c=float(B.get("realized_pnl_t1000_usd")or.0)
  H=round(1e2*g/a,2)if a>0 else.0;i=_wilson_lcb_pct(g,a);o=round(min(1e2,1e2*a/sp["min_settled"]),1);w=round(min(1e2,1e2*h/sp["min_days"]),1);O=(a>=sp["min_settled"]and h>=sp["min_days"]and H>=sp["min_wr_pct"]and i>=max(.0,sp["min_wr_pct"]-20.)and c>.0);j.append({"sleeve":sl,"wave":sp["wave"],"source":Q,"open_now":f,"settled_now":a,"target_settled":sp["min_settled"],"sample_progress_pct":o,"days_elapsed":h,"min_days":sp["min_days"],"time_progress_pct":w,"win_rate_pct":H,"wilson_lcb90_wr_pct":i,"target_wr_pct":sp["min_wr_pct"],"realized_pnl_t1000_usd":round(c,2),"ready_for_stage1_micro_live":O})
 scenarios=["P25_CONSERVATIVE","P50_BASE_FINLAND","P75_LONDON_UPSIDE"];v={sc:live_equity for sc in scenarios};n=E.date();daily_rows=[]
 for d in range(1,days+1):
  G=(n+timedelta(days=d-1)).isoformat();P={"day":d,"date_utc":G};e="";b={}
  for sc in scenarios:
   A=v[sc];N,M,L=simulate_single_day_net_pnl(d,A,sc,scale_up_threshold=m,shadow_by_sleeve=r,sol_shadow=K,phase3a_shadow=I,exp316_t1k=p);F=round(A+N,2);v[sc]=F;z=sc.split("_")[0].lower();P[f"{z}_daily_pnl_usd"]=N;P[f"{z}_end_equity_usd"]=F
   if sc=="P50_BASE_FINLAND":e=L;b=M;P["p50_v393_ticket_usd"]=compute_v540_ticket_size(A)
  P["active_regime_and_milestone"]=e;P["p50_sleeve_pnl_breakdown_usd"]=b;daily_rows.append(P)
 y={"generated_at_utc":E.isoformat(),"model_version":"v5.4.0_option_b_taker_only_clean_roster","quarantined_sleeves_excluded":sorted(QUARANTINED_SLEEVES),"anchor_live_state":{"live_equity_usd":round(live_equity,2),"high_water_mark_usd":round(q,2),"current_v393_ticket_usd":compute_v540_ticket_size(live_equity),"current_v540_btc_ticket_usd":round(min(2e2,live_equity*(.22 if live_equity<98. else.26)),2),"current_v540_eth_sol_ticket_usd":round(min(170.,live_equity*(.22 if live_equity<98. else.26)*.85),2),"distance_to_88_dynamic_sizing_usd":round(max(.0,98.-live_equity),2),"distance_to_98_hyper_growth_usd":round(max(.0,98.-live_equity),2),"distance_to_110_slot2_unlock_usd":round(max(.0,150.-live_equity),2),"distance_to_150_slot3_unlock_usd":round(max(.0,150.-live_equity),2),"distance_to_253_scale_tier_usd":round(max(.0,253.-live_equity),2),"live_closed_trades":len(closed_live),"live_wins":s,"live_win_rate_pct":round(1e2*s/len(closed_live),2)if closed_live else.0,"alpha124_markets_monitored":C.get("markets_monitored",{}),"alpha124_open_shadow_positions":C.get("open_positions_count",0),"alpha124_resting_maker_bids":C.get("pending_maker_orders_count",0),"sol_shadow_settled":K.get("total_trades_settled",0),"sol_shadow_win_rate_pct":K.get("win_rate_pct",.0),"phase3a_maker_settled":I.get("closed",0),"xrp_shadow_settled":J.get("total_trades_settled",0)},"summary_horizons_usd":{f"day_{k}":{"date_utc":daily_rows[k-1]["date_utc"],"p25_equity":daily_rows[k-1]["p25_end_equity_usd"],"p50_equity":daily_rows[k-1]["p50_end_equity_usd"],"p75_equity":daily_rows[k-1]["p75_end_equity_usd"],"p50_net_profit":round(daily_rows[k-1]["p50_end_equity_usd"]-live_equity,2)}for k in(1,4,7,10,14,21,30)if k<=len(daily_rows)},"p75_jurisdiction_compliance_note":("P75 models <15ms low-latency execution; Polymarket restricts UK (eu-west-2), FR, DE, IE, and ON — keep live execution on Finland (or another verified non-restricted EU region) unless lawful eligibility is confirmed."),"sleeve_graduation_live_tracker":j,"day_by_day_schedule":daily_rows};return y
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
 st=json.loads(STATE_FILE.read_text(encoding="utf-8"));print(f"=== ALPHA-124 SHADOW SCORECARD (Updated: {st.get('updated_at_utc')}) ===");print(f"Cycles: {st.get('cycle_count')} | MakerPending: {st.get('pending_maker_orders_count',0)} | Monitored: {st.get('markets_monitored')}");print(f"Spots : {st.get('spots')}");print(f"Realized PnL by Bankroll Tier: {st.get('portfolio_realized_pnl_by_bankroll_usd')}");print("\n--- Sleeve Breakdown ---")
 for sl,m in(st.get("by_sleeve")or{}).items():print(f"  {sl:28s} | Open={m['open']:2d} | Closed={m['closed']:3d} ({m['wins']}W/{m['losses']}L, WR={m['win_rate_pct']:5.1f}%) | T1000 PnL=${m['realized_pnl_t1000_usd']:+8.2f}")
 c=st.get("by_d1_asset")or{}
 if c:
  print("\n--- D1 Same-Oracle 7-Coin Graduation Status ---")
  for f,dm in c.items():print(f"  {f:6s} | Open={dm['open']:2d} | Closed={dm['closed']:3d} ({dm['wins']}W/{dm['losses']}L, WR={dm['win_rate_pct']:5.1f}%) | T1000 PnL=${dm['realized_pnl_t1000_usd']:+8.2f}")
 b=st.get("pending_maker_orders")or[]
 if b:
  print(f"\n--- Resting 0%-Fee Maker Entry Bids ({len(b)}) ---")
  for e in b[:10]:print(f"  [{e['sleeve']}] {e['asset_or_city']} {e['title']} ({e['side']}) | resting_bid=${e['resting_bid']:.3f} (ask_at_post=${e['best_ask_at_post']:.3f}, p_mod={e['p_model_at_post']:.3f})")
 a=st.get("open_positions")or[]
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
 env=dict(os.environ)
 if hasattr(os,"getuid"):env.setdefault("XDG_RUNTIME_DIR",f"/run/user/{os.getuid()}")
 svc_map={s:subprocess.run(["systemctl","--user","is-active",s],capture_output=True,text=True,env=env).stdout.strip()for s in SERVICES};g=_read_json("data/polymarket/live_harvester_state.json");b=_read_json("data/alpha124/alpha124_shadow_state.json");f=_read_json("data/polymarket/live_daily_projections.json");d=_read_json("data/polymarket/paper_trader_state.json");sol=_read_json("data/polymarket/state_shadow_sol_v392.json");xrp=_read_json("data/polymarket/state_shadow_xrp_v392.json");c=_read_json("data/exp316/exp316_shadow_state.json");closed=g.get("closed_positions")or[];e=sum(1 for t in closed if float(t.get("realized_pnl_usd")or t.get("net_pnl_usd")or(float(t.get("realized_exit_cash",.0))-float(t.get("notional_usd",.0))-float(t.get("fee_usd",.0))))>0);j_out=subprocess.run(["journalctl","--user","-u","polymarket-live-harvester","--since","24 hours ago","--no-pager"],capture_output=True,text=True,env=env).stdout.splitlines();h=[line for line in j_out if"SHADOW_PHASE3A"in line][-5:];p4=[line for line in j_out if"SHADOW_PHASE4"in line][-5:];alt_keys=["timestamp","current_equity","realized_pnl","total_trades_settled","winning_trades","losing_trades","win_rate_pct","profit_factor","active_open_positions_count","ready_for_live_graduation","graduation_criteria"];a={"services":svc_map,"all_services_active":all(v=="active"for v in svc_map.values()),"live_v392":{"updated_at_utc":g.get("updated_at_utc"),"live_bankroll_usd":g.get("live_bankroll"),"total_account_equity_usd":g.get("total_account_equity"),"high_water_mark_equity_usd":g.get("high_water_mark_equity"),"active_positions_count":g.get("active_positions_count"),"closed_positions_count":len(closed),"closed_wins":e,"progress_to_n40_gate":f"{len(closed)}/40","distance_to_88_dynamic_tier_usd":round(max(.0,88.-float(g.get("total_account_equity")or.0)),2),"distance_to_110_scaleup_tier_usd":round(max(.0,110.-float(g.get("total_account_equity")or.0)),2),"risk_halt":g.get("risk_halt"),"reconciliation_required":g.get("reconciliation_required"),"global_halt_reasons":g.get("global_halt_reasons")},"alpha124_11sleeve_shadow":{"updated_at_utc":b.get("updated_at_utc"),"markets_monitored":b.get("markets_monitored"),"open_positions_count":b.get("open_positions_count"),"pending_maker_orders_count":b.get("pending_maker_orders_count"),"portfolio_realized_pnl_by_bankroll_usd":b.get("portfolio_realized_pnl_by_bankroll_usd"),"by_sleeve":b.get("by_sleeve")},"live_daily_projections_summary":f.get("summary_horizons_usd",{}),"paper_sleeve1_benchmark":d.get("validation_oos_epoch",{}),"shadow_sol_v392":{k:sol.get(k)for k in alt_keys},"shadow_xrp_v392":{k:xrp.get(k)for k in alt_keys},"shadow_exp316":c,"shadow_phase3a_recent_24h":h,"shadow_phase4_recent_24h":p4};print(json.dumps(a,indent=2))
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
def test_kmia_convective_rain_cold_pool_bias_guard():from datetime import date,timedelta;from src.polymarket_research.weather_metar_engine import(WeatherBucket,WeatherEventSpec,compute_weather_probabilities);c=datetime(2026,10,25,17,0,tzinfo=timezone.utc);b=parse_metar_line("METAR KMIA 251653Z 07009KT 6SM RA SCT025CB BKN050 OVC110 25/21 A3004 RMK AO2 SLP173 CB OHD MOV SW P0004 T02500211","KMIA",c,"America/New_York");assert b is not None and b.has_convective_precip is True;d=[WeatherBucket("m1","c1","78-79°F","78-79°F","y1","n1","F",78.,79.),WeatherBucket("m2","c2","80-81°F","80-81°F","y2","n2","F",80.,81.),WeatherBucket("m3","c3","82-83°F","82-83°F","y3","n3","F",82.,83.),WeatherBucket("m4","c4","84°F or higher","84°F+","y4","n4","F",84.,float("inf"))];e=WeatherEventSpec(event_id="ev_mia",slug="miami-oct-25",series_slug="miami-daily-weather",title="Highest temperature in Miami on October 25?",icao="KMIA",city="Miami",lat=25.7959,lon=-80.287,tz_name="America/New_York",obs_date=date(2026,10,25),metric="HIGH",unit="F",fee_type="zero_fees",end_date_iso="2026-10-26T04:00:00Z",buckets=d);base_hr=int(datetime(2026,10,25,17,0,tzinfo=timezone.utc).timestamp());a={base_hr+h*3600:[27.3+(.9 if h in(2,3)else.2)+(m-30)*.02 for m in range(60)]for h in range(0,10)};f=compute_weather_probabilities(e,c,[b],a);assert f["convective_cold_pool"]is True;assert f["bias_c"]>=-.5;assert f["ensemble_member_count"]==60;assert f["probs"][0]<.35
def test_anchored_strike_regex_ignores_dates():from src.polymarket_research.multistrike_svi_scalper import _extract_threshold_strike;assert parse_strike_from_text("Will Bitcoin hit a new high on October 30, 2026?","")is None;assert parse_strike_from_text("Will Bitcoin reach 105k on October 30?","")==1.05e5;assert _extract_threshold_strike("Will Solana close higher on October 30, 2026?","October 30")is None;assert _extract_threshold_strike("Will Solana be above $105 on October 30?","$105")==105.
def test_alpha124_l2_depth_maker_queue_and_gamma_404_settlement(tmp_path,monkeypatch):
 import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124;c=a124.walk_l2_book_asks([{"price":"0.22","size":"50"}],notional_usd=50.,fee_rate=.0);assert c["filled"]is False and c["reason"]=="THIN_L1_DEPTH";a=a124.walk_l2_book_asks([{"price":"0.50","size":"60"}],notional_usd=50.,fee_rate=.0);assert a["filled"]is False and a["reason"]=="INSUFFICIENT_DEPTH";b=a124.walk_l2_book_asks([{"price":"0.50","size":"250"}],notional_usd=50.,fee_rate=.0);assert b["filled"]is True and b["fill_ratio"]==1.;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"state.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ledger.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"opps.json")
 async def _run_sim():
  d=a124.Alpha124ShadowDaemon(single_scan=True);d.spots["BTC"]=8.4e4;books={"tok_m1":{"bids":[{"price":"0.48","size":"200"}],"asks":[{"price":"0.50","size":"200"}]}}
  async def fake_fetch_json(url,timeout=5.):
   if"/book?token_id=tok_m1"in url:return books["tok_m1"]
   if"/book?token_id=tok_w1_closed"in url:return None
   if"/markets/mkt_w1"in url:return{"id":"mkt_w1","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["tok_w1_closed", "tok_w1_no"]',"outcomePrices":'["1", "0"]'}
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch_json);b=await d.post_shadow_maker_entry(sleeve="M1_SVI_MAKER_SCALP",dedupe_key="M1_test_YES",asset="BTC",title="BTC above $84,000?",side_label="YES",token_id="tok_m1",p_model=.58,close_ts=1999999999.,extra={"market_id":"m_btc","strike":8.4e4,"is_downward":False});assert b is True;assert len(d.pending_maker_orders)==1;assert len(d.open_positions)==0;c=next(iter(d.pending_maker_orders));d.pending_maker_orders[c]["created_ts"]-=15.;monkeypatch.setattr(a124,"evaluate_svi_digital_fair_value",lambda*args,**kwargs:{"p_yes":.58,"p_no":.42,"iv_annual":.45,"z_sigma":.5,"source":"TEST"});await d.manage_pending_maker_orders();assert len(d.pending_maker_orders)==1 and len(d.open_positions)==0;books["tok_m1"]={"bids":[{"price":"0.48","size":"200"}],"asks":[{"price":"0.49","size":"150"}]};await d.manage_pending_maker_orders();assert len(d.pending_maker_orders)==0 and len(d.open_positions)==1;d.open_positions["W1_test"]={"position_id":"W1_test","dedupe_key":"W1_ev_mkt_w1","sleeve":"W1_SOLAR_PEAK_LOCK","asset_or_city":"Tokyo_RJTT","title":"Tokyo 21°C","side":"YES","token_id":"tok_w1_closed","fee_rate":.0,"entry_ts":1e3,"close_ts":2e3,"p_model_entry":.92,"entry_eff_px_t1000":.8,"entry_vwap_t1000":.8,"maker_tp_px":.98,"tier_fills":{"T1000":{"spent_usd":1e2,"fee_usd":.0,"shares":125.}},"extra":{"market_id":"mkt_w1"},"status":"OPEN"};await d.manage_open_positions();assert"W1_test"not in d.open_positions;a=[p for p in d.closed_positions if p["position_id"]=="W1_test"];assert len(a)==1 and a[0]["won"]is True and a[0]["tier_pnls_usd"]["T1000"]==25.
 asyncio.run(_run_sim())
def test_live_executor_min_price_floor_zero_fees_neg_risk_and_maker_entry(tmp_path):from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;ex=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"dry.jsonl");a={"asks":[{"price":"0.25","size":"500"}],"bids":[{"price":"0.24","size":"500"}]};c=ex.execute_snipe_order(token_id="12345678901234567890",target_token="YES",notional_usd=25.,target_price=.25,trade_id="TEST_W2_ZERO_FEE",market_fee_rate=.0,market_fee_exponent=.0,min_price_floor=.15,max_price_ceiling=.65,prefetched_book=a,neg_risk=True);assert c.success is True and c.fee_usd==.0;assert ex.get_token_neg_risk("12345678901234567890")is True;b=ex.post_maker_entry_order(token_id="12345678901234567890",price=.42,notional_usd=25.,neg_risk=True);assert b["success"]is True and b["shares"]==59. and b["post_only"]is True
def test_same_oracle_dominance_box_math_equal_shares_and_strike_guard():from src.polymarket_research.same_oracle_dominance_box import(compute_dominance_box_payout_from_close,determine_dominance_legs,parse_authoritative_open_price,parse_twap_candle_event,walk_equal_shares_dominance_box);g={"title":"Ethereum Up or Down - 7:00PM-7:15PM ET","markets":[{"id":"6033093","conditionId":"0xc15","question":"Ethereum Up or Down - 7:00PM-7:15PM ET","eventStartTime":"2026-10-25T23:00:00Z","endDate":"2026-10-25T23:15:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["tok_15m_up", "tok_15m_dn"]',"feesEnabled":True,"feeSchedule":{"rate":.07,"exponent":1.},"cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"resolutionSource":"https://data.chain.link/streams/eth-usd-twap-60s-streams"}]};j={"title":"Ethereum Up or Down - 7:10PM-7:15PM ET","markets":[{"id":"6033145","conditionId":"0xc5","question":"Ethereum Up or Down - 7:10PM-7:15PM ET","eventStartTime":"2026-10-25T23:10:00Z","endDate":"2026-10-25T23:15:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["tok_5m_up", "tok_5m_dn"]',"feesEnabled":True,"feeSchedule":{"rate":.07,"exponent":1.},"cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"resolutionSource":"https://data.chain.link/streams/eth-usd-twap-60s-streams"}]};l=parse_twap_candle_event(g,"ETH","15m");m5=parse_twap_candle_event(j,"ETH","5m");assert l is not None and m5 is not None;f={"markets":[{**j["markets"][0],"cryptoMarketConfig":{"twapEnabled":False},"resolutionSource":"binance"}]};assert parse_twap_candle_event(f,"ETH","5m")is None;assert parse_authoritative_open_price({"openPrice":2393.534264,"completed":False,"cached":True})is None;assert parse_authoritative_open_price([{"closed":False,"eventMetadata":{"finalPrice":2393.534264}}])is None;assert parse_authoritative_open_price([{"closed":True,"eventMetadata":{"finalPrice":2393.534264}}])==2393.534264;k=determine_dominance_legs(l,2393.5343,m5,2392.8455);assert k is not None and k["regime"]=="5M_UP_PLUS_15M_DOWN";assert k["leg_a"]["token_id"]=="tok_5m_up"and k["leg_b"]["token_id"]=="tok_15m_dn";assert compute_dominance_box_payout_from_close(2389.55,k["k_low"],k["k_high"])==1.;assert compute_dominance_box_payout_from_close(2393.1,k["k_low"],k["k_high"])==2.;assert compute_dominance_box_payout_from_close(2399.,k["k_low"],k["k_high"])==1.;i=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.35","size":"45"}],asks_b_raw=[{"price":"0.56","size":"200"}],target_budget_usd=1e2,max_box_cost_net=.995);assert i["filled"]is True;assert i["shares"]==45;assert i["leg_a_walk"]["shares"]==45 and i["leg_b_walk"]["shares"]==45;assert i["box_cost_net"]<.95 and i["guaranteed_min_profit_usd"]>2.;h=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.52","size":"200"}],asks_b_raw=[{"price":"0.47","size":"200"}],target_budget_usd=1e2,max_box_cost_net=.995);assert h["filled"]is False;from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;d=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.90","size":"11"},{"price":"0.91","size":"138.36"}],asks_b_raw=[{"price":"0.07","size":"66.7"}],target_budget_usd=13.5,max_box_cost_net=.985,min_shares=8,min_box_notional_usd=7.);assert d["filled"]is False;assert d["reason"]=="LEG_BELOW_1USD_MIN";c=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.86","size":"11"},{"price":"0.88","size":"138.36"}],asks_b_raw=[{"price":"0.10","size":"66.7"}],target_budget_usd=13.5,max_box_cost_net=.985,min_shares=8,min_box_notional_usd=7.);assert c["filled"]is True;assert c["shares"]==11;assert c["leg_a_walk"]["worst_px"]==.86;assert c["leg_b_walk"]["worst_px"]==.1;assert c["box_cost_net"]<=.985;e=PolymarketLiveExecutor(dry_run=True);b=e.execute_atomic_dominance_box(box_id="D1_SOL_TRIM_TEST",leg_a_token_id="tok_sol_15m_up",leg_a_label="15M_UP",leg_a_limit_price=c["leg_a_walk"]["worst_px"],leg_b_token_id="tok_sol_5m_dn",leg_b_label="5M_DOWN",leg_b_limit_price=c["leg_b_walk"]["worst_px"],shares=c["shares"],max_box_cost_net=.985);assert b["success"]is True;a=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.90","size":"4"},{"price":"0.91","size":"138.36"}],asks_b_raw=[{"price":"0.07","size":"66.7"}],target_budget_usd=13.5,max_box_cost_net=.985,min_shares=8,min_box_notional_usd=7.);assert a["filled"]is False and a["reason"]=="WORST_LIMIT_COST_ABOVE_CAP"
def test_alpha124_d1_same_oracle_dominance_box_entry_and_settlement(tmp_path,monkeypatch):
 import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"state_d1.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ledger_d1.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"opps_d1.json")
 async def _sim_d1():
  d=a124.Alpha124ShadowDaemon(single_scan=True);b=1.79297e9;a=b+180.;g=TwapCandleMarketSpec(asset="ETH",horizon="15m",market_id="6033093",condition_id="0xc15",title="ETH 15m",start_iso="2026-10-25T23:00:00Z",end_iso="2026-10-25T23:15:00Z",start_ts=a-9e2,end_ts=a,up_token="tok_15m_up",down_token="tok_15m_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams");m5=TwapCandleMarketSpec(asset="ETH",horizon="5m",market_id="6033145",condition_id="0xc5",title="ETH 5m",start_iso="2026-10-25T23:10:00Z",end_iso="2026-10-25T23:15:00Z",start_ts=a-3e2,end_ts=a,up_token="tok_5m_up",down_token="tok_5m_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams");d.dominance_pairs[f"ETH_{int(a)}"]=(g,m5);prev_15m_slug=f"slug=eth-updown-5m-{int(round(g.start_ts))-300}";prev_5m_slug=f"slug=eth-updown-5m-{int(round(m5.start_ts))-300}"
  async def fake_fetch(url,timeout=5.):
   if prev_15m_slug in url:return[{"slug":url.split("slug=",1)[1],"closed":True,"eventMetadata":{"finalPrice":2390.}}]
   if prev_5m_slug in url:return[{"slug":url.split("slug=",1)[1],"closed":True,"eventMetadata":{"finalPrice":2394.}}]
   if"token_id=tok_15m_up"in url:return{"bids":[{"price":"0.52","size":"150"}],"asks":[{"price":"0.54","size":"150"}]}
   if"token_id=tok_5m_dn"in url:return{"bids":[{"price":"0.38","size":"150"}],"asks":[{"price":"0.40","size":"150"}]}
   if"token_id=tok_15m_dn"in url or"token_id=tok_5m_up"in url:return{"bids":[{"price":"0.47","size":"150"}],"asks":[{"price":"0.50","size":"150"}]}
   if"/markets/6033093"in url:return{"id":"6033093","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["tok_15m_up", "tok_15m_dn"]',"outcomePrices":'["1", "0"]'}
   if"/markets/6033145"in url:return{"id":"6033145","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["tok_5m_up", "tok_5m_dn"]',"outcomePrices":'["0", "1"]'}
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch);e=[];await d.scan_same_oracle_dominance_boxes(e,now_ts=b);assert len(d.open_positions)==1;f=next(iter(d.open_positions.values()));assert f["sleeve"]=="D1_SAME_ORACLE_DOMINANCE_BOX";assert f["entry_eff_px_t1000"]<.995;f["close_ts"]=1e3;await d.manage_open_positions();assert len(d.open_positions)==0 and len(d.closed_positions)==1;c=d.closed_positions[0];assert c["status"]=="SETTLED_DOMINANCE_DOUBLE_2X";assert c["net_payout_per_share"]==2.;assert c["tier_pnls_usd"]["T1000"]>1e2
 asyncio.run(_sim_d1())
def test_live_executor_atomic_dominance_box_and_legging_unwind(tmp_path,monkeypatch):
 from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;ex=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"box.jsonl");r_ok=ex.execute_atomic_dominance_box(box_id="BOX_ETH_1",leg_a_token_id="tok_a",leg_a_label="15M_UP",leg_a_limit_price=.54,leg_b_token_id="tok_b",leg_b_label="5M_DOWN",leg_b_limit_price=.4,shares=25,max_box_cost_net=.995,leg_a_avail_shares=120.,leg_b_avail_shares=30.);assert r_ok["success"]is True and r_ok["leg_1"]["label"]=="5M_DOWN";r_cap=ex.execute_atomic_dominance_box(box_id="BOX_EXP",leg_a_token_id="tok_a",leg_a_label="15M_UP",leg_a_limit_price=.55,leg_b_token_id="tok_b",leg_b_label="5M_DOWN",leg_b_limit_price=.44,shares=25,max_box_cost_net=.995);assert r_cap["success"]is False and"WORST_LIMIT_BOX_COST_EXCEEDS_CAP"in r_cap["error"];ex.dry_run=False;ex.is_authenticated=True
 class FakeClient:
  def __init__(self):self.posts=0
  def create_order(self,args,options=None):return{"token_id":args.token_id,"price":args.price,"size":args.size}
  def post_order(self,signed,order_type):
   self.posts+=1
   if self.posts==1:return{"orderID":"OID_LEG1_FILLED"}
   return{"errorMsg":"FOK order couldn't be fully filled"}
 ex.client=FakeClient();monkeypatch.setattr(ex,"get_token_tick_size",lambda tid:.01);monkeypatch.setattr(ex,"get_token_neg_risk",lambda tid,explicit_neg_risk=None:False);unwind_calls=[]
 def fake_unwind(token_id,size,side="SELL",min_price=.01,neg_risk=None):unwind_calls.append((token_id,size,side,min_price));return{"success":True,"orderID":"OID_UNWIND_1","matched_size":size}
 monkeypatch.setattr(ex,"execute_unwind_order",fake_unwind);r_leg=ex.execute_atomic_dominance_box(box_id="BOX_LEG_FAIL",leg_a_token_id="tok_a",leg_a_label="15M_UP",leg_a_limit_price=.54,leg_b_token_id="tok_b",leg_b_label="5M_DOWN",leg_b_limit_price=.4,shares=20,max_box_cost_net=.995,leg_a_avail_shares=25.,leg_b_avail_shares=1e2);assert r_leg["success"]is False;assert r_leg["stage"]=="LEG_2_REJECTED_UNWOUND";assert r_leg["legged_out"]is True;assert len(unwind_calls)==1 and unwind_calls[0][0]=="tok_a"and unwind_calls[0][1]==20.
def test_exact_twap_lock_engine_math_and_whipsaw_guard():import math;from src.polymarket_research.exact_twap_lock_engine import(compute_exact_twap_lock_probability,student_t_df5_cdf);assert abs(student_t_df5_cdf(.0)-.5)<1e-12;assert abs(student_t_df5_cdf(2.5)+student_t_df5_cdf(-2.5)-1.)<1e-12;a=.5*(1.+math.erf(3./math.sqrt(2.)));assert.96<student_t_df5_cdf(3.)<a;end_ts=1792970300.;d=end_ts-18.;c=[(end_ts-60.+i,2404.5)for i in range(43)];f=compute_exact_twap_lock_probability(asset="ETH",open_price=2400.123456789012,current_usd_spot=2404.6,rem_seconds=18.,now_ts=d,end_ts=end_ts,spot_samples=c,iv_annual=.65,usd_direct_feed=True);assert f["eligible"]is True;assert f["side"]=="UP";assert f["eff_alpha"]>.65;assert f["p_lock"]>=.975;b=compute_exact_twap_lock_probability(asset="ETH",open_price=2400.123456789012,current_usd_spot=2399.5,rem_seconds=18.,now_ts=d,end_ts=end_ts,spot_samples=c,iv_annual=.65,usd_direct_feed=True);assert b["eligible"]is False and b["reason"]=="WHIPSAW_SPLIT_ACROSS_STRIKE";e=compute_exact_twap_lock_probability(asset="ETH",open_price=2400.,current_usd_spot=2405.,rem_seconds=52.,now_ts=end_ts-52.,end_ts=end_ts,spot_samples=[]);assert e["eligible"]is False
def test_r01_relayer_hmac_deposit_wallet_eip712_and_negrisk_payout_logs(tmp_path):
 from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;h=PolymarketLiveExecutor.build_relayer_builder_headers(api_key="test-api-key",secret="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",passphrase="test-passphrase",method="POST",request_path="/orders",body={"hash":"0x123"},timestamp=1000000);assert h["POLY_BUILDER_SIGNATURE"]=="wdXSC4akzPKG0yFk9FJrIb7-rg73v_M7QDxIBp-P1CQ=";assert h["POLY_BUILDER_TIMESTAMP"]=="1000000"
 try:from py_clob_client.signing.hmac import build_hmac_signature;assert h["POLY_BUILDER_SIGNATURE"]==build_hmac_signature("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=","1000000","POST","/orders",{"hash":"0x123"})
 except ImportError:pass
 ex=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"r01.jsonl");ex.funder_address="0x013A2474454fBd8738cff6a7f204eF1bc377F4e9";d="0x"+"ab"*32;a="0x"+ex.funder_address.lower().replace("0x","").rjust(64,"0")
 try:import eth_account;import eth_utils;import web3;c="0x"+"11"*32;g=PolymarketLiveExecutor.build_deposit_wallet_relayer_batch(private_key=c,wallet_address=ex.funder_address,nonce=7,deadline=1900000000,calls=[{"target":PolymarketLiveExecutor.CTF_ADDRESS,"value":"0","data":"0x12345678"}],chain_id=137);assert g["type"]=="WALLET";assert g["nonce"]=="7";assert g["signature"].startswith("0x")and len(g["signature"])==132;assert g["depositWalletParams"]["depositWallet"].lower()==ex.funder_address.lower();b={"address":PolymarketLiveExecutor.CTF_ADDRESS,"topics":[PolymarketLiveExecutor._payout_redemption_topic(),a,"0x"+"00"*32],"data":"0x"+"ab"*32+"00"*32+f"{25500000:064x}","transactionHash":"0xtx_ctf","blockNumber":"0x100"};f={"address":PolymarketLiveExecutor.NEG_RISK_ADAPTER_ADDRESS,"topics":[PolymarketLiveExecutor._neg_risk_payout_redemption_topic(),a,d],"data":"0x"+"00"*32+f"{42250000:064x}","transactionHash":"0xtx_nr","blockNumber":"0x101"};e=ex.parse_payout_redemption_logs([b,f],d);assert len(e)==2;assert abs(e[0]["payout_usd"]-25.5)<1e-6;assert abs(e[1]["payout_usd"]-42.25)<1e-6
 except ImportError:pass
def test_alpha124_w2_maker_overround_m4_shock_wakeup_and_s2_twap_lock(tmp_path,monkeypatch):
 import asyncio;import json;import time;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.multistrike_svi_scalper import StrikeRungSpec;from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"state_all.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ledger_all.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"opps_all.json");shock_file=tmp_path/"live_shock_triggers.jsonl";shock_file.write_text("",encoding="utf-8");monkeypatch.setattr(a124,"SHOCK_TRIGGER_FILE",shock_file)
 async def _sim_new_sleeves():
  d=a124.Alpha124ShadowDaemon(single_scan=True);g=time.time();books={"tok_w2m":{"bids":[{"price":"0.26","size":"150"}],"asks":[{"price":"0.30","size":"150"}]},"tok_m1_yes":{"bids":[{"price":"0.49","size":"200"}],"asks":[{"price":"0.51","size":"200"}]},"tok_m4_no":{"bids":[{"price":"0.46","size":"250"}],"asks":[{"price":"0.48","size":"250"}]},"tok_s2_up":{"bids":[{"price":"0.86","size":"250"}],"asks":[{"price":"0.88","size":"250"}]}}
  async def fake_fetch(url,timeout=5.):
   for a,bk in books.items():
    if f"token_id={a}"in url:return bk
   if"slug=eth-updown-5m-1792969800"in url:return[{"slug":url.split("slug=",1)[1],"closed":True,"eventMetadata":{"finalPrice":2405.8}}]
   if"slug=eth-updown-5m-"in url:return[{"slug":url.split("slug=",1)[1],"closed":True,"eventMetadata":{"finalPrice":2400.123456789012}}]
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch);m=await d.post_shadow_maker_entry(sleeve="W2_MAKER_OVERROUND",dedupe_key="W2M_ev1_m1",asset="Miami_KMIA",title="Miami 82-83°F",side_label="YES",token_id="tok_w2m",p_model=.4,close_ts=g+28800.,extra={"event_id":"ev1","market_id":"m1","icao":"KMIA","obs_date":"2026-10-25"});assert m is True;f=next(iter(d.pending_maker_orders));assert d.pending_maker_orders[f]["resting_bid"]==.27;d.pending_maker_orders[f]["created_ts"]-=15.;books["tok_w2m"]={"bids":[{"price":"0.26","size":"150"}],"asks":[{"price":"0.27","size":"150"}]};await d.manage_pending_maker_orders();assert any(p["sleeve"]=="W2_MAKER_OVERROUND"for p in d.open_positions.values());d.spots["BTC"]=8.4e4;await d.post_shadow_maker_entry(sleeve="M1_SVI_MAKER_SCALP",dedupe_key="M1_btc_84k_YES",asset="BTC",title="BTC above $84,000?",side_label="YES",token_id="tok_m1_yes",p_model=.58,close_ts=g+43200.,extra={"market_id":"m_btc_84k","strike":8.4e4,"is_downward":False});assert len(d.pending_maker_orders)==1;d.strike_ladders["BTC_ev"]=[StrikeRungSpec(asset="BTC",series_slug="btc-multi-strikes",event_id="ev_btc",market_id="m_btc_84k",condition_id="0xc_btc",title="Bitcoin above ___ on Oct 25?",question="Bitcoin above $84,000 on Oct 25?",strike=8.4e4,is_downward=False,end_ts=g+43200.,yes_token="tok_m1_yes",no_token="tok_m4_no")];monkeypatch.setattr(a124,"evaluate_svi_digital_fair_value",lambda*args,**kwargs:{"p_yes":.38,"p_no":.62,"iv_annual":.45,"z_sigma":.8,"source":"TEST"});a={"shock_id":"SHK_BTC_1","t0_unix":time.time(),"shock_source":"FUTURES","asset":"BTC","shock_direction":"SELL","shock_ofi":-.88,"shock_volume_100ms":3.2e6,"spot_at_t0":83700.}
  with open(shock_file,"a",encoding="utf-8")as sf:sf.write(json.dumps(a)+"\n")
  l=d.poll_fresh_shock_triggers();assert len(l)==1;k=[];await d.handle_shock_triggers(l,k);assert len(d.pending_maker_orders)==0;assert any(p["sleeve"]=="M4_SHOCK_STRIKE_CATCHUP"and p["side"]=="NO"for p in d.open_positions.values());j=g+18.;n=TwapCandleMarketSpec(asset="ETH",horizon="5m",market_id="6055555",condition_id="0xc_s2",title="ETH Up or Down 5m",start_iso="2026-10-25T23:10:00Z",end_iso="2026-10-25T23:15:00Z",start_ts=j-3e2,end_ts=j,up_token="tok_s2_up",down_token="tok_s2_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/eth-usd-twap-60s-streams");d.twap_candles[f"ETH_5m_{int(j)}"]=n;d.spots["ETH"]=2406.;d.usd_direct_flags["ETH"]=True
  for i in range(43):d.usd_spot_hist["ETH"].append((j-60.+i,2405.8))
  monkeypatch.setattr(a124,"get_wing_implied_vol",lambda*args,**kwargs:(.65,"TEST"));e=[];await d.scan_exact_twap_locks(e,now_ts=g);b=[p for p in d.open_positions.values()if p["sleeve"]=="S2_EXACT_TWAP_LOCK"];assert len(b)==1;h=b[0];assert h["side"]=="UP"and h["p_model_entry"]>=.97;h["close_ts"]=g-2e2;await d.manage_open_positions();c=[p for p in d.closed_positions if p["sleeve"]=="S2_EXACT_TWAP_LOCK"];assert len(c)==1 and c[0]["won"]is True;assert c[0]["status"]=="SETTLED_ORACLE_TWAP_WIN"
 asyncio.run(_sim_new_sleeves())
def test_live_daily_projections_working_capital_and_monotonicity():
 from scripts.polymarket_daily_projections import(_depth_decay,build_live_projections,compute_v393_ticket_size);assert compute_v393_ticket_size(60.)==12.;assert compute_v393_ticket_size(73.01)==13.14;assert compute_v393_ticket_size(76.8)==13.82;assert compute_v393_ticket_size(95.)==17.1;assert compute_v393_ticket_size(120.)==26.4;assert _depth_decay(15.)==1.;assert.58<=_depth_decay(150.)<.85;proj=build_live_projections(days=30,fallback_equity=76.8);b=proj["day_by_day_schedule"];assert len(b)==30;quarantined_check={"B1_CONVEX_TAIL_YES","M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","SLEEVE_XRP_V392_SHADOW"};assert all(g["sleeve"]not in quarantined_check for g in proj["sleeve_graduation_live_tracker"])
 for r in b:
  assert r["p25_end_equity_usd"]<r["p50_end_equity_usd"]<r["p75_end_equity_usd"];assert r["p50_daily_pnl_usd"]>0
  for a in("B1_convex_barrier_tails","W2_weather_maker_and_mos","M1_M4_svi_maker_and_shock"):assert a not in r["p50_sleeve_pnl_breakdown_usd"]
def test_external_dual_audit_alpha124_and_oracle_regressions(tmp_path,monkeypatch):
 import asyncio;import json;import time;from datetime import date;from zoneinfo import ZoneInfo;import src.polymarket_research.alpha_124_shadow_daemon as a124;import src.polymarket_research.barrier_onetouch_svi_engine as b_eng;import src.polymarket_research.exact_twap_lock_engine as etwap;from src.polymarket_research.same_oracle_dominance_box import(TwapCandleMarketSpec,verify_same_oracle_pair);from src.polymarket_research.weather_metar_engine import(WeatherBucket,WeatherEventSpec,compute_weather_probabilities,parse_weather_event);C=datetime(2026,10,25,16,0,tzinfo=timezone.utc);k=parse_metar_line("METAR RJTT 250600Z 08007KT 9999 FEW020 02/// Q1017 RMK AO2 T0023////","RJTT",C,"Asia/Tokyo");assert k is not None and k.has_t_remark is True and abs(k.temp_c-2.3)<1e-6;j=parse_metar_line("METAR KORD 251051Z 29012KT 10SM CLR M02/// A3015 RMK AO2 T1017//// SLP210","KORD",C,"America/Chicago");assert j is not None and j.has_t_remark is True and abs(j.temp_c-(-1.7))<1e-6;B=parse_metar_line("METAR COR RJTT 250600Z 08007KT 9999 FEW020 19/12 Q1017 RMK AO2 T01940120","RJTT",C,"Asia/Tokyo");assert B is not None and B.is_corrected is True and abs(B.temp_c-19.4)<1e-6;A=ZoneInfo("America/New_York");s=parse_metar_line("METAR KLGA 260251Z 31012KT 10SM CLR 15/06 A3012 RMK AO2 T01500061","KLGA",datetime(2026,10,26,3,0,tzinfo=timezone.utc),"America/New_York");assert s is not None and s.local_dt.date()==date(2026,10,25);i=[WeatherBucket("b1","c1","14°C or below","14°C-","y1","n1","C",float("-inf"),14.),WeatherBucket("b2","c2","15°C","15°C","y2","n2","C",15.,15.),WeatherBucket("b3","c3","16°C","16°C","y3","n3","C",16.,16.),WeatherBucket("b4","c4","17°C or higher","17°C+","y4","n4","C",17.,float("inf"))];r=WeatherEventSpec(event_id="ev_klga_low",slug="nyc-low",series_slug="nyc-daily-weather",title="Lowest temperature in NYC on October 25?",icao="KLGA",city="NYC",lat=40.7769,lon=-73.874,tz_name="America/New_York",obs_date=date(2026,10,25),metric="LOW",unit="C",fee_type="zero_fees",end_date_iso="2026-10-26T05:00:00Z",buckets=i);g=datetime(2026,10,25,23,30,tzinfo=A).astimezone(timezone.utc);f=int(datetime(2026,10,26,0,0,tzinfo=A).astimezone(timezone.utc).timestamp());e={f:[12.]*30};q=compute_weather_probabilities(r,g,[s],e);assert q["rem_hours_count"]==1;assert q["probs"][0]>.5;h=datetime(2026,10,26,0,5,tzinfo=A).astimezone(timezone.utc);c=compute_weather_probabilities(r,h,[s],e);assert c["probs"][1]>.99;m={"id":"ev_fee_test","title":"Highest temperature in Tokyo on October 26?","endDate":"2026-10-26T15:00:00Z","markets":[{"id":f"m_{idx}","conditionId":f"0xc_{idx}","groupItemTitle":lbl,"description":"Resolves via https://aviationweather.gov/api/data/metar?ids=RJTT excluding SPECI on 26 Oct '26.","clobTokenIds":f'["y_{idx}", "n_{idx}"]',"feesEnabled":True,"feeSchedule":{"rate":.05,"exponent":1.}}for idx,lbl in enumerate(["18°C or below","19°C","20°C","21°C or higher"])]};parsed_fee_ev=parse_weather_event(m);assert parsed_fee_ev is not None and parsed_fee_ev.fee_type=="fees_enabled";assert all(abs(b.fee_rate-.05)<1e-9 for b in parsed_fee_ev.buckets);monkeypatch.setattr(etwap,"SHM_DIR",tmp_path);z=1792975000.;w=tmp_path/"pm_fast_tick_BTC.json";w.write_text(json.dumps({"timestamp_unix":z,"spot_price":84100.}),encoding="utf-8");assert etwap.read_shm_usd_anchor("BTC",z)["usd_spot"]is None;w.write_text(json.dumps({"timestamp_unix":z+4.,"chainlink_proxy_spot":84050.}),encoding="utf-8");assert etwap.read_shm_usd_anchor("BTC",z)["usd_spot"]is None;w.write_text(json.dumps({"timestamp_unix":z-.5,"chainlink_proxy_spot":84050.}),encoding="utf-8");assert etwap.read_shm_usd_anchor("BTC",z)["usd_spot"]==84050.;y=z+30.;v=etwap.compute_exact_twap_lock_probability(asset="ETH",open_price=2400.,current_usd_spot=2403.,rem_seconds=30.,now_ts=z,end_ts=y,spot_samples=[],shm_twap_60s=2415.,usd_direct_feed=True);assert v["eff_alpha"]==.0;l=TwapCandleMarketSpec("ETH","15m","1","0x1","ETH 15m","2026-10-25T23:00:00Z","2026-10-25T23:15:00Z",1e2,1e3,"u1","d1",.07,1.,False,60,"");o=TwapCandleMarketSpec("ETH","5m","2","0x2","ETH 5m","2026-10-25T23:10:00Z","2026-10-25T23:15:00Z",7e2,1e3,"u2","d2",.07,1.,False,60,"");assert verify_same_oracle_pair(l,o)is False;st_mid_hr=1792931400.;en_48h=st_mid_hr+48*3600.
 def fake_klines(sym,st_ms,en_ms,interval,timeout):
  if interval=="1m"and st_ms==int(st_mid_hr*1000):return[[st_ms,"84000","89500","83900","84100","10",st_ms+60000]]
  return[[int((st_mid_hr+3600)*1000),"84100","85000","83500","84200","100",int(en_48h*1000)]]
 monkeypatch.setattr(b_eng,"_fetch_finalized_klines",fake_klines);u=b_eng.fetch_binance_window_extremes_sync("BTC",st_mid_hr,en_48h,"1m");assert u is not None and u[0]==89500.;t=tmp_path/"a124_race_state.json";n=tmp_path/"a124_race_ledger.jsonl";x=tmp_path/"a124_race_opps.json";n.write_text('{"event": "SHADOW_ENTRY", "corrupt_json": \n'+json.dumps({"event":"SHADOW_ENTRY","position_id":"S2_VALID_HYDRATE","dedupe_key":"S2_BTC_5m_1","sleeve":"S2_EXACT_TWAP_LOCK","asset_or_city":"BTC","title":"BTC 5m","side":"UP","token_id":"tok_h","fee_rate":.07,"entry_ts":1e3,"close_ts":2e3,"tier_fills":{"T1000":{"spent_usd":1e2,"fee_usd":.5,"shares":115.}},"extra":{},"status":"OPEN"})+"\n",encoding="utf-8");monkeypatch.setattr(a124,"STATE_FILE",t);monkeypatch.setattr(a124,"LEDGER_FILE",n);monkeypatch.setattr(a124,"OPPS_FILE",x)
 async def _sim_concurrency_and_adverse_fill():
  d=a124.Alpha124ShadowDaemon(single_scan=True);assert"S2_VALID_HYDRATE"in d.open_positions;books={"tok_race":{"bids":[{"price":"0.84","size":"300"}],"asks":[{"price":"0.85","size":"300"}]},"tok_adv":{"bids":[{"price":"0.49","size":"200"}],"asks":[{"price":"0.51","size":"200"}]}}
  async def fake_fetch(url,timeout=5.):
   await asyncio.sleep(.01)
   for a,bk in books.items():
    if f"token_id={a}"in url:return bk
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch);r1,r2=await asyncio.gather(d.open_shadow_position("W1_SOLAR_PEAK_LOCK","W1_RACE_KEY","Tokyo_RJTT","Tokyo 20°C","YES","tok_race",.0,.94,time.time()+7200.,{"event_id":"ev_r"}),d.open_shadow_position("W1_SOLAR_PEAK_LOCK","W1_RACE_KEY","Tokyo_RJTT","Tokyo 20°C","YES","tok_race",.0,.94,time.time()+7200.,{"event_id":"ev_r"}));assert(r1,r2)in((True,False),(False,True));assert sum(1 for p in d.open_positions.values()if p.get("dedupe_key")=="W1_RACE_KEY")==1;d.spots["BTC"]=8.4e4;c=await d.post_shadow_maker_entry("M1_SVI_MAKER_SCALP","M1_ADV_RACE","BTC","BTC > 84k","YES","tok_adv",.58,time.time()+43200.,{"market_id":"m_adv","strike":8.4e4,"is_downward":False});assert c is True;b=next(iter(d.pending_maker_orders));d.pending_maker_orders[b]["created_ts"]-=2.;d.spots["BTC"]=83650.;books["tok_adv"]={"bids":[{"price":"0.48","size":"200"}],"asks":[{"price":"0.49","size":"250"}]};monkeypatch.setattr(a124,"evaluate_svi_digital_fair_value",lambda*a,**kw:{"p_yes":.36,"p_no":.64,"iv_annual":.45,"z_sigma":.9,"source":"TEST"});await d.manage_pending_maker_orders();a=[p for p in d.open_positions.values()if p.get("dedupe_key")=="M1_ADV_RACE"];assert len(a)==1 and a[0]["extra"].get("adverse_fill_during_cancel_window")is True
 asyncio.run(_sim_concurrency_and_adverse_fill())
def test_v40_profit_maximization_upgrades(tmp_path,monkeypatch):
 import asyncio;import time;from datetime import date;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.net_alpha_opportunity_engine import(estimate_quote_survival_and_net_alpha,evaluate_cross_oracle_basis_box_ev,evaluate_optimal_stopping_exit,fit_quote_survival_from_ledger,inspect_microstructure_feature_completeness,publish_global_positions_shm,rank_opportunities_capital_auction,read_global_positions_shm,scan_binary_complete_set_arb,select_maker_taker_skip_route);from src.polymarket_research.deribit_svi_surface import(DeribitSVISurfaceEngine,SVIParams,enforce_monotone_ladder_probabilities);from src.polymarket_research.multistrike_svi_scalper import(StrikeRungSpec,evaluate_coherent_strike_ladder);from src.polymarket_research.barrier_onetouch_svi_engine import(evaluate_barrier_no_net_ev,first_passage_touch_prob);from src.polymarket_research.weather_metar_engine import(WeatherBucket,WeatherEventSpec,compute_adaptive_metar_poll_ttl,evaluate_weather_event_slate,parse_taf_temperature_extremes,verify_weather_slate_partition);b="100434764618174237135201777197981253576172734064131101154122934005557319214073";t=inspect_microstructure_feature_completeness({"fee_metadata":{"fee_rate_market":.07},"shock_ofi":.9,"pre_shock_features_t0":{"UP":{"token_id":b,"age_ask_ms":None,"obi_l1":.2}}},"UP",b);assert t["hard_veto_live"]is True and"age_ask_ms"in t["missing_fields"];s=inspect_microstructure_feature_completeness({"fee_metadata":{"fee_rate_market":.07},"shock_ofi":None,"pre_shock_features_t0":{"UP":{"token_id":b,"age_ask_ms":180.,"obi_l1":.2}}},"UP",b);assert s["hard_veto_live"]is True and"shock_ofi"in s["missing_fields"];i=estimate_quote_survival_and_net_alpha(p_win=.9,ask_price=.74,limit_price=.74,p_max=.8,clob_rtt_ms=260.,age_ask_ms=280.);h=estimate_quote_survival_and_net_alpha(p_win=.9,ask_price=.74,limit_price=.76,p_max=.8,clob_rtt_ms=260.,age_ask_ms=280.);assert h["p_fill"]>i["p_fill"];assert h["eff_limit_px"]==.76<=.8;assert h["eligible"]is True and h["ev_net_usd"]>.0;B=fit_quote_survival_from_ledger([{"mode":"LIVE_CLOB","success":True,"latency_ms":210.},{"mode":"LIVE_CLOB","success":True,"latency_ms":225.},{"mode":"FAK_KILLED_NO_MATCH","success":False,"latency_ms":280.},{"mode":"LIVE_CLOB","success":True,"latency_ms":195.},{"mode":"FAK_KILLED_NO_MATCH","success":False,"latency_ms":265.}]);assert B["sample_count"]==5 and abs(B["empirical_fill_rate"]-.6)<1e-6;r=select_maker_taker_skip_route(p_win=.92,best_bid=.73,best_ask=.74,p_max=.81,clob_rtt_ms=190.);assert r["route"]=="TAKER_PRICE_IMPROVED_FAK"and r["taker_limit_px"]==.76;q=select_maker_taker_skip_route(p_win=.77,best_bid=.69,best_ask=.75,p_max=.74,clob_rtt_ms=280.);assert q["route"]=="MAKER_POST_ONLY_3P5S"and q["maker_bid_px"]==.7;y=select_maker_taker_skip_route(p_win=.6,best_bid=.68,best_ask=.7,p_max=.58);assert y["route"]=="SKIP";x=evaluate_optimal_stopping_exit(entry_px=.74,rem_shares=18.,best_bid=.99,best_ask=1.,curr_target_px=.99,tte_sec=15.);assert x["action"]=="PRE_EXPIRY_99C_RECYCLE"and x["taker_fee_ps"]<.001;o=evaluate_optimal_stopping_exit(entry_px=.7,rem_shares=18.,best_bid=.84,best_ask=.93,curr_target_px=.95,tte_sec=30.,opp_ask_complement=.09);assert o["action"]=="SYNTHETIC_COMPLEMENT_MERGE"and o["net_proceeds_ps"]>.9;w=evaluate_optimal_stopping_exit(entry_px=.74,rem_shares=18.,best_bid=.92,best_ask=.95,curr_target_px=.95,tte_sec=90.,obi_l1=-.65,v_spot_15s_pct=-.02);assert w["action"]=="OBI_MAKER_STEP_DOWN"and w["target_px"]==.93;c1=scan_binary_complete_set_arb(market_id="m_c1",condition_id="0xc1",yes_token="tok_y_c1",no_token="tok_n_c1",asks_yes_raw=[{"price":"0.47","size":"60"}],asks_no_raw=[{"price":"0.48","size":"60"}],target_budget_usd=30.,fee_rate=.07,max_complete_set_cost=.994);assert c1["filled"]is True and c1["box_cost_net"]<.994 and c1["guaranteed_min_profit_usd"]>.0;l=evaluate_cross_oracle_basis_box_ev(spot_px=84100.,k_low=8.4e4,k_high=84200.,c_taker_net=.975,tte_sec=6e2);assert l["classification"]=="PROBABILISTIC_CROSS_ORACLE_RV"and l["is_riskless"]is False;monkeypatch.setenv("PM_FAST_TICK_DIR",str(tmp_path));now_bus=time.time();assert publish_global_positions_shm("live_harvester",[{"trade_id":"T1","sleeve":"LIVE","asset":"BTC","target_token":"UP","candle_open_spot":8.4e4,"candle_expiry_ts":now_bus+6e2,"notional_usd":14.}])is True;g=read_global_positions_shm();j=g["daemons"]["live_harvester"]["positions"];assert len(j)==1 and j[0]["asset"]=="BTC";v=rank_opportunities_capital_auction([{"sleeve":"W2","asset":"NYC","side":"YES","ask_vwap":.5,"net_edge":.05,"tte_sec":3.6e4,"expiry_ts":now_bus+3.6e4},{"sleeve":"S2","asset":"BTC","side":"DOWN","strike":84250.,"ask_vwap":.85,"net_edge":.04,"tte_sec":3e2,"expiry_ts":now_bus+6e2}],active_global_positions=j);assert v[0]["sleeve"]=="S2"and v[0].get("synthetic_corridor_completion")is True;A=DeribitSVISurfaceEngine();A._cache["BTC"]=SVIParams(a=4e-4,b=2e-4,rho=-.15,m=.0,sigma=.05,t_years=30./365.25,forward_price=8.6e4,index_price=8.4e4,calibrated_at=time.time());assert A._cache["BTC"].implied_forward_drift_rate()>.15;n=A.evaluate_strike_probability("BTC",spot=8.4e4,strike=8.5e4,tte_seconds=14*86400.,allow_sync_fetch=False);A._cache["BTC"].index_price=8.6e4;u=A.evaluate_strike_probability("BTC",spot=8.4e4,strike=8.5e4,tte_seconds=14*86400.,allow_sync_fetch=False);assert n["p_above_strike"]>u["p_above_strike"];mono=enforce_monotone_ladder_probabilities([(8e4,.72),(8.2e4,.55),(8.4e4,.61),(8.6e4,.3)]);assert mono["probs"]==sorted(mono["probs"],reverse=True);assert all(iv>=.0 for iv in mono["interval_probs"])and mono["max_adjustment"]>.0;e=[StrikeRungSpec("ev1","btc-daily","BTC","BTC Daily",f"m_{k}",f"0x{k}",f"BTC > {k}",float(k),False,now_bus+7200.,f"ty_{k}",f"tn_{k}")for k in(82000,84000,86000)];z=evaluate_coherent_strike_ladder("BTC",8.4e4,e,7200.,now_ts=now_bus);assert z["probs"][0]>=z["probs"][1]>=z["probs"][2];m=first_passage_touch_prob(8.4e4,8.8e4,86400.,.5,"UP",realized_vol_ratio=1.,forward_drift_annual=.0);f=first_passage_touch_prob(8.4e4,8.8e4,86400.,.5,"UP",realized_vol_ratio=2.2,forward_drift_annual=.12);assert f>m;assert evaluate_barrier_no_net_ev(p_touch=.04,ask_no=.88)["eligible"]is True;assert evaluate_barrier_no_net_ev(p_touch=.01,ask_no=.95)["eligible"]is False;assert compute_adaptive_metar_poll_ttl("KLGA",None,datetime(2026,10,26,14,52,tzinfo=timezone.utc))==10.;assert compute_adaptive_metar_poll_ttl("KLGA",None,datetime(2026,10,26,14,25,tzinfo=timezone.utc))==3e2;c=parse_taf_temperature_extremes("TAF KLGA 261130Z 2612/2718 30012KT P6SM FEW050 TX19/2619Z TNM02/2710Z","KLGA",datetime(2026,10,26,12,0,tzinfo=timezone.utc),"America/New_York");assert c[date(2026,10,26)]["HIGH"]==19.;assert c[date(2026,10,27)]["LOW"]==-2.;w_spec=WeatherEventSpec(event_id="ev_w3",slug="tokyo-w3",series_slug="tokyo-daily-weather",title="Highest temperature in Tokyo on October 26?",icao="RJTT",city="Tokyo",lat=35.5494,lon=139.7798,tz_name="Asia/Tokyo",obs_date=date(2026,10,26),metric="HIGH",unit="C",fee_type="zero_fees",end_date_iso="2026-10-26T20:00:00Z",buckets=[WeatherBucket("wb1","0xwb1","18°C or below","18°C or below","wy1","wn1","C",float("-inf"),18.),WeatherBucket("wb2","0xwb2","19°C","19°C","wy2","wn2","C",19.,19.),WeatherBucket("wb3","0xwb3","20°C or higher","20°C or higher","wy3","wn3","C",20.,float("inf"))]);assert verify_weather_slate_partition(w_spec)is True
 slate_eval=evaluate_weather_event_slate(w_spec,[.2,.5,.3],{"wb1":{"ask_yes":.19,"ask_yes_shares":40.},"wb2":{"ask_yes":.46,"ask_yes_shares":40.},"wb3":{"ask_yes":.31,"ask_yes_shares":40.}},target_budget_usd=10.);assert slate_eval["full_slate_arb"]is not None;assert abs(slate_eval["full_slate_arb"]["sum_asks"]-.96)<1e-6
 async def _sim_v40_sleeves():
  monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"a124_v40_state.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"a124_v40_ledger.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"a124_v40_opps.json");d=a124.Alpha124ShadowDaemon(single_scan=True);d.spots["BTC"]=84500.;books_v40={"tok_c1_y":{"bids":[{"price":"0.46","size":"80"}],"asks":[{"price":"0.47","size":"80"}]},"tok_c1_n":{"bids":[{"price":"0.47","size":"80"}],"asks":[{"price":"0.48","size":"80"}]},"tok_m3_lo":{"bids":[{"price":"0.52","size":"80"}],"asks":[{"price":"0.53","size":"80"}]},"tok_m3_hi":{"bids":[{"price":"0.41","size":"80"}],"asks":[{"price":"0.42","size":"80"}]},"tok_m4_mkr":{"bids":[{"price":"0.50","size":"60"}],"asks":[{"price":"0.54","size":"60"}]}}
  async def fake_fetch_v40(url,timeout=5.):
   if"/book?token_id="in url:return books_v40.get(url.split("token_id=")[1])
   if"/markets/m_c1"in url:return{"closed":True,"outcomePrices":'["1", "0"]'}
   if"/markets/m_lo"in url:return{"closed":True,"outcomePrices":'["1", "0"]'}
   if"/markets/m_hi"in url:return{"closed":True,"outcomePrices":'["0", "1"]'}
   if"/markets/wb2"in url:return{"closed":True,"outcomePrices":'["1", "0"]'}
   if"/markets/wb1"in url or"/markets/wb3"in url:return{"closed":True,"outcomePrices":'["0", "1"]'}
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch_v40);g=await d.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key="C1_TEST_1",asset="BTC",title="BTC > 84k [YES+NO Complete Set]",leg_a={"token_id":"tok_c1_y","side":"YES","market_id":"m_c1","fee_rate":.07},leg_b={"token_id":"tok_c1_n","side":"NO","market_id":"m_c1","fee_rate":.07},bk_a=books_v40["tok_c1_y"],bk_b=books_v40["tok_c1_n"],close_ts=time.time()-60.,max_box_cost_net=.994,extra={"market_id":"m_c1"});f=await d.open_shadow_two_leg_box(sleeve="M3_LADDER_MONO_BOX",dedupe_key="M3_TEST_1",asset="BTC",title="BTC Ladder Box [84000..85000]",leg_a={"token_id":"tok_m3_lo","side":"YES","market_id":"m_lo","fee_rate":.07},leg_b={"token_id":"tok_m3_hi","side":"NO","market_id":"m_hi","fee_rate":.07},bk_a=books_v40["tok_m3_lo"],bk_b=books_v40["tok_m3_hi"],close_ts=time.time()-60.,max_box_cost_net=.995,extra={"low_market_id":"m_lo","high_market_id":"m_hi","low_strike":8.4e4,"high_strike":8.5e4});e=await d.open_shadow_weather_slate(w_spec,slate_eval["full_slate_arb"],close_ts=time.time()-60.);assert g is True and f is True and e is True;await d.manage_open_positions();c={p["sleeve"]:p for p in d.closed_positions};assert c["C1_BINARY_COMPLETE_SET"]["won"]is True and c["C1_BINARY_COMPLETE_SET"]["tier_pnls_usd"]["T1000"]>.0;assert c["M3_LADDER_MONO_BOX"]["won"]is True and c["M3_LADDER_MONO_BOX"]["status"]=="SETTLED_DOMINANCE_DOUBLE_2X";assert c["W3_WEATHER_SLATE_ARB"]["won"]is True and c["W3_WEATHER_SLATE_ARB"]["tier_pnls_usd"]["T1000"]>.0;b=await d.post_shadow_maker_entry(sleeve="M4_SHOCK_STRIKE_CATCHUP",dedupe_key="M4MKR_TEST",asset="BTC",title="BTC > 84500",side_label="YES",token_id="tok_m4_mkr",p_model=.62,close_ts=time.time()+7200.,extra={"market_id":"m_m4","strike":84500.,"is_downward":False},prefetched_book=books_v40["tok_m4_mkr"],ttl_override_sec=3.5);assert b is True;a=next(iter(d.pending_maker_orders));d.pending_maker_orders[a]["created_ts"]-=1.2;books_v40["tok_m4_mkr"]={"bids":[{"price":"0.50","size":"60"}],"asks":[{"price":"0.51","size":"80"}]};monkeypatch.setattr(a124,"evaluate_svi_digital_fair_value",lambda*a,**kw:{"p_yes":.62,"p_no":.38,"iv_annual":.45,"z_sigma":.5,"source":"TEST"});await d.manage_pending_maker_orders();assert any(p["sleeve"]=="M4_SHOCK_STRIKE_CATCHUP"for p in d.open_positions.values());d.write_state_files([{"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","ask_vwap":.98,"net_edge":.02,"tte_sec":180.}]);assert"alpha124_shadow"in read_global_positions_shm()["daemons"]
 asyncio.run(_sim_v40_sleeves())
def test_v42_seven_new_shadow_additions_and_quarantine(tmp_path,monkeypatch):
 import asyncio;import time;from src.polymarket_research import alpha_124_shadow_daemon as a124;from src.polymarket_research.multistrike_svi_scalper import(build_negrisk_cross_box_bundles,parse_daily_updown_event,parse_multistrike_event,parse_negrisk_bracket_event);from src.polymarket_research.same_oracle_dominance_box import(build_crypto_price_query_url,determine_dominance_legs,parse_twap_candle_event,verify_same_oracle_pair,walk_equal_shares_multi_leg_box);from src.polymarket_research.weather_metar_engine import HIGH_VOLUME_WEATHER_SERIES,parse_weather_event;monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","1")
 for w in("M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","S5M_CHAINLINK_SNIPER"):assert a124.is_shadow_sleeve_quarantined(w)is True
 for u in("W1_SOLAR_PEAK_LOCK","D1_4H_DOMINANCE_BOX","D1_QUIET_BOOK_BOX","N1_NEGRISK_CROSS_BOX","U1_DAILY_UPDOWN_LOCK"):assert a124.is_shadow_sleeve_quarantined(u)is False
 assert{"chengdu-daily-weather","beijing-daily-weather","seoul-daily-weather"}<=set(HIGH_VOLUME_WEATHER_SERIES);e=("This market will resolve to the highest temperature recorded at Chengdu Shuangliu International Airport according to https://aviationweather.gov/api/data/metar?ids=ZUUU on 27 Oct '26 (SPECI reports excluded).");g={"id":"ev_chengdu","title":"Highest temperature in Chengdu on October 27?","seriesSlug":"chengdu-daily-weather","description":e,"markets":[{"id":"m_zuuu_1","conditionId":"0xc1","groupItemTitle":"19°C or below","question":"19°C or below?","description":e,"endDate":"2026-10-27T16:00:00Z","clobTokenIds":'["tok_z1_y", "tok_z1_n"]'},{"id":"m_zuuu_2","conditionId":"0xc2","groupItemTitle":"20°C","question":"20°C?","description":e,"endDate":"2026-10-27T16:00:00Z","clobTokenIds":'["tok_z2_y", "tok_z2_n"]'},{"id":"m_zuuu_3","conditionId":"0xc3","groupItemTitle":"21°C","question":"21°C?","description":e,"endDate":"2026-10-27T16:00:00Z","clobTokenIds":'["tok_z3_y", "tok_z3_n"]'},{"id":"m_zuuu_4","conditionId":"0xc4","groupItemTitle":"22°C or higher","question":"22°C or higher?","description":e,"endDate":"2026-10-27T16:00:00Z","clobTokenIds":'["tok_z4_y", "tok_z4_n"]'}]};m=parse_weather_event(g,series_slug_hint="chengdu-daily-weather");assert m is not None and m.icao=="ZUUU"and m.unit=="C";t={"id":"ev_btc_4h","title":"Bitcoin Up or Down - Oct 26, 8:00AM-12:00PM ET","endDate":"2026-10-26T16:00:00Z","markets":[{"id":"m_btc_4h","conditionId":"0x4h","eventStartTime":"2026-10-26T12:00:00Z","endDate":"2026-10-26T16:00:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["tok_4h_up", "tok_4h_dn"]',"feesEnabled":True,"feeSchedule":{"rate":.072,"exponent":1},"cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"resolutionSource":"https://data.chain.link/streams/btc-usd"}]};l={"id":"ev_btc_15m","title":"Bitcoin Up or Down - Oct 26, 11:45AM-12:00PM ET","endDate":"2026-10-26T16:00:00Z","markets":[{"id":"m_btc_15m","conditionId":"0x15m","eventStartTime":"2026-10-26T15:45:00Z","endDate":"2026-10-26T16:00:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["tok_15m_up", "tok_15m_dn"]',"feesEnabled":True,"feeSchedule":{"rate":.072,"exponent":1},"cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"resolutionSource":"https://data.chain.link/streams/btc-usd"}]};s=parse_twap_candle_event(t,"BTC","4h");k=parse_twap_candle_event(l,"BTC","15m");assert s is not None and k is not None;v=build_crypto_price_query_url(s);assert"variant=fourhour"in v and"twapEnabled=true&twapLookbackSeconds=60"in v;assert verify_same_oracle_pair(s,k)is True;j=determine_dominance_legs(s,8e4,k,80500.);assert j is not None and j["regime"]=="4H_UP_PLUS_15M_DOWN";r={"id":"ev_ms","title":"Bitcoin above ___ on Oct 26?","endDate":"2026-10-26T16:00:00Z","markets":[{"id":"ms_72","conditionId":"0xms72","question":"Will the price of Bitcoin be above $72,000 on Oct 26?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["ms72_y", "ms72_n"]'},{"id":"ms_74","conditionId":"0xms74","question":"Will the price of Bitcoin be above $74,000 on Oct 26?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["ms74_y", "ms74_n"]'}]};q={"id":"ev_nr","title":"Bitcoin price on Oct 26?","endDate":"2026-10-26T16:00:00Z","markets":[{"id":"nr_lt72","conditionId":"0xnr1","groupItemTitle":"<72,000","question":"Will BTC be less than $72,000?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["nr_lt72_y", "nr_lt72_n"]'},{"id":"nr_72_74","conditionId":"0xnr2","groupItemTitle":"72,000-74,000","question":"Will BTC be between $72,000 and $74,000?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["nr_7274_y", "nr_7274_n"]'},{"id":"nr_gt74","conditionId":"0xnr3","groupItemTitle":">74,000","question":"Will BTC be greater than $74,000?","endDate":"2026-10-26T16:00:00Z","clobTokenIds":'["nr_gt74_y", "nr_gt74_n"]'}]};f=parse_multistrike_event(r,"BTC","btc-multi-strikes-weekly");a=parse_negrisk_bracket_event(q,"BTC","bitcoin-neg-risk-weekly");bundles=build_negrisk_cross_box_bundles(f,a);assert len(bundles)==6;i=[b for b in bundles if b["guaranteed_payout"]==1. and len(b["legs"])==3][0];h=walk_equal_shares_multi_leg_box([{"asks":[{"price":"0.28","size":"80"}],"fee_rate":.07,"fee_exponent":1.},{"asks":[{"price":"0.30","size":"80"}],"fee_rate":.07,"fee_exponent":1.},{"asks":[{"price":"0.31","size":"80"}],"fee_rate":.07,"fee_exponent":1.}],target_budget_usd=1e2,guaranteed_payout_per_bundle=i["guaranteed_payout"],max_bundle_cost_net=.992);assert h["filled"]is True and h["guaranteed_min_profit_usd"]>3.;o={"id":"ev_u1","title":"Bitcoin Up or Down on October 27?","endDate":"2026-10-27T16:00:00Z","markets":[{"id":"m_u1","conditionId":"0xu1","eventStartTime":"2026-10-26T16:00:00Z","endDate":"2026-10-27T16:00:00Z","outcomes":'["Up", "Down"]',"clobTokenIds":'["u1_up", "u1_dn"]'}]};n=parse_daily_updown_event(o,"BTC","btc-up-or-down-daily");assert n is not None and n.up_token=="u1_up"and n.down_token=="u1_dn"
 async def _sim_new_sleeves():
  monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"a124_v42_state.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"a124_v42_ledger.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"a124_v42_opps.json");d=a124.Alpha124ShadowDaemon(single_scan=True);l=1793026680.;d.spots["BTC"]=8.4e4;d.spots["ETH"]=2500.;b=a124.TwapCandleMarketSpec(asset="BTC",horizon="15m",market_id="m_pre_btc",condition_id="0xpreb",title="BTC PreOpen 15m",start_iso="2026-10-26T15:00:00Z",end_iso="2026-10-26T15:15:00Z",start_ts=1793026800.,end_ts=1793027700.,up_token="p1_btc_up",down_token="p1_btc_dn",fee_rate=.072,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/btc-usd");a=a124.TwapCandleMarketSpec(asset="ETH",horizon="15m",market_id="m_pre_eth",condition_id="0xpree",title="ETH PreOpen 15m",start_iso="2026-10-26T15:00:00Z",end_iso="2026-10-26T15:15:00Z",start_ts=1793026800.,end_ts=1793027700.,up_token="p1_eth_up",down_token="p1_eth_dn",fee_rate=.072,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/eth-usd");d.preopen_15m_candles={"BTC_pre15m_1793026800":b,"ETH_pre15m_1793026800":a};books={"p1_btc_up":{"bids":[{"price":"0.49","size":"100"}],"asks":[{"price":"0.51","size":"100"}]},"p1_btc_dn":{"bids":[{"price":"0.49","size":"100"}],"asks":[{"price":"0.51","size":"100"}]},"p1_eth_up":{"bids":[{"price":"0.49","size":"100"}],"asks":[{"price":"0.51","size":"100"}]},"p1_eth_dn":{"bids":[{"price":"0.49","size":"100"}],"asks":[{"price":"0.51","size":"100"}]},"s5m_btc_up":{"bids":[{"price":"0.78","size":"600"}],"asks":[{"price":"0.80","size":"600"}]}}
  async def fake_fetch(url,timeout=5.):
   if"/book?token_id="in url:return books.get(url.split("token_id=")[1])
   return None
  monkeypatch.setattr(d,"fetch_json",fake_fetch);h=[];await d.scan_and_manage_preopen_maker_straddles(h,now_ts=l);assert len(d.pending_preopen_straddles)==0;monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","0");await d.scan_and_manage_preopen_maker_straddles(h,now_ts=l);assert len(d.pending_preopen_straddles)==2;books["p1_btc_up"]["asks"]=[{"price":"0.48","size":"100"}];books["p1_btc_dn"]["asks"]=[{"price":"0.48","size":"100"}];books["p1_eth_up"]["asks"]=[{"price":"0.48","size":"100"}];books["p1_eth_up"]["bids"]=[{"price":"0.47","size":"100"}];await d.scan_and_manage_preopen_maker_straddles([],now_ts=1793026792.);assert any(p["sleeve"]=="P1_PREOPEN_MAKER_STRADDLE"for p in d.open_positions.values());e=[c for c in d.closed_positions if c["status"]=="PREOPEN_ONE_LEG_SCRATCH"];assert len(e)==1 and e[0]["tier_pnls_usd"]["T1000"]<.0;k=a124.TwapCandleMarketSpec(asset="BTC",horizon="5m",market_id="m_s5m",condition_id="0xs5m",title="BTC 5m",start_iso="2026-10-26T14:55:00Z",end_iso="2026-10-26T15:00:00Z",start_ts=1793026500.,end_ts=1793026800.,up_token="s5m_btc_up",down_token="s5m_btc_dn",fee_rate=.072,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/btc-usd");d.s5m_candles={"BTC_5m_1793026800":k};d.chainlink_open_cache[f"BTC_5m_{int(k.start_ts)}"]=(k.end_ts,83800.);d.usd_direct_flags["BTC"]=False;await d.scan_s5m_chainlink_sniper([],now_ts=1793026710.);assert not any(p["sleeve"]=="S5M_CHAINLINK_SNIPER"for p in d.open_positions.values());d.usd_direct_flags["BTC"]=True;await d.scan_s5m_chainlink_sniper([],now_ts=1793026710.);assert any(p["sleeve"]=="S5M_CHAINLINK_SNIPER"for p in d.open_positions.values());d.spot_hist["ETH"].clear();d.usd_spot_hist["ETH"].clear();d.spot_hist["ETH"].append((1e2,2306.5));d.spot_hist["ETH"].append((110.,2309.5));g=d.get_return_bps("ETH",5.);assert g>12.5;f={"shares":13,"avail_a_shares":1e2,"avail_b_shares":1e2,"leg_a_walk":{"best_ask":.8},"leg_b_walk":{"best_ask":.16}};j={"bids":[{"price":"0.78","size":"100"}],"asks":[{"price":"0.80","size":"100"}]};i={"bids":[{"price":"0.14","size":"100"}],"asks":[{"price":"0.16","size":"100"}]};assert d._passes_quiet_book_filter("ETH",j,i,f,110.)is False
 asyncio.run(_sim_new_sleeves())
def test_oct27_0655_strike_inversion_and_antibox_veto(tmp_path):
 from src.polymarket_research.same_oracle_dominance_box import(TwapCandleMarketSpec,build_prev_5m_gamma_event_url,compute_dominance_box_payout_from_close,determine_dominance_legs,parse_authoritative_open_price,walk_equal_shares_dominance_box);from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;l=TwapCandleMarketSpec(asset="SOL",horizon="15m",market_id="6247248",condition_id="0xsol15",title="SOL 6:45-7:00AM ET",start_iso="2026-10-27T10:45:00Z",end_iso="2026-10-27T11:00:00Z",start_ts=1793097900.,end_ts=1793098800.,up_token="sol_15m_up",down_token="sol_15m_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/sol-usd-twap-60s-streams");n=TwapCandleMarketSpec(asset="SOL",horizon="5m",market_id="6247315",condition_id="0xsol5",title="SOL 6:55-7:00AM ET",start_iso="2026-10-27T10:55:00Z",end_iso="2026-10-27T11:00:00Z",start_ts=1793098500.,end_ts=1793098800.,up_token="sol_5m_up",down_token="sol_5m_dn",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/sol-usd-twap-60s-streams");assert build_prev_5m_gamma_event_url(l).endswith("slug=sol-updown-5m-1793097600");assert build_prev_5m_gamma_event_url(n).endswith("slug=sol-updown-5m-1793098200");assert parse_authoritative_open_price({"openPrice":99.9644420334347,"completed":False,"cached":True})is None;assert parse_authoritative_open_price({"openPrice":99.9644420334347,"completed":False,"cached":True},request_url="https://polymarket.com/api/crypto/crypto-price?symbol=SOL&variant=fifteen")is None;from src.polymarket_research.same_oracle_dominance_box import build_crypto_price_query_url,parse_closed_gamma_event_settlement;h=build_crypto_price_query_url(l);k=build_crypto_price_query_url(n);assert"twapEnabled=true&twapLookbackSeconds=60"in h;assert parse_authoritative_open_price({"openPrice":99.8571312195911,"completed":False,"cached":True},request_url=h)==99.8571312195911;assert parse_authoritative_open_price({"openPrice":99.97149156931644,"completed":False,"cached":True},request_url=k)==99.97149156931644;g=parse_authoritative_open_price([{"closed":True,"eventMetadata":{"finalPrice":99.8571312195911}}]);j=parse_authoritative_open_price([{"closed":True,"eventMetadata":{"finalPrice":99.97149156931644}}]);assert g==99.8571312195911 and j==99.97149156931644;a=[{"closed":True,"eventMetadata":{"priceToBeat":99.8571312195911,"finalPrice":99.90631053937364}}];b=[{"closed":True,"eventMetadata":{"priceToBeat":99.97149156931644,"finalPrice":99.90631053937364}}];assert parse_closed_gamma_event_settlement(a,"DOWN")==.0;assert parse_closed_gamma_event_settlement(b,"UP")==.0;assert parse_closed_gamma_event_settlement(a,"UP")+parse_closed_gamma_event_settlement(b,"DOWN")==2.;i=determine_dominance_legs(l,g,n,j,min_corridor_bps=3.);assert i is not None and i["regime"]=="15M_UP_PLUS_5M_DOWN";assert i["leg_a"]["opp_token_id"]=="sol_15m_dn"and i["leg_b"]["opp_token_id"]=="sol_5m_up";assert compute_dominance_box_payout_from_close(99.90631053937364,i["k_low"],i["k_high"])==2.;m=walk_equal_shares_dominance_box(asks_a_raw=[{"price":"0.195","size":"100"}],asks_b_raw=[{"price":"0.574","size":"100"}],target_budget_usd=60.,max_box_cost_net=.985);assert m["filled"]is False and m["reason"]=="SUSPECT_INVERTED_ANTI_BOX";ex=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"antibox.jsonl");e=ex.execute_atomic_dominance_box(box_id="ANTI_BOX_VETO_TEST",leg_a_token_id="tok_a",leg_a_label="15M_DOWN",leg_a_limit_price=.22,leg_b_token_id="tok_b",leg_b_label="5M_UP",leg_b_limit_price=.48,shares=25,max_box_cost_net=.985);assert e["success"]is False and"ANTI_BOX_COST_FLOOR_VETO"in e["error"];d=ex.execute_atomic_dominance_box(box_id="ETH_THINNER_FIRST",leg_a_token_id="eth_15m",leg_a_label="15M_LEG",leg_a_limit_price=.24,leg_b_token_id="eth_5m",leg_b_label="5M_LEG",leg_b_limit_price=.7,shares=25,max_box_cost_net=.985,leg_a_avail_shares=442.,leg_b_avail_shares=173.);assert d["success"]is True and d["leg_1"]["label"]=="5M_LEG";p=build_prev_5m_gamma_event_url(l);o=[{"slug":"sol-updown-5m-1793097600","closed":True,"eventMetadata":{"finalPrice":99.8571312195911}}];f=[{"slug":"sol-updown-5m-1793097300","closed":True,"eventMetadata":{"finalPrice":99.}}];assert parse_authoritative_open_price(o,request_url=p)==99.8571312195911;assert parse_authoritative_open_price(f,request_url=p)is None;import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124_fc;c=tmp_path/"fc_state.json";a124_fc.STATE_FILE=c;q=a124_fc.Alpha124ShadowDaemon(single_scan=True);books_fc={}
 async def _fc_fetch(url,timeout=5.):
  for tk,bk in books_fc.items():
   if f"token_id={tk}"in url:return bk
  return None
 q.fetch_json=_fc_fetch;la={"opp_token_id":"oa","label":"A"};lb={"opp_token_id":"ob","label":"B"};assert asyncio.run(q._passes_complement_anti_box_check({"label":"A"},{"label":"B"}))is False;assert asyncio.run(q._passes_complement_anti_box_check(la,lb))is False;books_fc["oa"]={"bids":[{"price":"0.40","size":"50"}]};books_fc["ob"]={"bids":[]};assert asyncio.run(q._passes_complement_anti_box_check(la,lb))is False;books_fc["ob"]={"bids":[{"price":"0.55","size":"50"}]};assert asyncio.run(q._passes_complement_anti_box_check(la,lb))is True;books_fc["ob"]={"bids":[{"price":"0.61","size":"50"}]};assert asyncio.run(q._passes_complement_anti_box_check(la,lb))is False;books_fc["oa"]={"bids":[{"price":"0.985","size":"50"}],"asks":[{"price":"0.995","size":"50"}]};books_fc["ob"]={"bids":[],"asks":[{"price":"0.030","size":"80"}]};assert asyncio.run(q._passes_complement_anti_box_check(la,lb))is True;books_fc["oa"]={"bids":[{"price":"0.960","size":"50"}],"asks":[{"price":"0.970","size":"50"}]};books_fc["ob"]={"bids":[],"asks":[{"price":"0.100","size":"80"}]};assert asyncio.run(q._passes_complement_anti_box_check(la,lb))is False
def test_riskless_expansion_7coins_b3_w3no_pyth_and_maker_anchor(tmp_path):
 import asyncio;import time;from datetime import date;import src.polymarket_research.alpha_124_shadow_daemon as a124_exp;from src.polymarket_research.same_oracle_dominance_box import(DOMINANCE_ASSETS,MIN_CORRIDOR_BPS_BY_ASSET,build_crypto_price_query_url,determine_dominance_legs,parse_twap_candle_event);from src.polymarket_research.barrier_onetouch_svi_engine import detect_barrier_monotonicity_boxes;from src.polymarket_research.multistrike_svi_scalper import ZERO_FEE_PYTH_DAILY_SERIES;from src.polymarket_research.weather_metar_engine import(WeatherBucket,WeatherEventSpec,evaluate_weather_event_slate);assert set(DOMINANCE_ASSETS)=={"BTC","ETH","SOL","XRP","BNB","DOGE","HYPE"};assert len(ZERO_FEE_PYTH_DAILY_SERIES)==8;g={}
 for q,w,v in(("BNB","bnb","bnb-usd"),("DOGE","doge","doge-usd"),("HYPE","hype","hype-usd")):B={"slug":f"{w}-updown-15m-1793100000","endDate":"2026-10-27T11:15:00Z","markets":[{"id":f"m15_{q}","conditionId":"0x"+"11"*32,"question":f"{q} Up or Down 15m","eventStartTime":"2026-10-27T11:00:00Z","endDate":"2026-10-27T11:15:00Z","resolutionSource":f"https://data.chain.link/streams/{v}-twap-60s-streams","cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"outcomes":'["Up", "Down"]',"clobTokenIds":f'["{q}_15_up", "{q}_15_dn"]',"orderMinSize":5,"feesEnabled":True,"feeSchedule":{"rate":.07,"exponent":1}}]};D={"slug":f"{w}-updown-5m-1793100600","endDate":"2026-10-27T11:15:00Z","markets":[{"id":f"m5_{q}","conditionId":"0x"+"22"*32,"question":f"{q} Up or Down 5m","eventStartTime":"2026-10-27T11:10:00Z","endDate":"2026-10-27T11:15:00Z","resolutionSource":f"https://data.chain.link/streams/{v}-twap-60s-streams","cryptoMarketConfig":{"twapEnabled":True,"twapLookbackSeconds":60},"outcomes":'["Up", "Down"]',"clobTokenIds":f'["{q}_5_up", "{q}_5_dn"]',"orderMinSize":5,"feesEnabled":True,"feeSchedule":{"rate":.07,"exponent":1}}]};C=parse_twap_candle_event(B,q,"15m");s5=parse_twap_candle_event(D,q,"5m");assert C is not None and s5 is not None and C.asset==q;assert f"symbol={q}"in build_crypto_price_query_url(C);g[q]=(C,s5)
 dg15,t=g["DOGE"];assert determine_dominance_legs(dg15,.2,t,.20007,min_corridor_bps=MIN_CORRIDOR_BPS_BY_ASSET["DOGE"])is None;assert determine_dominance_legs(dg15,.2,t,.20014,min_corridor_bps=MIN_CORRIDOR_BPS_BY_ASSET["DOGE"])is not None;a124_exp.STATE_FILE=tmp_path/"exp_state.json";a124_exp.LEDGER_FILE=tmp_path/"exp_ledger.jsonl";a124_exp.LIVE_ALPHA124_STATE_MIRROR_FILE=tmp_path/"exp_mirror.json";a124_exp.D1_LIVE_CANDIDATES_FILE=tmp_path/"exp_d1_cands.jsonl";d_exp=a124_exp.Alpha124ShadowDaemon(single_scan=False);prev_slug=f"doge-updown-5m-{int(dg15.start_ts)-300}"
 async def _fetch_429_fallback(url,timeout=5.):
  if"crypto-price"in url:return None
  if prev_slug in url:return[{"slug":prev_slug,"closed":True,"eventMetadata":{"finalPrice":.21456}}]
  return None
 d_exp.fetch_json=_fetch_429_fallback;f=a124_exp.time.time
 try:a124_exp.time.time=lambda:dg15.start_ts+45.;z=asyncio.run(d_exp.get_authoritative_open_strike(dg15));assert z==.21456
 finally:a124_exp.time.time=f
 o=[{"direction":"UP","strike":1e5,"ask_yes":.5,"ask_no":.52,"market_id":"m_lo","condition_id":"0x1","yes_token":"t_lo_y","no_token":"t_lo_n","end_ts":time.time()+3600},{"direction":"UP","strike":1.05e5,"ask_yes":.58,"ask_no":.43,"market_id":"m_hi","condition_id":"0x2","yes_token":"t_hi_y","no_token":"t_hi_n","end_ts":time.time()+3600},{"direction":"DOWN","strike":8e4,"ask_yes":.58,"ask_no":.44,"market_id":"m_dlo","condition_id":"0x3","yes_token":"t_dlo_y","no_token":"t_dlo_n","end_ts":time.time()+3600},{"direction":"DOWN","strike":8.5e4,"ask_yes":.5,"ask_no":.52,"market_id":"m_dhi","condition_id":"0x4","yes_token":"t_dhi_y","no_token":"t_dhi_n","end_ts":time.time()+3600}];b3_found=detect_barrier_monotonicity_boxes(o,fee_rate=.07,max_box_cost_net=.985);assert len(b3_found)==2;assert{b["direction"]for b in b3_found}=={"UP","DOWN"};b1=WeatherBucket("w1","c1","<=69F","NYC <= 69F","w1_y","w1_n","F",-float("inf"),69.);b2=WeatherBucket("w2","c2","70-71F","NYC 70-71F","w2_y","w2_n","F",70.,71.);b3=WeatherBucket("w3","c3",">=72F","NYC >= 72F","w3_y","w3_n","F",72.,float("inf"));A=WeatherEventSpec("W_EV_NO","nyc-oct-27","nyc-daily-weather","NYC High","KLGA","NYC",40.77,-73.87,"America/New_York",date(2026,10,27),"HIGH","F","zero_fees","2026-10-28T04:00:00Z",[b1,b2,b3]);y=evaluate_weather_event_slate(A,[.34,.33,.33],{"w1":{"ask_yes":.42,"ask_yes_shares":50.,"ask_no":.62,"ask_no_shares":60.},"w2":{"ask_yes":.42,"ask_yes_shares":50.,"ask_no":.62,"ask_no_shares":60.},"w3":{"ask_yes":.42,"ask_yes_shares":50.,"ask_no":.62,"ask_no_shares":60.}},target_budget_usd=35.);j=y["full_slate_arb"];assert j is not None and j["mode"]=="FULL_SLATE_NO_COMPLEMENT_ARB";assert j["guaranteed_payout_per_set"]==2.;assert asyncio.run(d_exp.open_shadow_weather_slate(A,j,time.time()-60.))is True
 async def _fetch_w_closed(url,timeout=5.):
  if"/markets/w1"in url:return{"id":"w1","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["w1_y","w1_n"]',"outcomePrices":'["1","0"]'}
  if"/markets/w2"in url:return{"id":"w2","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["w2_y","w2_n"]',"outcomePrices":'["0","1"]'}
  if"/markets/w3"in url:return{"id":"w3","closed":True,"umaResolutionStatus":"resolved","clobTokenIds":'["w3_y","w3_n"]',"outcomePrices":'["0","1"]'}
  return None
 d_exp.fetch_json=_fetch_w_closed;asyncio.run(d_exp.manage_open_positions());i=[c for c in d_exp.closed_positions if c["sleeve"]=="W3_WEATHER_SLATE_ARB"];assert len(i)==1 and i[0]["won"]is True and i[0]["status"]=="SETTLED_WEATHER_SLATE_NX";assert i[0]["tier_pnls_usd"]["T100"]>.0;from dataclasses import replace as dc_replace;u=time.time();dg15=dc_replace(dg15,end_ts=u+180.);t=dc_replace(t,end_ts=u+180.);s=determine_dominance_legs(dg15,.2,t,.2002,min_corridor_bps=5.);assert s is not None;n=s["leg_a"]["token_id"];m=s["leg_b"]["token_id"];ma_books={n:{"bids":[{"price":"0.50","size":"80"}],"asks":[{"price":"0.53","size":"80"}]},m:{"bids":[{"price":"0.45","size":"220"}],"asks":[{"price":"0.46","size":"220"}]}}
 async def _fetch_ma(url,timeout=5.):
  for tk,bk in ma_books.items():
   if tk in url:return bk
  return None
 d_exp.fetch_json=_fetch_ma;assert d_exp.post_maker_anchor_candidate(dg15,t,s,ma_books[n],ma_books[m],now_ts=u-2.)is True;assert len(d_exp.pending_maker_anchors)==1;ma_books[n]={"bids":[{"price":"0.50","size":"80"}],"asks":[{"price":"0.51","size":"40"}]};asyncio.run(d_exp.manage_pending_maker_anchors(now_ts=u));assert len(d_exp.pending_maker_anchors)==0;l=[p for p in d_exp.open_positions.values()if p["sleeve"]=="D1_MAKER_ANCHOR_BOX"];assert len(l)==1 and l[0]["extra"]["is_maker_anchor_box"]is True;a,h=g["BNB"];a=dc_replace(a,end_ts=u+180.);h=dc_replace(h,end_ts=u+180.);k=determine_dominance_legs(a,6e2,h,600.6,min_corridor_bps=5.);assert k is not None;e=k["leg_a"]["token_id"];d=k["leg_b"]["token_id"];ma_books[e]={"bids":[{"price":"0.50","size":"80"}],"asks":[{"price":"0.53","size":"80"}]};ma_books[d]={"bids":[{"price":"0.45","size":"220"}],"asks":[{"price":"0.46","size":"220"}]};assert d_exp.post_maker_anchor_candidate(a,h,k,ma_books[e],ma_books[d],now_ts=u-2.)is True;assert len(d_exp.pending_maker_anchors)==1;ma_books[d]={"bids":[{"price":"0.45","size":"5"}],"asks":[{"price":"0.46","size":"5"}]};asyncio.run(d_exp.manage_pending_maker_anchors(now_ts=u));assert len(d_exp.pending_maker_anchors)==0;import json as _json_t;from src.polymarket_research.polymarket_terminal_recorder import ASSET_CONFIGS,PolymarketDualFeed1HRecorder
 for q in DOMINANCE_ASSETS:assert q in ASSET_CONFIGS;x=PolymarketDualFeed1HRecorder(asset=q);assert x.coinbase_product==f"{q}-USD";assert x.telemetry_5m_file.name==f"polymarket_5m_telemetry_{q.lower()}.jsonl";assert x.telemetry_15m_file.name==f"polymarket_15m_telemetry_{q.lower()}.jsonl";assert x.telemetry_4h_file.name==f"polymarket_4h_telemetry_{q.lower()}.jsonl"
 assert ASSET_CONFIGS["HYPE"].get("futures_only_ref")is True;assert ASSET_CONFIGS["DOGE"]["series_slug"]=="doge-up-or-down-hourly";assert ASSET_CONFIGS["BNB"]["series_slug"]=="bnb-up-or-down-hourly";d_exp._record_d1_corridor_telemetry("15m_5m",a,h,k,{"bids":[{"price":"0.50","size":"80"}],"asks":[{"price":"0.53","size":"80"}]},{"bids":[{"price":"0.45","size":"80"}],"asks":[{"price":"0.49","size":"80"}]},u);t_file=tmp_path/"alpha124_market_telemetry.jsonl";assert t_file.exists();t_rows=[_json_t.loads(ln)for ln in t_file.read_text(encoding="utf-8").splitlines()if ln.strip()];assert any(r["type"]=="D1_CORRIDOR"and r["asset"]=="BNB"and r["gross_box_l1"]==1.02 for r in t_rows)
def test_telemetry_compact_encoding_delta_dedupe_and_inode_safe_gzip_compactor(tmp_path,monkeypatch):
 import json as _json_c;import src.polymarket_research.alpha_124_shadow_daemon as a124;from scripts.honest_purged_wfo_optimizer import iter_jsonl_lines_with_archives;from scripts.polymarket_telemetry_compactor import compact_jsonl_file,is_protected_path;from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook,_dumps_compact;bk=L2OrderBook("tok_test");bk.apply_snapshot(bids=[{"price":str(round(.49-.01*i,2)),"size":"120"}for i in range(15)],asks=[{"price":str(round(.51+.01*i,2)),"size":"120"}for i in range(15)]);m=bk.last_book_update_ts+.5;l=bk.get_metrics(obs_ts=m,compact=False);comp_m=bk.get_metrics(obs_ts=m,compact=True);assert"microprice_formula"in l and"vwap_$250"in l and len(l["raw_top_bids"])==15;assert"microprice_formula"not in comp_m and"vwap_$250"not in comp_m and len(comp_m["raw_top_bids"])==10
 for k in("best_bid","best_ask","q_mid","q_micro","obi_l1","obi_depth","vwap_$20","vwap_$25","vwap_$50","effective_price_$50","fill_fees_$50"):assert comp_m[k]==l[k]
 c=len(_json_c.dumps({"UP":l,"DOWN":l}).encode("utf-8"));b=len(_dumps_compact({"UP":comp_m,"DOWN":comp_m}).encode("utf-8"));assert b<.45*c;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ldg.jsonl");monkeypatch.setattr(a124,"MARKET_TELEMETRY_FILE",tmp_path/"m_telem.jsonl");n=a124.Alpha124ShadowDaemon(single_scan=True);n._record_market_telemetry("W_SLATE_1",10.,{"type":"WEATHER_SLATE","sum_yes_l1":1.02},now_ts=1e3,sig=(1.02,));n._record_market_telemetry("W_SLATE_1",10.,{"type":"WEATHER_SLATE","sum_yes_l1":1.02},now_ts=1025.,sig=(1.02,));n._record_market_telemetry("W_SLATE_1",10.,{"type":"WEATHER_SLATE","sum_yes_l1":.99},now_ts=1040.,sig=(.99,));j=(tmp_path/"m_telem.jsonl").read_text(encoding="utf-8").splitlines();assert len(j)==2;assert is_protected_path(tmp_path/"live_orders.jsonl")is True;assert is_protected_path(tmp_path/"finalized_market_resolutions.jsonl")is True;assert is_protected_path(tmp_path/"alpha124_shadow_ledger.jsonl")is True;assert is_protected_path(tmp_path/"d1_live_box_candidates.jsonl")is True;assert is_protected_path(tmp_path/"polymarket_hourly_telemetry.jsonl")is False;assert is_protected_path(tmp_path/"alpha124_market_telemetry.jsonl")is False;assert is_protected_path(tmp_path/"counterfactual_candidates.jsonl")is False;pm_dir=tmp_path/"polymarket";pm_dir.mkdir(parents=True,exist_ok=True);h=pm_dir/"polymarket_hourly_telemetry.jsonl";g=pm_dir/"polymarket_hourly_telemetry_eth.jsonl";a=[f"btc_{i}"for i in range(400)];h.write_text("".join(_dumps_compact({"seq":i,"id":f"btc_{i}","UP":comp_m})+"\n"for i in range(400)),encoding="utf-8");g.write_text("".join(_dumps_compact({"seq":i,"id":f"eth_{i}","UP":comp_m})+"\n"for i in range(400)),encoding="utf-8");f=compact_jsonl_file(h,hot_threshold_bytes=20000,keep_tail_bytes=15000,min_archive_bytes=10000);e=compact_jsonl_file(g,hot_threshold_bytes=20000,keep_tail_bytes=15000,min_archive_bytes=10000);assert f["status"]=="COMPACTED"and f["inode_preserved"]is True and f["compression_ratio_x"]>3.;assert e["status"]=="COMPACTED";assert h.stat().st_size<25000;d=[_json_c.loads(ln)["id"]for ln in iter_jsonl_lines_with_archives(pm_dir,"polymarket_hourly_telemetry.jsonl")if ln.strip()];assert d==a
def test_multi_vertical_zero_fee_expansion_sleeves(tmp_path,monkeypatch):
 import asyncio;import time;from datetime import date;from zoneinfo import ZoneInfo;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.barrier_onetouch_svi_engine import BarrierRungSpec;from src.polymarket_research.tradfi_sports_zero_fee_engine import(compute_effective_trading_hours,detect_nba_dominance_boxes,detect_pyth_calendar_inclusion_boxes,detect_pyth_close_vs_hit_boxes,parse_nba_zero_fee_event,parse_zero_fee_negrisk_slate);from src.polymarket_research.weather_metar_engine import(MetarObservation,WeatherBucket,WeatherEventSpec,compute_weather_probabilities,parse_hko_csv_observations,parse_weather_event);A="Date time,Automatic Weather Station,Air Temperature(degree Celsius)\n202610281020,Chek Lap Kok,28.7\n202610281020,HK Observatory,26.2\n";z="Date time,Automatic Weather Station,Max,Min\n202610281020,Chek Lap Kok,28.7,26.0\n202610281020,HK Observatory,26.3,24.8\n";hko_obs=parse_hko_csv_observations(A,z,date(2026,10,28));assert len(hko_obs)==3;assert max(o.temp_c for o in hko_obs)==26.3;assert min(o.temp_c for o in hko_obs)==24.8;assert hko_obs[-1].temp_c==26.2;y={"id":"ev_hko_1","title":"Highest temperature in Hong Kong on October 28?","endDate":"2026-10-28T16:00:00Z","markets":[{"id":f"hk_{i}","conditionId":f"0xhk_{i}","groupItemTitle":lbl,"description":"Resolves to highest temperature recorded by the Hong Kong Observatory on 28 Oct '26 via https://www.weather.gov.hk/en/cis/climat.htm","clobTokenIds":f'["hy_{i}", "hn_{i}"]',"feeType":"zero_fees","feesEnabled":True,"feeSchedule":{"rate":0}}for i,lbl in enumerate(["25°C or below","26°C","27°C","28°C or higher"])]};x=parse_weather_event(y);assert x is not None and x.icao=="HKO"and x.fee_type=="zero_fees";tz_ny=ZoneInfo("America/New_York");f=[WeatherBucket("b0","c0","9°C or below","9-","y0","n0","C",float("-inf"),9.),WeatherBucket("b1","c1","10°C","10","y1","n1","C",10.,10.),WeatherBucket("b2","c2","11°C","11","y2","n2","C",11.,11.),WeatherBucket("b3","c3","12°C or higher","12+","y3","n3","C",12.,float("inf"))];w=WeatherEventSpec("ev_low","nyc-low","nyc-daily-lowest-temperature","Lowest temperature in NYC on October 28?","KLGA","NYC",40.7769,-73.874,"America/New_York",date(2026,10,28),"LOW","C","zero_fees","2026-10-29T04:00:00Z",f);E=datetime(2026,10,28,6,0,tzinfo=tz_ny);D=datetime(2026,10,28,11,0,tzinfo=tz_ny);t=[MetarObservation("KLGA",E.astimezone(timezone.utc),E,10.1,True,"T0101"),MetarObservation("KLGA",D.astimezone(timezone.utc),D,14.5,True,"T0145")];q={int(datetime(2026,10,28,h,0,tzinfo=tz_ny).astimezone(timezone.utc).timestamp()):[13.5]*20 for h in range(12,24)};q[int(datetime(2026,10,29,0,0,tzinfo=tz_ny).astimezone(timezone.utc).timestamp())]=[13.2]*20;v=compute_weather_probabilities(w,D.astimezone(timezone.utc),t,q);assert v["is_solar_lock"]is True and v["locked_bucket_idx"]==1;n=dict(q);n[int(datetime(2026,10,28,23,0,tzinfo=tz_ny).astimezone(timezone.utc).timestamp())]=[10.8]*20;s=compute_weather_probabilities(w,D.astimezone(timezone.utc),t,n);assert s["is_solar_lock"]is False;m=datetime(2026,10,30,15,0,tzinfo=tz_ny).timestamp();e=datetime(2026,11,2,10,30,tzinfo=tz_ny).timestamp();assert abs(compute_effective_trading_hours(m,e,"EQUITY_RTH")-2.)<1e-6;l=detect_pyth_calendar_inclusion_boxes([{"asset":"WTI","direction":"UP","strike":105.,"fee_rate":.0,"start_ts":1e3,"end_ts":5e4,"ask_yes":.45,"ask_no":.56,"market_id":"w1","condition_id":"cw1","yes_token":"wy","no_token":"wn"},{"asset":"WTI","direction":"UP","strike":105.,"fee_rate":.0,"start_ts":9e2,"end_ts":2e5,"ask_yes":.42,"ask_no":.59,"market_id":"m1","condition_id":"cm1","yes_token":"my","no_token":"mn"}]);assert len(l)==1 and abs(l[0]["box_cost_net"]-.98)<1e-6;k=detect_pyth_close_vs_hit_boxes(close_rows=[{"asset":"SPY","strike":775.,"is_downward":False,"fee_rate":.0,"end_ts":5e3,"ask_no":.55,"market_id":"c1","condition_id":"cc1","yes_token":"cy","no_token":"cn"}],hit_rows=[{"asset":"SPY","strike":775.,"direction":"UP","fee_rate":.0,"start_ts":1e3,"end_ts":9e3,"ask_yes":.43,"market_id":"h1","condition_id":"ch1","yes_token":"hy","no_token":"hn"}],now_ts=2e3);assert len(k)==1 and abs(k[0]["box_cost_net"]-.98)<1e-6;u={"id":"nba_1","slug":"nba-bkn-bos","title":"Nets vs. Celtics","endDate":"2026-10-28T23:30:00Z","markets":[{"id":"ml","conditionId":"c_ml","sportsMarketType":"moneyline","question":"Nets vs. Celtics","outcomes":'["Nets", "Celtics"]',"clobTokenIds":'["t_nets_ml", "t_bos_ml"]',"feeType":"zero_fees","feesEnabled":True,"feeSchedule":{"rate":0}},{"id":"sp_bos","conditionId":"c_sp1","sportsMarketType":"spreads","question":"Spread: Celtics (-4.5)","outcomes":'["Celtics", "Nets"]',"line":-4.5,"clobTokenIds":'["t_bos_m45", "t_nets_p45"]',"feeType":"zero_fees","feesEnabled":True,"feeSchedule":{"rate":0}},{"id":"sp_1h","conditionId":"c_1h","sportsMarketType":"first_half_spreads","question":"1H Spread: Celtics (-2.5)","outcomes":'["Celtics", "Nets"]',"line":-2.5,"clobTokenIds":'["t_1h_a", "t_1h_b"]',"feeType":"zero_fees"},{"id":"tot_lo","conditionId":"c_tl","sportsMarketType":"totals","question":"Nets vs. Celtics: O/U 215.5","outcomes":'["Over", "Under"]',"line":215.5,"clobTokenIds":'["t_ov_215", "t_un_215"]',"feeType":"zero_fees"},{"id":"tot_hi","conditionId":"c_th","sportsMarketType":"totals","question":"Nets vs. Celtics: O/U 220.5","outcomes":'["Over", "Under"]',"line":220.5,"clobTokenIds":'["t_ov_220", "t_un_220"]',"feeType":"zero_fees"}]};sp_nba=parse_nba_zero_fee_event(u,now_ts=1.79322e9);assert sp_nba is not None;assert all("1h"not in lg.token_id for lg in sp_nba.margin_legs);nba_arbs=detect_nba_dominance_boxes(sp_nba,{"t_bos_ml":.56,"t_nets_p45":.425,"t_bos_m45":.58,"t_nets_ml":.4,"t_ov_215":.52,"t_un_220":.465},max_box_cost_net=.994);labels={a["label"]for a in nba_arbs};assert"Nets +4.5 + Celtics ML"in labels;assert"Over 215.5 + Under 220.5"in labels;assert not any("Nets ML"in lbl and"Celtics -4.5"in lbl for lbl in labels),"Anti-box must never be emitted!";C={"id":"nr_elon","title":"Elon tweets 48h?","negRisk":True,"endDate":"2026-10-30T16:00:00Z","markets":[{"id":"e0","closed":True,"outcomePrices":'["0", "1"]'},{"id":"e1","conditionId":"ce1","groupItemTitle":"40-64","clobTokenIds":'["ey1","en1"]',"feeType":"zero_fees"},{"id":"e2","conditionId":"ce2","groupItemTitle":"65-89","clobTokenIds":'["ey2","en2"]',"feeType":"zero_fees"},{"id":"e3","conditionId":"ce3","groupItemTitle":"90+","clobTokenIds":'["ey3","en3"]',"feeType":"zero_fees"}]};assert parse_zero_fee_negrisk_slate(C,"elon-tweets-48h")is not None;C["markets"][0]["outcomePrices"]='["1", "0"]';assert parse_zero_fee_negrisk_slate(C,"elon-tweets-48h")is None;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"b4_st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"b4_ldg.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"b4_opps.json")
 async def _run_b4():
  d=a124.Alpha124ShadowDaemon(single_scan=True);b=time.time();d.spots["BTC"]=84200.;d.barrier_rungs["m_b4"]=BarrierRungSpec(asset="BTC",horizon_group="WEEK",series_slug="btc-hit",event_id="ev_b4",market_id="m_b4",condition_id="0xcb4",group_label="↑ 85,000",question="Will BTC hit $85,000?",strike=8.5e4,direction="UP",start_ts=b-7200.,end_ts=b+86400.,yes_token="t_b4_y",no_token="t_b4_n",fee_rate=.07);d.barrier_rungs["m_b4_stale"]=BarrierRungSpec(asset="BTC",horizon_group="MONTH",series_slug="btc-hit",event_id="ev_b4",market_id="m_b4_stale",condition_id="0xcst",group_label="↑ 85,000",question="Will BTC reach $85,000 in Oct?",strike=8.5e4,direction="UP",start_ts=b-6e2,end_ts=b+86400.,yes_token="t_b4_stale_y",no_token="t_b4_stale_n",fee_rate=.07);d.barrier_ext_cache["ev_b4"]=(b,(85120.,83900.,84200.))
  async def fake_batch(toks,timeout=3.):return{"t_b4_y":{"bids":[{"price":"0.95","size":"200"}],"asks":[{"price":"0.97","size":"200"}]},"t_b4_stale_y":{"bids":[{"price":"0.07","size":"200"}],"asks":[{"price":"0.085","size":"200"}]}}
  monkeypatch.setattr(d,"fetch_books_batch",fake_batch);a=[];await d.scan_barrier_markets(a);assert any(p["sleeve"]=="B4_TOUCHED_BARRIER_WICK_LOCK"and p["dedupe_key"]=="B4_m_b4"for p in d.open_positions.values());assert not any(p["dedupe_key"]=="B4_m_b4_stale"for p in d.open_positions.values())
 asyncio.run(_run_b4());from src.polymarket_research.barrier_onetouch_svi_engine import parse_hit_event;from src.polymarket_research.tradfi_sports_zero_fee_engine import is_same_continuous_session;mid_ev={"id":"ev_oct","startDate":"2026-10-01T05:00:00Z","endDate":"2026-11-01T03:59:59Z","markets":[{"id":"m_init","conditionId":"c1","question":"Will ETH reach $3,000 in October?","groupItemTitle":"↑ 3,000","clobTokenIds":'["y1","n1"]',"startDate":"2026-10-01T05:00:00Z"},{"id":"m_minted","conditionId":"c2","question":"Will ETH reach $2,600 in October?","groupItemTitle":"↑ 2,600","clobTokenIds":'["y2","n2"]',"startDate":"2026-10-22T16:18:20Z","description":"from the creation of this market through 11:59 PM ET"}]};g={r.market_id:r for r in parse_hit_event(mid_ev,"ETH","MONTHLY","ethereum-hit-price-monthly")};assert g["m_minted"].start_ts>g["m_init"].start_ts+15*86400.;B=ZoneInfo("America/New_York");c=a124.datetime(2026,10,27,23,0,tzinfo=B).timestamp();j=a124.datetime(2026,10,30,14,0,tzinfo=B).timestamp();b=a124.datetime(2026,10,30,16,0,tzinfo=B).timestamp();assert not is_same_continuous_session(c,b,"EQUITY_RTH"),"Multi-day / overnight earnings gap must be vetoed!";assert is_same_continuous_session(j,b,"EQUITY_RTH"),"Friday same-session RTH final 2h must pass!"
def test_phase2_macro_counting_ctf_aaa_and_maker_anchors(monkeypatch,tmp_path):
 import asyncio;from datetime import datetime;from zoneinfo import ZoneInfo;from src.polymarket_research import alpha_124_shadow_daemon as a124;from src.polymarket_research.macro_counting_ctf_engine import(ALL_FOMC_MASK,ALL_OIL_SENATE_MASK,build_fomc_truth_table_legs,build_oil_senate_truth_table_legs,detect_counting_subwindow_boxes,detect_d2_12pm_binance_boxes,evaluate_ai_elo_ci_lock,evaluate_counting_dead_no_locks,evaluate_locked_market_reward_carry,evaluate_pyth_catalyst_shock,find_cross_event_bitmask_boxes,parse_aaa_gas_html,parse_counting_slate_event,walk_equal_shares_overround_bids);from src.polymarket_research.redeem_settled_positions import(encode_ctf_merge_or_split_calldata,inspect_mergeable_complete_set);B={"id":"ev_elon_7d","slug":"elon-musk-of-tweets-october-27-november-3","title":"Elon Musk # tweets October 27 - November 3, 2026?","endDate":"2026-11-03T17:00:00Z","description":"from October 27, 2026, 12:00 PM ET to November 3, 2026, 12:00 PM ET","markets":[{"id":"c7_0","closed":True,"groupItemTitle":"<40","outcomePrices":'["0","1"]'},{"id":"c7_1","conditionId":"0xc71","groupItemTitle":"40-64","clobTokenIds":'["t7_y1","t7_n1"]',"feeType":"zero_fees","rewardsMinSize":50,"rewardsMaxSpread":3.5},{"id":"c7_2","conditionId":"0xc72","groupItemTitle":"65-89","clobTokenIds":'["t7_y2","t7_n2"]',"feeType":"zero_fees"},{"id":"c7_3","conditionId":"0xc73","groupItemTitle":"140+","clobTokenIds":'["t7_yup","t7_nup"]',"feeType":"zero_fees"}]};u={"id":"ev_elon_48h","slug":"elon-musk-of-tweets-october-29-october-31","title":"Elon Musk # tweets October 29 - October 31, 2026?","endDate":"2026-10-31T16:00:00Z","description":"from October 29, 2026, 12:00 PM ET to October 31, 2026, 12:00 PM ET","markets":[{"id":"c2_0","conditionId":"0xc20","groupItemTitle":"<40","clobTokenIds":'["t2_ylo","t2_nlo"]',"feeType":"zero_fees"},{"id":"c2_1","conditionId":"0xc21","groupItemTitle":"40-89","clobTokenIds":'["t2_ym","t2_nm"]',"feeType":"zero_fees"},{"id":"c2_2","conditionId":"0xc22","groupItemTitle":"90+","clobTokenIds":'["t2_yup","t2_nup"]',"feeType":"zero_fees"}]};s7=parse_counting_slate_event(B,"elon-tweets","elonmusk");s2=parse_counting_slate_event(u,"elon-tweets-48h","elonmusk");assert s7 is not None and s2 is not None and s7.gamma_closed_floor==40;t={s7.slug:{"total":68,"hourly":[(s7.window_start_ts+3600.,55)]}};o,dead=evaluate_counting_dead_no_locks(s7,t,safety_post_buffer=2);assert o==68 and[b.market_id for b in dead]==["c7_1"];rw=evaluate_locked_market_reward_carry(1.,.975,.99,50.,3.5,.0);assert rw["eligible"]is True and.975<=rw["resting_bid"]<=.985;tw_boxes=detect_counting_subwindow_boxes([s7,s2],{"t2_nup":.44,"t7_yup":.54},{"elonmusk":t},max_box_cost_net=.99);assert any(b["box_kind"]=="TW1_UPPER_SUBWINDOW"and abs(b["box_cost_net"]-.98)<1e-6 for b in tw_boxes);g=[{"slug":"fed-decision-in-october-2026","endDate":"2026-10-29T18:00:00Z","markets":[{"id":"fo_p","conditionId":"0xfop","groupItemTitle":"No change","clobTokenIds":'["fop_y","fop_n"]',"feeType":"zero_fees"}]}];n=[{"slug":"fed-decisions-oct-jan","endDate":"2027-01-29T19:00:00Z","markets":[{"id":"fp_1","conditionId":"0xfp1","groupItemTitle":"Pause-Pause-Pause","clobTokenIds":'["fp1_y","fp1_n"]',"feeType":"zero_fees"},{"id":"fp_2","conditionId":"0xfp2","groupItemTitle":"Hike-Pause-Pause","clobTokenIds":'["fp2_y","fp2_n"]',"feeType":"zero_fees"},{"id":"fp_o","conditionId":"0xfpo","groupItemTitle":"Other","clobTokenIds":'["fpo_y","fpo_n"]',"feeType":"zero_fees"}]}];s=build_fomc_truth_table_legs(g,n);m=find_cross_event_bitmask_boxes(s,{"fop_y":.88,"fp1_n":.105},ALL_FOMC_MASK,max_2leg_cost=.995);assert len(m)==1 and m[0]["n_legs"]==2 and m[0]["box_cost_net"]==.985;r={"which-party-will-win-the-senate-in-2026":{"endDate":"2026-11-04T00:00:00Z","markets":[{"id":"sm_d","conditionId":"0xsmd","groupItemTitle":"Democratic Party","clobTokenIds":'["smd_y","smd_n"]',"feeType":"zero_fees"}]},"who-wins-the-senate-pending-oil-above-or-below-80-before-the-midterms":{"endDate":"2026-11-04T00:00:00Z","markets":[{"id":"s80_ld","conditionId":"0x80ld","groupItemTitle":"Oil < $80; D Senate","clobTokenIds":'["o80ld_y","o80ld_n"]',"feeType":"zero_fees"},{"id":"s80_gd","conditionId":"0x80gd","groupItemTitle":"Oil ≥ $80; D Senate","clobTokenIds":'["o80gd_y","o80gd_n"]',"feeType":"zero_fees"}]},"who-wins-the-senate-pending-oil-below-85-before-the-midterms":{"endDate":"2026-11-04T00:00:00Z","markets":[{"id":"s85_ld","conditionId":"0x85ld","groupItemTitle":"Oil < $85; D Senate","clobTokenIds":'["o85ld_y","o85ld_n"]',"feeType":"zero_fees"}]}};l=build_oil_senate_truth_table_legs(r);os_boxes=find_cross_event_bitmask_boxes(l,{"o80ld_y":.01,"o80gd_y":.64,"smd_n":.335,"o80ld_n":.97,"o85ld_y":.015},ALL_OIL_SENATE_MASK,max_2leg_cost=.995,max_3leg_cost=.995);assert any(b["n_legs"]==3 and abs(b["box_cost_net"]-.985)<1e-6 for b in os_boxes);assert any(b["n_legs"]==2 and abs(b["box_cost_net"]-.985)<1e-6 for b in os_boxes);C=walk_equal_shares_overround_bids([{"bids":[{"price":"0.52","size":"50"}],"fee_rate":.0,"fee_exponent":1.},{"bids":[{"price":"0.49","size":"50"}],"fee_rate":.0,"fee_exponent":1.}],target_mint_budget_usd=40.,min_net_proceeds_per_set=1.004);assert C["filled"]is True and C["net_proceeds_per_set"]==1.01;k="0x"+"ab"*32;from src.polymarket_research import redeem_settled_positions as rsp;_,f=encode_ctf_merge_or_split_calldata(k,25.,is_split=False,neg_risk=False);_,e=encode_ctf_merge_or_split_calldata(k,25.,is_split=True,neg_risk=False);_,j=encode_ctf_merge_or_split_calldata(k,25.,is_split=False,neg_risk=True);_,i=encode_ctf_merge_or_split_calldata(k,25.,is_split=True,neg_risk=True);assert f[:10]=="0x9e7212ad"and e[:10]=="0x72ce4275";assert j[:10]=="0xb10c5c17"and i[:10]=="0xa3d7da1d";monkeypatch.setattr(rsp,"get_token_balance_onchain",lambda addr,tok:12.5 if tok=="tok_y"else 15.);assert inspect_mergeable_complete_set("0x1111111111111111111111111111111111111111","tok_y","tok_n")==12.5;c='<div>Price as of 10/27/26</div><td>$4.2661</td><td>$4.2661</td><td>$4.7966</td><td>$5.1822</td><td>$5.5656</td><td>$3.2856</td><td>$4.2602</td>';A=parse_aaa_gas_html(c);assert A=={"as_of_date":"2026-10-27","current_regular":4.2661,"yesterday_regular":4.2602};from src.polymarket_research.tradfi_sports_zero_fee_engine import detect_pyth_calendar_inclusion_boxes,parse_pyth_hit_event;q={"id":"ev_nov","startDate":"2026-10-25T04:02:00Z","endDate":"2026-12-01T04:59:59Z","markets":[{"id":"6172752","conditionId":"0xnov","question":"Will WTI Crude Oil (WTI) hit (HIGH) $100 in November?","groupItemTitle":"↑ $100","clobTokenIds":'["ny","nn"]',"feeType":"zero_fees","description":"during a trading session of November 2026, any Pyth 1-minute candle"}]};z=parse_pyth_hit_event(q,"WTI","MONTHLY","wti-hit");a=datetime(2026,10,28,12,0,tzinfo=ZoneInfo("America/New_York")).timestamp();assert len(z)==1 and z[0].start_ts>a;assert detect_pyth_calendar_inclusion_boxes([{"asset":"WTI","direction":"UP","strike":1e2,"start_ts":a-86400.,"end_ts":a+86400.,"ask_no":.4,"ask_yes":.6,"fee_rate":.0},{"asset":"WTI","direction":"UP","strike":1e2,"start_ts":z[0].start_ts,"end_ts":z[0].end_ts,"ask_no":.5,"ask_yes":.5,"fee_rate":.0}],now_ts=a)==[];ny=ZoneInfo("America/New_York");y=datetime(2026,10,28,10,31,tzinfo=ny).timestamp();x=datetime(2026,10,28,11,30,tzinfo=ny).timestamp();w=evaluate_pyth_catalyst_shock("WTI",69.,70.2,71.,"UP",3.,.35,y);v=evaluate_pyth_catalyst_shock("WTI",69.,70.2,71.,"UP",3.,.35,x);assert w["eligible"]is True and w["catalyst"]=="EIA_1030_PETROLEUM"and w["side"]=="YES";assert v["eligible"]is False;h=[{"organization":"Google","rating":1395,"rating_q025":1388,"rating_q975":1402},{"organization":"OpenAI","rating":1372,"rating_q025":1365,"rating_q975":1379}]
 assert evaluate_ai_elo_ci_lock(h,1e3,5e4,3.6e4)["eligible"]is False,"Stale >6h snapshot must be rejected!";assert evaluate_ai_elo_ci_lock(h,4.8e4,5e4,3.6e4)["eligible"]is True;d2=detect_d2_12pm_binance_boxes({"asset":"BTC","market_id":"h1","condition_id":"0xh1","end_ts":1793203200.,"up_token":"h_up","down_token":"h_dn","fee_rate":.07},83800.,[{"market_id":"d1","condition_id":"0xd1","end_ts":1793203200.,"strike":84400.,"is_downward":False,"yes_token":"d_y","no_token":"d_n","fee_rate":.07}]);assert len(d2)==1 and d2[0]["leg_a"]["token_id"]=="h_up"and d2[0]["leg_b"]["token_id"]=="d_n";monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"zfa_st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"zfa_ldg.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"zfa_opps.json")
 async def _run_zfa():
  d=a124.Alpha124ShadowDaemon(single_scan=True);c=1.79322e9;la={"token_id":"za1","opp_token_id":"za2","condition_id":"0x1","side":"YES","label":"Nets +4.5","market_id":"m1","fee_rate":.0};lb={"token_id":"zb1","opp_token_id":"zb2","condition_id":"0x2","side":"YES","label":"Celtics ML","market_id":"m2","fee_rate":.0};b={"bids":[{"price":"0.41","size":"200"}],"asks":[{"price":"0.45","size":"200"}]};a={"bids":[{"price":"0.54","size":"300"}],"asks":[{"price":"0.56","size":"300"}]};ok=d.post_zero_fee_maker_anchor_box("SP1_NBA","NBA","ZFA_TEST_1",la,lb,b,a,c+7200.,"Nets vs Celtics",c);assert ok is True and d.pending_zero_fee_maker_anchors["ZFA_TEST_1"]["bid_px"]==.42
  async def fake_bks_fill(toks,timeout=3.):return{"za1":{"bids":[{"price":"0.41","size":"200"}],"asks":[{"price":"0.42","size":"200"}]},"zb1":{"bids":[{"price":"0.54","size":"300"}],"asks":[{"price":"0.56","size":"300"}]}}
  monkeypatch.setattr(d,"fetch_books_batch",fake_bks_fill);await d.manage_pending_zero_fee_maker_anchors(c+2.);assert any(p["sleeve"]in("ZF_INTRADAY_MAKER_BOX","ZERO_FEE_MAKER_ANCHOR_BOX")and p["entry_eff_px_t1000"]==.98 for p in d.open_positions.values())
 asyncio.run(_run_zfa())
def test_exp406_hardened_d1_maker_leg1_wfo_and_microstructure_shields(tmp_path,monkeypatch):
 import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.orderflow_wfo_simulators import calibrate_d1_maker_leg1_wfo;from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec,determine_dominance_legs;m=calibrate_d1_maker_leg1_wfo();assert m["sealed_holdout"]["legging_adjusted_pnl_usd"]>.0;assert m["sealed_holdout"]["scratches"]==0;assert m["sealed_holdout"]["legging_adjusted_pnl_usd"]>m["unguarded_maker_holdout_baseline"]["legging_adjusted_pnl_usd"];monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"m406_st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"m406_ldg.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"m406_opps.json");monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","0");d=a124.Alpha124ShadowDaemon(single_scan=True);g=1793226000.;l=TwapCandleMarketSpec(asset="BTC",horizon="15m",market_id="m15_btc",condition_id="0xc15",title="BTC 15m",start_iso="2026-10-28T22:15:00Z",end_iso="2026-10-28T22:30:00Z",start_ts=g-700,end_ts=g+200,up_token="t15u",down_token="t15d",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams");s5=TwapCandleMarketSpec(asset="BTC",horizon="5m",market_id="m5_btc",condition_id="0xc5",title="BTC 5m",start_iso="2026-10-28T22:25:00Z",end_iso="2026-10-28T22:30:00Z",start_ts=g-100,end_ts=g+200,up_token="t5u",down_token="t5d",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/btc-usd-twap-60s-streams");k=determine_dominance_legs(l,8.1e4,s5,81050.,min_corridor_bps=3.);assert k is not None;ta,tb=k["leg_a"]["token_id"],k["leg_b"]["token_id"];a={"bids":[{"price":"0.48","size":"20"}],"asks":[{"price":"0.49","size":"60"}]};e={"bids":[{"price":"0.48","size":"80"}],"asks":[{"price":"0.49","size":"80"}]};assert d.post_maker_anchor_candidate(l,s5,k,a,a,now_ts=g)is False;d.spots["BTC"]=81025.;b={"bids":[{"price":"0.48","size":"90"}],"asks":[{"price":"0.49","size":"80"}]};assert d.post_maker_anchor_candidate(l,s5,k,b,e,now_ts=g)is True;dk=f"D1_MKR_BTC_{l.market_id}_{s5.market_id}";assert d.pending_maker_anchors[dk]["bid_px"]==.48 and d.pending_maker_anchors[dk]["queue_front"]is False;bks_live={ta:b,tb:e}
 async def _fb(toks,timeout=2.5):return{t:bks_live[t]for t in toks if t in bks_live}
 monkeypatch.setattr(d,"fetch_books_batch",_fb)
 if k["leg_a"]["side"]=="UP":d.spots["BTC"]=81025.*1.0003
 else:d.spots["BTC"]=81025.*.9997
 asyncio.run(d.manage_pending_maker_anchors(now_ts=g+.5));assert dk in d.pending_maker_anchors,"Favorable spot move must NOT cancel resting anchor!"
 if k["leg_a"]["side"]=="UP":d.spots["BTC"]=81025.*.99965
 else:d.spots["BTC"]=81025.*1.00035
 asyncio.run(d.manage_pending_maker_anchors(now_ts=g+.8));assert dk not in d.pending_maker_anchors,"Adverse spot move > 2.5 bps MUST cancel resting anchor at $0 cost!";x4=TwapCandleMarketSpec(asset="XRP",horizon="4h",market_id="m4_xrp",condition_id="0xx4",title="XRP 4h",start_iso="2026-10-28T20:00:00Z",end_iso="2026-10-29T00:00:00Z",start_ts=g-14000,end_ts=g+200,up_token="tx4u",down_token="tx4d",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/xrp-usd-twap-60s-streams");j=TwapCandleMarketSpec(asset="XRP",horizon="15m",market_id="m15_xrp",condition_id="0xx15",title="XRP 15m",start_iso="2026-10-28T23:45:00Z",end_iso="2026-10-29T00:00:00Z",start_ts=g-700,end_ts=g+200,up_token="tx15u",down_token="tx15d",fee_rate=.07,fee_exponent=1.,neg_risk=False,twap_lookback_sec=60,resolution_source="https://data.chain.link/streams/xrp-usd-twap-60s-streams");f=determine_dominance_legs(x4,.52,j,.522,min_corridor_bps=3.);assert f is not None;i,h=f["leg_a"]["token_id"],f["leg_b"]["token_id"];d.spots["XRP"]=.521;bks_live[i]={"bids":[{"price":"0.963","size":"80"}],"asks":[{"price":"0.999","size":"80"}]};bks_live[h]={"bids":[{"price":"0.018","size":"80"}],"asks":[{"price":"0.020","size":"80"}]};assert d.post_maker_anchor_candidate(x4,j,f,bks_live[i],bks_live[h],now_ts=g)is True;dk_x=f"D1_MKR_XRP_{x4.market_id}_{j.market_id}";assert d.pending_maker_anchors[dk_x]["bid_px"]==.964;bks_live[i]={"bids":[{"price":"0.963","size":"80"}],"asks":[{"price":"0.964","size":"40"}]};asyncio.run(d.manage_pending_maker_anchors(now_ts=g+1.));c=[p for p in d.open_positions.values()if p["dedupe_key"]==dk_x];assert len(c)==1 and c[0]["entry_eff_px_t1000"]<.988;assert c[0]["extra"]["legging_drag_usd_by_tier"]["T1000"]>.0
def test_overround_bid_unwind_ctf_merge_and_corridor_preservation(tmp_path,monkeypatch):
 import asyncio;import time;import src.polymarket_research.alpha_124_shadow_daemon as a124;from src.polymarket_research.macro_counting_ctf_engine import walk_position_overround_bid_unwind;from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor;f=walk_position_overround_bid_unwind([{"bids":[{"price":"0.52","size":"25"}],"fee_rate":.0,"fee_exponent":1.},{"bids":[{"price":"0.52","size":"15"}],"fee_rate":.0,"fee_exponent":1.}],exact_shares=25.,min_net_proceeds_per_set=1.005);assert f["filled"]is False,"Must reject partial unwind if any leg lacks 100% of exact_shares!";e=walk_position_overround_bid_unwind([{"bids":[{"price":"0.52","size":"40"}],"fee_rate":.0,"fee_exponent":1.},{"bids":[{"price":"0.51","size":"40"}],"fee_rate":.0,"fee_exponent":1.}],exact_shares=25.,min_net_proceeds_per_set=1.005);assert e["filled"]is True;assert abs(e["net_proceeds_per_set"]-1.03)<1e-6;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"st_uw.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"ld_uw.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"op_uw.json");monkeypatch.setattr(a124,"LIVE_ALPHA124_STATE_MIRROR_FILE",tmp_path/"mirror_uw.json");d=a124.Alpha124ShadowDaemon(single_scan=True);h=time.time();d.open_positions["FED1_TEST"]={"position_id":"FED1_TEST","dedupe_key":"FED1_DK","sleeve":"FED1_CENTRAL_BANK_LP_BOX","asset_or_city":"FOMC","title":"FOMC 2-Leg Box","side":"BOX","token_id":"tok_fomc_a+tok_fomc_b","fee_rate":.0,"entry_ts":h-60.,"close_ts":h+2e3*3600.,"entry_eff_px_t1000":.99,"p_model_entry":1.,"tier_fills":{"T100":{"shares":10.,"spent_usd":9.9,"fee_usd":.0},"T1000":{"shares":25.,"spent_usd":24.75,"fee_usd":.0}},"extra":{"is_two_leg_box":True,"guaranteed_payout":1.,"leg_a":{"token_id":"tok_fomc_a","market_id":"m_fomc_1","side":"YES","fee_rate":.0},"leg_b":{"token_id":"tok_fomc_b","market_id":"m_fomc_2","side":"NO","fee_rate":.0}}};d.open_positions["D1_NEAR_TEST"]={"position_id":"D1_NEAR_TEST","dedupe_key":"D1_NEAR_DK","sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","asset_or_city":"BTC","title":"BTC 15m/5m Corridor Box","side":"BOX","token_id":"tok_d1_a+tok_d1_b","fee_rate":.07,"entry_ts":h-45.,"close_ts":h+120.,"entry_eff_px_t1000":.98,"p_model_entry":1.,"tier_fills":{"T1000":{"shares":25.,"spent_usd":24.5,"fee_usd":.0}},"extra":{"guaranteed_payout":1.,"leg_a":{"token_id":"tok_d1_a","market_id":"m_d1_1","side":"UP","fee_rate":.07},"leg_b":{"token_id":"tok_d1_b","market_id":"m_d1_2","side":"DOWN","fee_rate":.07}}};d.open_positions["C1_MERGE_TEST"]={"position_id":"C1_MERGE_TEST","dedupe_key":"C1_DK","sleeve":"C1_BINARY_COMPLETE_SET","asset_or_city":"BTC","title":"BTC Single-Condition Complete Set","side":"COMPLETE_SET","token_id":"tok_c1_y+tok_c1_n","fee_rate":.0,"entry_ts":h-30.,"close_ts":h+7200.,"entry_eff_px_t1000":.985,"p_model_entry":1.,"tier_fills":{"T1000":{"shares":20.,"spent_usd":19.7,"fee_usd":.0}},"extra":{"guaranteed_payout":1.,"leg_a":{"token_id":"tok_c1_y","market_id":"m_c1_same","side":"YES","fee_rate":.0},"leg_b":{"token_id":"tok_c1_n","market_id":"m_c1_same","side":"NO","fee_rate":.0}}};books_map={"tok_fomc_a":{"bids":[{"price":"0.52","size":"50"}],"asks":[{"price":"0.54","size":"50"}]},"tok_fomc_b":{"bids":[{"price":"0.51","size":"50"}],"asks":[{"price":"0.53","size":"50"}]},"tok_d1_a":{"bids":[{"price":"0.53","size":"50"}],"asks":[{"price":"0.54","size":"50"}]},"tok_d1_b":{"bids":[{"price":"0.52","size":"50"}],"asks":[{"price":"0.53","size":"50"}]},"tok_c1_y":{"bids":[{"price":"0.49","size":"50"}],"asks":[{"price":"0.50","size":"50"}]},"tok_c1_n":{"bids":[{"price":"0.49","size":"50"}],"asks":[{"price":"0.50","size":"50"}]}}
 async def _fake_fetch(url,timeout=2.5):
  for tk,bk in books_map.items():
   if f"token_id={tk}"in url:return bk
  return None
 monkeypatch.setattr(d,"fetch_json",_fake_fetch);asyncio.run(d.manage_open_positions());assert"D1_NEAR_TEST"in d.open_positions,"Near-expiry D1 box must NOT unwind early on +3c overround; preserve $2.00 corridor!";assert"FED1_TEST"not in d.open_positions;assert"C1_MERGE_TEST"not in d.open_positions;a={c["position_id"]:c for c in d.closed_positions};assert a["FED1_TEST"]["status"]=="EARLY_OVERROUND_BID_UNWIND";assert abs(a["FED1_TEST"]["tier_pnls_usd"]["T1000"]-1.)<1e-6;assert a["C1_MERGE_TEST"]["status"]=="CTF_COMPLETE_SET_MERGED";assert abs(a["C1_MERGE_TEST"]["tier_pnls_usd"]["T1000"]-.3)<1e-6;ex=PolymarketLiveExecutor(dry_run=True,ledger_path=tmp_path/"merge_ex.jsonl");b="0x"+"cd"*32;g=ex.merge_complete_set_positions(b,25.,neg_risk=False);i=ex.merge_complete_set_positions(b,25.,neg_risk=True);assert g["merged"]is True and g["target_contract"].lower()==ex.CTF_ADDRESS.lower();assert g["calldata"].startswith("0x9e7212ad");assert i["merged"]is True and i["target_contract"].lower()==ex.NEG_RISK_ADAPTER_ADDRESS.lower();assert i["calldata"].startswith("0xb10c5c17")
def test_d1_quiet_book_graduation_and_close_position_growth_tier_promotion(tmp_path,monkeypatch):
 import json;import time;import src.polymarket_research.polymarket_live_harvester as harvester_mod;from src.polymarket_research.polymarket_live_harvester import ExecutionStatus,PolymarketLiveHarvester;e=tmp_path/"live_pm";e.mkdir(parents=True,exist_ok=True);monkeypatch.setattr(harvester_mod,"DATA_DIR",e);monkeypatch.setattr(harvester_mod,"STATE_FILE",e/"live_harvester_state.json");monkeypatch.setenv("PM_DISABLE_NYSE_BLACKOUT","1");(e/"alpha124_shadow_state.json").write_text(json.dumps({"by_sleeve":{"D1_SAME_ORACLE_DOMINANCE_BOX":{"closed":5,"win_rate_pct":1e2,"realized_pnl_t1000_usd":15.,"legging_adjusted_pnl_t1000_usd":12.},"D1_QUIET_BOOK_BOX":{"closed":13,"win_rate_pct":1e2,"realized_pnl_t1000_usd":43.25,"legging_adjusted_pnl_t1000_usd":42.18}},"by_d1_asset":{}}),encoding="utf-8");h=PolymarketLiveHarvester(dry_run=True,dynamic_sizing=True,hold_to_maturity=False,ticket_notional=12.,max_exposure=76.25,max_concurrent=2,allowed_assets={"BTC","ETH"});h.dry_run=False;h.executor.dry_run=False;h.executor.auth_mode="AUTHENTICATED_L2";h.executor.is_authenticated=True;h.executor.is_heartbeat_healthy=lambda:True;h.state_file=e/"live_harvester_state.json";h._startup_reconciled=True;h._last_known_collateral=138.98;h.high_water_mark_equity=138.98;h._update_equity_tier(138.98);assert h.current_equity_tier=="RECOVERY";tok_a="111111111111111111111111111111";i="222222222222222222222222222222";tok_b="333333333333333333333333333333";g="444444444444444444444444444444";j=time.time();d={"box_id":"D1_QUIET_BTC_1","dedupe_key":"D1_QB_BTC_1","box_type":"DOMINANCE","ts_unix":j,"expiry_ts":j+180.,"asset":"BTC","corridor_bps":8.,"k_low":8e4,"k_high":80064.,"is_quiet_book":True,"shares":25,"box_cost_net":.981,"max_box_cost_net":.985,"leg_a_token_id":tok_a,"leg_a_opp_token_id":i,"leg_a_label":"15M_UP","leg_a_side":"UP","leg_a_horizon":"15m","leg_a_market_id":"610001","leg_a_condition_id":"0x"+"11"*32,"leg_a_strike":8e4,"leg_a_limit_price":.47,"leg_a_avail_shares":120.,"leg_a_fee_rate":.07,"leg_a_fee_exponent":1.,"leg_b_token_id":tok_b,"leg_b_opp_token_id":g,"leg_b_label":"5M_DOWN","leg_b_side":"DOWN","leg_b_horizon":"5m","leg_b_market_id":"610002","leg_b_condition_id":"0x"+"22"*32,"leg_b_strike":80064.,"leg_b_limit_price":.47,"leg_b_avail_shares":120.,"leg_b_fee_rate":.07,"leg_b_fee_exponent":1.};a=h.maybe_execute_graduated_d1_box({**d,"sleeve_source":"D1_SAME_ORACLE_DOMINANCE_BOX","dedupe_key":"D1_CORE_BLK"});assert a["executed"]is False and a["reason"]=="D1_NOT_YET_8_OF_8_GRADUATED";qb_books={tok_a:{"asks":[{"price":"0.47","size":"120"}],"bids":[{"price":"0.45","size":"120"}]},tok_b:{"asks":[{"price":"0.47","size":"120"}],"bids":[{"price":"0.45","size":"120"}]},i:{"asks":[{"price":"0.55","size":"120"}],"bids":[{"price":"0.52","size":"120"}]},g:{"asks":[{"price":"0.55","size":"120"}],"bids":[{"price":"0.47","size":"120"}]}};h.executor.get_market_book=lambda tid:qb_books[tid];h._wallet_token_balance=lambda tid:(.0,h.ONCHAIN_SOURCE);captured_qb={}
 def _mock_qb_box(**kw):captured_qb.update(kw);sh=float(kw["shares"]);return{"success":True,"box_id":kw["box_id"],"shares":sh,"leg_1":{"token_id":tok_a,"label":kw["leg_a_label"],"price":.47,"orderID":"OID_QBA","raw":{"makingAmount":round(sh*.47,2)}},"leg_2":{"token_id":tok_b,"label":kw["leg_b_label"],"price":.47,"orderID":"OID_QBB","raw":{"makingAmount":round(sh*.47,2)}}}
 h.executor.execute_atomic_dominance_box=_mock_qb_box;c=h.maybe_execute_graduated_d1_box({**d,"sleeve_source":"D1_QUIET_BOOK_BOX"});assert c["executed"]is True;assert captured_qb["parallel_dispatch"]is False,"Tighter (0.975..0.985] quiet box must preserve sequential Leg-1 dispatch!";assert h.active_positions["D1_QUIET_BTC_1_L1"]["sleeve_source"]=="D1_QUIET_BOOK_BOX";h.active_positions.clear();h._last_known_collateral=108.78;h.active_positions["LIVE_WIN_141"]={"trade_id":"LIVE_WIN_141","token_id":"tok_eth_up","target_token":"UP","asset":"ETH","entry_price":.85,"entry_shares":35.,"remaining_shares":.0,"filled_exit_shares":35.,"notional_usd":29.75,"fee_usd":.45,"confirmed_realized_cash":32.9,"realized_exit_cash":32.9,"realized_exit_fee":.0,"entry_ts":j-120.,"candle_expiry_ts":j+1800.,"status":ExecutionStatus.POSITION_CONFIRMED};f=h._close_position("LIVE_WIN_141",h.active_positions["LIVE_WIN_141"],ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True);assert abs(f-2.7)<1e-2;assert h.current_equity_tier=="GROWTH";assert abs(h.max_exposure-106.26)<1e-2;assert h.max_concurrent_positions==3;assert abs(h.dynamic_bankroll_pct-.26)<1e-6;b=json.loads((e/"live_harvester_state.json").read_text(encoding="utf-8"));assert b["equity_tier"]=="GROWTH";assert abs(float(b["max_exposure"])-106.26)<1e-2;assert int(b["max_concurrent_positions"])==3
def test_bond1_uma_resolution_carry_onchain_and_settlement_guard(tmp_path,monkeypatch):
 import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124;import src.polymarket_research.uma_nba_endgame_engine as uma_mod;from src.polymarket_research.uma_nba_endgame_engine import(HALF_E18,ONE_E18,is_objective_uma_market,verify_uma_onchain_proposal_sync);base_mkt={"id":"990001","conditionId":"0x"+"aa"*32,"questionID":"0x"+"bb"*32,"negRisk":True,"negRiskRequestID":"0x"+"cc"*32,"resolvedBy":"0x69c47De9D4D3Dad79590d61b9e05918E03775f24","closed":False,"archived":False,"acceptingOrders":True,"umaResolutionStatus":"proposed","umaResolutionStatuses":'["proposed"]',"outcomes":'["Yes", "No"]',"outcomePrices":'["0.004", "0.996"]',"clobTokenIds":'["tok_uma_yes", "tok_uma_no"]',"question":"Will the highest temperature in Tokyo be 21°C on October 28?","description":"Resolves via https://aviationweather.gov/api/data/metar?ids=RJTT routine METAR; SPECI excluded.","feesEnabled":False};k,i=is_objective_uma_market(base_mkt);assert k is True and i=="VERIFIED_PRIMARY_ORACLE";h,f=is_objective_uma_market({**base_mkt,"question":'Will Trump say "Tariff" during his speech?'});assert h is False and f=="SUBJECTIVE_OR_SPEECH_VETO";c,b=is_objective_uma_market({**base_mkt,"umaResolutionStatuses":'["proposed", "disputed", "proposed"]'});assert c is False and b=="PRIOR_DISPUTE_HISTORY";a,e=is_objective_uma_market({**base_mkt,"negRiskRequestID":""});assert a is False and e=="MISSING_REQUEST_ID"
 def _build_gq_hex(req_ts,anc,reset=False):a=[b"\x00"*32 for _ in range(13)];a[1]=req_ts.to_bytes(32,"big");a[4]=(7200).to_bytes(32,"big");a[8]=(1 if reset else 0).to_bytes(32,"big");a[12]=(12*32).to_bytes(32,"big");b=b"\x00"*((32-len(anc)%32)%32);return"0x"+b"".join(a).hex()+len(anc).to_bytes(32,"big").hex()+(anc+b).hex()
 def _build_rq_hex(proposer_hex,disputer_hex,prop_price,exp_ts):w=[b"\x00"*32 for _ in range(16)];w[0]=bytes.fromhex(proposer_hex.replace("0x","").rjust(64,"0"));w[1]=bytes.fromhex(disputer_hex.replace("0x","").rjust(64,"0"));w[10]=(7200).to_bytes(32,"big");a=prop_price if prop_price>=0 else(1<<256)+prop_price;w[11]=a.to_bytes(32,"big");w[13]=exp_ts.to_bytes(32,"big");return"0x"+b"".join(w).hex()
 now_u=1.7932e9;g=int(now_u+3600);anc_b=b"q: title: Tokyo 21C, res_data: p1: 0, p2: 1, p3: 0.5.";oo_addr_hex="0x"+"2c0367a9db231ddebd88a94b4f6461a6e47c58b1".rjust(64,"0");prop_addr="0x"+"11"*20;rpc_state={"oo_state":2,"disputer":uma_mod.ZERO_ADDR,"price":0,"reset":False,"exp":g}
 def _fake_rpc_post(rpc_url,payload,timeout=5.):
  c=[]
  for a in payload:
   b=a["id"]
   if b==1:c.append({"id":1,"result":_build_gq_hex(1793190000,anc_b,reset=rpc_state["reset"])})
   elif b==2:c.append({"id":2,"result":oo_addr_hex})
   elif b==10:c.append({"id":10,"result":hex(rpc_state["oo_state"])})
   elif b==11:c.append({"id":11,"result":_build_rq_hex(prop_addr,rpc_state["disputer"],rpc_state["price"],rpc_state["exp"])})
  return c
 uma_mod._OO_ADDR_CACHE.clear();monkeypatch.setattr(uma_mod,"_rpc_post",_fake_rpc_post);j=verify_uma_onchain_proposal_sync(base_mkt,rpc_url="http://mock",now_ts=now_u);assert j["verified"]is True;assert j["win_index"]==1 and j["win_outcome_name"]=="No"and j["win_token"]=="tok_uma_no";rpc_state["disputer"]="0x"+"99"*20;assert verify_uma_onchain_proposal_sync(base_mkt,rpc_url="http://mock",now_ts=now_u)["verified"]is False;rpc_state["disputer"]=uma_mod.ZERO_ADDR;rpc_state["price"]=HALF_E18;assert verify_uma_onchain_proposal_sync(base_mkt,rpc_url="http://mock",now_ts=now_u)["reason"]=="TIE_50_50_PROPOSAL_VETO";rpc_state["price"]=0;rpc_state["reset"]=True;assert verify_uma_onchain_proposal_sync(base_mkt,rpc_url="http://mock",now_ts=now_u)["verified"]is False;rpc_state["reset"]=False;rpc_state["exp"]=int(now_u+7150);assert"PROPOSAL_TOO_FRESH"in verify_uma_onchain_proposal_sync(base_mkt,rpc_url="http://mock",now_ts=now_u)["reason"];rpc_state["exp"]=g;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"b1_state.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"b1_ledger.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"b1_opps.json");gamma_resolved={"done":False}
 async def _run_bond_sim():
  d=a124.Alpha124ShadowDaemon(single_scan=True);d.uma_proposed_markets={"990001":base_mkt};d.last_uma_discovery_ts=now_u
  async def _fake_disc(ts):d.uma_proposed_markets={"990001":base_mkt}
  async def _fake_fetch(url,timeout=4.):
   if"tok_uma_no"in url:return{"bids":[{"price":"0.991","size":"500"}],"asks":[{"price":"0.992","size":"500"}]}
   if"tok_uma_yes"in url:return{"bids":[{"price":"0.001","size":"200"}],"asks":[{"price":"0.004","size":"500"}]}
   if"/markets/990001"in url:
    if gamma_resolved["done"]:return{**base_mkt,"closed":True,"umaResolutionStatus":"resolved","outcomePrices":'["0", "1"]'}
    return{**base_mkt,"closed":False,"umaResolutionStatus":"proposed"}
   return None
  async def _fake_batch(toks,timeout=3.5):return{t:await _fake_fetch(t)for t in toks}
  monkeypatch.setattr(d,"discover_uma_proposed_markets",_fake_disc);monkeypatch.setattr(d,"fetch_json",_fake_fetch);monkeypatch.setattr(d,"fetch_books_batch",_fake_batch);a=[];await d.scan_uma_resolution_bonds(a,now_ts=now_u);assert len(d.open_positions)==1;c=next(iter(d.open_positions));b=d.open_positions[c];assert b["sleeve"]=="BOND1_UMA_RESOLUTION_CARRY";assert abs(float(b["entry_eff_px_t1000"])-.992)<1e-4;b["close_ts"]=time.time()-120.;await d.manage_open_positions();assert c in d.open_positions,"BOND1 must NEVER self-settle on CLOB best_bid >= 0.99 while UMA is still proposed!";gamma_resolved["done"]=True;await d.manage_open_positions();assert c not in d.open_positions;assert d.closed_positions[-1]["won"]is True;assert abs(d.closed_positions[-1]["tier_pnls_usd"]["T1000"]-round(120./.992-120.,2))<.05
 import time;asyncio.run(_run_bond_sim())
def test_w1_v2_cape_town_fact_and_low_trough_lock_cold_front_veto():
 from datetime import date;from src.polymarket_research.weather_metar_engine import(HIGH_VOLUME_WEATHER_SERIES,STATION_CATALOG,WeatherBucket,WeatherEventSpec,compute_weather_probabilities,parse_metar_line,parse_weather_event);assert"FACT"in STATION_CATALOG
 for o in("atlanta-daily-weather","san-francisco-daily-weather","seattle-daily-weather","amsterdam-daily-weather","cape-town-daily-weather","tokyo-daily-lowest-temperature"):assert o in HIGH_VOLUME_WEATHER_SERIES
 ev_fact={"id":"ev_fact_1","title":"Highest temperature in Cape Town on October 29?","series":[{"slug":"cape-town-daily-weather"}],"endDate":"2026-10-29T22:00:00Z","markets":[{"id":f"m_{i}","conditionId":f"0x{i}","groupItemTitle":lbl,"clobTokenIds":f'["y_{i}", "n_{i}"]',"description":"Resolves to the highest temperature recorded in a routine (METAR) observation for Cape Town International Airport (FACT) on October 29, 2026. SPECI reports are excluded."}for i,lbl in enumerate(["18°C or below","19°C","20°C","21°C or higher"])]};l=parse_weather_event(ev_fact);assert l is not None and l.icao=="FACT"and l.city=="Cape Town";c={**ev_fact,"markets":[{**m,"description":"Resolves via Wunderground station history for Cape Town (FACT)."}for m in ev_fact["markets"]]};assert parse_weather_event(c,allow_historical_same_station=False)is None;j=datetime(2026,10,29,2,0,tzinfo=timezone.utc);b=parse_metar_line("METAR RJTT 282000Z 34008KT 9999 FEW030 12/06 Q1018 RMK T01200060","RJTT",j,"Asia/Tokyo");g=parse_metar_line("METAR RJTT 290200Z 02009KT 9999 FEW035 15/07 Q1019 RMK T01540070","RJTT",j,"Asia/Tokyo");assert b is not None and g is not None;k=[WeatherBucket("b1","c1","11°C or below","11C-","y1","n1","C",float("-inf"),11.),WeatherBucket("b2","c2","12°C","12C","y2","n2","C",12.,12.),WeatherBucket("b3","c3","13°C","13C","y3","n3","C",13.,13.),WeatherBucket("b4","c4","14°C or higher","14C+","y4","n4","C",14.,float("inf"))];n=WeatherEventSpec(event_id="ev_rjtt_low",slug="tokyo-low-oct-29",series_slug="tokyo-daily-lowest-temperature",title="Lowest temperature in Tokyo on October 29?",icao="RJTT",city="Tokyo",lat=35.5523,lon=139.7798,tz_name="Asia/Tokyo",obs_date=date(2026,10,29),metric="LOW",unit="C",fee_type="zero_fees",end_date_iso="2026-10-29T15:00:00Z",buckets=k);base_hr=int(j.timestamp());f={base_hr+h*3600:[15.5+.02*m for m in range(40)]for h in range(0,14)};e=compute_weather_probabilities(n,j,[b,g],f);assert e["is_solar_lock"]is True and e["locked_bucket_idx"]==1 and e["p_locked_bucket"]>=.93;a={base_hr+h*3600:([13.2+.05*m for m in range(40)]if h==11 else[15.5 for _ in range(40)])for h in range(0,14)};d=compute_weather_probabilities(n,j,[b,g],a);assert d["is_solar_lock"]is False
def test_sp2_nba_endgame_lock_espn_parser_and_overtime_trap_veto():from src.polymarket_research.tradfi_sports_zero_fee_engine import NbaGameSpec,NbaOutcomeLeg;from src.polymarket_research.uma_nba_endgame_engine import(LiveNbaGameState,evaluate_nba_endgame_locks,match_nba_live_game,parse_espn_nba_scoreboard,verify_uma_against_nba_live);b={"events":[{"id":"401700001","date":"2026-10-29T00:00Z","competitions":[{"date":"2026-10-29T00:00Z","status":{"clock":35.,"displayClock":"0:35","period":4,"type":{"state":"in","completed":False}},"competitors":[{"homeAway":"home","score":"114","team":{"name":"Celtics","abbreviation":"BOS"}},{"homeAway":"away","score":"103","team":{"name":"Heat","abbreviation":"MIA"}}]}]}]};m=parse_espn_nba_scoreboard(b);assert len(m)==1 and m[0].home_score==114 and m[0].away_score==103 and m[0].clock_sec==35.;k=1793232000.;m[0].start_ts=k;o=NbaGameSpec(event_id="nba_1",slug="nba-mia-bos",title="Heat vs. Celtics",team_a="Heat",team_b="Celtics",tipoff_ts=k,settle_est_ts=k+9600.,margin_legs=[NbaOutcomeLeg("m_ml","c_ml","moneyline","tok_mia","tok_bos",0,"YES","ML Heat","GT",.0),NbaOutcomeLeg("m_ml","c_ml","moneyline","tok_bos","tok_mia",1,"NO","ML Celtics","LT",.0),NbaOutcomeLeg("m_sp","c_sp","spreads","tok_mia_p75","tok_bos_m75",0,"YES","Heat +7.5","GT",-7.5),NbaOutcomeLeg("m_sp","c_sp","spreads","tok_bos_m75","tok_mia_p75",1,"NO","Celtics -7.5","LT",-7.5)],total_legs=[NbaOutcomeLeg("m_tot","c_tot","totals","tok_ov","tok_un",0,"YES","Over 214.5","OVER",214.5),NbaOutcomeLeg("m_tot","c_tot","totals","tok_un","tok_ov",1,"NO","Under 214.5","UNDER",214.5)]);g=match_nba_live_game(o,m);assert g is not None;n,j,i=g;assert j==103 and i==114;f,e=verify_uma_against_nba_live({"question":"Heat vs. Celtics","sportsMarketType":"moneyline","outcomes":'["Heat", "Celtics"]',"gameStartTime":"2026-10-29T00:00:00Z"},1,m);assert f is False and e=="NBA_GAME_NOT_FINAL_YET";locks_q4=evaluate_nba_endgame_locks(o,n,j,i);a={c["leg"].display_label:c for c in locks_q4};assert"Over 214.5"in a and a["Over 214.5"]["mode"]=="LIVE_TOTAL_OVER_LOCKED";assert"ML Celtics"in a and a["ML Celtics"]["p_lock"]>=.993;assert"Celtics -7.5"not in a;h=LiveNbaGameState("401",k,"in",False,4,10.,"Celtics","BOS",105,"Heat","MIA",105);locks_tied=evaluate_nba_endgame_locks(o,h,105,105);assert all(c["leg"].display_label!="Heat +7.5"for c in locks_tied),"Must veto +7.5 spread when tied (Overtime trap)!";l=LiveNbaGameState("401",k,"post",True,4,.0,"Celtics","BOS",114,"Heat","MIA",103);locks_fin=evaluate_nba_endgame_locks(o,l,103,114);d={c["leg"].display_label for c in locks_fin};assert{"ML Celtics","Celtics -7.5","Over 214.5"}<=d
def test_focus_upgrades_locked_maker_depth_cap_and_tight_zf_boxes(tmp_path,monkeypatch):
 import asyncio;import io;import json;import time;import urllib.request;import src.polymarket_research.alpha_124_shadow_daemon as a124;import src.polymarket_research.uma_nba_endgame_engine as u_eng;monkeypatch.setattr(a124,"STATE_FILE",tmp_path/"foc_st.json");monkeypatch.setattr(a124,"LEDGER_FILE",tmp_path/"foc_ldg.jsonl");monkeypatch.setattr(a124,"OPPS_FILE",tmp_path/"foc_opps.json");monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","0");seen_urls=[]
 class _FakeResp(io.BytesIO):
  def __enter__(self):return self
  def __exit__(self,*args):pass
 def _fake_urlopen(req,timeout=4.5):u=req.full_url if hasattr(req,"full_url")else str(req);seen_urls.append(u);a="401_YEST"if len(seen_urls)==1 else"401_TODAY";ev={"events":[{"id":a,"date":"2026-10-29T02:00Z","status":{"period":4,"clock":18.,"type":{"state":"in","completed":False}},"competitions":[{"competitors":[{"homeAway":"home","score":"112","team":{"shortDisplayName":"Lakers","abbreviation":"LAL"}},{"homeAway":"away","score":"101","team":{"shortDisplayName":"Suns","abbreviation":"PHX"}}]}]}]};return _FakeResp(json.dumps(ev).encode("utf-8"))
 monkeypatch.setattr(urllib.request,"urlopen",_fake_urlopen);games_dual=u_eng.fetch_espn_nba_scoreboard_sync(now_ts=1.79325e9);assert len(seen_urls)==2 and all("?dates="in u for u in seen_urls);assert{g.game_id for g in games_dual}=={"401_YEST","401_TODAY"}
 async def _run_focus():
  d=a124.Alpha124ShadowDaemon(single_scan=True);o=time.time();bk_wellington={"bids":[{"price":"0.60","size":"50"}],"asks":[{"price":"0.768","size":"24.0"}]};bk_milan_empty_ask={"bids":[{"price":"0.87","size":"120"}],"asks":[]};bk_uma_empty_ask={"bids":[{"price":"0.991","size":"500"}],"asks":[]};tape_state={"uma_created_ts":o}
  async def _fake_fetch_tape(url,timeout=3.):
   if"token_id=tok_nzwn_y"in url:return bk_wellington
   if"token_id=tok_uma_w"in url:return bk_uma_empty_ask
   if"token_id=tok_uma_l"in url:return{"bids":[{"price":"0.001","size":"100"}],"asks":[]}
   if"token_id=tok_limc_y"in url:return bk_milan_empty_ask
   if"data-api.polymarket.com/trades?market=0xcond_uma"in url:a=int(tape_state["uma_created_ts"]);return[{"timestamp":a-5,"asset":"tok_uma_w","price":.99,"size":500,"transactionHash":"0xold"},{"timestamp":a+5,"asset":"tok_uma_w","price":.992,"size":25.,"transactionHash":"0xfresh"}]
   return[]
  monkeypatch.setattr(d,"fetch_json",_fake_fetch_tape);n=await d.open_shadow_position(sleeve="W1_LOW_TROUGH_LOCK",dedupe_key="W1LOW_NZWN_13C",asset_or_city="Wellington_NZWN",title="Wellington Lowest Temp [13°C]",side_label="YES",token_id="tok_nzwn_y",fee_rate=.0,p_model=.99,close_ts=o+14400.,extra={"condition_id":"0xcond_nzwn"},prefetched_book=bk_wellington);assert n is True;m=next(p for p in d.open_positions.values()if p["dedupe_key"]=="W1LOW_NZWN_13C");assert m["tier_fills"]["T100"]["spent_usd"]==15.;assert m["tier_fills"]["T1000"]["spent_usd"]==18.43;assert m["tier_fills"]["T1000"]["depth_capped"]is True;b=await d.post_shadow_maker_entry(sleeve="W1_LOW_TROUGH_LOCK",dedupe_key="W1LOW_LIMC_5C",asset="Milan_LIMC",title="Milan Lowest Temp [5°C]",side_label="YES",token_id="tok_limc_y",p_model=.99,close_ts=o+21600.,extra={"condition_id":"0xcond_limc","opp_token_id":"tok_limc_n"},prefetched_book=bk_milan_empty_ask);assert b is True;l=next(v for v in d.pending_maker_orders.values()if v["dedupe_key"]=="W1LOW_LIMC_5C");assert l["resting_bid"]==.88 and l["queue_ahead_usd"]==.0;a=await d.post_shadow_maker_entry(sleeve="BOND1_UMA_RESOLUTION_CARRY",dedupe_key="BOND1_NBA_FIN",asset="SPORTS",title="Celtics vs Heat [Celtics]",side_label="YES",token_id="tok_uma_w",p_model=1.,close_ts=o+3600.,extra={"condition_id":"0xcond_uma","opp_token_id":"tok_uma_l"},prefetched_book=bk_uma_empty_ask);assert a is True;g=next(v for v in d.pending_maker_orders.values()if v["dedupe_key"]=="BOND1_NBA_FIN");assert g["resting_bid"]==.992;g["created_ts"]=o-20.;l["created_ts"]=o-20.;tape_state["uma_created_ts"]=g["created_ts"];await d.manage_pending_maker_orders();f=[p for p in d.open_positions.values()if p["dedupe_key"]=="BOND1_NBA_FIN"];assert len(f)==1;assert f[0]["maker_tp_px"]is None;assert f[0]["extra"].get("filled_via_trade_tape")is True;assert f[0]["tier_fills"]["T100"]["shares"]==round(20./.992,4);assert f[0]["tier_fills"]["T1000"]["shares"]==25.;k={"token_id":"sp1_a","opp_token_id":"sp1_ao","condition_id":"0xsp1","side":"YES","label":"Suns +4.5","market_id":"msp1","fee_rate":.0};j={"token_id":"sp1_b","opp_token_id":"sp1_bo","condition_id":"0xsp2","side":"YES","label":"Lakers -2.5","market_id":"msp2","fee_rate":.0};e={"bids":[{"price":"0.43","size":"120"}],"asks":[{"price":"0.44","size":"100"}]};c={"bids":[{"price":"0.43","size":"120"}],"asks":[{"price":"0.55","size":"100"}]};c["bids"]=[{"price":"0.54","size":"120"}];i=d.post_zero_fee_maker_anchor_box("SP1_NBA","NBA","ZFA_TIGHT_1C",k,j,e,c,o+5400.,"Suns vs Lakers",o);assert i is True;h=d.pending_zero_fee_maker_anchors["ZFA_TIGHT_1C"];assert h["queue_front"]is False and h["pair_est"]==.98
 asyncio.run(_run_focus())
def test_sp3_sports_corridor_and_negrisk_convert_sleeves(monkeypatch,tmp_path):
 from src.polymarket_research.tradfi_sports_zero_fee_engine import(parse_multi_sport_corridor_event,detect_multi_sport_corridor_boxes,parse_negrisk_convert_event,detect_negrisk_no_pair_boxes,detect_negrisk_convert_positions_arbs);from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon;k={"id":"ev_sp3_1","slug":"nfl-kc-buf-2026-11-01","title":"Chiefs vs. Bills","endDate":"2026-11-02T01:00:00Z","markets":[{"id":"901001","conditionId":"0xc1","sportsMarketType":"spreads","line":-2.5,"question":"Spread: Chiefs (-2.5)","outcomes":'["Chiefs", "Bills"]',"clobTokenIds":'["111111111111111111111", "111111111111111111112"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True},{"id":"901002","conditionId":"0xc2","sportsMarketType":"spreads","line":-6.5,"question":"Spread: Chiefs (-6.5)","outcomes":'["Chiefs", "Bills"]',"clobTokenIds":'["222222222222222222221", "222222222222222222222"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True},{"id":"901003","conditionId":"0xc3","sportsMarketType":"totals","line":44.5,"question":"Chiefs vs. Bills: O/U 44.5","outcomes":'["Over", "Under"]',"clobTokenIds":'["333333333333333333331", "333333333333333333332"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True},{"id":"901004","conditionId":"0xc4","sportsMarketType":"totals","line":48.5,"question":"Chiefs vs. Bills: O/U 48.5","outcomes":'["Over", "Under"]',"clobTokenIds":'["444444444444444444441", "444444444444444444442"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True},{"id":"901005","conditionId":"0xc5","sportsMarketType":"totals","line":46.,"question":"Chiefs vs. Bills: O/U 46.0","outcomes":'["Over", "Under"]',"clobTokenIds":'["555555555555555555551", "555555555555555555552"]',"feeType":"sports_fees_nfl_cfb_oct26","feesEnabled":True}]};sp_spec=parse_multi_sport_corridor_event(k);assert sp_spec is not None and sp_spec.sport=="NFL";assert len(sp_spec.legs)==8;assert"901005"not in{lg.market_id for lg in sp_spec.legs};assert all(abs(lg.fee_rate-.03)<1e-9 for lg in sp_spec.legs);a={"111111111111111111111":.46,"222222222222222222222":.49,"333333333333333333331":.47,"444444444444444444442":.48};cands_sp3=detect_multi_sport_corridor_boxes(sp_spec,a,max_box_cost_net=.985);assert len(cands_sp3)==2;assert all(.95<c["box_cost_net"]<=.985 for c in cands_sp3);p={"id":"ev_nba_1h","slug":"nba-bos-mia-2026-11-01","title":"Celtics vs. Heat","endDate":"2026-11-02T01:00:00Z","markets":[{"id":"902001","conditionId":"0xn1","sportsMarketType":"first_half_spreads","line":-1.5,"question":"1H Spread: Celtics (-1.5)","outcomes":'["Celtics", "Heat"]',"clobTokenIds":'["611111111111111111111", "611111111111111111112"]',"feesEnabled":False},{"id":"902002","conditionId":"0xn2","sportsMarketType":"first_half_spreads","line":-4.5,"question":"1H Spread: Celtics (-4.5)","outcomes":'["Celtics", "Heat"]',"clobTokenIds":'["622222222222222222221", "622222222222222222222"]',"feesEnabled":False},{"id":"902003","conditionId":"0xn3","sportsMarketType":"spreads","line":-3.5,"question":"Spread: Celtics (-3.5)","outcomes":'["Celtics", "Heat"]',"clobTokenIds":'["633333333333333333331", "633333333333333333332"]',"feesEnabled":False},{"id":"902004","conditionId":"0xn4","sportsMarketType":"spreads","line":-7.5,"question":"Spread: Celtics (-7.5)","outcomes":'["Celtics", "Heat"]',"clobTokenIds":'["644444444444444444441", "644444444444444444442"]',"feesEnabled":False}]};m=parse_multi_sport_corridor_event(p,skip_nba_fg_zero_fee=True);l={"611111111111111111111":.48,"622222222222222222222":.49,"633333333333333333331":.48,"644444444444444444442":.49};j=detect_multi_sport_corridor_boxes(m,l,max_box_cost_net=.988);assert len(j)==1 and j[0]["scope"]=="1H:SPREAD";d={"id":"ev_nr_closed","slug":"fed-chair-vote-margin","title":"Vote Margin Partition","enableNegRisk":True,"negRiskAugmented":False,"negRiskMarketID":"0x"+"ab"*32,"endDate":"2026-11-05T18:00:00Z","markets":[{"id":"910001","conditionId":"0xd1","negRisk":True,"groupItemTitle":"Bucket A","questionID":"0x"+"ab"*31+"00","clobTokenIds":'["711111111111111111111", "711111111111111111112"]',"feesEnabled":False},{"id":"910002","conditionId":"0xd2","negRisk":True,"groupItemTitle":"Bucket B","questionID":"0x"+"ab"*31+"01","clobTokenIds":'["722222222222222222221", "722222222222222222222"]',"feesEnabled":False},{"id":"910003","conditionId":"0xd3","negRisk":True,"groupItemTitle":"Bucket C","questionID":"0x"+"ab"*31+"02","clobTokenIds":'["733333333333333333331", "733333333333333333332"]',"feesEnabled":False}]};i=parse_negrisk_convert_event(d);assert i is not None and i.is_closed_convert_safe is True;bks_nr={"711111111111111111112":{"asks":[{"price":"0.46","size":"100"}]},"722222222222222222222":{"asks":[{"price":"0.51","size":"100"}]},"733333333333333333331":{"bids":[{"price":"0.08","size":"100"}]},"733333333333333333332":{"asks":[{"price":"0.94","size":"100"}]}};f={"711111111111111111112":.46,"722222222222222222222":.51,"733333333333333333332":.94};b=detect_negrisk_no_pair_boxes(i,f,max_box_cost_net=.99);assert len(b)==1 and abs(b[0]["box_cost_net"]-.97)<1e-6;e=detect_negrisk_convert_positions_arbs(i,bks_nr,min_net_edge_per_share=.012);assert len(e)>=1 and e[0]["net_edge_per_share"]>.08;h=dict(d,id="ev_nr_aug",negRiskAugmented=True);o=parse_negrisk_convert_event(h);assert o is not None and o.is_closed_convert_safe is False;assert len(detect_negrisk_no_pair_boxes(o,f,max_box_cost_net=.99))==1;assert detect_negrisk_convert_positions_arbs(o,bks_nr,min_net_edge_per_share=.012)==[];import asyncio;import src.polymarket_research.alpha_124_shadow_daemon as a124_mod;monkeypatch.setattr(a124_mod,"STATE_FILE",tmp_path/"a124_q.json");monkeypatch.setattr(a124_mod,"LEDGER_FILE",tmp_path/"a124_q_ledger.jsonl");monkeypatch.setenv("PM_QUARANTINE_LOSING_SLEEVES","1");n=Alpha124ShadowDaemon(single_scan=False);n.twap_candles={"dummy":1};asyncio.run(n.scan_exact_twap_locks([]));assert n.twap_candles=={};n._apply_ws_book_snapshot("tok_lazy",[{"price":"0.45","size":"50"}],[{"price":"0.47","size":"50"}],1e3);assert n._apply_ws_price_changes("tok_lazy",[{"price":"0.46","size":"60","side":"BUY"}],1001.)is True;assert"tok_lazy"in n._ws_books._dirty;q=n._ws_books["tok_lazy"];assert q[0]==1001. and q[1]["bids"][0]["price"]=="0.4600"
 async def _mock_fetch_batch(toks,timeout=3.):return bks_nr
 n.fetch_books_batch=_mock_fetch_batch;g=[];assert asyncio.run(n.execute_negrisk_convert_positions_arb(i,e[0],bks_nr,g))is True;assert n.closed_positions[-1]["sleeve"]=="NR_CONV_NO_BASKET_ARB"and n.closed_positions[-1]["won"]is True
def test_riskless_frontier_v2_all_six_sleeves(monkeypatch,tmp_path):
 from src.polymarket_research.riskless_frontier_v2_engine import(MOOV2_ORACLE_ADDR,build_lp1_bop_2026_truth_legs,build_lp1_nba_exact_margin_bundle,detect_nr2_convert_no_subset_arbs,detect_soc1_regulation_boxes,detect_sp4_milestone_ladder_boxes,evaluate_api1_esports_bo3_opportunities,evaluate_sp4_ingame_clinch_locks,find_state_matrix_dominance_boxes,link_and_parse_soccer_regulation_trees,parse_espn_nba_boxscore_players,parse_esports_bo3_event,parse_nba_player_props_from_event,verify_bond2_moov2_final_hour_sync);from src.polymarket_research.tradfi_sports_zero_fee_engine import(detect_negrisk_convert_positions_arbs,parse_negrisk_convert_event);from src.polymarket_research.uma_nba_endgame_engine import LiveNbaGameState;import src.polymarket_research.riskless_frontier_v2_engine as rfv2;z={"id":"ev_nr5","slug":"closed-5way-slate","title":"Closed 5-Way Slate","enableNegRisk":True,"negRiskAugmented":False,"negRiskMarketID":"0x"+"cd"*32,"endDate":"2026-11-10T18:00:00Z","markets":[{"id":f"92000{i}","conditionId":f"0xe{i}","negRisk":True,"active":True,"groupItemTitle":f"Contender {i}","questionID":"0x"+"cd"*31+f"0{i}","clobTokenIds":f'["8{i}1111111111111111111", "8{i}2222222222222222222"]',"feesEnabled":False}for i in range(5)]};I=parse_negrisk_convert_event(z);assert I is not None and I.is_closed_convert_safe is True;E={**z,"markets":[*z["markets"][:4],{**z["markets"][4],"groupItemTitle":"Party A"}]};assert parse_negrisk_convert_event(E).is_closed_convert_safe is False;p={"802222222222222222222":{"asks":[{"price":"0.48","size":"100"}]},"812222222222222222222":{"asks":[{"price":"0.56","size":"100"}]},"821111111111111111111":{"bids":[{"price":"0.08","size":"100"}]},"831111111111111111111":{"bids":[]},"841111111111111111111":{"bids":[]}};assert detect_negrisk_convert_positions_arbs(I,p)==[];h=detect_nr2_convert_no_subset_arbs(I,p,target_budget_usd=1e2);assert len(h)==1;assert h[0]["m_no_legs"]==2 and h[0]["retained_tail_count"]==2;assert abs(h[0]["net_edge_per_share"]-.04)<1e-4;y={"id":"ev_nba_sp4","slug":"nba-sas-uta-2026-10-30","title":"Spurs vs. Jazz","startTime":"2026-10-30T23:00:00Z","markets":[{"id":"p1","conditionId":"0xc1","sportsMarketType":"points","line":23.5,"feeType":"zero_fees","groupItemTitle":"Victor Wembanyama: Points O/U 23.5","outcomes":'["Yes", "No"]',"clobTokenIds":'["90011", "90012"]'},{"id":"p2","conditionId":"0xc2","sportsMarketType":"points","line":27.5,"feeType":"zero_fees","groupItemTitle":"Victor Wembanyama: Points O/U 27.5","outcomes":'["Yes", "No"]',"clobTokenIds":'["90021", "90022"]'}]};w=parse_nba_player_props_from_event(y);assert w is not None;H=detect_sp4_milestone_ladder_boxes(w,{"90011":.61,"90022":.37},max_box_cost_net=.992);assert len(H)==1 and abs(H[0]["box_cost_net"]-.98)<1e-6;d={"boxscore":{"players":[{"statistics":[{"keys":["minutes","points","rebounds","assists","threePointFieldGoalsMade-threePointFieldGoalsAttempted"],"athletes":[{"athlete":{"displayName":"Victor Wembanyama"},"didNotPlay":False,"stats":["28","24","9","4","3-7"]},{"athlete":{"displayName":"DNP Bench"},"didNotPlay":True,"stats":["0","30","0","0","0-0"]}]}]}]}};o=parse_espn_nba_boxscore_players(d);assert"dnp bench"not in o and o["victor wembanyama"]["points"]==24;G=LiveNbaGameState("g1",1e3,"in",False,3,120.,"Jazz","UTA",80,"Spurs","SAS",84);v=LiveNbaGameState("g1",1e3,"post",True,4,.0,"Jazz","UTA",102,"Spurs","SAS",108);assert evaluate_sp4_ingame_clinch_locks(w,G,o)==[];assert len(evaluate_sp4_ingame_clinch_locks(w,v,o))==1;o["victor wembanyama"]["points"]=25;assert len(evaluate_sp4_ingame_clinch_locks(w,G,o))==1;monkeypatch.setattr(rfv2,"verify_uma_onchain_proposal_sync",lambda m,**kw:{"verified":True,"adapter":"0x65070be91477460d8a7aeeb94ef92fe056c2f2a7","oo_address":MOOV2_ORACLE_ADDR,"proposer":"0x"+"11"*20,"proposal_age_sec":4200.,"rem_challenge_sec":1800.,"win_index":0,"win_label":"YES","win_outcome_name":"Yes","win_token":"t_w","lose_token":"t_l","expiration_ts":5e3,"fee_rate":.0,"fee_exponent":1.,"domain":"SPORTS_POINTS","oo_state":2});monkeypatch.setattr(rfv2,"verify_proposer_whitelisted_sync",lambda addr,**kw:addr.endswith("1111"));assert verify_bond2_moov2_final_hour_sync({"id":"m_b2"})["verified"]is True;monkeypatch.setattr(rfv2,"verify_proposer_whitelisted_sync",lambda addr,**kw:False);assert verify_bond2_moov2_final_hour_sync({"id":"m_b2"})["reason"]=="PROPOSER_NOT_WHITELISTED";u={"id":"s3","slug":"epl-ars-che-2026-11-01","title":"Arsenal vs. Chelsea","gameId":"99001","negRisk":True,"negRiskAugmented":False,"negRiskMarketID":"0x"+"ef"*32,"startTime":"2026-11-01T16:30:00Z","markets":[{"id":"s_h","conditionId":"0x1","sportsMarketType":"moneyline","feeType":"sports_fees_v3","groupItemTitle":"Arsenal","question":"Will Arsenal win?","outcomes":'["Yes","No"]',"clobTokenIds":'["sh1","sh2"]',"questionID":"0x"+"ef"*31+"00"},{"id":"s_d","conditionId":"0x2","sportsMarketType":"moneyline","feeType":"sports_fees_v3","groupItemTitle":"Draw","question":"Will Arsenal vs Chelsea end in a draw?","outcomes":'["Yes","No"]',"clobTokenIds":'["sd1","sd2"]',"questionID":"0x"+"ef"*31+"01"},{"id":"s_a","conditionId":"0x3","sportsMarketType":"moneyline","feeType":"sports_fees_v3","groupItemTitle":"Chelsea","question":"Will Chelsea win?","outcomes":'["Yes","No"]',"clobTokenIds":'["sa1","sa2"]',"questionID":"0x"+"ef"*31+"02"}]};s={"id":"s_mm","slug":"epl-ars-che-2026-11-01-more-markets","gameId":"99001","negRisk":False,"markets":[{"id":"s_o05","conditionId":"0x4","sportsMarketType":"totals","line":.5,"feeType":"sports_fees_v3","groupItemTitle":"O/U 0.5","question":"O/U 0.5","outcomes":'["Over","Under"]',"clobTokenIds":'["so1","so2"]'}]};D=link_and_parse_soccer_regulation_trees([u,s]);assert"99001"in D and D["99001"].over05_leg is not None;assert detect_soc1_regulation_boxes(D["99001"],{},{"sd1":.22,"so1":.76},max_2leg_cost_net=.988)["two_leg_boxes"]==[];assert len(detect_soc1_regulation_boxes(D["99001"],{},{"sd1":.2,"so1":.75},max_2leg_cost_net=.988)["two_leg_boxes"])==1;g=build_lp1_bop_2026_truth_legs({"balance-of-power-2026-midterms":{"markets":[{"id":"b1","conditionId":"0xb1","question":"2026 Balance of Power: D Senate, D House","feeType":"zero_fees","endDate":"2026-11-04T00:00:00Z","clobTokenIds":'["by1","bn1"]'},{"id":"b5","conditionId":"0xb5","question":"2026 Balance of Power: Other","feeType":"zero_fees","endDate":"2026-11-04T00:00:00Z","clobTokenIds":'["by5","bn5"]'}]},"which-party-will-win-the-senate-in-2026":{"markets":[{"id":"s1","conditionId":"0xs1","groupItemTitle":"Democratic Party","feeType":"zero_fees","endDate":"2026-11-04T00:00:00Z","clobTokenIds":'["sy1","sn1"]'}]}});n=find_state_matrix_dominance_boxes(g,{"bn1":.3,"sy1":.67},max_2leg_cost_net=.993);assert len(n)==1 and n[0]["min_payout"]==1. and n[0]["jackpot_states"]==2;C={"id":"np1","slug":"nba-bos-nyk-2026-10-30","title":"Celtics vs. Knicks","startTime":"2026-10-30T23:30:00Z","markets":[{"id":"ml1","conditionId":"0xm1","sportsMarketType":"moneyline","feeType":"zero_fees","outcomes":'["Celtics","Knicks"]',"clobTokenIds":'["mla","mlb"]'}]};em_bands=[("Celtics","1-5"),("Celtics","6-10"),("Celtics","11-15"),("Celtics","16-20"),("Celtics","21+"),("Knicks","1-5"),("Knicks","6-10"),("Knicks","11-15"),("Knicks","16-20"),("Knicks","21+")];r={"id":"ne1","slug":"nba-bos-nyk-2026-10-30-exact-margin","negRisk":True,"negRiskAugmented":False,"negRiskMarketID":"0x"+"aa"*32,"markets":[{"id":f"em{k}","conditionId":f"0xem{k}","feeType":"zero_fees","groupItemTitle":f"Exact Margin: {tm} by {bd}","clobTokenIds":f'["emy{k}","emn{k}"]',"questionID":"0x"+"aa"*31+f"{k:02x}"}for k,(tm,bd)in enumerate(em_bands)]+[{"id":"em10","conditionId":"0xem10","feeType":"zero_fees","groupItemTitle":"Other","clobTokenIds":'["emy10","emn10"]',"questionID":"0x"+"aa"*31+"0a"}]}
 b=build_lp1_nba_exact_margin_bundle(C,r);assert b is not None and len(b["legs"])==24;m=find_state_matrix_dominance_boxes(b["legs"],{"mla":.58,"emn1":.4},max_2leg_cost_net=.993);assert len(m)==1 and m[0]["min_payout"]==1. and m[0]["max_payout"]==2.;l={"id":"esp1","slug":"cs2-navi-faze-2026-10-30","title":"Counter-Strike: NAVI vs FaZe (BO3)","startTime":"2026-10-30T20:00:00Z","markets":[{"id":"eml","conditionId":"0x1","sportsMarketType":"moneyline","feeType":"sports_fees_v2","outcomes":'["NAVI","FaZe"]',"clobTokenIds":'["mla_e","mlb_e"]'},{"id":"ehc","conditionId":"0x2","sportsMarketType":"map_handicap","line":-1.5,"feeType":"sports_fees_v2","groupItemTitle":"Map Handicap: NAVI (-1.5) vs FaZe (+1.5)","description":'This market will resolve to "NAVI" if NAVI wins 2 or more maps than FaZe',"outcomes":'["NAVI","FaZe"]',"clobTokenIds":'["hcm_e","hcp_e"]'},{"id":"em1","conditionId":"0x3","sportsMarketType":"child_moneyline","feeType":"sports_fees_v2","groupItemTitle":"Map 1 Winner","outcomes":'["NAVI","FaZe"]',"clobTokenIds":'["m1a_e","m1b_e"]',"outcomePrices":'["0", "1"]',"closed":True}]};q=parse_esports_bo3_event(l);assert q is not None and q.hc_fav_is_a is True and q.map1_resolved_winner=="B";j={**l,"title":"NAVI vs FaZe (BO5)","markets":[*l["markets"],{"id":"em4","sportsMarketType":"child_moneyline","groupItemTitle":"Map 4 Winner"}]};assert parse_esports_bo3_event(j)is None;f=evaluate_api1_esports_bo3_opportunities(q,{},{"mla_e":.55,"hcp_e":.41},max_middle_cost_net=.988);assert len(f["single_leg_locks"])==1 and f["single_leg_locks"][0]["token_id"]=="hcp_e";assert len(f["two_leg_boxes"])==1 and f["two_leg_boxes"][0]["post_m1_forfeit_immune"]is True;import asyncio;import json;import time as _time_m;import src.polymarket_research.alpha_124_shadow_daemon as a124_mod;cand_out=tmp_path/"d1_cands.jsonl";monkeypatch.setattr(a124_mod,"STATE_FILE",tmp_path/"a124_fv2.json");monkeypatch.setattr(a124_mod,"LEDGER_FILE",tmp_path/"a124_fv2_ledger.jsonl");monkeypatch.setattr(a124_mod,"MARKET_TELEMETRY_FILE",tmp_path/"a124_fv2_telem.jsonl");monkeypatch.setattr(a124_mod,"D1_LIVE_CANDIDATES_FILE",cand_out);B=a124_mod.Alpha124ShadowDaemon(single_scan=True);A=_time_m.time();w.settle_est_ts=A+7200.
 for F in b["legs"]:F["end_ts"]=A+7200.
 b["end_ts"]=A+7200.;B.nba_prop_slates={w.event_id:w};B.lp1_nba_em_bundles={b["event_id"]:b};mock_books={"90011":{"bids":[{"price":"0.60","size":"150"}],"asks":[{"price":"0.62","size":"150"}]},"90012":{"bids":[{"price":"0.36","size":"150"}],"asks":[{"price":"0.38","size":"150"}]},"90021":{"bids":[{"price":"0.62","size":"150"}],"asks":[{"price":"0.65","size":"150"}]},"90022":{"bids":[{"price":"0.33","size":"150"}],"asks":[{"price":"0.35","size":"150"}]},"mla":{"bids":[{"price":"0.56","size":"200"}],"asks":[{"price":"0.58","size":"200"}]},"mlb":{"bids":[{"price":"0.40","size":"200"}],"asks":[{"price":"0.42","size":"200"}]},"emy1":{"bids":[{"price":"0.58","size":"200"}],"asks":[{"price":"0.60","size":"200"}]},"emn1":{"bids":[{"price":"0.38","size":"200"}],"asks":[{"price":"0.40","size":"200"}]}}
 async def _mock_fb_fv2(toks,timeout=3.5):return{t:mock_books[t]for t in toks if t in mock_books}
 B.fetch_books_batch=_mock_fb_fv2;e=[];asyncio.run(B._scan_frontier_v2_sleeves(e,A));emitted_lines=[json.loads(x)for x in cand_out.read_text(encoding="utf-8").splitlines()if x.strip()];a={c["sleeve_source"]for c in emitted_lines};assert"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"in a;assert"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"in a
if __name__=="__main__":test_polymarket_weather_rounding_spec_examples();test_metar_parser_speci_and_t_remark();test_bucket_bounds_parser();test_barrier_and_svi_monotonicity();test_exact_twap_lock_engine_math_and_whipsaw_guard();print("ALL ALPHA-124 ORACLE & PRICING UNIT TESTS PASSED!")

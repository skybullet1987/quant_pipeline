"""
========================================================================================
DOMINUS POLYMARKET ALPHA-124 EXPANSION + PROJECTIONS + TESTS (<1 MB AST-INVARIANT COMPANION BUNDLE)
Generated: 2026-11-13 15:35:51 UTC
Pairs with polymarket_all_in_one.txt (<1 MB) for tools enforcing a 1 MB per-file upload cap
Repository: C:/Users/Anton/source/repos/Dominus
========================================================================================

TABLE OF CONTENTS (Exact 1-Based Line Ranges & Raw Module Sizes):
  [01] systemd/polymarket-alpha124-shadow.service (Lines 34 - 67 | 1,025 B) :: Alpha-124 Unified Shadow systemd Unit
  [02] src/polymarket_research/directional_wfo_shadow_sleeves.py (Lines 68 - 489 | 72,784 B) :: v3.9.5 WFO Graduation Shadow Sleeves (SLEEVE_HYBRID_ZSPLIT_SHADOW & SLEEVE_BTC_5M_SNIPER_SHADOW)
  [03] src/polymarket_research/orderflow_wfo_simulators.py (Lines 490 - 802 | 67,237 B) :: v4.0 100ms Micro-Clip 4-Step Cascade Replay, D1 Latency-Skew WFO & Legging-Drag Parity Engine
  [04] src/polymarket_research/net_alpha_opportunity_engine.py (Lines 803 - 1,047 | 51,345 B) :: v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine
  [05] src/polymarket_research/weather_metar_engine.py (Lines 1,048 - 1,485 | 73,834 B) :: Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb
  [06] src/polymarket_research/barrier_onetouch_svi_engine.py (Lines 1,486 - 1,627 | 22,955 B) :: Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)
  [07] src/polymarket_research/multistrike_svi_scalper.py (Lines 1,628 - 1,804 | 33,496 B) :: Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner
  [08] src/polymarket_research/same_oracle_dominance_box.py (Lines 1,805 - 2,070 | 45,702 B) :: Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine
  [09] src/polymarket_research/exact_twap_lock_engine.py (Lines 2,071 - 2,132 | 13,478 B) :: Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock
  [10] src/polymarket_research/tradfi_sports_zero_fee_engine.py (Lines 2,133 - 2,677 | 80,846 B) :: Zero-Fee Pyth Commodities/Metals/Equities (CM_B3/B2/U1), B4 Wick Lock, NBA Polish-Middle (SP1) & NegRisk (NR0)
  [11] src/polymarket_research/macro_counting_ctf_engine.py (Lines 2,678 - 3,099 | 61,607 B) :: Phase-2 Multi-Vertical Structural & Oracle Engine (TW1 xtracker, FED1 125-State LP, COND1 Oil-Senate, CTF Overround, AAA Gas, D2 12PM)
  [12] src/polymarket_research/uma_nba_endgame_engine.py (Lines 3,100 - 3,350 | 39,046 B) :: Evergreen On-Chain UMA Resolution Bond Harvester (BOND1) & 0%-Fee Live NBA Final-2m/Post-Buzzer Sniper (SP2)
  [13] src/polymarket_research/riskless_frontier_v2_engine.py (Lines 3,351 - 3,795 | 87,117 B) :: Riskless Frontier v2 Engine (NR2 Subset Convert + Free Tail, SP4 NBA Props, BOND2 Whitelisted MOOv2, SOC1 3-Way Soccer, LP1 Implication Matrix, API1 BO3 Esports)
  [14] src/polymarket_research/riskless_frontier_v3_engine.py (Lines 3,796 - 4,468 | 111,459 B) :: Riskless Frontier v3 Engine (NFL Exact Margin/Spread, Subperiod Clinch, Deadline Ladder, Tennis Retirement-Safe Corridor, Multi-Sport Post-Review Clinch)
  [15] src/polymarket_research/riskless_frontier_v4_engine.py (Lines 4,469 - 5,059 | 119,757 B) :: Riskless Frontier v4 Evergreen Engine (AFF1 Subperiod Collapse, SOC2 83-State Lattice, NFL_PRP1 Locks, SUM1 Frechet Triangles, CRY_INC1 Binance Inclusion, MKR_LOCK1)
  [16] src/polymarket_research/alpha_124_shadow_daemon.py (Lines 5,060 - 9,002 | 876,182 B) :: Unified Multi-Vertical Shadow Daemon (Crypto, Weather METAR/HKO, Pyth Commodities/Metals/Equities, Sports, UMA Bonds, Frontier v2/v3/v4)
  [17] scripts/backtest_alpha_124.py (Lines 9,003 - 9,226 | 40,201 B) :: Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124
  [18] scripts/polymarket_daily_projections.py (Lines 9,227 - 9,440 | 75,445 B) :: Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker
  [19] scripts/alpha124_status.py (Lines 9,441 - 9,468 | 3,091 B) :: Live Alpha-124 Multi-Sleeve Scorecard & Orderbook Opportunity Inspector
  [20] scripts/polymarket_scorecard_snapshot.py (Lines 9,469 - 9,484 | 4,891 B) :: Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot
"""

from __future__ import annotations

# ======================================================================================
# [01/20] MODULE: systemd/polymarket-alpha124-shadow.service
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
Environment=MALLOC_ARENA_MAX=2
Environment=PM_DISABLE_SHADOW_M4_CATCHUP=1
Environment=PM_DISABLE_SHADOW_W2_TAKER=1
Environment=PM_UNQUARANTINE_S2_TWAP_LOCK=1
CPUWeight=50
IOWeight=200
Nice=10
OOMScoreAdjust=500
MemoryHigh=950M
MemoryMax=1100M
MemorySwapMax=0
ExecStart=/home/skybullet1987/quant_pipeline/venv/bin/python src/polymarket_research/alpha_124_shadow_daemon.py --riskless-bridge-only
Restart=always
RestartSec=10
KillSignal=SIGTERM
KillMode=process
TimeoutStopSec=15s
[Install]
WantedBy=default.target
'''
# ======================================================================================
# [02/20] MODULE: src/polymarket_research/directional_wfo_shadow_sleeves.py
# PURPOSE: v3.9.5 WFO Graduation Shadow Sleeves (SLEEVE_HYBRID_ZSPLIT_SHADOW & SLEEVE_BTC_5M_SNIPER_SHADOW)
# ======================================================================================

import json;import math;import os;import random;import re;import time;from datetime import datetime,timezone;from pathlib import Path;from typing import Any,Dict,List,Optional,Set,Tuple;from zoneinfo import ZoneInfo;from src.polymarket_research.exact_twap_lock_engine import should_suppress_final60s_twap_salvage;from src.polymarket_research.polymarket_live_executor import calculate_taker_fee;from src.polymarket_research.polymarket_live_harvester import evaluate_coinbase_venue_veto;from src.polymarket_research.riskless_protocol_v2_expansion import get_us_eastern_tz;SHADOW_INITIAL_CAPITAL=5e2;SHADOW_TICKET_USD=15.;SHADOW_ELASTIC_USD=12.;XAU_TICKET_USD=12.;MAX_MAKER_JOIN_QUEUE_USD=350.;TRANSIT_LATENCY_SEC=.5;MAKER_TTL_SEC=6.;SHIELD_DECAY_FRAC=.5;Z_TAKER_CUT=1.2;_NY_TZ=get_us_eastern_tz()
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
      try:q=json.loads(r)
      except Exception:continue
      p=str(q.get("trade_id")or"");o=str(q.get("market_id")or"")
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
  if a.production_mode:
   from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as c
   if not bool(c.snapshot.get("shadow_governance",{}).get("enable_hybrid_zsplit_shadow",True)):return False
  M=str(shock.get("market_id")or"")
  if not M or M in a.hz_open or M in a.hz_pending or M in a.hz_settled_markets:return False
  if len(a.hz_open)+len(a.hz_pending)>=2:return False
  J=str(shock.get("title")or"");y=J.lower();e=str(shock.get("asset")or"").upper()
  if not e:e="BTC"if("bitcoin"in y or"btc"in y)else("ETH"if("ethereum"in y or"eth"in y)else"")
  if e not in("BTC","ETH"):return False
  G=str(shock.get("horizon")or shock.get("candle_interval")or"").lower();L=str(shock.get("series_slug")or shock.get("slug")or"").lower();o=f"{G} {L} {y}"
  if re.search(r"(?<![0-9])5m(?![0-9a-z])|(?<![0-9])300s(?![0-9a-z])",o):return False
  b=False;F=re.search(r"(\d{1,2}):(\d{2})\s*(?:am|pm)?\s*-\s*(\d{1,2}):(\d{2})\s*(?:am|pm)",y)
  if F:
   Q,P=int(F.group(2)),int(F.group(4));x=(P-Q)%60
   if x==15:b=True
   elif x==5:return False
  E=bool(re.search(r"(?<![0-9])15m(?![0-9a-z])|(?<![0-9])900s(?![0-9a-z])",o))or b;I=not E and(bool(re.search(r"(?<![0-9])(?:1h|60m)(?![0-9a-z])|hourly",o))or("am et"in y or"pm et"in y))
  if not(E or I):return False
  S="15m"if E else"1h";a.hz_funnel["signals_seen"]=int(a.hz_funnel.get("signals_seen",0))+1;w=float(shock.get("t0_unix")or time.time())
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   R=datetime.fromtimestamp(w,tz=timezone.utc)
   if R.hour==13 and R.minute>=30:return False
  O=float(shock.get("seconds_to_expiry")or.0)
  if S=="15m"and not((180.<=O<=390.)if a.production_mode else(90.<=O<=480.)):return False
  if S=="1h"and not((150.<=O<=2400.)if a.production_mode else(150.<=O<=6e2)):return False
  j=str(shock.get("shock_direction")or"").upper()
  if j not in("BUY","SELL"):return False
  K="UP"if j=="BUY"else"DOWN";v,_=evaluate_coinbase_venue_veto(shock,K)
  if v:return False
  i=abs(float(shock.get("shock_ofi")if shock.get("shock_ofi")is not None else 1.))
  if i<.6:return False
  u=float(shock.get("spot_at_t0")or shock.get("trigger_price")or.0);t=float(shock.get("candle_open_spot")or shock.get("finalized_1h_open")or.0);h=float(shock.get("twap_60s_open")or.0);s=float(shock.get("chainlink_proxy_usd_spot")or.0);r=float(shock.get("authoritative_chainlink_open")or.0);q=a._compute_signed_cushion(K,S,u,t,h,s,r)
  if q is None or q<4e-4:return False
  p=float(shock.get("candle_sigma")or.0);n=(p*2. if E else p)if p>.0 else(.005 if e=="BTC"else.0068);g=max(.00025,n*math.sqrt(max(O,30.)/3600.));m=q/g
  if m<.78:return False
  N=(shock.get("pre_shock_features_t0")or{}).get(K)or{};l=N.get("raw_top_asks")or[];k=N.get("raw_top_bids")or[];D=float(N.get("best_ask")or(l[0][0]if l else 1.));C=float(N.get("best_bid")or(k[0][0]if k else.0));B=float(N.get("ask_size_l1")or(l[0][1]if l else.0));f=round(D-C,4)if C>0 else.99;A=D*B;d=(.72 if E else.76)if a.production_mode else.82
  if not(.55<=D<=d)or C<=.0 or f>.03 or A<20.:return False
  a.hz_funnel["signals_evaluated"]+=1;z="TAKER_PLUS_P3A"if m>=Z_TAKER_CUT else"SHIELDED_MAKER_FIRST"
  if z=="SHIELDED_MAKER_FIRST":a.hz_funnel["maker_branch_queued"]+=1
  else:a.hz_funnel["taker_branch_queued"]+=1
  H=time.time();a.hz_pending[M]={"sleeve":"SLEEVE_HYBRID_ZSPLIT_SHADOW","trade_id":f"HZSHDW_{M}_{int(w)}_{K}","market_id":M,"title":J,"asset":e,"horizon":S,"target_token":K,"t0_unix":w,"queued_mono":H,"arrival_mono":H+a.latency_sec,"expiry_unix":float(shock.get("candle_expiry_ts")or shock.get("expiry_ts")or(w+O)),"tte_t0":O,"ask_t0":D,"bid_t0":C,"l1_usd_t0":round(A,2),"cush_t0":q,"z_strike":round(m,4),"open_usdt":t,"twap_open_usdt":h,"auth_cl_open_usd":r,"branch":z,"phase":"IN_TRANSIT","maker_px":None,"deadline_mono":None};return True
 def _ingest_btc_5m_telemetry_tick(a,d):
  n=str(d.get("asset")or"").upper();A=str(d.get("horizon")or"").lower()
  if n!="BTC"or A!="5m":return
  a.b5_funnel["ticks_scanned"]+=1;z=float(d.get("timestamp_unix")or time.time());y=float(d.get("binance_spot")or.0)
  if y>0:
   x=int(z//60)
   if x>a._btc_last_1m_bkt:
    if a._btc_last_1m_spot>0:g=max(1,x-a._btc_last_1m_bkt)if a._btc_last_1m_bkt>0 else 1;w=math.log(y/a._btc_last_1m_spot);a._btc_sigma_1h=max(.002,min(.02,math.sqrt(.94*(a._btc_sigma_1h**2)+.06*((60./g)*w*w))))
    a._btc_last_1m_spot=y;a._btc_last_1m_bkt=x
  p=str(d.get("market_id")or"")
  if not p:return
  if p in a.b5_open:a._check_open_position_exit(a.b5_open,p,d,is_btc_5m=True);return
  if p in a.b5_pending or p in a.b5_settled_markets:return
  if len(a.b5_open)+len(a.b5_pending)>=2:return
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   v=datetime.fromtimestamp(z,tz=timezone.utc)
   if v.hour==13 and v.minute>=30:return
  t=float(d.get("seconds_to_expiry")or.0)
  if not(60.<=t<=180.):return
  k=float(d.get("binance_open")or.0);j=float(d.get("twap_60s_open")or.0);m=float(d.get("chainlink_proxy_usd_spot")or.0);f=float(d.get("authoritative_chainlink_open")or.0)
  if y<=0 or k<=0:return
  b=max(.00025,a._btc_sigma_1h*math.sqrt(max(t,15.)/3600.))
  for o in("UP","DOWN"):
   u=d.get(o)or{};s=float(u.get("best_bid")or.0);r=float(u.get("best_ask")or 1.);q=float(u.get("ask_size_l1")or.0)
   if u.get("is_crossed")or s<=.0 or r>=.99 or s>=r:continue
   i=round(r-s,4);h=r*q
   if not(.55<=r<=.85)or i>.03 or h<15.:continue
   e=a._compute_signed_cushion(o,"5m",y,k,j,m,f)
   if e is None or e<3e-4:continue
   c=e/b
   if c<.8:continue
   l=time.time();a.b5_funnel["candidates_queued"]+=1;a.b5_pending[p]={"sleeve":"SLEEVE_BTC_5M_SNIPER_SHADOW","trade_id":f"BTC5M_{p}_{int(z)}_{o}","market_id":p,"title":str(d.get("title")or f"BTC 5m {p}"),"asset":"BTC","horizon":"5m","target_token":o,"t0_unix":z,"queued_mono":l,"arrival_mono":l+a.latency_sec,"expiry_unix":z+t,"tte_t0":t,"ask_t0":r,"bid_t0":s,"l1_usd_t0":round(h,2),"cush_t0":e,"z_strike":round(c,4),"open_usdt":k,"twap_open_usdt":j,"auth_cl_open_usd":f,"latest_tick":d};break
 def _ingest_sol_5m_telemetry_tick(a,d):
  p=str(d.get("asset")or"").upper();C=str(d.get("horizon")or"").lower()
  if p!="SOL"or C!="5m":return
  a.s5_funnel["ticks_scanned"]+=1;B=float(d.get("timestamp_unix")or time.time());A=float(d.get("binance_spot")or.0)
  if A>0:
   z=int(B//60)
   if z>a._sol_last_1m_bkt:
    if a._sol_last_1m_spot>0:h=max(1,z-a._sol_last_1m_bkt)if a._sol_last_1m_bkt>0 else 1;y=math.log(A/a._sol_last_1m_spot);a._sol_sigma_1h=max(.004,min(.03,math.sqrt(.94*(a._sol_sigma_1h**2)+.06*((60./h)*y*y))))
    a._sol_last_1m_spot=A;a._sol_last_1m_bkt=z
  r=str(d.get("market_id")or"")
  if not r:return
  if r in a.s5_open:a._check_open_position_exit(a.s5_open,r,d,sleeve_tag="s5");return
  if r in a.s5_pending or r in a.s5_settled_markets:return
  if len(a.s5_open)+len(a.s5_pending)>=2:return
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   x=datetime.fromtimestamp(B,tz=timezone.utc)
   if x.hour==13 and x.minute>=30:return
  v=float(d.get("seconds_to_expiry")or.0)
  if not(60.<=v<=180.):return
  m=float(d.get("binance_open")or.0);l=float(d.get("twap_60s_open")or.0);o=float(d.get("chainlink_proxy_usd_spot")or.0);g=float(d.get("authoritative_chainlink_open")or.0)
  if A<=0 or m<=0:return
  b=float(d.get("candle_sigma")or.0);k=(b*math.sqrt(12.))if b>.0 else a._sol_sigma_1h;c=max(.00035,k*math.sqrt(max(v,15.)/3600.))
  for q in("UP","DOWN"):
   w=d.get(q)or{};u=float(w.get("best_bid")or.0);t=float(w.get("best_ask")or 1.);s=float(w.get("ask_size_l1")or.0)
   if w.get("is_crossed")or u<=.0 or t>=.99 or u>=t:continue
   j=round(t-u,4);i=t*s
   if not(.55<=t<=.85)or j>.03 or i<15.:continue
   f=a._compute_signed_cushion(q,"5m",A,m,l,o,g)
   if f is None or f<4e-4:continue
   e=f/c
   if e<.8:continue
   n=time.time();a.s5_funnel["candidates_queued"]+=1;a.s5_pending[r]={"sleeve":"SLEEVE_SOL_5M_CANARY_SHADOW","trade_id":f"SOL5M_{r}_{int(B)}_{q}","market_id":r,"title":str(d.get("title")or f"SOL 5m {r}"),"asset":"SOL","horizon":"5m","target_token":q,"t0_unix":B,"queued_mono":n,"arrival_mono":n+a.latency_sec,"expiry_unix":B+v,"tte_t0":v,"ask_t0":t,"bid_t0":u,"l1_usd_t0":round(i,2),"cush_t0":f,"z_strike":round(e,4),"open_usdt":m,"twap_open_usdt":l,"auth_cl_open_usd":g,"latest_tick":d};break
 def ingest_xau_15m_tick(a,d):
  t=str(d.get("asset")or"").upper();H=str(d.get("horizon")or"").lower()
  if t not in("XAU","GOLD")or H!="15m":return False
  a.xau_funnel["ticks_scanned"]+=1;G=float(d.get("timestamp_unix")or time.time());k,_=is_xau_cme_blackout_or_inactive_session(G)
  if k:a.xau_funnel["cme_or_session_blocked"]+=1;return False
  p=compute_synthetic_xau_usd_anchor(binance_xau_usdt=float(d.get("binance_xau_usdt")or d.get("binance_spot")or.0),coinbase_usdt_usd=float(d.get("coinbase_usdt_usd")or.0),swissquote_bid=float(d.get("swissquote_bid")or.0),swissquote_ask=float(d.get("swissquote_ask")or.0),max_basis_bps=2.5)
  if not p["valid"]:a.xau_funnel["basis_or_anchor_rejected"]+=1;return False
  j=float(p["xau_usd"]);F=int(G//60)
  if F>a._xau_last_1m_bkt:
   if a._xau_last_1m_spot>0:i=max(1,F-a._xau_last_1m_bkt)if a._xau_last_1m_bkt>0 else 1;E=math.log(j/a._xau_last_1m_spot);a._xau_sigma_1h=max(.001,min(.012,math.sqrt(.94*(a._xau_sigma_1h**2)+.06*((60./i)*E*E))))
   a._xau_last_1m_spot=j;a._xau_last_1m_bkt=F
  x=str(d.get("market_id")or"")
  if not x:return False
  if x in a.xau_open:s=dict(d,chainlink_proxy_usd_spot=j);a._check_open_position_exit(a.xau_open,x,s,sleeve_tag="xau");return False
  if x in a.xau_pending or x in a.xau_settled_markets:return False
  if len(a.xau_open)+len(a.xau_pending)>=1:return False
  C=float(d.get("seconds_to_expiry")or.0)
  if not(90.<=C<=480.):return False
  r=d.get("authoritative_chainlink_open")or d.get("strike_usd")
  if r is None or float(r)<=.0:a.xau_funnel["basis_or_anchor_rejected"]+=1;return False
  b=round(float(r),3);h=float(d.get("candle_sigma")or.0);o=(h*2.)if h>.0 else a._xau_sigma_1h;c=max(.00018,o*math.sqrt(C/3600.))
  for w in("UP","DOWN"):
   D=d.get(w)or{};n=d.get("DOWN"if w=="UP"else"UP")or{};B=float(D.get("best_bid")or.0);A=float(D.get("best_ask")or 1.);z=float(D.get("ask_size_l1")or.0);y=float(D.get("bid_size_l1")or.0);g=float(n.get("best_bid")or.0)
   if D.get("is_crossed")or B<=.0 or A>=.99 or B>=A:continue
   m=round(A-B,4);l=A*z
   if not(.56<=A<=.83)or m>.02 or l<50.:continue
   v=1. if w=="UP"else-1.;u=v*(j-b)/b
   if u<.00025:continue
   f=u/c
   if f<.85:continue
   e=round(min(.82,A-.01,B+(.01 if m>=.02 else.0)),2)
   if e<.55 or e>=A-1e-6:continue
   if e<=B+1e-6 and(B*y)>MAX_MAKER_JOIN_QUEUE_USD:a.xau_funnel["queue_depth_rejected"]+=1;continue
   if g>.0 and round(1.-g,4)<=e+1e-6:a.xau_funnel["shield_or_comp_canceled"]+=1;continue
   q=time.time();a.xau_funnel["maker_queued"]+=1;a.xau_pending[x]={"sleeve":"SLEEVE_XAU_15M_MAKER_SHADOW","trade_id":f"XAU15M_{x}_{int(G)}_{w}","market_id":x,"title":str(d.get("title")or f"XAU/USD 15m {x}"),"asset":"XAU","horizon":"15m","target_token":w,"t0_unix":G,"queued_mono":q,"arrival_mono":q+a.latency_sec,"expiry_unix":G+C,"tte_t0":C,"ask_t0":A,"bid_t0":B,"maker_px":e,"deadline_mono":q+a.latency_sec+MAKER_TTL_SEC,"l1_usd_t0":round(l,2),"cush_t0":u,"z_strike":round(f,4),"open_usdt":.0,"twap_open_usdt":.0,"auth_cl_open_usd":b,"latest_tick":d};return True
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
  n=time.time();f={}
  if a.production_mode:from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as c;f=c.snapshot.get("shadow_governance",{})or{}
  m=bool(f.get("enable_btc_5m_sniper_shadow",f.get("enable_btc_5m_shadow",False)));l=bool(f.get("enable_sol_5m_canary_shadow",f.get("enable_sol_5m_shadow",False)))
  if(not a.production_mode)or m:
   for j in a._tail_jsonl_file(a.b5_telem_file,"b5_file_pos"):
    a._ingest_btc_5m_telemetry_tick(j);b=str(j.get("market_id")or"")
    if b in a.b5_pending:a.b5_pending[b]["latest_tick"]=j
  if(not a.production_mode)or l:
   for j in a._tail_jsonl_file(a.s5_telem_file,"s5_file_pos"):
    a._ingest_sol_5m_telemetry_tick(j);b=str(j.get("market_id")or"")
    if b in a.s5_pending:a.s5_pending[b]["latest_tick"]=j
  if(not a.production_mode)or bool(f.get("enable_xau_15m_maker_shadow",True)):
   for j in a._tail_jsonl_file(a.xau_telem_file,"xau_file_pos"):
    a.ingest_xau_15m_tick(j);b=str(j.get("market_id")or"")
    if b in a.xau_pending:a.xau_pending[b]["latest_tick"]=j
  e=((a.t15_btc_file,"t15_btc_pos"),(a.t15_eth_file,"t15_eth_pos"),(a.t1h_btc_file,"t1h_btc_pos"),(a.t1h_eth_file,"t1h_eth_pos"))
  if a.hz_open:
   for i,h in e:
    for j in a._tail_jsonl_file(i,h):
     b=str(j.get("market_id")or"")
     if b in a.hz_open:a._check_open_position_exit(a.hz_open,b,j,sleeve_tag="hz")
  else:
   for i,h in e:
    if i.exists():setattr(a,h,i.stat().st_size)
  k=time.time()
  if a.hz_pending:a._step_hz_pending(k)
  if a.b5_pending:a._step_b5_pending(k)
  if a.s5_pending:a._step_s5_pending(k)
  if a.xau_pending:a._step_xau_pending(k)
  for b,g in list(a.hz_open.items()):
   d=a._extract_market_view(g["asset"],b,g["horizon"])
   if d is not None:a._check_open_position_exit(a.hz_open,b,d,sleeve_tag="hz")
  for b,g in list(a.b5_open.items()):
   d=a._extract_market_view("BTC",b,"5m")
   if d is not None:a._check_open_position_exit(a.b5_open,b,d,sleeve_tag="b5")
  for b,g in list(a.s5_open.items()):
   d=a._extract_market_view("SOL",b,"5m")
   if d is not None:a._check_open_position_exit(a.s5_open,b,d,sleeve_tag="s5")
  for b,g in list(a.xau_open.items()):
   d=a._extract_market_view("XAU",b,"15m")
   if d is not None:a._check_open_position_exit(a.xau_open,b,d,sleeve_tag="xau")
  if(n-a._last_state_flush_ts)>=15.:a.save_states()
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
# [03/20] MODULE: src/polymarket_research/orderflow_wfo_simulators.py
# PURPOSE: v4.0 100ms Micro-Clip 4-Step Cascade Replay, D1 Latency-Skew WFO & Legging-Drag Parity Engine
# ======================================================================================

import json;import math;from pathlib import Path;from typing import Any,Dict,List,Optional,Sequence,Tuple;DEFAULT_FEE_RATE=.07
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
 l=[];b={"SINGLE_LEG_MAKER_LOCK","SINGLE_LEG_LOCK","NEGRISK_CONVERT","MULTI_LEG_BUNDLE","CTF_OVERROUND","COMPLETE_SET"}
 if data_dir is not None:
  for k in(Path(data_dir)/"d1_live_box_candidates.jsonl.1",Path(data_dir)/"d1_live_box_candidates.jsonl"):
   if not k.exists():continue
   try:a=k.read_text(encoding="utf-8",errors="ignore").splitlines()
   except Exception:a=[]
   for u in a:
    if not u.strip():continue
    try:
     d=json.loads(u)
     if not isinstance(d,dict):continue
     r=str(d.get("box_type")or"").strip().upper()
     if r in b:continue
     if r and not(d.get("leg_b_token_id")or d.get("leg_b_avail_shares")is not None):continue
     t=max(5.,float(d.get("shares")or 12.));f=float(d.get("leg_a_avail_shares")or t*1.8);e=float(d.get("leg_b_avail_shares")or t*1.8);l.append({**d,"depletion_a_per_s":round(max(4.,.32*f),2),"depletion_b_per_s":round(max(4.,.24*e),2),"bid_drop_a":.02 if float(d.get("box_cost_net")or.98)<=.98 else.03,"bid_drop_b":.02})
    except Exception:continue
 if len(l)>=36:return l
 j=[];c=[(.968,36.,34.,"15m","5m",14.,12.,.015,False),(.974,19.,42.,"15m","5m",22.,10.,.02,False),(.991,13.5,28.,"15m","5m",24.,14.,.03,False),(.976,38.,20.,"4h","15m",10.,26.,.025,False),(.964,30.,29.,"15m","5m",12.,12.,.015,True),(.982,16.,35.,"4h","15m",28.,12.,.03,False)]
 for s in range(60):i,f,e,q,p,n,m,h,o=c[s%len(c)];g=(s%5-2)*.0015;j.append({"shares":12.,"box_cost_net":round(i+g,4),"leg_a_limit_price":round(.5*(i+g)-.01,4),"leg_b_limit_price":round(.5*(i+g)-.01,4),"leg_a_avail_shares":f,"leg_b_avail_shares":e,"leg_a_horizon":q,"leg_b_horizon":p,"depletion_a_per_s":n,"depletion_b_per_s":m,"bid_drop_a":h,"bid_drop_b":.02,"corridor_jackpot":bool(o and(s%12==4))})
 return j
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
 C=float(ev["bid_anc"]);B=float(ev["ask_anc"]);t=float(ev.get("obi_anc",.0));A=float(ev["ask_hdg"]);z=float(ev["hdg_shares"]);H=max(5.,float(ev.get("shares",18.)));G=float(ev.get("fee_rate",DEFAULT_FEE_RATE));E=str(ev.get("anc_side","UP")).upper();h=float(ev.get("spot_ret_bps",.0))
 def a(p):p=round(float(p),4);return(math.floor((p+1e-9)*1e2)/1e2)if(.04+1e-9<p<.96-1e-9)else(math.floor((p+1e-9)*1e3)/1e3)
 y=.001 if(C>=.96 or C<.04)else.01;x=.001 if(B>.96 or B<=.04)else.01;o=a(C+y);l=a(B-x);F=round(B-C,4);e=bool(cfg.get("allow_join_1c_mid",True));k=float(cfg.get("min_obi_join_1c",-.15));j=float(cfg.get("min_obi_any",-.35));g=float(cfg.get("min_hdg_depth_mult",2.5));f=float(cfg.get("max_post_net",.988));d=float(cfg.get("adverse_spot_cancel_bps",2.5))
 if t<j or z<max(15.,g*H):return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 if o<=l+1e-9 and o>C+1e-9:b=min(o,l);c=True
 elif e and F>=.01-1e-9 and.15<=B<=.85 and t>=k:b=a(C);c=False
 else:return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 n=A+v2_taker_fee_per_share(A,G);s=a(f-n);w=min(b,s)
 if w<round(C-(y if c else.0),3)or w<=.02 or w>=B:return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 if not(.9<=(w+n)<=f):return{"posted":False,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 r=(-h)if E=="UP"else h
 if r>d:return{"posted":True,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 if not ev.get("passive_fill",True):return{"posted":True,"filled":False,"hedged":False,"pnl_usd":.0,"scratched":False}
 i=round(A+(float(ev.get("hdg_jump_on_adverse",.0))if r>1.5 else.0),4);m=w+i+v2_taker_fee_per_share(i,G)
 if.9<=m<=.995:D=compute_d1_maker_anchor_drag_haircut(shares=H,pair_eff=m,bid_anc=w,hdg_px=i,hdg_avail_shares=z,fee_rate_anc=G,queue_front=c);return{"posted":True,"filled":True,"hedged":True,"scratched":False,"pnl_usd":round(H*(1.-m),4),"adj_pnl_usd":D["legging_adjusted_min_profit_usd"]}
 v=max(.01,w-max(.015,float(ev.get("hdg_jump_on_adverse",.02))));q=v-v2_taker_fee_per_share(v,G);u=round(H*(q-w),4);return{"posted":True,"filled":True,"hedged":False,"scratched":True,"pnl_usd":u,"adj_pnl_usd":u}
def calibrate_d1_maker_leg1_wfo(maker_events=None,purge_gap=3):
 q=list(maker_events)if maker_events is not None else _default_d1_maker_leg1_events();n=len(q);z=max(4,int(.5*n));p=min(n,z+purge_gap);o=max(p+2,int(.75*n));m=min(n,o+purge_gap);w,v,u=q[:z],q[p:o],q[m:]
 def a(sub,cfg):F=[simulate_d1_maker_leg1_box(e,cfg)for e in sub];D=[r for r in F if r["filled"]];E=[r for r in D if r["hedged"]];n=[r for r in D if r["scratched"]];C=sum(float(r.get("adj_pnl_usd",r["pnl_usd"]))for r in D);B=sum(float(r["pnl_usd"])for r in D);return{"posted":sum(1 for r in F if r["posted"]),"fills":len(D),"wins":len(E),"scratches":len(n),"win_rate_pct":round(1e2*len(E)/len(D),2)if D else.0,"raw_pnl_usd":round(B,4),"legging_adjusted_pnl_usd":round(C,4)}
 f=-1e9;d={"allow_join_1c_mid":True,"min_obi_join_1c":-.15,"min_obi_any":-.35,"min_hdg_depth_mult":2.5,"adverse_spot_cancel_bps":2.5,"max_post_net":.988};c={};b={};g=0
 for k in(True,False):
  for j in(2.,2.5,5.):
   for l in(-.15,-.4):
    for t in(1.5,2.5):
     s={"allow_join_1c_mid":k,"min_obi_join_1c":l,"min_obi_any":-.35,"min_hdg_depth_mult":t,"adverse_spot_cancel_bps":j,"max_post_net":.988};g+=1;y,x=a(w,s),a(v,s)
     if y["fills"]<3 or x["fills"]<2:continue
     A=(min(y["legging_adjusted_pnl_usd"],x["legging_adjusted_pnl_usd"])+.3*(y["legging_adjusted_pnl_usd"]+x["legging_adjusted_pnl_usd"])-6.*(y["scratches"]+x["scratches"]))
     if A>f:f,d,c,b=A,s,y,x
 if not c:c,b=a(w,d),a(v,d)
 i=a(u,d);h=a(u,{"allow_join_1c_mid":True,"min_obi_join_1c":-1.,"min_obi_any":-1.,"min_hdg_depth_mult":1.,"adverse_spot_cancel_bps":99.,"max_post_net":.992});return{"events_total":n,"purge_gap_events":purge_gap,"grid_configs_evaluated":g,"selected_maker_leg1_policy":d,"train":c,"val":b,"sealed_holdout":i,"unguarded_maker_holdout_baseline":h}
def compute_v395_pricing_and_twap_gate(cand,*,df=None,jump_vol_mult=1.,use_kemna_vorst=False):
 from src.polymarket_research.exact_twap_lock_engine import(compute_kemna_vorst_twap_sigma_rem as b,compute_unit_variance_student_t_cdf as a);j=float(cand.get("cushion_oracle",cand.get("cushion_min",.0))or.0);l=max(5.,float(cand.get("tte",3e2)or 3e2));d=max(.00025,float(cand.get("sigma_rem",.002)or.002));h=d/math.sqrt(max(l,1.)/3600.)
 if use_kemna_vorst and str(cand.get("hz")or"")in("5m","15m"):c=max(.00018,b(h,l,window_sec=60.))
 else:c=d
 f=c*max(.5,float(jump_vol_mult));i=j/f;k=min(1.,max(.0,float(cand.get("shock_ofi",.0)or.0)));g=i+.25*k
 if df is None or math.isinf(float(df))or float(df)>1e2:e=.5*(1.+math.erf(g/math.sqrt(2.)))
 else:e=a(g,df=float(df))
 return round(i,5),round(max(.01,min(.995,e)),5)
def run_wfo_post_selection_diagnostics(*,cands,dev_cands,holdout_cands,best_cfg,best_tr,best_vl,best_hold_500,stage2_results,data_dir,purge_sec,evaluate_portfolio_fn,prefilter_fn,dev_score_fn,simulate_single_fn):
 import itertools;import random;import statistics;U=sorted(cands,key=lambda x:x["t0"]);_C=len(U);_d=6;G=[]
 for _B in range(_d):_P=int((_B/_d)*_C);_O=int(((_B+1)/_d)*_C)-1;G.append((U[_P]["t0"],U[max(_P,_O)]["t0"]))
 n=[]
 for _A,_z in[(.55,.8),(.55,.82),(.55,.85)]:
  for _N in[.65,.85,1.05]:
   for _M in[4e-4,6e-4]:
    for _6 in[.01,.02]:
     for _L in["single_95","two_tranche_14_98","two_tranche_95_98","hold_98"]:
      for _5,_4,_3,_2 in[("spot_persist",None,9e-4,18.),("hybrid_persist",.12,6e-4,15.)]:n.append({"assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":90.,"max_tte_15m":480.,"min_tte_1h":150.,"max_tte_1h":1200.,"min_px":_A,"max_px":_z,"max_spread":.03,"min_l1_usd":20.,"min_cushion":_M,"min_z":_N,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True,"entry_mode":"taker_fak","fak_buffer":_6,"exit_policy":_L,"ratchet_arm":_4,"ratchet_drop":.06,"salvage_mode":_5,"wrong_side_thresh":_3,"salvage_persist_s":_2,"clob_drop_thresh":.22,"final_45s_unwind":False})
 r=prefilter_fn(U,{"assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":90.,"max_tte_15m":480.,"min_tte_1h":150.,"max_tte_1h":1200.,"min_px":.55,"max_px":.85,"max_spread":.03,"min_l1_usd":20.,"min_cushion":4e-4,"min_z":.65,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True});O=[]
 for _1,_0 in itertools.combinations(range(_d),2):
  A=[G[_1],G[_0]];T=[c for c in r if all((c["exp_ts"]<(ts_i-purge_sec))or(c["t0"]>(te_i+purge_sec))for ts_i,te_i in A)];_c=[]
  for _Z in(_1,_0):_Y,_X=G[_Z];S=purge_sec if(_Z>0 and(_Z-1)not in(_1,_0))else.0;N=purge_sec if(_Z<_d-1 and(_Z+1)not in(_1,_0))else.0;_y,_x=_Y+S,_X-N*.25;_c.extend(c for c in r if _y<=c["t0"]<=_x and c["exp_ts"]<=_X)
  _c.sort(key=lambda x:x["t0"]);_K=len(T);M=T[int(.7*_K)]["t0"]if _K>=20 else.0;_w=[c for c in T if c["exp_ts"]<=M];_v=[c for c in T if c["t0"]>=(M+purge_sec)];g=n[0];e=-1e9
  for q in n:
   _u=evaluate_portfolio_fn(_w,q,latency_mode="500ms")
   if _u["trades"]<20 or _u["total_pnl"]<=0 or _u["profit_factor"]<1.2:continue
   _t=evaluate_portfolio_fn(_v,q,latency_mode="500ms")
   if _t["trades"]<8 or _t["total_pnl"]<=0 or _t["profit_factor"]<1.15:continue
   _b=dev_score_fn(_u,_t)
   if _b>e:e,g=_b,q
  if e<=-1e8:
   for q in n:
    _m=evaluate_portfolio_fn(T,q,latency_mode="500ms")
    if _m["trades"]>=25 and _m["total_pnl"]>0:
     _b=dev_score_fn(_m,_m)
     if _b>e:e,g=_b,q
  _l=evaluate_portfolio_fn(_c,g,latency_mode="500ms");L=evaluate_portfolio_fn(_c,g,latency_mode="500ms",max_concurrent=1,ticket_usd=12.);O.append({"test_groups":[_1,_0],"fitted_exit_policy":g["exit_policy"],"fitted_min_z":g["min_z"],"trades":_l["trades"],"total_pnl":_l["total_pnl"],"seed_12_c1_pnl":L["total_pnl"],"win_rate":_l["win_rate"],"profit_factor":_l["profit_factor"],"sharpe":_l["sharpe"],"wipeout_rate":_l["wipeout_rate"]})
 z=[s["total_pnl"]for s in O];y=[s["seed_12_c1_pnl"]for s in O];F={"mode":"GENUINE_OUT_OF_SAMPLE_REFIT_CPCV_6_2","n_groups":6,"k_test_groups":2,"apriori_grid_size":len(n),"total_combinations":len(O),"positive_combinations":sum(1 for x in z if x>0),"positive_rate":round(sum(1 for x in z if x>0)/max(len(O),1),4),"seed_12_c1_positive_combinations":sum(1 for x in y if x>0),"median_oos_trades":int(statistics.median(s["trades"]for s in O)),"median_oos_pnl_usd":round(statistics.median(z),2),"mean_oos_pnl_usd":round(statistics.mean(z),2),"median_seed_12_c1_oos_pnl_usd":round(statistics.median(y),2),"min_oos_pnl_usd":round(min(z),2),"median_oos_pf":round(statistics.median(s["profit_factor"]for s in O),3),"median_oos_sharpe":round(statistics.median(s["sharpe"]for s in O),3),"splits":O};B=set();_s=data_dir/"verified_gamma_resolutions.json"
 if _s.exists():
  try:
   for _W,_V in json.loads(_s.read_text(encoding="utf-8")).items():
    if isinstance(_V,dict)and(_V.get("oracle_mismatch")or _V.get("mismatch")or(_V.get("binance_winner")and _V.get("winner")and _V.get("binance_winner")!=_V.get("winner"))):B.add(str(_W))
  except Exception:pass
 for _h in("ground_truth_resolutions.jsonl","ground_truth_resolutions_eth.jsonl","ground_truth_resolutions_sol.jsonl"):
  _J=data_dir/_h
  if _J.exists():
   try:
    for ln in _J.read_text(encoding="utf-8",errors="replace").splitlines():
     if ln.strip():
      _r=json.loads(ln)
      if _r.get("oracle_mismatch")or(_r.get("binance_winning_outcome")and _r.get("gamma_winning_outcome")and _r.get("binance_winning_outcome")!=_r.get("gamma_winning_outcome")):B.add(str(_r.get("market_id")))
   except Exception:pass
 for _k in U:
  if _k["path"]:
   V,R,_,_,_=_k["path"][-1]
   if V<=30. and abs(R)>=1e-5 and((R>0)!=bool(_k["won"])):B.add(str(_k.get("mid")))
  if str(_k.get("mid"))in B:_k["oracle_mismatch"]=True
 w=[c for c in U if c.get("oracle_mismatch")];_j=evaluate_portfolio_fn(w,dict(best_cfg,use_cl_proxy=False),latency_mode="500ms");_q=evaluate_portfolio_fn(w,dict(best_cfg,use_cl_proxy=True),latency_mode="500ms");Q=evaluate_portfolio_fn(U,dict(best_cfg,use_cl_proxy=False),latency_mode="500ms");E=evaluate_portfolio_fn(U,dict(best_cfg,use_cl_proxy=True),latency_mode="500ms");_a=dict(best_cfg)
 if not str(_a.get("exit_policy","")).startswith("two_tranche"):_a["exit_policy"]="two_tranche_12_98"
 K=evaluate_portfolio_fn(U,dict(_a,t2_post_lag_s=5.),latency_mode="500ms");P=evaluate_portfolio_fn(U,dict(_a,t2_post_lag_s=.05),latency_mode="500ms");u=evaluate_portfolio_fn(U,dict(_a,t2_post_lag_s=.0),latency_mode="500ms");j={"mismatch_markets_identified":len(B),"mismatch_candidates_total":len(w),"mismatch_raw_trades":_j["trades"],"mismatch_raw_pnl":_j["total_pnl"],"mismatch_cl_proxy_trades":_q["trades"],"mismatch_cl_proxy_pnl":_q["total_pnl"],"full_dataset_raw_pnl":Q["total_pnl"],"full_dataset_raw_pf":Q["profit_factor"],"full_dataset_cl_proxy_pnl":E["total_pnl"],"full_dataset_cl_proxy_pf":E["profit_factor"],"blueprint1_tranche2_comparison":{"delayed_5s_pnl":K["total_pnl"],"delayed_5s_pf":K["profit_factor"],"inline_50ms_pnl":P["total_pnl"],"inline_50ms_pf":P["profit_factor"],"concurrent_0ms_pnl":u["total_pnl"],"concurrent_0ms_pf":u["profit_factor"]}};h=[p/15. for p in(best_vl["pnls"]+best_hold_500["pnls"])]
 if len(h)<20:h=[p/15. for p in best_tr["pnls"]]
 def a(label,start_eq,base_pct,min_tkt,floor_u,seed_cap=.0,corr_p=.0):
  _8=random.Random(20261025);k=0;x,v=[],[];n_r=max(1,len(h))
  for _ in range(10000):
   s,pk,_7,p,c=start_eq,start_eq,.0,False,0
   while c<50 and h:
    if s<floor_u:p=True;break
    if seed_cap>.0 and s<seed_cap:s+=min(s,12.)*h[_8.randrange(n_r)];c+=1
    else:
     tkt=min(s,max(min_tkt,round(s*base_pct,2)))
     if corr_p>.0 and _8.random()<corr_p and(c+1)<50:r1=h[_8.randrange(n_r)];r2=r1 if _8.random()<.75 else h[_8.randrange(n_r)];s+=tkt*r1+(tkt*.54)*r2;c+=2
     else:s+=tkt*h[_8.randrange(n_r)];c+=1
    pk=max(pk,s);_7=max(_7,pk-s)
    if s<floor_u:p=True;break
   if p:k+=1
   x.append(s);v.append(_7)
  x.sort();v.sort();return{"policy":label,"start_equity_usd":start_eq,"floor_usd":floor_u,"halt_prob_50_trades":round(k/10000,4),"median_terminal_equity_usd":round(x[5000],2),"p05_terminal_equity_usd":round(x[500],2),"p95_terminal_equity_usd":round(x[9500],2),"p95_max_drawdown_usd":round(v[9500],2)}
 J=[a("v3.7_UNPATCHED_22PCT_FLOOR65_CONC2",76.49,.22,12.,65.,corr_p=.25),a("CENTRAL_CFG_18PCT_FLOOR66.67_CONC2",76.49,.18,12.,66.67,corr_p=.25),a("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR48",76.49,.18,12.,48.,seed_cap=88.,corr_p=.15),a("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR52",76.49,.18,12.,52.,seed_cap=88.,corr_p=.15)];D=[];t=set()
 for sc,_U,_I,_H,_ in stage2_results:
  _G=(_U["assets"],_U["horizons"],_U["min_px"],_U["max_px"],_U["min_z"],_U["min_cushion"],_U["entry_mode"],_U["exit_policy"])
  if _G in t:continue
  t.add(_G);_F=evaluate_portfolio_fn(holdout_cands,_U,latency_mode="500ms");D.append({"score":round(sc,2),"config":{k:(list(v)if isinstance(v,tuple)else v)for k,v in _U.items()},"train":{k:v for k,v in _I.items()if k!="pnls"},"val":{k:v for k,v in _H.items()if k!="pnls"},"holdout":{k:v for k,v in _F.items()if k!="pnls"}})
  if len(D)>=5:break
 b={};_g=data_dir/"live_harvester_state.json"
 if _g.exists():
  st=json.loads(_g.read_text(encoding="utf-8"));I=st.get("closed_positions",[]);H={c["event_id"]:c for c in cands};o,i,d,f=.0,0,0,0;m=[]
  for _T in I:
   _f=float(_T.get("net_pnl_usd")or.0);_S=str(_T.get("event_id")or"");_R=str(_T.get("trade_id")or"");_e=H.get(_S)
   if not _e:continue
   i+=1;_Q=simulate_single_fn(_e,best_cfg,latency_mode="500ms");Z=float(_T.get("notional_usd")or 15.)
   if _Q is None:
    C,l=.0,"VETOED_AT_ENTRY"
    if _f<0:d+=1
    else:f+=1
   else:C,l=round(_Q[0]*Z,2),_Q[1]
   o+=C
   if"6076647"in _R or"6082720"in _R or _f<=-15.:m.append({"trade_id":_R,"entry_price":_T.get("entry_price"),"max_seen_bid":_T.get("max_seen_bid"),"actual_pnl_usd":round(_f,2),"actual_close_reason":_T.get("close_reason"),"wfo_counterfactual_pnl_usd":C,"wfo_counterfactual_action":l})
  b={"total_live_closed_trades":len(I),"matched_to_trigger_dataset":i,"actual_matched_subset_pnl_usd":round(sum(float(p.get("net_pnl_usd")or.0)for p in I if str(p.get("event_id")or"")in H),2),"wfo_optimal_counterfactual_pnl_usd":round(o,2),"filtered_out_losing_trades":d,"filtered_out_winning_trades":f,"wipeout_trades_counterfactual":m}
 Y=[];_p=len(dev_cands)
 if _p>=100:
  for X,(_E,_D)in enumerate([(.25,.43),(.43,.62),(.62,.81),(.81,1.)],start=1):_o=dev_cands[int(_E*_p)]["t0"];_n=dev_cands[min(_p-1,int(_D*_p)-1)]["t0"];W=[c for c in dev_cands if(_o+purge_sec)<=c["t0"]<=_n];_i=evaluate_portfolio_fn(W,best_cfg,latency_mode="500ms");Y.append({"fold":X,"oos_candidates":len(W),"trades":_i["trades"],"total_pnl":_i["total_pnl"],"win_rate":_i["win_rate"],"profit_factor":_i["profit_factor"],"wipeout_rate":_i["wipeout_rate"]})
 return{"cpcv_summary":F,"chainlink_proxy_audit":j,"bankroll_mc":J,"top5_summary":D,"live_counterfactual":b,"cv_folds":Y}
def run_subhourly_v395_wfo_ablation_suite(cands,evaluate_portfolio_fn,purge_sec=9e2):
 m=sorted([c for c in cands if c.get("hz")=="15m"],key=lambda x:x["t0"]);o=sorted([c for c in cands if c.get("hz")=="5m"],key=lambda x:x["t0"])
 def b(items,embargo):
  if len(items)<12:return list(items),[],[]
  y=[c["t0"]for c in items];x=y[int(.5*len(y))];r=y[int(.75*len(y))];F=[c for c in items if c["exp_ts"]<=x];E=[c for c in items if c["t0"]>=(x+embargo)and c["exp_ts"]<=r];D=[c for c in items if c["t0"]>=(r+embargo)];return F,E,D
 w,v,u=b(m,purge_sec);C,B,A=b(o,max(3e2,purge_sec*.5));f=[c for c in(w+v)if 60.<=c["tte"]<=480. and.75<=abs(c.get("z_oracle",.0))<=2.5];h=[c for c in u if 60.<=c["tte"]<=480. and.75<=abs(c.get("z_oracle",.0))<=2.5]
 def d(rows,df_v,jvm):
  if not rows:return.25
  c=.0
  for r in rows:_,x=compute_v395_pricing_and_twap_gate(r,df=df_v,jump_vol_mult=jvm,use_kemna_vorst=True);y=1. if r.get("won")else.0;c+=(x-y)**2
  return round(c/len(rows),6)
 k=[];e={"df":None,"jump_vol_mult":1.,"dev_brier":1.}
 for n in(None,4.,6.,8.):
  for l in(1.,1.15,1.25):
   t=d(f,n,l);z=d(h,n,l);s={"df":"gaussian"if n is None else n,"jump_vol_mult":l,"dev_n":len(f),"dev_brier":t,"holdout_n":len(h),"holdout_brier":z};k.append(s)
   if t<e["dev_brier"]:e={"df":s["df"],"jump_vol_mult":l,"dev_brier":t,"holdout_brier":z}
 j={"assets":("BTC","ETH","SOL"),"horizons":("15m",),"min_tte_15m":90.,"max_tte_15m":480.,"min_tte_5m":60.,"max_tte_5m":180.,"min_tte_1h":150.,"max_tte_1h":6e2,"min_px":.55,"max_px":.81,"max_spread":.03,"min_l1_usd":12.,"min_cushion":6e-4,"min_z":.78,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True,"entry_mode":"cascade_v4","fak_buffer":.02,"cascade_ticket_usd":16.5,"elastic_downsnap_usd":12.,"min_elastic_usd":8.,"exit_policy":"hold_98","ratchet_arm":None,"ratchet_drop":.06,"salvage_mode":"spot_persist","wrong_side_thresh":9e-4,"salvage_persist_s":18.,"clob_drop_thresh":.3,"final_45s_unwind":False}
 def a(label,overrides,slices):c={**j,**overrides};F,E,D=slices;y=evaluate_portfolio_fn(F,c,latency_mode="500ms")if F else{"trades":0,"total_pnl":.0,"profit_factor":.0,"win_rate":.0};x=evaluate_portfolio_fn(E,c,latency_mode="500ms")if E else{"trades":0,"total_pnl":.0,"profit_factor":.0,"win_rate":.0};r=evaluate_portfolio_fn(D,c,latency_mode="500ms")if D else{"trades":0,"total_pnl":.0,"profit_factor":.0,"win_rate":.0};return{"label":label,"train":{"trades":y["trades"],"pnl":y["total_pnl"],"pf":y["profit_factor"],"wr":y["win_rate"]},"val":{"trades":x["trades"],"pnl":x["total_pnl"],"pf":x["profit_factor"],"wr":x["win_rate"]},"sealed_holdout":{"trades":r["trades"],"pnl":r["total_pnl"],"pf":r["profit_factor"],"wr":r["win_rate"]}}
 g=[a("BASELINE_15M_CASCADE_TAKER_90_480",{},(w,v,u)),a("KEMNA_VORST_TWAP_BRIDGE_45_480",{"min_tte_15m":45.,"use_kemna_vorst":True},(w,v,u)),a("HYBRID_ZSPLIT_1.15_UNSHIELDED_MAKER",{"hybrid_z_split":True,"z_taker_cut":1.15,"use_complement_shield":False,"include_maker_rebate":False},(w,v,u)),a("HYBRID_ZSPLIT_1.15_COMP_SHIELD_NO_REBATE",{"hybrid_z_split":True,"z_taker_cut":1.15,"use_complement_shield":True,"include_maker_rebate":False},(w,v,u)),a("HYBRID_ZSPLIT_1.15_COMP_SHIELD_WITH_20PCT_REBATE",{"hybrid_z_split":True,"z_taker_cut":1.15,"use_complement_shield":True,"include_maker_rebate":True},(w,v,u)),a("HYBRID_ZSPLIT_1.25_COMP_SHIELD_WITH_20PCT_REBATE",{"hybrid_z_split":True,"z_taker_cut":1.25,"use_complement_shield":True,"include_maker_rebate":True},(w,v,u)),a("STUDENT_T_DF4_UNIT_VAR_JVM_1.15",{"v395_df":4.,"v395_jump_vol_mult":1.15,"use_kemna_vorst":True},(w,v,u)),a("COINBASE_250MS_IMPULSE_VETO_2.5BPS",{"cb_250ms_veto_bps":-2.5},(w,v,u))];i=[]
 if o:
  for q,p in[(("BTC",),"BTC_5M_ONLY"),(("SOL",),"SOL_5M_CANARY"),(("BTC","ETH","SOL"),"ALL_CRYPTO_5M")]:i.append(a(p,{"assets":q,"horizons":("5m",),"min_z":.8,"use_kemna_vorst":True},(C,B,A)))
 return{"counts":{"subhourly_15m_total":len(m),"subhourly_5m_total":len(o)},"splits_15m":{"train":len(w),"val":len(v),"sealed_holdout":len(u)},"splits_5m":{"train":len(C),"val":len(B),"sealed_holdout":len(A)},"brier_calibration_selected_on_dev":e,"brier_calibration_grid":k,"ablations_15m":g,"ablations_5m":i}
# ======================================================================================
# [04/20] MODULE: src/polymarket_research/net_alpha_opportunity_engine.py
# PURPOSE: v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine
# ======================================================================================

import json;import math;import os;import threading;import time;from pathlib import Path;from typing import Any,Dict,Iterable,List,Optional,Tuple
try:import orjson as _orjson
except ImportError:_orjson=None
_INV_SQRT2=.7071067811865475
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
 def b(raw):
  E=[]
  for D in raw or[]:
   if isinstance(D,dict):p,s=float(D.get("price")or.0),float(D.get("size")or.0)
   elif isinstance(D,(list,tuple))and len(D)>=2:p,s=float(D[0]),float(D[1])
   else:continue
   if p>.0 and s>.0:E.append((p,s))
  E.sort(key=lambda x:x[0]);return E
 w=b(asks_yes_raw);v=b(asks_no_raw)
 if not w or not v:return{"filled":False,"reason":"EMPTY_SIDE_BOOK"}
 m=w[0][0]*w[0][1];l=v[0][0]*v[0][1];h=round(min(m,l),2);u,t=w[0][0],v[0][0];f=(compute_category_taker_fee_per_share(u,fee_rate,fee_exponent)+compute_category_taker_fee_per_share(t,fee_rate,fee_exponent))
 if(u+t+f)>max_complete_set_cost+.015:return{"filled":False,"reason":"NO_UNDERROUND","best_pair_net":round(u+t+f,5)}
 o=sum(s for p,s in w if p<=u+.02);n=sum(s for p,s in v if p<=t+.02);e=int(math.floor(float(target_budget_usd)/max(.1,u+t)));A=int(min(e,math.floor(o),math.floor(n)))
 if A<int(min_shares):return{"filled":False,"reason":"INSUFFICIENT_EQUAL_SHARES","l1_usd":h}
 def a(levels,q_req):
  D=q_req;s=.0;p=.0
  for H,G in levels:
   F=min(D,G);s+=F*H;p=max(p,H);D-=F
   if D<=1e-6:break
  if D>1e-5:return None
  E=s/q_req;x=compute_category_taker_fee_per_share(E,fee_rate,fee_exponent);return E,x,p
 C=a(w,float(A));B=a(v,float(A))
 if C is None or B is None:return{"filled":False,"reason":"DEPTH_WALK_SHORTFALL","l1_usd":h}
 r,k,z=C;q,j,y=B;d=r+k+q+j
 if d>max_complete_set_cost+1e-6:return{"filled":False,"reason":"NET_COST_ABOVE_CAP","box_cost_net":round(d,5),"l1_usd":h}
 g=A*(r+q);i=A*(k+j);c=A*(1.-d);return{"filled":True,"market_id":str(market_id),"condition_id":str(condition_id),"yes_token":str(yes_token),"no_token":str(no_token),"shares":A,"vwap":round(r+q,5),"eff_px":round(d,5),"box_cost_net":round(d,5),"riskless_floor_per_pair":round(1.-d,5),"guaranteed_min_profit_usd":round(c,4),"spent_usd":round(g,2),"fee_usd":round(i,4),"limit_yes":round(z,4),"limit_no":round(y,4),"avail_yes_shares":round(o,2),"avail_no_shares":round(n,2),"l1_usd":h}
def evaluate_cross_oracle_basis_box_ev(spot_px,k_low,k_high,c_taker_net,tte_sec,sigma_1h=.0055,mu_basis_bps=2.,sigma_basis_bps=8.5):
 if spot_px<=.0 or k_low<=.0 or k_high<k_low:return{"eligible":False,"ev_per_pair":-1.,"p_double_loss":1.,"p_double_win":.0}
 f=(k_high-k_low)/k_low;l=max(4e-4,float(sigma_1h)*math.sqrt(max(15.,float(tte_sec))/3600.));e=l*math.sqrt(min(1.,20./max(20.,float(tte_sec))))*.35;j=math.hypot(float(sigma_basis_bps)/1e4,e);o=float(mu_basis_bps)/1e4;n=math.log(k_high/spot_px)/l;m=math.log(k_low/spot_px)/l;d=max(.0,min(1.,_norm_cdf(n)-_norm_cdf(m)));h=_norm_cdf((-f-abs(o))/max(1e-5,j));a=min(1.,.35+.65*math.exp(-abs(math.log(((k_low+k_high)*.5)/spot_px))/l));c=max(5e-4,min(.45,h*a));g=max(.0,d*(1.-h));k=max(.0,1.-g-c);b=2.*g+1.*k;i=b-float(c_taker_net);return{"classification":"PROBABILISTIC_CROSS_ORACLE_RV","is_riskless":False,"p_double_win":round(g,4),"p_single_floor":round(k,4),"p_double_loss":round(c,4),"expected_payout":round(b,4),"ev_per_pair":round(i,4),"expected_net_profit_per_pair":round(i,4),"eligible":bool(i>=.018 and c<=.045)}
_SHM_CACHE_LOCK=threading.Lock();_SHM_READ_CACHE={};_SHM_CREATED_DIRS=set()
def _global_positions_shm_path():
 b=os.environ.get("PM_FAST_TICK_DIR")
 if b:return Path(b)/"pm_global_positions.json"
 a=Path("/dev/shm")
 if a.exists():return a/"pm_global_positions.json"
 return Path(__file__).resolve().parent.parent.parent/"data"/"polymarket"/"pm_global_positions.json"
def read_global_positions_shm(max_age_sec=120.):
 j=_global_positions_shm_path();f=str(j)
 try:m=os.stat(f)
 except OSError:return{"daemons":{}}
 e=m.st_mtime_ns;i=m.st_size;a=None
 with _SHM_CACHE_LOCK:
  g=_SHM_READ_CACHE.get(f)
  if g is not None and g[0]==e and g[1]==i:a=g[2]
 try:
  if a is None:
   d=j.read_bytes();h=(_orjson.loads(d)if _orjson is not None else json.loads(d.decode("utf-8")))
   if not isinstance(h,dict):return{"daemons":{}}
   c=h.get("daemons")
   if not isinstance(c,dict):return{"daemons":{}}
   a=c
   with _SHM_CACHE_LOCK:_SHM_READ_CACHE[f]=(e,i,a)
  if not a:return{"daemons":{}}
  l=time.time();b={k:v for k,v in a.items()if isinstance(v,dict)and(l-float(v.get("updated_ts")or.0))<=max_age_sec};return{"daemons":b}
 except Exception:return{"daemons":{}}
def publish_global_positions_shm(daemon_name,positions):
 h=_global_positions_shm_path();b=str(h);f=None
 try:
  a=str(h.parent)
  if a not in _SHM_CREATED_DIRS:h.parent.mkdir(parents=True,exist_ok=True);_SHM_CREATED_DIRS.add(a)
  i=read_global_positions_shm(max_age_sec=6e2);e=dict(i.get("daemons")or{});d=[]
  for p in positions:
   if not isinstance(p,dict):continue
   d.append({"id":str(p.get("trade_id")or p.get("position_id")or""),"sleeve":str(p.get("sleeve")or""),"asset":str(p.get("asset")or p.get("asset_or_city")or"").upper(),"side":str(p.get("target_token")or p.get("side")or"").upper(),"strike":float(p.get("candle_open_spot")or(p.get("extra")or{}).get("strike")or.0),"expiry_ts":float(p.get("candle_expiry_ts")or p.get("close_ts")or.0),"notional_usd":float(p.get("notional_usd")or p.get("entry_eff_px_t1000")or.0)})
  g=round(time.time(),3);e[str(daemon_name)]={"updated_ts":g,"positions":d};c={"updated_at_ts":g,"daemons":e};f=h.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
  if _orjson is not None:f.write_bytes(_orjson.dumps(c))
  else:f.write_text(json.dumps(c,separators=(",",":")),encoding="utf-8")
  os.replace(f,b)
  try:
   j=os.stat(b)
   with _SHM_CACHE_LOCK:_SHM_READ_CACHE[b]=(j.st_mtime_ns,j.st_size,e)
  except OSError:pass
  return True
 except Exception:
  if f is not None:
   try:f.unlink(missing_ok=True)
   except Exception:pass
  return False
_CORRIDOR_SIDES=frozenset(("UP","DOWN","YES","NO"))
def _precompute_pos_tuples(active_global_positions):
 if not active_global_positions:return[]
 b=[]
 for a in active_global_positions:b.append((str(a.get("asset")or"").upper(),float(a.get("expiry_ts")or.0),str(a.get("side")or"").upper(),float(a.get("strike")or.0)))
 return b
def _compute_capital_efficiency_utility_fast(candidate,pos_tuples):
 m=float(candidate.get("net_edge")or.0);s=max(.05,float(candidate.get("ask_vwap")or.5));q=float(candidate.get("p_model")or(s+m));p=max(15.,float(candidate.get("tte_sec")or 3600.));i=max(.08,min(24.,p/3600.));c=(m/s)/i;e=max(.0,1.-q);f=.08*(e*e);b=.0;a=.0
 if pos_tuples:
  h=str(candidate.get("asset")or"").upper()
  if h:
   j=str(candidate.get("side")or"").upper();l=float(candidate.get("expiry_ts")or.0);g=float(candidate.get("strike")or.0);d=j in _CORRIDOR_SIDES
   for o,t,r,k in pos_tuples:
    if o!=h:continue
    if l>.0 and t>.0 and abs(l-t)<=9e2:
     if r==j and d:b+=.12
     elif(g>.0 and k>.0 and((r=="UP"and j=="DOWN"and k<g)or(r=="DOWN"and j=="UP"and g<k))):a+=.25
 n=c-f-b+a;return(round(c,4),round(n,4),round(i,3),round(b,4),round(a,4))
def compute_capital_efficiency_utility(candidate,active_global_positions=None):d,e,c,b,a=_compute_capital_efficiency_utility_fast(candidate,_precompute_pos_tuples(active_global_positions));return{"ev_per_dollar_hour":d,"utility_score":e,"lock_hours":c,"corr_penalty":b,"corridor_completion_bonus":a}
def rank_opportunities_capital_auction(opportunities,active_global_positions=None,active_positions=None):
 a=active_global_positions if active_global_positions is not None else active_positions;b=_precompute_pos_tuples(a);d=[]
 for h in opportunities:
  g=h.copy();e,f,_,_,c=_compute_capital_efficiency_utility_fast(g,b);g["ev_per_dollar_hour"]=e;g["utility_score"]=f
  if c>.0:g["synthetic_corridor_completion"]=True
  d.append(g)
 d.sort(key=lambda x:(-float(x.get("utility_score",.0)),-float(x.get("net_edge",.0))));return d
def infer_polymarket_tick_size(price_hint):
 a=float(price_hint or.0)
 if(.0<a<.04)or a>=.96:return.001
 return.01
def compute_capital_velocity_ev(net_edge_per_share,expected_hold_seconds=3e2,*,fill_prob=1.,early_recycle_factor=1.,net_cost_per_share=1.):b=max(.05,float(net_cost_per_share or 1.));a=max(10.,float(expected_hold_seconds or 3e2)*max(.1,float(early_recycle_factor or 1.)));c=max(.01,min(1.,float(fill_prob if fill_prob is not None else 1.)));return(float(net_edge_per_share or.0)/b)*c/a
def compute_smart_maker_bid(best_bid,best_ask,max_cap_px=None,min_floor_px=.001,obi_l1=.0,tick_size=None,*,max_ceiling=None,max_bid_px=None,min_floor=None):
 def a(v,dflt=.0):return float(v)if(isinstance(v,(int,float))and not isinstance(v,bool)and math.isfinite(v))else dflt
 e=a(max_cap_px if max_cap_px is not None else(max_ceiling if max_ceiling is not None else(max_bid_px if max_bid_px is not None else.99)),.99);d=a(min_floor if min_floor is not None else min_floor_px,.001);o=a(best_ask,.0);n=a(best_bid,.0);j=a(obi_l1,.0);l=a(tick_size,.0);h=o if o>.0 else e;k=l if l>.0 else infer_polymarket_tick_size(h);g=3 if k<.009 else 2;b=(o-k)if o>k else e;c=min(e,b);m=round(math.floor((c+1e-9)/k)*k,g)
 if m<d-1e-9 or m<=.0:return None,False
 if n>.0:
  f=(o-n)if o>n else.0;i=round(n+k,g)
  if f>=(2.*k-1e-9)and i<=m+1e-9:return min(m,i),True
  if n<=m+1e-9:
   if.0<f<=(k+1e-9)and j<-.35:return None,False
   return round(min(m,n),g),False
 return m,True
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
 b=_precompute_pos_tuples(active_positions)
 def a(s):
  u=str(s.get("shock_direction")or"BUY").upper();v="UP"if u in("BUY","UP")else"DOWN";y=(s.get("pre_shock_features_t0")or{}).get(v)or{};p=float(y.get("best_ask")or y.get("vwap_$25")or y.get("effective_price_$25")or.7);p=max(.05,min(.95,p));h=abs(float(s.get("candle_distance_pct")or.0));x=max(30.,float(s.get("seconds_to_expiry")or 3e2));t=str(s.get("asset")or"BTC").upper();k=float(s.get("candle_sigma")or.0);z=str(s.get("horizon")or"").lower();o=(k*(2. if"15m"in z else(math.sqrt(12.)if z in("5m","5min","300s")or"-5m"in z else 1.))if k>.0 else(.005 if t=="BTC"else(.0068 if t=="ETH"else.009)));j=max(.00025,o*math.sqrt(x/3600.));w=min(1.,abs(float(s.get("shock_ofi")if s.get("shock_ofi")is not None else.85)));r=(h/1e2)/j+.35*w;q=.5*(1.+math.erf(r*_INV_SQRT2));n=compute_category_taker_fee_per_share(p,.07,1.);i=q*.98+(1.-q)*.36;c=(i-p-n)/(p+n);m=float(y.get("age_ask_ms")if y.get("age_ask_ms")is not None else 3e2);l=1.15 if m>=250. else 1.;e=.015 if t=="BTC"else(.008 if t=="ETH"else.0);d=c*l+e
  if b:_,_,_,g,f=_compute_capital_efficiency_utility_fast({"asset":t,"side":v,"expiry_ts":s.get("candle_expiry_ts")or s.get("expiry_ts")or.0,"strike":s.get("candle_open_spot")or.0,"net_edge":max(.0,i-p-n),"ask_vwap":p,"p_model":q,"tte_sec":x},b);d+=f-g
  return round(d,6),r
 return sorted(shocks,key=a,reverse=True)
# ======================================================================================
# [05/20] MODULE: src/polymarket_research/weather_metar_engine.py
# PURPOSE: Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb
# ======================================================================================

import json;import logging;import math;import re;import time;import urllib.parse;import urllib.request;from dataclasses import dataclass,field;from datetime import date,datetime,timedelta,timezone;from typing import Any,Dict,List,Optional,Tuple;from src.polymarket_research.riskless_protocol_v2_expansion import safe_zoneinfo as ZoneInfo;logger=logging.getLogger("WeatherMetarEngine");GAMMA_API_URL="https://gamma-api.polymarket.com";CLOB_API_URL="https://clob.polymarket.com";AWC_METAR_URL="https://aviationweather.gov/api/data/metar";AWC_STATION_URL="https://aviationweather.gov/api/data/stationinfo";IEM_ASOS_URL="https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py";OPEN_METEO_ENSEMBLE_URL="https://ensemble-api.open-meteo.com/v1/ensemble";OPEN_METEO_FORECAST_URL="https://api.open-meteo.com/v1/forecast";OPEN_METEO_HIST_FORECAST_URL="https://historical-forecast-api.open-meteo.com/v1/forecast";STATION_CATALOG={"RJTT":(35.5523,139.7798,"Asia/Tokyo","Tokyo"),"EGLC":(51.5053,.0553,"Europe/London","London"),"ZSPD":(31.1434,121.8052,"Asia/Shanghai","Shanghai"),"ZSQD":(36.3667,120.0944,"Asia/Shanghai","Qingdao"),"WMKK":(2.7456,101.7099,"Asia/Kuala_Lumpur","Kuala Lumpur"),"RCSS":(25.0694,121.5525,"Asia/Taipei","Taipei"),"EDDM":(48.3538,11.7861,"Europe/Berlin","Munich"),"LFPB":(48.9694,2.4414,"Europe/Paris","Paris"),"ZUUU":(30.5785,103.9471,"Asia/Shanghai","Chengdu"),"SBGR":(-23.4356,-46.4731,"America/Sao_Paulo","Sao Paulo"),"LEMD":(40.4719,-3.5626,"Europe/Madrid","Madrid"),"ZHHH":(30.7838,114.2081,"Asia/Shanghai","Wuhan"),"EHAM":(52.3086,4.7639,"Europe/Amsterdam","Amsterdam"),"EPWA":(52.1657,20.9671,"Europe/Warsaw","Warsaw"),"WSSS":(1.3502,103.994,"Asia/Singapore","Singapore"),"ZBAA":(40.0801,116.5846,"Asia/Shanghai","Beijing"),"ZUCK":(29.7192,106.6417,"Asia/Shanghai","Chongqing"),"LTFM":(41.2753,28.7519,"Europe/Istanbul","Istanbul"),"KMIA":(25.7959,-80.287,"America/New_York","Miami"),"OPKC":(24.9065,67.1608,"Asia/Karachi","Karachi"),"KLGA":(40.7769,-73.874,"America/New_York","NYC"),"RKSI":(37.4602,126.4407,"Asia/Seoul","Seoul"),"LLBG":(32.0114,34.8867,"Asia/Jerusalem","Tel Aviv"),"ZGGG":(23.3924,113.2988,"Asia/Shanghai","Guangzhou"),"OEJN":(21.6796,39.1565,"Asia/Riyadh","Jeddah"),"VILK":(26.7606,80.8893,"Asia/Kolkata","Lucknow"),"ZGSZ":(22.6393,113.8107,"Asia/Shanghai","Shenzhen"),"LIMC":(45.6306,8.7281,"Europe/Rome","Milan"),"RKPK":(35.1795,128.9382,"Asia/Seoul","Busan"),"LTAC":(40.1281,32.9951,"Europe/Istanbul","Ankara"),"SAEZ":(-34.8222,-58.5358,"America/Argentina/Buenos_Aires","Buenos Aires"),"KSEA":(47.4502,-122.3088,"America/Los_Angeles","Seattle"),"KDAL":(32.8471,-96.8518,"America/Chicago","Dallas"),"NZWN":(-41.3272,174.8053,"Pacific/Auckland","Wellington"),"KSFO":(37.6213,-122.379,"America/Los_Angeles","San Francisco"),"KORD":(41.9742,-87.9073,"America/Chicago","Chicago"),"MMMX":(19.4363,-99.0721,"America/Mexico_City","Mexico City"),"CYYZ":(43.6777,-79.6248,"America/Toronto","Toronto"),"RPLL":(14.5086,121.0194,"Asia/Manila","Manila"),"EFHK":(60.3172,24.9633,"Europe/Helsinki","Helsinki"),"KATL":(33.6407,-84.4277,"America/New_York","Atlanta"),"KHOU":(29.6454,-95.2789,"America/Chicago","Houston"),"KDEN":(39.8561,-104.6737,"America/Denver","Denver"),"UUWW":(55.5915,37.2615,"Europe/Moscow","Moscow"),"MPMG":(8.9733,-79.5556,"America/Panama","Panama City"),"KAUS":(30.1945,-97.6699,"America/Chicago","Austin"),"KLAX":(33.9425,-118.4081,"America/Los_Angeles","Los Angeles"),"FACT":(-33.9648,18.6017,"Africa/Johannesburg","Cape Town"),"HKO":(22.3019,114.1742,"Asia/Hong_Kong","Hong Kong"),"ZSJN":(36.8572,117.216,"Asia/Shanghai","Jinan"),"ZHCC":(34.5197,113.8408,"Asia/Shanghai","Zhengzhou")};HKO_1MIN_CSV_URL="https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature.csv";HKO_MAXMIN_CSV_URL="https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_since_midnight_maxmin.csv";HKO_RHRREAD_URL="https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en";_T_REMARK_RE=re.compile(r"(?:^|\s)T([01])(\d{3})(?:\d{4}|////)(?=\s|$)");_BODY_TEMP_RE=re.compile(r"(?:^|\s)(M?\d{2})/(?:M?\d{2}|//)(?=\s|$)");_METAR_TS_RE=re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b");_SYNOPTIC_6H_MAX_RE=re.compile(r"(?:^|\s)1([01])(\d{3})(?=\s|$)");_SYNOPTIC_6H_MIN_RE=re.compile(r"(?:^|\s)2([01])(\d{3})(?=\s|$)");_SYNOPTIC_24H_EXT_RE=re.compile(r"(?:^|\s)4([01])(\d{3})([01])(\d{3})(?=\s|$)");_ASOS_AO_RE=re.compile(r"\bAO[12]\b")
def _build_us_asos_valid_tenths_int():
 d=set()
 for c in range(-130,165):b=((c-32)*50.)/9.;a=int(math.floor(b+.5+1e-12))if b>=.0 else-int(math.floor(-b+.5+1e-12));d.add(a)
 return frozenset(d)
US_ASOS_VALID_TENTHS_INT=_build_us_asos_valid_tenths_int();_CONVECTIVE_WX_RE=re.compile(r"(?:^|\s)(?:[-+]|VC)?(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)(?:TS|SH|RA|DZ|SN|SG|PL|GR|GS)*\b" r"|(?:FEW|SCT|BKN|OVC)\d{3}(?:CB|TCU)\b" r"|\b(?:CB|TCU|RAB\d{2,4}|TSB\d{2,4}|P\d{4})\b");_AWC_ICAO_RE=re.compile(r"aviationweather\.gov/api/data/metar\?ids=([A-Z0-9]{4})",re.IGNORECASE);_NOAA_ICAO_RE=re.compile(r"weather\.gov/wrh/timeseries\?site=([A-Z0-9]{4})",re.IGNORECASE);_PAREN_ICAO_RE=re.compile(r"\(([A-Z]{4})\)");_SERIES_TO_ICAO={"tokyo-daily-weather":"RJTT","tokyo-daily-lowest-temperature":"RJTT","london-daily-weather":"EGLC","london-daily-lowest-temperature":"EGLC","shanghai-daily-weather":"ZSPD","shanghai-daily-lowest-temperature":"ZSPD","chengdu-daily-weather":"ZUUU","chengdu-daily-lowest-temperature":"ZUUU","beijing-daily-weather":"ZBAA","beijing-daily-lowest-temperature":"ZBAA","wuhan-daily-weather":"ZHHH","wuhan-daily-lowest-temperature":"ZHHH","chongqing-daily-weather":"ZUCK","chongqing-daily-lowest-temperature":"ZUCK","guangzhou-daily-weather":"ZGGG","guangzhou-daily-lowest-temperature":"ZGGG","shenzhen-daily-weather":"ZGSZ","shenzhen-daily-lowest-temperature":"ZGSZ","qingdao-daily-weather":"ZSQD","qingdao-daily-lowest-temperature":"ZSQD","paris-daily-weather":"LFPB","paris-daily-lowest-temperature":"LFPB","munich-daily-weather":"EDDM","munich-daily-lowest-temperature":"EDDM","miami-daily-weather":"KMIA","miami-daily-lowest-temperature":"KMIA","nyc-daily-weather":"KLGA","nyc-daily-lowest-temperature":"KLGA","houston-daily-weather":"KHOU","houston-daily-lowest-temperature":"KHOU","austin-daily-weather":"KAUS","austin-daily-lowest-temperature":"KAUS","los-angeles-daily-weather":"KLAX","los-angeles-daily-lowest-temperature":"KLAX","seoul-daily-weather":"RKSI","seoul-daily-lowest-temperature":"RKSI","busan-daily-weather":"RKPK","busan-daily-lowest-temperature":"RKPK","chicago-daily-weather":"KORD","chicago-daily-lowest-temperature":"KORD","seattle-daily-weather":"KSEA","seattle-daily-lowest-temperature":"KSEA","dallas-daily-weather":"KDAL","dallas-daily-lowest-temperature":"KDAL","madrid-daily-weather":"LEMD","madrid-daily-lowest-temperature":"LEMD","amsterdam-daily-weather":"EHAM","amsterdam-daily-lowest-temperature":"EHAM","taipei-daily-weather":"RCSS","taipei-daily-lowest-temperature":"RCSS","singapore-daily-weather":"WSSS","singapore-daily-lowest-temperature":"WSSS","hong-kong-daily-weather":"HKO","hong-kong-daily-lowest-temperature":"HKO","wellington-daily-weather":"NZWN","wellington-daily-lowest-temperature":"NZWN","warsaw-daily-weather":"EPWA","warsaw-daily-lowest-temperature":"EPWA","buenos-aires-daily-weather":"SAEZ","buenos-aires-daily-lowest-temperature":"SAEZ","helsinki-daily-weather":"EFHK","helsinki-daily-lowest-temperature":"EFHK","denver-daily-weather":"KDEN","denver-daily-lowest-temperature":"KDEN","toronto-daily-weather":"CYYZ","toronto-daily-lowest-temperature":"CYYZ","mexico-city-daily-weather":"MMMX","mexico-city-daily-lowest-temperature":"MMMX","tel-aviv-daily-weather":"LLBG","tel-aviv-daily-lowest-temperature":"LLBG","istanbul-daily-weather":"LTFM","istanbul-daily-lowest-temperature":"LTFM","sao-paulo-daily-weather":"SBGR","sao-paulo-daily-lowest-temperature":"SBGR","manila-daily-weather":"RPLL","manila-daily-lowest-temperature":"RPLL","atlanta-daily-weather":"KATL","atlanta-daily-lowest-temperature":"KATL","san-francisco-daily-weather":"KSFO","san-francisco-daily-lowest-temperature":"KSFO","panama-daily-weather":"MPMG","panama-daily-lowest-temperature":"MPMG","milan-daily-weather":"LIMC","milan-daily-lowest-temperature":"LIMC","lucknow-daily-weather":"VILK","lucknow-daily-lowest-temperature":"VILK","karachi-daily-weather":"OPKC","karachi-daily-lowest-temperature":"OPKC","jeddah-daily-weather":"OEJN","jeddah-daily-lowest-temperature":"OEJN","ankara-daily-weather":"LTAC","ankara-daily-lowest-temperature":"LTAC","kuala-lumpur-daily-weather":"WMKK","kuala-lumpur-daily-lowest-temperature":"WMKK","moscow-daily-weather":"UUWW","moscow-daily-lowest-temperature":"UUWW","cape-town-daily-weather":"FACT","cape-town-daily-lowest-temperature":"FACT","jinan-daily-weather":"ZSJN","jinan-daily-lowest-temperature":"ZSJN","zhengzhou-daily-weather":"ZHCC","zhengzhou-daily-lowest-temperature":"ZHCC"};HIGH_VOLUME_WEATHER_SERIES=("hong-kong-daily-weather","hong-kong-daily-lowest-temperature","atlanta-daily-weather","atlanta-daily-lowest-temperature","san-francisco-daily-weather","san-francisco-daily-lowest-temperature","seattle-daily-weather","seattle-daily-lowest-temperature","amsterdam-daily-weather","amsterdam-daily-lowest-temperature","panama-daily-weather","manila-daily-weather","mexico-city-daily-weather","munich-daily-weather","milan-daily-weather","istanbul-daily-weather","lucknow-daily-weather","tel-aviv-daily-weather","karachi-daily-weather","sao-paulo-daily-weather","jeddah-daily-weather","ankara-daily-weather","busan-daily-weather","cape-town-daily-weather","cape-town-daily-lowest-temperature","qingdao-daily-weather","kuala-lumpur-daily-weather","moscow-daily-weather","chengdu-daily-weather","beijing-daily-weather","seoul-daily-weather","seoul-daily-lowest-temperature","shanghai-daily-weather","shanghai-daily-lowest-temperature","tokyo-daily-weather","tokyo-daily-lowest-temperature","wuhan-daily-weather","chongqing-daily-weather","guangzhou-daily-weather","shenzhen-daily-weather","taipei-daily-weather","singapore-daily-weather","nyc-daily-weather","nyc-daily-lowest-temperature","chicago-daily-weather","chicago-daily-lowest-temperature","london-daily-weather","london-daily-lowest-temperature","miami-daily-weather","miami-daily-lowest-temperature","austin-daily-weather","austin-daily-lowest-temperature","los-angeles-daily-weather","los-angeles-daily-lowest-temperature","houston-daily-weather","houston-daily-lowest-temperature","dallas-daily-weather","dallas-daily-lowest-temperature","wellington-daily-weather","wellington-daily-lowest-temperature","warsaw-daily-weather","warsaw-daily-lowest-temperature","buenos-aires-daily-weather","helsinki-daily-weather","denver-daily-weather","denver-daily-lowest-temperature","toronto-daily-weather","toronto-daily-lowest-temperature","paris-daily-weather","paris-daily-lowest-temperature","madrid-daily-weather");_MONTH_MAP={"january":1,"jan":1,"february":2,"feb":2,"march":3,"mar":3,"april":4,"apr":4,"may":5,"june":6,"jun":6,"july":7,"jul":7,"august":8,"aug":8,"september":9,"sep":9,"sept":9,"october":10,"oct":10,"november":11,"nov":11,"december":12,"dec":12}
@dataclass
class WeatherBucket:
 market_id:str;condition_id:str;label:str;question:str;yes_token:str;no_token:str;unit:str;low_bound:float;high_bound:float;outcome_yes_resolved:Optional[int]=None;fee_rate:float=.0;fee_exponent:float=1.;neg_risk:Optional[bool]=None;rewards_min_size:float=.0;rewards_max_spread:float=.0;question_index:Optional[int]=None
 def contains_rounded(a,rounded_int):return a.low_bound<=rounded_int<=a.high_bound
@dataclass
class WeatherEventSpec:event_id:str;slug:str;series_slug:str;title:str;icao:str;city:str;lat:float;lon:float;tz_name:str;obs_date:date;metric:str;unit:str;fee_type:str;end_date_iso:str;buckets:List[WeatherBucket]=field(default_factory=list)
@dataclass
class MetarObservation:icao:str;utc_dt:datetime;local_dt:datetime;temp_c:float;has_t_remark:bool;raw_line:str;has_convective_precip:bool=False;is_corrected:bool=False;is_anomalous:bool=False;has_maintenance_indicator:bool=False;rmk_6h_max_c:Optional[float]=None;rmk_6h_min_c:Optional[float]=None;rmk_24h_max_c:Optional[float]=None;rmk_24h_min_c:Optional[float]=None
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
 I=raw_line.strip()
 if not I:return None
 B=I.upper();w=B.split()
 if not w:return None
 if"SPECI"in w[:3]:return None
 if icao.upper()not in w[:4]:return None
 v="COR"in w[:5];j=explicit_utc_dt
 if j is None:
  H=_METAR_TS_RE.search(B)
  if not H:return None
  A,G,z=int(H.group(1)),int(H.group(2)),int(H.group(3));m=[]
  for y in(-32,0,32):
   u=ref_utc+timedelta(days=y)
   try:F=datetime(u.year,u.month,A,G,z,tzinfo=timezone.utc);m.append(F)
   except ValueError:continue
  if not m:return None
  j=min(m,key=lambda c:abs((c-ref_utc).total_seconds()))
 r="RMK"in B;o,q=B.split("RMK",1)if r else(B,B);t=_BODY_TEMP_RE.search(o);g=None
 if t:J=t.group(1);g=-float(int(J[1:]))if J.startswith("M")else float(int(J))
 s=icao.upper();a=False;x=_T_REMARK_RE.search(q)
 if x:
  h=(-1 if x.group(1)=="1"else 1)*int(x.group(2));i=h/10.;l=True
  if len(s)==4 and s.startswith("K")and h not in US_ASOS_VALID_TENTHS_INT:a=True
  if g is not None and abs(i-g)>.65:a=True
 else:
  if g is None:return None
  i=g;l=False
 f=None;e=None;d=None;b=None
 if r and _ASOS_AO_RE.search(q):
  if j.hour in(23,0,5,6,11,12,17,18):
   E=_SYNOPTIC_6H_MAX_RE.search(q)
   if E:f=(-1. if E.group(1)=="1"else 1.)*(int(E.group(2))/10.)
   D=_SYNOPTIC_6H_MIN_RE.search(q)
   if D:e=(-1. if D.group(1)=="1"else 1.)*(int(D.group(2))/10.)
  C=_SYNOPTIC_24H_EXT_RE.search(q)
  if C:d=(-1. if C.group(1)=="1"else 1.)*(int(C.group(2))/10.);b=(-1. if C.group(3)=="1"else 1.)*(int(C.group(4))/10.)
 p=j.astimezone(ZoneInfo(tz_name));k=bool(_CONVECTIVE_WX_RE.search(B));n=bool(r and("$"in q.split()or q.rstrip().endswith("$")));return MetarObservation(icao=s,utc_dt=j,local_dt=p,temp_c=i,has_t_remark=l,raw_line=I,has_convective_precip=k,is_corrected=v,is_anomalous=a,has_maintenance_indicator=n,rmk_6h_max_c=f,rmk_6h_min_c=e,rmk_24h_max_c=d,rmk_24h_min_c=b)
def has_metar_oracle_contradiction(obs_seq):
 if not obs_seq:return False
 for o in obs_seq:
  if bool(getattr(o,"is_anomalous",False)):return True
 for i in obs_seq:
  h=getattr(i,"utc_dt",None)
  if h is None:continue
  g=getattr(i,"rmk_6h_max_c",None);f=getattr(i,"rmk_6h_min_c",None);c=getattr(i,"rmk_24h_max_c",None);b=getattr(i,"rmk_24h_min_c",None)
  if g is None and f is None and c is None and b is None:continue
  for e in obs_seq:
   d=getattr(e,"utc_dt",None);a=getattr(e,"temp_c",None)
   if d is None or a is None:continue
   j=(h-d).total_seconds()
   if.0<=j<=21300.:
    if g is not None and float(a)>float(g)+.15:return True
    if f is not None and float(a)<float(f)-.15:return True
   if.0<=j<=85800.:
    if c is not None and float(a)>float(c)+.15:return True
    if b is not None and float(a)<float(b)-.15:return True
 return False
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
 C=str(ev.get("title")or"");M=C.lower()
 if"highest temperature in"in M:h="HIGH"
 elif"lowest temperature in"in M:h="LOW"
 else:return None
 G=ev.get("markets")or[]
 if len(G)<4:return None
 n=ev.get("series")or[];A=str(n[0].get("slug")if n else(ev.get("seriesSlug")or series_slug_hint or""));F=str(G[0].get("description")or ev.get("description")or"");c=None;z=_AWC_ICAO_RE.search(F)
 if z and"SPECI"in F:c=z.group(1).upper()
 elif"weather.gov.hk"in F.lower()and"hong kong observatory"in F.lower():c="HKO"
 elif"routine (metar)"in F.lower()or"speci"in F.lower():
  l=_PAREN_ICAO_RE.search(F)
  if l and l.group(1).upper()in STATION_CATALOG:c=l.group(1).upper()
 elif allow_historical_same_station:
  y=_NOAA_ICAO_RE.search(F);B=_PAREN_ICAO_RE.search(F)
  if y and y.group(1).upper()in STATION_CATALOG:c=y.group(1).upper()
  elif B and B.group(1).upper()in STATION_CATALOG:c=B.group(1).upper()
  elif A in _SERIES_TO_ICAO:c=_SERIES_TO_ICAO[A]
 if not c or c not in STATION_CATALOG:return None
 J,I,u,E=STATION_CATALOG[c];t=str(ev.get("endDate")or G[0].get("endDate")or"");q=parse_obs_date_from_event(C,F,t)
 if q is None:return None
 e=str(G[0].get("feeType")or"zero_fees");s=[]
 for m in G:
  H=str(m.get("groupItemTitle")or m.get("question")or"");x=parse_bucket_bounds(H)
  if not x:continue
  D,L,K=x;g=m.get("clobTokenIds")
  if isinstance(g,str):
   try:g=json.loads(g)
   except Exception:g=[]
  if not g or len(g)<2:continue
  a=None
  if m.get("closed"):
   w=m.get("outcomePrices")
   if isinstance(w,str):
    try:w=json.loads(w)
    except Exception:w=None
   if isinstance(w,list)and len(w)>=2:
    try:
     if float(w[0])>=.99:a=1
     elif float(w[1])>=.99:a=0
    except Exception:pass
  i=m.get("feeSchedule")if isinstance(m.get("feeSchedule"),dict)else{};f=bool(m.get("feesEnabled",False));p=float(i.get("rate")or.0);k=p if(f and p>.0)else.0;o=float(i.get("exponent")or 1.);v=m.get("negRisk")if m.get("negRisk")is not None else ev.get("negRisk");j=bool(v)if v is not None else None;r=str(m.get("questionID")or"").strip();d=None
  if r.startswith("0x")and len(r)==66:
   try:d=int(r[-2:],16)
   except ValueError:d=None
  s.append(WeatherBucket(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),label=H,question=str(m.get("question")or H),yes_token=str(g[0]),no_token=str(g[1]),unit=D,low_bound=L,high_bound=K,outcome_yes_resolved=a,fee_rate=k,fee_exponent=o,neg_risk=j,rewards_min_size=float(m.get("rewardsMinSize")or.0),rewards_max_spread=float(m.get("rewardsMaxSpread")or.0),question_index=d))
 if len(s)<4:return None
 s.sort(key=lambda b:(b.low_bound,b.high_bound))
 if any(b.fee_rate>.0 for b in s):e="fees_enabled"
 return WeatherEventSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),series_slug=A,title=C,icao=c,city=E,lat=J,lon=I,tz_name=u,obs_date=q,metric=h,unit=s[0].unit,fee_type=e,end_date_iso=t,buckets=s)
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
 except Exception:pass
 try:a=urllib.request.urlopen(urllib.request.Request(HKO_MAXMIN_CSV_URL,headers=i),timeout=timeout).read().decode("utf-8-sig",errors="ignore")
 except Exception:pass
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
 x=ZoneInfo(tz_name);e=datetime(obs_date.year,obs_date.month,obs_date.day,0,0,tzinfo=x);g=e+timedelta(days=1);b=g.astimezone(timezone.utc)+timedelta(hours=3);m=datetime.now(timezone.utc);d=min(m,b);j=(m-e.astimezone(timezone.utc)).total_seconds()/86400.;f={}
 def a(parsed_obs):
  y=int(parsed_obs.utc_dt.timestamp());o=f.get(y)
  if(o is None or parsed_obs.is_corrected or(not o.is_corrected and(parsed_obs.has_t_remark or not o.has_t_remark))):f[y]=parsed_obs
 if j<=13.5:
  t=d.strftime("%Y-%m-%dT%H:%M:%SZ");w=f"{AWC_METAR_URL}?ids={icao.upper()}&format=raw&date={t}&hours=36"
  try:
   p=urllib.request.Request(w,headers={"User-Agent":"DominusWeatherEngine/1.0"});i=urllib.request.urlopen(p,timeout=timeout).read().decode("utf-8",errors="ignore")
   for u in reversed(i.splitlines()):
    c=parse_metar_line(u,icao,d,tz_name)
    if c and c.local_dt.date()==obs_date:a(c)
  except Exception:pass
 if not f:
  l=e.astimezone(timezone.utc)-timedelta(hours=2);s=g.astimezone(timezone.utc)+timedelta(hours=2);h=icao.upper()[1:]if(len(icao)==4 and icao.upper().startswith("K"))else icao.upper();q=urllib.parse.urlencode({"station":h,"data":"metar","year1":l.year,"month1":l.month,"day1":l.day,"year2":s.year,"month2":s.month,"day2":s.day,"tz":"Etc/UTC","format":"onlycomma","latlon":"no","elev":"no","missing":"M","trace":"T","direct":"no","report_type":["3","4"]},doseq=True)
  try:
   p=urllib.request.Request(f"{IEM_ASOS_URL}?{q}",headers={"User-Agent":"DominusWeatherEngine/1.0"});k=urllib.request.urlopen(p,timeout=timeout+4.).read().decode("utf-8",errors="ignore")
   for v in k.splitlines()[1:]:
    r=v.split(",",2)
    if len(r)<3:continue
    try:n=datetime.strptime(r[1].strip(),"%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:continue
    c=parse_metar_line(r[2],icao,n,tz_name,explicit_utc_dt=n)
    if c and c.local_dt.date()==obs_date:a(c)
  except Exception:pass
 return sorted(f.values(),key=lambda o:o.utc_dt)
def compute_weather_probabilities(spec,eval_utc,metars_so_far,ensemble_hourly_c,forecast_sigma_base_c=1.15,bias_decay_tau_hr=6.,taf_extreme_c=None):
 tz=ZoneInfo(spec.tz_name);Z=eval_utc.astimezone(tz);I=datetime(spec.obs_date.year,spec.obs_date.month,spec.obs_date.day,0,0,tzinfo=tz);N=I+timedelta(days=1);_d=[o for o in metars_so_far if o.utc_dt<=eval_utc and o.local_dt.date()==spec.obs_date];_e=len(_d)>0;Y=_d[-1]if _e else None;B=any(bool(getattr(o,"is_corrected",False))for o in _d);x=any(bool(getattr(o,"has_maintenance_indicator",False))for o in _d);q=has_metar_oracle_contradiction(_d)
 if _e:
  if spec.metric=="HIGH":e=max(o.temp_c for o in _d)
  else:e=min(o.temp_c for o in _d)
  l=celsius_to_market_int(e,spec.unit)
 else:e=None;l=None
 y=.0;k=bias_decay_tau_hr;i=False;c=False
 if Y is not None:
  M=[o for o in _d if(eval_utc-o.utc_dt).total_seconds()<=12600.][-3:];i=any(o.has_convective_precip for o in _d if(eval_utc-o.utc_dt).total_seconds()<=7200.);Q=Z.hour+Z.minute/60.;u=(spec.metric=="HIGH"and 9.<=Q<=16.25 and e is not None and(e-Y.temp_c)>=1.2)
  if ensemble_hourly_c and M:
   X=[]
   for _m in M:
    W=int(round(_m.utc_dt.timestamp()/3600.)*3600);V=ensemble_hourly_c.get(W)
    if V:U=sum(V)/len(V);X.append(_m.temp_c-U)
   if X:
    X.sort()
    if len(X)==3:E=X[1]
    else:E=sum(X)/len(X)
    y=max(-1.5,min(1.5,E))
    if spec.metric=="HIGH"and E<-.35 and(i or u):c=True;y=max(-.45,E*.2);k=min(bias_decay_tau_hr,1.2)
  elif i or u:c=spec.metric=="HIGH"
 T=[];P=max(I,Z.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1))
 while P<N:T.append(int(P.astimezone(timezone.utc).timestamp()));P+=timedelta(hours=1)
 if Z<N and not T:T.append(int(N.astimezone(timezone.utc).timestamp()))
 m=[len(ensemble_hourly_c[t])for t in T if t in ensemble_hourly_c and ensemble_hourly_c[t]]
 if not m and ensemble_hourly_c:m=[len(v)for v in ensemble_hourly_c.values()if v]
 _l=min(m)if m else 0;_g=[-2.1,-1.5,-1.1,-.75,-.45,-.2,.0,.2,.45,.75,1.1,1.5,2.1];L=[.0 for _ in spec.buckets];f=.0;H=[];G=len(T)
 if Z>=N and l is not None:
  for _f,b in enumerate(spec.buckets):L[_f]=1. if b.contains_rounded(l)else.0
  f=1.
 elif _l>0 and G>0:
  S=forecast_sigma_base_c*min(1.,math.sqrt(max(1.,G)/10.))
  if _l>=15:g=max(.45,.55*S)
  else:g=max(.75,S)
  if c:g*=1.45
  for _k in range(_l):
   D=[]
   for _o in T:
    _n=ensemble_hourly_c.get(_o)
    if not _n:continue
    v=_n[min(_k,len(_n)-1)];_j=max(.0,(_o-eval_utc.timestamp())/3600.);O=y*math.exp(-_j/max(.5,k));D.append(v+O)
   if not D:continue
   n=max(D)if spec.metric=="HIGH"else min(D)
   if taf_extreme_c is not None and math.isfinite(float(taf_extreme_c)):n=.85*n+.15*float(taf_extreme_c)
   H.append(n)
   for z in _g:
    w=math.exp(-.5*z*z);_c=n+z*g
    if e is not None:K=max(e,_c)if spec.metric=="HIGH"else min(e,_c)
    else:K=_c
    _b=celsius_to_market_int(K,spec.unit)
    for _i,b in enumerate(spec.buckets):
     if b.contains_rounded(_b):L[_i]+=w;break
    f+=w
 r=.0
 if len(H)>=4:_h=sorted(H);_r=_h[int(.25*(len(_h)-1))];_q=_h[int(.75*(len(_h)-1))];r=max(.0,_q-_r)
 if f<=.0:F=[1./len(spec.buckets)for _ in spec.buckets]
 else:F=[max(.001,min(.998,w/f))for w in L];_p=sum(F);F=[p/_p for p in F]
 a=False;d=.0;h=None;j=.0
 if _e and Y is not None and e is not None and l is not None:
  J=Z.hour+Z.minute/60.
  for _f,b in enumerate(spec.buckets):
   if b.contains_rounded(l):h=_f;j=F[_f];break
  if spec.metric=="HIGH":
   d=e-Y.temp_c;R=17.5 if(i or c)else 15.75;_a=(Z.date()>spec.obs_date)or(Z.date()==spec.obs_date and J>=R)
   if _a and(Z.date()>spec.obs_date or d>=.8)and j>=.88:a=True
  else:
   A=Y.temp_c-e;d=A;C=(Z.date()>spec.obs_date)or(Z.date()==spec.obs_date and J>=22.5);s=(Z.date()==spec.obs_date and 9.5<=J<22.5 and A>=2.5 and _l>=15 and bool(H)and min(H)>=(e+2.)and j>=.93)
   if((C and j>=.9 and(Z.date()>spec.obs_date or A>=1.))or s):a=True
  if B or q or(x and G>0):a=False
 return{"probs":F,"has_obs":_e,"obs_count":len(_d),"has_corrected_obs":B,"has_maintenance_obs":x,"has_oracle_contradiction":q,"latest_temp_c":Y.temp_c if Y else None,"running_ext_c":e,"running_ext_int":l,"bias_c":round(y,3),"convective_cold_pool":c,"ensemble_member_count":_l,"peak_iqr_c":round(r,3),"rem_hours_count":G,"is_solar_lock":a,"cooling_cushion_c":round(d,2),"locked_bucket_idx":h,"p_locked_bucket":round(j,4)}
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
  except Exception:
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
NWS_API_LATEST_OBS_TMPL="https://api.weather.gov/stations/{icao}/observations/latest";NWS_API_CLI_LIST_TMPL="https://api.weather.gov/products/types/CLI/locations/{wfo}";NWS_API_USER_AGENT="DominusWeatherEngine/1.0 (contact@dominus-research.local)";WEATHER_NEIGHBOR_STATIONS={"KLGA":("KJFK","KEWR","KTEB"),"KJFK":("KLGA","KEWR"),"KORD":("KMDW","KPWK"),"KMDW":("KORD",),"KMIA":("KOPF","KFLL"),"KSEA":("KBFI","KPAE"),"KDFW":("KDAL","KAFW"),"KDAL":("KDFW",),"KLAX":("KSMO","KBUR"),"EGLC":("EGLL","EGKB"),"EGLL":("EGLC",)};_NWS_CLI_MAX_RE=re.compile(r"TEMPERATURE\s*\(F\).*?MAXIMUM\s+(-?\d+)\s+",re.IGNORECASE|re.DOTALL);_NWS_CLI_MIN_RE=re.compile(r"TEMPERATURE\s*\(F\).*?MINIMUM\s+(-?\d+)\s+",re.IGNORECASE|re.DOTALL);_NWS_DSM_MAX_RE=re.compile(r"\bMS\s+\d+\s+\d{4}/\d{2}/\d{2}\b.*?\b(-?\d{1,3})/(-?\d{1,3})\b")
def fetch_nws_latest_observation_sync(icao,tz_name="America/New_York",*,timeout=3.):
 m=str(icao or"").strip().upper()
 if len(m)!=4:return None
 l=NWS_API_LATEST_OBS_TMPL.format(icao=m)
 try:
  k=urllib.request.Request(l,headers={"User-Agent":NWS_API_USER_AGENT,"Accept":"application/geo+json"});d=json.loads(urllib.request.urlopen(k,timeout=timeout).read().decode("utf-8",errors="ignore"));i=d.get("properties")if isinstance(d,dict)else None
  if not isinstance(i,dict):return None
  a=str(i.get("rawMessage")or"").strip();g=str(i.get("timestamp")or"").strip();f=datetime.fromisoformat(g.replace("Z","+00:00"))if g else datetime.now(timezone.utc)
  if a:
   e=parse_metar_line(a,m,f,tz_name,explicit_utc_dt=f)
   if e is not None:return e
  if a.upper().startswith("SPECI ")or" SPECI "in a.upper()or"$"in a:return None
  c=i.get("temperature")if isinstance(i.get("temperature"),dict)else{};h=c.get("value")
  if h is None:return None
  j=float(h);b=f.astimezone(ZoneInfo(tz_name));return MetarObservation(icao=m,utc_dt=f,local_dt=b,temp_c=j,has_t_remark=False,raw_line=a or f"NWS_JSON {m} {j:.1f}C",is_corrected=False,has_maintenance_indicator=False)
 except Exception:return None
def parse_nws_dsm_or_cli_text(text,*,product_type="CLI"):
 d=str(text or"")
 if not d.strip():return None
 e=str(product_type or"CLI").upper();c=_NWS_CLI_MAX_RE.search(d);b=_NWS_CLI_MIN_RE.search(d)
 if c:return{"product_type":e,"max_temp_f":float(c.group(1)),"min_temp_f":float(b.group(1))if b else None,"is_final_cli":e=="CLI"}
 a=_NWS_DSM_MAX_RE.search(d)
 if a:return{"product_type":"DSM","max_temp_f":float(a.group(1)),"min_temp_f":float(a.group(2)),"is_final_cli":False}
 return None
def check_neighbor_station_temp_anomaly(primary_obs,neighbor_observations,*,max_delta_c=6.):
 if primary_obs.has_maintenance_indicator:return True,"D006_ASOS_DOLLAR_MAINTENANCE_FLAG"
 b=[o for o in neighbor_observations if o.icao!=primary_obs.icao and not o.has_maintenance_indicator and abs((o.utc_dt-primary_obs.utc_dt).total_seconds())<=5400.]
 if len(b)<2:return False,"INSUFFICIENT_NEIGHBORS"
 a=[abs(float(primary_obs.temp_c)-float(p.temp_c))for p in b]
 if min(a)>float(max_delta_c):return True,f"SPATIAL_SENSOR_ANOMALY_DELTA_{min(a):.2f}C"
 return False,"OK"
# ======================================================================================
# [06/20] MODULE: src/polymarket_research/barrier_onetouch_svi_engine.py
# PURPOSE: Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)
# ======================================================================================

import json;import logging;import math;import re;import urllib.request;from dataclasses import dataclass;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;_INV_SQRT2=.7071067811865475
def _fast_norm_cdf(x):return.5*(1.+math.erf(x*_INV_SQRT2))
try:from src.polymarket_research.deribit_svi_surface import(GLOBAL_SVI_ENGINE,SVIParams,scale_svi_sticky_delta)
except Exception:GLOBAL_SVI_ENGINE=None;SVIParams=Any;scale_svi_sticky_delta=None
logger=logging.getLogger("BarrierOneTouchEngine");GAMMA_API_URL="https://gamma-api.polymarket.com";BINANCE_API_URL="https://api.binance.com";BINANCE_FAPI_URL="https://fapi.binance.com";HIT_SERIES=[("BTC","DAILY","bitcoin-hit-price-daily"),("BTC","WEEKLY","bitcoin-hit-price-weekly"),("BTC","MONTHLY","bitcoin-hit-price-monthly"),("ETH","DAILY","ethereum-hit-price-daily"),("ETH","WEEKLY","ethereum-hit-price-weekly"),("ETH","MONTHLY","ethereum-hit-price-monthly"),("SOL","DAILY","solana-hit-price-daily"),("SOL","WEEKLY","solana-hit-price-weekly"),("SOL","MONTHLY","solana-hit-price-monthly"),("XRP","DAILY","xrp-hit-price-daily"),("XRP","WEEKLY","xrp-hit-price-weekly"),("XRP","MONTHLY","xrp-hit-price-monthly"),("BNB","MONTHLY","bnb-hit-price-monthly"),("DOGE","MONTHLY","dogecoin-hit-price-monthly"),("HYPE","MONTHLY","hyperliquid-hit-price-monthly")];ASSET_BINANCE_SYMBOL={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT","BNB":"BNBUSDT","DOGE":"DOGEUSDT","HYPE":"HYPEUSDT"};ASSET_BINANCE_FUTURES_ONLY=frozenset({"HYPE"});ASSET_VOL_MULT_VS_BTC={"BTC":1.,"ETH":1.28,"SOL":1.75,"XRP":1.85,"BNB":1.45,"DOGE":2.1,"HYPE":2.35}
@dataclass
class BarrierRungSpec:event_id:str;series_slug:str;horizon_group:str;asset:str;market_id:str;condition_id:str;question:str;group_label:str;strike:float;direction:str;start_ts:float;end_ts:float;yes_token:str;no_token:str;fee_rate:float=.07;resolved_yes:Optional[int]=None;fee_exponent:float=1.
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
 p=str(ev.get("endDate")or"");i=str(ev.get("startDate")or ev.get("creationDate")or"")
 if not p:return[]
 try:t=datetime.fromisoformat(p.replace("Z","+00:00")).timestamp()
 except Exception:return[]
 g={"DAILY":86400.,"WEEKLY":7*86400.,"MONTHLY":30*86400.}.get(horizon_group,86400.);c=t-g
 if i:
  try:
   o=datetime.fromisoformat(i.replace("Z","+00:00")).timestamp()
   if t-35*86400.<=o<t:c=max(c,o)
  except Exception:pass
 y=_CRYPTO_MONTH_RE.search(str(ev.get("title")or""))
 if y:
  try:from src.polymarket_research.riskless_protocol_v2_expansion import get_us_eastern_tz as e;B=e();x=_CRYPTO_MONTHS[y.group(1).lower()];w=int(y.group(2))if y.group(2)else datetime.fromtimestamp(t-5*86400.,tz=B).year;c=max(c,datetime(w,x,1,0,0,tzinfo=B).timestamp())
  except Exception:pass
 u=[]
 for m in ev.get("markets")or[]:
  q=str(m.get("question")or"");A=str(m.get("groupItemTitle")or"");h=parse_barrier_direction(q,A);s=parse_strike_from_text(q,A)
  if not h or not s or s<=0:continue
  f=m.get("clobTokenIds")
  if isinstance(f,str):
   try:f=json.loads(f)
   except Exception:f=[]
  if not f or len(f)<2:continue
  a=None
  if m.get("closed"):
   r=m.get("outcomePrices")
   if isinstance(r,str):
    try:r=json.loads(r)
    except Exception:r=None
   if isinstance(r,list)and len(r)>=2:
    try:
     if float(r[0])>=.99:a=1
     elif float(r[1])>=.99:a=0
    except Exception:pass
  d=c
  for n in(m.get("startDate"),m.get("createdAt")):
   if n:
    try:
     v=datetime.fromisoformat(str(n).replace("Z","+00:00")).timestamp()
     if c-3600.<=v<t:z=60. if(v>c+3e2 or"creation of this market"in str(m.get("description")or"").lower())else.0;d=max(d,min(t-60.,v+z))
    except Exception:pass
  l=.07;j=1.
  try:
   from src.polymarket_research.tradfi_sports_zero_fee_engine import _extract_market_fee_rate as b
   if any(k in m for k in("feeSchedule","feeType","feesEnabled","takerBaseFee")):l,j=b(m)
  except Exception:pass
  u.append(BarrierRungSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,horizon_group=horizon_group,asset=asset.upper(),market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),question=q,group_label=A,strike=s,direction=h,start_ts=d,end_ts=t,yes_token=str(f[0]),no_token=str(f[1]),fee_rate=l,resolved_yes=a,fee_exponent=j))
 return u
def first_passage_touch_prob(spot,strike,tte_seconds,iv_annual,direction,wick_vol_multiplier=1.12,jump_tail_blend=.08,forward_drift_annual=.0,realized_vol_ratio=1.):
 if spot<=.0 or strike<=.0:return.0
 if direction=="UP"and spot>=strike:return 1.
 if direction=="DOWN"and spot<=strike:return 1.
 if tte_seconds<=1.:return.0
 i=tte_seconds/(365.25*86400.);b=abs(math.log(strike/spot));h=max(-.3,min(.4,float(forward_drift_annual or.0)))
 def a(sig):
  m=max(.08,min(4.,sig));l=m*math.sqrt(i)
  if l<=1e-8:return.0
  q=(h-.5*(m**2))if direction=="UP"else(-h+.5*(m**2));o=(-b+q*i)/l;n=(-b-q*i)/l;k=max(-60.,min(60.,(2.*q*b)/(m**2)));p=_fast_norm_cdf(o)+math.exp(k)*_fast_norm_cdf(n);return max(1e-4,min(.9999,p))
 e=iv_annual*wick_vol_multiplier;d=a(e);j=a(e*1.65);g=max(.5,min(3.5,float(realized_vol_ratio or 1.)))**1.5;c=min(.35,max(.02,float(jump_tail_blend)*g))if abs(realized_vol_ratio-1.)>1e-6 else float(jump_tail_blend);f=(1.-c)*d+c*j;return max(1e-4,min(.9999,f))
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
# [07/20] MODULE: src/polymarket_research/multistrike_svi_scalper.py
# PURPOSE: Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner
# ======================================================================================

import json;import logging;import math;import re;from dataclasses import dataclass;from datetime import datetime;from typing import Any,Dict,List,Optional,Tuple;_INV_SQRT2=.7071067811865475
def _fast_norm_cdf(x):return.5*(1.+math.erf(x*_INV_SQRT2))
def _fast_bs_call(F,K,T,sigma):
 if T<=.0 or sigma<=.0 or K<=.0 or F<=.0:return max(.0,F-K)
 a=sigma*math.sqrt(T);c=(math.log(F/K)+.5*(sigma**2)*T)/a;b=c-a;return F*_fast_norm_cdf(c)-K*_fast_norm_cdf(b)
def _fast_bl_digital(F,K,T_years,svi):b=max(1e-6,T_years);g=max(.01,K*.001);f=math.log((K+g)/F);e=math.log(max(1e-6,K-g)/F);d=_fast_bs_call(F,K+g,b,svi.implied_vol(f,t_override=b));c=_fast_bs_call(F,max(1e-6,K-g),b,svi.implied_vol(e,t_override=b));a=-(d-c)/(2.*g);return max(1e-4,min(.9999,a))
try:from src.polymarket_research.deribit_svi_surface import(GLOBAL_SVI_ENGINE,SVIParams,compute_breeden_litzenberger_digital,enforce_monotone_ladder_probabilities)
except Exception:GLOBAL_SVI_ENGINE=None;SVIParams=Any;compute_breeden_litzenberger_digital=None;enforce_monotone_ladder_probabilities=None
logger=logging.getLogger("MultiStrikeSVIScalper");STRIKE_SERIES=[("BTC","btc-multi-strikes-weekly"),("ETH","ethereum-multi-strikes-weekly"),("SOL","solana-multi-strikes-weekly"),("XRP","xrp-multi-strikes-weekly")];ASSET_VOL_MULT_VS_BTC={"BTC":1.,"ETH":1.28,"SOL":1.75,"XRP":1.85}
@dataclass
class StrikeRungSpec:event_id:str;series_slug:str;asset:str;title:str;market_id:str;condition_id:str;question:str;strike:float;is_downward:bool;end_ts:float;yes_token:str;no_token:str;fee_rate:float=.07;resolved_yes:Optional[int]=None
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
   m=d[i];l=d[j]
   if l["strike"]<=m["strike"]:continue
   c=float(m.get("ask_yes")or 1.);b=float(l.get("ask_no")or 1.)
   if not(.01<=c<=.98 and.01<=b<=.98):continue
   f=float(m.get("fee_rate",fee_rate)or.0);e=float(l.get("fee_rate",fee_rate)or.0);k=min(.5,max(.0,f*(1.-c)))if f>.0 else.0;h=min(.5,max(.0,e*(1.-b)))if e>.0 else.0;a=c/(1.-k)+b/(1.-h)
   if a<=.996:g.append({"low_strike":m["strike"],"high_strike":l["strike"],"low_market_id":m["market_id"],"high_market_id":l["market_id"],"yes_token_low":m["yes_token"],"no_token_high":l["no_token"],"ask_yes_low":c,"ask_no_high":b,"box_cost_net":round(a,5),"riskless_floor_edge":round(1.-a,5)})
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
class NegRiskBracketSpec:event_id:str;series_slug:str;asset:str;title:str;market_id:str;condition_id:str;question:str;bracket_kind:str;k_low:Optional[float];k_high:Optional[float];end_ts:float;yes_token:str;no_token:str;fee_rate:float=.07;resolution_source:str=""
@dataclass
class DailyUpDownSpec:event_id:str;series_slug:str;asset:str;title:str;market_id:str;condition_id:str;start_ts:float;end_ts:float;up_token:str;down_token:str;fee_rate:float=.07;resolution_source:str=""
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
 g=sorted([r for r in rungs if not r.is_downward],key=lambda r:float(r.strike));o={round(float(r.strike),4):r for r in g};c={round(float(b.k_low),4):b for b in brackets if b.bracket_kind=="RANGE"and b.k_low is not None and b.k_high is not None};n=[]
 for t in brackets:
  if spot>.0:
   s=t.k_low if t.k_low is not None else(t.k_high or spot);j=tail_max_strike_dist_log if t.bracket_kind in("LOWER_TAIL","UPPER_TAIL")else max_strike_dist_log
   if s>0 and abs(math.log(s/spot))>j:continue
  if t.bracket_kind=="LOWER_TAIL"and t.k_high is not None:
   e=round(float(t.k_high),4);h=o.get(e);i=[r for r in g if float(r.strike)<float(t.k_high)-1e-6];m=c.get(e)
   if i:l=i[-1];n.append({"bundle_id":f"TAIL_LOW_OVERLAP_YES_{t.market_id}_{l.market_id}","label":f"NR_YES(<{t.k_high:g})+MS_YES(>{l.strike:g})","guaranteed_payout":1.,"pin_free_verified":True,"end_ts":t.end_ts,"legs":[{"token_id":t.yes_token,"opp_token_id":t.no_token,"condition_id":t.condition_id,"neg_risk":True,"strike":float(t.k_high),"side":"YES","market_id":t.market_id,"fee_rate":t.fee_rate,"label":f"NR_YES<{t.k_high:g}"},{"token_id":l.yes_token,"opp_token_id":l.no_token,"condition_id":l.condition_id,"neg_risk":False,"strike":float(l.strike),"side":"YES","market_id":l.market_id,"fee_rate":l.fee_rate,"label":f"MS_YES>{l.strike:g}"}]})
   elif h is not None and m is not None:n.append({"bundle_id":f"TAIL_LOW_PIN_SAFE_BRIDGE_{t.market_id}_{m.market_id}_{h.market_id}","label":f"NR_YES(<{t.k_high:g})+NR_YES([{m.k_low:g},{m.k_high:g}])+MS_YES(>{h.strike:g})","guaranteed_payout":1.,"pin_free_verified":True,"end_ts":t.end_ts,"legs":[{"token_id":t.yes_token,"opp_token_id":t.no_token,"condition_id":t.condition_id,"neg_risk":True,"strike":float(t.k_high),"side":"YES","market_id":t.market_id,"fee_rate":t.fee_rate,"label":f"NR_YES<{t.k_high:g}"},{"token_id":m.yes_token,"opp_token_id":m.no_token,"condition_id":m.condition_id,"neg_risk":True,"strike":float(m.k_high or t.k_high),"side":"YES","market_id":m.market_id,"fee_rate":m.fee_rate,"label":f"NR_YES[{m.k_low:g}-{m.k_high:g}]"},{"token_id":h.yes_token,"opp_token_id":h.no_token,"condition_id":h.condition_id,"neg_risk":False,"strike":float(h.strike),"side":"YES","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"MS_YES>{h.strike:g}"}]})
   if h is not None:n.append({"bundle_id":f"TAIL_LOW_NO_{t.market_id}_{h.market_id}","label":f"NR_NO(<{t.k_high:g})+MS_NO(>{h.strike:g})","guaranteed_payout":1.,"pin_free_verified":True,"end_ts":t.end_ts,"legs":[{"token_id":t.no_token,"opp_token_id":t.yes_token,"condition_id":t.condition_id,"neg_risk":True,"strike":float(t.k_high),"side":"NO","market_id":t.market_id,"fee_rate":t.fee_rate,"label":f"NR_NO<{t.k_high:g}"},{"token_id":h.no_token,"opp_token_id":h.yes_token,"condition_id":h.condition_id,"neg_risk":False,"strike":float(h.strike),"side":"NO","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"MS_NO>{h.strike:g}"}]})
  elif t.bracket_kind=="UPPER_TAIL"and t.k_low is not None:
   h=o.get(round(float(t.k_low),4));k=(t.question or"").lower();a=any(u in k for u in("or above","or higher","at least",">="))
   if h is not None:
    n.append({"bundle_id":f"TAIL_HIGH_A_{t.market_id}_{h.market_id}","label":f"NR_YES(>{t.k_low:g})+MS_NO(>{h.strike:g})","guaranteed_payout":1.,"pin_free_verified":True,"end_ts":t.end_ts,"legs":[{"token_id":t.yes_token,"opp_token_id":t.no_token,"condition_id":t.condition_id,"neg_risk":True,"strike":float(t.k_low),"side":"YES","market_id":t.market_id,"fee_rate":t.fee_rate,"label":f"NR_YES>{t.k_low:g}"},{"token_id":h.no_token,"opp_token_id":h.yes_token,"condition_id":h.condition_id,"neg_risk":False,"strike":float(h.strike),"side":"NO","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"MS_NO>{h.strike:g}"}]});d=[r for r in g if float(r.strike)<float(t.k_low)-1e-6]
    if not a:n.append({"bundle_id":f"TAIL_HIGH_B_{t.market_id}_{h.market_id}","label":f"NR_NO(>{t.k_low:g})+MS_YES(>{h.strike:g})","guaranteed_payout":1.,"pin_free_verified":True,"end_ts":t.end_ts,"legs":[{"token_id":t.no_token,"opp_token_id":t.yes_token,"condition_id":t.condition_id,"neg_risk":True,"strike":float(t.k_low),"side":"NO","market_id":t.market_id,"fee_rate":t.fee_rate,"label":f"NR_NO>{t.k_low:g}"},{"token_id":h.yes_token,"opp_token_id":h.no_token,"condition_id":h.condition_id,"neg_risk":False,"strike":float(h.strike),"side":"YES","market_id":h.market_id,"fee_rate":h.fee_rate,"label":f"MS_YES>{h.strike:g}"}]})
    elif d:f=d[-1];n.append({"bundle_id":f"TAIL_HIGH_OVERLAP_B_{t.market_id}_{f.market_id}","label":f"NR_NO(>={t.k_low:g})+MS_YES(>{f.strike:g})","guaranteed_payout":1.,"pin_free_verified":True,"end_ts":t.end_ts,"legs":[{"token_id":t.no_token,"opp_token_id":t.yes_token,"condition_id":t.condition_id,"neg_risk":True,"strike":float(t.k_low),"side":"NO","market_id":t.market_id,"fee_rate":t.fee_rate,"label":f"NR_NO>={t.k_low:g}"},{"token_id":f.yes_token,"opp_token_id":f.no_token,"condition_id":f.condition_id,"neg_risk":False,"strike":float(f.strike),"side":"YES","market_id":f.market_id,"fee_rate":f.fee_rate,"label":f"MS_YES>{f.strike:g}"}]})
  elif t.bracket_kind=="RANGE"and t.k_low is not None and t.k_high is not None:
   q=o.get(round(float(t.k_low),4));p=o.get(round(float(t.k_high),4))
   if q is not None and p is not None:n.append({"bundle_id":f"PART_1X_{t.market_id}_{q.market_id}_{p.market_id}","label":f"MS_NO(>{t.k_low:g})+NR_YES([{t.k_low:g},{t.k_high:g}])+MS_YES(>{t.k_high:g})","guaranteed_payout":1.,"end_ts":t.end_ts,"legs":[{"token_id":q.no_token,"side":"NO","market_id":q.market_id,"fee_rate":q.fee_rate,"label":f"MS_NO>{t.k_low:g}"},{"token_id":t.yes_token,"side":"YES","market_id":t.market_id,"fee_rate":t.fee_rate,"label":f"NR_YES[{t.k_low:g}-{t.k_high:g}]"},{"token_id":p.yes_token,"side":"YES","market_id":p.market_id,"fee_rate":p.fee_rate,"label":f"MS_YES>{t.k_high:g}"}]});n.append({"bundle_id":f"COMP_2X_{t.market_id}_{q.market_id}_{p.market_id}","label":f"MS_YES(>{t.k_low:g})+NR_NO([{t.k_low:g},{t.k_high:g}])+MS_NO(>{t.k_high:g})","guaranteed_payout":2.,"end_ts":t.end_ts,"legs":[{"token_id":q.yes_token,"side":"YES","market_id":q.market_id,"fee_rate":q.fee_rate,"label":f"MS_YES>{t.k_low:g}"},{"token_id":t.no_token,"side":"NO","market_id":t.market_id,"fee_rate":t.fee_rate,"label":f"NR_NO[{t.k_low:g}-{t.k_high:g}]"},{"token_id":p.no_token,"side":"NO","market_id":p.market_id,"fee_rate":p.fee_rate,"label":f"MS_NO>{t.k_high:g}"}]})
 return n
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
# [08/20] MODULE: src/polymarket_research/same_oracle_dominance_box.py
# PURPOSE: Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine
# ======================================================================================

import json;import math;from dataclasses import dataclass;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;CORE_LIVE_DOMINANCE_ASSETS=("BTC","ETH","SOL","XRP");EXPANSION_DOMINANCE_ASSETS=("BNB","DOGE","HYPE","ZEC");DOMINANCE_ASSETS=CORE_LIVE_DOMINANCE_ASSETS+EXPANSION_DOMINANCE_ASSETS;DOMINANCE_SERIES_SLUGS={"BTC":{"4h":"btc-up-or-down-4h","15m":"btc-up-or-down-15m","5m":"btc-up-or-down-5m"},"ETH":{"4h":"eth-up-or-down-4h","15m":"eth-up-or-down-15m","5m":"eth-up-or-down-5m"},"SOL":{"4h":"sol-up-or-down-4h","15m":"sol-up-or-down-15m","5m":"sol-up-or-down-5m"},"XRP":{"4h":"xrp-up-or-down-4h","15m":"xrp-up-or-down-15m","5m":"xrp-up-or-down-5m"},"BNB":{"4h":"bnb-up-or-down-4h","15m":"bnb-up-or-down-15m","5m":"bnb-up-or-down-5m"},"DOGE":{"4h":"doge-up-or-down-4h","15m":"doge-up-or-down-15m","5m":"doge-up-or-down-5m"},"HYPE":{"4h":"hype-up-or-down-4h","15m":"hype-up-or-down-15m","5m":"hype-up-or-down-5m"},"ZEC":{"4h":"zec-up-or-down-4h","15m":"zec-up-or-down-15m","5m":"zec-up-or-down-5m"}};METAL_DOMINANCE_ASSETS=("XAU","XAG");METAL_DOMINANCE_SERIES_SLUGS={"XAU":{"1h":"gold-up-or-down-1h","15m":"gold-up-or-down-15m"},"XAG":{"1h":"silver-up-or-down-1h","15m":"silver-up-or-down-15m"}};EMPIRICAL_BOX_ASSET_CAPS_USD={"BTC":150.,"ETH":75.,"SOL":22.,"XRP":22.,"BNB":22.,"HYPE":15.,"DOGE":15.,"ZEC":10.,"XAU":22.,"XAG":22.};MIN_CORRIDOR_BPS_BY_ASSET={"BTC":3.,"ETH":3.,"SOL":3.,"XRP":3.,"BNB":5.,"DOGE":5.,"HYPE":5.,"ZEC":6.,"XAU":4.,"XAG":4.}
def build_deterministic_updown_event_slug(asset,horizon,window_end_ts):
 e=HORIZON_TO_DURATION_SEC.get(str(horizon or"").strip().lower());d=str(asset or"").strip().upper();b={"BTC":"btc","ETH":"eth","SOL":"sol","XRP":"xrp","BNB":"bnb","DOGE":"doge","HYPE":"hype","ZEC":"zec"};c=b.get(d)
 if not e or not c or float(window_end_ts or.0)<=e:return None
 a=int(round(float(window_end_ts)-float(e)));return f"{c}-updown-{str(horizon).strip().lower()}-{a}"
POLYMARKET_CRYPTO_PRICE_URL="https://polymarket.com/api/crypto/crypto-price";GAMMA_EVENTS_URL="https://gamma-api.polymarket.com/events";HORIZON_TO_VARIANT={"4h":"fourhour","1h":"hourly","15m":"fifteen","5m":"fiveminute"};HORIZON_TO_DURATION_SEC={"4h":14400.,"1h":3600.,"15m":9e2,"5m":3e2}
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
 B,L,F=_sorted_asks(asks_a_raw,max_slip_cents);A,K,E=_sorted_asks(asks_b_raw,max_slip_cents)
 if not B or not A:return{"filled":False,"reason":"EMPTY_BOOK","best_sum":round(L+K,4)}
 i=_net_unit_cost_buy(L,fee_rate_a,fee_exponent_a)+_net_unit_cost_buy(K,fee_rate_b,fee_exponent_b)
 if i<min_box_cost_net-.025 or(L+K)<.855:return{"filled":False,"reason":"SUSPECT_INVERTED_ANTI_BOX","best_a":round(L,4),"best_b":round(K,4),"l1_box_cost_net":round(i,5)}
 if i>max_box_cost_net+.015:return{"filled":False,"reason":"BOX_TOO_EXPENSIVE_L1","best_a":round(L,4),"best_b":round(K,4),"l1_box_cost_net":round(i,5),"avail_pair_shares":int(math.floor(min(F,E)))}
 p=int(math.floor(min(F,E)))
 if p<max(5,min_shares):return{"filled":False,"reason":"INSUFFICIENT_PAIR_SHARES","best_a":round(L,4),"best_b":round(K,4),"l1_box_cost_net":round(i,5),"avail_pair_shares":p}
 r=int(math.floor(float(target_budget_usd)/max(.1,i)));j=min(r,p)
 if j<max(5,min_shares):return{"filled":False,"reason":"BUDGET_BELOW_MIN_SHARES","l1_box_cost_net":round(i,5),"avail_pair_shares":p}
 y=_walk_exact_shares(B,j,fee_rate_a,fee_exponent_a);x=_walk_exact_shares(A,j,fee_rate_b,fee_exponent_b)
 if y is None or x is None:return{"filled":False,"reason":"WALK_FAILED","avail_pair_shares":p}
 e=y["spent_usd"]+x["spent_usd"];f=y["fee_usd"]+x["fee_usd"];c=e+f;d=c/float(j)
 if c>target_budget_usd*1.02:
  J=int(math.floor(float(target_budget_usd)/d))
  if J<max(5,min_shares):return{"filled":False,"reason":"TRIMMED_BELOW_MIN_SHARES","box_cost_net":round(d,5)}
  j=J;y=_walk_exact_shares(B,j,fee_rate_a,fee_exponent_a);x=_walk_exact_shares(A,j,fee_rate_b,fee_exponent_b)
  if y is None or x is None:return{"filled":False,"reason":"WALK_TRIM_FAILED"}
  e=y["spent_usd"]+x["spent_usd"];f=y["fee_usd"]+x["fee_usd"];c=e+f;d=c/float(j)
 def b(wa_d,wb_d):pa,pb=float(wa_d["worst_px"]),float(wb_d["worst_px"]);return round(_net_unit_cost_buy(pa,fee_rate_a,fee_exponent_a)+_net_unit_cost_buy(pb,fee_rate_b,fee_exponent_b),6)
 if b(y,x)>max_box_cost_net+1e-6:
  W=max(5,int(min_shares));I=set()
  for z in(B,A):
   u=.0
   for _,H in z:
    u+=H;_a=int(math.floor(u+1e-9))
    if W<=_a<j:I.add(_a)
  n=False
  for G in sorted(I,reverse=True):
   Z=_walk_exact_shares(B,G,fee_rate_a,fee_exponent_a);Y=_walk_exact_shares(A,G,fee_rate_b,fee_exponent_b)
   if Z is None or Y is None:continue
   X=Z["spent_usd"]+Y["spent_usd"]
   if X<min_box_notional_usd:continue
   if b(Z,Y)<=max_box_cost_net+1e-6:j=G;y,x=Z,Y;e=X;f=y["fee_usd"]+x["fee_usd"];c=e+f;d=c/float(j);n=True;break
  if not n:return{"filled":False,"reason":"WORST_LIMIT_COST_ABOVE_CAP","best_a":round(L,4),"best_b":round(K,4),"box_cost_net":round(d,5),"worst_limit_cost_net":b(y,x),"l1_box_cost_net":round(i,5),"avail_pair_shares":p}
 V=float(y.get("share_haircut")or.0);U=float(x.get("share_haircut")or.0);D=max(V,U);t=math.ceil((float(j)/max(1e-6,1.-V))*1e2-1e-9)/1e2;s=math.ceil((float(j)/max(1e-6,1.-U))*1e2-1e-9)/1e2
 def a(asks_cap,req_sh,lim_px):
  _b=req_sh;_c=.0
  for _f,_e in asks_cap:
   if _f>lim_px+1e-9:break
   _d=min(_b,_e)
   if _d>.0:
    _c+=_d*_f;_b-=_d
    if _b<=1e-8:return True,_c
  return False,_c
 T,S=a(B,t,float(y["worst_px"]));R,Q=a(A,s,float(x["worst_px"]))
 if T and R and(S+Q)<=float(target_budget_usd)*1.02+1e-6:h=float(j);m=t;l=s;g=S+Q
 else:
  h=math.floor(float(j)*(1.-D)*1e2+1e-9)/1e2
  if h<5.-1e-9:return{"filled":False,"reason":"NET_PAIRED_SHARES_BELOW_5SH_MIN","best_a":round(L,4),"best_b":round(K,4),"net_paired_shares":round(h,4),"avail_pair_shares":p}
  m=min(float(j),math.ceil((h/max(1e-6,1.-V))*1e2-1e-9)/1e2);l=min(float(j),math.ceil((h/max(1e-6,1.-U))*1e2-1e-9)/1e2);P,O=a(B,m,float(y["worst_px"]));N,M=a(A,l,float(x["worst_px"]))
  if not(P and N):return{"filled":False,"reason":"DEPTH_CAP_GROSS_WALK_FAILED","best_a":round(L,4),"best_b":round(K,4),"avail_pair_shares":p}
  g=O+M
 k=min(m*max(1e-6,1.-V),l*max(1e-6,1.-U));o=g/max(1e-6,k);d=max(d,o);e=g;f=max(.0,g-h*(y["vwap"]+x["vwap"]));c=g;w=min(L,K);C=int(math.ceil(1./max(w,.01)-1e-9))
 if j<C or(m*L)<1.-1e-6 or(l*K)<1.-1e-6:return{"filled":False,"reason":"LEG_BELOW_1USD_MIN","best_a":round(L,4),"best_b":round(K,4),"l1_box_cost_net":round(i,5),"avail_pair_shares":p}
 if e<min_box_notional_usd:return{"filled":False,"reason":"BELOW_MIN_BOX_NOTIONAL","box_cost_net":round(d,5),"spent_usd":round(e,2)}
 if d<min_box_cost_net:return{"filled":False,"reason":"SUSPECT_INVERTED_ANTI_BOX","best_a":round(L,4),"best_b":round(K,4),"box_cost_net":round(d,5)}
 if d>max_box_cost_net:return{"filled":False,"reason":"BOX_COST_ABOVE_CAP","best_a":round(L,4),"best_b":round(K,4),"box_cost_net":round(d,5),"l1_box_cost_net":round(i,5),"avail_pair_shares":p}
 q=1.-d;v=round(min(F,E)*(L+K),2);return{"filled":True,"shares":int(j),"net_paired_shares":round(h,4),"leg_a_gross_shares":round(m,2),"leg_b_gross_shares":round(l,2),"best_ask":round(L+K,4),"vwap":round(e/float(j),5),"eff_px":round(d,5),"box_cost_net":round(d,5),"riskless_floor_per_pair":round(q,5),"guaranteed_min_profit_usd":round(h*q,4),"corridor_bonus_profit_usd":round(h*(2.-d),4),"slip_cents":round((e/float(j)-(L+K))*1e2,2),"spent_usd":round(e,4),"fee_usd":round(f,4),"fill_ratio":round(min(1.,c/max(1e-6,float(target_budget_usd))),4),"l1_usd":v,"avail_pair_shares":p,"avail_a_shares":round(F,2),"avail_b_shares":round(E,2),"leg_a_walk":y,"leg_b_walk":x,"levels":max(y["levels"],x["levels"])}
def compute_dominance_box_payout_from_close(close_px,k_low,k_high):b=1. if close_px>=k_low else.0;a=1. if close_px<k_high else.0;return b+a
def walk_equal_shares_multi_leg_box(legs_spec,target_budget_usd,guaranteed_payout_per_bundle=1.,max_bundle_cost_net=.992,max_slip_cents=.025,min_shares=5,min_box_notional_usd=4.85):
 if len(legs_spec)<2 or guaranteed_payout_per_bundle<=.0:return{"filled":False,"reason":"INVALID_BUNDLE_SPEC"}
 o=[];s=[];E=[];h=.0
 for B in legs_spec:
  capped,D,A=_sorted_asks(B.get("asks")or[],max_slip_cents)
  if not capped:return{"filled":False,"reason":"EMPTY_LEG_BOOK"}
  G=float(B.get("fee_rate",.07));F=float(B.get("fee_exponent",1.));o.append(capped);s.append(D);E.append(A);h+=_net_unit_cost_buy(D,G,F)
 if h>max_bundle_cost_net+.015:return{"filled":False,"reason":"BUNDLE_TOO_EXPENSIVE_L1","l1_bundle_cost_net":round(h,5)}
 n=int(math.floor(min(E)))
 if n<max(5,min_shares):return{"filled":False,"reason":"INSUFFICIENT_BUNDLE_SHARES","avail_bundle_shares":n}
 r=int(math.floor(float(target_budget_usd)/max(.1,h)));x=min(r,n)
 if x<max(5,min_shares):return{"filled":False,"reason":"BUDGET_BELOW_MIN_SHARES"}
 q=[]
 for B,capped in zip(legs_spec,o):
  w_i=_walk_exact_shares(capped,x,float(B.get("fee_rate",.07)),float(B.get("fee_exponent",1.)))
  if w_i is None:return{"filled":False,"reason":"LEG_WALK_FAILED"}
  q.append(w_i)
 d=sum(w["spent_usd"]for w in q);f=sum(w["fee_usd"]for w in q);i=d+f;b=i/float(x)
 if i>target_budget_usd*1.02:
  C=int(math.floor(float(target_budget_usd)/b))
  if C<max(5,min_shares):return{"filled":False,"reason":"TRIMMED_BELOW_MIN_SHARES"}
  x=C;q=[]
  for B,capped in zip(legs_spec,o):
   w_i=_walk_exact_shares(capped,x,float(B.get("fee_rate",.07)),float(B.get("fee_exponent",1.)))
   if w_i is None:return{"filled":False,"reason":"LEG_TRIM_WALK_FAILED"}
   q.append(w_i)
  d=sum(w["spent_usd"]for w in q);f=sum(w["fee_usd"]for w in q);i=d+f;b=i/float(x)
 def a(asks_cap,req_sh,lim_px):
  w=req_sh;H=.0
  for K,J in asks_cap:
   if K>lim_px+1e-9:break
   I=min(w,J)
   if I>.0:
    H+=I*K;w-=I
    if w<=1e-8:return True,H
  return False,H
 v=[float(w.get("share_haircut")or.0)for w in q];z=max(v)if v else.0;l=[math.ceil((float(x)/max(1e-6,1.-h_i))*1e2-1e-9)/1e2 for h_i in v];u=[a(capped,g_i,float(w_i["worst_px"]))for capped,g_i,w_i in zip(o,l,q)]
 if all(ok_i for ok_i,_ in u)and sum(sp_i for _,sp_i in u)<=float(target_budget_usd)*1.02+1e-6:g=float(x);e=l;c=sum(sp_i for _,sp_i in u)
 else:
  g=math.floor(float(x)*(1.-z)*1e2+1e-9)/1e2
  if g<5.-1e-9:return{"filled":False,"reason":"NET_BUNDLE_SHARES_BELOW_5SH_MIN","avail_bundle_shares":n}
  e=[min(float(x),math.ceil((g/max(1e-6,1.-h_i))*1e2-1e-9)/1e2)for h_i in v];t=[a(capped,g_i,float(w_i["worst_px"]))for capped,g_i,w_i in zip(o,e,q)]
  if not all(ok_i for ok_i,_ in t):return{"filled":False,"reason":"DEPTH_CAP_MULTI_LEG_WALK_FAILED","avail_bundle_shares":n}
  c=sum(sp_i for _,sp_i in t)
 j=c/max(1e-6,g);b=max(b,j);d=c;f=max(.0,c-g*sum(float(w["vwap"])for w in q));p=min(s);y=int(math.ceil(1./max(p,.01)-1e-9))
 if x<y or any((g_i*H)<1.-1e-6 for g_i,H in zip(e,s)):return{"filled":False,"reason":"LEG_BELOW_1USD_MIN","avail_bundle_shares":n}
 if d<min_box_notional_usd:return{"filled":False,"reason":"BELOW_MIN_BOX_NOTIONAL","spent_usd":round(d,2)}
 if b>max_bundle_cost_net:return{"filled":False,"reason":"BUNDLE_COST_ABOVE_CAP","bundle_cost_net":round(b,5),"l1_bundle_cost_net":round(h,5)}
 k=guaranteed_payout_per_bundle-b;m=round(min(E)*sum(s),2);return{"filled":True,"shares":int(x),"net_paired_shares":round(g,4),"leg_gross_shares":[round(g_i,2)for g_i in e],"best_ask":round(sum(s),4),"vwap":round(d/max(1e-6,g),5),"eff_px":round(b,5),"box_cost_net":round(b,5),"guaranteed_payout_per_bundle":round(guaranteed_payout_per_bundle,4),"riskless_floor_per_pair":round(k,5),"guaranteed_min_profit_usd":round(g*k,4),"spent_usd":round(d,4),"fee_usd":round(f,4),"l1_usd":m,"avail_bundle_shares":n,"leg_walks":q}
# ======================================================================================
# [09/20] MODULE: src/polymarket_research/exact_twap_lock_engine.py
# PURPOSE: Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock
# ======================================================================================

import json;import math;import os;from pathlib import Path;from typing import Any,Dict,List,Optional,Sequence,Tuple;DEFAULT_ANNUAL_IV_FLOORS={"BTC":.55,"ETH":.7,"SOL":.9,"XRP":.95,"BNB":.85,"DOGE":1.15,"ZEC":1.25,"HYPE":1.35};SECONDS_PER_YEAR=365.25*86400.;SHM_DIR=Path(os.getenv("PM_FAST_TICK_DIR","/dev/shm"))
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
# [10/20] MODULE: src/polymarket_research/tradfi_sports_zero_fee_engine.py
# PURPOSE: Zero-Fee Pyth Commodities/Metals/Equities (CM_B3/B2/U1), B4 Wick Lock, NBA Polish-Middle (SP1) & NegRisk (NR0)
# ======================================================================================

import json;import logging;import math;import re;import time;import urllib.parse;import urllib.request;from dataclasses import dataclass,field;from datetime import datetime,timedelta,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;from src.polymarket_research.barrier_onetouch_svi_engine import(detect_barrier_monotonicity_boxes,first_passage_touch_prob);from src.polymarket_research.riskless_protocol_v2_expansion import(get_us_eastern_tz,is_conditional_negrisk_missing_catchall);logger=logging.getLogger("TradFiSportsZeroFee");NY_TZ=get_us_eastern_tz();PYTH_ASSET_CONFIG={"WTI":("CL=F","CME_23H",True,.0045,.32),"NG":("NG=F","CME_23H",True,.006,.48),"GC":("GC=F","CME_23H",True,.002,.2),"SI":("SI=F","CME_23H",True,.003,.32),"XAUUSD":("GC=F","CME_23H",False,.015,.2),"XAGUSD":("SI=F","CME_23H",False,.02,.32),"SPY":("SPY","EQUITY_RTH",True,.0015,.18),"NVDA":("NVDA","EQUITY_RTH",True,.0015,.42),"AMZN":("AMZN","EQUITY_RTH",True,.0015,.34),"GOOGL":("GOOGL","EQUITY_RTH",True,.0015,.34),"MSFT":("MSFT","EQUITY_RTH",True,.0015,.3),"META":("META","EQUITY_RTH",True,.0015,.38),"AAPL":("AAPL","EQUITY_RTH",True,.0015,.28),"TSLA":("TSLA","EQUITY_RTH",True,.0015,.52),"COIN":("COIN","EQUITY_RTH",True,.002,.65),"HOOD":("HOOD","EQUITY_RTH",True,.002,.58),"PLTR":("PLTR","EQUITY_RTH",True,.002,.55)};PYTH_HIT_SERIES=(("WTI","MONTH","crude-oil-cl-hit"),("WTI","WEEK","wti-crude-oil-hit-price-weekly"),("NG","WEEK","natural-gas-hit-price-weekly"),("XAUUSD","MONTH","xauusd-hit-month"),("XAUUSD","WEEK","gold-hit-price-weekly"),("GC","MONTH","what-will-gold-gc-hit"),("XAGUSD","MONTH","xagusd-hit-month"),("XAGUSD","WEEK","silver-hit-price-weekly"),("SI","MONTH","what-will-silver-si-hit"),("SPY","MONTH","spy-hit-month"),("SPY","WEEK","spy-hit-price-weekly"),("NVDA","MONTH","nvidia-hit-price-monthly"),("NVDA","WEEK","nvidia-hit-price-weekly"),("AMZN","WEEK","amazon-hit-price-weekly"),("GOOGL","WEEK","google-hit-price-weekly"),("MSFT","WEEK","microsoft-hit-price-weekly"),("META","WEEK","meta-hit-price-weekly"),("AAPL","WEEK","apple-hit-price-weekly"),("TSLA","WEEK","tesla-hit-price-weekly"),("COIN","MONTH","coin-hit-month"),("HOOD","MONTH","hood-hit-month"),("PLTR","WEEK","palantir-hit-price-weekly"));PYTH_CLOSE_SERIES=(("SPY","spy-daily-close-uo"),("WTI","wti-daily-close-uo"),("MSFT","msft-multi-strikes-weekly"),("NVDA","nvda-multi-strikes-weekly"),("AAPL","aapl-multi-strikes-weekly"),("TSLA","tsla-multi-strikes-weekly"),("AMZN","amzn-multi-strikes-weekly"),("GOOGL","googl-multi-strikes-weekly"),("META","meta-multi-strikes-weekly"),("COIN","coin-multi-strikes-weekly"),("HOOD","hood-multi-strikes-weekly"),("PLTR","pltr-multi-strikes-weekly"),("NVDA","nvda-above-on-daily"),("TSLA","tsla-above-on-daily"),("AAPL","aapl-above-on-daily"),("MSFT","msft-above-on-daily"),("AMZN","amzn-above-on-daily"),("GOOGL","googl-above-on-daily"),("META","meta-above-on-daily"),("PLTR","pltr-above-on-daily"));NBA_SERIES_SLUGS=("nba-2026",);MULTI_SPORT_CORRIDOR_SERIES=(("NBA","nba-2026"),("NFL","nfl-2026"),("CFB","cfb-2026"),("NHL","nhl-2026"));ZERO_FEE_NEGRISK_SERIES=("elon-tweets","elon-tweets-48h","trump-truth-social","fomc","fed-3-parlay","bank-of-japan","bank-of-canada-decision","reserve-bank-of-australia-decision","reserve-bank-of-new-zealand-decision","us-gas-price-daily","best-ai-company","chinese-ai-1");_STRIKE_PRICE_RE=re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)");_SPREAD_FAV_RE=re.compile(r"Spread:\s*(.+?)\s*\(\s*([-+]?\d+(?:\.\d+)?)\s*\)",re.IGNORECASE);_FEE_TYPE_FALLBACK_RATES={"sports_fees_nfl_cfb_oct26":(.03,1.),"sports_fees_v2":(.03,1.),"sports_fees_v3":(.05,1.),"crypto_fees_v2":(.07,1.),"crypto_15_min":(.072,1.),"politics_fees":(.04,1.),"weather_fees":(.05,1.),"culture_fees":(.05,1.),"economics_fees":(.05,1.),"finance_prices_fees":(.04,1.),"tech_fees":(.04,1.),"mentions_fees":(.05,1.),"general_fees":(.04,1.)}
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
class PythBarrierRungSpec:event_id:str;market_id:str;condition_id:str;asset:str;horizon_group:str;series_slug:str;question:str;strike:float;direction:str;yes_token:str;no_token:str;start_ts:float;end_ts:float;fee_rate:float=.0;fee_exponent:float=1.
@dataclass
class PythCloseRungSpec:event_id:str;market_id:str;condition_id:str;asset:str;series_slug:str;question:str;strike:float;is_downward:bool;yes_token:str;no_token:str;end_ts:float;fee_rate:float=.0;fee_exponent:float=1.
@dataclass
class NbaOutcomeLeg:market_id:str;condition_id:str;market_type:str;token_id:str;opp_token_id:str;side_index:int;side_label:str;display_label:str;relation:str;threshold:float;fee_rate:float=.0;fee_exponent:float=1.
@dataclass
class NbaGameSpec:event_id:str;slug:str;title:str;team_a:str;team_b:str;tipoff_ts:float;settle_est_ts:float;margin_legs:List[NbaOutcomeLeg]=field(default_factory=list);total_legs:List[NbaOutcomeLeg]=field(default_factory=list)
@dataclass
class ZeroFeeNegRiskSlateSpec:event_id:str;series_slug:str;title:str;end_ts:float;brackets:List[Dict[str,Any]];neg_risk_augmented:bool=False
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
_TRADFI_PYTH_ALIASES={"GOLD":"XAU","GC=F":"XAU","SILVER":"XAG","SI=F":"XAG","BTC":"BTC","ETH":"ETH","SOL":"SOL","XRP":"XRP","BNB":"BNB","DOGE":"DOGE","SPY":"SPY","QQQ":"QQQ","NVDA":"NVDA","TSLA":"TSLA","AAPL":"AAPL","MSFT":"MSFT","AMZN":"AMZN","GOOGL":"GOOGL","META":"META","NFLX":"NFLX","COIN":"COIN","XAU":"XAU","XAG":"XAG"}
def _extract_polybolt_spot_sample(chainlink_stream,sym,now_ts,max_age_sec):
 if chainlink_stream is None or not sym or not hasattr(chainlink_stream,"get_latest_spot"):return None
 try:c=chainlink_stream.get_latest_spot(sym,now_ts=now_ts,max_age_sec=max_age_sec)
 except TypeError:
  try:c=chainlink_stream.get_latest_spot(sym)
  except Exception:return None
 except Exception:return None
 if c is None:return None
 if isinstance(c,(tuple,list))and len(c)>=2:b,a=float(c[0]or.0),float(c[1]or now_ts)
 elif isinstance(c,dict):b=float(c.get("price")or c.get("spot")or.0);a=float(c.get("ts")or c.get("rx_ts")or now_ts)
 elif isinstance(c,(int,float))and not isinstance(c,bool):b,a=float(c),now_ts
 else:return None
 if b<=.0 or(now_ts-a)>max_age_sec:return None
 return b,a
def fetch_pyth_intraday_or_spot_sync(asset,yahoo_symbol="",vol_floor_annual=.25,*,pyth_stream=None,chainlink_stream=None,cached_yahoo=None,yahoo_ttl_sec=90.,use_pyth_hermes=True,max_spot_age_sec=4.,timeout=2.,now_ts=None,session=None):
 import os;x=float(now_ts if now_ts is not None else time.time());v=str(os.environ.get("DOMINUS_NETWORK_MODE")or"").strip().lower()=="offline";o=str(asset or"").strip().upper();n=_TRADFI_PYTH_ALIASES.get(o)or _TRADFI_PYTH_ALIASES.get(str(yahoo_symbol or"").strip().upper(),"");f=None
 if isinstance(cached_yahoo,dict)and cached_yahoo.get("spot"):
  if(x-float(cached_yahoo.get("yahoo_fetched_ts")or cached_yahoo.get("fetched_ts")or.0))<=max(1.,float(yahoo_ttl_sec)):f=cached_yahoo
 if f is None and yahoo_symbol and not v:f=fetch_yahoo_1m_intraday_sync(yahoo_symbol,vol_floor_annual=vol_floor_annual,timeout=max(2.,float(timeout)))
 e=None
 if n and pyth_stream is not None and hasattr(pyth_stream,"get_latest"):
  try:
   q=pyth_stream.get_latest(n,max_age_sec=max_spot_age_sec)
   if isinstance(q,dict)and float(q.get("price")or.0)>.0:e=q
  except Exception:e=None
 h=_extract_polybolt_spot_sample(chainlink_stream,n or o,x,max_spot_age_sec)
 if e is None and n and use_pyth_hermes and not v:
  try:
   from src.polymarket_research.riskless_fast_feeds import PYTH_FEED_IDS as i,fetch_pyth_hermes_latest_sync as g
   if n in i:
    u=g([n],timeout=timeout,session=session)
    if isinstance(u,dict)and isinstance(u.get(n),dict):
     w=u[n]
     if float(w.get("price")or.0)>.0:e=w
  except Exception:e=None
 t=float(e["price"])if isinstance(e,dict)and float(e.get("price")or.0)>.0 else None;m=float(e.get("conf")or.0)if isinstance(e,dict)else.0;s=float(e.get("rx_ts")or e.get("publish_time")or x)if isinstance(e,dict)else.0;k=float(h[0])if h is not None else None;j=float(h[1])if h is not None else.0;r=float(f["spot"])if isinstance(f,dict)and float(f.get("spot")or.0)>.0 else None;p=float(f.get("yahoo_fetched_ts")or f.get("fetched_ts")or.0)if isinstance(f,dict)else.0;d=None;a=.0;c=x;b=""
 if t is not None and k is not None:
  if j>s+.5:d,a,c,b=k,m,j,"polybolt_price_equity"
  else:d,a,c,b=t,m,s,str(e.get("source")or"pyth_hermes")
 elif t is not None:d,a,c,b=t,m,s,str(e.get("source")or"pyth_hermes")
 elif k is not None:d,a,c,b=k,.0,j,"polybolt_price_equity"
 elif r is not None:d,a,c,b=r,.0,p or x,"yahoo_1m_fallback"
 if d is None or d<=.0:return None
 l=max(float(vol_floor_annual),float((f or{}).get("sigma_session")or vol_floor_annual));return{"spot":float(d),"sigma_session":round(l,4),"bars":list((f or{}).get("bars")or[]),"fetched_ts":float(c),"yahoo_fetched_ts":float(p),"spot_source":b,"conf":float(a),"conf_bps":round(1e4*a/d,2)if a>.0 else.0,"pyth_spot":t,"polybolt_spot":k,"yahoo_spot":r}
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
 except Exception:return None
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
 return ZeroFeeNegRiskSlateSpec(event_id=str(ev.get("id")or""),series_slug=series_slug,title=str(ev.get("title")or series_slug),end_ts=float(c),brackets=a,neg_risk_augmented=bool(ev.get("negRiskAugmented",False)))
@dataclass
class MultiSportCorridorLeg:market_id:str;condition_id:str;scope_key:str;token_id:str;opp_token_id:str;side_index:int;side_label:str;display_label:str;relation:str;threshold:float;fee_rate:float=.0;fee_exponent:float=1.;neg_risk:bool=False
@dataclass
class MultiSportCorridorSpec:
 event_id:str;slug:str;sport:str;title:str;team_a:str;team_b:str;start_ts:float;settle_est_ts:float;legs_by_scope:Dict[str,List[MultiSportCorridorLeg]]=field(default_factory=dict)
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
 u=ev.get("markets")or[]
 if len(u)<2:return None
 q=_parse_iso_ts(ev.get("endDate"))
 if not q:return None
 i=str(ev.get("negRiskMarketID")or"").strip().lower();p=bool(ev.get("negRiskAugmented",True));g=len(i)==66 and i.startswith("0x");f=[];a=True;c=False;o=re.compile(r"(?:\bplaceholder\b|^(?:person|party|option|candidate|team|player)\s+[a-z0-9]{1,2}$)",re.IGNORECASE)
 for m in u:
  l=str(m.get("groupItemTitle")or m.get("question")or"").strip()
  if o.search(l):c=True
  if m.get("archived")or m.get("closed")or m.get("active")is False:a=False;continue
  t=_parse_clob_tokens(m)
  if not t:a=False;continue
  v,s=_extract_market_fee_rate(m);r=str(m.get("questionID")or"").strip().lower();e=None
  if g and len(r)==66 and r.startswith("0x")and r[:64]==i[:64]:
   try:e=int(r[64:],16)
   except ValueError:e=None
  f.append({"market_id":str(m.get("id")or""),"condition_id":str(m.get("conditionId")or""),"question_id":r,"question_index":e,"label":l[:48],"yes_token":t[0],"no_token":t[1],"fee_rate":v,"fee_exponent":s})
 if len(f)<2:return None
 k=len(u);j={b["question_index"]for b in f if isinstance(b.get("question_index"),int)};n=f"{ev.get('title')or''} {ev.get('slug')or''}";d=is_conditional_negrisk_missing_catchall(n,[str(b.get("label")or"")for b in f]);h=bool((not p)and(not c)and(not d)and g and a and 3<=k<=40 and len(f)==k and j==set(range(k)))
 if h:f.sort(key=lambda b:int(b["question_index"]))
 return NegRiskConvertSlateSpec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),title=str(ev.get("title")or ev.get("slug")or""),neg_risk_market_id=i,neg_risk_augmented=p,total_market_count=k,is_closed_convert_safe=h,end_ts=float(q),brackets=f)
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
# [11/20] MODULE: src/polymarket_research/macro_counting_ctf_engine.py
# PURPOSE: Phase-2 Multi-Vertical Structural & Oracle Engine (TW1 xtracker, FED1 125-State LP, COND1 Oil-Senate, CTF Overround, AAA Gas, D2 12PM)
# ======================================================================================

import json;import logging;import math;import re;import threading;import time;import urllib.request;from dataclasses import dataclass,field;from datetime import date,datetime,timedelta,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;_MACRO_FEED_LOCK=threading.RLock();_MACRO_FEED_CLIENT=None;_MACRO_FEED_CACHE=(.0,"",{})
def _get_macro_event_feed_client():
 global _MACRO_FEED_CLIENT
 with _MACRO_FEED_LOCK:
  if _MACRO_FEED_CLIENT is None:
   try:from src.polymarket_research.riskless_fast_feeds import MacroEventFeedClient as a;_MACRO_FEED_CLIENT=a()
   except Exception:_MACRO_FEED_CLIENT=False
  return None if _MACRO_FEED_CLIENT is False else _MACRO_FEED_CLIENT
from src.polymarket_research.barrier_onetouch_svi_engine import first_passage_touch_prob;from src.polymarket_research.tradfi_sports_zero_fee_engine import(_extract_market_fee_rate,_net_unit_ask,_parse_clob_tokens,_parse_iso_ts);logger=logging.getLogger("MacroCountingCTF")
try:from src.polymarket_research.riskless_protocol_v2_expansion import get_us_eastern_tz;NY_TZ=get_us_eastern_tz()
except Exception:
 try:NY_TZ=ZoneInfo("America/New_York")
 except Exception:NY_TZ=timezone(timedelta(hours=-4))
CHROME_UA=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36");XTRACKER_ALL_HANDLES=("elonmusk","cz_binance","WhiteHouse","ZelenskyyUa","tedcruz","realDonaldTrump");COUNTING_SERIES_HANDLES=(("elon-tweets","elonmusk"),("elon-tweets-48h","elonmusk"),("cz-tweets","cz_binance"),("cz-binance-tweets","cz_binance"),("whitehouse-tweets","WhiteHouse"),("white-house-tweets","WhiteHouse"),("zelenskyy-tweets","ZelenskyyUa"),("ted-cruz-tweets","tedcruz"),("tedcruz-tweets","tedcruz"),("trump-truth-social","realDonaldTrump"));FOMC_PARLAY_SERIES=("fomc","fed-3-parlay");OIL_SENATE_SLUGS=("which-party-will-win-the-senate-in-2026","who-wins-the-senate-pending-oil-below-85-before-the-midterms","who-wins-the-senate-pending-oil-above-or-below-80-before-the-midterms");GAS_SERIES_SLUGS=("us-gas-price-daily","gas-price-hits-weekly");AI_SERIES_SLUGS=("best-ai-company","chinese-ai-1");HOURLY_BINANCE_SERIES={"BTC":"btc-up-or-down-hourly","ETH":"eth-up-or-down-hourly","SOL":"solana-up-or-down-hourly","XRP":"xrp-up-or-down-hourly","BNB":"bnb-up-or-down-hourly","DOGE":"doge-up-or-down-hourly"};_XTRACKER_CACHE={};_AAA_GAS_CACHE=(.0,None)
@dataclass
class CountingBracket:market_id:str;condition_id:str;label:str;low_count:int;high_count:float;yes_token:str;no_token:str;fee_rate:float=.0;rewards_min_size:float=.0;rewards_max_spread:float=.0;neg_risk:bool=True;fee_exponent:float=1.
@dataclass
class CountingSlateSpec:event_id:str;slug:str;series_slug:str;handle:str;title:str;window_start_ts:float;window_end_ts:float;gamma_closed_floor:int;brackets:List[CountingBracket]=field(default_factory=list)
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
 except Exception:
  if d:return d[1]
 return n
def evaluate_counting_dead_no_locks(slate,xtracker_by_slug,safety_post_buffer=2):
 e=xtracker_by_slug.get(slate.slug)or{};b=int(e.get("total")or 0);a=max(int(slate.gamma_closed_floor),b);c=[]
 for d in slate.brackets:
  if math.isfinite(d.high_count)and a>=int(d.high_count)+max(1,safety_post_buffer):c.append(d)
 return a,c
def extract_xtracker_active_event_slugs(xtracker_by_handle):
 f=set();e=[]
 for c,b in(xtracker_by_handle or{}).items():
  for d in(b or{}).keys():
   a=str(d or"").strip()
   if a and a not in f:f.add(a);e.append((a,str(c)))
 return e
def detect_counting_pruned_exhaustive_yes_slate(slate,xtracker_by_slug,books_by_token,*,safety_post_buffer=2,max_bundle_cost_net=.99,max_surviving_legs=12,min_shares=5.):
 f,l=evaluate_counting_dead_no_locks(slate,xtracker_by_slug,safety_post_buffer=safety_post_buffer);k={b.market_id for b in l};h=[b for b in sorted(slate.brackets,key=lambda r:r.low_count)if b.market_id not in k]
 if not(2<=len(h)<=int(max_surviving_legs)):return None
 if not math.isinf(h[-1].high_count):return None
 if h[0].low_count>f:return None
 for v in range(len(h)-1):
  p=h[v].high_count;o=h[v+1].low_count
  if not math.isfinite(p)or int(round(p))+1!=int(o):return None
 n=max(5.,float(min_shares));j=[];c=.0;d=float("inf")
 for B in h:
  A=books_by_token.get(B.yes_token)or{};u=sorted([(float(a["price"]),float(a["size"]))for a in(A.get("asks")or[])if isinstance(a,dict)and float(a.get("price",.0))>0 and float(a.get("size",.0))>0],key=lambda t:t[0])
  if not u:return None
  g,e,i=.0,.0,u[0][0]
  for z,y in u:
   q=min(y,max(.0,n-g))
   if q<=0:break
   e+=q*z;i=z;g+=q
   if g>=n-1e-6:break
  if g<n-1e-6:return None
  x=float(B.fee_rate or.0);w=float(B.fee_exponent or 1.);m=_net_unit_ask(i,x,w);c+=m;d=min(d,sum(s for _,s in u[:3]));j.append({"market_id":B.market_id,"condition_id":B.condition_id,"token_id":B.yes_token,"opp_token_id":B.no_token,"label":B.label,"side":"YES","limit_price":round(i,4),"eff_cost_ps":round(m,6),"fee_rate":x,"fee_exponent":w,"neg_risk":B.neg_risk})
 if c>float(max_bundle_cost_net)+1e-9:return None
 return{"mode":"NR0_PRUNED_EXHAUSTIVE_YES_COMPLETE_SET","event_id":slate.event_id,"slug":slate.slug,"handle":slate.handle,"verified_floor":f,"pruned_dead_count":len(l),"surviving_leg_count":len(j),"includes_unbounded_top_cap":True,"bundle_cost_net_ps":round(c,6),"net_edge_per_share":round(1.-c,6),"shares":max(5,int(math.floor(min(25.,d/1.15)))),"close_ts":slate.window_end_ts,"legs":j}
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
_OIL_REGIME_RANK={"LT80":0,"B80_85":1,"GE85":2};OIL_SENATE_STATES=[(m_reg,M_reg,p)for m_reg in("LT80","B80_85","GE85")for M_reg in("LT80","B80_85","GE85")if _OIL_REGIME_RANK[m_reg]<=_OIL_REGIME_RANK[M_reg]for p in("DEM","REP","OTHER")];ALL_OIL_SENATE_MASK=(1<<len(OIL_SENATE_STATES))-1
def _infer_oil_barrier_polarity(slug_low,ev_desc,m_desc):
 c=f"{ev_desc} {m_desc}".lower();b=any(w in c for w in("hit $","hits $","reach $","reaches $","rise above","spike above","trade at or above"));a=any(w in c for w in("dip below","dips below","fall below","falls below","drop below","trade below"))
 if b and not a:return"UP_HIT"
 if a and not b:return"DOWN_DIP"
 if any(k in slug_low for k in("oil-hits-","oil-reaches-","oil-above-85","oil-above-90")):return"UP_HIT"
 return"DOWN_DIP"
def build_oil_senate_truth_table_legs(events_by_slug):
 v=[]
 for u,C in events_by_slug.items():
  if not C or C.get("closed"):continue
  k=_parse_iso_ts(C.get("endDate"))or.0
  if k<=0:continue
  o=u.lower();f=str(C.get("description")or"")
  for m in(C.get("markets")or[]):
   if m.get("closed"):continue
   B,A=_extract_market_fee_rate(m);t=_parse_clob_tokens(m)
   if not t:continue
   y=str(m.get("groupItemTitle")or m.get("question")or"").strip();z=y.lower();j=str(m.get("description")or"")
   if"pending-oil"in o and any(D in f"{f} {j}".lower()for D in("end of 2026","december 31")):continue
   a=0
   if"which-party-will-win-the-senate"in o:
    b="DEM"if"democrat"in z else("REP"if"republican"in z else None)
    if not b:continue
    for h,(_,_,c)in enumerate(OIL_SENATE_STATES):
     if c==b:a|=(1<<h)
    q="SENATE_MAIN"
   elif"pending-oil"in o:
    b="DEM"if("d senate"in z or"democrat"in z)else("REP"if("r senate"in z or"republican"in z)else None);i=85 if"85"in z else(80 if"80"in z else 0);n="<"in z or"below"in z or"less"in z;l="≥"in z or">="in z or"above"in z or"greater"in z
    if not b or i not in(80,85)or(n==l):continue
    d=_infer_oil_barrier_polarity(o,f,j)
    for h,(s,r,c)in enumerate(OIL_SENATE_STATES):
     if c!=b:continue
     e=r if d=="UP_HIT"else s;g=((e=="LT80"if n else e in("B80_85","GE85"))if i==80 else(e in("LT80","B80_85")if n else e=="GE85"))
     if g:a|=(1<<h)
    q=f"OIL_{i}_{d}_SENATE"
   else:continue
   x=str(m.get("id")or"");w=str(m.get("conditionId")or"");p=m.get("negRisk")if isinstance(m.get("negRisk"),bool)else(C.get("negRisk")if isinstance(C.get("negRisk"),bool)else None);v.append({"event_group":q,"market_id":x,"condition_id":w,"token_id":t[0],"opp_token_id":t[1],"side":"YES","label":f"YES[{y}]","mask":a,"end_ts":k,"fee_rate":B,"fee_exponent":A,"neg_risk":p});v.append({"event_group":q,"market_id":x,"condition_id":w,"token_id":t[1],"opp_token_id":t[0],"side":"NO","label":f"NO[{y}]","mask":ALL_OIL_SENATE_MASK^a,"end_ts":k,"fee_rate":B,"fee_exponent":A,"neg_risk":p})
 return v
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
 global _AAA_GAS_CACHE;c=time.time()
 if _AAA_GAS_CACHE[1]is not None and(c-_AAA_GAS_CACHE[0])<ttl_sec:return _AAA_GAS_CACHE[1]
 try:
  b=urllib.request.Request("https://gasprices.aaa.com/",headers={"User-Agent":CHROME_UA})
  with urllib.request.urlopen(b,timeout=6.)as r:a=parse_aaa_gas_html(r.read().decode("utf-8",errors="replace"))
  if a:_AAA_GAS_CACHE=(c,a);return a
 except Exception:pass
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
def poll_macro_catalyst_feeds_sync(now_ts,*,client=None,sec_ciks=(),bls_series_ids=(),ttl_sec=20.):
 global _MACRO_FEED_CACHE;e,d=is_in_scheduled_macro_catalyst_window(now_ts)
 if not e:return{"in_window":False,"dormant":True,"catalyst":"","fed_items":[],"sec_hits":[],"bls_data":None}
 with _MACRO_FEED_LOCK:
  h,g,f=_MACRO_FEED_CACHE
  if f and g==d and(float(now_ts)-h)<max(2.,float(ttl_sec)):return dict(f)
 j=client if client is not None else _get_macro_event_feed_client()
 if j is None:return{"in_window":True,"dormant":False,"catalyst":d,"fed_items":[],"sec_hits":[],"bls_data":None}
 a=j.fetch_fed_rss_sync(in_window=True)if hasattr(j,"fetch_fed_rss_sync")else[];c=[l for k in sec_ciks if k and(l:=(j.fetch_sec_submissions_sync(k,in_window=True)if hasattr(j,"fetch_sec_submissions_sync")else None))is not None];b=(j.fetch_bls_series_sync(bls_series_ids,in_window=True)if(d=="US_0830_MACRO_RELEASE"and bls_series_ids and hasattr(j,"fetch_bls_series_sync"))else None);i={"in_window":True,"dormant":False,"catalyst":d,"fed_items":list(a or[]),"sec_hits":c,"bls_data":b,"fetched_ts":float(now_ts)}
 with _MACRO_FEED_LOCK:_MACRO_FEED_CACHE=(float(now_ts),d,dict(i))
 return i
def evaluate_pyth_catalyst_shock(asset,prev_spot,cur_spot,strike,direction,eff_session_hours,sigma_session,now_ts,*,macro_client=None,poll_official_feeds=False):
 i,d=is_in_scheduled_macro_catalyst_window(now_ts)
 if not i or prev_spot<=0 or cur_spot<=0 or eff_session_hours<=.1:return{"eligible":False}
 a=None
 if poll_official_feeds or macro_client is not None:a=poll_macro_catalyst_feeds_sync(now_ts,client=macro_client)
 else:
  with _MACRO_FEED_LOCK:
   if _MACRO_FEED_CACHE[2]and(float(now_ts)-_MACRO_FEED_CACHE[0])<=120.:a=_MACRO_FEED_CACHE[2]
 k=(cur_spot-prev_spot)/prev_spot;c=.0035 if asset=="SPY"else.0045
 if abs(k)<c:return{"eligible":False}
 g=(eff_session_hours/1638.)*(365.25*86400.);b=first_passage_touch_prob(prev_spot,strike,g,sigma_session,direction,wick_vol_multiplier=1.1);f=first_passage_touch_prob(cur_spot,strike,g,sigma_session,direction,wick_vol_multiplier=1.1);l=f-b
 if abs(l)<.055:return{"eligible":False}
 j="YES"if l>0 else"NO";h=f if j=="YES"else(1.-f);e={"eligible":bool(.22<=h<=.94),"catalyst":d,"side":j,"p_fair":round(h,4),"delta_p":round(abs(l),4),"ret_pct":round(k*1e2,3)}
 if a is not None:e["official_macro_feed"]={"catalyst":d,"fed_release_count":len(a.get("fed_items")or()),"sec_hits_count":len(a.get("sec_hits")or()),"bls_present":bool(a.get("bls_data"))}
 return e
def evaluate_ai_elo_ci_lock(leaderboard_rows,snapshot_ts,now_ts,tte_sec,max_snapshot_age_sec=21600.):
 if not leaderboard_rows or(now_ts-snapshot_ts)>max_snapshot_age_sec or not(6e2<=tte_sec<=129600.):return{"eligible":False,"reason":"stale_or_outside_window"}
 f=sorted(leaderboard_rows,key=lambda r:float(r.get("rating")or.0),reverse=True)
 if len(f)<2:return{"eligible":False}
 g=f[0];c=str(g.get("organization")or"").strip();b=float(g.get("rating_q025")or.0);a=max((float(r.get("rating_q975")or.0)for r in f[1:]if str(r.get("organization")or"").strip()!=c),default=.0);e=b-a
 if not c or e<6.:return{"eligible":False,"ci_gap":round(e,2)}
 d=min(.992,.955+.0025*min(15.,e-6.));return{"eligible":True,"leader_org":c,"ci_gap":round(e,2),"p_lock":round(d,4)}
def _infer_binance_candle_close_offset_sec(spec,is_hourly_updown=False):
 if"oracle_close_offset_sec"in spec and spec["oracle_close_offset_sec"]is not None:return float(spec["oracle_close_offset_sec"])
 a=str(spec.get("description")or spec.get("resolution_rules")or spec.get("rules_text")or"").lower()
 if any(tok in a for tok in("1 minute candle","1-minute candle","1m candle")):return 60.
 if any(tok in a for tok in("1 hour candle","1-hour candle","1h candle")):return.0
 return.0 if is_hourly_updown else.0
def detect_d2_12pm_binance_boxes(hourly_spec,k_1h,terminal_specs,min_corridor_bps=25.):
 if k_1h<=0:return[]
 e=float(hourly_spec["end_ts"]);d=e+_infer_binance_candle_close_offset_sec(hourly_spec,is_hourly_updown=True);h=str(hourly_spec.get("candle_interval")or"").strip().lower();m=[]
 for g in terminal_specs:
  if g.get("is_downward"):continue
  k=str(g.get("candle_interval")or"").strip().lower()
  if h and k and h!=k:continue
  f=float(g["end_ts"])+_infer_binance_candle_close_offset_sec(g,is_hourly_updown=False)
  if abs(f-d)>1.:continue
  l=float(g["strike"])
  if l<=0:continue
  j,i=min(k_1h,l),max(k_1h,l);c=(i-j)/j*1e4
  if c<min_corridor_bps:continue
  if k_1h<l:b={"token_id":hourly_spec["up_token"],"opp_token_id":hourly_spec["down_token"],"condition_id":hourly_spec["condition_id"],"side":"UP","label":f"1H_UP>{k_1h:g}","market_id":hourly_spec["market_id"],"fee_rate":float(hourly_spec.get("fee_rate",.07)),"fee_exponent":1.,"strike":k_1h};a={"token_id":g["no_token"],"opp_token_id":g["yes_token"],"condition_id":g["condition_id"],"side":str(g.get("no_label","NO")),"label":f"12PM_NO<{l:g}","market_id":g["market_id"],"fee_rate":float(g.get("fee_rate",.07)),"fee_exponent":1.,"strike":l}
  else:b={"token_id":g["yes_token"],"opp_token_id":g["no_token"],"condition_id":g["condition_id"],"side":str(g.get("yes_label","YES")),"label":f"12PM_YES>{l:g}","market_id":g["market_id"],"fee_rate":float(g.get("fee_rate",.07)),"fee_exponent":1.,"strike":l};a={"token_id":hourly_spec["down_token"],"opp_token_id":hourly_spec["up_token"],"condition_id":hourly_spec["condition_id"],"side":"DOWN","label":f"1H_DN<{k_1h:g}","market_id":hourly_spec["market_id"],"fee_rate":float(hourly_spec.get("fee_rate",.07)),"fee_exponent":1.,"strike":k_1h}
  m.append({"asset":str(hourly_spec["asset"]),"k_low":j,"k_high":i,"corridor_bps":round(c,2),"leg_a":b,"leg_b":a,"close_ts":max(e,float(g["end_ts"])),"label":f"{b['label']} + {a['label']} ({c:.0f}bps)"})
 return m
# ======================================================================================
# [12/20] MODULE: src/polymarket_research/uma_nba_endgame_engine.py
# PURPOSE: Evergreen On-Chain UMA Resolution Bond Harvester (BOND1) & 0%-Fee Live NBA Final-2m/Post-Buzzer Sniper (SP2)
# ======================================================================================

import json;import logging;import math;import os;import re;import threading;import time;import urllib.request;from dataclasses import dataclass;from datetime import datetime,timedelta,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo
try:import orjson as _orjson
except ImportError:_orjson=None
try:import requests as _requests
except ImportError:_requests=None
_RPC_SESSION_LOCK=threading.RLock();_RPC_HTTP_SESSION=None;_SHARED_POLYGON_LOGS_WS=None
def set_shared_polygon_logs_ws(ws_client):global _SHARED_POLYGON_LOGS_WS;_SHARED_POLYGON_LOGS_WS=ws_client
from src.polymarket_research.tradfi_sports_zero_fee_engine import(NbaGameSpec,NbaOutcomeLeg,_extract_market_fee_rate,_norm_team,_parse_clob_tokens,_parse_iso_ts);logger=logging.getLogger("UmaNbaEndgameEngine");DEFAULT_POLYGON_RPC="https://polygon-bor-rpc.publicnode.com";FALLBACK_POLYGON_RPCS=("https://1rpc.io/matic","https://polygon-rpc.com");ESPN_NBA_SCOREBOARD_URL="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard";CDN_NBA_SCOREBOARD_URL="https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json";ZERO_ADDR="0x0000000000000000000000000000000000000000";ONE_E18=10**18;HALF_E18=5*(10**17);VERIFIED_UMA_ADAPTERS=frozenset({"0x65070be91477460d8a7aeeb94ef92fe056c2f2a7","0x69c47de9d4d3dad79590d61b9e05918e03775f24","0x2f5e3684cb1f318ec51b00edba38d79ac2c0aa9d","0x6a9d222616c90fca5754cd1333cfd9b7fb6a4f74","0x157ce2d672854c848c9b79c49a8cc6cc89176a49"});NEGRISK_UMA_ADAPTERS=frozenset({"0x69c47de9d4d3dad79590d61b9e05918e03775f24"});SEL_OPTIMISTIC_ORACLE="22302922";SEL_GET_QUESTION="58c039cd";SEL_GET_STATE="ba4b930c";SEL_GET_REQUEST="a9904f9b";YES_OR_NO_IDENT_HEX=b"YES_OR_NO_QUERY".ljust(32,b"\x00").hex();_OO_ADDR_CACHE={};_SUBJECTIVE_VETO_RE=re.compile(r'(\bsay\b.{0,30}["“]|\bmention\b|\btweet\b|\btruth social\b|\bceasefire\b' r'|\binvade\b|\bstrike on\b|\bpardon\b|\bresign\b|\bnominate\b' r'|\bsole discretion\b|\bplaceholder\b)',re.IGNORECASE);_OBJECTIVE_ORACLE_RE=re.compile(r"(aviationweather\.gov|weather\.gov\.hk|wunderground\.com|binance\.com|chain\.link" r"|pyth\.network|federalreserve\.gov|bls\.gov|bea\.gov|census\.gov|eia\.gov|treasury\.gov" r"|gasprices\.aaa\.com|boxofficemojo\.com|xtracker" r"|nba\.com|wnba\.com|nhl\.com|mlb\.com|nfl\.com|ncaa\.com|espn\.com" r"|premierleague\.com|uefa\.com|fifa\.com|fiba\.basketball|atptour\.com|wtatennis\.com" r"|ufc\.com|pgatour\.com|formula1\.com|vlr\.gg|liquipedia\.net|lolesports\.com|hlTV|lol\s*esports)",re.IGNORECASE);_OFFICIAL_SPORTS_OR_ROSTER_CLAUSE_RE=re.compile(r"(?:\bnext\s+team\s+.+?\s+officially\s+joins\s+by\b" r"|\bofficially\s+(?:signs?\s+with|traded\s+to|joins)\b" r"|\bmake\s+the\s+(?:20\d{2}(?:-\d{2})?\s+)?(?:nfl|nba|mlb|nhl|mls|cfb|college\s+football)\s+playoffs\b" r"|\bwin\s+the\s+(?:20\d{2}(?:-\d{2})?\s+)?(?:super\s+bowl|nba\s+finals|world\s+series|stanley\s+cup" r"|premier\s+league|champions\s+league|la\s+liga|serie\s+a|bundesliga|ligue\s+1" r"|cfb\s+national\s+championship|college\s+football\s+playoff|heisman\s+trophy" r"|afc|nfc|eastern\s+conference|western\s+conference" r"|(?:afc|nfc)\s+(?:east|north|south|west))\b" r"|\b(?:nfl|nba|mlb|nhl|premier\s+league|champions\s+league|ufc|formula\s+1|f1|valorant\s+champions\s+tour|vct|pro[\s\-]+football)\b" r".*\b(?:regular\s+season|clean\s+sheet|relegated|top\s+4|playoffs?|championship|division|roster|offseason|next[\s\-]+team|transaction\s+wire|trade\s+deadline)\b)",re.IGNORECASE|re.DOTALL);_NON_LEAGUE_POP_OR_POLITICS_VETO_RE=re.compile(r"\b(?:election|presidential|senate|congress|house\s+of\s+representatives|governor|mayor|parliament|prime\s+minister" r"|dancing\s+with\s+the\s+stars|bachelor|bachelorette|survivor|love\s+island|big\s+brother" r"|oscar|academy\s+awards?|grammy|emmy|golden\s+globe|eurovision" r"|gta\s+marathon|subathon|twitch|youtuber|streamer|tiktok|podcast)\b",re.IGNORECASE);_SPORTS_TITLE_RE=re.compile(r"(\bvs\.?\s+|\bwin on 20\d{2}-\d{2}-\d{2}\b|\bo/u\s+\d+|\bspread:\s+|\bgame\s+[1-7]\s+winner\b|\bmap\s+[1-5]\s+winner\b)",re.IGNORECASE);_EARLY_BARRIER_MARKET_RE=re.compile(r"\b(reach|hit|dip|touch|drop\s+to|fall\s+to|climb\s+to|at\s+any\s+point|before\s+20\d{2})\b",re.IGNORECASE);_HEX32_RE=re.compile(r"^0x[0-9a-fA-F]{64}$");_ANC_CORRESPONDS_RE=re.compile(r"p1\s+corresponds\s+to\s+([^,\.\n]+),\s*p2\s+to\s+([^,\.\n]+)",re.IGNORECASE)
@dataclass
class LiveNbaGameState:game_id:str;start_ts:float;state:str;completed:bool;period:int;clock_sec:float;home_name:str;home_abbr:str;home_score:int;away_name:str;away_abbr:str;away_score:int;source:str="espn"
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
 s=str(m.get("umaResolutionStatus")or"").strip().lower()
 if s!="proposed":return False,f"STATUS_{s.upper()or'NONE'}"
 p=[str(x).strip().lower()for x in _parse_json_list(m.get("umaResolutionStatuses"))]
 if any(x in("disputed","flagged","reset")for x in p):return False,"PRIOR_DISPUTE_HISTORY"
 if p.count("proposed")>2:return False,"EXCESS_PROPOSAL_CYCLES"
 e=str(m.get("resolvedBy")or"").strip().lower()
 if e not in VERIFIED_UMA_ADAPTERS:return False,"UNVERIFIED_ADAPTER"
 h=bool(m.get("negRisk"))or(e in NEGRISK_UMA_ADAPTERS);d=str(m.get("negRiskRequestID")if h else m.get("questionID")or"").strip()
 if not _HEX32_RE.match(d):return False,"MISSING_REQUEST_ID"
 n=_parse_clob_tokens(m);l=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))]
 if not n or len(l)!=2:return False,"NON_BINARY_OUTCOMES"
 if any(o.lower()in("other","placeholder","unknown")for o in l):return False,"PLACEHOLDER_OUTCOME"
 q=str(m.get("question")or"");k=str(m.get("description")or"");j=f"{q}\n{k}"
 if _SUBJECTIVE_VETO_RE.search(j):return False,"SUBJECTIVE_OR_SPEECH_VETO"
 r=str(m.get("sportsMarketType")or"").strip().lower()
 if r:return True,f"SPORTS_{r.upper()}"
 if _OBJECTIVE_ORACLE_RE.search(j):return True,"VERIFIED_PRIMARY_ORACLE"
 if _SPORTS_TITLE_RE.search(q):return True,"SPORTS_MATCH_RULE"
 a=f"{m.get('slug')or''} {m.get('_ev_slug')or''}\n{j}"
 if p.count("proposed")<=1 and not _NON_LEAGUE_POP_OR_POLITICS_VETO_RE.search(a):
  if _OFFICIAL_SPORTS_OR_ROSTER_CLAUSE_RE.search(a):
   c=float(m.get("_eval_now_ts")or time.time());b=_parse_iso_ts(m.get("endDate"))or.0
   if.0<b<=c:return True,"OFFICIAL_LEAGUE_POST_DEADLINE"
   f=_parse_json_list(m.get("outcomePrices"))
   if(len(l)==2 and l[0].lower()=="yes"and l[1].lower()=="no"and len(f)==2):
    try:
     g=float(f[0]);i=float(f[1])
     if i>=.94 and g<=.06:return True,"OFFICIAL_LEAGUE_ELIMINATED_NO"
    except(TypeError,ValueError):pass
 return False,"NO_OBJECTIVE_DOMAIN_MATCH"
def _get_rpc_session():
 global _RPC_HTTP_SESSION
 if _requests is None or not hasattr(_requests,"Session"):return None
 with _RPC_SESSION_LOCK:
  if _RPC_HTTP_SESSION is None:
   s=_requests.Session()
   if not hasattr(s,"post")or not hasattr(s,"headers"):return None
   s.headers.update({"Content-Type":"application/json","User-Agent":"DominusUmaVerifier/1.0"});_RPC_HTTP_SESSION=s
  return _RPC_HTTP_SESSION
def _rpc_post(rpc_url,payload,timeout=2.5):
 k=_orjson.dumps(payload)if _orjson is not None else json.dumps(payload).encode("utf-8");j=[rpc_url]
 if rpc_url==DEFAULT_POLYGON_RPC:j.extend(u for u in FALLBACK_POLYGON_RPCS if u!=rpc_url)
 d=max(.8,float(timeout));e=time.monotonic()+max(d,4.5);b=getattr(urllib.request.urlopen,"__module__","urllib.request")!="urllib.request";i=None if b else _get_rpc_session();a=None
 for n,u in enumerate(j):
  m=e-time.monotonic()
  if n>0 and m<=.4:break
  c=min(d,max(.8,m))
  try:
   if i is not None:
    h=i.post(u,data=k,timeout=c)
    if getattr(h,"status_code",200)>=400:raise RuntimeError(f"RPC_HTTP_{h.status_code}")
    return _orjson.loads(h.content)if _orjson is not None else h.json()
   l=urllib.request.Request(u,data=k,headers={"Content-Type":"application/json","User-Agent":"DominusUmaVerifier/1.0"},method="POST");g=urllib.request.urlopen(l,timeout=c).read();return _orjson.loads(g)if _orjson is not None else json.loads(g.decode("utf-8"))
  except Exception as f:a=f
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
def verify_uma_onchain_proposal_sync(m,rpc_url=None,now_ts=None,min_proposal_age_sec=120.,max_rem_challenge_sec=7500.,timeout=5.,scoped_logs_ws=None):
 _b,s=is_objective_uma_market(m)
 if not _b:return{"verified":False,"reason":s}
 _h=str(m.get("id")or m.get("market_id")or"").strip()
 if _h in("6707503","6707502"):return{"verified":False,"reason":"D001_DISPUTED_KMIA_QUARANTINED"}
 _l=float(now_ts if now_ts is not None else time.time());Q=scoped_logs_ws if scoped_logs_ws is not None else _SHARED_POLYGON_LOGS_WS;g=None
 if Q is not None:
  try:
   if _h and hasattr(Q,"get_market_oo_status"):
    _g=Q.get_market_oo_status(_h)
    if isinstance(_g,dict):
     if _g.get("quarantined_d001"):return{"verified":False,"reason":"D001_WS_QUARANTINED","ws_fast_path":True}
     _f=str(_g.get("status")or"").upper()
     if _f=="DISPUTED":return{"verified":False,"reason":"WS_DISPUTE_PRICE_VETO","ws_fast_path":True,"ws_event":_g}
     if _f=="SETTLED":return{"verified":False,"reason":"OO_STATE_6_WS_SETTLED","ws_fast_path":True,"ws_event":_g}
     g=_g
   _e=str(m.get("conditionId")or m.get("condition_id")or"").strip().lower()
   if _e and hasattr(Q,"get_condition_resolution")and Q.get_condition_resolution(_e)is not None:return{"verified":False,"reason":"CTF_CONDITION_ALREADY_RESOLVED_WS","ws_fast_path":True}
  except Exception:pass
 _k=rpc_url or os.getenv("POLYGON_RPC_URL")or DEFAULT_POLYGON_RPC;P=str(m.get("resolvedBy")or"").strip().lower();_d=bool(m.get("negRisk"))or(P in NEGRISK_UMA_ADAPTERS);q=str(m.get("negRiskRequestID")if _d else m.get("questionID")or"").strip().lower();_j=[str(o).strip()for o in _parse_json_list(m.get("outcomes"))];_i=_parse_clob_tokens(m);assert _i is not None
 try:
  f=_OO_ADDR_CACHE.get(P);O=[{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":P,"data":f"0x{SEL_GET_QUESTION}{q[2:]}"},"latest"]}]
  if not f:O.append({"jsonrpc":"2.0","id":2,"method":"eth_call","params":[{"to":P,"data":f"0x{SEL_OPTIMISTIC_ORACLE}"},"latest"]})
  _a=_rpc_post(_k,O,timeout=timeout);N={int(r["id"]):r.get("result")for r in _a if isinstance(r,dict)and"id"in r};Z=str(N.get(1)or"")
  if not Z.startswith("0x")or len(Z)<2+14*64:return{"verified":False,"reason":"INVALID_GET_QUESTION_BYTES"}
  if not f:
   Y=str(N.get(2)or"")
   if not Y.startswith("0x")or len(Y)<42:return{"verified":False,"reason":"MISSING_OO_ADDRESS"}
   f="0x"+Y[-40:].lower();_OO_ADDR_CACHE[P]=f
  X=bytes.fromhex(Z[2:]);_c=[X[i:i+32]for i in range(0,13*32,32)];W=int.from_bytes(_c[1],"big");d=int.from_bytes(_c[4],"big");u=int.from_bytes(_c[5],"big");p=int.from_bytes(_c[6],"big")!=0;E=int.from_bytes(_c[7],"big")!=0;M=int.from_bytes(_c[8],"big")!=0;D=int.from_bytes(_c[9],"big")!=0
  if W<=0:return{"verified":False,"reason":"UNINITIALIZED_QUESTION"}
  if p or E or M or D or u>0:return{"verified":False,"reason":f"QUESTION_FLAGS(res={p},pause={E},reset={M},refund={D})"}
  l=int.from_bytes(_c[12],"big");L=32+l
  if L+32>len(X):return{"verified":False,"reason":"TRUNCATED_ANCILLARY_OFFSET"}
  K=int.from_bytes(X[L:L+32],"big");t=X[L+32:L+32+K]
  if len(t)!=K:return{"verified":False,"reason":"TRUNCATED_ANCILLARY_BYTES"}
  C=t.decode("utf-8",errors="replace");J=[{"jsonrpc":"2.0","id":10,"method":"eth_call","params":[{"to":f,"data":_encode_oo_query_calldata(SEL_GET_STATE,P,W,t)},"latest"]},{"jsonrpc":"2.0","id":11,"method":"eth_call","params":[{"to":f,"data":_encode_oo_query_calldata(SEL_GET_REQUEST,P,W,t)},"latest"]}];V=_rpc_post(_k,J,timeout=timeout);I={int(r["id"]):r.get("result")for r in V if isinstance(r,dict)and"id"in r};U=str(I.get(10)or"");T=str(I.get(11)or"")
  if not U.startswith("0x")or not T.startswith("0x")or len(T)<2+16*64:return{"verified":False,"reason":"INVALID_OO_RESPONSE"}
  B=int(U,16);S=bytes.fromhex(T[2:]);A=[S[i:i+32]for i in range(0,16*32,32)];z="0x"+A[0].hex()[-40:].lower();y="0x"+A[1].hex()[-40:].lower();n=int.from_bytes(A[3],"big")!=0;a=int.from_bytes(A[10],"big");e=_decode_int256(A[11]);h=int.from_bytes(A[13],"big")
  if B not in(2,3):return{"verified":False,"reason":f"OO_STATE_{B}"}
  if z==ZERO_ADDR or y!=ZERO_ADDR or n:return{"verified":False,"reason":f"DISPUTER_OR_SETTLED(disp={y})"}
  if e==HALF_E18:return{"verified":False,"reason":"TIE_50_50_PROPOSAL_VETO"}
  H=map_uma_proposed_price_to_outcome_idx(e,C,_j)
  if H not in(0,1):return{"verified":False,"reason":f"NON_BINARY_PRICE_{e}"}
  op=_parse_json_list(m.get("outcomePrices"))
  if len(op)>=2:
   try:
    if float(op[H])<.9:return{"verified":False,"reason":f"GAMMA_PRICE_MISMATCH({op[H]})"}
   except Exception:pass
  j=(a or d or int(m.get("customLiveness")or 0)or 7200);k=float(h-j)
  if s=="VERIFIED_PRIMARY_ORACLE"and not _EARLY_BARRIER_MARKET_RE.search(str(m.get("question")or"")):
   x=_parse_iso_ts(m.get("endDate"))or.0
   if x>.0:
    if _l<x:return{"verified":False,"reason":f"MARKET_BEFORE_END_DATE(now={int(_l)}<end={int(x)})"}
    if k<(x-5.):return{"verified":False,"reason":f"PREMATURE_PROPOSAL_BEFORE_END_DATE(prop={int(k)}<end={int(x)})"}
  c=_l-k;b=max(.0,float(h)-_l)
  if c<min_proposal_age_sec:return{"verified":False,"reason":f"PROPOSAL_TOO_FRESH({c:.0f}s)"}
  if b>max_rem_challenge_sec:return{"verified":False,"reason":f"CHALLENGE_WINDOW_TOO_LONG({b:.0f}s)"}
  w,G=_extract_market_fee_rate(m);v=1-H;F={"verified":True,"domain":s,"adapter":P,"oo_address":f,"oo_state":B,"proposer":z,"proposed_price":e,"win_index":H,"win_label":"YES"if H==0 else"NO","win_outcome_name":_j[H],"win_token":_i[H],"lose_token":_i[v],"expiration_ts":float(h),"eff_liveness_sec":int(j),"proposal_age_sec":round(c,1),"rem_challenge_sec":round(b,1),"fee_rate":w,"fee_exponent":G}
  if g is not None:F["ws_fast_path_hint"]=g.get("event_kind")
  return F
 except Exception as R:return{"verified":False,"reason":f"RPC_ERR:{type(R).__name__}"}
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
 from src.polymarket_research.riskless_protocol_v2_expansion import get_us_eastern_tz as a;j={"User-Agent":"Mozilla/5.0","Accept":"application/json"};i=datetime.fromtimestamp(float(now_ts if now_ts is not None else time.time()),tz=a());b=[(i-timedelta(days=1)).strftime("%Y%m%d"),i.strftime("%Y%m%d")];e={}
 for m in dict.fromkeys(b):
  try:
   l=f"{ESPN_NBA_SCOREBOARD_URL}?dates={m}";d=json.loads(urllib.request.urlopen(urllib.request.Request(l,headers=j),timeout=timeout).read().decode("utf-8"))
   for g in parse_espn_nba_scoreboard(d):e[g.game_id]=g
  except Exception:pass
 if e:return list(e.values())
 try:
  d=json.loads(urllib.request.urlopen(urllib.request.Request(ESPN_NBA_SCOREBOARD_URL,headers=j),timeout=timeout).read().decode("utf-8"));h=parse_espn_nba_scoreboard(d)
  if h:return h
 except Exception:pass
 try:
  c={**j,"Referer":"https://www.nba.com/","Origin":"https://www.nba.com"};q=json.loads(urllib.request.urlopen(urllib.request.Request(CDN_NBA_SCOREBOARD_URL,headers=c),timeout=timeout).read().decode("utf-8"));k=[]
  for g in((q.get("scoreboard")or{}).get("games")or[]):p=int(g.get("gameStatus")or 1);f="pre"if p==1 else("in"if p==2 else"post");o,n=g.get("homeTeam")or{},g.get("awayTeam")or{};k.append(LiveNbaGameState(game_id=str(g.get("gameId")or""),start_ts=_parse_iso_ts(g.get("gameTimeUTC"))or.0,state=f,completed=(p==3),period=int(g.get("period")or 0),clock_sec=_parse_iso_clock_sec(g.get("gameClock")),home_name=str(o.get("teamName")or""),home_abbr=str(o.get("teamTricode")or"").upper(),home_score=int(o.get("score")or 0),away_name=str(n.get("teamName")or""),away_abbr=str(n.get("teamTricode")or"").upper(),away_score=int(n.get("score")or 0),source="cdn_nba"))
  return k
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
   if n:o.append({"leg":e,"mode":"POST_BUZZER_FINAL","p_lock":.999,"cushion_pts":round(abs(j-e.threshold),1),"clock_sec":.0,"period":game.period,"score_str":f"{spec.team_a} {score_a}-{score_b} {spec.team_b} (FINAL)"})
  for e in spec.total_legs:
   l=(c>e.threshold)if e.relation=="OVER"else(c<e.threshold)
   if l and abs(c-e.threshold)>=1.5:o.append({"leg":e,"mode":"POST_BUZZER_FINAL","p_lock":.999,"cushion_pts":round(abs(c-e.threshold),1),"clock_sec":.0,"period":game.period,"score_str":f"{spec.team_a} {score_a}-{score_b} {spec.team_b} (FINAL Tot={int(c)})"})
  return o
 if game.state!="in":return o
 if game.period>=3:
  for e in spec.total_legs:
   if e.relation=="OVER"and c>=e.threshold+2.5:o.append({"leg":e,"mode":"LIVE_TOTAL_OVER_LOCKED","p_lock":.999,"cushion_pts":round(c-e.threshold,1),"clock_sec":round(game.clock_sec,1),"period":game.period,"score_str":f"P{game.period} {game.clock_sec:.0f}s Tot={int(c)}>{e.threshold:g}"})
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
# [13/20] MODULE: src/polymarket_research/riskless_frontier_v2_engine.py
# PURPOSE: Riskless Frontier v2 Engine (NR2 Subset Convert + Free Tail, SP4 NBA Props, BOND2 Whitelisted MOOv2, SOC1 3-Way Soccer, LP1 Implication Matrix, API1 BO3 Esports)
# ======================================================================================

import itertools;import json;import math;import os;import re;import unicodedata;import urllib.request;from dataclasses import dataclass,field;from typing import Any,Dict,List,Optional,Tuple;from src.polymarket_research.tradfi_sports_zero_fee_engine import(NegRiskConvertSlateSpec,_extract_market_fee_rate,_net_unit_ask,_norm_team,_parse_clob_tokens,_parse_iso_ts,_walk_side_exact_shares);from src.polymarket_research.uma_nba_endgame_engine import(DEFAULT_POLYGON_RPC,LiveNbaGameState,_canon_nba_team,_parse_json_list,_rpc_post,verify_uma_onchain_proposal_sync);NEGRISK_ADAPTER_ADDR="0xd91e80cf2e7be2e162c6513ced06f1dd0da35296";SEL_NR_GET_QUESTION_COUNT="b7f75d2c";SEL_NR_GET_FEE_BIPS="2582cb5e";SEL_NR_GET_DETERMINED="7ae2e67b";UMA_V4_ADAPTERS=frozenset({"0x65070be91477460d8a7aeeb94ef92fe056c2f2a7","0x69c47de9d4d3dad79590d61b9e05918e03775f24"});MOOV2_ORACLE_ADDR="0x2c0367a9db231ddebd88a94b4f6461a6e47c58b1";UMA_PROPOSER_WHITELIST_ADDR="0x9f35885ce8f67a942d7b2f4fbf937987da08c463";SEL_IS_ON_WHITELIST="3a3ab672";ESPN_NBA_SUMMARY_URL="https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}";BOP_2026_SLUGS=("balance-of-power-2026-midterms","which-party-will-win-the-senate-in-2026","which-party-will-win-the-house-in-2026");_NR_ADAPTER_CACHE={};_WHITELIST_CACHE={};_PLAYER_SUFFIX_RE=re.compile(r"\b(?:jr|sr|ii|iii|iv|v)\b\.?",re.IGNORECASE);_PROP_TITLE_RE=re.compile(r"^(.+?):\s*(Points|Rebounds|Assists|3-Pointers Made|Threes|Three Pointers)\s+O/U\s+(\d+\.5)\b",re.IGNORECASE);_NBA_EM_BAND_RE=re.compile(r"Exact\s+Margin:\s*(.+?)\s+by\s+(\d+)(?:-(\d+)|\+)",re.IGNORECASE);_SOC_ADVANCE_VETO_RE=re.compile(r"\b(?:advance|qualify|lift\s+the\s+trophy|win\s+the\s+(?:cup|final|tie|trophy)|extra\s+time\s+included|penalt(?:y|ies)\s+included)\b",re.IGNORECASE);_SPREAD_PARSE_RE=re.compile(r"^(.+?)\s*\(([+-]?\d+\.5)\)\s*$");_MAP_HC_PAIR_RE=re.compile(r"Map\s+Handicap:\s*(.+?)\s*\(([+-]\d+\.5)\)\s*vs\.?\s*(.+?)\s*\(([+-]\d+\.5)\)",re.IGNORECASE)
def _net_unit_bid(px,fee_rate,fee_exp=1.):p=max(.0,min(1.,float(px)));a=float(fee_rate)*((p*(1.-p))**float(fee_exp))if fee_rate>.0 else.0;return max(.0,p-a)
def _is_half_hook(line):
 if line is None or not math.isfinite(line):return False
 a=abs(float(line))-math.floor(abs(float(line)));return abs(a-.5)<1e-6
def canon_player_name(raw):s=unicodedata.normalize("NFKD",str(raw or"")).encode("ascii","ignore").decode("ascii").lower();s=re.sub(r"[^a-z0-9\s]"," ",s);s=_PLAYER_SUFFIX_RE.sub(" ",s);return re.sub(r"\s+"," ",s).strip()
def verify_negrisk_adapter_slate_sync(neg_risk_market_id,expected_n,rpc_url=None,timeout=4.5):
 c=str(neg_risk_market_id or"").strip().lower()
 if len(c)!=66 or not c.startswith("0x"):return False,0,"INVALID_MARKET_ID"
 f=_NR_ADAPTER_CACHE.get(c)
 if f is not None:
  b,a,e=f
  if e:return False,a,"ALREADY_DETERMINED"
  if b!=expected_n:return False,a,f"QCOUNT_MISMATCH({b}!={expected_n})"
  return True,a,"OK"
 l=rpc_url or os.getenv("POLYGON_RPC_URL")or DEFAULT_POLYGON_RPC;k=c[2:];h=[{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":NEGRISK_ADAPTER_ADDR,"data":f"0x{SEL_NR_GET_QUESTION_COUNT}{k}"},"latest"]},{"jsonrpc":"2.0","id":2,"method":"eth_call","params":[{"to":NEGRISK_ADAPTER_ADDR,"data":f"0x{SEL_NR_GET_FEE_BIPS}{k}"},"latest"]},{"jsonrpc":"2.0","id":3,"method":"eth_call","params":[{"to":NEGRISK_ADAPTER_ADDR,"data":f"0x{SEL_NR_GET_DETERMINED}{k}"},"latest"]}]
 try:
  j=_rpc_post(l,h,timeout=timeout);g={int(r["id"]):str(r.get("result")or"")for r in j if isinstance(r,dict)and"id"in r}
  if not all(g.get(i,"").startswith("0x")and len(g[i])>=66 for i in(1,2,3)):return False,0,"BAD_ADAPTER_RPC"
  b=int(g[1],16);a=int(g[2],16);e=int(g[3],16)!=0
  if not e:_NR_ADAPTER_CACHE[c]=(b,a,e)
  if e:return False,a,"ALREADY_DETERMINED"
  if b!=expected_n:return False,a,f"QCOUNT_MISMATCH({b}!={expected_n})"
  return True,a,"OK"
 except Exception as d:return False,0,f"RPC_ERR:{type(d).__name__}"
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
class NbaPlayerPropRung:event_id:str;event_slug:str;game_title:str;market_id:str;condition_id:str;player_name:str;player_key:str;stat_type:str;line:float;yes_token:str;no_token:str;fee_rate:float;tipoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;fee_exponent:float=1.
@dataclass
class NbaPlayerPropSlate:event_id:str;slug:str;title:str;tipoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;props_by_player_stat:Dict[Tuple[str,str],List[NbaPlayerPropRung]]=field(default_factory=dict)
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
class SoccerRegulationTree:game_id:str;event_id_3way:str;slug_3way:str;title:str;neg_risk_market_id:str;end_ts:float;home_team:str;away_team:str;home_leg:Dict[str,Any];draw_leg:Dict[str,Any];away_leg:Dict[str,Any];over05_leg:Optional[Dict[str,Any]]=None;totals:List[Dict[str,Any]]=field(default_factory=list);spreads:List[Dict[str,Any]]=field(default_factory=list)
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
 f=[]
 def a(m,event_slug,tag_lbl,yes_fn):
  if m.get("closed")or m.get("archived")or m.get("active")is False:return
  j=_parse_clob_tokens(m)
  if not j:return
  p,o=_extract_market_fee_rate(m);g=_parse_iso_ts(m.get("endDate"))or.0;l=str(m.get("id")or"");k=str(m.get("conditionId")or"");n=bool(m.get("negRisk"));h=[1. if yes_fn(r,q)else.0 for r,q in BOP_9_STATES];i=[1.-x for x in h];f.append({"event_slug":event_slug,"market_id":l,"condition_id":k,"token_id":j[0],"opp_token_id":j[1],"side":"YES","label":f"YES[{tag_lbl}]","fee_rate":p,"fee_exponent":o,"neg_risk":n,"end_ts":g,"payoff_vec":h,"strike":1.});f.append({"event_slug":event_slug,"market_id":l,"condition_id":k,"token_id":j[1],"opp_token_id":j[0],"side":"NO","label":f"NO[{tag_lbl}]","fee_rate":p,"fee_exponent":o,"neg_risk":n,"end_ts":g,"payoff_vec":i,"strike":1.})
 e=events_by_slug.get("balance-of-power-2026-midterms")or{}
 for m in e.get("markets")or[]:
  q=str(m.get("question")or m.get("groupItemTitle")or"").lower()
  if"d senate, d house"in q or"democrats sweep"in q:a(m,"bop","BOP:D_Sweep",lambda s,h:s=="D"and h=="D")
  elif"d senate, r house"in q:a(m,"bop","BOP:DSen_RHouse",lambda s,h:s=="D"and h=="R")
  elif"r senate, d house"in q:a(m,"bop","BOP:RSen_DHouse",lambda s,h:s=="R"and h=="D")
  elif"r senate, r house"in q or"republicans sweep"in q:a(m,"bop","BOP:R_Sweep",lambda s,h:s=="R"and h=="R")
  elif"other"in q:a(m,"bop","BOP:Other",lambda s,h:s=="O"or h=="O")
 d=events_by_slug.get("which-party-will-win-the-senate-in-2026")or{}
 for m in d.get("markets")or[]:
  b=str(m.get("groupItemTitle")or"").strip().lower()
  if b=="democratic party":a(m,"senate","Sen:Dem",lambda s,h:s=="D")
  elif b=="republican party":a(m,"senate","Sen:Rep",lambda s,h:s=="R")
 c=events_by_slug.get("which-party-will-win-the-house-in-2026")or{}
 for m in c.get("markets")or[]:
  b=str(m.get("groupItemTitle")or"").strip().lower()
  if b=="democratic party":a(m,"house","House:Dem",lambda s,h:h=="D")
  elif b=="republican party":a(m,"house","House:Rep",lambda s,h:h=="R")
 return f
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
class EsportsBo3Spec:event_id:str;slug:str;title:str;end_ts:float;team_a:str;team_b:str;ml_market_id:str;ml_condition_id:str;ml_a_token:str;ml_b_token:str;ml_fee_rate:float;ml_fee_exp:float;hc_market_id:str;hc_condition_id:str;hc_fav_is_a:bool;hc_minus_token:str;hc_plus_token:str;hc_fee_rate:float;hc_fee_exp:float;map1_a_token:Optional[str]=None;map1_b_token:Optional[str]=None;map1_resolved_winner:Optional[str]=None;map2_a_token:Optional[str]=None;map2_b_token:Optional[str]=None;map2_resolved_winner:Optional[str]=None;ou25_over_token:Optional[str]=None;ou25_under_token:Optional[str]=None;ou25_market_id:str="";ou25_condition_id:str="";ou25_fee_rate:float=.03
def parse_esports_bo3_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived"):return None
 I=str(ev.get("title")or"");O=ev.get("markets")or[];f=bool(re.search(r"\(\s*bo3\s*\)|\bbest\s+of\s+3\b",I,re.IGNORECASE));c=any(re.search(r"\bmap\s+[45]\b",str(m.get("groupItemTitle")or m.get("question")or""),re.IGNORECASE)for m in O)
 if c:return None
 j=any(str(m.get("sportsMarketType")or"").lower()=="totals"and abs(float(m.get("line")or 0)-2.5)<1e-6 for m in O if m.get("line")is not None)
 if not(f or j):return None
 y=(_parse_iso_ts(ev.get("startTime")or ev.get("endDate"))or.0)+3.5*3600.
 if now_ts is not None and y<now_ts+60.:return None
 N=next((m for m in O if str(m.get("sportsMarketType")or"").lower()=="moneyline"and not m.get("closed")),None);M=next((m for m in O if str(m.get("sportsMarketType")or"").lower()=="map_handicap"and not m.get("closed")and abs(abs(float(m.get("line")or 0))-1.5)<1e-6),None)
 if N is None or M is None:return None
 s=_parse_clob_tokens(N);r=[str(o).strip()for o in _parse_json_list(N.get("outcomes"))];q=_parse_clob_tokens(M);p=[str(o).strip()for o in _parse_json_list(M.get("outcomes"))]
 if not s or len(r)!=2 or not q or len(p)!=2:return None
 w,v=r[0],r[1];L,K=_norm_team(w),_norm_team(v);n,l=_norm_team(p[0]),_norm_team(p[1])
 if{L,K}!={n,l}:return None
 k=str(M.get("description")or"");u=str(M.get("groupItemTitle")or M.get("question")or"");b=None;e=re.search(r'resolve\s+to\s+"([^"]+)"\s+if\s+.+?\s+wins\s+2\s+or\s+more\s+maps',k,re.IGNORECASE)
 if e:
  H=_norm_team(e.group(1))
  if H==L:b=True
  elif H==K:b=False
 if b is None:
  t=_MAP_HC_PAIR_RE.search(u)
  if t:P=float(t.group(2));i=n if P<0 else l;b=(i==L)
 if b is None:return None
 h=L if b else K;d,g=(q[0],q[1])if n==h else(q[1],q[0]);G,F=_extract_market_fee_rate(N);E,D=_extract_market_fee_rate(M);J=EsportsBo3Spec(event_id=str(ev.get("id")or""),slug=str(ev.get("slug")or""),title=I,end_ts=y,team_a=w,team_b=v,ml_market_id=str(N.get("id")or""),ml_condition_id=str(N.get("conditionId")or""),ml_a_token=s[0],ml_b_token=s[1],ml_fee_rate=G,ml_fee_exp=F,hc_market_id=str(M.get("id")or""),hc_condition_id=str(M.get("conditionId")or""),hc_fav_is_a=b,hc_minus_token=d,hc_plus_token=g,hc_fee_rate=E,hc_fee_exp=D)
 def a(cm):
  T=_parse_clob_tokens(cm);S=[_norm_team(str(x))for x in _parse_json_list(cm.get("outcomes"))];R=_parse_json_list(cm.get("outcomePrices"));Q,o=None,None
  if T and len(S)==2 and{S[0],S[1]}=={L,K}:Q,o=(T[0],T[1])if S[0]==L else(T[1],T[0])
  m=None
  if len(R)==2 and len(S)==2:
   try:
    V,U=float(R[0]),float(R[1])
    if cm.get("closed")or(max(V,U)>=.995 and min(V,U)<=.005):
     if V>=.995 and U<=.005:m="A"if S[0]==L else"B"
     elif U>=.995 and V<=.005:m="A"if S[1]==L else"B"
   except(TypeError,ValueError):pass
  return Q,o,m
 for cm in O:
  C=str(cm.get("sportsMarketType")or"").lower();B=str(cm.get("groupItemTitle")or cm.get("question")or"").lower()
  if C=="child_moneyline":
   if"map 1"in B or"game 1"in B:J.map1_a_token,J.map1_b_token,J.map1_resolved_winner=a(cm)
   elif"map 2"in B or"game 2"in B:J.map2_a_token,J.map2_b_token,J.map2_resolved_winner=a(cm)
  elif C=="totals"and not cm.get("closed")and cm.get("line")is not None and abs(float(cm.get("line"))-2.5)<1e-6:
   A=_parse_clob_tokens(cm);z=[str(x).lower()for x in _parse_json_list(cm.get("outcomes"))]
   if A and len(z)==2:J.ou25_over_token=A[0]if"over"in z[0]else A[1];J.ou25_under_token=A[1]if"over"in z[0]else A[0];J.ou25_market_id=str(cm.get("id")or"");J.ou25_condition_id=str(cm.get("conditionId")or"");J.ou25_fee_rate,_=_extract_market_fee_rate(cm)
 return J
def _infer_live_map_winner(resolved_flag,tok_a,tok_b,books_by_token,*,allow_quote_inferred=False):
 if resolved_flag in("A","B"):return resolved_flag
 if not allow_quote_inferred or not tok_a or not tok_b:return None
 h=books_by_token.get(tok_a)or{};g=books_by_token.get(tok_b)or{};f=max((float(b.get("price",0))for b in(h.get("bids")or[])if float(b.get("size",0))>0),default=.0);e=max((float(b.get("price",0))for b in(g.get("bids")or[])if float(b.get("size",0))>0),default=.0);d=min((float(a.get("price",1))for a in(h.get("asks")or[])if float(a.get("size",0))>0),default=1.);c=min((float(a.get("price",1))for a in(g.get("asks")or[])if float(a.get("size",0))>0),default=1.)
 if f>=.992 and e<=.005 and c<=.015:return"A"
 if e>=.992 and f<=.005 and d<=.015:return"B"
 return None
def evaluate_api1_esports_bo3_opportunities(spec,books_by_token,best_asks,max_middle_cost_net=.988,*,allow_quote_inferred=False):
 w=[];v=[];y=_infer_live_map_winner(spec.map1_resolved_winner,spec.map1_a_token,spec.map1_b_token,books_by_token,allow_quote_inferred=allow_quote_inferred);x=_infer_live_map_winner(spec.map2_resolved_winner,spec.map2_a_token,spec.map2_b_token,books_by_token,allow_quote_inferred=allow_quote_inferred);q="B"if spec.hc_fav_is_a else"A";p=spec.team_b if spec.hc_fav_is_a else spec.team_a;o=spec.team_a if spec.hc_fav_is_a else spec.team_b;h=spec.ml_a_token if spec.hc_fav_is_a else spec.ml_b_token;g=spec.ml_b_token if spec.hc_fav_is_a else spec.ml_a_token
 if y==q:w.append({"mode":"API1_BO3_MAP1_PLUS15_LOCK","token_id":spec.hc_plus_token,"opp_token_id":spec.hc_minus_token,"market_id":spec.hc_market_id,"condition_id":spec.hc_condition_id,"fee_rate":spec.hc_fee_rate,"fee_exponent":spec.hc_fee_exp,"p_lock":.999,"side_label":"PLUS_1.5","display_label":f"{p} (+1.5 Maps) [Map 1 Won]","close_ts":spec.end_ts})
 a=True
 try:from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as b;t=b.snapshot.get("riskless_boxes",{});a=bool(t.get("enable_esports1_bo3_intermission_box",True)and t.get("enable_esports1_intermission_hc_total_box",True))
 except Exception:pass
 n="A"if spec.hc_fav_is_a else"B"
 if(a and y==n and x is None and spec.ou25_over_token and spec.ou25_under_token and spec.hc_minus_token and spec.hc_plus_token):
  m=best_asks.get(spec.map2_a_token)if spec.map2_a_token else None;l=best_asks.get(spec.map2_b_token)if spec.map2_b_token else None;c=bool(m is not None and l is not None and.15<=float(m)<=.85 and.15<=float(l)<=.85 and(float(m)+float(l))<=1.08)
  if c:
   d=best_asks.get(spec.hc_minus_token);k=best_asks.get(spec.ou25_over_token)
   if d is not None and k is not None:
    s=round(_net_unit_ask(d,spec.hc_fee_rate,spec.hc_fee_exp)+_net_unit_ask(k,spec.ou25_fee_rate,1.),4)
    if s<=max_middle_cost_net:v.append({"mode":"ESPORTS1_BO3_INTERMISSION_HANDICAP_TOTAL_BOX","event_id":spec.event_id,"title":spec.title,"box_cost_net":s,"post_m1_forfeit_immune":True,"close_ts":spec.end_ts,"leg_a":{"token_id":spec.hc_minus_token,"opp_token_id":spec.hc_plus_token,"condition_id":spec.hc_condition_id,"market_id":spec.hc_market_id,"side":"HANDICAP","label":f"{o}(-1.5)","fee_rate":spec.hc_fee_rate,"fee_exponent":spec.hc_fee_exp,"neg_risk":False,"strike":-1.5},"leg_b":{"token_id":spec.ou25_over_token,"opp_token_id":spec.ou25_under_token,"condition_id":spec.ou25_condition_id,"market_id":spec.ou25_market_id,"side":"TOTAL_OVER","label":"Over(2.5)","fee_rate":spec.ou25_fee_rate,"fee_exponent":1.,"neg_risk":False,"strike":2.5},"label":f"{spec.title[:38]}: {o}(-1.5) + Over 2.5 [1-0 Break]"})
   e=best_asks.get(spec.hc_plus_token);f=best_asks.get(spec.ou25_under_token)
   if e is not None and f is not None:
    r=round(_net_unit_ask(e,spec.hc_fee_rate,spec.hc_fee_exp)+_net_unit_ask(f,spec.ou25_fee_rate,1.),4)
    if r<=max_middle_cost_net:v.append({"mode":"ESPORTS1_BO3_INTERMISSION_HANDICAP_TOTAL_BOX","event_id":spec.event_id,"title":spec.title,"box_cost_net":r,"post_m1_forfeit_immune":True,"close_ts":spec.end_ts,"leg_a":{"token_id":spec.hc_plus_token,"opp_token_id":spec.hc_minus_token,"condition_id":spec.hc_condition_id,"market_id":spec.hc_market_id,"side":"HANDICAP","label":f"{p}(+1.5)","fee_rate":spec.hc_fee_rate,"fee_exponent":spec.hc_fee_exp,"neg_risk":False,"strike":1.5},"leg_b":{"token_id":spec.ou25_under_token,"opp_token_id":spec.ou25_over_token,"condition_id":spec.ou25_condition_id,"market_id":spec.ou25_market_id,"side":"TOTAL_UNDER","label":"Under(2.5)","fee_rate":spec.ou25_fee_rate,"fee_exponent":1.,"neg_risk":False,"strike":2.5},"label":f"{spec.title[:38]}: {p}(+1.5) + Under 2.5 [1-0 Break]"})
 if y in("A","B")and x in("A","B")and y!=x and spec.ou25_over_token and spec.ou25_under_token:w.append({"mode":"API1_BO3_1_1_OVER25_LOCK","token_id":spec.ou25_over_token,"opp_token_id":spec.ou25_under_token,"market_id":spec.ou25_market_id,"condition_id":spec.ou25_condition_id,"fee_rate":spec.ou25_fee_rate,"fee_exponent":1.,"p_lock":.998,"side_label":"OVER_2.5","display_label":f"{spec.title[:44]} Over 2.5 Maps [1-1 Split]","close_ts":spec.end_ts})
 j=best_asks.get(h);i=best_asks.get(spec.hc_plus_token)
 if j is not None and i is not None:
  u=round(_net_unit_ask(j,spec.ml_fee_rate,spec.ml_fee_exp)+_net_unit_ask(i,spec.hc_fee_rate,spec.hc_fee_exp),4)
  if u<=max_middle_cost_net:v.append({"mode":"API1_BO3_POST_M1_MIDDLE"if y==q else"API1_BO3_2_1_POLISH_MIDDLE","event_id":spec.event_id,"title":spec.title,"box_cost_net":u,"post_m1_forfeit_immune":(y==q),"close_ts":spec.end_ts,"leg_a":{"token_id":h,"opp_token_id":g,"condition_id":spec.ml_condition_id,"market_id":spec.ml_market_id,"side":"ML","label":f"ML[{o}]","fee_rate":spec.ml_fee_rate,"fee_exponent":spec.ml_fee_exp,"neg_risk":False,"strike":.0},"leg_b":{"token_id":spec.hc_plus_token,"opp_token_id":spec.hc_minus_token,"condition_id":spec.hc_condition_id,"market_id":spec.hc_market_id,"side":"HANDICAP","label":f"{p}(+1.5)","fee_rate":spec.hc_fee_rate,"fee_exponent":spec.hc_fee_exp,"neg_risk":False,"strike":1.5},"label":f"{spec.title[:42]}: ML[{o}] + {p}(+1.5)"})
 return{"single_leg_locks":w,"two_leg_boxes":v}
# ======================================================================================
# [14/20] MODULE: src/polymarket_research/riskless_frontier_v3_engine.py
# PURPOSE: Riskless Frontier v3 Engine (NFL Exact Margin/Spread, Subperiod Clinch, Deadline Ladder, Tennis Retirement-Safe Corridor, Multi-Sport Post-Review Clinch)
# ======================================================================================

import json;import math;import re;import time;import urllib.request;from dataclasses import dataclass,field;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;from src.polymarket_research.riskless_frontier_v2_engine import(ESPN_NBA_SUMMARY_URL,NbaPlayerPropRung,NbaPlayerPropSlate,_infer_live_map_winner,_is_half_hook,_net_unit_bid,canon_player_name,find_state_matrix_dominance_boxes,parse_espn_nba_boxscore_players,verify_negrisk_adapter_slate_sync);from src.polymarket_research.tradfi_sports_zero_fee_engine import(_SPREAD_FAV_RE,_extract_market_fee_rate,_net_unit_ask,_norm_team,_parse_clob_tokens,_parse_iso_ts,_walk_side_exact_shares);from src.polymarket_research.uma_nba_endgame_engine import(LiveNbaGameState,_canon_nba_team,_parse_json_list);LP2_MIDTERM_CORE_SLUGS=("republican-house-seats-after-the-2026-midterm-elections","republican-senate-seats-after-the-2026-midterm-elections-927","which-party-will-win-the-house-in-2026","which-party-will-win-the-senate-in-2026","balance-of-power-2026-midterms","republican-trifecta-with-supermajority-in-the-senate","who-wins-the-senate-pending-hormuz-agreement-before-the-midterms");LP2_TOSSUP_CUBE_SLUG="which-tossup-senate-states-will-republicans-win-ak-ia-ks-me-mi-oh-tx";LP2_TOSSUP_STATE_SLUGS={"AK":"alaska-senate-election-winner","IA":"iowa-senate-election-winner","KS":"kansas-senate-election-winner","ME":"maine-senate-election-winner","MI":"michigan-senate-election-winner","OH":"ohio-senate-election-winner","TX":"texas-senate-election-winner"};ESPN_SCOREBOARD_URLS={"SOCCER":("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.europa/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard","https://site.api.espn.com/apis/site/v2/sports/soccer/ksa.1/scoreboard"),"NHL":("https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",),"NFL":("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",),"CFB":("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?limit=100",)};_EXT_PROP_TITLE_RE=re.compile(r"^(.+?):\s*(Steals|Blocks)\s+O/U\s+(\d+\.5)\b",re.IGNORECASE);_NFL_EM_BAND_RE=re.compile(r"Exact\s+Margin:\s*(.+?)\s+by\s+(\d+)(?:-(\d+)|\+)",re.IGNORECASE);_GENERIC_SPREAD_LINE_RE=re.compile(r"([+-]\d+\.5)\b");_SCALAR_MAG_RE=re.compile(r"(?:↑|above|over|at\s+least|more\s+than|exceeds?)?\s*\$?\s*(?<![a-zA-Z0-9_.\-])([0-9][0-9,]*(?:\.[0-9]+)?)(?![0-9,])\s*(?:([kmbt]|thousand|million|billion|trillion)\b)?(?!\.[0-9]|[a-zA-Z0-9_])",re.IGNORECASE);_COVERED_CRYPTO_PYTH_SLUG_RE=re.compile(r"\b(?:bitcoin|btc|ethereum|eth|solana|sol|xrp|dogecoin|doge|bnb|sui|cardano|avax" r"|wti|crude-oil|xauusd|xagusd|gold-gc|silver-si|spy-hit|spy-daily|nvidia-hit|nvda-multi" r"|apple-hit|aapl-multi|tesla-hit|tsla-multi|microsoft-hit|msft-multi|amazon-hit|google-hit" r"|palantir-hit|coin-hit|hood-hit|natural-gas-hit)\b",re.IGNORECASE);_RESET_WINDOW_VETO_RE=re.compile(r"\b(?:in\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)" r"|during\s+(?:the\s+)?(?:month|week|quarter|q[1-4])|between\s+[a-z]+\s+\d+\s+and\s+[a-z]+\s+\d+)\b",re.IGNORECASE);_MONTH_DATE_STRIP_RE=re.compile(r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)" r"\s+\d{1,2}(?:,\s*20\d{2})?\b|\b20\d{2}-\d{2}-\d{2}\b|\bq[1-4]\s+20\d{2}\b",re.IGNORECASE);_TZ_DETECT_RE=re.compile(r"\b(ET|EDT|EST|UTC|GMT|PT|PDT|PST|CT|EET|CET|IRST|Iran\s+Standard\s+Time|Eastern\s+European\s+Time|Eastern\s+Time)\b",re.IGNORECASE)
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
 O=[];u=[("LP2_HOUSE_CONVERT_POLISH_MIDDLE","republican-house-seats-after-the-2026-midterm-elections","which-party-will-win-the-house-in-2026",10,{"220-224","225-229","230+"},"House:Rep (218-219 $2x Middle)"),("LP2_SENATE_CONVERT_POLISH_MIDDLE","republican-senate-seats-after-the-2026-midterm-elections-927","which-party-will-win-the-senate-in-2026",11,{"51","52","53","54","55","56","57+"},"Sen:Rep (50-Seat $2x Middle)")]
 for N,l,k,I,d,s in u:
  M=events_by_slug.get(l)or{};L=events_by_slug.get(k)or{}
  if not M or not L or M.get("closed")or L.get("closed"):continue
  if not M.get("negRisk")or M.get("negRiskAugmented",True):continue
  H=str(M.get("negRiskMarketID")or"").strip().lower();C=M.get("markets")or[]
  if len(C)!=I:continue
  B,r,_=verify_negrisk_adapter_slate_sync(H,I,rpc_url=rpc_url)
  if not B:continue
  A=float(r)/1e4;G=next((m for m in(L.get("markets")or[])if str(m.get("groupItemTitle")or"").strip().lower()=="republican party"and not m.get("closed")),None)
  if G is None:continue
  q=_parse_clob_tokens(G)
  if not q:continue
  g=q[0];z,y=_extract_market_fee_rate(G);c=[]
  for F,m in enumerate(C):
   grp=str(m.get("groupItemTitle")or"").strip().lower()
   if grp in d:
    Q=_parse_clob_tokens(m)
    if not Q:break
    K=str(m.get("questionID")or"").strip().lower();h=int(K[64:],16)if(len(K)==66 and K.startswith("0x")and K[:64]==H[:64])else F;fr_m,fe_m=_extract_market_fee_rate(m);c.append((h,grp,Q[1],fr_m,fe_m,str(m.get("id")or"")))
  if len(c)!=len(d):continue
  E=len(c);v=int(math.floor(min(80.,target_budget_usd)))
  if v<min_shares:continue
  b=float(v)
  for _,_,n_tok,_,_,_ in c:J=(books_by_token.get(n_tok)or{}).get("asks")or[];b=min(b,sum(float(x.get("size",0))for x in J if float(x.get("price",0))>0))
  p=(books_by_token.get(g)or{}).get("asks")or[];b=min(b,sum(float(x.get("size",0))for x in p if float(x.get("price",0))>0));t=int(math.floor(b))
  if t<min_shares:continue
  i=t*(1.-A);D=_walk_side_exact_shares(p,i,z,y,is_ask=True)
  if D is None:continue
  o=[];n=True
  for h,grp,n_tok,fr_m,fe_m,mid_m in c:
   P=_walk_side_exact_shares((books_by_token.get(n_tok)or{}).get("asks")or[],float(t),fr_m,fe_m,is_ask=True)
   if P is None:n=False;break
   o.append((h,grp,n_tok,fr_m,fe_m,mid_m,P))
  if not n:continue
  j=sum(w["net_per_share"]for*_,w in o);f=float(E-1)*(1.-A);a=(j-f)/max(1e-6,(1.-A))+float(D["net_per_share"])
  if a<=max_synthetic_box_cost_net:e=[{"token_id":n_tok,"market_id":mid_m,"side":"NO","label":f"NO[{grp}]","fee_rate":float(fr_m or.0),"fee_exponent":float(fe_m or 1.)}for _,grp,n_tok,fr_m,fe_m,mid_m,_ in o]+[{"token_id":g,"market_id":str(G.get("id")or""),"side":"YES","label":f"YES[{s}]","fee_rate":z,"fee_exponent":y}];O.append({"mode":N,"seat_slug":l,"neg_risk_market_id":H,"m_no_legs":E,"index_set_int":sum(1<<R for R,*_ in o),"shares_in":t,"shares_out":round(i,4),"synthetic_box_cost_net":round(a,4),"guaranteed_floor_edge_ps":round(1.-a,4),"l1_usd":round(min([w["l1_usd"]for*_,w in o]+[D["l1_usd"]]),2),"close_ts":_parse_iso_ts(M.get("endDate"))or.0,"legs":e,"label":f"{N}: CONV({E}xNO)+YES[{s}] @ {a:.4f}"})
 return O
@dataclass
class NbaSubperiodMarketSpec:event_id:str;market_id:str;condition_id:str;period_scope:str;kind:str;line:Optional[float];team_side:Optional[str];tok_0:str;tok_1:str;out_0:str;out_1:str;fee_rate:float;settle_est_ts:float;display_title:str;neg_risk:bool=False;fee_exponent:float=1.
@dataclass
class NbaSubperiodAndExtPropSlate:event_id:str;slug:str;title:str;tipoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;ext_props_by_player_stat:Dict[Tuple[str,str],List[NbaPlayerPropRung]]=field(default_factory=dict);subperiod_markets:List[NbaSubperiodMarketSpec]=field(default_factory=list)
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
 z=str(ext_summary.get("state")or"pre")
 if z not in("in","post"):return[]
 i=bool(ext_summary.get("completed")and z=="post");y=bool(ext_summary.get("is_halftime"));p=int(ext_summary.get("period")or 0);d=float(ext_summary.get("clock_sec")or 720.);F=(ext_summary.get("linescores")or{}).get("home")or{};E=(ext_summary.get("linescores")or{}).get("away")or{};h=int(ext_summary.get("home_score")or 0);g=int(ext_summary.get("away_score")or 0);x=[]
 def a(p_scope):
  if p_scope=="FG":return g,h,i
  if p_scope in("Q1","Q2","Q3","Q4"):
   q=int(p_scope[1])
   if q not in E or q not in F:return None,None,False
   K=i or(q==1 and y)or(p>q and(d<=6e2 or p>=q+2));return E[q],F[q],K
  if p_scope=="1H":
   if 1 not in E or 1 not in F:return None,None,False
   O=E.get(1,0)+E.get(2,0);N=F.get(1,0)+F.get(2,0);K=i or(2 in E and 2 in F and(p>=3 or y));return O,N,K
  if p_scope=="2H":
   if p<3:return None,None,False
   M=sum(v for k,v in E.items()if k>=3);L=sum(v for k,v in F.items()if k>=3);return M,L,i
  return None,None,False
 for J in slate.subperiod_markets:
  D,C,c=a(J.period_scope)
  if D is None or C is None:continue
  f={slate.away_team:D,slate.home_team:C}
  if J.kind in("TOTAL","TEAM_TOTAL")and J.line is not None:
   m=(D+C)if J.kind=="TOTAL"else f.get(J.team_side or"",-1)
   if m<0:continue
   if c:
    l=.5 if(i or p>=(int(J.period_scope[1])+2 if J.period_scope.startswith("Q")else 4))else 1.5
    if abs(float(m)-J.line)>=l:e=float(m)>J.line;x.append({"mode":f"SP4_{J.period_scope}_SETTLED_TOTAL_LOCK","market_id":J.market_id,"condition_id":J.condition_id,"token_id":J.tok_0 if e else J.tok_1,"opp_token_id":J.tok_1 if e else J.tok_0,"side_label":"OVER"if e else"UNDER","display_label":f"{J.display_title} [{'OVER'if e else'UNDER'} {m} settled]","fee_rate":J.fee_rate,"fee_exponent":J.fee_exponent,"neg_risk":bool(J.neg_risk),"p_lock":.999,"close_ts":J.settle_est_ts})
    continue
   if m>=int(math.floor(J.line))+3:x.append({"mode":f"SP4_{J.period_scope}_LIVE_OVER_CLINCH","market_id":J.market_id,"condition_id":J.condition_id,"token_id":J.tok_0,"opp_token_id":J.tok_1,"side_label":"OVER","display_label":f"{J.display_title} [Live pts={m} >= {int(math.floor(J.line))+3}]","fee_rate":J.fee_rate,"fee_exponent":J.fee_exponent,"neg_risk":bool(J.neg_risk),"p_lock":.998,"close_ts":J.settle_est_ts})
  elif c and J.kind=="SPREAD"and J.line is not None and J.team_side in f:
   w=J.team_side;u=slate.home_team if w==slate.away_team else slate.away_team;b=float(f[w]-f[u])
   if abs(b-J.line)>=(.5 if i else 1.5):j=b>J.line;x.append({"mode":f"SP4_{J.period_scope}_SETTLED_SPREAD_LOCK","market_id":J.market_id,"condition_id":J.condition_id,"token_id":J.tok_0 if j else J.tok_1,"opp_token_id":J.tok_1 if j else J.tok_0,"side_label":J.out_0 if j else J.out_1,"display_label":f"{J.display_title} [Margin={b:+.0f} settled]","fee_rate":J.fee_rate,"fee_exponent":J.fee_exponent,"neg_risk":bool(J.neg_risk),"p_lock":.999,"close_ts":J.settle_est_ts})
  elif c and J.kind=="ML"and J.team_side in f:
   I=J.team_side;H=slate.home_team if I==slate.away_team else slate.away_team;B=f[I]-f[H]
   if abs(B)>=(1 if i else 2):o=B>0;x.append({"mode":f"SP4_{J.period_scope}_SETTLED_ML_LOCK","market_id":J.market_id,"condition_id":J.condition_id,"token_id":J.tok_0 if o else J.tok_1,"opp_token_id":J.tok_1 if o else J.tok_0,"side_label":J.out_0 if o else J.out_1,"display_label":f"{J.display_title} [{J.out_0 if o else J.out_1} +{abs(B)} settled]","fee_rate":J.fee_rate,"fee_exponent":J.fee_exponent,"neg_risk":bool(J.neg_risk),"p_lock":.999,"close_ts":J.settle_est_ts})
 if i:
  t=ext_summary.get("player_ext")or{}
  for(A,n),s in slate.ext_props_by_player_stat.items():
   r=(t.get(A)or{}).get(n)
   if r is None:continue
   for G in s:
    if int(r)>=int(math.floor(G.line))+2:x.append({"mode":"SP4_FINAL_EXT_STAT_LOCK","market_id":G.market_id,"condition_id":G.condition_id,"token_id":G.yes_token,"opp_token_id":G.no_token,"side_label":"YES","display_label":f"{G.player_name} {n} O{G.line} [Final={r}]","fee_rate":G.fee_rate,"fee_exponent":G.fee_exponent,"neg_risk":False,"p_lock":.998,"close_ts":G.settle_est_ts})
 return x
@dataclass
class MonotonicRung:market_id:str;condition_id:str;label:str;order_val:float;end_ts:float;yes_token:str;no_token:str;fee_rate:float;fee_exponent:float;clause_key:str;neg_risk:bool=False
@dataclass
class CalendarOrScalarLadderSpec:event_id:str;slug:str;title:str;ladder_kind:str;rungs:List[MonotonicRung]
def _canon_clause_stem(desc,group_title):
 s=str(desc or"").lower().replace("“",'"').replace("”",'"').replace("’","'");b=_TZ_DETECT_RE.search(desc or"");a=(b.group(1).upper().replace(" ","_")if b else"NO_TZ");c=str(group_title or"").strip().lower()
 if c and len(c)>=2:s=s.replace(c," <RUNG> ")
 s=_MONTH_DATE_STRIP_RE.sub(" <DATE> ",s);s=re.sub(r"\$\s*[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:[kmbt]|thousand|million|billion|trillion)?\b"," <STRIKE> ",s);s=re.sub(r"\b(greater\s+than|at\s+least|more\s+than|above|over|exceeds?)\s+[0-9][0-9,]*(?:\.[0-9]+)?\s*%?",r"\1 <STRIKE>",s);s=re.sub(r"\s+"," ",s).strip();return s,a
_MONTH_MAP_CAL1={"january":1,"jan":1,"february":2,"feb":2,"march":3,"mar":3,"april":4,"apr":4,"may":5,"june":6,"jun":6,"july":7,"jul":7,"august":8,"aug":8,"september":9,"sep":9,"sept":9,"october":10,"oct":10,"november":11,"nov":11,"december":12,"dec":12}
def _parse_group_label_date_ts(lbl,ref_end_ts):
 e=list(re.finditer(r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:,\s*(20\d{2}))?\b",str(lbl or""),re.IGNORECASE))
 if not e:return None
 m=e[-1];j=_MONTH_MAP_CAL1.get(m.group(1).lower());i=int(m.group(2))
 if not j:return None
 g=max(1.,float(ref_end_ts))
 if m.group(3):
  try:return datetime(int(m.group(3)),j,i,23,59,59,tzinfo=timezone.utc).timestamp()
  except ValueError:return None
 f=datetime.fromtimestamp(g,tz=timezone.utc).year;a=[];b=[]
 for d in(f-1,f,f+1):
  try:c=datetime(d,j,i,23,59,59,tzinfo=timezone.utc).timestamp()
  except ValueError:continue
  b.append(c)
  if c<=g+2.*86400.:a.append(c)
 h=a if a else b
 if not h:return None
 return min(h,key=lambda k:abs(k-g))
def _parse_scalar_strike(lbl):
 s=str(lbl or"").strip()
 if re.search(r"(?:↓|\bbelow\b|\bunder\b|\bless\s+than\b|\bat\s+most\b|\bfewer\s+than\b|\bbetween\b)",s,re.IGNORECASE):return None
 m=_SCALAR_MAG_RE.search(s)
 if not m:return None
 c=float(m.group(1).replace(",",""));b=(m.group(2)or"").lower();a={"k":1e3,"thousand":1e3,"m":1e6,"million":1e6,"b":1e9,"billion":1e9,"t":1e12,"trillion":1e12}.get(b,1.);return c*a
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
 elif any(k in h for k in("fdv above","total commitments","market cap above","box office","revenue above","rotten tomatoes","tomatometer","valuation")):a="SCALAR_ABOVE"
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
   if not any(w in g for w in("above","greater than","exceed","at least","more than","over ","or higher")):continue
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
 _h=[m for m in(ev.get("markets")or[])if not m.get("closed")and not m.get("archived")];r=[m for m in _h if str(m.get("sportsMarketType")or"").lower()=="exact_margin"];z=next((m for m in _h if str(m.get("sportsMarketType")or"").lower()=="moneyline"),None)
 if len(r)!=10 or z is None:return None
 i=_parse_iso_ts(ev.get("startTime")or z.get("gameStartTime")or ev.get("endDate"))or.0;y=i+3.75*3600.
 if now_ts is not None and y<now_ts+60.:return None
 q=_parse_clob_tokens(z);p=[str(o).strip()for o in _parse_json_list(z.get("outcomes"))]
 if not q or len(p)!=2:return None
 x,w=p[0],p[1];_g,_f=_norm_team(x),_norm_team(w);b=[];a=False
 for m in r:
  tk=_parse_clob_tokens(m);_e=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not tk or _e!=["yes","no"]:return None
  fr,fe=_extract_market_fee_rate(m);_l=str(m.get("groupItemTitle")or m.get("question")or"").strip()
  if re.search(r"exact\s+margin:\s*tie\b",_l,re.I):a=True;b.append(("TIE",0,0,m,tk,fr,fe,"Tie"));continue
  mb=_NFL_EM_BAND_RE.search(_l)
  if not mb:return None
  _d=_norm_team(mb.group(1));lo=int(mb.group(2));hi=int(mb.group(3))if mb.group(3)else 999;S="A"if(_d==_g or _d in _g or _g in _d)else("B"if(_d==_f or _d in _f or _f in _d)else"")
  if not S:return None
  b.append((S,lo,hi,m,tk,fr,fe,_l.replace("Exact Margin:","").strip()))
 if not a or len(b)!=10:return None
 for h in("A","B"):
  _k=sorted([(lo,hi)for wk,lo,hi,*_ in b if wk==h])
  if not _k or _k[0][0]!=1 or _k[-1][1]!=999:return None
  for R in range(len(_k)-1):
   if _k[R][1]+1!=_k[R+1][0]:return None
 g=11;_c=[];Q,P=_extract_market_fee_rate(z);O,v=str(z.get("id")or""),str(z.get("conditionId")or"");N=[1. if wk=="A"else(.5 if wk=="TIE"else.0)for wk,*_ in b]+[.5];M=[1. if wk=="B"else(.5 if wk=="TIE"else.0)for wk,*_ in b]+[.5];L=bool(z.get("negRisk"));_c.append({"market_id":O,"condition_id":v,"token_id":q[0],"opp_token_id":q[1],"side":"ML_A","label":f"ML[{x}]","fee_rate":Q,"fee_exponent":P,"neg_risk":L,"end_ts":y,"payoff_vec":N,"strike":.0});_c.append({"market_id":O,"condition_id":v,"token_id":q[1],"opp_token_id":q[0],"side":"ML_B","label":f"ML[{w}]","fee_rate":Q,"fee_exponent":P,"neg_risk":L,"end_ts":y,"payoff_vec":M,"strike":.0})
 for _b,(wk,lo,hi,_a,K,Z,Y,J)in enumerate(b):I=bool(_a.get("negRisk"));f=.0 if I else.5;e=(.0 if wk in("TIE","OTHER")else 1.)if I else.5;_j=[1. if s==_b else.0 for s in range(10)]+[f];_i=[1.-_j[s]for s in range(10)]+[e];H,G=str(_a.get("id")or""),str(_a.get("conditionId")or"");_c.append({"market_id":H,"condition_id":G,"token_id":K[0],"opp_token_id":K[1],"side":"YES","label":f"EM_Y[{J}]","fee_rate":Z,"fee_exponent":Y,"neg_risk":I,"end_ts":y,"payoff_vec":_j,"strike":float(lo)});_c.append({"market_id":H,"condition_id":G,"token_id":K[1],"opp_token_id":K[0],"side":"NO","label":f"EM_N[{J}]","fee_rate":Z,"fee_exponent":Y,"neg_risk":I,"end_ts":y,"payoff_vec":_i,"strike":float(lo)})
 for sm in _h:
  if str(sm.get("sportsMarketType")or"").lower()!="spreads"or sm.get("line")is None:continue
  ln=abs(float(sm.get("line")))
  if not _is_half_hook(ln):continue
  X=_parse_clob_tokens(sm);u=[str(o).strip()for o in _parse_json_list(sm.get("outcomes"))];W=_SPREAD_FAV_RE.search(str(sm.get("question")or sm.get("groupItemTitle")or""))
  if not X or len(u)!=2 or not W:continue
  n=_norm_team(W.group(1));l=float(W.group(2));F=("A"if n==_g else"B")if l<0 else("B"if n==_g else"A")
  if n not in(_g,_f):continue
  if any(wk==F and lo<ln<hi for wk,lo,hi,*_ in b):continue
  V=_norm_team(u[0]);E=_g if F=="A"else _f;k,j=(X[0],X[1])if V==E else(X[1],X[0]);d=x if F=="A"else w;c=w if F=="A"else x;D=[1. if(wk==F and lo>ln)else.0 for wk,lo,hi,*_ in b]+[.5];C=[1.-D[s]for s in range(10)]+[.5];U,T=_extract_market_fee_rate(sm);B,t=str(sm.get("id")or""),str(sm.get("conditionId")or"");A=bool(sm.get("negRisk"));_c.append({"market_id":B,"condition_id":t,"token_id":k,"opp_token_id":j,"side":"SPREAD_FAV","label":f"{d}(-{ln})","fee_rate":U,"fee_exponent":T,"neg_risk":A,"end_ts":y,"payoff_vec":D,"strike":-ln});_c.append({"market_id":B,"condition_id":t,"token_id":j,"opp_token_id":k,"side":"SPREAD_DOG","label":f"{c}(+{ln})","fee_rate":U,"fee_exponent":T,"neg_risk":A,"end_ts":y,"payoff_vec":C,"strike":ln})
 return{"event_id":str(ev.get("id")or""),"slug":str(ev.get("slug")or""),"title":str(ev.get("title")or""),"end_ts":y,"legs":_c}
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
class LiveMultiSportGame:sport:str;game_id:str;start_ts:float;state:str;completed:bool;is_halftime:bool;period:int;clock_sec:float;home_name:str;away_name:str;home_score:int;away_score:int;linescores_home:Dict[int,int]=field(default_factory=dict);linescores_away:Dict[int,int]=field(default_factory=dict)
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
 A=str(ms_spec.sport or"").upper()
 if A not in("NHL","NFL","CFB"):return[]
 s=live_boards.get(A)or[];d=None;c=False;a=float("inf");e=10800. if float(ms_spec.start_ts or.0)>.0 else(8.*3600.)
 for g in s:
  y=abs(float(g.start_ts)-float(ms_spec.start_ts))if(g.start_ts>.0 and float(ms_spec.start_ts or.0)>.0)else.0
  if g.start_ts>.0 and float(ms_spec.start_ts or.0)>.0 and y>e:continue
  if _teams_match_fuzzy(ms_spec.team_a,g.away_name)and _teams_match_fuzzy(ms_spec.team_b,g.home_name):
   if y<a:d,c,a=g,False,y
  elif _teams_match_fuzzy(ms_spec.team_a,g.home_name)and _teams_match_fuzzy(ms_spec.team_b,g.away_name):
   if y<a:d,c,a=g,True,y
 if d is None:return[]
 j=bool(d.completed and d.state=="post");x=d.home_score if c else d.away_score;w=d.away_score if c else d.home_score;v=d.linescores_home if c else d.linescores_away;u=d.linescores_away if c else d.linescores_home;r=[]
 if A=="NHL":
  i=tracker.observe_and_confirmed_floor("NHL",d.game_id,"TOT_GOALS",x+w,now_ts,min_confirm_sec=150.,is_final=j)
  for f in(ms_spec.legs_by_scope.get("FG:TOTAL")or[]):
   if f.relation=="OVER"and i>=int(math.floor(f.threshold))+1:r.append({"mode":"CL1_NHL_POST_CHALLENGE_OVER_LOCK","sport":"NHL","market_id":f.market_id,"condition_id":f.condition_id,"token_id":f.token_id,"opp_token_id":f.opp_token_id,"fee_rate":f.fee_rate,"fee_exponent":f.fee_exponent,"neg_risk":bool(getattr(f,"neg_risk",False)),"side_label":f.side_label,"display_label":f"{ms_spec.title[:38]} {f.display_label} [Goals={i}]","p_lock":.998,"close_ts":float(ms_spec.settle_est_ts)})
  return r
 o=1 if j else 9
 for f in(ms_spec.legs_by_scope.get("FG:TOTAL")or[]):
  if f.relation=="OVER"and(x+w)>=int(math.floor(f.threshold))+o:r.append({"mode":f"CL1_{A}_SCORE_OVER_LOCK","sport":A,"market_id":f.market_id,"condition_id":f.condition_id,"token_id":f.token_id,"opp_token_id":f.opp_token_id,"fee_rate":f.fee_rate,"fee_exponent":f.fee_exponent,"neg_risk":bool(getattr(f,"neg_risk",False)),"side_label":f.side_label,"display_label":f"{ms_spec.title[:36]} {f.display_label} [Score={x}-{w}]","p_lock":.999 if j else.997,"close_ts":float(ms_spec.settle_est_ts)})
 for n,t in ms_spec.legs_by_scope.items():
  z=n.split(":")[0];m,l,b=None,None,False
  if z in("Q1","Q2","Q3"):
   q=int(z[1])
   if q in v and q in u:m,l=v[q],u[q];b=j or(q==1 and d.is_halftime)or(d.period>q and(d.clock_sec<=780. or d.period>=q+2))
  elif z=="1H":
   if 1 in v and 1 in u and 2 in v and 2 in u:m,l=v[1]+v[2],u[1]+u[2];b=j or d.is_halftime or d.period>=3
  if not b or m is None or l is None:continue
  if n.endswith(":TOTAL"):
   p=float(m+l)
   for f in t:
    k=(p>f.threshold)if f.relation=="OVER"else(p<f.threshold)
    if k and abs(p-f.threshold)>=.5:r.append({"mode":f"CL1_{A}_{z}_SETTLED_TOTAL_LOCK","sport":A,"market_id":f.market_id,"condition_id":f.condition_id,"token_id":f.token_id,"opp_token_id":f.opp_token_id,"fee_rate":f.fee_rate,"fee_exponent":f.fee_exponent,"neg_risk":bool(getattr(f,"neg_risk",False)),"side_label":f.side_label,"display_label":f"{ms_spec.title[:34]} {f.display_label} [{z}={int(p)} settled]","p_lock":.999,"close_ts":float(ms_spec.settle_est_ts)})
  elif n.endswith(":SPREAD"):
   h=float(m-l)
   for f in t:
    k=(h>f.threshold)if f.relation=="GT"else(h<f.threshold)
    if k and abs(h-f.threshold)>=.5:r.append({"mode":f"CL1_{A}_{z}_SETTLED_SPREAD_LOCK","sport":A,"market_id":f.market_id,"condition_id":f.condition_id,"token_id":f.token_id,"opp_token_id":f.opp_token_id,"fee_rate":f.fee_rate,"fee_exponent":f.fee_exponent,"neg_risk":bool(getattr(f,"neg_risk",False)),"side_label":f.side_label,"display_label":f"{ms_spec.title[:34]} {f.display_label} [{z} M={h:+.0f}]","p_lock":.999,"close_ts":float(ms_spec.settle_est_ts)})
 return r
@dataclass
class TennisTotalRung:market_id:str;condition_id:str;scope:str;line:float;over_token:str;under_token:str;fee_rate:float;fee_exp:float;neg_risk:bool=False
@dataclass
class TennisMatchSpec:event_id:str;slug:str;title:str;player_a:str;player_b:str;end_ts:float;totals_by_scope:Dict[str,List[TennisTotalRung]]=field(default_factory=dict);set1_a_token:Optional[str]=None;set1_b_token:Optional[str]=None;set1_resolved_winner:Optional[str]=None;set2_a_token:Optional[str]=None;set2_b_token:Optional[str]=None;set2_resolved_winner:Optional[str]=None;sets_ou25_over_token:Optional[str]=None;sets_ou25_under_token:Optional[str]=None;sets_ou25_market_id:str="";sets_ou25_condition_id:str="";sets_ou25_fee_rate:float=.05;sets_ou25_fee_exp:float=1.;sets_ou25_neg_risk:bool=False;comp_yes_token:Optional[str]=None;comp_no_token:Optional[str]=None;comp_market_id:str="";comp_condition_id:str="";comp_fee_rate:float=.05;comp_fee_exp:float=1.;comp_neg_risk:bool=False
def parse_tennis_retirement_safe_event(ev,now_ts=None):
 if ev.get("closed")or ev.get("archived")or ev.get("negRisk"):return None
 q=str(ev.get("slug")or"").lower();p=ev.get("markets")or[]
 if not(q.startswith(("atp-","wta-"))or any(str(m.get("sportsMarketType")or"").startswith("tennis_")for m in p)):return None
 for m in p:
  g=str(m.get("groupItemTitle")or m.get("question")or"").lower()
  if re.search(r"\bset\s+[45]\b",g):return None
  if str(m.get("sportsMarketType")or"").lower()=="tennis_set_totals"and m.get("line")is not None and float(m.get("line"))>3.:return None
 n=next((m for m in p if str(m.get("sportsMarketType")or"").lower()=="moneyline"),None)
 if n is None:return None
 e=[str(o).strip()for o in _parse_json_list(n.get("outcomes"))]
 if len(e)!=2:return None
 A,z=e[0],e[1];l,j=_norm_team(A),_norm_team(z);f=(_parse_iso_ts(ev.get("startTime")or n.get("gameStartTime")or ev.get("endDate"))or.0)+3.25*3600.
 if now_ts is not None and f<now_ts+60.:return None
 i=TennisMatchSpec(event_id=str(ev.get("id")or""),slug=q,title=str(ev.get("title")or q),player_a=A,player_b=z,end_ts=f)
 def a(cm):
  D=_parse_clob_tokens(cm);o=[_norm_team(str(x))for x in _parse_json_list(cm.get("outcomes"))];k=_parse_json_list(cm.get("outcomePrices"));v,r=None,None
  if D and len(o)==2 and{o[0],o[1]}=={l,j}:v,r=(D[0],D[1])if o[0]==l else(D[1],D[0])
  m=None
  if len(k)==2 and len(o)==2:
   try:
    C,B=float(k[0]),float(k[1])
    if cm.get("closed")or(max(C,B)>=.995 and min(C,B)<=.005):
     if C>=.995 and B<=.005:m="A"if o[0]==l else"B"
     elif B>=.995 and C<=.005:m="A"if o[1]==l else"B"
   except(TypeError,ValueError):pass
  return v,r,m
 for m in p:
  t=str(m.get("sportsMarketType")or"").strip().lower();s=str(m.get("groupItemTitle")or m.get("question")or"")
  if t=="tennis_first_set_winner":i.set1_a_token,i.set1_b_token,i.set1_resolved_winner=a(m);continue
  if t=="tennis_set_winner"and(str(m.get("line")or"")=="2"or"set 2"in s.lower()):i.set2_a_token,i.set2_b_token,i.set2_resolved_winner=a(m);continue
  if m.get("closed")or m.get("archived")or m.get("acceptingOrders")is False:continue
  tk=_parse_clob_tokens(m);h=[str(o).strip().lower()for o in _parse_json_list(m.get("outcomes"))]
  if not tk or len(h)!=2:continue
  y,w=_extract_market_fee_rate(m)
  if t=="tennis_completed_match"and h==["yes","no"]:i.comp_yes_token,i.comp_no_token=tk[0],tk[1];i.comp_market_id=str(m.get("id")or"");i.comp_condition_id=str(m.get("conditionId")or"");i.comp_fee_rate,i.comp_fee_exp=y,w;i.comp_neg_risk=bool(m.get("negRisk"))
  elif t=="tennis_set_totals"and m.get("line")is not None and abs(float(m.get("line"))-2.5)<1e-6:
   if h[0].startswith("over")and h[1].startswith("under"):i.sets_ou25_over_token,i.sets_ou25_under_token=tk[0],tk[1];i.sets_ou25_market_id=str(m.get("id")or"");i.sets_ou25_condition_id=str(m.get("conditionId")or"");i.sets_ou25_fee_rate,i.sets_ou25_fee_exp=y,w;i.sets_ou25_neg_risk=bool(m.get("negRisk"))
  elif t in("tennis_first_set_totals","tennis_set_games_totals","tennis_match_totals")and m.get("line")is not None:
   u=float(m.get("line"))
   if not _is_half_hook(u)or not(h[0].startswith("over")and h[1].startswith("under")):continue
   if t=="tennis_first_set_totals":d="SET1_GAMES"
   elif t=="tennis_match_totals":d="MATCH_GAMES"
   elif"set 2"in s.lower():d="SET2_GAMES"
   elif"set 3"in s.lower():d="SET3_GAMES"
   else:continue
   i.totals_by_scope.setdefault(d,[]).append(TennisTotalRung(market_id=str(m.get("id")or""),condition_id=str(m.get("conditionId")or""),scope=d,line=u,over_token=tk[0],under_token=tk[1],fee_rate=y,fee_exp=w,neg_risk=bool(m.get("negRisk"))))
 for k in i.totals_by_scope:i.totals_by_scope[k].sort(key=lambda r:r.line)
 c=any(len(v)>=2 for v in i.totals_by_scope.values());b=bool(i.sets_ou25_over_token and i.comp_no_token)
 if not(c or b):return None
 return i
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
# [15/20] MODULE: src/polymarket_research/riskless_frontier_v4_engine.py
# PURPOSE: Riskless Frontier v4 Evergreen Engine (AFF1 Subperiod Collapse, SOC2 83-State Lattice, NFL_PRP1 Locks, SUM1 Frechet Triangles, CRY_INC1 Binance Inclusion, MKR_LOCK1)
# ======================================================================================

import json;import math;import re;import urllib.request;from dataclasses import dataclass,field;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;from src.polymarket_research.barrier_onetouch_svi_engine import(BarrierRungSpec,parse_barrier_direction,parse_hit_event,parse_strike_from_text);from src.polymarket_research.riskless_frontier_v2_engine import(NegRiskConvertSlateSpec,_is_half_hook,canon_player_name,detect_nr2_convert_no_subset_arbs,find_state_matrix_dominance_boxes);from src.polymarket_research.riskless_frontier_v3_engine import(LiveMultiSportGame,NbaSubperiodMarketSpec,ScoreConfirmationTracker,_teams_match_fuzzy,parse_nba_subperiod_and_ext_props);from src.polymarket_research.tradfi_sports_zero_fee_engine import(_SPREAD_FAV_RE,_extract_market_fee_rate,_net_unit_ask,_norm_team,_parse_clob_tokens,_parse_iso_ts);from src.polymarket_research.uma_nba_endgame_engine import(_canon_nba_team,_parse_json_list);FRONTIER_V4_GRAD8_SLEEVES=("AFF1_FROZEN_SUBPERIOD_COLLAPSE","SOC2_EXACT_SCORE_2D_LATTICE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS","SUM1_FRECHET_SUM_TRIANGLES","CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER");ESPN_NFL_SUMMARY_URL="https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={game_id}"
@dataclass
class FirstPassageMarketSpec:event_id:str;market_id:str;condition_id:str;kind:str;target_pts:int;away_token:str;home_token:str;away_label:str;home_label:str;fee_rate:float;fee_exponent:float;settle_est_ts:float;neg_risk:bool=False
@dataclass
class AffineGameBundle:
 sport:str;event_id:str;slug:str;title:str;tipoff_ts:float;settle_est_ts:float;away_team:str;home_team:str;markets:List[NbaSubperiodMarketSpec]=field(default_factory=list);overtime_yes_leg:Optional[Dict[str,Any]]=None;first_passage_markets:List[FirstPassageMarketSpec]=field(default_factory=list)
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
 g=[];f=[];e=[];X=str(live_summary.get("state")or"pre").lower()
 if X not in("in","post"):return{"two_leg_boxes":g,"three_leg_boxes":f,"single_leg_locks":e}
 y=bool(live_summary.get("completed")and X=="post");W=bool(live_summary.get("is_halftime"));Q=int(live_summary.get("period")or 0);J=int(live_summary.get("away_score")or 0);I=int(live_summary.get("home_score")or 0);_m=(live_summary.get("linescores")or{}).get("away")or{};_l=(live_summary.get("linescores")or{}).get("home")or{};_u=espn_game_id or bundle.event_id
 def c(mode,lg_a,lg_b,middle_width,desc):
  if lg_a["market_id"]==lg_b["market_id"]:return
  x=best_asks.get(lg_a["token_id"]);q=best_asks.get(lg_b["token_id"])
  if x is None or q is None or not(.005<=x<=.99 and.005<=q<=.99):return
  m=round(_net_unit_ask(float(x),lg_a["fee_rate"],lg_a["fee_exponent"])+_net_unit_ask(float(q),lg_b["fee_rate"],lg_b["fee_exponent"]),4)
  if m<=max_2leg_cost_net:g.append({"mode":mode,"sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"box_cost_gross":round(float(x)+float(q),4),"box_cost_net":m,"middle_width":round(float(middle_width),1),"close_ts":max(float(lg_a["end_ts"]),float(lg_b["end_ts"])),"leg_a":lg_a,"leg_b":lg_b,"label":f"{bundle.title}: {desc}"})
 w=(1 in _m and 1 in _l)and(y or W or Q>=2);H=freeze_tracker.confirm_frozen_pair(bundle.sport,_u,"Q1",int(_m.get(1,0)),int(_l.get(1,0)),period_ended=w,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=(y or W or Q>=3))
 if H is not None and not W and Q<=2 and not y:
  _k,_j=H;_i=float(_k+_j);_h=float(_k-_j);_g=[m for m in bundle.markets if m.period_scope=="1H"and m.kind=="TOTAL"and m.line is not None];_f=[m for m in bundle.markets if m.period_scope=="Q2"and m.kind=="TOTAL"and m.line is not None]
  for m1 in _g:
   _e=float(m1.line);G=_e-_i
   for m2 in _f:
    _d=float(m2.line)
    if G<=_d+1e-9:c("AFF1_POST_Q1_1H_VS_Q2_TOTAL",_leg_dict_from_subspec(m1,True,f"1H O{_e:g}"),_leg_dict_from_subspec(m2,False,f"Q2 U{_d:g}"),_d-G,f"1H O{_e:g} + Q2 U{_d:g} (Q1={int(_i)} frozen)")
    if _d<=G+1e-9:c("AFF1_POST_Q1_1H_VS_Q2_TOTAL",_leg_dict_from_subspec(m1,False,f"1H U{_e:g}"),_leg_dict_from_subspec(m2,True,f"Q2 O{_d:g}"),G-_d,f"1H U{_e:g} + Q2 O{_d:g} (Q1={int(_i)} frozen)")
  V=[x for m in bundle.markets if m.period_scope=="1H"and m.kind=="SPREAD"for x in _spread_signed_legs(m,bundle.away_team)];U=[x for m in bundle.markets if m.period_scope=="Q2"and m.kind=="SPREAD"for x in _spread_signed_legs(m,bundle.away_team)]
  for _t,_s,_r in V:
   P=_s-_h
   for _q,_p,_o in U:
    if _t=="GT"and _q=="LT"and P<=_p+1e-9:c("AFF1_POST_Q1_1H_VS_Q2_SPREAD",_r,_o,_p-P,f"{_r['label']} + {_o['label']} (mQ1={_h:+.0f})")
    elif _t=="LT"and _q=="GT"and _p<=P+1e-9:c("AFF1_POST_Q1_1H_VS_Q2_SPREAD",_r,_o,P-_p,f"{_r['label']} + {_o['label']} (mQ1={_h:+.0f})")
 if bundle.sport=="NBA":
  v=(1 in _m and 2 in _m and 1 in _l and 2 in _l)and(y or W or Q>=3);F=freeze_tracker.confirm_frozen_pair(bundle.sport,_u,"1H",int(_m.get(1,0))+int(_m.get(2,0)),int(_l.get(1,0))+int(_l.get(2,0)),period_ended=v,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=(y or Q>=4))
  if F is not None and not y:
   n={bundle.away_team:float(F[0]),bundle.home_team:float(F[1])}
   for tm,O in n.items():
    N=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TEAM_TOTAL"and m.team_side==tm and m.line is not None];M=[m for m in bundle.markets if m.period_scope=="2H"and m.kind=="TEAM_TOTAL"and m.team_side==tm and m.line is not None]
    for t in N:
     s=float(t.line);T=s-O
     for _c in M:
      _b=float(_c.line)
      if T<=_b+1e-9:c("AFF1_HT_TEAM_TOTAL_FG_VS_2H",_leg_dict_from_subspec(t,True,f"FG {tm.title()} O{s:g}"),_leg_dict_from_subspec(_c,False,f"2H {tm.title()} U{_b:g}"),_b-T,f"{tm.title()} FG O{s:g} + 2H U{_b:g} (1H={int(O)})")
      if _b<=T+1e-9:c("AFF1_HT_TEAM_TOTAL_FG_VS_2H",_leg_dict_from_subspec(t,False,f"FG {tm.title()} U{s:g}"),_leg_dict_from_subspec(_c,True,f"2H {tm.title()} O{_b:g}"),T-_b,f"{tm.title()} FG U{s:g} + 2H O{_b:g} (1H={int(O)})")
 if bundle.sport=="NBA":
  u=all(q in _m and q in _l for q in(1,2,3))and(y or Q>=4);E=freeze_tracker.confirm_frozen_pair(bundle.sport,_u,"Q1_Q3",int(_m.get(1,0))+int(_m.get(2,0))+int(_m.get(3,0)),int(_l.get(1,0))+int(_l.get(2,0))+int(_l.get(3,0)),period_ended=u,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=y)
  if E is not None and not y and Q==4:
   S=float(E[0]+E[1]);D=[m for m in bundle.markets if m.period_scope=="FG"and m.kind=="TOTAL"and m.line is not None];C=[m for m in bundle.markets if m.period_scope=="Q4"and m.kind=="TOTAL"and m.line is not None];L=bundle.overtime_yes_leg;R=best_asks.get(L["token_id"])if L is not None else None;_a=_net_unit_ask(float(R),L["fee_rate"],L["fee_exponent"])if(L and R is not None)else None
   for t in D:
    s=float(t.line);K=s-S
    for Z in C:
     Y=float(Z.line)
     if K<=Y+1e-9:c("AFF1_POST_Q3_FG_OVER_4Q_UNDER",_leg_dict_from_subspec(t,True,f"FG O{s:g}"),_leg_dict_from_subspec(Z,False,f"4Q U{Y:g}"),Y-K,f"FG O{s:g} + 4Q U{Y:g} (Q1..3={int(S)})")
     if Y<=K+1e-9 and L is not None and R is not None and _a is not None:
      B=_leg_dict_from_subspec(t,False,f"FG U{s:g}");A=_leg_dict_from_subspec(Z,True,f"4Q O{Y:g}");pu=best_asks.get(B["token_id"]);po=best_asks.get(A["token_id"])
      if(pu is not None and po is not None and.005<=float(pu)<=.99 and.005<=float(po)<=.99 and.005<=float(R)<=.99):
       c3=round(_net_unit_ask(float(pu),B["fee_rate"],B["fee_exponent"])+_net_unit_ask(float(po),A["fee_rate"],A["fee_exponent"])+_a,4)
       if c3<=max_3leg_cost_net:f.append({"mode":"AFF1_POST_Q3_OT_IMMUNIZED_3LEG","sport":bundle.sport,"event_id":bundle.event_id,"slug":bundle.slug,"title":bundle.title,"n_legs":3,"box_cost_gross":round(float(pu)+float(po)+float(R),4),"box_cost_net":c3,"middle_width":round(K-Y,1),"close_ts":max(B["end_ts"],A["end_ts"],L["end_ts"]),"legs":[B,A,L],"label":f"{bundle.title}: FG U{s:g} + 4Q O{Y:g} + YES[OT] (Q1..3={int(S)})"})
 for fp in bundle.first_passage_markets:
  _n=2 if fp.kind=="FIRST_SCORE"else 3;r=freeze_tracker.observe_and_confirm_race_winner(bundle.sport,_u,fp.target_pts,J,I,now_ts=now_ts,buffer_pts=_n,confirm_sec=freeze_confirm_sec,is_final=y)
  if r in("AWAY","HOME"):z=r=="AWAY";e.append({"mode":f"AFF1_{fp.kind}_LOCK","sport":bundle.sport,"event_id":bundle.event_id,"market_id":fp.market_id,"condition_id":fp.condition_id,"token_id":fp.away_token if z else fp.home_token,"opp_token_id":fp.home_token if z else fp.away_token,"side_label":fp.away_label if z else fp.home_label,"display_label":(f"{bundle.title} {'First Score'if fp.kind=='FIRST_SCORE'else f'Race to {fp.target_pts}'}: {fp.away_label if z else fp.home_label} [{J}-{I}]"),"fee_rate":fp.fee_rate,"fee_exponent":fp.fee_exponent,"neg_risk":fp.neg_risk,"p_lock":.998,"close_ts":fp.settle_est_ts})
 d={str(x["market_id"])for x in e}
 def a(scope,abs_diff):
  if not(W and not y and Q<3 and scope in("Q2","1H")and abs_diff<3.49):return False
  m="Q2_ONLY"if scope=="Q2"else"1H_LOCK";q=freeze_tracker._frozen_since.get((bundle.sport.upper(),str(_u),m))
  if q is None:return True
  return(float(now_ts)-float(q[1]))<480.
 def b(scope,a_pts,h_pts):
  _y=float(a_pts+h_pts);_B=float(a_pts-h_pts);_A="AFF1_FINAL_SUBPERIOD_LOCK"if y else f"AFF1_{scope}_SETTLED_LOCK"
  for sm in bundle.markets:
   if sm.period_scope!=scope or sm.line is None or sm.market_id in d:continue
   ln=float(sm.line);_v=None;x=None;q=None;m=""
   if sm.kind=="TOTAL"and abs(_y-ln)>=.49:
    if a(scope,abs(_y-ln)):continue
    _w=_y>ln;_v=sm.tok_0 if _w else sm.tok_1;x=sm.tok_1 if _w else sm.tok_0;q=sm.out_0 if _w else sm.out_1;m=f"{scope} Total={int(_y)} vs {ln:g}"
   elif sm.kind=="TEAM_TOTAL"and sm.team_side in(bundle.away_team,bundle.home_team):
    _z=float(a_pts if sm.team_side==bundle.away_team else h_pts)
    if abs(_z-ln)>=.49:
     if a(scope,abs(_z-ln)):continue
     _w=_z>ln;_v=sm.tok_0 if _w else sm.tok_1;x=sm.tok_1 if _w else sm.tok_0;q=sm.out_0 if _w else sm.out_1;m=f"{scope} {sm.team_side.title()}={int(_z)} vs {ln:g}"
   elif sm.kind=="SPREAD":
    _x=_spread_signed_legs(sm,bundle.away_team)
    if len(_x)==2 and abs(_B-float(_x[0][1]))>=.49:
     if a(scope,abs(_B-float(_x[0][1]))):continue
     for _E,_D,_C in _x:
      if(_E=="GT"and _B>_D)or(_E=="LT"and _B<_D):_v=str(_C["token_id"]);x=str(_C["opp_token_id"]);q=str(_C["label"]);m=f"{scope} Margin={a_pts}-{h_pts} ({_B:+.0f} vs {_D:+.1f})";break
   if _v and x and q:d.add(sm.market_id);e.append({"mode":_A,"sport":bundle.sport,"event_id":bundle.event_id,"market_id":sm.market_id,"condition_id":sm.condition_id,"token_id":_v,"opp_token_id":x,"side_label":q,"display_label":f"{bundle.title} {sm.display_title} -> {q} [{m}]","fee_rate":sm.fee_rate,"fee_exponent":sm.fee_exponent,"neg_risk":bool(sm.neg_risk),"p_lock":1.,"close_ts":sm.settle_est_ts})
 if H is not None:b("Q1",int(H[0]),int(H[1]))
 l=(2 in _m and 2 in _l)and(y or W or Q>=3);p=freeze_tracker.confirm_frozen_pair(bundle.sport,_u,"Q2_ONLY",int(_m.get(2,0)),int(_l.get(2,0)),period_ended=l,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=(y or Q>=4))
 if p is not None:b("Q2",int(p[0]),int(p[1]))
 h=(1 in _m and 2 in _m and 1 in _l and 2 in _l)and(y or W or Q>=3);k=freeze_tracker.confirm_frozen_pair(bundle.sport,_u,"1H_LOCK",int(_m.get(1,0))+int(_m.get(2,0)),int(_l.get(1,0))+int(_l.get(2,0)),period_ended=h,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=(y or Q>=4))
 if k is not None:b("1H",int(k[0]),int(k[1]))
 j=(3 in _m and 3 in _l)and(y or Q>=4);o=freeze_tracker.confirm_frozen_pair(bundle.sport,_u,"Q3_ONLY",int(_m.get(3,0)),int(_l.get(3,0)),period_ended=j,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=y)
 if o is not None:b("Q3",int(o[0]),int(o[1]))
 if y:
  i=freeze_tracker.confirm_frozen_pair(bundle.sport,_u,"FINAL_FG",J,I,period_ended=True,now_ts=now_ts,freeze_confirm_sec=freeze_confirm_sec,instant_settled=False)
  if i is not None:b("FG",int(i[0]),int(i[1]))
 g.sort(key=lambda x:float(x["box_cost_net"]));f.sort(key=lambda x:float(x["box_cost_net"]));return{"two_leg_boxes":g,"three_leg_boxes":f,"single_leg_locks":e}
SOC2_GRID_MAX=8;SOC2_PLAYED_STATES=[(h,a)for h in range(SOC2_GRID_MAX+1)for a in range(SOC2_GRID_MAX+1)];SOC2_NUM_STATES=len(SOC2_PLAYED_STATES)+2;_EXACT_SCORE_ITEM_RE=re.compile(r"(\d+)\s*[-–:]\s*(\d+)");_SOC_ADV_VETO_RE=re.compile(r"(\badvance\b|\bqualify\b|\blift the trophy\b|\bincluding extra time\b|\bpenalties\b)",re.IGNORECASE);_SOC_SUBPERIOD_OR_PROP_VETO_RE=re.compile(r"(\bfirst[\s_-]+half\b|\bsecond[\s_-]+half\b|\b1st[\s_-]+half\b|\b2nd[\s_-]+half\b" r"|\bhalftime\b|\bhalf-time\b|\beach[\s_-]+half\b|\bboth[\s_-]+halves\b" r"|\b1h\b|\b2h\b|\bteam[\s_-]+totals?\b|\bcorners?\b|\bcards?\b|\bshots?\b|\boffsides?\b)",re.IGNORECASE)
@dataclass
class SoccerExactScoreLattice:game_key:str;game_id:str;title:str;end_ts:float;home_team:str;away_team:str;exact_event_id:str;exact_slug:str;exact_neg_risk_market_id:str;is_closed_37_slate:bool;score_brackets:Dict[Tuple[int,int],Dict[str,Any]];any_other_bracket:Optional[Dict[str,Any]];convert_spec:Optional[NegRiskConvertSlateSpec];matrix_legs:List[Dict[str,Any]]=field(default_factory=list)
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
class NflPlayerPropRung:event_id:str;event_slug:str;game_title:str;market_id:str;condition_id:str;player_name:str;player_key:str;stat_type:str;line:float;yes_over_token:str;no_under_token:str;fee_rate:float;fee_exponent:float;kickoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;dnp_resolves_no:bool=False
@dataclass
class NflPlayerPropSlate:event_id:str;slug:str;title:str;kickoff_ts:float;settle_est_ts:float;home_team:str;away_team:str;anytime_td_by_player:Dict[str,NflPlayerPropRung]=field(default_factory=dict);two_plus_td_by_player:Dict[str,NflPlayerPropRung]=field(default_factory=dict);ladders_by_player_stat:Dict[Tuple[str,str],List[NflPlayerPropRung]]=field(default_factory=dict)
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
 n={};d=[];c=set()
 for j in((summary_json or{}).get("boxscore")or{}).get("players")or[]:
  s=str((j.get("team")or{}).get("id")or"")
  for i in j.get("statistics")or[]:
   H=str(i.get("name")or"").lower();y=[str(k)for k in(i.get("keys")or i.get("labels")or[])]
   for G in i.get("athletes")or[]:
    w=canon_player_name(str((G.get("athlete")or{}).get("displayName")or""))
    if not w:continue
    if G.get("didNotPlay"):d.append((s,w));continue
    F=[str(x)for x in(G.get("stats")or[])]
    if not F:continue
    c.add(s);q=n.setdefault(w,{"rush_rec_tds":0})
    def a(key_aliases):
     for k,x in enumerate(y):
      if x in key_aliases and k<len(F):
       try:return int(float(F[k].strip()))
       except ValueError:return None
     return None
    if H=="passing":
     for idx_k,kk in enumerate(y):
      if("completions"in kk or kk.upper()=="C/ATT")and idx_k<len(F)and"/"in F[idx_k]:
       E,D=F[idx_k].split("/",1)
       try:q["passing_completions"]=int(E);q["passing_attempts"]=int(D)
       except ValueError:pass
     N=a(("passingYards","YDS"));C=a(("passingTouchdowns","TD"))
     if N is not None:q["passing_yards"]=N
     if C is not None:q["passing_touchdowns"]=C
    elif H=="rushing":
     M=a(("rushingYards","YDS"));B=a(("rushingTouchdowns","TD"));L=a(("longRushing","LONG"))
     if M is not None:q["rushing_yards"]=M
     if L is not None:q["longest_rush"]=L
     if B is not None:q["rushing_tds"]=B
    elif H=="receiving":
     K=a(("receptions","REC"));A=a(("receivingYards","YDS"));v=a(("receivingTouchdowns","TD"));u=a(("longReception","LONG"))
     if K is not None:q["receptions"]=K
     if A is not None:q["receiving_yards"]=A
     if u is not None:q["longest_reception"]=u
     if v is not None:q["receiving_tds"]=v
    elif H in("defensive","kickreturns","puntreturns","fumbles","interceptions"):
     z=a(("defensiveTouchdowns","kickReturnTouchdowns","puntReturnTouchdowns","fumbleRecoveryTouchdowns","interceptionTouchdowns","touchdowns","TD"))
     if z is not None and z>0:q["non_off_tds"]=int(q.get("non_off_tds",0))+z
 for q in n.values():q["rush_rec_tds"]=int(q.get("rushing_tds",0))+int(q.get("receiving_tds",0));q["all_tds"]=int(q["rush_rec_tds"])+int(q.get("non_off_tds",0))
 e=[]
 for m in(summary_json or{}).get("scoringPlays")or[]:
  if not isinstance(m,dict):continue
  l=str(((m.get("scoringType")or{}).get("abbreviation")or(m.get("type")or{}).get("text")or"")).upper();p=str(m.get("text")or"")
  if"TD"in l or"TOUCHDOWN"in l or"touchdown"in p.lower():e.append(canon_player_name(p))
 g={O for(P,O)in d if P in c and O not in n};h,b,f,o="pre",False,0,"";r=((summary_json or{}).get("header")or{}).get("competitions")or[]
 if r:J=r[0];o=str(J.get("id")or"");I=J.get("status")or{};t=I.get("type")or{};h=str(t.get("state")or"pre").lower();b=bool(t.get("completed"));f=int(I.get("period")or 0)
 return{"game_id":o,"state":h,"completed":b,"period":f,"players":n,"inactive_players":g,"td_scoring_texts":e}
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
# [16/20] MODULE: src/polymarket_research/alpha_124_shadow_daemon.py
# PURPOSE: Unified Multi-Vertical Shadow Daemon (Crypto, Weather METAR/HKO, Pyth Commodities/Metals/Equities, Sports, UMA Bonds, Frontier v2/v3/v4)
# ======================================================================================

import argparse;import asyncio;import collections;import json;import logging;import math;import os;import re;import sqlite3;import sys;import time;from datetime import datetime,timezone;from pathlib import Path;from typing import Any,Deque,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo
try:import aiohttp
except ImportError:aiohttp=None
PROJECT_ROOT=Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT)not in sys.path:sys.path.insert(0,str(PROJECT_ROOT))
from src.polymarket_research.barrier_onetouch_svi_engine import(ASSET_BINANCE_SYMBOL,BINANCE_FAPI_URL,HIT_SERIES,BarrierRungSpec,detect_barrier_monotonicity_boxes,evaluate_barrier_no_net_ev,fetch_binance_window_extremes_sync,first_passage_touch_prob,get_wing_implied_vol,parse_hit_event);from src.polymarket_research.multistrike_svi_scalper import(DAILY_UPDOWN_SERIES,NEGRISK_SERIES,STRIKE_SERIES,ZERO_FEE_PYTH_DAILY_SERIES,DailyUpDownSpec,NegRiskBracketSpec,StrikeRungSpec,_fast_norm_cdf,build_negrisk_cross_box_bundles,detect_ladder_monotonicity_boxes,evaluate_coherent_strike_ladder,evaluate_svi_digital_fair_value,parse_daily_updown_event,parse_multistrike_event,parse_negrisk_bracket_event);from src.polymarket_research.net_alpha_opportunity_engine import(publish_global_positions_shm,rank_opportunities_capital_auction,read_global_positions_shm,scan_binary_complete_set_arb);from src.polymarket_research.orderflow_wfo_simulators import(compute_d1_legging_drag_haircut,compute_d1_maker_anchor_drag_haircut);from src.polymarket_research.riskless_machine_gun_engine import is_reward_locked_carry_live_ready;from src.polymarket_research.same_oracle_dominance_box import(DOMINANCE_ASSETS,DOMINANCE_SERIES_SLUGS,EMPIRICAL_BOX_ASSET_CAPS_USD,MIN_CORRIDOR_BPS_BY_ASSET,METAL_DOMINANCE_ASSETS,METAL_DOMINANCE_SERIES_SLUGS,TwapCandleMarketSpec,build_crypto_price_query_url,build_deterministic_updown_event_slug,build_own_gamma_event_url,build_prev_15m_gamma_event_url,build_prev_5m_gamma_event_url,determine_dominance_legs,parse_authoritative_close_price,parse_authoritative_open_price,parse_closed_gamma_event_settlement,parse_metal_forex_candle_event,parse_twap_candle_event,verify_same_oracle_pair,walk_equal_shares_dominance_box,walk_equal_shares_multi_leg_box);from src.polymarket_research.exact_twap_lock_engine import(compute_exact_twap_lock_probability,read_shm_usd_anchor)
try:from src.polymarket_research.polymarket_ws_streams import PolymarketChainlinkLiveStream
except ImportError:
 try:from polymarket_ws_streams import PolymarketChainlinkLiveStream
 except ImportError:PolymarketChainlinkLiveStream=None
try:from src.polymarket_research.riskless_fast_feeds import PolygonScopedLogsWs,PythHermesStream
except Exception:PolygonScopedLogsWs=None;PythHermesStream=None
try:from src.polymarket_research.economic_attribution_ledger import(GLOBAL_DECAY_TRACKER as _STAGE_B_DECAY_TRACKER,emit_funnel_event as _stage_b_emit_funnel)
except Exception:_STAGE_B_DECAY_TRACKER=None;_stage_b_emit_funnel=None
from src.polymarket_research.weather_metar_engine import(HIGH_VOLUME_WEATHER_SERIES,MetarObservation,WeatherEventSpec,celsius_to_market_int,compute_adaptive_metar_poll_ttl,compute_weather_probabilities,evaluate_weather_event_slate,fetch_live_ensemble_hourly_sync,fetch_metar_observations_sync,fetch_taf_extremes_sync,parse_weather_event);from src.polymarket_research.tradfi_sports_zero_fee_engine import(MULTI_SPORT_CORRIDOR_SERIES,NBA_SERIES_SLUGS,PYTH_ASSET_CONFIG,PYTH_CLOSE_SERIES,PYTH_HIT_SERIES,ZERO_FEE_NEGRISK_SERIES,MultiSportCorridorSpec,NbaGameSpec,NegRiskConvertSlateSpec,PythBarrierRungSpec,PythCloseRungSpec,ZeroFeeNegRiskSlateSpec,compute_effective_trading_hours,detect_multi_sport_corridor_boxes,detect_nba_dominance_boxes,detect_negrisk_convert_positions_arbs,detect_negrisk_no_pair_boxes,detect_pyth_calendar_inclusion_boxes,detect_pyth_close_vs_hit_boxes,evaluate_pyth_session_barrier_no_lock,evaluate_pyth_session_close_lock,fetch_pyth_intraday_or_spot_sync,fetch_yahoo_1m_intraday_sync,is_same_continuous_session,parse_multi_sport_corridor_event,parse_nba_zero_fee_event,parse_negrisk_convert_event,parse_pyth_close_event,parse_pyth_hit_event,parse_zero_fee_negrisk_slate,window_extremes_from_bars,_extract_market_fee_rate,_parse_clob_tokens,_parse_iso_ts);from src.polymarket_research.macro_counting_ctf_engine import(ALL_FOMC_MASK,ALL_OIL_SENATE_MASK,COUNTING_SERIES_HANDLES,FOMC_PARLAY_SERIES,GAS_SERIES_SLUGS,HOURLY_BINANCE_SERIES,NY_TZ,OIL_SENATE_SLUGS,XTRACKER_ALL_HANDLES,CountingSlateSpec,build_fomc_truth_table_legs,build_oil_senate_truth_table_legs,detect_counting_pruned_exhaustive_yes_slate,detect_counting_subwindow_boxes,detect_d2_12pm_binance_boxes,evaluate_counting_dead_no_locks,evaluate_locked_market_reward_carry,evaluate_pyth_catalyst_shock,extract_xtracker_active_event_slugs,fetch_aaa_national_gas_sync,fetch_xtracker_user_stats_sync,find_cross_event_bitmask_boxes,is_in_scheduled_macro_catalyst_window,parse_counting_slate_event,parse_gas_daily_bracket,poll_macro_catalyst_feeds_sync,walk_equal_shares_overround_bids,walk_position_overround_bid_unwind);from src.polymarket_research.uma_nba_endgame_engine import(LiveNbaGameState,evaluate_nba_endgame_locks,fetch_espn_nba_scoreboard_sync,is_objective_uma_market,match_nba_live_game,verify_uma_against_nba_live,verify_uma_onchain_proposal_sync);from src.polymarket_research.riskless_frontier_v2_engine import(BOP_2026_SLUGS,EsportsBo3Spec,NbaPlayerPropSlate,SoccerRegulationTree,build_lp1_bop_2026_truth_legs,build_lp1_nba_exact_margin_bundle,detect_nr2_convert_no_subset_arbs,detect_soc1_regulation_boxes,detect_sp4_milestone_ladder_boxes,evaluate_api1_esports_bo3_opportunities,evaluate_sp4_ingame_clinch_locks,fetch_espn_nba_boxscore_players_sync,find_state_matrix_dominance_boxes,link_and_parse_soccer_regulation_trees,parse_esports_bo3_event,parse_nba_player_props_from_event,verify_bond2_moov2_final_hour_sync,verify_negrisk_adapter_slate_sync);from src.polymarket_research.riskless_frontier_v3_engine import(LP2_MIDTERM_CORE_SLUGS,LP2_TOSSUP_CUBE_SLUG,LP2_TOSSUP_STATE_SLUGS,CalendarOrScalarLadderSpec,LiveMultiSportGame,NbaSubperiodAndExtPropSlate,ScoreConfirmationTracker,TennisMatchSpec,build_lp1_nfl_exact_margin_bundle,build_lp2_house_seats_truth_legs,build_lp2_pending_senate_conditional_groups,build_lp2_senate_seats_truth_legs,build_lp2_tossup_state_implication_groups,detect_cal1_monotonic_boxes,detect_lp2_seat_convert_implication_arbs,detect_multisport_ml_spread_polish_middles,detect_sp4_subperiod_and_ext_prop_boxes,evaluate_cl1_multisport_corridor_clinch_locks,evaluate_cl1_soccer_tree_clinch_locks,evaluate_sp4_subperiod_and_ext_locks,evaluate_ten1_tennis_opportunities,fetch_espn_multisport_board_sync,fetch_espn_nba_full_summary_sync,parse_cal1_monotonic_ladder_event,parse_nba_subperiod_and_ext_props,parse_tennis_retirement_safe_event,_teams_match_fuzzy);from src.polymarket_research.riskless_frontier_v4_engine import(FRONTIER_V4_GRAD8_SLEEVES,AffineGameBundle,CryptoCloseRungSpec,NflPlayerPropSlate,SoccerExactScoreLattice,SubperiodFreezeTracker,detect_cry_inc1_binance_inclusion_boxes,detect_nfl_prp1_boxes,detect_soc2_lattice_boxes_and_converts,detect_sum1_frechet_triangles,evaluate_aff1_frozen_subperiod_opportunities,evaluate_mkr_lock1_post_clinch_rebate_bid,evaluate_nfl_prp1_live_locks,evaluate_soc2_dead_score_no_locks,fetch_espn_nfl_summary_sync,link_and_parse_soc2_exact_score_lattices,parse_affine_game_bundle,parse_binance_terminal_close_event,parse_nfl_player_props_event);from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER;from src.polymarket_research.riskless_protocol_v2_expansion import(classify_market_rule_dispute_risk,compute_gatling_trajectory_projection,detect_b1_intraday_onetouch_noon_box,detect_d1_telescoping_candle_bridge,detect_dc1_double_chance_1x2_parity,detect_eq1_pyth_equity_dominance_box,detect_halftime_freeze_offset_box,detect_lp_comp1_sports_triangles,detect_mention1_cumulative_ladder_box,detect_nr_m1_dead_seed_fanout,detect_nr4_nr5_optimal_tail_convert,detect_nr6_cross_slate_surjection_box,detect_w_prune1_metar_slate_arb,evaluate_s2_rtds_exact_twap_integrator,passes_uma_bond_dispute_guard,safe_zoneinfo,scan_full_universe_c1_and_ctf_overround);DATA_DIR=PROJECT_ROOT/"data"/"alpha124";DATA_DIR.mkdir(parents=True,exist_ok=True);_DEFAULT_DATA_DIR=DATA_DIR;STATE_FILE=DATA_DIR/"alpha124_shadow_state.json";_DEFAULT_STATE_FILE=STATE_FILE;LEDGER_FILE=DATA_DIR/"alpha124_shadow_ledger.jsonl";_DEFAULT_LEDGER_FILE=LEDGER_FILE;MARKET_TELEMETRY_FILE=DATA_DIR/"alpha124_market_telemetry.jsonl";OPPS_FILE=DATA_DIR/"alpha124_live_opportunities.json";LOG_FILE=DATA_DIR/"alpha124_shadow.log";BACKTEST_CAL_FILE=DATA_DIR/"backtest_alpha_124_results.json";LIVE_POLYMARKET_DIR=PROJECT_ROOT/"data"/"polymarket";SHOCK_TRIGGER_FILE=LIVE_POLYMARKET_DIR/"live_shock_triggers.jsonl";LIVE_ALPHA124_STATE_MIRROR_FILE=LIVE_POLYMARKET_DIR/"alpha124_shadow_state.json";D1_LIVE_CANDIDATES_FILE=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl";logging.basicConfig(level=logging.INFO,format="[%(asctime)s UTC] [%(levelname)s] [ALPHA-124] %(message)s",datefmt="%Y-%m-%d %H:%M:%S",handlers=[logging.StreamHandler(sys.stdout)]);logger=logging.getLogger("Alpha124Shadow")
def _attach_daemon_log_file_handler():
 LOG_FILE.parent.mkdir(parents=True,exist_ok=True);b=logging.getLogger();a=str(LOG_FILE.resolve())
 for h in b.handlers:
  if isinstance(h,logging.FileHandler)and str(Path(h.baseFilename).resolve())==a:return
 c=logging.FileHandler(LOG_FILE,encoding="utf-8");c.setFormatter(logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [ALPHA-124] %(message)s",datefmt="%Y-%m-%d %H:%M:%S"));b.addHandler(c)
GAMMA_URL="https://gamma-api.polymarket.com";CLOB_URL="https://clob.polymarket.com";DATA_API_URL="https://data-api.polymarket.com";CLOB_WS_URL="wss://ws-subscriptions-clob.polymarket.com/ws/market";BINANCE_URL="https://api.binance.com";LOCKED_MAKER_SLEEVES=frozenset({"W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK","BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","SP2_NBA_ENDGAME_LOCK","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"});DEPTH_CAPPED_TAKER_SLEEVES=LOCKED_MAKER_SLEEVES|frozenset({"CM_B2_PYTH_SESSION_NO_LOCK","CM_U1_PYTH_CLOSE_LOCK","B4_TOUCHED_BARRIER_WICK_LOCK","TW1_COUNTING_TRUNCATION_AND_BOX","GAS1_AAA_GASOLINE_LOCK","API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","AFF1_FROZEN_SUBPERIOD_COLLAPSE","SOC2_EXACT_SCORE_2D_LATTICE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS"})
try:import orjson as _orjson
except Exception:_orjson=None
CRYPTO_FEE_RATE=.072;QUARANTINED_SHADOW_SLEEVES=frozenset({"M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","B1_CONVEX_TAIL_YES","B4_TOUCHED_BARRIER_WICK_LOCK","S2_EXACT_TWAP_LOCK","S5M_CHAINLINK_SNIPER","ZERO_FEE_MAKER_ANCHOR_BOX"});STRATEGY_EPOCH_MIN_TS={"S2_EXACT_TWAP_LOCK":1793758800.}
def _filter_epoch_closed_positions(sleeve,closed_list):
 a=STRATEGY_EPOCH_MIN_TS.get(str(sleeve))
 if not a:return closed_list
 return[p for p in closed_list if not(1.79e9<=float(p.get("entry_ts")or.0)<a)]
def is_shadow_sleeve_quarantined(sleeve):
 if sleeve=="S2_EXACT_TWAP_LOCK":
  if"PM_UNQUARANTINE_S2_TWAP_LOCK"in os.environ:return os.environ["PM_UNQUARANTINE_S2_TWAP_LOCK"]!="1"
  if"PM_QUARANTINE_LOSING_SLEEVES"in os.environ:return os.environ["PM_QUARANTINE_LOSING_SLEEVES"]=="1"
  return False
 if sleeve=="B4_TOUCHED_BARRIER_WICK_LOCK"and os.environ.get("PM_UNQUARANTINE_B4_WICK_LOCK")=="1":return False
 return os.getenv("PM_QUARANTINE_LOSING_SLEEVES","1")=="1"and sleeve in QUARANTINED_SHADOW_SLEEVES
FRONTIER_V3_GRAD8_SLEEVES=frozenset({"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR"});BANKROLL_TICKETS={"T100":{"W1_SOLAR_PEAK_LOCK":15.,"W2_ENSEMBLE_VALUE":10.,"W2_MAKER_OVERROUND":10.,"W3_WEATHER_SLATE_ARB":12.,"B1_CONVEX_TAIL_YES":4.,"B2_BARRIER_NO_LOCK":15.,"B3_BARRIER_MONO_BOX":18.,"M1_SVI_MAKER_SCALP":15.,"M2_STRIKE_CONVERGENCE":15.,"M3_LADDER_MONO_BOX":20.,"M4_SHOCK_STRIKE_CATCHUP":15.,"D1_SAME_ORACLE_DOMINANCE_BOX":20.,"D1_4H_DOMINANCE_BOX":20.,"D1_QUIET_BOOK_BOX":20.,"D1_MAKER_ANCHOR_BOX":18.,"S5M_CHAINLINK_SNIPER":15.,"N1_NEGRISK_CROSS_BOX":20.,"P1_PREOPEN_MAKER_STRADDLE":16.,"U1_DAILY_UPDOWN_LOCK":15.,"C1_BINARY_COMPLETE_SET":20.,"S2_EXACT_TWAP_LOCK":15.,"CM_B3_PYTH_BARRIER_BOX":20.,"CM_B2_PYTH_SESSION_NO_LOCK":15.,"CM_U1_PYTH_CLOSE_LOCK":15.,"B4_TOUCHED_BARRIER_WICK_LOCK":20.,"SP1_NBA_ZERO_FEE_BOX":20.,"NR0_ZERO_FEE_SLATE_ARB":15.,"ZERO_FEE_MAKER_ANCHOR_BOX":18.,"ZF_INTRADAY_MAKER_BOX":18.,"TW1_COUNTING_TRUNCATION_AND_BOX":18.,"FED1_CENTRAL_BANK_LP_BOX":20.,"COND1_MACRO_PARTITION_BOX":20.,"CTF_OVERROUND_MINT_SELL":20.,"D2_12PM_BINANCE_BOX":18.,"GAS1_AAA_GASOLINE_LOCK":15.,"CM_SHOCK_PYTH_CATALYST":15.,"S4H_CHAINLINK_CONVERGENCE":15.,"MKR_REWARD_LOCKED_CARRY":15.,"W1_LOW_TROUGH_LOCK":15.,"SP2_NBA_ENDGAME_LOCK":18.,"BOND1_UMA_RESOLUTION_CARRY":20.,"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX":20.,"NR_CONV_NO_BASKET_ARB":20.,"NR2_CONVERT_NO_SUBSET_ARB":20.,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":18.,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":20.,"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":20.,"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX":20.,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":18.,"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG":20.,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":18.,"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX":20.,"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX":20.,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":18.,"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR":18.,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":18.,"SOC2_EXACT_SCORE_2D_LATTICE":18.,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":18.,"SUM1_FRECHET_SUM_TRIANGLES":20.,"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION":20.,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":18.},"T1000":{"W1_SOLAR_PEAK_LOCK":1e2,"W2_ENSEMBLE_VALUE":50.,"W2_MAKER_OVERROUND":50.,"W3_WEATHER_SLATE_ARB":80.,"B1_CONVEX_TAIL_YES":25.,"B2_BARRIER_NO_LOCK":1e2,"B3_BARRIER_MONO_BOX":120.,"M1_SVI_MAKER_SCALP":1e2,"M2_STRIKE_CONVERGENCE":1e2,"M3_LADDER_MONO_BOX":150.,"M4_SHOCK_STRIKE_CATCHUP":1e2,"D1_SAME_ORACLE_DOMINANCE_BOX":1e2,"D1_4H_DOMINANCE_BOX":1e2,"D1_QUIET_BOOK_BOX":1e2,"D1_MAKER_ANCHOR_BOX":1e2,"S5M_CHAINLINK_SNIPER":1e2,"N1_NEGRISK_CROSS_BOX":150.,"P1_PREOPEN_MAKER_STRADDLE":96.,"U1_DAILY_UPDOWN_LOCK":1e2,"C1_BINARY_COMPLETE_SET":150.,"S2_EXACT_TWAP_LOCK":1e2,"CM_B3_PYTH_BARRIER_BOX":120.,"CM_B2_PYTH_SESSION_NO_LOCK":1e2,"CM_U1_PYTH_CLOSE_LOCK":1e2,"B4_TOUCHED_BARRIER_WICK_LOCK":120.,"SP1_NBA_ZERO_FEE_BOX":120.,"NR0_ZERO_FEE_SLATE_ARB":1e2,"ZERO_FEE_MAKER_ANCHOR_BOX":1e2,"ZF_INTRADAY_MAKER_BOX":110.,"TW1_COUNTING_TRUNCATION_AND_BOX":1e2,"FED1_CENTRAL_BANK_LP_BOX":120.,"COND1_MACRO_PARTITION_BOX":120.,"CTF_OVERROUND_MINT_SELL":120.,"D2_12PM_BINANCE_BOX":1e2,"GAS1_AAA_GASOLINE_LOCK":80.,"CM_SHOCK_PYTH_CATALYST":1e2,"S4H_CHAINLINK_CONVERGENCE":1e2,"MKR_REWARD_LOCKED_CARRY":1e2,"W1_LOW_TROUGH_LOCK":1e2,"SP2_NBA_ENDGAME_LOCK":1e2,"BOND1_UMA_RESOLUTION_CARRY":120.,"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX":120.,"NR_CONV_NO_BASKET_ARB":120.,"NR2_CONVERT_NO_SUBSET_ARB":120.,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":1e2,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":120.,"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":120.,"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX":120.,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":1e2,"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG":120.,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":1e2,"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX":120.,"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX":120.,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":1e2,"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR":1e2,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":110.,"SOC2_EXACT_SCORE_2D_LATTICE":110.,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":1e2,"SUM1_FRECHET_SUM_TRIANGLES":120.,"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION":120.,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":1e2},"T5000":{"W1_SOLAR_PEAK_LOCK":350.,"W2_ENSEMBLE_VALUE":175.,"W2_MAKER_OVERROUND":175.,"W3_WEATHER_SLATE_ARB":250.,"B1_CONVEX_TAIL_YES":75.,"B2_BARRIER_NO_LOCK":350.,"B3_BARRIER_MONO_BOX":4e2,"M1_SVI_MAKER_SCALP":350.,"M2_STRIKE_CONVERGENCE":350.,"M3_LADDER_MONO_BOX":5e2,"M4_SHOCK_STRIKE_CATCHUP":350.,"D1_SAME_ORACLE_DOMINANCE_BOX":3e2,"D1_4H_DOMINANCE_BOX":3e2,"D1_QUIET_BOOK_BOX":3e2,"D1_MAKER_ANCHOR_BOX":3e2,"S5M_CHAINLINK_SNIPER":3e2,"N1_NEGRISK_CROSS_BOX":5e2,"P1_PREOPEN_MAKER_STRADDLE":288.,"U1_DAILY_UPDOWN_LOCK":350.,"C1_BINARY_COMPLETE_SET":5e2,"S2_EXACT_TWAP_LOCK":3e2,"CM_B3_PYTH_BARRIER_BOX":4e2,"CM_B2_PYTH_SESSION_NO_LOCK":350.,"CM_U1_PYTH_CLOSE_LOCK":350.,"B4_TOUCHED_BARRIER_WICK_LOCK":4e2,"SP1_NBA_ZERO_FEE_BOX":4e2,"NR0_ZERO_FEE_SLATE_ARB":3e2,"ZERO_FEE_MAKER_ANCHOR_BOX":350.,"ZF_INTRADAY_MAKER_BOX":350.,"TW1_COUNTING_TRUNCATION_AND_BOX":350.,"FED1_CENTRAL_BANK_LP_BOX":4e2,"COND1_MACRO_PARTITION_BOX":4e2,"CTF_OVERROUND_MINT_SELL":4e2,"D2_12PM_BINANCE_BOX":3e2,"GAS1_AAA_GASOLINE_LOCK":250.,"CM_SHOCK_PYTH_CATALYST":3e2,"S4H_CHAINLINK_CONVERGENCE":3e2,"MKR_REWARD_LOCKED_CARRY":3e2,"W1_LOW_TROUGH_LOCK":350.,"SP2_NBA_ENDGAME_LOCK":350.,"BOND1_UMA_RESOLUTION_CARRY":4e2,"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX":4e2,"NR_CONV_NO_BASKET_ARB":4e2,"NR2_CONVERT_NO_SUBSET_ARB":4e2,"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK":350.,"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":4e2,"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":4e2,"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX":4e2,"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK":350.,"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG":4e2,"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION":350.,"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX":4e2,"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX":4e2,"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH":350.,"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR":350.,"AFF1_FROZEN_SUBPERIOD_COLLAPSE":350.,"SOC2_EXACT_SCORE_2D_LATTICE":350.,"NFL_PRP1_MILESTONE_AND_MAX_LOCKS":350.,"SUM1_FRECHET_SUM_TRIANGLES":4e2,"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION":4e2,"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":350.}}
for _v2_sl in("S2_RTDS_EXACT_TWAP_INTEGRATOR","D1_TELESCOPING_CANDLE_BRIDGE","B1_INTRADAY_ONETOUCH_NOON_BOX","EQ1_PYTH_EQUITY_DOMINANCE_BOX","DC1_DOUBLE_CHANCE_1X2_PARITY","LP_COMP1_SPORTS_TRIANGLES","HALFTIME_FREEZE_OFFSET_BOX","MENTION1_CUMULATIVE_LADDER_BOX","NR6_CROSS_SLATE_SURJECTION_BOX","NR4_EXHAUSTION_TAIL_YES_CONVERT","NR5_OVERROUND_ALL_YES_SELL","NR4_OPTIMAL_CHANNEL_CONVERT","NR5_LOTTERY_FREEROLL_CONVERT","CTF_OVERROUND_MINT_SELL","C1_BINARY_COMPLETE_SET","W_PRUNE1_METAR_SLATE_ARB","W_PRUNE1_NR0_BASKET","XV_SUBSET_NO_BOX","TAIL_BOUNDARY_001_ARB","BOND3_MULTISOURCE_DEAD_SPLIT","XV_FX_INVARIANT_CAD_USD_BOX","DERIBIT_VERTICAL_SUPER_REP","XV_HALFTIME_FREEZE_CORRIDOR","HEDGED_PRESPLIT_CONV_GUN","YIELD_STACKED_CARRY_BOX"):BANKROLL_TICKETS["T100"].setdefault(_v2_sl,20.);BANKROLL_TICKETS["T1000"].setdefault(_v2_sl,110.);BANKROLL_TICKETS["T5000"].setdefault(_v2_sl,350.)
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
 def __init__(b,single_scan=False,riskless_bridge_only=False):
  b.single_scan=single_scan;b.riskless_bridge_only=bool(riskless_bridge_only or os.environ.get("PM_RISKLESS_BRIDGE_ONLY")=="1");b.session=None;b.started_at=datetime.now(timezone.utc).isoformat();b.weather_sigma_c=1.05;b.barrier_wick_mult=1.12;b._load_calibration();b.spots={};b.spot_hist={a:collections.deque(maxlen=600)for a in(*DOMINANCE_ASSETS,*METAL_DOMINANCE_ASSETS)};b.usd_spot_hist={a:collections.deque(maxlen=400)for a in(*DOMINANCE_ASSETS,*METAL_DOMINANCE_ASSETS)};b.usd_direct_flags={};b.weather_events={};b.barrier_rungs={};b.strike_ladders={};b.negrisk_ladders={};b.daily_updown_markets={};b.pyth_daily_markets={};b.pyth_barrier_rungs={};b.pyth_close_ladders={};b.nba_games={};b.multi_sport_games={};b.negrisk_convert_slates={};b.live_nba_board=[];b.uma_proposed_markets={};b.uma_onchain_cache={};b.bond2_onchain_cache={};b.nba_prop_slates={};b.nba_boxscore_cache={};b.nba_subperiod_slates={};b.nba_ext_summary_cache={};b.soccer_trees={};b.lp1_bop_legs=[];b.lp1_nba_em_bundles={};b.esports_bo3_specs={};b.lp2_implication_groups=[];b.lp2_events_by_slug={};b.cal1_ladders={};b.lp1_nfl_em_bundles={};b.multisport_raw_events={};b.tennis_specs={};b.score_confirm_tracker=ScoreConfirmationTracker();b.live_multisport_boards={};b.aff1_bundles={};b.soc2_lattices={};b.nfl_prop_slates={};b.binance_close_rungs=[];b.subperiod_freeze_tracker=SubperiodFreezeTracker();b.nfl_summary_cache={};b.negrisk_zero_slates={};b.counting_slates={};b.fomc_truth_legs=[];b.zerofee_general_binaries=[];b.oil_senate_truth_legs=[];b.gas_events_raw={};b.hourly_12pm_markets={};b.s4h_candles={};b.pending_zero_fee_maker_anchors={};b.prev_pyth_spots={};b.pyth_intraday_cache={};b.dominance_pairs={};b.dominance_4h_pairs={};b.twap_candles={};b.s5m_candles={};b.preopen_15m_candles={};b.pending_preopen_straddles={};b.pending_maker_anchors={};b.chainlink_open_cache={};b.daily_open_cache={};b.metar_cache={};b.taf_cache={};b.ensemble_cache={};b.barrier_ext_cache={};b._last_w3_slate_chk_ts={};b._last_trade_tape_chk_ts={};b._open_meteo_sem=asyncio.Semaphore(2);b.last_discovery_ts=.0;b.last_weather_scan_ts=.0;b.last_crypto_mid_scan_ts=.0;b.last_tradfi_sports_scan_ts=.0;b.last_nba_endgame_scan_ts=.0;b.last_espn_board_ts=.0;b.last_uma_discovery_ts=.0;b.last_uma_bond_scan_ts=.0;b.last_dominance_discovery_ts=.0;b.last_4h_discovery_ts=.0;b.last_twap_discovery_ts=.0;b.last_s5m_discovery_ts=.0;b.last_preopen_discovery_ts=.0;b.last_usd_sample_ts=.0;b.cached_mid_opps=[];b.cached_weather_opps=[];b.cached_tradfi_sports_opps=[];b.cached_uma_bond_opps=[];b.cached_nba_endgame_opps=[];b.cached_shock_opps=[];b.cycle_count=0
  try:b._shock_file_offset=SHOCK_TRIGGER_FILE.stat().st_size if SHOCK_TRIGGER_FILE.exists()else 0
  except Exception:b._shock_file_offset=0
  b._seen_shock_ids=collections.deque(maxlen=256);b._last_m4_shock_ts_by_asset={};b._last_any_shock_ts_by_asset={};b._last_d1_live_emit_ts={};b._live_bridge_emits_total=0;b._live_bridge_emits_by_sleeve={};b._live_bridge_last_emit_ts=.0;b._bg_discovery_task=None;b._bg_weather_task=None;b._bg_mid_task=None;b._bg_tradfi_task=None;b._bg_uma_task=None;b._bg_nba_task=None;b._ws_books=_LazyWsBooksDict(b);b._ws_raw_levels={};b._ws_subscribed_tokens=set();b._ws_rest_seeded=set();b._ws_d1_priority_tokens=set();b._ws_nr_priority_tokens=set();b._ws_shard_tokens={};b._ws_shard_last_rx_ts={};b._ws_last_reconciled_ts={};b._rest_books_cache={};b._rest_empty_books_ts={};b._instant_arb_cooldown_until={};b._bg_chainlink_ws_task=None;b._chainlink_ws=(PolymarketChainlinkLiveStream(on_tick=b._on_chainlink_ws_tick)if(not b.single_scan and PolymarketChainlinkLiveStream is not None)else None);b._ws_d1_wakeup=asyncio.Event();b._ws_nr_wakeup=asyncio.Event();b._bg_clob_ws_task=None;b._strike_fail_backoff_ts={};b._last_telem_ts_by_key={};b._last_telem_sig_by_key={};b.open_positions={};b.pending_maker_orders={};b.closed_positions=[];b.entered_keys=set();b.inflight_keys=set();b.top_opportunities=[];b._hydrate_state()
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
    except Exception:pass
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
 @staticmethod
 def _release_unused_heap_memory():
  import gc as _gc;_gc.collect()
  if os.name!="nt":
   try:import ctypes;a=ctypes.CDLL("libc.so.6");return bool(a.malloc_trim(0))
   except Exception:return False
  return True
 @staticmethod
 def _slim_raw_gamma_event(ev):
  if not isinstance(ev,dict):return{}
  c={"description","image","icon","featuredImage","headerImage","tags","series","chats","cyom","templates","collections","categories","events"};b={"description","image","icon","twitterCardImage","events","categories","tags"};d={k:v for k,v in ev.items()if k not in c};a=ev.get("markets")
  if isinstance(a,list):d["markets"]=[{e:f for e,f in m.items()if e not in b}for m in a if isinstance(m,dict)]
  return d
 @staticmethod
 def _slim_rest_book(bk,max_levels=25):
  if not isinstance(bk,dict):return{}
  f=bk.get("bids");e=bk.get("asks");b=isinstance(f,list)and len(f)>max_levels;a=isinstance(e,list)and len(e)>max_levels
  if not b and not a:return bk
  i=dict(bk)
  if b:
   d=[]
   for r in f:
    if isinstance(r,dict):
     try:
      h=float(r.get("price",.0)or.0);g=float(r.get("size",.0)or.0)
      if h>.0 and g>.0:d.append((h,r))
     except Exception:continue
   d.sort(key=lambda kv:-kv[0]);i["bids"]=[r for _,r in d[:max_levels]]
  if a:
   c=[]
   for r in e:
    if isinstance(r,dict):
     try:
      h=float(r.get("price",.0)or.0);g=float(r.get("size",.0)or.0)
      if h>.0 and g>.0:c.append((h,r))
     except Exception:continue
   c.sort(key=lambda kv:kv[0]);i["asks"]=[r for _,r in c[:max_levels]]
  return i
 def _evict_stale_caches(a,now_ts=None):
  T=float(now_ts if now_ts is not None else time.time());c=0;b=0;m=set(a._ws_subscribed_tokens or())
  for p in(*a.open_positions.values(),*a.pending_maker_orders.values(),*a.pending_maker_anchors.values(),*a.pending_zero_fee_maker_anchors.values()):
   for M in("token_id","opp_token_id","anchor_token_id","hedge_token_id"):
    V=p.get(M)or(p.get("extra")or{}).get(M)
    if V:m.add(str(V))
  if m:
   for j in[t for t in list(a._ws_raw_levels.keys())if t not in m]:a._ws_raw_levels.pop(j,None);a._ws_books.pop(j,None);a._ws_rest_seeded.discard(j);a.__dict__.get("_ws_last_reconciled_ts",{}).pop(j,None);c+=1
   for j in[t for t in list(dict.keys(a._ws_books))if t not in m]:a._ws_books.pop(j,None);a._ws_rest_seeded.discard(j);a.__dict__.get("_ws_last_reconciled_ts",{}).pop(j,None);c+=1
  e=a.__dict__.get("_rest_books_cache")
  if isinstance(e,dict):
   for L,K in list(e.items()):
    if not isinstance(K,tuple)or(T-float(K[0]or.0))>120.:e.pop(L,None);b+=1
   if len(e)>1000:
    w=sorted(e.items(),key=lambda kv:float(kv[1][0]or.0)if isinstance(kv[1],tuple)and kv[1]else.0)
    for o,_ in w[:len(e)-1000]:e.pop(o,None);b+=1
  g=a.__dict__.get("_rest_empty_books_ts")
  if isinstance(g,dict):
   for J,C in list(g.items()):
    if(T-float(C or.0))>120.:g.pop(J,None);b+=1
  h=a.__dict__.get("_token_tick_boundary_ts")
  if isinstance(h,dict):
   for I,B in list(h.items()):
    if(T-float(B or.0))>1800. and I not in m:h.pop(I,None);b+=1
  l=a.__dict__.get("_token_tick_sizes")
  if isinstance(l,dict)and len(l)>2500:
   for H in list(l.keys()):
    if len(l)<=2500:break
    if H not in m and(not isinstance(h,dict)or H not in h):l.pop(H,None);b+=1
  f=a.__dict__.get("_ws_last_reconciled_ts")
  if isinstance(f,dict)and len(f)>2000:
   for G,A in list(f.items()):
    if G not in m and(T-float(A or.0))>6e2:f.pop(G,None);b+=1
  i=a.__dict__.get("_ws_dead_q_by_event")
  if isinstance(i,dict)and i:
   d=set((getattr(a,"negrisk_convert_slates",None)or{}).keys())
   for v in list(i.keys()):
    if v not in d:i.pop(v,None);b+=1
  for n,s in(("_zf_maker_cooldown_until",1800.),("_anti_box_warn_ts",3600.),("_strike_fail_log_ts",3600.)):
   r=a.__dict__.get(n)
   if isinstance(r,dict):
    for S,F in list(r.items()):
     if(T-float(F or.0))>s:r.pop(S,None);b+=1
  for z in(a.uma_onchain_cache,a.bond2_onchain_cache,a.nba_boxscore_cache,a.nba_ext_summary_cache,a.nfl_summary_cache,a.pyth_intraday_cache,a.metar_cache,a.taf_cache,a.ensemble_cache,a.barrier_ext_cache):
   for R,Q in list(z.items()):
    if isinstance(Q,tuple)and len(Q)>=1 and(T-float(Q[0]or.0))>3600.:z.pop(R,None);b+=1
  for y in(a.chainlink_open_cache,a.daily_open_cache):
   for P,O in list(y.items()):
    if isinstance(O,tuple)and len(O)>=1 and.0<float(O[0]or.0)<(T-7200.):y.pop(P,None);b+=1
  for u,q in((a._instant_arb_cooldown_until,6e2),(a._last_d1_live_emit_ts,3600.),(a._strike_fail_backoff_ts,3600.),(a._last_w3_slate_chk_ts,3600.),(a._last_trade_tape_chk_ts,3600.),(a._last_telem_ts_by_key,3600.)):
   for N,E in list(u.items()):
    if(T-float(E or.0))>q:u.pop(N,None);b+=1
  for x in list(a._last_telem_sig_by_key.keys()):
   if x not in a._last_telem_ts_by_key:a._last_telem_sig_by_key.pop(x,None)
  if len(a.entered_keys)>6000:
   k=set(a.open_positions.keys())|set(a.pending_maker_orders.keys())|set(a.pending_maker_anchors.keys())|set(a.pending_zero_fee_maker_anchors.keys())|set(a.inflight_keys)
   for D in a.closed_positions[-2500:]:
    for U in("dedupe_key","position_id","event_dedupe_key"):
     kv=D.get(U)or(D.get("extra")or{}).get(U)
     if kv:k.add(str(kv))
   a.entered_keys.intersection_update(k)
  a._release_unused_heap_memory();return{"evicted_books":c,"evicted_cache_entries":b}
 def _record_market_telemetry(a,key,min_interval_sec,payload,now_ts=None,sig=None,unchanged_heartbeat_sec=6e2):
  if getattr(a,"riskless_bridge_only",False):return
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
   d=json.loads(BACKTEST_CAL_FILE.read_text(encoding="utf-8"));e=d.get("option_1_weather",{}).get("calibrated_sigma_c");c=d.get("option_2_barrier_onetouch",{}).get("calibrated_wick_vol_mult")
   if e:a.weather_sigma_c=float(e)
   if c:a.barrier_wick_mult=float(c)
   logger.info(f"Loaded WFO calibration: weather_sigma_c={a.weather_sigma_c}, barrier_wick_mult={a.barrier_wick_mult}")
  except Exception as b:logger.warning(f"Calibration load notice: {b}")
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
 @staticmethod
 def _slim_closed_position_record(p):
  b={"position_id":p.get("position_id"),"dedupe_key":p.get("dedupe_key"),"sleeve":p.get("sleeve"),"asset_or_city":p.get("asset_or_city"),"status":p.get("status"),"entry_ts":p.get("entry_ts"),"closed_ts":p.get("closed_ts"),"entry_eff_px_t1000":p.get("entry_eff_px_t1000"),"won":p.get("won"),"tier_pnls_usd":p.get("tier_pnls_usd")or{}}
  if"legging_adjusted_tier_pnls_usd"in p:b["legging_adjusted_tier_pnls_usd"]=p.get("legging_adjusted_tier_pnls_usd")or{}
  c=p.get("extra")
  if isinstance(c,dict):
   a={k:c[k]for k in("event_id","event_dedupe_key")if c.get(k)}
   if a:b["extra"]=a
  return b
 def _hydrate_state(a):
  try:import orjson as _orjson;j=_orjson.loads
  except Exception:j=json.loads
  if STATE_FILE.exists():
   try:
    Q=j(STATE_FILE.read_bytes());a.started_at=Q.get("started_at",a.started_at)
    for p in Q.get("open_positions",[]):
     if isinstance(p,dict)and p.get("position_id")and not a._is_leaked_unit_test_artifact(p):
      a.open_positions[p["position_id"]]=p;a.entered_keys.add(str(p.get("dedupe_key")or p["position_id"]));b=(p.get("extra")or{}).get("event_id")
      if b:
       if p.get("sleeve")=="W2_ENSEMBLE_VALUE":a.entered_keys.add(f"W2_EVENT_{b}")
       elif p.get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.add(f"W2M_EVENT_{b}")
    for K in Q.get("pending_maker_orders",[]):
     if isinstance(K,dict)and K.get("order_id")and not a._is_leaked_unit_test_artifact(K):
      a.pending_maker_orders[K["order_id"]]=K
      if K.get("dedupe_key"):a.entered_keys.add(str(K["dedupe_key"]))
      b=(K.get("extra")or{}).get("event_id")
      if b and K.get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.add(f"W2M_EVENT_{b}")
    for p in Q.get("recent_closed_positions",[]):
     if isinstance(p,dict)and not a._is_leaked_unit_test_artifact(p):
      a.closed_positions.append(p)
      if p.get("dedupe_key"):a.entered_keys.add(str(p["dedupe_key"]))
      b=(p.get("extra")or{}).get("event_id")
      if b:
       if p.get("sleeve")=="W2_ENSEMBLE_VALUE":a.entered_keys.add(f"W2_EVENT_{b}")
       elif p.get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.add(f"W2M_EVENT_{b}")
   except Exception as g:logger.warning(f"State hydrate notice: {g}")
  n=a._resolve_ledger_path();c=set()
  if n.exists():
   try:
    d={str(p.get("position_id"))for p in a.closed_positions if isinstance(p,dict)and p.get("position_id")}
    with open(n,"rb")as A:
     for h in A:
      if b"SHADOW_CLOSE"in h:
       try:L=j(h)
       except Exception:continue
       if isinstance(L,dict)and L.get("event")=="SHADOW_CLOSE"and L.get("position_id"):d.add(str(L["position_id"]))
      elif b"SHADOW_MAKER_CANCEL"in h:
       try:L=j(h)
       except Exception:continue
       if isinstance(L,dict)and L.get("event")=="SHADOW_MAKER_CANCEL"and L.get("order_id"):c.add(str(L["order_id"]))
    m={};i={};o={str(p.get("position_id"))for p in a.closed_positions if isinstance(p,dict)and p.get("position_id")};f=collections.deque(maxlen=4000);e=collections.deque(maxlen=50)
    for z in a.closed_positions:e.append(z)
    with open(n,"rb")as P:
     for h in P:
      if not h.strip():continue
      try:r=j(h)
      except Exception:continue
      if not isinstance(r,dict)or a._is_leaked_unit_test_artifact(r):continue
      O=r.get("event")
      if O in("SHADOW_ENTRY","SHADOW_CLOSE")and r.get("dedupe_key"):f.append(str(r["dedupe_key"]))
      if O=="SHADOW_ENTRY":
       s=str(r.get("position_id")or"");J=str(r.get("dedupe_key")or"")
       if J and i:
        for I,N in list(i.items()):
         if str(N.get("dedupe_key")or"")==J:i.pop(I,None)
       b=(r.get("extra")or{}).get("event_id")
       if b:
        if r.get("sleeve")=="W2_ENSEMBLE_VALUE":f.append(f"W2_EVENT_{b}")
        elif r.get("sleeve")=="W2_MAKER_OVERROUND":f.append(f"W2M_EVENT_{b}")
       if s and s not in d:m[s]={k:v for k,v in r.items()if k!="event"}
      elif O=="SHADOW_CLOSE":
       s=str(r.get("position_id")or"")
       if s:
        m.pop(s,None);a.open_positions.pop(s,None)
        if s not in o:o.add(s);u={k:v for k,v in r.items()if k!="event"};t=a._slim_closed_position_record(u);e.append(u);a.closed_positions.append(t)
      elif O=="SHADOW_MAKER_POST":
       q=str(r.get("order_id")or"")
       if q and q not in c:
        i[q]={k:v for k,v in r.items()if k!="event"}
        if r.get("dedupe_key"):f.append(str(r["dedupe_key"]))
        b=(r.get("extra")or{}).get("event_id")
        if b and r.get("sleeve")=="W2_MAKER_OVERROUND":f.append(f"W2M_EVENT_{b}")
      elif O=="SHADOW_MAKER_CANCEL":
       q=str(r.get("order_id")or"")
       if q:
        H=i.pop(q,None);a.pending_maker_orders.pop(q,None)
        if H and H.get("dedupe_key"):a.entered_keys.discard(str(H["dedupe_key"]))
        b=((H or r).get("extra")or{}).get("event_id")
        if b and(H or r).get("sleeve")=="W2_MAKER_OVERROUND":a.entered_keys.discard(f"W2M_EVENT_{b}")
    a.entered_keys.update(f);l={}
    for y in e:
     y.pop("_slim_shadow_ref",None);G=str(y.get("position_id")or"")
     if G:l[G]=y
    if l:
     for F,E in enumerate(a.closed_positions):
      D=str(E.get("position_id")or"")
      if D in l:a.closed_positions[F]=l[D]
    for s,x in m.items():
     if s not in a.open_positions and s not in o:a.open_positions[s]=x
    for q,C in i.items():
     if q not in a.pending_maker_orders or float(C.get("last_repeg_ts")or.0)>float(a.pending_maker_orders[q].get("last_repeg_ts")or.0):a.pending_maker_orders[q]=C
   except Exception as g:logger.warning(f"Ledger hydrate notice: {g}")
  if a.closed_positions:
   a.closed_positions.sort(key=lambda p:float(p.get("closed_ts")or.0))
   if len(a.closed_positions)>50:
    for w in range(len(a.closed_positions)-50):
     if"title"in a.closed_positions[w]or"tier_fills"in a.closed_positions[w]:a.closed_positions[w]=a._slim_closed_position_record(a.closed_positions[w])
  for B,M in list(a.pending_maker_orders.items()):
   if is_shadow_sleeve_quarantined(str(M.get("sleeve")or"")):
    a.pending_maker_orders.pop(B,None)
    if B not in c:a._append_ledger({"event":"SHADOW_MAKER_CANCEL","reason":"SLEEVE_QUARANTINED",**M})
  if is_shadow_sleeve_quarantined("P1_PREOPEN_MAKER_STRADDLE"):a.pending_preopen_straddles.clear()
  if is_shadow_sleeve_quarantined("ZERO_FEE_MAKER_ANCHOR_BOX"):a.pending_zero_fee_maker_anchors.clear()
  import gc as _gc;_gc.collect()
 def _append_ledger(self,rec):
  a=self._resolve_ledger_path();a.parent.mkdir(parents=True,exist_ok=True)
  with open(a,"a",encoding="utf-8")as f:f.write(json.dumps(rec)+"\n")
 async def get_session(a):
  if a.session is None or a.session.closed:a.session=aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=24,enable_cleanup_closed=True),headers={"User-Agent":"DominusAlpha124Shadow/1.0","Accept":"application/json"},max_line_size=65536,max_field_size=65536)
  return a.session
 def _on_chainlink_ws_tick(a,asset,ts_sec,price_usd):
  if price_usd<=.0 or not math.isfinite(price_usd):return
  a.spots[asset]=price_usd;a.usd_direct_flags[asset]=True;b=a.usd_spot_hist.get(asset)
  if b is None:b=collections.deque(maxlen=450);a.usd_spot_hist[asset]=b
  if b and abs(ts_sec-float(b[-1][0]))<.05:b[-1]=(ts_sec,price_usd)
  elif b and ts_sec<float(b[-1][0]):return
  else:b.append((ts_sec,price_usd))
 async def fetch_json(a,url,timeout=5.):
  c=(not a.single_scan)and("/book?token_id="in str(url));e=""
  if c:
   e=str(url).split("token_id=",1)[1].split("&",1)[0].strip();l=time.time()
   if a._ws_books:
    k=a._ws_books.get(e)
    if k is not None and((l-k[0])<=1.5 or a._is_ws_book_live_on_healthy_shard(e,k[0],l,max_shard_silence_sec=5.)):
     n=k[1]
     if n.get("asks")or n.get("bids"):return n
   d=getattr(a,"_ws_subscribed_tokens",None)or set();j=12. if e in d else 45.;i=(a.__dict__.get("_rest_books_cache")or{}).get(e)
   if i is not None and(l-float(i[0]))<=j:
    m=i[1]
    if isinstance(m,dict)and(m.get("asks")or m.get("bids")):return m
   h=(a.__dict__.get("_rest_empty_books_ts")or{}).get(e)
   if h is not None and(l-float(h))<=(20. if e in d else 90.):return None
  o=await a.get_session()
  if c:
   b=a.__dict__.get("_book_get_sem")
   if b is None:b=asyncio.Semaphore(4);a.__dict__["_book_get_sem"]=b
   async with b:
    try:
     async with o.get(url,timeout=aiohttp.ClientTimeout(total=timeout))as f:
      if f.status==200:
       g=await f.json()
       if isinstance(g,dict)and e:a.__dict__.setdefault("_rest_books_cache",{})[e]=(time.time(),g);a.__dict__.setdefault("_rest_empty_books_ts",{}).pop(e,None)
       return g
      if f.status==404 and e:a.__dict__.setdefault("_rest_empty_books_ts",{})[e]=time.time()
    except Exception:return None
    return None
  try:
   async with o.get(url,timeout=aiohttp.ClientTimeout(total=timeout))as f:
    if f.status==200:return await f.json()
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
    g=round(float(d.get("price",.0)),4);f=float(d.get("size",.0))
    if g>.0 and f>.0:c[g]=f
   except Exception:continue
  for d in asks_raw or():
   try:
    g=round(float(d.get("price",.0)),4);f=float(d.get("size",.0))
    if g>.0 and f>.0:b[g]=f
   except Exception:continue
  a._ws_raw_levels[asset_id]=(c,b);a._rebuild_ws_book_dict(asset_id,c,b,now_ts)
  if from_rest:a._ws_rest_seeded.add(asset_id)
  else:
   a._ws_rest_seeded.discard(asset_id);a.__dict__.setdefault("_ws_last_reconciled_ts",{})[asset_id]=now_ts
   if _STAGE_B_DECAY_TRACKER is not None and not a.single_scan:e=min(b.keys())if b else.0;_STAGE_B_DECAY_TRACKER.on_top_of_book_tick(asset_id,e,b.get(e,.0)if e>.0 else.0)
 def _drop_ws_book(a,asset_id):a._ws_books.pop(asset_id,None);a._ws_raw_levels.pop(asset_id,None);a._ws_rest_seeded.discard(asset_id);a.__dict__.get("_ws_last_reconciled_ts",{}).pop(asset_id,None)
 def _apply_ws_price_changes(a,asset_id,changes,now_ts):
  n=a._ws_raw_levels.get(asset_id)
  if n is None:return False
  k,j=n;c=False
  for l in changes or():
   try:
    p=round(float(l.get("price",.0)),4);o=float(l.get("size",.0));m=str(l.get("side")or"").upper()
    if p<=.0:continue
    i=k if m=="BUY"else j
    if o<=.0:
     if p in i:i.pop(p,None);c=True
    else:i[p]=o;c=True
   except Exception:continue
  h=max(k.keys())if k else.0;g=min(j.keys())if j else.0;b=bool(k and j and h>=g)
  if not b:
   e=None;d=None
   for l in changes or():
    try:
     if l.get("best_bid")not in(None,""):e=float(l.get("best_bid"))
     if l.get("best_ask")not in(None,""):d=float(l.get("best_ask"))
    except Exception:continue
   if e is not None and.0<e<1. and abs(e-h)>1e-6:b=True
   if d is not None and.0<d<1. and abs(d-g)>1e-6:b=True
  if b:a._drop_ws_book(asset_id);return False
  if c:
   if len(k)>80:
    for f in sorted(k.keys(),reverse=True)[50:]:k.pop(f,None)
   if len(j)>80:
    for f in sorted(j.keys())[50:]:j.pop(f,None)
   a.__dict__.setdefault("_ws_last_reconciled_ts",{})[asset_id]=now_ts
   if isinstance(a._ws_books,_LazyWsBooksDict):a._ws_books.mark_dirty(asset_id,now_ts)
   else:a._rebuild_ws_book_dict(asset_id,k,j,now_ts)
   if _STAGE_B_DECAY_TRACKER is not None and not a.single_scan:_STAGE_B_DECAY_TRACKER.on_top_of_book_tick(asset_id,g,j.get(g,.0)if g>.0 else.0)
  return c
 def _load_dormant_priority_ws_tokens(a,now_ts,max_bps=50.,max_tokens=800):
  d=a.__dict__.get("_dormant_opps_path")
  if d is not None:b=Path(d)
  elif a.single_scan or("fetch_json"in a.__dict__):return[]
  else:b=PROJECT_ROOT/"data"/"full_throttle"/"pipeline"/"dormant_opportunities.json"
  h=a.__dict__.get("_dormant_ws_cache")
  if isinstance(h,tuple)and len(h)==3 and(now_ts-float(h[0]))<45.:return list(h[2][:max_tokens])
  try:
   if not b.is_file():a.__dict__["_dormant_ws_cache"]=(now_ts,0,[]);return[]
   o=int(b.stat().st_mtime_ns)
   if isinstance(h,tuple)and len(h)==3 and int(h[1])==o:a.__dict__["_dormant_ws_cache"]=(now_ts,o,h[2]);return list(h[2][:max_tokens])
   l=b.read_bytes();s=_orjson.loads(l)if _orjson is not None else json.loads(l.decode("utf-8"));e=s.get("entries")if isinstance(s,dict)else(s if isinstance(s,list)else[]);n=[]
   for q in(e or()):
    if not isinstance(q,dict):continue
    g={str(x).strip()for x in(q.get("market_ids")or())if x}
    if g&{"6707502","6707503"}:continue
    k=q.get("gap_to_breakeven_bps",q.get("distance_to_breakeven_bps",q.get("best_gap_to_breakeven_bps",9999.)));j=float(k if k is not None else 9999.)
    if j<=float(max_bps):
     i=0 if str(q.get("family_code")or"A").strip().upper()!="A"else 1;c=[str(t).strip()for t in(q.get("instrument_ids")or q.get("token_ids")or())if str(t or"").strip()]
     if c:n.append((i,j,c))
   n.sort(key=lambda r:(r[0],r[1]));m=[];f=set()
   for _,_,c in n:
    for p in c:
     if p not in f:
      f.add(p);m.append(p)
      if len(m)>=1400:break
    if len(m)>=1400:break
   a.__dict__["_dormant_ws_cache"]=(now_ts,o,m);return m[:max_tokens]
  except Exception:return[]
 def _desired_d1_ws_tokens(c,now_ts,max_cap=1250):
  I=[];D=set();k=set()
  def a(tok,*,is_nr=False):
   if len(I)>=max_cap:return False
   b=str(tok or"").strip()
   if b and b not in D:
    D.add(b);I.append(b)
    if is_nr:k.add(b)
   elif b and is_nr:k.add(b)
   return len(I)<max_cap
  for p,j in list(c.dominance_pairs.values())+list(c.dominance_4h_pairs.values()):
   if float(j.end_ts)<=now_ts+5.:continue
   for tok in(p.up_token,p.down_token,j.up_token,j.down_token):a(tok)
  if not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK"):
   for x in list(c.twap_candles.values()):
    if float(x.end_ts)>now_ts+5.:a(x.up_token);a(x.down_token)
  c._ws_d1_priority_tokens=set(I)
  for C in list(c.pyth_daily_markets.values())+list(c.daily_updown_markets.values()):
   if float(C.end_ts)>now_ts+60.:a(C.up_token);a(C.down_token)
  for w in list(c.strike_ladders.values()):
   if not w or float(w[0].end_ts)<=now_ts+60.:continue
   o=float(c.spots.get(w[0].asset)or.0);h=sorted(w,key=lambda r:abs(float(r.strike)-o))if o>.0 else list(w)
   for r in h[:4]:a(r.yes_token);a(r.no_token)
  for H in list(c.negrisk_ladders.values()):
   if not H or float(H[0].end_ts)<=now_ts+60.:continue
   n=float(c.spots.get(H[0].asset)or.0);g=sorted(H,key=lambda b:abs(.5*(float(b.k_low or n)+float(b.k_high or n))-n))if n>.0 else list(H)
   for b in g[:4]:a(b.yes_token);a(b.no_token)
  def d(br,attr):return br.get(attr)if isinstance(br,dict)else getattr(br,attr,None)
  for v in sorted(list(c.negrisk_zero_slates.values()),key=lambda s:float(s.end_ts)):
   if float(v.end_ts)<=now_ts+60. or len(v.brackets)>15:continue
   for G in v.brackets:a(d(G,"no_token"),is_nr=True);a(d(G,"yes_token"),is_nr=True)
  for m in sorted(list(c.negrisk_convert_slates.values()),key=lambda s:(not bool(s.is_closed_convert_safe),float(s.end_ts))):
   if float(m.end_ts)<=now_ts+60. or len(m.brackets)>15:continue
   for F in m.brackets:
    a(d(F,"no_token"),is_nr=True)
    if m.is_closed_convert_safe:a(d(F,"yes_token"),is_nr=True)
  for u in sorted(list(c.counting_slates.values()),key=lambda s:float(getattr(s,"window_end_ts",None)or getattr(s,"end_ts",.0)or.0)):
   if float(getattr(u,"window_end_ts",None)or getattr(u,"end_ts",.0)or.0)<=now_ts+60. or len(u.brackets)>15:continue
   for E in u.brackets:a(d(E,"no_token"),is_nr=True);a(d(E,"yes_token"),is_nr=True)
  for t in list(c.uma_proposed_markets.values())[:150]:
   if isinstance(t,dict):
    i=_parse_clob_tokens(t)
    if i:a(i[0],is_nr=True);a(i[1],is_nr=True)
    else:a(t.get("win_token")or t.get("yes_token"),is_nr=True);a(t.get("lose_token")or t.get("no_token"),is_nr=True)
  for B in sorted((c.__dict__.get("_ws_reactive_bin_metas")or()),key=lambda J:float(J.get("end_ts")or(now_ts+86400.)))[:160]:
   if float(B.get("end_ts")or(now_ts+86400.))>now_ts+60.:a(B.get("yes_token_id"),is_nr=True);a(B.get("no_token_id"),is_nr=True)
  e=c._load_dormant_priority_ws_tokens(now_ts,max_bps=50.,max_tokens=max_cap)
  for A in e[:400]:a(A,is_nr=True)
  for z in list(c.multi_sport_games.values())+list(c.nba_games.values()):
   q=float(getattr(z,"end_ts",.0)or.0)
   if 60.<(q-now_ts)<=21600.:
    for l in("ml_a_token","ml_b_token"):a(getattr(z,l,None))
    for y in(getattr(z,"spreads",None)or())[:3]:
     if isinstance(y,dict):a(y.get("yes_token"));a(y.get("no_token"))
  for f in e[400:]:
   if not a(f,is_nr=True):break
  c._ws_nr_priority_tokens=k;return I
 def _partition_ws_shards(self,now_ts,max_shards=5,per_shard=250):a=self._desired_d1_ws_tokens(now_ts,max_cap=max_shards*per_shard);return[a[i*per_shard:(i+1)*per_shard]for i in range(max_shards)]
 def _sync_ws_subscribed_union(a):
  b=set()
  for c in a._ws_shard_tokens.values():b.update(c)
  a._ws_subscribed_tokens=b
 async def _run_single_clob_ws_shard(a,shard_idx):
  j=a.__dict__.setdefault("_ws_shard_last_rx_ts",{})
  while not a.single_scan:
   t=a._partition_ws_shards(time.time());q=t[shard_idx]if shard_idx<len(t)else[]
   if not q:
    j.pop(shard_idx,None)
    for m in list(a._ws_shard_tokens.pop(shard_idx,set())):a._drop_ws_book(m)
    a._sync_ws_subscribed_union();await asyncio.sleep(1.5);continue
   try:
    E=await a.get_session()
    async with E.ws_connect(CLOB_WS_URL,heartbeat=15.,max_msg_size=4*1024*1024,timeout=aiohttp.ClientWSTimeout(ws_close=5.))as J:
     n=a._ws_shard_tokens.get(shard_idx,set())
     for m in list(n|set(q)):a._drop_ws_book(m)
     p=set(q);a._ws_shard_tokens[shard_idx]=p;a._sync_ws_subscribed_union();await J.send_str(json.dumps({"assets_ids":q,"type":"market"}));e=time.time();b=e;j[shard_idx]=b
     while not a.single_scan:
      y=time.time()
      if(y-e)>=2.:
       e=y;s=a._partition_ws_shards(y);f=set(s[shard_idx]if shard_idx<len(s)else[]);l=set()
       for x,r in a._ws_shard_tokens.items():
        if x!=shard_idx:l.update(r)
       f-=l
       for o in list(p-f):
        p.discard(o)
        if o not in l:a._drop_ws_book(o)
       a._sync_ws_subscribed_union()
       if not f:break
       w=sorted(f-p)
       if w:await J.send_str(json.dumps({"assets_ids":w,"operation":"subscribe"}));p.update(w);a._sync_ws_subscribed_union()
       elif len(p)>len(f)+32:break
      if(y-b)>30.:break
      try:H=await asyncio.wait_for(J.receive(),timeout=2.)
      except asyncio.TimeoutError:continue
      if H.type in(aiohttp.WSMsgType.CLOSED,aiohttp.WSMsgType.CLOSING,aiohttp.WSMsgType.ERROR):break
      if H.type not in(aiohttp.WSMsgType.TEXT,aiohttp.WSMsgType.BINARY):continue
      k=H.data
      if not k or k in("PONG",b"PONG"):b=time.time();j[shard_idx]=b;continue
      v=time.time();b=v;j[shard_idx]=v;D=_orjson.loads(k)if _orjson is not None else json.loads(k);d=False;c=False;i=a._ws_d1_priority_tokens;h=a._ws_nr_priority_tokens
      if isinstance(D,list):
       for C in D:
        if isinstance(C,dict):
         g=str(C.get("asset_id")or"")
         if g in p:
          B=C.get("tick_size")or C.get("minimum_tick_size")
          if B:a.__dict__.setdefault("_token_tick_sizes",{})[g]=str(B)
          a._apply_ws_book_snapshot(g,C.get("bids")or[],C.get("asks")or[],v);d=d or(g in i);c=c or(g in h)
      elif isinstance(D,dict):
       A=D.get("event_type")
       if A=="book":
        g=str(D.get("asset_id")or"")
        if g in p:
         z=D.get("tick_size")or D.get("minimum_tick_size")
         if z:a.__dict__.setdefault("_token_tick_sizes",{})[g]=str(z)
         a._apply_ws_book_snapshot(g,D.get("bids")or[],D.get("asks")or[],v);d=d or(g in i);c=c or(g in h)
       elif A=="tick_size_change":
        g=str(D.get("asset_id")or"");G=D.get("new_tick_size")or D.get("tick_size")
        if g and G:
         a.__dict__.setdefault("_token_tick_sizes",{})[g]=str(G)
         if g in a._ws_books and isinstance(a._ws_books[g][1],dict):a._ws_books[g][1]["minimum_tick_size"]=str(G)
       elif A=="price_change":
        u={}
        for I in D.get("price_changes")or():
         g=str(I.get("asset_id")or"")
         if g in p:u.setdefault(g,[]).append(I)
        for g,F in u.items():
         if a._apply_ws_price_changes(g,F,v):
          if g in i:d=True
          if g in h:c=True
      if(d and(a.is_in_same_oracle_overlap_window(v)or bool(a.pending_maker_anchors))and(v-getattr(a,"_last_ws_d1_wake_ts",.0))>=.12):a._last_ws_d1_wake_ts=v;a._ws_d1_wakeup.set()
      if c and(v-getattr(a,"_last_ws_nr_wake_ts",.0))>=.12:a._last_ws_nr_wake_ts=v;a._ws_nr_wakeup.set();a._ws_d1_wakeup.set()
   except asyncio.CancelledError:j.pop(shard_idx,None);raise
   except Exception:j.pop(shard_idx,None);await asyncio.sleep(1.)
   finally:j.pop(shard_idx,None)
 async def _scan_ws_reactive_negrisk_arbs(a,now_ts):
  from src.polymarket_research.riskless_machine_gun_engine import detect_nr3_synthetic_all_yes_overround as c;from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as d;o=[];v=d.snapshot.get("riskless_boxes",{});f=a.__dict__.get("_ws_dead_q_by_event")or{}
  for u in list(a.negrisk_convert_slates.values()):
   if not u.is_closed_convert_safe or u.end_ts<=now_ts+65. or len(u.brackets)>15:continue
   t={};e=True
   for N in u.brackets:
    for J in(N.get("no_token"),N.get("yes_token")):
     A=str(J or"");s=a._ws_books.get(A)if A else None
     if(s is None or A in a._ws_rest_seeded or((now_ts-float(s[0]))>2.5 and not a._is_ws_book_live_on_healthy_shard(A,float(s[0]),now_ts,max_shard_silence_sec=5.))):e=False;break
     t[A]=s[1]
    if not e:break
   if not e:continue
   l=detect_negrisk_convert_positions_arbs(u,t,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],min_net_edge_per_share=.005,min_shares=8)
   if l:await a.execute_negrisk_convert_positions_arb(u,l[0],t,o)
   k=(all(float(b.get("fee_rate",.0)or.0)<=1e-9 for b in u.brackets)and(u.end_ts-now_ts)<=172800.);n=detect_nr2_convert_no_subset_arbs(u,t,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR2_CONVERT_NO_SUBSET_ARB"],min_edge_pure_cash=.006 if k else.012,min_edge_with_yes_sell=.0085 if k else.015,min_shares=5 if k else 6)
   if n:await a.execute_nr2_subset_convert_arb(u,n[0],t,o)
   p=c(u,t,target_budget_usd=30.,min_net_edge_per_set=.008,min_shares=5)
   if p is not None:a.emit_live_negrisk_convert_candidate(sleeve_source="NR2_CONVERT_NO_SUBSET_ARB",spec=u,dedupe_key=f"NR3_OVR_{u.event_id}",arb_hit=p,books_by_token=t,now_ts=now_ts)
   r=f.get(u.event_id)
   if r and bool(v.get("enable_nr_m1_dead_seed_fanout",True)):
    z=detect_nr_m1_dead_seed_fanout(u,r,t,fee_bips=int(getattr(u,"fee_bips",0)or 0),min_shares=5.,min_net_edge_usd=.0035)
    if z is not None:a.emit_live_negrisk_convert_candidate(sleeve_source="W_PRUNE1_DEAD_NO_BOND",spec=u,dedupe_key=f"NRM1_WS_{u.event_id}_Q{z['dead_question_index']}",arb_hit=z,books_by_token=t,now_ts=now_ts,fee_bips=int(getattr(u,"fee_bips",0)or 0))
  j=a.__dict__.get("_ws_reactive_bin_metas")or()
  if j and bool(v.get("enable_zerofee1_mergeable_sweeper",True)):
   g=max(.001,float(v.get("zerofee1_min_net_edge_bps",15.)or 15.)/1e4);i=round(1.-g,4);m=[]
   for M in j:
    if float(M.get("end_ts")or(now_ts+86400.))<=now_ts+65.:continue
    L=a._get_fresh_ws_book(str(M["yes_token_id"]),now_ts,max_age_sec=2.5);K=a._get_fresh_ws_book(str(M["no_token_id"]),now_ts,max_age_sec=2.5)
    if L and K:I,H=extract_best_bid(L.get("bids")or[]);G,F=extract_best_bid(K.get("bids")or[]);E,D=a._best_ask_sz(L);C,B=a._best_ask_sz(K);m.append({**M,"yes_bid":I,"yes_bid_size":(H/I)if I>0 else.0,"no_bid":G,"no_bid_size":(F/G)if G>0 else.0,"yes_ask":E if E<1. else.0,"yes_ask_size":D,"no_ask":C if C<1. else.0,"no_ask_size":B,"bk_yes":L,"bk_no":K})
   if m:
    h={x["condition_id"]:x for x in m}
    for y in scan_full_universe_c1_and_ctf_overround(m,min_underround_edge=g,min_overround_edge=.0045):
     w=h.get(str(y.get("condition_id")or""))
     if not w:continue
     if y.get("sleeve")=="C1_BINARY_COMPLETE_SET"and float(y["cost_per_share"])<=i+1e-6:a.emit_live_two_leg_box_candidate(box_type="COMPLETE_SET",sleeve_source="C1_BINARY_COMPLETE_SET",asset=w["asset"],dedupe_key=f"C1V2_{w['market_id']}",leg_a={"token_id":w["yes_token_id"],"opp_token_id":w["no_token_id"],"label":"YES","side":"YES","market_id":w["market_id"],"condition_id":w["condition_id"],"fee_rate":w["fee_rate"],"fee_exponent":w["fee_exponent"],"neg_risk":w["neg_risk"],"end_ts":w["end_ts"]},leg_b={"token_id":w["no_token_id"],"opp_token_id":w["yes_token_id"],"label":"NO","side":"NO","market_id":w["market_id"],"condition_id":w["condition_id"],"fee_rate":w["fee_rate"],"fee_exponent":w["fee_exponent"],"neg_risk":w["neg_risk"],"end_ts":w["end_ts"]},bk_a=w["bk_yes"],bk_b=w["bk_no"],close_ts=w["end_ts"],now_ts=now_ts,max_box_cost_override=i)
     elif y.get("sleeve")=="CTF_OVERROUND_MINT_SELL"and not w["neg_risk"]:q=float(y.get("net_revenue_per_share")or y.get("net_proceeds_per_share")or 1.005);a.emit_live_special_v2_box_candidate(box_type="CTF_OVERROUND",sleeve_source="CTF_OVERROUND_MINT_SELL",asset=w["asset"],dedupe_key=f"CTFOVR_{w['market_id']}_{int(now_ts//15)}",close_ts=w["end_ts"],now_ts=now_ts,payload={"condition_id":w["condition_id"],"leg_a_market_id":w["market_id"],"yes_token_id":w["yes_token_id"],"no_token_id":w["no_token_id"],"yes_bid":y["yes_bid"],"no_bid":y["no_bid"],"fee_rate":w["fee_rate"],"fee_exponent":w["fee_exponent"],"max_fillable_shares":y["max_fillable_shares"],"box_cost_net":round(2.-q,4)})
 async def _run_clob_d1_ws_loop(a):
  if a.single_scan:return
  await asyncio.gather(*(a._run_single_clob_ws_shard(b)for b in range(5)))
 def _is_ws_book_live_on_healthy_shard(a,token_id,book_ts,now_ts,max_shard_silence_sec=5.,max_quiet_book_age_sec=120.):
  if not token_id or getattr(a,"single_scan",False):return False
  if token_id in getattr(a,"_ws_rest_seeded",set()):return False
  c=a.__dict__.get("_ws_shard_tokens");e=a.__dict__.get("_ws_shard_last_rx_ts")
  if not c or not e:return False
  b=float((a.__dict__.get("_ws_last_reconciled_ts")or{}).get(token_id,.0)or.0);d=max(float(book_ts),b)
  if(float(now_ts)-d)>float(max_quiet_book_age_sec):return False
  for g,f in c.items():
   if token_id in f:
    h=float(e.get(g,.0)or.0)
    if h>.0 and(float(now_ts)-h)<=float(max_shard_silence_sec):return True
  return False
 def _get_fresh_ws_book(a,token_id,now_ts,max_age_sec=5.):
  e=str(token_id or"")
  if not e or e in getattr(a,"_ws_rest_seeded",set()):return None
  c=a._ws_books.get(e)if getattr(a,"_ws_books",None)is not None else None
  if c is None:return None
  if(float(now_ts)-float(c[0]))>float(max_age_sec)and not a._is_ws_book_live_on_healthy_shard(e,float(c[0]),float(now_ts),max_shard_silence_sec=min(float(max_age_sec),5.)):return None
  g=c[1]
  if isinstance(g,dict):
   f=(a.__dict__.get("_token_tick_sizes")or{}).get(e);d=max((float(b.get("price",0)or 0)for b in(g.get("bids")or[])if isinstance(b,dict)),default=.0)
   if d>=.96 and str(f or g.get("minimum_tick_size")or"")=="0.01":g.pop("minimum_tick_size",None)
   elif f:g["minimum_tick_size"]=f
  return g if isinstance(g,dict)and(g.get("asks")or g.get("bids"))else None
 async def fetch_books_batch(a,token_ids,timeout=3.):
  G=list(dict.fromkeys(str(t)for t in token_ids if t))
  if not G:return{}
  if"fetch_json"in a.__dict__:v=await asyncio.gather(*(a.fetch_json(f"{CLOB_URL}/book?token_id={t}",timeout=timeout)for t in G));return{t:I for t,I in zip(G,v)if isinstance(I,dict)}
  H={};y=[];D=time.time();B=not a.single_scan;u=a.__dict__.setdefault("_token_tick_sizes",{});w=a.__dict__.setdefault("_token_tick_boundary_ts",{});l=a.__dict__.setdefault("_rest_books_cache",{});j=a.__dict__.setdefault("_rest_empty_books_ts",{});h=a.__dict__.setdefault("_ws_last_reconciled_ts",{})
  for t in G:
   s=a._ws_books.get(t)if B else None;q=(max((float(b.get("price",0)or 0)for b in(s[1].get("bids")or[])if isinstance(b,dict)),default=.0)if s is not None and isinstance(s[1],dict)else.0)
   if s is not None and isinstance(s[1],dict)and q>=.96 and str(s[1].get("minimum_tick_size")or"")=="0.01":s[1].pop("minimum_tick_size",None)
   f=(q>=.96 and str(u.get(t)or"")in("","0.01")and(D-float(w.get(t,.0)))>=8.);p=s is not None and((D-s[0])<=1.5 or a._is_ws_book_live_on_healthy_shard(t,s[0],D,max_shard_silence_sec=5.))
   if(p and(s[1].get("bids")or s[1].get("asks"))and not f):
    if t in u and not(q>=.96 and str(u.get(t)or"")=="0.01"):s[1]["minimum_tick_size"]=u[t]
    H[t]=s[1];continue
   if B:
    o=t in a._ws_subscribed_tokens;A=12. if o else 45.;n=l.get(t)
    if n is not None and(D-float(n[0]))<=A and isinstance(n[1],dict):
     m=max((float(b.get("price",0)or 0)for b in(n[1].get("bids")or[])if isinstance(b,dict)),default=.0);g=(m>=.96 and str(u.get(t)or"")in("","0.01")and(D-float(w.get(t,.0)))>=8.)
     if not g:H[t]=n[1];continue
    C=j.get(t)
    if C is not None and(D-float(C))<=(20. if o else 90.):continue
   y.append(t)
  if not y:return H
  F=await a.get_session();k=a.__dict__.get("_books_post_sem")
  if k is None:k=asyncio.Semaphore(4);a.__dict__["_books_post_sem"]=k
  def e(t_id,bk,ts_now):
   if not isinstance(bk,dict):return
   i=bk.get("minimum_tick_size")or bk.get("tick_size")
   if i:u[t_id]=str(i);w[t_id]=ts_now;bk["minimum_tick_size"]=str(i)
   b=a._slim_rest_book(bk);H[t_id]=b;l[t_id]=(ts_now,b);j.pop(t_id,None);h[t_id]=ts_now
  async def c(sub_chunk):
   async with k:
    b=0
    try:
     J=[{"token_id":t}for t in sub_chunk];R=max(float(timeout),6.5)if len(sub_chunk)>100 else float(timeout);L={"timeout":aiohttp.ClientTimeout(total=R+2.5,sock_read=R)if aiohttp is not None else R}
     if _orjson is not None:L["data"]=_orjson.dumps(J);L["headers"]={"Content-Type":"application/json"}
     else:L["json"]=J
     async with F.post(f"{CLOB_URL}/books",**L)as Y:
      b=int(Y.status or 0)
      if b==200:
       I=await Y.read();X=_orjson.loads(I)if _orjson is not None else json.loads(I)
       if isinstance(X,list):
        K=time.time();i=set()
        for r in X:
         if isinstance(r,dict)and r.get("asset_id"):
          Q=str(r["asset_id"]);i.add(Q);W=r.get("minimum_tick_size")or r.get("tick_size")
          if W:u[Q]=str(W);w[Q]=K;r["minimum_tick_size"]=str(W)
          M=a._slim_rest_book(r);H[Q]=M;l[Q]=(K,M);j.pop(Q,None);h[Q]=K
          if B and Q in a._ws_subscribed_tokens:
           if Q not in a._ws_raw_levels:a._apply_ws_book_snapshot(Q,M.get("bids")or[],M.get("asks")or[],K,from_rest=True)
           else:
            V,U=a._ws_raw_levels[Q];P=max(V.keys())if V else.0;O=min(U.keys())if U else.0;T=max((round(float(x.get("price",0)or 0),4)for x in(M.get("bids")or())if float(x.get("size",0)or 0)>0),default=.0);S=min((round(float(x.get("price",0)or 0),4)for x in(M.get("asks")or())if float(x.get("size",0)or 0)>0),default=.0)
            if abs(P-T)>1e-4 or abs(O-S)>1e-4:a._apply_ws_book_snapshot(Q,M.get("bids")or[],M.get("asks")or[],K,from_rest=True)
        for N in sub_chunk:
         if N not in i:j[N]=K;h[N]=K
        return True,200
    except Exception:pass
    return False,b
  async def d(chunk):
   K,J=await c(chunk)
   if K or(J==429 and"fetch_json"not in a.__dict__):return
   b=[]
   if len(chunk)>50:
    r=[chunk[i:i+50]for i in range(0,len(chunk),50)];I=await asyncio.gather(*(c(sc)for sc in r))
    for sc,(O,N)in zip(r,I):
     if not O and(N!=429 or"fetch_json"in a.__dict__):b.extend(sc)
   else:b=list(chunk)
   if not b:return
   M=time.time()
   for R in range(0,len(b),10):
    x=b[R:R+10];L=await asyncio.gather(*(a.fetch_json(f"{CLOB_URL}/book?token_id={t}",timeout=min(timeout,2.))for t in x),return_exceptions=True)
    for Q,P in zip(x,L):
     if isinstance(P,dict):e(Q,P,M)
  z=[y[I:I+400]for I in range(0,len(y),400)]
  if len(z)==1:await d(z[0])
  else:await asyncio.gather(*(d(I)for I in z))
  if len(l)>1000:
   for E,_ in sorted(l.items(),key=lambda I:float(I[1][0]))[:-800]:l.pop(E,None)
  return H
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
  logger.info("Discovering active Weather (#1), Barrier Hit (#2), Multi-Strike (#4), NegRisk, and Daily Up/Down markets...");K={};_j=time.time();from src.polymarket_research.riskless_protocol_v2_expansion import(attach_weather_neg_risk_from_gamma as c,resolve_weather_effective_end_ts as f)
  def d(sp_w):return f(sp_w,_j+86400.)>_j
  _a=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?tag_slug=weather&closed=false&limit=100&offset={w_off}",timeout=7.)for w_off in(0,100,200,300,400)))
  for _8 in _a:
   if isinstance(_8,list):
    for g in _8:
     sp=parse_weather_event(g)
     if sp is not None and d(sp):c(sp,g);K[sp.event_id]=sp
  m=[]
  for _aA in range(0,600,100):
   R=await a.fetch_json(f"{GAMMA_URL}/events?closed=false&order=volume24hr&ascending=false&limit=100&offset={_aA}",timeout=7.)
   if not isinstance(R,list)or not R:break
   m.extend(R)
   for g in R:
    sp=parse_weather_event(g)
    if sp is not None and d(sp):c(sp,g);K[sp.event_id]=sp
  J={sp.series_slug for sp in K.values()if sp.series_slug}
  for _az in HIGH_VOLUME_WEATHER_SERIES:
   if _az in J:continue
   _ay=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={_az}&closed=false&limit=3",timeout=5.)
   if isinstance(_ay,list):
    for g in _ay:
     sp=parse_weather_event(g,series_slug_hint=_az)
     if sp is not None and d(sp):c(sp,g);K[sp.event_id]=sp
  a.weather_events=K;I={}
  for h,_aT,slug in HIT_SERIES:
   R=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5",timeout=6.)
   if isinstance(R,list):
    for g in R:
     for r in parse_hit_event(g,h,_aT,slug):
      if r.resolved_yes is None and r.end_ts>time.time()+60:I[r.market_id]=r
  a.barrier_rungs=I;S={};x=[]
  for h,slug in STRIKE_SERIES:
   R=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5",timeout=6.)
   if isinstance(R,list):
    x.extend(R)
    for g in R:
     _aS=parse_multistrike_event(g,h,slug)
     if _aS and _aS[0].end_ts>time.time()+60:S[f"{h}_{g.get('id')}"]=_aS
  a.strike_ladders=S;H={}
  for h,slug in NEGRISK_SERIES:
   _7=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4",timeout=6.)
   if isinstance(_7,list):
    for g in _7:
     brs=parse_negrisk_bracket_event(g,h,slug)
     if brs and brs[0].end_ts>time.time()+60:H[f"{h}_{int(brs[0].end_ts)}"]=brs
  a.negrisk_ladders=H;Q={}
  for h,slug in DAILY_UPDOWN_SERIES:
   _6=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3",timeout=5.)
   if isinstance(_6,list):
    for g in _6:
     _aR=parse_daily_updown_event(g,h,slug)
     if _aR is not None and _aR.end_ts>time.time()+60:Q[_aR.market_id]=_aR
  a.daily_updown_markets=Q;_i={}
  for h,slug in ZERO_FEE_PYTH_DAILY_SERIES:
   _5=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=2",timeout=5.)
   if isinstance(_5,list):
    for g in _5:
     _aQ=parse_daily_updown_event(g,h,slug)
     if _aQ is not None and _aQ.end_ts>time.time()+60:_i[_aQ.market_id]=_aQ
  a.pyth_daily_markets=_i;P=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3",timeout=5.)for _,_,slug in PYTH_HIT_SERIES));A={};_G=time.time()
  for(_4,_3,_ax),_2 in zip(PYTH_HIT_SERIES,P):
   if isinstance(_2,list):
    for g in _2:
     for rp in parse_pyth_hit_event(g,_4,_3,_ax):
      if rp.end_ts>_G+60:A[rp.market_id]=rp
  a.pyth_barrier_rungs=A;Z=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3",timeout=5.)for _,slug in PYTH_CLOSE_SERIES));G={}
  for(_1,_aw),_0 in zip(PYTH_CLOSE_SERIES,Z):
   if isinstance(_0,list):
    for g in _0:
     _Z=parse_pyth_close_event(g,_1,_aw)
     if _Z and _Z[0].end_ts>_G+60:G[f"{_1}_{g.get('id')}"]=_Z
  a.pyth_close_ladders=G;_w={};_F={};_h={};F={};w={};_g={}
  for _E in NBA_SERIES_SLUGS:
   _D=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={_E}&closed=false&limit=40",timeout=6.5)
   if isinstance(_D,list):
    for g in _D:
     _aP=str(g.get("slug")or"").lower()
     if _aP.endswith("-exact-margin"):_g[_aP[:-13]]=g;continue
     w[_aP]=g;_av=parse_nba_zero_fee_event(g,now_ts=_G)
     if _av is not None:_w[_av.event_id]=_av
     _aO=parse_nba_player_props_from_event(g,now_ts=_G)
     if _aO is not None:_h[_aO.event_id]=_aO
     _au=parse_nba_subperiod_and_ext_props(g,now_ts=_G)
     if _au is not None:F[_au.event_id]=_au
     _v=parse_multi_sport_corridor_event(g,sport_hint="NBA",now_ts=_G,skip_nba_fg_zero_fee=True)
     if _v is not None:_F[_v.event_id]=_v
  v=[sl for sl in list(w.keys())[:10]if sl not in _g]
  if v:
   _f=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl}-exact-margin",timeout=4.5)for sl in v))
   for _a3,_at in zip(v,_f):
    if isinstance(_at,list)and _at:_g[_a3]=_at[0]
  u={}
  for _a2,_a1 in w.items():
   _a0=_g.get(_a2)
   if _a0 is not None:
    _aZ=build_lp1_nba_exact_margin_bundle(_a1,_a0)
    if _aZ is not None and float(_aZ["end_ts"])>_G+60:u[_aZ["event_id"]]=_aZ
  a.nba_games=_w;a.nba_prop_slates=_h;a.nba_subperiod_slates=F;a.lp1_nba_em_bundles=u;j=[(sl_s,sp_t)for sp_t,sl_s in MULTI_SPORT_CORRIDOR_SERIES if sl_s not in NBA_SERIES_SLUGS];_as=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={sl_s}&closed=false&limit=25",timeout=5.5)for sl_s,_ in j),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=sports&closed=false&order=volume24hr&ascending=false&limit=40",timeout=6.));O={};N={}
  for(_,_ar),_Y in zip(j,_as[:len(j)]):
   if isinstance(_Y,list):
    for g in _Y:
     _e=parse_multi_sport_corridor_event(g,sport_hint=_ar,now_ts=_G,skip_nba_fg_zero_fee=True)
     if _e is not None:_F[_e.event_id]=_e
     _X=str(g.get("id")or"")
     if _X and _ar in("NFL","CFB","NHL"):N[_X]=(_ar,g)
     if _ar=="NFL":
      _aN=build_lp1_nfl_exact_margin_bundle(g,now_ts=_G)
      if _aN is not None:O[_aN["event_id"]]=_aN
  a.lp1_nfl_em_bundles=O;a.multisport_raw_events=N;q=(_as[-1]if isinstance(_as[-1],list)else[])+[e for e in m if isinstance(e,dict)and not e.get("negRisk")and len(e.get("markets")or())>=8]
  for g in q:
   _W=str(g.get("id")or"")
   if _W and _W not in _F:
    _e=parse_multi_sport_corridor_event(g,now_ts=_G,skip_nba_fg_zero_fee=True)
    if _e is not None:_F[_e.event_id]=_e
  a.multi_sport_games=_F;_V=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4",timeout=5.)for slug in ZERO_FEE_NEGRISK_SERIES));_u={};E={}
  for _aq,_U in zip(ZERO_FEE_NEGRISK_SERIES,_V):
   if isinstance(_U,list):
    E[_aq]=_U;_C=_aq in("best-ai-company","chinese-ai-1")
    for g in _U:
     _aM=parse_zero_fee_negrisk_slate(g,_aq,allow_mixed_fees=_C)
     if _aM is not None and _aM.end_ts>_G+60:_u[_aM.event_id]=_aM
  a.negrisk_zero_slates=_u;z={}
  for _ap in(m+[e for lst in E.values()for e in(lst or[])]+[e for lst in _a if isinstance(lst,list)for e in lst]):
   if not isinstance(_ap,dict):continue
   _ao=parse_negrisk_convert_event(_ap)
   if _ao is not None and _ao.end_ts>_G+60 and len(_ao.brackets)<=45:z[_ao.event_id]=_ao
  _d=sorted(z.values(),key=lambda s:(not s.is_closed_convert_safe,(s.end_ts-_G)>172800.,s.end_ts))[:180];a.negrisk_convert_slates={s.event_id:s for s in _d};_t={}
  for _an,_B in COUNTING_SERIES_HANDLES:
   for _aY in(E.get(_an)or[]):
    _aX=parse_counting_slate_event(_aY,_an,_B)
    if _aX is not None and _aX.window_end_ts>_G+60:_t[_aX.event_id]=_aX
  if not(a.single_scan or("fetch_json"in a.__dict__))and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_xtrack1_expanded_handles",True)):await a._discover_xtracker_active_counting_slates(_t,_G)
  a.counting_slates=_t;a.fomc_truth_legs=build_fomc_truth_table_legs(E.get("fomc")or[],E.get("fed-3-parlay")or[],sep_2026_realized_action=(os.getenv("PM_SEP_2026_FOMC_ACTION")or"").strip().upper()or None);_am=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl_os}",timeout=5.)for sl_os in OIL_SENATE_SLUGS),a.fetch_json(f"{GAMMA_URL}/events?series_slug=gas-price-hits-weekly&closed=false&limit=2",timeout=5.));_c={}
  for sl_os,_al in zip(OIL_SENATE_SLUGS,_am[:len(OIL_SENATE_SLUGS)]):
   if isinstance(_al,list)and _al:
    _aW=_al[0];_c[sl_os]=_aW
    if"pending-oil"in sl_os:
     _A=parse_zero_fee_negrisk_slate(_aW,sl_os)
     if _A is not None and _A.end_ts>_G+60:a.negrisk_zero_slates[_A.event_id]=_A
  a.oil_senate_truth_legs=build_oil_senate_truth_table_legs(_c);a.gas_events_raw={"us-gas-price-daily":E.get("us-gas-price-daily")or[],"gas-price-hits-weekly":_am[-1]if isinstance(_am[-1],list)else[]};p={int(round(sp.end_ts))for sp in a.daily_updown_markets.values()}|{int(round(rgs[0].end_ts))for rgs in a.strike_ladders.values()if rgs};_ak=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?series_slug={h_slug}&closed=false&limit=6",timeout=4.5)for h_slug in HOURLY_BINANCE_SERIES.values()));_s={}
  for(_T,h_slug),_aj in zip(HOURLY_BINANCE_SERIES.items(),_ak):
   if isinstance(_aj,list):
    for _aV in _aj:
     _aU=parse_daily_updown_event(_aV,_T,h_slug)
     if _aU is not None and _aU.end_ts>_G+30 and any(abs(_aU.end_ts-te)<=5. for te in p):_s[_aU.market_id]=_aU
  a.hourly_12pm_markets=_s;Y=datetime.fromtimestamp(_G-4.*3600.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");_S=await asyncio.gather(a.fetch_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&order=volume24hr&ascending=false&limit=100",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&end_date_min={Y}&order=endDate&ascending=true&limit=100",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&order=volume24hr&ascending=false&limit=100",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&end_date_min={Y}&order=endDate&ascending=true&limit=100",timeout=5.5),*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl_b}",timeout=5.)for sl_b in BOP_2026_SLUGS));_r=(_S[0]if isinstance(_S[0],list)else[])+(_S[1]if isinstance(_S[1],list)else[]);_q=(_S[2]if isinstance(_S[2],list)else[])+(_S[3]if isinstance(_S[3],list)else[]);_R=list({str(e.get("id")):e for e in _r if isinstance(e,dict)and e.get("id")}.values());_Q=list({str(e.get("id")):e for e in _q if isinstance(e,dict)and e.get("id")}.values());a.soccer_trees=link_and_parse_soccer_regulation_trees(_R,now_ts=_G);_p={}
  for _ai in _Q:
   _ah=parse_esports_bo3_event(_ai,now_ts=_G)
   if _ah is not None:_p[_ah.event_id]=_ah
  a.esports_bo3_specs=_p;X={}
  for sl_b,_aL in zip(BOP_2026_SLUGS,_S[4:]):
   if isinstance(_aL,list)and _aL:X[sl_b]=_aL[0]
  a.lp1_bop_legs=build_lp1_bop_2026_truth_legs(X)
  for W in list(_g.values())+list(X.values()):
   _z=parse_negrisk_convert_event(W)
   if _z is not None and _z.is_closed_convert_safe and _z.end_ts>_G+60:a.negrisk_convert_slates[_z.event_id]=_z
  D=list(dict.fromkeys(list(LP2_MIDTERM_CORE_SLUGS)+[LP2_TOSSUP_CUBE_SLUG]+list(LP2_TOSSUP_STATE_SLUGS.values())));_P=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl_l2}",timeout=5.)for sl_l2 in D),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=tennis&active=true&closed=false&order=volume24hr&ascending=false&limit=45",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=midterms&active=true&closed=false&order=volume24hr&ascending=false&limit=60",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=politics&active=true&closed=false&order=volume24hr&ascending=false&limit=60",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=geopolitics&active=true&closed=false&order=volume24hr&ascending=false&limit=80",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=oil&active=true&closed=false&order=volume24hr&ascending=false&limit=50",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=ukraine&active=true&closed=false&order=volume24hr&ascending=false&limit=45",timeout=5.5),a.fetch_json(f"{GAMMA_URL}/events?tag_slug=world&active=true&closed=false&order=volume24hr&ascending=false&limit=60",timeout=5.5));V=dict(X)
  for sl_l2,_ag in zip(D,_P[:len(D)]):
   if isinstance(_ag,list)and _ag:V[sl_l2]=_ag[0]
  _y=len(D);_O=_P[_y]if isinstance(_P[_y],list)else[];_N=_P[_y+1]if isinstance(_P[_y+1],list)else[];_M=_P[_y+2]if isinstance(_P[_y+2],list)else[];_L=_P[_y+3]if isinstance(_P[_y+3],list)else[];_K=_P[_y+4]if isinstance(_P[_y+4],list)else[];_J=_P[_y+5]if isinstance(_P[_y+5],list)else[];_o=_P[_y+6]if isinstance(_P[_y+6],list)else[]
  for _aK in _N+_M:
   if isinstance(_aK,dict)and _aK.get("slug"):V.setdefault(str(_aK["slug"]),_aK)
  a.lp2_events_by_slug=V;_b=[];_I=build_lp2_house_seats_truth_legs(V)
  if _I:_b.append(("LP2_HOUSE_SEATS",_I))
  _H=build_lp2_senate_seats_truth_legs(V)
  if _H:_b.append(("LP2_SENATE_SEATS",_H))
  _b.extend(build_lp2_pending_senate_conditional_groups(list(V.values()),V.get("which-party-will-win-the-senate-in-2026")));_b.extend(build_lp2_tossup_state_implication_groups(V));a.lp2_implication_groups=_b
  for _n in list(V.values())+_L+_K+_J+_o:
   if not isinstance(_n,dict):continue
   _m=parse_negrisk_convert_event(_n)
   if _m is not None and _m.is_closed_convert_safe and _m.end_ts>_G+60 and len(_m.brackets)<=45:a.negrisk_convert_slates[_m.event_id]=_m
  _l={};M=set()
  for _af in m+_N+_M+_L+_K+_J+_o:
   if not isinstance(_af,dict):continue
   _aJ=str(_af.get("id")or"")
   if not _aJ or _aJ in M:continue
   M.add(_aJ)
   for _ae in parse_cal1_monotonic_ladder_event(_af,now_ts=_G):_l[_ae.event_id]=_ae
  a.cal1_ladders=_l;_k={}
  for _ad in _O+q:
   if not isinstance(_ad,dict):continue
   _ac=parse_tennis_retirement_safe_event(_ad,now_ts=_G)
   if _ac is not None:_k[_ac.event_id]=_ac
  a.tennis_specs=_k;y=[sl for sl,ev_n in sorted(w.items(),key=lambda kv:_parse_iso_ts(kv[1].get("startTime")or kv[1].get("endDate"))or 9e12)if not sl.endswith("-more-markets")][:12];l=[];k=[]
  for _aI,_aH in N.values():
   _aG=str(_aH.get("slug")or"").lower()
   if not _aG or any(_aG.endswith(sfx)for sfx in("-more-markets","-player-props","-exact-margin")):continue
   if _aI in("NFL","CFB")and len(l)<12:l.append(_aG)
   if _aI=="NFL"and len(k)<10:k.append(_aG)
  i={str(e.get("slug")or"").lower()for e in _R if isinstance(e,dict)};o=[f"{tr.slug_3way}-exact-score"for tr in sorted(a.soccer_trees.values(),key=lambda t:t.end_ts)[:16]if tr.slug_3way and f"{tr.slug_3way}-exact-score"not in i];n=list(dict.fromkeys([f"{sl}-more-markets"for sl in(y+l)]+[f"{sl}-player-props"for sl in k]+o));L=[]
  if n:
   U=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/events?slug={sl_v4}",timeout=4.5)for sl_v4 in n))
   for _ab in U:
    if isinstance(_ab,list)and _ab and isinstance(_ab[0],dict):L.append(_ab[0])
  C=(list(w.values())+[ev_m for sp_tm,ev_m in N.values()if sp_tm in("NFL","CFB")]+q+L);a.aff1_bundles={b.event_id:b for b in parse_affine_game_bundle(C,now_ts=_G)}
  for _aa in L:
   _aF=str(_aa.get("slug")or"").lower()
   if _aF.startswith("nba-"):
    _x=parse_nba_subperiod_and_ext_props(_aa,now_ts=_G)
    if _x is not None and _x.event_id not in a.nba_subperiod_slates:a.nba_subperiod_slates[_x.event_id]=_x
  a.soc2_lattices=link_and_parse_soc2_exact_score_lattices(_R+L,now_ts=_G)
  for _9 in a.soc2_lattices.values():
   if _9.convert_spec is not None and _9.convert_spec.end_ts>_G+60:a.negrisk_convert_slates[_9.convert_spec.event_id]=_9.convert_spec
  B={}
  for _aE in[ev_m for sp_tm,ev_m in N.values()if sp_tm=="NFL"]+L+q:
   if not isinstance(_aE,dict):continue
   _aD=parse_nfl_player_props_event(_aE,now_ts=_G)
   if _aD is not None:B[_aD.event_id]=_aD
  a.nfl_prop_slates=B;T={}
  for _aC in x+m:
   if isinstance(_aC,dict):
    for _aB in parse_binance_terminal_close_event(_aC):
     if _aB.close_ts>_G+120:T[_aB.market_id]=_aB
  a.binance_close_rungs=list(T.values())
  if bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_zerofee1_mergeable_sweeper",True)):a.zerofee_general_binaries=a.extract_zerofee_general_binaries(m+_N+_M+_L+_K+_J+_o+[e for lst in E.values()for e in(lst or[])if isinstance(e,dict)],_G,max_markets=1200)
  else:a.zerofee_general_binaries=[]
  a.lp2_events_by_slug={sl_k:a._slim_raw_gamma_event(ev_v)for sl_k,ev_v in V.items()if isinstance(ev_v,dict)};a.multisport_raw_events={ev_id_k:(sp_tag_v,a._slim_raw_gamma_event(ev_v))for ev_id_k,(sp_tag_v,ev_v)in list(N.items())[:24]if isinstance(ev_v,dict)};a.gas_events_raw={gk:[a._slim_raw_gamma_event(ge)for ge in(gv or[])if isinstance(ge,dict)]for gk,gv in a.gas_events_raw.items()};del m,_a,_r,_q,_N,_M,_L,_K,_J,_o,L;a._release_unused_heap_memory();a.last_discovery_ts=time.time();logger.info(f"Discovery complete: {len(a.weather_events)} Weather city-events, {len(a.barrier_rungs)} Barrier Hit rungs, {len(a.strike_ladders)} Multi-Strike ladders, {len(a.negrisk_ladders)} NegRisk ladders, {len(a.daily_updown_markets)} Crypto Daily Up/Down, {len(a.pyth_daily_markets)} Zero-Fee Pyth FX/Metals Daily, {len(a.pyth_barrier_rungs)} Pyth Hit rungs, {len(a.pyth_close_ladders)} Pyth Close ladders, {len(a.nba_games)} NBA games ({len(a.nba_prop_slates)} Prop, {len(a.nba_subperiod_slates)} SubPer, {len(a.lp1_nba_em_bundles)} EM), {len(a.multi_sport_games)} Multi-Sport ({len(a.lp1_nfl_em_bundles)} NFL EM, {len(a.nfl_prop_slates)} NFL Prop, {len(a.aff1_bundles)} AFF1/SUM1), {len(a.soccer_trees)} Soccer trees ({len(a.soc2_lattices)} SOC2 Exact-Score), {len(a.tennis_specs)} Tennis BO3, {len(a.esports_bo3_specs)} Esports BO3, {len(a.lp2_implication_groups)} LP2 DAG groups, {len(a.cal1_ladders)} CAL1 ladders, {len(a.binance_close_rungs)} Binance Close rungs, {len(a.lp1_bop_legs)//2} BOP/Chamber mkts, {len(a.zerofee_general_binaries)} ZeroFee GenBins, {len(a.negrisk_zero_slates)} NegRisk Slates, {len(a.negrisk_convert_slates)} NegRisk Convert slates, {len(a.counting_slates)} Counting slates, {len(a.fomc_truth_legs)//2} FOMC LP mkts, {len(a.oil_senate_truth_legs)//2} Oil-Senate mkts, {len(a.hourly_12pm_markets)} 12PM 1h pairs.")
 async def _discover_xtracker_active_counting_slates(b,cnt_found,now_disc):
  try:
   f=await asyncio.gather(*(asyncio.to_thread(fetch_xtracker_user_stats_sync,h)for h in XTRACKER_ALL_HANDLES),return_exceptions=True);i={}
   for m,l in zip(XTRACKER_ALL_HANDLES,f):
    if isinstance(l,dict)and l:i[m]=l
   c={s.slug for s in cnt_found.values()if s.slug};a=[(eslug,hnd)for eslug,hnd in extract_xtracker_active_event_slugs(i)if eslug and eslug not in c][:24]
   if not a:return
   d=await asyncio.gather(*(b.fetch_json(f"{GAMMA_URL}/events?slug={eslug}",timeout=4.5)for eslug,_ in a),return_exceptions=True)
   for(eslug,hnd),g in zip(a,d):
    if not isinstance(g,list)or not g or not isinstance(g[0],dict):continue
    k=g[0];j=parse_counting_slate_event(k,eslug,hnd)
    if j is not None and j.window_end_ts>now_disc+60:cnt_found[j.event_id]=j
    e=parse_negrisk_convert_event(k)
    if e is not None and e.is_closed_convert_safe and e.end_ts>now_disc+60 and len(e.brackets)<=45:b.negrisk_convert_slates[e.event_id]=e
  except Exception:pass
 @staticmethod
 def extract_zerofee_general_binaries(events,now_ts,max_markets=1200,*,include_neg_risk_subconditions=True):
  A={}
  for R in(events or[]):
   if not isinstance(R,dict)or bool(R.get("closed")):continue
   e=isinstance(R.get("markets"),list);F=(bool(R.get("negRisk"))or bool(R.get("enableNegRisk")))if e else False
   if F and not include_neg_risk_subconditions:continue
   n=str(R.get("slug")or"").strip().lower();k=R.get("markets")if e else([R]if("conditionId"in R or"clobTokenIds"in R)else[])
   for Q in(k or[]):
    if not isinstance(Q,dict):continue
    if bool(Q.get("closed"))or Q.get("active")is False or not bool(Q.get("enableOrderBook",True)):continue
    P=str(Q.get("id")or"").strip()
    if not P or P in("6707502","6707503"):continue
    if str(Q.get("umaResolutionStatus")or"").strip().lower()=="disputed":continue
    E=bool(Q.get("negRisk"))or F
    if E and not include_neg_risk_subconditions:continue
    z,m=_extract_market_fee_rate(Q);w=float(z or.0);O=float(m or 1.);g=str(Q.get("feeType")or"").strip().lower();f=(bool(Q.get("feesEnabled"))and g!="zero_fees")or(w>1e-9)
    if f:
     if w<=1e-9:y=float(Q.get("feeRateBps")or.0);w=(y/1e4)if y>.0 else.02
     v=Q.get("outcomePrices");a=[]
     if isinstance(v,str)and v.strip().startswith("["):
      try:a=[float(x)for x in json.loads(v)[:2]]
      except Exception:a=[]
     elif isinstance(v,(list,tuple)):
      try:a=[float(x)for x in v[:2]]
      except Exception:a=[]
     N=a[0]if len(a)>=2 else.0;M=a[1]if len(a)>=2 else.0;u=float(Q.get("yes_ask")or.0);t=float(Q.get("no_ask")or.0);s=float(Q.get("yes_bid")or.0);q=float(Q.get("no_bid")or.0);D=float(Q.get("bestAsk")or.0);C=float(Q.get("bestBid")or.0)
     if u>.0 and t>.0:c=u+t
     elif D>.0 and C>.0:c=D+(1.-C)
     elif N>.0 and M>.0 and(N+M)<.9995:c=N+M
     else:c=.0
     if s>.0 and q>.0:b=s+q
     elif D>.0 and C>.0:b=C+(1.-D)
     elif N>.0 and M>.0 and(N+M)>1.0005:b=N+M
     else:b=.0
     l=N>=.94 or M>=.94 or(.0<N<=.06)or(.0<M<=.06)or(.94<=C<1.)or(.94<=D<1.)or(.0<D<=.06)
     if not((.0<c<=1.005)or(b>=.995)or l):continue
    H=_parse_clob_tokens(Q);L=str(Q.get("conditionId")or"").strip()
    if not H or len(H)!=2 or not L.startswith("0x")or len(L)!=66:continue
    p=_parse_iso_ts(Q.get("endDate")or R.get("endDate"))or.0
    if p<=now_ts+120.:continue
    K=float(Q.get("liquidityNum")or Q.get("liquidity")or R.get("liquidity")or.0);B=float(Q.get("volume24hr")or R.get("volume24hr")or.0);j=max(.01,(p-now_ts)/86400.);d=(math.log1p(max(.0,B)*4.+max(.0,K))+(.55 if not f else.0)+(.45 if not E else.0)+(.3 if j<=7. else(.12 if j<=30. else.0)));i=(-round(d,4),min(j,30.),-max(B,K));J="ZF_"if not f else"FB_";h=(J+(n.split("-")[0]or"GEN").upper()[:8])if n else("ZEROFEE"if not f else"FEEBIN");I={"market_id":P,"condition_id":L,"yes_token":str(H[0]),"no_token":str(H[1]),"fee_rate":round(w,6)if f else.0,"fee_exponent":round(O,4),"fees_enabled":f,"holding_rewards_enabled":bool(Q.get("holdingRewardsEnabled")or R.get("holdingRewardsEnabled")),"neg_risk":E,"end_ts":float(p),"asset":h,"title":str(Q.get("question")or R.get("title")or P)[:96]};G=A.get(L)
    if G is None or i<G[0]:A[L]=(i,I)
  o=sorted(A.values(),key=lambda S:S[0])[:max(1,int(max_markets))];return[r for _,r in o]
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
  now=time.time();_C=datetime.now(timezone.utc);D=("fetch_json"not in d.__dict__)and(not d.single_scan)and bool(d.pending_maker_orders);p={};m={}
  if D:
   _B=[];_a=[];Z=set()
   for _m in d.pending_maker_orders.values():
    _sl=str(_m.get("sleeve")or"");_tk=str(_m.get("token_id")or"");_ab=now-float(_m.get("created_ts")or.0);_aa=float(_m.get("close_ts")or.0)-now;_ex=_m.get("extra")or{}
    if _tk and _ab>=.35:_B.append(_tk)
    _W=_sl=="MKR_REWARD_LOCKED_CARRY";_V=_sl in LOCKED_MAKER_SLEEVES
    if(_sl in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER")or _W):
     _U=str(_ex.get("opp_token_id")or"");_A=30. if(_W and _aa>9e2)else 12.
     if _U and(now-float(_m.get("_last_opp_chk_ts")or.0))>=_A:_B.append(_U)
    if _V or _W:
     _9=str(_ex.get("condition_id")or"");_T=float(d._last_trade_tape_chk_ts.get(_9)or.0);_S=45. if(_W and _aa>9e2)else 12.
     if _9 and _9 not in Z and(now-_T)>=_S:Z.add(_9);_a.append((_T,_aa,_9))
   if _B:p=await d.fetch_books_batch(_B,timeout=3.)
   if _a:
    _a.sort(key=lambda r:(r[0],r[1]));_h=[cid for _,_,cid in _a[:16]]
    for _R in _h:d._last_trade_tape_chk_ts[_R]=now
    _z=await asyncio.gather(*(d.fetch_json(f"{DATA_API_URL}/trades?market={cid}&limit=15",timeout=3.)for cid in _h));m={cid:tr for cid,tr in zip(_h,_z)}
  for oid,_7 in list(d.pending_maker_orders.items()):
   _Q=_7["sleeve"];x=_Q=="W2_MAKER_OVERROUND";A=_Q=="MKR_REWARD_LOCKED_CARRY";z=_Q in LOCKED_MAKER_SLEEVES;_6=_7["asset_or_city"];tok=_7["token_id"];N=float(_7["resting_bid"]);_t=float(_7["close_ts"]);_y=_t-now;_5=now-float(_7["created_ts"]);_4=dict(_7.get("extra")or{});_P=float(_4.get("strike")or.0);_x=bool(_4.get("is_downward"));_s=_7["side"];_w=(_s=="YES"and not _x)or(_s=="NO"and _x)
   def f(ord_obj):
    d.entered_keys.discard(ord_obj["dedupe_key"]);a=(ord_obj.get("extra")or{}).get("event_id")
    if a and ord_obj.get("sleeve")=="W2_MAKER_OVERROUND":d.entered_keys.discard(f"W2M_EVENT_{a}")
   _O=_7.get("ttl_override_sec")
   if _Q in("SP2_NBA_ENDGAME_LOCK","SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"):h=20.;g=float(_O)if _O is not None else 45.
   elif _Q in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"):h=60. if _Q=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"else 90.;g=float(_O)if _O is not None else 1800.
   elif _Q in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"):h=6e2;g=float(_O)if _O is not None else 3600.
   else:h=6e2 if A else(9e2 if _O is not None else(3600. if x else 7200.));g=float(_O)if _O is not None else(7200. if A else(2700. if x else 1800.))
   if _y<=h or _5>=g:d.pending_maker_orders.pop(oid,None);f(_7);d._append_ledger({"event":"SHADOW_MAKER_CANCEL","reason":"TTL_OR_EXPIRY",**_7});continue
   b=None;e=float(_7["p_model_at_post"])
   if _Q in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"):
    v=str(_4.get("event_id")or"");_p=d.weather_events.get(v)
    if _p is not None:
     X=f"{_p.icao}_{_p.obs_date.isoformat()}";w=(d.metar_cache.get(X)or(.0,[]))[1];W=(d.ensemble_cache.get(_p.icao)or(.0,{}))[1];_3=(d.taf_cache.get(_p.icao)or(.0,{}))[1]
     if w or W:
      V=compute_weather_probabilities(_p,_C,w,W,forecast_sigma_base_c=d.weather_sigma_c,taf_extreme_c=(_3 or{}).get(_p.metric));q=str(_4.get("market_id")or"")
      for U,I in enumerate(_p.buckets):
       if str(I.market_id)==q and U<len(V["probs"]):e=float(V["probs"][U]);break
      if V.get("convective_cold_pool"):b="CONVECTIVE_COLD_POOL"
      elif not V.get("is_solar_lock"):b="SOLAR_LOCK_INVALIDATED"
      elif(e-N)<.02:b="ADVERSE_METAR_OR_EDGE_DECAY"
   elif _Q in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER")or A:
    e=(float(_7.get("p_model_at_post")or 1.)if A else(float(_7.get("p_model_at_post")or.998)if _Q=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"else 1.));M=str(_4.get("opp_token_id")or"");L=30. if(D and A and _y>9e2)else 12.
    if M and(now-float(_7.get("_last_opp_chk_ts")or.0))>=L:
     _7["_last_opp_chk_ts"]=now;Y=(p.get(M)if D else await d.fetch_json(f"{CLOB_URL}/book?token_id={M}",timeout=2.5))
     if Y:
      J,_=extract_best_bid(Y.get("bids")or[]);K=(.008 if _Q=="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"else(.03 if(_Q=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"or A)else.012))
      if J>K:b="UMA_COMPLEMENT_DISPUTE_BID"
   elif _Q=="SP2_NBA_ENDGAME_LOCK":
    _r=d.nba_games.get(str(_4.get("event_id")or""))
    if _r is not None and d.live_nba_board:
     _g=match_nba_live_game(_r,d.live_nba_board)
     if _g is not None:
      _N,_M,_L=_g;_q=[c for c in evaluate_nba_endgame_locks(_r,_N,_M,_L)if c["leg"].token_id==tok]
      if not _q:b="NBA_ENDGAME_LOCK_INVALIDATED"
      else:e=float(_q[0]["p_lock"])
   elif x:
    v=str(_4.get("event_id")or"");_p=d.weather_events.get(v)
    if _p is not None:
     X=f"{_p.icao}_{_p.obs_date.isoformat()}";w=(d.metar_cache.get(X)or(.0,[]))[1];W=(d.ensemble_cache.get(_p.icao)or(.0,{}))[1]
     if w or W:
      V=compute_weather_probabilities(_p,_C,w,W,forecast_sigma_base_c=d.weather_sigma_c);q=str(_4.get("market_id")or"")
      for U,I in enumerate(_p.buckets):
       if str(I.market_id)==q and U<len(V["probs"]):e=float(V["probs"][U]);break
      if V.get("convective_cold_pool"):b="CONVECTIVE_COLD_POOL"
      elif(e-N)<.045:b="ADVERSE_METAR_OR_EDGE_DECAY"
   else:
    _o=d.spots.get(_6,.0);_f=float(_7.get("spot_at_post")or.0)
    if _o>0 and _P>0:_K=evaluate_svi_digital_fair_value(_6,_o,_P,_y,is_downward=_x,now_ts=now);e=float(_K["p_yes"]if _s=="YES"else _K["p_no"])
    if _o>0 and _f>0:
     _n=((_o-_f)/_f)*1e4
     if(_w and _n<-20.)or((not _w)and _n>20.):b="ADVERSE_SPOT_IMPULSE"
    if b is None and _o>0 and _P>0 and(e-N)<.035:b="SVI_EDGE_DECAY"
   bk=None;j=False
   if b is not None:
    if _5>=.35:
     _J=(p.get(tok)if D else await d.fetch_json(f"{CLOB_URL}/book?token_id={tok}",timeout=2.5))
     if _J:
      _l=[float(a["price"])for a in(_J.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]
      if _l and min(_l)<=N:bk=_J;j=True
    if not j:d.pending_maker_orders.pop(oid,None);f(_7);d._append_ledger({"event":"SHADOW_MAKER_CANCEL","reason":b,**_7});continue
   if not j:
    H=.5 if _O is not None else(4. if z else 10.)
    if _5<H:continue
    bk=(p.get(tok)if D else await d.fetch_json(f"{CLOB_URL}/book?token_id={tok}",timeout=3.))
   if not bk:continue
   _k=bk.get("asks")or[];T=[float(a["price"])for a in _k if float(a.get("price",0))>0 and float(a.get("size",0))>0];u=min(T)if T else 1.;n=(sum(float(a["size"])for a in _k if.0<float(a.get("price",0))<=N+1e-9 and float(a.get("size",0))>0)if T and u<=N else.0)
   if n<=.0 and(z or A):
    S=str(_4.get("condition_id")or"");G=float(d._last_trade_tape_chk_ts.get(S)or.0);o=None
    if D:o=m.get(S)
    elif S and(now-G)>=12.:d._last_trade_tape_chk_ts[S]=now;o=await d.fetch_json(f"{DATA_API_URL}/trades?market={S}&limit=15",timeout=3.)
    if isinstance(o,list)and o:
     _e=set(_7.get("_seen_trade_keys")or[]);R=str(_4.get("opp_token_id")or"");F=int(float(_7.get("last_repeg_ts")or _7["created_ts"]))+2;C=.0
     for tr in o:
      _2=int(float(tr.get("timestamp")or 0))
      if _2<F:continue
      _8=f"{tr.get('transactionHash')or''}_{_2}_{tr.get('asset')or''}_{tr.get('size')or''}_{tr.get('price')or''}"
      if _8 in _e:continue
      _H=str(tr.get("asset")or"");_1=float(tr.get("price")or.0);_0=float(tr.get("size")or.0)
      if _0<=.0 or _1<=.0:continue
      if(_H==tok and _1<=N+1e-6)or(R and _H==R and _1>=(1.-N)-1e-6):_e.add(_8);C+=_0
     if _e:_7["_seen_trade_keys"]=list(_e)[-30:]
     if C>.0:n=C;u=N;_4["filled_via_trade_tape"]=True
   if(n<=.0 and(z or A)and(now-float(_7.get("last_repeg_ts")or _7["created_ts"]))>=15. and _y>=180.):
    E,Q=extract_best_bid(bk.get("bids")or[])
    if E>N+1e-6:
     if A:k=.994 if e>=.999 else.99;i=.006 if e>=.999 else.008;s=.002 if u>.99 else.005
     elif _Q=="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":k,i,s=.996,.004,(.001 if u>.96 else.01)
     elif _Q=="BOND1_UMA_RESOLUTION_CARRY":k,i,s=.995,.005,(.001 if u>.96 else.01)
     elif _Q=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":k,i,s=.993,.0045,(.001 if u>.96 else.01)
     else:k,i,s=.0,1.,.01
     if k>.0:
      _Z=.001 if E>=.96 else.01;_v=(round(E+_Z,4)if(u-E)>=(_Z+s-1e-9)else E);_u=min(round(u-s,4),k,round(e-i,4));_j=.001 if min(_v,_u)>=.96-1e-9 else.01;_G=round(math.floor((min(_v,_u)+1e-9)/_j)*_j,4)
      if(_G>N+1e-6 and _G>=round(E-1e-9,4)and _G<=k+1e-9 and(e-_G)>=i-1e-9):_F=N;_7["resting_bid"]=_G;_7["l1_bid_usd"]=Q;_7["queue_ahead_usd"]=.0 if _G>E+1e-6 else round(min(Q*.5,60.),2);_7["maker_edge_at_post"]=round(e-_G,4);_7["last_repeg_ts"]=now;d._append_ledger({"event":"SHADOW_MAKER_POST",**_7});logger.info(f"[MAKER_OUTBID_REPEG:{_Q}] {_6} | {_7['title']} ({_s}) ${_F:.3f} -> ${_G:.3f} (outbid=${E:.3f}, ask=${u:.3f})");continue
   if n>.0:
    y=float(_7.get("queue_ahead_usd")or.0);B=y/max(.01,N);l=n-B
    if j:l=max(l,n,BANKROLL_TICKETS["T5000"][_Q]/max(.01,N))
    elif l<5.:_7["queue_ahead_usd"]=round(max(.0,y-n*N),2);continue
    d.pending_maker_orders.pop(oid,None);_d=max(.0,float(_4.get("maker_rebate_ps")or.0));P=round(max(.01,N-_d),6);O={}
    for _c,_Y in BANKROLL_TICKETS.items():_i=_Y[_Q];_b=_i/N;sh=round(min(_b,l),4);_X=round(sh*P,2);O[_c]={"filled":True,"best_ask":round(u,4),"vwap":N,"eff_px":P,"slip_cents":.0,"spent_usd":_X,"fee_usd":round(-sh*_d,4),"shares":sh,"fill_ratio":round(min(1.,_X/max(.01,_i)),4),"l1_usd":_7.get("l1_bid_usd",50.),"levels":1}
    _E=f"{_Q}_{int(now)}_{_7['dedupe_key'][-10:]}"
    if z or A or _Q in("BOND1_UMA_RESOLUTION_CARRY","SP2_NBA_ENDGAME_LOCK"):t=None
    elif _Q in("W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK"):t=.985
    elif x:t=min(.95,round(max(N+.07,e-.015),4))
    else:t=min(.96,round(N+.05,4))
    if j:_4["adverse_fill_during_cancel_window"]=True;_4["adverse_trigger"]=b
    pos={"position_id":_E,"dedupe_key":_7["dedupe_key"],"sleeve":_Q,"asset_or_city":_6,"title":_7["title"],"side":_s,"token_id":tok,"fee_rate":.0,"entry_ts":now,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":_t,"p_model_entry":round(e,4),"entry_eff_px_t1000":P,"entry_vwap_t1000":N,"realized_edge_t1000":round(e-P,4),"entry_best_bid":N,"last_bid":N,"maker_tp_px":t,"tier_fills":O,"extra":_4,"status":"OPEN"};d.open_positions[_E]=pos;d._append_ledger({"event":"SHADOW_ENTRY",**pos});_D=f"${t:.3f}"if t is not None else"HOLD_SETTLE";logger.info(f"[MAKER_FILLED:{_Q}] {_6} | {pos['title']} ({_s}) @ resting=${N:.3f} -> TP={_D} (p_mod={e:.3f}, adverse={j})")
 async def scan_weather_markets(c,opps_out):
  from src.polymarket_research.riskless_protocol_v2_expansion import resolve_weather_effective_end_ts as d;_Q=datetime.now(timezone.utc);_ae=time.time();w=[]
  for sp0 in list(c.weather_events.values()):
   _ad=d(sp0,_ae+86400.)
   if _ad<=_ae:c.weather_events.pop(sp0.event_id,None);continue
   try:_G=_Q.astimezone(safe_zoneinfo(sp0.tz_name))
   except Exception:_G=_Q
   if(sp0.obs_date-_G.date()).days>1 and not c.single_scan:continue
   w.append((0 if _G.date()>=sp0.obs_date else 1,_ad,sp0))
  w.sort(key=lambda r:(r[0],r[1]))
  for _,_,sp in w[:45]:
   _ac=time.time();F=d(sp,_ac+86400.)
   if F<=_ac:c.weather_events.pop(sp.event_id,None);continue
   _h=not c.single_scan and is_shadow_sleeve_quarantined("W2_ENSEMBLE_VALUE")and is_shadow_sleeve_quarantined("W2_MAKER_OVERROUND")
   if _h:
    try:o=_Q.astimezone(safe_zoneinfo(sp.tz_name))
    except Exception:o=_Q
    n=o.date()>=sp.obs_date
   else:n=True
   if _h and not n:_P=max(1,len(sp.buckets));_e=[round(1./_P,4)]*len(sp.buckets);_4={"is_solar_lock":False,"locked_bucket_idx":None,"p_locked_bucket":.0,"obs_count":0,"latest_temp_c":None,"running_ext_c":None,"peak_iqr_c":None,"cooling_cushion_c":.0,"convective_cold_pool":False,"probs":_e}
   else:
    _ab=f"{sp.icao}_{sp.obs_date.isoformat()}";_F=c.metar_cache.get(_ab);_s=compute_adaptive_metar_poll_ttl(sp.icao,_F[1]if _F else None,_Q)
    if _F is None or(_ac-_F[0])>=_s:G=await asyncio.to_thread(fetch_metar_observations_sync,sp.icao,sp.obs_date,sp.tz_name);c.metar_cache[_ab]=(_ac,G)
    else:G=_F[1]
    _g=c.taf_cache.get(_ab)
    if _g is None or(_ac-_g[0])>=1800.:v=await asyncio.to_thread(fetch_taf_extremes_sync,sp.icao,sp.obs_date,sp.tz_name);c.taf_cache[_ab]=(_ac,v)
    else:v=_g[1]
    _E=c.ensemble_cache.get(sp.icao);_O=1500. if(_E and _E[1])else 60.
    if _E is None or(_ac-_E[0])>=_O:
     async with c._open_meteo_sem:_f=await asyncio.to_thread(fetch_live_ensemble_hourly_sync,sp.lat,sp.lon);await asyncio.sleep(.18)
     c.ensemble_cache[sp.icao]=(_ac,_f)
    else:_f=_E[1]
    if not _f and not G:continue
    _4=compute_weather_probabilities(sp,_Q,G,_f,forecast_sigma_base_c=c.weather_sigma_c,taf_extreme_c=(v or{}).get(sp.metric));_e=_4["probs"]
   F=d(sp,_ac+86400.)
   if _4["is_solar_lock"]and _4["locked_bucket_idx"]is not None:
    _3=sp.buckets[_4["locked_bucket_idx"]];_2=_4["p_locked_bucket"];_1=float(getattr(_3,"fee_rate",.0)or.0);P=sp.metric=="LOW";_r="W1_LOW_TROUGH_LOCK"if P else"W1_SOLAR_PEAK_LOCK";_d=.96 if P else.94;O=.03 if P else.035;_N=f"W1LOW_{sp.event_id}_{_3.market_id}"if P else f"W1_{sp.event_id}_{_3.market_id}";bk=await c.fetch_json(f"{CLOB_URL}/book?token_id={_3.yes_token}",timeout=3.5)
    if bk:
     R=walk_l2_book_asks_depth_capped(bk.get("asks")or[],BANKROLL_TICKETS["T1000"][_r],BANKROLL_TICKETS["T100"][_r],fee_rate=_1,min_l1_usd=(15. if P else 20.),max_ask_px=_d+1e-4);_0,_c=extract_best_bid(bk.get("bids")or[]);c._record_market_telemetry(key=f"W1_LOCK_{sp.event_id}_{_3.market_id}",min_interval_sec=45.,now_ts=_ac,sig=(R.get("eff_px"),_0,round(float(_2),3)),payload={"type":"WEATHER_SOLAR_LOCK_SNAP","sleeve":_r,"event_id":sp.event_id,"city":sp.city,"icao":sp.icao,"metric":sp.metric,"obs_date":sp.obs_date.isoformat(),"bucket":_3.label,"obs_count":_4["obs_count"],"running_ext_c":_4["running_ext_c"],"cushion_c":_4["cooling_cushion_c"],"p_lock":_2,"ask_eff":R.get("eff_px")if R.get("filled")else None,"bid":_0 if _0>0 else None,"l1_usd":R.get("l1_usd",.0)});_D={"event_id":sp.event_id,"market_id":_3.market_id,"condition_id":_3.condition_id,"opp_token_id":_3.no_token,"icao":sp.icao,"metric":sp.metric,"obs_date":sp.obs_date.isoformat(),"bucket_label":_3.label,"running_ext_c":_4["running_ext_c"],"cooling_cushion_c":_4["cooling_cushion_c"]};p=False
     if R.get("filled")and.52<=R["eff_px"]<=_d:
      _t=_2-R["eff_px"];opps_out.append({"sleeve":_r,"market":f"{sp.city} ({sp.icao}) {sp.metric} {sp.obs_date} -> {_3.label}","ask_vwap":R["eff_px"],"p_model":_2,"net_edge":round(_t,4),"l1_usd":R["l1_usd"]})
      if _t>=O:
       _aa=getattr(_3,"neg_risk",None);E=GLOBAL_GOVERNANCE_MANAGER.snapshot;N=bool((E.get("directional")or{}).get("riskless_only_mode",False)or(E.get("riskless_boxes")or{}).get("strict_pure_riskless_mode",False));e=True
       if N:
        try:g=datetime.fromtimestamp(_ac,tz=safe_zoneinfo(sp.tz_name)).date()
        except Exception:g=sp.obs_date
        _b=(c.by_sleeve.get(_r)if hasattr(c,"by_sleeve")else None)or{};e=(g>sp.obs_date and int(_4.get("rem_hours_count",1)or 0)==0 and not bool(_4.get("has_corrected_obs"))and not bool(_4.get("has_oracle_contradiction"))and int(_b.get("losses",0)or 0)==0 and float(_2)>=1.)
       if(e and float(_2)>=(1. if N else.985)and _aa is not None and(F-_ac)<=86400.):_q=await c.fetch_json(f"{CLOB_URL}/book?token_id={_3.no_token}",timeout=2.5);c.emit_live_single_leg_lock_candidate(sleeve_source=_r,asset=f"{sp.city}_{sp.icao}",dedupe_key=_N,token_id=_3.yes_token,opp_token_id=_3.no_token,market_id=_3.market_id,condition_id=_3.condition_id,side_label="YES",display_label=f"{sp.city} {sp.metric} [{_3.label}]",bk_win=bk,bk_opp=_q if isinstance(_q,dict)else None,fee_rate=_1,fee_exponent=1.,neg_risk=bool(_aa),close_ts=F,now_ts=_ac,max_lock_eff_px=_d,max_opp_bid=.045,hold_to_maturity=True,p_model=float(_2))
       p=await c.open_shadow_position(sleeve=_r,dedupe_key=_N,asset_or_city=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_3.label}]",side_label="YES",token_id=_3.yes_token,fee_rate=_1,p_model=_2,close_ts=F,extra=_D,prefetched_book=bk)
     if(not p and not _4.get("convective_cold_pool")and(F-_ac)>9e2 and.25<=_0<=_d and(_2-_0)>=O):
      _p=await c.post_shadow_maker_entry(sleeve=_r,dedupe_key=_N,asset=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_3.label}]",side_label="YES",token_id=_3.yes_token,p_model=_2,close_ts=F,extra=_D,prefetched_book=bk)
      if _p and not R.get("filled"):opps_out.append({"sleeve":_r,"market":f"[MAKER] {sp.city} ({sp.icao}) {sp.metric} {sp.obs_date} -> {_3.label}","ask_vwap":_0,"p_model":_2,"net_edge":round(_2-_0,4),"l1_usd":_c,"close_ts":F})
   _o=f"W3_SLATE_{sp.event_id}";M=float(c._last_w3_slate_chk_ts.get(sp.event_id)or.0);L=45. if(sp.series_slug in HIGH_VOLUME_WEATHER_SERIES or(F-_ac)<=21600.)else 120.
   if(_o not in c.entered_keys and _o not in c.inflight_keys and len(sp.buckets)>=3 and(c.single_scan or(_ac-M)>=L)):
    c._last_w3_slate_chk_ts[sp.event_id]=_ac;_Z=[b_i.yes_token for b_i in sp.buckets]+[b_i.no_token for b_i in sp.buckets];_C=await c.fetch_books_batch(_Z,timeout=3.);t={};k={}
    for b_i in sp.buckets:
     _aj=_C.get(b_i.yes_token);_Y=_C.get(b_i.no_token);_9={}
     if _aj:
      k[b_i.market_id]=_aj;_X=sorted([(float(a["price"]),float(a["size"]))for a in(_aj.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
      if _X:_9["ask_yes"]=_X[0][0];_9["ask_yes_shares"]=_X[0][1]
     if _Y:
      _W=sorted([(float(a["price"]),float(a["size"]))for a in(_Y.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0],key=lambda x:x[0])
      if _W:_9["ask_no"]=_W[0][0];_9["ask_no_shares"]=_W[0][1]
     if _9:t[b_i.market_id]=_9
     if(_Y and int(_4.get("obs_count")or 0)>=1 and _4.get("running_ext_c")is not None and not _4.get("has_corrected_obs")and not _4.get("has_oracle_contradiction")and not(int(_4.get("rem_hours_count",0)or 0)>0 and _4.get("has_maintenance_obs"))and(F-_ac)>3e2):
      from src.polymarket_research.riskless_protocol_v2_expansion import classify_weather_station_oracle_rule as f;K=f(sp.icao,unit=b_i.unit,rules_text=str(getattr(sp,"rules_text","")or""));_a=float(_4["running_ext_c"]);_B=(.55 if(bool(K.get("prefer_body_integer_c"))or int(_4.get("rem_hours_count",0)or 0)>0)else.05);J=celsius_to_market_int(_a-_B,b_i.unit);Z=celsius_to_market_int(_a+_B,b_i.unit);_n=((sp.metric=="HIGH"and b_i.high_bound<=J-2)or(sp.metric=="LOW"and b_i.low_bound>=Z+2))
      if _n:
       _V,_=extract_best_bid(_Y.get("bids")or[]);_U=float(_9.get("ask_no",1.)or 1.);l=False
       if float(getattr(b_i,"rewards_min_size",.0)or.0)>.0:
        _ai=evaluate_locked_market_reward_carry(1.,_V,_U,float(b_i.rewards_min_size),float(b_i.rewards_max_spread),float(getattr(b_i,"fee_rate",.0)or.0))
        if _ai.get("eligible"):
         opps_out.append({"sleeve":"MKR_REWARD_LOCKED_CARRY","market":f"{sp.city} ({sp.icao}) Dead NO[{b_i.label}] @ ${_ai['resting_bid']:.3f}","ask_vwap":_ai["resting_bid"],"p_model":1.,"net_edge":_ai["carry_edge"],"l1_usd":50.,"close_ts":F});await c.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY",f"MKR_RW_W_{b_i.market_id}",f"{sp.city}_{sp.icao}",f"{sp.title} [Dead NO {b_i.label}]","NO",b_i.no_token,1.,F,{"market_id":b_i.market_id,"condition_id":b_i.condition_id,"opp_token_id":b_i.yes_token,"resting_bid_override":_ai["resting_bid"]},prefetched_book=_Y)
         if(is_reward_locked_carry_live_ready(c,1.,min_reward_shares=float(b_i.rewards_min_size or.0),resting_bid_px=float(_ai["resting_bid"]))and getattr(b_i,"neg_risk",None)is not None and _aj is not None):_A=max(.0,float(getattr(b_i,"fee_rate",.0)or.0));_z=max(1.,float(getattr(b_i,"fee_exponent",1.)or 1.));_y=float(_ai["resting_bid"]);_m=round(.2*_A*((_y*(1.-_y))**_z),5)if _A>.0 else.0;l=bool(c.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_REWARD_LOCKED_CARRY",asset=f"{sp.city}_{sp.icao}",dedupe_key=f"MKR_RW_W_{b_i.market_id}",pair_dedupe_key=f"MKR_RW_WPAIR_{b_i.market_id}",token_id=b_i.no_token,opp_token_id=b_i.yes_token,market_id=b_i.market_id,condition_id=b_i.condition_id,side_label="NO",display_label=f"{sp.city} Reward Carry NO[{b_i.label}]",bk_win=_Y,bk_opp=_aj,neg_risk=bool(b_i.neg_risk),close_ts=float(F),now_ts=_ac,min_resting_bid=.94,max_resting_bid=.994,min_maker_edge=.006,max_opp_bid=.03,hold_to_maturity=True,p_model=1.,target_bid_px=_y,maker_rebate_ps=_m,event_id=str(sp.event_id)))
       q=getattr(b_i,"question_index",None)
       if q is None and sp.event_id:
        _M=getattr(c,"negrisk_convert_slates",{}).get(str(sp.event_id))
        if _M is not None:
         for _8 in getattr(_M,"brackets",()):
          if(str(_8.get("market_id")or"")==str(b_i.market_id)or(b_i.condition_id and str(_8.get("condition_id")or"")==str(b_i.condition_id)))and _8.get("question_index")is not None:q=int(_8["question_index"]);break
       if q is not None and sp.event_id:c.__dict__.setdefault("_ws_dead_q_by_event",{}).setdefault(str(sp.event_id),set()).add(int(q))
       if(not c.single_scan and getattr(b_i,"neg_risk",None)is not None and _aj is not None and 120.<=(F-_ac)<=28800.):
        I=c.__dict__.setdefault("_last_wprune_ws_reg_ts",{})
        if(_ac-float(I.get(b_i.market_id,.0)or.0))>=180.:I[b_i.market_id]=_ac;from src.polymarket_research.riskless_protocol_v2_expansion import _write_and_notify_live_cand as h;h(c,{"box_id":f"CLINCH_WS_WPRUNE_{b_i.market_id}","dedupe_key":f"W_PRUNE1_{b_i.market_id}","pair_dedupe_key":f"W_PRUNE1_MKR_{b_i.market_id}","box_type":"CLINCH_WATCHLIST_REG","ts_unix":round(_ac,3),"asset":f"{sp.city}_{sp.icao}","event_id":str(sp.event_id),"sleeve_source":"W_PRUNE1_DEAD_NO_BOND","expiry_ts":float(F),"rem_hours_count":int(_4.get("rem_hours_count",0)or 0),"max_box_cost_net":.994,"max_opp_bid":.025,"hold_to_maturity":True,"p_model":1.,"leg_a_token_id":str(b_i.no_token),"leg_a_opp_token_id":str(b_i.yes_token),"leg_a_label":f"{sp.city} Dead NO [{b_i.label}]","leg_a_side":"NO","leg_a_market_id":str(b_i.market_id),"leg_a_condition_id":str(b_i.condition_id),"leg_a_fee_rate":max(.0,float(getattr(b_i,"fee_rate",.0)or.0)),"leg_a_fee_exponent":max(1.,float(getattr(b_i,"fee_exponent",1.)or 1.)),"leg_a_neg_risk":bool(b_i.neg_risk),"ws_books":{str(b_i.no_token):{"bids":(_Y.get("bids")or[])[:10],"asks":(_Y.get("asks")or[])[:10]},str(b_i.yes_token):{"bids":(_aj.get("bids")or[])[:10],"asks":(_aj.get("asks")or[])[:10]}},"ws_books_ts":round(_ac,3)},getattr(c,"d1_live_candidates_file",D1_LIVE_CANDIDATES_FILE),D1_LIVE_CANDIDATES_FILE)
        Y=.995 if(F-_ac)<=1.2e4 else.994;D=round(1.-Y,4)
        if not l and(F-_ac)<=28800. and.94<=_V<=Y:c.emit_live_single_leg_maker_lock_candidate(sleeve_source="W_PRUNE1_DEAD_NO_BOND",asset=f"{sp.city}_{sp.icao}",dedupe_key=f"W_PRUNE1_MKR_{b_i.market_id}",pair_dedupe_key=f"W_PRUNE1_{b_i.market_id}",token_id=b_i.no_token,opp_token_id=b_i.yes_token,market_id=b_i.market_id,condition_id=b_i.condition_id,side_label="NO",display_label=f"{sp.city} Dead NO [{b_i.label}]",bk_win=_Y,bk_opp=_aj,neg_risk=bool(b_i.neg_risk),close_ts=float(F),now_ts=_ac,min_resting_bid=.94,max_resting_bid=Y,min_maker_edge=D,max_opp_bid=.025,hold_to_maturity=True,p_model=1.,event_id=str(sp.event_id))
     if _aj and _Y and float(getattr(b_i,"fee_rate",.0)or.0)==.0:
      _ah=scan_binary_complete_set_arb(market_id=b_i.market_id,condition_id=b_i.condition_id,yes_token=b_i.yes_token,no_token=b_i.no_token,asks_yes_raw=_aj.get("asks")or[],asks_no_raw=_Y.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],fee_rate=.0,max_box_cost_net=.995)
      if _ah.get("filled"):
       opps_out.append({"sleeve":"C1_BINARY_COMPLETE_SET","market":f"{sp.city} ({sp.icao}) Complete-Set [{b_i.label}]","ask_vwap":_ah["box_cost_net"],"p_model":1.,"net_edge":_ah["riskless_floor_per_pair"],"l1_usd":_ah["l1_usd"],"close_ts":F});X=getattr(b_i,"neg_risk",None);_L={"token_id":b_i.yes_token,"opp_token_id":b_i.no_token,"condition_id":b_i.condition_id,"side":"YES","label":"YES","market_id":b_i.market_id,"fee_rate":.0,"strike":1e2,"neg_risk":bool(X)};_K={"token_id":b_i.no_token,"opp_token_id":b_i.yes_token,"condition_id":b_i.condition_id,"side":"NO","label":"NO","market_id":b_i.market_id,"fee_rate":.0,"strike":1e2,"neg_risk":bool(X)};await c.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key=f"C1_W_{b_i.market_id}",asset=f"{sp.city}_{sp.icao}",title=f"{sp.city} YES+NO Complete Set [{b_i.label}]",leg_a=_L,leg_b=_K,bk_a=_aj,bk_b=_Y,close_ts=F,max_box_cost_net=.995,extra={"is_complete_set":True,"market_id":b_i.market_id,"condition_id":b_i.condition_id})
       if X is not None and(F-_ac)<=86400. and float(_ah["box_cost_net"])<=.99:c.emit_live_two_leg_box_candidate(sleeve_source="C1_BINARY_COMPLETE_SET",box_type="COMPLETE_SET",asset=f"{sp.city}_{sp.icao}",dedupe_key=f"C1_W_{b_i.market_id}",leg_a=_L,leg_b=_K,bk_a=_aj,bk_b=_Y,close_ts=float(F),now_ts=_ac)
    _x=evaluate_weather_event_slate(sp,_e,t,target_budget_usd=BANKROLL_TICKETS["T1000"]["W3_WEATHER_SLATE_ARB"]);_w=_x.get("full_slate_arb")
    if len(t)==len(sp.buckets):_l=all(t[b.market_id].get("ask_yes",0)>0 for b in sp.buckets);_k=all(t[b.market_id].get("ask_no",0)>0 for b in sp.buckets);_v=round(sum(float(t[b.market_id]["ask_yes"])for b in sp.buckets),4)if _l else None;_u=round(sum(float(t[b.market_id]["ask_no"])for b in sp.buckets),4)if _k else None;_J=max(range(len(sp.buckets)),key=lambda idx_b:float(_e[idx_b]))if _e else 0;_I=sp.buckets[_J]if sp.buckets else None;_j=float(t[_I.market_id].get("ask_yes")or.0)if _I else.0;c._record_market_telemetry(key=f"W_SLATE_{sp.event_id}",min_interval_sec=45. if(F-_ac)<=7200. else 90.,now_ts=_ac,sig=(_v,_u,_4["running_ext_c"],round(_j,3),(_w or{}).get("mode")),payload={"type":"WEATHER_SLATE","event_id":sp.event_id,"city":sp.city,"icao":sp.icao,"metric":sp.metric,"obs_date":sp.obs_date.isoformat(),"n_buckets":len(sp.buckets),"tte_sec":round(F-_ac,0),"obs_count":_4["obs_count"],"latest_c":_4["latest_temp_c"],"running_ext_c":_4["running_ext_c"],"ens_iqr_c":_4["peak_iqr_c"],"solar_lock":_4["is_solar_lock"],"top_bucket":_I.label if _I else None,"top_p":round(float(_e[_J]),4)if _e else None,"top_ask_yes":round(_j,4)if _j>0 else None,"sum_yes_l1":_v,"sum_no_l1":_u,"no_payout":len(sp.buckets)-1,"arb_mode":(_w or{}).get("mode")})
    if _w:_ag=float(_w.get("guaranteed_payout_per_set")or 1.);opps_out.append({"sleeve":"W3_WEATHER_SLATE_ARB","market":f"{sp.city} ({sp.icao}) {sp.obs_date} Full-Slate ({len(sp.buckets)} buckets, {_w.get('side','ALL_BUCKETS_YES')})","ask_vwap":round(float(_w["sum_asks"])/_ag,4),"p_model":1.,"net_edge":round(float(_w["guaranteed_edge_per_set"])/_ag,4),"l1_usd":_w["total_cost_usd"]});await c.open_shadow_weather_slate(sp,_w,F)
    if all(b.market_id in k for b in sp.buckets):await c.execute_ctf_overround_mint_sell(dedupe_key=f"CTF_OVR_W_{sp.event_id}",asset=f"{sp.city}_{sp.icao}",title=f"{sp.city} {sp.obs_date} Weather NegRisk Overround Mint-Sell",legs_bids_spec=[{"bids":k[b.market_id].get("bids")or[],"fee_rate":float(getattr(b,"fee_rate",.0)or.0),"fee_exponent":1.}for b in sp.buckets],close_ts=F,min_net_proceeds_per_set=1.004,opps_out=opps_out,extra={"overround_kind":"WEATHER_NEGRISK","event_id":sp.event_id})
   else:k={}
   if is_shadow_sleeve_quarantined("W2_ENSEMBLE_VALUE")and is_shadow_sleeve_quarantined("W2_MAKER_OVERROUND"):continue
   z=int(_4.get("ensemble_member_count")or 0);W=float(_4.get("peak_iqr_c")or.0);u=f"W2_EVENT_{sp.event_id}"in c.entered_keys or f"W2_EVENT_{sp.event_id}"in c.inflight_keys;s=f"W2M_EVENT_{sp.event_id}"in c.entered_keys or f"W2M_EVENT_{sp.event_id}"in c.inflight_keys;m=None;j=None;H=sorted(range(len(_e)),key=lambda i:-_e[i])[:2]
   for idx in H:
    _7=_e[idx]
    if _7<.24:continue
    b=sp.buckets[idx];_6=float(getattr(b,"fee_rate",.0)or.0);bk=k.get(b.market_id)or await c.fetch_json(f"{CLOB_URL}/book?token_id={b.yes_token}",timeout=3.5)
    if not bk:continue
    V=bk.get("asks")or[];U=bk.get("bids")or[];T,C=extract_best_bid(U);B=[float(a["price"])for a in V if float(a.get("price",0))>0 and float(a.get("size",0))>0]
    if _6==.0 and B and T>0 and(min(B)-T)>=.02:
     S=round(min(B),4);y=round(min(T+.01,S-.01),4);A=_7-y
     if.14<=y<=.65 and A>=.055 and z>=50 and C>=10.:opps_out.append({"sleeve":"W2_MAKER_OVERROUND","market":f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label} [MakerBid]","ask_vwap":y,"p_model":round(_7,4),"net_edge":round(A,4),"l1_usd":C})
     if(not u and not s and(F-_ac)>=5400. and z>=50 and W<=2.2 and not _4.get("convective_cold_pool")and C>=10. and.14<=y<=.62 and _7>=.3 and A>=.085):
      if j is None or A>j[0]:j=(A,_7,y,b,bk)
    R=walk_l2_book_asks(V,50.,fee_rate=_6)
    if not R.get("filled"):continue
    _T=R["eff_px"];_t=_7-_T
    if.1<=_T<=.62 and _t>=.04 and z>=50:opps_out.append({"sleeve":"W2_ENSEMBLE_VALUE","market":f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label}","ask_vwap":_T,"p_model":round(_7,4),"net_edge":round(_t,4),"l1_usd":R["l1_usd"]})
    if(not u and not s and z>=50 and W<=2.2 and not _4.get("convective_cold_pool")and.16<=_T<=.62 and _7>=.34 and _t>=.095):
     if m is None or _t>m[0]:m=(_t,_7,_T,b,bk)
   if m is not None and os.getenv("PM_DISABLE_SHADOW_W2_TAKER","0")!="1":_,Q,_,_S,_H=m;await c.open_shadow_position(sleeve="W2_ENSEMBLE_VALUE",dedupe_key=f"W2_{sp.event_id}_{_S.market_id}",asset_or_city=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_S.label}]",side_label="YES",token_id=_S.yes_token,fee_rate=float(getattr(_S,"fee_rate",.0)or.0),p_model=Q,close_ts=F,extra={"event_id":sp.event_id,"market_id":_S.market_id,"condition_id":_S.condition_id,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket_label":_S.label,"bias_c":_4["bias_c"],"ensemble_members":z,"peak_iqr_c":W},prefetched_book=_H)
   elif j is not None:_,_i,_,_5,_R=j;await c.post_shadow_maker_entry(sleeve="W2_MAKER_OVERROUND",dedupe_key=f"W2M_{sp.event_id}_{_5.market_id}",asset=f"{sp.city}_{sp.icao}",title=f"{sp.title} [{_5.label}]",side_label="YES",token_id=_5.yes_token,p_model=_i,close_ts=F,extra={"execution_mode":"POST_ONLY_WEATHER_MAKER_ZERO_FEE","event_id":sp.event_id,"market_id":_5.market_id,"condition_id":_5.condition_id,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket_label":_5.label,"bias_c":_4["bias_c"],"ensemble_members":z,"peak_iqr_c":W},prefetched_book=_R)
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
  _h=time.time();Z=asyncio.get_running_loop();b=[sp for sp in[*a.daily_updown_markets.values(),*a.pyth_daily_markets.values()]if sp.end_ts>_h+60.]
  if b:
   A=await a.fetch_books_batch([sp.up_token for sp in b]+[sp.down_token for sp in b],timeout=3.)
   for J in b:
    Y=A.get(J.up_token);X=A.get(J.down_token)
    if not Y or not X:continue
    W,V=a._best_ask_sz(Y);U,T=a._best_ask_sz(X)
    if W<1. and U<1.:_g=float(J.fee_rate);a._record_market_telemetry(key=f"DAILY_C1_{J.market_id}",min_interval_sec=60.,now_ts=_h,sig=(W,U),payload={"type":"DAILY_COMPLETE_SET","asset":J.asset,"market_id":J.market_id,"title":J.title,"fee_rate":_g,"tte_sec":round(J.end_ts-_h,0),"up_ask":W,"down_ask":U,"gross_sum_l1":round(W+U,4),"net_sum_l1":round(W+U+_g*(W*(1.-W)+U*(1.-U)),4),"l1_min_shares":round(min(V,T),2)})
    z=.995 if J.fee_rate==.0 else.994;y=scan_binary_complete_set_arb(market_id=J.market_id,condition_id=J.condition_id,yes_token=J.up_token,no_token=J.down_token,asks_yes_raw=Y.get("asks")or[],asks_no_raw=X.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],fee_rate=J.fee_rate,max_box_cost_net=z)
    if y.get("filled"):
     opps_out.append({"sleeve":"C1_BINARY_COMPLETE_SET","market":f"{J.asset} Complete-Set {J.title}","ask_vwap":y["box_cost_net"],"p_model":1.,"net_edge":y["riskless_floor_per_pair"],"l1_usd":y["l1_usd"],"close_ts":J.end_ts});I={"token_id":J.up_token,"opp_token_id":J.down_token,"condition_id":J.condition_id,"side":"UP","label":"UP","market_id":J.market_id,"fee_rate":J.fee_rate,"strike":1e2};H={"token_id":J.down_token,"opp_token_id":J.up_token,"condition_id":J.condition_id,"side":"DOWN","label":"DOWN","market_id":J.market_id,"fee_rate":J.fee_rate,"strike":1e2};await a.open_shadow_two_leg_box(sleeve="C1_BINARY_COMPLETE_SET",dedupe_key=f"C1_D_{J.market_id}",asset=J.asset,title=f"{J.asset} UP+DOWN Complete Set: {J.title}",leg_a=I,leg_b=H,bk_a=Y,bk_b=X,close_ts=J.end_ts,max_box_cost_net=z,extra={"is_complete_set":True,"market_id":J.market_id,"condition_id":J.condition_id})
     if(J.end_ts-_h)<=86400. and float(y["box_cost_net"])<=(.99 if J.fee_rate==.0 else.988):a.emit_live_two_leg_box_candidate(sleeve_source="C1_BINARY_COMPLETE_SET",box_type="COMPLETE_SET",asset=J.asset,dedupe_key=f"C1_D_{J.market_id}",leg_a=I,leg_b=H,bk_a=Y,bk_b=X,close_ts=float(J.end_ts),now_ts=_h)
    await a.execute_ctf_overround_mint_sell(dedupe_key=f"CTF_OVR_D_{J.market_id}",asset=J.asset,title=f"{J.asset} Binary Overround Mint-Sell: {J.title}",legs_bids_spec=[{"bids":Y.get("bids")or[],"fee_rate":J.fee_rate,"fee_exponent":1.},{"bids":X.get("bids")or[],"fee_rate":J.fee_rate,"fee_exponent":1.}],close_ts=J.end_ts,min_net_proceeds_per_set=1.003 if J.fee_rate==.0 else 1.004,opps_out=opps_out,extra={"overround_kind":"BINARY_DAILY","market_id":J.market_id,"condition_id":J.condition_id})
  for _,S in list(a.hourly_12pm_markets.items()):
   G=S.end_ts-_h
   if not(60.<=G<=3540.)or _h<S.start_ts+20.:continue
   x=f"H1_{S.asset}_{int(S.start_ts)}";R=a.daily_open_cache.get(x)
   if R is None:
    w=await Z.run_in_executor(None,fetch_binance_window_extremes_sync,S.asset,S.start_ts-60.,S.start_ts+60.,"1m")
    if w is not None and w[2]>0:a.daily_open_cache[x]=(S.end_ts,float(w[2]));n=float(w[2])
    else:continue
   else:n=R[1]
   g=[]
   for Q in a.daily_updown_markets.values():
    if Q.asset==S.asset and abs(Q.end_ts-S.end_ts)<=5.:
     v=f"{Q.asset}_{int(Q.start_ts)}";P=a.daily_open_cache.get(v)
     if P is None:
      u=await Z.run_in_executor(None,fetch_binance_window_extremes_sync,Q.asset,Q.start_ts-60.,Q.start_ts+60.,"1m")
      if u is not None and u[2]>0:a.daily_open_cache[v]=(Q.end_ts,float(u[2]));i=float(u[2])
      else:i=.0
     else:i=P[1]
     if i>0:g.append({"market_id":Q.market_id,"condition_id":Q.condition_id,"end_ts":Q.end_ts,"strike":i,"is_downward":False,"yes_token":Q.up_token,"no_token":Q.down_token,"yes_label":"UP","no_label":"DOWN","fee_rate":Q.fee_rate})
   for m in a.strike_ladders.values():
    if m and m[0].asset==S.asset and abs(m[0].end_ts-S.end_ts)<=5.:
     for F in m:
      if not F.is_downward:g.append({"market_id":F.market_id,"condition_id":F.condition_id,"end_ts":F.end_ts,"strike":F.strike,"is_downward":False,"yes_token":F.yes_token,"no_token":F.no_token,"yes_label":"YES","no_label":"NO","fee_rate":CRYPTO_FEE_RATE})
   l=detect_d2_12pm_binance_boxes({"asset":S.asset,"market_id":S.market_id,"condition_id":S.condition_id,"end_ts":S.end_ts,"up_token":S.up_token,"down_token":S.down_token,"fee_rate":S.fee_rate},n,g)
   if l:
    p=sorted({str(c["leg_a"]["token_id"])for c in l}|{str(c["leg_b"]["token_id"])for c in l});t=await a.fetch_books_batch(p,timeout=3.)
    for dc in l:
     _f,_e=dc["leg_a"],dc["leg_b"];O,N=t.get(str(_f["token_id"])),t.get(str(_e["token_id"]))
     if not O or not N:continue
     _d,_=a._best_ask_sz(O);_c,_=a._best_ask_sz(N)
     if _d<1. and _c<1.:a._record_market_telemetry(key=f"D2_12PM_{_f['market_id']}_{_e['market_id']}",min_interval_sec=30.,now_ts=_h,sig=(_d,_c),payload={"type":"D2_12PM_CORRIDOR","asset":S.asset,"tte_sec":round(G,0),"k_low":dc["k_low"],"k_high":dc["k_high"],"corridor_bps":dc["corridor_bps"],"gross_box_l1":round(_d+_c,4),"label":dc["label"]})
     M=walk_equal_shares_dominance_box(O.get("asks")or[],N.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["D2_12PM_BINANCE_BOX"],fee_rate_a=float(_f["fee_rate"]),fee_rate_b=float(_e["fee_rate"]),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
     if M.get("filled"):opps_out.append({"sleeve":"D2_12PM_BINANCE_BOX","market":f"{S.asset} 12PM Box {dc['label']}","ask_vwap":round(float(M["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(M["box_cost_net"]),4),"l1_usd":M["l1_usd"],"close_ts":dc["close_ts"]});await a.open_shadow_two_leg_box(sleeve="D2_12PM_BINANCE_BOX",dedupe_key=f"D2_{_f['market_id']}_{_e['market_id']}",asset=S.asset,title=f"{S.asset} 12PM Binance Box {dc['label']}",leg_a=_f,leg_b=_e,bk_a=O,bk_b=N,close_ts=float(dc["close_ts"]),max_box_cost_net=.99,extra={"is_d2_12pm_box":True,"k_low":dc["k_low"],"k_high":dc["k_high"],"corridor_bps":dc["corridor_bps"]})
  for _,sp in list(a.daily_updown_markets.items()):
   _b=sp.end_ts-_h
   if not(120.<=_b<=5400.):continue
   L=a.spots.get(sp.asset,.0)
   if L<=.0:continue
   E=f"{sp.asset}_{int(sp.start_ts)}";k=a.daily_open_cache.get(E)
   if k is None:
    D=await Z.run_in_executor(None,fetch_binance_window_extremes_sync,sp.asset,sp.start_ts-60.,sp.start_ts+60.,"1m")
    if D is not None and D[2]>0:a.daily_open_cache[E]=(sp.end_ts,float(D[2]));d=float(D[2])
    else:continue
   else:d=k[1]
   s=evaluate_svi_digital_fair_value(sp.asset,L,d,_b,is_downward=False,now_ts=_h);j="UP"if L>d else"DOWN";r=float(s["p_yes"]if j=="UP"else s["p_no"]);C=abs(float(s.get("z_sigma")or.0))
   if C<1.8 or r<.93:continue
   o=a.get_return_bps(sp.asset,60.)
   if(j=="UP"and o<-10.)or(j=="DOWN"and o>10.):continue
   _a=sp.up_token if j=="UP"else sp.down_token;bk=await a.fetch_json(f"{CLOB_URL}/book?token_id={_a}",timeout=3.)
   if not bk:continue
   B=walk_l2_book_asks(bk.get("asks")or[],BANKROLL_TICKETS["T1000"]["U1_DAILY_UPDOWN_LOCK"],fee_rate=sp.fee_rate)
   if not B.get("filled"):continue
   q=float(B["eff_px"]);K=r-q
   if.66<=B["vwap"]<=.9 and K>=.025:opps_out.append({"sleeve":"U1_DAILY_UPDOWN_LOCK","market":f"{sp.asset} {sp.title} ({j}, TTE={_b/60:.0f}m, z={C:.2f})","ask_vwap":q,"p_model":round(r,4),"net_edge":round(K,4),"l1_usd":B["l1_usd"],"close_ts":sp.end_ts})
   if.66<=B["vwap"]<=.9 and K>=.042:
    f=sp.down_token if j=="UP"else sp.up_token;e=bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional",{}).get("riskless_only_mode",False))
    if C>=2.2 and r>=(.999 if e else.965):h=await a.fetch_json(f"{CLOB_URL}/book?token_id={f}",timeout=2.5);a.emit_live_single_leg_lock_candidate(sleeve_source="U1_DAILY_UPDOWN_LOCK",asset=sp.asset,dedupe_key=f"U1_{sp.market_id}_{j}",token_id=_a,opp_token_id=f,market_id=sp.market_id,condition_id=sp.condition_id,side_label=j,display_label=f"{sp.asset} Daily {j}",bk_win=bk,bk_opp=h if isinstance(h,dict)else None,fee_rate=sp.fee_rate,fee_exponent=1.,neg_risk=False,close_ts=sp.end_ts,now_ts=_h,max_lock_eff_px=.9,max_opp_bid=.36,hold_to_maturity=False,p_model=float(r))
    await a.open_shadow_position(sleeve="U1_DAILY_UPDOWN_LOCK",dedupe_key=f"U1_{sp.market_id}_{j}",asset_or_city=sp.asset,title=sp.title,side_label=j,token_id=_a,fee_rate=sp.fee_rate,p_model=r,close_ts=sp.end_ts,extra={"market_id":sp.market_id,"condition_id":sp.condition_id,"strike":d,"is_downward":(j=="DOWN"),"z_sigma":C},tp_target_px=.98,prefetched_book=bk)
 @staticmethod
 def is_in_same_oracle_overlap_window(now_ts):from src.polymarket_research.riskless_protocol_v2_expansion import compute_min_4h_boundary_rem_sec as a;b=math.ceil(now_ts/9e2)*9e2;c=b-now_ts;e=math.ceil(now_ts/3600.)*3600.-now_ts;d=a(now_ts);return(8.<=c<=305.)or(8.<=e<=905.)or(8.<=d<=905.)
 async def discover_dominance_pairs(b,now_ts=None):
  s=float(now_ts if now_ts is not None else time.time())
  for r,(n,_)in list(b.dominance_pairs.items()):
   if n.end_ts<s-6e2:b.dominance_pairs.pop(r,None)
  for f,(h,_)in list(b.chainlink_open_cache.items()):
   if h<s-6e2:b.chainlink_open_cache.pop(f,None)
  o=b.__dict__.get("_strike_source")or{}
  for f,(h,_)in list(o.items()):
   if h<s-6e2:o.pop(f,None)
  for f,q in list(b._strike_fail_backoff_ts.items()):
   if float(q or.0)<s-7200.:b._strike_fail_backoff_ts.pop(f,None)
  i=int(math.ceil(s/9e2)*900);l=float(i)-s;g=b.single_scan or("fetch_json"in b.__dict__);e=(i%3600)==0 and(5.<=l<=905.);j=305. if g else 335.
  if not(5.<=l<=j)and not(e and not g):return
  k=datetime.fromtimestamp(s-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  async def d(asset):
   v=f"{asset}_{i}"
   if v in b.dominance_pairs:return
   B=DOMINANCE_SERIES_SLUGS[asset];u,x=await asyncio.gather(b.fetch_json(f"{GAMMA_URL}/events?series_slug={B['15m']}&closed=false&end_date_min={k}&order=endDate&ascending=true&limit=3",timeout=4.),b.fetch_json(f"{GAMMA_URL}/events?series_slug={B['5m']}&closed=false&end_date_min={k}&order=endDate&ascending=true&limit=3",timeout=4.));a=None;m=None
   if isinstance(u,list):
    for D in u:
     E=parse_twap_candle_event(D,asset,"15m")
     if E and abs(E.end_ts-i)<=2.:a=E;break
   if isinstance(x,list):
    for D in x:
     F=parse_twap_candle_event(D,asset,"5m")
     if F and abs(F.end_ts-i)<=2.:m=F;break
   if(a is None or m is None)and not g:
    if a is None:
     A=build_deterministic_updown_event_slug(asset,"15m",i)
     if A:
      t=await b.fetch_json(f"{GAMMA_URL}/events?slug={A}",timeout=3.5)
      if isinstance(t,list)and t:
       y=parse_twap_candle_event(t[0],asset,"15m")
       if y and abs(y.end_ts-i)<=2.:a=y
    if m is None:
     C=build_deterministic_updown_event_slug(asset,"5m",i)
     if C:
      w=await b.fetch_json(f"{GAMMA_URL}/events?slug={C}",timeout=3.5)
      if isinstance(w,list)and w:
       z=parse_twap_candle_event(w[0],asset,"5m")
       if z and abs(z.end_ts-i)<=2.:m=z
   if a and m and verify_same_oracle_pair(a,m):b.dominance_pairs[v]=(a,m)
  async def c(metal):
   v=f"{metal}_1h15m_{i}"
   if v in b.dominance_pairs:return
   w=METAL_DOMINANCE_SERIES_SLUGS[metal];u,t=await asyncio.gather(b.fetch_json(f"{GAMMA_URL}/events?series_slug={w['1h']}&closed=false&end_date_min={k}&order=endDate&ascending=true&limit=3",timeout=4.),b.fetch_json(f"{GAMMA_URL}/events?series_slug={w['15m']}&closed=false&end_date_min={k}&order=endDate&ascending=true&limit=3",timeout=4.));m=None;a=None
   if isinstance(u,list):
    for y in u:
     z=parse_metal_forex_candle_event(y,metal,"1h")
     if z and abs(z.end_ts-i)<=2.:m=z;break
   if isinstance(t,list):
    for y in t:
     x=parse_metal_forex_candle_event(y,metal,"15m")
     if x and abs(x.end_ts-i)<=2.:a=x;break
   if m and a and verify_same_oracle_pair(m,a):b.dominance_pairs[v]=(m,a)
  p=[]
  if 5.<=l<=j:p.extend(d(a)for a in DOMINANCE_ASSETS)
  if e and(not g or os.getenv("PM_FORCE_METAL_D1_TEST")=="1"):p.extend(c(m)for m in METAL_DOMINANCE_ASSETS)
  if p:await asyncio.gather(*p)
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
  C=str(leg_a.get("opp_token_id")or"");B=str(leg_b.get("opp_token_id")or"")
  if not C or not B:return False
  h=(prefetched_books or{}).get(C);g=(prefetched_books or{}).get(B)
  if not(isinstance(h,dict)and isinstance(g,dict)):h,g=await asyncio.gather(a.fetch_json(f"{CLOB_URL}/book?token_id={C}",timeout=3.),a.fetch_json(f"{CLOB_URL}/book?token_id={B}",timeout=3.))
  if not(isinstance(h,dict)and isinstance(g,dict)):return False
  t,_=extract_best_bid(h.get("bids")or[]);s,_=extract_best_bid(g.get("bids")or[]);r,_=a._best_ask_sz(h);q,_=a._best_ask_sz(g);j=str(leg_a.get("token_id")or"");i=str(leg_b.get("token_id")or"");A=(prefetched_books or{}).get(j)if j else None;z=(prefetched_books or{}).get(i)if i else None;p,_=extract_best_bid(A.get("bids")or[])if isinstance(A,dict)else(.0,.0);o,_=extract_best_bid(z.get("bids")or[])if isinstance(z,dict)else(.0,.0);n,_=a._best_ask_sz(A)if isinstance(A,dict)else(.0,.0);m,_=a._best_ask_sz(z)if isinstance(z,dict)else(.0,.0);e=isinstance(A,dict)and p>=.88 and(.0<n<=.999);d=isinstance(z,dict)and o>=.88 and(.0<m<=.999);y=t>.0 or(.0<r<=.12)or e;x=s>.0 or(.0<q<=.12)or d;w=(t if t>.0 else(min(r,round(1.-p,4))if(e and r>.0)else(round(1.-p,4)if e else r)));v=(s if s>.0 else(min(q,round(1.-o,4))if(d and q>.0)else(round(1.-o,4)if d else q)));f=w+v
  if isinstance(A,dict)and isinstance(z,dict):c=((n>.0 and t>.0 and(n+t)>1.015)or(m>.0 and s>.0 and(m+s)>1.015)or(t+s)>1.16 or f>1.18)
  else:c=(t+s)>1. or f>1.035
  b=(t<=.0 and s<=.0)and not(e or d)
  if not(y and x)or b or c:
   l=a.__dict__.setdefault("_anti_box_warn_ts",{});u=f"{C}:{B}";k=time.time()
   if(k-float(l.get(u,.0)))>=30.:
    if len(l)>512:l.clear()
    l[u]=k;logger.warning(f"[ANTI-BOX VETO] Rejected box {leg_a.get('label')}+{leg_b.get('label')}: complement bids={t:.3f}+{s:.3f}={t+s:.3f} (ub={f:.3f}, unverified or > 1.00)")
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
  v="D1"if sleeve_override=="D1_SAME_ORACLE_DOMINANCE_BOX"else sleeve_override.split("_")[0]+"_"+sleeve_override.split("_")[1];k=f"{v}_{asset}_{m15.market_id}_{m5.market_id}";F=a._try_acquire_keys(k)
  if not F:return False
  try:
   C=dom_info["leg_a"];B=dom_info["leg_b"]
   if prefetched_books is not None:o,n=prefetched_books
   else:await asyncio.sleep(.05);o,n=await asyncio.gather(a.fetch_json(f"{CLOB_URL}/book?token_id={C['token_id']}",timeout=3.),a.fetch_json(f"{CLOB_URL}/book?token_id={B['token_id']}",timeout=3.))
   if not o or not n:return False
   u=o.get("asks")or[];t=n.get("asks")or[];A,_=extract_best_bid(o.get("bids")or[]);z,_=extract_best_bid(n.get("bids")or[]);c=a._strike_is_rest_verified(m15)and a._strike_is_rest_verified(m5);g=.86 if c else.9;f=walk_equal_shares_dominance_box(u,t,target_budget_usd=BANKROLL_TICKETS["T1000"][sleeve_override],fee_rate_a=float(C["fee_rate"]),fee_rate_b=float(B["fee_rate"]),fee_exponent_a=float(C["fee_exponent"]),fee_exponent_b=float(B["fee_exponent"]),max_box_cost_net=max_box_cost_override,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=g)
   if not f.get("filled")and sleeve_override=="D1_4H_DOMINANCE_BOX":f=walk_equal_shares_dominance_box(u,t,target_budget_usd=BANKROLL_TICKETS["T100"][sleeve_override],fee_rate_a=float(C["fee_rate"]),fee_rate_b=float(B["fee_rate"]),fee_exponent_a=float(C["fee_exponent"]),fee_exponent_b=float(B["fee_exponent"]),max_box_cost_net=max_box_cost_override,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=g)
   if not f.get("filled"):return False
   h=("4h"in(str(m15.horizon).lower(),str(m5.horizon).lower()))and(str(m15.horizon).lower()!=str(m5.horizon).lower());d=compute_d1_legging_drag_haircut(shares=float(f["shares"]),box_cost_net=float(f["box_cost_net"]),avail_a_shares=float(f["avail_a_shares"]),avail_b_shares=float(f["avail_b_shares"]),px_a=float(f["leg_a_walk"]["worst_px"]),px_b=float(f["leg_b_walk"]["worst_px"]),fee_rate_a=float(C["fee_rate"]),fee_rate_b=float(B["fee_rate"]),is_4h_mixed=h)
   if d["legging_adjusted_net_ev_per_pair"]<=.0 and sleeve_override=="D1_4H_DOMINANCE_BOX":
    j=min(float(f["avail_a_shares"]),float(f["avail_b_shares"]));e=min(float(BANKROLL_TICKETS["T100"][sleeve_override]),max(8.,math.floor(j/2.3)*float(f["box_cost_net"])));s=walk_equal_shares_dominance_box(u,t,target_budget_usd=e,fee_rate_a=float(C["fee_rate"]),fee_rate_b=float(B["fee_rate"]),fee_exponent_a=float(C["fee_exponent"]),fee_exponent_b=float(B["fee_exponent"]),max_box_cost_net=max_box_cost_override,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=g)
    if s.get("filled"):
     m=compute_d1_legging_drag_haircut(shares=float(s["shares"]),box_cost_net=float(s["box_cost_net"]),avail_a_shares=float(s["avail_a_shares"]),avail_b_shares=float(s["avail_b_shares"]),px_a=float(s["leg_a_walk"]["worst_px"]),px_b=float(s["leg_b_walk"]["worst_px"]),fee_rate_a=float(C["fee_rate"]),fee_rate_b=float(B["fee_rate"]),is_4h_mixed=h)
     if m["legging_adjusted_net_ev_per_pair"]>.0:f=s;d=m
   if d["legging_adjusted_net_ev_per_pair"]<=.0:logger.info(f"[SHADOW LEGGING PARITY REJECT] {asset} {sleeve_override}: box_net=${f['box_cost_net']:.4f} depth_mult={d['min_depth_mult']:.2f}x drag={d['legging_drag_per_pair']:.4f}/pair -> adj_ev={d['legging_adjusted_net_ev_per_pair']:+.4f}/pair <= 0");return False
   i={};b={}
   for l,y in BANKROLL_TICKETS.items():
    r=walk_equal_shares_dominance_box(u,t,target_budget_usd=y[sleeve_override],fee_rate_a=float(C["fee_rate"]),fee_rate_b=float(B["fee_rate"]),fee_exponent_a=float(C["fee_exponent"]),fee_exponent_b=float(B["fee_exponent"]),max_box_cost_net=max_box_cost_override,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=g)
    if sleeve_override=="D1_4H_DOMINANCE_BOX"and(not r.get("filled")or float(r.get("shares")or.0)>float(f.get("shares")or.0)):r=dict(f)
    if r.get("filled"):i[l]=r;p=compute_d1_legging_drag_haircut(shares=float(r["shares"]),box_cost_net=float(r["box_cost_net"]),avail_a_shares=float(r["avail_a_shares"]),avail_b_shares=float(r["avail_b_shares"]),px_a=float(r["leg_a_walk"]["worst_px"]),px_b=float(r["leg_b_walk"]["worst_px"]),fee_rate_a=float(C["fee_rate"]),fee_rate_b=float(B["fee_rate"]),is_4h_mixed=h);b[l]=float(p["legging_drag_usd"])
   if"T1000"not in i:return False
   E=time.time();q=f"{sleeve_override}_{int(E)}_{m5.market_id[-6:]}";x=f"{asset} {dom_info['regime']} [{dom_info['k_low']:.4f} .. {dom_info['k_high']:.4f}]";D={"position_id":q,"dedupe_key":k,"sleeve":sleeve_override,"asset_or_city":asset,"title":x,"side":f"{C['label']}+{B['label']}","token_id":f"{C['token_id']}|{B['token_id']}","fee_rate":float(C["fee_rate"]),"entry_ts":E,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":m5.end_ts,"p_model_entry":1.,"entry_eff_px_t1000":f["eff_px"],"entry_vwap_t1000":f["vwap"],"realized_edge_t1000":f["riskless_floor_per_pair"],"legging_adjusted_edge_t1000":d["legging_adjusted_net_ev_per_pair"],"entry_best_bid":round(A+z,4),"last_bid":round(A+z,4),"maker_tp_px":None,"tier_fills":i,"extra":{"is_dominance_box":True,"regime":dom_info["regime"],"k_low":dom_info["k_low"],"k_high":dom_info["k_high"],"corridor_bps":dom_info["corridor_bps"],"m15_horizon":m15.horizon,"m15_market_id":m15.market_id,"m15_start_iso":m15.start_iso,"m15_end_iso":m15.end_iso,"m5_horizon":m5.horizon,"m5_market_id":m5.market_id,"leg_a":C,"leg_b":B,"legging_drag_ref":d,"legging_drag_usd_by_tier":b},"status":"OPEN"};a.open_positions[q]=D
   for w in F:a.entered_keys.add(w)
   a._append_ledger({"event":"SHADOW_ENTRY",**D});logger.info(f"[ENTRY:{sleeve_override}] {x} | {f['shares']} pairs @ net=${f['eff_px']:.4f} (floor=${f['riskless_floor_per_pair']:+.4f}/pair, min_profit=${f['guaranteed_min_profit_usd']:+.2f})");return True
  finally:a._release_inflight_keys(F)
 def _d1_live_max_box_cost(self,*,zero_fee=False,rem_tte_sec=None):
  a=.985
  try:
   f=Path(os.getenv("POLYMARKET_RISK_CONFIG",str(PROJECT_ROOT/"config/polymarket_risk_config.json")));e=json.loads(f.read_text(encoding="utf-8"));v=float(e.get("d1_max_box_cost_net",.985))
   if.86<=v<=.995:a=v
  except Exception:pass
  if zero_fee:
   d=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{});c=float(d.get("d1_short_tte_threshold_sec",180.));b=min(.995,max(.985,float(d.get("d1_short_tte_max_box_cost_net",.9925))))
   if rem_tte_sec is not None and.0<float(rem_tte_sec)<=c:return max(a,b)
   return max(a,.99)
  return a
 @staticmethod
 def resolve_2026_maker_rebate_share(asset_str,sleeve_str=""):
  b=str(asset_str or"").strip().upper();a=str(sleeve_str or"").strip().upper()
  if b in{"BTC","ETH","SOL","XRP","DOGE","BNB","HYPE","ZEC"}or a.startswith("CRY_"):return.2
  if(a.startswith(("SP","CL1","TEN1","AFF1","SOC","NFL_","API1","ESPORTS","DC1","LP_COMP1"))or b in{"NBA","NFL","NHL","MLB","EPL","UCL","ATP","WTA","SOCCER","ESPORTS","CS2","LOL","DOTA2","VALORANT"}):return.15
  return.25
 @staticmethod
 def compute_live_8e_clinch_max_eff_px(max_eff_base,p_lock,rem_sec):
  b=float(max_eff_base)
  if float(p_lock)<.999:return b
  a=float(rem_sec)
  if.0<a<=3600.:return max(b,.994)
  if.0<a<=14400.:return max(b,.992)
  return b
 def emit_live_d1_box_candidate(a,m15,m5,dom_info,w_live,now_ts,*,is_quiet_book=False,sleeve_source="D1_SAME_ORACLE_DOMINANCE_BOX"):
  c=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==c:return False
  if not(a.single_scan or("fetch_json"in a.__dict__)):
   now_ts=time.time()
   if float(m5.end_ts-now_ts)<16.:return False
  i=f"{m15.asset}_{m15.market_id}_{m5.market_id}";g=float(a._last_d1_live_emit_ts.get(i,.0)or.0)
  if(now_ts-g)<10.:return False
  n=dom_info["leg_a"];m=dom_info["leg_b"];q=w_live["leg_a_walk"];p=w_live["leg_b_walk"];d=("4h"in(str(m15.horizon).lower(),str(m5.horizon).lower()))and(str(m15.horizon).lower()!=str(m5.horizon).lower());f=compute_d1_legging_drag_haircut(shares=float(w_live["shares"]),box_cost_net=float(w_live["box_cost_net"]),avail_a_shares=float(w_live["avail_a_shares"]),avail_b_shares=float(w_live["avail_b_shares"]),px_a=float(q["worst_px"]),px_b=float(p["worst_px"]),fee_rate_a=float(n["fee_rate"]),fee_rate_b=float(m["fee_rate"]),is_4h_mixed=d)
  if f["legging_adjusted_net_ev_per_pair"]<=.0:return False
  a._last_d1_live_emit_ts[i]=now_ts
  for l,k in list(a._last_d1_live_emit_ts.items()):
   if(now_ts-k)>1200.:a._last_d1_live_emit_ts.pop(l,None)
  j="D1_4H_LIVE"if str(m15.horizon).lower()=="4h"else"D1_LIVE";h=max(float(n["fee_rate"]),float(m["fee_rate"]))==.0;e=float(m5.end_ts-now_ts);o={"box_id":f"{j}_{m15.asset}_{int(m5.end_ts)}_{m5.market_id[-5:]}","dedupe_key":f"D1_{m15.asset}_{m15.market_id}_{m5.market_id}","ts_unix":round(now_ts,3),"asset":m15.asset,"regime":dom_info["regime"],"pair_horizons":f"{m15.horizon}_{m5.horizon}","sleeve_source":str(sleeve_source),"is_quiet_book":bool(is_quiet_book),"k_low":dom_info["k_low"],"k_high":dom_info["k_high"],"corridor_bps":dom_info["corridor_bps"],"expiry_ts":float(m5.end_ts),"rem_sec":round(e,2),"shares":int(w_live["shares"]),"net_paired_shares":float(w_live.get("net_paired_shares",w_live["shares"])),"leg_a_gross_shares":float(w_live.get("leg_a_gross_shares",w_live["shares"])),"leg_b_gross_shares":float(w_live.get("leg_b_gross_shares",w_live["shares"])),"box_cost_net":float(w_live["box_cost_net"]),"legging_drag_per_pair":f["legging_drag_per_pair"],"legging_adjusted_net_ev_per_pair":f["legging_adjusted_net_ev_per_pair"],"max_box_cost_net":a._d1_live_max_box_cost(zero_fee=h,rem_tte_sec=e),"leg_a_token_id":str(n["token_id"]),"leg_a_opp_token_id":str(n.get("opp_token_id")or""),"leg_a_label":str(n["label"]),"leg_a_side":str(n["side"]),"leg_a_horizon":str(n["horizon"]),"leg_a_market_id":str(n["market_id"]),"leg_a_condition_id":str(n["condition_id"]),"leg_a_strike":float(n["strike"]),"leg_a_limit_price":float(q["worst_px"]),"leg_a_avail_shares":float(w_live["avail_a_shares"]),"leg_a_fee_rate":float(n["fee_rate"]),"leg_a_fee_exponent":float(n["fee_exponent"]),"leg_a_neg_risk":bool(n["neg_risk"]),"leg_b_token_id":str(m["token_id"]),"leg_b_opp_token_id":str(m.get("opp_token_id")or""),"leg_b_label":str(m["label"]),"leg_b_side":str(m["side"]),"leg_b_horizon":str(m["horizon"]),"leg_b_market_id":str(m["market_id"]),"leg_b_condition_id":str(m["condition_id"]),"leg_b_strike":float(m["strike"]),"leg_b_limit_price":float(p["worst_px"]),"leg_b_avail_shares":float(w_live["avail_b_shares"]),"leg_b_fee_rate":float(m["fee_rate"]),"leg_b_fee_exponent":float(m["fee_exponent"]),"leg_b_neg_risk":bool(m["neg_risk"])};from src.polymarket_research.riskless_protocol_v2_expansion import attach_ws_books_and_write_d1_cand as b;return a._record_live_bridge_emit(sleeve_source,b(a,o,n,m,D1_LIVE_CANDIDATES_FILE,c))
 def _record_live_bridge_emit(a,sleeve_source,ok):
  if ok:a._live_bridge_emits_total=int(getattr(a,"_live_bridge_emits_total",0)or 0)+1;b=a.__dict__.setdefault("_live_bridge_emits_by_sleeve",{});c=str(sleeve_source or"UNKNOWN");b[c]=int(b.get(c,0)or 0)+1;a._live_bridge_last_emit_ts=round(time.time(),3)
  return bool(ok)
 def emit_live_two_leg_box_candidate(a,*,sleeve_source,box_type,asset,dedupe_key,leg_a,leg_b,bk_a,bk_b,close_ts,now_ts,k_low=1e2,k_high=1e2,max_box_cost_override=None,extra_fields=None):
  e=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl"
  if STATE_FILE!=(DATA_DIR/"alpha124_shadow_state.json")and D1_LIVE_CANDIDATES_FILE==e:return False
  if not(a.single_scan or("fetch_json"in a.__dict__)):now_ts=time.time()
  r=float(close_ts-now_ts)
  if r<25.:return False
  m=float(a._last_d1_live_emit_ts.get(dedupe_key,.0)or.0)
  if(now_ts-m)<15.:return False
  D=float(leg_a.get("fee_rate",CRYPTO_FEE_RATE));C=float(leg_b.get("fee_rate",CRYPTO_FEE_RATE));B=float(leg_a.get("fee_exponent",1.));A=float(leg_b.get("fee_exponent",1.));j=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{});d=(box_type=="COMPLETE_SET"and sleeve_source=="C1_BINARY_COMPLETE_SET"and max(D,C)==.0 and not bool(leg_a.get("neg_risk"))and not bool(leg_b.get("neg_risk"))and bool(str(leg_a.get("condition_id")or"").strip())and str(leg_a.get("condition_id")or"").strip()==str(leg_b.get("condition_id")or"").strip()and bool(j.get("enable_zerofee1_mergeable_sweeper",True))and bool(j.get("enable_c1_gasless_batch_merge",True)))
  if sleeve_source=="COND1_MACRO_PARTITION_BOX":b=(.992 if r<=1.08e5 else.988)if a.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX")else.985
  elif box_type=="BARRIER_MONO":b=.993
  elif d:b=round(1.-max(.001,float(j.get("zerofee1_min_net_edge_bps",15.)or 15.)/1e4),4)
  elif max(D,C)==.0 and(a.is_sleeve_grad8_ready(sleeve_source)or a._can_emit_zero_loss_math_live(sleeve_source,close_ts,now_ts))and r<=(604800. if sleeve_source in{"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION"}else 172800.):b=.992
  else:b=.99 if max(D,C)==.0 else.988
  if max_box_cost_override is not None:b=min(.999 if d else b,float(max_box_cost_override))
  w=walk_equal_shares_dominance_box(bk_a.get("asks")or[],bk_b.get("asks")or[],target_budget_usd=20.,fee_rate_a=D,fee_rate_b=C,fee_exponent_a=B,fee_exponent_b=A,max_box_cost_net=b,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.86)
  if not w.get("filled"):return False
  if len(a._last_d1_live_emit_ts)>256:a._last_d1_live_emit_ts={k:v for k,v in a._last_d1_live_emit_ts.items()if(now_ts-float(v))<=1200.}
  a._last_d1_live_emit_ts[dedupe_key]=now_ts;G=w["leg_a_walk"];F=w["leg_b_walk"];z,_=a._best_ask_sz(bk_a);y,_=a._best_ask_sz(bk_b);u,_=extract_best_bid(bk_a.get("bids")or[]);t,_=extract_best_bid(bk_b.get("bids")or[]);l=bool(u>.0 and t>.0 and(z-u)<=.041 and(y-t)<=.041 and(max(D,C)==.0 or(now_ts-float(a._last_any_shock_ts_by_asset.get(str(asset),.0)or.0))>=4.));p=round(abs(k_high-k_low)/max(1e-9,k_low)*1e4,2)if k_low>0 else.0;E={"box_id":f"{box_type}_LIVE_{asset}_{int(close_ts)}_{str(leg_a.get('market_id','0'))[-5:]}","dedupe_key":dedupe_key,"box_type":str(box_type),"ts_unix":round(now_ts,3),"asset":str(asset),"regime":f"{box_type}_{leg_a.get('label','A')}_PLUS_{leg_b.get('label','B')}","pair_horizons":str(box_type).lower(),"sleeve_source":str(sleeve_source),"is_quiet_book":l,"k_low":float(k_low),"k_high":float(k_high),"corridor_bps":p,"expiry_ts":float(close_ts),"rem_sec":round(r,2),"shares":int(w["shares"]),"net_paired_shares":float(w.get("net_paired_shares",w["shares"])),"leg_a_gross_shares":float(w.get("leg_a_gross_shares",w["shares"])),"leg_b_gross_shares":float(w.get("leg_b_gross_shares",w["shares"])),"box_cost_net":float(w["box_cost_net"]),"max_box_cost_net":b,"leg_a_token_id":str(leg_a["token_id"]),"leg_a_opp_token_id":str(leg_a.get("opp_token_id")or""),"leg_a_label":str(leg_a.get("label")or leg_a.get("side")or"YES"),"leg_a_side":str(leg_a.get("side")or"YES"),"leg_a_horizon":str(leg_a.get("horizon")or box_type.lower()),"leg_a_market_id":str(leg_a.get("market_id")or""),"leg_a_condition_id":str(leg_a.get("condition_id")or""),"leg_a_strike":float(leg_a.get("strike")or k_low),"leg_a_limit_price":float(G["worst_px"]),"leg_a_avail_shares":float(w["avail_a_shares"]),"leg_a_fee_rate":D,"leg_a_fee_exponent":B,"leg_a_neg_risk":bool(leg_a["neg_risk"])if isinstance(leg_a.get("neg_risk"),bool)else False,"leg_a_expiry_ts":float(leg_a.get("end_ts")or close_ts),"leg_b_token_id":str(leg_b["token_id"]),"leg_b_opp_token_id":str(leg_b.get("opp_token_id")or""),"leg_b_label":str(leg_b.get("label")or leg_b.get("side")or"NO"),"leg_b_side":str(leg_b.get("side")or"NO"),"leg_b_horizon":str(leg_b.get("horizon")or box_type.lower()),"leg_b_market_id":str(leg_b.get("market_id")or""),"leg_b_condition_id":str(leg_b.get("condition_id")or""),"leg_b_strike":float(leg_b.get("strike")or k_high),"leg_b_limit_price":float(F["worst_px"]),"leg_b_avail_shares":float(w["avail_b_shares"]),"leg_b_fee_rate":C,"leg_b_fee_exponent":A,"leg_b_neg_risk":bool(leg_b["neg_risk"])if isinstance(leg_b.get("neg_risk"),bool)else False,"leg_b_expiry_ts":float(leg_b.get("end_ts")or close_ts)}
  if isinstance(extra_fields,dict):E.update(extra_fields)
  if not a.single_scan and a._ws_books:
   o=[str(leg_a["token_id"]),str(leg_b["token_id"])]
   if str(box_type)!="COMPLETE_SET":
    for x in(str(leg_a.get("opp_token_id")or""),str(leg_b.get("opp_token_id")or"")):
     if x:o.append(x)
   n={str(leg_a["token_id"]),str(leg_b["token_id"])};f=getattr(a,"_ws_rest_seeded",set())
   if all(t_x in a._ws_books and t_x not in f and(now_ts-a._ws_books[t_x][0])<=2.5 and bool(a._ws_books[t_x][1].get("asks"))and(t_x not in n or bool(a._ws_books[t_x][1].get("bids")or a._ws_books[t_x][1].get("asks")))for t_x in o):E["ws_books"]={t_x:{"bids":(a._ws_books[t_x][1].get("bids")or[])[:12],"asks":(a._ws_books[t_x][1].get("asks")or[])[:12]}for t_x in o};E["ws_books_ts"]=round(min(a._ws_books[t_x][0]for t_x in o),3)
  try:
   try:import orjson as _orj;i=_orj.dumps(E)+b"\n";g=i.decode("utf-8")
   except Exception:g=json.dumps(E,separators=(",",":"))+"\n";i=g.encode("utf-8")
   if os.name!="nt"and D1_LIVE_CANDIDATES_FILE==e:
    if not str(D1_LIVE_CANDIDATES_FILE).startswith("/tmp/")and not a.single_scan:
     from src.polymarket_research.stage_c_zero_loss_velocity import evaluate_strict_pure_riskless_candidate as c;q,_=c(E,GLOBAL_GOVERNANCE_MANAGER.snapshot)
     if not q:return False
    try:
     import socket;h=getattr(a,"_d1_ipc_sock",None)
     if h is None:h=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);h.setblocking(False);a._d1_ipc_sock=h
     s=os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify");h.sendto(i,f"\x00{s}".encode("utf-8"))
    except Exception:pass
   D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True,exist_ok=True)
   with open(D1_LIVE_CANDIDATES_FILE,"a",encoding="utf-8")as H:H.write(g)
   return a._record_live_bridge_emit(sleeve_source,True)
  except Exception:return False
 def emit_live_single_leg_lock_candidate(b,*,sleeve_source,asset,dedupe_key,token_id,opp_token_id,market_id,condition_id,side_label,display_label,bk_win,bk_opp,fee_rate,fee_exponent,neg_risk,close_ts,now_ts,max_lock_eff_px,max_opp_bid=.025,hold_to_maturity=False,p_model=1.,event_id="",pair_dedupe_key=""):from src.polymarket_research.riskless_protocol_v2_expansion import emit_single_leg_lock_cand_impl as a;return b._record_live_bridge_emit(sleeve_source,a(b,sleeve_source=sleeve_source,asset=asset,dedupe_key=dedupe_key,token_id=token_id,opp_token_id=opp_token_id,market_id=market_id,condition_id=condition_id,side_label=side_label,display_label=display_label,bk_win=bk_win,bk_opp=bk_opp,fee_rate=fee_rate,fee_exponent=fee_exponent,neg_risk=neg_risk,close_ts=close_ts,now_ts=now_ts,max_lock_eff_px=max_lock_eff_px,max_opp_bid=max_opp_bid,hold_to_maturity=hold_to_maturity,p_model=p_model,extract_best_bid_fn=extract_best_bid,walk_l2_fn=walk_l2_book_asks_depth_capped,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json",event_id=event_id,pair_dedupe_key=pair_dedupe_key))
 def emit_live_special_v2_box_candidate(b,*,box_type,sleeve_source,asset,dedupe_key,close_ts,now_ts,payload):from src.polymarket_research.riskless_protocol_v2_expansion import emit_special_v2_box_cand_impl as a;return b._record_live_bridge_emit(sleeve_source,a(b,box_type=box_type,sleeve_source=sleeve_source,asset=asset,dedupe_key=dedupe_key,close_ts=close_ts,now_ts=now_ts,payload=payload,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json"))
 def emit_live_negrisk_convert_candidate(b,*,sleeve_source,spec,dedupe_key,arb_hit,books_by_token,now_ts,fee_bips=0):from src.polymarket_research.riskless_protocol_v2_expansion import emit_negrisk_convert_cand_impl as a;return b._record_live_bridge_emit(sleeve_source,a(b,sleeve_source=sleeve_source,spec=spec,dedupe_key=dedupe_key,arb_hit=arb_hit,books_by_token=books_by_token,now_ts=now_ts,fee_bips=fee_bips,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json"))
 def emit_live_single_leg_maker_lock_candidate(b,*,sleeve_source,asset,dedupe_key,pair_dedupe_key,token_id,opp_token_id,market_id,condition_id,side_label,display_label,bk_win,bk_opp,neg_risk,close_ts,now_ts,min_resting_bid=.94,max_resting_bid=.994,min_maker_edge=.006,max_opp_bid=.008,hold_to_maturity=True,p_model=1.,target_bid_px=None,maker_rebate_ps=.0,event_id=""):from src.polymarket_research.riskless_protocol_v2_expansion import emit_single_leg_maker_lock_cand_impl as a;return b._record_live_bridge_emit(sleeve_source,a(b,sleeve_source=sleeve_source,asset=asset,dedupe_key=dedupe_key,pair_dedupe_key=pair_dedupe_key,token_id=token_id,opp_token_id=opp_token_id,market_id=market_id,condition_id=condition_id,side_label=side_label,display_label=display_label,bk_win=bk_win,bk_opp=bk_opp,neg_risk=neg_risk,close_ts=close_ts,now_ts=now_ts,min_resting_bid=min_resting_bid,max_resting_bid=max_resting_bid,min_maker_edge=min_maker_edge,max_opp_bid=max_opp_bid,hold_to_maturity=hold_to_maturity,p_model=p_model,target_bid_px=target_bid_px,maker_rebate_ps=maker_rebate_ps,extract_best_bid_fn=extract_best_bid,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json",event_id=event_id))
 def emit_live_maker_anchor_box_candidate(b,*,sleeve_source,box_type,asset,dedupe_key,regime,pair_horizons,leg_a,leg_b,anchor_is_a,queue_front,anchor_bid_px,hedge_limit_px,avail_a_shares,avail_b_shares,close_ts,now_ts,k_low=1e2,k_high=1e2,corridor_bps=.0,posted_spot=.0):from src.polymarket_research.riskless_protocol_v2_expansion import emit_maker_anchor_box_cand_impl as a;return b._record_live_bridge_emit(sleeve_source,a(b,sleeve_source=sleeve_source,box_type=box_type,asset=asset,dedupe_key=dedupe_key,regime=regime,pair_horizons=pair_horizons,leg_a=leg_a,leg_b=leg_b,anchor_is_a=anchor_is_a,queue_front=queue_front,anchor_bid_px=anchor_bid_px,hedge_limit_px=hedge_limit_px,avail_a_shares=avail_a_shares,avail_b_shares=avail_b_shares,close_ts=close_ts,now_ts=now_ts,k_low=k_low,k_high=k_high,corridor_bps=corridor_bps,posted_spot=posted_spot,crypto_fee_rate=CRYPTO_FEE_RATE,project_root=PROJECT_ROOT,cand_file=D1_LIVE_CANDIDATES_FILE,default_cand_path=LIVE_POLYMARKET_DIR/"d1_live_box_candidates.jsonl",state_file=STATE_FILE,default_state_path=DATA_DIR/"alpha124_shadow_state.json"))
 def _latest_spot_px(a,asset):
  b=a.usd_spot_hist.get(asset)
  if b and len(b)>0 and(time.time()-float(b[-1][0]))<=10. and float(b[-1][1])>.0:return float(b[-1][1])
  return float(a.spots.get(asset)or.0)
 def post_maker_anchor_candidate(c,m15,m5,dom_info,bk_a,bk_b,now_ts,*,live_emit_only=False):
  if is_shadow_sleeve_quarantined("D1_MAKER_ANCHOR_BOX"):return False
  O=m5.end_ts-now_ts;t=880. if str(m5.horizon)=="15m"else 295.
  if not(65.<=O<=t):return False
  s=c.get_return_bps(m15.asset,5.)
  if abs(s)>4.5:return False
  if(now_ts-float(c._last_any_shock_ts_by_asset.get(m15.asset,.0)or.0))<4.:return False
  _r=f"D1_MKR_{m15.asset}_{m15.market_id}_{m5.market_id}"
  if not live_emit_only and(_r in c.entered_keys or _r in c.pending_maker_anchors or _r in c.inflight_keys):return False
  _q,_p=dom_info["leg_a"],dom_info["leg_b"];_a=sorted([(float(b["price"]),float(b["size"]))for b in(bk_a.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);Z=sorted([(float(b["price"]),float(b["size"]))for b in(bk_b.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);Y=sorted([(float(a["price"]),float(a["size"]))for a in(bk_a.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);X=sorted([(float(a["price"]),float(a["size"]))for a in(bk_b.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0])
  if not Y or not X or not _a or not Z:return False
  _o,_n=_a[0];_m,_l=Z[0];_k,_u=Y[0];_j,_t=X[0];_i,_h=round(_k-_o,4),round(_j-_m,4);_g=(_n-_u)/max(1e-9,_n+_u);_f=(_l-_t)/max(1e-9,_l+_t);r=float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(m15.asset,40.));o=min(float(BANKROLL_TICKETS["T100"]["D1_MAKER_ANCHOR_BOX"]),r);q=max(5.,math.floor(o/.985));n=max(5.,math.floor(min(float(BANKROLL_TICKETS["T1000"]["D1_MAKER_ANCHOR_BOX"]),r)/.985))
  def d(p):p=round(float(p),4);return(math.floor((p+1e-9)*1e2)/1e2)if(.04+1e-9<p<.96-1e-9)else(math.floor((p+1e-9)*1e3)/1e3)
  w=[]
  for f in(True,False):
   _e=_o if f else _m;N=_n if f else _l;_d=_k if f else _j;_c=_i if f else _h;M=_g if f else _f;L=_q if f else _p;F=X if f else Y;K=_p if f else _q
   if not(.03<=_d<=.999)or M<-.35:continue
   E=str(L.get("side")or"UP").upper()
   if(E=="UP"and s<-2.2)or(E=="DOWN"and s>2.2):continue
   W=.001 if(_e>=.96 or _e<.04)else.01;V=.001 if(_d>.96 or _d<=.04)else.01;U=d(_e+W);_b=d(_d-V)
   if U<=_b+1e-9 and U>_e+1e-9:j=min(U,_b);g=True
   elif _c>=.01-1e-9 and.15<=_d<=.85 and M>=-.15 and N>=15.:j=d(_e);g=False
   else:continue
   C=sum(sz for px,sz in F if px<=F[0][0]+.01)
   if C<max(15.,2.5*q):continue
   T=F[0][0];J=float(K["fee_rate"])*((T*(1.-T))**float(K.get("fee_exponent",1.)));k=T+J;m=min(j,d(.988-k));v=round(_e-(W if g else.0),3)
   if m<v or m<=.02 or m>=_d:continue
   D=round(m+k,4);l=.86 if(c._strike_is_rest_verified(m15)and c._strike_is_rest_verified(m5))else.9
   if l<=D<=.988:w.append((D-(5e-4 if g else.0),f,g,m,round(k,4),q))
  if not w:
   if(not c.single_scan and _g>=-.15 and _f>=-.15 and c._strike_is_rest_verified(m15)and c._strike_is_rest_verified(m5)):
    from src.polymarket_research.riskless_machine_gun_engine import evaluate_d1_maker_rebate_anchor as e,read_shm_spot_age_ms as h;_s=c.usd_spot_hist.get(m15.asset);B=h(m15.asset,now_ts,max(.0,(now_ts-float(_s[-1][0]))*1e3)if(_s and len(_s)>0)else 999.);S=sum(sz for px,sz in Y if px<=_k+.01);R=sum(sz for px,sz in X if px<=_j+.01)
    for I in(True,False):
     Q=e(anchor_bid_px=_o if I else _m,anchor_ask_px=_k if I else _j,hedge_ask_px=_j if I else _k,hedge_avail_shares=R if I else S,req_shares=q,fee_rate=float((_p if I else _q).get("fee_rate",CRYPTO_FEE_RATE)),fee_exponent=float((_p if I else _q).get("fee_exponent",1.)),spot_age_ms=B)
     if Q.get("eligible"):A=c.emit_live_maker_anchor_box_candidate(sleeve_source="D1_REBATE_MACHINE_GUN",box_type="DOMINANCE_MAKER_ANCHOR",asset=m15.asset,dedupe_key=f"D1_REBMG_{m15.asset}_{m15.market_id}_{m5.market_id}",regime=str(dom_info["regime"]),pair_horizons=f"{m15.horizon}_{m5.horizon}",leg_a=_q,leg_b=_p,anchor_is_a=I,queue_front=True,anchor_bid_px=float(Q["anchor_bid_px"]),hedge_limit_px=float(_j if I else _k),avail_a_shares=S,avail_b_shares=R,close_ts=float(m5.end_ts),now_ts=now_ts,k_low=float(dom_info["k_low"]),k_high=float(dom_info["k_high"]),corridor_bps=float(dom_info["corridor_bps"]),posted_spot=c._latest_spot_px(m15.asset));return A if live_emit_only else False
   return False
  w.sort(key=lambda z:z[0]);_,f,g,m,k,P=w[0];y=c._latest_spot_px(m15.asset)
  if not live_emit_only:c.pending_maker_anchors[_r]={"dedupe_key":_r,"asset":m15.asset,"m15":m15,"m5":m5,"dom_info":dom_info,"anchor_is_a":f,"queue_front":g,"bid_px":m,"pair_est":round(m+k,4),"req_shares_t100":P,"req_shares_t1000":n,"posted_ts":now_ts,"posted_spot":y}
  H=sum(sz for px,sz in Y if px<=_k+.01);G=sum(sz for px,sz in X if px<=_j+.01);u=_j if f else _k;i=False
  if c._strike_is_rest_verified(m15)and c._strike_is_rest_verified(m5):i=c.emit_live_maker_anchor_box_candidate(sleeve_source="D1_MAKER_ANCHOR_BOX",box_type="DOMINANCE_MAKER_ANCHOR",asset=m15.asset,dedupe_key=_r,regime=str(dom_info["regime"]),pair_horizons=f"{m15.horizon}_{m5.horizon}",leg_a=_q,leg_b=_p,anchor_is_a=f,queue_front=g,anchor_bid_px=m,hedge_limit_px=u,avail_a_shares=H,avail_b_shares=G,close_ts=float(m5.end_ts),now_ts=now_ts,k_low=float(dom_info["k_low"]),k_high=float(dom_info["k_high"]),corridor_bps=float(dom_info["corridor_bps"]),posted_spot=y)
  if live_emit_only:return i
  logger.info(f"[MAKER_ANCHOR_POST] {m15.asset} {dom_info['regime']} | Resting post_only=${m:.3f} (qf={g}) + hedge_eff=${k:.4f} = ${m+k:.4f} (TTE={O:.0f}s)");return True
 async def manage_pending_maker_anchors(b,now_ts=None):
  if not b.pending_maker_anchors:return
  _p=float(now_ts if now_ts is not None else time.time());p=[]
  for st in b.pending_maker_anchors.values():di=st["dom_info"];p.extend([str(di["leg_a"]["token_id"]),str(di["leg_b"]["token_id"])])
  _o=await b.fetch_books_batch(p,timeout=2.5)
  for _f,st in list(b.pending_maker_anchors.items()):
   _n=st["m15"];m5=st["m5"];di=st["dom_info"];_e,_d=di["leg_a"],di["leg_b"];J=bool(st["anchor_is_a"]);T=bool(st.get("queue_front",True));S=_e if J else _d;R=_d if J else _e;_b=_o.get(str(S["token_id"]));_a=_o.get(str(R["token_id"]));Z=float(st["bid_px"]);Y=_p-float(st["posted_ts"]);Q=m5.end_ts-_p;I=(_b or{}).get("asks")or[];l=min((float(a["price"])for a in I if float(a.get("size",0))>0),default=1.);w=_b is not None and Y>=.35 and l<=Z
   if w:
    b.pending_maker_anchors.pop(_f,None);b.entered_keys.add(_f);H=sorted([(float(a["price"]),float(a["size"]))for a in((_a or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);X=H[0][0]if H else 1.;B=sum(sz for px,sz in H if px<=X+.01)if H else.0;P=float(R["fee_rate"])*((X*(1.-X))**float(R.get("fee_exponent",1.)))if X<1. else.0;G=round(Z+X+P,4);o=float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(_n.asset,1e2));O="4h"in(str(_n.horizon).lower(),str(m5.horizon).lower())
    if _a is not None and H and B>=5. and.9<=G<=.995:
     v={};k={};c=.0
     for j,u in BANKROLL_TICKETS.items():
      sh=max(5.,min(B,math.floor(min(u["D1_MAKER_ANCHOR_BOX"],o)/G)));_c=round(sh*P,4);N=round(sh*(Z+X),2);v[j]={"filled":True,"vwap":round(Z+X,4),"eff_px":G,"spent_usd":N,"fee_usd":_c,"shares":sh,"l1_usd":round(B*G,2)};dr=compute_d1_maker_anchor_drag_haircut(shares=sh,pair_eff=G,bid_anc=Z,hdg_px=X,hdg_avail_shares=B,fee_rate_anc=float(S.get("fee_rate",CRYPTO_FEE_RATE)),fee_exponent_anc=float(S.get("fee_exponent",1.)),queue_front=T,is_4h_mixed=O);k[j]=float(dr["legging_drag_usd"])
      if j=="T1000":c=float(dr["maker_rebate_20pct_est_usd"])
     A,_=extract_best_bid((_o.get(str(_e["token_id"]))or{}).get("bids")or[]);z,_=extract_best_bid((_o.get(str(_d["token_id"]))or{}).get("bids")or[]);h=("D1_4H_DOMINANCE_BOX"if(O and not is_shadow_sleeve_quarantined("D1_4H_DOMINANCE_BOX"))else"D1_MAKER_ANCHOR_BOX");W=f"{h}_{int(_p)}_{m5.market_id[-6:]}";_m={"position_id":W,"dedupe_key":_f,"sleeve":h,"asset_or_city":_n.asset,"title":f"{_n.asset} {di['regime']} [0%-Fee Maker Anchor @ ${Z:.3f}]","side":f"{_e['label']}+{_d['label']}","token_id":f"{_e['token_id']}|{_d['token_id']}","fee_rate":float(R["fee_rate"]),"entry_ts":_p,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":m5.end_ts,"p_model_entry":1.,"entry_eff_px_t1000":G,"entry_vwap_t1000":round(Z+X,4),"realized_edge_t1000":round(1.-G,4),"entry_best_bid":round(A+z,4),"last_bid":round(A+z,4),"maker_tp_px":None,"tier_fills":v,"extra":{"is_dominance_box":True,"is_maker_anchor_box":True,"queue_front":T,"legging_drag_usd_by_tier":k,"maker_rebate_20pct_est_t1000_usd":c,"regime":di["regime"],"k_low":di["k_low"],"k_high":di["k_high"],"corridor_bps":di["corridor_bps"],"m15_horizon":_n.horizon,"m15_market_id":_n.market_id,"m15_start_iso":_n.start_iso,"m15_end_iso":_n.end_iso,"m5_horizon":m5.horizon,"m5_market_id":m5.market_id,"leg_a":_e,"leg_b":_d},"status":"OPEN"};b.open_positions[W]=_m;b._append_ledger({"event":"SHADOW_ENTRY",**_m});logger.info(f"[ENTRY:D1_MAKER_ANCHOR_BOX] {_m['title']} -> Hedged @ net=${G:.4f}!")
    else:
     g,_=extract_best_bid((_b or{}).get("bids")or[])
     if g<=.0:g=max(.01,Z-.03)
     M=float(S["fee_rate"])*((g*(1.-g))**float(S.get("fee_exponent",1.)));L=max(.0,g-M);_i={};_h={};F=max(.9,float(st.get("pair_est")or.985))
     for j,u in BANKROLL_TICKETS.items():_g=max(5.,float(math.floor(min(u["D1_MAKER_ANCHOR_BOX"],o)/F)));_l=round(_g*Z,2);_i[j]={"filled":True,"vwap":Z,"eff_px":Z,"spent_usd":_l,"fee_usd":.0,"shares":_g};_h[j]=round(_g*L-_l,2)
     K={"position_id":f"D1_MKR_SCRATCH_{int(_p)}_{m5.market_id[-6:]}","dedupe_key":_f,"sleeve":"D1_MAKER_ANCHOR_BOX","asset_or_city":_n.asset,"title":f"{_n.asset} {di['regime']} [Maker Anchor Unhedged Scratch]","side":f"{S['label']}_SCRATCH","token_id":str(S["token_id"]),"fee_rate":.0,"entry_ts":st["posted_ts"],"entry_utc":datetime.fromtimestamp(st["posted_ts"],tz=timezone.utc).isoformat(),"close_ts":m5.end_ts,"closed_ts":_p,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":.5,"entry_eff_px_t1000":Z,"entry_vwap_t1000":Z,"net_payout_per_share":round(L,4),"tier_fills":_i,"tier_pnls_usd":_h,"legging_adjusted_tier_pnls_usd":dict(_h),"won":_h.get("T1000",.0)>0,"status":"MAKER_ANCHOR_UNHEDGED_SCRATCH"};b.closed_positions.append(K);b._append_ledger({"event":"SHADOW_CLOSE",**K})
    continue
   t=sorted([(float(a["price"]),float(a["size"]))for a in((_a or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);E=t[0][0]if t else 1.;n=sum(sz for px,sz in t if px<=E+.01)if t else.0;y=float(R["fee_rate"])*((E*(1.-E))**float(R.get("fee_exponent",1.)))if E<1. else.0;s=float(st.get("req_shares_t100")or st.get("req_shares_t1000")or 15.);e=(n<max(12.,2.*s))or((Z+E+y)>.993);d=.0
   if _b is not None:
    _,V=extract_best_bid(_b.get("bids")or[]);U=sum(float(a.get("size",0))for a in I if abs(float(a.get("price",0))-l)<1e-6)
    if(V+U)>.0:d=(V-U)/(V+U)
   x=float(st.get("posted_spot")or.0);D=b._latest_spot_px(_n.asset);f=((D-x)/x*1e4)if(x>.0 and D>.0)else.0;C=b.get_return_bps(_n.asset,5.);r=str(S.get("side")or"UP").upper();m=2.5 if _n.asset in("BTC","ETH")else 4.5;q=((min(f,C)<-m)if r=="UP"else(max(f,C)>m));i=(_p-float(b._last_any_shock_ts_by_asset.get(_n.asset,.0)or.0))<4.
   if(Q<=45. or Y>=(12. if b.single_scan else 90.)or q or abs(C)>8. or d<-.35 or i or e):b.pending_maker_anchors.pop(_f,None)
 def post_zero_fee_maker_anchor_box(d,source_tag,asset,d_key,leg_a,leg_b,bk_a,bk_b,close_ts,title,now_ts,prefetched_books=None,*,live_emit_only=False):
  if is_shadow_sleeve_quarantined("ZF_INTRADAY_MAKER_BOX"):return False
  A=float(close_ts-now_ts);i=source_tag in{"CAL1_LADDER","NEGRISK_NO_PAIR","AFF1_DEADBALL","SP3_CORRIDOR"};o=259200. if source_tag in{"CAL1_LADDER","NEGRISK_NO_PAIR"}else 64800.
  if not(65.<=A<=o):return False
  M=d.__dict__.setdefault("_zf_maker_cooldown_until",{})
  if not live_emit_only and(d_key in d.entered_keys or d_key in d.pending_zero_fee_maker_anchors or float(M.get(d_key,.0)or.0)>now_ts):return False
  if float(leg_a.get("fee_rate",.0))>.0 or float(leg_b.get("fee_rate",.0))>.0:return False
  if prefetched_books:
   _d=str(leg_a.get("opp_token_id")or"");_c=str(leg_b.get("opp_token_id")or"")
   if _d in prefetched_books and _c in prefetched_books:
    _f,_=extract_best_bid((prefetched_books[_d]or{}).get("bids")or[]);_e,_=extract_best_bid((prefetched_books[_c]or{}).get("bids")or[]);L,_=d._best_ask_sz(bk_a);K,_=d._best_ask_sz(bk_b)
    if((L>.0 and _f>.0 and(L+_f)>1.015)or(K>.0 and _e>.0 and(K+_e)>1.015)or(_f+_e)>1.16):return False
  J=sorted([(float(b["price"]),float(b["size"]))for b in(bk_a.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);I=sorted([(float(b["price"]),float(b["size"]))for b in(bk_b.get("bids")or[])if float(b.get("price",0))>0 and float(b.get("size",0))>0],key=lambda x:-x[0]);H=sorted([(float(a["price"]),float(a["size"]))for a in(bk_a.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);G=sorted([(float(a["price"]),float(a["size"]))for a in(bk_b.get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0])
  if not H or not G or not J or not I:return False
  _b,_a=J[0];Z,Y=I[0];X,W=H[0];V,U=G[0];T=(_a-W)/max(1e-9,_a+W);S=(Y-U)/max(1e-9,Y+U);n=max(6.,math.floor(float(BANKROLL_TICKETS["T100"]["ZF_INTRADAY_MAKER_BOX"])/.988));k=max(6.,math.floor(float(BANKROLL_TICKETS["T1000"]["ZF_INTRADAY_MAKER_BOX"])/.988))
  def c(p):p=round(float(p),4);return(math.floor((p+1e-9)*1e2)/1e2)if(.04+1e-9<p<.96-1e-9)else(math.floor((p+1e-9)*1e3)/1e3)
  m=.992 if source_tag=="SP1_NBA"else(.985 if A>3600. else.988);t=[]
  for f in(True,False):
   R=_b if f else Z;y=_a if f else Y;Q=X if f else V;w=T if f else S;P=Z if f else _b;s=G if f else H;O=s[0][0]
   if not(.02<=Q<=.999)or not(.001<=O<=.985)or w<-.25:continue
   if P>.0 and O>.04 and(O-P)>.05:continue
   F=.001 if(R>=.96 or R<.04)else.01;E=.001 if(Q>.96 or Q<=.04)else.01;D=c(R+F);N=c(Q-E);r=sum(sz for px,sz in s if px<=O+.01);j=4. if i else 2.5
   if r<max(24. if i else 18.,j*n):continue
   e=True
   if D<=N+1e-9 and D>R+1e-9:h=min(D,N,c(m-O));e=h>R+1e-9
   elif(Q-R)>=.01-1e-9 and.15<=Q<=.88 and w>=-.15 and y>=15.:e=False;h=min(c(R),c(m-O))
   else:continue
   if h<round(R-F,3)or h<=.015 or h>=Q:continue
   g=round(h+O,4)
   if.86<=g<=m:t.append((g,f,round(h,4),round(O,4),e))
  if not t:return False
  t.sort(key=lambda z:(z[0],0 if z[4]else 1));g,f,C,B,l=t[0]
  if not live_emit_only:d.pending_zero_fee_maker_anchors[d_key]={"source_tag":source_tag,"dedupe_key":d_key,"asset":asset,"title":title,"leg_a":leg_a,"leg_b":leg_b,"anchor_is_a":f,"bid_px":C,"pair_est":g,"queue_front":l,"req_shares_t100":n,"req_shares_t1000":k,"close_ts":close_ts,"posted_ts":now_ts}
  v=sum(sz for px,sz in H if px<=X+.01);u=sum(sz for px,sz in G if px<=V+.01);q=d.emit_live_maker_anchor_box_candidate(sleeve_source="ZF_INTRADAY_MAKER_BOX",box_type="ZERO_FEE_MAKER_ANCHOR",asset=asset,dedupe_key=d_key,regime=f"ZF_{source_tag}",pair_horizons=f"zf_{source_tag.lower()}",leg_a=leg_a,leg_b=leg_b,anchor_is_a=f,queue_front=l,anchor_bid_px=C,hedge_limit_px=B,avail_a_shares=v,avail_b_shares=u,close_ts=float(close_ts),now_ts=now_ts,k_low=float(leg_a.get("strike")or 1e2),k_high=float(leg_b.get("strike")or 1e2))
  if live_emit_only:return q
  logger.info(f"[ZF_INTRADAY_MAKER_POST:{source_tag}] {title} | bid=${C:.3f} + hdg=${B:.3f} = ${g:.4f} (TTE={A/3600.:.2f}h)");return True
 async def manage_pending_zero_fee_maker_anchors(b,now_ts=None):
  if not b.pending_zero_fee_maker_anchors:return
  Z=float(now_ts if now_ts is not None else time.time());K=b.__dict__.setdefault("_zf_maker_cooldown_until",{});U=[t for st in b.pending_zero_fee_maker_anchors.values()for t in(str(st["leg_a"]["token_id"]),str(st["leg_b"]["token_id"]))];Y=await b.fetch_books_batch(U,timeout=3.)
  for N,st in list(b.pending_zero_fee_maker_anchors.items()):
   la,lb=st["leg_a"],st["leg_b"];v=bool(st["anchor_is_a"]);C=la if v else lb;B=lb if v else la;J=Y.get(str(C["token_id"]));I=Y.get(str(B["token_id"]));H=float(st["bid_px"]);G=Z-float(st["posted_ts"]);A=float(st["close_ts"])-Z;u=(J or{}).get("asks")or[];g=min((float(a["price"])for a in u if float(a.get("size",0))>0),default=1.)
   if J is not None and G>=.4 and g<=H:
    b.pending_zero_fee_maker_anchors.pop(N,None);b.entered_keys.add(N);s=sorted([(float(a["price"]),float(a["size"]))for a in((I or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);F=s[0][0]if s else 1.;p=sum(sz for px,sz in s if px<=F+.01)if s else.0;r=round(H+F,4)
    if I is not None and s and p>=5. and.9<=r<=.993:
     M={};z={}
     for f,m in BANKROLL_TICKETS.items():sh=max(5.,min(p,math.floor(m["ZF_INTRADAY_MAKER_BOX"]/r)));M[f]={"filled":True,"vwap":r,"eff_px":r,"spent_usd":round(sh*r,2),"fee_usd":.0,"shares":sh,"l1_usd":round(p*r,2)};T=compute_d1_maker_anchor_drag_haircut(shares=sh,pair_eff=r,bid_anc=H,hdg_px=F,hdg_avail_shares=p,fee_rate_anc=.0,fee_exponent_anc=1.,queue_front=bool(st.get("queue_front",True)),is_4h_mixed=False);z[f]=float(T["legging_drag_usd"])
     S,_=extract_best_bid((Y.get(str(la["token_id"]))or{}).get("bids")or[]);R,_=extract_best_bid((Y.get(str(lb["token_id"]))or{}).get("bids")or[]);X=f"ZF_INTRADAY_MKR_{int(Z)}_{N[-8:]}";W={"position_id":X,"dedupe_key":N,"sleeve":"ZF_INTRADAY_MAKER_BOX","asset_or_city":st["asset"],"title":f"{st['title']} [ZF Intraday Maker @ ${H:.3f}]","side":f"{la['label']}+{lb['label']}","token_id":f"{la['token_id']}|{lb['token_id']}","fee_rate":.0,"entry_ts":Z,"entry_utc":datetime.now(timezone.utc).isoformat(),"close_ts":st["close_ts"],"p_model_entry":1.,"entry_eff_px_t1000":r,"entry_vwap_t1000":r,"realized_edge_t1000":round(1.-r,4),"entry_best_bid":round(S+R,4),"last_bid":round(S+R,4),"maker_tp_px":None,"tier_fills":M,"extra":{"is_two_leg_box":True,"is_maker_anchor_box":True,"legging_drag_usd_by_tier":z,"source_tag":st["source_tag"],"leg_a":la,"leg_b":lb},"status":"OPEN"};b.open_positions[X]=W;b._append_ledger({"event":"SHADOW_ENTRY",**W});logger.info(f"[ENTRY:ZF_INTRADAY_MAKER_BOX] {W['title']} -> Hedged @ ${r:.4f}!")
    else:
     y,_=extract_best_bid((J or{}).get("bids")or[]);x=y if y>0 else max(.01,H-.03);Q,P={},{};i=max(.9,float(st.get("pair_est")or.986))
     for f,m in BANKROLL_TICKETS.items():O=max(5.,float(math.floor(m["ZF_INTRADAY_MAKER_BOX"]/i)));V=round(O*H,2);Q[f]={"filled":True,"vwap":H,"eff_px":H,"spent_usd":V,"fee_usd":.0,"shares":O};P[f]=round(O*x-V,2)
     w={"position_id":f"ZF_MKR_SCRATCH_{int(Z)}_{N[-8:]}","dedupe_key":N,"sleeve":"ZF_INTRADAY_MAKER_BOX","asset_or_city":st["asset"],"title":f"{st['title']} [ZF Intraday Maker Scratch]","side":f"{C['label']}_SCRATCH","token_id":str(C["token_id"]),"fee_rate":.0,"entry_ts":st["posted_ts"],"entry_utc":datetime.fromtimestamp(st["posted_ts"],tz=timezone.utc).isoformat(),"close_ts":st["close_ts"],"closed_ts":Z,"closed_utc":datetime.now(timezone.utc).isoformat(),"p_model_entry":.5,"entry_eff_px_t1000":H,"entry_vwap_t1000":H,"net_payout_per_share":round(x,4),"tier_fills":Q,"tier_pnls_usd":P,"legging_adjusted_tier_pnls_usd":dict(P),"won":P.get("T1000",.0)>0,"status":"MAKER_ANCHOR_UNHEDGED_SCRATCH"};b.closed_positions.append(w);b._append_ledger({"event":"SHADOW_CLOSE",**w})
    continue
   l=sorted([(float(a["price"]),float(a["size"]))for a in((I or{}).get("asks")or[])if float(a.get("price",0))>0 and float(a.get("size",0))>0]);q=l[0][0]if l else 1.;h=sum(sz for px,sz in l if px<=q+.01)if l else.0;k=float(st.get("req_shares_t100")or 18.);d,E=extract_best_bid((J or{}).get("bids")or[]);D=sum(float(a.get("size",0))for a in u if abs(float(a.get("price",0))-g)<1e-6);o=((E-D)/(E+D))if(E+D)>.0 else.0;e=.993 if st.get("source_tag")=="SP1_NBA"else.991;from src.polymarket_research.synthetic_maker_quoter import evaluate_resting_synthetic_quote_tick as c;n=time.monotonic();L=c(posted_bid_px=H,posted_shares=k,anchor_book=J,hedge_book=I,hedge_fee_rate=.0,hedge_fee_exponent=1.,max_entry_box_cost_net=e-.002,max_keep_box_cost_net=e,min_keep_depth_mult=2.,rem_tte_sec=A,min_rem_tte_sec=60.,advance_since_mono=n-1.,now_mono=n,advance_debounce_sec=.5,repeg_count=int(st.get("_repeg_count",0)or 0),max_repegs=3);j=(A<=60. or o<-.3 or(d>.0 and d<H-.015)or h<max(12.,2.*k)or(H+q)>e or L["action"]=="CANCEL_ADVERSE")
   if(not j and L["action"]=="REPEG_FIFO1"and L.get("repeg_bid_px")is not None and int(st.get("_repeg_count",0)or 0)<3):st["bid_px"]=float(L["repeg_bid_px"]);st["pair_est"]=round(float(st["bid_px"])+q,4);st["queue_front"]=True;st["_repeg_count"]=int(st.get("_repeg_count",0)or 0)+1;st["_last_repeg_elapsed"]=G
   if j or G>=(15. if b.single_scan else 90.):
    b.pending_zero_fee_maker_anchors.pop(N,None)
    if j:K[N]=Z+12.
    else:K.pop(N,None);b.last_tradfi_sports_scan_ts=min(float(b.last_tradfi_sports_scan_ts),Z-16.)
 async def scan_same_oracle_dominance_boxes(a,opps_out,now_ts=None):
  Q=float(now_ts if now_ts is not None else time.time())
  if a.pending_maker_anchors:await a.manage_pending_maker_anchors(Q)
  n=int(math.ceil(Q/9e2)*900);g=sum(1 for k in a.dominance_pairs if str(k).endswith(f"_{n}"));m=7. if g<len(DOMINANCE_ASSETS)else 12.;w=float(n)-Q;y=math.ceil(Q/3600.)*3600.-Q;s=(a.is_in_same_oracle_overlap_window(Q)if(a.single_scan or"fetch_json"in a.__dict__)else((5.<=w<=330.)or(5.<=y<=905.)))
  if s and(Q-a.last_dominance_discovery_ts)>=m:a.last_dominance_discovery_ts=Q;await a.discover_dominance_pairs(Q)
  if now_ts is None:a.record_usd_spot_samples(time.time())
  q=[(m15,m5)for m15,m5 in list(a.dominance_pairs.values())if(10.<=(m5.end_ts-Q)<=(9e2 if m5.horizon=="15m"else 3e2))and(Q>=m5.start_ts+1.)]
  if q:
   async def e(m15,m5):
    r,T=await asyncio.gather(a.get_authoritative_open_strike(m15),a.get_authoritative_open_strike(m5))
    if r is None or T is None:return None
    k=float(MIN_CORRIDOR_BPS_BY_ASSET.get(m15.asset,3.));U=determine_dominance_legs(m15,r,m5,T,min_corridor_bps=k);return(m15,m5,U)if U is not None else None
   l=[r for r in await asyncio.gather(*(e(m15,m5)for m15,m5 in q))if r is not None]
   if l:
    v=[]
    for _,_,di in l:S,R=di["leg_a"],di["leg_b"];v.extend([str(S["token_id"]),str(R["token_id"]),str(S.get("opp_token_id")or""),str(R.get("opp_token_id")or"")])
    x=await a.fetch_books_batch(v,timeout=3.)
    for m15,m5,G in l:
     I=m5.end_ts-Q;N,M=G["leg_a"],G["leg_b"];P=x.get(str(N["token_id"]));O=x.get(str(M["token_id"]))
     if not P or not O:continue
     b=None;F=float(now_ts)if now_ts is not None else time.time();E=f"{m15.horizon}_{m5.horizon}";a._record_d1_corridor_telemetry(E,m15,m5,G,P,O,F);D=m5.end_ts-F;f=a._strike_is_rest_verified(m15)and a._strike_is_rest_verified(m5);d=False;p=898. if m5.horizon=="15m"else 298.
     if f and 16.<=D<=p:
      L=max(float(N["fee_rate"]),float(M["fee_rate"]))==.0;j=a._d1_live_max_box_cost(zero_fee=L,rem_tte_sec=D);u=a.is_sleeve_grad8_ready("D1_QUIET_BOOK_BOX");i=max(j,.989)if u else j;K=walk_equal_shares_dominance_box(P.get("asks")or[],O.get("asks")or[],target_budget_usd=24.,fee_rate_a=float(N["fee_rate"]),fee_rate_b=float(M["fee_rate"]),fee_exponent_a=float(N["fee_exponent"]),fee_exponent_b=float(M["fee_exponent"]),max_box_cost_net=i,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.86)
      if K.get("filled"):
       h=a._passes_quiet_book_filter(m15.asset,P,O,K,F);o=i if(h and u)else j
       if float(K["box_cost_net"])<=o:
        b=await a._passes_complement_anti_box_check(N,M,prefetched_books=x)
        if not b:continue
        d=a.emit_live_d1_box_candidate(m15,m5,G,K,F,is_quiet_book=h,sleeve_source="D1_QUIET_BOOK_BOX"if h else"D1_SAME_ORACLE_DOMINANCE_BOX")
     J=walk_equal_shares_dominance_box(P.get("asks")or[],O.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_SAME_ORACLE_DOMINANCE_BOX"],fee_rate_a=float(N["fee_rate"]),fee_rate_b=float(M["fee_rate"]),fee_exponent_a=float(N["fee_exponent"]),fee_exponent_b=float(M["fee_exponent"]),max_box_cost_net=1.032,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=.86 if f else.9);c=False
     if J.get("filled"):
      H=float(J["box_cost_net"]);t=round(1.-H,4)
      if H<=1.005:opps_out.append({"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","market":f"{m15.asset} {G['regime']} (TTE={I:.0f}s, {G['corridor_bps']:.1f}bps)","ask_vwap":round(H,4),"p_model":1.,"net_edge":t,"l1_usd":J["l1_usd"]})
      if H<=.995:
       if b is None:b=await a._passes_complement_anti_box_check(N,M,prefetched_books=x)
       if not b:continue
       c=True;await a.open_shadow_dominance_box(m15.asset,m15,m5,G,prefetched_books=(P,O))
       if a._passes_quiet_book_filter(m15.asset,P,O,J,F):await a.open_shadow_dominance_box(m15.asset,m15,m5,G,prefetched_books=(P,O),sleeve_override="D1_QUIET_BOOK_BOX",max_box_cost_override=.992)
     if not c or not d:
      C,_=a._best_ask_sz(P);B,_=a._best_ask_sz(O);A,_=extract_best_bid(P.get("bids")or[]);z,_=extract_best_bid(O.get("bids")or[])
      if(C+B)<=1.02 or(A>.0 and z>.0 and min(A+B,C+z)<=1.005):
       if b is None:b=await a._passes_complement_anti_box_check(N,M,prefetched_books=x)
       if b:a.post_maker_anchor_candidate(m15,m5,G,P,O,F,live_emit_only=bool(c))
  await a._scan_4h_dominance_boxes(opps_out,now_ts)
 def _passes_quiet_book_filter(a,asset,bk_a,bk_b,w_scan,now_ts):
  if abs(a.get_return_bps(asset,5.))>4.5:return False
  if(now_ts-float(a._last_any_shock_ts_by_asset.get(asset,.0)or.0))<4.:return False
  g,_=extract_best_bid(bk_a.get("bids")or[]);f,_=extract_best_bid(bk_b.get("bids")or[]);e=float((w_scan.get("leg_a_walk")or{}).get("best_ask")or 1.);d=float((w_scan.get("leg_b_walk")or{}).get("best_ask")or 1.)
  if g<=.0 or f<=.0:return False
  if(e-g)>.041 or(d-f)>.041:return False
  c=float(w_scan.get("shares")or 12.);b=min(float(w_scan.get("avail_a_shares")or.0),float(w_scan.get("avail_b_shares")or.0));return b>=1.5*c
 async def discover_4h_dominance_pairs(a,now_ts):
  for k,(i,_)in list(a.dominance_4h_pairs.items()):
   if i.end_ts<now_ts-6e2:a.dominance_4h_pairs.pop(k,None)
  for l,j in list(a.s4h_candles.items()):
   if j.end_ts<now_ts-6e2:a.s4h_candles.pop(l,None)
  from src.polymarket_research.riskless_protocol_v2_expansion import(compute_min_4h_boundary_rem_sec,resolve_active_4h_target_end_ts as c);e,h=c(now_ts)
  if h<8.:return
  d=8.<=h<=905.;g=datetime.fromtimestamp(now_ts-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");f=h<=305.
  async def b(asset):
   Q=DOMINANCE_SERIES_SLUGS[asset];J=Q.get("4h")
   if not J:return
   t=f"{asset}_4h_{e}";v=f"{asset}_4h15m_{e}";B=f"{asset}_4h5m_{e}"
   if not d:
    if t in a.s4h_candles:return
    D=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={J}&closed=false&end_date_min={g}&order=endDate&ascending=true&limit=3",timeout=4.);r=bool(a.single_scan or("fetch_json"in a.__dict__));q=False
    if isinstance(D,list):
     for y in D:
      P=parse_twap_candle_event(y,asset,"4h")
      if P and(abs(P.end_ts-e)<=2. or 8.<=(P.end_ts-now_ts)<=14405.):w=int(round(P.end_ts));a.s4h_candles[f"{asset}_4h_{w}"]=P;q=True;break
    if not q and not r:
     M=build_deterministic_updown_event_slug(asset,"4h",e)
     if M:
      x=await a.fetch_json(f"{GAMMA_URL}/events?slug={M}",timeout=3.5)
      if isinstance(x,list)and x:
       L=parse_twap_candle_event(x[0],asset,"4h")
       if L and abs(L.end_ts-e)<=2.:w=int(round(L.end_ts));a.s4h_candles[f"{asset}_4h_{w}"]=L
    return
   if v in a.dominance_4h_pairs and((not f)or B in a.dominance_4h_pairs):return
   I,C=await asyncio.gather(a.fetch_json(f"{GAMMA_URL}/events?series_slug={J}&closed=false&end_date_min={g}&order=endDate&ascending=true&limit=3",timeout=4.),a.fetch_json(f"{GAMMA_URL}/events?series_slug={Q['15m']}&closed=false&end_date_min={g}&order=endDate&ascending=true&limit=3",timeout=4.));p=None;o=None;n=e;s=bool(a.single_scan or("fetch_json"in a.__dict__))
   if isinstance(I,list):
    for y in I:
     U=parse_twap_candle_event(y,asset,"4h")
     if U and(abs(U.end_ts-e)<=2. or 8.<=(U.end_ts-now_ts)<=905.):p=U;n=int(round(U.end_ts));a.s4h_candles[f"{asset}_4h_{n}"]=U;break
   if p is None and not s:
    S=build_deterministic_updown_event_slug(asset,"4h",e)
    if S:
     H=await a.fetch_json(f"{GAMMA_URL}/events?slug={S}",timeout=3.5)
     if isinstance(H,list)and H:
      O=parse_twap_candle_event(H[0],asset,"4h")
      if O and abs(O.end_ts-e)<=2.:p=O;n=int(round(O.end_ts));a.s4h_candles[f"{asset}_4h_{n}"]=O
   v=f"{asset}_4h15m_{n}";B=f"{asset}_4h5m_{n}";u=(float(n)-now_ts)<=305.
   if isinstance(C,list):
    for y in C:
     R=parse_twap_candle_event(y,asset,"15m")
     if R and abs(R.end_ts-n)<=2.:o=R;break
   if p and o is None and not s:
    A=build_deterministic_updown_event_slug(asset,"15m",n)
    if A:
     z=await a.fetch_json(f"{GAMMA_URL}/events?slug={A}",timeout=3.5)
     if isinstance(z,list)and z:
      K=parse_twap_candle_event(z[0],asset,"15m")
      if K and abs(K.end_ts-n)<=2.:o=K
   if p and o and verify_same_oracle_pair(p,o):a.dominance_4h_pairs[v]=(p,o)
   if p and u and B not in a.dominance_4h_pairs:
    G=await a.fetch_json(f"{GAMMA_URL}/events?series_slug={Q['5m']}&closed=false&end_date_min={g}&order=endDate&ascending=true&limit=3",timeout=4.);m=None
    if isinstance(G,list):
     for y in G:
      T=parse_twap_candle_event(y,asset,"5m")
      if T and abs(T.end_ts-n)<=2. and verify_same_oracle_pair(p,T):m=T;break
    if m is None and not s:
     F=build_deterministic_updown_event_slug(asset,"5m",n)
     if F:
      E=await a.fetch_json(f"{GAMMA_URL}/events?slug={F}",timeout=3.5)
      if isinstance(E,list)and E:
       N=parse_twap_candle_event(E[0],asset,"5m")
       if N and abs(N.end_ts-n)<=2. and verify_same_oracle_pair(p,N):m=N
    if m is not None:a.dominance_4h_pairs[B]=(p,m)
  await asyncio.gather(*(b(m)for m in DOMINANCE_ASSETS))
 async def _scan_4h_dominance_boxes(a,opps_out,now_ts=None):
  from src.polymarket_research.riskless_protocol_v2_expansion import compute_min_4h_boundary_rem_sec as e;J=float(now_ts if now_ts is not None else time.time());I=e(J);g=12. if(8.<=I<=905.)else 180.
  if I>=8. and(J-a.last_4h_discovery_ts)>=g:a.last_4h_discovery_ts=J;await a.discover_4h_dominance_pairs(J)
  for _,(m4,B)in list(a.dominance_4h_pairs.items()):
   A=B.end_ts-J;z=895. if B.horizon=="15m"else 298.
   if not(10.<=A<=z)or J<B.start_ts+1.:continue
   U,T=await asyncio.gather(a.get_authoritative_open_strike(m4),a.get_authoritative_open_strike(B))
   if U is None or T is None:continue
   o=float(MIN_CORRIDOR_BPS_BY_ASSET.get(m4.asset,3.));w=determine_dominance_legs(m4,U,B,T,min_corridor_bps=o)
   if w is None:continue
   L,K=w["leg_a"],w["leg_b"];H=await a.fetch_books_batch([str(L["token_id"]),str(K["token_id"]),str(L.get("opp_token_id")or""),str(K.get("opp_token_id")or"")],timeout=3.);S=H.get(str(L["token_id"]));R=H.get(str(K["token_id"]))
   if not S or not R:continue
   b=None;n=float(now_ts)if now_ts is not None else time.time();a._record_d1_corridor_telemetry(f"4h_{B.horizon}",m4,B,w,S,R,n)
   if now_ts is None:a.record_usd_spot_samples(n)
   m=B.end_ts-n;f=a._strike_is_rest_verified(m4)and a._strike_is_rest_verified(B);c=False
   if f and 18.<=m<=z:
    G=max(float(L["fee_rate"]),float(K["fee_rate"]))==.0;l=a._d1_live_max_box_cost(zero_fee=G,rem_tte_sec=m);h=a.is_sleeve_grad8_ready("D1_QUIET_BOOK_BOX");k=max(l,.989)if h else l;q=walk_equal_shares_dominance_box(S.get("asks")or[],R.get("asks")or[],target_budget_usd=13.5,fee_rate_a=float(L["fee_rate"]),fee_rate_b=float(K["fee_rate"]),fee_exponent_a=float(L["fee_exponent"]),fee_exponent_b=float(K["fee_exponent"]),max_box_cost_net=k,min_shares=5,min_box_notional_usd=4.85,min_box_cost_net=.86)
    if q.get("filled"):
     j=a._passes_quiet_book_filter(m4.asset,S,R,q,n);p=k if(j and h)else l
     if float(q["box_cost_net"])<=p:
      b=await a._passes_complement_anti_box_check(L,K,prefetched_books=H)
      if not b:continue
      c=a.emit_live_d1_box_candidate(m4,B,w,q,n,is_quiet_book=j,sleeve_source="D1_QUIET_BOOK_BOX"if j else"D1_4H_DOMINANCE_BOX")
   i=walk_equal_shares_dominance_box(S.get("asks")or[],R.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_4H_DOMINANCE_BOX"],fee_rate_a=float(L["fee_rate"]),fee_rate_b=float(K["fee_rate"]),fee_exponent_a=float(L["fee_exponent"]),fee_exponent_b=float(K["fee_exponent"]),max_box_cost_net=1.032,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=.86 if f else.9)
   if not i.get("filled"):i=walk_equal_shares_dominance_box(S.get("asks")or[],R.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T100"]["D1_4H_DOMINANCE_BOX"],fee_rate_a=float(L["fee_rate"]),fee_rate_b=float(K["fee_rate"]),fee_exponent_a=float(L["fee_exponent"]),fee_exponent_b=float(K["fee_exponent"]),max_box_cost_net=1.032,min_shares=8,min_box_notional_usd=7.5,min_box_cost_net=.86 if f else.9)
   d=False
   if i.get("filled"):
    y=float(i["box_cost_net"])
    if y<=1.005:opps_out.append({"sleeve":"D1_4H_DOMINANCE_BOX","market":f"{m4.asset} {w['regime']} (TTE={A:.0f}s, {w['corridor_bps']:.1f}bps)","ask_vwap":round(y,4),"p_model":1.,"net_edge":round(1.-y,4),"l1_usd":i["l1_usd"]})
    if y<=.995:
     if b is None:b=await a._passes_complement_anti_box_check(L,K,prefetched_books=H)
     if not b:continue
     d=True;await a.open_shadow_dominance_box(m4.asset,m4,B,w,prefetched_books=(S,R),sleeve_override="D1_4H_DOMINANCE_BOX",max_box_cost_override=.995)
     if a._passes_quiet_book_filter(m4.asset,S,R,i,n):await a.open_shadow_dominance_box(m4.asset,m4,B,w,prefetched_books=(S,R),sleeve_override="D1_QUIET_BOOK_BOX",max_box_cost_override=.992)
   if not d or not c:
    v,_=a._best_ask_sz(S);u,_=a._best_ask_sz(R);t,_=extract_best_bid(S.get("bids")or[]);s,_=extract_best_bid(R.get("bids")or[])
    if(v+u)<=1.02 or(t>.0 and s>.0 and min(t+u,v+s)<=1.005):
     if b is None:b=await a._passes_complement_anti_box_check(L,K,prefetched_books=H)
     if b:a.post_maker_anchor_candidate(m4,B,w,S,R,n,live_emit_only=bool(d))
  for _,Z in list(a.s4h_candles.items()):
   F=Z.end_ts-J
   if not(180.<=F<=9e2)or J<Z.start_ts+3600.:continue
   E=await a.get_authoritative_open_strike(Z)
   if E is None or E<=.0:continue
   Q=read_shm_usd_anchor(Z.asset,J,max_age_sec=3.);Y=a.usd_spot_hist.get(Z.asset);D=Q.get("usd_spot")or(float(Y[-1][1])if Y and(J-float(Y[-1][0]))<=5. else a.spots.get(Z.asset,.0))
   if not D or float(D)<=.0:continue
   r=float(D);C="UP"if r>E else"DOWN";x=a.get_return_bps(Z.asset,30.)
   if(C=="UP"and x<-6.)or(C=="DOWN"and x>6.):continue
   P=evaluate_svi_digital_fair_value(Z.asset,r,E,F,is_downward=False,now_ts=J);X=float(P["p_yes"]if C=="UP"else P["p_no"]);W=abs(float(P.get("z_sigma")or.0))
   if W<2.3 or X<.94:continue
   O=Z.up_token if C=="UP"else Z.down_token;V=await a.fetch_json(f"{CLOB_URL}/book?token_id={O}",timeout=2.5)
   if not V:continue
   w4=walk_l2_book_asks(V.get("asks")or[],BANKROLL_TICKETS["T1000"]["S4H_CHAINLINK_CONVERGENCE"],fee_rate=Z.fee_rate,min_l1_usd=18.)
   if not w4.get("filled"):continue
   N=float(w4["eff_px"]);M=X-N
   if.62<=N<=.89 and M>=.03:opps_out.append({"sleeve":"S4H_CHAINLINK_CONVERGENCE","market":f"{Z.asset} 4h {C} (TTE={F/60:.1f}m, z={W:.2f})","ask_vwap":N,"p_model":round(X,4),"net_edge":round(M,4),"l1_usd":w4["l1_usd"],"close_ts":Z.end_ts})
   if.62<=N<=.89 and M>=.045:await a.open_shadow_position(sleeve="S4H_CHAINLINK_CONVERGENCE",dedupe_key=f"S4H_{Z.asset}_{Z.market_id}",asset_or_city=Z.asset,title=f"{Z.title} [4h Chainlink Convergence]",side_label=C,token_id=O,fee_rate=Z.fee_rate,p_model=X,close_ts=Z.end_ts,extra={"market_id":Z.market_id,"condition_id":Z.condition_id,"horizon":"4h","start_iso":Z.start_iso,"end_iso":Z.end_iso,"open_price":E,"z_sigma":W},tp_target_px=.96,prefetched_book=V)
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
  except Exception:pass
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
  p=float(now_ts if now_ts is not None else time.time())
  for l,j in list(b.twap_candles.items()):
   if j.end_ts<p-3e2:b.twap_candles.pop(l,None)
  i=int(math.ceil(p/3e2)*300);h=float(i)-p;e=75. if(b.single_scan or"fetch_json"in b.__dict__)else 95.
  if not(3.5<=h<=e):return
  for _,(k,o)in b.dominance_pairs.items():
   if int(o.twap_lookback_sec)==60 and abs(o.end_ts-i)<=2.:b.twap_candles[f"{o.asset}_{o.horizon}_{i}"]=o
   if int(k.twap_lookback_sec)==60 and abs(k.end_ts-i)<=2.:b.twap_candles[f"{k.asset}_{k.horizon}_{i}"]=k
  for _,(n,m)in b.dominance_4h_pairs.items():
   if int(n.twap_lookback_sec)==60 and abs(n.end_ts-i)<=2.:b.twap_candles[f"{n.asset}_4h_{i}"]=n
  g=datetime.fromtimestamp(p-5.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");d=(i%900)==0
  async def c(asset):
   r=DOMINANCE_SERIES_SLUGS[asset];w=f"{asset}_5m_{i}"
   if w not in b.twap_candles:
    q=await b.fetch_json(f"{GAMMA_URL}/events?series_slug={r['5m']}&closed=false&end_date_min={g}&order=endDate&ascending=true&limit=3",timeout=3.)
    if isinstance(q,list):
     for t in q:
      v=parse_twap_candle_event(t,asset,"5m")
      if v and abs(v.end_ts-i)<=2.:b.twap_candles[w]=v;break
   if d:
    u=f"{asset}_15m_{i}"
    if u not in b.twap_candles:
     a=await b.fetch_json(f"{GAMMA_URL}/events?series_slug={r['15m']}&closed=false&end_date_min={g}&order=endDate&ascending=true&limit=3",timeout=3.)
     if isinstance(a,list):
      for t in a:
       s=parse_twap_candle_event(t,asset,"15m")
       if s and abs(s.end_ts-i)<=2.:b.twap_candles[u]=s;break
  await asyncio.gather(*(c(a)for a in DOMINANCE_ASSETS))
  if not b.single_scan and h>=22.:
   f=[sp for sp in list(b.twap_candles.values())if abs(sp.end_ts-i)<=2. and f"{sp.asset}_{sp.horizon}_{int(sp.start_ts)}"not in b.chainlink_open_cache]
   if f:await asyncio.gather(*(b.get_authoritative_open_strike(sp)for sp in f))
 async def scan_exact_twap_locks(a,opps_out,now_ts=None):
  if not a.single_scan and is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK"):
   if a.twap_candles:a.twap_candles.clear()
   return
  G=a.__dict__.setdefault("_s2_scan_lock",asyncio.Lock())
  if G.locked():return
  async with G:
   W=float(now_ts if now_ts is not None else time.time());j=bool(a.single_scan or"fetch_json"in a.__dict__);g={}
   if not j:from src.polymarket_research.riskless_protocol_v2_expansion import hydrate_fast_s2_from_shm as c;g=c(a,W)
   M=math.ceil(W/3e2)*3e2-W;F=8. if M<=40. else 12.;e=(not j)and M<=40. and any(abs(sp.end_ts-math.ceil(W/3e2)*3e2)<=2. for sp in a.twap_candles.values())
   if not e and 3.5<=M<=(75. if j else 95.)and(W-a.last_twap_discovery_ts)>=F:a.last_twap_discovery_ts=W;await a.discover_active_twap_candles(W)
   s=os.getenv("PM_QUARANTINE_LOSING_SLEEVES","1")=="1";p=38.5 if s else 45.;o=8. if a.single_scan else 4.2;z=.975 if s else.965;y=2.65 if s else.0;n=[spec for _,spec in sorted(a.twap_candles.items(),key=lambda Y:({"BTC":0,"ETH":1,"SOL":2}.get(getattr(Y[1],"asset",""),9),getattr(Y[1],"end_ts",.0)))if int(spec.twap_lookback_sec)==60 and(o<=(spec.end_ts-W)<=p)and(W>=spec.start_ts+60.)]
   if not n:return
   E=await asyncio.gather(*(a.get_authoritative_open_strike(sp)for sp in n));i=[(sp,Y)for sp,Y in zip(n,E)if Y is not None and Y>.0]
   if not i:return
   D=[]
   for sp,_ in i:D.extend([sp.up_token,sp.down_token])
   L=({**g,**(await a.fetch_books_batch(D,timeout=1.5)or{})}if not j else{})
   for Q,P in g.items():
    if isinstance(L.get(Q),dict)and"minimum_tick_size"not in L[Q]and P.get("minimum_tick_size"):L[Q]["minimum_tick_size"]=P["minimum_tick_size"]
   for spec,K in i:
    w=float(now_ts)if(a.single_scan and now_ts is not None)else time.time();C=spec.end_ts-w
    if not(o<=C<=p):continue
    V=(read_shm_usd_anchor(spec.asset,w,max_age_sec=2.5)if not(a.single_scan and a.usd_spot_hist.get(spec.asset))else{});v=getattr(a,"_chainlink_ws",None)if not a.single_scan else None;m=v.get_latest_spot(spec.asset,now_ts=w,max_age_sec=2.5)if v is not None else None;h=(v.get_latest_official_twap_60s(spec.asset,now_ts=w,max_age_sec=3.5)if(v is not None and hasattr(v,"get_latest_official_twap_60s"))else None);u=a.usd_spot_hist.get(spec.asset);d=m or V.get("usd_spot")
    if(not d or float(d)<=.0)and u and(w-float(u[-1][0]))<=5.:d=float(u[-1][1])
    if(not d or float(d)<=.0)and a.usd_direct_flags.get(spec.asset,False):d=a.spots.get(spec.asset,.0)
    if not d or float(d)<=.0:continue
    r=float(d);l=bool(m is not None or V.get("source")in("shm_chainlink_proxy","shm_coinlink_usd","shm_coinbase_usd")or a.usd_direct_flags.get(spec.asset,False));O,_=get_wing_implied_vol(spec.asset,r,K,86400.);f=v.get_recent_samples(spec.asset,spec.end_ts-125.)if v is not None else[];k=sum(1 for Y,_ in f if Y>=(spec.end_ts-60.5))
    if len(f)<2 or(C<=55. and u and k<int(max(3.,(60.-C)*.72))):
     q={round(float(Z),1):float(Y)for Z,Y in(u or[])if Z>=(spec.end_ts-125.)}
     for U,T in f:q[round(float(U),1)]=float(T)
     f=sorted(q.items(),key=lambda x:x[0])
    if not j and 3.8<=C<=38. and a._strike_is_rest_verified(spec)and len(f)>=6:from src.polymarket_research.riskless_protocol_v2_expansion import maybe_emit_s2_live_locks as b;b(a,spec=spec,k_open=K,eval_now=w,rem_sec=C,samples=f,off_twap_60=h,bks_s2=L or{},logger_obj=logger)
    B=compute_exact_twap_lock_probability(asset=spec.asset,open_price=K,current_usd_spot=r,rem_seconds=C,now_ts=w,end_ts=spec.end_ts,spot_samples=f,shm_twap_60s=h or V.get("twap_60s"),iv_annual=O,usd_direct_feed=l,authoritative_chainlink_ws=bool(m is not None),min_rem_seconds=o)
    if not B.get("eligible")or float(B["p_lock"])<.94 or float(B.get("z_lock",.0))<y:continue
    t=str(B["side"]);S=spec.up_token if t=="UP"else spec.down_token;A=spec.down_token if t=="UP"else spec.up_token;X=L.get(S)if L else await a.fetch_json(f"{CLOB_URL}/book?token_id={S}",timeout=2.5)
    if not X:continue
    J=L.get(A)if L else None;N=walk_l2_book_asks(X.get("asks")or[],BANKROLL_TICKETS["T1000"]["S2_EXACT_TWAP_LOCK"],fee_rate=spec.fee_rate,min_l1_usd=15.)
    if not N.get("filled"):continue
    I=float(N["eff_px"]);H=float(B["p_lock"]);R=H-I
    if.74<=I<=.955 and R>=.015:opps_out.append({"sleeve":"S2_EXACT_TWAP_LOCK","market":f"{spec.asset} {spec.horizon} {t} (TTE={C:.0f}s, alpha={B['eff_alpha']:.2f}, z={B['z_lock']:.2f})","ask_vwap":I,"p_model":H,"net_edge":round(R,4),"l1_usd":N["l1_usd"]})
    if H>=z and.76<=I<=.95 and R>=.03:await a.open_shadow_position(sleeve="S2_EXACT_TWAP_LOCK",dedupe_key=f"S2_{spec.asset}_{spec.horizon}_{spec.market_id}",asset_or_city=spec.asset,title=f"{spec.title} [{spec.horizon} TWAP Lock]",side_label=t,token_id=S,fee_rate=spec.fee_rate,p_model=H,close_ts=spec.end_ts,extra={"market_id":spec.market_id,"condition_id":spec.condition_id,"horizon":spec.horizon,"start_iso":spec.start_iso,"end_iso":spec.end_iso,"open_price":K,"mu_twap":B["mu_twap"],"eff_alpha":B["eff_alpha"],"z_lock":B["z_lock"],"cushion_bps":B["cushion_bps"],"rem_seconds_at_entry":B["rem_seconds"]},tp_target_px=None,prefetched_book=X)
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
  _3=time.time();_Z=asyncio.get_running_loop();_h=[]
  for _q,_o in list(c.open_positions.items()):
   _y=_o["sleeve"];_2=_o["token_id"]
   if _y=="W3_WEATHER_SLATE_ARB":
    e=float(_o["close_ts"]);_m=_o.get("extra")or{};_c=_m.get("legs")or[]
    if _3<e+30.:
     T=None
     if(_3-float(_o.get("_last_book_poll_ts")or.0))>=30. and _c:
      _o["_last_book_poll_ts"]=_3;T=await asyncio.gather(*[c.fetch_json(f"{CLOB_URL}/book?token_id={lg.get('token_id')or lg.get('yes_token','')}",timeout=2.5)for lg in _c])
      if all(T):
       _o["last_bid"]=round(sum(extract_best_bid((b or{}).get("bids")or[])[0]for b in T),4);_Y=c._try_early_overround_bid_unwind(_o,[{"bids":(b or{}).get("bids")or[],"fee_rate":.0,"fee_exponent":1.}for b in T],_3)
       if _Y is not None:_h.append((_q,"EARLY_OVERROUND_BID_UNWIND",_Y[0],_Y[1]));continue
     if(_3-float(_o.get("_last_gamma_chk_ts")or.0))<(30. if(T is not None and not all(T))else 120.):continue
     _o["_last_gamma_chk_ts"]=_3
    if _c:
     S=float(_m.get("guaranteed_payout")or 1.);i=await asyncio.gather(*[c.resolve_via_gamma_market({"token_id":lg.get("token_id")or lg.get("yes_token",""),"side":lg.get("side","YES"),"extra":{"market_id":lg["market_id"]}})for lg in _c])
     if i and all(v is not None for v in i):f=round(sum(float(v)for v in i if v is not None),4);_X="SETTLED_WEATHER_SLATE_1X"if S<=1.01 else"SETTLED_WEATHER_SLATE_NX";_h.append((_q,_X,max(S,f),.0))
    continue
   Y=_o.get("extra")or{}
   if _y in("D1_SAME_ORACLE_DOMINANCE_BOX","D1_4H_DOMINANCE_BOX","D1_QUIET_BOOK_BOX","D1_MAKER_ANCHOR_BOX","M3_LADDER_MONO_BOX","B3_BARRIER_MONO_BOX","C1_BINARY_COMPLETE_SET","CM_B3_PYTH_BARRIER_BOX","SP1_NBA_ZERO_FEE_BOX","ZERO_FEE_MAKER_ANCHOR_BOX","ZF_INTRADAY_MAKER_BOX","D2_12PM_BINANCE_BOX")or(Y.get("leg_a")and Y.get("leg_b")):
    m=_o.get("extra")or{};_Q=m.get("leg_a")or{};_P=m.get("leg_b")or{};e=float(_o["close_ts"])
    if _3<e+10.:
     _W,_V=await asyncio.gather(c.fetch_json(f"{CLOB_URL}/book?token_id={_Q.get('token_id','')}",timeout=2.5),c.fetch_json(f"{CLOB_URL}/book?token_id={_P.get('token_id','')}",timeout=2.5))
     if _W and _V:
      _O,_=extract_best_bid(_W.get("bids")or[]);_N,_=extract_best_bid(_V.get("bids")or[]);_o["last_bid"]=round(_O+_N,4);_x=float(_o.get("fee_rate")or.0);_U=c._try_early_overround_bid_unwind(_o,[{"bids":_W.get("bids")or[],"fee_rate":float(_Q.get("fee_rate",_x)),"fee_exponent":float(_Q.get("fee_exponent",1.))},{"bids":_V.get("bids")or[],"fee_rate":float(_P.get("fee_rate",_x)),"fee_exponent":float(_P.get("fee_exponent",1.))}],_3)
      if _U is not None:_h.append((_q,"EARLY_OVERROUND_BID_UNWIND",_U[0],_U[1]));continue
     if(_y=="C1_BINARY_COMPLETE_SET"and _Q.get("market_id")and _Q.get("market_id")==_P.get("market_id")and(_3-float(_o.get("entry_ts")or.0))>=15.):_h.append((_q,"CTF_COMPLETE_SET_MERGED",1.,.0));continue
     if _W and _V:continue
     if _W or _V or(_3-float(_o.get("_last_gamma_chk_ts")or.0))<60.:continue
     _o["_last_gamma_chk_ts"]=_3
    _M,_L=await asyncio.gather(c.resolve_via_gamma_market({"token_id":_Q.get("token_id",""),"side":_Q.get("side","UP"),"extra":{"market_id":_Q.get("market_id","")}}),c.resolve_via_gamma_market({"token_id":_P.get("token_id",""),"side":_P.get("side","DOWN"),"extra":{"market_id":_P.get("market_id","")}}))
    if _M is not None and _L is not None:f=round(float(_M)+float(_L),4);g="SETTLED_DOMINANCE_DOUBLE_2X"if f>=1.99 else"SETTLED_DOMINANCE_FLOOR_1X";_h.append((_q,g,f,.0));continue
    if _y=="B3_BARRIER_MONO_BOX"and _3>=e+9e2:
     _T=str(m.get("direction")or"UP").upper();_w=await _Z.run_in_executor(None,fetch_binance_window_extremes_sync,_o["asset_or_city"],float(_o["entry_ts"]),e,"1m")
     if _w is not None:t,s,_=_w;_v=float(_Q.get("strike")or.0);_u=float(_P.get("strike")or.0);_1=(_T=="UP"and t>=_v)or(_T=="DOWN"and s<=_v);_0=(_T=="UP"and t>=_u)or(_T=="DOWN"and s<=_u);f=(1. if _1 else.0)+(.0 if _0 else 1.);_h.append((_q,"SETTLED_BARRIER_MONO_2X"if f>=1.99 else"SETTLED_BARRIER_MONO_1X",f,.0))
     continue
    if _3>=e+360. and m.get("m15_start_iso"):
     _K=14400. if str(_Q.get("horizon"))=="4h"else(9e2 if str(_Q.get("horizon"))=="15m"else 3e2);_J=14400. if str(_P.get("horizon"))=="4h"else(9e2 if str(_P.get("horizon"))=="15m"else 3e2);_g=build_own_gamma_event_url(_o["asset_or_city"],str(_Q.get("horizon")or"15m"),e-_K);_f=build_own_gamma_event_url(_o["asset_or_city"],str(_P.get("horizon")or"5m"),e-_J);_e,_d=await asyncio.gather(c.fetch_json(_g,timeout=4.),c.fetch_json(_f,timeout=4.));_I=parse_closed_gamma_event_settlement(_e,str(_Q.get("side")or"UP"),_g);_H=parse_closed_gamma_event_settlement(_d,str(_P.get("side")or"DOWN"),_f)
     if _I is not None and _H is not None:f=round(_I+_H,4);g=("SETTLED_ORACLE_DOUBLE_2X"if f>=1.99 else("SETTLED_ORACLE_FLOOR_1X"if f>=.99 else"SETTLED_ORACLE_LOSS_0X"));_h.append((_q,g,f,.0))
    continue
   if _y in("N1_NEGRISK_CROSS_BOX","P1_PREOPEN_MAKER_STRADDLE","NR0_ZERO_FEE_SLATE_ARB")or bool(Y.get("legs")):
    m=_o.get("extra")or{};_c=m.get("legs")or[];e=float(_o["close_ts"])
    if m.get("v6_instant_realize"):
     if _3>=e:_h.append((_q,"SETTLED_V6_INSTANT_LOCK",float(m.get("guaranteed_payout")or _o.get("p_model_entry")or 1.),.0))
     continue
    J=bool(_c)and all(lg.get("token_id")and str(lg.get("venue","polymarket")).lower()=="polymarket"for lg in _c)
    if not J:
     if _3>=e and m.get("guaranteed_payout"):_h.append((_q,"SETTLED_V6_GUARANTEED_FLOOR",float(m["guaranteed_payout"]),.0))
     continue
    if _3<e+20.:
     R=None
     if(_3-float(_o.get("_last_book_poll_ts")or.0))>=30. and _c:
      _o["_last_book_poll_ts"]=_3;R=await asyncio.gather(*[c.fetch_json(f"{CLOB_URL}/book?token_id={lg['token_id']}",timeout=2.5)for lg in _c])
      if all(R):
       _o["last_bid"]=round(sum(extract_best_bid((b or{}).get("bids")or[])[0]for b in R),4);_b=float(_o.get("fee_rate")or.0);_S=c._try_early_overround_bid_unwind(_o,[{"bids":(b or{}).get("bids")or[],"fee_rate":float(lg.get("fee_rate",_b)),"fee_exponent":float(lg.get("fee_exponent",1.))}for lg,b in zip(_c,R)],_3)
       if _S is not None:_h.append((_q,"EARLY_OVERROUND_BID_UNWIND",_S[0],_S[1]));continue
     if(_3-float(_o.get("_last_gamma_chk_ts")or.0))<(30. if(R is not None and not all(R))else 120.):continue
     _o["_last_gamma_chk_ts"]=_3
    i=await asyncio.gather(*[c.resolve_via_gamma_market({"token_id":lg["token_id"],"side":lg.get("side","YES"),"extra":{"market_id":lg.get("market_id","")}})for lg in _c])
    if i and all(v is not None for v in i):f=round(sum(float(v)for v in i if v is not None)+float(m.get("guaranteed_coupon_per_share")or.0),4);_h.append((_q,"SETTLED_MULTI_LEG_ARB",f,.0))
    elif _y=="P1_PREOPEN_MAKER_STRADDLE"and _3>=e+9e2:_h.append((_q,"SETTLED_COMPLETE_SET_1X",1.,.0))
    elif m.get("v6_state_payoff_table")and m.get("guaranteed_payout")and _3>=e+9e2:_h.append((_q,"SETTLED_V6_GUARANTEED_FLOOR",float(m["guaranteed_payout"]),.0))
    continue
   if _y=="S2_EXACT_TWAP_LOCK":
    m=_o.get("extra")or{};e=float(_o["close_ts"])
    if _3<e+12.:
     _G=await c.fetch_json(f"{CLOB_URL}/book?token_id={_2}",timeout=2.5)
     if _G:_t,_=extract_best_bid(_G.get("bids")or[]);_o["last_bid"]=_t
     continue
    u=await c.resolve_via_gamma_market(_o)
    if u is not None:g="SETTLED_GAMMA_WIN"if u>=.99 else"SETTLED_GAMMA_LOSS";_h.append((_q,g,u,.0));continue
    if _3>=e+120. and m.get("start_iso"):
     E=build_own_gamma_event_url(_o["asset_or_city"],str(m.get("horizon")or"15m"),m["start_iso"]);l=await c.fetch_json(E,timeout=4.);q=parse_authoritative_close_price(l);z=float(m.get("open_price")or.0)
     if q is not None and z>.0:D=q>=z;B=D if str(_o.get("side")).upper()=="UP"else(not D);g="SETTLED_ORACLE_TWAP_WIN"if B else"SETTLED_ORACLE_TWAP_LOSS";_h.append((_q,g,1. if B else.0,.0))
    continue
   if _y in("B1_CONVEX_TAIL_YES","B2_BARRIER_NO_LOCK"):
    j=_o["asset_or_city"];k=float(_o["extra"].get("strike")or.0);d=_o["extra"].get("direction");Q=float(_o.get("_last_wick_chk_ts")or.0)
    if k>0 and(_3-Q)>=60.:
     _o["_last_wick_chk_ts"]=_3;y=float(_o["extra"].get("start_ts")or _o["entry_ts"]);_F=min(_3,float(_o["close_ts"]));_s=await _Z.run_in_executor(None,fetch_binance_window_extremes_sync,j,y,_F,"1m")
     if _s is not None:
      t,s,_=_s;x=(d=="UP"and t>=k)or(d=="DOWN"and s<=k)
      if x:C=1. if _o["side"]=="YES"else.0;_h.append((_q,"BARRIER_1M_WICK_SETTLED",C,.0));continue
   if(not c.single_scan and not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK")and c.is_in_exact_twap_lock_window(_3)and float(_o["close_ts"])>_3+120. and(_3-float(_o.get("_last_book_poll_ts")or.0))<20.):continue
   _o["_last_book_poll_ts"]=_3;bk=await c.fetch_json(f"{CLOB_URL}/book?token_id={_2}",timeout=3.)
   if bk:
    r,_=extract_best_bid(bk.get("bids")or[]);_o["last_bid"]=r;_E=_o.get("maker_tp_px")
    if _E and r>=float(_E)and(_3-_o["entry_ts"])>=15.:_h.append((_q,"MAKER_TP_FILLED",float(_E),.0));continue
    if _y in("M1_SVI_MAKER_SCALP","M4_SHOCK_STRIKE_CATCHUP")and r>0 and(_3-_o["entry_ts"])>=30.:
     n=float(_o["entry_vwap_t1000"]);_l=float(_o["close_ts"])-_3;X=.085 if _y=="M4_SHOCK_STRIKE_CATCHUP"else.075;G=9e2 if _y=="M4_SHOCK_STRIKE_CATCHUP"else 3600.
     if r<=n-X:h=CRYPTO_FEE_RATE*r*(1.-r);_h.append((_q,"HARD_STOP_SVI",max(.0,r-h),.0));continue
     if _l<=G:h=CRYPTO_FEE_RATE*r*(1.-r);_h.append((_q,"TIME_STOP",max(.0,r-h),.0));continue
    if _y=="M2_STRIKE_CONVERGENCE"and r>0 and(_3-_o["entry_ts"])>=30.:
     n=float(_o["entry_vwap_t1000"])
     if r<=max(.25,n-.22):h=CRYPTO_FEE_RATE*r*(1.-r);_h.append((_q,"SALVAGE_STOP",max(.0,r-h),.0));continue
   else:
    P=float(_o.get("_last_gamma_chk_ts")or.0)
    if(_3-P)>=60.:
     _o["_last_gamma_chk_ts"]=_3;u=await c.resolve_via_gamma_market(_o)
     if u is not None:g="SETTLED_GAMMA_WIN"if u>=.99 else"SETTLED_GAMMA_LOSS";_h.append((_q,g,u,.0));continue
   if _3>=float(_o["close_ts"])+30.:
    u=await c.resolve_via_gamma_market(_o)
    if u is not None:g="SETTLED_GAMMA_WIN"if u>=.99 else"SETTLED_GAMMA_LOSS";_h.append((_q,g,u,.0));continue
    if bk and _y in("BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY")and _3>=float(_o["close_ts"])+9e2:
     I,H=extract_best_bid(bk.get("bids")or[]);F=float(_o.get("entry_eff_px_t1000")or _o.get("entry_vwap_t1000")or.995);_D=float(_o.get("fee_rate")or.0);_C=float((_o.get("extra")or{}).get("fee_exponent")or 1.);O=I-(_D*((I*(1.-I))**_C)if _D>.0 else.0)
     if I>=.997 and H>=25. and O>=F+.002:
      _k=str((_o.get("extra")or{}).get("market_id")or"");_B=await c.fetch_json(f"{GAMMA_URL}/markets/{_k}",timeout=3.5)if _k else None;_r=str((_B or{}).get("umaResolutionStatus")or"").strip().lower()if isinstance(_B,dict)else""
      if _r=="disputed"or _3>=float(_o["close_ts"])+14400.:_h.append((_q,"UMA_DISPUTED_LOCK_PROFIT_RECYCLE",round(O,4),.0));continue
    if bk and _y not in("BOND1_UMA_RESOLUTION_CARRY","SP2_NBA_ENDGAME_LOCK"):
     r,_=extract_best_bid(bk.get("bids")or[]);_R=bk.get("asks")or[];_a=min((float(a["price"])for a in _R if float(a.get("size",0))>0),default=1.)
     if r>=.99:_h.append((_q,"SETTLED_WIN",1.,.0));continue
     if _a<=.01:_h.append((_q,"SETTLED_LOSS",.0,.0));continue
    if _y in("S5M_CHAINLINK_SNIPER","S4H_CHAINLINK_CONVERGENCE")and _3>=float(_o["close_ts"])+120.:
     m=_o.get("extra")or{}
     if m.get("start_iso"):
      E=build_own_gamma_event_url(_o["asset_or_city"],str(m.get("horizon")or"5m"),m["start_iso"]);l=await c.fetch_json(E,timeout=4.);q=parse_authoritative_close_price(l);z=float(m.get("open_price")or.0)
      if q is not None and z>.0:D=q>=z;B=D if str(_o.get("side")).upper()=="UP"else(not D);g="SETTLED_ORACLE_TWAP_WIN"if B else"SETTLED_ORACLE_TWAP_LOSS";_h.append((_q,g,1. if B else.0,.0));continue
    if _3>=float(_o["close_ts"])+9e2:
     if _y in("B1_CONVEX_TAIL_YES","B2_BARRIER_NO_LOCK"):
      j=_o["asset_or_city"];k=float(_o["extra"].get("strike")or.0);d=_o["extra"].get("direction");y=float(_o["extra"].get("start_ts")or _o["entry_ts"]);_j=await _Z.run_in_executor(None,fetch_binance_window_extremes_sync,j,y,float(_o["close_ts"]),"1m")
      if _j is not None and k>0:t,s,_=_j;x=(d=="UP"and t>=k)or(d=="DOWN"and s<=k);C=(1. if x else.0)if _o["side"]=="YES"else(.0 if x else 1.);_h.append((_q,"SETTLED_VERIFIED_1M_ORACLE",C,.0));continue
     elif _y=="U1_DAILY_UPDOWN_LOCK":
      j=_o["asset_or_city"];k=float(_o["extra"]["strike"]);e=float(_o["close_ts"]);w=await _Z.run_in_executor(None,fetch_binance_window_extremes_sync,j,e-120.,e,"1m")
      if w is not None and k>0:o=w[2];B=(o>=k)if str(_o["side"]).upper()=="UP"else(o<k);_h.append((_q,"SETTLED_VERIFIED_1M_CLOSE",1. if B else.0,.0));continue
     elif _y in("M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","M4_SHOCK_STRIKE_CATCHUP"):
      j=_o["asset_or_city"];k=float(_o["extra"]["strike"]);_A=bool(_o["extra"].get("is_downward"));e=float(_o["close_ts"]);w=await _Z.run_in_executor(None,fetch_binance_window_extremes_sync,j,e-120.,e,"1m")
      if w is not None and k>0:o=w[2];_i=(o<k)if _A else(o>k);B=_i if _o["side"]=="YES"else(not _i);_h.append((_q,"SETTLED_VERIFIED_1M_CLOSE",1. if B else.0,.0));continue
  for _q,_p,N,p in _h:
   _o=c.open_positions.pop(_q,None)
   if not _o:continue
   W={};A={};Z=(_o.get("extra")or{}).get("legging_drag_usd_by_tier")or{};V=p if isinstance(p,dict)else{}
   for _n,tf in _o["tier_fills"].items():M=float(tf["spent_usd"])+float(tf["fee_usd"]);L=float(V.get(_n,N));K=float(tf["shares"])*L;_z=round(K-M,2);W[_n]=_z;A[_n]=round(_z-float(Z.get(_n,.0)or.0),2)
   U=W.get("T1000",.0)>0;_o.update({"status":_p,"closed_ts":_3,"closed_utc":datetime.now(timezone.utc).isoformat(),"net_payout_per_share":round(N,4),"tier_pnls_usd":W,"legging_adjusted_tier_pnls_usd":A,"won":U});c.closed_positions.append(_o);c._append_ledger({"event":"SHADOW_CLOSE",**_o});logger.info(f"[CLOSE:{_o['sleeve']}] {_o['title']} ({_o['side']}) -> {_p} | PnL T100=${W.get('T100',0):+.2f} T1000=${W.get('T1000',0):+.2f} T5000=${W.get('T5000',0):+.2f}")
 def write_state_files(a,opps=None):
  E=list(opps)if opps is not None else list(getattr(a,"top_opportunities",None)or[])
  if len(a.closed_positions)>60:
   for D in range(len(a.closed_positions)-50):
    if"title"in a.closed_positions[D]or"tier_fills"in a.closed_positions[D]:a.closed_positions[D]=a._slim_closed_position_record(a.closed_positions[D])
  if len(getattr(a,"authoritative_strike_cache",{}))>2000:
   for S in list(a.authoritative_strike_cache.keys())[:-1500]:a.authoritative_strike_cache.pop(S,None)
  i=list(a.open_positions.values());d=list(a.closed_positions)
  if len(a.entered_keys)>5000:A={str(p.get("dedupe_key")or"")for p in i};a.entered_keys=A|set(list(a.entered_keys)[-3000:])
  t=read_global_positions_shm();h=[p for T,U in(t.get("daemons")or{}).items()if T!="alpha124_shadow"and isinstance(U,dict)for p in(U.get("positions")or[])];o=rank_opportunities_capital_auction(E,active_global_positions=i+h)[:25];a.top_opportunities=o;publish_global_positions_shm("alpha124_shadow",i);w={};n={"T100":.0,"T1000":.0,"T5000":.0}
  for R in BANKROLL_TICKETS["T1000"].keys():
   z=str(R).startswith("D1_");g=_filter_epoch_closed_positions(str(R),[p for p in d if p.get("sleeve")==R]);v=[p for p in g if not(z and p.get("status")!="MAKER_ANCHOR_UNHEDGED_SCRATCH"and float(p.get("entry_eff_px_t1000")or 1.)<.9)];f=len(g)-len(v);C=[p for p in i if p.get("sleeve")==R];P=sum(1 for p in v if p.get("won"));G=sum(float(p.get("tier_pnls_usd",{}).get("T1000",.0))for p in v);s=sum(float(p.get("legging_adjusted_tier_pnls_usd",p.get("tier_pnls_usd",{})).get("T1000",.0))for p in v)
   for Q in n:n[Q]=round(n[Q]+sum(float(p.get("tier_pnls_usd",{}).get(Q,.0))for p in v),2)
   w[R]={"open":len(C),"closed":len(v),"wins":P,"losses":len(v)-P,"win_rate_pct":round(1e2*P/len(v),2)if v else.0,"realized_pnl_t1000_usd":round(G,2),"legging_adjusted_pnl_t1000_usd":round(s,2),"excluded_anti_box":f,"quarantined":is_shadow_sleeve_quarantined(R),"grad8_live_promoted":bool(len(v)>=8 and P==len(v)and round(G,2)>.0 and round(s,2)>.0 and not is_shadow_sleeve_quarantined(R)and(R!="XV_SUBSET_NO_BOX"or sum(1 for p in v if not bool((p.get("extra")or{}).get("neg_risk_augmented",False))and(str((p.get("extra")or{}).get("box_type")or"")=="NEGRISK_2LEG"or len((p.get("extra")or{}).get("legs")or[])==2)and float((p.get("tier_pnls_usd")or{}).get("T1000",.0)or.0)>.0)>=8)and R not in{"XV_FX_INVARIANT_CAD_USD_BOX","DERIBIT_VERTICAL_SUPER_REP","XV_HALFTIME_FREEZE_CORRIDOR","HEDGED_PRESPLIT_CONV_GUN","YIELD_STACKED_CARRY_BOX"})}
  c={"D1_SAME_ORACLE_DOMINANCE_BOX","D1_4H_DOMINANCE_BOX","D1_QUIET_BOOK_BOX"};m={}
  for M in DOMINANCE_ASSETS:O=[p for p in d if str(p.get("sleeve")or"")in c and str(p.get("asset_or_city")or"").upper()==M and(p.get("status")=="MAKER_ANCHOR_UNHEDGED_SCRATCH"or float(p.get("entry_eff_px_t1000")or 1.)>=.9)];N=[p for p in i if str(p.get("sleeve")or"")in c and str(p.get("asset_or_city")or"").upper()==M];B=sum(1 for p in O if p.get("won"));y=sum(float(p.get("tier_pnls_usd",{}).get("T1000",.0))for p in O);j=sum(float(p.get("legging_adjusted_tier_pnls_usd",p.get("tier_pnls_usd",{})).get("T1000",.0))for p in O);m[M]={"open":len(N),"closed":len(O),"wins":B,"losses":len(O)-B,"win_rate_pct":round(1e2*B/len(O),2)if O else.0,"realized_pnl_t1000_usd":round(y,2),"legging_adjusted_pnl_t1000_usd":round(j,2)}
  F=round(time.time(),3);l=a.__dict__.get("_dormant_ws_cache");x=len(l[2])if(isinstance(l,tuple)and len(l)==3)else 0;k=sum(1 for T in list(a.uma_proposed_markets.values())if isinstance(T,dict)and(.9<=float(T.get("bestBid")or.0)<=.9985 or.002<=float(T.get("bestAsk")or 1.)<=.1));e={"zerofee_binaries":len(getattr(a,"zerofee_general_binaries",None)or()),"uma_proposed":len(a.uma_proposed_markets),"uma_hot_bonds":k,"negrisk_convert_slates":len(getattr(a,"negrisk_convert_slates",None)or{}),"cal1_ladders":len(getattr(a,"cal1_ladders",None)or{}),"ws_subscribed_tokens":len(getattr(a,"_ws_subscribed_tokens",None)or()),"ws_shards_active":len(getattr(a,"_ws_shard_tokens",None)or{}),"dormant_ws_pinned_tokens":x,"maker_pending":(len(a.pending_maker_orders)+len(a.pending_maker_anchors)+len(a.pending_zero_fee_maker_anchors))};b={"emitted_total":int(getattr(a,"_live_bridge_emits_total",0)or 0),"emitted_by_sleeve":dict(getattr(a,"_live_bridge_emits_by_sleeve",None)or{}),"last_emit_ts":float(getattr(a,"_live_bridge_last_emit_ts",.0)or.0),"pending_maker_orders_count":len(a.pending_maker_orders)};L={"updated_at_utc":datetime.now(timezone.utc).isoformat(),"updated_ts":F,"started_at":a.started_at,"cycle_count":a.cycle_count,"calibration":{"weather_sigma_c":a.weather_sigma_c,"barrier_wick_mult":a.barrier_wick_mult},"spots":dict(a.spots),"catalog_counts":e,"live_bridge_telemetry":b,"markets_monitored":{"weather_city_events":len(a.weather_events),"barrier_hit_rungs":len(a.barrier_rungs),"multistrike_ladders":len(a.strike_ladders),"negrisk_bracket_ladders":len(a.negrisk_ladders),"daily_updown_markets":len(a.daily_updown_markets),"pyth_daily_markets":len(a.pyth_daily_markets),"pyth_barrier_rungs":len(a.pyth_barrier_rungs),"pyth_close_ladders":len(a.pyth_close_ladders),"nba_zero_fee_games":len(a.nba_games),"live_nba_scoreboard_games":len(a.live_nba_board),"uma_proposed_markets":len(a.uma_proposed_markets),"negrisk_zero_fee_slates":len(a.negrisk_zero_slates),"negrisk_convert_slates":e["negrisk_convert_slates"],"zerofee_general_binaries":e["zerofee_binaries"],"cal1_ladders":e["cal1_ladders"],"ws_subscribed_tokens":e["ws_subscribed_tokens"],"counting_slates":len(a.counting_slates),"fomc_lp_markets":len(a.fomc_truth_legs)//2,"oil_senate_markets":len(a.oil_senate_truth_legs)//2,"hourly_12pm_pairs":len(a.hourly_12pm_markets),"same_oracle_dominance_pairs":len(a.dominance_pairs),"dominance_4h_pairs":len(a.dominance_4h_pairs),"exact_twap_lock_candles":len(a.twap_candles),"s5m_sniper_candles":len(a.s5m_candles),"s4h_candles":len(a.s4h_candles),"preopen_15m_candles":len(a.preopen_15m_candles)},"portfolio_realized_pnl_by_bankroll_usd":n,"gatling_projection":compute_gatling_trajectory_projection(starting_nav_usd=60.92),"by_sleeve":w,"per_strategy":w,"by_d1_asset":m,"open_positions_count":len(i),"pending_maker_orders_count":len(a.pending_maker_orders),"pending_maker_anchors_count":len(a.pending_maker_anchors),"pending_zero_fee_maker_anchors_count":len(a.pending_zero_fee_maker_anchors),"pending_preopen_straddles_count":len(a.pending_preopen_straddles),"pending_maker_orders":list(a.pending_maker_orders.values()),"open_positions":i,"recent_closed_positions":d[-30:],"v6_expansion":getattr(a,"_v6_expansion_stats",None)};K=STATE_FILE.with_suffix(".tmp");K.write_text(json.dumps(L,indent=2),encoding="utf-8");os.replace(K,STATE_FILE)
  if STATE_FILE==(DATA_DIR/"alpha124_shadow_state.json")or LIVE_ALPHA124_STATE_MIRROR_FILE!=(LIVE_POLYMARKET_DIR/"alpha124_shadow_state.json"):
   try:LIVE_ALPHA124_STATE_MIRROR_FILE.parent.mkdir(parents=True,exist_ok=True);J=LIVE_ALPHA124_STATE_MIRROR_FILE.with_suffix(".tmp");J.write_text(json.dumps({"updated_at_utc":L["updated_at_utc"],"updated_ts":F,"started_at":a.started_at,"cycle_count":a.cycle_count,"open_positions_count":len(i),"pending_maker_orders_count":len(a.pending_maker_orders),"catalog_counts":e,"live_bridge_telemetry":b,"markets_monitored":L["markets_monitored"],"by_sleeve":w,"per_strategy":w,"by_d1_asset":m},indent=2),encoding="utf-8");os.replace(J,LIVE_ALPHA124_STATE_MIRROR_FILE)
   except Exception:pass
  I=OPPS_FILE.with_suffix(".tmp");I.write_text(json.dumps({"updated_at_utc":L["updated_at_utc"],"top_opportunities":o},indent=2),encoding="utf-8");os.replace(I,OPPS_FILE);H=time.time();a.__dict__["_last_state_write_ts"]=H
  if(H-float(getattr(a,"_last_proj_write_ts",.0)))>=60.:
   a._last_proj_write_ts=H
   try:
    import importlib;import scripts.polymarket_daily_projections as _proj_mod;r=getattr(_proj_mod,"__file__",None)
    if r:
     u=Path(r).stat().st_mtime_ns;q=getattr(a,"_proj_mod_mtime_ns",None)
     if q is None:a._proj_mod_mtime_ns=u
     elif u!=q:_proj_mod=importlib.reload(_proj_mod);a._proj_mod_mtime_ns=u
    _proj_mod.write_live_projections_atomic(days=90)
   except Exception:pass
 def _get_state_io_executor(a):
  b=a.__dict__.get("_state_io_executor")
  if b is None:import concurrent.futures;b=concurrent.futures.ThreadPoolExecutor(max_workers=1,thread_name_prefix="a124-state-io");a.__dict__["_state_io_executor"]=b
  return b
 async def write_state_files_async(a,opps):
  b=a.__dict__.get("_state_write_lock")
  if b is None:b=asyncio.Lock();a.__dict__["_state_write_lock"]=b
  async with b:c=asyncio.get_running_loop();await c.run_in_executor(a._get_state_io_executor(),a.write_state_files,list(opps))
 @staticmethod
 def _extract_reconciled_live_equity_usd(lh_d):
  if not isinstance(lh_d,dict):return.0
  for c in("reconciled_nav_usd","locked_floor_equity","locked_box_payout_floor_equity_usd","live_bankroll","live_bankroll_usd","total_account_equity","total_account_equity_usd"):
   b=lh_d.get(c)
   if b is not None:
    try:
     a=float(b)
     if a>.0:return a
    except(TypeError,ValueError):continue
  return.0
 async def _run_bg_state_heartbeat(a):
  while not a.single_scan:
   await asyncio.sleep(30.);d=time.time();c=float(a.__dict__.get("_last_state_write_ts")or.0);b=float(a.__dict__.get("_last_main_loop_tick_mono")or.0)
   if((c<=.0 or(d-c)>=45.)and b>.0 and(time.monotonic()-b)<6e2):
    try:await a.write_state_files_async(list(getattr(a,"top_opportunities",None)or[]))
    except Exception:pass
 async def _run_bg_discovery(a):
  try:await a.discover_all_markets();a._evict_stale_caches()
  except Exception as b:logger.warning(f"Background discovery notice: {b}")
 async def _run_bg_mid_crypto(a):
  try:b=[];await a.scan_multistrike_markets(b);await a.scan_daily_updown_locks(b);await a.scan_barrier_markets(b);a.cached_mid_opps=b
  except Exception as c:logger.warning(f"Background mid-crypto scan notice: {c}")
 async def _run_bg_weather(a):
  try:c=[];await a.scan_weather_markets(c);a.cached_weather_opps=c
  except Exception as b:logger.warning(f"Background weather scan notice: {b}")
 async def _get_pyth_intraday(a,asset,now_ts):
  g=PYTH_ASSET_CONFIG.get(asset.upper())
  if not g:return None
  f,_,_,_,c=g;e=a.pyth_intraday_cache.get(f);b=e[1]if(e is not None and(now_ts-e[0])<90.)else None
  if b is None:
   b=await asyncio.to_thread(fetch_yahoo_1m_intraday_sync,f,c)
   if b is not None:a.pyth_intraday_cache[f]=(now_ts,b)
  d=await asyncio.to_thread(fetch_pyth_intraday_or_spot_sync,asset,f,c,pyth_stream=getattr(a,"_pyth_hermes_stream",None),chainlink_stream=getattr(a,"_chainlink_ws",None),cached_yahoo=b,yahoo_ttl_sec=90.,use_pyth_hermes=not bool(getattr(a,"single_scan",False)),now_ts=now_ts);return d if d is not None else b
 async def scan_tradfi_and_sports_markets(a,opps_out):
  e=time.time()
  for c,d in(("tradfi_sports_nr",a._scan_tradfi_sports_nr_core),("phase2_macro_uma",a._scan_phase2_macro_counting_gas),("frontier_v2",a._scan_frontier_v2_sleeves),("frontier_v3",a._scan_frontier_v3_sleeves),("frontier_v4",a._scan_frontier_v4_sleeves)):
   try:await d(opps_out,e)
   except Exception as b:logger.warning(f"[ALPHA-124] Sub-scanner {c} notice: {b}")
 async def _scan_tradfi_sports_nr_core(a,opps_out,now):
  i=sorted({r.asset for r in a.pyth_barrier_rungs.values()if r.end_ts>now+120}|{rgs[0].asset for rgs in a.pyth_close_ladders.values()if rgs and rgs[0].end_ts>now+120});w={}
  for a_p in i:
   fd=await a._get_pyth_intraday(a_p,now)
   if fd:w[a_p]=fd
  _x=[]
  for r in a.pyth_barrier_rungs.values():
   if r.end_ts<=now+120 or r.asset not in w:continue
   L=float(w[r.asset]["spot"])
   if L>0 and abs(math.log(r.strike/L))<=.25:_x.append(r)
  M=[]
  for rgs in a.pyth_close_ladders.values():
   for rc in rgs:
    if rc.end_ts<=now+120 or rc.asset not in w:continue
    L=float(w[rc.asset]["spot"])
    if L>0 and abs(math.log(rc.strike/L))<=.14:M.append(rc)
  Z=([r.yes_token for r in _x]+[r.no_token for r in _x]+[rc.yes_token for rc in M]+[rc.no_token for rc in M]);_w=await a.fetch_books_batch(Z,timeout=3.5)if Z else{};B=[];j=collections.defaultdict(list)
  for r in _x:
   _v,A=_w.get(r.yes_token),_w.get(r.no_token)
   if not _v or not A:continue
   cfg=PYTH_ASSET_CONFIG[r.asset];_,m,l,h,_=cfg;fd=w[r.asset];_al=float(fd["spot"]);n=now>=r.start_ts;_aT=window_extremes_from_bars(fd["bars"],r.start_ts,now)if n else None
   if n and now>=r.start_ts+3e2 and l and m in("EQUITY_RTH","CME_23H")and _aT is not None and f"B4_PYTH_{r.market_id}"not in a.entered_keys:
    _bn,_bm=_aT;_ak=.0015 if m=="EQUITY_RTH"else max(.008,2.5*h);K=.78 if m=="EQUITY_RTH"else.88
    if(r.direction=="UP"and _bn>=r.strike*(1.+_ak))or(r.direction=="DOWN"and _bm<=r.strike*(1.-_ak)):
     _U,_=extract_best_bid(_v.get("bids")or[]);_aS=walk_l2_book_asks(_v.get("asks")or[],1e2,fee_rate=r.fee_rate,min_l1_usd=15.,max_ask_px=.99,fee_exponent=r.fee_exponent)
     if _aS.get("filled")and _U>=K and.85<=float(_aS["eff_px"])<=.986:opps_out.append({"sleeve":"B4_TOUCHED_BARRIER_WICK_LOCK","market":f"{r.asset} Pyth Breached Wick Lock: {r.question}","ask_vwap":_aS["eff_px"],"p_model":1.,"net_edge":round(1.-float(_aS["eff_px"]),4),"l1_usd":_aS["l1_usd"]});await a.open_shadow_position(sleeve="B4_TOUCHED_BARRIER_WICK_LOCK",dedupe_key=f"B4_PYTH_{r.market_id}",asset_or_city=r.asset,title=r.question,side_label="YES",token_id=r.yes_token,fee_rate=r.fee_rate,p_model=1.,close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"strike":r.strike,"direction":r.direction,"session_class":m,"fee_exponent":r.fee_exponent},prefetched_book=_v);continue
   _u=walk_l2_book_asks(_v.get("asks")or[],35.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);_t=walk_l2_book_asks(A.get("asks")or[],35.,fee_rate=r.fee_rate,min_l1_usd=8.,fee_exponent=r.fee_exponent);_aR={"asset":r.asset,"event_id":r.event_id,"strike":r.strike,"direction":r.direction,"market_id":r.market_id,"condition_id":r.condition_id,"yes_token":r.yes_token,"no_token":r.no_token,"fee_rate":r.fee_rate,"fee_exponent":r.fee_exponent,"ask_yes":_u.get("vwap")if _u.get("filled")else None,"ask_no":_t.get("vwap")if _t.get("filled")else None,"bk_yes":_v,"bk_no":A,"start_ts":r.start_ts,"end_ts":r.end_ts};B.append(_aR);j[r.event_id].append(_aR);_T=compute_effective_trading_hours(now,r.end_ts,m);Y=is_same_continuous_session(now,r.end_ts,m);D=_aT is not None and((r.direction=="UP"and _aT[0]>=r.strike*(1.-h))or(r.direction=="DOWN"and _aT[1]<=r.strike*(1.+h)))
   if n and l and Y and not D and.25<=_T<=3.5:
    _aQ=evaluate_pyth_session_barrier_no_lock(_al,r.strike,r.direction,_T,float(fd["sigma_session"]),h);_aj=float(_aQ["p_no"])
    if _aj>=.94:
     _ai,_=extract_best_bid(A.get("bids")or[]);_bl=walk_l2_book_asks(A.get("asks")or[],1e2,fee_rate=r.fee_rate,min_l1_usd=15.,fee_exponent=r.fee_exponent)
     if _bl.get("filled")and.78<=float(_bl["eff_px"])<=.955 and _ai>0 and(float(_bl["vwap"])-_ai)<=.04:
      _S=_aj-float(_bl["eff_px"]);_bk=evaluate_barrier_no_net_ev(1.-_aj,float(_bl["vwap"]),fee_rate=r.fee_rate)
      if _S>=.025:opps_out.append({"sleeve":"CM_B2_PYTH_SESSION_NO_LOCK","market":f"{r.asset} Pyth NO ({_T:.1f}h sess): {r.question}","ask_vwap":_bl["eff_px"],"p_model":_aj,"net_edge":round(_S,4),"l1_usd":_bl["l1_usd"]})
      if _S>=.035 and _bk["eligible"]:await a.open_shadow_position(sleeve="CM_B2_PYTH_SESSION_NO_LOCK",dedupe_key=f"CMB2_{r.market_id}",asset_or_city=r.asset,title=r.question,side_label="NO",token_id=r.no_token,fee_rate=r.fee_rate,p_model=_aj,close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"strike":r.strike,"direction":r.direction,"eff_session_hours":round(_T,2),"fee_exponent":r.fee_exponent},prefetched_book=A)
   _R=a.prev_pyth_spots.get(r.asset,.0)
   if n and not a.single_scan and is_in_scheduled_macro_catalyst_window(now)[0]and(now-float(getattr(a,"_last_macro_rss_ts",.0)))>=2.:a._last_macro_rss_ts=now;await asyncio.to_thread(poll_macro_catalyst_feeds_sync,now)
   if n and l and Y and not D and _R>.0:
    _aP=evaluate_pyth_catalyst_shock(r.asset,_R,_al,r.strike,r.direction,_T,float(fd["sigma_session"]),now)
    if _aP.get("eligible"):
     _Q=str(_aP["side"]);_ah=r.yes_token if _Q=="YES"else r.no_token;_aO=_v if _Q=="YES"else A;_bj=walk_l2_book_asks(_aO.get("asks")or[],BANKROLL_TICKETS["T1000"]["CM_SHOCK_PYTH_CATALYST"],fee_rate=r.fee_rate,min_l1_usd=15.,fee_exponent=r.fee_exponent)
     if _bj.get("filled")and.18<=float(_bj["eff_px"])<=.88:
      _P=float(_aP["p_fair"])-float(_bj["eff_px"])
      if _P>=.045:opps_out.append({"sleeve":"CM_SHOCK_PYTH_CATALYST","market":f"{r.asset} [{_aP['catalyst']}] {_Q}: {r.question}","ask_vwap":_bj["eff_px"],"p_model":_aP["p_fair"],"net_edge":round(_P,4),"l1_usd":_bj["l1_usd"],"close_ts":r.end_ts});await a.open_shadow_position(sleeve="CM_SHOCK_PYTH_CATALYST",dedupe_key=f"CMSHK_{r.market_id}_{_Q}_{int(now//900)}",asset_or_city=r.asset,title=f"{r.question} [{_aP['catalyst']}]",side_label=_Q,token_id=_ah,fee_rate=r.fee_rate,p_model=float(_aP["p_fair"]),close_ts=r.end_ts,extra={"market_id":r.market_id,"condition_id":r.condition_id,"catalyst":_aP["catalyst"],"delta_p":_aP["delta_p"],"ret_pct":_aP["ret_pct"],"fee_exponent":r.fee_exponent},tp_target_px=min(.95,round(float(_bj["eff_px"])+.06,3)),prefetched_book=_aO)
  for a_p,_bi in w.items():a.prev_pyth_spots[a_p]=float(_bi["spot"])
  u=[]
  for rc in M:
   _v,A=_w.get(rc.yes_token),_w.get(rc.no_token)
   if not _v or not A:continue
   _u=walk_l2_book_asks(_v.get("asks")or[],35.,fee_rate=rc.fee_rate,min_l1_usd=8.,fee_exponent=rc.fee_exponent);_t=walk_l2_book_asks(A.get("asks")or[],35.,fee_rate=rc.fee_rate,min_l1_usd=8.,fee_exponent=rc.fee_exponent);u.append({"asset":rc.asset,"strike":rc.strike,"is_downward":rc.is_downward,"market_id":rc.market_id,"condition_id":rc.condition_id,"yes_token":rc.yes_token,"no_token":rc.no_token,"fee_rate":rc.fee_rate,"fee_exponent":rc.fee_exponent,"ask_yes":_u.get("vwap")if _u.get("filled")else None,"ask_no":_t.get("vwap")if _t.get("filled")else None,"bk_yes":_v,"bk_no":A,"end_ts":rc.end_ts});cfg=PYTH_ASSET_CONFIG[rc.asset];_,m,l,h,_=cfg;fd=w[rc.asset];X=compute_effective_trading_hours(now,rc.end_ts,m)
   if l and is_same_continuous_session(now,rc.end_ts,m)and.08<=X<=.75:
    _aN=evaluate_pyth_session_close_lock(float(fd["spot"]),rc.strike,rc.is_downward,X,float(fd["sigma_session"]),h)
    if _aN["eligible"]:
     _ad=str(_aN["side"]);_aM=rc.yes_token if _ad=="YES"else rc.no_token;_bh=_v if _ad=="YES"else A;_ac,_=extract_best_bid(_bh.get("bids")or[]);_bg=walk_l2_book_asks(_bh.get("asks")or[],1e2,fee_rate=rc.fee_rate,min_l1_usd=15.,fee_exponent=rc.fee_exponent)
     if _bg.get("filled")and.78<=float(_bg["eff_px"])<=.955 and _ac>0 and(float(_bg["vwap"])-_ac)<=.04:
      _O=float(_aN["p_lock"])-float(_bg["eff_px"])
      if _O>=.02:opps_out.append({"sleeve":"CM_U1_PYTH_CLOSE_LOCK","market":f"{rc.asset} Close Lock ({_ad}, z={_aN['z_session']:.2f}): {rc.question}","ask_vwap":_bg["eff_px"],"p_model":_aN["p_lock"],"net_edge":round(_O,4),"l1_usd":_bg["l1_usd"]})
      if _O>=.03:await a.open_shadow_position(sleeve="CM_U1_PYTH_CLOSE_LOCK",dedupe_key=f"CMU1_{rc.market_id}_{_ad}",asset_or_city=rc.asset,title=rc.question,side_label=_ad,token_id=_aM,fee_rate=rc.fee_rate,p_model=float(_aN["p_lock"]),close_ts=rc.end_ts,extra={"market_id":rc.market_id,"condition_id":rc.condition_id,"strike":rc.strike,"z_session":_aN["z_session"],"fee_exponent":rc.fee_exponent},prefetched_book=_bh)
  for _ab,_N in w.items():
   _aL=PYTH_ASSET_CONFIG.get(_ab)
   if not _aL:continue
   _,_aa,_M,_,_=_aL;J=[rh for rh in B if rh["asset"]==_ab and rh.get("ask_no")is not None]
   if not J:continue
   W=min(J,key=lambda x:(float(x["end_ts"]),abs(math.log(float(x["strike"])/max(1e-6,float(_N["spot"]))))));_L=compute_effective_trading_hours(now,float(W["end_ts"]),_aa);_9=is_same_continuous_session(now,float(W["end_ts"]),_aa);_s,_K=extract_best_bid(W["bk_no"].get("bids")or[]);_r,_q=a._best_ask_sz(W["bk_no"]);a._record_market_telemetry(key=f"PYTH_SNAP_{_ab}",min_interval_sec=120.,now_ts=now,sig=(round(float(_N["spot"]),3),round(_r,3),round(_s,3)),payload={"type":"PYTH_ASSET_SESSION_SNAP","asset":_ab,"session_class":_aa,"exact_directional_ok":_M,"spot":round(float(_N["spot"]),4),"sigma_session":_N["sigma_session"],"eff_session_hours":round(_L,2),"same_session":_9,"near_strike":W["strike"],"near_dir":W["direction"],"near_ask_no":round(_r,4)if _r<1. else None,"near_bid_no":round(_s,4)if _s>0 else None,"near_ask_l1_usd":round(_r*_q,2)if _r<1. else.0})
  t=[]
  for _J,_I in j.items():
   if len(_I)<2:continue
   _8=detect_barrier_monotonicity_boxes(_I,fee_rate=.0,max_box_cost_net=1.15)
   if _8:pd0=_8[0];a._record_market_telemetry(key=f"CMB3_DIAG_{_J}",min_interval_sec=90.,now_ts=now,sig=(pd0["direction"],pd0["low_strike"],pd0["high_strike"],pd0["box_cost_net"]),payload={"type":"PYTH_BARRIER_MONO_BEST","asset":_I[0]["asset"],"event_id":_J,"net_box_l1":pd0["box_cost_net"],"label":pd0["label"]})
   _aK={str(q["yes_token"]):q for q in _I};_aJ={str(q["no_token"]):q for q in _I}
   for ba in _8:
    if float(ba["box_cost_net"])>1.035:continue
    qy,qn=_aK.get(ba["yes_token"]),_aJ.get(ba["no_token"])
    if qy and qn:la={"token_id":ba["yes_token"],"opp_token_id":ba["yes_opp_token"],"condition_id":ba["leg_yes_condition_id"],"side":"YES","label":f"YES_{ba['direction']}","market_id":ba["leg_yes_market_id"],"fee_rate":float(qy.get("fee_rate",.0)),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(qy["strike"])};lb={"token_id":ba["no_token"],"opp_token_id":ba["no_opp_token"],"condition_id":ba["leg_no_condition_id"],"side":"NO","label":f"NO_{ba['direction']}","market_id":ba["leg_no_market_id"],"fee_rate":float(qn.get("fee_rate",.0)),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(qn["strike"])};t.append((qy["asset"],f"CMB3_MONO_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",la,lb,qy["bk_yes"],qn["bk_no"],float(qy["end_ts"]),f"{qy['asset']} Pyth Box {ba['label']}"))
  _p=detect_pyth_calendar_inclusion_boxes(B,max_box_cost_net=1.15)
  if _p:cd0=_p[0];a._record_market_telemetry(key=f"CMB3_CAL_BEST_{cd0['asset']}",min_interval_sec=90.,now_ts=now,sig=(cd0["direction"],cd0["strike"],cd0["box_cost_net"]),payload={"type":"PYTH_CALENDAR_BEST","asset":cd0["asset"],"net_box_l1":cd0["box_cost_net"],"label":cd0["label"]})
  for cal in _p:
   if float(cal["box_cost_net"])>1.035:continue
   qy,qn=cal["yes_row"],cal["no_row"];la={"token_id":qy["yes_token"],"opp_token_id":qy["no_token"],"condition_id":qy["condition_id"],"side":"YES","label":"YES_LONG","market_id":qy["market_id"],"fee_rate":float(qy.get("fee_rate",.0)),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(qy["strike"])};lb={"token_id":qn["no_token"],"opp_token_id":qn["yes_token"],"condition_id":qn["condition_id"],"side":"NO","label":"NO_SHORT","market_id":qn["market_id"],"fee_rate":float(qn.get("fee_rate",.0)),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(qn["strike"])};t.append((cal["asset"],f"CMB3_CAL_{qy['market_id']}_{qn['market_id']}",la,lb,qy["bk_yes"],qn["bk_no"],float(cal["close_ts"]),f"{cal['asset']} Calendar Box {cal['label']}"))
  _o=detect_pyth_close_vs_hit_boxes(u,B,now_ts=now,max_box_cost_net=1.15)
  if _o:vd0=_o[0];a._record_market_telemetry(key=f"CMB3_CVH_BEST_{vd0['asset']}",min_interval_sec=90.,now_ts=now,sig=(vd0["strike_hit"],vd0["strike_close"],vd0["box_cost_net"]),payload={"type":"PYTH_CLOSE_VS_HIT_BEST","asset":vd0["asset"],"net_box_l1":vd0["box_cost_net"],"label":vd0["label"]})
  for cvh in _o:
   if float(cvh["box_cost_net"])>1.035:continue
   qy,qn=cvh["yes_row"],cvh["no_row"];la={"token_id":qy["yes_token"],"opp_token_id":qy["no_token"],"condition_id":qy["condition_id"],"side":"YES","label":"YES_HIT","market_id":qy["market_id"],"fee_rate":float(qy.get("fee_rate",.0)),"fee_exponent":float(qy.get("fee_exponent",1.)),"strike":float(qy["strike"])};lb={"token_id":qn["no_token"],"opp_token_id":qn["yes_token"],"condition_id":qn["condition_id"],"side":"NO","label":"NO_CLOSE","market_id":qn["market_id"],"fee_rate":float(qn.get("fee_rate",.0)),"fee_exponent":float(qn.get("fee_exponent",1.)),"strike":float(qn["strike"])};t.append((cvh["asset"],f"CMB3_CVH_{qy['market_id']}_{qn['market_id']}",la,lb,qy["bk_yes"],qn["bk_no"],float(cvh["close_ts"]),f"{cvh['asset']} Close-vs-Hit Box {cvh['label']}"))
  t.sort(key=lambda x:((float(x[6])-now)>64800.,float(x[6])))
  for _H,_5,la,lb,_i,_h,_bf,_G in t:
   _be=walk_equal_shares_dominance_box(_i.get("asks")or[],_h.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["CM_B3_PYTH_BARRIER_BOX"],fee_rate_a=float(la["fee_rate"]),fee_rate_b=float(lb["fee_rate"]),fee_exponent_a=float(la.get("fee_exponent",1.)),fee_exponent_b=float(lb.get("fee_exponent",1.)),max_box_cost_net=.994,min_shares=6,min_box_notional_usd=5.5)
   if _be.get("filled"):
    opps_out.append({"sleeve":"CM_B3_PYTH_BARRIER_BOX","market":_G,"ask_vwap":round(float(_be["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_be["box_cost_net"]),4),"l1_usd":_be["l1_usd"],"close_ts":_bf});e=False
    if float(_be["box_cost_net"])<=.993 and(_bf-now)<=172800.:e=a.emit_live_two_leg_box_candidate(sleeve_source="CM_B3_PYTH_BARRIER_BOX",box_type="BARRIER_MONO",asset=_H,dedupe_key=_5,leg_a=la,leg_b=lb,bk_a=_i,bk_b=_h,close_ts=_bf,now_ts=now,k_low=min(float(la.get("strike")or 1e2),float(lb.get("strike")or 1e2)),k_high=max(float(la.get("strike")or 1e2),float(lb.get("strike")or 1e2)))
    if(_bf-now)<=172800.:await a.open_shadow_two_leg_box(sleeve="CM_B3_PYTH_BARRIER_BOX",dedupe_key=_5,asset=_H,title=_G,leg_a=la,leg_b=lb,bk_a=_i,bk_b=_h,close_ts=_bf,max_box_cost_net=.994,extra={"is_pyth_zero_fee_box":True})
    if not e:a.post_zero_fee_maker_anchor_box("CM_B3",_H,f"ZFA_{_5}",la,lb,_i,_h,_bf,_G,now,live_emit_only=bool((_bf-now)<=172800.))
   else:a.post_zero_fee_maker_anchor_box("CM_B3",_H,f"ZFA_{_5}",la,lb,_i,_h,_bf,_G,now)
  for _4 in list(a.nba_games.values()):
   if now>_4.tipoff_ts+6.*3600.:a.nba_games.pop(_4.event_id,None);continue
   _l=_4.margin_legs+_4.total_legs;_k=sorted({lg.token_id for lg in _l})
   if len(_k)<4:continue
   _F=await a.fetch_books_batch(_k,timeout=3.5);v={}
   for t_n,A in _F.items():
    _bd,_bc=a._best_ask_sz(A)
    if _bd<1. and _bc*_bd>=8.:v[t_n]=_bd
   _j=detect_nba_dominance_boxes(_4,v,max_box_cost_net=1.12)
   if _j:
    nd0=_j[0];_bb,_ba=nd0["leg_a"],nd0["leg_b"];_a9=_F.get(_bb.token_id)or{};_a8=_F.get(_ba.token_id)or{};aa0,sa0=a._best_ask_sz(_a9);ab0,sb0=a._best_ask_sz(_a8);ba0,_=extract_best_bid(_a9.get("bids")or[]);bb0,_=extract_best_bid(_a8.get("bids")or[]);V=[]
    if ba0>0 and(aa0-ba0)>=.02:V.append(round(min(ba0+.01,aa0-.01)+ab0,4))
    if bb0>0 and(ab0-bb0)>=.02:V.append(round(aa0+min(bb0+.01,ab0-.01),4))
    U=min(V)if V else None;a._record_market_telemetry(key=f"NBA_BOX_{_4.event_id}",min_interval_sec=45.,now_ts=now,sig=(nd0["label"],nd0["box_cost_net"],U),payload={"type":"NBA_ZERO_FEE_BOX_BEST","event_id":_4.event_id,"game":_4.title,"box_kind":nd0["box_kind"],"in_play":bool(now>=_4.tipoff_ts),"sec_from_tipoff":round(now-_4.tipoff_ts,0),"best_label":nd0["label"],"leg_a_ask":round(aa0,4),"leg_a_bid":round(ba0,4)if ba0>0 else None,"leg_b_ask":round(ab0,4),"leg_b_bid":round(bb0,4)if bb0>0 else None,"net_box_l1":nd0["box_cost_net"],"maker_anchor_box_l1":U,"l1_min_usd":round(min(aa0*sa0,ab0*sb0),2),"middle_pts":nd0["middle_width_pts"]})
   for nb in _j:
    if float(nb["box_cost_net"])>1.06:continue
    lga,lgb=nb["leg_a"],nb["leg_b"];_i,_h=_F.get(lga.token_id),_F.get(lgb.token_id)
    if not _i or not _h:continue
    _a7={"token_id":lga.token_id,"opp_token_id":lga.opp_token_id,"condition_id":lga.condition_id,"side":lga.side_label,"label":lga.display_label,"market_id":lga.market_id,"fee_rate":lga.fee_rate,"fee_exponent":lga.fee_exponent,"strike":float(lga.threshold)};_a6={"token_id":lgb.token_id,"opp_token_id":lgb.opp_token_id,"condition_id":lgb.condition_id,"side":lgb.side_label,"label":lgb.display_label,"market_id":lgb.market_id,"fee_rate":lgb.fee_rate,"fee_exponent":lgb.fee_exponent,"strike":float(lgb.threshold)}
    if float(nb["box_cost_net"])>.994:a.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_SP1_{_4.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",_a7,_a6,_i,_h,float(nb["close_ts"]),f"{_4.title} [{nb['label']}]",now,prefetched_books=_F);continue
    _aI=walk_equal_shares_dominance_box(_i.get("asks")or[],_h.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["SP1_NBA_ZERO_FEE_BOX"],fee_rate_a=lga.fee_rate,fee_rate_b=lgb.fee_rate,fee_exponent_a=lga.fee_exponent,fee_exponent_b=lgb.fee_exponent,max_box_cost_net=.994,min_shares=8,min_box_notional_usd=7.)
    if _aI.get("filled"):
     opps_out.append({"sleeve":"SP1_NBA_ZERO_FEE_BOX","market":f"NBA {_4.title}: {nb['label']} (mid={nb['middle_width_pts']}pt)","ask_vwap":round(float(_aI["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_aI["box_cost_net"]),4),"l1_usd":_aI["l1_usd"],"close_ts":nb["close_ts"]});d=False
     if float(_aI["box_cost_net"])<=.99 and(float(nb["close_ts"])-now)<=86400.:d=a.emit_live_two_leg_box_candidate(sleeve_source="SP1_NBA_ZERO_FEE_BOX",box_type="NBA_DOMINANCE",asset="NBA",dedupe_key=f"SP1_{_4.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",leg_a=_a7,leg_b=_a6,bk_a=_i,bk_b=_h,close_ts=float(nb["close_ts"]),now_ts=now)
     await a.open_shadow_two_leg_box(sleeve="SP1_NBA_ZERO_FEE_BOX",dedupe_key=f"SP1_{_4.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",asset="NBA",title=f"{_4.title} [{nb['label']}]",leg_a=_a7,leg_b=_a6,bk_a=_i,bk_b=_h,close_ts=float(nb["close_ts"]),max_box_cost_net=.994,extra={"is_nba_zero_fee_box":True,"box_kind":nb["box_kind"],"middle_width_pts":nb["middle_width_pts"]})
     if not d:a.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_SP1_{_4.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",_a7,_a6,_i,_h,float(nb["close_ts"]),f"{_4.title} [{nb['label']}]",now,prefetched_books=_F,live_emit_only=True)
    else:a.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_SP1_{_4.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",_a7,_a6,_i,_h,float(nb["close_ts"]),f"{_4.title} [{nb['label']}]",now,prefetched_books=_F)
  o=[]
  for I in list(a.multi_sport_games.values()):
   if now>I.start_ts+6.5*3600.:a.multi_sport_games.pop(I.event_id,None);continue
   if a.single_scan or("fetch_json"in a.__dict__)or now>=(I.start_ts-86400.):o.append(I)
  o.sort(key=lambda g:(now<(g.start_ts-9e2),abs(g.start_ts-now)))
  for I in o[:20]:
   _E=sorted({lg.token_id for lgs in I.legs_by_scope.values()for lg in lgs})
   if len(_E)<4:continue
   _3=await a.fetch_books_batch(_E,timeout=3.5);z={}
   for t_m,_a5 in _3.items():
    _a4,_a3=a._best_ask_sz(_a5)
    if _a4<1. and _a4*_a3>=8.:z[t_m]=_a4
   _D=detect_multi_sport_corridor_boxes(I,z,max_box_cost_net=1.08)
   if _D:md0=_D[0];a._record_market_telemetry(key=f"SP3_BOX_{I.event_id}",min_interval_sec=45.,now_ts=now,sig=(md0["label"],md0["box_cost_net"]),payload={"type":"MULTI_SPORT_CORRIDOR_BEST","sport":I.sport,"event_id":I.event_id,"game":I.title,"scope":md0["scope"],"in_play":bool(now>=I.start_ts),"best_label":md0["label"],"gross_box_l1":md0["box_cost_gross"],"net_box_l1":md0["box_cost_net"],"middle_pts":md0["middle_width_pts"]})
   for cb in _D:
    _aH,_aG=cb["leg_a"],cb["leg_b"];_g=max(float(_aH.fee_rate),float(_aG.fee_rate));T=.994 if _g==.0 else.99
    if float(cb["box_cost_net"])>(1.045 if _g==.0 else T):continue
    _aF,_aE=_3.get(_aH.token_id),_3.get(_aG.token_id)
    if not _aF or not _aE:continue
    _a2={"token_id":_aH.token_id,"opp_token_id":_aH.opp_token_id,"condition_id":_aH.condition_id,"side":_aH.side_label,"label":_aH.display_label,"market_id":_aH.market_id,"fee_rate":float(_aH.fee_rate),"fee_exponent":float(_aH.fee_exponent),"neg_risk":bool(_aH.neg_risk),"strike":float(_aH.threshold)};_a1={"token_id":_aG.token_id,"opp_token_id":_aG.opp_token_id,"condition_id":_aG.condition_id,"side":_aG.side_label,"label":_aG.display_label,"market_id":_aG.market_id,"fee_rate":float(_aG.fee_rate),"fee_exponent":float(_aG.fee_exponent),"neg_risk":bool(_aG.neg_risk),"strike":float(_aG.threshold)};_2=f"SP3_{I.event_id}_{_aH.token_id[-8:]}_{_aG.token_id[-8:]}"
    if float(cb["box_cost_net"])>T:
     if _g==.0:a.post_zero_fee_maker_anchor_box("SP3_SPORTS",I.sport,f"ZFA_{_2}",_a2,_a1,_aF,_aE,float(cb["close_ts"]),f"{I.title} [{cb['label']}]",now,prefetched_books=_3)
     continue
    _aD=walk_equal_shares_dominance_box(_aF.get("asks")or[],_aE.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["SP3_SPORTS_CORRIDOR_DOMINANCE_BOX"],fee_rate_a=float(_aH.fee_rate),fee_rate_b=float(_aG.fee_rate),fee_exponent_a=float(_aH.fee_exponent),fee_exponent_b=float(_aG.fee_exponent),max_box_cost_net=T,min_shares=8,min_box_notional_usd=7.)
    if _aD.get("filled"):
     opps_out.append({"sleeve":"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX","market":f"{I.sport} {I.title}: {cb['label']} (mid={cb['middle_width_pts']}pt)","ask_vwap":round(float(_aD["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_aD["box_cost_net"]),4),"l1_usd":_aD["l1_usd"],"close_ts":cb["close_ts"]});y=.99 if _g==.0 else.988
     if float(_aD["box_cost_net"])<=y and(float(cb["close_ts"])-now)<=86400.:a.emit_live_two_leg_box_candidate(sleeve_source="SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",box_type="SPORTS_CORRIDOR",asset=I.sport,dedupe_key=_2,leg_a=_a2,leg_b=_a1,bk_a=_aF,bk_b=_aE,close_ts=float(cb["close_ts"]),now_ts=now,k_low=float(_aH.threshold),k_high=float(_aG.threshold))
     await a.open_shadow_two_leg_box(sleeve="SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",dedupe_key=_2,asset=I.sport,title=f"{I.sport} {I.title} [{cb['label']}]",leg_a=_a2,leg_b=_a1,bk_a=_aF,bk_b=_aE,close_ts=float(cb["close_ts"]),max_box_cost_net=T,extra={"is_sports_corridor_box":True,"sport":I.sport,"scope":cb["scope"],"box_kind":cb["box_kind"],"middle_width_pts":cb["middle_width_pts"]})
  for _aC in sorted(list(a.negrisk_zero_slates.values()),key=lambda s:((float(s.end_ts)-now)>64800.,float(s.end_ts))):
   if _aC.end_ts<=now+60:a.negrisk_zero_slates.pop(_aC.event_id,None);continue
   _C=[b["yes_token"]for b in _aC.brackets]+[b["no_token"]for b in _aC.brackets];_1=await a.fetch_books_batch(_C,timeout=3.5)
   if not all(b["yes_token"]in _1 and b["no_token"]in _1 for b in _aC.brackets):continue
   H=[a._best_ask_sz(_1[b["yes_token"]])for b in _aC.brackets];G=[a._best_ask_sz(_1[b["no_token"]])for b in _aC.brackets];_aB=sum(p for p,_ in H);_aA=sum(p for p,_ in G);S=round(min(p*s for p,s in H),2);R=round(min(p*s for p,s in G),2);F=round(sum(extract_best_bid(_1[b["yes_token"]].get("bids")or[])[0]for b in _aC.brackets),4);E=round(sum(extract_best_bid(_1[b["no_token"]].get("bids")or[])[0]for b in _aC.brackets),4);_a0=len(_aC.brackets);a._record_market_telemetry(key=f"NR0_SLATE_{_aC.event_id}",min_interval_sec=60.,now_ts=now,sig=(round(_aB,3),round(_aA,3)),payload={"type":"ZERO_FEE_NEGRISK_SLATE","series":_aC.series_slug,"title":_aC.title,"tte_sec":round(_aC.end_ts-now,0),"n_open":_a0,"sum_yes_l1":round(_aB,4),"sum_yes_bids":F,"min_yes_l1_usd":S,"sum_no_l1":round(_aA,4),"sum_no_bids":E,"min_no_l1_usd":R,"no_payout":_a0-1})
   if _aB<=.99:
    _0=[{"token_id":b["yes_token"],"side":"YES","label":f"YES[{b['label']}]","market_id":b["market_id"],"fee_rate":float(b.get("fee_rate",.0))}for b in _aC.brackets];_az=walk_equal_shares_multi_leg_box([{"asks":_1[b["yes_token"]].get("asks")or[],"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.))}for b in _aC.brackets],target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],guaranteed_payout_per_bundle=1.,max_bundle_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
    if _az.get("filled"):
     opps_out.append({"sleeve":"NR0_ZERO_FEE_SLATE_ARB","market":f"{_aC.title} (ALL {_a0} YES)","ask_vwap":round(float(_az["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_az["box_cost_net"]),4),"l1_usd":_az["l1_usd"],"close_ts":_aC.end_ts})
     if _a0==2 and(float(_aC.end_ts)-now)<=172800. and a._can_emit_zero_loss_math_live("NR0_ZERO_FEE_SLATE_ARB",float(_aC.end_ts),now):_aZ,_aY=_aC.brackets[0],_aC.brackets[1];a.emit_live_two_leg_box_candidate(sleeve_source="NR0_ZERO_FEE_SLATE_ARB",box_type="NEGRISK_2LEG",asset=_aC.series_slug.upper(),dedupe_key=f"NR0_Y_{_aC.event_id}",leg_a={"token_id":_aZ["yes_token"],"opp_token_id":_aZ["no_token"],"condition_id":str(_aZ.get("condition_id")or""),"side":"YES","label":f"YES[{_aZ['label']}]","market_id":_aZ["market_id"],"fee_rate":float(_aZ.get("fee_rate",.0)),"fee_exponent":float(_aZ.get("fee_exponent",1.)),"neg_risk":True,"strike":1e2},leg_b={"token_id":_aY["yes_token"],"opp_token_id":_aY["no_token"],"condition_id":str(_aY.get("condition_id")or""),"side":"YES","label":f"YES[{_aY['label']}]","market_id":_aY["market_id"],"fee_rate":float(_aY.get("fee_rate",.0)),"fee_exponent":float(_aY.get("fee_exponent",1.)),"neg_risk":True,"strike":1e2},bk_a=_1[_aZ["yes_token"]],bk_b=_1[_aY["yes_token"]],close_ts=float(_aC.end_ts),now_ts=now)
     elif(3<=_a0<=12 and not bool(getattr(_aC,"neg_risk_augmented",False))and(float(_aC.end_ts)-now)<=86400. and a._can_emit_zero_loss_math_live("NR0_ZERO_FEE_SLATE_ARB",float(_aC.end_ts),now)):
      _f=a.negrisk_convert_slates.get(_aC.event_id)
      if _f is None or bool(_f.is_closed_convert_safe):
       _B=[{"token_id":str(b["yes_token"]),"market_id":str(b["market_id"]),"condition_id":str(b.get("condition_id")or""),"ask_px":float(H[idx][0]),"ask_size":float(H[idx][1]),"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.)),"neg_risk":True,"side":"YES","role":f"NR0_YES_{idx}","label":f"YES[{b['label']}]"}for idx,b in enumerate(_aC.brackets)]
       if all(.0<x["ask_px"]<1. and x["ask_size"]>=5. for x in _B):a.emit_live_special_v2_box_candidate(box_type="MULTI_LEG_BUNDLE",sleeve_source="NR0_ZERO_FEE_SLATE_ARB",asset=_aC.series_slug.upper(),dedupe_key=f"NR0_Y{_a0}_{_aC.event_id}",close_ts=float(_aC.end_ts),now_ts=now,payload={"legs":_B,"box_cost_net":round(float(_az["box_cost_net"]),6),"cost_per_share":round(float(_az["box_cost_net"]),6),"max_box_cost_net":.988,"max_fillable_shares":min(float(x["ask_size"])for x in _B),"neg_risk":True,"leg_a_fee_rate":max((float(x["fee_rate"])for x in _B),default=.0),"leg_b_fee_rate":.0})
     await a.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB",f"NR0_Y_{_aC.event_id}",_aC.series_slug.upper(),f"{_aC.title} [All-YES Partition]",_0,_1,_aC.end_ts,1.,.988,{"is_multi_leg_bundle":True,"guaranteed_payout":1.})
   elif _aA<=(_a0-1)-.01:
    _aX=float(_a0-1);_Z=[{"token_id":b["no_token"],"side":"NO","label":f"NO[{b['label']}]","market_id":b["market_id"],"fee_rate":float(b.get("fee_rate",.0))}for b in _aC.brackets];_ay=walk_equal_shares_multi_leg_box([{"asks":_1[b["no_token"]].get("asks")or[],"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.))}for b in _aC.brackets],target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],guaranteed_payout_per_bundle=_aX,max_bundle_cost_net=round(_aX-.012,4),min_shares=6,min_box_notional_usd=5.5)
    if _ay.get("filled"):
     opps_out.append({"sleeve":"NR0_ZERO_FEE_SLATE_ARB","market":f"{_aC.title} (ALL {_a0} NO)","ask_vwap":round(float(_ay["box_cost_net"])/_aX,4),"p_model":1.,"net_edge":round((_aX-float(_ay["box_cost_net"]))/_aX,4),"l1_usd":_ay["l1_usd"],"close_ts":_aC.end_ts})
     if(float(_aC.end_ts)-now)<=172800. and a._can_emit_zero_loss_math_live("NR0_ZERO_FEE_SLATE_ARB",float(_aC.end_ts),now):
      if _a0==2:_aW,_aV=_aC.brackets[0],_aC.brackets[1];a.emit_live_two_leg_box_candidate(sleeve_source="NR0_ZERO_FEE_SLATE_ARB",box_type="NEGRISK_2LEG",asset=_aC.series_slug.upper(),dedupe_key=f"NR0_N_{_aC.event_id}",leg_a={"token_id":_aW["no_token"],"opp_token_id":_aW["yes_token"],"condition_id":str(_aW.get("condition_id")or""),"side":"NO","label":f"NO[{_aW['label']}]","market_id":_aW["market_id"],"fee_rate":float(_aW.get("fee_rate",.0)),"fee_exponent":float(_aW.get("fee_exponent",1.)),"neg_risk":True,"strike":1e2},leg_b={"token_id":_aV["no_token"],"opp_token_id":_aV["yes_token"],"condition_id":str(_aV.get("condition_id")or""),"side":"NO","label":f"NO[{_aV['label']}]","market_id":_aV["market_id"],"fee_rate":float(_aV.get("fee_rate",.0)),"fee_exponent":float(_aV.get("fee_exponent",1.)),"neg_risk":True,"strike":1e2},bk_a=_1[_aW["no_token"]],bk_b=_1[_aV["no_token"]],close_ts=float(_aC.end_ts),now_ts=now)
      elif 3<=_a0<=15:
       _e=a.negrisk_convert_slates.get(_aC.event_id)
       if _e is not None and _e.is_closed_convert_safe:_d=_ay.get("leg_walks")or[];_ax={"mode":"NR2_PURE_CASH_CONVERT","shares":_ay["shares"],"net_edge_per_share":round((_aX-float(_ay["box_cost_net"]))/_aX,5),"no_legs":[{"token_id":b_z["no_token"],"bracket":b_z,"walk":(_d[idx_z]if idx_z<len(_d)else{"worst_px":a._best_ask_sz(_1[b_z["no_token"]])[0]})}for idx_z,b_z in enumerate(_e.brackets)],"yes_sell_legs":[],"retained_free_yes_brackets":[]};a.emit_live_negrisk_convert_candidate(sleeve_source="NR0_ZERO_FEE_SLATE_ARB",spec=_e,dedupe_key=f"NR0_N{_a0}_{_aC.event_id}",arb_hit=_ax,books_by_token=_1,now_ts=now)
     await a.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB",f"NR0_N_{_aC.event_id}",_aC.series_slug.upper(),f"{_aC.title} [All-NO Partition]",_Z,_1,_aC.end_ts,_aX,round(_aX-.012,4),{"is_multi_leg_bundle":True,"guaranteed_payout":_aX})
   if F>=1.004:await a.execute_ctf_overround_mint_sell(dedupe_key=f"CTF_OVR_NR_{_aC.event_id}",asset=_aC.series_slug.upper(),title=f"{_aC.title} NegRisk Overround Mint-Sell",legs_bids_spec=[{"bids":_1[b["yes_token"]].get("bids")or[],"fee_rate":float(b.get("fee_rate",.0)),"fee_exponent":float(b.get("fee_exponent",1.))}for b in _aC.brackets],close_ts=_aC.end_ts,min_net_proceeds_per_set=1.004,opps_out=opps_out,extra={"overround_kind":"NEGRISK_SLATE","series":_aC.series_slug,"event_id":_aC.event_id})
  f=[s for s in a.negrisk_convert_slates.values()if s.end_ts>now+60]
  if len(f)>72 and not a.single_scan and"fetch_json"not in a.__dict__:f.sort(key=lambda s:(not bool(s.is_closed_convert_safe),float(s.end_ts)));_c=f[36:];_aw=int(a.__dict__.get("_nrc_rot_cursor",0)or 0)%len(_c);Q=(_c[_aw:_aw+36]+_c[:max(0,_aw+36-len(_c))])[:36];a.__dict__["_nrc_rot_cursor"]=(_aw+36)%len(_c);f=f[:36]+Q
  if f:
   _b=[]
   for _av in f:
    for _au in _av.brackets:
     _b.append(_au["no_token"])
     if _av.is_closed_convert_safe:_b.append(_au["yes_token"])
   _A=await a.fetch_books_batch(_b,timeout=3.5);k={}
   for _aU,_at in _A.items():
    _as,_ar=a._best_ask_sz(_at)
    if _as<1. and _ar>=8. and _as*_ar>=1.05:k[_aU]=_as
   for _Y in f:
    P=detect_negrisk_no_pair_boxes(_Y,k,max_box_cost_net=1.04)
    if P:pa0=P[0];a._record_market_telemetry(key=f"NRCONV_2L_{_Y.event_id}",min_interval_sec=60.,now_ts=now,sig=(pa0["label"],pa0["box_cost_net"]),payload={"type":"NEGRISK_NO_PAIR_BEST","event_id":_Y.event_id,"title":_Y.title[:80],"augmented":_Y.neg_risk_augmented,"net_box_l1":pa0["box_cost_net"],"label":pa0["label"]})
    for pa in P:
     _aq,_ap=pa["bracket_a"],pa["bracket_b"];O=max(float(_aq["fee_rate"]),float(_ap["fee_rate"]));_z=.992 if O==.0 else.988;_X,_W=_A.get(_aq["no_token"]),_A.get(_ap["no_token"])
     if not _X or not _W:continue
     _ao={"token_id":_aq["no_token"],"opp_token_id":_aq["yes_token"],"condition_id":_aq["condition_id"],"side":"NO","label":f"NO[{_aq['label']}]","market_id":_aq["market_id"],"fee_rate":float(_aq["fee_rate"]),"fee_exponent":float(_aq["fee_exponent"]),"neg_risk":True,"strike":1e2};_an={"token_id":_ap["no_token"],"opp_token_id":_ap["yes_token"],"condition_id":_ap["condition_id"],"side":"NO","label":f"NO[{_ap['label']}]","market_id":_ap["market_id"],"fee_rate":float(_ap["fee_rate"]),"fee_exponent":float(_ap["fee_exponent"]),"neg_risk":True,"strike":1e2}
     if float(pa["box_cost_net"])>_z:
      if O==.0 and float(pa["box_cost_net"])<=1.035 and _aq["market_id"]!=_ap["market_id"]:a.post_zero_fee_maker_anchor_box("NEGRISK_NO_PAIR","NEGRISK",f"ZF_NRPAIR_{_Y.event_id}_{_aq['market_id']}_{_ap['market_id']}",_ao,_an,_X,_W,float(_Y.end_ts),f"{_Y.title[:50]}: {pa['label']}",now,prefetched_books=_A)
      continue
     _am=walk_equal_shares_dominance_box(_X.get("asks")or[],_W.get("asks")or[],target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],fee_rate_a=float(_aq["fee_rate"]),fee_rate_b=float(_ap["fee_rate"]),fee_exponent_a=float(_aq["fee_exponent"]),fee_exponent_b=float(_ap["fee_exponent"]),max_box_cost_net=_z,min_shares=8,min_box_notional_usd=7.)
     if _am.get("filled"):
      _V=f"NRCONV_2L_{_Y.event_id}_{_aq['market_id']}_{_ap['market_id']}";opps_out.append({"sleeve":"NR_CONV_NO_BASKET_ARB","market":f"{_Y.title[:50]}: {pa['label']}","ask_vwap":round(float(_am["box_cost_net"]),4),"p_model":1.,"net_edge":round(1.-float(_am["box_cost_net"]),4),"l1_usd":_am["l1_usd"],"close_ts":_Y.end_ts})
      if(_Y.end_ts-now)<=172800. and float(_am["box_cost_net"])<=(.99 if O==.0 else.988):a.emit_live_two_leg_box_candidate(sleeve_source="NR_CONV_NO_BASKET_ARB",box_type="NEGRISK_2LEG",asset="NEGRISK",dedupe_key=_V,leg_a=_ao,leg_b=_an,bk_a=_X,bk_b=_W,close_ts=float(_Y.end_ts),now_ts=now)
      await a.open_shadow_two_leg_box(sleeve="NR_CONV_NO_BASKET_ARB",dedupe_key=_V,asset="NEGRISK",title=f"{_Y.title} [{pa['label']}]",leg_a=_ao,leg_b=_an,bk_a=_X,bk_b=_W,close_ts=float(_Y.end_ts),max_box_cost_net=_z,extra={"is_negrisk_no_pair_box":True,"event_id":_Y.event_id,"neg_risk_augmented":_Y.neg_risk_augmented})
    if _Y.is_closed_convert_safe:
     N=detect_negrisk_convert_positions_arbs(_Y,_A,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],min_net_edge_per_share=.005,min_shares=8)
     if N:ca0=N[0];a._record_market_telemetry(key=f"NRCONV_M_{_Y.event_id}",min_interval_sec=60.,now_ts=now,sig=(ca0["m_no_legs"],ca0["net_edge_per_share"]),payload={"type":"NEGRISK_CONVERT_ARB_SNAP","event_id":_Y.event_id,"title":_Y.title[:80],"m_no_legs":ca0["m_no_legs"],"n_total":ca0["n_total"],"net_edge_per_share":ca0["net_edge_per_share"],"shares":ca0["shares"]});await a.execute_negrisk_convert_positions_arb(_Y,ca0,_A,opps_out)
     C=(all(float(b.get("fee_rate",.0)or.0)<=1e-9 for b in _Y.brackets)and(_Y.end_ts-now)<=172800.);_a=detect_nr2_convert_no_subset_arbs(_Y,_A,target_budget_usd=BANKROLL_TICKETS["T1000"]["NR2_CONVERT_NO_SUBSET_ARB"],min_edge_pure_cash=.006 if C else.012,min_edge_with_yes_sell=.0085 if C else.015,min_shares=5 if C else 6)
     try:
      from src.polymarket_research.riskless_machine_gun_engine import detect_nr3_synthetic_all_yes_overround as c;_y=c(_Y,_A,target_budget_usd=30.,min_net_edge_per_set=.008,min_shares=5)
      if _y is not None:opps_out.append({"sleeve":"NR2_CONVERT_NO_SUBSET_ARB","market":f"{_Y.title[:50]} [NR3 All-YES Overround]","ask_vwap":round(max(.01,1.-float(_y["net_edge_per_share"])),4),"p_model":1.,"net_edge":_y["net_edge_per_share"],"l1_usd":_y["l1_usd"],"close_ts":_Y.end_ts});a.emit_live_negrisk_convert_candidate(sleeve_source="NR2_CONVERT_NO_SUBSET_ARB",spec=_Y,dedupe_key=f"NR3_OVR_{_Y.event_id}",arb_hit=_y,books_by_token=_A,now_ts=now)
     except Exception:pass
     if _a:na0=_a[0];a._record_market_telemetry(key=f"NR2_SUB_{_Y.event_id}",min_interval_sec=60.,now_ts=now,sig=(na0["m_no_legs"],na0["net_edge_per_share"],na0["retained_tail_count"]),payload={"type":"NR2_SUBSET_CONVERT_SNAP","event_id":_Y.event_id,"title":_Y.title[:80],"m_no_legs":na0["m_no_legs"],"n_total":na0["n_total"],"retained_tail_count":na0["retained_tail_count"],"net_edge_per_share":na0["net_edge_per_share"]});await a.execute_nr2_subset_convert_arb(_Y,na0,_A,opps_out)
 async def _scan_frontier_v2_sleeves(a,opps_out,now):
  e=[s for s in a.nba_prop_slates.values()if s.settle_est_ts>now+120]
  for _j in e[:10]:
   I=[t for rgs in _j.props_by_player_stat.values()if len(rgs)>=2 for r in rgs for t in(r.yes_token,r.no_token)]
   if not I:continue
   V=await a.fetch_books_batch(I,timeout=3.5);H={t:p for t,bk in V.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.};n=detect_sp4_milestone_ladder_boxes(_j,H,max_box_cost_net=1.045)
   if n:b0=n[0];a._record_market_telemetry(f"SP4_3B_{_j.event_id}",90.,{"type":"SP4_MILESTONE_BOX_BEST","game":_j.title[:60],"label":b0["label"],"net_box_l1":b0["box_cost_net"]},now_ts=now,sig=(b0["label"],b0["box_cost_net"]))
   for bx in n[:8]:
    la,lb=bx["leg_a"],bx["leg_b"];_B,_A=V.get(la["token_id"]),V.get(lb["token_id"])
    if not _B or not _A:continue
    U=f"SP4_3B_{la['market_id']}_{lb['market_id']}"
    if float(bx["box_cost_net"])>.992:
     if la.get("market_id")!=lb.get("market_id"):a.post_zero_fee_maker_anchor_box("SP1_NBA","NBA",f"ZFA_{U}",la,lb,_B,_A,float(bx["close_ts"]),f"{_j.title} [{bx['label']}]",now,prefetched_books=V)
     continue
    _i=walk_equal_shares_dominance_box(_B.get("asks")or[],_A.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],float(la["fee_rate"]),float(lb["fee_rate"]),fee_exponent_a=float(la.get("fee_exponent",1.)),fee_exponent_b=float(lb.get("fee_exponent",1.)),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
    if _i.get("filled"):
     opps_out.append({"sleeve":"SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK","market":f"NBA Prop Corridor: {bx['label']}","ask_vwap":_i["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_i["box_cost_net"]),4),"l1_usd":_i["l1_usd"],"close_ts":bx["close_ts"]})
     if float(_i["box_cost_net"])<=.99 and(float(bx["close_ts"])-now)<=86400. and la.get("market_id")!=lb.get("market_id"):a.emit_live_two_leg_box_candidate(sleeve_source="SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",box_type="NBA_DOMINANCE",asset="NBA",dedupe_key=U,leg_a=la,leg_b=lb,bk_a=_B,bk_b=_A,close_ts=float(bx["close_ts"]),now_ts=now,k_low=float(bx["line_low"]),k_high=float(bx["line_high"]))
     await a.open_shadow_two_leg_box("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",U,"NBA_PROP",f"{_j.title} [{bx['label']}]",la,lb,_B,_A,float(bx["close_ts"]),.992,{"is_two_leg_box":True,"mode":bx["mode"],"player":bx["player_name"],"stat":bx["stat_type"]})
  k=[tr for tr in a.soccer_trees.values()if tr.end_ts>now+120]
  if k:
   A=[]
   for tr in k[:25]:
    for _z in(tr.home_leg,tr.draw_leg,tr.away_leg):A.extend((_z["yes_token"],_z["no_token"]))
    for tl in tr.totals:A.extend((tl["over_token"],tl["under_token"]))
    for sp in tr.spreads:A.extend((sp["fav_minus_token"],sp["dog_plus_token"]))
   G=await a.fetch_books_batch(A,timeout=3.5);z={t:p for t,bk in G.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for tr in k[:25]:
    F=detect_soc1_regulation_boxes(tr,G,z,max_2leg_cost_net=1.035,min_conv_edge_ps=.01,target_budget_usd=BANKROLL_TICKETS["T1000"]["SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"])
    if F["two_leg_boxes"]:_y=F["two_leg_boxes"][0];a._record_market_telemetry(f"SOC1_{tr.game_id}",90.,{"type":"SOC1_REGULATION_BOX_BEST","game":tr.title[:60],"mode":_y["mode"],"label":_y["label"],"net_box_l1":_y["box_cost_net"]},now_ts=now,sig=(_y["label"],_y["box_cost_net"]))
    for _w in F["two_leg_boxes"][:4]:
     if float(_w["box_cost_net"])>.988:continue
     _v,_u=_w["leg_a"],_w["leg_b"];_h,_g=G.get(_v["token_id"]),G.get(_u["token_id"])
     if not _h or not _g:continue
     _f=walk_equal_shares_dominance_box(_h.get("asks")or[],_g.get("asks")or[],BANKROLL_TICKETS["T1000"]["SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"],float(_v["fee_rate"]),float(_u["fee_rate"]),fee_exponent_a=float(_v["fee_exponent"]),fee_exponent_b=float(_u["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
     if _f.get("filled"):
      T=f"SOC1_2L_{tr.game_id}_{_v['token_id'][-6:]}_{_u['token_id'][-6:]}";opps_out.append({"sleeve":"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX","market":_w["label"],"ask_vwap":_f["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_f["box_cost_net"]),4),"l1_usd":_f["l1_usd"],"close_ts":tr.end_ts})
      if(float(tr.end_ts)-now)<=259200. and _v.get("market_id")!=_u.get("market_id"):a.emit_live_two_leg_box_candidate(sleeve_source="SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",box_type="SPORTS_CORRIDOR",asset="SOCCER",dedupe_key=T,leg_a=_v,leg_b=_u,bk_a=_h,bk_b=_g,close_ts=float(tr.end_ts),now_ts=now)
      await a.open_shadow_two_leg_box("SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",T,"SOCCER",_w["label"],_v,_u,_h,_g,float(tr.end_ts),.988,{"is_two_leg_box":True,"mode":_w["mode"],"game_id":tr.game_id})
    for _t in F["convert_arbs"][:1]:opps_out.append({"sleeve":"SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX","market":_t["label"],"ask_vwap":round(1.-float(_t["net_edge_per_share"]),4),"p_model":1.,"net_edge":_t["net_edge_per_share"],"l1_usd":_t["l1_usd"],"close_ts":tr.end_ts})
  j=[]
  if a.lp1_bop_legs:j.append(("BOP_2026",[lg for lg in a.lp1_bop_legs if float(lg["end_ts"])>now+60]))
  for _s in list(a.lp1_nba_em_bundles.values())[:10]:
   if float(_s["end_ts"])>now+60:j.append((f"NBA_EM_{_s['event_id']}",_s["legs"]))
  if j:
   y=sorted({str(lg["token_id"])for _,g_lgs in j for lg in g_lgs});E=await a.fetch_books_batch(y,timeout=3.5);w={t:p for t,bk in E.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for _e,g_lgs in j:
    if len(g_lgs)<4:continue
    m=_e.startswith("NBA_EM");i=find_state_matrix_dominance_boxes(g_lgs,w,max_2leg_cost_net=1.045,max_3leg_cost_net=1.03)
    if i:d0=i[0];a._record_market_telemetry(f"LP1_{_e}",90.,{"type":"LP1_IMPLICATION_BEST","group":_e,"n_legs":d0["n_legs"],"net_box_l1":d0["box_cost_net"],"label":d0["label"]},now_ts=now,sig=(d0["label"],d0["box_cost_net"]))
    for _r in i[:6]:
     _d=_r["legs"]
     if int(_r["n_legs"])==2:
      _q,_p=_d[0],_d[1];_c,_b=E.get(_q["token_id"]),E.get(_p["token_id"])
      if not _c or not _b:continue
      S=f"LP1_2L_{_e}_{_q['token_id'][-6:]}_{_p['token_id'][-6:]}";l=max(float(_q["fee_rate"]),float(_p["fee_rate"]))
      if float(_r["box_cost_net"])>.993:
       if l==.0 and _q.get("market_id")!=_p.get("market_id"):a.post_zero_fee_maker_anchor_box("SP1_NBA"if m else"LP1_BOP","NBA"if m else"MACRO",f"ZFA_{S}",_q,_p,_c,_b,float(_r["close_ts"]),f"{_e} [{_r['label']}]",now,prefetched_books=E)
       continue
      _a=walk_equal_shares_dominance_box(_c.get("asks")or[],_b.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"],float(_q["fee_rate"]),float(_p["fee_rate"]),max_box_cost_net=.993,min_shares=6,min_box_notional_usd=5.5)
      if _a.get("filled"):
       opps_out.append({"sleeve":"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX","market":f"{_e}: {_r['label']}","ask_vwap":_a["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_a["box_cost_net"]),4),"l1_usd":_a["l1_usd"],"close_ts":_r["close_ts"]});g=.99 if l==.0 else.988
       if float(_a["box_cost_net"])<=g:v="COMPLETE_SET"if _q.get("market_id")==_p.get("market_id")else("NBA_DOMINANCE"if m else"MACRO_DOMINANCE");a.emit_live_two_leg_box_candidate(sleeve_source="LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",box_type=v,asset="NBA"if m else"MACRO",dedupe_key=S,leg_a=_q,leg_b=_p,bk_a=_c,bk_b=_b,close_ts=float(_r["close_ts"]),now_ts=now)
       await a.open_shadow_two_leg_box("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",S,_e,f"{_e} {_r['label']}",_q,_p,_c,_b,float(_r["close_ts"]),.993,{"is_two_leg_box":True,"min_payout":_r["min_payout"],"jackpot_states":_r["jackpot_states"]})
     elif int(_r["n_legs"])==3 and float(_r["box_cost_net"])<=.991:
      R=walk_equal_shares_multi_leg_box([{"asks":E[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":1.}for x in _d],BANKROLL_TICKETS["T1000"]["LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"],1.,.991,min_shares=6,min_box_notional_usd=5.5)
      if R.get("filled"):Q=f"LP1_3L_{_e}_{'_'.join(x['token_id'][-5:]for x in _d)}";opps_out.append({"sleeve":"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX","market":f"{_e} 3L: {_r['label']}","ask_vwap":R["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(R["box_cost_net"]),4),"l1_usd":R["l1_usd"],"close_ts":_r["close_ts"]});await a.open_shadow_multi_leg_bundle("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",Q,_e,f"{_e} 3-Leg {_r['label']}",_d,E,float(_r["close_ts"]),1.,.991,{"is_multi_leg_bundle":True,"guaranteed_payout":1.})
  h=[sp for sp in a.esports_bo3_specs.values()if sp.end_ts>now+60]
  if h:
   u=[]
   for o in h[:25]:
    u.extend([o.ml_a_token,o.ml_b_token,o.hc_minus_token,o.hc_plus_token])
    for mt in(o.map1_a_token,o.map1_b_token,o.map2_a_token,o.map2_b_token,o.ou25_over_token,o.ou25_under_token):
     if mt:u.append(mt)
   D=await a.fetch_books_batch(u,timeout=3.5);q={t:p for t,bk in D.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.};b=not bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("strict_pure_riskless_mode",False))
   for o in h[:25]:
    P=evaluate_api1_esports_bo3_opportunities(o,D,q,max_middle_cost_net=1.035,allow_quote_inferred=b)
    if P["two_leg_boxes"]:_x=P["two_leg_boxes"][0];a._record_market_telemetry(f"API1_{o.event_id}",90.,{"type":"API1_ESPORTS_BO3_BEST","match":o.title[:60],"mode":_x["mode"],"net_box_l1":_x["box_cost_net"],"forfeit_immune":_x["post_m1_forfeit_immune"]},now_ts=now,sig=(_x["mode"],_x["box_cost_net"]))
    d=not(a.single_scan or("fetch_json"in a.__dict__))
    for _o in P["single_leg_locks"]:
     O=D.get(_o["token_id"]);N=D.get(_o["opp_token_id"])
     if not O or not N:continue
     C,_=extract_best_bid(N.get("bids")or[])
     if C>.04:continue
     _n=f"API1_LK_{o.event_id}_{_o['market_id']}";M=float(_o["p_lock"]);B=float(_o["close_ts"]);L=walk_l2_book_asks_depth_capped(O.get("asks")or[],BANKROLL_TICKETS["T1000"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],BANKROLL_TICKETS["T100"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],fee_rate=float(_o["fee_rate"]),min_l1_usd=15.,max_ask_px=.978,fee_exponent=float(_o["fee_exponent"]));f=bool(L.get("filled")and.72<=float(L["eff_px"])<=.978 and round(M-float(L["eff_px"]),4)>=.018)
     if(f or(d and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_partial_fak_single_leg_sweep",True))))and a._can_emit_zero_loss_math_live("API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",B,now,p_model=M):c=a.compute_live_8e_clinch_max_eff_px(.978,M,B-now)if d else.978;a.emit_live_single_leg_lock_candidate(sleeve_source="API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",asset="ESPORTS",dedupe_key=_n,token_id=str(_o["token_id"]),opp_token_id=str(_o["opp_token_id"]),market_id=str(_o["market_id"]),condition_id=str(_o["condition_id"]),side_label=str(_o["side_label"]),display_label=str(_o["display_label"]),bk_win=O,bk_opp=N,fee_rate=float(_o["fee_rate"]),fee_exponent=float(_o["fee_exponent"]),neg_risk=False,close_ts=B,now_ts=now,max_lock_eff_px=c,max_opp_bid=.025,hold_to_maturity=True,p_model=M)
     if f:Z=float(L["eff_px"]);Y=round(M-Z,4);opps_out.append({"sleeve":"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","market":f"Esports BO3 Lock: {_o['display_label']}","ask_vwap":Z,"p_model":M,"net_edge":Y,"l1_usd":L["l1_usd"],"close_ts":B});await a.open_shadow_position("API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",_n,"ESPORTS_BO3",f"{o.title} [{_o['display_label']}]",str(_o["side_label"]),str(_o["token_id"]),float(_o["fee_rate"]),M,B,{"market_id":_o["market_id"],"condition_id":_o["condition_id"],"mode":_o["mode"]},prefetched_book=O)
    for _m in P["two_leg_boxes"]:
     if float(_m["box_cost_net"])>.988:continue
     _l,_k=_m["leg_a"],_m["leg_b"];X,W=D.get(_l["token_id"]),D.get(_k["token_id"])
     if not X or not W:continue
     K=walk_equal_shares_dominance_box(X.get("asks")or[],W.get("asks")or[],BANKROLL_TICKETS["T1000"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],float(_l["fee_rate"]),float(_k["fee_rate"]),fee_exponent_a=float(_l["fee_exponent"]),fee_exponent_b=float(_k["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
     if K.get("filled"):
      J=f"API1_MID_{o.event_id}_{_l['market_id']}_{_k['market_id']}";opps_out.append({"sleeve":"API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","market":_m["label"],"ask_vwap":K["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(K["box_cost_net"]),4),"l1_usd":K["l1_usd"],"close_ts":_m["close_ts"]})
      if bool(_m.get("post_m1_forfeit_immune"))and _l.get("market_id")!=_k.get("market_id"):a.emit_live_two_leg_box_candidate(sleeve_source="API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",box_type="SPORTS_CORRIDOR",asset="ESPORTS",dedupe_key=J,leg_a=_l,leg_b=_k,bk_a=X,bk_b=W,close_ts=float(_m["close_ts"]),now_ts=now)
      await a.open_shadow_two_leg_box("API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",J,"ESPORTS_BO3",_m["label"],_l,_k,X,W,float(_m["close_ts"]),.988,{"is_two_leg_box":True,"mode":_m["mode"],"post_m1_forfeit_immune":_m["post_m1_forfeit_immune"]})
 async def _scan_frontier_v3_sleeves(a,opps_out,now):
  if a.lp2_implication_groups or a.lp2_events_by_slug:
   n={str(lg["token_id"])for _,lgs in a.lp2_implication_groups for lg in lgs if float(lg.get("end_ts")or.0)>now+60}
   for _m in("republican-house-seats-after-the-2026-midterm-elections","republican-senate-seats-after-the-2026-midterm-elections-927","which-party-will-win-the-house-in-2026","which-party-will-win-the-senate-in-2026"):
    _5=a.lp2_events_by_slug.get(_m)or{}
    for _as in _5.get("markets")or[]:
     if not _as.get("closed"):
      _4=_parse_clob_tokens(_as)
      if _4:n.update(_4)
   if n:
    _l=await a.fetch_books_batch(sorted(n),timeout=4.);X={t:p for t,bk in _l.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for W,V in a.lp2_implication_groups:
     _A=find_state_matrix_dominance_boxes(V,X,max_2leg_cost_net=1.045,max_3leg_cost_net=.992)
     if _A:_3=_A[0];a._record_market_telemetry(f"LP2_{W}",90.,{"type":"LP2_DAG_BOX_BEST","group":W,"n_legs":_3["n_legs"],"label":_3["label"],"net_box_l1":_3["box_cost_net"],"jackpot_states":_3["jackpot_states"]},now_ts=now,sig=(_3["label"],_3["box_cost_net"]))
     for bx in _A[:6]:
      if float(bx["box_cost_net"])>.992:continue
      _2=bx["legs"]
      if int(bx["n_legs"])==2:
       _ar,_aq=_2[0],_2[1];_1,_0=_l.get(_ar["token_id"]),_l.get(_aq["token_id"])
       if not _1 or not _0:continue
       _ap=walk_equal_shares_dominance_box(_1.get("asks")or[],_0.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],float(_ar["fee_rate"]),float(_aq["fee_rate"]),fee_exponent_a=float(_ar["fee_exponent"]),fee_exponent_b=float(_aq["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
       if _ap.get("filled"):
        _Z=f"LP2_{W}_{_ar['token_id'][-8:]}_{_aq['token_id'][-8:]}";opps_out.append({"sleeve":"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","market":f"{W}: {bx['label']}","ask_vwap":_ap["box_cost_net"],"p_model":float(bx["min_payout"]),"net_edge":round(float(bx["min_payout"])-float(_ap["box_cost_net"]),4),"l1_usd":_ap["l1_usd"],"close_ts":bx["close_ts"]})
        if(a._can_emit_zero_loss_math_live("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",float(bx["close_ts"]),now)and float(bx["min_payout"])>=1.-1e-6 and float(_ap["box_cost_net"])<=.99 and _ar.get("market_id")!=_aq.get("market_id")and.0<(float(bx["close_ts"])-now)<=604800.):a.emit_live_two_leg_box_candidate(sleeve_source="LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",box_type="MACRO_DOMINANCE",asset="MACRO",dedupe_key=_Z,leg_a=_ar,leg_b=_aq,bk_a=_1,bk_b=_0,close_ts=float(bx["close_ts"]),now_ts=now,k_low=1e2,k_high=101. if int(bx.get("jackpot_states")or 0)>0 else 1e2)
        await a.open_shadow_two_leg_box("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",_Z,W,f"{W}: {bx['label']}",_ar,_aq,_1,_0,float(bx["close_ts"]),.992,{"is_two_leg_box":True,"group":W,"guaranteed_payout":bx["min_payout"],"max_payout":bx["max_payout"],"jackpot_states":bx["jackpot_states"]})
      elif int(bx["n_legs"])==3 and all(x["token_id"]in _l for x in _2):
       _k=f"LP2_3L_{W}_{'_'.join(x['token_id'][-6:]for x in _2)}";_z=walk_equal_shares_multi_leg_box([{"asks":_l[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x["fee_exponent"])}for x in _2],BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],float(bx["min_payout"]),.992,min_shares=6,min_box_notional_usd=5.5)
       if _z.get("filled"):opps_out.append({"sleeve":"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","market":f"{W} 3-Leg: {bx['label']}","ask_vwap":_z["box_cost_net"],"p_model":float(bx["min_payout"]),"net_edge":round(float(bx["min_payout"])-float(_z["box_cost_net"]),4),"l1_usd":_z["l1_usd"],"close_ts":bx["close_ts"]});await a.open_shadow_multi_leg_bundle("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",_k,W,f"{W} 3-Leg: {bx['label']}",_2,_l,float(bx["close_ts"]),float(bx["min_payout"]),.992,{"is_multi_leg_bundle":True,"guaranteed_payout":bx["min_payout"],"max_payout":bx["max_payout"]})
    _j=await asyncio.to_thread(detect_lp2_seat_convert_implication_arbs,a.lp2_events_by_slug,_l,BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],1.035)
    if _j:
     _Y=_j[0];a._record_market_telemetry(f"LP2_CONV_{_Y['mode']}",90.,{"type":"LP2_CONVERT_MIDDLE_SNAP","mode":_Y["mode"],"synthetic_box_cost_net":_Y["synthetic_box_cost_net"],"shares_out":_Y["shares_out"]},now_ts=now,sig=(_Y["mode"],_Y["synthetic_box_cost_net"]))
     for cv in _j:
      if float(cv["synthetic_box_cost_net"])<=.992:_ao=int(cv["m_no_legs"]);C=float(_ao);I=float(_ao-1)+.992;_y=f"LP2_CV_{cv['mode']}";opps_out.append({"sleeve":"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","market":cv["label"],"ask_vwap":cv["synthetic_box_cost_net"],"p_model":1.,"net_edge":cv["guaranteed_floor_edge_ps"],"l1_usd":cv["l1_usd"],"close_ts":cv["close_ts"]});await a.open_shadow_multi_leg_bundle("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",_y,"LP2_CONVERT",cv["label"],cv["legs"],_l,float(cv["close_ts"]),C,I,{"is_multi_leg_bundle":True,"guaranteed_payout":C,"mode":cv["mode"],"index_set_int":cv["index_set_int"]})
  k=[s for s in a.nba_subperiod_slates.values()if s.settle_est_ts>now+120]
  for _x in k[:10]:
   h=[t for rgs in _x.ext_props_by_player_stat.values()if len(rgs)>=2 for r in rgs for t in(r.yes_token,r.no_token)];h+=[t for sm in _x.subperiod_markets if sm.period_scope in("1H","Q1")and sm.kind in("ML","SPREAD")for t in(sm.tok_0,sm.tok_1)]
   if not h:continue
   _i=await a.fetch_books_batch(sorted(set(h)),timeout=3.5);U={t:p for t,bk in _i.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.};H=detect_sp4_subperiod_and_ext_prop_boxes(_x,U,max_box_cost_net=1.045)
   if H:sb0=H[0];a._record_market_telemetry(f"SP4_SUB_{_x.event_id}",90.,{"type":"SP4_SUBPERIOD_BOX_BEST","game":_x.title[:60],"mode":sb0["mode"],"label":sb0["label"],"net_box_l1":sb0["box_cost_net"]},now_ts=now,sig=(sb0["label"],sb0["box_cost_net"]))
   for sbx in H[:8]:
    if float(sbx["box_cost_net"])>.992:continue
    _an,_am=sbx["leg_a"],sbx["leg_b"];_X,_W=_i.get(_an["token_id"]),_i.get(_am["token_id"])
    if not _X or not _W:continue
    _al=walk_equal_shares_dominance_box(_X.get("asks")or[],_W.get("asks")or[],BANKROLL_TICKETS["T1000"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],float(_an["fee_rate"]),float(_am["fee_rate"]),fee_exponent_a=float(_an.get("fee_exponent",1.)),fee_exponent_b=float(_am.get("fee_exponent",1.)),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
    if _al.get("filled"):
     _V=f"SP4_SUB_{_an['market_id']}_{_am['market_id']}";opps_out.append({"sleeve":"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","market":f"NBA [{sbx['mode']}] {sbx['label']}","ask_vwap":_al["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_al["box_cost_net"]),4),"l1_usd":_al["l1_usd"],"close_ts":sbx["close_ts"]})
     if(a._can_emit_zero_loss_math_live("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",float(sbx["close_ts"]),now)and float(_al["box_cost_net"])<=.99 and _an.get("market_id")!=_am.get("market_id")and.0<(float(sbx["close_ts"])-now)<=259200.):a.emit_live_two_leg_box_candidate(sleeve_source="SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",box_type="NBA_DOMINANCE",asset="NBA",dedupe_key=_V,leg_a=_an,leg_b=_am,bk_a=_X,bk_b=_W,close_ts=float(sbx["close_ts"]),now_ts=now,k_low=float(_an.get("strike")or 1e2),k_high=float(_am.get("strike")or 101.))
     await a.open_shadow_two_leg_box("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",_V,"NBA_SUBPERIOD",f"{_x.title} [{sbx['label']}]",_an,_am,_X,_W,float(sbx["close_ts"]),.992,{"is_two_leg_box":True,"mode":sbx["mode"]})
  g=bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_rt_mono1_scalar_ladders",True));B=[sp for sp in a.cal1_ladders.values()if sp.rungs and sp.rungs[-1].end_ts>now+120 and(g or"SCALAR"not in str(sp.ladder_kind or"").upper())]
  if B:
   T=sorted({t for sp in B for r in sp.rungs for t in(r.yes_token,r.no_token)});_h=await a.fetch_books_batch(T,timeout=4.);S={t:p for t,bk in _h.items()for p,s in[a._best_ask_sz(bk)]if p<1. and s>=8. and p*s>=1.05}
   for _w in B:
    G=detect_cal1_monotonic_boxes(_w,S,max_box_cost_net=1.045)
    if G:cb0=G[0];a._record_market_telemetry(f"CAL1_{_w.event_id}",90.,{"type":"CAL1_LADDER_BOX_BEST","kind":_w.ladder_kind,"label":cb0["label"],"net_box_l1":cb0["box_cost_net"]},now_ts=now,sig=(cb0["label"],cb0["box_cost_net"]))
    for cbx in G[:6]:
     _ak,_aj=cbx["leg_a"],cbx["leg_b"];_U,_T=_h.get(_ak["token_id"]),_h.get(_aj["token_id"])
     if not _U or not _T:continue
     if float(cbx["box_cost_net"])>.992:
      if(float(cbx["box_cost_net"])<=1.035 and max(float(_ak.get("fee_rate",.0)),float(_aj.get("fee_rate",.0)))==.0 and _ak.get("market_id")!=_aj.get("market_id")and(float(cbx.get("early_leg_close_ts")or cbx["close_ts"])-now)>=65.):a.post_zero_fee_maker_anchor_box("CAL1_LADDER","MACRO",f"ZF_CAL1_{_ak['market_id']}_{_aj['market_id']}",_ak,_aj,_U,_T,float(cbx["close_ts"]),str(cbx["label"]),now,prefetched_books=_h)
      continue
     _ai=walk_equal_shares_dominance_box(_U.get("asks")or[],_T.get("asks")or[],BANKROLL_TICKETS["T1000"]["CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"],float(_ak["fee_rate"]),float(_aj["fee_rate"]),fee_exponent_a=float(_ak["fee_exponent"]),fee_exponent_b=float(_aj["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
     if _ai.get("filled"):
      _S=f"CAL1_{_ak['market_id']}_{_aj['market_id']}";opps_out.append({"sleeve":"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","market":cbx["label"],"ask_vwap":_ai["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_ai["box_cost_net"]),4),"l1_usd":_ai["l1_usd"],"close_ts":cbx["close_ts"]})
      if(a._can_emit_zero_loss_math_live("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",float(cbx["close_ts"]),now)and _ak.get("market_id")!=_aj.get("market_id")and.0<(float(cbx["close_ts"])-now)<=604800. and(float(cbx.get("early_leg_close_ts")or cbx["close_ts"])-now)>=60.):a.emit_live_two_leg_box_candidate(sleeve_source="CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",box_type="MACRO_DOMINANCE",asset="MACRO",dedupe_key=_S,leg_a=_ak,leg_b=_aj,bk_a=_U,bk_b=_T,close_ts=float(cbx["close_ts"]),now_ts=now,k_low=float(_ak.get("strike")or 1e2),k_high=float(_aj.get("strike")or 101.))
      await a.open_shadow_two_leg_box("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",_S,f"CAL1_{_w.ladder_kind}",cbx["label"],_ak,_aj,_U,_T,float(cbx["close_ts"]),.992,{"is_two_leg_box":True,"mode":cbx["mode"],"ladder_kind":_w.ladder_kind})
  for _R in list(a.lp1_nfl_em_bundles.values())[:32]:
   if float(_R["end_ts"])<=now+60:continue
   R=sorted({str(lg["token_id"])for lg in _R["legs"]});_g=await a.fetch_books_batch(R,timeout=3.5);Q={t:p for t,bk in _g.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.};F=find_state_matrix_dominance_boxes(_R["legs"],Q,max_2leg_cost_net=1.045,max_3leg_cost_net=.99)
   if F:nb0=F[0];a._record_market_telemetry(f"LP1_NFL_EM_{_R['event_id']}",90.,{"type":"LP1_NFL_EM_BOX_BEST","game":_R["title"][:60],"n_legs":nb0["n_legs"],"label":nb0["label"],"net_box_l1":nb0["box_cost_net"]},now_ts=now,sig=(nb0["label"],nb0["box_cost_net"]))
   for nbx in F[:6]:
    if float(nbx["box_cost_net"])>.99 or int(nbx["n_legs"])!=2:continue
    _Q,_P=nbx["legs"][0],nbx["legs"][1];_v,_u=_g.get(_Q["token_id"]),_g.get(_P["token_id"])
    if not _v or not _u:continue
    _ah=walk_equal_shares_dominance_box(_v.get("asks")or[],_u.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX"],float(_Q["fee_rate"]),float(_P["fee_rate"]),fee_exponent_a=float(_Q["fee_exponent"]),fee_exponent_b=float(_P["fee_exponent"]),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
    if _ah.get("filled"):
     _O=f"LP1_NFLEM_{_R['event_id']}_{_Q['token_id'][-8:]}_{_P['token_id'][-8:]}";opps_out.append({"sleeve":"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","market":f"NFL EM [{_R['title']}]: {nbx['label']}","ask_vwap":_ah["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_ah["box_cost_net"]),4),"l1_usd":_ah["l1_usd"],"close_ts":nbx["close_ts"]})
     if(a._can_emit_zero_loss_math_live("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",float(nbx["close_ts"]),now)and float(nbx.get("min_payout",1.))>=1.-1e-6 and float(_ah["box_cost_net"])<=.988 and _Q.get("market_id")!=_P.get("market_id")and.0<(float(nbx["close_ts"])-now)<=604800.):a.emit_live_two_leg_box_candidate(sleeve_source="LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",box_type="SPORTS_CORRIDOR",asset="NFL",dedupe_key=_O,leg_a=_Q,leg_b=_P,bk_a=_v,bk_b=_u,close_ts=float(nbx["close_ts"]),now_ts=now,k_low=1e2,k_high=101. if float(nbx.get("max_payout",1.))>1.05 else 1e2)
     await a.open_shadow_two_leg_box("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",_O,"NFL_EM",f"{_R['title']} [{nbx['label']}]",_Q,_P,_v,_u,float(nbx["close_ts"]),.99,{"is_two_leg_box":True,"mode":"NFL_EXACT_MARGIN_DOMINANCE","max_payout":nbx["max_payout"]})
  A=list(a.multisport_raw_events.values())[:24]
  if A:
   z=[]
   for _,w in A:
    for _ag in w.get("markets")or[]:
     if not _ag.get("closed")and str(_ag.get("sportsMarketType")or"").lower()in("moneyline","spreads","first_half_moneyline","first_half_spreads","q1_moneyline","q1_spreads"):
      _N=_parse_clob_tokens(_ag)
      if _N:z.extend(_N)
   if z:
    E=await a.fetch_books_batch(sorted(set(z)),timeout=3.5);y={t:p for t,bk in E.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for P,w in A:
     O=detect_multisport_ml_spread_polish_middles(w,y,sport_hint=P,max_box_cost_net=1.04)
     for pbx in O[:4]:
      if float(pbx["box_cost_net"])>.988:continue
      _af,_ae=pbx["leg_a"],pbx["leg_b"];_M,_L=E.get(_af["token_id"]),E.get(_ae["token_id"])
      if not _M or not _L:continue
      _ad=walk_equal_shares_dominance_box(_M.get("asks")or[],_L.get("asks")or[],BANKROLL_TICKETS["T1000"]["LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX"],float(_af["fee_rate"]),float(_ae["fee_rate"]),fee_exponent_a=float(_af["fee_exponent"]),fee_exponent_b=float(_ae["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
      if _ad.get("filled"):
       _K=f"LP1_MSPM_{_af['market_id']}_{_ae['market_id']}";opps_out.append({"sleeve":"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","market":pbx["label"],"ask_vwap":_ad["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_ad["box_cost_net"]),4),"l1_usd":_ad["l1_usd"],"close_ts":pbx["close_ts"]})
       if(a._can_emit_zero_loss_math_live("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",float(pbx["close_ts"]),now)and _af.get("market_id")!=_ae.get("market_id")and.0<(float(pbx["close_ts"])-now)<=604800.):a.emit_live_two_leg_box_candidate(sleeve_source="LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",box_type="SPORTS_CORRIDOR",asset=str(P).upper(),dedupe_key=_K,leg_a=_af,leg_b=_ae,bk_a=_M,bk_b=_L,close_ts=float(pbx["close_ts"]),now_ts=now,k_low=1e2,k_high=101.)
       await a.open_shadow_two_leg_box("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",_K,f"{P}_MIDDLE",pbx["label"],_af,_ae,_M,_L,float(pbx["close_ts"]),.988,{"is_two_leg_box":True,"mode":pbx["mode"]})
  v=[t for t in a.tennis_specs.values()if t.end_ts>now+60]
  if v:
   N=[]
   for L in v[:25]:
    for _J in L.totals_by_scope.values():
     for r_t in _J:N.extend([r_t.over_token,r_t.under_token])
    for _t in(L.set1_a_token,L.set1_b_token,L.set2_a_token,L.set2_b_token,L.sets_ou25_over_token,L.sets_ou25_under_token,L.comp_yes_token,L.comp_no_token):
     if _t:N.append(_t)
   if N:
    _f=await a.fetch_books_batch(sorted(set(N)),timeout=3.5);M={t:p for t,bk in _f.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
    for L in v[:25]:
     _e=evaluate_ten1_tennis_opportunities(L,_f,M,max_box_cost_net=1.045)
     if _e:_ac=_e[0];a._record_market_telemetry(f"TEN1_{L.event_id}",90.,{"type":"TEN1_CORRIDOR_BEST","match":L.title[:60],"mode":_ac["mode"],"label":_ac["label"],"net_box_l1":_ac["box_cost_net"]},now_ts=now,sig=(_ac["label"],_ac["box_cost_net"]))
     for tbx in _e[:4]:
      if float(tbx["box_cost_net"])>.988:continue
      _I,_H=tbx["leg_a"],tbx["leg_b"];_s,_r=_f.get(_I["token_id"]),_f.get(_H["token_id"])
      if not _s or not _r:continue
      _ab=walk_equal_shares_dominance_box(_s.get("asks")or[],_r.get("asks")or[],BANKROLL_TICKETS["T1000"]["TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR"],float(_I["fee_rate"]),float(_H["fee_rate"]),fee_exponent_a=float(_I["fee_exponent"]),fee_exponent_b=float(_H["fee_exponent"]),max_box_cost_net=.988,min_shares=6,min_box_notional_usd=5.5)
      if _ab.get("filled"):
       _G=f"TEN1_{_I['market_id']}_{_H['market_id']}";opps_out.append({"sleeve":"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR","market":tbx["label"],"ask_vwap":_ab["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_ab["box_cost_net"]),4),"l1_usd":_ab["l1_usd"],"close_ts":tbx["close_ts"]})
       if(a._can_emit_zero_loss_math_live("TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",float(tbx["close_ts"]),now)and _I.get("market_id")!=_H.get("market_id")and.0<(float(tbx["close_ts"])-now)<=259200.):a.emit_live_two_leg_box_candidate(sleeve_source="TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",box_type="SPORTS_CORRIDOR",asset="TENNIS",dedupe_key=_G,leg_a=_I,leg_b=_H,bk_a=_s,bk_b=_r,close_ts=float(tbx["close_ts"]),now_ts=now,k_low=float(_I.get("strike")or 1e2),k_high=float(_H.get("strike")or 101.))
       await a.open_shadow_two_leg_box("TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",_G,"TENNIS_BO3",tbx["label"],_I,_H,_s,_r,float(tbx["close_ts"]),.988,{"is_two_leg_box":True,"mode":tbx["mode"]})
  j=[]
  if any((tr.end_ts-3.5*3600.)<=now<=(tr.end_ts+2.*3600.)for tr in a.soccer_trees.values()):j.append("SOCCER")
  for sp_k in("NHL","NFL","CFB"):
   if any(ms.sport==sp_k and(ms.start_ts-9e2)<=now<=(ms.start_ts+6.*3600.)for ms in a.multi_sport_games.values()):j.append(sp_k)
  u={}
  def i(sp_k):
   s=a.live_multisport_boards.get(sp_k);t=(s[1]or[])if s else[];p=any(getattr(gm,"state","")=="in"for gm in t);r=any(getattr(gm,"state","")=="in"and(float(getattr(gm,"clock_sec",9999)or 9999)<=125. or bool(getattr(gm,"is_halftime",False)))for gm in t)
   try:from src.polymarket_research.polymarket_direct_feeds import compute_adaptive_sports_poll_interval_sec as c;return min(20.,float(c(is_endgame_or_halftime=r,has_live_games=p)))
   except Exception:return.75 if r else(5.5 if p else 20.)
  l=[sp_k for sp_k in j if sp_k not in a.live_multisport_boards or(now-a.live_multisport_boards[sp_k][0])>=i(sp_k)];q=not a.single_scan and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_official_league_direct_feeds",True))
  if l:
   o=await asyncio.gather(*(asyncio.to_thread(fetch_espn_multisport_board_sync,sp_k)for sp_k in l))
   for sp_k,m in zip(l,o):
    if q and sp_k in("NHL","MLB"):
     try:from src.polymarket_research.polymarket_direct_feeds import(fetch_mlb_statsapi_scoreboard_sync as d,fetch_nhl_official_scoreboard_sync as e,reconcile_multisport_dual_source_boards as b);_d=e if sp_k=="NHL"else d;m=b(sp_k,m,await asyncio.to_thread(_d))
     except Exception:pass
    a.live_multisport_boards[sp_k]=(now,m)
  if q:
   for _F in("ATP","WTA"):
    _c=a.live_multisport_boards.get(_F);_b=any((gm.get("state")=="in")if isinstance(gm,dict)else False for gm in((_c[1]or[])if _c else[]))
    if _c is None or(now-_c[0])>=(1. if _b else 30.):
     try:from src.polymarket_research.polymarket_direct_feeds import fetch_atp_wta_live_scores_sync as f;_q=await asyncio.to_thread(f,_F.lower());a.live_multisport_boards[_F]=(now,_q)
     except Exception:pass
  for sp_k in j:
   if sp_k in a.live_multisport_boards:u[sp_k]=a.live_multisport_boards[sp_k][1]
  D=[]
  if"SOCCER"in u and u["SOCCER"]:
   for tr in a.soccer_trees.values():
    for _aa in evaluate_cl1_soccer_tree_clinch_locks(tr,u["SOCCER"],a.score_confirm_tracker,now):
     _E=f"CL1_SOC_{_aa['market_id']}"
     if _E not in a.entered_keys and _E not in a.inflight_keys:D.append({**_aa,"dedupe_key":_E,"title":getattr(tr,"title",""),"rules_text":getattr(tr,"rules_text","")})
  for _D in a.multi_sport_games.values():
   if _D.sport in u and u[_D.sport]:
    for _9 in evaluate_cl1_multisport_corridor_clinch_locks(_D,u,a.score_confirm_tracker,now):
     _p=f"CL1_{_D.sport}_{_9['market_id']}"
     if _p not in a.entered_keys and _p not in a.inflight_keys:D.append({**_9,"dedupe_key":_p,"title":getattr(_D,"title",""),"rules_text":getattr(_D,"rules_text","")})
  if D:
   _a=await a.fetch_books_batch(sorted({t for c in D for t in(c["token_id"],c["opp_token_id"])}),timeout=3.)
   for _8 in D:
    if"FINAL"not in str(_8.get("mode")or"").upper()and classify_market_rule_dispute_risk(_8)["veto_pre_final_clinch"]:continue
    Z,Y=_a.get(_8["token_id"]),_a.get(_8["opp_token_id"])
    if not Z or not Y:continue
    K,_=extract_best_bid(Y.get("bids")or[])
    if K>.04:continue
    _C=float(_8.get("fee_rate")or.0);_B=float(_8.get("fee_exponent")or 1.);_7=walk_l2_book_asks_depth_capped(Z.get("asks")or[],BANKROLL_TICKETS["T1000"]["CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"],BANKROLL_TICKETS["T100"]["CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"],fee_rate=_C,min_l1_usd=15.,max_ask_px=.9821,fee_exponent=_B)
    if _7.get("filled"):
     _o=float(_7["eff_px"]);_6=float(_8["p_lock"]);_n=round(_6-_o,4)
     if.72<=_o<=.982 and _n>=.015:
      J=max(now+6e2,float(_8["close_ts"]));opps_out.append({"sleeve":"CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","market":f"[{_8['mode']}] {_8['display_label']}","ask_vwap":_o,"p_model":_6,"net_edge":_n,"l1_usd":_7["l1_usd"],"close_ts":J})
      if a._can_emit_zero_loss_math_live("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",J,now,p_model=_6):a.emit_live_single_leg_lock_candidate(sleeve_source="CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",asset=str(_8["sport"]).upper(),dedupe_key=str(_8["dedupe_key"]),token_id=str(_8["token_id"]),opp_token_id=str(_8["opp_token_id"]),market_id=str(_8["market_id"]),condition_id=str(_8["condition_id"]),side_label=str(_8["side_label"]),display_label=str(_8["display_label"]),bk_win=Z,bk_opp=Y,fee_rate=_C,fee_exponent=_B,neg_risk=bool(_8.get("neg_risk",False)),close_ts=J,now_ts=now,max_lock_eff_px=.982,max_opp_bid=.025,hold_to_maturity=True,p_model=_6)
      await a.open_shadow_position("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",_8["dedupe_key"],_8["sport"],_8["display_label"],str(_8["side_label"]),str(_8["token_id"]),_C,_6,J,{"market_id":_8["market_id"],"condition_id":_8["condition_id"],"opp_token_id":_8["opp_token_id"],"mode":_8["mode"],"fee_exponent":_B},prefetched_book=Z)
 async def _scan_frontier_v4_sleeves(a,opps_out,now):
  y=[];a.subperiod_freeze_tracker.prune(now);a.score_confirm_tracker.prune(now);o=[]
  if any((lat.end_ts-3.5*3600.)<=now<=(lat.end_ts+2.5*3600.)for lat in a.soc2_lattices.values()):o.append("SOCCER")
  if any((b.sport=="NFL"and(b.start_ts-9e2)<=now<=(b.start_ts+6.*3600.))for b in a.aff1_bundles.values())or any((sl.kickoff_ts-9e2)<=now<=(sl.kickoff_ts+6.*3600.)for sl in a.nfl_prop_slates.values()):o.append("NFL")
  if any((b.sport=="CFB"and(b.start_ts-9e2)<=now<=(b.start_ts+6.*3600.))for b in a.aff1_bundles.values()):o.append("CFB")
  I=[sp_k for sp_k in o if sp_k not in a.live_multisport_boards or(now-a.live_multisport_boards[sp_k][0])>=20.]
  if I:
   O=await asyncio.gather(*(asyncio.to_thread(fetch_espn_multisport_board_sync,sp_k)for sp_k in I))
   for sp_k,_4 in zip(I,O):a.live_multisport_boards[sp_k]=(now,_4)
  N=[b for b in a.aff1_bundles.values()if b.settle_est_ts>now+120.]
  if N:
   _e={t for b in N for t in([tk for m in b.markets for tk in(m.tok_0,m.tok_1)]+([str(b.overtime_yes_leg["token_id"])]if b.overtime_yes_leg else[])+[tk for fp in b.first_passage_markets for tk in(fp.away_token,fp.home_token)])if t};_j=await a.fetch_books_batch(sorted(_e),timeout=3.5)if _e else{};_d={t:p for t,bk in _j.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for b in N:
    for tri in detect_sum1_frechet_triangles(b,_d,max_3leg_cost_net=.99):
     _3=tri["legs"]
     if not all(x["token_id"]in _j for x in _3):continue
     _D=f"SUM1_{b.event_id}_{'_'.join(str(x['token_id'])[-6:]for x in _3)}";_2=walk_equal_shares_multi_leg_box([{"asks":_j[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x["fee_exponent"])}for x in _3],BANKROLL_TICKETS["T1000"]["SUM1_FRECHET_SUM_TRIANGLES"],1.,.99,min_shares=6,min_box_notional_usd=5.5)
     if _2.get("filled"):opps_out.append({"sleeve":"SUM1_FRECHET_SUM_TRIANGLES","market":tri["label"],"ask_vwap":_2["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_2["box_cost_net"]),4),"l1_usd":_2["l1_usd"],"close_ts":tri["close_ts"]});await a.open_shadow_multi_leg_bundle("SUM1_FRECHET_SUM_TRIANGLES",_D,b.sport,tri["label"],_3,_j,float(tri["close_ts"]),1.,.99,{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"mode":tri["mode"]})
    d=None;i=""
    if b.sport=="NBA"and a.live_nba_board:
     M=a.nba_games.get(b.event_id);H=match_nba_live_game(M,a.live_nba_board)if M is not None else None
     if H is not None and H[0].state in("in","post"):
      i=str(H[0].game_id or"")
      if i:
       _1=a.nba_ext_summary_cache.get(i)
       if _1 is not None and(now-_1[0])<15.:d=_1[1]
       else:
        try:_C,_0=await asyncio.to_thread(fetch_espn_nba_full_summary_sync,i);a.nba_boxscore_cache[i]=(now,_C);a.nba_ext_summary_cache[i]=(now,_0);d=_0
        except Exception:d=None
    elif b.sport in("NFL","CFB")and b.sport in a.live_multisport_boards:
     for _ae in a.live_multisport_boards[b.sport][1]:
      if _ae.start_ts>0 and b.start_ts>0 and abs(_ae.start_ts-b.start_ts)>10.*3600.:continue
      _B=_teams_match_fuzzy(b.away_team,_ae.away_name)and _teams_match_fuzzy(b.home_team,_ae.home_name);_A=_teams_match_fuzzy(b.away_team,_ae.home_name)and _teams_match_fuzzy(b.home_team,_ae.away_name)
      if _B and _A:continue
      if _B or _A:i=_ae.game_id;_Z=dict(_ae.linescores_home if _A else _ae.linescores_away);_Y=dict(_ae.linescores_away if _A else _ae.linescores_home);d={"state":_ae.state,"completed":_ae.completed,"is_halftime":_ae.is_halftime,"period":_ae.period,"clock_sec":_ae.clock_sec,"away_score":_ae.home_score if _A else _ae.away_score,"home_score":_ae.away_score if _A else _ae.home_score,"linescores":{"away":_Z,"home":_Y}};break
    if d:
     _i=evaluate_aff1_frozen_subperiod_opportunities(b,d,_d,a.subperiod_freeze_tracker,now,espn_game_id=i,max_2leg_cost_net=1.035,max_3leg_cost_net=.99);w=bool(d.get("is_halftime"))or float(d.get("clock_sec")or.0)<=.01
     for abx in _i["two_leg_boxes"]:
      _X,_W=abx["leg_a"],abx["leg_b"];_z,_y=_j.get(_X["token_id"]),_j.get(_W["token_id"])
      if not _z or not _y:continue
      _x=f"AFF1_2L_{b.event_id}_{_X['token_id'][-8:]}_{_W['token_id'][-8:]}"
      if float(abx["box_cost_net"])>.992:
       if(w and not bool(d.get("completed"))and float(abx["box_cost_net"])<=1.035 and max(float(_X.get("fee_rate",.0)),float(_W.get("fee_rate",.0)))==.0):a.post_zero_fee_maker_anchor_box("AFF1_DEADBALL",str(b.sport),f"ZF_{_x}",_X,_W,_z,_y,float(abx["close_ts"]),str(abx["label"]),now,prefetched_books=_j)
       continue
      _V=walk_equal_shares_dominance_box(_z.get("asks")or[],_y.get("asks")or[],BANKROLL_TICKETS["T1000"]["AFF1_FROZEN_SUBPERIOD_COLLAPSE"],float(_X["fee_rate"]),float(_W["fee_rate"]),fee_exponent_a=float(_X["fee_exponent"]),fee_exponent_b=float(_W["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
      if _V.get("filled"):
       opps_out.append({"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","market":abx["label"],"ask_vwap":_V["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_V["box_cost_net"]),4),"l1_usd":_V["l1_usd"],"close_ts":abx["close_ts"]})
       if(a._can_emit_zero_loss_math_live("AFF1_FROZEN_SUBPERIOD_COLLAPSE",float(abx["close_ts"]),now)and float(_V["box_cost_net"])<=.988 and.0<(float(abx["close_ts"])-now)<=86400.):a.emit_live_two_leg_box_candidate(sleeve_source="AFF1_FROZEN_SUBPERIOD_COLLAPSE",box_type="SPORTS_CORRIDOR",asset=b.sport,dedupe_key=_x,leg_a=_X,leg_b=_W,bk_a=_z,bk_b=_y,close_ts=float(abx["close_ts"]),now_ts=now,k_low=float(_X.get("strike")or 1e2),k_high=float(_W.get("strike")or 101.))
       await a.open_shadow_two_leg_box("AFF1_FROZEN_SUBPERIOD_COLLAPSE",_x,b.sport,abx["label"],_X,_W,_z,_y,float(abx["close_ts"]),.992,{"is_two_leg_box":True,"mode":abx["mode"],"middle_width":abx["middle_width"]})
     for ab3 in _i["three_leg_boxes"]:
      _ad=ab3["legs"]
      if not all(x["token_id"]in _j for x in _ad):continue
      _w=f"AFF1_3L_{b.event_id}_{'_'.join(str(x['token_id'])[-6:]for x in _ad)}";_U=walk_equal_shares_multi_leg_box([{"asks":_j[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x["fee_exponent"])}for x in _ad],BANKROLL_TICKETS["T1000"]["AFF1_FROZEN_SUBPERIOD_COLLAPSE"],1.,.99,min_shares=6,min_box_notional_usd=5.5)
      if _U.get("filled"):opps_out.append({"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","market":ab3["label"],"ask_vwap":_U["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_U["box_cost_net"]),4),"l1_usd":_U["l1_usd"],"close_ts":ab3["close_ts"]});await a.open_shadow_multi_leg_bundle("AFF1_FROZEN_SUBPERIOD_COLLAPSE",_w,b.sport,ab3["label"],_ad,_j,float(ab3["close_ts"]),1.,.99,{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"mode":ab3["mode"]})
     for alk in _i["single_leg_locks"]:_v=f"AFF1_LK_{b.event_id}_{alk['market_id']}";y.append({**alk,"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","asset":b.sport,"dedupe_key":_v,"max_eff_px":.988,"title":getattr(b,"title",""),"rules_text":getattr(b,"rules_text","")})
  V=a.live_multisport_boards["SOCCER"][1]if"SOCCER"in a.live_multisport_boards else[]
  if V:
   for lat in a.soc2_lattices.values():
    if(lat.end_ts+7200.)<=now:continue
    for slk in evaluate_soc2_dead_score_no_locks(lat,V,a.score_confirm_tracker,now):_u=f"SOC2_NO_{slk['market_id']}";y.append({**slk,"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","asset":"SOCCER","dedupe_key":_u,"max_eff_px":.986,"title":getattr(lat,"title",""),"rules_text":getattr(lat,"rules_text","")})
  _c=[lat for lat in a.soc2_lattices.values()if lat.end_ts>now+120.][:10]
  if _c:
   U=sorted({str(lg["token_id"])for lat in _c for lg in lat.matrix_legs if lg.get("token_id")}|{str(t_cv)for lat in _c if lat.convert_spec is not None for b_cv in lat.convert_spec.brackets for t_cv in(b_cv.get("no_token"),b_cv.get("yes_token"))if t_cv});_b=await a.fetch_books_batch(U,timeout=3.5)if U else{};T={t:p for t,bk in _b.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for lat in _c:
    _t=detect_soc2_lattice_boxes_and_converts(lat,_b,T,max_2leg_cost_net=.99,max_3leg_cost_net=.988,target_budget_usd=BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"])
    for sbx in _t["matrix_boxes"]:
     _T=sbx["legs"]
     if int(sbx["n_legs"])==2:
      _ac,_ab=_T[0],_T[1];_S,_R=_b.get(_ac["token_id"]),_b.get(_ab["token_id"])
      if not _S or not _R:continue
      _Q=f"SOC2_2L_{lat.exact_event_id}_{_ac['token_id'][-8:]}_{_ab['token_id'][-8:]}";_aa=walk_equal_shares_dominance_box(_S.get("asks")or[],_R.get("asks")or[],BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"],float(_ac["fee_rate"]),float(_ab["fee_rate"]),fee_exponent_a=float(_ac.get("fee_exponent",1.)),fee_exponent_b=float(_ab.get("fee_exponent",1.)),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
      if _aa.get("filled"):
       opps_out.append({"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","market":f"{lat.title}: {sbx['label']}","ask_vwap":_aa["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_aa["box_cost_net"]),4),"l1_usd":_aa["l1_usd"],"close_ts":sbx["close_ts"]})
       if(bool(sbx.get("exhaustive_partition_verified"))and a._can_emit_zero_loss_math_live("SOC2_EXACT_SCORE_2D_LATTICE",float(sbx["close_ts"]),now)and _ac.get("market_id")!=_ab.get("market_id")and float(_aa["box_cost_net"])<=.988 and.0<(float(sbx["close_ts"])-now)<=172800.):a.emit_live_two_leg_box_candidate(sleeve_source="SOC2_EXACT_SCORE_2D_LATTICE",box_type="SPORTS_CORRIDOR",asset="SOCCER",dedupe_key=_Q,leg_a=_ac,leg_b=_ab,bk_a=_S,bk_b=_R,close_ts=float(sbx["close_ts"]),now_ts=now,k_low=float(_ac.get("strike")or 1e2),k_high=float(_ab.get("strike")or 101.))
       await a.open_shadow_two_leg_box("SOC2_EXACT_SCORE_2D_LATTICE",_Q,"SOCCER",f"{lat.title}: {sbx['label']}",_ac,_ab,_S,_R,float(sbx["close_ts"]),.99,{"is_two_leg_box":True,"mode":sbx["mode"]})
     elif int(sbx["n_legs"])==3 and all(x["token_id"]in _b for x in _T):
      _P=f"SOC2_3L_{lat.exact_event_id}_{'_'.join(str(x['token_id'])[-6:]for x in _T)}";_9=walk_equal_shares_multi_leg_box([{"asks":_b[x["token_id"]].get("asks")or[],"fee_rate":float(x["fee_rate"]),"fee_exponent":float(x.get("fee_exponent",1.))}for x in _T],BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"],1.,.988,min_shares=6,min_box_notional_usd=5.5)
      if _9.get("filled"):opps_out.append({"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","market":f"{lat.title} 3L: {sbx['label']}","ask_vwap":_9["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_9["box_cost_net"]),4),"l1_usd":_9["l1_usd"],"close_ts":sbx["close_ts"]});await a.open_shadow_multi_leg_bundle("SOC2_EXACT_SCORE_2D_LATTICE",_P,"SOCCER",f"{lat.title} 3L: {sbx['label']}",_T,_b,float(sbx["close_ts"]),1.,.988,{"is_multi_leg_bundle":True,"guaranteed_payout":1.,"mode":sbx["mode"]})
    if lat.convert_spec is not None and _t["convert_arbs"]:await a.execute_nr2_subset_convert_arb(lat.convert_spec,_t["convert_arbs"][0],_b,opps_out)
  v=[sl for sl in a.nfl_prop_slates.values()if sl.settle_est_ts>now+120.][:8]
  if v:
   A=sorted({tk for sl in v for rg in(list(sl.anytime_td_by_player.values())+list(sl.two_plus_td_by_player.values())+[r for r_list in sl.ladders_by_player_stat.values()for r in r_list])for tk in(rg.yes_over_token,rg.no_under_token)if tk});G=await a.fetch_books_batch(A,timeout=3.5)if A else{};z={t:p for t,bk in G.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.};S=a.live_multisport_boards["NFL"][1]if"NFL"in a.live_multisport_boards else[]
   for sl in v:
    for pbx in detect_nfl_prp1_boxes(sl,z,max_box_cost_net=.99):
     _O,_N=pbx["leg_a"],pbx["leg_b"];_s,_r=G.get(_O["token_id"]),G.get(_N["token_id"])
     if not _s or not _r:continue
     _M=f"NFL_PRP1_2L_{sl.event_id}_{_O['token_id'][-8:]}_{_N['token_id'][-8:]}";_8=walk_equal_shares_dominance_box(_s.get("asks")or[],_r.get("asks")or[],BANKROLL_TICKETS["T1000"]["NFL_PRP1_MILESTONE_AND_MAX_LOCKS"],float(_O["fee_rate"]),float(_N["fee_rate"]),fee_exponent_a=float(_O["fee_exponent"]),fee_exponent_b=float(_N["fee_exponent"]),max_box_cost_net=.99,min_shares=6,min_box_notional_usd=5.5)
     if _8.get("filled"):
      opps_out.append({"sleeve":"NFL_PRP1_MILESTONE_AND_MAX_LOCKS","market":f"{sl.title} [{pbx['label']}]","ask_vwap":_8["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_8["box_cost_net"]),4),"l1_usd":_8["l1_usd"],"close_ts":pbx["close_ts"]})
      if(a._can_emit_zero_loss_math_live("NFL_PRP1_MILESTONE_AND_MAX_LOCKS",float(pbx["close_ts"]),now)and _O.get("market_id")!=_N.get("market_id")and float(_8["box_cost_net"])<=.988 and.0<(float(pbx["close_ts"])-now)<=172800.):a.emit_live_two_leg_box_candidate(sleeve_source="NFL_PRP1_MILESTONE_AND_MAX_LOCKS",box_type="SPORTS_CORRIDOR",asset="NFL",dedupe_key=_M,leg_a=_O,leg_b=_N,bk_a=_s,bk_b=_r,close_ts=float(pbx["close_ts"]),now_ts=now,k_low=float(_O.get("strike")or.5),k_high=float(_N.get("strike")or 1.5))
      await a.open_shadow_two_leg_box("NFL_PRP1_MILESTONE_AND_MAX_LOCKS",_M,"NFL",f"{sl.title} [{pbx['label']}]",_O,_N,_s,_r,float(pbx["close_ts"]),.99,{"is_two_leg_box":True,"mode":pbx["mode"]})
    if S:
     F=next((g for g in S if(g.start_ts<=0 or abs(g.start_ts-sl.kickoff_ts)<=10.*3600.)and((_teams_match_fuzzy(sl.away_team,g.away_name)and _teams_match_fuzzy(sl.home_team,g.home_name))!=(_teams_match_fuzzy(sl.away_team,g.home_name)and _teams_match_fuzzy(sl.home_team,g.away_name)))),None)
     if F is not None and F.state in("in","post"):
      _7=a.nfl_summary_cache.get(F.game_id)
      if _7 is not None and(now-_7[0])<15.:h=_7[1]
      else:
       try:h=await asyncio.to_thread(fetch_espn_nfl_summary_sync,F.game_id);a.nfl_summary_cache[F.game_id]=(now,h)
       except Exception:h={}
      if h:
       for nlk in evaluate_nfl_prp1_live_locks(sl,h,a.score_confirm_tracker,now):_q=f"NFL_PRP1_LK_{sl.event_id}_{nlk['market_id']}";y.append({**nlk,"sleeve":"NFL_PRP1_MILESTONE_AND_MAX_LOCKS","asset":"NFL","dedupe_key":_q,"max_eff_px":.988,"title":getattr(sl,"title",""),"rules_text":getattr(sl,"rules_text","")})
  if a.barrier_rungs or a.binance_close_rungs:
   R=[hr for hr in a.barrier_rungs.values()if hr.resolved_yes is None and hr.end_ts>now+120. and hr.asset!="HYPE"and(a.spots.get(hr.asset,.0)<=.0 or abs(math.log(max(1e-9,hr.strike)/a.spots[hr.asset]))<=.35)];E=[cr for cr in a.binance_close_rungs if cr.close_ts>now+120. and cr.asset!="HYPE"and(a.spots.get(cr.asset,.0)<=.0 or abs(math.log(max(1e-9,cr.strike)/a.spots[cr.asset]))<=.35)];_a=sorted({t for hr in R for t in(hr.yes_token,hr.no_token)}|{cr.no_token for cr in E})
   if _a:
    _h=await a.fetch_books_batch(_a,timeout=3.5);Z={t:p for t,bk in _h.items()for p,s in[a._best_ask_sz(bk)]if p<1. and s>=8. and p*s>=1.05}
    for cbx in detect_cry_inc1_binance_inclusion_boxes(R,E,Z,now,max_box_cost_net=.992):
     _L,_K=cbx["leg_a"],cbx["leg_b"];_p,_o=_h.get(_L["token_id"]),_h.get(_K["token_id"])
     if not _p or not _o:continue
     _J=f"CRY_INC1_{cbx['asset']}_{_L['market_id']}_{_K['market_id']}";_6=walk_equal_shares_dominance_box(_p.get("asks")or[],_o.get("asks")or[],BANKROLL_TICKETS["T1000"]["CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION"],float(_L["fee_rate"]),float(_K["fee_rate"]),fee_exponent_a=float(_L["fee_exponent"]),fee_exponent_b=float(_K["fee_exponent"]),max_box_cost_net=.992,min_shares=6,min_box_notional_usd=5.5)
     if _6.get("filled"):
      opps_out.append({"sleeve":"CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION","market":cbx["label"],"ask_vwap":_6["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_6["box_cost_net"]),4),"l1_usd":_6["l1_usd"],"close_ts":cbx["close_ts"]})
      if(a._can_emit_zero_loss_math_live("CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",float(cbx["close_ts"]),now)and float(_6["box_cost_net"])<=.988 and.0<(float(cbx["close_ts"])-now)<=604800.):a.emit_live_two_leg_box_candidate(sleeve_source="CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",box_type="BARRIER_MONO",asset=str(cbx["asset"]),dedupe_key=_J,leg_a=_L,leg_b=_K,bk_a=_p,bk_b=_o,close_ts=float(cbx["close_ts"]),now_ts=now,k_low=min(float(_L["strike"]),float(_K["strike"])),k_high=max(float(_L["strike"]),float(_K["strike"])))
      await a.open_shadow_two_leg_box("CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",_J,str(cbx["asset"]),cbx["label"],_L,_K,_p,_o,float(cbx["close_ts"]),.992,{"is_two_leg_box":True,"mode":cbx["mode"],"direction":cbx["direction"]})
  u=[c for c in y if c["dedupe_key"]not in a.entered_keys and c["dedupe_key"]not in a.inflight_keys]
  if u:
   Q=await a.fetch_books_batch(sorted({t for c in u for t in(str(c["token_id"]),str(c["opp_token_id"]))if t}),timeout=3.)
   for clk in u:
    P=classify_market_rule_dispute_risk(clk)
    if"FINAL"not in str(clk.get("mode")or"").upper()and P["veto_pre_final_clinch"]:continue
    _I,_H=str(clk["token_id"]),str(clk["opp_token_id"]);q,_g=Q.get(_I),Q.get(_H)
    if not q or not _g:continue
    q={**q,"_s2_meta":{"mode":str(clk.get("mode")or""),"dispute_risk":bool(P["dispute_risk"]),"question":str(clk.get("question")or clk.get("display_label")or"")[:120],**({"volume24hr":round(float(clk.get("volume24hr")or.0),2)}if clk.get("volume24hr")is not None else{})}};L,_=extract_best_bid(_g.get("bids")or[])
    if L>.035:continue
    _G=str(clk["sleeve"]);_F=float(clk.get("fee_rate")or.0);_E=float(clk.get("fee_exponent")or 1.);K=float(clk.get("max_eff_px")or.988);_f=float(clk["p_lock"]);Y=max(now+6e2,float(clk["close_ts"]));j=not(a.single_scan or("fetch_json"in a.__dict__));_5=walk_l2_book_asks_depth_capped(q.get("asks")or[],BANKROLL_TICKETS["T1000"][_G],BANKROLL_TICKETS["T100"][_G],fee_rate=_F,min_l1_usd=15.,max_ask_px=K+1e-4,fee_exponent=_E);e=False;k=False
    if _5.get("filled"):
     _n=float(_5["eff_px"]);_m=round(_f-_n,4)
     if.72<=_n<=K and _m>=.012:k=True;opps_out.append({"sleeve":_G,"market":f"[{clk['mode']}] {clk['display_label']}","ask_vwap":_n,"p_model":_f,"net_edge":_m,"l1_usd":_5["l1_usd"],"close_ts":Y})
    f=False
    if(k or(j and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_partial_fak_single_leg_sweep",True))))and a._can_emit_zero_loss_math_live(_G,Y,now,p_model=_f):n=(a.compute_live_8e_clinch_max_eff_px(K,_f,Y-now)if j else K);f=bool(a.emit_live_single_leg_lock_candidate(sleeve_source=_G,asset=str(clk["asset"]).upper(),dedupe_key=str(clk["dedupe_key"]),token_id=_I,opp_token_id=_H,market_id=str(clk["market_id"]),condition_id=str(clk["condition_id"]),side_label=str(clk["side_label"]),display_label=str(clk["display_label"]),bk_win=q,bk_opp=_g,fee_rate=_F,fee_exponent=_E,neg_risk=bool(clk.get("neg_risk",False)),close_ts=Y,now_ts=now,max_lock_eff_px=n,max_opp_bid=.025,hold_to_maturity=True,p_model=_f))
    if k:e=await a.open_shadow_position(_G,str(clk["dedupe_key"]),str(clk["asset"]),str(clk["display_label"]),str(clk["side_label"]),_I,_F,_f,Y,{"market_id":clk["market_id"],"condition_id":clk["condition_id"],"opp_token_id":_H,"mode":clk["mode"],"fee_exponent":_E},prefetched_book=q)
    if not e and not f:
     _l=f"MKR_LK1_{clk['market_id']}";l=_l not in a.entered_keys and _l not in a.inflight_keys
     if l or(j and _l not in a.inflight_keys):
      X,J=extract_best_bid(q.get("bids")or[]);W,_=a._best_ask_sz(q);D=a.resolve_2026_maker_rebate_share(str(clk["asset"]),_G);C=.997 if(j and _f>=.999 and(Y-now)<=7200.)else.991;B=.0025 if C>=.997 else.006;_k=evaluate_mkr_lock1_post_clinch_rebate_bid(token_id=_I,opp_token_id=_H,market_id=str(clk["market_id"]),condition_id=str(clk["condition_id"]),display_label=str(clk["display_label"]),source_sleeve=_G,p_lock=_f,close_ts=Y,now_ts=now,best_bid=X if X>.0 else None,best_ask=W if W<1. else None,opp_best_bid=L,fee_rate=_F,fee_exponent=_E,maker_rebate_share=D,neg_risk=bool(clk.get("neg_risk",False)),max_maker_bid=C,min_net_edge_ps=B)
      if _k is not None:
       if l:opps_out.append({"sleeve":"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER","market":_k["display_label"],"ask_vwap":_k["effective_net_cost_per_share"],"p_model":_f,"net_edge":round(float(_k["expected_net_edge_per_share"]),4),"l1_usd":max(25.,J),"close_ts":Y})
       if(X>=.94-1e-9 and J>=10.-1e-6 and a._can_emit_zero_loss_math_live("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",Y,now,p_model=_f)):a.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",asset=str(clk["asset"]).upper(),dedupe_key=_l,pair_dedupe_key=str(clk["dedupe_key"]),token_id=_I,opp_token_id=_H,market_id=str(clk["market_id"]),condition_id=str(clk["condition_id"]),side_label=str(clk["side_label"]),display_label=str(clk["display_label"]),bk_win=q,bk_opp=_g,neg_risk=bool(clk.get("neg_risk",False)),close_ts=Y,now_ts=now,min_resting_bid=.94,max_resting_bid=C,min_maker_edge=B,max_opp_bid=.03,hold_to_maturity=True,p_model=_f,target_bid_px=float(_k["post_only_bid"]),maker_rebate_ps=float(_k["maker_rebate_per_share"]),event_id=str(clk.get("event_id")or clk.get("event_slug")or""))
       if l:await a.post_shadow_maker_entry(sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",dedupe_key=_l,asset=str(clk["asset"]),title=str(_k["display_label"]),side_label=str(clk["side_label"]),token_id=_I,p_model=_f,close_ts=Y,extra={"market_id":clk["market_id"],"condition_id":clk["condition_id"],"opp_token_id":_H,"source_sleeve":_G,"resting_bid_override":_k["post_only_bid"],"maker_rebate_ps":_k["maker_rebate_per_share"]},prefetched_book=q,ttl_override_sec=180.)
 async def _scan_phase2_macro_counting_gas(a,opps_out,now):
  try:await a._scan_phase2_macro_counting_gas_core(opps_out,now)
  except Exception as b:logger.warning(f"[ALPHA-124] Phase-2 macro/counting/gas scan notice: {b}")
  if a.single_scan or"fetch_json"in a.__dict__ or not bool(a.__dict__.get("_uma_bg_loop_active")):await a.scan_uma_resolution_bonds(opps_out,now_ts=now)
 async def _scan_phase2_macro_counting_gas_core(a,opps_out,now):
  F=[s for s in a.counting_slates.values()if s.window_end_ts>now+60]
  if F:
   _e=sorted({s.handle for s in F});_t=await asyncio.gather(*(asyncio.to_thread(fetch_xtracker_user_stats_sync,h)for h in _e));z=dict(zip(_e,_t));X=[t for s in F for b in s.brackets for t in(b.yes_token,b.no_token)];_d=await a.fetch_books_batch(X,timeout=3.5);n={}
   for t_c,_3 in _d.items():
    _2,_1=a._best_ask_sz(_3)
    if _2<1. and _2*_1>=8.:n[t_c]=_2
   for _0 in F:
    _c,W=evaluate_counting_dead_no_locks(_0,z.get(_0.handle)or{});a._record_market_telemetry(key=f"TW1_SNAP_{_0.event_id}",min_interval_sec=120.,now_ts=now,sig=(_c,len(W)),payload={"type":"COUNTING_TRACKER_SNAP","slug":_0.slug,"handle":_0.handle,"verified_floor":_c,"dead_open_brackets":len(W),"tte_sec":round(_0.window_end_ts-now,0)});m=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{})
    if W and bool(m.get("enable_xtrack1_expanded_handles",True)):
     E=detect_counting_pruned_exhaustive_yes_slate(_0,z.get(_0.handle)or{},_d,max_bundle_cost_net=.99,max_surviving_legs=12,min_shares=5.)
     if E is not None:
      _s=E["legs"];opps_out.append({"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","market":f"{_0.handle} Pruned Exhaustive YES ({len(_s)} legs, floor>={_c})","ask_vwap":E["bundle_cost_net_ps"],"p_model":1.,"net_edge":E["net_edge_per_share"],"l1_usd":round(float(E["shares"])*float(E["bundle_cost_net_ps"]),2),"close_ts":_0.window_end_ts})
      if len(_s)==2:a.emit_live_two_leg_box_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",box_type="COUNTING_DOMINANCE",asset=_0.handle.upper(),dedupe_key=f"NR0_PRUNED2_{_0.event_id}",leg_a=_s[0],leg_b=_s[1],bk_a=_d.get(_s[0]["token_id"])or{},bk_b=_d.get(_s[1]["token_id"])or{},close_ts=float(_0.window_end_ts),now_ts=now)
      elif 3<=len(_s)<=12:a.emit_live_special_v2_box_candidate(box_type="MULTI_LEG_BUNDLE",sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",asset=_0.handle.upper(),dedupe_key=f"NR0_PRUNED_{_0.event_id}",close_ts=float(_0.window_end_ts),now_ts=now,payload={"legs":_s,"shares":E["shares"],"max_fillable_shares":E["shares"],"cost_per_share":E["bundle_cost_net_ps"],"box_cost_net":E["bundle_cost_net_ps"],"max_box_cost_net":.99,"net_edge_per_share":E["net_edge_per_share"],"neg_risk":True,"includes_unbounded_top_cap":True})
    y=a.negrisk_convert_slates.get(_0.event_id)
    if(W and y is not None and y.is_closed_convert_safe and bool(m.get("enable_nr_m1_dead_seed_fanout",True))):
     w={dbr.market_id for dbr in W};D={int(b_nr.get("question_index")if isinstance(b_nr,dict)else b_nr.question_index)for b_nr in y.brackets if(b_nr.get("market_id")if isinstance(b_nr,dict)else getattr(b_nr,"market_id",None))in w and(b_nr.get("question_index")if isinstance(b_nr,dict)else getattr(b_nr,"question_index",None))is not None}
     if D:
      a.__dict__.setdefault("_ws_dead_q_by_event",{})[_0.event_id]=set(D);_r=detect_nr_m1_dead_seed_fanout(y,D,_d,fee_bips=int(getattr(y,"fee_bips",0)or 0),min_shares=5.,min_net_edge_usd=.0035)
      if _r is not None:opps_out.append({"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","market":f"{_0.handle} NR_M1 Dead-NO Fanout (Q{_r['dead_question_index']})","ask_vwap":_r["ask_eff_per_share"],"p_model":1.,"net_edge":_r["net_edge_per_share"],"l1_usd":round(float(_r["shares"])*float(_r["ask_eff_per_share"]),2),"close_ts":_0.window_end_ts});a.emit_live_negrisk_convert_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",spec=y,dedupe_key=f"NRM1_CNT_{_0.event_id}_Q{_r['dead_question_index']}",arb_hit=_r,books_by_token=_d,now_ts=now,fee_bips=int(getattr(y,"fee_bips",0)or 0))
    for dbr in(W if bool(m.get("enable_xtrack1_6handle_dead_no",True))else()):
     _q=_d.get(dbr.no_token)
     if not _q:continue
     _p,_=extract_best_bid(_q.get("bids")or[]);_o,_=a._best_ask_sz(_q);_n=float(getattr(dbr,"fee_rate",.0)or.0);_m=float(getattr(dbr,"fee_exponent",1.)or 1.);_L=walk_l2_book_asks(_q.get("asks")or[],BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"],fee_rate=_n,min_l1_usd=15.,max_ask_px=.99,fee_exponent=_m);C=bool(_L.get("filled")and.8<=float(_L["eff_px"])<=.99 and round(1.-float(_L["eff_px"]),4)>=.01)
     if C:_l=round(1.-float(_L["eff_px"]),4);opps_out.append({"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","market":f"{_0.handle} Dead Bracket NO[{dbr.label}] (count>={_c})","ask_vwap":_L["eff_px"],"p_model":1.,"net_edge":_l,"l1_usd":_L["l1_usd"],"close_ts":_0.window_end_ts})
     v=not(a.single_scan or("fetch_json"in a.__dict__));V=float(_0.window_end_ts-now)
     if 25.<V<=172800. and(C or(v and bool(m.get("enable_partial_fak_single_leg_sweep",True)))):u=((.995 if V<=14400. else(.992 if V<=43200. else.99))if v else.99);a.emit_live_single_leg_lock_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",asset=_0.handle.upper(),dedupe_key=f"TW1_NO_{dbr.market_id}",token_id=dbr.no_token,opp_token_id=dbr.yes_token,market_id=dbr.market_id,condition_id=dbr.condition_id,side_label="NO",display_label=f"{_0.handle} Dead NO[{dbr.label}]",bk_win=_q,bk_opp=_d.get(dbr.yes_token),fee_rate=_n,fee_exponent=_m,neg_risk=bool(dbr.neg_risk),close_ts=float(_0.window_end_ts),now_ts=now,max_lock_eff_px=u,max_opp_bid=.02,hold_to_maturity=(not C or float(_L["eff_px"])>=.98),p_model=1.)
     if C:await a.open_shadow_position("TW1_COUNTING_TRUNCATION_AND_BOX",f"TW1_NO_{dbr.market_id}",_0.handle.upper(),f"{_0.title} [Dead NO {dbr.label}]","NO",dbr.no_token,_n,1.,_0.window_end_ts,{"market_id":dbr.market_id,"condition_id":dbr.condition_id,"verified_floor":_c,"fee_exponent":_m},prefetched_book=_q)
     i=False;_K=evaluate_locked_market_reward_carry(1.,_p,_o,dbr.rewards_min_size,dbr.rewards_max_spread,_n)
     if _K.get("eligible"):
      opps_out.append({"sleeve":"MKR_REWARD_LOCKED_CARRY","market":f"{_0.handle} Locked Carry NO[{dbr.label}] @ ${_K['resting_bid']:.3f}","ask_vwap":_K["resting_bid"],"p_model":1.,"net_edge":_K["carry_edge"],"l1_usd":50.,"close_ts":_0.window_end_ts});await a.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY",f"MKR_RW_{dbr.market_id}",_0.handle.upper(),f"{_0.title} [Reward Carry NO {dbr.label}]","NO",dbr.no_token,1.,_0.window_end_ts,{"market_id":dbr.market_id,"condition_id":dbr.condition_id,"opp_token_id":dbr.yes_token,"resting_bid_override":_K["resting_bid"]},prefetched_book=_q)
      if(is_reward_locked_carry_live_ready(a,1.,min_reward_shares=float(dbr.rewards_min_size or.0),resting_bid_px=float(_K["resting_bid"]))and getattr(dbr,"neg_risk",None)is not None):_k=float(_K["resting_bid"]);B=a.resolve_2026_maker_rebate_share(_0.handle.upper(),"TW1_COUNTING_TRUNCATION_AND_BOX");_b=round(B*_n*((_k*(1.-_k))**_m),5)if _n>.0 else.0;i=bool(a.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_REWARD_LOCKED_CARRY",asset=_0.handle.upper(),dedupe_key=f"MKR_RW_{dbr.market_id}",pair_dedupe_key=f"MKR_RW_PAIR_{dbr.market_id}",token_id=dbr.no_token,opp_token_id=dbr.yes_token,market_id=dbr.market_id,condition_id=dbr.condition_id,side_label="NO",display_label=f"{_0.handle} Reward Carry NO[{dbr.label}]",bk_win=_q,bk_opp=_d.get(dbr.yes_token),neg_risk=bool(dbr.neg_risk),close_ts=float(_0.window_end_ts),now_ts=now,min_resting_bid=.94,max_resting_bid=.994,min_maker_edge=.006,max_opp_bid=.03,hold_to_maturity=True,p_model=1.,target_bid_px=_k,maker_rebate_ps=_b))
     if(not i and not C and v and getattr(dbr,"neg_risk",None)is not None and _d.get(dbr.yes_token)is not None and 120.<(float(_0.window_end_ts)-now)<=14400. and.94<=_p<=.994 and a._can_emit_zero_loss_math_live("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",float(_0.window_end_ts),now,p_model=1.)):r=a.resolve_2026_maker_rebate_share(_0.handle.upper(),"TW1_COUNTING_TRUNCATION_AND_BOX");K=round(r*_n*((_p*(1.-_p))**_m),5)if _n>.0 else.0;a.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",asset=_0.handle.upper(),dedupe_key=f"MKR_TW1_{dbr.market_id}",pair_dedupe_key=f"TW1_NO_{dbr.market_id}",token_id=dbr.no_token,opp_token_id=dbr.yes_token,market_id=dbr.market_id,condition_id=dbr.condition_id,side_label="NO",display_label=f"{_0.handle} Dead NO[{dbr.label}] FINAL",bk_win={**_q,"_s2_meta":{"is_final":True,"clinch_mode":"FINAL"}},bk_opp=_d.get(dbr.yes_token),neg_risk=bool(dbr.neg_risk),close_ts=float(_0.window_end_ts),now_ts=now,min_resting_bid=.94,max_resting_bid=.994,min_maker_edge=.005,max_opp_bid=.02,hold_to_maturity=True,p_model=1.,maker_rebate_ps=K)
   U=detect_counting_subwindow_boxes(F,n,z,max_box_cost_net=1.05)
   if U:tb0=U[0];a._record_market_telemetry(f"TW1_BOX_{tb0['handle']}",90.,{"type":"COUNTING_SUBWINDOW_BEST","handle":tb0["handle"],"net_box_l1":tb0["box_cost_net"],"label":tb0["label"]},now_ts=now,sig=(tb0["label"],tb0["box_cost_net"]))
   for tb in U:
    _Z,_Y=tb["leg_a"],tb["leg_b"];_J,_I=_d.get(_Z["token_id"]),_d.get(_Y["token_id"])
    if not _J or not _I:continue
    _H=f"TW1_BOX_{_Z['market_id']}_{_Y['market_id']}"
    if float(tb["box_cost_net"])<=.993:
     _X=walk_equal_shares_dominance_box(_J.get("asks")or[],_I.get("asks")or[],BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"],float(_Z.get("fee_rate",.0)),float(_Y.get("fee_rate",.0)),fee_exponent_a=float(_Z.get("fee_exponent",1.)),fee_exponent_b=float(_Y.get("fee_exponent",1.)),max_box_cost_net=.993,min_shares=6,min_box_notional_usd=5.5)
     if _X.get("filled"):
      opps_out.append({"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","market":f"Counting Box {tb['label']}","ask_vwap":_X["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_X["box_cost_net"]),4),"l1_usd":_X["l1_usd"],"close_ts":tb["close_ts"]});g=False
      if(float(tb["close_ts"])-now)<=86400. and float(_X["box_cost_net"])<=.99:g=a.emit_live_two_leg_box_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",box_type="COUNTING_DOMINANCE",asset=tb["handle"].upper(),dedupe_key=_H,leg_a=_Z,leg_b=_Y,bk_a=_J,bk_b=_I,close_ts=float(tb["close_ts"]),now_ts=now)
      await a.open_shadow_two_leg_box("TW1_COUNTING_TRUNCATION_AND_BOX",_H,tb["handle"].upper(),f"Counting Box {tb['label']}",_Z,_Y,_J,_I,float(tb["close_ts"]),.993,{"is_two_leg_box":True,"banked":tb["banked"]})
      if not g:a.post_zero_fee_maker_anchor_box("TW1",tb["handle"].upper(),f"ZFA_{_H}",_Z,_Y,_J,_I,float(tb["close_ts"]),f"Counting Box {tb['label']}",now,prefetched_books=_d,live_emit_only=True)
     else:a.post_zero_fee_maker_anchor_box("TW1",tb["handle"].upper(),f"ZFA_{_H}",_Z,_Y,_J,_I,float(tb["close_ts"]),f"Counting Box {tb['label']}",now,prefetched_books=_d)
    elif float(tb["box_cost_net"])<=1.035:a.post_zero_fee_maker_anchor_box("TW1",tb["handle"].upper(),f"ZFA_{_H}",_Z,_Y,_J,_I,float(tb["close_ts"]),f"Counting Box {tb['label']}",now,prefetched_books=_d)
  _a=[lg for lg in(a.fomc_truth_legs+a.oil_senate_truth_legs)if float(lg["end_ts"])>now+60]
  if _a:
   _j=await a.fetch_books_batch(sorted({str(lg["token_id"])for lg in _a}),timeout=3.5);Z={t:p for t,bk in _j.items()for p,s in[a._best_ask_sz(bk)]if p<1. and p*s>=8.}
   for _G,T,S,R,_i in(("FED1_CENTRAL_BANK_LP_BOX","FOMC",a.fomc_truth_legs,ALL_FOMC_MASK,"FOMC_LP_BEST"),("COND1_MACRO_PARTITION_BOX","OIL_SENATE",a.oil_senate_truth_legs,ALL_OIL_SENATE_MASK,"OIL_SENATE_PARTITION_BEST")):
    if not S:continue
    Y=find_cross_event_bitmask_boxes(S,Z,R,max_2leg_cost=1.05,max_3leg_cost=1.03)
    if Y:b0=Y[0];a._record_market_telemetry(f"{_i}_DIAG",90.,{"type":_i,"n_legs":b0["n_legs"],"net_box_l1":b0["box_cost_net"],"label":b0["label"]},now_ts=now,sig=(b0["label"],b0["box_cost_net"]))
    for bx in Y:
     _9=bx["legs"]
     if int(bx["n_legs"])==2:
      _W,_V=_9[0],_9[1];_F,_E=_j.get(_W["token_id"]),_j.get(_V["token_id"])
      if not _F or not _E:continue
      _U=f"{T}_2L_{_W['token_id'][-8:]}_{_V['token_id'][-8:]}"
      if float(bx["box_cost_net"])<=.994:
       _8=walk_equal_shares_dominance_box(_F.get("asks")or[],_E.get("asks")or[],BANKROLL_TICKETS["T1000"][_G],float(_W.get("fee_rate",.0)),float(_V.get("fee_rate",.0)),fee_exponent_a=float(_W.get("fee_exponent",1.)),fee_exponent_b=float(_V.get("fee_exponent",1.)),max_box_cost_net=.994,min_shares=6,min_box_notional_usd=5.5)
       if _8.get("filled"):
        opps_out.append({"sleeve":_G,"market":f"{T} {bx['label']}","ask_vwap":_8["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_8["box_cost_net"]),4),"l1_usd":_8["l1_usd"],"close_ts":bx["close_ts"]});d=False
        if _G=="FED1_CENTRAL_BANK_LP_BOX"and(float(bx["close_ts"])-now)<=172800. and float(_8["box_cost_net"])<=.99:d=a.emit_live_two_leg_box_candidate(sleeve_source=_G,box_type="MACRO_DOMINANCE",asset=T,dedupe_key=_U,leg_a=_W,leg_b=_V,bk_a=_F,bk_b=_E,close_ts=float(bx["close_ts"]),now_ts=now)
        elif(_G=="COND1_MACRO_PARTITION_BOX"and(float(bx["close_ts"])-now)<=(172800. if a.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX")else 1.08e5)and float(_8["box_cost_net"])<=((.992 if(float(bx["close_ts"])-now)<=1.08e5 else.988)if a.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX")else.985)):d=a.emit_live_two_leg_box_candidate(sleeve_source=_G,box_type="MACRO_DOMINANCE",asset=T,dedupe_key=_U,leg_a=_W,leg_b=_V,bk_a=_F,bk_b=_E,close_ts=float(bx["close_ts"]),now_ts=now)
        await a.open_shadow_two_leg_box(_G,_U,T,f"{T} {bx['label']}",_W,_V,_F,_E,float(bx["close_ts"]),.994,{"is_two_leg_box":True,"double_pay_states":bx["double_pay_states"]})
        if not d:a.post_zero_fee_maker_anchor_box(T,T,f"ZFA_{_U}",_W,_V,_F,_E,float(bx["close_ts"]),f"{T} {bx['label']}",now,prefetched_books=_j,live_emit_only=True)
       else:a.post_zero_fee_maker_anchor_box(T,T,f"ZFA_{_U}",_W,_V,_F,_E,float(bx["close_ts"]),f"{T} {bx['label']}",now,prefetched_books=_j)
      elif float(bx["box_cost_net"])<=1.035:a.post_zero_fee_maker_anchor_box(T,T,f"ZFA_{_U}",_W,_V,_F,_E,float(bx["close_ts"]),f"{T} {bx['label']}",now,prefetched_books=_j)
     elif int(bx["n_legs"])==3 and float(bx["box_cost_net"])<=.992:
      _T=f"{T}_3L_{'_'.join(x['token_id'][-6:]for x in _9)}";_7=walk_equal_shares_multi_leg_box([{"asks":_j[x["token_id"]].get("asks")or[],"fee_rate":float(x.get("fee_rate",.0)),"fee_exponent":float(x.get("fee_exponent",1.))}for x in _9],BANKROLL_TICKETS["T1000"][_G],1.,.992,min_shares=6,min_box_notional_usd=5.5)
      if _7.get("filled"):
       opps_out.append({"sleeve":_G,"market":f"{T} 3-Leg {bx['label']}","ask_vwap":_7["box_cost_net"],"p_model":1.,"net_edge":round(1.-float(_7["box_cost_net"]),4),"l1_usd":_7["l1_usd"],"close_ts":bx["close_ts"]})
       if((float(bx["close_ts"])-now)<=172800. and float(_7["box_cost_net"])<=.99 and all(isinstance(x.get("neg_risk"),bool)for x in _9)):
        Q=[]
        for _S in _9:
         _D=_j.get(str(_S["token_id"]))or{};_C,_B=a._best_ask_sz(_D)
         if _C<1. and _B>=5.:Q.append({"token_id":str(_S["token_id"]),"opp_token_id":str(_S.get("opp_token_id")or""),"market_id":str(_S.get("market_id")or""),"condition_id":str(_S.get("condition_id")or""),"side":str(_S.get("side")or"YES"),"label":str(_S.get("label")or""),"fee_rate":float(_S.get("fee_rate",.0)),"fee_exponent":float(_S.get("fee_exponent",1.)),"neg_risk":bool(_S["neg_risk"]),"ask_px":_C,"ask_size":_B})
        if len(Q)==3:a.emit_live_special_v2_box_candidate(box_type="MULTI_LEG_BUNDLE",sleeve_source=_G,asset=T,dedupe_key=_T,close_ts=float(bx["close_ts"]),now_ts=now,payload={"legs":Q,"shares":_7["shares"],"max_fillable_shares":min(float(_7["shares"]),min(float(c["ask_size"])for c in Q)),"cost_per_share":float(_7["box_cost_net"]),"box_cost_net":float(_7["box_cost_net"]),"max_box_cost_net":.99,"net_edge_per_share":round(1.-float(_7["box_cost_net"]),6),"neg_risk":any(bool(c["neg_risk"])for c in Q)})
       await a.open_shadow_multi_leg_bundle(_G,_T,T,f"{T} 3-Leg {bx['label']}",_9,_j,float(bx["close_ts"]),1.,.992,{"is_multi_leg_bundle":True,"guaranteed_payout":1.})
  l=[e for e in(a.gas_events_raw.get("us-gas-price-daily")or[])if not e.get("closed")]
  if l:
   _6=await asyncio.to_thread(fetch_aaa_national_gas_sync)
   if _6:
    a._record_market_telemetry("AAA_GAS_SNAP",3e2,{"type":"AAA_GAS_SNAP",**_6},now_ts=now,sig=(_6["as_of_date"],_6["current_regular"]));_h=float(_6["current_regular"])
    for _R in l:
     _A=_parse_iso_ts(_R.get("endDate"))or.0
     if not(60.<(_A-now)<=57600.):continue
     _g=re.search(r"(20\d{2}-\d{2}-\d{2})",str(_R.get("slug")or""));_f=_g.group(1)if _g else datetime.fromtimestamp(_A,tz=NY_TZ).date().isoformat()
     if _f!=_6["as_of_date"]:continue
     _z=[]
     for mg in(_R.get("markets")or[]):
      if mg.get("closed"):continue
      O,N=_extract_market_fee_rate(mg);P=_parse_clob_tokens(mg);_Q=parse_gas_daily_bracket(str(mg.get("groupItemTitle")or mg.get("question")or""))
      if P and _Q:_z.append((mg,P,_Q,O,N))
     if not _z:continue
     _y=await a.fetch_books_batch([t for _,tk,_,_,_ in _z for t in tk],timeout=3.)
     for mg,P,(_5,_4),O,N in _z:
      _x=str(mg.get("id")or"");_w=str(mg.get("groupItemTitle")or"")
      if(_5==.0 or _h>=_5+.0015)and(not math.isfinite(_4)or _h<=_4-.0015):q,A="YES",P[0]
      elif _h<=_5-.002 or(math.isfinite(_4)and _h>=_4+.002):q,A="NO",P[1]
      else:continue
      J=P[1]if q=="YES"else P[0];_O=mg.get("negRisk")if mg.get("negRisk")is not None else _R.get("negRisk");_N=_y.get(A)
      if not _N:continue
      wg=walk_l2_book_asks(_N.get("asks")or[],BANKROLL_TICKETS["T1000"]["GAS1_AAA_GASOLINE_LOCK"],fee_rate=O,min_l1_usd=15.,max_ask_px=.985,fee_exponent=N);k=bool(wg.get("filled")and.75<=float(wg["eff_px"])<=.983)
      if k:opps_out.append({"sleeve":"GAS1_AAA_GASOLINE_LOCK","market":f"AAA Gas ${_h:.4f} ({_6['as_of_date']}) -> {q}[{_w}]","ask_vwap":wg["eff_px"],"p_model":.998,"net_edge":round(.998-float(wg["eff_px"]),4),"l1_usd":wg["l1_usd"],"close_ts":_A});await a.open_shadow_position("GAS1_AAA_GASOLINE_LOCK",f"GAS1_{_x}_{q}","AAA_GAS",f"{_R.get('title')} [{q} {_w}]",q,A,O,.998,_A,{"market_id":_x,"condition_id":str(mg.get("conditionId")or""),"opp_token_id":J,"neg_risk":bool(_O)if isinstance(_O,bool)else False,"aaa_price":_h,"as_of_date":_6["as_of_date"],"fee_exponent":N},prefetched_book=_N)
      o=not(a.single_scan or("fetch_json"in a.__dict__));j=(((_5==.0 or _h>=_5+.002)and(not math.isfinite(_4)or _h<=_4-.002))if q=="YES"else(_h<=_5-.002 or(math.isfinite(_4)and _h>=_4+.002)));I=.999 if j else.998
      if(isinstance(_O,bool)and 30.<(_A-now)<=28800. and(k or(o and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_partial_fak_single_leg_sweep",True))))and a._can_emit_zero_loss_math_live("GAS1_AAA_GASOLINE_LOCK",_A,now,p_model=I)):a.emit_live_single_leg_lock_candidate(sleeve_source="GAS1_AAA_GASOLINE_LOCK",asset="AAA_GAS",dedupe_key=f"GAS1_{_x}_{q}",token_id=A,opp_token_id=J,market_id=_x,condition_id=str(mg.get("conditionId")or""),side_label=q,display_label=f"AAA Gas ${_h:.4f} {q}[{_w}]"[:56],bk_win=_N,bk_opp=_y.get(J),fee_rate=O,fee_exponent=N,neg_risk=bool(_O),close_ts=float(_A),now_ts=now,max_lock_eff_px=.992 if(_A-now)<=14400. else.988,max_opp_bid=.015,hold_to_maturity=True,p_model=I)
      _v,_=extract_best_bid(_N.get("bids")or[]);_u,_=a._best_ask_sz(_N);f=False;H=a.resolve_2026_maker_rebate_share("AAA_GAS","GAS1_AAA_GASOLINE_LOCK");_M=evaluate_locked_market_reward_carry(I,_v,_u,float(mg.get("rewardsMinSize")or.0),float(mg.get("rewardsMaxSpread")or.0),O)
      if _M.get("eligible"):
       opps_out.append({"sleeve":"MKR_REWARD_LOCKED_CARRY","market":f"AAA Gas Locked Carry {q}[{_w}] @ ${_M['resting_bid']:.3f}","ask_vwap":_M["resting_bid"],"p_model":I,"net_edge":_M["carry_edge"],"l1_usd":50.,"close_ts":_A});await a.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY",f"MKR_RW_GAS_{_x}_{q}","AAA_GAS",f"{_R.get('title')} [Reward Carry {q} {_w}]",q,A,I,_A,{"market_id":_x,"condition_id":str(mg.get("conditionId")or""),"opp_token_id":J,"resting_bid_override":_M["resting_bid"]},prefetched_book=_N)
       if(is_reward_locked_carry_live_ready(a,I,min_reward_shares=float(mg.get("rewardsMinSize")or.0),resting_bid_px=float(_M["resting_bid"]))and _O is not None and _y.get(J)is not None):M=float(_M["resting_bid"]);G=round(H*O*((M*(1.-M))**N),5)if O>.0 else.0;f=bool(a.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_REWARD_LOCKED_CARRY",asset="AAA_GAS",dedupe_key=f"MKR_RW_GAS_{_x}_{q}",pair_dedupe_key=f"MKR_RW_GASPAIR_{_x}",token_id=A,opp_token_id=J,market_id=_x,condition_id=str(mg.get("conditionId")or""),side_label=q,display_label=f"AAA Gas Reward Carry {q}[{_w}]",bk_win=_N,bk_opp=_y.get(J),neg_risk=bool(_O),close_ts=float(_A),now_ts=now,min_resting_bid=.94,max_resting_bid=.993 if I>=.999 else.99,min_maker_edge=.006 if I>=.999 else.008,max_opp_bid=.03,hold_to_maturity=True,p_model=I,target_bid_px=M,maker_rebate_ps=G,event_id=str(_R.get("id")or _R.get("slug")or"")))
      if(not f and not k and o and I>=.999 and isinstance(_O,bool)and _y.get(J)is not None and 120.<(float(_A)-now)<=14400. and.94<=_v<=.994 and a._can_emit_zero_loss_math_live("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",float(_A),now,p_model=I)):L=round(H*O*((_v*(1.-_v))**N),5)if O>.0 else.0;a.emit_live_single_leg_maker_lock_candidate(sleeve_source="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",asset="AAA_GAS",dedupe_key=f"MKR_GAS1_{_x}_{q}",pair_dedupe_key=f"GAS1_{_x}_{q}",token_id=A,opp_token_id=J,market_id=_x,condition_id=str(mg.get("conditionId")or""),side_label=q,display_label=f"AAA Gas ${_h:.4f} {q}[{_w}] FINAL"[:56],bk_win={**_N,"_s2_meta":{"is_final":True,"clinch_mode":"FINAL"}},bk_opp=_y.get(J),neg_risk=bool(_O),close_ts=float(_A),now_ts=now,min_resting_bid=.94,max_resting_bid=.993,min_maker_edge=.006,max_opp_bid=.015,hold_to_maturity=True,p_model=I,maker_rebate_ps=L,event_id=str(_R.get("id")or _R.get("slug")or""))
 def has_live_nba_window(self,now_ts):return any((sp.tipoff_ts-6e2)<=now_ts<=(sp.tipoff_ts+5.5*3600.)for sp in self.nba_games.values())
 def has_live_sports_window(a,now_ts):return(a.has_live_nba_window(now_ts)or any((c.start_ts-6e2)<=now_ts<=(c.start_ts+5.5*3600.)for c in a.multi_sport_games.values())or any((c.end_ts-2.5*3600.)<=now_ts<=(c.end_ts+1.5*3600.)for c in a.soccer_trees.values())or any((c.end_ts-3.5*3600.)<=now_ts<=(c.end_ts+1.*3600.)for c in a.tennis_specs.values())or any((b.start_ts-6e2)<=now_ts<=(b.start_ts+5.5*3600.)for b in a.aff1_bundles.values())or any((c.end_ts-2.5*3600.)<=now_ts<=(c.end_ts+2.*3600.)for c in a.soc2_lattices.values())or any((c.kickoff_ts-6e2)<=now_ts<=(c.kickoff_ts+5.5*3600.)for c in a.nfl_prop_slates.values()))
 def _load_registry_proposed_uma_markets(b,now_ts):
  c=b.__dict__.get("_universe_registry_db_path")
  if c is not None:d=Path(c)
  elif"fetch_json"in b.__dict__ and not b.__dict__.get("_enable_default_universe_registry_in_mock"):return{}
  else:d=PROJECT_ROOT/"data"/"universe"/"market_registry.sqlite3"
  if not d.is_file():return{}
  n={}
  try:
   m=sqlite3.connect(f"file:{d.as_posix()}?mode=ro",uri=True,timeout=2.)
   try:l=m.execute("SELECT market_id, event_id, condition_id, question_id, neg_risk, neg_risk_request_id, slug, question, outcomes_json, token_ids_json, indicative_prices_json, accepting_orders, enable_order_book, fees_enabled, fee_rate_bps, resolution_source, rule_summary, end_date_iso, volume_24hr, liquidity_usd FROM markets WHERE active=1 AND closed=0 AND archived=0 AND is_kmia_frozen_d001=0 AND lower(uma_resolution_status)='proposed'");j=l.fetchall()
   finally:m.close()
   for r in j:
    k=str(r[0]or"").strip()
    if not k or k in("6707502","6707503"):continue
    h=bool(r[4]);f=f"{r[16]or''}\n{r[15]or''}".strip();e=r[10]or"[]";a=.0
    if isinstance(e,str)and e.strip().startswith("["):
     try:
      g=[float(x)for x in json.loads(e)[:2]]
      if g and.0<g[0]<1.:a=g[0]
      elif len(g)>=2 and.0<g[1]<1.:a=1.-g[1]
     except Exception:a=.0
    o={"id":k,"_parent_event_id":str(r[1]or"").strip(),"conditionId":str(r[2]or"").strip(),"questionID":str(r[3]or"").strip(),"negRisk":h,"negRiskRequestID":str(r[5]or"").strip(),"slug":str(r[6]or"").strip(),"question":str(r[7]or""),"description":f,"outcomes":r[8]or"[]","clobTokenIds":r[9]or"[]","outcomePrices":e,"acceptingOrders":bool(r[11]),"enableOrderBook":bool(r[12]),"feesEnabled":bool(r[13]),"takerBaseFee":float(r[14]or.0),"umaResolutionStatus":"proposed","resolvedBy":("0x69c47de9d4d3dad79590d61b9e05918e03775f24"if h else"0x65070be91477460d8a7aeeb94ef92fe056c2f2a7"),"endDate":str(r[17]or""),"volume24hr":float(r[18]or.0),"liquidity":float(r[19]or.0),"closed":False,"archived":False,"_eval_now_ts":float(now_ts)}
    if.0<a<1.:o["bestBid"]=round(a,6);o["bestAsk"]=round(a,6)
    i,_=is_objective_uma_market(o)
    if i:n[k]=o
  except Exception:return{}
  return n
 async def discover_uma_proposed_markets(a,now_ts):
  c=datetime.fromtimestamp(now_ts+12.*3600.,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");h=[*(a.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=100&offset={E}",timeout=5.5)for E in range(0,900,100)),*(a.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&end_date_max={c}&order=volume24hr&ascending=false&limit=100&offset={E}",timeout=5.5)for E in range(0,400,100)),*(a.fetch_json(f"{GAMMA_URL}/events?active=true&closed=false&order=volume24hr&ascending=false&limit=100&offset={E}",timeout=6.)for E in range(0,1500,100)),*(a.fetch_json(f"{GAMMA_URL}/events?active=true&closed=false&end_date_max={c}&order=endDate&ascending=false&limit=100&offset={E}",timeout=6.)for E in(0,100,200,300))];t,g=await asyncio.gather(asyncio.gather(*h),asyncio.to_thread(a._load_registry_proposed_uma_markets,now_ts));s={}
  for D in t:
   if not isinstance(D,list):continue
   for B in D:
    if not isinstance(B,dict):continue
    e=B.get("markets")
    if isinstance(e,list):
     r=B.get("negRisk");n=str(B.get("id")or B.get("slug")or"").strip();m=str(B.get("slug")or"").strip()
     for A in e:
      if not isinstance(A,dict):continue
      q=str(A.get("id")or"").strip()
      if not q or q in s or q in("6707502","6707503"):continue
      if(("negRisk"not in A and r is not None)or(n and"_parent_event_id"not in A)or(m and"_ev_slug"not in A)):A={**A,**({"negRisk":r}if("negRisk"not in A and r is not None)else{}),**({"_parent_event_id":n}if(n and"_parent_event_id"not in A)else{}),**({"_ev_slug":m}if(m and"_ev_slug"not in A)else{})}
      z,_=is_objective_uma_market(A)
      if z:s[q]=A
    else:
     C=str(B.get("id")or"").strip()
     if not C or C in s or C in("6707502","6707503"):continue
     l,_=is_objective_uma_market(B)
     if l:s[C]=B
  if g:
   b=sorted([m_id for m_id in g if m_id not in s],key=lambda E:-((1e6 if(.9<=float(g[E].get("bestBid")or.0)<=.9985 or.002<=float(g[E].get("bestAsk")or 1.)<=.1)else.0)+float(g[E].get("volume24hr")or.0)))
   for m_id in b:s[m_id]=g[m_id]
   if b and"fetch_json"not in a.__dict__:
    k=b[:160];d=[k[i:i+40]for i in range(0,len(k),40)];f=await asyncio.gather(*(a.fetch_json(f"{GAMMA_URL}/markets?limit=50&"+"&".join(f"id={x}"for x in ch),timeout=4.5)for ch in d),return_exceptions=True)
    for y in f:
     if not isinstance(y,list):continue
     for w in y:
      if not isinstance(w,dict):continue
      p=str(w.get("id")or"").strip()
      if not p or p in("6707502","6707503"):continue
      v,_=is_objective_uma_market(w)
      if v:s[p]=w
      else:s.pop(p,None)
  for o in s.values():
   if isinstance(o,dict):
    if"_parent_event_id"not in o and isinstance(o.get("events"),list)and o["events"]:
     u=o["events"][0]
     if isinstance(u,dict)and(u.get("id")or u.get("slug")):o["_parent_event_id"]=str(u.get("id")or u.get("slug")).strip()
    for j in("events","chats","image","icon","twitterCardImage","clobRewards"):o.pop(j,None)
  a.uma_proposed_markets=s;a.last_uma_discovery_ts=now_ts
  if not a.single_scan and"fetch_json"not in a.__dict__:a._release_unused_heap_memory()
 async def scan_uma_resolution_bonds(b,opps_out,now_ts=None):
  _A=float(now_ts if now_ts is not None else time.time())
  if b.single_scan or not b.uma_proposed_markets or(_A-b.last_uma_discovery_ts)>=30.:await b.discover_uma_proposed_markets(_A)
  from src.polymarket_research.riskless_protocol_v2_expansion import augment_uma_proposed_from_universe_and_polygon as c;await c(b,_A,gamma_url=GAMMA_URL)
  if not b.uma_proposed_markets:return
  j=[];w=[];o=not(b.single_scan or("fetch_json"in b.__dict__))
  for mid,m in list(b.uma_proposed_markets.items()):
   _y=f"BOND1_{mid}"
   if _y in b.inflight_keys or(not o and _y in b.entered_keys):continue
   _b=b.uma_onchain_cache.get(mid);_x=float(m.get("bestBid")or.0);_w=float(m.get("bestAsk")or 1.);N=bool(.88<=_x<=.999 or.001<=_w<=.12 or.88<=_w<=.999);M=90. if N else 240.
   if _b is not None:
    _z=str(_b[1].get("reason")or"")
    if any(k in _z for k in("DISPUTER","TIE_50_50","QUESTION_FLAGS","PRIOR_DISPUTE","PREMATURE_PROPOSAL","MARKET_BEFORE_END_DATE")):M=3e2
   if _b is not None and(_A-_b[0])<M:
    ver=_b[1]
    if ver.get("verified"):
     A,_=verify_uma_against_nba_live(m,int(ver["win_index"]),b.live_nba_board)
     if A:j.append((mid,m,ver))
   else:u=(1e6 if(.9<=_x<=.9985 or.002<=_w<=.1 or.9<=_w<=.9985)else.0)+float(m.get("volume24hr")or.0);w.append((u,mid,m))
  if w:
   w.sort(key=lambda x:-x[0]);_i=asyncio.Semaphore(3)
   async def g(mid_u,m_u):
    async with _i:a=await asyncio.to_thread(verify_uma_onchain_proposal_sync,m_u,None,_A);return mid_u,m_u,a
   H=await asyncio.gather(*(g(mid_u,m_u)for _,mid_u,m_u in w[:32]))
   for mid_u,m_u,ver in H:
    b.uma_onchain_cache[mid_u]=(_A,ver)
    if not ver.get("verified"):continue
    A,_=verify_uma_against_nba_live(m_u,int(ver["win_index"]),b.live_nba_board)
    if A:j.append((mid_u,m_u,ver))
  j=[(mid,m,ver)for mid,m,ver in j if passes_uma_bond_dispute_guard(m,{**ver,"allow_pre_book_fast_season":True}if isinstance(ver,dict)else ver)]
  if not j:return
  S=[t for _,_,ver in j for t in(str(ver["win_token"]),str(ver["lose_token"]))];_h=await b.fetch_books_batch(S,timeout=3.5);z=BANKROLL_TICKETS["T1000"]["BOND1_UMA_RESOLUTION_CARRY"];from src.polymarket_research.riskless_protocol_v2_expansion import extract_gamma_parent_event_id as i
  def e(entry):
   _,_P,_O=entry;_N=_h.get(str(_O["win_token"]))or{};_M=_h.get(str(_O["lose_token"]))or{};_L,_K=extract_best_bid(_N.get("bids")or[]);_J,_=extract_best_bid(_M.get("bids")or[]);_I,_H=b._best_ask_sz(_N);_G=max(9e2,float(_O.get("rem_challenge_sec")or 3600.));_F=(_I*_H)if _I<1. else.0;_E=max(.0,float(_P.get("volume24hr")or.0));_C=max(_E,float(_P.get("volumeNum")or _P.get("volume")or.0));x=any(k in _P for k in("volume24hr","volumeNum","volume","liquidityNum","acceptingOrders"))
   if _F<5. and x and _C<25.:return(0,0,-2.)
   _D=int(.95<=_I<=.9975 and _F>=5. and _J<=.008 and _L>=.94);a=int(_F>=5. or _E>=5e2 or(_K>=1e2 and(not x or _C>=1e2)))
   if.94<=_L<=.998 and _J<=.008:_B=(1.-_L)if _F>=5. else min(.012,1.-_L);t=1.+min(1.5,.35*math.log10(1.+max(_E,_C*.5)/250.));m=(_B/_G)*t*(1. if _F>=5. else(.55 if _E>=5e2 else.2))
   else:m=-1.
   return _D,a,m
  j.sort(key=e,reverse=True)
  for mid,m,ver in j:
   _v,_u=str(ver["win_token"]),str(ver["lose_token"]);X,_t=_h.get(_v),_h.get(_u)
   if not X or not _t:continue
   _g=max(.0,float(ver.get("eff_liveness_sec")or 7200.)-float(ver.get("rem_challenge_sec")or 7200.));_f,_=extract_best_bid(X.get("bids")or[]);_a,_=extract_best_bid(_t.get("bids")or[]);Z,_=b._best_ask_sz(_t);G=bool(_f>=.98 and _a<=.002 and(Z>=.5 or Z<=.01))
   if not passes_uma_bond_dispute_guard(m,{**ver,"dual_book_consensus_confirmed":G}):continue
   Y=classify_market_rule_dispute_risk(m);R=i(m);p=any(k in m for k in("volume24hr","volumeNum","volume","liquidityNum","acceptingOrders"));F=max(.0,float(m.get("volumeNum")or m.get("volume")or.0),float(m.get("volume24hr")or.0));Q=max(.0,float(m.get("volume24hr")if m.get("volume24hr")is not None else F));X={**X,"_s2_meta":{"proposal_age_sec":round(float(ver.get("proposal_age_sec")if ver.get("proposal_age_sec")is not None else _g),1),"dispute_risk":bool(Y["dispute_risk"]),"reasons":list(Y["reasons"]),"question":str(m.get("question")or"")[:120],"dual_book_consensus_confirmed":G,**({"volume24hr":round(Q,2),"total_volume_usd":round(F,2)}if p else{}),**({"event_id":R}if R else{})}}
   if _a>.008 or _f<.94 or(Z<.5 and Z>.025):continue
   y=sum(float(a.get("price",.0)or.0)*float(a.get("size",.0)or.0)for a in(X.get("asks")or[])if isinstance(a,dict)and float(a.get("size",.0)or.0)>.0);n=bool(p and y<5. and F<25.);_o=walk_l2_book_asks_depth_capped(X.get("asks")or[],z,5. if o else BANKROLL_TICKETS["T100"]["BOND1_UMA_RESOLUTION_CARRY"],fee_rate=float(ver["fee_rate"]),min_l1_usd=5. if o else 15.,max_ask_px=.9976 if o else.9956,fee_exponent=float(ver["fee_exponent"]));_r=float(_o["eff_px"])if _o.get("filled")else None;b._record_market_telemetry(key=f"BOND1_SNAP_{mid}",min_interval_sec=60.,now_ts=_A,sig=(_r,_f,_a,ver["oo_state"]),payload={"type":"UMA_BOND_PROPOSAL_SNAP","market_id":mid,"question":str(m.get("question")or"")[:90],"domain":ver["domain"],"win_outcome":ver["win_outcome_name"],"oo_state":ver["oo_state"],"rem_challenge_sec":ver["rem_challenge_sec"],"win_ask_eff":_r,"win_bid":_f,"lose_bid":_a});_q=str(m.get("question")or f"Market {mid}");P=max(_A+9e2,float(ver["expiration_ts"])+6e2);L={"market_id":mid,"condition_id":str(m.get("conditionId")or""),"opp_token_id":_u,"fee_exponent":ver["fee_exponent"],"oo_state":ver["oo_state"],"proposer":ver["proposer"],"win_outcome_name":ver["win_outcome_name"],"expiration_ts":ver["expiration_ts"],"rem_challenge_sec":ver["rem_challenge_sec"],"domain":ver["domain"]};_e=f"BOND1_{mid}";s=_e not in b.entered_keys and _e not in b.inflight_keys;O=P-_A;v=(float(ver["rem_challenge_sec"])if ver.get("rem_challenge_sec")is not None else max(.0,O-6e2));E=.9975 if(o and v<=3600.)else(.9965 if(o and v<=7200.)else.9955);D=.998 if(o and v<=3600.)else(.9975 if(o and v<=7200.)else.995);K=round(1.-D,4);_n=float(ver["fee_rate"]);_m=float(ver["fee_exponent"]);J=round(.2*_n*((_f*(1.-_f))**_m),5)if(_n>.0 and.0<_f<1.)else.0;d=False
   if o and 180.<=float(ver.get("rem_challenge_sec")or.0)<=1500.:
    from src.polymarket_research.riskless_protocol_v2_expansion import score_uma_ready1_liveness_priority as f;C=.9975 if _n<=1e-9 else min(.995,E);_d=f(ask_price=_r if _r is not None else min(C,_f),remaining_liveness_sec=float(ver["rem_challenge_sec"]),disputed=False,proposal_bond_posted=True)
    if _d is not None:
     if s:opps_out.append({"sleeve":"UMA_READY1_LIVENESS_PRIORITY","market":f"[UMA_READY1:{ver['domain']}] {_q[:56]} ({ver['rem_challenge_sec']/60:.0f}m rem)","ask_vwap":_d["ask_px"],"p_model":1.,"net_edge":_d["net_edge_per_share"],"l1_usd":_o["l1_usd"]if _o.get("filled")else 25.,"close_ts":P})
     if _o.get("filled")and _r is not None and.95<=_r<=C and _a<=.008:d=bool(b.emit_live_single_leg_lock_candidate(sleeve_source="UMA_READY1_LIVENESS_PRIORITY",asset=str(ver["domain"]),dedupe_key=f"UMA_READY1_{mid}",pair_dedupe_key=_e,token_id=_v,opp_token_id=_u,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(ver["win_label"]),display_label=f"UMA_READY1 {ver['domain']} {ver['win_outcome_name']}",bk_win=X,bk_opp=_t,fee_rate=_n,fee_exponent=_m,neg_risk=bool(m.get("negRisk")),close_ts=P,now_ts=_A,max_lock_eff_px=C,max_opp_bid=.008,hold_to_maturity=True,p_model=1.,event_id=R))
   l=False;h=False;r=bool(_o.get("filled")and _r is not None and(.95<=_r<=E)and round(1.-_r,4)>=round(1.-E,4))
   if r:
    I=round(1.-_r,4)
    if s and _r<=.9955 and float(_o.get("spent_usd")or.0)>=19.5:opps_out.append({"sleeve":"BOND1_UMA_RESOLUTION_CARRY","market":f"[{ver['domain']}] {_q[:65]} -> {ver['win_outcome_name']} ({ver['rem_challenge_sec']/60:.0f}m rem)","ask_vwap":_r,"p_model":1.,"net_edge":I,"l1_usd":_o["l1_usd"],"close_ts":P})
    if not d:b.emit_live_single_leg_lock_candidate(sleeve_source="BOND1_UMA_RESOLUTION_CARRY",asset=str(ver["domain"]),dedupe_key=_e,token_id=_v,opp_token_id=_u,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(ver["win_label"]),display_label=f"{ver['domain']} {ver['win_outcome_name']}",bk_win=X,bk_opp=_t,fee_rate=_n,fee_exponent=_m,neg_risk=bool(m.get("negRisk")),close_ts=P,now_ts=_A,max_lock_eff_px=E,max_opp_bid=.008,hold_to_maturity=True,p_model=1.,event_id=R)
    if s and _r<=.9955 and float(_o.get("spent_usd")or.0)>=19.5:l=await b.open_shadow_position(sleeve="BOND1_UMA_RESOLUTION_CARRY",dedupe_key=_e,asset_or_city=str(ver["domain"]),title=f"{_q} [{ver['win_outcome_name']}]",side_label=str(ver["win_label"]),token_id=_v,fee_rate=_n,p_model=1.,close_ts=P,extra=L,tp_target_px=None,prefetched_book=X)
   if(not r and not l and not n and.94<=_f<=D and _a<=.008 and O>120.):
    W=dict(X);W["_s2_meta"]={**(X.get("_s2_meta")or{}),"leg_a_fee_rate":_n,"leg_a_fee_exponent":_m};h=bool(b.emit_live_single_leg_maker_lock_candidate(sleeve_source="BOND1_UMA_RESOLUTION_CARRY",asset=str(ver["domain"]),dedupe_key=f"BOND1_MKR_{mid}",pair_dedupe_key=_e,token_id=_v,opp_token_id=_u,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(ver["win_label"]),display_label=f"{ver['domain']} {ver['win_outcome_name']}",bk_win=W,bk_opp=_t,neg_risk=bool(m.get("negRisk")),close_ts=P,now_ts=_A,min_resting_bid=.94,max_resting_bid=D,min_maker_edge=K,max_opp_bid=.008,hold_to_maturity=True,p_model=1.,maker_rebate_ps=J,event_id=R))
    if s:
     B=await b.post_shadow_maker_entry(sleeve="BOND1_UMA_RESOLUTION_CARRY",dedupe_key=_e,asset=str(ver["domain"]),title=f"{_q} [{ver['win_outcome_name']}]",side_label=str(ver["win_label"]),token_id=_v,p_model=1.,close_ts=P,extra=L,prefetched_book=X)
     if B:opps_out.append({"sleeve":"BOND1_UMA_RESOLUTION_CARRY","market":f"[MAKER:{ver['domain']}] {_q[:58]} -> {ver['win_outcome_name']}","ask_vwap":_f,"p_model":1.,"net_edge":round(1.-_f,4),"l1_usd":extract_best_bid(X.get("bids")or[])[1],"close_ts":P})
   _p=f"BOND2_{mid}";q=_p not in b.entered_keys and _p not in b.inflight_keys
   if(not(not o and _p in b.entered_keys)and _p not in b.inflight_keys and float(ver.get("proposal_age_sec")or.0)>=3600. and 180.<=float(ver.get("rem_challenge_sec")or.0)<=3300. and _a<=.006 and _f>=.95):
    V=b.__dict__.setdefault("uma_bond2_cache",{})
    if len(V)>512:V.clear()
    U=id(verify_bond2_moov2_final_hour_sync);_l=V.get(mid)
    if _l is not None and _l[1]==U and(_A-float(_l[0]))<60.:T=_l[2]
    else:T=await asyncio.to_thread(verify_bond2_moov2_final_hour_sync,m,None,_A);V[mid]=(_A,U,T)
    if T.get("verified"):
     _c=.9975 if o else.9962;_s=walk_l2_book_asks_depth_capped(X.get("asks")or[],BANKROLL_TICKETS["T1000"]["BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"],BANKROLL_TICKETS["T100"]["BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"],fee_rate=float(T["fee_rate"]),min_l1_usd=10. if o else 15.,max_ask_px=round(_c+1e-4,4),fee_exponent=float(T["fee_exponent"]))
     if _s.get("filled")and.95<=float(_s["eff_px"])<=_c:
      _k=float(_s["eff_px"]);_j=round(1.-_k,4)
      if _j>=(.0025 if o else.0038):
       if q:opps_out.append({"sleeve":"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","market":f"[MOOv2_WL:{T['domain']}] {_q[:60]} -> {T['win_outcome_name']} ({T['rem_challenge_sec']/60:.0f}m rem)","ask_vwap":_k,"p_model":1.,"net_edge":_j,"l1_usd":_s["l1_usd"],"close_ts":P})
       b.emit_live_single_leg_lock_candidate(sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",asset=str(T["domain"]),dedupe_key=_p,token_id=_v,opp_token_id=_u,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(T["win_label"]),display_label=f"MOOv2_WL {T['domain']} {T['win_outcome_name']}",bk_win=X,bk_opp=_t,fee_rate=float(T["fee_rate"]),fee_exponent=float(T["fee_exponent"]),neg_risk=bool(m.get("negRisk")),close_ts=P,now_ts=_A,max_lock_eff_px=_c,max_opp_bid=.006,hold_to_maturity=True,p_model=1.)
       if q:await b.open_shadow_position(sleeve="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",dedupe_key=_p,asset_or_city=str(T["domain"]),title=f"{_q} [MOOv2 Whitelisted {T['win_outcome_name']}]",side_label=str(T["win_label"]),token_id=_v,fee_rate=float(T["fee_rate"]),p_model=1.,close_ts=P,extra={**L,"proposer_whitelisted":True,"oo_address":T["oo_address"]},tp_target_px=None,prefetched_book=X)
      elif o and not h and not n:b.emit_live_single_leg_maker_lock_candidate(sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",asset=str(T["domain"]),dedupe_key=f"{_p}_MKR",pair_dedupe_key=_p,token_id=_v,opp_token_id=_u,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(T["win_label"]),display_label=f"MOOv2_WL Maker {T['domain']} {T['win_outcome_name']}",bk_win=X,bk_opp=_t,neg_risk=bool(m.get("negRisk")),close_ts=P,now_ts=_A,min_resting_bid=.95,max_resting_bid=.998,min_maker_edge=.002,max_opp_bid=.006,p_model=1.,event_id=R)
     elif o and not h and not n:b.emit_live_single_leg_maker_lock_candidate(sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",asset=str(T["domain"]),dedupe_key=f"{_p}_MKR",pair_dedupe_key=_p,token_id=_v,opp_token_id=_u,market_id=mid,condition_id=str(m.get("conditionId")or""),side_label=str(T["win_label"]),display_label=f"MOOv2_WL Maker {T['domain']} {T['win_outcome_name']}",bk_win=X,bk_opp=_t,neg_risk=bool(m.get("negRisk")),close_ts=P,now_ts=_A,min_resting_bid=.95,max_resting_bid=.998,min_maker_edge=.002,max_opp_bid=.006,p_model=1.,event_id=R)
 async def scan_nba_endgame_locks(a,opps_out,now_ts=None):
  N=float(now_ts if now_ts is not None else time.time())
  if not a.nba_games:return
  i=a.has_live_nba_window(N);C=any(getattr(g,"state","")=="in"and((int(getattr(g,"period",0)or 0)>=4 and float(getattr(g,"clock_sec",9999)or 9999)<=125.)or(int(getattr(g,"period",0)or 0)==2 and float(getattr(g,"clock_sec",9999)or 9999)<=15.)or bool(getattr(g,"is_halftime",False)))for g in(a.live_nba_board or[]))
  try:
   from src.polymarket_research.polymarket_direct_feeds import compute_adaptive_sports_poll_interval_sec as b;e=float(b(is_endgame_or_halftime=C,has_live_games=i))
   if not i:e=max(60.,e)
  except Exception:e=.75 if C else(5.5 if i else 120.)
  if a.single_scan or not a.live_nba_board or(N-a.last_espn_board_ts)>=e:
   m=await asyncio.to_thread(fetch_espn_nba_scoreboard_sync)
   if not a.single_scan and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_official_league_direct_feeds",True)):
    try:from src.polymarket_research.polymarket_direct_feeds import(fetch_nba_cdn_scoreboard_sync as d,reconcile_nba_dual_source_boards as c);m=c(m,await asyncio.to_thread(d))
    except Exception:pass
   if m:a.live_nba_board=m;a.last_espn_board_ts=N
  if not a.live_nba_board:return
  p=[]
  for j in list(a.nba_games.values()):
   B=match_nba_live_game(j,a.live_nba_board)
   if B is None:continue
   A,M,L=B
   if A.state in("in","post"):a._record_market_telemetry(key=f"NBA_LIVE_{j.event_id}",min_interval_sec=30.,now_ts=N,sig=(A.state,A.period,int(A.clock_sec//10),M,L),payload={"type":"NBA_LIVE_SCORE_SNAP","event_id":j.event_id,"game":j.title,"state":A.state,"completed":A.completed,"period":A.period,"clock_sec":round(A.clock_sec,1),"score_a":M,"score_b":L,"source":A.source})
   for c_lk in evaluate_nba_endgame_locks(j,A,M,L):
    K=c_lk["leg"];H=f"SP2_{j.event_id}_{K.market_id}_{K.token_id[-8:]}"
    if H not in a.entered_keys and H not in a.inflight_keys:p.append((j,c_lk))
  if not p:await a._scan_sp4_live_nba_stat_locks(opps_out,N);return
  s=[t for _,c_lk in p for t in(c_lk["leg"].token_id,c_lk["leg"].opp_token_id)];z=await a.fetch_books_batch(s,timeout=3.);y=BANKROLL_TICKETS["T1000"]["SP2_NBA_ENDGAME_LOCK"]
  for j,c_lk in p:
   K=c_lk["leg"];G=z.get(K.token_id);F=z.get(K.opp_token_id)
   if not G or not F:continue
   x,_=extract_best_bid(F.get("bids")or[])
   if x>.18:continue
   k,h=extract_best_bid(G.get("bids")or[]);E=float(getattr(K,"fee_rate",.0)or.0);D=float(getattr(K,"fee_exponent",1.)or 1.);I=walk_l2_book_asks_depth_capped(G.get("asks")or[],y,BANKROLL_TICKETS["T100"]["SP2_NBA_ENDGAME_LOCK"],fee_rate=E,min_l1_usd=18.,max_ask_px=.9861,fee_exponent=D);J=float(c_lk["p_lock"]);o=max(N+6e2,float(j.settle_est_ts));r=f"SP2_{j.event_id}_{K.market_id}_{K.token_id[-8:]}";n={"event_id":j.event_id,"market_id":K.market_id,"condition_id":K.condition_id,"opp_token_id":K.opp_token_id,"mode":c_lk["mode"],"score_str":c_lk["score_str"],"cushion_pts":c_lk["cushion_pts"],"clock_sec":c_lk["clock_sec"],"period":c_lk["period"],"fee_exponent":D};f=False;w=bool(getattr(K,"neg_risk",False))
   if I.get("filled"):
    v=float(I["eff_px"]);u=round(J-v,4)
    if x<=(1.-v)+.025 and(.78<=v<=.986)and u>=.012:
     if J>=.998 and x<=.03:a.emit_live_single_leg_lock_candidate(sleeve_source="SP2_NBA_ENDGAME_LOCK",asset="NBA",dedupe_key=r,token_id=K.token_id,opp_token_id=K.opp_token_id,market_id=K.market_id,condition_id=K.condition_id,side_label=K.side_label,display_label=f"NBA {c_lk['score_str']} {K.display_label}",bk_win=G,bk_opp=F,fee_rate=E,fee_exponent=D,neg_risk=w,close_ts=o,now_ts=N,max_lock_eff_px=.988,max_opp_bid=.03,hold_to_maturity=True,p_model=J,event_id=str(j.event_id))
     opps_out.append({"sleeve":"SP2_NBA_ENDGAME_LOCK","market":f"NBA [{c_lk['mode']}] {c_lk['score_str']} -> {K.display_label}","ask_vwap":v,"p_model":J,"net_edge":u,"l1_usd":I["l1_usd"],"close_ts":o});f=await a.open_shadow_position(sleeve="SP2_NBA_ENDGAME_LOCK",dedupe_key=r,asset_or_city="NBA",title=f"{j.title} [{K.display_label} | {c_lk['mode']}]",side_label=K.side_label,token_id=K.token_id,fee_rate=E,p_model=J,close_ts=o,extra=n,tp_target_px=None,prefetched_book=G)
   if(not f and.72<=k<=.985 and x<=(1.-k)+.025 and(J-k)>=.012):
    if J>=.999 and.94<=k<=.992 and x<=.025:q=round(.2*E*((k*(1.-k))**D),5)if E>.0 else.0;a.emit_live_single_leg_maker_lock_candidate(sleeve_source="SP2_NBA_ENDGAME_LOCK",asset="NBA",dedupe_key=f"{r}_MKR",pair_dedupe_key=r,token_id=K.token_id,opp_token_id=K.opp_token_id,market_id=K.market_id,condition_id=K.condition_id,side_label=K.side_label,display_label=f"NBA {c_lk['score_str']} {K.display_label}",bk_win={**G,"_s2_meta":{"leg_a_fee_rate":E,"leg_a_fee_exponent":D}},bk_opp=F,neg_risk=w,close_ts=o,now_ts=N,min_resting_bid=.94,max_resting_bid=.992,min_maker_edge=.008,max_opp_bid=.025,hold_to_maturity=True,p_model=J,maker_rebate_ps=q,event_id=str(j.event_id))
    l=await a.post_shadow_maker_entry(sleeve="SP2_NBA_ENDGAME_LOCK",dedupe_key=r,asset="NBA",title=f"{j.title} [{K.display_label} | {c_lk['mode']}]",side_label=K.side_label,token_id=K.token_id,p_model=J,close_ts=o,extra=n,prefetched_book=G,ttl_override_sec=45.)
    if l:opps_out.append({"sleeve":"SP2_NBA_ENDGAME_LOCK","market":f"[MAKER] NBA [{c_lk['mode']}] {c_lk['score_str']} -> {K.display_label}","ask_vwap":k,"p_model":J,"net_edge":round(J-k,4),"l1_usd":h,"close_ts":o})
  await a._scan_sp4_live_nba_stat_locks(opps_out,N)
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
 async def scan_protocol_v2_expansion_opportunities(self,opps_out,now_ts=None):from src.polymarket_research.riskless_protocol_v2_expansion import run_protocol_v2_daemon_scan as a;await a(self,opps_out,now_ts=now_ts)
 async def scan_v6_riskless_expansion_opportunities(self,opps_out,now_ts=None):from src.polymarket_research.riskless_expansion_v6_engines import run_v6_expansion_alpha124_scan as a;await a(self,opps_out,now_ts=now_ts)
 async def _run_gatling_fast_gun_loop(a):
  b=.0;c=.0
  while True:
   try:
    j=time.time();i=math.ceil(j/3e2)*3e2-j
    if i<=65. and(j-a.last_usd_sample_ts)>=.95:a.record_usd_spot_samples(j)
    f=3.6<=i<=39.;h=.08 if f else 1.5
    if(3.6<=i<=92.)and(j-c)>=h:c=j;e=[];await a.scan_exact_twap_locks(e,now_ts=j)
    if a.is_in_same_oracle_overlap_window(j)and(j-b)>=.3:
     g=a.__dict__.setdefault("_d1_fast_scan_lock",asyncio.Lock())
     if not g.locked():
      b=j
      async with g:d=[];await a.scan_same_oracle_dominance_boxes(d,now_ts=j)
    await asyncio.sleep(.06 if f else.2)
   except asyncio.CancelledError:break
   except Exception:await asyncio.sleep(.5)
 async def _run_bg_nba_endgame(a):
  try:b=[];await a.scan_nba_endgame_locks(b);a.cached_nba_endgame_opps=b
  except Exception as c:logger.warning(f"Background NBA endgame scan notice: {c}")
 async def _run_bg_tradfi_sports(a):
  d=[]
  try:await a.scan_tradfi_and_sports_markets(d)
  except Exception as e:logger.warning(f"Background TradFi/Sports scan notice: {e}")
  try:await a.scan_protocol_v2_expansion_opportunities(d)
  except Exception as c:logger.warning(f"Background Protocol V2 scan notice: {c}")
  try:await a.scan_v6_riskless_expansion_opportunities(d)
  except Exception as b:logger.warning(f"Background v6 Riskless Expansion scan notice: {b}")
  a.cached_tradfi_sports_opps=d
 async def _run_bg_uma_bonds(b):
  c=[]
  try:await b.scan_uma_resolution_bonds(c);b.cached_uma_bond_opps=c
  except Exception as a:logger.warning(f"Background UMA bond scan notice: {a}")
 async def run_forever(a):
  logger.info("Starting Polymarket Alpha-124 Unified Shadow Daemon (Gatling High-Vol Machine Gun: S2 Live TWAP Lock + 9-Asset D1 + Protocol V2 Expansion)...")
  try:
   if not a.single_scan and(a._bg_clob_ws_task is None or a._bg_clob_ws_task.done()):a._bg_clob_ws_task=asyncio.create_task(a._run_clob_d1_ws_loop())
   if not a.single_scan and a._chainlink_ws is not None and(a._bg_chainlink_ws_task is None or a._bg_chainlink_ws_task.done()):a._bg_chainlink_ws_task=asyncio.create_task(a._chainlink_ws.run_forever())
   if not a.single_scan and PythHermesStream is not None:
    try:
     if getattr(a,"_pyth_hermes_stream",None)is None:a._pyth_hermes_stream=PythHermesStream()
     R=getattr(a,"_bg_pyth_hermes_task",None)
     if R is None or R.done():a._bg_pyth_hermes_task=asyncio.create_task(a._pyth_hermes_stream.run_forever())
    except Exception:pass
   if not a.single_scan and PolygonScopedLogsWs is not None:
    try:
     if getattr(a,"_polygon_logs_ws",None)is None:
      a._polygon_logs_ws=PolygonScopedLogsWs()
      try:from src.polymarket_research.uma_nba_endgame_engine import set_shared_polygon_logs_ws as f;f(a._polygon_logs_ws)
      except Exception:pass
      try:from src.polymarket_research.riskless_protocol_v2_expansion import set_shared_protocol_v2_polygon_logs_ws as d;d(a._polygon_logs_ws)
      except Exception:pass
     Q=getattr(a,"_bg_polygon_logs_ws_task",None)
     if Q is None or Q.done():a._bg_polygon_logs_ws_task=asyncio.create_task(a._polygon_logs_ws.run_forever())
    except Exception:pass
   n=getattr(a,"_bg_gatling_fast_task",None)
   if not a.single_scan and(n is None or n.done()):a._bg_gatling_fast_task=asyncio.create_task(a._run_gatling_fast_gun_loop())
   G=getattr(a,"_bg_state_hb_task",None)
   if not a.single_scan and(G is None or G.done()):a._bg_state_hb_task=asyncio.create_task(a._run_bg_state_heartbeat())
   while True:
    U=time.time();a.__dict__["_last_main_loop_tick_mono"]=time.monotonic();a.cycle_count+=1
    if not a.single_scan and(U-float(getattr(a,"_last_live_eq_poll_ts",.0)or.0))>=30.:
     a._last_live_eq_poll_ts=U
     try:
      F=LIVE_POLYMARKET_DIR/"live_harvester_state.json"
      if F.exists()and(U-F.stat().st_mtime)<=6e2:
       P=json.loads(F.read_text(encoding="utf-8"));O=a._extract_reconciled_live_equity_usd(P)
       if O>.0:a.live_account_equity_usd=O
     except Exception:pass
    await a.update_crypto_spots()
    if not a.weather_events or a.single_scan:await a.discover_all_markets()
    elif(U-a.last_discovery_ts)>=3e2 and(a._bg_discovery_task is None or a._bg_discovery_task.done()):a.last_discovery_ts=U;a._bg_discovery_task=asyncio.create_task(a._run_bg_discovery())
    if not a.single_scan and(U-float(a.__dict__.get("_last_mem_evict_ts")or.0))>=60.:a.__dict__["_last_mem_evict_ts"]=U;a._evict_stale_caches(now_ts=U)
    p=[]if a.riskless_bridge_only else a.poll_fresh_shock_triggers(now_ts=U)
    if p:w=[];await a.handle_shock_triggers(p,w,now_ts=U);a.cached_shock_opps=w
    h=[];x=[];E=[];J=[];await a.scan_same_oracle_dominance_boxes(h);await a.scan_exact_twap_locks(x)
    if not a.riskless_bridge_only:await a.scan_s5m_chainlink_sniper(E)
    if not a.riskless_bridge_only or a.pending_preopen_straddles:await a.scan_and_manage_preopen_maker_straddles(J)
    if a.single_scan:D=[];await a.scan_multistrike_markets(D);await a.scan_daily_updown_locks(D);await a.scan_barrier_markets(D);a.cached_mid_opps=D;L=[];await a.scan_weather_markets(L);a.cached_weather_opps=L;I=[];await a.scan_tradfi_and_sports_markets(I);await a.scan_protocol_v2_expansion_opportunities(I);await a.scan_v6_riskless_expansion_opportunities(I);a.cached_tradfi_sports_opps=I;C=[];await a.scan_nba_endgame_locks(C);a.cached_nba_endgame_opps=C
    else:
     s=6. if a.has_live_nba_window(U)else 120.
     if(U-a.last_nba_endgame_scan_ts)>=s and(a._bg_nba_task is None or a._bg_nba_task.done()):a.last_nba_endgame_scan_ts=U;a._bg_nba_task=asyncio.create_task(a._run_bg_nba_endgame())
     if(U-a.last_crypto_mid_scan_ts)>=18. and(a._bg_mid_task is None or a._bg_mid_task.done()):a.last_crypto_mid_scan_ts=U;a._bg_mid_task=asyncio.create_task(a._run_bg_mid_crypto())
     a.__dict__["_uma_bg_loop_active"]=True
     if(U-float(getattr(a,"last_uma_bond_scan_ts",.0)or.0))>=18. and(a._bg_uma_task is None or a._bg_uma_task.done()):a.last_uma_bond_scan_ts=U;a._bg_uma_task=asyncio.create_task(a._run_bg_uma_bonds())
     l=8. if(a.has_live_sports_window(U)or a.pending_zero_fee_maker_anchors)else 20.
     if(U-a.last_tradfi_sports_scan_ts)>=l and(a._bg_tradfi_task is None or a._bg_tradfi_task.done()):a.last_tradfi_sports_scan_ts=U;a._bg_tradfi_task=asyncio.create_task(a._run_bg_tradfi_sports())
     v=int((U//60)%60);g=(v>=49 or v<=6 or 19<=v<=35);i=12. if(g and a.weather_events)else 60.
     if(U-a.last_weather_scan_ts)>=i and(a._bg_weather_task is None or a._bg_weather_task.done()):a.last_weather_scan_ts=U;a._bg_weather_task=asyncio.create_task(a._run_bg_weather())
    T=(x+h+E+J+a.cached_shock_opps+a.cached_mid_opps+a.cached_nba_endgame_opps+a.cached_tradfi_sports_opps+a.cached_uma_bond_opps+a.cached_weather_opps);await a.manage_pending_maker_orders();await a.manage_pending_zero_fee_maker_anchors();await a.manage_open_positions();await a.write_state_files_async(T);logger.info(f"[Cycle {a.cycle_count}] BTC=${a.spots.get('BTC',0):,.1f} ETH=${a.spots.get('ETH',0):,.1f} | Monitored(W={len(a.weather_events)}, B={len(a.barrier_rungs)}, M={len(a.strike_ladders)}, NR={len(a.negrisk_ladders)}, PythH={len(a.pyth_barrier_rungs)}, PythC={len(a.pyth_close_ladders)}, NBA={len(a.nba_games)}/{len(a.live_nba_board)}live(SP4={len(a.nba_prop_slates)},SP4+={len(a.nba_subperiod_slates)},EM={len(a.lp1_nba_em_bundles)}), SP3={len(a.multi_sport_games)}(NFLEM={len(a.lp1_nfl_em_bundles)}), SOC1={len(a.soccer_trees)}, TEN1={len(a.tennis_specs)}, API1={len(a.esports_bo3_specs)}, BOP={len(a.lp1_bop_legs)//2}, LP2={len(a.lp2_implication_groups)}, CAL1={len(a.cal1_ladders)}, UMA={len(a.uma_proposed_markets)}, NR0={len(a.negrisk_zero_slates)}, NRC={len(a.negrisk_convert_slates)}, TW={len(a.counting_slates)}, FOMC={len(a.fomc_truth_legs)//2}, OS={len(a.oil_senate_truth_legs)//2}, D2={len(a.hourly_12pm_markets)}, U1={len(a.daily_updown_markets)}, D={len(a.dominance_pairs)}, D4h={len(a.dominance_4h_pairs)}, S5m={len(a.s5m_candles)}, P1={len(a.preopen_15m_candles)}, S2={len(a.twap_candles)}) | MakerPend={len(a.pending_maker_orders)} ZFAncPend={len(a.pending_zero_fee_maker_anchors)} PreOpenPend={len(a.pending_preopen_straddles)} OpenPos={len(a.open_positions)} ClosedPos={len(a.closed_positions)} | TopOpps={len(a.top_opportunities)}")
    if a.single_scan:break
    H=time.time();from src.polymarket_research.riskless_protocol_v2_expansion import compute_min_4h_boundary_rem_sec as e;u=e(H);k=not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK")
    if k and a.is_in_exact_twap_lock_window(H):b=3.
    elif a.is_in_same_oracle_overlap_window(H):b=3.5
    elif a.pending_zero_fee_maker_anchors:b=4.
    elif 8.<=u<=905. or a.pending_preopen_straddles or a.has_live_sports_window(H):b=6.
    else:b=12.
    B=U+max(2.,b);c=U
    while True:
     N=time.time()
     if N>=B:break
     o=a._ws_d1_wakeup.is_set()
     if o:a._ws_d1_wakeup.clear()
     j=a._ws_nr_wakeup.is_set()
     if j:a._ws_nr_wakeup.clear()
     t=.12 if o else.5
     if a.is_in_same_oracle_overlap_window(N)and(N-c)>=t:
      c=N;r=[];await a.scan_same_oracle_dominance_boxes(r,now_ts=N)
      if r:h=r
      if a.pending_zero_fee_maker_anchors:await a.manage_pending_zero_fee_maker_anchors(now_ts=N)
     elif(a.pending_maker_anchors or a.pending_zero_fee_maker_anchors)and(N-c)>=.5:
      c=N
      if a.pending_maker_anchors:await a.manage_pending_maker_anchors(now_ts=N)
      if a.pending_zero_fee_maker_anchors:await a.manage_pending_zero_fee_maker_anchors(now_ts=N)
     if j and(N-getattr(a,"_last_fast_nr_subscan",.0))>=.25:a._last_fast_nr_subscan=N;await a._scan_ws_reactive_negrisk_arbs(N)
     A=math.ceil(N/3e2)*3e2-N
     if k and A<=65. and(N-a.last_usd_sample_ts)>=1.:a.record_usd_spot_samples(N)
     z=[]if a.riskless_bridge_only else a.poll_fresh_shock_triggers(now_ts=N)
     if z:
      m=set(a.pending_maker_orders);q=len(a.open_positions);K=[];await a.handle_shock_triggers(z,K,now_ts=N)
      if K:a.cached_shock_opps=K
      if K or set(a.pending_maker_orders)!=m or len(a.open_positions)!=q:await a.write_state_files_async(x+h+E+J+a.cached_shock_opps+a.cached_mid_opps+a.cached_nba_endgame_opps+a.cached_tradfi_sports_opps+a.cached_weather_opps)
     if k and b>3. and a.is_in_exact_twap_lock_window(N):break
     y=min(.2,max(.03,B-time.time()))
     try:await asyncio.wait_for(a._ws_d1_wakeup.wait(),timeout=y)
     except asyncio.TimeoutError:pass
  finally:
   for S in(getattr(a,"_bg_state_hb_task",None),getattr(a,"_bg_gatling_fast_task",None),a._bg_chainlink_ws_task,a._bg_clob_ws_task,a._bg_discovery_task,a._bg_mid_task,a._bg_tradfi_task,a._bg_weather_task,a._bg_nba_task):
    if S is not None and not S.done():
     S.cancel()
     try:await S
     except BaseException:pass
   if a.session and not a.session.closed:await a.session.close()
   M=a.__dict__.pop("_state_io_executor",None)
   if M is not None:
    try:M.shutdown(wait=True)
    except Exception:pass
def main():
 _attach_daemon_log_file_handler();b=argparse.ArgumentParser(description="Polymarket Alpha-124 Shadow Daemon");b.add_argument("--single-scan",action="store_true",help="Run one full scan cycle and exit");b.add_argument("--riskless-bridge-only",action="store_true",help="Skip quarantined directional shock/sniper scans & disk telemetry");c=b.parse_args()
 if os.name!="nt":
  try:import uvloop;uvloop.install()
  except Exception:pass
 a=Alpha124ShadowDaemon(single_scan=c.single_scan,riskless_bridge_only=c.riskless_bridge_only);asyncio.run(a.run_forever())
if __name__=="__main__":main()
# ======================================================================================
# [17/20] MODULE: scripts/backtest_alpha_124.py
# PURPOSE: Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124
# ======================================================================================

import concurrent.futures;import json;import math;import os;import sys;import time;import urllib.request;from collections import defaultdict;from datetime import date,datetime,timedelta,timezone;from pathlib import Path;from typing import Any,Dict,List,Optional,Tuple;from zoneinfo import ZoneInfo;PROJECT_ROOT=Path(__file__).resolve().parent.parent
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
 print("[1/3] Fetching resolved October 2026 Daily Weather markets across 16 global cities...",flush=True);U=[]
 for Q in WEATHER_SERIES_SAMPLE:
  _a=http_get_json(f"{GAMMA_URL}/events?series_slug={Q}&closed=true&order=endDate&ascending=false&limit=20")or[]
  for ev in _a:
   sp=parse_weather_event(ev,allow_historical_same_station=True,series_slug_hint=Q)
   if sp is not None and date(2026,10,4)<=sp.obs_date<=date(2026,10,25):
    if any(b.outcome_yes_resolved==1 for b in sp.buckets):U.append(sp)
 print(f"      Parsed {len(U)} resolved METAR-governed city-days. Fetching NWP + METAR + CLOB series...",flush=True);L=defaultdict(list)
 for sp in U:L[sp.icao].append(sp)
 H={}
 for Z,J in L.items():
  T=min(s.obs_date for s in J)-timedelta(days=1);S=max(s.obs_date for s in J)+timedelta(days=1);s0=J[0]
  try:H[Z]=fetch_historical_nwp_hourly_sync(s0.lat,s0.lon,T,S)
  except Exception:H[Z]={}
 def c(sp):
  t=fetch_metar_observations_sync(sp.icao,sp.obs_date,sp.tz_name);s={}
  for b in sp.buckets:s[b.market_id]=fetch_clob_history(b.yes_token,fidelity=15)
  return sp,t,s
 K=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=24)as Y:
  for A in Y.map(c,U):
   if A[1]:K.append(A)
 print(f"      Loaded {len(K)} complete Weather city-day bundles with raw METAR + CLOB history.",flush=True);h=1.15;i=999.;p=[b for b in K if b[0].obs_date<=date(2026,10,16)]
 for I in(.85,1.05,1.25,1.45):
  m=.0;o=0
  for sp,metars,_ in p:
   from src.polymarket_research.riskless_protocol_v2_expansion import safe_zoneinfo as a;X=a(sp.tz_name);z=datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,11,0,tzinfo=X);k=z.astimezone(timezone.utc);_b=compute_weather_probabilities(sp,k,metars,H.get(sp.icao,{}),forecast_sigma_base_c=I)
   for B,b in enumerate(sp.buckets):y=1. if b.outcome_yes_resolved==1 else.0;m+=(_b["probs"][B]-y)**2;o+=1
  if o>0 and(m/o)<i:i=m/o;h=I
 print(f"      [TRAIN Calibration] Optimal Weather NWP kernel sigma={h:.2f}°C (Brier={i:.4f}).",flush=True);G=[];F=[];E=1e2;D=50.;j=.01
 for sp,metars,clob_map in sorted(K,key=lambda x:x[0].obs_date):
  from src.polymarket_research.riskless_protocol_v2_expansion import safe_zoneinfo as a;X=a(sp.tz_name);P=H.get(sp.icao,{});R="TRAIN"if sp.obs_date<=date(2026,10,16)else"TEST"
  def d(mkt_id,ts):
   t=clob_map.get(mkt_id)or[];b=None
   for s,x in t:
    if s<=ts:
     if ts-s<=7200:b=x
    else:break
   return b
  g=False
  for W,V in((9,0),(11,30),(13,30)):
   if g:break
   k=datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,W,V,tzinfo=X).astimezone(timezone.utc);n=int(k.timestamp());C=int(datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,14,0,tzinfo=X).astimezone(timezone.utc).timestamp());v=P.get(C)or[]
   if v and(max(v)-min(v))>1.6:continue
   A=compute_weather_probabilities(sp,k,metars,P,forecast_sigma_base_c=h);l=None
   for B,b in enumerate(sp.buckets):
    u=d(b.market_id,n)
    if u is None:continue
    e=round(u+j,4);w=A["probs"][B];r=w-e
    if.16<=e<=.62 and r>=.1 and w>=.34:
     if l is None or r>l[0]:l=(r,B,b,e,w)
   if l is not None:r,B,b,e,w=l;q=D/e;N=(b.outcome_yes_resolved==1);M=(q*1.-D)if N else(-D);F.append({"split":R,"sleeve":"W2_ENSEMBLE_VALUE","city":sp.city,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket":b.label,"entry_ts":n,"entry_px":e,"p_model":round(w,4),"edge":round(r,4),"won":N,"pnl_usd":round(M,2),"roi_pct":round(1e2*M/D,2)});g=True
  f=False
  for W,V in((16,0),(17,0),(18,0),(19,0),(20,0),(21,0),(22,0)):
   if f:break
   k=datetime(sp.obs_date.year,sp.obs_date.month,sp.obs_date.day,W,V,tzinfo=X).astimezone(timezone.utc);n=int(k.timestamp());A=compute_weather_probabilities(sp,k,metars,P,forecast_sigma_base_c=h)
   if not A["is_solar_lock"]or A["locked_bucket_idx"]is None:continue
   b=sp.buckets[A["locked_bucket_idx"]];u=d(b.market_id,n)
   if u is None:continue
   e=round(u+j,4);O=A["p_locked_bucket"];r=O-e
   if.55<=e<=.93 and r>=.04:q=E/e;N=(b.outcome_yes_resolved==1);M=(q*1.-E)if N else(-E);G.append({"split":R,"sleeve":"W1_SOLAR_PEAK_LOCK","city":sp.city,"icao":sp.icao,"obs_date":sp.obs_date.isoformat(),"bucket":b.label,"entry_ts":n,"entry_px":e,"p_model":round(O,4),"cooling_cushion_c":A["cooling_cushion_c"],"edge":round(r,4),"won":N,"pnl_usd":round(M,2),"roi_pct":round(1e2*M/E,2)});f=True
 return{"calibrated_sigma_c":h,"events_evaluated":len(K),"W1_SOLAR_PEAK_LOCK":{"ALL":summarize_trades(G,"W1_ALL"),"TRAIN":summarize_trades([t for t in G if t["split"]=="TRAIN"],"W1_TRAIN"),"TEST_OOS":summarize_trades([t for t in G if t["split"]=="TEST"],"W1_TEST_OOS"),"sample_trades":G[-8:]},"W2_ENSEMBLE_VALUE":{"ALL":summarize_trades(F,"W2_ALL"),"TRAIN":summarize_trades([t for t in F if t["split"]=="TRAIN"],"W2_TRAIN"),"TEST_OOS":summarize_trades([t for t in F if t["split"]=="TEST"],"W2_TEST_OOS"),"sample_trades":F[-8:]}}
def run_crypto_barrier_and_strike_backtests():
 print("[2/3] Fetching Oct 2026 Binance 5m klines + Deribit DVOL + Resolved Hit & Strike events...",flush=True);_h=int(datetime(2026,9,29,0,0,tzinfo=timezone.utc).timestamp());_t=int(datetime(2026,10,25,16,0,tzinfo=timezone.utc).timestamp());_x={"BTC":fetch_binance_5m_series("BTCUSDT",_h,_t),"ETH":fetch_binance_5m_series("ETHUSDT",_h,_t)};_G={"BTC":fetch_deribit_dvol_hourly("BTC",_h,_t),"ETH":fetch_deribit_dvol_hourly("ETH",_h,_t)}
 def c(asset,ts):t=(ts//300)*300;r=_x[asset].get(t)or _x[asset].get(t-300);return r[3]if r else None
 def d(asset,ts):
  b5=(ts//300)*300;_C=_x[asset];_E=[]
  for t in range(b5-48*300,b5,300):
   r0=_C.get(t);r1=_C.get(t+300)
   if r0 and r1 and r0[3]>0 and r1[3]>0:_E.append(math.log(r1[3]/r0[3]))
  if len(_E)<12:return.0
  r=sum(x*x for x in _E)/len(_E);return math.sqrt(r*(365.25*288.))
 def e(asset,ts):
  t=(ts//3600)*3600
  for r in(0,-3600,-7200,3600):
   if(t+r)in _G[asset]:return _G[asset][t+r]
  return.42 if asset=="BTC"else.54
 def b(asset,start_ts,now_ts,strike,direction):
  r=(int(start_ts)//300)*300;_C=(now_ts//300)*300;x=_x[asset]
  for t in range(r,_C+300,300):
   _E=x.get(t)
   if not _E:continue
   if direction=="UP"and _E[1]>=strike:return True
   if direction=="DOWN"and _E[2]<=strike:return True
  return False
 _g=[]
 for asset,_B,_o in[("BTC","DAILY","bitcoin-hit-price-daily"),("ETH","DAILY","ethereum-hit-price-daily"),("BTC","WEEKLY","bitcoin-hit-price-weekly"),("ETH","WEEKLY","ethereum-hit-price-weekly")]:
  _n=http_get_json(f"{GAMMA_URL}/events?series_slug={_o}&closed=true&order=endDate&ascending=false&limit=24")or[]
  for ev in _n:
   for r in parse_hit_event(ev,asset,_B,_o):
    if r.resolved_yes is not None and r.end_ts>=datetime(2026,10,2,tzinfo=timezone.utc).timestamp():_g.append(r)
 print(f"      Loaded {len(_g)} resolved Barrier Hit rungs. Fetching CLOB histories...",flush=True)
 def f(r):return r,fetch_clob_history(r.yes_token,fidelity=20),fetch_clob_history(r.no_token,fidelity=20)
 H=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=28)as _m:
  for _l in _m.map(f,_g):
   if _l[1]or _l[2]:H.append(_l)
 m=1.12;q=999.;O=[x for x in H if x[0].end_ts<=SPLIT_CUTOFF_TS]
 for _w in(.95,1.05,1.15,1.25):
  bs=.0;bn=0
  for r,y,_ in O:
   if not y:continue
   _s=len(y)//3;p,_=y[_s];U=r.end_ts-p;B=c(r.asset,p)
   if not B or U<=1800 or b(r.asset,r.start_ts,p,r.strike,r.direction):continue
   Y,_=get_wing_implied_vol(r.asset,B,r.strike,U,dvol_annual_override=e(r.asset,p));_I=first_passage_touch_prob(B,r.strike,U,Y,r.direction,wick_vol_multiplier=_w);bs+=(_I-float(r.resolved_yes))**2;bn+=1
  if bn>0 and(bs/bn)<q:q=bs/bn;m=_w
 print(f"      [TRAIN Calibration] Optimal Barrier 1m-Wick Vol Multiplier={m:.2f} (Brier={q:.4f}).",flush=True);N=[];E=[];_d=.07;_a=.008
 for r,y,W in sorted(H,key=lambda x:x[0].end_ts):
  _c="TRAIN"if r.end_ts<=SPLIT_CUTOFF_TS else"TEST"
  for _v,(p,V)in enumerate(y):
   U=r.end_ts-p
   if not(7200<=U<=5*86400):continue
   if not(.04<=V<=.26):continue
   B=c(r.asset,p);_A=c(r.asset,p-7200)
   if not B or not _A or b(r.asset,r.start_ts,p,r.strike,r.direction):continue
   _p=e(r.asset,p);_z=d(r.asset,p);P=(r.direction=="UP"and B>_A*1.003)or(r.direction=="DOWN"and B<_A*.997)
   if _z<.95*_p or not P:continue
   Y,_=get_wing_implied_vol(r.asset,B,r.strike,U,dvol_annual_override=max(_p,.5*(_p+_z)));L=first_passage_touch_prob(B,r.strike,U,Y,r.direction,wick_vol_multiplier=m);w=V+_a;D=_d*w*(1.-w);v=w+D;T=L-v
   if T>=.065 and(L/v)>=1.4:
    o=25.;n=o/v;_y=min(.88,round(2.*w,3));M=False
    for _b,C in y[_v+1:]:
     if C>=_y+.005:M=True;break
    if M:h=n*_y;s=True;a="MAKER_2X_TP"
    else:s=(r.resolved_yes==1);h=n*(1. if s else.0);a="HOLD_SETTLE"
    Q=h-o;N.append({"split":_c,"sleeve":"B1_CONVEX_TAIL_YES","asset":r.asset,"question":r.question,"entry_ts":p,"entry_px":round(v,4),"p_model":round(L,4),"edge":round(T,4),"exit_mode":a,"won":s,"pnl_usd":round(Q,2),"roi_pct":round(1e2*Q/o,2)});break
  for p,_f in W:
   U=r.end_ts-p
   if not(3600<=U<=36000):continue
   if not(.68<=_f<=.9):continue
   B=c(r.asset,p)
   if not B or b(r.asset,r.start_ts,p,r.strike,r.direction):continue
   Y,_=get_wing_implied_vol(r.asset,B,r.strike,U,dvol_annual_override=e(r.asset,p));L=first_passage_touch_prob(B,r.strike,U,Y,r.direction,wick_vol_multiplier=m);_D=1.-L;w=_f+_a;D=_d*w*(1.-w);v=w+D;T=_D-v
   if _D>=.88 and T>=.04:o=1e2;n=o/v;s=(r.resolved_yes==0);Q=(n*1.-o)if s else(-o);E.append({"split":_c,"sleeve":"B2_BARRIER_NO_LOCK","asset":r.asset,"question":r.question,"entry_ts":p,"entry_px":round(v,4),"p_model":round(_D,4),"edge":round(T,4),"won":s,"pnl_usd":round(Q,2),"roi_pct":round(1e2*Q/o,2)});break
 print("[3/3] Fetching resolved October 2026 Multi-Strike ('above ___') ladders...",flush=True);X=[]
 for asset,_o in[("BTC","btc-multi-strikes-weekly"),("ETH","ethereum-multi-strikes-weekly")]:
  _n=http_get_json(f"{GAMMA_URL}/events?series_slug={_o}&closed=true&order=endDate&ascending=false&limit=24")or[]
  for ev in _n:
   for sr in parse_multistrike_event(ev,asset,_o):
    if sr.resolved_yes is not None and sr.end_ts>=datetime(2026,10,2,tzinfo=timezone.utc).timestamp():X.append(sr)
 def g(sr):return sr,fetch_clob_history(sr.yes_token,fidelity=20),fetch_clob_history(sr.no_token,fidelity=20)
 K=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=28)as _m:
  for _l in _m.map(g,X):
   if _l[1]or _l[2]:K.append(_l)
 print(f"      Loaded {len(K)} resolved Multi-Strike contracts with CLOB histories.",flush=True);G=[];J=[]
 for sr,y,W in sorted(K,key=lambda x:x[0].end_ts):
  _c="TRAIN"if sr.end_ts<=SPLIT_CUTOFF_TS else"TEST"
  for _k,_H,_j in[("YES",y,sr.resolved_yes==1),("NO",W,sr.resolved_yes==0)]:
   A=False;z=False
   for _v,(p,V)in enumerate(_H):
    U=sr.end_ts-p
    if U<=900:break
    B=c(sr.asset,p);_r=c(sr.asset,p-900)
    if not B or not _r:continue
    if abs(math.log(sr.strike/B))>.08:continue
    _i=evaluate_svi_digital_fair_value(sr.asset,B,sr.strike,U,is_downward=sr.is_downward,dvol_annual_override=e(sr.asset,p),now_ts=float(p));_u=_i["p_yes"]if _k=="YES"else _i["p_no"];Z=((B-_r)/_r)*1e4;_q=(_k=="YES"and not sr.is_downward)or(_k=="NO"and sr.is_downward)
    if(_q and Z<-20.)or((not _q)and Z>20.):continue
    w=V+_a;D=_d*w*(1.-w);v=w+D;T=_u-v
    if(not A)and(10800<=U<=86400)and(.2<=w<=.8)and T>=.055:
     o=1e2;n=o/v;_e=min(.96,round(v+.05,4));S=max(.04,round(w-.075,4));l=None;j=.0;a="SETTLED"
     for _b,C in _H[_v+1:]:
      if C>=_e+.005:l=_e;j=.0;a="MAKER_TP_5C";break
      if C<=S:u=max(.01,C-_a);l=u;j=_d*u*(1.-u);a="HARD_STOP_7.5C";break
      if sr.end_ts-_b<=3600:u=max(.01,C-_a);l=u;j=_d*u*(1.-u);a="TIME_STOP_1H";break
     if l is not None:h=n*(l-j);s=h>o
     else:h=n*(1. if _j else.0);s=_j
     Q=h-o;G.append({"split":_c,"sleeve":"M1_SVI_MAKER_SCALP","asset":sr.asset,"question":sr.question,"side":_k,"entry_ts":p,"entry_px":round(v,4),"p_model":round(_u,4),"edge":round(T,4),"exit_mode":a,"won":s,"pnl_usd":round(Q,2),"roi_pct":round(1e2*Q/o,2)});A=True
    if((not z)and(1200<=U<=6300)and(.68<=w<=.9)and _i["z_sigma"]>=1.55 and _u>=.91 and T>=.04):
     o=1e2;n=o/v;k=None;i=.0;a="SETTLED";R=max(.25,w-.22)
     for _,C in _H[_v+1:]:
      if C>=.975:k=.97;i=.0;a="MAKER_TP_97C";break
      if C<=R:u=max(.05,C-_a);k=u;i=_d*u*(1.-u);a="SALVAGE_STOP";break
     if k is not None:h=n*(k-i);s=h>o
     else:h=n*(1. if _j else.0);s=_j
     Q=h-o;J.append({"split":_c,"sleeve":"M2_STRIKE_CONVERGENCE","asset":sr.asset,"question":sr.question,"side":_k,"entry_ts":p,"entry_px":round(v,4),"p_model":round(_u,4),"z_sigma":_i["z_sigma"],"edge":round(T,4),"exit_mode":a,"won":s,"pnl_usd":round(Q,2),"roi_pct":round(1e2*Q/o,2)});z=True
 F={"calibrated_wick_vol_mult":m,"rungs_evaluated":len(H),"B1_CONVEX_TAIL_YES":{"ALL":summarize_trades(N,"B1_ALL"),"TRAIN":summarize_trades([t for t in N if t["split"]=="TRAIN"],"B1_TRAIN"),"TEST_OOS":summarize_trades([t for t in N if t["split"]=="TEST"],"B1_TEST_OOS"),"sample_trades":N[-8:]},"B2_BARRIER_NO_LOCK":{"ALL":summarize_trades(E,"B2_ALL"),"TRAIN":summarize_trades([t for t in E if t["split"]=="TRAIN"],"B2_TRAIN"),"TEST_OOS":summarize_trades([t for t in E if t["split"]=="TEST"],"B2_TEST_OOS"),"sample_trades":E[-8:]}};I={"rungs_evaluated":len(K),"M1_SVI_MAKER_SCALP":{"ALL":summarize_trades(G,"M1_ALL"),"TRAIN":summarize_trades([t for t in G if t["split"]=="TRAIN"],"M1_TRAIN"),"TEST_OOS":summarize_trades([t for t in G if t["split"]=="TEST"],"M1_TEST_OOS"),"sample_trades":G[-8:]},"M2_STRIKE_CONVERGENCE":{"ALL":summarize_trades(J,"M2_ALL"),"TRAIN":summarize_trades([t for t in J if t["split"]=="TRAIN"],"M2_TRAIN"),"TEST_OOS":summarize_trades([t for t in J if t["split"]=="TEST"],"M2_TEST_OOS"),"sample_trades":J[-8:]}};return F,I
def main():
 l=time.time();b=run_weather_backtest();a,c=run_crypto_barrier_and_strike_backtests();d={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"elapsed_sec":round(time.time()-l,2),"split_cutoff_utc":"2026-10-16T23:59:59Z","option_1_weather":b,"option_2_barrier_onetouch":a,"option_4_multistrike_svi":c};REPORT_JSON.write_text(json.dumps(d,indent=2),encoding="utf-8");print("\n================= WALK-FORWARD BACKTEST SUMMARY =================")
 for f,e in[("OPTION #1 WEATHER",["W1_SOLAR_PEAK_LOCK","W2_ENSEMBLE_VALUE"]),("OPTION #2 BARRIER",["B1_CONVEX_TAIL_YES","B2_BARRIER_NO_LOCK"]),("OPTION #4 STRIKE SVI",["M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE"])]:
  g=(b if"WEATHER"in f else(a if"BARRIER"in f else c));print(f"\n--- {f} ---")
  for k in e:j=g[k]["TRAIN"];i=g[k]["TEST_OOS"];h=g[k]["ALL"];print(f"  {k:24s} | ALL: {h['trades']:3d} tr, WR={h['win_rate_pct']:5.1f}%, PnL=${h['net_pnl_usd']:+8.2f}, PF={h['profit_factor']:5.2f}, MaxDD=${h['max_drawdown_usd']:6.2f}\n  {'':24s} | TRN: {j['trades']:3d} tr, WR={j['win_rate_pct']:5.1f}%, PnL=${j['net_pnl_usd']:+8.2f}, PF={j['profit_factor']:5.2f} | OOS: {i['trades']:3d} tr, WR={i['win_rate_pct']:5.1f}%, PnL=${i['net_pnl_usd']:+8.2f}, PF={i['profit_factor']:5.2f}")
 print(f"\nSaved full JSON report -> {REPORT_JSON}")
if __name__=="__main__":main()
# ======================================================================================
# [18/20] MODULE: scripts/polymarket_daily_projections.py
# PURPOSE: Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker
# ======================================================================================

import argparse;import json;import os;from datetime import datetime,timedelta,timezone;from pathlib import Path;from typing import Any,Dict,List,Optional,Tuple;PIPELINE_ROOT=Path(__file__).resolve().parent.parent;LIVE_STATE_FILE=PIPELINE_ROOT/"data"/"polymarket"/"live_harvester_state.json";ALPHA124_STATE_FILE=(PIPELINE_ROOT/"data"/"alpha124"/"alpha124_shadow_state.json"if(PIPELINE_ROOT/"data"/"alpha124"/"alpha124_shadow_state.json").exists()else PIPELINE_ROOT/"data"/"polymarket"/"alpha124_shadow_state.json");EXP316_STATE_FILE=PIPELINE_ROOT/"data"/"exp316"/"exp316_shadow_state.json";SOL_SHADOW_FILE=PIPELINE_ROOT/"data"/"polymarket"/"state_shadow_sol_v392.json";XRP_SHADOW_FILE=PIPELINE_ROOT/"data"/"polymarket"/"state_shadow_xrp_v392.json";PHASE34_TRACKER_FILE=PIPELINE_ROOT/"data"/"polymarket"/"shadow_phase3_4_tracker.jsonl";RISK_CONFIG_FILE=PIPELINE_ROOT/"config"/"polymarket_risk_config.json";STRATEGY_RISK_CONFIG_FILE=PIPELINE_ROOT/"config"/"polymarket_strategy_and_risk.json";UNIVERSE_COVERAGE_FILE=PIPELINE_ROOT/"data"/"universe"/"coverage_snapshot.json";FULL_THROTTLE_DASHBOARD_FILE=PIPELINE_ROOT/"data"/"full_throttle"/"pipeline"/"dashboard_latest.json";OUTPUT_JSON_FILE=PIPELINE_ROOT/"data"/"polymarket"/"live_daily_projections.json";FINLAND_VM_COST_USD_PER_MONTH=24.67;FINLAND_VM_COST_USD_PER_DAY=.8223;QUARANTINED_SLEEVES=frozenset({"M4_SHOCK_STRIKE_CATCHUP","W2_ENSEMBLE_VALUE","W2_MAKER_OVERROUND","M1_SVI_MAKER_SCALP","M2_STRIKE_CONVERGENCE","P1_PREOPEN_MAKER_STRADDLE","B1_CONVEX_TAIL_YES","B4_TOUCHED_BARRIER_WICK_LOCK","ZERO_FEE_MAKER_ANCHOR_BOX","SLEEVE_XRP_V392_SHADOW","D1_MAKER_ANCHOR_BOX","ZF_INTRADAY_MAKER_BOX","SHADOW_PHASE3A_MAKER","NR_CONV_NO_BASKET_ARB"});DIRECTIONAL_ONLY_SLEEVES=frozenset({"SLEEVE_SOL_V392_SHADOW","S5M_CHAINLINK_SNIPER","S4H_CHAINLINK_CONVERGENCE","U1_DAILY_UPDOWN_LOCK","B2_BARRIER_NO_LOCK","CM_SHOCK_PYTH_CATALYST","EXP316_TRACK_A_LATE_LOCK"});GRADUATION_SPECS=[{"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","wave":"Wave 1 (Live Graduated)","target_day":1,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":13.5,"l1_daily_pnl_cap_usd":140.},{"sleeve":"D1_QUIET_BOOK_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":3,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":65.},{"sleeve":"D1_4H_DOMINANCE_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":60.},{"sleeve":"C1_BINARY_COMPLETE_SET","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"NR2_CONVERT_NO_SUBSET_ARB","wave":"Wave 1 (m=2 Atomic Convert)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"M3_LADDER_MONO_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"B3_BARRIER_MONO_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"D1_MAKER_ANCHOR_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":45.},{"sleeve":"N1_NEGRISK_CROSS_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":20.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"W3_WEATHER_SLATE_ARB","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"CM_B3_PYTH_BARRIER_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"SP1_NBA_ZERO_FEE_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"ZF_INTRADAY_MAKER_BOX","wave":"Wave 1 (Fast-Track Maker Box 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":92.,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"NR0_ZERO_FEE_SLATE_ARB","wave":"Wave 1 (Fast-Track 8/8)","target_day":4,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"ZERO_FEE_MAKER_ANCHOR_BOX","wave":"Wave 1 (Fast-Track Maker Box)","target_day":5,"min_days":1.,"min_settled":8,"min_wr_pct":92.,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"CTF_OVERROUND_MINT_SELL","wave":"Wave 1 (Instant Mint-Sell 8/8)","target_day":4,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"TW1_COUNTING_TRUNCATION_AND_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":5,"min_days":1.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"FED1_CENTRAL_BANK_LP_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"COND1_MACRO_PARTITION_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"D2_12PM_BINANCE_BOX","wave":"Wave 1 (Fast-Track 8/8)","target_day":5,"min_days":1.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"GAS1_AAA_GASOLINE_LOCK","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":20.},{"sleeve":"MKR_REWARD_LOCKED_CARRY","wave":"Wave 1 (Fast-Track 8/8)","target_day":6,"min_days":2.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":20.},{"sleeve":"BOND1_UMA_RESOLUTION_CARRY","wave":"Wave 1 (Live Graduated 8/8)","target_day":1,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":45.25,"l1_daily_pnl_cap_usd":35.},{"sleeve":"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"SOC2_EXACT_SCORE_2D_LATTICE","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":20.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"AFF1_FROZEN_SUBPERIOD_COLLAPSE","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":20.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER","wave":"Wave 1 (Liquid-Guarded Live)","target_day":1,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":22.,"l1_daily_pnl_cap_usd":20.},{"sleeve":"SP4_MULTISPORT_CORRIDOR_DOMINANCE_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"LP2_CROSS_MARKET_PARTITION_IMPLICATION_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"NR1_CLOSED_PARTITION_COMPLETE_SET","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"CRY_INC1_INTRADAY_STRIKE_INCLUSION_BOX","wave":"Wave 1 (0-Loss Math Live)","target_day":1,"min_days":1.,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":25.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"SP2_NBA_ENDGAME_LOCK","wave":"Wave 2 (Day 7 NBA Endgame)","target_day":7,"min_days":3.,"min_settled":15,"min_wr_pct":93.,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":45.},{"sleeve":"W1_LOW_TROUGH_LOCK","wave":"Wave 2 (Day 8 METAR Low)","target_day":8,"min_days":4.,"min_settled":15,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":40.},{"sleeve":"SLEEVE_SOL_V392_SHADOW","wave":"Wave 2 (Day 5 SOL)","target_day":5,"min_days":1.5,"min_settled":30,"min_wr_pct":85.,"source":"sol_shadow","stage1_ticket_usd":12.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"SHADOW_PHASE3A_MAKER","wave":"Wave 2 (Day 6 Maker)","target_day":6,"min_days":2.,"min_settled":25,"min_wr_pct":80.,"source":"phase3a_shadow","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":32.},{"sleeve":"W1_SOLAR_PEAK_LOCK","wave":"Wave 2 (Day 8 METAR)","target_day":8,"min_days":5.,"min_settled":20,"min_wr_pct":86.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":95.},{"sleeve":"B2_BARRIER_NO_LOCK","wave":"Wave 2 (Day 8 Barrier)","target_day":8,"min_days":5.,"min_settled":25,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":55.},{"sleeve":"CM_B2_PYTH_SESSION_NO_LOCK","wave":"Wave 2 (Day 9 Pyth 0%-Fee)","target_day":9,"min_days":5.,"min_settled":25,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":45.},{"sleeve":"CM_U1_PYTH_CLOSE_LOCK","wave":"Wave 2 (Day 10 Pyth Close)","target_day":10,"min_days":5.,"min_settled":25,"min_wr_pct":88.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"EXP316_TRACK_A_LATE_LOCK","wave":"Wave 2 (Day 10 Strike)","target_day":10,"min_days":5.,"min_settled":25,"min_wr_pct":80.,"source":"exp316","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"U1_DAILY_UPDOWN_LOCK","wave":"Wave 3 (Day 15 Daily)","target_day":15,"min_days":10.,"min_settled":20,"min_wr_pct":85.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"S5M_CHAINLINK_SNIPER","wave":"Wave 3 (Day 15 5m)","target_day":15,"min_days":7.,"min_settled":35,"min_wr_pct":82.,"source":"alpha124","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"S4H_CHAINLINK_CONVERGENCE","wave":"Wave 3 (Day 14 4h)","target_day":14,"min_days":7.,"min_settled":25,"min_wr_pct":85.,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":30.},{"sleeve":"CM_SHOCK_PYTH_CATALYST","wave":"Wave 3 (Day 16 Macro Jump)","target_day":16,"min_days":10.,"min_settled":25,"min_wr_pct":82.,"source":"alpha124","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"S2_EXACT_TWAP_LOCK","wave":"Wave 1 (Live Bridged S2MKR)","target_day":1,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"S2_RTDS_EXACT_TWAP_INTEGRATOR","wave":"Wave 1 (Live Bridged S2MKR)","target_day":1,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":14.,"l1_daily_pnl_cap_usd":35.},{"sleeve":"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","wave":"Wave 1 (Live BOND2 Carry)","target_day":1,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":16.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"UMA_READY1_LIVENESS_PRIORITY","wave":"Wave 1 (Live BOND1 Inherited)","target_day":1,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":18.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"W_PRUNE1_DEAD_NO_BOND","wave":"Wave 1 (Live METAR Ratchet)","target_day":1,"min_days":.25,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":25.},{"sleeve":"TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR","wave":"Wave 1 (Live Zero-Loss Math)","target_day":2,"min_days":.5,"min_settled":8,"min_wr_pct":1e2,"source":"alpha124","stage1_ticket_usd":15.,"l1_daily_pnl_cap_usd":25.}]
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
STRICT_PURE_RISKLESS_LIVE_SLEEVES=frozenset({"D1_SAME_ORACLE_DOMINANCE_BOX","D1_4H_DOMINANCE_BOX","D1_QUIET_BOOK_BOX","C1_BINARY_COMPLETE_SET","NR2_CONVERT_NO_SUBSET_ARB"})
def _is_riskless_only_mode_configured(strategy_cfg=None):
 b=strategy_cfg if isinstance(strategy_cfg,dict)else _load_json(STRATEGY_RISK_CONFIG_FILE);a=b.get("directional")if isinstance(b,dict)else None
 if isinstance(a,dict)and"riskless_only_mode"in a:return bool(a.get("riskless_only_mode"))
 return False
def _is_strict_pure_riskless_configured(strategy_cfg=None):
 b=strategy_cfg if isinstance(strategy_cfg,dict)else _load_json(STRATEGY_RISK_CONFIG_FILE);a=b.get("riskless_boxes")if isinstance(b,dict)else None
 if isinstance(a,dict)and"strict_pure_riskless_mode"in a:return bool(a.get("strict_pure_riskless_mode"))and not bool(a.get("enable_single_leg_maker_bond1",True))
 return False
def simulate_single_day_net_pnl(day_idx,equity_start,scenario,scale_up_threshold=98.,shadow_by_sleeve=None,sol_shadow=None,phase3a_shadow=None,exp316_t1k=None,riskless_only=None,strict_pure_riskless=None):
 i=_is_riskless_only_mode_configured()if riskless_only is None else bool(riskless_only);d=(i and(_is_strict_pure_riskless_configured()if strict_pure_riskless is None else bool(strict_pure_riskless)));_w=_box_concurrency_mult(equity_start)
 if d:
  f={"P25_CONSERVATIVE":.52,"P50_BASE_FINLAND":1.,"P75_LONDON_UPSIDE":1.82}[scenario];Y=60. if equity_start<98. else(120. if equity_start<253. else(160. if equity_start<1003. else 220.));_v=min(Y,max(10.,equity_start*.88));C=.92*f*(1.+.42*(_w-1.));X={"P25_CONSERVATIVE":10.5,"P50_BASE_FINLAND":19.5,"P75_LONDON_UPSIDE":36.}[scenario];W=min(X,_v*C*(.0245*_depth_decay(_v,knee_usd=85.)));V=55. if equity_start<98. else(105. if equity_start<253. else 155.);_u=min(V,max(10.,equity_start*.65));B=.16*f*_w;U={"P25_CONSERVATIVE":2.5,"P50_BASE_FINLAND":4.5,"P75_LONDON_UPSIDE":8.5}[scenario];T=min(U,_u*B*(.0145*_depth_decay(_u,knee_usd=80.)));x={"BOND1_and_BOND2_uma_resolution_carry":.0,"S2_rtds_twap_and_clinch_locks":.0,"D1_same_oracle_and_quiet_boxes":round(W,2),"V3_zero_loss_math_and_c1_merge_boxes":round(T,2),"dynamic_tier_unlock_sleeves":.0}
  if equity_start>=1003.:h="INSTITUTIONAL_MATH_RISKLESS (>=$1,003): Depth-Capped D1 Same-Oracle + C1 Merge + m=2 NR2 Convert ($220 Box Cap)"
  elif equity_start>=253.:h="SCALE_MATH_RISKLESS ($253-$1,003): $120-$160 D1/C1/NR2(m=2) Payoff-Dominance Only (0 Single-Leg Carries)"
  elif equity_start>=98.:h="GROWTH_MATH_RISKLESS ($98-$253): $120 D1 Cap + C1 Instant Merge + m=2 NR2 Convert (100% Unencumbered Cash)"
  else:h="SEED_MATH_RISKLESS (<$98): Pure Payoff-Dominance D1 + C1 Merge + m=2 NR2 (0 UMA/Single-Leg Dispute Exposure)"
  return round(sum(x.values()),2),x,h
 if i:
  k={"P25_CONSERVATIVE":.55,"P50_BASE_FINLAND":1.,"P75_LONDON_UPSIDE":1.72}[scenario];n={"P25_CONSERVATIVE":.58,"P50_BASE_FINLAND":1.,"P75_LONDON_UPSIDE":1.5}[scenario];m=max(10.,equity_start*.92);w=min(75.,max(18.,equity_start*.16))if equity_start>=125. else.0;_t=min(60.,max(15.,equity_start*.12))if equity_start>=140. else.0;_s=min(110.,max(25.,equity_start*.15))if equity_start>=253. else.0;_d=min(140.,max(35.,equity_start*.14))if equity_start>=5e2 else.0;A=min(240.,max(10.,m-w-_t-.5*_s));g=.86;v=1.85*g*n*(1.+.3*(_w-1.));u={"P25_CONSERVATIVE":7.5,"P50_BASE_FINLAND":13.5,"P75_LONDON_UPSIDE":22.}[scenario];t=min(u,A*v*(.0058*_depth_decay(A*.2,knee_usd=85.)));S=min(65.,max(6.5,equity_start*.24));q=1.65*(.5*n+.5*k)*(1.+.25*(_w-1.));_r={"P25_CONSERVATIVE":6.5,"P50_BASE_FINLAND":12.,"P75_LONDON_UPSIDE":21.}[scenario];_q=min(_r,S*q*(.0105*_depth_decay(S,knee_usd=70.)));R=60. if equity_start<98. else(120. if equity_start<253. else(165. if equity_start<1003. else 220.));_p=min(R,max(7.3,equity_start*.42));z=1.45*k*(1.+.38*(_w-1.));Q={"P25_CONSERVATIVE":15.,"P50_BASE_FINLAND":28.5,"P75_LONDON_UPSIDE":52.}[scenario];P=min(Q,_p*z*(.0215*_depth_decay(_p,knee_usd=75.)));O=55. if equity_start<98. else(110. if equity_start<253. else 165.);_o=min(O,max(7.3,equity_start*.32));y=2.65*(.35*n+.65*k)*_w;N={"P25_CONSERVATIVE":12.,"P50_BASE_FINLAND":22.5,"P75_LONDON_UPSIDE":38.}[scenario];M=min(N,_o*y*(.0145*_depth_decay(_o,knee_usd=80.)));b=.0
  if w>.0:b+=w*.0135*n
  if _t>.0:I=2.1*(.4*n+.6*k);_n={"P25_CONSERVATIVE":8.,"P50_BASE_FINLAND":14.5,"P75_LONDON_UPSIDE":25.}[scenario];b+=min(_n,_t*I*(.0115*_depth_decay(_t,knee_usd=75.)))
  if _s>.0:_m={"P25_CONSERVATIVE":5.5,"P50_BASE_FINLAND":10.5,"P75_LONDON_UPSIDE":18.}[scenario];b+=min(_m,_s*1.35*n*(.011*_depth_decay(_s,knee_usd=95.)))
  if _d>.0:_c={"P25_CONSERVATIVE":6.5,"P50_BASE_FINLAND":12.5,"P75_LONDON_UPSIDE":22.}[scenario];b+=min(_c,_d*1.15*k*(.014*_depth_decay(_d,knee_usd=95.)))
  s={"BOND1_and_BOND2_uma_resolution_carry":round(t,2),"S2_rtds_twap_and_clinch_locks":round(_q,2),"D1_same_oracle_and_quiet_boxes":round(P,2),"V3_zero_loss_math_and_c1_merge_boxes":round(M,2),"dynamic_tier_unlock_sleeves":round(b,2)}
  if equity_start>=1003.:a="INSTITUTIONAL_RISKLESS (>=$1,003): Full-Throttle 14-Family Stack ($165-$220 Caps + Stage G + Atomic NR3+)"
  elif equity_start>=5e2:a="MULTILEG_ATOMIC_UNLOCKED ($500-$1,003): >=3-Leg Atomic NegRisk + Stage G Cross-Venue + Pre-Split Gun"
  elif equity_start>=253.:a="SCALE_RISKLESS ($253-$500): Stage G CA-ON Cross-Venue Candidate + $120 D1/C1 Caps + Pre-Split Gun"
  elif equity_start>=140.:a="TIER_2_UNLOCKED (>=$140): Pre-Split Atomic Overround Gun + MKR_REWARD/Family L + Full-Throttle 2-Leg"
  elif equity_start>=125.:a="TIER_1_UNLOCKED ($125-$140): MKR_REWARD_LOCKED_CARRY + Family L Hedged Maker ($140 Pre-Split Next)"
  else:a="SEED_FULL_THROTTLE_RISKLESS (<$125): 606-UMA 18s BOND1 + 1,200-Bin 15bps C1 Merge + FT CLASS_A/B + D1"
  return round(sum(s.values()),2),s,a
 l={"P25_CONSERVATIVE":.85,"P50_BASE_FINLAND":1.35,"P75_LONDON_UPSIDE":1.95}[scenario];e={"P25_CONSERVATIVE":.145,"P50_BASE_FINLAND":.182,"P75_LONDON_UPSIDE":.21}[scenario];j={"P25_CONSERVATIVE":.91,"P50_BASE_FINLAND":.95,"P75_LONDON_UPSIDE":.97}[scenario];L={"P25_CONSERVATIVE":.62,"P50_BASE_FINLAND":1.,"P75_LONDON_UPSIDE":1.42}[scenario];_l=compute_v541_ticket_size(equity_start);H=1.28 if equity_start>=253. else(1.15 if equity_start>=150. else 1.);p=l*H;_k=e*j*_depth_decay(_l,knee_usd=65.);_b={"P25_CONSERVATIVE":55.,"P50_BASE_FINLAND":95.,"P75_LONDON_UPSIDE":145.}[scenario];_a=min(_b,_l*p*_k);_j=60. if equity_start<98. else(120. if equity_start<253. else(150. if equity_start<1003. else 220.));_y=min(_j,max(14.,equity_start*.48));K=1.95*L*(1.+.45*(_w-1.));_i={"P25_CONSERVATIVE":24.,"P50_BASE_FINLAND":38.,"P75_LONDON_UPSIDE":58.}[scenario];_h=min(_i,_y*K*(.031*_depth_decay(_y,knee_usd=75.)));_g=(60. if equity_start<98. else(max(60.,equity_start*.4)if equity_start<253. else(120. if equity_start<1003. else 150.)));_x=min(_g,max(14.,equity_start*.36));J=1.2*L*_w;_f={"P25_CONSERVATIVE":16.,"P50_BASE_FINLAND":26.,"P75_LONDON_UPSIDE":40.}[scenario];_e=min(_f,_x*J*(.0235*_depth_decay(_x,knee_usd=80.)));G=45.25 if equity_start<98. else(85. if equity_start<253. else(130. if equity_start<1003. else 180.));Z=min(G,equity_start*.42);r=2.1*L*(1.+.55*(_w-1.));F={"P25_CONSERVATIVE":6.5,"P50_BASE_FINLAND":11.,"P75_LONDON_UPSIDE":17.}[scenario];E=min(F,Z*r*.0082);D={"v541_high_z_directional_sniper":round(_a,2),"D1_same_oracle_and_quiet_boxes":round(_h,2),"V3_zero_loss_math_partition_boxes":round(_e,2),"BOND1_and_liquid_MKR_LOCK1_carry":round(E,2)}
 if equity_start>=1003.:c="INSTITUTIONAL (>=$1,003): 4 Dir Slots ($160-$200 Cap) + 10 Box Slots ($150-$220 L1 Depth Cap)"
 elif equity_start>=253.:c="SCALE ($253-$1,003): 4 Dir Slots (22% Ticket) + $120-$150 Box Cap + 88% BOND1"
 elif equity_start>=150.:c="HYPER_GROWTH 3-Slot (>=$150): 3 Crypto Dir Slots (26% Ticket) + $120 D1 Cap + 48h Velocity"
 elif equity_start>=98.:c="HYPER_GROWTH ($98-$150): 26% Dir Ticket + $120 D1 / 40% ZF Box Cap + 48h Velocity"
 else:c="UNLEASHED_LAUNCH (<$98): v5.4.1 High-Z Sniper + 90% D1 ($60) + 0-Loss Math Boxes + 78% BOND1"
 o=round(sum(D.values()),2);return o,D,c
def compute_live_equity_and_rates(live_st,fallback_equity=75.84):
 C=float(live_st.get("total_account_equity")or.0);H=live_st.get("live_bankroll")if live_st.get("live_bankroll")is not None else live_st.get("bankroll");B=float(H or.0);u=(("total_account_equity"in live_st and live_st.get("total_account_equity")is not None)or H is not None);N=live_st.get("active_positions");G=list(N.values())if isinstance(N,dict)else[];h=.0;z={};i=.0
 for W in G:
  if not isinstance(W,dict):continue
  q=float(W.get("remaining_cost_basis",W.get("notional_usd",.0))or.0);y=W.get("_closed_partner_leg")
  if(W.get("is_dominance_box")and isinstance(y,dict)and float(y.get("payout_usd",.0)or.0)<=.01):U=max(float(W.get("expected_terminal_payout_usd")or W.get("entry_shares")or.0),q+float(y.get("notional_usd",.0)or.0));h+=U;i+=U;continue
  k=.0
  if W.get("is_dominance_box")or W.get("is_single_leg_lock"):
   R=str(W.get("entry_fee_asset")or"").upper()
   if R!="SHARES":k=float(W.get("entry_fee_cash_usd")or W.get("fee_usd")or.0)
   elif(W.get("inventory_reconciled")and float(W.get("fee_usd",.0)or.0)==.0 and float(W.get("fee_rate_applied",.0)or.0)>.0 and float(W.get("entry_shares",.0)or.0)>.0 and float(W.get("entry_shares",.0)or.0)>=float(W.get("gross_entry_shares")or W.get("entry_shares")or.0)-.02):
    _f=float(W["entry_shares"]);_i=q/_f
    if.0<_i<1.:_e=float(W.get("fee_rate_applied")or.0);_d=float(W.get("fee_exponent_applied")or 1.);k=round(_f*_e*((_i*(1.-_i))**_d),4)
  S=q+k;h+=S;M=str(W.get("box_id")or"").strip()
  if W.get("is_dominance_box")and M:z.setdefault(M,[]).append(W)
  else:i+=S
 j=.0;b=.0;m=(live_st.get("collateral_includes_resting_maker")is False or str(live_st.get("collateral_source")or"").upper()=="CLOB_BALANCE_API")
 if isinstance(live_st.get("pending_entry_intents"),dict):
  for Z in live_st["pending_entry_intents"].values():
   if not isinstance(Z,dict):continue
   if m and(Z.get("live_maker_anchor_inflight")or Z.get("maker_wire_inflight")or Z.get("entry_order_id")):j+=max(.0,float(Z.get("notional_usd")or.0))
   if Z.get("live_maker_anchor_inflight"):
    Q=max(.0,float(Z.get("matched_notional_usd")or.0));Y=max(.0,float(Z.get("collat_drop_usd")or.0));_b=float(Z.get("heartbeat_ts")or.0);T=float(Z.get("_collat_surplus_ts")or Z.get("ts")or.0)
    if Y>Q+1e-6 and T>.0 and(_b-T)>=25.:b+=Y-Q
 if u:s=B+h+j;r=max(.0,C-b);l=max(r,s)
 else:l=float(fallback_equity)
 def e(p):return(bool(p.get("is_legged_out_residual"))or str(p.get("box_type")or"").upper()=="MULTI_LEG_RESIDUAL"or"_UNWRESID_"in str(p.get("trade_id")or""))
 def d(p):
  if not isinstance(p,dict):return False
  if bool(p.get("uma_disputed")or p.get("is_uma_disputed")or p.get("disputed")):return True
  for g in("umaResolutionStatus","uma_resolution_status","uma_status","resolution_status"):
   if"disput"in str(p.get(g)or"").strip().lower():return True
  return False
 def a(p):return e(p)or d(p)
 o=any(isinstance(x,dict)and a(x)for x in G);f=.0
 for X in z.values():
  if len(X)>=2 and not any(a(x)for x in X):P=min(float(x.get("remaining_shares",x.get("entry_shares",.0))or.0)for x in X);f+=max(P,sum(float(x.get("remaining_cost_basis",x.get("notional_usd",.0))or.0)for x in X))
  else:f+=sum(.0 if a(x)else float(x.get("remaining_cost_basis",x.get("notional_usd",.0))or.0)for x in X)
 c=.0
 for W in G:
  if not isinstance(W,dict):continue
  M=str(W.get("box_id")or"").strip()
  if W.get("is_dominance_box")and M:continue
  if a(W):continue
  q=float(W.get("remaining_cost_basis",W.get("notional_usd",.0))or.0)
  if W.get("is_single_leg_lock")or str(W.get("box_type")or"").upper()=="SINGLE_LEG_LOCK"or str(W.get("trade_id")or"").startswith(("WS_SNIPE_","LOCK1_","MKR_LOCK1_")):V=float(W.get("remaining_shares",W.get("entry_shares",.0))or.0);c+=max(q,V)
  else:c+=q
 A=B+c+f+j;n=((A if o else max(l,A))if u else l);L=max(float(live_st.get("high_water_mark_equity")or.0),l);F=[t for t in(live_st.get("closed_positions")or[])if isinstance(t,dict)];K={}
 for t in F:
  bk=str(t.get("box_id")or"").strip()
  if bk:K[bk]=K.get(bk,0)+1
 E={}
 for _h,t in enumerate(F):
  J=t.get("realized_pnl_usd")
  if J is None:J=t.get("net_pnl_usd")
  if J is not None:w=float(J)
  else:w=(float(t.get("realized_exit_cash",.0)or.0)-float(t.get("notional_usd",.0)or.0)-float(t.get("fee_usd",.0)or.0))
  bk=str(t.get("box_id")or"").strip();v=bool(bk)and(bool(t.get("is_dominance_box"))or K.get(bk,0)>1);_a=f"BOX::{bk}"if v else f"TRD::{_h}::{t.get('trade_id')or _h}";_g=E.setdefault(_a,{"pnl":.0,"any_won_flag":False,"legs":0});_g["pnl"]+=w;_g["legs"]+=1
  if t.get("won")is True:_g["any_won_flag"]=True
 I=len(E);O=sum(1 for g in E.values()if g["pnl"]>.0 or(abs(g["pnl"])<=1e-9 and g["any_won_flag"]));D=round(1e2*O/I,2)if I>0 else.0;return{"live_equity":l,"locked_floor_equity":n,"liquid_working_cash_usd":round(B+f,4)if u else round(l,4),"frozen_single_leg_cost_usd":round(i,4)if u else.0,"hwm_equity":L,"closed_legs_count":len(F),"economic_trades_count":I,"economic_wins":O,"economic_win_rate_pct":D}
def _simulate_cash_horizon(start_cash,days_n,scale_up_thr,*,strict_pure_riskless=False,start_date=None):
 b=("P25_CONSERVATIVE","P50_BASE_FINLAND","P75_LONDON_UPSIDE");i={sc:float(start_cash)for sc in b};g=start_date if start_date is not None else datetime.now(timezone.utc).date();k={}
 for d in range(1,max(days_n,365)+1):
  a=.0
  for sc in b:
   j,_,_=simulate_single_day_net_pnl(d,max(10.,i[sc]),sc,scale_up_threshold=scale_up_thr,riskless_only=True,strict_pure_riskless=strict_pure_riskless);i[sc]=round(i[sc]+j,2)
   if sc=="P50_BASE_FINLAND":a=j
  if d in(1,4,7,10,14,21,30,60,90,180,365):h=round(FINLAND_VM_COST_USD_PER_DAY*d,2);f=round(i["P25_CONSERVATIVE"]-float(start_cash),2);e=round(i["P50_BASE_FINLAND"]-float(start_cash),2);c=round(i["P75_LONDON_UPSIDE"]-float(start_cash),2);k[f"day_{d}"]={"date_utc":(g+timedelta(days=d-1)).isoformat(),"p25_equity":i["P25_CONSERVATIVE"],"p50_equity":i["P50_BASE_FINLAND"],"p75_equity":i["P75_LONDON_UPSIDE"],"p50_daily_pnl":a,"p25_net_profit":f,"p50_net_profit":e,"p75_net_profit":c,"vm_cost_cum_usd":h,"p25_net_after_vm_usd":round(f-h,2),"p50_net_after_vm_usd":round(e-h,2),"p75_net_after_vm_usd":round(c-h,2)}
 return k
def _compute_cash_milestone_etas(start_cash,scale_up_thr,*,strict_pure_riskless=False,max_days=540,start_date=None):
 a=("P25_CONSERVATIVE","P50_BASE_FINLAND","P75_LONDON_UPSIDE");f=(100,150,250,253,500,1000,2500,5000,10000);e={f"usd_{m}":{}for m in f};h={sc:float(start_cash)for sc in a};c=start_date if start_date is not None else datetime.now(timezone.utc).date()
 for d in range(1,max_days+1):
  g=(c+timedelta(days=d-1)).isoformat()
  for sc in a:
   i,_,_=simulate_single_day_net_pnl(d,max(10.,h[sc]),sc,scale_up_threshold=scale_up_thr,riskless_only=True,strict_pure_riskless=strict_pure_riskless);h[sc]=round(h[sc]+i,2);b=sc.split("_")[0].lower()
   for m in f:
    j=f"usd_{m}"
    if f"{b}_day"not in e[j]and h[sc]>=float(m):e[j][f"{b}_day"]=d;e[j][f"{b}_date_utc"]=g
 return e
def _load_full_throttle_telemetry():
 f=_load_json(UNIVERSE_COVERAGE_FILE);e=_load_json(FULL_THROTTLE_DASHBOARD_FILE);a=f.get("universe_summary")if isinstance(f,dict)else{}
 if not isinstance(a,dict):a={}
 b=(e.get("universe")or{})if isinstance(e,dict)else{};d=(e.get("opportunity_engine")or{})if isinstance(e,dict)else{};c=(e.get("hedged_maker_shadow")or{})if isinstance(e,dict)else{};return{"total_events":int(a.get("total_events")or b.get("total_events")or 0),"total_markets":int(a.get("total_markets")or b.get("total_markets")or 0),"active_orderbook_markets":int(a.get("active_orderbook_markets")or b.get("active_orderbook_markets")or 0),"total_tokens":int(a.get("total_tokens")or b.get("total_tokens")or 0),"proposition_graph_edges":int(d.get("proposition_graph_edges")or 0),"rule_trap_blocks":int(d.get("rule_trap_blocks")or 0),"dormant_near_arbs":int(d.get("dormant_watchlist_count")or 0),"family_l_shadow_pnl_usd":round(float(c.get("realized_shadow_pnl_usd")or.0),4)}
def build_live_projections(days=90,fallback_equity=75.84,riskless_only=None,strict_pure_riskless=None,live_state_override=None):
 _b=datetime.now(timezone.utc);_a=live_state_override if isinstance(live_state_override,dict)else _load_json(LIVE_STATE_FILE);Z=_load_json(ALPHA124_STATE_FILE);P=_load_json(EXP316_STATE_FILE);_i=_load_json(SOL_SHADOW_FILE);_h=_load_json(XRP_SHADOW_FILE);_g=_load_phase3a_summary(PHASE34_TRACKER_FILE);U=_load_json(RISK_CONFIG_FILE);O=_load_json(STRATEGY_RISK_CONFIG_FILE);_f=_load_full_throttle_telemetry();u=_is_riskless_only_mode_configured(O)if riskless_only is None else bool(riskless_only);r=(u and(_is_strict_pure_riskless_configured(O)if strict_pure_riskless is None else bool(strict_pure_riskless)));T=compute_live_equity_and_rates(_a,fallback_equity=fallback_equity);F=T["live_equity"];q=T["locked_floor_equity"];p=T["liquid_working_cash_usd"];i=T["frozen_single_leg_cost_usd"];K=T["hwm_equity"];B=float(U.get("scale_up_equity_threshold")or 110.);h=min(F,q)if u else F;E=_a.get("reconciled_nav_usd");o=(float(E)if(E is not None and float(E)>.0 and q>=F-.01)else(float(E)if(E is not None and float(E)<F-.01)else q));w=T["economic_trades_count"];N=T["economic_wins"];D=T["economic_win_rate_pct"];A=_parse_iso(Z.get("started_at"));n=(round(max(.0,(_b-A).total_seconds()/86400.),2)if A else 1.);M=Z.get("by_sleeve")or{};J=(P.get("tiers")or{}).get("T1000")or{};l={str(x).upper()for x in((O.get("riskless_boxes")or{}).get("paused_riskless_sleeves")or[])if x};z=[]
 for sp in GRADUATION_SPECS:
  sl=sp["sleeve"]
  if r and sl not in STRICT_PURE_RISKLESS_LIVE_SLEEVES:continue
  if sl in QUARANTINED_SLEEVES or sl.upper()in l:continue
  if u and sl in DIRECTIONAL_ONLY_SLEEVES:continue
  _o=sp["source"]
  if _o=="sol_shadow":a=int(_i.get("total_trades_settled")or 0);g=int(_i.get("winning_trades")or 0);f=int(_i.get("active_open_positions_count")or 0);c=float(_i.get("realized_pnl")or.0)
  elif _o=="phase3a_shadow":a=int(_g.get("closed")or 0);g=int(_g.get("wins")or 0);f=0;c=float(_g.get("pnl_usd")or.0)
  elif _o=="exp316":a=int(J.get("trades")or 0);g=int(J.get("wins")or 0);f=int(P.get("active_positions")or 0);c=float(J.get("net_pnl_usd")or.0)
  else:Y=M.get(sl)or{};a=int(Y.get("closed")or 0);g=int(Y.get("wins")or 0);f=int(Y.get("open")or 0);c=float(Y.get("realized_pnl_t1000_usd")or.0)
  _e=round(1e2*g/a,2)if a>0 else.0;y=_wilson_lcb_pct(g,a);I=round(min(1e2,1e2*a/sp["min_settled"]),1);S=round(min(1e2,1e2*n/sp["min_days"]),1);_m=(a>=sp["min_settled"]and n>=sp["min_days"]and _e>=sp["min_wr_pct"]and y>=max(.0,sp["min_wr_pct"]-20.)and c>.0);z.append({"sleeve":sl,"wave":sp["wave"],"source":_o,"open_now":f,"settled_now":a,"target_settled":sp["min_settled"],"sample_progress_pct":I,"days_elapsed":n,"min_days":sp["min_days"],"time_progress_pct":S,"win_rate_pct":_e,"wilson_lcb90_wr_pct":y,"target_wr_pct":sp["min_wr_pct"],"realized_pnl_t1000_usd":round(c,2),"ready_for_stage1_micro_live":_m})
 L=["P25_CONSERVATIVE","P50_BASE_FINLAND","P75_LONDON_UPSIDE"];R={sc:h for sc in L};H=_b.date();C=max(days,540);t=(100,150,250,253,500,1000,2500,5000,10000);v={f"usd_{m}":{}for m in t};Q=[]
 for d in range(1,C+1):
  _d=(H+timedelta(days=d-1)).isoformat();_n={"day":d,"date_utc":_d};e="";b={}
  for sc in L:
   X=R[sc];s=max(10.,X);_l,_k,_j=simulate_single_day_net_pnl(d,s,sc,scale_up_threshold=B,shadow_by_sleeve=M,sol_shadow=_i,phase3a_shadow=_g,exp316_t1k=J,riskless_only=u,strict_pure_riskless=r);_c=round(X+_l,2);R[sc]=_c;W=sc.split("_")[0].lower();_n[f"{W}_daily_pnl_usd"]=_l;_n[f"{W}_end_equity_usd"]=_c
   for m in t:
    mk=f"usd_{m}"
    if f"{W}_day"not in v[mk]and _c>=float(m):v[mk][f"{W}_day"]=d;v[mk][f"{W}_date_utc"]=_d
   if sc=="P50_BASE_FINLAND":e=_j;b=_k;_n["p50_post_vm_daily_net_usd"]=round(_l-FINLAND_VM_COST_USD_PER_DAY,2);_n["p50_v393_ticket_usd"]=.0 if u else compute_v541_ticket_size(X)
  _n["active_regime_and_milestone"]=e;_n["p50_sleeve_pnl_breakdown_usd"]=b;Q.append(_n)
 G=Q[:days];j=bool(F-q>.05);V={"generated_at_utc":_b.isoformat(),"model_version":("v6.2.0_strict_pure_riskless_math_dominance_only"if r else("v5.2_full_throttle_riskless_velocity"if u else"v5.4.1_high_z_sniper_plus_unleashed_zero_loss_boxes")),"riskless_only_mode":u,"strict_pure_riskless_mode":r,"strict_pure_riskless_firewall_enabled":bool(((O.get("riskless_boxes"))or{}).get("strict_pure_riskless_mode",False)),"row2_post_clinch_carries_enabled":bool(((O.get("riskless_boxes"))or{}).get("enable_single_leg_maker_bond1",True)),"vm_infra_cost_usd_per_month":FINLAND_VM_COST_USD_PER_MONTH,"vm_infra_cost_usd_per_day":FINLAND_VM_COST_USD_PER_DAY,"quarantined_sleeves_excluded":sorted(QUARANTINED_SLEEVES),"anchor_live_state":{"live_equity_usd":round(h,2),"reconciled_floor_nav_usd":round(q,2),"mark_to_bid_nav_usd":round(o,2),"persisted_book_equity_usd":round(F,2),"compounding_anchor_equity_usd":round(h,2),"liquid_working_cash_usd":round(p,2),"frozen_single_leg_cost_usd":round(i,2),"locked_box_payout_floor_equity_usd":round(q,2),"high_water_mark_usd":round(K,2),"vm_infra_cost_usd_per_day":FINLAND_VM_COST_USD_PER_DAY,"vm_breakeven_bps_per_hr":round((FINLAND_VM_COST_USD_PER_DAY/max(1.,h))*1e4/24.,2),"riskless_only_mode":u,"strict_pure_riskless_mode":r,"current_v393_ticket_usd":.0 if u else compute_v541_ticket_size(h),"current_v540_btc_ticket_usd":.0 if u else round(min(2e2,h*(.22 if h<98. else.26)),2),"current_v540_eth_sol_ticket_usd":.0 if u else round(min(170.,h*(.22 if h<98. else.26)*.85),2),"current_cancel_on_arb_max_sweep_usd":round(min(45.,max(20.,h*.88)),2),"distance_to_125_reward_carry_unlock_usd":round(max(.0,125.-h),2),"distance_to_140_presplit_overround_unlock_usd":round(max(.0,140.-h),2),"distance_to_88_dynamic_sizing_usd":round(max(.0,88.-h),2),"distance_to_98_hyper_growth_usd":round(max(.0,98.-h),2),"distance_to_110_slot2_unlock_usd":round(max(.0,110.-h),2),"distance_to_150_slot3_unlock_usd":round(max(.0,150.-h),2),"distance_to_253_scale_tier_usd":round(max(.0,253.-h),2),"distance_to_500_multileg_tier_usd":round(max(.0,5e2-h),2),"distance_to_1003_institutional_tier_usd":round(max(.0,1003.-h),2),"live_closed_trades":w,"live_closed_legs":T["closed_legs_count"],"live_wins":N,"live_win_rate_pct":D,"alpha124_markets_monitored":Z.get("markets_monitored",{}),"alpha124_catalog_counts":Z.get("catalog_counts",{}),"alpha124_open_shadow_positions":Z.get("open_positions_count",0),"alpha124_resting_maker_bids":Z.get("pending_maker_orders_count",0),"full_throttle_universe_telemetry":_f,"sol_shadow_settled":_i.get("total_trades_settled",0),"sol_shadow_win_rate_pct":_i.get("win_rate_pct",.0),"phase3a_maker_settled":_g.get("closed",0),"xrp_shadow_settled":_h.get("total_trades_settled",0)},"summary_horizons_usd":{f"day_{k}":{"date_utc":Q[k-1]["date_utc"],"p25_equity":Q[k-1]["p25_end_equity_usd"],"p50_equity":Q[k-1]["p50_end_equity_usd"],"p75_equity":Q[k-1]["p75_end_equity_usd"],"p50_daily_pnl":Q[k-1]["p50_daily_pnl_usd"],"p25_net_profit":round(Q[k-1]["p25_end_equity_usd"]-h,2),"p50_net_profit":round(Q[k-1]["p50_end_equity_usd"]-h,2),"p75_net_profit":round(Q[k-1]["p75_end_equity_usd"]-h,2),"vm_cost_cum_usd":round(FINLAND_VM_COST_USD_PER_DAY*k,2),"p25_net_after_vm_usd":round((Q[k-1]["p25_end_equity_usd"]-h)-FINLAND_VM_COST_USD_PER_DAY*k,2),"p50_net_after_vm_usd":round((Q[k-1]["p50_end_equity_usd"]-h)-FINLAND_VM_COST_USD_PER_DAY*k,2),"p75_net_after_vm_usd":round((Q[k-1]["p75_end_equity_usd"]-h)-FINLAND_VM_COST_USD_PER_DAY*k,2)}for k in(1,4,7,10,14,21,30,60,90,180,365)if k<=len(Q)},"milestone_eta_days":v,"post_nov14_miami_scenarios_usd":{"favorable_86_87f_payout_52usd":{"starting_liquid_cash_usd":round(h+(52. if j else.0),2),"horizons":_simulate_cash_horizon(h+(52. if j else.0),days,B,strict_pure_riskless=r,start_date=H),"milestone_eta_days":_compute_cash_milestone_etas(h+(52. if j else.0),B,strict_pure_riskless=r,start_date=H)},"adverse_zero_payout_0usd":{"starting_liquid_cash_usd":round(h,2),"requires_circuit_breaker_floor_ack_below_48usd":bool(h<48.),"horizons":_simulate_cash_horizon(h,days,B,strict_pure_riskless=r,start_date=H),"milestone_eta_days":_compute_cash_milestone_etas(h,B,strict_pure_riskless=r,start_date=H)}},"production_reconciled_48_70_floor_reference_usd":{"adverse_floor_48_70_usd":{"starting_floor_nav_usd":48.7,"horizons":_simulate_cash_horizon(48.7,days,B,strict_pure_riskless=r,start_date=H),"milestone_eta_days":_compute_cash_milestone_etas(48.7,B,strict_pure_riskless=r,start_date=H)},"favorable_kmia_100_70_usd":{"starting_floor_nav_usd":100.7,"horizons":_simulate_cash_horizon(100.7,days,B,strict_pure_riskless=r,start_date=H),"milestone_eta_days":_compute_cash_milestone_etas(100.7,B,strict_pure_riskless=r,start_date=H)}},"p75_jurisdiction_compliance_note":("P75 models lawful low-latency EU execution (~8-12ms RTT in Group-2 API-open regions such as GCP europe-west4 Netherlands or AWS eu-west-1 Dublin after verifying live POST /order via check_polymarket_region_latency.py --verify-post-only, while keeping manual Web UI access on Group-1 Finland europe-north1; or ~22-25ms RTT in Group-1 Stockholm europe-north2). Regulated cross-venue Stage G ($253+) uses strictly CA-ON-legal venues (ForecastEx / IBKR Canada + STX Ontario) with 0% proxy/VPN spoofing."),"live_riskless_funnel":_a.get("live_riskless_funnel",{}),"sleeve_graduation_live_tracker":z,"day_by_day_schedule":G};return V
def write_live_projections_atomic(days=90):a=build_live_projections(days=days);OUTPUT_JSON_FILE.parent.mkdir(parents=True,exist_ok=True);b=OUTPUT_JSON_FILE.with_suffix(".tmp");b.write_text(json.dumps(a,indent=2),encoding="utf-8");os.replace(b,OUTPUT_JSON_FILE);return a
def print_human_scorecard(payload):
 c=payload["anchor_live_state"];print(f"=== DOMINUS POLYMARKET LIVE DAY-BY-DAY PROJECTIONS [{payload.get('model_version')}] ({payload['generated_at_utc']}) ===")
 if payload.get("riskless_only_mode"):print(f"Anchor Floor NAV: ${c['reconciled_floor_nav_usd']:.2f} (MTM ${c['mark_to_bid_nav_usd']:.2f} | Book ${c['persisted_book_equity_usd']:.2f} | HWM ${c['high_water_mark_usd']:.2f}) | Live Epoch: {c['live_wins']}W/{c['live_closed_trades']-c['live_wins']}L ({c['live_win_rate_pct']:.1f}% WR) | To $125 Reward: ${c['distance_to_125_reward_carry_unlock_usd']:.2f} | To $140 Pre-Split: ${c['distance_to_140_presplit_overround_unlock_usd']:.2f}")
 else:print(f"Anchor Live Equity: ${c['live_equity_usd']:.2f} (HWM ${c['high_water_mark_usd']:.2f}) | Live Epoch: {c['live_wins']}W/{c['live_closed_trades']-c['live_wins']}L ({c['live_win_rate_pct']:.1f}% WR) | To $88 Dynamic: ${c['distance_to_88_dynamic_sizing_usd']:.2f} | To $110 Slot-2: ${c['distance_to_110_slot2_unlock_usd']:.2f}")
 print("\n--- Clean Active Shadow Sleeve Graduation Readiness (Quarantined Sleeves Excluded) ---")
 for g in payload["sleeve_graduation_live_tracker"]:a="READY"if g["ready_for_stage1_micro_live"]else"WAIT ";print(f"  [{a}] {g['sleeve']:28s} | {g['wave']:22s} | Settled={g['settled_now']:2d}/{g['target_settled']:2d} (Open={g['open_now']:2d}) | WR={g['win_rate_pct']:6.1f}% (req>={g['target_wr_pct']:5.1f}%) | Ref PnL=${g['realized_pnl_t1000_usd']:+7.2f}")
 b=payload["day_by_day_schedule"];print(f"\n--- {len(b)}-Day Reconciled-Floor-Anchored Compounding Schedule (Depth-Capped, Non-Cash Model) ---");print("Day | Date       | P25 Eq ($) | P50 Base Eq ($) | P50 Day PnL | P75 LowLat ($) | Active Regime / Graduation Milestone");print("-"*122)
 for r in b[:30]:print(f"D{r['day']:02d} | {r['date_utc']} | ${r['p25_end_equity_usd']:9.2f} | ${r['p50_end_equity_usd']:14.2f} | ${r['p50_daily_pnl_usd']:+10.2f} | ${r['p75_end_equity_usd']:13.2f} | {r['active_regime_and_milestone']}")
def main():
 b=argparse.ArgumentParser(description="Live Polymarket Day-by-Day Projections & Graduation Tracker");b.add_argument("--days",type=int,default=90,help="Projection horizon in days");b.add_argument("--json-only",action="store_true",help="Print JSON payload instead of ASCII table");c=b.parse_args();a=write_live_projections_atomic(days=c.days)
 if c.json_only:print(json.dumps(a,indent=2))
 else:print_human_scorecard(a)
if __name__=="__main__":main()
# ======================================================================================
# [19/20] MODULE: scripts/alpha124_status.py
# PURPOSE: Live Alpha-124 Multi-Sleeve Scorecard & Orderbook Opportunity Inspector
# ======================================================================================

import json;from pathlib import Path;PROJECT_ROOT=Path(__file__).resolve().parent.parent;STATE_FILE=PROJECT_ROOT/"data"/"alpha124"/"alpha124_shadow_state.json";OPPS_FILE=PROJECT_ROOT/"data"/"alpha124"/"alpha124_live_opportunities.json"
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
# [20/20] MODULE: scripts/polymarket_scorecard_snapshot.py
# PURPOSE: Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot
# ======================================================================================

import json;import os;import pathlib;import subprocess;ROOT=pathlib.Path("/home/skybullet1987/quant_pipeline");SERVICES=["polymarket-live-harvester","polymarket-alpha124-shadow","polymarket-trader","polymarket-exp316-shadow","polymarket-recorder","polymarket-recorder-eth","polymarket-recorder-sol","polymarket-recorder-xrp"]
def _read_json(rel_path):
 p=ROOT/rel_path
 if not p.exists():return{}
 try:return json.loads(p.read_text(encoding="utf-8"))
 except Exception as a:return{"error":str(a)}
def main():
 p=dict(os.environ)
 if hasattr(os,"getuid"):p.setdefault("XDG_RUNTIME_DIR",f"/run/user/{os.getuid()}")
 d={s:subprocess.run(["systemctl","--user","is-active",s],capture_output=True,text=True,env=p).stdout.strip()for s in SERVICES};l=_read_json("data/polymarket/live_harvester_state.json");c=_read_json("data/alpha124/alpha124_shadow_state.json");j=_read_json("data/polymarket/live_daily_projections.json");h=_read_json("data/polymarket/paper_trader_state.json");o=_read_json("data/polymarket/state_shadow_sol_v392.json");n=_read_json("data/polymarket/state_shadow_xrp_v392.json");f=_read_json("data/exp316/exp316_shadow_state.json");e=l.get("closed_positions")or[];i=sum(1 for t in e if float(t.get("realized_pnl_usd")or t.get("net_pnl_usd")or(float(t.get("realized_exit_cash",.0))-float(t.get("notional_usd",.0))-float(t.get("fee_usd",.0))))>0);g=subprocess.run(["journalctl","--user","-u","polymarket-live-harvester","--since","24 hours ago","--no-pager"],capture_output=True,text=True,env=p).stdout.splitlines();m=[line for line in g if"SHADOW_PHASE3A"in line][-5:];q=[line for line in g if"SHADOW_PHASE4"in line][-5:];b=["timestamp","current_equity","realized_pnl","total_trades_settled","winning_trades","losing_trades","win_rate_pct","profit_factor","active_open_positions_count","ready_for_live_graduation","graduation_criteria"];a={"services":d,"all_services_active":all(v=="active"for v in d.values()),"live_v392":{"updated_at_utc":l.get("updated_at_utc"),"live_bankroll_usd":l.get("live_bankroll"),"total_account_equity_usd":l.get("total_account_equity"),"high_water_mark_equity_usd":l.get("high_water_mark_equity"),"active_positions_count":l.get("active_positions_count"),"closed_positions_count":len(e),"closed_wins":i,"progress_to_n40_gate":f"{len(e)}/40","distance_to_88_dynamic_tier_usd":round(max(.0,88.-float(l.get("total_account_equity")or.0)),2),"distance_to_110_scaleup_tier_usd":round(max(.0,110.-float(l.get("total_account_equity")or.0)),2),"risk_halt":l.get("risk_halt"),"reconciliation_required":l.get("reconciliation_required"),"global_halt_reasons":l.get("global_halt_reasons")},"alpha124_11sleeve_shadow":{"updated_at_utc":c.get("updated_at_utc"),"markets_monitored":c.get("markets_monitored"),"open_positions_count":c.get("open_positions_count"),"pending_maker_orders_count":c.get("pending_maker_orders_count"),"portfolio_realized_pnl_by_bankroll_usd":c.get("portfolio_realized_pnl_by_bankroll_usd"),"by_sleeve":c.get("by_sleeve")},"live_daily_projections_summary":j.get("summary_horizons_usd",{}),"paper_sleeve1_benchmark":h.get("validation_oos_epoch",{}),"shadow_sol_v392":{k:o.get(k)for k in b},"shadow_xrp_v392":{k:n.get(k)for k in b},"shadow_exp316":f,"shadow_phase3a_recent_24h":m,"shadow_phase4_recent_24h":q};print(json.dumps(a,indent=2))
if __name__=="__main__":main()

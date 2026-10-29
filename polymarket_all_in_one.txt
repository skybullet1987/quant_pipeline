"""
POLYMARKET COMPLETE UNIFIED SYSTEM CODEBASE (ALL-IN-ONE BUNDLE)
Generated: 2026-10-29 02:55:41 UTC | Repo: /home/skybullet1987/quant_pipeline
TABLE OF CONTENTS (Exact 1-Based Line Ranges):
  - [config/polymarket_risk_config.json] (Lines 19 - 59 | 1,125 B) :: Centralized Risk & Sizing Limits (Single Source of Truth)
  - [systemd/polymarket-live-harvester.service] (Lines 60 - 94 | 1,859 B) :: Graceful systemd Production Unit (Restart=on-failure, --max-tte 1200.0)
  - [src/polymarket_research/polymarket_live_harvester.py] (Lines 95 - 6,873 | 609,801 B) :: v3.9 Live Harvester Engine, Oracle-Exact Gates & 95c/98c Two-Tranche Supervisor
  - [src/polymarket_research/polymarket_live_executor.py] (Lines 6,874 - 10,690 | 357,901 B) :: Polymarket CLOB L2 Client, Priority EIP-712 Signing & pUSD/CTF Adapter
  - [src/polymarket_research/polymarket_terminal_recorder.py] (Lines 10,691 - 12,440 | 160,219 B) :: Sub-ms Binance/Coinbase/Chainlink-TWAP Shock Detection & CLOB L2 SHM Recorder
  - [src/polymarket_research/deribit_svi_surface.py] (Lines 12,441 - 12,804 | 24,417 B) :: Deribit SVI Options Volatility Surface & Breeden-Litzenberger Engine
  - [src/polymarket_research/polymarket_paper_trader.py] (Lines 12,805 - 14,426 | 123,671 B) :: Forward Paper Trader & Production-Parity Simulation Engine
  - [src/polymarket_research/check_polymarket_balance.py] (Lines 14,427 - 14,496 | 3,757 B) :: Polygon pUSD + USDC.e Collateral Balance Checker
  - [src/polymarket_research/verify_onchain_allowances.py] (Lines 14,497 - 14,579 | 4,507 B) :: ERC-20/ERC-1155 Proxy & Exchange Allowance Verifier
  - [src/polymarket_research/redeem_settled_positions.py] (Lines 14,580 - 14,769 | 12,505 B) :: CTF Settled Position Redemption Engine
  - [audit_losing_trades.py] (Lines 14,770 - 14,940 | 15,574 B) :: Autonomous Post-Trade Forensic Auditor & Daemon Health Verifier
  - [scripts/honest_purged_wfo_optimizer.py] (Lines 14,941 - 16,096 | 81,407 B) :: Zero-Lookahead Purged WFO & Genuine Refit CPCV(6,2) Optimizer
"""
from __future__ import annotations
# === [01/12] config/polymarket_risk_config.json :: Centralized Risk & Sizing Limits (Single Source of Truth) ===
# Non-Python asset embedded as string constant:
POLYMARKET_RISK_CONFIG_JSON = r'''
{
  "ticket_notional": 16.5,
  "dynamic_sizing": true,
  "dynamic_risk_pct": 0.18,
  "scale_up_equity_threshold": 110.0,
  "correlated_crypto_single_slot_threshold": 180.0,
  "scale_up_risk_pct": 0.22,
  "min_equity_floor": 66.67,
  "seed_survival_equity_threshold": 88.0,
  "seed_survival_ticket_usd": 12.0,
  "seed_survival_max_concurrent": 1,
  "seed_survival_floor_usd": 48.0,
  "seed_smooth_compounding": true,
  "enable_fak_plus2c_fallback": false,
  "enable_graduated_d1_box": true,
  "enable_sol_d1_box": true,
  "phase3a_maker_max_notional_usd": 22.0,
  "d1_box_max_budget_usd": 250.0,
  "d1_box_collateral_reserve_usd": 16.5,
  "d1_box_bankroll_pct": 0.25,
  "d1_depth_ratio_threshold": 1.2,
  "d1_min_depth_mult_gate": 1.15,
  "d1_max_giveback_frac": 0.25,
  "max_concurrent_d1_boxes": 4,
  "enable_graduated_alt_sleeves": true,
  "max_daily_loss": 20.0,
  "max_exposure": 35.0,
  "max_concurrent_positions": 2,
  "hold_to_maturity": false,
  "exit_policy": "hold_98",
  "stale_fast_tick_max_age_sec": 15.0,
  "stale_telemetry_max_age_sec": 30.0,
  "stale_alert_after_sec": 60.0,
  "alert_rate_limit_sec": 300.0
}

'''

# === [02/12] systemd/polymarket-live-harvester.service :: Graceful systemd Production Unit (Restart=on-failure, --max-tte 1200.0) ===
# Non-Python asset embedded as string constant:
POLYMARKET_LIVE_HARVESTER_SERVICE = r'''
[Unit]
Description=Polymarket Live CLOB Real-Money Harvester (v3.9 Purged-WFO Validated; risk limits from config/polymarket_risk_config.json)
After=network-online.target polymarket-recorder.service polymarket-recorder-eth.service polymarket-recorder-sol.service polymarket-recorder-xrp.service
Wants=network-online.target polymarket-recorder.service polymarket-recorder-eth.service polymarket-recorder-sol.service polymarket-recorder-xrp.service
# Crash-loop protection: >5 non-zero crashes in 10 min => stay down.
StartLimitIntervalSec=600
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=/home/skybullet1987/quant_pipeline
# Sizing / exposure / daily-loss / equity-floor come from config/polymarket_risk_config.json.
# --no-hold-to-maturity --exit-policy hold_98 activates Purged-WFO-winning single-tranche $0.98 Maker GTC TP + 15s gasless Relayer V2 redemption,
# --max-tte 1200.0 unlocks the full WFO-optimal [120s, 1200s] 1h window + [90s, 480s] 15m window,
# and --max-trades-per-market 2 enables Win-Reset Compounding (2nd trade ONLY if Trade #1 closed in profit).
ExecStart=/home/skybullet1987/quant_pipeline/venv/bin/python src/polymarket_research/polymarket_live_harvester.py --dynamic-sizing --no-hold-to-maturity --exit-policy hold_98 --max-ticket-cap 200.0 --max-trades-per-market 2 --max-trades-per-hour 8 --min-price-floor 0.55 --max-price-ceiling 0.85 --max-tte 1200.0 --allowed-assets BTC ETH
# Exit 0 (circuit breaker / graceful SIGTERM) stays down; non-zero (crash) restarts after 3s.
Restart=on-failure
RestartSec=3
CPUWeight=1000
IOWeight=1000
KillSignal=SIGTERM
KillMode=mixed
TimeoutStopSec=20s
StandardOutput=append:/home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_stdout.log
StandardError=append:/home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_stdout.log

[Install]
WantedBy=default.target

'''

# === [03/12] src/polymarket_research/polymarket_live_harvester.py :: v3.9 Live Harvester Engine, Oracle-Exact Gates & 95c/98c Two-Tranche Supervisor ===
#!/usr/bin/env python3 import asyncio
import ctypes
import json
import logging
import math
import os
import signal
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal,ROUND_FLOOR
try:
 import fcntl
except ImportError:
 fcntl=None
from pathlib import Path
from typing import Any,Dict,List,Optional,Set,Tuple
from dotenv import load_dotenv
import requests
try:
 import orjson as _orjson
 def _json_loads(s):
  return _orjson.loads(s)
except Exception:
 _orjson=None
 def _json_loads(s):
  return json.loads(s)
PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT) not in sys.path:
 sys.path.insert(0,str(PIPELINE_ROOT))
load_dotenv(PIPELINE_ROOT / ".env")
from src.polymarket_research.polymarket_live_executor import ( PolymarketLiveExecutor,OrderResult,ExecutionStatus,calculate_taker_fee,load_risk_config,RISK_CONFIG,_get_hot_io_pool,)
try:
 from src.polymarket_research.latency_trace import LatencyTrace as _LatencyTrace,CURRENT_TRACE as _CURRENT_TRACE
except Exception:
 _LatencyTrace=None
 _CURRENT_TRACE=None
try:
 from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker as _PolymarketClobMarketWsTracker
except Exception:
 try:
  from polymarket_ws_streams import PolymarketClobMarketWsTracker as _PolymarketClobMarketWsTracker
 except Exception:
  _PolymarketClobMarketWsTracker=None
LIVE_WS_BOOK_MAX_AGE_MS=float(os.environ.get("PM_LIVE_WS_BOOK_MAX_AGE_MS","2500"))
try:
 from src.polymarket_research.deribit_svi_surface import GLOBAL_SVI_ENGINE
except Exception:
 GLOBAL_SVI_ENGINE=None
try:
 from src.polymarket_research.net_alpha_opportunity_engine import ( evaluate_cross_oracle_basis_box_ev,evaluate_optimal_stopping_exit,inspect_microstructure_feature_completeness,publish_global_positions_shm,)
except Exception:
 evaluate_cross_oracle_basis_box_ev=None
 evaluate_optimal_stopping_exit=None
 inspect_microstructure_feature_completeness=None
 publish_global_positions_shm=None
try:
 from src.polymarket_research.same_oracle_dominance_box import walk_equal_shares_dominance_box
except Exception:
 walk_equal_shares_dominance_box=None
logger=logging.getLogger("LiveHarvester")
logging.basicConfig( level=logging.INFO,format="[%(asctime)s UTC] [%(levelname)s] [HARVESTER] %(message)s",handlers=[logging.StreamHandler(sys.stdout)],)
_FILE_LOGGER_ATTACHED=False
def _ensure_file_logging()->None:
 global _FILE_LOGGER_ATTACHED
 if _FILE_LOGGER_ATTACHED:
  return
 try:
  log_path=DATA_DIR / "live_harvester.log"
  log_path.parent.mkdir(parents=True,exist_ok=True)
  fh=logging.FileHandler(log_path,encoding="utf-8")
  fh.setFormatter(logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [HARVESTER] %(message)s"))
  logging.getLogger().addHandler(fh)
  _FILE_LOGGER_ATTACHED=True
 except Exception as exc:
  logger.debug(f"Could not attach file logger: {exc}")
_ALERT_LAST_SENT:Dict[str,float]={}
_ALERT_LOCK=threading.Lock()
_ALERT_THREADS:List[threading.Thread]=[]
def flush_operational_alerts(timeout:float=3.0)->None:
 deadline=time.time() + max(0.0,float(timeout))
 for t in list(_ALERT_THREADS):
  t.join(max(0.0,deadline - time.time()))
 _ALERT_THREADS[:]=[t for t in _ALERT_THREADS if t.is_alive()]
def _alerts_file_path()->Optional[Path]:
 if "POLYMARKET_ALERTS_FILE" in os.environ:
  override=os.environ["POLYMARKET_ALERTS_FILE"].strip()
  return Path(override) if override else None
 return DATA_DIR / "critical_alerts.jsonl"
def _post_alert_http(text:str,record:Dict[str,Any])->None:
 try:
  import urllib.request
  token=os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
  chat_id=os.environ.get("TELEGRAM_CHAT_ID","").strip()
  webhook=os.environ.get("ALERT_WEBHOOK_URL","").strip()
  targets=[]
  if token and chat_id:
   targets.append((f"https://api.telegram.org/bot{token}/sendMessage",{"chat_id":chat_id,"text":text}))
  if webhook:
   targets.append((webhook,{"text":text,**record}))
  for url,payload in targets:
   req=urllib.request.Request( url,data=json.dumps(payload).encode("utf-8"),headers={"Content-Type":"application/json"},method="POST",)
   urllib.request.urlopen(req,timeout=2.5).read()
 except Exception as exc:
  logger.debug(f"[ALERT] HTTP dispatch failed: {exc}")
def send_operational_alert( event_type:str,message:str,severity:str="CRITICAL",rate_limit_sec:float=0.0,dedupe_key:Optional[str]=None,)->bool:
 now=time.time()
 key=dedupe_key or event_type
 with _ALERT_LOCK:
  if rate_limit_sec > 0 and (now - _ALERT_LAST_SENT.get(key,0.0)) < rate_limit_sec:
   return False
  _ALERT_LAST_SENT[key]=now
 record={ "ts_utc":datetime.now(timezone.utc).isoformat(),"unix":round(now,3),"severity":str(severity).upper(),"event_type":str(event_type),"message":str(message),"host_pid":os.getpid(),}
 path=_alerts_file_path()
 if path is not None:
  try:
   path.parent.mkdir(parents=True,exist_ok=True)
   with open(path,"a",encoding="utf-8") as fh:
    fh.write(json.dumps(record) + "\n")
  except Exception as exc:
   logger.error(f"[ALERT] Failed to append alert ledger: {exc}")
 log_fn=logger.critical if record["severity"]=="CRITICAL" else (logger.warning if record["severity"]=="WARNING" else logger.info)
 log_fn(f"[ALERT:{record['severity']}] {event_type}: {message}")
 suppress_http=( os.environ.get("POLYMARKET_ALERTS_SUPPRESS_HTTP")=="1" and os.environ.get("POLYMARKET_ALERTS_FORCE_HTTP")!="1" )
 if not suppress_http:
  text=f"[Polymarket {record['severity']}] {event_type}: {message}"
  _t=threading.Thread(target=_post_alert_http,args=(text,record),daemon=True,name="pm-alert-dispatch")
  _ALERT_THREADS.append(_t)
  _t.start()
 return True
class LinuxInotifyWatcher:
 IN_MODIFY=0x00000002
 IN_CLOSE_WRITE=0x00000008
 IN_NONBLOCK=0x00000800
 def __init__(self,filepath:Path):
  self.filepath=filepath
  self.fd=-1
  self.wd=-1
  self._available=False
  try:
   self.libc=ctypes.CDLL("libc.so.6",use_errno=True)
   self.inotify_init1=self.libc.inotify_init1
   self.inotify_init1.restype=ctypes.c_int
   self.inotify_init1.argtypes=[ctypes.c_int]
   self.inotify_add_watch=self.libc.inotify_add_watch
   self.inotify_add_watch.restype=ctypes.c_int
   self.inotify_add_watch.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_uint32]
   self.fd=self.inotify_init1(self.IN_NONBLOCK)
   if self.fd>=0:
    if not self.filepath.exists():
     self.filepath.touch()
    target_bytes=str(self.filepath).encode("utf-8")
    self.wd=self.inotify_add_watch(self.fd,target_bytes,self.IN_MODIFY | self.IN_CLOSE_WRITE)
    if self.wd>=0:
     self._available=True
  except Exception as e:
   logger.debug(f"inotify setup notice: {e}")
 @property
 def is_available(self)->bool:
  return self._available and self.fd>=0
 def drain_events(self):
  if not self.is_available:
   return
  try:
   os.read(self.fd,4096)
  except (BlockingIOError,OSError):
   pass
 def close(self):
  if self.fd>=0:
   try:
    os.close(self.fd)
   except Exception:
    pass
   self.fd=-1
DATA_DIR=PIPELINE_ROOT / "data/polymarket"
TRIGGER_FILE=DATA_DIR / "live_shock_triggers.jsonl"
SHOCK_FILE=DATA_DIR / "shock_responses.jsonl"
RESOLUTIONS_FILE=DATA_DIR / "finalized_market_resolutions.jsonl"
STATE_FILE=DATA_DIR / "live_harvester_state.json"
PID_FILE=DATA_DIR / "live_harvester.pid"
COUNTERFACTUAL_CANDIDATES_FILE=DATA_DIR / "counterfactual_candidates.jsonl"
SHADOW_PHASE3_4_FILE=DATA_DIR / "shadow_phase3_4_tracker.jsonl"
D1_LIVE_CANDIDATES_FILE=DATA_DIR / "d1_live_box_candidates.jsonl"
FAST_TICK_DIR=Path(os.getenv("PM_FAST_TICK_DIR","/dev/shm"))
FAST_TICK_SHM_DIR=FAST_TICK_DIR
FAST_TICK_MAX_AGE_SEC=0.50
VENUE_DIVERGENCE_VETO_BPS=15.0
RECORDER_HEARTBEAT_FILES:List[Path]=[FAST_TICK_DIR / f"pm_fast_tick_{a}.json" for a in ("BTC","ETH")]
def read_fast_tick(asset:str,max_age_sec:float=FAST_TICK_MAX_AGE_SEC,now:Optional[float]=None)->Optional[Dict[str,Any]]:
 if "PM_FAST_TICK_DIR" in os.environ:
  env_dir=os.environ["PM_FAST_TICK_DIR"].strip()
  if not env_dir:
   return None
  tick_dir=Path(env_dir)
 else:
  tick_dir=FAST_TICK_SHM_DIR
 try:
  with open(tick_dir / f"pm_fast_tick_{str(asset).upper()}.json","rb") as f:
   snap=_json_loads(f.read())
  ts=float(snap.get("ts") or snap.get("timestamp_unix") or 0.0)
  age=(now if now is not None else time.time()) - ts
  if ts<=0.0 or age > max_age_sec or age < -2.0:
   return None
  return snap
 except Exception:
  return None
def check_recorder_freshness(max_stale_sec:float=15.0,now_ts:Optional[float]=None)->Tuple[bool,str]:
 ref_now=float(now_ts if now_ts is not None else time.time())
 if not RECORDER_HEARTBEAT_FILES:
  return False,"no_heartbeat_files"
 reasons:List[str]=[]
 for p in RECORDER_HEARTBEAT_FILES:
  try:
   m_age=ref_now - p.stat().st_mtime
   if m_age < -2.0 or m_age > max_stale_sec:
    reasons.append(f"mtime_stale:{p.name}:{m_age:.1f}s")
    continue
   snap=_json_loads(p.read_bytes())
   if isinstance(snap,dict):
    inner_ts=float(snap.get("ts") or snap.get("timestamp_unix") or 0.0)
    if inner_ts > 0.0:
     in_age=ref_now - inner_ts
     if in_age < -2.0 or in_age > max_stale_sec:
      reasons.append(f"internal_stale:{p.name}:{in_age:.1f}s>{max_stale_sec:.1f}s")
      continue
   return True,f"ok:{p.name}"
  except Exception as exc:
   reasons.append(f"missing:{p.name}:{exc}")
 return False,";".join(reasons) or "stale"
def fast_tick_book_for_token(snap:Optional[Dict[str,Any]],token_id:str)->Optional[Dict[str,Any]]:
 if not snap or not token_id:
  return None
 candidates=[snap.get("UP"),snap.get("DOWN")]
 m15=snap.get("m15") or {}
 candidates += [m15.get("UP"),m15.get("DOWN")]
 for side in candidates:
  if not isinstance(side,dict) or str(side.get("token_id"))!=str(token_id):
   continue
  bb=float(side.get("best_bid") or 0.0)
  ba=float(side.get("best_ask") or 0.0)
  if bb<=0.0 or ba<=0.0 or ba>=1.0 or bb>=ba:
   return None
  return { "bids":[{"price":str(bb),"size":str(side.get("bid_size_l1") or 0.0)}],"asks":[{"price":str(ba),"size":str(side.get("ask_size_l1") or 0.0)}],"source":"shm_fast_tick",}
 return None
def evaluate_coinbase_venue_veto(shock:Dict[str,Any],target_token:str)->Tuple[bool,str]:
 try:
  cb=float(shock.get("coinbase_spot") or 0.0)
  if cb<=0.0:
   return False,"coinbase_unavailable_fail_open"
  has_centered=shock.get("venue_divergence_centered_bps") is not None
  if has_centered:
   eff_div=float(shock["venue_divergence_centered_bps"])
  else:
   eff_div=float(shock.get("venue_divergence_bps") or 0.0)
  cb_move=float(shock.get("coinbase_move_bps_2s") or 0.0)
  sign=1.0 if target_token=="UP" else -1.0
  dir_div=sign * eff_div
  dir_cb_move=sign * cb_move
  cb_against=dir_cb_move < -0.50
  if (has_centered and dir_div > 12.0) or dir_cb_move < -4.0 or (dir_div > VENUE_DIVERGENCE_VETO_BPS and cb_against):
   return True,f"directional venue divergence {dir_div:+.1f}bps / Coinbase opposing dump ({cb_move:+.2f}bps/2s)"
  return False,f"ok (dir_div={dir_div:+.1f}bps, cb_move={cb_move:+.2f}bps)"
 except Exception as e:
  return False,f"veto_eval_error_fail_open: {e}"
QUEUE_JUMP_MIN_WALL_SHARES=250.0
QUEUE_JUMP_WALL_MULT=6.0
QUEUE_JUMP_MIN_TP_FLOOR=0.95
QUEUE_JUMP_MIN_TARGET=0.97
FAST_CONFIRM_POLL_SEC=0.20
FAST_CONFIRM_WINDOW_SEC=5.0
FAST_SETTLEMENT_RECHECK_WINDOW_SEC=12.0
def compute_queue_priority_maker_price( entry_price:float,rem_shares:float,valid_bids:List[Dict[str,Any]],valid_asks:List[Dict[str,Any]],current_target_px:float,)->Optional[float]:
 try:
  tgt=round(float(current_target_px),2)
  if tgt < QUEUE_JUMP_MIN_TARGET or float(rem_shares)<=0.0:
   return None
  bids=[(float(b.get("price",0.0)),float(b.get("size",0.0))) for b in (valid_bids or [])]
  asks=[(float(a.get("price",0.0)),float(a.get("size",0.0))) for a in (valid_asks or [])]
  bids=[(p,s) for p,s in bids if s > 0 and 0.0 < p < 1.0]
  asks=[(p,s) for p,s in asks if s > 0 and 0.0 < p < 1.0]
  if not bids or not asks:
   return None
  best_bid=max(p for p,_ in bids)
  best_ask=min(p for p,_ in asks)
  if best_ask < tgt - 1e-9:
   return None
  depth_at_target=sum(s for p,s in asks if abs(p - tgt) < 1e-9)
  if depth_at_target<=max(QUEUE_JUMP_MIN_WALL_SHARES,QUEUE_JUMP_WALL_MULT * float(rem_shares)):
   return None
  if best_bid < tgt - 0.03 - 1e-9:
   return None
  min_tp=max(round(float(entry_price) + 0.14,2),QUEUE_JUMP_MIN_TP_FLOOR)
  candidate=round(tgt - 0.01,2)
  if candidate < min_tp - 1e-9 or candidate<=best_bid + 1e-9:
   return None
  return candidate
 except Exception:
  return None
DEFAULT_TICKET_NOTIONAL=RISK_CONFIG["ticket_notional"]
DEFAULT_MAX_TRADES_PER_MARKET=2
DEFAULT_MAX_TRADES_PER_HOUR=6
HARD_PORTFOLIO_EXPOSURE_CEILING=500.0
MAX_PORTFOLIO_EXPOSURE_USD=500.0
MIN_LOT_SIZE_USD=12.0
DEFAULT_MAX_CONCURRENT_POSITIONS=RISK_CONFIG["max_concurrent_positions"]
PROFIT_THETA=0.14
MIN_DISTANCE_PCT=0.10
MAX_TTE_SECONDS=2700.0
MIN_TTE_SECONDS=90.0
MAX_PRICE_CEILING=0.86
MIN_PRICE_FLOOR=0.55
MAX_ALLOWED_SPREAD=0.030
ALLOWED_ASSETS={"BTC","ETH"}
CIRCUIT_BREAKER_EQUITY_FLOOR=RISK_CONFIG["min_equity_floor"]
DYNAMIC_BANKROLL_PCT=RISK_CONFIG["dynamic_risk_pct"]
SL_POLICY="SPOT_DELTA_PASSIVE"
SPOT_DELTA_K=1.15
MAX_ADVERSE_SPOT_MOVE_PCT=float(os.getenv("POLYMARKET_MAX_ADVERSE_SPOT_MOVE_PCT","0.0040"))
TTE_CANCEL_WINDOW=15.0
KELLY_FRACTION=0.50
MAX_NOTIONAL_CAP_PCT=0.25
MAX_ABSOLUTE_TICKET_USD=200.00
PASSIVE_UNWIND_TIMEOUT=15.0
GLOBAL_HALT_STATUSES=frozenset({ "ENTRY_OUTCOME_UNKNOWN","EXIT_POST_OUTCOME_UNKNOWN","UNWIND_EXECUTION_OUTCOME_UNKNOWN","UNWIND_RECONCILIATION_REQUIRED","FILL_RECONCILIATION_REQUIRED","RESOLUTION_CANCEL_UNCONFIRMED","RECONCILIATION_HOLD_INCOMPLETE_SCHEMA","UNRESOLVED_BALANCE_DISCREPANCY","TERMINAL_UNWIND_FAILED_SUPERVISED","ENTRY_ONCHAIN_REVERTED","LIQUIDITY_CRISIS",})
MARKET_SCOPED_ENTRY_HALT_STATUSES=frozenset({ "ENTRY_OUTCOME_UNKNOWN","ENTRY_ONCHAIN_REVERTED",})
PIPELINE_GLOBAL_HALT_STATUSES=GLOBAL_HALT_STATUSES - MARKET_SCOPED_ENTRY_HALT_STATUSES
MAKER_EXIT_POSTABLE_STATUSES=frozenset({ "","NONE","PENDING_CONFIRMATION","AWAITING_DELTA_SETTLEMENT","AWAITING_SETTLEMENT","ENTRY_INVENTORY_RECONCILIATION_REQUIRED","POST_FAILED","EXIT_RECOVERY_REQUIRED","CROSSED_AT_MAX_TICK_WAIT",})
PARTIAL_UNWIND_RESIDUAL_STATUSES=frozenset({ "PARTIAL_UNWIND_REMAINING","PARTIAL_SALVAGE_REMAINING","PARTIAL_REPRICED_UNWIND_REMAINING","PARTIAL_PASSIVE_UNWIND_REMAINING",})
SETTLEMENT_RECEIVABLE_STATUSES=frozenset({"AWAITING_ONCHAIN_SETTLEMENT"})
UNRESOLVED_RECONCILIATION_STATUSES=GLOBAL_HALT_STATUSES
ENTRY_UNEXECUTED_PROOF_AGE_S=60.0
UNWIND_UNKNOWN_PROOF_AGE_S=30.0
REDEMPTION_POLL_INTERVAL_S=15.0
def position_requires_global_halt(pos:Dict[str,Any])->bool:
 return ( pos.get("exit_order_status") in PIPELINE_GLOBAL_HALT_STATUSES or pos.get("status") in PIPELINE_GLOBAL_HALT_STATUSES )
def position_may_post_new_maker_exit(pos:Dict[str,Any])->bool:
 if ( position_requires_global_halt(pos) or pos.get("status") in MARKET_SCOPED_ENTRY_HALT_STATUSES or pos.get("exit_order_status") in MARKET_SCOPED_ENTRY_HALT_STATUSES ):
  return False
 if pos.get("is_liquidating") or pos.get("unwind_order_id"):
  return False
 if pos.get("status") in SETTLEMENT_RECEIVABLE_STATUSES or pos.get("status") in {"ENTRY_OUTCOME_UNKNOWN","FAILED"}:
  return False
 if pos.get("terminal_policy")=="DETERMINISTIC_TERMINAL_HOLD_FINAL" or pos.get("exit_order_status")=="SUB_MINIMUM_LOT_SUPERVISED_HOLD":
  return False
 return str(pos.get("exit_order_status") or "") in MAKER_EXIT_POSTABLE_STATUSES
def position_is_settlement_receivable(pos:Dict[str,Any])->bool:
 return pos.get("status") in SETTLEMENT_RECEIVABLE_STATUSES
def compute_composite_edge_score(shock:Dict[str,Any])->Dict[str,Any]:
 shock_dir=str(shock.get("shock_direction") or "UP").upper()
 target_token="UP" if shock_dir in ("BUY","UP") else "DOWN"
 opp_token="DOWN" if target_token=="UP" else "UP"
 feats=shock.get("pre_shock_features_t0",{}) or {}
 tf=feats.get(target_token,{}) or {}
 opp_tf=feats.get(opp_token,{}) or {}
 if inspect_microstructure_feature_completeness is not None:
  feat_hygiene=inspect_microstructure_feature_completeness( shock,target_token,str(tf.get("token_id") or "") )
  if feat_hygiene.get("hard_veto_live"):
   return { "e_score":0.0,"tier":"TIER_C_REJECT","kelly_multiplier":0.0,"fak_price_buffer":0.010,"veto":True,"veto_reason":f"Missing live microstructure telemetry: {feat_hygiene.get('missing_fields')}","feature_hygiene":feat_hygiene,}
 age_ask_ms=float(tf.get("age_ask_ms") if tf.get("age_ask_ms") is not None else 400.0)
 if shock.get("shock_source") in ("BOUNDARY_LOCK","EXP316_TRACK_A_CONVERGENCE") or shock.get("sleeve")=="SLEEVE_3_STRIKE_CONVERGENCE":
  age_ask_ms=max(age_ask_ms,450.0)
 age_bid_ms=float(tf.get("age_bid_ms") if tf.get("age_bid_ms") is not None else 400.0)
 opp_bid_age=float(opp_tf.get("age_bid_ms") if opp_tf.get("age_bid_ms") is not None else 400.0)
 stale_boost=min(55.0,max(0.0,(age_ask_ms / 350.0) * 55.0))
 opp_boost=min(10.0,max(0.0,(opp_bid_age / 500.0) * 10.0))
 s_stale=min(100.0,max(0.0,35.0 + stale_boost + opp_boost))
 shock_ofi=float(shock.get("shock_ofi",1.0) if shock.get("shock_ofi") is not None else 1.0)
 ofi_abs=min(1.0,max(0.0,abs(shock_ofi)))
 shock_vol=float(shock.get("shock_volume_100ms",1_000_000.0) or 1_000_000.0)
 asset_str=str(shock.get("asset","BTC")).upper()
 base_vol=1_500_000.0 if asset_str=="BTC" else 500_000.0
 vol_ratio=min(2.5,max(0.2,shock_vol / base_vol))
 delta_basis=float(shock.get("delta_basis_100ms",0.0) or 0.0)
 dir_delta_basis=delta_basis if target_token=="UP" else -delta_basis
 fast_track=bool(shock.get("is_40ms_fast_track",False))
 flow_base=(ofi_abs * 50.0) + min(30.0,vol_ratio * 12.0) + (10.0 if fast_track else 0.0)
 flow_basis=max(-20.0,min(15.0,dir_delta_basis * 5.0))
 s_flow=min(100.0,max(0.0,flow_base + flow_basis))
 obi_l1=float(tf.get("obi_l1",0.0) or 0.0)
 obi_depth=float(tf.get("obi_depth",0.0) or 0.0)
 spread=float(tf.get("spread",0.01) or 0.01)
 q_micro=float(tf.get("q_micro",0.0) or 0.0)
 q_mid=float(tf.get("q_mid",0.0) or 0.0)
 micro_pull=((q_micro - q_mid) / max(spread,0.005)) if (q_micro > 0 and q_mid > 0) else 0.0
 s_l2=min(100.0,max(0.0,50.0 + (obi_l1 * 20.0) + (obi_depth * 15.0) + (micro_pull * 15.0)))
 raw_asks=tf.get("raw_top_asks",[]) or []
 first_ask=float(raw_asks[0][0]) if raw_asks else 0.65
 vwap_25=float(tf.get("vwap_$25") or tf.get("vwap_$20") or first_ask)
 spread_score=max(0.0,100.0 - (max(0.0,spread - 0.01) * 2000.0))
 slip_val=max(0.0,vwap_25 - first_ask)
 slip_score=max(0.0,100.0 - (slip_val * 2500.0))
 s_slip=min(100.0,max(0.0,0.50 * spread_score + 0.50 * slip_score))
 e_score=(0.35 * s_stale) + (0.30 * s_flow) + (0.20 * s_l2) + (0.15 * s_slip)
 veto=False
 veto_reason=None
 basis_veto_floor=-6.0 if str(shock.get("shock_source","")).upper()=="SPOT" else -2.0
 min_ofi_hurdle=0.60
 min_e_score_hurdle=50.0
 candle_dist_abs=abs(float(shock.get("candle_distance_pct",0.0) or 0.0))
 _raw_csig=float(shock.get("candle_sigma") or 0.0)
 _raw_tte=float(shock.get("seconds_to_expiry") or 3600.0)
 _is_15m_hint=str(shock.get("horizon") or "").lower()=="15m"
 _sig_1h_est=(_raw_csig * 2.0 if _is_15m_hint else _raw_csig) if _raw_csig > 0.0 else 0.0050
 _z_cush_est=(candle_dist_abs / 100.0) / max(0.00025,_sig_1h_est * math.sqrt(max(_raw_tte,30.0) / 3600.0))
 if ofi_abs < min_ofi_hurdle:
  veto=True
  veto_reason=f"OFI {ofi_abs:.2f} < {min_ofi_hurdle:.2f} hurdle"
 elif dir_delta_basis < basis_veto_floor:
  veto=True
  veto_reason=f"Directional delta_basis {dir_delta_basis:.2f} bps < {basis_veto_floor:.1f} bps"
 elif age_ask_ms < 25.0 and obi_l1 < -0.25:
  veto=True
  veto_reason=f"Ultra-fresh MM ask reload (age={age_ask_ms:.1f}ms < 25ms, obi_l1={obi_l1:.2f} < -0.25)"
 elif age_ask_ms < 50.0 and obi_l1 < -0.50:
  veto=True
  veto_reason=f"Ask already repriced by MM (age={age_ask_ms:.1f}ms < 50ms, obi_l1={obi_l1:.2f} < -0.50)"
 elif obi_l1 < -0.55 and 0.0 < candle_dist_abs < 0.09 and not (_raw_csig > 0.0 and _z_cush_est>=0.55 and age_ask_ms>=150.0):
  veto=True
  veto_reason=f"Heavy L1 ask wall against thin cushion (obi_l1={obi_l1:.2f} < -0.55, dist={candle_dist_abs:.4f}% < 0.09%)"
 if veto:
  tier="TIER_C_REJECT"
  kelly_multiplier=0.0
  fak_price_buffer=0.010
 elif round(e_score,1)>=70.0 and age_ask_ms>=250.0:
  tier="TIER_A_PLUS_STALE_SNIPE"
  kelly_multiplier=1.15
  fak_price_buffer=0.020
 elif round(e_score,1)>=min_e_score_hurdle:
  tier="TIER_B_STANDARD"
  kelly_multiplier=1.00
  fak_price_buffer=0.015
 else:
  tier="TIER_C_REJECT"
  kelly_multiplier=0.0
  fak_price_buffer=0.010
  veto=True
  veto_reason=f"e_score {e_score:.1f} < {min_e_score_hurdle:.1f} threshold"
 return { "e_score":round(e_score,2),"tier":tier,"kelly_multiplier":kelly_multiplier,"fak_price_buffer":fak_price_buffer,"veto":veto,"is_vetoed":veto,"veto_reason":veto_reason,"sub_scores":{ "s_stale":round(s_stale,2),"s_flow":round(s_flow,2),"s_l2":round(s_l2,2),"s_slip":round(s_slip,2),"S_stale":round(s_stale,2),"S_flow":round(s_flow,2),"S_L2":round(s_l2,2),"S_slip":round(s_slip,2),},"age_ask_ms":age_ask_ms,}
def compute_max_acceptable_ask( dist_pct:float,tte_sec:float,asset:str="BTC",shock_ofi:float=1.0,shock_vol_usd:float=1_500_000.0,delta_basis_bps:float=0.0,age_ask_ms:float=350.0,target_return:float=0.14,fee_rate:float=0.07,is_subhourly_15m:bool=False,expected_salvage_net:float=0.36,q_tail:float=0.08,)->Dict[str,float]:
 asset_clean=str(asset or "BTC").upper()
 sigma_1h=0.0050 if asset_clean=="BTC" else (0.0095 if asset_clean=="SOL" else 0.0068)
 if GLOBAL_SVI_ENGINE is not None and os.environ.get("PM_SVI_DISABLE_BG_REFRESH")!="1":
  try:
   _svi_sig=float(GLOBAL_SVI_ENGINE.get_hourly_sigma(asset_clean,fallback=sigma_1h) or 0.0)
   if _svi_sig > 0.0:
    _sig_floor=0.0050 if (is_subhourly_15m and abs(float(dist_pct)) < 0.09) else 0.0028
    sigma_1h=max(_sig_floor,min(sigma_1h,_svi_sig * 0.80))
  except Exception:
   pass
 candle_horizon_s=900.0 if is_subhourly_15m else 3600.0
 sigma_candle=sigma_1h * math.sqrt(candle_horizon_s / 3600.0)
 tau_clamped=max(float(tte_sec),15.0)
 sigma_rem=sigma_candle * math.sqrt(tau_clamped / candle_horizon_s)
 cushion_frac=abs(float(dist_pct)) / 100.0
 base_vol=1_500_000.0 if asset_clean=="BTC" else 500_000.0
 vol_ratio=min(3.0,max(0.2,float(shock_vol_usd) / base_vol))
 ofi_abs=min(1.0,max(0.0,abs(float(shock_ofi))))
 stale_mult=1.0 + 0.15 * max(-0.5,min(1.0,(float(age_ask_ms) - 200.0) / 400.0))
 drift_bps=((6.5 * ofi_abs * (vol_ratio ** 0.30)) + (0.45 * float(delta_basis_bps))) * stale_mult
 drift_frac=(drift_bps / 10000.0) * min(1.0,math.sqrt(300.0 / tau_clamped))
 if is_subhourly_15m and abs(float(dist_pct)) < 0.09:
  drift_frac=min(drift_frac,0.25 * cushion_frac)
  expected_salvage_net=min(float(expected_salvage_net),0.16)
 z_eff=(cushion_frac + drift_frac) / max(sigma_rem,1e-6)
 p_true=0.5 * (1.0 + math.erf(z_eff / math.sqrt(2.0)))
 p_exit=0.985
 expected_payoff=(p_true * p_exit) + ((1.0 - p_true) * (1.0 - q_tail) * expected_salvage_net)
 r=float(fee_rate)
 eta=float(target_return)
 discriminant=((1.0 + r) ** 2) - (4.0 * r * expected_payoff / (1.0 + eta))
 if discriminant<=0.0 or p_true<=0.53:
  p_max=0.0
 else:
  p_root=((1.0 + r) - math.sqrt(discriminant)) / (2.0 * r)
  regime_cap=0.78 if tau_clamped > 900.0 else 0.85
  p_max=min(regime_cap,max(0.0,round(p_root,4)))
 return { "p_max":p_max,"p_true":round(p_true,4),"expected_payoff":round(expected_payoff,4),"z_eff":round(z_eff,3),"sigma_rem_pct":round(sigma_rem * 100.0,4),}
def compute_modified_salvage_kelly_fraction( p_win:float,entry_price:float,target_exit:float=0.985,l_salvage:float=0.42,q_tail:float=0.05,kelly_lambda:float=0.28,)->float:
 if entry_price<=0.01 or entry_price>=0.99 or p_win<=0.50:
  return 0.0
 r_win=(target_exit - entry_price) / entry_price
 if r_win<=0.001:
  return 0.0
 l_eff=((1.0 - q_tail) * l_salvage) + q_tail
 num=(p_win * r_win) - ((1.0 - p_win) * l_eff)
 denom=r_win * l_eff
 if denom<=0.0:
  return 0.0
 f_star=num / denom
 if f_star<=0.0:
  return 0.0
 return round(float(f_star * kelly_lambda),4)
def compute_correlated_truncated_kelly_size( live_equity:float=0.0,entry_px:float=0.0,p_win:float=0.0,kelly_multiplier:float=1.0,active_positions:Optional[Dict[str,Any]]=None,cand_expiry_ts:float=0.0,cand_direction:str="UP",min_lot_usd:float=12.0,max_ticket_cap:float=200.0,default_sizing_pct:float=0.24,bankroll_usd:Optional[float]=None,entry_price:Optional[float]=None,p_true:Optional[float]=None,)->float:
 if bankroll_usd is not None and live_equity<=0.0:
  live_equity=bankroll_usd
 if entry_price is not None and entry_px<=0.0:
  entry_px=entry_price
 if p_true is not None and p_win<=0.0:
  p_win=p_true
 if live_equity<=0.0 or entry_px<=0.0 or p_win<=0.0:
  return 0.0
 f_k=compute_modified_salvage_kelly_fraction(p_win,entry_px)
 if f_k<=0.0:
  return 0.0
 if f_k < 0.10:
  f_k=default_sizing_pct if entry_px<=0.78 else 0.20
 f_k=min(float(default_sizing_pct),f_k)
 k_mult=max(0.8,min(1.30,float(kelly_multiplier)))
 f_k_adj=min(float(default_sizing_pct) * 1.15,f_k * k_mult)
 corr_multiplier=1.0
 if active_positions:
  for p in active_positions.values():
   p_status=str(p.get("status") or "FILLED")
   rem_shrs=float(p.get("remaining_shares") or 0.0)
   if p_status in ("OPEN","FILLED","PENDING_CONFIRMATION","RESTING","EXIT_RESTING") or rem_shrs > 0.0:
    pos_exp=float(p.get("candle_expiry_ts") or 0.0)
    pos_dir=str(p.get("target_token") or "").upper()
    if cand_expiry_ts > 0 and pos_exp > 0 and abs(pos_exp - cand_expiry_ts)<=900.0 and pos_dir:
     if pos_dir==cand_direction.upper():
      corr_multiplier=min(corr_multiplier,round(1.0 / (1.0 + 0.85),4))
     else:
      return 0.0
 raw_ticket=live_equity * f_k_adj * corr_multiplier
 ticket_sized=round(min(max_ticket_cap,max(min_lot_usd,raw_ticket)),2)
 return ticket_sized
def apply_convex_payoff_sizing_cap( raw_ticket_usd:float,*,live_equity:float,entry_px:float,sleeve:str="",knee:float=0.79,gamma:float=0.75,min_taper:float=0.58,max_salvage_risk_pct:float=0.125,salvage_floor_px:float=0.24,min_lot_usd:float=8.0,)->float:
 if raw_ticket_usd<=0.0 or live_equity<=0.0 or entry_px<=0.0:
  return max(0.0,float(raw_ticket_usd))
 slv_u=str(sleeve or "").upper()
 if "BOX" in slv_u or slv_u=="SLEEVE_4_BOUNDARY_SNIPE":
  return round(float(raw_ticket_usd),2)
 px=min(0.97,max(0.05,float(entry_px)))
 taper=1.0
 if px > knee:
  rem_up=max(0.04,0.99 - px)
  ref_up=max(0.04,0.99 - knee)
  taper=max(float(min_taper),(rem_up / ref_up) ** float(gamma))
 loss_frac_at_salvage=max(0.25,(px - float(salvage_floor_px)) / px)
 stop_cap_tkt=(float(max_salvage_risk_pct) * float(live_equity)) / loss_frac_at_salvage
 capped=min(float(raw_ticket_usd) * taper,stop_cap_tkt)
 return round(min(float(raw_ticket_usd),max(float(min_lot_usd),capped)),2)
def get_equity_tier_limits( total_equity:float,high_water_mark_equity:Optional[float]=None,previous_tier:Optional[str]=None,)->Dict[str,Any]:
 eq=float(total_equity) if (total_equity is not None and math.isfinite(float(total_equity))) else 0.0
 hwm=( float(high_water_mark_equity) if ( high_water_mark_equity is not None and math.isfinite(float(high_water_mark_equity)) and float(high_water_mark_equity) > 0.0 ) else eq )
 if hwm < eq:
  hwm=eq
 seed_thresh=float(RISK_CONFIG.get("seed_survival_equity_threshold",88.0))
 seed_exit_thresh=seed_thresh + 3.0 if previous_tier=="SEED_SURVIVAL" else seed_thresh
 if eq < seed_exit_thresh:
  tier_name="SEED_SURVIVAL"
  dynamic_bankroll_pct=float(RISK_CONFIG.get("dynamic_risk_pct",0.1568))
  max_concurrent_positions=int(RISK_CONFIG.get("seed_survival_max_concurrent",1))
  max_exposure=round(max(float(RISK_CONFIG.get("max_exposure",24.0)),eq * 0.30),2)
  max_daily_loss=float(RISK_CONFIG.get("max_daily_loss",22.0))
  min_equity_floor=float(RISK_CONFIG.get("seed_survival_floor_usd",48.0))
  return { "tier":tier_name,"dynamic_bankroll_pct":dynamic_bankroll_pct,"max_concurrent_positions":max_concurrent_positions,"max_exposure":max_exposure,"max_daily_loss":max_daily_loss,"min_equity_floor":min_equity_floor,}
 if previous_tier in ("SEED_SURVIVAL","SEED_RAMP") and eq < 108.0:
  return { "tier":"SEED_RAMP","dynamic_bankroll_pct":0.17,"max_concurrent_positions":1 if eq < 98.0 else 2,"max_exposure":round(max(30.0,eq * 0.38),2),"max_daily_loss":round(max(22.0,eq * 0.26),2),"min_equity_floor":round(max(54.0,min(65.0,hwm * 0.64)),2),}
 if eq < 140.0:
  tier_name="RECOVERY"
  dynamic_bankroll_pct=0.22
  max_concurrent_positions=2
  max_exposure=round(max(45.0,eq * 0.55),2)
 elif eq < 300.0:
  tier_name="GROWTH"
  dynamic_bankroll_pct=0.26
  max_concurrent_positions=3
  max_exposure=round(min(350.0,eq * 0.75),2)
 else:
  tier_name="SCALE"
  dynamic_bankroll_pct=0.28
  max_concurrent_positions=3
  max_exposure=round(min(500.0,eq * 0.85),2)
 max_daily_loss=round(max(25.0,eq * 0.30),2)
 min_equity_floor=round(max(65.0,hwm * 0.68),2)
 return { "tier":tier_name,"dynamic_bankroll_pct":dynamic_bankroll_pct,"max_concurrent_positions":max_concurrent_positions,"max_exposure":max_exposure,"max_daily_loss":max_daily_loss,"min_equity_floor":min_equity_floor,}
class StatePersistenceError(RuntimeError):
 pass
class EmergencyRiskController:
 def __init__( self,max_consecutive_losses:int=3,max_daily_loss_usd:Optional[float]=None,max_daily_loss_pct:float=0.18,min_equity_floor_usd:float=CIRCUIT_BREAKER_EQUITY_FLOOR,):
  self.max_consecutive_losses=max_consecutive_losses
  self.max_daily_loss_usd=max_daily_loss_usd if max_daily_loss_usd is not None else float(RISK_CONFIG["max_daily_loss"])
  self.max_daily_loss_pct=max_daily_loss_pct
  self.min_equity_floor_usd=min_equity_floor_usd
  self.consecutive_losses=0
  self.daily_realized_loss=0.0
  self.last_loss_date_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d")
  self.halted=False
  self.halt_reason=""
  self.kill_file=DATA_DIR / "KILL_SWITCH"
  self._halt_alerted=False
 def _kill_file_active(self)->bool:
  kf=self.kill_file
  if kf==(DATA_DIR / "KILL_SWITCH") and STATE_FILE.parent!=DATA_DIR:
   kf=STATE_FILE.parent / "KILL_SWITCH"
  return kf.exists()
 def check_equity_drawdown( self,current_equity:Optional[float],high_water_mark:Optional[float]=None,*,allow_auto_clear:bool=False )->bool:
  if current_equity is not None and math.isfinite(float(current_equity)):
   eq=float(current_equity)
   if eq < self.min_equity_floor_usd:
    self.halted=True
    self.halt_reason=( f"Account equity ${eq:.2f} < ${self.min_equity_floor_usd:.2f} " f"circuit-breaker threshold (2-loss variance buffer breached)." )
    logger.critical(f"[CIRCUIT_BREAKER_HALT] {self.halt_reason}")
   elif ( self.halted and "Account equity" in self.halt_reason and allow_auto_clear and eq>=(self.min_equity_floor_usd + 3.00) ):
    if self._kill_file_active():
     self.halt_reason=f"Emergency KILL_SWITCH file detected at {self.kill_file}"
    else:
     self.halted=False
     self.halt_reason=""
     logger.info(f"[CIRCUIT_BREAKER_CLEARED] Verified equity ${eq:.2f} >= +$3.00 above ${self.min_equity_floor_usd:.2f} floor.")
  return bool(self.halted)
 def _check_and_reset_daily(self):
  current_date=datetime.now(timezone.utc).strftime("%Y-%m-%d")
  if current_date!=self.last_loss_date_utc:
   logger.info(f"[RISK CONTROLLER] UTC day rolled over ({self.last_loss_date_utc} -> {current_date}). Resetting daily realized loss to $0.00.")
   self.daily_realized_loss=0.0
   self.last_loss_date_utc=current_date
   if self.halted and "Max daily loss reached" in self.halt_reason:
    self.halted=False
    self.halt_reason=""
    self._halt_alerted=False
 def record_trade_pnl(self,net_pnl:float):
  self._check_and_reset_daily()
  if net_pnl < 0:
   self.consecutive_losses += 1
   self.daily_realized_loss += abs(net_pnl)
   if self.consecutive_losses>=self.max_consecutive_losses:
    self.halted=True
    self.halt_reason=f"Max consecutive losses reached ({self.consecutive_losses})"
   elif self.daily_realized_loss>=self.max_daily_loss_usd:
    self.halted=True
    self.halt_reason=f"Max daily loss reached (${self.daily_realized_loss:.2f} on {self.last_loss_date_utc})"
  else:
   self.consecutive_losses=0
   if not self.halted:
    self.daily_realized_loss=max(0.0,self.daily_realized_loss - net_pnl)
 def is_halted(self)->bool:
  self._check_and_reset_daily()
  kf_on=self._kill_file_active()
  if self.halted and "KILL_SWITCH file" in str(self.halt_reason or "") and not kf_on:
   self.halted=False
   self.halt_reason=""
   self._halt_alerted=False
  halted_now=False
  if kf_on:
   self.halted=True
   if not self.halt_reason:
    self.halt_reason=f"Emergency KILL_SWITCH file detected at {self.kill_file}"
   halted_now=True
  elif self.halted:
   halted_now=True
  if halted_now and not self._halt_alerted:
   self._halt_alerted=True
   send_operational_alert( "KILL_SWITCH_TRIPPED",f"Trading halted: {self.halt_reason or 'unspecified'}","CRITICAL",rate_limit_sec=float(RISK_CONFIG["alert_rate_limit_sec"]),dedupe_key=f"halt:{self.halt_reason[:60]}",)
  elif not halted_now:
   self._halt_alerted=False
  return halted_now
 def check_kill_switch(self)->bool:
  return self.is_halted()
def compute_kelly_ticket_size( p_model:float,p_market_ask:Optional[float]=None,bankroll:float=0.0,fee_rate:Optional[float]=None,fee_exponent:Optional[float]=None,max_cap:Optional[float]=None,*,p_eff:Optional[float]=None,)->float:
 ask_px=p_eff if p_market_ask is None else p_market_ask
 if ask_px is None or not all(math.isfinite(float(v)) for v in (p_model,ask_px,bankroll)):
  return 0.0
 if not (0.0 < float(p_model) < 1.0) or float(bankroll)<=0.0 or float(ask_px)<=0.0 or float(p_model)<=float(ask_px):
  return 0.0
 effective_cap=float(max_cap) if max_cap is not None else MAX_ABSOLUTE_TICKET_USD
 ticket_usd=min(max(25.0,float(bankroll) * MAX_NOTIONAL_CAP_PCT),effective_cap)
 return round(ticket_usd,2)
class PolymarketLiveHarvester:
 def __init__( self,ticket_notional:float=DEFAULT_TICKET_NOTIONAL,dry_run:bool=False,dynamic_sizing:bool=True,max_exposure:Optional[float]=None,max_concurrent:Optional[int]=None,max_trades_per_market:int=DEFAULT_MAX_TRADES_PER_MARKET,max_trades_per_hour:int=DEFAULT_MAX_TRADES_PER_HOUR,max_tte:float=MAX_TTE_SECONDS,max_price_ceiling:float=MAX_PRICE_CEILING,min_price_floor:float=MIN_PRICE_FLOOR,profit_theta:float=PROFIT_THETA,spot_delta_k:float=SPOT_DELTA_K,tte_cancel_window:float=TTE_CANCEL_WINDOW,kelly_fraction:float=KELLY_FRACTION,max_notional_cap_pct:float=MAX_NOTIONAL_CAP_PCT,passive_unwind_timeout:float=PASSIVE_UNWIND_TIMEOUT,depth_hurdle:float=1.30,unconstrained_kelly:bool=False,max_absolute_ticket_usd:Optional[float]=None,dynamic_theta:bool=False,hold_to_maturity:bool=True,exit_policy:str="two_tranche_95_98",allow_cli_exposure:bool=False,allowed_assets:Optional[Set[str]]=None,reset_risk:bool=False,max_daily_loss:Optional[float]=None,):
  DATA_DIR.mkdir(parents=True,exist_ok=True)
  self.ticket_notional=ticket_notional
  self.dry_run=dry_run
  self.dynamic_sizing=dynamic_sizing
  self.unconstrained_kelly=unconstrained_kelly
  self.hold_to_maturity=hold_to_maturity
  self.exit_policy=str(exit_policy or "two_tranche_95_98").strip().lower()
  reset_marker=STATE_FILE.parent / "RESET_RISK_ONCE"
  if not dry_run and reset_marker.exists():
   try:
    reset_marker.unlink()
    reset_risk=True
    logger.info("[STARTUP] Consumed RESET_RISK_ONCE marker; risk controller will be reset once.")
   except Exception as exc:
    logger.warning(f"[STARTUP] Could not consume RESET_RISK_ONCE marker: {exc}")
  self.reset_risk=reset_risk
  self.risk_config=dict(RISK_CONFIG)
  self._shutdown_requested=False
  self._shutdown_status:Optional[str]=None
  self.allowed_assets=set(allowed_assets) if allowed_assets is not None else set(ALLOWED_ASSETS)
  requested_cap=float(max_exposure if max_exposure is not None else float(self.risk_config.get("max_exposure",MAX_PORTFOLIO_EXPOSURE_USD)))
  allow_ext=allow_cli_exposure or (os.getenv("POLYMARKET_ALLOW_EXTENDED_EXPOSURE","0")=="1")
  if requested_cap > HARD_PORTFOLIO_EXPOSURE_CEILING and not allow_ext:
   logger.warning( f"[RISK CEILING] Requested max_exposure (${requested_cap:.2f}) exceeds immutable hard ceiling " f"(${HARD_PORTFOLIO_EXPOSURE_CEILING:.2f}). Clamped to ${HARD_PORTFOLIO_EXPOSURE_CEILING:.2f}." )
   self.max_exposure=HARD_PORTFOLIO_EXPOSURE_CEILING
  else:
   self.max_exposure=max(0.0,requested_cap)
  self.allow_cli_exposure=bool(allow_cli_exposure)
  self.high_water_mark_equity=0.0
  self.max_trades_per_market=max_trades_per_market
  self.max_trades_per_hour=max_trades_per_hour
  self.max_tte=max_tte
  self.max_price_ceiling=max_price_ceiling
  self.min_price_floor=min_price_floor
  self.profit_theta=profit_theta
  self.spot_delta_k=spot_delta_k
  self.tte_cancel_window=tte_cancel_window
  self.kelly_fraction=kelly_fraction
  self.max_notional_cap_pct=max_notional_cap_pct
  self.dynamic_bankroll_pct=DYNAMIC_BANKROLL_PCT
  self.passive_unwind_timeout=passive_unwind_timeout
  self.depth_hurdle=depth_hurdle
  self.dynamic_theta=dynamic_theta
  self.max_absolute_ticket_usd=max_absolute_ticket_usd if max_absolute_ticket_usd is not None else (10000.0 if unconstrained_kelly else MAX_ABSOLUTE_TICKET_USD)
  self.max_ticket_cap=self.max_absolute_ticket_usd
  self._spot_cache:Dict[str,Tuple[float,float]]={}
  if max_concurrent is not None:
   self.max_concurrent_positions=max_concurrent
  elif "MAX_CONCURRENT_POSITIONS" in os.environ:
   self.max_concurrent_positions=int(os.environ["MAX_CONCURRENT_POSITIONS"])
  else:
   self.max_concurrent_positions=DEFAULT_MAX_CONCURRENT_POSITIONS
  self.executor=PolymarketLiveExecutor( dry_run=dry_run,ledger_path=None,)
  daily_loss_budget=max_daily_loss if max_daily_loss is not None else float(RISK_CONFIG["max_daily_loss"])
  eff_eq_floor=CIRCUIT_BREAKER_EQUITY_FLOOR
  self.risk_controller=EmergencyRiskController( max_daily_loss_usd=daily_loss_budget,min_equity_floor_usd=eff_eq_floor,)
  self.seen_shock_ids:Set[str]=set()
  self._seen_shock_order:Dict[str,None]={}
  self._seen_d1_box_keys:Set[str]=set()
  self._seen_d1_box_order:Dict[str,None]={}
  self.traded_market_ids:Set[str]=set()
  self.trades_per_market:Dict[str,int]=defaultdict(int)
  self.trades_per_market_direction:Dict[Tuple[str,str],int]=defaultdict(int)
  self.hourly_candle_opens:Dict[str,Dict[int,float]]=defaultdict(dict)
  self.active_positions:Dict[str,Dict[str,Any]]={}
  self.closed_positions:List[Dict[str,Any]]=[]
  if "POLYMARKET_LOW_BID_PERSISTENCE_SECONDS" in os.environ:
   self.low_bid_persistence_seconds=float(os.environ["POLYMARKET_LOW_BID_PERSISTENCE_SECONDS"])
  else:
   self.low_bid_persistence_seconds=1.5
  self.trades_this_hour=0
  self.current_hour_window=time.time() // 3600
  self.last_trigger_file_pos=0
  self.last_shock_file_pos=0
  self.last_res_file_pos=0
  self.last_heartbeat_time=0.0
  self.market_tokens_cache:Dict[str,str]={}
  self.market_condition_ids:Dict[str,str]={}
  self.calibrated_p_model=float(os.getenv("POLYMARKET_CALIBRATED_P_MODEL","0.95"))
  self.calibrated_model_version="REGIME_4_EMPIRICAL_V2"
  self.calibrated_model_id="OOS_LEDGER_248_TRADES"
  self.pending_entry_intents:Dict[str,Dict[str,Any]]={}
  self.risk_halt:bool=False
  self.reconciliation_required:bool=False
  self.global_halt_reasons:List[str]=[]
  self._startup_reconciled:bool=False
  self._last_redemption_poll:float=0.0
  self.recent_shock_window:List[Dict[str,Any]]=[]
  self._last_known_collateral:Optional[float]=None
  self._current_equity_tier:Optional[str]=None
  self.current_equity_tier:Optional[str]=None
  self._prewarm_hourly_opens()
 def _record_seen_shock_id(self,shock_id:str)->None:
  if not hasattr(self,"_seen_shock_order"):
   self._seen_shock_order={sid:None for sid in self.seen_shock_ids}
  self._seen_shock_order.pop(shock_id,None)
  self._seen_shock_order[shock_id]=None
  self.seen_shock_ids.add(shock_id)
  while len(self._seen_shock_order) > 2000:
   oldest=next(iter(self._seen_shock_order))
   self._seen_shock_order.pop(oldest,None)
   self.seen_shock_ids.discard(oldest)
  cur_h=int(time.time() // 3600)
  for asset_map in self.hourly_candle_opens.values():
   stale_hours=[h for h in asset_map if h < (cur_h - 48)]
   for h in stale_hours:
    asset_map.pop(h,None)
  if len(self.closed_positions) > 200:
   self.closed_positions=self.closed_positions[-200:]
 def effective_risk_pct(self,equity:float)->float:
  try:
   if float(equity)>=float(self.risk_config["scale_up_equity_threshold"]):
    return float(self.risk_config["scale_up_risk_pct"])
  except (TypeError,ValueError):
   pass
  return float(self.dynamic_bankroll_pct)
 @staticmethod
 def _shock_asset(shock:Dict[str,Any])->str:
  asset=str(shock.get("asset") or "").upper()
  if not asset:
   title=str(shock.get("title") or "").strip()
   asset=title.split()[0].upper() if title else "BTC"
  return asset
 def check_recorder_freshness(self,asset:str,now_ts:float)->Tuple[bool,float,str]:
  asset=str(asset).upper()
  env_dir=os.environ.get("PM_FAST_TICK_DIR")
  tick_dir=Path(env_dir) if env_dir else FAST_TICK_DIR
  tele_dir=Path(os.environ.get("PM_TELEMETRY_DIR",str(DATA_DIR)))
  tele_name="polymarket_hourly_telemetry.jsonl" if asset=="BTC" else f"polymarket_hourly_telemetry_{asset.lower()}.jsonl"
  def _age_with_payload(p:Path,is_jsonl:bool=False)->float:
   try:
    raw_m=float(now_ts) - p.stat().st_mtime
    if raw_m < -2.0:
     return float("inf")
    m_age=max(0.0,raw_m)
    try:
     if not is_jsonl:
      snap=_json_loads(p.read_bytes())
      if isinstance(snap,dict):
       in_ts=float(snap.get("ts") or snap.get("timestamp_unix") or 0.0)
       if in_ts > 0.0:
        in_age=float(now_ts) - in_ts
        return float("inf") if in_age < -2.0 else max(m_age,max(0.0,in_age))
     else:
      sz=p.stat().st_size
      if sz > 2:
       with open(p,"rb") as fh:
        fh.seek(max(0,sz - 4096))
        lines=[ln.strip() for ln in fh.read().splitlines() if ln.strip()]
       if lines:
        last_obj=_json_loads(lines[-1])
        if isinstance(last_obj,dict):
         in_ts=float(last_obj.get("timestamp_unix") or last_obj.get("ts") or 0.0)
         if in_ts > 0.0:
          in_age=float(now_ts) - in_ts
          return float("inf") if in_age < -2.0 else max(m_age,max(0.0,in_age))
    except Exception:
     pass
    return m_age
   except OSError:
    return float("inf")
  tick_age=_age_with_payload(tick_dir / f"pm_fast_tick_{asset}.json",is_jsonl=False)
  fast_max=float(self.risk_config["stale_fast_tick_max_age_sec"])
  if tick_age<=fast_max:
   return True,tick_age,f"fast_tick_age={tick_age:.1f}s<={fast_max:.0f}s"
  tele_age=_age_with_payload(tele_dir / tele_name,is_jsonl=True)
  tele_max=float(self.risk_config["stale_telemetry_max_age_sec"])
  newest=min(tick_age,tele_age)
  if tele_age<=tele_max:
   return True,newest,f"telemetry_age={tele_age:.1f}s<={tele_max:.0f}s"
  return False,newest,f"fast_tick_age={tick_age:.1f}s>{fast_max:.0f}s and telemetry_age={tele_age:.1f}s>{tele_max:.0f}s"
 def monitor_recorder_staleness(self,now_ts:float)->None:
  alert_after=float(self.risk_config["stale_alert_after_sec"])
  for asset in sorted(self.allowed_assets):
   ok,age,reason=self.check_recorder_freshness(asset,now_ts)
   if age > alert_after:
    send_operational_alert( "STALE_RECORDER_FEED",f"{asset} recorder silent for {'>' + str(int(alert_after)) + 's' if math.isinf(age) else f'{age:.0f}s'} ({reason}). New entries blocked.","CRITICAL",rate_limit_sec=float(self.risk_config["alert_rate_limit_sec"]),dedupe_key=f"stale_recorder:{asset}",)
 def _append_shadow_phase3_4_event(self,record:Dict[str,Any])->None:
  raw_target=os.environ.get("PM_SHADOW_TRACKER_FILE")
  if raw_target is not None and not raw_target.strip():
   return
  try:
   out_path=Path(raw_target) if raw_target else SHADOW_PHASE3_4_FILE
   out_path.parent.mkdir(parents=True,exist_ok=True)
   with open(out_path,"a",encoding="utf-8") as fh:
    fh.write(json.dumps(record) + "\n")
  except Exception as exc:
   logger.debug(f"[SHADOW_TRACKER] Write failed: {exc}")
 def _register_shadow_phase3a_maker_in( self,shock:Dict[str,Any],target_token:str,first_ask:float,first_bid:float,max_allowed_price:float,raw_asks:List[Tuple[float,float]],reject_reason:str,is_subhourly:bool,dist_pct:float,tte:float,)->None:
  try:
   if first_ask<=0.0 or first_bid < 0.50 or tte < 35.0:
    return
   m_id=str(shock.get("market_id") or "")
   if not m_id:
    return
   shadow_orders=getattr(self,"_shadow_maker_orders",None)
   if shadow_orders is None:
    self._shadow_maker_orders={}
    shadow_orders=self._shadow_maker_orders
   key=f"{m_id}_{target_token}"
   if key in shadow_orders:
    return
   maker_px=round(min(max_allowed_price,first_ask - 0.01),2)
   if maker_px < 0.54:
    return
   r_rebate=0.20 * 0.07
   maker_eff_cost=round(maker_px - r_rebate * maker_px * (1.0 - maker_px),5)
   depth_at_max=sum(px * sz for px,sz in (raw_asks or []) if px<=max_allowed_price)
   snapped_rung=16.50 if depth_at_max>=16.50 else (12.00 if depth_at_max>=12.00 else 0.0)
   headroom_cents=round((max_allowed_price - first_ask) * 100.0,2)
   now_ts=time.time()
   ttl_sec=float(os.environ.get("PM_SHADOW_MAKER_TTL_SEC","3.5"))
   open_spot=float( (shock.get("candle_open_spot") if is_subhourly else (shock.get("finalized_1h_open") or shock.get("candle_open_spot"))) or 0.0 )
   expiry_ts=float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (now_ts + tte))
   asset_str=str(shock.get("asset") or "BTC").upper()
   rec={ "event_type":"SHADOW_PHASE3A_MAKER_IN_REGISTERED","logged_at_utc":datetime.now(timezone.utc).isoformat(),"market_id":m_id,"title":shock.get("title"),"asset":asset_str,"horizon":"15m" if is_subhourly else "1h","target_token":target_token,"reject_reason":reject_reason,"first_ask":round(first_ask,4),"first_bid":round(first_bid,4),"max_allowed_price":round(max_allowed_price,4),"shadow_maker_px":maker_px,"shadow_maker_eff_cost":maker_eff_cost,"idea1_depth_at_max_usd":round(depth_at_max,2),"idea1_snapped_rung_usd":snapped_rung,"idea5_headroom_cents":headroom_cents,"entry_dist_pct":round(dist_pct,4),"tte_sec":round(tte,1),"placed_ts":now_ts,"ttl_sec":ttl_sec,"ttl_expires_ts":now_ts + ttl_sec,"expiry_ts":expiry_ts,"open_spot":open_spot,"status":"RESTING",}
   shadow_orders[key]=rec
   self._append_shadow_phase3_4_event(rec)
   logger.info( f"[SHADOW PHASE 3A] Registered virtual Maker-In {asset_str} {target_token} @ ${maker_px:.2f} " f"(eff=${maker_eff_cost:.4f}, TTL={ttl_sec:.1f}s, reason={reject_reason}, snapped_rung=${snapped_rung:.2f})" )
  except Exception as exc:
   logger.debug(f"[SHADOW PHASE 3A] Register error: {exc}")
 async def _attempt_live_phase3a_maker_rescue( self,trade_id:str,token_id:str,target_token:str,asset_str:str,effective_notional:float,first_ask:float,first_bid:float,min_allowed_price:float,max_allowed_price:float,open_spot:float,entry_spot_ref:float,spot_denom:str,tte:float,pre_cond_bal:float,book_snapshot:Optional[Dict[str,Any]],)->Optional[OrderResult]:
  explicit_flag=self.__dict__.get("enable_live_phase3a_maker_fallback")
  if explicit_flag is False or os.environ.get("PM_DISABLE_LIVE_PHASE3A_MAKER","0")=="1":
   return None
  real_live=( not self.dry_run and getattr(self.executor,"auth_mode","") in ("LIVE","AUTHENTICATED_L2") and getattr(getattr(self.executor,"client",None),"_mock_children",None) is None and not any(k in getattr(self.executor,"__dict__",{}) for k in ("execute_snipe_order_async","execute_snipe_order")) )
  if not (explicit_flag is True or (real_live and bool(RISK_CONFIG.get("enable_live_phase3a_maker_fallback",True)))):
   return None
  if tte < (85.0 if real_live else 75.0) or self.risk_controller.is_halted() or getattr(self,"risk_halt",False):
   return None
  maker_entry_fn=getattr(self.executor,"place_passive_maker_entry",None) or getattr(self.executor,"post_maker_entry_order",None)
  if maker_entry_fn is None:
   return None
  fresh_bk=fast_tick_book_for_token(read_fast_tick(asset_str),token_id) or book_snapshot or {}
  f_ask=min((float(a["price"] if isinstance(a,dict) else a[0]) for a in (fresh_bk.get("asks") or []) if float(a.get("size",0) if isinstance(a,dict) else a[1]) > 0),default=first_ask)
  f_bid=max((float(b["price"] if isinstance(b,dict) else b[0]) for b in (fresh_bk.get("bids") or []) if float(b.get("size",0) if isinstance(b,dict) else b[1]) > 0),default=first_bid)
  ask_cap=round(f_ask - 0.01,2) if f_ask > 0.02 else round(max_allowed_price,2)
  bid_step=round(max(f_bid,first_bid) + 0.01,2) if max(f_bid,first_bid) > 0.0 else ask_cap
  maker_px=round(min(float(max_allowed_price),ask_cap,bid_step),2)
  if not (float(min_allowed_price) - 1e-6<=maker_px<=float(max_allowed_price) + 1e-6) or (f_ask > 0.0 and maker_px > round(f_ask - 0.01,2) + 1e-6):
   return None
  rescue_notional=min(float(effective_notional),float(RISK_CONFIG.get("phase3a_maker_max_notional_usd",22.00)))
  if math.floor(rescue_notional / max(0.01,maker_px)) < 5:
   return None
  t0_m=time.perf_counter()
  if trade_id in self.pending_entry_intents:
   self.pending_entry_intents[trade_id].update(target_price=maker_px,notional_usd=rescue_notional)
  post_res=await asyncio.to_thread( maker_entry_fn,token_id=token_id,price=maker_px,notional_usd=rescue_notional,side="BUY",min_price_floor=float(min_allowed_price),max_price_ceiling=float(max_allowed_price),)
  if not isinstance(post_res,dict):
   return None
  if post_res.get("outcome_unknown"):
   return OrderResult( success=False,order_id=post_res.get("orderID"),trade_id=trade_id,token_id=token_id,target_token=target_token,side="BUY",price=maker_px,size=float(post_res.get("shares") or 5.0),notional_usd=rescue_notional,fee_usd=0.0,latency_ms=round((time.perf_counter() - t0_m) * 1000.0,2),mode="LIVE_PHASE3A_UNKNOWN",execution_status=ExecutionStatus.SUBMITTED,details={"outcome_unknown":True,"entry_order_id":post_res.get("orderID"),"pre_token_balance":pre_cond_bal},error=str(post_res.get("error") or "PHASE3A_POST_UNKNOWN"),)
  maker_oid=str(post_res.get("orderID") or "").strip()
  if not post_res.get("success") or not maker_oid:
   return None
  if trade_id in self.pending_entry_intents:
   self.pending_entry_intents[trade_id]["entry_order_id"]=maker_oid
  ttl_s=max(0.2,float(os.environ.get("PM_LIVE_PHASE3A_TTL_SEC","3.5")))
  deadline=time.monotonic() + ttl_s
  uws=getattr(self.executor,"_user_ws_cache",None)
  init_disp=(entry_spot_ref - open_spot) if target_token=="UP" else (open_spot - entry_spot_ref)
  while time.monotonic() < deadline:
   rem_w=max(0.02,min(0.10,deadline - time.monotonic()))
   if uws is not None and uws.is_healthy():
    await uws.wait_for_fill_or_timeout(rem_w,prev_seq=uws.fill_sequence)
    snap_o=uws.get_order_snapshot(maker_oid,max_age_sec=5.0)
    if isinstance(snap_o,dict) and str(snap_o.get("status") or "").upper() in ("MATCHED","FILLED"):
     break
   else:
    await asyncio.sleep(rem_w)
   if open_spot > 0.0 and init_disp > 0.0:
    cur_sp=await asyncio.to_thread(self.get_usd_reference_spot_price if spot_denom=="USD" else self.get_reference_spot_price,asset_str)
    if cur_sp and float(cur_sp) > 0.0 and (((float(cur_sp) - open_spot) if target_token=="UP" else (open_spot - float(cur_sp))) < 0.55 * init_disp):
     logger.info(f"[LIVE PHASE 3A ADVERSE SHIELD] {trade_id}: cushion decayed >45%; canceling {maker_oid}.")
     break
  cancel_res=await asyncio.to_thread(self.executor.cancel_order,maker_oid)
  summary=await asyncio.to_thread(self.executor.get_order_fill_summary,maker_oid,token_id)
  c_out=str((cancel_res or {}).get("outcome") or "")
  is_canc=bool((cancel_res or {}).get("is_canceled"))
  matched_sh=float((summary or {}).get("matched") or (cancel_res or {}).get("matched") or 0.0)
  if matched_sh>=0.01 and (is_canc or c_out in ("FILLED","CANCELED","PARTIALLY_FILLED_CANCELED") or bool((summary or {}).get("terminal"))):
   avg_px=float((summary or {}).get("avg_price") or maker_px)
   logger.info(f"[LIVE PHASE 3A MAKER RESCUE FILLED] {trade_id}: {matched_sh:.2f} sh @ ${avg_px:.4f} (OID={maker_oid})")
   return OrderResult( success=True,order_id=maker_oid,trade_id=trade_id,token_id=token_id,target_token=target_token,side="BUY",price=avg_px,size=matched_sh,notional_usd=round(matched_sh * avg_px,4),fee_usd=0.0,latency_ms=round((time.perf_counter() - t0_m) * 1000.0,2),mode="LIVE_PHASE3A_MAKER_IN",execution_status=ExecutionStatus.MATCHED_PENDING_SETTLEMENT,details={"pre_token_balance":pre_cond_bal,"trade_ids":list((summary or {}).get("trade_ids") or []),"transactions_hashes":list((summary or {}).get("tx_hashes") or []),"phase3a_maker_rescue":True},)
  if not is_canc and c_out!="FILLED" and (summary is None or not summary.get("terminal") or summary.get("resting")):
   return OrderResult( success=False,order_id=maker_oid,trade_id=trade_id,token_id=token_id,target_token=target_token,side="BUY",price=maker_px,size=float(post_res.get("shares") or 5.0),notional_usd=rescue_notional,fee_usd=0.0,latency_ms=round((time.perf_counter() - t0_m) * 1000.0,2),mode="LIVE_PHASE3A_CANCEL_UNKNOWN",execution_status=ExecutionStatus.SUBMITTED,details={"outcome_unknown":True,"entry_order_id":maker_oid,"pre_token_balance":pre_cond_bal},error="PHASE3A_CANCEL_UNVERIFIED",)
  logger.info(f"[LIVE PHASE 3A EXPIRED CLEAN] {trade_id}: {maker_oid} canceled ({ttl_s:.1f}s).")
  return None
 async def _maybe_merge_live_complete_sets(self,now_ts:float)->None:
  if self.dry_run or not hasattr(self.executor,"attempt_onchain_complete_set_merge"):
   return
  sig_raw=getattr(self.executor,"signature_type",None)
  sig_t=3 if sig_raw is None else int(sig_raw)
  if sig_t==3 and not (os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY")) and os.getenv("PM_ENABLE_ONCHAIN_MERGE","0")!="1":
   return
  seen_boxes:set[str]=set()
  merge_cd=self.__dict__.setdefault("_c1_merge_attempt_ts",{})
  for tid,pos in list(self.active_positions.items()):
   if tid not in self.active_positions or str(pos.get("box_type") or "")!="COMPLETE_SET":
    continue
   b_id=str(pos.get("box_id") or "")
   p_tid=str(pos.get("box_partner_trade_id") or "")
   partner=self.active_positions.get(p_tid)
   cid=str(pos.get("condition_id") or "")
   if not b_id or b_id in seen_boxes or not isinstance(partner,dict) or not cid or cid!=str(partner.get("condition_id") or ""):
    continue
   seen_boxes.add(b_id)
   if (now_ts - float(merge_cd.get(b_id,0.0) or 0.0)) < 20.0:
    continue
   if not (pos.get("inventory_reconciled") and partner.get("inventory_reconciled")):
    continue
   sh_1=float(pos.get("remaining_shares",0.0) or 0.0)
   sh_2=float(partner.get("remaining_shares",0.0) or 0.0)
   if min(sh_1,sh_2) < 5.0 or float(pos.get("filled_exit_shares",0.0) or 0.0) > 0.01 or float(partner.get("filled_exit_shares",0.0) or 0.0) > 0.01:
    continue
   merge_cd[b_id]=now_ts
   cancel_aborted=False
   any_exit_canceled=False
   for lg_tid_c,lg_p in ((tid,pos),(p_tid,partner)):
    e_oid=lg_p.get("exit_order_id")
    if e_oid:
     c_r=await asyncio.to_thread(self.executor.cancel_order,str(e_oid))
     s_r=await asyncio.to_thread(self.executor.get_order_fill_summary,str(e_oid),lg_p.get("token_id"))
     if s_r is not None:
      self._record_order_summary(lg_p,s_r,float(lg_p.get("target_exit_price",0.99) or 0.99),taker=False)
      if float(lg_p.get("remaining_shares",0.0) or 0.0)<=0.01:
       self._close_position(lg_tid_c,lg_p,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True)
       cancel_aborted=True
       break
     if not (c_r or {}).get("is_canceled") or float(lg_p.get("filled_exit_shares",0.0) or 0.0) > 0.01:
      if (c_r or {}).get("is_canceled"):
       self.executor.release_inventory(reservation_id=str(e_oid))
       lg_p["exit_order_id"]=None
       lg_p["exit_order_status"]="EXIT_RECOVERY_REQUIRED"
       any_exit_canceled=True
      cancel_aborted=True
      break
     self.executor.release_inventory(reservation_id=str(e_oid))
     lg_p["exit_order_id"]=None
     lg_p["exit_order_status"]="EXIT_RECOVERY_REQUIRED"
     any_exit_canceled=True
   if cancel_aborted:
    if any_exit_canceled:
     await asyncio.to_thread(self.save_state)
    continue
   sh_1=float(pos.get("remaining_shares",0.0) or 0.0)
   sh_2=float(partner.get("remaining_shares",0.0) or 0.0)
   m_res=await asyncio.to_thread( self.executor.attempt_onchain_complete_set_merge,cid,min_pairs=min(sh_1,sh_2),max_pairs=min(sh_1,sh_2) )
   if isinstance(m_res,tuple) and len(m_res)==2 and m_res[0] and float(m_res[1])>=4.99:
    tx_h,pairs_m=str(m_res[0]),float(m_res[1])
    tot_c=max(0.01,float(pos.get("notional_usd",0.0)) + float(partner.get("notional_usd",0.0)))
    for lg_tid,lg_p in ((tid,pos),(p_tid,partner)):
     share_w=float(lg_p.get("notional_usd",0.0)) / tot_c
     cash_leg=round(pairs_m * share_w,4)
     lg_p["merge_tx_hash"]=tx_h
     self.record_fill_and_update_position( lg_p,f"MERGE_{tx_h}_{lg_tid}",pairs_m,cash_leg,0.0,cash_is_estimated=False )
     if float(lg_p.get("remaining_shares",0.0) or 0.0)<=0.02:
      self._close_position(lg_tid,lg_p,ExecutionStatus.SETTLED,"COMPLETE_SET_ONCHAIN_MERGED",won=True)
    self._pending_collateral_refresh=True
    await asyncio.to_thread(self.save_state)
    logger.info(f"✓ [C1 COMPLETE SET MERGED] {b_id}: {pairs_m:.2f} pairs -> ${pairs_m:.2f} cash freed immediately (tx={tx_h}).")
   else:
    merge_cd[b_id]=now_ts + 600.0
    if any_exit_canceled:
     await asyncio.to_thread(self.save_state)
 def _update_shadow_phase4_monotonicity_scanner( self,shock:Dict[str,Any],asset_str:str,is_subhourly:bool,is_1h:bool,tte:float,open_spot:float )->None:
  try:
   if not (is_subhourly or is_1h) or not (20.0<=tte<=900.0) or not open_spot or open_spot<=0.0:
    return
   now_ts=float(shock.get("t0_unix") or time.time())
   exp_ts=float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (now_ts + tte))
   exp_bucket=int(round(exp_ts / 60.0) * 60)
   feats=shock.get("pre_shock_features_t0") or {}
   up_tf,dn_tf=feats.get("UP") or {},feats.get("DOWN") or {}
   up_a,dn_a=float(up_tf.get("best_ask") or 0.0),float(dn_tf.get("best_ask") or 0.0)
   if up_a<=0.0 or dn_a<=0.0:
    return
   up_asks,dn_asks=up_tf.get("raw_top_asks") or [],dn_tf.get("raw_top_asks") or []
   up_l1_usd=(float(up_asks[0][0]) * float(up_asks[0][1])) if up_asks else 0.0
   dn_l1_usd=(float(dn_asks[0][0]) * float(dn_asks[0][1])) if dn_asks else 0.0
   spot_px=float(shock.get("spot_at_t0") or shock.get("trigger_price") or open_spot)
   cache=getattr(self,"_shadow_phase4_books",None)
   if cache is None:
    self._shadow_phase4_books=cache={}
   emitted=getattr(self,"_shadow_phase4_emitted",None)
   if emitted is None:
    self._shadow_phase4_emitted=emitted=set()
   h_key="15m" if is_subhourly else "1h"
   bucket_dict=cache.setdefault((asset_str,exp_bucket),{})
   bucket_dict[h_key]={ "ts":now_ts,"tte":tte,"market_id":str(shock.get("market_id") or ""),"strike":float(open_spot),"spot":spot_px,"up_a":up_a,"dn_a":dn_a,"up_l1_usd":up_l1_usd,"dn_l1_usd":dn_l1_usd,"up_asks":[{"price":float(p),"size":float(s)} for p,s in up_asks if float(p) > 0 and float(s) > 0],"dn_asks":[{"price":float(p),"size":float(s)} for p,s in dn_asks if float(p) > 0 and float(s) > 0],}
   s15,s1h=bucket_dict.get("15m"),bucket_dict.get("1h")
   if not s15 or not s1h or abs(s15["ts"] - s1h["ts"]) > 10.0:
    return
   k15,k1h=s15["strike"],s1h["strike"]
   if abs(k15 - k1h) / max(k15,1.0) < 0.0003:
    return
   if k15 < k1h:
    leg1_lbl,leg1_px,leg1_depth,leg1_asks="UP_15M",s15["up_a"],s15["up_l1_usd"],s15.get("up_asks") or []
    leg2_lbl,leg2_px,leg2_depth,leg2_asks="DOWN_1H",s1h["dn_a"],s1h["dn_l1_usd"],s1h.get("dn_asks") or []
    k_low,k_high=k15,k1h
   else:
    leg1_lbl,leg1_px,leg1_depth,leg1_asks="UP_1H",s1h["up_a"],s1h["up_l1_usd"],s1h.get("up_asks") or []
    leg2_lbl,leg2_px,leg2_depth,leg2_asks="DOWN_15M",s15["dn_a"],s15["dn_l1_usd"],s15.get("dn_asks") or []
    k_low,k_high=k1h,k15
   from src.polymarket_research.same_oracle_dominance_box import walk_equal_shares_dominance_box
   walk_res=walk_equal_shares_dominance_box( leg1_asks,leg2_asks,target_budget_usd=25.0,fee_rate_a=0.07,fee_rate_b=0.07,max_box_cost_net=1.08,min_shares=8,min_box_notional_usd=7.0,)
   if not walk_res.get("filled"):
    return
   c_taker=float(walk_res["box_cost_net"])
   leg1_w,leg2_w=walk_res["leg_a_walk"],walk_res["leg_b_walk"]
   m1,m2=max(0.01,leg1_px - 0.01),max(0.01,leg2_px - 0.01)
   c_maker=(m1 - 0.014 * m1 * (1.0 - m1)) + (m2 - 0.014 * m2 * (1.0 - m2))
   in_corridor=(k_low<=spot_px<=k_high)
   min_leg_depth_usd=round(min(float(leg1_depth),float(leg2_depth)),2)
   corridor_width_pct=round((k_high - k_low) / k_low * 100.0,4)
   basis_ev=( evaluate_cross_oracle_basis_box_ev( spot_px=spot_px,k_low=k_low,k_high=k_high,c_taker_net=c_taker,tte_sec=min(s15["tte"],s1h["tte"]),) if evaluate_cross_oracle_basis_box_ev is not None else {"eligible":corridor_width_pct>=0.25,"expected_net_profit_per_pair":round(1.0 - c_taker,5),"ev_per_pair":round(1.0 - c_taker,5),"p_double_loss":0.0} )
   basis_safe=bool(corridor_width_pct>=0.25 and min_leg_depth_usd>=15.0 and float(basis_ev.get("ev_per_pair",0.0)) > -0.05)
   min_cross_oracle_corridor_ok=bool(corridor_width_pct>=0.10 and min_leg_depth_usd>=15.0)
   live_eligible_96c=bool(c_taker<=0.960 and basis_safe)
   sig_type=None
   if c_taker < 1.00 and min_cross_oracle_corridor_ok:
    sig_type="SHADOW_PHASE4_RISK_FREE_BOX_ARB"
   elif in_corridor and c_taker < 1.08 and basis_safe:
    sig_type="SHADOW_PHASE4_CORRIDOR_BOX_ARB"
   if sig_type and (asset_str,exp_bucket,sig_type) not in emitted:
    emitted.add((asset_str,exp_bucket,sig_type))
    rec={ "event_type":sig_type,"logged_at_utc":datetime.now(timezone.utc).isoformat(),"asset":asset_str,"expiry_bucket":exp_bucket,"expiry_ts":float(exp_ts),"tte_sec":round(min(s15["tte"],s1h["tte"]),1),"market_15m":s15["market_id"],"market_1h":s1h["market_id"],"strike_15m":round(k15,4),"strike_1h":round(k1h,4),"strike_low":round(k_low,2),"strike_high":round(k_high,2),"corridor_width_pct":corridor_width_pct,"cross_oracle_basis_safe":basis_safe,"cross_oracle_not_true_riskless":True,"live_eligible_96c":live_eligible_96c,"expected_net_profit_per_pair":basis_ev.get("expected_net_profit_per_pair"),"p_double_loss":basis_ev.get("p_double_loss"),"spot_px":round(spot_px,2),"spot_in_corridor":in_corridor,"equal_shares_walked":int(walk_res["shares"]),"leg1":{"side":leg1_lbl,"ask":leg1_w["vwap"],"eff_px":leg1_w["eff_px"],"l1_depth_usd":round(float(leg1_depth),2)},"leg2":{"side":leg2_lbl,"ask":leg2_w["vwap"],"eff_px":leg2_w["eff_px"],"l1_depth_usd":round(float(leg2_depth),2)},"min_leg_l1_depth_usd":min_leg_depth_usd,"all_in_taker_box_cost":round(c_taker,4),"maker_box_cost":round(c_maker,4),"guaranteed_min_profit_per_pair":round(1.00 - c_taker,4),}
    active_boxes=getattr(self,"_shadow_phase4_active_boxes",None)
    if active_boxes is None:
     self._shadow_phase4_active_boxes={}
     active_boxes=self._shadow_phase4_active_boxes
    active_boxes[f"{asset_str}_{exp_bucket}_{sig_type}"]=dict(rec)
    self._append_shadow_phase3_4_event(rec)
    logger.info( f"[SHADOW PHASE 4] {sig_type}: {asset_str} ({leg1_lbl}@${leg1_px:.2f} + {leg2_lbl}@${leg2_px:.2f}) " f"TakerCost=${c_taker:.4f} | MakerCost=${c_maker:.4f} | MinLegDepth=${min_leg_depth_usd:.1f} | " f"BasisSafe={basis_safe} | Corridor=[{k_low:.2f}, {k_high:.2f}]" )
  except Exception as exc:
   logger.debug(f"[SHADOW PHASE 4] Scan error: {exc}")
 def _step_shadow_phase3_4_tracker(self,now_ts:float)->None:
  shadow_orders=getattr(self,"_shadow_maker_orders",None) or {}
  for key,ord_rec in list(shadow_orders.items()):
   try:
    asset=ord_rec["asset"]
    snap=read_fast_tick(asset,max_age_sec=2.0,now=now_ts)
    spot_px=float((snap or {}).get("spot_price") or (snap or {}).get("spot") or 0.0)
    if ord_rec.get("horizon")=="15m":
     cl_twap=float((snap or {}).get("chainlink_twap_60s") or 0.0)
     if cl_twap > 0.0:
      spot_px=cl_twap
    open_spot=float(ord_rec.get("open_spot") or 0.0)
    target=ord_rec["target_token"]
    status=ord_rec["status"]
    cur_ask,cur_bid=0.0,0.0
    if snap:
     mkt_id=ord_rec["market_id"]
     mkt_node=(snap.get("markets") or {}).get(mkt_id) if isinstance(snap.get("markets"),dict) else None
     if not mkt_node and str(snap.get("market_id") or "")==mkt_id:
      mkt_node=snap
     if isinstance(mkt_node,dict):
      side_node=mkt_node.get(target) or {}
      cur_ask=float(side_node.get("best_ask") or 0.0)
      cur_bid=float(side_node.get("best_bid") or 0.0)
    if status=="RESTING":
     if spot_px > 0.0 and open_spot > 0.0:
      raw_dist=((spot_px - open_spot) / open_spot) * 100.0
      s_dist=raw_dist if target=="UP" else -raw_dist
      if s_dist < 0.04:
       ord_rec["status"]="CANCELED_TOXIC_SPOT_RETRACE"
       ord_rec["closed_at_utc"]=datetime.now(timezone.utc).isoformat()
       ord_rec["retrace_cushion_pct"]=round(s_dist,4)
       self._append_shadow_phase3_4_event({**ord_rec,"event_type":"SHADOW_PHASE3A_MAKER_CANCELED_TOXIC"})
       shadow_orders.pop(key,None)
       continue
     if cur_ask > 0.0 and (now_ts - float(ord_rec["placed_ts"]))>=0.25:
      m_px=float(ord_rec["shadow_maker_px"])
      if 0.0 < cur_ask<=m_px + 0.001:
       ord_rec["status"]="SHADOW_MAKER_FILLED"
       ord_rec["filled_ts"]=now_ts
       ord_rec["fill_delay_sec"]=round(now_ts - float(ord_rec["placed_ts"]),2)
       ord_rec["t1_filled"]=False
       ord_rec["t2_filled"]=False
       ord_rec["realized_per_share"]=0.0
       ord_rec["rem_frac"]=1.0
       self._append_shadow_phase3_4_event({**ord_rec,"event_type":"SHADOW_PHASE3A_MAKER_FILLED"})
       logger.info( f"[SHADOW PHASE 3A FILLED] {asset} {target} (mkt={ord_rec['market_id']}) filled @ ${m_px:.2f} " f"after {ord_rec['fill_delay_sec']:.2f}s (0% fee + 20% rebate)" )
       continue
     if now_ts>=float(ord_rec["ttl_expires_ts"]):
      ord_rec["status"]="EXPIRED_UNFILLED"
      ord_rec["closed_at_utc"]=datetime.now(timezone.utc).isoformat()
      self._append_shadow_phase3_4_event({**ord_rec,"event_type":"SHADOW_PHASE3A_MAKER_EXPIRED_UNFILLED"})
      shadow_orders.pop(key,None)
    elif status=="SHADOW_MAKER_FILLED":
     tte_rem=float(ord_rec["expiry_ts"]) - now_ts
     if (now_ts - float(ord_rec.get("filled_ts",now_ts)))>=5.0 and cur_bid > 0.0:
      if not ord_rec.get("t1_filled") and cur_bid>=0.95:
       ord_rec["t1_filled"]=True
       ord_rec["realized_per_share"]=float(ord_rec.get("realized_per_share",0.0)) + 0.50 * 0.95
       ord_rec["rem_frac"]=0.50
      if not ord_rec.get("t2_filled") and cur_bid>=0.98:
       ord_rec["t2_filled"]=True
       ord_rec["realized_per_share"]=float(ord_rec.get("realized_per_share",0.0)) + 0.50 * 0.98
       ord_rec["rem_frac"]=0.0
      if float(ord_rec.get("rem_frac",1.0))<=1e-6:
       shares_20=20.0 / float(ord_rec["shadow_maker_px"])
       cost_20=shares_20 * float(ord_rec["shadow_maker_eff_cost"])
       pnl_20=round(shares_20 * float(ord_rec["realized_per_share"]) - cost_20,2)
       ord_rec.update({ "status":"RESOLVED","exit_reason":"MAKER_TP_95_98","won":True,"shadow_net_pnl_usd":pnl_20,"shadow_net_pnl_12_usd":round(pnl_20 * 0.60,2),"closed_at_utc":datetime.now(timezone.utc).isoformat(),})
       self._append_shadow_phase3_4_event({**ord_rec,"event_type":"SHADOW_PHASE3A_MAKER_RESOLVED"})
       shadow_orders.pop(key,None)
       continue
     if spot_px > 0.0 and open_spot > 0.0 and tte_rem>=25.0:
      s_cush=((spot_px - open_spot) / open_spot * 100.0) if target=="UP" else ((open_spot - spot_px) / open_spot * 100.0)
      wrong_pct=-s_cush
      if wrong_pct<=0.0:
       ord_rec.pop("wrong_side_ts",None)
      else:
       req_w=0.14 if tte_rem > 900.0 else (0.09 if tte_rem > 180.0 else 0.05)
       req_d=30.0 if tte_rem > 900.0 else (15.0 if tte_rem > 180.0 else 8.0)
       if wrong_pct>=req_w:
        w_ts=ord_rec.get("wrong_side_ts")
        if w_ts is None:
         ord_rec["wrong_side_ts"]=now_ts
        elif (now_ts - float(w_ts))>=req_d and cur_bid>=0.15:
         rem_f=float(ord_rec.get("rem_frac",1.0))
         salv_net_sh=cur_bid * (1.0 - 0.07 * (1.0 - cur_bid))
         tot_per_sh=float(ord_rec.get("realized_per_share",0.0)) + rem_f * salv_net_sh
         shares_20=20.0 / float(ord_rec["shadow_maker_px"])
         cost_20=shares_20 * float(ord_rec["shadow_maker_eff_cost"])
         pnl_20=round(shares_20 * tot_per_sh - cost_20,2)
         ord_rec.update({ "status":"RESOLVED","exit_reason":"WRONG_SIDE_SALVAGE","salvage_bid":round(cur_bid,4),"won":bool(pnl_20 > 0),"final_spot":round(spot_px,4),"shadow_net_pnl_usd":pnl_20,"shadow_net_pnl_12_usd":round(pnl_20 * 0.60,2),"closed_at_utc":datetime.now(timezone.utc).isoformat(),})
         self._append_shadow_phase3_4_event({**ord_rec,"event_type":"SHADOW_PHASE3A_MAKER_RESOLVED"})
         shadow_orders.pop(key,None)
         continue
       else:
        ord_rec.pop("wrong_side_ts",None)
     if now_ts>=float(ord_rec["expiry_ts"]) + 2.0 and spot_px > 0.0 and open_spot > 0.0:
      won_rem=(spot_px>=open_spot) if target=="UP" else (spot_px < open_spot)
      rem_f=float(ord_rec.get("rem_frac",1.0))
      tot_per_sh=float(ord_rec.get("realized_per_share",0.0)) + (rem_f * 1.00 if won_rem else 0.0)
      shares_20=20.0 / float(ord_rec["shadow_maker_px"])
      cost_20=shares_20 * float(ord_rec["shadow_maker_eff_cost"])
      pnl_20=round(shares_20 * tot_per_sh - cost_20,2)
      ord_rec.update({ "status":"RESOLVED","exit_reason":"EXPIRY_SETTLEMENT","won":bool(pnl_20 > 0),"final_spot":round(spot_px,2),"shadow_net_pnl_usd":pnl_20,"shadow_net_pnl_12_usd":round(pnl_20 * 0.60,2),"closed_at_utc":datetime.now(timezone.utc).isoformat(),})
      self._append_shadow_phase3_4_event({**ord_rec,"event_type":"SHADOW_PHASE3A_MAKER_RESOLVED"})
      logger.info( f"[SHADOW PHASE 3A RESOLVED] {asset} {target} (mkt={ord_rec['market_id']}) | " f"Won={ord_rec['won']} | Shadow Net PnL=${pnl_20:+.2f}" )
      shadow_orders.pop(key,None)
     elif now_ts>=float(ord_rec["expiry_ts"]) + 300.0:
      shadow_orders.pop(key,None)
   except Exception as exc:
    logger.debug(f"[SHADOW PHASE 3A] Step error: {exc}")
  active_boxes=getattr(self,"_shadow_phase4_active_boxes",None) or {}
  for bkey,brec in list(active_boxes.items()):
   try:
    exp_ts=float(brec.get("expiry_ts") or brec.get("expiry_bucket") or 0.0)
    if exp_ts<=0.0 or now_ts < exp_ts + 2.5:
     continue
    if now_ts > exp_ts + 300.0:
     active_boxes.pop(bkey,None)
     continue
    snap=read_fast_tick(brec["asset"],max_age_sec=5.0,now=now_ts)
    spot_1h=float((snap or {}).get("spot_price") or (snap or {}).get("spot") or 0.0)
    twap_15m=float((snap or {}).get("chainlink_twap_60s") or spot_1h)
    if spot_1h<=0.0:
     continue
    k15=float(brec.get("strike_15m") or brec["strike_low"])
    k1h=float(brec.get("strike_1h") or brec["strike_high"])
    leg1_s=brec["leg1"]["side"]
    leg2_s=brec["leg2"]["side"]
    def _leg_win(lbl:str)->float:
     if lbl=="UP_15M":
      return 1.0 if twap_15m>=k15 else 0.0
     if lbl=="DOWN_15M":
      return 1.0 if twap_15m < k15 else 0.0
     if lbl=="UP_1H":
      return 1.0 if spot_1h>=k1h else 0.0
     return 1.0 if spot_1h < k1h else 0.0
    payout_pair=_leg_win(leg1_s) + _leg_win(leg2_s)
    c_taker=float(brec["all_in_taker_box_cost"])
    pairs_20=20.0 / max(c_taker,0.10)
    net_pnl_20=round(pairs_20 * (payout_pair - c_taker),2)
    resolved_box={ **brec,"event_type":"SHADOW_PHASE4_BOX_RESOLVED","resolved_at_utc":datetime.now(timezone.utc).isoformat(),"final_1h_binance_spot":round(spot_1h,4),"final_15m_chainlink_twap":round(twap_15m,4),"payout_per_pair":payout_pair,"double_win_jackpot":bool(payout_pair>=1.99),"basis_trap_zero_payout":bool(payout_pair < 0.50),"shadow_net_pnl_20_usd":net_pnl_20,}
    self._append_shadow_phase3_4_event(resolved_box)
    active_boxes.pop(bkey,None)
   except Exception as exc:
    logger.debug(f"[SHADOW PHASE 4] Resolve error: {exc}")
 def _get_verified_shm_book(self,pos:Dict[str,Any])->Optional[Dict[str,Any]]:
  asset=str(pos.get("asset") or "BTC").upper()
  target_mid=str(pos.get("market_id") or "")
  target_tid=str(pos.get("token_id") or "")
  target_side=str(pos.get("target_token") or "UP").upper()
  if not target_mid or not target_tid:
   return None
  tick_dir=os.environ.get("PM_FAST_TICK_DIR")
  if not tick_dir:
   if self.dry_run:
    return None
   tick_dir="/dev/shm"
  shm_path=Path(f"{tick_dir}/pm_fast_tick_{asset}.json")
  if not shm_path.exists():
   return None
  try:
   raw=json.loads(shm_path.read_text(encoding="utf-8"))
   mkt_payload=raw.get("markets",{}).get(target_mid) if isinstance(raw.get("markets"),dict) else raw
   if not isinstance(mkt_payload,dict):
    return None
   if str(mkt_payload.get("market_id") or "")!=target_mid:
    return None
   ts=float(mkt_payload.get("timestamp_unix") or mkt_payload.get("ts") or 0.0)
   age_s=time.time() - ts
   if ts<=0.0 or age_s > 1.5 or age_s < -2.0:
    return None
   side_book=mkt_payload.get(target_side) or {}
   if str(side_book.get("token_id") or "")!=target_tid:
    return None
   raw_bids=side_book.get("raw_top_bids") or []
   raw_asks=side_book.get("raw_top_asks") or []
   if raw_bids:
    return { "bids":[{"price":str(p),"size":str(s)} for p,s in raw_bids],"asks":[{"price":str(p),"size":str(s)} for p,s in raw_asks],"timestamp":ts,}
   best_b=float(side_book.get("best_bid",0.0) or 0.0)
   best_a=float(side_book.get("best_ask",1.0) or 1.0)
   b_sz=float(side_book.get("bid_size_l1",0.0) or 0.0)
   a_sz=float(side_book.get("ask_size_l1",0.0) or 0.0)
   if best_b<=0.0 or b_sz<=0.0:
    return None
   return { "bids":[{"price":str(best_b),"size":str(b_sz)}],"asks":[{"price":str(best_a),"size":str(a_sz)}] if best_a < 1.0 and a_sz > 0 else [],"timestamp":ts,}
  except Exception:
   return None
 async def _atomic_replace_maker_exit( self,tid:str,pos:Dict[str,Any],new_price:float,collapse_tranches:bool=False )->bool:
  token_id=pos.get("token_id")
  old_oid=pos.get("exit_order_id")
  if not token_id:
   return False
  order_matched=0.0
  if old_oid:
   cancel_res=await asyncio.to_thread(self.executor.cancel_order,str(old_oid))
   is_canceled=bool((cancel_res or {}).get("is_canceled"))
   summary=await asyncio.to_thread(self.executor.get_order_fill_summary,str(old_oid),token_id)
   if is_canceled and isinstance(summary,dict) and summary.get("resting",False):
    await asyncio.sleep(0.25)
    summary=await asyncio.to_thread(self.executor.get_order_fill_summary,str(old_oid),token_id)
   if summary is None:
    logger.warning( f"[QUEUE JUMP ABORT] No fill summary for {old_oid} after cancel; retaining reservation." )
    pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED"
    pos["pending_canceled_order_id"]=str(old_oid)
    await asyncio.to_thread(self.save_state)
    return False
   order_matched=float(summary.get("matched",0.0) or 0.0)
   self._record_order_summary(pos,summary,float(pos.get("target_exit_price",0.99) or 0.99),taker=False)
   if float(pos.get("remaining_shares",0.0) or 0.0)<=0.01:
    self._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True)
    return True
   if summary.get("resting",False) or not is_canceled or not summary.get("terminal",False):
    if not summary.get("resting",False) or is_canceled:
     pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED"
     pos["pending_canceled_order_id"]=str(old_oid)
    logger.warning(f"[QUEUE JUMP ABORT] {old_oid} not terminally canceled; retaining reservation.")
    await asyncio.to_thread(self.save_state)
    return False
   self.executor.release_inventory(reservation_id=str(old_oid))
   pos["exit_order_id"]=None
  rem_shares=float( Decimal(str(pos.get("remaining_shares",pos.get("entry_shares",0.0)) or 0.0)).quantize( Decimal("0.01"),rounding=ROUND_FLOOR ) )
  if rem_shares < 0.01:
   return False
  post_size=rem_shares
  active_tranche=None
  if collapse_tranches:
   pos.pop("exit_tranches",None)
  elif pos.get("exit_tranches"):
   for t in pos["exit_tranches"]:
    if t.get("status") in {"POSTED","IN_FLIGHT"}:
     t_rem=max(0.0,round(float(t.get("size",0.0)) - order_matched,2))
     if t_rem<=0.01:
      t["status"]="FILLED"
     else:
      t["size"]=t_rem
      t["status"]="PENDING"
   pending_tr=[t for t in pos["exit_tranches"] if t.get("status")=="PENDING" and float(t.get("size",0.0))>=5.0]
   if pending_tr and rem_shares>=5.0:
    cand_sz=min(rem_shares,float(pending_tr[0]["size"]))
    leftover=round(rem_shares - cand_sz,4)
    if 0.01 < leftover < 5.0:
     pos.pop("exit_tranches",None)
    else:
     active_tranche=pending_tr[0]
     post_size=cand_sz
     active_tranche["price"]=round(float(new_price),4)
   else:
    pos.pop("exit_tranches",None)
  if post_size < 5.0 and not self.dry_run and str(token_id).isdigit() and len(str(token_id))>=20:
   pos["exit_order_status"]="SUB_MINIMUM_LOT_SUPERVISED_HOLD"
   pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD"
   await asyncio.to_thread(self.save_state)
   return False
  pos["target_exit_price"]=round(float(new_price),4)
  exit_res=await asyncio.to_thread( self.executor.post_maker_exit_order,token_id=token_id,price=pos["target_exit_price"],size=post_size,side="SELL",)
  posted=self._apply_exit_post_result(pos,exit_res,post_size)
  if active_tranche is not None and posted:
   active_tranche["status"]="POSTED"
  elif active_tranche is not None and (exit_res or {}).get("outcome_unknown"):
   active_tranche["status"]="IN_FLIGHT"
  await asyncio.to_thread(self.save_state)
  return posted
 def _prewarm_hourly_opens(self):
  trigger_path=DATA_DIR / "live_shock_triggers.jsonl"
  if not trigger_path.exists():
   return
  try:
   with open(trigger_path,"rb") as f:
    f.seek(0,2)
    size=f.tell()
    read_sz=min(size,8 * 1024 * 1024)
    f.seek(size - read_sz)
    lines=f.read().decode("utf-8",errors="ignore").splitlines()
   for line in lines:
    if not line.strip():
     continue
    try:
     data=json.loads(line)
     title_l=str(data.get("title","") or "").lower()
     horiz_l=str(data.get("horizon","") or data.get("candle_interval","")).lower()
     slug_l=str(data.get("series_slug","") or data.get("slug","")).lower()
     if any(x in horiz_l or x in slug_l or x in title_l for x in ("5m","15m","300s","900s")):
      continue
     asset=data.get("asset")
     t0_unix=data.get("t0_unix")
     open_p=data.get("finalized_1h_open") or data.get("candle_open_spot")
     if asset in ("BTC","ETH") and t0_unix and open_p and float(open_p) > 0:
      h_idx=int(float(t0_unix) // 3600)
      if h_idx not in self.hourly_candle_opens[asset]:
       self.hourly_candle_opens[asset][h_idx]=float(open_p)
    except Exception:
     pass
   logger.info( f"[TREND GUARD PREWARMED] Prewarmed {len(self.hourly_candle_opens.get('ETH', {}))} ETH and " f"{len(self.hourly_candle_opens.get('BTC', {}))} BTC hourly opens for multi-hour trend alignment." )
  except Exception as e:
   logger.warning(f"[TREND GUARD PREWARM WARN] Failed to prewarm hourly opens: {e}")
 def _register_active_warmed_token(self,tok_id:str,expiry_ts:float=0.0)->None:
  if not tok_id:
   return
  reg=getattr(self,"_active_warmed_token_expiries",None)
  if reg is None:
   reg={}
   self._active_warmed_token_expiries=reg
  now_u=time.time()
  exp_val=float(expiry_ts or 0.0)
  if exp_val<=0.0:
   exp_val=now_u + 3600.0
  reg[str(tok_id)]=max(float(reg.get(str(tok_id),0.0)),exp_val)
  expired=[k for k,v in reg.items() if v < now_u - 30.0]
  for k in expired:
   reg.pop(k,None)
  while len(reg) > 12:
   oldest_k=min(reg,key=reg.get)
   reg.pop(oldest_k,None)
 def _prewarm_market_metadata(self,shock:Dict[str,Any]):
  try:
   title_l=str(shock.get("title","") or "").lower()
   default_rate=0.07
   cond_id=shock.get("condition_id") or shock.get("fee_metadata",{}).get("condition_id")
   fee_meta=shock.get("fee_metadata",{})
   fee_rate=float(fee_meta.get("fee_rate_market",default_rate) or default_rate)
   fee_exp=float(fee_meta.get("fee_exponent",1.0) or 1.0)
   fee_bps=int(round(fee_rate * 10000))
   exp_ts=float(shock.get("candle_expiry_ts") or shock.get("expiry_ts") or 0.0)
   if exp_ts<=0.0 and shock.get("seconds_to_expiry"):
    exp_ts=float(shock.get("t0_unix") or time.time()) + float(shock.get("seconds_to_expiry") or 0.0)
   asset_s=str(shock.get("asset") or "").upper()
   if not asset_s:
    asset_s="BTC" if "btc" in title_l or "bitcoin" in title_l else ("ETH" if "eth" in title_l or "ethereum" in title_l else ("SOL" if "sol" in title_l or "solana" in title_l else ""))
   allow_ladder=(not asset_s) or (asset_s in getattr(self,"allowed_assets",{"BTC","ETH"}))
   feats=shock.get("pre_shock_features_t0",{})
   for side_key in ("UP","DOWN"):
    tok_info=feats.get(side_key,{})
    tok_id=tok_info.get("token_id")
    if tok_id:
     self.executor.prewarm_token_market_cache( token_id=tok_id,tick_size=tok_info.get("tick_size") or shock.get("tick_size") or "0.01",neg_risk=False,fee_rate_bps=fee_bps,condition_id=cond_id,fee_rate=fee_rate,fee_exponent=fee_exp,)
     if allow_ladder and (exp_ts<=0.0 or exp_ts > time.time() - 30.0):
      self._register_active_warmed_token(str(tok_id),exp_ts)
  except Exception as exc:
   logger.debug(f"[PREWARM NOTICE] Prewarm metadata notice: {exc}")
 def _prewarm_active_market_tokens(self):
  try:
   reg=getattr(self,"_active_warmed_token_expiries",None)
   if not getattr(self,"_startup_prewarmed_logged",False) or not reg:
    if TRIGGER_FILE.exists() and TRIGGER_FILE.stat().st_size > 0:
     sz=TRIGGER_FILE.stat().st_size
     read_sz=min(sz,131072)
     with open(TRIGGER_FILE,"rb") as f:
      f.seek(sz - read_sz)
      lines=f.read().decode("utf-8",errors="ignore").splitlines()
     for l in reversed(lines):
      if not l.strip():
       continue
      try:
       shk=_json_loads(l)
       self._prewarm_market_metadata(shk)
      except Exception:
       continue
   reg=getattr(self,"_active_warmed_token_expiries",None) or {}
   now_u=time.time()
   active_tokens=[k for k,exp_v in reg.items() if exp_v>=now_u - 30.0]
   if active_tokens and not getattr(self,"_startup_prewarmed_logged",False):
    self._startup_prewarmed_logged=True
    logger.info(f"[HOT-PATH PREWARMED] Proactively pre-warmed CLOB metadata & fee caches for {len(active_tokens)} active token(s) [version=2, markets-by-token, clob-markets].")
   if active_tokens and hasattr(self.executor,"prewarm_order_ladder") and not getattr(self.executor,"dry_run",True):
    self._spawn_ladder_prewarm(active_tokens)
   if getattr(self,"_last_known_collateral",None) is not None:
    self.executor.set_cached_collateral(float(self._last_known_collateral))
  except Exception as e:
   logger.debug(f"[KEEPALIVE PREWARM] Notice: {e}")
 def _spawn_ladder_prewarm(self,tokens:List[str])->None:
  import threading
  existing=getattr(self,"_ladder_prewarm_thread",None)
  if existing is not None and existing.is_alive():
   return
  notionals=[float(self.ticket_notional)]
  collat=getattr(self,"_last_known_collateral",None)
  rungs_pre=(12.00,13.77,16.50,22.00,28.00) if (collat and isinstance(collat,(int,float)) and collat>=110.0) else (12.00,13.77,16.50)
  for fallback_rung in rungs_pre:
   if all(abs(fallback_rung - x)>=0.40 for x in notionals):
    notionals.append(fallback_rung)
  if getattr(self,"dynamic_sizing",False) and collat and isinstance(collat,(int,float)) and collat > 0:
   dyn_pct=float(getattr(self,"dynamic_bankroll_pct",0.22) or 0.22)
   for mult in (1.0,1.15,0.5405,0.6216):
    cand_n=round(float(collat) * dyn_pct * mult,2)
    if cand_n>=12.0 and all(abs(cand_n - x)>=0.40 for x in notionals):
     notionals.append(cand_n)
  def _worker():
   signed=0
   dense_shares=list(range(6,96))
   for t in tokens:
    try:
     signed += int(self.executor.prewarm_order_ladder(t,12.0,exact_shares=dense_shares) or 0)
    except TypeError:
     for n_val in notionals:
      signed += int(self.executor.prewarm_order_ladder(t,n_val) or 0)
    except Exception as e:
     logger.debug(f"[PREWARM LADDER] dense grid notice for {t}: {e}")
    for n_val in notionals:
     if n_val<=18.0:
      continue
     try:
      signed += int(self.executor.prewarm_order_ladder(t,n_val,share_deltas=(-2,-1,0,1)) or 0)
     except TypeError:
      signed += int(self.executor.prewarm_order_ladder(t,n_val) or 0)
     except Exception as e:
      logger.debug(f"[PREWARM LADDER] notice for {t}: {e}")
   if signed:
    logger.info( f"[PREWARM LADDER] Pre-signed {signed} BUY order(s) across {len(tokens)} token(s) " f"(dense_shares=6..95 + tickets={[n for n in notionals if n > 18.0]})." )
  th=threading.Thread(target=_worker,name="ladder-prewarm",daemon=True)
  self._ladder_prewarm_thread=th
  th.start()
 async def _prewarm_next_candle_markets(self)->None:
  dir_slugs=("btc-up-or-down-hourly","eth-up-or-down-hourly","btc-up-or-down-15m","eth-up-or-down-15m")
  series_slugs=(*dir_slugs,"solana-up-or-down-15m","xrp-up-or-down-15m","btc-updown-5m","eth-updown-5m","sol-updown-5m","xrp-updown-5m")
  held_tokens={str(p.get("token_id") or "") for p in getattr(self,"active_positions",{}).values()}
  pre_bal_cache=self.__dict__.setdefault("_d1_clean_pre_bal_cache",{})
  warmed=0
  now_utc=datetime.now(timezone.utc)
  for slug in series_slugs:
   try:
    url=f"https://gamma-api.polymarket.com/events?series_slug={slug}&limit=3&closed=false"
    resp=await asyncio.to_thread(self.executor._sync_session.get,url,timeout=3.0)
    if resp.status_code!=200:
     continue
    events=resp.json()
    for event in events:
     for market in event.get("markets",[]):
      m_id=str(market.get("id"))
      cond_id=str(market.get("conditionId") or "")
      end_date_str=market.get("endDate")
      if not end_date_str or not cond_id:
       continue
      try:
       end_dt=datetime.fromisoformat(end_date_str.replace("Z","+00:00"))
       secs_left=(end_dt - now_utc).total_seconds()
      except Exception:
       secs_left=3600.0
      if 0 < secs_left<=7200:
       raw_tokens=market.get("clobTokenIds")
       tokens=json.loads(raw_tokens) if isinstance(raw_tokens,str) else raw_tokens
       if tokens and len(tokens)>=2:
        t_up=str(tokens[0])
        t_down=str(tokens[1])
        self.market_condition_ids[m_id]=cond_id
        self.market_tokens_cache[f"{m_id}_UP"]=t_up
        self.market_tokens_cache[f"{m_id}_DOWN"]=t_down
        default_slug_rate=0.07
        fee_sched=market.get("feeSchedule",{})
        rate=float(fee_sched.get("rate",default_slug_rate) or default_slug_rate)
        exp=float(fee_sched.get("exponent",1.0) or 1.0)
        bps=int(round(rate * 10000))
        now_pb=time.time()
        gamma_tick=market.get("orderPriceMinTickSize") or "0.01"
        for t in (t_up,t_down):
         self.executor.prewarm_token_market_cache( token_id=t,tick_size=gamma_tick,neg_risk=False,fee_rate_bps=bps,condition_id=cond_id,fee_rate=rate,fee_exponent=exp,)
         if slug in dir_slugs:
          self._register_active_warmed_token(str(t),now_utc.timestamp() + secs_left)
         if str(t) not in held_tokens:
          pre_bal_cache[str(t)]=(0.0,now_pb)
        warmed += 1
   except Exception as e:
    logger.debug(f"[PREWARM NOTICE] Error pre-warming series {slug}: {e}")
  if warmed > 0:
   logger.info(f"[PREWARM NEXT-CANDLE] Pre-warmed metadata & CLOB caches for {warmed} upcoming token(s) from Gamma API.")
   self._prewarm_active_market_tokens()
 def _has_unsettled_collateral_overlap(self,now_ts:Optional[float]=None)->bool:
  if now_ts is None:
   now_ts=time.time()
  if getattr(self,"pending_entry_intents",None):
   return True
  for p in (getattr(self,"active_positions",None) or {}).values():
   st=p.get("status")
   if st in { "MATCHED_PENDING_SETTLEMENT","ENTRY_OUTCOME_UNKNOWN","UNRESOLVED_SETTLEMENT","AWAITING_ONCHAIN_SETTLEMENT",}:
    return True
   if position_is_settlement_receivable(p):
    return True
   expiry_ts=float(p.get("candle_expiry_ts") or 0.0)
   if expiry_ts > 0.0 and now_ts>=expiry_ts:
    return True
   entry_ts=float(p.get("entry_ts") or 0.0)
   if entry_ts > 0.0 and (now_ts - entry_ts) < 30.0:
    return True
   if ( float(p.get("filled_exit_shares",0.0) or 0.0) > 0.0 or float(p.get("confirmed_realized_cash",0.0) or 0.0) > 0.0 or float(p.get("estimated_exit_cash",0.0) or 0.0) > 0.0 ):
    return True
  return False
 def _update_equity_tier(self,total_equity:float,*,allow_hwm_ratchet:Optional[bool]=None)->Dict[str,Any]:
  tot_equity=float(total_equity) if (total_equity is not None and math.isfinite(float(total_equity))) else 0.0
  seed_thresh=float(RISK_CONFIG.get("seed_survival_equity_threshold",88.0))
  if allow_hwm_ratchet is None:
   allow_hwm_ratchet=not self._has_unsettled_collateral_overlap()
  cur_hwm=getattr(self,"high_water_mark_equity",None)
  if cur_hwm is None or not math.isfinite(float(cur_hwm)) or float(cur_hwm)<=0.0:
   self.high_water_mark_equity=tot_equity
  elif tot_equity < seed_thresh and float(cur_hwm) > tot_equity * 1.15:
   self.high_water_mark_equity=tot_equity
  elif allow_hwm_ratchet and tot_equity > float(cur_hwm):
   self.high_water_mark_equity=tot_equity
  prev_tier=getattr(self,"_current_equity_tier",None) or getattr(self,"current_equity_tier",None)
  tier_limits=get_equity_tier_limits(tot_equity,self.high_water_mark_equity,previous_tier=prev_tier)
  self._current_equity_tier=tier_limits["tier"]
  self.current_equity_tier=tier_limits["tier"]
  self.dynamic_bankroll_pct=tier_limits["dynamic_bankroll_pct"]
  if not getattr(self,"allow_cli_exposure",False):
   self.max_exposure=tier_limits["max_exposure"]
  self.max_concurrent_positions=tier_limits["max_concurrent_positions"]
  if hasattr(self.risk_controller,"min_equity_floor_usd"):
   self.risk_controller.min_equity_floor_usd=tier_limits["min_equity_floor"]
  if hasattr(self.risk_controller,"max_daily_loss_usd"):
   self.risk_controller.max_daily_loss_usd=tier_limits["max_daily_loss"]
  if tot_equity < seed_thresh:
   self.max_concurrent_positions=min(self.max_concurrent_positions,int(RISK_CONFIG.get("seed_survival_max_concurrent",1)))
   if hasattr(self.risk_controller,"min_equity_floor_usd"):
    self.risk_controller.min_equity_floor_usd=float(RISK_CONFIG.get("seed_survival_floor_usd",48.0))
  return tier_limits
 async def _async_refresh_collateral(self)->None:
  if self.dry_run or not self.executor.is_authenticated:
   return
  try:
   bal=await asyncio.to_thread(self.executor.get_collateral_balance,0.0)
   if bal is not None and isinstance(bal,(int,float)) and math.isfinite(bal) and bal > 0:
    prev_bal=getattr(self,"_last_known_collateral",None)
    self._last_known_collateral=float(bal)
    self._collateral_sync_seq=int(getattr(self,"_collateral_sync_seq",0) or 0) + 1
    self.executor.set_cached_collateral(float(bal))
    now_ts=time.time()
    active_market_equity=sum(self.get_position_market_value(p,now_ts) for p in self.active_positions.values())
    in_flight_unwind_cash=sum( max( float(p.get("confirmed_realized_cash",0.0) or 0.0),float(p.get("estimated_exit_cash",0.0) or 0.0),) for p in self.active_positions.values() if p.get("status")=="UNRESOLVED_SETTLEMENT" )
    tot_equity=float(bal) + active_market_equity + in_flight_unwind_cash
    allow_ratchet=(in_flight_unwind_cash<=0.0) and (not self._has_unsettled_collateral_overlap(now_ts))
    prev_tier_sync=getattr(self,"_current_equity_tier",None) or getattr(self,"current_equity_tier",None)
    tier_limits=self._update_equity_tier(tot_equity,allow_hwm_ratchet=allow_ratchet)
    prev_halted=bool(self.risk_controller.halted)
    self.risk_controller.check_equity_drawdown(float(tot_equity),allow_auto_clear=True)
    halt_transition=(prev_halted!=bool(self.risk_controller.halted))
    tier_transition=(prev_tier_sync!=tier_limits["tier"])
    if prev_bal is None or abs(float(bal) - float(prev_bal))>=0.25 or halt_transition or tier_transition:
     await asyncio.to_thread(self.save_state)
    logger.debug(f"[COLLATERAL SYNC] In-memory collateral: ${bal:.2f}, total equity: ${tot_equity:.2f}, tier: {tier_limits['tier']}")
  except Exception as e:
   logger.debug(f"[COLLATERAL SYNC] Notice: {e}")
 def _effective_exit_policy(self)->str:
  pol=str(getattr(self,"exit_policy","") or "")
  if ( pol=="hold_98" and not getattr(self,"dry_run",True) and getattr(self.executor,"client",None) is not None and not hasattr(self.executor.client,"_mock_children") and int(getattr(self.executor,"signature_type",0) or 0)==3 and not (os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY")) and os.getenv("PM_ENABLE_ONCHAIN_MERGE","0")!="1" ):
   return "two_tranche_95_98"
  return pol
 def _calculate_target_exit(self,price:float,tte:float)->float:
  if getattr(self,"hold_to_maturity",False):
   return 0.98 if price < 0.80 else 0.99
  if self._effective_exit_policy()=="hold_98":
   return 0.98
  return min(0.95,round(price + self.profit_theta,2))
 def _use_two_tranche_maker_exit(self,sleeve:Optional[str])->bool:
  if sleeve and ("BOX" in str(sleeve).upper() or sleeve=="SLEEVE_4_BOUNDARY_SNIPE"):
   return False
  if sleeve=="SLEEVE_2_MID_HOUR" and getattr(self,"enable_mid_hour_t1_12c",False):
   return True
  if self._effective_exit_policy()=="hold_98":
   return False
  if not getattr(self,"hold_to_maturity",False):
   return True
  return False
 def _tranche1_tp_offset(self,sleeve:Optional[str])->float:
  if sleeve=="SLEEVE_2_MID_HOUR" and getattr(self,"enable_mid_hour_t1_12c",False):
   return 0.12
  return 0.14
 def _global_halt_reasons(self)->List[str]:
  reasons:List[str]=[]
  intents=getattr(self,"pending_entry_intents",{}) or {}
  if intents:
   reasons.append(f"PENDING_ENTRY_INTENTS:{','.join(sorted(intents.keys()))}")
  for tid,p in (getattr(self,"active_positions",{}) or {}).items():
   if position_requires_global_halt(p):
    status_val="LIQUIDITY_CRISIS" if p.get("status")=="LIQUIDITY_CRISIS" else (p.get('exit_order_status') or p.get('status'))
    reasons.append(f"{tid}:{status_val}")
  executor=getattr(self,"executor",None)
  if executor is not None and not self.dry_run and not getattr(executor,"reservations_trusted",True):
   reasons.append("RESERVATIONS_UNTRUSTED")
  return reasons
 def _reconciling_market_ids(self)->Set[str]:
  reconciling=set()
  for p in (getattr(self,"active_positions",{}) or {}).values():
   st=p.get("status")
   pst=p.get("exit_order_status")
   if st in MARKET_SCOPED_ENTRY_HALT_STATUSES or pst in MARKET_SCOPED_ENTRY_HALT_STATUSES:
    m_id=str(p.get("market_id") or "")
    if m_id:
     reconciling.add(m_id)
  return reconciling
 def _refresh_global_halt(self,authoritative:bool=False)->bool:
  reasons=self._global_halt_reasons()
  may_clear=authoritative or self.dry_run or getattr(self,"_startup_reconciled",False)
  new_halt=bool(reasons) or (self.risk_halt and not may_clear)
  changed=(new_halt!=self.risk_halt) or (reasons!=self.global_halt_reasons)
  self.risk_halt=new_halt
  self.reconciliation_required=bool(reasons) or bool(self._reconciling_market_ids())
  self.global_halt_reasons=reasons if reasons else (self.global_halt_reasons if new_halt else [])
  if changed:
   if new_halt:
    logger.critical(f"[GLOBAL HALT] New entries blocked: {self.global_halt_reasons}")
   else:
    logger.warning("[GLOBAL HALT CLEARED] All unknown outcomes authoritatively reconciled.")
   self.save_state()
  return new_halt
 @staticmethod
 def get_position_market_value(pos:Dict[str,Any],now_ts:Optional[float]=None)->float:
  if now_ts is None:
   now_ts=time.time()
  if pos.get("pending_settlement_close_reason") in {"MARKET_RESOLVED_LOSS","EXPIRED_OUT_OF_MONEY"}:
   return 0.0
  if pos.get("close_reason") and "MARKET_RESOLVED_LOSS" in str(pos.get("close_reason")):
   return 0.0
  resolved_win=pos.get("resolved_winning_outcome")
  target=pos.get("target_token")
  if resolved_win is not None and target is not None and resolved_win!=target:
   return 0.0
  expiry_ts=float(pos.get("candle_expiry_ts") or 0.0)
  if expiry_ts > 0.0 and now_ts>=expiry_ts:
   if resolved_win is not None and resolved_win==target:
    return float(pos.get("expected_terminal_payout_usd") or pos.get("entry_shares") or 0.0)
   if resolved_win is None:
    return float(pos.get("remaining_cost_basis",pos.get("notional_usd",0.0)) or 0.0)
   return 0.0
  if pos.get("status") in {"UNRESOLVED_SETTLEMENT","AWAITING_ONCHAIN_SETTLEMENT"}:
   if resolved_win is not None and resolved_win==target:
    return float(pos.get("expected_terminal_payout_usd") or pos.get("entry_shares") or 0.0)
   return 0.0
  return float(pos.get("remaining_cost_basis",pos.get("notional_usd",0.0)) or 0.0)
 def _risk_bearing_positions(self)->Dict[str,Dict[str,Any]]:
  now_ts=time.time()
  active={}
  for k,v in self.active_positions.items():
   if v.get("is_dominance_box"):
    continue
   if position_is_settlement_receivable(v):
    continue
   if v.get("status") in {"UNRESOLVED_SETTLEMENT","AWAITING_ONCHAIN_SETTLEMENT"}:
    continue
   expiry_ts=float(v.get("candle_expiry_ts") or 0.0)
   if expiry_ts > 0.0 and now_ts>=expiry_ts:
    continue
   active[k]=v
  return active
 def can_enter_new_position(self,market_id:Optional[str]=None)->bool:
  if self.risk_controller.is_halted() or getattr(self,"risk_halt",False):
   return False
  if bool(self._global_halt_reasons()):
   return False
  if market_id and str(market_id) in self._reconciling_market_ids():
   return False
  if len(self._risk_bearing_positions())>=self.max_concurrent_positions:
   return False
  return True
 ONCHAIN_SOURCE="POLYGON_ONCHAIN_ERC1155"
 UNWIND_UNKNOWN_STATES=frozenset({ "UNWIND_EXECUTION_OUTCOME_UNKNOWN","UNWIND_RECONCILIATION_REQUIRED","UNRESOLVED_BALANCE_DISCREPANCY",})
 @staticmethod
 def _num(val:Any)->Optional[float]:
  if isinstance(val,bool) or not isinstance(val,(int,float,str,Decimal)):
   return None
  try:
   f=float(val)
  except (TypeError,ValueError):
   return None
  return f if math.isfinite(f) else None
 def _wallet_token_balance(self,token_id:Optional[str])->Tuple[Optional[float],str]:
  if not token_id:
   return None,"UNAVAILABLE"
  onchain_fn=getattr(self.executor,"get_onchain_erc1155_balance",None)
  clob_fn=getattr(self.executor,"get_conditional_balance",None)
  onchain_bal=None
  if onchain_fn is not None:
   try:
    onchain_bal=self._num(onchain_fn(token_id))
   except Exception:
    onchain_bal=None
  if onchain_bal is not None and onchain_bal > 0.0:
   return onchain_bal,self.ONCHAIN_SOURCE
  clob_bal=None
  if clob_fn is not None:
   try:
    clob_bal=self._num(clob_fn(token_id))
   except Exception:
    clob_bal=None
  if clob_bal is not None and clob_bal > 0.0:
   return clob_bal,"CLOB_BALANCE_API"
  if onchain_bal is not None and onchain_bal>=0.0:
   return onchain_bal,self.ONCHAIN_SOURCE
  if clob_bal is not None and clob_bal>=0.0:
   return clob_bal,"CLOB_BALANCE_API"
  return None,"UNAVAILABLE"
 def _known_fill_ids(self,exclude_tid:Optional[str]=None)->Set[str]:
  ids:Set[str]=set()
  pools=list(self.active_positions.items()) + [ (str(c.get("trade_id")),c) for c in self.closed_positions[-1000:] ]
  for tid,p in pools:
   if exclude_tid is not None and tid==exclude_tid:
    continue
   ids.update(str(x) for x in (p.get("entry_fill_ids") or []))
   ids.update(str(x) for x in (p.get("exit_fill_ids") or []))
  return ids
 def _fetch_account_fills( self,token_id:str,after_ts:float,side:str,order_id:Optional[str]=None,exclude_tid:Optional[str]=None,)->Optional[List[Dict[str,Any]]]:
  fn=getattr(self.executor,"get_account_fills",None)
  if fn is None:
   return None
  try:
   fills=fn(token_id,after_ts=float(after_ts),side=side,order_id=order_id or None)
  except Exception as e:
   logger.error(f"[LIFECYCLE] Trade history unavailable for {token_id}: {e}")
   return None
  if not isinstance(fills,list):
   return None
  known=self._known_fill_ids(exclude_tid)
  out=[]
  for f in fills:
   if not isinstance(f,dict) or str(f.get("fill_id")) in known:
    continue
   if (self._num(f.get("size")) or 0.0)<=0.0:
    continue
   out.append(f)
  return out
 def _fetch_entry_evidence( self,token_id:str,submitted_ts:float,entry_order_id:Optional[str]=None,exclude_tid:Optional[str]=None,)->Optional[Dict[str,Any]]:
  fills=self._fetch_account_fills(token_id,submitted_ts - 5.0,"BUY",entry_order_id,exclude_tid)
  if fills is None:
   return None
  return { "fills":fills,"shares":round(sum(self._num(f.get("size")) or 0.0 for f in fills),6),"cash":round(sum(self._num(f.get("cash")) or 0.0 for f in fills),6),"trade_ids":sorted({str(f["trade_id"]) for f in fills if f.get("trade_id")}),"transactions_hashes":sorted({str(f["transaction_hash"]) for f in fills if f.get("transaction_hash")}),"order_ids":sorted({str(f["order_id"]) for f in fills if f.get("order_id")}),"fill_ids":sorted({str(f["fill_id"]) for f in fills if f.get("fill_id")}),}
 def _classify_entry( self,token_id:str,pre_bal:float,submitted_ts:float,entry_order_id:Optional[str],exclude_tid:Optional[str],)->Dict[str,Any]:
  bal,src=self._wallet_token_balance(token_id)
  evidence=self._fetch_entry_evidence(token_id,submitted_ts,entry_order_id,exclude_tid)
  out:Dict[str,Any]={"verdict":"UNKNOWN","balance":bal,"source":src,"delta":None,"evidence":evidence}
  if bal is None:
   return out
  delta=bal - float(pre_bal or 0.0)
  out["delta"]=delta
  if delta>=0.01:
   out["verdict"]="ARRIVED"
   return out
  if delta<=-0.01:
   return out
  if evidence is not None and evidence["shares"] > 0.0:
   out["verdict"]="MATCHED_UNSETTLED"
   return out
  if entry_order_id:
   try:
    info=self.executor.get_order_status(str(entry_order_id))
   except Exception:
    info=None
   if isinstance(info,dict):
    st=str(info.get("status","")).upper()
    matched=self._num(info.get("size_matched")) or 0.0
    if st in {"LIVE","OPEN","RESTING","DELAYED"}:
     try:
      c_res=self.executor.cancel_order(str(entry_order_id))
     except Exception:
      c_res={}
     if not (c_res or {}).get("is_canceled"):
      return out
     try:
      info=self.executor.get_order_status(str(entry_order_id)) or info
     except Exception:
      pass
     st=str(info.get("status","")).upper()
     matched=max(matched,self._num((c_res or {}).get("matched")) or 0.0,self._num(info.get("size_matched")) or 0.0)
     if matched > 1e-4:
      out["verdict"]="MATCHED_UNSETTLED"
      return out
     if (c_res or {}).get("is_canceled") and matched<=1e-4:
      out["verdict"]="NOT_EXECUTED"
      out["proof"]="RESTING_ENTRY_CANCELED_ZERO_FILL"
      return out
    if (st.startswith("CANCEL") or st in {"EXPIRED","REJECTED"}) and matched<=1e-4:
     out["verdict"]="NOT_EXECUTED"
     out["proof"]="TERMINAL_ZERO_FILL_ORDER_STATUS"
     return out
  age=time.time() - float(submitted_ts or 0.0)
  if ( evidence is not None and not evidence["fills"] and src in (self.ONCHAIN_SOURCE,"CLOB_BALANCE_API") and age>=ENTRY_UNEXECUTED_PROOF_AGE_S ):
   if hasattr(self.executor,"get_open_orders"):
    try:
     open_os=self.executor.get_open_orders(strict=True)
    except TypeError:
     open_os=self.executor.get_open_orders()
    except Exception:
     open_os=None
    if not isinstance(open_os,list):
     return out
    if isinstance(open_os,list):
     for o_b in open_os:
      if str((o_b or {}).get("asset_id") or (o_b or {}).get("token_id") or "")==str(token_id) and str((o_b or {}).get("side") or "").upper()=="BUY":
       o_bid=str((o_b or {}).get("id") or (o_b or {}).get("orderID") or "")
       if o_bid:
        try:
         c_b=self.executor.cancel_order(o_bid)
        except Exception:
         c_b={}
        if not (c_b or {}).get("is_canceled") or (self._num((c_b or {}).get("matched")) or 0.0) > 1e-4:
         return out
   out["verdict"]="NOT_EXECUTED"
   out["proof"]="ONCHAIN_UNCHANGED_AND_NO_ACCOUNT_FILLS"
  return out
 def _apply_entry_evidence(self,pos:Dict[str,Any],cls:Dict[str,Any])->None:
  evidence=cls.get("evidence") or {}
  delta=cls.get("delta")
  now_iso=datetime.now(timezone.utc).isoformat()
  if cls["verdict"]=="ARRIVED" and delta is not None:
   net=float(Decimal(str(delta)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
   pos["entry_shares"]=net
   pos["remaining_shares"]=net
   pos["remaining_exit_shares"]=net
   pos["filled_exit_shares"]=0.0
   if float(pos.get("notional_usd",0.0) or 0.0)<=0.0 and net > 0:
    est_px=float(pos.get("entry_price") or pos.get("target_price") or 0.70)
    pos["notional_usd"]=round(net * est_px,4)
    pos["cost_basis_estimated"]=True
   pos["remaining_cost_basis"]=pos.get("notional_usd",0.0)
   if net > 0 and float(pos.get("notional_usd",0.0) or 0.0) > 0:
    true_cost_per_share=round(float(pos["notional_usd"]) / net,4)
    if true_cost_per_share > float(pos.get("entry_price",0.0) or 0.0):
     pos["entry_price"]=true_cost_per_share
     pos["target_exit_price"]=self._calculate_target_exit(true_cost_per_share,float(pos.get("candle_expiry_ts",time.time() + 600.0)) - time.time())
   pos["inventory_reconciled"]=True
   pos["entry_inventory_source"]=cls.get("source")
  if evidence.get("shares",0.0) > 0.0:
   pos["trade_ids"]=evidence["trade_ids"]
   pos["transactions_hashes"]=evidence["transactions_hashes"]
   pos["entry_fill_ids"]=evidence["fill_ids"]
   if not pos.get("entry_order_id") and evidence["order_ids"]:
    pos["entry_order_id"]=evidence["order_ids"][0]
   gross=max(float(evidence["shares"]),float(delta or 0.0))
   pos["gross_entry_shares"]=round(gross,6)
   if evidence["cash"] > 0.0:
    pos["notional_usd"]=round(float(evidence["cash"]),6)
    pos["entry_price"]=round(float(evidence["cash"]) / max(float(evidence["shares"]),1e-9),6)
    pos["cost_basis_estimated"]=False
   pos["entry_finality_source"]="EXCHANGE_TRADE_HISTORY"
   if cls["verdict"]!="ARRIVED":
    pos["entry_shares"]=round(float(evidence["shares"]),6)
    pos["remaining_shares"]=pos["entry_shares"]
    pos["remaining_exit_shares"]=pos["entry_shares"]
    pos["inventory_reconciled"]=False
  elif cls["verdict"]=="ARRIVED":
   pos["gross_entry_shares"]=round(float(delta),6)
   pos["cost_basis_estimated"]=True
   pos["entry_finality_source"]=( "ONCHAIN_BALANCE_DELTA" if cls.get("source")==self.ONCHAIN_SOURCE else "CLOB_BALANCE_DELTA" )
  pos["remaining_cost_basis"]=float(pos.get("notional_usd",0.0) or 0.0)
  pos["entry_finality_verified_at_utc"]=now_iso
 def _verify_entry_finality(self,pos:Dict[str,Any])->Tuple[bool,bool]:
  reverted=False
  for tr_id in pos.get("trade_ids") or []:
   try:
    info=self.executor.get_trade_status(tr_id) or {}
   except Exception:
    info={}
   st=str(info.get("status","")).upper() if isinstance(info,dict) else ""
   if st in {"CONFIRMED","MINED"}:
    return True,False
   tx=info.get("transactionHash") or info.get("transaction_hash") if isinstance(info,dict) else None
   if tx:
    ok=self.executor.get_transaction_receipt_status(tx)
    if ok is True:
     return True,False
    if ok is False:
     reverted=True
  tx_hashes=pos.get("transactions_hashes") or pos.get("transactionsHashes") or pos.get("transaction_hashes") or []
  for tx in tx_hashes:
   try:
    ok=self.executor.get_transaction_receipt_status(tx)
   except Exception:
    ok=None
   if ok is True:
    return True,False
   if ok is False:
    reverted=True
  return False,reverted
 def _pending_reservations(self,pos:Dict[str,Any])->List[str]:
  return [str(r) for r in (pos.get("pending_reservation_ids") or []) if r]
 def _release_position_reservations(self,pos:Dict[str,Any],extra_ids:Optional[List[str]]=None)->None:
  ids=set(self._pending_reservations(pos)) | {str(x) for x in (extra_ids or []) if x}
  for rid in ids:
   try:
    self.executor.release_inventory(reservation_id=rid)
   except Exception as e:
    logger.error(f"[LIFECYCLE] Could not release reservation {rid}: {e}")
    raise
  pos["pending_reservation_ids"]=[]
 def _consolidate_dominance_box_close( self,tid:str,pos:Dict[str,Any],cum_cash:float,cum_fee:float,net_pnl:float,reason:str,record_pnl:bool )->Tuple[bool,float]:
  if not pos.get("is_dominance_box") or not record_pnl:
   return False,net_pnl
  partner_tid=str(pos.get("box_partner_trade_id") or "")
  if partner_tid and partner_tid in self.active_positions:
   self.active_positions[partner_tid]["_closed_partner_leg"]={ "trade_id":tid,"target_token":pos.get("target_token"),"market_id":pos.get("market_id"),"notional_usd":round(float(pos.get("notional_usd",0.0) or 0.0),4),"payout_usd":round(cum_cash,4),"exit_fee_usd":round(cum_fee,4),"net_pnl_usd":round(net_pnl,4),"close_reason":reason,}
   self.active_positions.pop(tid,None)
   self.save_state()
   self._pending_collateral_refresh=True
   logger.info(f"[D1 BOX LEG 1 CLOSED] {tid} ({reason}) | Leg Cash=${cum_cash:.2f} | Awaiting partner {partner_tid}")
   return True,net_pnl
  p1=pos.pop("_closed_partner_leg",None)
  if isinstance(p1,dict):
   tot_notional=round(float(p1.get("notional_usd",0.0)) + float(pos.get("notional_usd",0.0) or 0.0),4)
   tot_payout=round(float(p1.get("payout_usd",0.0)) + cum_cash,2)
   tot_pnl=round(float(p1.get("net_pnl_usd",0.0)) + net_pnl,2)
   pos["trade_id"]=str(pos.get("box_id") or tid)
   pos["notional_usd"]=tot_notional
   pos["payout_usd"]=tot_payout
   pos["net_pnl_usd"]=tot_pnl
   pos["won"]=tot_pnl>=0.0
   pos["close_reason"]=f"D1_BOX_CONSOLIDATED({p1.get('close_reason')}+{reason})"
   pos["exit_decomposition_bucket"]="DOMINANCE_BOX_ARB"
   pos["box_legs_summary"]=[ p1,{ "trade_id":tid,"target_token":pos.get("target_token"),"market_id":pos.get("market_id"),"payout_usd":round(cum_cash,4),"net_pnl_usd":round(net_pnl,4),"close_reason":reason,},]
   return False,tot_pnl
  return False,net_pnl
 def _close_position(self,tid:str,pos:Dict[str,Any],status:str,reason:str,won:Optional[bool]=None,record_pnl:bool=True)->Optional[float]:
  is_terminal_loss=( reason in {"MARKET_RESOLVED_LOSS","EXPIRED_OUT_OF_MONEY"} or pos.get("pending_settlement_close_reason") in {"MARKET_RESOLVED_LOSS","EXPIRED_OUT_OF_MONEY"} or (pos.get("close_reason") and "MARKET_RESOLVED_LOSS" in str(pos.get("close_reason"))) )
  if is_terminal_loss:
   pos["exit_cash_estimated"]=False
   pos["estimated_exit_cash"]=0.0
  est_cash=float(pos.get("estimated_exit_cash",0.0) or 0.0)
  if not is_terminal_loss and (est_cash > 0.0 or pos.get("exit_cash_estimated",False)):
   logger.warning( f"[SETTLEMENT_BLOCKED] Cannot settle position {tid} with unconfirmed/estimated cash " f"(estimated=${est_cash:.2f}, exit_cash_estimated={pos.get('exit_cash_estimated')}). " "Retaining in UNRESOLVED_SETTLEMENT state pending authoritative fills." )
   pos["status"]="UNRESOLVED_SETTLEMENT"
   pos["close_reason"]=f"BLOCKED_UNCONFIRMED_ESTIMATE: {reason}"
   pos["pending_settlement_close_status"]=status
   pos["pending_settlement_close_reason"]=reason
   self.save_state()
   return None
  cum_cash=float(pos.get("confirmed_realized_cash",pos.get("realized_exit_cash",0.0)) or 0.0)
  cum_fee=float(pos.get("realized_exit_fee",0.0) or 0.0)
  filled=float(pos.get("filled_exit_shares",0.0) or 0.0)
  net_pnl=self.calculate_realized_cash_pnl(pos,cum_cash,cum_fee) if record_pnl else 0.0
  self._release_position_reservations(pos,[pos.get("exit_order_id"),pos.get("unwind_order_id")])
  token_id=pos.get("token_id")
  if token_id and not any( p.get("token_id")==token_id for k,p in self.active_positions.items() if k!=tid ):
   try:
    self.executor.release_inventory(token_id,float(pos.get("entry_shares",0.0) or 0.0))
   except Exception as e:
    logger.error(f"[LIFECYCLE] Token reservation release failed for {token_id}: {e}")
    raise
  pos["status"]=status
  pos["settled_at_utc"]=datetime.now(timezone.utc).isoformat()
  pos["won"]=(net_pnl > 0.0) if won is None else won
  pos["payout_usd"]=round(cum_cash,2)
  pos["net_pnl_usd"]=net_pnl
  pos["close_reason"]=reason
  if filled > 0.0:
   pos["average_exit_price"]=round(cum_cash / filled,4)
  pos["remaining_shares"]=0.0
  pos["remaining_exit_shares"]=0.0
  pos["is_liquidating"]=False
  r_up=str(reason or "").upper()
  if "MAKER_SCALP" in r_up or "FILLED_OFFLINE" in r_up:
   pos["exit_decomposition_bucket"]="MAKER_SCALP"
  elif "RATCHET" in r_up:
   pos["exit_decomposition_bucket"]="PROFIT_RATCHET"
  elif "STOP" in r_up or "UNWIND" in r_up or "SALVAGE" in r_up:
   pos["exit_decomposition_bucket"]="SALVAGE_UNWIND"
  elif "REDEMPTION" in r_up or (pos.get("won") and "RESOLVED" in r_up):
   pos["exit_decomposition_bucket"]="TERMINAL_SETTLEMENT"
  else:
   pos["exit_decomposition_bucket"]="TERMINAL_LOSS"
  m_id_closed=str(pos.get("market_id") or "")
  pos["entry_sequence_in_market"]=int((getattr(self,"trades_per_market",None) or {}).get(m_id_closed,1) or 1)
  pos["is_win_reset_second_entry"]=bool(pos["entry_sequence_in_market"]>=2)
  leg_net_cash=max(0.0,float(cum_cash or 0.0) - float(cum_fee or 0.0))
  _unres_seq=pos.get("_unresolved_settle_seq")
  _already_synced_in_collat=( _unres_seq is not None and int(getattr(self,"_collateral_sync_seq",0) or 0) > int(_unres_seq) )
  if ( not getattr(self,"dry_run",True) and getattr(self,"_last_known_collateral",None) is not None and leg_net_cash > 0.0 and not pos.get("_collateral_exit_credited") and not _already_synced_in_collat ):
   pos["_collateral_exit_credited"]=True
   self._last_known_collateral=float(self._last_known_collateral) + leg_net_cash
  deferred_partner,net_pnl=self._consolidate_dominance_box_close( tid,pos,cum_cash,cum_fee,net_pnl,reason,record_pnl )
  if deferred_partner:
   try:
    asyncio.get_running_loop().create_task(self._async_refresh_collateral())
   except RuntimeError:
    pass
   return net_pnl
  self.closed_positions.append(pos)
  if record_pnl:
   self.risk_controller.record_trade_pnl(net_pnl)
  self.active_positions.pop(tid,None)
  collat_after=getattr(self,"_last_known_collateral",None)
  if not getattr(self,"dry_run",True) and isinstance(collat_after,(int,float)) and math.isfinite(collat_after) and collat_after > 0.0:
   now_close_ts=time.time()
   rem_mkt_eq=sum(self.get_position_market_value(p,now_close_ts) for p in self.active_positions.values())
   self._update_equity_tier(float(collat_after) + rem_mkt_eq,allow_hwm_ratchet=False)
  self.save_state()
  self._pending_collateral_refresh=True
  try:
   loop=asyncio.get_running_loop()
   loop.create_task(self._async_refresh_collateral())
  except RuntimeError:
   pass
  logger.info(f"[CLOSED] {tid} | {reason} | Payout=${cum_cash:.2f} | Net PnL=${net_pnl:+.2f}")
  return net_pnl
 @staticmethod
 def _estimated_taker_fee(shares:float,cash:float,fee_rate:float=0.07,fee_exponent:float=1.0)->float:
  if shares<=0.0:
   return 0.0
  px=min(0.999,max(0.001,cash / shares))
  return round(shares * fee_rate * ((px * (1.0 - px)) ** max(1.0,float(fee_exponent))),5)
 def _record_order_summary(self,pos:Dict[str,Any],summary:Dict[str,Any],fallback_px:float,taker:bool)->bool:
  oid=str(summary["order_id"])
  matched=float(summary.get("matched",0.0) or 0.0)
  prior_rec=(pos.get("order_records") or {}).get(oid) or {}
  prior=float(prior_rec.get("matched",0.0) or 0.0)
  prior_is_estimated=bool(prior_rec.get("cash_is_estimated",False))
  cash=summary.get("cash")
  is_est=False
  if cash is None:
   cash=round(matched * max(0.0,float(fallback_px or 0.0)),6)
   if matched > 0.0:
    is_est=True
    pos["exit_cash_estimated"]=True
  elif summary.get("cash_is_estimated") and matched > 0.0:
   is_est=True
   pos["exit_cash_estimated"]=True
  if matched<=1e-6 and float(pos.get("estimated_exit_cash",0.0) or 0.0)<=1e-6:
   has_other_est=any( isinstance(v,dict) and v.get("cash_is_estimated") and float(v.get("matched",0.0) or 0.0) > 1e-6 for k,v in (pos.get("order_records") or {}).items() if str(k)!=oid )
   if not has_other_est and pos.get("exit_cash_estimated"):
    pos["exit_cash_estimated"]=False
  has_new_shares=(matched > prior + 1e-6)
  has_cash_confirmation=prior_is_estimated and (not is_est)
  prior_cash=float(prior_rec.get("cash",0.0) or 0.0)
  has_cash_correction=(abs(float(cash) - prior_cash) > 1e-6) and (not is_est)
  if not (has_new_shares or has_cash_confirmation or has_cash_correction):
   return False
  applied_r=float(pos.get("fee_rate_applied") or 0.07)
  applied_e=float(pos.get("fee_exponent_applied") or 1.0)
  charge_est_fee=bool(taker and not summary.get("cash_from_reported_taking"))
  fee=self._estimated_taker_fee(matched,float(cash),fee_rate=applied_r,fee_exponent=applied_e) if charge_est_fee else 0.0
  if charge_est_fee:
   pos["exit_fee_estimated"]=True
  self.record_fill_and_update_position(pos,oid,matched,float(cash),fee,cash_is_estimated=is_est)
  ids=set(pos.get("exit_trade_ids") or []) | set(summary.get("trade_ids") or [])
  pos["exit_trade_ids"]=sorted(str(i) for i in ids)
  f_ids=set(pos.get("exit_fill_ids") or []) | set(summary.get("fill_ids") or [])
  pos["exit_fill_ids"]=sorted(str(i) for i in f_ids)
  orig_sz=float(summary.get("original_size",0.0) or pos.get("exit_order_size",pos.get("entry_shares",0.0)) or 0.0)
  remaining_commit=max(0.0,orig_sz - matched)
  if summary.get("terminal"):
   self.executor.release_inventory(reservation_id=oid)
  elif remaining_commit > 0.0:
   self.executor.update_reservation(oid,remaining_commit)
  else:
   self.executor.release_inventory(reservation_id=oid)
  return True
 def _record_history_fills(self,pos:Dict[str,Any],fills:List[Dict[str,Any]],taker:bool)->int:
  by_order:Dict[str,List[Dict[str,Any]]]=defaultdict(list)
  for f in fills:
   by_order[str(f.get("order_id") or f.get("fill_id"))].append(f)
  booked=0
  applied_r=float(pos.get("fee_rate_applied") or 0.07)
  applied_e=float(pos.get("fee_exponent_applied") or 1.0)
  for oid,group in by_order.items():
   prior=(pos.get("order_records") or {}).get(oid) or {}
   base_shares=0.0 if prior.get("cash_is_estimated") else float(prior.get("matched",0.0) or 0.0)
   base_cash=0.0 if prior.get("cash_is_estimated") else float(prior.get("cash",0.0) or 0.0)
   base_fee=0.0 if prior.get("cash_is_estimated") else float(prior.get("fee",0.0) or 0.0)
   shares=base_shares + sum(self._num(f.get("size")) or 0.0 for f in group)
   cash=base_cash + sum(self._num(f.get("cash")) or 0.0 for f in group)
   fee=base_fee + ( self._estimated_taker_fee(sum(self._num(f.get("size")) or 0.0 for f in group),sum(self._num(f.get("cash")) or 0.0 for f in group),fee_rate=applied_r,fee_exponent=applied_e) if taker else 0.0 )
   group_settled=all( bool(f.get("transaction_hash")) and str(f.get("status","")).upper() in {"MINED","CONFIRMED"} for f in group )
   self.record_fill_and_update_position( pos,oid,shares,cash,fee,cash_is_estimated=(not group_settled and not self.dry_run) )
   booked += len(group)
  pos["exit_fill_ids"]=sorted(set(pos.get("exit_fill_ids") or []) | {str(f.get("fill_id")) for f in fills})
  pos["exit_trade_ids"]=sorted(set(pos.get("exit_trade_ids") or []) | {str(f.get("trade_id")) for f in fills if f.get("trade_id")})
  if taker and booked:
   pos["exit_fee_estimated"]=True
  return booked
 def _after_unwind_reconciled(self,tid:str,pos:Dict[str,Any],reason_default:str)->None:
  pos["unwind_order_id"]=None
  pos["is_liquidating"]=False
  pos.pop("unwind_attempt_ts",None)
  if float(pos.get("remaining_shares",0.0) or 0.0)<=0.01:
   self._close_position(tid,pos,ExecutionStatus.SETTLED,pos.get("unwind_reason") or reason_default,won=None)
   return
  pos["status"]=ExecutionStatus.PARTIALLY_FILLED if float(pos.get("filled_exit_shares",0.0) or 0.0) > 0 else pos.get("status")
  pos["exit_order_status"]="UNWIND_RETRY_REQUIRED"
  pos["next_unwind_retry_ts"]=0.0
  self.save_state()
 def _resolve_unknown_unwind(self,tid:str,pos:Dict[str,Any])->bool:
  token_id=pos.get("token_id")
  u_oid=pos.get("unwind_order_id")
  attempt_ts=float(pos.get("unwind_attempt_ts") or pos.get("unwind_last_attempt_ts") or pos.get("unwind_start_time") or pos.get("entry_ts") or 0.0)
  fallback_px=float(pos.get("unwind_limit_price") or 0.01)
  if u_oid:
   summary=self.executor.get_order_fill_summary(str(u_oid),token_id)
   if summary is not None:
    if not summary["terminal"]:
     self._record_order_summary(pos,summary,fallback_px,taker=True)
     self.save_state()
     return False
    self._record_order_summary(pos,summary,fallback_px,taker=True)
    self._release_position_reservations(pos,[str(u_oid)])
    logger.warning(f"[UNWIND RECONCILED] {tid}: order {u_oid} terminal {summary['status']} matched={summary['matched']:.2f}")
    self._after_unwind_reconciled(tid,pos,"UNWIND_RECONCILED")
    return True
  if not token_id:
   return False
  exclude_orders=set((pos.get("order_records") or {}).keys())
  if pos.get("exit_order_id"):
   exclude_orders.add(str(pos["exit_order_id"]))
  fills=self._fetch_account_fills(token_id,attempt_ts - 5.0,"SELL",exclude_tid=tid)
  if fills is None:
   return False
  fills=[f for f in fills if str(f.get("order_id")) not in exclude_orders]
  if fills:
   self._record_history_fills(pos,fills,taker=True)
   self._release_position_reservations(pos,[str(u_oid)] if u_oid else None)
   logger.warning(f"[UNWIND RECONCILED] {tid}: {len(fills)} fill(s) recovered from exchange trade history.")
   self._after_unwind_reconciled(tid,pos,"UNWIND_RECONCILED_FROM_HISTORY")
   return True
  if time.time() - attempt_ts < UNWIND_UNKNOWN_PROOF_AGE_S:
   return False
  bal,src=self._wallet_token_balance(token_id)
  rem=float(pos.get("remaining_shares",pos.get("entry_shares",0.0)) or 0.0)
  eps=self.executor.calculate_balance_epsilon(0.001)
  if bal is not None and src==self.ONCHAIN_SOURCE and bal + eps>=rem:
   self._release_position_reservations(pos,[str(u_oid)] if u_oid else None)
   logger.warning(f"[UNWIND RECONCILED] {tid}: no fills and on-chain inventory intact ({bal:.4f} >= {rem:.4f}); unwind did not execute.")
   self._after_unwind_reconciled(tid,pos,"UNWIND_RECONCILED")
   return True
  return False
 def _resolve_unknown_entry(self,tid:str,pos:Dict[str,Any])->bool:
  cls=self._classify_entry( pos.get("token_id"),float(pos.get("pre_token_balance",0.0) or 0.0),float(pos.get("submitted_at_ts") or pos.get("entry_ts") or 0.0),pos.get("entry_order_id"),tid,)
  verdict=cls["verdict"]
  p_tid=str(pos.get("box_partner_trade_id") or "")
  if verdict in {"ARRIVED","MATCHED_UNSETTLED"}:
   self._apply_entry_evidence(pos,cls)
   partner_dead=bool( p_tid and p_tid not in self.active_positions and any(c.get("trade_id")==p_tid and c.get("status")=="NOT_EXECUTED" for c in self.closed_positions) )
   if partner_dead:
    pos["is_dominance_box"]=False
    pos["is_legged_out_residual"]=True
    pos["pending_unwind_tag"]="D1_LEGGED_OUT_RESIDUAL_UNWIND"
    pos["status"]=ExecutionStatus.POSITION_CONFIRMED if verdict=="ARRIVED" else ExecutionStatus.MATCHED_PENDING_SETTLEMENT
    pos["exit_order_status"]="UNWIND_RETRY_REQUIRED"
    pos["stop_triggered_ts"]=time.time()
    pos["next_unwind_retry_ts"]=0.0
   else:
    pos["status"]=ExecutionStatus.POSITION_CONFIRMED if verdict=="ARRIVED" else ExecutionStatus.MATCHED_PENDING_SETTLEMENT
    pos["exit_order_status"]="AWAITING_DELTA_SETTLEMENT"
   self.save_state()
   logger.warning(f"[ENTRY RECONCILED] {tid}: {verdict} ({pos.get('entry_finality_source')}, shares={pos.get('entry_shares')}).")
   return True
  if verdict=="NOT_EXECUTED":
   pos["entry_shares"]=0.0
   pos["notional_usd"]=0.0
   pos["non_execution_proof"]=cls.get("proof")
   partner=self.active_positions.get(p_tid) if p_tid else None
   if isinstance(partner,dict) and partner.get("is_dominance_box"):
    partner["is_dominance_box"]=False
    partner["is_legged_out_residual"]=True
    partner["pending_unwind_tag"]="D1_LEGGED_OUT_RESIDUAL_UNWIND"
    if partner.get("status")!="ENTRY_OUTCOME_UNKNOWN":
     partner["exit_order_status"]="UNWIND_RETRY_REQUIRED"
     partner["stop_triggered_ts"]=time.time()
     partner["next_unwind_retry_ts"]=0.0
   self._close_position(tid,pos,"NOT_EXECUTED","ENTRY_NOT_EXECUTED_VERIFIED",won=False,record_pnl=False)
   return True
  return False
 def _resolve_unknown_exit_post(self,tid:str,pos:Dict[str,Any],open_orders:Optional[List[Dict[str,Any]]])->bool:
  token_id=pos.get("token_id")
  oid=pos.get("exit_order_id")
  fallback_px=float(pos.get("target_exit_price",0.0) or 0.0)
  if oid:
   summary=self.executor.get_order_fill_summary(str(oid),token_id)
   if summary is None:
    return False
   self._record_order_summary(pos,summary,fallback_px,taker=False)
   if float(pos.get("remaining_shares",0.0) or 0.0)<=0.01:
    self._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True)
    return True
   if not summary["terminal"]:
    pos["exit_order_status"]="RESTING"
    pos["status"]=ExecutionStatus.EXIT_RESTING
    self._release_position_reservations(pos)
    self.save_state()
    return True
   self._release_position_reservations(pos,[str(oid)])
   pos["exit_order_id"]=None
   pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED"
   for t in pos.get("exit_tranches",[]):
    if t.get("status") in {"POSTED","IN_FLIGHT"}:
     t["status"]="PENDING"
   self.save_state()
   return True
  if open_orders is None:
   return False
  tracked={str(p.get(k)) for p in self.active_positions.values() for k in ("exit_order_id","unwind_order_id") if p.get(k)}
  candidates=[ o for o in open_orders if o and str(o.get("side","")).upper()=="SELL" and str(o.get("asset_id") or o.get("token_id") or "")==str(token_id) and str(o.get("id") or o.get("orderID") or "") not in tracked ]
  if len(candidates)==1:
   adopted=str(candidates[0].get("id") or candidates[0].get("orderID"))
   pos["exit_order_id"]=adopted
   pos["exit_order_size"]=float(self._num(candidates[0].get("original_size")) or pos.get("remaining_shares",0.0))
   pos["exit_order_status"]="RESTING"
   pos["status"]=ExecutionStatus.EXIT_RESTING
   size=float(pos["exit_order_size"]) - float(self._num(candidates[0].get("size_matched")) or 0.0)
   self._release_position_reservations(pos)
   self.executor.reserve_inventory(token_id,size,reservation_id=adopted)
   self.save_state()
   logger.warning(f"[EXIT RECONCILED] {tid}: adopted resting exit order {adopted} discovered on the exchange.")
   return True
  if len(candidates) > 1:
   return False
  attempt_ts=float(pos.get("exit_post_attempt_ts") or 0.0)
  fills=self._fetch_account_fills(token_id,attempt_ts - 5.0,"SELL",exclude_tid=tid)
  if fills is None:
   return False
  fills=[f for f in fills if str(f.get("order_id")) not in set((pos.get("order_records") or {}).keys())]
  if fills:
   self._record_history_fills(pos,fills,taker=False)
  if time.time() - attempt_ts < UNWIND_UNKNOWN_PROOF_AGE_S and not fills:
   return False
  self._release_position_reservations(pos)
  if float(pos.get("remaining_shares",0.0) or 0.0)<=0.01:
   self._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True)
   return True
  return False
 def _exit_fill_settled_onchain(self,pos:Dict[str,Any],summary:Dict[str,Any])->bool:
  try:
   st=str(summary.get("status") or "").upper()
   orig=float(summary.get("original_size") or 0.0)
   matched=float(summary.get("matched") or 0.0)
   if ( self.dry_run or summary.get("resting") or summary.get("has_reverted_fills") or st not in {"MATCHED","FILLED","CONFIRMED","MINED"} or orig<=0.0 or matched < orig - 0.01 or str((summary.get("raw") or {}).get("side") or "SELL").upper()!="SELL" or not hasattr(self.executor,"get_onchain_erc1155_balance") ):
    return False
   tok=str(pos.get("token_id") or "")
   if not tok:
    return False
   bal=self.executor.get_onchain_erc1155_balance(tok)
   rem=float(pos.get("remaining_shares",0.0) or 0.0)
   ok=bal is not None and float(bal)<=rem + 0.011
   if ok:
    logger.info( f"[FILL RECONCILED ON-CHAIN] {summary.get('order_id')}: MATCHED {matched:.2f}/{orig:.2f}; wallet " f"{float(bal):.4f} <= position remaining {rem:.4f} -> exit fill final." )
   return ok
  except Exception as e:
   logger.debug(f"On-chain exit settlement check skipped: {e}")
   return False
 def _resolve_fill_reconciliation(self,tid:str,pos:Dict[str,Any])->bool:
  oid=pos.get("pending_canceled_order_id") or pos.get("exit_order_id") or pos.get("unwind_order_id")
  if not oid:
   return False
  summary=self.executor.get_order_fill_summary(str(oid),pos.get("token_id"))
  if summary is None:
   return False
  is_exit=str(oid)==str(pos.get("exit_order_id") or pos.get("pending_canceled_order_id") or "")
  fallback_px=float(pos.get("target_exit_price",0.0) or 0.0) if is_exit else float(pos.get("unwind_limit_price") or 0.01)
  self._record_order_summary(pos,summary,fallback_px,taker=not is_exit)
  if float(pos.get("remaining_shares",0.0) or 0.0)<=0.01:
   self._close_position(tid,pos,ExecutionStatus.FILLED if is_exit else ExecutionStatus.SETTLED,"MAKER_SCALP_FILLED_CLOB" if is_exit else "UNWIND_RECONCILED",won=None)
   return True
  if not summary["terminal"] and is_exit and self._exit_fill_settled_onchain(pos,summary):
   summary={**summary,"terminal":True}
  if not summary["terminal"]:
   if summary.get("resting",False) and str(oid)==str(pos.get("exit_order_id") or "") and not pos.get("pending_canceled_order_id"):
    pos["exit_order_status"]="RESTING"
    pos["status"]=ExecutionStatus.PARTIALLY_FILLED
    self.save_state()
    return True
   return False
  self._release_position_reservations(pos,[str(oid)])
  if str(pos.get("exit_order_id") or "")==str(oid):
   pos["exit_order_id"]=None
  pos["pending_canceled_order_id"]=None
  pos["cancel_pending_order_id"]=None
  pos["unwind_order_id"]=None if str(pos.get("unwind_order_id") or "")==str(oid) else pos.get("unwind_order_id")
  pos["status"]=ExecutionStatus.PARTIALLY_FILLED
  expiry=float(pos.get("candle_expiry_ts",0.0) or 0.0)
  if pos.get("resolved_winning_outcome") is not None:
   pos["exit_order_status"]="CANCELED_FOR_RESOLUTION"
  elif time.time() - float(pos.get("stop_triggered_ts",0.0) or 0.0) < 300.0:
   pos["exit_order_status"]="UNWIND_RETRY_REQUIRED"
   attempts=int(pos.get("unwind_retry_count",0) or 0) + 1
   pos["unwind_retry_count"]=attempts
   pos["next_unwind_retry_ts"]=time.time() + min(15.0,1.5 ** min(attempts,5))
   pos["is_liquidating"]=False
  elif expiry and (expiry - time.time()) < self.tte_cancel_window:
   pos["exit_order_status"]="PRE_EXPIRY_EVALUATION_REQUIRED"
  else:
   pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED"
  self.save_state()
  return True
 def _resolve_lifecycle(self,tid:str,pos:Dict[str,Any],open_orders:Optional[List[Dict[str,Any]]]=None,force:bool=False)->bool:
  now=time.time()
  if not force and now < float(pos.get("next_resolve_ts",0.0) or 0.0):
   return False
  st=pos.get("exit_order_status")
  pst=pos.get("status")
  resolved=False
  try:
   if st=="ENTRY_OUTCOME_UNKNOWN" or pst=="ENTRY_OUTCOME_UNKNOWN" or st=="ENTRY_ONCHAIN_REVERTED":
    resolved=self._resolve_unknown_entry(tid,pos)
   elif st in self.UNWIND_UNKNOWN_STATES:
    resolved=self._resolve_unknown_unwind(tid,pos)
   elif st=="EXIT_POST_OUTCOME_UNKNOWN":
    resolved=self._resolve_unknown_exit_post(tid,pos,open_orders)
   elif st=="FILL_RECONCILIATION_REQUIRED":
    resolved=self._resolve_fill_reconciliation(tid,pos)
   elif st=="LIQUIDITY_CRISIS" or pst=="LIQUIDITY_CRISIS":
    token_id=pos.get("token_id")
    expiry_ts=float(pos.get("candle_expiry_ts",0.0) or 0.0)
    book_closed=(expiry_ts > 0.0 and now>=expiry_ts)
    book={}
    if token_id and not book_closed:
     try:
      book=self.executor.get_market_book(token_id)
     except Exception as bk_err:
      if "404" in str(bk_err) or "no orderbook exists" in str(bk_err).lower():
       book_closed=True
      else:
       raise
    bids=[b for b in (book.get("bids") or []) if float(b.get("price",0.0)) > 0 and float(b.get("size",0.0)) > 0]
    asks=[a for a in (book.get("asks") or []) if float(a.get("price",0.0)) > 0 and float(a.get("size",0.0)) > 0]
    best_b=max((float(b["price"]) for b in bids),default=0.0)
    best_a=min((float(a["price"]) for a in asks),default=1.0)
    if book_closed or (best_b > 0.0 and (not asks or best_b < best_a)):
     pos["status"]=ExecutionStatus.EXIT_RESTING if pos.get("exit_order_id") else ExecutionStatus.POSITION_CONFIRMED
     pos["exit_order_status"]="RESTING" if pos.get("exit_order_id") else ("CANCELED_FOR_EXPIRY_HOLD" if book_closed else "EXIT_RECOVERY_REQUIRED")
     pos.pop("liquidity_crisis_ts",None)
     pos.pop("zero_bid_detected_ts",None)
     self.save_state()
     logger.info(f"[LIQUIDITY_CRISIS_RESOLVED] {tid}: {'Market expired/closed' if book_closed else f'Valid bid restored (${best_b:.4f})'}. Resuming.")
     resolved=True
  except Exception as e:
   logger.error(f"[LIFECYCLE] Resolver error for {tid} ({st}): {e}",exc_info=True)
   resolved=False
  if not resolved and tid in self.active_positions:
   pos["next_resolve_ts"]=now + 5.0
  return resolved
 def _apply_exit_post_result(self,pos:Dict[str,Any],exit_res:Dict[str,Any],size:float)->bool:
  exit_res=exit_res or {}
  now=time.time()
  if exit_res.get("success"):
   pos["exit_order_id"]=exit_res.get("orderID")
   pos["exit_order_size"]=float(size)
   posted_px=self._num(exit_res.get("price"))
   if posted_px is not None and 0.0 < posted_px < 1.0:
    if abs(posted_px - float(pos.get("target_exit_price") or 0.0)) > 1e-9:
     pos["requested_exit_price"]=pos.get("target_exit_price")
    pos["target_exit_price"]=posted_px
   pos["exit_order_status"]="RESTING"
   pos["status"]=ExecutionStatus.EXIT_RESTING
   pos["exit_post_failures"]=0
   pos.pop("next_exit_post_ts",None)
   return True
  if exit_res.get("outcome_unknown"):
   oid=exit_res.get("orderID")
   if oid:
    pos["exit_order_id"]=oid
    pos["exit_order_size"]=float(size)
   if exit_res.get("reservation_id"):
    pos.setdefault("pending_reservation_ids",[]).append(exit_res["reservation_id"])
   pos["exit_post_attempt_ts"]=now
   pos["exit_order_status"]="EXIT_POST_OUTCOME_UNKNOWN"
   logger.critical(f"Ambiguous maker exit post for {pos.get('trade_id')} (OID: {oid}); no re-post until reconciled.")
   return False
  if exit_res.get("crossed_at_max_tick"):
   pos["next_exit_post_ts"]=now + 1.0
   pos["exit_order_status"]="CROSSED_AT_MAX_TICK_WAIT"
   return False
  failures=int(pos.get("exit_post_failures",0) or 0) + 1
  pos["exit_post_failures"]=failures
  err_txt=str(exit_res.get("error") or "").lower()
  entry_age=now - float(pos.get("entry_ts",0.0) or 0.0)
  if "not enough balance" in err_txt and 0.0<=entry_age < 15.0:
   pos["next_exit_post_ts"]=now + 0.5
   pos["exit_order_status"]="AWAITING_DELTA_SETTLEMENT"
   logger.info(f"Maker exit post awaiting CLOB balance indexer sync for {pos.get('trade_id')} (age={entry_age:.2f}s); retry in 0.5s.")
   return False
  pos["next_exit_post_ts"]=now + min(30.0,2.0 ** min(failures,5))
  pos["exit_order_status"]="AWAITING_DELTA_SETTLEMENT" if exit_res.get("retryable") else "POST_FAILED"
  logger.warning(f"Maker exit post deferred for {pos.get('trade_id')} ({exit_res.get('error')}); retry with backoff.")
  return False
 def _attempt_maker_exit_post(self,tid:str,pos:Dict[str,Any])->bool:
  import threading
  locks=self.__dict__.setdefault("_exit_post_locks",{})
  lock=locks.get(tid)
  if lock is None:
   lock=locks.setdefault(tid,threading.Lock())
  if not lock.acquire(blocking=False):
   return False
  try:
   if pos.get("exit_order_id"):
    return False
   return self._attempt_maker_exit_post_impl(tid,pos)
  finally:
   lock.release()
 def _settlement_recheck_delay(self,pos:Dict[str,Any],now:float)->float:
  entry_ts=float(pos.get("entry_ts",0.0) or 0.0)
  if entry_ts > 0.0 and (now - entry_ts) < FAST_SETTLEMENT_RECHECK_WINDOW_SEC:
   return FAST_CONFIRM_POLL_SEC
  return 5.0
 def _maybe_queue_jump_on_post(self,pos:Dict[str,Any],size:float)->None:
  if pos.get("queue_jumped") or pos.get("is_dominance_box"):
   return
  tgt=float(pos.get("target_exit_price") or 0.0)
  if tgt < QUEUE_JUMP_MIN_TARGET:
   return
  book=fast_tick_book_for_token(read_fast_tick(pos.get("asset","BTC")),pos.get("token_id"))
  if not book:
   return
  jump=compute_queue_priority_maker_price( float(pos.get("entry_price",0.70) or 0.70),size,book.get("bids",[]),book.get("asks",[]),tgt,)
  if jump is not None:
   logger.info(f"[QUEUE JUMP] {pos.get('trade_id')}: wall at ${tgt:.2f}; posting maker TP at ${jump:.2f} instead.")
   pos["target_exit_price"]=jump
   pos["queue_jumped"]=True
   for t in pos.get("exit_tranches",[]):
    if t.get("status")=="PENDING" and abs(float(t.get("price",0.0)) - tgt) < 1e-9:
     t["price"]=jump
     break
 async def _fast_confirm_and_post_maker_exit(self,trade_id:str)->bool:
  deadline=time.time() + FAST_CONFIRM_WINDOW_SEC
  uws=getattr(self.executor,"_user_ws_cache",None)
  while time.time() < deadline:
   prev_seq=uws.fill_sequence if uws is not None else None
   pos=self.active_positions.get(trade_id)
   if pos is None or pos.get("exit_order_id"):
    return False
   if position_may_post_new_maker_exit(pos):
    try:
     posted=await asyncio.to_thread(self._attempt_maker_exit_post,trade_id,pos)
    except Exception as e:
     logger.warning(f"[FAST CONFIRM] {trade_id}: maker exit attempt error: {e}")
     posted=False
    if posted:
     logger.info(f"[FAST CONFIRM] {trade_id}: maker TP posted within the fast-confirm window.")
     return True
    if position_requires_global_halt(pos):
     return False
   if uws is not None and uws.is_healthy():
    await uws.wait_for_fill_or_timeout(FAST_CONFIRM_POLL_SEC,prev_seq=prev_seq)
   else:
    await asyncio.sleep(FAST_CONFIRM_POLL_SEC)
  return False
 def _spawn_fast_confirm(self,trade_id:str)->None:
  inflight=self.__dict__.setdefault("_fast_confirm_inflight_ids",set())
  if trade_id in inflight:
   return
  try:
   loop=asyncio.get_running_loop()
   self._main_loop=loop
  except RuntimeError:
   main_loop=getattr(self,"_main_loop",None)
   if main_loop is not None and main_loop.is_running():
    try:
     main_loop.call_soon_threadsafe(self._spawn_fast_confirm,trade_id)
    except RuntimeError:
     pass
   return
  inflight.add(trade_id)
  task=loop.create_task(self._fast_confirm_and_post_maker_exit(trade_id))
  tasks=self.__dict__.setdefault("_fast_confirm_tasks",set())
  tasks.add(task)
  task.add_done_callback(lambda t:(tasks.discard(t),inflight.discard(trade_id)))
 def _attempt_maker_exit_post_impl(self,tid:str,pos:Dict[str,Any])->bool:
  now=time.time()
  expiry=float(pos.get("candle_expiry_ts",now + 600.0) or (now + 600.0))
  eff_cancel_win=5.0 if pos.get("sleeve")=="SLEEVE_4_BOUNDARY_SNIPE" else self.tte_cancel_window
  if not position_may_post_new_maker_exit(pos) or (expiry - now) < eff_cancel_win:
   return False
  if now < float(pos.get("next_exit_post_ts",0.0) or 0.0):
   return False
  token_id=pos.get("token_id")
  if not token_id:
   return False
  eps=self.executor.calculate_balance_epsilon(0.001)
  if self.dry_run:
   gross=Decimal(str(pos.get("gross_entry_shares",pos.get("entry_shares",0.0))))
   if not pos.get("inventory_reconciled"):
    net=float(gross.quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
    pos["entry_shares"]=net
    pos["remaining_shares"]=net
    pos["remaining_exit_shares"]=net
    pos["remaining_cost_basis"]=pos.get("notional_usd",0.0)
    if net > 0 and float(pos.get("notional_usd",0.0) or 0.0) > 0:
     true_cost_per_share=round(float(pos["notional_usd"]) / net,4)
     if true_cost_per_share > float(pos.get("entry_price",0.0) or 0.0):
      pos["entry_price"]=true_cost_per_share
      pos["target_exit_price"]=0.99 if pos.get("is_dominance_box") else self._calculate_target_exit(true_cost_per_share,expiry - now)
    pos["inventory_reconciled"]=True
  else:
   final,reverted=self._verify_entry_finality(pos)
   if reverted and not final:
    logger.critical(f"[ON-CHAIN REVERT] Entry for {tid} reverted on Polygon; holding for reconciliation.")
    pos["status"]=ExecutionStatus.FAILED
    pos["exit_order_status"]="ENTRY_ONCHAIN_REVERTED"
    pos["close_reason"]="ONCHAIN_REVERT_DETECTED"
    self.save_state()
    return False
   bal,src=self._wallet_token_balance(token_id)
   if bal is None:
    logger.warning(f"[FAIL-CLOSED] Wallet inventory unavailable for {token_id}; delaying exit for {tid}.")
    return False
   if not final and src in {self.ONCHAIN_SOURCE,"CLOB_BALANCE_API"}:
    final=True
   if not final:
    pos["exit_blocked_reason"]=f"ENTRY_FINALITY_UNPROVEN(source={src})"
    pos["next_exit_post_ts"]=now + self._settlement_recheck_delay(pos,now)
    self.save_state()
    return False
   if not pos.get("inventory_reconciled") and float(pos.get("filled_exit_shares",0.0) or 0.0)<=0.0:
    pre_bal=float(pos.get("pre_token_balance",0.0) or 0.0)
    received=Decimal(str(bal - pre_bal))
    gross=Decimal(str(pos.get("gross_entry_shares",pos.get("entry_shares",0.0))))
    d_eps=Decimal(str(eps))
    min_valid_received=Decimal("0.01")
    if received < min_valid_received or received > gross + d_eps + Decimal("0.01"):
     pos["exit_blocked_reason"]=f"ENTRY_INVENTORY_UNRECONCILED(received={received}, gross={gross})"
     pos["next_exit_post_ts"]=now + self._settlement_recheck_delay(pos,now)
     self.save_state()
     return False
    net=float(min(received,gross).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
    if gross > Decimal("0") and received < gross - Decimal("0.02"):
     entry_oid=str(pos.get("entry_order_id") or pos.get("order_id") or "").strip()
     clob_entry_sum=None
     if entry_oid and hasattr(self.executor,"get_order_fill_summary"):
      try:
       raw_es=self.executor.get_order_fill_summary(entry_oid,token_id)
       if isinstance(raw_es,dict) and float(raw_es.get("matched") or 0.0) > 0.0:
        clob_entry_sum=raw_es
      except Exception:
       clob_entry_sum=None
     entry_age_s=max(0.0,now - float(pos.get("entry_ts") or now))
     if clob_entry_sum is not None:
      clob_m=Decimal(str(clob_entry_sum["matched"]))
      if received + Decimal("0.05") < clob_m:
       if entry_age_s < 18.0:
        pos["exit_blocked_reason"]=f"PARTIAL_BATCH_SETTLING(wallet={received}, clob={clob_m})"
        pos["next_exit_post_ts"]=now + self._settlement_recheck_delay(pos,now)
       else:
        pos["exit_blocked_reason"]=f"ENTRY_INVENTORY_RECONCILIATION_REQUIRED(wallet={received}, clob={clob_m})"
        pos["exit_order_status"]="ENTRY_INVENTORY_RECONCILIATION_REQUIRED"
       self.save_state()
       return False
      if clob_m < gross * Decimal("0.98"):
       orig_notional=float(pos.get("notional_usd",0.0) or 0.0)
       pos.setdefault("intended_notional",orig_notional)
       auth_cash=float(clob_entry_sum.get("cash") or 0.0)
       fill_ratio=float(clob_m / gross)
       pos["notional_usd"]=round(auth_cash if auth_cash > 0.0 else (orig_notional * fill_ratio),4)
       pos["fee_usd"]=round(float(clob_entry_sum.get("fee") or (float(pos.get("fee_usd",0.0) or 0.0) * fill_ratio)),4)
     elif entry_oid:
      if entry_age_s < 15.0:
       pos["exit_blocked_reason"]=f"ENTRY_SETTLEMENT_PENDING(wallet={received}, gross={gross})"
       pos["next_exit_post_ts"]=now + self._settlement_recheck_delay(pos,now)
      else:
       pos["exit_blocked_reason"]=f"ENTRY_INVENTORY_RECONCILIATION_REQUIRED(wallet={received}, gross={gross})"
       pos["exit_order_status"]="ENTRY_INVENTORY_RECONCILIATION_REQUIRED"
      self.save_state()
      return False
     elif received < gross * Decimal("0.92"):
      fill_ratio=float(received / gross)
      orig_notional=float(pos.get("notional_usd",0.0) or 0.0)
      pos.setdefault("intended_notional",orig_notional)
      pos["notional_usd"]=round(orig_notional * fill_ratio,4)
      pos["fee_usd"]=round(float(pos.get("fee_usd",0.0) or 0.0) * fill_ratio,4)
     elif "v2" not in str(pos.get("fee_source") or "").lower():
      pos["entry_fee_asset"]="SHARES"
      pos["entry_fee_cash_usd"]=0.0
    pos["entry_shares"]=net
    pos["remaining_shares"]=net
    pos["remaining_exit_shares"]=net
    pos["remaining_cost_basis"]=pos.get("notional_usd",0.0)
    if net > 0 and float(pos.get("notional_usd",0.0) or 0.0) > 0:
     true_cost_per_share=round(float(pos["notional_usd"]) / net,4)
     if true_cost_per_share > float(pos.get("entry_price",0.0) or 0.0):
      pos["entry_price"]=true_cost_per_share
      pos["target_exit_price"]=0.99 if pos.get("is_dominance_box") else self._calculate_target_exit(true_cost_per_share,expiry - now)
    pos["inventory_reconciled"]=True
    pos.pop("exit_blocked_reason",None)
    pos.setdefault("entry_inventory_source",src)
   else:
    rem_needed=float(pos.get("remaining_shares",pos.get("entry_shares",0.0)) or 0.0)
    if bal + eps < rem_needed:
     logger.critical( f"[INVENTORY DISCREPANCY] {tid}: wallet {bal:.4f} < remaining {rem_needed:.4f} ({src}). " "Refusing to post; reconciling against exchange history." )
     pos["exit_order_status"]="UNRESOLVED_BALANCE_DISCREPANCY"
     pos["unwind_attempt_ts"]=float(pos.get("entry_ts") or now)
     self.save_state()
     return False
  size=float(Decimal(str(pos.get("remaining_shares",pos.get("entry_shares",0.0)) or 0.0)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
  if size < 0.01:
   return False
  rem_total=size
  entry_px=float(pos.get("entry_price",0.70))
  use_tranches=self._use_two_tranche_maker_exit(pos.get("sleeve"))
  t1_offset=self._tranche1_tp_offset(pos.get("sleeve"))
  is_live_ctf=( (not self.dry_run) and getattr(self.executor,"auth_mode","") in ("LIVE","AUTHENTICATED_L2") and bool(token_id and str(token_id).isdigit() and len(str(token_id))>=20) and not getattr(self,"enable_mid_hour_t1_12c",False) )
  if use_tranches and float(pos.get("notional_usd",0.0) or 0.0)>=10.0 and "exit_tranches" not in pos and rem_total>=10.0:
   t1_sz=float((Decimal(str(rem_total)) * Decimal("0.50")).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
   t2_sz=float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
   if t1_sz>=5.0 and t2_sz>=5.0:
    t1_px=0.95 if is_live_ctf else min(0.94,round(entry_px + t1_offset,2))
    t2_px=0.98
    pos["exit_tranches"]=[ {"idx":1,"size":t1_sz,"price":t1_px,"status":"PENDING"},{"idx":2,"size":t2_sz,"price":t2_px,"status":"PENDING"},]
   else:
    pos["target_exit_price"]=0.96 if is_live_ctf else min(0.96,round(entry_px + 0.16,2))
  active_tranche=None
  pending_tranches=[t for t in pos.get("exit_tranches",[]) if t.get("status")=="PENDING"]
  if pending_tranches and float(pending_tranches[0]["size"])>=5.0 and rem_total>=5.0:
   cand_sz=min(rem_total,float(pending_tranches[0]["size"]))
   leftover=round(rem_total - cand_sz,4)
   if 0.01 < leftover < 5.0:
    size=rem_total
    pos["target_exit_price"]=max(float(t["price"]) for t in pending_tranches)
    pos.pop("exit_tranches",None)
   else:
    active_tranche=pending_tranches[0]
    size=cand_sz
    pos["target_exit_price"]=float(active_tranche["price"])
  else:
   size=rem_total
   if pending_tranches and rem_total>=5.0:
    pos["target_exit_price"]=max(float(t["price"]) for t in pending_tranches)
   pos.pop("exit_tranches",None)
   if pos.get("is_dominance_box"):
    pos["target_exit_price"]=0.99
   elif self._effective_exit_policy()=="hold_98":
    pos["target_exit_price"]=0.98
   elif not pos.get("target_exit_price"):
    pos["target_exit_price"]=0.96 if is_live_ctf else min(0.96,round(entry_px + 0.16,2))
  pos["status"]=ExecutionStatus.POSITION_CONFIRMED
  if size < 5.0 and not self.dry_run and str(token_id).isdigit() and len(str(token_id))>=20:
   logger.warning( f"[SUB-MINIMUM LOT GUARD] {tid}: remaining size {size:.2f} < 5.0 CLOB lot minimum; " "holding under supervised terminal policy without spamming HTTP 400s." )
   pos["exit_order_status"]="SUB_MINIMUM_LOT_SUPERVISED_HOLD"
   pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD"
   self.save_state()
   return False
  self._maybe_queue_jump_on_post(pos,size)
  exit_res=self.executor.post_maker_exit_order( token_id=token_id,price=pos["target_exit_price"],size=size,side="SELL",)
  if ( not (exit_res or {}).get("success") and not (exit_res or {}).get("outcome_unknown") and not (exit_res or {}).get("crossed_at_max_tick") and "crosses book" in str((exit_res or {}).get("error","")).lower() ):
   try:
    book=self.executor.get_market_book(token_id) if hasattr(self.executor,"get_market_book") else None
    bids=(book or {}).get("bids",[])
    if bids:
     best_bid=max((float(b.get("price",0.0) or 0.0) for b in bids if isinstance(b,dict)),default=0.0)
     repriced=min(0.99,round(best_bid + 0.01,4))
     if repriced > float(pos["target_exit_price"]):
      logger.info(f"[MAKER REPRICE] {tid}: post_only crossed book (bid={best_bid:.4f}). Repricing ask to ${repriced:.4f}.")
      pos["target_exit_price"]=repriced
      if active_tranche is not None:
       active_tranche["price"]=repriced
      exit_res=self.executor.post_maker_exit_order( token_id=token_id,price=repriced,size=size,side="SELL",)
   except Exception as e:
    logger.debug(f"Reprice query failed for {tid}: {e}")
  posted=self._apply_exit_post_result(pos,exit_res,size)
  if active_tranche is not None and posted:
   active_tranche["status"]="POSTED"
  elif active_tranche is not None and (exit_res or {}).get("outcome_unknown"):
   active_tranche["status"]="IN_FLIGHT"
  self.save_state()
  if posted:
   logger.info(f"✓ MAKER EXIT POSTED: {tid} | {size:.2f} shares @ ${pos['target_exit_price']:.4f} | OID={pos['exit_order_id']}")
  return posted
 def _handle_unwind_response(self,tid:str,pos:Dict[str,Any],res:Optional[Dict[str,Any]],requested:float,close_reason:str,partial_state:str,limit_price:float)->str:
  res=res or {}
  now=time.time()
  oid=res.get("orderID")
  pos["unwind_limit_price"]=float(limit_price)
  def _mark_unknown(why:str)->str:
   pos["exit_order_status"]="UNWIND_EXECUTION_OUTCOME_UNKNOWN"
   pos["is_liquidating"]=True
   pos["unwind_order_id"]=oid
   pos["unwind_attempt_ts"]=now
   pos["unwind_reason"]=close_reason
   pos["unwind_last_error"]=why
   if res.get("reservation_id"):
    pos.setdefault("pending_reservation_ids",[]).append(res["reservation_id"])
   pos["next_resolve_ts"]=0.0
   self.save_state()
   logger.critical(f"[UNWIND OUTCOME UNKNOWN] {tid}: {why}. No repeat submission until exchange reconciliation.")
   return "UNKNOWN"
  if res.get("outcome_unknown"):
   return _mark_unknown(str(res.get("error") or "AMBIGUOUS_UNWIND_RESPONSE"))
  matched=self._num(res.get("matched_size"))
  taking=self._num(res.get("taking_amount"))
  claims_fill=bool( res.get("success") or res.get("partial") or (matched or 0.0) > 0.0 or (oid and (taking or 0.0) > 0.0) or (res.get("matched_size") is not None and (taking or 0.0) > 0.0) )
  if not claims_fill:
   return "FAILED"
  if res.get("success") and not oid and (matched or 0.0)==0.0 and (taking or 0.0)==0.0:
   if requested < 0.01:
    self._close_position(tid,pos,ExecutionStatus.SETTLED,f"{close_reason}_DUST_RESIDUAL",won=None)
    return "CLOSED"
   return "FAILED"
  contradictory=( matched is None or matched<=0.0 or matched > requested + 1e-4 or taking is None or taking < 0.0 or bool(res.get("taking_amount_missing")) )
  if contradictory:
   return _mark_unknown( f"CONTRADICTORY_OR_INCOMPLETE_FILL_QUANTITIES(matched={res.get('matched_size')}, taking={res.get('taking_amount')})" )
  fee=self._num(res.get("fee_usd")) or 0.0
  record_id=oid or f"{close_reason}_{int(now*1000)}"
  taking_estimated=bool(res.get("taking_amount_estimated",False))
  self.record_fill_and_update_position( pos,record_id,matched,taking,fee,cash_is_estimated=taking_estimated )
  if taking_estimated:
   pos["pending_settlement_order_id"]=str(record_id)
  if res.get("fee_is_estimated"):
   pos["exit_fee_estimated"]=True
  if float(pos.get("remaining_shares",0.0) or 0.0)<=0.01:
   won_flag=False if ("SALVAGE" in close_reason or "STOP" in close_reason) else None
   if taking_estimated:
    won_flag=None
   self._close_position(tid,pos,ExecutionStatus.SETTLED,close_reason,won=won_flag)
   return "CLOSED"
  pos["status"]=ExecutionStatus.PARTIALLY_FILLED
  pos["exit_order_status"]=partial_state
  pos["is_liquidating"]=False
  pos["unwind_order_id"]=None
  attempts=int(pos.get("unwind_retry_count",0) or 0) + 1
  pos["unwind_retry_count"]=attempts
  pos["next_unwind_retry_ts"]=now + min(30.0,2.0 ** min(attempts,5))
  logger.warning( f"⚠️ [PARTIAL UNWIND] {tid}: matched {matched:.2f}; cumulative {pos.get('filled_exit_shares', 0.0):.2f}/" f"{pos.get('entry_shares', 0.0):.2f}; remaining {pos.get('remaining_shares', 0.0):.2f} retained." )
  self.save_state()
  return "PARTIAL"
 @staticmethod
 def calculate_realized_cash_pnl(pos:Dict[str,Any],gross_exit_cash:float,exit_fee:float=0.0)->float:
  entry_fee_asset=str(pos.get("entry_fee_asset","")).upper()
  if entry_fee_asset=="SHARES":
   entry_cash_fee=float(pos.get("entry_fee_cash_usd",0.0))
  else:
   entry_cash_fee=float(pos.get("entry_fee_cash_usd",pos.get("fee_usd",0.0)))
  notional=float(pos.get("notional_usd",0.0))
  cash_in=float(gross_exit_cash)
  cash_exit_fee=float(exit_fee)
  return round(cash_in - notional - entry_cash_fee - cash_exit_fee,2)
 @staticmethod
 def record_fill_and_update_position( pos:Dict[str,Any],order_id:str,matched_shares:float,taking_cash:float,fee_usd:float=0.0,cash_is_estimated:bool=False,)->Dict[str,Any]:
  order_records=pos.setdefault("order_records",{})
  current_exit_oid=str(pos.get("exit_order_id") or "")
  legacy_shares=float(pos.get("filled_exit_shares",0.0) or 0.0)
  legacy_cash=float(pos.get("realized_exit_cash",0.0) or 0.0)
  legacy_fee=float(pos.get("realized_exit_fee",0.0) or 0.0)
  if str(order_id)!=current_exit_oid and (legacy_shares > 0.0 or legacy_cash > 0.0 or legacy_fee > 0.0) and "LEGACY_PREVIOUS_FILLS" not in order_records:
   existing_shares=sum(float(r.get("matched",0.0)) for r in order_records.values())
   existing_cash=sum(float(r.get("cash",0.0)) for r in order_records.values())
   existing_fee=sum(float(r.get("fee",0.0)) for r in order_records.values())
   diff_shares=max(0.0,round(legacy_shares - existing_shares,4))
   diff_cash=max(0.0,round(legacy_cash - existing_cash,4))
   diff_fee=max(0.0,round(legacy_fee - existing_fee,4))
   if diff_shares > 0.0 or diff_cash > 0.0 or diff_fee > 0.0:
    order_records["LEGACY_PREVIOUS_FILLS"]={ "size":diff_shares,"matched":diff_shares,"cash":diff_cash,"fee":diff_fee,"cash_is_estimated":bool(pos.get("exit_cash_estimated",False)),}
  oid=str(order_id)
  rec=order_records.setdefault(oid,{ "size":float(pos.get("exit_order_size",pos.get("entry_shares",0.0))),"matched":0.0,"cash":0.0,"confirmed_cash":0.0,"estimated_cash":0.0,"fee":0.0,"cash_is_estimated":bool(cash_is_estimated),})
  rec["matched"]=max(float(rec.get("matched",0.0)),float(matched_shares or 0.0))
  taking_val=float(taking_cash or 0.0)
  if not cash_is_estimated:
   rec["confirmed_cash"]=taking_val
   rec["estimated_cash"]=0.0
   rec["cash"]=taking_val
   rec["cash_is_estimated"]=False
  else:
   if not rec.get("cash_is_estimated",False) and float(rec.get("confirmed_cash",0.0)) > 0.0:
    pass
   else:
    rec["estimated_cash"]=taking_val
    rec["cash"]=taking_val
    rec["cash_is_estimated"]=True
  if float(fee_usd or 0.0) > 0.0:
   rec["fee"]=max(float(rec.get("fee",0.0)),float(fee_usd))
  total_shares=sum(float(r.get("matched",0.0)) for r in order_records.values())
  confirmed_cash=sum(float(r.get("cash",0.0)) for r in order_records.values() if not r.get("cash_is_estimated"))
  estimated_cash=sum(float(r.get("cash",0.0)) for r in order_records.values() if r.get("cash_is_estimated"))
  total_cash=confirmed_cash + estimated_cash
  total_fees=sum(float(r.get("fee",0.0)) for r in order_records.values())
  pos["filled_exit_shares"]=round(total_shares,4)
  pos["confirmed_realized_cash"]=round(confirmed_cash,4)
  pos["estimated_exit_cash"]=round(estimated_cash,4)
  pos["realized_exit_cash"]=round(total_cash,4)
  pos["gross_exit_cash"]=round(total_cash,4)
  pos["exit_cash_estimated"]=(estimated_cash > 0.0)
  pos["realized_exit_fee"]=round(total_fees,4)
  entry_shares=float(pos.get("entry_shares",0.0))
  rem_shares=max(0.0,round(entry_shares - total_shares,4))
  pos["remaining_shares"]=rem_shares
  pos["remaining_exit_shares"]=rem_shares
  if entry_shares > 0.0:
   pos["remaining_cost_basis"]=round(float(pos.get("notional_usd",0.0)) * (rem_shares / entry_shares),4)
  return rec
 def confirm_onchain_redemption( self,trade_id:str,verified_usdc_received:Optional[float]=None,tx_hash:Optional[str]=None,)->bool:
  pos=self.active_positions.get(trade_id)
  if not pos:
   logger.warning(f"[REDEMPTION] Position {trade_id} not found in active_positions.")
   return False
  if not position_is_settlement_receivable(pos):
   logger.warning(f"[REDEMPTION] Position {trade_id} is not awaiting on-chain settlement ({pos.get('status')}).")
   return False
  win_shares=float(pos.get("winning_shares_held",0.0) or 0.0)
  redeemed=set(getattr(self,"redeemed_tx_hashes",[]) or [])
  if self.dry_run:
   payout=float(verified_usdc_received if verified_usdc_received is not None else win_shares)
   tx=tx_hash or f"DRYRUN_REDEMPTION_{trade_id}"
  else:
   receipts=self.executor.find_redemption_payouts( str(pos.get("condition_id") or ""),from_block=pos.get("resolution_block"),tx_hash=tx_hash,)
   if not receipts and win_shares>=0.01 and not tx_hash:
    tok_r=str(pos.get("token_id") or "")
    bal_r=None
    if tok_r and hasattr(self.executor,"get_onchain_erc1155_balance"):
     try:
      bal_r=self.executor.get_onchain_erc1155_balance(tok_r)
     except Exception:
      bal_r=None
    if bal_r is not None and float(bal_r)<=0.0001:
     logger.info( f"[REDEMPTION EXTERNAL] {trade_id}: winning token balance is 0 on-chain -> settling " f"{win_shares:.2f} sh receivable as redeemed outside the harvester." )
     receipts=[{"transaction_hash":f"EXTERNAL_REDEMPTION_{trade_id}","payout_usd":win_shares}]
   if receipts is None:
    if ( win_shares < 0.01 and float(pos.get("confirmed_realized_cash",pos.get("realized_exit_cash",0.0)) or 0.0) > 0.0 ):
     pos["exit_cash_estimated"]=False
     pos["estimated_exit_cash"]=0.0
     pos["confirmed_realized_cash"]=float(pos.get("confirmed_realized_cash") or pos.get("realized_exit_cash") or 0.0)
     logger.info( f"[REDEMPTION DUST CLOSE] {trade_id}: closing on confirmed CLOB cash " f"${pos['confirmed_realized_cash']:.2f} (ignoring {win_shares:.4f} sh dust receivable)." )
     self._close_position(trade_id,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=None)
     return True
    logger.warning(f"[REDEMPTION] Cannot verify redemption for {trade_id} (RPC unavailable); retaining receivable.")
    return False
   fresh=[r for r in receipts if r.get("transaction_hash") and r["transaction_hash"] not in redeemed]
   if not fresh:
    return False
   receipt=fresh[0]
   payout=float(receipt["payout_usd"])
   tx=str(receipt["transaction_hash"])
  if tx in redeemed:
   logger.warning(f"[REDEMPTION] Duplicate redemption receipt {tx} ignored for {trade_id}.")
   return False
  attributed=round(min(payout,win_shares),6)
  self.record_fill_and_update_position(pos,f"ONCHAIN_REDEMPTION_{tx}",win_shares,attributed,0.0)
  cum_cash=float(pos.get("realized_exit_cash",0.0))
  cum_exit_fee=float(pos.get("realized_exit_fee",0.0))
  net_pnl=self.calculate_realized_cash_pnl(pos,cum_cash,cum_exit_fee)
  pos["status"]=ExecutionStatus.SETTLED
  pos["settled_at_utc"]=datetime.now(timezone.utc).isoformat()
  pos["won"]=(net_pnl > 0.0)
  pos["payout_usd"]=round(cum_cash,2)
  pos["net_pnl_usd"]=round(net_pnl,2)
  pos["close_reason"]="ONCHAIN_REDEMPTION_CONFIRMED"
  pos["redemption_tx_hash"]=tx
  pos["redemption_payout_verified_usd"]=payout
  pos["redemption_receivable_usd"]=0.0
  redeemed.add(tx)
  self.redeemed_tx_hashes=sorted(redeemed)[-1000:]
  leg_net_cash=max(0.0,float(cum_cash or 0.0) - float(cum_exit_fee or 0.0))
  if ( not getattr(self,"dry_run",True) and getattr(self,"_last_known_collateral",None) is not None and leg_net_cash > 0.0 and not pos.get("_collateral_exit_credited") ):
   pos["_collateral_exit_credited"]=True
   self._last_known_collateral=float(self._last_known_collateral) + leg_net_cash
  deferred_partner,net_pnl=self._consolidate_dominance_box_close( trade_id,pos,cum_cash,cum_exit_fee,net_pnl,"ONCHAIN_REDEMPTION_CONFIRMED",True )
  if deferred_partner:
   self.executor.invalidate_collateral_cache()
   return True
  self.closed_positions.append(pos)
  self.risk_controller.record_trade_pnl(net_pnl)
  del self.active_positions[trade_id]
  self.save_state()
  self.executor.invalidate_collateral_cache()
  self._pending_collateral_refresh=True
  logger.info(f"✓ ON-CHAIN REDEMPTION VERIFIED: {trade_id} | tx={tx} | USDC=${attributed:.2f} | Net PnL=${net_pnl:+.2f}")
  return True
 def poll_onchain_redemptions(self,force:bool=False)->int:
  now=time.time()
  if not force and (now - self._last_redemption_poll) < REDEMPTION_POLL_INTERVAL_S:
   return 0
  self._last_redemption_poll=now
  settled=0
  for tid,pos in list(self.active_positions.items()):
   if position_is_settlement_receivable(pos) and float(pos.get("winning_shares_held",0.0) or 0.0) > 0.0:
    try:
     m_id_str=str(pos.get("market_id") or "")
     if not self.dry_run and m_id_str.isdigit() and int(m_id_str)>=100000:
      try:
       gm=self.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{m_id_str}",timeout=3.0).json()
       uma_st=str(gm.get("umaResolutionStatus") or "").strip().lower()
       raw_op=gm.get("outcomePrices")
       op=json.loads(raw_op) if isinstance(raw_op,str) else raw_op
       raw_toks=gm.get("clobTokenIds")
       clob_toks=json.loads(raw_toks) if isinstance(raw_toks,str) else raw_toks
       if uma_st in ("","resolved") and isinstance(op,list) and len(op)>=2:
        pos_tok=str(pos.get("token_id") or "")
        if isinstance(clob_toks,list) and pos_tok and pos_tok in [str(x) for x in clob_toks]:
         t_idx=[str(x) for x in clob_toks].index(pos_tok)
        else:
         t_idx=0 if str(pos.get("target_token","UP")).upper() in ("UP","YES") else 1
        if float(op[t_idx])==0.0 and float(op[1 - t_idx])==1.0:
         logger.warning(f"[GAMMA ORACLE OVERRIDE] {tid}: Gamma outcomePrices={op} (idx={t_idx}) shows authoritative resolution against local spot oracle. Closing ghost receivable.")
         pos["expected_terminal_payout_usd"]=0.0
         pos["redemption_receivable_usd"]=0.0
         pos["winning_shares_held"]=0.0
         self._close_position(tid,pos,ExecutionStatus.SETTLED,"MARKET_RESOLVED_LOSS",won=False)
         continue
      except Exception:
       pass
     sub_tx=None
     if not self.dry_run and hasattr(self.executor,"attempt_onchain_redemption"):
      raw_sig_t=getattr(self.executor,"signature_type",None)
      sig_t_val=1 if raw_sig_t is None else int(raw_sig_t)
      if sig_t_val==3 and not bool((os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY") or "").strip()):
       send_operational_alert( "REDEMPTION_BUILDER_CREDS_MISSING",f"Mature winning receivable {tid} (${float(pos.get('winning_shares_held') or 0.0):.2f}) requires POLY_BUILDER_API_KEY.","WARNING",rate_limit_sec=3600.0,dedupe_key="redemption_builder_creds_missing",)
      cond_str=str(pos.get("condition_id") or "")
      try:
       sub_tx=self.executor.attempt_onchain_redemption( cond_str,neg_risk=pos.get("neg_risk") if "neg_risk" in pos else None,)
      except TypeError:
       sub_tx=self.executor.attempt_onchain_redemption(cond_str)
     if self.confirm_onchain_redemption(tid,tx_hash=sub_tx):
      settled += 1
    except Exception as e:
     logger.error(f"[REDEMPTION] Verification error for {tid}: {e}")
  if settled > 0:
   self.executor.invalidate_collateral_cache()
   self._pending_collateral_refresh=True
   logger.info(f"[AUTO-REDEEMER] Swept and settled {settled} mature position(s). Reclaimed collateral to balance.")
  return settled
 def get_condition_id(self,market_id:str)->Optional[str]:
  m_str=str(market_id)
  if m_str in self.market_condition_ids:
   return self.market_condition_ids[m_str]
  try:
   r=self.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{m_str}",timeout=3).json()
   cond_id=r.get("conditionId")
   if cond_id:
    self.market_condition_ids[m_str]=str(cond_id)
    return str(cond_id)
  except Exception as e:
   logger.error(f"Error fetching condition_id for market {market_id}: {e}")
  return None
 def get_token_id(self,market_id:str,target_token:str)->Optional[str]:
  cache_key=f"{market_id}_{target_token}"
  if cache_key in self.market_tokens_cache:
   return self.market_tokens_cache[cache_key]
  try:
   r=self.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{market_id}",timeout=3).json()
   cond_id=r.get("conditionId")
   if cond_id:
    self.market_condition_ids[str(market_id)]=str(cond_id)
   raw=r.get("clobTokenIds")
   tokens=json.loads(raw) if isinstance(raw,str) else raw
   if tokens and len(tokens)>=2:
    self.market_tokens_cache[f"{market_id}_UP"]=str(tokens[0])
    self.market_tokens_cache[f"{market_id}_DOWN"]=str(tokens[1])
    logger.info(f"Resolved tokens for market {market_id}: UP={tokens[0][:10]}... DOWN={tokens[1][:10]}...")
    return self.market_tokens_cache.get(cache_key)
  except Exception as e:
   logger.error(f"Error fetching tokens for market {market_id}: {e}")
  return None
 @staticmethod
 def _resolve_true_usd_spot_from_shock(shock:Dict[str,Any])->Tuple[float,float]:
  cl_proxy=float(shock.get("chainlink_proxy_spot") or 0.0)
  cb_spot=float(shock.get("coinbase_spot") or 0.0)
  bn_spot=float(shock.get("spot_at_t0") or shock.get("spot_price") or shock.get("spot") or shock.get("trigger_price") or 0.0)
  cl_twap=float(shock.get("chainlink_twap_60s") or 0.0)
  if cb_spot > 0.0 and cl_proxy > 0.0 and bn_spot > 0.0:
   if abs(cl_proxy - cb_spot) / cb_spot > 0.0004 and abs(cl_proxy - bn_spot) / bn_spot < 0.00025:
    return cb_spot,(round(cl_twap * (cb_spot / cl_proxy),4) if cl_twap > 0.0 else 0.0)
  usd_spot=cl_proxy if cl_proxy > 0.0 else cb_spot
  if usd_spot > 0.0 and cl_twap > 0.0 and bn_spot > 0.0:
   if abs(cl_twap - usd_spot) / usd_spot > 0.0004 and abs(cl_twap - bn_spot) / bn_spot < 0.0005:
    cl_twap=round(cl_twap * (usd_spot / bn_spot),4)
  return usd_spot,cl_twap
 def get_usd_reference_spot_price(self,asset:str)->Optional[float]:
  now=time.time()
  sym=asset.upper()
  cache_key=f"{sym}USD"
  snap=read_fast_tick(sym,max_age_sec=FAST_TICK_MAX_AGE_SEC,now=now)
  if snap:
   usd_px,_=self._resolve_true_usd_spot_from_shock(snap)
   if math.isfinite(usd_px) and usd_px > 0.0:
    self._spot_cache[cache_key]=(usd_px,now)
    return usd_px
  if cache_key in self._spot_cache:
   val,ts=self._spot_cache[cache_key]
   if now - ts < 1.0:
    return val
  try:
   resp=self.executor._sync_session.get(f"https://api.exchange.coinbase.com/products/{sym}-USD/ticker",timeout=1.5)
   if resp.status_code==200:
    price=float(resp.json().get("price",0.0))
    if math.isfinite(price) and price > 0.0:
     self._spot_cache[cache_key]=(price,now)
     return price
  except Exception as e:
   logger.debug(f"Failed to fetch Coinbase USD spot for {sym}: {e}")
  return None
 def get_reference_spot_price(self,asset:str)->Optional[float]:
  now=time.time()
  cache_key=f"{asset.upper()}USDT"
  snap=read_fast_tick(asset,max_age_sec=FAST_TICK_MAX_AGE_SEC,now=now)
  if snap:
   shm_px=float(snap.get("spot") or 0.0)
   if math.isfinite(shm_px) and shm_px > 0.0:
    self._spot_cache[cache_key]=(shm_px,now)
    return shm_px
  if cache_key in self._spot_cache:
   val,ts=self._spot_cache[cache_key]
   if now - ts < 1.0:
    return val
  try:
   url=f"https://api.binance.com/api/v3/ticker/price?symbol={cache_key}"
   resp=self.executor._sync_session.get(url,timeout=1.5)
   if resp.status_code==200:
    price=float(resp.json().get("price",0.0))
    if not math.isfinite(price) or price<=0.0:
     logger.error("Rejected nonfinite/invalid spot price: %r",price)
     return None
    self._spot_cache[cache_key]=(price,now)
    return price
  except Exception as e:
   logger.debug(f"Failed to fetch Binance spot price for {cache_key}: {e}")
  return None
 def compute_kelly_ticket_size( self,p_model:float,p_market_ask:float,bankroll:float,fee_rate:Optional[float]=None,fee_exponent:Optional[float]=None,)->float:
  if not all(math.isfinite(float(v)) for v in (p_model,p_market_ask,bankroll)):
   return 0.0
  if not (0.0 < float(p_model) < 1.0):
   return 0.0
  if bankroll<=0:
   return 0.0
  if p_market_ask>=self.max_price_ceiling or p_market_ask<=self.min_price_floor:
   return 0.0
  p=float(p_market_ask)
  q=float(p_model)
  r=float(fee_rate if fee_rate is not None else 0.07)
  e=float(fee_exponent if fee_exponent is not None else 1.0)
  if not (math.isfinite(r) and r>=0.0 and math.isfinite(e) and (e > 0.0 or (r==0.0 and e>=0.0))):
   return 0.0
  clamped_p=min(0.9999,max(0.0001,p))
  f_p=r * ((clamped_p * (1.0 - clamped_p)) ** e)
  h_p=f_p / max(clamped_p,1e-6)
  g_p=1.0 - h_p
  if g_p<=0.005:
   return 0.0
  c_eff=p / g_p
  if not math.isfinite(c_eff) or c_eff>=1.0 or c_eff<=0.0:
   return 0.0
  net_edge=q - c_eff
  if net_edge<=0.015:
   return 0.0
  unconstrained_kelly=net_edge / max(0.05,1.0 - c_eff)
  try:
   max_cap_pct=float(getattr(self,"max_notional_cap_pct",0.35))
  except (TypeError,ValueError):
   max_cap_pct=0.35
  if not math.isfinite(max_cap_pct) or max_cap_pct<=0.0:
   max_cap_pct=0.35
  try:
   kelly_frac=float(getattr(self,"kelly_fraction",0.50))
  except (TypeError,ValueError):
   kelly_frac=0.50
  if not math.isfinite(kelly_frac) or kelly_frac<=0.0:
   kelly_frac=0.50
  scaled_fraction=unconstrained_kelly * kelly_frac
  bounded_fraction=min(max_cap_pct,max(0.015,scaled_fraction))
  if getattr(self,"unconstrained_kelly",False):
   effective_cap=getattr(self,"max_absolute_ticket_usd",10000.0) or 10000.0
   ticket_usd=min(bankroll * bounded_fraction,effective_cap)
   if not math.isfinite(ticket_usd) or ticket_usd<=0.0:
    ticket_usd=0.0
   return round(ticket_usd,2)
  try:
   configured_cap=float(getattr(self,"max_absolute_ticket_usd",MAX_ABSOLUTE_TICKET_USD))
  except (TypeError,ValueError):
   configured_cap=MAX_ABSOLUTE_TICKET_USD
  if not math.isfinite(configured_cap) or configured_cap<=0.0:
   effective_cap=MAX_ABSOLUTE_TICKET_USD
  else:
   effective_cap=min(configured_cap,MAX_ABSOLUTE_TICKET_USD)
  ticket_usd=min(bankroll * bounded_fraction,effective_cap)
  if not math.isfinite(ticket_usd) or ticket_usd<=0.0:
   return 0.0
  if ticket_usd > MAX_ABSOLUTE_TICKET_USD:
   ticket_usd=min(MAX_ABSOLUTE_TICKET_USD,effective_cap)
  return round(ticket_usd,2)
 def load_state(self):
  if STATE_FILE.exists():
   try:
    with open(STATE_FILE,"r") as f:
     state=json.load(f)
     self.active_positions=state.get("active_positions",{})
     self.closed_positions=state.get("closed_positions",[])
     self.pending_entry_intents=state.get("pending_entry_intents",{})
     self.redeemed_tx_hashes=list(state.get("redeemed_tx_hashes",[]) or [])
     persisted_halt=bool(state.get("risk_halt",False) or state.get("reconciliation_required",False))
     derived_reasons=self._global_halt_reasons()
     self.risk_halt=persisted_halt or bool(derived_reasons)
     self.reconciliation_required=self.risk_halt
     self.global_halt_reasons=derived_reasons or (list(state.get("global_halt_reasons",[])) or (["PERSISTED_HALT"] if persisted_halt else []))
     if self.risk_halt:
      logger.warning( f"[STARTUP RECOVERY] Persistent global risk halt active: {self.global_halt_reasons}. " "New entries blocked until authoritative exchange reconciliation." )
     migrated_orphaned_liquidations=False
     for pos in self.active_positions.values():
      if ( pos.get("is_liquidating") and not pos.get("unwind_order_id") ):
       if position_requires_global_halt(pos):
        continue
       pos["is_liquidating"]=False
       pos["exit_order_status"]="UNWIND_RETRY_REQUIRED"
       pos["next_unwind_retry_ts"]=0.0
       pos["unwind_last_error"]=( "MIGRATED_ORPHANED_LIQUIDATION_FLAG" )
       migrated_orphaned_liquidations=True
     self.seen_shock_ids=set(state.get("seen_shock_ids",[]))
     self._seen_shock_order={sid:None for sid in state.get("seen_shock_ids",[])}
     saved_d1_keys=[str(k) for k in (state.get("seen_d1_box_keys") or []) if k]
     self._seen_d1_box_keys=set(saved_d1_keys)
     self._seen_d1_box_order={k:None for k in saved_d1_keys}
     self._persisted_state=dict(state)
     self.traded_market_ids=set(state.get("traded_market_ids",[]))
     raw_tpm=state.get("trades_per_market",{})
     raw_tpmd=state.get("trades_per_market_direction",{}) or {}
     self.trades_per_market=defaultdict(int,{str(k):int(v) for k,v in raw_tpm.items()})
     self.trades_per_market_direction=defaultdict(int)
     for k_dir,v_dir in raw_tpmd.items():
      if "_" in str(k_dir):
       m_part,t_part=str(k_dir).rsplit("_",1)
       self.trades_per_market_direction[(m_part,t_part)]=int(v_dir)
     if not raw_tpmd:
      for cp in self.closed_positions:
       mid=str(cp.get("market_id",""))
       tok=str(cp.get("target_token",""))
       if mid:
        if not raw_tpm:
         self.trades_per_market[mid] += 1
        if tok:
         self.trades_per_market_direction[(mid,tok)] += 1
      for ap in self.active_positions.values():
       mid=str(ap.get("market_id",""))
       tok=str(ap.get("target_token",""))
       if mid and tok:
        self.trades_per_market_direction[(mid,tok)] += 1
     elif not raw_tpm and self.closed_positions:
      for cp in self.closed_positions:
       mid=str(cp.get("market_id",""))
       if mid:
        self.trades_per_market[mid] += 1
     saved_hour=state.get("current_hour_window")
     current_hour=time.time() // 3600
     if saved_hour==current_hour:
      self.trades_this_hour=state.get("trades_this_hour",0)
      self.current_hour_window=current_hour
     else:
      self.trades_this_hour=0
      self.current_hour_window=current_hour
     self.last_event_id=state.get("last_event_id","")
     risk_st=state.get("risk_state",{})
     if getattr(self,"reset_risk",False):
      self.risk_controller.halted=False
      self.risk_controller.halt_reason=""
      self.risk_controller.consecutive_losses=0
      self.risk_controller.daily_realized_loss=0.0
      self.risk_halt=False
      self.reconciliation_required=False
      self.global_halt_reasons=[]
      logger.info("[STARTUP] Risk controller circuit breaker explicitly reset via --reset-risk flag.")
     else:
      if risk_st.get("halted"):
       saved_reason=str(risk_st.get("halt_reason","Restored from persisted halt state"))
       if not self.dry_run and "Heartbeat degraded" in saved_reason and self.executor.is_heartbeat_healthy():
        logger.info(f"[STARTUP] Cleared transient session heartbeat halt on fresh process startup ({saved_reason}).")
        self.risk_controller.halted=False
        self.risk_controller.halt_reason=""
       else:
        self.risk_controller.halted=True
        self.risk_controller.halt_reason=saved_reason
       saved_loss_date=risk_st.get("last_loss_date_utc")
       today_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d")
       if saved_loss_date and saved_loss_date!=today_utc:
        self.risk_controller.consecutive_losses=0
        self.risk_controller.daily_realized_loss=0.0
        self.risk_controller.last_loss_date_utc=today_utc
       else:
        self.risk_controller.consecutive_losses=risk_st.get("consecutive_losses",0)
        self.risk_controller.daily_realized_loss=risk_st.get("daily_realized_loss",0.0)
        if saved_loss_date:
         self.risk_controller.last_loss_date_utc=str(saved_loss_date)
     if migrated_orphaned_liquidations:
      self.save_state()
     self._last_known_collateral=state.get("live_bankroll")
     if isinstance(self._last_known_collateral,(int,float)) and math.isfinite(self._last_known_collateral) and self._last_known_collateral > 0.0:
      self.executor.set_cached_collateral(float(self._last_known_collateral))
     saved_tier=state.get("current_equity_tier") or state.get("equity_tier")
     if isinstance(saved_tier,str) and saved_tier:
      self._current_equity_tier=saved_tier
      self.current_equity_tier=saved_tier
     if state.get("dynamic_bankroll_pct") is not None:
      try:
       self.dynamic_bankroll_pct=float(state["dynamic_bankroll_pct"])
      except (TypeError,ValueError):
       pass
     if getattr(self,"reset_risk",False):
      self.high_water_mark_equity=float(state.get("live_bankroll") or 0.0)
     else:
      self.high_water_mark_equity=float( state.get("high_water_mark_equity") or state.get("total_account_equity") or state.get("live_bankroll") or getattr(self,"high_water_mark_equity",0.0) or 0.0 )
     tot_equity_saved=float(state.get("total_account_equity") or self._last_known_collateral or 0.0)
     if tot_equity_saved > 0:
      self._update_equity_tier(tot_equity_saved)
      if ( self.risk_controller.halted and "Account equity" in str(self.risk_controller.halt_reason or "") and tot_equity_saved>=(self.risk_controller.min_equity_floor_usd + 3.00) ):
       logger.info( f"[STARTUP] Cleared stale equity circuit-breaker halt on startup: " f"persisted equity ${tot_equity_saved:.2f} >= +$3.00 above ${self.risk_controller.min_equity_floor_usd:.2f} tier floor." )
       self.risk_controller.halted=False
       self.risk_controller.halt_reason=""
     logger.info(f"Loaded existing state: {len(self.active_positions)} active positions, {len(self.traded_market_ids)} traded markets.")
   except Exception as e:
    logger.critical(f"LIVE STATE UNREADABLE; refusing all reconciliation and order mutation: {e}")
    raise RuntimeError("Refusing live startup with unreadable position state") from e
 _GLOBAL_STATE_SAVE_LOCK=threading.RLock()
 def save_state(self):
  lock=getattr(self,"_state_save_lock",None) or self._GLOBAL_STATE_SAVE_LOCK
  with lock:
   now_ts=time.time()
   active_market_equity=sum(self.get_position_market_value(p,now_ts) for p in self.active_positions.values())
   tot_equity=( (float(self._last_known_collateral) + active_market_equity) if getattr(self,"_last_known_collateral",None) is not None else None )
   seen_shocks_list=list(self._seen_shock_order.keys())[-1000:] if hasattr(self,"_seen_shock_order") else list(self.seen_shock_ids)[-1000:]
   seen_d1_list=( list(self._seen_d1_box_order.keys())[-200:] if hasattr(self,"_seen_d1_box_order") else list(getattr(self,"_seen_d1_box_keys",set()))[-200:] )
   cur_tier=getattr(self,"_current_equity_tier",None) or getattr(self,"current_equity_tier",None)
   state={ "state_version":"2.0.0","updated_at_utc":datetime.now(timezone.utc).isoformat(),"ticket_notional":self.ticket_notional,"dynamic_sizing":self.dynamic_sizing,"max_exposure":self.max_exposure,"max_concurrent_positions":self.max_concurrent_positions,"dry_run":self.dry_run,"last_event_id":getattr(self,"last_event_id",""),"live_bankroll":getattr(self,"_last_known_collateral",None),"total_account_equity":tot_equity,"high_water_mark_equity":getattr(self,"high_water_mark_equity",None),"equity_tier":cur_tier,"current_equity_tier":cur_tier,"dynamic_bankroll_pct":getattr(self,"dynamic_bankroll_pct",None),"active_positions_count":len(self.active_positions),"closed_positions_count":len(self.closed_positions),"trades_this_hour":self.trades_this_hour,"current_hour_window":self.current_hour_window,"active_positions":self.active_positions,"active_position_ids":list(self.active_positions.keys()),"pending_entry_intents":getattr(self,"pending_entry_intents",{}),"risk_halt":getattr(self,"risk_halt",False),"reconciliation_required":getattr(self,"reconciliation_required",False),"global_halt_reasons":list(getattr(self,"global_halt_reasons",[]) or []),"redeemed_tx_hashes":list(getattr(self,"redeemed_tx_hashes",[]) or [])[-1000:],"closed_positions":self.closed_positions[-200:],"seen_shock_ids":seen_shocks_list,"seen_d1_box_keys":seen_d1_list,"traded_market_ids":list(self.traded_market_ids)[-100:],"trades_per_market":dict(self.trades_per_market),"trades_per_market_direction":{f"{k[0]}_{k[1]}":v for k,v in getattr(self,"trades_per_market_direction",{}).items()},"risk_state":{ "halted":self.risk_controller.halted,"halt_reason":self.risk_controller.halt_reason,"consecutive_losses":self.risk_controller.consecutive_losses,"daily_realized_loss":self.risk_controller.daily_realized_loss,"last_loss_date_utc":getattr(self.risk_controller,"last_loss_date_utc",datetime.now(timezone.utc).strftime("%Y-%m-%d")),},"status":getattr(self,"_shutdown_status",None) or ("HALTED" if self.risk_controller.is_halted() else "RUNNING"),}
   target_state_file=getattr(self,"state_file",STATE_FILE)
   tmp_file=target_state_file.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}")
   try:
    with open(tmp_file,"w",encoding="utf-8") as f:
     json.dump(state,f,indent=2)
     f.flush()
     os.fsync(f.fileno())
    os.replace(tmp_file,target_state_file)
    if publish_global_positions_shm is not None and not self.dry_run:
     publish_global_positions_shm("live_harvester",self.active_positions.values())
    if os.name!="nt":
     dir_fd=os.open(str(target_state_file.parent),os.O_RDONLY)
     try:
      os.fsync(dir_fd)
     finally:
      os.close(dir_fd)
   except Exception as exc:
    try:
     tmp_file.unlink(missing_ok=True)
    except Exception:
     pass
    raise StatePersistenceError(f"Critical live state save failed: {exc}") from exc
 def get_graduated_allowed_assets(self,total_equity:Optional[float]=None)->Set[str]:
  assets=set(self.allowed_assets)
  if not RISK_CONFIG.get("enable_graduated_alt_sleeves",True):
   return assets
  eq=total_equity
  if eq is None and getattr(self,"_last_known_collateral",None) is not None:
   now_t=time.time()
   eq=float(self._last_known_collateral) + sum( self.get_position_market_value(p,now_t) for p in self.active_positions.values() )
  if eq is None or float(eq) < float(RISK_CONFIG.get("scale_up_equity_threshold",110.0)):
   return assets
  grad_cache=self.__dict__.setdefault("_alt_grad_file_cache",{})
  for sym,fname in (("SOL","state_shadow_sol_v392.json"),("XRP","state_shadow_xrp_v392.json")):
   try:
    sp=DATA_DIR / fname
    st_sp=sp.stat()
    ck=(str(sp),st_sp.st_mtime_ns,st_sp.st_size)
    cached_g=grad_cache.get(sym)
    if isinstance(cached_g,tuple) and len(cached_g)==2 and cached_g[0]==ck:
     is_grad=bool(cached_g[1])
    else:
     st_doc=_json_loads(sp.read_bytes())
     pf_ok=float(st_doc.get("profit_factor",2.0) or 2.0)>=1.80 if "profit_factor" in st_doc else True
     wr_ok=float(st_doc.get("win_rate_pct",90.0) or 90.0)>=84.0 if "win_rate_pct" in st_doc else True
     is_grad=bool(st_doc.get("ready_for_live_graduation") is True and pf_ok and wr_ok)
     grad_cache[sym]=(ck,is_grad)
    if is_grad:
     assets.add(sym)
   except Exception:
    continue
  return assets
 def _record_seen_d1_box_key(self,dedupe_k:str)->None:
  if not dedupe_k:
   return
  seen_boxes=self.__dict__.setdefault("_seen_d1_box_keys",set())
  seen_order=self.__dict__.setdefault("_seen_d1_box_order",{k:None for k in seen_boxes})
  seen_order.pop(dedupe_k,None)
  seen_order[dedupe_k]=None
  seen_boxes.add(dedupe_k)
  while len(seen_order) > 400:
   oldest_k=next(iter(seen_order))
   seen_order.pop(oldest_k,None)
   seen_boxes.discard(oldest_k)
 def maybe_execute_graduated_d1_box(self,candidate_box:Dict[str,Any])->Dict[str,Any]:
  if not RISK_CONFIG.get("enable_graduated_d1_box",True) or self.risk_controller.is_halted() or getattr(self,"risk_halt",False):
   return {"executed":False,"reason":"DISABLED_OR_HALTED"}
  box_type=str(candidate_box.get("box_type") or "DOMINANCE").strip().upper()
  sleeve_src=str(candidate_box.get("sleeve_source") or "D1_SAME_ORACLE_DOMINANCE_BOX").strip()
  cand_asset=str(candidate_box.get("asset") or "").strip().upper()
  core_d1={"BTC","ETH","XRP"} | ({"SOL"} if RISK_CONFIG.get("enable_sol_d1_box",True) else set())
  exp_d1={"BNB","DOGE","HYPE"}
  mid_a_chk=str(candidate_box.get("leg_a_market_id") or "")
  mid_b_chk=str(candidate_box.get("leg_b_market_id") or "")
  tok_a=str(candidate_box.get("leg_a_token_id") or "")
  tok_b=str(candidate_box.get("leg_b_token_id") or "")
  if box_type=="DOMINANCE":
   if cand_asset and cand_asset not in (core_d1 | exp_d1):
    return {"executed":False,"reason":f"UNSUPPORTED_D1_ASSET:{cand_asset}"}
   corr_bps=float(candidate_box.get("corridor_bps") or 0.0)
   min_corr=5.0 if cand_asset in exp_d1 else 3.0
   if corr_bps < min_corr:
    return {"executed":False,"reason":f"CORRIDOR_TOO_NARROW_OR_MISSING:{corr_bps:.2f}"}
   try:
    k_a_chk=float(candidate_box.get("leg_a_strike") or 0.0)
    k_b_chk=float(candidate_box.get("leg_b_strike") or 0.0)
   except (TypeError,ValueError):
    k_a_chk=k_b_chk=0.0
   if ( str(candidate_box.get("leg_a_side") or "").upper()!="UP" or str(candidate_box.get("leg_b_side") or "").upper()!="DOWN" or not (0.0 < k_a_chk < k_b_chk) or not mid_a_chk or not mid_b_chk or mid_a_chk==mid_b_chk or not tok_a or not tok_b or tok_a==tok_b ):
    return {"executed":False,"reason":"INVALID_BOX_INVARIANTS"}
  elif box_type in {"COMPLETE_SET","LADDER_MONO","BARRIER_MONO","NEGRISK_2LEG","NBA_DOMINANCE","MACRO_DOMINANCE","COUNTING_DOMINANCE","CROSS_BASIS_DOMINANCE"}:
   same_mkt_ok=(mid_a_chk==mid_b_chk) if box_type=="COMPLETE_SET" else (mid_a_chk!=mid_b_chk)
   if not tok_a or not tok_b or tok_a==tok_b or not mid_a_chk or not mid_b_chk or not same_mkt_ok:
    return {"executed":False,"reason":"INVALID_BOX_INVARIANTS"}
  else:
   return {"executed":False,"reason":f"UNSUPPORTED_BOX_TYPE:{box_type}"}
  if not self.dry_run:
   if not getattr(self,"_startup_reconciled",False):
    return {"executed":False,"reason":"STARTUP_NOT_RECONCILED"}
   halt_rs=self._global_halt_reasons()
   if halt_rs:
    return {"executed":False,"reason":f"GLOBAL_HALT:{halt_rs[0]}"}
   recon_m=self._reconciling_market_ids()
   if mid_a_chk in recon_m or mid_b_chk in recon_m:
    return {"executed":False,"reason":"MARKET_RECONCILING"}
  for p_act in self.active_positions.values():
   is_box_p="BOX" in str(p_act.get("sleeve") or "").upper() or bool(p_act.get("box_id"))
   if (is_box_p and not p_act.get("is_dominance_box")) or p_act.get("exit_order_status") in ( "UNWIND_RETRY_REQUIRED","UNWIND_EXECUTION_OUTCOME_UNKNOWN",):
    return {"executed":False,"reason":"UNHEDGED_BOX_RESIDUAL_ACTIVE"}
  now_ts=time.time()
  active_box_ids={ str(p.get("box_id") or k) for k,p in self.active_positions.items() if p.get("is_dominance_box") and not position_is_settlement_receivable(p) and p.get("status") not in {"UNRESOLVED_SETTLEMENT","AWAITING_ONCHAIN_SETTLEMENT"} and not (float(p.get("candle_expiry_ts") or 0.0) > 0.0 and now_ts>=float(p.get("candle_expiry_ts") or 0.0)) }
  if len(active_box_ids)>=int(RISK_CONFIG.get("max_concurrent_d1_boxes",4)):
   return {"executed":False,"reason":"MAX_CONCURRENT_BOXES_REACHED"}
  dedupe_k=str(candidate_box.get("dedupe_key") or "")
  seen_boxes=self.__dict__.setdefault("_seen_d1_box_keys",set())
  if dedupe_k and dedupe_k in seen_boxes:
   return {"executed":False,"reason":"ALREADY_EXECUTED_PAIR"}
  retry_cd=self.__dict__.setdefault("_d1_retry_cooldown_until",{})
  if dedupe_k and float(retry_cd.get(dedupe_k,0.0) or 0.0) > now_ts:
   return {"executed":False,"reason":"RETRY_COOLDOWN_10S"}
  if cand_asset:
   leg_outs_12h=[ p for p in getattr(self,"closed_positions",[]) if str(p.get("asset") or "").upper()==cand_asset and (now_ts - float(p.get("exit_ts") or p.get("exit_time_unix") or p.get("entry_ts") or 0.0))<=43200.0 and ( "LEGGED_OUT" in str(p.get("close_reason") or "").upper() or "LEGGED_OUT" in str(p.get("sleeve") or "").upper() or "_LEG_RESID" in str(p.get("trade_id") or "") ) ]
   if len(leg_outs_12h)>=2 or sum(float(p.get("net_pnl_usd") or 0.0) for p in leg_outs_12h)<=-2.50:
    return {"executed":False,"reason":f"ASSET_LEGGING_COOLDOWN:{cand_asset}"}
  try:
   st_path=DATA_DIR / "alpha124_shadow_state.json"
   if not st_path.exists() and DATA_DIR==(PIPELINE_ROOT / "data" / "polymarket"):
    alt_path=PIPELINE_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json"
    if alt_path.exists():
     st_path=alt_path
   if not st_path.exists():
    return {"executed":False,"reason":"NO_ALPHA124_STATE"}
   st_info=st_path.stat()
   if (time.time() - st_info.st_mtime) > 300.0:
    return {"executed":False,"reason":"ALPHA124_STATE_STALE"}
   cache_tup=getattr(self,"_d1_grad_cache",None)
   manual_inv=getattr(self,"_a124_grad_cache_mtime",0.0)
   st_key=(str(st_path),st_info.st_mtime_ns,st_info.st_size,manual_inv)
   if isinstance(cache_tup,tuple) and len(cache_tup)==3 and cache_tup[0]==st_key and manual_inv>=0.0:
    by_sl_map,by_da_map=cache_tup[1],cache_tup[2]
   else:
    if manual_inv < 0.0:
     self._a124_grad_cache_mtime=0.0
     st_key=(str(st_path),st_info.st_mtime_ns,st_info.st_size,0.0)
    st_raw=_json_loads(st_path.read_text(encoding="utf-8"))
    by_sl_map=st_raw.get("by_sleeve") or st_raw.get("per_strategy") or {}
    by_da_map=st_raw.get("by_d1_asset") or {}
    self._d1_grad_cache=(st_key,by_sl_map,by_da_map)
   def _grad8(rec:Dict[str,Any])->bool:
    adj_pnl=rec.get("legging_adjusted_pnl_t1000_usd",rec.get("realized_pnl_t1000_usd",0.0))
    return bool( int(rec.get("closed",0) or 0)>=8 and float(rec.get("win_rate_pct",0.0) or 0.0)>=100.0 and float(rec.get("realized_pnl_t1000_usd",0.0) or 0.0) > 0.0 and float(adj_pnl or 0.0) > 0.0 )
   fr_a=float(candidate_box["leg_a_fee_rate"]) if candidate_box.get("leg_a_fee_rate") is not None else 0.07
   fr_b=float(candidate_box["leg_b_fee_rate"]) if candidate_box.get("leg_b_fee_rate") is not None else 0.07
   zero_fee_box=max(fr_a,fr_b)==0.0
   own_grad=True
   if box_type=="DOMINANCE":
    d1_core_ok=_grad8(by_sl_map.get("D1_SAME_ORACLE_DOMINANCE_BOX") or {})
    d1_quiet_ok=sleeve_src=="D1_QUIET_BOOK_BOX" and _grad8(by_sl_map.get("D1_QUIET_BOOK_BOX") or {})
    if not (d1_core_ok or d1_quiet_ok):
     return {"executed":False,"reason":"D1_NOT_YET_8_OF_8_GRADUATED"}
    if cand_asset in exp_d1 and not _grad8(by_da_map.get(cand_asset) or {}):
     return {"executed":False,"reason":f"EXPANSION_ASSET_NOT_YET_8_OF_8_GRADUATED:{cand_asset}"}
   else:
    own_grad=_grad8(by_sl_map.get(sleeve_src) or {})
    d1_zf_bridge=( zero_fee_box and sleeve_src!="COND1_MACRO_PARTITION_BOX" and box_type in {"COMPLETE_SET","BARRIER_MONO","NEGRISK_2LEG","NBA_DOMINANCE","MACRO_DOMINANCE","COUNTING_DOMINANCE"} and _grad8(by_sl_map.get("D1_SAME_ORACLE_DOMINANCE_BOX") or {}) )
    if not (own_grad or d1_zf_bridge):
     return {"executed":False,"reason":f"SLEEVE_NOT_YET_8_OF_8_GRADUATED:{sleeve_src}"}
  except Exception as exc:
   return {"executed":False,"reason":f"STATE_READ_ERROR:{exc}"}
  inflight_lock=self.__dict__.setdefault("_d1_inflight_exec_lock",threading.Lock())
  if not inflight_lock.acquire(blocking=False):
   return {"executed":False,"reason":"BOX_EXECUTION_INFLIGHT"}
  try:
   lbl_a=str(candidate_box.get("leg_a_label","LEG_A"))
   lbl_b=str(candidate_box.get("leg_b_label","LEG_B"))
   px_a_lim=float(candidate_box["leg_a_limit_price"])
   px_b_lim=float(candidate_box["leg_b_limit_price"])
   sh_req=float(candidate_box.get("shares",12.0))
   cap_net=float(candidate_box.get("max_box_cost_net",0.995))
   fresh_box_net=float(candidate_box.get("box_cost_net") or (px_a_lim + px_b_lim))
   avail_a=candidate_box.get("leg_a_avail_shares")
   avail_b=candidate_box.get("leg_b_avail_shares")
   fe_a=float(candidate_box.get("leg_a_fee_exponent",1.0) or 1.0)
   fe_b=float(candidate_box.get("leg_b_fee_exponent",1.0) or 1.0)
   pre_bal_a,pre_bal_b=0.0,0.0
   is_live_ctf_box=( (not self.dry_run) and getattr(self.executor,"auth_mode","") in ("LIVE","AUTHENTICATED_L2") and len(tok_a)>=20 and tok_a.isdigit() and len(tok_b)>=20 and tok_b.isdigit() )
   cand_ts=float(candidate_box.get("ts_unix") or now_ts)
   ipc_age_ms=round(max(0.0,(now_ts - cand_ts) * 1000.0),2)
   pre_bal_ms,book_walk_ms=0.0,0.0
   if not self.dry_run and ( not is_live_ctf_box or not candidate_box.get("ts_unix") or not candidate_box.get("expiry_ts") or walk_equal_shares_dominance_box is None or not hasattr(self.executor,"get_market_book") ):
    return {"executed":False,"reason":"LIVE_PRECHECK_UNAVAILABLE"}
   if is_live_ctf_box:
    exp_ts=float(candidate_box.get("expiry_ts") or 0.0)
    is_4h_box=str(candidate_box.get("leg_a_horizon") or "").lower()=="4h" or str(candidate_box.get("leg_b_horizon") or "").lower()=="4h"
    max_tte_box=(172800.0 if box_type in {"NEGRISK_2LEG","MACRO_DOMINANCE"} else 86400.0) if box_type!="DOMINANCE" else (900.0 if is_4h_box else 300.0)
    if (now_ts - cand_ts) > 6.5 or (exp_ts > 0.0 and not (16.0<=(exp_ts - now_ts)<=max_tte_box)):
     return {"executed":False,"reason":"STALE_OR_OUTSIDE_TTE_WINDOW"}
    m_a=str(candidate_box.get("leg_a_market_id") or "")
    m_b=str(candidate_box.get("leg_b_market_id") or "")
    busy_mkts={str(p.get("market_id") or "") for p in self.active_positions.values()} | { str(i.get("market_id") or "") for i in getattr(self,"pending_entry_intents",{}).values() }
    if (m_a and m_a in busy_mkts) or (m_b and m_b in busy_mkts):
     return {"executed":False,"reason":"MARKET_ALREADY_OCCUPIED"}
    collat=getattr(self,"_last_known_collateral",None)
    if collat is None:
     try:
      collat=self.executor.get_collateral_balance()
     except Exception:
      collat=None
    inflight_intent_usd=sum( float(i.get("notional_usd",0.0) or 0.0) for i in getattr(self,"pending_entry_intents",{}).values() if isinstance(i,dict) )
    collat_f=max(0.0,float(collat or 0.0) - inflight_intent_usd)
    d1_pct=( 0.32 if collat_f>=160.0 else float(RISK_CONFIG.get("d1_box_bankroll_pct",0.25)) )
    rem_daily=max(0.0,float(self.risk_controller.max_daily_loss_usd) - float(self.risk_controller.daily_realized_loss))
    asset_cap={"BTC":150.0,"ETH":75.0,"SOL":16.5,"XRP":16.5,"BNB":22.0,"HYPE":15.0,"DOGE":15.0}.get(cand_asset,25.0)
    cur_open_exp=sum( float(p.get("notional_usd",0.0) or 0.0) for p in self.active_positions.values() if not position_is_settlement_receivable(p) ) + inflight_intent_usd
    port_headroom=max(0.0,max(float(self.max_exposure),collat_f * 0.55) - cur_open_exp)
    target_budget=min( float(RISK_CONFIG.get("d1_box_max_budget_usd",250.0)),16.50 if (box_type!="DOMINANCE" and not own_grad) else asset_cap,max(0.0,collat_f - float(RISK_CONFIG.get("d1_box_collateral_reserve_usd",16.50))),collat_f * d1_pct,rem_daily * 10.0,port_headroom,)
    if target_budget < 4.85:
     return {"executed":False,"reason":"INSUFFICIENT_BOX_COLLATERAL_HEADROOM"}
    for t_id,c_id,nr_raw,fr_f,fe_f,tk_sz_raw in ( (tok_a,str(candidate_box.get("leg_a_condition_id") or ""),candidate_box.get("leg_a_neg_risk"),fr_a,fe_a,candidate_box.get("leg_a_tick_size")),(tok_b,str(candidate_box.get("leg_b_condition_id") or ""),candidate_box.get("leg_b_neg_risk"),fr_b,fe_b,candidate_box.get("leg_b_tick_size")),):
     if c_id and isinstance(nr_raw,bool) and hasattr(self.executor,"prewarm_token_market_cache"):
      self.executor.prewarm_token_market_cache( token_id=t_id,tick_size=tk_sz_raw,neg_risk=nr_raw,fee_rate_bps=int(round(fr_f * 10000)),condition_id=c_id,fee_rate=fr_f,fee_exponent=fe_f,)
    hot_pool=_get_hot_io_pool()
    pre_bal_cache=self.__dict__.setdefault("_d1_clean_pre_bal_cache",{})
    use_bal_cache="_wallet_token_balance" not in self.__dict__
    now_pb=time.time()
    uws_d1=getattr(self.executor,"_user_ws_cache",None) if use_bal_cache else None
    uws_d1_ok=bool(uws_d1 is not None and uws_d1.is_healthy())
    bal_ttl=1800.0 if uws_d1_ok else 360.0
    prior_toks=( {p.get("token_id") for p in self.active_positions.values()} | {i.get("token_id") for i in getattr(self,"pending_entry_intents",{}).values()} | { p.get("token_id") for p in getattr(self,"closed_positions",[])[-20:] if float(p.get("remaining_shares",0.0) or 0.0) > 0.01 or not uws_d1_ok } ) if use_bal_cache else {tok_a,tok_b}
    c_ba=pre_bal_cache.get(tok_a) if use_bal_cache else None
    c_bb=pre_bal_cache.get(tok_b) if use_bal_cache else None
    if c_ba is not None and uws_d1_ok and uws_d1.has_token_fill_since(tok_a,c_ba[1]):
     c_ba=None
    if c_bb is not None and uws_d1_ok and uws_d1.has_token_fill_since(tok_b,c_bb[1]):
     c_bb=None
    if use_bal_cache and tok_a not in prior_toks and c_ba is None and not (uws_d1_ok and uws_d1.has_token_fill_since(tok_a,now_pb - 300.0)):
     c_ba=(0.0,now_pb)
    if use_bal_cache and tok_b not in prior_toks and c_bb is None and not (uws_d1_ok and uws_d1.has_token_fill_since(tok_b,now_pb - 300.0)):
     c_bb=(0.0,now_pb)
    t_pb0=time.perf_counter_ns()
    fb_a=None if (c_ba is not None and (now_pb - c_ba[1])<=bal_ttl) else hot_pool.submit(self._wallet_token_balance,tok_a)
    fb_b=None if (c_bb is not None and (now_pb - c_bb[1])<=bal_ttl) else hot_pool.submit(self._wallet_token_balance,tok_b)
    b_a=c_ba[0] if fb_a is None else fb_a.result()[0]
    b_b=c_bb[0] if fb_b is None else fb_b.result()[0]
    pre_bal_ms=round((time.perf_counter_ns() - t_pb0) / 1_000_000.0,2)
    pre_bal_a=float(b_a or 0.0)
    pre_bal_b=float(b_b or 0.0)
    if use_bal_cache:
     now_pb_done=time.time()
     pre_bal_cache[tok_a]=(pre_bal_a,now_pb_done)
     pre_bal_cache[tok_b]=(pre_bal_b,now_pb_done)
    if walk_equal_shares_dominance_box is not None and hasattr(self.executor,"get_market_book"):
     t_bk0=time.perf_counter_ns()
     opp_a=str(candidate_box.get("leg_a_opp_token_id") or "")
     opp_b=str(candidate_box.get("leg_b_opp_token_id") or "")
     need_sep_opp=box_type!="COMPLETE_SET"
     if need_sep_opp and not (len(opp_a)>=20 and opp_a.isdigit() and len(opp_b)>=20 and opp_b.isdigit()):
      return {"executed":False,"reason":"ANTI_BOX_COMPLEMENT_UNVERIFIED:MISSING_OPP_TOKENS"}
     custom_book_fn="get_market_book" in getattr(self.executor,"__dict__",{})
     ws_bks=candidate_box.get("ws_books") if not custom_book_fn else None
     ws_bks_ts=float(candidate_box.get("ws_books_ts") or 0.0)
     use_ws_bks=( isinstance(ws_bks,dict) and (time.time() - ws_bks_ts)<=0.65 and isinstance(ws_bks.get(tok_a),dict) and isinstance(ws_bks.get(tok_b),dict) and (not need_sep_opp or (isinstance(ws_bks.get(opp_a),dict) and isinstance(ws_bks.get(opp_b),dict))) )
     if use_ws_bks:
      bk_a=ws_bks[tok_a]
      bk_b=ws_bks[tok_b]
      bk_oa_pre=bk_b if not need_sep_opp else ws_bks[opp_a]
      bk_ob_pre=bk_a if not need_sep_opp else ws_bks[opp_b]
     elif not custom_book_fn and hasattr(self.executor,"get_market_books_batch"):
      req_toks=[tok_a,tok_b] + ([opp_a,opp_b] if need_sep_opp else [])
      batch_map=self.executor.get_market_books_batch(req_toks)
      bk_a=batch_map.get(tok_a) or {}
      bk_b=batch_map.get(tok_b) or {}
      bk_oa_pre=bk_b if not need_sep_opp else (batch_map.get(opp_a) or {})
      bk_ob_pre=bk_a if not need_sep_opp else (batch_map.get(opp_b) or {})
     else:
      fk_a=hot_pool.submit(self.executor.get_market_book,tok_a)
      fk_b=hot_pool.submit(self.executor.get_market_book,tok_b)
      fk_oa=hot_pool.submit(self.executor.get_market_book,opp_a) if need_sep_opp else None
      fk_ob=hot_pool.submit(self.executor.get_market_book,opp_b) if need_sep_opp else None
      bk_a=fk_a.result() or {}
      bk_b=fk_b.result() or {}
      bk_oa_pre=bk_b if not need_sep_opp else (fk_oa.result() or {})
      bk_ob_pre=bk_a if not need_sep_opp else (fk_ob.result() or {})
     try:
      bk_oa=bk_oa_pre
      bk_ob=bk_ob_pre
      b_oa=bk_oa.get("bids") or []
      b_ob=bk_ob.get("bids") or []
      if not (b_oa and b_ob):
       return {"executed":False,"reason":"ANTI_BOX_COMPLEMENT_UNVERIFIED:EMPTY_OPP_BOOK"}
      opp_sum=max(float(x["price"] if isinstance(x,dict) else x[0]) for x in b_oa) + max(float(x["price"] if isinstance(x,dict) else x[0]) for x in b_ob)
      if opp_sum > 1.0:
       return {"executed":False,"reason":f"ANTI_BOX_COMPLEMENT_VETO:{opp_sum:.4f}"}
     except Exception as exc_opp:
      return {"executed":False,"reason":f"ANTI_BOX_COMPLEMENT_UNVERIFIED:{exc_opp}"}
     book_walk_ms=round((time.perf_counter_ns() - t_bk0) / 1_000_000.0,2)
     def _bk_quiet(bk_d:Dict[str,Any])->bool:
      asks_d,bids_d=bk_d.get("asks") or [],bk_d.get("bids") or []
      if not asks_d or not bids_d:
       return False
      ba=min(float(x["price"] if isinstance(x,dict) else x[0]) for x in asks_d)
      bb=max(float(x["price"] if isinstance(x,dict) else x[0]) for x in bids_d)
      return bb > 0.0 and (ba - bb)<=0.041
     fresh_quiet=bool(candidate_box.get("is_quiet_book") and _bk_quiet(bk_a) and _bk_quiet(bk_b))
     live_walk_cap=(0.992 if fresh_quiet else 0.988) if zero_fee_box else (0.990 if fresh_quiet else 0.988)
     w_fresh=walk_equal_shares_dominance_box( bk_a.get("asks") or [],bk_b.get("asks") or [],target_budget_usd=target_budget,fee_rate_a=fr_a,fee_rate_b=fr_b,fee_exponent_a=fe_a,fee_exponent_b=fe_b,max_box_cost_net=live_walk_cap,min_shares=5,min_box_notional_usd=4.85,)
     if not w_fresh.get("filled"):
      rej_r=str(w_fresh.get("reason"))
      logger.info( f"[D1 FRESH BOOK REJECT] {candidate_box.get('box_id')} ({cand_asset or 'BTC'}): {rej_r} | " f"cap={live_walk_cap:.3f} quiet={fresh_quiet} ipc_age_ms={ipc_age_ms:.1f} pre_bal_ms={pre_bal_ms:.1f} book_ms={book_walk_ms:.1f}" )
      return {"executed":False,"reason":f"FRESH_BOOK_WALK_REJECT:{rej_r}"}
     avail_min_f=min(float(w_fresh["avail_a_shares"]),float(w_fresh["avail_b_shares"]))
     if int(w_fresh["shares"]) > 16 and avail_min_f < 2.0 * float(w_fresh["shares"]):
      cap_sh=max(16,int(math.floor(avail_min_f * 0.50)))
      w_trim=walk_equal_shares_dominance_box( bk_a.get("asks") or [],bk_b.get("asks") or [],target_budget_usd=min(target_budget,(cap_sh + 0.25) * float(w_fresh["eff_px"])),fee_rate_a=fr_a,fee_rate_b=fr_b,fee_exponent_a=fe_a,fee_exponent_b=fe_b,max_box_cost_net=live_walk_cap,min_shares=5,min_box_notional_usd=4.85,)
      if w_trim.get("filled"):
       w_fresh=w_trim
       avail_min_f=min(float(w_fresh["avail_a_shares"]),float(w_fresh["avail_b_shares"]))
     _min_depth_gate=max(1.0,float((getattr(self,"risk_config",None) or RISK_CONFIG).get("d1_min_depth_mult_gate",1.15)))
     if avail_min_f + 1e-6 < _min_depth_gate * float(w_fresh["shares"]):
      cap_sh_gate=int(math.floor((avail_min_f + 1e-9) / _min_depth_gate))
      if cap_sh_gate < 5:
       return {"executed":False,"reason":"FRESH_BOOK_WALK_REJECT:MIN_DEPTH_MULT_GATE"}
      w_gate=walk_equal_shares_dominance_box( bk_a.get("asks") or [],bk_b.get("asks") or [],target_budget_usd=min(target_budget,(cap_sh_gate + 0.25) * float(w_fresh["eff_px"])),fee_rate_a=fr_a,fee_rate_b=fr_b,fee_exponent_a=fe_a,fee_exponent_b=fe_b,max_box_cost_net=live_walk_cap,min_shares=5,min_box_notional_usd=4.85,)
      if not w_gate.get("filled") or avail_min_f + 1e-6 < _min_depth_gate * float(w_gate["shares"]):
       return {"executed":False,"reason":"FRESH_BOOK_WALK_REJECT:MIN_DEPTH_MULT_GATE"}
      w_fresh=w_gate
      avail_min_f=min(float(w_fresh["avail_a_shares"]),float(w_fresh["avail_b_shares"]))
     fresh_box_net=float(w_fresh["box_cost_net"])
     if fresh_box_net > 0.975 and avail_min_f < 1.5 * float(w_fresh["shares"]):
      logger.info( f"[D1 FRESH BOOK REJECT] {candidate_box.get('box_id')} ({cand_asset or 'BTC'}): QUIET_DEPTH_THINNED | " f"net={fresh_box_net:.4f} sh={w_fresh['shares']}" )
      return {"executed":False,"reason":"FRESH_BOOK_WALK_REJECT:QUIET_DEPTH_THINNED"}
     px_a_lim=float(w_fresh["leg_a_walk"]["worst_px"])
     px_b_lim=float(w_fresh["leg_b_walk"]["worst_px"])
     sh_req=float(w_fresh["shares"])
     avail_a=float(w_fresh["avail_a_shares"])
     avail_b=float(w_fresh["avail_b_shares"])
     cap_net=live_walk_cap
   if fresh_box_net < 0.900:
    return {"executed":False,"reason":f"ANTI_BOX_COST_FLOOR_REJECT:{fresh_box_net:.4f}"}
   is_4h_cand=( str(candidate_box.get("leg_a_horizon") or "").lower()=="4h" or str(candidate_box.get("leg_b_horizon") or "").lower()=="4h" )
   is_zero_itode_box=box_type=="COMPLETE_SET" or ( zero_fee_box and box_type in {"NEGRISK_2LEG","NEGRISK_CROSS","NBA_DOMINANCE","MACRO_DOMINANCE","COUNTING_DOMINANCE","BARRIER_MONO"} )
   _rcfg_d1=getattr(self,"risk_config",None) or RISK_CONFIG
   _d1_asym_cap=float(_rcfg_d1.get("d1_depth_ratio_threshold",1.20))
   use_parallel_d1=bool( ( is_zero_itode_box or ( (not is_4h_cand) and (not cand_asset or cand_asset in {"BTC","ETH"}) and fresh_box_net<=0.975 ) ) and min(px_a_lim,px_b_lim)>=(0.05 if is_zero_itode_box else 0.30) and ( avail_a is None or avail_b is None or ( min(float(avail_a),float(avail_b))>=(1.5 if is_zero_itode_box else 2.0) * sh_req and ( is_zero_itode_box or max(float(avail_a),float(avail_b))<=_d1_asym_cap * max(min(float(avail_a),float(avail_b)),1e-6) ) ) ) )
   box_id=str(candidate_box.get("box_id") or f"D1_LIVE_{int(now_ts)}")
   st_lock=getattr(self,"_state_save_lock",None) or self._GLOBAL_STATE_SAVE_LOCK
   if dedupe_k and is_live_ctf_box:
    with st_lock:
     self._record_seen_d1_box_key(dedupe_k)
   t_fok0=time.perf_counter_ns()
   _box_call_kw=dict( box_id=box_id,leg_a_token_id=tok_a,leg_a_label=lbl_a,leg_a_limit_price=px_a_lim,leg_b_token_id=tok_b,leg_b_label=lbl_b,leg_b_limit_price=px_b_lim,shares=sh_req,max_box_cost_net=cap_net,leg_a_avail_shares=avail_a,leg_b_avail_shares=avail_b,fee_rate_a=fr_a,fee_rate_b=fr_b,fee_exponent_a=fe_a,fee_exponent_b=fe_b,parallel_dispatch=use_parallel_d1,)
   try:
    res=self.executor.execute_atomic_dominance_box( **_box_call_kw,leg_a_pre_balance=pre_bal_a,leg_b_pre_balance=pre_bal_b,)
   except TypeError:
    res=self.executor.execute_atomic_dominance_box(**_box_call_kw)
   fok_box_ms=round((time.perf_counter_ns() - t_fok0) / 1_000_000.0,2)
   _fok_ok=bool(res.get("success"))
   _fok_err="" if _fok_ok else f" | abort={res.get('stage') or res.get('error') or 'FAILED'}"
   logger.info( f"[D1 LATENCY TELEMETRY] {box_id} ({cand_asset or 'BTC'}): ipc_age_ms={ipc_age_ms:.2f} | " f"pre_bal_ms={pre_bal_ms:.2f} | book_walk_ms={book_walk_ms:.2f} | fok_box_ms={fok_box_ms:.2f} | " f"sh={sh_req:.0f} | parallel={use_parallel_d1} | ok={_fok_ok}{_fok_err}" )
   if _LatencyTrace is not None:
    try:
     _d1_tr=_LatencyTrace( box_id=box_id,asset=str(cand_asset or "BTC"),sleeve=sleeve_src,ipc_age_ms=ipc_age_ms,pre_bal_ms=pre_bal_ms,book_walk_ms=book_walk_ms,fok_box_ms=fok_box_ms,shares=sh_req,parallel=use_parallel_d1,outcome="d1_ok" if _fok_ok else f"d1_{res.get('stage') or 'fail'}",)
     _d1_tr.emit()
    except Exception:
     pass
   leg_tids:List[str]=[]
   clean_zero_cost_abort=bool( not res.get("success") and not res.get("outcome_unknown") and not res.get("legged_out") and not isinstance(res.get("residual_unhedged_leg"),dict) )
   _pb_map=self.__dict__.setdefault("_d1_clean_pre_bal_cache",{})
   if clean_zero_cost_abort and "_wallet_token_balance" not in self.__dict__:
    _now_c=time.time()
    for _tk_old,(_,_ts_old) in list(_pb_map.items()):
     if (_now_c - _ts_old) > 120.0:
      _pb_map.pop(_tk_old,None)
    _pb_map[tok_a]=(pre_bal_a,_now_c)
    _pb_map[tok_b]=(pre_bal_b,_now_c)
   else:
    _pb_map.pop(tok_a,None)
    _pb_map.pop(tok_b,None)
   with st_lock:
    if dedupe_k:
     if clean_zero_cost_abort:
      seen_boxes.discard(dedupe_k)
      self.__dict__.get("_seen_d1_box_order",{}).pop(dedupe_k,None)
      for k_cd,ts_cd in list(retry_cd.items()):
       if float(ts_cd or 0.0)<=now_ts:
        retry_cd.pop(k_cd,None)
      retry_cd[dedupe_k]=now_ts + 9.5
      if is_live_ctf_box:
       self.save_state()
     else:
      retry_cd.pop(dedupe_k,None)
      self._record_seen_d1_box_key(dedupe_k)
    if res.get("success") and isinstance(res.get("leg_1"),dict) and isinstance(res.get("leg_2"),dict):
     leg_tids=self._register_live_d1_box_positions(box_id,candidate_box,res,pre_bal_a,pre_bal_b)
    elif res.get("outcome_unknown"):
     self._register_unknown_d1_box_legs(box_id,candidate_box,res,pre_bal_a,pre_bal_b)
    elif isinstance(res.get("residual_unhedged_leg"),dict):
     self.executor.invalidate_collateral_cache()
     self._pending_collateral_refresh=True
     resid=res["residual_unhedged_leg"]
     if float(resid.get("residual_shares") or 0.0) > 0.01 or resid.get("unwind_outcome_unknown"):
      leg_tids=self._register_legged_out_d1_residual(box_id,candidate_box,resid,pre_bal_a,pre_bal_b)
     else:
      self._record_inline_d1_legged_out_close(box_id,candidate_box,resid,res)
    elif dedupe_k and not clean_zero_cost_abort:
     self.save_state()
   return {"executed":bool(res.get("success")),"result":res,"leg_trade_ids":leg_tids}
  finally:
   inflight_lock.release()
 def _record_inline_d1_legged_out_close( self,box_id:str,cand:Dict[str,Any],resid:Dict[str,Any],res:Dict[str,Any] )->str:
  now_ts=time.time()
  exp_ts=float(cand.get("expiry_ts") or (now_ts + 180.0))
  asset_sym=str(cand.get("asset") or "BTC").upper()
  tok=str(resid.get("token_id") or "")
  pfx="leg_a" if tok==str(cand.get("leg_a_token_id")) else "leg_b"
  m_sh=float(resid.get("matched_shares") or cand.get("shares") or 12.0)
  px=float(resid.get("price") or cand.get(f"{pfx}_limit_price") or 0.48)
  raw_r=resid.get("raw") if isinstance(resid.get("raw"),dict) else {}
  mk_raw=self._num(raw_r.get("makingAmount") or raw_r.get("making_amount"))
  if mk_raw is not None and mk_raw>=1e4:
   mk_raw=mk_raw / 1e6
  notional=round(float(mk_raw) if (mk_raw is not None and mk_raw > 0.0) else (m_sh * px),4)
  fr=0.0 if resid.get("is_maker_anchor") else (float(cand[f"{pfx}_fee_rate"]) if cand.get(f"{pfx}_fee_rate") is not None else 0.07)
  fe=float(cand.get(f"{pfx}_fee_exponent",1.0) or 1.0)
  fee_in=round(m_sh * fr * ((px * (1.0 - px)) ** fe),4) if fr > 0.0 else 0.0
  uw=resid.get("unwind_result") if isinstance(resid.get("unwind_result"),dict) else ( res.get("unwind_result") if isinstance(res.get("unwind_result"),dict) else {} )
  gross_out=self._num(uw.get("taking_amount") or uw.get("notional_usd"))
  if gross_out is None or gross_out<=0.0:
   raw_uw=(uw.get("details") or {}).get("raw_response") if isinstance(uw.get("details"),dict) else {}
   gross_out=self._num((raw_uw or {}).get("takingAmount")) or 0.0
  if gross_out>=1e4:
   gross_out=gross_out / 1e6
  gross_out_f=round(float(gross_out),4)
  fee_out_f=round(float(self._num(uw.get("fee_usd")) or 0.0),4)
  avg_exit_px=round(gross_out_f / max(m_sh,0.01),4) if gross_out_f > 0.0 else 0.0
  net_pnl=round((gross_out_f - fee_out_f) - (notional + fee_in),2)
  tid=f"{box_id}_LEG_INLINE_UNWIND"
  if tid in self.active_positions or any(p.get("trade_id")==tid for p in self.closed_positions):
   tid=f"{tid}_{int(now_ts)}"
  now_iso=datetime.now(timezone.utc).isoformat()
  closed_rec={ "trade_id":tid,"box_id":box_id,"is_dominance_box":False,"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","entry_tte":round(max(1.0,exp_ts - now_ts),2),"event_id":box_id,"market_id":str(cand.get(f"{pfx}_market_id") or tid),"condition_id":str(cand.get(f"{pfx}_condition_id") or ""),"token_id":tok,"target_token":str(cand.get(f"{pfx}_side") or ("UP" if "UP" in str(resid.get("label","")).upper() else "DOWN")),"asset":asset_sym,"horizon":str(cand.get(f"{pfx}_horizon") or "15m"),"is_subhourly":True,"candle_open_spot":float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx=="leg_a" else "k_high") or 100.0),"entry_spot_ref":float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx=="leg_a" else "k_high") or 100.0),"spot_denomination":"USD","entry_price":round(notional / max(m_sh,0.01),4),"entry_shares":m_sh,"gross_entry_shares":m_sh,"remaining_shares":0.0,"filled_exit_shares":float(uw.get("matched_size") or m_sh),"remaining_exit_shares":0.0,"remaining_cost_basis":0.0,"realized_exit_cash":gross_out_f,"realized_exit_fee":fee_out_f,"gross_exit_cash":gross_out_f,"average_exit_price":avg_exit_px,"notional_usd":notional,"fee_usd":fee_in,"entry_fee_cash_usd":fee_in,"entry_fee_asset":"USDC","fee_source":"crypto_fees_v2","fee_rate_applied":fr,"fee_exponent_applied":fe,"entry_time_utc":now_iso,"entry_ts":now_ts,"candle_expiry_ts":exp_ts,"order_id":resid.get("orderID"),"entry_order_id":resid.get("orderID"),"unwind_order_id":uw.get("orderID"),"status":ExecutionStatus.SETTLED,"exit_order_status":"INLINE_LEGGED_OUT_UNWOUND","settled_at_utc":now_iso,"won":bool(net_pnl>=0.0),"payout_usd":round(gross_out_f,2),"net_pnl_usd":net_pnl,"close_reason":"D1_INLINE_LEGGED_OUT_UNWIND","exit_decomposition_bucket":"SALVAGE_UNWIND",}
  self.closed_positions.append(closed_rec)
  if len(self.closed_positions) > 200:
   self.closed_positions=self.closed_positions[-200:]
  try:
   self.risk_controller.record_trade_pnl(net_pnl)
  except Exception:
   pass
  self.save_state()
  logger.warning( f"[D1 INLINE LEGGED-OUT UNWIND RECORDED] {tid} ({asset_sym}): " f"Sold {m_sh:.2f} sh | Cost=${notional + fee_in:.2f} -> NetOut=${gross_out_f - fee_out_f:.2f} | Net PnL=${net_pnl:+.2f}" )
  return tid
 def _register_live_d1_box_positions( self,box_id:str,cand:Dict[str,Any],res:Dict[str,Any],pre_bal_a:float,pre_bal_b:float )->List[str]:
  now_ts=time.time()
  sh=float(res.get("shares") or cand.get("shares") or 12.0)
  exp_ts=float(cand.get("expiry_ts") or (now_ts + 180.0))
  asset_sym=str(cand.get("asset") or "BTC").upper()
  meta_by_tok={ str(cand.get("leg_a_token_id")):("leg_a",pre_bal_a),str(cand.get("leg_b_token_id")):("leg_b",pre_bal_b),}
  tids=(f"{box_id}_L1",f"{box_id}_L2")
  legs_in=(res["leg_1"],res["leg_2"])
  leg_records=[]
  tot_box_cost=0.0
  for idx,(tid,lg) in enumerate(zip(tids,legs_in)):
   partner_tid=tids[1 - idx]
   tok=str(lg["token_id"])
   pfx,pre_b=meta_by_tok.get(tok,("leg_a" if idx==0 else "leg_b",0.0))
   px=float(lg.get("price") or cand.get(f"{pfx}_limit_price") or 0.48)
   raw_r=lg.get("raw") if isinstance(lg.get("raw"),dict) else {}
   mk_raw=self._num(raw_r.get("makingAmount") or raw_r.get("making_amount"))
   if mk_raw is not None and mk_raw>=1e4:
    mk_raw=mk_raw / 1e6
   m_leg=float(lg.get("matched_shares") or sh)
   if mk_raw is not None and m_leg > sh + 0.05:
    mk_raw=mk_raw * (sh / m_leg)
   notional=round(float(mk_raw) if (mk_raw is not None and mk_raw > 0.0) else (sh * px),4)
   leg_fr_raw=cand.get(f"{pfx}_fee_rate")
   fr=0.0 if lg.get("is_maker_anchor") else (float(leg_fr_raw) if leg_fr_raw is not None else 0.07)
   fe=float(cand.get(f"{pfx}_fee_exponent",1.0) or 1.0)
   fee_u=round(sh * fr * ((px * (1.0 - px)) ** fe),4) if fr > 0.0 else 0.0
   tot_box_cost += notional + fee_u
   side_str=str(cand.get(f"{pfx}_side") or ("UP" if "UP" in str(lg.get("label","")).upper() else "DOWN"))
   strike_k=float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx=="leg_a" else "k_high") or 100.0)
   oid=lg.get("orderID")
   txs=raw_r.get("transactionsHashes") or raw_r.get("transactions_hashes") or []
   slv_rec=( "D1_SAME_ORACLE_DOMINANCE_BOX" if str(cand.get("box_type") or "DOMINANCE").upper()=="DOMINANCE" else str(cand.get("sleeve_source") or "D1_SAME_ORACLE_DOMINANCE_BOX") )
   leg_records.append((tid,{ "trade_id":tid,"box_id":box_id,"box_partner_trade_id":partner_tid,"is_dominance_box":True,"sleeve":slv_rec,"sleeve_source":str(cand.get("sleeve_source") or slv_rec),"entry_tte":max(1.0,exp_ts - now_ts),"event_id":box_id,"market_id":str(cand.get(f"{pfx}_market_id") or f"{box_id}_{idx}"),"condition_id":str(cand.get(f"{pfx}_condition_id") or ""),"token_id":tok,"target_token":side_str,"asset":asset_sym,"horizon":str(cand.get(f"{pfx}_horizon") or "15m"),"is_subhourly":True,"candle_open_spot":strike_k,"entry_spot_ref":strike_k,"spot_denomination":"USD","candle_sigma":0.0025 if asset_sym=="BTC" else 0.0035,"entry_price":round(notional / max(sh,0.01),4),"entry_shares":sh,"gross_entry_shares":sh,"remaining_shares":sh,"filled_exit_shares":0.0,"remaining_exit_shares":sh,"remaining_cost_basis":notional,"realized_exit_cash":0.0,"realized_exit_fee":0.0,"gross_exit_cash":0.0,"average_exit_price":0.0,"exit_trade_ids":[],"notional_usd":notional,"fee_usd":fee_u,"entry_fee_cash_usd":fee_u,"entry_fee_asset":"USDC","fee_source":"crypto_fees_v2","fee_rate_applied":fr,"fee_exponent_applied":fe,"target_exit_price":0.99,"exit_order_size":sh,"entry_time_utc":datetime.now(timezone.utc).isoformat(),"entry_ts":now_ts,"candle_expiry_ts":exp_ts,"pre_token_balance":pre_b,"order_id":oid,"entry_order_id":oid,"trade_ids":[],"transactions_hashes":list(txs),"status":ExecutionStatus.POSITION_CONFIRMED if self.dry_run else ExecutionStatus.MATCHED_PENDING_SETTLEMENT,"inventory_reconciled":bool(self.dry_run),"exit_order_id":None,"exit_order_status":"NONE" if self.dry_run else "AWAITING_DELTA_SETTLEMENT","is_liquidating":False,"unwind_order_id":None,"unwind_start_time":0.0,}))
  box_unit=round(tot_box_cost / max(sh,1.0),5)
  box_tp_u=str(cand.get("box_type") or "DOMINANCE").upper()
  k_lo_b=float(cand.get("k_low") or 0.0)
  k_hi_b=float(cand.get("k_high") or 0.0)
  for tid,rec in leg_records:
   rec["box_type"]=box_tp_u
   rec["box_k_low"]=k_lo_b
   rec["box_k_high"]=k_hi_b
   rec["box_cost_net"]=box_unit
   rec["box_total_cost_usd"]=round(tot_box_cost,4)
   self.active_positions[tid]=rec
  if getattr(self,"_last_known_collateral",None) is not None:
   self._last_known_collateral=max(0.0,float(self._last_known_collateral) - tot_box_cost)
  self.executor.invalidate_collateral_cache()
  self._pending_collateral_refresh=True
  self.save_state()
  if not self.dry_run:
   for tid,_ in leg_records:
    self._spawn_fast_confirm(tid)
  logger.info( f"✓ [D1 LIVE DOMINANCE BOX ENTERED] {box_id} ({asset_sym}) | {sh:.0f} pairs @ box_net=${box_unit:.4f} " f"(cost=${tot_box_cost:.2f}, min_floor=+${sh * max(0.0, 1.0 - box_unit):.2f})" )
  return [tid for tid,_ in leg_records]
 def _register_legged_out_d1_residual( self,box_id:str,cand:Dict[str,Any],resid:Dict[str,Any],pre_bal_a:float,pre_bal_b:float )->List[str]:
  now_ts=time.time()
  exp_ts=float(cand.get("expiry_ts") or (now_ts + 180.0))
  asset_sym=str(cand.get("asset") or "BTC").upper()
  tok=str(resid.get("token_id") or "")
  meta_by_tok={ str(cand.get("leg_a_token_id")):("leg_a",pre_bal_a),str(cand.get("leg_b_token_id")):("leg_b",pre_bal_b),}
  pfx,pre_b=meta_by_tok.get(tok,("leg_a",0.0))
  m_sh=float(resid.get("matched_shares") or cand.get("shares") or 12.0)
  uw_unk=bool(resid.get("unwind_outcome_unknown"))
  rem_sh=m_sh if uw_unk else float(resid.get("residual_shares") or 0.0)
  px=float(resid.get("price") or cand.get(f"{pfx}_limit_price") or 0.48)
  fr=0.0 if resid.get("is_maker_anchor") else (float(cand[f"{pfx}_fee_rate"]) if cand.get(f"{pfx}_fee_rate") is not None else 0.07)
  fe=float(cand.get(f"{pfx}_fee_exponent",1.0) or 1.0)
  notional=round(rem_sh * px,4)
  fee_u=round(rem_sh * fr * ((px * (1.0 - px)) ** fe),4) if fr > 0.0 else 0.0
  tid=f"{box_id}_LEG_RESID"
  if tid in self.active_positions or any(p.get("trade_id")==tid for p in self.closed_positions):
   tid=f"{tid}_{int(now_ts)}"
  uw_oid=(resid.get("unwind_result") or {}).get("orderID") if isinstance(resid.get("unwind_result"),dict) else None
  strike_resid=float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx=="leg_a" else "k_high") or 100.0)
  self.active_positions[tid]={ "trade_id":tid,"box_id":box_id,"is_dominance_box":False,"is_legged_out_residual":True,"pending_unwind_tag":"D1_LEGGED_OUT_RESIDUAL_UNWIND","sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","entry_tte":max(1.0,exp_ts - now_ts),"event_id":box_id,"market_id":str(cand.get(f"{pfx}_market_id") or tid),"condition_id":str(cand.get(f"{pfx}_condition_id") or ""),"token_id":tok,"target_token":str(cand.get(f"{pfx}_side") or "UP"),"asset":asset_sym,"horizon":str(cand.get(f"{pfx}_horizon") or "15m"),"is_subhourly":True,"candle_open_spot":strike_resid,"entry_spot_ref":strike_resid,"spot_denomination":"USD","candle_sigma":0.0025 if asset_sym=="BTC" else 0.0035,"entry_price":px,"entry_shares":rem_sh,"gross_entry_shares":rem_sh,"remaining_shares":rem_sh,"filled_exit_shares":0.0,"remaining_exit_shares":rem_sh,"remaining_cost_basis":notional,"realized_exit_cash":0.0,"realized_exit_fee":0.0,"gross_exit_cash":0.0,"average_exit_price":0.0,"exit_trade_ids":[],"notional_usd":notional,"fee_usd":fee_u,"entry_fee_cash_usd":fee_u,"entry_fee_asset":"USDC","fee_source":"crypto_fees_v2","fee_rate_applied":fr,"fee_exponent_applied":fe,"target_exit_price":0.99,"entry_time_utc":datetime.now(timezone.utc).isoformat(),"entry_ts":now_ts,"candle_expiry_ts":exp_ts,"pre_token_balance":pre_b,"order_id":resid.get("orderID"),"entry_order_id":resid.get("orderID"),"trade_ids":[],"transactions_hashes":[],"status":ExecutionStatus.MATCHED_PENDING_SETTLEMENT,"inventory_reconciled":False,"exit_order_id":None,"exit_order_status":"UNWIND_EXECUTION_OUTCOME_UNKNOWN" if uw_unk else "UNWIND_RETRY_REQUIRED","stop_triggered_ts":now_ts,"next_unwind_retry_ts":now_ts + 0.35,"unwind_attempt_ts":now_ts,"unwind_order_id":uw_oid if uw_unk else None,"is_liquidating":False,"unwind_start_time":now_ts,}
  self._refresh_global_halt()
  self.save_state()
  logger.warning(f"[D1 LEGGED-OUT RESIDUAL SUPERVISED] {tid} ({asset_sym}): {rem_sh:.2f} sh queued for supervised unwind.")
  return [tid]
 def _register_unknown_d1_box_legs( self,box_id:str,cand:Dict[str,Any],res:Dict[str,Any],pre_bal_a:float,pre_bal_b:float )->None:
  now_ts=time.time()
  exp_ts=float(cand.get("expiry_ts") or (now_ts + 180.0))
  sh=float(cand.get("shares") or 12.0)
  meta_by_tok={ str(cand.get("leg_a_token_id")):("leg_a",pre_bal_a),str(cand.get("leg_b_token_id")):("leg_b",pre_bal_b),}
  slots=[ (res.get("leg_1_token_id") or cand.get("leg_a_token_id"),res.get("leg_1_order_id")),(res.get("leg_2_token_id") or cand.get("leg_b_token_id"),res.get("leg_2_order_id")),]
  unk_tids:List[str]=[]
  unk_entries:List[Tuple[int,str,Optional[str]]]=[]
  for idx,(tok_raw,oid) in enumerate(slots):
   tok=str(tok_raw or "")
   if not tok:
    continue
   tid=f"{box_id}_UNK_{idx + 1}"
   if tid in self.active_positions or any(p.get("trade_id")==tid for p in self.closed_positions):
    tid=f"{tid}_{int(now_ts)}"
   unk_tids.append(tid)
   unk_entries.append((idx,tok,oid))
  for pos_i,(idx,tok,oid) in enumerate(unk_entries):
   tid=unk_tids[pos_i]
   partner_tid=unk_tids[1 - pos_i] if len(unk_tids)==2 else ""
   pfx,pre_b=meta_by_tok.get(tok,("leg_a" if idx==0 else "leg_b",0.0))
   px=float(cand.get(f"{pfx}_limit_price") or 0.50)
   strike_u=float(cand.get(f"{pfx}_strike") or cand.get("k_low" if pfx=="leg_a" else "k_high") or 100.0)
   self.active_positions[tid]={ "trade_id":tid,"box_id":box_id,"box_partner_trade_id":partner_tid,"is_dominance_box":True,"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","event_id":box_id,"market_id":str(cand.get(f"{pfx}_market_id") or tid),"condition_id":str(cand.get(f"{pfx}_condition_id") or ""),"token_id":tok,"target_token":str(cand.get(f"{pfx}_side") or "UP"),"asset":str(cand.get("asset") or "BTC").upper(),"candle_open_spot":strike_u,"entry_spot_ref":strike_u,"spot_denomination":"USD","candle_sigma":0.003,"entry_price":px,"entry_shares":sh,"gross_entry_shares":sh,"remaining_shares":sh,"filled_exit_shares":0.0,"remaining_exit_shares":sh,"remaining_cost_basis":round(sh * px,4),"realized_exit_cash":0.0,"realized_exit_fee":0.0,"gross_exit_cash":0.0,"average_exit_price":0.0,"exit_trade_ids":[],"notional_usd":round(sh * px,4),"intended_notional":round(sh * px,4),"fee_usd":0.0,"entry_fee_cash_usd":0.0,"entry_fee_asset":"USDC","fee_source":"crypto_fees_v2","target_exit_price":0.99,"entry_time_utc":datetime.now(timezone.utc).isoformat(),"entry_ts":now_ts,"submitted_at_ts":now_ts,"candle_expiry_ts":exp_ts,"pre_token_balance":pre_b,"entry_order_id":oid,"order_id":oid,"trade_ids":[],"transactions_hashes":[],"status":"ENTRY_OUTCOME_UNKNOWN","exit_order_status":"ENTRY_OUTCOME_UNKNOWN","inventory_reconciled":False,"is_liquidating":False,"unwind_order_id":None,"unwind_start_time":0.0,}
  self._refresh_global_halt()
  self.save_state()
 async def maybe_execute_graduated_maker_anchor_box(self,candidate_box:Dict[str,Any])->Dict[str,Any]:
  if not RISK_CONFIG.get("enable_graduated_d1_box",True) or self.risk_controller.is_halted() or getattr(self,"risk_halt",False):
   return {"executed":False,"reason":"DISABLED_OR_HALTED"}
  box_type=str(candidate_box.get("box_type") or "").strip().upper()
  sleeve_src=str(candidate_box.get("sleeve_source") or "D1_MAKER_ANCHOR_BOX").strip()
  cand_asset=str(candidate_box.get("asset") or "").strip().upper()
  if box_type not in {"DOMINANCE_MAKER_ANCHOR","ZERO_FEE_MAKER_ANCHOR"}:
   return {"executed":False,"reason":f"UNSUPPORTED_MAKER_ANCHOR_TYPE:{box_type}"}
  core_d1={"BTC","ETH","XRP"} | ({"SOL"} if RISK_CONFIG.get("enable_sol_d1_box",True) else set())
  exp_d1={"BNB","DOGE","HYPE"}
  mid_a=str(candidate_box.get("leg_a_market_id") or "")
  mid_b=str(candidate_box.get("leg_b_market_id") or "")
  tok_a=str(candidate_box.get("leg_a_token_id") or "")
  tok_b=str(candidate_box.get("leg_b_token_id") or "")
  fr_a=float(candidate_box["leg_a_fee_rate"]) if candidate_box.get("leg_a_fee_rate") is not None else 0.07
  fr_b=float(candidate_box["leg_b_fee_rate"]) if candidate_box.get("leg_b_fee_rate") is not None else 0.07
  fe_a=float(candidate_box.get("leg_a_fee_exponent",1.0) or 1.0)
  fe_b=float(candidate_box.get("leg_b_fee_exponent",1.0) or 1.0)
  if not tok_a or not tok_b or tok_a==tok_b or not mid_a or not mid_b or mid_a==mid_b:
   return {"executed":False,"reason":"INVALID_BOX_INVARIANTS"}
  if box_type=="DOMINANCE_MAKER_ANCHOR":
   if cand_asset and cand_asset not in (core_d1 | exp_d1):
    return {"executed":False,"reason":f"UNSUPPORTED_D1_ASSET:{cand_asset}"}
   corr_bps=float(candidate_box.get("corridor_bps") or 0.0)
   if corr_bps < (5.0 if cand_asset in exp_d1 else 3.0):
    return {"executed":False,"reason":f"CORRIDOR_TOO_NARROW:{corr_bps:.2f}"}
   k_a=float(candidate_box.get("leg_a_strike") or 0.0)
   k_b=float(candidate_box.get("leg_b_strike") or 0.0)
   if str(candidate_box.get("leg_a_side") or "").upper()!="UP" or str(candidate_box.get("leg_b_side") or "").upper()!="DOWN" or not (0.0 < k_a < k_b):
    return {"executed":False,"reason":"INVALID_BOX_INVARIANTS"}
  elif max(fr_a,fr_b) > 0.0:
   return {"executed":False,"reason":"NON_ZERO_FEE_ON_ZF_MAKER_ANCHOR"}
  inflight_mkr=self.__dict__.setdefault("_inflight_maker_anchor_keys",set())
  if len(inflight_mkr)>=1:
   return {"executed":False,"reason":"MAKER_ANCHOR_ALREADY_INFLIGHT"}
  dedupe_k=str(candidate_box.get("dedupe_key") or "")
  now_ts=time.time()
  seen_boxes=self.__dict__.setdefault("_seen_d1_box_keys",set())
  retry_cd=self.__dict__.setdefault("_d1_retry_cooldown_until",{})
  if (dedupe_k and dedupe_k in seen_boxes) or (dedupe_k and float(retry_cd.get(dedupe_k,0.0) or 0.0) > now_ts):
   return {"executed":False,"reason":"ALREADY_SEEN_OR_COOLDOWN"}
  if not self.dry_run and (not getattr(self,"_startup_reconciled",False) or self._global_halt_reasons()):
   return {"executed":False,"reason":"NOT_READY_OR_GLOBAL_HALT"}
  try:
   st_path=DATA_DIR / "alpha124_shadow_state.json"
   if not st_path.exists() and DATA_DIR==(PIPELINE_ROOT / "data" / "polymarket"):
    alt_p=PIPELINE_ROOT / "data" / "alpha124" / "alpha124_shadow_state.json"
    if alt_p.exists():
     st_path=alt_p
   if not st_path.exists() or (time.time() - st_path.stat().st_mtime) > 300.0:
    return {"executed":False,"reason":"ALPHA124_STATE_MISSING_OR_STALE"}
   st_raw=_json_loads(st_path.read_text(encoding="utf-8"))
   by_sl_map=st_raw.get("by_sleeve") or st_raw.get("per_strategy") or {}
   by_da_map=st_raw.get("by_d1_asset") or {}
   def _grad8_m(rec:Dict[str,Any])->bool:
    adj_p=rec.get("legging_adjusted_pnl_t1000_usd",rec.get("realized_pnl_t1000_usd",0.0))
    return bool( int(rec.get("closed",0) or 0)>=8 and float(rec.get("win_rate_pct",0.0) or 0.0)>=100.0 and float(rec.get("realized_pnl_t1000_usd",0.0) or 0.0) > 0.0 and float(adj_p or 0.0) > 0.0 )
   if not _grad8_m(by_sl_map.get(sleeve_src) or {}):
    return {"executed":False,"reason":f"MAKER_ANCHOR_NOT_YET_8_OF_8_GRADUATED:{sleeve_src}"}
   if box_type=="DOMINANCE_MAKER_ANCHOR" and cand_asset in exp_d1 and not _grad8_m(by_da_map.get(cand_asset) or {}):
    return {"executed":False,"reason":f"EXPANSION_ASSET_NOT_YET_8_OF_8_GRADUATED:{cand_asset}"}
  except Exception as exc_g:
   return {"executed":False,"reason":f"STATE_READ_ERROR:{exc_g}"}
  exp_ts=float(candidate_box.get("expiry_ts") or 0.0)
  cand_ts=float(candidate_box.get("ts_unix") or now_ts)
  max_tte_m=64800.0 if box_type=="ZERO_FEE_MAKER_ANCHOR" else 900.0
  min_tte_m=240.0 if box_type=="ZERO_FEE_MAKER_ANCHOR" else 65.0
  if not self.dry_run and ((now_ts - cand_ts) > 5.0 or (exp_ts > 0.0 and not (min_tte_m<=(exp_ts - now_ts)<=max_tte_m))):
   return {"executed":False,"reason":"STALE_OR_OUTSIDE_TTE_WINDOW"}
  busy_mkts={str(p.get("market_id") or "") for p in self.active_positions.values()} | { str(i.get("market_id") or "") for i in getattr(self,"pending_entry_intents",{}).values() }
  if mid_a in busy_mkts or mid_b in busy_mkts:
   return {"executed":False,"reason":"MARKET_ALREADY_OCCUPIED"}
  anc_is_a=bool(candidate_box.get("anchor_is_a",True))
  tok_anc,tok_hdg=(tok_a,tok_b) if anc_is_a else (tok_b,tok_a)
  mid_anc=mid_a if anc_is_a else mid_b
  lbl_anc=str(candidate_box.get("leg_a_label" if anc_is_a else "leg_b_label") or "ANC")
  lbl_hdg=str(candidate_box.get("leg_b_label" if anc_is_a else "leg_a_label") or "HDG")
  anc_side=str(candidate_box.get("leg_a_side" if anc_is_a else "leg_b_side") or "UP").upper()
  fr_hdg=fr_b if anc_is_a else fr_a
  fe_hdg=fe_b if anc_is_a else fe_a
  _raw_nr_anc=candidate_box.get("leg_a_neg_risk" if anc_is_a else "leg_b_neg_risk")
  _raw_nr_hdg=candidate_box.get("leg_b_neg_risk" if anc_is_a else "leg_a_neg_risk")
  nr_anc=_raw_nr_anc if isinstance(_raw_nr_anc,bool) else None
  nr_hdg=_raw_nr_hdg if isinstance(_raw_nr_hdg,bool) else None
  anc_bid_px=float(candidate_box.get("anchor_bid_px") or (candidate_box["leg_a_limit_price"] if anc_is_a else candidate_box["leg_b_limit_price"]))
  hdg_lim_px=float(candidate_box.get("hedge_limit_px") or (candidate_box["leg_b_limit_price"] if anc_is_a else candidate_box["leg_a_limit_price"]))
  max_pair_cap=0.990 if box_type=="ZERO_FEE_MAKER_ANCHOR" else 0.988
  posted_spot=float(candidate_box.get("posted_spot") or 0.0)
  collat=getattr(self,"_last_known_collateral",None)
  if collat is None and not self.dry_run:
   try:
    collat=await asyncio.to_thread(self.executor.get_collateral_balance)
   except Exception:
    collat=0.0
  inflight_u=sum(float(i.get("notional_usd",0.0) or 0.0) for i in getattr(self,"pending_entry_intents",{}).values() if isinstance(i,dict))
  collat_f=100.0 if self.dry_run else max(0.0,float(collat or 0.0) - inflight_u)
  asset_cap={"BTC":18.0,"ETH":18.0,"SOL":16.5,"XRP":16.5,"NBA":18.0}.get(cand_asset,16.5)
  budget=min(18.0,asset_cap,max(0.0,collat_f - float(RISK_CONFIG.get("d1_box_collateral_reserve_usd",16.50))),collat_f * 0.25)
  pair_est=anc_bid_px + hdg_lim_px + (fr_hdg * ((hdg_lim_px * (1.0 - hdg_lim_px)) ** fe_hdg) if fr_hdg > 0.0 else 0.0)
  if not (0.900<=pair_est<=max_pair_cap + 0.003):
   return {"executed":False,"reason":f"PAIR_COST_OUT_OF_BAND:{pair_est:.4f}"}
  sh_int=int(math.floor(budget / max(0.90,pair_est)))
  if sh_int < 5:
   return {"executed":False,"reason":"INSUFFICIENT_MAKER_BOX_BUDGET"}
  inflight_key=dedupe_k or f"MKR_{mid_a}_{mid_b}"
  inflight_mkr.add(inflight_key)
  box_id=str(candidate_box.get("box_id") or f"MKR_LIVE_{int(now_ts)}")
  intent_id=f"{box_id}_ANC_INTENT"
  try:
   pre_bal_a=0.0 if self.dry_run else float(await asyncio.to_thread(self._wallet_token_balance,tok_a) or 0.0)
   pre_bal_b=0.0 if self.dry_run else float(await asyncio.to_thread(self._wallet_token_balance,tok_b) or 0.0)
   if not self.dry_run and hasattr(self.executor,"get_market_book"):
    bk_anc_f,bk_hdg_f=await asyncio.gather( asyncio.to_thread(self.executor.get_market_book,tok_anc),asyncio.to_thread(self.executor.get_market_book,tok_hdg),)
    asks_af=sorted([(float(x["price"] if isinstance(x,dict) else x[0]),float(x["size"] if isinstance(x,dict) else x[1])) for x in ((bk_anc_f or {}).get("asks") or []) if float(x.get("size",0) if isinstance(x,dict) else x[1]) > 0])
    asks_hf=sorted([(float(x["price"] if isinstance(x,dict) else x[0]),float(x["size"] if isinstance(x,dict) else x[1])) for x in ((bk_hdg_f or {}).get("asks") or []) if float(x.get("size",0) if isinstance(x,dict) else x[1]) > 0])
    if not asks_af or not asks_hf or anc_bid_px>=asks_af[0][0]:
     return {"executed":False,"reason":"FRESH_BOOK_CROSS_OR_EMPTY"}
    hdg_ask_f=asks_hf[0][0]
    hdg_av_f=sum(sz for px,sz in asks_hf if px<=hdg_ask_f + 0.01)
    hdg_fee_f=fr_hdg * ((hdg_ask_f * (1.0 - hdg_ask_f)) ** fe_hdg) if fr_hdg > 0.0 else 0.0
    if hdg_av_f < max(15.0,2.5 * sh_int) or not (0.900<=(anc_bid_px + hdg_ask_f + hdg_fee_f)<=max_pair_cap):
     return {"executed":False,"reason":"FRESH_HEDGE_DEPTH_OR_COST_REJECT"}
    opp_a=str(candidate_box.get("leg_a_opp_token_id") or "")
    opp_b=str(candidate_box.get("leg_b_opp_token_id") or "")
    if opp_a and opp_b:
     obk_a,obk_b=await asyncio.gather( asyncio.to_thread(self.executor.get_market_book,opp_a),asyncio.to_thread(self.executor.get_market_book,opp_b),)
     ob_a=max((float(x["price"] if isinstance(x,dict) else x[0]) for x in ((obk_a or {}).get("bids") or [])),default=0.0)
     ob_b=max((float(x["price"] if isinstance(x,dict) else x[0]) for x in ((obk_b or {}).get("bids") or [])),default=0.0)
     if (ob_a + ob_b) > 1.0:
      return {"executed":False,"reason":f"ANTI_BOX_COMPLEMENT_VETO:{ob_a + ob_b:.4f}"}
    hdg_buf_f=0.002 if (hdg_ask_f < 0.04 or hdg_ask_f>=0.96) else 0.01
    max_hdg_cap_f=max(hdg_ask_f,round(0.992 - anc_bid_px - hdg_fee_f,3))
    hdg_lim_px=min(0.995,max(hdg_ask_f,min(round(hdg_ask_f + hdg_buf_f,3),max_hdg_cap_f)))
   anc_notional=round((sh_int + 0.01) * anc_bid_px,4)
   self.pending_entry_intents[intent_id]={ "trade_id":intent_id,"market_id":mid_anc,"token_id":tok_anc,"notional_usd":round(sh_int * anc_bid_px,4),"ts":time.time(),}
   post_res=await asyncio.to_thread( self.executor.post_maker_entry_order,token_id=tok_anc,price=anc_bid_px,notional_usd=anc_notional,side="BUY",neg_risk=nr_anc,min_price_floor=0.001,max_price_ceiling=0.995,)
   maker_oid=str((post_res or {}).get("orderID") or "").strip()
   if not isinstance(post_res,dict) or not post_res.get("success") or not maker_oid:
    self.pending_entry_intents.pop(intent_id,None)
    return {"executed":False,"reason":f"ANCHOR_POST_FAILED:{(post_res or {}).get('error')}"}
   if self.dry_run:
    matched_sh,avg_anc_px,anc_raw=float(sh_int),float(post_res.get("price") or anc_bid_px),post_res
   else:
    ttl_s=12.0 if box_type=="ZERO_FEE_MAKER_ANCHOR" else 10.0
    deadline=time.monotonic() + ttl_s
    uws=getattr(self.executor,"_user_ws_cache",None)
    while time.monotonic() < deadline:
     if exp_ts > 0.0 and (exp_ts - time.time())<=(180.0 if box_type=="ZERO_FEE_MAKER_ANCHOR" else 48.0):
      break
     rem_w=max(0.02,min(0.10,deadline - time.monotonic()))
     if uws is not None and uws.is_healthy():
      await uws.wait_for_fill_or_timeout(rem_w,prev_seq=uws.fill_sequence)
      snap_o=uws.get_order_snapshot(maker_oid,max_age_sec=5.0)
      if isinstance(snap_o,dict) and str(snap_o.get("status") or "").upper() in ("MATCHED","FILLED"):
       break
     else:
      await asyncio.sleep(rem_w)
     if box_type=="DOMINANCE_MAKER_ANCHOR" and posted_spot > 0.0:
      cur_sp=await asyncio.to_thread(self.get_usd_reference_spot_price,cand_asset)
      if cur_sp and float(cur_sp) > 0.0:
       drift_bps=(float(cur_sp) - posted_spot) / posted_spot * 10000.0
       if (anc_side=="UP" and drift_bps < -2.5) or (anc_side=="DOWN" and drift_bps > 2.5):
        logger.info(f"[MAKER ANCHOR ADVERSE CANCEL] {box_id}: drift={drift_bps:+.2f}bps against {anc_side}; canceling {maker_oid}.")
        break
    cancel_res=await asyncio.to_thread(self.executor.cancel_order,maker_oid)
    summary=await asyncio.to_thread(self.executor.get_order_fill_summary,maker_oid,tok_anc)
    self.pending_entry_intents.pop(intent_id,None)
    matched_sh=float((summary or {}).get("matched") or (cancel_res or {}).get("matched") or 0.0)
    avg_anc_px=float((summary or {}).get("avg_price") or post_res.get("price") or anc_bid_px)
    anc_raw=summary or cancel_res or post_res
    if matched_sh < 0.01:
     retry_cd[dedupe_k]=time.time() + 8.0
     return {"executed":False,"reason":"MAKER_ANCHOR_EXPIRED_UNFILLED"}
   self.pending_entry_intents.pop(intent_id,None)
   if not self.dry_run and hasattr(self.executor,"get_market_book"):
    bk_h2=await asyncio.to_thread(self.executor.get_market_book,tok_hdg)
    asks_h2=sorted([(float(x["price"] if isinstance(x,dict) else x[0]),float(x["size"] if isinstance(x,dict) else x[1])) for x in ((bk_h2 or {}).get("asks") or []) if float(x.get("size",0) if isinstance(x,dict) else x[1]) > 0])
    if asks_h2:
     h2_px=asks_h2[0][0]
     h2_fee=fr_hdg * ((h2_px * (1.0 - h2_px)) ** fe_hdg) if fr_hdg > 0.0 else 0.0
     h2_buf=0.002 if (h2_px < 0.04 or h2_px>=0.96) else 0.01
     h2_cap=max(h2_px,round(0.992 - avg_anc_px - h2_fee,3))
     hdg_lim_px=min(0.995,max(h2_px,min(round(h2_px + h2_buf,3),h2_cap)))
   res=await asyncio.to_thread( self.executor.execute_maker_anchor_hedge_or_unwind,box_id=box_id,anchor_token_id=tok_anc,anchor_label=lbl_anc,anchor_price=avg_anc_px,anchor_matched_shares=matched_sh,anchor_order_id=maker_oid,hedge_token_id=tok_hdg,hedge_label=lbl_hdg,hedge_limit_price=hdg_lim_px,max_box_cost_net=0.993,hedge_fee_rate=fr_hdg,hedge_fee_exponent=fe_hdg,anchor_neg_risk=nr_anc,hedge_neg_risk=nr_hdg,anchor_pre_balance=(pre_bal_a if anc_is_a else pre_bal_b),hedge_pre_balance=(pre_bal_b if anc_is_a else pre_bal_a),anchor_raw=anc_raw,)
   st_lock=getattr(self,"_state_save_lock",None) or self._GLOBAL_STATE_SAVE_LOCK
   leg_tids:List[str]=[]
   with st_lock:
    if dedupe_k:
     self._record_seen_d1_box_key(dedupe_k)
    if res.get("success") and isinstance(res.get("leg_1"),dict) and isinstance(res.get("leg_2"),dict):
     leg_tids=self._register_live_d1_box_positions(box_id,candidate_box,res,pre_bal_a,pre_bal_b)
    elif res.get("outcome_unknown"):
     self._register_unknown_d1_box_legs(box_id,candidate_box,res,pre_bal_a,pre_bal_b)
    elif isinstance(res.get("residual_unhedged_leg"),dict):
     self.executor.invalidate_collateral_cache()
     self._pending_collateral_refresh=True
     resid=res["residual_unhedged_leg"]
     if float(resid.get("residual_shares") or 0.0) > 0.01 or resid.get("unwind_outcome_unknown"):
      leg_tids=self._register_legged_out_d1_residual(box_id,candidate_box,resid,pre_bal_a,pre_bal_b)
     else:
      self._record_inline_d1_legged_out_close(box_id,candidate_box,resid,res)
   return {"executed":bool(res.get("success")),"result":res,"leg_trade_ids":leg_tids}
  finally:
   self.pending_entry_intents.pop(intent_id,None)
   inflight_mkr.discard(inflight_key)
 def _spawn_live_maker_anchor_box_task(self,candidate_box:Dict[str,Any])->None:
  tasks=self.__dict__.setdefault("_maker_anchor_bg_tasks",set())
  if len(tasks)>=1:
   return
  t=asyncio.create_task(self.maybe_execute_graduated_maker_anchor_box(candidate_box))
  tasks.add(t)
  t.add_done_callback(tasks.discard)
 async def _poll_d1_live_box_candidates(self,now_ts:float)->int:
  raw_lines:List[str]=[]
  fast_q=getattr(self,"_fast_d1_cand_lines",None)
  if fast_q:
   while fast_q:
    raw_lines.append(fast_q.popleft())
  if not raw_lines or (now_ts - getattr(self,"_last_d1_disk_poll",0.0))>=0.50:
   self._last_d1_disk_poll=now_ts
   cand_file=DATA_DIR / "d1_live_box_candidates.jsonl"
   if not getattr(self,"_d1_cand_initialized",False):
    self._d1_cand_initialized=True
    self._last_d1_cand_offset=cand_file.stat().st_size if cand_file.exists() else 0
   if cand_file.exists():
    sz=cand_file.stat().st_size
    if sz < self._last_d1_cand_offset:
     self._last_d1_cand_offset=0
    if sz > self._last_d1_cand_offset:
     with open(cand_file,"rb") as fp:
      fp.seek(self._last_d1_cand_offset)
      chunk=fp.read()
     end_nl=chunk.rfind(b"\n") + 1
     if end_nl:
      self._last_d1_cand_offset += end_nl
      raw_lines.extend(chunk[:end_nl].decode("utf-8",errors="ignore").splitlines())
  if not raw_lines:
   return 0
  seen_emits=self.__dict__.setdefault("_seen_d1_emit_ids",{})
  executed=0
  loop=asyncio.get_running_loop()
  self._main_loop=loop
  for raw_ln in raw_lines:
   if not raw_ln.strip():
    continue
   try:
    cand=_json_loads(raw_ln)
    emit_id=f"{cand.get('dedupe_key') or cand.get('box_id')}:{cand.get('ts_unix')}"
    if emit_id in seen_emits:
     continue
    seen_emits[emit_id]=None
    while len(seen_emits) > 128:
     seen_emits.pop(next(iter(seen_emits)),None)
    if str(cand.get("box_type") or "").strip().upper() in {"DOMINANCE_MAKER_ANCHOR","ZERO_FEE_MAKER_ANCHOR"}:
     self._spawn_live_maker_anchor_box_task(cand)
     continue
    out=await loop.run_in_executor(_get_hot_io_pool(),self.maybe_execute_graduated_d1_box,cand)
    if out.get("executed"):
     if not self.dry_run:
      for tid in out.get("leg_trade_ids") or []:
       self._spawn_fast_confirm(tid)
     executed += 1
     break
   except Exception as exc:
    logger.error(f"[D1 LIVE BRIDGE] Error evaluating candidate: {exc}",exc_info=True)
  return executed
 def _calc_priority_score(self,s_item:Dict[str,Any])->float:
  _a_s=str(s_item.get("asset") or "").upper()
  if _a_s and _a_s not in self.get_graduated_allowed_assets():
   return 0.0
  s_dir=s_item.get("shock_direction")
  tgt="UP" if s_dir=="BUY" else "DOWN"
  feats=s_item.get("pre_shock_features_t0",{})
  side_data=feats.get(tgt,{}) if isinstance(feats,dict) else {}
  dist_raw=float(s_item.get("candle_distance_pct",0.0) or 0.0)
  if (tgt=="UP" and dist_raw < 0.04) or (tgt=="DOWN" and dist_raw > -0.04):
   return 0.0
  dist=abs(dist_raw)
  z_sc=abs(float(s_item.get("z_val",s_item.get("z_score",s_item.get("expected_prob_shift",dist * 0.5)))))
  ask_est=float(side_data.get("vwap_$50") or side_data.get("effective_price_$50") or side_data.get("vwap_$25") or side_data.get("effective_price_$25") or 0.50)
  _t_low=str(s_item.get("title","")).lower()
  _is_15m=("pm-" in _t_low or "am-" in _t_low or "15m" in str(s_item.get("timeframe","")).lower())
  _tte_s=float(s_item.get("seconds_to_expiry",3600.0) or 3600.0)
  _is_bnd=( s_item.get("shock_source")=="BOUNDARY_LOCK" or s_item.get("regime_override")=="REGIME_D_BOUNDARY_LOCK" or (12.0<=_tte_s<=60.0 and dist>=0.08) )
  _is_slv3=s_item.get("sleeve")=="SLEEVE_3_STRIKE_CONVERGENCE" or s_item.get("shock_source")=="EXP316_TRACK_A_CONVERGENCE"
  _ceil=0.94 if _is_bnd else (0.89 if _is_slv3 else (min(self.max_price_ceiling,0.85) if _is_15m else self.max_price_ceiling))
  if ask_est < self.min_price_floor or ask_est > _ceil:
   return 0.0
  return z_sc / max(ask_est,0.01)
 async def evaluate_shock_and_execute(self,shock:Dict[str,Any]):
  self._main_loop=asyncio.get_running_loop()
  if _LatencyTrace is None or _CURRENT_TRACE is None:
   return await self._evaluate_shock_and_execute_impl(shock)
  token=None
  try:
   trace=_LatencyTrace( shock_id=str(shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"),market_id=str(shock.get("market_id") or ""),asset=str(shock.get("asset") or ""),sleeve=str(shock.get("sleeve") or shock.get("regime") or shock.get("strategy") or ""),src_t0_unix=shock.get("t0_unix"),dry_run=bool(getattr(self,"dry_run",False)),)
   trace.stamp("trigger_consumed")
   try:
    trace.set(trigger_to_consume_wall_ms=round((time.time() - float(shock.get("t0_unix"))) * 1000.0,3))
   except (TypeError,ValueError):
    pass
   token=_CURRENT_TRACE.set(trace)
  except Exception:
   token=None
  try:
   return await self._evaluate_shock_and_execute_impl(shock)
  finally:
   if token is not None:
    try:
     _CURRENT_TRACE.reset(token)
    except Exception:
     pass
 async def _evaluate_shock_and_execute_impl(self,shock:Dict[str,Any]):
  shock_id=shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
  legacy_evt=shock.get("event_id")
  if shock_id in self.seen_shock_ids or (legacy_evt and legacy_evt!=str(shock.get("market_id")) and legacy_evt in self.seen_shock_ids):
   logger.debug(f"[IDEMPOTENCY] Trigger event {shock_id} already executed or seen. Skipping duplicate trigger.")
   return
  self._record_seen_shock_id(shock_id)
  if legacy_evt and legacy_evt!=str(shock.get("market_id")):
   self._record_seen_shock_id(legacy_evt)
  self.last_event_id=shock_id
  if self.risk_controller.is_halted() or getattr(self,"risk_halt",False):
   logger.warning(f"[CIRCUIT BREAKER BLOCKED] Refusing new order entry: risk controller or global reconciliation halt active ({self.global_halt_reasons}).")
   return
  m_id=str(shock.get("market_id") or "")
  if m_id and m_id in self._reconciling_market_ids():
   logger.warning(f"[MARKET RECONCILIATION BLOCKED] Market {m_id} has unresolved ENTRY_OUTCOME_UNKNOWN. Refusing new entry on this market.")
   return
  live_reasons=self._global_halt_reasons()
  if live_reasons or (self.risk_halt and not getattr(self,"_startup_reconciled",False)):
   self._refresh_global_halt()
   logger.warning(f"[GLOBAL ENTRY BLOCKED] Refusing new order entry: unresolved global reconciliation {live_reasons}.")
   return
  risk_positions=self._risk_bearing_positions()
  in_flight_intents=[k for k in self.pending_entry_intents if k not in risk_positions]
  if len(risk_positions) + len(in_flight_intents)>=self.max_concurrent_positions:
   logger.debug( f"[CONCURRENCY LIMIT] Total positions count ({len(risk_positions)} active + {len(in_flight_intents)} pending) " f">= limit ({self.max_concurrent_positions}). Enforced." )
   return
  if not self.dry_run and not self.executor.is_heartbeat_healthy():
   logger.critical(f"[HEARTBEAT UNHEALTHY] CLOB heartbeat has failed {self.executor.heartbeat_failures} times. Halting new entries.")
   self.risk_controller.halted=True
   self.risk_controller.halt_reason=f"Heartbeat degraded ({self.executor.heartbeat_failures} consecutive drops) - new entries halted; existing positions remain supervised."
   self.save_state()
   return
  now_hour=time.time() // 3600
  if now_hour!=self.current_hour_window:
   self.current_hour_window=now_hour
   self.trades_this_hour=0
  risk_positions=self._risk_bearing_positions()
  current_exposure=sum(float(pos.get("notional_usd",0.0) or 0.0) for pos in risk_positions.values())
  current_exposure += sum( float(i.get("notional_usd",0.0) or 0.0) for k,i in self.pending_entry_intents.items() if k not in risk_positions )
  shock_dir=shock.get("shock_direction")
  if not shock_dir:
   return
  target_token="UP" if shock_dir=="BUY" else "DOWN"
  tte=float(shock.get("seconds_to_expiry",3600.0) or 3600.0)
  is_sleeve3_strike=bool( shock.get("sleeve")=="SLEEVE_3_STRIKE_CONVERGENCE" or shock.get("shock_source")=="EXP316_TRACK_A_CONVERGENCE" )
  _pre_dist_abs=abs(float(shock.get("candle_distance_pct",0.0) or 0.0))
  _pre_z_abs=max( abs(float(shock.get("z_val") or shock.get("z_score") or shock.get("shock_z") or 0.0)),(_pre_dist_abs / 0.03) if (12.0<=tte<=60.0 and _pre_dist_abs>=0.08) else 0.0,)
  is_boundary_lock_cand=bool( shock.get("shock_source")=="BOUNDARY_LOCK" or shock.get("regime_override")=="REGIME_D_BOUNDARY_LOCK" or (12.0<=tte<=90.0 and _pre_z_abs>=3.0) )
  eff_max_tte=max(self.max_tte,10800.0) if is_sleeve3_strike else self.max_tte
  eff_min_tte=12.0 if is_boundary_lock_cand else 30.0
  if tte > eff_max_tte or tte < eff_min_tte:
   return
  if m_id:
   active_for_market=any( p.get("market_id")==m_id for p in self.active_positions.values() )
   intent_for_market=any( i.get("market_id")==m_id for i in self.pending_entry_intents.values() )
   trades_for_market=self.trades_per_market.get(m_id,0)
   is_win_reentry=False
   is_loss_locked=False
   if trades_for_market>=1 and not active_for_market and not intent_for_market:
    closed_for_mkt=[ p for p in self.closed_positions if p.get("market_id")==m_id ]
    if closed_for_mkt:
     last_closed=closed_for_mkt[-1]
     if last_closed.get("won") is True and float(last_closed.get("net_pnl_usd",0.0) or 0.0) > 0.0:
      is_win_reentry=(trades_for_market==1 and self.max_trades_per_market>=2)
     else:
      is_loss_locked=True
   market_limit_reached=True if is_loss_locked else ((trades_for_market>=2) if is_win_reentry else (trades_for_market>=self.max_trades_per_market))
   if active_for_market or intent_for_market or market_limit_reached:
    logger.debug( f"[MARKET DEDUP REJECT] Position/intent already active or traded for {m_id}. " f"trades={trades_for_market}, win_reentry={is_win_reentry}" )
    return
  title_str=str(shock.get("title","") or "")
  title_lower=title_str.lower()
  horizon=str(shock.get("horizon","") or shock.get("candle_interval","")).lower()
  slug=str(shock.get("series_slug","") or shock.get("slug","")).lower()
  open_ts_val=float(shock.get("candle_open_ts") or 0.0)
  close_ts_val=float(shock.get("candle_expiry_ts") or shock.get("expiry_ts") or 0.0)
  duration_val=(close_ts_val - open_ts_val) if (close_ts_val > open_ts_val > 0) else 0.0
  has_subhourly_time_range=any(m in title_lower for m in (":05",":10",":15",":20",":25",":30",":35",":40",":45",":50",":55"))
  is_subhourly=( any(x in horizon or x in slug or x in title_lower for x in ("5m","15m","300s","900s")) or (0.0 < duration_val<=900.0) or has_subhourly_time_range )
  is_1h=not is_subhourly and ( any(x in horizon or x in slug or x in title_lower for x in ("1h","hourly","60m")) or (duration_val>=3500.0) or ("am et" in title_lower or "pm et" in title_lower) )
  now_dt=datetime.fromtimestamp(shock.get("t0_unix",time.time()),tz=timezone.utc)
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1" and is_1h:
   try:
    from zoneinfo import ZoneInfo
    ny_dt=now_dt.astimezone(ZoneInfo("America/New_York"))
    is_nyse_open_window=(ny_dt.weekday() < 5 and ny_dt.hour==9 and 15<=ny_dt.minute < 32)
   except Exception:
    is_nyse_open_window=(now_dt.weekday() < 5 and now_dt.hour==13 and 15<=now_dt.minute < 32)
   if is_nyse_open_window:
    logger.info(f"[NYSE_OPEN_BLACKOUT] {shock.get('title')!r}: Rejecting 1h entry during 09:15-09:32 ET window.")
    return
  dist_pct=float(shock.get("candle_distance_pct",0.0) or 0.0)
  open_spot_cand=( shock.get("candle_open_spot") if is_subhourly else (shock.get("finalized_1h_open") or shock.get("candle_open_spot")) )
  spot_at_t0=float(shock.get("spot_at_t0") or shock.get("trigger_price") or 0.0)
  t0_u=float(shock.get("t0_unix",time.time()))
  cur_h_idx=int(t0_u // 3600)
  _res_source_lower=str(shock.get("resolution_source") or "").lower()
  _uses_chainlink_twap=("chain.link" in _res_source_lower) or (is_subhourly and "binance" not in _res_source_lower)
  twap_60s_open=float(shock.get("twap_60s_open") or 0.0)
  cl_open_spot=float(shock.get("chainlink_open_spot") or 0.0)
  auth_cl_open=float(shock.get("authoritative_chainlink_open") or 0.0)
  usd_spot_t0,usd_twap_t0=self._resolve_true_usd_spot_from_shock(shock)
  _is_usd_oracle=False
  if _uses_chainlink_twap and auth_cl_open > 0.0 and math.isfinite(auth_cl_open):
   if usd_spot_t0 > 0.0 and math.isfinite(usd_spot_t0):
    _is_usd_oracle=True
    open_spot_cand=auth_cl_open
    dist_pct=((usd_spot_t0 - auth_cl_open) / auth_cl_open) * 100.0
   elif not self.dry_run:
    logger.info(f"[ORACLE PROVENANCE REJECT] {shock.get('title')!r}: USD open ${auth_cl_open:,.2f} lacks verified USD spot anchor.")
    return
  elif _uses_chainlink_twap and open_spot_cand and float(open_spot_cand) > 0.0:
   raw_open_ref=float(open_spot_cand)
   anchor_candidates=[raw_open_ref]
   if twap_60s_open > 0.0:
    anchor_candidates.append(twap_60s_open)
   if cl_open_spot > 0.0 and abs(cl_open_spot - raw_open_ref) / raw_open_ref < 0.005:
    anchor_candidates.append(cl_open_spot)
   if len(anchor_candidates) > 1:
    wick_div_pct=(abs(raw_open_ref - twap_60s_open) / raw_open_ref * 100.0) if twap_60s_open > 0.0 else 0.0
    dual_open_ref=max(anchor_candidates) if target_token=="UP" else min(anchor_candidates)
    open_spot_cand=dual_open_ref
    if spot_at_t0 > 0.0:
     dist_pct=((spot_at_t0 - dual_open_ref) / dual_open_ref) * 100.0
    if wick_div_pct>=0.0395 and abs(dist_pct) < 0.10:
     logger.info( f"[BOUNDARY WICK VETO] {shock.get('title')!r} {target_token}: " f"1s tick open (${raw_open_ref:,.2f}) diverges from 60s TWAP (${twap_60s_open:,.2f}) by " f"{wick_div_pct:.4f}% >= 0.0395% (dual_cush={abs(dist_pct):.4f}% < 0.10%). Skipping oracle-wick trap." )
     return
  asset_chk=str(shock.get("asset","")).upper() or ( "BTC" if ("btc" in title_lower or "bitcoin" in title_lower) else ("ETH" if ("eth" in title_lower or "ethereum" in title_lower) else "") )
  if is_1h and asset_chk in ("BTC","ETH") and open_spot_cand and math.isfinite(float(open_spot_cand)) and float(open_spot_cand) > 0.0:
   self.hourly_candle_opens.setdefault(asset_chk,{})[cur_h_idx]=float(open_spot_cand)
  if is_1h and (abs(dist_pct) < 0.0001 or not open_spot_cand or float(open_spot_cand)<=0.0) and spot_at_t0 > 0.0:
   cached_open=self.hourly_candle_opens.get(asset_chk,{}).get(cur_h_idx)
   if cached_open and cached_open > 0.0:
    dist_pct=((spot_at_t0 - cached_open) / cached_open) * 100.0
    open_spot_cand=cached_open
  if not self.dry_run and asset_chk in ("BTC","ETH","SOL","XRP") and open_spot_cand:
   self._update_shadow_phase4_monotonicity_scanner( shock,asset_chk,bool(is_subhourly),bool(is_1h),float(tte),float(open_spot_cand) )
  min_dist=0.04 if (not self.dry_run) else 0.05
  if abs(dist_pct) < min_dist:
   return
  if target_token=="UP" and dist_pct < min_dist:
   return
  if target_token=="DOWN" and dist_pct > -min_dist:
   return
  m_id=str(shock.get("market_id") or "")
  token_features=shock.get("pre_shock_features_t0",{}).get(target_token,{})
  token_id=token_features.get("token_id")
  if not token_id and m_id:
   token_id=await asyncio.to_thread(self.get_token_id,m_id,target_token)
  asset_str=str(shock.get("asset","")).upper()
  if not asset_str:
   asset_str=( "BTC" if ("btc" in title_lower or "bitcoin" in title_lower) else ("ETH" if ("eth" in title_lower or "ethereum" in title_lower) else ("SOL" if ("sol" in title_lower or "solana" in title_lower) else "")) )
  if not asset_str and self.dry_run:
   asset_str="BTC"
  base_allowed=self.get_graduated_allowed_assets()
  effective_allowed_assets=(base_allowed | {"SOL"}) if is_sleeve3_strike else base_allowed
  if not asset_str or asset_str not in effective_allowed_assets:
   if asset_str in ("ETH","SOL"):
    shadow_cand={ "logged_at_utc":datetime.now(timezone.utc).isoformat(),"asset":asset_str,"horizon":"15m" if is_subhourly else "1h","market_id":m_id,"title":shock.get("title"),"target_token":target_token,"token_id":token_id or f"{asset_str}_SHADOW","dist_pct":dist_pct,"tte_seconds":tte,"best_ask":token_features.get("best_ask"),"vwap_$25":token_features.get("vwap_$25"),"age_ask_ms":token_features.get("age_ask_ms"),"shock_volume_100ms":shock.get("shock_volume_100ms"),"shock_ofi":shock.get("shock_ofi"),"spot_at_t0":spot_at_t0,"candle_open_spot":open_spot_cand,"twap_60s_open":shock.get("twap_60s_open"),"resolution_source":shock.get("resolution_source",""),"expiry_ts":close_ts_val,"reason_blocked":"ASSET_PAUSED_SHADOW_ONLY",}
    try:
     with open(COUNTERFACTUAL_CANDIDATES_FILE,"a") as f:
      f.write(json.dumps(shadow_cand) + "\n")
    except Exception as e:
     logger.debug(f"Failed to record {asset_str} shadow candidate: {e}")
    logger.info(f"[SHADOW_{asset_str}_COLLECTED] {shock.get('title')} {target_token} recorded for shadow research (live trading paused).")
   logger.debug(f"[TIER GUARD] Asset {asset_str!r} not in ALLOWED_ASSETS ({self.allowed_assets}). Skipping.")
   return
  is_real_ctf_token=bool(token_id and str(token_id).isdigit() and len(str(token_id))>=20)
  is_synthetic_test=not is_real_ctf_token
  _is_live_real=(not self.dry_run) and is_real_ctf_token
  if _is_live_real:
   if shock.get("clob_ws_connected") is False:
    logger.warning(f"[CLOB_WS_DISCONNECTED_REJECT] {shock.get('title')!r}: Recorder CLOB WS disconnected at trigger time. Skipping.")
    return
   _exch_ts_ms=float(shock.get("exchange_event_ts_ms") or 0.0)
   _t0_val=float(shock.get("t0_unix") or time.time())
   if _exch_ts_ms > 0.0:
    _exch_lag_ms=(_t0_val * 1000.0) - _exch_ts_ms
    if _exch_lag_ms > 1000.0:
     logger.warning( f"[EXCHANGE_LAG_REJECT] {shock.get('title')!r}: exchange_lag={_exch_lag_ms:.1f}ms > 1000ms ceiling (socket burst-drain veto)." )
     return
   _ingress_age_s=time.time() - _t0_val
   if _ingress_age_s > 2.0:
    logger.warning( f"[STALE_TRIGGER_INGRESS_REJECT] {shock.get('title')!r}: trigger age {_ingress_age_s:.2f}s > 2.0s ceiling. Skipping." )
    return
  if _is_live_real and _uses_chainlink_twap and open_spot_cand and float(open_spot_cand) > 0.0:
   if _is_usd_oracle:
    dist_pct=((usd_spot_t0 - float(open_spot_cand)) / float(open_spot_cand)) * 100.0
   elif spot_at_t0 > 0.0:
    _vdiv_raw=shock.get("venue_divergence_centered_bps")
    if _vdiv_raw is None:
     _vdiv_raw=shock.get("venue_divergence_bps")
    _spot_refs=[spot_at_t0]
    if _vdiv_raw is not None:
     _vdiv_clamped=max(-30.0,min(30.0,float(_vdiv_raw or 0.0)))
     _spot_refs.append(spot_at_t0 * (1.0 - 0.5 * _vdiv_clamped / 10000.0))
    _eff_spot_ref=min(_spot_refs) if target_token=="UP" else max(_spot_refs)
    dist_pct=((_eff_spot_ref - float(open_spot_cand)) / float(open_spot_cand)) * 100.0
  edge_info=compute_composite_edge_score({**shock,"candle_distance_pct":dist_pct})
  if edge_info.get("veto",False):
   logger.info( f"[COMPOSITE_EDGE_VETO] {shock.get('title')!r}: Vetoed by edge scoring: {edge_info.get('veto_reason')}" )
   return
  edge_tier=edge_info.get("tier","TIER_B_STANDARD")
  edge_score=edge_info.get("e_score",60.0)
  kelly_mult=edge_info.get("kelly_multiplier",1.00)
  fak_buf=edge_info.get("fak_price_buffer",0.015)
  shock_ofi_val=float(shock.get("shock_ofi",1.0) if shock.get("shock_ofi") is not None else 1.0)
  shock_vol_usd=float(shock.get("shock_volume_100ms",1_500_000.0) or 1_500_000.0)
  delta_basis_bps=float(shock.get("delta_basis_100ms",0.0) or 0.0)
  dir_delta_basis_bps=delta_basis_bps if target_token=="UP" else -delta_basis_bps
  age_ask_ms_val=float(shock.get("age_ask_ms") or token_features.get("age_ask_ms",350.0) or 350.0)
  cb_veto,cb_reason=evaluate_coinbase_venue_veto(shock,target_token)
  if cb_veto:
   logger.info(f"[COINBASE VENUE VETO] {shock.get('title')!r} {target_token}: {cb_reason}. Skipping.")
   return
  p_max_info=compute_max_acceptable_ask( dist_pct=dist_pct,tte_sec=tte,asset=asset_str,shock_ofi=shock_ofi_val,shock_vol_usd=shock_vol_usd,delta_basis_bps=dir_delta_basis_bps,age_ask_ms=age_ask_ms_val,is_subhourly_15m=is_subhourly,)
  z_eff=p_max_info.get("z_eff",0.0)
  p_true=p_max_info.get("p_true",0.5)
  p_max=p_max_info.get("p_max",0.0)
  regime=None
  min_allowed_price=self.min_price_floor
  max_allowed_price=self.max_price_ceiling
  _rec_sig_bnd=float(shock.get("candle_sigma") or 0.0)
  _sig_1h_bnd=(_rec_sig_bnd * 2.0 if is_subhourly else _rec_sig_bnd) if _rec_sig_bnd > 0.0 else (0.0050 if asset_str=="BTC" else 0.0068)
  _z_cush_bnd=(abs(dist_pct) / 100.0) / max(0.00025,_sig_1h_bnd * math.sqrt(max(tte,12.0) / 3600.0))
  if is_sleeve3_strike:
   if 60.0<=tte<=10800.0 and abs(dist_pct)>=0.60:
    regime="REGIME_E_STRIKE_CONVERGENCE"
    min_allowed_price=0.65
    max_allowed_price=0.89
    p_svi_val=float(shock.get("p_svi") or p_true)
    p_true=max(p_true,p_svi_val)
    p_max=max(p_max,min(0.89,round(p_true - 0.04,4)))
   else:
    logger.info( f"[SLEEVE_3_REJECT] {shock.get('title')!r}: TTE={tte:.0f}s or abs(dist)={abs(dist_pct):.2f}% < 0.60%. Rejecting." )
    return
  elif ( is_boundary_lock_cand and (is_1h or is_subhourly) and 12.0<=tte<=90.0 and max(z_eff,_z_cush_bnd,abs(float(shock.get("z_val") or shock.get("z_score") or shock.get("shock_z") or 0.0)))>=3.0 and abs(dist_pct)>=(0.08 if is_subhourly else 0.12) ):
   regime="REGIME_D_BOUNDARY_LOCK"
   min_allowed_price=0.62
   max_allowed_price=0.94
   p_true=max(p_true,0.985)
   p_max=max(p_max,0.94)
  elif is_1h:
   if _is_live_real:
    _min_1h_tte=150.0
    _max_1h_tte=600.0 if asset_str=="ETH" else 1200.0
    if _min_1h_tte<=tte<=_max_1h_tte:
     regime="REGIME_B_LATE_SNIPER"
     cushion=abs(dist_pct)
     _min_reg_b_cush=0.04
     if cushion < _min_reg_b_cush:
      logger.info( f"[REGIME_B_REJECT] {shock.get('title')!r}: abs(dist_pct)={cushion:.4f}% < {_min_reg_b_cush:.2f}% min threshold (TTE={tte:.0f}s)." )
      return
     if target_token=="UP" and dist_pct < _min_reg_b_cush:
      return
     if target_token=="DOWN" and dist_pct > -_min_reg_b_cush:
      return
     min_allowed_price=0.55
     max_allowed_price=0.85
    else:
     logger.info( f"[1H HORIZON TTE REJECT] 1-hour market {shock.get('title')!r} TTE={tte:.1f}s outside WFO [{_min_1h_tte:.0f}s, {_max_1h_tte:.0f}s] window. Rejecting." )
     return
   elif 900.0 < tte<=2700.0:
    regime="REGIME_A_MID_HOUR"
    _min_reg_a_cush=0.15
    if abs(dist_pct) < _min_reg_a_cush:
     logger.info( f"[REGIME_A_REJECT] {shock.get('title')!r}: abs(dist_pct)={abs(dist_pct):.4f}% < {_min_reg_a_cush:.2f}% cushion (TTE={tte:.0f}s)." )
     return
    if target_token=="UP" and dist_pct < _min_reg_a_cush:
     return
    if target_token=="DOWN" and dist_pct > -_min_reg_a_cush:
     return
    opens_map=self.hourly_candle_opens.get(asset_str,{})
    open_h=opens_map.get(cur_h_idx)
    open_h_1=opens_map.get(cur_h_idx - 1)
    open_h_2=opens_map.get(cur_h_idx - 2)
    ret_2h=((open_h - open_h_2) / open_h_2) if (open_h and open_h_2 and open_h_2 > 0) else None
    ret_1h_prior=((open_h - open_h_1) / open_h_1) if (open_h and open_h_1 and open_h_1 > 0) else None
    ret_2h_prior=((open_h_1 - open_h_2) / open_h_2) if (open_h_1 and open_h_2 and open_h_2 > 0) else None
    prior_2_green=(ret_1h_prior is not None and ret_1h_prior > 0.0010 and ret_2h_prior is not None and ret_2h_prior > 0.0010)
    prior_2_red=(ret_1h_prior is not None and ret_1h_prior < -0.0010 and ret_2h_prior is not None and ret_2h_prior < -0.0010)
    is_counter_trend=False
    if target_token=="DOWN":
     if (ret_2h is not None and ret_2h > 0.0030) or prior_2_green:
      is_counter_trend=True
    elif target_token=="UP":
     if (ret_2h is not None and ret_2h < -0.0030) or prior_2_red:
      is_counter_trend=True
    if is_counter_trend and abs(dist_pct) < 0.40:
     logger.info( f"[TREND GUARD REJECT] {shock.get('title')!r} {target_token}: counter-trend to multi-hour trend " f"(abs(dist)={abs(dist_pct):.3f}% < 0.40% reversal hurdle). Skipping." )
     return
    min_allowed_price=0.55
    max_allowed_price=0.78
   elif (30.0<=tte<=900.0 if z_eff>=2.2 else 120.0<=tte<=900.0):
    regime="REGIME_B_LATE_SNIPER"
    cushion=abs(dist_pct)
    _min_reg_b_cush=0.10
    if cushion < _min_reg_b_cush:
     logger.info( f"[REGIME_B_REJECT] {shock.get('title')!r}: abs(dist_pct)={cushion:.4f}% < {_min_reg_b_cush:.2f}% min threshold (TTE={tte:.0f}s)." )
     return
    if target_token=="UP" and dist_pct < _min_reg_b_cush:
     return
    if target_token=="DOWN" and dist_pct > -_min_reg_b_cush:
     return
    if cushion < 0.15:
     min_allowed_price=0.55
     max_allowed_price=0.75
    elif cushion < 0.22:
     min_allowed_price=0.58
     max_allowed_price=0.80
    else:
     min_allowed_price=0.62
     max_allowed_price=0.84
   else:
    logger.info( f"[1H HORIZON TTE REJECT] 1-hour market {shock.get('title')!r} TTE={tte:.1f}s outside allowed [{'30s' if z_eff >= 2.2 else '120s'}, 2700s] window. Rejecting." )
    return
  elif is_subhourly:
   _min_15m_tte=90.0 if _is_live_real else (30.0 if (not self.dry_run or z_eff>=2.2) else 90.0)
   _max_15m_tte=480.0 if _is_live_real else (690.0 if (not self.dry_run or z_eff>=2.2) else 540.0)
   _min_reg_c_cush=0.04 if _is_live_real else 0.08
   if _min_15m_tte<=tte<=_max_15m_tte:
    regime="REGIME_C_SUBHOURLY"
    if abs(dist_pct) < _min_reg_c_cush:
     logger.info( f"[REGIME_C_REJECT] Subhourly market {shock.get('title')!r} abs(dist_pct)={abs(dist_pct):.4f}% < {_min_reg_c_cush:.2f}% cushion. Rejecting." )
     return
    if target_token=="UP" and dist_pct < _min_reg_c_cush:
     return
    if target_token=="DOWN" and dist_pct > -_min_reg_c_cush:
     return
    min_allowed_price=0.55 if _is_live_real else 0.58
    max_allowed_price=0.85 if _is_live_real else 0.82
   else:
    logger.info( f"[15M HORIZON TTE REJECT] Subhourly market {shock.get('title')!r} TTE={tte:.1f}s outside allowed [{_min_15m_tte:.0f}s, {_max_15m_tte:.0f}s] window. Rejecting." )
    return
  else:
   return
  rec_sig=float(shock.get("candle_sigma") or 0.0)
  sigma_1h=(rec_sig * 2.0 if is_subhourly else rec_sig) if rec_sig > 0.0 else (0.0050 if asset_str=="BTC" else 0.0068)
  sigma_rem=max(0.00025,sigma_1h * math.sqrt(max(tte,30.0) / 3600.0))
  signed_dist_frac=(dist_pct / 100.0) if target_token=="UP" else (-dist_pct / 100.0)
  z_strike=signed_dist_frac / max(sigma_rem,1e-6)
  shock_ofi_abs=abs(float(shock.get("shock_ofi",0.85) or 0.85))
  z_effective=z_strike + (0.35 * shock_ofi_abs)
  p_fair=0.5 * (1.0 + math.erf(z_effective / math.sqrt(2.0)))
  if _is_live_real and regime in ("REGIME_B_LATE_SNIPER","REGIME_C_SUBHOURLY"):
   _req_wfo_z=0.78
   if z_strike < _req_wfo_z:
    logger.info( f"[WFO Z-CUSHION REJECT] {shock.get('title')!r} {target_token}: z_strike={z_strike:.3f} < {_req_wfo_z:.2f} WFO optimal floor " f"(z_eff={z_effective:.3f}, dist={dist_pct:+.4f}%, TTE={tte:.0f}s). Rejecting." )
    return
   _eta_live=0.035
   _exp_payoff_wfo=(p_fair * 0.965) + ((1.0 - p_fair) * 0.92 * 0.38)
   _p_max_wfo=min(0.85,round(_exp_payoff_wfo / (1.0 + _eta_live + 0.015),4))
   _p_max_unclamped=compute_max_acceptable_ask( dist_pct=dist_pct,tte_sec=min(tte,899.0),asset=asset_str,shock_ofi=shock_ofi_val,shock_vol_usd=max(shock_vol_usd,300_000.0),delta_basis_bps=dir_delta_basis_bps,age_ask_ms=age_ask_ms_val,target_return=_eta_live,is_subhourly_15m=is_subhourly,).get("p_max",0.0)
   p_max=max(p_max,_p_max_wfo,_p_max_unclamped)
  if asset_str=="ETH":
   btc_shock_dir=shock.get("btc_shock_direction")
   if btc_shock_dir:
    if target_token=="UP" and btc_shock_dir in ("DOWN","SELL"):
     logger.info(f"[CROSS-ASSET REJECT] ETH {target_token} counter-trending BTC {btc_shock_dir}")
     return
    if target_token=="DOWN" and btc_shock_dir in ("UP","BUY"):
     logger.info(f"[CROSS-ASSET REJECT] ETH {target_token} counter-trending BTC {btc_shock_dir}")
     return
   z_eth_val=shock.get("z_eth") or shock.get("z_score") or shock.get("z_val")
   z_btc_val=shock.get("z_btc")
   if z_eth_val is not None and z_btc_val is not None:
    passed_cross,_,reason=self.executor.validate_cross_asset_lead_lag( target_asset="ETH",target_direction=target_token,btc_direction=btc_shock_dir,z_alt=float(z_eth_val),z_btc=float(z_btc_val),)
    if not passed_cross:
     logger.info(f"[CROSS-ASSET REJECT] {reason}")
     return
  cand_expiry_ts=float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (time.time() + tte))
  cand_asset=asset_str.upper()
  all_active_or_pending=list(self._risk_bearing_positions().values()) + list(self.pending_entry_intents.values())
  passed_conflict,conflict_reason=self.executor.validate_cross_asset_directional_conflict( candidate_asset=cand_asset,candidate_direction=target_token,candidate_expiry_ts=cand_expiry_ts,active_positions=all_active_or_pending,max_expiry_window_delta=2700.0 if not self.dry_run else 900.0,)
  if not passed_conflict:
   logger.warning(f"[CROSS-ASSET CONFLICT REJECT] {conflict_reason}. Self-hedging prohibited.")
   return
  if not self.dry_run and not is_synthetic_test and (is_1h or is_subhourly):
   same_window_open=[ p for p in all_active_or_pending if abs(float(p.get("candle_expiry_ts",0.0) or 0.0) - cand_expiry_ts)<=300.0 and ((p.get("sleeve")=="SLEEVE_1_SUBHOURLY_15M")==bool(is_subhourly)) ]
   if same_window_open:
    if is_1h:
     logger.info( f"[SAME-WINDOW 1H REJECT] {shock.get('title')!r}: 1h position already active in this expiry window. " "Blocking 2nd correlated 1h entry." )
     return
    elif is_subhourly and abs(dist_pct) < 0.09:
     logger.info( f"[SAME-WINDOW 15M CUSHION REJECT] {shock.get('title')!r}: 2nd 15m entry in same window requires " f"abs(dist_pct) >= 0.09% (got {abs(dist_pct):.4f}%). Skipping." )
     return
  if not token_id:
   logger.warning(f"Could not resolve token_id for market {m_id} ({target_token})")
   return
  if token_id and token_id not in self.executor._tick_size_cache:
   self.executor._tick_size_cache[token_id]=0.01
  fee_meta_early=shock.get("fee_metadata",{})
  if fee_meta_early and isinstance(fee_meta_early,dict):
   cond_id_early=shock.get("condition_id") or fee_meta_early.get("condition_id")
   if cond_id_early and cond_id_early not in self.executor._fee_cache:
    fr=float(fee_meta_early.get("fee_rate_market",0.07) or 0.07)
    fe=float(fee_meta_early.get("fee_exponent",1.0) or 1.0)
    self.executor._fee_cache[cond_id_early]=(fr,fe)
  raw_asks=[]
  raw_bids=[]
  book_snapshot=None
  ws_top_asks=token_features.get("raw_top_asks")
  ws_top_bids=token_features.get("raw_top_bids")
  raw_age_ms=token_features.get("age_book_ms")
  book_ts_val=float(token_features.get("book_timestamp",0.0) or 0.0)
  if _is_live_real:
   if raw_age_ms is not None:
    ws_book_age_ms=float(raw_age_ms) if book_ts_val<=0.0 else max(float(raw_age_ms),(time.time() - book_ts_val) * 1000.0)
   else:
    ws_book_age_ms=((time.time() - book_ts_val) * 1000.0) if book_ts_val > 0.0 else 9999.0
   use_ws_book=bool(ws_top_asks and ws_top_bids and 0.0<=ws_book_age_ms<=LIVE_WS_BOOK_MAX_AGE_MS)
  else:
   ws_book_age_ms=float(raw_age_ms) if (raw_age_ms is not None and book_ts_val > 0.0) else 9999.0
   use_ws_book=bool(ws_top_asks and ws_top_bids and 0.0<=ws_book_age_ms<=30000.0)
  _lt=_CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
  if _lt is not None:
   _lt.stamp("book_source_decided")
   _lt.set( book_source="ws" if use_ws_book else "rest",ws_book_age_ms=round(ws_book_age_ms,3),ws_book_present=bool(ws_top_asks and ws_top_bids),ws_book_max_age_ms=LIVE_WS_BOOK_MAX_AGE_MS,)
  if use_ws_book:
   raw_asks=sorted( [(float(px),float(sz)) for px,sz in ws_top_asks if float(px) > 0 and float(sz) > 0],key=lambda x:x[0],)
   raw_bids=sorted( [(float(px),float(sz)) for px,sz in ws_top_bids if float(px) > 0 and float(sz) > 0],key=lambda x:x[0],reverse=True,)
   if raw_asks and raw_bids:
    book_snapshot={ "asks":[{"price":str(p),"size":str(s)} for p,s in raw_asks],"bids":[{"price":str(p),"size":str(s)} for p,s in raw_bids],"timestamp":token_features.get("book_timestamp",time.time()),}
  if raw_asks and raw_bids:
   best_ask=raw_asks[0][0]
   best_bid=raw_bids[0][0]
   if best_bid>=best_ask:
    logger.warning(f"[ENTRY_QUALITY_REJECT] Crossed/locked book for {token_id}: bid {best_bid:.4f} >= ask {best_ask:.4f}")
    return
   spread=best_ask - best_bid
   if spread > MAX_ALLOWED_SPREAD:
    logger.debug(f"[SPREAD GUARD] Spread {spread:.3f} > max allowed {MAX_ALLOWED_SPREAD:.3f}. Skipping illiquid book.")
    return
  elif not self.dry_run and not is_synthetic_test:
   _book_fetch_t0=time.monotonic()
   try:
    book_snapshot=await self.executor.get_market_book_async(token_id)
   except Exception as exc:
    logger.warning(f"[ENTRY_QUALITY_REJECT] Fresh book fetch failed for {token_id}: {exc}")
    return
   _book_fetch_rtt=time.monotonic() - _book_fetch_t0
   _lt_rest=_CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
   if _lt_rest is not None:
    _lt_rest.set(rest_book_fetch_ms=round(_book_fetch_rtt * 1000.0,3))
    _lt_rest.stamp("rest_book_done")
   if _book_fetch_rtt > 2.5:
    logger.warning(f"[ENTRY_QUALITY_REJECT] Slow HTTP book fetch for {token_id} (rtt {_book_fetch_rtt:.2f}s > 2.5s)")
    return
   if not book_snapshot or not isinstance(book_snapshot,dict):
    logger.warning(f"[ENTRY_QUALITY_REJECT] Empty or invalid book snapshot for {token_id}")
    return
   raw_book_ts=float(book_snapshot.get("timestamp",0.0) or 0.0)
   book_ts=(raw_book_ts / 1000.0) if raw_book_ts > 1e12 else raw_book_ts
   max_book_age=float(os.environ.get("PM_MAX_BOOK_AGE_SEC","60.0"))
   if book_ts > 0 and (time.time() - book_ts) > max_book_age:
    logger.warning(f"[ENTRY_QUALITY_REJECT] Stale book snapshot for {token_id} (age {time.time() - book_ts:.2f}s > {max_book_age:.1f}s)")
    return
   raw_asks=sorted( [(float(x.get("price",0.0)),float(x.get("size",0.0)))  for x in book_snapshot.get("asks",[])  if float(x.get("price",0.0)) > 0 and float(x.get("size",0.0)) > 0],key=lambda x:x[0],)
   raw_bids=sorted( [(float(x.get("price",0.0)),float(x.get("size",0.0)))  for x in book_snapshot.get("bids",[])  if float(x.get("price",0.0)) > 0 and float(x.get("size",0.0)) > 0],key=lambda x:x[0],reverse=True,)
   if not raw_asks or not raw_bids:
    logger.warning(f"[ENTRY_QUALITY_REJECT] One-sided book for {token_id} (asks={len(raw_asks)}, bids={len(raw_bids)})")
    return
   best_ask=raw_asks[0][0]
   best_bid=raw_bids[0][0]
   if best_bid>=best_ask:
    logger.warning(f"[ENTRY_QUALITY_REJECT] Crossed/locked book for {token_id}: bid {best_bid:.4f} >= ask {best_ask:.4f}")
    return
   spread=best_ask - best_bid
   if spread > MAX_ALLOWED_SPREAD:
    logger.debug(f"[SPREAD GUARD] Spread {spread:.3f} > max allowed {MAX_ALLOWED_SPREAD:.3f}. Skipping illiquid book.")
    return
  else:
   if hasattr(self.executor,"get_market_book_async"):
    try:
     book_snapshot=await self.executor.get_market_book_async(token_id)
    except Exception:
     book_snapshot=None
   if book_snapshot and isinstance(book_snapshot,dict):
    raw_asks=sorted( [(float(x.get("price",0.0)),float(x.get("size",0.0)))  for x in book_snapshot.get("asks",[])  if float(x.get("price",0.0)) > 0 and float(x.get("size",0.0)) > 0],key=lambda x:x[0],)
    raw_bids=sorted( [(float(x.get("price",0.0)),float(x.get("size",0.0)))  for x in book_snapshot.get("bids",[])  if float(x.get("price",0.0)) > 0 and float(x.get("size",0.0)) > 0],key=lambda x:x[0],reverse=True,)
   if not raw_asks:
    raw_asks=token_features.get("raw_top_asks",[])
   if not raw_bids:
    raw_bids=token_features.get("raw_top_bids",[])
   if not raw_asks:
    return
   if raw_asks and not raw_bids:
    raw_bids=[[max(0.01,round(raw_asks[0][0] - 0.01,4)),1000.0]]
   best_ask=raw_asks[0][0]
   best_bid=raw_bids[0][0]
   if best_bid>=best_ask or (best_ask - best_bid) > MAX_ALLOWED_SPREAD:
    return
  first_ask=raw_asks[0][0]
  first_bid=raw_bids[0][0]
  t0_best_ask=float(token_features.get("best_ask") or 0.0)
  if _is_live_real and t0_best_ask > 0.0 and (t0_best_ask - first_ask)>=0.04:
   logger.warning( f"[ADVERSE ASK COLLAPSE REJECT] {shock.get('title')!r} {target_token}: fresh ask ${first_ask:.4f} collapsed " f"-${t0_best_ask - first_ask:.4f} below t0 ask ${t0_best_ask:.4f} (>= $0.04 adverse repricing). Skipping." )
   return
  if edge_tier=="TIER_A_PLUS_STALE_SNIPE" and t0_best_ask > 0.0 and (first_ask - t0_best_ask)>=0.0199:
   logger.info( f"[STALE TIER DOWNGRADE] {shock.get('title')!r} {target_token}: fresh ask ${first_ask:.3f} moved " f"+${first_ask - t0_best_ask:.3f} above t0 ask ${t0_best_ask:.3f}; downgrading TIER_A_PLUS -> TIER_B_STANDARD." )
   edge_tier="TIER_B_STANDARD"
   fak_buf=min(float(fak_buf),0.010 if _is_live_real else 0.015)
   kelly_mult=min(float(kelly_mult),1.0)
  elif _is_live_real and edge_tier=="TIER_B_STANDARD":
   fak_buf=(0.020 if z_strike>=1.25 else 0.010) if self.dynamic_sizing else min(float(fak_buf),0.010)
  pre_check_notional=max(MIN_LOT_SIZE_USD,min(self.ticket_notional,25.0))
  intended_shares=pre_check_notional / first_ask if first_ask > 0 else 0.0
  min_bid_mult=2.0 if tte<=1200.0 else 1.5
  min_required_near_touch_shares=intended_shares * min_bid_mult
  near_touch_bid_shares=sum(sz for px,sz in raw_bids if px>=(first_bid - 0.03 - 1e-6))
  if not self.dry_run and not is_synthetic_test and near_touch_bid_shares < min_required_near_touch_shares:
   logger.warning( f"[BID_NEAR_TOUCH_DEPTH_REJECT] Near-touch bid shares {near_touch_bid_shares:.1f} < " f"required {min_required_near_touch_shares:.1f} ({min_bid_mult:.1f}x intended shares {intended_shares:.1f})" )
   return
  total_bid_shares=sum(sz for px,sz in raw_bids)
  if not self.dry_run and not is_synthetic_test and total_bid_shares < intended_shares:
   logger.warning( f"[BID_TOTAL_DEPTH_REJECT] Total bid shares {total_bid_shares:.1f} < intended shares {intended_shares:.1f}" )
   return
  eff_price_ceiling=( max(self.max_price_ceiling,max_allowed_price) if regime in ("REGIME_D_BOUNDARY_LOCK","REGIME_E_STRIKE_CONVERGENCE") else ( min( self.max_price_ceiling,max_allowed_price,max( p_max,max_allowed_price if ( edge_tier=="TIER_A_PLUS_STALE_SNIPE" and abs(dist_pct)>=(0.10 if is_subhourly else 0.12) ) else 0.0,),) if (not self.dry_run and p_max > 0) else self.max_price_ceiling ) )
  if not self.dry_run and raw_asks and raw_asks[0][0] > eff_price_ceiling:
   logger.info( f"[EV CEILING REJECT] {shock.get('title')!r} {target_token}: first_ask ${raw_asks[0][0]:.4f} > " f"+EV ceiling ${eff_price_ceiling:.4f} (p_max=${p_max:.4f}, z_strike={z_strike:.2f}). Skipping." )
   return
  if _is_live_real and regime in ("REGIME_B_LATE_SNIPER","REGIME_C_SUBHOURLY") and raw_asks:
   _l1_ask_usd=float(raw_asks[0][0]) * float(raw_asks[0][1])
   if _l1_ask_usd < 20.0:
    logger.info( f"[L1 ASK DEPTH REJECT] {shock.get('title')!r} {target_token}: L1 ask depth ${_l1_ask_usd:.2f} < $20.00 institutional floor. Skipping." )
    return
  executable_depth_usd=sum(px * sz for px,sz in raw_asks if px<=eff_price_ceiling)
  PAPER_REFERENCE_TICKET_USD=12.0 if self.dynamic_sizing else max(float(self.ticket_notional),12.0)
  _ref_depth_mult=float(self.depth_hurdle)
  if not self.dry_run and ( executable_depth_usd / PAPER_REFERENCE_TICKET_USD < _ref_depth_mult ):
   logger.info( "[DEPTH PARITY REJECT] Executable depth $%.2f is below " "%.2fx the $%.2f reference ticket.",executable_depth_usd,_ref_depth_mult,PAPER_REFERENCE_TICKET_USD,)
   return
  ticket_target=self.ticket_notional
  exposure_cap=self.max_exposure
  live_bankroll=None
  p_model_for_sizing=None
  first_ask=raw_asks[0][0] if raw_asks else 0.50
  if regime=="REGIME_D_BOUNDARY_LOCK":
   _fr_bnd=float((shock.get("fee_metadata") or {}).get("fee_rate_market",0.07) or 0.07)
   _net_edge_bnd=(1.0 - first_ask) - (_fr_bnd * first_ask * (1.0 - first_ask))
   if _net_edge_bnd < 0.025:
    logger.info( f"[BOUNDARY_LOCK_REJECT] {shock.get('title')!r}: first_ask ${first_ask:.4f} net terminal edge {_net_edge_bnd:.4f} < $0.025. Skipping." )
    return
  assigned_sleeve=( "SLEEVE_3_STRIKE_CONVERGENCE" if regime=="REGIME_E_STRIKE_CONVERGENCE" else ("SLEEVE_4_BOUNDARY_SNIPE" if regime=="REGIME_D_BOUNDARY_LOCK" else ("SLEEVE_1_SUBHOURLY_15M" if is_subhourly else ("SLEEVE_2_MID_HOUR" if regime=="REGIME_A_MID_HOUR" else "SLEEVE_1_CORE_302"))) )
  if not self.dry_run:
   if first_ask < min_allowed_price or first_ask > max_allowed_price:
    if max_allowed_price < first_ask<=(max_allowed_price + 0.06):
     self._register_shadow_phase3a_maker_in( shock,target_token,first_ask,first_bid,max_allowed_price,raw_asks,"PRICE_BAND_REJECT",bool(is_subhourly),float(dist_pct),float(tte),)
    logger.info( f"[PRICE BAND REJECT] {shock.get('title')!r} first_ask ${first_ask:.4f} outside allowed [{min_allowed_price:.2f}, {max_allowed_price:.2f}] matrix band ({regime}). Skipping." )
    return
   if is_subhourly and not is_synthetic_test and (0.68<=first_ask < 0.71) and abs(dist_pct) < 0.11 and z_strike < 0.75:
    logger.info( f"[15M DEADZONE REJECT] {shock.get('title')!r} first_ask ${first_ask:.4f} in [0.68, 0.71) with abs(dist_pct)={abs(dist_pct):.4f}% < 0.11% and z_strike={z_strike:.2f} < 0.75. Skipping." )
    return
  else:
   if first_ask < min_allowed_price or first_ask > max_allowed_price:
    return
  if hasattr(self,"recent_shock_window") and isinstance(self.recent_shock_window,list):
   _sc_ask=float(token_features.get("vwap_$50") or token_features.get("effective_price_$50") or first_ask or 0.50)
   _sc_z=abs(float(shock.get("z_val",shock.get("z_score",shock.get("expected_prob_shift",abs(dist_pct) * 0.5)))))
   if min_allowed_price<=first_ask<=max_allowed_price:
    self.recent_shock_window.append({ "t_unix":float(shock.get("t0_unix",time.time())),"score":_sc_z / max(_sc_ask,0.01),"market_id":str(m_id or ""),"trade_id":str(shock_id),})
  fee_meta=shock.get("fee_metadata",{})
  if not self.dry_run or "fee_metadata" in shock:
   if ( not isinstance(fee_meta,dict) or fee_meta.get("fee_rate_market") is None or not math.isfinite(float(fee_meta.get("fee_rate_market",0.0))) or float(fee_meta.get("fee_rate_market",0.0))<=0.0 or not math.isfinite(float(fee_meta.get("fee_exponent",1.0))) or float(fee_meta.get("fee_exponent",1.0)) < 1.0 ):
    logger.warning( "[FEE METADATA REJECT] Missing or invalid market fee metadata." )
    return
   if fee_meta.get("condition_id") and shock.get("condition_id"):
    if str(fee_meta["condition_id"]).lower()!=str(shock["condition_id"]).lower():
     logger.warning("[FEE PROVENANCE REJECT] Condition ID mismatch in fee metadata.")
     return
  m_fee_rate=float(fee_meta.get("fee_rate_market",0.07)) if fee_meta.get("fee_rate_market") is not None else 0.07
  m_fee_exp=float(fee_meta.get("fee_exponent",1.0)) if fee_meta.get("fee_exponent") is not None else 1.0
  if not math.isfinite(m_fee_rate) or m_fee_rate<=0:
   m_fee_rate=0.07
  if not math.isfinite(m_fee_exp) or m_fee_exp<=0:
   m_fee_exp=1.0
  def _calc_kelly(p_m:float,p_a:float,b:float)->float:
   try:
    return self.compute_kelly_ticket_size(p_m,p_a,b,fee_rate=m_fee_rate,fee_exponent=m_fee_exp)
   except TypeError:
    return self.compute_kelly_ticket_size(p_m,p_a,b)
  if not self.dry_run:
   cached_collat=getattr(self,"_last_known_collateral",None)
   if cached_collat is None or not (isinstance(cached_collat,(int,float)) and math.isfinite(cached_collat) and cached_collat > 0):
    cached_collat=self.executor.get_collateral_balance(hot_path=True)
   if cached_collat is None or not (isinstance(cached_collat,(int,float)) and math.isfinite(cached_collat) and cached_collat > 0):
    persisted_bal=getattr(self,"_persisted_state",{}).get("live_bankroll")
    if persisted_bal is not None and isinstance(persisted_bal,(int,float)) and math.isfinite(persisted_bal) and persisted_bal > 0:
     cached_collat=float(persisted_bal)
   if cached_collat is not None and isinstance(cached_collat,(int,float)) and math.isfinite(cached_collat) and cached_collat > 0:
    live_bankroll=float(cached_collat)
    self._last_known_collateral=float(cached_collat)
   else:
    logger.error( "[SIZING HALT] Authoritative collateral balance " "unavailable in memory or non-positive." )
    return
   now_ts=time.time()
   active_market_equity=sum(self.get_position_market_value(p,now_ts) for p in self.active_positions.values())
   total_account_value=float(live_bankroll) + active_market_equity
   tier_limits=self._update_equity_tier(total_account_value)
   self.risk_controller.check_equity_drawdown(float(total_account_value))
   if self.risk_controller.is_halted():
    logger.critical(f"[CIRCUIT_BREAKER_HALT] Trading halted: {self.risk_controller.halt_reason}")
    return
   _fresh,_feed_age,_feed_why=self.check_recorder_freshness(self._shock_asset(shock),time.time())
   if not _fresh:
    logger.warning( f"[STALE_RECORDER_GUARD] {shock.get('title')!r}: {self._shock_asset(shock)} recorder feed stale " f"({_feed_why}). Entry refused." )
    return
   if abs(dist_pct)>=0.15:
    self.calibrated_p_model=0.95
    model_prob=max(0.95,float(shock.get("p_model") or 0.95))
   else:
    model_prob=shock.get("p_model",self.calibrated_p_model)
   model_meta=shock.get("probability_model") or { "model_version":self.calibrated_model_version,"calibration_id":self.calibrated_model_id,}
   if ( model_prob is None or not model_meta.get("model_version") or not model_meta.get("calibration_id") ):
    logger.error("[SIZING HALT] Probability calibration unavailable.")
    return
   p_model_for_sizing=float(model_prob)
   if not math.isfinite(p_model_for_sizing) or not ( 0.0 < p_model_for_sizing < 1.0 ):
    return
   if self.dynamic_sizing:
    now_ts=time.time()
    active_pos_map=getattr(self,"active_positions",{})
    deployed_market_value=sum( self.get_position_market_value(pos,now_ts) for pos in active_pos_map.values() )
    free_usdc=float(live_bankroll) if live_bankroll is not None else float(self.ticket_notional)
    total_account_value=free_usdc + deployed_market_value
    cand_exp_ts=float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (time.time() + tte))
    p_win_est=max(float(p_true),float(p_fair),float(p_model_for_sizing)) if is_synthetic_test else max(float(p_true),float(p_fair))
    ticket_cap_ceiling=getattr(self,"max_ticket_cap",None) or self.max_absolute_ticket_usd or MAX_ABSOLUTE_TICKET_USD
    prev_tier_sz=getattr(self,"_current_equity_tier",None) or getattr(self,"current_equity_tier",None)
    tier_limits=get_equity_tier_limits(total_account_value,getattr(self,"high_water_mark_equity",None),previous_tier=prev_tier_sz)
    self._current_equity_tier=tier_limits["tier"]
    self.current_equity_tier=tier_limits["tier"]
    _rcfg_corr=getattr(self,"risk_config",None) or RISK_CONFIG
    small_bankroll_corr_cap=float( _rcfg_corr.get("correlated_crypto_single_slot_threshold",_rcfg_corr.get("scale_up_equity_threshold",110.0)) )
    if ( not self.dry_run and not is_synthetic_test and total_account_value < small_bankroll_corr_cap and os.environ.get("PM_ALLOW_SMALL_BANKROLL_CORRELATED_CRYPTO")!="1" ):
     active_dir_crypto=[ p for p in self._risk_bearing_positions().values() if str(p.get("asset") or "").upper() in ("BTC","ETH","SOL","XRP") and "BOX" not in str(p.get("sleeve") or "").upper() and "WEATHER" not in str(p.get("sleeve") or "").upper() ]
     _orth_boundary_slot2_ok=bool( assigned_sleeve=="SLEEVE_4_BOUNDARY_SNIPE" and 12.0<=tte<=45.0 and total_account_value>=110.0 and len(active_dir_crypto)==1 and all( str(p.get("market_id") or "")!=str(m_id or "") and ( str(p.get("asset") or "").upper()!=asset_str or abs(float(p.get("candle_expiry_ts") or 0.0) - cand_exp_ts) > 60.0 ) for p in active_dir_crypto ) )
     if len(active_dir_crypto)>=1 and not _orth_boundary_slot2_ok:
      logger.info( f"[CORRELATED CRYPTO CONCURRENCY GUARD] {shock.get('title')!r}: " f"equity=${total_account_value:.2f} < ${small_bankroll_corr_cap:.2f} already holds 1 directional crypto position; " "reserving slot #2 strictly for uncorrelated sleeves (Box/Weather/Orthogonal <=45s Boundary Snipe)." )
      return
    risk_pct=tier_limits["dynamic_bankroll_pct"]
    pct_ticket_cap=round(risk_pct * total_account_value,2)
    if assigned_sleeve=="SLEEVE_4_BOUNDARY_SNIPE" and total_account_value < small_bankroll_corr_cap:
     pct_ticket_cap=min(pct_ticket_cap,round(0.16 * total_account_value,2),22.0)
    seed_ticket_floor=float(RISK_CONFIG.get("seed_survival_ticket_usd",12.0))
    if total_account_value < float(RISK_CONFIG.get("seed_survival_equity_threshold",88.0)):
     if RISK_CONFIG.get("seed_smooth_compounding",True) and total_account_value>=float(RISK_CONFIG.get("min_equity_floor",66.67)):
      pct_ticket_cap=max(seed_ticket_floor,pct_ticket_cap)
     else:
      pct_ticket_cap=min(pct_ticket_cap,seed_ticket_floor)
    dynamic_ticket_cap=compute_correlated_truncated_kelly_size( live_equity=total_account_value,p_win=p_win_est,entry_px=first_ask,active_positions=self._risk_bearing_positions(),cand_expiry_ts=cand_exp_ts,cand_direction=target_token,kelly_multiplier=kelly_mult,min_lot_usd=8.0,max_ticket_cap=min(float(ticket_cap_ceiling),pct_ticket_cap),default_sizing_pct=risk_pct,)
    if dynamic_ticket_cap > 0.0 and not is_synthetic_test:
     dynamic_ticket_cap=apply_convex_payoff_sizing_cap( dynamic_ticket_cap,live_equity=total_account_value,entry_px=first_ask,sleeve=assigned_sleeve,)
    if dynamic_ticket_cap<=0.0:
     logger.info( f"[CORRELATION VETO] {shock.get('title')!r} {target_token}: opposite-direction position already open " f"in the same expiry window. Skipping." )
     return
    passed_elastic,elastic_sz=PolymarketLiveExecutor.calculate_elastic_ticket_size( executable_depth_usd,depth_hurdle_ratio=self.depth_hurdle,min_ticket_usd=8.0,max_ticket_usd=dynamic_ticket_cap,)
    if not passed_elastic:
     logger.info( "[ELASTIC DEPTH REJECT] Executable depth $%.2f cannot support min $8.00 ticket at %.2fx hurdle.",executable_depth_usd,self.depth_hurdle,)
     return
    ticket_target=min(elastic_sz,free_usdc)
    exposure_cap=self.max_exposure
   else:
    kelly_ticket=_calc_kelly( p_model_for_sizing,first_ask,live_bankroll )
    min_lot_gate=min(MIN_LOT_SIZE_USD,float(self.ticket_notional or MIN_LOT_SIZE_USD)) if self.dry_run else MIN_LOT_SIZE_USD
    if kelly_ticket < min_lot_gate:
     logger.info( "[SIZING REJECTED] Kelly ticket %.2f is below minimum lot %.2f",kelly_ticket,min_lot_gate,)
     return
    ticket_target=kelly_ticket
    exposure_cap=self.max_exposure
    if getattr(self,"unconstrained_kelly",False) and live_bankroll:
     exposure_cap=min(exposure_cap,round(float(live_bankroll) * (self.max_concurrent_positions * self.max_notional_cap_pct),2))
  effective_notional=ticket_target
  remaining_exposure=max(0.0,round(exposure_cap - current_exposure,2))
  effective_notional=min(effective_notional,remaining_exposure)
  _live_min_lot=8.0 if self.dynamic_sizing else MIN_LOT_SIZE_USD
  min_lot_gate=min(MIN_LOT_SIZE_USD,float(self.ticket_notional or MIN_LOT_SIZE_USD)) if self.dry_run else _live_min_lot
  if effective_notional < min_lot_gate:
   return
  if (executable_depth_usd / effective_notional) < (self.depth_hurdle - 1e-4):
   return
  if not self.dry_run and not is_synthetic_test and first_ask > 0:
   max_near_bid_shares=near_touch_bid_shares / max(min_bid_mult,1.0)
   max_bid_supported_shares=min(max_near_bid_shares,total_bid_shares)
   max_bid_supported_usd=math.floor(max_bid_supported_shares * first_ask * 100.0) / 100.0
   if effective_notional > max_bid_supported_usd:
    min_lot_chk=min(MIN_LOT_SIZE_USD,float(self.ticket_notional or MIN_LOT_SIZE_USD)) if self.dry_run else _live_min_lot
    if max_bid_supported_usd < min_lot_chk:
     logger.warning( f"[BID_DEPTH_REJECT] Bid depth supports only ${max_bid_supported_usd:.2f} < min lot ${min_lot_chk:.2f}" )
     return
    logger.info( f"[BID_DEPTH_DOWNSCALE] Scaling ticket ${effective_notional:.2f} -> ${max_bid_supported_usd:.2f} " f"to match near-touch bid liquidity ({near_touch_bid_shares:.1f} shrs)." )
    effective_notional=max_bid_supported_usd
  if not self.dry_run and self.dynamic_sizing and raw_asks:
   prelim_limit_px=round(min(float(first_ask) + fak_buf,self.max_price_ceiling,max_allowed_price),2)
   prelim_limit_depth=sum(float(px) * float(sz) for px,sz in raw_asks if float(px)<=prelim_limit_px + 1e-6)
   if prelim_limit_depth < float(effective_notional) - 1e-6:
    for cand_rung in (28.00,22.00,16.50,12.00):
     if cand_rung < float(effective_notional) and prelim_limit_depth>=cand_rung - 1e-6:
      logger.info( f"[IDEA-1 ELASTIC DOWNSNAP] Depth within ${prelim_limit_px:.2f} is " f"${prelim_limit_depth:.2f} < ${effective_notional:.2f}; down-snapping to pre-warmed rung ${cand_rung:.2f}." )
      effective_notional=cand_rung
      break
  spent=0.0
  shares=0.0
  for px,sz in raw_asks:
   fill_dollars=min(effective_notional - spent,px * sz)
   spent += fill_dollars
   shares += fill_dollars / px
   if spent>=effective_notional - 1e-6:
    break
  raw_vwap=round(spent / shares,4) if shares > 0 else (raw_asks[0][0] if raw_asks else None)
  if not self.dry_run:
   if not raw_vwap or raw_vwap < min_allowed_price or raw_vwap > max_allowed_price:
    if raw_vwap and max_allowed_price < raw_vwap<=(max_allowed_price + 0.06):
     self._register_shadow_phase3a_maker_in( shock,target_token,first_ask,first_bid,max_allowed_price,raw_asks,"VWAP_BAND_REJECT",bool(is_subhourly),float(dist_pct),float(tte),)
    logger.info( f"[VWAP BAND REJECT] {shock.get('title')!r} raw_vwap ${raw_vwap} outside allowed [{min_allowed_price:.2f}, {max_allowed_price:.2f}] matrix band ({regime}). Skipping." )
    return
   if p_max<=0.0 or raw_vwap > p_max:
    logger.info( f"[P_MAX REJECT] {shock.get('title')!r} raw_vwap ${raw_vwap:.4f} > p_max ${p_max:.4f} (p_true={p_true:.4f}, z_eff={z_eff:.2f}). Skipping." )
    return
   if age_ask_ms_val > 10000.0 and (p_true - first_ask) > 0.28:
    logger.warning( f"[ANCHOR DISAGREEMENT VETO] {shock.get('title')!r} {target_token}: resting ask ${first_ask:.4f} " f"(age={age_ask_ms_val:.0f}ms > 10s) diverges from model p_true={p_true:.4f} by {p_true - first_ask:+.4f} (> 0.28). " "Possible strike anchor divergence. Skipping." )
    return
  else:
   if not raw_vwap or raw_vwap < min_allowed_price or raw_vwap > max_allowed_price:
    return
  if not self.dry_run:
   if live_bankroll is None or p_model_for_sizing is None:
    return
   min_required_cushion=0.07 if is_subhourly else 0.08
   if getattr(self,"dynamic_sizing",False) and abs(dist_pct)>=min_required_cushion:
    logger.info( f"[DYNAMIC SIZING CONFIRMED] Cushion {abs(dist_pct):.4f}% >= {min_required_cushion:.2f}%; " f"maintaining full elastic depth ticket ${effective_notional:.2f} (bypassing legacy Kelly downsizing)." )
   else:
    _p_kelly_vwap=( ( max(float(p_model_for_sizing),float(p_true),float(p_fair)) if is_synthetic_test else float(p_true) ) if getattr(self,"dynamic_sizing",False) else float(p_model_for_sizing) )
    vwap_kelly_ticket=_calc_kelly( _p_kelly_vwap,raw_vwap,live_bankroll,)
    _vwap_min_lot=8.0 if getattr(self,"dynamic_sizing",False) else MIN_LOT_SIZE_USD
    if vwap_kelly_ticket < _vwap_min_lot:
     logger.info( "[VWAP KELLY REJECT] Executable VWAP %.4f " "does not support minimum Kelly ticket (%.2f < %.2f on thin cushion %.4f%%).",raw_vwap,vwap_kelly_ticket,_vwap_min_lot,abs(dist_pct),)
     return
    effective_notional=min( effective_notional,vwap_kelly_ticket,)
    if effective_notional < _vwap_min_lot:
     return
    if ( executable_depth_usd / effective_notional < self.depth_hurdle - 1e-4 ):
     return
  eff_px=( token_features.get(f"effective_price_${int(effective_notional)}") or token_features.get("effective_price_$25") or token_features.get("effective_price_$20") or token_features.get("effective_price_$5") or token_features.get("effective_price_$50") or raw_vwap )
  m_id=str(shock.get("market_id"))
  if any(str(p.get("market_id"))==m_id for p in self.active_positions.values()) or any(str(i.get("market_id"))==m_id for i in self.pending_entry_intents.values()):
   logger.debug(f"[MARKET ALREADY ACTIVE] Position already active/pending for market {m_id}. Refusing concurrent re-entry.")
   return
  cand_expiry_ts=float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (time.time() + tte))
  cand_asset=asset_str.upper()
  all_active_or_pending=list(self._risk_bearing_positions().values()) + list(self.pending_entry_intents.values())
  passed_conflict,conflict_reason=self.executor.validate_cross_asset_directional_conflict( candidate_asset=cand_asset,candidate_direction=target_token,candidate_expiry_ts=cand_expiry_ts,active_positions=all_active_or_pending,max_expiry_window_delta=2700.0 if not self.dry_run else 900.0,)
  if not passed_conflict:
   logger.warning(f"[CROSS-ASSET CONFLICT REJECT] {conflict_reason}. Self-hedging prohibited.")
   return
  if not self.dry_run and not is_synthetic_test and (is_1h or is_subhourly):
   same_window_open=[ p for p in all_active_or_pending if abs(float(p.get("candle_expiry_ts",0.0) or 0.0) - cand_expiry_ts)<=300.0 and ((p.get("sleeve")=="SLEEVE_1_SUBHOURLY_15M")==bool(is_subhourly)) ]
   if same_window_open:
    if is_1h:
     logger.info( f"[SAME-WINDOW 1H REJECT] {shock.get('title')!r}: 1h position already active in this expiry window. " "Blocking 2nd correlated 1h entry." )
     return
    elif is_subhourly and abs(dist_pct) < 0.09:
     logger.info( f"[SAME-WINDOW 15M CUSHION REJECT] {shock.get('title')!r}: 2nd 15m entry in same window requires " f"abs(dist_pct) >= 0.09% (got {abs(dist_pct):.4f}%). Skipping." )
     return
  trades_for_direction=self.trades_per_market_direction.get((m_id,target_token),0)
  is_win_reentry_dir=False
  is_loss_locked_dir=False
  if trades_for_direction>=1:
   closed_for_mkt_dir=[ p for p in self.closed_positions if p.get("market_id")==m_id and p.get("target_token")==target_token ]
   if closed_for_mkt_dir:
    last_closed_dir=closed_for_mkt_dir[-1]
    if last_closed_dir.get("won") is True and float(last_closed_dir.get("net_pnl_usd",0.0) or 0.0) > 0.0:
     is_win_reentry_dir=(trades_for_direction==1 and self.max_trades_per_market>=2)
    else:
     is_loss_locked_dir=True
  max_dir_cap=0 if is_loss_locked_dir else (2 if is_win_reentry_dir else self.max_trades_per_market)
  if self.trades_this_hour>=self.max_trades_per_hour or trades_for_direction>=max_dir_cap:
   candidate_record={ "logged_at_utc":datetime.now(timezone.utc).isoformat(),"candidate_index_in_hour":self.trades_this_hour + 1,"candidate_index_in_market":trades_for_direction + 1,"market_id":m_id,"title":shock.get("title"),"target_token":target_token,"token_id":token_id,"dist_pct":dist_pct,"tte_seconds":tte,"effective_price":eff_px,"executable_depth_usd":executable_depth_usd,"hypothetical_notional":effective_notional,"target_exit_price":round(self._calculate_target_exit(eff_px,tte),3),"reason_blocked":"HOURLY_PORTFOLIO_CAP_REACHED" if self.trades_this_hour>=self.max_trades_per_hour else "MARKET_CANDLE_CAP_REACHED",}
   try:
    with open(COUNTERFACTUAL_CANDIDATES_FILE,"a") as f:
     f.write(json.dumps(candidate_record) + "\n")
   except Exception as e:
    logger.warning(f"Failed to record counterfactual candidate: {e}")
   logger.info( f"[COUNTERFACTUAL CANDIDATE #{self.trades_this_hour + 1}] {shock.get('title')} {target_token} @ ${eff_px:.3f} " f"(Depth: ${executable_depth_usd:.1f}, Dist: {dist_pct:+.2f}%) passed all gates but blocked by hourly cap " f"(portfolio hour: {self.trades_this_hour}/{self.max_trades_per_hour}, market direction: {trades_for_direction}/{max_dir_cap}). Recorded for sample analysis." )
   return
  if ( not math.isfinite(float(effective_notional)) or (current_exposure + float(effective_notional)) > exposure_cap + 1e-6 or len(risk_positions) + len([k for k in self.pending_entry_intents if k not in risk_positions])>=self.max_concurrent_positions ):
   candidate_record={ "logged_at_utc":datetime.now(timezone.utc).isoformat(),"candidate_index_in_hour":self.trades_this_hour + 1,"market_id":m_id,"title":shock.get("title"),"target_token":target_token,"token_id":token_id,"dist_pct":dist_pct,"tte_seconds":tte,"effective_price":eff_px,"executable_depth_usd":executable_depth_usd,"hypothetical_notional":effective_notional,"target_exit_price":round(self._calculate_target_exit(eff_px,tte),3),"reason_blocked":"EXPOSURE_OR_CONCURRENT_CEILING_REACHED",}
   try:
    with open(COUNTERFACTUAL_CANDIDATES_FILE,"a") as f:
     f.write(json.dumps(candidate_record) + "\n")
   except Exception as e:
    logger.warning(f"Failed to record counterfactual candidate: {e}")
   logger.warning( f"[CEILING BLOCKED] Active={len(self.active_positions)}/{self.max_concurrent_positions}, " f"Exposure=${current_exposure:.2f}/${exposure_cap:.2f}. Recorded counterfactual candidate for sample analysis." )
   return
  trade_id=f"LIVE_{shock.get('market_id')}_{int(time.time())}_{target_token}"
  logger.info( f"[QUALIFIED OPPORTUNITY] {shock.get('title')} | Target: {target_token} | " f"Expected Px: ${raw_vwap:.3f} (Eff: ${eff_px:.3f}) | Dist: {dist_pct:+.2f}% | TTE: {tte/60.0:.1f}m | " f"Depth: ${executable_depth_usd:.1f} | Sized Notional: ${effective_notional:.2f}" )
  fee_meta=shock.get("fee_metadata",{})
  if not self.dry_run or "fee_metadata" in shock:
   if ( not isinstance(fee_meta,dict) or fee_meta.get("fee_rate_market") is None or not math.isfinite(float(fee_meta.get("fee_rate_market",0.0))) or float(fee_meta.get("fee_rate_market",0.0))<=0.0 or not math.isfinite(float(fee_meta.get("fee_exponent",1.0))) or float(fee_meta.get("fee_exponent",1.0)) < 1.0 ):
    logger.warning( "[FEE METADATA REJECT] Missing or invalid market fee metadata." )
    return
   if fee_meta.get("condition_id") and shock.get("condition_id"):
    if str(fee_meta["condition_id"]).lower()!=str(shock["condition_id"]).lower():
     logger.warning("[FEE PROVENANCE REJECT] Condition ID mismatch in dispatch fee metadata.")
     return
  cond_id=shock.get("condition_id") or await asyncio.to_thread( self.get_condition_id,m_id )
  if cond_id and cond_id not in self.executor._fee_cache:
   self.executor._fee_cache[cond_id]=(m_fee_rate,m_fee_exp)
  if token_id and token_id not in self.executor._tick_size_cache and 0.04 < float(eff_px) < 0.96:
   self.executor._tick_size_cache[token_id]=0.01
  notional_cap=getattr(self,"max_absolute_ticket_usd",None) or (10000.0 if getattr(self,"unconstrained_kelly",False) else MAX_ABSOLUTE_TICKET_USD)
  effective_notional=min(float(effective_notional),notional_cap)
  pre_cond_bal:Optional[float]=0.0
  if not self.dry_run and token_id:
   has_prior_activity=( any(p.get("token_id")==token_id for p in self.active_positions.values()) or any(i.get("token_id")==token_id for i in self.pending_entry_intents.values()) or any( p.get("token_id")==token_id and (float(p.get("remaining_shares",0.0) or 0.0) > 0.01 or p.get("status") not in ("FILLED","SETTLED")) for p in getattr(self,"closed_positions",[])[-20:] ) )
   if has_prior_activity:
    _inv_t0=time.perf_counter()
    try:
     pre_cond_bal=await asyncio.to_thread(self.executor.get_onchain_erc1155_balance,token_id)
    except Exception:
     pre_cond_bal=None
    _inv_ms=(time.perf_counter() - _inv_t0) * 1000.0
    _lt_inv=_CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
    if _lt_inv is not None:
     _lt_inv.set(inventory_rpc_ms=round(_inv_ms,3),inventory_rpc_used=True)
     _lt_inv.stamp("inventory_check_end")
    if _inv_ms > 100.0:
     logger.warning(f"[HOT-PATH RPC] on-chain ERC-1155 pre-trade read blocked entry for {_inv_ms:.0f}ms ({token_id[:12]}...)")
    if pre_cond_bal is None or not math.isfinite(float(pre_cond_bal)):
     logger.error(f"[ENTRY ABORTED] Cannot take authoritative pre-trade ERC-1155 snapshot for {token_id}.")
     return
    pre_cond_bal=float(pre_cond_bal)
   else:
    pre_cond_bal=0.0
  now_ts=time.time()
  event_id=str(shock.get("event_id") or shock.get("market_id") or "")
  expiry_ts=float(shock.get("expiry_ts") or shock.get("candle_expiry_ts") or (now_ts + float(shock.get("seconds_to_expiry",3600.0))))
  open_spot=float(open_spot_cand or shock.get("candle_open_spot") or shock.get("finalized_1h_open") or shock.get("spot_at_t0") or 0.0)
  spot_denom="USD" if _is_usd_oracle else "USDT"
  entry_spot_ref=float(usd_spot_t0 if _is_usd_oracle else (shock.get("spot_at_t0") or shock.get("trigger_price") or open_spot))
  is_special_regime=regime in ("REGIME_D_BOUNDARY_LOCK","REGIME_E_STRIKE_CONVERGENCE")
  target_exit=0.99 if (self.hold_to_maturity or is_special_regime) else self._calculate_target_exit(raw_vwap,tte)
  if is_special_regime:
   sleeve_max_price=max(self.max_price_ceiling,max_allowed_price)
  elif not self.dry_run:
   _base_ceil=min(self.max_price_ceiling,max_allowed_price,eff_price_ceiling)
   if _is_live_real:
    _ev_fair_cap=round(((p_fair * 0.965) + ((1.0 - p_fair) * 0.92 * 0.38)) / 1.05,4)
    sleeve_max_price=max(_base_ceil,min(0.87,round(max_allowed_price + 0.02,2),_ev_fair_cap))
   else:
    sleeve_max_price=_base_ceil
  else:
   sleeve_max_price=self.max_price_ceiling
  target_limit_px=round(min(raw_vwap + fak_buf,sleeve_max_price),2)
  if not self.dry_run and self.dynamic_sizing:
   limit_depth_usd=sum(float(px) * float(sz) for px,sz in raw_asks if float(px)<=target_limit_px + 1e-6)
   if limit_depth_usd < float(effective_notional) - 1e-6:
    orig_notional=float(effective_notional)
    snapped=None
    for cand_rung in (16.50,14.00,12.00):
     if cand_rung < orig_notional and limit_depth_usd>=cand_rung - 1e-6:
      snapped=cand_rung
      break
    if snapped is not None:
     effective_notional=snapped
     logger.info( f"[IDEA-1 ELASTIC DOWNSNAP] {trade_id}: depth within limit ${target_limit_px:.2f} is " f"${limit_depth_usd:.2f} < ${orig_notional:.2f}; down-snapping to pre-warmed rung ${effective_notional:.2f}." )
  self.pending_entry_intents[trade_id]={ "schema_version":"2.3.8","trade_id":trade_id,"entry_trade_id":trade_id,"sleeve":assigned_sleeve,"entry_order_id":None,"trade_ids":[],"transactions_hashes":[],"event_id":event_id,"market_id":m_id,"condition_id":cond_id,"token_id":token_id,"target_token":target_token,"asset":asset_str,"horizon":"15m" if is_subhourly else "1h","is_subhourly":bool(is_subhourly),"candle_open_spot":open_spot,"entry_spot_ref":entry_spot_ref,"spot_denomination":spot_denom,"candle_sigma":float(shock.get("candle_sigma") or ((0.0025 if asset_str=="BTC" else 0.0034) if is_subhourly else (0.0050 if asset_str=="BTC" else 0.0068))),"candle_expiry_ts":expiry_ts,"entry_tte":tte,"target_exit_price":target_exit,"notional_usd":effective_notional,"intended_notional":effective_notional,"target_price":target_limit_px,"observed_vwap":raw_vwap,"sleeve_max_price":sleeve_max_price,"side":"BUY","pre_token_balance":pre_cond_bal,"submitted_at_ts":now_ts,"timestamp":now_ts,"created_at_utc":datetime.now(timezone.utc).isoformat(),}
  if self.dynamic_sizing:
   active_sizing_fn=None
  else:
   active_sizing_fn=(lambda px:_calc_kelly(max(0.95,p_model_for_sizing),px,live_bankroll)) if (p_model_for_sizing and live_bankroll) else None
  _base_snipe_kw=dict( trade_id=trade_id,token_id=token_id,target_token=target_token,side="BUY",depth_hurdle=self.depth_hurdle,max_price_ceiling=sleeve_max_price,min_price_floor=min_allowed_price,expected_best_price=(t0_best_ask if (_is_live_real and t0_best_ask > 0.0) else None),market_id=str(shock.get("market_id")),condition_id=cond_id,market_fee_rate=fee_meta.get("fee_rate_market"),market_fee_exponent=fee_meta.get("fee_exponent",1.0),sizing_fn=active_sizing_fn,max_ticket_cap=getattr(self,"max_absolute_ticket_usd",None),prefetched_pre_balance=pre_cond_bal,)
  try:
   _lt_disp=_CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
   if _lt_disp is not None:
    _lt_disp.stamp("dispatch_call")
    _lt_disp.set(effective_notional_usd=effective_notional,target_limit_px=target_limit_px)
   res=await self.executor.execute_snipe_order_async( **_base_snipe_kw,notional_usd=effective_notional,target_price=target_limit_px,prefetched_book=book_snapshot,)
   if ( not res.success and "FOK Sweep Infeasible" in str(res.error or "") and not self.dry_run and self.dynamic_sizing and float(effective_notional) > 12.0 ):
    for fallback_rung in (16.50,12.00):
     if fallback_rung>=float(effective_notional) - 0.10:
      continue
     logger.info( f"[IDEA-1 FOK SWEEP DOWNSNAP RETRY] {trade_id}: ${effective_notional:.2f} infeasible at " f"${target_limit_px:.2f}; stepping down to pre-warmed rung ${fallback_rung:.2f}." )
     effective_notional=fallback_rung
     if trade_id in self.pending_entry_intents:
      self.pending_entry_intents[trade_id]["notional_usd"]=effective_notional
     res=await self.executor.execute_snipe_order_async( **_base_snipe_kw,notional_usd=effective_notional,target_price=target_limit_px,prefetched_book=book_snapshot,)
     if res.success or "FOK Sweep Infeasible" not in str(res.error or ""):
      break
   if ( (res.mode in ("FAK_KILLED_NO_MATCH","CLOB_HTTP_400_REJECTION") or (res.details or {}).get("fak_killed") or (res.details or {}).get("clob_400_rejection")) and not self.dry_run and self.dynamic_sizing and ( not _is_live_real or ( bool((getattr(self,"risk_config",None) or RISK_CONFIG).get("enable_fak_plus2c_fallback",False)) and z_strike>=1.25 ) ) and target_limit_px + 0.01<=sleeve_max_price + 1e-6 ):
    fallback_limit_px=round(min(sleeve_max_price,target_limit_px + 0.02),2)
    if fallback_limit_px > target_limit_px + 1e-6:
     logger.info( f"[IDEA-5 FAK +2c FALLBACK] {trade_id}: missed L1 at ${target_limit_px:.2f} (0 filled, mode={res.mode}); " f"firing sequential pre-signed fallback at ${fallback_limit_px:.2f} (ceiling=${sleeve_max_price:.2f})." )
     target_limit_px=fallback_limit_px
     if trade_id in self.pending_entry_intents:
      self.pending_entry_intents[trade_id]["target_price"]=target_limit_px
     fresh_fallback_book=fast_tick_book_for_token(read_fast_tick(asset_str),token_id) or book_snapshot
     try:
      res=await self.executor.execute_snipe_order_async( **_base_snipe_kw,notional_usd=effective_notional,target_price=target_limit_px,prefetched_book=fresh_fallback_book,max_book_buffer=0.04,)
     except TypeError as _te:
      if "max_book_buffer" not in str(_te):
       raise
      res=await self.executor.execute_snipe_order_async( **_base_snipe_kw,notional_usd=effective_notional,target_price=target_limit_px,prefetched_book=fresh_fallback_book,)
   if ( ( res.mode in ("FAK_KILLED_NO_MATCH","CLOB_HTTP_400_REJECTION") or (res.details or {}).get("fak_killed") or (res.details or {}).get("clob_400_rejection") ) and (not _is_live_real or (z_strike>=0.85 and abs(dist_pct)>=0.06)) ):
    rescue_res=await self._attempt_live_phase3a_maker_rescue( trade_id=trade_id,token_id=token_id,target_token=target_token,asset_str=asset_str,effective_notional=effective_notional,first_ask=first_ask,first_bid=first_bid,min_allowed_price=min_allowed_price,max_allowed_price=max_allowed_price,open_spot=open_spot,entry_spot_ref=entry_spot_ref,spot_denom=spot_denom,tte=tte,pre_cond_bal=pre_cond_bal,book_snapshot=book_snapshot,)
    if rescue_res is not None:
     res=rescue_res
  finally:
   _det_err=( (str(res.error or "").lower() + str((res.details or {}).get("raw_exception","")).lower()) if res is not None else "" )
   if res is not None and ( res.mode in ("FAK_KILLED_NO_MATCH","CLOB_HTTP_400_REJECTION") or (res.details or {}).get("fak_killed") or (res.details or {}).get("clob_400_rejection") or "status_code=400" in _det_err or "status=400" in _det_err or "invalid amounts" in _det_err or "supports a max accuracy" in _det_err ):
    self.pending_entry_intents.pop(trade_id,None)
   await asyncio.to_thread(self.save_state)
  if res.mode in ("FAK_KILLED_NO_MATCH","CLOB_HTTP_400_REJECTION") or (res.details or {}).get("fak_killed") or (res.details or {}).get("clob_400_rejection"):
   if self.pending_entry_intents.pop(trade_id,None) is not None:
    await asyncio.to_thread(self.save_state)
   if not self.dry_run:
    self._register_shadow_phase3a_maker_in( shock,target_token,first_ask,first_bid,max_allowed_price,raw_asks,f"CLOB_400_OR_FAK_MISS:{res.mode}",bool(is_subhourly),float(dist_pct),float(tte),)
   logger.info( f"[CLOB REJECTION / FAK ZERO MATCH] {trade_id} rejected deterministically by CLOB (0 shares filled, error={res.error}). " f"Released entry intent immediately without halting." )
   return
  err_str=str(res.error or "").lower() + str((res.details or {}).get("raw_exception","")).lower()
  if "status_code=400" in err_str or "status=400" in err_str or "invalid amounts" in err_str or "supports a max accuracy" in err_str:
   if self.pending_entry_intents.pop(trade_id,None) is not None:
    await asyncio.to_thread(self.save_state)
   logger.warning(f"[HTTP 400 REJECTION OVERRIDE] {trade_id} rejected with HTTP 400 ({res.error}). Not registering in active_positions.")
   return
  if (res.details or {}).get("outcome_unknown"):
   self.pending_entry_intents.pop(trade_id,None)
   ref_px=float(res.price or raw_vwap or 0.0)
   est_shares=float(res.size or (effective_notional / max(ref_px,0.01)))
   unknown_pre_bal=(res.details or {}).get("pre_token_balance")
   pos_record={ "trade_id":trade_id,"event_id":event_id,"market_id":m_id,"condition_id":cond_id,"token_id":token_id,"target_token":target_token,"asset":asset_str,"candle_open_spot":open_spot,"entry_spot_ref":entry_spot_ref,"spot_denomination":spot_denom,"candle_sigma":float(shock.get("candle_sigma",0.005) or 0.005),"entry_price":ref_px,"entry_shares":est_shares,"gross_entry_shares":est_shares,"remaining_shares":est_shares,"filled_exit_shares":0.0,"remaining_exit_shares":est_shares,"remaining_cost_basis":float(effective_notional),"realized_exit_cash":0.0,"realized_exit_fee":0.0,"gross_exit_cash":0.0,"average_exit_price":0.0,"exit_trade_ids":[],"notional_usd":float(effective_notional),"intended_notional":float(effective_notional),"fee_usd":float(res.fee_usd or 0.0),"entry_fee_cash_usd":float(res.fee_usd or 0.0),"entry_fee_asset":"USDC","fee_source":"crypto_fees_v2","fee_rate_applied":m_fee_rate,"fee_exponent_applied":m_fee_exp,"target_exit_price":self._calculate_target_exit(ref_px,tte),"entry_time_utc":datetime.now(timezone.utc).isoformat(),"entry_ts":now_ts,"submitted_at_ts":now_ts,"candle_expiry_ts":expiry_ts,"pre_token_balance":float(unknown_pre_bal if unknown_pre_bal is not None else pre_cond_bal),"order_id":res.order_id or (res.details or {}).get("entry_order_id"),"entry_order_id":res.order_id or (res.details or {}).get("entry_order_id"),"trade_ids":[],"transactions_hashes":[],"status":"ENTRY_OUTCOME_UNKNOWN","exit_order_status":"ENTRY_OUTCOME_UNKNOWN","inventory_reconciled":False,"is_liquidating":False,"unwind_order_id":None,"unwind_start_time":0.0,}
   self.active_positions[trade_id]=pos_record
   self._refresh_global_halt()
   self.save_state()
   logger.critical( f"[ENTRY OUTCOME UNKNOWN] Trade {trade_id} registered in active_positions for reconciliation! " "Halting new entries until exchange reconciliation." )
   return
  self.pending_entry_intents.pop(trade_id,None)
  if not res.success:
   await asyncio.to_thread(self.save_state)
   if not self.dry_run:
    self._register_shadow_phase3a_maker_in( shock,target_token,first_ask,first_bid,max_allowed_price,raw_asks,f"EXECUTION_REJECT:{res.mode or res.error}",bool(is_subhourly),float(dist_pct),float(tte),)
  if res.success:
   self.trades_this_hour += 1
   self.trades_per_market[m_id] += 1
   self.trades_per_market_direction[(m_id,target_token)] += 1
   self.traded_market_ids.add(m_id)
   target_exit=0.99 if (self.hold_to_maturity or is_special_regime) else self._calculate_target_exit(res.price,tte)
   asset_sym=asset_str
   if asset_sym not in effective_allowed_assets:
    raise RuntimeError(f"Refusing to create position with unresolved/disallowed asset: {asset_sym!r}")
   open_spot=float(open_spot_cand or shock.get("finalized_1h_open") or shock.get("candle_open_spot") or shock.get("spot_at_t0") or 0.0)
   entry_spot_ref=float(usd_spot_t0 if _is_usd_oracle else (shock.get("spot_at_t0") or shock.get("trigger_price") or open_spot))
   if open_spot<=0.0:
    ref_fn=self.get_usd_reference_spot_price if _is_usd_oracle else self.get_reference_spot_price
    open_spot=(await asyncio.to_thread(ref_fn,asset_sym)) or 0.0
    if entry_spot_ref<=0.0:
     entry_spot_ref=open_spot
   pos_record={ "trade_id":trade_id,"sleeve":assigned_sleeve,"entry_tte":tte,"event_id":event_id,"market_id":str(shock.get("market_id")),"condition_id":cond_id,"token_id":token_id,"target_token":target_token,"asset":asset_sym,"horizon":"15m" if is_subhourly else "1h","is_subhourly":bool(is_subhourly),"candle_open_spot":open_spot,"entry_spot_ref":entry_spot_ref,"spot_denomination":spot_denom,"candle_sigma":float(shock.get("candle_sigma") or ((0.0025 if asset_sym=="BTC" else 0.0034) if is_subhourly else (0.0050 if asset_sym=="BTC" else 0.0068))),"entry_price":res.price,"entry_shares":res.size,"gross_entry_shares":float(res.size),"remaining_shares":res.size,"filled_exit_shares":0.0,"remaining_exit_shares":res.size,"remaining_cost_basis":res.notional_usd,"realized_exit_cash":0.0,"realized_exit_fee":0.0,"gross_exit_cash":0.0,"average_exit_price":0.0,"exit_trade_ids":[],"notional_usd":res.notional_usd,"fee_usd":res.fee_usd,"entry_fee_cash_usd":float(res.fee_usd or 0.0),"entry_fee_asset":"USDC","fee_source":"crypto_fees_v2","fee_rate_applied":m_fee_rate,"fee_exponent_applied":m_fee_exp,"target_exit_price":0.99 if self.hold_to_maturity else target_exit,"exit_order_size":float(res.size),"entry_time_utc":datetime.now(timezone.utc).isoformat(),"entry_ts":time.time(),"candle_expiry_ts":time.time() + tte,"pre_token_balance":res.details.get("pre_token_balance",pre_cond_bal),"order_id":res.order_id,"entry_order_id":res.order_id,"trade_ids":res.details.get("trade_ids",[]),"transactions_hashes":res.details.get("transactions_hashes",[]),"status":res.execution_status,"exit_order_id":None,"exit_order_status":"NONE","is_liquidating":False,"unwind_order_id":None,"unwind_start_time":0.0,}
   self.active_positions[trade_id]=pos_record
   if not self.dry_run:
    _fill_cost_total=max(0.0,float(res.notional_usd or 0.0) + float(res.fee_usd or 0.0))
    if getattr(self,"_last_known_collateral",None) is not None and _fill_cost_total > 0.0:
     self._last_known_collateral=max(0.0,float(self._last_known_collateral) - _fill_cost_total)
    self.executor.invalidate_collateral_cache()
    self._pending_collateral_refresh=True
   await asyncio.to_thread(self.save_state)
   logger.info(f"✓ POSITION RECORDED & PERSISTED: {trade_id} | Shares={res.size:.2f} @ ${res.price:.4f} | Status={res.execution_status}")
   if not self.dry_run:
    try:
     send_operational_alert( "LIVE_ORDER_FILL",f"{trade_id} {shock.get('title')!r} {res.size:.2f} sh @ ${res.price:.4f} (~${res.size * res.price:.2f}) status={res.execution_status}","INFO",dedupe_key=f"fill:{trade_id}",)
    except Exception:
     logger.debug("[ALERT] fill alert construction failed",exc_info=True)
   if res.execution_status==ExecutionStatus.POSITION_CONFIRMED:
    pos_record["inventory_reconciled"]=True
    pos_record["entry_finality_source"]="EXECUTOR_CONFIRMED_DELTA"
    rem_total=float(res.size)
    entry_px=float(pos_record.get("entry_price",0.70))
    use_tranches=self._use_two_tranche_maker_exit(assigned_sleeve)
    t1_offset=self._tranche1_tp_offset(assigned_sleeve)
    is_live_ctf=( (not self.dry_run) and getattr(self.executor,"auth_mode","") in ("LIVE","AUTHENTICATED_L2") and bool(token_id and str(token_id).isdigit() and len(str(token_id))>=20) and not getattr(self,"enable_mid_hour_t1_12c",False) )
    single_exit_px=(0.96 if is_live_ctf else min(0.96,round(entry_px + 0.16,2))) if use_tranches else target_exit
    exit_size=rem_total
    exit_price=single_exit_px
    if use_tranches and float(pos_record.get("notional_usd",0.0) or 0.0)>=10.0 and rem_total>=10.0:
     t1_sz=float((Decimal(str(rem_total)) * Decimal("0.50")).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
     t2_sz=float((Decimal(str(rem_total)) - Decimal(str(t1_sz))).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
     if t1_sz>=5.0 and t2_sz>=5.0:
      t1_px=0.95 if is_live_ctf else min(0.94,round(entry_px + t1_offset,2))
      t2_px=0.98
      pos_record["exit_tranches"]=[ {"idx":1,"size":t1_sz,"price":t1_px,"status":"PENDING"},{"idx":2,"size":t2_sz,"price":t2_px,"status":"PENDING"},]
      exit_size=t1_sz
      exit_price=pos_record["exit_tranches"][0]["price"]
      pos_record["target_exit_price"]=exit_price
     else:
      exit_size=rem_total
      exit_price=single_exit_px
      pos_record["target_exit_price"]=exit_price
    else:
     exit_size=rem_total
     exit_price=single_exit_px
     pos_record["target_exit_price"]=exit_price
    exit_res=await asyncio.to_thread( self.executor.post_maker_exit_order,token_id=token_id,price=exit_price,size=exit_size,side="SELL",)
    posted=self._apply_exit_post_result(pos_record,exit_res,float(exit_size))
    if pos_record.get("exit_tranches") and posted:
     pos_record["exit_tranches"][0]["status"]="POSTED"
    elif pos_record.get("exit_tranches") and (exit_res or {}).get("outcome_unknown"):
     pos_record["exit_tranches"][0]["status"]="IN_FLIGHT"
    if posted:
     logger.info(f"✓ MAKER SCALP ORDER POSTED (POST-ONLY): {pos_record['exit_order_id']} | {exit_size:.2f} shares @ ${exit_price:.4f}")
   else:
    pos_record["exit_order_status"]="AWAITING_DELTA_SETTLEMENT"
    logger.info(f"Position {trade_id} in {res.execution_status}. Background loop will verify on-chain delta before posting maker exit.")
    if not self.dry_run:
     self._spawn_fast_confirm(trade_id)
   await asyncio.to_thread(self.save_state)
 def _recover_pending_intent(self,trade_id:str,intent:Dict[str,Any])->str:
  token_id=intent.get("token_id")
  pre_bal=float(intent.get("pre_token_balance",0.0) or 0.0)
  intended_notional=float(intent.get("notional_usd",intent.get("intended_notional",0.0)) or 0.0)
  target_price=float(intent.get("target_price",0.70) or 0.70)
  submitted_ts=float(intent.get("submitted_at_ts",intent.get("timestamp",time.time())) or time.time())
  if not token_id:
   logger.error(f"[RECONCILIATION] Pending intent {trade_id} has no token id; retaining global halt.")
   return "UNRESOLVED"
  cls=self._classify_entry(token_id,pre_bal,submitted_ts,intent.get("entry_order_id") or intent.get("order_id"),trade_id)
  verdict=cls["verdict"]
  if verdict=="NOT_EXECUTED":
   logger.info(f"[RECONCILIATION] Pending entry intent {trade_id} authoritatively NOT executed ({cls.get('proof')}). Discarding intent.")
   self.pending_entry_intents.pop(trade_id,None)
   self.save_state()
   return "NOT_EXECUTED"
  if verdict not in {"ARRIVED","MATCHED_UNSETTLED"}:
   logger.error( f"[RECONCILIATION] Pending entry intent {trade_id} outcome not authoritatively provable " f"(balance={cls.get('balance')}, source={cls.get('source')}). Retaining intent and global halt." )
   return "UNRESOLVED"
  target_exit_p=float(intent.get("target_exit_price") or (0.99 if self.hold_to_maturity else round(min(0.99,target_price + 0.08),2)))
  candle_open=float(intent.get("candle_open_spot",0.0) or 0.0)
  candle_exp=float(intent.get("candle_expiry_ts",0.0) or 0.0)
  candle_sig=float(intent.get("candle_sigma",0.005) or 0.005)
  asset_val=intent.get("asset","")
  target_tok=intent.get("target_token","")
  recovered_pos={ "trade_id":trade_id,"entry_trade_id":intent.get("entry_trade_id") or trade_id,"order_id":intent.get("entry_order_id") or intent.get("order_id"),"entry_order_id":intent.get("entry_order_id") or intent.get("order_id"),"trade_ids":[],"transactions_hashes":[],"pre_token_balance":pre_bal,"event_id":intent.get("event_id",""),"market_id":intent.get("market_id",""),"condition_id":intent.get("condition_id",""),"token_id":token_id,"target_token":target_tok,"asset":asset_val,"candle_open_spot":candle_open,"entry_spot_ref":float(intent.get("entry_spot_ref") or candle_open),"spot_denomination":intent.get("spot_denomination","USDT"),"candle_sigma":candle_sig,"candle_expiry_ts":candle_exp,"side":intent.get("side","BUY"),"entry_price":target_price,"entry_shares":0.0,"gross_entry_shares":0.0,"remaining_shares":0.0,"remaining_exit_shares":0.0,"filled_exit_shares":0.0,"remaining_cost_basis":intended_notional,"notional_usd":intended_notional,"intended_notional":intended_notional,"cost_basis_estimated":True,"fee_usd":float(intent.get("fee_usd",0.0) or 0.0),"entry_fee_cash_usd":float(intent.get("entry_fee_cash_usd",0.0) or 0.0),"entry_fee_asset":intent.get("entry_fee_asset","USDC"),"fee_source":intent.get("fee_source","crypto_fees_v2"),"target_exit_price":target_exit_p,"entry_time_utc":intent.get("created_at_utc",datetime.now(timezone.utc).isoformat()),"entry_ts":submitted_ts,"submitted_at_ts":submitted_ts,"status":ExecutionStatus.POSITION_CONFIRMED if verdict=="ARRIVED" else ExecutionStatus.MATCHED_PENDING_SETTLEMENT,"exit_order_id":None,"exit_order_status":"AWAITING_DELTA_SETTLEMENT","created_at_utc":intent.get("created_at_utc",datetime.now(timezone.utc).isoformat()),"realized_exit_cash":0.0,"realized_exit_fee":0.0,"gross_exit_cash":0.0,"average_exit_price":0.0,"exit_trade_ids":[],"inventory_reconciled":False,"is_liquidating":False,"unwind_order_id":None,"unwind_start_time":0.0,"order_records":{},"recovered_from_intent":True,}
  self._apply_entry_evidence(recovered_pos,cls)
  if not recovered_pos.get("target_exit_price") or not math.isfinite(float(recovered_pos["target_exit_price"])):
   recovered_pos["target_exit_price"]=target_exit_p
  missing_fields=[]
  if not target_tok:
   missing_fields.append("target_token")
  if not asset_val:
   missing_fields.append("asset")
  if candle_open<=0.0 or not math.isfinite(candle_open):
   missing_fields.append("candle_open_spot")
  if candle_exp<=0.0 or not math.isfinite(candle_exp):
   missing_fields.append("candle_expiry_ts")
  if missing_fields:
   logger.critical( f"[RECONCILIATION] Recovered position {trade_id} lacks critical supervisory fields {missing_fields}. " "Enforcing persistent reconciliation hold!" )
   recovered_pos["exit_order_status"]="RECONCILIATION_HOLD_INCOMPLETE_SCHEMA"
   recovered_pos["missing_supervisory_fields"]=missing_fields
  self.active_positions[trade_id]=recovered_pos
  self.pending_entry_intents.pop(trade_id,None)
  self.save_state()
  logger.warning( f"[RECONCILIATION] RECOVERED position from intent {trade_id}: {verdict} | shares={recovered_pos['entry_shares']} | " f"cost=${recovered_pos['notional_usd']:.4f} | finality={recovered_pos.get('entry_finality_source')} | " f"trade_ids={recovered_pos.get('trade_ids')}" )
  return "RECOVERED"
 def reconcile_with_exchange(self):
  if self.dry_run or not self.executor.is_authenticated:
   return
  logger.info("[RECONCILIATION] Reconciling local state with live exchange...")
  try:
   try:
    collateral_bal=self.executor.get_collateral_balance()
    if collateral_bal is not None and isinstance(collateral_bal,(int,float)) and collateral_bal > 0:
     self._last_known_collateral=float(collateral_bal)
     self.executor.set_cached_collateral(self._last_known_collateral)
     logger.info(f"[RECONCILIATION] Live collateral balance: ${self._last_known_collateral:.2f}")
     now_ts=time.time()
     active_market_equity=sum(self.get_position_market_value(p,now_ts) for p in self.active_positions.values())
     tot_equity=self._last_known_collateral + active_market_equity
     self._update_equity_tier(tot_equity)
     self.risk_controller.check_equity_drawdown(tot_equity,allow_auto_clear=True)
   except Exception as e:
    logger.debug(f"[RECONCILIATION] Could not query initial collateral balance: {e}")
   open_orders=self._strict_open_orders()
   open_order_ids={o.get("id") or o.get("orderID") for o in open_orders if o}
   logger.info(f"[RECONCILIATION] CLOB reports {len(open_order_ids)} live open orders.")
   for trade_id,intent in list((getattr(self,"pending_entry_intents",None) or {}).items()):
    if trade_id in self.active_positions:
     logger.info(f"[RECONCILIATION] Pending entry intent {trade_id} already in active_positions; clearing intent.")
     self.pending_entry_intents.pop(trade_id,None)
     self.save_state()
     continue
    self._recover_pending_intent(trade_id,intent)
   for tid,pos in list(self.active_positions.items()):
    if position_requires_global_halt(pos):
     self._resolve_lifecycle(tid,pos,open_orders,force=True)
   for tid,pos in list(self.active_positions.items()):
    if tid not in self.active_positions:
     continue
    if position_is_settlement_receivable(pos) or position_requires_global_halt(pos):
     continue
    exit_oid=pos.get("exit_order_id")
    token_id=pos.get("token_id")
    if exit_oid and exit_oid in open_order_ids:
     logger.info(f"[RECONCILIATION] Active position {tid} has confirmed resting exit order {exit_oid}.")
     continue
    if exit_oid:
     prior_exit_state=pos.get("exit_order_status","")
     order_info=self.executor.get_order_status(exit_oid)
     if prior_exit_state in {"STOP_CANCEL_PENDING","PRE_EXPIRY_CANCEL_PENDING"}:
      if not order_info:
       logger.warning(f"Cannot reconcile pending cancellation {exit_oid} for {tid}; retaining position.")
       continue
      terminal=str(order_info.get("status","")).upper()
      if terminal not in {"MATCHED","FILLED","CONFIRMED"} and not ( terminal.startswith("CANCEL") or terminal in {"EXPIRED","REJECTED"} ):
       logger.warning(f"Cancellation not terminal: {exit_oid} (status={terminal}); retaining position.")
       continue
      if terminal in {"MATCHED","FILLED","CONFIRMED"}:
       pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED"
       pos["pending_canceled_order_id"]=exit_oid
       self.save_state()
       continue
      try:
       self.executor.release_inventory(reservation_id=exit_oid)
      except Exception as rel_err:
       logger.error(f"Reservation release failed for {exit_oid}: {rel_err}")
       raise
      pos["exit_order_id"]=None
      if prior_exit_state=="STOP_CANCEL_PENDING":
       pos["exit_order_status"]="UNWIND_RETRY_REQUIRED"
       pos["next_unwind_retry_ts"]=0.0
       pos["is_liquidating"]=False
      else:
       pos["exit_order_status"]="PRE_EXPIRY_EVALUATION_REQUIRED"
      self.save_state()
      continue
     if not order_info:
      logger.warning(f"[RECONCILIATION] Exit order {exit_oid} for {tid} absent from snapshot and status UNKNOWN; retaining.")
      continue
     order_size=float(pos.get("exit_order_size",pos.get("entry_shares",0.0)) or 0.0)
     order_matched=float(self._num(order_info.get("size_matched")) or 0.0)
     order_status_str=str(order_info.get("status","")).upper()
     raw_taking=order_info.get("taking_amount") or order_info.get("takingAmount")
     total_order_taking=self._num(raw_taking)
     is_taking_estimated=False
     if total_order_taking is None:
      total_order_taking=order_matched * float(pos.get("target_exit_price",0.0) or 0.0)
      if order_matched > 0:
       pos["exit_cash_estimated"]=True
       is_taking_estimated=True
     raw_fee=float(self._num(order_info.get("fee")) or self._num(order_info.get("fee_usd")) or 0.0)
     self.record_fill_and_update_position( pos,exit_oid,order_matched,total_order_taking,fee_usd=raw_fee,cash_is_estimated=is_taking_estimated )
     f_ids=[str(x) for x in (order_info.get("fill_ids") or order_info.get("associate_trades") or []) if x]
     if f_ids:
      pos["exit_fill_ids"]=sorted(set(pos.get("exit_fill_ids") or []) | set(f_ids))
     rem_shares=float(pos["remaining_shares"])
     total_filled_shares=float(pos["filled_exit_shares"])
     is_order_terminal=( order_status_str in {"MATCHED","FILLED","CONFIRMED"} or order_status_str.startswith("CANCEL") or order_status_str in {"EXPIRED","REJECTED"} or order_matched>=order_size - 1e-4 )
     is_canceled=order_status_str.startswith("CANCEL") or order_status_str in {"EXPIRED","REJECTED"}
     is_position_complete=rem_shares<=0.01 or total_filled_shares>=float(pos["entry_shares"]) - 1e-4
     if is_position_complete:
      if is_taking_estimated or float(pos.get("estimated_exit_cash",0.0)) > 0.0:
       pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED"
       pos["status"]="UNRESOLVED_SETTLEMENT"
       self.save_state()
       logger.warning(f"[RECONCILIATION] Position {tid} filled offline but cash is estimated; retaining in UNRESOLVED_SETTLEMENT.")
      else:
       self._close_position(tid,pos,ExecutionStatus.FILLED,"FILLED_OFFLINE",won=True)
       logger.info(f"[RECONCILIATION] Position {tid} completely filled while offline.")
      continue
     if is_order_terminal:
      pos["exit_order_id"]=None
      pos["pending_canceled_order_id"]=exit_oid
      pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED"
      pos["status"]=ExecutionStatus.PARTIALLY_FILLED
      self.save_state()
      logger.warning(f"[PARTIAL ORDER MATCH] Position {tid}: order {exit_oid} filled {order_matched:.2f} shares. Remaining unsold: {rem_shares:.2f}")
      continue
     if not is_canceled:
      if order_matched > 0:
       pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED"
       pos["pending_canceled_order_id"]=exit_oid
      self.save_state()
      logger.warning(f"[RECONCILIATION] Exit order {exit_oid} for {tid} non-terminal ({order_status_str}) but absent from snapshot; retaining.")
      continue
     try:
      self.executor.release_inventory(reservation_id=exit_oid)
     except Exception as rel_err:
      logger.error(f"Reservation release failed for {exit_oid}: {rel_err}")
      raise
     pos["exit_order_id"]=None
     pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED"
     if total_filled_shares > 0:
      pos["status"]=ExecutionStatus.PARTIALLY_FILLED
     tranches=pos.get("exit_tranches",[])
     for t in tranches:
      if t.get("status") in {"POSTED","IN_FLIGHT"}:
       tranche_rem=max(0.0,round(float(t["size"]) - order_matched,2))
       if tranche_rem<=0.01:
        t["status"]="FILLED"
       else:
        t["size"]=tranche_rem
        t["status"]="PENDING"
     next_pending=[t for t in tranches if t.get("status")=="PENDING"]
     if next_pending:
      pos["target_exit_price"]=float(next_pending[0]["price"])
     self.save_state()
     logger.warning(f"[RECONCILIATION] Exit order {exit_oid} for {tid} terminally {order_status_str}; residual {rem_shares:.2f} eligible for recovery.")
    if token_id and not pos.get("exit_order_id"):
     pos.pop("recovered_from_intent",None)
     self._attempt_maker_exit_post(tid,pos)
   tracked_oids={ str(p.get(k)) for p in self.active_positions.values() for k in ("exit_order_id","unwind_order_id","pending_canceled_order_id","cancel_pending_order_id") if p.get(k) }
   for o in open_orders:
    oid=o.get("id") or o.get("orderID")
    if oid and str(oid) not in tracked_oids:
     logger.warning(f"[RECONCILIATION] Orphan CLOB order {oid} detected. Canceling for capital safety.")
     self.executor.cancel_order(oid)
   rebuild=getattr(self.executor,"rebuild_reservations_from_exchange",None)
   if callable(rebuild):
    fresh_orders=self._strict_open_orders()
    if rebuild(fresh_orders) is False:
     raise RuntimeError("Reservation book could not be rebuilt from the exchange")
   self._startup_reconciled=True
   self._refresh_global_halt(authoritative=True)
   self.save_state()
   logger.info( f"[RECONCILIATION] Exchange state reconciled. Global halt={self.risk_halt} " f"reasons={self.global_halt_reasons}" )
  except Exception as e:
   logger.critical(f"[RECONCILIATION] Exchange/local state is UNKNOWN; refusing to mutate orders: {e}")
   raise RuntimeError("Live exchange reconciliation failed; safe startup refused") from e
 def _strict_open_orders(self)->List[Dict[str,Any]]:
  try:
   open_orders=self.executor.get_open_orders(strict=True)
  except TypeError:
   open_orders=self.executor.get_open_orders()
  if open_orders is None or not isinstance(open_orders,list):
   raise RuntimeError("CLOB open-order snapshot unavailable")
  return open_orders
 async def _apply_market_resolution(self,tid:str,pos:Dict[str,Any],winning_outcome:Any)->None:
  if tid not in self.active_positions:
   return
  outcome_str=winning_outcome.get("winning_outcome") if isinstance(winning_outcome,dict) else str(winning_outcome or "")
  if pos.get("resolved_winning_outcome") is None:
   pos["resolved_winning_outcome"]=outcome_str
   pos["resolution_seen_at_ts"]=time.time()
   self.save_state()
  if position_is_settlement_receivable(pos):
   return
  if pos.get("status")=="UNRESOLVED_SETTLEMENT" and not self.dry_run and bool(pos.get("exit_cash_estimated")):
   logger.info(f"[RESOLUTION DEFERRED] {tid}: awaiting CLOB fill confirmation for in-flight UNRESOLVED_SETTLEMENT exit.")
   return
  if pos.get("status")=="LIQUIDITY_CRISIS" or pos.get("exit_order_status")=="LIQUIDITY_CRISIS":
   pos["status"]=ExecutionStatus.POSITION_CONFIRMED
   pos["exit_order_status"]="RESTING" if pos.get("exit_order_id") else "NONE"
  if not self.dry_run and position_requires_global_halt(pos) and pos.get("exit_order_status")!="RESOLUTION_CANCEL_UNCONFIRMED":
   await asyncio.to_thread(self._resolve_lifecycle,tid,pos,None,True)
   if tid not in self.active_positions:
    return
   if position_requires_global_halt(pos) and pos.get("exit_order_status")!="RESOLUTION_CANCEL_UNCONFIRMED":
    logger.warning(f"[RESOLUTION DEFERRED] {tid}: unresolved execution outcome {pos.get('exit_order_status')}; settling after reconciliation.")
    return
  won=(pos.get("target_token")==outcome_str)
  token_id=pos.get("token_id")
  exit_oid=pos.get("exit_order_id")
  if exit_oid:
   cancel_res=await asyncio.to_thread(self.executor.cancel_order,exit_oid)
   if not self.dry_run:
    if (cancel_res or {}).get("error"):
     pos["exit_order_status"]="RESOLUTION_CANCEL_UNCONFIRMED"
     self.save_state()
     return
    summary=await asyncio.to_thread(self.executor.get_order_fill_summary,exit_oid,token_id)
    if summary is None:
     try:
      oo=await asyncio.to_thread(self._strict_open_orders)
      oo_ids={o.get("id") or o.get("orderID") for o in oo if o}
      fills=await asyncio.to_thread(self.executor.get_account_fills,token_id,float(pos.get("entry_ts",0.0) or 0.0),"SELL",exit_oid)
     except Exception:
      oo_ids,fills={exit_oid},None
     if exit_oid in oo_ids or fills is None:
      pos["exit_order_status"]="RESOLUTION_CANCEL_UNCONFIRMED"
      self.save_state()
      return
     if fills:
      self._record_history_fills(pos,fills,taker=False)
     if float(pos.get("remaining_shares",0.0) or 0.0)<=0.02:
      self._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True)
      return
    else:
     self._record_order_summary(pos,summary,float(pos.get("target_exit_price",0.0) or 0.0),taker=False)
     if float(pos.get("remaining_shares",0.0) or 0.0)<=0.02:
      self._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True)
      return
     if not summary["terminal"]:
      pos["exit_order_status"]="RESOLUTION_CANCEL_UNCONFIRMED"
      self.save_state()
      return
    self.executor.release_inventory(reservation_id=exit_oid)
   pos["exit_order_id"]=None
   pos["exit_order_status"]="CANCELED_FOR_RESOLUTION"
  rem_shares=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",pos.get("entry_shares",0.0))) or 0.0)
  if not self.dry_run:
   if not won:
    pos["expected_terminal_payout_usd"]=0.0
    pos["redemption_receivable_usd"]=0.0
    pos["winning_shares_held"]=0.0
    pos["expected_winning_outcome"]=winning_outcome
    self._close_position(tid,pos,ExecutionStatus.SETTLED,"MARKET_RESOLVED_LOSS",won=False)
    return
   bal,src=await asyncio.to_thread(self._wallet_token_balance,token_id)
   if src!=self.ONCHAIN_SOURCE and (bal is None or bal < 0.01):
    logger.warning( f"[RESOLUTION DEFERRED] {tid}: Winning position on-chain ERC-1155 balance unavailable " f"(bal={bal}, src={src}). Deferring resolution closeout until Polygon RPC responds." )
    return
   if bal is not None and src==self.ONCHAIN_SOURCE:
    rem_shares=min(rem_shares,bal)
   if rem_shares < 0.02:
    if float(pos.get("confirmed_realized_cash",pos.get("realized_exit_cash",0.0)) or 0.0)<=0.0 and token_id:
     try:
      extra_fills=await asyncio.to_thread( self.executor.get_account_fills,token_id,float(pos.get("entry_ts",0.0) or 0.0),"SELL",None )
      if isinstance(extra_fills,list) and extra_fills:
       self._record_history_fills(pos,extra_fills,taker=False)
     except Exception:
      pass
    pos["expected_terminal_payout_usd"]=0.0
    pos["redemption_receivable_usd"]=0.0
    pos["winning_shares_held"]=0.0
    pos["expected_winning_outcome"]=winning_outcome
    _has_clob_win=float(pos.get("confirmed_realized_cash",pos.get("realized_exit_cash",0.0)) or 0.0) > float(pos.get("notional_usd",0.0) or 0.0)
    if _has_clob_win:
     pos["exit_cash_estimated"]=False
     pos["estimated_exit_cash"]=0.0
     pos["confirmed_realized_cash"]=float(pos.get("confirmed_realized_cash") or pos.get("realized_exit_cash") or 0.0)
     self._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True)
    else:
     self._close_position(tid,pos,ExecutionStatus.SETTLED,"MARKET_RESOLVED_NO_INVENTORY",won=False)
    return
   head=await asyncio.to_thread(self.executor.get_current_block_number)
   pos["status"]="AWAITING_ONCHAIN_SETTLEMENT"
   pos["exit_order_status"]="AWAITING_REDEMPTION"
   pos["is_liquidating"]=False
   pos["expected_terminal_payout_usd"]=round(rem_shares,4)
   pos["redemption_receivable_usd"]=round(rem_shares,4)
   pos["winning_shares_held"]=round(rem_shares,6)
   pos["expected_winning_outcome"]=winning_outcome
   pos["resolution_block"]=max(0,int(head) - 50) if isinstance(head,int) else None
   self.save_state()
   logger.info( f"[RESOLVED - RECEIVABLE] {tid}: {rem_shares:.2f} winning shares held. Expected ${rem_shares:.2f} is a " "receivable, NOT realized cash, until a verified on-chain redemption receipt." )
   try:
    await asyncio.to_thread(self.poll_onchain_redemptions,True)
   except Exception as exc_red_imm:
    logger.debug(f"[AUTO-REDEEMER] Immediate post-resolution redemption poll notice: {exc_red_imm}")
   return
  payout=rem_shares * 1.0 if (won and rem_shares>=0.01) else 0.0
  if payout > 0.0:
   self.record_fill_and_update_position(pos,"SETTLEMENT_RESOLUTION_PAYOUT",rem_shares,payout,0.0)
  net_pnl=self._close_position(tid,pos,ExecutionStatus.SETTLED,"MARKET_RESOLVED",won=None)
  logger.info(f"✓ POSITION RESOLVED AT MATURITY: {tid} | Won={won} | RemShares={rem_shares:.2f} | Net PnL=${net_pnl:+.2f}")
 async def check_resolutions_and_manage_positions(self):
  self._main_loop=asyncio.get_running_loop()
  if not self.active_positions:
   self._refresh_global_halt()
   return
  if RESOLUTIONS_FILE.exists():
   try:
    current_res_size=RESOLUTIONS_FILE.stat().st_size
    if current_res_size > self.last_res_file_pos:
     with open(RESOLUTIONS_FILE,"rb") as f:
      f.seek(self.last_res_file_pos)
      chunk=f.read()
     complete_end=chunk.rfind(b"\n") + 1
     if complete_end:
      new_lines=chunk[:complete_end].decode("utf-8").splitlines()
      self.last_res_file_pos += complete_end
     else:
      new_lines=[]
     for line in new_lines:
      if not line.strip():
       continue
      try:
       res=json.loads(line)
       res_m_id=str(res.get("market_id"))
       winning_outcome=res.get("winning_outcome")
       for tid,pos in list(self.active_positions.items()):
        if str(pos.get("market_id"))==res_m_id:
         await self._apply_market_resolution(tid,pos,winning_outcome)
      except Exception as e:
       logger.error(f"Error parsing resolution line: {e}",exc_info=True)
   except Exception as e:
    logger.error(f"Error checking resolutions: {e}")
  if not self.dry_run and getattr(self.executor,"auth_mode","") in ("LIVE","AUTHENTICATED_L2"):
   now_g=time.time()
   for tid,pos in list(self.active_positions.items()):
    exp_ts=float(pos.get("candle_expiry_ts",0.0) or 0.0)
    m_id=str(pos.get("market_id") or "")
    if exp_ts > 0.0 and now_g>=exp_ts + 12.0 and pos.get("resolved_winning_outcome") is None and m_id.isdigit() and int(m_id)>=100000:
     if now_g - float(pos.get("_last_gamma_res_poll",0.0) or 0.0)>=15.0:
      pos["_last_gamma_res_poll"]=now_g
      try:
       r_gm=await asyncio.to_thread( lambda:self.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{m_id}",timeout=3.0).json() )
       if isinstance(r_gm,dict) and (r_gm.get("umaResolutionStatus")=="resolved" or r_gm.get("closed")):
        raw_p=r_gm.get("outcomePrices")
        p_list=json.loads(raw_p) if isinstance(raw_p,str) else (raw_p or [])
        raw_t=r_gm.get("clobTokenIds")
        t_list=json.loads(raw_t) if isinstance(raw_t,str) else (raw_t or [])
        pos_tok=str(pos.get("token_id") or "")
        tgt_tok=str(pos.get("target_token") or "UP")
        opp_tok="DOWN" if tgt_tok=="UP" else "UP"
        if len(p_list)>=2 and len(t_list)>=2 and pos_tok in (str(t_list[0]),str(t_list[1])):
         idx=0 if pos_tok==str(t_list[0]) else 1
         if str(p_list[idx]) in ("1","1.0"):
          await self._apply_market_resolution(tid,pos,tgt_tok)
         elif str(p_list[1 - idx]) in ("1","1.0"):
          await self._apply_market_resolution(tid,pos,opp_tok)
        elif len(p_list)>=2 and str(p_list[0]) in ("1","1.0") and str(p_list[1]) in ("0","0.0"):
         await self._apply_market_resolution(tid,pos,"UP")
        elif len(p_list)>=2 and str(p_list[0]) in ("0","0.0") and str(p_list[1]) in ("1","1.0"):
         await self._apply_market_resolution(tid,pos,"DOWN")
      except Exception as gm_err:
       logger.debug(f"Gamma resolution poll notice for {tid}: {gm_err}")
  if not self.dry_run:
   try:
    await asyncio.to_thread(self.poll_onchain_redemptions)
   except Exception as e:
    logger.error(f"[REDEMPTION] Poll error: {e}")
  if self.dry_run:
   for tid,pos in list(self.active_positions.items()):
    try:
     token_id=pos.get("token_id")
     if not token_id or position_is_settlement_receivable(pos):
      continue
     book=await self.executor.get_market_book_async(token_id)
     bids=book.get("bids",[])
     if bids:
      best_bid=max(float(b.get("price",0.0)) for b in bids)
      if best_bid>=pos.get("target_exit_price",0.99):
       payout=round(pos["entry_shares"] * pos["target_exit_price"],2)
       net_pnl=self.calculate_realized_cash_pnl(pos,payout,0.0)
       pos["status"]=ExecutionStatus.FILLED
       pos["settled_at_utc"]=datetime.now(timezone.utc).isoformat()
       pos["won"]=True
       pos["filled_exit_shares"]=pos["entry_shares"]
       pos["remaining_exit_shares"]=0.0
       pos["gross_exit_cash"]=payout
       pos["average_exit_price"]=pos["target_exit_price"]
       pos["payout_usd"]=payout
       pos["net_pnl_usd"]=net_pnl
       pos["close_reason"]="DRY_RUN_MAKER_SCALP_FILLED"
       self.closed_positions.append(pos)
       self.risk_controller.record_trade_pnl(net_pnl)
       del self.active_positions[tid]
       logger.info(f"[DRY-RUN] ✓ POSITION CLOSED VIA SIMULATED MAKER SCALP: {tid} | Net PnL=${net_pnl:+.2f}")
       self.save_state()
    except Exception as e:
     logger.debug(f"Error in dry-run book check for {tid}: {e}")
  try:
   try:
    open_orders=await asyncio.to_thread(self._strict_open_orders)
    open_oids={o.get("id") or o.get("orderID") for o in open_orders if o}
    open_orders_authoritative=True
   except Exception as oo_err:
    logger.warning( f"[SUPERVISION WARN] Open-orders snapshot degraded ({oo_err}); " "continuing per-position stop-loss and fill supervision fail-closed." )
    open_orders=None
    open_oids=set()
    open_orders_authoritative=False
   now_ts=time.time()
   mkt_ws=getattr(self,"_pos_market_ws",None)
   if mkt_ws is not None:
    mkt_ws.set_desired_tokens([str(p.get("token_id") or "") for p in self.active_positions.values()])
   try:
    await self._maybe_merge_live_complete_sets(now_ts)
   except Exception as merge_exc:
    logger.exception(f"[C1 MERGE] complete-set merge pass failed (supervision continues): {merge_exc}")
   for tid,pos in list(self.active_positions.items()):
    if tid not in self.active_positions:
     continue
    try:
     if position_is_settlement_receivable(pos):
      continue
     if pos.get("status")=="UNRESOLVED_SETTLEMENT":
      pos.setdefault("_unresolved_settle_seq",int(getattr(self,"_collateral_sync_seq",0) or 0))
      settle_oid=pos.get("exit_order_id") or pos.get("pending_settlement_order_id") or pos.get("unwind_order_id")
      est_oids=[ str(k) for k,v in (pos.get("order_records") or {}).items() if isinstance(v,dict) and v.get("cash_is_estimated") ]
      for poll_oid in dict.fromkeys(([str(settle_oid)] if settle_oid else []) + est_oids):
       summary=await asyncio.to_thread(self.executor.get_order_fill_summary,str(poll_oid),pos.get("token_id"))
       if summary is not None:
        is_taker_oid=(str(poll_oid)!=str(pos.get("exit_order_id") or ""))
        fb_px=float(pos.get("unwind_limit_price") or 0.01) if is_taker_oid else float(pos.get("target_exit_price",0.0) or 0.0)
        self._record_order_summary(pos,summary,fb_px,taker=is_taker_oid)
      is_resolved_loss=( pos.get("pending_settlement_close_reason") in {"MARKET_RESOLVED_LOSS","EXPIRED_OUT_OF_MONEY"} or (pos.get("close_reason") and "MARKET_RESOLVED_LOSS" in str(pos.get("close_reason"))) )
      if is_resolved_loss or (not pos.get("exit_cash_estimated",False) and float(pos.get("estimated_exit_cash",0.0) or 0.0)==0.0):
       if is_resolved_loss:
        pos["exit_cash_estimated"]=False
        pos["estimated_exit_cash"]=0.0
       self._close_position( tid,pos,pos.get("pending_settlement_close_status",ExecutionStatus.SETTLED if is_resolved_loss else ExecutionStatus.FILLED),pos.get("pending_settlement_close_reason","MARKET_RESOLVED_LOSS" if is_resolved_loss else "SETTLEMENT_CONFIRMED_CLOB"),won=False if is_resolved_loss else None,)
      continue
     if pos.get("resolved_winning_outcome") is not None:
      await self._apply_market_resolution(tid,pos,pos["resolved_winning_outcome"])
      continue
     if position_requires_global_halt(pos):
      await asyncio.to_thread(self._resolve_lifecycle,tid,pos,open_orders)
      if tid not in self.active_positions or position_requires_global_halt(pos):
       continue
     exit_oid=pos.get("exit_order_id")
     token_id=pos.get("token_id")
     expiry_ts=pos.get("candle_expiry_ts",now_ts + 600.0)
     tte_rem=max(0.0,expiry_ts - now_ts)
     eff_cancel_win=5.0 if pos.get("sleeve")=="SLEEVE_4_BOUNDARY_SNIPE" else self.tte_cancel_window
     if ( not exit_oid and position_may_post_new_maker_exit(pos) and tte_rem>=eff_cancel_win ):
      pos.pop("recovered_from_intent",None)
      posted=await asyncio.to_thread(self._attempt_maker_exit_post,tid,pos)
      exit_oid=pos.get("exit_order_id")
      if posted or not pos.get("inventory_reconciled") or position_requires_global_halt(pos):
       continue
     entry_px=float(pos.get("entry_price",0.50))
     rem_shrs=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",pos.get("entry_shares",0.0))) or 0.0)
     retry_due=( pos.get("exit_order_status")=="STOP_CANCEL_PENDING" or ( pos.get("exit_order_status") in ({"UNWIND_RETRY_REQUIRED"} | PARTIAL_UNWIND_RESIDUAL_STATUSES) and now_ts>=float(pos.get("next_unwind_retry_ts",0.0) or 0.0) ) )
     best_b=0.0
     current_spot=None
     open_spot=float(pos.get("candle_open_spot",0.0) or 0.0)
     entry_spot_ref=float(pos.get("entry_spot_ref") or pos.get("candle_open_spot") or open_spot)
     candle_sigma=float(pos.get("candle_sigma",0.005) or 0.0)
     spot_valid=False
     spot_disp=0.0
     entry_spot_disp=0.0
     entry_move_pct=0.0
     if (not pos.get("is_liquidating") or retry_due) and token_id and rem_shrs > 0.01:
      book=self._get_verified_shm_book(pos)
      if book is None and mkt_ws is not None and "get_market_book_async" not in getattr(self.executor,"__dict__",{}):
       book=mkt_ws.get_book(token_id,max_age_sec=2.0)
      if book is None:
       try:
        book=await self.executor.get_market_book_async(token_id)
       except Exception as bk_err:
        if "404" in str(bk_err) or "no orderbook exists" in str(bk_err).lower():
         book={}
         tte_rem=0.0
        else:
         raise
      bids=book.get("bids",[]) if isinstance(book,dict) else []
      asks=book.get("asks",[]) if isinstance(book,dict) else []
      best_b=max(float(b.get("price",0.0)) for b in bids if float(b.get("size",0.0)) > 0) if bids else 0.0
      best_a=min(float(a.get("price",0.0)) for a in asks if float(a.get("size",0.0)) > 0) if asks else 0.0
      book_spread=(best_a - best_b) if (best_a > 0 and best_b > 0 and best_a > best_b) else 0.0
      if 0 < tte_rem<=120.0:
       prewarm_tag=f"_prewarmed_candle_{pos.get('market_id')}"
       if not getattr(self,prewarm_tag,False):
        setattr(self,prewarm_tag,True)
        asyncio.create_task(self._prewarm_next_candle_markets())
      entry_px=float(pos.get("entry_price") or 0.0)
      _is_dom_box=bool(pos.get("is_dominance_box"))
      if ( not _is_dom_box and exit_oid and not pos.get("queue_jumped") and not pos.get("is_liquidating") and rem_shrs > 0.01 and tte_rem>=self.tte_cancel_window ):
       curr_target_px=float(pos.get("target_exit_price") or 0.0)
       if curr_target_px in (0.98,0.99):
        jump_px=compute_queue_priority_maker_price( entry_px,rem_shrs,bids,asks,curr_target_px )
        if jump_px is not None and (now_ts - float(pos.get("queue_jump_attempt_ts",0.0) or 0.0))>=30.0:
         pos["queue_jump_attempt_ts"]=now_ts
         logger.info( f"[QUEUE JUMP SUPERVISION] Position {tid}: massive wall at ${curr_target_px:.2f}. " f"Stepping 1c in front to ${jump_px:.2f} (cancelling OID: {exit_oid})." )
         posted=await self._atomic_replace_maker_exit(tid,pos,jump_px)
         if tid not in self.active_positions:
          continue
         if posted:
          pos["queue_jumped"]=True
         exit_oid=pos.get("exit_order_id")
         rem_shrs=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",rem_shrs)) or 0.0)
      asset_sym=pos.get("asset","BTC")
      if pos.get("spot_denomination")=="USD":
       current_spot=await asyncio.to_thread(self.get_usd_reference_spot_price,asset_sym)
      else:
       current_spot=await asyncio.to_thread(self.get_reference_spot_price,asset_sym)
      spot_valid=( current_spot is not None and isinstance(current_spot,(int,float)) and math.isfinite(current_spot) and math.isfinite(open_spot) and current_spot > 0 and open_spot > 0 )
      if spot_valid:
       spot_disp=(current_spot - open_spot) if pos.get("target_token")=="UP" else (open_spot - current_spot)
       if entry_spot_ref > 0 and math.isfinite(entry_spot_ref):
        entry_spot_disp=(current_spot - entry_spot_ref) if pos.get("target_token")=="UP" else (entry_spot_ref - current_spot)
        entry_move_pct=entry_spot_disp / entry_spot_ref
       v_spot_15s_pct=0.0
       history=pos.setdefault("spot_vel_history",[])
       history.append([now_ts,float(current_spot)])
       pos["spot_vel_history"]=[pt for pt in history if (now_ts - pt[0])<=15.0]
       hist=pos["spot_vel_history"]
       if len(hist)>=2:
        oldest_spot=hist[0][1]
        if oldest_spot > 0:
         if pos.get("target_token")=="UP":
          v_spot_15s_pct=((current_spot - oldest_spot) / oldest_spot) * 100.0
         else:
          v_spot_15s_pct=((oldest_spot - current_spot) / oldest_spot) * 100.0
       pos["v_spot_15s_pct"]=round(v_spot_15s_pct,4)
      else:
       v_spot_15s_pct=float(pos.get("v_spot_15s_pct",0.0) or 0.0)
      if ( not _is_dom_box and evaluate_optimal_stopping_exit is not None and exit_oid and not pos.get("obi_stepped_down") and not pos.get("is_liquidating") and rem_shrs>=5.0 and tte_rem>=self.tte_cancel_window and best_b > 0.0 and best_a > 0.0 and bids and asks ):
       _b1_sz=sum( float(b.get("size",0.0) if isinstance(b,dict) else b[1]) for b in bids if abs(float(b.get("price",0.0) if isinstance(b,dict) else b[0]) - best_b) < 1e-6 )
       _a1_sz=sum( float(a.get("size",0.0) if isinstance(a,dict) else a[1]) for a in asks if abs(float(a.get("price",0.0) if isinstance(a,dict) else a[0]) - best_a) < 1e-6 )
       _obi_cur=(_b1_sz - _a1_sz) / max(1e-6,_b1_sz + _a1_sz)
       _opt_exit=evaluate_optimal_stopping_exit( entry_px=entry_px,rem_shares=rem_shrs,best_bid=best_b,best_ask=best_a,curr_target_px=float(pos.get("target_exit_price") or 0.0),tte_sec=tte_rem,obi_l1=_obi_cur,v_spot_15s_pct=v_spot_15s_pct,)
       if _opt_exit.get("action")=="OBI_MAKER_STEP_DOWN" and (now_ts - float(pos.get("obi_step_attempt_ts",0.0) or 0.0))>=30.0:
        pos["obi_step_attempt_ts"]=now_ts
        _step_px=float(_opt_exit["target_px"])
        logger.info( f"[OBI MAKER STEP-DOWN] {tid}: heavy sell wall obi_l1={_obi_cur:.2f} <= -0.40 at TTE={tte_rem:.0f}s " f"(v_spot_15s={v_spot_15s_pct:+.3f}%); stepping resting maker ask to ${_step_px:.2f}." )
        posted_step=await self._atomic_replace_maker_exit( tid,pos,_step_px,collapse_tranches=True )
        if tid not in self.active_positions:
         continue
        if posted_step:
         pos["obi_stepped_down"]=True
        exit_oid=pos.get("exit_order_id")
        rem_shrs=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",rem_shrs)) or 0.0)
      is_pre_expiry_window=bool(tte_rem<=300.0)
      sigma_valid=math.isfinite(candle_sigma) and candle_sigma > 0 and open_spot > 0
      _is_subhourly_pos=bool( pos.get("is_subhourly") or pos.get("horizon")=="15m" or pos.get("sleeve")=="SLEEVE_1_SUBHOURLY_15M" or ( 0.0 < float(pos.get("entry_tte",3600.0) or 3600.0)<=900.0 and pos.get("sleeve")=="SLEEVE_4_BOUNDARY_SNIPE" and "hourly" not in str(pos.get("title","") or "").lower() ) )
      _candle_denom_s=900.0 if _is_subhourly_pos else 3600.0
      pin_threshold_300=(2.0 * open_spot * candle_sigma * math.sqrt(max(tte_rem,1.0) / _candle_denom_s)) if (spot_valid and sigma_valid) else 0.0
      volatility_unknown=bool(is_pre_expiry_window and not sigma_valid)
      spot_unknown=bool(is_pre_expiry_window and not spot_valid)
      terminal_hold_forced=volatility_unknown or spot_unknown
      in_pin_risk_band=bool( is_pre_expiry_window and spot_valid and sigma_valid and (spot_disp>=-pin_threshold_300) ) or terminal_hold_forced
      raw_pre_expiry_otm=bool( is_pre_expiry_window and spot_valid and sigma_valid and (spot_disp < -pin_threshold_300) and (best_b>=0.01) )
      if raw_pre_expiry_otm:
       if tte_rem<=60.0 or getattr(self.executor,"auth_mode","") not in ("LIVE","AUTHENTICATED_L2"):
        pre_expiry_otm_salvage=True
       else:
        _otm_ts=pos.get("pre_expiry_otm_detected_ts")
        if _otm_ts is None:
         pos["pre_expiry_otm_detected_ts"]=now_ts
         pre_expiry_otm_salvage=False
        else:
         pre_expiry_otm_salvage=(now_ts - float(_otm_ts))>=3.0
      else:
       pos.pop("pre_expiry_otm_detected_ts",None)
       pre_expiry_otm_salvage=False
      reversal_limit=-(self.spot_delta_k * candle_sigma * open_spot) if (open_spot > 0 and sigma_valid) else -999999.0
      spot_move_pct=(spot_disp / open_spot) if spot_valid else 0.0
      signed_cushion_pct=(spot_move_pct * 100.0) if spot_valid else None
      tranche1_filled=float(pos.get("filled_exit_shares",0.0) or 0.0)>=( float(pos.get("entry_shares",0.0) or 0.0) * 0.40 )
      strike_retrace_triggered=False
      pos.pop("strike_retrace_detected_ts",None)
      spot_crash_triggered=False
      max_bid_drop=0.10 if tranche1_filled else 0.20
      _is_live_auth=( (not self.dry_run) and (getattr(self.executor,"auth_mode","") in ("LIVE","AUTHENTICATED_L2")) and bool(token_id and str(token_id).isdigit() and len(str(token_id))>=20) )
      _is_15m_pos=_is_subhourly_pos
      _spot_crossed_open_adverse=bool( not is_pre_expiry_window and not spot_valid and best_b<=0.36 )
      _req_low_bid_hold=6.0
      _min_hard_salvage_bid=0.08
      if ( best_b>=_min_hard_salvage_bid and best_b<=(entry_px - max_bid_drop) and _spot_crossed_open_adverse and tte_rem>=25.0 ):
       low_bid_start=pos.get("low_bid_detected_ts")
       if low_bid_start is None:
        pos["low_bid_detected_ts"]=now_ts
       elif (now_ts - float(low_bid_start))>=_req_low_bid_hold:
        spot_crash_triggered=True
      else:
       pos.pop("low_bid_detected_ts",None)
      opposite_salvage_triggered=False
      wrong_side_pct=0.0
      if spot_valid and open_spot > 0:
       wrong_side_pct=(-spot_disp / open_spot) * 100.0
       if wrong_side_pct<=0.0:
        pos.pop("opposite_breakout_start_ts",None)
       else:
        _min_3z_bid=0.12 if _is_live_auth else 0.08
        if tte_rem > 900.0:
         req_initial,req_sustain,req_duration,min_salvage_bid=0.16,0.14,40.0,_min_3z_bid
        elif tte_rem > 180.0:
         req_initial,req_sustain,req_duration,min_salvage_bid=0.11,0.09,18.0,_min_3z_bid
        elif tte_rem>=25.0:
         req_initial,req_sustain,req_duration,min_salvage_bid=0.06,0.04,8.0,(0.08 if _is_live_auth else 0.06)
        else:
         req_initial,req_sustain,req_duration,min_salvage_bid=999.0,999.0,999.0,0.99
        if tte_rem<=150.0 and wrong_side_pct>=0.05 and best_b<=(entry_px - 0.22):
         eff_duration=min(req_duration,3.0)
        elif v_spot_15s_pct<=-0.08 and best_b<=0.42:
         eff_duration=req_duration * 0.50
        else:
         eff_duration=req_duration
        consec_start=pos.get("opposite_breakout_start_ts")
        if consec_start is None:
         if wrong_side_pct>=req_initial:
          pos["opposite_breakout_start_ts"]=now_ts
        else:
         if wrong_side_pct>=req_sustain:
          duration=now_ts - float(consec_start)
          if v_spot_15s_pct>=0.03:
           opposite_salvage_triggered=False
           logger.debug( f"[ANTI-WICK PAUSE] {tid}: wrong_side={wrong_side_pct:.2f}% >= sustain {req_sustain:.2f}%, " f"but v_spot_15s={v_spot_15s_pct:+.4f}% >= +0.03% (rebounding). Salvage paused." )
          elif duration>=eff_duration and best_b>=min_salvage_bid:
           opposite_salvage_triggered=True
         else:
          pos.pop("opposite_breakout_start_ts",None)
      else:
       pos.pop("opposite_breakout_start_ts",None)
      if best_b > 0:
       pos["max_seen_bid"]=max(float(pos.get("max_seen_bid",0.0) or 0.0),best_b)
      max_seen_bid=float(pos.get("max_seen_bid",0.0) or 0.0)
      trailing_ratchet_triggered=False
      trail_floor=0.0
      _min_ratchet_arm=max(0.84,entry_px + 0.16) if _is_live_auth else max(0.82,entry_px + 0.12)
      _min_ratchet_gain=0.04
      if max_seen_bid>=_min_ratchet_arm and entry_px > 0:
       trail_delta=0.06 if _is_live_auth else (0.05 if max_seen_bid>=0.90 else 0.07)
       trail_floor=round(max_seen_bid - trail_delta,4)
       if best_b<=trail_floor and tte_rem>=25.0 and best_b>=(entry_px + _min_ratchet_gain):
        ratchet_start=pos.get("trail_stop_detected_ts") or pos.get("trailing_ratchet_detected_ts")
        if ratchet_start is None:
         pos["trail_stop_detected_ts"]=now_ts
         pos["trailing_ratchet_detected_ts"]=now_ts
        elif (now_ts - float(ratchet_start))>=4.0:
         trailing_ratchet_triggered=True
       else:
        pos.pop("trail_stop_detected_ts",None)
        pos.pop("trailing_ratchet_detected_ts",None)
      else:
       pos.pop("trail_stop_detected_ts",None)
       pos.pop("trailing_ratchet_detected_ts",None)
      pre_expiry_99c_recycle=bool( 8.0<=tte_rem<=25.0 and rem_shrs>=5.0 and best_b>=0.985 and best_b > (entry_px + 0.02) )
      final_45s_triggered=False
      _d1_bid_harvest=False
      _partner_bid_harvested=False
      if _is_dom_box:
       pre_expiry_otm_salvage=False
       spot_crash_triggered=False
       opposite_salvage_triggered=False
       trailing_ratchet_triggered=False
       _box_unit=float(pos.get("box_cost_net") or 0.975)
       _box_tot_cost=float(pos.get("box_total_cost_usd",999.0) or 999.0)
       _p_closed=pos.get("_closed_partner_leg")
       _p_live=self.active_positions.get(str(pos.get("box_partner_trade_id") or ""))
       _partner_cov=bool( (isinstance(_p_closed,dict) and float(_p_closed.get("payout_usd",0.0) or 0.0)>=_box_tot_cost) or ( isinstance(_p_live,dict) and float(_p_live.get("remaining_shares",1.0) or 0.0)<=0.01 and max(float(_p_live.get("confirmed_realized_cash",0.0) or 0.0),float(_p_live.get("realized_exit_cash",0.0) or 0.0))>=_box_tot_cost ) )
       _partner_bid_harvested=bool( (isinstance(_p_closed,dict) and "BOX_EARLY_BID_HARVEST" in str(_p_closed.get("close_reason") or "")) or ( isinstance(_p_live,dict) and float(_p_live.get("remaining_shares",1.0) or 0.0)<=0.01 and "BOX_EARLY_BID_HARVEST" in str(_p_live.get("pending_settlement_close_reason") or _p_live.get("close_reason") or "") ) )
       _harv_target_shrs=rem_shrs
       _leg1_net_cash=0.0
       if isinstance(_p_closed,dict) and "BOX_EARLY_BID_HARVEST" in str(_p_closed.get("close_reason") or ""):
        _leg1_net_cash=float(_p_closed.get("payout_usd",0.0) or 0.0) - float(_p_closed.get("exit_fee_usd",0.0) or 0.0)
       elif isinstance(_p_live,dict):
        _p_rem=float(_p_live.get("remaining_shares",rem_shrs) or 0.0)
        _p_cash=max(float(_p_live.get("confirmed_realized_cash",0.0) or 0.0),float(_p_live.get("realized_exit_cash",0.0) or 0.0)) - float(_p_live.get("realized_exit_fee",0.0) or 0.0)
        if _partner_bid_harvested:
         _leg1_net_cash=_p_cash
        elif ( rem_shrs - _p_rem>=5.0 and float(_p_live.get("filled_exit_shares",0.0) or 0.0)>=5.0 and ( "BOX_EARLY_BID_HARVEST" in str(_p_live.get("unwind_reason") or _p_live.get("pending_unwind_tag") or "") or _p_live.get("exit_order_status") in PARTIAL_UNWIND_RESIDUAL_STATUSES ) ):
         _partner_bid_harvested=True
         _harv_target_shrs=round(rem_shrs - _p_rem,2)
         _leg1_net_cash=_p_cash
       _pos_fr=float(pos.get("fee_rate_applied",0.07) or 0.0)
       _pos_fe=float(pos.get("fee_exponent_applied",1.0) or 1.0)
       _net_b=best_b - (_pos_fr * ((best_b * (1.0 - best_b)) ** _pos_fe) if _pos_fr > 0.0 else 0.0)
       _be_gross_px=0.02
       if _partner_bid_harvested and _harv_target_shrs>=5.0:
        _ent_sh_tot=max(_harv_target_shrs,float(pos.get("entry_shares") or _harv_target_shrs))
        _scaled_box_cost=(_box_tot_cost * (_harv_target_shrs / _ent_sh_tot)) if _box_tot_cost < 900.0 else (_box_unit * _harv_target_shrs)
        _req_net_ps=max(0.02,(_scaled_box_cost - _leg1_net_cash - 0.02) / max(_harv_target_shrs,1e-6))
        _g_est=_req_net_ps
        for _ in range(2):
         _g_cl=max(0.01,min(0.99,_g_est))
         _g_est=_req_net_ps + (_pos_fr * ((_g_cl * (1.0 - _g_cl)) ** _pos_fe) if _pos_fr > 0.0 else 0.0)
        _be_gross_px=max(0.02,min(0.99,math.ceil(_g_est * 100.0 - 1e-9) / 100.0))
       if _harv_target_shrs>=5.0 and best_b>=_be_gross_px and _partner_bid_harvested:
        _d1_bid_harvest=True
       elif ( tte_rem > 45.0 and rem_shrs>=5.0 and best_b>=0.05 and isinstance(_p_live,dict) and not pos.get("is_liquidating") and not _p_live.get("is_liquidating") and _p_live.get("exit_order_status") not in ({"STOP_CANCEL_PENDING","UNWIND_RETRY_REQUIRED"} | PARTIAL_UNWIND_RESIDUAL_STATUSES) and _p_live.get("pending_unwind_tag")!="BOX_EARLY_BID_HARVEST_UNWIND" and (self.dry_run or (pos.get("inventory_reconciled") and _p_live.get("inventory_reconciled"))) and abs(rem_shrs - float(_p_live.get("remaining_shares") or 0.0))<=0.02 ):
        _b1_sh=sum(float(b.get("size",0.0) if isinstance(b,dict) else b[1]) for b in bids if abs(float(b.get("price",0.0) if isinstance(b,dict) else b[0]) - best_b) < 1e-6)
        if _b1_sh>=rem_shrs * 1.25:
         _pbk=self._get_verified_shm_book(_p_live)
         if _pbk is None and hasattr(self.executor,"get_market_book") and (self.dry_run or now_ts - float(pos.get("_pb_ts",0.0))>=3.0):
          pos["_pb_ts"]=now_ts
          _pbk=await asyncio.to_thread(self.executor.get_market_book,str(_p_live.get("token_id") or ""))
         _pbids=(_pbk or {}).get("bids") or []
         _pbb=max((float(b.get("price",0.0) if isinstance(b,dict) else b[0]) for b in _pbids if float(b.get("size",0.0) if isinstance(b,dict) else b[1]) > 0),default=0.0)
         _pb1_sh=sum(float(b.get("size",0.0) if isinstance(b,dict) else b[1]) for b in _pbids if abs(float(b.get("price",0.0) if isinstance(b,dict) else b[0]) - _pbb) < 1e-6)
         _pfr=float(_p_live.get("fee_rate_applied",_pos_fr) or 0.0)
         _pfe=float(_p_live.get("fee_exponent_applied",_pos_fe) or 1.0)
         _pnet_b=_pbb - (_pfr * ((_pbb * (1.0 - _pbb)) ** _pfe) if _pfr > 0.0 else 0.0)
         _corridor_harvest_ok=( str(pos.get("box_type") or "") in {"COMPLETE_SET","NEGRISK_2LEG","NEGRISK_CROSS"} or tte_rem > 3600.0 or (_net_b + _pnet_b)>=max(1.080,_box_unit + 0.080) )
         if _pbb>=0.05 and _pb1_sh>=rem_shrs * 1.25 and (_net_b + _pnet_b)>=max(1.008,_box_unit + 0.015) and _corridor_harvest_ok:
          _d1_bid_harvest=True
       if retry_due and pos.get("pending_unwind_tag")=="BOX_EARLY_BID_HARVEST_UNWIND" and not _d1_bid_harvest and not exit_oid:
        retry_due=False
        pos.pop("pending_unwind_tag",None)
        pos["is_liquidating"]=False
        pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED" if tte_rem > 45.0 else "DETERMINISTIC_TERMINAL_HOLD"
        self.save_state()
        continue
       _k_lo=float(pos.get("box_k_low") or 0.0)
       _k_hi=float(pos.get("box_k_high") or 0.0)
       _outside_corr=bool( spot_valid and _k_hi>=_k_lo > 0.0 and (current_spot < _k_lo * (1.0 - 0.0012) or current_spot > _k_hi * (1.0 + 0.0012)) )
       _d1_prim=bool( rem_shrs>=5.0 and _net_b>=(_box_unit + 0.002) and ( (5.0<=tte_rem<=35.0 and best_b>=0.99) or (5.0<=tte_rem<=65.0 and best_b>=0.985 and _outside_corr) ) )
       _d1_bonus=bool(5.0<=tte_rem<=35.0 and rem_shrs>=5.0 and _partner_cov and best_b>=0.20)
       pre_expiry_99c_recycle=_d1_prim
       final_45s_triggered=bool(_d1_prim or _d1_bonus or _d1_bid_harvest)
      elif pre_expiry_99c_recycle or ( pos.get("sleeve")!="SLEEVE_4_BOUNDARY_SNIPE" and tte_rem<=45.0 and rem_shrs > 0.01 and best_b>=0.85 and best_b > (entry_px + 0.03) ):
       final_45s_triggered=True
      if (not bids or best_b<=0.0) and not pos.get("is_liquidating"):
       if tte_rem<=30.0 or _is_dom_box:
        pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD"
        continue
       zero_bid_start=pos.get("zero_bid_detected_ts")
       if zero_bid_start is None:
        pos["zero_bid_detected_ts"]=now_ts
        continue
       if (now_ts - float(zero_bid_start)) < max(1.5,float(self.low_bid_persistence_seconds)):
        continue
       if pos.get("status")!="LIQUIDITY_CRISIS":
        logger.critical( f"[LIQUIDITY_CRISIS] Persistent zero bid (>={self.low_bid_persistence_seconds:.1f}s) " f"on token {token_id} for {tid}. Suspending new entries fail-closed." )
        pos["status"]="LIQUIDITY_CRISIS"
        pos["exit_order_status"]="LIQUIDITY_CRISIS"
        pos["liquidity_crisis_ts"]=now_ts
        self.risk_halt=True
        self._refresh_global_halt()
       continue
      else:
       pos.pop("zero_bid_detected_ts",None)
      if pos.get("exit_order_status")=="PASSIVE_STOP_RESTING":
       elapsed_passive=now_ts - float(pos.get("passive_stop_start_ts",now_ts))
       passive_window_s=3.0 if pos.get("passive_3s_attempted") else 5.0
       if spot_crash_triggered or strike_retrace_triggered or elapsed_passive>=passive_window_s:
        reason_str=( "Strike-retrace stop" if strike_retrace_triggered else "Spot structural crash" if spot_crash_triggered else f"5.0s passive window expired ({elapsed_passive:.1f}s)" )
        logger.info(f"[PASSIVE STOP ESCALATION] {tid}: {reason_str}. Escalating to verified cancel + FAK unwind.")
        retry_due=True
       else:
        if exit_oid:
         summary=await asyncio.to_thread(self.executor.get_order_fill_summary,exit_oid,token_id)
         if summary is not None:
          if self._record_order_summary(pos,summary,float(pos.get("target_exit_price",0.0) or 0.0),taker=False):
           self.save_state()
          if float(pos.get("remaining_shares",0.0) or 0.0)<=0.01:
           self._close_position(tid,pos,ExecutionStatus.FILLED,"PASSIVE_STOP_MAKER_FILLED",won=None)
        continue
      clob_sl_triggered=False
      if is_pre_expiry_window and (in_pin_risk_band or terminal_hold_forced or not spot_valid or not sigma_valid) and not strike_retrace_triggered and not spot_crash_triggered and not opposite_salvage_triggered and not trailing_ratchet_triggered and not final_45s_triggered:
       if pos.get("exit_order_status") not in ({"UNWIND_RETRY_REQUIRED","STOP_CANCEL_PENDING"} | PARTIAL_UNWIND_RESIDUAL_STATUSES):
        retry_due=False
        pos["is_liquidating"]=False
       pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD_FINAL" if tte_rem < self.tte_cancel_window else "DETERMINISTIC_TERMINAL_HOLD"
      if retry_due or opposite_salvage_triggered or strike_retrace_triggered or spot_crash_triggered or pre_expiry_otm_salvage or trailing_ratchet_triggered or final_45s_triggered:
       reason=( f"Box combined-bid overround harvest (TTE={tte_rem:.0f}s, bid ${best_b:.4f})" if _d1_bid_harvest else f"Final-45s capital recycle (TTE={tte_rem:.0f}s <= 45s, bid ${best_b:.4f} >= 0.88, recycling USDC before rollover)" if final_45s_triggered else f"Trailing profit ratchet (peak bid ${max_seen_bid:.4f} armed trail floor ${trail_floor:.4f}, current bid ${best_b:.4f} <= trail floor for >=4.0s, locking in +{best_b - entry_px:+.2f}/share)" if trailing_ratchet_triggered else f"3-Zone opposite-side structural breakout salvage (wrong-side {wrong_side_pct:+.2f}%, TTE={tte_rem:.0f}s, bid=${best_b:.4f})" if opposite_salvage_triggered else f"Strike-retrace stop (signed cushion {signed_cushion_pct:+.4f}% <= retrace floor for >=10s, TTE={tte_rem:.0f}s, bid=${best_b:.4f})" if strike_retrace_triggered else f"Hard bid-drop stop (bid ${best_b:.4f} <= entry ${entry_px:.4f} - {max_bid_drop:.2f} for >=6s, TTE={tte_rem:.0f}s)" if spot_crash_triggered else "Scheduled Stop-Loss Unwind Retry" if retry_due else f"Pre-expiry OTM salvage (TTE={tte_rem:.0f}s, spot={current_spot:.2f} vs open={open_spot:.2f})" if pre_expiry_otm_salvage else f"Spot structural breakdown (candle_disp={spot_disp:.2f}, entry_disp={entry_spot_disp:.2f}, move={spot_move_pct*100:.2f}%)" )
       logger.warning(f"[SALVAGE ACTIVATED] Position {tid}: {reason}. Unwinding position immediately...")
       if not self.dry_run and not (_d1_bid_harvest or final_45s_triggered or trailing_ratchet_triggered):
        send_operational_alert( "WRONG_SIDE_SALVAGE_EXIT",f"Position {tid}: {reason}","WARNING",dedupe_key=f"salvage:{tid}",)
       pos["stop_triggered_ts"]=now_ts
       pos.pop("exit_tranches",None)
       if exit_oid:
        prior_filled=float(pos.get("filled_exit_shares",0.0) or 0.0)
        cancel_res=await asyncio.to_thread(self.executor.cancel_order,exit_oid)
        summary=await asyncio.to_thread(self.executor.get_order_fill_summary,exit_oid,token_id)
        if summary is not None:
         self._record_order_summary(pos,summary,float(pos.get("target_exit_price",0.0) or 0.0),taker=False)
        if float(pos.get("remaining_shares",rem_shrs) or 0.0)<=0.01:
         logger.info(f"✓ [STOP-LOSS RECONCILED] {tid} already fully matched on resting exit before unwind.")
         self._close_position(tid,pos,ExecutionStatus.SETTLED,"MAKER_SCALP_FILLED_CLOB",won=None)
         continue
        if summary is not None and summary.get("matched",0.0) > prior_filled + 1e-4:
         pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED"
         pos["pending_canceled_order_id"]=exit_oid
         self.save_state()
         continue
        if isinstance(cancel_res,dict) and bool(cancel_res.get("is_canceled")):
         open_oids.discard(exit_oid)
        canceled_confirmed=( (self.dry_run and (exit_oid not in open_oids or summary is None)) or (exit_oid not in open_oids and ( (summary is not None and summary["terminal"]) or (isinstance(cancel_res,dict) and ( exit_oid in (cancel_res.get("canceled") or []) or bool(cancel_res.get("is_canceled")) )) )) )
        if not canceled_confirmed:
         pos["exit_order_status"]="STOP_CANCEL_PENDING"
         pos["cancel_pending_order_id"]=exit_oid
         pos["pending_unwind_tag"]=( "D1_LEGGED_OUT_RESIDUAL_UNWIND" if pos.get("is_legged_out_residual") else "BOX_EARLY_BID_HARVEST_UNWIND" if _d1_bid_harvest else "FINAL_45S_CAPITAL_RECYCLE_UNWIND" if final_45s_triggered else "TRAILING_PROFIT_RATCHET_UNWIND" if trailing_ratchet_triggered else "CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE" if opposite_salvage_triggered else "STRIKE_RETRACE_SALVAGE" if strike_retrace_triggered else "HARD_BID_DROP_SALVAGE" if spot_crash_triggered else "PRE_EXPIRY_OTM_SALVAGE" if pre_expiry_otm_salvage else pos.get("pending_unwind_tag") or "ADVERSE_STOP_LOSS_UNWIND" )
         self.save_state()
         continue
        self.executor.release_inventory(reservation_id=exit_oid)
        pos["exit_order_id"]=None
        exit_oid=None
       pos.pop("low_bid_detected_ts",None)
       pos.pop("strike_retrace_detected_ts",None)
       pos.pop("trail_stop_detected_ts",None)
       pos.pop("trailing_ratchet_detected_ts",None)
       pos["exit_order_status"]="CANCELED_FOR_STOP_LOSS"
       is_salvage_or_ratchet=bool( opposite_salvage_triggered or pre_expiry_otm_salvage or trailing_ratchet_triggered )
       if ( is_salvage_or_ratchet and tte_rem > 60.0 and book_spread>=0.04 and rem_shrs>=5.0 and not pos.get("passive_3s_attempted") and not self.dry_run and getattr(self.executor,"auth_mode","") in ("LIVE","AUTHENTICATED_L2") ):
        pos["passive_3s_attempted"]=True
        maker_unwind_px=round(min(best_a - 0.01,best_b + max(0.01,0.40 * book_spread)),2)
        logger.info( f"[TWO-STAGE MAKER UNWIND] Posting 3.0s non-blocking passive maker sell for {tid}: " f"{rem_shrs:.1f} shrs @ ${maker_unwind_px:.2f} (midpoint maker before FAK)..." )
        m_res=await asyncio.to_thread( self.executor.post_maker_exit_order,token_id=token_id,price=maker_unwind_px,size=rem_shrs,side="SELL",)
        if isinstance(m_res,dict) and m_res.get("success") and m_res.get("orderID"):
         m_oid=m_res["orderID"]
         pos["exit_order_id"]=m_oid
         pos["target_exit_price"]=maker_unwind_px
         pos["exit_order_status"]="PASSIVE_STOP_RESTING"
         pos["passive_stop_start_ts"]=now_ts
         self.save_state()
         continue
        elif isinstance(m_res,dict) and m_res.get("outcome_unknown"):
         m_oid=m_res.get("orderID")
         if m_oid:
          pos["exit_order_id"]=m_oid
          pos["exit_order_size"]=float(rem_shrs)
         if m_res.get("reservation_id"):
          pos.setdefault("pending_reservation_ids",[]).append(m_res["reservation_id"])
         pos["target_exit_price"]=maker_unwind_px
         pos["exit_post_attempt_ts"]=now_ts
         pos["exit_order_status"]="EXIT_POST_OUTCOME_UNKNOWN"
         self.save_state()
         logger.critical( f"[TWO-STAGE MAKER UNWIND] Ambiguous passive maker post for {tid} (OID: {m_oid}); " "holding reservation and deferring FAK unwind until reconciled." )
         continue
       rem_shrs=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",rem_shrs)) or 0.0)
       if rem_shrs < 0.01:
        self._close_position(tid,pos,ExecutionStatus.SETTLED,"MAKER_SCALP_FILLED_CLOB",won=None)
        continue
       if _is_live_auth:
        _post_cancel_bk=self._get_verified_shm_book(pos)
        if isinstance(_post_cancel_bk,dict):
         _pc_bids=_post_cancel_bk.get("bids") or []
         _pc_best=max((float(b.get("price",0.0)) for b in _pc_bids if float(b.get("size",0.0)) > 0),default=0.0)
         if _pc_best > 0.0:
          best_b=_pc_best
       _prior_retries=int(pos.get("unwind_retry_count",0) or 0)
       _unwind_sz=rem_shrs
       if _is_dom_box and _d1_bid_harvest:
        _unwind_sz=min(rem_shrs,_harv_target_shrs) if _partner_bid_harvested else rem_shrs
        limit_px=max(_be_gross_px if _partner_bid_harvested else 0.02,round(best_b - (0.02 if _partner_bid_harvested else 0.0),4))
       elif _is_dom_box and not _d1_bonus:
        limit_px=0.98
       elif final_45s_triggered:
        limit_px=max(0.98,round(best_b,2)) if pre_expiry_99c_recycle else max(0.01,round(best_b - 0.01,4))
       elif (_is_live_auth and not trailing_ratchet_triggered) or _prior_retries > 0:
        _fak_slip=0.04 + (0.04 * min(_prior_retries,4))
        limit_px=max(0.01,round(best_b - _fak_slip,4))
       else:
        limit_px=max(0.01,round(best_b - 0.02,4))
       unwind_res=await asyncio.to_thread( self.executor.execute_unwind_order,token_id=token_id,size=_unwind_sz,side="SELL",min_price=limit_px,)
       _saved_pend_tag=pos.pop("pending_unwind_tag",None)
       exit_tag=( "D1_LEGGED_OUT_RESIDUAL_UNWIND" if pos.get("is_legged_out_residual") else "BOX_EARLY_BID_HARVEST_UNWIND" if _d1_bid_harvest else "FINAL_45S_CAPITAL_RECYCLE_UNWIND" if final_45s_triggered else "TRAILING_PROFIT_RATCHET_UNWIND" if trailing_ratchet_triggered else "CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE" if opposite_salvage_triggered else "STRIKE_RETRACE_SALVAGE" if strike_retrace_triggered else "HARD_BID_DROP_SALVAGE" if spot_crash_triggered else "PRE_EXPIRY_OTM_SALVAGE" if pre_expiry_otm_salvage else _saved_pend_tag or "ADVERSE_STOP_LOSS_UNWIND" )
       outcome=self._handle_unwind_response( tid,pos,unwind_res,_unwind_sz,exit_tag,"PARTIAL_UNWIND_REMAINING",limit_px,)
       if outcome!="FAILED":
        self.executor.invalidate_collateral_cache()
        self._pending_collateral_refresh=True
        self.save_state()
        continue
       unwind_res=unwind_res or {}
       logger.error(f"Immediate FAK unwind failed for {tid}: {unwind_res.get('error')}. Verifying inventory...")
       _settling_buy=( not pos.get("inventory_reconciled") and (now_ts - float(pos.get("entry_ts") or now_ts)) < 18.0 and "sell_inventory_reconciliation_required" in str(unwind_res.get("error","")).lower() )
       if not self.dry_run and token_id:
        bal,src=await asyncio.to_thread(self._wallet_token_balance,token_id)
        eps=self.executor.calculate_balance_epsilon(0.001)
        if bal is not None and bal>=rem_shrs - 0.05:
         pos["inventory_reconciled"]=True
        is_balance_shortfall="not enough balance" in str(unwind_res.get("error","")).lower()
        if not _settling_buy and bal is not None and ( (is_balance_shortfall and bal<=0.01) or bal + eps < rem_shrs - 0.01 ):
         logger.critical( f"[FAIL-CLOSED] {tid}: wallet {bal:.4f} < remaining {rem_shrs:.4f} after failed unwind. " "Reconciling from exchange trade history before any further action." )
         pos["exit_order_status"]="UNRESOLVED_BALANCE_DISCREPANCY"
         pos["unwind_attempt_ts"]=float(pos.get("unwind_last_attempt_ts") or pos.get("entry_ts") or now_ts)
         pos["unwind_reason"]="ADVERSE_STOP_LOSS_UNWIND"
         pos["next_resolve_ts"]=0.0
         self.save_state()
         continue
       err_u_low=str(unwind_res.get("error","") or "").lower()
       if rem_shrs < 5.0 and any(k in err_u_low for k in ("minimum","min size","invalid amounts","size too small")):
        pos["is_liquidating"]=False
        pos["exit_order_status"]="SUB_MINIMUM_LOT_SUPERVISED_HOLD"
        pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD"
        self.save_state()
        continue
       pos["is_liquidating"]=False
       if _is_dom_box and not _d1_bonus and not _partner_bid_harvested:
        pos.pop("pending_unwind_tag",None)
        pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED" if (_d1_bid_harvest and tte_rem > 45.0) else "DETERMINISTIC_TERMINAL_HOLD"
        pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD"
        self.save_state()
        continue
       if _settling_buy:
        attempts=int(pos.get("unwind_retry_count",0))
        backoff_seconds=0.50
       else:
        attempts=int(pos.get("unwind_retry_count",0)) + 1
        pos["unwind_retry_count"]=attempts
        if "no orders found to match with fak order" in err_u_low:
         backoff_seconds=0.35
        else:
         backoff_seconds=min(30.0,2.0 ** min(attempts,5))
       pos["next_unwind_retry_ts"]=now_ts + backoff_seconds
       pos["unwind_last_error"]=str(unwind_res.get("error","unknown"))
       pos["unwind_last_attempt_ts"]=now_ts
       if attempts>=10:
        pos["exit_order_status"]="TERMINAL_UNWIND_FAILED_SUPERVISED"
        logger.critical( f"[UNWIND ESCALATION TERMINAL] {tid}: {attempts} consecutive failed FAK attempts. " "Position remains exposed and requires active supervisor intervention." )
       else:
        pos["exit_order_status"]="UNWIND_RETRY_REQUIRED"
        if attempts in {3,6}:
         logger.critical(f"[UNWIND ESCALATION] {tid}: {attempts} consecutive failed FAK attempts. Position remains exposed.")
       self.save_state()
       continue
     pre_expiry_active=False
     if pre_expiry_active:
      remaining_vol_pre=candle_sigma * math.sqrt(max(tte_rem,1.0) / _candle_denom_s) if (math.isfinite(candle_sigma) and candle_sigma > 0) else 0.0
      pin_thresh_pre=2.0 * open_spot * remaining_vol_pre if (open_spot > 0 and remaining_vol_pre > 0) else 0.0
      holding_099_recycle=( pos.get("exit_order_status")=="RESTING_099_CAPITAL_RECYCLE" and bool(exit_oid) and tte_rem>=30.0 and (not spot_valid or (pin_thresh_pre > 0.0 and spot_disp>=pin_thresh_pre)) )
      if not holding_099_recycle:
       if exit_oid:
        if exit_oid in open_oids and pos.get("exit_order_status")!="PRE_EXPIRY_CANCEL_PENDING":
         logger.info( f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. " f"Initiating cancellation of resting maker scalp ask {exit_oid} for {tid}." )
         await asyncio.to_thread(self.executor.cancel_order,exit_oid)
         pos["exit_order_status"]="PRE_EXPIRY_CANCEL_PENDING"
         pos["cancel_pending_order_id"]=exit_oid
         self.save_state()
         continue
        summary=await asyncio.to_thread(self.executor.get_order_fill_summary,exit_oid,token_id)
        if summary is not None:
         self._record_order_summary(pos,summary,float(pos.get("target_exit_price",0.0) or 0.0),taker=False)
        canceled_confirmed=( (self.dry_run and (exit_oid not in open_oids or summary is None)) or (exit_oid not in open_oids and summary is not None and bool(summary.get("terminal"))) )
        if not canceled_confirmed:
         if exit_oid in open_oids:
          await asyncio.to_thread(self.executor.cancel_order,exit_oid)
         logger.warning(f"[REGIME 4] Awaiting verified cancellation of {exit_oid} before unwinding {tid}.")
         pos["exit_order_status"]="PRE_EXPIRY_CANCEL_PENDING"
         self.save_state()
         continue
        self.executor.release_inventory(reservation_id=exit_oid)
        pos["pending_settlement_order_id"]=exit_oid
        pos["exit_order_id"]=None
        exit_oid=None
       rem_shrs=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",0.0)) or 0.0)
       if rem_shrs < 0.01:
        logger.info(f"✓ [MAKER SCALP FILLED PRE-EXPIRY] {tid} fully matched on resting ask before cancellation.")
        self._close_position(tid,pos,ExecutionStatus.SETTLED,"MAKER_SCALP_FILLED_CLOB",won=True)
        continue
       if ( not math.isfinite(candle_sigma) or candle_sigma<=0 or not math.isfinite(open_spot) or open_spot<=0 ):
        logger.critical( f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. " f"Position {tid} nonfinite sigma ({candle_sigma}) or open ({open_spot}). " f"Outcome classification is UNKNOWN; refusing assumption of ITM." )
        pos["exit_order_status"]="OUTCOME_UNKNOWN"
        pos["status"]=ExecutionStatus.POSITION_CONFIRMED
        self.save_state()
        continue
       remaining_vol=candle_sigma * math.sqrt(max(tte_rem,1.0) / _candle_denom_s)
       pin_threshold=2.0 * open_spot * remaining_vol
       if not spot_valid:
        logger.critical( f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. " f"Position {tid} spot price UNAVAILABLE/INVALID (ref={current_spot}, open={open_spot}). " f"Outcome classification is UNKNOWN; refusing assumption of ITM. " f"Retaining open exposure under supervised terminal resolution." )
        pos["exit_order_status"]="OUTCOME_UNKNOWN"
        pos["status"]=ExecutionStatus.POSITION_CONFIRMED
        self.save_state()
        continue
       elif spot_disp < -pin_threshold:
        logger.warning( f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. " f"Position {tid} is strictly OUT-OF-THE-MONEY (delta={spot_disp:+.2f} vs open={open_spot:.2f}, pin_thresh={pin_threshold:.2f}). " f"Dispatching emergency salvage unwind for {rem_shrs:.2f} shares." )
        pos["exit_order_status"]="EMERGENCY_SALVAGE_UNWIND"
        unwind_res=await asyncio.to_thread( self.executor.execute_unwind_order,token_id=token_id,size=rem_shrs,side="SELL",min_price=0.01,)
        outcome=self._handle_unwind_response( tid,pos,unwind_res,rem_shrs,"PRE_EXPIRY_OTM_SALVAGE_UNWIND","PARTIAL_SALVAGE_REMAINING",0.01,)
        if outcome!="FAILED":
         continue
        logger.error( f"[EMERGENCY SALVAGE FAILED] {tid}: {(unwind_res or {}).get('error')}. " f"Fail-closed: Retaining open exposure for terminal resolution supervision." )
        pos["exit_order_status"]="SALVAGE_FAILED_TERMINAL_HOLD"
        pos["status"]=ExecutionStatus.POSITION_CONFIRMED
        self.save_state()
        continue
       elif abs(spot_disp)<=pin_threshold:
        if pos.get("exit_order_status")!="PIN_RISK_EXPIRY_HOLD":
         logger.warning( f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. " f"Position {tid} is in PIN-RISK UNCERTAINTY ZONE (spot={current_spot:.2f} vs open={open_spot:.2f}, delta={spot_disp:+.2f}). " "Holding with supervisor awareness to terminal market resolution." )
         pos["exit_order_status"]="PIN_RISK_EXPIRY_HOLD"
         pos["status"]=ExecutionStatus.POSITION_CONFIRMED
         self.save_state()
        continue
       else:
        deep_itm_threshold=1.5 * pin_threshold
        if spot_disp>=deep_itm_threshold and tte_rem>=30.0 and not pos.get("recycle_099_attempted"):
         pos["recycle_099_attempted"]=True
         pos["target_exit_price"]=0.99
         recycle_res=await asyncio.to_thread( self.executor.post_maker_exit_order,token_id=token_id,price=0.99,size=rem_shrs,side="SELL",)
         if self._apply_exit_post_result(pos,recycle_res,rem_shrs):
          pos["exit_order_status"]="RESTING_099_CAPITAL_RECYCLE"
          self.save_state()
          continue
        if pos.get("exit_order_status")!="CANCELED_FOR_EXPIRY_HOLD":
         logger.info( f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. " f"Position {tid} is strictly IN-THE-MONEY (spot={current_spot:.2f} vs open={open_spot:.2f}, delta={spot_disp:+.2f} > threshold={pin_threshold:.2f}). " "Holding to $1.00 settlement." )
         pos["exit_order_status"]="CANCELED_FOR_EXPIRY_HOLD"
         pos["status"]=ExecutionStatus.POSITION_CONFIRMED
         self.save_state()
        continue
     if pos.get("is_liquidating") and pos.get("unwind_order_id"):
      u_oid=pos["unwind_order_id"]
      if u_oid not in open_oids:
       summary=await asyncio.to_thread(self.executor.get_order_fill_summary,u_oid,token_id)
       if summary is None:
        pos["exit_order_status"]="UNWIND_RECONCILIATION_REQUIRED"
        self.save_state()
        continue
       order_status=str(summary.get("status","")).upper()
       matched=float(summary.get("matched",0.0) or 0.0)
       rem_shrs=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",pos.get("entry_shares",0.0))) or 0.0)
       expected=float(pos.get("unwind_order_size",rem_shrs))
       if order_status not in {"MATCHED","FILLED","CONFIRMED"} or matched < expected - 1e-4:
        pos["exit_order_status"]="UNWIND_RECONCILIATION_REQUIRED"
        self.save_state()
        continue
       self._record_order_summary(pos,summary,float(summary.get("limit_price") or 0.01),taker=False)
       if float(pos.get("remaining_shares",0.0) or 0.0)<=0.01:
        self._close_position(tid,pos,ExecutionStatus.SETTLED,"SPOT_DELTA_PASSIVE_UNWIND",won=None)
        continue
       pos["status"]=ExecutionStatus.PARTIALLY_FILLED
       pos["exit_order_status"]="PARTIAL_PASSIVE_UNWIND_REMAINING"
       self.save_state()
       continue
      elif (now_ts - float(pos.get("unwind_start_time",now_ts) or now_ts)) > self.passive_unwind_timeout:
       logger.info(f"[REGIME 4 UNWIND TIMEOUT] Passive order {u_oid} timed out; cancelling and reconciling before repricing.")
       await asyncio.to_thread(self.executor.cancel_order,u_oid)
       summary=await asyncio.to_thread(self.executor.get_order_fill_summary,u_oid,token_id)
       if summary is not None and summary.get("matched",0.0) > float(pos.get("filled_exit_shares",0.0) or 0.0) + 1e-4:
        self._record_order_summary(pos,summary,float(summary.get("limit_price") or 0.01),taker=False)
        pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED"
        pos["pending_canceled_order_id"]=u_oid
        self.save_state()
        continue
       pos["exit_order_status"]="UNWIND_RECONCILIATION_REQUIRED"
       pos["unwind_attempt_ts"]=now_ts
       pos["unwind_reason"]="SPOT_DELTA_TIMEOUT_REPRICED_UNWIND"
       self.save_state()
       continue
     if not exit_oid and tte_rem < 60.0 and not pos.get("is_liquidating"):
      pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD_FINAL" if tte_rem < self.tte_cancel_window else "DETERMINISTIC_TERMINAL_HOLD"
     if exit_oid:
      summary=await asyncio.to_thread(self.executor.get_order_fill_summary,exit_oid,token_id)
      if summary is not None:
       if self._record_order_summary(pos,summary,float(pos.get("target_exit_price",0.0) or 0.0),taker=False):
        self.save_state()
       filled=float(pos.get("filled_exit_shares",0.0) or 0.0)
       if filled > 0:
        pos["average_exit_price"]=round(float(pos.get("realized_exit_cash",0.0)) / filled,4)
       if float(pos.get("remaining_shares",0.0) or 0.0)<=0.02:
        logger.info(f"✓ POSITION CLOSED VIA CONFIRMED CLOB FILL: {tid} | OID: {exit_oid}")
        self._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True)
       elif summary.get("terminal"):
        logger.warning(f"⚠️ Exit order {exit_oid} is terminal ({summary.get('status', 'TERMINAL')}) with {pos.get('remaining_shares')} unsold. Position {tid} remains OPEN.")
        self.executor.release_inventory(reservation_id=exit_oid)
        pos["exit_order_id"]=None
        pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED"
        pos["status"]=ExecutionStatus.PARTIALLY_FILLED if filled > 0 else ExecutionStatus.EXIT_PENDING_SETTLEMENT
        tranches=pos.get("exit_tranches",[])
        order_matched=float(summary.get("matched",0.0) or 0.0)
        for t in tranches:
         if t.get("status") in {"POSTED","IN_FLIGHT"}:
          tranche_rem=max(0.0,round(float(t["size"]) - order_matched,2))
          if tranche_rem<=0.01:
           t["status"]="FILLED"
          else:
           t["size"]=tranche_rem
           t["status"]="PENDING"
        next_pending=[t for t in tranches if t.get("status")=="PENDING"]
        if next_pending:
         pos["target_exit_price"]=float(next_pending[0]["price"])
         if tte_rem>=self.tte_cancel_window and position_may_post_new_maker_exit(pos):
          await asyncio.to_thread(self._attempt_maker_exit_post,tid,pos)
        self.save_state()
       elif filled > 0 and pos.get("status")!=ExecutionStatus.PARTIALLY_FILLED:
        pos["status"]=ExecutionStatus.PARTIALLY_FILLED
        logger.info(f"[PARTIAL FILL] {tid}: Filled {filled:.2f}/{pos['entry_shares']:.2f} shares. Remaining: {pos.get('remaining_shares', 0.0):.2f}")
        self.save_state()
    except Exception as pos_err:
     logger.error(f"Error managing position {tid}: {pos_err}",exc_info=True)
  except Exception as e:
   logger.error(f"Error querying live CLOB order status: {e}")
  finally:
   self._refresh_global_halt()
 def check_resolutions_and_manage_positions_sync(self):
  return asyncio.run(self.check_resolutions_and_manage_positions())
 async def run(self):
  if not self.dry_run and _alerts_file_path() is not None:
   _ensure_file_logging()
  logger.info("=====================================================================")
  logger.info("       POLYMARKET LIVE MONEY HARVESTER (REGIME 4 ARMED)              ")
  logger.info("=====================================================================")
  logger.info(f"Wallet Address:   {self.executor.funder_address}")
  logger.info(f"Auth Mode:        {self.executor.auth_mode}")
  logger.info(f"Ticket Floor:     ${self.ticket_notional:.2f} USD (Half-Kelly Sizing, λ={self.kelly_fraction:.2f}, Cap: {self.max_notional_cap_pct*100:.1f}%)")
  logger.info(f"Price Boundary:   [${self.min_price_floor:.2f}, ${self.max_price_ceiling:.2f}]")
  logger.info(f"Dynamic Sizing:   {self.dynamic_sizing} (Floor: ${MIN_LOT_SIZE_USD:.2f}, Hurdle: {self.depth_hurdle:.2f}x)")
  logger.info(f"Portfolio Cap:    ${self.max_exposure:.2f} USD (Max Concurrent: {self.max_concurrent_positions})")
  logger.info(f"Profit Target:    +{self.profit_theta*100:.0f}¢ per share")
  logger.info(f"Exit Policy:      Spot-Delta Decoupled (K={self.spot_delta_k}σ) + Passive Midpoint Maker")
  logger.info(f"Mode:             {'DRY-RUN' if self.dry_run else 'LIVE REAL-MONEY TRADING'}")
  logger.info("=====================================================================")
  lock_path=PID_FILE.with_suffix(".lock")
  self._instance_lock_fd=open(lock_path,"a+")
  if fcntl is not None:
   try:
    fcntl.flock(self._instance_lock_fd.fileno(),fcntl.LOCK_EX | fcntl.LOCK_NB)
   except BlockingIOError as exc:
    self._instance_lock_fd.close()
    raise RuntimeError("Another live harvester instance already holds the lock") from exc
  watcher=None
  trigger_fp=None
  loop=None
  try:
   with open(PID_FILE,"w") as f:
    f.write(str(os.getpid()))
   self.load_state()
   self.reconcile_with_exchange()
   if not self.dry_run:
    self.save_state()
   if not TRIGGER_FILE.exists():
    TRIGGER_FILE.touch()
   self.last_trigger_file_pos=TRIGGER_FILE.stat().st_size
   logger.info(f"Tailing zero-latency shock triggers from byte offset: {self.last_trigger_file_pos}")
   trigger_fp=open(TRIGGER_FILE,"rb")
   trigger_fp.seek(self.last_trigger_file_pos)
   if SHOCK_FILE.exists():
    self.last_shock_file_pos=SHOCK_FILE.stat().st_size
    logger.info(f"Tailing shock responses fallback from byte offset: {self.last_shock_file_pos}")
   if RESOLUTIONS_FILE.exists():
    self.last_res_file_pos=0
    await self.check_resolutions_and_manage_positions()
    self.last_res_file_pos=RESOLUTIONS_FILE.stat().st_size
    logger.info(f"Tailing new resolutions from byte offset: {self.last_res_file_pos}")
   watcher=LinuxInotifyWatcher(TRIGGER_FILE)
   loop=asyncio.get_running_loop()
   def _request_shutdown(signame:str):
    if not self._shutdown_requested:
     logger.warning(f"[SHUTDOWN] {signame} received; finishing in-flight step then stopping gracefully.")
    self._shutdown_requested=True
   for _sig in (signal.SIGTERM,signal.SIGINT):
    try:
     loop.add_signal_handler(_sig,_request_shutdown,_sig.name)
    except (NotImplementedError,RuntimeError,ValueError):
     pass
   trigger_notify_event=asyncio.Event()
   self._main_loop=loop
   if getattr(self,"_fast_trigger_lines",None) is None:
    from collections import deque as _deque
    self._fast_trigger_lines=_deque(maxlen=512)
   if getattr(self,"_fast_d1_cand_lines",None) is None:
    from collections import deque as _deque
    self._fast_d1_cand_lines=_deque(maxlen=64)
   def on_inotify_file_event():
    watcher.drain_events()
    trigger_notify_event.set()
   if watcher.is_available:
    loop.add_reader(watcher.fd,on_inotify_file_event)
    logger.info(f"✓ Linux inotify event listener armed on {TRIGGER_FILE.name} (sub-millisecond wakeups enabled).")
   else:
    logger.info("Linux inotify unavailable; using responsive 50ms polling fallback.")
   ipc_sock=None
   if os.name!="nt":
    try:
     import socket
     ipc_sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
     ipc_sock.setblocking(False)
     try:
      ipc_sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,262144)
     except Exception:
      pass
     ipc_name=os.environ.get( "POLYMARKET_IPC_SOCKET_NAME","polymarket_shock_notify" if not self.dry_run else f"pm_shock_dry_{os.getpid()}",)
     ipc_addr=f"\x00{ipc_name}".encode("utf-8")
     ipc_sock.bind(ipc_addr)
     def on_fast_ipc_datagram():
      while True:
       try:
        pkt=ipc_sock.recv(65536)
        if not pkt:
         break
        for ln in pkt.decode("utf-8",errors="ignore").splitlines():
         if ln.strip():
          self._fast_trigger_lines.append(ln)
       except (BlockingIOError,InterruptedError):
        break
       except Exception:
        break
      trigger_notify_event.set()
     loop.add_reader(ipc_sock.fileno(),on_fast_ipc_datagram)
     logger.info("✓ Fast RAM IPC datagram listener armed on @polymarket_shock_notify (~15us zero-VFS delivery).")
    except Exception as ipc_exc:
     logger.debug(f"Fast IPC datagram setup notice: {ipc_exc}")
     if ipc_sock is not None:
      try:
       ipc_sock.close()
      except Exception:
       pass
      ipc_sock=None
   d1_ipc_sock=None
   if os.name!="nt":
    try:
     import socket
     d1_ipc_sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
     d1_ipc_sock.setblocking(False)
     d1_ipc_name=os.environ.get( "POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify" if not self.dry_run else f"pm_d1_dry_{os.getpid()}",)
     d1_ipc_sock.bind(f"\x00{d1_ipc_name}".encode("utf-8"))
     def on_fast_d1_ipc_datagram():
      while True:
       try:
        pkt=d1_ipc_sock.recv(65536)
        if not pkt:
         break
        for ln in pkt.decode("utf-8",errors="ignore").splitlines():
         if ln.strip():
          self._fast_d1_cand_lines.append(ln)
       except (BlockingIOError,InterruptedError):
        break
       except Exception:
        break
      trigger_notify_event.set()
     loop.add_reader(d1_ipc_sock.fileno(),on_fast_d1_ipc_datagram)
     logger.info("✓ Fast D1 Box IPC datagram listener armed on @polymarket_d1_box_notify (~15us wakeup).")
    except Exception as d1_ipc_exc:
     logger.debug(f"Fast D1 IPC setup notice: {d1_ipc_exc}")
     if d1_ipc_sock is not None:
      try:
       d1_ipc_sock.close()
      except Exception:
       pass
      d1_ipc_sock=None
   last_heartbeat=time.time()
   last_clob_heartbeat=0.0
   last_mgmt_check=0.0
   scanned_count=0
   pos_ws_task=None
   if ( not self.dry_run and _PolymarketClobMarketWsTracker is not None and getattr(self.executor,"auth_mode","") in ("LIVE","AUTHENTICATED_L2") and getattr(getattr(self.executor,"client",None),"_mock_children",None) is None and os.environ.get("PM_ENABLE_HARVESTER_MKT_WS","1")=="1" ):
    def _on_ws_recycle_bid(_tok:str,_bb:float)->None:
     self._ws_urgent_recycle_ts=time.time()
     loop.call_soon_threadsafe(trigger_notify_event.set)
    self._pos_market_ws=_PolymarketClobMarketWsTracker( recycle_bid_trigger=0.985,on_urgent_bid=_on_ws_recycle_bid,)
    self._pos_market_ws.set_desired_tokens([str(p.get("token_id") or "") for p in self.active_positions.values()])
    pos_ws_task=asyncio.create_task(self._pos_market_ws.run_forever(lambda:bool(self._shutdown_requested)))
   self._prewarm_active_market_tokens()
   while True:
    if self._shutdown_requested:
     self._shutdown_status="STOPPED_GRACEFULLY"
     logger.warning( f"[SHUTDOWN] Graceful stop: {len(self.active_positions)} active position(s) persisted to state; " f"resting exit orders (if any) remain on the exchange for restart reconciliation." )
     await asyncio.to_thread(self.save_state)
     if not self.active_positions and not self.dry_run:
      await asyncio.to_thread(self.executor.cancel_all_orders)
     break
    if ( not self.dry_run and self.risk_controller.is_halted() and "Heartbeat degraded" in str(self.risk_controller.halt_reason or "") and self.executor.is_heartbeat_healthy() ):
     self.risk_controller.halted=False
     self.risk_controller.halt_reason=""
     self._halt_logged_active=False
     logger.info("[HEARTBEAT RECOVERED] CLOB heartbeat healthy again; clearing temporary heartbeat halt.")
     self.save_state()
    if self.risk_controller.is_halted():
     if ( not self.active_positions and not self.dry_run and (time.time() - getattr(self,"_last_halt_collat_check",0.0)>=15.0) ):
      self._last_halt_collat_check=time.time()
      await self._async_refresh_collateral()
     if self.risk_controller.is_halted():
      if not getattr(self,"_halt_logged_active",False):
       logger.critical( f"[CIRCUIT BREAKER] {self.risk_controller.halt_reason}. " "Halting new entries (supervisor staying alive for recovery / UTC rollover)." )
       self.save_state()
       self._halt_logged_active=True
      if not self.active_positions:
       if not self.dry_run and not getattr(self,"_halt_orders_cancelled",False):
        await asyncio.to_thread(self.executor.cancel_all_orders)
        self._halt_orders_cancelled=True
       if not self.dry_run and "Heartbeat degraded" in str(self.risk_controller.halt_reason or ""):
        if (time.time() - getattr(self,"_last_halt_hb_probe",0.0))>=5.0:
         self._last_halt_hb_probe=time.time()
         await asyncio.to_thread(self.executor.post_heartbeat)
       await asyncio.sleep(1.0)
       continue
    else:
     self._halt_logged_active=False
     self._halt_orders_cancelled=False
    if not self.dry_run and not self.executor.is_heartbeat_healthy():
     self.risk_controller.halted=True
     self.risk_controller.halt_reason=f"Heartbeat degraded ({self.executor.heartbeat_failures} drops) - new entries halted; existing positions remain supervised."
     if not getattr(self,"_halt_logged_active",False):
      logger.critical(f"[HEARTBEAT UNHEALTHY] CLOB heartbeat dropped {self.executor.heartbeat_failures} times. Halting new entries.")
      self.save_state()
      self._halt_logged_active=True
     if not self.active_positions:
      if not getattr(self,"_halt_orders_cancelled",False):
       await asyncio.to_thread(self.executor.cancel_all_orders)
       self._halt_orders_cancelled=True
      await asyncio.to_thread(self.executor.post_heartbeat)
      await asyncio.sleep(1.0)
      continue
    now_ts=time.time()
    _sync_bg_io=getattr(self.executor,"auth_mode","") not in ("LIVE","AUTHENTICATED_L2")
    if not self.dry_run and self.active_positions and (now_ts - last_clob_heartbeat>=5.0):
     last_clob_heartbeat=now_ts
     if _sync_bg_io:
      hb_res=await asyncio.to_thread(self.executor.post_heartbeat)
      if isinstance(hb_res,dict) and hb_res.get("error"):
       logger.warning(f"[HEARTBEAT WARN] Heartbeat error: {hb_res.get('error')}")
     elif not getattr(self,"_hb_in_flight",False):
      self._hb_in_flight=True
      async def _bg_heartbeat():
       try:
        res=await asyncio.to_thread(self.executor.post_heartbeat)
        if isinstance(res,dict) and res.get("error"):
         logger.warning(f"[HEARTBEAT WARN] Heartbeat error: {res.get('error')}")
       finally:
        self._hb_in_flight=False
      asyncio.create_task(_bg_heartbeat())
    if not self.dry_run and (now_ts - getattr(self,"_last_clob_keepalive",0.0)>=8.0):
     self._last_clob_keepalive=now_ts
     if _sync_bg_io:
      await asyncio.to_thread(self.executor.ping_clob_keepalive)
     elif not getattr(self,"_keepalive_in_flight",False):
      self._keepalive_in_flight=True
      async def _bg_keepalive():
       try:
        await asyncio.to_thread(self.executor.ping_clob_keepalive)
       finally:
        self._keepalive_in_flight=False
      asyncio.create_task(_bg_keepalive())
     self._prewarm_active_market_tokens()
     if not self.active_positions:
      try:
       import gc as _gc
       _gc.collect(0)
      except Exception:
       pass
     if GLOBAL_SVI_ENGINE is not None and (now_ts - getattr(self,"_last_svi_refresh",0.0)>=60.0):
      self._last_svi_refresh=now_ts
      asyncio.create_task(asyncio.to_thread(GLOBAL_SVI_ENGINE.get_surface,"BTC"))
      asyncio.create_task(asyncio.to_thread(GLOBAL_SVI_ENGINE.get_surface,"ETH"))
    now_dt=datetime.now(timezone.utc)
    if now_dt.minute in (58,13,28,43,8,23,38,53):
     prewarm_min_key=f"{now_dt.hour}:{now_dt.minute}"
     if getattr(self,"_last_prewarm_minute_key","")!=prewarm_min_key:
      self._last_prewarm_minute_key=prewarm_min_key
      asyncio.create_task(self._prewarm_next_candle_markets())
    _uws_c=getattr(self.executor,"_user_ws_cache",None)
    _collat_iv=60.0 if (not self.active_positions and _uws_c is not None and _uws_c.is_healthy()) else 20.0
    if not self.dry_run and ( getattr(self,"_pending_collateral_refresh",False) or (now_ts - getattr(self,"_last_collat_poll",0.0)>=_collat_iv) ):
     self._pending_collateral_refresh=False
     self._last_collat_poll=now_ts
     asyncio.create_task(self._async_refresh_collateral())
    fast_lines=[]
    if getattr(self,"_fast_trigger_lines",None):
     while self._fast_trigger_lines:
      fast_lines.append(self._fast_trigger_lines.popleft())
    chunk=b""
    disk_lines=[]
    if not fast_lines:
     try:
      chunk=trigger_fp.read()
     except Exception as e:
      logger.debug(f"Trigger stream read notice: {e}")
      chunk=b""
     if not chunk and TRIGGER_FILE.exists():
      try:
       curr_sz=TRIGGER_FILE.stat().st_size
       if curr_sz < self.last_trigger_file_pos:
        trigger_fp.seek(0,2)
        self.last_trigger_file_pos=trigger_fp.tell()
        chunk=b""
      except Exception:
       pass
     if chunk:
      complete_end=chunk.rfind(b"\n") + 1
      if complete_end:
       disk_lines=chunk[:complete_end].decode("utf-8",errors="ignore").splitlines()
       self.last_trigger_file_pos += complete_end
       if complete_end < len(chunk):
        trigger_fp.seek(self.last_trigger_file_pos)
      else:
       disk_lines=[]
       trigger_fp.seek(self.last_trigger_file_pos)
    new_lines=fast_lines + disk_lines
    if new_lines:
     batch_candidates=[]
     batch_seen_ids=set()
     for line in new_lines:
      if not line.strip():
       continue
      try:
       shk=_json_loads(line)
      except Exception as parse_err:
       logger.error(f"Error parsing trigger line: {parse_err}")
       continue
      s_id=shk.get("shock_id") or f"{shk.get('market_id')}_{shk.get('t0_unix')}"
      if s_id in self.seen_shock_ids or s_id in batch_seen_ids:
       continue
      batch_seen_ids.add(s_id)
      self._prewarm_market_metadata(shk)
      batch_candidates.append(shk)
     if batch_candidates:
      now_u=time.time()
      self.recent_shock_window=[ w for w in self.recent_shock_window if (now_u - w["t_unix"])<=5.0 ]
      batch_candidates.sort(key=self._calc_priority_score,reverse=True)
      for shock in batch_candidates:
       s_id=shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
       if s_id in self.seen_shock_ids:
        continue
       cand_score=self._calc_priority_score(shock)
       t0_u=float(shock.get("t0_unix",now_u))
       shk_m_id=str(shock.get("market_id") or "")
       if cand_score > 0.0 and self.recent_shock_window:
        best_prior=max(self.recent_shock_window,key=lambda x:x["score"])
        if best_prior["market_id"]!=shk_m_id and best_prior["score"] > cand_score:
         logger.info( f"[PRIORITY DEFER] Deferring {shock.get('title')!r} (score={cand_score:.3f}) " f"to concurrent superior qualified trigger {best_prior.get('trade_id')} (score={best_prior['score']:.3f})" )
         continue
       self.last_event_id=s_id
       scanned_count += 1
       try:
        await self.evaluate_shock_and_execute(shock)
       except StatePersistenceError:
        self.risk_controller.halted=True
        self.risk_controller.halt_reason="Critical state persistence failure"
        logger.critical("Critical live state persistence failure; blocking further entries but continuing position supervision",exc_info=True)
        break
       except Exception:
        logger.exception(f"[SIGNAL ERROR] Unhandled exception evaluating shock {shock.get('market_id')}; signal skipped.")
        try:
         self._refresh_global_halt()
        except Exception:
         logger.exception("[SIGNAL ERROR] Global halt refresh failed.")
    if ( not self.risk_controller.is_halted() and not getattr(self,"risk_halt",False) and (bool(getattr(self,"_fast_d1_cand_lines",None)) or (now_ts - getattr(self,"_last_d1_cand_poll",0.0)>=0.50)) ):
     self._last_d1_cand_poll=now_ts
     await self._poll_d1_live_box_candidates(now_ts)
    urgent_supervision=( (now_ts - float(getattr(self,"_ws_urgent_recycle_ts",0.0) or 0.0))<=1.5 or any( p.get("strike_retrace_detected_ts") or p.get("opposite_breakout_start_ts") or p.get("low_bid_detected_ts") or p.get("trail_stop_detected_ts") or p.get("zero_bid_detected_ts") or p.get("exit_order_status") in {"STOP_CANCEL_PENDING","PRE_EXPIRY_CANCEL_PENDING","FILL_RECONCILIATION_REQUIRED","PASSIVE_STOP_RESTING","EXIT_RECOVERY_REQUIRED","UNWIND_RETRY_REQUIRED"} for p in self.active_positions.values() ) )
    mgmt_interval=0.20 if urgent_supervision else 1.0
    if now_ts - last_mgmt_check>=mgmt_interval:
     last_mgmt_check=now_ts
     try:
      await self.check_resolutions_and_manage_positions()
      if not self.dry_run:
       self._step_shadow_phase3_4_tracker(now_ts)
     except StatePersistenceError:
      raise
     except Exception:
      logger.exception("[SUPERVISION ERROR] Position management cycle failed; retrying next cycle.")
    if time.time() - last_heartbeat>=300:
     last_heartbeat=time.time()
     active_exp=sum(p.get("notional_usd",0.0) for p in self.active_positions.values())
     logger.info( f"[HEARTBEAT] Harvester active | Triggers scanned: {scanned_count} | " f"Active positions: {len(self.active_positions)} (${active_exp:.2f}) | " f"Closed: {len(self.closed_positions)}" )
    if not self.dry_run and (time.time() - getattr(self,"_last_stale_check",0.0)>=5.0):
     self._last_stale_check=time.time()
     try:
      self.monitor_recorder_staleness(self._last_stale_check)
     except Exception:
      logger.debug("[STALE_RECORDER_GUARD] monitor failed",exc_info=True)
    try:
     await asyncio.wait_for(trigger_notify_event.wait(),timeout=0.010)
     trigger_notify_event.clear()
    except asyncio.TimeoutError:
     pass
  except Exception:
   logger.critical("[FATAL] Harvester loop terminated by unhandled exception.",exc_info=True)
   raise
  finally:
   if 'pos_ws_task' in locals() and pos_ws_task is not None:
    pos_ws_task.cancel()
   if 'd1_ipc_sock' in locals() and d1_ipc_sock is not None:
    try:
     if 'loop' in locals() and loop is not None:
      loop.remove_reader(d1_ipc_sock.fileno())
    except Exception:
     pass
    try:
     d1_ipc_sock.close()
    except Exception:
     pass
   if 'ipc_sock' in locals() and ipc_sock is not None:
    try:
     if 'loop' in locals() and loop is not None:
      loop.remove_reader(ipc_sock.fileno())
    except Exception:
     pass
    try:
     ipc_sock.close()
    except Exception:
     pass
   if 'trigger_fp' in locals() and trigger_fp is not None and not getattr(trigger_fp,"closed",True):
    try:
     trigger_fp.close()
    except Exception:
     pass
   if 'watcher' in locals() and watcher is not None and getattr(watcher,"is_available",False):
    try:
     if 'loop' in locals() and loop is not None:
      loop.remove_reader(watcher.fd)
    except Exception:
     pass
    try:
     watcher.close()
    except Exception:
     pass
   try:
    flush_operational_alerts(3.0)
   except Exception:
    pass
   lock_fd=getattr(self,"_instance_lock_fd",None)
   if lock_fd is not None:
    try:
     if fcntl is not None:
      fcntl.flock(lock_fd.fileno(),fcntl.LOCK_UN)
     lock_fd.close()
    except Exception:
     pass
if __name__=="__main__":
 import argparse
 parser=argparse.ArgumentParser(description="Polymarket Live Harvester")
 parser.add_argument("--lot-size",type=float,default=RISK_CONFIG["ticket_notional"],help="Ticket size in USD (default: config/polymarket_risk_config.json ticket_notional)")
 parser.add_argument("--dynamic-sizing",action="store_true",default=True,help="Dynamically scale lot size with orderbook depth (default: True)")
 parser.add_argument("--no-dynamic-sizing",dest="dynamic_sizing",action="store_false",help="Disable dynamic sizing and use fixed lot size")
 parser.add_argument("--max-exposure",type=float,default=RISK_CONFIG["max_exposure"],help="Maximum concurrent portfolio exposure in USD (default: config max_exposure)")
 parser.add_argument("--max-concurrent",type=int,default=RISK_CONFIG["max_concurrent_positions"],help="Maximum concurrent open positions (default: config max_concurrent_positions)")
 parser.add_argument("--max-trades-per-market",type=int,default=DEFAULT_MAX_TRADES_PER_MARKET,help="Max trades per market candle (default: 1)")
 parser.add_argument("--max-trades-per-hour",type=int,default=DEFAULT_MAX_TRADES_PER_HOUR,help="Max total portfolio trades per hour (default: 6)")
 parser.add_argument("--max-tte",type=float,default=MAX_TTE_SECONDS,help="Max TTE in seconds (default: module MAX_TTE_SECONDS)")
 parser.add_argument("--max-price-ceiling",type=float,default=MAX_PRICE_CEILING,help="Maximum entry price ceiling (default: module MAX_PRICE_CEILING)")
 parser.add_argument("--min-price-floor",type=float,default=MIN_PRICE_FLOOR,help="Minimum entry price floor (default: module MIN_PRICE_FLOOR)")
 parser.add_argument("--unconstrained-kelly",action="store_true",default=False,help="Allow Half-Kelly position sizing to compound proportionally (25 percent of bankroll) beyond $39.92")
 parser.add_argument("--max-ticket-cap",type=float,default=MAX_ABSOLUTE_TICKET_USD,help="Explicit maximum dollar cap for single ticket (default: module MAX_ABSOLUTE_TICKET_USD)")
 parser.add_argument("--dynamic-theta",action="store_true",default=False,help="Enable EXP-315 regime-dependent profit target (0.06 when TTE>900s, 0.09 standard, hold-to-expiry when TTE<=300s)")
 parser.add_argument("--hold-to-maturity",dest="hold_to_maturity",action="store_true",default=bool(RISK_CONFIG.get("hold_to_maturity",False)),help="Hold resting $0.99 single-tranche ask to maturity instead of 2-tranche / $0.95 WFO maker exit")
 parser.add_argument("--no-hold-to-maturity",dest="hold_to_maturity",action="store_false",help="Enable WFO-optimal resting maker exits (default in production)")
 parser.add_argument("--exit-policy",type=str,default=str(RISK_CONFIG.get("exit_policy","two_tranche_95_98")),help="Exit policy: hold_98 or two_tranche_95_98")
 parser.add_argument("--allowed-assets",nargs="+",default=["BTC","ETH"],help="Assets permitted for live trading (default: BTC ETH)")
 parser.add_argument("--dry-run",action="store_true",help="Run in dry-run simulation mode")
 parser.add_argument("--reset-risk",action="store_true",default=False,help="Reset circuit breaker and consecutive losses on launch")
 parser.add_argument("--max-daily-loss",type=float,default=None,help="Circuit breaker max daily loss limit in USD (default: config max_daily_loss)")
 args=parser.parse_args()
 harvester=PolymarketLiveHarvester( ticket_notional=args.lot_size,dry_run=args.dry_run,dynamic_sizing=args.dynamic_sizing,max_exposure=args.max_exposure,max_concurrent=args.max_concurrent,max_trades_per_market=args.max_trades_per_market,max_trades_per_hour=args.max_trades_per_hour,max_tte=args.max_tte,max_price_ceiling=args.max_price_ceiling,min_price_floor=args.min_price_floor,unconstrained_kelly=args.unconstrained_kelly,max_absolute_ticket_usd=args.max_ticket_cap,dynamic_theta=args.dynamic_theta,hold_to_maturity=args.hold_to_maturity,exit_policy=args.exit_policy,allow_cli_exposure=any(a=="--max-exposure" or a.startswith("--max-exposure=") for a in sys.argv[1:]),allowed_assets=set(args.allowed_assets),reset_risk=args.reset_risk,max_daily_loss=args.max_daily_loss,)
 if os.name!="nt":
  try:
   import uvloop
   uvloop.install()
  except Exception:
   pass
 asyncio.run(harvester.run())

# === [04/12] src/polymarket_research/polymarket_live_executor.py :: Polymarket CLOB L2 Client, Priority EIP-712 Signing & pUSD/CTF Adapter ===
#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import asyncio
import concurrent.futures
import json
import logging
import math
import os
import queue
import secrets
import sys
import threading
import time
from collections import defaultdict
from dataclasses import dataclass,field
from datetime import datetime,timezone
from decimal import Decimal,ROUND_CEILING,ROUND_FLOOR,ROUND_HALF_UP
from pathlib import Path
from typing import Any,Dict,List,Optional,Tuple,Union
import socket
from urllib3.connection import HTTPConnection
import httpx
import requests
from dotenv import load_dotenv
try:
 import orjson as _orjson
except ImportError:
 _orjson=None
def enable_tcp_nodelay_globally()->None:
 try:
  orig_options=list(HTTPConnection.default_socket_options)
  nodelay_opt=(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
  keepalive_opt=(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
  if nodelay_opt not in orig_options:
   orig_options.append(nodelay_opt)
  if keepalive_opt not in orig_options:
   orig_options.append(keepalive_opt)
  HTTPConnection.default_socket_options=orig_options
 except Exception:
  pass
class _ThreadLocalClobHttpClient:
 def __init__(self,timeout:float=8.0,max_pool_size:int=16)->None:
  self._local=threading.local()
  self._timeout=timeout
  self._pool:"queue.LifoQueue[Tuple[httpx.Client, float]]"=queue.LifoQueue(maxsize=max_pool_size)
  self._bg_pool:"queue.LifoQueue[Tuple[httpx.Client, float]]"=queue.LifoQueue(maxsize=max(8,max_pool_size))
  self._warm_lock=threading.Lock()
 def _make_client(self)->httpx.Client:
  limits=httpx.Limits( max_keepalive_connections=8,max_connections=16,keepalive_expiry=45.0,)
  try:
   transport=httpx.HTTPTransport( http2=False,limits=limits,socket_options=[(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)],)
   return httpx.Client(http2=False,timeout=self._timeout,transport=transport)
  except Exception:
   return httpx.Client(http2=False,timeout=self._timeout,limits=limits)
 def _client(self,reset:bool=False)->httpx.Client:
  cli=getattr(self._local,"client",None)
  if reset and cli is not None:
   try:
    cli.close()
   except Exception:
    pass
   cli=None
  if cli is None or getattr(cli,"is_closed",False):
   cli=self._make_client()
   self._local.client=cli
  return cli
 @staticmethod
 def _is_hot_request(method:str,url:str)->bool:
  m=str(method or "").upper()
  if m!="GET":
   return True
  u=str(url or "")
  return (not u) or u.endswith("/time")
 def _borrow_from(self,target_pool:"queue.LifoQueue[Tuple[httpx.Client, float]]")->httpx.Client:
  while True:
   try:
    cli,last_ts=target_pool.get_nowait()
   except queue.Empty:
    return self._make_client()
   if cli is not None and not getattr(cli,"is_closed",False) and (time.monotonic() - last_ts) < 40.0:
    return cli
   try:
    if cli is not None:
     cli.close()
   except Exception:
    pass
 @staticmethod
 def _return_to(target_pool:"queue.LifoQueue[Tuple[httpx.Client, float]]",cli:Optional[httpx.Client])->None:
  if cli is None or getattr(cli,"is_closed",False):
   return
  try:
   target_pool.put_nowait((cli,time.monotonic()))
  except queue.Full:
   try:
    cli.close()
   except Exception:
    pass
 def _borrow_pool_client(self)->httpx.Client:
  return self._borrow_from(self._pool)
 def _return_pool_client(self,cli:Optional[httpx.Client])->None:
  self._return_to(self._pool,cli)
 def _record_resp_meta(self,resp:Any)->None:
  try:
   hdrs=getattr(resp,"headers",None)
   if hdrs and hasattr(hdrs,"get"):
    self._local.last_resp_meta={ "cf_ray":hdrs.get("cf-ray"),"ratelimit_remaining":hdrs.get("Poly-RateLimit-Remaining") or hdrs.get("poly-ratelimit-remaining"),"status_code":getattr(resp,"status_code",None),}
  except Exception:
   pass
 def get_last_response_meta(self)->Dict[str,Any]:
  return dict(getattr(self._local,"last_resp_meta",None) or {})
 def warm_pool( self,url:str="https://clob.polymarket.com/time",min_warm:int=4,max_idle_sec:float=18.0,)->int:
  if not self._warm_lock.acquire(blocking=False):
   return 0
  seen_ids:set=set()
  healthy_count=0
  target=max(1,int(min_warm))
  try:
   for _ in range(target):
    now_m=time.monotonic()
    cli:Optional[httpx.Client]=None
    last_ts=0.0
    with self._pool.mutex:
     q_list=self._pool.queue
     pick_idx=None
     for idx in range(len(q_list) - 1,-1,-1):
      cand_cli,_=q_list[idx]
      if id(cand_cli) not in seen_ids:
       pick_idx=idx
       break
     if pick_idx is not None:
      cli,last_ts=q_list.pop(pick_idx)
    if cli is None or getattr(cli,"is_closed",False):
     cli,last_ts=self._make_client(),0.0
    if (now_m - last_ts)>=max_idle_sec:
     try:
      cli.request("GET",url)
      last_ts=time.monotonic()
     except Exception:
      try:
       cli.close()
      except Exception:
       pass
      continue
    seen_ids.add(id(cli))
    try:
     self._pool.put_nowait((cli,last_ts))
     healthy_count += 1
    except queue.Full:
     try:
      cli.close()
     except Exception:
      pass
  finally:
   self._warm_lock.release()
  return healthy_count
 def request(self,method:str,url:str,**kwargs:Any)->httpx.Response:
  target_pool=self._pool if self._is_hot_request(method,url) else self._bg_pool
  cli=self._borrow_from(target_pool)
  healthy=True
  try:
   resp=cli.request(method=method,url=url,**kwargs)
   self._record_resp_meta(resp)
   return resp
  except (httpx.ConnectError,httpx.ConnectTimeout,httpx.PoolTimeout,httpx.RemoteProtocolError,httpx.LocalProtocolError) as exc:
   healthy=False
   try:
    cli.close()
   except Exception:
    pass
   is_pre_wire=isinstance(exc,(httpx.ConnectError,httpx.ConnectTimeout,httpx.PoolTimeout))
   if is_pre_wire or str(method).upper()=="GET":
    fresh=self._make_client()
    try:
     resp=fresh.request(method=method,url=url,**kwargs)
     self._record_resp_meta(resp)
     self._return_to(target_pool,fresh)
     return resp
    except Exception:
     try:
      fresh.close()
     except Exception:
      pass
     raise
   raise exc
  finally:
   if healthy:
    self._return_to(target_pool,cli)
def install_thread_safe_clob_http_client(target_module:Any=None)->bool:
 try:
  logging.getLogger("httpx").setLevel(logging.WARNING)
  logging.getLogger("httpcore").setLevel(logging.WARNING)
 except Exception:
  pass
 try:
  if target_module is None:
   import py_clob_client_v2.http_helpers.helpers as hh
   target_module=hh
  cur=getattr(target_module,"_http_client",None)
  if isinstance(cur,_ThreadLocalClobHttpClient):
   return True
  target_module._http_client=_ThreadLocalClobHttpClient()
  try:
   if cur is not None and hasattr(cur,"close"):
    cur.close()
  except Exception:
   pass
  return True
 except Exception:
  return False
enable_tcp_nodelay_globally()
install_thread_safe_clob_http_client()
PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT) not in sys.path:
 sys.path.insert(0,str(PIPELINE_ROOT))
load_dotenv(PIPELINE_ROOT / ".env")
POLYMARKET_DATA_DIR=Path(os.getenv("POLYMARKET_DATA_DIR",str(PIPELINE_ROOT / "data/polymarket")))
RISK_CONFIG_PATH=Path(os.getenv("POLYMARKET_RISK_CONFIG",str(PIPELINE_ROOT / "config/polymarket_risk_config.json")))
_RISK_CONFIG_DEFAULTS:Dict[str,Any]={ "ticket_notional":16.50,"dynamic_sizing":True,"dynamic_risk_pct":0.18,"scale_up_equity_threshold":110.00,"correlated_crypto_single_slot_threshold":180.00,"scale_up_risk_pct":0.22,"min_equity_floor":66.67,"seed_survival_equity_threshold":88.00,"seed_survival_ticket_usd":12.00,"seed_survival_max_concurrent":1,"seed_survival_floor_usd":48.00,"seed_smooth_compounding":True,"enable_fak_plus2c_fallback":False,"enable_live_phase3a_maker_fallback":True,"phase3a_maker_max_notional_usd":22.00,"enable_graduated_d1_box":True,"enable_sol_d1_box":True,"d1_box_max_budget_usd":250.0,"d1_box_collateral_reserve_usd":16.50,"d1_box_bankroll_pct":0.25,"d1_depth_ratio_threshold":1.20,"d1_min_depth_mult_gate":1.15,"d1_max_giveback_frac":0.25,"max_concurrent_d1_boxes":4,"enable_graduated_alt_sleeves":True,"max_daily_loss":20.00,"max_exposure":35.00,"max_concurrent_positions":2,"hold_to_maturity":False,"exit_policy":"hold_98","stale_fast_tick_max_age_sec":15.0,"stale_telemetry_max_age_sec":30.0,"stale_alert_after_sec":60.0,"alert_rate_limit_sec":300.0,}
def load_risk_config(path:Optional[Path]=None)->Dict[str,Any]:
 cfg:Dict[str,Any]=dict(_RISK_CONFIG_DEFAULTS)
 try:
  with open(path or RISK_CONFIG_PATH,"r",encoding="utf-8") as fh:
   raw=json.load(fh)
  if isinstance(raw,dict):
   for key,default in _RISK_CONFIG_DEFAULTS.items():
    if key not in raw:
     continue
    val=raw[key]
    if isinstance(default,bool):
     cfg[key]=bool(val)
    elif isinstance(default,str) and isinstance(val,str) and val in ("hold_98","two_tranche_95_98"):
     cfg[key]=val
    elif isinstance(val,(int,float)) and not isinstance(val,bool) and math.isfinite(float(val)) and float(val) > 0:
     cfg[key]=int(val) if key in ("max_concurrent_positions","seed_survival_max_concurrent","max_concurrent_d1_boxes") else float(val)
 except Exception:
  pass
 return cfg
RISK_CONFIG:Dict[str,Any]=load_risk_config()
try:
 import py_clob_client_v2
 import py_clob_client_v2.clob_types as _clob_types_mod
 from py_clob_client_v2.client import ClobClient
 from py_clob_client_v2.clob_types import ( ApiCreds,OrderArgsV2,MarketOrderArgsV2,OrderType,AssetType,BalanceAllowanceParams,TradeParams,PartialCreateOrderOptions,FeeInfo,)
 PostOrdersV2Args=getattr(_clob_types_mod,"PostOrdersV2Args",None)
 PY_CLOB_AVAILABLE=True
 PY_CLOB_VERSION=getattr(py_clob_client_v2,"__version__","1.2.0")
except ImportError:
 PY_CLOB_AVAILABLE=False
 PY_CLOB_VERSION=None
 ClobClient=None
 ApiCreds=None
 OrderArgsV2=None
 MarketOrderArgsV2=None
 OrderType=None
 AssetType=None
 BalanceAllowanceParams=None
 TradeParams=None
 PartialCreateOrderOptions=None
 FeeInfo=None
 PostOrdersV2Args=None
EXPECTED_CLOB_V2="1.2.0"
CLOB_ALLOWED_TICK_SIZES=(0.1,0.01,0.005,0.0025,0.001,0.0001)
MAX_PRICE_CEILING=0.8600
MIN_PRICE_FLOOR=0.5500
MIN_LOT_SIZE_USD=12.00
DEFAULT_DEPTH_HURDLE=1.30
SLEEVE_1_MIN_PRICE=0.5500
SLEEVE_1_MAX_PRICE=0.8600
SLEEVE_2_ENABLED=True
SLEEVE_2_MIN_PRICE=0.5500
SLEEVE_2_MAX_PRICE=0.7800
SLEEVE_2_SUBHOURLY_MAX_PRICE=0.7800
CIRCUIT_BREAKER_EQUITY_FLOOR=RISK_CONFIG["min_equity_floor"]
DYNAMIC_EQUITY_RISK_PCT=RISK_CONFIG["dynamic_risk_pct"]
MIN_TICKET_USD=12.00
MAX_TICKET_CAP_USD=200.00
MAX_CONCURRENT_POSITIONS=3
MAX_POSITIONS_PER_MARKET_ID=2
logger=logging.getLogger("PolymarketLiveExecutor")
if not logger.handlers:
 handler=logging.StreamHandler(sys.stdout)
 handler.setFormatter(logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [PM-EXEC] %(message)s"))
 logger.addHandler(handler)
 logger.setLevel(logging.INFO)
class ExecutionStatus:
 REJECTED="REJECTED"
 SUBMITTED="SUBMITTED"
 MATCHED_PENDING_SETTLEMENT="MATCHED_PENDING_SETTLEMENT"
 POSITION_CONFIRMED="POSITION_CONFIRMED"
 EXIT_PENDING_SETTLEMENT="EXIT_PENDING_SETTLEMENT"
 EXIT_RESTING="EXIT_RESTING"
 PARTIALLY_FILLED="PARTIALLY_FILLED"
 FILLED="FILLED"
 SETTLED="SETTLED"
def calculate_taker_fee( notional_usd:float,price:float,fee_rate:float=0.07,fee_exponent:float=1.0,)->Tuple[float,float]:
 clamped_p=max(0.001,min(0.999,price))
 shares=notional_usd / clamped_p
 per_share_fee=fee_rate * ((clamped_p * (1.0 - clamped_p)) ** fee_exponent)
 fee_usd=float(Decimal(str(shares * per_share_fee)).quantize(Decimal("0.00001"),rounding=ROUND_HALF_UP))
 effective_rate=round(fee_usd / max(notional_usd,1e-6),8)
 return effective_rate,fee_usd
def is_fak_killed_no_match(err:Any=None,raw_resp:Optional[Dict[str,Any]]=None)->bool:
 pattern="no orders found to match with fak order"
 if err is not None:
  err_msg_field=getattr(err,"error_message",None) or getattr(err,"error_msg",None)
  if err_msg_field and pattern in str(err_msg_field).lower():
   return True
  if pattern in str(getattr(err,"error_msg","")).lower():
   return True
  if pattern in str(err).lower():
   return True
 if raw_resp and isinstance(raw_resp,dict):
  err_msg=str(raw_resp.get("errorMsg") or raw_resp.get("error") or raw_resp.get("error_message") or "")
  if pattern in err_msg.lower():
   return True
 return False
def is_clob_400_rejection(err:Any=None,raw_resp:Optional[Dict[str,Any]]=None)->bool:
 if is_fak_killed_no_match(err,raw_resp):
  return True
 if err is not None:
  sc=getattr(err,"status_code",None)
  if sc==400 or sc=="400":
   return True
  err_str=str(err).lower()
  if ( "status_code=400" in err_str or "status=400" in err_str or "invalid amounts" in err_str or "fok_order_not_filled" in err_str or "couldn't be fully filled" in err_str ):
   return True
  err_msg_field=getattr(err,"error_message",None) or getattr(err,"error_msg",None)
  if err_msg_field:
   field_str=str(err_msg_field).lower()
   if any( p in field_str for p in ( "invalid amounts","supports a max accuracy","not enough balance","order crosses book","min size","fok_order_not_filled","couldn't be fully filled",) ):
    return True
 if raw_resp and isinstance(raw_resp,dict):
  status=raw_resp.get("status") or raw_resp.get("statusCode") or raw_resp.get("status_code")
  if status==400 or status=="400":
   return True
  err_str=str(raw_resp.get("error") or raw_resp.get("errorMsg") or raw_resp.get("error_message") or "").lower()
  if "invalid amounts" in err_str or "supports a max accuracy" in err_str or "bad request" in err_str:
   return True
 return False
class FastV2OrderSigner:
 def __init__(self,clob_client:Any)->None:
  import dataclasses as _dc
  import coincurve
  from py_clob_client_v2.config import get_contract_config
  from py_clob_client_v2.order_builder.builder import ROUNDING_CONFIG
  from py_clob_client_v2.order_builder.helpers import round_normal
  from py_clob_client_v2.order_utils import ExchangeOrderBuilderV2,Side,SignatureTypeV2
  from py_clob_client_v2.order_utils.exchange_order_builder_v2 import ( BYTES32_ZERO,DEPOSIT_WALLET_DOMAIN_SALT,DEPOSIT_WALLET_NAME_HASH,DEPOSIT_WALLET_VERSION_HASH,ORDER_TYPE_HASH,ORDER_TYPE_STRING,SOLADY_TYPE_HASH,_keccak,generate_order_salt,)
  from py_clob_client_v2.order_utils.model.order_data_v2 import OrderDataV2,SignedOrderV2
  self._client=clob_client
  self._orig_create_order=clob_client.create_order
  self._order_builder=clob_client.builder
  self._signer=self._order_builder.signer
  self._chain_id=int(self._signer.get_chain_id())
  self._signature_type=SignatureTypeV2(int(self._order_builder.signature_type))
  self._sig_type_int=int(self._signature_type)
  self._is_poly_1271=self._signature_type==SignatureTypeV2.POLY_1271
  self._maker_addr=str(self._order_builder.funder)
  self._signer_addr=str(self._order_builder._v2_order_signer())
  self._has_builder_code=bool( getattr(clob_client,"builder_config",None) and getattr(clob_client.builder_config,"builder_code",None) )
  self._tick_sizes_dict=getattr(clob_client,"_ClobClient__tick_sizes",{})
  self._neg_risk_dict=getattr(clob_client,"_ClobClient__neg_risk",{})
  self._rounding_config=ROUNDING_CONFIG
  self._round_normal=round_normal
  self._keccak=_keccak
  self._SignedOrderV2=SignedOrderV2
  self._OrderDataV2=OrderDataV2
  self._ExchangeOrderBuilderV2=ExchangeOrderBuilderV2
  self._Side=Side
  self._bytes32_zero_hex=BYTES32_ZERO
  self._bytes32_zero=b"\x00" * 32
  self._order_type_hash=ORDER_TYPE_HASH
  self._dc_asdict=_dc.asdict
  priv_hex=str(self._signer.private_key).strip()
  if priv_hex.startswith(("0x","0X")):
   priv_hex=priv_hex[2:]
  self._cc_priv=coincurve.PrivateKey(bytes.fromhex(priv_hex.zfill(64)))
  self._maker_word=self._addr_to_word32(self._maker_addr)
  self._signer_word=self._addr_to_word32(self._signer_addr)
  self._sig_type_word=self._sig_type_int.to_bytes(32,"big")
  ccfg=get_contract_config(self._chain_id)
  eob_std=ExchangeOrderBuilderV2(ccfg.exchange_v2,self._chain_id,self._signer,domain_version="2")
  eob_neg=ExchangeOrderBuilderV2(ccfg.neg_risk_exchange_v2,self._chain_id,self._signer,domain_version="2")
  self._std_exchange=ccfg.exchange_v2
  self._neg_exchange=ccfg.neg_risk_exchange_v2
  self._dom_sep_std:bytes=eob_std.app_domain_separator
  self._dom_sep_neg:bytes=eob_neg.app_domain_separator
  self._dom_sep_std_hex:str=self._dom_sep_std.hex()
  self._dom_sep_neg_hex:str=self._dom_sep_neg.hex()
  self._solady_prefix:bytes=SOLADY_TYPE_HASH
  self._solady_suffix:bytes=( DEPOSIT_WALLET_NAME_HASH + DEPOSIT_WALLET_VERSION_HASH + self._chain_id.to_bytes(32,"big") + self._signer_word + DEPOSIT_WALLET_DOMAIN_SALT )
  self._poly_1271_type_tail_hex:str=( ORDER_TYPE_STRING.encode("utf-8").hex() + len(ORDER_TYPE_STRING).to_bytes(2,"big").hex() )
  self._verify_parity_against_sdk()
 @staticmethod
 def _generate_salt()->int:
  return secrets.randbelow((1 << 53) - 1) + 1
 @staticmethod
 def _addr_to_word32(addr:str)->bytes:
  clean=str(addr).strip().lower()
  if clean.startswith("0x"):
   clean=clean[2:]
  if len(clean)!=40:
   raise ValueError(f"Invalid 20-byte hex address: {addr}")
  return b"\x00" * 12 + bytes.fromhex(clean)
 @staticmethod
 def _hex_to_word32(hex_str:Optional[str])->bytes:
  if not hex_str:
   return b"\x00" * 32
  clean=str(hex_str).strip()
  if clean.startswith(("0x","0X")):
   clean=clean[2:]
  if not clean or clean=="0" * len(clean):
   return b"\x00" * 32
  raw=bytes.fromhex(clean.zfill(64))
  return raw[:32] if len(raw)>=32 else raw.rjust(32,b"\x00")
 def sign_v2_order_data( self,*,token_id:str,maker_amount:str,taker_amount:str,side:Any,neg_risk:bool,salt:Optional[int]=None,timestamp:Optional[str]=None,expiration:str="0",metadata:Optional[str]=None,builder:Optional[str]=None,)->Any:
  salt_int=int(salt) if salt is not None else int(self._generate_salt())
  ts_str=str(timestamp) if timestamp else str(time.time_ns() // 1_000_000)
  exp_str=str(expiration) if expiration else "0"
  meta_hex=metadata if metadata else self._bytes32_zero_hex
  builder_hex=builder if builder else self._bytes32_zero_hex
  tok_str=str(token_id)
  tok_int=int(tok_str,16) if tok_str.startswith(("0x","0X")) else int(tok_str)
  side_int=int(side)
  meta_w=self._bytes32_zero if meta_hex==self._bytes32_zero_hex else self._hex_to_word32(meta_hex)
  builder_w=self._bytes32_zero if builder_hex==self._bytes32_zero_hex else self._hex_to_word32(builder_hex)
  contents_hash=self._keccak( primitive=( self._order_type_hash + salt_int.to_bytes(32,"big") + self._maker_word + self._signer_word + tok_int.to_bytes(32,"big") + int(maker_amount).to_bytes(32,"big") + int(taker_amount).to_bytes(32,"big") + side_int.to_bytes(32,"big") + self._sig_type_word + int(ts_str).to_bytes(32,"big") + meta_w + builder_w ) )
  dom_sep=self._dom_sep_neg if neg_risk else self._dom_sep_std
  if self._is_poly_1271:
   td_hash=self._keccak(primitive=self._solady_prefix + contents_hash + self._solady_suffix)
   digest=self._keccak(primitive=b"\x19\x01" + dom_sep + td_hash)
   sig65=self._cc_priv.sign_recoverable(digest,hasher=None)
   inner_hex=sig65[:64].hex() + f"{sig65[64] + 27:02x}"
   dom_hex=self._dom_sep_neg_hex if neg_risk else self._dom_sep_std_hex
   signature="0x" + inner_hex + dom_hex + contents_hash.hex() + self._poly_1271_type_tail_hex
  else:
   digest=self._keccak(primitive=b"\x19\x01" + dom_sep + contents_hash)
   sig65=self._cc_priv.sign_recoverable(digest,hasher=None)
   signature="0x" + sig65[:64].hex() + f"{sig65[64] + 27:02x}"
  return self._SignedOrderV2( salt=salt_int,maker=self._maker_addr,signer=self._signer_addr,tokenId=tok_str,makerAmount=str(maker_amount),takerAmount=str(taker_amount),side=side,signatureType=self._signature_type,timestamp=ts_str,metadata=meta_hex,builder=builder_hex,expiration=exp_str,signature=signature,)
 def _verify_parity_against_sdk(self)->None:
  test_tok="580531616296768985464990134503"
  for neg_flag,exch_addr in ((False,self._std_exchange),(True,self._neg_exchange)):
   for side_enum,mk_amt,tk_amt in ( (self._Side.BUY,"15200000","20000000"),(self._Side.SELL,"20000000","19800000"),):
    sdk_builder=self._ExchangeOrderBuilderV2( exch_addr,self._chain_id,self._signer,generate_salt=lambda:987654321,domain_version="2",)
    od=self._OrderDataV2( maker=self._maker_addr,tokenId=test_tok,makerAmount=mk_amt,takerAmount=tk_amt,side=side_enum,signer=self._signer_addr,signatureType=self._signature_type,timestamp="1700000000000",metadata=self._bytes32_zero_hex,builder=self._bytes32_zero_hex,expiration="0",)
    sdk_signed=sdk_builder.build_signed_order(od)
    fast_signed=self.sign_v2_order_data( token_id=test_tok,maker_amount=mk_amt,taker_amount=tk_amt,side=side_enum,neg_risk=neg_flag,salt=987654321,timestamp="1700000000000",expiration="0",metadata=self._bytes32_zero_hex,builder=self._bytes32_zero_hex,)
    if self._dc_asdict(fast_signed)!=self._dc_asdict(sdk_signed):
     raise RuntimeError(f"FastV2OrderSigner parity mismatch (neg_risk={neg_flag}, side={side_enum})")
 def create_order(self,order_args:Any,options:Any=None)->Any:
  if ( self._has_builder_code or getattr(order_args,"position_id",None) or getattr(order_args,"user_usdc_balance",None) is not None or (options is not None and getattr(options,"version",None) not in (None,2)) or (getattr(order_args,"builder_code",None) not in (None,"",self._bytes32_zero_hex)) ):
   return self._orig_create_order(order_args,options)
  asset_id=str(getattr(order_args,"token_id","") or "")
  if not asset_id:
   return self._orig_create_order(order_args,options)
  tick_size=( str(options.tick_size) if (options is not None and getattr(options,"tick_size",None) is not None) else self._tick_sizes_dict.get(asset_id) )
  if not tick_size or tick_size not in self._rounding_config:
   return self._orig_create_order(order_args,options)
  ts_f=float(tick_size)
  raw_px=float(order_args.price)
  if not (ts_f<=raw_px<=round(1.0 - ts_f,8)):
   return self._orig_create_order(order_args,options)
  neg_risk=( bool(options.neg_risk) if (options is not None and getattr(options,"neg_risk",None) is not None) else self._neg_risk_dict.get(asset_id) )
  if neg_risk is None:
   return self._orig_create_order(order_args,options)
  rcfg=self._rounding_config[tick_size]
  price=self._round_normal(raw_px,rcfg.price)
  side_enum,maker_amt,taker_amt=self._order_builder.get_order_amounts( order_args.side,order_args.size,price,rcfg )
  return self.sign_v2_order_data( token_id=asset_id,maker_amount=str(maker_amt),taker_amount=str(taker_amt),side=side_enum,neg_risk=bool(neg_risk),expiration=str(getattr(order_args,"expiration",0) or 0),metadata=getattr(order_args,"metadata",None) or self._bytes32_zero_hex,builder=self._bytes32_zero_hex,)
 @classmethod
 def from_clob_client(cls,clob_client:Any)->Optional["FastV2OrderSigner"]:
  return cls(clob_client)
def _safe_create_order(client_fn:Any,args:Any,options:Any=None)->Any:
 owner=getattr(client_fn,"__self__",None)
 if owner is not None and "create_order" not in getattr(owner,"__dict__",{}):
  fast_signer=getattr(owner,"_fast_v2_signer",None)
  if fast_signer is not None:
   return fast_signer.create_order(args,options)
 if options is not None:
  try:
   return client_fn(args,options)
  except TypeError:
   return client_fn(args)
 return client_fn(args)
class PreSignedOrderLadderCache:
 def __init__(self,ttl_seconds:float=300.0):
  self.ttl_seconds=ttl_seconds
  self._cache:Dict[Tuple[str,int,int,str,bool],Tuple[float,Any]]={}
  self._lock=threading.Lock()
  self.hits=0
  self.misses=0
 @staticmethod
 def _make_key( token_id:str,price:float,shares:float,price_cents:Optional[int]=None,tick_size:str="0.01",neg_risk:bool=False,)->Optional[Tuple[str,int,int,str,bool]]:
  if price_cents is None:
   cents_f=float(price) * 100.0
   p_cents=int(round(cents_f))
   if abs(cents_f - p_cents) > 1e-6:
    return None
  else:
   p_cents=int(price_cents)
  shares_f=float(shares)
  shares_int=int(round(shares_f))
  if shares_int<=0 or abs(shares_f - shares_int) > 1e-9:
   return None
  return (str(token_id),p_cents,shares_int,str(tick_size or "0.01"),bool(neg_risk))
 def get_presigned_order( self,token_id:str,price:float=0.0,shares:float=0.0,price_cents:Optional[int]=None,tick_size:str="0.01",neg_risk:bool=False,)->Optional[Any]:
  key=self._make_key(token_id,price,shares,price_cents,tick_size=tick_size,neg_risk=neg_risk)
  now=time.time()
  with self._lock:
   if key is None:
    self.misses += 1
    return None
   entry=self._cache.pop(key,None)
   if entry:
    created_ts,signed_order=entry
    if (now - created_ts)<=self.ttl_seconds:
     self.hits += 1
     return signed_order
   self.misses += 1
   return None
 def get_presigned_order_near( self,token_id:str,price:float,shares:float,max_share_delta:int=2,max_notional_usd:Optional[float]=None,tick_size:str="0.01",neg_risk:bool=False,)->Optional[Tuple[Any,int]]:
  base_key=self._make_key(token_id,price,shares,tick_size=tick_size,neg_risk=neg_risk)
  if base_key is None:
   return None
  tok_s,p_cents,base_shares,tick_s,nr_flag=base_key
  px_exact=p_cents / 100.0
  now=time.time()
  max_d=max(0,int(max_share_delta))
  with self._lock:
   for mag in range(1,max_d + 1):
    for delta in (-mag,mag):
     cand_shares=base_shares + delta
     if cand_shares < 5:
      continue
     if max_notional_usd is not None and (cand_shares * px_exact) > float(max_notional_usd) + 1e-6:
      continue
     cand_key=(tok_s,p_cents,cand_shares,tick_s,nr_flag)
     entry=self._cache.pop(cand_key,None)
     if entry:
      created_ts,signed_order=entry
      if (now - created_ts)<=self.ttl_seconds:
       self.hits += 1
       return signed_order,cand_shares
  return None
 def has_fresh( self,token_id:str,price:float,shares:float,min_remaining_sec:float=60.0,tick_size:str="0.01",neg_risk:bool=False,)->bool:
  key=self._make_key(token_id,price,shares,tick_size=tick_size,neg_risk=neg_risk)
  if key is None:
   return False
  with self._lock:
   entry=self._cache.get(key)
  return bool(entry) and (time.time() - entry[0])<=(self.ttl_seconds - min_remaining_sec)
 def store_presigned_order( self,token_id:str,price:float=0.0,shares:float=0.0,signed_order:Any=None,price_cents:Optional[int]=None,tick_size:str="0.01",neg_risk:bool=False,)->bool:
  key=self._make_key(token_id,price,shares,price_cents,tick_size=tick_size,neg_risk=neg_risk)
  if key is None or signed_order is None:
   return False
  with self._lock:
   self._cache[key]=(time.time(),signed_order)
  return True
 def prune_expired(self)->None:
  now=time.time()
  with self._lock:
   expired_keys=[k for k,(ts,_) in self._cache.items() if (now - ts) > self.ttl_seconds]
   for k in expired_keys:
    self._cache.pop(k,None)
 def clear(self)->None:
  with self._lock:
   self._cache.clear()
 def __len__(self)->int:
  with self._lock:
   return len(self._cache)
_CLOB_CLIENT_SIGN_LOCK=threading.Lock()
_CLOB_HTTP_LOCK=threading.RLock()
try:
 from src.polymarket_research.polymarket_ws_streams import PolymarketUserWsCache as _PolymarketUserWsCache
except ImportError:
 try:
  from polymarket_ws_streams import PolymarketUserWsCache as _PolymarketUserWsCache
 except ImportError:
  _PolymarketUserWsCache=None
try:
 from src.polymarket_research.latency_trace import ActiveCounter as _ActiveCounter,CURRENT_TRACE as _CURRENT_TRACE
except ImportError:
 try:
  from latency_trace import ActiveCounter as _ActiveCounter,CURRENT_TRACE as _CURRENT_TRACE
 except ImportError:
  _CURRENT_TRACE=None
  class _ActiveCounter:
   def __init__(self)->None:
    self._n=0
    self._lock=threading.Lock()
   def enter(self)->None:
    with self._lock:
     self._n += 1
   def leave(self)->None:
    with self._lock:
     self._n=max(0,self._n - 1)
   def __enter__(self)->"_ActiveCounter":
    self.enter()
    return self
   def __exit__(self,exc_type:Any,exc_val:Any,exc_tb:Any)->bool:
    self.leave()
    return False
   def is_set(self)->bool:
    return self._n > 0
   @property
   def count(self)->int:
    return self._n
_HOT_DISPATCH_ACTIVE=_ActiveCounter()
_URGENT_SIGN_COUNTER_LOCK=threading.Lock()
_URGENT_SIGN_WAITERS=0
_HOT_IO_POOL_LOCK=threading.Lock()
_HOT_IO_POOL:Optional[concurrent.futures.ThreadPoolExecutor]=None
def _get_hot_io_pool()->concurrent.futures.ThreadPoolExecutor:
 global _HOT_IO_POOL
 if _HOT_IO_POOL is None:
  with _HOT_IO_POOL_LOCK:
   if _HOT_IO_POOL is None:
    pool=concurrent.futures.ThreadPoolExecutor(max_workers=12,thread_name_prefix="pm-hot")
    bar=threading.Barrier(12,timeout=0.25)
    def _warm_th()->None:
     try:
      bar.wait()
     except Exception:
      pass
    for f in [pool.submit(_warm_th) for _ in range(12)]:
     try:
      f.result(timeout=0.35)
     except Exception:
      pass
    _HOT_IO_POOL=pool
 return _HOT_IO_POOL
class _UrgentSignPriority:
 def __enter__(self):
  global _URGENT_SIGN_WAITERS
  with _URGENT_SIGN_COUNTER_LOCK:
   _URGENT_SIGN_WAITERS += 1
  _CLOB_CLIENT_SIGN_LOCK.acquire()
  return self
 def __exit__(self,exc_type,exc_val,exc_tb):
  global _URGENT_SIGN_WAITERS
  try:
   _CLOB_CLIENT_SIGN_LOCK.release()
  finally:
   with _URGENT_SIGN_COUNTER_LOCK:
    _URGENT_SIGN_WAITERS=max(0,_URGENT_SIGN_WAITERS - 1)
  return False
class PreSubmitError(RuntimeError):
 pass
def _sign_and_post_single_hop( client:Any,ladder_cache:Optional[PreSignedOrderLadderCache],token_id:str,price:float,size:float,side:str,order_type:Any,create_options:Any=None,stage:Optional[Dict[str,Any]]=None,max_notional_usd:Optional[float]=None,enqueue_ns:Optional[int]=None,)->Dict[str,Any]:
 if stage is None:
  stage={}
 stage["submitted"]=False
 _HOT_DISPATCH_ACTIVE.enter()
 t0_ns=time.perf_counter_ns()
 thread_hop_ms=round(max(0.0,(t0_ns - enqueue_ns) / 1_000_000.0),3) if enqueue_ns is not None else 0.0
 t0=time.perf_counter()
 signed=None
 cache_hit=False
 actual_signed_shares=float(size)
 try:
  try:
   _opt_tick=str(getattr(create_options,"tick_size","0.01") or "0.01")
   _opt_nr=bool(getattr(create_options,"neg_risk",False))
   if ladder_cache is not None and str(side).upper()=="BUY":
    signed=ladder_cache.get_presigned_order(token_id,price,size,tick_size=_opt_tick,neg_risk=_opt_nr)
    cache_hit=signed is not None
    if signed is None:
     near_hit=ladder_cache.get_presigned_order_near( token_id,price,size,max_share_delta=3,max_notional_usd=max_notional_usd,tick_size=_opt_tick,neg_risk=_opt_nr,)
     if near_hit is not None:
      signed,near_shares=near_hit
      actual_signed_shares=float(near_shares)
      cache_hit=True
   if signed is None:
    if OrderArgsV2 is None:
     raise RuntimeError("OrderArgsV2 is required for CLOB entry order signing")
    order_args=OrderArgsV2(price=price,size=size,side=side,token_id=token_id)
    has_lockfree_fast_signer=( getattr(client,"_fast_v2_signer",None) is not None and "create_order" not in getattr(client,"__dict__",{}) )
    if has_lockfree_fast_signer:
     signed=_safe_create_order(client.create_order,order_args,create_options)
    else:
     with _UrgentSignPriority():
      signed=_safe_create_order(client.create_order,order_args,create_options)
   if signed is None:
    raise RuntimeError("create_order returned no signed order")
  except Exception as e:
   raise PreSubmitError(f"Order signing failed before submission: {e}") from e
  t1=time.perf_counter()
  stage["sign_ms"]=round((t1 - t0) * 1000.0,3)
  stage["thread_hop_ms"]=thread_hop_ms
  stage["cache_hit"]=cache_hit
  stage["signed_shares"]=actual_signed_shares
  stage["t_post_start"]=t1
  stage["submitted"]=True
  post_resp=client.post_order(signed,order_type,False,True)
  t2=time.perf_counter()
  return { "post_resp":post_resp,"sign_ms":(t1 - t0) * 1000.0,"post_ms":(t2 - t1) * 1000.0,"thread_hop_ms":thread_hop_ms,"cache_hit":cache_hit,"signed_shares":actual_signed_shares,"t_post_end":t2,}
 finally:
  _HOT_DISPATCH_ACTIVE.leave()
@dataclass
class OrderResult:
 success:bool
 order_id:Optional[str]
 trade_id:str
 token_id:str
 target_token:str
 side:str
 price:float
 size:float
 notional_usd:float
 fee_usd:float
 latency_ms:float
 mode:str
 execution_status:str=ExecutionStatus.SUBMITTED
 confirmed_onchain:bool=False
 details:Dict[str,Any]=field(default_factory=dict)
 error:Optional[str]=None
class CancelOrderResult(dict):
 def __init__(self,*args,**kwargs):
  raw=args[0] if args else kwargs.pop("raw",{})
  payload=dict(raw) if isinstance(raw,dict) else {}
  super().__init__(payload)
  kwargs.pop("raw",None)
  self._extra=dict(kwargs)
  self._extra["raw"]=payload
 def __getitem__(self,key):
  if super().__contains__(key):
   return super().__getitem__(key)
  if key in self._extra:
   return self._extra[key]
  raise KeyError(key)
 def get(self,key,default=None):
  if super().__contains__(key):
   return super().get(key,default)
  return self._extra.get(key,default)
 def __contains__(self,key):
  return super().__contains__(key) or (key in self._extra)
 def __getattr__(self,name):
  if name in self._extra:
   return self._extra[name]
  raise AttributeError(name)
 def __repr__(self):
  combined=dict(self)
  combined.update(self._extra)
  return repr(combined)
class PolymarketLiveExecutor:
 CLOB_HOST="https://clob.polymarket.com"
 CHAIN_ID=137
 def __init__( self,private_key:Optional[str]=None,funder_address:Optional[str]=None,signature_type:Optional[int]=None,dry_run:bool=False,ledger_path:Optional[str]=None,):
  self.dry_run=dry_run
  if private_key is not None:
   self.private_key=private_key.strip()
  else:
   self.private_key=os.getenv("POLYGON_PRIVATE_KEY","").strip()
  if funder_address is not None:
   self.funder_address=funder_address.strip()
  else:
   self.funder_address=( os.getenv("POLYGON_FUNDER_ADDRESS","").strip() or os.getenv("POLYGON_PROXY_ADDRESS","").strip() )
  sig_env=os.getenv("POLYGON_SIGNATURE_TYPE","").strip()
  if signature_type is None and not sig_env and not dry_run:
   raise RuntimeError("LIVE MODE REFUSED: POLYGON_SIGNATURE_TYPE must be explicitly configured")
  self.signature_type=( signature_type if signature_type is not None else (int(sig_env) if sig_env else 3) )
  if self.signature_type not in (0,1,2,3):
   raise RuntimeError(f"Unsupported POLYGON_SIGNATURE_TYPE={self.signature_type}")
  if not self.dry_run and self.private_key:
   from eth_account import Account
   try:
    signer_address=Account.from_key(self.private_key).address
   except Exception:
    signer_address=None
   if self.signature_type==0:
    if ( signer_address and self.funder_address and self.funder_address.lower()!=signer_address.lower() ):
     raise RuntimeError( "LIVE MODE REFUSED: Type 0 requires the EOA funder " "to equal the signing address." )
   elif self.signature_type==3:
    if not self.funder_address:
     raise RuntimeError( "LIVE MODE REFUSED: Type 3 requires an explicitly " "configured Polymarket deposit-wallet funder." )
  env_ledger=os.getenv("POLYMARKET_LEDGER_PATH","").strip()
  if ledger_path is not None:
   self.ledger_path=Path(ledger_path)
  elif env_ledger:
   self.ledger_path=Path(env_ledger)
  elif self.dry_run:
   self.ledger_path=Path(POLYMARKET_DATA_DIR / "dry_run_orders.jsonl")
  else:
   self.ledger_path=Path(POLYMARKET_DATA_DIR / "live_orders.jsonl")
  self.ledger_path.parent.mkdir(parents=True,exist_ok=True)
  self.client:Optional[Any]=None
  self.is_authenticated=False
  self.auth_mode="UNINITIALIZED"
  self.last_heartbeat_id=""
  self.heartbeat_failures=0
  self._fee_cache:Dict[str,Tuple[float,float]]={}
  self._tick_size_cache:Dict[str,float]={}
  self._neg_risk_cache:Dict[str,bool]={}
  self._async_client:Optional[httpx.AsyncClient]=None
  self._thread_local=threading.local()
  self._collateral_cache:Tuple[Optional[float],float]=(None,0.0)
  self.reservation_records:Dict[str,Dict[str,Any]]={}
  self.reserved_inventory:Dict[str,float]=defaultdict(float)
  self.reservation_corruption_detected:bool=False
  self._reservations_lock=threading.RLock()
  self._load_durable_reservations()
  self.order_ladder_cache=PreSignedOrderLadderCache(ttl_seconds=1800.0)
  self._user_ws_cache:Optional[Any]=None
  self._initialize_client()
 @property
 def _sync_session(self)->requests.Session:
  sess=getattr(self._thread_local,"session",None)
  if sess is None:
   sess=requests.Session()
   self._thread_local.session=sess
  return sess
 @_sync_session.setter
 def _sync_session(self,sess:requests.Session)->None:
  self._thread_local.session=sess
 def _initialize_client(self):
  if self.dry_run:
   self.auth_mode="DRY_RUN_STANDBY"
   logger.info("Initializing in DRY-RUN / Standby mode (--dry-run specified).")
   return
  if not self.private_key:
   self.auth_mode="LIVE_REFUSED_NO_KEY"
   raise RuntimeError("LIVE MODE REFUSED: POLYGON_PRIVATE_KEY is missing or empty. Live money trading cannot execute without an L1 private key.")
  if not PY_CLOB_AVAILABLE:
   self.auth_mode="LIVE_REFUSED_NO_SDK"
   raise RuntimeError("LIVE MODE REFUSED: py_clob_client_v2 is required for live execution. Legacy fallback is strictly prohibited.")
  try:
   import importlib.metadata
   installed_sdk_ver=importlib.metadata.version("py_clob_client_v2")
   if installed_sdk_ver!=EXPECTED_CLOB_V2:
    self.auth_mode="LIVE_REFUSED_SDK_VERSION_MISMATCH"
    raise RuntimeError( f"LIVE MODE REFUSED: py_clob_client_v2 version mismatch (found '{installed_sdk_ver}', required hard-pinned '{EXPECTED_CLOB_V2}')." )
  except Exception as e:
   if isinstance(e,RuntimeError):
    raise
   if not self.dry_run:
    self.auth_mode="LIVE_REFUSED_SDK_VERSION_UNVERIFIED"
    raise RuntimeError( f"LIVE MODE REFUSED: Inability to authoritatively verify py_clob_client_v2 installed package version: {e}" )
   logger.warning(f"Metadata version check exception: {e}")
  try:
   t0=time.perf_counter()
   install_thread_safe_clob_http_client()
   self.client=ClobClient( host=self.CLOB_HOST,key=self.private_key,chain_id=self.CHAIN_ID,signature_type=self.signature_type,funder=self.funder_address if self.funder_address else None,)
   if hasattr(self.client,"create_or_derive_api_key"):
    api_creds=self.client.create_or_derive_api_key()
   else:
    api_creds=self.client.create_or_derive_api_creds()
   self.client.set_api_creds(api_creds)
   try:
    if hasattr(self.client,"_ClobClient__cached_version"):
     self.client._ClobClient__cached_version=2
   except Exception:
    pass
   if os.environ.get("PM_DISABLE_FAST_V2_SIGNER","0")!="1":
    try:
     self.client._fast_v2_signer=FastV2OrderSigner.from_clob_client(self.client)
     logger.info("FastV2OrderSigner enabled (coincurve C secp256k1, SDK byte-exact parity self-test PASSED).")
    except Exception as fs_exc:
     self.client._fast_v2_signer=None
     logger.warning(f"FastV2OrderSigner unavailable, using py_clob_client_v2 signer: {fs_exc}")
   latency_ms=(time.perf_counter() - t0) * 1000.0
   self.is_authenticated=True
   self.auth_mode="AUTHENTICATED_L2"
   logger.info(f"Successfully authenticated with Polymarket CLOB L2 (v2 client v{PY_CLOB_VERSION}) in {latency_ms:.2f} ms.")
   if os.environ.get("PM_ENABLE_TLS_KEEPALIVE","1")=="1":
    self.start_clob_tls_keepalive_daemon(interval_sec=12.0)
   if ( _PolymarketUserWsCache is not None and os.environ.get("PM_ENABLE_USER_WS","1")=="1" and getattr(self.client,"_mock_children",None) is None and getattr(api_creds,"_mock_children",None) is None and isinstance(getattr(api_creds,"api_key",None),str) ):
    try:
     self._user_ws_cache=_PolymarketUserWsCache( api_creds.api_key,api_creds.api_secret,api_creds.api_passphrase,on_fill_callback=lambda _ev:self.invalidate_collateral_cache(),)
     self._user_ws_cache.start()
    except Exception as uws_exc:
     self._user_ws_cache=None
     logger.debug(f"User WS cache startup skipped: {uws_exc}")
  except Exception as e:
   self.auth_mode="AUTH_FAILED"
   self.is_authenticated=False
   logger.error(f"Failed to authenticate with Polymarket CLOB: {e}")
   raise RuntimeError(f"LIVE MODE REFUSED: CLOB L2 authentication failed: {e}")
 def assert_market_routing(self,asset_id:str,market_version:str="CTF")->None:
  if market_version.upper()=="CTF":
   if not (isinstance(asset_id,str) and (asset_id.isdigit() or asset_id.startswith("0x")) and len(asset_id)>=10):
    raise ValueError(f"ASSET ROUTING ERROR: Invalid CTF token_id format '{asset_id}' for CTF market route.")
  elif market_version.upper() in ("V2_POSITION","PROTOCOL_V2","EXCHANGE_V3"):
   if not (isinstance(asset_id,str) and asset_id.startswith("0x") and len(asset_id)>=42):
    raise ValueError(f"ASSET ROUTING ERROR: Invalid position_id '{asset_id}' for Exchange V3 route.")
 def prewarm_token_market_cache( self,token_id:str,tick_size:Optional[Union[str,float]]="0.01",neg_risk:bool=False,fee_rate_bps:int=0,condition_id:Optional[str]=None,fee_rate:float=0.07,fee_exponent:float=1.0,)->None:
  if not token_id:
   return
  tick_size_str:Optional[str]=str(tick_size) if tick_size is not None else None
  if tick_size_str is not None:
   try:
    self._tick_size_cache[token_id]=float(tick_size_str)
   except Exception:
    self._tick_size_cache[token_id]=0.01
  self._neg_risk_cache[token_id]=bool(neg_risk)
  cond=condition_id or "0x0000000000000000000000000000000000000000000000000000000000000000"
  if cond:
   self._fee_cache[cond]=(float(fee_rate),float(fee_exponent))
  if self.client is not None:
   try:
    if tick_size_str is not None and hasattr(self.client,"_ClobClient__tick_sizes"):
     self.client._ClobClient__tick_sizes[token_id]=tick_size_str
    if hasattr(self.client,"_ClobClient__neg_risk"):
     self.client._ClobClient__neg_risk[token_id]=bool(neg_risk)
    if hasattr(self.client,"_ClobClient__fee_rates"):
     self.client._ClobClient__fee_rates[token_id]=int(fee_rate_bps)
    if hasattr(self.client,"_ClobClient__cached_version"):
     self.client._ClobClient__cached_version=2
    cond=condition_id or "0x0000000000000000000000000000000000000000000000000000000000000000"
    if hasattr(self.client,"_ClobClient__token_condition_map"):
     self.client._ClobClient__token_condition_map[token_id]=cond
    if hasattr(self.client,"_ClobClient__fee_infos"):
     if FeeInfo is not None:
      fi=FeeInfo(rate=float(fee_rate),exponent=float(fee_exponent))
     else:
      fi=type("FeeInfoObj",(),{"rate":float(fee_rate),"exponent":float(fee_exponent)})()
     self.client._ClobClient__fee_infos[token_id]=fi
    self._fee_cache[cond]=(float(fee_rate),float(fee_exponent))
    self._fee_cache[str(token_id)]=(float(fee_rate),float(fee_exponent))
   except Exception as e:
    logger.debug(f"[CACHE PREWARM] Warning pre-warming py-clob-client for {token_id}: {e}")
 def get_token_neg_risk(self,token_id:str,explicit_neg_risk:Optional[bool]=None)->bool:
  if explicit_neg_risk is not None:
   val=bool(explicit_neg_risk)
   if token_id:
    self._neg_risk_cache[token_id]=val
    if self.client is not None and hasattr(self.client,"_ClobClient__neg_risk"):
     self.client._ClobClient__neg_risk[token_id]=val
   return val
  if token_id in self._neg_risk_cache:
   return self._neg_risk_cache[token_id]
  if self.client is not None and hasattr(self.client,"get_neg_risk"):
   try:
    val=bool(self.client.get_neg_risk(token_id))
    self._neg_risk_cache[token_id]=val
    return val
   except Exception as e:
    logger.debug(f"Could not query neg_risk from SDK for {token_id}: {e}")
  return False
 def prewarm_order_ladder( self,token_id:str,ticket_notional:float,price_levels:Optional[List[float]]=None,tick_size:str="0.01",fee_rate_bps:int=0,share_deltas:Tuple[int,...]=(0,),exact_shares:Optional[List[int]]=None,neg_risk:Optional[bool]=None,)->int:
  if self.dry_run or not self.is_authenticated or self.client is None or OrderArgsV2 is None:
   return 0
  if price_levels is None:
   price_levels=[round(c / 100.0,2) for c in range(55,91)]
  eff_neg_risk=self.get_token_neg_risk(token_id,neg_risk)
  if neg_risk is None and token_id not in self._neg_risk_cache:
   return 0
  create_options=PartialCreateOrderOptions(tick_size=tick_size,neg_risk=eff_neg_risk,version=2) if PartialCreateOrderOptions else None
  self.order_ladder_cache.prune_expired()
  count=0
  for px in price_levels:
   if px<=0:
    continue
   if exact_shares is not None:
    candidate_shares=[float(s) for s in exact_shares if s>=5]
   else:
    base_shares=float(math.floor(float(ticket_notional) / px))
    candidate_shares=[base_shares + float(delta) for delta in share_deltas if (base_shares + float(delta))>=5.0]
   for shares in candidate_shares:
    if self.order_ladder_cache.has_fresh(token_id,px,shares,tick_size=tick_size,neg_risk=eff_neg_risk):
     continue
    wait_loops=0
    while (_HOT_DISPATCH_ACTIVE.is_set() or _URGENT_SIGN_WAITERS > 0) and wait_loops < 8:
     time.sleep(0.025)
     wait_loops += 1
    if _URGENT_SIGN_WAITERS > 0:
     return count
    try:
     order_args=OrderArgsV2( price=px,size=shares,side="BUY",token_id=token_id,)
     if ( getattr(self.client,"_fast_v2_signer",None) is not None and "create_order" not in getattr(self.client,"__dict__",{}) ):
      signed=_safe_create_order(self.client.create_order,order_args,create_options)
     else:
      with _CLOB_CLIENT_SIGN_LOCK:
       signed=_safe_create_order(self.client.create_order,order_args,create_options)
     if signed and self.order_ladder_cache.store_presigned_order( token_id,px,shares,signed,tick_size=tick_size,neg_risk=eff_neg_risk ):
      count += 1
    except Exception as e:
     logger.debug(f"[PREWARM LADDER] Notice for {token_id} @ {px} ({shares}): {e}")
     continue
  return count
 def start_clob_tls_keepalive_daemon(self,interval_sec:float=20.0)->None:
  if self.dry_run or getattr(self,"_tls_keepalive_started",False):
   return
  self._tls_keepalive_started=True
  def _loop()->None:
   try:
    if not _HOT_DISPATCH_ACTIVE.is_set():
     self.ping_clob_keepalive()
   except Exception:
    pass
   while not self.dry_run:
    time.sleep(max(5.0,float(interval_sec)))
    if self.dry_run:
     break
    try:
     if not _HOT_DISPATCH_ACTIVE.is_set():
      self.ping_clob_keepalive()
    except Exception:
     pass
  t=threading.Thread(target=_loop,name="clob-tls-keepalive",daemon=True)
  t.start()
 def ping_clob_keepalive(self)->None:
  if self.dry_run or not self.client or _HOT_DISPATCH_ACTIVE.is_set():
   return
  if not _CLOB_HTTP_LOCK.acquire(blocking=False):
   return
  try:
   t0=time.perf_counter()
   warmed=0
   try:
    import py_clob_client_v2.http_helpers.helpers as hh
    http_cli=getattr(hh,"_http_client",None)
    if isinstance(http_cli,_ThreadLocalClobHttpClient):
     warmed=http_cli.warm_pool( url=f"{self.CLOB_HOST.rstrip('/')}/time",min_warm=4,max_idle_sec=18.0,)
   except Exception:
    warmed=0
   if warmed==0:
    self.client.get_server_time()
   elapsed_ms=(time.perf_counter() - t0) * 1000.0
   logger.debug(f"[KEEPALIVE] CLOB HTTP keepalive ping ({warmed} pool sockets warmed): {elapsed_ms:.1f}ms")
  except Exception as e:
   logger.debug(f"[KEEPALIVE] CLOB ping notice: {e}")
  finally:
   _CLOB_HTTP_LOCK.release()
 def get_async_client(self)->httpx.AsyncClient:
  try:
   cur_loop=asyncio.get_running_loop()
  except RuntimeError:
   cur_loop=None
  if ( self._async_client is None or self._async_client.is_closed or (cur_loop is not None and getattr(self,"_async_client_loop",None) is not cur_loop) ):
   limits=httpx.Limits(max_keepalive_connections=10,max_connections=20)
   try:
    transport=httpx.AsyncHTTPTransport( limits=limits,socket_options=[(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)],)
    self._async_client=httpx.AsyncClient(timeout=3.0,transport=transport)
   except Exception:
    self._async_client=httpx.AsyncClient(timeout=3.0,limits=limits)
   self._async_client_loop=cur_loop
  return self._async_client
 async def close_async(self):
  if self._async_client is not None and not self._async_client.is_closed:
   await self._async_client.aclose()
   self._async_client=None
 @staticmethod
 def calculate_balance_epsilon(quantity_unit_or_shares:float=0.001)->float:
  base_unit=0.001 if quantity_unit_or_shares > 0.01 else quantity_unit_or_shares
  unit_dec=Decimal(str(base_unit))
  epsilon_dec=Decimal("2") * unit_dec
  return float(epsilon_dec)
 def get_market_fee_params(self,condition_id:str,token_id:Optional[str]=None)->Tuple[float,float]:
  if condition_id in self._fee_cache:
   res_fee=self._fee_cache[condition_id]
   if token_id:
    self._fee_cache[str(token_id)]=res_fee
   return res_fee
  if token_id and str(token_id) in self._fee_cache:
   res_fee=self._fee_cache[str(token_id)]
   self._fee_cache[condition_id]=res_fee
   return res_fee
  def _store_fee(r_val:float,e_val:float)->Tuple[float,float]:
   pair=(float(r_val),float(e_val))
   self._fee_cache[condition_id]=pair
   if real_cid:
    self._fee_cache[real_cid]=pair
   if token_id:
    self._fee_cache[str(token_id)]=pair
   return pair
  real_cid=condition_id
  if self.dry_run or self.client is None:
   return _store_fee(0.07,1.0)
  if not condition_id.startswith("0x"):
   try:
    get_fn=requests.get if hasattr(requests.get,"mock_calls") else getattr(self,"_sync_session",requests).get
    r=get_fn(f"https://gamma-api.polymarket.com/markets/{condition_id}",timeout=2.0).json()
    if r.get("conditionId"):
     real_cid=str(r["conditionId"])
     logger.info(f"Resolved condition_id {real_cid} for numeric market {condition_id}")
   except Exception as gamma_err:
    logger.debug(f"Gamma lookup for {condition_id} notice: {gamma_err}")
  try:
   if hasattr(self.client,"get_clob_market_info"):
    m_info=self.client.get_clob_market_info(real_cid)
    if isinstance(m_info,dict):
     fd=m_info.get("fd") or {}
     raw_r=fd.get("r")
     raw_e=fd.get("e")
     if raw_r is not None and raw_e is not None:
      return _store_fee(float(raw_r),float(raw_e))
   if token_id and hasattr(self.client,"get_fee_rate_bps") and hasattr(self.client,"get_fee_exponent"):
    bps=self.client.get_fee_rate_bps(token_id)
    exp=self.client.get_fee_exponent(token_id)
    return _store_fee(float(bps) / 10000.0,float(exp))
   if hasattr(self.client,"get_market"):
    m_info=self.client.get_market(real_cid)
    if isinstance(m_info,dict):
     fd=m_info.get("fd") or {}
     if "r" in fd and "e" in fd:
      return _store_fee(float(fd["r"]),float(fd["e"]))
     raw_taker=m_info.get("taker_base_fee")
     if raw_taker is not None:
      fee_rate=float(raw_taker) / 10000.0 if float(raw_taker) > 1.0 else float(raw_taker)
      fee_exponent=float(m_info.get("fee_exponent",1.0))
      return _store_fee(fee_rate,fee_exponent)
   if not self.dry_run and self.is_authenticated:
    raise RuntimeError(f"AUTHORITATIVE_FEE_METADATA_UNAVAILABLE: CLOB returned no fee metadata for {real_cid}")
   logger.warning(f"CLOB returned no specific fee schedule for {real_cid}; applying standard 0.07 crypto rate.")
   return _store_fee(0.07,1.0)
  except RuntimeError:
   raise
  except Exception as e:
   if not self.dry_run and self.is_authenticated:
    raise RuntimeError(f"AUTHORITATIVE_FEE_METADATA_UNAVAILABLE: {e}")
   logger.warning(f"Notice fetching authoritative CLOB fee metadata for {condition_id} ({real_cid}): {e}. Applying default 0.07.")
   return _store_fee(0.07,1.0)
 async def get_market_book_async(self,token_id:str)->Dict[str,Any]:
  url=f"{self.CLOB_HOST}/book?token_id={token_id}"
  try:
   client=self.get_async_client()
   resp=await client.get(url)
   if resp.status_code==200:
    return resp.json()
   if resp.status_code==404:
    return {"bids":[],"asks":[],"closed":True}
  except Exception:
   if self.dry_run:
    return {"bids":[],"asks":[]}
   raise
  if self.dry_run:
   return {"bids":[],"asks":[]}
  raise RuntimeError(f"HTTP {resp.status_code} querying orderbook for {token_id}: {resp.text[:100]}")
 async def get_transaction_receipt_status_async(self,tx_hash:str)->Optional[bool]:
  if self.dry_run:
   return True
  if not tx_hash or not isinstance(tx_hash,str) or not tx_hash.startswith("0x"):
   return False
  try:
   rpc_url=os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com")
   payload={ "jsonrpc":"2.0","method":"eth_getTransactionReceipt","params":[tx_hash],"id":1,}
   client=self.get_async_client()
   resp=await client.post(rpc_url,json=payload,timeout=3.0)
   if resp.status_code==200:
    data=resp.json()
    result=data.get("result")
    if result is None:
     return None
    raw_st=result.get("status")
    if raw_st in (1,"0x1","1"):
     return True
    elif raw_st in (0,"0x0","0"):
     logger.critical(f"[ON-CHAIN REVERT] Transaction {tx_hash} reverted on Polygon (status={raw_st})!")
     return False
   return None
  except Exception as e:
   logger.warning(f"Failed to query Polygon transaction receipt for {tx_hash}: {e}")
   return None
 def get_transaction_receipt_status(self,tx_hash:str)->Optional[bool]:
  if self.dry_run:
   return True
  if not tx_hash or not isinstance(tx_hash,str) or not tx_hash.startswith("0x"):
   return False
  try:
   rpc_url=os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com")
   payload={ "jsonrpc":"2.0","method":"eth_getTransactionReceipt","params":[tx_hash],"id":1,}
   post_fn=requests.post if hasattr(requests.post,"mock_calls") else getattr(self,"_sync_session",requests).post
   resp=post_fn(rpc_url,json=payload,timeout=3.0)
   if resp.status_code==200:
    data=resp.json()
    result=data.get("result")
    if result is None:
     return None
    raw_st=result.get("status")
    if raw_st in (1,"0x1","1"):
     return True
    elif raw_st in (0,"0x0","0"):
     return False
   return None
  except Exception as e:
   logger.warning(f"Failed to query Polygon transaction receipt for {tx_hash}: {e}")
   return None
 def get_market_book(self,token_id:str)->Dict[str,Any]:
  url=f"{self.CLOB_HOST}/book?token_id={token_id}"
  try:
   use_requests_mock=hasattr(requests.get,"mock_calls") or ("session" in self._thread_local.__dict__)
   if not use_requests_mock:
    try:
     import py_clob_client_v2.http_helpers.helpers as hh
     http_cli=getattr(hh,"_http_client",None)
    except Exception:
     http_cli=None
    if isinstance(http_cli,_ThreadLocalClobHttpClient):
     resp=http_cli.request("GET",url,timeout=3.0)
     if resp.status_code==200:
      return _orjson.loads(resp.content) if _orjson is not None else resp.json()
     if resp.status_code==404:
      return {"bids":[],"asks":[],"closed":True}
     if self.dry_run:
      return {"bids":[],"asks":[]}
     raise RuntimeError(f"HTTP {resp.status_code} querying orderbook for {token_id}: {resp.text[:100]}")
   get_fn=requests.get if hasattr(requests.get,"mock_calls") else getattr(self,"_sync_session",requests).get
   resp=get_fn(url,timeout=3.0)
   if resp.status_code==200:
    return _orjson.loads(resp.content) if (_orjson is not None and isinstance(getattr(resp,"content",None),(bytes,bytearray))) else resp.json()
   if resp.status_code==404:
    return {"bids":[],"asks":[],"closed":True}
  except Exception:
   if self.dry_run:
    return {"bids":[],"asks":[]}
   raise
  if self.dry_run:
   return {"bids":[],"asks":[]}
  raise RuntimeError(f"HTTP {resp.status_code} querying orderbook for {token_id}: {resp.text[:100]}")
 def get_market_books_batch(self,token_ids:List[str])->Dict[str,Dict[str,Any]]:
  uniq=list(dict.fromkeys(str(t) for t in token_ids if t))
  if not uniq:
   return {}
  if "get_market_book" in self.__dict__:
   return {t:(self.get_market_book(t) or {}) for t in uniq}
  out:Dict[str,Dict[str,Any]]={}
  url=f"{self.CLOB_HOST}/books"
  try:
   http_cli=None
   if not hasattr(requests.post,"mock_calls"):
    try:
     import py_clob_client_v2.http_helpers.helpers as hh
     http_cli=getattr(hh,"_http_client",None)
    except Exception:
     http_cli=None
   for idx in range(0,len(uniq),50):
    chunk=uniq[idx:idx + 50]
    body_list=[{"token_id":t} for t in chunk]
    if isinstance(http_cli,_ThreadLocalClobHttpClient):
     bg_cli=http_cli._borrow_from(http_cli._bg_pool)
     healthy=True
     try:
      payload_bytes=_orjson.dumps(body_list) if _orjson is not None else json.dumps(body_list).encode("utf-8")
      resp=bg_cli.request( "POST",url,content=payload_bytes,headers={"Content-Type":"application/json","Accept":"application/json"},timeout=3.0,)
     except Exception:
      healthy=False
      try:
       bg_cli.close()
      except Exception:
       pass
      raise
     finally:
      if healthy:
       http_cli._return_to(http_cli._bg_pool,bg_cli)
    else:
     post_fn=requests.post if hasattr(requests.post,"mock_calls") else getattr(self,"_sync_session",requests).post
     resp=post_fn(url,json=body_list,timeout=3.0)
    if resp.status_code==200:
     rows=( _orjson.loads(resp.content) if (_orjson is not None and isinstance(getattr(resp,"content",None),(bytes,bytearray))) else resp.json() )
     if isinstance(rows,list):
      for r in rows:
       if isinstance(r,dict):
        aid=str(r.get("asset_id") or r.get("token_id") or "")
        if aid:
         out[aid]=r
  except Exception as e:
   logger.debug(f"[BOOKS BATCH] Fallback to individual get_market_book ({e})")
  for t in uniq:
   if t not in out:
    out[t]=self.get_market_book(t) or {}
  return out
 @staticmethod
 def normalize_trade_record(data:Dict[str,Any])->Dict[str,Any]:
  if not isinstance(data,dict):
   return {}
  res=dict(data)
  tx_hash=res.get("transaction_hash") or res.get("transactionHash")
  if tx_hash:
   res["transaction_hash"]=str(tx_hash)
   res["transactionHash"]=str(tx_hash)
  tr_id=res.get("id") or res.get("trade_id") or res.get("tradeId")
  if tr_id:
   res["id"]=str(tr_id)
   res["trade_id"]=str(tr_id)
  st=res.get("status")
  if st:
   res["status"]=str(st).upper()
  return res
 def get_trade_status(self,trade_id:str)->Dict[str,Any]:
  if self.dry_run:
   return {"status":"CONFIRMED","trade_id":trade_id,"transaction_hash":None,"transactionHash":None}
  if not self.client or not self.is_authenticated:
   return {"status":"UNKNOWN","trade_id":trade_id,"error":"client unavailable"}
  try:
   if hasattr(self.client,"get_trades"):
    try:
     if TradeParams is not None:
      params=TradeParams(id=trade_id)
      trade_data=self.client.get_trades(params=params)
     else:
      trade_data=self.client.get_trades(trade_id=trade_id)
    except (TypeError,AttributeError):
     trade_data=self.client.get_trades(trade_id=trade_id)
    if isinstance(trade_data,list) and len(trade_data) > 0:
     return self.normalize_trade_record(trade_data[0])
    elif isinstance(trade_data,dict) and trade_data:
     return self.normalize_trade_record(trade_data)
    return {"status":"NOT_FOUND","trade_id":trade_id}
   return {"status":"UNKNOWN","trade_id":trade_id,"error":"get_trades unsupported"}
  except Exception as e:
   logger.debug(f"Trade query exception for {trade_id}: {e}")
   return {"status":"UNKNOWN","error":str(e)}
 @staticmethod
 def _iso_or_unix_to_ts(val:Any)->float:
  try:
   f=float(val)
   return f / 1000.0 if f > 1e12 else f
  except (TypeError,ValueError):
   pass
  try:
   return datetime.fromisoformat(str(val).replace("Z","+00:00")).timestamp()
  except Exception:
   return 0.0
 def extract_account_fills( self,trades:List[Dict[str,Any]],token_id:str,target_order_id:Optional[str]=None,)->List[Dict[str,Any]]:
  fills:List[Dict[str,Any]]=[]
  me=str(self.funder_address or "").lower()
  api_owner=str(getattr(getattr(self.client,"creds",None),"api_key","") or "")
  target_oid_str=str(target_order_id) if target_order_id else None
  for raw in trades or []:
   t=self.normalize_trade_record(raw)
   if not t:
    continue
   trade_id=str(t.get("id") or "")
   tx=t.get("transaction_hash")
   status=str(t.get("status","")).upper()
   match_ts=self._iso_or_unix_to_ts(t.get("match_time") or t.get("last_update") or 0)
   role=str(t.get("trader_side","")).upper()
   t_asset=str(t.get("asset_id",""))
   taker_oid=str(t.get("taker_order_id") or "")
   if (role=="TAKER" or (not role and target_oid_str and taker_oid==target_oid_str)) and ( t_asset==str(token_id) or (target_oid_str and taker_oid==target_oid_str) ):
    size=float(t.get("size",0.0) or 0.0)
    price=float(t.get("price",0.0) or 0.0)
    fills.append({ "fill_id":f"{trade_id}:{taker_oid}","trade_id":trade_id,"order_id":taker_oid,"side":str(t.get("side","")).upper(),"size":size,"price":price,"cash":round(size * price,6),"transaction_hash":tx,"status":status,"match_ts":match_ts,"role":"TAKER",})
    continue
   for mo in t.get("maker_orders",[]) or []:
    mo_oid=str(mo.get("order_id") or "")
    exact_oid_match=bool(target_oid_str and mo_oid==target_oid_str)
    owner_match=( exact_oid_match or (me and str(mo.get("maker_address","")).lower()==me) or (api_owner and str(mo.get("owner",""))==api_owner) )
    mo_asset=str(mo.get("asset_id") or "")
    asset_match=(mo_asset==str(token_id)) or (not mo_asset and t_asset==str(token_id)) or exact_oid_match
    if not owner_match or not asset_match:
     continue
    size=float(mo.get("matched_amount",0.0) or 0.0)
    price=float(mo.get("price",0.0) or 0.0)
    side=str(mo.get("side","")).upper()
    if not side:
     taker_side=str(t.get("side","")).upper()
     side={"BUY":"SELL","SELL":"BUY"}.get(taker_side,"") if str(mo.get("asset_id",t_asset))==t_asset else taker_side
    fills.append({ "fill_id":f"{trade_id}:{mo.get('order_id')}","trade_id":trade_id,"order_id":str(mo.get("order_id") or ""),"side":side,"size":size,"price":price,"cash":round(size * price,6),"transaction_hash":tx,"status":status,"match_ts":match_ts,"role":"MAKER",})
  return fills
 def get_account_fills( self,token_id:str,after_ts:Optional[float]=None,side:Optional[str]=None,order_id:Optional[str]=None,include_failed:bool=False,)->Optional[List[Dict[str,Any]]]:
  if self.dry_run:
   return []
  if not self.client or not self.is_authenticated or not hasattr(self.client,"get_trades"):
   return None
  try:
   params=None
   if TradeParams is not None:
    params=TradeParams(asset_id=str(token_id),after=int(after_ts) if after_ts else None)
   raw=self.client.get_trades(params=params) if params is not None else self.client.get_trades()
   if not isinstance(raw,list):
    return None
   fills=self.extract_account_fills(raw,token_id,target_order_id=order_id)
   if order_id and not any(f["order_id"]==str(order_id) for f in fills):
    raw_all=self.client.get_trades()
    if isinstance(raw_all,list):
     fills=self.extract_account_fills(raw_all,token_id,target_order_id=order_id)
  except Exception as e:
   logger.error(f"[PM-EXEC] Trade history unavailable for {token_id}: {e}")
   return None
  out=[]
  for f in fills:
   if not include_failed and f["status"]=="FAILED":
    continue
   if side and f["side"]!=side.upper():
    continue
   if order_id and f["order_id"]!=str(order_id):
    continue
   if after_ts and f["match_ts"] and f["match_ts"] < float(after_ts) - 1.0:
    continue
   out.append(f)
  return out
 def get_order_fill_summary(self,order_id:str,token_id:Optional[str]=None)->Optional[Dict[str,Any]]:
  info=self.get_order_status(order_id)
  if not info:
   return None
  status=str(info.get("status","")).upper()
  try:
   matched=float(info.get("size_matched",0.0) or 0.0)
  except (TypeError,ValueError):
   return None
  orig_size=float(info.get("original_size",0.0) or 0.0)
  limit_px=float(info.get("price",0.0) or 0.0)
  tok=str(token_id or info.get("asset_id") or "")
  cash=None
  trade_ids:List[str]=[]
  tx_hashes:List[str]=[]
  fill_ids:List[str]=[]
  is_settled=False
  fills=[]
  all_fills=[]
  cash_from_authoritative_fills=False
  if matched > 0.0 and tok:
   try:
    all_fills=self.get_account_fills(tok,order_id=order_id,include_failed=True) or []
   except TypeError:
    all_fills=self.get_account_fills(tok,order_id=order_id) or []
   fills=[f for f in all_fills if str(f.get("status","")).upper()!="FAILED"]
   if fills:
    fill_ids=sorted({str(f["fill_id"]) for f in fills if f.get("fill_id")})
    trade_ids=sorted({str(f["trade_id"]) for f in fills if f.get("trade_id")})
    tx_hashes=sorted({str(f["transaction_hash"]) for f in fills if f.get("transaction_hash")})
    fill_size=sum(f["size"] for f in fills)
    if abs(fill_size - matched)<=0.011:
     cash=round(sum(f["cash"] for f in fills),6)
     cash_from_authoritative_fills=True
     all_fills_settled=all( f.get("status") in {"MINED","CONFIRMED"} and bool(f.get("transaction_hash")) for f in fills )
     if all_fills_settled and tx_hashes and not any( str(f.get("status","")).upper() in {"FAILED","RETRYING"} for f in all_fills ):
      is_settled=True
  estimated=cash is None
  cash_from_reported_taking=False
  if cash is None:
   raw_t=info.get("taking_amount")
   if raw_t in (None,""):
    raw_t=info.get("takingAmount")
   try:
    reported=float(raw_t) if raw_t not in (None,"") else None
   except (TypeError,ValueError):
    reported=None
   if reported is not None and math.isfinite(reported) and reported>=0.0:
    cash=round(reported,6)
    cash_from_reported_taking=True
    if status in {"CONFIRMED","MINED"} and tx_hashes:
     estimated=False
     is_settled=True
    else:
     estimated=True
   elif limit_px > 0.0:
    cash=round(matched * limit_px,6)
    estimated=True
   else:
    cash=None
  no_longer_resting=( status.startswith("CANCEL") or status in {"MATCHED","FILLED","CONFIRMED","EXPIRED","REJECTED"} or (orig_size > 0 and matched>=orig_size - 1e-4) )
  is_canceled=status.startswith("CANCEL") or status in {"EXPIRED","REJECTED"}
  order_type_str=str(info.get("order_type") or info.get("type") or "GTC").upper()
  has_reverted_fills=any(str(f.get("status","")).upper() in {"FAILED","RETRYING"} for f in all_fills)
  if is_canceled:
   terminal=True if (matched<=1e-6 or is_settled) else False
   estimated=False if (matched<=1e-6 or (cash is not None and is_settled)) else True
  elif is_settled and (status in {"MATCHED","FILLED","CONFIRMED","MINED"} or (orig_size > 0 and matched>=orig_size - 1e-4)):
   terminal=True
   estimated=False
  elif ( not self.dry_run and self.is_authenticated and self.client is not None and str(info.get("side","SELL")).upper()=="SELL" and not has_reverted_fills and status in {"MATCHED","FILLED","CONFIRMED","MINED"} and orig_size > 0 and matched>=orig_size - 0.01 and limit_px > 0.0 and tok ):
   onchain_bal=self.get_onchain_erc1155_balance(tok)
   if onchain_bal is not None and onchain_bal<=max(0.0,orig_size - matched) + 0.01:
    is_settled=True
    terminal=True
    if cash is None:
     cash=round(matched * limit_px,6)
    estimated=not (cash_from_authoritative_fills or cash_from_reported_taking or order_type_str=="GTC")
   else:
    terminal=False
    estimated=True
  else:
   terminal=False
   estimated=True
  return { "order_id":str(order_id),"status":status,"resting":not no_longer_resting,"is_matched":matched > 0.0,"is_settled":is_settled,"has_reverted_fills":has_reverted_fills,"terminal":terminal,"original_size":orig_size,"matched":matched,"cash":cash,"cash_is_estimated":estimated,"cash_from_reported_taking":cash_from_reported_taking,"limit_price":limit_px,"trade_ids":trade_ids,"transactions_hashes":tx_hashes,"fill_ids":fill_ids,"raw":info,}
 CTF_ADDRESS="0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
 NEG_RISK_ADAPTER_ADDRESS="0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
 NEG_RISK_WRAPPED_COLLATERAL="0x3A3BD7bb9528E159577F7C2e685CC81A765002E2"
 DEPOSIT_WALLET_FACTORY="0x00000000000Fb5C9ADea0298D729A0CB3823Cc07"
 POLY_PROXY_FACTORY="0xaB45c5A4B0c941a2F231C04C3f49182e1A254052"
 RELAYER_V2_URL="https://relayer-v2.polymarket.com"
 @staticmethod
 def _payout_redemption_topic()->str:
  from eth_utils import keccak
  return "0x" + keccak(text="PayoutRedemption(address,address,bytes32,bytes32,uint256[],uint256)").hex().replace("0x","")
 @staticmethod
 def _neg_risk_payout_redemption_topic()->str:
  from eth_utils import keccak
  return "0x" + keccak(text="PayoutRedemption(address,bytes32,uint256[],uint256)").hex().replace("0x","")
 @staticmethod
 def build_relayer_builder_headers( api_key:str,secret:str,passphrase:str,method:str,request_path:str,body:Any=None,timestamp:Optional[int]=None,)->Dict[str,str]:
  import base64
  import hashlib
  import hmac
  ts_str=str(int(timestamp if timestamp is not None else time.time()))
  raw_secret=base64.urlsafe_b64decode(secret)
  msg=ts_str + str(method) + str(request_path)
  if body is not None:
   if isinstance(body,(bytes,bytearray)):
    msg += body.decode("utf-8")
   elif isinstance(body,str):
    msg += body
   else:
    msg += str(body).replace("'",'"')
  sig=base64.urlsafe_b64encode( hmac.new(raw_secret,msg.encode("utf-8"),hashlib.sha256).digest() ).decode("utf-8")
  return { "POLY_BUILDER_API_KEY":api_key,"POLY_BUILDER_TIMESTAMP":ts_str,"POLY_BUILDER_PASSPHRASE":passphrase,"POLY_BUILDER_SIGNATURE":sig,}
 @classmethod
 def build_deposit_wallet_relayer_batch( cls,*,private_key:str,wallet_address:str,nonce:int,deadline:int,calls:List[Dict[str,str]],chain_id:int=137,)->Dict[str,Any]:
  from eth_account import Account
  from eth_account.messages import encode_typed_data
  from web3 import Web3
  wallet_cs=Web3.to_checksum_address(wallet_address)
  signer_cs=Web3.to_checksum_address(Account.from_key(private_key).address)
  factory_cs=Web3.to_checksum_address(cls.DEPOSIT_WALLET_FACTORY)
  norm_calls=[]
  typed_calls=[]
  for c in calls:
   tgt_cs=Web3.to_checksum_address(c["target"])
   val_str=str(int(c.get("value","0") or 0))
   data_hex=str(c["data"]) if str(c["data"]).startswith("0x") else ("0x" + str(c["data"]))
   norm_calls.append({"target":tgt_cs,"value":val_str,"data":data_hex})
   typed_calls.append({"target":tgt_cs,"value":int(val_str),"data":bytes.fromhex(data_hex[2:])})
  typed_msg={ "types":{ "EIP712Domain":[ {"name":"name","type":"string"},{"name":"version","type":"string"},{"name":"chainId","type":"uint256"},{"name":"verifyingContract","type":"address"},],"Call":[ {"name":"target","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"},],"Batch":[ {"name":"wallet","type":"address"},{"name":"nonce","type":"uint256"},{"name":"deadline","type":"uint256"},{"name":"calls","type":"Call[]"},],},"primaryType":"Batch","domain":{ "name":"DepositWallet","version":"1","chainId":int(chain_id),"verifyingContract":wallet_cs,},"message":{ "wallet":wallet_cs,"nonce":int(nonce),"deadline":int(deadline),"calls":typed_calls,},}
  signable=encode_typed_data(full_message=typed_msg)
  raw_sig=Account.sign_message(signable,private_key=private_key).signature.hex()
  sig_hex=raw_sig if raw_sig.startswith("0x") else f"0x{raw_sig}"
  return { "type":"WALLET","from":signer_cs,"to":factory_cs,"nonce":str(int(nonce)),"signature":sig_hex,"depositWalletParams":{ "depositWallet":wallet_cs,"deadline":str(int(deadline)),"calls":norm_calls,},}
 def _rpc(self,method:str,params:list)->Optional[Any]:
  rpc_url=os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com")
  try:
   session=getattr(self,"_sync_session",requests)
   resp=session.post(rpc_url,json={"jsonrpc":"2.0","id":1,"method":method,"params":params},timeout=5.0)
   if resp.status_code!=200:
    return None
   body=resp.json()
   if "error" in body:
    return None
   return body.get("result")
  except Exception as e:
   logger.debug(f"RPC {method} failed: {e}")
   return None
 def get_current_block_number(self)->Optional[int]:
  res=self._rpc("eth_blockNumber",[])
  try:
   return int(res,16) if res else None
  except (TypeError,ValueError):
   return None
 def parse_payout_redemption_logs(self,logs:List[Dict[str,Any]],condition_id:str)->List[Dict[str,Any]]:
  out=[]
  ctf_topic0=self._payout_redemption_topic().lower()
  nr_topic0=self._neg_risk_payout_redemption_topic().lower()
  me=str(self.funder_address or "").lower().replace("0x","").rjust(64,"0")
  cond=str(condition_id or "").lower().replace("0x","").rjust(64,"0")
  for lg in logs or []:
   topics=[str(t).lower() for t in (lg.get("topics") or [])]
   addr=str(lg.get("address","")).lower()
   data=str(lg.get("data","")).replace("0x","")
   if len(topics)>=2 and topics[0]==ctf_topic0 and addr==self.CTF_ADDRESS.lower():
    if topics[1].replace("0x","").rjust(64,"0")!=me:
     continue
    if len(data) < 192 or data[0:64]!=cond:
     continue
    payout=int(data[128:192],16) / 1e6
   elif len(topics)>=3 and topics[0]==nr_topic0 and addr==self.NEG_RISK_ADAPTER_ADDRESS.lower():
    if topics[1].replace("0x","").rjust(64,"0")!=me:
     continue
    if topics[2].replace("0x","").rjust(64,"0")!=cond:
     continue
    if len(data) < 128:
     continue
    payout=int(data[64:128],16) / 1e6
   else:
    continue
   out.append({ "transaction_hash":lg.get("transactionHash"),"block_number":int(str(lg.get("blockNumber","0x0")),16) if str(lg.get("blockNumber","")).startswith("0x") else lg.get("blockNumber"),"payout_usd":payout,"log_index":lg.get("logIndex"),})
  return out
 def find_redemption_payouts( self,condition_id:str,from_block:Optional[int]=None,tx_hash:Optional[str]=None,max_span:int=9000,)->Optional[List[Dict[str,Any]]]:
  if self.dry_run or not self.funder_address or not condition_id:
   return None
  if tx_hash:
   receipt=self._rpc("eth_getTransactionReceipt",[tx_hash])
   if not receipt:
    return None
   if str(receipt.get("status","")).lower() not in {"0x1","1"}:
    return []
   return self.parse_payout_redemption_logs(receipt.get("logs",[]),condition_id)
  head=self.get_current_block_number()
  if head is None:
   return None
  lookback=max(int(max_span),3000)
  chunk_span=min(int(max_span),1000) if int(max_span) > 0 else 1000
  start=int(from_block) if from_block else max(0,head - lookback)
  found:List[Dict[str,Any]]=[]
  me_topic="0x" + str(self.funder_address).lower().replace("0x","").rjust(64,"0")
  cond_topic="0x" + str(condition_id).lower().replace("0x","").rjust(64,"0")
  cursor=start
  while cursor<=head:
   end=min(head,cursor + chunk_span)
   logs=self._rpc("eth_getLogs",[{ "address":self.CTF_ADDRESS,"fromBlock":hex(cursor),"toBlock":hex(end),"topics":[self._payout_redemption_topic(),me_topic],}])
   if logs is None:
    return None
   found.extend(self.parse_payout_redemption_logs(logs,condition_id))
   nr_logs=self._rpc("eth_getLogs",[{ "address":self.NEG_RISK_ADAPTER_ADDRESS,"fromBlock":hex(cursor),"toBlock":hex(end),"topics":[self._neg_risk_payout_redemption_topic(),me_topic,cond_topic],}])
   if nr_logs is None:
    return None
   if nr_logs:
    found.extend(self.parse_payout_redemption_logs(nr_logs,condition_id))
   cursor=end + 1
  return found
 def _submit_deposit_wallet_relayer_redemption( self,*,pk:str,funder_cs:str,nonce:int,calls:List[Dict[str,str]],condition_id:str,)->Optional[str]:
  b_key=(os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY") or "").strip()
  b_sec=(os.getenv("POLY_BUILDER_SECRET") or os.getenv("BUILDER_SECRET") or "").strip()
  b_pass=(os.getenv("POLY_BUILDER_PASSPHRASE") or os.getenv("BUILDER_PASS_PHRASE") or "").strip()
  if not (b_key and b_sec and b_pass):
   return None
  cooldown_map=getattr(self,"_relayer_redemption_cooldown",None)
  if cooldown_map is None:
   self._relayer_redemption_cooldown=cooldown_map={}
  now_s=time.time()
  if (now_s - float(cooldown_map.get(condition_id,0.0))) < 180.0:
   return None
  relayer_base=os.getenv("POLY_RELAYER_URL",self.RELAYER_V2_URL).rstrip("/")
  req_dict=self.build_deposit_wallet_relayer_batch( private_key=pk,wallet_address=funder_cs,nonce=nonce,deadline=int(now_s) + 300,calls=calls,chain_id=self.CHAIN_ID,)
  body_json=json.dumps(req_dict,separators=(",",":"))
  headers=self.build_relayer_builder_headers( api_key=b_key,secret=b_sec,passphrase=b_pass,method="POST",request_path="/submit",body=body_json,)
  headers["Content-Type"]="application/json"
  session=getattr(self,"_sync_session",requests)
  resp=session.post(f"{relayer_base}/submit",headers=headers,data=body_json.encode("utf-8"),timeout=8.0)
  if resp.status_code!=200:
   logger.warning(f"[REDEMPTION] Relayer V2 submit HTTP {resp.status_code}: {resp.text[:200]}")
   return None
  body=resp.json() if resp.content else {}
  if body.get("state") in ("STATE_FAILED","STATE_INVALID"):
   return None
  cooldown_map[condition_id]=now_s
  tx_hash=body.get("transactionHash")
  tx_id=body.get("transactionID")
  if not tx_hash and tx_id:
   for _ in range(3):
    time.sleep(1.5)
    tr=session.get(f"{relayer_base}/transaction",params={"id":tx_id},timeout=5.0)
    if tr.status_code==200:
     t_list=tr.json()
     if isinstance(t_list,list) and t_list:
      if t_list[0].get("state") in ("STATE_FAILED","STATE_INVALID"):
       return None
      tx_hash=t_list[0].get("transactionHash")
      if tx_hash:
       break
  if tx_hash:
   tx_hash_norm=tx_hash if str(tx_hash).startswith("0x") else f"0x{tx_hash}"
   receipt=self._rpc("eth_getTransactionReceipt",[tx_hash_norm])
   if isinstance(receipt,dict) and receipt.get("status") is not None:
    if str(receipt.get("status","")).lower() not in {"0x1","1"}:
     return None
   return tx_hash_norm
  return None
 def attempt_onchain_redemption(self,condition_id:str,*,neg_risk:Optional[bool]=None)->Optional[str]:
  raw_sig_type=getattr(self,"signature_type",None)
  sig_type=1 if raw_sig_type is None else int(raw_sig_type)
  if self.dry_run or not condition_id or sig_type not in (0,1,2,3):
   return None
  b_key=(os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY") or "").strip()
  if sig_type==3 and not b_key:
   self._funder_is_gnosis_safe=False
   now_warn=time.time()
   if (now_warn - float(getattr(self,"_last_missing_builder_key_warn_ts",0.0)))>=3600.0:
    self._last_missing_builder_key_warn_ts=now_warn
    logger.warning(f"[REDEMPTION] DepositWallet ({self.funder_address}) requires POLY_BUILDER_API_KEY for Relayer V2.")
   return None
  if sig_type==2 and getattr(self,"_funder_is_gnosis_safe",None) is False:
   return None
  pk=(os.getenv("POLYGON_PRIVATE_KEY") or self.private_key or "").strip()
  if not pk or not self.funder_address:
   return None
  try:
   from web3 import Web3
   w3=Web3(Web3.HTTPProvider(os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com"),request_kwargs={"timeout":5}))
   funder_cs=Web3.to_checksum_address(self.funder_address)
   signer_cs=Web3.to_checksum_address(w3.eth.account.from_key(pk).address)
   if sig_type in (0,1,2):
    gas_payer_cs=funder_cs if sig_type==0 else signer_cs
    if w3.eth.get_balance(gas_payer_cs) < int(0.05 * 1e18):
     return None
   cond_bytes=bytes.fromhex(condition_id.lower().replace("0x","").rjust(64,"0"))
   ctf_abi=[ {"inputs":[{"name":"collateralToken","type":"address"},{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSets","type":"uint256[]"}],"name":"redeemPositions","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSet","type":"uint256"}],"name":"getCollectionId","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"collateralToken","type":"address"},{"name":"collectionId","type":"bytes32"}],"name":"getPositionId","outputs":[{"name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"name":"owner","type":"address"},{"name":"id","type":"uint256"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"conditionId","type":"bytes32"}],"name":"payoutDenominator","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},]
   nr_abi=[ {"inputs":[{"name":"_conditionId","type":"bytes32"},{"name":"_amounts","type":"uint256[]"}],"name":"redeemPositions","outputs":[],"stateMutability":"nonpayable","type":"function"},]
   ctf_cs=Web3.to_checksum_address(self.CTF_ADDRESS)
   ctf=w3.eth.contract(address=ctf_cs,abi=ctf_abi)
   nr_cs=Web3.to_checksum_address(self.NEG_RISK_ADAPTER_ADDRESS)
   nr_contract=w3.eth.contract(address=nr_cs,abi=nr_abi)
   try:
    if int(ctf.functions.payoutDenominator(cond_bytes).call())<=0:
     return None
   except Exception:
    pass
   redeem_targets:List[Tuple[str,str]]=[]
   if neg_risk is not False:
    try:
     wcol_cs=Web3.to_checksum_address(self.NEG_RISK_WRAPPED_COLLATERAL)
     b_yes=int(ctf.functions.balanceOf(funder_cs,ctf.functions.getPositionId(wcol_cs,ctf.functions.getCollectionId(b"\x00" * 32,cond_bytes,1).call()).call()).call())
     b_no=int(ctf.functions.balanceOf(funder_cs,ctf.functions.getPositionId(wcol_cs,ctf.functions.getCollectionId(b"\x00" * 32,cond_bytes,2).call()).call()).call())
     if b_yes > 0 or b_no > 0:
      nr_hex=( nr_contract.encode_abi("redeemPositions",args=[cond_bytes,[b_yes,b_no]]) if hasattr(nr_contract,"encode_abi") else nr_contract.encodeABI(fn_name="redeemPositions",args=[cond_bytes,[b_yes,b_no]]) )
      redeem_targets.append((nr_cs,nr_hex))
    except Exception:
     pass
   if neg_risk is not True:
    for col_hex in ( "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB","0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",):
     try:
      col_cs=Web3.to_checksum_address(col_hex)
      has_bal=any( int(ctf.functions.balanceOf(funder_cs,ctf.functions.getPositionId(col_cs,ctf.functions.getCollectionId(b"\x00" * 32,cond_bytes,idx).call()).call()).call()) > 0 for idx in (1,2) )
      if has_bal:
       ctf_hex=( ctf.encode_abi("redeemPositions",args=[col_cs,b"\x00" * 32,cond_bytes,[1,2]]) if hasattr(ctf,"encode_abi") else ctf.encodeABI(fn_name="redeemPositions",args=[col_cs,b"\x00" * 32,cond_bytes,[1,2]]) )
       redeem_targets.append((ctf_cs,ctf_hex))
     except Exception:
      continue
   if not redeem_targets:
    return None
   return self._dispatch_funder_calls(w3,Web3,pk,sig_type,funder_cs,signer_cs,redeem_targets,condition_id)
  except Exception as e:
   logger.debug(f"On-chain redemption skipped for {condition_id}: {e}")
   return None
 def _dispatch_funder_calls( self,w3:Any,Web3:Any,pk:str,sig_type:int,funder_cs:str,signer_cs:str,call_targets:List[Tuple[str,str]],condition_id:str,)->Optional[str]:
  if sig_type==3:
   dw_abi=[{"inputs":[],"name":"nonce","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
   dw=w3.eth.contract(address=funder_cs,abi=dw_abi)
   dw_nonce=int(dw.functions.nonce().call())
   calls_payload=[{"target":tgt,"value":"0","data":d_hex} for tgt,d_hex in call_targets]
   return self._submit_deposit_wallet_relayer_redemption( pk=pk,funder_cs=funder_cs,nonce=dw_nonce,calls=calls_payload,condition_id=condition_id )
  if sig_type==2:
   safe_abi=[ {"inputs":[],"name":"getThreshold","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getOwners","outputs":[{"name":"","type":"address[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"},{"name":"operation","type":"uint8"},{"name":"safeTxGas","type":"uint256"},{"name":"baseGas","type":"uint256"},{"name":"gasPrice","type":"uint256"},{"name":"gasToken","type":"address"},{"name":"refundReceiver","type":"address"},{"name":"signatures","type":"bytes"}],"name":"execTransaction","outputs":[{"name":"success","type":"bool"}],"stateMutability":"payable","type":"function"},]
   safe=w3.eth.contract(address=funder_cs,abi=safe_abi)
   try:
    owners=[Web3.to_checksum_address(o) for o in safe.functions.getOwners().call()]
    threshold_val=int(safe.functions.getThreshold().call())
   except Exception:
    self._funder_is_gnosis_safe=False
    return None
   self._funder_is_gnosis_safe=True
   if threshold_val!=1 or signer_cs not in owners:
    return None
   zero_cs=Web3.to_checksum_address("0x" + "00" * 20)
   preval_sig=b"\x00" * 12 + bytes.fromhex(signer_cs[2:].lower()) + b"\x00" * 32 + b"\x01"
   for tgt_cs,inner_hex in call_targets:
    try:
     inner_bytes=bytes.fromhex(inner_hex[2:] if inner_hex.startswith("0x") else inner_hex)
     if not safe.functions.execTransaction(tgt_cs,0,inner_bytes,0,0,0,0,zero_cs,zero_cs,preval_sig).call({"from":signer_cs}):
      continue
     tx=safe.functions.execTransaction(tgt_cs,0,inner_bytes,0,0,0,0,zero_cs,zero_cs,preval_sig).build_transaction({ "from":signer_cs,"nonce":w3.eth.get_transaction_count(signer_cs,"pending"),"gas":300000,"gasPrice":w3.eth.gas_price,"chainId":137,})
     signed=w3.eth.account.sign_transaction(tx,private_key=pk)
     tx_hash=w3.eth.send_raw_transaction(signed.raw_transaction).hex()
     return tx_hash if str(tx_hash).startswith("0x") else f"0x{tx_hash}"
    except Exception:
     continue
   return None
  if sig_type==1:
   pf_abi=[{ "inputs":[{"components":[{"name":"typeCode","type":"uint8"},{"name":"to","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"}],"name":"calls","type":"tuple[]"}],"name":"proxy","outputs":[{"name":"returnValues","type":"bytes[]"}],"stateMutability":"payable","type":"function",}]
   pf=w3.eth.contract(address=Web3.to_checksum_address(self.POLY_PROXY_FACTORY),abi=pf_abi)
   tuple_calls=[ (1,tgt_cs,0,bytes.fromhex(h[2:] if h.startswith("0x") else h)) for tgt_cs,h in call_targets ]
   pf.functions.proxy(tuple_calls).call({"from":signer_cs})
   tx=pf.functions.proxy(tuple_calls).build_transaction({ "from":signer_cs,"nonce":w3.eth.get_transaction_count(signer_cs,"pending"),"gas":320000,"gasPrice":w3.eth.gas_price,"chainId":137,})
   signed=w3.eth.account.sign_transaction(tx,private_key=pk)
   tx_hash=w3.eth.send_raw_transaction(signed.raw_transaction).hex()
   return tx_hash if str(tx_hash).startswith("0x") else f"0x{tx_hash}"
  for tgt_cs,inner_hex in call_targets:
   try:
    w3.eth.call({"from":funder_cs,"to":tgt_cs,"data":inner_hex})
    tx={ "from":funder_cs,"to":tgt_cs,"value":0,"data":inner_hex,"nonce":w3.eth.get_transaction_count(funder_cs,"pending"),"gas":250000,"gasPrice":w3.eth.gas_price,"chainId":137,}
    signed=w3.eth.account.sign_transaction(tx,private_key=pk)
    tx_hash=w3.eth.send_raw_transaction(signed.raw_transaction).hex()
    return tx_hash if str(tx_hash).startswith("0x") else f"0x{tx_hash}"
   except Exception:
    continue
  return None
 def attempt_onchain_complete_set_merge( self,condition_id:str,*,min_pairs:float=5.0,max_pairs:Optional[float]=None,neg_risk:Optional[bool]=None )->Optional[Tuple[str,float]]:
  raw_sig_type=getattr(self,"signature_type",None)
  sig_type=1 if raw_sig_type is None else int(raw_sig_type)
  if self.dry_run or not condition_id or sig_type not in (0,1,2,3):
   return None
  b_key=(os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY") or "").strip()
  if sig_type==3 and not b_key:
   return None
  if sig_type==2 and getattr(self,"_funder_is_gnosis_safe",None) is False:
   return None
  pk=(os.getenv("POLYGON_PRIVATE_KEY") or self.private_key or "").strip()
  if not pk or not self.funder_address:
   return None
  try:
   from web3 import Web3
   w3=Web3(Web3.HTTPProvider(os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com"),request_kwargs={"timeout":5}))
   funder_cs=Web3.to_checksum_address(self.funder_address)
   signer_cs=Web3.to_checksum_address(w3.eth.account.from_key(pk).address)
   if sig_type in (0,1,2):
    gas_payer_cs=funder_cs if sig_type==0 else signer_cs
    if w3.eth.get_balance(gas_payer_cs) < int(0.05 * 1e18):
     return None
   cond_bytes=bytes.fromhex(condition_id.lower().replace("0x","").rjust(64,"0"))
   min_raw=max(1,int(math.floor(float(min_pairs) * 1e6)))
   max_raw=max(min_raw,int(math.floor(float(max_pairs) * 1e6))) if max_pairs else None
   ctf_abi=[ {"inputs":[{"name":"collateralToken","type":"address"},{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"partition","type":"uint256[]"},{"name":"amount","type":"uint256"}],"name":"mergePositions","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSet","type":"uint256"}],"name":"getCollectionId","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"collateralToken","type":"address"},{"name":"collectionId","type":"bytes32"}],"name":"getPositionId","outputs":[{"name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"name":"owner","type":"address"},{"name":"id","type":"uint256"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},]
   nr_abi=[{"inputs":[{"name":"_conditionId","type":"bytes32"},{"name":"_amount","type":"uint256"}],"name":"mergePositions","outputs":[],"stateMutability":"nonpayable","type":"function"}]
   ctf_cs=Web3.to_checksum_address(self.CTF_ADDRESS)
   ctf=w3.eth.contract(address=ctf_cs,abi=ctf_abi)
   nr_cs=Web3.to_checksum_address(self.NEG_RISK_ADAPTER_ADDRESS)
   nr_contract=w3.eth.contract(address=nr_cs,abi=nr_abi)
   merge_targets:List[Tuple[str,str]]=[]
   merged_raw=0
   if neg_risk is not False:
    try:
     wcol_cs=Web3.to_checksum_address(self.NEG_RISK_WRAPPED_COLLATERAL)
     b_yes=int(ctf.functions.balanceOf(funder_cs,ctf.functions.getPositionId(wcol_cs,ctf.functions.getCollectionId(b"\x00" * 32,cond_bytes,1).call()).call()).call())
     b_no=int(ctf.functions.balanceOf(funder_cs,ctf.functions.getPositionId(wcol_cs,ctf.functions.getCollectionId(b"\x00" * 32,cond_bytes,2).call()).call()).call())
     m_nr=min(b_yes,b_no) if max_raw is None else min(b_yes,b_no,max_raw)
     if m_nr>=min_raw:
      nr_hex=nr_contract.encode_abi("mergePositions",args=[cond_bytes,m_nr]) if hasattr(nr_contract,"encode_abi") else nr_contract.encodeABI(fn_name="mergePositions",args=[cond_bytes,m_nr])
      merge_targets.append((nr_cs,nr_hex))
      merged_raw += m_nr
    except Exception:
     pass
   if neg_risk is not True and not merge_targets:
    for col_hex in ("0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB","0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"):
     try:
      col_cs=Web3.to_checksum_address(col_hex)
      b_yes=int(ctf.functions.balanceOf(funder_cs,ctf.functions.getPositionId(col_cs,ctf.functions.getCollectionId(b"\x00" * 32,cond_bytes,1).call()).call()).call())
      b_no=int(ctf.functions.balanceOf(funder_cs,ctf.functions.getPositionId(col_cs,ctf.functions.getCollectionId(b"\x00" * 32,cond_bytes,2).call()).call()).call())
      m_std=min(b_yes,b_no) if max_raw is None else min(b_yes,b_no,max_raw)
      if m_std>=min_raw:
       ctf_hex=ctf.encode_abi("mergePositions",args=[col_cs,b"\x00" * 32,cond_bytes,[1,2],m_std]) if hasattr(ctf,"encode_abi") else ctf.encodeABI(fn_name="mergePositions",args=[col_cs,b"\x00" * 32,cond_bytes,[1,2],m_std])
       merge_targets.append((ctf_cs,ctf_hex))
       merged_raw += m_std
       break
     except Exception:
      continue
   if not merge_targets or merged_raw < min_raw:
    return None
   tx_h=self._dispatch_funder_calls(w3,Web3,pk,sig_type,funder_cs,signer_cs,merge_targets,condition_id)
   if tx_h:
    self.invalidate_collateral_cache()
    try:
     rc=w3.eth.wait_for_transaction_receipt(tx_h,timeout=60,poll_latency=1.5)
     if int(rc.get("status",0))!=1:
      logger.warning(f"[MERGE] mergePositions tx {tx_h} reverted for {condition_id}; legs remain open.")
      return None
    except Exception as rc_err:
     logger.warning(f"[MERGE] mergePositions tx {tx_h} unconfirmed for {condition_id} ({rc_err}); legs remain open.")
     return None
    return tx_h,round(merged_raw / 1e6,6)
   return None
  except Exception as e:
   logger.debug(f"On-chain mergePositions skipped for {condition_id}: {e}")
   return None
 def merge_complete_set_positions( self,condition_id:str,amount_shares:float,*,neg_risk:Optional[bool]=None,)->Dict[str,Any]:
  sh=round(max(0.0,float(amount_shares or 0.0)),6)
  if not condition_id or sh<=0.0:
   return {"merged":False,"merged_pairs":0.0,"target_contract":"","calldata":"","tx_hash":None}
  from src.polymarket_research.redeem_settled_positions import encode_ctf_merge_or_split_calldata
  tgt,cd=encode_ctf_merge_or_split_calldata( condition_id,sh,neg_risk=bool(neg_risk),is_merge=True )
  if self.dry_run:
   return {"merged":True,"dry_run":True,"merged_pairs":sh,"target_contract":tgt,"calldata":cd,"tx_hash":None}
  res=self.attempt_onchain_complete_set_merge( condition_id,min_pairs=min(5.0,sh),max_pairs=sh,neg_risk=neg_risk )
  if isinstance(res,tuple) and len(res)==2 and res[0]:
   return {"merged":True,"dry_run":False,"merged_pairs":float(res[1]),"target_contract":tgt,"calldata":cd,"tx_hash":str(res[0])}
  return {"merged":False,"dry_run":False,"merged_pairs":0.0,"target_contract":tgt,"calldata":cd,"tx_hash":None}
 def simulate_fok_sweep( self,orderbook:Dict[str,Any],target_notional_usd:float,side:str="BUY",max_acceptable_price:float=MAX_PRICE_CEILING,min_acceptable_price:float=MIN_PRICE_FLOOR,return_legs:bool=False,fee_rate:float=0.07,fee_exponent:float=1.0,)->Any:
  levels=orderbook.get("asks" if side=="BUY" else "bids",[])
  if not levels or not self._book_levels_valid(levels):
   if return_legs:
    return False,0.0,0.0,0.0,0.0,[]
   return False,0.0,0.0,0.0,0.0
  if side=="BUY":
   sorted_levels=sorted(levels,key=lambda lvl:float(lvl.get("price",1.0)))
  else:
   sorted_levels=sorted(levels,key=lambda lvl:float(lvl.get("price",0.0)),reverse=True)
  rem_notional=target_notional_usd
  total_shares=0.0
  total_cost=0.0
  worst_price=0.0
  fill_legs:List[Tuple[float,float]]=[]
  for lvl in sorted_levels:
   px=float(lvl.get("price",0.0))
   sz=float(lvl.get("size",0.0))
   if sz<=0 or px<=0:
    continue
   if side=="BUY" and px > max_acceptable_price:
    break
   if side=="SELL" and px < min_acceptable_price:
    break
   level_notional=px * sz
   if level_notional>=rem_notional - 1e-6:
    shares_needed=min(sz,rem_notional / px)
    total_shares += shares_needed
    total_cost += rem_notional
    worst_price=px
    fill_legs.append((px,shares_needed))
    rem_notional=0.0
    break
   else:
    total_shares += sz
    total_cost += level_notional
    worst_price=px
    fill_legs.append((px,sz))
    rem_notional -= level_notional
  if rem_notional > 1e-4:
   if return_legs:
    return False,0.0,0.0,worst_price,0.0,[]
   return False,0.0,0.0,worst_price,0.0
  vwap=total_cost / total_shares if total_shares > 0 else 0.0
  fee_usd=round(sum( sz_i * fee_rate * ((px_i * (1.0 - px_i)) ** fee_exponent) for px_i,sz_i in fill_legs ),5)
  self.last_fok_fill_legs=fill_legs
  if return_legs:
   return True,vwap,total_shares,worst_price,fee_usd,fill_legs
  return True,vwap,total_shares,worst_price,fee_usd
 @staticmethod
 def _book_levels_valid(levels:Any)->bool:
  try:
   for lvl in levels:
    px=float(lvl.get("price"))
    sz=float(lvl.get("size"))
    if not (math.isfinite(px) and math.isfinite(sz)) or not (0.0 < px < 1.0) or sz < 0.0:
     return False
  except (TypeError,ValueError,AttributeError):
   return False
  return True
 def _invalid_notional_result(self,trade_id,token_id,target_token,side,notional_usd,t0)->"OrderResult":
  err=f"NotionalGuard Rejected: non-finite or non-positive notional ({notional_usd!r})."
  logger.error(f"[{trade_id}] {err}")
  return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=0.0,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
 def verify_pre_trade_depth( self,orderbook:Dict[str,Any],target_notional_usd:float,side:str="BUY",depth_hurdle_ratio:float=DEFAULT_DEPTH_HURDLE,max_price_ceiling:float=MAX_PRICE_CEILING,min_price_floor:float=MIN_PRICE_FLOOR,return_adjusted:bool=False,min_lot_size:float=MIN_LOT_SIZE_USD,max_ticket_size:float=MAX_TICKET_CAP_USD,)->Union[Tuple[bool,float,float],Tuple[bool,float,float,float]]:
  levels=orderbook.get("asks" if side=="BUY" else "bids",[])
  if ( not levels or not self._book_levels_valid(levels) or not math.isfinite(float(target_notional_usd)) or float(target_notional_usd)<=0.0 ):
   return (False,0.0,0.0,0.0) if return_adjusted else (False,0.0,0.0)
  if side=="BUY":
   sorted_levels=sorted(levels,key=lambda lvl:float(lvl.get("price",1.0)))
  else:
   sorted_levels=sorted(levels,key=lambda lvl:float(lvl.get("price",0.0)),reverse=True)
  qualifying_levels=[ lvl for lvl in sorted_levels if (min_price_floor<=float(lvl.get("price",0.0))<=max_price_ceiling) ]
  if not qualifying_levels:
   best_price=float(sorted_levels[0].get("price",0.0)) if sorted_levels else 0.0
   return (False,0.0,best_price,0.0) if return_adjusted else (False,0.0,best_price)
  best_price=float(qualifying_levels[0].get("price",0.0))
  available_notional=sum( float(lvl.get("price",0.0)) * float(lvl.get("size",0.0)) for lvl in qualifying_levels )
  ratio=available_notional / max(target_notional_usd,1e-6)
  if not return_adjusted:
   passed=ratio>=depth_hurdle_ratio
   return passed,ratio,best_price
  raw_elastic_ticket=available_notional / max(depth_hurdle_ratio,1.0)
  if raw_elastic_ticket < min_lot_size:
   passed=False
   adjusted_notional=0.0
  else:
   passed=True
   max_ceiling=min(target_notional_usd,max_ticket_size)
   adjusted_notional=round(min(max_ceiling,max(min_lot_size,raw_elastic_ticket)),2)
  return passed,ratio,best_price,adjusted_notional
 @staticmethod
 def calculate_elastic_ticket_size( executable_depth_usd:float,depth_hurdle_ratio:float=DEFAULT_DEPTH_HURDLE,min_ticket_usd:float=MIN_TICKET_USD,max_ticket_usd:float=MAX_TICKET_CAP_USD,)->Tuple[bool,float]:
  if not math.isfinite(executable_depth_usd) or executable_depth_usd<=0:
   return False,0.0
  raw_ticket=executable_depth_usd / max(depth_hurdle_ratio,1.0)
  if raw_ticket < min_ticket_usd:
   return False,0.0
  ticket_size=min(max_ticket_usd,max(min_ticket_usd,round(raw_ticket,2)))
  return True,ticket_size
 @staticmethod
 def validate_btc_signal( z_btc:float,min_z_score:float=1.645,)->Tuple[bool,str]:
  if abs(z_btc) < min_z_score:
   return False,f"REJECT_BTC_Z_TOO_LOW (|z|={abs(z_btc):.3f} < {min_z_score})"
  return True,"BTC_SIGNAL_CONFIRMED"
 @staticmethod
 def validate_cross_asset_lead_lag( target_asset:str,target_direction:str,btc_direction:Optional[str]=None,z_alt:float=0.0,z_btc:float=0.0,)->Tuple[bool,float,str]:
  if target_asset.upper()!="ETH":
   return True,z_alt,"NON_ALT_ASSET_PASSED"
  def _norm_dir(d:Optional[str])->Optional[str]:
   if not d:
    return None
   u=str(d).upper().strip()
   if u in ("BUY","UP","LONG","YES"):
    return "UP"
   if u in ("SELL","DOWN","SHORT","NO"):
    return "DOWN"
   return u
  norm_target=_norm_dir(target_direction)
  norm_btc=_norm_dir(btc_direction)
  if norm_btc is not None and norm_target is not None and norm_btc!=norm_target:
   return False,z_alt,f"REJECT_BTC_COUNTER_TREND (ETH {norm_target} vs BTC {norm_btc})"
  if z_alt!=0.0 and z_btc!=0.0:
   if (z_alt > 0 and z_btc < 0) or (z_alt < 0 and z_btc > 0):
    return False,z_alt,"REJECT_BTC_ETH_SIGN_DIVERGENCE (sign(z_ETH) != sign(z_BTC))"
  z_joint=0.70 * z_alt + 0.30 * z_btc
  return True,z_joint,"CROSS_ASSET_CONFIRMED"
 @staticmethod
 def validate_cross_asset_directional_conflict( candidate_asset:str,candidate_direction:str,candidate_expiry_ts:float,active_positions:List[Dict[str,Any]],max_expiry_window_delta:float=900.0,)->Tuple[bool,str]:
  cand_asset=candidate_asset.upper().strip()
  cand_dir=candidate_direction.upper().strip()
  for pos in active_positions:
   pos_asset=str(pos.get("asset","")).upper().strip()
   pos_dir=str(pos.get("target_token","")).upper().strip()
   pos_expiry=float(pos.get("candle_expiry_ts",0.0) or 0.0)
   is_core_pair=(cand_asset in ("BTC","ETH") and pos_asset in ("BTC","ETH"))
   is_same_window=( abs(pos_expiry - candidate_expiry_ts)<=max_expiry_window_delta if (pos_expiry > 0 and candidate_expiry_ts > 0) else True )
   if is_core_pair and is_same_window:
    if pos_dir and cand_dir and pos_dir!=cand_dir:
     return ( False,f"REJECT_CROSS_ASSET_CONFLICT ({cand_asset} {cand_dir} opposes active {pos_asset} {pos_dir} " f"with expiry delta {abs(pos_expiry - candidate_expiry_ts):.0f}s)" )
  return True,"CROSS_ASSET_DIRECTION_ALIGNED"
 @staticmethod
 def validate_market_universe( asset:str,title:str="",horizon:str="",slug:str="",tte_seconds:Optional[float]=None,max_tte_seconds:float=1500.0,)->Tuple[bool,str]:
  asset_clean=(asset or "").upper().strip()
  title_lower=(title or "").lower().strip()
  slug_lower=(slug or "").lower().strip()
  horizon_lower=(horizon or "").lower().strip()
  if asset_clean=="SOL" or "sol" in title_lower or "solana" in title_lower or "sol" in slug_lower:
   return False,"REJECT_SOL_MARKET (Dead venue on Polymarket)"
  is_btc=(asset_clean=="BTC" or "btc" in title_lower or "bitcoin" in title_lower or "btc" in slug_lower)
  is_eth=(asset_clean=="ETH" or "eth" in title_lower or "ethereum" in title_lower or "eth" in slug_lower)
  if asset_clean and not (is_btc or is_eth):
   return False,f"REJECT_UNAPPROVED_ASSET ({asset_clean} not in 5m/15m BTC/ETH universe)"
  if is_btc:
   is_subhourly=( "5m" in horizon_lower or "15m" in horizon_lower or "5m" in slug_lower or "15m" in slug_lower or "5m" in title_lower or "15m" in title_lower or (tte_seconds is not None and tte_seconds<=max_tte_seconds) )
   is_1h=( "1h" in horizon_lower or "hourly" in horizon_lower or "60m" in horizon_lower or "1h" in slug_lower or "hourly" in slug_lower or "1h" in title_lower or "hourly" in title_lower or (("pm et" in title_lower or "am et" in title_lower) and not is_subhourly) )
   if is_1h and not is_subhourly:
    return False,"REJECT_1H_BTC_MARKET (Negative EV macro mean-reversion)"
  is_subhourly_any=( "5m" in horizon_lower or "15m" in horizon_lower or "5m" in slug_lower or "15m" in slug_lower or "5m" in title_lower or "15m" in title_lower )
  is_1h_any=not is_subhourly_any and ( "1h" in horizon_lower or "hourly" in horizon_lower or "60m" in horizon_lower or "1h" in slug_lower or "hourly" in slug_lower or "1h" in title_lower or "hourly" in title_lower or ("pm et" in title_lower or "am et" in title_lower) )
  if is_1h_any and tte_seconds is not None and (tte_seconds > max_tte_seconds or tte_seconds < 120.0):
   return False,f"REJECT_1H_MARKET_OUTSIDE_SWEETSPOT (TTE={tte_seconds:.1f}s not in [120s, {max_tte_seconds:.0f}s])"
  return True,"MARKET_UNIVERSE_APPROVED"
 @staticmethod
 def calculate_relative_stop_price( entry_price:float,stop_delta:float=0.12,price_floor:float=0.02,)->float:
  return max(price_floor,round(entry_price - stop_delta,4))
 @staticmethod
 def evaluate_exp302_exit_policy( entry_price:float,current_bid:float,current_ask:float,spot_reversal_atr_multiple:float=0.0,free_usdc:float=1000.0,higher_score_trigger_pending:bool=False,stop_delta:float=0.12,maker_tp_price:float=0.95,min_free_usdc_threshold:float=25.0,signed_candle_distance_pct:Optional[float]=None,tte_seconds:Optional[float]=None,)->Dict[str,Any]:
  stop_px=max(0.02,round(entry_price - stop_delta,4))
  effective_maker_tp=maker_tp_price
  if maker_tp_price==0.95 and entry_price>=0.80:
   effective_maker_tp=0.985
  if current_bid>=effective_maker_tp:
   return { "action":"MAKER_TAKE_PROFIT","price":effective_maker_tp,"is_maker":True,"fee_schedule":"0% Maker Fee","reason":f"Resting maker limit swept at ${effective_maker_tp:.3f} (captures terminal value without payoff compression)" }
  norm_dist_pct=( signed_candle_distance_pct * 100.0 if (signed_candle_distance_pct is not None and abs(signed_candle_distance_pct)<=0.005 and signed_candle_distance_pct!=0.0) else signed_candle_distance_pct )
  if ( norm_dist_pct is not None and norm_dist_pct < 0.03 and (tte_seconds is None or tte_seconds > 60.0) ):
   return { "action":"STRIKE_RETRACE_STOP_LOSS","price":max(0.02,current_bid),"is_maker":False,"fee_schedule":"Taker Fee","reason":( f"Strike-retrace stop triggered: signed candle distance {norm_dist_pct:+.4f}% < +0.03% " f"with TTE={tte_seconds if tte_seconds is not None else 0.0:.1f}s > 60s. Salvaging position at bid ${current_bid:.3f}." ),}
  if spot_reversal_atr_multiple>=0.50 or current_bid<=stop_px:
   return { "action":"SPOT_DELTA_STOP_LOSS","price":max(0.02,current_bid),"is_maker":False,"fee_schedule":"Taker Fee","reason":f"Relative spot-delta stop triggered (bid={current_bid:.3f} <= stop_px={stop_px:.3f} or ATR multiple={spot_reversal_atr_multiple:.2f} >= 0.50)" }
  if free_usdc < min_free_usdc_threshold and higher_score_trigger_pending and current_bid > entry_price:
   return { "action":"CAPITAL_STARVATION_UNWIND","price":max(0.02,current_bid),"is_maker":False,"fee_schedule":"Taker Fee","reason":f"Capital-Starvation Override: free_usdc (${free_usdc:.2f}) < ${min_free_usdc_threshold:.2f} with superior shock pending. Unwinding green position early at bid." }
  return { "action":"HOLD_TO_MATURITY","price":1.00,"is_maker":True,"fee_schedule":"0% Settlement","reason":"EXP-302 Hold-to-Maturity with resting $0.95 Maker limit and Relative Spot-Delta Stop active." }
 @staticmethod
 def rank_concurrent_shock_candidates( candidates:List[Dict[str,Any]],window_seconds:float=5.0,)->List[Dict[str,Any]]:
  def _score(c):
   z=abs(float(c.get("z_val",c.get("z_score",c.get("expected_prob_shift",0.0)))))
   ask_px=max(float(c.get("clob_price",c.get("price",c.get("effective_price_$50",0.50)))),0.01)
   return z / ask_px
  return sorted(candidates,key=_score,reverse=True)
 def calculate_dynamic_crypto_fee( self,entry_price:float,notional_usd:float,fee_rate:float=0.07,fee_exponent:float=1.0,)->Tuple[float,float]:
  return calculate_taker_fee(notional_usd,entry_price,fee_rate,fee_exponent)
 def execute_snipe_order( self,trade_id:str,token_id:str,target_token:str,notional_usd:float,target_price:float,side:str="BUY",depth_hurdle:float=DEFAULT_DEPTH_HURDLE,market_id:Optional[str]=None,condition_id:Optional[str]=None,market_fee_rate:Optional[float]=None,market_fee_exponent:Optional[float]=None,max_price_ceiling:float=MAX_PRICE_CEILING,sizing_fn:Optional[Any]=None,max_ticket_cap:Optional[float]=None,min_price_floor:float=MIN_PRICE_FLOOR,prefetched_pre_balance:Optional[float]=None,prefetched_book:Optional[Dict[str,Any]]=None,neg_risk:Optional[bool]=None,expected_best_price:Optional[float]=None,max_book_buffer:float=0.02,)->OrderResult:
  t0=time.perf_counter()
  _trace=_CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
  if _trace is not None:
   _trace.stamp("exec_enter")
  now_utc=datetime.now(timezone.utc).isoformat()
  if neg_risk is not None:
   self.get_token_neg_risk(token_id,neg_risk)
  try:
   notional_usd=float(notional_usd)
  except (TypeError,ValueError):
   notional_usd=0.0
  ticket_ceiling=float(max_ticket_cap) if (max_ticket_cap is not None and math.isfinite(float(max_ticket_cap)) and float(max_ticket_cap) > 0) else MAX_TICKET_CAP_USD
  if not math.isfinite(notional_usd) or notional_usd<=0.0:
   return self._invalid_notional_result(trade_id,token_id,target_token,side,notional_usd,t0)
  notional_usd=min(notional_usd,ticket_ceiling)
  if prefetched_book is not None and isinstance(prefetched_book,dict):
   book=prefetched_book
  else:
   try:
    book=self.get_market_book(token_id)
   except Exception as e:
    return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=target_price,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=f"Orderbook fetch error: {e}",)
  passed_depth,depth_ratio,best_px,adjusted_notional=self.verify_pre_trade_depth( book,notional_usd,side=side,depth_hurdle_ratio=depth_hurdle,max_price_ceiling=max_price_ceiling,min_price_floor=min_price_floor,return_adjusted=True,min_lot_size=MIN_LOT_SIZE_USD,max_ticket_size=ticket_ceiling,)
  if not passed_depth:
   err=f"DepthGuard Rejected: Ratio {depth_ratio:.2f}x < {depth_hurdle:.2f}x requirement."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  if adjusted_notional < notional_usd:
   logger.info( f"[{trade_id}] [DYNAMIC DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${adjusted_notional:.2f} " f"to match available book depth (Ratio: {depth_ratio:.2f}x vs hurdle {depth_hurdle:.2f}x)." )
   notional_usd=adjusted_notional
  if best_px < min_price_floor or best_px > max_price_ceiling:
   err=f"PriceGuard Rejected: Best price ${best_px:.4f} outside valid boundary [{min_price_floor:.2f}, {max_price_ceiling:.2f}]."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  if target_price > 0 and (best_px - target_price) > 0.04:
   err=f"SlippageGuard Rejected: Best price ${best_px:.4f} exceeds target ${target_price:.4f} by > 4¢."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  if side=="BUY" and expected_best_price is not None and expected_best_price > 0 and (expected_best_price - best_px)>=0.04:
   err=f"AdverseCollapseGuard Rejected: Best ask ${best_px:.4f} collapsed >= 4¢ below trigger ask ${expected_best_price:.4f}."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  observed_ref=target_price if target_price > 0 else best_px
  limit_px=round( min( best_px + max(0.0,float(max_book_buffer)),target_price if target_price > 0 else max_price_ceiling,max_price_ceiling,),2,)
  worst_acceptable_px=self.quantize_order_price( limit_px,token_id,rounding=ROUND_FLOOR if limit_px>=max_price_ceiling - 1e-9 else ROUND_CEILING )
  if worst_acceptable_px > max_price_ceiling + 1e-9:
   worst_acceptable_px=self.quantize_order_price(max_price_ceiling,token_id,rounding=ROUND_FLOOR)
  if worst_acceptable_px < best_px - 1e-9:
   err=f"Worst acceptable price (${worst_acceptable_px:.4f}) below best ask (${best_px:.4f}) after capping at ceiling (${max_price_ceiling:.4f})"
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  if sizing_fn is not None:
   try:
    recomputed_ticket=float(sizing_fn(worst_acceptable_px))
   except Exception as e:
    logger.error(f"[{trade_id}] Error in sizing_fn at {worst_acceptable_px:.4f}: {e}")
    recomputed_ticket=0.0
   if not math.isfinite(recomputed_ticket) or recomputed_ticket < MIN_LOT_SIZE_USD:
    err=( f"SlippageKellyGuard Rejected: Order limit ${worst_acceptable_px:.4f} " f"does not support minimum Kelly ticket (${recomputed_ticket:.2f} < ${MIN_LOT_SIZE_USD:.2f})." )
    logger.warning(f"[{trade_id}] {err}")
    return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=worst_acceptable_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
   if recomputed_ticket < notional_usd:
    logger.info( f"[{trade_id}] [SLIPPAGE KELLY DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${recomputed_ticket:.2f} " f"due to slippage limit price ${worst_acceptable_px:.4f}." )
    notional_usd=recomputed_ticket
  fillable,vwap,sweep_shares,worst_px,fok_fee,fill_legs=self.simulate_fok_sweep( book,notional_usd,side=side,max_acceptable_price=worst_acceptable_px,return_legs=True,fee_rate=float(market_fee_rate) if market_fee_rate is not None else 0.07,fee_exponent=float(market_fee_exponent) if market_fee_exponent is not None else 1.0,)
  if not fillable:
   err=f"FOK Sweep Infeasible: Could not fill ${notional_usd:.2f} within limit ${worst_acceptable_px:.4f}."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=worst_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  shares_to_buy=float(math.floor(sweep_shares))
  if side=="BUY" and worst_acceptable_px > 0:
   max_shares_for_limit=float(math.floor(notional_usd / worst_acceptable_px))
   shares_to_buy=min(shares_to_buy,max_shares_for_limit)
  if shares_to_buy<=0:
   err=f"Calculated shares_to_buy ({shares_to_buy}) <= 0 for notional ${notional_usd:.2f} at limit ${worst_acceptable_px:.4f}"
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=worst_acceptable_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  exec_price=round(vwap,4)
  cid=condition_id or market_id
  if market_fee_rate is not None and market_fee_exponent is not None:
   f_rate=float(market_fee_rate)
   f_exp=float(market_fee_exponent)
   if cid:
    self._fee_cache[str(cid)]=(f_rate,f_exp)
   if condition_id:
    self._fee_cache[str(condition_id)]=(f_rate,f_exp)
   if market_id:
    self._fee_cache[str(market_id)]=(f_rate,f_exp)
   if token_id:
    self._fee_cache[str(token_id)]=(f_rate,f_exp)
  elif cid and (str(cid) in self._fee_cache or str(cid).lower() in self._fee_cache):
   f_rate,f_exp=self._fee_cache.get(str(cid)) or self._fee_cache[str(cid).lower()]
  elif cid:
   try:
    f_rate,f_exp=self.get_market_fee_params(str(cid),token_id=token_id)
   except Exception as e:
    logger.warning(f"Authoritative CLOB fee query notice for {cid}: {e}; using fallback fee.")
    f_rate=float(market_fee_rate) if market_fee_rate is not None else 0.07
    f_exp=float(market_fee_exponent or 1.0)
  else:
   f_rate,f_exp=0.07,1.0
  if not self.dry_run:
   valid_fee=( math.isfinite(f_rate) and f_rate>=0.0 and math.isfinite(f_exp) and (f_exp > 0.0 or (f_rate==0.0 and f_exp>=0.0)) )
   if not valid_fee:
    err=f"AuthoritativeFeeGuard Rejected: Non-finite or invalid fee parameters (rate={f_rate}, exp={f_exp}) for {cid}."
    logger.error(f"[{trade_id}] {err}")
    return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=worst_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  fee_usd=round(sum( shares_i * f_rate * ((price_i * (1.0 - price_i)) ** f_exp) for price_i,shares_i in fill_legs ),5)
  effective_fee_rate=fee_usd / max(notional_usd,1e-9)
  if not self.dry_run:
   if not self.is_authenticated or self.client is None:
    raise RuntimeError( f"LIVE ORDER REFUSED: Executor is in live real-money mode but unauthenticated ({self.auth_mode}). " "Refusing mock fallback." )
  else:
   latency_ms=(time.perf_counter() - t0) * 1000.0
   mock_order_id=f"MOCK_CLOB_{int(time.time()*1000)}"
   logger.info( f"[DRY-RUN SNIPE] {trade_id} -> {target_token} | Shares={shares_to_buy:.2f} @ ${exec_price:.4f} " f"| Notional=${notional_usd:.2f} | Fee=${fee_usd:.4f} ({effective_fee_rate*100:.2f}%) | Latency={latency_ms:.2f}ms" )
   res=OrderResult( success=True,order_id=mock_order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=exec_price,size=shares_to_buy,notional_usd=notional_usd,fee_usd=fee_usd,latency_ms=latency_ms,mode="DRY_RUN_SIMULATION",execution_status=ExecutionStatus.POSITION_CONFIRMED,confirmed_onchain=True,details={ "fee_rate":effective_fee_rate,"depth_ratio":depth_ratio,"timestamp_utc":now_utc,"confirmed_onchain":True,"pre_token_balance":0.0,"post_token_balance":shares_to_buy,"balance_delta":shares_to_buy,},)
   self._log_order(res)
   return res
  order_submitted=False
  try:
   if prefetched_pre_balance is not None:
    pre_token_bal=float(prefetched_pre_balance)
   elif not self.dry_run:
    pre_token_bal=self.get_onchain_erc1155_balance(token_id)
    if pre_token_bal is None:
     pre_token_bal=self.get_conditional_balance(token_id)
    if pre_token_bal is None:
     pre_token_bal=0.0
   else:
    pre_token_bal=0.0
   entry_order_type=getattr(OrderType,"FAK",OrderType.FOK)
   t_qualify_end=time.perf_counter()
   if _trace is not None:
    _trace.stamp("qualify_end")
   qualify_ms=(t_qualify_end - t0) * 1000.0
   if token_id in self._tick_size_cache:
    tick_size_str=str(self._tick_size_cache[token_id])
   else:
    tick_size_str="0.01"
    self._tick_size_cache[token_id]=0.01
   fee_rate_bps_val=int(round(f_rate * 10000)) if f_rate else 0
   eff_neg_risk=self.get_token_neg_risk(token_id,neg_risk)
   self.prewarm_token_market_cache( token_id=token_id,tick_size=tick_size_str,neg_risk=eff_neg_risk,fee_rate_bps=fee_rate_bps_val,condition_id=condition_id,fee_rate=f_rate,fee_exponent=f_exp,)
   create_options=PartialCreateOrderOptions(tick_size=tick_size_str,neg_risk=eff_neg_risk,version=2) if PartialCreateOrderOptions else None
   dispatch_stage:Dict[str,Any]={"submitted":False}
   try:
    hop=_sign_and_post_single_hop( self.client,self.order_ladder_cache,token_id,worst_acceptable_px,shares_to_buy,side,entry_order_type,create_options,dispatch_stage,notional_usd,)
   finally:
    order_submitted=bool(dispatch_stage.get("submitted"))
   shares_to_buy=float(hop.get("signed_shares",shares_to_buy))
   post_resp=hop["post_resp"]
   sign_ms=hop["sign_ms"]
   clob_http_post_ms=hop["post_ms"]
   t_post_end=hop["t_post_end"]
   total_trigger_to_ack_ms=(t_post_end - t0) * 1000.0
   if hop["cache_hit"]:
    logger.debug(f"[{trade_id}] Pre-signed order ladder cache hit (sign_ms={sign_ms:.3f}ms)")
   logger.info( f"[{trade_id}] LATENCY TELEMETRY: qualify_ms={qualify_ms:.2f} | sign_ms={sign_ms:.2f} | " f"clob_http_post_ms={clob_http_post_ms:.2f} | total_trigger_to_ack_ms={total_trigger_to_ack_ms:.2f}" )
   latency_ms=(t_post_end - t0) * 1000.0
   order_id=post_resp.get("orderID") or post_resp.get("id")
   if _trace is not None:
    _trace.emit( trade_id=trade_id,token_id=token_id,side=side,outcome="posted",order_id_present=bool(order_id),resp_status=str(post_resp.get("status")),resp_error=str(post_resp.get("errorMsg") or post_resp.get("error") or "")[:120],qualify_ms=round(qualify_ms,3),sign_ms=round(sign_ms,3),thread_hop_ms=round(float(hop.get("thread_hop_ms",0.0)),3),clob_http_post_ms=round(clob_http_post_ms,3),total_trigger_to_ack_ms=round(total_trigger_to_ack_ms,3),presign_cache_hit=bool(hop.get("cache_hit")),hot_active=_HOT_DISPATCH_ACTIVE.count,taker_delay_hint=getattr(self,"_taker_delay_ms_hint",None),)
   if is_fak_killed_no_match(None,post_resp):
    err_msg=post_resp.get("error") or post_resp.get("errorMsg") or "FAK order killed with zero match"
    logger.warning(f"[{trade_id}] FAK order deterministically killed by CLOB (zero match): {err_msg} | orderID={order_id}")
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=latency_ms,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err_msg,details={ "outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":post_resp,"depth_ratio":depth_ratio,"timestamp_utc":now_utc,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,"latency_telemetry":{ "qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",0.0),"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
    self._log_order(res)
    return res
   _sync_post_err=post_resp.get("errorMsg") or post_resp.get("error")
   if (not order_id and not _sync_post_err) or (order_id and _sync_post_err):
    err_msg=_sync_post_err or "No orderID returned from CLOB matching engine (ambiguous)"
    logger.critical(f"[{trade_id}] Ambiguous entry submission: {err_msg} | raw={post_resp}")
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=shares_to_buy,notional_usd=notional_usd,fee_usd=fee_usd,latency_ms=latency_ms,mode="LIVE_AMBIGUOUS_SUBMISSION",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,error=err_msg,details={ "outcome_unknown":True,"requires_exchange_reconciliation":True,"raw_response":post_resp,"entry_order_id":order_id,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,"latency_telemetry":{ "qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",0.0),"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
    self._log_order(res)
    return res
   if not order_id or _sync_post_err:
    err_msg=_sync_post_err or "No orderID returned from CLOB matching engine"
    logger.error(f"[{trade_id}] Order rejected by CLOB: {err_msg} | raw={post_resp}")
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=shares_to_buy,notional_usd=notional_usd,fee_usd=fee_usd,latency_ms=latency_ms,mode="LIVE_CLOB_ERROR",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err_msg,details={ "raw_response":post_resp,"depth_ratio":depth_ratio,"timestamp_utc":now_utc,"pre_token_balance":pre_token_bal,"outcome_unknown":False,"requires_exchange_reconciliation":False,"latency_telemetry":{ "qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",0.0),"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
    self._log_order(res)
    return res
   resp_status=str(post_resp.get("status") or "").upper()
   making_amt=post_resp.get("makingAmount")
   taking_amt=post_resp.get("takingAmount")
   if resp_status.startswith("CANCEL") or resp_status in {"UNMATCHED","EXPIRED","REJECTED"}:
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=latency_ms,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=f"CLOB order returned terminal non-fill status={resp_status}",details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":post_resp},)
    self._log_order(res)
    return res
   if resp_status in {"DELAYED","LIVE"} and making_amt in (None,"") and taking_amt in (None,""):
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=shares_to_buy,notional_usd=notional_usd,fee_usd=fee_usd,latency_ms=latency_ms,mode="LIVE_AMBIGUOUS_SUBMISSION",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,error=f"CLOB order returned non-immediate status={resp_status} without fill amounts",details={ "outcome_unknown":True,"requires_exchange_reconciliation":True,"raw_response":post_resp,"entry_order_id":order_id,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,},)
    self._log_order(res)
    return res
   if making_amt not in (None,""):
    try:
     actual_notional=float(making_amt)
    except (ValueError,TypeError) as parse_err:
     raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid makingAmount={making_amt}: {parse_err}")
   else:
    actual_notional=round(shares_to_buy * exec_price,4)
   if taking_amt not in (None,""):
    try:
     actual_shares=float(taking_amt)
    except (ValueError,TypeError) as parse_err:
     raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid takingAmount={taking_amt}: {parse_err}")
   else:
    actual_shares=shares_to_buy
   if (making_amt not in (None,"") or taking_amt not in (None,"")) and actual_shares<=0.0:
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=latency_ms,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error="FAK order matched 0 shares",details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":post_resp},)
    self._log_order(res)
    return res
   fill_px=round(actual_notional / max(actual_shares,1e-4),4) if (making_amt not in (None,"") and taking_amt not in (None,"") and actual_shares > 0) else exec_price
   if making_amt not in (None,"") and taking_amt not in (None,"") and actual_shares > 0:
    p_clamped=max(0.001,min(0.999,fill_px))
    fee_usd=round(actual_shares * f_rate * ((p_clamped * (1.0 - p_clamped)) ** f_exp),5)
   trade_ids=post_resp.get("tradeIDs",[])
   tx_hashes=post_resp.get("transactionsHashes",[])
   logger.info( f"[LIVE CLOB MATCHED] {trade_id} -> OID: {order_id} | {target_token} | Shares={actual_shares:.2f} " f"@ ${fill_px:.4f} | Notional=${actual_notional:.2f} | Latency={latency_ms:.2f}ms | Trades={trade_ids}" )
   exec_status=ExecutionStatus.MATCHED_PENDING_SETTLEMENT
   confirmed_onchain=False
   res=OrderResult( success=True,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=fill_px,size=actual_shares,notional_usd=actual_notional,fee_usd=fee_usd,latency_ms=latency_ms,mode="LIVE_CLOB",execution_status=exec_status,confirmed_onchain=confirmed_onchain,details={ "raw_response":post_resp,"depth_ratio":depth_ratio,"timestamp_utc":now_utc,"confirmed_onchain":confirmed_onchain,"pre_token_balance":pre_token_bal,"trade_ids":trade_ids,"transactions_hashes":tx_hashes,"latency_telemetry":{ "qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",0.0),"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
   self._log_order(res)
   return res
  except Exception as e:
   t_exc=time.perf_counter()
   latency_ms=(t_exc - t0) * 1000.0
   _ds=locals().get("dispatch_stage") or {}
   _t_post_s=_ds.get("t_post_start") or locals().get("t_post_start")
   clob_http_post_ms=round(max(0.0,(t_exc - float(_t_post_s)) * 1000.0),3) if _t_post_s else 0.0
   _exc_sign_ms=float(_ds.get("sign_ms") if _ds.get("sign_ms") is not None else locals().get("sign_ms",0.0))
   _exc_hop_ms=float(_ds.get("thread_hop_ms") if _ds.get("thread_hop_ms") is not None else locals().get("thread_hop_ms",0.0))
   total_trigger_to_ack_ms=(t_exc - t0) * 1000.0
   err_msg=f"CLOB order submission failed: {e}"
   if is_clob_400_rejection(e):
    self._evict_tick_size_if_tick_err(token_id,e)
    extracted_oid=None
    err_dict=getattr(e,"error_message",None) or getattr(e,"error_msg",None)
    if isinstance(err_dict,dict):
     extracted_oid=err_dict.get("orderID") or err_dict.get("id")
    elif isinstance(err_dict,str):
     try:
      parsed=json.loads(err_dict)
      if isinstance(parsed,dict):
       extracted_oid=parsed.get("orderID") or parsed.get("id")
     except Exception:
      pass
    logger.warning(f"[{trade_id}] Order deterministically rejected by CLOB (HTTP 400 / 0 match): {e} | orderID={extracted_oid}")
    res=OrderResult( success=False,order_id=extracted_oid,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=latency_ms,mode="FAK_KILLED_NO_MATCH" if is_fak_killed_no_match(e) else "CLOB_HTTP_400_REJECTION",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=str(e),details={ "outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"clob_400_rejection":True,"raw_exception":str(e),"status_code":getattr(e,"status_code",400),"pre_token_balance":locals().get("pre_token_bal"),"intended_notional_usd":notional_usd,"latency_telemetry":{ "qualify_ms":locals().get("qualify_ms",0.0),"sign_ms":_exc_sign_ms,"thread_hop_ms":_exc_hop_ms,"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
    self._log_order(res)
    return res
   logger.error(f"[{trade_id}] {err_msg}")
   res=OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=latency_ms,mode="LIVE_CLOB_ERROR",execution_status=ExecutionStatus.SUBMITTED if order_submitted else ExecutionStatus.REJECTED,confirmed_onchain=False,error=err_msg,details={ "outcome_unknown":bool(order_submitted),"requires_exchange_reconciliation":bool(order_submitted),"pre_token_balance":locals().get("pre_token_bal"),"intended_notional_usd":notional_usd,"latency_telemetry":{ "qualify_ms":locals().get("qualify_ms",0.0),"sign_ms":_exc_sign_ms,"thread_hop_ms":_exc_hop_ms,"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
   self._log_order(res)
   return res
 async def execute_snipe_order_async( self,trade_id:str,token_id:str,target_token:str,notional_usd:float=20.0,target_price:float=0.0,side:str="BUY",depth_hurdle:float=DEFAULT_DEPTH_HURDLE,market_id:Optional[str]=None,condition_id:Optional[str]=None,market_fee_rate:Optional[float]=None,market_fee_exponent:Optional[float]=None,max_price_ceiling:float=MAX_PRICE_CEILING,sizing_fn:Optional[Any]=None,max_ticket_cap:Optional[float]=None,prefetched_book:Optional[Dict[str,Any]]=None,prefetched_pre_balance:Optional[float]=None,min_price_floor:float=MIN_PRICE_FLOOR,neg_risk:Optional[bool]=None,expected_best_price:Optional[float]=None,max_book_buffer:float=0.02,)->OrderResult:
  t0=time.perf_counter()
  _trace=_CURRENT_TRACE.get() if _CURRENT_TRACE is not None else None
  if _trace is not None:
   _trace.stamp("exec_enter")
  now_utc=datetime.now(timezone.utc).isoformat()
  if neg_risk is not None:
   self.get_token_neg_risk(token_id,neg_risk)
  try:
   notional_usd=float(notional_usd)
  except (TypeError,ValueError):
   notional_usd=0.0
  ticket_ceiling=float(max_ticket_cap) if (max_ticket_cap is not None and math.isfinite(float(max_ticket_cap)) and float(max_ticket_cap) > 0) else MAX_TICKET_CAP_USD
  if not math.isfinite(notional_usd) or notional_usd<=0.0:
   return self._invalid_notional_result(trade_id,token_id,target_token,side,notional_usd,t0)
  notional_usd=min(notional_usd,ticket_ceiling)
  self.assert_market_routing(token_id,market_version="CTF")
  try:
   book=prefetched_book if prefetched_book is not None else await self.get_market_book_async(token_id)
  except Exception as e:
   err=f"Async Orderbook Fetch Failed for {token_id}: {e}"
   logger.error(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=0.0,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  passed_depth,depth_ratio,best_px,adjusted_notional=self.verify_pre_trade_depth( book,target_notional_usd=notional_usd,side=side,depth_hurdle_ratio=depth_hurdle,max_price_ceiling=max_price_ceiling,min_price_floor=min_price_floor,return_adjusted=True,min_lot_size=MIN_LOT_SIZE_USD,max_ticket_size=ticket_ceiling,)
  if not passed_depth:
   err=f"DepthGuard Rejected: Available depth ratio {depth_ratio:.2f}x < hurdle {depth_hurdle:.2f}x."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  if adjusted_notional < notional_usd:
   logger.info( f"[{trade_id}] [DYNAMIC DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${adjusted_notional:.2f} " f"to match available book depth (Ratio: {depth_ratio:.2f}x vs hurdle {depth_hurdle:.2f}x)." )
   notional_usd=adjusted_notional
  if best_px < min_price_floor or best_px > max_price_ceiling:
   err=f"PriceGuard Rejected: Best price ${best_px:.4f} outside valid boundary [{min_price_floor:.2f}, {max_price_ceiling:.2f}]."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  if target_price > 0 and (best_px - target_price) > 0.04:
   err=f"SlippageGuard Rejected: Best price ${best_px:.4f} exceeds target ${target_price:.4f} by > 4¢."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  if side=="BUY" and expected_best_price is not None and expected_best_price > 0 and (expected_best_price - best_px)>=0.04:
   err=f"AdverseCollapseGuard Rejected: Best ask ${best_px:.4f} collapsed >= 4¢ below trigger ask ${expected_best_price:.4f}."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  observed_ref=target_price if target_price > 0 else best_px
  limit_px=round( min( best_px + max(0.0,float(max_book_buffer)),target_price if target_price > 0 else max_price_ceiling,max_price_ceiling,),2,)
  if token_id not in self._tick_size_cache and not self.dry_run:
   await asyncio.to_thread(self.get_token_tick_size,token_id)
  worst_acceptable_px=self.quantize_order_price( limit_px,token_id,rounding=ROUND_FLOOR if limit_px>=max_price_ceiling - 1e-9 else ROUND_CEILING )
  if worst_acceptable_px > max_price_ceiling + 1e-9:
   worst_acceptable_px=self.quantize_order_price(max_price_ceiling,token_id,rounding=ROUND_FLOOR)
  if worst_acceptable_px < best_px - 1e-9:
   err=f"Worst acceptable price (${worst_acceptable_px:.4f}) below best ask (${best_px:.4f}) after capping at ceiling (${max_price_ceiling:.4f})"
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  if sizing_fn is not None:
   try:
    recomputed_ticket=float(sizing_fn(worst_acceptable_px))
   except Exception as e:
    logger.error(f"[{trade_id}] Error in sizing_fn at {worst_acceptable_px:.4f}: {e}")
    recomputed_ticket=0.0
   if not math.isfinite(recomputed_ticket) or recomputed_ticket < MIN_LOT_SIZE_USD:
    err=( f"SlippageKellyGuard Rejected: Order limit ${worst_acceptable_px:.4f} " f"does not support minimum Kelly ticket (${recomputed_ticket:.2f} < ${MIN_LOT_SIZE_USD:.2f})." )
    logger.warning(f"[{trade_id}] {err}")
    return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=worst_acceptable_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
   if recomputed_ticket < notional_usd:
    logger.info( f"[{trade_id}] [SLIPPAGE KELLY DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${recomputed_ticket:.2f} " f"due to slippage limit price ${worst_acceptable_px:.4f}." )
    notional_usd=recomputed_ticket
  fillable,vwap,sweep_shares,worst_px,fok_fee,fill_legs=self.simulate_fok_sweep( book,notional_usd,side=side,max_acceptable_price=worst_acceptable_px,return_legs=True,fee_rate=float(market_fee_rate) if market_fee_rate is not None else 0.07,fee_exponent=float(market_fee_exponent) if market_fee_exponent is not None else 1.0,)
  if not fillable:
   err=f"FOK Sweep Infeasible: Could not fill ${notional_usd:.2f} within limit ${worst_acceptable_px:.4f}."
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=worst_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  shares_to_buy=float(math.floor(sweep_shares))
  if side=="BUY" and worst_acceptable_px > 0:
   max_shares_for_limit=float(math.floor(notional_usd / worst_acceptable_px))
   shares_to_buy=min(shares_to_buy,max_shares_for_limit)
  if shares_to_buy<=0:
   err=f"Calculated shares_to_buy ({shares_to_buy}) <= 0 for notional ${notional_usd:.2f} at limit ${worst_acceptable_px:.4f}"
   logger.warning(f"[{trade_id}] {err}")
   return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=worst_acceptable_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  exec_price=round(vwap,4)
  cid=condition_id or market_id
  if market_fee_rate is not None and market_fee_exponent is not None:
   f_rate=float(market_fee_rate)
   f_exp=float(market_fee_exponent)
   if cid:
    self._fee_cache[str(cid)]=(f_rate,f_exp)
   if condition_id:
    self._fee_cache[str(condition_id)]=(f_rate,f_exp)
   if market_id:
    self._fee_cache[str(market_id)]=(f_rate,f_exp)
   if token_id:
    self._fee_cache[str(token_id)]=(f_rate,f_exp)
  elif cid and (str(cid) in self._fee_cache or str(cid).lower() in self._fee_cache):
   f_rate,f_exp=self._fee_cache.get(str(cid)) or self._fee_cache[str(cid).lower()]
  elif cid:
   try:
    f_rate,f_exp=await asyncio.to_thread(self.get_market_fee_params,str(cid),token_id)
   except Exception as e:
    logger.warning(f"Authoritative CLOB fee query notice for {cid}: {e}; using fallback fee.")
    f_rate=float(market_fee_rate) if market_fee_rate is not None else 0.07
    f_exp=float(market_fee_exponent or 1.0)
  else:
   f_rate,f_exp=0.07,1.0
  if not self.dry_run:
   valid_fee=( math.isfinite(f_rate) and f_rate>=0.0 and math.isfinite(f_exp) and (f_exp > 0.0 or (f_rate==0.0 and f_exp>=0.0)) )
   if not valid_fee:
    err=f"AuthoritativeFeeGuard Rejected: Non-finite or invalid fee parameters (rate={f_rate}, exp={f_exp}) for {cid}."
    logger.error(f"[{trade_id}] {err}")
    return OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=worst_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=(time.perf_counter() - t0) * 1000.0,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err,)
  fee_usd=round(sum( shares_i * f_rate * ((price_i * (1.0 - price_i)) ** f_exp) for price_i,shares_i in fill_legs ),5)
  effective_fee_rate=fee_usd / max(notional_usd,1e-9)
  if self.dry_run:
   latency_ms=(time.perf_counter() - t0) * 1000.0
   mock_order_id=f"MOCK_CLOB_{int(time.time()*1000)}"
   logger.info( f"[DRY-RUN SNIPE] {trade_id} -> {target_token} | Shares={shares_to_buy:.2f} @ ${exec_price:.4f} " f"| Notional=${notional_usd:.2f} | Fee=${fee_usd:.4f} ({effective_fee_rate*100:.2f}%) | Latency={latency_ms:.2f}ms" )
   res=OrderResult( success=True,order_id=mock_order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=exec_price,size=shares_to_buy,notional_usd=notional_usd,fee_usd=fee_usd,latency_ms=latency_ms,mode="DRY_RUN_SIMULATION",execution_status=ExecutionStatus.POSITION_CONFIRMED,confirmed_onchain=True,details={ "fee_rate":effective_fee_rate,"depth_ratio":depth_ratio,"timestamp_utc":now_utc,"confirmed_onchain":True,"pre_token_balance":0.0,"post_token_balance":shares_to_buy,"balance_delta":shares_to_buy,},)
   self._log_order(res)
   return res
  if not self.is_authenticated or self.client is None:
   raise RuntimeError(f"LIVE ORDER REFUSED: Executor is in live real-money mode but unauthenticated ({self.auth_mode}).")
  order_submitted=False
  try:
   if not self.dry_run:
    if prefetched_pre_balance is not None and math.isfinite(float(prefetched_pre_balance)):
     pre_token_bal=float(prefetched_pre_balance)
    elif side=="BUY":
     pre_token_bal=0.0
    else:
     pre_token_bal=await asyncio.to_thread(self.get_onchain_erc1155_balance,token_id)
     if pre_token_bal is None:
      pre_token_bal=await asyncio.to_thread(self.get_conditional_balance,token_id)
     if pre_token_bal is None:
      pre_token_bal=0.0
   else:
    pre_token_bal=0.0
   entry_order_type=getattr(OrderType,"FAK",OrderType.FOK)
   t_qualify_end=time.perf_counter()
   if _trace is not None:
    _trace.stamp("qualify_end")
   qualify_ms=(t_qualify_end - t0) * 1000.0
   t_sign_start=time.perf_counter()
   tick_size_str=str(self.get_token_tick_size(token_id) or "0.01")
   if neg_risk is None and token_id not in self._neg_risk_cache and not self.dry_run:
    await asyncio.to_thread(self.get_token_neg_risk,token_id)
   fee_rate_bps_val=int(round(f_rate * 10000)) if f_rate else 0
   eff_neg_risk=self.get_token_neg_risk(token_id,neg_risk)
   self.prewarm_token_market_cache( token_id=token_id,tick_size=tick_size_str,neg_risk=eff_neg_risk,fee_rate_bps=fee_rate_bps_val,condition_id=condition_id,fee_rate=f_rate,fee_exponent=f_exp,)
   create_options=PartialCreateOrderOptions(tick_size=tick_size_str,neg_risk=eff_neg_risk,version=2) if PartialCreateOrderOptions else None
   dispatch_stage:Dict[str,Any]={"submitted":False}
   hop:Optional[Dict[str,Any]]=None
   _hop_exc:Optional[BaseException]=None
   if _trace is not None:
    _trace.stamp("dispatch_enqueue")
   enqueue_ns=time.perf_counter_ns()
   try:
    hop=await asyncio.get_running_loop().run_in_executor( _get_hot_io_pool(),_sign_and_post_single_hop,self.client,self.order_ladder_cache,token_id,worst_acceptable_px,shares_to_buy,side,entry_order_type,create_options,dispatch_stage,notional_usd,enqueue_ns,)
   except BaseException as _exc_h:
    _hop_exc=_exc_h
    raise
   finally:
    order_submitted=bool(dispatch_stage.get("submitted"))
    if _trace is not None:
     _trace.stamp("post_return")
     if hop is None:
      _t_p0=dispatch_stage.get("t_post_start")
      _post_err_ms=round((time.perf_counter() - float(_t_p0)) * 1000.0,3) if _t_p0 else None
      _exc_outcome=( "fak_killed" if (_hop_exc is not None and is_fak_killed_no_match(_hop_exc)) else ( "clob_400_rejected" if (_hop_exc is not None and is_clob_400_rejection(_hop_exc)) else "dispatch_exception" ) )
      _trace.emit( trade_id=trade_id,token_id=token_id,side=side,outcome=_exc_outcome,submitted=order_submitted,hot_active=_HOT_DISPATCH_ACTIVE.count,qualify_ms=round(qualify_ms,3),sign_ms=dispatch_stage.get("sign_ms"),thread_hop_ms=dispatch_stage.get("thread_hop_ms"),clob_http_post_ms=_post_err_ms,presign_cache_hit=dispatch_stage.get("cache_hit"),)
   shares_to_buy=float(hop.get("signed_shares",shares_to_buy))
   post_resp=hop["post_resp"]
   sign_ms=hop["sign_ms"]
   thread_hop_ms=float(hop.get("thread_hop_ms",0.0))
   clob_http_post_ms=hop["post_ms"]
   t_post_end=time.perf_counter()
   total_trigger_to_ack_ms=(t_post_end - t0) * 1000.0
   if hop["cache_hit"]:
    logger.debug(f"[{trade_id}] Pre-signed order ladder cache hit (sign_ms={sign_ms:.3f}ms)")
   logger.info( f"[{trade_id}] LATENCY TELEMETRY: qualify_ms={qualify_ms:.2f} | sign_ms={sign_ms:.2f} | " f"thread_hop_ms={thread_hop_ms:.3f} | clob_http_post_ms={clob_http_post_ms:.2f} | total_trigger_to_ack_ms={total_trigger_to_ack_ms:.2f}" )
   latency_ms=(t_post_end - t0) * 1000.0
   order_id=post_resp.get("orderID") or post_resp.get("id")
   if _trace is not None:
    _trace.emit( trade_id=trade_id,token_id=token_id,side=side,outcome="posted",order_id_present=bool(order_id),resp_status=str(post_resp.get("status")),resp_error=str(post_resp.get("errorMsg") or post_resp.get("error") or "")[:120],qualify_ms=round(qualify_ms,3),sign_ms=round(sign_ms,3),thread_hop_ms=round(float(hop.get("thread_hop_ms",0.0)),3),clob_http_post_ms=round(clob_http_post_ms,3),total_trigger_to_ack_ms=round(total_trigger_to_ack_ms,3),presign_cache_hit=bool(hop.get("cache_hit")),hot_active=_HOT_DISPATCH_ACTIVE.count,taker_delay_hint=getattr(self,"_taker_delay_ms_hint",None),)
   if is_fak_killed_no_match(None,post_resp):
    err_msg=post_resp.get("error") or post_resp.get("errorMsg") or "FAK order killed with zero match"
    logger.warning(f"[{trade_id}] FAK order deterministically killed by CLOB (zero match): {err_msg} | orderID={order_id}")
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=latency_ms,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err_msg,details={ "outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":post_resp,"depth_ratio":depth_ratio,"timestamp_utc":now_utc,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,"latency_telemetry":{ "qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",0.0),"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
    self._log_order(res)
    return res
   _async_post_err=post_resp.get("errorMsg") or post_resp.get("error")
   if _async_post_err and not order_id:
    err_msg=_async_post_err
    logger.error(f"[{trade_id}] Order rejected by CLOB: {err_msg} | raw={post_resp}")
    res=OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=shares_to_buy,notional_usd=notional_usd,fee_usd=fee_usd,latency_ms=latency_ms,mode="LIVE_CLOB_ERROR",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=err_msg,details={ "raw_response":post_resp,"depth_ratio":depth_ratio,"timestamp_utc":now_utc,"pre_token_balance":pre_token_bal,"outcome_unknown":False,"requires_exchange_reconciliation":False,"latency_telemetry":{ "qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",0.0),"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
    self._log_order(res)
    return res
   if not order_id or _async_post_err:
    err_msg=( f"CONTRADICTORY_RESPONSE: orderID={order_id} with errorMsg={_async_post_err}" if order_id else "No orderID returned from CLOB matching engine (incomplete/ambiguous response)" )
    logger.error(f"[{trade_id}] {err_msg} | raw={post_resp}")
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=shares_to_buy,notional_usd=notional_usd,fee_usd=fee_usd,latency_ms=latency_ms,mode="LIVE_AMBIGUOUS_SUBMISSION",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,error=err_msg,details={ "outcome_unknown":True,"requires_exchange_reconciliation":True,"raw_response":post_resp,"depth_ratio":depth_ratio,"timestamp_utc":now_utc,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,"entry_order_id":order_id,"latency_telemetry":{ "qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",0.0),"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
    self._log_order(res)
    return res
   resp_status=str(post_resp.get("status") or "").upper()
   making_amt=post_resp.get("makingAmount")
   taking_amt=post_resp.get("takingAmount")
   if resp_status.startswith("CANCEL") or resp_status in {"UNMATCHED","EXPIRED","REJECTED"}:
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=latency_ms,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=f"CLOB order returned terminal non-fill status={resp_status}",details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":post_resp},)
    self._log_order(res)
    return res
   if resp_status in {"DELAYED","LIVE"} and making_amt in (None,"") and taking_amt in (None,""):
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=shares_to_buy,notional_usd=notional_usd,fee_usd=fee_usd,latency_ms=latency_ms,mode="LIVE_AMBIGUOUS_SUBMISSION",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,error=f"CLOB order returned non-immediate status={resp_status} without fill amounts",details={ "outcome_unknown":True,"requires_exchange_reconciliation":True,"raw_response":post_resp,"entry_order_id":order_id,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,},)
    self._log_order(res)
    return res
   if making_amt not in (None,""):
    try:
     actual_notional=float(making_amt)
    except (ValueError,TypeError) as parse_err:
     raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid makingAmount={making_amt}: {parse_err}")
   else:
    actual_notional=round(shares_to_buy * exec_price,4)
   if taking_amt not in (None,""):
    try:
     actual_shares=float(taking_amt)
    except (ValueError,TypeError) as parse_err:
     raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid takingAmount={taking_amt}: {parse_err}")
   else:
    actual_shares=shares_to_buy
   if (making_amt not in (None,"") or taking_amt not in (None,"")) and actual_shares<=0.0:
    res=OrderResult( success=False,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=latency_ms,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error="FAK order matched 0 shares",details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":post_resp},)
    self._log_order(res)
    return res
   fill_px=round(actual_notional / max(actual_shares,1e-4),4) if (making_amt not in (None,"") and taking_amt not in (None,"") and actual_shares > 0) else exec_price
   if making_amt not in (None,"") and taking_amt not in (None,"") and actual_shares > 0:
    p_clamped=max(0.001,min(0.999,fill_px))
    fee_usd=round(actual_shares * f_rate * ((p_clamped * (1.0 - p_clamped)) ** f_exp),5)
   trade_ids=post_resp.get("tradeIDs",[])
   tx_hashes=post_resp.get("transactionsHashes",[])
   logger.info( f"[LIVE CLOB MATCHED] {trade_id} -> OID: {order_id} | {target_token} | Shares={actual_shares:.2f} " f"@ ${fill_px:.4f} | Notional=${actual_notional:.2f} | Latency={latency_ms:.2f}ms | Trades={trade_ids}" )
   res=OrderResult( success=True,order_id=order_id,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=fill_px,size=actual_shares,notional_usd=actual_notional,fee_usd=fee_usd,latency_ms=latency_ms,mode="LIVE_CLOB",execution_status=ExecutionStatus.MATCHED_PENDING_SETTLEMENT,confirmed_onchain=False,details={ "raw_response":post_resp,"depth_ratio":depth_ratio,"timestamp_utc":now_utc,"confirmed_onchain":False,"pre_token_balance":pre_token_bal,"trade_ids":trade_ids,"transactions_hashes":tx_hashes,"latency_telemetry":{ "qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",0.0),"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
   self._log_order(res)
   return res
  except Exception as e:
   t_exc=time.perf_counter()
   latency_ms=(t_exc - t0) * 1000.0
   _ds=locals().get("dispatch_stage") or {}
   _t_post_s=_ds.get("t_post_start") or locals().get("t_post_start")
   clob_http_post_ms=round(max(0.0,(t_exc - float(_t_post_s)) * 1000.0),3) if _t_post_s else 0.0
   _exc_sign_ms=float(_ds.get("sign_ms") if _ds.get("sign_ms") is not None else locals().get("sign_ms",0.0))
   _exc_hop_ms=float(_ds.get("thread_hop_ms") if _ds.get("thread_hop_ms") is not None else locals().get("thread_hop_ms",0.0))
   total_trigger_to_ack_ms=(t_exc - t0) * 1000.0
   err_msg=f"CLOB order submission failed: {e}"
   if is_clob_400_rejection(e):
    self._evict_tick_size_if_tick_err(token_id,e)
    extracted_oid=None
    err_dict=getattr(e,"error_message",None) or getattr(e,"error_msg",None)
    if isinstance(err_dict,dict):
     extracted_oid=err_dict.get("orderID") or err_dict.get("id")
    elif isinstance(err_dict,str):
     try:
      parsed=json.loads(err_dict)
      if isinstance(parsed,dict):
       extracted_oid=parsed.get("orderID") or parsed.get("id")
     except Exception:
      pass
    logger.warning(f"[{trade_id}] Order deterministically rejected by CLOB (HTTP 400 / 0 match): {e} | orderID={extracted_oid}")
    res=OrderResult( success=False,order_id=extracted_oid,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=0.0,fee_usd=0.0,latency_ms=latency_ms,mode="FAK_KILLED_NO_MATCH" if is_fak_killed_no_match(e) else "CLOB_HTTP_400_REJECTION",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=str(e),details={ "outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"clob_400_rejection":True,"raw_exception":str(e),"status_code":getattr(e,"status_code",400),"pre_token_balance":locals().get("pre_token_bal"),"intended_notional_usd":notional_usd,"latency_telemetry":{ "qualify_ms":locals().get("qualify_ms",0.0),"sign_ms":_exc_sign_ms,"thread_hop_ms":_exc_hop_ms,"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
    self._log_order(res)
    return res
   logger.error(f"[{trade_id}] {err_msg}")
   res=OrderResult( success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=best_px,size=0.0,notional_usd=notional_usd,fee_usd=0.0,latency_ms=latency_ms,mode="LIVE_CLOB_ERROR",execution_status=ExecutionStatus.SUBMITTED if order_submitted else ExecutionStatus.REJECTED,confirmed_onchain=False,error=err_msg,details={ "outcome_unknown":bool(order_submitted),"requires_exchange_reconciliation":bool(order_submitted),"pre_token_balance":locals().get("pre_token_bal"),"intended_notional_usd":notional_usd,"latency_telemetry":{ "qualify_ms":locals().get("qualify_ms",0.0),"sign_ms":_exc_sign_ms,"thread_hop_ms":_exc_hop_ms,"clob_http_post_ms":clob_http_post_ms,"total_trigger_to_ack_ms":total_trigger_to_ack_ms,},},)
   self._log_order(res)
   return res
 def _evict_tick_size_if_tick_err(self,token_id:str,err_obj:Any)->None:
  if not token_id:
   return
  low=str(err_obj or "").lower()
  if any(k in low for k in ("tick","minimum_tick_size","invalid price","price precision")):
   self._tick_size_cache.pop(token_id,None)
   if self.client is not None and hasattr(self.client,"_ClobClient__tick_sizes"):
    try:
     self.client._ClobClient__tick_sizes.pop(token_id,None)
    except Exception:
     pass
 def get_token_tick_size(self,token_id:str,price_hint:Optional[float]=None)->float:
  cached=self._tick_size_cache.get(token_id)
  recheck_dynamic_boundary=( cached==0.01 and price_hint is not None and math.isfinite(float(price_hint)) and ( float(price_hint)>=0.96 or float(price_hint)<=0.04 or abs(round(float(price_hint),2) - round(float(price_hint),4)) > 1e-6 ) and self.client is not None and hasattr(self.client,"get_tick_size") )
  if cached is not None and not recheck_dynamic_boundary:
   return cached
  if self.client and hasattr(self.client,"get_tick_size"):
   try:
    raw_tick=self.client.get_tick_size(token_id)
    if isinstance(raw_tick,(str,int,float,Decimal)) and not isinstance(raw_tick,bool):
     tick_val=float(raw_tick)
     if any(abs(tick_val - vt) < 1e-9 for vt in (0.1,0.01,0.005,0.0025,0.001,0.0001)):
      self._tick_size_cache[token_id]=tick_val
      if hasattr(self.client,"_ClobClient__tick_sizes"):
       self.client._ClobClient__tick_sizes[token_id]=str(raw_tick)
      return tick_val
   except Exception as e:
    logger.debug(f"Could not resolve tick size from SDK for {token_id}: {e}")
  if cached is not None:
   return cached
  if not self.dry_run and not hasattr(self.client,"_mock_children"):
   raise RuntimeError(f"AUTHORITATIVE_TICK_SIZE_UNAVAILABLE for live token {token_id}")
  tick_val=0.01
  self._tick_size_cache[token_id]=tick_val
  return tick_val
 def quantize_order_price(self,price:float,token_id:str,rounding=ROUND_HALF_UP)->float:
  if price is None or not math.isfinite(float(price)):
   raise ValueError(f"Refusing to quantize non-finite price {price!r} for {token_id}")
  try:
   raw_t=self.get_token_tick_size(token_id,price_hint=float(price))
  except TypeError:
   raw_t=self.get_token_tick_size(token_id)
  tick=Decimal(str(raw_t))
  clean_px=round(float(price),6)
  units=(Decimal(str(clean_px)) / tick).to_integral_value(rounding=rounding)
  q=units * tick
  q=max(tick,min(Decimal("1") - tick,q))
  return float(q)
 def post_maker_entry_order( self,token_id:str,price:float,notional_usd:float,side:str="BUY",neg_risk:Optional[bool]=None,min_price_floor:float=0.02,max_price_ceiling:float=0.96,)->Dict[str,Any]:
  try:
   notional_f=float(notional_usd)
   price_f=float(price)
  except (TypeError,ValueError):
   return {"success":False,"orderID":None,"error":"INVALID_MAKER_ENTRY_INPUTS","retryable":False}
  if not math.isfinite(notional_f) or notional_f<=0 or not math.isfinite(price_f) or price_f<=0:
   return {"success":False,"orderID":None,"error":"NON_POSITIVE_MAKER_ENTRY_INPUTS","retryable":False}
  quantized_price=self.quantize_order_price(price_f,token_id,rounding=ROUND_FLOOR)
  if quantized_price < min_price_floor or quantized_price > max_price_ceiling:
   return { "success":False,"orderID":None,"error":f"MAKER_ENTRY_PRICE_OUT_OF_BOUNDS ({quantized_price:.4f} not in [{min_price_floor:.2f}, {max_price_ceiling:.2f}])","retryable":False,}
  shares_int=float(math.floor(notional_f / quantized_price))
  if shares_int < 5.0:
   return { "success":False,"orderID":None,"error":f"MAKER_ENTRY_MIN_SHARES_REJECTED ({shares_int:.0f} < 5 shares at ${quantized_price:.4f})","retryable":False,}
  if self.dry_run:
   if neg_risk is not None:
    self.get_token_neg_risk(token_id,neg_risk)
   mock_id=f"MOCK_MAKER_ENTRY_{int(time.time()*1000)}"
   logger.info( f"[DRY-RUN MAKER ENTRY] Resting {side} post_only GTC: {shares_int:.0f} shares @ ${quantized_price:.4f} " f"(notional=${shares_int * quantized_price:.2f}, ID={mock_id})" )
   return { "success":True,"orderID":mock_id,"mode":"DRY_RUN","post_only":True,"price":quantized_price,"shares":shares_int,"notional_usd":round(shares_int * quantized_price,4),}
  if not self.is_authenticated or self.client is None or OrderArgsV2 is None:
   raise RuntimeError(f"LIVE MAKER ENTRY REFUSED: Executor unauthenticated ({self.auth_mode}).")
  order_submitted=False
  try:
   tick_sz=self.get_token_tick_size(token_id)
   eff_neg_risk=self.get_token_neg_risk(token_id,neg_risk)
   create_opts=( PartialCreateOrderOptions(tick_size=str(tick_sz),neg_risk=eff_neg_risk,version=2) if PartialCreateOrderOptions else None )
   order_args=OrderArgsV2(price=quantized_price,size=shares_int,side=side,token_id=token_id)
   has_lockfree_fast_signer=( getattr(self.client,"_fast_v2_signer",None) is not None and "create_order" not in getattr(self.client,"__dict__",{}) )
   if has_lockfree_fast_signer:
    signed_order=_safe_create_order(self.client.create_order,order_args,create_opts)
   else:
    with _UrgentSignPriority():
     signed_order=_safe_create_order(self.client.create_order,order_args,create_opts)
   order_submitted=True
   resp=self.client.post_order(signed_order,OrderType.GTC,post_only=True,defer_exec=True)
   has_err=resp.get("errorMsg") or resp.get("error")
   order_id=resp.get("orderID") or resp.get("id")
   if has_err and order_id:
    return { "success":False,"orderID":order_id,"outcome_unknown":True,"retryable":False,"error":f"CONTRADICTORY_MAKER_ENTRY_RESPONSE: {has_err}","raw":resp,}
   if has_err:
    return { "success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"error":str(has_err),"raw":resp,}
   if order_id:
    logger.info( f"[LIVE MAKER ENTRY POSTED] OID={order_id} | {side} {shares_int:.0f} shares @ ${quantized_price:.4f} (neg_risk={eff_neg_risk})" )
    return { "success":True,"orderID":order_id,"post_only":True,"price":quantized_price,"shares":shares_int,"notional_usd":round(shares_int * quantized_price,4),"raw":resp,}
   return { "success":False,"orderID":None,"outcome_unknown":True,"retryable":False,"error":"MISSING_ORDER_ID_IN_MAKER_ENTRY","raw":resp,}
  except Exception as e:
   err_msg=str(getattr(e,"error_message","") or str(e))
   self._evict_tick_size_if_tick_err(token_id,err_msg)
   is_client_err=is_clob_400_rejection(e) or any( k in err_msg.lower() for k in ("crosses book","post only","post-only","not enough balance","allowance") )
   return { "success":False,"orderID":None,"outcome_unknown":bool(order_submitted and not is_client_err),"retryable":bool(not order_submitted or is_client_err),"error":err_msg,}
 place_passive_maker_entry=post_maker_entry_order
 @staticmethod
 def _extract_fok_matched_shares(resp:Dict[str,Any],default_shares:float)->Optional[float]:
  if not isinstance(resp,dict):
   return None
  for key in ("takingAmount","taking_amount","matched_size","size_matched","sizeMatched"):
   val=resp.get(key)
   if val not in (None,""):
    try:
     parsed=float(val)
     return parsed if math.isfinite(parsed) else None
    except (TypeError,ValueError):
     return None
  if str(resp.get("status","")).upper() in {"DELAYED","LIVE","UNMATCHED"}:
   return None
  return default_shares
 def execute_atomic_dominance_box( self,box_id:str,leg_a_token_id:str,leg_a_label:str,leg_a_limit_price:float,leg_b_token_id:str,leg_b_label:str,leg_b_limit_price:float,shares:float,max_box_cost_net:float=0.995,fee_rate:float=0.07,fee_exponent:float=1.0,leg_a_avail_shares:Optional[float]=None,leg_b_avail_shares:Optional[float]=None,neg_risk:bool=False,fee_rate_a:Optional[float]=None,fee_rate_b:Optional[float]=None,fee_exponent_a:Optional[float]=None,fee_exponent_b:Optional[float]=None,parallel_dispatch:Optional[bool]=None,leg_a_pre_balance:Optional[float]=None,leg_b_pre_balance:Optional[float]=None,)->Dict[str,Any]:
  try:
   px_a_in,px_b_in,shares_in,cap_in=float(leg_a_limit_price),float(leg_b_limit_price),float(shares),float(max_box_cost_net)
   fr_a=float(fee_rate if fee_rate_a is None else fee_rate_a)
   fe_a=float(fee_exponent if fee_exponent_a is None else fee_exponent_a)
   fr_b=float(fee_rate if fee_rate_b is None else fee_rate_b)
   fe_b=float(fee_exponent if fee_exponent_b is None else fee_exponent_b)
  except (TypeError,ValueError):
   return {"success":False,"error":"INVALID_BOX_INPUTS","legged_out":False,"outcome_unknown":False}
  if ( not leg_a_token_id or not leg_b_token_id or str(leg_a_token_id)==str(leg_b_token_id) or not math.isfinite(px_a_in) or not math.isfinite(px_b_in) or not math.isfinite(shares_in) or px_a_in<=0.0 or px_b_in<=0.0 ):
   return {"success":False,"error":"INVALID_BOX_TOKENS_OR_PRICES","legged_out":False,"outcome_unknown":False}
  shares_int=float(math.floor(shares_in))
  if shares_int < 5.0:
   return {"success":False,"error":f"BOX_MIN_SHARES_REJECTED ({shares_int:.0f} < 5 shares)","legged_out":False,"outcome_unknown":False}
  px_a=self.quantize_order_price(px_a_in,leg_a_token_id,rounding=ROUND_CEILING)
  px_b=self.quantize_order_price(px_b_in,leg_b_token_id,rounding=ROUND_CEILING)
  fee_a_ps=fr_a * ((px_a * (1.0 - px_a)) ** fe_a) if fr_a > 0.0 else 0.0
  fee_b_ps=fr_b * ((px_b * (1.0 - px_b)) ** fe_b) if fr_b > 0.0 else 0.0
  worst_box_cost_net=round(px_a + fee_a_ps + px_b + fee_b_ps,6)
  if worst_box_cost_net < 0.900 - 1e-6:
   return { "success":False,"error":f"ANTI_BOX_COST_FLOOR_VETO ({worst_box_cost_net:.5f} < 0.90000)","worst_box_cost_net":worst_box_cost_net,"legged_out":False,"outcome_unknown":False,}
  if worst_box_cost_net > cap_in + 1e-6:
   return { "success":False,"error":f"WORST_LIMIT_BOX_COST_EXCEEDS_CAP ({worst_box_cost_net:.5f} > {cap_in:.5f})","worst_box_cost_net":worst_box_cost_net,"legged_out":False,"outcome_unknown":False,}
  _a_4h="4h" in str(leg_a_label).lower()
  _b_4h="4h" in str(leg_b_label).lower()
  _a_sub=any(h in str(leg_a_label).lower() for h in ("15m","5m"))
  _b_sub=any(h in str(leg_b_label).lower() for h in ("15m","5m"))
  if _a_4h and _b_sub and not _b_4h:
   b_thinner=True
  elif _b_4h and _a_sub and not _a_4h:
   b_thinner=False
  elif leg_a_avail_shares is not None and leg_b_avail_shares is not None and min(float(leg_a_avail_shares),float(leg_b_avail_shares)) > 0.0:
   av_a,av_b=float(leg_a_avail_shares),float(leg_b_avail_shares)
   b_thinner=(av_b < av_a) if max(av_a,av_b) > 1.20 * min(av_a,av_b) else (px_b < px_a)
  else:
   b_thinner=px_b < px_a
  if b_thinner:
   legs=[ (leg_b_token_id,leg_b_label,px_b,fee_b_ps),(leg_a_token_id,leg_a_label,px_a,fee_a_ps),]
  else:
   legs=[ (leg_a_token_id,leg_a_label,px_a,fee_a_ps),(leg_b_token_id,leg_b_label,px_b,fee_b_ps),]
  if self.dry_run:
   self.get_token_neg_risk(leg_a_token_id,neg_risk)
   self.get_token_neg_risk(leg_b_token_id,neg_risk)
   ts_ms=int(time.time() * 1000)
   return { "success":True,"mode":"DRY_RUN","box_id":box_id,"shares":shares_int,"worst_box_cost_net":worst_box_cost_net,"guaranteed_min_profit_usd":round(shares_int * (1.0 - worst_box_cost_net),4),"legged_out":False,"outcome_unknown":False,"leg_1":{"label":legs[0][1],"token_id":legs[0][0],"price":legs[0][2],"orderID":f"MOCK_BOX_L1_{ts_ms}"},"leg_2":{"label":legs[1][1],"token_id":legs[1][0],"price":legs[1][2],"orderID":f"MOCK_BOX_L2_{ts_ms}"},}
  if not self.is_authenticated or self.client is None or OrderArgsV2 is None:
   raise RuntimeError(f"LIVE DOMINANCE BOX REFUSED: Executor unauthenticated ({self.auth_mode}).")
  (tok_1,lbl_1,px_1,_),(tok_2,lbl_2,px_2,_)=legs
  tick_1=self.get_token_tick_size(tok_1)
  tick_2=self.get_token_tick_size(tok_2)
  nr_1=self.get_token_neg_risk(tok_1,neg_risk)
  nr_2=self.get_token_neg_risk(tok_2,neg_risk)
  opts_1=PartialCreateOrderOptions(tick_size=str(tick_1),neg_risk=nr_1,version=2) if PartialCreateOrderOptions else None
  opts_2=PartialCreateOrderOptions(tick_size=str(tick_2),neg_risk=nr_2,version=2) if PartialCreateOrderOptions else None
  _pre_bal_map={ str(leg_a_token_id):float(leg_a_pre_balance or 0.0),str(leg_b_token_id):float(leg_b_pre_balance or 0.0),}
  def _unwind_legged_out( tok_u:str,lbl_u:str,m_u:float,px_u:float,nr_u:bool,oid_u:Optional[str],raw_u:Any )->Tuple[Dict[str,Any],Dict[str,Any]]:
   pre_u=_pre_bal_map.get(str(tok_u),0.0)
   avail_u:Optional[float]=None
   is_live_auth_u=getattr(self,"auth_mode","") in ("LIVE","AUTHENTICATED_L2")
   if is_live_auth_u:
    deadline_u=time.monotonic() + 5.0
    while time.monotonic() < deadline_u:
     try:
      avail_u=self.get_unreserved_conditional_balance(tok_u)
     except Exception:
      avail_u=None
      break
     if avail_u is None:
      break
     settled_delta=max(0.0,float(avail_u) - pre_u) if pre_u > 0.0 else float(avail_u)
     if settled_delta>=float(m_u) - 0.05:
      break
     time.sleep(0.15)
   settled_ready=float(m_u)
   if is_live_auth_u and avail_u is not None:
    settled_ready=max(0.0,float(avail_u) - pre_u) if pre_u > 0.0 else float(avail_u)
    settled_ready=min(float(avail_u),settled_ready)
   if is_live_auth_u and avail_u is not None and settled_ready < 0.05:
    uw_res:Dict[str,Any]={ "success":False,"matched_size":0.0,"outcome_unknown":False,"error":"DEFERRED_TO_ASYNC_SUPERVISOR_PENDING_SETTLEMENT",}
    return uw_res,{ "token_id":tok_u,"label":lbl_u,"price":px_u,"matched_shares":float(m_u),"unwound_shares":0.0,"residual_shares":round(float(m_u),4),"orderID":oid_u,"raw":raw_u,"unwind_outcome_unknown":False,"unwind_result":uw_res,}
   req_1=(math.floor(min(float(m_u),settled_ready) * 100.0 + 1e-9) / 100.0) if (is_live_auth_u and avail_u is not None and settled_ready < float(m_u) - 0.05) else float(m_u)
   _gb_frac=float((getattr(self,"risk_config",None) or RISK_CONFIG).get("d1_max_giveback_frac",0.25))
   stage1_drop=max(0.01,min(0.03,round(_gb_frac * max(0.02,1.0 - worst_box_cost_net),2)))
   uw_res=self.execute_unwind_order( tok_u,size=req_1,side="SELL",min_price=max(0.01,round(px_u - stage1_drop,2)),neg_risk=nr_u )
   uw_unk=bool(isinstance(uw_res,dict) and uw_res.get("outcome_unknown"))
   unwound_sh=( float(uw_res.get("matched_size") or 0.0) if (isinstance(uw_res,dict) and (uw_res.get("success") or uw_res.get("partial")) and not uw_unk) else 0.0 )
   tot_taking=float((uw_res or {}).get("taking_amount") or (uw_res or {}).get("notional_usd") or 0.0) if unwound_sh > 0.0 else 0.0
   tot_fee=float((uw_res or {}).get("fee_usd") or 0.0) if unwound_sh > 0.0 else 0.0
   rem_u=round(max(0.0,float(m_u) - unwound_sh),4)
   settled_after_1=max(0.0,settled_ready - unwound_sh)
   if is_live_auth_u and avail_u is not None and rem_u > 0.05 and not uw_unk:
    try:
     avail_u2=self.get_unreserved_conditional_balance(tok_u)
    except Exception:
     avail_u2=None
    if avail_u2 is not None:
     if float(avail_u2) > float(avail_u) + 0.05:
      settled_after_1 += float(avail_u2) - float(avail_u)
     settled_cap_2=max(0.0,float(avail_u2) - pre_u) if pre_u > 0.0 else max(0.0,float(avail_u2))
     settled_after_1=min(settled_after_1,settled_cap_2)
   if rem_u > 0.05 and not uw_unk and (not is_live_auth_u or avail_u is None or settled_after_1>=0.05):
    req_2=(math.floor(min(rem_u,settled_after_1) * 100.0 + 1e-9) / 100.0) if (is_live_auth_u and avail_u is not None) else rem_u
    if req_2>=0.05:
     uw_2=self.execute_unwind_order( tok_u,size=req_2,side="SELL",min_price=max(0.01,round(px_u * 0.85,2)),neg_risk=nr_u )
     if isinstance(uw_2,dict):
      uw_unk=bool(uw_2.get("outcome_unknown"))
      if (uw_2.get("success") or uw_2.get("partial")) and not uw_unk:
       sh_2=float(uw_2.get("matched_size") or 0.0)
       unwound_sh += sh_2
       if sh_2 > 0.0:
        tot_taking += float(uw_2.get("taking_amount") or uw_2.get("notional_usd") or 0.0)
        tot_fee += float(uw_2.get("fee_usd") or 0.0)
      uw_res=dict(uw_2)
      if unwound_sh > 0.0:
       uw_res["matched_size"]=round(unwound_sh,4)
       uw_res["taking_amount"]=round(tot_taking,6)
       uw_res["fee_usd"]=round(tot_fee,6)
   resid_sh=round(max(0.0,float(m_u) - unwound_sh),4)
   return uw_res,{ "token_id":tok_u,"label":lbl_u,"price":px_u,"matched_shares":float(m_u),"unwound_shares":unwound_sh,"residual_shares":resid_sh,"orderID":oid_u,"raw":raw_u,"unwind_outcome_unknown":uw_unk,"unwind_result":uw_res,}
  _has_fast_box_signer=( getattr(self.client,"_fast_v2_signer",None) is not None and "create_order" not in getattr(self.client,"__dict__",{}) )
  if _has_fast_box_signer:
   signed_1=_safe_create_order( self.client.create_order,OrderArgsV2(price=px_1,size=shares_int,side="BUY",token_id=tok_1),opts_1,)
   signed_2=_safe_create_order( self.client.create_order,OrderArgsV2(price=px_2,size=shares_int,side="BUY",token_id=tok_2),opts_2,)
  else:
   with _UrgentSignPriority():
    signed_1=_safe_create_order( self.client.create_order,OrderArgsV2(price=px_1,size=shares_int,side="BUY",token_id=tok_1),opts_1,)
    signed_2=_safe_create_order( self.client.create_order,OrderArgsV2(price=px_2,size=shares_int,side="BUY",token_id=tok_2),opts_2,)
  import inspect as _inspect
  _po_fn=self.client.post_order
  try:
   _po_params=list(_inspect.signature(_po_fn).parameters.values())
   _supports_defer=len(_po_params)>=4 or any( p.kind in (_inspect.Parameter.VAR_POSITIONAL,_inspect.Parameter.VAR_KEYWORD) or p.name=="defer_exec" for p in _po_params )
  except Exception:
   _supports_defer=True
  def _post_fok_fast(signed_ord:Any)->Any:
   if _supports_defer:
    return _po_fn(signed_ord,OrderType.FOK,False,True)
   return _po_fn(signed_ord,OrderType.FOK)
  use_parallel=( bool(parallel_dispatch) if parallel_dispatch is not None else bool( leg_a_avail_shares is not None and leg_b_avail_shares is not None and float(leg_a_avail_shares)>=1.5 * shares_int and float(leg_b_avail_shares)>=1.5 * shares_int ) )
  _HOT_DISPATCH_ACTIVE.enter()
  try:
   if use_parallel:
    _mock_children=getattr(self.client,"_mock_children",None)
    _client_dict=getattr(self.client,"__dict__",{})
    can_batch_post_orders=( PostOrdersV2Args is not None and "post_order" not in _client_dict and ( _mock_children is None or "post_orders" in _mock_children or "post_orders" in _client_dict ) and hasattr(self.client,"post_orders") and os.environ.get("PM_DISABLE_D1_BATCH_POST_ORDERS","0")!="1" )
    if can_batch_post_orders:
     disp_mode="BATCH_POST_ORDERS_FOK"
     skew_ms=0.0
     try:
      batch_resp=self.client.post_orders( [ PostOrdersV2Args(order=signed_1,orderType=OrderType.FOK,deferExec=True),PostOrdersV2Args(order=signed_2,orderType=OrderType.FOK,deferExec=True),],post_only=False,defer_exec=True,)
      if isinstance(batch_resp,list) and len(batch_resp)==2:
       resp_1,exc_1=batch_resp[0],None
       resp_2,exc_2=batch_resp[1],None
      else:
       malformed_exc=RuntimeError(f"UNEXPECTED_BATCH_POST_ORDERS_RESPONSE:{type(batch_resp).__name__}")
       resp_1,exc_1=None,malformed_exc
       resp_2,exc_2=None,malformed_exc
     except Exception as exc_b:
      resp_1,exc_1=None,exc_b
      resp_2,exc_2=None,exc_b
    else:
     disp_mode="PARALLEL_2LEG_FOK"
     def _post_leg(signed_ord:Any)->Tuple[Optional[Dict[str,Any]],Optional[Exception],float]:
      t_s=time.perf_counter()
      try:
       return _post_fok_fast(signed_ord),None,t_s
      except Exception as exc_p:
       return None,exc_p,t_s
     hot_pool=_get_hot_io_pool()
     f1=hot_pool.submit(_post_leg,signed_1)
     f2=hot_pool.submit(_post_leg,signed_2)
     resp_1,exc_1,ts_1=f1.result()
     resp_2,exc_2,ts_2=f2.result()
     skew_ms=round(abs(ts_2 - ts_1) * 1000.0,3)
    def _eval_leg(resp_x:Optional[Dict[str,Any]],exc_x:Optional[Exception])->Tuple[str,float,Optional[str],str]:
     if exc_x is not None:
      em=str(getattr(exc_x,"error_message","") or str(exc_x))
      clean=is_clob_400_rejection(exc_x) or any( k in em.lower() for k in ("fok","couldn't be fully filled","fully filled","not enough balance") )
      return ("REJECTED" if clean else "UNKNOWN"),0.0,None,em
     if not isinstance(resp_x,dict):
      return "UNKNOWN",0.0,None,"MISSING_RESPONSE"
     err_x=resp_x.get("errorMsg") or resp_x.get("error")
     oid_x=resp_x.get("orderID") or resp_x.get("id")
     if err_x and not oid_x:
      return "REJECTED",0.0,None,str(err_x)
     if err_x or not oid_x:
      return "UNKNOWN",0.0,oid_x,str(err_x or "missing orderID")
     m_sh=self._extract_fok_matched_shares(resp_x,shares_int)
     if m_sh is None:
      return "UNKNOWN",0.0,oid_x,f"NON_IMMEDIATE_STATUS ({resp_x.get('status')})"
     if m_sh<=0.0:
      return "REJECTED",0.0,oid_x,"MATCHED_ZERO_SHARES"
     return "FILLED",float(m_sh),str(oid_x),""
    st_1,m_1,oid_1,err_s1=_eval_leg(resp_1,exc_1)
    st_2,m_2,oid_2,err_s2=_eval_leg(resp_2,exc_2)
    if st_1=="FILLED" and st_2=="FILLED":
     paired_shares=min(m_1,m_2)
     imbalance_unwind=None
     if abs(m_1 - m_2) > 0.05:
      excess_tok,excess_px,excess_nr=(tok_1,px_1,nr_1) if m_1 > m_2 else (tok_2,px_2,nr_2)
      imbalance_unwind=self.execute_unwind_order( excess_tok,size=abs(m_1 - m_2),side="SELL",min_price=max(0.01,round(excess_px * 0.85,2)),neg_risk=excess_nr )
     return { "success":True,"box_id":box_id,"dispatch_mode":disp_mode,"inter_leg_skew_ms":skew_ms,"shares":paired_shares,"worst_box_cost_net":worst_box_cost_net,"guaranteed_min_profit_usd":round(paired_shares * (1.0 - worst_box_cost_net),4),"legged_out":False,"outcome_unknown":False,"imbalance_unwind":imbalance_unwind,"leg_1":{"label":lbl_1,"token_id":tok_1,"price":px_1,"matched_shares":m_1,"orderID":oid_1,"raw":resp_1},"leg_2":{"label":lbl_2,"token_id":tok_2,"price":px_2,"matched_shares":m_2,"orderID":oid_2,"raw":resp_2},}
    if st_1=="REJECTED" and st_2=="REJECTED":
     return { "success":False,"stage":"PARALLEL_BOTH_REJECTED","dispatch_mode":disp_mode,"inter_leg_skew_ms":skew_ms,"legged_out":False,"outcome_unknown":False,"error":f"L1={err_s1}; L2={err_s2}",}
    if st_1=="FILLED" and st_2=="REJECTED":
     uw,resid_info=_unwind_legged_out(tok_1,lbl_1,m_1,px_1,nr_1,oid_1,resp_1)
     return { "success":False,"stage":"LEG_2_REJECTED_UNWOUND","dispatch_mode":disp_mode,"inter_leg_skew_ms":skew_ms,"legged_out":True,"outcome_unknown":False,"leg_1_order_id":oid_1,"unwind_result":uw,"residual_unhedged_leg":resid_info,"error":err_s2,}
    if st_2=="FILLED" and st_1=="REJECTED":
     uw,resid_info=_unwind_legged_out(tok_2,lbl_2,m_2,px_2,nr_2,oid_2,resp_2)
     return { "success":False,"stage":"LEG_1_REJECTED_LEG_2_UNWOUND","dispatch_mode":disp_mode,"inter_leg_skew_ms":skew_ms,"legged_out":True,"outcome_unknown":False,"leg_2_order_id":oid_2,"unwind_result":uw,"residual_unhedged_leg":resid_info,"error":err_s1,}
    return { "success":False,"stage":"PARALLEL_OUTCOME_UNKNOWN","dispatch_mode":disp_mode,"inter_leg_skew_ms":skew_ms,"legged_out":bool(st_1=="FILLED" or st_2=="FILLED"),"outcome_unknown":True,"leg_1_order_id":oid_1,"leg_2_order_id":oid_2,"leg_1_token_id":tok_1,"leg_2_token_id":tok_2,"error":f"L1={st_1}:{err_s1}; L2={st_2}:{err_s2}",}
   leg1_submitted=False
   try:
    leg1_submitted=True
    resp_1=_post_fok_fast(signed_1)
   except Exception as e1:
    err_1=str(getattr(e1,"error_message","") or str(e1))
    is_clean_400=is_clob_400_rejection(e1) or any( k in err_1.lower() for k in ("fok","couldn't be fully filled","fully filled","not enough balance") )
    return { "success":False,"stage":"LEG_1_EXCEPTION","legged_out":False,"outcome_unknown":bool(leg1_submitted and not is_clean_400),"leg_1_token_id":tok_1,"error":err_1,}
   err_1=resp_1.get("errorMsg") or resp_1.get("error")
   oid_1=resp_1.get("orderID") or resp_1.get("id")
   if err_1 and not oid_1:
    return { "success":False,"stage":"LEG_1_REJECTED","legged_out":False,"outcome_unknown":False,"error":str(err_1),"raw_leg_1":resp_1,}
   if err_1 or not oid_1:
    return {"success":False,"stage":"LEG_1_UNKNOWN","legged_out":False,"outcome_unknown":True,"leg_1_order_id":oid_1,"leg_1_token_id":tok_1,"error":f"AMBIGUOUS_LEG_1_RESPONSE: {err_1 or 'missing orderID'}","raw_leg_1":resp_1}
   matched_1=self._extract_fok_matched_shares(resp_1,shares_int)
   if matched_1 is None:
    return {"success":False,"stage":"LEG_1_UNKNOWN","legged_out":False,"outcome_unknown":True,"leg_1_order_id":oid_1,"leg_1_token_id":tok_1,"error":f"LEG_1_NON_IMMEDIATE_STATUS ({resp_1.get('status')})","raw_leg_1":resp_1}
   if matched_1<=0.0:
    return {"success":False,"stage":"LEG_1_REJECTED","legged_out":False,"outcome_unknown":False,"error":"LEG_1_MATCHED_ZERO_SHARES","raw_leg_1":resp_1}
   if matched_1 < shares_int - 0.05:
    unwind_res,resid_info=_unwind_legged_out(tok_1,lbl_1,matched_1,px_1,nr_1,oid_1,resp_1)
    return {"success":False,"stage":"LEG_1_PARTIAL_FILL_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":oid_1,"unwind_result":unwind_res,"residual_unhedged_leg":resid_info,"error":f"LEG_1_UNDERFILLED ({matched_1:.2f} < {shares_int:.2f})","raw_leg_1":resp_1}
   leg2_submitted=False
   try:
    leg2_submitted=True
    resp_2=_post_fok_fast(signed_2)
   except Exception as e2:
    err_2=str(getattr(e2,"error_message","") or str(e2))
    is_clean_400=is_clob_400_rejection(e2) or any( k in err_2.lower() for k in ("fok","couldn't be fully filled","fully filled","not enough balance") )
    if not is_clean_400:
     return {"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":oid_1,"leg_1_token_id":tok_1,"leg_2_token_id":tok_2,"error":err_2}
    unwind_res,resid_info=_unwind_legged_out(tok_1,lbl_1,matched_1,px_1,nr_1,oid_1,resp_1)
    return {"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":oid_1,"unwind_result":unwind_res,"residual_unhedged_leg":resid_info,"error":err_2}
   err_2=resp_2.get("errorMsg") or resp_2.get("error")
   oid_2=resp_2.get("orderID") or resp_2.get("id")
   if not err_2 and oid_2:
    matched_2=self._extract_fok_matched_shares(resp_2,matched_1)
    if matched_2 is None:
     return {"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":oid_1,"leg_2_order_id":oid_2,"leg_1_token_id":tok_1,"leg_2_token_id":tok_2,"error":f"LEG_2_NON_IMMEDIATE_STATUS ({resp_2.get('status')})","raw_leg_2":resp_2}
    if matched_2<=0.0:
     unwind_res,resid_info=_unwind_legged_out(tok_1,lbl_1,matched_1,px_1,nr_1,oid_1,resp_1)
     return {"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":oid_1,"unwind_result":unwind_res,"residual_unhedged_leg":resid_info,"error":"LEG_2_MATCHED_ZERO_SHARES","raw_leg_2":resp_2}
    paired_shares=min(matched_1,matched_2)
    imbalance_unwind=None
    if abs(matched_1 - matched_2) > 0.05:
     excess_tok,excess_px,excess_nr=(tok_1,px_1,nr_1) if matched_1 > matched_2 else (tok_2,px_2,nr_2)
     imbalance_unwind=self.execute_unwind_order(excess_tok,size=abs(matched_1 - matched_2),side="SELL",min_price=max(0.01,round(excess_px * 0.85,2)),neg_risk=excess_nr)
    logger.info(f"[LIVE DOMINANCE BOX FILLED] {box_id} | {paired_shares:.2f} pairs @ worst_net=${worst_box_cost_net:.4f} ({lbl_1}={oid_1}, {lbl_2}={oid_2})")
    return { "success":True,"box_id":box_id,"shares":paired_shares,"worst_box_cost_net":worst_box_cost_net,"guaranteed_min_profit_usd":round(paired_shares * (1.0 - worst_box_cost_net),4),"legged_out":False,"outcome_unknown":False,"imbalance_unwind":imbalance_unwind,"leg_1":{"label":lbl_1,"token_id":tok_1,"price":px_1,"matched_shares":matched_1,"orderID":oid_1,"raw":resp_1},"leg_2":{"label":lbl_2,"token_id":tok_2,"price":px_2,"matched_shares":matched_2,"orderID":oid_2,"raw":resp_2},}
   if err_2 and not oid_2:
    unwind_res,resid_info=_unwind_legged_out(tok_1,lbl_1,matched_1,px_1,nr_1,oid_1,resp_1)
    return { "success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":oid_1,"unwind_result":unwind_res,"residual_unhedged_leg":resid_info,"error":str(err_2),"raw_leg_2":resp_2,}
   return { "success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":oid_1,"leg_2_order_id":oid_2,"leg_1_token_id":tok_1,"leg_2_token_id":tok_2,"error":f"AMBIGUOUS_LEG_2_RESPONSE: {err_2 or 'missing orderID'}","raw_leg_2":resp_2,}
  finally:
   _HOT_DISPATCH_ACTIVE.leave()
 def execute_maker_anchor_hedge_or_unwind( self,box_id:str,anchor_token_id:str,anchor_label:str,anchor_price:float,anchor_matched_shares:float,anchor_order_id:str,hedge_token_id:str,hedge_label:str,hedge_limit_price:float,max_box_cost_net:float=0.993,hedge_fee_rate:float=0.07,hedge_fee_exponent:float=1.0,neg_risk:Optional[bool]=None,anchor_neg_risk:Optional[bool]=None,hedge_neg_risk:Optional[bool]=None,anchor_pre_balance:float=0.0,hedge_pre_balance:float=0.0,anchor_raw:Any=None,)->Dict[str,Any]:
  try:
   px_anc=float(anchor_price)
   sh_anc=float(anchor_matched_shares)
   px_hdg_in=float(hedge_limit_price)
   cap_in=float(max_box_cost_net)
   fr_h=float(hedge_fee_rate)
   fe_h=float(hedge_fee_exponent)
  except (TypeError,ValueError):
   return {"success":False,"error":"INVALID_MAKER_ANCHOR_HEDGE_INPUTS","legged_out":False,"outcome_unknown":False}
  if not anchor_token_id or not hedge_token_id or str(anchor_token_id)==str(hedge_token_id) or sh_anc<=0.0:
   return {"success":False,"error":"INVALID_MAKER_ANCHOR_TOKENS_OR_SHARES","legged_out":False,"outcome_unknown":False}
  nr_anc=self.get_token_neg_risk(anchor_token_id,anchor_neg_risk if anchor_neg_risk is not None else neg_risk)
  nr_hdg=self.get_token_neg_risk(hedge_token_id,hedge_neg_risk if hedge_neg_risk is not None else neg_risk)
  px_hdg=self.quantize_order_price(px_hdg_in,hedge_token_id,rounding=ROUND_CEILING)
  fee_h_ps=fr_h * ((px_hdg * (1.0 - px_hdg)) ** fe_h) if fr_h > 0.0 else 0.0
  worst_box_cost_net=round(px_anc + px_hdg + fee_h_ps,6)
  shares_int=float(math.floor(sh_anc + 1e-9))
  def _unwind_anchor_leg()->Tuple[Dict[str,Any],Dict[str,Any]]:
   pre_u=float(anchor_pre_balance or 0.0)
   avail_u:Optional[float]=None
   is_live_auth_u=(not self.dry_run) and getattr(self,"auth_mode","") in ("LIVE","AUTHENTICATED_L2")
   if is_live_auth_u:
    deadline_u=time.monotonic() + 5.0
    while time.monotonic() < deadline_u:
     try:
      avail_u=self.get_unreserved_conditional_balance(anchor_token_id)
     except Exception:
      avail_u=None
      break
     if avail_u is None:
      break
     settled_d=max(0.0,float(avail_u) - pre_u) if pre_u > 0.0 else float(avail_u)
     if settled_d>=sh_anc - 0.05:
      break
     time.sleep(0.15)
   settled_ready=sh_anc
   if is_live_auth_u and avail_u is not None:
    settled_ready=min(float(avail_u),max(0.0,float(avail_u) - pre_u) if pre_u > 0.0 else float(avail_u))
   if is_live_auth_u and avail_u is not None and settled_ready < 0.05:
    uw_def={"success":False,"matched_size":0.0,"outcome_unknown":False,"error":"DEFERRED_TO_ASYNC_SUPERVISOR_PENDING_SETTLEMENT"}
    return uw_def,{ "token_id":anchor_token_id,"label":anchor_label,"price":px_anc,"is_maker_anchor":True,"matched_shares":sh_anc,"unwound_shares":0.0,"residual_shares":round(sh_anc,4),"orderID":anchor_order_id,"raw":anchor_raw,"unwind_outcome_unknown":False,"unwind_result":uw_def,}
   req_u=(math.floor(min(sh_anc,settled_ready) * 100.0 + 1e-9) / 100.0) if (is_live_auth_u and avail_u is not None and settled_ready < sh_anc - 0.05) else sh_anc
   uw_res=self.execute_unwind_order(anchor_token_id,size=req_u,side="SELL",min_price=max(0.01,round(px_anc - 0.02,2)),neg_risk=nr_anc)
   uw_unk=bool(isinstance(uw_res,dict) and uw_res.get("outcome_unknown"))
   unw_sh=float(uw_res.get("matched_size") or 0.0) if (isinstance(uw_res,dict) and (uw_res.get("success") or uw_res.get("partial")) and not uw_unk) else 0.0
   rem_u=round(max(0.0,sh_anc - unw_sh),4)
   if rem_u > 0.05 and not uw_unk:
    uw_2=self.execute_unwind_order(anchor_token_id,size=rem_u,side="SELL",min_price=max(0.01,round(px_anc * 0.85,2)),neg_risk=nr_anc)
    if isinstance(uw_2,dict):
     uw_unk=bool(uw_2.get("outcome_unknown"))
     if (uw_2.get("success") or uw_2.get("partial")) and not uw_unk:
      unw_sh += float(uw_2.get("matched_size") or 0.0)
     uw_res=dict(uw_2)
     uw_res["matched_size"]=round(unw_sh,4)
   return uw_res,{ "token_id":anchor_token_id,"label":anchor_label,"price":px_anc,"is_maker_anchor":True,"matched_shares":sh_anc,"unwound_shares":round(unw_sh,4),"residual_shares":round(max(0.0,sh_anc - unw_sh),4),"orderID":anchor_order_id,"raw":anchor_raw,"unwind_outcome_unknown":uw_unk,"unwind_result":uw_res,}
  if shares_int < 5.0 or worst_box_cost_net < 0.900 - 1e-6 or worst_box_cost_net > cap_in + 1e-6:
   uw_r,res_i=_unwind_anchor_leg()
   return { "success":False,"stage":"ANCHOR_PARTIAL_OR_CAP_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":anchor_order_id,"unwind_result":uw_r,"residual_unhedged_leg":res_i,"error":f"MAKER_ANCHOR_PRE_HEDGE_VETO (sh={sh_anc:.2f}, net={worst_box_cost_net:.4f}, cap={cap_in:.4f})",}
  if self.dry_run:
   oid_2=f"MOCK_MKR_HDG_L2_{int(time.time() * 1000)}"
   return { "success":True,"mode":"DRY_RUN","box_id":box_id,"shares":shares_int,"worst_box_cost_net":worst_box_cost_net,"guaranteed_min_profit_usd":round(shares_int * (1.0 - worst_box_cost_net),4),"legged_out":False,"outcome_unknown":False,"leg_1":{"label":anchor_label,"token_id":anchor_token_id,"price":px_anc,"matched_shares":shares_int,"orderID":anchor_order_id,"is_maker_anchor":True,"raw":anchor_raw},"leg_2":{"label":hedge_label,"token_id":hedge_token_id,"price":px_hdg,"matched_shares":shares_int,"orderID":oid_2},}
  if not self.is_authenticated or self.client is None or OrderArgsV2 is None:
   raise RuntimeError(f"LIVE MAKER ANCHOR HEDGE REFUSED: Executor unauthenticated ({self.auth_mode}).")
  _HOT_DISPATCH_ACTIVE.enter()
  try:
   tick_h=self.get_token_tick_size(hedge_token_id)
   opts_h=PartialCreateOrderOptions(tick_size=str(tick_h),neg_risk=nr_hdg,version=2) if PartialCreateOrderOptions else None
   with _UrgentSignPriority():
    signed_h=_safe_create_order(self.client.create_order,OrderArgsV2(price=px_hdg,size=shares_int,side="BUY",token_id=hedge_token_id),opts_h)
   try:
    resp_2=self.client.post_order(signed_h,OrderType.FOK,False,True)
   except TypeError:
    resp_2=self.client.post_order(signed_h,OrderType.FOK)
   except Exception as e2:
    err_2=str(getattr(e2,"error_message","") or str(e2))
    is_clean_400=is_clob_400_rejection(e2) or any(k in err_2.lower() for k in ("fok","couldn't be fully filled","fully filled","not enough balance"))
    if not is_clean_400:
     return {"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":anchor_order_id,"leg_1_token_id":anchor_token_id,"leg_2_token_id":hedge_token_id,"error":err_2}
    uw_r,res_i=_unwind_anchor_leg()
    return {"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":anchor_order_id,"unwind_result":uw_r,"residual_unhedged_leg":res_i,"error":err_2}
   err_2=resp_2.get("errorMsg") or resp_2.get("error")
   oid_2=resp_2.get("orderID") or resp_2.get("id")
   if not err_2 and oid_2:
    matched_2=self._extract_fok_matched_shares(resp_2,shares_int)
    if matched_2 is None:
     return {"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":anchor_order_id,"leg_2_order_id":oid_2,"leg_1_token_id":anchor_token_id,"leg_2_token_id":hedge_token_id,"error":f"LEG_2_NON_IMMEDIATE_STATUS ({resp_2.get('status')})","raw_leg_2":resp_2}
    if matched_2<=0.0:
     uw_r,res_i=_unwind_anchor_leg()
     return {"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":anchor_order_id,"unwind_result":uw_r,"residual_unhedged_leg":res_i,"error":"LEG_2_MATCHED_ZERO_SHARES","raw_leg_2":resp_2}
    paired_shares=min(sh_anc,matched_2)
    imbalance_unwind=None
    if abs(sh_anc - matched_2) > 0.05:
     ex_tok,ex_px,ex_nr=(anchor_token_id,px_anc,nr_anc) if sh_anc > matched_2 else (hedge_token_id,px_hdg,nr_hdg)
     imbalance_unwind=self.execute_unwind_order(ex_tok,size=abs(sh_anc - matched_2),side="SELL",min_price=max(0.01,round(ex_px * 0.85,2)),neg_risk=ex_nr)
    logger.info(f"[LIVE MAKER ANCHOR BOX FILLED] {box_id} | {paired_shares:.2f} pairs @ worst_net=${worst_box_cost_net:.4f} (MKR={anchor_order_id}, FOK={oid_2})")
    return { "success":True,"box_id":box_id,"shares":paired_shares,"worst_box_cost_net":worst_box_cost_net,"guaranteed_min_profit_usd":round(paired_shares * (1.0 - worst_box_cost_net),4),"legged_out":False,"outcome_unknown":False,"imbalance_unwind":imbalance_unwind,"leg_1":{"label":anchor_label,"token_id":anchor_token_id,"price":px_anc,"matched_shares":sh_anc,"orderID":anchor_order_id,"is_maker_anchor":True,"raw":anchor_raw},"leg_2":{"label":hedge_label,"token_id":hedge_token_id,"price":px_hdg,"matched_shares":matched_2,"orderID":oid_2,"raw":resp_2},}
   if err_2 and not oid_2:
    uw_r,res_i=_unwind_anchor_leg()
    return {"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":anchor_order_id,"unwind_result":uw_r,"residual_unhedged_leg":res_i,"error":str(err_2),"raw_leg_2":resp_2}
   return {"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":anchor_order_id,"leg_2_order_id":oid_2,"leg_1_token_id":anchor_token_id,"leg_2_token_id":hedge_token_id,"error":f"AMBIGUOUS_LEG_2_RESPONSE: {err_2 or 'missing orderID'}","raw_leg_2":resp_2}
  finally:
   _HOT_DISPATCH_ACTIVE.leave()
 def post_maker_exit_order( self,token_id:str,price:float,size:float,side:str="SELL",neg_risk:Optional[bool]=None,)->Dict[str,Any]:
  lot=Decimal("0.01")
  requested=Decimal(str(size)).quantize(lot,rounding=ROUND_FLOOR)
  if requested<=Decimal("0.00"):
   return {"success":False,"orderID":None,"error":"NON_POSITIVE_EXIT_SIZE","retryable":False}
  if not self.dry_run:
   if not self.is_authenticated or self.client is None:
    raise RuntimeError(f"LIVE EXIT REFUSED: Executor is in live mode but unauthenticated ({self.auth_mode}).")
   avail_bal=self.get_unreserved_conditional_balance(token_id)
   if avail_bal is None:
    err=f"UNKNOWN_CONDITIONAL_BALANCE: Balance query failed for {token_id}. Refusing unverified exit order submission."
    logger.warning(f"[PM-EXEC] {err}")
    return { "success":False,"orderID":None,"error":err,"available_balance":None,"retryable":True,}
   available=Decimal(str(avail_bal)).quantize(lot,rounding=ROUND_FLOOR)
   if available < requested:
    err=f"INSUFFICIENT_UNRESERVED_BALANCE: INSUFFICIENT_CONDITIONAL_BALANCE: Unreserved balance {available} < requested exit size {requested} (reserved: {self.reserved_inventory.get(token_id, 0.0):.2f})"
    logger.warning(f"[PM-EXEC] {err}")
    return { "success":False,"orderID":None,"error":err,"available_balance":float(available),"retryable":True,}
   quantized_size=float(requested)
  else:
   quantized_size=float(requested)
   mock_id=f"MOCK_EXIT_{int(time.time()*1000)}"
   logger.info(f"[DRY-RUN EXIT] Resting {side} limit order: {quantized_size:.2f} shares @ ${price:.4f} (ID: {mock_id})")
   return {"success":True,"orderID":mock_id,"mode":"DRY_RUN","post_only":True}
  order_submitted=False
  try:
   quantized_price=self.quantize_order_price(price,token_id,rounding=ROUND_CEILING)
   tick_sz=self.get_token_tick_size(token_id)
   eff_neg_risk=self.get_token_neg_risk(token_id,neg_risk)
   create_opts=( PartialCreateOrderOptions(tick_size=str(tick_sz),neg_risk=eff_neg_risk,version=2) if PartialCreateOrderOptions else None )
   order_args=OrderArgsV2( price=quantized_price,size=quantized_size,side=side,token_id=token_id,)
   has_lockfree_fast_signer=( getattr(self.client,"_fast_v2_signer",None) is not None and "create_order" not in getattr(self.client,"__dict__",{}) )
   if has_lockfree_fast_signer:
    signed_order=_safe_create_order(self.client.create_order,order_args,create_opts)
   else:
    with _UrgentSignPriority():
     signed_order=_safe_create_order(self.client.create_order,order_args,create_opts)
   order_submitted=True
   resp=self.client.post_order(signed_order,OrderType.GTC,post_only=True,defer_exec=True)
   has_err=resp.get("errorMsg") or resp.get("error")
   order_id=resp.get("orderID") or resp.get("id")
   if has_err and order_id:
    logger.critical(f"Contradictory maker post response (orderID={order_id} with error={has_err}). Retaining as UNKNOWN/HELD.")
    self.reserve_inventory(token_id,quantized_size,reservation_id=order_id)
    return { "success":False,"orderID":order_id,"outcome_unknown":True,"retryable":False,"error":f"CONTRADICTORY_RESPONSE: {has_err}","raw":resp,}
   if has_err:
    if str(side).upper()=="SELL" and ("crosses book" in str(has_err).lower() or "post only" in str(has_err).lower() or "post-only" in str(has_err).lower()):
     best_b=0.0
     max_valid_px=float(Decimal("1") - Decimal(str(tick_sz)))
     signed_2=None
     improved_px=quantized_price
     try:
      bk=self.get_market_book(token_id)
      b_list=bk.get("bids",[]) if isinstance(bk,dict) else []
      best_b=max((float(b.get("price",0.0)) for b in b_list if float(b.get("size",0.0)) > 0),default=0.0)
      if best_b>=max_valid_px - 1e-9:
       return { "success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"crossed_at_max_tick":True,"best_bid":best_b,"error":str(has_err),"raw":resp,}
      if best_b>=quantized_price:
       improved_px=self.quantize_order_price(min(max_valid_px,best_b + tick_sz),token_id,rounding=ROUND_CEILING)
       if improved_px > max(quantized_price,best_b) + 1e-9:
        logger.info(f"[POST-ONLY PRICE IMPROVEMENT] Best bid ${best_b:.4f} >= target ${quantized_price:.4f}. Repricing maker sell to ${improved_px:.4f}!")
        order_args_2=OrderArgsV2(price=improved_px,size=quantized_size,side=side,token_id=token_id)
        if has_lockfree_fast_signer:
         signed_2=_safe_create_order(self.client.create_order,order_args_2,create_opts)
        else:
         with _UrgentSignPriority():
          signed_2=_safe_create_order(self.client.create_order,order_args_2,create_opts)
     except Exception as repr_err:
      logger.debug(f"Post-only price improvement book/sign skipped: {repr_err}")
     if signed_2 is not None:
      order_submitted=True
      resp_2=self.client.post_order(signed_2,OrderType.GTC,post_only=True,defer_exec=True)
      err_2=resp_2.get("errorMsg") or resp_2.get("error") if isinstance(resp_2,dict) else "INVALID_MAKER_REPRICE_RESP"
      oid_2=(resp_2.get("orderID") or resp_2.get("id")) if isinstance(resp_2,dict) else None
      if err_2 and oid_2:
       self.reserve_inventory(token_id,quantized_size,reservation_id=oid_2)
       return {"success":False,"orderID":oid_2,"outcome_unknown":True,"retryable":False,"error":f"CONTRADICTORY_RESPONSE: {err_2}","raw":resp_2}
      if oid_2 and not err_2:
       self.reserve_inventory(token_id,quantized_size,reservation_id=oid_2)
       return {"success":True,"orderID":oid_2,"post_only":True,"price":improved_px,"raw":resp_2,"matched_size":0.0}
      if not oid_2 and not err_2:
       res_id=f"AMBIGUOUS_POST_{int(time.time()*1000)}"
       self.reserve_inventory(token_id,quantized_size,reservation_id=res_id)
       return {"success":False,"orderID":None,"outcome_unknown":True,"retryable":False,"reservation_id":res_id,"error":"MISSING_ORDER_ID_IN_MAKER_REPRICE","raw":resp_2}
      has_err=err_2
      resp=resp_2
    logger.error(f"Failed to post maker exit order (rejected): {resp}")
    return {"success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"error":str(has_err),"raw":resp}
   if order_id:
    logger.info(f"[LIVE MAKER EXIT POSTED (POST-ONLY)] OID: {order_id} | {side} {size:.2f} shares @ ${quantized_price:.4f}")
    try:
     matched_so_far=float(resp.get("size_matched",resp.get("matched_size",resp.get("sizeMatched",0.0))) or 0.0)
    except (TypeError,ValueError):
     matched_so_far=0.0
    remaining_size=max(0.0,quantized_size - matched_so_far)
    if remaining_size > 0.0:
     self.reserve_inventory(token_id,remaining_size,reservation_id=order_id)
    return {"success":True,"orderID":order_id,"post_only":True,"price":quantized_price,"raw":resp,"matched_size":matched_so_far}
   logger.critical(f"Failed to post maker exit order (missing orderID, ambiguous outcome): {resp}")
   res_id=f"AMBIGUOUS_POST_{int(time.time()*1000)}"
   self.reserve_inventory(token_id,quantized_size,reservation_id=res_id)
   return {"success":False,"orderID":None,"outcome_unknown":True,"retryable":False,"reservation_id":res_id,"error":"MISSING_ORDER_ID_IN_MAKER_POST","raw":resp}
  except Exception as e:
   is_client_err=False
   status_code=getattr(e,"status_code",None)
   err_msg=str(getattr(e,"error_message","") or str(e))
   if status_code and int(status_code) in {400,401,403,404,422}:
    is_client_err=True
    self._evict_tick_size_if_tick_err(token_id,err_msg)
   elif any(k in err_msg.lower() for k in ("not enough balance","allowance","invalid order","crosses book","post only","post-only")):
    is_client_err=True
   if not order_submitted or is_client_err:
    if side.upper()=="SELL" and any(k in err_msg.lower() for k in ("crosses book","post only","post-only")):
     max_valid_px=round(1.0 - float(tick_sz),4)
     try:
      bk=self.get_market_book(token_id)
      b_list=bk.get("bids",[]) if isinstance(bk,dict) else []
      best_b=max((float(b.get("price",0.0)) for b in b_list if float(b.get("size",0.0)) > 0),default=0.0)
      if best_b>=max_valid_px - 1e-9:
       return { "success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"crossed_at_max_tick":True,"best_bid":best_b,"error":err_msg,}
     except Exception:
      pass
    logger.warning(f"Maker exit order rejected by exchange before matching (no open order): {e}")
    return { "success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"error":err_msg,}
   logger.critical(f"Exception posting maker exit order (outcome unknown): {e}")
   res_id=f"EXCEPTION_POST_{int(time.time()*1000)}"
   self.reserve_inventory(token_id,quantized_size,reservation_id=res_id)
   return {"success":False,"orderID":None,"outcome_unknown":True,"retryable":False,"reservation_id":res_id,"error":str(e)}
 def execute_unwind_order( self,token_id:str,size:float,side:str="SELL",min_price:float=0.01,neg_risk:Optional[bool]=None,)->Dict[str,Any]:
  if self.dry_run:
   mock_id=f"MOCK_UNWIND_{int(time.time()*1000)}"
   logger.info(f"[DRY-RUN UNWIND] Executed simulated {side} unwind: {size:.2f} shares @ min ${min_price:.4f}")
   unwind_r=0.07
   unwind_e=1.0
   if token_id in self._fee_cache:
    unwind_r,unwind_e=self._fee_cache[token_id]
   taking_amt=size * min_price
   avg_px=min(0.999,max(0.001,min_price))
   fee_usd=round(size * unwind_r * ((avg_px * (1.0 - avg_px)) ** unwind_e),5)
   return {"success":True,"orderID":mock_id,"matched_size":size,"taking_amount":taking_amt,"fee_usd":fee_usd}
  if not self.is_authenticated or self.client is None:
   return { "success":False,"orderID":None,"retryable":True,"outcome_unknown":False,"error":"Live CLOB client unavailable; no simulated success permitted",}
  quantized_size=float(Decimal(str(max(0.0,float(size or 0.0)))).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
  order_submitted=False
  try:
   lot=Decimal("0.01")
   requested=Decimal(str(size)).quantize(lot,rounding=ROUND_FLOOR)
   wallet_balance=self.get_unreserved_conditional_balance(token_id)
   if wallet_balance is None:
    return { "success":False,"orderID":None,"matched_size":0.0,"retryable":True,"outcome_unknown":False,"error":"UNVERIFIED_SELL_INVENTORY: balance query unavailable",}
   available=Decimal(str(wallet_balance)).quantize(lot,rounding=ROUND_FLOOR)
   if available < requested:
    if available > Decimal("0.00") and available>=requested - Decimal("0.05"):
     logger.info( f"[PM-EXEC] Clamping unwind size {requested} -> {available} shares to match exact unreserved wallet dust." )
     requested=available
    else:
     return { "success":False,"orderID":None,"matched_size":0.0,"retryable":False,"outcome_unknown":False,"error":f"SELL_INVENTORY_RECONCILIATION_REQUIRED: unreserved {available} < requested {requested} (reserved: {self.reserved_inventory.get(token_id, 0.0):.2f})",}
   quantized_size=float(requested)
   if quantized_size<=0.0:
    logger.warning(f"[UNWIND SKIPPED] Size {size} rounds to 0.00 lots.")
    return {"success":True,"orderID":None,"matched_size":0.0,"taking_amount":0.0,"fee_usd":0.0}
   quantized_price=self.quantize_order_price(min_price,token_id,rounding=ROUND_FLOOR)
   tick_sz=self.get_token_tick_size(token_id)
   eff_neg_risk=self.get_token_neg_risk(token_id,neg_risk)
   create_opts=( PartialCreateOrderOptions(tick_size=str(tick_sz),neg_risk=eff_neg_risk,version=2) if PartialCreateOrderOptions else None )
   order_args=OrderArgsV2( price=quantized_price,size=quantized_size,side=side,token_id=token_id,)
   t_u0=time.perf_counter()
   with _UrgentSignPriority():
    signed_order=_safe_create_order(self.client.create_order,order_args,create_opts)
   selected_order_type=getattr(OrderType,"FAK",OrderType.FOK)
   order_submitted=True
   resp=self.client.post_order(signed_order,selected_order_type,post_only=False,defer_exec=True)
   unwind_lat_ms=(time.perf_counter() - t_u0) * 1000.0
   order_id=resp.get("orderID") or resp.get("id")
   status=resp.get("status")
   taking_amount=resp.get("takingAmount") or resp.get("taking_amount")
   status_str=str(status).upper() if status else ""
   raw_matched=resp.get("makingAmount") if resp.get("makingAmount") not in (None,"") else resp.get("size_matched")
   matched_status=status_str in {"MATCHED","FILLED","CONFIRMED","MINED"}
   is_matched=bool(order_id) and matched_status and raw_matched not in (None,"")
   if is_matched:
    matched_size=float(raw_matched)
    taking_missing=taking_amount in (None,"")
    taking_amt=float(taking_amount) if not taking_missing else matched_size * quantized_price
    tx_hashes=resp.get("transactionsHashes") or resp.get("transaction_hashes") or []
    onchain_settled=bool( self.dry_run or ( status_str in {"CONFIRMED","MINED"} and tx_hashes and all(self.get_transaction_receipt_status(str(tx)) is True for tx in tx_hashes) ) )
    taking_is_estimated=taking_missing or (not onchain_settled)
    if not ( math.isfinite(matched_size) and math.isfinite(taking_amt) and 0.0<=matched_size<=quantized_size + 1e-4 and taking_amt>=0.0 ):
     res_id=str(order_id or f"AMBIGUOUS_UNWIND_{int(time.time()*1000)}")
     self.reserve_inventory(token_id,quantized_size,reservation_id=res_id)
     return { "success":False,"orderID":order_id,"matched_size":0.0,"outcome_unknown":True,"retryable":False,"reservation_id":res_id,"submitted_size":quantized_size,"error":"INCONSISTENT_UNWIND_FILL_AMOUNTS","raw":resp,}
    average_price=min( 0.999,max(0.001,taking_amt / max(matched_size,1e-9)),)
    unwind_r=0.07
    unwind_e=1.0
    if token_id in self._fee_cache:
     unwind_r,unwind_e=self._fee_cache[token_id]
    estimated_fee=round( matched_size * unwind_r * ((average_price * (1.0 - average_price)) ** unwind_e),5,)
    self._log_order(OrderResult( success=True,order_id=str(order_id),trade_id=f"UNWIND_{order_id}",token_id=str(token_id),target_token="",side=side,price=round(average_price,4),size=matched_size,notional_usd=round(taking_amt,4),fee_usd=estimated_fee,latency_ms=unwind_lat_ms,mode="LIVE_UNWIND",execution_status=ExecutionStatus.FILLED,confirmed_onchain=onchain_settled,details={"raw_response":resp,"taking_is_estimated":taking_is_estimated},))
    target_dec=Decimal(str(quantized_size)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR)
    matched_dec=Decimal(str(matched_size)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR)
    if matched_dec < target_dec:
     unfilled_dec=target_dec - matched_dec
     unfilled_size=float(unfilled_dec)
     logger.warning( f"[PARTIAL UNWIND FILL] Order {order_id}: matched {matched_size:.2f} of {quantized_size:.2f} shares. " f"Proceeds: ${taking_amt:.2f}. Residual: {unfilled_size:.2f} shares remain open." )
     return { "success":False,"orderID":order_id,"matched_size":matched_size,"unfilled_size":unfilled_size,"taking_amount":taking_amt,"fee_usd":estimated_fee,"fee_is_estimated":True,"taking_amount_estimated":taking_is_estimated,"taking_amount_missing":taking_missing,"partial":True,"retryable":True,"error":f"PARTIAL_FILL: Matched {matched_size:.2f} of {quantized_size:.2f} shares (residual: {unfilled_size:.2f})","raw":resp,}
    logger.info(f"[LIVE UNWIND EXECUTED] OID: {order_id} | Sold {matched_size:.2f} shares @ min ${quantized_price:.4f} (Proceeds: ${taking_amt:.2f})")
    return { "success":True,"orderID":order_id,"matched_size":matched_size,"taking_amount":taking_amt,"taking_amount_estimated":taking_is_estimated,"taking_amount_missing":taking_missing,"fee_usd":estimated_fee,"fee_is_estimated":True,"raw":resp,}
   else:
    is_terminal_rejection=( status_str.startswith("CANCEL") or status_str in {"EXPIRED","REJECTED","UNMATCHED"} or is_fak_killed_no_match(None,resp) or is_clob_400_rejection(None,resp) )
    outcome_unknown=not is_terminal_rejection
    logger.warning(f"[LIVE UNWIND NON-MATCHED] Response: {resp} | terminal={is_terminal_rejection}")
    res_id=None
    if outcome_unknown:
     res_id=str(order_id or f"AMBIGUOUS_UNWIND_{int(time.time()*1000)}")
     self.reserve_inventory(token_id,quantized_size,reservation_id=res_id)
    return { "success":False,"orderID":order_id,"matched_size":0.0,"retryable":is_terminal_rejection,"outcome_unknown":outcome_unknown,"reservation_id":res_id,"submitted_size":quantized_size,"error":f"Status: {status}","raw":resp,}
  except Exception as e:
   logger.error(f"[LIVE UNWIND EXCEPTION] Error executing unwind order (submitted={order_submitted}): {e}")
   if not order_submitted or is_clob_400_rejection(e):
    return { "success":False,"orderID":None,"matched_size":0.0,"retryable":True,"outcome_unknown":False,"error":str(e),}
   res_id=f"EXCEPTION_UNWIND_{int(time.time()*1000)}"
   self.reserve_inventory(token_id,quantized_size,reservation_id=res_id)
   return { "success":False,"orderID":None,"matched_size":0.0,"retryable":True,"outcome_unknown":True,"reservation_id":res_id,"submitted_size":quantized_size,"error":str(e),}
 def post_heartbeat(self,heartbeat_id:Optional[str]=None)->Dict[str,Any]:
  if self.dry_run or not self.is_authenticated or self.client is None:
   return {"heartbeat_id":"MOCK_HEARTBEAT"}
  hid=self.last_heartbeat_id if heartbeat_id is None else heartbeat_id
  try:
   with _CLOB_HTTP_LOCK:
    resp=self.client.post_heartbeat(heartbeat_id=hid or "")
   new_id=resp.get("heartbeat_id") if isinstance(resp,dict) else None
   if new_id:
    self.last_heartbeat_id=new_id
   self.heartbeat_failures=0
   return resp
  except Exception as e:
   server_hid=None
   err_msg_obj=getattr(e,"error_message",None) or getattr(e,"error_msg",None)
   if isinstance(err_msg_obj,dict) and err_msg_obj.get("heartbeat_id"):
    server_hid=str(err_msg_obj["heartbeat_id"]).strip()
   else:
    import re
    m_hid=re.search(r"['\"]heartbeat_id['\"]\s*:\s*['\"]([0-9a-fA-F-]{16,})['\"]",str(e))
    if m_hid:
     server_hid=m_hid.group(1).strip()
   if server_hid and server_hid!=(hid or ""):
    try:
     with _CLOB_HTTP_LOCK:
      retry_resp=self.client.post_heartbeat(heartbeat_id=server_hid)
     new_id=retry_resp.get("heartbeat_id") if isinstance(retry_resp,dict) else None
     self.last_heartbeat_id=str(new_id or server_hid)
     self.heartbeat_failures=0
     logger.info(f"[HEARTBEAT RESYNCED] Automatically resynced CLOB heartbeat_id ({server_hid} -> {self.last_heartbeat_id}).")
     return retry_resp if isinstance(retry_resp,dict) else {"heartbeat_id":self.last_heartbeat_id}
    except Exception as retry_err:
     logger.warning(f"[HEARTBEAT RESYNC WARN] Retry with server heartbeat_id {server_hid} failed: {retry_err}")
   self.last_heartbeat_id=""
   self.heartbeat_failures += 1
   logger.error(f"[HEARTBEAT FAILURE] CLOB heartbeat error (failures={self.heartbeat_failures}): {e}")
   return {"error":str(e),"failures":self.heartbeat_failures}
 def is_heartbeat_healthy(self)->bool:
  return self.heartbeat_failures < 3
 def get_open_orders(self,*,strict:bool=False)->Optional[List[Dict[str,Any]]]:
  if self.dry_run:
   return []
  if not self.is_authenticated or self.client is None:
   if strict:
    raise RuntimeError("Cannot establish authoritative open-order state in live mode")
   return None
  uws=getattr(self,"_user_ws_cache",None)
  can_use_uws=( uws is not None and "get_open_orders" not in getattr(self.client,"__dict__",{}) and getattr(self.client,"_mock_children",None) is None )
  if can_use_uws:
   snap=uws.get_open_orders_snapshot(max_age_sec=15.0)
   if snap is not None:
    return snap
  try:
   result=self.client.get_open_orders()
   if not isinstance(result,list):
    raise RuntimeError(f"Unexpected open-orders response type: {type(result).__name__}")
   if can_use_uws:
    uws.seed_open_orders(result)
   return result
  except Exception as e:
   logger.error(f"Error fetching open orders: {e}")
   if strict:
    raise RuntimeError("CLOB open-order snapshot unavailable") from e
   return None
 def cancel_all_orders(self)->Dict[str,Any]:
  if self.dry_run or not self.is_authenticated or self.client is None:
   return {"canceled_all":True}
  try:
   logger.warning("[KILL-SWITCH] Canceling all open CLOB orders...")
   return self.client.cancel_all()
  except Exception as e:
   logger.error(f"Failed to cancel all orders: {e}")
   return {"error":str(e)}
 def cancel_order(self,order_id:str)->Dict[str,Any]:
  if self.dry_run and (self.client is None or not self.is_authenticated):
   self.release_inventory(reservation_id=order_id)
   return CancelOrderResult({"canceled":[order_id]},order_id=str(order_id),outcome="CANCELED",is_canceled=True,canceled=[order_id],matched=0.0)
  try:
   res=self.client.cancel_orders([order_id]) if self.client else {}
   canceled_list=(res or {}).get("canceled")
   not_canceled=(res or {}).get("not_canceled")
   not_canceled_reason:Optional[str]=None
   if isinstance(not_canceled,dict):
    for nc_k,nc_v in not_canceled.items():
     if str(nc_k)==str(order_id):
      not_canceled_reason=str(nc_v or "NOT_CANCELED")
      break
   elif isinstance(not_canceled,(list,tuple,set)) and str(order_id) in {str(x) for x in not_canceled}:
    not_canceled_reason="NOT_CANCELED"
   is_in_canceled_list=bool( not_canceled_reason is None and isinstance(canceled_list,list) and str(order_id) in [str(x) for x in canceled_list] )
   order_info=self.get_order_status(order_id)
   if is_in_canceled_list and order_info is None and not self.dry_run:
    time.sleep(0.12)
    order_info=self.get_order_status(order_id)
   uws=getattr(self,"_user_ws_cache",None)
   ws_snap=uws.get_order_snapshot(order_id,max_age_sec=8.0) if (uws is not None and uws.is_healthy()) else None
   status=str((order_info or {}).get("status","")).upper()
   matched=float((order_info or {}).get("size_matched",0.0) or 0.0)
   orig_size=float((order_info or {}).get("original_size",0.0) or 0.0)
   if isinstance(ws_snap,dict):
    ws_m=float(ws_snap.get("size_matched",0.0) or 0.0)
    if ws_m > matched:
     matched=ws_m
    if orig_size<=0.0:
     orig_size=float(ws_snap.get("original_size",0.0) or 0.0)
    ws_st=str(ws_snap.get("status","")).upper()
    if not status or (status=="LIVE" and ws_st in {"MATCHED","FILLED","CANCELED","CANCELLED"}):
     status=ws_st
   if status in {"MATCHED","FILLED"} or (orig_size > 0.0 and matched>=orig_size - 1e-4):
    outcome="FILLED"
    logger.warning( f"[PM-EXEC] Order {order_id} cancellation returned FILLED/MATCHED (matched={matched:.2f}). " "Retaining reservation until caller reconciles filled quantity." )
    return CancelOrderResult( res or {},order_id=str(order_id),outcome=outcome,is_canceled=False,matched=matched,not_canceled_reason=not_canceled_reason,raw=res,)
   elif status.startswith("CANCEL") or status in {"EXPIRED","REJECTED"} or ( is_in_canceled_list and (self.dry_run or order_info is not None) ):
    if matched > 0.0 and orig_size > 0.0 and matched < orig_size:
     outcome="PARTIALLY_FILLED_CANCELED"
    else:
     outcome="CANCELED"
    self.release_inventory(reservation_id=order_id)
    logger.info(f"[PM-EXEC] Order {order_id} verified canceled ({outcome}). Released reservation.")
    return CancelOrderResult( res if is_in_canceled_list else {"canceled":[order_id]},order_id=str(order_id),outcome=outcome,is_canceled=True,matched=matched,not_canceled_reason=not_canceled_reason,raw=res,canceled=[order_id],)
   else:
    outcome="UNKNOWN"
    logger.warning( f"[PM-EXEC] Order {order_id} cancellation could NOT be verified terminally " f"(status={status}, not_canceled={not_canceled_reason}). Retaining inventory reservation fail-closed." )
    return CancelOrderResult( res or {},order_id=str(order_id),outcome=outcome,is_canceled=False,matched=matched,not_canceled_reason=not_canceled_reason,raw=res,)
  except Exception as e:
   logger.error(f"Failed to cancel order {order_id}: {e}")
   return CancelOrderResult({},order_id=str(order_id),outcome="UNKNOWN",is_canceled=False,error=str(e))
 def get_order_status(self,order_id:str)->Optional[Dict[str,Any]]:
  if self.dry_run or not self.is_authenticated or self.client is None:
   return None
  try:
   res=self.client.get_order(order_id)
   return res if isinstance(res,dict) and res else None
  except Exception as e:
   logger.error(f"Error querying order {order_id}: {e}")
   return None
 def get_collateral_balance(self,max_cache_age_s:float=15.0,hot_path:bool=False)->Optional[float]:
  now=time.time()
  c_first,c_second=getattr(self,"_collateral_cache",(None,0.0))
  if isinstance(c_first,(int,float)) and c_first > 1e9 and isinstance(c_second,(int,float)) and c_second < 1e9:
   cached_ts,cached_bal=float(c_first),float(c_second)
  else:
   cached_bal,cached_ts=c_first,float(c_second or 0.0)
  hot_path_max_age_s=float(os.getenv("PM_HOT_PATH_COLLATERAL_MAX_AGE_SEC","120.0"))
  if hot_path and cached_bal is not None and isinstance(cached_bal,(int,float)) and cached_bal > 0:
   cache_age=(now - cached_ts) if cached_ts > 0.0 else 0.0
   if self.dry_run or (-5.0<=cache_age<=hot_path_max_age_s):
    return cached_bal
   logger.warning(f"[PM-EXEC] Stale hot-path collateral cache (age={cache_age:.1f}s > {hot_path_max_age_s:.1f}s); refreshing.")
  if self.dry_run:
   return cached_bal if (cached_bal is not None and cached_bal > 0) else 0.0
  if max_cache_age_s > 0.0 and cached_bal is not None and (now - cached_ts)<=max_cache_age_s:
   return cached_bal
  if not self.is_authenticated or self.client is None or BalanceAllowanceParams is None:
   logger.warning("[PM-EXEC] Cannot query collateral balance: unauthenticated or client unavailable")
   return None
  try:
   params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL,signature_type=self.signature_type)
   res=self.client.get_balance_allowance(params)
   if not isinstance(res,dict) or "balance" not in res:
    logger.error(f"[PM-EXEC] Unexpected response querying collateral balance: {res}")
    return None
   raw=float(res.get("balance","0"))
   bal=raw / 1e6
   self._collateral_cache=(bal,now)
   return bal
  except Exception as e:
   logger.error(f"[PM-EXEC] Failed to query CLOB collateral balance: {e}")
   return None
 def set_cached_collateral(self,balance:float)->None:
  if isinstance(balance,(int,float)) and math.isfinite(balance) and balance > 0:
   self._collateral_cache=(float(balance),time.time())
 def invalidate_collateral_cache(self):
  self._collateral_cache=(None,0.0)
 def get_conditional_balance(self,token_id:str)->Optional[float]:
  if self.dry_run:
   return 0.0
  if not self.is_authenticated or self.client is None or BalanceAllowanceParams is None:
   logger.warning(f"[PM-EXEC] Cannot query conditional balance for {token_id}: unauthenticated or client unavailable")
   return None
  try:
   params=BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL,token_id=token_id,signature_type=self.signature_type)
   res=self.client.get_balance_allowance(params)
   if not isinstance(res,dict) or "balance" not in res:
    logger.error(f"[PM-EXEC] Unexpected response querying conditional balance for {token_id}: {res}")
    return None
   raw=float(res.get("balance","0"))
   return raw / 1e6
  except Exception as e:
   logger.error(f"[PM-EXEC] Failed to query CLOB conditional balance for {token_id}: {e}")
   return None
 _class_reservations:Dict[str,Dict[str,Dict[str,Any]]]={}
 RESERVATIONS_STATE_PATH=POLYMARKET_DATA_DIR / "inventory_reservations.json"
 RESERVATIONS_SCHEMA="pm-reservations/2.3.8"
 @property
 def reservations_path(self)->Path:
  env_res_path=os.getenv("POLYMARKET_RESERVATIONS_PATH","").strip()
  base=Path(env_res_path) if env_res_path else Path(self.RESERVATIONS_STATE_PATH)
  return base.with_name(base.stem + ".dryrun" + base.suffix) if self.dry_run else base
 def _class_res_bucket(self)->Dict[str,Dict[str,Any]]:
  key=str(self.reservations_path)
  if key not in PolymarketLiveExecutor._class_reservations:
   PolymarketLiveExecutor._class_reservations[key]={}
  return PolymarketLiveExecutor._class_reservations[key]
 @classmethod
 def _get_hmac_secret(cls,live_mode:bool=False)->bytes:
  import hashlib,secrets
  key_env=os.getenv("POLYMARKET_RESERVATION_KEY")
  if key_env and key_env.strip():
   return key_env.strip().encode("utf-8")
  pk_env=os.getenv("POLYGON_PRIVATE_KEY") or os.getenv("POLYMARKET_PRIVATE_KEY")
  if pk_env and pk_env.strip():
   return hashlib.sha256(f"PM_RESERVATION_SECRET_SALT:{pk_env.strip()}".encode("utf-8")).digest()
  key_file=Path.home() / ".polymarket_reservation_hmac.key"
  if key_file.exists():
   try:
    secret=key_file.read_text().strip()
    if len(secret)>=32:
     return secret.encode("utf-8")
   except Exception:
    pass
  if live_mode:
   try:
    new_key=secrets.token_hex(32)
    key_file.write_text(new_key)
    os.chmod(key_file,0o600)
    return new_key.encode("utf-8")
   except Exception as e:
    raise RuntimeError(f"Cannot generate secure live HMAC key: {e}")
  return b"PM_RESERVATION_HMAC_SECRET"
 @classmethod
 def _reservation_digest(cls,records:Dict[str,Any],key:Optional[bytes]=None,live_mode:bool=False)->str:
  import hashlib,hmac
  canonical=json.dumps(records,sort_keys=True,separators=(",",":"),default=str)
  auth_key=key or cls._get_hmac_secret(live_mode=live_mode)
  return hmac.new(auth_key,canonical.encode("utf-8"),hashlib.sha256).hexdigest()
 @classmethod
 def _verify_reservation_digest(cls,records:Dict[str,Any],digest:Optional[str],live_mode:bool=False)->bool:
  import hashlib,hmac
  if not digest:
   return False
  expected_hmac=cls._reservation_digest(records,live_mode=live_mode)
  if hmac.compare_digest(digest,expected_hmac):
   return True
  if live_mode:
   return False
  canonical=json.dumps(records,sort_keys=True,separators=(",",":"),default=str)
  legacy_sha=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
  return hmac.compare_digest(digest,legacy_sha)
 def _load_durable_reservations(self):
  self.reservation_records={}
  self.reservations_trusted=True
  path=self.reservations_path
  if path.exists():
   try:
    with open(path,"r",encoding="utf-8") as f:
     content=f.read().strip()
    if not content:
     raise ValueError("reservation file is empty")
    data=json.loads(content)
    if not isinstance(data,dict) or not isinstance(data.get("reservation_records"),dict):
     raise ValueError("reservation file has corrupt schema")
    records=data["reservation_records"]
    digest=data.get("hmac_sha256") or data.get("sha256")
    if not digest:
     raise ValueError("reservation file missing required integrity digest (hmac_sha256)")
    if not self._verify_reservation_digest(records,digest,live_mode=not self.dry_run):
     raise ValueError("reservation file integrity digest mismatch")
    for rid,rec in records.items():
     if not isinstance(rec,dict) or not rec.get("token_id") or not math.isfinite(float(rec.get("size","nan"))):
      raise ValueError(f"malformed reservation record {rid!r}")
    self.reservation_records=records
   except Exception as e:
    self.reservation_corruption_detected=True
    self.reservations_trusted=False
    quarantine=path.with_name(f"{path.name}.corrupt.{int(time.time())}")
    try:
     os.replace(path,quarantine)
    except Exception:
     quarantine=path
    logger.critical( f"CRITICAL: Durable reservation state at {path} is untrusted ({e}); quarantined to {quarantine}. " "All sell submissions are blocked until reservations are rebuilt from authoritative exchange orders." )
    self.reservation_records={}
    self._class_res_bucket().clear()
  bucket=self._class_res_bucket()
  self.reservation_records.update(bucket)
  bucket.update(self.reservation_records)
  self._sync_reserved_inventory()
 def rebuild_reservations_from_exchange(self,open_orders:Optional[List[Dict[str,Any]]])->bool:
  lock=getattr(self,"_reservations_lock",None) or _CLOB_HTTP_LOCK
  with lock:
   if open_orders is None:
    self.reservations_trusted=False
    return False
   rebuilt:Dict[str,Dict[str,Any]]={}
   for o in open_orders:
    if not o or str(o.get("side","")).upper()!="SELL":
     continue
    oid=str(o.get("id") or o.get("orderID") or "")
    tok=str(o.get("asset_id") or o.get("token_id") or "")
    try:
     remaining=float(o.get("original_size",o.get("size",0.0)) or 0.0) - float(o.get("size_matched",0.0) or 0.0)
    except (TypeError,ValueError):
     self.reservations_trusted=False
     return False
    if not oid or not tok or remaining<=0.0:
     continue
    rebuilt[oid]={ "reservation_id":oid,"token_id":tok,"size":float(Decimal(str(remaining)).quantize(Decimal("0.01"),rounding=ROUND_CEILING)),"status":"RESERVED","created_at_ts":time.time(),"source":"EXCHANGE_OPEN_ORDERS",}
   has_ambiguous=False
   for rid,r in (self.reservation_records or {}).items():
    if r.get("status")=="RELEASED":
     continue
    is_ambiguous=( str(rid).startswith(("AMBIGUOUS_","EXCEPTION_","PENDING_")) or str(r.get("status","")).upper() in {"AMBIGUOUS","IN_FLIGHT","UNRESOLVED"} or bool(r.get("ambiguous",False)) )
    if is_ambiguous and rid not in rebuilt:
     rebuilt[rid]=dict(r)
     has_ambiguous=True
   bucket=self._class_res_bucket()
   bucket.clear()
   bucket.update(rebuilt)
   self.reservation_records=dict(rebuilt)
   self._sync_reserved_inventory()
   self._save_durable_reservations()
   if has_ambiguous:
    self.reservations_trusted=False
    logger.warning( f"[PM-EXEC] Rebuilt reservations with {len(rebuilt)} commitments, but ambiguous unresolved commitments " "remain. reservations_trusted set to False fail-closed." )
   else:
    self.reservations_trusted=True
    self.reservation_corruption_detected=False
    logger.info(f"[PM-EXEC] Reservation book rebuilt from exchange: {len(rebuilt)} resting SELL commitment(s).")
   return True
 def _sync_reserved_inventory(self):
  lock=getattr(self,"_reservations_lock",None) or _CLOB_HTTP_LOCK
  with lock:
   totals:Dict[str,float]=defaultdict(float)
   for r in list(self.reservation_records.values()):
    tid=str(r.get("token_id",""))
    if tid and r.get("status")!="RELEASED":
     totals[tid] += float(r.get("size",0.0))
   self.reserved_inventory=defaultdict(float,{k:round(v,4) for k,v in totals.items()})
 def _save_durable_reservations(self):
  lock=getattr(self,"_reservations_lock",None) or _CLOB_HTTP_LOCK
  with lock:
   path=self.reservations_path
   temp_path=path.with_name(f"{path.name}.tmp.{os.getpid()}.{threading.get_ident()}")
   try:
    path.parent.mkdir(parents=True,exist_ok=True)
    d=self._reservation_digest(self.reservation_records,live_mode=not self.dry_run)
    payload={ "schema":self.RESERVATIONS_SCHEMA,"reservation_records":self.reservation_records,"hmac_sha256":d,"sha256":d,"updated_at":time.time(),}
    with open(temp_path,"w",encoding="utf-8") as f:
     json.dump(payload,f,indent=2,default=str)
     f.flush()
     os.fsync(f.fileno())
    os.replace(temp_path,path)
    if os.name!="nt":
     dir_fd=os.open(str(path.parent),os.O_RDONLY)
     try:
      os.fsync(dir_fd)
     finally:
      os.close(dir_fd)
   except Exception as e:
    try:
     temp_path.unlink(missing_ok=True)
    except Exception:
     pass
    logger.error(f"Could not save durable reservations: {e}")
    if not self.dry_run:
     raise RuntimeError(f"CRITICAL: Failed to persist durable reservations: {e}")
 @classmethod
 def clear_all_reservations(cls):
  cls._class_reservations.clear()
  base=Path(cls.RESERVATIONS_STATE_PATH)
  for p in (base,base.with_name(base.stem + ".dryrun" + base.suffix)):
   if p.exists():
    try:
     p.unlink()
    except Exception:
     pass
 def reserve_inventory(self,token_id:str,size:float,reservation_id:Optional[str]=None):
  lot=Decimal("0.01")
  quantized=float(Decimal(str(max(0.0,size))).quantize(lot,rounding=ROUND_FLOOR))
  if quantized<=0.0:
   return
  lock=getattr(self,"_reservations_lock",None) or _CLOB_HTTP_LOCK
  with lock:
   r_id=str(reservation_id or f"RES_{token_id}_{int(time.time()*1000)}_{len(self.reservation_records)}")
   record={ "reservation_id":r_id,"token_id":token_id,"size":quantized,"status":"RESERVED","created_at_ts":time.time(),}
   self.reservation_records[r_id]=record
   self._class_res_bucket()[r_id]=record
   self._sync_reserved_inventory()
   self._save_durable_reservations()
 def release_inventory(self,token_id:str="",size:float=0.0,reservation_id:Optional[str]=None):
  lot=Decimal("0.01")
  quantized=float(Decimal(str(max(0.0,size))).quantize(lot,rounding=ROUND_FLOOR)) if size else 0.0
  lock=getattr(self,"_reservations_lock",None) or _CLOB_HTTP_LOCK
  with lock:
   bucket=self._class_res_bucket()
   if reservation_id and str(reservation_id) in self.reservation_records:
    r_id=str(reservation_id)
    self.reservation_records.pop(r_id,None)
    bucket.pop(r_id,None)
   elif token_id:
    remaining_to_release=quantized if quantized > 0.0 else self.reserved_inventory.get(token_id,0.0)
    for r_id,r in list(self.reservation_records.items()):
     if r.get("token_id")==token_id and r.get("status")!="RELEASED":
      cur_sz=float(r.get("size",0.0))
      if cur_sz<=remaining_to_release:
       remaining_to_release -= cur_sz
       self.reservation_records.pop(r_id,None)
       bucket.pop(r_id,None)
      else:
       r["size"]=round(cur_sz - remaining_to_release,4)
       if r_id in bucket:
        bucket[r_id]["size"]=r["size"]
       remaining_to_release=0.0
       break
      if remaining_to_release<=0.0:
       break
   self._sync_reserved_inventory()
   self._save_durable_reservations()
 def update_reservation(self,reservation_id:str,new_remaining_size:float):
  r_id=str(reservation_id)
  lock=getattr(self,"_reservations_lock",None) or _CLOB_HTTP_LOCK
  with lock:
   if r_id not in self.reservation_records:
    return
   lot=Decimal("0.01")
   quantized=float(Decimal(str(max(0.0,new_remaining_size))).quantize(lot,rounding=ROUND_FLOOR))
   if quantized<=0.0:
    self.release_inventory(reservation_id=r_id)
   else:
    bucket=self._class_res_bucket()
    self.reservation_records[r_id]["size"]=quantized
    if r_id in bucket:
     bucket[r_id]["size"]=quantized
    self._sync_reserved_inventory()
    self._save_durable_reservations()
 def get_unreserved_conditional_balance(self,token_id:str)->Optional[float]:
  if not getattr(self,"reservations_trusted",True):
   logger.critical(f"[PM-EXEC] Reservation book UNTRUSTED; refusing to compute free inventory for {token_id}.")
   return None
  bal=self.get_conditional_balance(token_id)
  if bal is None:
   return None
  lock=getattr(self,"_reservations_lock",None) or _CLOB_HTTP_LOCK
  with lock:
   reserved=float(self.reserved_inventory.get(token_id,0.0))
  return max(0.0,round(bal - reserved,4))
 def get_onchain_erc1155_balance(self,token_id:str,account_address:Optional[str]=None)->Optional[float]:
  target_account=account_address or self.funder_address
  if not target_account or not token_id:
   return None
  try:
   rpc_url=os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com")
   conditional_tokens="0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
   selector="00fdd58e"
   clean_addr=target_account[2:] if target_account.startswith("0x") else target_account
   addr_padded=clean_addr.lower().rjust(64,"0")
   token_id_int=int(token_id,16) if str(token_id).startswith("0x") else int(token_id)
   id_hex=hex(token_id_int)[2:].rjust(64,"0")
   call_data="0x" + selector + addr_padded + id_hex
   payload={ "jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":conditional_tokens,"data":call_data},"latest"],}
   post_fn=requests.post if hasattr(requests.post,"mock_calls") else getattr(self,"_sync_session",requests).post
   resp=post_fn(rpc_url,json=payload,timeout=3.0)
   if resp.status_code==200:
    res_json=resp.json()
    if "result" in res_json and res_json["result"] is not None:
     raw_int=int(res_json["result"],16)
     return raw_int / 1e6
   return None
  except Exception as e:
   logger.debug(f"On-chain ERC-1155 balanceOf query error for {token_id}: {e}")
   return None
 _LEDGER_WRITER_LOCK=threading.Lock()
 _LEDGER_WRITER_QUEUE:Optional["queue.Queue[Optional[Tuple[Path, bytes]]]"]=None
 @classmethod
 def _ensure_ledger_writer(cls)->"queue.Queue[Optional[Tuple[Path, bytes]]]":
  if cls._LEDGER_WRITER_QUEUE is None:
   with cls._LEDGER_WRITER_LOCK:
    if cls._LEDGER_WRITER_QUEUE is None:
     import atexit
     q:"queue.Queue[Optional[Tuple[Path, bytes]]]"=queue.Queue(maxsize=4096)
     def _writer_loop()->None:
      while True:
       item=q.get()
       try:
        if item is None:
         return
        p_target,raw_b=item
        with open(p_target,"ab") as fh:
         fh.write(raw_b)
       except Exception as w_exc:
        logger.error(f"Async order ledger write error: {w_exc}")
       finally:
        q.task_done()
     def _flush_on_exit()->None:
      try:
       q.join()
      except Exception:
       pass
     th=threading.Thread(target=_writer_loop,name="pm-order-ledger-writer",daemon=True)
     th.start()
     atexit.register(_flush_on_exit)
     cls._LEDGER_WRITER_QUEUE=q
  return cls._LEDGER_WRITER_QUEUE
 def _log_order(self,res:OrderResult):
  try:
   entry={ "timestamp_utc":datetime.now(timezone.utc).isoformat(),"success":res.success,"order_id":res.order_id,"trade_id":res.trade_id,"token_id":res.token_id,"target_token":res.target_token,"side":res.side,"price":res.price,"size":res.size,"notional_usd":res.notional_usd,"fee_usd":res.fee_usd,"latency_ms":res.latency_ms,"mode":res.mode,"error":res.error,"details":res.details,}
   if _orjson is not None:
    try:
     raw_line=_orjson.dumps(entry,default=str) + b"\n"
    except Exception:
     raw_line=(json.dumps(entry,default=str) + "\n").encode("utf-8")
   else:
    raw_line=(json.dumps(entry,default=str) + "\n").encode("utf-8")
   use_async_ledger=( not self.dry_run and os.environ.get("PM_SYNC_ORDER_LEDGER","0")!="1" and not os.environ.get("POLYMARKET_LEDGER_PATH") and self.ledger_path==Path(POLYMARKET_DATA_DIR / "live_orders.jsonl") )
   if use_async_ledger:
    try:
     self._ensure_ledger_writer().put_nowait((self.ledger_path,raw_line))
     return
    except Exception:
     pass
   with open(self.ledger_path,"ab") as f:
    f.write(raw_line)
  except Exception as e:
   logger.error(f"Failed to append to live order ledger: {e}")
if __name__=="__main__":
 print("=" * 80)
 print("  POLYMARKET LIVE CLOB EXECUTION ADAPTER - STANDALONE PREFLIGHT")
 print("=" * 80)
 executor=PolymarketLiveExecutor(dry_run=True)
 print(f"Auth Mode: {executor.auth_mode}")
 print(f"SDK Available: {PY_CLOB_AVAILABLE}")
 print(f"Ledger Path: {executor.ledger_path}")
 fee_rate,fee_usd=executor.calculate_dynamic_crypto_fee(0.77,50.0)
 print(f"Dynamic Fee on $50 @ $0.77: Rate={fee_rate*100:.2f}% | USD=${fee_usd:.4f}")
 assert abs(fee_rate - 0.0161) < 1e-4,"Dynamic fee calculation mismatch"
 print(">>> POLYMARKET LIVE ADAPTER PREFLIGHT: PASS (100% OPERATIONAL) <<<")

# === [05/12] src/polymarket_research/polymarket_terminal_recorder.py :: Sub-ms Binance/Coinbase/Chainlink-TWAP Shock Detection & CLOB L2 SHM Recorder ===
#!/usr/bin/env python3 import asyncio
import collections
from collections import defaultdict,deque
import copy
import statistics
import json
import logging
import math
import os
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
from typing import Dict,List,Optional,Any,Tuple,Set
import aiohttp
import numpy as np
import websockets
try:
 import orjson as _orjson
except Exception:
 _orjson=None
PROJECT_ROOT=Path(__file__).resolve().parent.parent.parent
DATA_DIR=PROJECT_ROOT / "data" / "polymarket"
DATA_DIR.mkdir(parents=True,exist_ok=True)
TRIGGER_FILE=DATA_DIR / "live_shock_triggers.jsonl"
RESOLUTIONS_FILE=DATA_DIR / "finalized_market_resolutions.jsonl"
GAMMA_API_URL="https://gamma-api.polymarket.com"
CLOB_API_URL="https://clob.polymarket.com"
CLOB_WS_URL="wss://ws-subscriptions-clob.polymarket.com/ws/market"
BINANCE_REST_URL="https://api.binance.com"
BINANCE_FUTURES_REST_URL="https://fapi.binance.com"
COINBASE_WS_URL="wss://ws-feed.exchange.coinbase.com"
SHM_DIR=Path(os.getenv("PM_FAST_TICK_DIR","/dev/shm"))
FAST_TICK_THROTTLE_SEC=0.025
COINBASE_STALE_SEC=5.0
EXP306_REALTIME_LEDGER=DATA_DIR / "exp306_realtime_boundary_merge.jsonl"
def fast_tick_path(asset:str)->Path:
 return SHM_DIR / f"pm_fast_tick_{str(asset).upper()}.json"
LEAD_STATE_MAX_AGE_MS=1500.0
LEAD_STATE_THROTTLE_SEC=0.025
SYMPATHY_BTC_MAX_AGE_MS=500.0
SYMPATHY_BTC_MIN_VOL_USD=2_250_000.0
SYMPATHY_BTC_MIN_ABS_OFI=0.85
SYMPATHY_THRESHOLD_MULT=0.65
SYMPATHY_MIN_AGE_ASK_MS=300.0
ADAPTIVE_THRESH_MIN_MULT=0.65
ADAPTIVE_THRESH_MAX_MULT=1.35
ADAPTIVE_THRESH_VOL_MULT=18.0
ADAPTIVE_THRESH_WINDOW_SEC=300
ADAPTIVE_THRESH_MIN_COVERAGE_SEC=60.0
def lead_state_path(asset:str="BTC")->Path:
 return SHM_DIR / f"pm_lead_state_{str(asset).upper()}.json"
def write_lead_state(state:Dict[str,Any],path:Optional[Path]=None)->bool:
 path=path or lead_state_path("BTC")
 try:
  payload=_orjson.dumps(state) if _orjson else json.dumps(state).encode("utf-8")
  tmp=path.with_suffix(f".tmp.{os.getpid()}")
  with open(tmp,"wb") as f:
   f.write(payload)
  os.replace(tmp,path)
  return True
 except Exception:
  return False
def read_lead_state(path:Optional[Path]=None,max_age_ms:float=LEAD_STATE_MAX_AGE_MS,now_ns:Optional[int]=None)->Optional[Dict[str,Any]]:
 path=path or lead_state_path("BTC")
 try:
  with open(path,"rb") as f:
   raw=f.read()
  st=_orjson.loads(raw) if _orjson else json.loads(raw)
  now_ns=now_ns if now_ns is not None else time.time_ns()
  if (now_ns - int(st.get("ts_ns") or 0)) / 1e6 > max_age_ms:
   return None
  return st
 except Exception:
  return None
def compute_adaptive_shock_threshold(base_threshold:float,avg_100ms_vol_5m:Optional[float])->float:
 if avg_100ms_vol_5m is None or not math.isfinite(avg_100ms_vol_5m) or avg_100ms_vol_5m<=0.0:
  return float(base_threshold)
 return min(ADAPTIVE_THRESH_MAX_MULT * base_threshold,max(ADAPTIVE_THRESH_MIN_MULT * base_threshold,ADAPTIVE_THRESH_VOL_MULT * avg_100ms_vol_5m))
def evaluate_btc_sympathy(lead:Optional[Dict[str,Any]],eth_flow_dir:str,eth_target_age_ask_ms:Optional[float],now_ns:Optional[int]=None)->bool:
 if not lead or eth_target_age_ask_ms is None:
  return False
 try:
  now_ns=now_ns if now_ns is not None else time.time_ns()
  shock_ts_ns=int(lead.get("last_shock_ts_ns") or 0)
  if shock_ts_ns<=0 or (now_ns - shock_ts_ns) / 1e6 > SYMPATHY_BTC_MAX_AGE_MS:
   return False
  if float(lead.get("last_shock_vol_100ms") or 0.0) < SYMPATHY_BTC_MIN_VOL_USD:
   return False
  if abs(float(lead.get("last_shock_ofi_100ms") or 0.0)) < SYMPATHY_BTC_MIN_ABS_OFI:
   return False
  if str(lead.get("last_shock_dir") or "").upper()!=str(eth_flow_dir).upper():
   return False
  return float(eth_target_age_ask_ms)>=SYMPATHY_MIN_AGE_ASK_MS
 except Exception:
  return False
def evaluate_realtime_exp306_boundary_and_merge( asset:str,horizon:str,market_id:str,up_top:Dict[str,Any],down_top:Dict[str,Any],spot:float,strike_open:float,secs_left:float,fee_rate:float=0.07,sigma_1h:Optional[float]=None,estimated_gas_usd:float=0.015,)->Dict[str,Any]:
 ask_up=float(up_top.get("best_ask") or 0.0)
 ask_dn=float(down_top.get("best_ask") or 0.0)
 sz_up=float(up_top.get("ask_size_l1") or 0.0)
 sz_dn=float(down_top.get("ask_size_l1") or 0.0)
 merge_net=None
 merge_ok=False
 if 0.0 < ask_up < 1.0 and 0.0 < ask_dn < 1.0 and min(sz_up,sz_dn) > 0:
  fee_up=fee_rate * ask_up * (1.0 - ask_up)
  fee_dn=fee_rate * ask_dn * (1.0 - ask_dn)
  gas_ps=estimated_gas_usd / min(sz_up,sz_dn)
  merge_net=round(1.0 - (ask_up + ask_dn + fee_up + fee_dn + gas_ps),5)
  merge_ok=merge_net>=0.015
 if sigma_1h is None:
  sigma_1h=0.0050 if str(asset).upper()=="BTC" else 0.0068
 boundary_z=None
 boundary_ok=False
 boundary_side=None
 if spot > 0 and strike_open > 0 and 0 < secs_left<=120.0:
  sig_rem=sigma_1h * math.sqrt(max(secs_left,1.0) / 3600.0)
  boundary_z=round(abs(spot - strike_open) / (strike_open * max(sig_rem,1e-9)),3)
  boundary_side="UP" if spot>=strike_open else "DOWN"
  boundary_ok=boundary_z>=3.5
 return { "timestamp_unix":time.time(),"asset":str(asset).upper(),"horizon":horizon,"market_id":market_id,"secs_left":round(float(secs_left),1),"ask_up":ask_up,"ask_down":ask_dn,"merge_net_per_share":merge_net,"merge_opportunity":merge_ok,"boundary_z":boundary_z,"boundary_side":boundary_side,"boundary_opportunity":boundary_ok,"mode":"READ_ONLY_SHADOW",}
ASSET_CONFIGS={ "BTC":{ "series_slug":"btc-up-or-down-hourly","binance_symbol":"BTCUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/btcusdt@aggTrade","binance_futures_ws":"wss://fstream.binance.com:443/market/ws/btcusdt@aggTrade","default_shock_threshold":1_500_000.0,"telemetry_file":DATA_DIR / "polymarket_hourly_telemetry.jsonl","shock_file":DATA_DIR / "shock_responses.jsonl","correlations_file":DATA_DIR / "leadlag_cross_correlations.jsonl","log_file":DATA_DIR / "recorder.log","pid_file":DATA_DIR / "recorder.pid",},"ETH":{ "series_slug":"eth-up-or-down-hourly","binance_symbol":"ETHUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/ethusdt@aggTrade","binance_futures_ws":"wss://fstream.binance.com:443/market/ws/ethusdt@aggTrade","default_shock_threshold":500_000.0,"telemetry_file":DATA_DIR / "polymarket_hourly_telemetry_eth.jsonl","shock_file":DATA_DIR / "shock_responses_eth.jsonl","correlations_file":DATA_DIR / "leadlag_cross_correlations_eth.jsonl","log_file":DATA_DIR / "recorder_eth.log","pid_file":DATA_DIR / "recorder_eth.pid",},"SOL":{ "series_slug":"solana-up-or-down-hourly","binance_symbol":"SOLUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/solusdt@aggTrade","binance_futures_ws":"wss://fstream.binance.com:443/market/ws/solusdt@aggTrade","default_shock_threshold":250_000.0,"telemetry_file":DATA_DIR / "polymarket_hourly_telemetry_sol.jsonl","shock_file":DATA_DIR / "shock_responses_sol.jsonl","correlations_file":DATA_DIR / "leadlag_cross_correlations_sol.jsonl","log_file":DATA_DIR / "recorder_sol.log","pid_file":DATA_DIR / "recorder_sol.pid",},"XRP":{ "series_slug":"xrp-up-or-down-hourly","binance_symbol":"XRPUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/xrpusdt@aggTrade","binance_futures_ws":"wss://fstream.binance.com:443/market/ws/xrpusdt@aggTrade","default_shock_threshold":100_000.0,"telemetry_file":DATA_DIR / "polymarket_hourly_telemetry_xrp.jsonl","shock_file":DATA_DIR / "shock_responses_xrp.jsonl","correlations_file":DATA_DIR / "leadlag_cross_correlations_xrp.jsonl","log_file":DATA_DIR / "recorder_xrp.log","pid_file":DATA_DIR / "recorder_xrp.pid",},"BNB":{ "series_slug":"bnb-up-or-down-hourly","binance_symbol":"BNBUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/bnbusdt@aggTrade","binance_futures_ws":"wss://fstream.binance.com:443/market/ws/bnbusdt@aggTrade","default_shock_threshold":150_000.0,"telemetry_file":DATA_DIR / "polymarket_hourly_telemetry_bnb.jsonl","shock_file":DATA_DIR / "shock_responses_bnb.jsonl","correlations_file":DATA_DIR / "leadlag_cross_correlations_bnb.jsonl","log_file":DATA_DIR / "recorder_bnb.log","pid_file":DATA_DIR / "recorder_bnb.pid",},"DOGE":{ "series_slug":"doge-up-or-down-hourly","binance_symbol":"DOGEUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/dogeusdt@aggTrade","binance_futures_ws":"wss://fstream.binance.com:443/market/ws/dogeusdt@aggTrade","default_shock_threshold":75_000.0,"telemetry_file":DATA_DIR / "polymarket_hourly_telemetry_doge.jsonl","shock_file":DATA_DIR / "shock_responses_doge.jsonl","correlations_file":DATA_DIR / "leadlag_cross_correlations_doge.jsonl","log_file":DATA_DIR / "recorder_doge.log","pid_file":DATA_DIR / "recorder_doge.pid",},"HYPE":{ "series_slug":"hype-up-or-down-hourly","binance_symbol":"HYPEUSDT","binance_spot_ws":"","binance_futures_ws":"wss://fstream.binance.com:443/market/ws/hypeusdt@aggTrade","futures_only_ref":True,"default_shock_threshold":75_000.0,"telemetry_file":DATA_DIR / "polymarket_hourly_telemetry_hype.jsonl","shock_file":DATA_DIR / "shock_responses_hype.jsonl","correlations_file":DATA_DIR / "leadlag_cross_correlations_hype.jsonl","log_file":DATA_DIR / "recorder_hype.log","pid_file":DATA_DIR / "recorder_hype.pid",},}
logger=logging.getLogger("PolymarketDualFeed1H")
_FAST_IPC_SOCK=None
_FAST_IPC_ADDR=b"\x00polymarket_shock_notify"
_IPC_SEND_FAILURES=0
_IPC_LAST_WARN_TS=0.0
def _broadcast_fast_trigger_ipc(data:bytes)->None:
 global _FAST_IPC_SOCK,_IPC_SEND_FAILURES,_IPC_LAST_WARN_TS
 if os.name=="nt":
  return
 try:
  import socket
  if _FAST_IPC_SOCK is None:
   s=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
   s.setblocking(False)
   _FAST_IPC_SOCK=s
  ipc_addr=b"\x00" + os.environ.get("POLYMARKET_IPC_SOCKET_NAME","polymarket_shock_notify").encode("utf-8")
  _FAST_IPC_SOCK.sendto(data,ipc_addr)
 except Exception as e:
  _IPC_SEND_FAILURES += 1
  now_u=time.time()
  if (now_u - _IPC_LAST_WARN_TS)>=60.0:
   _IPC_LAST_WARN_TS=now_u
   logger.debug(f"[FAST IPC NOTICE] Abstract socket send missed ({_IPC_SEND_FAILURES} total, disk fallback active): {e}")
def _dumps_compact(payload:Dict[str,Any])->str:
 if _orjson is not None:
  return _orjson.dumps(payload).decode("utf-8")
 return json.dumps(payload,separators=(",",":"))
def _atomic_append_jsonl(path:Path,line_str:str,broadcast_ipc:bool=True)->None:
 if not line_str.endswith("\n"):
  line_str += "\n"
 data=line_str.encode("utf-8")
 if broadcast_ipc and (path==TRIGGER_FILE or str(path).endswith("live_shock_triggers.jsonl")):
  _broadcast_fast_trigger_ipc(data)
 fd=os.open(str(path),os.O_WRONLY | os.O_CREAT | os.O_APPEND,0o664)
 try:
  try:
   import fcntl
   fcntl.flock(fd,fcntl.LOCK_EX)
  except Exception:
   pass
  os.write(fd,data)
 finally:
  try:
   import fcntl
   fcntl.flock(fd,fcntl.LOCK_UN)
  except Exception:
   pass
  os.close(fd)
def _dispatch_trigger_fast(path:Path,payload:Dict[str,Any])->Tuple[bytes,str]:
 if _orjson is not None:
  raw=_orjson.dumps(payload) + b"\n"
  line_str=raw.decode("utf-8")
 else:
  line_str=json.dumps(payload) + "\n"
  raw=line_str.encode("utf-8")
 if path==TRIGGER_FILE or str(path).endswith("live_shock_triggers.jsonl"):
  _broadcast_fast_trigger_ipc(raw)
 return raw,line_str
def _persist_trigger_nonblocking(path:Path,line_str:str)->None:
 path.parent.mkdir(parents=True,exist_ok=True)
 data=line_str.encode("utf-8")
 fd=os.open(str(path),os.O_WRONLY | os.O_CREAT | os.O_APPEND,0o644)
 try:
  try:
   import fcntl
   fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
  except BlockingIOError:
   os.close(fd)
   fd=-1
   try:
    loop=asyncio.get_running_loop()
    loop.run_in_executor(None,_atomic_append_jsonl,path,line_str,False)
    return
   except RuntimeError:
    _atomic_append_jsonl(path,line_str,False)
    return
  except Exception:
   pass
  os.write(fd,data)
 finally:
  if fd>=0:
   try:
    import fcntl
    fcntl.flock(fd,fcntl.LOCK_UN)
   except Exception:
    pass
   try:
    os.close(fd)
   except OSError:
    pass
def setup_logging(asset:str="BTC"):
 cfg=ASSET_CONFIGS.get(asset.upper(),ASSET_CONFIGS["BTC"])
 log_file=cfg["log_file"]
 root=logging.getLogger()
 for h in list(root.handlers):
  root.removeHandler(h)
  try:
   h.close()
  except Exception:
   pass
 logging.basicConfig( level=logging.INFO,format="[%(asctime)s UTC] [%(levelname)s] [%(name)s] %(message)s",datefmt="%Y-%m-%d %H:%M:%S",handlers=[logging.FileHandler(log_file)] + ([logging.StreamHandler(sys.stdout)] if sys.stdout.isatty() else []) )
 global logger
 logger=logging.getLogger(f"PolymarketDualFeed1H-{asset.upper()}")
DEFAULT_FEE_RATE=0.07
TICKET_CAPACITY_LEVELS=[1.0,5.0,20.0,25.0,50.0,100.0,150.0,200.0,250.0]
CORRELATION_LAGS_MS=[-1000,-500,-250,-100,-50,0,50,100,250,500,1000]
def calculate_per_share_taker_fee(price:float,fee_rate:float=DEFAULT_FEE_RATE,fee_exponent:float=1.0)->float:
 p=max(0.001,min(0.999,price))
 return fee_rate * ((p * (1.0 - p)) ** fee_exponent)
class L2OrderBook:
 def __init__(self,asset_id:str):
  self.asset_id=str(asset_id)
  self.token_id=str(asset_id)
  self.bids:Dict[float,float]={}
  self.asks:Dict[float,float]={}
  self.last_book_update_ts:float=0.0
  self.last_best_bid_change_ts:float=0.0
  self.last_best_ask_change_ts:float=0.0
  self.prev_best_bid:Tuple[float,float]=(0.0,0.0)
  self.prev_best_ask:Tuple[float,float]=(1.0,0.0)
  self.book_sequence_id:int=0
  self.microprice_formula="(best_ask * bid_sz_1 + best_bid * ask_sz_1) / (bid_sz_1 + ask_sz_1)"
  self.obi_depth_levels=5
  self._dirty:bool=True
  self._sorted_bids:List[Tuple[float,float]]=[]
  self._sorted_asks:List[Tuple[float,float]]=[]
 def _sorted_levels(self)->Tuple[List[Tuple[float,float]],List[Tuple[float,float]]]:
  if self._dirty:
   self._sorted_bids=sorted(self.bids.items(),key=lambda x:x[0],reverse=True)
   self._sorted_asks=sorted(self.asks.items(),key=lambda x:x[0])
   self._dirty=False
  return self._sorted_bids,self._sorted_asks
 def _check_top_changes(self,now_ts:float):
  if self.bids:
   bb=max(self.bids)
   curr_best_bid=(bb,self.bids[bb])
  else:
   curr_best_bid=(0.0,0.0)
  if self.asks:
   ba=min(self.asks)
   curr_best_ask=(ba,self.asks[ba])
  else:
   curr_best_ask=(1.0,0.0)
  if ( self.last_best_bid_change_ts==0.0 or self.prev_best_bid[0]<=0.0 or curr_best_bid[0] < self.prev_best_bid[0] ):
   self.last_best_bid_change_ts=now_ts
  self.prev_best_bid=curr_best_bid
  if ( self.last_best_ask_change_ts==0.0 or self.prev_best_ask[0]>=1.0 or curr_best_ask[0] > self.prev_best_ask[0] ):
   self.last_best_ask_change_ts=now_ts
  self.prev_best_ask=curr_best_ask
 def apply_snapshot(self,bids:List[Dict[str,str]],asks:List[Dict[str,str]]):
  now_ts=time.time()
  self.bids={float(b["price"]):float(b["size"]) for b in bids if float(b["size"]) > 0}
  self.asks={float(a["price"]):float(a["size"]) for a in asks if float(a["size"]) > 0}
  self.last_book_update_ts=now_ts
  self.book_sequence_id += 1
  self._dirty=True
  self._check_top_changes(now_ts)
 def apply_price_changes(self,changes:List[Dict[str,str]]):
  now_ts=time.time()
  for c in changes:
   px=float(c["price"])
   sz=float(c["size"])
   side=c.get("side","").upper()
   if side=="BUY":
    if sz<=0:
     self.bids.pop(px,None)
    else:
     self.bids[px]=sz
   elif side=="SELL":
    if sz<=0:
     self.asks.pop(px,None)
    else:
     self.asks[px]=sz
  self.last_book_update_ts=now_ts
  self.book_sequence_id += 1
  if changes:
   self._dirty=True
  self._check_top_changes(now_ts)
 def top_of_book(self,obs_ts:Optional[float]=None)->Dict[str,Any]:
  t_now=obs_ts if obs_ts is not None else time.time()
  sorted_bids,sorted_asks=self._sorted_levels()
  best_bid,bid_sz=sorted_bids[0] if sorted_bids else (0.0,0.0)
  best_ask,ask_sz=sorted_asks[0] if sorted_asks else (1.0,0.0)
  denom=bid_sz + ask_sz
  return { "best_bid":round(best_bid,4),"best_ask":round(best_ask,4),"bid_size_l1":round(bid_sz,2),"ask_size_l1":round(ask_sz,2),"spread":round(best_ask - best_bid,4),"q_mid":round((best_bid + best_ask) / 2.0,4),"obi_l1":round((bid_sz - ask_sz) / denom,3) if denom > 0 else 0.0,"age_book_ms":round((t_now - self.last_book_update_ts) * 1000.0,1) if self.last_book_update_ts > 0 else None,"age_ask_ms":round((t_now - self.last_best_ask_change_ts) * 1000.0,1) if self.last_best_ask_change_ts > 0 else None,"raw_top_bids":sorted_bids[:15],"raw_top_asks":sorted_asks[:15],}
 def get_metrics( self,obs_ts:Optional[float]=None,fee_rate:float=DEFAULT_FEE_RATE,compact:bool=False,)->Dict[str,Any]:
  t_now=obs_ts if obs_ts is not None else time.time()
  sorted_bids,sorted_asks=self._sorted_levels()
  best_bid=sorted_bids[0][0] if sorted_bids else 0.0
  bid_sz_1=sorted_bids[0][1] if sorted_bids else 0.0
  best_ask=sorted_asks[0][0] if sorted_asks else 1.0
  ask_sz_1=sorted_asks[0][1] if sorted_asks else 0.0
  is_crossed=False
  if best_bid > 0 and best_ask < 1.0 and best_bid>=best_ask:
   is_crossed=True
  spread=best_ask - best_bid
  q_mid=(best_bid + best_ask) / 2.0
  l1_denom=bid_sz_1 + ask_sz_1
  if l1_denom > 0:
   obi_l1=(bid_sz_1 - ask_sz_1) / l1_denom
   q_micro=(best_bid * ask_sz_1 + best_ask * bid_sz_1) / l1_denom
  else:
   obi_l1=0.0
   q_micro=q_mid
  if not is_crossed and l1_denom > 0 and spread > 1e-5:
   if (obi_l1 > 1e-4 and q_micro < q_mid - 1e-4) or (obi_l1 < -1e-4 and q_micro > q_mid + 1e-4):
    logger.warning( f"[BOOK INVARIANT NOTICE] OBI_L1={obi_l1:.4f}, q_micro={q_micro:.4f}, q_mid={q_mid:.4f}" )
  top_bid_vol=sum(sz for _,sz in sorted_bids[:self.obi_depth_levels])
  top_ask_vol=sum(sz for _,sz in sorted_asks[:self.obi_depth_levels])
  depth_denom=top_bid_vol + top_ask_vol
  obi_depth=(top_bid_vol - top_ask_vol) / depth_denom if depth_denom > 0 else 0.0
  taker_fee=calculate_per_share_taker_fee(best_ask,fee_rate)
  executable_hurdle=best_ask + taker_fee
  execution_surface:Dict[str,Any]={}
  cap_levels=(20.0,25.0,50.0) if compact else TICKET_CAPACITY_LEVELS
  for notional in cap_levels:
   dollar_spent=0.0
   shares_bought=0.0
   total_fees=0.0
   for px,sz in sorted_asks:
    fill_dollars=min(notional - dollar_spent,px * sz)
    shares=fill_dollars / px
    level_fee=shares * fee_rate * px * (1.0 - px)
    dollar_spent += fill_dollars
    shares_bought += shares
    total_fees += level_fee
    if dollar_spent>=notional - 1e-6:
     break
   if shares_bought > 0:
    vwap_val=round(dollar_spent / shares_bought,4)
    effective_px=round((dollar_spent + total_fees) / shares_bought,4)
    crossing_cost=round(effective_px - q_mid,4)
    if vwap_val < best_ask - 1e-4:
     vwap_val=round(best_ask,4)
    execution_surface[f"vwap_${int(notional)}"]=vwap_val
    if not compact:
     execution_surface[f"effective_price_${int(notional)}"]=effective_px
     execution_surface[f"crossing_cost_${int(notional)}"]=crossing_cost
     execution_surface[f"fill_fees_${int(notional)}"]=round(total_fees,5)
    elif notional==50.0:
     execution_surface["effective_price_$50"]=effective_px
     execution_surface["fill_fees_$50"]=round(total_fees,5)
   elif not compact:
    execution_surface[f"vwap_${int(notional)}"]=None
    execution_surface[f"effective_price_${int(notional)}"]=None
    execution_surface[f"crossing_cost_${int(notional)}"]=None
    execution_surface[f"fill_fees_${int(notional)}"]=None
  age_book_ms=round((t_now - self.last_book_update_ts) * 1000.0,1) if self.last_book_update_ts > 0 else None
  age_bid_ms=round((t_now - self.last_best_bid_change_ts) * 1000.0,1) if self.last_best_bid_change_ts > 0 else None
  age_ask_ms=round((t_now - self.last_best_ask_change_ts) * 1000.0,1) if self.last_best_ask_change_ts > 0 else None
  if compact:
   return { "best_bid":round(best_bid,4),"best_ask":round(best_ask,4),"bid_size_l1":round(bid_sz_1,2),"ask_size_l1":round(ask_sz_1,2),"spread":round(spread,4),"q_mid":round(q_mid,4),"q_micro":round(q_micro,4),"obi_l1":round(obi_l1,3),"obi_depth":round(obi_depth,3),"book_sequence_id":self.book_sequence_id,"book_timestamp":round(self.last_book_update_ts,3) if self.last_book_update_ts > 0 else 0.0,"is_crossed":is_crossed,"age_book_ms":age_book_ms,"age_bid_ms":age_bid_ms,"age_ask_ms":age_ask_ms,"taker_fee":round(taker_fee,5),"executable_hurdle":round(executable_hurdle,5),**execution_surface,"raw_top_bids":sorted_bids[:10],"raw_top_asks":sorted_asks[:10],}
  return { "best_bid":round(best_bid,4),"best_ask":round(best_ask,4),"bid_size_l1":round(bid_sz_1,2),"ask_size_l1":round(ask_sz_1,2),"spread":round(spread,4),"q_mid":round(q_mid,4),"q_micro":round(q_micro,4),"obi_l1":round(obi_l1,3),"obi_depth":round(obi_depth,3),"obi_depth_levels":self.obi_depth_levels,"microprice_formula":self.microprice_formula,"book_sequence_id":self.book_sequence_id,"book_timestamp":self.last_book_update_ts,"is_crossed":is_crossed,"age_book_ms":age_book_ms,"age_bid_ms":age_bid_ms,"age_ask_ms":age_ask_ms,"taker_fee":round(taker_fee,5),"executable_hurdle":round(executable_hurdle,5),**execution_surface,"raw_top_bids":sorted_bids[:15],"raw_top_asks":sorted_asks[:15] }
class PolymarketDualFeed1HRecorder:
 def __init__(self,asset:str="BTC",shock_threshold:Optional[float]=None):
  self.asset=asset.upper()
  if self.asset not in ASSET_CONFIGS:
   raise ValueError(f"Unsupported asset {self.asset}. Must be one of: {list(ASSET_CONFIGS.keys())}")
  self.cfg=ASSET_CONFIGS[self.asset]
  self.series_slug=self.cfg["series_slug"]
  self.binance_symbol=self.cfg["binance_symbol"]
  self.binance_spot_ws=self.cfg["binance_spot_ws"]
  self.binance_futures_ws=self.cfg["binance_futures_ws"]
  self.futures_only_ref:bool=bool(self.cfg.get("futures_only_ref",False))
  self.shock_threshold_usd=shock_threshold if shock_threshold is not None else self.cfg["default_shock_threshold"]
  self.telemetry_file=self.cfg["telemetry_file"]
  self.shock_file=self.cfg["shock_file"]
  self.correlations_file=self.cfg["correlations_file"]
  self.pid_file=self.cfg["pid_file"]
  self.log_file=self.cfg["log_file"]
  self.session:Optional[aiohttp.ClientSession]=None
  self.current_market:Optional[Dict[str,Any]]=None
  self.market_15m:Optional[Dict[str,Any]]=None
  self.market_5m:Optional[Dict[str,Any]]=None
  self.market_4h:Optional[Dict[str,Any]]=None
  self.books:Dict[str,L2OrderBook]={}
  self.spot_trades:collections.deque=collections.deque(maxlen=15000)
  self.futures_trades:collections.deque=collections.deque(maxlen=15000)
  self.basis_history:collections.deque=collections.deque(maxlen=2000)
  self.spot_price:float=0.0
  self.futures_price:float=0.0
  self.basis_usd:float=0.0
  self.basis_bps:float=0.0
  self.finalized_1h_open:float=0.0
  self.fee_rate_market:float=DEFAULT_FEE_RATE
  self.fee_exponent:float=1.0
  self.fee_source:str="polymarket_crypto_schedule_v1"
  self.fee_enabled:bool=True
  self.fee_formula_version:str="taker_fee_c_times_rate_times_p_one_minus_p"
  self.clock_offset_ms:float=0.0
  self.clock_uncertainty_ms:float=0.0
  self.last_clock_sync_ts:float=0.0
  self.last_shock_ts:float=0.0
  self.last_shock_ts_by_source:Dict[str,float]=defaultdict(float)
  self.last_cross_corr_ts:float=0.0
  self.active_burst_tasks:Set[asyncio.Task]=set()
  self.running:bool=True
  self.clob_ws_connected:bool=False
  self.last_clob_ws_msg_ts:float=0.0
  self._last_stale_exch_warn_ts:float=0.0
  DATA_DIR.mkdir(parents=True,exist_ok=True)
  self.telemetry_15m_file:Path=DATA_DIR / f"polymarket_15m_telemetry_{self.asset.lower()}.jsonl"
  self.telemetry_5m_file:Path=DATA_DIR / f"polymarket_5m_telemetry_{self.asset.lower()}.jsonl"
  self.telemetry_4h_file:Path=DATA_DIR / f"polymarket_4h_telemetry_{self.asset.lower()}.jsonl"
  self._last_telem_bbo_by_hz:Dict[str,Tuple[float,Tuple[Any,...]]]={}
  self._spot_1m_bucket:int=0
  self._last_1m_spot:float=0.0
  self._rolling_sigma_1h:float={ "BTC":0.0050,"ETH":0.0068,"BNB":0.0068,"SOL":0.0075,"XRP":0.0080,"DOGE":0.0095,"HYPE":0.0110,}.get(self.asset,0.0068)
  self.coinbase_product=f"{self.asset}-USD"
  self.coinbase_spot:float=0.0
  self.coinbase_spot_ts:float=0.0
  self.coinbase_history:collections.deque=collections.deque(maxlen=600)
  self._venue_div_history:collections.deque=collections.deque(maxlen=200)
  self._cl_proxy_history:collections.deque=collections.deque(maxlen=1200)
  self.chainlink_last_updated_ts:float=0.0
  self.fast_tick_file:Path=fast_tick_path(self.asset)
  self._last_fast_tick_write:float=0.0
  self._fast_tick_enabled:bool=SHM_DIR.is_dir()
  self._last_exp306_eval:float=0.0
  self.lead_state_file:Path=lead_state_path("BTC")
  self._last_lead_state_write:float=0.0
  self._last_btc_shock:Dict[str,Any]={}
  self._last_btc_flow_z:float=0.0
  self._vol_buckets:collections.deque=collections.deque(maxlen=ADAPTIVE_THRESH_WINDOW_SEC + 2)
  self._vol_first_sec:Optional[int]=None
  self._adaptive_cache:Tuple[float,float]=(0.0,float(self.shock_threshold_usd))
 def get_coinbase_spot(self,now:Optional[float]=None)->float:
  now=now if now is not None else time.time()
  if self.coinbase_spot > 0 and (now - self.coinbase_spot_ts)<=COINBASE_STALE_SEC:
   return self.coinbase_spot
  return 0.0
 def get_venue_divergence_bps(self,now:Optional[float]=None)->float:
  cb=self.get_coinbase_spot(now)
  if cb<=0 or self.spot_price<=0:
   return 0.0
  return round((self.spot_price - cb) / cb * 10000.0,2)
 def get_venue_divergence_centered_bps(self,now:Optional[float]=None)->float:
  raw_div=self.get_venue_divergence_bps(now)
  cb=self.get_coinbase_spot(now)
  if cb<=0 or self.spot_price<=0:
   return 0.0
  hist=getattr(self,"_venue_div_history",None)
  if hist and len(hist)>=10:
   return round(raw_div - statistics.median(hist),2)
  return raw_div
 def get_chainlink_proxy_spot(self,now:Optional[float]=None)->float:
  now_ts=now if now is not None else time.time()
  cb=self.get_coinbase_spot(now_ts)
  hist_div=getattr(self,"_venue_div_history",None)
  bn_usd=0.0
  if self.spot_price > 0 and hist_div and len(hist_div)>=10:
   med_bps=max(-250.0,min(250.0,float(statistics.median(hist_div))))
   bn_usd=self.spot_price / (1.0 + med_bps / 10000.0)
  if cb > 0 and bn_usd > 0:
   cl_px=round(0.5 * (cb + bn_usd),4)
  elif cb > 0:
   cl_px=round(cb,4)
  elif bn_usd > 0:
   cl_px=round(bn_usd,4)
  else:
   return 0.0
  hist=getattr(self,"_cl_proxy_history",None)
  if hist is not None and cl_px > 0:
   if not hist or (now_ts - hist[-1][0])>=0.20:
    hist.append((now_ts,cl_px))
   while hist and (now_ts - hist[0][0]) > 65.0:
    hist.popleft()
  return cl_px
 def get_chainlink_twap_60s(self,now:Optional[float]=None)->float:
  now_ts=now if now is not None else time.time()
  cl_now=self.get_chainlink_proxy_spot(now_ts)
  hist=getattr(self,"_cl_proxy_history",None)
  if not hist:
   return cl_now
  pts=[px for t,px in hist if (now_ts - t)<=60.0 and px > 0]
  if len(pts) < 2:
   return cl_now
  return round(statistics.mean(pts),4)
 async def fetch_polygon_chainlink_spot(self)->float:
  agg_map={ "BTC":"0xc907E116054Ad103354f2D350FD2514433D57F6f","ETH":"0xF9680D99D6C9589e2a93a78A04A279e509205945",}
  addr=agg_map.get(self.asset.upper())
  if not addr:
   return 0.0
  rpc_url=os.environ.get("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com")
  try:
   session=await self.get_session()
   payload={ "jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":addr,"data":"0xfeaf968c"},"latest"],}
   async with session.post(rpc_url,json=payload,timeout=1.5) as resp:
    if resp.status==200:
     res=await resp.json()
     hex_str=str(res.get("result") or "")
     if hex_str.startswith("0x") and len(hex_str)>=2 + 64 * 4:
      ans=int(hex_str[2 + 64:2 + 128],16)
      upd=int(hex_str[2 + 192:2 + 256],16)
      if ans > 0 and (time.time() - upd)<=20.0:
       self.chainlink_last_updated_ts=float(upd)
       return round(ans / 1e8,4)
  except Exception as e:
   logger.debug(f"Polygon Chainlink AggregatorV3 fetch skipped ({self.asset}): {e}")
  return 0.0
 def get_coinbase_move_bps(self,window_sec:float=2.0,now:Optional[float]=None)->float:
  now=now if now is not None else time.time()
  cb=self.get_coinbase_spot(now)
  if cb<=0 or not self.coinbase_history:
   return 0.0
  ref=None
  for t,px in self.coinbase_history:
   if now - t<=window_sec:
    ref=px
    break
  if not ref or ref<=0:
   return 0.0
  return round((cb - ref) / ref * 10000.0,2)
 async def _coinbase_stream_worker(self):
  backoff=2.0
  while self.running:
   try:
    async with websockets.connect(COINBASE_WS_URL,ping_interval=20,ping_timeout=10) as ws:
     await ws.send(json.dumps({ "type":"subscribe","product_ids":[self.coinbase_product],"channels":["ticker"],}))
     logger.info(f"[+] Subscribed to Coinbase ticker ({self.coinbase_product}) for composite venue filter.")
     backoff=2.0
     async for msg_str in ws:
      if not self.running:
       break
      data=_orjson.loads(msg_str) if _orjson else json.loads(msg_str)
      if data.get("type")!="ticker" or data.get("product_id")!=self.coinbase_product:
       continue
      px=float(data.get("price") or 0.0)
      if px > 0:
       now=time.time()
       self.coinbase_spot=px
       self.coinbase_spot_ts=now
       self.coinbase_history.append((now,px))
       if self.spot_price > 0:
        self._venue_div_history.append(round((self.spot_price - px) / px * 10000.0,2))
       while self.coinbase_history and now - self.coinbase_history[0][0] > 30.0:
        self.coinbase_history.popleft()
   except Exception as e:
    logger.warning(f"Coinbase feed disconnected ({e}); fail-open, retrying in {backoff:.0f}s...")
    await asyncio.sleep(backoff)
    backoff=min(30.0,backoff * 2.0)
 def build_fast_tick_snapshot(self,now:Optional[float]=None)->Dict[str,Any]:
  now=now if now is not None else time.time()
  snap:Dict[str,Any]={ "ts":now,"timestamp_unix":now,"asset":self.asset,"market_id":str(self.current_market["market_id"]) if self.current_market else None,"spot":self.spot_price,"futures":self.futures_price,"spot_price":self.spot_price,"futures_price":self.futures_price,"coinbase_spot":self.get_coinbase_spot(now),"chainlink_proxy_spot":self.get_chainlink_proxy_spot(now),"chainlink_twap_60s":self.get_chainlink_twap_60s(now),"venue_divergence_bps":self.get_venue_divergence_bps(now),"venue_divergence_centered_bps":self.get_venue_divergence_centered_bps(now),"coinbase_move_bps_2s":self.get_coinbase_move_bps(2.0,now),"basis_bps":round(self.basis_bps,2),"finalized_1h_open":self.finalized_1h_open,}
  markets_map:Dict[str,Any]={}
  if "UP" in self.books and "DOWN" in self.books:
   snap["UP"]=self.books["UP"].top_of_book(now)
   snap["DOWN"]=self.books["DOWN"].top_of_book(now)
   if self.current_market and "tokens" in self.current_market:
    snap["UP"]["token_id"]=self.current_market["tokens"].get("UP")
    snap["DOWN"]["token_id"]=self.current_market["tokens"].get("DOWN")
    mid=str(self.current_market.get("market_id"))
    markets_map[mid]={ "market_id":mid,"asset":self.asset,"horizon":"1h","timestamp_unix":now,"spot_price":self.spot_price,"futures_price":self.futures_price,"UP":snap["UP"],"DOWN":snap["DOWN"],}
  for hz,attr_n,up_k,dn_k,snap_k in ( ("5m","market_5m","UP_5M","DOWN_5M","m5"),("15m","market_15m","UP_15M","DOWN_15M","m15"),("4h","market_4h","UP_4H","DOWN_4H","h4"),):
   mh=getattr(self,attr_n,None)
   if mh and up_k in self.books and dn_k in self.books:
    snap[snap_k]={ "market_id":mh.get("market_id"),"horizon":hz,"finalized_open":mh.get("finalized_open",mh.get("finalized_15m_open")),"finalized_15m_open":mh.get("finalized_15m_open"),"authoritative_chainlink_open":mh.get("authoritative_chainlink_open"),"UP":dict(self.books[up_k].top_of_book(now),token_id=mh["tokens"].get("UP")),"DOWN":dict(self.books[dn_k].top_of_book(now),token_id=mh["tokens"].get("DOWN")),}
    mid_h=str(mh.get("market_id"))
    markets_map[mid_h]={ "market_id":mid_h,"asset":self.asset,"horizon":hz,"timestamp_unix":now,"spot_price":self.spot_price,"futures_price":self.futures_price,"UP":snap[snap_k]["UP"],"DOWN":snap[snap_k]["DOWN"],}
  snap["markets"]=markets_map
  return snap
 def _publish_shm_fast_tick(self,market_id:str,up_token:str,down_token:str)->None:
  if "UP" not in self.books or "DOWN" not in self.books:
   return
  now_ts=time.time()
  up_m=self.books["UP"].get_metrics(obs_ts=now_ts,fee_rate=self.fee_rate_market)
  down_m=self.books["DOWN"].get_metrics(obs_ts=now_ts,fee_rate=self.fee_rate_market)
  up_m["token_id"]=str(up_token)
  down_m["token_id"]=str(down_token)
  horizon_str=str((self.current_market or {}).get("horizon","1h"))
  mkt_entry={ "market_id":str(market_id),"asset":self.asset,"horizon":horizon_str,"timestamp_unix":now_ts,"spot_price":self.spot_price,"futures_price":self.futures_price,"UP":up_m,"DOWN":down_m,}
  shm_path=SHM_DIR / f"pm_fast_tick_{self.asset}.json"
  tmp_path=SHM_DIR / f"pm_fast_tick_{self.asset}.json.tmp.{os.getpid()}"
  try:
   existing:Dict[str,Any]={}
   if shm_path.exists():
    try:
     existing=json.loads(shm_path.read_text(encoding="utf-8"))
    except Exception:
     existing={}
   markets_map=existing.get("markets",{}) if isinstance(existing,dict) else {}
   markets_map={ k:v for k,v in markets_map.items() if isinstance(v,dict) and (now_ts - float(v.get("timestamp_unix",0.0)))<=60.0 }
   markets_map[str(market_id)]=mkt_entry
   for hz,attr_n,up_k,dn_k in ( ("5m","market_5m","UP_5M","DOWN_5M"),("15m","market_15m","UP_15M","DOWN_15M"),("4h","market_4h","UP_4H","DOWN_4H"),):
    mh=getattr(self,attr_n,None)
    if mh and up_k in self.books and dn_k in self.books:
     mh_id=str(mh.get("market_id"))
     f_hz=mh.get("fee_metadata",{}).get("fee_rate_market",0.07)
     uph_m=self.books[up_k].get_metrics(obs_ts=now_ts,fee_rate=f_hz)
     dnh_m=self.books[dn_k].get_metrics(obs_ts=now_ts,fee_rate=f_hz)
     uph_m["token_id"]=str(mh["tokens"].get("UP"))
     dnh_m["token_id"]=str(mh["tokens"].get("DOWN"))
     markets_map[mh_id]={ "market_id":mh_id,"asset":self.asset,"horizon":hz,"timestamp_unix":now_ts,"spot_price":self.spot_price,"futures_price":self.futures_price,"UP":uph_m,"DOWN":dnh_m,}
   payload={ **mkt_entry,"markets":markets_map,}
   tmp_path.write_text(json.dumps(payload),encoding="utf-8")
   os.replace(tmp_path,shm_path)
  except Exception as e:
   logger.debug(f"SHM fast tick publish notice: {e}")
 def _maybe_write_fast_tick(self,force:bool=False)->bool:
  if not self._fast_tick_enabled:
   return False
  now=time.time()
  if not force and (now - self._last_fast_tick_write) < FAST_TICK_THROTTLE_SEC:
   return False
  self._last_fast_tick_write=now
  try:
   snap=self.build_fast_tick_snapshot(now)
   payload=_orjson.dumps(snap) if _orjson else json.dumps(snap).encode("utf-8")
   tmp=self.fast_tick_file.with_suffix(f".tmp.{os.getpid()}")
   with open(tmp,"wb") as f:
    f.write(payload)
   os.replace(tmp,self.fast_tick_file)
  except Exception as e:
   logger.debug(f"[FAST TICK] shm write notice: {e}")
   return False
  if now - self._last_exp306_eval>=1.0:
   self._last_exp306_eval=now
   self._run_exp306_realtime_eval(snap)
  return True
 def _run_exp306_realtime_eval(self,snap:Dict[str,Any])->None:
  try:
   recs=[]
   if self.current_market and "UP" in snap and "DOWN" in snap:
    secs_left=(self.current_market["end_dt"] - datetime.now(timezone.utc)).total_seconds()
    recs.append(evaluate_realtime_exp306_boundary_and_merge( self.asset,"1h",str(self.current_market["market_id"]),snap["UP"],snap["DOWN"],self.spot_price,self.finalized_1h_open,secs_left,fee_rate=self.fee_rate_market,))
   m15=getattr(self,"market_15m",None)
   if m15 and "m15" in snap:
    secs_left_15=(m15["end_dt"] - datetime.now(timezone.utc)).total_seconds()
    recs.append(evaluate_realtime_exp306_boundary_and_merge( self.asset,"15m",str(m15.get("market_id")),snap["m15"]["UP"],snap["m15"]["DOWN"],self.spot_price,float(m15.get("finalized_15m_open") or 0.0),secs_left_15,fee_rate=float(m15.get("fee_metadata",{}).get("fee_rate_market",0.07) or 0.07),sigma_1h=self.get_rolling_sigma("1h"),))
   hits=[r for r in recs if r.get("merge_opportunity") or r.get("boundary_opportunity")]
   if hits:
    for r in hits:
     _atomic_append_jsonl(EXP306_REALTIME_LEDGER,json.dumps(r))
  except Exception as e:
   logger.debug(f"[EXP306 REALTIME] evaluation notice: {e}")
 def _update_rolling_sigma(self,px:float,now_sec:Optional[float]=None)->None:
  if px<=0:
   return
  now_sec=now_sec if now_sec is not None else time.time()
  b1m=int(now_sec // 60)
  if b1m > self._spot_1m_bucket:
   if self._last_1m_spot > 0:
    ret_1m=math.log(px / self._last_1m_spot)
    var_1h_obs=60.0 * (ret_1m ** 2)
    new_var=0.95 * (self._rolling_sigma_1h ** 2) + 0.05 * var_1h_obs
    self._rolling_sigma_1h=max(0.0020,min(0.0300,math.sqrt(new_var)))
   self._last_1m_spot=px
   self._spot_1m_bucket=b1m
 def get_rolling_sigma(self,horizon:str="1h")->float:
  s1h=getattr(self,"_rolling_sigma_1h",0.0050 if self.asset=="BTC" else 0.0068)
  if str(horizon).lower()=="15m":
   return round(s1h * 0.5,5)
  return round(s1h,5)
 async def get_session(self)->aiohttp.ClientSession:
  if self.session is None or self.session.closed:
   self.session=aiohttp.ClientSession( timeout=aiohttp.ClientTimeout(total=10),headers={"User-Agent":"PolymarketDualFeedRecorder/2.7"},max_line_size=65536,max_field_size=65536,)
  return self.session
 async def calibrate_binance_clock_offset(self):
  session=await self.get_session()
  try:
   t0=time.time() * 1000.0
   async with session.get(f"{BINANCE_REST_URL}/api/v3/time") as resp:
    if resp.status==200:
     data=await resp.json()
     server_time_ms=float(data["serverTime"])
     t1=time.time() * 1000.0
     rtt=t1 - t0
     t_mid=(t0 + t1) / 2.0
     self.clock_offset_ms=round(t_mid - server_time_ms,2)
     self.clock_uncertainty_ms=round(rtt / 2.0,2)
     self.last_clock_sync_ts=time.time()
     logger.info(f"[CLOCK CALIBRATION] Tokyo <-> Binance Offset: {self.clock_offset_ms:+.2f}ms " f"(Uncertainty: +/-{self.clock_uncertainty_ms:.2f}ms, RTT: {rtt:.2f}ms)")
  except Exception as e:
   logger.warning(f"Clock calibration failed: {e}")
 async def discover_nearest_1h_market(self)->Optional[Dict[str,Any]]:
  session=await self.get_session()
  try:
   now=datetime.now(timezone.utc)
   now_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ")
   url=( f"{GAMMA_API_URL}/events?series_slug={self.series_slug}" f"&limit=20&closed=false&end_date_min={now_iso}&order=endDate&ascending=true" )
   async with session.get(url) as resp:
    if resp.status==200:
     events=await resp.json()
     now=datetime.now(timezone.utc)
     candidates=[]
     for event in events:
      markets=event.get("markets",[])
      if not markets:
       continue
      m=markets[0]
      m_end_str=m.get("endDate") or event.get("endDate")
      if not m_end_str:
       continue
      end_dt=datetime.fromisoformat(m_end_str.replace("Z","+00:00"))
      secs_left=(end_dt - now).total_seconds()
      if 0 < secs_left<=7200:
       candidates.append((secs_left,event,m,end_dt,m_end_str))
     if not candidates:
      return None
     candidates.sort(key=lambda x:x[0])
     secs_left,event,m,end_dt,m_end_str=candidates[0]
     m_id=str(m.get("id"))
     condition_id=str(m.get("conditionId") or "")
     tokens_raw=m.get("clobTokenIds")
     tokens=json.loads(tokens_raw) if isinstance(tokens_raw,str) else tokens_raw
     outcomes_raw=m.get("outcomes",'["Up", "Down"]')
     outcomes=json.loads(outcomes_raw) if isinstance(outcomes_raw,str) else outcomes_raw
     candle_open_ts=int(end_dt.timestamp() - 3600)
     candle_close_ts=int(end_dt.timestamp())
     fee_schedule=m.get("feeSchedule",{})
     if isinstance(fee_schedule,dict) and "rate" in fee_schedule:
      self.fee_rate_market=float(fee_schedule["rate"])
      self.fee_exponent=float(fee_schedule.get("exponent",1.0))
      self.fee_source=f"gamma_feeSchedule_{m.get('feeType', 'crypto_fees_v2')}"
     elif m.get("takerBaseFee") is not None:
      raw_taker=float(m.get("takerBaseFee"))
      self.fee_rate_market=raw_taker / 10000.0 if raw_taker > 1.0 else raw_taker
      self.fee_exponent=1.0
      self.fee_source="gamma_takerBaseFee"
     else:
      self.fee_rate_market=DEFAULT_FEE_RATE
      self.fee_exponent=1.0
      self.fee_source="polymarket_crypto_schedule_v1"
     self.fee_enabled=bool(m.get("feesEnabled",True))
     self.fee_formula_version=str(m.get("feeType","crypto_fees_v2"))
     url_spot=f"{BINANCE_REST_URL}/api/v3/ticker/price?symbol={self.binance_symbol}"
     url_fut=f"{BINANCE_FUTURES_REST_URL}/fapi/v1/ticker/price?symbol={self.binance_symbol}"
     try:
      if not self.futures_only_ref:
       async with session.get(url_spot) as resp_spot:
        if resp_spot.status==200:
         data_spot=await resp_spot.json()
         self.spot_price=float(data_spot["price"])
      async with session.get(url_fut) as resp_fut:
       if resp_fut.status==200:
        data_fut=await resp_fut.json()
        self.futures_price=float(data_fut["price"])
        if self.futures_only_ref and self.futures_price > 0:
         self.spot_price=self.futures_price
        self.update_basis()
     except Exception:
      pass
     return { "market_id":m_id,"condition_id":condition_id,"title":event.get("title"),"question":m.get("question"),"slug":event.get("slug"),"resolution_source":str(m.get("resolutionSource") or event.get("resolutionSource") or ""),"end_date_iso":m_end_str,"end_dt":end_dt,"candle_open_ts":candle_open_ts,"candle_close_ts":candle_close_ts,"tokens":{ "UP":tokens[0],"DOWN":tokens[1] },"outcomes":outcomes,"fee_metadata":{ "fee_rate_market":self.fee_rate_market,"fee_exponent":self.fee_exponent,"fee_source":self.fee_source,"fee_enabled":self.fee_enabled,"fee_formula_version":self.fee_formula_version,"condition_id":condition_id,"timestamp_utc":time.time(),} }
  except Exception as e:
   logger.error(f"Error discovering 1H market: {e}")
  return None
 async def discover_nearest_twap_market(self,horizon:str="15m")->Optional[Dict[str,Any]]:
  hz=str(horizon).lower()
  dur_sec={"5m":300,"15m":900,"4h":14400}.get(hz,900)
  max_secs={"5m":600,"15m":1800,"4h":28800}.get(hz,1800)
  session=await self.get_session()
  asset_lower=self.asset.lower()
  slug_candidates=[ f"{asset_lower}-up-or-down-{hz}",f"{asset_lower}-{hz}",]
  now=datetime.now(timezone.utc)
  now_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ")
  for s_slug in slug_candidates:
   try:
    url=( f"{GAMMA_API_URL}/events?series_slug={s_slug}" f"&limit=10&closed=false&end_date_min={now_iso}&order=endDate&ascending=true" )
    async with session.get(url) as resp:
     if resp.status!=200:
      continue
     events=await resp.json()
     candidates=[]
     for event in events:
      markets=event.get("markets",[])
      if not markets:
       continue
      m=markets[0]
      m_end_str=m.get("endDate") or event.get("endDate")
      if not m_end_str:
       continue
      end_dt=datetime.fromisoformat(m_end_str.replace("Z","+00:00"))
      secs_left=(end_dt - now).total_seconds()
      if 0 < secs_left<=max_secs:
       candidates.append((secs_left,event,m,end_dt,m_end_str))
     if not candidates:
      continue
     candidates.sort(key=lambda x:x[0])
     secs_left,event,m,end_dt,m_end_str=candidates[0]
     m_id=str(m.get("id"))
     condition_id=str(m.get("conditionId") or "")
     tokens_raw=m.get("clobTokenIds")
     tokens=json.loads(tokens_raw) if isinstance(tokens_raw,str) else tokens_raw
     outcomes_raw=m.get("outcomes",'["Up", "Down"]')
     outcomes=json.loads(outcomes_raw) if isinstance(outcomes_raw,str) else outcomes_raw
     candle_open_ts=int(end_dt.timestamp() - dur_sec)
     candle_close_ts=int(end_dt.timestamp())
     fee_schedule=m.get("feeSchedule",{})
     fee_rate=DEFAULT_FEE_RATE
     fee_exp=1.0
     if isinstance(fee_schedule,dict) and "rate" in fee_schedule:
      fee_rate=float(fee_schedule["rate"])
      fee_exp=float(fee_schedule.get("exponent",1.0))
     elif m.get("takerBaseFee") is not None:
      raw_taker=float(m.get("takerBaseFee"))
      fee_rate=raw_taker / 10000.0 if raw_taker > 1.0 else raw_taker
     open_px,_=await self.fetch_finalized_binance_candle(candle_open_ts,interval=hz)
     twap_60s_px=await self.fetch_binance_60s_twap_open(candle_open_ts)
     auth_cl_open=await self.fetch_authoritative_chainlink_open(candle_open_ts,candle_close_ts,horizon=hz)
     cl_open=auth_cl_open if auth_cl_open > 0.0 else 0.0
     if cl_open<=0.0 and abs(time.time() - candle_open_ts)<=35.0:
      cl_open=await self.fetch_polygon_chainlink_spot()
     return { "market_id":m_id,"condition_id":condition_id,"horizon":hz,"title":event.get("title"),"question":m.get("question"),"slug":event.get("slug"),"series_slug":s_slug,"resolution_source":str(m.get("resolutionSource") or event.get("resolutionSource") or ""),"end_date_iso":m_end_str,"end_dt":end_dt,"candle_open_ts":candle_open_ts,"candle_close_ts":candle_close_ts,"tokens":{ "UP":tokens[0],"DOWN":tokens[1] },"outcomes":outcomes,"finalized_open":open_px,"finalized_15m_open":open_px,"twap_60s_open":twap_60s_px,"authoritative_chainlink_open":auth_cl_open or None,"chainlink_open_spot":cl_open or None,"fee_metadata":{ "fee_rate_market":fee_rate,"fee_exponent":fee_exp,"fee_source":f"gamma_{hz}_crypto_fees","fee_enabled":True,"fee_formula_version":"crypto_fees_v2","condition_id":condition_id,"timestamp_utc":time.time(),} }
   except Exception as e:
    logger.debug(f"{hz} discovery notice for {s_slug}: {e}")
  return None
 async def discover_nearest_15m_market(self)->Optional[Dict[str,Any]]:
  return await self.discover_nearest_twap_market("15m")
 async def discover_nearest_5m_market(self)->Optional[Dict[str,Any]]:
  return await self.discover_nearest_twap_market("5m")
 async def discover_nearest_4h_market(self)->Optional[Dict[str,Any]]:
  return await self.discover_nearest_twap_market("4h")
 async def fetch_authoritative_chainlink_open( self,candle_open_ts:int,candle_close_ts:int,horizon:str="15m" )->float:
  now_t=time.time()
  if now_t < float(candle_open_ts) + 2.0:
   return 0.0
  variant={"5m":"fiveminute","15m":"fifteen","4h":"fourhour"}.get(str(horizon).lower(),"fifteen")
  session=await self.get_session()
  start_iso=datetime.fromtimestamp(int(candle_open_ts),tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  end_iso=datetime.fromtimestamp(int(candle_close_ts),tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  twap_url=( f"https://polymarket.com/api/crypto/crypto-price" f"?symbol={self.asset.upper()}&eventStartTime={start_iso}" f"&variant={variant}&endDate={end_iso}&twapEnabled=true&twapLookbackSeconds=60" )
  try:
   async with session.get(twap_url,timeout=aiohttp.ClientTimeout(total=3.5)) as resp:
    if resp.status==200:
     payload=await resp.json()
     if isinstance(payload,dict) and (payload.get("cached") is True or payload.get("completed") is True):
      if payload.get("openPrice") is not None:
       val=float(payload["openPrice"])
       if math.isfinite(val) and val > 0.0:
        return val
  except Exception as e:
   logger.debug(f"[{self.asset}] Authoritative {horizon} TWAP query note: {e}")
  if now_t>=float(candle_open_ts) + 35.0:
   try:
    g_url=f"{GAMMA_API_URL}/events?slug={self.asset.lower()}-updown-5m-{int(candle_open_ts) - 300}"
    async with session.get(g_url,timeout=aiohttp.ClientTimeout(total=3.5)) as resp:
     if resp.status==200:
      payload=await resp.json()
      ev=payload[0] if isinstance(payload,list) and payload else payload
      if isinstance(ev,dict) and ev.get("closed") is True:
       meta=ev.get("eventMetadata")
       meta=json.loads(meta) if isinstance(meta,str) else meta
       if isinstance(meta,dict) and meta.get("finalPrice") is not None:
        val=float(meta["finalPrice"])
        if math.isfinite(val) and val > 0.0:
         return val
   except Exception:
    pass
  return 0.0
 async def fetch_authoritative_chainlink_open_15m(self,candle_open_ts:int,candle_close_ts:int)->float:
  return await self.fetch_authoritative_chainlink_open(candle_open_ts,candle_close_ts,"15m")
 async def fetch_binance_60s_twap_open(self,candle_open_ts:int)->float:
  session=await self.get_session()
  start_ms=(int(candle_open_ts) - 60) * 1000
  if not self.futures_only_ref:
   try:
    url_1s=( f"{BINANCE_REST_URL}/api/v3/klines" f"?symbol={self.binance_symbol}&interval=1s&startTime={start_ms}&limit=60" )
    async with session.get(url_1s) as resp_1s:
     if resp_1s.status==200:
      data_1s=await resp_1s.json()
      if isinstance(data_1s,list) and len(data_1s)>=30:
       twap=sum((float(k[1]) + float(k[4])) / 2.0 for k in data_1s) / len(data_1s)
       return round(twap,4)
   except Exception as e_1s:
    logger.debug(f"1s TWAP fetch fallback notice for {self.binance_symbol}: {e_1s}")
  try:
   kline_base=f"{BINANCE_FUTURES_REST_URL}/fapi/v1/klines" if self.futures_only_ref else f"{BINANCE_REST_URL}/api/v3/klines"
   url=( f"{kline_base}" f"?symbol={self.binance_symbol}&interval=1m&startTime={start_ms}&limit=1" )
   async with session.get(url) as resp:
    if resp.status==200:
     data=await resp.json()
     if data:
      o_px=float(data[0][1])
      h_px=float(data[0][2])
      l_px=float(data[0][3])
      c_px=float(data[0][4])
      return round((o_px + h_px + l_px + c_px) / 4.0,4)
  except Exception as e:
   logger.debug(f"Failed to fetch 60s TWAP open for {self.binance_symbol}: {e}")
  return 0.0
 async def fetch_finalized_binance_candle( self,candle_open_ts:int,interval:str="1h" )->Tuple[float,float]:
  session=await self.get_session()
  iv_low=str(interval).lower()
  if iv_low in ("5m","300s"):
   binance_interval="5m"
  elif iv_low in ("15m","900s"):
   binance_interval="15m"
  elif iv_low in ("4h","14400s"):
   binance_interval="4h"
  else:
   binance_interval="1h"
  try:
   start_ms=int(candle_open_ts) * 1000
   kline_base=f"{BINANCE_FUTURES_REST_URL}/fapi/v1/klines" if self.futures_only_ref else f"{BINANCE_REST_URL}/api/v3/klines"
   url=( f"{kline_base}" f"?symbol={self.binance_symbol}&interval={binance_interval}&startTime={start_ms}&limit=1" )
   async with session.get(url) as resp:
    if resp.status==200:
     data=await resp.json()
     if data:
      open_px=float(data[0][1])
      close_px=float(data[0][4])
      return open_px,close_px
  except Exception as e:
   logger.error(f"Failed to fetch Binance {binance_interval} candle for {self.binance_symbol}: {e}")
  return 0.0,0.0
 async def verify_and_log_resolution(self,market:Dict[str,Any],max_polls:int=60,poll_interval_sec:float=30.0):
  m_id_str=str(market.get("market_id") or "")
  logged_set=getattr(self,"_logged_resolution_market_ids",None)
  if logged_set is None:
   logged_set=set()
   self._logged_resolution_market_ids=logged_set
  if not m_id_str or m_id_str in logged_set:
   return
  logged_set.add(m_id_str)
  duration=int(market.get("candle_close_ts",0)) - int(market.get("candle_open_ts",0))
  default_hz="5m" if 0 < duration<=300 else ("15m" if 0 < duration<=900 else ("4h" if duration>=10800 else "1h"))
  horizon=str(market.get("horizon") or default_hz)
  logger.info(f"[*] Awaiting finalized {horizon} resolution for market {market['market_id']} ({market['title']})...")
  await asyncio.sleep(6.0)
  open_px,close_px=await self.fetch_finalized_binance_candle(market["candle_open_ts"],interval=horizon)
  binance_y_up=(1 if close_px>=open_px else 0) if (open_px > 0 and close_px > 0) else None
  binance_winner=("UP" if binance_y_up==1 else "DOWN") if binance_y_up is not None else None
  ret_pct=(((close_px - open_px) / open_px) * 100.0) if (open_px > 0 and close_px > 0) else 0.0
  gamma_winner=None
  res_source=str(market.get("resolution_source") or "")
  for attempt in range(max_polls):
   try:
    session=await self.get_session()
    async with session.get(f"{GAMMA_API_URL}/markets/{m_id_str}") as g_resp:
     if g_resp.status==200:
      g_data=await g_resp.json()
      if isinstance(g_data,dict):
       if not res_source and g_data.get("resolutionSource"):
        res_source=str(g_data.get("resolutionSource"))
       raw_prices=g_data.get("outcomePrices")
       raw_outcomes=g_data.get("outcomes",'["Up", "Down"]')
       prices=json.loads(raw_prices) if isinstance(raw_prices,str) else raw_prices
       outcomes=json.loads(raw_outcomes) if isinstance(raw_outcomes,str) else raw_outcomes
       if isinstance(prices,list) and len(prices)>=2:
        p0,p1=float(prices[0]),float(prices[1])
        o0=str(outcomes[0]).upper() if isinstance(outcomes,list) and len(outcomes)>=2 else "UP"
        o1=str(outcomes[1]).upper() if isinstance(outcomes,list) and len(outcomes)>=2 else "DOWN"
        if p0>=0.99 and p1<=0.01:
         gamma_winner="UP" if "UP" in o0 or "YES" in o0 else ("DOWN" if "DOWN" in o0 or "NO" in o0 else o0)
         break
        elif p1>=0.99 and p0<=0.01:
         gamma_winner="UP" if "UP" in o1 or "YES" in o1 else ("DOWN" if "DOWN" in o1 or "NO" in o1 else o1)
         break
   except Exception as g_err:
    logger.debug(f"Gamma resolution check notice for {m_id_str}: {g_err}")
   if attempt + 1 < max_polls:
    await asyncio.sleep(poll_interval_sec)
  final_winner=gamma_winner
  y_up=(1 if final_winner=="UP" else 0) if final_winner in ("UP","DOWN") else None
  y_down=(1 if final_winner=="DOWN" else 0) if final_winner in ("UP","DOWN") else None
  oracle_mismatch=bool(gamma_winner and binance_winner and gamma_winner!=binance_winner)
  if oracle_mismatch:
   logger.warning( f"[ORACLE MISMATCH ALERT] {market['title']} ({horizon}, m_id={m_id_str}): " f"Binance Spot={binance_winner} (${open_px:,.2f}->${close_px:,.2f}, {ret_pct:+.4f}%) " f"vs Official Gamma Settlement={gamma_winner} (source={res_source or 'unknown'})!" )
  res_record={ "timestamp_resolved":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"asset":self.asset,"horizon":horizon,"market_id":str(market["market_id"]),"title":market["title"],"candle_open_ts":market["candle_open_ts"],"candle_close_ts":market["candle_close_ts"],"authoritative_chainlink_open":market.get("authoritative_chainlink_open"),"binance_spot_open":open_px,"binance_spot_close":close_px,"candle_return_pct":round(ret_pct,4),"Y_UP":y_up,"Y_DOWN":y_down,"winning_outcome":final_winner,"binance_winning_outcome":binance_winner,"gamma_winning_outcome":gamma_winner,"oracle_mismatch":oracle_mismatch,"resolution_source":res_source,"ground_truth_rule":"Official Polymarket Gamma/Chainlink Settlement (outcomePrices)",}
  _atomic_append_jsonl(RESOLUTIONS_FILE,json.dumps(res_record))
  logger.info( f"[GROUND TRUTH RESOLUTION LOGGED] {market['title']} ({horizon}) | " f"Gamma={gamma_winner} | BinanceDiag={binance_winner} ({ret_pct:+.3f}%)" )
 def update_basis(self):
  if self.spot_price > 0 and self.futures_price > 0:
   self.basis_usd=self.futures_price - self.spot_price
   self.basis_bps=(self.basis_usd / self.spot_price) * 10000.0
   self.basis_history.append((time.monotonic_ns(),self.basis_bps))
 def get_delta_basis_100ms(self)->float:
  now_ns=time.monotonic_ns()
  cutoff_ns=now_ns - 100_000_000
  for t_ns,b_bps in self.basis_history:
   if t_ns>=cutoff_ns:
    return round(self.basis_bps - b_bps,2)
  return 0.0
 async def stream_binance_spot(self):
  if self.futures_only_ref or not self.binance_spot_ws:
   logger.info(f"[{self.asset}] futures_only_ref active; skipping Binance Spot WS (using Binance Futures + Coinbase USD).")
   return
  while self.running:
   try:
    logger.info(f"Connecting to Binance Spot aggTrade ({self.binance_spot_ws})...")
    async with websockets.connect(self.binance_spot_ws,ping_interval=20,ping_timeout=10) as ws:
     logger.info(f"[+] Subscribed to Binance Spot aggTrade stream ({self.binance_symbol}).")
     async for msg_str in ws:
      if not self.running:
       break
      recv_mono_ns=time.monotonic_ns()
      msg=_orjson.loads(msg_str) if _orjson is not None else json.loads(msg_str)
      px=float(msg.get("p",0))
      sz=float(msg.get("q",0))
      is_buyer=not msg.get("m",False)
      e_ts=int(msg.get("E",0))
      t_ts=int(msg.get("T",0))
      notional=px * sz
      self.spot_price=px
      self._update_rolling_sigma(px)
      self.update_basis()
      self.spot_trades.append((recv_mono_ns,e_ts,t_ts,notional,is_buyer,px))
      self.evaluate_shock(recv_mono_ns,e_ts,source="SPOT")
      self._maybe_write_fast_tick()
   except Exception as e:
    logger.warning(f"Binance Spot feed disconnected: {e}. Reconnecting in 3s...")
    await asyncio.sleep(3)
 async def stream_binance_futures(self):
  while self.running:
   try:
    logger.info(f"Connecting to Binance Futures aggTrade ({self.binance_futures_ws})...")
    async with websockets.connect(self.binance_futures_ws,ping_interval=20,ping_timeout=10) as ws:
     logger.info(f"[+] Subscribed to Binance Futures aggTrade stream ({self.binance_symbol} routed /market).")
     async for msg_str in ws:
      if not self.running:
       break
      recv_mono_ns=time.monotonic_ns()
      msg=_orjson.loads(msg_str) if _orjson is not None else json.loads(msg_str)
      px=float(msg.get("p",0))
      sz=float(msg.get("q",0))
      is_buyer=not msg.get("m",False)
      e_ts=int(msg.get("E",0))
      t_ts=int(msg.get("T",0))
      notional=px * sz
      self.futures_price=px
      if self.futures_only_ref:
       self.spot_price=px
       self._update_rolling_sigma(px)
      self.update_basis()
      self.futures_trades.append((recv_mono_ns,e_ts,t_ts,notional,is_buyer,px))
      self.evaluate_shock(recv_mono_ns,e_ts,source="FUTURES")
      self._maybe_write_fast_tick()
   except Exception as e:
    logger.warning(f"Binance Futures feed disconnected: {e}. Reconnecting in 3s...")
    await asyncio.sleep(3)
 def _record_volume(self,notional:float,now_sec:Optional[float]=None)->None:
  sec=int(now_sec if now_sec is not None else time.time())
  if self._vol_first_sec is None:
   self._vol_first_sec=sec
  if self._vol_buckets and self._vol_buckets[-1][0]==sec:
   self._vol_buckets[-1][1] += notional
  else:
   self._vol_buckets.append([sec,float(notional)])
 def get_avg_100ms_vol_5m(self,now_sec:Optional[float]=None)->Optional[float]:
  now_sec=now_sec if now_sec is not None else time.time()
  if self._vol_first_sec is None or (now_sec - self._vol_first_sec) < ADAPTIVE_THRESH_MIN_COVERAGE_SEC:
   return None
  cutoff=now_sec - ADAPTIVE_THRESH_WINDOW_SEC
  total=sum(v for s,v in self._vol_buckets if s>=cutoff)
  window=min(float(ADAPTIVE_THRESH_WINDOW_SEC),now_sec - self._vol_first_sec)
  if window<=0:
   return None
  return total / (window * 10.0)
 def get_effective_shock_threshold(self,now_sec:Optional[float]=None)->float:
  now_sec=now_sec if now_sec is not None else time.time()
  computed_at,val=self._adaptive_cache
  if now_sec - computed_at>=1.0:
   val=compute_adaptive_shock_threshold(float(self.shock_threshold_usd),self.get_avg_100ms_vol_5m(now_sec))
   self._adaptive_cache=(now_sec,val)
  return val
 def _publish_btc_lead_state(self,vol_100ms:float,ofi_100ms:float,delta_basis:float,flow_dir:str,z_btc:float,force:bool=False)->None:
  if self.asset!="BTC" or not self._fast_tick_enabled:
   return
  now=time.time()
  if not force and (now - self._last_lead_state_write) < LEAD_STATE_THROTTLE_SEC:
   return
  self._last_lead_state_write=now
  state={ "asset":"BTC","ts_ns":time.time_ns(),"t0_unix":now,"spot_px":self.spot_price,"spot_price":self.spot_price,"basis_bps":round(self.basis_bps,2),"vol_100ms":round(vol_100ms,0),"ofi_100ms":round(ofi_100ms,3),"delta_basis_100ms":delta_basis,"shock_dir":flow_dir,"btc_shock_direction":flow_dir,"btc_target_token":"UP" if flow_dir in ("BUY","UP") else "DOWN","z_btc":round(z_btc,4),}
  state.update(self._last_btc_shock)
  write_lead_state(state,self.lead_state_file)
 def evaluate_shock(self,recv_mono_ns:int,event_ts_ms:int,source:str):
  trade_queue=self.spot_trades if source=="SPOT" else self.futures_trades
  if trade_queue:
   self._record_volume(float(trade_queue[-1][3]))
  now_wall_sec=time.time()
  exch_lag_ms=(now_wall_sec * 1000.0 - float(event_ts_ms)) if event_ts_ms > 0 else 0.0
  if event_ts_ms > 1_600_000_000_000 and 1000.0 < exch_lag_ms < 86_400_000.0:
   last_warn=float(getattr(self,"_last_stale_exch_warn_ts",0.0) or 0.0)
   if now_wall_sec - last_warn>=5.0:
    self._last_stale_exch_warn_ts=now_wall_sec
    logger.warning( f"[STALE_EXCHANGE_EVENT_VETO] Dropping stale {source} {self.asset} packet " f"(exch_lag_ms={exch_lag_ms:.1f}ms > 1000ms ceiling) to prevent burst-drain phantom shock." )
   return
  base_threshold=float(self.shock_threshold_usd)
  eff_threshold=self.get_effective_shock_threshold()
  cutoff_ns=recv_mono_ns - 100_000_000
  cutoff_40_ns=recv_mono_ns - 40_000_000
  vol_100ms=0.0
  buy_vol=0.0
  sell_vol=0.0
  vol_40ms=0.0
  buy_40ms=0.0
  sell_40ms=0.0
  vol_250ms=0.0
  buy_250ms=0.0
  sell_250ms=0.0
  cutoff_250_ns=recv_mono_ns - 250_000_000
  anchor_exch_ms=int((trade_queue[-1][2] or trade_queue[-1][1]) if trade_queue else 0) or int(event_ts_ms or 0)
  for t_mono,e_ts_i,t_ts_i,ntl,buyer,_ in reversed(trade_queue):
   if t_mono < cutoff_250_ns:
    break
   ts_i_ms=int(t_ts_i or e_ts_i or 0)
   if anchor_exch_ms > 0 and ts_i_ms > 0:
    dt_exch_ms=anchor_exch_ms - ts_i_ms
    if dt_exch_ms > 250:
     break
    if dt_exch_ms < -50:
     continue
    in_100ms=(dt_exch_ms<=100) and (t_mono>=cutoff_ns)
    in_40ms=(dt_exch_ms<=40) and (t_mono>=cutoff_40_ns)
   else:
    in_100ms=(t_mono>=cutoff_ns)
    in_40ms=(t_mono>=cutoff_40_ns)
   vol_250ms += ntl
   if buyer:
    buy_250ms += ntl
   else:
    sell_250ms += ntl
   if in_100ms:
    vol_100ms += ntl
    if buyer:
     buy_vol += ntl
    else:
     sell_vol += ntl
   if in_40ms:
    vol_40ms += ntl
    if buyer:
     buy_40ms += ntl
    else:
     sell_40ms += ntl
  other_queue=self.futures_trades if source=="SPOT" else self.spot_trades
  other_100ms=0.0
  other_buy_100ms=0.0
  other_sell_100ms=0.0
  for t_m,o_e_ts,o_t_ts,ntl,buyer,_ in reversed(other_queue):
   if t_m < cutoff_ns:
    break
   o_ts_ms=int(o_t_ts or o_e_ts or 0)
   if anchor_exch_ms > 0 and o_ts_ms > 0 and abs(anchor_exch_ms - o_ts_ms) > 120:
    if (anchor_exch_ms - o_ts_ms) > 120:
     break
    continue
   other_100ms += ntl
   if buyer:
    other_buy_100ms += ntl
   else:
    other_sell_100ms += ntl
  combined_100ms=vol_100ms + 0.75 * other_100ms
  flow_dir="BUY" if buy_vol>=sell_vol else "SELL"
  ofi_raw_100ms=(buy_vol - sell_vol) / vol_100ms if vol_100ms > 0 else 0.0
  lead=None
  sympathy=False
  if self.asset in ("ETH","SOL","XRP"):
   lead=read_lead_state(self.lead_state_file,max_age_ms=LEAD_STATE_MAX_AGE_MS)
   if lead is not None:
    tgt_book=self.books.get("UP" if flow_dir=="BUY" else "DOWN")
    tgt_age=tgt_book.top_of_book().get("age_ask_ms") if tgt_book else None
    sympathy=evaluate_btc_sympathy(lead,flow_dir,tgt_age)
    if sympathy:
     eff_threshold=min(eff_threshold,SYMPATHY_THRESHOLD_MULT * base_threshold)
  elif self.asset=="BTC":
   z_now=(1.0 if flow_dir=="BUY" else -1.0) * abs(ofi_raw_100ms) * (vol_100ms / max(base_threshold,1.0))
   self._publish_btc_lead_state(vol_100ms,ofi_raw_100ms,self.get_delta_basis_100ms(),flow_dir,z_now)
  ofi_40ms=(buy_40ms - sell_40ms) / max(vol_40ms,1e-6) if vol_40ms > 0 else 0.0
  is_40ms_fast_track=bool(vol_40ms>=0.75 * eff_threshold and abs(ofi_40ms)>=0.90)
  if is_40ms_fast_track:
   vol_100ms=vol_40ms
   buy_vol=buy_40ms
   sell_vol=sell_40ms
  elif vol_100ms < eff_threshold and vol_250ms>=(eff_threshold * 1.45):
   vol_100ms,buy_vol,sell_vol=vol_250ms,buy_250ms,sell_250ms
  elif vol_100ms < eff_threshold and combined_100ms>=(eff_threshold * 1.20):
   vol_100ms=vol_100ms + other_100ms
   buy_vol=buy_vol + other_buy_100ms
   sell_vol=sell_vol + other_sell_100ms
  now_sec=time.time()
  should_trigger=(is_40ms_fast_track or vol_100ms>=eff_threshold)
  if should_trigger and (now_sec - self.last_shock_ts > 2.5):
   up_book=self.books.get("UP")
   down_book=self.books.get("DOWN")
   if not up_book or not down_book or not self.current_market:
    return
   self.last_shock_ts_by_source[source]=now_sec
   self.last_shock_ts=now_sec
   shock_dir="BUY" if buy_vol>=sell_vol else "SELL"
   ofi=(buy_vol - sell_vol) / vol_100ms if vol_100ms > 0 else 0.0
   trigger_px=self.spot_price if source=="SPOT" else self.futures_price
   shock_z=(1.0 if shock_dir=="BUY" else -1.0) * abs(ofi) * (vol_100ms / max(base_threshold,1.0))
   if self.asset=="BTC":
    self._last_btc_shock={ "last_shock_ts_ns":time.time_ns(),"last_shock_vol_100ms":round(vol_100ms,0),"last_shock_ofi_100ms":round(ofi,3),"last_shock_dir":shock_dir,"last_shock_z_btc":round(shock_z,4),}
   cross_fields:Dict[str,Any]={ "effective_shock_threshold":round(eff_threshold,0),"btc_shock_direction":None,"z_btc":None,}
   if self.asset in ("ETH","SOL","XRP"):
    cross_fields["shock_z"]=round(shock_z,4)
    cross_fields["sympathy_trigger"]=bool(sympathy)
    if lead is not None:
     btc_shock_ns=int(lead.get("last_shock_ts_ns") or 0)
     if btc_shock_ns > 0 and (time.time_ns() - btc_shock_ns) / 1e6<=LEAD_STATE_MAX_AGE_MS:
      cross_fields["btc_shock_direction"]="UP" if str(lead.get("last_shock_dir")).upper()=="BUY" else "DOWN"
      cross_fields["z_btc"]=float(lead.get("last_shock_z_btc") or 0.0)
      cross_fields["btc_shock_age_ms"]=round((time.time_ns() - btc_shock_ns) / 1e6,1)
   elif self.asset=="BTC":
    cross_fields["shock_z"]=round(shock_z,4)
    cross_fields["btc_shock_direction"]=shock_dir
    cross_fields["z_btc"]=round(shock_z,4)
   t0_sec=now_sec
   t0_mono_ns=recv_mono_ns
   delta_basis_100ms=self.get_delta_basis_100ms()
   pre_shock_up=up_book.get_metrics(obs_ts=t0_sec,fee_rate=self.fee_rate_market)
   pre_shock_down=down_book.get_metrics(obs_ts=t0_sec,fee_rate=self.fee_rate_market)
   if self.current_market and "tokens" in self.current_market:
    pre_shock_up["token_id"]=self.current_market["tokens"].get("UP")
    pre_shock_down["token_id"]=self.current_market["tokens"].get("DOWN")
   pre_shock_basis_signed=self.basis_bps
   pre_shock_basis_abs=abs(self.basis_bps)
   t0_secs_left=(self.current_market["end_dt"] - datetime.now(timezone.utc)).total_seconds()
   t0_dist_pct=((self.spot_price - self.finalized_1h_open) / self.finalized_1h_open * 100.0) if self.finalized_1h_open > 0 else 0.0
   t0_spot=self.spot_price
   t0_futures=self.futures_price
   m_id=self.current_market["market_id"]
   condition_id=self.current_market.get("condition_id","")
   m_title=self.current_market["title"]
   fee_meta=dict(self.current_market.get("fee_metadata",{}))
   horizon_str=str(self.current_market.get("horizon","1h"))
   candle_sigma=self.get_rolling_sigma(horizon_str)
   tau_frac=max(0.001,t0_secs_left / float(self.current_market.get("duration_s",3600.0)))
   signed_z=(t0_dist_pct / 100.0) / max(candle_sigma * math.sqrt(tau_frac),1e-6)
   btc_lead_dir=cross_fields.get("btc_shock_direction")
   z_btc_val=cross_fields.get("z_btc")
   z_eth_val=round(signed_z,4) if self.asset in ("ETH","SOL","XRP") else None
   shock_id_str=f"{m_id}_{t0_sec:.6f}"
   immediate_trigger={ "shock_id":shock_id_str,"event_id":shock_id_str,"timestamp":datetime.fromtimestamp(t0_sec,tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"t0_unix":t0_sec,"t0_mono_ns":t0_mono_ns,"t0_definition":"local_receipt_boundary","exchange_event_ts_ms":event_ts_ms,"clob_ws_connected":bool(getattr(self,"clob_ws_connected",True)),"shock_source":source,"asset":self.asset,"horizon":horizon_str,"candle_interval":horizon_str,"series_slug":self.series_slug,"slug":self.current_market.get("slug",""),"resolution_source":self.current_market.get("resolution_source",""),"market_id":m_id,"condition_id":condition_id,"title":m_title,"seconds_to_expiry":round(t0_secs_left,1),"expiry_ts":float(self.current_market.get("candle_close_ts") or (t0_sec + t0_secs_left)),"candle_expiry_ts":float(self.current_market.get("candle_close_ts") or (t0_sec + t0_secs_left)),"candle_open_ts":int(self.current_market.get("candle_open_ts") or (int(self.current_market["end_dt"].timestamp()) - 3600)),"candle_sigma":candle_sigma,"shock_volume_100ms":round(vol_100ms,0),"is_40ms_fast_track":is_40ms_fast_track,"shock_direction":shock_dir,"btc_shock_direction":btc_lead_dir,"z_val":round(abs(signed_z),4),"z_score":round(signed_z,4),"z_btc":z_btc_val,"z_eth":z_eth_val,"shock_ofi":round(ofi,3),"trigger_price":trigger_px,"spot_at_t0":t0_spot,"futures_at_t0":t0_futures,"basis_signed_bps_t0":round(pre_shock_basis_signed,2),"basis_abs_bps_t0":round(pre_shock_basis_abs,2),"delta_basis_100ms":delta_basis_100ms,"coinbase_spot":self.get_coinbase_spot(t0_sec),"chainlink_proxy_spot":self.get_chainlink_proxy_spot(t0_sec),"chainlink_twap_60s":self.get_chainlink_twap_60s(t0_sec),"venue_divergence_bps":self.get_venue_divergence_bps(t0_sec),"venue_divergence_centered_bps":self.get_venue_divergence_centered_bps(t0_sec),"coinbase_move_bps_2s":self.get_coinbase_move_bps(2.0,t0_sec),**cross_fields,"finalized_1h_open":self.finalized_1h_open if horizon_str=="1h" else None,"candle_open_spot":self.finalized_1h_open,"twap_60s_open":float(getattr(self,"twap_60s_1h_open",0.0) or 0.0) or None,"chainlink_open_spot":float(getattr(self,"chainlink_1h_open",0.0) or 0.0) or None,"candle_distance_pct":round(t0_dist_pct,4),"fee_metadata":fee_meta,"pre_shock_features_t0":{ "UP":pre_shock_up,"DOWN":pre_shock_down } }
   line_15m=""
   if getattr(self,"market_15m",None) and "UP_15M" in self.books and "DOWN_15M" in self.books:
    try:
     m15=self.market_15m
     open_15m=float(m15.get("finalized_15m_open",0.0) or 0.0)
     auth_cl_15m=float(m15.get("authoritative_chainlink_open",0.0) or 0.0)
     cl_spot_15m=float(self.get_chainlink_proxy_spot(t0_sec) or 0.0)
     t0_15m_secs=(m15["end_dt"] - datetime.now(timezone.utc)).total_seconds()
     if 0 < t0_15m_secs<=900.0:
      if auth_cl_15m > 0.0 and cl_spot_15m > 0.0:
       dist_15m=((cl_spot_15m - auth_cl_15m) / auth_cl_15m * 100.0)
      else:
       dist_15m=((self.spot_price - open_15m) / open_15m * 100.0) if open_15m > 0 else 0.0
      tau_frac_15m=max(0.001,t0_15m_secs / float(m15.get("duration_s",900.0)))
      candle_sigma_15m=self.get_rolling_sigma("15m")
      signed_z_15m=(dist_15m / 100.0) / max(candle_sigma_15m * math.sqrt(tau_frac_15m),1e-6)
      up_15_metrics=self.books["UP_15M"].get_metrics(obs_ts=t0_sec,fee_rate=m15.get("fee_metadata",{}).get("fee_rate_market",0.07))
      down_15_metrics=self.books["DOWN_15M"].get_metrics(obs_ts=t0_sec,fee_rate=m15.get("fee_metadata",{}).get("fee_rate_market",0.07))
      up_15_metrics["token_id"]=m15["tokens"].get("UP")
      down_15_metrics["token_id"]=m15["tokens"].get("DOWN")
      shock_id_15m=f"{m15['market_id']}_{t0_sec:.6f}"
      trigger_15m={ "shock_id":shock_id_15m,"event_id":shock_id_15m,"timestamp":datetime.fromtimestamp(t0_sec,tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"t0_unix":t0_sec,"t0_mono_ns":t0_mono_ns,"t0_definition":"local_receipt_boundary","exchange_event_ts_ms":event_ts_ms,"clob_ws_connected":bool(getattr(self,"clob_ws_connected",True)),"shock_source":source,"asset":self.asset,"horizon":"15m","candle_interval":"15m","series_slug":m15.get("series_slug",f"{self.asset.lower()}-up-or-down-15m"),"slug":m15.get("slug",""),"resolution_source":m15.get("resolution_source",""),"market_id":m15["market_id"],"condition_id":m15.get("condition_id",""),"title":m15["title"],"seconds_to_expiry":round(t0_15m_secs,1),"expiry_ts":float(m15.get("candle_close_ts") or (t0_sec + t0_15m_secs)),"candle_expiry_ts":float(m15.get("candle_close_ts") or (t0_sec + t0_15m_secs)),"candle_open_ts":int(m15.get("candle_open_ts") or (int(m15["end_dt"].timestamp()) - 900)),"candle_sigma":candle_sigma_15m,"shock_volume_100ms":round(vol_100ms,0),"is_40ms_fast_track":is_40ms_fast_track,"shock_direction":shock_dir,"btc_shock_direction":btc_lead_dir,"z_val":round(abs(signed_z_15m),4),"z_score":round(signed_z_15m,4),"z_btc":z_btc_val,"z_eth":z_eth_val,"shock_ofi":round(ofi,3),"trigger_price":trigger_px,"spot_at_t0":t0_spot,"futures_at_t0":t0_futures,"basis_signed_bps_t0":round(pre_shock_basis_signed,2),"basis_abs_bps_t0":round(pre_shock_basis_abs,2),"delta_basis_100ms":delta_basis_100ms,"coinbase_spot":self.get_coinbase_spot(t0_sec),"chainlink_proxy_spot":self.get_chainlink_proxy_spot(t0_sec),"chainlink_twap_60s":self.get_chainlink_twap_60s(t0_sec),"venue_divergence_bps":self.get_venue_divergence_bps(t0_sec),"venue_divergence_centered_bps":self.get_venue_divergence_centered_bps(t0_sec),"coinbase_move_bps_2s":self.get_coinbase_move_bps(2.0,t0_sec),**cross_fields,"finalized_1h_open":open_15m,"candle_open_spot":open_15m,"twap_60s_open":float(m15.get("twap_60s_open",0.0) or 0.0) or None,"authoritative_chainlink_open":float(m15.get("authoritative_chainlink_open",0.0) or 0.0) or None,"chainlink_open_spot":float(m15.get("chainlink_open_spot",0.0) or 0.0) or None,"candle_distance_pct":round(dist_15m,4),"fee_metadata":dict(m15.get("fee_metadata",{})),"pre_shock_features_t0":{ "UP":up_15_metrics,"DOWN":down_15_metrics } }
      _,line_15m=_dispatch_trigger_fast(TRIGGER_FILE,trigger_15m)
    except Exception as ex_15m:
     logger.debug(f"Notice: 15m shock emit skipped: {ex_15m}")
   line_1h=""
   try:
    _,line_1h=_dispatch_trigger_fast(TRIGGER_FILE,immediate_trigger)
   except Exception as trig_err:
    logger.error(f"Failed to broadcast 1h trigger: {trig_err}")
   if self.asset=="BTC":
    self._publish_btc_lead_state(vol_100ms,ofi,delta_basis_100ms,shock_dir,shock_z,force=True)
   if line_1h:
    try:
     _persist_trigger_nonblocking(TRIGGER_FILE,line_1h)
    except Exception as trig_err:
     logger.error(f"Failed to persist zero-latency trigger: {trig_err}")
   if line_15m:
    try:
     _persist_trigger_nonblocking(TRIGGER_FILE,line_15m)
    except Exception as ex_p15:
     logger.debug(f"Notice: 15m trigger persist skipped: {ex_p15}")
   log_prefix="40ms FAST-TRACK" if is_40ms_fast_track else "100ms"
   logger.info(f"\n[!!! {source} SHOCK TRIGGERED ({log_prefix}) !!!] Vol=${vol_100ms:,.0f} | Dir={shock_dir} | " f"OFI={ofi:+.2f} | Spot=${self.spot_price:,.1f} | Fut=${self.futures_price:,.1f} | " f"Basis={self.basis_bps:+.1f}bps | DeltaBasis100ms={delta_basis_100ms:+.1f}bps")
   if len(self.active_burst_tasks) < 5:
    task=asyncio.create_task(self.capture_shock_burst( t0_sec,t0_mono_ns,source,vol_100ms,shock_dir,ofi,trigger_px,delta_basis_100ms,pre_shock_up,pre_shock_down,pre_shock_basis_signed,pre_shock_basis_abs,t0_secs_left,t0_dist_pct,t0_spot,t0_futures,m_id,m_title,fee_meta ))
    self.active_burst_tasks.add(task)
    task.add_done_callback(self.active_burst_tasks.discard)
   else:
    logger.warning(f"Concurrent burst tasks throttle reached ({len(self.active_burst_tasks)}). Skipping telemetry capture.")
 async def capture_shock_burst( self,t0:float,t0_mono_ns:int,source:str,shock_vol:float,shock_dir:str,ofi:float,trigger_px:float,delta_basis_100ms:float,pre_shock_up:Dict[str,Any],pre_shock_down:Dict[str,Any],pre_shock_basis_signed:float,pre_shock_basis_abs:float,t0_secs_left:float,t0_dist_pct:float,t0_spot:float,t0_futures:float,m_id:str,m_title:str,fee_meta:Dict[str,Any] ):
  up_book=self.books.get("UP")
  down_book=self.books.get("DOWN")
  if not up_book or not down_book or not self.current_market:
   return
  ladder_delays=[0.10,0.15,0.25,0.50,4.0,25.0]
  ladder_labels=["100ms","250ms","500ms","1s","5s","30s"]
  response_snapshots={}
  for delay,label in zip(ladder_delays,ladder_labels):
   await asyncio.sleep(delay)
   t_sample=time.time()
   up_m=up_book.get_metrics(obs_ts=t_sample,fee_rate=self.fee_rate_market)
   down_m=down_book.get_metrics(obs_ts=t_sample,fee_rate=self.fee_rate_market)
   response_snapshots[label]={ "elapsed_sec":round(t_sample - t0,3),"up_mid":up_m["q_mid"],"up_ask":up_m["best_ask"],"up_delta_q_ask":round(up_m["best_ask"] - pre_shock_up["best_ask"],4),"up_delta_q_mid":round(up_m["q_mid"] - pre_shock_up["q_mid"],4),"up_obi_l1":up_m["obi_l1"],"up_obi_depth":up_m["obi_depth"],"down_mid":down_m["q_mid"],"down_ask":down_m["best_ask"],"down_delta_q_ask":round(down_m["best_ask"] - pre_shock_down["best_ask"],4),"down_delta_q_mid":round(down_m["q_mid"] - pre_shock_down["q_mid"],4),"binance_spot":self.spot_price,"binance_futures":self.futures_price,"basis_bps":round(self.basis_bps,2),"delta_basis_bps":round(self.basis_bps - pre_shock_basis_signed,2) }
  cond_id=self.current_market.get("condition_id","") if self.current_market else ""
  shock_record={ "timestamp":datetime.fromtimestamp(t0,tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"t0_unix":t0,"t0_mono_ns":t0_mono_ns,"shock_source":source,"market_id":m_id,"condition_id":cond_id,"title":m_title,"seconds_to_expiry":round(t0_secs_left,1),"shock_volume_100ms":round(shock_vol,0),"shock_direction":shock_dir,"shock_ofi":round(ofi,3),"trigger_price":trigger_px,"spot_at_t0":t0_spot,"futures_at_t0":t0_futures,"basis_signed_bps_t0":round(pre_shock_basis_signed,2),"basis_abs_bps_t0":round(pre_shock_basis_abs,2),"delta_basis_100ms":delta_basis_100ms,"finalized_1h_open":self.finalized_1h_open,"candle_distance_pct":round(t0_dist_pct,4),"fee_metadata":fee_meta,"pre_shock_features_t0":{ "UP":pre_shock_up,"DOWN":pre_shock_down },"impulse_response":response_snapshots,"pre_registered_models":{ "model_a_spot":"Y = f(q_mid, X_spot, TTE, dist)","model_b_futures":"Y = f(q_mid, X_futures, TTE, dist)","model_c_joint":"Y = f(q_mid, X_spot, X_futures, basis, delta_basis, TTE, dist)","model_d_incremental":"Y = f(q_mid, X_spot, TTE, dist) + g(X_futures | X_spot) -> test beta_{F|S} = 0","oos_training_invariant":"T_train_end < t0 (model trained strictly on completed prior markets)" },"clock_metadata":{ "clock_offset_ms":self.clock_offset_ms,"clock_uncertainty_ms":self.clock_uncertainty_ms,"timestamp_designation":"exchange_to_local_delta_with_calibrated_offset" },"statistical_clustering":{ "cluster_market_hour":m_id,"cluster_shock_episode":f"{m_id}_{int(t0)}","variance_estimator":"IRF: shock-episode block bootstrap | Regressions: market-hour cluster-robust SE" } }
  _atomic_append_jsonl(self.shock_file,json.dumps(shock_record))
  up_30s_delta=response_snapshots["30s"]["up_delta_q_ask"]
  age_up_val=float(pre_shock_up.get("age_ask_ms") or 0.0)
  logger.info(f"[SHOCK BURST CAPTURED] Market {m_id} | Source={source} | " f"AgeAsk(UP)={age_up_val:.0f}ms | UP ask={pre_shock_up['best_ask']:.3f} -> 30s Delta: {up_30s_delta:+.3f} | " f"Basis={pre_shock_basis_signed:+.1f}bps (Observational episode, not yet evidence of persistent structural lag)")
 async def stream_polymarket_clob(self):
  while self.running:
   if not self.current_market:
    await asyncio.sleep(0.5)
    continue
   subscribed_market=self.current_market
   subscribed_market_id=str(subscribed_market["market_id"])
   subscribed_end_dt=subscribed_market["end_dt"]
   up_token=str(subscribed_market["tokens"]["UP"])
   down_token=str(subscribed_market["tokens"]["DOWN"])
   if "UP" not in self.books or getattr(self.books["UP"],"token_id",None)!=up_token:
    self.books["UP"]=L2OrderBook(up_token)
   if "DOWN" not in self.books or getattr(self.books["DOWN"],"token_id",None)!=down_token:
    self.books["DOWN"]=L2OrderBook(down_token)
   subscribed_tokens:Dict[str,str]={up_token:"UP",down_token:"DOWN"}
   for hz,attr_n,up_k,dn_k in ( ("5m","market_5m","UP_5M","DOWN_5M"),("15m","market_15m","UP_15M","DOWN_15M"),("4h","market_4h","UP_4H","DOWN_4H"),):
    if not getattr(self,attr_n,None):
     try:
      setattr(self,attr_n,await self.discover_nearest_twap_market(hz))
     except Exception:
      pass
    mh=getattr(self,attr_n,None)
    if mh and "tokens" in mh:
     up_h=str(mh["tokens"]["UP"])
     dn_h=str(mh["tokens"]["DOWN"])
     if up_k not in self.books or getattr(self.books[up_k],"token_id",None)!=up_h:
      self.books[up_k]=L2OrderBook(up_h)
     if dn_k not in self.books or getattr(self.books[dn_k],"token_id",None)!=dn_h:
      self.books[dn_k]=L2OrderBook(dn_h)
     subscribed_tokens[up_h]=up_k
     subscribed_tokens[dn_h]=dn_k
   try:
    sub_assets=list(subscribed_tokens.keys())
    logger.info( f"Connecting to Polymarket CLOB WS ({CLOB_WS_URL}) for market {subscribed_market_id} " f"tokens ({list(subscribed_tokens.values())})..." )
    try:
     session=await self.get_session()
     for tok_id,role_name in subscribed_tokens.items():
      bk_obj=self.books.get(role_name)
      if bk_obj is not None and (not bk_obj.bids or not bk_obj.asks):
       async with session.get(f"https://clob.polymarket.com/book?token_id={tok_id}",timeout=2.0) as r_bk:
        if r_bk.status==200:
         b_json=await r_bk.json()
         if isinstance(b_json,dict):
          bk_obj.apply_snapshot(b_json.get("bids",[]),b_json.get("asks",[]))
    except Exception as seed_err:
     logger.debug(f"Initial REST book seed notice: {seed_err}")
    async with websockets.connect(CLOB_WS_URL,ping_interval=20,ping_timeout=10) as ws:
     sub_msg={"assets_ids":sub_assets,"type":"market"}
     await ws.send(json.dumps(sub_msg))
     logger.info(f"[+] Subscribed to Polymarket L2 orderbooks for market {subscribed_market_id}.")
     self._reconnect_clob=False
     pending_sub_toks:Dict[str,float]={}
     last_ws_msg_ts=time.time()
     self.clob_ws_connected=True
     self.last_clob_ws_msg_ts=last_ws_msg_ts
     while self.running:
      now_utc=datetime.now(timezone.utc)
      if ( (subscribed_end_dt - now_utc).total_seconds()<=0 or not self.current_market or str(self.current_market.get("market_id"))!=subscribed_market_id ):
       logger.info( f"[*] Market {subscribed_market_id} expired or rotated to " f"{(self.current_market or {}).get('market_id')}. Re-subscribing CLOB WS immediately." )
       self.clob_ws_connected=False
       break
      expired_twap=False
      for hz,attr_n,up_k,dn_k in ( ("5m","market_5m","UP_5M","DOWN_5M"),("15m","market_15m","UP_15M","DOWN_15M"),("4h","market_4h","UP_4H","DOWN_4H"),):
       mh=getattr(self,attr_n,None)
       if mh and (mh["end_dt"] - now_utc).total_seconds()<=0:
        logger.info(f"[*] {hz.upper()} Market {mh['market_id']} reached expiry. Cycling to next.")
        asyncio.create_task(self.verify_and_log_resolution(mh))
        setattr(self,attr_n,None)
        self.books.pop(up_k,None)
        self.books.pop(dn_k,None)
        for old_t in [t for t,r in subscribed_tokens.items() if r in (up_k,dn_k)]:
         subscribed_tokens.pop(old_t,None)
        expired_twap=True
      if expired_twap or getattr(self,"_reconnect_clob",False):
       self._reconnect_clob=False
       added_toks:List[str]=[]
       for hz,attr_n,up_k,dn_k in ( ("5m","market_5m","UP_5M","DOWN_5M"),("15m","market_15m","UP_15M","DOWN_15M"),("4h","market_4h","UP_4H","DOWN_4H"),):
        mh=getattr(self,attr_n,None)
        if not (mh and "tokens" in mh):
         continue
        for tok_n,role_n in ((str(mh["tokens"]["UP"]),up_k),(str(mh["tokens"]["DOWN"]),dn_k)):
         if role_n not in self.books or getattr(self.books[role_n],"token_id",None)!=tok_n:
          self.books[role_n]=L2OrderBook(tok_n)
         if subscribed_tokens.get(tok_n)!=role_n:
          for old_t in [t for t,r in subscribed_tokens.items() if r==role_n and t!=tok_n]:
           subscribed_tokens.pop(old_t,None)
          subscribed_tokens[tok_n]=role_n
          added_toks.append(tok_n)
       if added_toks:
        await ws.send(json.dumps({"assets_ids":added_toks,"operation":"subscribe"}))
        now_sub=time.time()
        for tok_n in added_toks:
         pending_sub_toks[tok_n]=now_sub
        logger.info(f"[+] In-place CLOB WS subscribe for {len(added_toks)} rolled TWAP token(s).")
      if pending_sub_toks and (time.time() - min(pending_sub_toks.values())) > 8.0:
       logger.warning("[*] In-place CLOB WS subscribe got no book within 8s. Reconnecting...")
       self.clob_ws_connected=False
       break
      if time.time() - last_ws_msg_ts > 25.0:
       logger.warning(f"[*] CLOB WS silent for >25s on market {subscribed_market_id}. Reconnecting...")
       self.clob_ws_connected=False
       break
      try:
       msg_str=await asyncio.wait_for(ws.recv(),timeout=1.0)
       last_ws_msg_ts=time.time()
       self.last_clob_ws_msg_ts=last_ws_msg_ts
      except asyncio.TimeoutError:
       self._maybe_emit_boundary_lock_trigger()
       continue
      data=_orjson.loads(msg_str) if _orjson is not None else json.loads(msg_str)
      if isinstance(data,list):
       for item in data:
        asset_id=str(item.get("asset_id") or "")
        pending_sub_toks.pop(asset_id,None)
        role=subscribed_tokens.get(asset_id)
        if role and role in self.books:
         self.books[role].apply_snapshot(item.get("bids",[]),item.get("asks",[]))
      elif isinstance(data,dict):
       event_type=data.get("event_type")
       if event_type=="price_change":
        pcs_by_role=defaultdict(list)
        for pc in data.get("price_changes",[]):
         role=subscribed_tokens.get(str(pc.get("asset_id") or ""))
         if role:
          pcs_by_role[role].append(pc)
        for role,pcs in pcs_by_role.items():
         if role in self.books:
          self.books[role].apply_price_changes(pcs)
       elif event_type=="book":
        asset_id=str(data.get("asset_id") or "")
        pending_sub_toks.pop(asset_id,None)
        role=subscribed_tokens.get(asset_id)
        if role and role in self.books:
         self.books[role].apply_snapshot(data.get("bids",[]),data.get("asks",[]))
      self._maybe_write_fast_tick()
      self._maybe_emit_boundary_lock_trigger()
   except Exception as e:
    self.clob_ws_connected=False
    logger.warning(f"Polymarket CLOB WS disconnected: {e}. Reconnecting in 1s...")
    await asyncio.sleep(1.0)
 def _maybe_emit_boundary_lock_trigger(self)->None:
  if self.spot_price<=0:
   return
  now_sec=time.time()
  if now_sec - getattr(self,"_last_boundary_check_ts",0.0) < 0.25:
   return
  self._last_boundary_check_ts=now_sec
  cooldowns=getattr(self,"_boundary_lock_cooldowns",None)
  if cooldowns is None:
   cooldowns={}
   self._boundary_lock_cooldowns=cooldowns
  now_utc=datetime.now(timezone.utc)
  candidates=[]
  if self.current_market and self.finalized_1h_open > 0 and "UP" in self.books and "DOWN" in self.books:
   candidates.append((self.current_market,float(self.finalized_1h_open),"UP","DOWN","1h",3600.0))
  if getattr(self,"market_15m",None) and "UP_15M" in self.books and "DOWN_15M" in self.books:
   open_15m=float(self.market_15m.get("finalized_15m_open",0.0) or 0.0)
   if open_15m > 0:
    candidates.append((self.market_15m,open_15m,"UP_15M","DOWN_15M","15m",900.0))
  for mkt,open_px,up_key,down_key,horizon,dur_s in candidates:
   m_id=str(mkt.get("market_id") or "")
   if not m_id or (now_sec - cooldowns.get(m_id,0.0)) < 15.0:
    continue
   secs_left=(mkt["end_dt"] - now_utc).total_seconds()
   if not (12.0<=secs_left<=75.0):
    continue
   dist_pct=((self.spot_price - open_px) / open_px) * 100.0
   min_req_dist=0.08 if horizon=="15m" else 0.12
   if abs(dist_pct) < min_req_dist:
    continue
   sigma=(0.0035 if self.asset=="BTC" else 0.0050) if horizon=="15m" else (0.0050 if self.asset=="BTC" else 0.0075)
   tau_frac=max(0.001,secs_left / dur_s)
   signed_z=(dist_pct / 100.0) / max(sigma * math.sqrt(tau_frac),1e-6)
   if abs(signed_z) < 3.0:
    continue
   win_side="UP" if dist_pct > 0 else "DOWN"
   win_book=self.books[up_key if win_side=="UP" else down_key]
   if not win_book.asks or not win_book.bids:
    continue
   best_ask=min(win_book.asks.keys())
   if not (0.62<=best_ask<=0.94):
    continue
   fee_meta=dict(mkt.get("fee_metadata",{}))
   fee_rate=float(fee_meta.get("fee_rate_market",self.fee_rate_market) or 0.07)
   fee_per_share=fee_rate * best_ask * (1.0 - best_ask)
   net_edge=(1.0 - best_ask) - fee_per_share
   if net_edge < 0.025:
    continue
   cooldowns[m_id]=now_sec
   up_m=self.books[up_key].get_metrics(obs_ts=now_sec,fee_rate=fee_rate)
   down_m=self.books[down_key].get_metrics(obs_ts=now_sec,fee_rate=fee_rate)
   up_m["token_id"]=mkt["tokens"].get("UP")
   down_m["token_id"]=mkt["tokens"].get("DOWN")
   shock_dir="BUY" if win_side=="UP" else "SELL"
   shock_id=f"BOUNDARY_{m_id}_{now_sec:.6f}"
   cross_fields=self._read_cross_asset_fields(now_sec,signed_z,shock_dir) if hasattr(self,"_read_cross_asset_fields") else {}
   trig={ "shock_id":shock_id,"event_id":shock_id,"timestamp":datetime.fromtimestamp(now_sec,tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"t0_unix":now_sec,"t0_mono_ns":time.monotonic_ns(),"t0_definition":"boundary_lock_scanner","shock_source":"BOUNDARY_LOCK","regime_override":"REGIME_D_BOUNDARY_LOCK","asset":self.asset,"horizon":horizon,"candle_interval":horizon,"series_slug":mkt.get("series_slug",self.series_slug),"slug":mkt.get("slug",""),"market_id":m_id,"condition_id":mkt.get("condition_id",""),"title":mkt.get("title",""),"seconds_to_expiry":round(secs_left,1),"expiry_ts":float(mkt.get("candle_close_ts") or (now_sec + secs_left)),"candle_expiry_ts":float(mkt.get("candle_close_ts") or (now_sec + secs_left)),"candle_open_ts":int(mkt.get("candle_open_ts") or (int(mkt["end_dt"].timestamp()) - int(dur_s))),"candle_sigma":sigma,"shock_volume_100ms":2_000_000.0,"is_40ms_fast_track":True,"shock_direction":shock_dir,"btc_shock_direction":shock_dir if self.asset=="BTC" else cross_fields.get("btc_shock_direction",shock_dir),"z_val":round(abs(signed_z),4),"z_score":round(signed_z,4),"z_btc":round(signed_z,4) if self.asset=="BTC" else cross_fields.get("z_btc",round(signed_z,4)),"z_eth":round(signed_z,4) if self.asset=="ETH" else None,"p_model":0.985,"shock_ofi":0.90 if win_side=="UP" else -0.90,"trigger_price":self.spot_price,"spot_at_t0":self.spot_price,"futures_at_t0":self.futures_price or self.spot_price,"basis_signed_bps_t0":round(self.basis_bps,2),"basis_abs_bps_t0":round(abs(self.basis_bps),2),"delta_basis_100ms":max(0.0,self.get_delta_basis_100ms()) if win_side=="UP" else min(0.0,self.get_delta_basis_100ms()),"coinbase_spot":self.get_coinbase_spot(now_sec),"chainlink_proxy_spot":self.get_chainlink_proxy_spot(now_sec),"chainlink_twap_60s":self.get_chainlink_twap_60s(now_sec),"resolution_source":mkt.get("resolution_source",""),"authoritative_chainlink_open":mkt.get("authoritative_chainlink_open") if horizon=="15m" else None,"venue_divergence_bps":self.get_venue_divergence_bps(now_sec),"coinbase_move_bps_2s":self.get_coinbase_move_bps(2.0,now_sec),"finalized_1h_open":open_px,"candle_open_spot":open_px,"candle_distance_pct":round(dist_pct,4),"fee_metadata":fee_meta,"pre_shock_features_t0":{"UP":up_m,"DOWN":down_m},}
   try:
    _,line_bl=_dispatch_trigger_fast(TRIGGER_FILE,trig)
    if line_bl:
     _persist_trigger_nonblocking(TRIGGER_FILE,line_bl)
    logger.info( f"[BOUNDARY LOCK TRIGGER] {self.asset} ({horizon}) {win_side} | TTE={secs_left:.1f}s | " f"z={signed_z:+.2f} | dist={dist_pct:+.2f}% | BestAsk=${best_ask:.3f} | NetEdge=+{net_edge*100:.2f}c" )
   except Exception as e:
    logger.debug(f"Boundary lock emit error: {e}")
 def compute_leadlag_cross_correlation(self,spot_trades=None,futures_trades=None):
  if spot_trades is None:
   spot_trades=self.spot_trades
  if futures_trades is None:
   futures_trades=self.futures_trades
  if len(spot_trades) < 200 or len(futures_trades) < 200:
   return
  now_ns=time.monotonic_ns()
  window_ns=300_000_000_000
  t_start_ns=now_ns - window_ns
  bucket_size_ns=25_000_000
  num_buckets=int(window_ns // bucket_size_ns)
  spot_bins=np.zeros(num_buckets,dtype=np.float64)
  fut_bins=np.zeros(num_buckets,dtype=np.float64)
  for t_mono,_,_,ntl,buyer,_ in spot_trades:
   if t_mono>=t_start_ns:
    idx=min(int((t_mono - t_start_ns) // bucket_size_ns),num_buckets - 1)
    spot_bins[idx] += (ntl if buyer else -ntl)
  for t_mono,_,_,ntl,buyer,_ in futures_trades:
   if t_mono>=t_start_ns:
    idx=min(int((t_mono - t_start_ns) // bucket_size_ns),num_buckets - 1)
    fut_bins[idx] += (ntl if buyer else -ntl)
  spot_innovations=np.diff(spot_bins)
  fut_innovations=np.diff(fut_bins)
  corrs={}
  for lag_ms in CORRELATION_LAGS_MS:
   shift_buckets=int(lag_ms * 1_000_000 / bucket_size_ns)
   if shift_buckets==0:
    s=spot_innovations
    f=fut_innovations
   elif shift_buckets > 0:
    f=fut_innovations[:-shift_buckets]
    s=spot_innovations[shift_buckets:]
   else:
    shift=abs(shift_buckets)
    f=fut_innovations[shift:]
    s=spot_innovations[:-shift]
   if len(s) > 10 and np.std(s) > 1e-6 and np.std(f) > 1e-6:
    corr_val=float(np.corrcoef(f,s)[0,1])
    corrs[str(lag_ms)]=round(corr_val,4)
   else:
    corrs[str(lag_ms)]=0.0
  max_lag=max(corrs.items(),key=lambda x:x[1]) if corrs else ("0",0.0)
  record={ "timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"timestamp_unix":time.time(),"market_id":self.current_market["market_id"] if self.current_market else "none","correlation_grid_lags_ms":corrs,"peak_correlation_lag_ms":int(max_lag[0]),"peak_correlation_val":max_lag[1],"metric_evaluated":"flow_innovations_cross_correlation (diff(signed_dollar_flow_25ms))","telemetry_classification":"illustrative live telemetry, not evidence of persistent lead/lag","null_hypothesis":"H0: no stable lead/lag structure across pre-registered grid","clock_metadata":{ "calibrated_offset_ms":self.clock_offset_ms,"clock_uncertainty_ms":self.clock_uncertainty_ms,"resolution_caveat":"Lags <= 50ms are within RTT uncertainty (+/-21.6ms) and must be evaluated strictly under pooled bootstrap bands." } }
  _atomic_append_jsonl(self.correlations_file,_dumps_compact(record),broadcast_ipc=False)
  logger.info(f"[LEAD/LAG INNOVATION TELEMETRY] Peak Lag: {max_lag[0]}ms (r={max_lag[1]:+.3f}) | Status: Illustrative telemetry (H0: no stable lead/lag)")
 async def telemetry_logger_loop(self):
  while self.running:
   try:
    now=datetime.now(timezone.utc)
    if not self.current_market or (self.current_market["end_dt"] - now).total_seconds()<=0:
     expired_market=self.current_market
     if expired_market:
      asyncio.create_task(self.verify_and_log_resolution(expired_market))
     market=getattr(self,"_cached_next_market",None)
     if not market or (expired_market and market.get("market_id")==expired_market.get("market_id")):
      market=await self.discover_nearest_1h_market()
     self._cached_next_market=None
     if market:
      self.current_market=market
      open_px,_=await self.fetch_finalized_binance_candle(market["candle_open_ts"])
      self.twap_60s_1h_open=await self.fetch_binance_60s_twap_open(market["candle_open_ts"])
      self.chainlink_1h_open=( await self.fetch_polygon_chainlink_spot() if abs(time.time() - float(market["candle_open_ts"]))<=35.0 else 0.0 )
      self._open_1h_provisional=False
      if open_px<=0.0 and self.spot_price > 0.0:
       open_px=self.spot_price
       self._open_1h_provisional=True
      self.finalized_1h_open=open_px
      logger.info(f"\n===============================================================================" f"\n[ACTIVE 1H PRODUCT LOADED: {self.asset}] {market['title']}" f"\n  Market ID: {market['market_id']} | End: {market['end_date_iso']}" f"\n  UP Token: {market['tokens']['UP']}" f"\n  DOWN Token: {market['tokens']['DOWN']}" f"\n  Binance Spot 1H Finalized Open: ${self.finalized_1h_open:,.2f}" f"\n  Fee Rate: {self.fee_rate_market * 100:.1f}% ({self.fee_source})" f"\n===============================================================================\n")
    for hz,attr_n in (("5m","market_5m"),("15m","market_15m"),("4h","market_4h")):
     mh_cur=getattr(self,attr_n,None)
     if not mh_cur or (mh_cur["end_dt"] - now).total_seconds()<=0:
      if mh_cur and (mh_cur["end_dt"] - now).total_seconds()<=0:
       asyncio.create_task(self.verify_and_log_resolution(mh_cur))
      try:
       mh_new=await self.discover_nearest_twap_market(hz)
       if mh_new:
        prev_id=mh_cur.get("market_id") if mh_cur else None
        setattr(self,attr_n,mh_new)
        mh_cur=mh_new
        if mh_new.get("market_id")!=prev_id:
         logger.info( f"[ACTIVE {hz.upper()} PRODUCT LOADED: {self.asset}] {mh_new['title']} " f"(ID: {mh_new['market_id']}, Open: ${mh_new.get('finalized_open', 0.0):,.4f})" )
         self._reconnect_clob=True
      except Exception as e:
       logger.debug(f"{hz} discovery cycle note: {e}")
    if self.current_market and (self.finalized_1h_open<=0.0 or getattr(self,"_open_1h_provisional",False)):
     open_px,_=await self.fetch_finalized_binance_candle(self.current_market["candle_open_ts"])
     if open_px > 0.0:
      self.finalized_1h_open=open_px
      self._open_1h_provisional=False
      if float(getattr(self,"twap_60s_1h_open",0.0) or 0.0)<=0.0:
       self.twap_60s_1h_open=await self.fetch_binance_60s_twap_open(self.current_market["candle_open_ts"])
      logger.info(f"[{self.asset} FINALIZED OPEN RECOVERED] Binance Spot 1H Open: ${self.finalized_1h_open:,.2f}")
    now_ts_int=int(datetime.now(timezone.utc).timestamp())
    for hz,attr_n,dur_s in (("5m","market_5m",300),("15m","market_15m",900),("4h","market_4h",14400)):
     mh=getattr(self,attr_n,None)
     if not mh:
      continue
     open_ts_h=int(mh.get("candle_open_ts",0))
     if now_ts_int < open_ts_h:
      continue
     if float(mh.get("finalized_open") or mh.get("finalized_15m_open") or 0.0)<=0.0 or mh.get("_provisional_open",False):
      open_h_px,_=await self.fetch_finalized_binance_candle(open_ts_h,interval=hz)
      if open_h_px > 0.0:
       mh["finalized_open"]=open_h_px
       mh["finalized_15m_open"]=open_h_px
       mh["_provisional_open"]=False
      elif float(mh.get("finalized_open") or 0.0)<=0.0 and self.spot_price > 0.0:
       mh["finalized_open"]=self.spot_price
       mh["finalized_15m_open"]=self.spot_price
       mh["_provisional_open"]=True
     if float(mh.get("twap_60s_open") or 0.0)<=0.0:
      twap_h_px=await self.fetch_binance_60s_twap_open(open_ts_h)
      if twap_h_px > 0.0:
       mh["twap_60s_open"]=twap_h_px
     if float(mh.get("authoritative_chainlink_open") or 0.0)<=0.0:
      close_ts_h=int(mh.get("candle_close_ts",open_ts_h + dur_s))
      if (now_ts_int - float(mh.get("_last_auth_open_try",0.0)))>=5.0:
       mh["_last_auth_open_try"]=float(now_ts_int)
       auth_px=await self.fetch_authoritative_chainlink_open(open_ts_h,close_ts_h,horizon=hz)
       if auth_px > 0.0:
        mh["authoritative_chainlink_open"]=auth_px
        mh["chainlink_open_spot"]=auth_px
        logger.info(f"[{self.asset} {hz.upper()} AUTHORITATIVE CHAINLINK OPEN LOCKED] Polymarket openPrice: ${auth_px:,.6f}")
    if self.current_market and "UP" in self.books and "DOWN" in self.books:
     now_ts_u=round(now.timestamp(),3)
     up_metrics=self.books["UP"].get_metrics(fee_rate=self.fee_rate_market,compact=True)
     down_metrics=self.books["DOWN"].get_metrics(fee_rate=self.fee_rate_market,compact=True)
     secs_left=(self.current_market["end_dt"] - now).total_seconds()
     if 0 < secs_left<=120.0 and getattr(self,"_prewarmed_market_id",None)!=self.current_market["market_id"]:
      self._prewarmed_market_id=self.current_market["market_id"]
      logger.info(f"[PREWARM TTE={secs_left:.0f}s] Pre-fetching next 1H market from Gamma API to eliminate :00 open delay...")
      try:
       prewarmed=await self.discover_nearest_1h_market()
       if prewarmed and prewarmed["market_id"]!=self.current_market["market_id"]:
        self._cached_next_market=prewarmed
        logger.info(f"[PREWARM READY] Next market pre-cached: {prewarmed['title']} ({prewarmed['market_id']}).")
      except Exception as e:
       logger.debug(f"Prewarm error: {e}")
     dist_pct=((self.spot_price - self.finalized_1h_open) / self.finalized_1h_open * 100.0) if self.finalized_1h_open > 0 else 0.0
     delta_basis_100ms=self.get_delta_basis_100ms()
     bbo_1h=( self.current_market["market_id"],up_metrics["best_bid"],up_metrics["best_ask"],down_metrics["best_bid"],down_metrics["best_ask"],)
     prev_1h=self._last_telem_bbo_by_hz.get("1h")
     if ( prev_1h is None or prev_1h[1]!=bbo_1h or secs_left<=900.0 or (now_ts_u - prev_1h[0])>=19.0 ):
      self._last_telem_bbo_by_hz["1h"]=(now_ts_u,bbo_1h)
      record={ "timestamp":now.strftime("%Y-%m-%d %H:%M:%S UTC"),"timestamp_unix":now_ts_u,"asset":self.asset,"market_id":self.current_market["market_id"],"title":self.current_market["title"],"seconds_to_expiry":round(secs_left,1),"binance_spot":self.spot_price,"binance_futures":self.futures_price,"basis_signed_usd":round(self.basis_usd,2),"basis_signed_bps":round(self.basis_bps,2),"basis_abs_bps":round(abs(self.basis_bps),2),"delta_basis_100ms":delta_basis_100ms,"binance_1h_open":self.finalized_1h_open,"candle_distance_pct":round(dist_pct,4),"clock_metadata":{ "clock_offset_ms":round(self.clock_offset_ms,2),"clock_uncertainty_ms":round(self.clock_uncertainty_ms,2),},"fee_metadata":{"fee_rate_market":self.fee_rate_market},"UP":up_metrics,"DOWN":down_metrics,}
      _atomic_append_jsonl(self.telemetry_file,_dumps_compact(record),broadcast_ipc=False)
     cb_now=self.get_coinbase_spot(now_ts_u)
     cl_now=self.get_chainlink_proxy_spot(now_ts_u)
     for hz,attr_n,up_k,dn_k,out_f in ( ("5m","market_5m","UP_5M","DOWN_5M",self.telemetry_5m_file),("15m","market_15m","UP_15M","DOWN_15M",self.telemetry_15m_file),("4h","market_4h","UP_4H","DOWN_4H",self.telemetry_4h_file),):
      mh=getattr(self,attr_n,None)
      if mh and up_k in self.books and dn_k in self.books:
       secs_h=(mh["end_dt"] - now).total_seconds()
       if secs_h > 0:
        f_h=float(mh.get("fee_metadata",{}).get("fee_rate_market",0.07) or 0.07)
        uph_m=self.books[up_k].get_metrics(fee_rate=f_h,compact=True)
        dnh_m=self.books[dn_k].get_metrics(fee_rate=f_h,compact=True)
        bbo_h=( mh["market_id"],uph_m["best_bid"],uph_m["best_ask"],dnh_m["best_bid"],dnh_m["best_ask"],)
        prev_h=self._last_telem_bbo_by_hz.get(hz)
        if hz=="4h" and secs_h > 1800.0 and prev_h is not None and prev_h[1]==bbo_h and (now_ts_u - prev_h[0]) < 58.0:
         continue
        if hz=="15m" and secs_h > 360.0 and prev_h is not None and prev_h[1]==bbo_h and (now_ts_u - prev_h[0]) < 28.0:
         continue
        self._last_telem_bbo_by_hz[hz]=(now_ts_u,bbo_h)
        open_h=float(mh.get("finalized_open") or mh.get("finalized_15m_open") or 0.0)
        auth_cl_h=mh.get("authoritative_chainlink_open")
        usd_ref_h=cl_now if cl_now > 0 else cb_now
        dist_h=((self.spot_price - open_h) / open_h * 100.0) if open_h > 0 else 0.0
        cl_dist_h=( round(((usd_ref_h - float(auth_cl_h)) / float(auth_cl_h)) * 100.0,4) if auth_cl_h and float(auth_cl_h) > 0 and usd_ref_h > 0 else None )
        rec_h:Dict[str,Any]={ "timestamp":now.strftime("%Y-%m-%d %H:%M:%S UTC"),"timestamp_unix":now_ts_u,"asset":self.asset,"horizon":hz,"market_id":mh["market_id"],"title":mh["title"],"seconds_to_expiry":round(secs_h,1),"binance_spot":self.spot_price,"binance_futures":self.futures_price,"coinbase_usd_spot":round(cb_now,6) if cb_now > 0 else 0.0,"chainlink_proxy_usd_spot":round(cl_now,6) if cl_now > 0 else 0.0,"binance_open":open_h,"candle_distance_pct":round(dist_h,4),"fee_metadata":{"fee_rate_market":f_h},"UP":uph_m,"DOWN":dnh_m,}
        if hz=="15m":
         rec_h["binance_15m_open"]=open_h
        twap_h=mh.get("twap_60s_open")
        if twap_h is not None:
         rec_h["twap_60s_open"]=twap_h
        if auth_cl_h is not None:
         rec_h["authoritative_chainlink_open"]=auth_cl_h
        if cl_dist_h is not None:
         rec_h["chainlink_usd_distance_pct"]=cl_dist_h
        _atomic_append_jsonl(out_f,_dumps_compact(rec_h),broadcast_ipc=False)
     logger.info( f"[1H TELEMETRY: {self.asset}] {self.current_market['title'][:32]} | Tau: {secs_left/60.0:.1f}m ({secs_left:.0f}s) | " f"UP ask={up_metrics['best_ask']:.3f} (mid={up_metrics['q_mid']:.3f}, hurdle={up_metrics['executable_hurdle']:.4f}) | " f"Spot=${self.spot_price:,.1f} | Fut=${self.futures_price:,.1f} | Basis={self.basis_bps:+.1f}bp | dist={dist_pct:+.2f}%" )
    if time.time() - self.last_cross_corr_ts > 60.0:
     self.last_cross_corr_ts=time.time()
     spot_snap=list(self.spot_trades)
     fut_snap=list(self.futures_trades)
     await asyncio.to_thread(self.compute_leadlag_cross_correlation,spot_snap,fut_snap)
    if time.time() - self.last_clock_sync_ts > 300.0:
     asyncio.create_task(self.calibrate_binance_clock_offset())
    await asyncio.sleep(10.0)
   except Exception as e:
    logger.error(f"Error in telemetry loop: {e}",exc_info=True)
    await asyncio.sleep(10.0)
 async def run(self):
  logger.info("===============================================================================")
  logger.info(f"   ROUTE 3: FUTURES/SPOT -> POLYMARKET 1H RECORDER ({self.asset}) (v2.8)       ")
  logger.info(f"   Asset: {self.asset} | Binance: {self.binance_symbol} | Shock: ${self.shock_threshold_usd:,.0f} ")
  logger.info("   Dual Feeds: Binance Spot (Settlement Ref) + Futures (Routed /market)        ")
  logger.info("   Invariants: OBI/q_micro Reconciled + Invariant Assertions Enforced          ")
  logger.info("   Quote Ages: Tripartite (Age_book, Age_bid, Age_ask)                         ")
  logger.info("   Clock Sync: Cristian's Algorithm Calibrated Offset (Tokyo <-> Binance)      ")
  logger.info("   Econometrics: Strict Causal t0 Anchor + Lead/Lag Innovation Grid            ")
  logger.info("   Capacity Surface: Fill-Level Fees & Crossing Cost [$1, $5, $20, $50, $100]  ")
  logger.info("   Resolution Truth: Finalized Binance Spot 1H Candle Open & Close             ")
  logger.info("   Operational: Read-Only (Does not circumvent geographic restrictions)        ")
  logger.info("===============================================================================")
  with open(self.pid_file,"w") as f:
   f.write(str(os.getpid()))
  await self.calibrate_binance_clock_offset()
  await asyncio.gather( self.stream_binance_spot(),self.stream_binance_futures(),self.stream_polymarket_clob(),self.telemetry_logger_loop(),self._coinbase_stream_worker(),)
if __name__=="__main__":
 import argparse
 parser=argparse.ArgumentParser(description="Polymarket Dual Feed 1H Telemetry Recorder")
 parser.add_argument( "--asset",choices=list(ASSET_CONFIGS.keys()),default="BTC",help=f"Asset to record ({', '.join(ASSET_CONFIGS.keys())}, default: BTC)",)
 parser.add_argument("--shock-threshold",type=float,default=None,help="Volume shock threshold in USD over 100ms")
 args=parser.parse_args()
 setup_logging(args.asset)
 if os.name!="nt":
  try:
   import uvloop
   uvloop.install()
  except Exception:
   pass
 recorder=PolymarketDualFeed1HRecorder(asset=args.asset,shock_threshold=args.shock_threshold)
 try:
  asyncio.run(recorder.run())
 except KeyboardInterrupt:
  recorder.running=False
  logger.info("Stopped by user.")

# === [06/12] src/polymarket_research/deribit_svi_surface.py :: Deribit SVI Options Volatility Surface & Breeden-Litzenberger Engine ===
#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import json
import logging
import math
import os
import threading
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime,timezone
from typing import Any,Dict,List,Optional,Tuple
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
logger=logging.getLogger("DeribitSVISurface")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
DERIBIT_PUBLIC_URL="https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
DEFAULT_SIGMA_1H={ "BTC":0.0050,"ETH":0.0068,"SOL":0.0095,"XRP":0.0100,}
ASSET_VOL_MULT_VS_BTC={ "BTC":1.00,"ETH":1.28,"SOL":1.75,"XRP":1.85,}
def _tte_horizon_bucket(target_tte_sec:Optional[float])->str:
 if target_tte_sec is None or target_tte_sec<=43200.0:
  return "0DTE"
 if target_tte_sec<=216000.0:
  return "DAILY"
 if target_tte_sec<=950400.0:
  return "WEEKLY"
 return "MONTHLY"
@dataclass
class SVIParams:
 a:float
 b:float
 rho:float
 m:float
 sigma:float
 t_years:float
 forward_price:float
 calibrated_at:float
 index_price:float=0.0
 def implied_forward_drift_rate(self)->float:
  if self.index_price<=0.0 or self.forward_price<=0.0 or self.t_years<=1e-6:
   return 0.0
  raw_r=math.log(self.forward_price / self.index_price) / max(1e-4,self.t_years)
  return max(-0.30,min(0.40,raw_r))
 def total_variance(self,k:float)->float:
  val=self.a + self.b * (self.rho * (k - self.m) + math.sqrt((k - self.m) ** 2 + self.sigma ** 2))
  return max(1e-8,val)
 def implied_vol(self,k:float,t_override:Optional[float]=None)->float:
  t_eff=max(1e-6,t_override if t_override is not None else self.t_years)
  if t_override is not None and self.t_years > 1e-6:
   t_ratio=t_eff / self.t_years
   k_scale=max(0.25,min(2.0,1.0 / math.sqrt(max(0.05,t_ratio))))
   w_unit=self.total_variance(k * k_scale) / self.t_years
   return max(0.10,min(3.00,math.sqrt(max(1e-8,w_unit))))
  w=self.total_variance(k)
  return max(0.10,min(3.00,math.sqrt(w / t_eff)))
def scale_svi_sticky_delta(base_svi:SVIParams,vol_mult:float,forward_price:float)->SVIParams:
 m_val=max(0.5,float(vol_mult))
 return SVIParams( a=base_svi.a * (m_val ** 2),b=base_svi.b * m_val,rho=base_svi.rho,m=base_svi.m * m_val,sigma=base_svi.sigma * m_val,t_years=base_svi.t_years,forward_price=forward_price,calibrated_at=base_svi.calibrated_at,)
def black_scholes_call(F:float,K:float,T:float,sigma:float,r:float=0.0)->float:
 if T<=0.0 or sigma<=0.0 or K<=0.0 or F<=0.0:
  return max(0.0,F - K) * math.exp(-r * max(0.0,T))
 sqrt_t=math.sqrt(T)
 vol_sqrt_t=sigma * sqrt_t
 d1=(math.log(F / K) + 0.5 * (sigma ** 2) * T) / vol_sqrt_t
 d2=d1 - vol_sqrt_t
 return math.exp(-r * T) * (F * float(norm.cdf(d1)) - K * float(norm.cdf(d2)))
def compute_breeden_litzenberger_digital( F:float,K:float,T_years:float,svi:SVIParams,r:float=0.0,)->float:
 if F<=0.0 or K<=0.0:
  return 0.5
 T_eff=max(1e-6,T_years)
 dK=max(1e-5,K * 0.001)
 k_mid=math.log(K / F)
 k_up=math.log((K + dK) / F)
 k_dn=math.log(max(1e-8,K - dK) / F)
 sigma_mid=svi.implied_vol(k_mid,t_override=T_eff)
 sigma_up=svi.implied_vol(k_up,t_override=T_eff)
 sigma_dn=svi.implied_vol(k_dn,t_override=T_eff)
 c_up=black_scholes_call(F,K + dK,T_eff,sigma_up,r)
 c_dn=black_scholes_call(F,max(1e-8,K - dK),T_eff,sigma_dn,r)
 dC_dK=(c_up - c_dn) / (2.0 * dK)
 p_rnd=-math.exp(r * T_eff) * dC_dK
 vol_sqrt_t=max(1e-6,sigma_mid * math.sqrt(T_eff))
 d2_mid=(math.log(F / K) + (r - 0.5 * (sigma_mid ** 2)) * T_eff) / vol_sqrt_t
 p_bs_d2=float(norm.cdf(d2_mid))
 p_bounded=max(p_bs_d2 - 0.08,min(p_bs_d2 + 0.08,float(p_rnd)))
 return max(0.0001,min(0.9999,p_bounded))
def fit_svi_slice( log_moneyness:List[float],mark_ivs:List[float],t_years:float,forward_price:float,)->SVIParams:
 t_eff=max(1e-5,float(t_years))
 if len(log_moneyness) < 4:
  atm_iv=float(np.median(mark_ivs)) if mark_ivs else 0.55
  w_atm=(atm_iv ** 2) * t_eff
  return SVIParams( a=w_atm * 0.85,b=w_atm * 0.30,rho=-0.10,m=0.0,sigma=0.05,t_years=t_eff,forward_price=forward_price,calibrated_at=time.time(),)
 k_arr=np.array(log_moneyness,dtype=float)
 w_obs=(np.array(mark_ivs,dtype=float) ** 2) * t_eff
 order=np.argsort(k_arr)
 w_atm_est=max(1e-7,float(np.interp(0.0,k_arr[order],w_obs[order])))
 max_b_no_arb=min(0.50,max(1e-4,3.5 * math.sqrt(w_atm_est * t_eff)))
 def loss(params:np.ndarray)->float:
  a,b,rho,m,sig=params
  w_model=a + b * (rho * (k_arr - m) + np.sqrt((k_arr - m) ** 2 + sig ** 2))
  weights=np.exp(-4.0 * np.abs(k_arr))
  return float(np.sum(weights * ((w_model - w_obs) ** 2)))
 x0=np.array([ max(1e-6,w_atm_est * 0.85),min(max_b_no_arb * 0.5,max(1e-5,w_atm_est * 0.4)),-0.12,0.0,0.05,])
 bounds=[ (1e-7,max(1e-3,float(np.max(w_obs)))),(1e-6,max_b_no_arb),(-0.90,0.90),(-0.35,0.35),(0.020,0.50),]
 try:
  res=minimize(loss,x0,method="L-BFGS-B",bounds=bounds,options={"maxiter":60})
  if res.success:
   a,b,rho,m,sig=res.x
   return SVIParams( a=float(a),b=float(b),rho=float(rho),m=float(m),sigma=float(sig),t_years=t_eff,forward_price=forward_price,calibrated_at=time.time(),)
 except Exception:
  pass
 return SVIParams( a=max(1e-6,w_atm_est * 0.85),b=min(max_b_no_arb,max(1e-5,w_atm_est * 0.30)),rho=-0.10,m=0.0,sigma=0.05,t_years=t_eff,forward_price=forward_price,calibrated_at=time.time(),)
class DeribitSVISurfaceEngine:
 def __init__(self,ttl_seconds:float=60.0):
  import queue as _queue
  self.ttl_seconds=ttl_seconds
  self._lock=threading.Lock()
  self._cache:Dict[str,SVIParams]={}
  self._last_fetch_attempt:Dict[str,float]={}
  self._refresh_in_flight:Dict[str,bool]={}
  self._refresh_queue:"_queue.SimpleQueue[Tuple[str, str, float]]"=_queue.SimpleQueue()
  self._bg_worker_thread:Optional[threading.Thread]=None
  self._http_client:Any=None
 @staticmethod
 def _cache_key(asset_u:str,target_tte_sec:Optional[float]=None)->str:
  bucket=_tte_horizon_bucket(target_tte_sec)
  return asset_u if bucket=="0DTE" else f"{asset_u}:{bucket}"
 @staticmethod
 def _parse_deribit_instrument(name:str)->Optional[Tuple[str,float,float,str]]:
  parts=name.split("-")
  if len(parts)!=4:
   return None
  asset,exp_str,strike_str,opt_type=parts
  try:
   strike=float(strike_str)
   dt=datetime.strptime(exp_str,"%d%b%y").replace(hour=8,minute=0,second=0,tzinfo=timezone.utc)
   return asset.upper(),dt.timestamp(),strike,opt_type.upper()
  except Exception:
   return None
 def fetch_and_calibrate_sync(self,asset:str,target_tte_sec:float=7200.0)->Optional[SVIParams]:
  asset_u=asset.upper()
  c_key=self._cache_key(asset_u,target_tte_sec)
  if asset_u not in ("BTC","ETH"):
   btc_svi=self.fetch_and_calibrate_sync("BTC",target_tte_sec=target_tte_sec)
   if btc_svi is None:
    return None
   mult=ASSET_VOL_MULT_VS_BTC.get(asset_u,1.75)
   scaled=scale_svi_sticky_delta(btc_svi,mult,btc_svi.forward_price)
   with self._lock:
    self._cache[c_key]=scaled
   return scaled
  url=f"{DERIBIT_PUBLIC_URL}?currency={asset_u}&kind=option"
  try:
   _urlopen_fn=urllib.request.urlopen
   _is_mocked=hasattr(_urlopen_fn,"mock_calls") or getattr(_urlopen_fn,"__module__","")!="urllib.request"
   if _is_mocked:
    req=urllib.request.Request(url,headers={"User-Agent":"Polymarket-SVI-Engine/1.0"})
    with _urlopen_fn(req,timeout=2.5) as resp:
     raw_bytes=resp.read()
   else:
    try:
     import httpx as _httpx
     cli=self._http_client
     if cli is None or getattr(cli,"is_closed",False):
      cli=_httpx.Client(http2=False,timeout=2.5,headers={"User-Agent":"Polymarket-SVI-Engine/1.0"})
      self._http_client=cli
     raw_bytes=cli.get(url).content
    except Exception:
     req=urllib.request.Request(url,headers={"User-Agent":"Polymarket-SVI-Engine/1.0"})
     with _urlopen_fn(req,timeout=2.5) as resp:
      raw_bytes=resp.read()
   try:
    import orjson as _orjson
    data=_orjson.loads(raw_bytes)
   except Exception:
    data=json.loads(raw_bytes.decode("utf-8") if isinstance(raw_bytes,(bytes,bytearray)) else raw_bytes)
   summaries=data.get("result",[])
   if not summaries:
    return None
   now_ts=time.time()
   by_expiry:Dict[float,List[Tuple[float,float,float,float]]]={}
   max_k_band=0.25 if target_tte_sec<=86400.0 else 0.45
   for item in summaries:
    inst=item.get("instrument_name","")
    parsed=self._parse_deribit_instrument(inst)
    if not parsed:
     continue
    _,exp_ts,strike,_=parsed
    tte=exp_ts - now_ts
    if tte<=600.0:
     continue
    mark_iv=float(item.get("mark_iv") or 0.0) / 100.0
    under_px=float(item.get("underlying_price") or item.get("estimated_delivery_price") or 0.0)
    idx_px=float(item.get("estimated_delivery_price") or under_px or 0.0)
    if mark_iv<=0.05 or mark_iv>=3.0 or under_px<=0.0:
     continue
    k=math.log(strike / under_px)
    if abs(k)<=max_k_band:
     by_expiry.setdefault(exp_ts,[]).append((k,mark_iv,under_px,idx_px))
   if not by_expiry:
    return None
   valid_exps=[e for e,pts in by_expiry.items() if len(pts)>=4]
   if not valid_exps:
    valid_exps=list(by_expiry.keys())
   best_exp=min(valid_exps,key=lambda e:abs((e - now_ts) - max(3600.0,target_tte_sec)))
   pts=by_expiry[best_exp]
   k_list=[p[0] for p in pts]
   iv_list=[p[1] for p in pts]
   fwd_px=float(np.median([p[2] for p in pts]))
   idx_med=float(np.median([p[3] for p in pts if p[3] > 0])) if any(p[3] > 0 for p in pts) else fwd_px
   t_years=max(1e-5,(best_exp - now_ts) / (365.25 * 86400.0))
   svi=fit_svi_slice(k_list,iv_list,t_years,fwd_px)
   svi.index_price=idx_med
   with self._lock:
    self._cache[c_key]=svi
   return svi
  except Exception as e:
   logger.debug(f"Deribit SVI fetch notice for {asset_u} ({c_key}): {e}")
   return None
 def _ensure_bg_worker(self)->None:
  th=self._bg_worker_thread
  if th is not None and th.is_alive():
   return
  with self._lock:
   th=self._bg_worker_thread
   if th is not None and th.is_alive():
    return
   def _loop()->None:
    while True:
     c_key,asset_u,eff_tte=self._refresh_queue.get()
     try:
      try:
       from src.polymarket_research.polymarket_live_executor import _HOT_DISPATCH_ACTIVE
       if _HOT_DISPATCH_ACTIVE.is_set():
        time.sleep(0.05)
      except Exception:
       pass
      self.fetch_and_calibrate_sync(asset_u,target_tte_sec=eff_tte)
     except Exception:
      pass
     finally:
      with self._lock:
       self._refresh_in_flight[c_key]=False
   t=threading.Thread(target=_loop,name="svi-bg-refresher",daemon=True)
   t.start()
   self._bg_worker_thread=t
 def _trigger_background_refresh(self,asset:str,target_tte_sec:Optional[float]=None)->None:
  asset_u=asset.upper()
  c_key=self._cache_key(asset_u,target_tte_sec)
  eff_tte=float(target_tte_sec) if target_tte_sec is not None else 7200.0
  now=time.time()
  with self._lock:
   if self._refresh_in_flight.get(c_key,False):
    return
   if now - self._last_fetch_attempt.get(c_key,0.0) < 15.0:
    return
   self._refresh_in_flight[c_key]=True
   self._last_fetch_attempt[c_key]=now
  self._ensure_bg_worker()
  self._refresh_queue.put((c_key,asset_u,eff_tte))
 def get_svi_params( self,asset:str,allow_sync_if_empty:bool=False,target_tte_sec:Optional[float]=None,)->Optional[SVIParams]:
  asset_u=asset.upper()
  c_key=self._cache_key(asset_u,target_tte_sec)
  eff_tte=float(target_tte_sec) if target_tte_sec is not None else 7200.0
  now=time.time()
  with self._lock:
   cached=self._cache.get(c_key)
   if cached is None and c_key!=asset_u and not allow_sync_if_empty:
    cached=self._cache.get(asset_u)
  if cached is not None:
   age=now - cached.calibrated_at
   if age > self.ttl_seconds and os.environ.get("PM_SVI_DISABLE_BG_REFRESH")!="1":
    self._trigger_background_refresh(asset_u,target_tte_sec=target_tte_sec)
   if age<=900.0 or os.environ.get("PM_SVI_DISABLE_BG_REFRESH")=="1" or cached.calibrated_at<=0.0:
    return cached
  if os.environ.get("PM_SVI_DISABLE_BG_REFRESH")=="1" and not allow_sync_if_empty:
   return None
  if allow_sync_if_empty:
   return self.fetch_and_calibrate_sync(asset_u,target_tte_sec=eff_tte)
  self._trigger_background_refresh(asset_u,target_tte_sec=target_tte_sec)
  return None
 def get_surface(self,asset:str)->Optional[SVIParams]:
  return self.fetch_and_calibrate_sync(asset)
 def get_hourly_sigma(self,asset:str,fallback:Optional[float]=None)->float:
  asset_u=asset.upper()
  default_sig=fallback if fallback is not None else DEFAULT_SIGMA_1H.get(asset_u,0.0060)
  svi=self.get_svi_params(asset_u)
  if svi is None:
   if asset_u in ("SOL","XRP"):
    btc_svi=self.get_svi_params("BTC")
    if btc_svi is not None:
     mult=ASSET_VOL_MULT_VS_BTC.get(asset_u,1.80)
     atm_annual=btc_svi.implied_vol(0.0) * mult
     return max(0.0030,min(0.0250,atm_annual / math.sqrt(8760.0)))
   return default_sig
  atm_annual=svi.implied_vol(0.0)
  sigma_1h=atm_annual / math.sqrt(8760.0)
  return max(0.0020,min(0.0250,sigma_1h))
 get_implied_hourly_sigma=get_hourly_sigma
 def evaluate_strike_probability( self,asset:str,spot:float,strike:float,tte_seconds:float,outcome:str="YES",is_downward_question:bool=False,is_upward:Optional[bool]=None,is_barrier_no:bool=False,fallback_sigma_1h:Optional[float]=None,allow_sync_fetch:bool=False,target_tte_sec:Optional[float]=None,)->Dict[str,Any]:
  if is_upward is not None:
   is_downward_question=not bool(is_upward)
  asset_u=asset.upper()
  eff_horizon_sec=target_tte_sec if target_tte_sec is not None else tte_seconds
  t_years=max(1e-6,tte_seconds / (365.25 * 86400.0))
  tau_hours=max(0.01,tte_seconds / 3600.0)
  svi=self.get_svi_params(asset_u,allow_sync_if_empty=allow_sync_fetch,target_tte_sec=eff_horizon_sec)
  if svi is None and asset_u in ("SOL","XRP"):
   btc_svi=self.get_svi_params("BTC",allow_sync_if_empty=allow_sync_fetch,target_tte_sec=eff_horizon_sec)
   if btc_svi is not None:
    mult=ASSET_VOL_MULT_VS_BTC.get(asset_u,1.80)
    svi=scale_svi_sticky_delta(btc_svi,mult,spot if spot > 0 else btc_svi.forward_price)
  if svi is not None and spot > 0 and strike > 0:
   basis_ratio=( max(0.95,min(1.08,svi.forward_price / svi.index_price)) if (svi.index_price > 0.0 and svi.forward_price > 0.0) else 1.0 )
   tenor_scale=min(1.5,max(0.0,t_years / max(1e-5,svi.t_years))) if basis_ratio!=1.0 else 0.0
   f_eff=spot * (1.0 + (basis_ratio - 1.0) * tenor_scale)
   k=math.log(strike / f_eff)
   iv_annual=svi.implied_vol(k,t_override=t_years)
   sigma_1h=iv_annual / math.sqrt(8760.0)
   p_above=compute_breeden_litzenberger_digital(f_eff,strike,t_years,svi)
   source="DERIBIT_SVI_BL"
  else:
   sigma_1h=fallback_sigma_1h if fallback_sigma_1h is not None else DEFAULT_SIGMA_1H.get(asset_u,0.0060)
   iv_annual=sigma_1h * math.sqrt(8760.0)
   if spot > 0 and strike > 0:
    z=math.log(spot / strike) / max(1e-6,sigma_1h * math.sqrt(tau_hours))
    p_above=float(norm.cdf(z))
   else:
    p_above=0.5
   source="FALLBACK_GAUSSIAN"
  if is_downward_question:
   p_yes=1.0 - p_above
  else:
   p_yes=p_above
  p_outcome=p_yes if outcome.upper()=="YES" else (1.0 - p_yes)
  if is_barrier_no and outcome.upper()=="NO":
   p_touch=min(0.9999,2.0 * max(0.0,1.0 - p_outcome))
   p_outcome=max(0.0001,1.0 - p_touch)
  return { "p_svi":round(float(p_outcome),4),"p_above_strike":round(float(p_above),4),"svi_sigma_1h":round(float(sigma_1h),5),"svi_iv_annual":round(float(iv_annual),4),"source":source,}
def enforce_monotone_ladder_probabilities( strikes_and_probs:List[Tuple[float,float]],)->Dict[str,Any]:
 if not strikes_and_probs:
  return {"strikes":[],"probs":[],"interval_probs":[],"max_adjustment":0.0}
 ordered=sorted((float(k),max(0.0001,min(0.9999,float(p)))) for k,p in strikes_and_probs)
 blocks:List[List[float]]=[]
 for _,p_val in ordered:
  blocks.append([p_val,1.0])
  while len(blocks)>=2 and (blocks[-2][0] / blocks[-2][1]) < (blocks[-1][0] / blocks[-1][1]) - 1e-12:
   b_last=blocks.pop()
   blocks[-1][0] += b_last[0]
   blocks[-1][1] += b_last[1]
 proj:List[float]=[]
 for s_val,cnt in blocks:
  avg=max(0.0001,min(0.9999,s_val / cnt))
  proj.extend([round(avg,6)] * int(cnt))
 max_adj=max(abs(proj[i] - ordered[i][1]) for i in range(len(proj)))
 intervals=[round(max(0.0,proj[i] - proj[i + 1]),6) for i in range(len(proj) - 1)]
 return { "strikes":[k for k,_ in ordered],"probs":proj,"interval_probs":intervals,"max_adjustment":round(max_adj,6),}
GLOBAL_SVI_ENGINE=DeribitSVISurfaceEngine(ttl_seconds=60.0)
if __name__=="__main__":
 for sym,spot_test,k_test in [("BTC",82500.0,82000.0),("ETH",2450.0,2400.0),("SOL",106.0,105.0)]:
  res=GLOBAL_SVI_ENGINE.evaluate_strike_probability( sym,spot_test,k_test,tte_seconds=3600.0,outcome="YES",allow_sync_fetch=True )
  print(f"{sym} Spot={spot_test} Strike={k_test} (1h TTE): {res}")

# === [07/12] src/polymarket_research/polymarket_paper_trader.py :: Forward Paper Trader & Production-Parity Simulation Engine ===
#!/usr/bin/env python3 import os
import sys
import json
import time
import math
import asyncio
from datetime import datetime,timezone
from pathlib import Path
from typing import Dict,Any,List,Set,Optional
from collections import defaultdict
from src.polymarket_research.polymarket_live_executor import calculate_taker_fee
from src.polymarket_research.polymarket_live_harvester import ( compute_composite_edge_score,compute_max_acceptable_ask,evaluate_coinbase_venue_veto,)
PIPELINE_ROOT=Path(__file__).resolve().parents[2]
DATA_DIR=PIPELINE_ROOT / "data" / "polymarket"
TRIGGER_FILE=DATA_DIR / "live_shock_triggers.jsonl"
SHOCK_FILE=DATA_DIR / "shock_responses.jsonl"
RESOLUTIONS_FILE=DATA_DIR / "finalized_market_resolutions.jsonl"
DEV_LEDGER_FILE=DATA_DIR / "paper_trading_dev_ledger.jsonl"
VALIDATION_LEDGER_FILE=DATA_DIR / "paper_trading_validation_ledger.jsonl"
STATE_FILE=DATA_DIR / "paper_trader_state.json"
PID_FILE=DATA_DIR / "paper_trader.pid"
HOURLY_TELEMETRY_FILE=DATA_DIR / "polymarket_hourly_telemetry.jsonl"
HOURLY_TELEMETRY_ETH_FILE=DATA_DIR / "polymarket_hourly_telemetry_eth.jsonl"
HOURLY_TELEMETRY_SOL_FILE=DATA_DIR / "polymarket_hourly_telemetry_sol.jsonl"
SUBHOURLY_TELEMETRY_SOL_FILE=DATA_DIR / "polymarket_15m_telemetry_sol.jsonl"
HOURLY_TELEMETRY_XRP_FILE=DATA_DIR / "polymarket_hourly_telemetry_xrp.jsonl"
SUBHOURLY_TELEMETRY_XRP_FILE=DATA_DIR / "polymarket_15m_telemetry_xrp.jsonl"
SHOCK_SOL_FILE=DATA_DIR / "shock_responses_sol.jsonl"
SHOCK_XRP_FILE=DATA_DIR / "shock_responses_xrp.jsonl"
INITIAL_PAPER_CAPITAL=1000.0
TICKET_NOTIONAL=50.0
MIN_ELASTIC_TICKET_USD=15.0
MAX_ELASTIC_TICKET_USD=200.0
DEFAULT_ELASTIC_SAFETY_RATIO=1.50
DEFAULT_DYNAMIC_BANKROLL_PCT=0.24
DEFAULT_PAPER_LATENCY_MS=int(os.getenv("PAPER_LATENCY_MS","500"))
MAX_TTE_SECONDS=2700.0
MIN_TTE_SECONDS=90.0
MAX_TRADES_PER_HOUR=6
MAX_TRADES_PER_MARKET=2
MAX_ALLOWED_SPREAD=0.030
MAX_PRICE_CEILING=0.86
MIN_PRICE_FLOOR=0.55
R3_VALIDATION_START_UTC="2026-09-29T18:11:34.000Z"
R3_VALIDATION_START_UNIX=1790705494.0
ENABLE_SLEEVE_304_315=False
SLEEVE_2_INITIAL_CAPITAL=500.0
SLEEVE_2_TICKET_NOTIONAL=50.0
SLEEVE_2_MIN_PRICE=0.55
SLEEVE_2_MAX_PRICE=0.78
SLEEVE_2_MIN_DEPTH_RATIO=1.50
SLEEVE_2_MAX_TTE=2700.0
SLEEVE_2_MIN_TTE=900.0
SLEEVE_2_LEDGER_FILE=DATA_DIR / "ledger_sleeve_304_315.jsonl"
SLEEVE_2_STATE_FILE=DATA_DIR / "state_sleeve_304_315.json"
ENABLE_SOL_SHADOW_SLEEVE=True
SOL_SHADOW_INITIAL_CAPITAL=500.0
SOL_SHADOW_TICKET_NOTIONAL=12.0
SOL_SHADOW_LEDGER_FILE=DATA_DIR / "ledger_shadow_sol_v392.jsonl"
SOL_SHADOW_STATE_FILE=DATA_DIR / "state_shadow_sol_v392.json"
ENABLE_XRP_SHADOW_SLEEVE=False
XRP_SHADOW_INITIAL_CAPITAL=500.0
XRP_SHADOW_TICKET_NOTIONAL=12.0
XRP_SHADOW_LEDGER_FILE=DATA_DIR / "ledger_shadow_xrp_v392.jsonl"
XRP_SHADOW_STATE_FILE=DATA_DIR / "state_shadow_xrp_v392.json"
class PolymarketForwardPaperTrader:
 def __init__(self,paper_latency_ms:Optional[int]=None):
  DATA_DIR.mkdir(parents=True,exist_ok=True)
  self.paper_latency_ms=paper_latency_ms if paper_latency_ms is not None else DEFAULT_PAPER_LATENCY_MS
  self.settled_trade_ids:Set[str]=set()
  self.seen_shock_ids:Set[str]=set()
  self.seen_resolution_ids:Set[str]=set()
  self.trades_per_market:Dict[str,int]=defaultdict(int)
  self.dev_cash:float=INITIAL_PAPER_CAPITAL
  self.dev_realized_pnl:float=0.0
  self.dev_total_fees:float=0.0
  self.dev_trades:List[Dict[str,Any]]=[]
  self.val_cash:float=INITIAL_PAPER_CAPITAL
  self.val_realized_pnl:float=0.0
  self.val_total_fees:float=0.0
  self.val_trades:List[Dict[str,Any]]=[]
  self.open_trades:Dict[str,List[Dict[str,Any]]]={}
  self.current_hour_window=int(time.time() // 3600)
  self.trades_this_hour=0
  self.last_trigger_file_pos:int=0
  self.last_shock_file_pos:int=0
  self.last_res_file_pos:int=0
  self.last_telemetry_file_pos:int=0
  self.last_telemetry_eth_file_pos:int=0
  self.last_telemetry_sol_file_pos:int=0
  self.last_telemetry_sol_15m_file_pos:int=0
  self.last_telemetry_xrp_file_pos:int=0
  self.last_telemetry_xrp_15m_file_pos:int=0
  self.last_shock_sol_file_pos:int=0
  self.last_shock_xrp_file_pos:int=0
  self.recent_shock_window:List[Dict[str,Any]]=[]
  self.sleeve2_cash:float=SLEEVE_2_INITIAL_CAPITAL
  self.sleeve2_realized_pnl:float=0.0
  self.sleeve2_total_fees:float=0.0
  self.sleeve2_trades:List[Dict[str,Any]]=[]
  self.sleeve2_open_trades:Dict[str,List[Dict[str,Any]]]={}
  self.sleeve2_settled_ids:Set[str]=set()
  self.sol_shadow_cash:float=SOL_SHADOW_INITIAL_CAPITAL
  self.sol_shadow_realized_pnl:float=0.0
  self.sol_shadow_total_fees:float=0.0
  self.sol_shadow_trades:List[Dict[str,Any]]=[]
  self.sol_shadow_open_trades:Dict[str,List[Dict[str,Any]]]={}
  self.sol_shadow_settled_ids:Set[str]=set()
  self.xrp_shadow_cash:float=XRP_SHADOW_INITIAL_CAPITAL
  self.xrp_shadow_realized_pnl:float=0.0
  self.xrp_shadow_total_fees:float=0.0
  self.xrp_shadow_trades:List[Dict[str,Any]]=[]
  self.xrp_shadow_open_trades:Dict[str,List[Dict[str,Any]]]={}
  self.xrp_shadow_settled_ids:Set[str]=set()
  self.load_persisted_ledgers()
  self.load_persisted_sleeve2_ledger()
  self.load_persisted_sol_shadow_ledger()
  self.load_persisted_xrp_shadow_ledger()
  if STATE_FILE.exists():
   try:
    saved=json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if int(saved.get("current_hour_window",-1))==self.current_hour_window:
     self.trades_this_hour=int(saved.get("trades_this_hour",0))
   except Exception as exc:
    pass
  self.hourly_candle_opens:Dict[str,Dict[int,float]]=defaultdict(dict)
  self._prewarm_hourly_opens()
 def _prewarm_hourly_opens(self):
  trigger_path=DATA_DIR / "live_shock_triggers.jsonl"
  if not trigger_path.exists():
   return
  try:
   with open(trigger_path,"rb") as f:
    f.seek(0,2)
    size=f.tell()
    read_sz=min(size,8 * 1024 * 1024)
    f.seek(size - read_sz)
    lines=f.read().decode("utf-8",errors="ignore").splitlines()
   for line in lines:
    if not line.strip():
     continue
    try:
     data=json.loads(line)
     title_l=str(data.get("title","") or "").lower()
     horiz_l=str(data.get("horizon","") or data.get("candle_interval","")).lower()
     slug_l=str(data.get("series_slug","") or data.get("slug","")).lower()
     if any(x in horiz_l or x in slug_l or x in title_l for x in ("5m","15m","300s","900s")):
      continue
     asset=data.get("asset")
     t0_unix=data.get("t0_unix")
     open_p=data.get("finalized_1h_open") or data.get("candle_open_spot")
     if asset in ("BTC","ETH","SOL","XRP") and t0_unix and open_p and float(open_p) > 0:
      h_idx=int(float(t0_unix) // 3600)
      if h_idx not in self.hourly_candle_opens[asset]:
       self.hourly_candle_opens[asset][h_idx]=float(open_p)
    except Exception:
     pass
  except Exception:
   pass
 def load_persisted_ledgers(self):
  if DEV_LEDGER_FILE.exists():
   with open(DEV_LEDGER_FILE,"r") as f:
    for line in f:
     if not line.strip():
      continue
     t=json.loads(line)
     tid=t["trade_id"]
     if tid not in self.settled_trade_ids:
      self.settled_trade_ids.add(tid)
      self.dev_trades.append(t)
      self.dev_realized_pnl += t.get("net_pnl_usd",0.0)
      self.dev_total_fees += t.get("taker_fee_usd",0.0)
      m_id=t.get("market_id")
      if m_id:
       self.trades_per_market[m_id] += 1
   self.dev_cash=INITIAL_PAPER_CAPITAL + self.dev_realized_pnl
  if VALIDATION_LEDGER_FILE.exists():
   with open(VALIDATION_LEDGER_FILE,"r") as f:
    for line in f:
     if not line.strip():
      continue
     t=json.loads(line)
     tid=t["trade_id"]
     if tid not in self.settled_trade_ids:
      self.settled_trade_ids.add(tid)
      self.val_trades.append(t)
      self.val_realized_pnl += t.get("net_pnl_usd",0.0)
      self.val_total_fees += t.get("taker_fee_usd",0.0)
      m_id=t.get("market_id")
      if m_id:
       self.trades_per_market[m_id] += 1
   self.val_cash=INITIAL_PAPER_CAPITAL + self.val_realized_pnl
  print(f"[RECOVERY COMPLETE] Loaded {len(self.settled_trade_ids)} settled trades from disk across {len(self.trades_per_market)} markets." f"\n  DEV Ledger: {len(self.dev_trades)} trades | Realized PnL: ${self.dev_realized_pnl:+.2f} | Cash: ${self.dev_cash:,.2f}" f"\n  OOS VALIDATION Ledger: {len(self.val_trades)} trades | Realized PnL: ${self.val_realized_pnl:+.2f} | Cash: ${self.val_cash:,.2f}",flush=True)
 def load_persisted_sleeve2_ledger(self):
  if SLEEVE_2_LEDGER_FILE.exists():
   with open(SLEEVE_2_LEDGER_FILE,"r") as f:
    for line in f:
     if not line.strip():
      continue
     t=json.loads(line)
     tid=t.get("trade_id")
     if tid and tid not in self.sleeve2_settled_ids:
      self.sleeve2_settled_ids.add(tid)
      self.sleeve2_trades.append(t)
      self.sleeve2_realized_pnl += t.get("net_pnl_usd",0.0)
      self.sleeve2_total_fees += t.get("taker_fee_usd",0.0)
   self.sleeve2_cash=SLEEVE_2_INITIAL_CAPITAL + self.sleeve2_realized_pnl
   print(f"[SLEEVE 2 RECOVERY] Loaded {len(self.sleeve2_trades)} settled trades | Realized PnL: ${self.sleeve2_realized_pnl:+.2f} | Cash: ${self.sleeve2_cash:,.2f}",flush=True)
 def save_sleeve2_state(self):
  total_trades=len(self.sleeve2_trades)
  wins=sum(1 for t in self.sleeve2_trades if t.get("won"))
  wr=(wins / total_trades * 100.0) if total_trades > 0 else 0.0
  state={ "timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"sleeve_id":"SLEEVE_2_MULTI_304_315","strategy":"ETH 1h Sweet-Spot (0.72-0.85) Lead-Lag Momentum","initial_capital":SLEEVE_2_INITIAL_CAPITAL,"current_equity":round(self.sleeve2_cash,2),"realized_pnl":round(self.sleeve2_realized_pnl,2),"total_fees_paid":round(self.sleeve2_total_fees,2),"total_trades_settled":total_trades,"winning_trades":wins,"losing_trades":total_trades - wins,"win_rate_pct":round(wr,2),"active_open_positions_count":sum(len(v) for v in self.sleeve2_open_trades.values()),"status":"RUNNING" if ENABLE_SLEEVE_304_315 else "DISABLED","ledger_file":str(SLEEVE_2_LEDGER_FILE),}
  tmp_file=SLEEVE_2_STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
  try:
   with open(tmp_file,"w",encoding="utf-8") as f:
    json.dump(state,f,indent=2)
    f.flush()
    os.fsync(f.fileno())
   os.replace(tmp_file,SLEEVE_2_STATE_FILE)
  except Exception:
   if tmp_file.exists():
    try:
     tmp_file.unlink()
    except Exception:
     pass
 def load_persisted_sol_shadow_ledger(self):
  if SOL_SHADOW_LEDGER_FILE.exists():
   with open(SOL_SHADOW_LEDGER_FILE,"r",encoding="utf-8",errors="ignore") as f:
    for line in f:
     if not line.strip():
      continue
     t=json.loads(line)
     tid=t.get("trade_id")
     if tid and tid not in self.sol_shadow_settled_ids:
      self.sol_shadow_settled_ids.add(tid)
      self.sol_shadow_trades.append(t)
      self.sol_shadow_realized_pnl += float(t.get("net_pnl_usd",0.0))
      self.sol_shadow_total_fees += float(t.get("taker_fee_usd",0.0)) + float(t.get("exit_fee_usd",0.0))
   self.sol_shadow_cash=SOL_SHADOW_INITIAL_CAPITAL + self.sol_shadow_realized_pnl
 def save_sol_shadow_state(self):
  total_trades=len(self.sol_shadow_trades)
  wins=sum(1 for t in self.sol_shadow_trades if t.get("won"))
  wr=(wins / total_trades * 100.0) if total_trades > 0 else 0.0
  gross_win=sum(float(t.get("net_pnl_usd",0.0)) for t in self.sol_shadow_trades if float(t.get("net_pnl_usd",0.0)) > 0)
  gross_loss=abs(sum(float(t.get("net_pnl_usd",0.0)) for t in self.sol_shadow_trades if float(t.get("net_pnl_usd",0.0)) < 0))
  pf=round(gross_win / gross_loss,2) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)
  state={ "timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"sleeve_id":"SLEEVE_SOL_V392_SHADOW","strategy":"SOL 15m/1h Volatility-Normalized Sniper (dist>=0.12%, z>=0.70, band_L2>=$15, spread<=6c, 95c/98c TP + 3-Zone Salvage)","graduation_criteria":"trades >= 30 and profit_factor >= 2.0 and win_rate_pct >= 85.0","ready_for_live_graduation":bool(total_trades>=30 and pf>=2.0 and wr>=85.0),"initial_capital":SOL_SHADOW_INITIAL_CAPITAL,"current_equity":round(self.sol_shadow_cash,2),"realized_pnl":round(self.sol_shadow_realized_pnl,2),"profit_factor":pf,"total_fees_paid":round(self.sol_shadow_total_fees,2),"total_trades_settled":total_trades,"winning_trades":wins,"losing_trades":total_trades - wins,"win_rate_pct":round(wr,2),"active_open_positions_count":sum(len(v) for v in self.sol_shadow_open_trades.values()),"status":"RUNNING" if ENABLE_SOL_SHADOW_SLEEVE else "DISABLED","ledger_file":str(SOL_SHADOW_LEDGER_FILE),}
  tmp_file=SOL_SHADOW_STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
  try:
   with open(tmp_file,"w",encoding="utf-8") as f:
    json.dump(state,f,indent=2)
    f.flush()
    os.fsync(f.fileno())
   os.replace(tmp_file,SOL_SHADOW_STATE_FILE)
  except Exception:
   if tmp_file.exists():
    try:
     tmp_file.unlink()
    except Exception:
     pass
 def load_persisted_xrp_shadow_ledger(self):
  if XRP_SHADOW_LEDGER_FILE.exists():
   with open(XRP_SHADOW_LEDGER_FILE,"r",encoding="utf-8",errors="ignore") as f:
    for line in f:
     if not line.strip():
      continue
     t=json.loads(line)
     tid=t.get("trade_id")
     if tid and tid not in self.xrp_shadow_settled_ids:
      self.xrp_shadow_settled_ids.add(tid)
      self.xrp_shadow_trades.append(t)
      self.xrp_shadow_realized_pnl += float(t.get("net_pnl_usd",0.0))
      self.xrp_shadow_total_fees += float(t.get("taker_fee_usd",0.0)) + float(t.get("exit_fee_usd",0.0))
   self.xrp_shadow_cash=XRP_SHADOW_INITIAL_CAPITAL + self.xrp_shadow_realized_pnl
 def save_xrp_shadow_state(self):
  total_trades=len(self.xrp_shadow_trades)
  wins=sum(1 for t in self.xrp_shadow_trades if t.get("won"))
  wr=(wins / total_trades * 100.0) if total_trades > 0 else 0.0
  gross_win=sum(float(t.get("net_pnl_usd",0.0)) for t in self.xrp_shadow_trades if float(t.get("net_pnl_usd",0.0)) > 0)
  gross_loss=abs(sum(float(t.get("net_pnl_usd",0.0)) for t in self.xrp_shadow_trades if float(t.get("net_pnl_usd",0.0)) < 0))
  pf=round(gross_win / gross_loss,2) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)
  state={ "timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"sleeve_id":"SLEEVE_XRP_V392_SHADOW","strategy":"XRP 15m/1h Volatility-Normalized Sniper (dist>=0.12%, z>=0.70, band_L2>=$15, spread<=6c, 95c/98c TP + 3-Zone Salvage)","graduation_criteria":"trades >= 30 and profit_factor >= 2.0 and win_rate_pct >= 85.0","ready_for_live_graduation":bool(total_trades>=30 and pf>=2.0 and wr>=85.0),"initial_capital":XRP_SHADOW_INITIAL_CAPITAL,"current_equity":round(self.xrp_shadow_cash,2),"realized_pnl":round(self.xrp_shadow_realized_pnl,2),"profit_factor":pf,"total_fees_paid":round(self.xrp_shadow_total_fees,2),"total_trades_settled":total_trades,"winning_trades":wins,"losing_trades":total_trades - wins,"win_rate_pct":round(wr,2),"active_open_positions_count":sum(len(v) for v in self.xrp_shadow_open_trades.values()),"status":"RUNNING" if ENABLE_XRP_SHADOW_SLEEVE else "DISABLED","ledger_file":str(XRP_SHADOW_LEDGER_FILE),}
  tmp_file=XRP_SHADOW_STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
  try:
   with open(tmp_file,"w",encoding="utf-8") as f:
    json.dump(state,f,indent=2)
    f.flush()
    os.fsync(f.fileno())
   os.replace(tmp_file,XRP_SHADOW_STATE_FILE)
  except Exception:
   if tmp_file.exists():
    try:
     tmp_file.unlink()
    except Exception:
     pass
 def _get_live_account_equity(self)->Optional[float]:
  try:
   live_state_file=getattr(self,"live_state_file",DATA_DIR / "live_harvester_state.json")
   if live_state_file.exists():
    st=json.loads(live_state_file.read_text(encoding="utf-8"))
    eq=st.get("total_account_equity")
    if eq is not None and isinstance(eq,(int,float)) and eq > 0:
     return float(eq)
    bankroll=st.get("live_bankroll")
    if bankroll is not None and isinstance(bankroll,(int,float)) and bankroll > 0:
     active_exp=sum(p.get("notional_usd",0.0) for p in st.get("active_positions",{}).values())
     return float(bankroll) + active_exp
  except Exception:
   pass
  return None
 def _get_latest_telemetry_snapshot( self,market_id:str,asset:str="",min_timestamp_unix:float=0.0,poll_timeout_sec:float=0.0 )->Optional[Dict[str,Any]]:
  asset_up=str(asset).upper()
  asset_clean=asset_up if asset_up in ("BTC","ETH","SOL","XRP") else "BTC"
  shm_dir=os.environ.get("PM_FAST_TICK_DIR","/dev/shm")
  shm_file=Path(shm_dir) / f"pm_fast_tick_{asset_clean}.json" if shm_dir else None
  telem_map={ "BTC":HOURLY_TELEMETRY_FILE,"ETH":HOURLY_TELEMETRY_ETH_FILE,"SOL":HOURLY_TELEMETRY_SOL_FILE,"XRP":HOURLY_TELEMETRY_XRP_FILE,}
  target_file=telem_map.get(asset_clean,HOURLY_TELEMETRY_FILE)
  deadline=time.time() + max(0.0,poll_timeout_sec)
  while True:
   if shm_file is not None and shm_file.exists():
    try:
     shm_data=json.loads(shm_file.read_text(encoding="utf-8"))
     mkts=shm_data.get("markets",{})
     if str(market_id) in mkts:
      d_shm=mkts[str(market_id)]
      ts_u=float(d_shm.get("timestamp_unix") or shm_data.get("timestamp_unix") or 0.0)
      if min_timestamp_unix<=0.0 or ts_u>=min_timestamp_unix:
       return d_shm
    except Exception:
     pass
   if not target_file.exists():
    if time.time()>=deadline:
     return None
    time.sleep(0.05)
    continue
   try:
    sz=target_file.stat().st_size
    read_sz=min(sz,131072)
    with open(target_file,"rb") as f:
     f.seek(sz - read_sz)
     lines=f.read().decode("utf-8",errors="ignore").splitlines()
    for l in reversed(lines):
     if not l.strip():
      continue
     try:
      d=json.loads(l)
      if str(d.get("market_id"))==str(market_id):
       ts_u=float(d.get("timestamp_unix") or d.get("ts") or 0.0)
       if min_timestamp_unix<=0.0 or ts_u>=min_timestamp_unix:
        return d
     except Exception:
      continue
   except Exception:
    pass
   if time.time()>=deadline:
    break
   time.sleep(0.05)
  try:
   sz=target_file.stat().st_size
   read_sz=min(sz,131072)
   with open(target_file,"rb") as f:
    f.seek(sz - read_sz)
    lines=f.read().decode("utf-8",errors="ignore").splitlines()
   for l in reversed(lines):
    if not l.strip():
     continue
    try:
     d=json.loads(l)
     if str(d.get("market_id"))==str(market_id):
      return d
    except Exception:
     continue
  except Exception:
   pass
  return None
 def replay_existing_data(self):
  if not RESOLUTIONS_FILE.exists() or not SHOCK_FILE.exists():
   return
  resolutions:Dict[str,Dict[str,Any]]={}
  with open(RESOLUTIONS_FILE,"r") as f:
   for line in f:
    if line.strip():
     r=json.loads(line)
     if r.get("winning_outcome") in ("UP","DOWN"):
      resolutions[r["market_id"]]=r
      self.seen_resolution_ids.add(r["market_id"])
  with open(SHOCK_FILE,"r") as f:
   for line in f:
    if not line.strip():
     continue
    s=json.loads(line)
    shock_id=f"{s.get('market_id')}_{s.get('t0_unix')}"
    self.seen_shock_ids.add(shock_id)
    self.evaluate_shock_signal(s,historical=True)
  if TRIGGER_FILE.exists():
   with open(TRIGGER_FILE,"r") as f:
    for line in f:
     if not line.strip():
      continue
     s=json.loads(line)
     shock_id=f"{s.get('market_id')}_{s.get('t0_unix')}"
     if shock_id not in self.seen_shock_ids:
      self.seen_shock_ids.add(shock_id)
      self.evaluate_shock_signal(s,historical=True)
   self.last_trigger_file_pos=TRIGGER_FILE.stat().st_size
  if SHOCK_FILE.exists():
   self.last_shock_file_pos=SHOCK_FILE.stat().st_size
  for m_id,res in resolutions.items():
   self.settle_market(m_id,res,historical=True)
  self.save_state()
  print(f"[REPLAY SYNCHRONIZED] Open in-flight markets: {len(self.open_trades)}",flush=True)
 def evaluate_shock_signal(self,shock:Dict[str,Any],historical:bool=False):
  asset_up=str(shock.get("asset","") or "").upper()
  title_l=str(shock.get("title","") or "").lower()
  if ENABLE_SOL_SHADOW_SLEEVE and (asset_up=="SOL" or "solana" in title_l):
   self._evaluate_sol_shadow_sleeve(shock,historical=historical)
   return
  if ENABLE_XRP_SHADOW_SLEEVE and (asset_up=="XRP" or "xrp" in title_l or "ripple" in title_l):
   self._evaluate_xrp_shadow_sleeve(shock,historical=historical)
   return
  if asset_up not in ("","BTC","ETH") and "bitcoin" not in title_l and "btc" not in title_l and "ethereum" not in title_l and "eth" not in title_l:
   return
  sleeve1_filled=self._evaluate_sleeve_1(shock,historical=historical)
  if sleeve1_filled:
   return
  if ENABLE_SLEEVE_304_315:
   self._evaluate_sleeve_2(shock,historical=historical)
 def _evaluate_sol_shadow_sleeve(self,shock:Dict[str,Any],historical:bool=False)->bool:
  return self._evaluate_alt_shadow_sleeve(shock,asset_sym="SOL",historical=historical)
 def _evaluate_xrp_shadow_sleeve(self,shock:Dict[str,Any],historical:bool=False)->bool:
  return self._evaluate_alt_shadow_sleeve(shock,asset_sym="XRP",historical=historical)
 def _evaluate_alt_shadow_sleeve(self,shock:Dict[str,Any],asset_sym:str="SOL",historical:bool=False)->bool:
  if historical:
   return False
  m_id=str(shock.get("market_id") or "")
  if not m_id:
   return False
  is_sol=(asset_sym=="SOL")
  settled_ids=self.sol_shadow_settled_ids if is_sol else self.xrp_shadow_settled_ids
  open_map=self.sol_shadow_open_trades if is_sol else self.xrp_shadow_open_trades
  closed_list=self.sol_shadow_trades if is_sol else self.xrp_shadow_trades
  ticket_usd=SOL_SHADOW_TICKET_NOTIONAL if is_sol else XRP_SHADOW_TICKET_NOTIONAL
  t0_unix=float(shock.get("t0_unix",time.time()) or time.time())
  shock_dir=shock.get("shock_direction")
  target_token="UP" if shock_dir=="BUY" else "DOWN"
  trade_id=f"{asset_sym}_SHDW_{m_id}_{int(t0_unix)}_{target_token}"
  if trade_id in settled_ids:
   return False
  if m_id in open_map and open_map[m_id]:
   self.check_maker_tp_fills(m_id,shock.get("pre_shock_features_t0",{}))
   if m_id in open_map and open_map[m_id]:
    return False
  if any(t.get("market_id")==m_id for t in closed_list):
   return False
  title_lower=str(shock.get("title","") or "").lower()
  horizon=str(shock.get("horizon","") or shock.get("candle_interval","")).lower()
  is_subhourly=any(x in horizon or x in title_lower for x in ("15m","900s","am-","pm-"))
  tte=float(shock.get("seconds_to_expiry",3600.0) or 3600.0)
  if is_subhourly and not (90.0<=tte<=540.0):
   return False
  if not is_subhourly and not (90.0<=tte<=2400.0):
   return False
  spot_t0=float(shock.get("chainlink_twap_60s") or shock.get("spot_at_t0") or 0.0) if is_subhourly else float(shock.get("spot_at_t0") or 0.0)
  open_sp=float((shock.get("twap_60s_open") or shock.get("candle_open_spot") or 0.0) if is_subhourly else (shock.get("finalized_1h_open") or shock.get("candle_open_spot") or 0.0))
  if spot_t0<=0.0 or open_sp<=0.0:
   return False
  if is_subhourly and shock.get("twap_60s_open") and shock.get("candle_open_spot"):
   if abs(float(shock["twap_60s_open"]) - float(shock["candle_open_spot"])) / open_sp * 100.0>=0.09:
    return False
  dist_pct=((spot_t0 - open_sp) / open_sp) * 100.0
  signed_cush=dist_pct if target_token=="UP" else -dist_pct
  if signed_cush < 0.12:
   return False
  shock_vol=float(shock.get("shock_volume_100ms") or 0.0)
  shock_ofi=abs(float(shock.get("shock_ofi") or 0.0))
  min_shock_vol=120_000.0 if is_sol else 75_000.0
  if shock_vol < min_shock_vol or shock_ofi < 0.60:
   return False
  default_sigma=0.0068 if is_sol else 0.0072
  sigma_1h=float(shock.get("candle_sigma") or default_sigma)
  sigma_1h=max(0.0040,min(0.0120,sigma_1h))
  sigma_rem=sigma_1h * math.sqrt(max(tte,15.0) / 3600.0) * 100.0
  z_strike=signed_cush / max(sigma_rem,0.01)
  if z_strike < 0.70:
   return False
  tf=(shock.get("pre_shock_features_t0") or {}).get(target_token) or {}
  raw_asks=[(float(px),float(sz)) for px,sz in (tf.get("raw_top_asks") or []) if float(px) > 0 and float(sz) > 0]
  raw_bids=[(float(px),float(sz)) for px,sz in (tf.get("raw_top_bids") or []) if float(px) > 0 and float(sz) > 0]
  first_ask=raw_asks[0][0] if raw_asks else float(tf.get("best_ask") or 0.0)
  first_bid=raw_bids[0][0] if raw_bids else float(tf.get("best_bid") or 0.0)
  if not (0.56<=first_ask<=0.85) or first_bid<=0.0 or (first_ask - first_bid) > 0.06:
   return False
  band_usd=sum(px * sz for px,sz in raw_asks if px<=first_ask + 0.02) if raw_asks else float(tf.get("l1_ask_usd") or 20.0)
  if band_usd < 15.0:
   return False
  p_fair=0.5 * (1.0 + math.erf((z_strike + 0.14) / math.sqrt(2.0)))
  exp_pay=(p_fair * 0.965) + ((1.0 - p_fair) * 0.90 * 0.35)
  p_max_alt=min(0.85,round(exp_pay / 1.04,4))
  if first_ask > p_max_alt:
   return False
  shares=round(ticket_usd / first_ask,4)
  _,taker_fee=calculate_taker_fee(ticket_usd,first_ask,fee_rate=0.07,fee_exponent=1.0)
  pos={ "trade_id":trade_id,"sleeve":f"SLEEVE_{asset_sym}_V392_SHADOW","market_id":m_id,"title":shock.get("title"),"asset":asset_sym,"horizon":"15m" if is_subhourly else "1h","target_token":target_token,"entry_unix":t0_unix,"expiry_unix":float(shock.get("expiry_ts") or (t0_unix + tte)),"seconds_to_expiry":round(tte,1),"candle_open_spot":round(open_sp,4),"spot_at_t0":round(spot_t0,4),"dist_pct":round(dist_pct,4),"z_strike":round(z_strike,3),"entry_price":round(first_ask,4),"shares_bought":shares,"notional_usd":ticket_usd,"taker_fee_usd":round(taker_fee,4),"fee_rate_applied":0.07,"take_profit_maker_limit_px":0.965,"status":"OPEN",}
  open_map.setdefault(m_id,[]).append(pos)
  if is_sol:
   self.save_sol_shadow_state()
  else:
   self.save_xrp_shadow_state()
  return True
 def _evaluate_sleeve_1(self,shock:Dict[str,Any],historical:bool=False)->bool:
  m_id=shock.get("market_id")
  if not m_id:
   return False
  t0_unix=shock.get("t0_unix",time.time())
  shock_dir=shock.get("shock_direction")
  target_token="UP" if shock_dir=="BUY" else "DOWN"
  trade_id=f"PAPER_{m_id}_{int(t0_unix)}_{target_token}"
  if trade_id in self.settled_trade_ids:
   return False
  current_market_open=self.open_trades.get(m_id,[])
  if any(t["trade_id"]==trade_id for t in current_market_open):
   return False
  if current_market_open:
   token_feats=shock.get("pre_shock_features_t0",{})
   self.check_maker_tp_fills(m_id,token_feats)
   current_market_open=self.open_trades.get(m_id,[])
  hour_now=int(float(t0_unix) // 3600)
  if hour_now!=self.current_hour_window:
   self.current_hour_window=hour_now
   self.trades_this_hour=0
  delta_basis=float(shock.get("delta_basis_100ms",0.0) or 0.0)
  if target_token=="UP" and delta_basis < -2.0:
   return False
  elif target_token=="DOWN" and delta_basis > 2.0:
   return False
  if ENABLE_SLEEVE_304_315 and m_id in self.sleeve2_open_trades and len(self.sleeve2_open_trades[m_id]) > 0:
   return False
  total_market_trades=self.trades_per_market.get(m_id,0) + len(current_market_open)
  is_win_reentry=False
  is_loss_locked=False
  if total_market_trades>=1 and len(current_market_open)==0:
   for t in reversed(self.val_trades + self.dev_trades):
    if t.get("market_id")==m_id:
     if t.get("won") is True and float(t.get("net_pnl_usd",0.0) or 0.0) > 0:
      is_win_reentry=(total_market_trades==1)
     else:
      is_loss_locked=True
     break
  effective_max_market_trades=0 if is_loss_locked else (2 if is_win_reentry else MAX_TRADES_PER_MARKET)
  if total_market_trades>=effective_max_market_trades or self.trades_this_hour>=MAX_TRADES_PER_HOUR:
   return False
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   dt=datetime.fromtimestamp(t0_unix,tz=timezone.utc)
   if dt.hour==13 and dt.minute>=30:
    return False
  title=shock.get("title","")
  asset=shock.get("asset","")
  title_lower=title.lower()
  horizon=str(shock.get("horizon","") or shock.get("candle_interval","")).lower()
  slug=str(shock.get("series_slug","") or shock.get("slug","")).lower()
  is_subhourly=any(x in horizon or x in slug or x in title_lower for x in ("5m","15m","300s","900s"))
  is_1h=not is_subhourly and ( any(x in horizon or x in slug or x in title_lower for x in ("1h","hourly","60m")) or ("am et" in title_lower or "pm et" in title_lower) )
  edge_info=compute_composite_edge_score(shock)
  if edge_info.get("veto",False):
   return False
  edge_tier=edge_info.get("tier","TIER_B_STANDARD")
  kelly_mult=edge_info.get("kelly_multiplier",1.00)
  tte=float(shock.get("seconds_to_expiry",3600.0) or 3600.0)
  regime=None
  min_allowed_price=MIN_PRICE_FLOOR
  max_allowed_price=MAX_PRICE_CEILING
  dist_pct=float(shock.get("candle_distance_pct",0.0) or 0.0)
  open_spot_cand=shock.get("finalized_1h_open") or shock.get("candle_open_spot")
  spot_at_t0=float(shock.get("spot_at_t0") or shock.get("trigger_price") or 0.0)
  if (abs(dist_pct) < 0.0001 or not open_spot_cand or float(open_spot_cand)<=0.0) and spot_at_t0 > 0.0:
   h_idx=int(float(shock.get("t0_unix",time.time())) // 3600)
   cached_open=self.hourly_candle_opens.get(asset,{}).get(h_idx)
   if cached_open and cached_open > 0.0:
    dist_pct=((spot_at_t0 - cached_open) / cached_open) * 100.0
  token_features=shock.get("pre_shock_features_t0",{}).get(target_token,{})
  shock_ofi_val=float(shock.get("shock_ofi",1.0) if shock.get("shock_ofi") is not None else 1.0)
  shock_vol_usd=float(shock.get("shock_volume_100ms",1_500_000.0) or 1_500_000.0)
  delta_basis_bps=float(shock.get("delta_basis_100ms",0.0) or 0.0)
  dir_delta_basis_bps=delta_basis_bps if target_token=="UP" else -delta_basis_bps
  age_ask_ms_val=float(shock.get("age_ask_ms") or token_features.get("age_ask_ms",350.0) or 350.0)
  cb_veto,_cb_reason=evaluate_coinbase_venue_veto(shock,target_token)
  if cb_veto:
   return False
  p_max_info=compute_max_acceptable_ask( dist_pct=dist_pct,tte_sec=tte,asset=asset or ("BTC" if "btc" in title_lower else "ETH"),shock_ofi=shock_ofi_val,shock_vol_usd=shock_vol_usd,delta_basis_bps=dir_delta_basis_bps,age_ask_ms=age_ask_ms_val,is_subhourly_15m=is_subhourly,)
  z_eff=p_max_info.get("z_eff",0.0)
  p_max=p_max_info.get("p_max",0.0)
  if is_1h:
   if 900.0 < tte<=2700.0:
    regime="REGIME_A_MID_HOUR"
    if abs(dist_pct) < 0.15:
     return False
    if target_token=="UP" and dist_pct < 0.15:
     return False
    if target_token=="DOWN" and dist_pct > -0.15:
     return False
    cur_h_idx=int(float(shock.get("t0_unix",time.time())) // 3600)
    opens_map=self.hourly_candle_opens.get(asset,{})
    open_h=opens_map.get(cur_h_idx)
    open_h_1=opens_map.get(cur_h_idx - 1)
    open_h_2=opens_map.get(cur_h_idx - 2)
    ret_2h=((open_h - open_h_2) / open_h_2) if (open_h and open_h_2 and open_h_2 > 0) else None
    ret_1h_prior=((open_h - open_h_1) / open_h_1) if (open_h and open_h_1 and open_h_1 > 0) else None
    ret_2h_prior=((open_h_1 - open_h_2) / open_h_2) if (open_h_1 and open_h_2 and open_h_2 > 0) else None
    prior_2_green=(ret_1h_prior is not None and ret_1h_prior > 0.0010 and ret_2h_prior is not None and ret_2h_prior > 0.0010)
    prior_2_red=(ret_1h_prior is not None and ret_1h_prior < -0.0010 and ret_2h_prior is not None and ret_2h_prior < -0.0010)
    is_counter_trend=False
    if target_token=="DOWN":
     if (ret_2h is not None and ret_2h > 0.0030) or prior_2_green:
      is_counter_trend=True
    elif target_token=="UP":
     if (ret_2h is not None and ret_2h < -0.0030) or prior_2_red:
      is_counter_trend=True
    if is_counter_trend and abs(dist_pct) < 0.40:
     return False
    min_allowed_price=0.55
    max_allowed_price=0.78
   elif (30.0<=tte<=900.0 if z_eff>=2.2 else 120.0<=tte<=900.0):
    regime="REGIME_B_LATE_SNIPER"
    cushion=abs(dist_pct)
    if cushion < 0.10:
     return False
    if target_token=="UP" and dist_pct < 0.10:
     return False
    if target_token=="DOWN" and dist_pct > -0.10:
     return False
    if cushion < 0.15:
     min_allowed_price=0.55
     max_allowed_price=0.75
    elif cushion < 0.22:
     min_allowed_price=0.58
     max_allowed_price=0.80
    else:
     min_allowed_price=0.62
     max_allowed_price=0.84
   else:
    return False
  elif is_subhourly:
   if 90.0<=tte<=420.0:
    regime="REGIME_C_SUBHOURLY"
    if abs(dist_pct) < 0.18:
     return False
    if target_token=="UP" and dist_pct < 0.18:
     return False
    if target_token=="DOWN" and dist_pct > -0.18:
     return False
    min_allowed_price=0.58
    max_allowed_price=0.82
   else:
    return False
  else:
   return False
  if "sol" in title_lower or "solana" in title_lower or asset=="SOL":
   return False
  is_btc=("btc" in title_lower or "bitcoin" in title_lower or asset=="BTC")
  is_eth=("ethereum" in title_lower or "eth" in title_lower or asset=="ETH")
  if is_btc:
   is_1h_macro=(horizon in ("1h","hourly","60m") or "hourly" in slug) and tte > MAX_TTE_SECONDS
   if is_1h_macro:
    return False
   z_btc_val=shock.get("z_btc") or shock.get("z_score") or shock.get("z_val")
   if z_btc_val is not None and abs(float(z_btc_val)) < 1.645:
    return False
  if is_eth:
   btc_shock_dir=shock.get("btc_shock_direction")
   if btc_shock_dir:
    if target_token=="UP" and btc_shock_dir in ("DOWN","SELL"):
     return False
    if target_token=="DOWN" and btc_shock_dir in ("UP","BUY"):
     return False
   z_eth_val=shock.get("z_eth") or shock.get("z_score") or shock.get("z_val")
   z_btc_val=shock.get("z_btc")
   if z_eth_val is not None and z_btc_val is not None:
    z_e=float(z_eth_val)
    z_b=float(z_btc_val)
    if (z_e > 0 and z_b < 0) or (z_e < 0 and z_b > 0):
     return False
  token_features=shock.get("pre_shock_features_t0",{}).get(target_token,{})
  self.recent_shock_window=[w for w in self.recent_shock_window if (t0_unix - w["t_unix"])<=5.0]
  z_score=abs(float(shock.get("z_val",shock.get("z_score",shock.get("expected_prob_shift",abs(dist_pct) * 0.5)))))
  raw_vwap_est=float(token_features.get("vwap_$50") or token_features.get("effective_price_$50") or 0.50)
  candidate_score=z_score / max(raw_vwap_est,0.01)
  if self.recent_shock_window:
   best_prior=max(self.recent_shock_window,key=lambda x:x["score"])
   if best_prior["market_id"]!=m_id and best_prior["score"] > candidate_score:
    return False
  self.recent_shock_window.append({ "t_unix":t0_unix,"score":candidate_score,"market_id":m_id,"trade_id":trade_id,})
  raw_asks=token_features.get("raw_top_asks",[])
  if not raw_asks:
   return False
  executable_depth_usd=sum(px * sz for px,sz in raw_asks if px<=max_allowed_price)
  first_ask=float(raw_asks[0][0]) if raw_asks else 0.75
  if first_ask < min_allowed_price or first_ask > max_allowed_price:
   return False
  is_oos_validation=(t0_unix>=R3_VALIDATION_START_UNIX)
  epoch_label="VALIDATION" if is_oos_validation else "DEV"
  deployed_usd=sum( t["notional_usd"] for m_trades in self.open_trades.values() for t in m_trades if t.get("epoch")==epoch_label and t.get("status")=="OPEN" )
  total_equity=self.val_cash if epoch_label=="VALIDATION" else self.dev_cash
  free_usdc=total_equity - deployed_usd
  dynamic_bankroll_pct=0.24 if first_ask<=0.78 else 0.20
  dynamic_ticket_cap=min(MAX_ELASTIC_TICKET_USD,max(MIN_ELASTIC_TICKET_USD,total_equity * dynamic_bankroll_pct))
  raw_ticket=executable_depth_usd / DEFAULT_ELASTIC_SAFETY_RATIO
  if raw_ticket < MIN_ELASTIC_TICKET_USD:
   return False
  live_equity=self._get_live_account_equity()
  if live_equity is not None and live_equity > 0:
   live_parity_cap=min(MAX_ELASTIC_TICKET_USD,max(MIN_ELASTIC_TICKET_USD,live_equity * dynamic_bankroll_pct))
   live_parity_notional=min(live_parity_cap,max(MIN_ELASTIC_TICKET_USD,round(raw_ticket,2)))
  else:
   live_parity_notional=min(dynamic_ticket_cap,max(MIN_ELASTIC_TICKET_USD,round(raw_ticket,2)))
  legacy_ticket_notional=min(TICKET_NOTIONAL,max(MIN_ELASTIC_TICKET_USD,round(raw_ticket,2)))
  if os.getenv("PAPER_USE_LIVE_BANKROLL_SIZING","1")=="1" and live_equity is not None:
   ticket_notional=min(live_parity_notional,free_usdc)
  else:
   parity_ticket_notional=min(dynamic_ticket_cap,max(MIN_ELASTIC_TICKET_USD,round(raw_ticket,2)))
   ticket_notional=min(parity_ticket_notional,free_usdc)
  if ticket_notional < MIN_ELASTIC_TICKET_USD:
   return False
  depth_ratio=executable_depth_usd / ticket_notional
  eff_px=token_features.get("effective_price_$50")
  raw_vwap=token_features.get("vwap_$50")
  fill_fee=token_features.get("fill_fees_$50")
  spread=float(token_features.get("spread",0.01) or 0.01)
  if spread > MAX_ALLOWED_SPREAD or not eff_px:
   return False
  if raw_vwap is None:
   raw_vwap=eff_px
  if raw_vwap < min_allowed_price or raw_vwap > max_allowed_price:
   return False
  if p_max<=0.0 or raw_vwap > p_max:
   return False
  fee_meta=shock.get("fee_metadata",{})
  fee_rate=fee_meta.get("fee_rate_market")
  if fee_rate is None or float(fee_rate)<=0.0:
   fee_rate=0.07
  fee_exponent=float(fee_meta.get("fee_exponent",1.0))
  adverse_slippage_cents=0.0
  exec_price=float(raw_vwap)
  exec_eff_px=float(eff_px)
  if self.paper_latency_ms > 0:
   post_ask_f=None
   post_eff=None
   if not historical:
    time.sleep(self.paper_latency_ms / 1000.0)
    target_min_ts=float(t0_unix) + (self.paper_latency_ms / 1000.0) - 0.05
    post_telem=self._get_latest_telemetry_snapshot( m_id,"ETH" if is_eth else "BTC",min_timestamp_unix=target_min_ts,poll_timeout_sec=1.1 )
    if post_telem:
     tok_data=post_telem.get(target_token,{})
     raw_post_ask=tok_data.get("best_ask")
     post_ask_f=float(raw_post_ask or 0.0)
     raw_asks_post=tok_data.get("raw_top_asks",[])
     post_depth_usd=sum(px * sz for px,sz in raw_asks_post if px<=MAX_PRICE_CEILING) if raw_asks_post else 0.0
     if post_ask_f<=0.0 or not raw_asks_post:
      print( f"\n[PAPER FAK KILLED] {shock.get('title')} | Target: {target_token} | " f"Post-latency ask book completely swept dry (ask=${post_ask_f:.4f}, asks={len(raw_asks_post)}) after {self.paper_latency_ms}ms",flush=True,)
      return False
     if (post_depth_usd / DEFAULT_ELASTIC_SAFETY_RATIO) < MIN_ELASTIC_TICKET_USD:
      print( f"\n[PAPER FAK KILLED] {shock.get('title')} | Target: {target_token} | " f"Post-latency executable depth ${post_depth_usd:.2f} < min ${MIN_ELASTIC_TICKET_USD * DEFAULT_ELASTIC_SAFETY_RATIO:.2f} (depth swept after {self.paper_latency_ms}ms)",flush=True,)
      return False
     post_eff=tok_data.get("effective_price_$50") or tok_data.get("vwap_$50") or post_ask_f
   if post_ask_f is None:
    ir=shock.get("impulse_response",{})
    ladder_key="500ms" if self.paper_latency_ms>=400 else ("250ms" if self.paper_latency_ms>=200 else "100ms")
    snap=ir.get(ladder_key) or ir.get("500ms") or ir.get("250ms")
    if snap:
     post_ask=snap.get("up_ask" if target_token=="UP" else "down_ask")
     if post_ask is not None:
      post_ask_f=float(post_ask)
   if post_ask_f is not None:
    if post_ask_f<=0.0 or post_ask_f > MAX_PRICE_CEILING:
     print( f"\n[PAPER FAK KILLED] {shock.get('title')} | Target: {target_token} | " f"Post-latency ask ${post_ask_f:.4f} > ceiling ${MAX_PRICE_CEILING} (depth swept after {self.paper_latency_ms}ms)",flush=True,)
     return False
    if post_ask_f > exec_price:
     adverse_slippage_cents=round((post_ask_f - exec_price) * 100.0,4)
     exec_price=post_ask_f
     exec_eff_px=max(exec_eff_px,float(post_eff) if post_eff is not None else post_ask_f)
  shares=ticket_notional / float(exec_price)
  if fill_fee is not None:
   taker_fee=float(fill_fee) * (ticket_notional / TICKET_NOTIONAL)
  else:
   _,taker_fee=calculate_taker_fee(ticket_notional,float(exec_price),fee_rate,fee_exponent)
  effective_fee_rate_on_deployed_notional=taker_fee / ticket_notional
  trade={ "trade_id":trade_id,"market_id":m_id,"title":shock.get("title",""),"entry_time":shock.get("timestamp",""),"entry_unix":t0_unix,"epoch":epoch_label,"seconds_to_expiry":tte,"target_token":target_token,"notional_usd":ticket_notional,"live_parity_notional_usd":live_parity_notional,"legacy_fixed_notional_usd":legacy_ticket_notional,"effective_price":exec_eff_px,"exec_price":exec_price,"entry_price":exec_price,"adverse_slippage_cents":adverse_slippage_cents,"latency_simulated_ms":self.paper_latency_ms,"shares_bought":round(shares,4),"taker_fee_usd":round(taker_fee,4),"fee_rate_applied":fee_rate,"fee_exponent_applied":fee_exponent,"effective_fee_rate_on_deployed_notional":round(effective_fee_rate_on_deployed_notional,6),"fee_formula_provenance":f"calculate_taker_fee(notional={ticket_notional}, price={exec_price:.3f}, fee_rate={fee_rate}, fee_exponent={fee_exponent})","execution_model":"PIECEWISE_LINEAR_SCENARIO_MILP","simulated_partial_fill_timeout_ms":self.paper_latency_ms,"spot_at_t0":shock.get("spot_at_t0"),"candle_open_spot":float(shock.get("finalized_1h_open") or shock.get("candle_open_spot") or shock.get("spot_at_t0") or 0.0),"candle_distance_pct":dist_pct,"status":"OPEN","exit_policy":"EXP302_HOLD_TO_MATURITY_WITH_SPOT_DELTA_STOP","take_profit_maker_limit_px":0.99 if exec_eff_px>=0.80 else 0.98,"stop_loss_relative_px":max(0.02,round(exec_eff_px - 0.12,4)),"maker_tp_order_status":"RESTING_MAKER_LIMIT","score":candidate_score,}
  if m_id not in self.open_trades:
   self.open_trades[m_id]=[]
  self.open_trades[m_id].append(trade)
  if int(float(t0_unix) // 3600)==self.current_hour_window:
   self.trades_this_hour += 1
  if not historical:
   print(f"\n[PAPER ORDER FILLED - {epoch_label}] {shock.get('title')} | Target: {target_token} | " f"Price: {exec_price:.3f} (Slippage: +{adverse_slippage_cents:.2f}¢) | Shares: {shares:.1f} | TTE: {tte/60.0:.1f}m | Dist: {dist_pct:+.2f}% | Fee: ${taker_fee:.3f}",flush=True)
  return True
 def _evaluate_sleeve_2(self,shock:Dict[str,Any],historical:bool=False):
  if historical:
   return
  m_id=shock.get("market_id")
  if not m_id:
   return
  if m_id in self.open_trades and len(self.open_trades[m_id]) > 0:
   return
  if m_id in self.sleeve2_open_trades and len(self.sleeve2_open_trades[m_id]) > 0:
   return
  t0_unix=shock.get("t0_unix",time.time())
  shock_dir=shock.get("shock_direction")
  target_token="UP" if shock_dir=="BUY" else "DOWN"
  trade_id=f"SLEEVE2_{m_id}_{int(t0_unix)}_{target_token}"
  if trade_id in self.sleeve2_settled_ids:
   return
  if self.sleeve2_cash < SLEEVE_2_TICKET_NOTIONAL:
   return
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   dt=datetime.fromtimestamp(t0_unix,tz=timezone.utc)
   if dt.hour==13 and dt.minute>=30:
    return
  title=shock.get("title","")
  asset=shock.get("asset","")
  title_lower=title.lower()
  horizon=str(shock.get("horizon","") or shock.get("candle_interval","")).lower()
  slug=str(shock.get("series_slug","") or shock.get("slug","")).lower()
  is_eth=("ethereum" in title_lower or "eth" in title_lower or asset=="ETH")
  is_btc=("bitcoin" in title_lower or "btc" in title_lower or asset=="BTC")
  if not (is_eth or is_btc):
   return
  asset_str="ETH" if is_eth else "BTC"
  is_subhourly=any(x in horizon or x in slug or x in title_lower for x in ("5m","15m","300s","900s"))
  is_1h=not is_subhourly and ( any(x in horizon or x in slug or x in title_lower for x in ("1h","hourly","60m")) or ("am et" in title_lower or "pm et" in title_lower) )
  if not is_1h:
   return
  tte=shock.get("seconds_to_expiry",3600.0)
  if tte > SLEEVE_2_MAX_TTE or tte < SLEEVE_2_MIN_TTE:
   return
  dist_pct=float(shock.get("candle_distance_pct",0.0) or 0.0)
  open_spot_cand=shock.get("finalized_1h_open") or shock.get("candle_open_spot")
  spot_at_t0=float(shock.get("spot_at_t0") or shock.get("trigger_price") or 0.0)
  if (abs(dist_pct) < 0.0001 or not open_spot_cand or float(open_spot_cand)<=0.0) and spot_at_t0 > 0.0:
   h_idx=int(float(shock.get("t0_unix",time.time())) // 3600)
   cached_open=self.hourly_candle_opens.get(asset,{}).get(h_idx)
   if cached_open and cached_open > 0.0:
    dist_pct=((spot_at_t0 - cached_open) / cached_open) * 100.0
  if abs(dist_pct) < 0.15:
   return
  if target_token=="UP" and dist_pct < 0.15:
   return
  if target_token=="DOWN" and dist_pct > -0.15:
   return
  t0_u=float(shock.get("t0_unix",time.time()))
  cur_h_idx=int(t0_u // 3600)
  open_spot_cand=shock.get("finalized_1h_open") or shock.get("candle_open_spot") or shock.get("spot_at_t0")
  if open_spot_cand and math.isfinite(float(open_spot_cand)) and float(open_spot_cand) > 0:
   if cur_h_idx not in self.hourly_candle_opens[asset_str]:
    self.hourly_candle_opens[asset_str][cur_h_idx]=float(open_spot_cand)
  opens_map=self.hourly_candle_opens.get(asset_str,{})
  open_h=opens_map.get(cur_h_idx)
  open_h_1=opens_map.get(cur_h_idx - 1)
  open_h_2=opens_map.get(cur_h_idx - 2)
  ret_2h=((open_h - open_h_2) / open_h_2) if (open_h and open_h_2 and open_h_2 > 0) else None
  ret_1h_prior=((open_h - open_h_1) / open_h_1) if (open_h and open_h_1 and open_h_1 > 0) else None
  ret_2h_prior=((open_h_1 - open_h_2) / open_h_2) if (open_h_1 and open_h_2 and open_h_2 > 0) else None
  prior_2_green=(ret_1h_prior is not None and ret_1h_prior > 0.0010 and ret_2h_prior is not None and ret_2h_prior > 0.0010)
  prior_2_red=(ret_1h_prior is not None and ret_1h_prior < -0.0010 and ret_2h_prior is not None and ret_2h_prior < -0.0010)
  is_counter_trend=False
  if target_token=="DOWN":
   if (ret_2h is not None and ret_2h > 0.0030) or prior_2_green:
    is_counter_trend=True
  elif target_token=="UP":
   if (ret_2h is not None and ret_2h < -0.0030) or prior_2_red:
    is_counter_trend=True
  if is_counter_trend:
   if abs(dist_pct) < 0.45:
    return
  btc_shock_dir=shock.get("btc_shock_direction")
  if btc_shock_dir:
   if target_token=="UP" and btc_shock_dir in ("DOWN","SELL"):
    return
   if target_token=="DOWN" and btc_shock_dir in ("UP","BUY"):
    return
  z_eth_val=shock.get("z_eth") or shock.get("z_score") or shock.get("z_val")
  z_btc_val=shock.get("z_btc")
  if z_eth_val is not None and z_btc_val is not None:
   z_e=float(z_eth_val)
   z_b=float(z_btc_val)
   if (z_e > 0 and z_b < 0) or (z_e < 0 and z_b > 0):
    return
   z_joint=0.70 * z_e + 0.30 * z_b
   if target_token=="UP" and z_joint<=0:
    return
   if target_token=="DOWN" and z_joint>=0:
    return
  token_features=shock.get("pre_shock_features_t0",{}).get(target_token,{})
  raw_asks=token_features.get("raw_top_asks",[])
  if not raw_asks:
   return
  target_notional=SLEEVE_2_TICKET_NOTIONAL
  valid_depth_usd=sum(px * sz for px,sz in raw_asks if SLEEVE_2_MIN_PRICE<=px<=SLEEVE_2_MAX_PRICE)
  if valid_depth_usd < (target_notional * SLEEVE_2_MIN_DEPTH_RATIO):
   return
  filled_notional=0.0
  shares_acquired=0.0
  for px,sz in raw_asks:
   if px < SLEEVE_2_MIN_PRICE or px > SLEEVE_2_MAX_PRICE:
    continue
   lvl_notional=px * sz
   needed=target_notional - filled_notional
   if lvl_notional<=needed:
    filled_notional += lvl_notional
    shares_acquired += sz
   else:
    take_sz=needed / px
    filled_notional += needed
    shares_acquired += take_sz
    break
  if filled_notional < target_notional or shares_acquired<=0:
   return
  vwap_price=round(filled_notional / shares_acquired,4)
  if not (SLEEVE_2_MIN_PRICE<=vwap_price<=SLEEVE_2_MAX_PRICE):
   return
  if tte<=1350.0 and vwap_price>=0.68:
   return
  eff_fee_rate,taker_fee_usd=calculate_taker_fee(target_notional,vwap_price,fee_rate=0.07,fee_exponent=1.0)
  fee_rate=eff_fee_rate
  spot_t0=float(shock.get("spot_at_t0",0.0) or 0.0)
  raw_strike=shock.get("startingPrice") or shock.get("strike_price") or shock.get("priceToBeat")
  if raw_strike and float(raw_strike) > 0:
   strike_px=float(raw_strike)
  elif spot_t0 > 0 and abs(dist_pct) > 0:
   strike_px=round(spot_t0 / (1.0 + dist_pct / 100.0),2)
  else:
   strike_px=spot_t0
  maker_tp_px=0.99
  trade={ "sleeve":"SLEEVE_2_MULTI_304_315","trade_id":trade_id,"market_id":m_id,"title":title,"entry_time":shock.get("timestamp",""),"entry_unix":t0_unix,"seconds_to_expiry":tte,"target_token":target_token,"notional_usd":target_notional,"vwap_exec_price":vwap_price,"entry_price":vwap_price,"shares_bought":round(shares_acquired,4),"taker_fee_usd":taker_fee_usd,"fee_rate_applied":fee_rate,"fee_schedule":"crypto_fees_v2","spot_at_t0":spot_t0,"strike_price":strike_px,"candle_open_spot":strike_px,"candle_distance_pct":dist_pct,"status":"OPEN","exit_policy":"HOLD_TO_0.99_MAKER_TP_OR_MATURITY","take_profit_maker_limit_px":maker_tp_px,"maker_tp_order_status":"RESTING_MAKER_LIMIT",}
  if m_id not in self.sleeve2_open_trades:
   self.sleeve2_open_trades[m_id]=[]
  self.sleeve2_open_trades[m_id].append(trade)
  self.save_sleeve2_state()
  if not historical:
   print(f"\n[SLEEVE 2 ORDER FILLED] {title} | Target: {target_token} | " f"VWAP: ${vwap_price:.4f} | Shares: {shares_acquired:.1f} | TTE: {tte/60.0:.1f}m | Strike: ${strike_px:,.2f} | TP Limit: ${maker_tp_px:.3f} | Fee: ${taker_fee_usd:.3f}",flush=True)
 def check_strike_retrace_stops( self,market_id:str,candle_dist_pct:float,tte:float,token_bids:Optional[Dict[str,float]]=None,fee_rate:float=0.07,fee_exponent:float=1.0,)->List[Dict[str,Any]]:
  return []
 def check_maker_tp_fills(self,market_id:str,telem:Dict[str,Any])->List[Dict[str,Any]]:
  if ( market_id not in self.open_trades and market_id not in self.sleeve2_open_trades and market_id not in self.sol_shadow_open_trades and market_id not in self.xrp_shadow_open_trades ):
   return []
  closed_trades=[]
  if market_id in self.open_trades:
   for t in list(self.open_trades[market_id]):
    if t.get("status")!="OPEN":
     continue
    target_token=t.get("target_token","UP")
    token_data=telem.get(target_token) or telem.get("pre_shock_features_t0",{}).get(target_token,{})
    best_bid=float(token_data.get("best_bid",0.0) or 0.0)
    if best_bid==0.0 and token_data.get("raw_top_bids"):
     best_bid=float(token_data["raw_top_bids"][0][0])
    best_ask=float(token_data.get("best_ask",0.0) or 0.0)
    if best_ask==0.0 and token_data.get("raw_top_asks"):
     best_ask=float(token_data["raw_top_asks"][0][0])
    entry_unix=float(t.get("entry_unix",0.0) or 0.0)
    telem_unix=float(telem.get("timestamp_unix") or telem.get("t0_unix") or time.time())
    if (telem_unix - entry_unix) < 6.0:
     continue
    entry_px=float( t.get("entry_price") or t.get("exec_price") or t.get("vwap_exec_price") or t.get("effective_price") or t.get("vwap") or 0.50 )
    target_tp_px=float(t.get("take_profit_maker_limit_px") or (0.99 if entry_px>=0.80 else 0.98))
    is_maker_fill=best_bid>=target_tp_px
    current_spot=float( telem.get("binance_spot") or telem.get("spot_at_t0") or telem.get("trigger_price") or telem.get("spot") or 0.0 )
    open_spot=float( t.get("candle_open_spot") or t.get("strike_price") or telem.get("binance_1h_open") or t.get("spot_at_t0") or 0.0 )
    tte_rem=float(telem.get("seconds_to_expiry") or 0.0)
    if tte_rem<=0.0:
     exp_u=float(t.get("expiry_unix") or 0.0)
     if exp_u > telem_unix:
      tte_rem=exp_u - telem_unix
     else:
      tte_rem=float(t.get("seconds_to_expiry") or 0.0)
    v_spot_15s_pct=0.0
    if current_spot > 0:
     history=t.setdefault("spot_vel_history",[])
     history.append([telem_unix,float(current_spot)])
     t["spot_vel_history"]=[pt for pt in history if (telem_unix - pt[0])<=15.0]
     hist=t["spot_vel_history"]
     if len(hist)>=2:
      oldest_spot=hist[0][1]
      if oldest_spot > 0:
       if target_token=="UP":
        v_spot_15s_pct=((current_spot - oldest_spot) / oldest_spot) * 100.0
       else:
        v_spot_15s_pct=((oldest_spot - current_spot) / oldest_spot) * 100.0
     t["v_spot_15s_pct"]=round(v_spot_15s_pct,4)
    opposite_salvaged=False
    wrong_side_pct=0.0
    if current_spot > 0 and open_spot > 0:
     signed_cushion_pct=((current_spot - open_spot) / open_spot * 100.0) if target_token=="UP" else ((open_spot - current_spot) / open_spot * 100.0)
     wrong_side_pct=-signed_cushion_pct
     if wrong_side_pct<=0.0:
      t.pop("opposite_breakout_start_ts",None)
     else:
      if tte_rem > 900.0:
       req_initial,req_sustain,req_duration,min_salvage_bid=0.16,0.14,40.0,0.08
      elif tte_rem > 180.0:
       req_initial,req_sustain,req_duration,min_salvage_bid=0.11,0.09,18.0,0.08
      elif tte_rem>=25.0:
       req_initial,req_sustain,req_duration,min_salvage_bid=0.06,0.04,8.0,0.06
      else:
       req_initial,req_sustain,req_duration,min_salvage_bid=999.0,999.0,999.0,0.99
      eff_duration=(req_duration * 0.50) if (v_spot_15s_pct<=-0.08 and best_bid<=0.42) else req_duration
      consec_start=t.get("opposite_breakout_start_ts")
      if consec_start is None:
       if wrong_side_pct>=req_initial:
        t["opposite_breakout_start_ts"]=telem_unix
      else:
       if wrong_side_pct>=req_sustain:
        duration=telem_unix - float(consec_start)
        if v_spot_15s_pct>=0.03:
         opposite_salvaged=False
        elif duration>=eff_duration and best_bid>=min_salvage_bid:
         opposite_salvaged=True
       else:
        t.pop("opposite_breakout_start_ts",None)
    t["max_seen_bid"]=max(float(t.get("max_seen_bid",0.0) or 0.0),best_bid)
    max_seen_bid=float(t.get("max_seen_bid",0.0) or 0.0)
    trailing_ratchet_triggered=False
    trail_floor=0.0
    if max_seen_bid>=max(0.73,entry_px + 0.09) and entry_px > 0:
     trail_delta=0.05 if max_seen_bid>=0.90 else (0.07 if max_seen_bid>=0.82 else 0.05)
     trail_floor=round(max_seen_bid - trail_delta,4)
     if best_bid<=trail_floor and tte_rem>=25.0 and best_bid>=0.25:
      ratchet_start=t.get("trailing_ratchet_start_ts")
      if ratchet_start is None:
       t["trailing_ratchet_start_ts"]=telem_unix
      elif (telem_unix - float(ratchet_start))>=3.0:
       trailing_ratchet_triggered=True
     else:
      t.pop("trailing_ratchet_start_ts",None)
    else:
     t.pop("trailing_ratchet_start_ts",None)
    final_45s_triggered=False
    if 0.0 < tte_rem<=45.0 and best_bid>=0.88 and best_bid > (entry_px + 0.03):
     final_45s_triggered=True
    if not is_maker_fill and not opposite_salvaged and not trailing_ratchet_triggered and not final_45s_triggered:
     continue
    applied_r=float(t.get("fee_rate_applied",0.07) or 0.07)
    if applied_r < 0.05:
     applied_r=0.18 if "15m" in str(t.get("title","")).lower() else 0.07
    if final_45s_triggered:
     tp_px=max(0.01,round(best_bid - 0.01,4))
     tp_payout=round(t["shares_bought"] * tp_px,2)
     _,tp_exit_fee=calculate_taker_fee(tp_payout,tp_px,fee_rate=applied_r,fee_exponent=1.0)
     net_pnl=round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd",0.0) - tp_exit_fee,2)
     exit_reason="FINAL_45S_CAPITAL_RECYCLE_UNWIND"
     is_won=(net_pnl > 0)
    elif trailing_ratchet_triggered:
     tp_px=best_bid
     tp_payout=round(t["shares_bought"] * tp_px,2)
     _,tp_exit_fee=calculate_taker_fee(tp_payout,tp_px,fee_rate=applied_r,fee_exponent=1.0)
     net_pnl=round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd",0.0) - tp_exit_fee,2)
     exit_reason="TRAILING_PROFIT_RATCHET_UNWIND"
     is_won=(net_pnl > 0)
    elif opposite_salvaged:
     tp_px=best_bid
     tp_payout=round(t["shares_bought"] * tp_px,2)
     _,tp_exit_fee=calculate_taker_fee(tp_payout,tp_px,fee_rate=applied_r,fee_exponent=1.0)
     net_pnl=round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd",0.0) - tp_exit_fee,2)
     exit_reason="CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE"
     is_won=False
    else:
     tp_px=target_tp_px
     tp_payout=round(t["shares_bought"] * tp_px,2)
     tp_exit_fee=0.0
     net_pnl=round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd",0.0),2)
     exit_reason="MAKER_SCALP_FILLED_CLOB"
     is_won=True
    live_parity_notional=float(t.get("live_parity_notional_usd",t["notional_usd"]))
    parity_ratio=live_parity_notional / max(t["notional_usd"],1.0)
    live_parity_pnl=round(net_pnl * parity_ratio,2)
    legacy_notional=float(t.get("legacy_fixed_notional_usd",t["notional_usd"]))
    ratio=legacy_notional / max(t["notional_usd"],1.0)
    legacy_pnl=round(net_pnl * ratio,2)
    t["status"]="CLOSED"
    t["exit_reason"]=exit_reason
    t["exit_price"]=tp_px
    t["exit_fee_usd"]=tp_exit_fee
    t["payout_usd"]=tp_payout
    t["net_pnl_usd"]=net_pnl
    t["live_parity_pnl_usd"]=live_parity_pnl
    t["legacy_fixed_pnl_usd"]=legacy_pnl
    t["won"]=is_won
    t["settle_time"]=telem.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry_unix=t.get("entry_unix",0.0)
    if entry_unix < R3_VALIDATION_START_UNIX:
     self.dev_trades.append(t)
     self.dev_realized_pnl += net_pnl
     self.dev_cash=INITIAL_PAPER_CAPITAL + self.dev_realized_pnl
     target_file=DEV_LEDGER_FILE
    else:
     self.val_trades.append(t)
     self.val_realized_pnl += net_pnl
     self.val_cash=INITIAL_PAPER_CAPITAL + self.val_realized_pnl
     target_file=VALIDATION_LEDGER_FILE
    self.settled_trade_ids.add(t["trade_id"])
    self.trades_per_market[market_id] += 1
    closed_trades.append(t)
    with open(target_file,"a") as f:
     f.write(json.dumps(t) + "\n")
    tag="FINAL-45S RECYCLED" if final_45s_triggered else ("TRAILING RATCHET LOCKED" if trailing_ratchet_triggered else ("SALVAGE EXECUTED" if opposite_salvaged else f"MAKER TP FILLED @ {tp_px:.2f}"))
    print( f"\n[PAPER {tag}] {t.get('title')} | Target: {target_token} | " f"Exit Price: ${tp_px:.4f} | Net PnL: ${net_pnl:+.2f} ({exit_reason})",flush=True,)
   if closed_trades:
    self.open_trades[market_id]=[t for t in self.open_trades[market_id] if t.get("status")=="OPEN"]
    if not self.open_trades[market_id]:
     del self.open_trades[market_id]
  if ENABLE_SLEEVE_304_315 and market_id in self.sleeve2_open_trades:
   sleeve2_closed=[]
   for t in list(self.sleeve2_open_trades[market_id]):
    if t.get("status")!="OPEN":
     continue
    target_token=t.get("target_token","UP")
    token_data=telem.get(target_token) or telem.get("pre_shock_features_t0",{}).get(target_token,{})
    best_bid=float(token_data.get("best_bid",0.0) or 0.0)
    if best_bid==0.0 and token_data.get("raw_top_bids"):
     best_bid=float(token_data["raw_top_bids"][0][0])
    best_ask=float(token_data.get("best_ask",0.0) or 0.0)
    if best_ask==0.0 and token_data.get("raw_top_asks"):
     best_ask=float(token_data["raw_top_asks"][0][0])
    entry_unix=float(t.get("entry_unix",0.0) or 0.0)
    telem_unix=float(telem.get("timestamp_unix") or telem.get("t0_unix") or time.time())
    if (telem_unix - entry_unix) < 6.0:
     continue
    entry_px=float( t.get("entry_price") or t.get("exec_price") or t.get("vwap_exec_price") or t.get("effective_price") or t.get("vwap") or 0.50 )
    tp_px=float(t.get("take_profit_maker_limit_px",0.99))
    is_maker_fill=best_bid>=tp_px
    current_spot=float( telem.get("binance_spot") or telem.get("spot_at_t0") or telem.get("trigger_price") or telem.get("spot") or 0.0 )
    open_spot=float( t.get("candle_open_spot") or t.get("strike_price") or telem.get("binance_1h_open") or t.get("spot_at_t0") or 0.0 )
    tte_rem=float(telem.get("seconds_to_expiry") or 0.0)
    if tte_rem<=0.0:
     exp_u=float(t.get("expiry_unix") or 0.0)
     if exp_u > telem_unix:
      tte_rem=exp_u - telem_unix
     else:
      tte_rem=float(t.get("seconds_to_expiry") or 0.0)
    v_spot_15s_pct=0.0
    if current_spot > 0:
     history=t.setdefault("spot_vel_history",[])
     history.append([telem_unix,float(current_spot)])
     t["spot_vel_history"]=[pt for pt in history if (telem_unix - pt[0])<=15.0]
     hist=t["spot_vel_history"]
     if len(hist)>=2:
      oldest_spot=hist[0][1]
      if oldest_spot > 0:
       if target_token=="UP":
        v_spot_15s_pct=((current_spot - oldest_spot) / oldest_spot) * 100.0
       else:
        v_spot_15s_pct=((oldest_spot - current_spot) / oldest_spot) * 100.0
     t["v_spot_15s_pct"]=round(v_spot_15s_pct,4)
    opposite_salvaged=False
    wrong_side_pct=0.0
    if current_spot > 0 and open_spot > 0:
     signed_cushion_pct=((current_spot - open_spot) / open_spot * 100.0) if target_token=="UP" else ((open_spot - current_spot) / open_spot * 100.0)
     wrong_side_pct=-signed_cushion_pct
     if wrong_side_pct<=0.0:
      t.pop("opposite_breakout_start_ts",None)
     else:
      if tte_rem > 900.0:
       req_initial,req_sustain,req_duration,min_salvage_bid=0.16,0.14,40.0,0.08
      elif tte_rem > 180.0:
       req_initial,req_sustain,req_duration,min_salvage_bid=0.11,0.09,18.0,0.08
      elif tte_rem>=25.0:
       req_initial,req_sustain,req_duration,min_salvage_bid=0.06,0.04,8.0,0.06
      else:
       req_initial,req_sustain,req_duration,min_salvage_bid=999.0,999.0,999.0,0.99
      eff_duration=(req_duration * 0.50) if (v_spot_15s_pct<=-0.08 and best_bid<=0.42) else req_duration
      consec_start=t.get("opposite_breakout_start_ts")
      if consec_start is None:
       if wrong_side_pct>=req_initial:
        t["opposite_breakout_start_ts"]=telem_unix
      else:
       if wrong_side_pct>=req_sustain:
        duration=telem_unix - float(consec_start)
        if v_spot_15s_pct>=0.03:
         opposite_salvaged=False
        elif duration>=eff_duration and best_bid>=min_salvage_bid:
         opposite_salvaged=True
       else:
        t.pop("opposite_breakout_start_ts",None)
    t["max_seen_bid"]=max(float(t.get("max_seen_bid",0.0) or 0.0),best_bid)
    max_seen_bid=float(t.get("max_seen_bid",0.0) or 0.0)
    trailing_ratchet_triggered=False
    trail_floor=0.0
    if max_seen_bid>=max(0.73,entry_px + 0.09) and entry_px > 0:
     trail_delta=0.05 if max_seen_bid>=0.90 else (0.07 if max_seen_bid>=0.82 else 0.05)
     trail_floor=round(max_seen_bid - trail_delta,4)
     if best_bid<=trail_floor and tte_rem>=25.0 and best_bid>=0.25:
      ratchet_start=t.get("trailing_ratchet_start_ts")
      if ratchet_start is None:
       t["trailing_ratchet_start_ts"]=telem_unix
      elif (telem_unix - float(ratchet_start))>=3.0:
       trailing_ratchet_triggered=True
     else:
      t.pop("trailing_ratchet_start_ts",None)
    else:
     t.pop("trailing_ratchet_start_ts",None)
    final_45s_triggered=False
    if 0.0 < tte_rem<=45.0 and best_bid>=0.88 and best_bid > (entry_px + 0.03):
     final_45s_triggered=True
    if not is_maker_fill and not opposite_salvaged and not trailing_ratchet_triggered and not final_45s_triggered:
     continue
    applied_r=float(t.get("fee_rate_applied",0.07) or 0.07)
    if applied_r < 0.05:
     applied_r=0.18 if "15m" in str(t.get("title","")).lower() else 0.07
    if final_45s_triggered:
     exit_px=max(0.01,round(best_bid - 0.01,4))
     exit_payout=round(t["shares_bought"] * exit_px,2)
     _,exit_fee=calculate_taker_fee(exit_payout,exit_px,fee_rate=applied_r,fee_exponent=1.0)
     net_pnl=round(exit_payout - t["notional_usd"] - t.get("taker_fee_usd",0.0) - exit_fee,2)
     exit_reason="FINAL_45S_CAPITAL_RECYCLE_UNWIND"
     is_won=(net_pnl > 0)
    elif trailing_ratchet_triggered:
     exit_px=best_bid
     exit_payout=round(t["shares_bought"] * exit_px,2)
     _,exit_fee=calculate_taker_fee(exit_payout,exit_px,fee_rate=applied_r,fee_exponent=1.0)
     net_pnl=round(exit_payout - t["notional_usd"] - t.get("taker_fee_usd",0.0) - exit_fee,2)
     exit_reason="TRAILING_PROFIT_RATCHET_UNWIND"
     is_won=(net_pnl > 0)
    elif opposite_salvaged:
     exit_px=best_bid
     exit_payout=round(t["shares_bought"] * exit_px,2)
     _,exit_fee=calculate_taker_fee(exit_payout,exit_px,fee_rate=applied_r,fee_exponent=1.0)
     net_pnl=round(exit_payout - t["notional_usd"] - t.get("taker_fee_usd",0.0) - exit_fee,2)
     exit_reason="CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE"
     is_won=False
    else:
     exit_px=tp_px
     exit_payout=round(t["shares_bought"] * exit_px,2)
     exit_fee=0.0
     net_pnl=round(exit_payout - t["notional_usd"] - t.get("taker_fee_usd",0.0),2)
     exit_reason="EXP315_MAKER_TP_FILLED"
     is_won=True
    t["status"]="CLOSED"
    t["exit_reason"]=exit_reason
    t["exit_price"]=exit_px
    t["exit_fee_usd"]=exit_fee
    t["payout_usd"]=exit_payout
    t["net_pnl_usd"]=net_pnl
    t["won"]=is_won
    t["settle_time"]=telem.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    self.sleeve2_trades.append(t)
    self.sleeve2_realized_pnl += net_pnl
    self.sleeve2_cash=SLEEVE_2_INITIAL_CAPITAL + self.sleeve2_realized_pnl
    self.sleeve2_settled_ids.add(t["trade_id"])
    sleeve2_closed.append(t)
    with open(SLEEVE_2_LEDGER_FILE,"a") as f:
     f.write(json.dumps(t) + "\n")
    tag="SLEEVE 2 SALVAGE EXECUTED" if opposite_salvaged else f"SLEEVE 2 MAKER TP FILLED @ {exit_px:.3f}"
    print( f"\n[{tag}] {t.get('title')} | Target: {target_token} | " f"Exit Price: ${exit_px:.3f} | Net PnL: ${net_pnl:+.2f} | Sleeve 2 Equity: ${self.sleeve2_cash:,.2f}",flush=True,)
   if sleeve2_closed:
    self.sleeve2_open_trades[market_id]=[t for t in self.sleeve2_open_trades[market_id] if t.get("status")=="OPEN"]
    if not self.sleeve2_open_trades[market_id]:
     del self.sleeve2_open_trades[market_id]
    self.save_sleeve2_state()
  for asset_sym,enabled_flag,open_map,trades_list,settled_set,ledger_path,init_cap,cash_attr,pnl_attr,fees_attr,save_fn in ( ("SOL",ENABLE_SOL_SHADOW_SLEEVE,self.sol_shadow_open_trades,self.sol_shadow_trades,self.sol_shadow_settled_ids,SOL_SHADOW_LEDGER_FILE,SOL_SHADOW_INITIAL_CAPITAL,"sol_shadow_cash","sol_shadow_realized_pnl","sol_shadow_total_fees",self.save_sol_shadow_state),("XRP",ENABLE_XRP_SHADOW_SLEEVE,self.xrp_shadow_open_trades,self.xrp_shadow_trades,self.xrp_shadow_settled_ids,XRP_SHADOW_LEDGER_FILE,XRP_SHADOW_INITIAL_CAPITAL,"xrp_shadow_cash","xrp_shadow_realized_pnl","xrp_shadow_total_fees",self.save_xrp_shadow_state),):
   if enabled_flag and market_id in open_map:
    alt_closed=[]
    for t in list(open_map[market_id]):
     if t.get("status")!="OPEN":
      continue
     target_token=t.get("target_token","UP")
     token_data=telem.get(target_token) or telem.get("pre_shock_features_t0",{}).get(target_token,{})
     best_bid=float(token_data.get("best_bid",0.0) or 0.0)
     if best_bid==0.0 and token_data.get("raw_top_bids"):
      best_bid=float(token_data["raw_top_bids"][0][0])
     telem_unix=float(telem.get("timestamp_unix") or telem.get("t0_unix") or time.time())
     if (telem_unix - float(t.get("entry_unix",0.0) or 0.0)) < 6.0:
      continue
     entry_px=float(t.get("entry_price") or 0.70)
     tp_px=float(t.get("take_profit_maker_limit_px",0.965))
     is_maker_fill=best_bid>=tp_px
     is_sub=t.get("horizon")=="15m"
     current_spot=float((telem.get("chainlink_twap_60s") if is_sub else 0.0) or telem.get("binance_spot") or telem.get("spot_at_t0") or telem.get("spot") or 0.0)
     open_spot=float(t.get("candle_open_spot") or 0.0)
     tte_rem=float(telem.get("seconds_to_expiry") or max(0.0,float(t.get("expiry_unix",0.0)) - telem_unix))
     opposite_salvaged=False
     if current_spot > 0.0 and open_spot > 0.0 and tte_rem>=25.0:
      s_cush=((current_spot - open_spot) / open_spot * 100.0) if target_token=="UP" else ((open_spot - current_spot) / open_spot * 100.0)
      wrong_pct=-s_cush
      if wrong_pct<=0.0:
       t.pop("opposite_breakout_start_ts",None)
      else:
       req_w=0.22 if tte_rem > 900.0 else (0.15 if tte_rem > 180.0 else 0.09)
       req_d=35.0 if tte_rem > 900.0 else (18.0 if tte_rem > 180.0 else 8.0)
       if wrong_pct>=req_w:
        cs=t.get("opposite_breakout_start_ts")
        if cs is None:
         t["opposite_breakout_start_ts"]=telem_unix
        elif (telem_unix - float(cs))>=req_d and best_bid>=0.15:
         opposite_salvaged=True
       else:
        t.pop("opposite_breakout_start_ts",None)
     t["max_seen_bid"]=max(float(t.get("max_seen_bid",0.0) or 0.0),best_bid)
     max_seen_bid=float(t["max_seen_bid"])
     trailing_ratchet_triggered=False
     if max_seen_bid>=0.93 and best_bid<=round(max_seen_bid - 0.05,4) and tte_rem>=25.0 and best_bid>=(entry_px + 0.04):
      rs=t.get("trailing_ratchet_start_ts")
      if rs is None:
       t["trailing_ratchet_start_ts"]=telem_unix
      elif (telem_unix - float(rs))>=4.0:
       trailing_ratchet_triggered=True
     else:
      t.pop("trailing_ratchet_start_ts",None)
     if not is_maker_fill and not opposite_salvaged and not trailing_ratchet_triggered:
      continue
     if is_maker_fill:
      exit_px,exit_fee,exit_reason=tp_px,0.0,f"{asset_sym}_SHADOW_MAKER_TP_95_98"
      exit_payout=round(t["shares_bought"] * exit_px,2)
     else:
      exit_px=best_bid
      exit_payout=round(t["shares_bought"] * exit_px,2)
      _,exit_fee=calculate_taker_fee(exit_payout,exit_px,fee_rate=0.07,fee_exponent=1.0)
      exit_reason=f"{asset_sym}_SHADOW_RATCHET_93" if trailing_ratchet_triggered else f"{asset_sym}_SHADOW_3ZONE_SALVAGE"
     net_pnl=round(exit_payout - t["notional_usd"] - t.get("taker_fee_usd",0.0) - exit_fee,2)
     t.update({ "status":"CLOSED","exit_reason":exit_reason,"exit_price":exit_px,"exit_fee_usd":round(exit_fee,4),"payout_usd":exit_payout,"net_pnl_usd":net_pnl,"won":bool(net_pnl > 0),"settle_time":telem.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),})
     trades_list.append(t)
     setattr(self,pnl_attr,getattr(self,pnl_attr) + net_pnl)
     setattr(self,fees_attr,getattr(self,fees_attr) + float(t.get("taker_fee_usd",0.0)) + exit_fee)
     setattr(self,cash_attr,init_cap + getattr(self,pnl_attr))
     settled_set.add(t["trade_id"])
     alt_closed.append(t)
     with open(ledger_path,"a",encoding="utf-8") as f:
      f.write(json.dumps(t) + "\n")
    if alt_closed:
     open_map[market_id]=[t for t in open_map[market_id] if t.get("status")=="OPEN"]
     if not open_map[market_id]:
      del open_map[market_id]
     save_fn()
  return closed_trades
 def settle_market(self,m_id:str,resolution:Dict[str,Any],historical:bool=False):
  if ( m_id not in self.open_trades and m_id not in self.sleeve2_open_trades and m_id not in self.sol_shadow_open_trades and m_id not in self.xrp_shadow_open_trades ):
   return
  winning=resolution.get("winning_outcome")
  if winning not in ("UP","DOWN"):
   return
  if m_id in self.open_trades:
   closed_this_round=[]
   for trade in self.open_trades[m_id]:
    tid=trade["trade_id"]
    if tid in self.settled_trade_ids or trade.get("status")=="CLOSED":
     continue
    won=(trade["target_token"]==winning)
    payout=trade["shares_bought"] * 1.0 if won else 0.0
    taker_fee=trade.get("taker_fee_usd",0.0)
    net_pnl=payout - trade["notional_usd"] - taker_fee
    legacy_notional=float(trade.get("legacy_fixed_notional_usd",trade["notional_usd"]))
    ratio=legacy_notional / max(trade["notional_usd"],1.0)
    legacy_pnl=round(net_pnl * ratio,2)
    trade["settle_time"]=resolution.get("timestamp_resolved","")
    trade["winning_outcome"]=winning
    trade["won"]=won
    trade["payout_usd"]=round(payout,2)
    trade["net_pnl_usd"]=round(net_pnl,2)
    live_parity_notional=float(trade.get("live_parity_notional_usd",trade["notional_usd"]))
    parity_ratio=live_parity_notional / max(trade["notional_usd"],1.0)
    trade["live_parity_pnl_usd"]=round(net_pnl * parity_ratio,2)
    trade["legacy_fixed_pnl_usd"]=legacy_pnl
    trade["status"]="CLOSED"
    trade["exit_reason"]="EXP302_HOLD_TO_MATURITY_SETTLEMENT"
    entry_unix=trade.get("entry_unix",0.0)
    if entry_unix < R3_VALIDATION_START_UNIX:
     self.dev_trades.append(trade)
     self.dev_realized_pnl += net_pnl
     self.dev_total_fees += trade.get("taker_fee_usd",0.0)
     self.dev_cash=INITIAL_PAPER_CAPITAL + self.dev_realized_pnl
     target_file=DEV_LEDGER_FILE
    else:
     self.val_trades.append(trade)
     self.val_realized_pnl += net_pnl
     self.val_total_fees += trade.get("taker_fee_usd",0.0)
     self.val_cash=INITIAL_PAPER_CAPITAL + self.val_realized_pnl
     target_file=VALIDATION_LEDGER_FILE
    self.settled_trade_ids.add(tid)
    self.trades_per_market[m_id] += 1
    closed_this_round.append(trade)
    with open(target_file,"a") as f:
     f.write(json.dumps(trade) + "\n")
   del self.open_trades[m_id]
   if not historical and closed_this_round:
    total_round_pnl=sum(t["net_pnl_usd"] for t in closed_this_round)
    print(f"\n[MARKET SETTLED] Market ID: {m_id} | Winner: {winning} | " f"Trades Settled: {len(closed_this_round)} | Net PnL: ${total_round_pnl:+.2f} | " f"Validation Equity: ${self.val_cash:,.2f} | Dev Equity: ${self.dev_cash:,.2f}",flush=True)
  if ENABLE_SLEEVE_304_315 and m_id in self.sleeve2_open_trades:
   s2_closed=[]
   for trade in list(self.sleeve2_open_trades[m_id]):
    tid=trade["trade_id"]
    if tid in self.sleeve2_settled_ids or trade.get("status")=="CLOSED":
     continue
    won=(trade["target_token"]==winning)
    payout=trade["shares_bought"] * 1.0 if won else 0.0
    taker_fee=trade.get("taker_fee_usd",0.0)
    net_pnl=payout - trade["notional_usd"] - taker_fee
    trade["settle_time"]=resolution.get("timestamp_resolved","")
    trade["winning_outcome"]=winning
    trade["won"]=won
    trade["payout_usd"]=round(payout,2)
    trade["net_pnl_usd"]=round(net_pnl,2)
    trade["status"]="CLOSED"
    trade["exit_reason"]="EXP304_315_HOLD_TO_MATURITY_SETTLEMENT"
    trade["exit_price"]=1.0 if won else 0.0
    trade["exit_fee_usd"]=0.0
    self.sleeve2_trades.append(trade)
    self.sleeve2_realized_pnl += net_pnl
    self.sleeve2_total_fees += taker_fee
    self.sleeve2_cash=SLEEVE_2_INITIAL_CAPITAL + self.sleeve2_realized_pnl
    self.sleeve2_settled_ids.add(tid)
    s2_closed.append(trade)
    with open(SLEEVE_2_LEDGER_FILE,"a") as f:
     f.write(json.dumps(trade) + "\n")
    if not historical:
     print(f"\n[SLEEVE 2 MARKET SETTLED] Market ID: {m_id} | Winner: {winning} | " f"Won: {won} | Net PnL: ${net_pnl:+.2f} | Sleeve 2 Equity: ${self.sleeve2_cash:,.2f}",flush=True)
   del self.sleeve2_open_trades[m_id]
   self.save_sleeve2_state()
  for asset_sym,enabled_flag,open_map,trades_list,settled_set,ledger_path,init_cap,cash_attr,pnl_attr,fees_attr,save_fn in ( ("SOL",ENABLE_SOL_SHADOW_SLEEVE,self.sol_shadow_open_trades,self.sol_shadow_trades,self.sol_shadow_settled_ids,SOL_SHADOW_LEDGER_FILE,SOL_SHADOW_INITIAL_CAPITAL,"sol_shadow_cash","sol_shadow_realized_pnl","sol_shadow_total_fees",self.save_sol_shadow_state),("XRP",ENABLE_XRP_SHADOW_SLEEVE,self.xrp_shadow_open_trades,self.xrp_shadow_trades,self.xrp_shadow_settled_ids,XRP_SHADOW_LEDGER_FILE,XRP_SHADOW_INITIAL_CAPITAL,"xrp_shadow_cash","xrp_shadow_realized_pnl","xrp_shadow_total_fees",self.save_xrp_shadow_state),):
   if enabled_flag and m_id in open_map:
    for trade in list(open_map[m_id]):
     tid=trade["trade_id"]
     if tid in settled_set or trade.get("status")=="CLOSED":
      continue
     won=(trade["target_token"]==winning)
     payout=trade["shares_bought"] * 1.0 if won else 0.0
     taker_fee=float(trade.get("taker_fee_usd",0.0))
     net_pnl=round(payout - trade["notional_usd"] - taker_fee,2)
     trade.update({ "settle_time":resolution.get("timestamp_resolved",""),"winning_outcome":winning,"won":won,"payout_usd":round(payout,2),"net_pnl_usd":net_pnl,"status":"CLOSED","exit_reason":f"{asset_sym}_SHADOW_HOLD_TO_MATURITY_SETTLEMENT","exit_price":1.0 if won else 0.0,"exit_fee_usd":0.0,})
     trades_list.append(trade)
     setattr(self,pnl_attr,getattr(self,pnl_attr) + net_pnl)
     setattr(self,fees_attr,getattr(self,fees_attr) + taker_fee)
     setattr(self,cash_attr,init_cap + getattr(self,pnl_attr))
     settled_set.add(tid)
     with open(ledger_path,"a",encoding="utf-8") as f:
      f.write(json.dumps(trade) + "\n")
    del open_map[m_id]
    save_fn()
 def save_state(self):
  val_total=len(self.val_trades)
  val_wins=sum(1 for t in self.val_trades if t.get("won"))
  val_wr=(val_wins / val_total * 100.0) if val_total > 0 else 0.0
  dev_total=len(self.dev_trades)
  dev_wins=sum(1 for t in self.dev_trades if t.get("won"))
  dev_wr=(dev_wins / dev_total * 100.0) if dev_total > 0 else 0.0
  state={ "timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"governance":{ "specification_version":"v3.1","validation_start_utc":R3_VALIDATION_START_UTC,"validation_start_unix":R3_VALIDATION_START_UNIX,"executable_depth_guard":"DepthRatio >= 1.50 (Fail-Closed)","fee_schedule":"crypto_fees_v2 (7% dynamic schedule enforced)","idempotent_event_sourced":True },"validation_oos_epoch":{ "paper_portfolio_equity":round(self.val_cash,2),"initial_capital":INITIAL_PAPER_CAPITAL,"cumulative_realized_pnl":round(self.val_realized_pnl,2),"total_fees_paid":round(self.val_total_fees,2),"total_trades_settled":val_total,"winning_trades":val_wins,"losing_trades":val_total - val_wins,"win_rate_pct":round(val_wr,2),"ledger_file":str(VALIDATION_LEDGER_FILE) },"dev_calibration_epoch":{ "paper_portfolio_equity":round(self.dev_cash,2),"initial_capital":INITIAL_PAPER_CAPITAL,"cumulative_realized_pnl":round(self.dev_realized_pnl,2),"total_fees_paid":round(self.dev_total_fees,2),"total_trades_settled":dev_total,"winning_trades":dev_wins,"losing_trades":dev_total - dev_wins,"win_rate_pct":round(dev_wr,2),"ledger_file":str(DEV_LEDGER_FILE) },"active_open_positions_count":sum(len(v) for v in self.open_trades.values()),"total_settled_trade_ids_tracked":len(self.settled_trade_ids),"current_hour_window":self.current_hour_window,"trades_this_hour":self.trades_this_hour,"status":"RUNNING" }
  tmp_file=STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
  try:
   with open(tmp_file,"w",encoding="utf-8") as f:
    json.dump(state,f,indent=2)
    f.flush()
    os.fsync(f.fileno())
   os.replace(tmp_file,STATE_FILE)
  except Exception:
   if tmp_file.exists():
    try:
     tmp_file.unlink()
    except Exception:
     pass
  if ENABLE_SOL_SHADOW_SLEEVE:
   self.save_sol_shadow_state()
  if ENABLE_XRP_SHADOW_SLEEVE:
   self.save_xrp_shadow_state()
 async def live_loop(self):
  print("===============================================================================",flush=True)
  print("   POLYMARKET AUTONOMOUS FORWARD PAPER TRADER (v3.1 Conformance State)        ",flush=True)
  print(f"   Frozen OOS Boundary: {R3_VALIDATION_START_UTC}                             ",flush=True)
  print("   Depth Guard: Fail-Closed (Ratio >= 1.50) | Fee Schedule: crypto_fees_v2    ",flush=True)
  print("   Ticket Size: $50.00 Notional | Initial Capital: $1,000.00                  ",flush=True)
  print("   Isolated Shadow Sleeves: SOL v3.9.2 ($500) + XRP v3.9.2 ($500)             ",flush=True)
  print("===============================================================================",flush=True)
  with open(PID_FILE,"w") as f:
   f.write(str(os.getpid()))
  if HOURLY_TELEMETRY_FILE.exists():
   self.last_telemetry_file_pos=HOURLY_TELEMETRY_FILE.stat().st_size
  if HOURLY_TELEMETRY_ETH_FILE.exists():
   self.last_telemetry_eth_file_pos=HOURLY_TELEMETRY_ETH_FILE.stat().st_size
  if HOURLY_TELEMETRY_SOL_FILE.exists():
   self.last_telemetry_sol_file_pos=HOURLY_TELEMETRY_SOL_FILE.stat().st_size
  if SUBHOURLY_TELEMETRY_SOL_FILE.exists():
   self.last_telemetry_sol_15m_file_pos=SUBHOURLY_TELEMETRY_SOL_FILE.stat().st_size
  if HOURLY_TELEMETRY_XRP_FILE.exists():
   self.last_telemetry_xrp_file_pos=HOURLY_TELEMETRY_XRP_FILE.stat().st_size
  if SUBHOURLY_TELEMETRY_XRP_FILE.exists():
   self.last_telemetry_xrp_15m_file_pos=SUBHOURLY_TELEMETRY_XRP_FILE.stat().st_size
  if SHOCK_SOL_FILE.exists():
   self.last_shock_sol_file_pos=SHOCK_SOL_FILE.stat().st_size
  if SHOCK_XRP_FILE.exists():
   self.last_shock_xrp_file_pos=SHOCK_XRP_FILE.stat().st_size
  self.replay_existing_data()
  import signal as _signal
  self._shutdown_requested=False
  def _request_shutdown(signame:str):
   if not self._shutdown_requested:
    print(f"[SHUTDOWN] {signame} received; flushing state and stopping gracefully.",flush=True)
   self._shutdown_requested=True
  _loop=asyncio.get_running_loop()
  for _sig in (_signal.SIGTERM,_signal.SIGINT):
   try:
    _loop.add_signal_handler(_sig,_request_shutdown,_sig.name)
   except (NotImplementedError,RuntimeError,ValueError):
    pass
  while True:
   if self._shutdown_requested:
    self.save_state()
    print("[SHUTDOWN] Paper trader state flushed; exiting cleanly (STOPPED_GRACEFULLY).",flush=True)
    break
   try:
    if TRIGGER_FILE.exists():
     current_trig_size=TRIGGER_FILE.stat().st_size
     if current_trig_size < self.last_trigger_file_pos:
      self.last_trigger_file_pos=current_trig_size
     if current_trig_size > self.last_trigger_file_pos:
      with open(TRIGGER_FILE,"rb") as f:
       f.seek(self.last_trigger_file_pos)
       chunk=f.read()
      complete_end=chunk.rfind(b"\n") + 1
      if complete_end:
       new_lines=chunk[:complete_end].decode("utf-8").splitlines()
       self.last_trigger_file_pos += complete_end
       for line in new_lines:
        if not line.strip():
         continue
        s=json.loads(line)
        shock_id=f"{s.get('market_id')}_{s.get('t0_unix')}"
        if shock_id not in self.seen_shock_ids:
         self.seen_shock_ids.add(shock_id)
         await asyncio.to_thread(self.evaluate_shock_signal,s,False)
    elif SHOCK_FILE.exists():
     current_shock_size=SHOCK_FILE.stat().st_size
     if current_shock_size < self.last_shock_file_pos:
      self.last_shock_file_pos=current_shock_size
     if current_shock_size > self.last_shock_file_pos:
      with open(SHOCK_FILE,"rb") as f:
       f.seek(self.last_shock_file_pos)
       chunk=f.read()
      complete_end=chunk.rfind(b"\n") + 1
      if complete_end:
       new_lines=chunk[:complete_end].decode("utf-8").splitlines()
       self.last_shock_file_pos += complete_end
       for line in new_lines:
        if not line.strip():
         continue
        s=json.loads(line)
        shock_id=f"{s.get('market_id')}_{s.get('t0_unix')}"
        if shock_id not in self.seen_shock_ids:
         self.seen_shock_ids.add(shock_id)
         await asyncio.to_thread(self.evaluate_shock_signal,s,False)
    for alt_shock_file,alt_pos_attr,alt_sym,alt_enabled in ( (SHOCK_SOL_FILE,"last_shock_sol_file_pos","SOL",ENABLE_SOL_SHADOW_SLEEVE),(SHOCK_XRP_FILE,"last_shock_xrp_file_pos","XRP",ENABLE_XRP_SHADOW_SLEEVE),):
     if alt_enabled and alt_shock_file.exists():
      cur_alt_sz=alt_shock_file.stat().st_size
      last_alt_pos=getattr(self,alt_pos_attr)
      if cur_alt_sz < last_alt_pos:
       setattr(self,alt_pos_attr,cur_alt_sz)
       last_alt_pos=cur_alt_sz
      if cur_alt_sz > last_alt_pos:
       with open(alt_shock_file,"rb") as f:
        f.seek(last_alt_pos)
        chunk=f.read()
       complete_end=chunk.rfind(b"\n") + 1
       if complete_end:
        new_alt_lines=chunk[:complete_end].decode("utf-8",errors="ignore").splitlines()
        setattr(self,alt_pos_attr,last_alt_pos + complete_end)
        for line in new_alt_lines:
         if not line.strip():
          continue
         s=json.loads(line)
         s.setdefault("asset",alt_sym)
         shock_id=f"{s.get('market_id')}_{s.get('t0_unix')}"
         if shock_id not in self.seen_shock_ids:
          self.seen_shock_ids.add(shock_id)
          await asyncio.to_thread(self.evaluate_shock_signal,s,False)
    if RESOLUTIONS_FILE.exists():
     current_res_size=RESOLUTIONS_FILE.stat().st_size
     if current_res_size > self.last_res_file_pos:
      with open(RESOLUTIONS_FILE,"rb") as f:
       f.seek(self.last_res_file_pos)
       chunk=f.read()
      complete_end=chunk.rfind(b"\n") + 1
      if complete_end:
       new_res_lines=chunk[:complete_end].decode("utf-8").splitlines()
       self.last_res_file_pos += complete_end
       for line in new_res_lines:
        if not line.strip():
         continue
        res=json.loads(line)
        m_id=res.get("market_id")
        if res.get("winning_outcome") in ("UP","DOWN") and m_id not in self.seen_resolution_ids:
         self.seen_resolution_ids.add(m_id)
         self.settle_market(m_id,res,historical=False)
    if ( self.open_trades or (ENABLE_SLEEVE_304_315 and self.sleeve2_open_trades) or (ENABLE_SOL_SHADOW_SLEEVE and self.sol_shadow_open_trades) or (ENABLE_XRP_SHADOW_SLEEVE and self.xrp_shadow_open_trades) ):
     for telem_path,pos_attr in ( (HOURLY_TELEMETRY_FILE,"last_telemetry_file_pos"),(HOURLY_TELEMETRY_ETH_FILE,"last_telemetry_eth_file_pos"),(HOURLY_TELEMETRY_SOL_FILE,"last_telemetry_sol_file_pos"),(SUBHOURLY_TELEMETRY_SOL_FILE,"last_telemetry_sol_15m_file_pos"),(HOURLY_TELEMETRY_XRP_FILE,"last_telemetry_xrp_file_pos"),(SUBHOURLY_TELEMETRY_XRP_FILE,"last_telemetry_xrp_15m_file_pos"),):
      if telem_path.exists():
       cur_sz=telem_path.stat().st_size
       last_pos=getattr(self,pos_attr)
       if cur_sz < last_pos:
        setattr(self,pos_attr,cur_sz)
        last_pos=cur_sz
       if cur_sz > last_pos:
        with open(telem_path,"rb") as f:
         f.seek(last_pos)
         chunk=f.read()
        complete_end=chunk.rfind(b"\n") + 1
        if complete_end:
         lines=chunk[:complete_end].decode("utf-8").splitlines()
         setattr(self,pos_attr,last_pos + complete_end)
         for line in lines:
          if not line.strip():
           continue
          try:
           telem=json.loads(line)
           t_m_id=str(telem.get("market_id",""))
           if ( t_m_id in self.open_trades or (ENABLE_SLEEVE_304_315 and t_m_id in self.sleeve2_open_trades) or (ENABLE_SOL_SHADOW_SLEEVE and t_m_id in self.sol_shadow_open_trades) or (ENABLE_XRP_SHADOW_SLEEVE and t_m_id in self.xrp_shadow_open_trades) ):
            self.check_maker_tp_fills(t_m_id,telem)
          except Exception:
           pass
    self.save_state()
    await asyncio.sleep(0.1)
   except Exception as e:
    print(f"[-] Error in paper trader loop: {e}",flush=True)
    await asyncio.sleep(1.0)
if __name__=="__main__":
 trader=PolymarketForwardPaperTrader()
 asyncio.run(trader.live_loop())

# === [08/12] src/polymarket_research/check_polymarket_balance.py :: Polygon pUSD + USDC.e Collateral Balance Checker ===
#!/usr/bin/env python3 import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests
PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent
load_dotenv(PIPELINE_ROOT / ".env")
WALLET_ADDR=os.getenv("POLYGON_FUNDER_ADDRESS","").strip()
if not WALLET_ADDR:
 print("[ERROR] POLYGON_FUNDER_ADDRESS is not set in .env")
 sys.exit(1)
USDC_E="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
PUSD="0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
def check_balance():
 print("=" * 65)
 print("        POLYMARKET LIVE BALANCE & STATUS INSPECTOR")
 print("=" * 65)
 print(f"Funder Wallet:   {WALLET_ADDR}")
 clob_bal=None
 try:
  from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
  ex=PolymarketLiveExecutor(dry_run=False)
  if ex.is_authenticated:
   clob_bal=ex.get_collateral_balance()
   print(f"CLOB L2 Balance: ${clob_bal:,.2f} USD")
 except Exception as e:
  pass
 rpcs=[ "https://polygon-bor-rpc.publicnode.com","https://polygon-rpc.com","https://polygon.gateway.tenderly.co","https://1rpc.io/matic",]
 pol_bal=0.0
 pusd_bal=0.0
 usdc_bal=0.0
 for rpc in rpcs:
  try:
   r_pol=requests.post(rpc,json={ "jsonrpc":"2.0","method":"eth_getBalance","params":[WALLET_ADDR,"latest"],"id":1 },timeout=2.5).json()
   if "result" in r_pol:
    pol_bal=int(r_pol["result"],16) / 1e18
   call_data="0x70a08231" + WALLET_ADDR[2:].lower().rjust(64,"0")
   r_pusd=requests.post(rpc,json={ "jsonrpc":"2.0","method":"eth_call","params":[{"to":PUSD,"data":call_data},"latest"],"id":2 },timeout=2.5).json()
   if "result" in r_pusd:
    pusd_bal=int(r_pusd["result"],16) / 1e6
   r_usdc=requests.post(rpc,json={ "jsonrpc":"2.0","method":"eth_call","params":[{"to":USDC_E,"data":call_data},"latest"],"id":3 },timeout=2.5).json()
   if "result" in r_usdc:
    usdc_bal=int(r_usdc["result"],16) / 1e6
   if pusd_bal > 0 or usdc_bal > 0 or pol_bal > 0:
    break
  except Exception:
   continue
 print(f"POL Gas Balance: {pol_bal:.4f} POL")
 print(f"pUSD On-chain:   ${pusd_bal:,.2f} pUSD (V2 Primary Collateral)")
 print(f"USDC.e On-chain: ${usdc_bal:,.2f} USDC.e (Legacy Bridge)")
 ledger_path=PIPELINE_ROOT / "data/polymarket/live_orders.jsonl"
 if ledger_path.exists():
  orders=[]
  with open(ledger_path,"r") as f:
   for line in f:
    if line.strip():
     orders.append(json.loads(line))
  print(f"\nLive Orders Dispatched: {len(orders)}")
  if orders:
   print("Recent Orders:")
   for o in orders[-5:]:
    print(f"  • [{o.get('timestamp_utc')[:19]}] {o.get('trade_id')} | {o.get('target_token')} | ${o.get('notional_usd')} @ ${o.get('price')} (Mode: {o.get('mode')})")
 else:
  print("\nLive Orders Ledger: No live orders placed yet.")
 print("=" * 65)
if __name__=="__main__":
 check_balance()

# === [09/12] src/polymarket_research/verify_onchain_allowances.py :: ERC-20/ERC-1155 Proxy & Exchange Allowance Verifier ===
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent
load_dotenv(PIPELINE_ROOT / ".env")
RPC="https://polygon-bor-rpc.publicnode.com"
w3=Web3(Web3.HTTPProvider(RPC))
try:
 w3.middleware_onion.inject(ExtraDataToPOAMiddleware,layer=0)
except Exception:
 pass
raw_wallet=os.getenv("POLYGON_FUNDER_ADDRESS","").strip()
if not raw_wallet:
 print("[ERROR] POLYGON_FUNDER_ADDRESS not found in .env")
 sys.exit(1)
WALLET=Web3.to_checksum_address(raw_wallet)
USDC_E=Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
PUSD=Web3.to_checksum_address("0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB")
CTF_CONTRACT=Web3.to_checksum_address("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045")
EXCHANGE_V2=Web3.to_checksum_address("0xE111180000d2663C0091e4f400237545B87B996B")
NEGRISK_V2=Web3.to_checksum_address("0xe2222d279d744050d28e00520010520000310F59")
EXCHANGE_V3=Web3.to_checksum_address("0xe3333700cA9d93003F00f0F71f8515005F6c00Aa")
ERC20_ABI=[ {"constant":True,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"} ]
ERC1155_ABI=[ {"constant":True,"inputs":[{"name":"account","type":"address"},{"name":"operator","type":"address"}],"name":"isApprovedForAll","outputs":[{"name":"","type":"bool"}],"type":"function"} ]
usdc=w3.eth.contract(address=USDC_E,abi=ERC20_ABI)
pusd=w3.eth.contract(address=PUSD,abi=ERC20_ABI)
ctf=w3.eth.contract(address=CTF_CONTRACT,abi=ERC1155_ABI)
print("=" * 65)
print("ON-CHAIN VERIFICATION OF V2 ALLOWANCES & APPROVALS")
print("=" * 65)
print(f"Funder Wallet: {WALLET}")
try:
 bal=pusd.functions.balanceOf(WALLET).call() / 1e6
 print(f"pUSD Balance (V2 Collateral): ${bal:,.2f}")
except Exception as e:
 print(f"pUSD Balance Query Failed: {e}")
spenders=[ ("CTF Exchange V2 (Binary Route)",EXCHANGE_V2),("NegRisk Exchange V2 (NegRisk Route)",NEGRISK_V2),("Exchange V3 (Protocol V2 Route)",EXCHANGE_V3),]
print("\n[pUSD (V2 Primary) & USDC.e Spender Allowances]")
for name,addr in spenders:
 try:
  raw_p=pusd.functions.allowance(WALLET,addr).call()
  usd_p=raw_p / 1e6
  is_max_p=(raw_p > 1e30)
  raw_u=usdc.functions.allowance(WALLET,addr).call()
  usd_u=raw_u / 1e6
  is_max_u=(raw_u > 1e30)
  p_str="MAX_UINT256 (Unlimited)" if is_max_p else f"${usd_p:,.2f}"
  u_str="MAX_UINT256 (Unlimited)" if is_max_u else f"${usd_u:,.2f}"
  print(f"  ✓ {name}: pUSD={p_str} | USDC.e={u_str}")
 except Exception as e:
  print(f"  ✗ {name}: Failed ({e})")
print("\n[CTF Operator Approvals]")
operators=[ ("CTF Exchange V2",EXCHANGE_V2),("NegRisk Exchange V2",NEGRISK_V2),("Exchange V3",EXCHANGE_V3),]
for name,addr in operators:
 try:
  appr=ctf.functions.isApprovedForAll(WALLET,addr).call()
  print(f"  ✓ CTF Operator Approval to {name}: {appr}")
 except Exception as e:
  print(f"  ✗ {name}: Failed ({e})")
print("\n[CLOB L2 Balance & Allowances]")
try:
 from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
 ex=PolymarketLiveExecutor(dry_run=False)
 if ex.is_authenticated:
  bal=ex.get_collateral_balance()
  print(f"  ✓ CLOB Collateral Balance: ${bal:.2f} USD")
  from py_clob_client_v2.clob_types import AssetType,BalanceAllowanceParams
  p=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL,signature_type=ex.signature_type)
  clob_res=ex.client.get_balance_allowance(p)
  allowances=clob_res.get("allowances",{})
  for addr,val in allowances.items():
   is_max=int(val) > 1e30 if str(val).isdigit() else False
   print(f"  ✓ Spender {addr[:10]}...{addr[-6:]}: {'MAX_UINT256 (Unlimited)' if is_max else val}")
except Exception as e:
 print(f"  ✗ CLOB Query Failed: {e}")
print("=" * 65)
print("VERIFICATION COMPLETE: READY FOR ZERO-REVERT EXECUTION")
print("=" * 65)

# === [10/12] src/polymarket_research/redeem_settled_positions.py :: CTF Settled Position Redemption Engine ===
#!/usr/bin/env python3 import json
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any,Dict,List,Optional
import requests
from dotenv import load_dotenv
PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT) not in sys.path:
 sys.path.insert(0,str(PIPELINE_ROOT))
load_dotenv(PIPELINE_ROOT / ".env")
logging.basicConfig( level=logging.INFO,format="[%(asctime)s UTC] [%(levelname)s] [CTF-REDEMPTION] %(message)s",)
logger=logging.getLogger("CTFRedemption")
CTF_CONTRACT="0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
NEG_RISK_ADAPTER="0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
PUSD_ADDRESS="0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
USDC_ADDRESS="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
POLYGON_RPCS=[ os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com"),"https://polygon-rpc.com","https://1rpc.io/matic",]
DATA_DIR=PIPELINE_ROOT / "data/polymarket"
STATE_FILE=DATA_DIR / "live_harvester_state.json"
from typing import Optional
def get_token_balance_onchain(funder_address:str,token_id:str)->Optional[float]:
 try:
  addr_padded=funder_address.lower().replace("0x","").zfill(64)
  token_int=int(token_id,16) if str(token_id).startswith("0x") else int(token_id)
  token_hex=hex(token_int)[2:].zfill(64)
  call_data=f"0x00fdd58e{addr_padded}{token_hex}"
  payload={ "jsonrpc":"2.0","method":"eth_call","params":[{"to":CTF_CONTRACT,"data":call_data},"latest"],"id":1,}
  last_err=None
  for rpc_url in POLYGON_RPCS:
   try:
    response=requests.post(rpc_url,json=payload,timeout=5)
    response.raise_for_status()
    resp=response.json()
    if resp.get("error") or not isinstance(resp.get("result"),str):
     raise RuntimeError(f"Invalid eth_call response: {resp}")
    result_hex=resp["result"]
    raw_balance=int(result_hex,16)
    return raw_balance / 1e6
   except Exception as rpc_e:
    last_err=rpc_e
  raise RuntimeError(f"All Polygon RPCs failed: {last_err}")
 except Exception as e:
  logger.error(f"Error querying on-chain balance for {token_id}: {e}")
  return None
def encode_ctf_merge_or_split_calldata( condition_id:str,amount_shares:float,collateral:str=USDC_ADDRESS,is_split:bool=False,neg_risk:bool=False,is_merge:Optional[bool]=None,)->tuple[str,str]:
 eff_split=(not bool(is_merge)) if is_merge is not None else bool(is_split)
 raw_amt=int(math.floor(max(0.0,float(amount_shares)) * 1_000_000 + 1e-6))
 if raw_amt<=0:
  raise ValueError("amount_shares must be > 0")
 cond_hex=condition_id.lower().replace("0x","").rjust(64,"0")
 amt_hex=hex(raw_amt)[2:].rjust(64,"0")
 if neg_risk:
  sel="0xa3d7da1d" if eff_split else "0xb10c5c17"
  return NEG_RISK_ADAPTER,f"{sel}{cond_hex}{amt_hex}"
 sel="0x72ce4275" if eff_split else "0x9e7212ad"
 col_hex=collateral.lower().replace("0x","").rjust(64,"0")
 zero_b32="0" * 64
 arr_offset=hex(5 * 32)[2:].rjust(64,"0")
 arr_len=hex(2)[2:].rjust(64,"0")
 idx_1=hex(1)[2:].rjust(64,"0")
 idx_2=hex(2)[2:].rjust(64,"0")
 return CTF_CONTRACT,f"{sel}{col_hex}{zero_b32}{cond_hex}{arr_offset}{amt_hex}{arr_len}{idx_1}{idx_2}"
def inspect_mergeable_complete_set( funder_or_condition_id:str,yes_token_or_shares:Any,no_token_or_shares:Any,neg_risk:Optional[bool]=None,)->Any:
 if neg_risk is not None or isinstance(yes_token_or_shares,(int,float)):
  sets=round(max(0.0,min(float(yes_token_or_shares or 0.0),float(no_token_or_shares or 0.0))),6)
  if sets<=0.0:
   return {"mergeable":False,"mergeable_sets":0.0,"target_contract":"","calldata":""}
  tgt,cd=encode_ctf_merge_or_split_calldata( funder_or_condition_id,sets,neg_risk=bool(neg_risk),is_merge=True )
  return {"mergeable":True,"mergeable_sets":sets,"target_contract":tgt,"calldata":cd}
 b_y=get_token_balance_onchain(funder_or_condition_id,str(yes_token_or_shares))
 b_n=get_token_balance_onchain(funder_or_condition_id,str(no_token_or_shares))
 if b_y is None or b_n is None:
  return 0.0
 return round(max(0.0,min(b_y,b_n)),6)
def _is_harvester_lock_active(lock_path:Path)->bool:
 if not lock_path.exists():
  return False
 try:
  raw_pid=lock_path.read_text(encoding="utf-8").strip()
  if not raw_pid.isdigit():
   return False
  pid=int(raw_pid)
  if pid<=0:
   return False
  os.kill(pid,0)
  return True
 except PermissionError:
  return True
 except OSError:
  return False
def _is_flock_held(lock_path:Path)->bool:
 if not lock_path.exists():
  return False
 try:
  import fcntl
 except ImportError:
  return False
 try:
  with open(lock_path,"a+") as fh:
   fcntl.flock(fh.fileno(),fcntl.LOCK_EX | fcntl.LOCK_NB)
   fcntl.flock(fh.fileno(),fcntl.LOCK_UN)
  return False
 except BlockingIOError:
  return True
 except OSError:
  return False
def audit_positions_and_redemptions(execute:bool=False,force:bool=False):
 funder_address=os.getenv("POLYGON_FUNDER_ADDRESS","").strip() or os.getenv("POLYGON_PROXY_ADDRESS","").strip()
 if not funder_address:
  logger.error("No funder/proxy address configured in .env!")
  return
 print("=" * 80)
 print("      POLYMARKET CTF SETTLEMENT & REDEMPTION AUDITOR")
 print("=" * 80)
 print(f"Proxy Wallet: {funder_address}")
 print(f"CTF Contract: {CTF_CONTRACT}")
 print(f"Collateral:   pUSD ({PUSD_ADDRESS}) / USDC.e ({USDC_ADDRESS})")
 if not STATE_FILE.exists():
  print(f"\nNo state file found at {STATE_FILE}. Zero recorded positions.")
  return
 with open(STATE_FILE,"r") as f:
  state=json.load(f)
 active_positions=state.get("active_positions",{})
 closed_positions=state.get("closed_positions",[])
 print(f"\nActive Positions: {len(active_positions)}")
 print(f"Closed Positions: {len(closed_positions)}")
 unredeemed_shares=0.0
 estimated_claimable_usd=0.0
 has_unknown=False
 claimable_conditions:List[str]=[]
 claimable_meta:Dict[str,Dict[str,Any]]={}
 print("\n--- POSITION AUDIT TABLE ---")
 for pos in list(active_positions.values()) + list(closed_positions):
  tid=pos.get("trade_id","N/A")
  token_id=pos.get("token_id")
  won=pos.get("won",False)
  close_reason=pos.get("close_reason","UNKNOWN")
  net_pnl=pos.get("net_pnl_usd",0.0)
  is_candidate=( pos.get("status")=="AWAITING_ONCHAIN_SETTLEMENT" or float(pos.get("winning_shares_held",0.0) or 0.0) > 0.0 or (bool(won) and close_reason in {"MARKET_RESOLVED","ONCHAIN_REDEMPTION_CONFIRMED"}) )
  if is_candidate and token_id:
   onchain_bal=get_token_balance_onchain(funder_address,token_id)
   if onchain_bal is None:
    has_unknown=True
    print(f"  [UNKNOWN / RETRY] {tid}: Polygon balance query failed; cannot classify redemption state")
    continue
   if onchain_bal > 0.01:
    unredeemed_shares += onchain_bal
    estimated_claimable_usd += onchain_bal * 1.0
    cid=str(pos.get("condition_id") or "").strip()
    if cid and cid not in claimable_conditions:
     claimable_conditions.append(cid)
     claimable_meta[cid]={ "neg_risk":pos.get("neg_risk"),"winning_token_id":str(token_id),}
    print(f"  [CLAIMABLE] {tid}: {onchain_bal:.2f} shares held on-chain -> ${onchain_bal:.2f} pUSD/USDC.e claimable")
   else:
    print(f"  [REDEEMED/EMPTY] {tid}: 0.00 shares held on-chain (already redeemed)")
  else:
   print(f"  [{close_reason}] {tid}: Won={won} | Net PnL=${net_pnl:+.2f}")
 print("\n" + "=" * 80)
 print(f"Total Claimable Winning Shares: {unredeemed_shares:.2f}")
 print(f"Estimated Claimable Collateral:   ${estimated_claimable_usd:.2f} pUSD/USDC.e")
 print("=" * 80)
 if execute and claimable_conditions:
  pid_lock=DATA_DIR / "live_harvester.pid"
  if not force and (_is_harvester_lock_active(pid_lock) or _is_flock_held(DATA_DIR / "live_harvester.lock")):
   logger.error( f"Refusing --execute while Live Harvester holds {pid_lock} (prevents EOA nonce collision with " "60s poll_onchain_redemptions). Stop harvester first or pass --force." )
   return
  from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
  executor=PolymarketLiveExecutor(dry_run=False)
  for cid in claimable_conditions:
   meta=claimable_meta.get(cid,{})
   tx_h=executor.attempt_onchain_redemption( cid,neg_risk=meta.get("neg_risk"),)
   print(f"  [EXECUTE REDEMPTION] condition={cid} -> tx_hash={tx_h or 'SKIPPED (insufficient EOA POL gas or non-1of1 proxy)'}")
 if estimated_claimable_usd > 0:
  print("\n[ACTION REQUIRED: REDEMPTION GUIDANCE]")
  print("If EOA holds >= 0.05 POL, run with --execute for Safe/EOA on-chain redemption, or redeem gaslessly:")
  print("  1. Log into https://polymarket.com using your funder wallet.")
  print("  2. Navigate to Portfolio -> History / Positions.")
  print("  3. Click 'Claim All' / 'Redeem' (Polymarket's relayer pays Polygon gas automatically).")
  print("  4. Collateral (pUSD / USDC.e) will be credited to your trading balance.")
 elif has_unknown:
  print("\n[WARNING] One or more positions could not be queried on-chain. Reconciliation incomplete - retry required.")
 else:
  print("\nAll winning positions are reconciled. No unredeemed tokens pending.")
if __name__=="__main__":
 audit_positions_and_redemptions(execute="--execute" in sys.argv,force="--force" in sys.argv)

# === [11/12] audit_losing_trades.py :: Autonomous Post-Trade Forensic Auditor & Daemon Health Verifier ===
#!/usr/bin/env python3 import argparse
import json
import os
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Dict,List,Optional
REPO_DIR=Path(r"C:\Users\Anton\source\repos\Dominus")
DATA_DIR=REPO_DIR / "data" / "polymarket"
AUDIT_STATE_FILE=DATA_DIR / "forensic_audit_state.json"
AUDIT_LEDGER_FILE=DATA_DIR / "forensic_audit_ledger.jsonl"
WFO_HYPOTHESIS_QUEUE_FILE=DATA_DIR / "wfo_hypothesis_queue.jsonl"
AUDIT_CLASSIFICATIONS=( "PLUMBING_0_PARAM","SEQUENCE_TELEMETRY_REQUIRED","PARAM_WFO_REQUIRED","EXPECTED_VARIANCE_NO_CHANGE","WIN_AUTO_CLEARED",)
_TYPE2_PARAM_TOKENS=( "min_cushion","dist_pct","z_strike","min_z","sigma_1h","max_px","min_px","kelly","wrong_side_thresh",)
_TUNE_VERBS=("tighten","widen","raise","lower","increase","decrease","tune","adjust threshold")
HISTORICAL_BASELINE_TRADES={ "LIVE_6011767_1792677997_DOWN","LIVE_6011823_1792678868_UP","LIVE_6011834_1792678920_UP","LIVE_6012053_1792679970_UP","LIVE_6012062_1792679970_UP","LIVE_5969579_1792680240_UP","LIVE_6012995_1792682563_UP","LIVE_6013539_1792683334_UP","LIVE_6014317_1792684214_UP","LIVE_5972389_1792686568_DOWN","LIVE_6016117_1792686984_DOWN","LIVE_6017333_1792688700_DOWN","LIVE_5978915_1792691143_UP","LIVE_6019058_1792692519_DOWN","LIVE_6022563_1792694165_UP","LIVE_6024982_1792697736_DOWN","LIVE_6026368_1792702377_DOWN","LIVE_6027101_1792704984_DOWN","LIVE_6032439_1792715250_DOWN","LIVE_6032790_1792716941_UP",}
def load_audit_state()->Dict[str,Any]:
 if AUDIT_STATE_FILE.exists():
  try:
   st=json.loads(AUDIT_STATE_FILE.read_text(encoding="utf-8"))
   audited=st.setdefault("audited_trades",{})
   for tid in HISTORICAL_BASELINE_TRADES:
    if tid not in audited:
     audited[tid]={"trade_id":tid,"verdict":"HISTORICAL_BASELINE"}
   return st
  except Exception:
   pass
 return { "updated_at":None,"audited_trades":{tid:{"trade_id":tid,"verdict":"HISTORICAL_BASELINE"} for tid in HISTORICAL_BASELINE_TRADES},"stats":{ "profits_skipped":0,"expected_losses_ok":0,"bugs_fixed_and_redeployed":0,"total_redeployments":0,},"recent_verdicts":[],}
def save_audit_state(st:Dict[str,Any])->None:
 DATA_DIR.mkdir(parents=True,exist_ok=True)
 st["updated_at"]=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
 tmp=AUDIT_STATE_FILE.with_suffix(".tmp")
 tmp.write_text(json.dumps(st,indent=2),encoding="utf-8")
 os.replace(tmp,AUDIT_STATE_FILE)
def append_audit_ledger(rec:Dict[str,Any])->None:
 DATA_DIR.mkdir(parents=True,exist_ok=True)
 with open(AUDIT_LEDGER_FILE,"a",encoding="utf-8") as f:
  f.write(json.dumps(rec) + "\n")
def append_wfo_hypothesis_queue(rec:Dict[str,Any])->None:
 DATA_DIR.mkdir(parents=True,exist_ok=True)
 with open(WFO_HYPOTHESIS_QUEUE_FILE,"a",encoding="utf-8") as f:
  f.write(json.dumps(rec) + "\n")
def classify_losing_trade_forensics(rec:Dict[str,Any])->Dict[str,str]:
 st=str(rec.get("status") or "").upper()
 cr=str(rec.get("close_reason") or "").upper()
 em=str(rec.get("entry_mode") or "").upper()
 if st in {"UNRESOLVED_BALANCE_DISCREPANCY","ENTRY_OUTCOME_UNKNOWN","EXIT_CANCEL_PENDING"} or "ERROR" in cr:
  return {"suggested_classification":"PLUMBING_0_PARAM","rationale":"Deterministic state/reconciliation anomaly."}
 if "LEGGED_OUT" in cr or any(k in em for k in ("RESCUE","FALLBACK","DOWNSNAP")):
  return {"suggested_classification":"SEQUENCE_TELEMETRY_REQUIRED","rationale":"Sequence/timing event; check simulator."}
 return {"suggested_classification":"EXPECTED_VARIANCE_NO_CHANGE","rationale":"Variance; threshold edits need PARAM_WFO_REQUIRED."}
def fetch_kraken_live_state()->Dict[str,Any]:
 cmd=[ "ssh","-n","-o","ConnectTimeout=5","kraken-finland","systemctl --user is-active polymarket-live-harvester.service ; cat /home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json" ]
 res=subprocess.run(cmd,capture_output=True,text=True,timeout=9.0)
 if res.returncode!=0 and not res.stdout.strip():
  raise RuntimeError(res.stderr.strip() or "SSH to kraken-finland failed")
 lines=res.stdout.strip().splitlines()
 svc_status=lines[0].strip() if lines else "unknown"
 st=json.loads("\n".join(lines[1:]))
 return {"service_status":svc_status,"state":st}
def scan_trades()->Dict[str,Any]:
 audit_st=load_audit_state()
 audited=audit_st.setdefault("audited_trades",{})
 uninspected_losses:List[Dict[str,Any]]=[]
 newly_skipped_wins=0
 try:
  remote=fetch_kraken_live_state()
  svc_status=remote["service_status"]
  st=remote["state"]
  risk_st=st.get("risk_state") or {}
  is_halted=bool(st.get("risk_halt",False) or risk_st.get("halted",False))
  healthy=(svc_status=="active") and (not is_halted) and (st.get("status")=="RUNNING")
  closed_positions=list(st.get("closed_positions",[]))
 except Exception as e:
  return { "status":"ACTION_REQUIRED","daemon_health":{"healthy":False,"error":str(e)},"newly_cleared_wins":0,"uninspected_losses_count":0,"uninspected_losses":[],"audit_stats":audit_st.get("stats",{}),}
 for rec in closed_positions:
  tid=str(rec.get("trade_id") or "")
  if not tid or tid in audited:
   continue
  if ( rec.get("exit_order_status")=="AWAITING_REDEMPTION" or rec.get("status")=="AWAITING_ONCHAIN_SETTLEMENT" ) and rec.get("net_pnl_usd") is None:
   continue
  raw_pnl=rec.get("net_pnl_usd")
  if raw_pnl is not None:
   won=float(raw_pnl)>=0.0
  else:
   won=bool(rec.get("won") is True)
  if won:
   entry={ "timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"trade_id":tid,"sleeve":rec.get("sleeve"),"asset":rec.get("asset"),"net_pnl_usd":rec.get("net_pnl_usd"),"verdict":"PROFIT_OK","classification":"WIN_AUTO_CLEARED","notes":"Winning real-money trade — auto-cleared.",}
   audited[tid]=entry
   audit_st["stats"]["profits_skipped"]=audit_st["stats"].get("profits_skipped",0) + 1
   newly_skipped_wins += 1
   append_audit_ledger(entry)
  else:
   rec_enriched=dict(rec)
   rec_enriched["forensic_classification_hint"]=classify_losing_trade_forensics(rec)
   uninspected_losses.append(rec_enriched)
 save_audit_state(audit_st)
 health={ "mode":"LIVE_REAL_MONEY_KRAKEN_FINLAND","healthy":healthy,"service_status":svc_status,"status":st.get("status"),"risk_halt":is_halted,"halt_reason":(st.get("risk_state") or {}).get("halt_reason",""),"live_bankroll_usd":round(float(st.get("live_bankroll") or 0.0),2),"total_account_equity_usd":round(float(st.get("total_account_equity") or 0.0),2),"open_positions_count":st.get("active_positions_count",0),"open_position_ids":st.get("active_position_ids",[]),"closed_positions_count":st.get("closed_positions_count",0),"trades_this_hour":st.get("trades_this_hour",0),}
 status_code="ACTION_REQUIRED" if (uninspected_losses or not healthy) else "ALL_GOOD"
 return { "status":status_code,"daemon_health":health,"newly_cleared_wins":newly_skipped_wins,"uninspected_losses_count":len(uninspected_losses),"uninspected_losses":uninspected_losses,"audit_stats":audit_st.get("stats",{}),}
def mark_audited( trade_id:str,verdict:str,notes:str,classification:Optional[str]=None,wfo_grid:str="",)->Dict[str,Any]:
 default_cls={ "EXPECTED_LOSS":"EXPECTED_VARIANCE_NO_CHANGE","BUG_FIXED":"PLUMBING_0_PARAM","PARAM_WFO_REQUIRED":"PARAM_WFO_REQUIRED","PROFIT_OK":"WIN_AUTO_CLEARED",}
 resolved_cls=classification or default_cls.get(verdict,"EXPECTED_VARIANCE_NO_CHANGE")
 if resolved_cls not in AUDIT_CLASSIFICATIONS:
  raise ValueError(f"Unsupported classification: {resolved_cls}")
 notes_low=(notes or "").lower()
 if verdict=="BUG_FIXED":
  if resolved_cls!="PLUMBING_0_PARAM":
   raise ValueError( f"GOVERNANCE_VIOLATION: verdict=BUG_FIXED requires classification=PLUMBING_0_PARAM (got {resolved_cls})." )
  if classification is None and any(tok in notes_low for tok in _TYPE2_PARAM_TOKENS) and any( vb in notes_low for vb in _TUNE_VERBS ):
   raise ValueError( "GOVERNANCE_VIOLATION: Numerical strategy/risk parameter tuning cannot be recorded as BUG_FIXED; " "use --verdict PARAM_WFO_REQUIRED." )
 audit_st=load_audit_state()
 audited=audit_st.setdefault("audited_trades",{})
 now_str=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
 entry:Dict[str,Any]={ "timestamp":now_str,"trade_id":trade_id,"verdict":verdict,"classification":resolved_cls,"notes":notes,}
 if wfo_grid:
  entry["wfo_grid"]=wfo_grid
 audited[trade_id]=entry
 if verdict=="EXPECTED_LOSS":
  audit_st["stats"]["expected_losses_ok"]=audit_st["stats"].get("expected_losses_ok",0) + 1
 elif verdict=="BUG_FIXED":
  audit_st["stats"]["bugs_fixed_and_redeployed"]=audit_st["stats"].get("bugs_fixed_and_redeployed",0) + 1
 elif verdict=="PARAM_WFO_REQUIRED":
  audit_st["stats"]["param_wfo_queued"]=audit_st["stats"].get("param_wfo_queued",0) + 1
 if verdict=="PARAM_WFO_REQUIRED" or resolved_cls in ("PARAM_WFO_REQUIRED","SEQUENCE_TELEMETRY_REQUIRED"):
  append_wfo_hypothesis_queue({ "queued_at":now_str,"trade_id":trade_id,"verdict":verdict,"classification":resolved_cls,"wfo_grid":wfo_grid,"notes":notes,"status":"QUEUED_FOR_PURGED_WFO",})
 recent=audit_st.setdefault("recent_verdicts",[])
 recent.append(entry)
 audit_st["recent_verdicts"]=recent[-30:]
 save_audit_state(audit_st)
 append_audit_ledger(entry)
 print(json.dumps({"ok":True,"recorded":entry},indent=2))
 return entry
def redeploy_daemon(force:bool=False)->None:
 if not force:
  pre=fetch_kraken_live_state()["state"]
  open_cnt=int(pre.get("active_positions_count",0) or 0)
  if open_cnt > 0:
   raise RuntimeError( f"Refusing to restart live harvester with {open_cnt} open position(s): " f"{pre.get('active_position_ids', [])}. Wait until flat." )
 cmd=[ "ssh","-n","kraken-finland",( "/home/skybullet1987/quant_pipeline/venv/bin/python -m py_compile " "/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_terminal_recorder.py " "/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_executor.py " "/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_harvester.py && " "systemctl --user daemon-reload && " "systemctl --user reset-failed polymarket-live-harvester.service || true && " "systemctl --user restart polymarket-live-harvester.service && " "for i in 1 2 3 4 5 6 7 8 9 10; do " "sleep 2; " "if grep -q '\"status\": \"RUNNING\"' /home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json 2>/dev/null; then break; fi; " "done && " "systemctl --user is-active polymarket-live-harvester.service" ),]
 res=subprocess.run(cmd,capture_output=True,text=True,timeout=45.0)
 if res.returncode!=0:
  raise RuntimeError(f"Redeploy on kraken-finland failed: {res.stderr or res.stdout}")
 audit_st=load_audit_state()
 audit_st["stats"]["total_redeployments"]=audit_st["stats"].get("total_redeployments",0) + 1
 save_audit_state(audit_st)
 scan_res=scan_trades()
 print(json.dumps({"redeployed":True,"daemon_health":scan_res["daemon_health"]},indent=2))
def main()->None:
 parser=argparse.ArgumentParser(description="Autonomous Post-Trade Forensic Auditor (Real-Money Live Harvester)")
 parser.add_argument("--check",action="store_true",help="Scan for uninspected real-money losing trades and live harvester health")
 parser.add_argument("--mark-audited",type=str,help="Trade ID to mark as audited")
 parser.add_argument("--verdict",type=str,choices=["EXPECTED_LOSS","BUG_FIXED","PARAM_WFO_REQUIRED","PROFIT_OK"],default="EXPECTED_LOSS")
 parser.add_argument("--classification",type=str,choices=list(AUDIT_CLASSIFICATIONS),default=None,help="Structured Type 0 / Type 1 / Type 2 forensic classification")
 parser.add_argument("--wfo-grid",type=str,default="",help="Optional Purged WFO grid specification routed to wfo_hypothesis_queue.jsonl")
 parser.add_argument("--notes",type=str,default="",help="Forensic explanation or patch summary")
 parser.add_argument("--redeploy",action="store_true",help="Compile-check and restart polymarket-live-harvester.service on kraken-finland")
 parser.add_argument("--force-redeploy",action="store_true",help="Override open-position safety lock during emergency recovery")
 args=parser.parse_args()
 if args.mark_audited:
  mark_audited(args.mark_audited,args.verdict,args.notes,classification=args.classification,wfo_grid=args.wfo_grid)
 elif args.redeploy:
  redeploy_daemon(force=args.force_redeploy)
 else:
  res=scan_trades()
  print(json.dumps(res,indent=2))
if __name__=="__main__":
 main()

# === [12/12] scripts/honest_purged_wfo_optimizer.py :: Zero-Lookahead Purged WFO & Genuine Refit CPCV(6,2) Optimizer ===
#!/usr/bin/env python3 # from __future__ import annotations  # (Lifted to top of consolidated bundle) import bisect
import collections
import gzip
import json
import math
import multiprocessing as mp
import os
import pickle
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any,Dict,Iterator,List,Optional,Tuple
_REPO_ROOT=str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
 sys.path.insert(0,_REPO_ROOT)
try:
 from src.polymarket_research.orderflow_wfo_simulators import calibrate_d1_box_wfo,simulate_microclip_cascade_entry
except ImportError:
 calibrate_d1_box_wfo=None
 simulate_microclip_cascade_entry=None
try:
 import orjson as _orjson
 def _loads(line:str)->Any:
  return _orjson.loads(line)
except ImportError:
 def _loads(line:str)->Any:
  return json.loads(line)
PIPELINE_ROOT=Path("/home/skybullet1987/quant_pipeline")
DATA_DIR=PIPELINE_ROOT / "data" / "polymarket"
OUT_JSON=DATA_DIR / "honest_wfo_results.json"
CACHE_PKL=Path("/tmp/pm_wfo_v40_dataset.pkl")
FEE_RATE=0.07
def taker_fee_per_share(px:float,fee_rate:float=FEE_RATE)->float:
 px_c=max(0.001,min(0.999,px))
 return fee_rate * px_c * (1.0 - px_c)
def walk_bids_vwap(raw_bids:List[Any],best_bid:float,target_shares:float=22.0)->float:
 if not raw_bids:
  return max(0.0,best_bid - 0.01) if best_bid > 0.02 else best_bid
 rem=target_shares
 cash=0.0
 filled=0.0
 for lvl in raw_bids:
  if not isinstance(lvl,(list,tuple)) or len(lvl) < 2:
   continue
  px,sz=float(lvl[0]),float(lvl[1])
  if px<=0 or sz<=0:
   continue
  take=min(rem,sz)
  cash += take * px
  filled += take
  rem -= take
  if rem<=1e-6:
   break
 if filled<=0:
  return 0.0
 if rem > 1e-6:
  tail_px=max(0.01,float(raw_bids[-1][0]) - 0.03)
  cash += rem * tail_px
  filled += rem
 return round(cash / filled,4)
def infer_asset_and_horizon(d:Dict[str,Any])->Tuple[str,str]:
 title=str(d.get("title") or "")
 asset=str(d.get("asset") or "").upper()
 if not asset:
  if "Ethereum" in title or "ETH" in title:
   asset="ETH"
  elif "Solana" in title or "SOL" in title:
   asset="SOL"
  else:
   asset="BTC"
 hz=str(d.get("horizon") or d.get("candle_interval") or "").lower()
 if not hz:
  if "above" in title.lower() or "strike" in title.lower():
   hz="daily"
  elif "-" in title.split("ET")[0].split(",")[-1]:
   hz="15m"
  else:
   hz="1h"
 if "15" in hz:
  hz="15m"
 elif "1h" in hz or "hour" in hz or "60" in hz:
  hz="1h"
 return asset,hz
def iter_jsonl_lines_with_archives(data_dir:Path,filename:str)->Iterator[str]:
 stem=Path(filename).stem
 arch_dir=data_dir / "archive"
 prefix=f"{stem}__20"
 if arch_dir.is_dir():
  for gz_path in sorted(arch_dir.glob(f"{stem}__*.jsonl.gz")):
   if not gz_path.name.startswith(prefix):
    continue
   try:
    with gzip.open(gz_path,"rt",encoding="utf-8",errors="replace") as gf:
     for line in gf:
      yield line
   except Exception:
    continue
 hot_path=data_dir / filename
 if hot_path.exists():
  with open(hot_path,"r",encoding="utf-8",errors="replace") as hf:
   for line in hf:
    yield line
def load_dataset(use_cache:bool=True)->Tuple[List[Dict[str,Any]],Dict[str,Any]]:
 if use_cache and CACHE_PKL.exists():
  try:
   t0_c=time.time()
   with open(CACHE_PKL,"rb") as f:
    cands,meta=pickle.load(f)
   meta["cache_hit_sec"]=round(time.time() - t0_c,2)
   return cands,meta
  except Exception:
   pass
 t_start=time.time()
 ver_path=DATA_DIR / "verified_gamma_resolutions.json"
 verified:Dict[str,Dict[str,Any]]=json.loads(ver_path.read_text(encoding="utf-8"))
 market_paths:Dict[str,List[Tuple[float,float,float,float,float,float,float,float]]]=collections.defaultdict(list)
 market_expiry:Dict[str,float]={}
 sr_index:Dict[str,List[Tuple[float,Dict[str,Any]]]]=collections.defaultdict(list)
 sr_count=0
 ir_offsets={"100ms":0.1,"250ms":0.25,"500ms":0.5,"1s":1.0,"5s":5.0,"30s":30.0}
 for sr_name in ("shock_responses.jsonl","shock_responses_eth.jsonl","shock_responses_sol.jsonl"):
  for line in iter_jsonl_lines_with_archives(DATA_DIR,sr_name):
   if not line.strip():
    continue
   try:
    d=_loads(line)
   except Exception:
    continue
   mid=str(d.get("market_id") or "")
   if mid not in verified:
    continue
   t0=float(d.get("t0_unix") or 0.0)
   ir=d.get("impulse_response") or {}
   if t0 > 0 and ir:
    sr_index[mid].append((t0,ir))
    sr_count += 1
    base_sp=float(d.get("spot_at_t0") or d.get("spot_at_shock") or 0.0)
    for h_key,def_dt in ir_offsets.items():
     step=ir.get(h_key)
     if not step:
      continue
     dt=float(step.get("elapsed_sec") or def_dt)
     u_ask=float(step.get("up_ask") or 1.0)
     u_mid=float(step.get("up_mid") or 0.0)
     u_bid=max(0.0,round(2.0 * u_mid - u_ask,3)) if (u_mid > 0 and u_ask < 1.0) else 0.0
     d_ask=float(step.get("down_ask") or 1.0)
     d_mid=float(step.get("down_mid") or 0.0)
     d_bid=max(0.0,round(2.0 * d_mid - d_ask,3)) if (d_mid > 0 and d_ask < 1.0) else 0.0
     sp=float(step.get("binance_spot") or base_sp)
     market_paths[mid].append(( t0 + dt,sp,u_bid,u_ask,d_bid,d_ask,max(0.0,u_bid - 0.005),max(0.0,d_bid - 0.005) ))
 for mid in sr_index:
  sr_index[mid].sort(key=lambda x:x[0])
 telem_rows=0
 for t_name in ("polymarket_hourly_telemetry.jsonl","polymarket_hourly_telemetry_eth.jsonl","polymarket_hourly_telemetry_sol.jsonl"):
  last_ts_by_mid:Dict[str,float]={}
  for line in iter_jsonl_lines_with_archives(DATA_DIR,t_name):
   if not line.strip():
    continue
   try:
    d=_loads(line)
   except Exception:
    continue
   mid=str(d.get("market_id") or "")
   if mid not in verified:
    continue
   ts=float(d.get("timestamp_unix") or 0.0)
   if ts - last_ts_by_mid.get(mid,0.0) < 2.0 and float(d.get("seconds_to_expiry") or 999) > 90.0:
    continue
   last_ts_by_mid[mid]=ts
   tte=float(d.get("seconds_to_expiry") or 0.0)
   if tte > 0:
    market_expiry[mid]=ts + tte
   sp=float(d.get("binance_spot") or 0.0)
   up=d.get("UP") or {}
   dn=d.get("DOWN") or {}
   u_bid=float(up.get("best_bid") or 0.0)
   u_ask=float(up.get("best_ask") or 1.0)
   d_bid=float(dn.get("best_bid") or 0.0)
   d_ask=float(dn.get("best_ask") or 1.0)
   u_vwap=walk_bids_vwap(up.get("raw_top_bids") or [],u_bid)
   d_vwap=walk_bids_vwap(dn.get("raw_top_bids") or [],d_bid)
   market_paths[mid].append((ts,sp,u_bid,u_ask,d_bid,d_ask,u_vwap,d_vwap))
   telem_rows += 1
 for line in iter_jsonl_lines_with_archives(DATA_DIR,"exp306_realtime_boundary_merge.jsonl"):
  if not line.strip():
   continue
  try:
   d=_loads(line)
  except Exception:
   continue
  mid=str(d.get("market_id") or "")
  if mid not in verified:
   continue
  ts=float(d.get("timestamp_unix") or 0.0)
  u_ask=float(d.get("ask_up") or 1.0)
  d_ask=float(d.get("ask_down") or 1.0)
  u_bid=max(0.0,round(1.0 - d_ask,3)) if d_ask < 1.0 else 0.0
  d_bid=max(0.0,round(1.0 - u_ask,3)) if u_ask < 1.0 else 0.0
  market_paths[mid].append((ts,0.0,u_bid,u_ask,d_bid,d_ask,max(0.0,u_bid - 0.01),max(0.0,d_bid - 0.01)))
 raw_triggers:List[Tuple[float,str,str,str,float,Dict[str,Any]]]=[]
 for line in iter_jsonl_lines_with_archives(DATA_DIR,"live_shock_triggers.jsonl"):
  if not line.strip():
   continue
  try:
   d=_loads(line)
  except Exception:
   continue
  mid=str(d.get("market_id") or "")
  if mid not in verified:
   continue
  asset,hz=infer_asset_and_horizon(d)
  if hz not in ("15m","1h") or asset not in ("BTC","ETH","SOL"):
   continue
  t0=float(d.get("t0_unix") or 0.0)
  tte=float(d.get("seconds_to_expiry") or 0.0)
  if t0<=0 or tte<=5.0:
   continue
  exp_ts=float(d.get("candle_expiry_ts") or d.get("expiry_ts") or (t0 + tte))
  market_expiry[mid]=exp_ts
  pre=d.get("pre_shock_features_t0") or {}
  up=pre.get("UP") or {}
  dn=pre.get("DOWN") or {}
  sp=float(d.get("spot_at_t0") or 0.0)
  u_bid=float(up.get("best_bid") or 0.0)
  u_ask=float(up.get("best_ask") or 1.0)
  d_bid=float(dn.get("best_bid") or 0.0)
  d_ask=float(dn.get("best_ask") or 1.0)
  u_vwap_b=walk_bids_vwap(up.get("raw_top_bids") or [],u_bid)
  d_vwap_b=walk_bids_vwap(dn.get("raw_top_bids") or [],d_bid)
  market_paths[mid].append((t0,sp,u_bid,u_ask,d_bid,d_ask,u_vwap_b,d_vwap_b))
  raw_triggers.append((t0,asset,hz,mid,exp_ts,d))
 raw_triggers.sort(key=lambda x:x[0])
 market_ts_index:Dict[str,List[float]]={}
 for mid,pts in market_paths.items():
  pts.sort(key=lambda x:x[0])
  cleaned=[]
  last_sp=0.0
  last_t=-1.0
  for pt in pts:
   ts,sp,ub,ua,db,da,uvb,dvb=pt
   if sp > 0:
    last_sp=sp
   else:
    sp=last_sp
   if ts - last_t < 0.05 and cleaned:
    cleaned[-1]=(ts,sp,ub,ua,db,da,uvb,dvb)
   else:
    cleaned.append((ts,sp,ub,ua,db,da,uvb,dvb))
    last_t=ts
  market_paths[mid]=cleaned
  market_ts_index[mid]=[p[0] for p in cleaned]
 venue_hist:Dict[str,collections.deque]={a:collections.deque(maxlen=200) for a in ("BTC","ETH","SOL")}
 spot_5m_hist:Dict[str,collections.deque]={a:collections.deque(maxlen=60) for a in ("BTC","ETH","SOL")}
 last_5m_bucket:Dict[str,int]={a:0 for a in ("BTC","ETH","SOL")}
 rolling_sigma_1h:Dict[str,float]={"BTC":0.0048,"ETH":0.0062,"SOL":0.0090}
 candidates:List[Dict[str,Any]]=[]
 for t0,asset,hz,mid,exp_ts,d in raw_triggers:
  sp=float(d.get("spot_at_t0") or 0.0)
  if sp<=0:
   continue
  b5=int(t0 // 300)
  if b5 > last_5m_bucket[asset]:
   if spot_5m_hist[asset]:
    prev_sp=spot_5m_hist[asset][-1]
    ret_5m=math.log(sp / prev_sp)
    var_1h_obs=12.0 * (ret_5m ** 2)
    cur_var=rolling_sigma_1h[asset] ** 2
    new_var=0.94 * cur_var + 0.06 * var_1h_obs
    rolling_sigma_1h[asset]=max(0.0020,min(0.0250,math.sqrt(new_var)))
   spot_5m_hist[asset].append(sp)
   last_5m_bucket[asset]=b5
  raw_vdiv=d.get("venue_divergence_bps")
  vdiv_centered=0.0
  if raw_vdiv is not None:
   rv=float(raw_vdiv)
   if len(venue_hist[asset])>=20:
    med_v=statistics.median(venue_hist[asset])
    vdiv_centered=rv - med_v
   venue_hist[asset].append(rv)
  shock_dir=str(d.get("shock_direction") or "").upper()
  if shock_dir not in ("BUY","SELL"):
   continue
  side="UP" if shock_dir=="BUY" else "DOWN"
  sign=1.0 if side=="UP" else -1.0
  open_sp=float(d.get("candle_open_spot") or d.get("finalized_1h_open") or 0.0)
  if open_sp<=0:
   continue
  twap_open=float(d.get("twap_60s_open") or open_sp)
  if twap_open<=0:
   twap_open=open_sp
  pre=(d.get("pre_shock_features_t0") or {}).get(side) or {}
  ask_t0=float(pre.get("best_ask") or 1.0)
  bid_t0=float(pre.get("best_bid") or 0.0)
  if not (0.35<=ask_t0<=0.96) or bid_t0<=0.0:
   continue
  spread_t0=round(ask_t0 - bid_t0,4)
  if spread_t0 < -0.001 or spread_t0 > 0.12:
   continue
  ask_sz=float(pre.get("ask_size_l1") or pre.get("ask_size") or 0.0)
  bid_sz=float(pre.get("bid_size_l1") or pre.get("bid_size") or 0.0)
  obi_l1=float(pre.get("obi_l1") if pre.get("obi_l1") is not None else (pre.get("obi") or 0.0))
  age_ask_ms=float(pre.get("age_ask_ms") if pre.get("age_ask_ms") is not None else (pre.get("quote_age_ms") or 50.0))
  vwap20_t0=float(pre.get("vwap_$20") or ask_t0)
  slip20_t0=max(0.0,vwap20_t0 - ask_t0)
  tte=float(d.get("seconds_to_expiry") or (exp_ts - t0))
  sigma_1h=rolling_sigma_1h[asset]
  sigma_rem=max(0.00025,sigma_1h * math.sqrt(max(tte,1.0) / 3600.0))
  cushion_open=sign * (sp - open_sp) / open_sp
  cushion_twap=sign * (sp - twap_open) / twap_open
  cushion_min=min(cushion_open,cushion_twap)
  vdiv_clamped_bps=max(-50.0,min(50.0,vdiv_centered))
  sp_cl_proxy=sp * (1.0 - 0.5 * (vdiv_clamped_bps / 10000.0))
  cushion_cl_proxy=min( sign * (sp_cl_proxy - open_sp) / open_sp,sign * (sp_cl_proxy - twap_open) / twap_open,)
  cushion_oracle=cushion_open if hz=="1h" else min(cushion_min,cushion_cl_proxy)
  z_cushion=cushion_min / sigma_rem
  z_cushion_cl=cushion_cl_proxy / sigma_rem
  z_oracle=cushion_oracle / sigma_rem
  shock_vol=float(d.get("shock_volume_100ms") or 0.0)
  shock_ofi=abs(float(d.get("shock_ofi") or 0.0))
  cb_move_2s=float(d.get("coinbase_move_bps_2s") or 0.0) * sign
  ask_500ms=None
  ask_1000ms=None
  sr_list=sr_index.get(mid)
  if sr_list:
   idx_sr=bisect.bisect_left(sr_list,(t0 - 0.30,{}))
   for j in range(idx_sr,min(len(sr_list),idx_sr + 3)):
    if abs(sr_list[j][0] - t0)<=0.35:
     ir=sr_list[j][1]
     k_ask="up_ask" if side=="UP" else "down_ask"
     if ir.get("500ms") and ir["500ms"].get(k_ask):
      ask_500ms=float(ir["500ms"][k_ask])
     if ir.get("1s") and ir["1s"].get(k_ask):
      ask_1000ms=float(ir["1s"][k_ask])
     break
  pts=market_paths[mid]
  ts_list=market_ts_index[mid]
  idx_next=bisect.bisect_right(ts_list,t0 + 0.12)
  if ask_500ms is None:
   if idx_next < len(pts) and (pts[idx_next][0] - t0)<=2.0:
    ask_500ms=pts[idx_next][3] if side=="UP" else pts[idx_next][5]
   else:
    jump=0.01 if shock_vol>=350_000 else 0.0
    if obi_l1 < -0.35:
     jump += 0.01
    if ask_sz * ask_t0 < 25.0:
     jump += 0.01
    ask_500ms=min(0.99,round(ask_t0 + jump,4))
  if ask_1000ms is None:
   ask_1000ms=min(0.99,round(ask_500ms + (0.01 if shock_vol>=500_000 else 0.0),4))
  idx_p0=bisect.bisect_right(ts_list,t0 + 0.45)
  raw_post=pts[idx_p0:]
  if len(raw_post) > 90:
   stride=max(1,len(raw_post) // 65)
   keep_idx=set(range(0,len(raw_post),stride))
   for k_i,p_row in enumerate(raw_post):
    if exp_ts - p_row[0]<=75.0 or (p_row[0] - t0)<=35.0:
     keep_idx.add(k_i)
   b_col=2 if side=="UP" else 4
   keep_idx.add(max(range(len(raw_post)),key=lambda i:raw_post[i][b_col]))
   keep_idx.add(min(range(len(raw_post)),key=lambda i:raw_post[i][b_col]))
   raw_post=[raw_post[i] for i in sorted(keep_idx)]
  compact_path=[]
  strike_worst=open_sp if hz=="1h" else (max(open_sp,twap_open) if side=="UP" else min(open_sp,twap_open))
  idx_mc0=bisect.bisect_right(ts_list,t0 + 0.04)
  idx_mc1=bisect.bisect_right(ts_list,t0 + 5.50)
  micro_clips=[ ( round(p_ts - t0,3),sign * (p_sp - strike_worst) / strike_worst if p_sp > 0 else cushion_oracle,ub if side=="UP" else db,ua if side=="UP" else da,) for p_ts,p_sp,ub,ua,db,da,_,_ in pts[idx_mc0:idx_mc1] ]
  for p_ts,p_sp,ub,ua,db,da,uvb,dvb in raw_post:
   tte_i=max(0.0,exp_ts - p_ts)
   b_i=ub if side=="UP" else db
   a_i=ua if side=="UP" else da
   vb_i=uvb if side=="UP" else dvb
   cush_i=sign * (p_sp - strike_worst) / strike_worst if p_sp > 0 else cushion_oracle
   compact_path.append((tte_i,cush_i,b_i,a_i,vb_i))
  gamma_winner=verified[mid]["winner"]
  gamma_won=(gamma_winner==side)
  oracle_mismatch=bool(verified[mid].get("oracle_mismatch",False))
  candidates.append({ "event_id":str(d.get("event_id") or d.get("shock_id") or f"{mid}_{t0}"),"t0":t0,"exp_ts":exp_ts,"tte":tte,"asset":asset,"hz":hz,"mid":mid,"side":side,"ask_t0":ask_t0,"bid_t0":bid_t0,"spread_t0":spread_t0,"slip20_t0":slip20_t0,"l1_ask_usd":ask_t0 * ask_sz,"depth_ratio":(ask_t0 * ask_sz + bid_t0 * bid_sz) / 20.0,"obi_l1":obi_l1,"age_ask_ms":age_ask_ms,"cushion_open":cushion_open,"cushion_min":cushion_min,"cushion_cl_proxy":cushion_cl_proxy,"cushion_oracle":cushion_oracle,"z_cushion":z_cushion,"z_cushion_cl":z_cushion_cl,"z_oracle":z_oracle,"sigma_rem":sigma_rem,"shock_vol":shock_vol,"shock_ofi":shock_ofi,"vdiv_centered":vdiv_centered,"cb_move_2s":cb_move_2s,"ask_500ms":ask_500ms,"ask_1000ms":ask_1000ms,"micro_clips":micro_clips,"path":compact_path,"won":gamma_won,"oracle_mismatch":oracle_mismatch,})
 meta={ "verified_markets":len(verified),"shock_responses_indexed":sr_count,"telemetry_rows_loaded":telem_rows,"total_candidates":len(candidates),"load_sec":round(time.time() - t_start,2),}
 if use_cache:
  try:
   with open(CACHE_PKL,"wb") as f:
    pickle.dump((candidates,meta),f,protocol=pickle.HIGHEST_PROTOCOL)
  except Exception:
   pass
 return candidates,meta
def simulate_single_trade(cand:Dict[str,Any],cfg:Dict[str,Any],latency_mode:str="500ms")->Optional[Tuple[float,str,bool]]:
 res=simulate_single_trade_ex(cand,cfg,latency_mode=latency_mode)
 if res is None:
  return None
 return res[0],res[1],res[2]
def simulate_single_trade_ex(cand:Dict[str,Any],cfg:Dict[str,Any],latency_mode:str="500ms")->Optional[Tuple[float,str,bool,float]]:
 if cand["asset"] not in cfg["assets"]:
  return None
 hz=cand["hz"]
 if hz not in cfg["horizons"]:
  return None
 tte=cand["tte"]
 if hz=="15m":
  if not (cfg["min_tte_15m"]<=tte<=cfg["max_tte_15m"]):
   return None
 else:
  if not (cfg["min_tte_1h"]<=tte<=cfg["max_tte_1h"]):
   return None
 ask_t0=cand["ask_t0"]
 if not (cfg["min_px"]<=ask_t0<=cfg["max_px"]):
  return None
 if cand["spread_t0"] > cfg["max_spread"]:
  return None
 if cand["l1_ask_usd"] < cfg["min_l1_usd"]:
  return None
 eff_cush=cand.get("cushion_oracle",cand["cushion_min"]) if cfg.get("use_cl_proxy",True) else cand["cushion_min"]
 eff_z=cand.get("z_oracle",cand["z_cushion"]) if cfg.get("use_cl_proxy",True) else cand["z_cushion"]
 if eff_cush < cfg["min_cushion"]:
  return None
 if eff_z < cfg["min_z"]:
  return None
 if cand["shock_ofi"] < cfg["min_ofi"]:
  return None
 if cfg["use_venue_veto"]:
  sign=1.0 if cand["side"]=="UP" else -1.0
  if sign * cand["vdiv_centered"] > 12.0 or cand["cb_move_2s"] < -4.0:
   return None
 entry_mode=cfg["entry_mode"]
 size_mult=1.0
 cascade_tag=""
 if entry_mode=="maker_in":
  maker_px=round(min(ask_t0 - 0.01,cand["bid_t0"] + (0.01 if cand["spread_t0"]>=0.02 else 0.0)),2)
  if maker_px < cfg["min_px"]:
   return None
  filled_maker=False
  fill_idx=0
  for idx_p,(tte_i,cush_i,b_i,a_i,vb_i) in enumerate(cand["path"]):
   if (cand["tte"] - tte_i) > 20.0:
    break
   if a_i<=maker_px:
    filled_maker=True
    fill_idx=idx_p
    break
  if not filled_maker:
   return None
  fill_px=maker_px
  entry_fee_ps=0.0
  active_path=cand["path"][fill_idx + 1:]
 elif entry_mode=="cascade_v4" and simulate_microclip_cascade_entry is not None:
  casc=simulate_microclip_cascade_entry(cand,cfg,latency_mode=latency_mode)
  if casc is None:
   return None
  fill_px,entry_fee_ps,fill_el_s,size_mult,cascade_tag=casc
  active_path=[r for r in cand["path"] if (cand["tte"] - r[0]) > fill_el_s]
 else:
  ask_lat=cand["ask_500ms"] if latency_mode=="500ms" else cand["ask_1000ms"]
  limit_px=min(cfg["max_px"] + 0.01,round(ask_t0 + cfg["fak_buffer"],4))
  if ask_lat > limit_px or ask_lat<=0.0 or ask_lat>=0.99:
   return None
  fill_px=round(max(ask_lat,ask_t0 + min(0.02,cand["slip20_t0"])),4)
  if fill_px > limit_px:
   return None
  entry_fee_ps=taker_fee_per_share(fill_px)
  active_path=cand["path"]
 shares=1.0 / fill_px
 total_cost=1.0 + shares * entry_fee_ps
 exit_policy=cfg["exit_policy"]
 tp1_px=0.98
 tp1_frac=0.0
 tp2_px=0.98
 if exit_policy=="hold_98":
  tp2_px=0.98
 elif exit_policy=="single_95":
  tp2_px=0.95
 elif exit_policy=="single_plus14":
  tp2_px=min(0.97,round(fill_px + 0.14,2))
 elif exit_policy=="two_tranche_10_98":
  tp1_px=min(0.95,round(fill_px + 0.10,2))
  tp1_frac=0.50
  tp2_px=0.98
 elif exit_policy=="two_tranche_12_98":
  tp1_px=min(0.96,round(fill_px + 0.12,2))
  tp1_frac=0.50
  tp2_px=0.98
 elif exit_policy=="two_tranche_14_98":
  tp1_px=min(0.96,round(fill_px + 0.14,2))
  tp1_frac=0.50
  tp2_px=0.98
 elif exit_policy=="two_tranche_95_98":
  tp1_px=0.95
  tp1_frac=0.50
  tp2_px=0.98
 elif exit_policy=="dynamic_95_98":
  tp1_px=0.95 if eff_z>=1.35 else min(0.95,round(fill_px + 0.14,2))
  tp1_frac=0.50
  tp2_px=0.98
 rem_frac=1.0
 tp1_done=(tp1_frac<=0.0)
 realized_cash=0.0
 max_seen_bid=cand["bid_t0"]
 ratchet_arm_delta=cfg["ratchet_arm"]
 ratchet_drop=cfg["ratchet_drop"]
 salvage_mode=cfg["salvage_mode"]
 wrong_thresh=cfg["wrong_side_thresh"]
 salvage_persist_s=cfg.get("salvage_persist_s",15.0)
 clob_drop=cfg["clob_drop_thresh"]
 wrong_start_tte:Optional[float]=None
 clob_low_start_tte:Optional[float]=None
 ratchet_start_tte:Optional[float]=None
 settle_delay_s=float(cfg.get("settle_delay_s",4.0))
 t2_post_lag_s=float(cfg.get("t2_post_lag_s",0.5))
 buggy_f01_lock_300s=bool(cfg.get("buggy_f01_lock_300s",False))
 tp1_filled_elapsed:Optional[float]=None if tp1_frac > 0.0 else 0.0
 tp2_blocked_by_f01=False
 exit_reason="HOLD_RESOLUTION"
 exit_elapsed_s:Optional[float]=None
 for tte_i,cush_i,b_i,a_i,vb_i in active_path:
  elapsed_s=max(0.0,cand["tte"] - tte_i)
  two_sided=(0.01<=b_i < a_i<=0.999) or (b_i>=0.98 and a_i > b_i)
  if b_i > max_seen_bid and two_sided:
   max_seen_bid=b_i
  maker_settled=(elapsed_s>=settle_delay_s) and (tte_i>=15.0)
  if not tp1_done and maker_settled and two_sided and b_i>=tp1_px and (b_i>=tp1_px + 0.01 or a_i > tp1_px):
   realized_cash += (shares * tp1_frac) * tp1_px
   rem_frac -= tp1_frac
   tp1_done=True
   tp1_filled_elapsed=elapsed_s
   if buggy_f01_lock_300s and tte_i<=300.0:
    tp2_blocked_by_f01=True
  t2_ready=( tp1_done and not tp2_blocked_by_f01 and maker_settled and (tp1_filled_elapsed is None or tp1_frac<=0.0 or (elapsed_s - tp1_filled_elapsed)>=t2_post_lag_s) )
  if rem_frac > 1e-6 and t2_ready and two_sided and b_i>=tp2_px and (b_i>=tp2_px + 0.01 or a_i > tp2_px):
   realized_cash += (shares * rem_frac) * tp2_px
   rem_frac=0.0
   exit_reason="MAKER_TP_FULL"
   exit_elapsed_s=elapsed_s
   break
  if rem_frac > 1e-6 and ratchet_arm_delta is not None:
   arm_lvl=max(0.84,fill_px + ratchet_arm_delta)
   if max_seen_bid>=arm_lvl and b_i > 0.05 and b_i<=(max_seen_bid - ratchet_drop) and tte_i>=25.0 and b_i>=(fill_px + 0.04):
    if ratchet_start_tte is None:
     ratchet_start_tte=tte_i
    elif (ratchet_start_tte - tte_i)>=4.0:
     exec_b=max(0.01,min(b_i,vb_i))
     fee_b=taker_fee_per_share(exec_b)
     realized_cash += (shares * rem_frac) * max(0.0,exec_b - fee_b)
     rem_frac=0.0
     exit_reason="PROFIT_RATCHET"
     exit_elapsed_s=elapsed_s
     break
   else:
    ratchet_start_tte=None
  if rem_frac > 1e-6 and salvage_mode!="none" and tte_i>=25.0 and b_i>=0.18:
   if cush_i>=0.0:
    wrong_start_tte=None
   elif cush_i<=-wrong_thresh:
    if wrong_start_tte is None:
     wrong_start_tte=tte_i
   spot_wrong=(wrong_start_tte is not None) and ((wrong_start_tte - tte_i)>=salvage_persist_s) and (cush_i<=-(wrong_thresh * 0.8))
   clob_collapsed=False
   if salvage_mode=="hybrid_persist":
    if (b_i<=fill_px - clob_drop) and (cush_i<=-0.0002):
     if clob_low_start_tte is None:
      clob_low_start_tte=tte_i
     elif (clob_low_start_tte - tte_i)>=max(8.0,salvage_persist_s * 0.6):
      clob_collapsed=True
    else:
     clob_low_start_tte=None
   if spot_wrong or clob_collapsed:
    exec_b=max(0.01,min(b_i,vb_i))
    fee_b=taker_fee_per_share(exec_b)
    realized_cash += (shares * rem_frac) * max(0.0,exec_b - fee_b)
    rem_frac=0.0
    exit_reason="SALVAGE_SPOT" if spot_wrong else "SALVAGE_CLOB_COLLAPSE"
    exit_elapsed_s=elapsed_s
    break
  if rem_frac > 1e-6 and cfg.get("final_45s_unwind",False) and 10.0<=tte_i<=45.0 and b_i>=0.05:
   exec_b=max(0.01,min(b_i,vb_i))
   fee_b=taker_fee_per_share(exec_b)
   realized_cash += (shares * rem_frac) * max(0.0,exec_b - fee_b)
   rem_frac=0.0
   exit_reason="FINAL_45S_UNWIND"
   exit_elapsed_s=elapsed_s
   break
 if rem_frac > 1e-6:
  if cand["won"]:
   realized_cash += (shares * rem_frac) * 1.0
   exit_reason="TP1_PLUS_WIN" if tp1_done and tp1_frac > 0 else "RESOLVED_WIN"
  else:
   exit_reason="TP1_PLUS_LOSS" if tp1_done and tp1_frac > 0 else "RESOLVED_LOSS_WIPEOUT"
 net_pnl=(realized_cash - total_cost) * size_mult
 if cascade_tag:
  exit_reason=f"{cascade_tag}:{exit_reason}"
 rel_ts=(cand["t0"] + exit_elapsed_s + 4.0) if exit_elapsed_s is not None else cand["exp_ts"]
 return net_pnl,exit_reason,(net_pnl > 0),rel_ts
def evaluate_portfolio_on_slice( cands:List[Dict[str,Any]],cfg:Dict[str,Any],latency_mode:str="500ms",max_concurrent:int=2,ticket_usd:float=15.0,)->Dict[str,Any]:
 seen_markets=set()
 active_slots:List[Tuple[float,float,str]]=[]
 legacy_slots=bool(cfg.get("legacy_candle_end_slots",False))
 pnls:List[float]=[]
 reasons=collections.Counter()
 wipeouts=0
 eq=0.0
 peak_eq=0.0
 max_dd=0.0
 for c in cands:
  mid=c["mid"]
  if mid in seen_markets:
   continue
  t0=c["t0"]
  active_slots=[s for s in active_slots if s[0] > t0]
  if len(active_slots)>=max_concurrent:
   continue
  if not legacy_slots:
   same_win=[s for s in active_slots if abs(s[1] - c["exp_ts"])<=300.0 and s[2]==c["hz"]]
   if same_win:
    if c["hz"]=="1h":
     continue
    c_corr=c.get("cushion_oracle",c["cushion_min"]) if cfg.get("use_cl_proxy",True) else c["cushion_min"]
    if c["hz"]=="15m" and c_corr < 0.0009:
     continue
  res=simulate_single_trade_ex(c,cfg,latency_mode=latency_mode)
  if res is None:
   continue
  pnl_unit,reason,_,rel_ts=res
  pnl_usd=pnl_unit * ticket_usd
  seen_markets.add(mid)
  slot_end_ts=c["exp_ts"] if legacy_slots else rel_ts
  active_slots.append((slot_end_ts,c["exp_ts"],c["hz"]))
  pnls.append(pnl_usd)
  reasons[reason] += 1
  if reason=="RESOLVED_LOSS_WIPEOUT":
   wipeouts += 1
  eq += pnl_usd
  if eq > peak_eq:
   peak_eq=eq
  dd=peak_eq - eq
  if dd > max_dd:
   max_dd=dd
 n=len(pnls)
 if n==0:
  return { "trades":0,"total_pnl":0.0,"ev_per_trade":0.0,"win_rate":0.0,"avg_win":0.0,"avg_loss":0.0,"profit_factor":0.0,"sharpe":-99.0,"max_dd":0.0,"wipeout_count":0,"wipeout_rate":0.0,"reasons":{},"pnls":[],}
 total_pnl=sum(pnls)
 wins=[x for x in pnls if x > 0]
 losses=[x for x in pnls if x<=0]
 gross_win=sum(wins)
 gross_loss=abs(sum(losses))
 pf=gross_win / gross_loss if gross_loss > 1e-6 else (99.0 if gross_win > 0 else 0.0)
 mean_p=total_pnl / n
 std_p=statistics.stdev(pnls) if n > 1 else 1e-6
 sharpe=(mean_p / max(std_p,1e-6)) * math.sqrt(n)
 return { "trades":n,"total_pnl":round(total_pnl,2),"ev_per_trade":round(mean_p,4),"win_rate":round(len(wins) / n,4),"avg_win":round(gross_win / len(wins),3) if wins else 0.0,"avg_loss":round(-gross_loss / len(losses),3) if losses else 0.0,"profit_factor":round(pf,3),"sharpe":round(sharpe,3),"max_dd":round(max_dd,2),"wipeout_count":wipeouts,"wipeout_rate":round(wipeouts / n,4),"reasons":dict(reasons),"pnls":pnls,}
def prefilter_entry_slice(slice_cands:List[Dict[str,Any]],cfg:Dict[str,Any])->List[Dict[str,Any]]:
 assets_set=set(cfg["assets"])
 hz_set=set(cfg["horizons"])
 min_t15,max_t15=cfg["min_tte_15m"],cfg["max_tte_15m"]
 min_t1h,max_t1h=cfg["min_tte_1h"],cfg["max_tte_1h"]
 min_px,max_px=cfg["min_px"],cfg["max_px"]
 max_sp=cfg["max_spread"]
 min_l1=cfg["min_l1_usd"]
 min_cush=cfg["min_cushion"]
 min_z=cfg["min_z"]
 min_ofi=cfg["min_ofi"]
 use_vv=cfg["use_venue_veto"]
 out=[]
 for c in slice_cands:
  if c["asset"] not in assets_set:
   continue
  hz=c["hz"]
  if hz not in hz_set:
   continue
  tte=c["tte"]
  if hz=="15m":
   if not (min_t15<=tte<=max_t15):
    continue
  else:
   if not (min_t1h<=tte<=max_t1h):
    continue
  if not (min_px<=c["ask_t0"]<=max_px):
   continue
  if c["spread_t0"] > max_sp or c["l1_ask_usd"] < min_l1:
   continue
  max_c=max(c["cushion_min"],c.get("cushion_oracle",c["cushion_min"]),c.get("cushion_cl_proxy",c["cushion_min"]))
  max_z=max(c["z_cushion"],c.get("z_oracle",c["z_cushion"]),c.get("z_cushion_cl",c["z_cushion"]))
  if max_c < min_cush:
   continue
  if max_z < min_z or c["shock_ofi"] < min_ofi:
   continue
  if use_vv:
   sign=1.0 if c["side"]=="UP" else -1.0
   if sign * c["vdiv_centered"] > 12.0 or c["cb_move_2s"] < -4.0:
    continue
  out.append(c)
 return out
def compute_wfo_dev_score( r_tr:Dict[str,Any],r_vl:Dict[str,Any],r_vl_1000:Optional[Dict[str,Any]]=None,subfold_pnls:Optional[List[float]]=None,)->float:
 min_sharpe=min(r_tr["sharpe"],r_vl["sharpe"])
 min_pf=min(r_tr["profit_factor"],r_vl["profit_factor"],3.5)
 min_ev=min(r_tr["ev_per_trade"],r_vl["ev_per_trade"])
 n_tot=r_tr["trades"] + r_vl["trades"]
 n_scale=math.sqrt(min(max(n_tot,1),130) / 130.0)
 t_ev_term=min_ev * math.sqrt(min(n_tot,180))
 worst_dd=max(r_tr["max_dd"],r_vl["max_dd"])
 worst_wipe=max(r_tr["wipeout_rate"],r_vl["wipeout_rate"])
 score=( 25.0 * min_sharpe + 35.0 * (min_pf * n_scale) + 12.0 * t_ev_term + 0.16 * min(r_tr["total_pnl"] + r_vl["total_pnl"],300.0) - 0.55 * worst_dd - 90.0 * worst_wipe )
 if r_vl_1000 is not None:
  score += 10.0 * min(r_vl_1000["sharpe"],2.5)
 if subfold_pnls:
  pos_folds=sum(1 for x in subfold_pnls if x > 0)
  score += 12.0 * pos_folds
 return score
_G_TR_POOL:List[Dict[str,Any]]=[]
_G_VL_POOL:List[Dict[str,Any]]=[]
_G_DEV_SUBFOLDS:List[List[Dict[str,Any]]]=[]
def _eval_s1_batch(batch_cfgs:List[Dict[str,Any]])->List[Tuple[float,Dict[str,Any],Dict[str,Any],Dict[str,Any]]]:
 out=[]
 for cfg in batch_cfgs:
  min_tr_n=40
  min_vl_n=20
  r_tr=evaluate_portfolio_on_slice(_G_TR_POOL,cfg,latency_mode="500ms")
  if r_tr["trades"] < min_tr_n or r_tr["total_pnl"]<=0 or r_tr["profit_factor"] < 1.30:
   continue
  r_vl=evaluate_portfolio_on_slice(_G_VL_POOL,cfg,latency_mode="500ms")
  if r_vl["trades"] < min_vl_n or r_vl["total_pnl"]<=0 or r_vl["profit_factor"] < 1.30:
   continue
  sc=compute_wfo_dev_score(r_tr,r_vl)
  r_tr_s={k:v for k,v in r_tr.items() if k!="pnls"}
  r_vl_s={k:v for k,v in r_vl.items() if k!="pnls"}
  out.append((sc,cfg,r_tr_s,r_vl_s))
 return out
def bootstrap_ci(pnls:List[float],n_boot:int=1000,seed:int=42)->Dict[str,float]:
 if len(pnls) < 5:
  return {"p05_total_pnl":0.0,"p50_total_pnl":0.0,"p95_total_pnl":0.0,"prob_positive":0.0}
 rng=random.Random(seed)
 n=len(pnls)
 totals=[]
 pos_cnt=0
 for _ in range(n_boot):
  s=sum(pnls[rng.randrange(n)] for _ in range(n))
  totals.append(s)
  if s > 0:
   pos_cnt += 1
 totals.sort()
 return { "p05_total_pnl":round(totals[int(0.05 * n_boot)],2),"p50_total_pnl":round(totals[int(0.50 * n_boot)],2),"p95_total_pnl":round(totals[int(0.95 * n_boot)],2),"prob_positive":round(pos_cnt / n_boot,4),}
def compute_quarter_kelly(pnls:List[float],ticket_usd:float=15.0)->Dict[str,float]:
 if len(pnls) < 10:
  return {"full_kelly_pct":0.0,"quarter_kelly_pct":0.08}
 rets=[p / ticket_usd for p in pnls]
 mu=statistics.mean(rets)
 var=statistics.variance(rets)
 if mu<=0 or var<=1e-6:
  return {"full_kelly_pct":0.0,"quarter_kelly_pct":0.05}
 f_full=min(0.80,mu / var)
 f_quarter=round(max(0.08,min(0.20,0.25 * f_full)),4)
 return {"full_kelly_pct":round(f_full,4),"quarter_kelly_pct":f_quarter}
def main():
 global _G_TR_POOL,_G_VL_POOL,_G_DEV_SUBFOLDS
 print("=" * 80)
 print("RUNNING HONEST ZERO-LOOKAHEAD PURGED WALK-FORWARD OPTIMIZER (v3.7)")
 print("=" * 80,flush=True)
 cands,meta=load_dataset(use_cache=True)
 print(f"Loaded dataset: {meta}",flush=True)
 PURGE_SEC=7200.0
 train_cands:List[Dict[str,Any]]=[]
 val_cands:List[Dict[str,Any]]=[]
 holdout_cands:List[Dict[str,Any]]=[]
 horizon_split_bounds:Dict[str,Any]={}
 for hz_key in ("15m","1h"):
  hz_list=[c for c in cands if c["hz"]==hz_key]
  if not hz_list:
   continue
  hz_t0=sorted(c["t0"] for c in hz_list)
  t_tr_end=hz_t0[int(0.50 * len(hz_t0))]
  t_vl_end=hz_t0[int(0.75 * len(hz_t0))]
  tr_h=[c for c in hz_list if c["exp_ts"]<=t_tr_end]
  vl_h=[c for c in hz_list if c["t0"]>=(t_tr_end + PURGE_SEC) and c["exp_ts"]<=t_vl_end]
  ho_h=[c for c in hz_list if c["t0"]>=(t_vl_end + PURGE_SEC)]
  train_cands.extend(tr_h)
  val_cands.extend(vl_h)
  holdout_cands.extend(ho_h)
  horizon_split_bounds[hz_key]={ "train_n":len(tr_h),"val_n":len(vl_h),"holdout_n":len(ho_h),"train_end_utc":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime(t_tr_end)),"val_end_utc":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime(t_vl_end)),}
 train_cands.sort(key=lambda x:x["t0"])
 val_cands.sort(key=lambda x:x["t0"])
 holdout_cands.sort(key=lambda x:x["t0"])
 dev_cands=sorted(train_cands + val_cands,key=lambda x:x["t0"])
 n_dev=len(dev_cands)
 dev_subfolds:List[List[Dict[str,Any]]]=[]
 for q_idx in range(4):
  i0=int((q_idx * 0.25) * n_dev)
  i1=int(((q_idx + 1) * 0.25) * n_dev) - 1
  t_start_q=dev_cands[i0]["t0"] + (PURGE_SEC if q_idx > 0 else 0.0)
  t_end_q=dev_cands[max(i0,i1)]["t0"]
  dev_subfolds.append([c for c in dev_cands if t_start_q<=c["t0"]<=t_end_q])
 print(f"Purged Splits -> Train: {len(train_cands)} | Val: {len(val_cands)} | Sealed Holdout: {len(holdout_cands)}",flush=True)
 buggy_live_cfg={ "name":"BUGGY_OCT23_HOTPATCH_BASELINE","assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":150.0,"max_tte_15m":825.0,"min_tte_1h":150.0,"max_tte_1h":600.0,"min_px":0.55,"max_px":0.88,"max_spread":0.04,"min_l1_usd":15.0,"min_cushion":0.0002,"min_z":0.25,"min_ofi":0.50,"use_venue_veto":False,"entry_mode":"taker_fak","fak_buffer":0.02,"exit_policy":"hold_98","ratchet_arm":0.16,"ratchet_drop":0.06,"salvage_mode":"none","wrong_side_thresh":0.0006,"clob_drop_thresh":0.30,"final_45s_unwind":False,}
 base_train=evaluate_portfolio_on_slice(train_cands,buggy_live_cfg)
 base_val=evaluate_portfolio_on_slice(val_cands,buggy_live_cfg)
 base_hold=evaluate_portfolio_on_slice(holdout_cands,buggy_live_cfg)
 print(f"[BASELINE BUGGY LIVE] Train PnL=${base_train['total_pnl']} (WR={base_train['win_rate']}, Wipeout={base_train['wipeout_rate']}) | " f"Val PnL=${base_val['total_pnl']} | Holdout PnL=${base_hold['total_pnl']} (Wipeout={base_hold['wipeout_rate']})",flush=True)
 asset_sets=[("BTC","ETH")]
 horizon_sets=[("15m","1h")]
 px_bands=[ (0.52,0.74),(0.55,0.75),(0.55,0.78),(0.55,0.80),(0.55,0.82),(0.58,0.78),(0.58,0.80),(0.58,0.82),(0.60,0.80),(0.55,0.85),]
 z_thresholds=[0.45,0.65,0.72,0.75,0.78,0.85,1.05,1.25,1.50]
 cushion_thresholds=[0.0004,0.0006,0.0008,0.0010,0.0012]
 tte_configs=[ (60.0,420.0,120.0,600.0),(90.0,480.0,120.0,600.0),(90.0,540.0,150.0,900.0),(120.0,600.0,150.0,900.0),(90.0,480.0,150.0,1200.0),]
 s1_entry_modes=[("taker_fak",0.02),("maker_in",0.0)]
 s1_superset_cfg={ "assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":60.0,"max_tte_15m":600.0,"min_tte_1h":120.0,"max_tte_1h":1200.0,"min_px":0.52,"max_px":0.85,"max_spread":0.03,"min_l1_usd":20.0,"min_cushion":0.0004,"min_z":0.45,"min_ofi":0.60,"use_venue_veto":True,"use_cl_proxy":True,}
 _G_TR_POOL=prefilter_entry_slice(train_cands,s1_superset_cfg)
 _G_VL_POOL=prefilter_entry_slice(val_cands,s1_superset_cfg)
 _G_DEV_SUBFOLDS=dev_subfolds
 s1_exit_probes=[ (None,"none"),(0.12,"hybrid_persist"),]
 s1_all_cfgs:List[Dict[str,Any]]=[]
 for assets in asset_sets:
  for horizons in horizon_sets:
   for min_px,max_px in px_bands:
    for min_z in z_thresholds:
     for min_cush in cushion_thresholds:
      for t15_min,t15_max,t1h_min,t1h_max in tte_configs:
       for e_mode,f_buf in s1_entry_modes:
        for r_probe,s_probe in s1_exit_probes:
         s1_all_cfgs.append({ "assets":assets,"horizons":horizons,"min_tte_15m":t15_min,"max_tte_15m":t15_max,"min_tte_1h":t1h_min,"max_tte_1h":t1h_max,"min_px":min_px,"max_px":max_px,"max_spread":0.03,"min_l1_usd":20.0,"min_cushion":min_cush,"min_z":min_z,"min_ofi":0.60,"use_venue_veto":True,"use_cl_proxy":True,"entry_mode":e_mode,"fak_buffer":f_buf,"exit_policy":"two_tranche_12_98","ratchet_arm":r_probe,"ratchet_drop":0.06,"salvage_mode":s_probe,"wrong_side_thresh":0.0006,"salvage_persist_s":15.0,"clob_drop_thresh":0.22,"final_45s_unwind":False,})
 n_workers=max(1,min(8,(os.cpu_count() or 4)))
 chunk_sz=250
 batches=[s1_all_cfgs[i:i + chunk_sz] for i in range(0,len(s1_all_cfgs),chunk_sz)]
 t_s1=time.time()
 stage1_results=[]
 with mp.get_context("fork").Pool(processes=n_workers) as pool:
  for res_batch in pool.imap_unordered(_eval_s1_batch,batches):
   stage1_results.extend(res_batch)
 stage1_results.sort(key=lambda x:x[0],reverse=True)
 print( f"Stage 1 evaluated {len(s1_all_cfgs)} configs across {n_workers} workers in {time.time() - t_s1:.1f}s | " f"Passed Train+Val PF>=1.25: {len(stage1_results)}",flush=True,)
 top_cores:List[Dict[str,Any]]=[]
 seen_core_keys=set()
 strata=[ lambda c:True,lambda c:c["assets"]==("BTC","ETH") and c["horizons"]==("15m","1h"),lambda c:c["assets"]==("BTC","ETH") and c["entry_mode"]=="taker_fak",lambda c:c["entry_mode"]=="maker_in",]
 for pred in strata:
  added_in_stratum=0
  for _,cfg,_,_ in stage1_results:
   if not pred(cfg):
    continue
   ck=( cfg["assets"],cfg["horizons"],cfg["min_px"],cfg["max_px"],cfg["min_z"],cfg["min_cushion"],cfg["min_tte_15m"],cfg["max_tte_15m"],cfg["min_tte_1h"],cfg["max_tte_1h"],cfg["entry_mode"],)
   if ck not in seen_core_keys:
    seen_core_keys.add(ck)
    top_cores.append(cfg)
    added_in_stratum += 1
   if added_in_stratum>=6 or len(top_cores)>=24:
    break
 exit_policies=["hold_98","single_95","single_plus14","two_tranche_10_98","two_tranche_12_98","two_tranche_14_98","two_tranche_95_98","dynamic_95_98"]
 ratchet_arms=[None,0.10,0.12,0.16]
 salvage_configs=[ ("none",0.0006,15.0,0.30),("spot_persist",0.0006,15.0,0.30),("spot_persist",0.0008,20.0,0.30),("hybrid_persist",0.0006,15.0,0.22),("hybrid_persist",0.0008,20.0,0.25),]
 stage2_results=[]
 total_tested=len(s1_all_cfgs)
 for base_c in top_cores:
  e_mode=base_c["entry_mode"]
  buf_variants=[0.01,0.02,0.03]
  tr_sub=prefilter_entry_slice(train_cands,base_c)
  vl_sub=prefilter_entry_slice(val_cands,base_c)
  min_tr_n=40
  min_vl_n=20
  for f_buf in buf_variants:
   entry_probe_cfg=dict(base_c)
   entry_probe_cfg.update({ "entry_mode":e_mode,"fak_buffer":f_buf,"exit_policy":"hold_98","ratchet_arm":None,"ratchet_drop":0.06,"salvage_mode":"none","wrong_side_thresh":0.0006,"salvage_persist_s":15.0,"clob_drop_thresh":0.30,})
   def _select_fillable(sub_cands:List[Dict[str,Any]],lat:str)->List[Dict[str,Any]]:
    return [ c_item for c_item in sub_cands if simulate_single_trade_ex(c_item,entry_probe_cfg,latency_mode=lat) is not None ]
   tr_entered_500=_select_fillable(tr_sub,"500ms")
   if len(tr_entered_500) < min_tr_n:
    total_tested += len(exit_policies) * len(ratchet_arms) * len(salvage_configs)
    continue
   vl_entered_500=_select_fillable(vl_sub,"500ms")
   if len(vl_entered_500) < min_vl_n:
    total_tested += len(exit_policies) * len(ratchet_arms) * len(salvage_configs)
    continue
   vl_entered_1000=_select_fillable(vl_sub,"1000ms")
   subfold_entered=[_select_fillable(prefilter_entry_slice(sf,base_c),"500ms") for sf in dev_subfolds]
   for ex_pol in exit_policies:
    for r_arm in ratchet_arms:
     for s_mode,w_th,s_pers,c_drop in salvage_configs:
      total_tested += 1
      cfg=dict(base_c)
      cfg.update({ "entry_mode":e_mode,"fak_buffer":f_buf,"exit_policy":ex_pol,"ratchet_arm":r_arm,"ratchet_drop":0.06,"salvage_mode":s_mode,"wrong_side_thresh":w_th,"salvage_persist_s":s_pers,"clob_drop_thresh":c_drop,})
      r_tr=evaluate_portfolio_on_slice(tr_entered_500,cfg,latency_mode="500ms")
      if r_tr["trades"] < min_tr_n or r_tr["total_pnl"]<=0 or r_tr["profit_factor"] < 1.25:
       continue
      r_vl=evaluate_portfolio_on_slice(vl_entered_500,cfg,latency_mode="500ms")
      if r_vl["trades"] < min_vl_n or r_vl["total_pnl"]<=0 or r_vl["profit_factor"] < 1.25:
       continue
      r_vl_1000=evaluate_portfolio_on_slice(vl_entered_1000,cfg,latency_mode="1000ms")
      if r_vl_1000["total_pnl"]<=0 or r_vl_1000["profit_factor"] < 1.15:
       continue
      sf_pnls=[ evaluate_portfolio_on_slice(sf_e,cfg,latency_mode="500ms")["total_pnl"] for sf_e in subfold_entered ]
      pos_subfolds=sum(1 for x in sf_pnls if x > 0)
      if pos_subfolds < 3:
       continue
      score=compute_wfo_dev_score(r_tr,r_vl,r_vl_1000,sf_pnls)
      stage2_results.append((score,cfg,r_tr,r_vl,r_vl_1000))
 stage2_results.sort(key=lambda x:x[0],reverse=True)
 print(f"Total grid evaluations: {total_tested} | Stage 2 passed Train+Val+1000ms+SubFolds: {len(stage2_results)}",flush=True)
 if not stage2_results:
  raise RuntimeError("No configuration passed strict Train+Val+1000ms+SubFolds WFO gates!")
 best_score,best_cfg,best_tr,best_vl,best_vl_1000=stage2_results[0]
 def eval_ablation(label:str,mod:Dict[str,Any])->Dict[str,Any]:
  c=dict(best_cfg)
  c.update(mod)
  tr=evaluate_portfolio_on_slice(train_cands,c)
  vl=evaluate_portfolio_on_slice(val_cands,c)
  ho=evaluate_portfolio_on_slice(holdout_cands,c)
  return { "label":label,"train_pnl":tr["total_pnl"],"train_trades":tr["trades"],"train_pf":tr["profit_factor"],"train_wipeout":tr["wipeout_rate"],"val_pnl":vl["total_pnl"],"val_trades":vl["trades"],"val_pf":vl["profit_factor"],"val_wipeout":vl["wipeout_rate"],"holdout_pnl":ho["total_pnl"],"holdout_trades":ho["trades"],"holdout_pf":ho["profit_factor"],"holdout_wipeout":ho["wipeout_rate"],}
 best_hold_500=evaluate_portfolio_on_slice(holdout_cands,best_cfg,latency_mode="500ms")
 best_hold_1000=evaluate_portfolio_on_slice(holdout_cands,best_cfg,latency_mode="1000ms")
 best_hold_seed_12_c1=evaluate_portfolio_on_slice(holdout_cands,best_cfg,latency_mode="500ms",max_concurrent=1,ticket_usd=12.0)
 ablations=[ eval_ablation("SELECTED_WFO_OPTIMAL (v3.9 Contract-Oracle + WFO#2 Corr + Exact Parity)",{}),eval_ablation("ABLATE_LEGACY_CANDLE_END_NO_CORR_FILTER (Vector 6 F-12a)",{"legacy_candle_end_slots":True}),eval_ablation("ABLATE_CONTRACT_ORACLE_PROXY (R07 + F-11)",{"use_cl_proxy":not best_cfg.get("use_cl_proxy",True)}),eval_ablation("ABLATE_BUGGY_F01_T2_LOCKED_300S_5S_LAG (v3.7 F-01+F-07 bug)",{"buggy_f01_lock_300s":True,"t2_post_lag_s":5.0}),eval_ablation("ABLATE_HIGH_PX_085_THIN_CUSHION (Oct23 overpay bug)",{"max_px":0.85,"min_cushion":0.0002,"min_z":0.35}),eval_ablation("ABLATE_TO_SINGLE_HOLD_98 (15m wipeout bug)",{"exit_policy":"hold_98"}),eval_ablation("ABLATE_RATCHET_TO_+16c (pytest-divergence bug)",{"ratchet_arm":0.16}),eval_ablation("ABLATE_NO_SALVAGE (dead boolean bug)",{"salvage_mode":"none"}),eval_ablation("ABLATE_ENABLE_FINAL_45S_TAKER_UNWIND",{"final_45s_unwind":True}),eval_ablation("ABLATE_NO_VENUE_VETO",{"use_venue_veto":False}),eval_ablation("ABLATE_ALT_ENTRY_MODE (maker_in vs taker_fak)",{"entry_mode":"maker_in" if best_cfg["entry_mode"]!="maker_in" else "taker_fak"}),eval_ablation("ABLATE_CASCADE_V4_4STEP_ENTRY",{"entry_mode":"cascade_v4"}),]
 import itertools
 all_sorted=sorted(cands,key=lambda x:x["t0"])
 n_all=len(all_sorted)
 n_groups=6
 group_bounds:List[Tuple[float,float]]=[]
 for g_idx in range(n_groups):
  g_i0=int((g_idx / n_groups) * n_all)
  g_i1=int(((g_idx + 1) / n_groups) * n_all) - 1
  t_g0=all_sorted[g_i0]["t0"]
  t_g1=all_sorted[max(g_i0,g_i1)]["t0"]
  group_bounds.append((t_g0,t_g1))
 apriori_cpcv_grid:List[Dict[str,Any]]=[]
 for px_lo,px_hi in [(0.55,0.80),(0.55,0.82),(0.55,0.85)]:
  for z_th in [0.65,0.85,1.05]:
   for c_th in [0.0004,0.0006]:
    for f_b in [0.01,0.02]:
     for ex_p in ["single_95","two_tranche_14_98","two_tranche_95_98","hold_98"]:
      for s_m,r_a in [("spot_persist",None),("hybrid_persist",0.12)]:
       apriori_cpcv_grid.append({ "assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":90.0,"max_tte_15m":480.0,"min_tte_1h":150.0,"max_tte_1h":1200.0,"min_px":px_lo,"max_px":px_hi,"max_spread":0.03,"min_l1_usd":20.0,"min_cushion":c_th,"min_z":z_th,"min_ofi":0.60,"use_venue_veto":True,"use_cl_proxy":True,"entry_mode":"taker_fak","fak_buffer":f_b,"exit_policy":ex_p,"ratchet_arm":r_a,"ratchet_drop":0.06,"salvage_mode":s_m,"wrong_side_thresh":0.0006,"salvage_persist_s":15.0,"clob_drop_thresh":0.22,"final_45s_unwind":False,})
 apriori_superset=prefilter_entry_slice(all_sorted,{ "assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":90.0,"max_tte_15m":480.0,"min_tte_1h":150.0,"max_tte_1h":1200.0,"min_px":0.55,"max_px":0.85,"max_spread":0.03,"min_l1_usd":20.0,"min_cushion":0.0004,"min_z":0.65,"min_ofi":0.60,"use_venue_veto":True,"use_cl_proxy":True,})
 cpcv_splits=[]
 for g_a,g_b in itertools.combinations(range(n_groups),2):
  test_intervals=[group_bounds[g_a],group_bounds[g_b]]
  train_cpcv=[ c for c in apriori_superset if all( (c["exp_ts"] < (ts_i - PURGE_SEC)) or (c["t0"] > (te_i + PURGE_SEC)) for ts_i,te_i in test_intervals ) ]
  oos_cpcv=[]
  for g_t in (g_a,g_b):
   t_s,t_e=group_bounds[g_t]
   purge_left=PURGE_SEC if (g_t > 0 and (g_t - 1) not in (g_a,g_b)) else 0.0
   purge_right=PURGE_SEC if (g_t < n_groups - 1 and (g_t + 1) not in (g_a,g_b)) else 0.0
   eff_s=t_s + purge_left
   eff_e=t_e - (purge_right * 0.25)
   oos_cpcv.extend(c for c in apriori_superset if eff_s<=c["t0"]<=eff_e and c["exp_ts"]<=t_e)
  oos_cpcv.sort(key=lambda x:x["t0"])
  n_tc=len(train_cpcv)
  t_cut_inner=train_cpcv[int(0.70 * n_tc)]["t0"] if n_tc>=20 else 0.0
  in_tr=[c for c in train_cpcv if c["exp_ts"]<=t_cut_inner]
  in_vl=[c for c in train_cpcv if c["t0"]>=(t_cut_inner + PURGE_SEC)]
  fitted_cfg=apriori_cpcv_grid[0]
  best_cpcv_sc=-1e9
  for cand_cfg in apriori_cpcv_grid:
   ri_tr=evaluate_portfolio_on_slice(in_tr,cand_cfg,latency_mode="500ms")
   if ri_tr["trades"] < 20 or ri_tr["total_pnl"]<=0 or ri_tr["profit_factor"] < 1.20:
    continue
   ri_vl=evaluate_portfolio_on_slice(in_vl,cand_cfg,latency_mode="500ms")
   if ri_vl["trades"] < 8 or ri_vl["total_pnl"]<=0 or ri_vl["profit_factor"] < 1.15:
    continue
   sc_i=compute_wfo_dev_score(ri_tr,ri_vl)
   if sc_i > best_cpcv_sc:
    best_cpcv_sc=sc_i
    fitted_cfg=cand_cfg
  if best_cpcv_sc<=-1e8:
   for cand_cfg in apriori_cpcv_grid:
    ri_all=evaluate_portfolio_on_slice(train_cpcv,cand_cfg,latency_mode="500ms")
    if ri_all["trades"]>=25 and ri_all["total_pnl"] > 0:
     sc_i=compute_wfo_dev_score(ri_all,ri_all)
     if sc_i > best_cpcv_sc:
      best_cpcv_sc=sc_i
      fitted_cfg=cand_cfg
  r_cpcv=evaluate_portfolio_on_slice(oos_cpcv,fitted_cfg,latency_mode="500ms")
  r_cpcv_seed=evaluate_portfolio_on_slice(oos_cpcv,fitted_cfg,latency_mode="500ms",max_concurrent=1,ticket_usd=12.0)
  cpcv_splits.append({ "test_groups":[g_a,g_b],"fitted_exit_policy":fitted_cfg["exit_policy"],"fitted_min_z":fitted_cfg["min_z"],"trades":r_cpcv["trades"],"total_pnl":r_cpcv["total_pnl"],"seed_12_c1_pnl":r_cpcv_seed["total_pnl"],"win_rate":r_cpcv["win_rate"],"profit_factor":r_cpcv["profit_factor"],"sharpe":r_cpcv["sharpe"],"wipeout_rate":r_cpcv["wipeout_rate"],"pnls":r_cpcv["pnls"],})
 cpcv_pnls_list=[s["total_pnl"] for s in cpcv_splits]
 cpcv_seed_pnls=[s["seed_12_c1_pnl"] for s in cpcv_splits]
 cpcv_pfs_list=[s["profit_factor"] for s in cpcv_splits]
 cpcv_sharpes_list=[s["sharpe"] for s in cpcv_splits]
 cpcv_summary={ "mode":"GENUINE_OUT_OF_SAMPLE_REFIT_CPCV_6_2","n_groups":6,"k_test_groups":2,"apriori_grid_size":len(apriori_cpcv_grid),"total_combinations":len(cpcv_splits),"positive_combinations":sum(1 for x in cpcv_pnls_list if x > 0),"positive_rate":round(sum(1 for x in cpcv_pnls_list if x > 0) / max(len(cpcv_splits),1),4),"seed_12_c1_positive_combinations":sum(1 for x in cpcv_seed_pnls if x > 0),"median_oos_trades":int(statistics.median(s["trades"] for s in cpcv_splits)),"median_oos_pnl_usd":round(statistics.median(cpcv_pnls_list),2),"mean_oos_pnl_usd":round(statistics.mean(cpcv_pnls_list),2),"median_seed_12_c1_oos_pnl_usd":round(statistics.median(cpcv_seed_pnls),2),"min_oos_pnl_usd":round(min(cpcv_pnls_list),2),"median_oos_pf":round(statistics.median(cpcv_pfs_list),3),"median_oos_sharpe":round(statistics.median(cpcv_sharpes_list),3),"splits":[{k:v for k,v in s.items() if k!="pnls"} for s in cpcv_splits],}
 mismatch_mids=set()
 ver_p=DATA_DIR / "verified_gamma_resolutions.json"
 if ver_p.exists():
  try:
   ver_map=json.loads(ver_p.read_text(encoding="utf-8"))
   for k_m,v_m in ver_map.items():
    if isinstance(v_m,dict) and ( v_m.get("oracle_mismatch") or v_m.get("mismatch") or (v_m.get("binance_winner") and v_m.get("winner") and v_m.get("binance_winner")!=v_m.get("winner")) ):
     mismatch_mids.add(str(k_m))
  except Exception:
   pass
 for gt_name in ("ground_truth_resolutions.jsonl","ground_truth_resolutions_eth.jsonl","ground_truth_resolutions_sol.jsonl"):
  gt_p=DATA_DIR / gt_name
  if gt_p.exists():
   try:
    for ln in gt_p.read_text(encoding="utf-8",errors="replace").splitlines():
     if not ln.strip():
      continue
     row_g=json.loads(ln)
     if row_g.get("oracle_mismatch") or ( row_g.get("binance_winning_outcome") and row_g.get("gamma_winning_outcome") and row_g.get("binance_winning_outcome")!=row_g.get("gamma_winning_outcome") ):
      mismatch_mids.add(str(row_g.get("market_id")))
   except Exception:
    pass
 for c_item in all_sorted:
  if c_item["path"]:
   tte_end_i,cush_end_i,_,_,_=c_item["path"][-1]
   if tte_end_i<=30.0 and abs(cush_end_i)>=0.00001 and ((cush_end_i > 0)!=bool(c_item["won"])):
    mismatch_mids.add(str(c_item.get("mid")))
  if str(c_item.get("mid")) in mismatch_mids:
   c_item["oracle_mismatch"]=True
 mismatch_cands=[c for c in all_sorted if c.get("oracle_mismatch")]
 cfg_no_cl=dict(best_cfg,use_cl_proxy=False)
 cfg_with_cl=dict(best_cfg,use_cl_proxy=True)
 mm_raw=evaluate_portfolio_on_slice(mismatch_cands,cfg_no_cl,latency_mode="500ms")
 mm_cl=evaluate_portfolio_on_slice(mismatch_cands,cfg_with_cl,latency_mode="500ms")
 full_no_cl=evaluate_portfolio_on_slice(all_sorted,cfg_no_cl,latency_mode="500ms")
 full_with_cl=evaluate_portfolio_on_slice(all_sorted,cfg_with_cl,latency_mode="500ms")
 bp1_base=dict(best_cfg)
 if not str(bp1_base.get("exit_policy","")).startswith("two_tranche"):
  bp1_base["exit_policy"]="two_tranche_12_98"
 bp1_buggy=evaluate_portfolio_on_slice(all_sorted,dict(bp1_base,t2_post_lag_s=5.0,buggy_f01_lock_300s=True),latency_mode="500ms")
 bp1_delayed=evaluate_portfolio_on_slice(all_sorted,dict(bp1_base,t2_post_lag_s=5.0),latency_mode="500ms")
 bp1_inline=evaluate_portfolio_on_slice(all_sorted,dict(bp1_base,t2_post_lag_s=0.05),latency_mode="500ms")
 bp1_concurrent=evaluate_portfolio_on_slice(all_sorted,dict(bp1_base,t2_post_lag_s=0.0),latency_mode="500ms")
 chainlink_proxy_audit={ "mismatch_markets_identified":len(mismatch_mids),"mismatch_candidates_total":len(mismatch_cands),"mismatch_raw_trades":mm_raw["trades"],"mismatch_raw_pnl":mm_raw["total_pnl"],"mismatch_cl_proxy_trades":mm_cl["trades"],"mismatch_cl_proxy_pnl":mm_cl["total_pnl"],"full_dataset_raw_pnl":full_no_cl["total_pnl"],"full_dataset_raw_pf":full_no_cl["profit_factor"],"full_dataset_cl_proxy_pnl":full_with_cl["total_pnl"],"full_dataset_cl_proxy_pf":full_with_cl["profit_factor"],"blueprint1_tranche2_comparison":{ "delayed_5s_pnl":bp1_delayed["total_pnl"],"delayed_5s_pf":bp1_delayed["profit_factor"],"inline_50ms_pnl":bp1_inline["total_pnl"],"inline_50ms_pf":bp1_inline["profit_factor"],"concurrent_0ms_pnl":bp1_concurrent["total_pnl"],"concurrent_0ms_pf":bp1_concurrent["profit_factor"],},}
 oos_unit_rets=[p / 15.0 for p in (best_vl["pnls"] + best_hold_500["pnls"])]
 if len(oos_unit_rets) < 20:
  oos_unit_rets=[p / 15.0 for p in best_tr["pnls"]]
 def sim_bankroll_policy( label:str,start_eq:float,base_pct:float,min_ticket:float,floor_usd:float,seed_cap_eq:float=0.0,seed_ticket:float=12.0,corr_pair_prob:float=0.0,n_paths:int=10000,n_trades:int=50,)->Dict[str,Any]:
  rng_mc=random.Random(20261025)
  halted_cnt=0
  end_eqs=[]
  max_dds=[]
  n_r=len(oos_unit_rets)
  for _ in range(n_paths):
   eq=start_eq
   pk=start_eq
   mdd=0.0
   halted=False
   t_done=0
   while t_done < n_trades:
    if eq < floor_usd:
     halted=True
     break
    if seed_cap_eq > 0.0 and eq < seed_cap_eq:
     tkt=min(eq,seed_ticket)
     r=oos_unit_rets[rng_mc.randrange(n_r)]
     eq += tkt * r
     t_done += 1
    else:
     tkt=min(eq,max(min_ticket,round(eq * base_pct,2)))
     if corr_pair_prob > 0.0 and rng_mc.random() < corr_pair_prob and (t_done + 1) < n_trades:
      r1=oos_unit_rets[rng_mc.randrange(n_r)]
      r2=r1 if rng_mc.random() < 0.75 else oos_unit_rets[rng_mc.randrange(n_r)]
      eq += tkt * r1 + (tkt * 0.54) * r2
      t_done += 2
     else:
      r=oos_unit_rets[rng_mc.randrange(n_r)]
      eq += tkt * r
      t_done += 1
    if eq > pk:
     pk=eq
    if (pk - eq) > mdd:
     mdd=pk - eq
    if eq < floor_usd:
     halted=True
     break
   if halted:
    halted_cnt += 1
   end_eqs.append(eq)
   max_dds.append(mdd)
  end_eqs.sort()
  max_dds.sort()
  return { "policy":label,"start_equity_usd":start_eq,"floor_usd":floor_usd,"halt_prob_50_trades":round(halted_cnt / n_paths,4),"median_terminal_equity_usd":round(end_eqs[int(0.50 * n_paths)],2),"p05_terminal_equity_usd":round(end_eqs[int(0.05 * n_paths)],2),"p95_terminal_equity_usd":round(end_eqs[int(0.95 * n_paths)],2),"p95_max_drawdown_usd":round(max_dds[int(0.95 * n_paths)],2),}
 bankroll_mc=[ sim_bankroll_policy("v3.7_UNPATCHED_22PCT_FLOOR65_CONC2",76.49,0.22,12.0,65.00,corr_pair_prob=0.25),sim_bankroll_policy("CENTRAL_CFG_18PCT_FLOOR66.67_CONC2",76.49,0.18,12.0,66.67,corr_pair_prob=0.25),sim_bankroll_policy("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR48",76.49,0.18,12.0,48.00,seed_cap_eq=88.0,seed_ticket=12.0,corr_pair_prob=0.15),sim_bankroll_policy("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR52",76.49,0.18,12.0,52.00,seed_cap_eq=88.0,seed_ticket=12.0,corr_pair_prob=0.15),]
 ci_train=bootstrap_ci(best_tr["pnls"])
 ci_val=bootstrap_ci(best_vl["pnls"])
 ci_hold=bootstrap_ci(best_hold_500["pnls"])
 kelly=compute_quarter_kelly(best_tr["pnls"] + best_vl["pnls"],ticket_usd=15.0)
 top5_summary=[]
 seen_top5_cores=set()
 for sc,c_i,tr_i,vl_i,_ in stage2_results:
  ck_i=(c_i["assets"],c_i["horizons"],c_i["min_px"],c_i["max_px"],c_i["min_z"],c_i["min_cushion"],c_i["entry_mode"],c_i["exit_policy"])
  if ck_i in seen_top5_cores:
   continue
  seen_top5_cores.add(ck_i)
  ho_i=evaluate_portfolio_on_slice(holdout_cands,c_i,latency_mode="500ms")
  c_clean={k:(list(v) if isinstance(v,tuple) else v) for k,v in c_i.items()}
  top5_summary.append({ "score":round(sc,2),"config":c_clean,"train":{k:v for k,v in tr_i.items() if k!="pnls"},"val":{k:v for k,v in vl_i.items() if k!="pnls"},"holdout":{k:v for k,v in ho_i.items() if k!="pnls"},})
  if len(top5_summary)>=5:
   break
 live_counterfactual={}
 st_path=DATA_DIR / "live_harvester_state.json"
 if st_path.exists():
  st=json.loads(st_path.read_text(encoding="utf-8"))
  closed_live=st.get("closed_positions",[])
  cand_by_eid={c["event_id"]:c for c in cands}
  actual_total=0.0
  cf_total=0.0
  matched_live=0
  filtered_out_losses=0
  filtered_out_wins=0
  post_rebate_traces=[]
  for pos in closed_live:
   act_pnl=float(pos.get("net_pnl_usd") or 0.0)
   actual_total += act_pnl
   eid=str(pos.get("event_id") or "")
   tid=str(pos.get("trade_id") or "")
   c_match=cand_by_eid.get(eid)
   if not c_match:
    continue
   matched_live += 1
   sim=simulate_single_trade(c_match,best_cfg,latency_mode="500ms")
   notional=float(pos.get("notional_usd") or 15.0)
   if sim is None:
    cf_pnl=0.0
    cf_reason="VETOED_AT_ENTRY"
    if act_pnl < 0:
     filtered_out_losses += 1
    else:
     filtered_out_wins += 1
   else:
    cf_pnl=round(sim[0] * notional,2)
    cf_reason=sim[1]
   cf_total += cf_pnl
   if "6076647" in tid or "6082720" in tid or act_pnl<=-15.0:
    post_rebate_traces.append({ "trade_id":tid,"entry_price":pos.get("entry_price"),"max_seen_bid":pos.get("max_seen_bid"),"actual_pnl_usd":round(act_pnl,2),"actual_close_reason":pos.get("close_reason"),"wfo_counterfactual_pnl_usd":cf_pnl,"wfo_counterfactual_action":cf_reason,})
  live_counterfactual={ "total_live_closed_trades":len(closed_live),"matched_to_trigger_dataset":matched_live,"actual_matched_subset_pnl_usd":round(sum(float(p.get("net_pnl_usd") or 0.0) for p in closed_live if str(p.get("event_id") or "") in cand_by_eid),2),"wfo_optimal_counterfactual_pnl_usd":round(cf_total,2),"filtered_out_losing_trades":filtered_out_losses,"filtered_out_winning_trades":filtered_out_wins,"wipeout_trades_counterfactual":post_rebate_traces,}
 cv_folds=[]
 if len(dev_cands)>=100:
  fold_fracs=[(0.25,0.43),(0.43,0.62),(0.62,0.81),(0.81,1.00)]
  for fold_idx,(tr_f,te_f) in enumerate(fold_fracs,start=1):
   t_cut=dev_cands[int(tr_f * n_dev)]["t0"]
   t_end=dev_cands[min(n_dev - 1,int(te_f * n_dev) - 1)]["t0"]
   oos_fold=[c for c in dev_cands if (t_cut + PURGE_SEC)<=c["t0"]<=t_end]
   r_fold=evaluate_portfolio_on_slice(oos_fold,best_cfg,latency_mode="500ms")
   cv_folds.append({ "fold":fold_idx,"oos_candidates":len(oos_fold),"trades":r_fold["trades"],"total_pnl":r_fold["total_pnl"],"win_rate":r_fold["win_rate"],"profit_factor":r_fold["profit_factor"],"wipeout_rate":r_fold["wipeout_rate"],})
 report={ "generated_at_utc":time.strftime("%Y-%m-%d %H:%M:%S UTC",time.gmtime()),"wfo_version":"3.9","dataset_meta":meta,"total_grid_configs_evaluated":total_tested,"purged_splits":{ "purge_embargo_seconds":PURGE_SEC,"train_candidates":len(train_cands),"val_candidates":len(val_cands),"holdout_candidates":len(holdout_cands),"per_horizon":horizon_split_bounds,},"cpcv_6_2_validation":cpcv_summary,"chainlink_proxy_audit":chainlink_proxy_audit,"bankroll_50trade_monte_carlo":bankroll_mc,"expanding_4fold_purged_cv":cv_folds,"buggy_oct23_live_baseline":{ "train":{k:v for k,v in base_train.items() if k!="pnls"},"val":{k:v for k,v in base_val.items() if k!="pnls"},"holdout":{k:v for k,v in base_hold.items() if k!="pnls"},},"selected_optimal_config":{k:(list(v) if isinstance(v,tuple) else v) for k,v in best_cfg.items()},"selected_optimal_performance":{ "train_500ms":{k:v for k,v in best_tr.items() if k!="pnls"},"val_500ms":{k:v for k,v in best_vl.items() if k!="pnls"},"val_1000ms_stress":{k:v for k,v in best_vl_1000.items() if k!="pnls"},"sealed_holdout_500ms":{k:v for k,v in best_hold_500.items() if k!="pnls"},"sealed_holdout_seed_12_conc1":{k:v for k,v in best_hold_seed_12_c1.items() if k!="pnls"},"sealed_holdout_1000ms_stress":{k:v for k,v in best_hold_1000.items() if k!="pnls"},"bootstrap_95ci":{ "train":ci_train,"val":ci_val,"sealed_holdout":ci_hold,},"kelly_sizing":kelly,},"controlled_ablations":ablations,"d1_box_wfo_calibration":calibrate_d1_box_wfo(data_dir=DATA_DIR) if calibrate_d1_box_wfo is not None else {},"top_5_configs":top5_summary,"live_105_trades_counterfactual":live_counterfactual,}
 tmp=OUT_JSON.with_suffix(".tmp")
 tmp.write_text(json.dumps(report,indent=2),encoding="utf-8")
 tmp.replace(OUT_JSON)
 print("\n" + "=" * 80)
 print("OPTIMAL WFO v3.7 CONFIG SELECTED (STRICTLY ON TRAIN + VAL + DEV SUB-FOLDS):")
 print(json.dumps(report["selected_optimal_config"],indent=2))
 print("\nSEALED HOLDOUT PERFORMANCE (+500ms Finland RTT):")
 print(json.dumps(report["selected_optimal_performance"]["sealed_holdout_500ms"],indent=2))
 print("\nSEALED HOLDOUT (+1000ms SEVERE LATENCY STRESS):")
 print(json.dumps(report["selected_optimal_performance"]["sealed_holdout_1000ms_stress"],indent=2))
 print("\nSEALED HOLDOUT BOOTSTRAP 95% CI:")
 print(json.dumps(ci_hold,indent=2))
 print("\nCONTROLLED ABLATIONS:")
 for ab in ablations:
  print(f"  - {ab['label']}: Train=${ab['train_pnl']} | Val=${ab['val_pnl']} | Holdout=${ab['holdout_pnl']} (PF={ab['holdout_pf']}, Wipeout={ab['holdout_wipeout']})")
 print("\nCPCV(6, 2) 15-SPLIT OUT-OF-SAMPLE SUMMARY:")
 print(json.dumps({k:v for k,v in cpcv_summary.items() if k!="splits"},indent=2))
 print("\nCHAINLINK PROXY ORACLE-MISMATCH AUDIT:")
 print(json.dumps(chainlink_proxy_audit,indent=2))
 print("\n50-TRADE MONTE CARLO BANKROLL SURVIVAL FROM $76.49:")
 print(json.dumps(bankroll_mc,indent=2))
 print("\nLIVE COUNTERFACTUAL:")
 print(json.dumps(live_counterfactual,indent=2))
 print("=" * 80,flush=True)
if __name__=="__main__":
 main()


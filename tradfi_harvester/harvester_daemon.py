import os
import sys
import time
import json
import math
import logging
import datetime
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv(os.path.expanduser('~/quant_pipeline/.env'))

STATE_FILE = os.path.expanduser("~/quant_pipeline/tradfi_harvester/harvester_state.json")
LOG_FILE = os.path.expanduser("~/quant_pipeline/tradfi_harvester/harvester.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [HARVESTER] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HarvesterDaemon")

CONFIG = {
    "network": os.getenv("HARVESTER_NETWORK", "mainnet"),
    "pairs": [
        {"id": "CRUDE", "sym_a": "xyz:CL", "sym_b": "xyz:BRENTOIL", "max_hold": 12, "notional_usd": 150.0},
        {"id": "METALS", "sym_a": "xyz:GOLD", "sym_b": "xyz:SILVER", "max_hold": 14, "notional_usd": 100.0},
    ],
    "z_entry": 2.00,
    "z_target": 0.25,
    "z_stop": 3.20,
    "friction_pct": 0.0003  # 3 bps round-trip friction
}

info = Info(constants.MAINNET_API_URL if CONFIG["network"].lower() == "mainnet" else constants.TESTNET_API_URL, skip_ws=True)

class StateManager:
    @staticmethod
    def load() -> dict:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not read state file, initializing fresh: {e}")
        return {
            "positions": {},
            "realized_pnl_usd": 0.0,
            "trade_history": []
        }

    @staticmethod
    def save(state: dict):
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

class SessionManager:
    @staticmethod
    def get_status(dt_utc: datetime.datetime):
        """Active Monday 00:00 UTC to Friday 20:30 UTC. Flat on weekends."""
        weekday = dt_utc.weekday()
        hour = dt_utc.hour
        minute = dt_utc.minute
        
        # Friday flatting trigger
        if weekday == 4 and (hour > 20 or (hour == 20 and minute >= 30)):
            return "WEEKEND_FLAT"
        if weekday in [5, 6]:
            return "WEEKEND_FLAT"
        return "ACTIVE"

class DynamicKalmanFilter:
    def __init__(self, q: float = 1e-7, r: float = 1e-3):
        self.theta = np.array([1.0, 0.0])
        self.P = np.eye(2) * 1.0
        self.R = r
        self.Q = np.eye(2) * q

    def update(self, y: float, x: float):
        H = np.array([x, 1.0])
        P_prior = self.P + self.Q
        err = y - np.dot(H, self.theta)
        S = np.dot(H, np.dot(P_prior, H.T)) + self.R
        K = np.dot(P_prior, H.T) / S
        self.theta = self.theta + K * err
        self.P = P_prior - np.outer(K, np.dot(H, P_prior))
        return self.theta[0], self.theta[1], err

def fetch_pair_data(sym_a: str, sym_b: str, lookback_hours: int = 120):
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (lookback_hours * 3600 * 1000)
    
    def get_candles(sym):
        payload = {"type": "candleSnapshot", "req": {"coin": sym, "interval": "1h", "startTime": start_ms, "endTime": now_ms}}
        return info.post("/info", payload) or []

    ca = get_candles(sym_a)
    cb = get_candles(sym_b)
    if not ca or not cb:
        return None
        
    df_a = pd.DataFrame(ca)[["t", "c"]].rename(columns={"t": "time", "c": "px_a"}).astype(float)
    df_b = pd.DataFrame(cb)[["t", "c"]].rename(columns={"t": "time", "c": "px_b"}).astype(float)
    df = pd.merge(df_a, df_b, on="time").dropna()
    df["log_a"] = np.log(df["px_a"])
    df["log_b"] = np.log(df["px_b"])
    return df

def evaluate_pair(df: pd.DataFrame):
    kf = DynamicKalmanFilter()
    betas, alphas = [], []
    for _, row in df.iterrows():
        b, a, _ = kf.update(row["log_a"], row["log_b"])
        betas.append(b)
        alphas.append(a)
        
    df["beta"] = betas
    df["alpha"] = alphas
    df["spread"] = df["log_a"] - (df["beta"] * df["log_b"] + df["alpha"])
    
    roll_mean = df["spread"].rolling(72).mean()
    roll_std = df["spread"].rolling(72).std()
    df["z_score"] = (df["spread"] - roll_mean) / roll_std
    
    latest = df.iloc[-1]
    return latest["z_score"], latest["beta"], latest["px_a"], latest["px_b"]

def process_cycle():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    status = SessionManager.get_status(now_utc)
    state = StateManager.load()
    
    logger.info(f"--- HARVESTER CYCLE: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} [Status: {status}] ---")

    # If weekend halt is active, ensure all positions are liquidated
    if status == "WEEKEND_FLAT":
        if state["positions"]:
            logger.warning("[MANDATORY FLAT] Weekend approach. Liquidating all active spread inventory.")
            for pid, pos in list(state["positions"].items()):
                logger.info(f"Closing position {pid} for weekend cash preservation.")
                del state["positions"][pid]
            StateManager.save(state)
        else:
            logger.info("Weekend window active. Holding 100% cash.")
        return

    # Evaluate each commodity pair
    for pair in CONFIG["pairs"]:
        pid = pair["id"]
        sym_a, sym_b = pair["sym_a"], pair["sym_b"]
        
        df = fetch_pair_data(sym_a, sym_b)
        if df is None or len(df) < 72:
            logger.warning(f"Insufficient data for {pid}. Skipping.")
            continue
            
        z, beta, px_a, px_b = evaluate_pair(df)
        pos = state["positions"].get(pid)
        
        logger.info(f"[{pid}] {sym_a}/${sym_b} | Z: {z:+.2f} | Beta: {beta:.4f} | Px: ${px_a:.2f} / ${px_b:.2f} | Active Pos: {bool(pos)}")

        # Case 1: No open position -> Check entry triggers
        if not pos:
            if z >= CONFIG["z_entry"]:
                logger.info(f"[{pid}] ENTRY SIGNAL: SHORT SPREAD (Short {sym_a}, Long {sym_b})")
                state["positions"][pid] = {
                    "direction": -1,
                    "entry_z": z,
                    "entry_beta": beta,
                    "entry_px_a": px_a,
                    "entry_px_b": px_b,
                    "bars_held": 0,
                    "notional": pair["notional_usd"]
                }
            elif z <= -CONFIG["z_entry"]:
                logger.info(f"[{pid}] ENTRY SIGNAL: LONG SPREAD (Long {sym_a}, Short {sym_b})")
                state["positions"][pid] = {
                    "direction": 1,
                    "entry_z": z,
                    "entry_beta": beta,
                    "entry_px_a": px_a,
                    "entry_px_b": px_b,
                    "bars_held": 0,
                    "notional": pair["notional_usd"]
                }

        # Case 2: Open position active -> Check exit triggers
        else:
            pos["bars_held"] += 1
            direction = pos["direction"]
            entry_beta = pos["entry_beta"]
            
            # Calculate spread return
            ret_a = (px_a - pos["entry_px_a"]) / pos["entry_px_a"]
            ret_b = (px_b - pos["entry_px_b"]) / pos["entry_px_b"]
            spread_ret = (ret_a - (entry_beta * ret_b)) * direction - CONFIG["friction_pct"]
            pnl_usd = spread_ret * pos["notional"]

            exit_reason = None
            if direction == 1:  # Long spread
                if z >= -CONFIG["z_target"]:
                    exit_reason = "TARGET_REVERSION"
                elif z <= -CONFIG["z_stop"]:
                    exit_reason = "STOP_LOSS"
                elif pos["bars_held"] >= pair["max_hold"]:
                    exit_reason = "TIME_EXPIRATION"
            else:  # Short spread
                if z <= CONFIG["z_target"]:
                    exit_reason = "TARGET_REVERSION"
                elif z >= CONFIG["z_stop"]:
                    exit_reason = "STOP_LOSS"
                elif pos["bars_held"] >= pair["max_hold"]:
                    exit_reason = "TIME_EXPIRATION"

            if exit_reason:
                logger.info(f"[{pid}] EXIT TRIGGERED ({exit_reason}) | PnL: ${pnl_usd:+.2f} ({spread_ret * 100:+.2f}%) | Bars Held: {pos['bars_held']}")
                state["realized_pnl_usd"] += pnl_usd
                state["trade_history"].append({
                    "pair": pid,
                    "exit_reason": exit_reason,
                    "pnl_usd": round(pnl_usd, 2),
                    "bars_held": pos["bars_held"],
                    "timestamp": now_utc.isoformat()
                })
                del state["positions"][pid]
            else:
                logger.info(f"[{pid}] HOLDING SPREAD | Open PnL: ${pnl_usd:+.2f} | Bars: {pos['bars_held']}/{pair['max_hold']}")

    StateManager.save(state)

def main():
    logger.info("=== Starting Project Harvester Autonomous Engine ===")
    while True:
        try:
            process_cycle()
        except Exception as e:
            logger.error(f"Unexpected error in cycle: {e}", exc_info=True)
            
        # Align sleep until the start of next hour + 30 seconds
        now = datetime.datetime.now(datetime.timezone.utc)
        sleep_secs = 3600 - (now.minute * 60 + now.second) + 30
        logger.info(f"[SLEEP] Pausing {sleep_secs // 60}m {sleep_secs % 60}s until next hourly candle...\n")
        time.sleep(sleep_secs)

if __name__ == "__main__":
    main()

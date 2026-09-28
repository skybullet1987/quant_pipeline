"""
Automated Scheduler for Derive Tenor Probes (Bucket D2 and Bucket D3)
File: scripts/schedule_derive_probes.py

Schedules and executes:
  1. Bucket D2 Probe at 04:00 UTC (4 hours to 08:00 UTC expiry):
     - Measures theta decay vs multiplier expansion
     - Measures market maker spread defense (markup <= 30%)
  2. Bucket D3 Probe at 07:00 UTC (1 hour to 08:00 UTC expiry / terminal 0DTE):
     - Measures displayed book depth within $1,000 of spot
     - Checks if liquidity survives pin risk in the final hour
"""

import os
import sys
import time
import datetime
import subprocess

OUTPUT_DIR = "/home/skybullet1987/quant_pipeline/data/derive"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_next_schedule():
    now = datetime.datetime.now(datetime.timezone.utc)
    base_date = now.date() if now.hour < 4 else (now + datetime.timedelta(days=1)).date()
    d2_dt = datetime.datetime.combine(base_date, datetime.time(4, 0, 0), tzinfo=datetime.timezone.utc)
    d3_dt = datetime.datetime.combine(base_date, datetime.time(7, 0, 0), tzinfo=datetime.timezone.utc)
    return [
        ("D2_4h_acceleration", d2_dt),
        ("D3_1h_terminal_0dte", d3_dt)
    ]

def run_probe(label: str):
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(OUTPUT_DIR, f"audit_{label}_{timestamp_str}.log")
    
    print(f"\n[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S UTC')}] "
          f"EXECUTING SCHEDULED PROBE: {label}", flush=True)
    
    with open(log_file, "w") as out:
        out.write(f"=== SCHEDULED PROBE: {label} ({timestamp_str} UTC) ===\n\n")
        out.flush()
        
        # 1. Run BTC Audit
        print("  Running BTC probe...", flush=True)
        p_btc = subprocess.run(
            ["./venv/bin/python3", "src/derive_research/gate0_derive_rfq.py", "BTC"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            cwd="/home/skybullet1987/quant_pipeline"
        )
        out.write(p_btc.stdout + "\n\n")
        out.flush()
        
        # 2. Run ETH Audit
        print("  Running ETH probe...", flush=True)
        p_eth = subprocess.run(
            ["./venv/bin/python3", "src/derive_research/gate0_derive_rfq.py", "ETH"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            cwd="/home/skybullet1987/quant_pipeline"
        )
        out.write(p_eth.stdout + "\n\n")
        out.flush()

    print(f"[+] Completed {label}! Output saved to: {log_file}", flush=True)

def main():
    print("===============================================================================", flush=True)
    print("   DERIVE TENOR PROBE AUTONOMOUS SCHEDULER (Bucket D2 & Bucket D3)", flush=True)
    print("===============================================================================", flush=True)
    
    schedule = get_next_schedule()
    for label, target_dt in schedule:
        target_ts = target_dt.timestamp()
        target_time_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        now_ts = time.time()
        delay = target_ts - now_ts
        
        if delay > 0:
            print(f"[*] Next target: {label} at {target_time_str} UTC (Sleeping for {delay/3600.0:.2f} hours / {delay:.0f}s)...", flush=True)
            time.sleep(delay)
            run_probe(label)
        else:
            print(f"[!] Target {label} ({target_time_str} UTC) is in the past. Executing immediately...", flush=True)
            run_probe(label)
            
    print("\n[+] All scheduled tenor probes complete.", flush=True)

if __name__ == "__main__":
    main()

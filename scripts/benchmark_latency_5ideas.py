import json
import socket
import statistics
import time
import hmac
import hashlib
import base64
import httpx

print("=== 1. CLOUDFLARE POP & HTTP/2 RTT FROM KRAKEN-FINLAND ===")
with httpx.Client(http2=True, timeout=5.0) as client:
    r0 = client.get("https://clob.polymarket.com/time")
    cf_ray = r0.headers.get("cf-ray", "unknown")
    rtts = []
    for _ in range(12):
        t0 = time.perf_counter()
        client.get("https://clob.polymarket.com/time")
        rtts.append((time.perf_counter() - t0) * 1000.0)
print(f"Cloudflare cf-ray: {cf_ray}")
print(f"Warm HTTP/2 GET /time RTT (ms): min={min(rtts):.2f}, median={statistics.median(rtts):.2f}, mean={statistics.mean(rtts):.2f}, max={max(rtts):.2f}")

ips = sorted({ai[4][0] for ai in socket.getaddrinfo("clob.polymarket.com", 443, socket.AF_INET)})
for ip in ips:
    tcp_rtts = []
    for _ in range(5):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(2.0)
        t0 = time.perf_counter()
        s.connect((ip, 443))
        tcp_rtts.append((time.perf_counter() - t0) * 1000.0)
        s.close()
    print(f"  Anycast IP {ip}: TCP SYN-ACK min={min(tcp_rtts):.2f}ms, med={statistics.median(tcp_rtts):.2f}ms")

print("\n=== 2. HISTORICAL LIVE ORDER LATENCY BREAKDOWN (live_orders.jsonl) ===")
lats = []
post_only_lats = []
with open("data/polymarket/live_orders.jsonl") as f:
    for line in f:
        if not line.strip():
            continue
        d = json.loads(line)
        lat = d.get("latency_ms")
        if lat and d.get("mode") != "DRY_RUN":
            if d.get("side") == "BUY":
                lats.append(float(lat))
            elif d.get("side") == "SELL":
                post_only_lats.append(float(lat))

if lats:
    q = statistics.quantiles(lats, n=4)
    print(f"BUY Snipe Orders (n={len(lats)}): min={min(lats):.1f}ms, p25={q[0]:.1f}ms, median={statistics.median(lats):.1f}ms, p75={q[2]:.1f}ms, max={max(lats):.1f}ms")
    print(f"Last 15 BUY latencies (ms): {[round(x, 1) for x in lats[-15:]]}")
if post_only_lats:
    q2 = statistics.quantiles(post_only_lats, n=4)
    print(f"SELL Exit Orders (n={len(post_only_lats)}): min={min(post_only_lats):.1f}ms, p25={q2[0]:.1f}ms, median={statistics.median(post_only_lats):.1f}ms, p75={q2[2]:.1f}ms")

print("\n=== 3. BENCHMARKING JSON + HMAC L2 HEADER OVERHEAD (IDEA #4) ===")
dummy_body_dict = {
    "order": {
        "salt": 123456789012345,
        "maker": "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9",
        "signer": "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9",
        "taker": "0x0000000000000000000000000000000000000000",
        "tokenId": "71321045679252212594626385532706912750332728571942532289631379312455583992563",
        "makerAmount": "16500000",
        "takerAmount": "25000000",
        "expiration": "0",
        "nonce": "0",
        "feeRateBps": "700",
        "side": "BUY",
        "signatureType": 0,
        "signature": "0x" + "a" * 130,
    },
    "owner": "00000000-0000-0000-0000-000000000000",
    "orderType": "FAK",
}
secret_b64 = base64.urlsafe_b64encode(b"0" * 32).decode("ascii")
raw_secret = base64.urlsafe_b64decode(secret_b64)

N = 10000
t0 = time.perf_counter()
for _ in range(N):
    body_str = json.dumps(dummy_body_dict, separators=(",", ":"))
    ts_str = str(int(time.time()))
    msg = f"{ts_str}POST/order{body_str}".encode("utf-8")
    sig = base64.urlsafe_b64encode(hmac.new(raw_secret, msg, hashlib.sha256).digest()).decode("ascii")
t_std_us = ((time.perf_counter() - t0) / N) * 1e6

hmac_tmpl = hmac.new(raw_secret, digestmod=hashlib.sha256)
pre_bytes = json.dumps(dummy_body_dict, separators=(",", ":")).encode("utf-8")
t0 = time.perf_counter()
for _ in range(N):
    ts_str = str(int(time.time()))
    h = hmac_tmpl.copy()
    h.update(f"{ts_str}POST/order".encode("ascii"))
    h.update(pre_bytes)
    sig = base64.urlsafe_b64encode(h.digest()).decode("ascii")
t_opt_us = ((time.perf_counter() - t0) / N) * 1e6
print(f"Standard json.dumps + HMAC per order: {t_std_us:.2f} microseconds ({t_std_us/1000:.4f} ms)")
print(f"Pre-encoded bytes + HMAC copy per order: {t_opt_us:.2f} microseconds ({t_opt_us/1000:.4f} ms)")

print("\n=== 4. END-TO-END TRIGGER (t0_unix) TO HARVESTER WAKEUP & CLOB ACK ===")
import re
from datetime import datetime, timezone

triggers = {}
with open("data/polymarket/live_shock_triggers.jsonl") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            m = str(d.get("market_id"))
            t0 = float(d.get("t0_unix", 0))
            triggers.setdefault(m, []).append(t0)
        except Exception:
            pass

with open("data/polymarket/live_harvester_stdout.log") as f:
    lines = f.readlines()[-4000:]

qual_ts_by_mkt = {}
for line in lines:
    if "[QUALIFIED OPPORTUNITY]" in line:
        m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) UTC\]", line)
        if m:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S,%f").replace(tzinfo=timezone.utc)
            qual_ts_by_mkt["last"] = dt.timestamp()
    if "LATENCY TELEMETRY" in line and "HARVESTER" in line:
        m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) UTC\].*\[(LIVE_(\d+)_(\d+)_[A-Z]+)\] LATENCY TELEMETRY: (.*)", line)
        if m:
            dt_str, tid, mid, t_sec, tele = m.groups()
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S,%f").replace(tzinfo=timezone.utc)
            ack_unix = dt.timestamp()
            q_unix = qual_ts_by_mkt.get("last", ack_unix)
            cand_t0s = [t for t in triggers.get(mid, []) if abs(t - ack_unix) < 5.0 and t <= ack_unix]
            if cand_t0s:
                t0 = max(cand_t0s)
                ipc_and_gates_ms = (q_unix - t0) * 1000.0
                e2e_ms = (ack_unix - t0) * 1000.0
                print(f"{tid}: ipc+gates={ipc_and_gates_ms:.1f}ms | e2e_t0_to_ack={e2e_ms:.1f}ms | {tele}")


#!/usr/bin/env python3
with open("monitor_live_telemetry.py", "r") as f:
    code = f.read()

# Replace deprecated utcnow and utcfromtimestamp
code = code.replace("from datetime import datetime, timedelta", "from datetime import datetime, timedelta, timezone")
code = code.replace("datetime.utcnow()", "datetime.now(timezone.utc)")
code = code.replace("datetime.utcfromtimestamp(f[\"time\"] / 1000.0)", "datetime.fromtimestamp(f[\"time\"] / 1000.0, timezone.utc)")

with open("monitor_live_telemetry.py", "w") as f:
    f.write(code)

print("[SUCCESS] Patched monitor_live_telemetry.py datetime methods.")

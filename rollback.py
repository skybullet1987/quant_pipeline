#!/usr/bin/env python3
import json
import os

MANIFEST = "models/manifest.json"

if not os.path.exists(MANIFEST):
    print(f"[ERROR] {MANIFEST} not found.")
    exit(1)

with open(MANIFEST, "r") as f:
    m = json.load(f)

curr = m.get("active_version")
prev = m.get("previous_version")

if not prev:
    print(f"[INFO] Active version is '{curr}'. No previous version available for rollback.")
    exit(0)

m["active_version"] = prev
m["previous_version"] = curr

with open(MANIFEST, "w") as f:
    json.dump(m, f, indent=2)

print(f"[SUCCESS] Swapped active model version:")
print(f"  • Previous: {curr}")
print(f"  • Active  : {prev}")

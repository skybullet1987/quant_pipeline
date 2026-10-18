import json
import hashlib
from pathlib import Path

journal_path = Path("/home/skybullet1987/quant_pipeline/data/papertrade_journal.jsonl")
backup_path = Path("/home/skybullet1987/quant_pipeline/data/papertrade_journal.jsonl.bak")

# Read all entries
entries = []
with open(journal_path, "r") as f:
    for line in f:
        line = line.strip()
        if line:
            entries.append(json.loads(line))

print(f"Read {len(entries)} entries from {journal_path}")

# Re-sequence and re-hash
last_hash = "0" * 64
repaired_entries = []

for idx, entry in enumerate(entries, 1):
    ev_type = entry.get("event_type")
    payload = entry.get("payload", {})
    ts_ms = entry.get("timestamp_ms")
    schema_ver = entry.get("schema_version", 2)
    
    envelope = {
        "event_id": idx,
        "event_type": ev_type,
        "timestamp_ms": ts_ms,
        "payload": payload,
        "prev_hash": last_hash,
        "schema_version": schema_ver,
    }
    envelope_bytes = json.dumps(envelope, sort_keys=True).encode("utf-8")
    computed_hash = hashlib.sha256(envelope_bytes).hexdigest()
    
    repaired_entry = {
        "event_id": idx,
        "event_type": ev_type,
        "timestamp_ms": ts_ms,
        "payload": payload,
        "prev_hash": last_hash,
        "schema_version": schema_ver,
        "hash": computed_hash,
    }
    repaired_entries.append(repaired_entry)
    last_hash = computed_hash

with open(journal_path, "w") as f:
    for entry in repaired_entries:
        f.write(json.dumps(entry) + "\n")

print(f"Successfully repaired {len(repaired_entries)} entries in {journal_path}")

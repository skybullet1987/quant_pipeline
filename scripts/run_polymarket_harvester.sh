#!/usr/bin/env bash
# Supervisor for the Polymarket live harvester (Round 10 P1-05).
#  - Non-zero exit (crash)        -> restart after exponential backoff (startup reconciliation re-runs on every boot).
#  - Exit 0 (circuit breaker / intentional halt) -> stay down; a human must review.
#  - >5 crashes within 10 minutes -> stay down (crash loop; do not hammer the exchange).
#  - Persistent crash history across supervisor restarts in supervisor_crash_history.json.
set -u
cd "$(dirname "$0")/.."
LOG=data/polymarket/live_harvester_supervisor.log
CRASH_FILE=data/polymarket/supervisor_crash_history.json
mkdir -p data/polymarket

load_recent_crashes() {
  local now=$1
  local recent=()
  if [ -f "$CRASH_FILE" ]; then
    # Extract numeric timestamps from JSON array or line-delimited file
    for t in $(grep -oE '[0-9]{10,}' "$CRASH_FILE" 2>/dev/null || true); do
      if [ -n "$t" ] && [ $((now - t)) -lt 600 ] && [ $((now - t)) -ge 0 ]; then
        recent+=("$t")
      fi
    done
  fi
  echo "${recent[@]:-}"
}

save_crashes() {
  local arr=($@)
  local json="["
  local first=1
  for t in "${arr[@]:-}"; do
    if [ -n "$t" ]; then
      if [ $first -eq 0 ]; then json="$json, "; fi
      json="$json$t"
      first=0
    fi
  done
  json="$json]"
  echo "$json" > "${CRASH_FILE}.tmp" && mv -f "${CRASH_FILE}.tmp" "$CRASH_FILE"
}

while true; do
  echo "[$(date -u +%FT%TZ)] starting harvester: $*" >> "$LOG"
  venv/bin/python src/polymarket_research/polymarket_live_harvester.py "$@"
  rc=$?
  now=$(date +%s)
  if [ "$rc" -eq 0 ]; then
    echo "[$(date -u +%FT%TZ)] harvester exited cleanly (rc=0, intentional halt). Not restarting." >> "$LOG"
    save_crashes ""
    exit 0
  fi

  read -r -a recent <<< "$(load_recent_crashes "$now")"
  recent+=("$now")
  save_crashes "${recent[@]}"

  crash_count=${#recent[@]}
  if [ "$crash_count" -gt 5 ]; then
    echo "[$(date -u +%FT%TZ)] CRASH LOOP: $crash_count crashes in 10 min (last rc=$rc). Supervisor giving up." >> "$LOG"
    exit "$rc"
  fi

  # Exponential backoff: 15s, 30s, 60s, 120s (max 120s)
  shift=$(( crash_count - 1 ))
  if [ "$shift" -gt 3 ]; then shift=3; fi
  backoff=$(( 15 * (1 << shift) ))
  if [ "$backoff" -gt 120 ]; then backoff=120; fi

  echo "[$(date -u +%FT%TZ)] harvester CRASHED rc=$rc; restart #$crash_count in ${backoff}s (exponential backoff)" >> "$LOG"
  sleep "$backoff"
done

#!/usr/bin/env bash
# Owner Safe Stop / Resume Control for PAA Autonomous Operating System (`scripts/paa_emergency_stop.sh`)
# Usage:
#   ./scripts/paa_emergency_stop.sh                 # Stops ALL PAA autonomous AI timers & workers (leaves live CLOB order risk management running)
#   ./scripts/paa_emergency_stop.sh --all           # Stops ALL PAA autonomous timers AND gracefully stops live/shadow trading services
#   ./scripts/paa_emergency_stop.sh --resume        # Clears PAA_MASTER_STOP and resumes all PAA autonomous schedules
set -euo pipefail

REPO_DIR="/home/skybullet1987/quant_pipeline"
PY="${REPO_DIR}/venv/bin/python"
MODE="${1:---autonomy-only}"

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"

if [[ "${MODE}" == "--resume" ]]; then
    sudo systemctl enable --now paa-system-supervisor.timer || true
    "${PY}" "${REPO_DIR}/scripts/paa_cli.py" resume
    exit 0
fi

sudo systemctl stop paa-system-supervisor.timer || true
if [[ "${MODE}" == "--all" ]]; then
    "${PY}" "${REPO_DIR}/scripts/paa_cli.py" emergency-stop --include-trading --reason "Owner invoked paa_emergency_stop.sh --all"
else
    "${PY}" "${REPO_DIR}/scripts/paa_cli.py" emergency-stop --reason "Owner invoked paa_emergency_stop.sh (autonomy halted, live order management preserved)"
fi

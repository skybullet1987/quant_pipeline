#!/usr/bin/env bash
# ==============================================================================
# QUANT PIPELINE SYSTEMD USER SERVICE SUPERVISOR & RUNNER (v1.0)
# ==============================================================================

set -e

SERVICES=(
    "apex-perp"
    "exp104-hedge"
    "ratchet-shadow"
    "exp201a-telemetry"
    "polymarket-recorder"
    "polymarket-trader"
)

SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
PIPELINE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
    echo "Usage: $0 {status|install|enable|start|stop|restart|logs} [service-name]"
    echo ""
    echo "Services managed:"
    for s in "${SERVICES[@]}"; do
        echo "  - $s"
    done
    exit 1
}

cmd="${1:-status}"
target_service="$2"

case "$cmd" in
    install)
        echo "Installing systemd unit files to ${SYSTEMD_USER_DIR}..."
        mkdir -p "${SYSTEMD_USER_DIR}"
        for s in "${SERVICES[@]}"; do
            cp "${PIPELINE_ROOT}/systemd/${s}.service" "${SYSTEMD_USER_DIR}/"
            echo "  [+] Installed ${s}.service"
        done
        systemctl --user daemon-reload
        echo "Systemd user daemon reloaded successfully."
        ;;

    enable)
        echo "Enabling automated on-boot restart for all services..."
        for s in "${SERVICES[@]}"; do
            systemctl --user enable "$s"
            echo "  [+] Enabled ${s}"
        done
        ;;

    status)
        echo "================================================================================"
        echo "                      QUANT PIPELINE SERVICE STATUS AUDIT                       "
        echo "================================================================================"
        for s in "${SERVICES[@]}"; do
            if systemctl --user is-active --quiet "$s" 2>/dev/null; then
                status_str="ACTIVE (RUNNING)"
            else
                status_str="INACTIVE / STOPPED"
            fi
            printf "Service: %-25s | Status: %s\n" "$s" "$status_str"
        done
        echo "================================================================================"
        echo "Active Background Python PIDs:"
        ps aux | grep -E "python.*(apex|ratchet|polymarket|exp104|exp201)" | grep -v grep || echo "  (None)"
        echo "================================================================================"
        ;;

    start)
        if [ -n "$target_service" ]; then
            systemctl --user start "$target_service"
            echo "Started $target_service."
        else
            for s in "${SERVICES[@]}"; do
                systemctl --user start "$s"
                echo "Started $s."
            done
        fi
        ;;

    stop)
        if [ -n "$target_service" ]; then
            systemctl --user stop "$target_service"
            echo "Stopped $target_service."
        else
            for s in "${SERVICES[@]}"; do
                systemctl --user stop "$s"
                echo "Stopped $s."
            done
        fi
        ;;

    restart)
        if [ -n "$target_service" ]; then
            systemctl --user restart "$target_service"
            echo "Restarted $target_service."
        else
            for s in "${SERVICES[@]}"; do
                systemctl --user restart "$s"
                echo "Restarted $s."
            done
        fi
        ;;

    logs)
        if [ -z "$target_service" ]; then
            echo "Please specify a service to tail logs for:"
            for s in "${SERVICES[@]}"; do
                echo "  $0 logs $s"
            done
            exit 1
        fi
        journalctl --user -u "$target_service" -f -n 50
        ;;

    *)
        usage
        ;;
esac

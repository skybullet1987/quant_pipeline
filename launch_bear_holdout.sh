#!/usr/bin/env bash
set -e

SESSION_NAME="bear_holdout"
LOG_FILE="$HOME/quant_pipeline/bear_holdout.log"

tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
rm -f "$LOG_FILE"

tmux new-session -d -s "$SESSION_NAME" "bash -c 'source $HOME/quant_pipeline/venv/bin/activate && python3 -u $HOME/quant_pipeline/src/backtest/run_institutional_bear_holdout.py > $LOG_FILE 2>&1'"

echo "=================================================================="
echo " [TMUX] Bear market holdout job started in session: '$SESSION_NAME'"
echo " [LOG]  Writing output directly to: $LOG_FILE"
echo "=================================================================="
echo "Monitor safely with:   tail -f -n 25 $LOG_FILE"
echo "Attach to tmux with:   tmux attach -t $SESSION_NAME"
echo "=================================================================="

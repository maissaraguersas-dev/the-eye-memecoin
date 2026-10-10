#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# THE EYE — Alert Dispatch Cron Job
# Runs every 60 minutes to flush the alert queue
# ═══════════════════════════════════════════════════════════════════════════

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/alert-dispatch.log"

mkdir -p "$LOG_DIR"

if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

cd "$PROJECT_DIR" || exit 1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] alert-dispatch started" >> "$LOG_FILE"

"$PYTHON" "$PROJECT_DIR/main.py" dispatch-alerts >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] alert-dispatch FAILED (exit=$EXIT_CODE)" >> "$LOG_FILE"
else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] alert-dispatch completed" >> "$LOG_FILE"
fi

exit $EXIT_CODE

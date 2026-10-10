#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# THE EYE — Social Scan Cron Job
# Runs every 10 minutes to scan social sentiment
# ═══════════════════════════════════════════════════════════════════════════

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/social-scan.log"

mkdir -p "$LOG_DIR"

if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

cd "$PROJECT_DIR" || exit 1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] social-scan started" >> "$LOG_FILE"

"$PYTHON" "$PROJECT_DIR/main.py" scan --source social --mode auto >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] social-scan FAILED (exit=$EXIT_CODE)" >> "$LOG_FILE"
else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] social-scan completed" >> "$LOG_FILE"
fi

exit $EXIT_CODE

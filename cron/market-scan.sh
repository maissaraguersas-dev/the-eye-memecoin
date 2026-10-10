#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# THE EYE — Market Scan Cron Job
# Runs every 15 minutes to scan market data and detect manipulation
# ═══════════════════════════════════════════════════════════════════════════

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/market-scan.log"

mkdir -p "$LOG_DIR"

if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

cd "$PROJECT_DIR" || exit 1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] market-scan started" >> "$LOG_FILE"

"$PYTHON" "$PROJECT_DIR/main.py" scan-market >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] market-scan FAILED (exit=$EXIT_CODE)" >> "$LOG_FILE"
else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] market-scan completed" >> "$LOG_FILE"
fi

exit $EXIT_CODE

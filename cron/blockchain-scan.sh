#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# THE EYE — Blockchain Scan Cron Job
# Runs every 5 minutes to scan on-chain whale movements
# ═══════════════════════════════════════════════════════════════════════════

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/blockchain-scan.log"

mkdir -p "$LOG_DIR"

# Use venv Python (falls back to system python3 if venv missing)
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

cd "$PROJECT_DIR" || exit 1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] blockchain-scan started" >> "$LOG_FILE"

"$PYTHON" "$PROJECT_DIR/main.py" scan --chain eth --mode auto >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] blockchain-scan FAILED (exit=$EXIT_CODE)" >> "$LOG_FILE"
else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] blockchain-scan completed" >> "$LOG_FILE"
fi

exit $EXIT_CODE

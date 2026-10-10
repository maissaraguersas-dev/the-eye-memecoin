#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# THE EYE — 24/7 Monitoring Setup
# Sets up cron jobs for continuous market monitoring
# ═══════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_DIR/.venv/bin/python"

echo "🐋👁️  THE EYE — Setting up 24/7 monitoring..."
echo ""

# Check venv exists
if [ ! -f "$PYTHON" ]; then
    echo "⚠️  Virtual environment not found. Setting up..."
    cd "$PROJECT_DIR"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e . -q
    echo "✅ venv created"
fi

# Make cron scripts executable
chmod +x "$PROJECT_DIR/cron/"*.sh 2>/dev/null

echo ""
echo "Choose your 24/7 setup method:"
echo ""
echo "  1) CRON JOBS (recommended) — runs scans on a schedule"
echo "     Each scan type runs at its own interval:"
echo "       • Blockchain scan: every 5 min"
echo "       • Social scan:    every 10 min"
echo "       • Market scan:    every 15 min"
echo "       • Temporal scan:  every 30 min"
echo "       • Alert dispatch: every 60 min"
echo ""
echo "  2) CONTINUOUS MONITOR — runs in a screen/tmux session"
echo "     Full scan cycle every 60 seconds, 24/7"
echo ""
echo "  3) BOTH — cron for scheduled scans + screen for live monitor"
echo ""

read -p "Enter choice [1/2/3] (default: 1): " CHOICE
CHOICE=${CHOICE:-1}

case $CHOICE in
    1|3)
        echo ""
        echo "Setting up cron jobs..."
        # Install crontab
        (crontab -l 2>/dev/null | grep -v "the-eye-memecoin/cron"; cat "$PROJECT_DIR/cron/the-eye-cron") | crontab -
        echo "✅ Cron jobs installed. View with: crontab -l"
        echo "   View logs: tail -f $PROJECT_DIR/logs/*.log"
        ;;
esac

case $CHOICE in
    2|3)
        echo ""
        echo "Starting continuous monitor in screen session..."
        if command -v screen &>/dev/null; then
            screen -dmS the-eye "$PYTHON" "$PROJECT_DIR/main.py" monitor
            echo "✅ Monitor started in screen session 'the-eye'"
            echo "   Attach:  screen -r the-eye"
            echo "   Detach:  Ctrl+A then D"
            echo "   Stop:    screen -S the-eye -X quit"
        elif command -v tmux &>/dev/null; then
            tmux new-session -d -s the-eye "$PYTHON $PROJECT_DIR/main.py monitor"
            echo "✅ Monitor started in tmux session 'the-eye'"
            echo "   Attach:  tmux attach -t the-eye"
            echo "   Detach:  Ctrl+B then D"
            echo "   Stop:    tmux kill-session -t the-eye"
        else
            echo "⚠️  Neither screen nor tmux found. Running in foreground..."
            echo "   (Press Ctrl+C to stop)"
            "$PYTHON" "$PROJECT_DIR/main.py" monitor
        fi
        ;;
esac

echo ""
echo "🐋👁️  24/7 setup complete!"
echo ""
echo "Useful commands:"
echo "  opencode status          — check system status"
echo "  opencode danger-window   — check current time risk"
echo "  opencode scan-market     — run a manual full scan"
echo "  opencode monitor         — live continuous monitoring"
echo "  crontab -l               — view scheduled jobs"

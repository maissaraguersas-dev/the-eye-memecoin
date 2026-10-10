#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# THE EYE — Memecoin Pattern Recognition System
# One-command setup for OpenCode agents
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCODE_DIR="$PROJECT_DIR/.opencode"

echo "═════════════════════════════════════════════════════════════════"
echo "  THE EYE — Setting up OpenCode agents..."
echo "═════════════════════════════════════════════════════════════════"
echo ""

# ─── 1. Create .opencode directory structure ─────────────────────────────────
echo "[1/5] Creating .opencode directory structure..."
mkdir -p "$OPENCODE_DIR/agents"
mkdir -p "$OPENCODE_DIR/commands"
mkdir -p "$OPENCODE_DIR/skills"
mkdir -p "$OPENCODE_DIR/config"
echo "  ✓ Directory structure created"

# ─── 2. Copy agent configs ──────────────────────────────────────────────────
echo "[2/5] Setting up agent configurations..."

# Whale Tracker Agent
cat > "$OPENCODE_DIR/agents/whale-tracker.md" << 'AGENT_EOF'
# Whale Tracker Agent
Monitors on-chain whale wallets and matches against historical profiles.
- Trigger: New large transaction detected
- Pattern: sniper, accumulate_pump_dump, diamond_hands, failed_whale
- Output: WhaleMatch with confidence score and recommendations
AGENT_EOF

# Rug Detector Agent
cat > "$OPENCODE_DIR/agents/rug-detector.md" << 'AGENT_EOF'
# Rug Detector Agent
Monitors developer wallets and contracts for rug pull signatures.
- Trigger: New token deployment or dev wallet activity
- Pattern: soft_rug, hard_rug, honey_pot, team_wallet_cluster
- Output: DevMatch with rug_probability and urgency
AGENT_EOF

# Pump Detector Agent
cat > "$OPENCODE_DIR/agents/pump-detector.md" << 'AGENT_EOF'
# Pump Detector Agent
Detects coordinated artificial pumps and bot networks.
- Trigger: Suspicious volume/price movement
- Pattern: bot_army, wash_trading, volume_price_divergence, social_manipulation
- Output: ManipulationResult with fake_pump_score
AGENT_EOF

# Temporal Scanner Agent
cat > "$OPENCODE_DIR/agents/temporal-scanner.md" << 'AGENT_EOF'
# Temporal Scanner Agent
Analyzes time-of-day and day-of-week patterns for risk prediction.
- Trigger: Periodic (every 30 min) or on-demand
- Pattern: rug_hour, fomo_peak, dead_zone, weekend_trap, golden_hour
- Output: TemporalRiskResult with risk_score and recommendations
AGENT_EOF

# Alert Dispatcher Agent
cat > "$OPENCODE_DIR/agents/alert-dispatcher.md" << 'AGENT_EOF'
# Alert Dispatcher Agent
Formats and dispatches alerts to all configured channels.
- Trigger: New alert from any detection agent
- Channels: Telegram, Discord, local notification, log file
- Output: DispatchResult per channel
AGENT_EOF

echo "  ✓ 5 agent configurations created"

# ─── 3. Copy commands ────────────────────────────────────────────────────────
echo "[3/5] Setting up commands..."

cat > "$OPENCODE_DIR/commands/scan.md" << 'CMD_EOF'
# /scan <token_address> [chain]
Run a full scan pipeline on a token address across all detection modules.
CMD_EOF

cat > "$OPENCODE_DIR/commands/watch.md" << 'CMD_EOF'
# /watch <token_address> <chain>
Add a token to the 24/7 watchlist for continuous monitoring.
CMD_EOF

cat > "$OPENCODE_DIR/commands/unwatch.md" << 'CMD_EOF'
# /unwatch <token>
Remove a token from the watchlist.
CMD_EOF

cat > "$OPENCODE_DIR/commands/status.md" << 'CMD_EOF'
# /status
Show current monitoring status, watchlist, and active alerts.
CMD_EOF

cat > "$OPENCODE_DIR/commands/temporal.md" << 'CMD_EOF'
# /temporal
Show current temporal risk analysis and active danger windows.
CMD_EOF

echo "  ✓ 5 commands created"

# ─── 4. Copy skills ─────────────────────────────────────────────────────────
echo "[4/5] Setting up skills..."

cat > "$OPENCODE_DIR/skills/pattern-recognition.md" << 'SKILL_EOF'
# Pattern Recognition Skill
Identifies memecoin trading patterns from on-chain data.
Matches wallets against historical whale profiles and rug signatures.
SKILL_EOF

cat > "$OPENCODE_DIR/skills/risk-scoring.md" << 'SKILL_EOF'
# Risk Scoring Skill
Computes composite risk scores from whale, rug, pump, and temporal signals.
SKILL_EOF

echo "  ✓ 2 skills created"

# ─── 5. Verify all files ────────────────────────────────────────────────────
echo "[5/5] Verifying installation..."

REQUIRED_FILES=(
    "$OPENCODE_DIR/agents/whale-tracker.md"
    "$OPENCODE_DIR/agents/rug-detector.md"
    "$OPENCODE_DIR/agents/pump-detector.md"
    "$OPENCODE_DIR/agents/temporal-scanner.md"
    "$OPENCODE_DIR/agents/alert-dispatcher.md"
    "$OPENCODE_DIR/commands/scan.md"
    "$OPENCODE_DIR/commands/watch.md"
    "$OPENCODE_DIR/commands/unwatch.md"
    "$OPENCODE_DIR/commands/status.md"
    "$OPENCODE_DIR/commands/temporal.md"
    "$OPENCODE_DIR/skills/pattern-recognition.md"
    "$OPENCODE_DIR/skills/risk-scoring.md"
)

MISSING=0
for f in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
        echo "  ✗ MISSING: $f"
        MISSING=$((MISSING + 1))
    fi
done

if [[ $MISSING -eq 0 ]]; then
    echo "  ✓ All 12 files present"
else
    echo "  ✗ $MISSING file(s) missing!"
    exit 1
fi

# ─── Done ────────────────────────────────────────────────────────────────────
echo ""
echo "═════════════════════════════════════════════════════════════════"
echo "  ✓ OpenCode setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Review agents in .opencode/agents/"
echo "    2. Run: python main.py scan --token <address>"
echo "    3. Set up 24/7 monitoring: bash scripts/setup-24-7.sh"
echo "    4. Configure alerts: python scripts/telegram-bot-setup.py"
echo "═════════════════════════════════════════════════════════════════"

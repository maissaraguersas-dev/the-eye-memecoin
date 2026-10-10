# THE EYE — Complete Usage Guide

> **Memecoin Pattern Recognition System v1.0.0**
>
> Predictive intelligence engine for memecoin markets.
> 100% Free. 24/7 Autonomous. Zero API Keys Required.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [CLI Commands Reference](#cli-commands-reference)
4. [Data Sources (All Free)](#data-sources-all-free)
5. [24/7 Autonomous Monitoring](#247-autonomous-monitoring)
6. [Alert Configuration](#alert-configuration)
7. [Pattern Recognition Details](#pattern-recognition-details)
8. [Self-Improvement System](#self-improvement-system)
9. [Project Architecture](#project-architecture)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Usage](#advanced-usage)

---

## Quick Start

```bash
# 1. Clone/enter the project directory
cd the-eye-memecoin

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run your first scan
python main.py scan --token PEPE --address 0x6982508159220719284f3a0

# 4. Check if current time is dangerous
python main.py danger-window

# 5. Add a token to 24/7 monitoring
python main.py add-watchlist --token DOGE --chain eth

# 6. Check system status
python main.py status
```

---

## Installation

### Prerequisites
- Python 3.9+
- `requests` library (the only dependency)

### Install Steps

```bash
# 1. Navigate to the project
cd the-eye-memecoin

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. (Optional) Set up environment variables
cp .env.example .env
# Edit .env to add optional API keys for higher rate limits

# 4. (Optional) Set up alert dispatch channels
python scripts/telegram-bot-setup.py    # Free Telegram alerts
python scripts/discord-webhook-setup.py # Free Discord alerts

# 5. Verify installation
python main.py --version
# Output: THE EYE v1.0.0

python main.py status
# Should show all data sources as OK
```

### Optional API Keys (All Free, But Provide Higher Rate Limits)

| Key | How to Get | Benefit |
|-----|-----------|---------|
| `ETHERSCAN_API_KEY` | etherscan.io → API | 5 calls/sec → 100 calls/sec |
| `COINGECKO_DEMO_KEY` | coingecko.com → API | 30 calls/min → 500 calls/min |
| `BIRDEYE_API_KEY` | birdeye.so → API | Solana data access |
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram | Alert dispatch |
| `DISCORD_WEBHOOK_URL` | Discord server settings | Alert dispatch |

**Without any keys, the system still works 100%. Keys just improve rate limits.**

---

## CLI Commands Reference

### `scan` — Full Token Analysis

Runs the complete analysis pipeline: blockchain data → social signals → market data → all pattern matchers → analysis engines → alert generation.

```bash
python main.py scan --token PEPE --address 0x6982508159220719284f3a0 --chain eth
python main.py scan --token BONK --chain solana
python main.py scan --token DOGE --json    # Machine-readable output
```

**Options:**
- `--token TOKEN` (required) — Token symbol or name
- `--address ADDRESS` — Contract address (improves accuracy)
- `--chain CHAIN` — `eth` or `solana` (default: `eth`)
- `--json` — Output as JSON instead of formatted text
- `--verbose` / `-v` — Debug logging

**Output includes:**
- Rug pull probability with urgency classification
- Whale activity analysis with trading recommendations
- Fake pump detection with timing predictions
- Temporal danger window assessment
- Combined confidence score

---

### `whale-watch` — Track a Whale Wallet

Monitors a specific wallet against historical whale behavior patterns.

```bash
python main.py whale-watch --wallet 0x4a2b8c1d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b --chain eth
```

**Options:**
- `--wallet WALLET` (required) — Wallet address to track
- `--chain CHAIN` — `eth` or `solana` (default: `eth`)

**Patterns detected:**
- 🐋 Sniper — Buys within 0-5 min of launch
- 💎 Diamond Hands — Holds through dumps
- 📉 Failed Whale — Inverse signal (buys tops, sells bottoms)
- 🔄 Copy-Trader — Mirrors known successful whale
- 🏦 Liquidity Migration — Moves between DEXes
- 🌉 Bridge Movement — Cross-chain transfers

---

### `rug-check` — Rug Pull Probability

Analyzes a contract's deployer and code for rug pull indicators.

```bash
python main.py rug-check --address 0x9f1d2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e --chain eth
```

**Options:**
- `--address ADDRESS` (required) — Contract or deployer address
- `--chain CHAIN` — `eth` or `solana` (default: `eth`)

**Indicators checked:**
| Indicator | Rug Probability Bonus |
|-----------|---------------------|
| No liquidity lock | +30% |
| Dev holds >30% supply | +25% |
| Fresh dev wallet (<14 days) | +20% |
| Known serial rugger | +40% |
| Social 100% bot-driven | +15% |
| No social presence | +10% |
| Liquidity lock <30 days | +15% |

**Urgency classification:**
- 🚨 **CRITICAL** — Liquidity removal detected → EXIT IMMEDIATELY
- ⚠️ **HIGH** — Dev → CEX deposit → EXIT WITHIN 1 HOUR
- 🔵 **MEDIUM** — Suspicious patterns → REDUCE POSITION 50%
- 🟢 **LOW** — Not conclusive → SET ALERTS, MONITOR

---

### `pump-scan` — Detect Fake Pump

Determines if a price spike is organic or coordinated bot activity.

```bash
python main.py pump-scan --token PEPE2 --address 0xabc123...
```

**Fake pump indicators:**
- >70% wallets created <3 days ago
- >80% buy / <20% sell ratio (unnatural)
- Volume-price divergence >2σ
- Social mentions 90%+ from bot accounts
- 0 organic TikTok/Reddit presence
- Dev wallet selling during pump

**Output example:**
```
⚠️  FAKE PUMP DETECTED — 94% confidence
WHO:   Bot network (47 wallets, avg age: 3.2 days)
WHAT:  $PEPE2 up 300% in 2 hours. Artificial volume spike.
WHEN:  Peak ETA: 2-3 hours. Collapse: -70% within 6 hours.
HOW:   DO NOT FOMO. If holding: TAKE PROFITS NOW.
```

---

### `danger-window` — Temporal Risk Scan

Analyzes current time against historical attack patterns to identify high-risk windows.

```bash
python main.py danger-window
```

**Temporal windows:**
| Window | UTC Time | Risk Level | Action |
|--------|----------|------------|--------|
| 🚨 Rug Hour | 02:00-05:00 | 78% of rugs happen here | No new entries |
| 🎯 Sniper Window | Launch + 0-5min | Bot dominance 90% | Avoid at launch |
| 😱 FOMO Peak | 18:00-22:00 | Price peak → overnight dump | Take profits |
| 💀 Dead Zone | 08:00-12:00 | Lowest liquidity | Wider stop-losses |
| 🎰 Weekend Trap | Fri 20:00-Mon 08:00 | More scams, less moderation | Reduce positions |
| ✨ Golden Hour | 14:00-16:00 | Best liquidity | Optimal entry |

---

### `add-watchlist` / `remove-watchlist` / `list-watchlist`

Manage tokens under 24/7 autonomous monitoring.

```bash
# Add a token to monitoring
python main.py add-watchlist --token PEPE --address 0x6982... --chain eth --interval 15

# List all monitored tokens
python main.py list-watchlist

# Remove a token from monitoring
python main.py remove-watchlist --token PEPE
```

**Options:**
- `--token TOKEN` (required) — Token symbol
- `--address ADDRESS` — Contract address
- `--chain CHAIN` — `eth` or `solana` (default: `eth`)
- `--interval MINUTES` — Scan interval in minutes (default: 15)

---

### `status` — System Health Check

Shows the health of all data sources, watchlist state, alert queue, and prediction accuracy.

```bash
python main.py status
```

**Output includes:**
- All data source health (DexScreener, Etherscan, Solscan, etc.)
- Watchlist token count and scan schedule
- Alert queue stats (pending, dispatched, failed)
- Prediction accuracy over last 30 days
- Workflow state (last scan times)

---

### `monitor` — Start 24/7 Continuous Monitoring

Starts the autonomous monitoring loop with scheduled scans.

```bash
python main.py monitor                # Default 60-second check interval
python main.py monitor --interval 30  # Check every 30 seconds
```

**Default monitoring schedule:**
| Job | Interval | Purpose |
|-----|----------|---------|
| blockchain-scan | Every 5 min | Scan on-chain data for watchlist tokens |
| social-scan | Every 10 min | Scan social signals |
| market-scan | Every 15 min | Fetch market data |
| temporal-scan | Every 30 min | Check danger windows |
| alert-dispatch | Every 60 min | Flush pending alerts to channels |

Press `Ctrl+C` for graceful shutdown. All state is persisted, so monitoring resumes where it left off on restart.

---

### `dispatch-alerts` — Flush Alert Queue

Manually dispatch all pending alerts to configured channels.

```bash
python main.py dispatch-alerts
```

---

### `backtest` — Evaluate Prediction Accuracy

Shows how accurate the system's predictions have been over a time period.

```bash
python main.py backtest              # Last 30 days
python main.py backtest --days 7     # Last 7 days
```

---

## Data Sources (All Free)

### Blockchain Data

| Source | Rate Limit | Coverage | Cost |
|--------|-----------|----------|------|
| **DexScreener** | Unlimited | All DEXes (Uniswap, Raydium, etc.) | **Free** |
| **Blockchair** | ~30 req/min | Ethereum mainnet | **Free** |
| **Etherscan Free** | 5 calls/sec | Ethereum contracts & wallets | **Free** |
| **Solscan Free** | ~10 req/min | Solana tokens & wallets | **Free** |
| **Pump.fun** | ~20 req/min | Solana memecoin launches | **Free** |
| **Public RPCs** | Varies | Ethereum & Solana RPC | **Free** |
| **GeckoTerminal** | ~30 req/min | DEX analytics | **Free** |

### Social Data

| Source | Rate Limit | Coverage | Cost |
|--------|-----------|----------|------|
| **Nitter** | Varies | Twitter/X search (5 instances rotated) | **Free** |
| **Reddit JSON API** | ~60 req/min | Crypto subreddits | **Free** |
| **Telegram Bot API** | ~30 msg/sec | Group monitoring | **Free** |
| **Discord Webhooks** | ~5 req/sec | Server notifications | **Free** |
| **TikTok** | Best effort | Organic video search | **Free** |

### Market Data

| Source | Rate Limit | Coverage | Cost |
|--------|-----------|----------|------|
| **CoinGecko Free** | 10-30 calls/min | Prices, volume, market cap | **Free** |
| **DexScreener** | Unlimited | Real-time DEX pairs | **Free** |
| **Birdeye Free** | ~10 req/min | Solana token data | **Free** |
| **GeckoTerminal** | ~30 req/min | Trending DEX pools | **Free** |

**Total cost: $0/month. Compare to $200-1000/month for paid alternatives.**

---

## 24/7 Autonomous Monitoring

### Method 1: Built-in Monitor Command

```bash
# Start continuous monitoring (runs until Ctrl+C)
python main.py monitor

# With custom check interval
python main.py monitor --interval 30
```

### Method 2: Cron Jobs

```bash
# Set up cron jobs
bash scripts/setup-24-7.sh

# Or manually install cron entries from cron/the-eye-cron
crontab cron/the-eye-cron
```

### Method 3: Systemd Service (Linux)

```ini
# /etc/systemd/system/the-eye.service
[Unit]
Description=THE EYE Memecoin Monitor
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/the-eye-memecoin
ExecStart=/usr/bin/python3 main.py monitor
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable the-eye
sudo systemctl start the-eye
```

### Method 4: Screen/Tmux

```bash
# Using screen
screen -dmS the-eye python main.py monitor
screen -r the-eye  # Attach to view

# Using tmux
tmux new -d -s the-eye "python main.py monitor"
tmux attach -t the-eye  # Attach to view
```

### State Persistence

All monitoring state persists across restarts:

| File | Purpose |
|------|---------|
| `WORKFLOW_STATE.md` | Current tasks, last scan times |
| `src/data/watchlist.json` | Tokens under monitoring |
| `src/data/alert_queue.json` | Pending alerts buffer |
| `src/data/prediction_log.json` | All predictions for accuracy tracking |
| `src/data/learning_db.json` | Confirmed patterns (self-improving) |

When the system restarts, it reads these files and resumes exactly where it left off.

---

## Alert Configuration

### Telegram Alerts (Free)

```bash
# Interactive setup
python scripts/telegram-bot-setup.py

# Manual setup:
# 1. Message @BotFather on Telegram → /newbot → get token
# 2. Get your chat_id (message the bot, then check /getUpdates)
# 3. Edit .env:
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

### Discord Alerts (Free)

```bash
# Interactive setup
python scripts/discord-webhook-setup.py

# Manual setup:
# 1. Server Settings → Integrations → Webhooks → New Webhook
# 2. Copy webhook URL
# 3. Edit .env:
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Alert Format

Every alert follows the WHO/WHAT/WHY/WHEN/HOW/CONFIDENCE/URGENCY format:

```
🚨 CRITICAL RUG PULL ALERT — 96% confidence
WHO:   Deployer 0x9f1d...a3b (Label: "Serial Rugger #14")
WHAT:  Liquidity NOT locked. Dev wallet funded from known rug wallet.
WHY:   Matches "Soft Rug → Hard Rug" signature.
WHEN:  Exit window: 54-66 hours.
HOW:   DO NOT BUY. If holding: EXIT IMMEDIATELY.
```

---

## Pattern Recognition Details

### Whale Patterns (7 patterns)

1. **Sniper** — Buys within 0-5 min of launch, sells at +30-200%. Confidence: 60-95%
2. **Accumulate → Pump → Dump** — Stealth buys 2-6h, hype spike, dump 1-3h. Confidence: 55-90%
3. **Copy-Trader** — Mirrors known whale with 5-15 min delay. Confidence: 50-80%
4. **Diamond Hands** — Holds through dumps, never sells >20%. Confidence: 45-75%
5. **Failed Whale** — Buys tops, sells bottoms (INVERSE SIGNAL). Confidence: 40-70%
6. **Liquidity Migration** — Moves from DEX A to DEX B before pump. Confidence: 55-85%
7. **Bridge Movement** — Cross-chain movement before major event. Confidence: 50-80%

### Rug Signatures (7 signatures)

1. **Soft Rug** — Gradual sell 24-72h, never pulls liquidity. Base probability: 65%
2. **Hard Rug** — Removes 100% liquidity in single tx. Base probability: 85%
3. **Honey Pot** — Allows buys, blocks sells. Base probability: 90%
4. **Migration Scam** — v2 announcement, drains v1. Base probability: 75%
5. **Ownership Renounce Fake** — Retains upgrade proxy. Base probability: 70%
6. **Serial Rugger** — 3+ rug history, fresh wallets. Base probability: 80%
7. **Team Wallet Cluster** — 5-10 wallets from same source. Base probability: 72%

### Manipulation Patterns (7 patterns)

1. **Bot Army** — 20+ wallets same day, funded from 1-3 sources
2. **Wash Trading** — Circular buy/sell to inflate volume
3. **Volume-Price Divergence** — Price up but real volume doesn't support
4. **Social Manipulation** — 50K+ Twitter, 95% bots, 0 organic
5. **Holder Inflation** — 10K holders but 80% bot wallets
6. **Influencer Paid Pump** — Sudden spike after paid tweet
7. **Exchange Listing Fake-Out** — Rumor → bot pump → dev dump

---

## Self-Improvement System

THE EYE learns from its predictions to improve over time:

### How It Works

1. **Prediction Logging** — Every prediction is saved with timestamp, confidence, and outcome
2. **Outcome Tracking** — Predictions are marked as confirmed/rejected when actual outcomes are known
3. **Confidence Calibration** — The ConfidenceEngine adjusts future predictions based on past accuracy
4. **Pattern Database** — Confirmed patterns are added to the learning database
5. **Temporal Updates** — Confirmed rug observations update the temporal patterns database

### Updating Predictions

```python
# In Python code
from src.analysis.prediction import PredictionGenerator

generator = PredictionGenerator()
generator.evaluate_prediction("pred-abc123", was_correct=True)
```

### Viewing Accuracy

```bash
python main.py backtest --days 30
```

---

## Project Architecture

```
the-eye-memecoin/
├── main.py                    ← CLI entry point
├── AGENTS.md                  ← Project instructions
├── opencode.json              ← OpenCode configuration
├── WORKFLOW_STATE.md          ← Shared state
├── requirements.txt           ← Python dependencies
├── .env.example               ← Environment template
│
├── src/
│   ├── main.py                ← CLI implementation (12 subcommands)
│   ├── monitors/              ← Data fetchers
│   │   ├── blockchain.py      ← Free on-chain data (7 sources)
│   │   ├── social.py          ← Free social scraping (5 sources)
│   │   └── market.py          ← Free market data (4 sources)
│   ├── pattern/               ← Pattern matching engines
│   │   ├── whale_matcher.py   ← 7 whale behavior patterns
│   │   ├── dev_matcher.py     ← 7 rug pull signatures
│   │   ├── manipulation_detector.py ← 7 manipulation patterns
│   │   └── temporal_analyzer.py     ← 6 temporal windows
│   ├── analysis/              ← Analysis engines
│   │   ├── rug_probability.py ← Multi-signal rug calculator
│   │   ├── pump_scorer.py     ← Viral/moon potential scorer
│   │   ├── confidence.py      ← Recency × frequency weighting
│   │   └── prediction.py      ← Timing + magnitude forecasts
│   ├── alerts/                ← Alert system
│   │   ├── formatter.py       ← WHO/WHAT/WHY/WHEN/HOW formatter
│   │   └── dispatcher.py      ← Telegram/Discord/local dispatch
│   ├── autonomous/            ← 24/7 autonomous operation
│   │   ├── cron_scheduler.py  ← Monitoring schedule
│   │   ├── state_manager.py   ← Persistent state
│   │   ├── watchlist_manager.py ← Token CRUD
│   │   └── alert_queue.py     ← Alert buffering
│   └── data/                  ← JSON databases & cache
│       ├── whale_profiles.json
│       ├── dev_signatures.json
│       ├── manipulation_patterns.json
│       ├── temporal_patterns.json
│       ├── watchlist.json
│       ├── alert_queue.json
│       ├── prediction_log.json
│       ├── learning_db.json
│       └── dispatch_config.json
│
├── tests/                     ← 110 tests, 100% passing
├── scripts/                   ← Setup & management scripts
├── cron/                      ← Cron job definitions
├── docs/                      ← Documentation
└── .opencode/                 ← Agent & command configs
    ├── agents/ (17 agents)
    ├── commands/ (9 commands)
    └── skills/ (1 skill group)
```

---

## Troubleshooting

### Common Issues

**"No module named 'src.xxx'"**
→ Run commands from the project root directory: `cd the-eye-memecoin`

**"Rate limited by Etherscan"**
→ The system auto-retries with alternative sources. Get a free API key at etherscan.io for higher limits.

**"Nitter instances down"**
→ The system auto-rotates through 5 instances. If all fail, social data is unavailable but other analysis continues.

**"Telegram alerts not sending"**
→ Run `python scripts/telegram-bot-setup.py` to verify your bot token and chat ID.

**"Watchlist not persisting"**
→ Check that `src/data/` is writable. The system saves state after every operation.

**"Tests failing"**
→ Run `python -m pytest tests/ -v` to see detailed error output. Ensure you're in the project root.

### Debug Mode

```bash
# Enable debug logging
python main.py scan --token PEPE --verbose

# Check all source health
python main.py status
```

---

## Advanced Usage

### Python API (Programmatic Access)

```python
import sys
sys.path.insert(0, '/path/to/the-eye-memecoin')

from src.monitors.blockchain import BlockchainMonitor
from src.pattern.whale_matcher import WhaleMatcher
from src.pattern.dev_matcher import DevMatcher
from src.analysis.rug_probability import RugProbabilityEngine
from src.alerts.formatter import AlertFormatter

# Initialize components
blockchain = BlockchainMonitor()
whale_matcher = WhaleMatcher()
dev_matcher = DevMatcher()
rug_engine = RugProbabilityEngine(dev_matcher, whale_matcher)
formatter = AlertFormatter()

# Analyze a token on-chain
on_chain = blockchain.analyze_token("0x...", chain="eth")

# Check rug probability
rug_result = rug_engine.calculate(
    token="TOKEN",
    token_address="0x...",
    chain="eth",
    on_chain_data=on_chain,
    social_signals=None,
    market_data=None
)

# Format and dispatch alert
if rug_result.urgency in ("HIGH", "CRITICAL"):
    alert = formatter.format_rug_alert(rug_result, token="TOKEN", chain="eth")
    print(formatter.to_text(alert))
```

### Updating Databases

```bash
# Add a known whale to the database
python scripts/update-whale-db.py --wallet 0x... --label "Whale Alpha" --chain eth --pattern sniper

# Add a known rugger to the database
python scripts/update-dev-db.py --wallet 0x... --label "Serial Rugger" --rug-count 5 --chain eth

# Mark a developer as honest
python scripts/update-dev-db.py --wallet 0x... --label "Verified Dev" --honest
```

### Custom Scan Intervals

```bash
# Scan every 5 minutes for high-priority tokens
python main.py add-watchlist --token PEPE --interval 5

# Scan every 60 minutes for low-priority tokens
python main.py add-watchlist --token DOGE --interval 60
```

### JSON Output (For Automation)

```bash
# Get machine-readable output
python main.py scan --token PEPE --json > pepe_analysis.json
python main.py danger-window --json > current_risk.json
```

---

## License

MIT License — Use freely, trade wisely, never trust a memecoin dev who doesn't lock liquidity.

**Built for the 99% scam rate. Designed for the 1% that moon. 🐋👁️**

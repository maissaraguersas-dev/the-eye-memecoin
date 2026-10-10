# 🐋👁️ THE EYE — Memecoin Market Intelligence Engine

**Monitors the ENTIRE memecoin market across all chains. Not your portfolio.**

THE EYE is a professional-grade market intelligence system that scans every memecoin across Ethereum, Solana, Base, Arbitrum, and BSC — discovering opportunities, detecting rugs, tracking whales, and alerting you in real-time. All data sources are 100% free. No API keys required.

---

## Quick Start (3 Steps)

```bash
# 1. Navigate to the project
cd /home/z/my-project/the-eye-memecoin

# 2. Run any command — it just works
opencode status          # Check system status
opencode danger-window   # Check current time-based risk
opencode scan-market     # Full market-wide scan
opencode monitor         # 24/7 continuous monitoring
```

That's it. Type `opencode` followed by any command.

---

## All Commands

| Command | What It Does |
|---------|-------------|
| `opencode` | Interactive mode — shows menu of all options |
| `opencode --version` | Show version |
| `opencode status` | System status: chains, watchlist, data sources |
| `opencode danger-window` | Current temporal risk window (rug hour, FOMO peak, etc.) |
| `opencode scan --token <ADDRESS>` | Deep scan a single token |
| `opencode scan-market` | **Full market-wide scan** — discovers + analyzes all tokens |
| `opencode rug-check --token <ADDRESS>` | Check rug probability for a token |
| `opencode pump-scan` | Scan for organic pumps vs fake pumps |
| `opencode whale-watch` | Monitor whale activity and patterns |
| `opencode monitor` | **24/7 continuous monitoring** — runs until you stop it |
| `opencode add-watchlist <TOKEN> <ADDRESS>` | Add token to watchlist |
| `opencode remove-watchlist <TOKEN>` | Remove from watchlist |
| `opencode list-watchlist` | Show watched tokens |
| `opencode dispatch-alerts` | Flush queued alerts to Telegram/Discord |
| `opencode backtest` | Run prediction accuracy backtest |

---

## 24/7 Setup — How to Run Non-Stop

### Option 1: One Command Setup (Recommended)

```bash
cd /home/z/my-project/the-eye-memecoin
bash scripts/setup-24-7.sh
```

This gives you 3 choices:
1. **Cron jobs** — each scan type runs on its own schedule (5/10/15/30/60 min intervals)
2. **Screen/tmux session** — continuous monitoring every 60 seconds
3. **Both** — cron for scheduled scans + screen for live monitor

### Option 2: Manual Cron Setup

```bash
# Install the crontab
(crontab -l 2>/dev/null; cat /home/z/my-project/the-eye-memecoin/cron/the-eye-cron) | crontab -

# View installed jobs
crontab -l

# View logs
tail -f /home/z/my-project/the-eye-memecoin/logs/*.log
```

### Option 3: Screen Session (Simple)

```bash
# Start
screen -dmS the-eye opencode monitor

# Attach to see it live
screen -r the-eye

# Detach (keeps running)
# Press Ctrl+A then D

# Stop
screen -S the-eye -X quit
```

---

## What It Monitors (Free Data Sources)

| Source | What It Provides | Chains | Cost |
|--------|-----------------|--------|------|
| **DexScreener** | Token prices, volume, liquidity, pairs, trending | ETH, SOL, Base, ARB, BSC + 20 more | Free |
| **GeckoTerminal** | Trending pools, new pool launches, OHLCV | ETH, SOL, Base, ARB, BSC | Free |
| **CoinGecko** | Market caps, trending coins, category data | All chains | Free |
| **Nitter/Twitter** | Social mentions, sentiment, bot detection | — | Free (scraped) |
| **Reddit** | Community sentiment, mention counts | — | Free (scraped) |

No API keys needed. All endpoints work out of the box.

---

## What It Detects

### 🚨 Rug Pull Detection (0–100% probability)
7 rug signatures analyzed:
1. **Soft rug** — dev slowly sells while shilling
2. **Hard rug** — sudden liquidity removal
3. **Honeypot** — can buy but can't sell
4. **Mint exploit** — hidden mint function
5. **Proxy rug** — upgradeable proxy backdoor
6. **Serial rugger** — dev has rugged before
7. **Social-only rug** — all social, no product

### 🐋 Whale Pattern Detection (7 patterns)
1. **Sniper** — buys at block 0, sells at peak
2. **Accumulate→Pump→Dump** — classic whale cycle
3. **Copy-trader** — mirrors successful wallets
4. **Diamond hands** — long-term holder (bullish signal)
5. **Failed whale** — bought top, can't exit
6. **Liquidity migration** — moving LP to new token
7. **Bridge movement** — cross-chain whale transfers

### 🎭 Manipulation Detection (7 types)
1. **Bot army** — automated buy/sell rings
2. **Wash trading** — same wallet buying and selling
3. **Volume-price divergence** — volume up but price flat (fake volume)
4. **Social manipulation** — coordinated shill campaigns
5. **Holder inflation** — sybil wallets boosting holder count
6. **Coordinated pump** — synchronized buys across wallets
7. **Spoofing** — large orders placed then cancelled

### ⏰ Temporal Windows (4 danger zones)
| Window | UTC Hours | Risk | Why |
|--------|-----------|------|-----|
| **Rug Hour** | 02:00–05:00 | 90% | Low liquidity, devs pull liquidity |
| **FOMO Peak** | 18:00–22:00 | 70% | Maximum retail activity, tops happen |
| **Dead Zone** | 08:00–12:00 | 30% | Low activity, slow drift |
| **Golden Hour** | 14:00–16:00 | 20% | Best entry window, organic growth |

### 🚀 Pump Scoring (organic vs fake)
Each token gets two scores:
- **Moon Score (0–100)** — how likely this is a real, organic pump
- **Fake Pump Score (0–100)** — how likely this is an artificial pump

### 🔮 Prediction Engine
Generates predictions with:
- **Type** — rug_imminent, pump_likely, dump_coming, accumulation
- **Timing** — when it's expected to happen
- **Magnitude** — expected price move %
- **Confidence** — 0–100% based on signal strength
- **Urgency** — low/medium/high/critical

---

## Alert System

Every alert follows the **WHO/WHAT/WHY/WHEN/HOW** framework:

```
🚨 RUG ALERT: PEPE

WHO:     Token PEPE on ETH
WHAT:    Rug probability: 82% — HIGH risk
WHY:     Dev sold 15% of supply; liquidity unlocked; serial rugger
WHEN:    NOW
HOW:     AVOID
CONF:    78%
URGENCY: CRITICAL
```

### Alert Channels (all free)
- **Terminal** — printed to console with formatting
- **Log file** — `src/data/alert_log.json`
- **Telegram** — via free bot API (setup: `python scripts/telegram-bot-setup.py`)
- **Discord** — via free webhook (setup: `python scripts/discord-webhook-setup.py`)

---

## Self-Improvement

THE EYE learns from its own predictions:
1. Every prediction is logged to `src/data/prediction_log.json`
2. After outcomes are known, accuracy is tracked
3. Pattern weights are adjusted based on hit rate
4. Over time, predictions become more accurate

Run `opencode backtest` to see prediction accuracy.

---

## Project Structure

```
the-eye-memecoin/
├── main.py                    # CLI entry point (13 commands)
├── opencode                   # Shell launcher script
├── pyproject.toml             # Package config
├── .env.example               # Optional env vars
│
├── config/
│   ├── defaults.json          # All default settings
│   └── settings.py            # Settings singleton
│
├── src/
│   ├── monitors/
│   │   ├── blockchain.py      # DexScreener, GeckoTerminal APIs
│   │   ├── market.py          # CoinGecko, market overview
│   │   └── social.py          # Twitter, Reddit sentiment
│   │
│   ├── pattern/
│   │   ├── whale_matcher.py   # 7 whale patterns
│   │   ├── dev_matcher.py     # 7 dev rug signatures
│   │   └── manipulation_detector.py  # 7 manipulation types
│   │
│   ├── analysis/
│   │   ├── rug_probability.py # 0–100% rug scoring
│   │   ├── pump_scorer.py     # Organic vs fake pump
│   │   ├── temporal_analyzer.py # Time-of-day risk
│   │   ├── confidence.py      # Signal confidence weighting
│   │   └── prediction.py      # Prediction engine + learning
│   │
│   ├── scanner/
│   │   └── market_scanner.py  # Core engine — full market scan
│   │
│   ├── alerts/
│   │   ├── formatter.py       # WHO/WHAT/WHY/WHEN/HOW alerts
│   │   └── dispatcher.py      # Telegram/Discord/terminal/log
│   │
│   ├── autonomous/
│   │   ├── cron_scheduler.py  # 24/7 job scheduler
│   │   ├── watchlist_manager.py
│   │   ├── state_manager.py
│   │   └── alert_queue.py     # Alert buffering + dispatch
│   │
│   └── data/                  # JSON databases (whales, devs, predictions, etc.)
│
├── cron/                      # Cron scripts for 24/7
│   ├── the-eye-cron           # Crontab template
│   ├── blockchain-scan.sh     # Every 5 min
│   ├── social-scan.sh         # Every 10 min
│   ├── market-scan.sh         # Every 15 min
│   ├── temporal-scan.sh       # Every 30 min
│   └── alert-dispatch.sh      # Every 60 min
│
├── scripts/
│   ├── setup-24-7.sh          # One-command 24/7 setup
│   ├── telegram-bot-setup.py  # Interactive Telegram config
│   └── discord-webhook-setup.py # Interactive Discord config
│
├── docs/
│   ├── HOW_IT_WORKS.md        # Deep technical explanation
│   ├── USAGE_GUIDE.md         # Detailed usage guide
│   ├── 24-7_SETUP.md         # 24/7 setup guide
│   ├── FREE_SOURCES_GUIDE.md # Data source documentation
│   ├── PATTERN_CATALOG.md    # All detection patterns
│   ├── SELF_IMPROVEMENT.md   # How the learning system works
│   └── TROUBLESHOOTING.md    # Common issues & fixes
│
└── tests/                     # Unit tests
```

---

## Configuration

All settings live in `config/defaults.json`. Key settings:

```json
{
  "scan": {
    "max_tokens_per_cycle": 200,      // Max tokens to scan per cycle
    "chains": ["eth", "sol", "base", "arb", "bsc"],
    "min_liquidity_usd": 1000,        // Min liquidity to scan
    "min_volume_24h_usd": 500         // Min 24h volume to scan
  },
  "alerts": {
    "min_confidence": 60,             // Min confidence % to alert
    "min_urgency": "medium",          // Min urgency level to alert
    "cooldown_sec": 300,              // Don't repeat same alert for 5 min
    "max_per_hour": 20                // Max 20 alerts per hour
  }
}
```

### Optional: Alert Channels

Create a `.env` file from `.env.example`:

```bash
# Telegram (free from @BotFather)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-1001234567890

# Discord (free webhook)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Or use the interactive setup scripts:
```bash
python scripts/telegram-bot-setup.py
python scripts/discord-webhook-setup.py
```

---

## How It Works (Full Explanation)

See **[docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)** for a detailed step-by-step explanation of every component, how data flows through the system, and what each analysis engine does.

---

## FAQ

**Q: Do I need API keys?**
A: No. All data sources are free. DexScreener, GeckoTerminal, and CoinGecko have free APIs. Twitter/Reddit are scraped via free interfaces.

**Q: Does this track my portfolio?**
A: No. THE EYE monitors the ENTIRE memecoin market. It discovers tokens, detects patterns, and alerts you to opportunities and risks across all chains simultaneously.

**Q: How accurate are the predictions?**
A: Predictions start with pattern-based estimates and improve over time through the self-improvement feedback loop. Run `opencode backtest` to check accuracy.

**Q: Can I run this on a server 24/7?**
A: Yes. Run `bash scripts/setup-24-7.sh` to set up cron jobs and/or a screen session.

**Q: Which chains are supported?**
A: Ethereum, Solana, Base, Arbitrum, and BSC by default. DexScreener supports 20+ additional chains.

**Q: How do I stop the 24/7 monitor?**
A: For screen: `screen -S the-eye -X quit`. For cron: `crontab -r` removes all cron jobs.

---

## License

MIT

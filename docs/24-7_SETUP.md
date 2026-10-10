# 24/7 Setup Guide — THE EYE

## Overview
THE EYE is designed to run 24/7, continuously monitoring your watchlist for whale activity, rug indicators, pump patterns, and temporal risk windows. This guide explains how to set up continuous operation.

---

## Prerequisites

1. **Python 3.8+** installed
2. **requests** library: `pip install -r requirements.txt`
3. **Internet access** for free API calls
4. **Disk space**: ~100MB for state files and logs
5. **Linux/macOS** (cron support) or Windows (Task Scheduler)

---

## Quick Start

### 1. Install Dependencies
```bash
cd /home/z/my-project/the-eye-memecoin
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
```bash
cp .env.example .env
# Edit .env with optional API keys (all are optional)
```

### 3. Add Tokens to Watchlist
```
/add-watchlist PEPE
/add-watchlist BONK
/add-watchlist DOGE
```

### 4. Set Up Cron Jobs
```bash
# Install the crontab
crontab cron/crontab

# Or set up manually:
crontab -e
# Add:
*/15 * * * * cd /path/to/the-eye-memecoin && python3 scripts/scan_watchlist.py >> logs/scan.log 2>&1
*/10 * * * * cd /path/to/the-eye-memecoin && python3 scripts/whale_check.py >> logs/whale.log 2>&1
*/30 * * * * cd /path/to/the-eye-memecoin && python3 scripts/rug_monitor.py >> logs/rug.log 2>&1
0 * * * * cd /path/to/the-eye-memecoin && python3 scripts/temporal_update.py >> logs/temporal.log 2>&1
0 0 * * * cd /path/to/the-eye-memecoin && python3 scripts/cleanup.py >> logs/cleanup.log 2>&1
```

### 5. Configure Alerts (Optional)
```bash
# Telegram alerts
# 1. Create bot via @BotFather → get TELEGRAM_BOT_TOKEN
# 2. Add bot to your channel/group → get TELEGRAM_CHAT_ID
# 3. Add to .env

# Discord alerts
# 1. Create webhook in Discord channel → get DISCORD_WEBHOOK_URL
# 2. Add to .env
```

### 6. Verify Operation
```bash
# Check cron is running
crontab -l

# Monitor logs
tail -f logs/scan.log

# Check system status
/status
```

---

## Scan Intervals

| Scanner | Interval | Purpose |
|---------|----------|---------|
| Main Scan | 15 min | Price, volume, social for all watchlist tokens |
| Whale Check | 10 min | Whale wallet activity monitor |
| Rug Monitor | 30 min | Re-check rug indicators |
| Temporal Update | 60 min | Update danger windows and market cycle |
| Cleanup | 24 hr | Prune old data, validate predictions |

---

## Log Management

### Log Files
- `logs/scan.log` — Main scan cycle output
- `logs/whale.log` — Whale monitoring output
- `logs/rug.log` — Rug monitoring output
- `logs/temporal.log` — Temporal analysis output
- `logs/cleanup.log` — Cleanup output
- `logs/alerts.log` — Alert dispatch log

### Log Rotation (Linux)
```bash
# Create logrotate config
sudo tee /etc/logrotate.d/the-eye << EOF
/home/z/my-project/the-eye-memecoin/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
}
EOF
```

---

## Alert Channels

### Telegram Setup
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow prompts → get `TELEGRAM_BOT_TOKEN`
3. Add bot to your channel/group
4. Get chat ID (send message to bot, check updates API)
5. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### Discord Setup
1. Open Discord channel settings → Integrations → Webhooks
2. Create new webhook → copy URL
3. Add to `.env`:
   ```
   DISCORD_WEBHOOK_URL=your_webhook_url
   ```

### Console Output
- Always active (no configuration needed)
- Alerts print to stdout with ANSI colors
- Visible in log files

---

## Monitoring the Monitor

### Health Checks
- `/status` — Check system health at any time
- Cron jobs log timestamps to WORKFLOW_STATE.md
- If last scan >2x expected interval → system may be down

### Restarting After Downtime
1. Cron automatically resumes on next scheduled run
2. All state files persist (watchlist, whale-db, dev-db)
3. Caches may be stale but will refresh on first scan
4. No manual intervention needed in most cases

### Stopping Monitoring
```bash
# Remove all cron jobs
crontab -r

# Or disable specific jobs by commenting out
crontab -e
```

---

## Resource Usage

### Expected Load
- **CPU**: <5% average (API calls are I/O-bound)
- **Memory**: <100MB (Python + JSON state files)
- **Network**: ~500 API calls/hour (well within free limits)
- **Disk**: ~10MB/day (logs + state updates)

### Scaling Limits
- **Watchlist**: Recommended max 50 tokens for single-instance
- **Whale DB**: Max 10MB (~10,000 whale entries)
- **Dev DB**: Max 5MB (~5,000 developer entries)
- **Alerts**: Max 10/hour (except EMERGENCY)

---

## Windows Setup (Alternative)

Use Task Scheduler instead of cron:
```powershell
# Create scheduled tasks
schtasks /create /sc MINUTE /mo 15 /tn "THE_EYE_Scan" /tr "python3 C:\path\to\scripts\scan_watchlist.py"
schtasks /create /sc MINUTE /mo 10 /tn "THE_EYE_Whale" /tr "python3 C:\path\to\scripts\whale_check.py"
schtasks /create /sc MINUTE /mo 30 /tn "THE_EYE_Rug" /tr "python3 C:\path\to\scripts\rug_monitor.py"
schtasks /create /sc HOURLY /tn "THE_EYE_Temporal" /tr "python3 C:\path\to\scripts\temporal_update.py"
```

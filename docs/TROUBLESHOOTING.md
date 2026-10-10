# Troubleshooting Guide — THE EYE

## Common Issues and Fixes

---

### Issue: "Rate limit exceeded" (429 errors)

**Symptoms**: API calls returning HTTP 429, logs showing "Too Many Requests"

**Cause**: Exceeding free tier rate limits on data sources

**Fixes**:
1. **Increase cache TTL**: Edit scan scripts to cache longer (60s → 120s)
2. **Reduce scan frequency**: Change cron from `*/10` to `*/15` or `*/30`
3. **Reduce watchlist size**: Remove less important tokens
4. **Get free API key**: Register at Etherscan/CoinGecko for higher limits
5. **Distribute load**: Use different sources for different tokens

**Rate Limits by Source**:
- DexScreener: 100 req/min
- CoinGecko: 30 req/min (500 with demo key)
- Etherscan: 5 req/s
- Reddit: 60 req/min
- Blockchair: ~20 req/min

---

### Issue: "Nitter instance not responding"

**Symptoms**: Social scanning fails, Twitter/X data unavailable

**Cause**: Nitter instance is down or blocked

**Fixes**:
1. **Automatic rotation**: System tries next instance automatically
2. **Update instance list**: Edit the NITTER_INSTANCES list in config
3. **Skip social**: System continues without Twitter data (marks as UNAVAILABLE)
4. **Check status**: https://status.nitter.net for instance health

**Fallback**: Reddit and Telegram still provide social signals

---

### Issue: "Contract source not verified"

**Symptoms**: Rug detector cannot analyze contract code

**Cause**: Developer did not verify source code on Etherscan

**Fixes**:
1. **Bytecode analysis**: System falls back to bytecode pattern matching
2. **GoPlus Security**: Use GoPlus for basic security checks (works on unverified)
3. **Increase uncertainty**: Mark contract_risk as 0.5 (unknown) with lower confidence
4. **Check other chains**: Same token may be verified on another chain

**Impact**: Rug probability less accurate, confidence reduced

---

### Issue: "Token not found on CoinGecko"

**Symptoms**: Token lookup returns 404

**Cause**: Token too new, too small, or delisted

**Fixes**:
1. **Use DexScreener**: Better coverage of small/new DEX tokens
2. **Use GeckoTerminal**: Alternative DEX data source
3. **Direct contract lookup**: Use Etherscan/Solscan with contract address
4. **Token may be rug**: Very new tokens with no CoinGecko listing are higher risk

---

### Issue: "All alerts going to console only"

**Symptoms**: No Telegram/Discord messages received

**Cause**: Alert channels not configured or misconfigured

**Fixes**:
1. **Check .env file**: Ensure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set
2. **Test Telegram bot**: Send a test message via the Bot API
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=Test"
   ```
3. **Test Discord webhook**:
   ```bash
   curl -X POST "<WEBHOOK_URL>" -H "Content-Type: application/json" -d '{"content":"Test"}'
   ```
4. **Check bot permissions**: Bot must be in the group/channel

---

### Issue: "State files corrupted"

**Symptoms**: JSON parse errors on startup, missing data

**Cause**: Unexpected shutdown during write, disk full

**Fixes**:
1. **Restore from backup**: Check `src/data/backups/` for recent backup
2. **Reinitialize**: Delete corrupted file, system creates empty state on restart
3. **Prevention**: System uses atomic writes (write to .tmp then rename)
4. **Check disk space**: Ensure adequate disk space for state files

---

### Issue: "Whale wallet data outdated"

**Symptoms**: Whale tracking showing stale data, no recent transactions

**Cause**: Whale check cron not running, or API access blocked

**Fixes**:
1. **Check cron**: `crontab -l` to verify whale_check is scheduled
2. **Check logs**: `tail logs/whale.log` for errors
3. **Manual scan**: Run `/whale-watch <address>` manually
4. **Verify blockchain API**: Test Etherscan/Blockchair connectivity

---

### Issue: "High memory usage"

**Symptoms**: Python process using >500MB RAM

**Cause**: Large state files loaded into memory, or memory leak

**Fixes**:
1. **Check state file sizes**: `du -h src/data/*.json`
2. **Prune old data**: Run cleanup script manually
3. **Reduce whale DB**: Prune entries with low accuracy scores
4. **Restart process**: Kill and let cron restart on next cycle

---

### Issue: "Predictions seem inaccurate"

**Symptoms**: Predictions not matching actual outcomes

**Cause**: Model weights need calibration, or insufficient historical data

**Fixes**:
1. **Check prediction log**: Review past predictions vs outcomes in `src/data/predictions.json`
2. **Self-improvement cycle**: System adjusts weights based on accuracy weekly
3. **More data**: Add more tokens to watchlist for broader pattern learning
4. **Review factors**: Check which factors are contributing most to errors

---

### Issue: "System not starting after reboot"

**Symptoms**: No monitoring after server restart

**Cause**: Cron jobs not installed or not persisting

**Fixes**:
1. **Reinstall crontab**: `crontab cron/crontab`
2. **Check cron service**: `sudo systemctl status cron` (Linux)
3. **Use @reboot**: Add `@reboot` cron entry for immediate start
4. **Systemd service**: Create systemd service for more robust startup

**Systemd Service Example**:
```ini
[Unit]
Description=THE EYE Memecoin Monitor
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /path/to/the-eye-memecoin/scripts/scan_watchlist.py
User=youruser

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
```

---

### Issue: "DexScreener returning stale data"

**Symptoms**: Prices not updating, volume figures seem old

**Cause**: DexScreener caching on their end, or low-liquidity token

**Fixes**:
1. **Cross-reference**: Check CoinGecko for same token
2. **Direct DEX query**: Use GeckoTerminal for same pair
3. **Accept latency**: DexScreener may have 30-60s cache
4. **Low liquidity**: Very small tokens may have genuinely no new trades

---

## Getting Help

1. **Check status first**: Run `/status` for system health overview
2. **Review logs**: Check `logs/` directory for error details
3. **Verify sources**: Test API connectivity manually with curl
4. **Check state**: Verify `src/data/*.json` files are valid JSON

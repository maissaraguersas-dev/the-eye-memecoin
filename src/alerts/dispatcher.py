"""THE EYE — Alert Dispatcher

Dispatches alerts to: Telegram, Discord, local terminal, and log files.
All channels are free — no paid services required.
"""
import asyncio
import aiohttp
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from src.alerts.formatter import Alert
from config.settings import settings


@dataclass
class DispatchResult:
    alert: Alert
    channels: list[str] = field(default_factory=list)
    success: bool = True
    errors: list[str] = field(default_factory=list)


class Dispatcher:
    """Send alerts to all configured channels — Telegram, Discord, terminal, log."""

    ALERTS_DIR = Path(__file__).parent.parent.parent / "src" / "data"
    LOG_FILE = ALERTS_DIR / "alert_log.json"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._cooldown: dict[str, float] = {}  # alert_key → last_sent timestamp
        self._alert_count: dict[str, int] = {}  # hour_key → count

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # ── Cooldown & Rate Limiting ────────────────────────────────────

    def _should_send(self, alert: Alert) -> bool:
        """Check cooldown and rate limits before sending."""
        # Cooldown: don't send same alert type for same token too frequently
        key = f"{alert.alert_type}:{alert.token_symbol}"
        cooldown = settings.get("alerts.cooldown_sec", 300)
        if key in self._cooldown and (time.time() - self._cooldown[key]) < cooldown:
            return False

        # Rate limit: max alerts per hour
        hour_key = time.strftime("%Y%m%d%H")
        max_per_hour = settings.get("alerts.max_per_hour", 20)
        if self._alert_count.get(hour_key, 0) >= max_per_hour:
            return False

        return True

    def _mark_sent(self, alert: Alert):
        """Mark alert as sent for cooldown tracking."""
        key = f"{alert.alert_type}:{alert.token_symbol}"
        self._cooldown[key] = time.time()
        hour_key = time.strftime("%Y%m%d%H")
        self._alert_count[hour_key] = self._alert_count.get(hour_key, 0) + 1

    # ── Telegram ────────────────────────────────────────────────────

    async def send_telegram(self, alert: Alert) -> bool:
        """Send alert to Telegram via bot API (free)."""
        token = settings.get("alerts.telegram_bot_token", "")
        chat_id = settings.get("alerts.telegram_chat_id", "")
        if not token or not chat_id:
            return False

        session = await self._get_session()
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": alert.to_telegram(),
                "parse_mode": "Markdown",
            }
            async with session.post(url, json=payload) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[Telegram error] {e}")
            return False

    # ── Discord ─────────────────────────────────────────────────────

    async def send_discord(self, alert: Alert) -> bool:
        """Send alert to Discord via webhook (free)."""
        webhook_url = settings.get("alerts.discord_webhook_url", "")
        if not webhook_url:
            return False

        session = await self._get_session()
        try:
            payload = {"content": alert.to_discord()}
            async with session.post(webhook_url, json=payload) as resp:
                return resp.status == 204
        except Exception as e:
            print(f"[Discord error] {e}")
            return False

    # ── Terminal ────────────────────────────────────────────────────

    def send_terminal(self, alert: Alert):
        """Print alert to terminal with formatting."""
        print(f"\n{alert.to_text()}\n")

    # ── Log File ────────────────────────────────────────────────────

    def send_log(self, alert: Alert):
        """Write alert to local JSON log file."""
        self.ALERTS_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "type": alert.alert_type,
            "title": alert.title,
            "token": alert.token_symbol,
            "confidence": alert.confidence,
            "urgency": alert.urgency,
            "timestamp": alert.timestamp,
            "what": alert.what,
            "why": alert.why,
        }
        # Append to log
        existing = []
        if self.LOG_FILE.exists():
            with open(self.LOG_FILE) as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []
        existing.append(entry)
        # Keep last 500
        with open(self.LOG_FILE, "w") as f:
            json.dump(existing[-500:], f, indent=2)

    # ── Dispatch All ────────────────────────────────────────────────

    async def dispatch(self, alerts: list[Alert],
                        terminal: bool = True,
                        telegram: bool = True,
                        discord: bool = True,
                        log: bool = True) -> list[DispatchResult]:
        """Dispatch a list of alerts to all configured channels."""
        results = []
        min_conf = settings.get("alerts.min_confidence", 60)
        min_urgency = settings.get("alerts.min_urgency", "medium")
        urgency_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

        for alert in alerts:
            # Filter by confidence and urgency
            if alert.confidence < min_conf:
                continue
            if urgency_order.get(alert.urgency, 0) < urgency_order.get(min_urgency, 1):
                continue

            # Check cooldown
            if not self._should_send(alert):
                continue

            channels = []
            errors = []

            # Terminal
            if terminal:
                self.send_terminal(alert)
                channels.append("terminal")

            # Telegram
            if telegram:
                try:
                    ok = await self.send_telegram(alert)
                    if ok:
                        channels.append("telegram")
                except Exception as e:
                    errors.append(f"telegram: {e}")

            # Discord
            if discord:
                try:
                    ok = await self.send_discord(alert)
                    if ok:
                        channels.append("discord")
                except Exception as e:
                    errors.append(f"discord: {e}")

            # Log
            if log:
                self.send_log(alert)
                channels.append("log")

            self._mark_sent(alert)

            results.append(DispatchResult(
                alert=alert,
                channels=channels,
                success=len(errors) == 0,
                errors=errors,
            ))

        return results

    async def dispatch_queued(self):
        """Dispatch any pending alerts from the log."""
        if not self.LOG_FILE.exists():
            print("No pending alerts.")
            return

        with open(self.LOG_FILE) as f:
            try:
                entries = json.load(f)
            except json.JSONDecodeError:
                entries = []

        print(f"📬 {len(entries)} logged alerts on file.")
        for entry in entries[-10:]:
            alert = Alert(
                alert_type=entry.get("type", "unknown"),
                title=entry.get("title", ""),
                who="", what=entry.get("what", ""),
                why=entry.get("why", ""), when="", how="",
                confidence=entry.get("confidence", 0),
                urgency=entry.get("urgency", "low"),
                token_symbol=entry.get("token", ""),
                timestamp=entry.get("timestamp", 0),
            )
            self.send_terminal(alert)

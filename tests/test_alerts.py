"""
Tests for AlertFormatter and AlertDispatcher — alert formatting,
serialization, and dispatch to various channels.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.alerts.formatter import (
    AlertFormatter,
    Alert,
    AlertType,
    Urgency,
    _urgency_from_confidence,
)
from src.alerts.dispatcher import AlertDispatcher, DispatchResult


# ─── Alert formatting ────────────────────────────────────────────────────────

class TestFormatWhaleAlert:
    def test_format_whale_alert(self):
        """Whale alert follows WHO/WHAT/WHY/WHEN/HOW format."""
        fmt = AlertFormatter()
        whale_match = {
            "wallet": "0xwhale123",
            "amount_usd": 500_000,
            "direction": "buy",
            "tx_hash": "0xtx456",
            "confidence": 80,
            "agents": ["whale-tracker"],
        }
        alert = fmt.format_whale_alert(whale_match, "PEPE", "eth")

        assert alert.alert_type == AlertType.WHALE
        assert alert.who == "0xwhale123"
        assert "500,000" in alert.what
        assert alert.confidence == 80
        assert alert.chain == "eth"
        assert alert.token == "PEPE"


class TestFormatRugAlert:
    def test_format_rug_alert_critical(self):
        """CRITICAL rug alert uses correct urgency."""
        fmt = AlertFormatter()
        dev_match = {
            "developer": "0xdev789",
            "risk_flags": ["no_lock", "serial_rugger"],
            "risk_score": 90,
            "evidence": "Multiple rug indicators",
            "confidence": 85,
            "agents": ["rug-detector"],
        }
        alert = fmt.format_rug_alert(dev_match, "SCAMCOIN", "eth")

        assert alert.alert_type == AlertType.RUG
        assert alert.who == "0xdev789"
        assert alert.confidence == 85
        # Rug with confidence >= 70 should be CRITICAL
        assert alert.urgency == Urgency.CRITICAL

    def test_format_rug_alert_low(self):
        """Low-confidence rug alert is LOW urgency."""
        fmt = AlertFormatter()
        dev_match = {
            "developer": "0xdev",
            "risk_flags": [],
            "risk_score": 20,
            "evidence": "Minor suspicion",
            "confidence": 30,
            "agents": ["rug-detector"],
        }
        alert = fmt.format_rug_alert(dev_match, "TESTCOIN", "eth")
        assert alert.urgency == Urgency.LOW


class TestFormatPumpAlert:
    def test_format_pump_alert(self):
        """Fake pump alert formatted correctly."""
        fmt = AlertFormatter()
        manipulation_result = {
            "pattern": "bot_army_coordination",
            "wallets": ["0xbot1", "0xbot2"],
            "volume_usd": 200_000,
            "confidence": 75,
            "agents": ["pump-detector"],
        }
        alert = fmt.format_pump_alert(manipulation_result, "FAKEPUMP", "solana")

        assert alert.alert_type == AlertType.PUMP
        assert "bot_army" in alert.what.lower()
        assert alert.chain == "solana"


class TestFormatTemporalAlert:
    def test_format_temporal_alert(self):
        """Temporal danger window alert formatted correctly."""
        fmt = AlertFormatter()
        temporal_risk = {
            "window": "rug_hour",
            "risk_level": "HIGH",
            "reasoning": "78% of rugs happen in this window",
            "confidence": 70,
            "agents": ["temporal-scanner"],
        }
        alert = fmt.format_temporal_alert(temporal_risk, "PEPE")

        assert alert.alert_type == AlertType.TEMPORAL
        assert "rug_hour" in alert.what
        assert "PEPE" in alert.why


# ─── Output format conversions ───────────────────────────────────────────────

class TestToText:
    def test_to_text(self):
        """Human-readable text output contains all key fields."""
        fmt = AlertFormatter()
        alert = Alert(
            alert_type=AlertType.WHALE,
            token="PEPE",
            who="0xwhale",
            what="Whale buy detected",
            why="Large transaction",
            when="2026-08-11T12:00:00Z",
            how="On-chain monitoring",
            confidence=80,
            urgency=Urgency.HIGH,
            chain="eth",
            source_agents=["whale-tracker"],
        )
        text = fmt.to_text(alert)
        assert "WHALE" in text
        assert "0xwhale" in text
        assert "Whale buy" in text
        assert "80/100" in text
        assert "HIGH" in text


class TestToJson:
    def test_to_json(self):
        """JSON serialization produces valid JSON with all fields."""
        fmt = AlertFormatter()
        alert = Alert(
            alert_type=AlertType.RUG,
            token="SCAM",
            who="0xdev",
            what="Rug detected",
            why="Dev removed liquidity",
            when="2026-08-11T12:00:00Z",
            how="Rug detector",
            confidence=90,
            urgency=Urgency.CRITICAL,
            chain="eth",
        )
        json_str = fmt.to_json(alert)
        data = json.loads(json_str)
        assert data["alert_type"] == "rug"
        assert data["urgency"] == "CRITICAL"
        assert data["confidence"] == 90


class TestToTelegram:
    def test_to_telegram(self):
        """Telegram markdown format contains alert info."""
        fmt = AlertFormatter()
        alert = Alert(
            alert_type=AlertType.WHALE,
            token="PEPE",
            who="0xwhale",
            what="Whale buy",
            why="Large buy",
            when="2026-08-11T12:00:00Z",
            how="Monitoring",
            confidence=80,
            urgency=Urgency.HIGH,
            chain="eth",
        )
        text = fmt.to_telegram(alert)
        assert "WHALE" in text
        assert "PEPE" in text


class TestToDiscord:
    def test_to_discord(self):
        """Discord embed format has proper structure."""
        fmt = AlertFormatter()
        alert = Alert(
            alert_type=AlertType.PUMP,
            token="FAKE",
            who="0xbot",
            what="Fake pump",
            why="Bot army",
            when="2026-08-11T12:00:00Z",
            how="Pump detector",
            confidence=75,
            urgency=Urgency.HIGH,
            chain="eth",
        )
        payload = fmt.to_discord(alert)
        assert "embeds" in payload
        embed = payload["embeds"][0]
        assert "title" in embed
        assert "fields" in embed
        assert embed["color"] > 0  # should have a color


# ─── Dispatcher tests ────────────────────────────────────────────────────────

class TestDispatcherTelegram:
    def test_dispatcher_telegram_mocked(self, tmp_path):
        """Telegram dispatch succeeds when mocked."""
        config = {
            "channels": {
                "telegram": {
                    "enabled": True,
                    "bot_token": "123456:ABC-DEF",
                    "chat_id": "-1001234567890",
                },
                "discord": {"enabled": False, "webhook_url": ""},
                "local": {"enabled": False},
                "log": {"enabled": False, "path": str(tmp_path / "alerts.log")},
            },
            "min_urgency": "LOW",
        }
        config_path = tmp_path / "dispatch_config.json"
        config_path.write_text(json.dumps(config))

        dispatcher = AlertDispatcher(config_path=str(config_path))

        alert = Alert(
            alert_type=AlertType.WHALE,
            token="PEPE",
            who="0xwhale",
            what="Whale buy",
            why="Large buy",
            when="2026-08-11T12:00:00Z",
            how="Monitoring",
            confidence=80,
            urgency=Urgency.HIGH,
            chain="eth",
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"ok": True}).encode()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = dispatcher.dispatch_telegram(alert)
            assert result.success is True
            assert result.channel == "telegram"


class TestDispatcherDiscord:
    def test_dispatcher_discord_mocked(self, tmp_path):
        """Discord dispatch succeeds when mocked."""
        config = {
            "channels": {
                "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
                "discord": {"enabled": True, "webhook_url": "https://discord.com/api/webhooks/test/token"},
                "local": {"enabled": False},
                "log": {"enabled": False, "path": str(tmp_path / "alerts.log")},
            },
            "min_urgency": "LOW",
        }
        config_path = tmp_path / "dispatch_config.json"
        config_path.write_text(json.dumps(config))

        dispatcher = AlertDispatcher(config_path=str(config_path))

        alert = Alert(
            alert_type=AlertType.RUG,
            token="SCAM",
            who="0xdev",
            what="Rug detected",
            why="Liquidity removed",
            when="2026-08-11T12:00:00Z",
            how="Rug detector",
            confidence=90,
            urgency=Urgency.CRITICAL,
            chain="eth",
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 204
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = dispatcher.dispatch_discord(alert)
            assert result.success is True
            assert result.channel == "discord"


class TestDispatcherLog:
    def test_dispatcher_log(self, tmp_path):
        """Log dispatch writes to the log file."""
        log_path = tmp_path / "alerts.log"
        config = {
            "channels": {
                "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
                "discord": {"enabled": False, "webhook_url": ""},
                "local": {"enabled": False},
                "log": {"enabled": True, "path": str(log_path)},
            },
            "min_urgency": "LOW",
        }
        config_path = tmp_path / "dispatch_config.json"
        config_path.write_text(json.dumps(config))

        dispatcher = AlertDispatcher(config_path=str(config_path))

        alert = Alert(
            alert_type=AlertType.SYSTEM,
            token="SYSTEM",
            who="the-eye",
            what="Test alert",
            why="Testing",
            when="2026-08-11T12:00:00Z",
            how="Test",
            confidence=100,
            urgency=Urgency.LOW,
        )

        result = dispatcher.dispatch_log(alert)
        assert result.success is True
        assert result.channel == "log"
        assert log_path.exists()
        content = log_path.read_text()
        assert "Test alert" in content

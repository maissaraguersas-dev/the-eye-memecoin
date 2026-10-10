"""
Integration tests for THE EYE — end-to-end pipeline tests.

Tests the full scan pipeline across all modules, including whale watch,
rug check, pump detection, temporal analysis, and the complete watchlist
lifecycle (add -> scan -> alert -> remove).
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.pattern.whale_matcher import WhaleMatcher, WhaleMatch
from src.pattern.dev_matcher import DevMatcher, DevMatch
from src.pattern.manipulation_detector import ManipulationDetector, ManipulationResult
from src.pattern.temporal_analyzer import TemporalAnalyzer, TemporalRiskResult
from src.alerts.formatter import AlertFormatter, Alert, AlertType, Urgency
from src.alerts.dispatcher import AlertDispatcher
from src.autonomous.watchlist_manager import WatchlistManager
from src.autonomous.state_manager import StateManager
from src.autonomous.alert_queue import AlertQueue


# ─── Full scan pipeline ──────────────────────────────────────────────────────

class TestFullScanPipeline:
    """End-to-end: token address -> all modules -> aggregated alerts."""

    def test_full_scan_pipeline(self, tmp_data_dir):
        """Run all detection modules on a suspicious token."""
        # Instantiate all modules with isolated data
        whale = WhaleMatcher(db_path=tmp_data_dir / "whale_profiles.json")
        dev = DevMatcher(db_path=tmp_data_dir / "dev_signatures.json")
        pump = ManipulationDetector(db_path=tmp_data_dir / "manipulation_patterns.json")
        temporal = TemporalAnalyzer(db_path=tmp_data_dir / "temporal_patterns.json")
        fmt = AlertFormatter()

        # 1. Whale matching — known sniper
        txs = [
            {"timestamp": "2026-08-10T12:02:00Z", "is_swap": True, "value_eth": 5.0, "token_amount": 500000},
        ]
        whale_result = whale.match_wallet(
            "0x4a2b8c1d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
            wallet_txs=txs,
            token_launch_time="2026-08-10T12:00:00Z",
        )
        assert whale_result.is_known_whale is True

        # 2. Rug detection — known serial rugger
        dev_result = dev.analyze_dev(
            "0x9f1d2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e",
            liquidity_locked=False,
            dev_holds_pct=40.0,
            dev_wallet_age_days=2,
        )
        assert dev_result.known_serial_rugger is True
        assert dev_result.rug_probability >= 70

        # 3. Pump detection — bot army
        funder = "0xbotfunder"
        holders = [
            {"wallet_age_days": 1.0, "funded_from": funder, "address": f"0xbot{i:04x}"}
            for i in range(25)
        ]
        pump_result = pump.analyze_manipulation(
            token="FAKEPUMP",
            holders=holders,
            price_change_24h=350.0,
            volume_24h=1_000_000,
            market_cap=5_000_000,
            real_volume_pct=10.0,
            twitter_mentions=55000,
            twitter_bot_ratio=0.97,
            tiktok_videos=0,
            reddit_mentions=0,
        )
        assert len(pump_result.detected_patterns) >= 1

        # 4. Temporal analysis
        temporal_result = temporal.calculate_temporal_risk(chain="eth")
        assert 0 <= temporal_result.risk_score <= 100

        # 5. Format alerts
        whale_alert = fmt.format_whale_alert(
            {"wallet": "0xwhale", "amount_usd": 500000, "direction": "buy",
             "tx_hash": "0xtx", "confidence": 80, "agents": ["whale-tracker"]},
            "FAKEPUMP", "eth",
        )
        rug_alert = fmt.format_rug_alert(
            {"developer": "0xdev", "risk_flags": ["serial_rugger"],
             "risk_score": 90, "evidence": "Known rugger", "confidence": 85,
             "agents": ["rug-detector"]},
            "FAKEPUMP", "eth",
        )
        assert whale_alert.alert_type == AlertType.WHALE
        assert rug_alert.alert_type == AlertType.RUG


# ─── Whale watch pipeline ────────────────────────────────────────────────────

class TestWhaleWatchPipeline:
    def test_whale_watch_pipeline(self, tmp_data_dir):
        """End-to-end: detect whale -> format alert -> dispatch."""
        whale = WhaleMatcher(db_path=tmp_data_dir / "whale_profiles.json")
        fmt = AlertFormatter()

        # Match a known whale
        txs = [
            {"timestamp": "2026-08-10T12:02:00Z", "is_swap": True, "value_eth": 5.0, "token_amount": 500000},
        ]
        result = whale.match_wallet(
            "0x4a2b8c1d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
            wallet_txs=txs,
            token_launch_time="2026-08-10T12:00:00Z",
        )
        assert result.is_known_whale

        # Format alert
        alert = fmt.format_whale_alert(
            {"wallet": "PEPE Sniper", "amount_usd": 500000, "direction": "buy",
             "tx_hash": "0xtx", "confidence": int(result.confidence), "agents": ["whale-tracker"]},
            "PEPE", "eth",
        )
        assert alert.confidence > 0

        # Verify text output
        text = fmt.to_text(alert)
        assert "PEPE Sniper" in text or "WHALE" in text


# ─── Rug check pipeline ──────────────────────────────────────────────────────

class TestRugCheckPipeline:
    def test_rug_check_pipeline(self, tmp_data_dir):
        """End-to-end: analyze dev -> classify urgency -> format alert."""
        dev = DevMatcher(db_path=tmp_data_dir / "dev_signatures.json")
        fmt = AlertFormatter()

        result = dev.analyze_dev(
            "0x9f1d2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e",
            liquidity_locked=False,
            dev_holds_pct=50.0,
            dev_wallet_age_days=1,
            social_bot_pct=97,
        )

        # Should be high-risk
        assert result.rug_probability >= 70
        assert result.urgency in ("HIGH", "CRITICAL")

        # Format alert
        alert = fmt.format_rug_alert(
            {"developer": result.dev_address, "risk_flags": result.indicators_matched,
             "risk_score": int(result.rug_probability), "evidence": "; ".join(result.evidence),
             "confidence": int(result.confidence), "agents": ["rug-detector"]},
            "SCAMCOIN", "eth",
        )
        assert alert.urgency in (Urgency.HIGH, Urgency.CRITICAL)


# ─── Pump scan pipeline ──────────────────────────────────────────────────────

class TestPumpScanPipeline:
    def test_pump_scan_pipeline(self, tmp_data_dir):
        """End-to-end: detect manipulation -> classify -> format alert."""
        pump = ManipulationDetector(db_path=tmp_data_dir / "manipulation_patterns.json")
        fmt = AlertFormatter()

        funder = "0xbotfunder"
        holders = [
            {"wallet_age_days": 1.0, "funded_from": funder, "address": f"0xbot{i:04x}"}
            for i in range(25)
        ]

        result = pump.analyze_manipulation(
            token="FAKEPUMP",
            holders=holders,
            price_change_24h=350.0,
            volume_24h=1_000_000,
            market_cap=5_000_000,
            real_volume_pct=10.0,
            twitter_mentions=55000,
            twitter_bot_ratio=0.97,
            tiktok_videos=0,
            reddit_mentions=0,
            dev_selling_during_pump=True,
        )

        assert result.is_fake_pump is True

        alert = fmt.format_pump_alert(
            {"pattern": "bot_army", "wallets": [f"0xbot{i}" for i in range(5)],
             "volume_usd": 200000, "confidence": int(result.confidence),
             "agents": ["pump-detector"]},
            "FAKEPUMP", "eth",
        )
        assert alert.alert_type == AlertType.PUMP


# ─── Danger window pipeline ─────────────────────────────────────────────────

class TestDangerWindowPipeline:
    def test_danger_window_pipeline(self, tmp_data_dir):
        """End-to-end: temporal analysis -> risk score -> format alert."""
        analyzer = TemporalAnalyzer(db_path=tmp_data_dir / "temporal_patterns.json")
        fmt = AlertFormatter()

        result = analyzer.calculate_temporal_risk(chain="eth")

        # Should have valid results
        assert 0 <= result.risk_score <= 100
        assert isinstance(result.active_windows, list)
        assert isinstance(result.recommendations, list)

        # Format temporal alert
        alert = fmt.format_temporal_alert(
            {"window": "rug_hour", "risk_level": "HIGH",
             "reasoning": "78% of rugs happen here", "confidence": 70,
             "agents": ["temporal-scanner"]},
            "PEPE",
        )
        assert alert.alert_type == AlertType.TEMPORAL


# ─── Watchlist lifecycle ─────────────────────────────────────────────────────

class TestWatchlistLifecycle:
    def test_watchlist_lifecycle(self, tmp_data_dir, tmp_path):
        """Full lifecycle: add -> scan -> alert -> remove."""
        wl_path = tmp_path / "watchlist.json"
        wl_path.write_text("[]")
        sm = StateManager(state_dir=str(tmp_path))
        wl = WatchlistManager(watchlist_path=str(wl_path), state_manager=sm)
        fmt = AlertFormatter()

        # 1. Add token to watchlist
        entry = wl.add_token("PEPE", "0xpepe", "eth", reason="Whale alert", scan_interval=5)
        assert wl.is_watched("PEPE")

        # 2. Token is due for scan
        due = wl.get_tokens_due_for_scan()
        assert any(t.token == "PEPE" for t in due)

        # 3. Scan the token (simulate finding a whale)
        wl.update_scan_time("PEPE")

        # 4. Generate and record alert
        alert = fmt.format_whale_alert(
            {"wallet": "0xwhale", "amount_usd": 500000, "direction": "buy",
             "tx_hash": "0xtx", "confidence": 80, "agents": ["whale-tracker"]},
            "PEPE", "eth",
        )
        wl.increment_alert_count("PEPE")
        tokens = wl.list_tokens()
        pepe_entry = next(t for t in tokens if t.token == "PEPE")
        assert pepe_entry.alert_count == 1

        # 5. Remove token from watchlist
        removed = wl.remove_token("PEPE")
        assert removed is True
        assert not wl.is_watched("PEPE")

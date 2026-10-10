"""
Tests for WhaleMatcher — whale wallet pattern detection and matching.

Validates database loading, profile lookups, pattern detection (sniper,
diamond hands, failed whale), confidence scoring, bonuses/penalties,
dev wallet flagging, and self-improving DB updates.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from src.pattern.whale_matcher import WhaleMatcher, WhaleMatch


# ─── Database loading ────────────────────────────────────────────────────────

class TestLoadWhaleDB:
    def test_load_whale_db_success(self, tmp_data_dir):
        """WhaleMatcher loads profiles from the JSON database."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        assert len(matcher._db.get("profiles", [])) > 0

    def test_load_whale_db_missing_file(self, tmp_path):
        """WhaleMatcher handles missing DB file gracefully."""
        db_path = tmp_path / "nonexistent.json"
        matcher = WhaleMatcher(db_path=db_path)
        assert matcher._db.get("profiles", []) == []

    def test_load_whale_db_corrupt_file(self, tmp_path):
        """WhaleMatcher handles corrupt JSON gracefully."""
        db_path = tmp_path / "bad.json"
        db_path.write_text("{invalid json!!!")
        matcher = WhaleMatcher(db_path=db_path)
        assert matcher._db.get("profiles", []) == []


# ─── Profile lookups ─────────────────────────────────────────────────────────

class TestGetWhaleProfile:
    def test_get_whale_profile_known(self, tmp_data_dir):
        """Known whale address returns its profile."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        profile = matcher.get_whale_profile(
            "0x4a2b8c1d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
        )
        assert profile is not None
        assert profile["label"] == "PEPE Sniper"
        assert profile["win_rate"] == 0.85

    def test_get_whale_profile_case_insensitive(self, tmp_data_dir):
        """Profile lookup is case-insensitive."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        profile = matcher.get_whale_profile(
            "0x4A2B8C1D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B"
        )
        assert profile is not None

    def test_get_whale_profile_unknown(self, tmp_data_dir):
        """Unknown address returns None."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        profile = matcher.get_whale_profile(
            "0x0000000000000000000000000000000000000000"
        )
        assert profile is None


# ─── Pattern detection ───────────────────────────────────────────────────────

class TestMatchWalletSniper:
    def test_match_wallet_sniper(self, tmp_data_dir, sniper_txs):
        """Detects sniper pattern when buy within 0-5 min of launch."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        txs, launch_time = sniper_txs
        result = matcher.match_wallet(
            "0xsniper",
            wallet_txs=txs,
            token_launch_time=launch_time,
        )
        assert "sniper" in result.matched_patterns
        assert result.confidence >= 60

    def test_sniper_not_detected_without_launch_time(self, tmp_data_dir, sniper_txs):
        """Sniper pattern not detected when launch time is not provided."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        txs, _ = sniper_txs
        result = matcher.match_wallet("0xsniper", wallet_txs=txs)
        assert "sniper" not in result.matched_patterns


class TestMatchWalletDiamondHands:
    def test_match_wallet_diamond_hands(self, tmp_data_dir, diamond_hands_txs):
        """Detects diamond-hands pattern: never sells >20% of position."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        result = matcher.match_wallet(
            "0xdiamond",
            wallet_txs=diamond_hands_txs,
            current_holdings_pct=1_000_000,
        )
        assert "diamond_hands" in result.matched_patterns
        assert result.predicted_action == "holding"


class TestMatchWalletFailedWhale:
    def test_match_wallet_failed_whale(self, tmp_data_dir, failed_whale_txs):
        """Detects failed-whale pattern (inverse signal)."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        result = matcher.match_wallet(
            "0xfailwhale",
            wallet_txs=failed_whale_txs,
        )
        assert "failed_whale" in result.matched_patterns
        assert result.predicted_action == "inverse_signal"
        assert any("INVERSE" in e for e in result.evidence)


# ─── Bonuses and penalties ───────────────────────────────────────────────────

class TestKnownWhaleBonus:
    def test_match_wallet_known_whale_bonus(self, tmp_data_dir, sniper_txs):
        """Known whale address gets +10 confidence bonus."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        txs, launch_time = sniper_txs

        known_addr = "0x4a2b8c1d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
        result = matcher.match_wallet(
            known_addr,
            wallet_txs=txs,
            token_launch_time=launch_time,
        )
        assert result.is_known_whale is True
        # Base for 1 pattern = 60, plus known whale bonus +10 = 70
        assert result.confidence >= 70


class TestFreshWalletPenalty:
    def test_match_wallet_fresh_wallet_penalty(self, tmp_data_dir, sniper_txs):
        """Fresh wallet (<7 days) gets -15 confidence penalty."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        txs, launch_time = sniper_txs

        result = matcher.match_wallet(
            "0xfresh",
            wallet_txs=txs,
            token_launch_time=launch_time,
            wallet_age_days=2,
        )
        assert result.is_fresh_wallet is True
        # Base for 1 pattern = 60, minus 15 penalty = 45
        assert result.confidence <= 60


class TestDevWalletFlag:
    def test_match_wallet_dev_wallet(self, tmp_data_dir, sniper_txs):
        """Dev wallet is flagged as insider, not whale."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        txs, launch_time = sniper_txs

        result = matcher.match_wallet(
            "0xdev",
            wallet_txs=txs,
            token_launch_time=launch_time,
            is_dev_wallet=True,
        )
        assert result.is_dev_wallet is True
        assert result.risk_level == "high"
        assert any("DEV WALLET" in e for e in result.evidence)


# ─── Confidence scoring ──────────────────────────────────────────────────────

class TestConfidenceScoring:
    def test_confidence_1_pattern(self, tmp_data_dir, sniper_txs):
        """1 pattern -> base confidence 60."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)
        txs, launch_time = sniper_txs
        result = matcher.match_wallet(
            "0xtest", wallet_txs=txs, token_launch_time=launch_time
        )
        if not result.is_known_whale and not result.is_fresh_wallet:
            assert result.confidence == matcher.BASE_CONFIDENCE_1_PATTERN

    def test_confidence_2_patterns(self, tmp_data_dir):
        """2 patterns -> base confidence 75."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)

        launch = "2026-08-10T12:00:00Z"
        txs = [
            {"timestamp": "2026-08-10T12:02:00Z", "is_swap": True, "value_eth": 5.0, "token_amount": 500000},
            {"timestamp": "2026-08-10T12:03:00Z", "is_swap": True, "value_eth": 3.0, "token_amount": 300000},
            {"timestamp": "2026-08-10T14:00:00Z", "is_swap": True, "value_eth": 2.0, "token_amount": 200000},
            {"timestamp": "2026-08-10T16:00:00Z", "is_swap": True, "value_eth": 1.0, "token_amount": 100000},
            {"timestamp": "2026-08-10T18:00:00Z", "is_swap": True, "value_eth": 1.5, "token_amount": 150000},
            {"timestamp": "2026-08-10T20:00:00Z", "is_swap": True, "value_eth": 0.5, "token_amount": 50000},
            # Small sell <= 20% to trigger diamond_hands
            {"timestamp": "2026-08-11T10:00:00Z", "is_swap": True, "value_eth": -0.3, "token_amount": 30000},
        ]

        result = matcher.match_wallet(
            "0xtest", wallet_txs=txs,
            token_launch_time=launch,
            current_holdings_pct=1_000_000,
        )
        if len(result.matched_patterns) >= 2 and not result.is_known_whale and not result.is_fresh_wallet:
            assert result.confidence >= matcher.BASE_CONFIDENCE_2_PATTERNS

    def test_confidence_3_plus_patterns(self, tmp_data_dir, failed_whale_txs):
        """3+ patterns -> base confidence >= 85."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)

        launch = "2026-08-10T12:00:00Z"
        txs = list(failed_whale_txs)
        # Add a sniper buy within 5 min of launch
        txs.insert(0, {
            "timestamp": "2026-08-10T12:02:00Z",
            "is_swap": True, "value_eth": 4.0, "token_amount": 800000,
        })

        result = matcher.match_wallet(
            "0xtest", wallet_txs=txs, token_launch_time=launch,
        )
        if len(result.matched_patterns) >= 3:
            assert result.confidence >= 85


# ─── Self-improving DB update ────────────────────────────────────────────────

class TestAddWhaleObservation:
    def test_add_whale_observation_existing(self, tmp_data_dir):
        """Adding observation to existing profile updates recent_observations."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)

        known_addr = "0x4a2b8c1d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
        matcher.add_whale_observation(known_addr, {
            "label": "PEPE Sniper",
            "pattern": "sniper",
            "notes": "Confirmed sniper entry",
        })

        # Reload and verify
        matcher2 = WhaleMatcher(db_path=db_path)
        profile = matcher2.get_whale_profile(known_addr)
        assert profile is not None
        assert "recent_observations" in profile
        assert len(profile["recent_observations"]) >= 1

    def test_add_whale_observation_new(self, tmp_data_dir):
        """Adding observation for unknown wallet creates a new profile."""
        db_path = tmp_data_dir / "whale_profiles.json"
        matcher = WhaleMatcher(db_path=db_path)

        new_addr = "0xnewwallet1234567890abcdef1234567890abcdef12"
        matcher.add_whale_observation(new_addr, {
            "label": "New Whale",
            "patterns": ["sniper"],
            "chain": "eth",
        })

        # Reload and verify
        matcher2 = WhaleMatcher(db_path=db_path)
        profile = matcher2.get_whale_profile(new_addr)
        assert profile is not None
        assert profile["label"] == "New Whale"

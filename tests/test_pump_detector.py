"""
Tests for ManipulationDetector — bot army, wash trading, volume-price
divergence, social manipulation detection, and fake pump classification.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from src.pattern.manipulation_detector import ManipulationDetector, ManipulationResult


# ─── Bot army detection ──────────────────────────────────────────────────────

class TestDetectBotArmy:
    def test_detect_bot_army(self, tmp_data_dir):
        """20+ fresh wallets funded from few sources triggers bot army."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)

        funder = "0xbotfunder"
        holders = [
            {
                "wallet_age_days": 1.0,
                "funded_from": funder,
                "address": f"0xbot{i:04x}",
            }
            for i in range(25)
        ]
        detected, score, bot_count, fund_sources, avg_age, evidence = detector.detect_bot_army(holders)
        assert detected is True
        assert score >= 25  # scoring weight
        assert bot_count >= 20
        assert len(evidence) > 0

    def test_no_bot_army_few_wallets(self, tmp_data_dir):
        """Fewer than 20 wallets does not trigger bot army."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)
        holders = [
            {"wallet_age_days": 1.0, "funded_from": "0xa", "address": f"0xw{i}"}
            for i in range(10)
        ]
        detected, score, *_ = detector.detect_bot_army(holders)
        assert detected is False


# ─── Wash trading detection ──────────────────────────────────────────────────

class TestDetectWashTrading:
    def test_detect_wash_trading(self, tmp_data_dir):
        """Circular transaction patterns trigger wash trading detection."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)

        txs = []
        wallets = [f"0xw{i}" for i in range(5)]
        # Create circular A->B and B->A patterns
        for i in range(50):
            a = wallets[i % len(wallets)]
            b = wallets[(i + 1) % len(wallets)]
            txs.append({"from_address": a, "to_address": b})
            txs.append({"from_address": b, "to_address": a})  # circular

        detected, score, evidence = detector.detect_wash_trading(txs)
        assert detected is True
        assert score > 0

    def test_no_wash_trading_organic(self, tmp_data_dir):
        """Organic (one-directional) transactions don't trigger wash trading."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)

        # One-directional: all go to the same target (no circular)
        txs = [
            {"from_address": f"0xuser{i}", "to_address": "0xdex_pool"}
            for i in range(20)
        ]
        detected, score, evidence = detector.detect_wash_trading(txs)
        assert detected is False


# ─── Volume-price divergence ─────────────────────────────────────────────────

class TestDetectVolumePriceDivergence:
    def test_detect_volume_price_divergence(self, tmp_data_dir):
        """Price up 300% with <20% real volume triggers divergence."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)
        detected, score, sigma, evidence = detector.detect_volume_price_divergence(
            price_change_24h=350.0,
            volume_24h=1_000_000,
            market_cap=5_000_000,
            real_volume_pct=10.0,
        )
        assert detected is True
        assert score >= 15
        assert sigma > 2.0

    def test_no_divergence_organic_pump(self, tmp_data_dir):
        """Organic pump with real volume doesn't trigger divergence."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)
        detected, score, sigma, evidence = detector.detect_volume_price_divergence(
            price_change_24h=50.0,
            volume_24h=1_000_000,
            market_cap=5_000_000,
            real_volume_pct=80.0,
        )
        assert detected is False


# ─── Social manipulation ─────────────────────────────────────────────────────

class TestDetectSocialManipulation:
    def test_detect_social_manipulation(self, tmp_data_dir):
        """High bot ratio + no organic content triggers social manipulation."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)
        detected, score, evidence = detector.detect_social_manipulation(
            twitter_mentions=55000,
            twitter_bot_ratio=0.97,
            tiktok_videos=0,
            reddit_mentions=0,
        )
        assert detected is True
        assert score >= 20  # social bot weight + zero organic weight

    def test_no_social_manipulation_organic(self, tmp_data_dir):
        """Organic social presence doesn't trigger manipulation."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)
        detected, score, evidence = detector.detect_social_manipulation(
            twitter_mentions=5000,
            twitter_bot_ratio=0.3,
            tiktok_videos=100,
            reddit_mentions=50,
        )
        assert detected is False


# ─── Comprehensive analysis ──────────────────────────────────────────────────

class TestAnalyzeManipulation:
    def test_analyze_manipulation_full(self, tmp_data_dir):
        """Comprehensive analysis combining all detectors."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)

        funder = "0xbotfunder"
        holders = [
            {"wallet_age_days": 1.0, "funded_from": funder, "address": f"0xbot{i:04x}"}
            for i in range(25)
        ]

        result = detector.analyze_manipulation(
            token="FAKEPUMP",
            holders=holders,
            price_change_24h=300.0,
            volume_24h=1_000_000,
            market_cap=5_000_000,
            real_volume_pct=10.0,
            twitter_mentions=55000,
            twitter_bot_ratio=0.97,
            tiktok_videos=0,
            reddit_mentions=0,
            dev_selling_during_pump=True,
        )
        assert result.fake_pump_score > 0
        assert len(result.detected_patterns) >= 2
        assert len(result.evidence) > 0

    def test_fake_pump_threshold(self, tmp_data_dir):
        """Score >= 50 triggers is_fake_pump = True."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)

        funder = "0xbotfunder"
        holders = [
            {"wallet_age_days": 1.0, "funded_from": funder, "address": f"0xbot{i:04x}"}
            for i in range(25)
        ]

        result = detector.analyze_manipulation(
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
            buy_sell_ratio=5.0,
            dev_selling_during_pump=True,
        )
        if result.fake_pump_score >= 50:
            assert result.is_fake_pump is True

    def test_organic_pump_classification(self, tmp_data_dir):
        """Score < 50 means is_fake_pump = False."""
        db_path = tmp_data_dir / "manipulation_patterns.json"
        detector = ManipulationDetector(db_path=db_path)

        result = detector.analyze_manipulation(
            token="ORGANICPUMP",
            holders=[],
            price_change_24h=30.0,
            volume_24h=5_000_000,
            market_cap=50_000_000,
            real_volume_pct=90.0,
            twitter_mentions=1000,
            twitter_bot_ratio=0.2,
            tiktok_videos=200,
            reddit_mentions=50,
        )
        assert result.is_fake_pump is False
        assert result.fake_pump_score < 50

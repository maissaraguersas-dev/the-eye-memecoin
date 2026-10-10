"""
Tests for DevMatcher — rug pull signature detection.

Validates known rugger identification, honest dev detection, scoring
weights (+30% no lock, +25% dev holds >30%, +20% fresh wallet, +40%
serial rugger), urgency classification, specific rug signature detectors
(soft rug, hard rug, honey pot, team wallet cluster), and
self-improving DB updates.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from src.pattern.dev_matcher import DevMatcher, DevMatch


# ─── Known rugger / honest dev ───────────────────────────────────────────────

class TestKnownRugger:
    def test_is_known_rugger(self, tmp_data_dir):
        """Identifies a serial rugger from the database."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        is_rugger, count, profile = matcher.is_known_rugger(
            "0x9f1d2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e"
        )
        assert is_rugger is True
        assert count == 14
        assert profile is not None

    def test_is_not_rugger(self, tmp_data_dir):
        """Unknown address is not a rugger."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        is_rugger, count, profile = matcher.is_known_rugger(
            "0x0000000000000000000000000000000000000000"
        )
        assert is_rugger is False
        assert count == 0


class TestHonestDev:
    def test_is_honest_dev(self, tmp_data_dir):
        """Identifies a verified honest developer."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        is_honest, profile = matcher.is_honest_dev(
            "0x1111222233334444555566667777888899990000"
        )
        assert is_honest is True
        assert profile is not None
        assert profile.get("doxxed") is True

    def test_is_not_honest_dev(self, tmp_data_dir):
        """Unknown address is not an honest dev."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        is_honest, profile = matcher.is_honest_dev(
            "0x0000000000000000000000000000000000000000"
        )
        assert is_honest is False


# ─── Scoring weight tests ────────────────────────────────────────────────────

class TestAnalyzeDevScoring:
    def test_analyze_dev_no_liquidity_lock(self, tmp_data_dir):
        """+30% when liquidity is NOT locked."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        result = matcher.analyze_dev(
            "0xunknown",
            liquidity_locked=False,
        )
        assert result.rug_probability >= 30
        assert "no_liquidity_lock" in result.indicators_matched

    def test_analyze_dev_holds_30pct(self, tmp_data_dir):
        """+25% when dev holds >30% of supply."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        result = matcher.analyze_dev(
            "0xunknown",
            liquidity_locked=True,  # avoid the +30
            dev_holds_pct=35.0,
        )
        assert result.rug_probability >= 25
        assert "dev_holds_gt_30pct" in result.indicators_matched

    def test_analyze_dev_fresh_wallet(self, tmp_data_dir):
        """+20% for fresh dev wallet (<14 days)."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        result = matcher.analyze_dev(
            "0xunknown",
            liquidity_locked=True,
            dev_wallet_age_days=3,
        )
        assert result.rug_probability >= 20
        assert "fresh_dev_wallet_lt_14d" in result.indicators_matched

    def test_analyze_dev_known_rugger(self, tmp_data_dir):
        """+40% for known serial rugger."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        result = matcher.analyze_dev(
            "0x9f1d2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e",
            liquidity_locked=True,
        )
        assert result.rug_probability >= 40
        assert "known_serial_rugger" in result.indicators_matched
        assert result.known_serial_rugger is True

    def test_combined_indicators(self, tmp_data_dir):
        """Multiple indicators combine (30+25+20 = 75)."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        result = matcher.analyze_dev(
            "0xunknown",
            liquidity_locked=False,
            dev_holds_pct=40.0,
            dev_wallet_age_days=5,
        )
        # 30 (no lock) + 25 (holds >30%) + 20 (fresh wallet) = 75
        assert result.rug_probability >= 75


# ─── Urgency classification ──────────────────────────────────────────────────

class TestUrgencyClassification:
    def test_urgency_critical(self, tmp_data_dir):
        """CRITICAL urgency for hard_rug with probability >= 85."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)

        # Hard rug liquidity event
        liquidity_events = [{
            "type": "liquidity_removal",
            "percentage_removed": 100,
            "tx_hash": "0xabc123",
        }]
        result = matcher.analyze_dev(
            "0xunknown",
            liquidity_locked=False,
            liquidity_events=liquidity_events,
        )
        assert result.urgency == "CRITICAL"
        assert result.rug_type == "hard_rug"

    def test_urgency_high(self, tmp_data_dir):
        """HIGH urgency for known serial rugger."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        result = matcher.analyze_dev(
            "0x9f1d2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e",
            liquidity_locked=False,
        )
        assert result.urgency in ("HIGH", "CRITICAL")

    def test_urgency_medium(self, tmp_data_dir):
        """MEDIUM urgency when probability >= 40."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        result = matcher.analyze_dev(
            "0xunknown",
            liquidity_locked=False,
            dev_holds_pct=35.0,
        )
        # 30 + 25 = 55 => MEDIUM
        assert result.urgency in ("MEDIUM", "HIGH", "CRITICAL")

    def test_urgency_low(self, tmp_data_dir):
        """LOW urgency when few/no risk indicators."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        result = matcher.analyze_dev(
            "0xunknown",
            liquidity_locked=True,
            dev_holds_pct=5.0,
            dev_wallet_age_days=365,
            has_social_presence=True,
        )
        assert result.urgency == "LOW"


# ─── Specific rug signature detectors ────────────────────────────────────────

class TestDetectSoftRug:
    def test_detect_soft_rug(self, tmp_data_dir, soft_rug_dev_txs):
        """Detects gradual selling over 24-72 hours."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        detected, confidence, evidence = matcher.detect_soft_rug(
            soft_rug_dev_txs, total_supply=1_000_000
        )
        assert detected is True
        assert confidence > 0
        assert len(evidence) > 0

    def test_no_soft_rug_few_sells(self, tmp_data_dir):
        """No soft rug with fewer than 3 sells."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        txs = [
            {"timestamp": "2026-08-01T10:00:00Z", "value_eth": -1.0, "token_amount": 100000},
            {"timestamp": "2026-08-01T22:00:00Z", "value_eth": -1.5, "token_amount": 150000},
        ]
        detected, confidence, evidence = matcher.detect_soft_rug(txs)
        assert detected is False


class TestDetectHardRug:
    def test_detect_hard_rug(self, tmp_data_dir):
        """Detects single-tx liquidity removal >= 90%."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        events = [{
            "type": "liquidity_removal",
            "percentage_removed": 100,
            "tx_hash": "0xbadrug",
        }]
        detected, confidence, evidence = matcher.detect_hard_rug(events)
        assert detected is True
        assert confidence >= 80
        assert any("CRITICAL" in e for e in evidence)

    def test_no_hard_rug_partial_removal(self, tmp_data_dir):
        """No hard rug for removal < 90%."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        events = [{
            "type": "liquidity_removal",
            "percentage_removed": 30,
            "tx_hash": "0xpartial",
        }]
        detected, confidence, evidence = matcher.detect_hard_rug(events)
        assert detected is False


class TestDetectHoneyPot:
    def test_detect_honey_pot_sell_blocked(self, tmp_data_dir):
        """Detects sell-blocking contract (honey pot)."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        analysis = {
            "sell_simulation_failed": True,
            "has_blacklist_function": True,
        }
        detected, confidence, evidence = matcher.detect_honey_pot(analysis)
        assert detected is True
        assert confidence >= 85

    def test_no_honey_pot_clean_contract(self, tmp_data_dir):
        """No honey pot for clean contract."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)
        analysis = {}
        detected, confidence, evidence = matcher.detect_honey_pot(analysis)
        assert detected is False


class TestDetectTeamWalletCluster:
    def test_detect_team_wallet_cluster(self, tmp_data_dir):
        """Detects coordinated wallet cluster funded from same source."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)

        funder = "0xfunder1234"
        holders = [
            {"address": f"0xholder{i}", "funded_from": funder, "percentage": 8.0}
            for i in range(7)
        ]
        detected, confidence, evidence = matcher.detect_team_wallet_cluster(
            holders, "0xdev"
        )
        assert detected is True
        assert confidence >= 70
        assert any("cluster" in e.lower() for e in evidence)

    def test_no_team_wallet_cluster_few_wallets(self, tmp_data_dir):
        """No cluster detected with <5 wallets from same source."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)

        funder = "0xfunder1234"
        holders = [
            {"address": f"0xholder{i}", "funded_from": funder, "percentage": 8.0}
            for i in range(3)
        ]
        detected, confidence, evidence = matcher.detect_team_wallet_cluster(
            holders, "0xdev"
        )
        assert detected is False


# ─── Self-improving DB update ────────────────────────────────────────────────

class TestAddRugObservation:
    def test_add_rug_observation_existing(self, tmp_data_dir):
        """Adding observation to known rugger increments rug_count."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)

        rugger_addr = "0x9f1d2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e"
        matcher.add_rug_observation(rugger_addr, {
            "project": "$NEWRUG",
            "rug_type": "hard_rug",
            "loss_usd": 100000,
        })

        # Reload and verify count increased
        matcher2 = DevMatcher(db_path=db_path)
        is_rugger, count, profile = matcher2.is_known_rugger(rugger_addr)
        assert is_rugger is True
        assert count >= 15  # was 14

    def test_add_rug_observation_new(self, tmp_data_dir):
        """Adding observation for unknown dev creates a new entry."""
        db_path = tmp_data_dir / "dev_signatures.json"
        matcher = DevMatcher(db_path=db_path)

        new_addr = "0xnewrugger1234567890abcdef1234567890abcdef12"
        matcher.add_rug_observation(new_addr, {
            "label": "New Rugger",
            "project": "$SCAM",
            "rug_type": "soft_rug",
            "loss_usd": 50000,
            "chain": "eth",
        })

        matcher2 = DevMatcher(db_path=db_path)
        is_rugger, count, profile = matcher2.is_known_rugger(new_addr)
        assert is_rugger is True
        assert count == 1

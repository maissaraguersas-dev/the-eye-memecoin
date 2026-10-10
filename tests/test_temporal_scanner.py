"""
Tests for TemporalAnalyzer — time-of-day / day-of-week risk prediction.

Validates all temporal window detectors (rug hour, FOMO peak, dead zone,
golden hour, weekend trap), risk scoring, attack frequency prediction,
result structure, and self-improving observations.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.pattern.temporal_analyzer import (
    TemporalAnalyzer,
    TemporalRiskResult,
    SCORE_ATTACK_FREQUENCY_3X,
    SCORE_GEOGRAPHIC_GAP,
    SCORE_WEEKEND,
)


# Helper: create an analyzer with a fake "now" time

def _make_analyzer_with_time(tmp_data_dir, fake_now):
    """Create a TemporalAnalyzer with _now_utc patched to return fake_now."""
    db_path = tmp_data_dir / "temporal_patterns.json"
    analyzer = TemporalAnalyzer(db_path=db_path)
    analyzer._now_utc = lambda: fake_now
    return analyzer


# ─── Rug Hour (02:00-05:00 UTC) ─────────────────────────────────────────────

class TestDetectRugHour:
    def test_detect_rug_hour_inside(self, tmp_data_dir):
        """02:00-05:00 UTC is the rug hour."""
        fake_now = datetime(2026, 8, 11, 3, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_rug_hour() is True

    def test_detect_rug_hour_outside(self, tmp_data_dir):
        """14:00 UTC is NOT the rug hour."""
        fake_now = datetime(2026, 8, 11, 14, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_rug_hour() is False

    def test_detect_rug_hour_boundary_start(self, tmp_data_dir):
        """02:00 UTC is inside rug hour (inclusive start)."""
        fake_now = datetime(2026, 8, 11, 2, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_rug_hour() is True

    def test_detect_rug_hour_boundary_end(self, tmp_data_dir):
        """05:00 UTC is outside rug hour (exclusive end)."""
        fake_now = datetime(2026, 8, 11, 5, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_rug_hour() is False


# ─── FOMO Peak (18:00-22:00 UTC) ────────────────────────────────────────────

class TestDetectFomoPeak:
    def test_detect_fomo_peak_inside(self, tmp_data_dir):
        """19:00 UTC is inside FOMO peak."""
        fake_now = datetime(2026, 8, 11, 19, 30, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_fomo_peak() is True

    def test_detect_fomo_peak_outside(self, tmp_data_dir):
        """10:00 UTC is NOT FOMO peak."""
        fake_now = datetime(2026, 8, 11, 10, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_fomo_peak() is False


# ─── Dead Zone (08:00-12:00 UTC) ────────────────────────────────────────────

class TestDetectDeadZone:
    def test_detect_dead_zone_inside(self, tmp_data_dir):
        """10:00 UTC is inside the dead zone."""
        fake_now = datetime(2026, 8, 11, 10, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_dead_zone() is True

    def test_detect_dead_zone_outside(self, tmp_data_dir):
        """15:00 UTC is NOT the dead zone."""
        fake_now = datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_dead_zone() is False


# ─── Golden Hour (14:00-16:00 UTC) ──────────────────────────────────────────

class TestDetectGoldenHour:
    def test_detect_golden_hour_inside(self, tmp_data_dir):
        """15:00 UTC is inside golden hour."""
        fake_now = datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_golden_hour() is True

    def test_detect_golden_hour_outside(self, tmp_data_dir):
        """20:00 UTC is NOT golden hour."""
        fake_now = datetime(2026, 8, 11, 20, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_golden_hour() is False


# ─── Weekend Trap (Friday 20:00 - Monday 08:00 UTC) ─────────────────────────

class TestDetectWeekendTrap:
    def test_detect_weekend_trap_saturday(self, tmp_data_dir):
        """Saturday 10:00 UTC is inside weekend trap."""
        # 2026-08-15 is a Saturday
        fake_now = datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_weekend_trap() is True

    def test_detect_weekend_trap_friday_night(self, tmp_data_dir):
        """Friday 21:00 UTC is inside weekend trap."""
        # 2026-08-14 is a Friday
        fake_now = datetime(2026, 8, 14, 21, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_weekend_trap() is True

    def test_detect_weekend_trap_wednesday(self, tmp_data_dir):
        """Wednesday 10:00 UTC is NOT weekend trap."""
        # 2026-08-12 is a Wednesday
        fake_now = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        assert analyzer.detect_weekend_trap() is False


# ─── Hourly risk score ───────────────────────────────────────────────────────

class TestCalculateHourlyRiskScore:
    def test_risk_score_rug_hour(self, tmp_data_dir):
        """Risk score is high during rug hour."""
        fake_now = datetime(2026, 8, 11, 3, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        score = analyzer.calculate_hourly_risk_score()
        assert score >= 40  # at least the rug_hour base

    def test_risk_score_golden_hour(self, tmp_data_dir):
        """Risk score is low during golden hour."""
        fake_now = datetime(2026, 8, 11, 15, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        score = analyzer.calculate_hourly_risk_score()
        # Golden hour is protective; score should be low
        assert score <= 30

    def test_risk_score_bounded(self, tmp_data_dir):
        """Risk score is always between 0 and 100."""
        for hour in range(24):
            fake_now = datetime(2026, 8, 11, hour, 0, 0, tzinfo=timezone.utc)
            analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
            score = analyzer.calculate_hourly_risk_score()
            assert 0 <= score <= 100


# ─── Attack frequency prediction ─────────────────────────────────────────────

class TestPredictAttackFrequency:
    def test_predict_attack_frequency_uses_data(self, tmp_data_dir):
        """Predicts attack frequency from historical data."""
        db_path = tmp_data_dir / "temporal_patterns.json"
        analyzer = TemporalAnalyzer(db_path=db_path)

        # Rug hour (03:00) should have high multiplier
        rug_hour_pred = analyzer.predict_attack_frequency(hour_utc=3, day_of_week=5)
        # Non-rug hour (15:00) should have lower multiplier
        safe_pred = analyzer.predict_attack_frequency(hour_utc=15, day_of_week=2)
        assert rug_hour_pred > safe_pred

    def test_predict_attack_frequency_baseline(self, tmp_data_dir):
        """Hours with no data default to 1.0 multiplier."""
        db_path = tmp_data_dir / "temporal_patterns.json"
        # Create a minimal DB with no hourly data
        minimal_db = {
            "version": "1.0.0",
            "temporal_windows": [],
            "hourly_attack_frequency": {},
            "day_of_week_attack_frequency": {},
            "geographic_gaps": [],
            "historical_confirmed_rugs": [],
        }
        db_path2 = tmp_data_dir / "minimal_temporal.json"
        db_path2.write_text(json.dumps(minimal_db))
        analyzer = TemporalAnalyzer(db_path=db_path2)

        pred = analyzer.predict_attack_frequency(hour_utc=12, day_of_week=2)
        assert pred == 1.0


# ─── Temporal risk result structure ──────────────────────────────────────────

class TestTemporalRiskResultStructure:
    def test_temporal_risk_result_all_fields(self, tmp_data_dir):
        """All fields are present in TemporalRiskResult."""
        fake_now = datetime(2026, 8, 11, 3, 0, 0, tzinfo=timezone.utc)
        analyzer = _make_analyzer_with_time(tmp_data_dir, fake_now)
        result = analyzer.calculate_temporal_risk()

        # Check all expected fields exist
        assert hasattr(result, "current_utc_time")
        assert hasattr(result, "risk_score")
        assert hasattr(result, "active_windows")
        assert hasattr(result, "recommendations")
        assert hasattr(result, "is_rug_hour")
        assert hasattr(result, "is_fomo_peak")
        assert hasattr(result, "is_dead_zone")
        assert hasattr(result, "is_weekend_trap")
        assert hasattr(result, "is_golden_hour")
        assert hasattr(result, "attack_frequency_multiplier")
        assert hasattr(result, "liquidity_thinning_pct")
        assert hasattr(result, "geographic_gap")
        assert hasattr(result, "evidence")

        # Validate types
        assert isinstance(result.risk_score, float)
        assert isinstance(result.active_windows, list)
        assert isinstance(result.recommendations, list)
        assert isinstance(result.evidence, list)
        assert 0 <= result.risk_score <= 100


# ─── Self-improving observation ──────────────────────────────────────────────

class TestAddConfirmedRugObservation:
    def test_add_confirmed_rug_observation(self, tmp_data_dir):
        """Adding confirmed rug updates historical data and frequency."""
        db_path = tmp_data_dir / "temporal_patterns.json"
        analyzer = TemporalAnalyzer(db_path=db_path)

        original_rugs = len(analyzer._db.get("historical_confirmed_rugs", []))

        analyzer.add_confirmed_rug_observation({
            "project": "$NEWSCAM",
            "date": "2026-08-12T03:15:00Z",
            "rug_type": "hard_rug",
            "chain": "eth",
            "loss_usd": 50000,
            "dev_address": "0xdev123",
        })

        # Reload and verify
        analyzer2 = TemporalAnalyzer(db_path=db_path)
        new_rugs = len(analyzer2._db.get("historical_confirmed_rugs", []))
        assert new_rugs == original_rugs + 1

    def test_add_rug_observation_missing_keys(self, tmp_data_dir):
        """Observation with missing required keys is rejected."""
        db_path = tmp_data_dir / "temporal_patterns.json"
        analyzer = TemporalAnalyzer(db_path=db_path)
        original_rugs = len(analyzer._db.get("historical_confirmed_rugs", []))

        # Missing 'chain' key
        analyzer.add_confirmed_rug_observation({
            "project": "$BAD",
            "date": "2026-08-12T03:15:00Z",
            "rug_type": "hard_rug",
            # missing chain
        })

        new_rugs = len(analyzer._db.get("historical_confirmed_rugs", []))
        assert new_rugs == original_rugs  # no change

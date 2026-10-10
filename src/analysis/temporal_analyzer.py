"""THE EYE — Temporal Risk Analyzer

Analyzes time-of-day risk patterns for memecoin trading.

| Window       | UTC Time    | Risk                                         |
|--------------|-------------|----------------------------------------------|
| 🚨 Rug Hour  | 02:00-05:00 | 78% of rugs happen here                      |
| 😱 FOMO Peak | 18:00-22:00 | Prices peak → overnight dump                 |
| 💀 Dead Zone | 08:00-12:00 | Lowest liquidity                             |
| ✨ Golden Hour| 14:00-16:00 | Best time to enter                           |
"""
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

from config.settings import settings


@dataclass
class TimeWindow:
    name: str
    start_hour: int
    end_hour: int
    risk_level: str  # "critical", "high", "medium", "low", "optimal"
    risk_score: float  # 0-100, higher = more dangerous
    description: str
    emoji: str


@dataclass
class TemporalResult:
    current_window: TimeWindow
    utc_hour: float
    risk_score: float  # 0-100
    recommendation: str
    all_windows: list[TimeWindow]
    timestamp: float = 0.0


class TemporalAnalyzer:
    """Analyze time-based risk patterns for memecoin markets."""

    # Based on empirical data: 78% of rugs happen during low-liquidity hours
    WINDOWS = None  # loaded from settings

    def __init__(self):
        self._load_windows()

    def _load_windows(self):
        t = settings.all.get("temporal", {})
        self.WINDOWS = [
            TimeWindow(
                name="Rug Hour",
                start_hour=t.get("rug_hour_start", 2),
                end_hour=t.get("rug_hour_end", 5),
                risk_level="critical",
                risk_score=85,
                description="78% of rug pulls happen during these hours. Low liquidity, "
                           "low visibility — developers exploit the cover of low activity.",
                emoji="🚨",
            ),
            TimeWindow(
                name="FOMO Peak",
                start_hour=t.get("fomo_peak_start", 18),
                end_hour=t.get("fomo_peak_end", 22),
                risk_level="high",
                risk_score=70,
                description="Prices tend to peak during evening hours (US/EU overlap). "
                           "Overnight dumps are common — FOMO buys become bag holds.",
                emoji="😱",
            ),
            TimeWindow(
                name="Dead Zone",
                start_hour=t.get("dead_zone_start", 8),
                end_hour=t.get("dead_zone_end", 12),
                risk_level="medium",
                risk_score=50,
                description="Lowest liquidity period. Spread is wider, slippage higher. "
                           "Not ideal for large entries but okay for limit orders.",
                emoji="💀",
            ),
            TimeWindow(
                name="Golden Hour",
                start_hour=t.get("golden_hour_start", 14),
                end_hour=t.get("golden_hour_end", 16),
                risk_level="optimal",
                risk_score=20,
                description="Best time to enter positions. Liquidity is recovering, "
                           "market is active but not overheated. Optimal entry window.",
                emoji="✨",
            ),
            TimeWindow(
                name="Neutral",
                start_hour=0,
                end_hour=24,
                risk_level="low",
                risk_score=35,
                description="Standard market activity. No extreme time-based risk factors.",
                emoji="📊",
            ),
        ]

    def get_current_window(self) -> TimeWindow:
        """Get the current time window based on UTC time."""
        now = datetime.now(timezone.utc)
        hour = now.hour + now.minute / 60

        for window in self.WINDOWS[:-1]:  # skip "Neutral" (fallback)
            if window.start_hour <= hour < window.end_hour:
                return window
        return self.WINDOWS[-1]  # Neutral

    def analyze(self) -> TemporalResult:
        """Full temporal analysis of current time risk."""
        now = datetime.now(timezone.utc)
        hour = now.hour + now.minute / 60
        current = self.get_current_window()

        # Generate recommendation
        recommendations = {
            "critical": "⚠️  HIGH DANGER: Rug hour active. Avoid new positions. "
                       "Watch for dev sells and liquidity removal.",
            "high": "⚠️  CAUTION: FOMO peak hours. Prices may be artificially inflated. "
                   "Consider taking profits rather than entering.",
            "medium": "💀 Low liquidity period. Use limit orders, expect wider spreads. "
                     "Not ideal for large market orders.",
            "optimal": "✨ OPTIMAL ENTRY WINDOW: Good liquidity, moderate activity. "
                      "Best time for new positions.",
            "low": "📊 Standard market conditions. Normal risk management applies.",
        }
        recommendation = recommendations.get(current.risk_level, recommendations["low"])

        return TemporalResult(
            current_window=current,
            utc_hour=hour,
            risk_score=current.risk_score,
            recommendation=recommendation,
            all_windows=self.WINDOWS,
            timestamp=time.time(),
        )

    def get_rug_hour_active(self) -> bool:
        """Check if we're currently in rug hour — for alert suppression."""
        return self.get_current_window().name == "Rug Hour"

    def get_optimal_entry(self) -> bool:
        """Check if current time is optimal for entry."""
        return self.get_current_window().name == "Golden Hour"

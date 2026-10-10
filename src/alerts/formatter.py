"""THE EYE — Alert Formatter

Formats all analysis results into the WHO/WHAT/WHY/WHEN/HOW/CONFIDENCE/URGENCY framework.
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from src.scanner.market_scanner import TokenScanResult, MarketScanResult
from src.analysis.prediction import PredictionType
from src.analysis.rug_probability import RugResult
from src.analysis.pump_scorer import PumpResult
from src.analysis.temporal_analyzer import TemporalResult


@dataclass
class Alert:
    alert_type: str  # "rug", "pump", "whale", "temporal", "opportunity", "risk"
    title: str
    who: str  # who is involved
    what: str  # what is happening
    why: str  # why it matters
    when: str  # when it's happening
    how: str  # how to act
    confidence: float  # 0-100
    urgency: str  # "low", "medium", "high", "critical"
    token_symbol: str = ""
    token_address: str = ""
    chain: str = ""
    details: dict = field(default_factory=dict)
    timestamp: float = 0.0

    def to_text(self) -> str:
        """Format alert as readable text."""
        emoji_map = {
            "rug": "🚨", "pump": "🚀", "whale": "🐋",
            "temporal": "⏰", "opportunity": "✨", "risk": "⚠️"
        }
        emoji = emoji_map.get(self.alert_type, "📊")
        lines = [
            f"{emoji} {self.title}",
            f"",
            f"WHO:     {self.who}",
            f"WHAT:    {self.what}",
            f"WHY:     {self.why}",
            f"WHEN:    {self.when}",
            f"HOW:     {self.how}",
            f"CONF:    {self.confidence:.0f}%",
            f"URGENCY: {self.urgency.upper()}",
        ]
        return "\n".join(lines)

    def to_telegram(self) -> str:
        """Format for Telegram (markdown)."""
        emoji_map = {"rug": "🚨", "pump": "🚀", "whale": "🐋",
                     "temporal": "⏰", "opportunity": "✨", "risk": "⚠️"}
        emoji = emoji_map.get(self.alert_type, "📊")
        return (
            f"{emoji} *{self.title}*\n\n"
            f"*WHO:* {self.who}\n"
            f"*WHAT:* {self.what}\n"
            f"*WHY:* {self.why}\n"
            f"*WHEN:* {self.when}\n"
            f"*HOW:* {self.how}\n"
            f"*CONF:* {self.confidence:.0f}% | *URGENCY:* {self.urgency.upper()}"
        )

    def to_discord(self) -> str:
        """Format for Discord (markdown)."""
        return self.to_telegram()  # same format works for Discord


class AlertFormatter:
    """Convert scan results into structured alerts."""

    def format_token_alert(self, scan: TokenScanResult) -> list[Alert]:
        """Generate alerts from a single token scan result."""
        alerts = []
        token = scan.token
        sym = token.symbol or token.address[:8]

        # Rug alert
        if scan.rug_result and scan.rug_result.rug_probability > 50:
            rug = scan.rug_result
            alerts.append(Alert(
                alert_type="rug",
                title=f"RUG ALERT: {sym}",
                who=f"Token {sym} on {token.chain.upper()}",
                what=f"Rug probability: {rug.rug_probability:.0f}% — {rug.risk_level} risk",
                why="; ".join(rug.indicators + rug.dev_flags) or "Multiple risk factors detected",
                when="NOW" if rug.rug_probability > 75 else "Active monitoring",
                how="AVOID" if rug.rug_probability > 75 else "Monitor closely, set stop-loss",
                confidence=rug.confidence,
                urgency="critical" if rug.rug_probability > 75 else
                        "high" if rug.rug_probability > 55 else "medium",
                token_symbol=sym,
                token_address=token.address,
                chain=token.chain,
                timestamp=time.time(),
            ))

        # Pump opportunity
        if scan.pump_result and scan.pump_result.moon_score > 50:
            pump = scan.pump_result
            alerts.append(Alert(
                alert_type="pump",
                title=f"MOON SIGNAL: {sym}",
                who=f"Token {sym} — organic momentum detected",
                what=f"Moon score: {pump.moon_score:.0f}% — {pump.verdict.replace('_', ' ')}",
                why="; ".join(pump.evidence[:3]) or "Organic buying pressure",
                when="NOW" if pump.moon_score > 70 else "Building momentum",
                how="Consider entry with stop-loss" if pump.fake_pump_score < 30 else "CAUTION — possible fake pump",
                confidence=pump.confidence,
                urgency="high" if pump.moon_score > 70 else "medium",
                token_symbol=sym,
                token_address=token.address,
                chain=token.chain,
                timestamp=time.time(),
            ))

        # Prediction alert
        if scan.prediction and scan.prediction.confidence > 60:
            pred = scan.prediction
            type_names = {
                PredictionType.RUG_IMMINENT: "Rug Imminent",
                PredictionType.PUMP_LIKELY: "Pump Likely",
                PredictionType.DUMP_COMING: "Dump Coming",
                PredictionType.ACCUMULATION: "Accumulation Phase",
            }
            if pred.prediction_type in type_names:
                alert_type = "risk" if pred.prediction_type in [
                    PredictionType.RUG_IMMINENT, PredictionType.DUMP_COMING
                ] else "opportunity"
                alerts.append(Alert(
                    alert_type=alert_type,
                    title=f"PREDICTION: {sym} — {type_names[pred.prediction_type]}",
                    who=f"Token {sym} on {token.chain.upper()}",
                    what=f"Prediction: {pred.prediction_type.value} | "
                         f"Direction: {pred.direction} | Magnitude: {pred.magnitude}",
                    why="; ".join(pred.reasoning[:3]) or "Pattern analysis",
                    when=f"Timing: {pred.timing}",
                    how=f"Risk/Reward: {pred.risk_reward:.1f}x",
                    confidence=pred.confidence,
                    urgency=pred.urgency,
                    token_symbol=sym,
                    token_address=token.address,
                    chain=token.chain,
                    timestamp=time.time(),
                ))

        return alerts

    def format_market_alerts(self, result: MarketScanResult) -> list[Alert]:
        """Generate all alerts from a market-wide scan."""
        alerts = []

        # Token-level alerts
        for sr in result.opportunities + result.risks + result.rug_alerts + result.pump_alerts:
            alerts.extend(self.format_token_alert(sr))

        # Temporal alert
        if result.temporal and result.temporal.risk_score > 60:
            t = result.temporal
            w = t.current_window
            alerts.append(Alert(
                alert_type="temporal",
                title=f"TIME ALERT: {w.emoji} {w.name}",
                who="Market-wide",
                what=f"Current window: {w.name} (risk: {w.risk_score:.0f}%)",
                why=w.description,
                when=f"UTC {t.utc_hour:.1f}h — {w.start_hour}:00-{w.end_hour}:00",
                how=t.recommendation,
                confidence=80,
                urgency="high" if w.risk_score > 70 else "medium",
                timestamp=time.time(),
            ))

        # Sort by urgency
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(key=lambda a: (urgency_order.get(a.urgency, 3), -a.confidence))

        return alerts

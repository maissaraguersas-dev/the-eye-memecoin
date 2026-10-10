"""THE EYE — Prediction Engine

Generates timing + magnitude forecasts based on all signals.
What WILL happen, WHEN, and HOW BIG.
"""
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class PredictionType(Enum):
    RUG_IMMINENT = "rug_imminent"
    PUMP_LIKELY = "pump_likely"
    DUMP_COMING = "dump_coming"
    ACCUMULATION = "accumulation"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class Prediction:
    token_address: str
    token_symbol: str
    chain: str
    prediction_type: PredictionType
    timing: str  # "imminent", "hours", "days", "uncertain"
    magnitude: str  # "minimal", "moderate", "significant", "extreme"
    direction: str  # "up", "down", "sideways"
    confidence: float  # 0-100
    reasoning: list[str] = field(default_factory=list)
    risk_reward: float = 0.0  # risk/reward ratio
    urgency: str = "low"  # "low", "medium", "high", "critical"
    timestamp: float = 0.0


@dataclass
class PredictionLogEntry:
    prediction_id: str
    token_address: str
    token_symbol: str
    prediction_type: str
    predicted_at: float
    outcome: str = "pending"  # "pending", "confirmed", "rejected", "expired"
    outcome_at: float = 0.0
    confidence: float = 0.0


class PredictionEngine:
    """Generate predictions with timing + magnitude from all signal sources."""

    DATA_DIR = Path(__file__).parent.parent.parent / "src" / "data"
    LOG_FILE = DATA_DIR / "prediction_log.json"

    def __init__(self):
        self.log: list[PredictionLogEntry] = []
        self._load_log()

    def _load_log(self):
        if self.LOG_FILE.exists():
            with open(self.LOG_FILE) as f:
                data = json.load(f)
            for entry in data:
                self.log.append(PredictionLogEntry(**entry))

    def _save_log(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "prediction_id": e.prediction_id,
                "token_address": e.token_address,
                "token_symbol": e.token_symbol,
                "prediction_type": e.prediction_type,
                "predicted_at": e.predicted_at,
                "outcome": e.outcome,
                "outcome_at": e.outcome_at,
                "confidence": e.confidence,
            }
            for e in self.log[-1000:]  # keep last 1000
        ]
        with open(self.LOG_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def predict(self, token_address: str, token_symbol: str, chain: str = "eth",
                rug_probability: float = 0.0,
                moon_score: float = 0.0,
                fake_pump_score: float = 0.0,
                price_change_24h: float = 0.0,
                volume_change_24h: float = 0.0,
                buy_sell_ratio: float = 1.0,
                temporal_risk: float = 50.0,
                whale_bearish: bool = False,
                whale_bullish: bool = False,
                social_sentiment: float = 0.0,
                holders_change_24h: int = 0) -> Prediction:
        """Generate a prediction from all available signals."""

        reasoning = []
        prediction_type = PredictionType.STABLE
        timing = "uncertain"
        magnitude = "moderate"
        direction = "sideways"
        confidence = 30.0
        urgency = "low"

        # ── Rug imminent ────────────────────────────────────────────
        if rug_probability > 75:
            prediction_type = PredictionType.RUG_IMMINENT
            direction = "down"
            timing = "imminent" if rug_probability > 90 else "hours"
            magnitude = "extreme"
            urgency = "critical"
            confidence = rug_probability * 0.9
            reasoning.append(f"Rug probability {rug_probability:.0f}% — IMMUNE DANGER")
            if temporal_risk > 70:
                reasoning.append("Active during high-risk time window")
                confidence = min(100, confidence + 5)

        # ── Pump likely ─────────────────────────────────────────────
        elif moon_score > 60 and fake_pump_score < 30:
            prediction_type = PredictionType.PUMP_LIKELY
            direction = "up"
            timing = "hours" if moon_score > 70 else "days"
            magnitude = "significant" if moon_score > 70 else "moderate"
            confidence = moon_score * 0.8
            urgency = "high" if moon_score > 75 else "medium"
            reasoning.append(f"Organic pump score {moon_score:.0f}% — real momentum")
            if whale_bullish:
                reasoning.append("Whale accumulation confirmed")
                confidence = min(100, confidence + 10)
            if social_sentiment > 0.5:
                reasoning.append(f"Positive social sentiment ({social_sentiment:.2f})")
            if holders_change_24h > 50:
                reasoning.append(f"+{holders_change_24h} new holders — growing community")

        # ── Dump coming ─────────────────────────────────────────────
        elif fake_pump_score > 60 or (whale_bearish and price_change_24h > 20):
            prediction_type = PredictionType.DUMP_COMING
            direction = "down"
            timing = "hours"
            magnitude = "significant"
            confidence = fake_pump_score * 0.7
            urgency = "high"
            reasoning.append(f"Fake pump score {fake_pump_score:.0f}% — manipulation likely")
            if whale_bearish:
                reasoning.append("Whale selling pressure detected")

        # ── Accumulation ────────────────────────────────────────────
        elif (volume_change_24h > 30 and abs(price_change_24h) < 5
              and buy_sell_ratio > 1.5 and whale_bullish):
            prediction_type = PredictionType.ACCUMULATION
            direction = "up"
            timing = "days"
            magnitude = "moderate"
            confidence = 55
            urgency = "low"
            reasoning.append("Quiet accumulation: volume rising, price stable, whales buying")

        # ── Volatile ────────────────────────────────────────────────
        elif abs(price_change_24h) > 30 and buy_sell_ratio > 2:
            prediction_type = PredictionType.VOLATILE
            direction = "up" if price_change_24h > 0 else "down"
            timing = "hours"
            magnitude = "significant"
            confidence = 45
            urgency = "medium"
            reasoning.append(f"High volatility: {price_change_24h:+.0f}% in 24h")

        # ── Risk/Reward ─────────────────────────────────────────────
        if prediction_type == PredictionType.PUMP_LIKELY:
            risk_reward = (100 - rug_probability) / max(100 - confidence, 1)
        elif prediction_type == PredictionType.RUG_IMMINENT:
            risk_reward = 0.0
        elif prediction_type == PredictionType.ACCUMULATION:
            risk_reward = 3.0
        else:
            risk_reward = 1.0

        pred = Prediction(
            token_address=token_address,
            token_symbol=token_symbol,
            chain=chain,
            prediction_type=prediction_type,
            timing=timing,
            magnitude=magnitude,
            direction=direction,
            confidence=round(confidence, 1),
            reasoning=reasoning,
            risk_reward=round(risk_reward, 2),
            urgency=urgency,
            timestamp=time.time(),
        )

        # Log prediction
        self._log_prediction(pred)
        return pred

    def _log_prediction(self, pred: Prediction):
        """Log prediction for self-improvement tracking."""
        entry = PredictionLogEntry(
            prediction_id=f"{pred.token_symbol}_{int(pred.timestamp)}",
            token_address=pred.token_address,
            token_symbol=pred.token_symbol,
            prediction_type=pred.prediction_type.value,
            predicted_at=pred.timestamp,
            confidence=pred.confidence,
        )
        self.log.append(entry)
        self._save_log()

    def resolve_prediction(self, prediction_id: str, outcome: str):
        """Mark a prediction as confirmed/rejected — self-improvement loop."""
        for entry in self.log:
            if entry.prediction_id == prediction_id and entry.outcome == "pending":
                entry.outcome = outcome
                entry.outcome_at = time.time()
                break
        self._save_log()

    def get_accuracy(self) -> dict:
        """Calculate prediction accuracy for self-improvement reporting."""
        confirmed = sum(1 for e in self.log if e.outcome == "confirmed")
        rejected = sum(1 for e in self.log if e.outcome == "rejected")
        pending = sum(1 for e in self.log if e.outcome == "pending")
        total = confirmed + rejected
        accuracy = confirmed / total if total > 0 else 0
        return {
            "total_predictions": len(self.log),
            "confirmed": confirmed,
            "rejected": rejected,
            "pending": pending,
            "accuracy": f"{accuracy:.1%}",
        }

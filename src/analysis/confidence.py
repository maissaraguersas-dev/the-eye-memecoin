"""THE EYE — Confidence Weighting Engine

Applies recency × frequency weighting to all signals.
Recent signals are weighted higher. Frequent patterns get confidence boosts.
"""
import time
from dataclasses import dataclass


@dataclass
class SignalObservation:
    signal_type: str
    token_address: str
    observed_at: float
    strength: float  # 0-1
    source: str


class ConfidenceEngine:
    """Weight signals by recency and frequency — the core of self-improvement."""

    # Recency decay: signals lose weight over time
    RECENCY_HALF_LIFE_HOURS = 24.0  # signal loses half its weight every 24h

    # Frequency boost: repeated observations increase confidence
    FREQUENCY_BOOST_FACTOR = 0.1  # each repeat adds 10% confidence (capped)

    def __init__(self):
        self.observations: list[SignalObservation] = []

    def record(self, signal_type: str, token_address: str,
               strength: float = 1.0, source: str = "unknown"):
        """Record a new signal observation."""
        obs = SignalObservation(
            signal_type=signal_type,
            token_address=token_address,
            observed_at=time.time(),
            strength=min(1.0, max(0.0, strength)),
            source=source,
        )
        self.observations.append(obs)

    def recency_weight(self, observed_at: float) -> float:
        """Calculate recency weight using exponential decay.
        Most recent = 1.0, decays to 0.5 after half-life, approaches 0.
        """
        age_hours = (time.time() - observed_at) / 3600
        decay = 0.5 ** (age_hours / self.RECENCY_HALF_LIFE_HOURS)
        return max(0.01, min(1.0, decay))

    def frequency_count(self, signal_type: str, token_address: str,
                         window_hours: float = 72.0) -> int:
        """Count how many times this signal was observed for this token recently."""
        cutoff = time.time() - (window_hours * 3600)
        return sum(1 for obs in self.observations
                   if obs.signal_type == signal_type
                   and obs.token_address == token_address
                   and obs.observed_at >= cutoff)

    def frequency_weight(self, signal_type: str, token_address: str) -> float:
        """Calculate frequency weight: repeated observations boost confidence.
        Returns 1.0 + boost, where boost = count * FREQUENCY_BOOST_FACTOR, capped at 1.0.
        """
        count = self.frequency_count(signal_type, token_address)
        boost = min(1.0, count * self.FREQUENCY_BOOST_FACTOR)
        return 1.0 + boost

    def combined_confidence(self, signal_type: str, token_address: str,
                             raw_confidence: float,
                             observed_at: float = None) -> float:
        """Apply recency × frequency weighting to a raw confidence score.
        Returns confidence 0-100.
        """
        if observed_at is None:
            observed_at = time.time()

        recency = self.recency_weight(observed_at)
        frequency = self.frequency_weight(signal_type, token_address)

        weighted = raw_confidence * recency * frequency
        return min(100.0, max(0.0, weighted))

    def get_token_signals(self, token_address: str,
                           window_hours: float = 72.0) -> list[SignalObservation]:
        """Get all recent signals for a token."""
        cutoff = time.time() - (window_hours * 3600)
        return [obs for obs in self.observations
                if obs.token_address == token_address
                and obs.observed_at >= cutoff]

    def get_top_signals(self, limit: int = 20) -> list[tuple[str, str, float]]:
        """Get the top signals across all tokens by recency-weighted strength."""
        scored = []
        for obs in self.observations:
            weight = self.recency_weight(obs.observed_at) * obs.strength
            scored.append((obs.signal_type, obs.token_address, weight))
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:limit]

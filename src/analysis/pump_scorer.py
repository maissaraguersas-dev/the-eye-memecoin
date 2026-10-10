"""THE EYE — Pump Score Engine

Determines if a price pump is organic (real moon) or fake (manipulation).
Scores: moon_score (organic potential) vs fake_pump_score (manipulation likelihood).
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from src.pattern.manipulation_detector import ManipulationDetector, MarketSnapshot


@dataclass
class PumpResult:
    token_address: str
    token_symbol: str
    moon_score: float  # 0-100, organic pump potential
    fake_pump_score: float  # 0-100, manipulation likelihood
    verdict: str  # "organic_moon", "likely_organic", "suspicious", "likely_fake", "fake_pump"
    manipulation_types: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = 0.0


class PumpScorer:
    """Score whether a pump is organic (moon) or fake (manipulation)."""

    def __init__(self, manipulation_detector: Optional[ManipulationDetector] = None):
        self.detector = manipulation_detector or ManipulationDetector()

    def score(self, snap: MarketSnapshot) -> PumpResult:
        """Calculate moon vs fake pump scores from market snapshot."""

        moon_score = 0.0
        fake_score = 0.0
        evidence = []
        manip_types = []

        # ── Organic pump indicators ─────────────────────────────────
        # High volume with proportional price increase
        if snap.volume_24h > 50000 and snap.price_change_24h > 10:
            vol_price_ratio = snap.volume_24h / max(snap.price_change_24h, 1)
            if vol_price_ratio > 1000:  # substantial volume backing the move
                moon_score += 20
                evidence.append(f"Strong volume/price alignment: ${snap.volume_24h:,.0f} vol")

        # Buy/sell ratio indicates organic demand
        buy_sell = snap.buys_24h / max(snap.sells_24h, 1)
        if 1.2 < buy_sell < 4.0:  # healthy but not extreme
            moon_score += 15
            evidence.append(f"Healthy buy/sell ratio: {buy_sell:.1f}x")
        elif buy_sell > 4.0:
            # Could be FOMO or coordinated
            fake_score += 10
            evidence.append(f"Extreme buy/sell ratio: {buy_sell:.1f}x — could be FOMO")

        # Many unique buyers = organic
        if snap.unique_buyers > 100 and snap.unique_buyers > snap.buys_24h * 0.3:
            moon_score += 15
            evidence.append(f"Many unique buyers: {snap.unique_buyers}")

        # Low bot ratio in social
        if snap.social_bot_ratio < 0.3 and snap.social_mentions_24h > 10:
            moon_score += 10
            evidence.append(f"Low bot ratio: {snap.social_bot_ratio:.0%}")

        # ── Fake pump indicators ────────────────────────────────────
        # Run manipulation detector
        manip_results = self.detector.analyze_token(snap)
        for result in manip_results:
            fake_score += result.confidence * 0.4
            manip_types.append(f"{result.manipulation_type.value} ({result.confidence:.0f}%)")
            evidence.append(f"Manipulation: {result.description}")

        # Extreme price spike with low liquidity
        if snap.price_change_1h > 20 and snap.liquidity_usd < 50000:
            fake_score += 20
            evidence.append(f"Extreme spike +{snap.price_change_1h:.0f}% on thin liquidity")

        # Volume spike without holder growth
        if snap.volume_change_24h > 100 and snap.holders_change_24h < 10:
            fake_score += 15
            evidence.append("Volume spike without new holders — wash trading?")

        # Social mentions far exceed on-chain activity
        if snap.social_mentions_24h > 100 and snap.volume_24h < 10000:
            fake_score += 15
            evidence.append("Social hype >> on-chain activity — manipulation")

        # ── Cap scores ──────────────────────────────────────────────
        moon_score = min(100, moon_score)
        fake_score = min(100, fake_score)

        # ── Verdict ─────────────────────────────────────────────────
        if moon_score > 60 and fake_score < 30:
            verdict = "organic_moon"
        elif moon_score > 40 and fake_score < 50:
            verdict = "likely_organic"
        elif fake_score > 60 and moon_score < 30:
            verdict = "fake_pump"
        elif fake_score > 40:
            verdict = "likely_fake"
        else:
            verdict = "suspicious"

        # Confidence based on data quality
        data_points = len(evidence)
        confidence = min(90, 20 + data_points * 12)

        return PumpResult(
            token_address=snap.token_address,
            token_symbol=snap.token_symbol,
            moon_score=moon_score,
            fake_pump_score=fake_score,
            verdict=verdict,
            manipulation_types=manip_types,
            evidence=evidence,
            confidence=confidence,
            timestamp=time.time(),
        )

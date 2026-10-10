"""THE EYE — Rug Probability Engine

Combines all signals into a single rug probability score (0-100%).

Indicators and their weights:
| Indicator                    | Rug Probability |
|------------------------------|-----------------|
| No liquidity lock            | +30%            |
| Dev holds >30% supply        | +25%            |
| Fresh dev wallet (<14 days)  | +20%            |
| Known serial rugger          | +40%            |
| Social 100% bot              | +15%            |
| No social presence           | +10%            |
| Honey pot detected           | +35%            |
| Proxy contract               | +20%            |
| Mint function                | +25%            |
| Top holder >50%              | +20%            |
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from src.pattern.dev_matcher import DevMatcher, DevProfile
from src.pattern.whale_matcher import WhaleMatcher
from config.settings import settings


@dataclass
class RugResult:
    token_address: str
    token_symbol: str
    chain: str
    rug_probability: float  # 0-100%
    risk_level: str  # "safe", "low", "medium", "high", "critical"
    indicators: list[str] = field(default_factory=list)
    dev_flags: list[str] = field(default_factory=list)
    whale_flags: list[str] = field(default_factory=list)
    social_flags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = 0.0


class RugProbabilityEngine:
    """Calculate combined rug probability from all signal sources."""

    def __init__(self, dev_matcher: Optional[DevMatcher] = None,
                 whale_matcher: Optional[WhaleMatcher] = None):
        self.dev_matcher = dev_matcher or DevMatcher()
        self.whale_matcher = whale_matcher or WhaleMatcher()

    def calculate(self, token_address: str, token_symbol: str = "",
                  chain: str = "eth",
                  dev_address: str = "",
                  dev_supply_pct: float = 0.0,
                  dev_wallet_age_days: float = 999.0,
                  liquidity_locked: bool = True,
                  lock_duration_days: float = 0.0,
                  top_holder_pct: float = 0.0,
                  holders_count: int = 0,
                  social_bot_ratio: float = 0.0,
                  has_social: bool = True,
                  is_honeypot: bool = False,
                  is_proxy: bool = False,
                  has_mint: bool = False) -> RugResult:
        """Calculate rug probability from all available signals."""

        probability = 0.0
        indicators = []
        dev_flags = []
        whale_flags = []
        social_flags = []

        # ── Liquidity lock check ────────────────────────────────────
        if not liquidity_locked:
            probability += 30
            indicators.append("No liquidity lock (+30%)")
        elif lock_duration_days < settings.get("rug_check.min_liquidity_lock_days", 30):
            probability += 15
            indicators.append(f"Short lock ({lock_duration_days:.0f}d) (+15%)")

        # ── Dev supply check ────────────────────────────────────────
        dev_threshold = settings.get("rug_check.dev_max_supply_pct", 30)
        if dev_supply_pct > dev_threshold:
            probability += 25
            dev_flags.append(f"Dev holds {dev_supply_pct:.1f}% supply (+25%)")
        elif dev_supply_pct > dev_threshold / 2:
            probability += 10
            dev_flags.append(f"Dev holds {dev_supply_pct:.1f}% supply (+10%)")

        # ── Fresh dev wallet ────────────────────────────────────────
        fresh_days = settings.get("rug_check.fresh_wallet_days", 14)
        if dev_wallet_age_days < fresh_days:
            probability += 20
            dev_flags.append(f"Fresh dev wallet ({dev_wallet_age_days:.0f}d old) (+20%)")

        # ── Serial rugger check ─────────────────────────────────────
        if dev_address:
            dev_rug_add = self.dev_matcher.get_total_rug_probability_add(dev_address, chain)
            if dev_rug_add > 0:
                probability += dev_rug_add
                dev_flags.append(f"Known dev signature (+{dev_rug_add:.0f}%)")

            # Check specific signatures
            dev_results = self.dev_matcher.analyze_dev(dev_address, chain)
            for r in dev_results:
                dev_flags.append(f"{r.signature.value}: {r.description}")

        # ── Top holder concentration ────────────────────────────────
        if top_holder_pct > 50:
            probability += 20
            indicators.append(f"Top holder {top_holder_pct:.1f}% (+20%)")
        elif top_holder_pct > 30:
            probability += 10
            indicators.append(f"Top holder {top_holder_pct:.1f}% (+10%)")

        # ── Social signals ──────────────────────────────────────────
        if social_bot_ratio > 0.8:
            probability += 15
            social_flags.append("Social ~100% bot (+15%)")
        elif social_bot_ratio > 0.5:
            probability += 8
            social_flags.append(f"Social {social_bot_ratio:.0%} bot (+8%)")

        if not has_social:
            probability += 10
            social_flags.append("No social presence (+10%)")

        # ── Contract red flags ──────────────────────────────────────
        if is_honeypot:
            probability += 35
            indicators.append("Honey pot detected (+35%)")

        if is_proxy:
            probability += 20
            indicators.append("Proxy contract (+20%)")

        if has_mint:
            probability += 25
            indicators.append("Mint function (+25%)")

        # ── Cap probability ─────────────────────────────────────────
        probability = min(probability, 100)

        # ── Risk level ──────────────────────────────────────────────
        low = settings.get("rug_check.threshold_low", 30)
        med = settings.get("rug_check.threshold_medium", 55)
        high = settings.get("rug_check.threshold_high", 75)

        if probability < low:
            risk_level = "safe" if probability < 15 else "low"
        elif probability < med:
            risk_level = "medium"
        elif probability < high:
            risk_level = "high"
        else:
            risk_level = "critical"

        # ── Confidence (how many data points we had) ────────────────
        data_points = len(indicators) + len(dev_flags) + len(whale_flags) + len(social_flags)
        confidence = min(95, 30 + data_points * 10)

        return RugResult(
            token_address=token_address,
            token_symbol=token_symbol,
            chain=chain,
            rug_probability=probability,
            risk_level=risk_level,
            indicators=indicators,
            dev_flags=dev_flags,
            whale_flags=whale_flags,
            social_flags=social_flags,
            confidence=confidence,
            timestamp=time.time(),
        )

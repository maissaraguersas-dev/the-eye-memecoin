"""THE EYE — Whale Pattern Matcher

Detects 7 whale behavior patterns:
1. Sniper — buys at launch, sells quickly
2. Accumulate→Pump→Dump — systematic accumulation before orchestrated dump
3. Copy-Trader — mirrors successful whale wallets
4. Diamond Hands — holds through volatility (inverse signal = strong project)
5. Failed Whale — attempted manipulation that failed (inverse signal)
6. Liquidity Migration — moving liquidity between pools
7. Bridge Movement — cross-chain movement (often precedes big action)
"""
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from config.settings import settings


class WhalePattern(Enum):
    SNIPER = "sniper"
    ACCUMULATE_PUMP_DUMP = "accumulate_pump_dump"
    COPY_TRADER = "copy_trader"
    DIAMOND_HANDS = "diamond_hands"
    FAILED_WHALE = "failed_whale"
    LIQUIDITY_MIGRATION = "liquidity_migration"
    BRIDGE_MOVEMENT = "bridge_movement"


@dataclass
class WhaleProfile:
    wallet: str
    chain: str
    patterns: list[WhalePattern] = field(default_factory=list)
    total_buy_usd: float = 0.0
    total_sell_usd: float = 0.0
    buy_count: int = 0
    sell_count: int = 0
    avg_hold_time_hours: float = 0.0
    success_rate: float = 0.0  # profitable trade %
    tokens_traded: list[str] = field(default_factory=list)
    last_active: float = 0.0
    confidence: float = 0.0  # 0-100 how sure we are of this pattern
    notes: str = ""


@dataclass
class WhaleMatchResult:
    wallet: str
    pattern: WhalePattern
    confidence: float  # 0-100
    description: str
    impact: str  # "bullish", "bearish", "neutral", "dangerous"
    related_token: str = ""
    timestamp: float = 0.0


class WhaleMatcher:
    """Match whale wallet behavior to known manipulation patterns."""

    DATA_DIR = Path(__file__).parent.parent / "data"
    PROFILES_FILE = DATA_DIR / "whale_profiles.json"

    def __init__(self):
        self.profiles: dict[str, WhaleProfile] = {}
        self._load_profiles()

    def _load_profiles(self):
        if self.PROFILES_FILE.exists():
            with open(self.PROFILES_FILE) as f:
                data = json.load(f)
            for wallet, prof in data.items():
                patterns = [WhalePattern(p) for p in prof.get("patterns", []) if p in [e.value for e in WhalePattern]]
                self.profiles[wallet] = WhaleProfile(
                    wallet=wallet,
                    chain=prof.get("chain", "eth"),
                    patterns=patterns,
                    total_buy_usd=prof.get("total_buy_usd", 0),
                    total_sell_usd=prof.get("total_sell_usd", 0),
                    buy_count=prof.get("buy_count", 0),
                    sell_count=prof.get("sell_count", 0),
                    avg_hold_time_hours=prof.get("avg_hold_time_hours", 0),
                    success_rate=prof.get("success_rate", 0),
                    last_active=prof.get("last_active", 0),
                    confidence=prof.get("confidence", 0),
                    notes=prof.get("notes", ""),
                )

    def _save_profiles(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {}
        for wallet, prof in self.profiles.items():
            data[wallet] = {
                "chain": prof.chain,
                "patterns": [p.value for p in prof.patterns],
                "total_buy_usd": prof.total_buy_usd,
                "total_sell_usd": prof.total_sell_usd,
                "buy_count": prof.buy_count,
                "sell_count": prof.sell_count,
                "avg_hold_time_hours": prof.avg_hold_time_hours,
                "success_rate": prof.success_rate,
                "last_active": prof.last_active,
                "confidence": prof.confidence,
                "notes": prof.notes,
            }
        with open(self.PROFILES_FILE, "w") as f:
            json.dump(data, f, indent=2)

    # ── Pattern Detection ───────────────────────────────────────────

    def detect_sniper(self, profile: WhaleProfile) -> Optional[WhaleMatchResult]:
        """Sniper: buys at token launch, sells within minutes-hours for quick profit."""
        if profile.avg_hold_time_hours < 2 and profile.buy_count >= 3:
            confidence = min(95, 50 + (profile.success_rate * 40) + (profile.buy_count * 2))
            return WhaleMatchResult(
                wallet=profile.wallet,
                pattern=WhalePattern.SNIPER,
                confidence=confidence,
                description=f"Sniper wallet: avg hold {profile.avg_hold_time_hours:.1f}h, "
                           f"success rate {profile.success_rate:.0%}",
                impact="dangerous",
                timestamp=time.time(),
            )
        return None

    def detect_accumulate_pump_dump(self, profile: WhaleProfile) -> Optional[WhaleMatchResult]:
        """Accumulate→Pump→Dump: systematic buying followed by large sells."""
        if (profile.total_buy_usd > 50000 and
            profile.total_sell_usd > profile.total_buy_usd * 0.8 and
            profile.sell_count >= 2):
            confidence = min(90, 40 + (profile.total_sell_usd / profile.total_buy_usd * 30))
            return WhaleMatchResult(
                wallet=profile.wallet,
                pattern=WhalePattern.ACCUMULATE_PUMP_DUMP,
                confidence=confidence,
                description=f"Accumulate→Pump→Dump: bought ${profile.total_buy_usd:,.0f}, "
                           f"sold ${profile.total_sell_usd:,.0f}",
                impact="bearish",
                timestamp=time.time(),
            )
        return None

    def detect_copy_trader(self, profile: WhaleProfile) -> Optional[WhaleMatchResult]:
        """Copy-Trader: mirrors successful whale wallets with similar timing."""
        if profile.success_rate > 0.7 and profile.buy_count >= 5:
            # Would need cross-wallet analysis for full detection
            confidence = 50  # base confidence without cross-referencing
            return WhaleMatchResult(
                wallet=profile.wallet,
                pattern=WhalePattern.COPY_TRADER,
                confidence=confidence,
                description=f"Potential copy-trader: {profile.success_rate:.0%} success, "
                           f"{profile.buy_count} trades",
                impact="neutral",
                timestamp=time.time(),
            )
        return None

    def detect_diamond_hands(self, profile: WhaleProfile) -> Optional[WhaleMatchResult]:
        """Diamond Hands: holds through volatility — bullish inverse signal."""
        if (profile.avg_hold_time_hours > 168 and  # > 7 days
            profile.buy_count > 0 and
            profile.sell_count == 0):
            confidence = min(85, 50 + (profile.avg_hold_time_hours / 24))
            return WhaleMatchResult(
                wallet=profile.wallet,
                pattern=WhalePattern.DIAMOND_HANDS,
                confidence=confidence,
                description=f"Diamond hands: holding {profile.avg_hold_time_hours:.0f}h, "
                           f"never sold",
                impact="bullish",
                timestamp=time.time(),
            )
        return None

    def detect_failed_whale(self, profile: WhaleProfile) -> Optional[WhaleMatchResult]:
        """Failed Whale: attempted manipulation that backfired — inverse signal."""
        if (profile.sell_count > profile.buy_count * 2 and
            profile.success_rate < 0.3 and
            profile.total_sell_usd > 10000):
            confidence = min(70, 30 + (1 - profile.success_rate) * 40)
            return WhaleMatchResult(
                wallet=profile.wallet,
                pattern=WhalePattern.FAILED_WHALE,
                confidence=confidence,
                description=f"Failed whale: success rate {profile.success_rate:.0%}, "
                           f"selling at losses",
                impact="bullish",  # Failed dump = bullish inverse
                timestamp=time.time(),
            )
        return None

    def detect_liquidity_migration(self, profile: WhaleProfile) -> Optional[WhaleMatchResult]:
        """Liquidity Migration: moving liquidity between pools — often rug precursor."""
        # Would need LP transaction analysis
        if profile.sell_count > 3 and profile.avg_hold_time_hours < 1:
            confidence = 40
            return WhaleMatchResult(
                wallet=profile.wallet,
                pattern=WhalePattern.LIQUIDITY_MIGRATION,
                confidence=confidence,
                description=f"Possible liquidity migration: rapid pool movements",
                impact="dangerous",
                timestamp=time.time(),
            )
        return None

    def detect_bridge_movement(self, profile: WhaleProfile) -> Optional[WhaleMatchResult]:
        """Bridge Movement: cross-chain movement — often precedes big action."""
        # Would need cross-chain tracking
        if len(profile.tokens_traded) > 10 and profile.buy_count > 5:
            confidence = 35
            return WhaleMatchResult(
                wallet=profile.wallet,
                pattern=WhalePattern.BRIDGE_MOVEMENT,
                confidence=confidence,
                description=f"Cross-chain movement: {len(profile.tokens_traded)} tokens",
                impact="neutral",
                timestamp=time.time(),
            )
        return None

    # ── Full Analysis ───────────────────────────────────────────────

    def analyze_wallet(self, wallet: str, chain: str = "eth") -> list[WhaleMatchResult]:
        """Run all 7 pattern detections on a wallet."""
        profile = self.profiles.get(wallet, WhaleProfile(wallet=wallet, chain=chain))
        results = []

        detectors = [
            self.detect_sniper,
            self.detect_accumulate_pump_dump,
            self.detect_copy_trader,
            self.detect_diamond_hands,
            self.detect_failed_whale,
            self.detect_liquidity_migration,
            self.detect_bridge_movement,
        ]

        for detector in detectors:
            match = detector(profile)
            if match:
                results.append(match)

        # Update profile
        self.profiles[wallet] = profile
        self._save_profiles()

        return results

    def analyze_whales_for_token(self, token_address: str,
                                  whale_profiles: list[WhaleProfile]) -> list[WhaleMatchResult]:
        """Analyze all known whales interacting with a token."""
        all_results = []
        for prof in whale_profiles:
            if token_address in prof.tokens_traded:
                results = self.analyze_wallet(prof.wallet, prof.chain)
                for r in results:
                    r.related_token = token_address
                all_results.extend(results)
        # Sort by confidence
        all_results.sort(key=lambda r: r.confidence, reverse=True)
        return all_results

    def update_profile(self, wallet: str, chain: str = "eth", **kwargs):
        """Update a whale profile with new data — learning mechanism."""
        if wallet not in self.profiles:
            self.profiles[wallet] = WhaleProfile(wallet=wallet, chain=chain)
        prof = self.profiles[wallet]
        for k, v in kwargs.items():
            if hasattr(prof, k):
                setattr(prof, k, v)
        prof.last_active = time.time()
        self._save_profiles()

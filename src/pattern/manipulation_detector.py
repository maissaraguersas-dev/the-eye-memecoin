"""THE EYE — Manipulation Detector

Detects 7 market manipulation patterns:
1. Bot Army — coordinated bot buying/selling
2. Wash Trading — self-trading to inflate volume
3. Volume-Price Divergence — volume up but price stagnant (accumulation)
4. Social Manipulation — bot-driven social hype
5. Holder Inflation — fake wallet count inflation
6. Coordinated Pump — synchronized buying across wallets
7. Spoofing — large fake orders to move price
"""
import time
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ManipulationType(Enum):
    BOT_ARMY = "bot_army"
    WASH_TRADING = "wash_trading"
    VOLUME_PRICE_DIVERGENCE = "volume_price_divergence"
    SOCIAL_MANIPULATION = "social_manipulation"
    HOLDER_INFLATION = "holder_inflation"
    COORDINATED_PUMP = "coordinated_pump"
    SPOOFING = "spoofing"


@dataclass
class ManipulationResult:
    token_address: str
    token_symbol: str
    manipulation_type: ManipulationType
    confidence: float  # 0-100
    severity: str  # "low", "medium", "high", "critical"
    description: str
    evidence: list[str] = field(default_factory=list)
    impact_on_price: str = "neutral"  # "artificial_pump", "artificial_dump", "neutral"
    timestamp: float = 0.0


@dataclass
class MarketSnapshot:
    """Snapshot of market data needed for manipulation detection."""
    token_address: str
    token_symbol: str
    price_usd: float
    price_change_1h: float
    price_change_24h: float
    volume_24h: float
    volume_change_24h: float
    buys_24h: int
    sells_24h: int
    holders_count: int
    holders_change_24h: int
    liquidity_usd: float
    top_holder_pct: float
    unique_buyers: int = 0
    unique_sellers: int = 0
    avg_tx_size_usd: float = 0.0
    social_bot_ratio: float = 0.0
    social_mentions_24h: int = 0


class ManipulationDetector:
    """Detect market manipulation patterns from free market data."""

    def detect_bot_army(self, snap: MarketSnapshot) -> Optional[ManipulationResult]:
        """Bot Army: many small coordinated transactions from similar wallets."""
        if snap.buys_24h > 100 and snap.avg_tx_size_usd < 50:
            # Small, frequent buys = likely bot army
            bot_score = min(90, (snap.buys_24h / max(snap.unique_buyers, 1)) * 20)
            if bot_score > 40:
                return ManipulationResult(
                    token_address=snap.token_address,
                    token_symbol=snap.token_symbol,
                    manipulation_type=ManipulationType.BOT_ARMY,
                    confidence=bot_score,
                    severity="high" if bot_score > 70 else "medium",
                    description=f"Bot army detected: {snap.buys_24h} buys from "
                               f"~{snap.unique_buyers} unique wallets, avg ${snap.avg_tx_size_usd:.0f}",
                    evidence=[f"Buys/wallet ratio: {snap.buys_24h/max(snap.unique_buyers,1):.1f}",
                             f"Avg tx size: ${snap.avg_tx_size_usd:.0f}"],
                    impact_on_price="artificial_pump",
                    timestamp=time.time(),
                )
        return None

    def detect_wash_trading(self, snap: MarketSnapshot) -> Optional[ManipulationResult]:
        """Wash Trading: same wallets buying and selling to inflate volume."""
        # If buy/sell ratio is very close to 1.0 with high volume, suspicious
        buy_sell_ratio = snap.buys_24h / max(snap.sells_24h, 1)
        if (abs(buy_sell_ratio - 1.0) < 0.15 and
            snap.volume_24h > 10000 and
            snap.unique_buyers < snap.buys_24h * 0.3):
            wash_score = min(85, 30 + (snap.volume_24h / 10000))
            return ManipulationResult(
                token_address=snap.token_address,
                token_symbol=snap.token_symbol,
                manipulation_type=ManipulationType.WASH_TRADING,
                confidence=wash_score,
                severity="high" if wash_score > 65 else "medium",
                description=f"Wash trading: buy/sell ratio {buy_sell_ratio:.2f}, "
                           f"volume ${snap.volume_24h:,.0f} with few unique traders",
                evidence=[f"Buy/sell ratio: {buy_sell_ratio:.2f}",
                         f"Unique traders: {snap.unique_buyers}"],
                impact_on_price="neutral",
                timestamp=time.time(),
            )
        return None

    def detect_volume_price_divergence(self, snap: MarketSnapshot) -> Optional[ManipulationResult]:
        """Volume-Price Divergence: volume rising but price flat — accumulation phase."""
        if (snap.volume_change_24h > 50 and
            abs(snap.price_change_24h) < 3):
            div_score = min(80, snap.volume_change_24h / 2)
            return ManipulationResult(
                token_address=snap.token_address,
                token_symbol=snap.token_symbol,
                manipulation_type=ManipulationType.VOLUME_PRICE_DIVERGENCE,
                confidence=div_score,
                severity="medium",
                description=f"Vol/price divergence: volume +{snap.volume_change_24h:.0f}%, "
                           f"price {snap.price_change_24h:+.1f}% — possible accumulation",
                evidence=[f"Volume change: +{snap.volume_change_24h:.0f}%",
                         f"Price change: {snap.price_change_24h:+.1f}%"],
                impact_on_price="neutral",
                timestamp=time.time(),
            )
        return None

    def detect_social_manipulation(self, snap: MarketSnapshot) -> Optional[ManipulationResult]:
        """Social Manipulation: bot-driven social hype disproportionate to on-chain activity."""
        if (snap.social_bot_ratio > 0.5 and
            snap.social_mentions_24h > 50 and
            snap.volume_24h < snap.social_mentions_24h * 100):
            soc_score = min(85, snap.social_bot_ratio * 100)
            return ManipulationResult(
                token_address=snap.token_address,
                token_symbol=snap.token_symbol,
                manipulation_type=ManipulationType.SOCIAL_MANIPULATION,
                confidence=soc_score,
                severity="high" if soc_score > 70 else "medium",
                description=f"Social manipulation: {snap.social_bot_ratio:.0%} bots, "
                           f"{snap.social_mentions_24h} mentions but ${snap.volume_24h:,.0f} volume",
                evidence=[f"Bot ratio: {snap.social_bot_ratio:.0%}",
                         f"Mentions/volume ratio: {snap.social_mentions_24h/max(snap.volume_24h,1)*1000:.1f}"],
                impact_on_price="artificial_pump",
                timestamp=time.time(),
            )
        return None

    def detect_holder_inflation(self, snap: MarketSnapshot) -> Optional[ManipulationResult]:
        """Holder Inflation: rapid holder count increase with no real volume — fake wallets."""
        if (snap.holders_change_24h > 100 and
            snap.volume_24h < snap.holders_change_24h * 10):
            inf_score = min(80, snap.holders_change_24h / 5)
            return ManipulationResult(
                token_address=snap.token_address,
                token_symbol=snap.token_symbol,
                manipulation_type=ManipulationType.HOLDER_INFLATION,
                confidence=inf_score,
                severity="medium",
                description=f"Holder inflation: +{snap.holders_change_24h} holders but "
                           f"only ${snap.volume_24h:,.0f} volume",
                evidence=[f"New holders: +{snap.holders_change_24h}",
                         f"Volume: ${snap.volume_24h:,.0f}"],
                impact_on_price="neutral",
                timestamp=time.time(),
            )
        return None

    def detect_coordinated_pump(self, snap: MarketSnapshot) -> Optional[ManipulationResult]:
        """Coordinated Pump: synchronized buying across many wallets at same time."""
        if (snap.price_change_1h > 10 and
            snap.buys_24h > snap.sells_24h * 3 and
            snap.avg_tx_size_usd < 200):
            pump_score = min(85, snap.price_change_1h * 3)
            return ManipulationResult(
                token_address=snap.token_address,
                token_symbol=snap.token_symbol,
                manipulation_type=ManipulationType.COORDINATED_PUMP,
                confidence=pump_score,
                severity="high" if pump_score > 60 else "medium",
                description=f"Coordinated pump: +{snap.price_change_1h:.1f}% in 1h, "
                           f"buy/sell {snap.buys_24h/max(snap.sells_24h,1):.1f}x",
                evidence=[f"1h price change: +{snap.price_change_1h:.1f}%",
                         f"Buy/sell ratio: {snap.buys_24h/max(snap.sells_24h,1):.1f}"],
                impact_on_price="artificial_pump",
                timestamp=time.time(),
            )
        return None

    def detect_spoofing(self, snap: MarketSnapshot) -> Optional[ManipulationResult]:
        """Spoofing: large orders placed then cancelled to move price."""
        # Would need order book data for full detection
        if (snap.top_holder_pct > 20 and
            snap.price_change_1h > 5 and
            snap.volume_24h < snap.market_cap_usd * 0.01 if hasattr(snap, 'market_cap_usd') else False):
            return ManipulationResult(
                token_address=snap.token_address,
                token_symbol=snap.token_symbol,
                manipulation_type=ManipulationType.SPOOFING,
                confidence=40,
                severity="low",
                description="Possible spoofing: large holder + price movement + thin volume",
                evidence=["Top holder > 20%", "Thin volume relative to market cap"],
                impact_on_price="artificial_pump",
                timestamp=time.time(),
            )
        return None

    # ── Full Analysis ───────────────────────────────────────────────

    def analyze_token(self, snap: MarketSnapshot) -> list[ManipulationResult]:
        """Run all 7 manipulation detections on a token."""
        results = []
        detectors = [
            self.detect_bot_army,
            self.detect_wash_trading,
            self.detect_volume_price_divergence,
            self.detect_social_manipulation,
            self.detect_holder_inflation,
            self.detect_coordinated_pump,
            self.detect_spoofing,
        ]
        for detector in detectors:
            result = detector(snap)
            if result:
                results.append(result)
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def analyze_market_batch(self, snapshots: list[MarketSnapshot]) -> dict[str, list[ManipulationResult]]:
        """Batch analyze multiple tokens — for market-wide monitoring."""
        results = {}
        for snap in snapshots:
            token_results = self.analyze_token(snap)
            if token_results:
                results[snap.token_symbol] = token_results
        return results

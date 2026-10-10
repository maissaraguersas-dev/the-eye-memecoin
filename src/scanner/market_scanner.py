"""THE EYE — Market-Wide Scanner & Discovery Engine

This is NOT a portfolio tracker. It scans the ENTIRE memecoin market across
all chains, discovers new tokens, and identifies opportunities/risks in real-time.
"""
import asyncio
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from src.monitors.blockchain import BlockchainMonitor, TokenOnChain
from src.monitors.social import SocialMonitor, SocialSignals
from src.monitors.market import MarketMonitor, MarketData, MarketOverview
from src.pattern.whale_matcher import WhaleMatcher, WhaleMatchResult
from src.pattern.dev_matcher import DevMatcher
from src.pattern.manipulation_detector import ManipulationDetector, MarketSnapshot
from src.analysis.rug_probability import RugProbabilityEngine, RugResult
from src.analysis.pump_scorer import PumpScorer, PumpResult
from src.analysis.temporal_analyzer import TemporalAnalyzer, TemporalResult
from src.analysis.confidence import ConfidenceEngine
from src.analysis.prediction import PredictionEngine, Prediction
from config.settings import settings


@dataclass
class TokenScanResult:
    """Complete analysis of a single token — the core output of THE EYE."""
    token: TokenOnChain
    market_data: Optional[MarketData] = None
    social_signals: Optional[SocialSignals] = None
    rug_result: Optional[RugResult] = None
    pump_result: Optional[PumpResult] = None
    prediction: Optional[Prediction] = None
    whale_matches: list[WhaleMatchResult] = field(default_factory=list)
    manipulation_results: list = field(default_factory=list)
    scan_timestamp: float = 0.0


@dataclass
class MarketScanResult:
    """Complete market-wide scan result — the output of a full scan cycle."""
    tokens_discovered: int = 0
    tokens_scanned: int = 0
    opportunities: list[TokenScanResult] = field(default_factory=list)
    risks: list[TokenScanResult] = field(default_factory=list)
    trending: list[TokenScanResult] = field(default_factory=list)
    new_launches: list[TokenScanResult] = field(default_factory=list)
    rug_alerts: list[TokenScanResult] = field(default_factory=list)
    pump_alerts: list[TokenScanResult] = field(default_factory=list)
    whale_alerts: list[TokenScanResult] = field(default_factory=list)
    market_overview: Optional[MarketOverview] = None
    temporal: Optional[TemporalResult] = None
    scan_duration_sec: float = 0.0
    timestamp: float = 0.0


class MarketScanner:
    """THE EYE's market-wide scanner — monitors the ENTIRE memecoin market."""

    def __init__(self):
        self.blockchain = BlockchainMonitor()
        self.social = SocialMonitor()
        self.market = MarketMonitor()
        self.whale_matcher = WhaleMatcher()
        self.dev_matcher = DevMatcher()
        self.manipulation_detector = ManipulationDetector()
        self.rug_engine = RugProbabilityEngine(self.dev_matcher, self.whale_matcher)
        self.pump_scorer = PumpScorer(self.manipulation_detector)
        self.temporal = TemporalAnalyzer()
        self.confidence = ConfidenceEngine()
        self.prediction = PredictionEngine()

        self._watchlist: dict[str, dict] = {}
        self._last_scan: Optional[MarketScanResult] = None
        self._known_tokens: dict[str, float] = {}  # address → first_seen timestamp
        self._running = False

    # ── Single Token Deep Scan ──────────────────────────────────────

    async def scan_token(self, address: str, chain: str = "eth",
                         symbol: str = "") -> TokenScanResult:
        """Deep scan a single token — all analysis pipelines."""
        # 1. Blockchain data
        token = await self.blockchain.get_token_by_address(address, chain)
        if not token:
            token = TokenOnChain(address=address, symbol=symbol or address[:8], chain=chain)

        result = TokenScanResult(token=token, scan_timestamp=time.time())

        # 2. Market data
        market_data = await self.market.get_token_market_data(address, chain)
        result.market_data = market_data

        # 3. Social signals
        if token.symbol:
            result.social_signals = await self.social.scan_token_social(token.symbol, address)

        # 4. Rug check
        result.rug_result = self.rug_engine.calculate(
            token_address=address,
            token_symbol=token.symbol,
            chain=chain,
            dev_address=token.deployer_address,
            liquidity_locked=token.liquidity_locked,
            lock_duration_days=token.lock_duration_days,
            social_bot_ratio=result.social_signals.bot_ratio if result.social_signals else 0,
            has_social=result.social_signals is not None and result.social_signals.twitter_mentions_24h > 0,
        )

        # 5. Pump scan
        if market_data:
            snap = MarketSnapshot(
                token_address=address,
                token_symbol=token.symbol,
                price_usd=market_data.price_usd,
                price_change_1h=market_data.price_change_1h,
                price_change_24h=market_data.price_change_24h,
                volume_24h=market_data.volume_24h,
                volume_change_24h=market_data.volume_change_24h,
                buys_24h=market_data.buys_24h,
                sells_24h=market_data.sells_24h,
                holders_count=0,
                holders_change_24h=0,
                liquidity_usd=market_data.liquidity_usd,
                top_holder_pct=0,
                social_bot_ratio=result.social_signals.bot_ratio if result.social_signals else 0,
                social_mentions_24h=result.social_signals.twitter_mentions_24h if result.social_signals else 0,
            )
            result.pump_result = self.pump_scorer.score(snap)
            result.manipulation_results = self.manipulation_detector.analyze_token(snap)

        # 6. Prediction
        result.prediction = self.prediction.predict(
            token_address=address,
            token_symbol=token.symbol,
            chain=chain,
            rug_probability=result.rug_result.rug_probability,
            moon_score=result.pump_result.moon_score if result.pump_result else 0,
            fake_pump_score=result.pump_result.fake_pump_score if result.pump_result else 0,
            price_change_24h=market_data.price_change_24h if market_data else 0,
            volume_change_24h=market_data.volume_change_24h if market_data else 0,
            buy_sell_ratio=market_data.buy_sell_ratio if market_data else 1,
            temporal_risk=self.temporal.analyze().risk_score,
            whale_bullish=any(m.impact == "bullish" for m in result.whale_matches),
            whale_bearish=any(m.impact == "bearish" for m in result.whale_matches),
            social_sentiment=result.social_signals.twitter_sentiment if result.social_signals else 0,
        )

        return result

    # ── Market-Wide Full Scan ───────────────────────────────────────

    async def scan_market(self) -> MarketScanResult:
        """Full market-wide scan — discovers ALL new tokens and analyzes them.
        This is the core loop that runs 24/7.
        """
        start = time.time()
        result = MarketScanResult(timestamp=time.time())

        # 1. Discover tokens across all chains
        print("🔍 [DISCOVERY] Scanning all chains for new/trending tokens...")
        discovered = await self.blockchain.discover_all_tokens()
        result.tokens_discovered = len(discovered)
        print(f"   Found {len(discovered)} tokens across {len(settings.chains)} chains")

        # 2. Also check DexScreener trending
        for chain in settings.chains:
            try:
                trending = await self.blockchain.get_trending_tokens(chain)
                discovered.extend(trending)
            except Exception:
                pass

        # Also check CoinGecko trending
        try:
            cg_trending = await self.market.get_trending_coingecko()
            for coin in cg_trending:
                item = coin.get("item", {})
                addr = item.get("id", "")
                if addr and addr not in self._known_tokens:
                    discovered.append(TokenOnChain(
                        address=addr,
                        name=item.get("name", ""),
                        symbol=item.get("symbol", "").upper(),
                        chain="eth",  # default
                    ))
        except Exception:
            pass

        # Deduplicate
        seen = set()
        unique_tokens = []
        for t in discovered:
            key = f"{t.chain}:{t.address}"
            if key not in seen and t.address:
                seen.add(key)
                unique_tokens.append(t)

        # 3. Identify new launches (tokens we haven't seen before)
        now = time.time()
        for t in unique_tokens:
            key = f"{t.chain}:{t.address}"
            if key not in self._known_tokens:
                self._known_tokens[key] = now
                # New token!
                age_h = (now * 1000 - t.created_at) / (1000 * 3600) if t.created_at else 0
                if age_h < 24:
                    result.new_launches.append(TokenScanResult(
                        token=t, scan_timestamp=now
                    ))

        # 4. Filter tokens worth scanning (min liquidity/volume)
        min_liq = settings.get("scan.min_liquidity_usd", 1000)
        min_vol = settings.get("scan.min_volume_24h_usd", 500)
        max_per_cycle = settings.get("scan.max_tokens_per_cycle", 200)

        scanable = []
        for t in unique_tokens:
            if t.liquidity_usd >= min_liq or t.volume_24h >= min_vol:
                scanable.append(t)
        scanable = scanable[:max_per_cycle]

        print(f"📊 [SCANNING] Analyzing {len(scanable)} tokens (filtered from {len(unique_tokens)})...")

        # 5. Deep scan each token (with concurrency limit)
        sem = asyncio.Semaphore(settings.get("monitor.max_concurrent_scans", 5))
        async def limited_scan(t):
            async with sem:
                return await self.scan_token(t.address, t.chain, t.symbol)

        tasks = [limited_scan(t) for t in scanable]
        scan_results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for sr in scan_results:
            if isinstance(sr, TokenScanResult):
                valid_results.append(sr)
                result.tokens_scanned += 1

        # 6. Classify results
        temporal = self.temporal.analyze()
        result.temporal = temporal

        for sr in valid_results:
            # Rug alerts
            if sr.rug_result and sr.rug_result.rug_probability > 55:
                result.rug_alerts.append(sr)
                result.risks.append(sr)

            # Pump alerts
            if sr.pump_result and sr.pump_result.moon_score > 50:
                result.pump_alerts.append(sr)
                result.opportunities.append(sr)

            # Whale alerts
            if sr.whale_matches:
                result.whale_alerts.append(sr)

            # Trending (high volume)
            if sr.market_data and sr.market_data.volume_24h > 100000:
                result.trending.append(sr)

        # Sort by confidence
        result.opportunities.sort(key=lambda x: x.prediction.confidence if x.prediction else 0, reverse=True)
        result.risks.sort(key=lambda x: x.rug_result.rug_probability if x.rug_result else 0, reverse=True)

        # 7. Market overview
        token_dicts = [{"address": t.address, "chain": t.chain} for t in scanable]
        result.market_overview = await self.market.scan_market_overview(token_dicts)

        result.scan_duration_sec = time.time() - start
        self._last_scan = result

        print(f"✅ [COMPLETE] Scan done in {result.scan_duration_sec:.1f}s — "
              f"{len(result.opportunities)} opportunities, {len(result.risks)} risks, "
              f"{len(result.rug_alerts)} rug alerts")

        return result

    # ── Watchlist Management ────────────────────────────────────────

    def add_watchlist(self, token: str, address: str, chain: str = "eth",
                       interval: int = 15):
        """Add a token to the watchlist for continuous monitoring."""
        self._watchlist[token] = {
            "address": address,
            "chain": chain,
            "interval": interval,
            "added_at": time.time(),
        }

    def remove_watchlist(self, token: str):
        """Remove a token from the watchlist."""
        self._watchlist.pop(token, None)

    def list_watchlist(self) -> dict:
        """List all watched tokens."""
        return self._watchlist.copy()

    # ── Continuous Monitoring ───────────────────────────────────────

    async def monitor(self, interval: int = 60):
        """Start continuous market monitoring — runs until stopped."""
        self._running = True
        print(f"🐋👁️  THE EYE — Market Monitor Active")
        print(f"   Scanning every {interval}s across {len(settings.chains)} chains")
        print(f"   Press Ctrl+C to stop\n")

        cycle = 0
        while self._running:
            cycle += 1
            print(f"\n{'='*60}")
            print(f"CYCLE {cycle} — {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
            print(f"{'='*60}")

            try:
                result = await self.scan_market()
                # Display summary
                self._display_summary(result)
            except Exception as e:
                print(f"❌ [ERROR] Scan failed: {e}")

            await asyncio.sleep(interval)

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False

    def _display_summary(self, result: MarketScanResult):
        """Display a scan summary in the terminal."""
        print(f"\n{'─'*60}")
        print(f"📊 MARKET SUMMARY")
        print(f"{'─'*60}")
        print(f"  Tokens discovered: {result.tokens_discovered}")
        print(f"  Tokens scanned:    {result.tokens_scanned}")
        print(f"  New launches:      {len(result.new_launches)}")
        print(f"  Opportunities:     {len(result.opportunities)}")
        print(f"  Risks:             {len(result.risks)}")
        print(f"  Rug alerts:        {len(result.rug_alerts)}")
        print(f"  Pump alerts:       {len(result.pump_alerts)}")
        print(f"  Whale alerts:      {len(result.whale_alerts)}")

        if result.temporal:
            w = result.temporal.current_window
            print(f"\n⏰ TIME: {w.emoji} {w.name} (risk: {w.risk_score:.0f}%)")

        if result.opportunities:
            print(f"\n🚀 TOP OPPORTUNITIES:")
            for opp in result.opportunities[:5]:
                sym = opp.token.symbol or opp.token.address[:8]
                pred = opp.prediction
                if pred:
                    print(f"  • {sym}: {pred.prediction_type.value} "
                          f"(confidence: {pred.confidence:.0f}%, "
                          f"urgency: {pred.urgency})")

        if result.rug_alerts:
            print(f"\n🚨 RUG ALERTS:")
            for risk in result.rug_alerts[:5]:
                sym = risk.token.symbol or risk.token.address[:8]
                rug = risk.rug_result
                if rug:
                    print(f"  • {sym}: rug probability {rug.rug_probability:.0f}% "
                          f"({rug.risk_level})")

        print(f"\n  Scan duration: {result.scan_duration_sec:.1f}s")
        print(f"{'─'*60}")

    # ── Cleanup ─────────────────────────────────────────────────────

    async def close(self):
        """Close all HTTP sessions."""
        await self.blockchain.close()
        await self.social.close()
        await self.market.close()

"""THE EYE — Social Signal Monitor

Free sources: Nitter (Twitter), Reddit JSON API, Telegram Bot API, Discord, TikTok.
"""
import asyncio
import aiohttp
import re
import time
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import quote_plus


@dataclass
class SocialSignals:
    token_symbol: str
    twitter_mentions_24h: int = 0
    twitter_sentiment: float = 0.0  # -1 to 1
    reddit_mentions_24h: int = 0
    reddit_sentiment: float = 0.0
    telegram_members: int = 0
    telegram_active_users: int = 0
    discord_members: int = 0
    bot_ratio: float = 0.0  # 0 = all human, 1 = all bot
    organic_hype_score: float = 0.0  # 0-100
    fake_hype_score: float = 0.0  # 0-100
    influencer_count: int = 0
    viral_coefficient: float = 0.0  # mentions growth rate
    social_volume_rank: int = 0  # rank among all tokens
    timestamp: float = 0.0


class SocialMonitor:
    """Monitor social signals from free sources — no API keys required."""

    NITTER_INSTANCES = [
        "https://nitter.net",
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
    ]
    REDDIT_BASE = "https://www.reddit.com"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # ── Twitter/X via Nitter (free) ─────────────────────────────────

    async def get_twitter_mentions(self, query: str) -> dict:
        """Scrape Twitter mentions via Nitter instances (free, no API key)."""
        session = await self._get_session()
        mentions = 0
        positive = 0
        negative = 0
        for instance in self.NITTER_INSTANCES:
            try:
                url = f"{instance}/search?f=tweets&q={quote_plus(query)}"
                headers = {"User-Agent": "Mozilla/5.0"}
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # Count tweet containers
                        mentions += text.count("timeline-item")
                        # Simple sentiment from emojis/keywords
                        positive += len(re.findall(r'🚀|🌙|💎|bullish|moon|pump|buy|hold|based', text, re.I))
                        negative += len(re.findall(r'rip|dead|dump|scam|rug|sell|bear|trash', text, re.I))
            except Exception:
                continue
        total = positive + negative if (positive + negative) > 0 else 1
        sentiment = (positive - negative) / total
        return {"mentions": mentions, "sentiment": sentiment}

    # ── Reddit (free JSON API) ──────────────────────────────────────

    async def get_reddit_mentions(self, query: str) -> dict:
        """Search Reddit for token mentions — free JSON API."""
        session = await self._get_session()
        mentions = 0
        positive = 0
        negative = 0
        subreddits = ["cryptocurrency", "satoshistreetbets", "cryptomoonshots"]
        for sub in subreddits:
            try:
                url = f"{self.REDDIT_BASE}/r/{sub}/search.json?q={quote_plus(query)}&sort=new&limit=25"
                headers = {"User-Agent": "THE-EYE/1.0"}
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        posts = data.get("data", {}).get("children", [])
                        mentions += len(posts)
                        for post in posts:
                            title = post.get("data", {}).get("title", "").lower()
                            score = post.get("data", {}).get("score", 0)
                            if any(w in title for w in ["moon", "bullish", "buy", "gem"]):
                                positive += max(score, 1)
                            elif any(w in title for w in ["scam", "rug", "dump", "sell"]):
                                negative += max(score, 1)
            except Exception:
                continue
        total = positive + negative if (positive + negative) > 0 else 1
        sentiment = (positive - negative) / total
        return {"mentions": mentions, "sentiment": sentiment}

    # ── Bot detection ───────────────────────────────────────────────

    def calculate_bot_ratio(self, social_data: dict) -> float:
        """Estimate bot ratio from social patterns (0 = human, 1 = bot)."""
        bot_score = 0.0
        mentions = social_data.get("twitter_mentions", 0)
        # High mentions with low unique posters = suspicious
        if mentions > 100:
            poster_ratio = social_data.get("unique_posters", 1) / max(mentions, 1)
            if poster_ratio < 0.1:
                bot_score += 0.4
        # Repetitive content patterns
        if social_data.get("repetition_rate", 0) > 0.6:
            bot_score += 0.3
        # Identical timestamps (coordinated)
        if social_data.get("coordination_score", 0) > 0.5:
            bot_score += 0.3
        return min(bot_score, 1.0)

    def calculate_organic_vs_fake(self, social_signals: SocialSignals) -> tuple[float, float]:
        """Split social hype into organic (real) vs fake (bot-driven).
        Returns (organic_score, fake_score) each 0-100.
        """
        total_mentions = (social_signals.twitter_mentions_24h +
                          social_signals.reddit_mentions_24h)
        if total_mentions == 0:
            return 0.0, 0.0

        bot_ratio = social_signals.bot_ratio
        organic_mentions = total_mentions * (1 - bot_ratio)
        fake_mentions = total_mentions * bot_ratio

        # Weight by sentiment quality
        sentiment_boost = max(0, social_signals.twitter_sentiment)
        organic_score = min(100, (organic_mentions / 10) * (1 + sentiment_boost))
        fake_score = min(100, (fake_mentions / 10) * (1 + bot_ratio))

        return organic_score, fake_score

    # ── Full social scan ────────────────────────────────────────────

    async def scan_token_social(self, symbol: str, token_address: str = "") -> SocialSignals:
        """Full social scan for a token across all free sources."""
        twitter = await self.get_twitter_mentions(symbol)
        reddit = await self.get_reddit_mentions(symbol)

        signals = SocialSignals(
            token_symbol=symbol,
            twitter_mentions_24h=twitter.get("mentions", 0),
            twitter_sentiment=twitter.get("sentiment", 0.0),
            reddit_mentions_24h=reddit.get("mentions", 0),
            reddit_sentiment=reddit.get("sentiment", 0.0),
            timestamp=time.time(),
        )

        # Calculate bot ratio and organic/fake split
        social_data = {
            "twitter_mentions": signals.twitter_mentions_24h,
            "unique_posters": signals.twitter_mentions_24h * 0.3,  # estimate
            "repetition_rate": 0.3,
            "coordination_score": 0.2,
        }
        signals.bot_ratio = self.calculate_bot_ratio(social_data)
        signals.organic_hype_score, signals.fake_hype_score = self.calculate_organic_vs_fake(signals)

        # Viral coefficient (mentions growth rate estimation)
        if signals.twitter_mentions_24h > 0:
            signals.viral_coefficient = (signals.twitter_mentions_24h + signals.reddit_mentions_24h) / max(signals.telegram_members, 1)

        return signals

    async def scan_market_social(self, tokens: list[str]) -> list[SocialSignals]:
        """Batch social scan across multiple tokens — for market-wide monitoring."""
        results = []
        tasks = [self.scan_token_social(sym) for sym in tokens[:20]]  # limit concurrency
        signals = await asyncio.gather(*tasks, return_exceptions=True)
        for s in signals:
            if isinstance(s, SocialSignals):
                results.append(s)
        # Sort by organic hype
        results.sort(key=lambda x: x.organic_hype_score, reverse=True)
        return results

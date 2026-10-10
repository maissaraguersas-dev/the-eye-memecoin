"""THE EYE — Market Data Monitor

Free sources: CoinGecko free API, DexScreener, Birdeye, GeckoTerminal.
"""
import asyncio
import aiohttp
import time
from typing import Optional
from dataclasses import dataclass, field

from config.settings import settings


@dataclass
class MarketData:
    token_address: str
    symbol: str
    chain: str
    price_usd: float = 0.0
    price_change_1h: float = 0.0
    price_change_24h: float = 0.0
    price_change_7d: float = 0.0
    volume_24h: float = 0.0
    volume_change_24h: float = 0.0
    market_cap_usd: float = 0.0
    liquidity_usd: float = 0.0
    buys_24h: int = 0
    sells_24h: int = 0
    buy_sell_ratio: float = 0.0
    volume_price_divergence: bool = False
    holder_change_24h: int = 0
    age_hours: float = 0.0
    timestamp: float = 0.0


@dataclass
class MarketOverview:
    total_tokens_scanned: int = 0
    avg_volume_24h: float = 0.0
    avg_price_change_24h: float = 0.0
    top_gainers: list = field(default_factory=list)
    top_losers: list = field(default_factory=list)
    highest_volume: list = field(default_factory=list)
    newest_tokens: list = field(default_factory=list)
    suspicious_tokens: list = field(default_factory=list)
    timestamp: float = 0.0


class MarketMonitor:
    """Fetch market data from free APIs — no API keys required."""

    COINGECKO_BASE = "https://api.coingecko.com/api/v3"
    DEXSCREENER_BASE = "https://api.dexscreener.com"
    BIRDEYE_BASE = "https://public-api.birdeye.so"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # ── CoinGecko (free tier) ───────────────────────────────────────

    async def get_trending_coingecko(self) -> list[dict]:
        """Get trending coins from CoinGecko (free)."""
        session = await self._get_session()
        try:
            url = f"{self.COINGECKO_BASE}/search/trending"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("coins", [])
        except Exception as e:
            print(f"[CoinGecko trending error] {e}")
        return []

    async def get_new_coins_coingecko(self) -> list[dict]:
        """Get recently added coins from CoinGecko (free)."""
        session = await self._get_session()
        try:
            url = f"{self.COINGECKO_BASE}/coins/list/new"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
        except Exception as e:
            print(f"[CoinGecko new coins error] {e}")
        return []

    # ── DexScreener market data ─────────────────────────────────────

    async def get_token_market_data(self, address: str, chain: str = "eth") -> Optional[MarketData]:
        """Get detailed market data for a token."""
        session = await self._get_session()
        try:
            url = f"{self.DEXSCREENER_BASE}/latest/dex/search?q={address}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for pair in data.get("pairs", []):
                        return self._parse_market_pair(pair, chain)
        except Exception as e:
            print(f"[Market data error] {e}")
        return None

    async def scan_market_overview(self, tokens: list[dict]) -> MarketOverview:
        """Build a market overview from scanned tokens — market-wide analysis."""
        overview = MarketOverview(timestamp=time.time())
        market_data_list = []

        for token_info in tokens[:100]:
            address = token_info.get("address", "")
            chain = token_info.get("chain", "eth")
            md = await self.get_token_market_data(address, chain)
            if md:
                market_data_list.append(md)

        if not market_data_list:
            return overview

        overview.total_tokens_scanned = len(market_data_list)
        overview.avg_volume_24h = sum(m.volume_24h for m in market_data_list) / len(market_data_list)
        overview.avg_price_change_24h = sum(m.price_change_24h for m in market_data_list) / len(market_data_list)

        # Sort and rank
        by_gain = sorted(market_data_list, key=lambda m: m.price_change_24h, reverse=True)
        by_loss = sorted(market_data_list, key=lambda m: m.price_change_24h)
        by_vol = sorted(market_data_list, key=lambda m: m.volume_24h, reverse=True)
        by_age = sorted(market_data_list, key=lambda m: m.age_hours)

        overview.top_gainers = [(m.symbol, m.price_change_24h, m.volume_24h) for m in by_gain[:10]]
        overview.top_losers = [(m.symbol, m.price_change_24h, m.volume_24h) for m in by_loss[:10]]
        overview.highest_volume = [(m.symbol, m.volume_24h, m.price_change_24h) for m in by_vol[:10]]
        overview.newest_tokens = [(m.symbol, m.age_hours, m.volume_24h) for m in by_age[:10]]

        # Detect suspicious: volume-price divergence
        for m in market_data_list:
            if m.volume_24h > 10000 and m.price_change_24h < -5:
                m.volume_price_divergence = True
                overview.suspicious_tokens.append((m.symbol, "vol↑price↓", m.volume_24h))

        return overview

    # ── Batch scan for market monitor ───────────────────────────────

    async def batch_get_market_data(self, addresses: list[tuple[str, str]]) -> list[MarketData]:
        """Batch fetch market data for multiple tokens. Input: [(address, chain), ...]"""
        results = []
        tasks = [self.get_token_market_data(addr, chain) for addr, chain in addresses[:30]]
        data = await asyncio.gather(*tasks, return_exceptions=True)
        for d in data:
            if isinstance(d, MarketData):
                results.append(d)
        return results

    # ── Parser ──────────────────────────────────────────────────────

    def _parse_market_pair(self, pair: dict, chain: str) -> Optional[MarketData]:
        if not pair:
            return None
        try:
            base = pair.get("baseToken", {})
            buys = int(pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0)
            sells = int(pair.get("txns", {}).get("h24", {}).get("sells", 0) or 0)
            ratio = buys / max(sells, 1)
            created = pair.get("pairCreatedAt", 0) or 0
            age_h = (time.time() * 1000 - created) / (1000 * 3600) if created else 999

            return MarketData(
                token_address=base.get("address", ""),
                symbol=base.get("symbol", ""),
                chain=chain,
                price_usd=float(pair.get("priceUsd", 0) or 0),
                price_change_1h=float(pair.get("priceChange", {}).get("h1", 0) or 0),
                price_change_24h=float(pair.get("priceChange", {}).get("h24", 0) or 0),
                price_change_7d=float(pair.get("priceChange", {}).get("d7", 0) or 0),
                volume_24h=float(pair.get("volume", {}).get("h24", 0) or 0),
                market_cap_usd=float(pair.get("marketCap", 0) or 0),
                liquidity_usd=float(pair.get("liquidity", {}).get("usd", 0) or 0),
                buys_24h=buys,
                sells_24h=sells,
                buy_sell_ratio=ratio,
                age_hours=age_h,
                timestamp=time.time(),
            )
        except Exception:
            return None

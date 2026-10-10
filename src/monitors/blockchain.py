"""THE EYE — Blockchain Monitor

Free data sources: DexScreener, GeckoTerminal, CoinGecko.
No API keys required. All endpoints verified working.
"""
import asyncio
import aiohttp
import time
from typing import Optional
from dataclasses import dataclass, field

from config.settings import settings


@dataclass
class TokenOnChain:
    address: str
    name: str = ""
    symbol: str = ""
    chain: str = "eth"
    price_usd: float = 0.0
    price_change_1h: float = 0.0
    price_change_24h: float = 0.0
    volume_24h: float = 0.0
    liquidity_usd: float = 0.0
    market_cap_usd: float = 0.0
    holders_count: int = 0
    buys_24h: int = 0
    sells_24h: int = 0
    deployer_address: str = ""
    created_at: float = 0.0
    liquidity_locked: bool = False
    lock_duration_days: float = 0.0
    top_holders: list = field(default_factory=list)
    dex_id: str = ""
    pair_address: str = ""
    fdv: float = 0.0


# Chain name → DexScreener chainId
CHAIN_TO_DEXSCREENER = {
    "eth": "ethereum",
    "sol": "solana",
    "base": "base",
    "arb": "arbitrum",
    "bsc": "bsc",
}

# Chain name → GeckoTerminal network slug
CHAIN_TO_GECKOTERMINAL = {
    "eth": "eth",
    "sol": "solana",
    "base": "base",
    "arb": "arbitrum",
    "bsc": "bsc",
}

# DexScreener chainId → our chain name
DEXSCREENER_TO_CHAIN = {v: k for k, v in CHAIN_TO_DEXSCREENER.items()}
DEXSCREENER_TO_CHAIN.update({
    "polygon": "matic",
    "optimism": "op",
    "avalanche": "avax",
})


class BlockchainMonitor:
    """Fetch on-chain data from free APIs — no API keys required."""

    DEXSCREENER_BASE = "https://api.dexscreener.com"
    GECKOTERMINAL_BASE = "https://api.geckoterminal.com/api/v2"

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

    # ── DexScreener ─────────────────────────────────────────────────

    async def search_dexscreener(self, query: str) -> list[dict]:
        """Search tokens by name, symbol, or address on DexScreener."""
        session = await self._get_session()
        try:
            url = f"{self.DEXSCREENER_BASE}/latest/dex/search?q={query}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("pairs", [])
        except Exception as e:
            print(f"  [DexScreener error] {e}")
        return []

    async def get_token_by_address(self, address: str, chain: str = "eth") -> Optional[TokenOnChain]:
        """Get token data by contract address, filtered by chain."""
        results = await self.search_dexscreener(address)
        target_chain_id = CHAIN_TO_DEXSCREENER.get(chain, chain)

        # First try exact chain match
        for pair in results:
            if pair.get("chainId") == target_chain_id:
                return self._parse_dexscreener_pair(pair)

        # Fallback: return best result (highest liquidity)
        if results:
            sorted_pairs = sorted(
                results,
                key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0),
                reverse=True
            )
            return self._parse_dexscreener_pair(sorted_pairs[0])
        return None

    async def get_token_boosts(self) -> list[dict]:
        """Get latest boosted tokens from DexScreener."""
        session = await self._get_session()
        try:
            url = f"{self.DEXSCREENER_BASE}/latest/token-boosts/latest"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
        except Exception:
            pass
        return []

    async def get_token_profiles(self) -> list[dict]:
        """Get token profiles from DexScreener — links, socials, descriptions."""
        session = await self._get_session()
        try:
            url = f"{self.DEXSCREENER_BASE}/latest/token-profiles"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
        except Exception:
            pass
        return []

    # ── GeckoTerminal ───────────────────────────────────────────────

    async def get_trending_pools(self, chain: str = "eth") -> list[dict]:
        """Get trending pools from GeckoTerminal for a chain."""
        session = await self._get_session()
        net = CHAIN_TO_GECKOTERMINAL.get(chain, chain)
        try:
            url = f"{self.GECKOTERMINAL_BASE}/networks/{net}/trending_pools"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
        except Exception:
            pass
        return []

    async def get_new_pools(self, chain: str = "eth") -> list[dict]:
        """Get newly created pools from GeckoTerminal — fresh launch detection."""
        session = await self._get_session()
        net = CHAIN_TO_GECKOTERMINAL.get(chain, chain)
        try:
            url = f"{self.GECKOTERMINAL_BASE}/networks/{net}/new_pools"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
        except Exception:
            pass
        return []

    # ── Market-wide discovery ───────────────────────────────────────

    async def discover_all_tokens(self) -> list[TokenOnChain]:
        """Scan all chains for trending + new tokens — the market-wide discovery engine."""
        all_tokens = []
        chains = settings.chains

        # 1. GeckoTerminal: trending + new pools per chain
        for chain in chains:
            try:
                trending = await self.get_trending_pools(chain)
                for pool in trending:
                    token = self._parse_geckoterminal_pool(pool, chain)
                    if token:
                        all_tokens.append(token)
            except Exception:
                pass

            await asyncio.sleep(0.3)  # rate limit

            try:
                new = await self.get_new_pools(chain)
                for pool in new:
                    token = self._parse_geckoterminal_pool(pool, chain)
                    if token:
                        all_tokens.append(token)
            except Exception:
                pass

            await asyncio.sleep(0.3)

        # 2. DexScreener boosted tokens
        try:
            boosts = await self.get_token_boosts()
            for boost in boosts[:20]:
                addr = boost.get("tokenAddress", "")
                chain_hint = boost.get("chainId", "")
                chain = DEXSCREENER_TO_CHAIN.get(chain_hint, "eth")
                if addr:
                    all_tokens.append(TokenOnChain(
                        address=addr,
                        name=boost.get("name", ""),
                        symbol=boost.get("symbol", ""),
                        chain=chain,
                    ))
        except Exception:
            pass

        # Deduplicate
        seen = set()
        unique = []
        for t in all_tokens:
            key = f"{t.chain}:{t.address}"
            if key not in seen and t.address:
                seen.add(key)
                unique.append(t)

        return unique

    # ── Parsers ─────────────────────────────────────────────────────

    def _parse_dexscreener_pair(self, pair: dict) -> Optional[TokenOnChain]:
        if not pair:
            return None
        try:
            chain = DEXSCREENER_TO_CHAIN.get(pair.get("chainId", ""), pair.get("chainId", "eth"))
            base = pair.get("baseToken", {})
            return TokenOnChain(
                address=base.get("address", ""),
                name=base.get("name", ""),
                symbol=base.get("symbol", ""),
                chain=chain,
                price_usd=float(pair.get("priceUsd", 0) or 0),
                price_change_1h=float(pair.get("priceChange", {}).get("h1", 0) or 0),
                price_change_24h=float(pair.get("priceChange", {}).get("h24", 0) or 0),
                volume_24h=float(pair.get("volume", {}).get("h24", 0) or 0),
                liquidity_usd=float(pair.get("liquidity", {}).get("usd", 0) or 0),
                market_cap_usd=float(pair.get("marketCap", 0) or 0),
                buys_24h=int(pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0),
                sells_24h=int(pair.get("txns", {}).get("h24", {}).get("sells", 0) or 0),
                dex_id=pair.get("dexId", ""),
                pair_address=pair.get("pairAddress", ""),
                fdv=float(pair.get("fdv", 0) or 0),
                created_at=float(pair.get("pairCreatedAt", 0) or 0) / 1000 if pair.get("pairCreatedAt") else 0,
            )
        except Exception:
            return None

    def _parse_geckoterminal_pool(self, pool: dict, chain: str = "eth") -> Optional[TokenOnChain]:
        if not pool:
            return None
        try:
            attrs = pool.get("attributes", {})

            # GeckoTerminal pool attributes contain:
            #   name: "FWA / ETH" (pair name)
            #   base_token_price_usd, price_change_percentage.h24, volume_usd.h24
            #   reserve_in_usd (liquidity), market_cap_usd, fdv_usd
            #   transactions.h24.buys/sells

            # Extract base token info from relationships
            relationships = pool.get("relationships", {})
            base_data = relationships.get("base_token", {}).get("data", {})
            base_attrs = base_data.get("attributes", {})

            # Name/symbol: pool name is "SYMBOL / WETH", extract base symbol
            pool_name = attrs.get("name", "")
            if pool_name and " / " in pool_name:
                symbol = pool_name.split(" / ")[0].strip()
            else:
                symbol = base_attrs.get("symbol", "") or pool_name

            # Token address: base_data.id is like "eth_0xa0df..." — extract the hex part
            base_id = base_data.get("id", "")
            if "_" in base_id:
                address = base_id.split("_", 1)[1]
            else:
                address = base_id or attrs.get("address", "")

            # Price
            price_usd = float(attrs.get("base_token_price_usd", 0) or 0)

            # 24h price change
            price_change = attrs.get("price_change_percentage", {})
            price_change_24h = float(price_change.get("h24", 0) or 0)
            price_change_1h = float(price_change.get("h1", 0) or 0)

            # Volume (nested dict)
            vol_obj = attrs.get("volume_usd", {})
            if isinstance(vol_obj, dict):
                volume_24h = float(vol_obj.get("h24", 0) or 0)
            else:
                volume_24h = float(vol_obj or 0)

            # Transactions
            txs = attrs.get("transactions", {})
            txs_h24 = txs.get("h24", {}) if isinstance(txs, dict) else {}
            buys = int(txs_h24.get("buys", 0) or 0)
            sells = int(txs_h24.get("sells", 0) or 0)

            # Pool creation time
            created = attrs.get("pool_created_at", "")
            created_at = 0.0
            if created:
                try:
                    from datetime import datetime, timezone
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    created_at = dt.timestamp()
                except Exception:
                    pass

            return TokenOnChain(
                address=address,
                name=base_attrs.get("name", "") or symbol,
                symbol=symbol,
                chain=chain,
                price_usd=price_usd,
                price_change_1h=price_change_1h,
                price_change_24h=price_change_24h,
                volume_24h=volume_24h,
                liquidity_usd=float(attrs.get("reserve_in_usd", 0) or 0),
                market_cap_usd=float(attrs.get("market_cap_usd", 0) or 0),
                buys_24h=buys,
                sells_24h=sells,
                dex_id=attrs.get("dex_id", ""),
                pair_address=attrs.get("address", ""),
                fdv=float(attrs.get("fdv_usd", 0) or 0),
                created_at=created_at,
            )
        except Exception:
            return None

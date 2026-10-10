# Free Data Sources Guide — THE EYE

## Overview
THE EYE operates 100% on free data sources. This guide provides a complete directory of every free source used, their rate limits, capabilities, and alternatives if a source goes down.

---

## Blockchain Data Sources

| Source | Chains | Rate Limit | Key Required | Capabilities |
|--------|--------|------------|--------------|-------------|
| **Blockchair** | BTC, ETH, SOL, BNB, +15 | ~1 req/3s | No | Transactions, balances, blocks |
| **Etherscan** | Ethereum | 5 req/s | Optional (free) | TX history, contract code, holders, events |
| **BscScan** | BSC | 5 req/s | Optional (free) | Same as Etherscan, for BSC |
| **Arbiscan** | Arbitrum | 5 req/s | Optional (free) | Same as Etherscan, for Arbitrum |
| **Solscan** | Solana | Generous | No | TX details, token info, holdings |
| **DexScreener** | All DEX chains | ~100 req/min | No | DEX pairs, price, volume, liquidity, trades |
| **GoPlus Security** | ETH, BSC, SOL, +6 | 10 req/s | No | Contract security, honeypot detection |
| **Token Sniffer** | ETH, BSC | Varies | No | Clone detection, security score |

### Etherscan Family (Free Tier)
- **Etherscan**: Ethereum mainnet
- **BscScan**: BNB Smart Chain
- **Arbiscan**: Arbitrum
- **Polygonscan**: Polygon
- **Optimistic Etherscan**: Optimism
- **BaseScan**: Base
- All share the same API structure and free tier limits

### Blockchain Source Selection Strategy
1. **For DEX data**: Always use DexScreener first (most complete, free)
2. **For contract analysis**: Etherscan family (source code, events)
3. **For security checks**: GoPlus Security → Token Sniffer
4. **For Solana**: Solscan → Birdeye
5. **For general data**: Blockchair (broadest chain support)

---

## Social Data Sources

| Source | Type | Rate Limit | Key Required | Capabilities |
|--------|------|------------|--------------|-------------|
| **Nitter** | Twitter/X proxy | ~1 req/2s | No | Tweet search, timelines, hashtags |
| **Reddit JSON API** | Reddit | 60 req/min | No | Subreddit posts, comments, search |
| **Telegram Bot API** | Telegram | 30 msg/s | Bot token (free) | Group messages, channel monitoring |

### Nitter Instances (Rotation List)
Public Nitter instances rotate to avoid single-point failure:
```
https://nitter.net
https://nitter.poast.org
https://nitter.privacydev.net
https://nitter.woodland.cafe
https://nitter.kavin.rocks
```
**Fallback**: If all Nitter instances fail, social scanning relies on Reddit and Telegram only.

### Reddit Subreddits Monitored
```
r/cc, r/solana, r/ethtrader, r/cryptomoonshots
r/memecoins, r/dogecoin, r/shibainucoin, r/SatoshiBets
r/CryptoCurrency, r/altcoin
```

### Social Source Selection Strategy
1. **For Twitter/X**: Nitter (rotate instances on failure)
2. **For community sentiment**: Reddit JSON API
3. **For pump signals**: Telegram Bot (if configured)
4. **For token discovery**: DexScreener social links

---

## Market Data Sources

| Source | Chains | Rate Limit | Key Required | Capabilities |
|--------|--------|------------|--------------|-------------|
| **CoinGecko** | All | 30 req/min | Optional (demo) | Price, volume, mcap, trending, historical |
| **DexScreener** | All DEX | ~100 req/min | No | Real-time DEX data, pairs, trades |
| **GeckoTerminal** | All | 30 req/min | No | DEX pools, OHLCV, trending |
| **Birdeye** | Solana-focused | Varies | Optional | SOL prices, trending, new listings |
| **DefiLlama** | All DeFi | ~30 req/min | No | TVL, protocol data, yields |

### CoinGecko Free vs Demo Key

| Feature | No Key | Demo Key (Free) |
|---------|--------|------------------|
| Rate limit | 30 req/min | 500 req/min |
| Historical data | Limited | Extended |
| Trending | Yes | Yes |
| Search | Yes | Yes |

**Demo Key**: Register at coingecko.com for free — highly recommended.

### Market Source Selection Strategy
1. **For real-time DEX price**: DexScreener (fastest, most reliable)
2. **For market cap/rankings**: CoinGecko
3. **For OHLCV charts**: GeckoTerminal
4. **For Solana tokens**: Birdeye → DexScreener
5. **For macro context**: CoinGecko (BTC dominance) + DefiLlama (TVL)

---

## Rate Limit Summary

| Source | Requests/Min | Cache TTL | Priority |
|--------|-------------|-----------|----------|
| DexScreener | 100 | 30s | Primary |
| CoinGecko (demo) | 500 | 60s | Primary |
| CoinGecko (no key) | 30 | 60s | Primary |
| GeckoTerminal | 30 | 60s | Secondary |
| Etherscan | 300 | 60s | Secondary |
| Blockchair | 20 | 120s | Secondary |
| Reddit | 30 | 300s | Secondary |
| Nitter | 30 | 300s | Secondary |
| Birdeye | 20 | 30s | Tertiary |
| GoPlus | 600 | 3600s | On-demand |
| Solscan | 30 | 60s | On-demand |

---

## Fallback Chains

### If DexScreener is down:
1. GeckoTerminal (same data, different API)
2. CoinGecko (limited DEX data)
3. Birdeye (for Solana)

### If CoinGecko is down:
1. DexScreener (has price data)
2. CoinMarketCap (basic free tier)
3. GeckoTerminal

### If Nitter is down (all instances):
1. Reddit (alternative social signal)
2. Telegram (if configured)
3. Skip social scoring (mark as UNAVAILABLE)

### If Etherscan is down:
1. Blockchair (limited contract data)
2. DexScreener (transaction data from DEX)
3. Skip contract analysis (increase rug risk uncertainty)

---

## Cost Guarantee
**Total cost: $0.00** — All sources listed above are free. Optional API keys provide higher rate limits but are not required for core functionality.

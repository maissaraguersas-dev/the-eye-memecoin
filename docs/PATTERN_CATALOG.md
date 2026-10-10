# Pattern Catalog — THE EYE

## Overview
This catalog describes every pattern THE EYE can detect, with examples, confidence thresholds, and predicted outcomes.

---

## Whale Patterns

### W1: Whale Accumulation Cluster
**Description**: 3+ large wallets buying the same token within a 4-hour window.

**Signals**:
- Multiple transactions >$10K to same token contract
- Wallets are not linked (independent actors)
- Buy timing clusters within tight window

**Example**:
```
Token: 0xPEPE... 
02:14 UTC — Wallet A buys $25K
02:18 UTC — Wallet B buys $40K  
02:31 UTC — Wallet C buys $15K
→ Accumulation Cluster detected (confidence: 0.75)
```

**Predicted Outcome**: Bullish pressure, price increase likely within 12-24h
**Confidence Range**: 0.5-0.9 (higher with more whales, higher volume, historically accurate whales)

### W2: Whale Distribution Cascade
**Description**: Top holders sequentially selling their positions.

**Signals**:
- Top 10 holders selling in sequence
- Sell volume increasing over time
- New wallets receiving tokens (retail absorption)

**Example**:
```
Token: 0xBONK...
Whale #1 sells 2% of supply → Whale #2 sells 1.5% → Whale #3 sells 1%
→ Distribution Cascade (confidence: 0.80)
```

**Predicted Outcome**: Price decline, potential dump within 6-12h
**Confidence Range**: 0.6-0.9

### W3: Whale Wallet Rebirth
**Description**: A previously profitable whale re-enters a position after exiting.

**Signals**:
- Whale sold at profit previously
- Same whale buying back same token
- Time since exit: 1-14 days

**Predicted Outcome**: Moderate bullish signal
**Confidence Range**: 0.4-0.6

### W4: Coordinated Wash Trade
**Description**: Circular whale transactions creating artificial volume.

**Signals**:
- Funds returning to source wallet within 3 hops
- Same wallets buying and selling repeatedly
- Volume without price impact

**Predicted Outcome**: Manipulation detected, price likely to dump when washing stops
**Confidence Range**: 0.7-0.95

---

## Rug Pull Patterns

### R1: Honeypot Contract
**Description**: Token can be bought but selling is blocked or severely restricted.

**Signals**:
- Buy transactions succeed, sell transactions fail
- Contract contains transfer restrictions
- High buy count, zero sell count

**Example**:
```
Token: 0xSCAM...
Buys: 342, Sells: 0 (all fail with "transfer failed")
→ Honeypot detected (confidence: 0.95)
```

**Predicted Outcome**: 100% rug — users cannot recover funds
**Confidence Range**: 0.9-1.0

### R2: Liquidity Drain Setup
**Description**: Developer holds LP tokens with no lock, enabling instant liquidity removal.

**Signals**:
- LP tokens in deployer wallet
- No liquidity lock contract
- Low liquidity relative to market cap

**Predicted Outcome**: Rug pull when dev removes liquidity
**Confidence Range**: 0.6-0.9

### R3: Developer Serial Rugger
**Description**: Same developer wallet has deployed tokens that were previously rugged.

**Signals**:
- Dev wallet in dev_db with rug_count > 0
- Same funded_from source as known rugger
- Similar contract bytecode to previous rugs

**Predicted Outcome**: High probability of rug (>80%)
**Confidence Range**: 0.7-0.95

### R4: Token Migration Bait
**Description**: Pattern where holders are encouraged to migrate to a "new" token that is actually a trap.

**Signals**:
- Announcement of "upgrade" or "V2" token
- Original token still tradeable but deprecated
- New token has worse contract terms

**Predicted Outcome**: V2 token will rug, V1 may also be drained
**Confidence Range**: 0.5-0.8

### R5: Flash Loan Vulnerability
**Description**: LP configuration that allows flash loan exploitation.

**Signals**:
- Single token pair with low liquidity
- No flash loan guard in contract
- Pool can be manipulated with single large transaction

**Predicted Outcome**: Pool will be exploited, token price goes to 0
**Confidence Range**: 0.5-0.8

---

## Pump Patterns

### P1: Telegram Coordinated Pump
**Description**: Buy signal posted in Telegram group, followed by synchronized buying.

**Signals**:
- "Buy signal" message in monitored group
- 5+ wallets buying within 5 minutes of signal
- Planned dump time mentioned or implied

**Example**:
```
14:00 — Telegram: "🚀 BUY $SCAM NOW! Dump at 14:30!"
14:01-14:05 — 23 wallets buy
14:30 — Top holders sell
→ Coordinated Pump (confidence: 0.90)
```

**Predicted Outcome**: Dump at announced time or shortly after
**Confidence Range**: 0.7-0.95

### P2: Volume Inflation (Wash Trading)
**Description**: High trading volume with no price impact, indicating wash trading.

**Signals**:
- Volume >200% of average but price change <5%
- Same wallets on both buy and sell side
- Circular transaction patterns

**Predicted Outcome**: Artificial volume will stop, price will correct
**Confidence Range**: 0.6-0.9

### P3: Spoof Liquidity
**Description**: Large buy walls that disappear when price approaches.

**Signals**:
- Large orders visible in order book
- Orders cancelled before execution
- Pattern repeats multiple times

**Predicted Outcome**: Price will not reach spoof level, real sell pressure behind wall
**Confidence Range**: 0.5-0.7

### P4: Dev Wallet Pump
**Description**: Developer buying their own token to create momentum.

**Signals**:
- Deployer wallet buying tokens
- Buy timed with marketing pushes
- No organic volume increase

**Predicted Outcome**: Pump will be short-lived, dev will eventually sell
**Confidence Range**: 0.5-0.8

---

## Temporal Patterns

### T1: Ghost Hour Rug
**Description**: Rug pulls that occur during lowest-activity hours (02:00-06:00 UTC).

**Signals**:
- Token age <48h
- Liquidity removal during ghost hours
- Minimal monitoring during this window

**Statistical Basis**: ~70% of rug pulls occur between 02:00-06:00 UTC
**Predicted Outcome**: Rug pull in progress or imminent
**Confidence Range**: 0.5-0.8

### T2: Weekend Drain
**Description**: Dumping during weekends when retail monitoring is lower.

**Signals**:
- Large sell orders on Saturday/Sunday
- Reduced social activity (fewer users online)
- Whale selling into thin weekend liquidity

**Predicted Outcome**: Continued selling pressure through weekend
**Confidence Range**: 0.4-0.7

### T3: Post-Listing Dump
**Description**: Coordinated selling after exchange listing creates hype.

**Signals**:
- Token recently listed on CEX
- Sell volume spikes 4-12h after listing
- Top holders reducing positions

**Predicted Outcome**: Price decline 10-50% within 24h of listing
**Confidence Range**: 0.6-0.8

### T4: Rotation Risk
**Description**: Capital leaving memecoins when BTC dominance rises.

**Signals**:
- BTC dominance increasing >1% in 24h
- Memecoin sector volume declining
- Risk-off sentiment in social media

**Predicted Outcome**: Broad memecoin sell-off
**Confidence Range**: 0.4-0.7

### T5: Unlock Cliff
**Description**: Token unlocks creating sudden supply shock.

**Signals**:
- Large token unlock scheduled within 24h
- Unlock >5% of circulating supply
- Recipients likely to sell (investors, team)

**Predicted Outcome**: Price decline post-unlock as new supply hits market
**Confidence Range**: 0.5-0.8

---

## Pattern Interaction Matrix

When multiple patterns coincide, the combined prediction is stronger:

| Pattern A | Pattern B | Combined Effect |
|-----------|-----------|-----------------|
| W1 (Accumulation) | P1 (Coordinated Pump) | Contradictory — reduce confidence |
| R1 (Honeypot) | Any | R1 overrides all — EXIT_NOW |
| W2 (Distribution) | T1 (Ghost Hour) | Strong dump signal — +0.2 confidence |
| R2 (Liquidity Drain) | T1 (Ghost Hour) | Strong rug signal — +0.3 confidence |
| P1 (Telegram Pump) | W4 (Wash Trade) | Confirmed manipulation — +0.2 confidence |
| T4 (Rotation Risk) | W2 (Distribution) | Sector-wide dump — +0.15 confidence |

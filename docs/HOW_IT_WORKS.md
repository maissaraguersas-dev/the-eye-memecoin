# 🐋👁️ HOW THE EYE WORKS — Complete Technical Explanation

This document explains exactly how every component of THE EYE works, from data fetch to alert dispatch. No black boxes — everything explained.

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────┐
│                    THE EYE ENGINE                        │
│                                                         │
│  1. DISCOVER    Scan all chains for tokens              │
│       ↓                                                 │
│  2. FETCH       Get price, volume, liquidity, holders   │
│       ↓                                                 │
│  3. ANALYZE     Run all detection engines               │
│       ↓                                                 │
│  4. SCORE       Calculate rug %, moon %, predictions    │
│       ↓                                                 │
│  5. ALERT       WHO/WHAT/WHY/WHEN/HOW to all channels   │
│       ↓                                                 │
│  6. LEARN       Track prediction accuracy, improve      │
└─────────────────────────────────────────────────────────┘
```

THE EYE is NOT a portfolio tracker. It does not watch your bags. It watches the **entire market** — every memecoin on every chain — looking for patterns that indicate opportunities or risks.

---

## Step 1: DISCOVERY — Finding Tokens

### How It Works

When you run `opencode scan-market`, the system:

1. **Queries DexScreener** for boosted/trending tokens across all chains
2. **Queries GeckoTerminal** for trending pools AND new pools on each chain (ETH, SOL, Base, ARB, BSC)
3. **Queries CoinGecko** for trending coins globally
4. **Deduplicates** by chain+address (same token on multiple DEXes = one token)

### What APIs Are Called

| API Call | URL | Frequency | Returns |
|----------|-----|-----------|---------|
| DexScreener Boosted | `api.dexscreener.com/latest/token-boosts/latest` | Per scan | ~20-50 tokens |
| DexScreener Profiles | `api.dexscreener.com/latest/token-profiles` | Per scan | ~100 tokens |
| GeckoTerminal Trending | `api.geckoterminal.com/api/v2/networks/{chain}/trending_pools` | Per chain | ~25 pools/chain |
| GeckoTerminal New | `api.geckoterminal.com/api/v2/networks/{chain}/new_pools` | Per chain | ~25 pools/chain |
| CoinGecko Trending | `api.coingecko.com/api/v3/search/trending` | Per scan | ~7 coins |

### Token Filtering

Not every token gets a full scan. Tokens are filtered by:
- **Minimum liquidity**: $1,000 (configurable)
- **Minimum 24h volume**: $500 (configurable)
- **Max per cycle**: 200 tokens (to avoid API rate limits)

---

## Step 2: FETCH — Getting Token Data

For each token that passes filtering, THE EYE fetches:

### Blockchain Data (`src/monitors/blockchain.py`)

**DexScreener** provides:
- Token address, name, symbol, chain
- Price in USD
- 1-hour and 24-hour price changes
- 24-hour volume and liquidity
- Market cap and FDV (Fully Diluted Valuation)
- Buy/sell transaction counts (24h)
- Pair creation timestamp (to detect new launches)
- Deployer address (for dev rug checks)

**GeckoTerminal** provides:
- Pool-level data (reserve amounts, pool creation time)
- Transaction counts and volumes per pool
-DEX identifier and pair address

### Market Data (`src/monitors/market.py`)

**CoinGecko** provides:
- Market cap rankings
- 24h price/volume changes
- Category data (is it tagged as "memecoin"?)
- Community data (Twitter followers, Reddit subscribers)

### Social Data (`src/monitors/social.py`)

**Twitter (via Nitter)** provides:
- Mention count in the last 24h
- Sentiment score (positive/negative/neutral)
- Bot ratio estimation (repetitive posts, similar content)

**Reddit** provides:
- Post count mentioning the token
- Comment sentiment
- Upvote patterns

---

## Step 3: ANALYZE — Detection Engines

This is the core of THE EYE. Five engines run on every token:

### 3A. Whale Pattern Detection (`src/pattern/whale_matcher.py`)

**What it does**: Matches wallet behavior against 7 known whale patterns.

**How each pattern works**:

1. **Sniper Pattern**:
   - Wallet buys within the first 3 blocks of token launch
   - Sells within 1-3 hours at peak
   - Score: buy_block < 3 AND sell within 3h AND profit > 50%

2. **Accumulate→Pump→Dump**:
   - Wallet accumulates over 24-72h (small buys, no sells)
   - Then pumps (large buy or shill on social)
   - Then dumps (large sell within hours of pump)
   - Score: accumulation_ratio > 0.7 AND dump_pct > 15%

3. **Copy-Trader**:
   - Wallet's buys/sells correlate >0.8 with a known whale
   - Time delay < 5 minutes between copy and original
   - Score: correlation > 0.8 AND time_delay < 300s

4. **Diamond Hands**:
   - Wallet has held >30 days with no sells
   - Position is in profit (>100% gain)
   - This is a BULLISH signal
   - Score: hold_days > 30 AND pnl_pct > 100

5. **Failed Whale**:
   - Wallet made large buy at high price
   - Token dropped >50% and wallet hasn't sold
   - Likely stuck/trapped
   - Score: buy_at_top AND price_drop > 50% AND no_recent_sells

6. **Liquidity Migration**:
   - Dev or large holder removes LP from one DEX
   - Adds it to a different token or chain
   - Score: lp_removed AND lp_added_to_different_token

7. **Bridge Movement**:
   - Large holder bridges tokens to different chain
   - Often precedes cross-chain dump
   - Score: bridge_tx AND value > $10k

**Whale profiles are persisted** in `src/data/whale_profiles.json` so patterns are tracked across scans.

### 3B. Dev Rug Detection (`src/pattern/dev_matcher.py`)

**What it does**: Checks the token developer's wallet for 7 known rug signatures.

**How each signature works**:

1. **Soft Rug**:
   - Dev holds >10% of supply
   - Dev has been selling small amounts consistently
   - Social posts continue to shill while selling
   - Score: dev_supply_pct > 10% AND consistent_small_sells

2. **Hard Rug**:
   - Liquidity was removed entirely in one transaction
   - Or: dev called a function that transferred LP to themselves
   - Score: liquidity_removed AND dev_is_sender

3. **Honeypot**:
   - Token can be bought but not sold (sell always reverts)
   - Detect by checking if sell simulation fails
   - Score: sell_fails_on_simulation

4. **Mint Exploit**:
   - Contract has a hidden mint function
   - Dev can create tokens out of thin air
   - Score: hidden_mint_function_detected

5. **Proxy Rug**:
   - Contract uses upgradeable proxy pattern
   - Dev can change contract logic after deployment
   - Score: is_proxy AND dev_is_admin

6. **Serial Rugger**:
   - Dev wallet has created multiple tokens
   - Previous tokens all rugged (liquidity = 0, price = 0)
   - Score: num_rugged_tokens > 0

7. **Social-Only Rug**:
   - Token has elaborate social presence (website, Twitter, TG)
   - But contract has red flags (no audit, dev holds too much)
   - Score: has_social_presence AND contract_red_flags

**Dev signatures are persisted** in `src/data/dev_signatures.json`.

### 3C. Manipulation Detection (`src/pattern/manipulation_detector.py`)

**What it does**: Detects 7 forms of market manipulation using price/volume/holder data.

**How each type works**:

1. **Bot Army**:
   - Many wallets buying at the same second
   - Identical buy amounts
   - Wallets created within hours of each other
   - Score: simultaneous_buys > 5 AND identical_amounts

2. **Wash Trading**:
   - Same wallet or related wallets both buying and selling
   - Net position change ≈ 0 but volume is high
   - Score: buy_sell_same_wallet AND net_position ≈ 0

3. **Volume-Price Divergence**:
   - Volume increased >3x but price barely moved
   - Indicates fake volume (wash trades or bot activity)
   - Score: volume_spike > 3x AND price_change < 5%

4. **Social Manipulation**:
   - Bot ratio on social >70%
   - Coordinated posting pattern (many posts at same time)
   - Score: bot_ratio > 0.7 AND posting_coordination

5. **Holder Inflation**:
   - Holder count spiked but volume didn't
   - Many new wallets with identical balances
   - Score: holder_spike AND no_volume_increase

6. **Coordinated Pump**:
   - Multiple wallets buying within seconds
   - Similar buy amounts
   - Often after a social media signal
   - Score: simultaneous_buys AND correlated_amounts

7. **Spoofing**:
   - Large orders appearing in the order book then disappearing
   - Price moves toward the spoofed direction
   - Score: large_orders_cancelled AND price_followed

### 3D. Temporal Analysis (`src/analysis/temporal_analyzer.py`)

**What it does**: Determines the current time-based risk window.

**The 4 windows** (times in UTC):

| Window | Start | End | Risk | What Happens |
|--------|-------|-----|------|-------------|
| Rug Hour | 02:00 | 05:00 | 90% | Devs pull liquidity while Western traders sleep |
| FOMO Peak | 18:00 | 22:00 | 70% | Maximum retail activity, market tops form |
| Dead Zone | 08:00 | 12:00 | 30% | Low activity, slow drift, safe to research |
| Golden Hour | 14:00 | 16:00 | 20% | Post-lunch activity, organic growth, best entry |

**How it's calculated**:
1. Get current UTC hour
2. Match to the active window
3. Calculate risk score (higher during rug hour/FOMO peak)
4. Generate recommendation (e.g., "Avoid new entries during Rug Hour")

### 3E. Confidence Engine (`src/analysis/confidence.py`)

**What it does**: Weights signals by recency and frequency.

**How it works**:
- A signal seen 10 times in the last hour is weighted higher than one seen once
- Formula: `confidence = base_confidence × recency_factor × frequency_factor`
- `recency_factor` decays exponentially (half-life: 1 hour)
- `frequency_factor` increases logarithmically (more sightings = more confidence)

---

## Step 4: SCORE — Combining All Signals

### Rug Probability (`src/analysis/rug_probability.py`)

**Input**: All signals from whale, dev, manipulation, social, and temporal engines.
**Output**: A single number 0–100% representing rug probability.

**How it's calculated**:

```
rug_probability = (
    dev_rug_score × 0.35 +        # Dev behavior is the strongest signal
    whale_dump_score × 0.25 +      # Whale dump preparation
    manipulation_score × 0.20 +    # Market manipulation detected
    social_bot_score × 0.10 +      # Fake social presence
    temporal_risk × 0.10           # Time-of-day risk
)
```

**Risk levels**:
- 0–30%: LOW — probably safe
- 31–55%: MEDIUM — caution, monitor
- 56–75%: HIGH — avoid or set tight stop-loss
- 76–100%: CRITICAL — avoid entirely

### Pump Scorer (`src/analysis/pump_scorer.py`)

**Input**: Market data + manipulation results + social signals.
**Output**: Two scores — Moon Score (organic) and Fake Pump Score (artificial).

**Moon Score factors** (higher = more likely organic pump):
- Volume spike with price increase (organic demand)
- High buy/sell ratio (>2:1)
- Low bot ratio on social
- Multiple independent buyers (not coordinated)
- Positive social sentiment

**Fake Pump factors** (higher = more likely fake pump):
- Volume spike without price follow-through
- Wash trading detected
- High bot ratio on social
- Coordinated buying patterns
- Volume-price divergence

**Verdict**:
- moon_score > 60 AND fake_pump < 30 → "ORGANIC MOON"
- moon_score > 50 AND fake_pump > 50 → "SUSPICIOUS PUMP"
- fake_pump > 60 AND moon < 40 → "FAKE PUMP — AVOID"
- Otherwise → "INCONCLUSIVE"

### Prediction Engine (`src/analysis/prediction.py`)

**Input**: All scores + market data + temporal window.
**Output**: Prediction with type, timing, magnitude, confidence, urgency.

**How predictions are made**:

1. **Rug Imminent**: rug_probability > 75% AND in Rug Hour → timing: "minutes", magnitude: "-80% to -100%"
2. **Pump Likely**: moon_score > 60% AND in Golden Hour → timing: "1-6 hours", magnitude: "+30% to +200%"
3. **Dump Coming**: whale_dump_score > 60% AND price already dropping → timing: "1-4 hours", magnitude: "-20% to -50%"
4. **Accumulation**: whale_accumulating AND price_stable → timing: "ongoing", magnitude: "setup for pump"

**Confidence** is calculated by:
```
confidence = (
    signal_agreement × 0.4 +       # How many engines agree
    signal_strength × 0.3 +        # How strong each signal is
    historical_accuracy × 0.3      # Past prediction accuracy (self-improvement)
)
```

**Urgency levels**:
- `critical` — act now (rug imminent, whale dumping)
- `high` — act within minutes (pump building, temporal danger)
- `medium` — monitor closely (accumulation, suspicious activity)
- `low` — worth watching (interesting pattern, no immediate action)

---

## Step 5: ALERT — Dispatch System

### Alert Formatting (`src/alerts/formatter.py`)

Every alert follows the **WHO/WHAT/WHY/WHEN/HOW** framework:

- **WHO** — who is involved (token, dev, whale)
- **WHAT** — what is happening (rug detected, pump building, whale accumulating)
- **WHY** — why it matters (the evidence and reasoning)
- **WHEN** — when it's happening (NOW, building, temporal window)
- **HOW** — how to act (AVOID, consider entry, set stop-loss, monitor)

Plus: **CONFIDENCE** (0–100%) and **URGENCY** (low/medium/high/critical)

### Alert Dispatch (`src/alerts/dispatcher.py`)

Alerts go to 4 channels (all free):

1. **Terminal** — printed with emoji formatting
2. **Log file** — `src/data/alert_log.json` (last 500 alerts)
3. **Telegram** — via free Bot API (needs TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)
4. **Discord** — via free webhook (needs DISCORD_WEBHOOK_URL)

**Cooldown**: Same alert type for same token won't repeat within 5 minutes.
**Rate limit**: Max 20 alerts per hour to prevent spam.

### Alert Queue (`src/autonomous/alert_queue.py`)

Alerts are buffered in a FIFO queue before dispatch:
1. Alert is enqueued with timestamp
2. Queue is persisted to `src/data/alert_queue.json`
3. On flush, all pending alerts are dispatched
4. Failed dispatches are retried up to 3 times
5. After 3 failures, alert is marked as permanently failed
6. Old dispatched alerts (>24h) are cleaned up

---

## Step 6: LEARN — Self-Improvement

### How It Works

THE EYE tracks its own prediction accuracy and adjusts weights over time.

1. **Logging**: Every prediction is saved to `src/data/prediction_log.json` with:
   - Token, prediction type, confidence, timestamp
   - Predicted timing and magnitude

2. **Feedback**: After the predicted time window passes, the system checks:
   - Did the predicted event happen?
   - Was the magnitude correct?
   - Was the timing correct?

3. **Weight Adjustment**: If a prediction was wrong:
   - The signals that contributed are downweighted
   - The signals that were correct are upweighted
   - Adjustment factor: 0.1 (slow learning to avoid overfitting)

4. **Minimum Samples**: Weights only update after 10+ predictions for a signal type (to avoid noise)

### Backtesting

Run `opencode backtest` to see:
- Overall prediction accuracy %
- Accuracy by prediction type (rug, pump, dump, accumulation)
- Most reliable signals
- Least reliable signals
- Recommended weight adjustments

---

## The Full Scan Cycle (What Happens When You Run `scan-market`)

```
1. DISCOVERY PHASE (5-15 seconds)
   ├── DexScreener: get boosted tokens
   ├── GeckoTerminal: get trending pools per chain (5 chains)
   ├── GeckoTerminal: get new pools per chain (5 chains)
   ├── CoinGecko: get trending coins
   └── Deduplicate by chain+address

2. FILTERING PHASE (<1 second)
   ├── Remove tokens below min liquidity ($1,000)
   ├── Remove tokens below min volume ($500)
   └── Limit to 200 tokens per cycle

3. DEEP SCAN PHASE (30-120 seconds, 5 concurrent)
   For each token:
   ├── Fetch DexScreener token data
   ├── Fetch CoinGecko market data
   ├── Fetch social signals (Twitter + Reddit)
   ├── Run whale pattern detection (7 patterns)
   ├── Run dev rug detection (7 signatures)
   ├── Run manipulation detection (7 types)
   ├── Calculate rug probability (0-100%)
   ├── Calculate pump scores (moon vs fake)
   ├── Get temporal risk window
   ├── Calculate confidence
   └── Generate prediction

4. CLASSIFICATION PHASE (<1 second)
   ├── Sort by rug probability → rug alerts
   ├── Sort by moon score → pump alerts
   ├── Sort by whale activity → whale alerts
   ├── Sort by volume → trending
   └── Identify new launches (<24h old)

5. ALERT PHASE (1-5 seconds)
   ├── Format alerts (WHO/WHAT/WHY/WHEN/HOW)
   ├── Filter by min confidence (60%) and urgency
   ├── Apply cooldown (5 min) and rate limit (20/hr)
   └── Dispatch to terminal + log + Telegram + Discord

6. LEARNING PHASE (<1 second)
   ├── Log predictions
   ├── Check past prediction outcomes
   └── Adjust signal weights if enough samples
```

Total time per full scan: **30-120 seconds** depending on how many tokens pass filtering.

---

## Continuous Monitoring (`opencode monitor`)

When you run `opencode monitor`, the system:

1. Runs the full scan cycle above
2. Displays a summary in the terminal
3. Sleeps for 60 seconds (configurable)
4. Repeats forever until you press Ctrl+C

Each cycle shows:
- Tokens discovered and scanned
- Opportunities found (sorted by confidence)
- Risks detected (sorted by rug probability)
- Current temporal window
- Active alerts

---

## 24/7 Cron Mode (`scripts/setup-24-7.sh`)

Instead of one continuous loop, cron mode spreads scans across time:

| Scan | Interval | What It Does |
|------|----------|-------------|
| Blockchain | Every 5 min | Whale movements, new tokens |
| Social | Every 10 min | Twitter/Reddit sentiment |
| Market | Every 15 min | Full market-wide analysis |
| Temporal | Every 30 min | Time-window risk assessment |
| Alert Dispatch | Every 60 min | Flush queued alerts |

This is lighter on API rate limits than continuous monitoring and survives server restarts.

---

## Data Persistence

THE EYE stores all learned data in JSON files under `src/data/`:

| File | What's Stored | Purpose |
|------|--------------|---------|
| `whale_profiles.json` | Known whale wallets + patterns | Track whales across scans |
| `dev_signatures.json` | Known dev wallets + rug history | Detect serial rugger devs |
| `prediction_log.json` | All predictions + outcomes | Self-improvement |
| `learning_db.json` | Signal weights + accuracy | Adjust detection sensitivity |
| `alert_log.json` | All dispatched alerts | Audit trail |
| `alert_queue.json` | Pending alerts | Buffered dispatch |
| `watchlist.json` | User's watched tokens | Personal monitoring |

These files grow over time, making THE EYE smarter with more data.

---

## No Black Boxes

Every component above is in a single Python file you can read:
- Want to know how rug probability is calculated? → `src/analysis/rug_probability.py`
- Want to see the whale detection logic? → `src/pattern/whale_matcher.py`
- Want to understand alert formatting? → `src/alerts/formatter.py`

No compiled code, no hidden logic, no external services beyond the free APIs listed.

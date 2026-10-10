#!/usr/bin/env python3
"""🐋👁️  THE EYE — Memecoin Market Intelligence Engine

Monitors the ENTIRE memecoin market across all chains. Not your portfolio.
Identifies opportunities AND risks in real-time. 100% free data. No API keys.
"""
import sys
import os
import asyncio
import argparse
import time
import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.scanner.market_scanner import MarketScanner, TokenScanResult, MarketScanResult
from src.monitors.blockchain import BlockchainMonitor, TokenOnChain
from src.monitors.market import MarketMonitor
from src.alerts.formatter import AlertFormatter
from src.alerts.dispatcher import Dispatcher
from src.analysis.temporal_analyzer import TemporalAnalyzer
from src.analysis.prediction import PredictionEngine
from src.analysis.rug_probability import RugProbabilityEngine
from src.pattern.whale_matcher import WhaleMatcher
from src.pattern.dev_matcher import DevMatcher
from config.settings import settings

VERSION = "1.0.0"

# ── Display helpers ──────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

def c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"

def box(title: str, lines: list[str], width: int = 62) -> str:
    """Create a bordered box with title and content lines."""
    top = f"╔{'═'*(width-2)}╗"
    mid_title = f"║ {BOLD}{title.center(width-4)}{RESET} ║"
    sep = f"╟{'─'*int((width-4)/2)}┬{'─'*int((width-4)/2)}╡" if False else f"╟{'─'*(width-2)}╢"
    content = []
    for line in lines:
        # Truncate if too long
        if len(line) > width - 4:
            line = line[:width-7] + "..."
        content.append(f"║ {line.ljust(width-4)} ║")
    bot = f"╚{'═'*(width-2)}╝"
    return "\n".join([top, mid_title, sep, *content, bot])

def pct_bar(value: float, max_val: float = 100, width: int = 20) -> str:
    """Create a visual percentage bar."""
    ratio = min(value / max_val, 1.0) if max_val > 0 else 0
    filled = int(ratio * width)
    if ratio > 0.7:
        color = RED
    elif ratio > 0.4:
        color = YELLOW
    else:
        color = GREEN
    return f"{color}{'█'*filled}{'░'*(width-filled)}{RESET} {value:.0f}%"

def risk_label(level: str) -> str:
    colors = {"safe": GREEN, "low": GREEN, "medium": YELLOW,
              "high": RED, "critical": RED, "optimal": CYAN}
    return f"{colors.get(level, RESET)}{level.upper()}{RESET}"

def chain_label(chain: str) -> str:
    colors = {"eth": BLUE, "sol": MAGENTA, "base": BLUE,
              "arb": CYAN, "bsc": YELLOW}
    return f"{colors.get(chain, RESET)}{chain.upper()}{RESET}"

def money(val: float) -> str:
    if val >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    elif val >= 1_000:
        return f"${val/1_000:.1f}K"
    else:
        return f"${val:.2f}"

def price_fmt(val: float) -> str:
    if val == 0:
        return "—"
    elif val >= 1:
        return f"${val:,.2f}"
    elif val >= 0.001:
        return f"${val:.4f}"
    else:
        return f"${val:.8f}"

def change_fmt(val: float) -> str:
    if val > 0:
        return c(GREEN, f"+{val:.1f}%")
    elif val < 0:
        return c(RED, f"{val:.1f}%")
    return f"{val:.1f}%"


# ── BANNER ───────────────────────────────────────────────────────────

def show_banner():
    print()
    print(c(CYAN, "  ╔══════════════════════════════════════════════════════════╗"))
    print(c(CYAN, "  ║                                                          ║"))
    print(c(CYAN, "  ║") + BOLD + "   🐋👁️  THE EYE — Memecoin Market Intelligence Engine   " + RESET + c(CYAN, "║"))
    print(c(CYAN, "  ║                                                          ║"))
    print(c(CYAN, "  ║") + DIM + "   Monitors the ENTIRE market. Not your portfolio.        " + RESET + c(CYAN, "║"))
    print(c(CYAN, "  ║") + DIM + "   100% free data. No API keys. 5 chains. 16 sources.     " + RESET + c(CYAN, "║"))
    print(c(CYAN, "  ║") + f"   v{VERSION}                                                  " + c(CYAN, "║"))
    print(c(CYAN, "  ╚══════════════════════════════════════════════════════════╝"))
    print()


# ── HOW IT WORKS ─────────────────────────────────────────────────────

def show_how_it_works():
    """Show the intelligence pipeline — this is what the user was missing."""
    print()
    print(box("HOW THE EYE WORKS", [
        "",
        BOLD + "THE INTELLIGENCE PIPELINE" + RESET,
        "",
        "Every scan runs this exact sequence:",
        "",
        c(CYAN, "  1. DISCOVER") + " → Find all tokens across 5 chains",
        "             GeckoTerminal trending + new pools",
        "             DexScreener boosted tokens",
        "             CoinGecko trending coins",
        "",
        c(CYAN, "  2. FETCH") + "   → Get on-chain data for each token",
        "             Price, volume, liquidity, buy/sell ratio",
        "             Holders, market cap, deployer address",
        "",
        c(CYAN, "  3. ANALYZE") + " → Run 7+7+7 pattern detectors:",
        "             7 whale patterns (sniper, diamond hands, etc.)",
        "             7 dev rug signatures (soft rug, honeypot, etc.)",
        "             7 manipulation types (wash trade, bot army, etc.)",
        "",
        c(CYAN, "  4. SCORE") + "   → Combine all signals into scores:",
        "             Rug probability (0-100%)",
        "             Moon vs fake pump score",
        "             Temporal risk (what time is it?)",
        "",
        c(CYAN, "  5. PREDICT") + " → Generate forecasts:",
        "             What will happen, when, how big",
        "             Confidence + urgency + risk/reward",
        "",
        c(CYAN, "  6. ALERT") + "   → Send to Telegram/Discord/terminal",
        "             WHO / WHAT / WHY / WHEN / HOW",
        "             Filtered by confidence & urgency",
        "",
    ]))
    print()
    print(box("DATA SOURCES (ALL FREE)", [
        "",
        f"  {BOLD}Blockchain:{RESET}  DexScreener, GeckoTerminal, CoinGecko",
        f"  {BOLD}Social:{RESET}      Nitter/Twitter, Reddit, Telegram, Discord",
        f"  {BOLD}Market:{RESET}      DexScreener pairs, GeckoTerminal OHLCV",
        "",
        f"  Chains: {chain_label('eth')} {chain_label('sol')} {chain_label('base')} {chain_label('arb')} {chain_label('bsc')}",
        f"  Cost:   {c(GREEN, '$0')} — no API keys needed",
        "",
    ]))


# ── LIVE MARKET DASHBOARD ────────────────────────────────────────────

async def show_live_dashboard():
    """The main opencode experience — a live market overview dashboard."""
    show_banner()
    show_how_it_works()

    print(BOLD + "  Loading live market data..." + RESET)
    print()

    # ── Phase 1: Time window ────────────────────────────────────────
    temporal = TemporalAnalyzer().analyze()
    w = temporal.current_window

    print(box("CURRENT MARKET WINDOW", [
        "",
        f"  {w.emoji} {BOLD}{w.name}{RESET}",
        f"  UTC: {temporal.utc_hour:.1f}h  |  Window: {w.start_hour}:00-{w.end_hour}:00 UTC",
        f"  Risk: {pct_bar(w.risk_score)}  |  Level: {risk_label(w.risk_level)}",
        "",
        f"  {DIM}{w.description}{RESET}",
        "",
        f"  {temporal.recommendation}",
        "",
    ]))

    # ── Phase 2: Discover tokens across all chains ──────────────────
    print(DIM + "  Discovering tokens across all chains..." + RESET)

    blockchain = BlockchainMonitor()
    market = MarketMonitor()

    all_tokens = []
    source_counts = {"geckoterminal": 0, "coingecko": 0, "dexscreener": 0}

    # GeckoTerminal: trending pools per chain (best data source — has vol/liq/txs)
    for chain in settings.chains:
        try:
            pools = await blockchain.get_trending_pools(chain)
            for pool in pools:
                token = blockchain._parse_geckoterminal_pool(pool, chain)
                if token and token.symbol:
                    all_tokens.append(token)
                    source_counts["geckoterminal"] += 1
            await asyncio.sleep(0.5)  # rate limit between chains
        except Exception:
            pass

    # CoinGecko trending (basic info — name/symbol/mcap only)
    try:
        cg_trending = await market.get_trending_coingecko()
        for coin in cg_trending:
            item = coin.get("item", {})
            sym = item.get("symbol", "").upper()
            if sym:
                all_tokens.append(TokenOnChain(
                    address=item.get("id", ""),
                    name=item.get("name", ""),
                    symbol=sym,
                    chain="eth",
                    market_cap_usd=float(item.get("market_cap", 0) or 0),
                ))
                source_counts["coingecko"] += 1
    except Exception:
        pass

    # DexScreener boosted tokens
    try:
        boosts = await blockchain.get_token_boosts()
        for b in boosts[:10]:
            sym = b.get("symbol", "")
            if sym:
                all_tokens.append(TokenOnChain(
                    address=b.get("tokenAddress", ""),
                    name=b.get("name", ""),
                    symbol=sym,
                    chain=b.get("chainId", "eth"),
                ))
                source_counts["dexscreener"] += 1
    except Exception:
        pass

    await blockchain.close()
    await market.close()

    # Deduplicate (prefer tokens with more data)
    seen = set()
    unique = []
    for t in sorted(all_tokens, key=lambda x: x.volume_24h + x.liquidity_usd, reverse=True):
        key = f"{t.chain}:{t.symbol}"
        if key not in seen and t.symbol:
            seen.add(key)
            unique.append(t)

    # ── Phase 3: Display discovered tokens ──────────────────────────
    print()
    src_info = f"GeckoTerminal:{source_counts['geckoterminal']} CoinGecko:{source_counts['coingecko']} DexScreener:{source_counts['dexscreener']}"
    print(box(f"MARKET SCAN: {len(unique)} TOKENS DISCOVERED", [
        f"  Sources: {DIM}{src_info}{RESET}",
        "",
    ]))

    if unique:
        # Group by chain
        by_chain: dict[str, list[TokenOnChain]] = {}
        for t in unique:
            by_chain.setdefault(t.chain, []).append(t)

        for chain in settings.chains:
            tokens = by_chain.get(chain, [])
            if not tokens:
                continue

            print(f"  {chain_label(chain)} — {len(tokens)} tokens")
            print(f"  {'─'*56}")

            # Show top tokens with data
            shown = 0
            for t in tokens[:8]:
                sym = t.symbol or "???"
                name = (t.name[:20] + "...") if len(t.name) > 20 else t.name
                price = price_fmt(t.price_usd)
                vol = money(t.volume_24h) if t.volume_24h else "—"
                liq = money(t.liquidity_usd) if t.liquidity_usd else "—"
                chg = change_fmt(t.price_change_24h) if t.price_change_24h else "—"
                mcap = money(t.market_cap_usd) if t.market_cap_usd else "—"

                print(f"    {BOLD}{sym:<8}{RESET} {DIM}{name:<22}{RESET} "
                      f"Price:{price:>12}  24h:{chg:>8}  Vol:{vol:>8}  Liq:{liq:>8}")
                shown += 1

            if len(tokens) > 8:
                print(f"    {DIM}... and {len(tokens)-8} more{RESET}")
            print()

    # ── Phase 4: Quick rug scan on tokens with data ─────────────────
    print(box("INTELLIGENCE ANALYSIS", [""]))

    rug_engine = RugProbabilityEngine()
    scanner = MarketScanner()

    # Analyze tokens that have real data
    tokens_with_data = [t for t in unique if t.volume_24h > 0 or t.liquidity_usd > 0][:15]

    opportunities = []
    risks = []

    if tokens_with_data:
        print(DIM + "  Running rug check + pump analysis on discovered tokens..." + RESET)
        print()

        for t in tokens_with_data:
            sym = t.symbol or t.address[:8]

            # Rug check (using available data, no additional API call needed)
            rug = rug_engine.calculate(
                token_address=t.address,
                token_symbol=sym,
                chain=t.chain,
                liquidity_locked=t.liquidity_locked,
                dev_supply_pct=0,  # would need holder analysis
            )

            # Quick pump assessment from price/volume data
            if t.price_change_24h > 15 and t.volume_24h > 10000:
                opportunities.append((t, rug, f"Strong momentum +{t.price_change_24h:.0f}%"))
            elif t.price_change_24h < -15 and t.volume_24h > 10000:
                risks.append((t, rug, f"Dumping {t.price_change_24h:.0f}%"))

            if rug.rug_probability > 50:
                risks.append((t, rug, f"Rug risk {rug.rug_probability:.0f}%"))

        # Show opportunities
        if opportunities:
            print(f"  {c(GREEN, BOLD + '🚀 OPPORTUNITIES' + RESET)}")
            print(f"  {'─'*56}")
            for t, rug, reason in opportunities[:5]:
                sym = t.symbol or "???"
                print(f"    {BOLD}{sym:<10}{RESET} on {chain_label(t.chain)}  "
                      f"{change_fmt(t.price_change_24h)}  "
                      f"Vol:{money(t.volume_24h)}  "
                      f"Liq:{money(t.liquidity_usd)}")
                print(f"    {'':10} {c(GREEN, reason)}  Rug: {pct_bar(rug.rug_probability, width=10)}")
            print()

        # Show risks
        if risks:
            print(f"  {c(RED, BOLD + '🚨 RISKS' + RESET)}")
            print(f"  {'─'*56}")
            seen_risk = set()
            for t, rug, reason in risks[:5]:
                sym = t.symbol or "???"
                if sym in seen_risk:
                    continue
                seen_risk.add(sym)
                print(f"    {BOLD}{sym:<10}{RESET} on {chain_label(t.chain)}  "
                      f"{change_fmt(t.price_change_24h)}  "
                      f"Vol:{money(t.volume_24h)}  "
                      f"Liq:{money(t.liquidity_usd)}")
                print(f"    {'':10} {c(RED, reason)}")
            print()

        if not opportunities and not risks:
            print(f"  {DIM}No high-confidence signals detected in this scan.{RESET}")
            print(f"  {DIM}Run 'opencode monitor' for continuous monitoring.{RESET}")
            print()

    else:
        print(f"  {DIM}Limited data from APIs in this cycle. Try 'opencode scan-market' for deep scan.{RESET}")
        print()

    # ── Phase 5: Summary footer ─────────────────────────────────────
    now = datetime.now(timezone.utc)
    pred_engine = PredictionEngine()
    accuracy = pred_engine.get_accuracy()

    print(box("SESSION SUMMARY", [
        "",
        f"  Tokens discovered:  {len(unique)}",
        f"  Tokens with data:   {len(tokens_with_data)}",
        f"  Opportunities:      {c(GREEN, str(len(opportunities)))}",
        f"  Risks:              {c(RED, str(len(risks)))}",
        f"  Time window:        {w.emoji} {w.name} ({w.risk_score:.0f}% risk)",
        f"  Predictions logged: {accuracy['total_predictions']} (accuracy: {accuracy['accuracy']})",
        f"  UTC:                {now.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]))

    print()
    print(BOLD + "  COMMANDS:" + RESET)
    print(f"    {c(CYAN, 'scan-market')}     Full deep scan of all discovered tokens")
    print(f"    {c(CYAN, 'monitor')}         Start 24/7 autonomous monitoring")
    print(f"    {c(CYAN, 'scan --token X')}  Deep scan a specific token")
    print(f"    {c(CYAN, 'rug-check')}       Check rug probability")
    print(f"    {c(CYAN, 'danger-window')}   Time risk analysis")
    print(f"    {c(CYAN, 'status')}          System health check")
    print(f"    {c(CYAN, 'how')}             Show how THE EYE works")
    print(f"    {c(CYAN, 'quit')}            Exit")
    print()


# ── CLI Commands ─────────────────────────────────────────────────────

async def cmd_scan(args):
    """Deep scan a specific token."""
    show_banner()
    print(f"  {BOLD}Deep Scanning: {args.token}{RESET}")
    print(f"  Address: {args.address}")
    print(f"  Chain: {chain_label(args.chain)}")
    print()

    scanner = MarketScanner()
    try:
        result = await scanner.scan_token(args.address, args.chain, args.token)
        token = result.token

        lines = [
            "",
            f"  Name:     {token.name or 'Unknown'}",
            f"  Symbol:   {token.symbol or '???'}",
            f"  Chain:    {chain_label(token.chain)}",
            f"  Address:  {token.address}",
            f"  Price:    {price_fmt(token.price_usd)}",
        ]
        if result.market_data:
            md = result.market_data
            lines += [
                f"  24h:      {change_fmt(md.price_change_24h)}",
                f"  Volume:   {money(md.volume_24h)}",
                f"  Liquidity:{money(md.liquidity_usd)}",
                f"  Mcap:     {money(md.market_cap_usd)}",
                f"  Buys/Sells: {md.buys_24h}/{md.sells_24h} ({md.buy_sell_ratio:.2f}x)",
            ]

        print(box("TOKEN DATA", lines))

        if result.rug_result:
            rug = result.rug_result
            print(box("RUG CHECK", [
                "",
                f"  Probability: {pct_bar(rug.rug_probability)}",
                f"  Risk Level:  {risk_label(rug.risk_level)}",
                f"  Confidence:  {rug.confidence:.0f}%",
                "",
                *([f"  • {i}" for i in rug.indicators[:5]] if rug.indicators else [f"  {DIM}No indicators triggered{RESET}"]),
                *([f"  • {d}" for d in rug.dev_flags[:5]] if rug.dev_flags else []),
                "",
            ]))

        if result.pump_result:
            pump = result.pump_result
            print(box("PUMP ANALYSIS", [
                "",
                f"  Moon Score:   {pct_bar(pump.moon_score)}",
                f"  Fake Score:   {pct_bar(pump.fake_pump_score)}",
                f"  Verdict:      {pump.verdict.replace('_', ' ').upper()}",
                f"  Confidence:   {pump.confidence:.0f}%",
                "",
                *([f"  • {e}" for e in pump.evidence[:5]] if pump.evidence else []),
                "",
            ]))

        if result.prediction:
            pred = result.prediction
            print(box("PREDICTION", [
                "",
                f"  Type:       {BOLD}{pred.prediction_type.value.replace('_', ' ').upper()}{RESET}",
                f"  Direction:  {pred.direction}  |  Timing: {pred.timing}  |  Size: {pred.magnitude}",
                f"  Confidence: {pred.confidence:.0f}%  |  Urgency: {pred.urgency}",
                f"  Risk/Reward: {pred.risk_reward:.1f}x",
                "",
                *([f"  • {r}" for r in pred.reasoning[:5]] if pred.reasoning else []),
                "",
            ]))

    finally:
        await scanner.close()


async def cmd_scan_market(args):
    """Full market-wide scan with all analysis pipelines."""
    show_banner()
    print(f"  {BOLD}Running full market scan...{RESET}")
    print()

    scanner = MarketScanner()
    try:
        result = await scanner.scan_market()

        temporal = result.temporal
        if temporal:
            w = temporal.current_window
            print(box("TIME WINDOW", [
                "", f"  {w.emoji} {w.name} — Risk: {pct_bar(w.risk_score)}", "",
            ]))

        print(box(f"SCAN RESULTS — {result.tokens_scanned} TOKENS ANALYZED", [
            "",
            f"  Discovered:    {result.tokens_discovered}",
            f"  Analyzed:      {result.tokens_scanned}",
            f"  Opportunities: {c(GREEN, str(len(result.opportunities)))}",
            f"  Risks:         {c(RED, str(len(result.risks)))}",
            f"  New launches:  {len(result.new_launches)}",
            f"  Rug alerts:    {c(RED, str(len(result.rug_alerts)))}",
            f"  Pump alerts:   {c(GREEN, str(len(result.pump_alerts)))}",
            f"  Duration:      {result.scan_duration_sec:.1f}s",
            "",
        ]))

        if result.opportunities:
            print(f"  {BOLD}{c(GREEN, '🚀 OPPORTUNITIES')}{RESET}")
            for opp in result.opportunities[:10]:
                t = opp.token
                sym = t.symbol or t.address[:8]
                conf = opp.prediction.confidence if opp.prediction else 0
                ptype = opp.prediction.prediction_type.value if opp.prediction else "—"
                print(f"    {BOLD}{sym:<10}{RESET} {chain_label(t.chain)}  "
                      f"Conf:{conf:.0f}%  {ptype}")
            print()

        if result.risks:
            print(f"  {BOLD}{c(RED, '🚨 RISKS')}{RESET}")
            for risk in result.risks[:10]:
                t = risk.token
                sym = t.symbol or t.address[:8]
                rug_pct = risk.rug_result.rug_probability if risk.rug_result else 0
                print(f"    {BOLD}{sym:<10}{RESET} {chain_label(t.chain)}  "
                      f"Rug:{rug_pct:.0f}%  {risk_label(risk.rug_result.risk_level if risk.rug_result else 'unknown')}")
            print()

    finally:
        await scanner.close()


async def cmd_rug_check(args):
    """Check rug probability."""
    show_banner()
    rug_engine = RugProbabilityEngine()
    result = rug_engine.calculate(
        token_address=args.address,
        token_symbol=getattr(args, 'token', ''),
        chain=args.chain,
    )
    print(box("RUG CHECK", [
        "",
        f"  Token:       {args.address[:20]}...",
        f"  Chain:       {chain_label(args.chain)}",
        f"  Probability: {pct_bar(result.rug_probability)}",
        f"  Risk Level:  {risk_label(result.risk_level)}",
        f"  Confidence:  {result.confidence:.0f}%",
        "",
        *([f"  • {i}" for i in result.indicators] if result.indicators else ["  No indicators"]),
        *([f"  • {d}" for d in result.dev_flags] if result.dev_flags else []),
        "",
    ]))


async def cmd_pump_scan(args):
    """Detect fake/organic pump."""
    show_banner()
    scanner = MarketScanner()
    try:
        result = await scanner.scan_token(args.address, args.chain, getattr(args, 'token', ''))
        if result.pump_result:
            pump = result.pump_result
            print(box("PUMP SCAN", [
                "",
                f"  Moon Score:   {pct_bar(pump.moon_score)}",
                f"  Fake Score:   {pct_bar(pump.fake_pump_score)}",
                f"  Verdict:      {BOLD}{pump.verdict.replace('_', ' ').upper()}{RESET}",
                f"  Confidence:   {pump.confidence:.0f}%",
                "",
                *([f"  • {e}" for e in pump.evidence[:8]] if pump.evidence else []),
                "",
            ]))
        else:
            print("  Insufficient data for pump analysis.")
    finally:
        await scanner.close()


async def cmd_whale_watch(args):
    """Track a whale wallet."""
    show_banner()
    matcher = WhaleMatcher()
    results = matcher.analyze_wallet(args.wallet, args.chain)
    if results:
        lines = ["", f"  Wallet: {args.wallet[:16]}...", f"  Chain:  {chain_label(args.chain)}", ""]
        for r in results:
            impact_color = GREEN if r.impact == "bullish" else RED if r.impact in ("bearish", "dangerous") else YELLOW
            lines += [
                f"  Pattern:     {BOLD}{r.pattern.value.replace('_', ' ').upper()}{RESET}",
                f"  Confidence:  {r.confidence:.0f}%",
                f"  Impact:      {c(impact_color, r.impact.upper())}",
                f"  Description: {r.description}",
                "",
            ]
        print(box("WHALE ANALYSIS", lines))
    else:
        print(f"  No known patterns for {args.wallet[:16]}...")
        print(f"  Wallet will be tracked — patterns develop over time.")


async def cmd_danger_window(args):
    """Show current time risk level."""
    show_banner()
    analyzer = TemporalAnalyzer()
    result = analyzer.analyze()
    w = result.current_window

    lines = [
        "",
        f"  {w.emoji} {BOLD}{w.name}{RESET}",
        f"  UTC: {result.utc_hour:.1f}h  |  Window: {w.start_hour}:00-{w.end_hour}:00 UTC",
        f"  Risk: {pct_bar(w.risk_score)}  |  Level: {risk_label(w.risk_level)}",
        "",
        f"  {w.description}",
        "",
        f"  {result.recommendation}",
        "",
    ]
    print(box("DANGER WINDOW", lines))

    print(f"\n  {BOLD}ALL TIME WINDOWS:{RESET}")
    for win in result.all_windows:
        current = " ◀ NOW" if win.name == w.name else ""
        print(f"    {win.emoji} {win.name:<16} {win.start_hour}:00-{win.end_hour}:00 UTC  "
              f"Risk: {win.risk_score:.0f}%  {risk_label(win.risk_level)}{current}")


async def cmd_monitor(args):
    """Start 24/7 market monitoring."""
    show_banner()
    interval = args.interval or settings.get("monitor.default_interval_sec", 60)
    scanner = MarketScanner()
    formatter = AlertFormatter()
    dispatcher = Dispatcher()

    print(f"  {BOLD}24/7 Market Monitor Active{RESET}")
    print(f"  Scanning every {interval}s across {len(settings.chains)} chains")
    print(f"  Press Ctrl+C to stop\n")

    try:
        cycle = 0
        while True:
            cycle += 1
            now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
            print(f"\n  {'─'*56}")
            print(f"  CYCLE {cycle} — {now}")
            print(f"  {'─'*56}")

            try:
                result = await scanner.scan_market()
                scanner._display_summary(result)
                alerts = formatter.format_market_alerts(result)
                if alerts:
                    await dispatcher.dispatch(alerts, terminal=True)
            except Exception as e:
                print(f"  {c(RED, f'Error: {e}')}")

            await asyncio.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n\n  {BOLD}🐋👁️  THE EYE stopping. Goodbye!{RESET}")
    finally:
        await scanner.close()
        await dispatcher.close()


async def cmd_add_watchlist(args):
    scanner = MarketScanner()
    scanner.add_watchlist(args.token, args.address, args.chain, args.interval)
    print(f"  ✅ Added {BOLD}{args.token}{RESET} to watchlist (every {args.interval}s)")


async def cmd_remove_watchlist(args):
    scanner = MarketScanner()
    scanner.remove_watchlist(args.token)
    print(f"  ✅ Removed {args.token} from watchlist")


async def cmd_list_watchlist(args):
    show_banner()
    scanner = MarketScanner()
    wl = scanner.list_watchlist()
    if wl:
        for token, data in wl.items():
            print(f"  {BOLD}{token:<10}{RESET} {data['address'][:16]}... {chain_label(data['chain'])} every {data['interval']}s")
    else:
        print("  No tokens in watchlist.")


async def cmd_status(args):
    """System health check."""
    show_banner()
    pred_engine = PredictionEngine()
    accuracy = pred_engine.get_accuracy()
    temporal = TemporalAnalyzer().analyze()
    w = temporal.current_window

    data_dir = PROJECT_ROOT / "src" / "data"
    db_files = list(data_dir.glob("*.json"))

    print(box("SYSTEM STATUS", [
        "",
        f"  Version:       v{VERSION}",
        f"  Chains:        {' '.join(chain_label(c) for c in settings.chains)}",
        f"  Scan interval: {settings.scan_interval}s",
        f"  Min confidence:{settings.min_confidence}%",
        f"  Time window:   {w.emoji} {w.name} ({w.risk_score:.0f}% risk)",
        "",
        f"  {BOLD}Prediction Engine:{RESET}",
        f"    Total:      {accuracy['total_predictions']}",
        f"    Confirmed:  {accuracy['confirmed']}",
        f"    Accuracy:   {accuracy['accuracy']}",
        "",
        f"  {BOLD}Database Files:{RESET}",
        *[f"    {f.name}: {f.stat().st_size:,} bytes" for f in db_files[:6]],
        "",
    ]))


async def cmd_dispatch_alerts(args):
    show_banner()
    dispatcher = Dispatcher()
    try:
        await dispatcher.dispatch_queued()
    finally:
        await dispatcher.close()


async def cmd_backtest(args):
    show_banner()
    engine = PredictionEngine()
    accuracy = engine.get_accuracy()
    print(box(f"BACKTEST — {args.days} DAYS", [
        "",
        f"  Total:     {accuracy['total_predictions']}",
        f"  Confirmed: {accuracy['confirmed']}",
        f"  Rejected:  {accuracy['rejected']}",
        f"  Pending:   {accuracy['pending']}",
        f"  Accuracy:  {accuracy['accuracy']}",
        "",
    ]))

    cutoff = time.time() - (args.days * 86400)
    recent = [e for e in engine.log if e.predicted_at >= cutoff]
    if recent:
        print(f"  {BOLD}Recent predictions:{RESET}")
        for entry in recent[-15:]:
            age = (time.time() - entry.predicted_at) / 86400
            outcome_color = GREEN if entry.outcome == "confirmed" else RED if entry.outcome == "rejected" else YELLOW
            print(f"    {entry.token_symbol:<10} {entry.prediction_type:<20} → "
                  f"{c(outcome_color, entry.outcome)} ({entry.confidence:.0f}%, {age:.1f}d ago)")


# ── Interactive Mode ─────────────────────────────────────────────────

async def interactive_mode():
    """When you just type `opencode` — show the live dashboard, then drop into interactive."""
    # First, show the live dashboard
    await show_live_dashboard()

    # Then drop into interactive prompt
    scanner = MarketScanner()
    formatter = AlertFormatter()
    dispatcher = Dispatcher()

    try:
        while True:
            try:
                cmd = input(c(CYAN, BOLD + "  🐋👁️ > " + RESET)).strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n  {BOLD}Goodbye!{RESET}")
                break

            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0].lower()

            if action in ("quit", "exit", "q"):
                print(f"  {BOLD}🐋👁️  Goodbye!{RESET}")
                break
            elif action == "how":
                show_how_it_works()
            elif action == "scan":
                if len(parts) >= 3:
                    await cmd_scan(argparse.Namespace(token=parts[1], address=parts[2], chain=parts[3] if len(parts) > 3 else "eth"))
                elif len(parts) == 2:
                    await cmd_scan(argparse.Namespace(token=parts[1], address=parts[1], chain="eth"))
                else:
                    print("  Usage: scan <symbol> <address> [chain]")
            elif action == "scan-market":
                await cmd_scan_market(argparse.Namespace())
            elif action in ("danger-window", "dw"):
                await cmd_danger_window(argparse.Namespace())
            elif action == "status":
                await cmd_status(argparse.Namespace())
            elif action == "monitor":
                await cmd_monitor(argparse.Namespace(interval=60))
            elif action == "help":
                show_how_it_works()
                print(BOLD + "  COMMANDS:" + RESET)
                print(f"    how             Show how THE EYE works")
                print(f"    scan-market     Full market scan")
                print(f"    scan <addr>     Scan a token")
                print(f"    monitor         24/7 monitoring")
                print(f"    danger-window   Time risk level")
                print(f"    status          System health")
                print(f"    quit            Exit")
            else:
                print(f"  Unknown: {action}. Type {c(CYAN, 'help')} for commands.")
    finally:
        await scanner.close()
        await dispatcher.close()


# ── CLI Parser ──────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opencode",
        description="🐋👁️ THE EYE — Memecoin Market Intelligence Engine",
    )
    parser.add_argument("--version", action="version", version=f"THE EYE v{VERSION}")

    sub = parser.add_subparsers(dest="command", help="Command")

    p = sub.add_parser("scan", help="Deep scan a token")
    p.add_argument("--token", required=True)
    p.add_argument("--address", required=True)
    p.add_argument("--chain", default="eth")

    sub.add_parser("scan-market", help="Full market-wide scan")

    p = sub.add_parser("rug-check", help="Check rug probability")
    p.add_argument("--address", required=True)
    p.add_argument("--token", default="")
    p.add_argument("--chain", default="eth")

    p = sub.add_parser("pump-scan", help="Detect fake/organic pump")
    p.add_argument("--address", required=True)
    p.add_argument("--token", default="")
    p.add_argument("--chain", default="eth")

    p = sub.add_parser("whale-watch", help="Track a whale wallet")
    p.add_argument("--wallet", required=True)
    p.add_argument("--chain", default="eth")

    sub.add_parser("danger-window", help="Current time risk level")

    p = sub.add_parser("monitor", help="Start 24/7 monitoring")
    p.add_argument("--interval", type=int, default=None)

    p = sub.add_parser("add-watchlist", help="Add token to watchlist")
    p.add_argument("--token", required=True)
    p.add_argument("--address", required=True)
    p.add_argument("--chain", default="eth")
    p.add_argument("--interval", type=int, default=15)

    p = sub.add_parser("remove-watchlist", help="Remove from watchlist")
    p.add_argument("--token", required=True)

    sub.add_parser("list-watchlist", help="Show watchlist")
    sub.add_parser("status", help="System health check")
    sub.add_parser("dispatch-alerts", help="Send queued alerts")

    p = sub.add_parser("backtest", help="Check prediction accuracy")
    p.add_argument("--days", type=int, default=30)

    return parser


COMMAND_MAP = {
    "scan": cmd_scan,
    "scan-market": cmd_scan_market,
    "rug-check": cmd_rug_check,
    "pump-scan": cmd_pump_scan,
    "whale-watch": cmd_whale_watch,
    "danger-window": cmd_danger_window,
    "monitor": cmd_monitor,
    "add-watchlist": cmd_add_watchlist,
    "remove-watchlist": cmd_remove_watchlist,
    "list-watchlist": cmd_list_watchlist,
    "status": cmd_status,
    "dispatch-alerts": cmd_dispatch_alerts,
    "backtest": cmd_backtest,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        asyncio.run(interactive_mode())
        return

    handler = COMMAND_MAP.get(args.command)
    if handler:
        asyncio.run(handler(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

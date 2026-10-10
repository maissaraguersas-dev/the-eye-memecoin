#!/usr/bin/env python3
"""
THE EYE — Memecoin Pattern Recognition System
CLI Entry Point

Production-grade command-line interface that ties together ALL modules:
  - Monitors:  Blockchain, Social, Market
  - Pattern:   WhaleMatcher, DevMatcher, TemporalAnalyzer, ManipulationDetector
  - Analysis:  RugProbability, Confidence, Prediction, PumpScorer
  - Alerts:    Formatter, Dispatcher
  - Autonomous: CronScheduler, WatchlistManager, StateManager, AlertQueue

Subcommands:
    scan             Full analysis of a token
    whale-watch      Track a specific whale wallet
    rug-check        Rug pull probability check
    pump-scan        Detect fake pump
    danger-window    Temporal risk scan
    add-watchlist    Add token to 24/7 monitoring
    remove-watchlist Remove token from monitoring
    list-watchlist   Show monitored tokens
    status           Show system health and last scans
    monitor          Start 24/7 continuous monitoring
    dispatch-alerts  Flush pending alert queue
    backtest         Evaluate prediction accuracy
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import signal
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Constants ──────────────────────────────────────────────────────────────

VERSION = "1.0.0"
DATA_DIR = Path(__file__).parent / "data"

# ANSI color codes
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

URGENCY_COLORS = {
    "CRITICAL": Colors.RED + Colors.BOLD,
    "HIGH": Colors.YELLOW + Colors.BOLD,
    "MEDIUM": Colors.BLUE,
    "LOW": Colors.GREEN,
}

# ─── Lazy imports (avoid heavy init at import time) ─────────────────────────

_loggers_setup = False


def setup_logging(verbose: bool = False) -> None:
    """Configure root logging for the CLI."""
    global _loggers_setup
    if _loggers_setup:
        return
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )
    _loggers_setup = True


def _color(text: str, color: str) -> str:
    """Apply ANSI color to text if stdout is a TTY."""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.RESET}"
    return text


def _urgency_color(text: str, urgency: str) -> str:
    """Color text based on urgency level."""
    return _color(text, URGENCY_COLORS.get(urgency, Colors.RESET))


def _banner() -> str:
    """Return the THE EYE ASCII banner."""
    return _color(
        r"""
  _____ _   _ _____   ___  ___  ___ _____
 |_   _| | | /  ___| / _ \ |  \/  |/  ___|
   | | | |_| \ `--. / /_\ \| .  . |\ `--.
   | | |  _  |`--. \|  _  || |\/| | `--. \
   | | | | | /\__/ /| | | || |  | |/\__/ /
   \_/ \_| |_|____/ \_| |_/\_|  |_/\____/

  Memecoin Pattern Recognition System v""" + VERSION,
        Colors.CYAN + Colors.BOLD,
    )


def _section(title: str) -> str:
    """Return a section header line."""
    line = "─" * 60
    return f"\n{line}\n  {title}\n{line}"


def _print_result(result: Any, json_output: bool = False) -> None:
    """Print a result object in text or JSON format."""
    if json_output:
        if hasattr(result, "to_dict"):
            data = result.to_dict()
        elif hasattr(result, "__dataclass_fields__"):
            data = asdict(result)
        else:
            data = result
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    else:
        print(result)


# ─── Module Initializers ────────────────────────────────────────────────────

def _init_blockchain():
    from src.monitors.blockchain import BlockchainMonitor
    return BlockchainMonitor()


def _init_social():
    from src.monitors.social import SocialScanner
    return SocialScanner()


def _init_market():
    from src.monitors.market import MarketFeed
    return MarketFeed()


def _init_whale_matcher():
    from src.pattern.whale_matcher import WhaleMatcher
    return WhaleMatcher()


def _init_dev_matcher():
    from src.pattern.dev_matcher import DevMatcher
    return DevMatcher()


def _init_temporal():
    from src.pattern.temporal_analyzer import TemporalAnalyzer
    return TemporalAnalyzer()


def _init_manipulation():
    from src.pattern.manipulation_detector import ManipulationDetector
    return ManipulationDetector()


def _init_rug_engine():
    from src.analysis.rug_probability import RugProbabilityEngine
    dev_matcher = _init_dev_matcher()
    whale_matcher = _init_whale_matcher()
    return RugProbabilityEngine(dev_matcher=dev_matcher, whale_matcher=whale_matcher)


def _init_confidence():
    from src.analysis.confidence import ConfidenceEngine
    return ConfidenceEngine()


def _init_prediction():
    from src.analysis.prediction import PredictionGenerator
    return PredictionGenerator()


def _init_pump_scorer():
    from src.analysis.pump_scorer import PumpScorer
    manipulation = _init_manipulation()
    return PumpScorer(manipulation_detector=manipulation)


def _init_alert_formatter():
    from src.alerts.formatter import AlertFormatter
    return AlertFormatter()


def _init_dispatcher():
    from src.alerts.dispatcher import AlertDispatcher
    return AlertDispatcher()


def _init_state_manager():
    from src.autonomous.state_manager import StateManager
    return StateManager()


def _init_watchlist(state_manager=None):
    from src.autonomous.watchlist_manager import WatchlistManager
    sm = state_manager or _init_state_manager()
    watchlist_path = str(DATA_DIR / "watchlist.json")
    return WatchlistManager(watchlist_path=watchlist_path, state_manager=sm)


def _init_alert_queue():
    from src.autonomous.alert_queue import AlertQueue
    queue_path = str(DATA_DIR / "alert_queue.json")
    return AlertQueue(queue_path=queue_path)


def _init_scheduler():
    from src.autonomous.cron_scheduler import CronScheduler
    return CronScheduler()


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: scan
# ═══════════════════════════════════════════════════════════════════════════

def cmd_scan(args: argparse.Namespace) -> int:
    """Full analysis of a token: blockchain → social → market → patterns → analysis → alert."""
    logger = logging.getLogger("the-eye.scan")
    token = args.token
    address = args.address or ""
    chain = args.chain

    print(_banner())
    print(_section(f"FULL SCAN: {token}"))
    if address:
        print(f"  Address : {address}")
    print(f"  Chain   : {chain}")
    print(f"  Time    : {datetime.now(timezone.utc).isoformat()}")

    try:
        # 1. Blockchain Monitor
        print(_section("1/7 — Blockchain Monitor"))
        blockchain = _init_blockchain()
        if address:
            on_chain = blockchain.analyze_token(address, chain=chain)
            print(f"  Token Name       : {on_chain.token_name or 'N/A'}")
            print(f"  Data Source      : {on_chain.data_source or 'N/A'}")
            print(f"  Liquidity (USD)  : ${on_chain.liquidity_usd:,.2f}")
            print(f"  Holders          : {on_chain.holder_count}")
            print(f"  Contract Verified: {on_chain.contract_verified}")
            print(f"  Dev Holds %      : {on_chain.dev_holds_pct:.2f}%")
        else:
            on_chain = None
            print("  No address provided — skipping on-chain analysis")

        # 2. Social Scanner
        print(_section("2/7 — Social Scanner"))
        social = _init_social()
        social_signals = social.analyze_social_signals(token)
        print(f"  Twitter (24h)    : {social_signals.twitter_mentions_24h}")
        print(f"  Twitter Bot Ratio: {social_signals.twitter_bot_ratio:.2f}")
        print(f"  Reddit (24h)     : {social_signals.reddit_mentions_24h}")
        print(f"  TikTok (24h)     : {social_signals.tiktok_videos_24h}")
        print(f"  Sentiment        : {_urgency_color(social_signals.overall_sentiment, 'HIGH' if social_signals.overall_sentiment == 'artificial' else 'LOW')}")
        print(f"  Viral Potential  : {social_signals.viral_potential_score:.1f}/100")

        # 3. Market Feed
        print(_section("3/7 — Market Feed"))
        market = _init_market()
        market_data = market.get_market_data(token, token_address=address, chain=chain)
        print(f"  Price (USD)      : ${market_data.price_usd:.8f}" if market_data.price_usd < 1 else f"  Price (USD)      : ${market_data.price_usd:,.2f}")
        print(f"  Price Change 24h : {market_data.price_change_24h:+.2f}%")
        print(f"  Volume 24h (USD) : ${market_data.volume_24h_usd:,.2f}")
        print(f"  MCap (USD)       : ${market_data.market_cap_usd:,.2f}")
        print(f"  Liquidity (USD)  : ${market_data.liquidity_usd:,.2f}")
        print(f"  Buy/Sell Ratio   : {market_data.buy_sell_ratio:.2f}")
        print(f"  Data Source      : {market_data.data_source or 'N/A'}")

        # 4. Whale Matcher
        print(_section("4/7 — Pattern Matchers"))
        whale_matcher = _init_whale_matcher()
        if on_chain and on_chain.top_holders:
            top_holder = on_chain.top_holders[0]
            wallet = top_holder.get("wallet", "")
            whale_match = whale_matcher.match_wallet(
                wallet_address=wallet,
                wallet_txs=[],
                wallet_age_days=on_chain.deployer_wallet_age_days,
            )
            print(f"  Whale Match      : {whale_match.matched_label or 'No known whale'}")
            print(f"  Patterns         : {', '.join(whale_match.matched_patterns) or 'None'}")
            print(f"  Confidence       : {whale_match.confidence:.1f}/100")
            print(f"  Risk Level       : {_urgency_color(whale_match.risk_level, whale_match.risk_level.upper())}")
        else:
            whale_match = None
            print("  No on-chain data — whale matching skipped")

        # 5. Dev Matcher + Rug Probability
        print(_section("5/7 — Rug Probability Engine"))
        dev_matcher = _init_dev_matcher()
        dev_address = on_chain.deployer if on_chain and on_chain.deployer else address
        if dev_address:
            dev_match = dev_matcher.analyze_dev(
                dev_address=dev_address,
                chain=chain,
                liquidity_locked=on_chain.liquidity_locked if on_chain else False,
                liquidity_lock_days=on_chain.liquidity_lock_duration_days if on_chain else 0,
                dev_holds_pct=on_chain.dev_holds_pct if on_chain else 0,
                dev_wallet_age_days=on_chain.deployer_wallet_age_days if on_chain else 999,
                social_bot_pct=social_signals.twitter_bot_ratio * 100,
            )
            print(f"  Rug Probability  : {_urgency_color(f'{dev_match.rug_probability:.1f}%', dev_match.urgency)}")
            print(f"  Rug Type         : {dev_match.rug_type or 'None detected'}")
            print(f"  Urgency          : {_urgency_color(dev_match.urgency, dev_match.urgency)}")
            print(f"  Indicators       : {', '.join(dev_match.indicators_matched) or 'None'}")
            if dev_match.evidence:
                for ev in dev_match.evidence[:5]:
                    print(f"    • {ev}")
        else:
            dev_match = None
            print("  No dev address — rug analysis skipped")

        # 6. Manipulation Detector + Pump Scorer
        print(_section("6/7 — Pump / Manipulation Analysis"))
        pump_scorer = _init_pump_scorer()
        social_dict = {
            "tiktok_organic_videos": social_signals.tiktok_videos_24h,
            "reddit_organic_posts": social_signals.reddit_mentions_24h,
            "twitter_organic_mentions": int(social_signals.twitter_mentions_24h * (1 - social_signals.twitter_bot_ratio)),
            "twitter_total_mentions": social_signals.twitter_mentions_24h,
            "twitter_bot_ratio": social_signals.twitter_bot_ratio,
            "telegram_new_members_day": social_signals.telegram_growth_24h,
            "social_bot_pct": social_signals.twitter_bot_ratio * 100,
        }
        market_dict = {
            "price_change_24h_pct": market_data.price_change_24h,
            "volume_24h": market_data.volume_24h_usd,
            "market_cap": market_data.market_cap_usd,
            "liquidity_usd": market_data.liquidity_usd,
            "buy_sell_ratio": market_data.buy_sell_ratio,
            "real_volume_pct": 100.0,
        }
        on_chain_dict = {
            "holder_count": on_chain.holder_count if on_chain else 0,
            "top_10_holders_pct": on_chain.dev_holds_pct if on_chain else 0,
        }
        pump_result = pump_scorer.score(
            token=token,
            social_signals=social_dict,
            market_data=market_dict,
            on_chain_data=on_chain_dict,
            holders=on_chain.top_holders if on_chain else [],
        )
        print(f"  Moon Probability : {_color(f'{pump_result.moon_probability:.1f}%', Colors.GREEN if pump_result.moon_probability > 50 else Colors.YELLOW)}")
        print(f"  Viral Score      : {pump_result.viral_score:.1f}/100")
        print(f"  Is Organic       : {_color(str(pump_result.is_organic), Colors.GREEN if pump_result.is_organic else Colors.RED)}")
        print(f"  Is Fake Pump     : {_color(str(pump_result.is_fake_pump), Colors.RED if pump_result.is_fake_pump else Colors.GREEN)}")
        print(f"  Social Score     : {pump_result.social_score:.1f}")
        print(f"  On-Chain Score   : {pump_result.on_chain_score:.1f}")
        print(f"  Timing Score     : {pump_result.timing_score:.1f}")
        if pump_result.evidence:
            for ev in pump_result.evidence[:5]:
                print(f"    • {ev}")
        print(f"  Recommendation   : {pump_result.recommended_action}")

        # 7. Alert Formatter
        print(_section("7/7 — Alert Output"))
        formatter = _init_alert_formatter()

        # Build a composite alert from the strongest signal
        if dev_match and dev_match.rug_probability >= 40:
            alert = formatter.format_rug_alert(
                dev_match={
                    "developer": dev_match.dev_address,
                    "risk_flags": dev_match.indicators_matched,
                    "risk_score": dev_match.rug_probability,
                    "evidence": "; ".join(dev_match.evidence[:3]),
                    "confidence": int(dev_match.confidence),
                    "agents": ["dev-matcher", "rug-probability"],
                },
                token=token,
                chain=chain,
            )
        elif whale_match and whale_match.confidence >= 60:
            alert = formatter.format_whale_alert(
                whale_match={
                    "wallet": whale_match.wallet_address,
                    "amount_usd": 0,
                    "direction": "buy",
                    "tx_hash": "",
                    "confidence": int(whale_match.confidence),
                    "agents": ["whale-matcher"],
                },
                token=token,
                chain=chain,
            )
        else:
            alert = formatter.format_pump_alert(
                manipulation_result={
                    "pattern": "pump_scorer",
                    "wallets": [],
                    "volume_usd": market_data.volume_24h_usd,
                    "confidence": int(pump_result.moon_probability),
                    "agents": ["pump-scorer", "social-scanner", "market-feed"],
                },
                token=token,
                chain=chain,
            )

        if args.json:
            print(formatter.to_json(alert))
        else:
            print(formatter.to_text(alert))

        # Enqueue the alert
        try:
            alert_queue = _init_alert_queue()
            alert_queue.enqueue(alert)
            logger.info("Alert enqueued: %s", alert.id)
        except Exception as e:
            logger.warning("Failed to enqueue alert: %s", e)

        return 0

    except Exception as e:
        logger.exception("Scan failed: %s", e)
        print(_color(f"\n✗ SCAN FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: whale-watch
# ═══════════════════════════════════════════════════════════════════════════

def cmd_whale_watch(args: argparse.Namespace) -> int:
    """Track a specific whale wallet."""
    logger = logging.getLogger("the-eye.whale-watch")
    wallet = args.wallet
    chain = args.chain

    print(_banner())
    print(_section(f"WHALE WATCH: {wallet[:16]}..."))
    print(f"  Chain: {chain}")

    try:
        # Fetch wallet activity
        print(_section("Blockchain Activity"))
        blockchain = _init_blockchain()
        txs = blockchain.get_wallet_activity(wallet, chain=chain)
        raw_txs = [asdict(tx) for tx in txs] if txs else []
        print(f"  Transactions Found: {len(txs)}")
        if txs:
            for tx in txs[:5]:
                print(f"    • {tx.tx_hash[:16]}... | {tx.value_eth:.4f} ETH | {tx.timestamp}")

        # Run whale matcher
        print(_section("Whale Pattern Matching"))
        whale_matcher = _init_whale_matcher()
        match = whale_matcher.match_wallet(
            wallet_address=wallet,
            wallet_txs=raw_txs,
        )

        print(f"  Known Whale      : {match.is_known_whale}")
        print(f"  Label            : {match.matched_label or 'Unknown'}")
        print(f"  Patterns Matched : {', '.join(match.matched_patterns) or 'None'}")
        print(f"  Confidence       : {match.confidence:.1f}/100")
        print(f"  Win Rate         : {match.historical_win_rate:.1%}" if match.historical_win_rate else "  Win Rate         : N/A")
        print(f"  Predicted Action : {match.predicted_action or 'N/A'}")
        print(f"  Risk Level       : {_urgency_color(match.risk_level, match.risk_level.upper())}")

        if match.evidence:
            print("\n  Evidence:")
            for ev in match.evidence:
                print(f"    • {ev}")

        # Generate prediction
        print(_section("Prediction"))
        if match.matched_patterns:
            pred_gen = _init_prediction()
            try:
                prediction = pred_gen.generate_moon_prediction(
                    token="WALLET:" + wallet[:12],
                    probability=match.confidence,
                    whale_match=match,
                    timing_hours=match.predicted_sell_window_hours or 48,
                )
                print(f"  Type             : {prediction.prediction_type}")
                print(f"  Probability      : {prediction.probability:.1f}%")
                print(f"  Timing           : {prediction.timing_hours:.1f} hours")
                print(f"  Status           : {prediction.status}")
            except Exception as e:
                logger.warning("Prediction generation failed: %s", e)
                print("  Prediction generation skipped")
        else:
            print("  No patterns matched — no prediction generated")

        if args.json:
            print(json.dumps(asdict(match), indent=2, default=str))

        return 0

    except Exception as e:
        logger.exception("Whale watch failed: %s", e)
        print(_color(f"\n✗ WHALE WATCH FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: rug-check
# ═══════════════════════════════════════════════════════════════════════════

def cmd_rug_check(args: argparse.Namespace) -> int:
    """Rug pull probability check."""
    logger = logging.getLogger("the-eye.rug-check")
    address = args.address
    chain = args.chain

    print(_banner())
    print(_section(f"RUG CHECK: {address}"))
    print(f"  Chain: {chain}")

    try:
        # 1. Blockchain analysis
        print(_section("On-Chain Analysis"))
        blockchain = _init_blockchain()
        on_chain = blockchain.analyze_token(address, chain=chain)
        print(f"  Token Name       : {on_chain.token_name or 'N/A'}")
        print(f"  Liquidity Locked : {_color(str(on_chain.liquidity_locked), Colors.GREEN if on_chain.liquidity_locked else Colors.RED)}")
        print(f"  Lock Duration    : {on_chain.liquidity_lock_duration_days} days")
        print(f"  Liquidity (USD)  : ${on_chain.liquidity_usd:,.2f}")
        print(f"  Dev Holds %      : {on_chain.dev_holds_pct:.2f}%")
        print(f"  Dev Wallet Age   : {on_chain.deployer_wallet_age_days:.1f} days")
        print(f"  Contract Verified: {on_chain.contract_verified}")

        # 2. Social signals (for bot ratio)
        print(_section("Social Signals"))
        social = _init_social()
        token_name = on_chain.token_name or address[:12]
        social_signals = social.analyze_social_signals(token_name)
        social_bot_pct = social_signals.twitter_bot_ratio * 100
        print(f"  Twitter Bot Ratio: {social_bot_pct:.1f}%")
        print(f"  Sentiment        : {social_signals.overall_sentiment}")

        # 3. Dev Matcher
        print(_section("Dev Matcher"))
        dev_matcher = _init_dev_matcher()
        dev_address = on_chain.deployer or address
        dev_match = dev_matcher.analyze_dev(
            dev_address=dev_address,
            chain=chain,
            liquidity_locked=on_chain.liquidity_locked,
            liquidity_lock_days=on_chain.liquidity_lock_duration_days,
            dev_holds_pct=on_chain.dev_holds_pct,
            dev_wallet_age_days=on_chain.deployer_wallet_age_days,
            social_bot_pct=social_bot_pct,
            has_social_presence=social_signals.overall_sentiment != "unknown",
        )

        # 4. Rug Probability Engine
        print(_section("Rug Probability Engine"))
        rug_engine = _init_rug_engine()
        rug_result = rug_engine.calculate(
            token=token_name,
            dev_address=dev_address,
            chain=chain,
            on_chain_data={
                "liquidity_locked": on_chain.liquidity_locked,
                "liquidity_lock_days": on_chain.liquidity_lock_duration_days,
                "dev_holds_pct": on_chain.dev_holds_pct,
                "contract_verified": on_chain.contract_verified,
            },
            social_data={
                "bot_pct": social_bot_pct,
                "sentiment": social_signals.overall_sentiment,
                "has_social_presence": social_signals.overall_sentiment != "unknown",
            },
            market_data={
                "liquidity_usd": on_chain.liquidity_usd,
            },
        )

        probability = rug_result.get("probability", dev_match.rug_probability)
        urgency = rug_result.get("urgency", dev_match.urgency)
        rug_type = rug_result.get("rug_type", dev_match.rug_type)
        evidence = rug_result.get("evidence", dev_match.evidence)
        exit_window = rug_result.get("exit_window_hours", dev_match.exit_window_hours)

        print(f"  Rug Probability  : {_urgency_color(f'{probability:.1f}%', urgency)}")
        print(f"  Rug Type         : {rug_type or 'None detected'}")
        print(f"  Urgency          : {_urgency_color(urgency, urgency)}")
        print(f"  Exit Window      : {exit_window:.1f} hours")
        print(f"  Serial Rugger    : {_color(str(dev_match.known_serial_rugger), Colors.RED if dev_match.known_serial_rugger else Colors.GREEN)}")
        if dev_match.known_rug_count:
            print(f"  Known Rug Count  : {dev_match.known_rug_count}")

        if evidence:
            print("\n  Evidence Chain:")
            for ev in evidence[:10]:
                print(f"    • {ev}")

        # Format and enqueue alert
        formatter = _init_alert_formatter()
        alert = formatter.format_rug_alert(
            dev_match={
                "developer": dev_address,
                "risk_flags": dev_match.indicators_matched,
                "risk_score": probability,
                "evidence": "; ".join(evidence[:5]) if evidence else "",
                "confidence": int(dev_match.confidence),
                "agents": ["dev-matcher", "rug-probability", "blockchain-monitor"],
            },
            token=token_name,
            chain=chain,
        )

        if args.json:
            print(formatter.to_json(alert))
        else:
            print("\n" + formatter.to_text(alert))

        try:
            alert_queue = _init_alert_queue()
            alert_queue.enqueue(alert)
        except Exception as e:
            logger.warning("Failed to enqueue alert: %s", e)

        return 0

    except Exception as e:
        logger.exception("Rug check failed: %s", e)
        print(_color(f"\n✗ RUG CHECK FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: pump-scan
# ═══════════════════════════════════════════════════════════════════════════

def cmd_pump_scan(args: argparse.Namespace) -> int:
    """Detect fake pump."""
    logger = logging.getLogger("the-eye.pump-scan")
    token = args.token
    address = args.address or ""

    print(_banner())
    print(_section(f"PUMP SCAN: {token}"))

    try:
        # 1. Market Feed
        print(_section("Market Data"))
        market = _init_market()
        market_data = market.get_market_data(token, token_address=address)
        print(f"  Price (USD)      : ${market_data.price_usd:.8f}" if market_data.price_usd < 1 else f"  Price (USD)      : ${market_data.price_usd:,.2f}")
        print(f"  Price Change 24h : {market_data.price_change_24h:+.2f}%")
        print(f"  Volume 24h       : ${market_data.volume_24h_usd:,.2f}")
        print(f"  Buy/Sell Ratio   : {market_data.buy_sell_ratio:.2f}")

        # 2. Social Scanner
        print(_section("Social Signals"))
        social = _init_social()
        social_signals = social.analyze_social_signals(token)
        print(f"  Twitter (24h)    : {social_signals.twitter_mentions_24h}")
        print(f"  Bot Ratio        : {social_signals.twitter_bot_ratio:.2f}")
        print(f"  Sentiment        : {social_signals.overall_sentiment}")

        # 3. Manipulation Detector
        print(_section("Manipulation Detection"))
        manipulation = _init_manipulation()
        manip_result = manipulation.analyze_manipulation(
            token=token,
            price_change_24h=market_data.price_change_24h,
            volume_24h=market_data.volume_24h_usd,
            market_cap=market_data.market_cap_usd,
            buy_sell_ratio=market_data.buy_sell_ratio,
            twitter_mentions=social_signals.twitter_mentions_24h,
            twitter_bot_ratio=social_signals.twitter_bot_ratio,
            tiktok_videos=social_signals.tiktok_videos_24h,
            reddit_mentions=social_signals.reddit_mentions_24h,
        )
        print(f"  Fake Pump Score  : {_urgency_color(f'{manip_result.fake_pump_score:.1f}/100', manip_result.urgency)}")
        print(f"  Is Fake Pump     : {_color(str(manip_result.is_fake_pump), Colors.RED if manip_result.is_fake_pump else Colors.GREEN)}")
        print(f"  Confidence       : {manip_result.confidence:.1f}/100")
        print(f"  Urgency          : {_urgency_color(manip_result.urgency, manip_result.urgency)}")
        print(f"  Detected Patterns: {', '.join(manip_result.detected_patterns) or 'None'}")
        if manip_result.evidence:
            for ev in manip_result.evidence[:5]:
                print(f"    • {ev}")

        # 4. Pump Scorer
        print(_section("Pump Scoring"))
        pump_scorer = _init_pump_scorer()
        social_dict = {
            "tiktok_organic_videos": social_signals.tiktok_videos_24h,
            "reddit_organic_posts": social_signals.reddit_mentions_24h,
            "twitter_organic_mentions": int(social_signals.twitter_mentions_24h * (1 - social_signals.twitter_bot_ratio)),
            "twitter_total_mentions": social_signals.twitter_mentions_24h,
            "twitter_bot_ratio": social_signals.twitter_bot_ratio,
            "social_bot_pct": social_signals.twitter_bot_ratio * 100,
        }
        market_dict = {
            "price_change_24h_pct": market_data.price_change_24h,
            "volume_24h": market_data.volume_24h_usd,
            "market_cap": market_data.market_cap_usd,
            "liquidity_usd": market_data.liquidity_usd,
            "buy_sell_ratio": market_data.buy_sell_ratio,
            "real_volume_pct": 100.0,
        }
        pump_result = pump_scorer.score(
            token=token,
            social_signals=social_dict,
            market_data=market_dict,
            on_chain_data={"holder_count": 0, "top_10_holders_pct": 0},
            holders=[],
        )
        print(f"  Moon Probability : {_color(f'{pump_result.moon_probability:.1f}%', Colors.GREEN if pump_result.moon_probability > 50 else Colors.YELLOW)}")
        print(f"  Viral Score      : {pump_result.viral_score:.1f}/100")
        print(f"  Is Organic       : {_color(str(pump_result.is_organic), Colors.GREEN if pump_result.is_organic else Colors.RED)}")
        print(f"  Recommendation   : {pump_result.recommended_action}")

        # Alert
        formatter = _init_alert_formatter()
        alert = formatter.format_pump_alert(
            manipulation_result={
                "pattern": ", ".join(manip_result.detected_patterns) or "pump_analysis",
                "wallets": [],
                "volume_usd": market_data.volume_24h_usd,
                "confidence": int(manip_result.confidence),
                "agents": ["manipulation-detector", "pump-scorer", "social-scanner", "market-feed"],
            },
            token=token,
            chain="",
        )

        if args.json:
            print(formatter.to_json(alert))
        else:
            print("\n" + formatter.to_text(alert))

        try:
            alert_queue = _init_alert_queue()
            alert_queue.enqueue(alert)
        except Exception as e:
            logger.warning("Failed to enqueue alert: %s", e)

        return 0

    except Exception as e:
        logger.exception("Pump scan failed: %s", e)
        print(_color(f"\n✗ PUMP SCAN FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: danger-window
# ═══════════════════════════════════════════════════════════════════════════

def cmd_danger_window(args: argparse.Namespace) -> int:
    """Temporal risk scan."""
    logger = logging.getLogger("the-eye.danger-window")

    print(_banner())
    print(_section("DANGER WINDOW SCAN"))

    try:
        temporal = _init_temporal()
        risk_result = temporal.calculate_temporal_risk()

        now = datetime.now(timezone.utc)
        print(f"  Current UTC Time : {now.isoformat()}")
        print(f"  Risk Score       : {_urgency_color(f'{risk_result.risk_score:.1f}/100', 'CRITICAL' if risk_result.risk_score > 70 else 'HIGH' if risk_result.risk_score > 40 else 'MEDIUM' if risk_result.risk_score > 20 else 'LOW')}")
        print(f"  Active Windows   : {', '.join(risk_result.active_windows) or 'None'}")

        print(f"\n  {'Window':<20} {'Status':<10}")
        print(f"  {'─'*20} {'─'*10}")
        windows = [
            ("Rug Hour (02-05)", risk_result.is_rug_hour, "CRITICAL"),
            ("FOMO Peak (18-22)", risk_result.is_fomo_peak, "HIGH"),
            ("Dead Zone (08-12)", risk_result.is_dead_zone, "MEDIUM"),
            ("Weekend Trap", risk_result.is_weekend_trap, "MEDIUM"),
            ("Golden Hour (14-16)", risk_result.is_golden_hour, "LOW"),
        ]
        for name, active, level in windows:
            status = _urgency_color("● ACTIVE", level) if active else _color("○ Clear", Colors.DIM)
            print(f"  {name:<20} {status}")

        print(f"\n  Attack Freq Mult : {risk_result.attack_frequency_multiplier:.1f}×")
        print(f"  Liq Thinning     : {risk_result.liquidity_thinning_pct:.1f}%")
        print(f"  Geographic Gap   : {risk_result.geographic_gap}")

        if risk_result.evidence:
            print("\n  Evidence:")
            for ev in risk_result.evidence:
                print(f"    • {ev}")

        if risk_result.recommendations:
            print("\n  Recommendations:")
            for rec in risk_result.recommendations:
                print(f"    → {rec}")

        # Alert
        formatter = _init_alert_formatter()
        alert = formatter.format_temporal_alert(
            temporal_risk={
                "window": ", ".join(risk_result.active_windows) or "none",
                "risk_level": "CRITICAL" if risk_result.risk_score > 70 else "HIGH" if risk_result.risk_score > 40 else "MEDIUM" if risk_result.risk_score > 20 else "LOW",
                "reasoning": "; ".join(risk_result.evidence[:3]) if risk_result.evidence else "",
                "confidence": int(min(risk_result.risk_score, 100)),
                "agents": ["temporal-analyzer"],
            },
            token="SYSTEM",
        )

        if args.json:
            print(formatter.to_json(alert))
        else:
            print("\n" + formatter.to_text(alert))

        return 0

    except Exception as e:
        logger.exception("Danger window failed: %s", e)
        print(_color(f"\n✗ DANGER WINDOW FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: add-watchlist
# ═══════════════════════════════════════════════════════════════════════════

def cmd_add_watchlist(args: argparse.Namespace) -> int:
    """Add token to 24/7 monitoring."""
    logger = logging.getLogger("the-eye.add-watchlist")

    try:
        wl = _init_watchlist()
        entry = wl.add_token(
            token=args.token,
            address=args.address or "",
            chain=args.chain,
            reason=f"CLI add-watchlist",
            scan_interval=args.interval,
        )
        print(_color(f"✓ Added {args.token} to watchlist", Colors.GREEN + Colors.BOLD))
        print(f"  Token     : {entry.token}")
        print(f"  Address   : {entry.address or 'N/A'}")
        print(f"  Chain     : {entry.chain}")
        print(f"  Interval  : {entry.scan_interval_minutes} min")
        print(f"  Added At  : {entry.added_at}")

        if args.json:
            print(json.dumps(entry.to_dict(), indent=2, default=str))

        return 0

    except Exception as e:
        logger.exception("Add watchlist failed: %s", e)
        print(_color(f"\n✗ ADD WATCHLIST FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: remove-watchlist
# ═══════════════════════════════════════════════════════════════════════════

def cmd_remove_watchlist(args: argparse.Namespace) -> int:
    """Remove token from monitoring."""
    logger = logging.getLogger("the-eye.remove-watchlist")

    try:
        wl = _init_watchlist()
        removed = wl.remove_token(args.token)
        if removed:
            print(_color(f"✓ Removed {args.token} from watchlist", Colors.GREEN + Colors.BOLD))
        else:
            print(_color(f"✗ Token {args.token} not found in watchlist", Colors.YELLOW))

        if args.json:
            print(json.dumps({"token": args.token, "removed": removed}))

        return 0 if removed else 1

    except Exception as e:
        logger.exception("Remove watchlist failed: %s", e)
        print(_color(f"\n✗ REMOVE WATCHLIST FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: list-watchlist
# ═══════════════════════════════════════════════════════════════════════════

def cmd_list_watchlist(args: argparse.Namespace) -> int:
    """Show monitored tokens."""
    logger = logging.getLogger("the-eye.list-watchlist")

    try:
        wl = _init_watchlist()
        entries = wl.list_tokens()

        if not entries:
            print(_color("Watchlist is empty", Colors.DIM))
            return 0

        print(_banner())
        print(_section(f"WATCHLIST ({len(entries)} tokens)"))
        print(f"  {'Token':<15} {'Chain':<8} {'Interval':<10} {'Alerts':<8} {'Last Scan'}")
        print(f"  {'─'*15} {'─'*8} {'─'*10} {'─'*8} {'─'*25}")

        for entry in entries:
            last_scan = entry.last_scanned_at or "Never"
            print(f"  {entry.token:<15} {entry.chain:<8} {entry.scan_interval_minutes}m{'':<7} {entry.alert_count:<8} {last_scan}")

        if args.json:
            print(json.dumps([e.to_dict() for e in entries], indent=2, default=str))

        return 0

    except Exception as e:
        logger.exception("List watchlist failed: %s", e)
        print(_color(f"\n✗ LIST WATCHLIST FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: status
# ═══════════════════════════════════════════════════════════════════════════

def cmd_status(args: argparse.Namespace) -> int:
    """Show system health and last scans."""
    logger = logging.getLogger("the-eye.status")

    print(_banner())
    print(_section("SYSTEM STATUS"))

    try:
        # 1. Data sources health
        print(_section("Data Sources"))
        try:
            blockchain = _init_blockchain()
            health = blockchain.health_check()
            for source, healthy in health.items():
                status = _color("● OK", Colors.GREEN) if healthy else _color("● DOWN", Colors.RED)
                print(f"  {source:<15} {status}")
        except Exception as e:
            print(f"  Blockchain monitor: {_color(f'✗ {e}', Colors.RED)}")

        # Social health
        try:
            social = _init_social()
            social_health = social.health_check()
            for source, healthy in social_health.items():
                status = _color("● OK", Colors.GREEN) if healthy else _color("● DOWN", Colors.RED)
                print(f"  {source:<15} {status}")
        except Exception as e:
            print(f"  Social scanner   : {_color(f'✗ {e}', Colors.RED)}")

        # 2. Watchlist
        print(_section("Watchlist"))
        try:
            wl = _init_watchlist()
            entries = wl.list_tokens()
            due = wl.get_tokens_due_for_scan()
            print(f"  Total Tokens     : {len(entries)}")
            print(f"  Due for Scan     : {len(due)}")
        except Exception as e:
            print(f"  {_color(f'✗ {e}', Colors.RED)}")

        # 3. Alert queue
        print(_section("Alert Queue"))
        try:
            alert_queue = _init_alert_queue()
            stats = alert_queue.get_queue_stats()
            print(f"  Pending Alerts   : {stats.get('pending', 0)}")
            print(f"  Dispatched       : {stats.get('dispatched', 0)}")
            print(f"  Failed           : {stats.get('failed', 0)}")
            print(f"  Total            : {stats.get('total', 0)}")
        except Exception as e:
            print(f"  {_color(f'✗ {e}', Colors.RED)}")

        # 4. Dispatcher health
        print(_section("Dispatch Channels"))
        try:
            dispatcher = _init_dispatcher()
            dispatch_health = dispatcher.health_check()
            for ch_name, ch_info in dispatch_health.get("channels", {}).items():
                reachable = ch_info.get("reachable")
                if reachable is True:
                    status = _color("● OK", Colors.GREEN)
                elif reachable is False:
                    status = _color("● FAIL", Colors.RED)
                else:
                    status = _color("○ Disabled", Colors.DIM)
                note = ch_info.get("note", "")
                print(f"  {ch_name:<10} {status}  {note}")
        except Exception as e:
            print(f"  {_color(f'✗ {e}', Colors.RED)}")

        # 5. Prediction accuracy
        print(_section("Prediction Accuracy"))
        try:
            pred_gen = _init_prediction()
            accuracy = pred_gen.get_prediction_accuracy(days_back=30)
            overall = accuracy.get("overall_accuracy", 0)
            total = accuracy.get("total_predictions", 0)
            confirmed = accuracy.get("confirmed", 0)
            print(f"  Overall Accuracy : {overall:.1f}%")
            print(f"  Total Predictions: {total}")
            print(f"  Confirmed        : {confirmed}")
        except Exception as e:
            print(f"  {_color(f'✗ {e}', Colors.RED)}")

        # 6. Confidence engine
        try:
            confidence_engine = _init_confidence()
            overall_accuracy = confidence_engine.get_overall_accuracy()
            pattern_stats = confidence_engine.get_all_pattern_stats()
            print(f"  Learning DB Acc  : {overall_accuracy:.1f}%")
            print(f"  Patterns Tracked : {len(pattern_stats)}")
        except Exception as e:
            print(f"  {_color(f'✗ {e}', Colors.RED)}")

        # 7. Workflow state
        print(_section("Workflow State"))
        try:
            sm = _init_state_manager()
            ws = sm.get_workflow_state()
            print(f"  Status           : {_urgency_color(ws.status, 'CRITICAL' if ws.status == 'error' else 'LOW')}")
            print(f"  Active Tasks     : {', '.join(ws.active_tasks) or 'None'}")
            print(f"  Last Updated     : {ws.last_updated}")
        except Exception as e:
            print(f"  {_color(f'✗ {e}', Colors.RED)}")

        if args.json:
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "watchlist_count": len(entries) if 'entries' in dir() else 0,
                "alert_queue_stats": stats if 'stats' in dir() else {},
                "prediction_accuracy": accuracy if 'accuracy' in dir() else {},
            }
            print(json.dumps(result, indent=2, default=str))

        return 0

    except Exception as e:
        logger.exception("Status failed: %s", e)
        print(_color(f"\n✗ STATUS FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: monitor
# ═══════════════════════════════════════════════════════════════════════════

def cmd_monitor(args: argparse.Namespace) -> int:
    """Start 24/7 continuous monitoring."""
    logger = logging.getLogger("the-eye.monitor")
    interval = args.interval

    print(_banner())
    print(_section("24/7 CONTINUOUS MONITORING"))
    print(f"  Check Interval   : {interval}s")
    print(f"  Started At       : {datetime.now(timezone.utc).isoformat()}")
    print(f"\n  Press {_color('Ctrl+C', Colors.BOLD)} to stop gracefully.\n")

    try:
        scheduler = _init_scheduler()

        # Register agent functions with the scheduler
        def _blockchain_agent(**kwargs):
            """Blockchain scan agent."""
            try:
                blockchain = _init_blockchain()
                wl = _init_watchlist()
                due = wl.get_tokens_due_for_scan()
                results = []
                for entry in due:
                    if entry.address:
                        on_chain = blockchain.analyze_token(entry.address, chain=entry.chain)
                        results.append({"token": entry.token, "holders": on_chain.holder_count})
                        wl.update_scan_time(entry.token)
                return {"scanned": len(results), "results": results}
            except Exception as e:
                return {"error": str(e)}

        def _social_agent(**kwargs):
            """Social scan agent."""
            try:
                social = _init_social()
                wl = _init_watchlist()
                entries = wl.list_tokens()
                results = []
                for entry in entries[:10]:
                    signals = social.analyze_social_signals(entry.token)
                    results.append({"token": entry.token, "sentiment": signals.overall_sentiment})
                return {"scanned": len(results)}
            except Exception as e:
                return {"error": str(e)}

        def _market_agent(**kwargs):
            """Market scan agent."""
            try:
                market = _init_market()
                wl = _init_watchlist()
                entries = wl.list_tokens()
                results = []
                for entry in entries[:10]:
                    md = market.get_market_data(entry.token, token_address=entry.address, chain=entry.chain)
                    results.append({"token": entry.token, "price": md.price_usd, "change_24h": md.price_change_24h})
                return {"scanned": len(results)}
            except Exception as e:
                return {"error": str(e)}

        def _temporal_agent(**kwargs):
            """Temporal scan agent."""
            try:
                temporal = _init_temporal()
                risk = temporal.calculate_temporal_risk()
                return {"risk_score": risk.risk_score, "windows": risk.active_windows}
            except Exception as e:
                return {"error": str(e)}

        def _dispatch_agent(**kwargs):
            """Alert dispatch agent."""
            try:
                alert_queue = _init_alert_queue()
                result = alert_queue.flush()
                return result
            except Exception as e:
                return {"error": str(e)}

        from src.autonomous.cron_scheduler import register_agent
        register_agent("whale-tracker", _blockchain_agent)
        register_agent("social-sentiment", _social_agent)
        register_agent("pump-detector", _market_agent)
        register_agent("temporal-scanner", _temporal_agent)
        register_agent("alert-dispatcher", _dispatch_agent)

        # Run the continuous scheduler loop
        scheduler.run_continuous(interval_seconds=interval)
        return 0

    except KeyboardInterrupt:
        print(_color("\n\n✓ Monitoring stopped by user", Colors.GREEN + Colors.BOLD))
        return 0
    except Exception as e:
        logger.exception("Monitor failed: %s", e)
        print(_color(f"\n✗ MONITOR FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: dispatch-alerts
# ═══════════════════════════════════════════════════════════════════════════

def cmd_dispatch_alerts(args: argparse.Namespace) -> int:
    """Flush pending alert queue."""
    logger = logging.getLogger("the-eye.dispatch-alerts")

    print(_banner())
    print(_section("DISPATCH ALERTS"))

    try:
        alert_queue = _init_alert_queue()
        stats = alert_queue.get_queue_stats()
        print(f"  Pending Alerts   : {stats.get('pending', 0)}")
        print(f"  Total in Queue   : {stats.get('total', 0)}")

        if stats.get("pending", 0) == 0:
            print(_color("\n  No pending alerts to dispatch.", Colors.DIM))
            return 0

        print("\n  Dispatching...")
        result = alert_queue.flush()

        print(f"\n  Attempted  : {result.get('attempted', 0)}")
        print(f"  Succeeded  : {_color(str(result.get('succeeded', 0)), Colors.GREEN)}")
        print(f"  Failed     : {_color(str(result.get('failed', 0)), Colors.RED)}")
        print(f"  Skipped    : {result.get('skipped', 0)}")

        # Cleanup old entries
        cleaned = alert_queue.cleanup()
        if cleaned > 0:
            print(f"  Cleaned Up : {cleaned} old entries")

        if args.json:
            print(json.dumps(result, indent=2, default=str))

        return 0 if result.get("failed", 0) == 0 else 1

    except Exception as e:
        logger.exception("Dispatch alerts failed: %s", e)
        print(_color(f"\n✗ DISPATCH ALERTS FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: backtest
# ═══════════════════════════════════════════════════════════════════════════

def cmd_backtest(args: argparse.Namespace) -> int:
    """Evaluate prediction accuracy."""
    logger = logging.getLogger("the-eye.backtest")
    days = args.days

    print(_banner())
    print(_section(f"BACKTEST — Last {days} Days"))

    try:
        pred_gen = _init_prediction()
        accuracy = pred_gen.get_prediction_accuracy(days_back=days)

        overall = accuracy.get("overall_accuracy", 0)
        total = accuracy.get("total_predictions", 0)
        confirmed = accuracy.get("confirmed", 0)
        rejected = accuracy.get("rejected", 0)
        expired = accuracy.get("expired", 0)
        pending_count = accuracy.get("pending", 0)
        by_type = accuracy.get("by_type", {})

        print(f"  Overall Accuracy : {_urgency_color(f'{overall:.1f}%', 'LOW' if overall > 70 else 'MEDIUM' if overall > 40 else 'HIGH' if overall > 20 else 'CRITICAL')}")
        print(f"  Total Predictions: {total}")
        print(f"  Confirmed        : {_color(str(confirmed), Colors.GREEN)}")
        print(f"  Rejected         : {_color(str(rejected), Colors.RED)}")
        print(f"  Expired          : {expired}")
        print(f"  Pending          : {pending_count}")

        if by_type:
            print(f"\n  {'Type':<10} {'Total':<8} {'Confirmed':<12} {'Rejected':<12} {'Accuracy'}")
            print(f"  {'─'*10} {'─'*8} {'─'*12} {'─'*12} {'─'*10}")
            for pred_type, type_stats in by_type.items():
                type_total = type_stats.get("total", 0)
                type_confirmed = type_stats.get("confirmed", 0)
                type_rejected = type_stats.get("rejected", 0)
                type_accuracy = type_stats.get("accuracy", 0)
                print(f"  {pred_type:<10} {type_total:<8} {type_confirmed:<12} {type_rejected:<12} {type_accuracy:.1f}%")

        # Also show confidence engine accuracy
        print(_section("Confidence Engine"))
        try:
            confidence_engine = _init_confidence()
            ce_accuracy = confidence_engine.get_overall_accuracy()
            pattern_stats = confidence_engine.get_all_pattern_stats()
            print(f"  Learning DB Acc  : {ce_accuracy:.1f}%")
            print(f"  Patterns Tracked : {len(pattern_stats)}")
            if pattern_stats:
                print(f"\n  {'Pattern':<30} {'Confirmed':<12} {'Rejected':<12}")
                print(f"  {'─'*30} {'─'*12} {'─'*12}")
                for pname, pstats in sorted(pattern_stats.items(), key=lambda x: x[1].get("confirmed_count", 0), reverse=True)[:15]:
                    print(f"  {pname:<30} {pstats.get('confirmed_count', 0):<12} {pstats.get('rejected_count', 0):<12}")
        except Exception as e:
            print(f"  {_color(f'✗ {e}', Colors.RED)}")

        if args.json:
            print(json.dumps(accuracy, indent=2, default=str))

        return 0

    except Exception as e:
        logger.exception("Backtest failed: %s", e)
        print(_color(f"\n✗ BACKTEST FAILED: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# ARGPARSE SETUP
# ═══════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="the-eye",
        description="THE EYE — Memecoin Pattern Recognition System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  the-eye scan --token DOGE --address 0x... --chain eth
  the-eye whale-watch --wallet 0x... --chain eth
  the-eye rug-check --address 0x... --chain eth
  the-eye pump-scan --token PEPE
  the-eye danger-window
  the-eye add-watchlist --token SHIB --address 0x... --chain eth
  the-eye monitor --interval 60
  the-eye status
  the-eye backtest --days 30
""",
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"THE EYE v{VERSION}",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output machine-readable JSON",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="command",
        metavar="COMMAND",
        help="Available subcommands",
    )

    # ── scan ─────────────────────────────────────────────────────────────
    p_scan = subparsers.add_parser(
        "scan",
        help="Full analysis of a token",
        description="Run full analysis: blockchain → social → market → patterns → analysis → alert",
    )
    p_scan.add_argument("--token", "-t", required=True, help="Token name or symbol")
    p_scan.add_argument("--address", "-a", help="Token contract address")
    p_scan.add_argument("--chain", "-c", default="eth", choices=["eth", "solana"], help="Blockchain (default: eth)")

    # ── whale-watch ──────────────────────────────────────────────────────
    p_whale = subparsers.add_parser(
        "whale-watch",
        help="Track a specific whale wallet",
        description="Fetch wallet activity, run whale matcher, generate prediction",
    )
    p_whale.add_argument("--wallet", "-w", required=True, help="Wallet address")
    p_whale.add_argument("--chain", "-c", default="eth", choices=["eth", "solana"], help="Blockchain (default: eth)")

    # ── rug-check ────────────────────────────────────────────────────────
    p_rug = subparsers.add_parser(
        "rug-check",
        help="Rug pull probability check",
        description="Check rug pull probability for a contract or deployer address",
    )
    p_rug.add_argument("--address", "-a", required=True, help="Contract or deployer address")
    p_rug.add_argument("--chain", "-c", default="eth", choices=["eth", "solana"], help="Blockchain (default: eth)")

    # ── pump-scan ────────────────────────────────────────────────────────
    p_pump = subparsers.add_parser(
        "pump-scan",
        help="Detect fake pump",
        description="Detect coordinated artificial pump using market + social + manipulation analysis",
    )
    p_pump.add_argument("--token", "-t", required=True, help="Token name or symbol")
    p_pump.add_argument("--address", "-a", help="Token contract address")

    # ── danger-window ────────────────────────────────────────────────────
    p_danger = subparsers.add_parser(
        "danger-window",
        help="Temporal risk scan",
        description="Check current time-based risk windows (rug hour, FOMO peak, etc.)",
    )

    # ── add-watchlist ────────────────────────────────────────────────────
    p_add_wl = subparsers.add_parser(
        "add-watchlist",
        help="Add token to 24/7 monitoring",
        description="Add a token to the persistent watchlist for continuous monitoring",
    )
    p_add_wl.add_argument("--token", "-t", required=True, help="Token name or symbol")
    p_add_wl.add_argument("--address", "-a", help="Token contract address")
    p_add_wl.add_argument("--chain", "-c", default="eth", choices=["eth", "solana"], help="Blockchain (default: eth)")
    p_add_wl.add_argument("--interval", "-i", type=int, default=15, help="Scan interval in minutes (default: 15)")

    # ── remove-watchlist ─────────────────────────────────────────────────
    p_rm_wl = subparsers.add_parser(
        "remove-watchlist",
        help="Remove token from monitoring",
        description="Remove a token from the persistent watchlist",
    )
    p_rm_wl.add_argument("--token", "-t", required=True, help="Token name or symbol")

    # ── list-watchlist ───────────────────────────────────────────────────
    p_ls_wl = subparsers.add_parser(
        "list-watchlist",
        help="Show monitored tokens",
        description="Display all tokens currently in the watchlist",
    )

    # ── status ───────────────────────────────────────────────────────────
    p_status = subparsers.add_parser(
        "status",
        help="Show system health and last scans",
        description="Display data source health, watchlist stats, pending alerts, prediction accuracy",
    )

    # ── monitor ──────────────────────────────────────────────────────────
    p_monitor = subparsers.add_parser(
        "monitor",
        help="Start 24/7 continuous monitoring",
        description="Start the cron scheduler loop with graceful SIGINT/SIGTERM shutdown",
    )
    p_monitor.add_argument("--interval", "-i", type=int, default=60, help="Check interval in seconds (default: 60)")

    # ── dispatch-alerts ──────────────────────────────────────────────────
    p_dispatch = subparsers.add_parser(
        "dispatch-alerts",
        help="Flush pending alert queue",
        description="Dispatch all queued alerts to configured channels (Telegram, Discord, etc.)",
    )

    # ── backtest ─────────────────────────────────────────────────────────
    p_backtest = subparsers.add_parser(
        "backtest",
        help="Evaluate prediction accuracy",
        description="Show prediction accuracy from prediction_log.json over a lookback period",
    )
    p_backtest.add_argument("--days", "-d", type=int, default=30, help="Lookback period in days (default: 30)")

    return parser


# ═══════════════════════════════════════════════════════════════════════════
# COMMAND DISPATCH TABLE
# ═══════════════════════════════════════════════════════════════════════════

COMMAND_MAP = {
    "scan": cmd_scan,
    "whale-watch": cmd_whale_watch,
    "rug-check": cmd_rug_check,
    "pump-scan": cmd_pump_scan,
    "danger-window": cmd_danger_window,
    "add-watchlist": cmd_add_watchlist,
    "remove-watchlist": cmd_remove_watchlist,
    "list-watchlist": cmd_list_watchlist,
    "status": cmd_status,
    "monitor": cmd_monitor,
    "dispatch-alerts": cmd_dispatch_alerts,
    "backtest": cmd_backtest,
}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Parse arguments, set up logging, and dispatch to the appropriate subcommand."""
    parser = build_parser()
    args = parser.parse_args()

    # No subcommand → print help
    if args.command is None:
        parser.print_help()
        return 0

    # Configure logging
    setup_logging(verbose=args.verbose)

    # Dispatch
    handler = COMMAND_MAP.get(args.command)
    if handler is None:
        parser.error(f"Unknown command: {args.command}")

    try:
        return handler(args)
    except KeyboardInterrupt:
        print(_color("\n\nInterrupted by user.", Colors.YELLOW))
        return 130
    except Exception as e:
        logging.getLogger("the-eye").exception("Unhandled exception: %s", e)
        print(_color(f"\n✗ UNHANDLED ERROR: {e}", Colors.RED + Colors.BOLD), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
THE EYE — Shared test fixtures for all test modules.

Provides temp data directories with sample JSON databases, sample data
structures, and mocked monitor instances.
"""

import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ─── Project paths ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = SRC_DIR / "data"


# ─── Temporary data directory with sample JSON files ─────────────────────────

@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create a temp directory with copies of all JSON data files.

    Each test gets its own isolated copy so writes don't pollute other tests
    or the real database.
    """
    data = tmp_path / "data"
    data.mkdir()

    # Copy every JSON file from the real data directory
    for json_file in DATA_DIR.glob("*.json"):
        shutil.copy2(json_file, data / json_file.name)

    return data


# ─── Sample whale profile fixture ────────────────────────────────────────────

@pytest.fixture
def sample_whale_profile() -> Dict[str, Any]:
    """A representative whale profile dict for testing."""
    return {
        "address": "0x4a2b8c1d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
        "label": "PEPE Sniper",
        "chain": "eth",
        "win_count": 17,
        "total_trades": 20,
        "win_rate": 0.85,
        "patterns": ["sniper", "accumulate_pump_dump"],
        "avg_hold_time_hours": 48,
        "avg_profit_pct": 40,
        "avg_entry_timing": "launch_0_to_5_min",
        "first_seen": "2025-03-15T00:00:00Z",
        "last_seen": "2026-08-10T12:00:00Z",
        "total_volume_usd": 2_500_000,
        "known_associated_wallets": [],
        "notes": "High-conviction sniper.",
        "risk_level": "low",
    }


# ─── Sample dev signature fixture ────────────────────────────────────────────

@pytest.fixture
def sample_dev_signature() -> Dict[str, Any]:
    """A representative dev signature dict for testing."""
    return {
        "address": "0x9f1d2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e",
        "label": "Serial Rugger #14",
        "chain": "eth",
        "rug_count": 14,
        "rug_type": "hard_rug",
        "first_rug_date": "2025-01-15T00:00:00Z",
        "last_rug_date": "2026-08-09T03:00:00Z",
        "patterns": ["no_liquidity_lock", "fresh_wallets", "team_cluster", "social_bots"],
        "avg_rug_time_hours": 48,
        "total_stolen_usd": 4_200_000,
        "known_rug_projects": ["$MOONRUG", "$SAFEPEPE", "$ELONDOGE2", "$FLOKI2025"],
        "risk_score": 100,
    }


# ─── Sample temporal patterns fixture ────────────────────────────────────────

@pytest.fixture
def sample_temporal_patterns() -> Dict[str, Any]:
    """A representative temporal patterns dict for testing."""
    return {
        "version": "1.0.0",
        "temporal_windows": [
            {
                "name": "rug_hour",
                "start_utc": "02:00",
                "end_utc": "05:00",
                "attack_frequency_multiplier": 3.2,
                "rug_pull_percentage": 78,
                "liquidity_thinning_pct": 60,
                "geographic_gap": True,
                "risk_score_base": 40,
            },
            {
                "name": "fomo_peak",
                "start_utc": "18:00",
                "end_utc": "22:00",
                "risk_score_base": 25,
            },
            {
                "name": "dead_zone",
                "start_utc": "08:00",
                "end_utc": "12:00",
                "risk_score_base": 20,
            },
            {
                "name": "weekend_trap",
                "start_utc": "Friday 20:00",
                "end_utc": "Monday 08:00",
                "risk_score_base": 15,
            },
            {
                "name": "golden_hour",
                "start_utc": "14:00",
                "end_utc": "16:00",
                "risk_score_base": 5,
            },
        ],
        "hourly_attack_frequency": {
            "02": 3.2, "03": 3.57, "04": 3.1,
            "14": 0.6, "15": 0.5,
        },
        "day_of_week_attack_frequency": {
            "0": 1.2, "5": 1.5, "6": 1.6,
        },
        "geographic_gaps": [
            {"utc_window": "02:00-05:00", "risk_multiplier": 3.2},
        ],
        "historical_confirmed_rugs": [],
    }


# ─── Mocked monitor fixtures ────────────────────────────────────────────────

@pytest.fixture
def blockchain_monitor():
    """A mocked BlockchainMonitor that never makes real HTTP requests."""
    with patch("src.monitors.blockchain.BlockchainMonitor") as MockCls:
        instance = MagicMock()
        instance.analyze_token.return_value = MagicMock(
            chain="eth",
            token_address="0xtoken",
            token_name="TESTCOIN",
            deployer="0xdev",
            liquidity_locked=False,
            liquidity_lock_duration_days=0,
            liquidity_usd=50_000.0,
            holder_count=150,
            top_holders=[],
            recent_transactions=[],
            contract_verified=False,
            contract_age_hours=48.0,
            deployer_wallet_age_days=3.0,
            dev_holds_pct=35.0,
            data_source="dexscreener",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            error=None,
        )
        instance.health_check.return_value = {
            "dexscreener": True,
            "etherscan": True,
            "solscan": True,
        }
        MockCls.return_value = instance
        yield instance


@pytest.fixture
def social_scanner():
    """A mocked SocialScanner that never makes real HTTP requests."""
    with patch("src.monitors.social.SocialMonitor") as MockCls:
        instance = MagicMock()
        instance.scan_token.return_value = {
            "twitter_mentions": 55000,
            "twitter_bot_ratio": 0.97,
            "tiktok_videos": 0,
            "reddit_mentions": 0,
        }
        MockCls.return_value = instance
        yield instance


@pytest.fixture
def market_feed():
    """A mocked MarketFeed that never makes real HTTP requests."""
    with patch("src.monitors.market.MarketFeed") as MockCls:
        instance = MagicMock()
        instance.get_token_price.return_value = {
            "price_usd": 0.001,
            "price_change_24h": 350.0,
            "volume_24h": 1_000_000,
            "market_cap": 5_000_000,
        }
        MockCls.return_value = instance
        yield instance


# ─── Helper: build sniper transactions ──────────────────────────────────────

@pytest.fixture
def sniper_txs():
    """Transactions typical of a sniper wallet (buy within 5 min of launch)."""
    launch = "2026-08-10T12:00:00Z"
    return [
        {
            "timestamp": "2026-08-10T12:02:30Z",
            "is_swap": True,
            "value_eth": 5.0,
            "token_amount": 1000000,
        },
        {
            "timestamp": "2026-08-10T12:03:15Z",
            "is_swap": True,
            "value_eth": 3.0,
            "token_amount": 600000,
        },
    ], launch


# ─── Helper: build diamond-hands transactions ────────────────────────────────

@pytest.fixture
def diamond_hands_txs():
    """Transactions typical of a diamond-hands wallet (many buys, tiny sells)."""
    base = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    txs = []
    for i in range(8):
        ts = (base + timedelta(hours=i * 12)).isoformat().replace("+00:00", "Z")
        txs.append({
            "timestamp": ts,
            "is_swap": True,
            "value_eth": 2.0,
            "token_amount": 400000,
        })
    # Only one small sell (10% of position)
    ts = (base + timedelta(days=5)).isoformat().replace("+00:00", "Z")
    txs.append({
        "timestamp": ts,
        "is_swap": True,
        "value_eth": -0.5,
        "token_amount": 100000,  # 10% of 1_000_000
    })
    return txs


# ─── Helper: build failed-whale transactions ────────────────────────────────

@pytest.fixture
def failed_whale_txs():
    """Transactions typical of a failed whale (panic sells after buys)."""
    base = datetime(2026, 8, 1, 18, 0, 0, tzinfo=timezone.utc)
    txs = []
    # 3 buys
    for i in range(3):
        ts = (base + timedelta(hours=i * 6)).isoformat().replace("+00:00", "Z")
        txs.append({
            "timestamp": ts,
            "is_swap": True,
            "value_eth": 3.0,
            "token_amount": 500000,
        })
    # 3 quick panic sells within 12h of buys
    for i in range(3):
        ts = (base + timedelta(hours=i * 6 + 2)).isoformat().replace("+00:00", "Z")
        txs.append({
            "timestamp": ts,
            "is_swap": True,
            "value_eth": -2.5,
            "token_amount": 400000,
        })
    return txs


# ─── Helper: soft-rug dev transactions ──────────────────────────────────────

@pytest.fixture
def soft_rug_dev_txs():
    """Dev transactions typical of a soft rug (gradual selling over 24-72h)."""
    base = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
    txs = []
    for i in range(5):
        ts = (base + timedelta(hours=i * 12)).isoformat().replace("+00:00", "Z")
        txs.append({
            "timestamp": ts,
            "is_swap": True,
            "value_eth": -(1.0 + i * 0.5),  # sells
            "token_amount": 200000,
        })
    return txs

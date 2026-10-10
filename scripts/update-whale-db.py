#!/usr/bin/env python3
"""
THE EYE — Whale Profile Database Updater

Manually add or update whale wallet profiles in the whale_profiles.json database.

Usage:
    python scripts/update-whale-db.py --wallet 0xabc... --label "My Whale" --chain eth --pattern sniper
    python scripts/update-whale-db.py --wallet 0xabc... --label "New Label" --pattern diamond_hands
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
WHALE_DB_FILE = DATA_DIR / "whale_profiles.json"


def load_db(path: Path) -> dict:
    """Load the whale profiles database."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"ERROR: Failed to load {path}: {e}", file=sys.stderr)
            sys.exit(1)
    return {"version": "1.0.0", "profiles": [], "pattern_definitions": {}}


def save_db(db: dict, path: Path) -> None:
    """Save the whale profiles database."""
    db["last_updated"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Saved to {path}")


def find_profile(db: dict, wallet: str) -> dict | None:
    """Find a profile by wallet address (case-insensitive)."""
    normalized = wallet.lower()
    for profile in db.get("profiles", []):
        if profile.get("address", "").lower() == normalized:
            return profile
    return None


def main():
    parser = argparse.ArgumentParser(description="Update THE EYE whale profile database")
    parser.add_argument("--wallet", required=True, help="Wallet address")
    parser.add_argument("--label", default=None, help="Whale label (e.g. 'PEPE Sniper')")
    parser.add_argument("--chain", default="eth", help="Blockchain (eth, solana, base)")
    parser.add_argument("--pattern", action="append", default=[], help="Pattern(s) to add (repeatable)")
    parser.add_argument("--win-rate", type=float, default=None, help="Win rate (0.0-1.0)")
    parser.add_argument("--risk-level", choices=["low", "medium", "high", "critical"], default=None, help="Risk level")
    parser.add_argument("--notes", default=None, help="Notes about this whale")
    parser.add_argument("--delete", action="store_true", help="Delete this whale profile instead of adding/updating")
    args = parser.parse_args()

    db = load_db(WHALE_DB_FILE)

    if args.delete:
        # Delete the profile
        original_count = len(db.get("profiles", []))
        db["profiles"] = [
            p for p in db.get("profiles", [])
            if p.get("address", "").lower() != args.wallet.lower()
        ]
        if len(db["profiles"]) < original_count:
            save_db(db, WHALE_DB_FILE)
            print(f"✓ Deleted whale profile for {args.wallet}")
        else:
            print(f"✗ Whale {args.wallet} not found in database")
        return

    # Find or create profile
    profile = find_profile(db, args.wallet)
    if profile:
        print(f"Updating existing whale: {profile.get('label', args.wallet)}")
    else:
        profile = {
            "address": args.wallet,
            "label": args.wallet[:8] + "...",
            "chain": args.chain,
            "win_count": 0,
            "total_trades": 0,
            "win_rate": 0.0,
            "patterns": [],
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "total_volume_usd": 0,
            "known_associated_wallets": [],
            "notes": "",
            "risk_level": "medium",
        }
        db["profiles"].append(profile)
        print(f"Adding new whale: {args.wallet}")

    # Update fields
    if args.label:
        profile["label"] = args.label
    if args.chain:
        profile["chain"] = args.chain
    if args.pattern:
        for p in args.pattern:
            if p not in profile.get("patterns", []):
                profile.setdefault("patterns", []).append(p)
    if args.win_rate is not None:
        profile["win_rate"] = args.win_rate
    if args.risk_level is not None:
        profile["risk_level"] = args.risk_level
    if args.notes is not None:
        profile["notes"] = args.notes

    profile["last_seen"] = datetime.now(timezone.utc).isoformat()

    save_db(db, WHALE_DB_FILE)
    print(f"  Label:      {profile.get('label', 'N/A')}")
    print(f"  Chain:      {profile.get('chain', 'N/A')}")
    print(f"  Patterns:   {', '.join(profile.get('patterns', []))}")
    print(f"  Win Rate:   {profile.get('win_rate', 0):.0%}")
    print(f"  Risk Level: {profile.get('risk_level', 'N/A')}")


if __name__ == "__main__":
    main()

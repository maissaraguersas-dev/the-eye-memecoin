#!/usr/bin/env python3
"""
THE EYE — Dev Signature Database Updater

Manually add or update developer wallet signatures in the dev_signatures.json database.

Usage:
    python scripts/update-dev-db.py --wallet 0xabc... --label "New Rugger" --rug-count 3 --chain eth
    python scripts/update-dev-db.py --wallet 0xabc... --label "Updated" --rug-count 5
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
DEV_DB_FILE = DATA_DIR / "dev_signatures.json"


def load_db(path: Path) -> dict:
    """Load the dev signatures database."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"ERROR: Failed to load {path}: {e}", file=sys.stderr)
            sys.exit(1)
    return {
        "version": "1.0.0",
        "signatures": [],
        "honest_dev_markers": [],
        "rug_signatures": {},
        "scoring_weights": {},
    }


def save_db(db: dict, path: Path) -> None:
    """Save the dev signatures database."""
    db["last_updated"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Saved to {path}")


def find_signature(db: dict, wallet: str) -> dict | None:
    """Find a dev signature by wallet address (case-insensitive)."""
    normalized = wallet.lower()
    for sig in db.get("signatures", []):
        if sig.get("address", "").lower() == normalized:
            return sig
    # Also check honest devs
    for dev in db.get("honest_dev_markers", []):
        if dev.get("address", "").lower() == normalized:
            return dev
    return None


def main():
    parser = argparse.ArgumentParser(description="Update THE EYE dev signature database")
    parser.add_argument("--wallet", required=True, help="Developer wallet address")
    parser.add_argument("--label", default=None, help="Developer label")
    parser.add_argument("--rug-count", type=int, default=None, help="Number of confirmed rugs")
    parser.add_argument("--chain", default="eth", help="Blockchain (eth, solana, base)")
    parser.add_argument("--rug-type", choices=["hard_rug", "soft_rug", "honey_pot", "migration_scam"], default=None, help="Rug type")
    parser.add_argument("--risk-score", type=int, default=None, help="Risk score (0-100)")
    parser.add_argument("--honest", action="store_true", help="Mark as honest dev instead of rugger")
    parser.add_argument("--delete", action="store_true", help="Delete this dev signature")
    args = parser.parse_args()

    db = load_db(DEV_DB_FILE)

    if args.delete:
        original_count = len(db.get("signatures", []))
        db["signatures"] = [
            s for s in db.get("signatures", [])
            if s.get("address", "").lower() != args.wallet.lower()
        ]
        db["honest_dev_markers"] = [
            d for d in db.get("honest_dev_markers", [])
            if d.get("address", "").lower() != args.wallet.lower()
        ]
        total_removed = original_count - len(db["signatures"]) + (
            len([d for d in db.get("honest_dev_markers", [])])  # not accurate but close enough
        )
        save_db(db, DEV_DB_FILE)
        print(f"✓ Deleted dev signature for {args.wallet}")
        return

    if args.honest:
        # Add to honest_dev_markers
        markers = db.setdefault("honest_dev_markers", [])
        existing = None
        for m in markers:
            if m.get("address", "").lower() == args.wallet.lower():
                existing = m
                break

        if existing:
            print(f"Updating existing honest dev: {existing.get('label', args.wallet)}")
            entry = existing
        else:
            entry = {
                "address": args.wallet,
                "label": args.label or args.wallet[:8] + "...",
                "chain": args.chain,
                "successful_projects": 0,
                "renounced_ownership": True,
                "locked_liquidity": True,
                "lock_duration_days": 365,
                "doxxed": False,
                "audit_reports": 0,
                "risk_score": 5,
            }
            markers.append(entry)
            print(f"Adding new honest dev: {args.wallet}")

        if args.label:
            entry["label"] = args.label
        if args.risk_score is not None:
            entry["risk_score"] = args.risk_score
    else:
        # Add to signatures (rugger)
        sigs = db.setdefault("signatures", [])
        existing = find_signature(db, args.wallet)

        if existing and existing in sigs:
            print(f"Updating existing dev signature: {existing.get('label', args.wallet)}")
            entry = existing
        else:
            entry = {
                "address": args.wallet,
                "label": args.label or args.wallet[:8] + "...",
                "chain": args.chain,
                "rug_count": 0,
                "rug_type": "unknown",
                "first_rug_date": datetime.now(timezone.utc).isoformat(),
                "last_rug_date": datetime.now(timezone.utc).isoformat(),
                "patterns": [],
                "total_stolen_usd": 0,
                "known_rug_projects": [],
                "risk_score": 50,
            }
            sigs.append(entry)
            print(f"Adding new dev signature: {args.wallet}")

        if args.label:
            entry["label"] = args.label
        if args.rug_count is not None:
            entry["rug_count"] = args.rug_count
        if args.rug_type is not None:
            entry["rug_type"] = args.rug_type
        if args.risk_score is not None:
            entry["risk_score"] = args.risk_score

    save_db(db, DEV_DB_FILE)
    print(f"  Label:      {entry.get('label', 'N/A')}")
    print(f"  Chain:      {entry.get('chain', 'N/A')}")
    if not args.honest:
        print(f"  Rug Count:  {entry.get('rug_count', 0)}")
        print(f"  Rug Type:   {entry.get('rug_type', 'N/A')}")
    print(f"  Risk Score: {entry.get('risk_score', 'N/A')}")


if __name__ == "__main__":
    main()

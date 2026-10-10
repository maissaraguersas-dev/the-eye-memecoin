#!/usr/bin/env python3
"""THE EYE — Discord Webhook Setup

Interactive script to configure Discord webhook for alerts.
"""
import json
import sys
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"
USER_CONFIG = CONFIG_DIR / "user.json"


def main():
    print("🐋👁️  THE EYE — Discord Webhook Setup")
    print()
    print("Steps to get free Discord webhook:")
    print("1. Open your Discord server settings")
    print("2. Go to Integrations → Webhooks")
    print("3. Click 'New Webhook'")
    print("4. Name it 'The Eye Alerts'")
    print("5. Choose a channel (e.g., #memecoin-alerts)")
    print("6. Copy the webhook URL")
    print()

    webhook_url = input("Enter your webhook URL: ").strip()
    if not webhook_url:
        print("No URL provided. Exiting.")
        sys.exit(1)

    # Save to user config
    config = {}
    if USER_CONFIG.exists():
        with open(USER_CONFIG) as f:
            config = json.load(f)

    if "alerts" not in config:
        config["alerts"] = {}

    config["alerts"]["discord_webhook_url"] = webhook_url

    with open(USER_CONFIG, "w") as f:
        json.dump(config, f, indent=2)

    print()
    print("✅ Discord webhook configured! Alerts will be sent to your channel.")
    print(f"   Config saved to: {USER_CONFIG}")


if __name__ == "__main__":
    main()

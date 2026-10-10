#!/usr/bin/env python3
"""THE EYE — Telegram Bot Setup

Interactive script to configure Telegram bot for alerts.
"""
import json
import sys
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"
USER_CONFIG = CONFIG_DIR / "user.json"


def main():
    print("🐋👁️  THE EYE — Telegram Bot Setup")
    print()
    print("Steps to get free Telegram bot:")
    print("1. Open Telegram, search for @BotFather")
    print("2. Send /newbot")
    print("3. Choose a name (e.g., 'The Eye Memecoin Alerts')")
    print("4. Choose a username (e.g., 'the_eye_alerts_bot')")
    print("5. BotFather will give you a token like: 123456:ABC-DEF...")
    print()

    token = input("Enter your bot token: ").strip()
    if not token:
        print("No token provided. Exiting.")
        sys.exit(1)

    print()
    print("Now get your chat_id:")
    print("1. Send a message to your bot in Telegram")
    print("2. Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
    print("3. Find 'chat': {'id': <YOUR_CHAT_ID>}")
    print()

    chat_id = input("Enter your chat_id: ").strip()
    if not chat_id:
        print("No chat_id provided. Exiting.")
        sys.exit(1)

    # Save to user config
    config = {}
    if USER_CONFIG.exists():
        with open(USER_CONFIG) as f:
            config = json.load(f)

    if "alerts" not in config:
        config["alerts"] = {}

    config["alerts"]["telegram_bot_token"] = token
    config["alerts"]["telegram_chat_id"] = chat_id

    with open(USER_CONFIG, "w") as f:
        json.dump(config, f, indent=2)

    print()
    print("✅ Telegram bot configured! Alerts will be sent to your bot.")
    print(f"   Config saved to: {USER_CONFIG}")


if __name__ == "__main__":
    main()

"""THE EYE — Configuration Manager"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

CONFIG_DIR = Path(__file__).parent
DEFAULTS_FILE = CONFIG_DIR / "defaults.json"
USER_CONFIG_FILE = CONFIG_DIR / "user.json"


def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class Settings:
    """Singleton configuration loaded from defaults.json + user.json overrides."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        defaults = _load_json(DEFAULTS_FILE)
        user = _load_json(USER_CONFIG_FILE)
        self._config = _deep_merge(defaults, user)

    def reload(self):
        self._load()

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value: Any):
        keys = key.split(".")
        cfg = self._config
        for k in keys[:-1]:
            cfg = cfg.setdefault(k, {})
        cfg[keys[-1]] = value
        self._save_user()

    def _save_user(self):
        with open(USER_CONFIG_FILE, "w") as f:
            json.dump(self._config, f, indent=2)

    @property
    def all(self) -> dict:
        return self._config.copy()

    # Convenience accessors
    @property
    def chains(self) -> list:
        return self.get("scan.chains", ["eth", "sol", "base"])

    @property
    def min_confidence(self) -> int:
        return self.get("alerts.min_confidence", 60)

    @property
    def scan_interval(self) -> int:
        return self.get("market_scanner.discovery_interval_sec", 60)


settings = Settings()

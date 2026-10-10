"""
THE EYE — Memecoin Pattern Recognition System
Watchlist Manager Module

Manages tokens under 24/7 monitoring: adding, removing, scheduling
scans, and tracking alert counts per token.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .state_manager import StateManager

logger = logging.getLogger("the-eye.watchlist-manager")


# ---------------------------------------------------------------------------
# WatchlistEntry dataclass
# ---------------------------------------------------------------------------

@dataclass
class WatchlistEntry:
    """A single token under active monitoring."""

    token: str
    address: str
    chain: str
    added_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    added_reason: str = ""
    scan_interval_minutes: int = 5
    last_scanned_at: Optional[str] = None
    alert_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WatchlistEntry":
        return cls(
            token=d.get("token", ""),
            address=d.get("address", ""),
            chain=d.get("chain", ""),
            added_at=d.get("added_at", datetime.now(timezone.utc).isoformat()),
            added_reason=d.get("added_reason", ""),
            scan_interval_minutes=int(d.get("scan_interval_minutes", 5)),
            last_scanned_at=d.get("last_scanned_at"),
            alert_count=int(d.get("alert_count", 0)),
        )

    def is_due_for_scan(self) -> bool:
        """Return True if this token's next scan is overdue."""
        if self.last_scanned_at is None:
            return True
        try:
            last = datetime.fromisoformat(self.last_scanned_at)
            next_scan = last + timedelta(minutes=self.scan_interval_minutes)
            return datetime.now(timezone.utc) >= next_scan
        except (ValueError, TypeError):
            # If we can't parse the timestamp, consider it due
            return True


# ---------------------------------------------------------------------------
# WatchlistManager
# ---------------------------------------------------------------------------

class WatchlistManager:
    """CRUD + scheduling operations for the token watchlist."""

    def __init__(
        self,
        watchlist_path: Optional[str] = None,
        state_manager: Optional[StateManager] = None,
    ) -> None:
        self.watchlist_path = Path(watchlist_path) if watchlist_path else None
        self.state_manager = state_manager or StateManager()
        self._entries: Dict[str, WatchlistEntry] = {}
        self._load()

    # ------------------------------------------------------------------
    # Internal persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load watchlist entries from the JSON file."""
        raw: List[Dict[str, Any]] = []
        if self.watchlist_path and self.watchlist_path.exists():
            import json
            try:
                with open(self.watchlist_path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load watchlist from %s: %s", self.watchlist_path, exc)
                raw = []
        else:
            # Fallback to state_manager's watchlist
            raw = self.state_manager.get_watchlist()

        for d in raw:
            entry = WatchlistEntry.from_dict(d)
            self._entries[entry.token] = entry

    def _save(self) -> None:
        """Persist current entries back to storage."""
        data = [e.to_dict() for e in self._entries.values()]
        self.state_manager.update_watchlist(data)

        if self.watchlist_path:
            import json
            try:
                self.watchlist_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.watchlist_path, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
            except OSError as exc:
                logger.error("Failed to write watchlist to %s: %s", self.watchlist_path, exc)

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def add_token(
        self,
        token: str,
        address: str,
        chain: str,
        reason: str = "",
        scan_interval: int = 5,
    ) -> WatchlistEntry:
        """Add a token to the watchlist. Returns the new entry.

        If the token already exists, its fields are updated in-place
        (except alert_count is preserved).
        """
        now = datetime.now(timezone.utc).isoformat()
        existing = self._entries.get(token)

        entry = WatchlistEntry(
            token=token,
            address=address,
            chain=chain,
            added_at=existing.added_at if existing else now,
            added_reason=reason,
            scan_interval_minutes=scan_interval,
            last_scanned_at=existing.last_scanned_at if existing else None,
            alert_count=existing.alert_count if existing else 0,
        )
        self._entries[token] = entry
        self._save()
        logger.info(
            "Added token %s (%s) to watchlist — interval %d min",
            token, chain, scan_interval,
        )
        return entry

    def remove_token(self, token: str) -> bool:
        """Remove a token from the watchlist. Returns True if removed."""
        if token in self._entries:
            del self._entries[token]
            self._save()
            logger.info("Removed token %s from watchlist", token)
            return True
        logger.debug("Token %s not found in watchlist", token)
        return False

    def list_tokens(self) -> List[WatchlistEntry]:
        """Return all watchlist entries."""
        return list(self._entries.values())

    # ------------------------------------------------------------------
    # Scheduling helpers
    # ------------------------------------------------------------------

    def get_tokens_due_for_scan(self) -> List[WatchlistEntry]:
        """Return tokens where last_scanned_at + scan_interval < now."""
        due = [e for e in self._entries.values() if e.is_due_for_scan()]
        logger.debug("%d / %d tokens are due for scan", len(due), len(self._entries))
        return due

    def update_scan_time(self, token: str) -> bool:
        """Update last_scanned_at to now for the given token."""
        entry = self._entries.get(token)
        if entry is None:
            logger.warning("Cannot update scan time — token %s not in watchlist", token)
            return False
        entry.last_scanned_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def increment_alert_count(self, token: str) -> int:
        """Increment alert count for the given token. Returns new count."""
        entry = self._entries.get(token)
        if entry is None:
            logger.warning("Cannot increment alert count — token %s not in watchlist", token)
            return 0
        entry.alert_count += 1
        self._save()
        return entry.alert_count

    def is_watched(self, token: str) -> bool:
        """Check if a token is in the watchlist."""
        return token in self._entries

"""
THE EYE — Memecoin Pattern Recognition System
Alert Queue Module

Buffers and flushes alerts: enqueue → FIFO dequeue → dispatch → cleanup.
Provides retry accounting and queue statistics.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.alerts.formatter import Alert
from dataclasses import asdict

logger = logging.getLogger("the-eye.alert-queue")

# Maximum dispatch attempts before marking an alert as permanently failed
MAX_DISPATCH_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# QueuedAlert dataclass
# ---------------------------------------------------------------------------

@dataclass
class QueuedAlert:
    """An Alert wrapped with dispatch bookkeeping."""

    alert: Alert
    queued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dispatched: bool = False
    dispatch_attempts: int = 0
    last_attempt_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "alert": asdict(self.alert),
            "queued_at": self.queued_at,
            "dispatched": self.dispatched,
            "dispatch_attempts": self.dispatch_attempts,
            "last_attempt_at": self.last_attempt_at,
        }
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "QueuedAlert":
        alert_data = d.get("alert", {})
        alert = Alert(**{k: v for k, v in alert_data.items() if k in Alert.__dataclass_fields__})
        return cls(
            alert=alert,
            queued_at=d.get("queued_at", datetime.now(timezone.utc).isoformat()),
            dispatched=d.get("dispatched", False),
            dispatch_attempts=int(d.get("dispatch_attempts", 0)),
            last_attempt_at=d.get("last_attempt_at"),
        )

    @property
    def is_failed(self) -> bool:
        """True if max dispatch attempts have been exhausted without success."""
        return self.dispatch_attempts >= MAX_DISPATCH_ATTEMPTS and not self.dispatched


# ---------------------------------------------------------------------------
# AlertQueue
# ---------------------------------------------------------------------------

class AlertQueue:
    """Buffers alerts and flushes them through the dispatcher."""

    def __init__(
        self,
        queue_path: Optional[str] = None,
        dispatcher: Optional[Any] = None,
    ) -> None:
        """
        Args:
            queue_path: Path to alert_queue.json for persistence.
                        Falls back to StateManager default if None.
            dispatcher: An AlertDispatcher instance (lazy-imported if None).
        """
        self.queue_path = Path(queue_path) if queue_path else None
        self._dispatcher = dispatcher
        self._queue: List[QueuedAlert] = []
        self._load()

    # ------------------------------------------------------------------
    # Lazy dispatcher access (avoids circular import at module level)
    # ------------------------------------------------------------------

    @property
    def dispatcher(self) -> Any:
        if self._dispatcher is None:
            from src.alerts.dispatcher import Dispatcher
            self._dispatcher = Dispatcher()
        return self._dispatcher

    # ------------------------------------------------------------------
    # Internal persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load the queue from disk."""
        if self.queue_path and self.queue_path.exists():
            try:
                with open(self.queue_path, "r", encoding="utf-8") as fh:
                    raw: List[Dict[str, Any]] = json.load(fh)
                self._queue = [QueuedAlert.from_dict(d) for d in raw]
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load alert queue from %s: %s", self.queue_path, exc)
                self._queue = []
        else:
            # Try state_manager fallback
            try:
                from .state_manager import StateManager
                sm = StateManager()
                raw = sm.get_alert_queue()
                self._queue = [QueuedAlert.from_dict(d) for d in raw]
            except Exception as exc:
                logger.debug("State manager fallback failed: %s", exc)
                self._queue = []

    def _save(self) -> None:
        """Persist the queue to disk."""
        data = [qa.to_dict() for qa in self._queue]

        if self.queue_path:
            try:
                self.queue_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.queue_path, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
            except OSError as exc:
                logger.error("Failed to write alert queue to %s: %s", self.queue_path, exc)

        # Also persist via state_manager for redundancy
        try:
            from .state_manager import StateManager
            sm = StateManager()
            sm.update_alert_queue(data)
        except Exception as exc:
            logger.debug("State manager save fallback failed: %s", exc)

    # ------------------------------------------------------------------
    # Core queue operations
    # ------------------------------------------------------------------

    def enqueue(self, alert: Alert) -> QueuedAlert:
        """Add an alert to the queue. Returns the queued wrapper."""
        qa = QueuedAlert(alert=alert)
        self._queue.append(qa)
        self._save()
        logger.info("Enqueued alert [%s] (%s) — queue size: %d", alert.title, alert.alert_type, len(self._queue))
        return qa

    def dequeue(self, limit: int = 10) -> List[QueuedAlert]:
        """Get pending (undispatched, non-failed) alerts in FIFO order.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            List of QueuedAlert objects that are pending dispatch.
        """
        pending = [
            qa for qa in self._queue
            if not qa.dispatched and not qa.is_failed
        ]
        return pending[:limit]

    def mark_dispatched(self, alert_title: str) -> bool:
        """Mark an alert as successfully dispatched by title."""
        for qa in self._queue:
            if qa.alert.title == alert_title:
                qa.dispatched = True
                qa.last_attempt_at = datetime.now(timezone.utc).isoformat()
                self._save()
                logger.info("Alert %s marked as dispatched", alert_title)
                return True
        logger.warning("Alert %s not found in queue", alert_title)
        return False

    # ------------------------------------------------------------------
    # Flush — dispatch all pending alerts
    # ------------------------------------------------------------------

    def flush(self) -> Dict[str, Any]:
        """Dispatch all pending alerts through the dispatcher.

        Returns a summary dict with success/failure counts.
        """
        pending = self.dequeue(limit=1000)  # dispatch all pending
        results = {"attempted": 0, "succeeded": 0, "failed": 0, "skipped": 0}

        for qa in pending:
            # Skip old alerts (>24h since queued)
            try:
                queued_time = datetime.fromisoformat(qa.queued_at)
                age = datetime.now(timezone.utc) - queued_time
                if age > timedelta(hours=24):
                    qa.dispatched = True
                    results["skipped"] += 1
                    continue
            except Exception:
                pass

            qa.dispatch_attempts += 1
            qa.last_attempt_at = datetime.now(timezone.utc).isoformat()
            results["attempted"] += 1

            try:
                dispatch_results = self.dispatcher.dispatch(qa.alert)
                # Consider dispatch successful if at least one channel succeeded
                any_success = any(r.success for r in dispatch_results)
                if any_success:
                    qa.dispatched = True
                    results["succeeded"] += 1
                elif not dispatch_results:
                    # No channels configured / urgency below threshold
                    qa.dispatched = True
                    results["skipped"] += 1
                    results["attempted"] -= 1
                else:
                    results["failed"] += 1
                    if qa.is_failed:
                        logger.warning(
                            "Alert [%s] permanently failed after %d attempts",
                            qa.alert.title, qa.dispatch_attempts,
                        )
            except Exception as exc:
                logger.exception("Dispatch error for alert [%s]: %s", qa.alert.title, exc)
                results["failed"] += 1

        self._save()
        logger.info("Flush complete: %s", results)
        return results

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self, max_age_hours: int = 24) -> int:
        """Remove old dispatched or failed alerts from the queue.

        Args:
            max_age_hours: Remove entries older than this.

        Returns:
            Number of entries removed.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        original_len = len(self._queue)

        self._queue = [
            qa for qa in self._queue
            if not (qa.dispatched or qa.is_failed)
            or datetime.fromisoformat(qa.queued_at) > cutoff
        ]

        removed = original_len - len(self._queue)
        if removed > 0:
            self._save()
            logger.info("Cleaned up %d old queue entries", removed)
        return removed

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_pending_count(self) -> int:
        """Return the number of undispatched, non-failed alerts."""
        return sum(1 for qa in self._queue if not qa.dispatched and not qa.is_failed)

    def get_queue_stats(self) -> Dict[str, Any]:
        """Return queue statistics."""
        pending = sum(1 for qa in self._queue if not qa.dispatched and not qa.is_failed)
        dispatched = sum(1 for qa in self._queue if qa.dispatched)
        failed = sum(1 for qa in self._queue if qa.is_failed)
        return {
            "total": len(self._queue),
            "pending": pending,
            "dispatched": dispatched,
            "failed": failed,
            "oldest_pending": self._oldest_pending_iso(),
        }

    def _oldest_pending_iso(self) -> Optional[str]:
        """Return the queued_at timestamp of the oldest pending alert."""
        pending_times = [
            qa.queued_at for qa in self._queue
            if not qa.dispatched and not qa.is_failed
        ]
        return min(pending_times) if pending_times else None

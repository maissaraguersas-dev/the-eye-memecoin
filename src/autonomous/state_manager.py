"""
THE EYE — Memecoin Pattern Recognition System
State Manager Module

Manages persistent state files (WORKFLOW_STATE.md, watchlist.json,
alert_queue.json, prediction_log.json, learning_db.json) under src/data/.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("the-eye.state-manager")

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# WorkflowState dataclass
# ---------------------------------------------------------------------------

@dataclass
class WorkflowState:
    """Represents the current state of the monitoring workflow."""

    status: str = "idle"                               # idle | running | paused | error
    last_scan_times: Dict[str, str] = field(default_factory=dict)
    active_tasks: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowState":
        return cls(
            status=d.get("status", "idle"),
            last_scan_times=d.get("last_scan_times", {}),
            active_tasks=d.get("active_tasks", []),
            last_updated=d.get("last_updated", datetime.now(timezone.utc).isoformat()),
        )


# ---------------------------------------------------------------------------
# StateManager
# ---------------------------------------------------------------------------

class StateManager:
    """Reads and writes all persistent state files in src/data/."""

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self.state_dir = Path(state_dir) if state_dir else DATA_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Canonical file paths
        self._workflow_state_path = self.state_dir / "WORKFLOW_STATE.md"
        self._watchlist_path = self.state_dir / "watchlist.json"
        self._alert_queue_path = self.state_dir / "alert_queue.json"
        self._prediction_log_path = self.state_dir / "prediction_log.json"
        self._learning_db_path = self.state_dir / "learning_db.json"

    # ------------------------------------------------------------------
    # Internal I/O helpers
    # ------------------------------------------------------------------

    def _read_json(self, path: Path, default: Any = None) -> Any:
        """Read a JSON file; return *default* if missing / corrupt."""
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read %s: %s", path, exc)
            return default

    def _write_json(self, path: Path, data: Any) -> None:
        """Atomically-ish write a JSON file with pretty-printing."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
        except OSError as exc:
            logger.error("Failed to write %s: %s", path, exc)
            raise

    # ------------------------------------------------------------------
    # WORKFLOW_STATE.md
    # ------------------------------------------------------------------

    def get_workflow_state(self) -> WorkflowState:
        """Read WORKFLOW_STATE.md and return a WorkflowState object.

        The file is a simple markdown document with a JSON code block.
        If the file doesn't exist, return a default idle state.
        """
        if not self._workflow_state_path.exists():
            return WorkflowState()

        try:
            text = self._workflow_state_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Cannot read WORKFLOW_STATE.md: %s", exc)
            return WorkflowState()

        # Extract JSON from ```json ... ``` block
        json_str = self._extract_json_block(text)
        if json_str is None:
            return WorkflowState()

        try:
            data = json.loads(json_str)
            return WorkflowState.from_dict(data)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON in WORKFLOW_STATE.md: %s", exc)
            return WorkflowState()

    def update_workflow_state(self, state: WorkflowState) -> None:
        """Write WorkflowState to WORKFLOW_STATE.md as a markdown document."""
        state.last_updated = datetime.now(timezone.utc).isoformat()
        data = state.to_dict()
        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        content = (
            "# THE EYE — Workflow State\n\n"
            f"**Last Updated:** {state.last_updated}\n\n"
            f"**Status:** {state.status}\n\n"
            f"**Active Tasks:** {', '.join(state.active_tasks) or 'none'}\n\n"
            "```json\n"
            f"{json_str}\n"
            "```\n"
        )

        try:
            self._workflow_state_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to write WORKFLOW_STATE.md: %s", exc)
            raise

    @staticmethod
    def _extract_json_block(text: str) -> Optional[str]:
        """Extract content from the first ```json ... ``` block."""
        marker = "```json"
        start = text.find(marker)
        if start == -1:
            return None
        start += len(marker)
        end = text.find("```", start)
        if end == -1:
            return None
        return text[start:end].strip()

    # ------------------------------------------------------------------
    # watchlist.json
    # ------------------------------------------------------------------

    def get_watchlist(self) -> List[Dict[str, Any]]:
        """Read watchlist.json and return a list of token dicts."""
        return self._read_json(self._watchlist_path, default=[])

    def update_watchlist(self, tokens: List[Dict[str, Any]]) -> None:
        """Write watchlist.json."""
        self._write_json(self._watchlist_path, tokens)

    # ------------------------------------------------------------------
    # alert_queue.json
    # ------------------------------------------------------------------

    def get_alert_queue(self) -> List[Dict[str, Any]]:
        """Read alert_queue.json and return a list of queued alert dicts."""
        return self._read_json(self._alert_queue_path, default=[])

    def update_alert_queue(self, queue: List[Dict[str, Any]]) -> None:
        """Write alert_queue.json."""
        self._write_json(self._alert_queue_path, queue)

    # ------------------------------------------------------------------
    # prediction_log.json
    # ------------------------------------------------------------------

    def get_prediction_log(self) -> List[Dict[str, Any]]:
        """Read prediction_log.json and return a list of prediction dicts."""
        return self._read_json(self._prediction_log_path, default=[])

    def append_prediction(self, prediction: Dict[str, Any]) -> None:
        """Append a single prediction dict to prediction_log.json."""
        log = self.get_prediction_log()
        # Ensure timestamp
        if "timestamp" not in prediction:
            prediction["timestamp"] = datetime.now(timezone.utc).isoformat()
        log.append(prediction)
        self._write_json(self._prediction_log_path, log)

    # ------------------------------------------------------------------
    # learning_db.json
    # ------------------------------------------------------------------

    def get_learning_db(self) -> Dict[str, Any]:
        """Read learning_db.json and return the learning database dict."""
        return self._read_json(self._learning_db_path, default={"patterns": {}, "stats": {}})

    def update_learning_db(self, db: Dict[str, Any]) -> None:
        """Write learning_db.json."""
        self._write_json(self._learning_db_path, db)

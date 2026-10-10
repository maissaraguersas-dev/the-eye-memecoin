"""
THE EYE — Memecoin Pattern Recognition System
Cron Scheduler Module

Provides 24/7 scheduling for monitoring agents with default jobs:
  - blockchain-scan  (5 min)
  - social-scan      (10 min)
  - market-scan      (15 min)
  - temporal-scan    (30 min)
  - alert-dispatch   (60 min)

Supports one-shot cycle execution and a continuous run loop.
"""

from __future__ import annotations

import logging
import signal
import time
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional

from .state_manager import StateManager, WorkflowState
from .watchlist_manager import WatchlistManager
from .alert_queue import AlertQueue

logger = logging.getLogger("the-eye.cron-scheduler")


# ---------------------------------------------------------------------------
# CronJob dataclass
# ---------------------------------------------------------------------------

@dataclass
class CronJob:
    """A scheduled monitoring job."""

    name: str
    interval_minutes: int
    agent_name: str
    last_run: Optional[str] = None
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CronJob":
        return cls(
            name=d.get("name", ""),
            interval_minutes=int(d.get("interval_minutes", 5)),
            agent_name=d.get("agent_name", ""),
            last_run=d.get("last_run"),
            enabled=d.get("enabled", True),
        )

    def is_due(self) -> bool:
        """Return True if this job is scheduled to run now."""
        if not self.enabled:
            return False
        if self.last_run is None:
            return True
        try:
            last = datetime.fromisoformat(self.last_run)
            next_run = last + timedelta(minutes=self.interval_minutes)
            return datetime.now(timezone.utc) >= next_run
        except (ValueError, TypeError):
            return True


# ---------------------------------------------------------------------------
# Default jobs
# ---------------------------------------------------------------------------

DEFAULT_JOBS: List[Dict[str, Any]] = [
    {"name": "blockchain-scan",  "interval_minutes": 5,  "agent_name": "whale-tracker"},
    {"name": "social-scan",      "interval_minutes": 10, "agent_name": "social-sentiment"},
    {"name": "market-scan",      "interval_minutes": 15, "agent_name": "pump-detector"},
    {"name": "temporal-scan",    "interval_minutes": 30, "agent_name": "temporal-scanner"},
    {"name": "alert-dispatch",   "interval_minutes": 60, "agent_name": "alert-dispatcher"},
]


# ---------------------------------------------------------------------------
# Agent execution registry
# ---------------------------------------------------------------------------

# Each agent function signature: (watchlist_manager, alert_queue, state_manager) -> dict
# Users register their own implementations via register_agent().

_AGENT_REGISTRY: Dict[str, Callable] = {}


def register_agent(name: str, func: Callable) -> None:
    """Register a callable to be invoked when a job with *agent_name* executes."""
    _AGENT_REGISTRY[name] = func
    logger.info("Registered agent: %s", name)


# ---------------------------------------------------------------------------
# CronScheduler
# ---------------------------------------------------------------------------

class CronScheduler:
    """Schedules and executes monitoring agent jobs on a recurring basis."""

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        watchlist_manager: Optional[WatchlistManager] = None,
        alert_queue: Optional[AlertQueue] = None,
    ) -> None:
        self.state_manager = state_manager or StateManager()
        self.watchlist_manager = watchlist_manager or WatchlistManager(
            state_manager=self.state_manager,
        )
        self.alert_queue = alert_queue or AlertQueue()

        self._jobs: Dict[str, CronJob] = {}
        self._running = False
        self._lock = threading.Lock()

        # Load default jobs
        self._load_default_jobs()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _load_default_jobs(self) -> None:
        """Populate the default job set (idempotent)."""
        for jd in DEFAULT_JOBS:
            job = CronJob.from_dict(jd)
            if job.name not in self._jobs:
                self._jobs[job.name] = job
        logger.info("Loaded %d default jobs", len(DEFAULT_JOBS))

    # ------------------------------------------------------------------
    # Job CRUD
    # ------------------------------------------------------------------

    def add_job(
        self,
        name: str,
        interval_minutes: int,
        agent_name: str,
        enabled: bool = True,
    ) -> CronJob:
        """Add (or replace) a cron job."""
        job = CronJob(
            name=name,
            interval_minutes=interval_minutes,
            agent_name=agent_name,
            enabled=enabled,
        )
        self._jobs[name] = job
        logger.info("Added job %s — interval %d min, agent %s", name, interval_minutes, agent_name)
        return job

    def remove_job(self, name: str) -> bool:
        """Remove a cron job by name. Returns True if removed."""
        if name in self._jobs:
            del self._jobs[name]
            logger.info("Removed job %s", name)
            return True
        logger.warning("Job %s not found", name)
        return False

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def get_jobs_due(self) -> List[CronJob]:
        """Return all jobs that are due for execution."""
        return [j for j in self._jobs.values() if j.is_due()]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_job(self, job: CronJob) -> Dict[str, Any]:
        """Execute a single monitoring job.

        Looks up the registered agent function and calls it with the
        watchlist_manager, alert_queue, and state_manager. If no agent
        is registered, logs a warning and returns a no-op result.

        Returns:
            Dict with keys: job, success, result, error, executed_at
        """
        now = datetime.now(timezone.utc).isoformat()
        result_info: Dict[str, Any] = {
            "job": job.name,
            "agent": job.agent_name,
            "success": False,
            "result": None,
            "error": None,
            "executed_at": now,
        }

        agent_func = _AGENT_REGISTRY.get(job.agent_name)
        if agent_func is None:
            msg = f"No agent registered for '{job.agent_name}' — skipping"
            logger.warning(msg)
            result_info["error"] = msg
            # Still mark as run so we don't hammer the log
            job.last_run = now
            return result_info

        try:
            logger.info("Executing job %s (agent: %s)", job.name, job.agent_name)
            result = agent_func(
                watchlist_manager=self.watchlist_manager,
                alert_queue=self.alert_queue,
                state_manager=self.state_manager,
            )
            job.last_run = now
            result_info["success"] = True
            result_info["result"] = result
            logger.info("Job %s completed successfully", job.name)
        except Exception as exc:
            logger.exception("Job %s failed", job.name)
            result_info["error"] = str(exc)
            job.last_run = now  # still mark so we respect the interval

        return result_info

    # ------------------------------------------------------------------
    # Run cycle
    # ------------------------------------------------------------------

    def run_cycle(self) -> List[Dict[str, Any]]:
        """Run one cycle: execute all due jobs, update workflow state.

        Returns:
            List of result dicts from each executed job.
        """
        due = self.get_jobs_due()
        if not due:
            logger.debug("No jobs due this cycle")
            return []

        logger.info("Cycle: %d jobs due", len(due))
        results: List[Dict[str, Any]] = []

        # Update workflow state to running
        ws = self.state_manager.get_workflow_state()
        ws.status = "running"
        ws.active_tasks = [j.name for j in due]
        self.state_manager.update_workflow_state(ws)

        for job in due:
            result = self.execute_job(job)
            results.append(result)

        # Update workflow state
        ws = self.state_manager.get_workflow_state()
        ws.active_tasks = []
        ws.status = "idle"
        self.state_manager.update_workflow_state(ws)

        return results

    # ------------------------------------------------------------------
    # Continuous loop
    # ------------------------------------------------------------------

    def run_continuous(self, interval_seconds: int = 30) -> None:
        """Run the scheduler in a continuous loop.

        Args:
            interval_seconds: How often to check for due jobs.

        The loop runs until interrupted (SIGINT / SIGTERM) or
        ``stop()`` is called from another thread.
        """
        self._running = True

        # Graceful shutdown on signals
        def _signal_handler(signum: int, frame: Any) -> None:
            logger.info("Received signal %d — stopping scheduler", signum)
            self._running = False

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        logger.info(
            "Scheduler started — checking every %d s. Press Ctrl+C to stop.",
            interval_seconds,
        )

        # Update workflow state
        ws = self.state_manager.get_workflow_state()
        ws.status = "running"
        self.state_manager.update_workflow_state(ws)

        while self._running:
            try:
                self.run_cycle()
            except Exception as exc:
                logger.exception("Unexpected error in run_cycle: %s", exc)

            # Sleep in small increments so we can respond to stop() quickly
            slept = 0.0
            while slept < interval_seconds and self._running:
                time.sleep(min(1.0, interval_seconds - slept))
                slept += 1.0

        # Clean exit
        ws = self.state_manager.get_workflow_state()
        ws.status = "idle"
        ws.active_tasks = []
        self.state_manager.update_workflow_state(ws)
        logger.info("Scheduler stopped")

    def stop(self) -> None:
        """Signal the continuous loop to stop."""
        self._running = False
        logger.info("Stop requested")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_job_status(self) -> List[Dict[str, Any]]:
        """Return the status of all jobs."""
        now = datetime.now(timezone.utc)
        statuses: List[Dict[str, Any]] = []
        for job in self._jobs.values():
            status_entry: Dict[str, Any] = {
                "name": job.name,
                "agent": job.agent_name,
                "interval_minutes": job.interval_minutes,
                "enabled": job.enabled,
                "last_run": job.last_run,
                "due_now": job.is_due(),
            }
            # Compute next run time
            if job.last_run:
                try:
                    last = datetime.fromisoformat(job.last_run)
                    next_run = last + timedelta(minutes=job.interval_minutes)
                    status_entry["next_run"] = next_run.isoformat()
                    status_entry["seconds_until_next"] = max(0, (next_run - now).total_seconds())
                except (ValueError, TypeError):
                    status_entry["next_run"] = None
                    status_entry["seconds_until_next"] = 0
            else:
                status_entry["next_run"] = now.isoformat()
                status_entry["seconds_until_next"] = 0

            statuses.append(status_entry)

        return statuses

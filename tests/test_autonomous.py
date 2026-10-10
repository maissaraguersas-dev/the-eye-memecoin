"""
Tests for autonomous modules — WatchlistManager, AlertQueue,
StateManager, and CronScheduler.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.autonomous.watchlist_manager import WatchlistManager, WatchlistEntry
from src.autonomous.alert_queue import AlertQueue, QueuedAlert, MAX_DISPATCH_ATTEMPTS
from src.autonomous.state_manager import StateManager, WorkflowState
from src.autonomous.cron_scheduler import CronScheduler, CronJob, DEFAULT_JOBS
from src.alerts.formatter import Alert, AlertType, Urgency


# ─── WatchlistManager ────────────────────────────────────────────────────────

class TestWatchlistAddRemove:
    def test_watchlist_add(self, tmp_path):
        """Add a token to the watchlist."""
        wl_path = tmp_path / "watchlist.json"
        wl_path.write_text("[]")
        sm = StateManager(state_dir=str(tmp_path))
        mgr = WatchlistManager(watchlist_path=str(wl_path), state_manager=sm)

        entry = mgr.add_token("PEPE", "0xpepe", "eth", reason="Whale detected")
        assert entry.token == "PEPE"
        assert entry.chain == "eth"
        assert mgr.is_watched("PEPE") is True

    def test_watchlist_remove(self, tmp_path):
        """Remove a token from the watchlist."""
        wl_path = tmp_path / "watchlist.json"
        wl_path.write_text("[]")
        sm = StateManager(state_dir=str(tmp_path))
        mgr = WatchlistManager(watchlist_path=str(wl_path), state_manager=sm)

        mgr.add_token("PEPE", "0xpepe", "eth")
        removed = mgr.remove_token("PEPE")
        assert removed is True
        assert mgr.is_watched("PEPE") is False

    def test_watchlist_remove_nonexistent(self, tmp_path):
        """Removing a non-existent token returns False."""
        wl_path = tmp_path / "watchlist.json"
        wl_path.write_text("[]")
        sm = StateManager(state_dir=str(tmp_path))
        mgr = WatchlistManager(watchlist_path=str(wl_path), state_manager=sm)
        assert mgr.remove_token("NOTEXIST") is False

    def test_watchlist_list_tokens(self, tmp_path):
        """List all tokens in the watchlist."""
        wl_path = tmp_path / "watchlist.json"
        wl_path.write_text("[]")
        sm = StateManager(state_dir=str(tmp_path))
        mgr = WatchlistManager(watchlist_path=str(wl_path), state_manager=sm)

        mgr.add_token("PEPE", "0xpepe", "eth")
        mgr.add_token("DOGE", "0xdoge", "eth")
        tokens = mgr.list_tokens()
        assert len(tokens) == 2
        names = {t.token for t in tokens}
        assert names == {"PEPE", "DOGE"}


class TestWatchlistDueForScan:
    def test_watchlist_due_for_scan_new(self, tmp_path):
        """Newly added token with no last_scanned_at is due."""
        wl_path = tmp_path / "watchlist.json"
        wl_path.write_text("[]")
        sm = StateManager(state_dir=str(tmp_path))
        mgr = WatchlistManager(watchlist_path=str(wl_path), state_manager=sm)

        mgr.add_token("PEPE", "0xpepe", "eth", scan_interval=5)
        due = mgr.get_tokens_due_for_scan()
        assert len(due) == 1

    def test_watchlist_due_for_scan_recently_scanned(self, tmp_path):
        """Token scanned within interval is NOT due."""
        wl_path = tmp_path / "watchlist.json"
        wl_path.write_text("[]")
        sm = StateManager(state_dir=str(tmp_path))
        mgr = WatchlistManager(watchlist_path=str(wl_path), state_manager=sm)

        mgr.add_token("PEPE", "0xpepe", "eth", scan_interval=60)
        mgr.update_scan_time("PEPE")  # just scanned
        due = mgr.get_tokens_due_for_scan()
        assert len(due) == 0


# ─── AlertQueue ──────────────────────────────────────────────────────────────

class TestAlertQueueEnqueueDequeue:
    def test_alert_queue_enqueue(self, tmp_path):
        """Enqueue an alert adds it to the queue."""
        q_path = tmp_path / "alert_queue.json"
        q_path.write_text("[]")
        queue = AlertQueue(queue_path=str(q_path), dispatcher=MagicMock())

        alert = Alert(alert_type=AlertType.WHALE, token="PEPE", what="Whale buy", confidence=80, urgency=Urgency.HIGH)
        qa = queue.enqueue(alert)
        assert qa.dispatched is False
        assert queue.get_pending_count() == 1

    def test_alert_queue_dequeue(self, tmp_path):
        """Dequeue returns pending alerts in FIFO order."""
        q_path = tmp_path / "alert_queue.json"
        q_path.write_text("[]")
        queue = AlertQueue(queue_path=str(q_path), dispatcher=MagicMock())

        a1 = Alert(alert_type=AlertType.WHALE, token="PEPE", what="Whale buy", confidence=80, urgency=Urgency.HIGH)
        a2 = Alert(alert_type=AlertType.RUG, token="SCAM", what="Rug detected", confidence=90, urgency=Urgency.CRITICAL)
        queue.enqueue(a1)
        queue.enqueue(a2)

        pending = queue.dequeue(limit=10)
        assert len(pending) == 2

    def test_alert_queue_mark_dispatched(self, tmp_path):
        """Mark dispatched removes alert from pending."""
        q_path = tmp_path / "alert_queue.json"
        q_path.write_text("[]")
        queue = AlertQueue(queue_path=str(q_path), dispatcher=MagicMock())

        alert = Alert(alert_type=AlertType.WHALE, token="PEPE", what="Whale buy", confidence=80, urgency=Urgency.HIGH)
        qa = queue.enqueue(alert)
        queue.mark_dispatched(alert.id)
        assert queue.get_pending_count() == 0


class TestAlertQueueFlush:
    def test_alert_queue_flush(self, tmp_path):
        """Flush dispatches all pending alerts."""
        q_path = tmp_path / "alert_queue.json"
        q_path.write_text("[]")

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = [
            MagicMock(success=True, channel="log")
        ]

        queue = AlertQueue(queue_path=str(q_path), dispatcher=mock_dispatcher)

        alert = Alert(alert_type=AlertType.WHALE, token="PEPE", what="Whale buy", confidence=80, urgency=Urgency.HIGH)
        queue.enqueue(alert)

        results = queue.flush()
        assert results["attempted"] >= 1
        assert results["succeeded"] >= 1


# ─── StateManager ────────────────────────────────────────────────────────────

class TestStateManagerWorkflow:
    def test_state_manager_read_write(self, tmp_path):
        """Read and write WORKFLOW_STATE through StateManager."""
        sm = StateManager(state_dir=str(tmp_path))

        # Write
        ws = WorkflowState(status="running", active_tasks=["blockchain-scan"])
        sm.update_workflow_state(ws)

        # Read back
        ws2 = sm.get_workflow_state()
        assert ws2.status == "running"
        assert "blockchain-scan" in ws2.active_tasks

    def test_state_manager_default_state(self, tmp_path):
        """Default state is idle with no tasks."""
        sm = StateManager(state_dir=str(tmp_path))
        ws = sm.get_workflow_state()
        assert ws.status == "idle"

    def test_state_manager_watchlist(self, tmp_path):
        """Read and write watchlist through StateManager."""
        sm = StateManager(state_dir=str(tmp_path))
        sm.update_watchlist([{"token": "PEPE", "address": "0xpepe", "chain": "eth"}])
        wl = sm.get_watchlist()
        assert len(wl) == 1
        assert wl[0]["token"] == "PEPE"

    def test_state_manager_prediction_log(self, tmp_path):
        """Append predictions to the log."""
        sm = StateManager(state_dir=str(tmp_path))
        sm.append_prediction({"token": "PEPE", "action": "buy", "confidence": 80})
        sm.append_prediction({"token": "DOGE", "action": "sell", "confidence": 60})
        log = sm.get_prediction_log()
        assert len(log) == 2


# ─── CronScheduler ───────────────────────────────────────────────────────────

class TestCronSchedulerJobs:
    def test_cron_scheduler_default_jobs(self, tmp_path):
        """Default job setup creates all 5 monitoring jobs."""
        sm = StateManager(state_dir=str(tmp_path))
        scheduler = CronScheduler(state_manager=sm)
        assert len(scheduler._jobs) == 5
        job_names = set(scheduler._jobs.keys())
        assert job_names == {
            "blockchain-scan", "social-scan", "market-scan",
            "temporal-scan", "alert-dispatch",
        }

    def test_cron_scheduler_job_intervals(self, tmp_path):
        """Default jobs have correct intervals."""
        sm = StateManager(state_dir=str(tmp_path))
        scheduler = CronScheduler(state_manager=sm)

        assert scheduler._jobs["blockchain-scan"].interval_minutes == 5
        assert scheduler._jobs["social-scan"].interval_minutes == 10
        assert scheduler._jobs["market-scan"].interval_minutes == 15
        assert scheduler._jobs["temporal-scan"].interval_minutes == 30
        assert scheduler._jobs["alert-dispatch"].interval_minutes == 60

    def test_cron_scheduler_add_remove_job(self, tmp_path):
        """Add and remove custom jobs."""
        sm = StateManager(state_dir=str(tmp_path))
        scheduler = CronScheduler(state_manager=sm)

        job = scheduler.add_job("custom-scan", interval_minutes=2, agent_name="custom-agent")
        assert "custom-scan" in scheduler._jobs

        removed = scheduler.remove_job("custom-scan")
        assert removed is True
        assert "custom-scan" not in scheduler._jobs


class TestCronSchedulerDueJobs:
    def test_cron_scheduler_due_jobs_initial(self, tmp_path):
        """All jobs are due initially (never run)."""
        sm = StateManager(state_dir=str(tmp_path))
        scheduler = CronScheduler(state_manager=sm)
        due = scheduler.get_jobs_due()
        assert len(due) == 5

    def test_cron_scheduler_due_jobs_after_run(self, tmp_path):
        """After a job runs, it's not due until interval passes."""
        sm = StateManager(state_dir=str(tmp_path))
        scheduler = CronScheduler(state_manager=sm)

        # Simulate all jobs just ran
        now = datetime.now(timezone.utc).isoformat()
        for job in scheduler._jobs.values():
            job.last_run = now

        due = scheduler.get_jobs_due()
        assert len(due) == 0

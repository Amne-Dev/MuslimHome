"""Scheduling utilities for triggering Adhan playback and daily refreshes."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Iterable, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from prayer_times import PrayerInfo

LOGGER = logging.getLogger(__name__)


class PrayerScheduler:
    """Wrap APScheduler to manage one-off prayer event jobs."""

    def __init__(self, timezone: str) -> None:
        self._scheduler = BackgroundScheduler(timezone=timezone)
        self._jobs: List[str] = []
        self._refresh_job_id: Optional[str] = None

    def start(self) -> None:
        if not self._scheduler.running:
            LOGGER.info("Starting background scheduler")
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            LOGGER.info("Stopping background scheduler")
            self._scheduler.shutdown(wait=False)

    @property
    def timezone(self) -> str:
        tzinfo = self._scheduler.timezone
        zone = getattr(tzinfo, "zone", None)
        return str(zone or tzinfo)

    def schedule_prayers(self, prayers: Iterable[PrayerInfo], callback: Callable[[str], None]) -> None:
        """Schedule callbacks for each upcoming prayer time."""
        self._clear_prayer_jobs()

        now = datetime.now(self._scheduler.timezone)
        for info in prayers:
            if info.time <= now:
                continue
            trigger = DateTrigger(run_date=info.time)
            job = self._scheduler.add_job(callback, trigger=trigger, args=[info.name])
            LOGGER.debug("Scheduled prayer job %s at %s", job.id, info.time)
            self._jobs.append(job.id)

    def schedule_refresh(self, next_run: datetime, refresh_callback: Callable[[], None]) -> None:
        """Schedule a single refresh job, replacing any existing one."""
        if self._refresh_job_id:
            LOGGER.debug("Removing existing refresh job %s", self._refresh_job_id)
            self._scheduler.remove_job(self._refresh_job_id)
            self._refresh_job_id = None

        trigger = DateTrigger(run_date=next_run)
        job = self._scheduler.add_job(refresh_callback, trigger=trigger)
        LOGGER.debug("Scheduled refresh job %s at %s", job.id, next_run)
        self._refresh_job_id = job.id

    def _clear_prayer_jobs(self) -> None:
        for job_id in self._jobs:
            with suppress_not_found():
                self._scheduler.remove_job(job_id)
        self._jobs.clear()


class suppress_not_found:
    """Context manager that suppresses APScheduler job lookup errors."""

    def __enter__(self) -> None:  # pragma: no cover - trivial
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:  # pragma: no cover - trivial
        from apscheduler.jobstores.base import JobLookupError

        if exc_type is None:
            return False
        return isinstance(exc, JobLookupError)

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from campus_ai.config import get_settings
from campus_ai.db import SessionLocal
from campus_ai.jobs import enqueue_job


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def enqueue_daily_fetch() -> None:
    settings = get_settings()
    today = datetime.now(ZoneInfo(settings.timezone)).date().isoformat()
    with SessionLocal() as session:
        job = enqueue_job(
            session,
            kind="fetch_all",
            payload={"run_key": today},
            dedupe_key=f"fetch-all:{today}",
            max_attempts=3,
        )
        logger.info("daily_fetch_enqueued job_id=%s run_key=%s", job.id, today)


def run() -> None:
    settings = get_settings()
    scheduler = BlockingScheduler(timezone=settings.timezone)
    scheduler.add_job(
        enqueue_daily_fetch,
        "cron",
        hour=settings.daily_fetch_hour,
        minute=settings.daily_fetch_minute,
        id="daily-fetch",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=3600,
    )
    logger.info(
        "scheduler_started timezone=%s schedule=%02d:%02d",
        settings.timezone,
        settings.daily_fetch_hour,
        settings.daily_fetch_minute,
    )
    scheduler.start()


if __name__ == "__main__":
    run()

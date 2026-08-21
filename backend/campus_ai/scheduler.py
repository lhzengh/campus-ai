from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

from campus_ai.config import get_settings
from campus_ai.db import SessionLocal
from campus_ai.jobs import enqueue_job
from campus_ai.models import Source, utcnow
from campus_ai.scheduling import as_utc, next_daily_run


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def process_due_sources(session: Session, *, now: datetime | None = None) -> dict[str, int]:
    """Queue each due source once and advance it to its next future slot."""

    current = as_utc(now or utcnow())
    sources = session.scalars(
        select(Source).where(
            Source.enabled.is_(True),
            Source.archived_at.is_(None),
            Source.schedule_mode == "daily",
        )
    ).all()
    queued = 0
    initialized = 0
    for source in sources:
        if source.next_run_at is None:
            source.next_run_at = next_daily_run(
                source.schedule_time,
                source.schedule_timezone,
                after=current,
            )
            initialized += 1
            continue
        scheduled_for = as_utc(source.next_run_at)
        if scheduled_for > current:
            continue
        enqueue_job(
            session,
            kind="sync_source",
            payload={"source_id": source.id, "scheduled_for": scheduled_for.isoformat()},
            dedupe_key=f"scheduled-sync:{source.id}:{scheduled_for.isoformat()}",
            max_attempts=3,
        )
        source.next_run_at = next_daily_run(
            source.schedule_time,
            source.schedule_timezone,
            after=current,
        )
        queued += 1
    session.commit()
    return {"queued": queued, "initialized": initialized}


def enqueue_due_sources() -> None:
    """Run one short database-backed scheduling tick."""

    with SessionLocal() as session:
        result = process_due_sources(session)
    if result["queued"] or result["initialized"]:
        logger.info(
            "source_schedule_tick queued=%s initialized=%s",
            result["queued"],
            result["initialized"],
        )


def run() -> None:
    settings = get_settings()
    scheduler = BlockingScheduler(timezone=settings.timezone)
    scheduler.add_job(
        enqueue_due_sources,
        "interval",
        minutes=1,
        id="source-schedule-scan",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,
    )
    logger.info(
        "scheduler_started timezone=%s interval=60s legacy_default=%02d:%02d",
        settings.timezone,
        settings.daily_fetch_hour,
        settings.daily_fetch_minute,
    )
    scheduler.start()


if __name__ == "__main__":
    run()

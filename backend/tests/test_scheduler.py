from __future__ import annotations

from datetime import datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from campus_ai.models import Job, Source
from campus_ai.scheduler import process_due_sources
from campus_ai.scheduling import next_daily_run


def test_next_daily_run_respects_the_source_timezone() -> None:
    after = datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc)

    result = next_daily_run(time(9, 0), "Asia/Shanghai", after=after)

    assert result == datetime(2026, 8, 21, 1, 0, tzinfo=timezone.utc)


def test_scheduler_initializes_then_queues_each_due_slot_once(session: Session) -> None:
    now = datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc)
    source = Source(
        name="daily",
        connector_id="example.static",
        enabled=True,
        schedule_mode="daily",
        schedule_time=time(7, 0),
        schedule_timezone="UTC",
    )
    session.add(source)
    session.commit()

    initialized = process_due_sources(session, now=now)
    assert initialized == {"queued": 0, "initialized": 1}
    source.next_run_at = datetime(2026, 8, 20, 7, 0, tzinfo=timezone.utc)
    session.commit()

    first = process_due_sources(session, now=now)
    second = process_due_sources(session, now=now)

    assert first == {"queued": 1, "initialized": 0}
    assert second == {"queued": 0, "initialized": 0}
    jobs = session.scalars(select(Job).where(Job.kind == "sync_source")).all()
    assert len(jobs) == 1
    assert source.next_run_at == datetime(2026, 8, 21, 7, 0, tzinfo=timezone.utc)


def test_scheduler_ignores_manual_disabled_and_archived_sources(session: Session) -> None:
    for name, enabled, mode, archived_at in (
        ("manual", True, "manual", None),
        ("disabled", False, "daily", None),
        ("archived", True, "daily", datetime(2026, 8, 20, tzinfo=timezone.utc)),
    ):
        session.add(
            Source(
                name=name,
                connector_id="example.static",
                enabled=enabled,
                schedule_mode=mode,
                schedule_time=time(7, 0),
                schedule_timezone="UTC",
                archived_at=archived_at,
            )
        )
    session.commit()

    result = process_due_sources(session, now=datetime(2026, 8, 21, tzinfo=timezone.utc))

    assert result == {"queued": 0, "initialized": 0}

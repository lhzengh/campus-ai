from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from campus_ai.jobs import claim_job, complete_job, enqueue_job, fail_job, recover_stale_jobs
from campus_ai.models import JobStatus, utcnow


def test_job_deduplication_and_completion(session: Session) -> None:
    first = enqueue_job(session, kind="example", payload={"value": 1}, dedupe_key="same")
    second = enqueue_job(session, kind="example", payload={"value": 2}, dedupe_key="same")

    assert first.id == second.id
    claimed = claim_job(session)
    assert claimed is not None
    assert claimed.status is JobStatus.running
    assert claimed.attempts == 1

    complete_job(session, claimed)
    assert claimed.status is JobStatus.succeeded


def test_job_retries_then_fails(session: Session) -> None:
    enqueue_job(session, kind="example", payload={}, dedupe_key="retry", max_attempts=2)
    first = claim_job(session)
    assert first is not None
    fail_job(session, first, RuntimeError("temporary"))
    first.available_at = utcnow() - timedelta(seconds=1)
    session.commit()

    second = claim_job(session)
    assert second is not None
    fail_job(session, second, RuntimeError("permanent"))
    assert second.status is JobStatus.failed
    assert "permanent" in (second.last_error or "")


def test_stale_running_job_is_recovered(session: Session) -> None:
    enqueue_job(session, kind="example", payload={}, dedupe_key="stale")
    job = claim_job(session)
    assert job is not None
    job.locked_at = utcnow() - timedelta(minutes=10)
    session.commit()

    assert recover_stale_jobs(session, lock_timeout_seconds=30) == 1
    session.refresh(job)
    assert job.status is JobStatus.pending
    assert job.locked_at is None

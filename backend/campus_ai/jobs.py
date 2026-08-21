from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from sqlalchemy import Select, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from campus_ai.models import Job, JobStatus, utcnow


def enqueue_job(
    session: Session,
    *,
    kind: str,
    payload: dict[str, object],
    dedupe_key: str,
    max_attempts: int = 3,
) -> Job:
    existing = session.scalar(select(Job).where(Job.dedupe_key == dedupe_key))
    if existing is not None:
        session.commit()
        return existing

    job = Job(kind=kind, payload=payload, dedupe_key=dedupe_key, max_attempts=max_attempts)
    session.add(job)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(select(Job).where(Job.dedupe_key == dedupe_key))
        if existing is None:
            raise
        return existing
    session.refresh(job)
    return job


def _claim_query(kinds: set[str] | None) -> Select[tuple[Job]]:
    query = (
        select(Job)
        .where(Job.status == JobStatus.pending, Job.available_at <= utcnow())
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if kinds:
        query = query.where(Job.kind.in_(kinds))
    return query


def claim_job(session: Session, kinds: set[str] | None = None) -> Job | None:
    job = session.scalar(_claim_query(kinds))
    if job is None:
        session.rollback()
        return None
    job.status = JobStatus.running
    job.attempts += 1
    job.locked_at = utcnow()
    job.last_error = None
    session.commit()
    session.refresh(job)
    return job


def complete_job(session: Session, job: Job) -> None:
    job.status = JobStatus.succeeded
    job.locked_at = None
    session.commit()


def fail_job(session: Session, job: Job, error: Exception) -> None:
    job.last_error = f"{type(error).__name__}: {error}"[:4000]
    job.locked_at = None
    if job.attempts >= job.max_attempts:
        job.status = JobStatus.failed
    else:
        job.status = JobStatus.pending
        job.available_at = utcnow() + timedelta(seconds=min(2**job.attempts, 300))
    session.commit()


def recover_stale_jobs(session: Session, lock_timeout_seconds: int) -> int:
    cutoff = utcnow() - timedelta(seconds=lock_timeout_seconds)
    result = session.execute(
        update(Job)
        .where(Job.status == JobStatus.running, Job.locked_at < cutoff)
        .values(status=JobStatus.pending, locked_at=None, available_at=utcnow(), last_error="Recovered stale lock")
    )
    session.commit()
    return result.rowcount or 0


def list_jobs(session: Session, limit: int = 100) -> Iterable[Job]:
    return session.scalars(select(Job).order_by(Job.created_at.desc()).limit(limit)).all()

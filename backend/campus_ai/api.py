from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from campus_ai import __version__
from campus_ai.db import get_session
from campus_ai.jobs import enqueue_job, list_jobs
from campus_ai.models import Job, JobStatus, Message
from campus_ai.schemas import JobCreate, JobView, MessageView


app = FastAPI(title="Campus AI Validation API", version=__version__)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/health/ready")
def ready(session: Session = Depends(get_session)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.post("/v1/jobs", response_model=JobView, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, session: Session = Depends(get_session)) -> Job:
    return enqueue_job(
        session,
        kind=payload.kind,
        payload=payload.payload,
        dedupe_key=payload.dedupe_key,
        max_attempts=payload.max_attempts,
    )


@app.get("/v1/jobs", response_model=list[JobView])
def jobs(limit: int = Query(default=100, ge=1, le=500), session: Session = Depends(get_session)) -> list[Job]:
    return list(list_jobs(session, limit=limit))


@app.post("/v1/jobs/{job_id}/retry", response_model=JobView)
def retry_job(job_id: str, session: Session = Depends(get_session)) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobStatus.pending
    job.last_error = None
    session.commit()
    session.refresh(job)
    return job


@app.get("/v1/messages", response_model=list[MessageView])
def messages(limit: int = Query(default=50, ge=1, le=200), session: Session = Depends(get_session)) -> list[Message]:
    return list(session.scalars(select(Message).order_by(Message.fetched_at.desc()).limit(limit)).all())

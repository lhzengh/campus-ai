from __future__ import annotations

from sqlalchemy.orm import Session

from campus_ai.api import app, create_job, jobs, live, ready
from campus_ai.schemas import JobCreate


def test_health_and_job_api(session: Session) -> None:
    assert live()["status"] == "ok"
    assert ready(session) == {"status": "ready"}
    created = create_job(
        JobCreate(
            kind="fetch_all",
            payload={"run_key": "2026-08-19"},
            dedupe_key="fetch-all:2026-08-19",
        ),
        session,
    )
    assert created.status.value == "pending"
    listed = jobs(limit=100, session=session)
    assert len(listed) == 1
    assert listed[0].dedupe_key == "fetch-all:2026-08-19"

    paths = app.openapi()["paths"]
    assert "/health/live" in paths
    assert "/v1/jobs" in paths

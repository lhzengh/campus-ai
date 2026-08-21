from __future__ import annotations

from datetime import time
from uuid import uuid4

from campus_connector_sdk import AuthResult, ConnectorErrorCode
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from campus_ai import __version__
from campus_ai.config import get_settings
from campus_ai.connectors import ConnectorClient, ConnectorClientError, ConnectorEndpointRegistry, get_connector_registry
from campus_ai.db import get_session
from campus_ai.jobs import enqueue_job, list_jobs
from campus_ai.models import Job, JobStatus, Message, Source, utcnow
from campus_ai.scheduling import next_daily_run
from campus_ai.schemas import (
    ConnectorRegistrationView,
    JobCreate,
    JobView,
    MessageView,
    SourceAuthResponse,
    SourceCheckResult,
    SourceCreate,
    SourceSchedule,
    SourceUpdate,
    SourceView,
)


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


@app.get("/v1/jobs/{job_id}", response_model=JobView)
def job(job_id: str, session: Session = Depends(get_session)) -> Job:
    """Return one job so clients can poll a manual synchronization safely."""

    value = session.get(Job, job_id)
    if value is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return value


@app.post("/v1/jobs/{job_id}/retry", response_model=JobView)
def retry_job(job_id: str, session: Session = Depends(get_session)) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobStatus.pending
    job.started_at = None
    job.finished_at = None
    job.result = {}
    job.last_error = None
    session.commit()
    session.refresh(job)
    return job


@app.get("/v1/messages", response_model=list[MessageView])
def messages(limit: int = Query(default=50, ge=1, le=200), session: Session = Depends(get_session)) -> list[Message]:
    return list(session.scalars(select(Message).order_by(Message.fetched_at.desc()).limit(limit)).all())


def _connector_http_error(exc: Exception) -> HTTPException:
    """Translate internal Connector failures into safe Client API errors."""

    if isinstance(exc, ConnectorClientError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_422_UNPROCESSABLE_ENTITY
        return HTTPException(status_code=status_code, detail={"code": exc.code.value, "message": str(exc)})
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@app.get("/v1/connectors", response_model=list[ConnectorRegistrationView])
def connectors(
    registry: ConnectorEndpointRegistry = Depends(get_connector_registry),
) -> list[ConnectorRegistrationView]:
    results: list[ConnectorRegistrationView] = []
    for connector_id in registry.connector_ids():
        try:
            manifest = registry.get(connector_id).manifest
        except (ConnectorClientError, ValueError) as exc:
            # One optional or broken Connector must not hide healthy peers.
            incompatible = isinstance(exc, ConnectorClientError) and exc.code is ConnectorErrorCode.PROTOCOL_MISMATCH
            results.append(
                ConnectorRegistrationView(
                    connector_id=connector_id,
                    status="incompatible" if incompatible else "unavailable",
                    error=str(exc),
                )
            )
        else:
            results.append(
                ConnectorRegistrationView(
                    connector_id=connector_id,
                    status="available",
                    manifest=manifest,
                )
            )
    return results


@app.post("/v1/sources", response_model=SourceView, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceCreate,
    session: Session = Depends(get_session),
    registry: ConnectorEndpointRegistry = Depends(get_connector_registry),
) -> Source:
    try:
        connector = registry.get(payload.connector_id)
        manifest = connector.manifest
        properties = manifest.config_schema.get("properties", {})
        # Ordinary source config is readable metadata. Secrets use a separate
        # challenge or Secret-store path and must never be persisted here.
        secret_fields = {
            name
            for name, schema in properties.items()
            if isinstance(schema, dict) and schema.get("x-campus-secret") is True
        }
        supplied_secrets = secret_fields.intersection(payload.config)
        if supplied_secrets:
            names = ", ".join(sorted(supplied_secrets))
            raise ValueError(f"Secret fields must use the authentication or Secret flow: {names}")
        normalized_config = connector.validate_config(payload.config)
    except (ConnectorClientError, ValueError) as exc:
        raise _connector_http_error(exc) from exc
    settings = get_settings()
    schedule = payload.schedule or SourceSchedule(
        mode="daily",
        time=time(hour=settings.daily_fetch_hour, minute=settings.daily_fetch_minute),
        timezone=settings.timezone,
    )
    source = Source(
        name=payload.name,
        connector_id=manifest.connector_id,
        connector_version=manifest.version,
        enabled=payload.enabled,
        config=normalized_config,
        auth_status="unknown",
        schedule_mode=schedule.mode,
        schedule_time=schedule.time,
        schedule_timezone=schedule.timezone,
    )
    _refresh_next_run(source)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


@app.get("/v1/sources", response_model=list[SourceView])
def sources(
    include_archived: bool = False,
    session: Session = Depends(get_session),
) -> list[Source]:
    query = select(Source)
    if not include_archived:
        query = query.where(Source.archived_at.is_(None))
    return list(session.scalars(query.order_by(Source.name, Source.created_at)).all())


def _source(source_id: str, session: Session, *, include_archived: bool = False) -> Source:
    source = session.get(Source, source_id)
    if source is None or (source.archived_at is not None and not include_archived):
        raise HTTPException(status_code=404, detail="Source not found")
    return source


def _refresh_next_run(source: Source) -> None:
    """Apply one scheduling policy consistently across all source mutations."""

    if not source.enabled or source.archived_at is not None or source.schedule_mode == "manual":
        source.next_run_at = None
        return
    source.next_run_at = next_daily_run(
        source.schedule_time,
        source.schedule_timezone,
        after=utcnow(),
    )


def _validate_source_config(
    connector: ConnectorClient,
    config: dict[str, object],
) -> dict[str, object]:
    properties = connector.manifest.config_schema.get("properties", {})
    secret_fields = {
        name
        for name, schema in properties.items()
        if isinstance(schema, dict) and schema.get("x-campus-secret") is True
    }
    supplied_secrets = secret_fields.intersection(config)
    if supplied_secrets:
        names = ", ".join(sorted(supplied_secrets))
        raise ValueError(f"Secret fields must use the authentication or Secret flow: {names}")
    return connector.validate_config(config)


@app.get("/v1/sources/{source_id}", response_model=SourceView)
def get_source(source_id: str, session: Session = Depends(get_session)) -> Source:
    return _source(source_id, session)


@app.patch("/v1/sources/{source_id}", response_model=SourceView)
def update_source(
    source_id: str,
    payload: SourceUpdate,
    session: Session = Depends(get_session),
    registry: ConnectorEndpointRegistry = Depends(get_connector_registry),
) -> Source:
    source = _source(source_id, session)
    changes = payload.model_fields_set
    if "config" in changes:
        try:
            connector = registry.get(source.connector_id, expected_version=source.connector_version)
            source.config = _validate_source_config(connector, payload.config or {})
        except (ConnectorClientError, ValueError) as exc:
            raise _connector_http_error(exc) from exc
    if "name" in changes and payload.name is not None:
        source.name = payload.name
    if "enabled" in changes and payload.enabled is not None:
        source.enabled = payload.enabled
    if "schedule" in changes and payload.schedule is not None:
        source.schedule_mode = payload.schedule.mode
        source.schedule_time = payload.schedule.time
        source.schedule_timezone = payload.schedule.timezone
    _refresh_next_run(source)
    session.commit()
    session.refresh(source)
    return source


@app.delete("/v1/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_source(source_id: str, session: Session = Depends(get_session)) -> None:
    source = _source(source_id, session)
    source.enabled = False
    source.archived_at = utcnow()
    source.next_run_at = None
    source.credential_refs = {}
    source.auth_status = "unknown"
    session.commit()


@app.post("/v1/sources/{source_id}/restore", response_model=SourceView)
def restore_source(source_id: str, session: Session = Depends(get_session)) -> Source:
    source = _source(source_id, session, include_archived=True)
    if source.archived_at is None:
        raise HTTPException(status_code=409, detail="Source is not archived")
    source.archived_at = None
    source.enabled = False
    source.next_run_at = None
    session.commit()
    session.refresh(source)
    return source


def _source_and_connector(
    source_id: str,
    session: Session,
    registry: ConnectorEndpointRegistry,
) -> tuple[Source, ConnectorClient]:
    source = _source(source_id, session)
    try:
        connector = registry.get(source.connector_id, expected_version=source.connector_version)
    except (ConnectorClientError, ValueError) as exc:
        raise _connector_http_error(exc) from exc
    return source, connector


@app.post("/v1/sources/{source_id}/check", response_model=SourceCheckResult)
def check_source(
    source_id: str,
    session: Session = Depends(get_session),
    registry: ConnectorEndpointRegistry = Depends(get_connector_registry),
) -> SourceCheckResult:
    source, connector = _source_and_connector(source_id, session, registry)
    try:
        connector.validate_config(source.config)
        auth = connector.auth_status(source.id, source.config)
    except (ConnectorClientError, ValueError) as exc:
        raise _connector_http_error(exc) from exc
    source.auth_status = auth.state.value
    session.commit()
    return SourceCheckResult(
        connector_status="available",
        config_status="valid",
        auth_status=auth.state.value,
        checked_at=utcnow(),
    )


@app.post("/v1/sources/{source_id}/auth/status", response_model=AuthResult)
def source_auth_status(
    source_id: str,
    session: Session = Depends(get_session),
    registry: ConnectorEndpointRegistry = Depends(get_connector_registry),
) -> AuthResult:
    source, connector = _source_and_connector(source_id, session, registry)
    try:
        result = connector.auth_status(source.id, source.config)
    except ConnectorClientError as exc:
        raise _connector_http_error(exc) from exc
    source.auth_status = result.state.value
    session.commit()
    return result


@app.post("/v1/sources/{source_id}/auth/begin", response_model=AuthResult)
def begin_source_auth(
    source_id: str,
    session: Session = Depends(get_session),
    registry: ConnectorEndpointRegistry = Depends(get_connector_registry),
) -> AuthResult:
    source, connector = _source_and_connector(source_id, session, registry)
    try:
        result = connector.begin_auth(source.id, source.config)
    except ConnectorClientError as exc:
        raise _connector_http_error(exc) from exc
    source.auth_status = result.state.value
    session.commit()
    return result


@app.post("/v1/sources/{source_id}/auth/respond", response_model=AuthResult)
def respond_to_source_auth(
    source_id: str,
    payload: SourceAuthResponse,
    session: Session = Depends(get_session),
    registry: ConnectorEndpointRegistry = Depends(get_connector_registry),
) -> AuthResult:
    source, connector = _source_and_connector(source_id, session, registry)
    try:
        result = connector.submit_auth_response(
            source.id,
            source.config,
            payload.challenge_id,
            payload.response,
        )
    except ConnectorClientError as exc:
        raise _connector_http_error(exc) from exc
    source.auth_status = result.state.value
    session.commit()
    return result


@app.post("/v1/sources/{source_id}/sync", response_model=JobView, status_code=status.HTTP_202_ACCEPTED)
def sync_source(source_id: str, session: Session = Depends(get_session)) -> Job:
    source = session.get(Source, source_id)
    if source is None or not source.enabled or source.archived_at is not None:
        raise HTTPException(status_code=404, detail="Enabled source not found")
    return enqueue_job(
        session,
        kind="sync_source",
        payload={"source_id": source.id},
        dedupe_key=f"manual-sync:{source.id}:{uuid4()}",
        max_attempts=3,
    )


@app.post("/v1/sources/{source_id}/preview", response_model=JobView, status_code=status.HTTP_202_ACCEPTED)
def preview_source(source_id: str, session: Session = Depends(get_session)) -> Job:
    source = session.get(Source, source_id)
    if source is None or not source.enabled or source.archived_at is not None:
        raise HTTPException(status_code=404, detail="Enabled source not found")
    return enqueue_job(
        session,
        kind="preview_source",
        payload={"source_id": source.id, "max_items": 10},
        dedupe_key=f"preview-source:{source.id}:{uuid4()}",
        max_attempts=2,
    )

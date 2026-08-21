from __future__ import annotations

from campus_connector_sdk import AuthResult, AuthState, ConnectorManifest
from sqlalchemy.orm import Session

from campus_ai.api import (
    app,
    archive_source,
    check_source,
    connectors as list_connectors,
    create_job,
    create_source,
    get_source,
    job,
    jobs,
    live,
    preview_source,
    ready,
    restore_source,
    sources,
    update_source,
)
from campus_ai.models import Message
from campus_ai.schemas import JobCreate, SourceCreate, SourceSchedule, SourceUpdate, SourceView


class FakeConnectorClient:
    manifest = ConnectorManifest(
        connector_id="example.static",
        version="1.0.0",
        display_name="Example",
        config_schema={"type": "object", "properties": {"url": {"type": "string"}}},
    )

    def validate_config(self, config: dict[str, object]) -> dict[str, object]:
        return {**config, "validated": True}

    def auth_status(self, instance_id: str, config: dict[str, object]) -> AuthResult:
        return AuthResult(state=AuthState.NOT_REQUIRED)


class FakeConnectorRegistry:
    def get(self, connector_id: str, *, expected_version: str | None = None) -> FakeConnectorClient:
        assert connector_id == "example.static"
        return FakeConnectorClient()


class PartiallyAvailableRegistry:
    def connector_ids(self) -> list[str]:
        return ["example.static", "example.unavailable"]

    def get(self, connector_id: str, *, expected_version: str | None = None) -> FakeConnectorClient:
        if connector_id == "example.unavailable":
            raise ValueError("Connector is not available")
        return FakeConnectorClient()


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
    assert job(created.id, session).id == created.id

    paths = app.openapi()["paths"]
    assert "/health/live" in paths
    assert "/v1/jobs" in paths
    assert "/v1/jobs/{job_id}" in paths
    assert "/v1/connectors" in paths
    assert "/v1/sources" in paths
    assert "/v1/sources/{source_id}" in paths
    assert "/v1/sources/{source_id}/check" in paths
    assert "/v1/sources/{source_id}/preview" in paths


def test_source_is_created_through_connector_contract(session: Session) -> None:
    source = create_source(
        SourceCreate(
            name="Public notices",
            connector_id="example.static",
            config={"url": "https://campus.example/notices"},
        ),
        session=session,
        registry=FakeConnectorRegistry(),  # type: ignore[arg-type]
    )

    assert source.connector_version == "1.0.0"
    assert source.config["validated"] is True
    assert sources(session=session) == [source]
    view = SourceView.model_validate(source)
    assert view.schedule.mode == "daily"
    assert view.next_run_at is not None


def test_connector_discovery_isolates_unavailable_services() -> None:
    discovered = list_connectors(registry=PartiallyAvailableRegistry())  # type: ignore[arg-type]

    assert discovered[0].status == "available"
    assert discovered[0].manifest is not None
    assert discovered[1].status == "unavailable"
    assert discovered[1].manifest is None


def test_source_can_be_updated_checked_archived_and_restored(session: Session) -> None:
    registry = FakeConnectorRegistry()
    source = create_source(
        SourceCreate(
            name="Notices",
            connector_id="example.static",
            config={"url": "https://campus.example/notices"},
        ),
        session=session,
        registry=registry,  # type: ignore[arg-type]
    )
    updated = update_source(
        source.id,
        SourceUpdate(
            name="Important notices",
            schedule=SourceSchedule(mode="manual", time="08:30", timezone="UTC"),
        ),
        session=session,
        registry=registry,  # type: ignore[arg-type]
    )
    assert updated.name == "Important notices"
    assert updated.schedule_mode == "manual"
    assert updated.next_run_at is None

    checked = check_source(source.id, session=session, registry=registry)  # type: ignore[arg-type]
    assert checked.connector_status == "available"
    assert checked.auth_status == "not_required"

    session.add(
        Message(
            source_id=source.id,
            external_id="notice-1",
            source_url="https://campus.example/notices/1",
            title="Existing",
            content_text="History must survive archival.",
            content_hash="a" * 64,
        )
    )
    source.credential_refs = {"password": "secret-ref"}
    session.commit()

    archive_source(source.id, session=session)
    assert sources(session=session) == []
    assert sources(include_archived=True, session=session) == [source]
    assert session.get(Message, session.query(Message.id).scalar()) is not None
    assert source.credential_refs == {}

    restored = restore_source(source.id, session=session)
    assert restored.archived_at is None
    assert restored.enabled is False
    assert get_source(source.id, session=session) == restored


def test_preview_creates_a_bounded_diagnostic_job(session: Session) -> None:
    source = create_source(
        SourceCreate(name="Notices", connector_id="example.static", config={}),
        session=session,
        registry=FakeConnectorRegistry(),  # type: ignore[arg-type]
    )

    created = preview_source(source.id, session=session)

    assert created.kind == "preview_source"
    assert created.payload == {"source_id": source.id, "max_items": 10}

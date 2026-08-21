from __future__ import annotations

from campus_connector_sdk import AuthResult, AuthState, ConnectorManifest
from sqlalchemy.orm import Session

from campus_ai.api import app, connectors as list_connectors, create_job, create_source, jobs, live, ready, sources
from campus_ai.schemas import JobCreate, SourceCreate


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

    paths = app.openapi()["paths"]
    assert "/health/live" in paths
    assert "/v1/jobs" in paths
    assert "/v1/connectors" in paths
    assert "/v1/sources" in paths


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


def test_connector_discovery_isolates_unavailable_services() -> None:
    discovered = list_connectors(registry=PartiallyAvailableRegistry())  # type: ignore[arg-type]

    assert discovered[0].status == "available"
    assert discovered[0].manifest is not None
    assert discovered[1].status == "unavailable"
    assert discovered[1].manifest is None

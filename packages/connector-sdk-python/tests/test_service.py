from __future__ import annotations

import pytest
from fastapi import HTTPException

from campus_connector_sdk import (
    CampusConnector,
    ConnectorCapability,
    ConnectorManifest,
    ConnectorMessage,
    SyncBatch,
    SyncRequest,
    create_connector_app,
)


class ExampleConnector(CampusConnector):
    @property
    def manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_id="example.test",
            version="1.0.0",
            display_name="Example",
            capabilities={ConnectorCapability.SYNC},
            config_schema={"type": "object", "properties": {}},
        )

    def validate_config(self, config: dict[str, object]) -> dict[str, object]:
        return dict(config)

    def sync(self, request: SyncRequest) -> SyncBatch:
        return SyncBatch(
            items=[ConnectorMessage(external_id="one", url="https://campus.example/1", title="One", body="Body")],
            next_cursor={"last": "one"},
        )


def test_service_exposes_versioned_contract_and_checks_token() -> None:
    app = create_connector_app(ExampleConnector(), shared_token="test-token")
    routes = {route.path: route for route in app.routes if hasattr(route, "path")}

    assert routes["/health/live"].endpoint() == {"status": "ok"}
    assert routes["/v1/manifest"].endpoint().connector_id == "example.test"
    response = routes["/v1/sync"].endpoint(
        SyncRequest(instance_id="instance", config={}, cursor={})
    )
    assert response.next_cursor == {"last": "one"}

    authorize = routes["/v1/manifest"].dependant.dependencies[0].call
    with pytest.raises(HTTPException):
        authorize(None)
    authorize("Bearer test-token")

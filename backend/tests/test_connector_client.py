from __future__ import annotations

import httpx
import pytest

from campus_connector_sdk import ConnectorErrorCode, SyncRequest
from campus_ai.connectors.client import ConnectorClient, ConnectorClientError, validate_connector_endpoint


def manifest(connector_id: str = "example.static") -> dict[str, object]:
    return {
        "connector_id": connector_id,
        "version": "1.2.3",
        "contract_version": "1.0",
        "display_name": "Example",
        "capabilities": ["sync"],
        "config_schema": {"type": "object", "properties": {}},
        "requires_browser": False,
    }


def test_connector_client_validates_manifest_and_sync_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/manifest":
            return httpx.Response(200, json=manifest())
        if request.url.path == "/v1/sync":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "external_id": "one",
                            "url": "https://campus.example/one",
                            "title": "One",
                            "body": "Body",
                        }
                    ],
                    "next_cursor": {"last": "one"},
                    "has_more": False,
                    "auth_state": "not_required",
                    "warnings": [],
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="https://connector.example", transport=transport)
    client = ConnectorClient(
        expected_connector_id="example.static",
        expected_version="1.2.3",
        base_url="https://connector.example",
        client=http_client,
    )

    batch = client.sync(SyncRequest(instance_id="source", config={}, cursor={}))
    assert batch.items[0].external_id == "one"
    assert batch.next_cursor == {"last": "one"}


def test_connector_client_rejects_manifest_id_mismatch() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=manifest("different.connector")))
    client = ConnectorClient(
        expected_connector_id="example.static",
        base_url="https://connector.example",
        client=httpx.Client(base_url="https://connector.example", transport=transport),
    )

    with pytest.raises(ConnectorClientError) as raised:
        _ = client.manifest

    assert raised.value.code is ConnectorErrorCode.PROTOCOL_MISMATCH


def test_connector_endpoint_rejects_embedded_credentials() -> None:
    with pytest.raises(ValueError):
        validate_connector_endpoint("https://user:password@connector.example")

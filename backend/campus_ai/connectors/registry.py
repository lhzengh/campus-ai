from __future__ import annotations

from functools import lru_cache

from campus_ai.config import get_settings
from campus_ai.connectors.client import ConnectorClient, validate_connector_endpoint


class ConnectorEndpointRegistry:
    """Runtime-only mapping from stable Connector IDs to service endpoints."""

    def __init__(self, endpoints: dict[str, str], *, shared_token: str = "") -> None:
        self.endpoints = {
            connector_id: validate_connector_endpoint(endpoint)
            for connector_id, endpoint in endpoints.items()
        }
        self.shared_token = shared_token

    def connector_ids(self) -> list[str]:
        return sorted(self.endpoints)

    def get(self, connector_id: str, *, expected_version: str | None = None) -> ConnectorClient:
        try:
            endpoint = self.endpoints[connector_id]
        except KeyError as exc:
            raise ValueError(f"Connector is not registered: {connector_id}") from exc
        return ConnectorClient(
            expected_connector_id=connector_id,
            expected_version=expected_version,
            base_url=endpoint,
            shared_token=self.shared_token,
        )


@lru_cache
def get_connector_registry() -> ConnectorEndpointRegistry:
    # Connector locations belong to deployment configuration, never source rows.
    settings = get_settings()
    return ConnectorEndpointRegistry(
        settings.connector_endpoint_map,
        shared_token=settings.connector_shared_token,
    )

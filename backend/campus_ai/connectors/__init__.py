"""Core-side clients for the out-of-process Connector protocol."""

from campus_ai.connectors.client import ConnectorClient, ConnectorClientError
from campus_ai.connectors.registry import ConnectorEndpointRegistry, get_connector_registry

__all__ = [
    "ConnectorClient",
    "ConnectorClientError",
    "ConnectorEndpointRegistry",
    "get_connector_registry",
]

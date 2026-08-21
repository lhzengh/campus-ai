from __future__ import annotations

from abc import ABC, abstractmethod

from campus_connector_sdk.errors import ConnectorProtocolError
from campus_connector_sdk.models import (
    AuthResult,
    AuthState,
    ConnectorErrorCode,
    ConnectorManifest,
    SyncBatch,
    SyncRequest,
)


class CampusConnector(ABC):
    """The only interface a Python Connector implementation must provide."""

    @property
    @abstractmethod
    def manifest(self) -> ConnectorManifest:
        """Describe the Connector and the runtime configuration it accepts."""

    @abstractmethod
    def validate_config(self, config: dict[str, object]) -> dict[str, object]:
        """Validate and normalize non-secret instance configuration."""

    def auth_status(self, instance_id: str, config: dict[str, object]) -> AuthResult:
        return AuthResult(state=AuthState.NOT_REQUIRED)

    def begin_auth(self, instance_id: str, config: dict[str, object]) -> AuthResult:
        raise ConnectorProtocolError(
            ConnectorErrorCode.UNSUPPORTED_OPERATION,
            "This Connector does not require interactive authentication",
        )

    def submit_auth_response(
        self,
        instance_id: str,
        config: dict[str, object],
        challenge_id: str,
        response: dict[str, str],
    ) -> AuthResult:
        raise ConnectorProtocolError(
            ConnectorErrorCode.UNSUPPORTED_OPERATION,
            "This Connector does not accept authentication responses",
        )

    @abstractmethod
    def sync(self, request: SyncRequest) -> SyncBatch:
        """Return a normalized, cursor-aware batch without accessing Core storage."""

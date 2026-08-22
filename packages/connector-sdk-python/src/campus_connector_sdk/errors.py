"""Typed errors that cross the Connector HTTP boundary."""

from __future__ import annotations

from typing import Any

from campus_connector_sdk.models import ConnectorErrorCode


class ConnectorProtocolError(RuntimeError):
    """An expected Connector failure that Core can handle deterministically."""

    def __init__(
        self,
        code: ConnectorErrorCode,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.details = details or {}

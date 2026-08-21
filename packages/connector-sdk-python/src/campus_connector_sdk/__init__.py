"""Public SDK for implementing out-of-process Campus AI connectors."""

from campus_connector_sdk.base import CampusConnector
from campus_connector_sdk.errors import ConnectorProtocolError
from campus_connector_sdk.models import (
    CONTRACT_VERSION,
    AuthChallenge,
    AuthChallengeField,
    AuthChallengeKind,
    AuthResult,
    AuthState,
    AuthStatusRequest,
    BeginAuthRequest,
    ConfigValidationRequest,
    ConfigValidationResult,
    ConnectorAttachment,
    ConnectorCapability,
    ConnectorErrorCode,
    ConnectorManifest,
    ConnectorMessage,
    SubmitAuthRequest,
    SyncBatch,
    SyncRequest,
)
from campus_connector_sdk.service import create_connector_app

__all__ = [
    "CONTRACT_VERSION",
    "AuthChallenge",
    "AuthChallengeField",
    "AuthChallengeKind",
    "AuthResult",
    "AuthState",
    "AuthStatusRequest",
    "BeginAuthRequest",
    "CampusConnector",
    "ConfigValidationRequest",
    "ConfigValidationResult",
    "ConnectorAttachment",
    "ConnectorCapability",
    "ConnectorErrorCode",
    "ConnectorManifest",
    "ConnectorMessage",
    "ConnectorProtocolError",
    "SubmitAuthRequest",
    "SyncBatch",
    "SyncRequest",
    "create_connector_app",
]

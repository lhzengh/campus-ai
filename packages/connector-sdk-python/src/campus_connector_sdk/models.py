from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


CONTRACT_VERSION = "1.0"


# Capabilities let Core discover optional behavior without importing Connector code.
class ConnectorCapability(StrEnum):
    SYNC = "sync"
    INCREMENTAL_SYNC = "incremental_sync"
    ATTACHMENTS = "attachments"
    USER_ASSISTED_AUTH = "user_assisted_auth"
    BROWSER = "browser"


class AuthState(StrEnum):
    NOT_REQUIRED = "not_required"
    AUTH_REQUIRED = "auth_required"
    WAITING_FOR_USER = "waiting_for_user"
    READY = "ready"
    EXPIRED = "expired"


class AuthChallengeKind(StrEnum):
    USERNAME_PASSWORD = "username_password"
    SMS_CODE = "sms_code"
    QR_SCAN = "qr_scan"
    CAPTCHA = "captcha"
    BROWSER_INTERACTION = "browser_interaction"
    CONFIRMATION = "confirmation"


class ConnectorErrorCode(StrEnum):
    CONFIG_INVALID = "config_invalid"
    AUTH_REQUIRED = "auth_required"
    ACCESS_DENIED = "access_denied"
    RATE_LIMITED = "rate_limited"
    SOURCE_CHANGED = "source_changed"
    TEMPORARY_FAILURE = "temporary_failure"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    PROTOCOL_MISMATCH = "protocol_mismatch"


class ConnectorManifest(BaseModel):
    """Stable identity and configuration metadata advertised to Core and clients."""

    connector_id: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)+$")
    version: str = Field(min_length=1)
    contract_version: str = CONTRACT_VERSION
    display_name: str = Field(min_length=1)
    description: str = ""
    capabilities: set[ConnectorCapability] = Field(default_factory=lambda: {ConnectorCapability.SYNC})
    config_schema: dict[str, Any]
    requires_browser: bool = False

    @field_validator("config_schema")
    @classmethod
    def validate_schema_shape(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value.get("type") != "object":
            raise ValueError("Connector config_schema must describe a JSON object")
        return value


class ConfigValidationRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class ConfigValidationResult(BaseModel):
    valid: bool = True
    normalized_config: dict[str, Any] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


class AuthChallengeField(BaseModel):
    name: str
    label: str
    input_type: str = "text"
    secret: bool = False
    required: bool = True


class AuthChallenge(BaseModel):
    """A provider-neutral user interaction that Client can render through Core."""

    challenge_id: str
    kind: AuthChallengeKind
    title: str
    instructions: str = ""
    fields: list[AuthChallengeField] = Field(default_factory=list)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthResult(BaseModel):
    state: AuthState
    challenge: AuthChallenge | None = None
    message: str = ""


class AuthStatusRequest(BaseModel):
    instance_id: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)


class BeginAuthRequest(AuthStatusRequest):
    pass


class SubmitAuthRequest(AuthStatusRequest):
    challenge_id: str = Field(min_length=1)
    response: dict[str, str] = Field(default_factory=dict)


class ConnectorAttachment(BaseModel):
    external_id: str | None = None
    name: str
    url: str
    media_type: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorMessage(BaseModel):
    """Canonical source message; Core owns persistence and downstream analysis."""

    external_id: str = Field(min_length=1, max_length=500)
    url: str
    title: str = Field(min_length=1)
    body: str
    published_at: datetime | None = None
    attachments: list[ConnectorAttachment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SyncRequest(BaseModel):
    """Cursor is opaque to Core and interpreted only by the owning Connector."""

    instance_id: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    cursor: dict[str, Any] = Field(default_factory=dict)
    max_items: int = Field(default=100, ge=1, le=1000)


class SyncBatch(BaseModel):
    """One bounded incremental result returned across the process boundary."""

    items: list[ConnectorMessage] = Field(default_factory=list)
    next_cursor: dict[str, Any] = Field(default_factory=dict)
    has_more: bool = False
    auth_state: AuthState = AuthState.NOT_REQUIRED
    warnings: list[str] = Field(default_factory=list)


class ConnectorErrorBody(BaseModel):
    code: ConnectorErrorCode
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)

"""Versioned, provider-neutral data contract shared by Core and Connectors."""

from __future__ import annotations

import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


CONTRACT_VERSION = "1.0"


# Capabilities let Core discover optional behavior without importing Connector code.
class ConnectorCapability(StrEnum):
    """Optional behaviors advertised by a Connector manifest."""

    SYNC = "sync"
    INCREMENTAL_SYNC = "incremental_sync"
    ATTACHMENTS = "attachments"
    USER_ASSISTED_AUTH = "user_assisted_auth"
    BROWSER = "browser"


class AuthState(StrEnum):
    """Portable authentication state understood by Core and clients."""

    NOT_REQUIRED = "not_required"
    AUTH_REQUIRED = "auth_required"
    WAITING_FOR_USER = "waiting_for_user"
    READY = "ready"
    EXPIRED = "expired"


class AuthChallengeKind(StrEnum):
    """User interactions that a client may need to render."""

    USERNAME_PASSWORD = "username_password"
    SMS_CODE = "sms_code"
    QR_SCAN = "qr_scan"
    CAPTCHA = "captcha"
    BROWSER_INTERACTION = "browser_interaction"
    CONFIRMATION = "confirmation"


class ConnectorErrorCode(StrEnum):
    """Stable failure categories that Core can handle without log parsing."""

    CONFIG_INVALID = "config_invalid"
    AUTH_REQUIRED = "auth_required"
    ACCESS_DENIED = "access_denied"
    RATE_LIMITED = "rate_limited"
    SOURCE_CHANGED = "source_changed"
    TEMPORARY_FAILURE = "temporary_failure"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    PROTOCOL_MISMATCH = "protocol_mismatch"


class CampusItemType(StrEnum):
    """Broad content categories used consistently across institutions."""

    ANNOUNCEMENT = "announcement"
    NEWS = "news"
    EVENT = "event"
    RESOURCE = "resource"
    OTHER = "other"


class AttachmentAccessMode(StrEnum):
    """How Core may retrieve an attachment without learning source secrets."""

    PUBLIC_URL = "public_url"
    CONNECTOR_FETCH = "connector_fetch"


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
        """Require a top-level object so clients can render named fields."""

        if value.get("type") != "object":
            raise ValueError("Connector config_schema must describe a JSON object")
        return value


class ConfigValidationRequest(BaseModel):
    """Raw instance configuration submitted for Connector validation."""

    config: dict[str, Any] = Field(default_factory=dict)


class ConfigValidationResult(BaseModel):
    """Normalized configuration or field-level validation failures."""

    valid: bool = True
    normalized_config: dict[str, Any] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


class AuthChallengeField(BaseModel):
    """One provider-neutral input requested during assisted authentication."""

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
    """Current authentication state plus an optional user challenge."""

    state: AuthState
    challenge: AuthChallenge | None = None
    message: str = ""


class AuthStatusRequest(BaseModel):
    """Instance context required to evaluate authentication readiness."""

    instance_id: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)


class BeginAuthRequest(AuthStatusRequest):
    """Request to start authentication for a configured instance."""

    pass


class SubmitAuthRequest(AuthStatusRequest):
    """User response submitted for an active authentication challenge."""

    challenge_id: str = Field(min_length=1)
    response: dict[str, str] = Field(default_factory=dict)


def _absolute_http_url(value: str, *, field_name: str) -> str:
    """Validate transport URLs without normalizing source-owned identifiers."""

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{field_name} must not contain credentials")
    return value


def _bounded_json(value: dict[str, Any], *, field_name: str, max_bytes: int = 65_536) -> dict[str, Any]:
    """Keep opaque protocol state bounded and JSON serializable."""

    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain JSON-compatible values") from exc
    if len(encoded) > max_bytes:
        raise ValueError(f"{field_name} must not exceed {max_bytes} UTF-8 bytes")
    return value


class CampusPublisher(BaseModel):
    """Publisher explicitly named by the source, never inferred by Connector code."""

    name: str = Field(min_length=1, max_length=500)
    external_id: str | None = Field(default=None, max_length=500)


class AttachmentAccess(BaseModel):
    """Either a public URL or an opaque reference resolved by the Connector."""

    mode: AttachmentAccessMode
    url: str | None = None
    ref: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def validate_mode_fields(self) -> AttachmentAccess:
        """Require exactly the locator used by the selected access mode."""

        if self.mode is AttachmentAccessMode.PUBLIC_URL:
            if not self.url or self.ref is not None:
                raise ValueError("public_url access requires url and forbids ref")
            self.url = _absolute_http_url(self.url, field_name="attachment access URL")
        elif not self.ref or self.url is not None:
            raise ValueError("connector_fetch access requires ref and forbids url")
        return self


class CampusAttachment(BaseModel):
    """Normalized attachment metadata with an explicit access strategy."""

    external_id: str | None = Field(default=None, max_length=500)
    name: str = Field(min_length=1, max_length=1_000)
    media_type: str | None = Field(default=None, max_length=255)
    size_bytes: int | None = Field(default=None, ge=0)
    content_hash: str | None = Field(default=None, max_length=200)
    access: AttachmentAccess


class CampusItem(BaseModel):
    """Canonical source fact; Core owns persistence, analysis, and notification."""

    external_id: str = Field(min_length=1, max_length=500)
    item_type: CampusItemType = CampusItemType.ANNOUNCEMENT
    source_url: str
    title: str = Field(min_length=1, max_length=2_000)
    content_text: str = Field(max_length=1_000_000)
    content_html: str | None = Field(default=None, max_length=2_000_000)
    publisher: CampusPublisher | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    attachments: list[CampusAttachment] = Field(default_factory=list, max_length=100)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        """Accept only absolute credential-free source URLs."""

        return _absolute_http_url(value, field_name="source_url")

    @field_validator("published_at", "updated_at")
    @classmethod
    def require_timestamp_offset(cls, value: datetime | None) -> datetime | None:
        """Reject ambiguous source timestamps without timezone offsets."""

        if value is not None and value.utcoffset() is None:
            raise ValueError("source timestamps must include an explicit UTC offset")
        return value

    @field_validator("extensions")
    @classmethod
    def validate_extensions(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Namespace and bound Connector-owned extension data."""

        connector_id = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)+$")
        if any(connector_id.fullmatch(key) is None for key in value):
            raise ValueError("extensions keys must be stable Connector IDs")
        return _bounded_json(value, field_name="extensions")


class SyncWarning(BaseModel):
    """Structured non-fatal problem that does not invalidate the whole batch."""

    code: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
    message: str = Field(min_length=1, max_length=2_000)
    external_id: str | None = Field(default=None, max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("details")
    @classmethod
    def validate_details(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Bound warning details before they cross process boundaries."""

        return _bounded_json(value, field_name="warning details")


class SyncRequest(BaseModel):
    """Cursor is opaque to Core and interpreted only by the owning Connector."""

    instance_id: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    cursor: dict[str, Any] = Field(default_factory=dict)
    max_items: int = Field(default=100, ge=1, le=1000)


class CampusItemBatch(BaseModel):
    """One bounded incremental result returned across the process boundary."""

    contract_version: Literal["1.0"] = CONTRACT_VERSION
    items: list[CampusItem] = Field(default_factory=list, max_length=1_000)
    next_cursor: dict[str, Any] = Field(default_factory=dict)
    has_more: bool = False
    auth_state: AuthState = AuthState.NOT_REQUIRED
    warnings: list[SyncWarning] = Field(default_factory=list, max_length=100)

    @field_validator("next_cursor")
    @classmethod
    def validate_cursor(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Keep opaque incremental state bounded and serializable."""

        return _bounded_json(value, field_name="next_cursor")

    @model_validator(mode="after")
    def require_pagination_cursor(self) -> CampusItemBatch:
        """Ensure Core can make progress whenever more items are advertised."""

        if self.has_more and not self.next_cursor:
            raise ValueError("has_more requires a non-empty next_cursor")
        return self


# Temporary symbol aliases aid migration; legacy serialized field names stay invalid.
ConnectorAttachment = CampusAttachment
ConnectorMessage = CampusItem
SyncBatch = CampusItemBatch


class ConnectorErrorBody(BaseModel):
    """Serializable error envelope returned by a Connector service."""

    code: ConnectorErrorCode
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)

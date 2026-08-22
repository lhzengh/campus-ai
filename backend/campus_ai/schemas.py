"""Declare validated Client API requests and response views."""

from __future__ import annotations

from datetime import datetime, time as dt_time
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from campus_connector_sdk import ConnectorManifest
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Deadline(BaseModel):
    """A source-supported deadline extracted by the analysis provider."""

    time: datetime | None = None
    timezone: str = "Asia/Shanghai"
    all_day: bool = False
    confidence: float = Field(ge=0, le=1)
    evidence: str


class AnalysisResult(BaseModel):
    """Structured AI output consumed by ranking and notification policies."""

    category: str
    summary_short: str
    summary_detail: str
    relevance_score: int = Field(ge=0, le=100)
    importance_score: int = Field(ge=0, le=100)
    urgency: Literal["low", "medium", "high", "unknown"]
    audience: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    reason: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class JobCreate(BaseModel):
    """Internal request for enqueueing a deduplicated asynchronous job."""

    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str
    max_attempts: int = Field(default=3, ge=1, le=20)


class JobView(BaseModel):
    """Client-safe job status and structured execution diagnostics."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    payload: dict[str, Any]
    dedupe_key: str
    status: str
    attempts: int
    max_attempts: int
    available_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    result: dict[str, Any]
    last_error: str | None


class MessageView(BaseModel):
    """Canonical message facts exposed without ORM implementation details."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    external_id: str
    item_type: str
    source_url: str
    title: str
    content_text: str
    content_html: str | None
    publisher_json: dict[str, Any] | None
    published_at: datetime | None
    source_updated_at: datetime | None
    fetched_at: datetime
    attachments_json: list[dict[str, Any]]
    extensions_json: dict[str, Any]


class SourceSchedule(BaseModel):
    """A manual or daily source schedule expressed in an IANA timezone."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["manual", "daily"] = "daily"
    time: dt_time = dt_time(hour=7)
    timezone: str = "Asia/Shanghai"

    @field_validator("timezone")
    @classmethod
    def timezone_is_iana(cls, value: str) -> str:
        """Reject platform-specific aliases and misspelled timezones."""

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA name") from exc
        return value


class SourceCreate(BaseModel):
    """Request for creating one runtime-configured Connector instance."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    connector_id: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)+$")
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    schedule: SourceSchedule | None = None


class SourceUpdate(BaseModel):
    """Partial update for mutable source metadata and collection policy."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    config: dict[str, Any] | None = None
    enabled: bool | None = None
    schedule: SourceSchedule | None = None


class SourceView(BaseModel):
    """Client-facing source configuration, lifecycle, and diagnostic state."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    connector_id: str
    connector_version: str | None
    enabled: bool
    config: dict[str, Any]
    schedule: SourceSchedule
    next_run_at: datetime | None
    archived_at: datetime | None
    auth_status: str
    sync_cursor: dict[str, Any]
    last_success_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class SourceAuthResponse(BaseModel):
    """Ephemeral user input for a Connector-owned authentication challenge."""

    challenge_id: str = Field(min_length=1)
    response: dict[str, str] = Field(default_factory=dict)


class SourceCheckResult(BaseModel):
    """Non-collecting validation result for Connector, config, and auth state."""

    connector_status: Literal["available"]
    config_status: Literal["valid"]
    auth_status: str
    checked_at: datetime


class ConnectorRegistrationView(BaseModel):
    """Availability and manifest data for one runtime-registered Connector."""

    connector_id: str
    status: Literal["available", "unavailable", "incompatible"]
    manifest: ConnectorManifest | None = None
    error: str | None = None

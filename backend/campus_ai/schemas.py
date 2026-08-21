from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from campus_connector_sdk import ConnectorManifest
from pydantic import BaseModel, ConfigDict, Field


class Deadline(BaseModel):
    time: datetime | None = None
    timezone: str = "Asia/Shanghai"
    all_day: bool = False
    confidence: float = Field(ge=0, le=1)
    evidence: str


class AnalysisResult(BaseModel):
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
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str
    max_attempts: int = Field(default=3, ge=1, le=20)


class JobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    payload: dict[str, Any]
    dedupe_key: str
    status: str
    attempts: int
    max_attempts: int
    available_at: datetime
    last_error: str | None


class MessageView(BaseModel):
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


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    connector_id: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)+$")
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class SourceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    connector_id: str
    connector_version: str | None
    enabled: bool
    config: dict[str, Any]
    auth_status: str
    sync_cursor: dict[str, Any]
    last_success_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class SourceAuthResponse(BaseModel):
    challenge_id: str = Field(min_length=1)
    response: dict[str, str] = Field(default_factory=dict)


class ConnectorRegistrationView(BaseModel):
    connector_id: str
    status: Literal["available", "unavailable", "incompatible"]
    manifest: ConnectorManifest | None = None
    error: str | None = None

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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
    url: str
    title: str
    body: str
    published_at: datetime | None
    fetched_at: datetime
    metadata_json: dict[str, Any]

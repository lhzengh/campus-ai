"""Define Core-owned persistence models and their database invariants."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from campus_ai.db import Base


def utcnow() -> datetime:
    """Return an aware UTC timestamp for consistent persisted defaults."""

    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    """Durable lifecycle states shared by producers, workers, and clients."""

    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class Source(Base):
    """A user-configured Connector instance and its collection state."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200))
    connector_id: Mapped[str] = mapped_column(String(200), index=True)
    connector_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    credential_refs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sync_cursor: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    auth_status: Mapped[str] = mapped_column(String(30), default="unknown")
    schedule_mode: Mapped[str] = mapped_column(String(20), default="daily")
    schedule_time: Mapped[time] = mapped_column(Time, default=lambda: time(hour=7))
    schedule_timezone: Mapped[str] = mapped_column(String(100), default="Asia/Shanghai")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    @property
    def schedule(self) -> dict[str, str]:
        """Expose the normalized schedule without leaking persistence details."""

        return {
            "mode": self.schedule_mode,
            "time": self.schedule_time.isoformat(timespec="minutes"),
            "timezone": self.schedule_timezone,
        }


class Message(Base):
    """One canonical source item, unique within its owning source."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_message_source_external"),
        Index("ix_messages_published_at", "published_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column(String(500))
    item_type: Mapped[str] = mapped_column(String(30), default="announcement")
    source_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    content_text: Mapped[str] = mapped_column(Text)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher_json: Mapped[dict[str, Any] | None] = mapped_column("publisher", JSON, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column("updated_at", DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    content_hash: Mapped[str] = mapped_column(String(64))
    attachments_json: Mapped[list[dict[str, Any]]] = mapped_column("attachments", JSON, default=list)
    extensions_json: Mapped[dict[str, Any]] = mapped_column("extensions", JSON, default=dict)

    source: Mapped[Source] = relationship()


class Analysis(Base):
    """A versioned AI interpretation that never replaces source facts."""

    __tablename__ = "analyses"
    __table_args__ = (UniqueConstraint("message_id", "provider", "model", "prompt_version", name="uq_analysis_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(50))
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Job(Base):
    """A durable unit of asynchronous work with retry diagnostics."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_job_dedupe_key"),
        Index("ix_jobs_claim", "status", "available_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kind: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    dedupe_key: Mapped[str] = mapped_column(String(500))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    @property
    def duration_ms(self) -> int | None:
        """Return the final-attempt duration for API diagnostics."""

        if self.started_at is None or self.finished_at is None:
            return None
        started_at = self.started_at
        finished_at = self.finished_at
        # SQLite drops timezone metadata even for timezone-aware columns.
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        if finished_at.tzinfo is None:
            finished_at = finished_at.replace(tzinfo=timezone.utc)
        return max(0, round((finished_at - started_at).total_seconds() * 1000))


class NotificationDelivery(Base):
    """An idempotency record for one channel, device, and logical event."""

    __tablename__ = "notification_deliveries"
    __table_args__ = (UniqueConstraint("channel", "device_id", "event_key", name="uq_notification_delivery"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel: Mapped[str] = mapped_column(String(50))
    device_id: Mapped[str] = mapped_column(String(200))
    event_key: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30))
    response: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import date
from typing import Any

from campus_connector_sdk import AuthState, ConnectorMessage, SyncRequest
from sqlalchemy import select
from sqlalchemy.orm import Session

from campus_ai.ai.openai_compatible import OpenAICompatibleProvider
from campus_ai.config import get_settings
from campus_ai.connectors import ConnectorClientError, get_connector_registry
from campus_ai.jobs import enqueue_job
from campus_ai.models import Analysis, Message, Source, utcnow


JobHandler = Callable[[Session, dict[str, Any]], None]


def _content_hash(title: str, body: str) -> str:
    normalized = "\n".join((title.strip(), body.strip()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _persist_message(session: Session, source: Source, normalized: ConnectorMessage) -> Message | None:
    """Persist one canonical message without exposing database models to Connectors."""

    content_hash = _content_hash(normalized.title, normalized.body)
    existing = session.scalar(
        select(Message).where(
            Message.source_id == source.id,
            Message.external_id == normalized.external_id,
        )
    )
    if existing is not None and existing.content_hash == content_hash:
        return None
    if existing is None:
        duplicate = session.scalar(
            select(Message).where(Message.source_id == source.id, Message.content_hash == content_hash)
        )
        if duplicate is not None:
            return None
        message = Message(
            source_id=source.id,
            external_id=normalized.external_id,
            url=normalized.url,
            title=normalized.title,
            body=normalized.body,
            published_at=normalized.published_at,
            content_hash=content_hash,
            metadata_json={
                **normalized.metadata,
                "attachments": [attachment.model_dump(mode="json") for attachment in normalized.attachments],
            },
        )
        session.add(message)
    else:
        existing.url = normalized.url
        existing.title = normalized.title
        existing.body = normalized.body
        existing.published_at = normalized.published_at
        existing.content_hash = content_hash
        existing.metadata_json = {
            **normalized.metadata,
            "attachments": [attachment.model_dump(mode="json") for attachment in normalized.attachments],
        }
        message = existing
    session.commit()
    session.refresh(message)
    enqueue_job(
        session,
        kind="analyze_message",
        payload={"message_id": message.id},
        dedupe_key=f"analyze:{message.id}:{content_hash}",
        max_attempts=4,
    )
    return message


def handle_fetch_all(session: Session, payload: dict[str, Any]) -> None:
    run_key = str(payload.get("run_key") or date.today().isoformat())
    # Authentication-blocked sources stay paused until the user completes a challenge.
    sources = session.scalars(
        select(Source).where(
            Source.enabled.is_(True),
            Source.auth_status.notin_({"auth_required", "waiting_for_user", "expired"}),
        )
    ).all()
    for source in sources:
        enqueue_job(
            session,
            kind="sync_source",
            payload={"source_id": source.id, "run_key": run_key},
            dedupe_key=f"fetch-source:{source.id}:{run_key}",
            max_attempts=3,
        )


def handle_sync_source(session: Session, payload: dict[str, Any]) -> None:
    """Run every source through the same versioned Connector client path."""

    source_id = str(payload["source_id"])
    source = session.get(Source, source_id)
    if source is None or not source.enabled:
        raise ValueError(f"Enabled source not found: {source_id}")
    try:
        connector = get_connector_registry().get(
            source.connector_id,
            expected_version=source.connector_version,
        )
        batch = connector.sync(
            SyncRequest(
                instance_id=source.id,
                config=source.config,
                cursor=source.sync_cursor,
                max_items=int(payload.get("max_items", 100)),
            )
        )
    except ConnectorClientError as exc:
        source.last_error = f"{exc.code.value}: {exc}"
        if exc.code.value == "auth_required":
            source.auth_status = "auth_required"
        session.commit()
        raise
    except ValueError as exc:
        source.last_error = str(exc)
        session.commit()
        raise

    for normalized in batch.items:
        _persist_message(session, source, normalized)

    source.sync_cursor = batch.next_cursor
    source.auth_status = batch.auth_state.value
    source.last_success_at = utcnow()
    source.last_error = None
    session.commit()

    if batch.has_more:
        # A cursor-derived key permits pagination while preventing a broken
        # Connector from creating an infinite sequence with an unchanged cursor.
        cursor_json = json.dumps(batch.next_cursor, sort_keys=True, separators=(",", ":"))
        cursor_hash = hashlib.sha256(cursor_json.encode("utf-8")).hexdigest()[:16]
        run_key = str(payload.get("run_key") or date.today().isoformat())
        enqueue_job(
            session,
            kind="sync_source",
            payload={"source_id": source.id, "run_key": run_key},
            dedupe_key=f"sync-source:{source.id}:{run_key}:{cursor_hash}",
            max_attempts=3,
        )


def handle_fetch_source(session: Session, payload: dict[str, Any]) -> None:
    """Compatibility alias for jobs created before Connector migration 0002."""
    handle_sync_source(session, payload)


def handle_browser_fetch(session: Session, payload: dict[str, Any]) -> None:
    """Compatibility alias for jobs created before Connector migration 0002."""
    handle_sync_source(session, payload)


def handle_analyze_message(session: Session, payload: dict[str, Any]) -> None:
    settings = get_settings()
    message = session.get(Message, str(payload["message_id"]))
    if message is None:
        raise ValueError("Message not found")
    provider = OpenAICompatibleProvider(
        base_url=settings.api_base_url,
        api_key=settings.api_key,
        model=settings.model,
        output_mode=settings.ai_output_mode,
    )
    response = provider.analyze(title=message.title, body=message.body, profile=payload.get("profile", {}))
    analysis = Analysis(
        message_id=message.id,
        provider="openai-compatible",
        model=settings.model,
        prompt_version=provider.prompt_version,
        result=response.result.model_dump(mode="json"),
        latency_ms=response.latency_ms,
        usage=response.usage,
    )
    session.add(analysis)
    session.commit()


HANDLERS: dict[str, JobHandler] = {
    "fetch_all": handle_fetch_all,
    "sync_source": handle_sync_source,
    "fetch_source": handle_fetch_source,
    "browser_fetch": handle_browser_fetch,
    "analyze_message": handle_analyze_message,
}

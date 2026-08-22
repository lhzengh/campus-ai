"""Implement worker-side collection, persistence, and analysis workflows."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import date
from typing import Any, Literal

from campus_connector_sdk import AuthState, CampusItem, SyncRequest
from sqlalchemy import select
from sqlalchemy.orm import Session

from campus_ai.ai.openai_compatible import OpenAICompatibleProvider
from campus_ai.config import get_settings
from campus_ai.connectors import ConnectorClientError, get_connector_registry
from campus_ai.jobs import enqueue_job
from campus_ai.models import Analysis, Message, Source, utcnow


JobResult = dict[str, object]
JobHandler = Callable[[Session, dict[str, Any]], JobResult | None]


def _content_hash(item: CampusItem) -> str:
    """Fingerprint only standard facts that can affect analysis."""

    content = {
        "item_type": item.item_type.value,
        "title": item.title.strip(),
        "content_text": item.content_text.strip(),
        "content_html": item.content_html,
        "publisher": item.publisher.model_dump(mode="json") if item.publisher else None,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "attachments": [attachment.model_dump(mode="json") for attachment in item.attachments],
    }
    normalized = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _apply_item(message: Message, item: CampusItem) -> None:
    """Map a protocol fact to Core-owned persistence fields."""

    message.item_type = item.item_type.value
    message.source_url = item.source_url
    message.title = item.title
    message.content_text = item.content_text
    message.content_html = item.content_html
    message.publisher_json = item.publisher.model_dump(mode="json") if item.publisher else None
    message.published_at = item.published_at
    message.source_updated_at = item.updated_at
    message.fetched_at = utcnow()
    message.attachments_json = [attachment.model_dump(mode="json") for attachment in item.attachments]
    message.extensions_json = item.extensions


def _persist_message(
    session: Session,
    source: Source,
    item: CampusItem,
) -> tuple[Literal["created", "updated", "unchanged"], Message]:
    """Persist one canonical Item without exposing database models to Connectors."""

    content_hash = _content_hash(item)
    existing = session.scalar(
        select(Message).where(
            Message.source_id == source.id,
            Message.external_id == item.external_id,
        )
    )
    if existing is not None and existing.content_hash == content_hash:
        # Non-analysis fields may still change without changing the source facts.
        _apply_item(existing, item)
        session.commit()
        return "unchanged", existing
    if existing is None:
        message = Message(
            source_id=source.id,
            external_id=item.external_id,
            content_hash=content_hash,
        )
        _apply_item(message, item)
        session.add(message)
        outcome: Literal["created", "updated", "unchanged"] = "created"
    else:
        existing.content_hash = content_hash
        _apply_item(existing, item)
        message = existing
        outcome = "updated"
    session.commit()
    session.refresh(message)
    enqueue_job(
        session,
        kind="analyze_message",
        payload={"message_id": message.id},
        dedupe_key=f"analyze:{message.id}:{content_hash}",
        max_attempts=4,
    )
    return outcome, message


def handle_fetch_all(session: Session, payload: dict[str, Any]) -> JobResult:
    """Fan out one run into per-source jobs while skipping blocked auth states."""

    run_key = str(payload.get("run_key") or date.today().isoformat())
    # Authentication-blocked sources stay paused until the user completes a challenge.
    sources = session.scalars(
        select(Source).where(
            Source.enabled.is_(True),
            Source.archived_at.is_(None),
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
    return {"sources_queued": len(sources)}


def handle_sync_source(session: Session, payload: dict[str, Any]) -> JobResult:
    """Run every source through the same versioned Connector client path."""

    source_id = str(payload["source_id"])
    source = session.get(Source, source_id)
    if source is None or not source.enabled or source.archived_at is not None:
        raise ValueError(f"Enabled source not found: {source_id}")
    if source.auth_status in {"auth_required", "waiting_for_user", "expired"}:
        raise ValueError(f"Source authentication is required: {source_id}")
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

    counts = {"created": 0, "updated": 0, "unchanged": 0}
    for normalized in batch.items:
        outcome, _ = _persist_message(session, source, normalized)
        counts[outcome] += 1

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
    return {
        "items_seen": len(batch.items),
        **counts,
        "has_more": batch.has_more,
        "next_page_queued": batch.has_more,
        "warnings": batch.warnings,
    }


def handle_preview_source(session: Session, payload: dict[str, Any]) -> JobResult:
    """Fetch a small diagnostic sample without changing Core collection state."""

    source_id = str(payload["source_id"])
    source = session.get(Source, source_id)
    if source is None or not source.enabled or source.archived_at is not None:
        raise ValueError(f"Enabled source not found: {source_id}")
    connector = get_connector_registry().get(
        source.connector_id,
        expected_version=source.connector_version,
    )
    batch = connector.sync(
        SyncRequest(
            instance_id=source.id,
            config=source.config,
            cursor=source.sync_cursor,
            max_items=min(int(payload.get("max_items", 10)), 10),
        )
    )
    items: list[dict[str, object]] = []
    for item in batch.items:
        preview = item.model_dump(mode="json")
        preview["content_text"] = item.content_text[:1000]
        preview["content_html"] = None
        preview["attachments"] = preview["attachments"][:5]
        items.append(preview)
    source.auth_status = batch.auth_state.value
    session.commit()
    return {
        "items": items,
        "items_seen": len(items),
        "has_more": batch.has_more,
        "auth_status": batch.auth_state.value,
        "warnings": batch.warnings,
    }


def handle_fetch_source(session: Session, payload: dict[str, Any]) -> JobResult:
    """Compatibility alias for jobs created before Connector migration 0002."""
    return handle_sync_source(session, payload)


def handle_browser_fetch(session: Session, payload: dict[str, Any]) -> JobResult:
    """Compatibility alias for jobs created before Connector migration 0002."""
    return handle_sync_source(session, payload)


def handle_analyze_message(session: Session, payload: dict[str, Any]) -> JobResult:
    """Persist one versioned cloud analysis without modifying source facts."""

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
    response = provider.analyze(
        title=message.title,
        body=message.content_text,
        profile=payload.get("profile", {}),
    )
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
    return {"analysis_id": analysis.id, "message_id": message.id}


HANDLERS: dict[str, JobHandler] = {
    "fetch_all": handle_fetch_all,
    "sync_source": handle_sync_source,
    "preview_source": handle_preview_source,
    "fetch_source": handle_fetch_source,
    "browser_fetch": handle_browser_fetch,
    "analyze_message": handle_analyze_message,
}

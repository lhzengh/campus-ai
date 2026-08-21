from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from campus_ai.ai.openai_compatible import OpenAICompatibleProvider
from campus_ai.config import get_settings
from campus_ai.jobs import enqueue_job
from campus_ai.models import Analysis, Message, Source
from campus_ai.sources.base import DiscoveredItem, NormalizedMessage
from campus_ai.sources.playwright_portal import PortalBrowserSession
from campus_ai.sources.static_http import StaticHttpSourceAdapter


JobHandler = Callable[[Session, dict[str, Any]], None]


def _content_hash(title: str, body: str) -> str:
    normalized = "\n".join((title.strip(), body.strip()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _persist_message(session: Session, source: Source, normalized: NormalizedMessage) -> Message | None:
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
            metadata_json=normalized.metadata,
        )
        session.add(message)
    else:
        existing.url = normalized.url
        existing.title = normalized.title
        existing.body = normalized.body
        existing.published_at = normalized.published_at
        existing.content_hash = content_hash
        existing.metadata_json = normalized.metadata
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
    sources = session.scalars(select(Source).where(Source.enabled.is_(True))).all()
    for source in sources:
        job_kind = "browser_fetch" if source.kind == "playwright_portal" else "fetch_source"
        enqueue_job(
            session,
            kind=job_kind,
            payload={"source_id": source.id},
            dedupe_key=f"fetch-source:{source.id}:{run_key}",
            max_attempts=3,
        )


def handle_fetch_source(session: Session, payload: dict[str, Any]) -> None:
    source_id = str(payload["source_id"])
    source = session.get(Source, source_id)
    if source is None or not source.enabled:
        raise ValueError(f"Enabled source not found: {source_id}")
    if source.kind != "static_http":
        raise ValueError(f"Unsupported source kind for this worker: {source.kind}")

    adapter = StaticHttpSourceAdapter(**source.config)
    adapter.health_check()
    for item in adapter.discover():
        raw = adapter.fetch(item)
        normalized = adapter.normalize(item, raw)
        _persist_message(session, source, normalized)


def handle_browser_fetch(session: Session, payload: dict[str, Any]) -> None:
    settings = get_settings()
    source = session.get(Source, str(payload["source_id"]))
    if source is None or not source.enabled or source.kind != "playwright_portal":
        raise ValueError("Enabled Playwright portal source not found")
    config = dict(source.config)
    url = str(config.pop("url"))
    encrypted_state_path = Path(str(config.pop("encrypted_state_path", "/app/data/sessions/portal.enc")))
    portal = PortalBrowserSession(encrypted_state_path, settings.secret_key)
    raw = portal.open_authenticated_page(url, headless=True)
    adapter = StaticHttpSourceAdapter(
        index_url=url,
        item_link_selector="a",
        title_selector=str(config["title_selector"]),
        body_selector=str(config["body_selector"]),
        published_selector=config.get("published_selector"),
        published_format=config.get("published_format"),
        timezone_name=str(config.get("timezone_name", settings.timezone)),
        request_interval_seconds=0,
    )
    external_id = hashlib.sha256(url.encode("utf-8")).hexdigest()
    normalized = adapter.normalize(DiscoveredItem(external_id=external_id, url=url), raw)
    _persist_message(session, source, normalized)


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
    "fetch_source": handle_fetch_source,
    "browser_fetch": handle_browser_fetch,
    "analyze_message": handle_analyze_message,
}

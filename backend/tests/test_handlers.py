from __future__ import annotations

from datetime import datetime

from campus_connector_sdk import CampusItem, CampusItemBatch
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from campus_ai.handlers import _persist_message, handle_fetch_all, handle_preview_source, handle_sync_source
from campus_ai.models import Job, Message, Source


class FakeConnectorClient:
    def sync(self, request) -> CampusItemBatch:
        return CampusItemBatch(
            items=[
                CampusItem(
                    external_id="notice-1",
                    source_url="https://campus.example/notice/1",
                    title="考试安排",
                    content_text="考试时间为2026年9月1日。",
                    published_at=datetime.fromisoformat("2026-08-19T08:00:00+08:00"),
                )
            ],
            next_cursor={"last": "notice-1"},
        )


class FakeConnectorRegistry:
    def get(self, connector_id: str, *, expected_version: str | None = None) -> FakeConnectorClient:
        assert connector_id == "example.static"
        return FakeConnectorClient()


def test_fetch_all_enqueues_each_enabled_source(session: Session) -> None:
    session.add_all(
        [
            Source(name="enabled", connector_id="example.static", enabled=True, config={}),
            Source(name="disabled", connector_id="example.static", enabled=False, config={}),
        ]
    )
    session.commit()

    handle_fetch_all(session, {"run_key": "2026-08-19"})
    jobs = session.scalars(select(Job)).all()
    assert len(jobs) == 1
    assert jobs[0].kind == "sync_source"


def test_fetch_source_is_incremental_and_enqueues_analysis(session: Session, monkeypatch) -> None:
    source = Source(name="public", connector_id="example.static", enabled=True, config={})
    session.add(source)
    session.commit()
    monkeypatch.setattr("campus_ai.handlers.get_connector_registry", lambda: FakeConnectorRegistry())

    first = handle_sync_source(session, {"source_id": source.id})
    second = handle_sync_source(session, {"source_id": source.id})

    assert session.scalar(select(func.count()).select_from(Message)) == 1
    analysis_jobs = session.scalars(select(Job).where(Job.kind == "analyze_message")).all()
    assert len(analysis_jobs) == 1
    assert source.sync_cursor == {"last": "notice-1"}
    assert first["created"] == 1
    assert second["unchanged"] == 1


def test_distinct_external_ids_are_not_deduplicated_by_content(session: Session) -> None:
    source = Source(name="public", connector_id="example.static", enabled=True, config={})
    session.add(source)
    session.commit()

    for external_id in ("notice-1", "notice-2"):
        _persist_message(
            session,
            source,
            CampusItem(
                external_id=external_id,
                source_url=f"https://campus.example/{external_id}",
                title="Shared title",
                content_text="Shared body",
            ),
        )

    assert session.scalar(select(func.count()).select_from(Message)) == 2


def test_preview_does_not_persist_messages_or_advance_cursor(session: Session, monkeypatch) -> None:
    source = Source(
        name="public",
        connector_id="example.static",
        enabled=True,
        config={},
        sync_cursor={"before": "preview"},
    )
    session.add(source)
    session.commit()
    monkeypatch.setattr("campus_ai.handlers.get_connector_registry", lambda: FakeConnectorRegistry())

    result = handle_preview_source(session, {"source_id": source.id, "max_items": 10})

    assert result["items_seen"] == 1
    assert session.scalar(select(func.count()).select_from(Message)) == 0
    assert source.sync_cursor == {"before": "preview"}

from __future__ import annotations

from datetime import datetime

from campus_connector_sdk import ConnectorMessage, SyncBatch
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from campus_ai.handlers import handle_fetch_all, handle_sync_source
from campus_ai.models import Job, Message, Source


class FakeConnectorClient:
    def sync(self, request) -> SyncBatch:
        return SyncBatch(
            items=[
                ConnectorMessage(
                    external_id="notice-1",
                    url="https://campus.example/notice/1",
                    title="考试安排",
                    body="考试时间为2026年9月1日。",
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

    handle_sync_source(session, {"source_id": source.id})
    handle_sync_source(session, {"source_id": source.id})

    assert session.scalar(select(func.count()).select_from(Message)) == 1
    analysis_jobs = session.scalars(select(Job).where(Job.kind == "analyze_message")).all()
    assert len(analysis_jobs) == 1
    assert source.sync_cursor == {"last": "notice-1"}

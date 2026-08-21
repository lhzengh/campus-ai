from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from campus_ai.handlers import handle_fetch_all, handle_fetch_source
from campus_ai.models import Job, Message, Source
from campus_ai.sources.base import DiscoveredItem, NormalizedMessage


class FakeSourceAdapter:
    def __init__(self, **config) -> None:
        self.config = config

    def health_check(self) -> None:
        return None

    def discover(self) -> list[DiscoveredItem]:
        return [DiscoveredItem(external_id="notice-1", url="https://campus.example/notice/1")]

    def fetch(self, item: DiscoveredItem) -> str:
        return "raw"

    def normalize(self, item: DiscoveredItem, raw: str) -> NormalizedMessage:
        return NormalizedMessage(
            external_id=item.external_id,
            url=item.url,
            title="考试安排",
            body="考试时间为2026年9月1日。",
            published_at=datetime.fromisoformat("2026-08-19T08:00:00+08:00"),
        )


def test_fetch_all_enqueues_each_enabled_source(session: Session) -> None:
    session.add_all(
        [
            Source(name="enabled", kind="static_http", enabled=True, config={}),
            Source(name="disabled", kind="static_http", enabled=False, config={}),
        ]
    )
    session.commit()

    handle_fetch_all(session, {"run_key": "2026-08-19"})
    jobs = session.scalars(select(Job)).all()
    assert len(jobs) == 1
    assert jobs[0].kind == "fetch_source"


def test_fetch_source_is_incremental_and_enqueues_analysis(session: Session, monkeypatch) -> None:
    source = Source(name="public", kind="static_http", enabled=True, config={})
    session.add(source)
    session.commit()
    monkeypatch.setattr("campus_ai.handlers.StaticHttpSourceAdapter", FakeSourceAdapter)

    handle_fetch_source(session, {"source_id": source.id})
    handle_fetch_source(session, {"source_id": source.id})

    assert session.scalar(select(func.count()).select_from(Message)) == 1
    analysis_jobs = session.scalars(select(Job).where(Job.kind == "analyze_message")).all()
    assert len(analysis_jobs) == 1

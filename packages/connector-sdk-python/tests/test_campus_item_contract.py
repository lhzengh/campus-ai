from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from campus_connector_sdk import (
    AttachmentAccess,
    AttachmentAccessMode,
    CampusItem,
    CampusItemBatch,
)


def test_campus_item_requires_safe_source_facts() -> None:
    item = CampusItem(
        external_id="notice-1",
        source_url="https://campus.example/notices/1",
        title="Notice",
        content_text="Body",
        published_at=datetime.fromisoformat("2026-08-21T08:00:00+08:00"),
        extensions={"example.portal": {"section": "academic"}},
    )

    assert item.item_type.value == "announcement"
    assert item.published_at is not None and item.published_at.utcoffset() is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_url", "https://user:password@campus.example/notices/1"),
        ("published_at", datetime(2026, 8, 21, 8, 0, 0)),
        ("extensions", {"not namespaced": {}}),
    ],
)
def test_campus_item_rejects_unsafe_or_ambiguous_values(field: str, value: object) -> None:
    payload: dict[str, object] = {
        "external_id": "notice-1",
        "source_url": "https://campus.example/notices/1",
        "title": "Notice",
        "content_text": "Body",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        CampusItem.model_validate(payload)


def test_attachment_access_modes_are_unambiguous() -> None:
    public = AttachmentAccess(
        mode=AttachmentAccessMode.PUBLIC_URL,
        url="https://campus.example/file.pdf",
    )
    private = AttachmentAccess(
        mode=AttachmentAccessMode.CONNECTOR_FETCH,
        ref="opaque-reference",
    )

    assert public.url is not None and public.ref is None
    assert private.ref == "opaque-reference" and private.url is None

    with pytest.raises(ValidationError):
        AttachmentAccess(mode=AttachmentAccessMode.PUBLIC_URL, ref="not-a-url")


def test_paginated_batch_requires_a_cursor() -> None:
    with pytest.raises(ValidationError):
        CampusItemBatch(has_more=True)

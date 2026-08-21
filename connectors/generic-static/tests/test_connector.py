from __future__ import annotations

import httpx
import pytest

from campus_connector_sdk import ConnectorErrorCode, ConnectorProtocolError, SyncRequest
from campus_connector_sdk.testing import assert_connector_conformance
from campus_ai_connector_generic_static import GenericStaticConnector


INDEX = """
<html><body>
  <a class="notice" href="/notice/1#detail">First</a>
  <a class="notice" href="/notice/1">Duplicate</a>
  <a class="notice" href="https://outside.example/notice/2">Outside</a>
</body></html>
"""

ARTICLE = """
<html><body>
  <h1>Course registration notice</h1>
  <time>2026-08-21 17:00</time>
  <article><p>Confirm registration before the deadline.</p></article>
</body></html>
"""

CONFIG: dict[str, object] = {
    "index_url": "https://campus.example/notices",
    "allowed_hosts": ["campus.example"],
    "item_link_selector": "a.notice",
    "title_selector": "h1",
    "body_selector": "article",
    "published_selector": "time",
    "published_format": "%Y-%m-%d %H:%M",
    "request_interval_seconds": 0,
}


def build_connector() -> GenericStaticConnector:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/notices":
            return httpx.Response(200, text=INDEX)
        if request.url.path == "/notice/1":
            return httpx.Response(200, text=ARTICLE)
        return httpx.Response(404)

    return GenericStaticConnector(client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_connector_is_conformant_and_incremental() -> None:
    connector = build_connector()
    assert_connector_conformance(connector, valid_config=CONFIG)

    first = connector.sync(SyncRequest(instance_id="source", config=CONFIG, max_items=10))
    second = connector.sync(
        SyncRequest(instance_id="source", config=CONFIG, cursor=first.next_cursor, max_items=10)
    )

    assert len(first.items) == 1
    assert first.items[0].title == "Course registration notice"
    assert first.items[0].published_at is not None
    assert second.items == []


def test_connector_requires_an_explicit_allowlist() -> None:
    connector = build_connector()
    invalid = dict(CONFIG)
    invalid["allowed_hosts"] = ["other.example"]

    with pytest.raises(ConnectorProtocolError) as raised:
        connector.validate_config(invalid)

    assert raised.value.code is ConnectorErrorCode.CONFIG_INVALID


def test_connector_blocks_redirects_outside_allowlist() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/notices":
            return httpx.Response(302, headers={"location": "https://outside.example/notices"})
        raise AssertionError("The outside host must never be requested")

    connector = GenericStaticConnector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ConnectorProtocolError) as raised:
        connector.sync(SyncRequest(instance_id="source", config=CONFIG))

    assert raised.value.code is ConnectorErrorCode.ACCESS_DENIED

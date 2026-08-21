from __future__ import annotations

import httpx

from campus_ai.sources.static_http import StaticHttpSourceAdapter


INDEX = """
<html><body>
  <a class="notice" href="/notice/1#detail">第一条</a>
  <a class="notice" href="/notice/1">重复链接</a>
</body></html>
"""

ARTICLE = """
<html><body>
  <h1>课程补选确认通知</h1>
  <time>2026-08-21 17:00</time>
  <article><p>请在截止时间前登录教务系统确认。</p></article>
</body></html>
"""


def test_static_source_discovers_deduplicates_and_normalizes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/notices":
            return httpx.Response(200, text=INDEX)
        if request.url.path == "/notice/1":
            return httpx.Response(200, text=ARTICLE)
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = StaticHttpSourceAdapter(
        index_url="https://campus.example/notices",
        item_link_selector="a.notice",
        title_selector="h1",
        body_selector="article",
        published_selector="time",
        published_format="%Y-%m-%d %H:%M",
        request_interval_seconds=0,
        client=client,
    )

    adapter.health_check()
    discovered = adapter.discover()
    assert len(discovered) == 1
    message = adapter.normalize(discovered[0], adapter.fetch(discovered[0]))
    assert message.title == "课程补选确认通知"
    assert "教务系统" in message.body
    assert message.published_at is not None
    assert message.published_at.year == 2026
    assert message.published_at.utcoffset() is not None

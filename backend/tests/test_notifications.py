from __future__ import annotations

import json

import httpx

from campus_ai.notifications import NotificationEvent, UnifiedPushNotificationChannel


def test_unified_push_posts_structured_event() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(201, headers={"X-Message-Id": "message-1"})

    channel = UnifiedPushNotificationChannel(client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = channel.send(
        endpoint="https://push.example/device-token",
        event=NotificationEvent(
            event_key="important:message-1",
            title="重要校园消息",
            body="请在周五前确认课程。",
            data={"message_id": "message-1"},
        ),
    )

    assert captured["event_key"] == "important:message-1"
    assert result.provider_message_id == "message-1"

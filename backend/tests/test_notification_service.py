from __future__ import annotations

from sqlalchemy.orm import Session

from campus_ai.notification_service import send_once
from campus_ai.notifications.base import NotificationChannel, NotificationEvent, NotificationResult


class FakeChannel(NotificationChannel):
    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def send(self, *, endpoint: str, event: NotificationEvent) -> NotificationResult:
        self.calls += 1
        return NotificationResult(provider_message_id="provider-1", response={"endpoint": endpoint})


class FlakyChannel(FakeChannel):
    name = "flaky"

    def send(self, *, endpoint: str, event: NotificationEvent) -> NotificationResult:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary")
        return NotificationResult(provider_message_id="provider-2", response={})


def test_send_once_deduplicates_delivery(session: Session) -> None:
    channel = FakeChannel()
    event = NotificationEvent(event_key="event-1", title="Title", body="Body")

    first, first_sent = send_once(
        session,
        channel=channel,
        device_id="device-1",
        endpoint="endpoint-1",
        event=event,
    )
    second, second_sent = send_once(
        session,
        channel=channel,
        device_id="device-1",
        endpoint="endpoint-1",
        event=event,
    )

    assert first.id == second.id
    assert first_sent is True
    assert second_sent is False
    assert channel.calls == 1


def test_failed_delivery_can_be_retried(session: Session) -> None:
    channel = FlakyChannel()
    event = NotificationEvent(event_key="event-retry", title="Title", body="Body")

    try:
        send_once(session, channel=channel, device_id="device-1", endpoint="endpoint-1", event=event)
    except RuntimeError:
        pass
    else:
        raise AssertionError("First delivery should fail")

    delivery, sent = send_once(
        session,
        channel=channel,
        device_id="device-1",
        endpoint="endpoint-1",
        event=event,
    )
    assert sent is True
    assert delivery.status == "accepted"
    assert channel.calls == 2

"""Deliver self-hostable push messages to UnifiedPush distributor endpoints."""

from __future__ import annotations

import json

import httpx

from campus_ai.notifications.base import NotificationChannel, NotificationEvent, NotificationResult


class UnifiedPushNotificationChannel(NotificationChannel):
    """Send to the per-device endpoint supplied by a UnifiedPush distributor."""

    name = "unified_push"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=httpx.Timeout(20))

    def send(self, *, endpoint: str, event: NotificationEvent) -> NotificationResult:
        """Post the neutral event payload directly to a device endpoint."""

        payload = {
            "event_key": event.event_key,
            "title": event.title,
            "body": event.body,
            "data": event.data,
        }
        response = self.client.post(
            endpoint,
            content=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        response.raise_for_status()
        provider_message_id = response.headers.get("X-Message-Id")
        return NotificationResult(
            provider_message_id=provider_message_id,
            response={"status_code": response.status_code},
        )

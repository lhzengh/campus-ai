from __future__ import annotations

from pathlib import Path

import google.auth.transport.requests
import httpx
from google.oauth2 import service_account

from campus_ai.notifications.base import NotificationChannel, NotificationEvent, NotificationResult


FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


class FcmNotificationChannel(NotificationChannel):
    name = "fcm"

    def __init__(
        self,
        *,
        project_id: str,
        credentials_path: Path,
        client: httpx.Client | None = None,
    ) -> None:
        self.project_id = project_id
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=[FCM_SCOPE],
        )
        self.client = client or httpx.Client(timeout=httpx.Timeout(20))

    def _access_token(self) -> str:
        request = google.auth.transport.requests.Request()
        self.credentials.refresh(request)
        if not self.credentials.token:
            raise RuntimeError("FCM credentials did not produce an access token")
        return self.credentials.token

    def send(self, *, endpoint: str, event: NotificationEvent) -> NotificationResult:
        response = self.client.post(
            f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send",
            headers={"Authorization": f"Bearer {self._access_token()}"},
            json={
                "message": {
                    "token": endpoint,
                    "notification": {"title": event.title, "body": event.body},
                    "data": {"event_key": event.event_key, **event.data},
                    "android": {"priority": "high"},
                }
            },
        )
        response.raise_for_status()
        data = response.json()
        return NotificationResult(provider_message_id=data.get("name"), response=data)

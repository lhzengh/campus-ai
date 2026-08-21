from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    event_key: str
    title: str
    body: str
    data: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NotificationResult:
    provider_message_id: str | None
    response: dict[str, Any]


class NotificationChannel(ABC):
    name: str

    @abstractmethod
    def send(self, *, endpoint: str, event: NotificationEvent) -> NotificationResult:
        """Send one notification to a registered device endpoint."""

"""Define provider-neutral notification events and channel interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    """One stable event that can be delivered through multiple transports."""

    event_key: str
    title: str
    body: str
    data: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NotificationResult:
    """Normalized provider acknowledgement retained for diagnostics."""

    provider_message_id: str | None
    response: dict[str, Any]


class NotificationChannel(ABC):
    """Transport boundary implemented by each notification provider."""

    name: str

    @abstractmethod
    def send(self, *, endpoint: str, event: NotificationEvent) -> NotificationResult:
        """Send one notification to a registered device endpoint."""

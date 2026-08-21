from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class DiscoveredItem:
    external_id: str
    url: str


@dataclass(frozen=True, slots=True)
class NormalizedMessage:
    external_id: str
    url: str
    title: str
    body: str
    published_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(ABC):
    @abstractmethod
    def health_check(self) -> None:
        """Raise an exception when the source is not currently available."""

    @abstractmethod
    def discover(self) -> list[DiscoveredItem]:
        """Discover candidate items without parsing all article content."""

    @abstractmethod
    def fetch(self, item: DiscoveredItem) -> str:
        """Fetch a discovered item's raw representation."""

    @abstractmethod
    def normalize(self, item: DiscoveredItem, raw: str) -> NormalizedMessage:
        """Convert raw source content into the canonical message representation."""

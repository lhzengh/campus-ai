from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from campus_ai.schemas import AnalysisResult


@dataclass(frozen=True, slots=True)
class AIResponse:
    result: AnalysisResult
    latency_ms: int
    usage: dict[str, Any] = field(default_factory=dict)


class AIProvider(ABC):
    @abstractmethod
    def analyze(self, *, title: str, body: str, profile: dict[str, Any]) -> AIResponse:
        """Analyze a normalized campus message."""

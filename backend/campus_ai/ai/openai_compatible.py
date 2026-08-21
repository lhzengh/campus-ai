from __future__ import annotations

import json
import time
from typing import Any

import httpx

from campus_ai.ai.base import AIProvider, AIResponse
from campus_ai.schemas import AnalysisResult


SYSTEM_PROMPT = """你是校园消息分析器。只根据给出的原文和用户画像提取信息。
不得编造日期、适用对象、行动项或链接；无法判断时使用 unknown、空数组或低置信度。
证据字段必须是原文中的简短片段。输出必须符合给定 JSON Schema。"""


class OpenAICompatibleProvider(AIProvider):
    prompt_version = "campus-message-v1"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        output_mode: str = "json_schema",
        timeout_seconds: float = 60,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url or not api_key or not model:
            raise ValueError("Cloud AI base URL, API key and model are required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.output_mode = output_mode
        self.client = client or httpx.Client(timeout=httpx.Timeout(timeout_seconds))

    def _response_format(self) -> dict[str, Any]:
        if self.output_mode == "json_object":
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "campus_message_analysis",
                "strict": True,
                "schema": AnalysisResult.model_json_schema(),
            },
        }

    def analyze(self, *, title: str, body: str, profile: dict[str, Any]) -> AIResponse:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"profile": profile, "message": {"title": title, "body": body}},
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": self._response_format(),
        }
        started = time.monotonic()
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        latency_ms = round((time.monotonic() - started) * 1000)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Cloud AI response did not contain message content") from exc
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        result = AnalysisResult.model_validate_json(content)
        return AIResponse(result=result, latency_ms=latency_ms, usage=data.get("usage", {}))

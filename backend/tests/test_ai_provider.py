from __future__ import annotations

import json

import httpx

from campus_ai.ai.openai_compatible import OpenAICompatibleProvider


VALID_ANALYSIS = {
    "category": "academic",
    "summary_short": "本周五前完成课程补选确认。",
    "summary_detail": "学生需要登录教务系统确认课程补选结果。",
    "relevance_score": 90,
    "importance_score": 88,
    "urgency": "high",
    "audience": ["相关课程学生"],
    "action_items": ["登录教务系统确认"],
    "deadlines": [
        {
            "time": "2026-08-21T17:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "all_day": False,
            "confidence": 0.98,
            "evidence": "8月21日17:00前",
        }
    ],
    "reason": "存在明确且临近的办理截止时间",
    "evidence": ["请于8月21日17:00前完成确认"],
    "confidence": 0.95,
}


def test_openai_compatible_provider_validates_structured_response() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(VALID_ANALYSIS, ensure_ascii=False)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 80},
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://ai.example/v1",
        api_key="test-secret",
        model="test-model",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    response = provider.analyze(
        title="补选通知",
        body="请于8月21日17:00前完成确认",
        profile={"identity": "本科生"},
    )

    assert response.result.importance_score == 88
    assert response.result.deadlines[0].time is not None
    assert response.usage["prompt_tokens"] == 100
    assert captured["response_format"]["type"] == "json_schema"  # type: ignore[index]

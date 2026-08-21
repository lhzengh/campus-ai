#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any

from campus_ai.ai.openai_compatible import OpenAICompatibleProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an OpenAI-compatible model on annotated campus messages.")
    parser.add_argument("dataset", type=Path, help="JSONL evaluation dataset")
    parser.add_argument("--max-cost-cny", type=float, default=20)
    parser.add_argument("--input-cny-per-million", type=float, required=True)
    parser.add_argument("--output-cny-per-million", type=float, required=True)
    return parser.parse_args()


def normalized_deadlines(value: list[dict[str, Any]]) -> set[str]:
    result = set()
    for deadline in value:
        raw = deadline.get("time")
        if raw:
            result.add(str(raw)[:10])
    return result


def main() -> int:
    args = parse_args()
    provider = OpenAICompatibleProvider(
        base_url=os.environ.get("CAMPUS_AI_API_BASE_URL", ""),
        api_key=os.environ.get("CAMPUS_AI_API_KEY", ""),
        model=os.environ.get("CAMPUS_AI_MODEL", ""),
        output_mode=os.environ.get("CAMPUS_AI_AI_OUTPUT_MODE", "json_schema"),
    )
    rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    important_total = important_found = schema_success = deadline_total = deadline_correct = 0
    input_tokens = output_tokens = 0
    latencies: list[int] = []
    failures: list[dict[str, str]] = []

    for row in rows:
        try:
            response = provider.analyze(title=row["title"], body=row["body"], profile=row.get("profile", {}))
            schema_success += 1
            latencies.append(response.latency_ms)
            input_tokens += int(response.usage.get("prompt_tokens", 0))
            output_tokens += int(response.usage.get("completion_tokens", 0))
            expected_important = bool(row["expected"].get("important"))
            if expected_important:
                important_total += 1
                if response.result.importance_score >= 70:
                    important_found += 1
            expected_deadlines = set(row["expected"].get("deadline_dates", []))
            if expected_deadlines:
                deadline_total += 1
                actual = normalized_deadlines([item.model_dump(mode="json") for item in response.result.deadlines])
                if actual == expected_deadlines:
                    deadline_correct += 1
        except Exception as exc:
            failures.append({"id": str(row.get("id", "unknown")), "error": f"{type(exc).__name__}: {exc}"})

    estimated_cost = (
        input_tokens * args.input_cny_per_million + output_tokens * args.output_cny_per_million
    ) / 1_000_000
    report = {
        "total": len(rows),
        "schema_success_rate": schema_success / len(rows) if rows else 0,
        "important_recall": important_found / important_total if important_total else None,
        "deadline_accuracy": deadline_correct / deadline_total if deadline_total else None,
        "latency_ms_p50": statistics.median(latencies) if latencies else None,
        "latency_ms_max": max(latencies) if latencies else None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_cny": round(estimated_cost, 4),
        "cost_limit_cny": args.max_cost_cny,
        "failures": failures,
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    print()
    passed = (
        report["schema_success_rate"] >= 0.99
        and (report["important_recall"] is None or report["important_recall"] >= 0.95)
        and (report["deadline_accuracy"] is None or report["deadline_accuracy"] >= 0.95)
        and estimated_cost <= args.max_cost_cny
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

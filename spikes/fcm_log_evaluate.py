#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


MARKER = "CAMPUS_AI_FCM_RECEIVED "


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate FCM receipt records captured from adb logcat.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--expected", type=int, default=20)
    parser.add_argument("--run-id")
    return parser.parse_args()


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def main() -> int:
    args = parse_args()
    records: list[dict[str, Any]] = []
    for line in args.log.read_text(encoding="utf-8", errors="replace").splitlines():
        if MARKER not in line:
            continue
        try:
            record = json.loads(line.split(MARKER, 1)[1])
        except json.JSONDecodeError:
            continue
        if args.run_id and record.get("run_id") != args.run_id:
            continue
        records.append(record)

    keys = [record.get("event_key") for record in records if record.get("event_key")]
    unique_keys = set(keys)
    duplicates = len(keys) - len(unique_keys)
    latencies = []
    for record in records:
        sent = parse_timestamp(record.get("sent_at"))
        received = parse_timestamp(record.get("received_at"))
        if sent is not None and received is not None:
            latencies.append(max(0.0, (received - sent).total_seconds() * 1000))
    latencies.sort()
    p95_ms = latencies[max(0, math.ceil(len(latencies) * 0.95) - 1)] if latencies else None
    delivery_rate = len(unique_keys) / args.expected if args.expected else 0.0
    passed = delivery_rate >= 0.95 and duplicates == 0 and p95_ms is not None and p95_ms <= 60_000
    print(
        json.dumps(
            {
                "expected": args.expected,
                "received": len(records),
                "unique": len(unique_keys),
                "duplicates": duplicates,
                "delivery_rate": round(delivery_rate, 4),
                "p95_latency_ms": round(p95_ms, 1) if p95_ms is not None else None,
                "passed": passed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

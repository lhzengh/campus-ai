#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from campus_ai.sources.static_http import StaticHttpSourceAdapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe one public campus source using CSS selectors.")
    parser.add_argument("config", type=Path, help="Path to a JSON source configuration")
    parser.add_argument("--limit", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    adapter = StaticHttpSourceAdapter(**config)
    report: dict[str, object] = {"source": config.get("index_url"), "requested_limit": args.limit}
    started = time.monotonic()
    try:
        adapter.health_check()
        items = adapter.discover()[: args.limit]
        parsed = []
        errors = []
        for item in items:
            try:
                message = adapter.normalize(item, adapter.fetch(item))
                parsed.append(
                    {
                        "external_id": message.external_id,
                        "url": message.url,
                        "has_title": bool(message.title),
                        "body_length": len(message.body),
                        "published_at": message.published_at.isoformat() if message.published_at else None,
                    }
                )
            except Exception as exc:
                errors.append({"url": item.url, "error": f"{type(exc).__name__}: {exc}"})
        report.update(
            {
                "discovered": len(items),
                "parsed": len(parsed),
                "success_rate": len(parsed) / len(items) if items else 0,
                "items": parsed,
                "errors": errors,
            }
        )
    except Exception as exc:
        report["fatal_error"] = f"{type(exc).__name__}: {exc}"
    report["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0 if report.get("success_rate", 0) >= 0.98 else 1


if __name__ == "__main__":
    raise SystemExit(main())

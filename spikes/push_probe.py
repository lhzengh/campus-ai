#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

from campus_ai.notifications import FcmNotificationChannel, NotificationEvent, UnifiedPushNotificationChannel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a batch of uniquely identified push probes.")
    subparsers = parser.add_subparsers(dest="channel", required=True)
    unified = subparsers.add_parser("unified-push")
    unified.add_argument("endpoint")
    fcm = subparsers.add_parser("fcm")
    fcm.add_argument("token")
    fcm.add_argument("--project-id", required=True)
    fcm.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--interval", type=float, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.channel == "fcm":
        channel = FcmNotificationChannel(project_id=args.project_id, credentials_path=args.credentials)
        endpoint = args.token
    else:
        channel = UnifiedPushNotificationChannel()
        endpoint = args.endpoint

    run_id = str(uuid.uuid4())
    accepted = []
    failures = []
    for index in range(args.count):
        event = NotificationEvent(
            event_key=f"probe:{run_id}:{index}",
            title="Campus AI 推送验证",
            body=f"验证消息 {index + 1}/{args.count}",
            data={
                "run_id": run_id,
                "sequence": str(index),
                "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
        started = time.monotonic()
        try:
            result = channel.send(endpoint=endpoint, event=event)
            accepted.append(
                {
                    "sequence": index,
                    "provider_message_id": result.provider_message_id,
                    "request_ms": round((time.monotonic() - started) * 1000),
                }
            )
        except Exception as exc:
            failures.append({"sequence": index, "error": f"{type(exc).__name__}: {exc}"})
        time.sleep(args.interval)
    print(json.dumps({"run_id": run_id, "accepted": accepted, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

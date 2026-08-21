from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from spikes import fcm_log_evaluate


def test_fcm_log_evaluator_reports_delivery_metrics(tmp_path, monkeypatch, capsys) -> None:
    started = datetime(2026, 8, 19, tzinfo=timezone.utc)
    lines = []
    for index in range(20):
        record = {
            "event_key": f"probe:run-1:{index}",
            "run_id": "run-1",
            "sequence": str(index),
            "sent_at": started.isoformat(),
            "received_at": (started + timedelta(seconds=index)).isoformat(),
        }
        lines.append(f"I/flutter: {fcm_log_evaluate.MARKER}{json.dumps(record)}")
    log = tmp_path / "fcm.log"
    log.write_text("\n".join(lines), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["fcm_log_evaluate.py", str(log), "--expected", "20", "--run-id", "run-1"],
    )

    assert fcm_log_evaluate.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["delivery_rate"] == 1.0
    assert result["duplicates"] == 0
    assert result["p95_latency_ms"] == 18000.0
    assert result["passed"] is True

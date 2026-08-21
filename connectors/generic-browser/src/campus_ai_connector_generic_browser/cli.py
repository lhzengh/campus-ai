from __future__ import annotations

import argparse
import os
from pathlib import Path

from campus_ai_connector_generic_browser.session import EncryptedBrowserSession


def main() -> None:
    """Capture a session locally without sending credentials through Core."""

    parser = argparse.ArgumentParser(description="Capture a user-assisted encrypted browser session")
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--login-url", required=True)
    parser.add_argument("--success-url-pattern", required=True)
    parser.add_argument("--allowed-host", action="append", required=True)
    parser.add_argument("--timeout-ms", type=int, default=180_000)
    args = parser.parse_args()

    session = EncryptedBrowserSession(
        Path(os.environ.get("CAMPUS_CONNECTOR_SESSION_DIR", "/app/data/sessions")),
        os.environ.get("CAMPUS_CONNECTOR_SESSION_KEY", ""),
    )
    session.capture_user_login(
        args.instance_id,
        args.login_url,
        success_url_pattern=args.success_url_pattern,
        allowed_hosts={host.lower().rstrip(".") for host in args.allowed_host},
        timeout_ms=args.timeout_ms,
    )

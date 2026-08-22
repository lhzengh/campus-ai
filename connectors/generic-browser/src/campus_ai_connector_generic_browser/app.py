"""ASGI application for the authenticated-browser Connector process."""

from __future__ import annotations

import os
from pathlib import Path

from campus_connector_sdk import create_connector_app
from campus_ai_connector_generic_browser.connector import GenericBrowserConnector


app = create_connector_app(
    GenericBrowserConnector(
        session_directory=Path(os.environ.get("CAMPUS_CONNECTOR_SESSION_DIR", "/app/data/sessions")),
        secret_key=os.environ.get("CAMPUS_CONNECTOR_SESSION_KEY", ""),
    ),
    shared_token=os.environ.get("CAMPUS_CONNECTOR_SHARED_TOKEN", ""),
)

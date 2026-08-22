"""ASGI application for the generic static-site Connector process."""

from __future__ import annotations

import os

from campus_connector_sdk import create_connector_app
from campus_ai_connector_generic_static.connector import GenericStaticConnector


app = create_connector_app(
    GenericStaticConnector(),
    shared_token=os.environ.get("CAMPUS_CONNECTOR_SHARED_TOKEN", ""),
)

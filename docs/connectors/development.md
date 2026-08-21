# Connector Development Guide

Campus AI Connectors are independent services. A Connector may live in this Monorepo or another repository, but it depends only on the public Connector SDK and protocol—not on `campus_ai` Core modules or the Core database.

## Required implementation

A Python Connector subclasses `CampusConnector` and implements:

```python
from campus_connector_sdk import CampusConnector, ConnectorManifest, SyncBatch, SyncRequest


class MyConnector(CampusConnector):
    @property
    def manifest(self) -> ConnectorManifest:
        ...

    def validate_config(self, config: dict[str, object]) -> dict[str, object]:
        ...

    def sync(self, request: SyncRequest) -> SyncBatch:
        ...
```

Override `auth_status`, `begin_auth`, and `submit_auth_response` only when the source requires interactive authentication. Passwords, SMS codes, CAPTCHAs, cookies, and tokens must not be placed in ordinary config, fixtures, logs, or the repository.

## Manifest and configuration

Use a globally stable lowercase Connector ID such as `publisher.connector-name`. The Manifest declares the implementation version, Connector API version, capabilities, browser requirement, and a JSON Schema for non-secret configuration.

Configuration keys marked with `x-campus-secret: true` are never accepted by Core's ordinary source-creation flow. Authentication challenges or a future Secret broker carry those values transiently. Every network-capable Connector should require an explicit host allowlist and reject URLs containing user information.

## Standard output

`SyncBatch` contains normalized `ConnectorMessage` records, an opaque next cursor, a `has_more` flag, authentication state, and non-fatal warnings. Core owns database IDs, deduplication, AI analysis, notifications, and retry policy. A Connector must not write to Core storage.

## Local validation

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -e packages/connector-sdk-python
.venv/bin/pip install -e 'connectors/generic-static[dev]'
PYTHONPATH=packages/connector-sdk-python/src:connectors/generic-static/src \
  .venv/bin/pytest connectors/generic-static/tests
```

Use `campus_connector_sdk.testing.assert_connector_conformance` in each Connector test suite. Add source-specific, anonymized parser fixtures alongside the generic conformance tests.

## Deployment

Build and run the Connector independently, then register its internal HTTPS or trusted-network HTTP address in Core's runtime Connector endpoint map. Protect protocol endpoints with a generated shared token. Do not expose Connector containers directly to clients or the public internet.

The two initial examples are:

- `connectors/generic-static`: static announcement lists with runtime CSS selectors and a strict host allowlist.
- `connectors/generic-browser`: one authenticated Playwright page with Connector-owned encrypted session state and an operator-assisted login command.

The generic browser example is a validation implementation. A production school-specific Connector should model the site's exact permitted login and navigation workflow and provide regression fixtures without embedding a real institution URL or account.

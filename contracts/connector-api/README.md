# Campus AI Connector API

The Connector API is the only runtime boundary between Campus AI Core and a source-specific Connector. Its current contract version is `1.0`.

- [`openapi.yaml`](openapi.yaml) defines the language-neutral HTTP/JSON surface.
- `packages/connector-sdk-python` provides the first implementation SDK and FastAPI service wrapper.
- A Connector must return a Manifest whose `connector_id` matches the ID registered in Core.
- Contract major versions must match. Connector implementation versions may be pinned per source instance.
- Core supplies non-secret instance configuration and an opaque cursor. Connector returns a versioned `CampusItemBatch` and the next cursor. The normative field semantics are documented in [`docs/connectors/campus-item-contract.md`](../../docs/connectors/campus-item-contract.md).
- Interactive authentication uses generic status/challenge endpoints. Clients never call these endpoints directly; Core forwards authorized requests.
- Deployments must protect non-health endpoints with an internal bearer token and a trusted network or TLS boundary.

The OpenAPI file is intentionally independent of the Python SDK so a Connector can be implemented in another language.

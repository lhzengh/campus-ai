# Campus AI Client API

The Client API is the only boundary used by Flutter clients. The current implementation is exposed by Core under `/v1`, and its live OpenAPI document is available at `/openapi.json`.

Current Phase 0 endpoints cover:

- health and readiness;
- persistent job creation, listing, single-job polling, and retry;
- normalized message listing;
- Connector Manifest discovery through Core;
- source creation/listing and manual synchronization;
- source authentication status, challenge start, and challenge response forwarding.

The Flutter validation client now consumes these endpoints through typed presentation models. It discovers Connector Manifests through Core, renders a documented JSON Schema subset for ordinary configuration, keeps `x-campus-secret` fields out of that configuration, renders provider-neutral authentication challenges, and polls a manual sync through `GET /v1/jobs/{job_id}`. English protocol tokens are never localized; translated strings are a client-only concern.

Flutter must never call a Connector address directly. Before the cross-platform MVP is declared stable, the generated Core OpenAPI document will be checked into this directory as a versioned release snapshot and used to generate the Dart client package. Authentication, pagination, device registration, state synchronization, and production error envelopes are still under development, so the Client API is not yet declared stable.

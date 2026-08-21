# Campus AI Client API

The Client API is the only boundary used by Flutter clients. The current implementation is exposed by Core under `/v1`, and its live OpenAPI document is available at `/openapi.json`.

Current Phase 0 endpoints cover:

- health and readiness;
- persistent job creation, listing, single-job polling, retry, timing, and structured results;
- normalized message listing;
- Connector Manifest discovery through Core;
- source creation, listing, editing, enable/disable, soft archival, and restoration;
- per-source `manual` or timezone-aware `daily` collection schedules;
- non-collecting Connector/configuration checks and bounded asynchronous previews;
- manual synchronization and source-level job diagnostics;
- source authentication status, challenge start, and challenge response forwarding.

The Flutter validation client consumes these endpoints through typed presentation models. It discovers Connector Manifests through Core, renders a documented JSON Schema subset for ordinary configuration, keeps `x-campus-secret` fields out of that configuration, renders provider-neutral authentication challenges, and polls sync or preview work through `GET /v1/jobs/{job_id}`. English protocol tokens are never localized; translated strings are a client-only concern.

`DELETE /v1/sources/{source_id}` is deliberately a reversible soft archive. It disables scheduling, clears Core credential references, and preserves collected messages and analyses. `POST /v1/sources/{source_id}/restore` restores the configuration in a disabled state. A future permanent-data deletion API will require an explicit, higher-risk confirmation flow.

Flutter must never call a Connector address directly. Before the cross-platform MVP is declared stable, the generated Core OpenAPI document will be checked into this directory as a versioned release snapshot and used to generate the Dart client package. Authentication, pagination, device registration, state synchronization, and production error envelopes are still under development, so the Client API is not yet declared stable.

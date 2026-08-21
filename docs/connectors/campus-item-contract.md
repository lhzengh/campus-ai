# CampusItem Contract v1

`CampusItem` is the canonical fact record returned by every Connector. `CampusItemBatch` is the bounded, incremental transport unit received by Core. This contract is independent of any institution, website layout, programming language, or Core database schema.

## Responsibility boundary

A Connector extracts and normalizes source facts. Core owns source identity, database IDs, observation timestamps, content fingerprints, deduplication, AI analysis, notification decisions, and user state.

A Connector must never return passwords, verification codes, cookies, browser state, access tokens, credential-bearing URLs, or AI-generated importance decisions. Source-specific fields belong only in a Connector-ID-namespaced `extensions` object.

## Canonical batch

```json
{
  "contract_version": "1.0",
  "items": [
    {
      "external_id": "notice-20260821-001",
      "item_type": "announcement",
      "source_url": "https://campus.example/notices/001",
      "title": "Course selection notice",
      "content_text": "Students must confirm their selections before Friday.",
      "content_html": null,
      "publisher": {
        "name": "Academic Affairs Office",
        "external_id": null
      },
      "published_at": "2026-08-21T08:30:00+08:00",
      "updated_at": null,
      "attachments": [
        {
          "external_id": "attachment-001",
          "name": "Instructions.pdf",
          "media_type": "application/pdf",
          "size_bytes": 245760,
          "content_hash": null,
          "access": {
            "mode": "public_url",
            "url": "https://campus.example/files/instructions.pdf",
            "ref": null
          }
        }
      ],
      "extensions": {
        "org.example.portal": {
          "section": "academic",
          "original_label": "Undergraduate Notices"
        }
      }
    }
  ],
  "next_cursor": {
    "opaque_token": "connector-defined-value"
  },
  "has_more": false,
  "auth_state": "ready",
  "warnings": []
}
```

## Item fields

| Field | Required | Contract |
| --- | --- | --- |
| `external_id` | Yes | Stable within one source instance. It must survive content edits and must not be a list position. A normalized-URL hash is acceptable when the source has no ID. |
| `item_type` | Yes | One of `announcement`, `news`, `event`, `resource`, or `other`. Use only explicit source facts; do not infer importance or urgency. |
| `source_url` | Yes | Absolute HTTP(S) origin URL without embedded credentials. |
| `title` | Yes | Original source title, not an AI rewrite. |
| `content_text` | Yes | Clean plain text used as the primary analysis input. |
| `content_html` | No | Untrusted rich source content. Core must sanitize it before rendering. Plain text remains mandatory. |
| `publisher` | No | Publisher explicitly named by the source. It must not be guessed. |
| `published_at` | No | Source publication time as RFC 3339 with an explicit offset. Missing source time remains `null`. |
| `updated_at` | No | Source-provided update time, not the Connector fetch time. |
| `attachments` | Yes | Attachment facts and access references; an empty list is valid. |
| `extensions` | Yes | Optional source-specific JSON keyed by a stable Connector ID; an empty object is valid. |

Core adds `id`, `source_id`, `connector_id`, `connector_version`, `fetched_at`, `content_hash`, analysis results, and notification state after accepting an Item. Those values never cross from a Connector as source facts.

## Attachment access

`public_url` means Core may retrieve the attachment directly. `connector_fetch` means the source requires Connector-owned authentication; `ref` is opaque and can later be supplied to the versioned attachment-fetch operation. Core must never receive the source session itself.

```json
{"mode": "public_url", "url": "https://campus.example/file.pdf", "ref": null}
```

```json
{"mode": "connector_fetch", "url": null, "ref": "opaque-attachment-reference"}
```

The v1 synchronization contract records both forms. Downloading `connector_fetch` content is a separate capability and may be unavailable in an early Connector implementation.

## Batch, cursor, and update semantics

- A batch never exceeds the `max_items` requested by Core.
- `next_cursor` is opaque Connector-owned JSON. Core stores it only after every Item in the batch is committed successfully.
- `has_more: true` requires a usable next cursor and schedules another bounded request.
- Warnings describe partial, non-fatal problems with structured codes. A failed operation uses the standard Connector error response instead.
- Core uses `(source_id, external_id)` as the idempotency key.
- An unchanged standard content fingerprint is not analyzed twice. Changed content under the same ID is an update.
- A Connector must emit records in a deterministic order so retries and pagination cannot silently skip records.

Deletion and historical version transport are intentionally not represented as fake Items in v1. Core retains accepted revisions; a future contract revision can add explicit tombstones without overloading the meaning of an Item.

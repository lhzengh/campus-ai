"""Call out-of-process Connectors through the versioned protocol boundary."""

from __future__ import annotations

from functools import cached_property
from urllib.parse import urlsplit

import httpx

from campus_connector_sdk import (
    CONTRACT_VERSION,
    AuthResult,
    AuthStatusRequest,
    BeginAuthRequest,
    CampusItemBatch,
    ConfigValidationRequest,
    ConfigValidationResult,
    ConnectorErrorCode,
    ConnectorManifest,
    SubmitAuthRequest,
    SyncRequest,
)


class ConnectorClientError(RuntimeError):
    """Typed remote failure used by Core retry and authentication policies."""

    def __init__(
        self,
        code: ConnectorErrorCode,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.status_code = status_code


def validate_connector_endpoint(value: str) -> str:
    """Reject ambiguous or credential-bearing service addresses before use."""

    endpoint = value.rstrip("/")
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Connector endpoint must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Connector endpoint must not embed credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("Connector endpoint must not contain a query or fragment")
    return endpoint


def _major(version: str) -> str:
    """Extract the compatibility-significant major version component."""

    return version.split(".", maxsplit=1)[0]


class ConnectorClient:
    """Validate Connector identity and normalize remote protocol failures."""

    def __init__(
        self,
        *,
        expected_connector_id: str,
        base_url: str,
        shared_token: str = "",
        expected_version: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.expected_connector_id = expected_connector_id
        self.expected_version = expected_version
        self.base_url = validate_connector_endpoint(base_url)
        self.headers = {"Authorization": f"Bearer {shared_token}"} if shared_token else {}
        self.client = client or httpx.Client(timeout=httpx.Timeout(30))

    def _request(self, method: str, path: str, *, payload: dict[str, object] | None = None) -> dict[str, object]:
        """Perform one authenticated request and require an object response."""

        try:
            response = self.client.request(
                method,
                f"{self.base_url}{path}",
                json=payload,
                headers=self.headers,
            )
        except httpx.RequestError as exc:
            raise ConnectorClientError(
                ConnectorErrorCode.TEMPORARY_FAILURE,
                f"Connector {self.expected_connector_id} is unavailable",
                retryable=True,
            ) from exc
        if response.is_error:
            try:
                body = response.json()
            except ValueError:
                body = {}
            try:
                code = ConnectorErrorCode(body.get("code", ConnectorErrorCode.TEMPORARY_FAILURE))
            except ValueError:
                code = ConnectorErrorCode.TEMPORARY_FAILURE
            raise ConnectorClientError(
                code,
                str(body.get("message") or f"Connector returned HTTP {response.status_code}"),
                retryable=bool(body.get("retryable", response.status_code >= 500)),
                status_code=response.status_code,
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                "Connector returned a non-JSON response",
            ) from exc
        if not isinstance(body, dict):
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                "Connector response must be a JSON object",
            )
        return body

    @cached_property
    def manifest(self) -> ConnectorManifest:
        """Load and pin the remote Connector identity for later operations."""

        # Cache identity per client so every operation uses the same verified peer.
        try:
            manifest = ConnectorManifest.model_validate(self._request("GET", "/v1/manifest"))
        except ValueError as exc:
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                "Connector Manifest does not match the protocol schema",
            ) from exc
        if manifest.connector_id != self.expected_connector_id:
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                f"Registered Connector ID {self.expected_connector_id!r} does not match Manifest ID {manifest.connector_id!r}",
            )
        if _major(manifest.contract_version) != _major(CONTRACT_VERSION):
            # Minor protocol additions remain compatible; major changes do not.
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                f"Connector contract {manifest.contract_version} is incompatible with Core contract {CONTRACT_VERSION}",
            )
        if self.expected_version and manifest.version != self.expected_version:
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                f"Connector version {manifest.version} does not match pinned version {self.expected_version}",
            )
        return manifest

    def validate_config(self, config: dict[str, object]) -> dict[str, object]:
        """Ask the owning Connector to validate and normalize public config."""

        _ = self.manifest
        result = ConfigValidationResult.model_validate(
            self._request(
                "POST",
                "/v1/config/validate",
                payload=ConfigValidationRequest(config=config).model_dump(mode="json"),
            )
        )
        if not result.valid:
            raise ConnectorClientError(
                ConnectorErrorCode.CONFIG_INVALID,
                "; ".join(result.errors.values()) or "Connector rejected the configuration",
            )
        return result.normalized_config

    def auth_status(self, instance_id: str, config: dict[str, object]) -> AuthResult:
        """Read authentication state without beginning user interaction."""

        _ = self.manifest
        payload = AuthStatusRequest(instance_id=instance_id, config=config)
        return AuthResult.model_validate(self._request("POST", "/v1/auth/status", payload=payload.model_dump(mode="json")))

    def begin_auth(self, instance_id: str, config: dict[str, object]) -> AuthResult:
        """Request the next Connector-defined authentication challenge."""

        _ = self.manifest
        payload = BeginAuthRequest(instance_id=instance_id, config=config)
        return AuthResult.model_validate(self._request("POST", "/v1/auth/begin", payload=payload.model_dump(mode="json")))

    def submit_auth_response(
        self,
        instance_id: str,
        config: dict[str, object],
        challenge_id: str,
        response: dict[str, str],
    ) -> AuthResult:
        """Submit ephemeral challenge input directly to the Connector."""

        _ = self.manifest
        payload = SubmitAuthRequest(
            instance_id=instance_id,
            config=config,
            challenge_id=challenge_id,
            response=response,
        )
        return AuthResult.model_validate(
            self._request("POST", "/v1/auth/respond", payload=payload.model_dump(mode="json"))
        )

    def sync(self, request: SyncRequest) -> CampusItemBatch:
        """Fetch one bounded batch and enforce the complete wire contract."""

        _ = self.manifest
        body = self._request("POST", "/v1/sync", payload=request.model_dump(mode="json"))
        # Unlike SDK-side defaults, the process boundary must be self-describing.
        required_batch_fields = {
            "contract_version",
            "items",
            "next_cursor",
            "has_more",
            "auth_state",
            "warnings",
        }
        if not required_batch_fields.issubset(body):
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                "Connector batch is missing required CampusItemBatch v1 fields",
            )
        if body.get("contract_version") != CONTRACT_VERSION:
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                f"Connector batch contract {body.get('contract_version')!r} does not match {CONTRACT_VERSION}",
            )
        required_item_fields = {
            "external_id",
            "item_type",
            "source_url",
            "title",
            "content_text",
            "attachments",
            "extensions",
        }
        raw_items = body.get("items")
        if not isinstance(raw_items, list) or any(
            not isinstance(item, dict) or not required_item_fields.issubset(item)
            for item in raw_items
        ):
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                "Connector batch contains an incomplete CampusItem v1 record",
            )
        try:
            batch = CampusItemBatch.model_validate(body)
        except ValueError as exc:
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                "Connector sync response does not match CampusItemBatch v1",
            ) from exc
        if len(batch.items) > request.max_items:
            raise ConnectorClientError(
                ConnectorErrorCode.PROTOCOL_MISMATCH,
                "Connector returned more items than Core requested",
            )
        return batch

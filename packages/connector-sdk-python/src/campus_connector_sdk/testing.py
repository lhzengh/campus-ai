"""Reusable contract checks for independently developed Connectors."""

from __future__ import annotations

from campus_connector_sdk.base import CampusConnector
from campus_connector_sdk.models import CONTRACT_VERSION, CampusItemBatch, ConnectorCapability, SyncRequest


def _require(condition: bool, message: str) -> None:
    """Raise a stable conformance failure even when Python optimization is enabled."""

    if not condition:
        raise AssertionError(message)


def assert_connector_conformance(
    connector: CampusConnector,
    *,
    valid_config: dict[str, object],
    exercise_sync: bool = True,
) -> None:
    """Run implementation-independent checks usable by any Connector repository."""

    manifest = connector.manifest
    # These checks intentionally use only the public SDK surface so third-party
    # repositories can run the same suite without installing Campus AI Core.
    _require(
        manifest.contract_version == CONTRACT_VERSION,
        "Connector contract version does not match the SDK",
    )
    _require(ConnectorCapability.SYNC in manifest.capabilities, "Connector must advertise sync capability")
    _require(manifest.config_schema.get("type") == "object", "Connector configuration must be an object")

    normalized = connector.validate_config(valid_config)
    _require(isinstance(normalized, dict), "Connector validation must return a dictionary")

    if exercise_sync:
        batch = connector.sync(
            SyncRequest(instance_id="conformance-instance", config=normalized, cursor={}, max_items=10)
        )
        _require(isinstance(batch, CampusItemBatch), "Connector sync must return CampusItemBatch")
        CampusItemBatch.model_validate(batch.model_dump(mode="json"))

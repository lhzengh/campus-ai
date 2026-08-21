from __future__ import annotations

from campus_connector_sdk.base import CampusConnector
from campus_connector_sdk.models import CONTRACT_VERSION, CampusItemBatch, ConnectorCapability, SyncRequest


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
    assert manifest.contract_version == CONTRACT_VERSION
    assert ConnectorCapability.SYNC in manifest.capabilities
    assert manifest.config_schema.get("type") == "object"

    normalized = connector.validate_config(valid_config)
    assert isinstance(normalized, dict)

    if exercise_sync:
        batch = connector.sync(
            SyncRequest(instance_id="conformance-instance", config=normalized, cursor={}, max_items=10)
        )
        assert isinstance(batch, CampusItemBatch)
        CampusItemBatch.model_validate(batch.model_dump(mode="json"))

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from selectolax.parser import HTMLParser

from campus_connector_sdk import (
    AuthChallenge,
    AuthChallengeField,
    AuthChallengeKind,
    AuthResult,
    AuthState,
    CampusConnector,
    CampusItem,
    CampusItemBatch,
    ConnectorCapability,
    ConnectorErrorCode,
    ConnectorManifest,
    ConnectorProtocolError,
    SyncRequest,
)
from campus_ai_connector_generic_browser.session import EncryptedBrowserSession


CONFIG_SCHEMA: dict[str, Any] = {
    # No account, password, OTP, cookie, or institution URL belongs in this schema.
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "page_url",
        "login_url",
        "success_url_pattern",
        "allowed_hosts",
        "title_selector",
        "body_selector",
    ],
    "properties": {
        "page_url": {"type": "string", "format": "uri"},
        "login_url": {"type": "string", "format": "uri"},
        "success_url_pattern": {"type": "string", "minLength": 1},
        "allowed_hosts": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "title_selector": {"type": "string", "minLength": 1},
        "body_selector": {"type": "string", "minLength": 1},
        "published_selector": {"type": ["string", "null"]},
        "published_format": {"type": ["string", "null"]},
        "timezone_name": {"type": "string", "default": "Asia/Shanghai"},
    },
}


def _validated_url(value: object, *, field: str) -> str:
    url = str(value or "")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, f"{field} must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, f"{field} must not contain credentials")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ""))


class GenericBrowserConnector(CampusConnector):
    """Validation Connector for one authenticated, browser-rendered page."""

    def __init__(self, *, session_directory: Path, secret_key: str) -> None:
        self.session_directory = session_directory
        self.secret_key = secret_key
        self._challenges: dict[str, str] = {}

    @property
    def manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_id="campus-ai.generic-browser",
            version="0.1.0",
            display_name="Generic Authenticated Browser",
            description="Loads one authenticated page with encrypted Connector-owned Playwright state.",
            capabilities={
                ConnectorCapability.SYNC,
                ConnectorCapability.INCREMENTAL_SYNC,
                ConnectorCapability.USER_ASSISTED_AUTH,
                ConnectorCapability.BROWSER,
            },
            config_schema=CONFIG_SCHEMA,
            requires_browser=True,
        )

    def _session(self) -> EncryptedBrowserSession:
        try:
            return EncryptedBrowserSession(self.session_directory, self.secret_key)
        except (ValueError, TypeError) as exc:
            raise ConnectorProtocolError(
                ConnectorErrorCode.CONFIG_INVALID,
                "The browser Connector session key is missing or invalid",
            ) from exc

    def validate_config(self, config: dict[str, object]) -> dict[str, object]:
        normalized = dict(config)
        normalized["page_url"] = _validated_url(config.get("page_url"), field="page_url")
        normalized["login_url"] = _validated_url(config.get("login_url"), field="login_url")
        for field in ("success_url_pattern", "title_selector", "body_selector"):
            value = config.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, f"{field} is required")
            normalized[field] = value.strip()

        raw_hosts = config.get("allowed_hosts")
        if not isinstance(raw_hosts, list) or not raw_hosts or not all(isinstance(item, str) for item in raw_hosts):
            raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, "allowed_hosts must be a non-empty string list")
        allowed_hosts = sorted({item.strip().lower().rstrip(".") for item in raw_hosts if item.strip()})
        required_hosts = {
            (urlsplit(str(normalized["page_url"])).hostname or "").lower().rstrip("."),
            (urlsplit(str(normalized["login_url"])).hostname or "").lower().rstrip("."),
        }
        if not required_hosts.issubset(set(allowed_hosts)):
            raise ConnectorProtocolError(
                ConnectorErrorCode.CONFIG_INVALID,
                "page_url and login_url hosts must be included in allowed_hosts",
            )
        normalized["allowed_hosts"] = allowed_hosts

        timezone_name = str(config.get("timezone_name") or "Asia/Shanghai")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, "timezone_name is unknown") from exc
        normalized["timezone_name"] = timezone_name
        normalized["published_selector"] = config.get("published_selector") or None
        normalized["published_format"] = config.get("published_format") or None
        return normalized

    def auth_status(self, instance_id: str, config: dict[str, object]) -> AuthResult:
        self.validate_config(config)
        state = AuthState.READY if self._session().has_state(instance_id) else AuthState.AUTH_REQUIRED
        return AuthResult(state=state)

    def begin_auth(self, instance_id: str, config: dict[str, object]) -> AuthResult:
        normalized = self.validate_config(config)
        challenge_id = str(uuid.uuid4())
        # The challenge carries instructions only; credentials never transit config.
        self._challenges[instance_id] = challenge_id
        return AuthResult(
            state=AuthState.WAITING_FOR_USER,
            challenge=AuthChallenge(
                challenge_id=challenge_id,
                kind=AuthChallengeKind.BROWSER_INTERACTION,
                title="Complete portal sign-in",
                instructions=(
                    "Run the Connector's campus-browser-login command on a trusted desktop session, "
                    "complete all password, SMS, QR, or CAPTCHA steps yourself, then confirm here."
                ),
                fields=[
                    AuthChallengeField(
                        name="confirmed",
                        label="I completed sign-in",
                        input_type="boolean",
                    )
                ],
                metadata={"login_url": normalized["login_url"]},
            ),
        )

    def submit_auth_response(
        self,
        instance_id: str,
        config: dict[str, object],
        challenge_id: str,
        response: dict[str, str],
    ) -> AuthResult:
        self.validate_config(config)
        if self._challenges.get(instance_id) != challenge_id:
            raise ConnectorProtocolError(ConnectorErrorCode.AUTH_REQUIRED, "Authentication challenge is not active")
        if response.get("confirmed", "").lower() not in {"1", "true", "yes"}:
            return AuthResult(state=AuthState.WAITING_FOR_USER, message="Complete sign-in before confirming")
        if not self._session().has_state(instance_id):
            return AuthResult(
                state=AuthState.WAITING_FOR_USER,
                message="No encrypted browser session has been captured yet",
            )
        self._challenges.pop(instance_id, None)
        return AuthResult(state=AuthState.READY)

    def sync(self, request: SyncRequest) -> CampusItemBatch:
        config = self.validate_config(request.config)
        url = str(config["page_url"])
        raw = self._session().open_authenticated_page(
            request.instance_id,
            url,
            allowed_hosts=set(config["allowed_hosts"]),
        )
        tree = HTMLParser(raw)
        title_node = tree.css_first(str(config["title_selector"]))
        body_node = tree.css_first(str(config["body_selector"]))
        if title_node is None or body_node is None:
            raise ConnectorProtocolError(
                ConnectorErrorCode.SOURCE_CHANGED,
                "Required title or body selector did not match",
            )

        published_at = None
        if config.get("published_selector"):
            published_node = tree.css_first(str(config["published_selector"]))
            if published_node is not None:
                value = published_node.text(strip=True)
                try:
                    published_at = (
                        datetime.strptime(value, str(config["published_format"]))
                        if config.get("published_format")
                        else datetime.fromisoformat(value)
                    )
                except ValueError as exc:
                    raise ConnectorProtocolError(
                        ConnectorErrorCode.SOURCE_CHANGED,
                        "The publication time no longer matches the configured format",
                    ) from exc
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=ZoneInfo(str(config["timezone_name"])))

        message = CampusItem(
            external_id=hashlib.sha256(url.encode("utf-8")).hexdigest(),
            source_url=url,
            title=title_node.text(separator=" ", strip=True),
            content_text=body_node.text(separator="\n", strip=True),
            published_at=published_at,
        )
        # A changed hash re-emits the stable external ID so Core records an update.
        content_hash = hashlib.sha256(
            f"{message.title.strip()}\n{message.content_text.strip()}".encode("utf-8")
        ).hexdigest()
        if request.cursor.get("content_hash") == content_hash:
            items: list[CampusItem] = []
        else:
            items = [message]
        return CampusItemBatch(
            items=items,
            next_cursor={"content_hash": content_hash},
            auth_state=AuthState.READY,
        )

from __future__ import annotations

import hashlib
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from selectolax.parser import HTMLParser

from campus_connector_sdk import (
    CampusConnector,
    ConnectorCapability,
    ConnectorErrorCode,
    ConnectorManifest,
    ConnectorMessage,
    ConnectorProtocolError,
    SyncBatch,
    SyncRequest,
)


CONFIG_SCHEMA: dict[str, Any] = {
    # Core forwards this schema to Client instead of knowing source-specific fields.
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "index_url",
        "allowed_hosts",
        "item_link_selector",
        "title_selector",
        "body_selector",
    ],
    "properties": {
        "index_url": {"type": "string", "format": "uri", "title": "Announcement index URL"},
        "allowed_hosts": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
            "title": "Allowed host names",
        },
        "item_link_selector": {"type": "string", "minLength": 1},
        "title_selector": {"type": "string", "minLength": 1},
        "body_selector": {"type": "string", "minLength": 1},
        "published_selector": {"type": ["string", "null"]},
        "published_format": {"type": ["string", "null"]},
        "timezone_name": {"type": "string", "default": "Asia/Shanghai"},
        "request_interval_seconds": {"type": "number", "minimum": 0, "default": 0.5},
    },
}


def canonicalize_url(url: str) -> str:
    """Remove fragments and normalize host casing for stable source identity."""

    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))


def _validated_url(value: object, *, field: str) -> str:
    url = str(value or "")
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, f"{field} must be an absolute HTTP(S) URL")
    if parts.username is not None or parts.password is not None:
        raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, f"{field} must not contain credentials")
    return canonicalize_url(url)


class GenericStaticConnector(CampusConnector):
    """Runtime-configured HTTP collector with no dependency on Campus AI Core."""

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            follow_redirects=False,
            timeout=httpx.Timeout(20),
            headers={"User-Agent": "CampusAI-GenericStaticConnector/0.1"},
        )
        self._last_request_at = 0.0

    @property
    def manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_id="campus-ai.generic-static",
            version="0.1.0",
            display_name="Generic Static Website",
            description="Collects announcement pages using runtime CSS selectors and a strict host allowlist.",
            capabilities={ConnectorCapability.SYNC, ConnectorCapability.INCREMENTAL_SYNC},
            config_schema=CONFIG_SCHEMA,
        )

    def validate_config(self, config: dict[str, object]) -> dict[str, object]:
        required_strings = ("item_link_selector", "title_selector", "body_selector")
        normalized = dict(config)
        normalized["index_url"] = _validated_url(config.get("index_url"), field="index_url")

        for field in required_strings:
            value = config.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, f"{field} is required")
            normalized[field] = value.strip()

        raw_hosts = config.get("allowed_hosts")
        if not isinstance(raw_hosts, list) or not raw_hosts or not all(isinstance(item, str) for item in raw_hosts):
            raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, "allowed_hosts must be a non-empty string list")
        allowed_hosts = sorted({item.strip().lower().rstrip(".") for item in raw_hosts if item.strip()})
        index_host = (urlsplit(str(normalized["index_url"])).hostname or "").lower().rstrip(".")
        if index_host not in allowed_hosts:
            raise ConnectorProtocolError(
                ConnectorErrorCode.CONFIG_INVALID,
                "The index_url host must be included in allowed_hosts",
            )
        normalized["allowed_hosts"] = allowed_hosts

        timezone_name = str(config.get("timezone_name") or "Asia/Shanghai")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ConnectorProtocolError(ConnectorErrorCode.CONFIG_INVALID, "timezone_name is unknown") from exc
        normalized["timezone_name"] = timezone_name

        try:
            interval = float(config.get("request_interval_seconds", 0.5))
        except (TypeError, ValueError) as exc:
            raise ConnectorProtocolError(
                ConnectorErrorCode.CONFIG_INVALID,
                "request_interval_seconds must be a number",
            ) from exc
        if interval < 0:
            raise ConnectorProtocolError(
                ConnectorErrorCode.CONFIG_INVALID,
                "request_interval_seconds must not be negative",
            )
        normalized["request_interval_seconds"] = interval
        normalized["published_selector"] = config.get("published_selector") or None
        normalized["published_format"] = config.get("published_format") or None
        return normalized

    def _get(self, url: str, *, allowed_hosts: set[str], interval: float) -> httpx.Response:
        normalized_url = _validated_url(url, field="requested URL")
        host = (urlsplit(normalized_url).hostname or "").lower().rstrip(".")
        # Validate every discovered URL, not only the configured index URL.
        if host not in allowed_hosts:
            raise ConnectorProtocolError(
                ConnectorErrorCode.ACCESS_DENIED,
                f"Refusing a URL outside allowed_hosts: {host}",
            )
        remaining = interval - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)
        try:
            current_url = normalized_url
            for _ in range(6):
                response = self.client.get(current_url)
                self._last_request_at = time.monotonic()
                if not response.is_redirect:
                    response.raise_for_status()
                    return response
                location = response.headers.get("location")
                if not location:
                    raise ConnectorProtocolError(
                        ConnectorErrorCode.TEMPORARY_FAILURE,
                        "Source returned a redirect without a location",
                        retryable=True,
                    )
                # Redirect targets pass through the same allowlist before a request is sent.
                current_url = _validated_url(urljoin(current_url, location), field="redirect URL")
                redirect_host = (urlsplit(current_url).hostname or "").lower().rstrip(".")
                if redirect_host not in allowed_hosts:
                    raise ConnectorProtocolError(
                        ConnectorErrorCode.ACCESS_DENIED,
                        f"Refusing a redirect outside allowed_hosts: {redirect_host}",
                    )
            raise ConnectorProtocolError(
                ConnectorErrorCode.TEMPORARY_FAILURE,
                "Source exceeded the redirect limit",
                retryable=True,
            )
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in {401, 403}:
                code = ConnectorErrorCode.ACCESS_DENIED
                retryable = False
            elif status_code == 429:
                code = ConnectorErrorCode.RATE_LIMITED
                retryable = True
            else:
                code = ConnectorErrorCode.TEMPORARY_FAILURE
                retryable = status_code >= 500
            raise ConnectorProtocolError(code, f"Source returned HTTP {status_code}", retryable=retryable) from exc
        except httpx.RequestError as exc:
            raise ConnectorProtocolError(
                ConnectorErrorCode.TEMPORARY_FAILURE,
                "Source request failed",
                retryable=True,
            ) from exc

    def _normalize(self, url: str, raw: str, config: dict[str, object]) -> ConnectorMessage:
        tree = HTMLParser(raw)
        title_node = tree.css_first(str(config["title_selector"]))
        body_node = tree.css_first(str(config["body_selector"]))
        if title_node is None or body_node is None:
            raise ConnectorProtocolError(
                ConnectorErrorCode.SOURCE_CHANGED,
                "Required title or body selector did not match",
            )

        published_at = None
        published_selector = config.get("published_selector")
        if published_selector:
            published_node = tree.css_first(str(published_selector))
            if published_node is not None:
                value = published_node.text(strip=True)
                try:
                    published_format = config.get("published_format")
                    published_at = (
                        datetime.strptime(value, str(published_format))
                        if published_format
                        else datetime.fromisoformat(value)
                    )
                except ValueError as exc:
                    raise ConnectorProtocolError(
                        ConnectorErrorCode.SOURCE_CHANGED,
                        "The publication time no longer matches the configured format",
                    ) from exc
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=ZoneInfo(str(config["timezone_name"])))

        external_id = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return ConnectorMessage(
            external_id=external_id,
            url=url,
            title=title_node.text(separator=" ", strip=True),
            body=body_node.text(separator="\n", strip=True),
            published_at=published_at,
        )

    def sync(self, request: SyncRequest) -> SyncBatch:
        config = self.validate_config(request.config)
        index_url = str(config["index_url"])
        allowed_hosts = set(config["allowed_hosts"])
        interval = float(config["request_interval_seconds"])
        index = self._get(index_url, allowed_hosts=allowed_hosts, interval=interval)
        tree = HTMLParser(index.text)

        discovered: dict[str, str] = {}
        for node in tree.css(str(config["item_link_selector"])):
            href = node.attributes.get("href")
            if not href:
                continue
            url = canonicalize_url(urljoin(index_url, href))
            host = (urlsplit(url).hostname or "").lower().rstrip(".")
            if host in allowed_hosts:
                discovered[url] = hashlib.sha256(url.encode("utf-8")).hexdigest()

        # Content hashes detect edits while keeping the cursor opaque to Core.
        previous_hashes = request.cursor.get("content_hashes", {})
        if not isinstance(previous_hashes, dict):
            previous_hashes = {}
        next_hashes = {str(key): str(value) for key, value in previous_hashes.items()}
        items: list[ConnectorMessage] = []
        remaining = False

        for url, external_id in discovered.items():
            raw = self._get(url, allowed_hosts=allowed_hosts, interval=interval).text
            message = self._normalize(url, raw, config)
            content_hash = hashlib.sha256(
                f"{message.title.strip()}\n{message.body.strip()}".encode("utf-8")
            ).hexdigest()
            if next_hashes.get(external_id) == content_hash:
                continue
            if len(items) >= request.max_items:
                remaining = True
                continue
            items.append(message)
            next_hashes[external_id] = content_hash

        # Bound cursor growth for long-lived sources.
        if len(next_hashes) > 2000:
            next_hashes = dict(list(next_hashes.items())[-2000:])
        return SyncBatch(items=items, next_cursor={"content_hashes": next_hashes}, has_more=remaining)

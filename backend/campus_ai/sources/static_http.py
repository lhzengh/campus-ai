from __future__ import annotations

import hashlib
import time
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import httpx
from selectolax.parser import HTMLParser

from campus_ai.sources.base import DiscoveredItem, NormalizedMessage, SourceAdapter


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))


class StaticHttpSourceAdapter(SourceAdapter):
    def __init__(
        self,
        *,
        index_url: str,
        item_link_selector: str,
        title_selector: str,
        body_selector: str,
        published_selector: str | None = None,
        published_format: str | None = None,
        timezone_name: str = "Asia/Shanghai",
        request_interval_seconds: float = 0.5,
        client: httpx.Client | None = None,
    ) -> None:
        self.index_url = index_url
        self.item_link_selector = item_link_selector
        self.title_selector = title_selector
        self.body_selector = body_selector
        self.published_selector = published_selector
        self.published_format = published_format
        self.timezone = ZoneInfo(timezone_name)
        self.request_interval_seconds = max(0, request_interval_seconds)
        self._last_request_at = 0.0
        self.client = client or httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(20),
            headers={"User-Agent": "CampusAI-Validation/0.1 (+personal information assistant)"},
        )

    def _get(self, url: str) -> httpx.Response:
        remaining = self.request_interval_seconds - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)
        response = self.client.get(url)
        self._last_request_at = time.monotonic()
        return response

    def health_check(self) -> None:
        response = self._get(self.index_url)
        response.raise_for_status()

    def discover(self) -> list[DiscoveredItem]:
        response = self._get(self.index_url)
        response.raise_for_status()
        tree = HTMLParser(response.text)
        discovered: dict[str, DiscoveredItem] = {}
        for node in tree.css(self.item_link_selector):
            href = node.attributes.get("href")
            if not href:
                continue
            url = canonicalize_url(urljoin(self.index_url, href))
            external_id = hashlib.sha256(url.encode("utf-8")).hexdigest()
            discovered[url] = DiscoveredItem(external_id=external_id, url=url)
        return list(discovered.values())

    def fetch(self, item: DiscoveredItem) -> str:
        response = self._get(item.url)
        response.raise_for_status()
        return response.text

    def normalize(self, item: DiscoveredItem, raw: str) -> NormalizedMessage:
        tree = HTMLParser(raw)
        title_node = tree.css_first(self.title_selector)
        body_node = tree.css_first(self.body_selector)
        if title_node is None or body_node is None:
            raise ValueError(f"Required selectors did not match for {item.url}")

        published_at = None
        if self.published_selector:
            published_node = tree.css_first(self.published_selector)
            if published_node is not None:
                value = published_node.text(strip=True)
                published_at = (
                    datetime.strptime(value, self.published_format)
                    if self.published_format
                    else datetime.fromisoformat(value)
                )
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=self.timezone)

        return NormalizedMessage(
            external_id=item.external_id,
            url=item.url,
            title=title_node.text(separator=" ", strip=True),
            body=body_node.text(separator="\n", strip=True),
            published_at=published_at,
        )

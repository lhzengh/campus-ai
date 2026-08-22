"""Encrypted Playwright storage-state lifecycle owned by the Connector."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken
from playwright.sync_api import BrowserContext, Page, Route, sync_playwright

from campus_connector_sdk import ConnectorErrorCode, ConnectorProtocolError


class EncryptedBrowserSession:
    """Connector-owned Playwright state; Core never sees cookies or storage state."""

    def __init__(self, session_directory: Path, secret_key: str) -> None:
        if not secret_key:
            raise ValueError("CAMPUS_CONNECTOR_SESSION_KEY is required")
        self.session_directory = session_directory
        self.cipher = Fernet(secret_key.encode("ascii"))

    def state_path(self, instance_id: str) -> Path:
        """Derive a safe opaque file name for one source instance."""

        # Hash untrusted IDs so they can never select an arbitrary filesystem path.
        digest = hashlib.sha256(instance_id.encode("utf-8")).hexdigest()
        return self.session_directory / f"{digest}.enc"

    def has_state(self, instance_id: str) -> bool:
        """Return whether an encrypted session has been captured."""

        return self.state_path(instance_id).is_file()

    def _decrypt_state(self, instance_id: str, temporary_path: Path) -> bool:
        encrypted_path = self.state_path(instance_id)
        if not encrypted_path.exists():
            return False
        try:
            plaintext = self.cipher.decrypt(encrypted_path.read_bytes())
        except InvalidToken as exc:
            raise ConnectorProtocolError(
                ConnectorErrorCode.AUTH_REQUIRED,
                "Stored browser session could not be decrypted; authenticate again",
            ) from exc
        # Playwright requires a file, so plaintext exists only in a mode-0600 temp file.
        temporary_path.write_bytes(plaintext)
        os.chmod(temporary_path, 0o600)
        return True

    def _encrypt_state(self, instance_id: str, temporary_path: Path) -> None:
        encrypted_path = self.state_path(instance_id)
        encrypted_path.parent.mkdir(parents=True, exist_ok=True)
        encrypted_path.write_bytes(self.cipher.encrypt(temporary_path.read_bytes()))
        os.chmod(encrypted_path, 0o600)

    @staticmethod
    def _route_policy(allowed_hosts: set[str]) -> Callable[[Route], None]:
        """Block browser subrequests that escape the configured source boundary."""

        def route_request(route: Route) -> None:
            """Apply the allowlist to each browser subrequest."""

            parsed = urlsplit(route.request.url)
            host = (parsed.hostname or "").lower().rstrip(".")
            if parsed.scheme in {"data", "blob"} or host in allowed_hosts:
                route.continue_()
            else:
                route.abort("blockedbyclient")

        return route_request

    def open_authenticated_page(self, instance_id: str, url: str, *, allowed_hosts: set[str]) -> str:
        """Render an allowlisted page and persist refreshed encrypted state."""

        temporary = tempfile.NamedTemporaryFile(prefix="campus-connector-session-", suffix=".json", delete=False)
        temporary_path = Path(temporary.name)
        temporary.close()
        try:
            if not self._decrypt_state(instance_id, temporary_path):
                raise ConnectorProtocolError(ConnectorErrorCode.AUTH_REQUIRED, "Browser authentication is required")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context: BrowserContext = browser.new_context(storage_state=str(temporary_path))
                context.route("**/*", self._route_policy(allowed_hosts))
                page: Page = context.new_page()
                response = page.goto(url, wait_until="networkidle")
                if response is None:
                    raise ConnectorProtocolError(
                        ConnectorErrorCode.TEMPORARY_FAILURE,
                        "Portal navigation returned no response",
                        retryable=True,
                    )
                final_host = (urlsplit(page.url).hostname or "").lower().rstrip(".")
                if final_host not in allowed_hosts:
                    raise ConnectorProtocolError(ConnectorErrorCode.ACCESS_DENIED, "Portal redirected outside allowed_hosts")
                if response.status in {401, 403}:
                    raise ConnectorProtocolError(ConnectorErrorCode.AUTH_REQUIRED, "Portal session has expired")
                content = page.content()
                context.storage_state(path=str(temporary_path))
                self._encrypt_state(instance_id, temporary_path)
                browser.close()
                return content
        finally:
            temporary_path.unlink(missing_ok=True)

    def capture_user_login(
        self,
        instance_id: str,
        login_url: str,
        *,
        success_url_pattern: str,
        allowed_hosts: set[str],
        timeout_ms: int = 180_000,
    ) -> None:
        """Let the operator solve every interactive challenge in a visible browser."""

        temporary = tempfile.NamedTemporaryFile(prefix="campus-connector-login-", suffix=".json", delete=False)
        temporary_path = Path(temporary.name)
        temporary.close()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=False)
                context = browser.new_context()
                context.route("**/*", self._route_policy(allowed_hosts))
                page = context.new_page()
                page.goto(login_url)
                page.wait_for_url(success_url_pattern, timeout=timeout_ms)
                final_host = (urlsplit(page.url).hostname or "").lower().rstrip(".")
                if final_host not in allowed_hosts:
                    raise ConnectorProtocolError(ConnectorErrorCode.ACCESS_DENIED, "Login redirected outside allowed_hosts")
                context.storage_state(path=str(temporary_path))
                self._encrypt_state(instance_id, temporary_path)
                browser.close()
        finally:
            temporary_path.unlink(missing_ok=True)

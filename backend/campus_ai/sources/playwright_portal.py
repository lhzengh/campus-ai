from __future__ import annotations

import os
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from playwright.sync_api import BrowserContext, Page, sync_playwright


class PortalBrowserSession:
    """Small validation wrapper for user-assisted portal authentication.

    It deliberately does not attempt to solve or bypass CAPTCHA challenges.
    """

    def __init__(self, encrypted_state_path: Path, secret_key: str) -> None:
        if not secret_key:
            raise ValueError("A Fernet secret key is required for portal session storage")
        self.encrypted_state_path = encrypted_state_path
        self.cipher = Fernet(secret_key.encode("ascii"))

    def _decrypt_state(self, temporary_path: Path) -> bool:
        if not self.encrypted_state_path.exists():
            return False
        try:
            plaintext = self.cipher.decrypt(self.encrypted_state_path.read_bytes())
        except InvalidToken as exc:
            raise ValueError("Portal session state could not be decrypted") from exc
        temporary_path.write_bytes(plaintext)
        os.chmod(temporary_path, 0o600)
        return True

    def _encrypt_state(self, temporary_path: Path) -> None:
        self.encrypted_state_path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = self.cipher.encrypt(temporary_path.read_bytes())
        self.encrypted_state_path.write_bytes(encrypted)
        os.chmod(self.encrypted_state_path, 0o600)

    def open_authenticated_page(self, url: str, *, headless: bool = True) -> str:
        temporary = tempfile.NamedTemporaryFile(prefix="campus-ai-session-", suffix=".json", delete=False)
        temporary_path = Path(temporary.name)
        temporary.close()
        try:
            has_state = self._decrypt_state(temporary_path)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=headless)
                context_args: dict[str, str] = {}
                if has_state:
                    context_args["storage_state"] = str(temporary_path)
                context: BrowserContext = browser.new_context(**context_args)
                page: Page = context.new_page()
                response = page.goto(url, wait_until="networkidle")
                if response is None:
                    raise RuntimeError(f"Portal navigation returned no response: {url}")
                if response.status in {401, 403}:
                    raise PermissionError(f"Portal authentication is required: HTTP {response.status}")
                content = page.content()
                context.storage_state(path=str(temporary_path))
                self._encrypt_state(temporary_path)
                browser.close()
                return content
        finally:
            temporary_path.unlink(missing_ok=True)

    def capture_user_login(
        self,
        login_url: str,
        *,
        success_url_pattern: str,
        timeout_ms: int = 180_000,
    ) -> None:
        """Open a visible browser and wait for the user to finish authentication."""
        temporary = tempfile.NamedTemporaryFile(prefix="campus-ai-login-", suffix=".json", delete=False)
        temporary_path = Path(temporary.name)
        temporary.close()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                page.goto(login_url)
                page.wait_for_url(success_url_pattern, timeout=timeout_ms)
                context.storage_state(path=str(temporary_path))
                self._encrypt_state(temporary_path)
                browser.close()
        finally:
            temporary_path.unlink(missing_ok=True)

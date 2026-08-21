from __future__ import annotations

from cryptography.fernet import Fernet

from campus_connector_sdk import AuthState
from campus_ai_connector_generic_browser import EncryptedBrowserSession, GenericBrowserConnector


CONFIG: dict[str, object] = {
    "page_url": "https://campus.example/notices/current",
    "login_url": "https://campus.example/login",
    "success_url_pattern": "https://campus.example/**",
    "allowed_hosts": ["campus.example"],
    "title_selector": "h1",
    "body_selector": "article",
}


def test_browser_state_is_connector_owned_and_encrypted(tmp_path) -> None:
    session = EncryptedBrowserSession(tmp_path, Fernet.generate_key().decode("ascii"))
    plaintext_path = tmp_path / "state.json"
    restored_path = tmp_path / "restored.json"
    plaintext_path.write_text('{"cookies": [{"name": "session", "value": "secret"}]}', encoding="utf-8")

    session._encrypt_state("instance-one", plaintext_path)
    assert b"secret" not in session.state_path("instance-one").read_bytes()
    assert session._decrypt_state("instance-one", restored_path) is True
    assert "secret" in restored_path.read_text(encoding="utf-8")


def test_browser_connector_exposes_user_assisted_auth_state(tmp_path) -> None:
    connector = GenericBrowserConnector(
        session_directory=tmp_path,
        secret_key=Fernet.generate_key().decode("ascii"),
    )

    assert connector.auth_status("instance-one", CONFIG).state is AuthState.AUTH_REQUIRED
    challenge = connector.begin_auth("instance-one", CONFIG)
    assert challenge.state is AuthState.WAITING_FOR_USER
    assert challenge.challenge is not None

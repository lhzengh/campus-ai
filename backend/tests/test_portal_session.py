from __future__ import annotations

from cryptography.fernet import Fernet

from campus_ai.sources.playwright_portal import PortalBrowserSession


def test_portal_state_is_encrypted(tmp_path) -> None:
    encrypted_path = tmp_path / "session.enc"
    plaintext_path = tmp_path / "state.json"
    restored_path = tmp_path / "restored.json"
    plaintext_path.write_text('{"cookies": [{"name": "session", "value": "secret"}]}', encoding="utf-8")
    portal = PortalBrowserSession(encrypted_path, Fernet.generate_key().decode("ascii"))

    portal._encrypt_state(plaintext_path)
    assert b"secret" not in encrypted_path.read_bytes()
    assert portal._decrypt_state(restored_path) is True
    assert "secret" in restored_path.read_text(encoding="utf-8")

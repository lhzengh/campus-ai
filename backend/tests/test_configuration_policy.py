from __future__ import annotations

import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_compose_requires_external_database_configuration() -> None:
    compose = (REPOSITORY_ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "${CAMPUS_AI_DATABASE_URL:?" in compose
    assert "${POSTGRES_DB:?" in compose
    assert "${POSTGRES_USER:?" in compose
    assert "${POSTGRES_PASSWORD:?" in compose
    assert "change" + "-me" not in compose
    assert ":-postgresql" not in compose


def test_flutter_api_endpoint_has_no_compiled_default() -> None:
    config = (REPOSITORY_ROOT / "frontend/lib/core/app_config.dart").read_text(encoding="utf-8")
    api_declaration = config.split("static const enableFcm", maxsplit=1)[0]

    assert "String.fromEnvironment('CAMPUS_AI_API_URL')" in api_declaration
    assert "defaultValue" not in api_declaration


def test_production_urls_do_not_embed_credentials() -> None:
    embedded_credentials = re.compile(r"https?://[^\s/@:]+:[^\s/@]+@")
    production_paths = [
        REPOSITORY_ROOT / "compose.yaml",
        *sorted((REPOSITORY_ROOT / "backend/campus_ai").rglob("*.py")),
        *sorted((REPOSITORY_ROOT / "frontend/lib").rglob("*.dart")),
    ]

    offenders = [
        str(path.relative_to(REPOSITORY_ROOT))
        for path in production_paths
        if embedded_credentials.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []

from __future__ import annotations

import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from campus_connector_sdk.base import CampusConnector
from campus_connector_sdk.errors import ConnectorProtocolError
from campus_connector_sdk.models import (
    AuthResult,
    AuthStatusRequest,
    BeginAuthRequest,
    CampusItemBatch,
    ConfigValidationRequest,
    ConfigValidationResult,
    ConnectorErrorBody,
    ConnectorManifest,
    SubmitAuthRequest,
    SyncRequest,
)


def create_connector_app(connector: CampusConnector, *, shared_token: str = "") -> FastAPI:
    """Expose a Connector through the stable HTTP boundary used by Core."""

    app = FastAPI(
        title=f"{connector.manifest.display_name} Connector",
        version=connector.manifest.version,
    )

    def authorize(authorization: str | None = Header(default=None)) -> None:
        # Empty tokens are useful only for isolated tests; deployments provide one.
        if not shared_token:
            return
        expected = f"Bearer {shared_token}"
        if authorization is None or not secrets.compare_digest(authorization, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Connector token")

    protected = [Depends(authorize)]

    @app.exception_handler(ConnectorProtocolError)
    async def handle_protocol_error(_: Request, exc: ConnectorProtocolError) -> JSONResponse:
        # Preserve typed failures so Core never has to parse Connector log text.
        status_code = {
            "config_invalid": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "auth_required": status.HTTP_409_CONFLICT,
            "access_denied": status.HTTP_403_FORBIDDEN,
            "rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
            "unsupported_operation": status.HTTP_405_METHOD_NOT_ALLOWED,
            "protocol_mismatch": status.HTTP_409_CONFLICT,
        }.get(exc.code.value, status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_422_UNPROCESSABLE_ENTITY)
        body = ConnectorErrorBody(
            code=exc.code,
            message=str(exc),
            retryable=exc.retryable,
            details=exc.details,
        )
        return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/manifest", response_model=ConnectorManifest, dependencies=protected)
    def manifest() -> ConnectorManifest:
        return connector.manifest

    @app.post("/v1/config/validate", response_model=ConfigValidationResult, dependencies=protected)
    def validate_config(payload: ConfigValidationRequest) -> ConfigValidationResult:
        normalized = connector.validate_config(payload.config)
        return ConfigValidationResult(normalized_config=normalized)

    @app.post("/v1/auth/status", response_model=AuthResult, dependencies=protected)
    def auth_status(payload: AuthStatusRequest) -> AuthResult:
        return connector.auth_status(payload.instance_id, payload.config)

    @app.post("/v1/auth/begin", response_model=AuthResult, dependencies=protected)
    def begin_auth(payload: BeginAuthRequest) -> AuthResult:
        return connector.begin_auth(payload.instance_id, payload.config)

    @app.post("/v1/auth/respond", response_model=AuthResult, dependencies=protected)
    def submit_auth_response(payload: SubmitAuthRequest) -> AuthResult:
        return connector.submit_auth_response(
            payload.instance_id,
            payload.config,
            payload.challenge_id,
            payload.response,
        )

    @app.post("/v1/sync", response_model=CampusItemBatch, dependencies=protected)
    def sync(payload: SyncRequest) -> CampusItemBatch:
        return connector.sync(payload)

    return app

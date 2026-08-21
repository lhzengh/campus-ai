FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY packages/connector-sdk-python /build/connector-sdk
RUN pip install --no-cache-dir /build/connector-sdk

COPY backend/pyproject.toml ./
COPY backend/campus_ai ./campus_ai
RUN pip install --no-cache-dir .

COPY backend/alembic.ini ./
COPY backend/migrations ./migrations

RUN useradd --create-home --uid 10001 campus-ai \
    && chown -R campus-ai:campus-ai /app
USER campus-ai

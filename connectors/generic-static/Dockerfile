FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY packages/connector-sdk-python /build/connector-sdk
RUN pip install --no-cache-dir /build/connector-sdk

COPY connectors/generic-static /build/connector
RUN pip install --no-cache-dir /build/connector

RUN useradd --create-home --uid 10002 connector
USER connector

EXPOSE 8100
CMD ["uvicorn", "campus_ai_connector_generic_static.app:app", "--host", "0.0.0.0", "--port", "8100"]

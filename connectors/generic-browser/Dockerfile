FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY packages/connector-sdk-python /build/connector-sdk
RUN pip install --no-cache-dir /build/connector-sdk

COPY connectors/generic-browser /build/connector
RUN pip install --no-cache-dir /build/connector \
    && playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright

RUN useradd --create-home --uid 10003 connector \
    && mkdir -p /app/data/sessions \
    && chown -R connector:connector /app/data
USER connector

EXPOSE 8200
CMD ["uvicorn", "campus_ai_connector_generic_browser.app:app", "--host", "0.0.0.0", "--port", "8200"]

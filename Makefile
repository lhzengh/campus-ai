.PHONY: help test test-coverage security-audit compose-config up down migrate flutter-test

PYTHON_PACKAGE_PATH := packages/connector-sdk-python/src:connectors/generic-static/src:connectors/generic-browser/src:backend

help:
	@echo "Campus AI phase-0 commands"
	@echo "  make test             Run SDK, Connector, and Core unit tests"
	@echo "  make test-coverage    Run all Python tests with Core coverage"
	@echo "  make security-audit   Audit Python dependencies and production source"
	@echo "  make compose-config   Validate the resolved Compose configuration"
	@echo "  make up               Build and start the validation backend"
	@echo "  make down             Stop the validation backend"
	@echo "  make migrate          Apply database migrations with the one-shot service"
	@echo "  make flutter-test     Analyze and test the Flutter client"

test:
	PYTHONPATH=$(PYTHON_PACKAGE_PATH) .venv/bin/pytest packages/connector-sdk-python/tests connectors/generic-static/tests connectors/generic-browser/tests backend/tests

test-coverage:
	PYTHONPATH=$(PYTHON_PACKAGE_PATH) .venv/bin/pytest packages/connector-sdk-python/tests connectors/generic-static/tests connectors/generic-browser/tests backend/tests --cov=campus_ai --cov-report=term-missing

security-audit:
	.venv/bin/pip-audit --local --skip-editable
	.venv/bin/bandit -r backend/campus_ai connectors/generic-browser/src connectors/generic-static/src packages/connector-sdk-python/src spikes -q -ll

compose-config:
	docker compose config --quiet

up:
	docker compose up --build -d

down:
	docker compose down

migrate:
	docker compose run --rm migrate

flutter-test:
	cd frontend && ../.tooling/flutter/bin/flutter analyze
	cd frontend && ../.tooling/flutter/bin/flutter test

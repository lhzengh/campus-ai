.PHONY: help test test-coverage compose-config up down migrate flutter-test

help:
	@echo "Campus AI phase-0 commands"
	@echo "  make test             Run backend unit tests"
	@echo "  make test-coverage    Run backend tests with coverage"
	@echo "  make compose-config   Validate the resolved Compose configuration"
	@echo "  make up               Build and start the validation backend"
	@echo "  make down             Stop the validation backend"
	@echo "  make migrate          Apply database migrations with the one-shot service"
	@echo "  make flutter-test     Analyze and test the Flutter client"

test:
	.venv/bin/pytest backend/tests

test-coverage:
	.venv/bin/pytest backend/tests --cov=campus_ai --cov-report=term-missing

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

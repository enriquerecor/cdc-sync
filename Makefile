SHELL := /bin/bash

ENV_FILE ?= .env
FRONTEND_ENV_TEMPLATE := frontend/.env.example
FRONTEND_ENV_FILE := frontend/.env
WORKER_TEST_VENV_DIR := .venv
WORKER_TEST_VENV_PYTHON := $(WORKER_TEST_VENV_DIR)/bin/python
WORKER_TEST_VENV_STAMP := $(WORKER_TEST_VENV_DIR)/.worker-test-installed
POSTGRES_CONNECTOR_TEMPLATE := infrastructure/debezium/connectors/postgresql/source.config.template.json
POSTGRES_CONNECTOR_ENV_TEMPLATE := infrastructure/debezium/connectors/postgresql/source.local.env.example
POSTGRES_CONNECTOR_ENV_FILE := infrastructure/debezium/connectors/generated/postgresql-source.local.env
POSTGRES_CONNECTOR_OUTPUT := infrastructure/debezium/connectors/generated/postgresql-source.local.json
CONNECT_RETRY_ATTEMPTS ?= 15
CONNECT_RETRY_DELAY_SECONDS ?= 2
DEMO_RUNNER := python3 infrastructure/e2e/demo_local.py
ANALYTICS_DATASET_PYTHON ?= /usr/bin/python3
ANALYTICS_DATASET_RUNNER := $(ANALYTICS_DATASET_PYTHON) demos/industrial-analytics/industrial_analytics_dataset.py
ANALYTICS_DATASET_SIZE ?= small
ANALYTICS_DATASET_SCHEMA ?= industrial_analytics
ANALYTICS_DATASET_SEED ?= 20260617
ANALYTICS_DATASET_SCALE ?= 1
ANALYTICS_DATASET_TERM ?= aislamiento
ANALYTICS_DATASET_ARGS ?=

define require_env_file
	@if [[ ! -f "$(ENV_FILE)" ]]; then \
		echo "No existe $(ENV_FILE). Ejecuta 'make env-init' antes de continuar." >&2; \
		exit 1; \
	fi
endef

define require_postgres_connector_env_file
	@if [[ ! -f "$(POSTGRES_CONNECTOR_ENV_FILE)" ]]; then \
		echo "No existe $(POSTGRES_CONNECTOR_ENV_FILE). Ejecuta 'make env-init' antes de continuar." >&2; \
		exit 1; \
	fi
endef

.DEFAULT_GOAL := help

.PHONY: help env-init api-up api-migrate api-logs api-health api-test api-test-integration frontend-install frontend-dev frontend-build frontend-smoke frontend-api-types frontend-up frontend-logs worker-test-deps worker-test workers-up workers-down demo-up demo-migrate demo-configure demo-materialize demo-workers demo-changes demo-assert demo-local e2e-validate analytics-dataset-load analytics-dataset-changes analytics-dataset-benchmark analytics-dataset-demo debezium-postgres-render debezium-postgres-apply debezium-postgres-status

help:
	@echo "Objetivos disponibles:"
	@echo "  make env-init"
	@echo "  make api-up"
	@echo "  make api-migrate"
	@echo "  make api-logs"
	@echo "  make api-health"
	@echo "  make api-test"
	@echo "  make api-test-integration"
	@echo "  make frontend-install"
	@echo "  make frontend-dev"
	@echo "  make frontend-build"
	@echo "  make frontend-smoke"
	@echo "  make frontend-api-types"
	@echo "  make frontend-up"
	@echo "  make frontend-logs"
	@echo "  make worker-test-deps"
	@echo "  make worker-test"
	@echo "  make workers-up WORKER_IDS=crm-worker,sales-worker"
	@echo "  make workers-down WORKER_IDS=crm-worker,sales-worker"
	@echo "  make demo-up"
	@echo "  make demo-migrate"
	@echo "  make demo-configure"
	@echo "  make demo-materialize"
	@echo "  make demo-workers"
	@echo "  make demo-changes"
	@echo "  make demo-assert"
	@echo "  make demo-local"
	@echo "  make e2e-validate"
	@echo "  make analytics-dataset-load ANALYTICS_DATASET_SIZE=small"
	@echo "  make analytics-dataset-changes"
	@echo "  make analytics-dataset-benchmark"
	@echo "  make analytics-dataset-demo"
	@echo "  make debezium-postgres-render"
	@echo "  make debezium-postgres-apply"
	@echo "  make debezium-postgres-status"

env-init:
	@if [[ -f "$(ENV_FILE)" ]]; then \
		echo "$(ENV_FILE) ya existe. No se sobrescribe."; \
	else \
		cp .env.example "$(ENV_FILE)"; \
		echo "$(ENV_FILE) creado a partir de .env.example"; \
	fi
	@if [[ -f "$(POSTGRES_CONNECTOR_ENV_FILE)" ]]; then \
		echo "$(POSTGRES_CONNECTOR_ENV_FILE) ya existe. No se sobrescribe."; \
	else \
		mkdir -p "$$(dirname "$(POSTGRES_CONNECTOR_ENV_FILE)")"; \
		cp "$(POSTGRES_CONNECTOR_ENV_TEMPLATE)" "$(POSTGRES_CONNECTOR_ENV_FILE)"; \
		echo "$(POSTGRES_CONNECTOR_ENV_FILE) creado a partir de $(POSTGRES_CONNECTOR_ENV_TEMPLATE)"; \
	fi
	@if [[ -f "$(FRONTEND_ENV_FILE)" ]]; then \
		echo "$(FRONTEND_ENV_FILE) ya existe. No se sobrescribe."; \
	else \
		cp "$(FRONTEND_ENV_TEMPLATE)" "$(FRONTEND_ENV_FILE)"; \
		echo "$(FRONTEND_ENV_FILE) creado a partir de $(FRONTEND_ENV_TEMPLATE)"; \
	fi

api-up:
	@docker compose up -d --build control-plane-postgres api

api-migrate:
	@docker compose up -d control-plane-postgres
	@docker compose run --rm api alembic -c api/alembic.ini upgrade head

api-logs:
	@docker compose logs -f api control-plane-postgres

api-health:
	$(require_env_file)
	@set -a; source "$(ENV_FILE)"; set +a; \
	curl -fsS "http://localhost:$${API_PORT:-8000}/health"

api-test:
	@docker build --target test -f api/Dockerfile -t cdc-sync-api-test .
	@docker run --rm cdc-sync-api-test

api-test-integration:
	@docker build --target test -f api/Dockerfile -t cdc-sync-api-test .
	@set -euo pipefail; \
	network_name="cdc-sync-api-repo-test"; \
	postgres_name="cdc-sync-api-repo-test-postgres"; \
	cleanup() { \
		docker rm -f "$${postgres_name}" >/dev/null 2>&1 || true; \
		docker network rm "$${network_name}" >/dev/null 2>&1 || true; \
	}; \
	cleanup; \
	trap cleanup EXIT; \
	docker network create "$${network_name}" >/dev/null; \
	docker run --rm -d \
		--name "$${postgres_name}" \
		--network "$${network_name}" \
		-e POSTGRES_DB=cdc_sync_control_plane_test \
		-e POSTGRES_USER=cdc_sync_control_plane_test \
		-e POSTGRES_PASSWORD=cdc_sync_control_plane_test \
		postgres:16-alpine >/dev/null; \
	for attempt in {1..30}; do \
		if docker exec "$${postgres_name}" pg_isready \
			-U cdc_sync_control_plane_test \
			-d cdc_sync_control_plane_test >/dev/null 2>&1; then \
			break; \
		fi; \
		if [[ "$${attempt}" == "30" ]]; then \
			echo "PostgreSQL de integración no arrancó a tiempo" >&2; \
			exit 1; \
		fi; \
		sleep 1; \
	done; \
	docker run --rm \
		--network "$${network_name}" \
		-e API_REPOSITORY_INTEGRATION_TESTS=true \
		-e API_TEST_DATABASE_URL="postgresql+psycopg://cdc_sync_control_plane_test:cdc_sync_control_plane_test@$${postgres_name}:5432/cdc_sync_control_plane_test" \
		cdc-sync-api-test \
		pytest api/tests/test_control_plane_repository_integration.py -v

frontend-install:
	@npm --prefix frontend ci

frontend-dev:
	@npm --prefix frontend run dev

frontend-build:
	@npm --prefix frontend run build

frontend-smoke:
	@npm --prefix frontend run smoke:admin

frontend-api-types:
	@npm --prefix frontend run api:types

frontend-up:
	@set -euo pipefail; \
	output="$$(docker compose up -d --build --quiet-build --quiet-pull frontend 2>&1)" || { \
		echo "$$output" >&2; \
		exit 1; \
	}; \
	echo "Frontend disponible en http://localhost:5173"

frontend-logs:
	@docker compose logs -f frontend

worker-test-deps: $(WORKER_TEST_VENV_STAMP)
	@echo "Entorno virtual del worker disponible en $(WORKER_TEST_VENV_DIR)"

worker-test: $(WORKER_TEST_VENV_STAMP)
	@PYTHONPATH="worker/src" \
		"$(WORKER_TEST_VENV_PYTHON)" -m pytest worker/tests -v

workers-up:
	@WORKER_IDS="$(WORKER_IDS)" $(DEMO_RUNNER) workers-up

workers-down:
	@WORKER_IDS="$(WORKER_IDS)" $(DEMO_RUNNER) workers-down

demo-up:
	@$(DEMO_RUNNER) up

demo-migrate:
	@$(DEMO_RUNNER) migrate

demo-configure:
	@$(DEMO_RUNNER) configure

demo-materialize:
	@$(DEMO_RUNNER) materialize

demo-workers:
	@$(DEMO_RUNNER) workers

demo-changes:
	@$(DEMO_RUNNER) changes

demo-assert:
	@$(DEMO_RUNNER) assert

demo-local:
	@$(DEMO_RUNNER) all

e2e-validate:
	@$(MAKE) demo-local

analytics-dataset-load:
	@docker compose up -d postgres
	@$(ANALYTICS_DATASET_RUNNER) load \
		--size "$(ANALYTICS_DATASET_SIZE)" \
		--schema "$(ANALYTICS_DATASET_SCHEMA)" \
		--seed "$(ANALYTICS_DATASET_SEED)" \
		--scale "$(ANALYTICS_DATASET_SCALE)" \
		$(ANALYTICS_DATASET_ARGS)

analytics-dataset-changes:
	@$(ANALYTICS_DATASET_RUNNER) changes \
		--schema "$(ANALYTICS_DATASET_SCHEMA)"

analytics-dataset-benchmark:
	@$(ANALYTICS_DATASET_RUNNER) benchmark \
		--schema "$(ANALYTICS_DATASET_SCHEMA)" \
		--term "$(ANALYTICS_DATASET_TERM)"

analytics-dataset-demo:
	@$(MAKE) analytics-dataset-load
	@$(MAKE) analytics-dataset-benchmark


$(WORKER_TEST_VENV_PYTHON):
	@python3 -m venv "$(WORKER_TEST_VENV_DIR)"

$(WORKER_TEST_VENV_STAMP): worker/requirements.txt worker/requirements-dev.txt | $(WORKER_TEST_VENV_PYTHON)
	@"$(WORKER_TEST_VENV_PYTHON)" -m pip install -r worker/requirements-dev.txt
	@touch "$(WORKER_TEST_VENV_STAMP)"

debezium-postgres-render:
	$(require_postgres_connector_env_file)
	@./infrastructure/debezium/connectors/render-template.sh \
		"$(POSTGRES_CONNECTOR_TEMPLATE)" \
		"$(POSTGRES_CONNECTOR_OUTPUT)" \
		"$(POSTGRES_CONNECTOR_ENV_FILE)"
	@echo "Configuración renderizada en $(POSTGRES_CONNECTOR_OUTPUT)"

debezium-postgres-apply: debezium-postgres-render
	$(require_env_file)
	$(require_postgres_connector_env_file)
	@set -a; source "$(ENV_FILE)"; source "$(POSTGRES_CONNECTOR_ENV_FILE)"; set +a; \
	attempt=1; \
	while [[ $$attempt -le $(CONNECT_RETRY_ATTEMPTS) ]]; do \
		if curl -fsS -X PUT "http://localhost:$${CONNECT_PORT}/connectors/$${DEBEZIUM_POSTGRES_CONNECTOR_NAME}/config" \
			-H "Content-Type: application/json" \
			--data @"$(POSTGRES_CONNECTOR_OUTPUT)"; then \
			exit 0; \
		fi; \
		if [[ $$attempt -lt $(CONNECT_RETRY_ATTEMPTS) ]]; then \
			sleep $(CONNECT_RETRY_DELAY_SECONDS); \
		fi; \
		((attempt++)); \
	done; \
	echo "No se pudo aplicar el conector $${DEBEZIUM_POSTGRES_CONNECTOR_NAME}" >&2; \
	exit 1

debezium-postgres-status:
	$(require_env_file)
	$(require_postgres_connector_env_file)
	@set -a; source "$(ENV_FILE)"; source "$(POSTGRES_CONNECTOR_ENV_FILE)"; set +a; \
	attempt=1; \
	while [[ $$attempt -le $(CONNECT_RETRY_ATTEMPTS) ]]; do \
		if curl -fsS "http://localhost:$${CONNECT_PORT}/connectors/$${DEBEZIUM_POSTGRES_CONNECTOR_NAME}/status"; then \
			exit 0; \
		fi; \
		if [[ $$attempt -lt $(CONNECT_RETRY_ATTEMPTS) ]]; then \
			sleep $(CONNECT_RETRY_DELAY_SECONDS); \
		fi; \
		((attempt++)); \
	done; \
	echo "No se pudo obtener el estado del conector $${DEBEZIUM_POSTGRES_CONNECTOR_NAME}" >&2; \
	exit 1

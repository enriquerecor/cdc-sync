SHELL := /bin/bash

ENV_FILE ?= .env
WORKER_TABLE_CONFIG_TEMPLATE := worker/config/tables.example.json
WORKER_TABLE_CONFIG_OUTPUT := worker/config/tables.json
WORKER_TEST_VENV_DIR := .venv
WORKER_TEST_VENV_PYTHON := $(WORKER_TEST_VENV_DIR)/bin/python
WORKER_TEST_VENV_STAMP := $(WORKER_TEST_VENV_DIR)/.worker-test-installed
POSTGRES_CONNECTOR_TEMPLATE := infrastructure/debezium/connectors/postgresql/source.config.template.json
POSTGRES_CONNECTOR_OUTPUT := infrastructure/debezium/connectors/generated/postgresql-source.local.json
CONNECT_RETRY_ATTEMPTS ?= 15
CONNECT_RETRY_DELAY_SECONDS ?= 2

.DEFAULT_GOAL := help

.PHONY: help env-init worker-test-deps worker-test debezium-postgres-render debezium-postgres-apply debezium-postgres-status

help:
	@echo "Objetivos disponibles:"
	@echo "  make env-init"
	@echo "  make worker-test-deps"
	@echo "  make worker-test"
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
	@if [[ -f "$(WORKER_TABLE_CONFIG_OUTPUT)" ]]; then \
		echo "$(WORKER_TABLE_CONFIG_OUTPUT) ya existe. No se sobrescribe."; \
	else \
		cp "$(WORKER_TABLE_CONFIG_TEMPLATE)" "$(WORKER_TABLE_CONFIG_OUTPUT)"; \
		echo "$(WORKER_TABLE_CONFIG_OUTPUT) creado a partir de $(WORKER_TABLE_CONFIG_TEMPLATE)"; \
	fi

worker-test-deps: $(WORKER_TEST_VENV_STAMP)
	@echo "Entorno virtual del worker disponible en $(WORKER_TEST_VENV_DIR)"

worker-test: $(WORKER_TEST_VENV_STAMP)
	@PYTHONPATH="worker/src" \
		"$(WORKER_TEST_VENV_PYTHON)" -m pytest worker/tests -v

$(WORKER_TEST_VENV_PYTHON):
	@python3 -m venv "$(WORKER_TEST_VENV_DIR)"

$(WORKER_TEST_VENV_STAMP): worker/requirements.txt worker/requirements-dev.txt | $(WORKER_TEST_VENV_PYTHON)
	@"$(WORKER_TEST_VENV_PYTHON)" -m pip install -r worker/requirements-dev.txt
	@touch "$(WORKER_TEST_VENV_STAMP)"

debezium-postgres-render:
	@./infrastructure/debezium/connectors/render-template.sh \
		"$(POSTGRES_CONNECTOR_TEMPLATE)" \
		"$(POSTGRES_CONNECTOR_OUTPUT)" \
		"$(ENV_FILE)"
	@echo "Configuracion renderizada en $(POSTGRES_CONNECTOR_OUTPUT)"

debezium-postgres-apply: debezium-postgres-render
	@set -a; source "$(ENV_FILE)"; set +a; \
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
	@set -a; source "$(ENV_FILE)"; set +a; \
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

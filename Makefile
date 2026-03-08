SHELL := /bin/bash

ENV_FILE ?= .env
POSTGRES_CONNECTOR_TEMPLATE := infrastructure/debezium/connectors/postgresql/source.config.template.json
POSTGRES_CONNECTOR_OUTPUT := infrastructure/debezium/connectors/generated/postgresql-source.local.json

.DEFAULT_GOAL := help

.PHONY: help env-init debezium-postgres-render debezium-postgres-apply debezium-postgres-status

help:
	@echo "Objetivos disponibles:"
	@echo "  make env-init"
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

debezium-postgres-render:
	@./infrastructure/debezium/connectors/render-template.sh \
		"$(POSTGRES_CONNECTOR_TEMPLATE)" \
		"$(POSTGRES_CONNECTOR_OUTPUT)" \
		"$(ENV_FILE)"
	@echo "Configuracion renderizada en $(POSTGRES_CONNECTOR_OUTPUT)"

debezium-postgres-apply: debezium-postgres-render
	@set -a; source "$(ENV_FILE)"; set +a; \
	curl -fsS -X PUT "http://localhost:$${CONNECT_PORT}/connectors/$${DEBEZIUM_POSTGRES_CONNECTOR_NAME}/config" \
		-H "Content-Type: application/json" \
		--data @"$(POSTGRES_CONNECTOR_OUTPUT)"

debezium-postgres-status:
	@set -a; source "$(ENV_FILE)"; set +a; \
	for attempt in 1 2 3 4 5; do \
		if curl -fsS "http://localhost:$${CONNECT_PORT}/connectors/$${DEBEZIUM_POSTGRES_CONNECTOR_NAME}/status"; then \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "No se pudo obtener el estado del conector $${DEBEZIUM_POSTGRES_CONNECTOR_NAME}" >&2; \
	exit 1
